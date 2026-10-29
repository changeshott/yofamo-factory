#!/usr/bin/env python3
"""Kai — editor Yofamo. Merakit video Short final langsung dengan ffmpeg (gratis, tanpa buka CapCut):
shot Bima + voice-over Dara + subtitle kata-per-kata yang menyala + teks hook + punch zoom + whoosh + musik.

    python agents/editor/rakit.py <slug>          # hasil: videos/<slug>/export/final.mp4, status → draft
    python agents/editor/rakit.py <slug> --uji    # tanpa vo asli (nada uji), status tidak diubah

Gaya diatur di bible/gaya-edit.json. Musik latar: taruh file .mp3/.m4a/.wav di folder musik/.
Efek suara: taruh file di sfx/ (nama mengandung 'whoosh'); kalau kosong, whoosh dibuat otomatis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "aset"))
import gerak  # noqa: E402

VIDEOS = ROOT / "videos"
CACHE = ROOT / "cache" / "editor"
AUDIO_EXT = {".mp3", ".m4a", ".wav", ".aac", ".ogg", ".flac"}
FAMILY = {"seguibl": "Segoe UI Black", "ariblk": "Arial Black", "arialbd": "Arial", "poppins-bold": "Poppins",
          "dejavusans-bold": "DejaVu Sans", "arial bold": "Arial"}


def log(msg: str) -> None:
    print(f"[kai] {msg}", flush=True)


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def style() -> dict:
    base = read_json(ROOT / "bible" / "gaya-edit.json", {})
    for k in ("subtitle", "hook", "gerak", "audio", "handle"):
        base.setdefault(k, {})
    return base


def ass_color(hex_rgb: str, alpha: str = "00") -> str:
    h = (hex_rgb or "FFFFFF").lstrip("#").upper().rjust(6, "0")
    return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}"


def ass_time(t: float) -> str:
    t = max(0.0, t)
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02}:{s:02}.{cs:02}"


def clean(text: str) -> str:
    return re.sub(r"[{}\\]", "", text).strip()


# ------------------------------------------------------------------ subtitle ASS
def groups(words: list[dict], sentence_starts: list[float], max_words: int) -> list[list[dict]]:
    out, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        new_sentence = nxt is not None and any(w["mulai"] < s <= nxt["mulai"] + 1e-6 for s in sentence_starts)
        if len(cur) >= max_words or nxt is None or new_sentence or (nxt["mulai"] - w["selesai"] > 0.35):
            out.append(cur)
            cur = []
    return out


def kunci(t: str) -> str:
    return re.sub(r"[^0-9a-z]", "", t.lower())


def build_ass(words: list[dict], kalimat: list[dict], hook: str, total: float, st: dict, family: str,
              senyap: list[tuple[float, float]] | None = None, narasi: list[dict] | None = None,
              akhir: float | None = None) -> str:
    """senyap: rentang waktu kartu grafis; subtitle disembunyikan di sana supaya tidak bertabrakan dengan teks kartu.
    narasi: kalimat naskah Raka (teks_layar → teks atas sesaat, penekanan → kata disorot).
    akhir: durasi video termasuk penutup (frame terakhir ditahan + teks ajakan)."""
    sub, hk, hd = st["subtitle"], st["hook"], st["handle"]
    tl, pn = st.get("teks_layar", {}), st.get("penutup", {})
    akhir = akhir or total
    narasi = narasi or []
    white, act = ass_color(sub.get("warna", "FFFFFF")), ass_color(sub.get("warna_aktif", "FF9A4D"))
    tek = ass_color(sub.get("warna_tekan", "FFD23F"))
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{family},{sub.get('ukuran', 92)},{white},{white},&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,{sub.get('garis', 7)},3,2,60,60,{sub.get('jarak_bawah', 560)},1
Style: Hook,{family},{hk.get('ukuran', 84)},{ass_color(hk.get('warna_teks', '141414'))},{white},{ass_color(hk.get('warna_kotak', 'FF9A4D'))},&H00000000,-1,0,0,0,100,100,0,0,3,22,0,8,70,70,{hk.get('jarak_atas', 260)},1
Style: Handle,{family},{hd.get('ukuran', 34)},{ass_color('FFFFFF', '70')},{white},&H90000000,&H00000000,-1,0,0,0,100,100,0,0,1,2,0,9,40,40,70,1
Style: Layar,{family},{tl.get('ukuran', 78)},{ass_color(tl.get('warna_teks', 'FFFFFF'))},{white},{ass_color(tl.get('warna_kotak', '141414'), '30')},&H00000000,-1,0,0,0,100,100,0,0,3,18,0,8,80,80,{tl.get('jarak_atas', 300)},1
Style: Akhir,{family},{pn.get('ukuran', 80)},{ass_color(pn.get('warna_teks', '141414'))},{white},{ass_color(pn.get('warna_kotak', 'FF9A4D'))},&H00000000,-1,0,0,0,100,100,0,0,3,24,0,2,90,90,{pn.get('jarak_bawah', sub.get('jarak_bawah', 560))},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    if hk.get("tampil", True) and hook:
        end = min(float(hk.get("maks_detik", 2.6)), (kalimat[0]["selesai"] if kalimat else 2.6))
        txt = "\\N".join(textwrap.wrap(clean(hook).upper(), 16)[:3])
        ev.append(f"Dialogue: 2,{ass_time(0)},{ass_time(end)},Hook,,0,0,0,,"
                  f"{{\\fad(0,180)\\fscx60\\fscy60\\t(0,120,\\fscx108\\fscy108)\\t(120,200,\\fscx100\\fscy100)}}{txt}")
    if hd.get("tampil", True) and hd.get("teks"):
        ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(akhir)},Handle,,0,0,0,,{clean(hd['teks'])}")
    sepi = senyap or []
    # teks layar: 1–4 kata penegas di atas, muncul di awal kalimatnya (bukan di kalimat hook & bukan saat kartu grafis)
    if tl.get("tampil", True):
        for k in kalimat:
            i = int(k.get("i", -1))
            teks = clean(str((narasi[i] if 0 <= i < len(narasi) else {}).get("teks_layar") or "")).strip()
            if not teks or i == 0 or any(a <= k["mulai"] + 0.1 < b for a, b in sepi):
                continue
            a = k["mulai"]
            b = min(k["selesai"], a + float(tl.get("maks_detik", 1.6)))
            ev.append(f"Dialogue: 2,{ass_time(a)},{ass_time(b)},Layar,,0,0,0,,"
                      f"{{\\fad(60,160)\\fscx70\\fscy70\\t(0,110,\\fscx106\\fscy106)\\t(110,180,\\fscx100\\fscy100)}}{teks.upper()}")
    # penutup: frame terakhir ditahan, ajakan singkat di tengah layar → video tidak terasa terpotong
    if akhir > total + 0.05 and pn.get("teks"):
        txt = "\\N".join(textwrap.wrap(clean(pn["teks"]).upper(), 18)[:3])
        mv = 330 if any(b >= total - 0.05 for _, b in sepi) else 0     # shot terakhir kartu grafis → turunkan supaya tidak menimpa teksnya
        ev.append(f"Dialogue: 3,{ass_time(total)},{ass_time(akhir)},Akhir,,0,0,{mv},,"
                  f"{{\\fad(150,250)\\fscx85\\fscy85\\t(0,200,\\fscx100\\fscy100)}}{txt}")
    # kata penekanan per kalimat → disorot warna lain
    tekan: set[tuple[int, str]] = set()
    for k in kalimat:
        i = int(k.get("i", -1))
        for w in (narasi[i] if 0 <= i < len(narasi) else {}).get("penekanan") or []:
            for bag in str(w).split():
                if kunci(bag):
                    tekan.add((i, kunci(bag)))

    def kal_dari(t: float) -> int:
        for k in kalimat:
            if k["mulai"] - 0.05 <= t < k["selesai"] + 0.05:
                return int(k.get("i", -1))
        return -1
    upper = sub.get("huruf_besar", True)
    starts = [k["mulai"] for k in kalimat[1:]]
    gs = groups(words, starts, int(sub.get("maks_kata", 3)))
    for gi, g in enumerate(gs):
        mid = (g[0]["mulai"] + g[-1]["selesai"]) / 2
        if any(a <= mid < b for a, b in sepi):
            continue
        limit = gs[gi + 1][0]["mulai"] if gi + 1 < len(gs) else total      # jangan tumpang tindih dengan grup berikutnya
        texts = [clean(w["kata"]).upper() if upper else clean(w["kata"]) for w in g]
        ki = kal_dari(mid)
        penting = [(ki, kunci(w["kata"])) in tekan for w in g]
        for j, w in enumerate(g):
            a = w["mulai"]
            b = g[j + 1]["mulai"] if j + 1 < len(g) else min(w["selesai"] + 0.12, limit)
            parts = []
            for q, t in enumerate(texts):
                if q == j:
                    besar = "\\fscx112\\fscy112" if penting[q] else ""
                    parts.append(f"{{\\c{tek if penting[q] else act}&{besar}}}{t}{{\\c{white}&\\fscx100\\fscy100}}")
                elif penting[q]:
                    parts.append(f"{{\\c{tek}&}}{t}{{\\c{white}&}}")
                else:
                    parts.append(t)
            pop = "{\\fscx78\\fscy78\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)}" if (j == 0 and sub.get("pop", True)) else ""
            ev.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,{pop}{' '.join(parts)}")
    return head + "\n".join(ev) + "\n"


# ------------------------------------------------------------------ audio pendukung
def pick_music(slug: str, mode: str, suasana: str = "") -> Path | None:
    """Pilih lagu dari musik/. Kalau naskah punya 'suasana' (tegang/ceria/misterius/epik/haru), utamakan
    lagu di musik/<suasana>/ atau yang namanya mengandung kata itu."""
    semua = sorted(f for f in (ROOT / "musik").rglob("*") if f.suffix.lower() in AUDIO_EXT)
    cocok = [f for f in semua if suasana and (suasana in f.parent.name.lower() or suasana in f.stem.lower())] if suasana else []
    files = cocok or semua
    if not files or mode == "tidak":
        return None
    if mode not in ("acak", ""):
        named = [f for f in files if f.name == mode]
        if named:
            return named[0]
    return files[int(hashlib.sha1(slug.encode()).hexdigest(), 16) % len(files)]


def whoosh_file() -> Path:
    own = sorted(f for f in (ROOT / "sfx").glob("*") if f.suffix.lower() in AUDIO_EXT and "whoosh" in f.name.lower())
    if own:
        return own[0]
    CACHE.mkdir(parents=True, exist_ok=True)
    out = CACHE / "whoosh.wav"
    if not out.exists():   # whoosh buatan: noise yang disapu filter + fade, 0,45 detik
        gerak.ff("-f", "lavfi", "-i", "anoisesrc=d=0.45:c=pink:a=0.6:r=48000",
                 "-af", "highpass=f=300,lowpass=f=5000,afade=t=in:d=0.18,afade=t=out:st=0.2:d=0.25,volume=0.9", str(out))
    return out


# ------------------------------------------------------------------ rakit
def main() -> None:
    ap = argparse.ArgumentParser(description="Kai: rakit video final dari shot Bima + suara Dara")
    ap.add_argument("slug")
    ap.add_argument("--uji", action="store_true", help="pakai nada uji sebagai suara, status tidak diubah")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{3,80}", a.slug):
        sys.exit("[kai] slug tidak valid")
    gerak.need_ffmpeg()
    vdir = VIDEOS / a.slug
    man = read_json(vdir / "aset" / "manifest.json", None)
    words = read_json(vdir / "words.json", None)
    script = read_json(vdir / "script.json", {})
    if not man or not man.get("klip"):
        sys.exit("[kai] aset/manifest.json belum ada. Bima harus menyiapkan visual dulu.")
    if man.get("kurang"):
        sys.exit(f"[kai] Visual kalimat {man['kurang']} belum ada. Jalankan Bima lagi.")
    if not words or not words.get("kata"):
        sys.exit("[kai] words.json belum ada. Dara harus membuat suara dulu.")
    if not a.uji:
        r = subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "list", "--json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
        st_now = next((v["status"] for v in json.loads(r.stdout or "[]") if v["slug"] == a.slug), None)
        if st_now not in ("aset", "draft"):
            sys.exit(f"[kai] status video '{st_now}'. Video dirakit setelah visual dari Bima siap (status aset).")
        if words.get("uji") or not (vdir / "vo.mp3").exists():
            sys.exit("[kai] vo.mp3 asli belum ada (words.json masih mode uji). Jalankan Dara tanpa --uji dulu.")

    st = style()
    font = Path(st.get("font") or gerak.font())
    family = FAMILY.get(font.stem.lower(), font.stem)
    total = float(man.get("durasi") or words.get("durasi"))
    pn = st.get("penutup", {})
    tutup = max(0.0, min(3.0, float(pn.get("detik", 1.2)))) if pn.get("tampil", True) else 0.0
    akhir = total + tutup
    klip = sorted(man["klip"], key=lambda k: (k["i"], k["potong"]))
    missing = [k["file"] for k in klip if not (vdir / "aset" / k["file"]).exists()]
    if missing:
        sys.exit(f"[kai] file shot hilang: {', '.join(missing[:5])}")

    out_dir = vdir / "export"
    out_dir.mkdir(exist_ok=True)
    ass = out_dir / "subtitle.ass"
    senyap = [(k["mulai"], k["selesai"]) for k in man["klip"] if k.get("jenis") == "grafis"]
    narasi = [x for x in script.get("narasi", []) if str(x.get("kalimat", "")).strip()]
    ass.write_text(build_ass(words["kata"], words.get("kalimat", []), script.get("hook_teks", ""), total, st, family, senyap,
                             narasi, akhir), encoding="utf-8")

    # ---- input
    args: list[str] = []
    for k in klip:
        args += ["-i", str(vdir / "aset" / k["file"])]
    n = len(klip)
    if a.uji:
        args += ["-f", "lavfi", "-t", f"{total:.3f}", "-i", "sine=frequency=180:sample_rate=48000"]
    else:
        args += ["-i", str(vdir / "vo.mp3")]
    idx_vo = n
    music = pick_music(a.slug, str(st["audio"].get("musik", "acak")), str(script.get("suasana", "")).lower().strip())
    idx = n + 1
    idx_bgm = idx_wh = None
    if music:
        args += ["-stream_loop", "-1", "-i", str(music)]
        idx_bgm, idx = idx, idx + 1
    cuts = [k["mulai"] for k in klip if k["potong"] == 0 and k["i"] > 0]
    if st["audio"].get("whoosh", True) and cuts:
        args += ["-i", str(whoosh_file())]
        idx_wh = idx

    # ---- video: punch zoom tiap shot (kecuali grafis yang sudah beranimasi), lalu sambung
    z, zd = float(st["gerak"].get("punch_zoom", 0.08)), float(st["gerak"].get("punch_detik", 0.28))
    chains = []
    for j, k in enumerate(klip):
        f = f"[{j}:v]trim=duration={k['durasi']:.3f},setpts=PTS-STARTPTS,fps={gerak.FPS}"
        if z > 0 and k["jenis"] != "grafis":
            s = f"(1+{z}*max(0\\,1-t/{zd}))"
            f += (f",scale=w='trunc({gerak.W}*{s}/2)*2':h='trunc({gerak.H}*{s}/2)*2':eval=frame:flags=bicubic,"
                  f"crop={gerak.W}:{gerak.H}")
        chains.append(f + ",setsar=1,format=yuv420p" + f"[v{j}]")
    chains.append("".join(f"[v{j}]" for j in range(n)) + f"concat=n={n}:v=1:a=0[cat]")
    if tutup > 0:   # tahan frame terakhir, sedikit digelapkan perlahan supaya teks penutup terbaca
        chains.append(f"[cat]tpad=stop_mode=clone:stop_duration={tutup:.3f},eq=brightness='if(gte(t\\,{total:.3f})\\,-0.3*min(1\\,(t-{total:.3f})/0.4)\\,0)':eval=frame[base]")
    else:
        chains.append("[cat]null[base]")
    fontsdir = gerak.esc(font.parent)
    chains.append(f"[base]subtitles=filename='{gerak.esc(ass)}':fontsdir='{fontsdir}'[vout]")

    # ---- audio: suara + musik (otomatis mengecil saat ada suara) + whoosh di pergantian kalimat
    chains.append(f"[{idx_vo}:a]aresample=48000,apad=whole_dur={akhir:.3f},asplit=2[vo1][vo2]")
    mix = ["[vo1]"]
    if idx_bgm is not None:
        chains.append(f"[{idx_bgm}:a]aresample=48000,atrim=duration={akhir:.3f},volume={st['audio'].get('volume_musik_db', -20)}dB,"
                      f"afade=t=out:st={max(0, akhir - max(1.2, tutup + 0.6)):.2f}:d={max(1.2, tutup + 0.6):.2f}[bg]")
        chains.append("[bg][vo2]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=350[bgd]")
        mix.append("[bgd]")
    else:
        chains.append("[vo2]anullsink")
    if idx_wh is not None:
        chains.append(f"[{idx_wh}:a]aresample=48000,volume={st['audio'].get('volume_whoosh_db', -16)}dB,asplit={len(cuts)}"
                      + "".join(f"[w{c}]" for c in range(len(cuts))))
        for c, t in enumerate(cuts):
            ms = max(0, int((t - 0.18) * 1000))
            chains.append(f"[w{c}]adelay={ms}|{ms}[wd{c}]")
            mix.append(f"[wd{c}]")
    lufs = st["audio"].get("loudness_lufs", -14)
    chains.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I={lufs}:TP=-1.5:LRA=11,"
                  f"aresample=48000[aout]")

    final = out_dir / "final.mp4"
    tmp = out_dir / "final.tmp.mp4"
    log(f"merakit {n} shot, {total:.1f} dtk + penutup {tutup:.1f} dtk{', musik: ' + music.name if music else ', tanpa musik'}{', whoosh' if idx_wh is not None else ''}")
    t0 = time.time()
    gerak.ff(*args, "-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]", "-t", f"{akhir:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(gerak.FPS),
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp))
    tmp.replace(final)
    gerak.ff("-ss", "0.8", "-i", str(final), "-frames:v", "1", "-q:v", "3", str(out_dir / "sampul.jpg"))
    info = {"dibuat": datetime.now().isoformat(timespec="seconds"), "uji": a.uji, "durasi": round(gerak.duration(final), 2),
            "shot": n, "musik": music.name if music else None, "font": family, "pakai_ai": bool(man.get("pakai_ai")),
            "suara_detik": round(total, 2), "penutup_detik": round(tutup, 2)}
    (out_dir / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"selesai dalam {time.time() - t0:.0f} dtk: videos/{a.slug}/export/final.mp4 ({info['durasi']} dtk)")
    if not music:
        log("Tanpa musik latar. Taruh beberapa lagu bebas royalti di folder musik/ (misalnya dari YouTube Audio Library).")
    if man.get("pakai_ai"):
        log("Ada gambar AI realistis: saat upload, centang 'konten diubah/sintetis'.")
    if a.uji:
        log("mode uji: status tidak diubah")
        return
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", a.slug, "draft", "--note", "dirakit Kai"], check=True, cwd=ROOT)
    log("status → draft (video jadi, tunggu dicek Zona)")


if __name__ == "__main__":
    main()

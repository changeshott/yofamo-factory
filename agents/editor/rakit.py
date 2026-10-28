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


def build_ass(words: list[dict], kalimat: list[dict], hook: str, total: float, st: dict, family: str) -> str:
    sub, hk, hd = st["subtitle"], st["hook"], st["handle"]
    white, act = ass_color(sub.get("warna", "FFFFFF")), ass_color(sub.get("warna_aktif", "FF9A4D"))
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
        ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(total)},Handle,,0,0,0,,{clean(hd['teks'])}")
    upper = sub.get("huruf_besar", True)
    starts = [k["mulai"] for k in kalimat[1:]]
    gs = groups(words, starts, int(sub.get("maks_kata", 3)))
    for gi, g in enumerate(gs):
        limit = gs[gi + 1][0]["mulai"] if gi + 1 < len(gs) else total      # jangan tumpang tindih dengan grup berikutnya
        texts = [clean(w["kata"]).upper() if upper else clean(w["kata"]) for w in g]
        for j, w in enumerate(g):
            a = w["mulai"]
            b = g[j + 1]["mulai"] if j + 1 < len(g) else min(w["selesai"] + 0.12, limit)
            parts = [f"{{\\c{act}&}}{t}{{\\c{white}&}}" if q == j else t for q, t in enumerate(texts)]
            pop = "{\\fscx78\\fscy78\\t(0,90,\\fscx106\\fscy106)\\t(90,150,\\fscx100\\fscy100)}" if (j == 0 and sub.get("pop", True)) else ""
            ev.append(f"Dialogue: 1,{ass_time(a)},{ass_time(b)},Sub,,0,0,0,,{pop}{' '.join(parts)}")
    return head + "\n".join(ev) + "\n"


# ------------------------------------------------------------------ audio pendukung
def pick_music(slug: str, mode: str) -> Path | None:
    files = sorted(f for f in (ROOT / "musik").glob("*") if f.suffix.lower() in AUDIO_EXT)
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
    klip = sorted(man["klip"], key=lambda k: (k["i"], k["potong"]))
    missing = [k["file"] for k in klip if not (vdir / "aset" / k["file"]).exists()]
    if missing:
        sys.exit(f"[kai] file shot hilang: {', '.join(missing[:5])}")

    out_dir = vdir / "export"
    out_dir.mkdir(exist_ok=True)
    ass = out_dir / "subtitle.ass"
    ass.write_text(build_ass(words["kata"], words.get("kalimat", []), script.get("hook_teks", ""), total, st, family), encoding="utf-8")

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
    music = pick_music(a.slug, str(st["audio"].get("musik", "acak")))
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
    chains.append("".join(f"[v{j}]" for j in range(n)) + f"concat=n={n}:v=1:a=0[base]")
    fontsdir = gerak.esc(font.parent)
    chains.append(f"[base]subtitles=filename='{gerak.esc(ass)}':fontsdir='{fontsdir}'[vout]")

    # ---- audio: suara + musik (otomatis mengecil saat ada suara) + whoosh di pergantian kalimat
    chains.append(f"[{idx_vo}:a]aresample=48000,apad=whole_dur={total:.3f},asplit=2[vo1][vo2]")
    mix = ["[vo1]"]
    if idx_bgm is not None:
        chains.append(f"[{idx_bgm}:a]aresample=48000,atrim=duration={total:.3f},volume={st['audio'].get('volume_musik_db', -20)}dB,"
                      f"afade=t=out:st={max(0, total - 1.2):.2f}:d=1.2[bg]")
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
    log(f"merakit {n} shot, {total:.1f} dtk{', musik: ' + music.name if music else ', tanpa musik'}{', whoosh' if idx_wh is not None else ''}")
    t0 = time.time()
    gerak.ff(*args, "-filter_complex", ";".join(chains), "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
             "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(gerak.FPS),
             "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(tmp))
    tmp.replace(final)
    gerak.ff("-ss", "0.8", "-i", str(final), "-frames:v", "1", "-q:v", "3", str(out_dir / "sampul.jpg"))
    info = {"dibuat": datetime.now().isoformat(timespec="seconds"), "uji": a.uji, "durasi": round(gerak.duration(final), 2),
            "shot": n, "musik": music.name if music else None, "font": family, "pakai_ai": bool(man.get("pakai_ai"))}
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

#!/usr/bin/env python3
"""Bima — pencari aset Yofamo. Untuk setiap kalimat naskah menyiapkan 1–3 shot vertikal 1080x1920
(ganti visual tiap ±3 detik supaya tidak kaku) dari tiga jenis sumber gratis:

    footage  YouTube Creative Commons (CC BY) → NASA → Wikimedia Commons → Pexels/Pixabay (opsional)
    ai       gambar FLUX gratis (Cloudflare Workers AI) yang digerakkan halus (Ken Burns)
    grafis   kartu angka / teks kinetik yang dirender sendiri

Alur (dari root project):
    python agents/aset/cari_aset.py cari  <slug>             # cari kandidat + lembar kontak aset/lembar/NN.jpg
    python agents/aset/cari_aset.py unduh <slug>             # unduh pilihan di aset/pilihan.json → klip final
    python agents/aset/cari_aset.py unduh <slug> --otomatis  # pilih sendiri kandidat teratas (tanpa Claude)
    python agents/aset/cari_aset.py semua <slug>             # cari + unduh --otomatis sekaligus
    python agents/aset/cari_aset.py unduh <slug> --ulang 3   # buat ulang kalimat ke-3 saja
    tambahkan --uji untuk tes tanpa internet (kandidat & klip palsu, status tidak diubah)

Rencana per kalimat ditulis Bima (Claude) di aset/rencana.json:
    {"rencana": [{"i": 0, "jenis": "footage", "kata": ["robot hand touch", "robotic hand"],
                  "prompt_ai": "macro photo of a robotic hand ...", "grafis": {"gaya": "teks", "teks": "..."}}]}
Pilihan setelah melihat lembar kontak, di aset/pilihan.json (nomor sesuai lembar, mulai 1):
    {"pilihan": [{"i": 0, "pakai": [3, 1]}, {"i": 4, "pakai": ["ai"]}, {"i": 6, "pakai": ["grafis"]}]}

Hasil: aset/NN-a.mp4, NN-b.mp4 …, aset/manifest.json (timeline per shot), KREDIT.txt, kredit_deskripsi.txt.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[1]))
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("yt_dlp")
import gerak  # noqa: E402
import sumber  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = ROOT / "videos"
CACHE = ROOT / "cache" / "aset"
MILIK = ROOT / "milik-saya"      # rekaman Zona sendiri: prioritas tertinggi
VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".m4v"}
MAX_FOOTAGE_BERUNTUN = 2         # setelah 2 shot footage berturut-turut, wajib selingan AI/animasi
FIXTURE = Path(__file__).with_name("contoh_respon.json")
SHOT_MAX = 3.0          # bible: ganti visual tiap 1,5–3 detik
MAX_BYTES = 300 * 1024 * 1024
WPS = 2.6
UJI = False


def log(msg: str) -> None:
    print(f"[bima] {msg}", flush=True)


def load_env() -> None:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def write_json(p: Path, data) -> None:
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pabrik(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), *args], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")


def status_of(slug: str) -> str | None:
    try:
        return next((r["status"] for r in json.loads(pabrik("list", "--json").stdout) if r["slug"] == slug), None)
    except ValueError:
        return None


# ------------------------------------------------------------------ naskah, timing, rencana
def load_video(slug: str) -> tuple[Path, list[dict], list[tuple[float, float]], float]:
    folder = VIDEOS / slug
    script = read_json(folder / "script.json", None)
    if not script:
        sys.exit(f"[bima] videos/{slug}/script.json belum ada.")
    narasi = [n for n in script.get("narasi", []) if str(n.get("kalimat", "")).strip()]
    if not narasi:
        sys.exit("[bima] naskah kosong")
    words = read_json(folder / "words.json", {})
    by_i = {k["i"]: (k["mulai"], k["selesai"]) for k in words.get("kalimat", []) if "i" in k}
    starts, t = [], 0.0
    for i, n in enumerate(narasi):                   # tanpa words.json: perkiraan dari jumlah kata
        s, e = by_i.get(i, (t, t + len(n["kalimat"].split()) / WPS))
        starts.append((s, e))
        t = e + 0.2
    total = float(words.get("durasi") or starts[-1][1] + 0.3)
    # visual menutup celah antarkalimat: kalimat i tampil sampai kalimat i+1 mulai
    spans = []
    for i, (s, _) in enumerate(starts):
        a = 0.0 if i == 0 else s
        b = starts[i + 1][0] if i + 1 < len(starts) else total
        spans.append((round(a, 3), round(max(b, a + 0.8), 3)))
    return folder, narasi, spans, total


def load_plan(folder: Path, narasi: list[dict]) -> list[dict]:
    raw = read_json(folder / "aset" / "rencana.json", {}).get("rencana") or [
        {"i": q.get("i"), "jenis": "footage", "kata": q.get("kata", [])} for q in read_json(folder / "aset" / "kueri.json", {}).get("kueri", [])]
    by_i = {}
    for r in raw:
        try:
            by_i[int(r["i"])] = r
        except (KeyError, TypeError, ValueError):
            pass
    plan = []
    for i, n in enumerate(narasi):
        r = by_i.get(i, {})
        jenis = r.get("jenis") if r.get("jenis") in ("footage", "ai", "grafis") else "footage"
        kata = [str(k).strip() for k in r.get("kata", []) if str(k).strip()][:4] or [n.get("visual") or n["kalimat"]]
        plan.append({"i": i, "jenis": jenis, "kata": kata, "prompt_ai": str(r.get("prompt_ai", "")).strip(),
                     "grafis": r.get("grafis") if isinstance(r.get("grafis"), dict) else {"gaya": "teks", "teks": n["kalimat"]},
                     "inggris": bool(r)})
    return plan


def shots_for(span: tuple[float, float], jenis: str) -> int:
    return 1 if jenis == "grafis" else max(1, min(3, math.ceil((span[1] - span[0]) / SHOT_MAX)))


# ------------------------------------------------------------------ cari kandidat
def search_all(query: str, english: bool) -> list[dict]:
    """Ambil dari semua sumber yang tersedia, lalu selang-seling (2 teratas tiap sumber dulu)."""
    if UJI:
        fx = read_json(FIXTURE, {})
        per = {"youtube": [sumber.kandidat(**c) for c in fx.get("youtube", [])],
               "nasa": [sumber.kandidat(**c) for c in fx.get("nasa", [])],
               "wikimedia": [sumber.kandidat(**c) for c in fx.get("wikimedia", [])],
               "pexels": [c for v in fx.get("pexels", {}).get("videos", []) if (c := sumber.from_pexels(v))]}
    else:
        per = {}
        yt, pex, pix = os.environ.get("YOUTUBE_API_KEY", ""), os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
        jobs = [("youtube", lambda: sumber.youtube_cc(query, yt) if yt and english else []),
                ("nasa", lambda: sumber.nasa(query) if english else []),
                ("wikimedia", lambda: sumber.wikimedia(query) if english else []),
                ("pexels", lambda: sumber.pexels(query, pex) if pex else []),
                ("pixabay", lambda: sumber.pixabay(query, pix) if pix else [])]
        for name, fn in jobs:
            try:
                per[name] = fn()
            except urllib.error.HTTPError as err:
                log(f"  {name}: ditolak ({err.code}), dilewati")
                per[name] = []
            except (urllib.error.URLError, TimeoutError, ValueError) as err:
                log(f"  {name}: tidak bisa dihubungi ({err}), dilewati")
                per[name] = []
    out, rnd = [], 0
    while any(per.values()) and len(out) < 24:
        for name in ("youtube", "nasa", "wikimedia", "pexels", "pixabay"):
            lst = per.get(name) or []
            take = 2 if rnd == 0 else 1
            out += lst[:take]
            per[name] = lst[take:]
        rnd += 1
    return out


def tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) >= 3}


def own_matches(texts: list[str]) -> list[dict]:
    """Cocokkan nama file di milik-saya/ dengan kata kunci & kolom visual (nama file sebaiknya deskriptif)."""
    if not MILIK.is_dir():
        return []
    want = set().union(*(tokens(t) for t in texts)) if texts else set()
    scored = []
    for f in MILIK.rglob("*"):
        if f.suffix.lower() in VIDEO_EXT and f.is_file():
            score = len(tokens(f.stem.replace("-", " ").replace("_", " ")) & want)
            if score:
                scored.append((score, f))
    out = []
    for score, f in sorted(scored, key=lambda x: -x[0])[:4]:
        out.append(sumber.kandidat(sumber="milik", id=f.stem[:60], judul=f.name, pembuat="Zona", gambar=f"file:{f}",
                                   durasi=gerak.duration(f), lisensi="milik Zona", unduh=str(f), url_halaman=""))
    return out


def fetch_thumb(url: str, dest: Path, label: str) -> bool:
    if url.startswith("file:"):
        try:
            gerak.ff("-ss", "1", "-i", url[5:], "-frames:v", "1", "-vf", "scale=480:-2", str(dest))
            return True
        except RuntimeError:
            return False
    if UJI:
        gerak.placeholder(dest, label, "0x2A4A6B", "480x270" if "yt" in label or "nasa" in label else "270x480")
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": sumber.UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            dest.write_bytes(r.read(5_000_000))
        return True
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        return False


def cmd_cari(slug: str) -> None:
    folder, narasi, spans, total = load_video(slug)
    plan = load_plan(folder, narasi)
    aset = folder / "aset"
    (aset / "lembar").mkdir(parents=True, exist_ok=True)
    log(f"{len(narasi)} kalimat, durasi {total:.1f} dtk. Rencana: {'aset/rencana.json' if plan[0]['inggris'] else 'kolom visual naskah'}")
    result = []
    for p, span in zip(plan, spans):
        i, n_shot = p["i"], shots_for(span, p["jenis"])
        entry = {"i": i, "kalimat": narasi[i]["kalimat"], "jenis": p["jenis"], "mulai": span[0], "selesai": span[1],
                 "shot": n_shot, "kandidat": [], "lembar": None}
        if p["jenis"] == "footage":
            seen, cands = set(), []
            for c in own_matches(p["kata"] + [narasi[i].get("visual", ""), narasi[i]["kalimat"]]):
                seen.add((c["sumber"], c["id"]))
                cands.append({**c, "kueri": "milik-saya"})
            for q in p["kata"]:
                for c in search_all(q, p["inggris"]):
                    if (c["sumber"], c["id"]) not in seen:
                        seen.add((c["sumber"], c["id"]))
                        cands.append({**c, "kueri": q})
                if len(cands) >= 8:
                    break
            cands = cands[:8]
            tmp = aset / "lembar" / f"_{i + 1:02}"
            tmp.mkdir(exist_ok=True)
            thumbs = []
            for k, c in enumerate(cands):
                t = tmp / f"{k + 1}.jpg"
                if c["gambar"] and fetch_thumb(c["gambar"], t, f"{c['sumber']} {k + 1}"):
                    thumbs.append(t)
                else:
                    gerak.placeholder(t, "tanpa gambar", "0x333333", "320x320")
                    thumbs.append(t)
            if thumbs:
                sheet = aset / "lembar" / f"{i + 1:02}.jpg"
                gerak.sheet(thumbs, sheet)
                entry["lembar"] = str(sheet.relative_to(folder)).replace("\\", "/")
            shutil.rmtree(tmp, ignore_errors=True)
            entry["kandidat"] = cands
            src = ", ".join(sorted({c["sumber"] for c in cands})) or "-"
            log(f"{i + 1:02}. {len(cands)} kandidat ({src}), butuh {n_shot} shot")
        else:
            log(f"{i + 1:02}. {p['jenis']} ({n_shot} shot)")
        result.append(entry)
    write_json(aset / "kandidat.json", {"slug": slug, "dibuat": datetime.now().isoformat(timespec="seconds"), "uji": UJI,
                                         "durasi": total, "kalimat": result})
    log("kandidat siap: aset/kandidat.json + aset/lembar/NN.jpg")


# ------------------------------------------------------------------ unduh + bentuk klip
def cache_path(name: str) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / re.sub(r"[^\w.\-]", "_", name)


def http_download(url: str, dest: Path) -> Path:
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    part = dest.with_suffix(".part")
    size = 0
    try:
        req = urllib.request.Request(url, headers={"User-Agent": sumber.UA})
        with urllib.request.urlopen(req, timeout=90) as r, part.open("wb") as f:
            while chunk := r.read(1 << 16):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("file lebih dari 300 MB")
                f.write(chunk)
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    return dest


def yt_segment(c: dict, need: float, used: list[tuple[float, float]]) -> tuple[Path, float]:
    """Unduh potongan video YouTube CC. Titik awal: bagian 'paling sering diputar ulang' (heatmap) bila ada."""
    try:
        import yt_dlp
        from yt_dlp.utils import download_range_func
    except ImportError:
        raise RuntimeError("yt-dlp belum terpasang (python -m pip install -r requirements.txt)")
    opts = {"quiet": True, "no_warnings": True, "noplaylist": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(c["unduh"], download=False)
    if info.get("license") and "creative commons" not in str(info.get("license")).lower():
        raise RuntimeError("lisensi bukan Creative Commons")
    dur = float(info.get("duration") or c["durasi"] or 60)
    peaks = sorted(info.get("heatmap") or [], key=lambda h: h.get("value", 0), reverse=True)
    start = None
    for h in peaks:
        s = float(h.get("start_time", 0))
        if dur * 0.04 < s < dur - need - 1 and all(abs(s - u0) > need + 1 for u0, _ in used):
            start = s
            break
    if start is None:
        start = min(max(0.0, dur * (0.22 + 0.18 * len(used))), max(0.0, dur - need - 0.5))
    end = min(dur, start + need + 0.6)
    used.append((start, end))
    out = cache_path(f"yt-{c['id']}-{int(start * 10)}")
    have = list(CACHE.glob(out.name + ".*"))
    if have:
        return have[0], 0.0
    opts.update({"format": "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b[height<=1080]",
                 "outtmpl": str(out) + ".%(ext)s", "download_ranges": download_range_func(None, [(start, end)]),
                 "force_keyframes_at_cuts": False})
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([c["unduh"]])
    files = [f for f in CACHE.glob(out.name + ".*") if not f.name.endswith(".part")]
    if not files:
        raise RuntimeError("unduhan YouTube tidak menghasilkan file")
    return files[0], 0.0


def raw_footage(c: dict, need: float, seg: int, used: list) -> tuple[Path, float]:
    """Kembalikan (file mentah, detik mulai dipotong)."""
    if UJI and c["sumber"] != "milik":
        p = cache_path(f"uji-{c['sumber']}-{c['id']}.mp4")
        if not p.exists():
            size = "1280x720" if c["sumber"] in ("youtube", "nasa", "wikimedia") else "720x1280"
            gerak.placeholder(p, f"{c['sumber']} {c['id']}", "", size, max(need + 2, 8))
        return p, min(seg * (need + 0.5), max(0.0, gerak.duration(p) - need))
    if c["sumber"] == "youtube":
        return yt_segment(c, need, used)
    if c["sumber"] == "milik":
        p = Path(c["unduh"])
        d = gerak.duration(p)
        return p, max(0.0, min(0.5 + seg * (need + 0.5), d - need)) if d > need else 0.0
    url = sumber.nasa_file(c["id"]) if c["sumber"] == "nasa" else c["unduh"]
    ext = Path(urllib.parse.urlparse(url).path).suffix.lower() if c["sumber"] == "wikimedia" else ".mp4"
    p = http_download(url, cache_path(f"{c['sumber']}-{c['id']}{ext if ext in ('.webm', '.ogv', '.mp4', '.mpg', '.mpeg') else '.mp4'}"))
    d = gerak.duration(p)
    base = d * 0.15 if c["sumber"] in ("nasa", "wikimedia") else min(0.6, max(0.0, d - need))
    return p, max(0.0, min(base + seg * (need + 0.5), d - need)) if d > need else 0.0


def ai_image(prompt: str) -> Path:
    import hashlib
    p = cache_path(f"ai-{hashlib.sha1(prompt.encode()).hexdigest()[:12]}.jpg")
    if p.exists():
        return p
    if UJI:
        gerak.placeholder(p, "AI", "0x3B2E5A", "1024x1024")
        return p
    acc, tok = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not acc or not tok:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi di .env")
    p.write_bytes(sumber.flux_image(prompt, acc, tok))
    return p


# Sudut kamera per shot (a/b/c) supaya shot dalam satu kalimat tidak memakai gambar yang sama.
FRAMING = ["medium shot", "extreme close-up detail", "wide establishing shot, different angle"]


GAYA = ["dramatic lighting", "soft studio lighting", "moody neon lighting", "natural daylight"]


def ai_prompt(p: dict, kalimat: str, shot: int = 0, varian: int = 0) -> str:
    """varian > 0 dipakai saat QC menolak gambar sebelumnya: sudut & cahaya diganti supaya hasilnya beda."""
    base = p["prompt_ai"] or p["kata"][0]
    return (f"{base}. {FRAMING[(shot + varian) % len(FRAMING)]}, vertical cinematic shot, photorealistic, "
            f"{GAYA[varian % len(GAYA)]}, shallow depth of field, high detail. Clean image with absolutely no letters, "
            f"no words, no numbers, no signs, no screens with writing, no captions, no labels, no watermark, no logo")


def auto_pick(entry: dict, n: int, taken: set) -> list:
    """Kandidat teratas yang belum dipakai kalimat lain (supaya visual tidak berulang)."""
    free = [k + 1 for k, c in enumerate(entry["kandidat"]) if (c["sumber"], c["id"]) not in taken]
    return free[:n] or [k + 1 for k in range(min(n, len(entry["kandidat"])))]


def cmd_unduh(slug: str, otomatis: bool, ulang: set[int]) -> None:
    folder, narasi, spans, total = load_video(slug)
    plan = load_plan(folder, narasi)
    aset = folder / "aset"
    kand = read_json(aset / "kandidat.json", None)
    if not kand:
        sys.exit("[bima] aset/kandidat.json belum ada. Jalankan dulu: cari_aset.py cari <slug>")
    entries = {e["i"]: e for e in kand.get("kalimat", [])}
    picks = {}
    if not otomatis:
        for r in read_json(aset / "pilihan.json", {}).get("pilihan", []):
            try:
                picks[int(r["i"])] = list(r.get("pakai") or [])
            except (KeyError, TypeError, ValueError):
                pass
        if not picks:
            log("aset/pilihan.json kosong, memakai pilihan otomatis")
    old = {(k["i"], k["potong"]): k for k in read_json(aset / "manifest.json", {}).get("klip", [])}
    # shot yang ditolak QC Rara (atau Zona): kandidat footage itu tidak dipakai lagi, gambar AI dibuat ulang dengan variasi lain
    tolak = read_json(aset / "tolak.json", {}).get("tolak", [])
    ditolak = {(str(t.get("sumber")), str(t.get("id"))) for t in tolak if t.get("jenis") == "footage"}
    varian_ai = {}
    for t in tolak:
        if t.get("jenis") == "ai":
            varian_ai[(t.get("i"), t.get("potong"))] = varian_ai.get((t.get("i"), t.get("potong")), 0) + 1
    klip, kurang = [], []
    taken = {(k.get("sumber"), k.get("id")) for (ii, _), k in old.items() if ii + 1 not in ulang and k.get("jenis") == "footage"} | ditolak
    streak = 0                                   # jumlah shot footage berturut-turut
    for p, span in zip(plan, spans):
        i = p["i"]
        e = entries.get(i, {"kandidat": [], "jenis": p["jenis"]})
        n = shots_for(span, p["jenis"])
        bounds = [span[0] + (span[1] - span[0]) * k / n for k in range(n + 1)]
        choice = picks.get(i) or (["grafis"] if p["jenis"] == "grafis" else ["ai"] * n if p["jenis"] == "ai" else auto_pick(e, n, taken))
        bad = {k + 1 for k, c in enumerate(e["kandidat"]) if (str(c["sumber"]), str(c["id"])) in ditolak}
        choice = [c for c in choice if c not in bad] or (["ai"] * n if p["jenis"] != "grafis" else ["grafis"])
        queue = [c for c in choice] + [k + 1 for k in range(len(e["kandidat"])) if k + 1 not in choice and k + 1 not in bad]
        used_segments: dict[str, list] = {}
        for s in range(n):
            letter = "abc"[s]
            name = f"{i + 1:02}-{letter}.mp4"
            out = aset / name
            dur = round(bounds[s + 1] - bounds[s], 3)
            keep = old.get((i, s))
            if (i + 1) not in ulang and keep and keep.get("file") == name and out.exists() and abs(keep["durasi"] - dur) < 0.05 and keep.get("uji") == UJI:
                klip.append(keep)
                streak = streak + 1 if keep.get("jenis") == "footage" else 0
                continue
            meta = None
            want = choice[s] if s < len(choice) else (choice[s % len(choice)] if choice else "ai")
            if want not in ("ai", "grafis") and streak >= MAX_FOOTAGE_BERUNTUN and i > 0:
                want = "ai"                      # selingan supaya ritme tidak monoton
            tries = [want] + [q for q in queue if q != want] + ["ai"]
            for t in tries:
                try:
                    if t == "grafis":
                        gerak.grafis(p["grafis"], out, dur)
                        meta = {"jenis": "grafis", "sumber": "grafis", "judul": p["grafis"].get("teks") or p["grafis"].get("label", ""), "lisensi": "buatan sendiri"}
                    elif t == "ai":
                        prompt = ai_prompt(p, narasi[i]["kalimat"], s, varian_ai.get((i, s), 0))
                        img = ai_image(prompt)
                        gerak.kenburns(img, out, dur, seed=i * 7 + s)
                        meta = {"jenis": "ai", "sumber": "cloudflare-flux", "judul": prompt, "lisensi": "gambar AI (konten sintetis)"}
                    else:
                        c = e["kandidat"][int(t) - 1]
                        segs = used_segments.setdefault(f"{c['sumber']}-{c['id']}", [])
                        raw, start = raw_footage(c, dur, len(segs) if c["sumber"] != "youtube" else 0, segs)
                        if c["sumber"] != "youtube":
                            segs.append((start, start + dur))
                        have = gerak.duration(raw) - start
                        if have < dur - 0.05:
                            tmp = out.with_name(f"_{name}")
                            gerak.normalize(raw, tmp, start, have)
                            gerak.loop_to(tmp, out, dur)
                            tmp.unlink(missing_ok=True)
                        else:
                            gerak.normalize(raw, out, start, dur)
                        gelap, beku = gerak.cek_shot(out)
                        if gelap > 0.35 or beku > 0.7:
                            taken.add((c["sumber"], c["id"]))
                            raise RuntimeError(f"klip {'gelap' if gelap > 0.35 else 'diam/beku'} ({max(gelap, beku):.0%}), cari yang lain")
                        meta = {"jenis": "footage", **{k: c[k] for k in ("sumber", "id", "judul", "url_halaman", "pembuat", "lisensi", "kueri")},
                                "sumber_mulai": round(start, 2), "kandidat_no": int(t)}
                        taken.add((c["sumber"], c["id"]))
                    break
                except (RuntimeError, ValueError, OSError, IndexError, urllib.error.URLError, TimeoutError) as err:
                    log(f"{i + 1:02}{letter}: {t} gagal ({str(err)[:120]}), coba berikutnya")
                except Exception as err:  # yt-dlp melempar jenis error sendiri
                    log(f"{i + 1:02}{letter}: {t} gagal ({type(err).__name__}: {str(err)[:120]}), coba berikutnya")
            if not meta:
                kurang.append(i + 1)
                continue
            rec = {"i": i, "potong": s, "file": name, "mulai": round(bounds[s], 3), "selesai": round(bounds[s + 1], 3),
                   "durasi": dur, "kalimat": narasi[i]["kalimat"], "uji": UJI, **meta}
            klip.append(rec)
            streak = streak + 1 if rec["jenis"] == "footage" else 0
            log(f"{i + 1:02}{letter}. {rec['jenis']:<8} {rec['sumber']:<15} {dur:.1f} dtk")

    klip.sort(key=lambda k: (k["i"], k["potong"]))
    pakai_ai = any(k["jenis"] == "ai" for k in klip)
    write_json(aset / "manifest.json", {"slug": slug, "dibuat": datetime.now().isoformat(timespec="seconds"), "uji": UJI,
                                         "durasi": total, "resolusi": "1080x1920", "fps": gerak.FPS, "pakai_ai": pakai_ai,
                                         "klip": klip, "kurang": sorted(set(kurang))})
    write_credits(aset, klip)
    counts = {j: sum(1 for k in klip if k["jenis"] == j) for j in ("footage", "ai", "grafis")}
    log(f"{len(klip)} shot: {counts['footage']} footage, {counts['ai']} AI, {counts['grafis']} grafis. Rata-rata {total / max(1, len(klip)):.1f} dtk per shot.")
    if pakai_ai:
        log("Ada gambar AI realistis: saat upload, centang 'konten diubah/sintetis' di YouTube Studio.")
    if kurang:
        log(f"Kurang: kalimat {sorted(set(kurang))}. Perbaiki aset/rencana.json lalu jalankan lagi.")
        return
    if UJI:
        log("selesai (uji, status tidak diubah)")
        return
    pabrik("set", slug, "aset", "--note", "klip disiapkan Bima")
    log(f"selesai: videos/{slug}/aset/ (status → aset)")


def write_credits(aset: Path, klip: list[dict]) -> None:
    lines, desc, seen = ["Kredit aset video:", ""], [], set()
    for k in klip:
        lines.append(f"{k['file']}: {k['jenis']} · {k.get('sumber')} · {k.get('pembuat', '')} · {k.get('lisensi', '')} · {k.get('url_halaman', '')}")
        key = (k.get("sumber"), k.get("id"))
        if k["jenis"] != "footage" or key in seen:
            continue
        seen.add(key)
        if k["sumber"] == "youtube":
            desc.append(f"🎬 \"{k['judul']}\" oleh {k['pembuat']} (CC BY) {k['url_halaman']}")
        elif k["sumber"] == "wikimedia":
            desc.append(f"🎬 \"{k['judul']}\" oleh {k['pembuat']} ({k['lisensi']}) {k['url_halaman']}")
        elif k["sumber"] == "nasa":
            desc.append("🎬 Footage: NASA")
    if any(k.get("sumber") in ("pexels", "pixabay") for k in klip):
        desc.append("🎬 Stok video: Pexels / Pixabay")
    (aset / "KREDIT.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (aset / "kredit_deskripsi.txt").write_text(("Kredit:\n" + "\n".join(desc) + "\n") if desc else "", encoding="utf-8")


# ------------------------------------------------------------------ utama
def main() -> None:
    global UJI
    ap = argparse.ArgumentParser(description="Bima: aset video per kalimat (footage CC/NASA/stok, gambar AI, grafis)")
    ap.add_argument("perintah", choices=["cari", "unduh", "semua"])
    ap.add_argument("slug")
    ap.add_argument("--otomatis", action="store_true", help="unduh: pilih kandidat teratas tanpa pilihan.json")
    ap.add_argument("--ulang", type=int, action="append", default=[], help="unduh: buat ulang kalimat nomor ini (mulai 1)")
    ap.add_argument("--uji", action="store_true", help="tanpa internet: kandidat & klip palsu, status tidak diubah")
    a = ap.parse_args()
    UJI = a.uji
    if not re.fullmatch(r"[a-z0-9-]{3,80}", a.slug):
        sys.exit("[bima] slug tidak valid")
    gerak.need_ffmpeg()
    if not UJI:
        st = status_of(a.slug)
        if st not in ("suara", "aset"):
            sys.exit(f"[bima] status video '{st}'. Aset disiapkan setelah Dara membuat suara (status suara).")
        load_env()
        if not any(os.environ.get(k) for k in ("PEXELS_API_KEY", "PIXABAY_API_KEY", "YOUTUBE_API_KEY")):
            sys.exit("[bima] Belum ada API key sumber klip di .env (YOUTUBE_API_KEY / PEXELS_API_KEY).")
    if a.perintah in ("cari", "semua"):
        cmd_cari(a.slug)
    if a.perintah in ("unduh", "semua"):
        cmd_unduh(a.slug, a.otomatis or a.perintah == "semua", set(a.ulang))


if __name__ == "__main__":
    main()

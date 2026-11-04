#!/usr/bin/env python3
"""Tio (gaya dokumenter modern) — merender tiap adegan video panjang 16:9 (1920x1080, 30 fps).

    python agents/panjang/dokumenter.py <slug>                # semua adegan yang belum jadi → panjang/<slug>/adegan/NN.mp4
    python agents/panjang/dokumenter.py <slug> --ulang 3 7    # render ulang adegan tertentu
    python agents/panjang/dokumenter.py <slug> --pratinjau    # foto beberapa frame tiap adegan motion graphic (cepat)

Gaya (referensi Video 1 Zona, bible/gaya-dokumenter.json): kertas abu-abu terang, tinta hitam, serif elegan, benda ASLI
berlatar transparan melayang dengan bayangan, foto hitam-putih, butiran film tipis + garis VHS halus.
  • footage   → ffmpeg (cepat): shot footage asli tanpa teks (Bima 16:9), gerak geser pelan, warna sedikit diredam,
                butiran film & vignette tipis, subtitle KECIL di tengah bawah (maks 2 baris).
  • motion graphic (kata, angka, cara_kerja, banding, garis_waktu, objek, hp, tv, judul_bab, pembuka, penutup)
                → HyperFrames (agents/panjang/dokumenter.html), tanpa subtitle (tulisan besar sudah ada).
Media per adegan dari footage_panjang.py: panjang/<slug>/footage/manifest.json (shot), media/NN-*.png (objek asli).
"""
from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
import animasi  # noqa: E402  (render HyperFrames, tunggu_shorts)

TEMPLATE = Path(__file__).with_name("dokumenter.html")
FONTS = ROOT / "fonts"
GAYA = ROOT / "bible" / "gaya-dokumenter.json"
BERSAMA = ROOT / "cache" / "dokumenter"
FPS = 30
MOGRAPH = {"kata", "angka", "cara_kerja", "banding", "garis_waktu", "objek", "hp", "tv", "judul_bab", "pembuka", "footage_teks", "penutup"}


def log(m: str) -> None:
    print(f"[tio] {m}", flush=True)


def rj(p: Path, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if d is None else d


def gaya() -> dict:
    g = {"warna": {"kertas": "#E7E6E2", "tinta": "#151515", "abu": "#8A8986", "aksen": "#2D6BFF"},
         "subtitle": {"tampil": True, "ukuran": 40, "maks_huruf": 44, "jarak_bawah": 64},
         "footage": {"saturasi": 0.88, "kontras": 1.04, "butiran": 9, "vignette": True}, "handle": "@yofamoo_technology"}
    for k, v in rj(GAYA).items():
        g[k] = {**g[k], **v} if isinstance(v, dict) and isinstance(g.get(k), dict) else v
    return g


def ff(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal: {r.stderr[-500:]}")


def durasi(f: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(f)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


# ------------------------------------------------------------------ tekstur bersama (dibuat sekali)
def tekstur() -> dict:
    """Kertas abu-abu bertekstur + 4 ubin butiran film (PNG). Dibuat dengan kode → bebas hak cipta."""
    from PIL import Image, ImageFilter
    import numpy as np
    BERSAMA.mkdir(parents=True, exist_ok=True)
    kertas = BERSAMA / "kertas.jpg"
    if not kertas.exists():
        rng = np.random.default_rng(7)
        h, w = 1080, 1920
        dasar = np.full((h, w), 231.0)
        serat = Image.fromarray((rng.normal(128, 40, (h // 4, w // 4))).clip(0, 255).astype("uint8")).resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(2))
        halus = rng.normal(0, 3.2, (h, w))
        img = dasar + (np.asarray(serat, float) - 128) * 0.05 + halus
        rgb = np.stack([img, img - 1.0, img - 4.5], -1).clip(0, 255).astype("uint8")
        Image.fromarray(rgb).save(kertas, quality=90)
    grain = []
    for n in range(4):
        f = BERSAMA / f"grain-{n}.png"
        if not f.exists():
            rng = np.random.default_rng(100 + n)
            g = rng.normal(128, 46, (512, 512)).clip(0, 255).astype("uint8")
            Image.fromarray(g, "L").convert("RGB").save(f)
        grain.append(f)
    return {"kertas": kertas, "grain": grain}


# ------------------------------------------------------------------ data adegan
def data_adegan(i: int, a: dict, waktu: dict, g: dict, slug: str) -> dict:
    w = waktu.get(str(i)) or {}
    dur = float(w.get("durasi") or a.get("durasi") or 3.0)
    kata = [{"t": k["kata"], "a": round(float(k["mulai"]), 3), "b": round(float(k["selesai"]), 3)} for k in w.get("kata", [])]
    kal = [{"a": round(float(k["mulai"]), 3), "b": round(float(k["selesai"]), 3)} for k in w.get("kalimat", [])]
    j = a.get("jenis")
    isi = {k: v for k, v in a.items() if k not in ("narasi", "jenis", "kata_kunci_visual", "objek_cari")}
    if j == "judul_bab":
        isi["nomor"] = a.get("nomor") or 1
    if j in ("pembuka", "footage_teks"):
        isi["teks"] = a.get("teks_layar") or a.get("teks") or ""
    if j == "penutup":
        isi["teks"] = a.get("teks_layar") or a.get("pertanyaan") or ""
    return {"jenis": j, "durasi": round(dur, 3), "fps": FPS, "kata": kata, "kalimat": kal, "isi": isi,
            "warna": {f"{k}": v for k, v in (g.get("warna") or {}).items()}, "handle": g.get("handle", "")}


def media_adegan(vdir: Path, i: int, a: dict, man: dict) -> dict:
    """File media (asli) untuk adegan i: video shot, objek transparan, foto banding, latar hitam-putih."""
    md = vdir / "media"
    shots = [vdir / "footage" / s["file"] for s in (man.get(str(i)) or []) if (vdir / "footage" / s["file"]).exists()]
    m: dict = {}
    if shots:
        m["video"] = shots[0]
    objek = sorted(md.glob(f"{i + 1:02}-objek*.png")) if md.is_dir() else []
    if objek:
        m["objek"] = objek
    foto = sorted(md.glob(f"{i + 1:02}-foto*.jpg")) if md.is_dir() else []
    if foto:
        m["foto"] = foto
    latar = md / f"{i + 1:02}-latar.jpg"
    if latar.exists():
        m["latar"] = latar
    return m


def tulis_proyek(pdir: Path, data: dict, media: dict, tx: dict, judul: str) -> Path:
    if pdir.exists():
        shutil.rmtree(pdir, ignore_errors=True)
    (pdir / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(animasi.GSAP, pdir / "assets" / "gsap.min.js")
    for f in ("InstrumentSerif-Regular.ttf", "InstrumentSerif-Italic.ttf", "Inter.ttf"):
        shutil.copy2(FONTS / f, pdir / "assets" / "fonts" / f)
    shutil.copy2(tx["kertas"], pdir / "assets" / "kertas.jpg")
    data["grain"] = []
    for n, f in enumerate(tx["grain"]):
        shutil.copy2(f, pdir / "assets" / f"grain-{n}.png")
        data["grain"].append(f"assets/grain-{n}.png")
    M: dict = {}
    if media.get("video"):
        ff("-i", str(media["video"]), "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
           "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30", str(pdir / "assets" / "video.mp4"))
        M["video"] = "assets/video.mp4"
    for k in ("objek", "foto"):
        if media.get(k):
            M[k] = []
            for n, f in enumerate(media[k]):
                nama = f"{k}-{n}{f.suffix}"
                shutil.copy2(f, pdir / "assets" / nama)
                M[k].append(f"assets/{nama}")
    if media.get("latar"):
        shutil.copy2(media["latar"], pdir / "assets" / "latar.jpg")
        M["latar"] = "assets/latar.jpg"
    data["media"] = M
    dur = max(1.0, round(round(data["durasi"] * FPS) / FPS, 3))
    html = (TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__DURASI__", f"{dur:.3f}").replace("__FPS__", str(FPS)).replace("__JUDUL__", re.sub(r"[<>&]", "", judul)[:80]))
    (pdir / "index.html").write_text(html, encoding="utf-8")
    return pdir / "index.html"


# ------------------------------------------------------------------ footage (ffmpeg)
def ass_waktu(t: float) -> str:
    cs = int(round(max(0.0, t) * 100))
    return f"{cs // 360000}:{cs % 360000 // 6000:02d}:{cs % 6000 // 100:02d}.{cs % 100:02d}"


def subtitle_ass(kata: list[dict], g: dict, out: Path) -> bool:
    """Subtitle kecil di tengah bawah: potongan 5–9 kata (pecah di tanda baca), maks 2 baris."""
    sg = g.get("subtitle") or {}
    if not sg.get("tampil", True) or not kata:
        return False
    maks = int(sg.get("maks_huruf", 44))
    potong, cur = [], []
    for k in kata:
        cur.append(k)
        teks = " ".join(x["kata"] for x in cur)
        if len(teks) >= maks * 1.6 or re.search(r"[.,!?;:]$", k["kata"]) and len(cur) >= 4:
            potong.append(cur)
            cur = []
    if cur:
        if potong and (len(cur) <= 2 or len(" ".join(x["kata"] for x in cur)) < 12) \
                and len(" ".join(x["kata"] for x in potong[-1] + cur)) <= maks * 2:
            potong[-1] += cur                          # jangan sisakan 1–2 kata sendirian ("jam")
        else:
            potong.append(cur)
    baris = []
    for n, grp in enumerate(potong):
        teks = " ".join(x["kata"] for x in grp)
        if len(teks) > maks:                          # bagi 2 baris seimbang
            kk, best = teks.split(), None
            for c in range(1, len(kk)):
                a, b = " ".join(kk[:c]), " ".join(kk[c:])
                if best is None or abs(len(a) - len(b)) < abs(len(best[0]) - len(best[1])):
                    best = (a, b)
            teks = best[0] + r"\N" + best[1] if best else teks
        a = float(grp[0]["mulai"])
        b = float(potong[n + 1][0]["mulai"]) if n + 1 < len(potong) and float(potong[n + 1][0]["mulai"]) - float(grp[-1]["selesai"]) < 0.5 else float(grp[-1]["selesai"]) + 0.25
        baris.append(f"Dialogue: 0,{ass_waktu(a)},{ass_waktu(b)},Sub,,0,0,0,,{teks}")
    ukuran, bawah = int(sg.get("ukuran", 40)), int(sg.get("jarak_bawah", 64))
    out.write_text("\n".join([
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1920", "PlayResY: 1080", "WrapStyle: 2", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Sub,Inter,{ukuran},&H00F4F2EE,&H00F4F2EE,&H66000000,&H66000000,0,0,0,0,100,100,0.5,0,3,9,0,2,300,300,{bawah},1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text", *baris, ""]), encoding="utf-8")
    return True


def render_footage(vdir: Path, i: int, a: dict, waktu: dict, man: dict, g: dict, out: Path) -> None:
    w = waktu.get(str(i)) or {}
    dur = float(w.get("durasi") or 4.0)
    shots = [vdir / "footage" / s["file"] for s in (man.get(str(i)) or []) if (vdir / "footage" / s["file"]).exists()]
    if not shots:
        raise RuntimeError(f"adegan {i + 1}: belum ada footage (jalankan footage_panjang.py)")
    n = len(shots)
    per = dur / n
    args, rantai = [], []
    rng = random.Random(i * 31 + 7)
    for k, s in enumerate(shots):
        args += ["-stream_loop", "-1", "-i", str(s)]
        arah = rng.choice([1, -1])
        x = f"(iw-ow)*{'t' if arah > 0 else f'({per:.3f}-t)'}/{per:.3f}"
        rantai.append(f"[{k}:v]trim=0:{per:.3f},setpts=PTS-STARTPTS,fps={FPS},scale=2016:1134:force_original_aspect_ratio=increase,"
                      f"crop=1920:1080:x='{x}':y='(ih-oh)/2',setsar=1[s{k}]")
    fg = g.get("footage") or {}
    rantai.append("".join(f"[s{k}]" for k in range(n)) + f"concat=n={n}:v=1:a=0[v0]")
    efek = f"eq=saturation={fg.get('saturasi', 0.88)}:contrast={fg.get('kontras', 1.04)},noise=alls={int(fg.get('butiran', 9))}:allf=t"
    if fg.get("vignette", True):
        efek += ",vignette=PI/5.5"
    ass = out.with_suffix(".ass")
    if subtitle_ass(w.get("kata", []), g, ass):
        efek += f",subtitles=filename='{esc(ass)}':fontsdir='{esc(FONTS)}'"
    rantai.append(f"[v0]{efek},format=yuv420p[v]")
    ff(*args, "-filter_complex", ";".join(rantai), "-map", "[v]", "-t", f"{dur:.3f}", "-r", str(FPS), "-an",
       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", str(out))
    ass.unlink(missing_ok=True)


def esc(p: Path | str) -> str:
    return str(Path(p).resolve()).replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


# ------------------------------------------------------------------ utama
def render_adegan(vdir: Path, i: int, a: dict, waktu: dict, man: dict, g: dict, tx: dict, judul: str, slug: str) -> Path:
    out = vdir / "adegan" / f"{i + 1:02}.mp4"
    out.parent.mkdir(exist_ok=True)
    if a.get("jenis") == "footage":
        render_footage(vdir, i, a, waktu, man, g, out)
        return out
    data = data_adegan(i, a, waktu, g, slug)
    pdir = vdir / "hf" / f"{i + 1:02}"
    tulis_proyek(pdir, data, media_adegan(vdir, i, a, man), tx, judul)
    animasi.render(pdir, out, FPS)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Tio: render adegan gaya dokumenter")
    ap.add_argument("slug")
    ap.add_argument("--ulang", nargs="*", type=int, default=[])
    ap.add_argument("--pratinjau", action="store_true")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = rj(vdir / "naskah.json")
    waktu = rj(vdir / "suara" / "waktu.json")
    man = rj(vdir / "footage" / "manifest.json")
    g, tx = gaya(), tekstur()
    adegan = naskah.get("adegan") or []
    if a.pratinjau:
        for i, ad in enumerate(adegan):
            if ad.get("jenis") == "footage":
                continue
            data = data_adegan(i, ad, waktu, g, a.slug)
            pdir = vdir / "hf" / f"{i + 1:02}"
            tulis_proyek(pdir, data, media_adegan(vdir, i, ad, man), tx, naskah.get("judul", ""))
            animasi.pratinjau(pdir, vdir / "pratinjau" / f"{i + 1:02}.jpg", [0.4, data["durasi"] * 0.5, max(0.5, data["durasi"] - 0.4)])
        log(f"pratinjau → panjang/{a.slug}/pratinjau/")
        return
    t0, n = time.time(), 0
    for i, ad in enumerate(adegan):
        out = vdir / "adegan" / f"{i + 1:02}.mp4"
        if out.exists() and (i + 1) not in a.ulang:
            continue
        animasi.tunggu_shorts(a.uji)
        t1 = time.time()
        render_adegan(vdir, i, ad, waktu, man, g, tx, naskah.get("judul", ""), a.slug)
        n += 1
        log(f"adegan {i + 1:02}/{len(adegan)} ({ad.get('jenis')}): {time.time() - t1:.0f} dtk")
    shutil.rmtree(vdir / "hf", ignore_errors=True)
    if not a.uji and n:
        st_panjang.set_status(a.slug, "animasi", f"{len(adegan)} adegan")
    log(f"selesai {n} adegan dalam {(time.time() - t0) / 60:.1f} menit")


if __name__ == "__main__":
    main()

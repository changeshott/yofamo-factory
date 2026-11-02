#!/usr/bin/env python3
"""Tio — animator tim video panjang. Mengubah tiap adegan naskah menjadi animasi kartun 80-an (HyperFrames: HTML + GSAP).

    python agents/panjang/animasi.py <slug>                 # render semua adegan yang belum jadi → panjang/<slug>/adegan/NN.mp4
    python agents/panjang/animasi.py <slug> --ulang 3 7     # render ulang adegan tertentu
    python agents/panjang/animasi.py <slug> --pratinjau     # hanya foto beberapa frame tiap adegan (cepat, tanpa render video)

Tiap adegan = proyek HyperFrames sendiri (agents/panjang/adegan.html + data adegan) supaya bisa dilanjutkan kalau terputus.
Gerak dikunci 12 fps ("on twos" khas kartun 80-an) lalu dijadikan 24 fps saat dirakit. Butuh Node 22+ & npm install.
"""
from __future__ import annotations

import argparse
import json
import os
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

TEMPLATE = Path(__file__).with_name("adegan.html")
HF_BIN = ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
GSAP = ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js"
FONTS = ROOT / "fonts"
GAYA = ROOT / "bible" / "gaya-animasi.json"
TRANSISI = ["iris", "bintang", "diagonal", "iris", "potong"]


def log(msg: str) -> None:
    print(f"[tio] {msg}", flush=True)


def rj(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if default is None else default


def gaya() -> dict:
    return rj(GAYA)


def data_adegan(i: int, a: dict, waktu: dict, vdir: Path, g: dict) -> dict:
    """Data untuk template: jenis, durasi, kata bertiming (sinkron mulut & kata kunci), kalimat, ilustrasi."""
    w = waktu.get(str(i)) or waktu.get(i) or {}
    durasi = float(w.get("durasi") or a.get("durasi") or 3.0)
    kata = [{"t": k["kata"], "a": round(float(k["mulai"]), 3), "b": round(float(k["selesai"]), 3)} for k in w.get("kata", [])]
    kalimat = [{"a": round(float(k["mulai"]), 3), "b": round(float(k["selesai"]), 3)} for k in w.get("kalimat", [])]
    # kata kunci: muncul tepat saat kata itu diucapkan
    kk = []
    for teks in (a.get("kata_kunci") or [])[:4]:
        t0 = next((k["a"] for k in kata if re.sub(r"\W", "", k["t"].lower()).startswith(re.sub(r"\W", "", str(teks).split()[0].lower())[:5])), None)
        if t0 is not None:
            kk.append({"teks": str(teks).upper()[:28], "a": t0})
    il = a.get("_ilustrasi")
    pal = g.get("sinar") or [["FF7A2F", "FFD23F"], ["2F6BFF", "19C6C6"], ["F2385A", "FF7A2F"], ["6B3FD4", "2F6BFF"], ["39D36B", "19C6C6"]]
    sinar = pal[i % len(pal)]
    return {
        "jenis": a.get("jenis", "host"), "durasi": round(durasi, 3), "fps": int(g.get("fps_render", 12)),
        "kata": kata, "kalimat": kalimat, "kata_kunci": kk, "ekspresi": a.get("ekspresi", "senang"),
        "teks_layar": a.get("teks_layar", ""), "label": a.get("label", ""), "judul": a.get("judul", ""), "nomor": a.get("nomor"),
        "ilustrasi": "assets/ilustrasi.jpg" if il else None, "gerak": a.get("gerak", ["zoom", "kiri", "kanan", "naik"][i % 4]),
        "host_kecil": bool(a.get("host_kecil")), "diagram": a.get("diagram") or {},
        "transisi": a.get("transisi") or (TRANSISI[i % len(TRANSISI)] if i else "iris"),
        "sinar": ["#" + sinar[0], "#" + sinar[1]], "warna": g.get("warna") or {},
    }


def tulis_proyek(pdir: Path, data: dict, ilustrasi: Path | None, judul: str) -> Path:
    (pdir / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    shutil.copy2(GSAP, pdir / "assets" / "gsap.min.js")
    for f in ("Poppins-Black.ttf", "Poppins-ExtraBold.ttf"):
        if (FONTS / f).exists():
            shutil.copy2(FONTS / f, pdir / "assets" / "fonts" / f)
    if ilustrasi and ilustrasi.exists():
        shutil.copy2(ilustrasi, pdir / "assets" / "ilustrasi.jpg")
    fps = data["fps"]
    durasi = max(1.0, round(round(data["durasi"] * fps) / fps, 3))
    html = (TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__DURASI__", f"{durasi:.3f}").replace("__FPS__", str(fps)).replace("__JUDUL__", re.sub(r"[<>&]", "", judul)[:80]))
    (pdir / "index.html").write_text(html, encoding="utf-8")
    return pdir / "index.html"


def render(pdir: Path, out: Path, fps: int) -> None:
    node = shutil.which("node")
    if not node or not HF_BIN.exists():
        raise RuntimeError("HyperFrames belum terpasang (Node.js 22+ lalu npm install di folder project)")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1", "HYPERFRAMES_SKIP_SKILLS": "1"}
    tmp = out.with_suffix(".tmp.mp4")
    r = subprocess.run([node, str(HF_BIN), "render", str(pdir), "-o", str(tmp), "--fps", str(fps), "--quality", "standard", "--quiet"],
                       cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not tmp.exists():
        pesan = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError("render gagal: " + " | ".join(pesan[-5:])[:500])
    tmp.replace(out)


def pratinjau(pdir: Path, out_jpg: Path, waktu: list[float]) -> None:
    """Foto beberapa frame (seek timeline GSAP) memakai Playwright Chromium — cepat untuk memeriksa tampilan."""
    from playwright.sync_api import sync_playwright  # type: ignore
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        salah: list[str] = []
        pg.on("pageerror", lambda e: salah.append(str(e)))
        pg.goto((pdir / "index.html").resolve().as_uri())
        try:
            pg.wait_for_function("!!(window.__timelines && window.__timelines.main)", timeout=20000)
        except Exception:
            raise RuntimeError("template gagal dibangun: " + " | ".join(salah)[:500])
        for n, t in enumerate(waktu):
            pg.evaluate(f"void window.__timelines.main.seek({t}, false)")
            pg.wait_for_timeout(120)
            pg.screenshot(path=str(out_jpg.with_name(f"{out_jpg.stem}-{n}.jpg")), type="jpeg", quality=80)
        b.close()


def tunggu_shorts(uji: bool) -> None:
    """Shorts didahulukan: selama produksi Shorts berjalan (produksi/produser.lock dipegang proses hidup), adegan berikutnya menunggu."""
    from kunci import Kunci
    k = Kunci(ROOT / "produksi" / ("produser-uji.lock" if uji else "produser.lock"), maks_jam=6)
    if not k.sibuk():
        return
    log("produksi Shorts sedang berjalan → render adegan berikutnya menunggu dulu")
    batas = time.time() + 4 * 3600
    while k.sibuk() and time.time() < batas:
        time.sleep(60)
    log("lanjut merender")


def main() -> None:
    ap = argparse.ArgumentParser(description="Tio: animasi adegan video panjang")
    ap.add_argument("slug")
    ap.add_argument("--ulang", type=int, nargs="*", default=[])
    ap.add_argument("--pratinjau", action="store_true")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = rj(vdir / "naskah.json")
    waktu = rj(vdir / "suara" / "waktu.json")
    if not naskah.get("adegan") or not waktu:
        sys.exit("[tio] naskah.json / suara/waktu.json belum ada")
    g = gaya()
    fps = int(g.get("fps_render", 12))
    adir = vdir / "adegan"
    adir.mkdir(exist_ok=True)
    il_dir = vdir / "ilustrasi"
    jadi = 0
    for i, ad in enumerate(naskah["adegan"]):
        out = adir / f"{i + 1:02}.mp4"
        il = il_dir / f"{i + 1:02}.jpg"
        ad = {**ad, "_ilustrasi": il.exists()}
        if ad.get("jenis") == "judul_bab":
            ad["nomor"] = sum(1 for x in naskah["adegan"][: i + 1] if x.get("jenis") == "judul_bab")
        data = data_adegan(i, ad, waktu, vdir, g)
        pdir = vdir / "hf" / f"{i + 1:02}"
        tulis_proyek(pdir, data, il if il.exists() else None, naskah.get("judul", a.slug))
        if a.pratinjau:
            d = data["durasi"]
            pratinjau(pdir, adir / f"pratinjau-{i + 1:02}.jpg", [min(d - 0.05, 0.25), d * 0.45, max(0, d - 0.3)])
            continue
        if out.exists() and (i + 1) not in a.ulang:
            continue
        tunggu_shorts(a.uji)
        log(f"adegan {i + 1}/{len(naskah['adegan'])} ({data['jenis']}, {data['durasi']:.1f} dtk)…")
        render(pdir, out, fps)
        jadi += 1
    if not a.pratinjau:
        st_panjang.set_status(a.slug, "animasi", f"{jadi} adegan dirender")
        log(f"selesai: {jadi} adegan baru dirender → panjang/{a.slug}/adegan/")


if __name__ == "__main__":
    main()

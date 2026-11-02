#!/usr/bin/env python3
"""Laras — ilustrator video panjang. Gambar kartun 80-an untuk tiap adegan ilustrasi & diagram 'bagian' (FLUX gratis, Cloudflare).

    python agents/panjang/ilustrasi.py <slug>               # semua adegan yang butuh gambar → panjang/<slug>/ilustrasi/NN.jpg
    python agents/panjang/ilustrasi.py <slug> --ulang 4 9   # buat ulang gambar adegan tertentu (sudut lain)
    python agents/panjang/ilustrasi.py <slug> --uji         # tanpa internet: gambar contoh

Prompt = gaya kartun 80-an (bible/gaya-animasi.json) + isi adegan dari naskah (bahasa Inggris, objek/aksi spesifik)
+ larangan (tanpa tulisan, logo, orang sungguhan). Kuota gratis ±170 gambar/hari; satu video ±10–25 gambar.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "aset"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402

GAYA = ROOT / "bible" / "gaya-animasi.json"
SUDUT = ["", "dynamic low angle view", "close-up detail view", "wide establishing view"]


def log(msg: str) -> None:
    print(f"[laras] {msg}", flush=True)


def load_env() -> None:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def butuh_gambar(ad: dict) -> bool:
    return ad.get("jenis") == "ilustrasi" or (ad.get("jenis") == "diagram" and (ad.get("diagram") or {}).get("tipe") == "bagian") \
        or (ad.get("jenis") == "thumbnail")


def prompt_untuk(ad: dict, g: dict, varian: int = 0) -> str:
    il = g.get("ilustrasi", {})
    isi = str(ad.get("gambar") or ad.get("prompt") or ad.get("visual") or "").strip()
    if ad.get("jenis") == "diagram":
        isi = f"{isi}. {il.get('objek', '')}"
    sudut = SUDUT[varian % len(SUDUT)]
    return ", ".join(x for x in [il.get("gaya", ""), isi, sudut, il.get("larangan", "")] if x)


def contoh(out: Path, teks: str, n: int) -> None:
    from PIL import Image, ImageDraw
    warna = ["#8FD8FF", "#FFD23F", "#FF7A2F", "#39D36B", "#F2385A", "#19C6C6"]
    im = Image.new("RGB", (1024, 1024), warna[n % len(warna)])
    d = ImageDraw.Draw(im)
    d.ellipse((220, 200, 800, 780), fill=warna[(n + 2) % len(warna)], outline="#14101F", width=16)
    d.rectangle((0, 820, 1024, 1024), fill=warna[(n + 4) % len(warna)], outline="#14101F", width=16)
    d.text((40, 40), teks[:60], fill="#14101F")
    im.save(out, quality=90)


def main() -> None:
    ap = argparse.ArgumentParser(description="Laras: ilustrasi kartun 80-an")
    ap.add_argument("slug")
    ap.add_argument("--ulang", type=int, nargs="*", default=[])
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    g = json.loads(GAYA.read_text(encoding="utf-8")) if GAYA.exists() else {}
    idir = vdir / "ilustrasi"
    idir.mkdir(exist_ok=True)
    load_env()
    acc, tok = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not a.uji and (not acc or not tok):
        sys.exit("[laras] CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi di .env")
    import sumber  # noqa: E402  (agents/aset/sumber.py: flux_image)
    catatan = json.loads((idir / "prompt.json").read_text(encoding="utf-8")) if (idir / "prompt.json").exists() else {}
    adegan = list(naskah["adegan"])
    if naskah.get("thumbnail", {}).get("prompt"):
        adegan.append({"jenis": "thumbnail", "prompt": naskah["thumbnail"]["prompt"], "_nama": "thumbnail"})
    dibuat = gagal = 0
    for i, ad in enumerate(adegan):
        if not butuh_gambar(ad):
            continue
        nama = ad.get("_nama") or f"{i + 1:02}"
        out = idir / f"{nama}.jpg"
        ulang = (i + 1) in a.ulang
        if out.exists() and not ulang:
            continue
        varian = catatan.get(nama, {}).get("varian", -1) + 1 if ulang else 0
        p = prompt_untuk(ad, g, varian)
        try:
            if a.uji:
                contoh(out, p, i)
            else:
                out.write_bytes(sumber.flux_image(p, acc, tok))
            catatan[nama] = {"prompt": p, "varian": varian}
            dibuat += 1
            log(f"{nama}: {str(ad.get('gambar') or ad.get('prompt') or '')[:70]}")
        except Exception as err:  # satu gambar gagal tidak menghentikan yang lain; animator memakai latar cadangan
            gagal += 1
            log(f"{nama}: gagal ({str(err)[:120]})")
    (idir / "prompt.json").write_text(json.dumps(catatan, ensure_ascii=False, indent=1), encoding="utf-8")
    st_panjang.set_status(a.slug, "ilustrasi", f"{dibuat} gambar baru, {gagal} gagal")
    log(f"selesai: {dibuat} gambar baru{f', {gagal} gagal' if gagal else ''} → panjang/{a.slug}/ilustrasi/")


if __name__ == "__main__":
    main()

"""Mesin gambar Ruang Animasi: FLUX.2 [klein] 4B di Cloudflare Workers AI (gratis 10.000 neuron/hari).

Kenapa klein-4b: bisa menerima GAMBAR ACUAN (sampai 4, input_image_0..3) → host Yofa & gaya lukisnya tetap sama di
semua adegan, dan murah (±140 neuron per gambar 1536x864 → ±70 gambar/hari gratis). Kalau kuota/model gagal, cadangan
FLUX.1 schnell (tanpa acuan). Juga: kunci latar pink (chroma) → PNG transparan untuk host & objek yang dianimasikan.
"""
from __future__ import annotations

import base64
import io
import json
import os
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "YofamoFactory/1.0"


class KuotaGambar(Exception):
    """Kuota gratis Cloudflare hari ini habis (reset 07:00 WIB)."""


def load_env() -> tuple[str, str]:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")


def kecilkan(data: bytes, maks: int = 500) -> bytes:
    """Gambar acuan wajib < 512x512."""
    from PIL import Image
    im = Image.open(io.BytesIO(data)).convert("RGB")
    im.thumbnail((maks, maks))
    out = io.BytesIO()
    im.save(out, "JPEG", quality=92)
    return out.getvalue()


def _multipart(fields: dict[str, str], files: dict[str, bytes]) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    parts = []
    for k, v in fields.items():
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode())
    for k, v in files.items():
        parts.append(f"--{b}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{k}.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + v + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={b}"


def _baca_hasil(raw: bytes, ctype: str) -> bytes:
    if ctype.startswith("image/"):
        return raw
    d = json.loads(raw.decode("utf-8", "replace"))
    img = (d.get("result") or {}).get("image") if isinstance(d.get("result"), dict) else d.get("image")
    if not img:
        raise ValueError(f"Cloudflare tidak mengirim gambar: {json.dumps(d.get('errors'))[:300]}")
    return base64.b64decode(img)


def flux2(prompt: str, lebar: int = 1536, tinggi: int = 864, acuan: list[bytes] | None = None, seed: int | None = None,
          model: str = "flux-2-klein-4b") -> bytes:
    acc, tok = load_env()
    if not acc or not tok:
        raise RuntimeError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi di .env")
    fields = {"prompt": prompt[:2400], "width": str(max(256, min(1920, lebar // 16 * 16))), "height": str(max(256, min(1920, tinggi // 16 * 16)))}
    if seed is not None:
        fields["seed"] = str(int(seed) % 2_000_000_000)
    files = {f"input_image_{i}": kecilkan(a) for i, a in enumerate((acuan or [])[:4])}
    body, ctype = _multipart(fields, files)
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/@cf/black-forest-labs/{model}"
    req = urllib.request.Request(url, data=body, headers={"Authorization": f"Bearer {tok}", "Content-Type": ctype, "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return _baca_hasil(r.read(), r.headers.get("Content-Type", ""))
    except urllib.error.HTTPError as err:
        teks = err.read().decode("utf-8", "replace")[:400]
        if err.code == 429 or "neuron" in teks.lower() or "quota" in teks.lower() or "limit" in teks.lower():
            raise KuotaGambar(f"kuota gambar Cloudflare habis ({err.code})") from err
        raise RuntimeError(f"Cloudflare {err.code}: {teks}") from err


def gambar(prompt: str, lebar: int = 1536, tinggi: int = 864, acuan: list[bytes] | None = None, seed: int | None = None) -> bytes:
    """klein-4b dengan acuan; kalau modelnya gagal (bukan kuota), cadangan FLUX.1 schnell tanpa acuan."""
    try:
        return flux2(prompt, lebar, tinggi, acuan, seed)
    except KuotaGambar:
        raise
    except Exception:  # model sedang bermasalah / format berubah → tetap dapat gambar
        import sys
        sys.path.insert(0, str(ROOT / "agents" / "aset"))
        import sumber  # noqa: E402
        acc, tok = load_env()
        return sumber.flux_image(prompt, acc, tok)


# ------------------------------------------------------------------ latar pink → transparan
def potong_latar(data: bytes, toleransi: int = 60, pangkas: bool = True, garis: int = 7) -> "Image.Image":  # noqa: F821
    """Latar polos (pink studio) dihapus mulai dari tepi gambar (flood fill), tepi diperhalus, lalu diberi garis tinta
    tebal di sekeliling (gaya stiker komik). pangkas=False menjaga ukuran kanvas (pose host harus sejajar satu sama lain)."""
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    im = Image.open(io.BytesIO(data)).convert("RGB")
    w, h = im.size
    tanda = (1, 254, 3)                                  # warna penanda yang hampir mustahil ada di gambar
    kerja = im.copy()
    for x, y in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1), (w // 2, 0), (0, h // 2), (w - 1, h // 2), (w // 4, 0), (3 * w // 4, 0)]:
        if kerja.getpixel((x, y)) != tanda:
            ImageDraw.floodfill(kerja, (x, y), tanda, thresh=toleransi)
    beda = ImageChops.difference(kerja, Image.new("RGB", (w, h), tanda)).convert("L")
    alpha = beda.point(lambda v: 255 if v > 6 else 0)
    alpha = alpha.filter(ImageFilter.MinFilter(3)).filter(ImageFilter.GaussianBlur(1.2))
    rgba = im.convert("RGBA")
    rgba.putalpha(alpha)
    if garis:
        # garis tinta: alpha dilebarkan → siluet gelap di belakang gambar
        tepi = alpha.point(lambda v: 255 if v > 90 else 0).filter(ImageFilter.MaxFilter(garis * 2 + 1)).filter(ImageFilter.GaussianBlur(0.8))
        dasar = Image.new("RGBA", (w, h), (18, 10, 31, 0))
        dasar.putalpha(tepi)
        rgba = Image.alpha_composite(dasar, rgba)
        alpha = rgba.getchannel("A")
    kotak = alpha.point(lambda v: 255 if v > 20 else 0).getbbox()
    if kotak and pangkas:
        pad = 12
        rgba = rgba.crop((max(0, kotak[0] - pad), max(0, kotak[1] - pad), min(w, kotak[2] + pad), min(h, kotak[3] + pad)))
    return rgba


def contoh_uji(path: Path, teks: str, n: int, lebar: int = 1536, tinggi: int = 864, pink: bool = False) -> None:
    """Gambar pengganti untuk mode uji (tanpa internet)."""
    from PIL import Image, ImageDraw
    warna = ["#FF2E88", "#19D3FF", "#FFE14D", "#6B3FD4", "#39D36B"]
    im = Image.new("RGB", (lebar, tinggi), "#FF5CA8" if pink else warna[n % len(warna)])
    d = ImageDraw.Draw(im)
    cx, cy, r = lebar // 2, tinggi // 2, min(lebar, tinggi) // 3
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=warna[(n + 2) % len(warna)], outline="#120A1F", width=14)
    for i in range(0, lebar, 28):
        for j in range(0, tinggi, 28):
            if (i // 28 + j // 28) % 3 == 0 and not pink:
                d.ellipse((i, j, i + 6, j + 6), fill="#120A1F")
    d.text((30, 30), teks[:70], fill="#120A1F")
    im.save(path, quality=92)

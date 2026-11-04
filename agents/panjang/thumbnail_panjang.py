#!/usr/bin/env python3
"""Mila (16:9) — thumbnail video panjang gaya dokumenter: 1280x720 < 2 MB.

    python agents/panjang/thumbnail_panjang.py <slug>

Komposisi (selaras gaya video & identitas channel): frame footage hitam-putih yang digelapkan di latar, OBJEK ASLI
berwarna (latar transparan, bayangan tebal di sekelilingnya) di kanan, 2–4 kata besar Poppins Black di kiri (putih, kata
terakhir kuning) dengan garis & bayangan tebal seperti hook Shorts. Objek: media/thumbnail-objek.png (footage_panjang.py),
cadangan objek adegan lain.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "thumbnail"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as st_panjang  # noqa: E402

W, H = 1280, 720
FONT = ROOT / "fonts" / "Poppins-Black.ttf"


def buat(vdir: Path, naskah: dict, out: Path) -> Path:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps
    import thumbnail as mila
    md = vdir / "media"
    # latar: frame footage (pembuka dulu) → hitam-putih, gelap, sedikit buram
    latar = None
    man = json.loads((vdir / "footage" / "manifest.json").read_text(encoding="utf-8")) if (vdir / "footage" / "manifest.json").exists() else {}
    for k in sorted(man, key=int):
        for s in man[k][:1]:
            src = vdir / "footage" / s["file"]
            if src.exists():
                import subprocess
                tmp = vdir / "export" / "_latar.jpg"
                tmp.parent.mkdir(exist_ok=True)
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(src), "-frames:v", "1", str(tmp)], capture_output=True)
                if tmp.exists():
                    latar = Image.open(tmp).convert("RGB")
                    tmp.unlink()
            break
        if latar:
            break
    if latar is None:
        latar = Image.new("RGB", (W, H), (40, 42, 46))
    latar = ImageOps.fit(latar, (W, H))
    latar = ImageEnhance.Brightness(ImageOps.grayscale(latar).convert("RGB").filter(ImageFilter.GaussianBlur(3))).enhance(0.42)
    kanvas = latar.convert("RGBA")
    gelap = Image.new("L", (W, H), 0)
    ImageDraw.Draw(gelap).rectangle((0, 0, W // 2, H), fill=120)
    kanvas = Image.composite(Image.new("RGBA", (W, H), (0, 0, 0, 255)), kanvas, gelap.filter(ImageFilter.GaussianBlur(160)))
    # objek asli berwarna di kanan
    objek = md / "thumbnail-objek.png"
    if not objek.exists():
        objek = next(iter(sorted(md.glob("*-objek*.png"))), None) if md.is_dir() else None
    if objek and objek.exists():
        ob = Image.open(objek).convert("RGBA")
        s = min(640 / ob.width, 600 / ob.height)
        ob = ob.resize((max(1, int(ob.width * s)), max(1, int(ob.height * s))), Image.LANCZOS)
        x, y = W - ob.width - 50, (H - ob.height) // 2 + 10
        lapis = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        lapis.paste(ob, (x, y), ob)
        hitam = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        hitam.putalpha(mila.bayangan(lapis.getchannel("A"), [(0, 26, .9), (20, 34, .7)], pelebaran=3))
        kanvas = Image.alpha_composite(Image.alpha_composite(kanvas, hitam), lapis)
    # 2–4 kata besar di kiri
    kata = str((naskah.get("thumbnail") or {}).get("teks") or naskah.get("judul", "")).upper().split()[:4]
    baris = [" ".join(kata[:2]), " ".join(kata[2:])] if len(kata) > 2 else [" ".join(kata)]
    baris = [b for b in baris if b]
    teks = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bentuk = Image.new("L", (W, H), 0)
    y = H // 2 - len(baris) * 70
    for n, b in enumerate(baris):
        px = 150
        while px > 60 and ImageFont.truetype(str(FONT), px).getlength(b) > 640:
            px -= 4
        f = ImageFont.truetype(str(FONT), px)
        warna = "#FFD23F" if n == len(baris) - 1 and len(baris) > 1 else "#FFFFFF"
        for img, isi in ((teks, warna), (bentuk, 255)):
            ImageDraw.Draw(img).text((60, y), b, font=f, fill=isi, stroke_width=max(3, px // 22), stroke_fill="#000000" if img is teks else 255)
        y += int(px * 1.02)
    hitam = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    hitam.putalpha(mila.bayangan(bentuk, [(0, 34, .75), (22, 50, .95), (17, 0, .5), (10, 0, .9)]))
    kanvas = Image.alpha_composite(Image.alpha_composite(kanvas, hitam), teks)
    rgb = kanvas.convert("RGB")
    for q in (92, 86, 78, 70):
        buf = io.BytesIO()
        rgb.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= 1_900_000:
            break
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(buf.getvalue())
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("pakai: thumbnail_panjang.py <slug>")
    v = st_panjang.folder(sys.argv[1])
    n = json.loads((v / "naskah.json").read_text(encoding="utf-8-sig"))
    print(buat(v, n, v / "export" / "thumbnail.jpg"))

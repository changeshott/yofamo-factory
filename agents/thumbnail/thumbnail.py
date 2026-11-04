#!/usr/bin/env python3
"""Mila — desainer thumbnail Shorts Yofamo.

Membuat thumbnail 1080x1920 yang SAMA gayanya dengan hook di video:
  latar = frame shot pembuka Bima (digelapkan + cahaya biru khas) →
  OBJEK yang dibahas (gambar AI, latar transparan, bayangan tebal di sekelilingnya) di belakang tulisan →
  hook bertingkat (font Poppins Black, warna putih/kuning/biru, garis hitam, bayangan TEBAL berlapis).
Objek yang sama dipakai Kai di detik-detik awal video: objek & tulisan hook muncul bersamaan (animasi selaras),
jadi frame pertama video = thumbnail.

    python agents/thumbnail/thumbnail.py <slug>            # objek (sekali, lalu dipakai ulang) + export/thumbnail.jpg
    python agents/thumbnail/thumbnail.py <slug> --ulang    # gambar objek BARU (mis. ditolak Rara), lalu thumbnail
    python agents/thumbnail/thumbnail.py <slug> --uji      # tanpa internet (objek contoh)

Hasil: videos/<slug>/thumbnail/objek.png (transparan), thumbnail/info.json, export/thumbnail.jpg (< 2 MB, siap diunggah Uli).
Objek diambil dari script.json → thumbnail_objek (Raka, bahasa Inggris); cadangan: kata kunci visual kalimat pembuka.
Gambar AI: tanpa orang, tangan, tulisan, logo (aturan channel). Gratis: FLUX.2 klein di Cloudflare (kuota bersama Laras).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "panjang"))
sys.path.insert(0, str(ROOT / "agents" / "editor"))
sys.path.insert(0, str(ROOT / "agents" / "aset"))
import gambar_ai  # noqa: E402
import gerak  # noqa: E402
import rakit  # noqa: E402  (hook_baris & gaya: sama persis dengan video)

VIDEOS = ROOT / "videos"
FONT = ROOT / "fonts" / "Poppins-Black.ttf"
W, H = 1080, 1920
MAKS_BYTE = 1_900_000            # batas YouTube 2 MB

# Bayangan hook (TEBAL, permintaan Zona) — sama dengan .hook-baris di agents/editor/hf_template.html
# (dy px, blur px CSS, alpha)
BAYANGAN_HOOK = [(0, 52, .75), (34, 80, .95), (26, 0, .5), (15, 0, .9)]
# Bayangan objek: lingkaran gelap di sekeliling + jatuh ke bawah (sama dengan filter drop-shadow di template)
BAYANGAN_OBJEK = [(0, 34, .9), (28, 46, .7)]


def log(m: str) -> None:
    print(f"[mila] {m}", flush=True)


def rj(p: Path, d=None):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if d is None else d


def gaya_thumb(st: dict) -> dict:
    t = st.get("thumbnail") or {}
    return {"lebar": int(t.get("objek_lebar_maks", 900)), "tinggi": int(t.get("objek_tinggi_maks", 840)),
            "naik": int(t.get("objek_naik", 290))}


def objek_teks(script: dict, idea: dict) -> str:
    t = script.get("thumbnail_objek")
    if isinstance(script.get("thumbnail"), dict):
        t = t or script["thumbnail"].get("objek")
    if not t:
        for n in script.get("narasi") or []:
            kk = n.get("kata_kunci_visual") or []
            if kk:
                t = kk[0]
                break
    if not t:
        kk = idea.get("kata_kunci_visual") or []
        t = kk[0] if kk else (idea.get("judul_kerja") or script.get("judul") or "futuristic technology device")
    return str(t).strip()[:120]


def prompt_objek(objek: str) -> str:
    return (f"High-detail photorealistic 3D product render of {objek}. One single object, the entire object fully visible, centered, "
            "with generous empty margin on every side, dramatic studio rim lighting, vivid saturated colors, crisp clean edges, "
            "isolated on a perfectly flat plain solid hot pink background (#FF5CA8), no floor, no shadow on the background, "
            "no people, no hands, no face, no text, no letters, no numbers, no logo, no watermark")


def nilai_potongan(rgba) -> tuple[bool, str]:
    """Apakah latar benar-benar terhapus & objeknya utuh?"""
    a = rgba.getchannel("A")
    w, h = a.size
    hist = a.point(lambda v: 255 if v > 20 else 0).histogram()
    isi = hist[255] / (w * h)
    kotak = a.point(lambda v: 255 if v > 20 else 0).getbbox()
    if not kotak or isi < 0.05:
        return False, f"objek terlalu kecil ({isi:.0%})"
    if isi > 0.82:
        return False, f"latar tidak terhapus ({isi:.0%} gambar)"
    sentuh = sum([kotak[0] <= 2, kotak[1] <= 2, kotak[2] >= w - 2, kotak[3] >= h - 2])
    if sentuh >= 3:
        return False, "objek terpotong tepi gambar"
    return True, f"objek {isi:.0%} gambar"


def buat_objek(vdir: Path, objek: str, uji: bool, ulang: bool) -> tuple[Path | None, dict]:
    tdir = vdir / "thumbnail"
    tdir.mkdir(exist_ok=True)
    png = tdir / "objek.png"
    lama = rj(tdir / "info.json")
    if png.exists() and not ulang and lama.get("objek") == objek:
        return png, lama
    putaran = int(lama.get("putaran_objek", 0)) + (1 if ulang else 0)
    dasar = int(hashlib.md5(f"{vdir.name}|{objek}".encode()).hexdigest()[:8], 16)
    info = {"objek": objek, "prompt": prompt_objek(objek), "putaran_objek": putaran, "riwayat": lama.get("riwayat", [])}
    for coba in range(3):
        seed = dasar + putaran * 101 + coba * 17
        try:
            if uji:
                mentah = tdir / "objek-mentah.jpg"
                gambar_ai.contoh_uji(mentah, objek, coba, 1024, 1024, pink=True)
                data = mentah.read_bytes()
            else:
                data = gambar_ai.gambar(info["prompt"], 1024, 1024, seed=seed)
                (tdir / "objek-mentah.jpg").write_bytes(data)
        except gambar_ai.KuotaGambar as err:
            log(f"{err}: thumbnail dibuat tanpa objek (coba lagi setelah 07:00 WIB dengan --ulang)")
            return None, {**info, "sumber": "tanpa", "alasan": str(err)}
        except Exception as err:  # noqa: BLE001 — tanpa key/internet: tetap ada thumbnail
            log(f"gambar objek gagal ({str(err)[:160]}): thumbnail dibuat tanpa objek")
            return None, {**info, "sumber": "tanpa", "alasan": str(err)[:200]}
        rgba = gambar_ai.potong_latar(data, toleransi=60, pangkas=False, garis=0)
        ok, ket = nilai_potongan(rgba)
        log(f"objek percobaan {coba + 1}: {ket}")
        if ok:
            kotak = rgba.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
            rgba.crop((max(0, kotak[0] - 6), max(0, kotak[1] - 6), min(rgba.width, kotak[2] + 6), min(rgba.height, kotak[3] + 6))).save(png)
            return png, {**info, "sumber": "uji" if uji else "ai", "seed": seed, "cek": ket}
    return None, {**info, "sumber": "tanpa", "alasan": "latar objek tidak bisa dipotong rapi"}


# ------------------------------------------------------------------ gambar
def latar(vdir: Path, st: dict):
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
    pal = st.get("palet") or {}
    gelap = "#" + str(pal.get("gelap", "071631")).lstrip("#")
    utama = tuple(int(str(pal.get("utama", "2D8CFF")).lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    bg = Image.new("RGB", (W, H), gelap)
    man = rj(vdir / "aset" / "manifest.json")
    klip = sorted(man.get("klip") or [], key=lambda k: (k.get("i", 0), k.get("potong", 0)))
    for k in klip[:3]:                                   # shot pembuka (hook) Bima; grafis dilewati
        if k.get("jenis") == "grafis":
            continue
        f = vdir / "aset" / k.get("file", "")
        if not f.exists():
            continue
        frame = vdir / "thumbnail" / "latar.jpg"
        t = max(0.0, (gerak.duration(f) or 1.0) * 0.4)
        if subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(f), "-frames:v", "1", "-q:v", "2", str(frame)],
                          capture_output=True).returncode == 0 and frame.exists():
            im = Image.open(frame).convert("RGB")
            s = max(W / im.width, H / im.height)
            im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
            im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
            bg = ImageEnhance.Brightness(im.filter(ImageFilter.GaussianBlur(11))).enhance(0.5)
            break
    # cahaya biru khas di belakang objek + vignette
    cahaya = Image.new("L", (W // 4, H // 4), 0)
    ImageDraw.Draw(cahaya).ellipse((W // 4 * 0.05, H // 4 * 0.18, W // 4 * 0.95, H // 4 * 0.62), fill=150)
    cahaya = cahaya.filter(ImageFilter.GaussianBlur(28)).resize((W, H), Image.LANCZOS)
    bg = Image.composite(Image.new("RGB", (W, H), utama), bg, cahaya.point(lambda v: int(v * .55)))
    vig = Image.new("L", (W // 4, H // 4), 0)
    ImageDraw.Draw(vig).ellipse((-W // 4 * 0.25, -H // 4 * 0.05, W // 4 * 1.25, H // 4 * 1.05), fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(40)).resize((W, H), Image.LANCZOS)
    return Image.composite(bg, Image.new("RGB", (W, H), (2, 6, 16)), vig).convert("RGBA")


def bayangan(alpha, lapis: list[tuple[int, int, float]], pelebaran: int = 0):
    """Bayangan berlapis dari bentuk (alpha): (geser y, blur CSS px, kekuatan)."""
    from PIL import Image, ImageChops, ImageFilter
    if pelebaran:
        alpha = alpha.filter(ImageFilter.MaxFilter(pelebaran * 2 + 1))
    hasil = Image.new("L", alpha.size, 0)
    for dy, blur, kuat in lapis:
        a = ImageChops.offset(alpha, 0, dy)
        if dy > 0:
            a.paste(0, (0, 0, a.width, dy))
        if blur:
            a = a.filter(ImageFilter.GaussianBlur(blur / 2))
        hasil = ImageChops.lighter(hasil, a.point(lambda v, k=kuat: int(v * k)))
    return hasil


def ukur_hook(baris: list[tuple[str, str, float]], st: dict):
    """Ukuran & posisi tiap baris — rumus sama dengan template HyperFrames (pas lebar 860 px, tinggi maks, rapat)."""
    from PIL import ImageFont
    hf, hk = st.get("hyperframes", {}), st.get("hook", {})
    maks = float(hf.get("hook_px_maks", 230))
    rapat = float(hk.get("jarak_baris", 0.8)) + 0.12
    out = []
    for t, warna, sk in baris:
        px = int(maks * sk)
        while px > 60 and ImageFont.truetype(str(FONT), px).getlength(t) > 860:
            px -= 2
        out.append([t, warna, px])
    muat = float(hk.get("tinggi_maks", 900)) / max(1, sum(b[2] * rapat for b in out))
    if muat < 1:
        for b in out:
            b[2] = int(b[2] * muat)
    tinggi = [b[2] * rapat for b in out]
    y = int(hf.get("hook_y", 1000)) - sum(tinggi) / 2
    pos = []
    for b, tg in zip(out, tinggi):
        pos.append((b[0], b[1], b[2], y))
        y += tg
    return pos


def gambar_hook(kanvas, baris: list[tuple[str, str, float]], st: dict):
    from PIL import Image, ImageDraw, ImageFont
    teks = Image.new("RGBA", kanvas.size, (0, 0, 0, 0))
    bentuk = Image.new("L", kanvas.size, 0)
    for t, warna, px, top in ukur_hook(baris, st):
        f = ImageFont.truetype(str(FONT), px)
        garis = max(2, round(px * .09 / 2))             # -webkit-text-stroke (9% px) dengan paint-order stroke → separuh terlihat
        xy = (W / 2, top + px * .95 / 2)
        ImageDraw.Draw(teks).text(xy, t, font=f, fill="#" + warna.lstrip("#"), anchor="mm", stroke_width=garis, stroke_fill="#000000")
        ImageDraw.Draw(bentuk).text(xy, t, font=f, fill=255, anchor="mm", stroke_width=garis, stroke_fill=255)
    hitam = Image.new("RGBA", kanvas.size, (0, 0, 0, 255))
    hitam.putalpha(bayangan(bentuk, BAYANGAN_HOOK))
    return Image.alpha_composite(Image.alpha_composite(kanvas, hitam), teks)


def letak_objek(ukuran: tuple[int, int], st: dict) -> tuple[int, int, int, int]:
    """(x, y, lebar, tinggi) objek — sama dengan Kai (komposisi.py → hook.objek)."""
    g = gaya_thumb(st)
    s = min(g["lebar"] / ukuran[0], g["tinggi"] / ukuran[1])
    w, h = round(ukuran[0] * s), round(ukuran[1] * s)
    cy = int(st.get("hyperframes", {}).get("hook_y", 1000)) - g["naik"]
    return (W - w) // 2, cy - h // 2, w, h


def susun(vdir: Path, script: dict, st: dict, png: Path | None) -> Path:
    from PIL import Image
    kanvas = latar(vdir, st)
    if png and png.exists():
        ob = Image.open(png).convert("RGBA")
        x, y, w, h = letak_objek(ob.size, st)
        ob = ob.resize((w, h), Image.LANCZOS)
        lapis = Image.new("RGBA", kanvas.size, (0, 0, 0, 0))
        lapis.paste(ob, (x, y), ob)
        hitam = Image.new("RGBA", kanvas.size, (0, 0, 0, 255))
        hitam.putalpha(bayangan(lapis.getchannel("A"), BAYANGAN_OBJEK, pelebaran=4))
        kanvas = Image.alpha_composite(Image.alpha_composite(kanvas, hitam), lapis)
    baris = rakit.hook_baris(str(script.get("hook_teks", "")), script, [str(x) for x in st.get("hook", {}).get("warna", [])])
    if baris:
        kanvas = gambar_hook(kanvas, baris, st)
    out = vdir / "export" / "thumbnail.jpg"
    out.parent.mkdir(exist_ok=True)
    rgb = kanvas.convert("RGB")
    for q in (92, 88, 84, 78, 70):
        buf = io.BytesIO()
        rgb.save(buf, "JPEG", quality=q, optimize=True, progressive=True)
        if buf.tell() <= MAKS_BYTE:
            break
    out.write_bytes(buf.getvalue())
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Mila: thumbnail Shorts (objek transparan di belakang hook)")
    ap.add_argument("slug")
    ap.add_argument("--ulang", action="store_true", help="gambar objek baru")
    ap.add_argument("--uji", action="store_true")
    ap.add_argument("--catatan", default="", help="alasan --ulang (dicatat)")
    a = ap.parse_args()
    vdir = VIDEOS / a.slug
    script = rj(vdir / "script.json")
    if not script:
        sys.exit(f"[mila] script.json belum ada untuk {a.slug}")
    st = rakit.style()
    objek = objek_teks(script, rj(vdir / "idea.json"))
    log(f"objek: {objek}")
    png, info = buat_objek(vdir, objek, a.uji, a.ulang)
    out = susun(vdir, script, st, png)
    info.update({"dibuat": datetime.now().isoformat(timespec="seconds"), "thumbnail": "export/thumbnail.jpg",
                 "ukuran_kb": round(out.stat().st_size / 1024), "ada_objek": bool(png)})
    if a.catatan:
        info.setdefault("riwayat", []).append({"waktu": info["dibuat"], "catatan": a.catatan})
    (vdir / "thumbnail" / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"selesai: videos/{a.slug}/export/thumbnail.jpg ({info['ukuran_kb']} KB){'' if png else ' — tanpa objek'}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Host Yofa — karakter orisinal Ruang Animasi, digambar AI dengan gaya lukis-komik (bible/gaya-animasi.json).

    python agents/panjang/maskot.py kandidat        # 4 desain host berbeda → bible/maskot/kandidat/k1..k4.jpg (Zona memilih)
    python agents/panjang/maskot.py pilih 2         # kandidat k2 jadi host utama → bible/maskot/utama.jpg/.png
    python agents/panjang/maskot.py pose            # 7 pose/ekspresi dari host utama (gambar acuan) → bible/maskot/pose/*.png
    python agents/panjang/maskot.py acuan-gaya      # 1 adegan contoh → bible/maskot/acuan-gaya.jpg (acuan gaya semua ilustrasi)
    python agents/panjang/maskot.py pakai 2         # pilih kandidat 2 lalu langsung buat pose + acuan gaya (tombol Studio)
    python agents/panjang/maskot.py otomatis        # kandidat → pilih 1 → pose → acuan-gaya (sekali jalan)
    ... --uji                                       # tanpa internet: gambar pengganti

Konsistensi: semua pose dibuat dari GAMBAR UTAMA sebagai acuan (FLUX.2 klein), seed tetap. Latar pink polos dipotong
→ PNG transparan, lalu Tio menganimasikannya (mulut buka/tutup ikut suku kata, kepala mengangguk, ekspresi per adegan).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import gambar_ai  # noqa: E402

DIR = ROOT / "bible" / "maskot"          # mode --uji memakai produksi/uji-maskot (bible tidak tersentuh)
GAYA = ROOT / "bible" / "gaya-animasi.json"
SEED = 2026_1102


STATUS = ROOT / "produksi" / "maskot.json"   # dibaca Studio (Ruang Animasi → Gaya & host)


def log(msg: str) -> None:
    print(f"[laras] {msg}", flush=True)


def catat(status: str, pesan: str) -> None:
    STATUS.parent.mkdir(exist_ok=True)
    STATUS.write_text(json.dumps({"status": status, "pesan": pesan, "waktu": time.strftime("%Y-%m-%dT%H:%M:%S")}, ensure_ascii=False), encoding="utf-8")


def gaya() -> dict:
    return json.loads(GAYA.read_text(encoding="utf-8"))


def simpan_potong(jpg: Path, pangkas: bool = True) -> Path:
    png = jpg.with_suffix(".png")
    gambar_ai.potong_latar(jpg.read_bytes(), pangkas=pangkas).save(png)
    return png


def kandidat(uji: bool, n: int = 4) -> None:
    g, m = gaya(), gaya()["maskot"]
    kdir = DIR / "kandidat"
    kdir.mkdir(parents=True, exist_ok=True)
    for i in range(1, n + 1):
        out = kdir / f"k{i}.jpg"
        prompt = ", ".join([g["ilustrasi"]["gaya"], m["prompt"], m["pose"]["diam"], m["latar"], g["ilustrasi"]["larangan"]])
        if uji:
            gambar_ai.contoh_uji(out, f"host kandidat {i}", i, 1024, 1024, pink=True)
        else:
            out.write_bytes(gambar_ai.gambar(prompt, 1024, 1024, seed=SEED + i * 101))
        simpan_potong(out)
        log(f"kandidat host k{i} → bible/maskot/kandidat/k{i}.jpg")
    log("Pilih host di Studio (Ruang Animasi → Gaya & host) atau: python agents/panjang/maskot.py pilih <nomor>")


def pilih(n: int) -> None:
    src = DIR / "kandidat" / f"k{n}.jpg"
    if not src.exists():
        sys.exit(f"[laras] kandidat k{n} belum ada. Jalankan dulu: maskot.py kandidat")
    shutil.copy2(src, DIR / "utama.jpg")
    simpan_potong(DIR / "utama.jpg")
    log(f"host utama = kandidat k{n}. Lanjut: python agents/panjang/maskot.py pose")


def pose(uji: bool) -> None:
    g, m = gaya(), gaya()["maskot"]
    utama = DIR / "utama.jpg"
    if not utama.exists():
        sys.exit("[laras] host utama belum dipilih (maskot.py kandidat → pilih <n>)")
    pdir = DIR / "pose"
    pdir.mkdir(parents=True, exist_ok=True)
    acuan = utama.read_bytes()
    for i, (nama, desk) in enumerate(m["pose"].items()):
        out = pdir / f"{nama}.jpg"
        prompt = (f"The exact same character as the reference image (same face, same hair, same outfit, same badge, same headset, "
                  f"same painting style and colors), {desk}, shoulders-up portrait, centered, {m['latar']}. "
                  f"{g['ilustrasi']['gaya']}. {g['ilustrasi']['larangan']}")
        if uji:
            gambar_ai.contoh_uji(out, f"pose {nama}", i, 1024, 1024, pink=True)
        else:
            out.write_bytes(gambar_ai.gambar(prompt, 1024, 1024, acuan=[acuan], seed=SEED))
        simpan_potong(out, pangkas=False)          # kanvas utuh: semua pose sejajar saat mulut buka/tutup
        log(f"pose {nama} → {pdir.relative_to(ROOT).as_posix()}/{nama}.png")


def acuan_gaya(uji: bool) -> None:
    """Adegan contoh TANPA orang: dipakai Laras sebagai acuan gaya semua ilustrasi. Kalau acuannya memuat host, FLUX ikut
    menyalin wajah Yofa ke setiap ilustrasi (host jadi muncul dobel), jadi host sengaja tidak dipakai sebagai acuan di sini."""
    g = gaya()
    out = DIR / "acuan-gaya.jpg"
    prompt = (f"{g['ilustrasi']['gaya']}, an empty futuristic technology laboratory with a glowing robotic arm, holographic screens and "
              f"floating glass vials, wide cinematic view, no people, no person, no face, no character, {g['ilustrasi']['larangan']}")
    if uji:
        gambar_ai.contoh_uji(out, "acuan gaya", 3)
    else:
        out.write_bytes(gambar_ai.gambar(prompt, 1536, 864, seed=SEED + 7))
    (DIR / "acuan-gaya.json").write_text(json.dumps({"tanpa_host": True, "versi": 2}), encoding="utf-8")
    log(f"acuan gaya (tanpa orang) → {out.relative_to(ROOT).as_posix()}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Host Yofa (gambar AI gaya lukis-komik)")
    ap.add_argument("perintah", choices=["kandidat", "pilih", "pakai", "pose", "acuan-gaya", "otomatis"])
    ap.add_argument("nomor", nargs="?", type=int)
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    global DIR
    if a.uji:
        DIR = ROOT / "produksi" / "uji-maskot"
    DIR.mkdir(parents=True, exist_ok=True)
    from kunci import Kunci
    kunci = Kunci(ROOT / "produksi" / "maskot.lock", maks_jam=2)
    if not a.uji and not kunci.ambil(a.perintah):
        sys.exit("[laras] host sedang digambar oleh proses lain, tunggu selesai")
    nama = {"kandidat": "menggambar 4 kandidat host", "pilih": "memilih host", "pakai": "menggambar pose host",
            "pose": "menggambar pose host", "acuan-gaya": "menggambar acuan gaya", "otomatis": "menggambar host Yofa"}[a.perintah]
    if not a.uji:
        catat("berjalan", nama + "…")
    try:
        if a.perintah == "kandidat":
            kandidat(a.uji)
        elif a.perintah == "pilih":
            pilih(a.nomor or 1)
        elif a.perintah == "pakai":
            pilih(a.nomor or 1)
            pose(a.uji)
            acuan_gaya(a.uji)
        elif a.perintah == "pose":
            pose(a.uji)
        elif a.perintah == "acuan-gaya":
            acuan_gaya(a.uji)
        else:
            kandidat(a.uji)
            pilih(1)
            pose(a.uji)
            acuan_gaya(a.uji)
        if not a.uji:
            catat("selesai", {"kandidat": "4 kandidat siap. Pilih satu.", "pilih": "Host dipilih."}.get(a.perintah, "Host Yofa siap dipakai."))
    except gambar_ai.KuotaGambar as err:
        if not a.uji:
            catat("gagal", "Kuota gambar gratis hari ini habis. Coba lagi setelah 07:00 WIB.")
        sys.exit(f"[laras] {err}. Kuota gratis Cloudflare reset tiap hari jam 07:00 WIB.")
    except BaseException as err:
        if not a.uji:
            catat("gagal", f"{type(err).__name__}: {err}"[:200])
        raise
    finally:
        if not a.uji:
            kunci.lepas()

if __name__ == "__main__":
    main()

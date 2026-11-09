#!/usr/bin/env python3
"""Nova: cek ketersediaan visual LEGAL untuk satu topik SEBELUM topik itu dipilih.
Video pertama pabrik jadi 79% gambar AI karena footage-nya tidak ada; ini mencegah hal itu sejak tahap ide.

    python agents/ide/cek_visual.py "Samsung Galaxy Ring" "smart ring health tracking"   # kata kunci PERTAMA = nama produk/teknologi
    python agents/ide/cek_visual.py --yt "cultured meat" "lab grown chicken"      # + YouTube CC (100 unit kuota/kata)
    python agents/ide/cek_visual.py --tulis <slug> "kata 1" "kata 2"             # simpan hasil ke videos/<slug>/idea.json → visual

Sumber: NASA & Wikimedia (tanpa key), Pexels/Pixabay (kalau ada key), YouTube Creative Commons (opsional --yt).
Skor 0–10: makin banyak footage asli yang relevan, makin tinggi. < 4 = topik berisiko jadi video "AI semua".
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "aset"))
import sumber  # noqa: E402


def yt_cari(q: str, key: str) -> list[dict]:
    """Lewat cache pencarian Bima (cache/yt-cari/): hemat kuota YouTube & Bima nanti memakai hasil yang sama tanpa kuota."""
    try:
        import cari_aset
        return cari_aset.youtube_cari(q, key)
    except ImportError:
        return sumber.youtube_cc(q, key)

# YouTube CC paling sering MEMPERLIHATKAN produknya (demo, hands-on); NASA dulu berbobot tinggi → topik antariksa selalu
# terlihat "punya footage" dan Nova terdorong memilihnya. Sekarang NASA kecil.
BOBOT = {"youtube": 2.0, "nasa": 0.3, "wikimedia": 0.6, "pexels": 0.6, "pixabay": 0.5}
UMUM = {"video", "footage", "technology", "tech", "device", "hands", "review", "with", "from", "using", "close", "shot", "people",
        "person", "new", "the", "and", "for", "demo", "test", "testing", "first", "look", "into", "this", "that"}


def inti(kata: list[str]) -> set[str]:
    """Kata penting dari kata kunci PERTAMA (nama produk/teknologi): hasil pencarian hanya dihitung kalau judulnya menyebut salah satunya."""
    return {w for w in re.findall(r"[a-z0-9]+", (kata[0] if kata else "").lower()) if len(w) >= 3 and w not in UMUM}


def load_env() -> None:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def cek(kata: list[str], yt: bool = True) -> dict:
    load_env()
    kunci = inti(kata)
    tidak_relevan = 0
    pex, pix, ytk = os.environ.get("PEXELS_API_KEY"), os.environ.get("PIXABAY_API_KEY"), os.environ.get("YOUTUBE_API_KEY")
    temuan: dict[str, list[str]] = {k: [] for k in BOBOT}
    gagal = []
    for q in kata:
        jobs = [("nasa", lambda: sumber.nasa(q)), ("wikimedia", lambda: sumber.wikimedia(q))]
        if pex:
            jobs.append(("pexels", lambda: sumber.pexels(q, pex)))
        if pix:
            jobs.append(("pixabay", lambda: sumber.pixabay(q, pix)))
        if yt and ytk:
            jobs.append(("youtube", lambda: yt_cari(q, ytk)))
        for nama, fn in jobs:
            try:
                for c in fn()[:8]:
                    j = f"{c['judul'][:70]}"
                    if kunci and not (kunci & set(re.findall(r"[a-z0-9]+", str(c.get("judul", "")).lower()))):
                        tidak_relevan += 1          # footage umum yang tidak memperlihatkan produk/teknologinya
                        continue
                    if j not in temuan[nama]:
                        temuan[nama].append(j)
            except Exception as err:  # jaringan/kuota: catat, lanjut
                gagal.append(f"{nama}: {str(err)[:80]}")
    nilai = sum(min(len(v), 6) * BOBOT[k] for k, v in temuan.items())
    skor = round(min(10.0, nilai / 1.8), 1)
    if not any(temuan.values()) and gagal:
        skor = None                      # tidak bisa dicek (jaringan), bukan berarti tidak ada footage
    return {"kata_kunci": kata, "skor": skor, "inti": sorted(kunci), "tidak_relevan": tidak_relevan, "jumlah": {k: len(v) for k, v in temuan.items() if v},
            "contoh": {k: v[:3] for k, v in temuan.items() if v}, "gagal": gagal[:6],
            "catatan": "tidak bisa dicek (cek koneksi)" if skor is None else "skor < 4: footage asli langka, video akan banyak gambar AI" if skor < 4 else "cukup footage asli"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Cek ketersediaan footage legal untuk topik")
    ap.add_argument("kata", nargs="+", help="kata kunci bahasa Inggris (2–4)")
    ap.add_argument("--yt", action="store_true", help="(bawaan sekarang) YouTube Creative Commons ikut dicari")
    ap.add_argument("--tanpa-yt", action="store_true", help="lewati YouTube CC (hemat kuota API)")
    ap.add_argument("--tulis", metavar="SLUG", help="simpan hasil ke videos/<slug>/idea.json")
    a = ap.parse_args()
    kata = [k.strip() for k in a.kata if k.strip()][:4]
    if a.tulis and not re.fullmatch(r"[a-z0-9-]{3,80}", a.tulis):
        sys.exit("[nova] slug tidak valid")
    h = cek(kata, not a.tanpa_yt)
    print(f"[nova] visual skor {h['skor'] if h['skor'] is not None else '?'}/10 (hanya footage yang judulnya menyebut: {', '.join(h['inti']) or '-'}; "
          f"{h['tidak_relevan']} hasil umum diabaikan) · " + ", ".join(f"{k} {n}" for k, n in h["jumlah"].items()) + f" · {h['catatan']}")
    for k, v in h["contoh"].items():
        print(f"[nova]   {k}: " + " | ".join(v))
    if h["gagal"]:
        print("[nova]   tidak bisa dicek: " + "; ".join(h["gagal"]))
    if a.tulis:
        p = ROOT / "videos" / a.tulis / "idea.json"
        try:
            idea = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            sys.exit(f"[nova] {p.relative_to(ROOT)} belum ada / rusak")
        idea["visual"] = h
        p.write_text(json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[nova] tersimpan di videos/{a.tulis}/idea.json → visual")


if __name__ == "__main__":
    main()

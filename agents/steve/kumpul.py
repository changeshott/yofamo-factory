#!/usr/bin/env python3
"""Steve: kumpulkan semua data sekaligus (tanpa kuota Claude), lalu hitung analisanya.

    python agents/steve/kumpul.py            # harian: statistik + komentar + analitik (kalau login) + analisa
    python agents/steve/kumpul.py --pasar    # + radar pasar (otomatis kalau radar terakhir > 6 hari)
    python agents/steve/kumpul.py --ringan   # statistik + analisa saja (dipakai Studio sekali sehari)

Satu sumber gagal tidak menghentikan yang lain; semuanya dicatat di akhir.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ytdata  # noqa: E402

PY = sys.executable


def jalan(nama: str, *args: str) -> bool:
    print(f"\n[steve] ── {nama}", flush=True)
    ok = subprocess.run([PY, *args], cwd=ROOT).returncode == 0
    if not ok:
        print(f"[steve] {nama}: gagal (lanjut ke data berikutnya)", flush=True)
    return ok


def main() -> None:
    ap = argparse.ArgumentParser(description="Steve: kumpulkan semua data + analisa")
    ap.add_argument("--pasar", action="store_true", help="paksa radar pasar")
    ap.add_argument("--ringan", action="store_true", help="statistik + analisa saja")
    a = ap.parse_args()
    if a.ringan:
        # Mode ringan (Studio, otomatis tiap hari) dulu TIDAK PERNAH mengambil retensi/komentar → data retensi berhenti di 31 Okt 2026
        # dan tim belajar dari data lama. Sekarang: sekali sehari mode ringan dinaikkan jadi lengkap (retensi + komentar, tanpa kuota Claude).
        last = ytdata.latest("analitik")
        umur_a = (date.today() - date.fromisoformat(last.stem.replace("analitik-", ""))).days if last else 999
        if umur_a >= 1 and (ROOT / "rahasia" / "token.json").exists():
            print(f"[steve] data retensi terakhir {umur_a if umur_a < 999 else '—'} hari lalu → hari ini diambil lengkap", flush=True)
            a.ringan = False
    hasil = {"statistik": jalan("statistik publik channel", "agents/steve/fetch_stats.py")}
    if not a.ringan:
        hasil["komentar"] = jalan("komentar penonton", "agents/steve/komentar.py")
        if (ROOT / "rahasia" / "token.json").exists():
            hasil["analitik"] = jalan("YouTube Analytics (retensi, traffic, audiens)", "agents/steve/analitik.py")
            if hasil["analitik"] and any((ROOT / "panjang").glob("*/export/upload.json")):
                hasil["retensi_panjang"] = jalan("retensi video panjang per bab & adegan", "agents/steve/retensi_panjang.py")
        else:
            print("\n[steve] ── YouTube Analytics dilewati: YouTube belum dihubungkan (meja Uli)", flush=True)
        last = ytdata.latest("pasar")
        umur = (date.today() - date.fromisoformat(last.stem.replace("pasar-", ""))).days if last else 999
        if a.pasar or umur > 6:
            hasil["pasar"] = jalan("radar pasar Shorts teknologi Indonesia", "agents/steve/pasar.py")
        else:
            print(f"\n[steve] ── radar pasar dilewati (terakhir {umur} hari lalu; mingguan cukup)", flush=True)
    hasil["analisa"] = jalan("analisa gabungan", "agents/steve/analisa.py")
    subprocess.run([PY, "agents/otak.py", "perbarui", "--data"], cwd=ROOT, capture_output=True)   # otak: data Steve terbaru
    print("\n[steve] ringkasan: " + ", ".join(f"{k} {'OK' if v else 'GAGAL'}" for k, v in hasil.items()), flush=True)
    sys.exit(0 if hasil["analisa"] else 1)


if __name__ == "__main__":
    main()

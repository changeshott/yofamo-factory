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
    hasil = {"statistik": jalan("statistik publik channel", "agents/steve/fetch_stats.py")}
    if not a.ringan:
        hasil["komentar"] = jalan("komentar penonton", "agents/steve/komentar.py")
        if (ROOT / "rahasia" / "token.json").exists():
            hasil["analitik"] = jalan("YouTube Analytics (retensi, traffic, audiens)", "agents/steve/analitik.py")
        else:
            print("\n[steve] ── YouTube Analytics dilewati: YouTube belum dihubungkan (meja Uli)", flush=True)
        last = ytdata.latest("pasar")
        umur = (date.today() - date.fromisoformat(last.stem.replace("pasar-", ""))).days if last else 999
        if a.pasar or umur > 6:
            hasil["pasar"] = jalan("radar pasar Shorts teknologi Indonesia", "agents/steve/pasar.py")
        else:
            print(f"\n[steve] ── radar pasar dilewati (terakhir {umur} hari lalu; mingguan cukup)", flush=True)
    hasil["analisa"] = jalan("analisa gabungan", "agents/steve/analisa.py")
    print("\n[steve] ringkasan: " + ", ".join(f"{k} {'OK' if v else 'GAGAL'}" for k, v in hasil.items()), flush=True)
    sys.exit(0 if hasil["analisa"] else 1)


if __name__ == "__main__":
    main()

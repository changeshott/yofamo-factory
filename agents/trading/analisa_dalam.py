#!/usr/bin/env python3
"""Nadia — analisa mendalam satu koin/gold dengan Claude (narasi, berita, sosial, + semua angka tim) → trading/analisa/<id>.md

    python agents/trading/analisa_dalam.py <sinyal_id | alamat_token | gold>

Dipanggil tombol "Analisa mendalam" di Studio. Memakai kuota Claude (±3–6 menit). Tidak pernah mengirim order.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import tanpa_jendela  # noqa: E402,F401
import produser as pr  # noqa: E402

ROOT = HERE.parents[1]


def main() -> None:
    if len(sys.argv) < 2 or not re.fullmatch(r"[A-Za-z0-9:_-]{3,80}", sys.argv[1]):
        sys.exit("[nadia] pakai: analisa_dalam.py <sinyal_id | alamat_token | gold>")
    target = sys.argv[1]
    (ROOT / "trading" / "analisa").mkdir(parents=True, exist_ok=True)
    try:
        kode = pr.claude(f"/trading-analisa {target}",
                         pr.tools("agents/trading/meja.py", "agents/trading/lihat.py", web=True), 20 * 60, turns=40)
    except pr.KuotaClaude as err:
        sys.exit(f"[nadia] {err}")
    sys.exit(kode)


if __name__ == "__main__":
    main()

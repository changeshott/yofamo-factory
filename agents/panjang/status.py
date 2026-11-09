"""Status video panjang (terpisah dari pabrik Shorts supaya autopilot Shorts tidak pernah menyentuhnya).

panjang/<slug>/status.json → {"status": ..., "riwayat": [{"ke", "waktu", "catatan"}]}
Urutan: ide → naskah → suara → ilustrasi → animasi → draft → export → terbit (atau ditolak).
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "panjang"
URUT = ["ide", "naskah", "suara", "ilustrasi", "animasi", "draft", "export", "terbit"]


def folder(slug: str) -> Path:
    if not re.fullmatch(r"[a-z0-9-]{3,80}", slug or ""):
        raise SystemExit(f"slug tidak valid: {slug}")
    return BASE / slug


def baca(slug: str) -> dict:
    try:
        return json.loads((folder(slug) / "status.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def status(slug: str) -> str | None:
    return baca(slug).get("status")


def sudah(slug: str, tahap: str) -> bool:
    s = status(slug)
    return s in URUT and URUT.index(s) >= URUT.index(tahap)


def set_status(slug: str, ke: str, catatan: str = "") -> None:
    d = baca(slug)
    # status tidak boleh mundur setelah video diupload (dulu render ulang yang masih berjalan mengembalikan video tayang ke 'draft')
    if ke not in ("export", "terbit") and sudah_diunggah(slug) and os.environ.get("YOFAMO_PAKSA") != "1":
        print(f"[status] {slug} sudah diupload: status tidak diubah ke '{ke}'", flush=True)
        return
    d.setdefault("riwayat", []).append({"dari": d.get("status"), "ke": ke, "waktu": datetime.now().isoformat(timespec="seconds"), "catatan": catatan})
    d["status"] = ke
    d["riwayat"] = d["riwayat"][-40:]
    f = folder(slug) / "status.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(f)


def sudah_diunggah(slug: str) -> bool:
    try:
        up = json.loads((folder(slug) / "export" / "upload.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return False
    return bool(up.get("videoId")) and up.get("videoId") != "UJI" and not up.get("dibatalkan")


def jaga_belum_terbit(slug: str, nama: str) -> None:
    """Penjaga: video yang sudah diupload tidak boleh dirender/diubah lagi (dulu Wulan me-render ulang saat Uli mengunggah,
    lalu bersih.py menghapus adegannya). Lewati dengan env YOFAMO_PAKSA=1 kalau memang sengaja."""
    if sudah_diunggah(slug) and os.environ.get("YOFAMO_PAKSA") != "1":
        raise SystemExit(f"[{nama}] {slug} sudah diupload ke YouTube: tidak dirender ulang (YOFAMO_PAKSA=1 untuk memaksa)")


def semua() -> list[dict]:
    out = []
    for d in sorted(BASE.glob("*/status.json"), reverse=True):
        s = json.loads(d.read_text(encoding="utf-8"))
        out.append({"slug": d.parent.name, "status": s.get("status"), "diubah": (s.get("riwayat") or [{}])[-1].get("waktu")})
    return out


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "set":
        set_status(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
        print(f"[panjang] {sys.argv[2]} → {sys.argv[3]}")
    else:
        for v in semua():
            print(f"{v['status'] or '-':10} {v['slug']}  ({v['diubah']})")

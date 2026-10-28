#!/usr/bin/env python3
"""Pencatat antrean video pabrik Yofamo (SQLite: state.db).

Pemakaian (dari root project):
    python agents/pabrik.py new "Judul kerja video"     # buat folder + catatan, status 'ide'
    python agents/pabrik.py list [--status STATUS] [--json]
    python agents/pabrik.py show <slug>
    python agents/pabrik.py set <slug> <status> [--note "catatan"]
    python agents/pabrik.py history [--limit 40] --json   # riwayat (dipakai Studio)
    python agents/pabrik.py week --json                   # jumlah terbit sejak Senin

Status berurutan:
    ide → disetujui → naskah → suara → aset → draft → export → terbit
    (ditolak = ide dibuang)
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "state.db"
VIDEOS = ROOT / "videos"

STATUSES = ["ide", "disetujui", "naskah", "suara", "aset", "draft", "export", "terbit", "ditolak"]
STATUS_LABEL = {
    "ide": "Ide menunggu persetujuan",
    "disetujui": "Ide disetujui, siap ditulis",
    "naskah": "Naskah siap",
    "suara": "Suara siap",
    "aset": "Aset siap",
    "draft": "Draft CapCut siap",
    "export": "Sudah di-export",
    "terbit": "Sudah terbit",
    "ditolak": "Ditolak",
}


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS videos (
        slug TEXT PRIMARY KEY,
        judul_kerja TEXT NOT NULL,
        status TEXT NOT NULL,
        dibuat TEXT NOT NULL,
        diubah TEXT NOT NULL,
        catatan TEXT DEFAULT ''
    )""")
    con.execute("""CREATE TABLE IF NOT EXISTS riwayat (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        slug TEXT NOT NULL,
        dari TEXT,
        ke TEXT NOT NULL,
        waktu TEXT NOT NULL,
        catatan TEXT DEFAULT ''
    )""")
    return con


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return "-".join(text.split("-")[:6]) or "video"


def create(judul: str) -> dict:
    with connect() as con:
        base = f"{datetime.now():%Y%m%d}-{slugify(judul)}"
        slug, n = base, 2
        while con.execute("SELECT 1 FROM videos WHERE slug=?", (slug,)).fetchone():
            slug, n = f"{base}-{n}", n + 1
        t = now()
        con.execute("INSERT INTO videos(slug, judul_kerja, status, dibuat, diubah) VALUES (?,?,?,?,?)",
                    (slug, judul.strip(), "ide", t, t))
        con.execute("INSERT INTO riwayat(slug, dari, ke, waktu) VALUES (?,?,?,?)", (slug, None, "ide", t))
    (VIDEOS / slug).mkdir(parents=True, exist_ok=True)
    return get(slug)


def get(slug: str) -> dict | None:
    with connect() as con:
        row = con.execute("SELECT * FROM videos WHERE slug=?", (slug,)).fetchone()
    return dict(row) if row else None


def all_videos(status: str | None = None) -> list[dict]:
    with connect() as con:
        if status:
            rows = con.execute("SELECT * FROM videos WHERE status=? ORDER BY dibuat", (status,)).fetchall()
        else:
            rows = con.execute("SELECT * FROM videos ORDER BY dibuat DESC").fetchall()
    return [dict(r) for r in rows]


def set_status(slug: str, status: str, note: str = "") -> dict:
    if status not in STATUSES:
        raise ValueError(f"Status tidak dikenal: {status}. Pilihan: {', '.join(STATUSES)}")
    cur = get(slug)
    if not cur:
        raise ValueError(f"Video tidak ditemukan: {slug}")
    t = now()
    with connect() as con:
        con.execute("UPDATE videos SET status=?, diubah=?, catatan=? WHERE slug=?",
                    (status, t, note or cur["catatan"], slug))
        con.execute("INSERT INTO riwayat(slug, dari, ke, waktu, catatan) VALUES (?,?,?,?,?)",
                    (slug, cur["status"], status, t, note))
    return get(slug)


def history(limit: int = 30) -> list[dict]:
    """Riwayat perubahan status terbaru, lengkap dengan judul kerja."""
    with connect() as con:
        rows = con.execute("""SELECT r.slug, r.dari, r.ke, r.waktu, r.catatan, v.judul_kerja
                              FROM riwayat r LEFT JOIN videos v ON v.slug = r.slug
                              ORDER BY r.id DESC LIMIT ?""", (limit,)).fetchall()
    return [dict(r) for r in rows]


def published_since(iso_date: str) -> int:
    with connect() as con:
        row = con.execute("SELECT COUNT(DISTINCT slug) FROM riwayat WHERE ke='terbit' AND waktu >= ?",
                          (iso_date,)).fetchone()
    return int(row[0])


def read_json(slug: str, name: str) -> dict | None:
    path = VIDEOS / slug / name
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError:
        return {"_error": f"{name} bukan JSON yang valid"}


def main() -> None:
    ap = argparse.ArgumentParser(description="Antrean video pabrik Yofamo")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_new = sub.add_parser("new"); p_new.add_argument("judul")
    p_list = sub.add_parser("list"); p_list.add_argument("--status"); p_list.add_argument("--json", action="store_true")
    p_show = sub.add_parser("show"); p_show.add_argument("slug")
    p_set = sub.add_parser("set"); p_set.add_argument("slug"); p_set.add_argument("status"); p_set.add_argument("--note", default="")
    p_hist = sub.add_parser("history"); p_hist.add_argument("--limit", type=int, default=40); p_hist.add_argument("--json", action="store_true")
    p_week = sub.add_parser("week"); p_week.add_argument("--json", action="store_true")
    args = ap.parse_args()

    try:
        if args.cmd == "new":
            v = create(args.judul)
            print(f"[pabrik] dibuat: {v['slug']}  → tulis file ke videos/{v['slug']}/")
        elif args.cmd == "list":
            rows = all_videos(args.status)
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            elif not rows:
                print("[pabrik] antrean kosong")
            else:
                for r in rows:
                    print(f"{r['status']:<10} {r['slug']}  — {r['judul_kerja']}")
        elif args.cmd == "show":
            v = get(args.slug)
            if not v:
                sys.exit(f"[pabrik] tidak ditemukan: {args.slug}")
            files = sorted(p.name for p in (VIDEOS / args.slug).glob("*")) if (VIDEOS / args.slug).exists() else []
            print(json.dumps({**v, "files": files}, ensure_ascii=False, indent=2))
        elif args.cmd == "history":
            print(json.dumps(history(args.limit), ensure_ascii=False))
        elif args.cmd == "week":
            from datetime import date, timedelta
            monday = date.today() - timedelta(days=date.today().weekday())
            print(json.dumps({"since": monday.isoformat(), "published": published_since(monday.isoformat())}))
        elif args.cmd == "set":
            v = set_status(args.slug, args.status, args.note)
            print(f"[pabrik] {v['slug']} → {v['status']}")
    except ValueError as err:
        sys.exit(f"[pabrik] {err}")


if __name__ == "__main__":
    main()

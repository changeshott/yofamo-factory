#!/usr/bin/env python3
"""Cek apakah topik sudah pernah dibahas di channel Yofamo (atau sedang dikerjakan pabrik).

    python agents/ide/cek_topik.py --daftar                       # semua judul yang sudah ada (channel + pabrik)
    python agents/ide/cek_topik.py "lensa kontak pintar layar AR" # cek satu kandidat topik

Sumber: snapshot terbaru insights/raw/YYYY-MM-DD.json (semua video channel, diambil Steve)
dan antrean pabrik (state.db, kecuali ide yang ditolak).
Keluar dengan kode 2 kalau topik terlalu mirip dengan yang sudah ada (DUPLIKAT), 0 kalau aman.
Ini saringan kasar berbasis kata; Nova tetap wajib menilai sendiri apakah teknologinya sama.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insights" / "raw"

STOP = set("""
yang ini itu ini? bisa di ke dari dan atau jadi beneran nyata teknologi tech shorts teknologi? dengan untuk
pakai paling bikin kamu kita aku sudah akan baru gila canggih ajaib keren tanpa juga lagi sama ada apa aja
the a of to in and is for with resmi dijual bebas ilmuwan ciptakan diciptakan masa depan mirip semua
banget dunia sekarang orang manusia sendiri seperti tapi bukan cuma hanya sci fi scifi real time
""".split())
SINONIM = {"ponsel": "hp", "handphone": "hp", "smartphone": "hp", "pakaian": "baju", "kain": "baju", "busana": "baju",
           "3d": "printer3d", "print": "printer3d", "printer": "printer3d", "mencetak": "printer3d", "dicetak": "printer3d",
           "lensa": "lensa", "kontak": "lensa", "kacamata": "kacamata", "glasses": "kacamata", "robotik": "robot",
           "exoskeleton": "rangka", "eksoskeleton": "rangka", "headset": "speaker", "earbud": "earbud", "earbuds": "earbud",
           "daging": "daging", "steak": "daging", "jantung": "organ", "ginjal": "organ", "hewan": "hewan", "purba": "hewan"}


def tokens(text: str) -> set[str]:
    text = re.sub(r"#\w+", " ", text.lower())
    out = set()
    for w in re.findall(r"[a-z0-9]+", text):
        if len(w) < 3 and w != "3d" and w != "hp" or w in STOP:
            continue
        out.add(SINONIM.get(w, w))
    return out


def existing() -> list[dict]:
    items = []
    snaps = sorted(f for f in RAW.glob("*.json") if re.fullmatch(r"\d{4}-\d\d-\d\d\.json", f.name))
    if snaps:
        try:
            for v in json.loads(snaps[-1].read_text(encoding="utf-8-sig")).get("videos", []):
                items.append({"asal": "channel", "judul": v.get("title", ""), "terbit": v.get("published", "")[:10]})
        except ValueError:
            pass
    r = subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "list", "--json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
    try:
        for v in json.loads(r.stdout or "[]"):
            if v.get("status") != "ditolak":
                items.append({"asal": f"pabrik:{v['status']}", "judul": v.get("judul_kerja", ""), "slug": v.get("slug")})
    except ValueError:
        pass
    return items


def main() -> None:
    ap = argparse.ArgumentParser(description="Cek topik belum pernah dibahas")
    ap.add_argument("topik", nargs="?")
    ap.add_argument("--daftar", action="store_true")
    ap.add_argument("--abaikan", default="", help="slug pabrik yang tidak ikut dibandingkan (ide itu sendiri)")
    a = ap.parse_args()
    items = [i for i in existing() if not (a.abaikan and i.get("slug") == a.abaikan)]
    snap_ok = any(i["asal"] == "channel" for i in items)
    if a.daftar or not a.topik:
        print(f"[cek] {sum(i['asal'] == 'channel' for i in items)} video channel, {sum(i['asal'] != 'channel' for i in items)} di pabrik"
              + ("" if snap_ok else " — PERINGATAN: belum ada snapshot channel, jalankan agents/steve/fetch_stats.py"))
        for i in items:
            print(f"- [{i['asal']}] {i['judul']}")
        return
    t = tokens(a.topik)
    hasil = []
    for i in items:
        e = tokens(i["judul"])
        shared = t & e
        if not shared:
            continue
        score = len(shared) / max(1, min(len(t), len(e)))
        hasil.append((score, len(shared), i, sorted(shared)))
    hasil.sort(key=lambda x: (-x[0], -x[1]))
    dup = [h for h in hasil if h[0] >= 0.5 and h[1] >= 2]
    for score, n, i, shared in hasil[:5]:
        print(f"[cek] {score:.0%} mirip [{i['asal']}] {i['judul']}  (kata sama: {', '.join(shared)})")
    if not snap_ok:
        print("[cek] PERINGATAN: belum ada snapshot channel; hasil hanya dari pabrik.")
    if dup:
        print(f"[cek] DUPLIKAT: topik ini sudah dibahas/sedang dibuat ({dup[0][2]['judul']}). Pilih teknologi lain.")
        sys.exit(2)
    print("[cek] AMAN: tidak ada judul yang sangat mirip. Tetap pastikan teknologinya memang berbeda.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Kata pencarian YouTube (gratis, tanpa token & tanpa kuota API): apa yang benar-benar diketik orang Indonesia tentang satu produk.

    python agents/ide/kata_cari.py "Oura Ring 5"                     # saran pencarian YouTube untuk beberapa pola kueri
    python agents/ide/kata_cari.py "Oura Ring 5" --tulis <slug>      # + simpan ke panjang/<slug>/kata_cari.json (Bayu/Citra)
    python agents/ide/kata_cari.py "Oura Ring 5" --shorts <slug>     # + simpan ke videos/<slug>/kata_cari.json (Raka)

Video panjang hidup dari PENCARIAN (Shorts dari feed). Judul yang memuat frasa yang dicari orang → muncul di hasil pencarian.
Sumber: layanan saran pencarian (autocomplete) YouTube, bahasa & wilayah Indonesia. Urutan saran = urutan dari YouTube (yang
teratas paling populer). Kalau layanan tidak bisa dihubungi, hasil kosong dengan catatan — tidak pernah dikarang.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UA = "Mozilla/5.0 (YofamoKataCari/1.0)"
URL = "https://suggestqueries.google.com/complete/search?"
POLA = ["{p}", "{p} review", "{p} indonesia", "apa itu {p}", "{p} harga", "{p} vs", "cara kerja {p}"]


def saran(kueri: str, timeout: int = 15) -> list[str]:
    q = urllib.parse.urlencode({"client": "firefox", "ds": "yt", "hl": "id", "gl": "id", "q": kueri})
    req = urllib.request.Request(URL + q, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    return [str(x) for x in (data[1] if isinstance(data, list) and len(data) > 1 else [])]


def token(t: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", t.lower()) if len(w) >= 2}


def kumpulkan(produk: str, ambil=saran) -> dict:
    inti = token(produk)
    semua: dict[str, dict] = {}
    gagal = []
    for k, pola in enumerate(POLA):
        q = pola.format(p=produk.strip())
        try:
            hasil = ambil(q)
        except Exception as err:  # noqa: BLE001 — layanan tidak terjangkau: catat, jangan dikarang
            gagal.append(f"{q}: {str(err)[:60]}")
            continue
        for urut, s in enumerate(hasil):
            s = " ".join(s.split())
            if not s or not (inti & token(s)):
                continue                                   # saran yang tidak menyebut produknya tidak dipakai
            e = semua.setdefault(s.lower(), {"frasa": s, "muncul": 0, "skor": 0.0, "dari": []})
            e["muncul"] += 1
            e["skor"] += round(1.0 / (1 + urut), 3)         # posisi atas = lebih populer
            e["dari"].append(q)
        if k < len(POLA) - 1:
            time.sleep(0.3)
    daftar = sorted(semua.values(), key=lambda e: (-e["skor"], -e["muncul"], len(e["frasa"])))
    tanya = [e["frasa"] for e in daftar if re.match(r"^(apa|bagaimana|cara|kenapa|berapa|apakah)\b", e["frasa"].lower())]
    return {"produk": produk, "dibuat": datetime.now().isoformat(timespec="minutes"), "frasa": daftar[:25],
            "pertanyaan": tanya[:8], "gagal": gagal,
            "catatan": "data belum cukup (layanan saran tidak terjangkau)" if not daftar and gagal else ""}


def main() -> None:
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Saran pencarian YouTube untuk satu produk")
    ap.add_argument("produk")
    ap.add_argument("--tulis", metavar="SLUG", help="simpan ke panjang/<slug>/kata_cari.json")
    ap.add_argument("--shorts", metavar="SLUG", help="simpan ke videos/<slug>/kata_cari.json")
    a = ap.parse_args()
    d = kumpulkan(a.produk)
    for slug, base in ((a.tulis, "panjang"), (a.shorts, "videos")):
        if slug:
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,79}", slug):
                sys.exit(f"slug tidak valid: {slug}")
            f = ROOT / base / slug / "kata_cari.json"
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"[kata-cari] → {f.relative_to(ROOT).as_posix()}")
    print(f"Kata pencarian YouTube (Indonesia) untuk \"{a.produk}\":")
    for e in d["frasa"][:15]:
        print(f"  {e['skor']:.2f}  {e['frasa']}")
    if d["pertanyaan"]:
        print("Pertanyaan yang dicari orang: " + " | ".join(d["pertanyaan"][:5]))
    if d["catatan"]:
        print(d["catatan"])
    if d["gagal"]:
        print(f"({len(d['gagal'])} kueri gagal)")


if __name__ == "__main__":
    main()

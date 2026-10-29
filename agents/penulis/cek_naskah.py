#!/usr/bin/env python3
"""Validasi videos/<slug>/script.json sesuai channel bible.

Pemakaian (dari root project):
    python agents/penulis/cek_naskah.py <slug>
Keluar dengan kode 0 kalau LOLOS, 1 kalau ada GAGAL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS_PER_SECOND = 2.6  # tempo TTS sedikit lebih cepat dari normal


def count_words(text: str) -> int:
    return len(re.findall(r"[\w'-]+", text))


def check(slug: str) -> tuple[list[str], list[str], dict]:
    fails, warns, info = [], [], {}
    folder = ROOT / "videos" / slug
    path = folder / "script.json"
    if not path.exists():
        return [f"{path.relative_to(ROOT)} tidak ada"], warns, info
    try:
        s = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as err:
        return [f"script.json bukan JSON valid: {err}"], warns, info

    for key in ("judul", "hook_teks", "narasi", "deskripsi", "tag", "sumber"):
        if not s.get(key):
            fails.append(f"field '{key}' kosong atau tidak ada")
    if fails:
        return fails, warns, info

    judul = s["judul"].strip()
    if not judul.endswith("#Shorts #Teknologi"):
        fails.append("judul harus diakhiri tepat '#Shorts #Teknologi'")
    if len(judul) > 100:
        fails.append(f"judul {len(judul)} karakter (maksimal 100)")
    klaim = judul.replace("#Shorts #Teknologi", "").strip()
    letters = [c for c in klaim.split("!")[0].split("?")[0] if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) < 0.8:
        warns.append("bagian klaim judul sebaiknya HURUF KAPITAL")

    hook_words = count_words(s["hook_teks"])
    if hook_words > 6:
        fails.append(f"hook_teks {hook_words} kata (maksimal 6)")

    narasi = s["narasi"]
    if not isinstance(narasi, list) or not all(isinstance(n, dict) for n in narasi):
        fails.append("narasi harus berupa daftar {kalimat, visual}")
        return fails, warns, info
    if not 6 <= len(narasi) <= 12:
        warns.append(f"narasi {len(narasi)} kalimat (disarankan 6–12)")
    for i, n in enumerate(narasi, 1):
        if not str(n.get("kalimat", "")).strip():
            fails.append(f"narasi #{i} tidak punya kalimat")
        if len(str(n.get("visual", "")).strip()) < 8:
            fails.append(f"narasi #{i} butuh petunjuk visual yang konkret")
        if re.search(r"\d{4,}|\d+[.,]\d{3}", str(n.get("kalimat", ""))):
            warns.append(f"narasi #{i} memuat angka panjang; tulis dengan huruf supaya TTS membacanya benar")

    words = sum(count_words(str(n.get("kalimat", ""))) for n in narasi)
    info["kata"] = words
    info["durasi_detik"] = round(words / WORDS_PER_SECOND)
    if not 80 <= words <= 98:
        fails.append(f"narasi {words} kata (harus 80–98, supaya suara 30–45 detik)")

    tags = s["tag"]
    if not isinstance(tags, list) or not 8 <= len(tags) <= 15:
        fails.append("tag harus daftar 8–15 item")
    elif any(str(t).startswith("#") for t in tags):
        fails.append("tag ditulis tanpa '#'")

    sumber = [u for u in s["sumber"] if isinstance(u, str)]
    if len(sumber) < 2 or not all(u.startswith("http") for u in sumber):
        fails.append("minimal 2 URL sumber yang valid")
    else:
        idea_path = folder / "idea.json"
        if idea_path.exists():
            try:
                idea = json.loads(idea_path.read_text(encoding="utf-8-sig"))
                known = {f.get("sumber_url") for f in idea.get("fakta", [])}
                unknown = [u for u in sumber if u not in known]
                if unknown:
                    fails.append(f"{len(unknown)} sumber tidak ada di idea.json (jangan menambah fakta baru)")
            except ValueError:
                warns.append("idea.json tidak bisa dibaca untuk mencocokkan sumber")
        if not any(u in s["deskripsi"] for u in sumber):
            warns.append("deskripsi sebaiknya mencantumkan URL sumber")

    return fails, warns, info


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Pemakaian: python agents/penulis/cek_naskah.py <slug>")
    fails, warns, info = check(sys.argv[1])
    for f in fails:
        print(f"GAGAL  {f}")
    for w in warns:
        print(f"SARAN  {w}")
    if info:
        print(f"INFO   {info.get('kata')} kata, estimasi {info.get('durasi_detik')} detik")
    print("LOLOS" if not fails else f"{len(fails)} masalah harus diperbaiki")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()

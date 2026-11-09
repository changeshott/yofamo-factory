#!/usr/bin/env python3
"""Kamus pelafalan Dara & Gilang: nama produk/merek asing dibaca benar oleh suara AI berbahasa Indonesia.

Suara Indonesia membaca ejaan apa adanya ("Xiaomi" → "ksi-a-o-mi", "Oura" → "o-u-ra"). Sebelum TTS, kata di kamus diganti
ejaan bacanya (bagian dipisah tanda hubung, mis. "ei-ai"); sesudah TTS, timing kata DIPULIHKAN ke tulisan aslinya sehingga
subtitle & pemetaan kalimat tetap menulis "Xiaomi", bukan "syaomi".

Sumber kamus (yang belakangan menimpa):
  1. bible/lafal.json                              — kamus tetap channel (Zona boleh mengedit)
  2. naskah: script.json / naskah.json → "lafal"   — tambahan per video dari Raka/Citra, mis. {"SOLIX": "so-liks"}

    python agents/suara/lafal.py "Oura Ring 5 dari Xiaomi pakai AI"     # lihat teks yang dibacakan
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KAMUS_F = ROOT / "bible" / "lafal.json"
TOKEN = re.compile(r"[\w'’-]+", re.UNICODE)


def norm(w: str) -> str:
    return re.sub(r"[^\w]", "", str(w).lower())


def kamus(tambahan: dict | None = None) -> dict[str, str]:
    try:
        k = json.loads(KAMUS_F.read_text(encoding="utf-8-sig")).get("kamus") or {}
    except (OSError, ValueError):
        k = {}
    out = {str(a).strip(): str(b).strip() for a, b in {**k, **(tambahan or {})}.items()
           if str(a).strip() and str(b).strip() and not str(a).startswith("_") and " " not in str(a).strip()}
    return out


def _cocok(tok: str, k: dict[str, str]) -> str | None:
    """Kunci kamus yang cocok untuk satu token. Singkatan huruf besar ≤ 4 (AI, VR, GPU) harus sama persis hurufnya
    supaya kata Indonesia biasa tidak ikut terganti; lainnya tidak peka huruf besar/kecil."""
    if tok in k:
        return tok
    low = tok.lower()
    for a in k:
        if not (a.isupper() and len(a) <= 4) and a.lower() == low:
            return a
    return None


def ucapkan(teks: str, k: dict[str, str]) -> str:
    """Teks untuk TTS: token yang ada di kamus diganti ejaan bacanya. Tanda baca & spasi lain tidak diubah."""
    if not k:
        return teks
    def ganti(m: re.Match) -> str:
        tok = m.group(0)
        a = _cocok(tok, k)
        if a is None and "-" in tok:            # "USB-C" utuh tidak ada → coba tiap bagian ("Wi-Fi-nya" jarang; cukup bagian depan)
            return tok
        return k[a] if a is not None else tok
    return TOKEN.sub(ganti, teks)


def pulihkan(kata: list[dict], teks_asli: str, k: dict[str, str]) -> list[dict]:
    """Timing kata hasil TTS (ejaan baca) → tulisan asli. Ejaan baca yang dipecah TTS menjadi beberapa kata ("ei", "ai")
    digabung lagi jadi satu kata ("AI") dengan waktu mulai kata pertama & selesai kata terakhir."""
    if not k or not kata:
        return kata
    target: dict[str, str] = {}
    for tok in TOKEN.findall(teks_asli):
        a = _cocok(tok, k)
        if a is not None:
            target[norm(k[a])] = tok             # tulisan asli seperti di naskah
    if not target:
        return kata
    out, i = [], 0
    while i < len(kata):
        gabung, j, cocok = "", i, None
        while j < len(kata) and len(gabung) < max(len(t) for t in target):
            gabung += norm(kata[j].get("kata", ""))
            j += 1
            if gabung in target:
                cocok = (j, target[gabung])
                break
            if not any(t.startswith(gabung) for t in target):
                break
        if cocok:
            j, asli = cocok
            out.append({**kata[i], "kata": asli, "selesai": kata[j - 1]["selesai"]})
            i = j
        else:
            out.append(kata[i])
            i += 1
    return out


if __name__ == "__main__":
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    teks = " ".join(sys.argv[1:]) or "Oura Ring 5 dari Xiaomi pakai AI dan Wi-Fi"
    print(ucapkan(teks, kamus()))

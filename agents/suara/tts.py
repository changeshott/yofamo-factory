#!/usr/bin/env python3
"""Perekam suara edge-tts bersama (Dara & Gilang): audio + waktu tiap kata, untuk SEMUA jenis suara.

Suara Indonesia asli (Ardi, Gadis) mengirim batas tiap kata. Sebagian suara multibahasa yang lebih natural hanya mengirim
batas kalimat (atau tidak sama sekali); untuk itu waktu tiap kata DIPERKIRAKAN dari panjang suku katanya di dalam kalimat,
sehingga subtitle 1 kata & grafis tetap sinkron (selisih kecil, ±0,1 dtk).

    kata = asyncio.run(tts.rekam("Halo dunia.", "id-ID-ArdiNeural", "+10%", "+0Hz", Path("a.mp3")))
    → [{"kata": "Halo", "mulai": 0.05, "selesai": 0.41}, ...]
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

TICKS = 10_000_000
TOKEN = re.compile(r"[\w'’-]+", re.UNICODE)


def durasi(f: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(f)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def bobot(kata: str) -> float:
    """Perkiraan lama pengucapan satu kata: jumlah suku kata (kelompok vokal); angka dibaca panjang."""
    if re.fullmatch(r"[\d.,]+", kata):
        return 1.2 + 1.3 * len(re.sub(r"\D", "", kata))
    return max(1.0, len(re.findall(r"[aiueoAIUEO]+", kata))) + 0.35


def perkirakan(kalimat: list[dict], total: float) -> list[dict]:
    """[{teks, mulai, selesai}] per kalimat → waktu tiap kata, dibagi menurut bobot suku kata."""
    out = []
    for k in kalimat:
        toks = TOKEN.findall(k["teks"])
        if not toks:
            continue
        a, b = max(0.0, float(k["mulai"])), min(total or 1e9, float(k["selesai"]))
        b = max(b, a + 0.12 * len(toks))
        w = [bobot(t) for t in toks]
        t, per = a, (b - a) / sum(w)
        for tok, wi in zip(toks, w):
            d = per * wi
            out.append({"kata": tok, "mulai": round(t, 3), "selesai": round(t + d * 0.94, 3)})
            t += d
    return out


async def _alir(teks: str, voice: str, rate: str, pitch: str, out: Path, batas: str) -> tuple[list[dict], list[dict]]:
    import edge_tts  # type: ignore
    comm = edge_tts.Communicate(teks, voice, rate=rate, pitch=pitch, boundary=batas)
    kata, kal = [], []
    with out.open("wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / TICKS
                kata.append({"kata": ch["text"], "mulai": round(s, 3), "selesai": round(s + ch["duration"] / TICKS, 3)})
            elif ch["type"] == "SentenceBoundary":
                s = ch["offset"] / TICKS
                kal.append({"teks": ch["text"], "mulai": s, "selesai": s + ch["duration"] / TICKS})
    return kata, kal


CADANGAN = "id-ID-ArdiNeural"


async def rekam(teks: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz", out: Path = Path("tts.mp3"), cadangan: str | None = CADANGAN) -> list[dict]:
    """Rekam `teks` ke `out` (mp3) dan kembalikan waktu tiap kata. Suara pilihan (mis. multibahasa) gagal → otomatis suara
    cadangan Ardi supaya produksi tidak berhenti (cadangan=None mematikan ini). Melempar RuntimeError kalau tidak ada audio."""
    if cadangan and voice != cadangan:
        try:
            return await _rekam(teks, voice, rate, pitch, out)
        except Exception as err:  # noqa: BLE001
            print(f"[suara] {voice} gagal ({str(err)[:90]}) → memakai suara cadangan {cadangan}", flush=True)
            return await _rekam(teks, cadangan, rate, pitch, out)
    return await _rekam(teks, voice, rate, pitch, out)


async def _rekam(teks: str, voice: str, rate: str, pitch: str, out: Path) -> list[dict]:
    kata: list[dict] = []
    try:
        kata, _ = await _alir(teks, voice, rate, pitch, out, "WordBoundary")
    except Exception as err:  # noqa: BLE001 — suara yang tidak mendukung batas kata: coba batas kalimat
        if "WordBoundary" not in str(err) and "metadata" not in str(err).lower():
            raise
    if kata and out.exists() and out.stat().st_size > 0:
        return kata
    _, kal = await _alir(teks, voice, rate, pitch, out, "SentenceBoundary")
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError("layanan TTS tidak mengirim audio")
    total = durasi(out)
    if not kal:
        kal = [{"teks": teks, "mulai": 0.08, "selesai": max(0.3, total - 0.12)}]
    return perkirakan(kal, total)

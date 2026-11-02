#!/usr/bin/env python3
"""Gilang — pengisi suara video panjang. Narasi tiap adegan → suara (edge-tts, gratis) + timing tiap kata & kalimat.

    python agents/panjang/suara_panjang.py <slug>          # semua adegan → panjang/<slug>/suara/NN.mp3 + waktu.json
    python agents/panjang/suara_panjang.py <slug> --uji    # tanpa internet: timing perkiraan + audio senyap

Timing kata dipakai Tio (animator) untuk gerak mulut maskot, kata kunci di layar, dan butir diagram yang muncul per kalimat.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "suara"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("edge_tts")
import buat_suara as dara  # noqa: E402
import status as st_panjang  # noqa: E402

GAYA = ROOT / "bible" / "gaya-animasi.json"
# akting suara per jenis adegan (edge-tts tidak punya emosi → tempo & nada)
PROSODI = {"host": (0, 2), "ilustrasi": (-2, 0), "diagram": (-5, -1), "penutup": (-4, -2), "judul_bab": (0, 0)}


def log(msg: str) -> None:
    print(f"[gilang] {msg}", flush=True)


def kalimat_dari(narasi: str) -> list[str]:
    return [k.strip() for k in re.split(r"(?<=[.!?…])\s+", narasi.strip()) if k.strip()]


def petakan_kalimat(kal: list[str], kata: list[dict]) -> list[dict]:
    out, i = [], 0
    for k in kal:
        n = len(dara.tokens(k))
        if not n or i >= len(kata):
            continue
        seg = kata[i: i + n]
        out.append({"teks": k, "mulai": seg[0]["mulai"], "selesai": seg[-1]["selesai"]})
        i += n
    return out


def senyap(out: Path, detik: float) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{detik:.3f}",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(out)], check=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Gilang: suara video panjang")
    ap.add_argument("slug")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    g = json.loads(GAYA.read_text(encoding="utf-8")) if GAYA.exists() else {}
    sg = g.get("suara", {})
    voice, rate = sg.get("voice", "id-ID-ArdiNeural"), sg.get("rate", "+6%")
    pad, judul_detik = float(sg.get("jeda_antar_adegan", 0.35)), float(sg.get("judul_bab_detik", 2.6))
    m = re.match(r"([+-]\d+)%", rate)
    dasar = int(m.group(1)) if m else 0
    sdir = vdir / "suara"
    sdir.mkdir(exist_ok=True)
    waktu, total = {}, 0.0
    for i, ad in enumerate(naskah["adegan"]):
        out = sdir / f"{i + 1:02}.mp3"
        teks = str(ad.get("narasi") or "").strip()
        if not teks:
            durasi = judul_detik if ad.get("jenis") == "judul_bab" else 2.0
            senyap(out, durasi)
            waktu[str(i)] = {"durasi": round(durasi, 3), "kata": [], "kalimat": [], "jeda_awal": 0.0}
            total += durasi
            continue
        kal = kalimat_dari(teks)
        if a.uji:
            kata = dara.estimate(kal, f"{dasar:+d}%")
            senyap(out, (kata[-1]["selesai"] if kata else 1.0) + 0.1)
        else:
            tempo, nada = PROSODI.get(ad.get("jenis", "host"), (0, 0))
            kata = asyncio.run(_synth(teks, voice, f"{dasar + tempo:+d}%", f"{nada:+d}Hz", out))
        durasi = round(max(dara.durasi_audio(out), kata[-1]["selesai"] if kata else 0) + pad, 3)
        waktu[str(i)] = {"durasi": durasi, "kata": kata, "kalimat": petakan_kalimat(kal, kata)}
        total += durasi
        log(f"adegan {i + 1:02} ({ad.get('jenis')}): {durasi:.1f} dtk, {len(kata)} kata")
    (sdir / "waktu.json").write_text(json.dumps(waktu, ensure_ascii=False, indent=1), encoding="utf-8")
    st_panjang.set_status(a.slug, "suara", f"{total / 60:.1f} menit")
    log(f"selesai: {len(waktu)} adegan, total {total / 60:.1f} menit → panjang/{a.slug}/suara/")


async def _synth(teks: str, voice: str, rate: str, pitch: str, out: Path) -> list[dict]:
    import edge_tts  # type: ignore
    comm = edge_tts.Communicate(teks, voice, rate=rate, pitch=pitch, boundary="WordBoundary")
    kata: list[dict] = []
    with out.open("wb") as f:
        async for ch in comm.stream():
            if ch["type"] == "audio":
                f.write(ch["data"])
            elif ch["type"] == "WordBoundary":
                s = ch["offset"] / dara.TICKS
                kata.append({"kata": ch["text"], "mulai": round(s, 3), "selesai": round(s + ch["duration"] / dara.TICKS, 3)})
    return kata


if __name__ == "__main__":
    main()

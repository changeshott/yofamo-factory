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
    try:        # suara pilihan Zona di laptop ini (agents/suara/contoh_suara.py --pakai)
        voice = json.loads((ROOT / "bible" / "suara-pilihan.json").read_text(encoding="utf-8")).get("suara_pria") or voice
    except (OSError, ValueError):
        pass
    pad, judul_detik = float(sg.get("jeda_antar_adegan", 0.35)), float(sg.get("judul_bab_detik", 2.6))
    m = re.match(r"([+-]\d+)%", rate)
    dasar = int(m.group(1)) if m else 0
    sdir = vdir / "suara"
    sdir.mkdir(exist_ok=True)
    waktu, total = {}, 0.0
    sys.path.insert(0, str(ROOT / "agents" / "suara"))
    import lafal  # noqa: E402  kamus pelafalan: bible/lafal.json + naskah.json → lafal
    kamus = lafal.kamus(naskah.get("lafal") if isinstance(naskah.get("lafal"), dict) else None)
    # lanjut dari titik terakhir (mis. laptop dimatikan di tengah): adegan yang suaranya sudah jadi dengan narasi sama tidak diulang
    parsial_f = sdir / "waktu.parsial.json"
    try:
        parsial = json.loads(parsial_f.read_text(encoding="utf-8")) if parsial_f.exists() and not a.uji else {}
    except ValueError:
        parsial = {}
    for i, ad in enumerate(naskah["adegan"]):
        out = sdir / f"{i + 1:02}.mp3"
        teks = str(ad.get("narasi") or "").strip()
        lama = parsial.get(str(i))
        if lama and lama.get("teks") == teks and out.exists() and out.stat().st_size > 0:
            waktu[str(i)] = {k: v for k, v in lama.items() if k != "teks"}
            total += float(lama["durasi"])
            continue
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
            kata = asyncio.run(_synth(lafal.ucapkan(teks, kamus), voice, f"{dasar + tempo:+d}%", f"{nada:+d}Hz", out))
            kata = lafal.pulihkan(kata, teks, kamus)
        durasi = round(max(dara.durasi_audio(out), kata[-1]["selesai"] if kata else 0) + pad, 3)
        waktu[str(i)] = {"durasi": durasi, "kata": kata, "kalimat": petakan_kalimat(kal, kata)}
        total += durasi
        log(f"adegan {i + 1:02} ({ad.get('jenis')}): {durasi:.1f} dtk, {len(kata)} kata")
        if not a.uji:
            parsial[str(i)] = {**waktu[str(i)], "teks": teks}
            parsial_f.write_text(json.dumps(parsial, ensure_ascii=False), encoding="utf-8")
    (sdir / "waktu.json").write_text(json.dumps(waktu, ensure_ascii=False, indent=1), encoding="utf-8")
    parsial_f.unlink(missing_ok=True)
    st_panjang.set_status(a.slug, "suara", f"{total / 60:.1f} menit")
    log(f"selesai: {len(waktu)} adegan, total {total / 60:.1f} menit → panjang/{a.slug}/suara/")


async def _synth(teks: str, voice: str, rate: str, pitch: str, out: Path) -> list[dict]:
    sys.path.insert(0, str(ROOT / "agents" / "suara"))
    import tts  # noqa: E402  (batas kata, atau perkiraan dari batas kalimat untuk suara multibahasa)
    return await tts.rekam(teks, voice, rate, pitch, out)


if __name__ == "__main__":
    main()

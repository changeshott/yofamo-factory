#!/usr/bin/env python3
"""Pilih jenis suara (gratis, edge-tts): dengarkan contoh semua suara yang bisa berbahasa Indonesia, lalu pakai yang paling natural.

    python agents/suara/contoh_suara.py                      # buat contoh semua suara → suara-khas/contoh/NN-<nama>.mp3 + DAFTAR.txt
    python agents/suara/contoh_suara.py --teks "kalimat"     # pakai kalimat sendiri
    python agents/suara/contoh_suara.py --pakai en-US-AndrewMultilingualNeural            # suara utama Shorts + video panjang
    python agents/suara/contoh_suara.py --pakai en-US-AvaMultilingualNeural --wanita      # suara untuk pilihan "wanita" (Shorts)
    python agents/suara/contoh_suara.py --lihat              # suara yang sedang dipakai

Kandidat diambil dari daftar suara layanan saat itu juga: suara Indonesia asli (id-ID) + semua suara "Multilingual"
(dibuat untuk banyak bahasa; intonasinya lebih hidup, kadang beraksen sedikit — karena itu didengarkan dulu).
Pilihan disimpan di bible/suara-pilihan.json (khusus laptop ini, tidak di-commit) dan dibaca Dara & Gilang.
Windows: klik dua kali contoh_suara.bat.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).parent))
import pakai_python  # noqa: E402

pakai_python.pastikan("edge_tts")
import lafal  # noqa: E402
import tts  # noqa: E402

PILIHAN = ROOT / "bible" / "suara-pilihan.json"
KELUAR = ROOT / "suara-khas" / "contoh"
TEKS = ("Tau nggak, cincin sekecil ini bisa memantau detak jantung, suhu tubuh, dan kualitas tidur kamu? "
        "Namanya Oura Ring 5, tebalnya cuma dua milimeter, dan baterainya tahan sampai delapan hari!")


def pilihan() -> dict:
    try:
        return json.loads(PILIHAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


async def kandidat() -> list[dict]:
    import edge_tts  # type: ignore
    semua = await edge_tts.list_voices()
    out = [v for v in semua if str(v.get("Locale", "")).startswith("id-")]
    out += sorted((v for v in semua if "Multilingual" in str(v.get("ShortName", ""))), key=lambda v: v["ShortName"])
    return out


async def buat(teks: str) -> None:
    KELUAR.mkdir(parents=True, exist_ok=True)
    baca = lafal.ucapkan(teks, lafal.kamus())
    try:
        ks = await kandidat()
    except Exception as err:  # noqa: BLE001
        sys.exit(f"[suara] daftar suara tidak bisa diambil ({str(err)[:100]}). Cek koneksi internet.")
    import edge_tts  # type: ignore
    print(f"[suara] Python: {sys.executable} · edge-tts {getattr(edge_tts, '__version__', '?')}", flush=True)
    gagal403 = 0
    baris = [f"Contoh suara — kalimat: {teks}", "Dengarkan, lalu pakai yang paling natural:", "    python agents/suara/contoh_suara.py --pakai <nama>", ""]
    for n, v in enumerate(ks, 1):
        nama, jk = v["ShortName"], "wanita" if str(v.get("Gender", "")).lower().startswith("f") else "pria"
        f = KELUAR / f"{n:02d}-{nama}.mp3"
        try:
            kata = await tts.rekam(baca, nama, "+8%", "+0Hz", f, cadangan=None)
            cara = "waktu kata asli" if kata and len(kata) >= len(tts.TOKEN.findall(baca)) * 0.8 else "waktu kata perkiraan"
            baris.append(f"{n:02d}  {nama:38} {jk:7} {tts.durasi(f):5.1f} dtk  ({cara})")
            print(f"[suara] {baris[-1]}", flush=True)
        except Exception as err:  # noqa: BLE001 — satu suara gagal → lanjut
            f.unlink(missing_ok=True)
            gagal403 += "403" in str(err)
            print(f"[suara] {nama}: gagal ({str(err)[:80]})", flush=True)
            if gagal403 >= 2 and n <= 3:      # dua suara pertama ditolak 403 → bukan soal suaranya; berhenti & jelaskan
                print("\n[suara] Layanan suara menolak (403). Ini bukan karena jenis suaranya. Penyebab umum & perbaikannya:\n"
                      "  1. Paket edge-tts di Python ini sudah usang → jalankan:  python -m pip install -U edge-tts\n"
                      "  2. Jam laptop meleset lebih dari beberapa menit → Setelan Windows → Waktu → Sinkronkan sekarang\n"
                      "  3. VPN/proxy aktif → matikan dulu\n"
                      "Lalu jalankan contoh_suara.bat lagi.", flush=True)
                sys.exit(3)
    (KELUAR / "DAFTAR.txt").write_text("\n".join(baris) + "\n", encoding="utf-8")
    print(f"[suara] selesai → {KELUAR.relative_to(ROOT).as_posix()}/ (buka foldernya, dengarkan satu per satu)")


def main() -> None:
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description="Contoh & pilihan jenis suara")
    ap.add_argument("--teks", default=TEKS)
    ap.add_argument("--pakai", default="")
    ap.add_argument("--wanita", action="store_true")
    ap.add_argument("--panjang", action="store_true", help="pakai juga untuk video panjang (bawaan: hanya Shorts, karena video panjang bisa terupload otomatis)")
    ap.add_argument("--lihat", action="store_true")
    a = ap.parse_args()
    if a.lihat:
        p = pilihan()
        print(f"Shorts: {p.get('suara_pria') or 'bawaan (id-ID-ArdiNeural)'} · wanita: {p.get('suara_wanita') or 'bawaan (id-ID-GadisNeural)'} · "
              f"video panjang: {p.get('suara_panjang') or 'bawaan (id-ID-ArdiNeural)'}")
        return
    if a.pakai:
        p = pilihan()
        p["suara_wanita" if a.wanita else "suara_pria"] = a.pakai.strip()
        if a.panjang:
            p["suara_panjang"] = a.pakai.strip()
        PILIHAN.write_text(json.dumps(p, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[suara] {'suara wanita' if a.wanita else 'suara utama Shorts'}{' + video panjang' if a.panjang else ''} sekarang: {a.pakai}. Berlaku untuk video berikutnya.")
        return
    asyncio.run(buat(a.teks))


if __name__ == "__main__":
    main()

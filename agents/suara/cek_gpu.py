#!/usr/bin/env python3
"""Dara: cek apakah laptop siap untuk suara natural VoxCPM2 (GPU NVIDIA) dan mesin video HyperFrames (Node 22).

    python agents/suara/cek_gpu.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "editor"))


def main() -> None:
    print("== Cek mesin Yofamo ==")
    smi = shutil.which("nvidia-smi")
    gpu = ""
    if smi:
        r = subprocess.run([smi, "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True)
        gpu = r.stdout.strip().splitlines()[0] if r.returncode == 0 and r.stdout.strip() else ""
    if gpu:
        nama, mem = [x.strip() for x in gpu.split(",", 1)]
        gb = float("".join(c for c in mem if c.isdigit() or c == ".") or 0) / 1024
        print(f"GPU      : {nama} ({gb:.1f} GB)")
        if gb >= 7.5:
            print("           → cocok untuk VoxCPM2 (suara natural). Jalankan setup_suara.bat")
        elif gb >= 5.5:
            print("           → bisa VoxCPM2 tapi pas-pasan; tutup aplikasi lain saat membuat suara")
        else:
            print("           → VRAM kecil; tetap pakai edge-tts (atau coba VoxCPM2 dengan risiko kehabisan memori)")
    else:
        print("GPU      : tidak ada GPU NVIDIA terdeteksi → suara tetap edge-tts (gratis, online)")
    import mesin_suara
    ok, ket = mesin_suara.siap()
    print(f"Suara    : {'VoxCPM2 SIAP — ' if ok else 'edge-tts (cadangan) — '}{ket}")
    import komposisi
    ok, ket = komposisi.tersedia()
    print(f"Video    : {'HyperFrames SIAP' if ok else 'ffmpeg (cadangan) — ' + ket}")


if __name__ == "__main__":
    main()

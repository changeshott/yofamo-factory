"""Pastikan script agent berjalan di Python yang paketnya lengkap.

Di komputer Zona, `python` pertama di PATH bisa saja venv aplikasi lain (misalnya hermes-agent)
yang tidak punya edge-tts / yt-dlp. Studio dan produser.py menaruh Python yang benar di
YOFAMO_PYTHON; kalau script dijalankan Claude dengan python yang salah, script menjalankan
dirinya sendiri ulang dengan Python itu.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def pastikan(*modul: str) -> None:
    if all(importlib.util.find_spec(m) for m in modul):
        return
    alt = os.environ.get("YOFAMO_PYTHON", "")
    if not alt or not Path(alt).is_file() or Path(alt).resolve() == Path(sys.executable).resolve():
        return  # tidak ada pengganti; script sendiri yang memberi pesan error
    print(f"[python] {sys.executable} tidak punya {', '.join(modul)}; pindah ke {alt}", flush=True)
    sys.exit(subprocess.run([alt, sys.argv[0], *sys.argv[1:]]).returncode)

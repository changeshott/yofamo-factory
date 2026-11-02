"""Windows: semua proses anak (claude, python, ffmpeg, node) berjalan TANPA jendela console.

Autopilot dijalankan Studio/Task Scheduler di latar belakang (tanpa console). Tanpa ini, setiap program console
yang dijalankannya membuka jendela baru (judulnya "claude"), dan kalau jendela itu ditutup, produksinya ikut mati.
Cukup di-import sekali di awal script; cucu proses ikut memakai console tersembunyi yang sama.
"""
from __future__ import annotations

import os
import subprocess

CREATE_NO_WINDOW = 0x08000000

if os.name == "nt" and not getattr(subprocess, "_yofamo_tanpa_jendela", False):
    _Asli = subprocess.Popen

    class _PopenTanpaJendela(_Asli):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            if not kwargs.get("creationflags"):
                kwargs["creationflags"] = CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _PopenTanpaJendela  # type: ignore[misc]
    subprocess._yofamo_tanpa_jendela = True  # type: ignore[attr-defined]

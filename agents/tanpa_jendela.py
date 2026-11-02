"""Windows: semua proses anak (claude, python, ffmpeg, node) berjalan TANPA jendela console.

Cara utama: Studio & Task Scheduler menjalankan autopilot/video panjang lewat latar.vbs (console tersembunyi), sehingga
semua proses anak memakai console tersembunyi yang sama dan keluarannya tetap masuk log. Modul ini hanya cadangan:
kalau proses ini TIDAK punya console sama sekali (dijalankan terlepas), proses anak diberi CREATE_NO_WINDOW supaya
tidak membuka jendela "claude" (yang kalau ditutup ikut mematikan produksi).
"""
from __future__ import annotations

import os
import subprocess

CREATE_NO_WINDOW = 0x08000000

def _tanpa_console() -> bool:
    try:
        import ctypes
        return ctypes.windll.kernel32.GetConsoleCP() == 0     # 0 = proses ini tidak punya console
    except (OSError, AttributeError):
        return False


if os.name == "nt" and not getattr(subprocess, "_yofamo_tanpa_jendela", False) and _tanpa_console():
    _Asli = subprocess.Popen

    class _PopenTanpaJendela(_Asli):  # type: ignore[misc, valid-type]
        def __init__(self, *args, **kwargs):
            if not kwargs.get("creationflags"):
                kwargs["creationflags"] = CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)

    subprocess.Popen = _PopenTanpaJendela  # type: ignore[misc]
    subprocess._yofamo_tanpa_jendela = True  # type: ignore[attr-defined]


def prioritas_rendah() -> None:
    """Proses ini (dan semua anaknya) memakai prioritas CPU rendah — dipakai video panjang supaya produksi Shorts
    tetap didahulukan saat laptop dipakai bersamaan."""
    try:
        if os.name == "nt":
            import ctypes
            ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x00004000)  # BELOW_NORMAL
        else:
            os.nice(10)
    except (OSError, AttributeError):
        pass

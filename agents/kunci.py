"""Kunci proses sederhana (file berisi PID) supaya dua produksi/autopilot tidak berjalan bersamaan.

Kunci yang ditinggalkan proses yang sudah mati (mis. dihentikan paksa) otomatis diambil alih.
"""
from __future__ import annotations

import atexit
import json
import os
import time
from pathlib import Path


def hidup(pid: int) -> bool:
    """Apakah proses dengan PID ini masih berjalan. Windows: os.kill(pid, 0) justru MEMATIKAN proses, jadi pakai WinAPI."""
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes
        k32 = ctypes.windll.kernel32
        h = k32.OpenProcess(0x1000, False, pid)          # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        kode = ctypes.c_ulong()
        ok = k32.GetExitCodeProcess(h, ctypes.byref(kode))
        k32.CloseHandle(h)
        return bool(ok) and kode.value == 259             # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Kunci:
    def __init__(self, path: Path, maks_jam: float = 6.0):
        self.path, self.maks, self.punya = Path(path), maks_jam * 3600, False

    def pemilik(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def sibuk(self) -> bool:
        d = self.pemilik()
        return bool(d) and hidup(int(d.get("pid", 0))) and time.time() - float(d.get("mulai", 0)) < self.maks

    def ambil(self, nama: str = "") -> bool:
        if self.sibuk():
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"pid": os.getpid(), "mulai": time.time(), "nama": nama}), encoding="utf-8")
        self.punya = True
        atexit.register(self.lepas)
        return True

    def lepas(self) -> None:
        if self.punya and self.pemilik().get("pid") == os.getpid():
            try:
                self.path.unlink()
            except OSError:
                pass
        self.punya = False

"""Dara: mesin suara natural (VoxCPM2) yang berjalan di Python khusus suara (.venv-suara).

Dipakai buat_suara.py. Edge-tts tetap jadi cadangan otomatis kalau mesin ini belum dipasang / tidak ada GPU.
Pasang sekali di Windows: setup_suara.bat (lihat SETUP.md). Cek kesiapan: python agents/suara/cek_gpu.py
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KONFIG = ROOT / "bible" / "gaya-suara.json"
SUARA_KHAS = ROOT / "suara-khas"
DEFAULT = {
    "mesin": "auto",
    "voxcpm": {
        "desain_pria": "(A young Indonesian man in his twenties, warm, energetic and curious tech YouTuber, clear articulation, lively fast pace, expressive and natural)",
        "desain_wanita": "(A young Indonesian woman in her twenties, bright, friendly and energetic tech YouTuber, clear articulation, lively pace, expressive and natural)",
        "ref_teks": "Tau nggak, teknologi yang dulu cuma ada di film fiksi ilmiah, sekarang sudah benar-benar ada. Ini Yofamo Technology.",
        "cfg": 2.0, "langkah": 10, "seed": 42, "jeda": 0.1, "jeda_hook": 0.18, "perangkat": "auto", "wajib_gpu": True,
    },
    "edge": {"suara_pria": "id-ID-ArdiNeural", "suara_wanita": "id-ID-GadisNeural", "kecepatan": "+15%"},
}


def konfig() -> dict:
    try:
        user = json.loads(KONFIG.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        user = {}
    out = json.loads(json.dumps(DEFAULT))
    for k, v in user.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def py_suara() -> str | None:
    env = os.environ.get("YOFAMO_PY_SUARA", "").strip()
    for p in [env, ROOT / ".venv-suara" / "Scripts" / "python.exe", ROOT / ".venv-suara" / "bin" / "python"]:
        if p and Path(p).exists():
            return str(p)
    return None


def siap() -> tuple[bool, str]:
    """(bisa dipakai, keterangan). Cek: Python suara ada, paket voxcpm terpasang, GPU NVIDIA (kecuali wajib_gpu=false)."""
    py = py_suara()
    if not py:
        return False, "mesin suara natural belum dipasang (jalankan setup_suara.bat)"
    kode = ("import importlib.util as u, json, torch; print(json.dumps({'vox': u.find_spec('voxcpm') is not None, "
            "'cuda': torch.cuda.is_available(), 'gpu': torch.cuda.get_device_name(0) if torch.cuda.is_available() else '', "
            "'vram': round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1) if torch.cuda.is_available() else 0, "
            "'asr': u.find_spec('faster_whisper') is not None}))")
    try:
        r = subprocess.run([py, "-c", kode], capture_output=True, text=True, timeout=120)
        info = json.loads(r.stdout.strip().splitlines()[-1])
    except (OSError, ValueError, IndexError, subprocess.TimeoutExpired):
        return False, "Python suara rusak / torch belum terpasang"
    if not info.get("vox"):
        return False, "paket voxcpm belum terpasang di .venv-suara"
    if not info.get("cuda") and konfig()["voxcpm"].get("wajib_gpu", True):
        return False, "tidak ada GPU NVIDIA (CUDA) — VoxCPM2 terlalu lambat di CPU"
    return True, f"GPU {info.get('gpu')} {info.get('vram')} GB" + ("" if info.get("asr") else " (tanpa faster-whisper: timing kata diperkirakan)")


def buat(kalimat: list[str], suara: str, rate: str, vo_mp3: Path) -> list[dict]:
    """Membuat vo.mp3 dengan VoxCPM2; mengembalikan timing kata [{kata, mulai, selesai}] untuk seluruh audio."""
    c = konfig()["voxcpm"]
    py = py_suara()
    if not py:
        raise RuntimeError("Python suara tidak ditemukan")
    jenis = "wanita" if "gadis" in suara.lower() or suara == "wanita" else "pria"
    ref = SUARA_KHAS / f"yofamo-{jenis}.wav"
    with tempfile.TemporaryDirectory(prefix="dara-") as td:
        td_p = Path(td)
        tugas = {"kalimat": kalimat, "keluar": str(td_p / "wav"), "ref_wav": str(ref), "ref_teks": c["ref_teks"],
                 "desain": c[f"desain_{jenis}"], "cfg": c["cfg"], "langkah": c["langkah"], "seed": c["seed"],
                 "perangkat": c["perangkat"], "selaraskan": True}
        (td_p / "tugas.json").write_text(json.dumps(tugas, ensure_ascii=False), encoding="utf-8")
        r = subprocess.run([py, str(Path(__file__).with_name("voxcpm_kerja.py")), "--tugas", str(td_p / "tugas.json")], cwd=ROOT)
        hasil_p = td_p / "wav" / "hasil.json"
        if r.returncode != 0 or not hasil_p.exists():
            raise RuntimeError("VoxCPM2 gagal membuat suara")
        hasil = json.loads(hasil_p.read_text(encoding="utf-8"))
        # tempo: edge-tts dasar +15% = suara natural VoxCPM apa adanya
        m = re.fullmatch(r"([+-]\d{1,2})%", rate)
        tempo = max(0.85, min(1.25, (100 + int(m.group(1) if m else 15)) / 115))
        args, rantai, kata, t = [], [], [], 0.0
        for i, k in enumerate(hasil["kalimat"]):
            args += ["-i", str(td_p / "wav" / k["file"])]
            jeda = float(c["jeda_hook"] if i == 0 else c["jeda"]) if i + 1 < len(hasil["kalimat"]) else 0.25
            rantai.append(f"[{i}:a]aresample=48000,aformat=channel_layouts=mono,apad=pad_dur={jeda:.2f}[a{i}]")
            for w, m0, m1 in k["kata"]:
                kata.append({"kata": w, "mulai": round((t + m0) / tempo, 3), "selesai": round((t + m1) / tempo, 3)})
            t += float(k["durasi"]) + jeda
        n = len(hasil["kalimat"])
        rantai.append("".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,atempo={tempo:.4f},"
                      "highpass=f=70,acompressor=threshold=-20dB:ratio=3:attack=5:release=80,loudnorm=I=-16:TP=-1.5[o]")
        tmp = vo_mp3.with_suffix(".tmp.mp3")
        ff = shutil.which("ffmpeg") or "ffmpeg"
        r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", ";".join(rantai), "-map", "[o]",
                            "-c:a", "libmp3lame", "-b:a", "192k", str(tmp)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg gagal menggabung suara: {r.stderr[-300:]}")
        tmp.replace(vo_mp3)
    return kata

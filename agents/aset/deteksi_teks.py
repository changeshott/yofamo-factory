#!/usr/bin/env python3
"""Pendeteksi teks di footage (gratis, lokal): subtitle tertempel, judul, watermark, tulisan besar.

Dipakai Rara (pra-periksa Shorts) dan Bima versi 16:9 (video panjang): klip YouTube/stok yang ADA TULISAN di dalam
videonya ditolak supaya tidak bertabrakan dengan subtitle & teks Yofamo.

    python agents/aset/deteksi_teks.py <video.mp4|gambar.jpg> [...]     # laporan per file
    python agents/aset/deteksi_teks.py --siapkan                        # pasang model sekali (otomatis juga saat dipakai)

Model: detektor teks PP-OCRv3 (±2,4 MB, dari paket rapidocr-onnxruntime yang dipasang TANPA dependensi berat)
dijalankan dengan onnxruntime (sudah terpasang bersama rembg). Hanya MENDETEKSI letak teks, tidak membaca isinya.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_SESI: dict = {}
PAKET = ["rapidocr-onnxruntime==1.2.3"]


def log(m: str) -> None:
    print(f"[teks] {m}", flush=True)


def _model() -> Path | None:
    try:
        import importlib.util
        s = importlib.util.find_spec("rapidocr_onnxruntime")
        if s and s.origin:
            p = Path(s.origin).parent / "models" / "ch_PP-OCRv3_det_infer.onnx"
            return p if p.exists() else None
    except (ImportError, ValueError):
        return None
    return None


def pasang() -> bool:
    """Pasang model sekali (Zona mengizinkan pemasangan otomatis). Gagal → dicoba lagi besok."""
    import importlib
    tanda = ROOT / "produksi" / "ocr-gagal.json"
    try:
        g = json.loads(tanda.read_text(encoding="utf-8"))
        if time.time() - float(g.get("waktu", 0)) < 20 * 3600:
            return False
    except (OSError, ValueError):
        pass
    perlu = [] if _bisa_import("onnxruntime") else ["onnxruntime"]
    log("memasang pendeteksi teks (sekali, ±3 MB)…")
    r1 = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-deps", *PAKET],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20 * 60)
    r2 = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check", *perlu],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20 * 60) if perlu else r1
    importlib.invalidate_caches()
    if _model() and _bisa_import("onnxruntime"):
        tanda.unlink(missing_ok=True)
        return True
    (ROOT / "produksi").mkdir(exist_ok=True)
    tanda.write_text(json.dumps({"waktu": time.time(), "pesan": ((r1.stderr or "") + (r2.stderr or ""))[-600:]}), encoding="utf-8")
    log("pendeteksi teks gagal dipasang; dicoba lagi besok")
    return False


def _bisa_import(nama: str) -> bool:
    try:
        __import__(nama)
        return True
    except ImportError:
        return False


def sesi():
    if "s" in _SESI:
        return _SESI["s"]
    _SESI["s"] = None
    m = _model()
    if not m or not _bisa_import("onnxruntime"):
        if not pasang():
            return None
        m = _model()
    try:
        import onnxruntime as ort
        o = ort.SessionOptions()
        o.log_severity_level = 3
        _SESI["s"] = ort.InferenceSession(str(m), o, providers=["CPUExecutionProvider"])
    except Exception as err:  # noqa: BLE001
        log(f"model teks tidak bisa dimuat: {str(err)[:120]}")
    return _SESI["s"]


def teks_gambar(im) -> dict | None:
    """Letak teks pada satu gambar (PIL). {luas: porsi area teks, kotak: jumlah, bawah: porsi teks di 35% bawah,
    besar: kotak teks terbesar (porsi tinggi gambar)}. None kalau detektor belum siap."""
    import numpy as np
    s = sesi()
    if s is None:
        return None
    from scipy import ndimage
    im = im.convert("RGB")
    w0, h0 = im.size
    k = 736 / min(w0, h0)
    w, h = max(32, int(round(w0 * k / 32)) * 32), max(32, int(round(h0 * k / 32)) * 32)
    if max(w, h) > 1600:
        f = 1600 / max(w, h)
        w, h = max(32, int(w * f) // 32 * 32), max(32, int(h * f) // 32 * 32)
    a = np.asarray(im.resize((w, h)), dtype=np.float32)[:, :, ::-1] / 255.0          # BGR seperti cv2
    a = (a - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    peta = s.run(None, {s.get_inputs()[0].name: a.transpose(2, 0, 1)[None]})[0][0, 0]
    biner = ndimage.binary_dilation(peta > 0.3, iterations=2)
    lab, n = ndimage.label(biner)
    luas, bawah, besar, jumlah = 0.0, 0.0, 0.0, 0
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        bagian = lab[sl] == i
        skor = float(peta[sl][bagian].mean())
        tinggi, lebar = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if skor < 0.6 or tinggi < 6 or lebar < 10 or lebar < tinggi * 1.8:     # baris teks itu melebar; tekstur/benda kotak bukan teks
            continue
        jumlah += 1
        porsi = bagian.sum() / (w * h)
        luas += porsi
        if sl[0].start >= h * 0.65:
            bawah += porsi
        besar = max(besar, tinggi / h)
    return {"luas": round(luas, 4), "kotak": jumlah, "bawah": round(bawah, 4), "besar": round(besar, 3)}


def ada_teks(r: dict | None, ketat: bool = True) -> str | None:
    """Alasan penolakan, atau None kalau bersih. Subtitle/teks di bawah & teks besar = tolak; tulisan kecil di benda boleh."""
    if not r:
        return None
    if r["bawah"] >= 0.002 and r["kotak"] >= 1:
        return "ada subtitle/tulisan di bagian bawah"
    if r["besar"] >= 0.06 or r["luas"] >= (0.006 if ketat else 0.012):
        return "ada tulisan besar di video"
    return None


def cek_video(path: Path, titik: tuple[float, ...] = (0.2, 0.5, 0.8)) -> tuple[str | None, list[dict]]:
    """Ambil beberapa frame; ditolak kalau ≥ 2 frame (atau satu-satunya frame) bertulisan."""
    from PIL import Image
    if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        r = teks_gambar(Image.open(path))
        return ada_teks(r), [r] if r else []
    dur = _durasi(path) or 1.0
    hasil, alasan = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for n, t in enumerate(titik):
            jpg = Path(tmp) / f"f{n}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * t:.2f}", "-i", str(path), "-frames:v", "1", "-vf", "scale=-2:720", str(jpg)],
                           capture_output=True)
            if not jpg.exists():
                continue
            r = teks_gambar(Image.open(jpg))
            if r is None:
                return None, []
            hasil.append(r)
            if (a := ada_teks(r)):
                alasan.append(a)
    if hasil and len(alasan) >= min(2, len(hasil)):
        return alasan[0], hasil
    return None, hasil


def _durasi(p: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(p)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


if __name__ == "__main__":
    if "--siapkan" in sys.argv:
        sys.exit(0 if sesi() is not None else 1)
    for f in sys.argv[1:]:
        a, r = cek_video(Path(f))
        print(f"{f}: {'TOLAK — ' + a if a else 'bersih'}  {json.dumps(r)}")

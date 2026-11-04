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


def teks_gambar(im, halus: bool = False) -> dict | None:
    """Letak teks pada satu gambar (PIL). {luas: porsi area teks, kotak: jumlah, bawah: porsi teks di 35% bawah,
    besar: kotak teks terbesar (porsi tinggi gambar), kecil: baris teks kecil yang bertumpuk (label nama, papan, watermark)}.
    halus=True: dianalisis di 1080p (video panjang 16:9) supaya tulisan kecil ikut terlihat. None kalau detektor belum siap."""
    import numpy as np
    s = sesi()
    if s is None:
        return None
    from scipy import ndimage
    im = im.convert("RGB")
    w0, h0 = im.size
    k = (1080 if halus else 736) / min(w0, h0)
    w, h = max(32, int(round(w0 * k / 32)) * 32), max(32, int(round(h0 * k / 32)) * 32)
    if max(w, h) > (1984 if halus else 1600):
        f = (1984 if halus else 1600) / max(w, h)
        w, h = max(32, int(w * f) // 32 * 32), max(32, int(h * f) // 32 * 32)
    a = np.asarray(im.resize((w, h)), dtype=np.float32)[:, :, ::-1] / 255.0          # BGR seperti cv2
    a = (a - np.array([0.485, 0.456, 0.406], np.float32)) / np.array([0.229, 0.224, 0.225], np.float32)
    peta = s.run(None, {s.get_inputs()[0].name: a.transpose(2, 0, 1)[None]})[0][0, 0]
    biner = ndimage.binary_dilation(peta > 0.3, iterations=2)
    lab, n = ndimage.label(biner)
    luas, bawah, besar, jumlah = 0.0, 0.0, 0.0, 0
    kecil_kotak: list[tuple[int, int, int, int]] = []
    pojok = 0
    for i, sl in enumerate(ndimage.find_objects(lab), 1):
        if sl is None:
            continue
        bagian = lab[sl] == i
        skor = float(peta[sl][bagian].mean())
        tinggi, lebar = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if skor < 0.6 or tinggi < 6 or lebar < 10 or lebar < tinggi * 1.8:     # baris teks itu melebar; tekstur/benda kotak bukan teks
            continue
        if halus and tinggi <= h * 0.035 and lebar >= tinggi * 2.5:
            kecil_kotak.append((sl[0].start, sl[0].stop, sl[1].start, sl[1].stop))
            cx, cy = (sl[1].start + sl[1].stop) / 2 / w, (sl[0].start + sl[0].stop) / 2 / h
            if skor >= 0.65 and (cx < 0.2 or cx > 0.8) and (cy < 0.15 or cy > 0.85):
                pojok += 1                                                     # watermark/logo teks di pojok
        jumlah += 1
        porsi = bagian.sum() / (w * h)
        luas += porsi
        if sl[0].start >= h * 0.65:
            bawah += porsi
        besar = max(besar, tinggi / h)
    # baris kecil yang bertumpuk (≥ 2 baris saling berdekatan & sejajar) = tulisan sungguhan, bukan tekstur acak
    kecil = set()
    for a_, (y0, y1, x0, x1) in enumerate(kecil_kotak):
        for b_, (v0, v1, u0, u1) in enumerate(kecil_kotak[a_ + 1:], a_ + 1):
            tumpang = min(x1, u1) - max(x0, u0)
            jarak = max(v0 - y1, y0 - v1)
            if tumpang >= 0.3 * min(x1 - x0, u1 - u0) and jarak <= 2.5 * max(y1 - y0, v1 - v0):
                kecil.update((a_, b_))
    return {"luas": round(luas, 4), "kotak": jumlah, "bawah": round(bawah, 4), "besar": round(besar, 3), "kecil": len(kecil), "pojok": pojok}


def ada_teks(r: dict | None, ketat: bool = True) -> str | None:
    """Alasan penolakan, atau None kalau bersih. Subtitle/teks di bawah & teks besar = tolak; tulisan kecil di benda boleh."""
    if not r:
        return None
    if r["bawah"] >= 0.002 and r["kotak"] >= 1:
        return "ada subtitle/tulisan di bagian bawah"
    if r["besar"] >= 0.06 or r["luas"] >= (0.006 if ketat else 0.012):
        return "ada tulisan besar di video"
    if r.get("kecil", 0) >= 2:
        return "ada tulisan kecil (label nama/papan/watermark)"
    return None


def cek_video(path: Path, titik: tuple[float, ...] = (0.2, 0.5, 0.8), halus: bool = False) -> tuple[str | None, list[dict]]:
    """Ambil beberapa frame; ditolak kalau ≥ 2 frame (atau satu-satunya frame) bertulisan.
    halus=True (video panjang): analisis 1080p + tulisan kecil bertumpuk di SATU frame saja sudah cukup untuk menolak."""
    from PIL import Image
    path = Path(path)
    if path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
        im = Image.open(path)
        r = teks_gambar(im)
        if r is not None and halus:
            r2 = teks_gambar(im, True) or {}
            r["kecil"], r["pojok"] = r2.get("kecil", 0), r2.get("pojok", 0)
        return ada_teks(r), [r] if r else []
    dur = _durasi(path) or 1.0
    if halus and titik == (0.2, 0.5, 0.8):
        titik = (0.1, 0.3, 0.5, 0.7, 0.9)          # tulisan kecil sering hanya terlihat sebentar saat kamera bergerak
    hasil, alasan = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for n, t in enumerate(titik):
            jpg = Path(tmp) / f"f{n}.jpg"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{dur * t:.2f}", "-i", str(path), "-frames:v", "1", "-q:v", "2", "-vf", f"scale=-2:{1080 if halus else 720}", str(jpg)],
                           capture_output=True)
            if not jpg.exists():
                continue
            im = Image.open(jpg)
            r = teks_gambar(im)                      # aturan subtitle/tulisan besar: dikalibrasi di 736p
            if r is None:
                return None, []
            if halus:                                # tulisan kecil bertumpuk & watermark pojok: perlu 1080p
                r2 = teks_gambar(im, True) or {}
                r["kecil"], r["pojok"] = r2.get("kecil", 0), r2.get("pojok", 0)
            hasil.append(r)
            if (a := ada_teks(r)):
                if r.get("kecil", 0) >= 2 and a.startswith("ada tulisan kecil"):
                    return a, hasil
                alasan.append(a)
    if hasil and len(alasan) >= min(2, len(hasil)):
        return alasan[0], hasil
    if halus and sum(1 for r in hasil if r.get("pojok", 0) >= 1) >= max(2, len(hasil) // 2 + 1):
        return "ada watermark/tulisan di pojok video", hasil
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
    halus = "--halus" in sys.argv
    for f in [x for x in sys.argv[1:] if not x.startswith("--")]:
        a, r = cek_video(Path(f), halus=halus)
        print(f"{f}: {'TOLAK — ' + a if a else 'bersih'}  {json.dumps(r)}")

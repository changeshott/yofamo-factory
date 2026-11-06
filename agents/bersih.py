#!/usr/bin/env python3
"""Bersih-bersih penyimpanan Yofamo (permintaan Zona): file besar yang sudah tidak diperlukan dihapus otomatis.

    python agents/bersih.py video <slug>      # satu video yang SUDAH diupload: hapus file besarnya
    python agents/bersih.py semua             # semua video yang sudah diupload + cache lama + file sementara
    python agents/bersih.py semua --coba      # hanya tampilkan apa yang akan dihapus & ruang yang kembali

Yang dihapus dari video yang sudah diupload (videonya aman di YouTube, bisa diunduh lagi dari YouTube Studio):
  export/final.mp4, base.mp4, folder hf/ (salinan render), lembar frame QC, shot aset/NN-x.mp4, lembar kontak, vo.mp3.
Yang DISIMPAN (kecil, dipakai Steve untuk belajar & post-mortem, dan untuk kredit):
  idea.json, script.json, naskah.md, words.json, transkrip.txt, captions.srt, aset/manifest.json, KREDIT.txt,
  export/info.json, upload.json, qc.json, qc_review.json, sampul.jpg, thumbnail.jpg.
Lainnya: cache unduhan footage lebih tua dari cache_maks_hari (atau melebihi cache_maks_gb), file sementara *_tmp.py
di logs/, log & catatan produksi lebih tua dari log_maks_hari. Video yang belum diupload TIDAK pernah disentuh.
Pengaturan: bible/penyimpanan.json.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIDEOS = ROOT / "videos"
CACHE = ROOT / "cache" / "aset"
CONFIG = ROOT / "bible" / "penyimpanan.json"
SIMPAN_EXPORT = {"info.json", "upload.json", "qc.json", "qc_review.json", "sampul.jpg", "thumbnail.jpg"}
SIMPAN_ASET = {"manifest.json", "KREDIT.txt", "kredit_deskripsi.txt", "rencana.json", "pilihan.json", "kandidat.json", "tolak.json"}
HAPUS_VIDEO_ROOT = {"vo.mp3", "vo_mentah.mp3"}
COBA = False


def log(msg: str) -> None:
    print(f"[bersih] {msg}", flush=True)


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def cfg() -> dict:
    c = rj(CONFIG)
    return {"aktif": bool(c.get("hapus_setelah_upload", True)), "cache_hari": float(c.get("cache_maks_hari", 3)),
            "cache_gb": float(c.get("cache_maks_gb", 3)), "log_hari": float(c.get("log_maks_hari", 30))}


_DIHITUNG: set[tuple[int, int]] = set()


def ukuran(p: Path) -> int:
    """Byte yang benar-benar kembali: file hardlink (base.mp4 ↔ hf/assets/base.mp4) dihitung sekali."""
    total = 0
    for f in ([p] if p.is_file() else p.rglob("*") if p.is_dir() else []):
        if f.is_file():
            st = f.stat()
            if (st.st_dev, st.st_ino) not in _DIHITUNG:
                _DIHITUNG.add((st.st_dev, st.st_ino))
                total += st.st_size
    return total


def hapus(p: Path) -> int:
    if not p.exists():
        return 0
    n = ukuran(p)
    if not COBA:
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                p.unlink()
            except OSError:
                return 0
    return n


def sudah_upload(slug: str) -> bool:
    up = rj(VIDEOS / slug / "export" / "upload.json")
    return bool(up.get("videoId")) and up.get("videoId") != "UJI"


def bersih_video(slug: str) -> int:
    """File besar satu video yang sudah diupload. Kembalikan byte yang dibebaskan."""
    vdir = VIDEOS / slug
    if not re.fullmatch(r"[a-z0-9-]{3,80}", slug) or not vdir.is_dir():
        log(f"{slug}: video tidak ditemukan")
        return 0
    if not sudah_upload(slug):
        log(f"{slug}: belum diupload ke YouTube, tidak disentuh")
        return 0
    n = 0
    exp = vdir / "export"
    for f in (exp.iterdir() if exp.is_dir() else []):
        if f.name not in SIMPAN_EXPORT:
            n += hapus(f)
    aset = vdir / "aset"
    for f in (aset.iterdir() if aset.is_dir() else []):
        if f.name not in SIMPAN_ASET:
            n += hapus(f)
    for nama in HAPUS_VIDEO_ROOT:
        n += hapus(vdir / nama)
    if n and not COBA:
        info = rj(exp / "info.json")
        info["file_dihapus"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        (exp / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    if n:
        log(f"{slug}: {n / 1048576:.0f} MB {'akan ' if COBA else ''}dibebaskan (video aman di YouTube)")
    return n


def bersih_panjang() -> int:
    """Video panjang yang sudah diupload: hapus final.mp4, render adegan, proyek HyperFrames, suara, shot footage; simpan naskah,
    ilustrasi/objek (kecil, bisa dipakai ulang), manifest & kredit footage, timing, info, bab, subtitle, thumbnail, upload."""
    base = ROOT / "panjang"
    n = 0
    for v in sorted(base.iterdir()) if base.is_dir() else []:
        up = rj(v / "export" / "upload.json")
        if not v.is_dir() or not up.get("videoId") or up.get("videoId") == "UJI":
            continue
        m = 0
        for d in ("adegan", "hf"):
            m += hapus(v / d)
        m += hapus(v / "export" / "final.mp4")
        for f in (v / "suara").glob("*.mp3") if (v / "suara").is_dir() else []:
            m += hapus(f)
        for f in (v / "footage").glob("*.mp4") if (v / "footage").is_dir() else []:      # shot footage (manifest & kredit tetap)
            m += hapus(f)
        if m:
            log(f"panjang/{v.name}: {m / 1048576:.0f} MB {'akan ' if COBA else ''}dibebaskan (video aman di YouTube)")
        n += m
    return n


def bersih_cache(c: dict) -> int:
    if not CACHE.is_dir():
        return 0
    batas = time.time() - c["cache_hari"] * 86400
    files = sorted((f for f in CACHE.iterdir() if f.is_file()), key=lambda f: f.stat().st_mtime)
    n = 0
    total = sum(f.stat().st_size for f in files)
    for f in files:
        terlalu_besar = total > c["cache_gb"] * 1024 ** 3
        if f.stat().st_mtime < batas or (terlalu_besar and f.stat().st_mtime < time.time() - 3600):
            b = hapus(f)
            n += b
            total -= b
    if n:
        log(f"cache unduhan: {n / 1048576:.0f} MB {'akan ' if COBA else ''}dibebaskan")
    return n


def bersih_lain(c: dict) -> int:
    n = 0
    logs = ROOT / "logs"
    batas = time.time() - c["log_hari"] * 86400
    for f in (logs.iterdir() if logs.is_dir() else []):
        if f.is_file() and (f.name.endswith("_tmp.py") or (f.suffix == ".txt" and f.stat().st_mtime < batas)):
            n += hapus(f)
    prod = ROOT / "produksi"
    for f in (prod.glob("*.json") if prod.is_dir() else []):
        if f.name not in ("autopilot.json", "autopilot-panjang.json", "youtube-izin.json", "notif.json") and f.stat().st_mtime < batas:
            n += hapus(f)
    for f in (prod.glob("*.tmp") if prod.is_dir() else []):
        n += hapus(f)
    return n


def main() -> None:
    global COBA
    ap = argparse.ArgumentParser(description="Bersihkan file yang sudah tidak diperlukan")
    ap.add_argument("perintah", choices=["video", "semua"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--coba", action="store_true", help="hanya tampilkan, tidak menghapus")
    ap.add_argument("--otomatis", action="store_true", help="dipanggil Uli/autopilot: patuhi hapus_setelah_upload")
    a = ap.parse_args()
    COBA = a.coba
    c = cfg()
    if a.otomatis and not c["aktif"]:
        return
    if a.perintah == "video":
        if not a.slug:
            sys.exit("[bersih] sebutkan slug video")
        bersih_video(a.slug)
        return
    total = 0
    for d in sorted(VIDEOS.iterdir()) if VIDEOS.is_dir() else []:
        if d.is_dir() and sudah_upload(d.name):
            total += bersih_video(d.name)
    total += bersih_panjang()
    total += bersih_cache(c)
    total += bersih_lain(c)
    log(f"total {total / 1048576:.0f} MB {'akan ' if COBA else ''}dibebaskan")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Wulan (QC) — pemeriksaan otomatis video panjang sebelum ditonton Zona.

    python agents/panjang/periksa_panjang.py <slug>

Cek: resolusi 1920x1080, durasi sesuai target (dokumenter 5–12 menit, kartun 6–10), layar hitam lama, kerasnya suara (-14 LUFS),
chapter ≥ 3, thumbnail ada, adegan tanpa ilustrasi (kartun) / adegan yang meminjam footage adegan lain (dokumenter).
Membuat lembar frame tengah tiap adegan (export/lembar.jpg) → export/qc.json dengan skor 0–10
(dipakai autopilot video panjang untuk menyetujui otomatis: lolos + skor ≥ skor_qc_min).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
from rakit_panjang import durasi, ff, lufs  # noqa: E402


def log(msg: str) -> None:
    print(f"[wulan] {msg}", flush=True)


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("pakai: periksa_panjang.py <slug>")
    slug = sys.argv[1]
    vdir = st_panjang.folder(slug)
    exp = vdir / "export"
    final = exp / "final.mp4"
    if not final.exists():
        sys.exit("[wulan] export/final.mp4 belum ada")
    naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    dok = naskah.get("format") == "dokumenter"
    gf = ROOT / "bible" / ("gaya-dokumenter.json" if dok else "gaya-animasi.json")
    g = json.loads(gf.read_text(encoding="utf-8")) if gf.exists() else {}
    if dok:
        g.setdefault("durasi_menit", [5, 12])
    masalah, catatan = [], []
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0", str(final)], capture_output=True, text=True)
    if r.stdout.strip() != "1920,1080":
        masalah.append(f"resolusi {r.stdout.strip()} (harus 1920x1080)")
    d = durasi(final)
    lo, hi = [m * 60 for m in g.get("durasi_menit", [6, 10])]
    if not lo * 0.85 <= d <= hi * 1.15:
        masalah.append(f"durasi {d / 60:.1f} menit (target {lo / 60:.0f}–{hi / 60:.0f} menit)")
    bd = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(final), "-vf", "blackdetect=d=1.5:pic_th=0.95", "-an", "-f", "null", "-"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    hitam = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", bd)
    if hitam:
        masalah.append("layar hitam ≥ 1,5 dtk di " + ", ".join(f"{float(a):.0f}s" for a, _ in hitam[:5]))
    l = lufs(final)
    if l is not None and not -16 <= l <= -12:
        masalah.append(f"kerasnya suara {l:.1f} LUFS (target -14)")
    info = json.loads((exp / "info.json").read_text(encoding="utf-8")) if (exp / "info.json").exists() else {}
    if len(info.get("bab", [])) < 3:
        catatan.append("chapter kurang dari 3 (YouTube butuh ≥ 3 untuk menampilkan bab)")
    if not (exp / "thumbnail.jpg").exists():
        masalah.append("thumbnail belum ada")
    tanpa = [i + 1 for i, a in enumerate(naskah["adegan"]) if a.get("jenis") == "ilustrasi" and not (vdir / "ilustrasi" / f"{i + 1:02}.jpg").exists()]
    if tanpa:
        catatan.append(f"adegan tanpa ilustrasi (memakai kartu teks): {tanpa[:10]}")
    if dok:
        try:
            man = json.loads((vdir / "footage" / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            man = {}
        pinjam = sorted(int(k) + 1 for k, v in man.items() if v and all(x.get("cadangan") for x in v))
        maks = int((g.get("qc") or {}).get("maks_adegan_cadangan", 3))
        if len(pinjam) > maks:
            masalah.append(f"{len(pinjam)} adegan memakai footage pinjaman adegan lain: {pinjam[:10]}")
        elif pinjam:
            catatan.append(f"adegan memakai footage pinjaman adegan lain: {pinjam}")
    # lembar frame: tengah tiap adegan, 6 kolom
    mulai, t = [], 0.0
    for i in range(len(naskah["adegan"])):
        dd = durasi(vdir / "adegan" / f"{i + 1:02}.mp4")
        mulai.append(t + dd * 0.6)
        t += dd
    pilih = "+".join(f"between(t\\,{m - 0.05:.2f}\\,{m + 0.05:.2f})" for m in mulai)
    try:
        cols = 6
        rows = max(1, -(-len(mulai) // cols))
        ff("-i", str(final), "-vf", f"select='{pilih}',scale=320:180,tile={cols}x{rows}", "-frames:v", "1", "-fps_mode", "vfr", str(exp / "lembar.jpg"))
    except RuntimeError as err:
        catatan.append(f"lembar frame gagal: {str(err)[:100]}")
    skor = max(0.0, round(10 - 2.5 * len(masalah) - 0.5 * len(catatan), 1))
    hasil = {"slug": slug, "dibuat": datetime.now().isoformat(timespec="seconds"), "durasi": round(d, 1), "lufs": l,
             "lolos": not masalah, "skor": skor, "masalah": masalah, "catatan": catatan, "lembar": "export/lembar.jpg"}
    (exp / "qc.json").write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"{d / 60:.1f} menit · {l} LUFS · skor {skor:g} · {'LOLOS' if not masalah else 'MASALAH: ' + '; '.join(masalah)}")
    for c in catatan:
        log(f"catatan: {c}")


if __name__ == "__main__":
    main()

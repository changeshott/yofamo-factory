#!/usr/bin/env python3
"""Rara — QC (quality control) Yofamo. Memeriksa video final sebelum sampai ke Zona, lalu memperbaiki sendiri.

    python agents/qc/periksa.py cek <slug>                      # pemeriksaan otomatis + lembar frame untuk dilihat Rara
    python agents/qc/periksa.py ganti <slug> 3a 5b --alasan "teks rusak di gambar AI"
                                                                # tolak shot itu → Bima ganti → Kai rakit ulang
    python agents/qc/periksa.py otomatis <slug> [--putaran 2]   # tanpa Claude: cek → ganti shot gelap/beku → ulangi
    tambahkan --uji untuk mode uji (tanpa vo asli)

Hasil: videos/<slug>/export/qc.json dan export/qc/lembar-1.jpg (frame tengah tiap shot, berlabel 1a, 1b, …).
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "aset"))
import gerak  # noqa: E402

VIDEOS = ROOT / "videos"
PY = sys.executable
PER_LEMBAR = 20   # 5 kolom x 4 baris


def log(msg: str) -> None:
    print(f"[rara] {msg}", flush=True)


def rj(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def label(k: dict) -> str:
    return f"{k['i'] + 1}{'abc'[k['potong']]}"


def loudness(p: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(p), "-af", "ebur128", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def sheets(vdir: Path, klip: list[dict]) -> list[str]:
    """Frame dari video FINAL di tengah tiap shot (jadi subtitle & hook ikut terlihat), diberi label shot."""
    final = vdir / "export" / "final.mp4"
    qdir = vdir / "export" / "qc"
    qdir.mkdir(parents=True, exist_ok=True)
    for f in qdir.glob("*.jpg"):
        f.unlink()
    font = gerak.esc(gerak.font())
    frames = []
    for k in klip:
        t = (k["mulai"] + k["selesai"]) / 2
        out = qdir / f"f-{label(k)}.jpg"
        gerak.ff("-ss", f"{t:.2f}", "-i", str(final), "-frames:v", "1", "-vf",
                 f"scale=270:480,drawbox=x=0:y=0:w=86:h=50:color=0xFF9A4D:t=fill,"
                 f"drawtext=fontfile='{font}':text='{label(k)}':fontsize=38:fontcolor=0x24140A:x=10:y=6", str(out))
        frames.append(out)
    paths = []
    for n in range(0, len(frames), PER_LEMBAR):
        part = frames[n:n + PER_LEMBAR]
        cols = 5
        rows = (len(part) + cols - 1) // cols
        args, chains = [], []
        for j, f in enumerate(part):
            args += ["-i", str(f)]
            chains.append(f"[{j}:v]null[c{j}]")
        for j in range(len(part), rows * cols):
            args += ["-f", "lavfi", "-i", "color=c=0x0B1220:s=270x480:d=1"]
            chains.append(f"[{j}:v]null[c{j}]")
        layout = "|".join(f"{(j % cols) * 270}_{(j // cols) * 480}" for j in range(rows * cols))
        chains.append("".join(f"[c{j}]" for j in range(rows * cols)) + f"xstack=inputs={rows * cols}:layout={layout}[o]")
        out = qdir / f"lembar-{n // PER_LEMBAR + 1}.jpg"
        gerak.ff(*args, "-filter_complex", ";".join(chains), "-map", "[o]", "-frames:v", "1", "-q:v", "4", str(out))
        paths.append(str(out.relative_to(vdir)).replace("\\", "/"))
    for f in frames:
        f.unlink(missing_ok=True)
    return paths


def cek(slug: str) -> dict:
    vdir = VIDEOS / slug
    man = rj(vdir / "aset" / "manifest.json", None)
    final = vdir / "export" / "final.mp4"
    if not man or not final.exists():
        sys.exit("[rara] video final belum ada. Kai harus merakit dulu.")
    klip = sorted(man["klip"], key=lambda k: (k["i"], k["potong"]))
    words = rj(vdir / "words.json", {})
    masalah, ganti = [], []
    dur = gerak.duration(final)
    info = rj(vdir / "export" / "info.json", {})
    target = float(words.get("durasi") or man.get("durasi") or dur)
    harap = target + float(info.get("penutup_detik") or 0)
    if abs(dur - harap) > 0.35:
        masalah.append(f"durasi final {dur:.1f} dtk tidak sama dengan suara + penutup {harap:.1f} dtk")
    tg = words.get("target") or {}
    lo, hi = float(tg.get("min") or 28), float(tg.get("maks") or 45.5)
    if not lo - 0.5 <= target <= hi + 0.5:
        masalah.append(f"durasi suara {target:.1f} dtk di luar target naskah {lo:.0f}–{hi:.0f} dtk")
    for k in klip:
        f = vdir / "aset" / k["file"]
        if not f.exists():
            ganti.append({**ref(k), "alasan": "file shot hilang"})
            continue
        if k["jenis"] == "grafis":
            continue
        gelap, beku = gerak.cek_shot(f)
        if gelap > 0.35:
            ganti.append({**ref(k), "alasan": f"gelap {gelap:.0%}"})
        elif beku > 0.7 and k["jenis"] == "footage":
            ganti.append({**ref(k), "alasan": f"diam/beku {beku:.0%}"})
    total = sum(k["durasi"] for k in klip) or 1
    porsi = {j: round(sum(k["durasi"] for k in klip if k["jenis"] == j) / total, 2) for j in ("footage", "ai", "grafis")}
    if porsi["ai"] > 0.3:
        masalah.append(f"gambar AI {porsi['ai']:.0%} dari durasi (target ≤ 20%, utamakan potongan YouTube CC). Cek yt-dlp/sumber footage.")
    lufs = loudness(final)
    if lufs is not None and not -16.5 <= lufs <= -11.5:
        masalah.append(f"kerasnya suara {lufs:.1f} LUFS (target -14)")
    hasil = {"slug": slug, "dibuat": datetime.now().isoformat(timespec="seconds"), "durasi": round(dur, 2),
             "shot": len(klip), "porsi": porsi, "lufs": lufs, "masalah": masalah, "ganti_otomatis": ganti,
             "lembar": sheets(vdir, klip),
             "shot_info": [{"shot": label(k), "jenis": k["jenis"], "sumber": k.get("sumber"), "kalimat": k["kalimat"],
                            "dari": round(k["mulai"], 1), "sampai": round(k["selesai"], 1)} for k in klip]}
    old = rj(vdir / "export" / "qc.json", {})
    hasil["putaran"] = int(old.get("putaran", 0))
    hasil["riwayat"] = old.get("riwayat", [])
    (vdir / "export" / "qc.json").write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"{len(klip)} shot · footage {porsi['footage']:.0%} · AI {porsi['ai']:.0%} · grafis {porsi['grafis']:.0%} · {lufs} LUFS · {dur:.1f} dtk")
    for m in masalah:
        log(f"MASALAH: {m}")
    for g in ganti:
        log(f"GANTI {g['shot']}: {g['alasan']}")
    log(f"lembar frame: {', '.join(hasil['lembar'])}")
    return hasil


def ref(k: dict) -> dict:
    return {"shot": label(k), "i": k["i"], "potong": k["potong"], "jenis": k["jenis"], "sumber": k.get("sumber"), "id": k.get("id")}


def ganti(slug: str, shots: list[str], alasan: str, uji: bool) -> None:
    vdir = VIDEOS / slug
    man = rj(vdir / "aset" / "manifest.json", {})
    by_label = {label(k): k for k in man.get("klip", [])}
    pilih = [by_label[s] for s in shots if s in by_label]
    if not pilih:
        sys.exit(f"[rara] shot tidak dikenal: {' '.join(shots)}. Contoh label: {', '.join(list(by_label)[:4])}")
    tpath = vdir / "aset" / "tolak.json"
    tolak = rj(tpath, {"tolak": []})
    for k in pilih:
        tolak["tolak"].append({**ref(k), "alasan": alasan, "waktu": datetime.now().isoformat(timespec="seconds")})
    tpath.write_text(json.dumps(tolak, ensure_ascii=False, indent=2), encoding="utf-8")
    kalimat = sorted({k["i"] + 1 for k in pilih})
    log(f"menolak {', '.join(label(k) for k in pilih)} ({alasan}); Bima mengganti kalimat {kalimat}")
    args = [PY, "agents/aset/cari_aset.py", "unduh", slug]
    for n in kalimat:
        args += ["--ulang", str(n)]
    if uji:
        args.append("--uji")
    if subprocess.run(args, cwd=ROOT).returncode != 0:
        sys.exit("[rara] Bima gagal mengganti shot")
    if subprocess.run([PY, "agents/editor/rakit.py", slug, *(["--uji"] if uji else [])], cwd=ROOT).returncode != 0:
        sys.exit("[rara] Kai gagal merakit ulang")
    q = rj(vdir / "export" / "qc.json", {})
    q["putaran"] = int(q.get("putaran", 0)) + 1
    q.setdefault("riwayat", []).append({"waktu": datetime.now().isoformat(timespec="seconds"), "ganti": [label(k) for k in pilih], "alasan": alasan})
    (vdir / "export" / "qc.json").write_text(json.dumps(q, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Rara: QC video final")
    ap.add_argument("perintah", choices=["cek", "ganti", "otomatis"])
    ap.add_argument("slug")
    ap.add_argument("shot", nargs="*", help="label shot untuk 'ganti', misalnya 3a 5b")
    ap.add_argument("--alasan", default="ditolak QC")
    ap.add_argument("--putaran", type=int, default=2)
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{3,80}", a.slug):
        sys.exit("[rara] slug tidak valid")
    gerak.need_ffmpeg()
    if a.perintah == "cek":
        cek(a.slug)
    elif a.perintah == "ganti":
        q = rj(VIDEOS / a.slug / "export" / "qc.json", {})
        if int(q.get("putaran", 0)) >= 3:
            sys.exit("[rara] sudah 3 putaran perbaikan. Serahkan ke Zona dengan catatan.")
        ganti(a.slug, a.shot, a.alasan, a.uji)
        cek(a.slug)
    else:
        for n in range(a.putaran + 1):
            h = cek(a.slug)
            if not h["ganti_otomatis"] or n == a.putaran:
                break
            ganti(a.slug, [g["shot"] for g in h["ganti_otomatis"]], "; ".join(sorted({g["alasan"] for g in h["ganti_otomatis"]})), a.uji)
        log("selesai" + (" — masih ada catatan untuk Zona" if (h["masalah"] or h["ganti_otomatis"]) else " — lolos"))


if __name__ == "__main__":
    main()

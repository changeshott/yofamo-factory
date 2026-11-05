#!/usr/bin/env python3
"""Wulan — editor akhir video panjang. Menyambung adegan Tio + suara Gilang + musik → export/final.mp4 (1920x1080; dokumenter 30 fps, kartun 24 fps).

    python agents/panjang/rakit_panjang.py <slug>          # final.mp4 + thumbnail.jpg + bab (chapter) + subtitle.srt
    python agents/panjang/rakit_panjang.py <slug> --uji    # tanpa status (untuk tes)

Hasil di panjang/<slug>/export/: final.mp4, thumbnail.jpg (1280x720), bab.txt (timestamp chapter untuk deskripsi YouTube),
subtitle.srt (bisa diunggah sebagai teks tertutup), info.json. Status → draft (menunggu Zona menonton & menyetujui).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
import animasi  # noqa: E402

AUDIO_EXT = {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".flac"}


def log(msg: str) -> None:
    print(f"[wulan] {msg}", flush=True)


def ff(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"ffmpeg gagal: {r.stderr[-400:]}")


def durasi(f: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(f)], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def lufs(f: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(f), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s*(-?[\d.]+) LUFS", r.stderr)
    return float(m[-1]) if m else None


def pilih_musik(slug: str, suasana: str) -> Path | None:
    folder = ROOT / "musik"
    semua = sorted(f for f in folder.rglob("*") if f.suffix.lower() in AUDIO_EXT) if folder.is_dir() else []
    cocok = [f for f in semua if suasana and suasana in str(f.parent.name).lower()] or semua
    if not cocok:
        return None
    dipakai: dict[str, int] = {}
    for info in (ROOT / "panjang").glob("*/export/info.json"):
        m = json.loads(info.read_text(encoding="utf-8")).get("musik")
        if m and info.parent.parent.name != slug:
            dipakai[m] = dipakai.get(m, 0) + 1
    h = int(hashlib.sha1(slug.encode()).hexdigest(), 16)
    return min(cocok, key=lambda f: (dipakai.get(f.name, 0), (h + cocok.index(f) * 7919) % 997))


def ts(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def srt_waktu(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def thumbnail(vdir: Path, naskah: dict, out: Path) -> None:
    """Thumbnail lukis-komik: host Yofa berekspresi + ilustrasi + 2–4 kata besar (dirender HyperFrames, diambil 1 frame)."""
    th = naskah.get("thumbnail") or {}
    g = animasi.gaya()
    il = vdir / "ilustrasi" / "thumbnail.jpg"
    if not il.exists():
        il = next(iter(sorted((vdir / "ilustrasi").glob("[0-9][0-9].jpg"))), None) if (vdir / "ilustrasi").is_dir() else None
    data = animasi.data_adegan(0, {"jenis": "thumbnail", "judul": th.get("teks") or naskah.get("judul", "")[:30], "ekspresi": th.get("ekspresi", "kaget"),
                                   "_ilustrasi": bool(il)}, {"0": {"durasi": 1.0}}, vdir, g)
    pdir = vdir / "hf" / "thumbnail"
    animasi.tulis_proyek(pdir, data, il, naskah.get("judul", ""))
    tmp = vdir / "hf" / "thumbnail.mp4"
    animasi.render(pdir, tmp, data["fps"])
    ff("-sseof", "-0.2", "-i", str(tmp), "-frames:v", "1", "-vf", "scale=1280:720", "-q:v", "3", str(out))
    tmp.unlink(missing_ok=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Wulan: rakit video panjang")
    ap.add_argument("slug")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    waktu = json.loads((vdir / "suara" / "waktu.json").read_text(encoding="utf-8"))
    g = animasi.gaya()
    dok = naskah.get("format") == "dokumenter"
    fps_r, fps_k = (30, 30) if dok else (int(g.get("fps_render", 12)), int(g.get("fps_keluar", 24)))
    adegan = naskah["adegan"]
    klip = [vdir / "adegan" / f"{i + 1:02}.mp4" for i in range(len(adegan))]
    kurang = [k.name for k in klip if not k.exists()]
    if kurang:
        sys.exit(f"[wulan] adegan belum dirender: {', '.join(kurang[:8])}")
    exp = vdir / "export"
    exp.mkdir(exist_ok=True)
    animasi.tunggu_shorts(a.uji)
    # ---- video: sambung adegan (sama-sama dari HyperFrames) lalu 12 → 24 fps (gerak tetap "on twos")
    daftar = exp / "adegan.txt"
    daftar.write_text("".join(f"file '{k.resolve().as_posix()}'\n" for k in klip), encoding="utf-8")
    durasi_adegan = [durasi(k) for k in klip]
    mulai = [sum(durasi_adegan[:i]) for i in range(len(klip))]
    total = sum(durasi_adegan)
    # ---- audio: suara tiap adegan diletakkan tepat di awal adegannya
    args, parts = [], []
    for i in range(len(klip)):
        args += ["-i", str(vdir / "suara" / f"{i + 1:02}.mp3")]
        parts.append(f"[{i + 1}:a]aresample=48000,aformat=channel_layouts=stereo,apad,atrim=0:{durasi_adegan[i]:.3f}[a{i}]")
    n = len(klip)
    chains = parts + ["".join(f"[a{i}]" for i in range(n)) + f"concat=n={n}:v=0:a=1,asplit=2[vo1][vo2]"]
    mix = ["[vo1]"]
    musik = pilih_musik(a.slug, str(naskah.get("suasana", "")).lower())
    if musik:
        args += ["-stream_loop", "-1", "-i", str(musik)]
        l_mu = lufs(musik) or -14.0
        db = max(-40.0, min(6.0, (-18.0 - float(g.get("musik_di_bawah_narasi_db", 16))) - l_mu))
        chains.append(f"[{n + 1}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{total:.3f},volume={db:.2f}dB,equalizer=f=2600:t=q:w=1.3:g=-4,"
                      f"afade=t=in:d=1.5,afade=t=out:st={max(0, total - 4):.2f}:d=4[bg]")
        chains.append("[bg][vo2]sidechaincompress=threshold=0.05:ratio=2:attack=60:release=600:makeup=1[bgd]")
        mix.append("[bgd]")
    else:
        chains.append("[vo2]anullsink")
    chains.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[aout]")
    final, tmp = exp / "final.mp4", exp / "final.tmp.mp4"
    log(f"merakit {n} adegan, {total / 60:.1f} menit{', musik: ' + musik.name if musik else ', tanpa musik'}…")
    ff("-f", "concat", "-safe", "0", "-i", str(daftar), *args, "-filter_complex", ";".join(chains),
       "-map", "0:v:0", "-map", "[aout]", "-r", str(fps_k), "-c:v", "libx264", "-preset", "medium", "-crf", "19" if dok else "18",
       *(["-maxrate", "16M", "-bufsize", "32M"] if dok else []),        # butiran film membuat bitrate meledak: batasi supaya upload ringan
       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", f"{total:.3f}", str(tmp))
    tmp.replace(final)
    daftar.unlink(missing_ok=True)
    # ---- chapter YouTube: 0:00 pembuka + tiap kartu judul bab
    bab = [{"t": 0.0, "judul": naskah.get("bab_pembuka", "Pembuka")}]
    for i, ad in enumerate(adegan):
        if ad.get("jenis") == "judul_bab" and mulai[i] - bab[-1]["t"] >= 10:
            bab.append({"t": mulai[i], "judul": str(ad.get("judul", "")).strip()})
    if adegan and adegan[-1].get("jenis") == "penutup" and mulai[-1] - bab[-1]["t"] >= 10 and total - mulai[-1] >= 10:
        bab.append({"t": mulai[-1], "judul": "Penutup"})
    (exp / "bab.txt").write_text("\n".join(f"{ts(b['t'])} {b['judul']}" for b in bab) + "\n", encoding="utf-8")
    # ---- subtitle .srt (6–9 kata per baris) dari timing kata
    baris, no = [], 1
    for i in range(n):
        kata = (waktu.get(str(i)) or {}).get("kata", [])
        for k in range(0, len(kata), 7):
            grp = kata[k:k + 7]
            baris.append(f"{no}\n{srt_waktu(mulai[i] + grp[0]['mulai'])} --> {srt_waktu(mulai[i] + grp[-1]['selesai'] + 0.15)}\n{' '.join(x['kata'] for x in grp)}\n")
            no += 1
    (exp / "subtitle.srt").write_text("\n".join(baris), encoding="utf-8")
    # ---- thumbnail
    try:
        if dok:
            import thumbnail_panjang
            thumbnail_panjang.buat(vdir, naskah, exp / "thumbnail.jpg")
        else:
            thumbnail(vdir, naskah, exp / "thumbnail.jpg")
    except (RuntimeError, OSError, ValueError) as err:
        log(f"thumbnail gagal ({str(err)[:160]}); memakai frame video")
        ff("-ss", "2", "-i", str(final), "-frames:v", "1", "-vf", "scale=1280:720", "-q:v", "3", str(exp / "thumbnail.jpg"))
    info = {"dibuat": datetime.now().isoformat(timespec="seconds"), "uji": a.uji, "durasi": round(durasi(final), 2), "adegan": n,
            "musik": musik.name if musik else None, "bab": bab, "fps": fps_k, "format": naskah.get("format", "kartun"),
            "mulai_adegan": [round(m, 2) for m in mulai]}          # dipakai Steve untuk memetakan retensi ke adegan
    (exp / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(vdir / "hf" / "thumbnail", ignore_errors=True)
    if not a.uji:
        st_panjang.set_status(a.slug, "draft", f"final {info['durasi'] / 60:.1f} menit")
    log(f"selesai: panjang/{a.slug}/export/final.mp4 ({info['durasi'] / 60:.1f} menit, {len(bab)} bab)")


if __name__ == "__main__":
    main()

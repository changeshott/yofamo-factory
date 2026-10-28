"""Alat ffmpeg Bima: menyeragamkan klip ke 1080x1920, membuat gerak Ken Burns untuk gambar AI,
merender kartu grafis, dan membuat lembar kontak kandidat. Butuh ffmpeg di PATH."""
from __future__ import annotations

import os
import random
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

W, H, FPS = 1080, 1920, 30
INK, INK2, ORANGE, WHITE = "0x0B1220", "0x16304F", "0xFF9A4D", "0xF4F1E8"

FONT_CANDIDATES = [
    "C:/Windows/Fonts/seguibl.ttf", "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def need_ffmpeg() -> None:
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise SystemExit("[bima] ffmpeg belum terpasang. Windows: winget install Gyan.FFmpeg (lalu buka terminal baru).")


def font() -> str:
    for f in [os.environ.get("YOFAMO_FONT", "")] + FONT_CANDIDATES:
        if f and Path(f).exists():
            return f
    raise SystemExit("[bima] Font tebal tidak ditemukan. Isi YOFAMO_FONT=path/ke/font.ttf di .env.")


def esc(path: str | Path) -> str:
    """Escape path untuk opsi filter ffmpeg (C:/... → C\\:/...)."""
    return str(path).replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


def ff(*args: str) -> None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise RuntimeError(f"ffmpeg gagal: {r.stderr.strip()[-400:]}")


def duration(path: str | Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


ENC = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS), "-movflags", "+faststart"]


# ------------------------------------------------------------------ footage
def normalize(src: Path, out: Path, start: float, dur: float) -> None:
    """Potong [start, start+dur] lalu isi penuh layar 9:16 (crop tengah), 30 fps, tanpa audio."""
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H},setsar=1,fps={FPS}"
    ff("-ss", f"{max(0.0, start):.3f}", "-t", f"{dur:.3f}", "-i", str(src), "-vf", vf, *ENC, str(out))


def loop_to(src: Path, out: Path, dur: float) -> None:
    """Klip lebih pendek dari kebutuhan: diperlambat sedikit (maks 1,4×) lalu diulang bolak-balik bila perlu."""
    have = duration(src) or dur
    slow = min(1.4, max(1.0, dur / have))
    vf = f"setpts={slow:.3f}*PTS,split[a][b];[b]reverse[r];[a][r]concat=n=2:v=1:a=0,loop=-1:size=32767,trim=duration={dur:.3f},setpts=PTS-STARTPTS"
    ff("-i", str(src), "-filter_complex", vf, *ENC, str(out))


# ------------------------------------------------------------------ gambar AI → video
def kenburns(img: Path, out: Path, dur: float, seed: int) -> None:
    """Gerak kamera halus (zoom + geser dengan easing) supaya gambar diam terasa hidup, bukan slideshow kaku."""
    rnd = random.Random(seed)
    n = max(2, round(dur * FPS))
    e = f"((on/{n - 1})*(on/{n - 1})*(3-2*(on/{n - 1})))"         # smoothstep 0→1
    zoom_in = rnd.random() < 0.7
    z0, z1 = (1.0, 1.14) if zoom_in else (1.14, 1.02)
    ax, bx = rnd.choice([(0.5, 0.0), (0.3, 0.4), (0.7, -0.4)])     # posisi horizontal awal + arah geser
    ay, by = rnd.choice([(0.5, 0.0), (0.4, 0.2), (0.6, -0.2)])
    vf = (f"scale=-2:{H * 2}:flags=lanczos,crop='min(iw,ih*{W}/{H})':ih,"
          f"zoompan=z='{z0}+({z1 - z0})*{e}':x='(iw-iw/zoom)*({ax}+({bx})*{e})':y='(ih-ih/zoom)*({ay}+({by})*{e})'"
          f":d={n}:s={W}x{H}:fps={FPS},unsharp=5:5:0.6,setsar=1")
    ff("-loop", "1", "-framerate", str(FPS), "-t", f"{dur:.3f}", "-i", str(img), "-vf", vf, "-frames:v", str(n), *ENC, str(out))


# ------------------------------------------------------------------ kartu grafis
def _bg(dur: float) -> str:
    return (f"gradients=s={W}x{H}:c0={INK}:c1={INK2}:x0=0:y0=0:x1={W}:y1={H}:speed=0.006:r={FPS}:d={dur:.3f},"
            f"noise=alls=3:allf=t,vignette=PI/5")


def _text(tmp: Path, name: str, content: str) -> str:
    p = tmp / name
    p.write_text(content, encoding="utf-8")
    return esc(p)


def _pop(t0: float, base_y: str) -> tuple[str, str]:
    alpha = f"alpha='min(1,max(0,(t-{t0})/0.3))'"
    y = f"y='{base_y}+70*pow(max(0,1-(t-{t0})/0.4),3)'"
    return alpha, y


def grafis(spec: dict, out: Path, dur: float) -> None:
    """Dua gaya: 'angka' (angka besar menghitung naik + label) dan 'teks' (kalimat pendek muncul per baris)."""
    f = esc(font())
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        layers = [f"drawbox=x=90:y=300:w='min(220,t*900)':h=14:color={ORANGE}:t=fill"]
        if spec.get("gaya") == "angka":
            raw = str(spec.get("angka", "")).strip() or "?"
            digits = raw.replace(".", "")
            if digits.isdigit() and int(digits) < 1000:
                num = f"%{{eif:floor({int(digits)}*(1-pow(1-min(1,t/0.9),3))):d}}"
            else:
                num = raw
            suffix = str(spec.get("akhiran", ""))
            a, y = _pop(0.05, "(h/2)-330")
            size = int(min(260, 900 / (0.62 * max(1, len(raw + suffix)))))   # muat di lebar layar
            layers.append(f"drawtext=fontfile='{f}':textfile='{_text(tmp, 'n.txt', num + suffix)}':expansion=normal:"
                          f"fontsize={size}:fontcolor={ORANGE}:x=90:{y}:{a}:shadowcolor=0x000000@0.5:shadowx=0:shadowy=8")
            label = textwrap.fill(str(spec.get("label", "")), 20)
            a, y = _pop(0.35, "(h/2)+10")
            layers.append(f"drawtext=fontfile='{f}':textfile='{_text(tmp, 'l.txt', label)}':fontsize=76:fontcolor={WHITE}:"
                          f"line_spacing=18:x=90:{y}:{a}")
        else:
            lines = textwrap.wrap(str(spec.get("teks", "")).upper(), 13)[:4] or ["?"]
            top = 960 - len(lines) * 75
            for k, ln in enumerate(lines):
                a, y = _pop(0.08 + k * 0.16, str(top + k * 150))
                col = ORANGE if k == len(lines) - 1 else WHITE
                layers.append(f"drawtext=fontfile='{f}':textfile='{_text(tmp, f't{k}.txt', ln)}':fontsize=124:fontcolor={col}:"
                              f"x=90:{y}:{a}:shadowcolor=0x000000@0.5:shadowx=0:shadowy=8")
        ff("-f", "lavfi", "-i", _bg(dur), "-vf", ",".join(layers), "-t", f"{dur:.3f}", *ENC, str(out))


# ------------------------------------------------------------------ lembar kontak (dicek Claude)
def sheet(thumbs: list[Path], out: Path) -> None:
    """Grid 4 kolom, tiap sel 360x360 dengan nomor kandidat besar di pojok."""
    f = esc(font())
    cols = 4
    rows = (len(thumbs) + cols - 1) // cols
    args, chains = [], []
    for k, t in enumerate(thumbs):
        args += ["-i", str(t)]
        chains.append(f"[{k}:v]scale=356:356:force_original_aspect_ratio=decrease,pad=360:360:(ow-iw)/2:(oh-ih)/2:color=0x101826,"
                      f"drawbox=x=0:y=0:w=64:h=64:color=0xFF9A4D:t=fill,"
                      f"drawtext=fontfile='{f}':text='{k + 1}':fontsize=48:fontcolor=0x24140A:x=(64-tw)/2:y=8[c{k}]")
    for k in range(len(thumbs), rows * cols):            # sel kosong
        args += ["-f", "lavfi", "-i", "color=c=0x0B1220:s=360x360:d=1"]
        chains.append(f"[{k}:v]null[c{k}]")
    layout = "|".join(f"{(k % cols) * 360}_{(k // cols) * 360}" for k in range(rows * cols))
    chains.append("".join(f"[c{k}]" for k in range(rows * cols)) + f"xstack=inputs={rows * cols}:layout={layout}[o]")
    ff(*args, "-filter_complex", ";".join(chains), "-map", "[o]", "-frames:v", "1", "-q:v", "3", str(out))


def placeholder(out: Path, label: str, color: str, size: str = "640x360", dur: float | None = None) -> None:
    """Untuk mode uji: gambar/klip palsu berwarna dengan label."""
    f = esc(font())
    src = f"testsrc2=s={size}:r={FPS}" if dur else f"color=c={color}:s={size}"
    vf = f"drawtext=fontfile='{f}':text='{label}':fontsize=40:fontcolor=white:box=1:boxcolor=0x000000@0.6:x=(w-tw)/2:y=(h-th)/2"
    if dur:
        ff("-f", "lavfi", "-i", src, "-vf", vf, "-t", f"{dur:.2f}", "-pix_fmt", "yuv420p", str(out))
    else:
        ff("-f", "lavfi", "-i", src, "-vf", vf, "-frames:v", "1", str(out))

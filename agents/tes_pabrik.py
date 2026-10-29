#!/usr/bin/env python3
"""Tes menyeluruh pabrik Yofamo. Aman: semua tes berjalan di folder sementara, project asli tidak disentuh.

    python agents/tes_pabrik.py            # tes alur lengkap tanpa internet (Steve → Nova → Raka → Dara → Bima)
    python agents/tes_pabrik.py --online   # + cek koneksi sungguhan: YouTube, edge-tts, Cloudflare, NASA, Wikimedia, yt-dlp

Kirim seluruh keluarannya ke Claude kalau ada yang GAGAL.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
HASIL: list[tuple[str, bool, str]] = []

IDEA = {
    "judul_kerja": "Kulit buatan yang bisa merasakan sentuhan", "kategori": "kesehatan", "status_teknologi": "prototipe",
    "kenapa_menang": "Menyentuh tubuh.", "hook_ide": "Robot ini bisa merasakan sakit?!",
    "fakta": [{"klaim": "Contoh klaim A", "sumber_nama": "Sumber A", "sumber_url": "https://example.org/a"},
              {"klaim": "Contoh klaim B", "sumber_nama": "Sumber B", "sumber_url": "https://example.com/b"}],
    "visual_tersedia": "Video demo", "risiko": "Prototipe",
}
NARASI = [
    ("Robot ini bisa ngerasain sakit beneran, dan ini bukan film fiksi ilmiah sama sekali.", "close-up tangan robot disentuh jarum"),
    ("Ilmuwan bikin kulit buatan yang tipis banget, lentur, dan penuh sensor kecil di dalamnya.", "lembar kulit buatan ditarik pelan"),
    ("Setiap sensor mengubah tekanan jadi sinyal listrik, mirip saraf di kulit kita sendiri.", "animasi sinyal mengalir dari ujung jari"),
    ("Kalau ditekan terlalu keras, robotnya langsung menarik tangan, persis seperti refleks manusia.", "robot menarik tangan dari benda tajam"),
    ("Tujuannya bukan bikin robot menderita, tapi bikin tangan palsu yang bisa merasakan lagi.", "tangan prostetik memegang gelas"),
    ("Bayangin pengguna tangan palsu bisa ngerasain hangatnya genggaman orang yang mereka sayang.", "dua tangan saling menggenggam"),
    ("Teknologinya masih di laboratorium, jadi belum dijual bebas di mana pun saat ini.", "ruang laboratorium dengan peneliti"),
    ("Jadi kalau robot bisa ngerasain sakit, kira-kira dia juga bisa ngerasa sedih nggak ya?", "wajah robot menatap kamera"),
]
SCRIPT = {
    "judul": "ROBOT BISA MERASAKAN SAKIT?! Kulit Buatan Ini Bikin Merinding #Shorts #Teknologi",
    "hook_teks": "ROBOT BISA NGERASA SAKIT?!",
    "narasi": [{"kalimat": k, "visual": v} for k, v in NARASI],
    "deskripsi": "Kulit buatan ini bikin robot bisa merasakan sentuhan.\nSumber: https://example.org/a https://example.com/b",
    "tag": ["teknologi", "robot", "kulit buatan", "sensor", "prostetik", "sains", "inovasi", "teknologi masa depan"],
    "sumber": ["https://example.org/a", "https://example.com/b"], "catatan_editor": "-",
}
RENCANA = {"rencana": [
    {"i": 0, "jenis": "footage", "kata": ["robot hand touch"], "prompt_ai": "robot hand touched by needle"},
    {"i": 1, "jenis": "footage", "kata": ["electronic skin"], "prompt_ai": "thin electronic skin"},
    {"i": 2, "jenis": "ai", "kata": ["nerve signal"], "prompt_ai": "glowing signals in artificial nerves"},
    {"i": 3, "jenis": "grafis", "grafis": {"gaya": "angka", "angka": "240", "akhiran": "+", "label": "sensor per cm persegi"}},
    {"i": 4, "jenis": "footage", "kata": ["prosthetic hand"]},
    {"i": 5, "jenis": "footage", "kata": ["holding hands"]},
    {"i": 6, "jenis": "footage", "kata": ["robotics lab"]},
    {"i": 7, "jenis": "grafis", "grafis": {"gaya": "teks", "teks": "Bisa sedih juga nggak ya?"}},
]}


def cek(nama: str, ok: bool, info: str = "") -> bool:
    HASIL.append((nama, ok, info))
    print(f"  {'OK   ' if ok else 'GAGAL'} {nama}{(' — ' + info) if info else ''}", flush=True)
    return ok


def run(root: Path, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([PY, *args], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, env=env)


def ffprobe_size(p: Path) -> tuple[int, int, float]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                        "-of", "json", str(p)], capture_output=True, text=True)
    d = json.loads(r.stdout or "{}")
    s = (d.get("streams") or [{}])[0]
    return s.get("width", 0), s.get("height", 0), float((d.get("format") or {}).get("duration", 0))


def srt_ok(text: str) -> tuple[bool, str]:
    times = re.findall(r"(\d\d):(\d\d):(\d\d),(\d{3}) --> (\d\d):(\d\d):(\d\d),(\d{3})", text)
    sec = [(int(a) * 3600 + int(b) * 60 + int(c) + int(d) / 1000, int(e) * 3600 + int(f) * 60 + int(g) + int(h) / 1000) for a, b, c, d, e, f, g, h in times]
    if not sec:
        return False, "tidak ada baris waktu"
    bad = sum(1 for k, (s, e) in enumerate(sec) if e <= s or (k and s < sec[k - 1][1] - 0.001))
    return bad == 0, f"{len(sec)} baris subtitle, {bad} tumpang tindih"


# ------------------------------------------------------------------ tes tanpa internet
def offline() -> None:
    print("\n== Tes alur lengkap (tanpa internet, folder sementara) ==")
    tmp = Path(tempfile.mkdtemp(prefix="yofamo-tes-"))
    try:
        for d in ("agents", "bible"):
            shutil.copytree(ROOT / d, tmp / d, ignore=shutil.ignore_patterns("__pycache__"))
        (tmp / "videos").mkdir()
        cek("ffmpeg & ffprobe ada", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), "" if shutil.which("ffmpeg") else "winget install Gyan.FFmpeg")

        # Steve
        r = run(tmp, "agents/steve/fetch_stats.py", "--fixture", "agents/steve/sample_videos.json")
        raws = list((tmp / "insights" / "raw").glob("*.json"))
        cek("Steve: statistik dari data contoh", r.returncode == 0 and bool(raws), r.stderr.strip()[-200:])

        # Nova → antrean
        r = run(tmp, "agents/pabrik.py", "new", IDEA["judul_kerja"])
        rows = json.loads(run(tmp, "agents/pabrik.py", "list", "--json").stdout or "[]")
        slug = rows[0]["slug"] if rows else ""
        cek("Pabrik: ide masuk antrean", r.returncode == 0 and bool(slug), slug)
        vdir = tmp / "videos" / slug
        vdir.mkdir(parents=True, exist_ok=True)
        (vdir / "idea.json").write_text(json.dumps({**IDEA, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        cek("Zona menyetujui ide", run(tmp, "agents/pabrik.py", "set", slug, "disetujui").returncode == 0)

        # Raka
        (vdir / "script.json").write_text(json.dumps({**SCRIPT, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        r = run(tmp, "agents/penulis/cek_naskah.py", slug)
        cek("Raka: naskah lolos validasi", r.returncode == 0 and "LOLOS" in r.stdout, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
        run(tmp, "agents/pabrik.py", "set", slug, "naskah")

        # Dara (mode uji)
        r = run(tmp, "agents/suara/buat_suara.py", slug, "--uji")
        w = json.loads((vdir / "words.json").read_text(encoding="utf-8")) if (vdir / "words.json").exists() else {}
        cek("Dara: timing kata + kalimat", r.returncode == 0 and len(w.get("kalimat", [])) == len(NARASI), f"durasi {w.get('durasi')} dtk, {len(w.get('kata', []))} kata")
        cek("Dara: durasi 28–47 detik", 28 <= float(w.get("durasi") or 0) <= 47, str(w.get("durasi")))
        ok, info = srt_ok((vdir / "captions.srt").read_text(encoding="utf-8")) if (vdir / "captions.srt").exists() else (False, "tidak ada")
        cek("Dara: subtitle SRT rapi", ok, info)
        run(tmp, "agents/pabrik.py", "set", slug, "suara")

        # Bima (mode uji)
        milik = tmp / "milik-saya"
        milik.mkdir()
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc=s=1080x1920:r=30:d=6", "-pix_fmt", "yuv420p",
                        str(milik / "tangan-robot-lab.mp4")], check=False)
        (vdir / "aset").mkdir()
        (vdir / "aset" / "rencana.json").write_text(json.dumps(RENCANA), encoding="utf-8")
        t0 = time.time()
        r = run(tmp, "agents/aset/cari_aset.py", "semua", slug, "--uji")
        m = json.loads((vdir / "aset" / "manifest.json").read_text(encoding="utf-8")) if (vdir / "aset" / "manifest.json").exists() else {}
        kl = m.get("klip", [])
        cek("Bima: semua kalimat punya visual", r.returncode == 0 and bool(kl) and not m.get("kurang"), f"{len(kl)} shot dalam {time.time() - t0:.0f} dtk" if kl else r.stdout[-300:] + r.stderr[-300:])
        total = sum(k["durasi"] for k in kl)
        cek("Bima: durasi shot = durasi suara", abs(total - float(m.get("durasi") or 0)) < 0.1, f"{total:.2f} vs {m.get('durasi')}")
        sizes = [ffprobe_size(vdir / "aset" / k["file"]) for k in kl]
        bad = [k["file"] for k, (wd, ht, d) in zip(kl, sizes) if (wd, ht) != (1080, 1920) or abs(d - k["durasi"]) > 0.15]
        cek("Bima: semua shot 1080x1920 dan durasinya pas", not bad, ", ".join(bad[:5]))
        longest = max((k["durasi"] for k in kl if k["jenis"] != "grafis"), default=0)
        cek("Bima: ganti visual maks ±3,5 detik", longest <= 3.5, f"terpanjang {longest:.1f} dtk")
        streak = run_max = 0
        for k in kl:
            streak = streak + 1 if k["jenis"] == "footage" else 0
            run_max = max(run_max, streak)
        cek("Bima: maks 2 footage berturut-turut", run_max <= 2, f"{run_max} beruntun")
        jenis = {j: sum(1 for k in kl if k["jenis"] == j) for j in ("footage", "ai", "grafis")}
        cek("Bima: campuran footage/AI/grafis", all(jenis.values()), json.dumps(jenis))
        cek("Bima: rekaman milik-saya dipakai", any(k.get("sumber") == "milik" for k in kl))
        cek("Bima: lembar kontak & kredit dibuat", bool(list((vdir / "aset" / "lembar").glob("*.jpg"))) and (vdir / "aset" / "KREDIT.txt").exists())
        frames = [k for k in kl if k["jenis"] == "grafis"][:1]
        if frames:
            f = vdir / "aset" / frames[0]["file"]
            cek("Bima: kartu grafis ter-render", ffprobe_size(f)[0] == 1080)
        # Kai (mode uji)
        run(tmp, "agents/pabrik.py", "set", slug, "aset")
        (tmp / "musik").mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=12", str(tmp / "musik" / "uji.mp3")], check=False)
        shutil.copy(ROOT / "bible" / "gaya-edit.json", tmp / "bible" / "gaya-edit.json") if (ROOT / "bible" / "gaya-edit.json").exists() else None
        t0 = time.time()
        r = run(tmp, "agents/editor/rakit.py", slug, "--uji")
        fin = vdir / "export" / "final.mp4"
        wd, ht, d = ffprobe_size(fin) if fin.exists() else (0, 0, 0)
        cek("Kai: video final 1080x1920", r.returncode == 0 and (wd, ht) == (1080, 1920), f"{d:.1f} dtk, render {time.time() - t0:.0f} dtk" if fin.exists() else (r.stdout + r.stderr)[-300:])
        cek("Kai: durasi final = durasi suara", abs(d - float(m.get("durasi") or 0)) < 0.15, f"{d:.2f} vs {m.get('durasi')}")
        ar = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(fin)], capture_output=True, text=True)
        cek("Kai: ada audio AAC", "aac" in ar.stdout)
        cek("Kai: subtitle & sampul dibuat", (vdir / "export" / "subtitle.ass").exists() and (vdir / "export" / "sampul.jpg").exists())
    except Exception:
        cek("tes tanpa internet berjalan sampai selesai", False, traceback.format_exc().strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------ tes koneksi sungguhan
def online() -> None:
    print("\n== Tes koneksi sungguhan (memakai .env, tidak mengubah project) ==")
    import importlib.util
    kurang = [m for m in ("edge_tts", "yt_dlp") if importlib.util.find_spec(m) is None]
    cek("Python punya paket pabrik", not kurang,
        sys.executable if not kurang else f"{sys.executable} tidak punya {', '.join(kurang)} — pakai Python lain "
        f"atau jalankan: \"{sys.executable}\" -m pip install -r requirements.txt")
    sys.path.insert(0, str(ROOT / "agents" / "aset"))
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8-sig").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    tmp = Path(tempfile.mkdtemp(prefix="yofamo-online-"))
    try:
        import sumber
        r = run(ROOT, "agents/steve/fetch_stats.py", "--check", timeout=60)
        cek("YouTube Data API (Steve)", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")

        try:
            import asyncio
            import edge_tts
            async def tts() -> int:
                n = 0
                c = edge_tts.Communicate("Halo, ini tes suara Dara dari pabrik Yofamo.", "id-ID-ArdiNeural", rate="+10%", boundary="WordBoundary")
                with (tmp / "t.mp3").open("wb") as f:
                    async for ch in c.stream():
                        if ch["type"] == "audio":
                            f.write(ch["data"])
                        elif ch["type"] == "WordBoundary":
                            n += 1
                return n
            n = asyncio.run(tts())
            cek("edge-tts (suara Dara)", (tmp / "t.mp3").stat().st_size > 5000 and n > 3, f"{n} kata bertiming")
        except Exception as e:
            cek("edge-tts (suara Dara)", False, f"{type(e).__name__}: {e}"[:200])

        acc, tok = os.environ.get("CLOUDFLARE_ACCOUNT_ID", ""), os.environ.get("CLOUDFLARE_API_TOKEN", "")
        try:
            if not (acc and tok):
                raise ValueError("CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi")
            img = sumber.flux_image("macro photo of a robotic hand, studio light, no text", acc, tok)
            cek("Cloudflare FLUX (gambar AI)", len(img) > 10_000, f"{len(img) // 1024} KB")
        except Exception as e:
            cek("Cloudflare FLUX (gambar AI)", False, f"{type(e).__name__}: {e}"[:200])

        for nama, fn in [("NASA", lambda: sumber.nasa("robot arm")), ("Wikimedia Commons", lambda: sumber.wikimedia("robot"))]:
            try:
                res = fn()
                cek(f"{nama} (footage tanpa key)", bool(res), f"{len(res)} hasil")
            except Exception as e:
                cek(f"{nama} (footage tanpa key)", False, f"{type(e).__name__}: {e}"[:200])

        yt = []
        try:
            yt = sumber.youtube_cc("robot arm laboratory", os.environ.get("YOUTUBE_API_KEY", ""))
            cek("YouTube Creative Commons (cari)", bool(yt), f"{len(yt)} video CC BY")
        except Exception as e:
            cek("YouTube Creative Commons (cari)", False, f"{type(e).__name__}: {e}"[:200])
        try:
            import yt_dlp
            from yt_dlp.utils import download_range_func
            if not yt:
                raise ValueError("tidak ada video CC untuk dites")
            url = yt[0]["unduh"]
            opts = {"quiet": True, "no_warnings": True, "noplaylist": True,
                    "format": "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b[height<=1080]",
                    "outtmpl": str(tmp / "yt.%(ext)s"), "download_ranges": download_range_func(None, [(10, 13)])}
            with yt_dlp.YoutubeDL(opts) as y:
                y.download([url])
            got = [f for f in tmp.glob("yt.*") if not f.name.endswith(".part")]
            wd, ht, d = ffprobe_size(got[0]) if got else (0, 0, 0)
            cek("yt-dlp (potong 3 detik video CC)", bool(got) and d > 1, f"{wd}x{ht}, {d:.1f} dtk")
        except Exception as e:
            cek("yt-dlp (potong 3 detik video CC)", False, f"{type(e).__name__}: {e}"[:200] + ("" if isinstance(e, ImportError) else " (sudah install Deno?)"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Tes menyeluruh pabrik Yofamo")
    ap.add_argument("--online", action="store_true", help="juga tes koneksi sungguhan ke layanan luar")
    a = ap.parse_args()
    offline()
    if a.online:
        online()
    gagal = [h for h in HASIL if not h[1]]
    print(f"\n== Ringkasan: {len(HASIL) - len(gagal)}/{len(HASIL)} OK ==")
    for n, _, info in gagal:
        print(f"  GAGAL: {n}{(' — ' + info) if info else ''}")
    sys.exit(1 if gagal else 0)


if __name__ == "__main__":
    main()

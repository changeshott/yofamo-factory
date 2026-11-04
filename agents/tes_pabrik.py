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
from datetime import datetime, timedelta, timezone
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
    ("Tau nggak, robot ini bisa ngerasain sakit beneran, bukan film fiksi ilmiah.", "close-up tangan robot disentuh jarum"),
    ("Ilmuwan bikin kulit buatan yang tipis, lentur, dan penuh sensor kecil di dalamnya.", "lembar kulit buatan ditarik pelan"),
    ("Setiap sensor mengubah tekanan jadi sinyal listrik, mirip saraf di kulit kita.", "animasi sinyal mengalir dari ujung jari"),
    ("Kalau ditekan terlalu keras, robotnya langsung menarik tangan, seperti refleks manusia.", "robot menarik tangan dari benda tajam"),
    ("Tujuannya bukan bikin robot menderita, tapi bikin tangan palsu yang bisa merasakan lagi.", "tangan prostetik memegang gelas"),
    ("Bayangin pengguna tangan palsu bisa ngerasain hangatnya genggaman orang yang mereka sayang.", "dua tangan saling menggenggam"),
    ("Teknologinya masih di laboratorium, jadi belum dijual bebas di mana pun.", "ruang laboratorium dengan peneliti"),
    ("Jadi kalau robot bisa ngerasain sakit, kira-kira dia juga bisa ngerasa sedih nggak ya?", "wajah robot menatap kamera"),
]
BAGIAN = ["hook", "konteks", "cara_kerja", "wow", "dampak", "dampak", "bukti", "penutup"]
VIS = [("footage", ["robot hand touch"], None, ["sakit"]), ("footage", ["electronic skin"], None, []), ("ai", ["nerve signal"], None, ["sinyal listrik"]),
       ("footage", ["robot reflex"], "REFLEKS!", ["langsung"]), ("footage", ["prosthetic hand"], None, []), ("footage", ["holding hands"], None, ["hangatnya"]),
       ("footage", ["robotics lab"], "PROTOTIPE", []), ("grafis", [], None, ["sedih"])]
GG = {2: {"tipe": "langkah", "poin": ["Ditekan", "Sinyal listrik", "Refleks"]},
      5: {"tipe": "perbandingan", "kiri": "Tangan palsu biasa", "kanan": "Pakai kulit ini", "nilai_kiri": "mati rasa", "nilai_kanan": "bisa merasa"}}
SCRIPT = {
    "judul": "ROBOT BISA MERASAKAN SAKIT?! Kulit Buatan Ini Bikin Merinding #Shorts #Teknologi",
    "judul_alternatif": ["KULIT ROBOT INI BISA NGERASA SAKIT! #Shorts #Teknologi", "ROBOT PUNYA SARAF?! Kulit Buatan Paling Gila #Shorts #Teknologi"],
    "hook_teks": "ROBOT BISA NGERASA SAKIT?!",
    "target_durasi": 42, "suasana": "misterius", "penutup_tipe": "pertanyaan",
    "komentar_pin": "Kalau robot bisa ngerasa sakit, perlu nggak robot punya hak? Tulis pendapatmu!",
    "narasi": [{"kalimat": k, "visual": v, "bagian": b, "jenis_visual": vi[0], "kata_kunci_visual": vi[1], "teks_layar": vi[2], "penekanan": vi[3],
                **({"grafis_gerak": GG[i]} if i in GG else {})}
               for i, ((k, v), b, vi) in enumerate(zip(NARASI, BAGIAN, VIS))],
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


def run(root: Path, *args: str, timeout: int = 900, env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", **(env_extra or {})}
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
        for d in ("agents", "bible", "fonts"):
            shutil.copytree(ROOT / d, tmp / d, ignore=shutil.ignore_patterns("__pycache__"))
        if (ROOT / "node_modules").exists():          # mesin HyperFrames (kalau sudah npm install)
            try:
                os.symlink(ROOT / "node_modules", tmp / "node_modules", target_is_directory=True)
            except OSError:
                pass
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

        # Nova pro: validator ide (sumber tier, kutipan, angka kunci) + skor
        rich = {**IDEA, "slug": slug, "status_teknologi": "prototipe",
                "hook_varian": [{"jenis": "pertanyaan", "teks": "Robot ini bisa merasakan sakit?!"}, {"jenis": "angka", "teks": "240 sensor per sentimeter"},
                                {"jenis": "kamu", "teks": "Kulitmu kalah sensitif?"}],
                "fakta": [{"klaim": "Kulit buatan memuat 240 sensor per sentimeter persegi", "sumber_nama": "Universitas", "sumber_url": "https://news.stanford.edu/x",
                           "kutipan": "240 sensors per square centimeter", "tanggal_sumber": "2026-05"},
                          {"klaim": "Robot menarik tangan dalam 0,1 detik", "sumber_nama": "Nature", "sumber_url": "https://www.nature.com/articles/x",
                           "kutipan": "withdrawal within 0.1 s", "tanggal_sumber": "2026-05"},
                          {"klaim": "Diuji di laboratorium", "sumber_nama": "IEEE Spectrum", "sumber_url": "https://spectrum.ieee.org/x",
                           "kutipan": "tested in the lab", "tanggal_sumber": "2026-06"}],
                "angka_kunci": [{"angka": "240", "label": "sensor per cm²"}], "kata_kunci_visual": ["robot hand", "electronic skin"],
                "rubrik": {"wow": 5, "dekat": 4, "bukti": 5, "kebaruan": 4, "risiko_rendah": 4, "visual": 3}}
        (vdir / "idea.json").write_text(json.dumps(rich, ensure_ascii=False), encoding="utf-8")
        r = run(tmp, "agents/ide/cek_ide.py", slug, "--tulis")
        sk = (json.loads((vdir / "idea.json").read_text(encoding="utf-8")).get("skor") or {}).get("total")
        cek("Nova: ide lengkap lolos validasi & berskor", r.returncode == 0 and sk is not None, f"skor {sk}/100")
        bad = {**rich, "fakta": rich["fakta"][:2] + [{**rich["fakta"][2], "sumber_url": "https://medium.com/x"}],
               "angka_kunci": [{"angka": "999", "label": "karangan"}]}
        (vdir / "idea.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
        r = run(tmp, "agents/ide/cek_ide.py", slug)
        cek("Nova: sumber tier 3 & angka karangan ditolak", r.returncode == 1 and "tier 3" in r.stdout and "999" in r.stdout)
        (vdir / "idea.json").write_text(json.dumps({**IDEA, "slug": slug}, ensure_ascii=False), encoding="utf-8")  # kembali ke ide contoh untuk tes Raka

        # Raka
        (vdir / "script.json").write_text(json.dumps({**SCRIPT, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        r = run(tmp, "agents/penulis/cek_naskah.py", slug)
        cek("Raka: naskah lolos validasi", r.returncode == 0 and "LOLOS" in r.stdout, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
        run(tmp, "agents/penulis/cek_naskah.py", slug, "--tulis")
        cek("Raka: naskah.md untuk tim dibuat", (vdir / "naskah.md").exists() and "penutup" in (vdir / "naskah.md").read_text(encoding="utf-8"))
        jelek = json.loads(json.dumps(SCRIPT))
        jelek["narasi"][-1]["kalimat"] = "Dan yang lebih gila lagi, ternyata teknologi ini juga bisa dipakai untuk..."
        jelek["narasi"][0]["kalimat"] = "Halo guys, robot ini bisa ngerasain sakit beneran."
        jelek["judul"] = "Halo guys, di video kali ini kita bahas kulit robot #Shorts #Teknologi"
        (vdir / "script.json").write_text(json.dumps({**jelek, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        r2 = run(tmp, "agents/penulis/cek_naskah.py", slug)
        cek("Raka: akhir menggantung & basa-basi ditolak", r2.returncode != 0 and "GAGAL" in r2.stdout)
        (vdir / "script.json").write_text(json.dumps({**SCRIPT, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        run(tmp, "agents/pabrik.py", "set", slug, "naskah")

        # Dara (mode uji)
        r = run(tmp, "agents/suara/buat_suara.py", slug, "--uji")
        w = json.loads((vdir / "words.json").read_text(encoding="utf-8")) if (vdir / "words.json").exists() else {}
        cek("Dara: timing kata + kalimat", r.returncode == 0 and len(w.get("kalimat", [])) == len(NARASI), f"durasi {w.get('durasi')} dtk, {len(w.get('kata', []))} kata")
        cek("Dara: durasi 28–47 detik", 28 <= float(w.get("durasi") or 0) <= 47, str(w.get("durasi")))
        tg = w.get("target") or {}
        cek("Dara: transkrip & target durasi naskah", (vdir / "transkrip.txt").exists() and tg.get("detik") == SCRIPT["target_durasi"],
            f"target {tg.get('min')}–{tg.get('maks')} dtk")
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
        dur_j = {j: sum(k["durasi"] for k in kl if k["jenis"] == j) for j in ("footage", "ai", "grafis")}
        tot_j = sum(dur_j.values()) or 1
        cek("Bima: footage asli diutamakan, gambar AI ≤ 10% shot", sum(1 for k in kl if k["jenis"] == "ai") <= int(len(kl) * 0.10)
            and dur_j["footage"] / tot_j >= 0.6, f"footage {dur_j['footage'] / tot_j:.0%}, AI {dur_j['ai'] / tot_j:.0%}")
        k_ai = [k for k in kl if k["i"] == 2]
        cek("Bima: kalimat 'ai' dicarikan footage relevan dulu", bool(k_ai) and all(k["jenis"] == "footage" and k.get("relevansi", 0) > 0 for k in k_ai),
            ", ".join(f"{k['potong']}:{k['jenis']}/{k.get('judul', '')[:30]}" for k in k_ai))
        rel = [k for k in kl if k["jenis"] == "footage" and k.get("sumber") != "milik"]
        cek("Bima: footage menonjolkan yang dibahas (relevan)", sum(1 for k in rel if k.get("relevansi", 0) > 0) >= 0.7 * max(1, len(rel)),
            f"{sum(1 for k in rel if k.get('relevansi', 0) > 0)}/{len(rel)} relevan")
        yt_pertama = [k for k in kl if k["jenis"] == "footage" and k.get("sumber") == "youtube"]
        cek("Bima: potongan YouTube CC dipakai paling banyak", len(yt_pertama) >= max((sum(1 for k in kl if k.get("sumber") == s_) for s_ in ("nasa", "wikimedia", "pexels")), default=0),
            f"{len(yt_pertama)} potongan YouTube")
        jenis = {j: sum(1 for k in kl if k["jenis"] == j) for j in ("footage", "ai", "grafis")}
        cek("Bima: campuran footage + grafis", jenis["footage"] > 0 and jenis["grafis"] > 0, json.dumps(jenis))
        # pilihan Bima (Claude) yang terlalu banyak AI tetap dibatasi: hook tanpa AI, total AI ≤ 10% shot
        (vdir / "aset" / "pilihan.json").write_text(json.dumps({"pilihan": [{"i": 0, "pakai": [1, "ai"]}, {"i": 1, "pakai": ["ai", "ai"]},
                                                                            {"i": 4, "pakai": ["ai", "ai"]}]}), encoding="utf-8")
        r = run(tmp, "agents/aset/cari_aset.py", "unduh", slug, "--uji", "--ulang", "1", "--ulang", "2", "--ulang", "5")
        kl2 = json.loads((vdir / "aset" / "manifest.json").read_text(encoding="utf-8")).get("klip", [])
        n_ai = sum(1 for k in kl2 if k["jenis"] == "ai")
        cek("Bima: pilihan penuh AI dibatasi (hook tanpa AI, AI ≤ 10% shot)", r.returncode == 0 and n_ai <= int(len(kl2) * 0.10)
            and not any(k["jenis"] == "ai" for k in kl2 if k["i"] == 0), f"{n_ai} AI dari {len(kl2)} shot; ulang pakai: {sum(1 for k in kl2 if k.get('pakai_ulang'))}")
        (vdir / "aset" / "pilihan.json").unlink()
        cek("Bima: rekaman milik-saya dipakai", any(k.get("sumber") == "milik" for k in kl))
        cek("Bima: lembar kontak & kredit dibuat", bool(list((vdir / "aset" / "lembar").glob("*.jpg"))) and (vdir / "aset" / "KREDIT.txt").exists())
        frames = [k for k in kl if k["jenis"] == "grafis"][:1]
        if frames:
            f = vdir / "aset" / frames[0]["file"]
            cek("Bima: kartu grafis ter-render & ringan", ffprobe_size(f)[0] == 1080 and f.stat().st_size < 8 * 1024 * 1024,
                f"{f.stat().st_size / 1048576:.1f} MB")
        # Rara pra-periksa (sebelum Kai merakit): shot hitam diganti Bima TANPA render, lembar shot dibuat
        run(tmp, "agents/pabrik.py", "set", slug, "aset")
        kl_now = json.loads((vdir / "aset" / "manifest.json").read_text(encoding="utf-8")).get("klip", [])
        rusak = next(k for k in kl_now if k["jenis"] != "grafis")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1080x1920:r=30:d={rusak['durasi']:.3f}",
                        "-pix_fmt", "yuv420p", str(vdir / "aset" / rusak["file"])], check=False)
        t0 = time.time()
        r = run(tmp, "agents/qc/periksa.py", "pra", slug, "--uji")
        pq = json.loads((vdir / "export" / "qc_pra.json").read_text(encoding="utf-8")) if (vdir / "export" / "qc_pra.json").exists() else {}
        cek("Rara pra: shot hitam diganti sebelum dirakit (tanpa render)", r.returncode == 0 and bool(pq) and not pq.get("ganti_otomatis")
            and not (vdir / "export" / "final.mp4").exists(), f"{pq.get('shot')} shot, {time.time() - t0:.0f} dtk" if pq else (r.stdout + r.stderr)[-300:])
        cek("Rara pra: lembar shot dibuat", bool(pq.get("lembar")) and all((vdir / x).exists() for x in pq.get("lembar", [])) and "pra-lembar" in str(pq.get("lembar")))
        lbl = pq.get("shot_info", [{}])[0].get("shot", "1a")
        r = run(tmp, "agents/qc/periksa.py", "ganti", slug, lbl, "--tanpa-rakit", "--alasan", "uji tolak manual", "--uji")
        pq2 = json.loads((vdir / "export" / "qc_pra.json").read_text(encoding="utf-8")) if (vdir / "export" / "qc_pra.json").exists() else {}
        cek("Rara pra: tolak manual tanpa rakit + hitung putaran", r.returncode == 0 and pq2.get("putaran_rara") == 1 and not (vdir / "export" / "final.mp4").exists(),
            f"putaran {pq2.get('putaran_rara')}" if pq2 else (r.stdout + r.stderr)[-300:])
        # Kai (mode uji)
        run(tmp, "agents/pabrik.py", "set", slug, "aset")
        (tmp / "musik").mkdir(exist_ok=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=12", str(tmp / "musik" / "uji.mp3")], check=False)
        shutil.copy(ROOT / "bible" / "gaya-edit.json", tmp / "bible" / "gaya-edit.json") if (ROOT / "bible" / "gaya-edit.json").exists() else None
        t0 = time.time()
        (tmp / "musik" / "misterius").mkdir(parents=True, exist_ok=True)     # perpustakaan musik contoh (suasana naskah: misterius)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=330:duration=60", "-c:a", "libmp3lame",
                        str(tmp / "musik" / "misterius" / "lagu-uji.mp3")], check=False)
        (tmp / "musik" / "misterius" / "lagu-uji.txt").write_text("Lagu Uji oleh Contoh (CC BY 4.0)", encoding="utf-8")
        r = run(tmp, "agents/editor/rakit.py", slug, "--uji")
        fin = vdir / "export" / "final.mp4"
        wd, ht, d = ffprobe_size(fin) if fin.exists() else (0, 0, 0)
        cek("Kai: video final 1080x1920", r.returncode == 0 and (wd, ht) == (1080, 1920), f"{d:.1f} dtk, render {time.time() - t0:.0f} dtk" if fin.exists() else (r.stdout + r.stderr)[-300:])
        inf = json.loads((vdir / "export" / "info.json").read_text(encoding="utf-8")) if (vdir / "export" / "info.json").exists() else {}
        harap = float(m.get("durasi") or 0) + float(inf.get("penutup_detik") or 0)
        cek("Kai: durasi final = suara + penutup", inf.get("penutup_detik", 0) > 0 and abs(d - harap) < 0.15,
            f"{d:.2f} vs {m.get('durasi')} + {inf.get('penutup_detik')}")
        ass_txt = (vdir / "export" / "subtitle.ass").read_text(encoding="utf-8") if (vdir / "export" / "subtitle.ass").exists() else ""
        try:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-sseof", "-0.5", "-i", str(fin), "-frames:v", "1", "-vf", "scale=360:-2",
                            os.environ.get("TES_FRAME_AKHIR", str(tmp / "akhir.jpg"))], check=False)
        except OSError:
            pass
        subs = [l.split(",,", 1)[-1] for l in ass_txt.splitlines() if ",Sub," in l]
        satu_kata = all(len(re.sub(r"\{[^}]*\}", "", t).split()) == 1 for t in subs)
        cek("Kai: subtitle 1 kata di tengah layar", bool(subs) and satu_kata and all("\\an5" in t for t in subs), f"{len(subs)} kata")
        hk = [l for l in ass_txt.splitlines() if ",Hook," in l]
        cek("Kai: hook bertingkat warna-warni muncul bertahap", len(hk) >= 3 and len({re.search(r"\\c(&H\w+&)", l).group(1) for l in hk}) >= 3
            and len({l.split(",")[1] for l in hk}) >= 3, f"{len(hk)} baris")
        cek("Kai: transisi antar-kalimat & denyut penekanan", len(inf.get("transisi", [])) == len(NARASI) - 1 and inf.get("denyut_tekanan", 0) > 0,
            ", ".join(inf.get("transisi", [])[:4]))
        if (tmp / "node_modules").exists():
            hfd = json.loads((vdir / "export" / "hf" / "data.json").read_text(encoding="utf-8")) if (vdir / "export" / "hf" / "data.json").exists() else {}
            tipe = sorted({g["tipe"] for g in hfd.get("grafis", [])})
            cek("Kai: mesin HyperFrames + grafis gerak sesuai kalimat", inf.get("mesin") == "hyperframes" and len(hfd.get("grafis", [])) >= 3,
                f"mesin {inf.get('mesin')}, grafis: {', '.join(tipe)}")
            gg = inf.get("gaya_gerak") or {}
            sys.path.insert(0, str(tmp / "agents" / "editor"))
            import komposisi as _kp
            g2 = _kp.pilih_gaya("video-uji-berikutnya", tmp / "videos")
            beda = [k for k in _kp.VARIAN if g2.get(k) != gg.get(k)]
            sama_lagi = _kp.pilih_gaya(slug, tmp / "videos")
            cek("Kai: gaya gerak tercatat, video berikutnya berbeda, rakit ulang tetap sama",
                bool(gg) and len(beda) == len(_kp.VARIAN) and all(sama_lagi.get(k) == gg.get(k) for k in _kp.VARIAN) and hfd.get("gaya", {}).get("hook") == gg.get("hook"),
                f"video ini: {gg.get('hook')}/{gg.get('sub')}/{gg.get('kartu')} → berikutnya: {g2.get('hook')}/{g2.get('sub')}/{g2.get('kartu')}")
        fdir = os.environ.get("TES_FRAME_DIR")
        if fdir:
            for t in (0.15, 0.5, 1.2, 4.0, 6.0):
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(fin), "-frames:v", "1", "-vf", "scale=360:-2",
                                str(Path(fdir) / f"f{t:.2f}.jpg")], check=False)
        cek("Kai: musik latar sesuai suasana, 10 dB di bawah narasi, kredit tercatat", inf.get("musik") == "lagu-uji.mp3" and inf.get("musik_di_bawah_narasi_db") == 10
            and "Lagu Uji" in str(inf.get("musik_kredit")), f"{inf.get('musik')} · -{inf.get('musik_di_bawah_narasi_db')} dB")
        cek("Kai: penutup, teks layar & penekanan tampil", ",Akhir," in ass_txt and ",Layar," in ass_txt and "PROTOTIPE" in ass_txt and "REFLEKS!" not in ass_txt and "&H003FD2FF&" in ass_txt)
        ar = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name", "-of", "csv=p=0", str(fin)], capture_output=True, text=True)
        cek("Kai: ada audio AAC", "aac" in ar.stdout)
        cek("Kai: subtitle & sampul dibuat", (vdir / "export" / "subtitle.ass").exists() and (vdir / "export" / "sampul.jpg").exists())

        # Rara (QC otomatis): rusak satu shot dengan klip hitam → harus terdeteksi dan diganti
        target = next(k for k in kl if k["jenis"] != "grafis")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "lavfi", "-i", f"color=black:s=1080x1920:r=30:d={target['durasi']:.3f}",
                        "-pix_fmt", "yuv420p", str(vdir / "aset" / target["file"])], check=False)
        t0 = time.time()
        r = run(tmp, "agents/qc/periksa.py", "otomatis", slug, "--uji")
        q = json.loads((vdir / "export" / "qc.json").read_text(encoding="utf-8")) if (vdir / "export" / "qc.json").exists() else {}
        cek("Rara: shot hitam terdeteksi & diganti", r.returncode == 0 and q.get("putaran", 0) >= 1 and not q.get("ganti_otomatis"),
            f"{q.get('putaran')} putaran, {time.time() - t0:.0f} dtk" if q else (r.stdout + r.stderr)[-300:])
        cek("Rara: lembar frame dibuat", bool(q.get("lembar")) and all((vdir / x).exists() for x in q.get("lembar", [])))

        # Uli: deskripsi tanpa link sumber, kredit singkat, hashtag lengkap
        r = run(tmp, "agents/upload/unggah.py", "pratinjau", slug)
        desk = r.stdout.split("DESKRIPSI:", 1)[-1].split("TAG:", 1)[0]
        tagar = re.findall(r"#\w+", desk)
        cek("Uli: deskripsi tanpa link, ada kredit & hashtag lengkap", r.returncode == 0 and not re.search(r"https?://|www\\.", desk)
            and "Sumber:" not in desk and "Kredit" in desk and len(tagar) >= 8 and len(set(tagar)) == len(tagar),
            f"{len(tagar)} hashtag: {' '.join(tagar[:6])}…" if r.returncode == 0 else (r.stdout + r.stderr)[-300:])

        # Jadwal tayang: 3 slot/hari, jarak ≥ 3 jam, di jam wajar
        r = run(tmp, "agents/upload/jadwal.py")
        jd = json.loads((tmp / "insights" / "jadwal.json").read_text(encoding="utf-8")) if (tmp / "insights" / "jadwal.json").exists() else {}
        hari0 = list((jd.get("slot") or {}).values())[:1]
        jam0 = [int(x["jam"][:2]) for x in (hari0[0] if hari0 else [])]
        cek("Jadwal: 3 jam tayang per hari, berjarak ≥ 3 jam", r.returncode == 0 and len(jam0) == 3 and all(7 <= h <= 22 for h in jam0)
            and all(b_ - a_ >= 3 for a_, b_ in zip(jam0, jam0[1:])), ", ".join(f"{h:02d}:00" for h in jam0))

        # Autopilot: video lolos QC → disetujui otomatis → dijadwalkan di slot terdekat → setelah jamnya lewat ditandai tayang
        ap_cfg = json.loads((tmp / "bible" / "autopilot.json").read_text(encoding="utf-8"))
        ap_cfg.update(aktif=True, mulai_produksi_jam_sebelum=0, video_per_hari=1, isi_hari=1)
        (tmp / "bible" / "autopilot.json").write_text(json.dumps(ap_cfg), encoding="utf-8")
        (tmp / "produksi").mkdir(exist_ok=True)
        (tmp / "produksi" / "autopilot.json").write_text(json.dumps({"slot": {}, "dibuat": [slug]}), encoding="utf-8")
        run(tmp, "agents/pabrik.py", "set", slug, "draft")
        hari_ini = datetime.now(timezone(timedelta(hours=7))).date().isoformat()
        r = run(tmp, "agents/autopilot.py", "jalan", "--uji", "--sekarang", f"{hari_ini}T06:00")
        stt = json.loads((tmp / "produksi" / "autopilot.json").read_text(encoding="utf-8"))
        isi = [(k_, v_) for k_, v_ in stt.get("slot", {}).items() if v_.get("slug") == slug]
        st_v = next((x["status"] for x in json.loads(run(tmp, "agents/pabrik.py", "list", "--json").stdout or "[]") if x["slug"] == slug), None)
        cek("Autopilot: video lolos Rara disetujui otomatis & dijadwalkan", r.returncode == 0 and len(isi) == 1 and st_v == "export",
            f"{isi[0][0]} WIB, status {st_v}" if isi else (r.stdout + r.stderr)[-300:])
        aktif_lagi = json.loads((tmp / "bible" / "autopilot.json").read_text(encoding="utf-8")).get("aktif")
        cek("Autopilot: stok lengkap → mati sendiri", aktif_lagi is False and bool(stt.get("selesai")), f"aktif={aktif_lagi}")
        if isi:
            jam_tayang = datetime.strptime(isi[0][0], "%Y-%m-%d %H:%M") + timedelta(minutes=30)
            r = run(tmp, "agents/autopilot.py", "jalan", "--uji", "--paksa", "--sekarang", jam_tayang.strftime("%Y-%m-%dT%H:%M"))
            stt = json.loads((tmp / "produksi" / "autopilot.json").read_text(encoding="utf-8"))
            cek("Autopilot: setelah jam tayang lewat, video ditandai tayang", stt["slot"][isi[0][0]].get("status") == "tayang")
        k_lock = tmp / "produksi" / "produser-uji.lock"
        k_lock.write_text(json.dumps({"pid": os.getpid(), "mulai": time.time(), "nama": "tes"}), encoding="utf-8")
        r = run(tmp, "agents/produser.py", "tes", "--uji")
        cek("Produser: menolak jalan bersamaan dengan produksi lain", r.returncode == 3 and "produksi lain" in r.stdout, r.stdout.strip()[-120:])
        k_lock.unlink()

        # Bersih-bersih: video belum diupload tidak disentuh; setelah diupload file besarnya dihapus, data kecil tetap ada
        r = run(tmp, "agents/bersih.py", "video", slug)
        utuh = (vdir / "export" / "final.mp4").exists()
        (vdir / "export" / "upload.json").write_text(json.dumps({"videoId": "abcDEF12345", "url": "https://youtube.com/shorts/abcDEF12345"}), encoding="utf-8")
        mb0 = sum(f.stat().st_size for f in vdir.rglob("*") if f.is_file()) / 1048576
        r = run(tmp, "agents/bersih.py", "semua")
        mb1 = sum(f.stat().st_size for f in vdir.rglob("*") if f.is_file()) / 1048576
        tetap = all((vdir / x).exists() for x in ("script.json", "idea.json", "words.json", "export/info.json", "export/upload.json", "aset/manifest.json"))
        cek("Bersih: file besar video yang sudah diupload dihapus, data kecil tetap", utuh and r.returncode == 0 and tetap
            and not (vdir / "export" / "final.mp4").exists() and not list((vdir / "aset").glob("*.mp4")), f"{mb0:.0f} MB → {mb1:.1f} MB")

        # Ruang Animasi (video panjang): validator, suara & ilustrasi uji, pratinjau frame tiap adegan (tanpa render penuh)
        pslug = "uji-panjang-kulit"
        pdir = tmp / "panjang" / pslug
        pdir.mkdir(parents=True)
        shutil.copy(tmp / "agents" / "panjang" / "contoh" / "ide.json", pdir / "ide.json")
        shutil.copy(tmp / "agents" / "panjang" / "contoh" / "naskah.json", pdir / "naskah.json")
        run(tmp, "agents/panjang/status.py", "set", pslug, "ide", "tes")
        r = run(tmp, "agents/panjang/cek_naskah_panjang.py", pslug)
        cek("Ruang Animasi: validator naskah menolak naskah terlalu pendek", r.returncode != 0 and "perkiraan durasi" in r.stdout, r.stdout.strip().splitlines()[-1] if r.stdout else r.stderr[-200:])
        r1 = run(tmp, "agents/panjang/suara_panjang.py", pslug, "--uji")
        r2 = run(tmp, "agents/panjang/ilustrasi.py", pslug, "--uji")
        wpj = json.loads((pdir / "suara" / "waktu.json").read_text(encoding="utf-8")) if (pdir / "suara" / "waktu.json").exists() else {}
        cek("Ruang Animasi: suara + timing kata & ilustrasi per adegan", r1.returncode == 0 and r2.returncode == 0 and len(wpj) == 10
            and len(list((pdir / "ilustrasi").glob("*.jpg"))) >= 3, (r1.stdout + r1.stderr + r2.stderr)[-200:] if r1.returncode or r2.returncode else f"{len(wpj)} adegan")
        from PIL import Image
        objek = pdir / "ilustrasi" / "04.png"
        cek("Ruang Animasi: objek diagram dipotong dari latar pink → PNG transparan", objek.exists() and Image.open(objek).getchannel("A").getextrema()[0] == 0)
        # host Yofa (mode uji: gambar pengganti di produksi/uji-maskot, bible/maskot tidak tersentuh)
        sebelum = sorted(p.name for p in (tmp / "bible" / "maskot").rglob("*")) if (tmp / "bible" / "maskot").is_dir() else []
        r = run(tmp, "agents/panjang/maskot.py", "otomatis", "--uji")
        pose_dir = tmp / "produksi" / "uji-maskot" / "pose"
        pose = sorted(p.stem for p in pose_dir.glob("*.png"))
        sesudah = sorted(p.name for p in (tmp / "bible" / "maskot").rglob("*")) if (tmp / "bible" / "maskot").is_dir() else []
        ukuran = {Image.open(p).size for p in pose_dir.glob("*.png")}
        cek("Host Yofa: 4 kandidat → 7 pose transparan berkanvas sama (sejajar), bible tidak tersentuh saat uji",
            r.returncode == 0 and len(pose) == 7 and {"diam", "bicara"} <= set(pose) and len(ukuran) == 1 and sebelum == sesudah
            and len(list((tmp / "produksi" / "uji-maskot" / "kandidat").glob("k*.jpg"))) == 4, (r.stdout + r.stderr)[-200:] if r.returncode else f"{pose}")
        try:
            import playwright  # noqa: F401
            r = run(tmp, "agents/panjang/animasi.py", pslug, "--pratinjau")
            foto = list((pdir / "adegan").glob("pratinjau-*.jpg"))
            cek("Ruang Animasi: semua adegan (host, bab, ilustrasi, diagram, penutup) terbangun tanpa error", r.returncode == 0 and len(foto) == 30,
                f"{len(foto)} frame" if r.returncode == 0 else (r.stdout + r.stderr)[-300:])
            r = run(tmp, "agents/panjang/animasi.py", pslug, "--pratinjau", env_extra={"YOFAMO_POSE_DIR": str(pose_dir)})
            cek("Ruang Animasi: host gambar AI (pose PNG + mulut ikut suku kata) terbangun tanpa error",
                r.returncode == 0 and (pdir / "hf" / "01" / "assets" / "maskot" / "bicara.png").exists() and '"bicara"' in (pdir / "hf" / "01" / "index.html").read_text(encoding="utf-8"),
                (r.stdout + r.stderr)[-300:] if r.returncode else "")
        except ImportError:
            print("  (lewati pratinjau animasi: playwright tidak terpasang)")

        # Kontrol Zona: hapus video
        r = run(tmp, "agents/pabrik.py", "hapus", slug, "--ya")
        rows = json.loads(run(tmp, "agents/pabrik.py", "list", "--json").stdout or "[]")
        cek("Hapus video: catatan & folder hilang", r.returncode == 0 and not vdir.exists() and not any(x["slug"] == slug for x in rows))
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

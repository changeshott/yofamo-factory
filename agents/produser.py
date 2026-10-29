#!/usr/bin/env python3
"""Produser Yofamo: satu permintaan Zona → satu video jadi, otomatis lewat semua agent.

    python agents/produser.py "robot yang bisa merasakan sakit"
    python agents/produser.py "baju yang bisa ganti warna" --suara wanita --visual cepat
    python agents/produser.py "tes" --uji        # tanpa Claude & internet (data contoh), untuk mengetes alur

Urutan: Nova (1 ide sesuai permintaan, tetap wajib 2 sumber) → disetujui (karena Zona sendiri yang meminta)
→ Raka (naskah) → Dara (suara) → Bima (visual) → Kai (video final, status draft).
Video tetap harus ditonton dan disetujui Zona di Studio sebelum dianggap siap upload.
Kemajuan dicatat di produksi/<id>.json (dibaca Studio).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROD = ROOT / "produksi"
PY = sys.executable
MODEL = "sonnet"
# `python` yang dipanggil Claude (skill) harus Python yang sama dengan produser ini,
# bukan python lain yang kebetulan lebih dulu di PATH (misalnya venv aplikasi lain).
os.environ["PATH"] = os.pathsep.join([str(Path(PY).parent), str(Path(PY).parent / "Scripts"), os.environ.get("PATH", "")])
os.environ.setdefault("YOFAMO_PYTHON", PY)  # cadangan kalau shell Claude menyusun ulang PATH (lihat agents/pakai_python.py)

TAHAP = [
    ("nova", "ide", "Nova meriset ide"),
    ("setuju", "", "Ide disetujui (permintaanmu)"),
    ("raka", "penulis", "Raka menulis naskah"),
    ("dara", "suara", "Dara membuat suara"),
    ("bima", "aset", "Bima menyiapkan visual"),
    ("kai", "editor", "Kai merakit video"),
]


def tools(*scripts: str, web: bool = False) -> list[str]:
    out = ["Read", "Write", "Glob", "Grep"]
    for sc in scripts:
        for py in ("python", "python3"):
            out += [f"Bash({py} {sc} *)", f"Bash({py} {sc})"]
        out += [f"PowerShell(python {sc} *)", f"PowerShell(python {sc})"]
    return out + (["WebSearch", "WebFetch"] if web else [])


class Catatan:
    """File kemajuan produksi/<id>.json, ditulis ulang tiap ada perubahan."""

    def __init__(self, pid: str, permintaan: str, opsi: dict):
        PROD.mkdir(exist_ok=True)
        self.path = PROD / f"{pid}.json"
        self.d = {"id": pid, "permintaan": permintaan, "opsi": opsi, "dibuat": now(), "selesai": None,
                  "status": "berjalan", "slug": None, "pesan": "",
                  "tahap": [{"kunci": k, "job": j, "nama": n, "status": "menunggu", "mulai": None, "selesai": None, "catatan": ""} for k, j, n in TAHAP]}
        self.save()

    def save(self) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.d, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def tahap(self, kunci: str, status: str, catatan: str = "") -> None:
        t = next(x for x in self.d["tahap"] if x["kunci"] == kunci)
        t["status"] = status
        if status == "jalan":
            t["mulai"] = now()
        if status in ("ok", "gagal"):
            t["selesai"] = now()
        if catatan:
            t["catatan"] = catatan
        self.save()
        print(f"\n[produser] {t['nama']}: {status}{(' — ' + catatan) if catatan else ''}", flush=True)

    def akhir(self, status: str, pesan: str) -> None:
        self.d.update(status=status, pesan=pesan, selesai=now())
        self.save()
        print(f"\n[produser] {status.upper()}: {pesan}", flush=True)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def jalan(args: list[str], timeout: int) -> int:
    """Jalankan perintah, teruskan keluarannya ke log Studio."""
    print(f"[produser] $ {' '.join(a if len(a) < 80 else a[:77] + '…' for a in args[:4])}", flush=True)
    try:
        return subprocess.run(args, cwd=ROOT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print("[produser] waktu habis", flush=True)
        return 124


def videos() -> dict[str, str]:
    r = subprocess.run([PY, str(ROOT / "agents" / "pabrik.py"), "list", "--json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
    try:
        return {v["slug"]: v["status"] for v in json.loads(r.stdout or "[]")}
    except ValueError:
        return {}


def pabrik(*args: str) -> None:
    subprocess.run([PY, str(ROOT / "agents" / "pabrik.py"), *args], cwd=ROOT, check=True)


def claude(prompt: str, allowed: list[str], timeout: int) -> int:
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("perintah 'claude' tidak ditemukan")
    return jalan([exe, "-p", prompt, "--model", MODEL, "--max-turns", "60", "--allowedTools", *allowed], timeout)


def main() -> None:
    ap = argparse.ArgumentParser(description="Produser: permintaan → video jadi")
    ap.add_argument("permintaan")
    ap.add_argument("--suara", choices=["pria", "wanita"], default="pria")
    ap.add_argument("--visual", choices=["teliti", "cepat"], default="teliti")
    ap.add_argument("--id", default="")
    ap.add_argument("--uji", action="store_true", help="tanpa Claude & internet: data contoh, untuk mengetes alur")
    a = ap.parse_args()
    teks = re.sub(r"[^\w\s,.\-?!]", "", a.permintaan, flags=re.UNICODE).strip()[:200]
    if len(teks) < 3:
        sys.exit("[produser] permintaan terlalu pendek")
    pid = a.id if re.fullmatch(r"[\w-]{3,40}", a.id or "") else datetime.now().strftime("%Y%m%d-%H%M%S")
    cat = Catatan(pid, teks, {"suara": a.suara, "visual": a.visual, "uji": a.uji})
    slug = ""
    try:
        # 1. Nova
        cat.tahap("nova", "jalan")
        before = videos()
        if a.uji:
            sys.path.insert(0, str(ROOT / "agents"))
            import tes_pabrik as fx
            pabrik("new", fx.IDEA["judul_kerja"])
        else:
            claude(f"/ide-riset --permintaan {teks}", tools("agents/pabrik.py", web=True), 40 * 60)
        new = [s for s, st in videos().items() if s not in before and st == "ide"]
        if not new:
            cat.tahap("nova", "gagal", "Nova tidak membuat ide (topik tidak bisa diverifikasi dengan 2 sumber, atau melanggar bible). Coba topik yang lebih spesifik.")
            return cat.akhir("gagal", "Berhenti di tahap ide.")
        slug = sorted(new)[-1]
        cat.d["slug"] = slug
        if a.uji:
            (ROOT / "videos" / slug).mkdir(parents=True, exist_ok=True)
            (ROOT / "videos" / slug / "idea.json").write_text(json.dumps({**fx.IDEA, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        judul = json.loads((ROOT / "videos" / slug / "idea.json").read_text(encoding="utf-8-sig")).get("judul_kerja", slug)
        cat.tahap("nova", "ok", judul)

        # 2. disetujui oleh permintaan Zona
        cat.tahap("setuju", "jalan")
        pabrik("set", slug, "disetujui", "--note", f"disetujui lewat permintaan Zona: {teks[:80]}")
        cat.tahap("setuju", "ok")

        # 3. Raka
        cat.tahap("raka", "jalan")
        if a.uji:
            (ROOT / "videos" / slug / "script.json").write_text(json.dumps({**fx.SCRIPT, "slug": slug}, ensure_ascii=False), encoding="utf-8")
            pabrik("set", slug, "naskah")
        else:
            claude(f"/penulis {slug}", tools("agents/pabrik.py", "agents/penulis/cek_naskah.py"), 30 * 60)
        if videos().get(slug) != "naskah":
            cat.tahap("raka", "gagal", "Naskah belum lolos validasi. Buka log, lalu minta Raka menulis ulang dari kartu video.")
            return cat.akhir("gagal", "Berhenti di tahap naskah.")
        cat.tahap("raka", "ok", json.loads((ROOT / "videos" / slug / "script.json").read_text(encoding="utf-8-sig")).get("judul", ""))

        # 4. Dara
        cat.tahap("dara", "jalan")
        voice = ["--voice", "id-ID-GadisNeural"] if a.suara == "wanita" else []
        code = jalan([PY, "agents/suara/buat_suara.py", slug, *voice, *(["--uji"] if a.uji else [])], 10 * 60)
        if a.uji and code == 0:
            pabrik("set", slug, "suara")
        if code != 0 or videos().get(slug) != "suara":
            cat.tahap("dara", "gagal", "Suara gagal dibuat (cek internet / edge-tts).")
            return cat.akhir("gagal", "Berhenti di tahap suara.")
        w = json.loads((ROOT / "videos" / slug / "words.json").read_text(encoding="utf-8"))
        cat.tahap("dara", "ok", f"{w.get('durasi')} detik")

        # 5. Bima
        cat.tahap("bima", "jalan")
        if a.uji:
            (ROOT / "videos" / slug / "aset").mkdir(exist_ok=True)
            (ROOT / "videos" / slug / "aset" / "rencana.json").write_text(json.dumps(fx.RENCANA), encoding="utf-8")
            code = jalan([PY, "agents/aset/cari_aset.py", "semua", slug, "--uji"], 30 * 60)
            if code == 0:
                pabrik("set", slug, "aset")
        elif a.visual == "cepat":
            jalan([PY, "agents/aset/cari_aset.py", "semua", slug], 40 * 60)
        else:
            claude(f"/aset {slug}", tools("agents/pabrik.py", "agents/aset/cari_aset.py"), 50 * 60)
        if videos().get(slug) != "aset":
            cat.tahap("bima", "gagal", "Visual belum lengkap. Buka kartu video untuk melihat kalimat yang kurang.")
            return cat.akhir("gagal", "Berhenti di tahap visual.")
        m = json.loads((ROOT / "videos" / slug / "aset" / "manifest.json").read_text(encoding="utf-8"))
        cat.tahap("bima", "ok", f"{len(m.get('klip', []))} shot")

        # 6. Kai
        cat.tahap("kai", "jalan")
        code = jalan([PY, "agents/editor/rakit.py", slug, *(["--uji"] if a.uji else [])], 30 * 60)
        if a.uji and code == 0:
            pabrik("set", slug, "draft")
        if code != 0 or not (ROOT / "videos" / slug / "export" / "final.mp4").exists():
            cat.tahap("kai", "gagal", "Video gagal dirakit. Cek log.")
            return cat.akhir("gagal", "Berhenti di tahap rakit.")
        cat.tahap("kai", "ok", "export/final.mp4")
        cat.akhir("selesai", "Video jadi. Tonton lalu setujui di Studio.")
    except Exception as err:  # jangan sampai catatan tertinggal 'berjalan'
        for t in cat.d["tahap"]:
            if t["status"] == "jalan":
                t["status"] = "gagal"
                t["catatan"] = f"{type(err).__name__}: {err}"[:200]
        cat.akhir("gagal", f"Error tak terduga: {err}"[:200])
        raise


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[produser] total {time.time() - t0:.0f} dtk", flush=True)

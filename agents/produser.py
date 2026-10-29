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
    ("steve", "fetch", "Steve memperbarui daftar video channel"),
    ("nova", "ide", "Nova memilih & meriset topik baru"),
    ("setuju", "", "Ide disetujui (tombol Buat video-mu)"),
    ("raka", "penulis", "Raka menulis naskah"),
    ("dara", "suara", "Dara membuat suara"),
    ("bima", "aset", "Bima menyiapkan visual"),
    ("kai", "editor", "Kai merakit video"),
    ("rara", "qc", "Rara memeriksa kualitas"),
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
        if status == "jalan" and not t["mulai"]:
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


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


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
    ap.add_argument("permintaan", nargs="?", default="", help="arahan tema (opsional). Kosong = tim memilih topik sendiri")
    ap.add_argument("--suara", choices=["pria", "wanita"], default="pria")
    ap.add_argument("--visual", choices=["teliti", "cepat"], default="teliti")
    ap.add_argument("--id", default="")
    ap.add_argument("--uji", action="store_true", help="tanpa Claude & internet: data contoh, untuk mengetes alur")
    a = ap.parse_args()
    teks = re.sub(r"[^\w\s,.\-?!]", "", a.permintaan, flags=re.UNICODE).strip()[:200]
    judul_req = teks if len(teks) >= 3 else "Topik dipilih tim"
    if len(teks) < 3:
        teks = ""
    pid = a.id if re.fullmatch(r"[\w-]{3,40}", a.id or "") else datetime.now().strftime("%Y%m%d-%H%M%S")
    cat = Catatan(pid, judul_req, {"suara": a.suara, "visual": a.visual, "uji": a.uji})
    slug = ""
    try:
        # 0. Steve: daftar video channel terbaru, supaya Nova tidak mengulang topik lama
        cat.tahap("steve", "jalan")
        if a.uji:
            cat.tahap("steve", "ok", "mode uji: memakai snapshot yang ada")
        elif jalan([PY, "agents/steve/fetch_stats.py"], 5 * 60) == 0:
            cat.tahap("steve", "ok", "daftar video channel terbaru")
        else:
            cat.tahap("steve", "ok", "gagal mengambil data baru; memakai snapshot terakhir")

        # 1. Nova: tim memilih topik (arahan Zona hanya arah), wajib belum pernah dibahas
        cat.tahap("nova", "jalan")
        sys.path.insert(0, str(ROOT / "agents"))
        slug, alasan_tolak = "", ""
        for coba in range(2):
            before = videos()
            if a.uji:
                import tes_pabrik as fx
                pabrik("new", fx.IDEA["judul_kerja"])
            else:
                extra = "" if coba == 0 else f" (percobaan ke-2: ide sebelumnya ditolak karena {alasan_tolak}, pilih teknologi lain)"
                claude(f"/ide-riset --otomatis {teks}{extra}".strip(),
                       tools("agents/pabrik.py", "agents/ide/cek_topik.py", "agents/ide/cek_visual.py", "agents/ide/cek_ide.py", web=True), 45 * 60)
            new = [x for x, st in videos().items() if x not in before and st == "ide"]
            if not new:
                break
            cand = sorted(new)[-1]
            for extra_slug in sorted(new)[:-1]:  # mode otomatis = 1 ide; sisanya ditolak supaya antrean bersih
                pabrik("set", extra_slug, "ditolak", "--note", "kelebihan ide di mode otomatis")
            jk = json.loads((ROOT / "videos" / cand / "idea.json").read_text(encoding="utf-8-sig")).get("judul_kerja", cand) if (ROOT / "videos" / cand / "idea.json").exists() else cand
            dup = subprocess.run([PY, "agents/ide/cek_topik.py", jk, "--abaikan", cand], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
            if dup.returncode == 2 and not a.uji:
                print(dup.stdout, flush=True)
                pabrik("set", cand, "ditolak", "--note", "duplikat topik yang sudah ada di channel")
                cat.tahap("nova", "jalan", f"'{jk}' ternyata mirip video lama, cari topik lain")
                alasan_tolak = "duplikat topik lama"
                continue
            if not a.uji:   # editor riset: ide harus lolos validasi sumber, kutipan, angka, dan punya skor
                v = subprocess.run([PY, "agents/ide/cek_ide.py", cand, "--tulis"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                print(v.stdout, flush=True)
                if v.returncode != 0:
                    pabrik("set", cand, "ditolak", "--note", "gagal validasi ide (sumber/kutipan/angka)")
                    cat.tahap("nova", "jalan", f"'{jk}' belum lolos validasi sumber, cari lagi")
                    alasan_tolak = "tidak lolos validasi sumber/kutipan/angka"
                    continue
            slug = cand
            break
        if not slug:
            cat.tahap("nova", "gagal", "Nova tidak menemukan topik baru yang lolos verifikasi 2 sumber dan belum pernah dibahas. Coba lagi, atau beri arahan tema.")
            return cat.akhir("gagal", "Berhenti di tahap ide.")
        cat.d["slug"] = slug
        if a.uji:
            (ROOT / "videos" / slug).mkdir(parents=True, exist_ok=True)
            (ROOT / "videos" / slug / "idea.json").write_text(json.dumps({**fx.IDEA, "slug": slug}, ensure_ascii=False), encoding="utf-8")
        idea_now = json.loads((ROOT / "videos" / slug / "idea.json").read_text(encoding="utf-8-sig"))
        judul = idea_now.get("judul_kerja", slug)
        sk = (idea_now.get("skor") or {}).get("total")
        cat.tahap("nova", "ok", f"{judul}{f' · skor {sk}/100' if sk is not None else ''}")

        # 2. disetujui oleh permintaan Zona
        cat.tahap("setuju", "jalan")
        pabrik("set", slug, "disetujui", "--note", f"disetujui lewat tombol Buat video Zona{(': ' + teks[:80]) if teks else ' (topik dipilih tim)'}")
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
        # kontrol durasi: target ditentukan Raka (target_durasi). Atur kecepatan suara dulu; kalau masih jauh, Raka memangkas.
        d = float(w.get("durasi") or 0)
        tg = w.get("target") or {}
        t_det, t_lo, t_hi = float(tg.get("detik") or 40), float(tg.get("min") or 28), float(tg.get("maks") or 45)
        if not a.uji and (d > t_hi or d < t_lo):
            rate = round((1.15 * d / t_det - 1) * 100)
            if d > t_hi and rate > 28:
                cat.tahap("dara", "jalan", f"{d:.1f} dtk kepanjangan, Raka memangkas naskah")
                pabrik("set", slug, "naskah", "--note", f"suara {d:.1f} dtk, dipangkas")
                claude(f"/penulis {slug} --pangkas {d:.0f}", tools("agents/pabrik.py", "agents/penulis/cek_naskah.py"), 20 * 60)
                rate = 15
            rate = max(-5, min(28, rate))
            cat.tahap("dara", "jalan", f"{d:.1f} dtk di luar target, rekam ulang kecepatan +{rate}%")
            jalan([PY, "agents/suara/buat_suara.py", slug, *voice, "--rate", f"{rate:+d}%"], 10 * 60)
            w = json.loads((ROOT / "videos" / slug / "words.json").read_text(encoding="utf-8"))
            if videos().get(slug) != "suara":
                cat.tahap("dara", "gagal", "Rekam ulang gagal.")
                return cat.akhir("gagal", "Berhenti di tahap suara.")
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

        # 7. Rara (QC): periksa, ganti shot jelek, rakit ulang (maks 2 putaran)
        cat.tahap("rara", "jalan")
        if a.uji or a.visual == "cepat":
            jalan([PY, "agents/qc/periksa.py", "otomatis", slug, *(["--uji"] if a.uji else [])], 40 * 60)
        else:
            claude(f"/qc {slug}", tools("agents/pabrik.py", "agents/qc/periksa.py"), 60 * 60)
        q = rj(ROOT / "videos" / slug / "export" / "qc.json")
        rv = rj(ROOT / "videos" / slug / "export" / "qc_review.json")
        info = []
        if rv.get("skor") is not None:
            info.append(f"skor {rv['skor']}/10")
        if q.get("putaran"):
            info.append(f"{q['putaran']} putaran perbaikan")
        if q.get("masalah"):
            info.append(f"{len(q['masalah'])} catatan")
        cat.tahap("rara", "ok", ", ".join(info) or "lolos pemeriksaan otomatis")
        cat.akhir("selesai", "Video jadi dan sudah diperiksa Rara. Tonton lalu setujui di Studio.")
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

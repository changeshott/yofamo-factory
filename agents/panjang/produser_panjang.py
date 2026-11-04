#!/usr/bin/env python3
"""Produser Ruang Animasi: satu klik → video YouTube panjang (5–8 menit) full animasi lukis-komik.

    python agents/panjang/produser_panjang.py ["arahan tema"]          # Bayu pilih topik → … → video draft
    python agents/panjang/produser_panjang.py --lanjut <slug>          # lanjutkan yang terhenti (tahap yang beres dilewati)
    python agents/panjang/produser_panjang.py --uji                    # tanpa Claude & internet (naskah contoh), untuk tes

Tahap: Bayu (riset & alur, Claude) → Citra (naskah adegan, Claude) → Gilang (suara) → Laras (host & ilustrasi FLUX.2 klein)
→ Tio (animasi HyperFrames) → Wulan (rakit + QC) → status draft: Zona menonton & menyetujui di Studio (Ruang Animasi).
Tidak mengganggu Shorts: seluruh proses berjalan dengan prioritas CPU rendah, dan render tiap adegan menunggu dulu
kalau produksi Shorts sedang berjalan (produksi/produser.lock). Satu video panjang pada satu waktu (produksi/panjang.lock).
Kemajuan: produksi/panjang/<id>.json, log di logs/.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
from kunci import Kunci  # noqa: E402
import produser as pr  # noqa: E402  (claude() dengan coba ulang, tools())

PY = sys.executable
PROD = ROOT / "produksi" / "panjang"
CONTOH = Path(__file__).with_name("contoh")
TAHAP = [("bayu", "p_ide", "Bayu meriset topik & alur"), ("citra", "p_naskah", "Citra menulis naskah adegan"),
         ("gilang", "p_suara", "Gilang mengisi suara"), ("laras", "p_ilustrasi", "Laras menggambar ilustrasi"),
         ("tio", "p_animasi", "Tio menganimasikan adegan"), ("wulan", "p_rakit", "Wulan merakit & memeriksa")]


class Catatan:
    def __init__(self, pid: str, permintaan: str, opsi: dict):
        PROD.mkdir(parents=True, exist_ok=True)
        self.path = PROD / f"{pid}.json"
        self.d = {"id": pid, "permintaan": permintaan, "opsi": opsi, "dibuat": now(), "selesai": None, "status": "berjalan",
                  "slug": None, "pesan": "", "tahap": [{"kunci": k, "job": j, "nama": n, "status": "menunggu", "mulai": None, "selesai": None, "catatan": ""}
                                                      for k, j, n in TAHAP]}
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
        print(f"\n[produser-panjang] {t['nama']}: {status}{(' — ' + catatan) if catatan else ''}", flush=True)

    def akhir(self, status: str, pesan: str) -> None:
        self.d.update(status=status, pesan=pesan, selesai=now())
        self.save()
        print(f"\n[produser-panjang] {status.upper()}: {pesan}", flush=True)


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def jalan(args: list[str], timeout: int) -> int:
    print(f"[produser-panjang] $ {' '.join(args[1:4])}", flush=True)
    try:
        return subprocess.run(args, cwd=ROOT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print("[produser-panjang] waktu habis", flush=True)
        return 124


def slug_baru(sebelum: set[str]) -> str | None:
    baru = [d.name for d in st_panjang.BASE.glob("*") if d.is_dir() and d.name not in sebelum and (d / "ide.json").exists()]
    return sorted(baru, key=lambda s: (st_panjang.BASE / s / "ide.json").stat().st_mtime)[-1] if baru else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Produser video panjang")
    ap.add_argument("permintaan", nargs="?", default="")
    ap.add_argument("--lanjut", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    teks = re.sub(r"[^\w\s,.\-?!]", "", a.permintaan, flags=re.UNICODE).strip()[:200]
    pid = a.id if re.fullmatch(r"[\w-]{3,40}", a.id or "") else datetime.now().strftime("%Y%m%d-%H%M%S")
    cat = Catatan(pid, teks or ("Lanjutkan: " + a.lanjut if a.lanjut else "Topik dipilih tim"), {"uji": a.uji})
    tanpa_jendela.prioritas_rendah()
    kunci = Kunci(ROOT / "produksi" / ("panjang-uji.lock" if a.uji else "panjang.lock"), maks_jam=12)
    if not kunci.ambil(pid):
        cat.tahap("bayu", "gagal", "Masih ada video panjang lain yang sedang dibuat.")
        cat.akhir("gagal", "Masih ada video panjang lain yang sedang dibuat. Tunggu selesai.")
        sys.exit(3)
    try:
        # 1. Bayu: topik + riset + alur bab
        slug = a.lanjut
        if slug:
            if not st_panjang.status(slug):
                cat.tahap("bayu", "gagal", f"Video '{slug}' tidak ditemukan.")
                return cat.akhir("gagal", "Video tidak ditemukan.")
            cat.tahap("bayu", "ok", "sudah beres sebelumnya")
        else:
            cat.tahap("bayu", "jalan")
            if a.uji:
                slug = "uji-" + datetime.now().strftime("%H%M%S") + "-kulit-robot"
                vdir = st_panjang.folder(slug)
                vdir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(CONTOH / "ide.json", vdir / "ide.json")
                st_panjang.set_status(slug, "ide", "mode uji")
            else:
                sebelum = {d.name for d in st_panjang.BASE.glob("*")} if st_panjang.BASE.is_dir() else set()
                pr.claude(f"/panjang-ide {teks}".strip(), pr.tools("agents/panjang/status.py", "agents/ide/radar.py", "agents/ide/cek_topik.py", web=True),
                          60 * 60, turns=50)
                slug = slug_baru(sebelum)
            if not slug:
                cat.tahap("bayu", "gagal", "Bayu belum menulis ide.json.")
                return cat.akhir("gagal", "Berhenti di tahap riset.")
        cat.d["slug"] = slug
        vdir = st_panjang.folder(slug)
        ide = json.loads((vdir / "ide.json").read_text(encoding="utf-8-sig"))
        cat.tahap("bayu", "ok", ide.get("judul_kerja", slug))

        # 2. Citra: naskah adegan
        cat.tahap("citra", "jalan")
        if not st_panjang.sudah(slug, "naskah"):
            if a.uji:
                n = json.loads((CONTOH / "naskah.json").read_text(encoding="utf-8"))
                (vdir / "naskah.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
                st_panjang.set_status(slug, "naskah", "mode uji")
            else:
                pr.claude(f"/panjang-naskah {slug}", pr.tools("agents/panjang/status.py", "agents/panjang/cek_naskah_panjang.py"), 60 * 60, turns=60)
        if not st_panjang.sudah(slug, "naskah"):
            cat.tahap("citra", "gagal", "Naskah belum lolos cek_naskah_panjang.py.")
            return cat.akhir("gagal", "Berhenti di tahap naskah.")
        naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
        cat.tahap("citra", "ok", f"{naskah.get('judul', '')} · {len(naskah.get('adegan', []))} adegan")

        # 3. Gilang: suara
        cat.tahap("gilang", "jalan")
        if not st_panjang.sudah(slug, "suara") and jalan([PY, "agents/panjang/suara_panjang.py", slug, *(["--uji"] if a.uji else [])], 40 * 60) != 0:
            cat.tahap("gilang", "gagal", "Suara gagal dibuat (cek internet / edge-tts).")
            return cat.akhir("gagal", "Berhenti di tahap suara.")
        w = json.loads((vdir / "suara" / "waktu.json").read_text(encoding="utf-8"))
        cat.tahap("gilang", "ok", f"{sum(x['durasi'] for x in w.values()) / 60:.1f} menit")

        # 4. Laras: ilustrasi
        cat.tahap("laras", "jalan")
        if not a.uji and not (ROOT / "bible" / "maskot" / "pose" / "bicara.png").exists():
            # host Yofa belum pernah digambar: buat otomatis (kandidat 1). Zona bisa ganti kapan saja di Studio → Gaya & host.
            cat.tahap("laras", "jalan", "menggambar host Yofa pertama kali…")
            jalan([PY, "agents/panjang/maskot.py", "otomatis"], 30 * 60)
        acuan_meta = ROOT / "bible" / "maskot" / "acuan-gaya.json"
        if not a.uji and (ROOT / "bible" / "maskot" / "pose" / "bicara.png").exists() and not acuan_meta.exists():
            cat.tahap("laras", "jalan", "menggambar ulang acuan gaya tanpa orang…")
            jalan([PY, "agents/panjang/maskot.py", "acuan-gaya"], 10 * 60)
        if not st_panjang.sudah(slug, "ilustrasi"):
            if jalan([PY, "agents/panjang/ilustrasi.py", slug, *(["--uji"] if a.uji else [])], 60 * 60) == 5:
                cat.tahap("laras", "gagal", "Kuota gambar gratis Cloudflare hari ini habis. Lanjutkan setelah 07:00 WIB.")
                return cat.akhir("gagal", "Berhenti di tahap ilustrasi (kuota gambar habis). Tekan Lanjutkan setelah 07:00 WIB.")
        n_il = len(list((vdir / "ilustrasi").glob("*.jpg"))) if (vdir / "ilustrasi").is_dir() else 0
        cat.tahap("laras", "ok", f"{n_il} gambar")

        # 5–6. Tio & Wulan: render berat (prioritas rendah; tiap adegan menunggu kalau produksi Shorts sedang jalan)
        cat.tahap("tio", "jalan", "merender adegan (Shorts tetap didahulukan)…")
        if jalan([PY, "agents/panjang/animasi.py", slug, *(["--uji"] if a.uji else [])], 12 * 3600) != 0:
            cat.tahap("tio", "gagal", "Render adegan gagal. Cek log, lalu Lanjutkan (adegan yang sudah jadi tidak dirender ulang).")
            return cat.akhir("gagal", "Berhenti di tahap animasi.")
        cat.tahap("tio", "ok", f"{len(naskah['adegan'])} adegan")
        cat.tahap("wulan", "jalan")
        if jalan([PY, "agents/panjang/rakit_panjang.py", slug, *(["--uji"] if a.uji else [])], 3 * 3600) != 0:
            cat.tahap("wulan", "gagal", "Rakit gagal. Cek log.")
            return cat.akhir("gagal", "Berhenti di tahap rakit.")
        jalan([PY, "agents/panjang/periksa_panjang.py", slug], 30 * 60)
        q = json.loads((vdir / "export" / "qc.json").read_text(encoding="utf-8")) if (vdir / "export" / "qc.json").exists() else {}
        info = json.loads((vdir / "export" / "info.json").read_text(encoding="utf-8"))
        cat.tahap("wulan", "ok", f"{info['durasi'] / 60:.1f} menit, {len(info.get('bab', []))} bab" + (f", {len(q.get('masalah', []))} masalah" if q.get("masalah") else ", lolos QC"))
        cat.akhir("selesai", "Video panjang jadi. Tonton lalu setujui di Studio (Ruang Animasi).")
    except Exception as err:
        for t in cat.d["tahap"]:
            if t["status"] == "jalan":
                t["status"] = "gagal"
                t["catatan"] = f"{type(err).__name__}: {err}"[:200]
        cat.akhir("gagal", f"Error tak terduga: {err}"[:200])
        raise


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"[produser-panjang] total {time.time() - t0:.0f} dtk", flush=True)

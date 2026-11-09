#!/usr/bin/env python3
"""Produser Ruang Animasi: satu klik → video YouTube panjang (5–12 menit) gaya dokumenter modern:
footage asli teknologi yang dibahas (tanpa teks di dalamnya) + selingan motion graphic (kertas abu-abu, serif, benda asli).

    python agents/panjang/produser_panjang.py ["arahan tema"]          # Bayu pilih topik → … → video draft
    python agents/panjang/produser_panjang.py --lanjut <slug>          # lanjutkan yang terhenti (tahap yang beres dilewati)
    python agents/panjang/produser_panjang.py --uji                    # tanpa Claude & internet (naskah contoh), untuk tes

Tahap: Bayu (riset & alur + cek footage, Claude) → Citra (naskah adegan dokumenter, Claude) → Gilang (suara)
→ Laras (footage 16:9 + objek asli, dicek OCR; kurang → Citra mengganti kata kunci → cadangan pinjam shot adegan terdekat)
→ Tio (motion graphic HyperFrames + footage berbutiran & subtitle) → Wulan (rakit + QC berskor) → status draft:
Zona menonton & menyetujui di Studio (Ruang Animasi), atau autopilot video panjang menyetujui otomatis kalau QC lolos.
Video lama format kartun (naskah tanpa "format": "dokumenter") tetap dilanjutkan dengan jalur lama (ilustrasi.py + animasi.py).
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
         ("gilang", "p_suara", "Gilang mengisi suara"), ("laras", "p_ilustrasi", "Laras mencari footage & objek asli"),
         ("tio", "p_animasi", "Tio membuat motion graphic & merender"), ("wulan", "p_rakit", "Wulan merakit & memeriksa")]


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
        kode = subprocess.run(args, cwd=ROOT, timeout=timeout).returncode
    except subprocess.TimeoutExpired:
        print("[produser-panjang] waktu habis", flush=True)
        return 124
    if kode != 0:
        print(f"[produser-panjang] {Path(args[1]).name} berhenti dengan kode {kode}", flush=True)
    return kode


def jalan_ulang(args: list[str], timeout: int, coba: int = 3, kode_tetap: tuple[int, ...] = (2,)) -> int:
    """Untuk tahap yang bisa dilanjutkan dari titik terakhir (footage, render, rakit): kalau prosesnya berhenti tiba-tiba
    (dimatikan, kehabisan memori, jendela ditutup), langsung dicoba lagi — bagian yang sudah jadi tidak diulang.
    Kode di `kode_tetap` (mis. 2 = footage kurang) tidak diulang di sini karena butuh penanganan lain."""
    kode = 1
    for n in range(coba):
        kode = jalan(args, timeout)
        if kode == 0 or kode in kode_tetap or kode == 124:
            return kode
        if n + 1 < coba:
            print(f"[produser-panjang] dicoba lagi otomatis ({n + 2}/{coba}), melanjutkan dari bagian terakhir…", flush=True)
            time.sleep(30)
    return kode


def slug_baru(sebelum: set[str]) -> str | None:
    baru = [d.name for d in st_panjang.BASE.glob("*") if d.is_dir() and d.name not in sebelum and (d / "ide.json").exists()]
    return sorted(baru, key=lambda s: (st_panjang.BASE / s / "ide.json").stat().st_mtime)[-1] if baru else None


def kurang_footage(vdir: Path) -> list[int]:
    """Nomor adegan (1-based) yang butuh footage tapi belum punya shot."""
    try:
        n = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
        man = json.loads((vdir / "footage" / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [i + 1 for i, ad in enumerate(n.get("adegan") or []) if ad.get("jenis") in ("footage", "pembuka", "hp", "tv") and not man.get(str(i))]


def tinjau_visual(slug: str) -> dict:
    """Wulan (Claude) melihat lembar frame bernomor & thumbnail, mengganti adegan berat (maks 1 putaran) → export/qc_review.json.
    Melempar KuotaClaude/LoginClaude/Offline dari produser.claude (pemanggil yang memutuskan)."""
    rv = st_panjang.folder(slug) / "export" / "qc_review.json"
    rv.unlink(missing_ok=True)
    pr.claude(f"/qc-panjang {slug}", pr.tools("agents/panjang/periksa_panjang.py", "agents/panjang/footage_panjang.py", "agents/panjang/dokumenter.py",
                                               "agents/panjang/rakit_panjang.py", "agents/panjang/status.py"), 120 * 60, turns=70)
    try:
        return json.loads(rv.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def rakit(cat: Catatan, slug: str, vdir: Path, naskah: dict, uji: bool) -> None:
    cat.tahap("wulan", "jalan")
    if jalan_ulang([PY, "agents/panjang/rakit_panjang.py", slug, *(["--uji"] if uji else [])], 3 * 3600, coba=2) != 0:
        cat.tahap("wulan", "gagal", "Rakit gagal. Cek log.")
        return cat.akhir("gagal", "Berhenti di tahap rakit.")
    jalan([PY, "agents/panjang/periksa_panjang.py", slug], 30 * 60)
    rv = {}
    if not uji and (vdir / "export" / "final.mp4").exists():
        cat.tahap("wulan", "jalan", "QC visual: melihat frame tiap adegan & thumbnail…")
        try:
            rv = tinjau_visual(slug)
        except Exception as err:  # noqa: BLE001 — kuota Claude habis dll: video tetap jadi, QC visual menyusul (autopilot mengulang)
            cat.tahap("wulan", "jalan", f"QC visual tertunda: {str(err)[:120]}")
    q = json.loads((vdir / "export" / "qc.json").read_text(encoding="utf-8")) if (vdir / "export" / "qc.json").exists() else {}
    info = json.loads((vdir / "export" / "info.json").read_text(encoding="utf-8"))
    cat.tahap("wulan", "ok", f"{info['durasi'] / 60:.1f} menit, {len(info.get('bab', []))} bab, skor teknis {q.get('skor', '-')}"
              + (f", {len(q.get('masalah', []))} masalah" if q.get("masalah") else ", lolos cek teknis")
              + (f" · QC visual {rv.get('skor', '-')}{'' if rv.get('lolos') else ' (belum lolos)'}" if rv else "" if uji else " · QC visual menyusul"))
    cat.akhir("selesai", "Video panjang jadi. Tonton lalu setujui di Studio (Ruang Animasi)"
              + (" — atau autopilot menyetujui & menjadwalkannya otomatis." if cat.d.get("id", "").startswith("autopilot") else "."))


def main() -> None:
    ap = argparse.ArgumentParser(description="Produser video panjang")
    ap.add_argument("permintaan", nargs="?", default="")
    ap.add_argument("--lanjut", default="")
    ap.add_argument("--id", default="")
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    teks = re.sub(r"[^\w\s,.\-?!]", "", a.permintaan, flags=re.UNICODE).strip()[:200]
    pid = a.id if re.fullmatch(r"[\w-]{3,40}", a.id or "") else datetime.now().strftime("%Y%m%d-%H%M%S")
    import os
    os.environ["YOFAMO_PRODUKSI_ID"], os.environ["YOFAMO_PRODUKSI_JENIS"] = pid, "panjang"     # pencatatan token per video
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
                pr.claude(f"/panjang-ide {teks}".strip(), pr.tools("agents/panjang/status.py", "agents/ide/radar.py", "agents/ide/cek_topik.py",
                                                                    "agents/ide/cek_visual.py", web=True),
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
                n = json.loads((CONTOH / "naskah-dokumenter.json").read_text(encoding="utf-8"))
                (vdir / "naskah.json").write_text(json.dumps(n, ensure_ascii=False, indent=1), encoding="utf-8")
                st_panjang.set_status(slug, "naskah", "mode uji")
            else:
                pr.claude(f"/panjang-naskah {slug}", pr.tools("agents/panjang/status.py", "agents/panjang/cek_naskah_panjang.py", "agents/ide/cek_visual.py"),
                          60 * 60, turns=60)
        if not st_panjang.sudah(slug, "naskah"):
            cat.tahap("citra", "gagal", "Naskah belum lolos cek_naskah_panjang.py.")
            return cat.akhir("gagal", "Berhenti di tahap naskah.")
        naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
        dok = naskah.get("format") == "dokumenter"
        cat.d["format"] = "dokumenter" if dok else "kartun"
        cat.tahap("citra", "ok", f"{naskah.get('judul', '')} · {len(naskah.get('adegan', []))} adegan")

        # 3. Gilang: suara
        cat.tahap("gilang", "jalan")
        if not st_panjang.sudah(slug, "suara") and jalan_ulang([PY, "agents/panjang/suara_panjang.py", slug, *(["--uji"] if a.uji else [])], 40 * 60, coba=2) != 0:
            cat.tahap("gilang", "gagal", "Suara gagal dibuat (cek internet / edge-tts).")
            return cat.akhir("gagal", "Berhenti di tahap suara.")
        w = json.loads((vdir / "suara" / "waktu.json").read_text(encoding="utf-8"))
        cat.tahap("gilang", "ok", f"{sum(x['durasi'] for x in w.values()) / 60:.1f} menit")

        # 4. Laras: footage & objek asli (dokumenter) — atau ilustrasi (kartun lama)
        if dok:
            cat.tahap("laras", "jalan", "mencari footage 16:9 tanpa teks & memotong objek asli…")
            if not st_panjang.sudah(slug, "ilustrasi"):
                kode = jalan_ulang([PY, "agents/panjang/footage_panjang.py", slug, *(["--uji"] if a.uji else [])], 3 * 3600)
                if kode == 2 and not a.uji:
                    # footage bersih kurang: Citra mengganti kata kunci visual adegan itu, lalu Laras mencari ulang
                    kurang = kurang_footage(vdir)
                    cat.tahap("laras", "jalan", f"footage kurang di adegan {kurang}; Citra mengganti kata kunci…")
                    pr.claude(f"/panjang-naskah {slug} --visual {','.join(map(str, kurang))}",
                              pr.tools("agents/panjang/status.py", "agents/panjang/cek_naskah_panjang.py", "agents/ide/cek_visual.py"), 30 * 60, turns=30)
                    kode = jalan([PY, "agents/panjang/footage_panjang.py", slug, "--ulang", *map(str, kurang)], 2 * 3600)
                if kode == 2:
                    cat.tahap("laras", "jalan", f"masih kurang di adegan {kurang_footage(vdir)}; meminjam shot adegan terdekat…")
                    kode = jalan([PY, "agents/panjang/footage_panjang.py", slug, "--cadangan", *(["--uji"] if a.uji else [])], 3600)
                if kode != 0:
                    cat.tahap("laras", "gagal", "Footage tidak cukup (cek log). Ubah kata kunci visual di naskah lalu Lanjutkan.")
                    return cat.akhir("gagal", "Berhenti di tahap footage.")
            man = json.loads((vdir / "footage" / "manifest.json").read_text(encoding="utf-8")) if (vdir / "footage" / "manifest.json").exists() else {}
            n_media = len(list((vdir / "media").glob("*.png"))) if (vdir / "media").is_dir() else 0
            cat.tahap("laras", "ok", f"{sum(len(v) for v in man.values())} shot footage, {n_media} objek asli")
            cat.tahap("tio", "jalan", "motion graphic & footage (Shorts tetap didahulukan)…")
            if jalan_ulang([PY, "agents/panjang/dokumenter.py", slug, *(["--uji"] if a.uji else [])], 12 * 3600) != 0:
                cat.tahap("tio", "gagal", "Render adegan gagal. Cek log, lalu Lanjutkan (adegan yang sudah jadi tidak dirender ulang).")
                return cat.akhir("gagal", "Berhenti di tahap render.")
            cat.tahap("tio", "ok", f"{len(naskah['adegan'])} adegan")
            return rakit(cat, slug, vdir, naskah, a.uji)
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
        return rakit(cat, slug, vdir, naskah, a.uji)
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

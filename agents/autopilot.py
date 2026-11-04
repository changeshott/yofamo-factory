#!/usr/bin/env python3
"""Autopilot Yofamo — tim bekerja sendiri: membuat video & menjadwalkan tayang (bawaan 3 video/hari).

    python agents/autopilot.py jalan            # satu putaran (dipanggil tiap jam oleh Windows Task Scheduler)
    python agents/autopilot.py status           # jadwal hari ini & besok, video yang terisi, produksi hari ini
    python agents/autopilot.py nyala | mati     # hidupkan / matikan autopilot (bible/autopilot.json → aktif)

Satu putaran:
  1. Hitung ulang jam tayang terbaik (agents/upload/jadwal.py → insights/jadwal.md) kalau sudah > 6 jam.
  2. Video yang jam tayangnya sudah lewat → status 'terbit'.
  3. Isi slot tayang sampai akhir hari "isi_hari" (bawaan 2 = hari ini + besok) dengan video siap: status 'export' yang belum diupload (sudah disetujui Zona),
     lalu video buatan autopilot yang lolos Rara dengan skor >= skor_qc_min (disetujui otomatis kalau setujui_otomatis).
     Uli mengunggahnya PRIVATE + jadwal tayang → YouTube menayangkan sendiri tepat di jam itu.
  4. Slot hari ini & besok yang belum punya video → produser membuat video baru, berurutan dari slot terdekat
     (hari pertama 6 video: 3 tayang hari ini + 3 besok; hari berikutnya cukup menambah stok besok)
     (Nova pilih topik baru → Raka → Dara → Bima → Kai → Rara), maksimal maks_produksi_per_hari.
Video buatan autopilot yang skornya di bawah batas tetap 'draft' dan menunggu Zona di Studio.
Hanya satu putaran yang berjalan pada satu waktu (produksi/autopilot.lock); produksi tidak bentrok dengan tombol Studio.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "upload"))
import tanpa_jendela  # noqa: E402,F401  (Windows: claude/ffmpeg/node tanpa jendela console)
from kunci import Kunci  # noqa: E402
import jadwal  # noqa: E402

PY = sys.executable
CONFIG = ROOT / "bible" / "autopilot.json"
STATE = ROOT / "produksi" / "autopilot.json"
VIDEOS = ROOT / "videos"
WIB = timezone(timedelta(hours=7))
UJI = False
SEKARANG: datetime | None = None
LOG_FILE: Path | None = None
API_LIMIT = re.compile(r"Kuota Claude|usage limit|limit reached|rate.?limit|credit balance|hit your [\w -]*limit|\d+-hour limit", re.I)
RESET = re.compile(r"(?:resets?|pulih) (?:at )?(\d{1,2})(?::(\d\d))?\s*(am|pm)?", re.I)


def jam_pulih(teks: str) -> datetime:
    """Kapan kuota Claude pulih (dari pesan 'resets 1:10pm'); kalau tidak ada, 3 jam lagi."""
    m = RESET.search(teks)
    if not m:
        return now() + timedelta(hours=3)
    h, mnt, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    h = h % 12 + (12 if ap == "pm" else 0) if ap else h
    t = now().replace(hour=h % 24, minute=mnt, second=0, microsecond=0)
    if t <= now():
        t += timedelta(days=1)
    return t + timedelta(minutes=5)


def now() -> datetime:
    return SEKARANG or datetime.now(WIB)


def log(msg: str) -> None:
    line = f"[autopilot {now().strftime('%H:%M')}] {msg}"
    print(line, flush=True)
    if LOG_FILE:
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def rj(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if default is None else default


def wj(p: Path, d) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def cfg() -> dict:
    c = rj(CONFIG)
    return {"aktif": bool(c.get("aktif", False)), "n": max(1, min(6, int(c.get("video_per_hari", 3)))),
            "setujui": bool(c.get("setujui_otomatis", True)), "skor_min": float(c.get("skor_qc_min", 7)),
            "maks_produksi": max(1, int(c.get("maks_produksi_per_hari", 8))), "jam_sebelum": float(c.get("mulai_produksi_jam_sebelum", 48)),
            "isi_hari": max(1, min(3, int(c.get("isi_hari", 2)))),
            "suara": c.get("suara", "pria") if c.get("suara") in ("pria", "wanita") else "pria",
            "visual": c.get("visual", "teliti") if c.get("visual") in ("teliti", "cepat") else "teliti",
            "arahan": re.sub(r"[^\w\s,.\-?!]", "", str(c.get("arahan_tema", "")), flags=re.UNICODE)[:200]}


def pabrik(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([PY, str(ROOT / "agents" / "pabrik.py"), *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def daftar_video() -> dict[str, str]:
    try:
        return {v["slug"]: v["status"] for v in json.loads(pabrik("list", "--json").stdout or "[]")}
    except ValueError:
        return {}


# ------------------------------------------------------------------ slot
def akhir_stok(c: dict) -> datetime:
    """Batas stok: akhir hari ke-isi_hari (2 = sampai tengah malam besok)."""
    return datetime.combine(now().date() + timedelta(days=c["isi_hari"]), datetime.min.time()).replace(tzinfo=WIB)


def pengganti(state: dict, data: dict, tgl: str, asli: datetime, jam_hari: list[datetime]) -> datetime | None:
    """Slot hari ini yang terlewat (video belum siap) dipindah ke jam lain hari ini yang masih sempat:
    skor jadwal tertinggi, ≥ 1 jam dari sekarang, ≤ jam_akhir, berjarak ≥ 2 jam dari slot lain. Hasilnya dicatat supaya tetap."""
    peta = state.setdefault("pengganti", {})
    k = kunci_slot(asli)
    if k in peta:
        try:
            return datetime.strptime(peta[k], "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
        except ValueError:
            return None
    akhir = int((data.get("pengaturan") or {}).get("jam_akhir", 22))
    lain = [t for t in jam_hari if t != asli] + [datetime.strptime(v, "%Y-%m-%d %H:%M").replace(tzinfo=WIB) for v in peta.values() if v.startswith(tgl)]
    calon = []
    for j in data.get("jam") or []:
        t = datetime.fromisoformat(f"{tgl}T{int(j['jam']):02d}:00").replace(tzinfo=WIB)
        if t >= now() + timedelta(minutes=60) and t.hour <= akhir and all(abs((t - x).total_seconds()) >= 2 * 3600 for x in lain):
            calon.append((j["skor"], t))
    if not calon:
        return None
    t = max(calon)[1]
    peta[k] = kunci_slot(t)
    log(f"slot {asli.strftime('%H:%M')} terlewat (video belum siap) → diganti {t.strftime('%H:%M')} hari ini")
    return t


def slot_ke_depan(state: dict, n: int, jam_ke_depan: float = 48, batas: datetime | None = None) -> list[datetime]:
    data = rj(jadwal.OUT_JSON)
    out: list[datetime] = []
    ujung = min(now() + timedelta(hours=jam_ke_depan), batas) if batas else now() + timedelta(hours=jam_ke_depan)
    hari_ini = now().date().isoformat()
    for tgl, slots in (data.get("slot") or {}).items():
        jam_hari = []
        for s in slots[:n]:
            try:
                jam_hari.append(datetime.fromisoformat(f"{tgl}T{s['jam']}").replace(tzinfo=WIB))
            except (ValueError, KeyError):
                continue
        for t in jam_hari:
            if tgl == hari_ini and t < now() + timedelta(minutes=20) and kunci_slot(t) not in state["slot"]:
                t = pengganti(state, data, tgl, t, jam_hari) or t      # 3 video tetap tayang hari ini kalau masih sempat
            if now() + timedelta(minutes=20) <= t < ujung and kunci_slot(t) not in state["slot"]:
                out.append(t)
    return sorted(set(out))


def kunci_slot(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M")


def perbarui_jadwal(n: int) -> None:
    d = rj(jadwal.OUT_JSON)
    try:
        umur = abs((now() - datetime.fromisoformat(d["dibuat"])).total_seconds()) / 3600
    except (KeyError, ValueError, TypeError):
        umur = 99
    hari = (d.get("slot") or {})
    if umur > 6 or d.get("video_per_hari") != n or now().date().isoformat() not in hari:
        data = jadwal.tulis(jadwal.hitung(), n, mulai=now().date())
        log("jadwal tayang diperbarui: " + "; ".join(f"{k}: {', '.join(s['jam'] for s in v)}" for k, v in list(data["slot"].items())[:2]))


# ------------------------------------------------------------------ video siap
def skor_qc(slug: str) -> tuple[float | None, bool]:
    rv = rj(VIDEOS / slug / "export" / "qc_review.json")
    skor = rv.get("skor")
    try:
        skor = float(skor) if skor is not None else None
    except (TypeError, ValueError):
        skor = None
    return skor, rv.get("lolos") is not False


def siap_tayang(state: dict, c: dict) -> list[tuple[str, str]]:
    """[(slug, alasan)] urut: yang sudah disetujui Zona dulu, lalu buatan autopilot yang lolos Rara."""
    vids = daftar_video()
    terisi = {v.get("slug") for v in state["slot"].values()}
    out = []
    for slug, st in sorted(vids.items()):
        exp = VIDEOS / slug / "export"
        info = rj(exp / "info.json")
        if slug in terisi or rj(exp / "upload.json").get("videoId") or not (exp / "final.mp4").exists():
            continue
        if info.get("uji") and not UJI:
            continue
        if st == "export":
            out.append((slug, "disetujui Zona"))
    for slug in state.get("dibuat", []):
        if vids.get(slug) != "draft" or slug in terisi or not c["setujui"]:
            continue
        exp = VIDEOS / slug / "export"
        if not (exp / "final.mp4").exists() or rj(exp / "upload.json").get("videoId"):
            continue
        skor, lolos = skor_qc(slug)
        if UJI and skor is None:
            skor = 10.0                      # mode uji: Rara otomatis tanpa skor
        if skor is not None and skor >= c["skor_min"] and lolos:
            out.append((slug, f"lolos Rara (skor {skor:g})"))
        elif not state.setdefault("menunggu_zona", {}).get(slug):
            state["menunggu_zona"][slug] = f"skor QC {skor if skor is not None else '-'} di bawah {c['skor_min']:g}; tunggu Zona"
            log(f"{slug}: skor QC {skor} di bawah batas, menunggu Zona menonton & menyetujui di Studio")
    return out


def unggah(slug: str, t: datetime) -> dict | None:
    jadwal_str = t.strftime("%Y-%m-%dT%H:%M")
    if UJI:
        log(f"[uji] {slug} → tayang {jadwal_str} WIB (tidak benar-benar diupload)")
        return {"videoId": "UJI", "url": "", "jadwal": jadwal_str}
    r = subprocess.run([PY, str(ROOT / "agents" / "upload" / "unggah.py"), "unggah", slug, "--jadwal", jadwal_str], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=3600)
    for line in (r.stdout + r.stderr).strip().splitlines()[-4:]:
        log(f"  {line}")
    up = rj(VIDEOS / slug / "export" / "upload.json")
    return up if up.get("videoId") else None


def isi_slot(state: dict, c: dict) -> int:
    slots = slot_ke_depan(state, c["n"], 72, akhir_stok(c))
    siap = siap_tayang(state, c)
    terisi = 0
    for t in slots:
        if not siap:
            break
        slug, alasan = siap.pop(0)
        if daftar_video().get(slug) == "draft":
            r = pabrik("set", slug, "export", "--note", f"disetujui otomatis oleh autopilot ({alasan})")
            if r.returncode != 0:
                log(f"{slug}: gagal disetujui otomatis: {r.stderr.strip()[-200:]}")
                continue
        up = unggah(slug, t)
        if not up:
            log(f"{slug}: upload gagal, dicoba lagi di putaran berikutnya")
            break
        state["slot"][kunci_slot(t)] = {"slug": slug, "videoId": up.get("videoId"), "url": up.get("url"), "status": "terjadwal", "alasan": alasan}
        terisi += 1
        log(f"{slug} dijadwalkan tayang {kunci_slot(t)} WIB ({alasan})")
    return terisi


def tandai_tayang(state: dict) -> None:
    for k, v in state["slot"].items():
        if v.get("status") != "terjadwal":
            continue
        t = datetime.strptime(k, "%Y-%m-%d %H:%M").replace(tzinfo=WIB)
        if t + timedelta(minutes=10) <= now():
            if not UJI:
                pabrik("set", v["slug"], "terbit", "--note", f"tayang terjadwal {k} WIB (autopilot)")
            v["status"] = "tayang"
            log(f"{v['slug']} sudah tayang ({k} WIB)")


# ------------------------------------------------------------------ produksi
def macet(state: dict) -> list[str]:
    """Video dari 'Buat video'/autopilot (3 hari terakhir) yang berhenti di tengah jalan (mis. rakit ulang terputus):
    dilanjutkan dulu sebelum membuat video baru — lebih hemat daripada mulai dari nol."""
    vids = daftar_video()
    out = []
    batas = time.time() - 3 * 86400
    for f in sorted((ROOT / "produksi").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        if f.name in ("autopilot.json", "antrean.json") or f.stat().st_mtime < batas:
            continue
        rec = rj(f)
        slug = rec.get("slug")
        if not slug or slug in out or rec.get("status") == "berjalan" or (rec.get("opsi") or {}).get("uji") and not UJI:
            continue
        st = vids.get(slug)
        exp, mf = VIDEOS / slug / "export", VIDEOS / slug / "aset" / "manifest.json"
        fin = exp / "final.mp4"
        selesai = st == "draft" and fin.exists() and not (mf.exists() and fin.stat().st_mtime < mf.stat().st_mtime)
        if st in ("disetujui", "naskah", "suara", "aset", "draft") and not selesai and state.setdefault("dilanjutkan", {}).get(slug, 0) < 2:
            out.append(slug)
    return out


def produksi(state: dict, c: dict, lanjut: str = "") -> str | None:
    pid = f"autopilot-{datetime.now(WIB).strftime('%Y%m%d-%H%M%S')}"
    args = [PY, str(ROOT / "agents" / "produser.py"), c["arahan"], "--suara", c["suara"], "--visual", c["visual"], "--id", pid]
    if lanjut:
        args += ["--lanjut", lanjut]
        state.setdefault("dilanjutkan", {})[lanjut] = state["dilanjutkan"].get(lanjut, 0) + 1
    if UJI:
        args.append("--uji")
    log(f"melanjutkan video yang terhenti: {lanjut} ({pid})…" if lanjut else f"memproduksi video baru ({pid})…")
    lf = ROOT / "logs" / f"produksi-{pid}.txt"
    lf.parent.mkdir(exist_ok=True)
    with lf.open("w", encoding="utf-8") as f:
        f.write(f"# Produksi autopilot — {now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.flush()
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
        try:
            subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, env=env, timeout=4 * 3600)
        except subprocess.TimeoutExpired:
            f.write("\n[autopilot] waktu produksi habis (4 jam)\n")
    hari = now().date().isoformat()
    state.setdefault("produksi", {})[hari] = state.get("produksi", {}).get(hari, 0) + 1
    cat = rj(ROOT / "produksi" / f"{pid}.json")
    slug, status = cat.get("slug"), cat.get("status")
    teks = lf.read_text(encoding="utf-8", errors="replace")[-6000:]
    if status == "selesai" and slug:
        state.pop("masalah", None)
        state.setdefault("dibuat", []).append(slug)
        skor, _ = skor_qc(slug)
        log(f"video jadi: {slug} (skor QC {skor if skor is not None else '-'})")
        return slug
    if API_LIMIT.search(teks):
        pulih = jam_pulih(teks[-3000:])
        state["jeda_sampai"] = pulih.isoformat(timespec="minutes")
        state["masalah"] = f"Kuota Claude habis, pulih ±{pulih.strftime('%H:%M')}."
        log(f"kuota Claude habis → autopilot berhenti produksi sampai {pulih.strftime('%H:%M')} (video ini dilanjutkan setelahnya)")
    elif "Login Claude kedaluwarsa" in teks:
        state["jeda_sampai"] = (now() + timedelta(hours=2)).isoformat(timespec="minutes")
        state["masalah"] = "Login Claude kedaluwarsa: buka terminal, ketik claude lalu /login (sekali saja)."
        log("login Claude kedaluwarsa → produksi berhenti; Zona perlu menjalankan `claude` lalu /login")
    elif "Internet laptop mati" in teks or "Internet laptop sedang mati" in teks:
        state["jeda_sampai"] = (now() + timedelta(minutes=15)).isoformat(timespec="minutes")
        state["masalah"] = "Internet laptop mati saat produksi; dicoba lagi otomatis."
        if state.get("produksi", {}).get(hari, 0) > 0:
            state["produksi"][hari] -= 1          # tidak dihitung kuota harian
        log("internet laptop mati → autopilot mencoba lagi 15 menit lagi (tidak dihitung kuota harian)")
        return None
    elif "Masih ada produksi lain" in teks:
        log("produksi lain sedang berjalan (tombol Studio); dicoba lagi nanti")
        return None
    log(f"produksi gagal: {cat.get('pesan') or 'cek ' + lf.name}")
    if slug and slug not in state.setdefault("dibuat", []):
        state["dibuat"].append(slug)          # kalau nanti dilanjutkan Zona & lolos, tetap bisa dijadwalkan
    return None


def butuh_produksi(state: dict, c: dict) -> int:
    slots = slot_ke_depan(state, c["n"], c["jam_sebelum"], akhir_stok(c))
    return max(0, len(slots) - len(siap_tayang(state, c)))


def putaran(paksa: bool = False) -> None:
    c = cfg()
    if not c["aktif"] and not paksa:
        log("autopilot nonaktif (bible/autopilot.json → aktif). Nyalakan di Studio atau: python agents/autopilot.py nyala")
        return
    k = Kunci(ROOT / "produksi" / ("autopilot-uji.lock" if UJI else "autopilot.lock"), maks_jam=14)
    if not k.ambil("autopilot"):
        log("putaran sebelumnya masih berjalan, dilewati")
        return
    state = rj(STATE)
    state.setdefault("slot", {})
    state.setdefault("dibuat", [])
    try:
        perbarui_jadwal(c["n"])
        tandai_tayang(state)
        isi_slot(state, c)
        gagal_beruntun = 0
        for _ in range(8):                     # satu putaran boleh membuat beberapa video berturut-turut (hari ini + besok)
            perlu = butuh_produksi(state, c)
            hari = now().date().isoformat()
            if perlu <= 0:
                break
            if not cfg()["aktif"] and not paksa:
                log("autopilot dimatikan Zona → berhenti setelah video terakhir")
                break
            if state.get("jeda_sampai") and now() < datetime.fromisoformat(state["jeda_sampai"]).replace(tzinfo=WIB):
                log(f"jeda produksi sampai {state['jeda_sampai']} ({state.get('masalah') or 'kuota Claude / gagal beruntun'})")
                break
            if state.get("produksi", {}).get(hari, 0) >= c["maks_produksi"]:
                log(f"batas {c['maks_produksi']} produksi hari ini tercapai; slot yang kosong menunggu besok")
                break
            log(f"{perlu} slot tayang belum punya video → produksi")
            wj(STATE, state)
            terhenti = macet(state)
            t0 = time.time()
            hasil = produksi(state, c, terhenti[0] if terhenti else "")
            if hasil is None and state.get("jeda_sampai") and now() < datetime.fromisoformat(state["jeda_sampai"]).replace(tzinfo=WIB):
                wj(STATE, state)
                break                                  # kuota Claude habis / internet mati / perlu login: tunggu
            if hasil is None:
                gagal_beruntun += 1
                if time.time() - t0 < 300 and state.get("produksi", {}).get(hari, 0) > 0:
                    state["produksi"][hari] -= 1          # mati dalam < 5 menit (dihentikan/ditutup): tidak dihitung kuota harian
                if time.time() - t0 < 600 or gagal_beruntun >= 2:
                    state["jeda_sampai"] = (now() + timedelta(hours=1)).isoformat(timespec="minutes")
                    log("produksi gagal (terlalu cepat atau 2x berturut-turut) → autopilot berhenti dulu 1 jam supaya tidak mengulang terus")
                    wj(STATE, state)
                    break
            else:
                gagal_beruntun = 0
            wj(STATE, state)
            isi_slot(state, c)
        if not UJI:                            # hemat ruang: cache lama & file video yang sudah diupload
            subprocess.run([PY, str(ROOT / "agents" / "bersih.py"), "semua", "--otomatis"], cwd=ROOT, capture_output=True)
        state["putaran_terakhir"] = now().isoformat(timespec="seconds")
        # stok lengkap (semua jam tayang hari ini + besok sudah punya video) → autopilot mati sendiri sampai Studio dibuka lagi
        if not slot_ke_depan(state, c["n"], 24 * c["isi_hari"], akhir_stok(c)):
            state["selesai"] = now().isoformat(timespec="minutes")
            if cfg()["aktif"]:
                setel_aktif(False, "stok selesai")
        state["slot"] = dict(sorted(state["slot"].items())[-60:])
        state["dibuat"] = state["dibuat"][-60:]
    finally:
        wj(STATE, state)
        k.lepas()
    ringkas(state, c)


def ringkas(state: dict, c: dict) -> None:
    hari_ini = now().date()
    for d in (hari_ini, hari_ini + timedelta(days=1)):
        slots = (rj(jadwal.OUT_JSON).get("slot") or {}).get(d.isoformat(), [])[:c["n"]]
        isi = []
        for s in slots:
            k = f"{d.isoformat()} {s['jam']}"
            k = (state.get("pengganti") or {}).get(k, k)
            v = state["slot"].get(k)
            isi.append(f"{k[11:]} {('→ ' + v['slug'][:40] + ' (' + v['status'] + ')') if v else '(kosong)'}")
        log(f"{d.isoformat()}: " + " · ".join(isi))
    log(f"produksi hari ini: {state.get('produksi', {}).get(hari_ini.isoformat(), 0)}/{c['maks_produksi']}")


def setel_aktif(aktif: bool, alasan: str = "") -> None:
    c = rj(CONFIG)
    c["aktif"] = aktif
    wj(CONFIG, c)
    if alasan == "stok selesai":
        log("SELESAI: semua jam tayang hari ini & besok sudah terisi → autopilot dimatikan. Buka Studio lagi untuk putaran berikutnya.")
    else:
        log("autopilot " + ("AKTIF" if aktif else "dimatikan"))


def main() -> None:
    global UJI, SEKARANG, LOG_FILE
    ap = argparse.ArgumentParser(description="Autopilot Yofamo: buat & jadwalkan video otomatis")
    ap.add_argument("perintah", choices=["jalan", "status", "nyala", "mati"])
    ap.add_argument("--uji", action="store_true", help="tanpa Claude/internet/upload sungguhan (untuk tes)")
    ap.add_argument("--paksa", action="store_true", help="jalan walau autopilot nonaktif")
    ap.add_argument("--mulai", action="store_true", help="dimulai Zona (tombol Studio): abaikan jeda sebelumnya")
    ap.add_argument("--sekarang", help="(tes) anggap sekarang jam ini, mis. 2026-11-02T08:00")
    a = ap.parse_args()
    UJI = a.uji
    if a.sekarang:
        SEKARANG = datetime.fromisoformat(a.sekarang).replace(tzinfo=WIB)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if a.perintah == "jalan" and a.mulai:
        # dimulai Zona: lupakan jeda, dan hitung ulang kuota harian dari produksi yang benar-benar berjalan
        # (produksi yang mati di awal, mis. jendelanya ditutup, tidak dihitung)
        st0 = rj(STATE)
        st0.pop("jeda_sampai", None)
        st0.pop("masalah", None)
        hari = now().strftime("%Y%m%d")
        nyata = 0
        for f in (ROOT / "produksi").glob(f"autopilot-{hari}-*.json"):
            tahap = {t.get("kunci"): t.get("status") for t in rj(f).get("tahap", [])}
            nyata += any(tahap.get(k) == "ok" for k in ("dara", "bima", "kai"))
        st0.setdefault("produksi", {})[now().date().isoformat()] = nyata
        wj(STATE, st0)
    if a.perintah == "jalan":
        LOG_FILE = ROOT / "logs" / f"autopilot-{now().strftime('%Y-%m-%d')}.txt"
        LOG_FILE.parent.mkdir(exist_ok=True)
        t0 = time.time()
        putaran(paksa=a.paksa)
        log(f"putaran selesai ({time.time() - t0:.0f} dtk)")
    elif a.perintah == "status":
        state = rj(STATE)
        state.setdefault("slot", {})
        ringkas(state, cfg())
        print(f"aktif: {cfg()['aktif']} · putaran terakhir: {state.get('putaran_terakhir', '-')}")
    else:
        setel_aktif(a.perintah == "nyala")


if __name__ == "__main__":
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    main()

#!/usr/bin/env python3
"""Autopilot Yofamo — tim bekerja sendiri: membuat video & menjadwalkan tayang (bawaan 3 video/hari).

    python agents/autopilot.py jalan            # satu putaran (dipanggil tiap jam oleh Windows Task Scheduler)
    python agents/autopilot.py status           # jadwal hari ini & besok, video yang terisi, produksi hari ini
    python agents/autopilot.py nyala | mati     # hidupkan / matikan autopilot (bible/autopilot.json → aktif)

Satu putaran:
  1. Hitung ulang jam tayang terbaik (agents/upload/jadwal.py → insights/jadwal.md) kalau sudah > 6 jam.
  2. Video yang jam tayangnya sudah lewat → status 'terbit'.
  3. Isi slot tayang 36 jam ke depan dengan video siap: status 'export' yang belum diupload (sudah disetujui Zona),
     lalu video buatan autopilot yang lolos Rara dengan skor >= skor_qc_min (disetujui otomatis kalau setujui_otomatis).
     Uli mengunggahnya PRIVATE + jadwal tayang → YouTube menayangkan sendiri tepat di jam itu.
  4. Kalau ada slot dalam mulai_produksi_jam_sebelum jam yang belum punya video → produser membuat video baru
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
API_LIMIT = re.compile(r"Kuota Claude|usage limit|limit reached|rate.?limit|credit balance", re.I)


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
            "maks_produksi": max(1, int(c.get("maks_produksi_per_hari", 5))), "jam_sebelum": float(c.get("mulai_produksi_jam_sebelum", 10)),
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
def slot_ke_depan(state: dict, n: int, jam_ke_depan: float = 36) -> list[datetime]:
    data = rj(jadwal.OUT_JSON)
    out = []
    for tgl, slots in (data.get("slot") or {}).items():
        for s in slots[:n]:
            try:
                t = datetime.fromisoformat(f"{tgl}T{s['jam']}").replace(tzinfo=WIB)
            except (ValueError, KeyError):
                continue
            if now() + timedelta(minutes=20) <= t <= now() + timedelta(hours=jam_ke_depan) and kunci_slot(t) not in state["slot"]:
                out.append(t)
    return sorted(out)


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
    slots = slot_ke_depan(state, c["n"])
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
def produksi(state: dict, c: dict) -> str | None:
    pid = f"autopilot-{datetime.now(WIB).strftime('%Y%m%d-%H%M%S')}"
    args = [PY, str(ROOT / "agents" / "produser.py"), c["arahan"], "--suara", c["suara"], "--visual", c["visual"], "--id", pid]
    if UJI:
        args.append("--uji")
    log(f"memproduksi video baru ({pid})…")
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
        state.setdefault("dibuat", []).append(slug)
        skor, _ = skor_qc(slug)
        log(f"video jadi: {slug} (skor QC {skor if skor is not None else '-'})")
        return slug
    if API_LIMIT.search(teks):
        state["jeda_sampai"] = (now() + timedelta(hours=3)).isoformat(timespec="minutes")
        log("kuota Claude habis/dibatasi → autopilot berhenti produksi 3 jam")
    elif "Masih ada produksi lain" in teks:
        state["produksi"][hari] -= 1
        log("produksi lain sedang berjalan (tombol Studio); dicoba lagi nanti")
        return None
    log(f"produksi gagal: {cat.get('pesan') or 'cek ' + lf.name}")
    if slug and slug not in state.setdefault("dibuat", []):
        state["dibuat"].append(slug)          # kalau nanti dilanjutkan Zona & lolos, tetap bisa dijadwalkan
    return None


def butuh_produksi(state: dict, c: dict) -> int:
    slots = slot_ke_depan(state, c["n"], c["jam_sebelum"])
    return max(0, len(slots) - len(siap_tayang(state, c)))


def putaran(paksa: bool = False) -> None:
    c = cfg()
    if not c["aktif"] and not paksa:
        log("autopilot nonaktif (bible/autopilot.json → aktif). Nyalakan di Studio atau: python agents/autopilot.py nyala")
        return
    k = Kunci(ROOT / "produksi" / ("autopilot-uji.lock" if UJI else "autopilot.lock"), maks_jam=6)
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
        for _ in range(3):                     # maksimal 3 video per putaran (putaran berikutnya melanjutkan)
            perlu = butuh_produksi(state, c)
            hari = now().date().isoformat()
            if perlu <= 0:
                break
            if state.get("jeda_sampai") and now() < datetime.fromisoformat(state["jeda_sampai"]).replace(tzinfo=WIB):
                log(f"jeda produksi sampai {state['jeda_sampai']} (kuota Claude)")
                break
            if state.get("produksi", {}).get(hari, 0) >= c["maks_produksi"]:
                log(f"batas {c['maks_produksi']} produksi hari ini tercapai; slot yang kosong menunggu besok")
                break
            log(f"{perlu} slot tayang belum punya video → produksi")
            wj(STATE, state)
            produksi(state, c)
            wj(STATE, state)
            isi_slot(state, c)
        if not UJI:                            # hemat ruang: cache lama & file video yang sudah diupload
            subprocess.run([PY, str(ROOT / "agents" / "bersih.py"), "semua", "--otomatis"], cwd=ROOT, capture_output=True)
        state["putaran_terakhir"] = now().isoformat(timespec="seconds")
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
            v = state["slot"].get(f"{d.isoformat()} {s['jam']}")
            isi.append(f"{s['jam']} {('→ ' + v['slug'][:40] + ' (' + v['status'] + ')') if v else '(kosong)'}")
        log(f"{d.isoformat()}: " + " · ".join(isi))
    log(f"produksi hari ini: {state.get('produksi', {}).get(hari_ini.isoformat(), 0)}/{c['maks_produksi']}")


def setel_aktif(aktif: bool) -> None:
    c = rj(CONFIG)
    c["aktif"] = aktif
    wj(CONFIG, c)
    log("autopilot " + ("AKTIF — Task Scheduler menjalankannya tiap jam (pasang sekali: pasang_autopilot.bat)" if aktif else "dimatikan"))


def main() -> None:
    global UJI, SEKARANG, LOG_FILE
    ap = argparse.ArgumentParser(description="Autopilot Yofamo: buat & jadwalkan video otomatis")
    ap.add_argument("perintah", choices=["jalan", "status", "nyala", "mati"])
    ap.add_argument("--uji", action="store_true", help="tanpa Claude/internet/upload sungguhan (untuk tes)")
    ap.add_argument("--paksa", action="store_true", help="jalan walau autopilot nonaktif")
    ap.add_argument("--sekarang", help="(tes) anggap sekarang jam ini, mis. 2026-11-02T08:00")
    a = ap.parse_args()
    UJI = a.uji
    if a.sekarang:
        SEKARANG = datetime.fromisoformat(a.sekarang).replace(tzinfo=WIB)
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
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

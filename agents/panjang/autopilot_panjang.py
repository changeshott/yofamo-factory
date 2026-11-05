#!/usr/bin/env python3
"""Autopilot video panjang — tim Ruang Animasi membuat & menjadwalkan sendiri 1 video panjang per hari (bawaan).

    python agents/panjang/autopilot_panjang.py jalan          # satu putaran (dipanggil Studio saat dibuka & tiap ±1 jam, dan oleh autopilot.py)
    python agents/panjang/autopilot_panjang.py status         # slot tayang hari ini & besok + isinya
    python agents/panjang/autopilot_panjang.py nyala | mati   # bible/autopilot.json → panjang.aktif

Satu putaran:
  1. Video panjang yang jam tayangnya sudah lewat → status 'terbit'.
  2. Isi slot tayang (1 per hari, hari ini + besok) dengan video siap: status 'export' yang belum diupload (disetujui Zona) dulu,
     lalu video buatan autopilot yang lolos QC Wulan (skor ≥ panjang.skor_qc_min) → disetujui otomatis (kalau panjang.setujui_otomatis)
     → Uli mengunggah PRIVATE + jadwal tayang (publishAt) → YouTube menayangkan sendiri walau laptop mati.
  3. Slot yang belum punya video → produser_panjang membuat video baru (Bayu pilih topik baru → … → Wulan), maks
     panjang.maks_produksi_per_hari. Video terhenti (kuota Claude / laptop mati) dilanjutkan dulu sebelum membuat yang baru.
Jam tayang: panjang.jam ("19:30") atau otomatis = jam terbaik dari insights/jadwal.json di rentang 15–21, menit :30,
berjarak ≥ 90 menit dari jam tayang Shorts hari itu. Video di bawah skor tetap 'draft' menunggu Zona.
Satu putaran pada satu waktu (produksi/autopilot-panjang.lock); produksi memakai produksi/panjang.lock seperti tombol Studio,
prioritas CPU rendah, dan tiap adegan menunggu kalau produksi Shorts sedang berjalan.
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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
from kunci import Kunci  # noqa: E402

PY = sys.executable
CONFIG = ROOT / "bible" / "autopilot.json"
STATE = ROOT / "produksi" / "autopilot-panjang.json"
JADWAL = ROOT / "insights" / "jadwal.json"
PROD = ROOT / "produksi" / "panjang"
WIB = timezone(timedelta(hours=7))
UJI = False
SEKARANG: datetime | None = None
LOG_FILE: Path | None = None
API_LIMIT = re.compile(r"Kuota Claude|usage limit|limit reached|rate.?limit|credit balance|hit your [\w -]*limit|\d+-hour limit", re.I)
RESET = re.compile(r"(?:resets?|pulih) (?:at )?(\d{1,2})(?::(\d\d))?\s*(am|pm)?", re.I)
BAWAAN = {"aktif": True, "video_per_hari": 1, "isi_hari": 2, "setujui_otomatis": True, "skor_qc_min": 7,
          "maks_produksi_per_hari": 2, "jam": "", "arahan_tema": ""}


def now() -> datetime:
    return SEKARANG or datetime.now(WIB)


def log(msg: str) -> None:
    line = f"[autopilot-panjang {now().strftime('%H:%M')}] {msg}"
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
    c = {**BAWAAN, **(rj(CONFIG).get("panjang") or {})}
    jam = str(c.get("jam") or "")
    return {"aktif": bool(c["aktif"]), "n": max(1, min(2, int(c["video_per_hari"]))), "isi_hari": max(1, min(3, int(c["isi_hari"]))),
            "setujui": bool(c["setujui_otomatis"]), "skor_min": float(c["skor_qc_min"]), "maks_produksi": max(1, int(c["maks_produksi_per_hari"])),
            "jam": jam if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", jam) else "",
            "arahan": re.sub(r"[^\w\s,.\-?!]", "", str(c.get("arahan_tema", "")), flags=re.UNICODE)[:200]}


def setel_aktif(aktif: bool) -> None:
    c = rj(CONFIG)
    c["panjang"] = {**BAWAAN, **(c.get("panjang") or {}), "aktif": aktif}
    wj(CONFIG, c)
    log("autopilot video panjang " + ("AKTIF" if aktif else "dimatikan"))


# ------------------------------------------------------------------ slot
def jam_slot(tgl: str, c: dict, ke: int = 0) -> datetime:
    """Jam tayang video panjang ke-`ke` pada tanggal itu: jam tetap dari pengaturan, atau jam terbaik (15–21, :30)
    yang berjarak ≥ 90 menit dari jam tayang Shorts hari itu."""
    if c["jam"] and ke == 0:
        return datetime.fromisoformat(f"{tgl}T{c['jam']}").replace(tzinfo=WIB)
    jd = rj(JADWAL)
    n_shorts = int((rj(CONFIG).get("video_per_hari")) or 3)
    shorts = []
    for s in ((jd.get("slot") or {}).get(tgl) or [])[:n_shorts]:
        try:
            h, m = map(int, str(s["jam"]).split(":"))
            shorts.append(h * 60 + m)
        except (KeyError, ValueError):
            continue
    skor = {}
    for j in jd.get("jam") or []:
        try:
            skor[int(j["jam"])] = float(j.get("skor", 0))
        except (KeyError, TypeError, ValueError):
            continue
    calon = sorted(range(15, 22), key=lambda h: (-skor.get(h, 0), abs(h - 19)))
    bebas = [h for h in calon if all(abs(h * 60 + 30 - x) >= 90 for x in shorts)] or calon
    h = bebas[min(ke, len(bebas) - 1)]
    return datetime.fromisoformat(f"{tgl}T{h:02d}:30").replace(tzinfo=WIB)


def kunci_slot(t: datetime) -> str:
    return t.strftime("%Y-%m-%d %H:%M")


def semua_slot(c: dict) -> list[datetime]:
    out = []
    for d in range(c["isi_hari"]):
        tgl = (now().date() + timedelta(days=d)).isoformat()
        out += [jam_slot(tgl, c, k) for k in range(c["n"])]
    return sorted(set(out))


def slot_terbuka(state: dict, c: dict) -> list[datetime]:
    """Slot dalam stok yang belum terisi dan masih sempat diunggah (≥ 45 menit lagi)."""
    return [t for t in semua_slot(c) if kunci_slot(t) not in state["slot"] and t >= now() + timedelta(minutes=45)]


# ------------------------------------------------------------------ video siap
def skor_qc(slug: str) -> tuple[float | None, bool]:
    q = rj(st_panjang.folder(slug) / "export" / "qc.json")
    try:
        skor = float(q["skor"]) if q.get("skor") is not None else None
    except (TypeError, ValueError):
        skor = None
    return skor, q.get("lolos") is True


def siap_tayang(state: dict, c: dict) -> list[tuple[str, str]]:
    terisi = {v.get("slug") for v in state["slot"].values()}
    out = []
    vids = {v["slug"]: v["status"] for v in st_panjang.semua()}

    def bisa(slug: str) -> bool:
        exp = st_panjang.folder(slug) / "export"
        info = rj(exp / "info.json")
        return (slug not in terisi and (exp / "final.mp4").exists() and not rj(exp / "upload.json").get("videoId")
                and (not info.get("uji") or UJI))

    for slug, st in sorted(vids.items(), key=lambda kv: kv[0]):
        if st == "export" and bisa(slug):
            out.append((slug, "disetujui Zona"))
    for slug in state.get("dibuat", []):
        if (vids.get(slug) != "draft" and not UJI) or vids.get(slug) in ("export", "terbit", "ditolak") or not bisa(slug) or not c["setujui"]:
            continue
        skor, lolos = skor_qc(slug)
        if skor is not None and skor >= c["skor_min"] and lolos:
            out.append((slug, f"lolos QC Wulan (skor {skor:g})"))
        elif not state.setdefault("menunggu_zona", {}).get(slug):
            state["menunggu_zona"][slug] = f"skor QC {skor if skor is not None else '-'} (batas {c['skor_min']:g}) atau ada masalah; tunggu Zona"
            log(f"{slug}: QC belum lolos (skor {skor}), menunggu Zona menonton & menyetujui di Ruang Animasi")
    return out


def unggah(slug: str, t: datetime) -> dict | None:
    jadwal = t.strftime("%Y-%m-%dT%H:%M")
    if UJI:
        log(f"[uji] {slug} → tayang {jadwal} WIB (tidak benar-benar diupload)")
        return {"videoId": "UJI", "url": "", "jadwal": jadwal}
    lf = ROOT / "logs" / f"upload-panjang-{now().strftime('%Y%m%d-%H%M%S')}.txt"
    with lf.open("w", encoding="utf-8") as f:
        try:
            subprocess.run([PY, str(ROOT / "agents" / "panjang" / "unggah_panjang.py"), "unggah", slug, "--jadwal", jadwal], cwd=ROOT,
                           stdout=f, stderr=subprocess.STDOUT, timeout=4 * 3600, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        except subprocess.TimeoutExpired:
            f.write("\n[autopilot-panjang] upload terlalu lama (4 jam)\n")
    for line in lf.read_text(encoding="utf-8", errors="replace").strip().splitlines()[-3:]:
        log(f"  {line}")
    up = rj(st_panjang.folder(slug) / "export" / "upload.json")
    return up if up.get("videoId") else None


def isi_slot(state: dict, c: dict) -> int:
    siap, n = siap_tayang(state, c), 0
    for t in slot_terbuka(state, c):
        if not siap:
            break
        slug, alasan = siap.pop(0)
        if st_panjang.status(slug) not in ("export", "terbit"):
            st_panjang.set_status(slug, "export", f"disetujui otomatis oleh autopilot video panjang ({alasan})")
        up = unggah(slug, t)
        if not up:
            log(f"{slug}: upload gagal, dicoba lagi di putaran berikutnya")
            break
        state["slot"][kunci_slot(t)] = {"slug": slug, "videoId": up.get("videoId"), "url": up.get("url"), "status": "terjadwal", "alasan": alasan}
        state.get("menunggu_zona", {}).pop(slug, None)
        n += 1
        log(f"{slug} dijadwalkan tayang {kunci_slot(t)} WIB ({alasan})")
    return n


def tandai_tayang(state: dict) -> None:
    for k, v in state["slot"].items():
        if v.get("status") == "terjadwal" and datetime.strptime(k, "%Y-%m-%d %H:%M").replace(tzinfo=WIB) + timedelta(minutes=10) <= now():
            if not UJI and st_panjang.status(v["slug"]) == "export":
                st_panjang.set_status(v["slug"], "terbit", f"tayang terjadwal {k} WIB (autopilot)")
            v["status"] = "tayang"
            log(f"{v['slug']} sudah tayang ({k} WIB)")


# ------------------------------------------------------------------ produksi
def jam_pulih(teks: str) -> datetime:
    m = RESET.search(teks)
    if not m:
        return now() + timedelta(hours=3)
    h, mnt, ap = int(m.group(1)), int(m.group(2) or 0), (m.group(3) or "").lower()
    h = h % 12 + (12 if ap == "pm" else 0) if ap else h
    t = now().replace(hour=h % 24, minute=mnt, second=0, microsecond=0)
    return (t + timedelta(days=1) if t <= now() else t) + timedelta(minutes=5)


def macet(state: dict) -> str:
    """Video autopilot (3 hari terakhir) yang terhenti di tengah jalan → dilanjutkan dulu (lebih hemat dari mulai baru).
    Catatan 'berjalan' tanpa proses hidup (laptop tidur/mati, jendela ditutup) juga dianggap terhenti."""
    batas = time.time() - 3 * 86400
    ada_proses = Kunci(ROOT / "produksi" / ("panjang-uji.lock" if UJI else "panjang.lock"), maks_jam=12).sibuk()
    for f in sorted(PROD.glob("autopilot-panjang-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        rec = rj(f)
        slug = rec.get("slug")
        if (f.stat().st_mtime < batas or not slug or rec.get("status") == "selesai" or (rec.get("status") == "berjalan" and ada_proses)
                or (st_panjang.folder(slug) / "export" / "final.mp4").exists() or (rec.get("opsi") or {}).get("uji") and not UJI):
            continue
        st = st_panjang.status(slug)
        if st and st not in ("draft", "export", "terbit", "ditolak") and state.setdefault("dilanjutkan", {}).get(slug, 0) < 2:
            return slug
    return ""


def produksi(state: dict, c: dict, lanjut: str = "") -> str | None:
    pid = f"autopilot-panjang-{now().strftime('%Y%m%d-%H%M%S')}"
    args = [PY, str(ROOT / "agents" / "panjang" / "produser_panjang.py"), *(["--lanjut", lanjut] if lanjut else [c["arahan"]]), "--id", pid]
    if lanjut:
        state.setdefault("dilanjutkan", {})[lanjut] = state["dilanjutkan"].get(lanjut, 0) + 1
    if UJI:
        args.append("--uji")
    log(f"melanjutkan video panjang yang terhenti: {lanjut} ({pid})…" if lanjut else f"memproduksi video panjang baru ({pid})…")
    hari = now().date().isoformat()
    if not lanjut:                      # melanjutkan video yang terhenti tidak dihitung kuota produksi harian
        state.setdefault("produksi", {})[hari] = state.get("produksi", {}).get(hari, 0) + 1
    wj(STATE, state)
    lf = ROOT / "logs" / f"{pid}.txt"
    lf.parent.mkdir(exist_ok=True)
    t0 = time.time()
    with lf.open("w", encoding="utf-8") as f:
        f.write(f"# Produksi autopilot video panjang — {now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.flush()
        try:
            subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=16 * 3600,
                           env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
        except subprocess.TimeoutExpired:
            f.write("\n[autopilot-panjang] waktu produksi habis (16 jam)\n")
    cat = rj(PROD / f"{pid}.json")
    slug, status = cat.get("slug"), cat.get("status")
    teks = lf.read_text(encoding="utf-8", errors="replace")[-6000:]
    if slug and slug not in state.setdefault("dibuat", []):
        state["dibuat"].append(slug)
    if status == "selesai" and slug:
        state.pop("masalah", None)
        skor, lolos = skor_qc(slug)
        log(f"video panjang jadi: {slug} (skor QC {skor if skor is not None else '-'}{', lolos' if lolos else ', ada masalah'})")
        return slug
    if "Masih ada video panjang lain" in teks:
        if not lanjut:
            state["produksi"][hari] -= 1
        log("video panjang lain sedang dibuat (tombol Studio); dicoba lagi nanti")
        return None
    if API_LIMIT.search(teks):
        pulih = jam_pulih(teks[-3000:])
        state["jeda_sampai"] = pulih.isoformat(timespec="minutes")
        state["masalah"] = f"Kuota Claude habis, pulih ±{pulih.strftime('%H:%M')}."
        log(f"kuota Claude habis → produksi video panjang berhenti sampai {pulih.strftime('%H:%M')} (dilanjutkan setelahnya)")
    elif "Login Claude kedaluwarsa" in teks:
        state["jeda_sampai"] = (now() + timedelta(hours=2)).isoformat(timespec="minutes")
        state["masalah"] = "Login Claude kedaluwarsa: buka terminal, ketik claude lalu /login (sekali saja)."
    elif "Internet laptop" in teks:
        state["jeda_sampai"] = (now() + timedelta(minutes=30)).isoformat(timespec="minutes")
        state["masalah"] = "Internet laptop mati saat produksi video panjang; dicoba lagi otomatis."
        if not lanjut:
            state["produksi"][hari] -= 1
    else:
        state["jeda_sampai"] = (now() + timedelta(hours=1 if time.time() - t0 < 900 else 0.25)).isoformat(timespec="minutes")
        state["masalah"] = f"Produksi video panjang gagal: {cat.get('pesan') or 'cek ' + lf.name}"[:200]
    log(f"produksi video panjang berhenti: {cat.get('pesan') or 'cek ' + lf.name}")
    return None


def putaran(paksa: bool = False) -> None:
    c = cfg()
    if not c["aktif"] and not paksa:
        log("autopilot video panjang nonaktif (bible/autopilot.json → panjang.aktif)")
        return
    k = Kunci(ROOT / "produksi" / ("autopilot-panjang-uji.lock" if UJI else "autopilot-panjang.lock"), maks_jam=20)
    if not k.ambil("autopilot-panjang"):
        log("putaran sebelumnya masih berjalan, dilewati")
        return
    state = rj(STATE)
    state.setdefault("slot", {})
    state.setdefault("dibuat", [])
    try:
        tandai_tayang(state)
        isi_slot(state, c)
        for _ in range(3):
            hari = now().date().isoformat()
            perlu = len(slot_terbuka(state, c)) - len(siap_tayang(state, c))
            if perlu <= 0:
                break
            if not cfg()["aktif"] and not paksa:
                break
            if state.get("jeda_sampai") and now() < datetime.fromisoformat(state["jeda_sampai"]).replace(tzinfo=WIB):
                log(f"jeda produksi sampai {state['jeda_sampai'][11:16]} ({state.get('masalah') or '-'})")
                break
            lanjut = macet(state)
            if not lanjut and state.get("produksi", {}).get(hari, 0) >= c["maks_produksi"]:
                log(f"batas {c['maks_produksi']} produksi video panjang baru hari ini tercapai")
                break
            log(f"{perlu} slot tayang video panjang belum punya video → produksi")
            hasil = produksi(state, c, lanjut)
            wj(STATE, state)
            isi_slot(state, c)
            if hasil is None:
                break
        state["putaran_terakhir"] = now().isoformat(timespec="seconds")
        state["jadwal"] = [kunci_slot(t) for t in semua_slot(c)]          # untuk sidebar jadwal Studio (slot kosong ikut tampil)
        state["slot"] = dict(sorted(state["slot"].items())[-40:])
        state["dibuat"] = state["dibuat"][-40:]
    finally:
        wj(STATE, state)
        k.lepas()
    ringkas(state, c)


def ringkas(state: dict, c: dict) -> None:
    for t in semua_slot(c):
        v = state["slot"].get(kunci_slot(t))
        log(f"{kunci_slot(t)}: {('→ ' + v['slug'][:50] + ' (' + v['status'] + ')') if v else '(kosong)'}")
    log(f"produksi hari ini: {state.get('produksi', {}).get(now().date().isoformat(), 0)}/{c['maks_produksi']}")


def main() -> None:
    global UJI, SEKARANG, LOG_FILE
    ap = argparse.ArgumentParser(description="Autopilot video panjang: buat & jadwalkan 1 video panjang per hari")
    ap.add_argument("perintah", choices=["jalan", "status", "nyala", "mati"])
    ap.add_argument("--uji", action="store_true", help="tanpa Claude/internet/upload sungguhan (untuk tes)")
    ap.add_argument("--paksa", action="store_true", help="jalan walau nonaktif")
    ap.add_argument("--mulai", action="store_true", help="dimulai Zona: abaikan jeda sebelumnya")
    ap.add_argument("--sekarang", help="(tes) anggap sekarang jam ini, mis. 2026-11-05T08:00")
    a = ap.parse_args()
    UJI = a.uji
    if a.sekarang:
        SEKARANG = datetime.fromisoformat(a.sekarang).replace(tzinfo=WIB)
    global STATE
    if UJI:
        STATE = ROOT / "produksi" / "autopilot-panjang-uji.json"
    if a.perintah == "jalan":
        if a.mulai:
            st0 = rj(STATE)
            st0.pop("jeda_sampai", None)
            st0.pop("masalah", None)
            wj(STATE, st0)
        LOG_FILE = ROOT / "logs" / f"autopilot-panjang-{now().strftime('%Y-%m-%d')}.txt"
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


def mulai_latar(alasan: str = "") -> bool:
    """Dipanggil autopilot Shorts: jalankan satu putaran autopilot video panjang di LATAR (proses terpisah) kalau aktif
    dan belum berjalan. Tidak menunggu — produksi video panjang bisa berjam-jam."""
    if not cfg()["aktif"] or Kunci(ROOT / "produksi" / "autopilot-panjang.lock", maks_jam=20).sibuk():
        return False
    lf = ROOT / "logs" / f"autopilot-panjang-latar-{datetime.now(WIB).strftime('%Y-%m-%d')}.txt"
    lf.parent.mkdir(exist_ok=True)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if os.name == "nt":   # sama seperti Studio: latar.vbs → console tersembunyi, keluaran ke log
        subprocess.Popen(["wscript.exe", str(ROOT / "latar.vbs"), str(lf), PY, "agents/panjang/autopilot_panjang.py", "jalan"], cwd=ROOT, env=env)
    else:
        with lf.open("a", encoding="utf-8") as f:
            subprocess.Popen([PY, "agents/panjang/autopilot_panjang.py", "jalan"], cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                             stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    log(f"autopilot video panjang dimulai di latar{' (' + alasan + ')' if alasan else ''}")
    return True


if __name__ == "__main__":
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    main()

#!/usr/bin/env python3
"""Jadwal tayang Yofamo — mencari jam upload yang paling cocok untuk Shorts, tanpa kuota API & tanpa Claude.

    python agents/upload/jadwal.py              # hitung ulang → insights/jadwal.json + insights/jadwal.md
    python agents/upload/jadwal.py --lihat      # tampilkan slot 3 hari ke depan

Cara kerja (skor tiap jam 07–22 WIB):
  1. Dasar: pola umum jam aktif penonton Shorts Indonesia (makan siang, pulang sekolah/kerja, malam). Ini DUGAAN awal,
     bukan data channel, dan bobotnya mengecil sendiri begitu data channel bertambah.
  2. Data channel sendiri: performa tiap Short menurut jam tayangnya (WIB). Supaya adil, video baru dibandingkan
     memakai views saat umurnya ±2 hari (dari snapshot harian Steve), video lama memakai total views. Efeknya disusutkan
     ke nol kalau videonya sedikit (perlu ±4 video di jam itu untuk berpengaruh penuh) → < 5 video tetap "dugaan".
  3. Data pasar (Shorts teknologi Indonesia lain, dari radar pasar Steve): jam tayang video yang views/harinya tinggi.
  4. Pilih slot: skor tertinggi dengan jarak minimal antar-slot (bawaan 3 jam). Tiap 2 hari, satu slot dipakai untuk
     EKSPLORASI jam yang belum pernah dicoba channel ini, supaya algoritmanya terus belajar dari data sendiri.
Pengaturan di bible/autopilot.json → jadwal.
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import statistics as st
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insights" / "raw"
OUT_JSON = ROOT / "insights" / "jadwal.json"
OUT_MD = ROOT / "insights" / "jadwal.md"
CONFIG = ROOT / "bible" / "autopilot.json"
WIB = timezone(timedelta(hours=7))

# Pola umum jam aktif penonton Shorts di Indonesia (WIB), skala 0–1. Dugaan awal: makan siang 11–13,
# sore pulang sekolah/kerja 16–18, puncak malam 19–21. Data channel & pasar menggeser angka ini.
DASAR = {6: .30, 7: .42, 8: .48, 9: .52, 10: .58, 11: .78, 12: .88, 13: .80, 14: .62, 15: .66, 16: .80, 17: .92,
         18: .97, 19: 1.0, 20: .96, 21: .82, 22: .55, 23: .32}
K_CHANNEL, K_PASAR, BOBOT_PASAR = 4.0, 12.0, 0.5


def rj(p: Path, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def cfg() -> dict:
    c = (rj(CONFIG, {}) or {}).get("jadwal", {})
    return {"jam_awal": int(c.get("jam_awal", 7)), "jam_akhir": int(c.get("jam_akhir", 22)),
            "jarak_jam": float(c.get("jarak_jam", 3)), "eksplorasi": bool(c.get("eksplorasi", True)),
            "slot_tetap": [str(x) for x in c.get("slot_tetap") or []]}


def jam_wib(iso: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).astimezone(WIB)
    except ValueError:
        return None


def data_channel() -> list[dict]:
    """Tiap Short channel: jam tayang (WIB) + skor log(performa / median kelompoknya)."""
    snaps = []
    for f in sorted(glob.glob(str(RAW / "20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"))):
        d = rj(Path(f), {}) or {}
        if d.get("videos"):
            snaps.append(d)
    if not snaps:
        return []
    akhir = {v["id"]: v for v in snaps[-1]["videos"] if v.get("is_short")}
    awal: dict[str, float] = {}                 # views saat umur ±2 hari (1,2–3,5 hari), paling dekat ke 2
    for s in snaps:
        for v in s["videos"]:
            if v.get("id") in akhir and 1.2 <= float(v.get("age_days") or 0) <= 3.5:
                lama = awal.get(v["id"] + "_umur")
                if lama is None or abs(float(v["age_days"]) - 2) < abs(lama - 2):
                    awal[v["id"]] = float(v.get("views") or 0)
                    awal[v["id"] + "_umur"] = float(v["age_days"])
    baris = []
    for vid, v in akhir.items():
        t = jam_wib(v.get("published_at") or "")
        if not t:
            continue
        if vid in awal:
            baris.append({"id": vid, "jam": t.hour, "hari": t.weekday(), "kelompok": "awal", "nilai": awal[vid]})
        elif float(v.get("age_days") or 0) >= 14:
            baris.append({"id": vid, "jam": t.hour, "hari": t.weekday(), "kelompok": "total", "nilai": float(v.get("views") or 0)})
    for g in ("awal", "total"):
        xs = [b["nilai"] for b in baris if b["kelompok"] == g and b["nilai"] > 0]
        med = st.median(xs) if xs else 0
        for b in baris:
            if b["kelompok"] == g:
                b["skor"] = math.log(max(b["nilai"], 1) / med) if med else 0.0
    return baris


def data_pasar() -> list[dict]:
    """Shorts teknologi Indonesia lain (radar pasar Steve) yang punya jam tayang: skor log(views per hari / median)."""
    f = sorted(glob.glob(str(RAW / "pasar-*.json")))
    vids = []
    for p in f[-3:]:
        for v in (rj(Path(p), {}) or {}).get("video", []):
            t = jam_wib(v.get("terbit_at") or "")
            if t and float(v.get("views_per_hari") or 0) > 0:
                vids.append({"id": v.get("id"), "jam": t.hour, "nilai": float(v["views_per_hari"])})
    uniq = {v["id"]: v for v in vids}
    vids = list(uniq.values())
    med = st.median([v["nilai"] for v in vids]) if vids else 0
    for v in vids:
        v["skor"] = math.log(v["nilai"] / med) if med else 0.0
    return vids


def efek(baris: list[dict], jam: int, k: float) -> tuple[float, float]:
    """Rata-rata skor video yang tayang di jam itu (±1 jam setengah bobot), disusutkan ke 0 dengan k video semu."""
    w = s = 0.0
    for b in baris:
        d = min(abs(b["jam"] - jam), 24 - abs(b["jam"] - jam))
        bobot = 1.0 if d == 0 else 0.5 if d == 1 else 0.0
        w += bobot
        s += bobot * b.get("skor", 0.0)
    return (s / (w + k) if w else 0.0), w


def hitung() -> dict:
    c = cfg()
    ch, ps = data_channel(), data_pasar()
    jam = []
    for h in range(c["jam_awal"], c["jam_akhir"] + 1):
        e_ch, n_ch = efek(ch, h, K_CHANNEL)
        e_ps, n_ps = efek(ps, h, K_PASAR)
        skor = math.log(DASAR.get(h, .2)) + e_ch + BOBOT_PASAR * e_ps
        jam.append({"jam": h, "skor": round(skor, 3), "dasar": DASAR.get(h, .2), "efek_channel": round(e_ch, 3), "n_channel": n_ch,
                    "video_di_jam_ini": sum(1 for b in ch if b["jam"] == h),
                    "efek_pasar": round(e_ps, 3), "n_pasar": n_ps})
    catatan = []
    n_vid = len(ch)
    if n_vid < 5:
        catatan.append(f"Data channel baru {n_vid} video dengan jam tayang: jadwal masih DUGAAN dari pola umum penonton Indonesia.")
    jam_dicoba = sorted({b["jam"] for b in ch})
    if jam_dicoba:
        catatan.append("Channel ini sejauh ini tayang di jam: " + ", ".join(f"{h:02d}" for h in jam_dicoba) + " WIB.")
    if not ps:
        catatan.append("Radar pasar belum mencatat jam tayang (tersedia mulai radar pasar Steve berikutnya).")
    hari = {}
    for b in ch:
        hari.setdefault(b["hari"], []).append(b.get("skor", 0.0))
    return {"dibuat": datetime.now(WIB).isoformat(timespec="seconds"), "pengaturan": c, "jam": jam,
            "dasar": {"video_channel": n_vid, "video_pasar": len(ps)},
            "hari": {["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"][k]: {"n": len(v), "median": round(st.median(v), 2)} for k, v in sorted(hari.items())},
            "catatan": catatan}


def slot_hari(data: dict, tgl: date, n: int) -> list[dict]:
    """n jam tayang untuk tanggal tgl: skor tertinggi dengan jarak minimal; tiap 2 hari 1 slot eksplorasi."""
    c = data["pengaturan"]
    if c["slot_tetap"]:
        return [{"jam": s, "eksplorasi": False, "alasan": "slot tetap dari bible/autopilot.json"} for s in c["slot_tetap"][:n]]
    urut = sorted(data["jam"], key=lambda x: -x["skor"])
    pilih: list[dict] = []
    for j in urut:
        if len(pilih) >= n:
            break
        if all(abs(j["jam"] - p["jam"]) >= c["jarak_jam"] for p in pilih):
            pilih.append(j)
    # eksplorasi: kalau semua slot sudah punya data, tiap 2 hari satu slot (bukan yang terbaik) dipindah ke jam ramai
    # yang paling sedikit dicoba → data channel sendiri terus bertambah di jam-jam baru
    if c["eksplorasi"] and n >= 2 and tgl.toordinal() % 2 == 0 and all(p["video_di_jam_ini"] >= 2 for p in pilih):
        kandidat = sorted((j for j in urut if j not in pilih and j["dasar"] >= .55 and j["video_di_jam_ini"] < 2),
                          key=lambda j: (j["video_di_jam_ini"], -j["skor"]))
        for j in kandidat:
            sisa = pilih[:-1]
            if all(abs(j["jam"] - p["jam"]) >= c["jarak_jam"] for p in sisa):
                pilih = sisa + [j]
                break
    out = []
    for j in sorted(pilih, key=lambda x: x["jam"]):
        baru = j["video_di_jam_ini"] < 2
        alasan = (f"skor {j['skor']:+.2f}: pola umum {j['dasar']:.2f}"
                  + (f", data channel {j['efek_channel']:+.2f} ({j['video_di_jam_ini']} video di jam ini)" if j["n_channel"] else ", belum ada data channel")
                  + (f", pasar {j['efek_pasar']:+.2f}" if j["n_pasar"] else "") + ("; sekaligus eksplorasi jam baru" if baru else ""))
        out.append({"jam": f"{j['jam']:02d}:00", "eksplorasi": baru, "alasan": alasan})
    return out


def tulis(data: dict, n: int, hari_ke_depan: int = 7, mulai: date | None = None) -> dict:
    hari_ini = mulai or datetime.now(WIB).date()
    data["slot"] = {(hari_ini + timedelta(days=d)).isoformat(): slot_hari(data, hari_ini + timedelta(days=d), n) for d in range(hari_ke_depan)}
    data["video_per_hari"] = n
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    L = ["# Jadwal tayang Yofamo", "", f"Dibuat {data['dibuat'][:16].replace('T', ' ')} WIB · {n} video/hari · "
         f"data: {data['dasar']['video_channel']} Short channel, {data['dasar']['video_pasar']} Short pasar", ""]
    L += [f"- {x}" for x in data["catatan"]] + ["", "## Slot", ""]
    for tgl, slots in data["slot"].items():
        L.append(f"- **{tgl}**: " + ", ".join(s["jam"] + (" (eksplorasi)" if s["eksplorasi"] else "") for s in slots))
    L += ["", "## Skor per jam (WIB)", "", "| Jam | Skor | Pola umum | Efek channel (video di jam ini) | Efek pasar (bobot) |", "| --- | --- | --- | --- | --- |"]
    for j in data["jam"]:
        L.append(f"| {j['jam']:02d}:00 | {j['skor']:+.2f} | {j['dasar']:.2f} | {j['efek_channel']:+.2f} ({j['video_di_jam_ini']}) | {j['efek_pasar']:+.2f} ({j['n_pasar']:.1f}) |")
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    return data


def video_per_hari() -> int:
    return max(1, min(6, int((rj(CONFIG, {}) or {}).get("video_per_hari", 3))))


def main() -> None:
    ap = argparse.ArgumentParser(description="Jadwal tayang Yofamo")
    ap.add_argument("--lihat", action="store_true")
    a = ap.parse_args()
    data = tulis(hitung(), video_per_hari())
    for c_ in data["catatan"]:
        print(f"[jadwal] {c_}")
    for tgl, slots in list(data["slot"].items())[: 3 if a.lihat else 2]:
        print(f"[jadwal] {tgl}: " + ", ".join(s["jam"] + (" (eksplorasi)" if s["eksplorasi"] else "") for s in slots))
    print(f"[jadwal] → {OUT_JSON.relative_to(ROOT)}, {OUT_MD.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

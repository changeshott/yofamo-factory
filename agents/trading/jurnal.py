"""Yudi — jurnal & evaluasi. Mencatat setiap posisi (latihan = uang pura-pura, nyata = yang Zona beli sendiri di FOMO),
memantau harga, menutup posisi latihan otomatis di stop/target/batas waktu, dan memberi PERINGATAN untuk posisi nyata
(agent tidak pernah menjual — Zona yang menjual di FOMO lalu menekan "Saya sudah jual").
Statistik jujur: semua hasil sudah dipotong biaya & slippage.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import data

WIB = timezone(timedelta(hours=7))
F = data.TRADING / "jurnal.json"


def sekarang() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%dT%H:%M:%S")


def baca() -> dict:
    try:
        return json.loads(F.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"posisi": [], "peringatan": []}


def simpan(j: dict) -> None:
    F.parent.mkdir(parents=True, exist_ok=True)
    tmp = F.with_suffix(".tmp")
    tmp.write_text(json.dumps(j, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(F)


def hari_ini(j: dict, mode: str) -> dict:
    """Rugi terealisasi + risiko posisi terbuka & jumlah trade hari ini (WIB) untuk satu mode."""
    tgl = datetime.now(WIB).strftime("%Y-%m-%d")
    rugi = trade = bersih = 0.0
    for p in j["posisi"]:
        if p["mode"] != mode:
            continue
        if (p.get("ditutup") or "").startswith(tgl):
            bersih += p.get("pnl_usd", 0)
        if not p["dibuka"].startswith(tgl):
            continue
        trade += 1
        if p["status"] == "terbuka":
            rugi += p.get("rugi_di_stop_usd", 0)
        elif p.get("pnl_usd", 0) < 0:
            rugi += -p["pnl_usd"]
    return {"rugi_usd": round(rugi, 2), "trade": int(trade), "pnl_usd": round(bersih, 2)}


def token_terbuka(j: dict, mode: str) -> list[str]:
    return [p["token"] for p in j["posisi"] if p["status"] == "terbuka" and p["mode"] == mode]


def buka(sinyal: dict, mode: str, harga: float | None = None, usd: float | None = None) -> dict:
    j = baca()
    s, r = sinyal["setup"], sinyal["risiko"]
    masuk = float(harga or s["masuk"])
    geser = masuk - s["masuk"]                        # harga beli nyata beda → stop & target ikut bergeser sama jauh
    p = {"id": f"{sinyal['id']}-{mode[0]}", "sinyal": sinyal["id"], "pasar": sinyal["pasar"], "simbol": sinyal["simbol"], "token": sinyal["token"],
         "pool": sinyal.get("pool"), "coin": sinyal.get("coin"), "arah": s["arah"], "mode": mode, "dibuka": sekarang(), "t_buka": int(time.time()),
         "masuk": masuk, "stop": s["stop"] + geser, "target": s["target"] + geser, "posisi_usd": float(usd or r["posisi_usd"]),
         "biaya_pp_pct": r["biaya_pp_pct"], "rugi_di_stop_usd": r["rugi_di_stop_usd"], "tahan_maks_jam": sinyal["tahan_maks_jam"],
         "status": "terbuka", "harga_kini": masuk, "pnl_kini_usd": 0.0}
    if any(x["id"] == p["id"] for x in j["posisi"]):
        return next(x for x in j["posisi"] if x["id"] == p["id"])
    j["posisi"].append(p)
    simpan(j)
    return p


def _pnl(p: dict, keluar: float) -> tuple[float, float]:
    beli = p["arah"] == "beli"
    gerak = ((keluar - p["masuk"]) if beli else (p["masuk"] - keluar)) / p["masuk"] * 100
    pnl = p["posisi_usd"] * (gerak - p["biaya_pp_pct"]) / 100
    risiko = abs(p["masuk"] - p["stop"]) / p["masuk"] * 100
    return round(pnl, 2), round((gerak - p["biaya_pp_pct"]) / risiko, 2) if risiko else 0.0


def tutup(pid: str, harga: float, alasan: str = "manual") -> dict:
    j = baca()
    for p in j["posisi"]:
        if p["id"] == pid and p["status"] == "terbuka":
            p["keluar"], p["ditutup"], p["status"] = float(harga), sekarang(), alasan
            p["pnl_usd"], p["R"] = _pnl(p, float(harga))
            simpan(j)
            return p
    raise SystemExit(f"[yudi] posisi terbuka {pid} tidak ditemukan")


def _candle_sejak(p: dict) -> list[dict]:
    if p["pasar"] == "gold":
        bars = data.hl_candle(p["coin"], "5m", 300)
    else:
        bars = data.gt_candle("solana", p["pool"], "minute", 5, 300)
    return [b for b in bars if b["t"] + 300 > p["t_buka"]]


def pantau() -> list[str]:
    """Perbarui semua posisi terbuka. Kembalikan daftar pesan penting."""
    j = baca()
    pesan: list[str] = []
    for p in j["posisi"]:
        if p["status"] != "terbuka":
            continue
        try:
            bars = _candle_sejak(p)
        except data.DataGagal as err:
            pesan.append(f"{p['simbol']}: harga tidak bisa dibaca ({err})")
            continue
        if not bars:
            continue
        beli = p["arah"] == "beli"
        kena = None
        for b in bars:
            if (beli and b["l"] <= p["stop"]) or (not beli and b["h"] >= p["stop"]):
                kena = ("stop", p["stop"])
                break
            if (beli and b["h"] >= p["target"]) or (not beli and b["l"] <= p["target"]):
                kena = ("target", p["target"])
                break
        harga = bars[-1]["c"]
        p["harga_kini"] = harga
        p["pnl_kini_usd"], _ = _pnl(p, harga)
        habis = time.time() - p["t_buka"] > p["tahan_maks_jam"] * 3600
        if p["mode"] == "latihan":
            if kena or habis:
                alasan, keluar = kena or ("waktu", harga)
                p["keluar"], p["ditutup"], p["status"] = keluar, sekarang(), alasan
                p["pnl_usd"], p["R"] = _pnl(p, keluar)
                pesan.append(f"[latihan] {p['simbol']} ditutup di {alasan}: {p['pnl_usd']:+.2f} USD ({p['R']:+.2f}R)")
        else:
            kunci = kena[0] if kena else ("waktu" if habis else None)
            if kunci and p.get("diingatkan") != kunci:
                p["diingatkan"] = kunci
                teks = {"stop": f"{p['simbol']} menyentuh STOP {p['stop']:.6g} — jual sekarang di FOMO supaya rugi tidak membesar",
                        "target": f"{p['simbol']} menyentuh TARGET {p['target']:.6g} — jual di FOMO untuk mengunci untung",
                        "waktu": f"{p['simbol']} sudah {p['tahan_maks_jam']} jam — rencana selesai, pertimbangkan jual di FOMO"}[kunci]
                j.setdefault("peringatan", []).append({"waktu": sekarang(), "posisi": p["id"], "jenis": kunci, "teks": teks})
                j["peringatan"] = j["peringatan"][-50:]
                pesan.append("[NYATA] " + teks)
                import notif
                notif.kirim({"stop": "STOP: jual sekarang", "target": "TARGET: ambil untung", "waktu": "Waktu habis"}[kunci] + f" — {p['simbol']}",
                            teks + f"\nHarga kini {harga:.6g} · PnL kira-kira {p['pnl_kini_usd']:+.2f} USD", 5 if kunci == "stop" else 4,
                            {"stop": "rotating_light", "target": "moneybag", "waktu": "hourglass"}[kunci])
    simpan(j)
    return pesan


def statistik(j: dict | None = None) -> dict:
    j = j or baca()
    hasil = {}
    tgl = datetime.now(WIB).strftime("%Y-%m-%d")
    for mode in ("latihan", "nyata"):
        ps = [p for p in j["posisi"] if p["mode"] == mode and p["status"] != "terbuka"]
        menang = [p for p in ps if p.get("pnl_usd", 0) > 0]
        hari = sorted({p["ditutup"][:10] for p in ps})
        total = sum(p.get("pnl_usd", 0) for p in ps)
        hasil[mode] = {"trade": len(ps), "menang": len(menang), "kalah": len(ps) - len(menang),
                       "winrate_pct": round(len(menang) / len(ps) * 100, 1) if ps else None,
                       "rata_R": round(sum(p.get("R", 0) for p in ps) / len(ps), 2) if ps else None,
                       "pnl_total_usd": round(total, 2), "pnl_hari_ini_usd": round(sum(p.get("pnl_usd", 0) for p in ps if p["ditutup"].startswith(tgl)), 2),
                       "hari_aktif": len(hari), "rata_per_hari_usd": round(total / len(hari), 2) if hari else None,
                       "terbuka": sum(1 for p in j["posisi"] if p["mode"] == mode and p["status"] == "terbuka"),
                       "catatan": "kurang dari 30 trade: belum bisa disimpulkan" if len(ps) < 30 else ""}
    return hasil

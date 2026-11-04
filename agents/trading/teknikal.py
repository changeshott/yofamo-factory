"""Dimas — analis teknikal. Membaca candle 5 menit (+ 1 jam untuk tren) dan mencari dua setup yang aturannya tertulis
di bible/trading-bible.md: breakout & pullback. Stop dan target ditentukan SEBELUM masuk (metode trader-entry/trader-exit
dari day-trader-skill, diadaptasi untuk crypto 24 jam). Arah turun (short, hanya gold perpetual) memakai cermin harga.
"""
from __future__ import annotations

import indikator as ind


def cermin(bars: list[dict]) -> list[dict]:
    return [{"t": b["t"], "o": -b["o"], "h": -b["l"], "l": -b["h"], "c": -b["c"], "v": b["v"]} for b in bars]


def tren_1j(bars1h: list[dict], bars5: list[dict]) -> tuple[str, float]:
    """naik / turun / datar dari EMA21 1 jam (cadangan: EMA50 di 5 menit)."""
    src = bars1h if len(bars1h) >= 24 else bars5
    if len(src) < 24:
        return "datar", 0.0
    c = [b["c"] for b in src]
    e = ind.ema(c, 21 if src is bars1h else 50)
    k = ind.kemiringan(e, 8)
    ambang = 0.05 if src is bars1h else 0.01
    if c[-1] > e[-1] and k > ambang:
        return "naik", k
    if c[-1] < e[-1] and k < -ambang:
        return "turun", k
    return "datar", k


def _analisa_naik(bars: list[dict], bars1h: list[dict], rr: float, biaya_pct: float = 0.0) -> dict:
    c = [b["c"] for b in bars]
    e9, e21, e50 = ind.ema(c, 9), ind.ema(c, 21), ind.ema(c, 50)
    vw, r, a = ind.vwap(bars), ind.rsi(c), ind.atr(bars)
    b0, atr0, rsi0 = bars[-1], a[-1], r[-1]
    tren, k1j = tren_1j(bars1h, bars)
    vz = ind.vol_z(bars)
    hi, lo = ind.swing(bars[-60:])
    naik_rendah = len(lo) >= 2 and lo[-1][1] > lo[-2][1]
    rentang = b0["h"] - b0["l"]
    kualitas = (b0["c"] - b0["l"]) / rentang if rentang > 0 else 0.5
    hijau = b0["c"] > b0["o"]
    data = {"harga": b0["c"], "ema9": e9[-1], "ema21": e21[-1], "ema50": e50[-1], "vwap": vw[-1], "rsi": round(rsi0, 1),
            "atr": atr0, "atr_pct": round(atr0 / b0["c"] * 100, 2) if b0["c"] else 0, "volume_x": round(vz, 2), "tren_1j": tren,
            "low_makin_tinggi": naik_rendah}
    alasan_tolak: list[str] = []
    setup = None
    # --- breakout
    tinggi_2j = max(b["h"] for b in bars[-25:-1])
    if b0["c"] > tinggi_2j:
        syarat = [(vz >= 1.8, f"volume {vz:.1f}× (< 1,8×)"), (b0["c"] > e21[-1] and b0["c"] > vw[-1], "di bawah EMA21/VWAP"),
                  (55 <= rsi0 <= 78, f"RSI {rsi0:.0f} di luar 55–78"), (tren != "turun", "tren 1 jam turun"),
                  (b0["c"] - e21[-1] <= 4 * atr0, "terlalu jauh di atas EMA21 (mengejar harga)")]
        gagal = [t for ok, t in syarat if not ok]
        if not gagal:
            stop = min(tinggi_2j - 0.5 * atr0, b0["c"] - 0.8 * atr0)
            setup = {"jenis": "breakout", "masuk": b0["c"], "stop": stop, "level": tinggi_2j}
        else:
            alasan_tolak.append("breakout belum sah: " + ", ".join(gagal))
    # --- pullback
    if not setup:
        susun = e9[-1] > e21[-1] > e50[-1]
        sentuh = any(b["l"] <= max(e21[-1 - i], vw[-1 - i]) * 1.004 for i, b in enumerate(reversed(bars[-4:])))
        if susun and sentuh:
            syarat = [(tren == "naik", f"tren 1 jam {tren}"), (hijau and b0["c"] > e9[-1], "belum ada candle hijau tutup di atas EMA9"),
                      (40 <= rsi0 <= 62, f"RSI {rsi0:.0f} di luar 40–62"), (b0["c"] > e50[-1], "di bawah EMA50")]
            gagal = [t for ok, t in syarat if not ok]
            if not gagal:
                stop = min(b["l"] for b in bars[-6:]) - 0.3 * atr0
                setup = {"jenis": "pullback", "masuk": b0["c"], "stop": stop, "level": e21[-1]}
            else:
                alasan_tolak.append("pullback belum sah: " + ", ".join(gagal))
        elif not susun:
            alasan_tolak.append("EMA belum tersusun naik (9 > 21 > 50)")
    # --- skor teknikal 0–100 (dipakai juga saat tidak ada setup)
    skor = 0
    skor += {"naik": 25, "datar": 10, "turun": 0}[tren]
    skor += min(20, max(0, (vz - 0.8) * 12))
    skor += 15 if 50 <= rsi0 <= 70 else 8 if 40 <= rsi0 <= 78 else 0
    skor += (8 if b0["c"] > vw[-1] else 0) + (7 if b0["c"] > e21[-1] else 0)
    skor += 15 if naik_rendah else 0
    skor += 10 * kualitas if hijau else 0
    hasil = {"skor": round(min(100, skor)), "data": data, "setup": None, "catatan": alasan_tolak}
    if setup:
        risiko = setup["masuk"] - setup["stop"]
        if risiko <= 0 or risiko < 0.35 * atr0:
            hasil["catatan"].append("stop terlalu dekat (kena noise)")
            return hasil
        # target dipilih supaya untung BERSIH (setelah biaya pulang-pergi) = rr × rugi BERSIH di stop
        rp = risiko / setup["masuk"] * 100
        target = setup["masuk"] * (1 + (rr * (rp + biaya_pct) + biaya_pct) / 100)
        res = [p for p, kuat in ind.level(bars[-200:]) if kuat >= 2 and setup["masuk"] + 0.3 * risiko < p < target]
        if res and (res[0] - setup["masuk"]) < 1.5 * risiko:
            hasil["catatan"].append(f"resistance terlalu dekat ({res[0]:.6g}) sebelum target")
            return hasil
        setup.update({"target": target, "rr": rr, "rr_kotor": round((target - setup["masuk"]) / risiko, 2), "risiko_pct": rp,
                      "resistance": res[0] if res else None})
        hasil["setup"] = setup
    return hasil


def analisa(bars5: list[dict], bars1h: list[dict] | None = None, rr: float = 2.0, dua_arah: bool = False, biaya_pct: float = 0.0) -> dict:
    """Hasil: skor, data indikator, setup (arah, masuk, stop, target) atau None + catatan kenapa tidak ada setup."""
    bars1h = bars1h or []
    if len(bars5) < 60:
        return {"skor": 0, "data": {}, "setup": None, "catatan": [f"candle 5 menit baru {len(bars5)} (butuh ≥ 60)"], "arah": None}
    naik = _analisa_naik(bars5, bars1h, rr, biaya_pct)
    naik["arah"] = "beli"
    if naik["setup"] or not dua_arah:
        if naik["setup"]:
            naik["setup"]["arah"] = "beli"
        return naik
    turun = _analisa_naik(cermin(bars5), cermin(bars1h), rr, biaya_pct)
    if turun["setup"]:
        s = turun["setup"]
        for k in ("masuk", "stop", "target", "level", "resistance"):
            if s.get(k) is not None:
                s[k] = -s[k]
        s["arah"] = "jual"
        for k in ("harga", "ema9", "ema21", "ema50", "vwap"):
            turun["data"][k] = -turun["data"][k]
        turun["data"]["tren_1j"] = {"naik": "turun", "turun": "naik"}.get(turun["data"]["tren_1j"], "datar")
        turun["arah"] = "jual"
        return turun
    naik["catatan"] += ["(arah jual) " + c for c in turun["catatan"][:2]]
    return naik


def grafik(bars: list[dict], n: int = 96) -> list[list[float]]:
    """Candle ringkas untuk Studio: [t, o, h, l, c]."""
    return [[b["t"], b["o"], b["h"], b["l"], b["c"]] for b in bars[-n:]]

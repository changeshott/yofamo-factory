"""Bagas — mesin waktu. Sebelum satu dolar pun dipertaruhkan: putar ulang jam-jam berikutnya 10.000 kali dari candle 5 menit
koin itu sendiri, lalu uji ulang setup yang sama pada setiap kali ia muncul di riwayat. Diadaptasi dari trader-timemachine
(day-trader-skill, MIT): rasio OHLC per bar terhadap close sebelumnya, stop dicek dulu (bar yang menyentuh keduanya = stop),
vonis dibanding titik impas 1/(1+R). Bedanya: crypto 24 jam (tanpa sesi), sampel blok 3 bar supaya momentum terbawa,
dan biaya FOMO + slippage dipotong dari setiap hasil.
"""
from __future__ import annotations

import random


def _rasio(bars: list[dict]) -> list[tuple[float, float, float, float]]:
    out = []
    for i in range(1, len(bars)):
        pc = bars[i - 1]["c"]
        if pc > 0:
            b = bars[i]
            out.append((b["o"] / pc, b["h"] / pc, b["l"] / pc, b["c"] / pc))
    return out


def mesin_waktu(bars: list[dict], setup: dict, biaya_pct: float, maks_bar: int, ulang: int = 10000, seed: int = 19) -> dict:
    """biaya_pct = total biaya pulang-pergi (beli+jual+slippage) dalam % harga masuk."""
    pool = _rasio(bars[-577:])
    masuk, stop, target = setup["masuk"], setup["stop"], setup["target"]
    beli = setup.get("arah", "beli") == "beli"
    risiko = abs(masuk - stop)
    if len(pool) < 30 or risiko <= 0:
        return {"cukup": False, "catatan": "data candle belum cukup untuk simulasi"}
    R_target = abs(target - masuk) / risiko
    biaya_R = (biaya_pct / 100 * masuk) / risiko
    rng = random.Random(seed)
    n_pool = len(pool)
    kena_t = kena_s = 0
    total_R, akhir = 0.0, []
    for _ in range(ulang):
        p, hasil, i = masuk, None, 0
        while i < maks_bar and hasil is None:
            j = rng.randrange(n_pool - 2)
            for k in range(3):
                if i >= maks_bar:
                    break
                _, h, l, c = pool[j + k]
                hi, lo, p = p * h, p * l, p * c
                if beli:
                    if lo <= stop:
                        hasil = -1.0
                    elif hi >= target:
                        hasil = R_target
                else:
                    if hi >= stop:
                        hasil = -1.0
                    elif lo <= target:
                        hasil = R_target
                i += 1
                if hasil is not None:
                    break
        if hasil is None:
            hasil = ((p - masuk) if beli else (masuk - p)) / risiko
            akhir.append(p)
        elif hasil > 0:
            kena_t += 1
        else:
            kena_s += 1
        total_R += hasil - biaya_R
    selesai = kena_t + kena_s
    impas = (1 + biaya_R) / (1 + R_target)        # peluang target minimal supaya impas setelah biaya
    p_t = kena_t / selesai if selesai else 0
    return {"cukup": True, "ulang": ulang, "seed": seed, "maks_bar": maks_bar, "R_target": round(R_target, 2), "biaya_R": round(biaya_R, 3),
            "peluang_target_pct": round(kena_t / ulang * 100, 1), "peluang_stop_pct": round(kena_s / ulang * 100, 1),
            "masih_terbuka_pct": round((ulang - selesai) / ulang * 100, 1), "target_dulu_dari_selesai_pct": round(p_t * 100, 1),
            "impas_pct": round(impas * 100, 1), "ev_R": round(total_R / ulang, 3), "vonis": vonis(p_t, impas, selesai)}


def vonis(p: float, impas: float, selesai: int) -> str:
    if selesai < 200:
        return "Kebanyakan jalur belum selesai sampai batas waktu — hasilnya lebih ditentukan arah harga saat ditutup."
    d = (p - impas) * 100
    if abs(d) < 5:
        return "Dekat titik impas setelah biaya — praktis lempar koin."
    if d >= 15:
        return "Sangat condong ke target."
    if d >= 5:
        return "Condong ke target."
    if d <= -15:
        return "Sangat condong ke stop."
    return "Condong ke stop."


def riwayat(bars: list[dict], deteksi, biaya_pct: float, maks_bar: int, mulai: int = 60) -> dict:
    """Jalankan aturan setup yang sama di setiap titik riwayat; tiap kali muncul, lihat apa yang BENAR-BENAR terjadi."""
    menang = kalah = terbuka = 0
    total_R = 0.0
    i = mulai
    while i < len(bars) - 1:
        s = deteksi(bars[: i + 1])
        if not s:
            i += 1
            continue
        beli = s.get("arah", "beli") == "beli"
        risiko = abs(s["masuk"] - s["stop"])
        Rt = abs(s["target"] - s["masuk"]) / risiko if risiko else 0
        biaya_R = (biaya_pct / 100 * s["masuk"]) / risiko if risiko else 0
        hasil, j = None, i + 1
        while j < min(len(bars), i + 1 + maks_bar) and hasil is None:
            b = bars[j]
            if (beli and b["l"] <= s["stop"]) or (not beli and b["h"] >= s["stop"]):
                hasil = -1.0
            elif (beli and b["h"] >= s["target"]) or (not beli and b["l"] <= s["target"]):
                hasil = Rt
            j += 1
        if hasil is None:
            if j >= len(bars):            # masih berjalan sampai candle terakhir: jangan dihitung
                break
            akhir = bars[j - 1]["c"]
            hasil = ((akhir - s["masuk"]) if beli else (s["masuk"] - akhir)) / risiko
            terbuka += 1
        elif hasil > 0:
            menang += 1
        else:
            kalah += 1
        total_R += hasil - biaya_R
        i = j                             # tidak tumpang tindih: setup berikutnya dicari setelah yang ini selesai
    n = menang + kalah + terbuka
    return {"muncul": n, "target": menang, "stop": kalah, "waktu_habis": terbuka, "ev_R": round(total_R / n, 3) if n else None,
            "catatan": "riwayat < 5 kali: belum bisa disebut pola" if n < 5 else ""}

"""Indikator teknikal murni (tanpa library): bar = {t,o,h,l,c,v}, urut lama → baru."""
from __future__ import annotations

import math


def ema(nilai: list[float], n: int) -> list[float]:
    if not nilai:
        return []
    k, out = 2 / (n + 1), [nilai[0]]
    for v in nilai[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def sma(nilai: list[float], n: int) -> list[float]:
    out, s = [], 0.0
    for i, v in enumerate(nilai):
        s += v
        if i >= n:
            s -= nilai[i - n]
        out.append(s / min(i + 1, n))
    return out


def rsi(close: list[float], n: int = 14) -> list[float]:
    if len(close) < 2:
        return [50.0] * len(close)
    out, naik, turun = [50.0], 0.0, 0.0
    for i in range(1, len(close)):
        d = close[i] - close[i - 1]
        g, l = max(d, 0), max(-d, 0)
        if i <= n:
            naik += g / n
            turun += l / n
        else:
            naik = (naik * (n - 1) + g) / n
            turun = (turun * (n - 1) + l) / n
        out.append(100.0 if turun == 0 else 100 - 100 / (1 + naik / turun))
    return out


def atr(bars: list[dict], n: int = 14) -> list[float]:
    tr = []
    for i, b in enumerate(bars):
        pc = bars[i - 1]["c"] if i else b["c"]
        tr.append(max(b["h"] - b["l"], abs(b["h"] - pc), abs(b["l"] - pc)))
    out = []
    for i, v in enumerate(tr):
        out.append(v if i == 0 else (out[-1] * (n - 1) + v) / n)
    return out


def vwap(bars: list[dict], n: int = 48) -> list[float]:
    """VWAP bergulir n bar (crypto 24 jam tidak punya sesi)."""
    out, pv, vv = [], [], []
    for b in bars:
        tp = (b["h"] + b["l"] + b["c"]) / 3
        pv.append(tp * b["v"])
        vv.append(b["v"])
        a, z = sum(pv[-n:]), sum(vv[-n:])
        out.append(a / z if z > 0 else b["c"])
    return out


def macd(close: list[float]) -> tuple[list[float], list[float]]:
    e12, e26 = ema(close, 12), ema(close, 26)
    m = [a - b for a, b in zip(e12, e26)]
    return m, ema(m, 9)


def swing(bars: list[dict], kiri: int = 3, kanan: int = 3) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    """Titik swing high & low (indeks, harga)."""
    hi, lo = [], []
    for i in range(kiri, len(bars) - kanan):
        jendela = bars[i - kiri:i + kanan + 1]
        if bars[i]["h"] == max(b["h"] for b in jendela):
            hi.append((i, bars[i]["h"]))
        if bars[i]["l"] == min(b["l"] for b in jendela):
            lo.append((i, bars[i]["l"]))
    return hi, lo


def level(bars: list[dict], toleransi: float = 0.012) -> list[tuple[float, int]]:
    """Support/resistance: swing yang berkumpul di harga mirip → (harga, kekuatan)."""
    hi, lo = swing(bars)
    titik = sorted(p for _, p in hi + lo)
    kelompok: list[list[float]] = []
    for p in titik:
        if kelompok and abs(p - kelompok[-1][-1]) / max(p, 1e-12) <= toleransi:
            kelompok[-1].append(p)
        else:
            kelompok.append([p])
    return sorted(((sum(k) / len(k), len(k)) for k in kelompok), key=lambda x: x[0])


def vol_z(bars: list[dict], n: int = 30) -> float:
    """Volume bar terakhir dibanding rata-rata n bar sebelumnya (kelipatan)."""
    if len(bars) < 5:
        return 1.0
    sebelum = [b["v"] for b in bars[-n - 1:-1]]
    rata = sum(sebelum) / max(1, len(sebelum))
    return bars[-1]["v"] / rata if rata > 0 else 1.0


def kemiringan(nilai: list[float], n: int = 10) -> float:
    """% perubahan per bar dari regresi garis n titik terakhir."""
    y = nilai[-n:]
    if len(y) < 3 or y[-1] == 0:
        return 0.0
    xs = range(len(y))
    mx, my = sum(xs) / len(y), sum(y) / len(y)
    b = sum((x - mx) * (v - my) for x, v in zip(xs, y)) / max(1e-12, sum((x - mx) ** 2 for x in xs))
    return b / abs(my) * 100


def volatilitas(bars: list[dict], n: int = 48) -> float:
    """Standar deviasi return log per bar (%)."""
    c = [b["c"] for b in bars[-n - 1:]]
    r = [math.log(c[i] / c[i - 1]) for i in range(1, len(c)) if c[i - 1] > 0 and c[i] > 0]
    if len(r) < 3:
        return 0.0
    m = sum(r) / len(r)
    return math.sqrt(sum((x - m) ** 2 for x in r) / (len(r) - 1)) * 100

#!/usr/bin/env python3
"""Membuat data contoh (sintetis, deterministik) untuk mode uji Ruang Trading: format persis seperti API aslinya.
Empat token: UJIBREAK (sehat + breakout), UJIRUG (berbahaya), UJIDIAM (sehat, belum ada setup), UJISEPI (likuiditas tipis),
plus gold (xyz:GOLD) dari Hyperliquid. Jalankan ulang hanya kalau formatnya berubah: python agents/trading/contoh/buat_contoh.py
"""
from __future__ import annotations

import gzip
import json
import math
import random
import time
from pathlib import Path

OUT = Path(__file__).resolve().parent
T0 = 1793750400            # titik waktu tetap supaya hasil uji selalu sama


def tulis(nama: str, d) -> None:
    raw = json.dumps(d, separators=(",", ":")).encode()
    if len(raw) > 40_000:
        (OUT / f"{nama}.json.gz").write_bytes(gzip.compress(raw, mtime=0))
    else:
        (OUT / f"{nama}.json").write_bytes(raw)


def jalan(seed: int, n: int, p0: float, drift: float, vol: float, akhir: str = "") -> list[list[float]]:
    rng = random.Random(seed)
    bars, p = [], p0
    for i in range(n):
        d = drift
        if akhir == "breakout" and n - 40 <= i < n - 1:
            d = 0.0                                   # konsolidasi 3 jam sebelum breakout
        r = rng.gauss(d, vol * (0.55 if akhir == "breakout" and n - 40 <= i < n - 1 else 1))
        o = p
        c = p * math.exp(r)
        if akhir == "breakout" and i == n - 1:
            c = max(b[2] for b in bars[-25:]) * 1.018    # tutup di atas high 2 jam
        h = max(o, c) * (1 + abs(rng.gauss(0, vol * 0.5)))
        l = min(o, c) * (1 - abs(rng.gauss(0, vol * 0.5)))
        v = abs(rng.gauss(8000, 2500)) * (3.2 if akhir == "breakout" and i == n - 1 else 1)
        bars.append([T0 - (n - 1 - i) * 300, o, h, l, c, v])
        p = c
    return bars


def gt(bars):
    return {"data": {"attributes": {"ohlcv_list": list(reversed(bars))}}}


def jam(bars5):
    out = []
    for i in range(0, len(bars5) - 11, 12):
        k = bars5[i:i + 12]
        out.append([k[0][0], k[0][1], max(b[2] for b in k), min(b[3] for b in k), k[-1][4], sum(b[5] for b in k)])
    return out


TOKEN = {
    "UJIBREAK": dict(mint="UjBrk7xQ9wz3Lm2Np4Rs6Tv8Xy1Ab3Cd5Ef7GhpumpA", pool="PoBrk7xQ9wz3Lm2Np4Rs6Tv8Xy1Ab3Cd5Ef7GhPool1", liq=180000, mcap=2400000,
                     vol1=95000, buys=820, sells=540, h1=6.5, h24=48, umur=30, seed=7, drift=0.004, vol=0.03, akhir="breakout",
                     risks=[{"name": "Mutable metadata", "level": "warn", "score": 100}], skor=12, lp=100, mintA=None, top=[4.1, 3.0, 2.2, 1.9, 1.5, 1.2, 1.0, 0.9, 0.8, 0.7]),
    "UJIRUG": dict(mint="UjRug4Kp8Lm2Nq6Rs1Tv3Wx5Yz7Ab9Cd2Ef4GhpumpB", pool="PoRug4Kp8Lm2Nq6Rs1Tv3Wx5Yz7Ab9Cd2Ef4GhPool2", liq=90000, mcap=900000,
                   vol1=60000, buys=700, sells=500, h1=12, h24=120, umur=9, seed=11, drift=0.002, vol=0.02, akhir="",
                   risks=[{"name": "Mint Authority still enabled", "level": "danger", "score": 3000}, {"name": "Top 10 holders high ownership", "level": "danger", "score": 1500}],
                   skor=78, lp=20, mintA="UjRugMintAuth1111111111111111111111111111", top=[22, 9, 6, 5, 4, 3, 3, 2, 2, 2]),
    "UJIDIAM": dict(mint="UjDiam2Hk5Lm8Np1Qr4St7Uv9Wx2Yz5Ab8CdpumpC", pool="PoDiam2Hk5Lm8Np1Qr4St7Uv9Wx2Yz5Ab8CdPool3", liq=250000, mcap=5200000,
                    vol1=40000, buys=300, sells=320, h1=-1.2, h24=-8, umur=96, seed=23, drift=-0.0002, vol=0.006, akhir="",
                    risks=[], skor=4, lp=100, mintA=None, top=[3.0, 2.5, 2.0, 1.8, 1.4, 1.1, 1.0, 0.9, 0.8, 0.7]),
    "UJISEPI": dict(mint="UjSepi9Bc3Df6Gh9Jk2Lm5Np8Qr1St4Uv7WxpumpD", pool="PoSepi9Bc3Df6Gh9Jk2Lm5Np8Qr1St4Uv7WxPool4", liq=9000, mcap=60000,
                    vol1=2000, buys=30, sells=25, h1=2, h24=10, umur=40, seed=31, drift=0.0, vol=0.01, akhir="",
                    risks=[], skor=20, lp=100, mintA=None, top=[5] * 10),
}


def main() -> None:
    trending, pairs = [], []
    for sim, t in TOKEN.items():
        trending.append({"id": f"solana_{t['pool']}", "type": "pool", "attributes": {"name": f"{sim} / SOL", "address": t["pool"]},
                         "relationships": {"base_token": {"data": {"id": f"solana_{t['mint']}", "type": "token"}}}})
        pairs.append({"chainId": "solana", "dexId": "raydium", "url": f"https://dexscreener.com/solana/{t['pool'].lower()}", "pairAddress": t["pool"],
                      "baseToken": {"address": t["mint"], "name": sim.title(), "symbol": sim}, "quoteToken": {"address": "So11111111111111111111111111111111111111112", "name": "Wrapped SOL", "symbol": "SOL"},
                      "priceUsd": "0.001", "txns": {"m5": {"buys": t["buys"] // 12, "sells": t["sells"] // 12}, "h1": {"buys": t["buys"], "sells": t["sells"]},
                      "h6": {"buys": t["buys"] * 5, "sells": t["sells"] * 5}, "h24": {"buys": t["buys"] * 18, "sells": t["sells"] * 18}},
                      "volume": {"h24": t["vol1"] * 16, "h6": t["vol1"] * 5, "h1": t["vol1"], "m5": t["vol1"] / 12},
                      "priceChange": {"m5": 0.8, "h1": t["h1"], "h6": t["h1"] * 2, "h24": t["h24"]}, "liquidity": {"usd": t["liq"], "base": 1, "quote": 1},
                      "fdv": t["mcap"], "marketCap": t["mcap"], "pairCreatedAt": int((time.time() - t["umur"] * 3600) * 1000),
                      "info": {"websites": [{"label": "Website", "url": "https://contoh.invalid"}], "socials": [{"type": "twitter", "url": "https://x.com/contoh"}]}})
        tulis(f"rc_{t['mint'][:8]}", {"tokenProgram": "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", "tokenType": "", "risks": t["risks"], "score": t["skor"] * 10,
                                       "score_normalised": t["skor"], "lpLockedPct": t["lp"]})
        tulis(f"rcfull_{t['mint'][:8]}", {"mintAuthority": t["mintA"], "freezeAuthority": None, "rugged": False, "totalHolders": 4200 if sim != "UJIRUG" else 380,
                                           "markets": [{"pubkey": t["pool"], "liquidityAAccount": t["pool"][:-1] + "A"}],
                                           "topHolders": [{"address": t["pool"][:-1] + "A", "owner": t["pool"], "pct": 18.0, "insider": False}] +
                                                         [{"address": f"Holder{sim}{i:02d}xxxxxxxxxxxxxxxxxxxxxxxxxxxx", "owner": f"Owner{sim}{i:02d}xxxxxxxxxxxxxxxxxxxxxxxxxxx", "pct": p, "insider": False}
                                                          for i, p in enumerate(t["top"])]})
        b5 = jalan(t["seed"], 300, 0.001, t["drift"], t["vol"], t["akhir"])
        tulis(f"gt_candle_{t['pool'][:8]}_minute5", gt(b5))
        tulis(f"gt_candle_{t['pool'][:8]}_hour1", gt(jam(jalan(t["seed"] + 1, 72 * 12, 0.0006, t["drift"], t["vol"]))))
    tulis("gt_trending_solana", {"data": trending})
    tulis("ds_pairs_solana", pairs)
    tulis("ds_profil", [{"chainId": "solana", "tokenAddress": TOKEN["UJIDIAM"]["mint"]}])
    tulis("ds_boosts", [{"chainId": "solana", "tokenAddress": TOKEN["UJIRUG"]["mint"], "totalAmount": 500}])
    # gold: pullback/breakout netral — tujuan uji: jalur berjalan tanpa error
    g5 = jalan(101, 400, 4020.0, 0.00006, 0.0012, "breakout")
    g1 = jam(jalan(102, 200 * 12, 3900.0, 0.00006, 0.0012))
    hl = lambda bars: [{"t": int(b[0] * 1000), "T": int(b[0] * 1000) + 299999, "s": "xyz:GOLD", "i": "5m", "o": f"{b[1]:.2f}", "c": f"{b[4]:.2f}",
                        "h": f"{b[2]:.2f}", "l": f"{b[3]:.2f}", "v": f"{b[5] / 1000:.3f}", "n": 40} for b in bars]
    tulis("hl_xyz_GOLD_5m", hl(g5))
    tulis("hl_xyz_GOLD_1h", hl(g1))
    tulis("hlctx_xyz", [{"universe": [{"name": "xyz:GOLD", "szDecimals": 4, "maxLeverage": 25}]},
                        [{"funding": "0.0000125", "openInterest": "15234.5", "markPx": f"{g5[-1][4]:.2f}", "oraclePx": f"{g5[-1][4] * 0.9998:.2f}", "dayNtlVlm": "48200000"}]])
    print("contoh dibuat:", sorted(p.name for p in OUT.glob("*.json*")))


if __name__ == "__main__":
    main()

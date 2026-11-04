"""Nadia — analis fundamental on-chain. Memecoin tidak punya laporan keuangan; "fundamental"-nya adalah kesehatan pasar
token itu sendiri: kedalaman likuiditas dibanding market cap, perputaran volume, tekanan beli (jumlah & pembeli unik),
konsistensi momentum lintas jangka waktu, umur, sebaran holder, dan kehadiran komunitas. Untuk gold: funding,
open interest, dan selisih harga mark vs oracle. Narasi & berita dibahas Nadia lewat /trading-analisa (Claude + web).
"""
from __future__ import annotations


def _f(x, d=0.0) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def meme(pair: dict, aman: dict) -> dict:
    liq = _f((pair.get("liquidity") or {}).get("usd"))
    mcap = _f(pair.get("marketCap") or pair.get("fdv"))
    vol24 = _f((pair.get("volume") or {}).get("h24"))
    vol1 = _f((pair.get("volume") or {}).get("h1"))
    pc = pair.get("priceChange") or {}
    tx = pair.get("txns") or {}
    b1, s1 = _f((tx.get("h1") or {}).get("buys")), _f((tx.get("h1") or {}).get("sells"))
    b6, s6 = _f((tx.get("h6") or {}).get("buys")), _f((tx.get("h6") or {}).get("sells"))
    info = pair.get("info") or {}
    sosial = sorted({s.get("type", "web") for s in info.get("socials") or []} | ({"website"} if info.get("websites") else set()))
    r = aman.get("rincian") or {}
    poin, catatan = 0.0, []
    # 1. likuiditas vs mcap (sehat 4–30%)
    rasio = liq / mcap * 100 if mcap else 0
    if 4 <= rasio <= 30:
        poin += 20
        catatan.append(f"likuiditas {rasio:.1f}% dari market cap (sehat)")
    elif rasio > 30:
        poin += 12
        catatan.append(f"likuiditas {rasio:.0f}% dari market cap (tebal, gerak lebih lambat)")
    else:
        poin += 4
        catatan.append(f"likuiditas hanya {rasio:.1f}% dari market cap (tipis, mudah dibanting)")
    # 2. perputaran volume 24 jam / likuiditas (aktif tapi tidak gila)
    putar = vol24 / liq if liq else 0
    poin += 15 if 1 <= putar <= 15 else 8 if putar > 15 else 3
    catatan.append(f"volume 24 jam {putar:.1f}× likuiditas")
    # 3. tekanan beli 1 jam & 6 jam
    tb1 = b1 / (b1 + s1) if b1 + s1 else 0.5
    tb6 = b6 / (b6 + s6) if b6 + s6 else 0.5
    poin += 20 * min(1, max(0, (tb1 - 0.45) / 0.2)) * 0.6 + 20 * min(1, max(0, (tb6 - 0.45) / 0.2)) * 0.4
    catatan.append(f"porsi transaksi beli: {tb1 * 100:.0f}% (1 jam), {tb6 * 100:.0f}% (6 jam)")
    # 4. konsistensi momentum
    m5, h1, h6, h24 = (_f(pc.get(k)) for k in ("m5", "h1", "h6", "h24"))
    positif = sum(1 for x in (h1, h6, h24) if x > 0)
    poin += positif * 5
    if h1 > 60:
        poin -= 8
        catatan.append(f"naik {h1:.0f}% dalam 1 jam (euforia, rawan koreksi)")
    # 5. umur & holder
    umur = r.get("umur_jam")
    if umur is not None:
        poin += 10 if umur >= 24 else 6 if umur >= 6 else 2
    holder = r.get("holder_total")
    if holder:
        poin += 10 if holder >= 3000 else 6 if holder >= 800 else 2
        catatan.append(f"{int(holder):,} holder")
    # 6. komunitas
    poin += min(10, 4 * len(sosial))
    if not sosial:
        catatan.append("tanpa website/sosial media")
    return {"skor": round(max(0, min(100, poin))), "catatan": catatan,
            "angka": {"mcap_usd": mcap, "likuiditas_usd": liq, "likuiditas_per_mcap_pct": round(rasio, 2), "volume_24j_usd": vol24,
                      "volume_1j_usd": vol1, "perputaran_24j": round(putar, 2), "porsi_beli_1j": round(tb1, 3), "porsi_beli_6j": round(tb6, 3),
                      "perubahan_pct": {"5m": m5, "1j": h1, "6j": h6, "24j": h24}, "sosial": sosial}}


def gold(ctx: dict, arah: str | None) -> dict:
    """funding positif = posisi beli membayar posisi jual tiap jam (biaya menahan)."""
    if not ctx:
        return {"skor": 50, "catatan": ["konteks pasar Hyperliquid tidak tersedia"], "angka": {}}
    f = ctx.get("funding", 0) * 100
    selisih = (ctx["mark"] - ctx["oracle"]) / ctx["oracle"] * 100 if ctx.get("oracle") else 0
    poin, cat = 60.0, [f"funding {f:+.4f}%/jam", f"mark vs oracle {selisih:+.3f}%", f"open interest {ctx.get('oi', 0):,.0f}"]
    bayar = (arah == "beli" and f > 0) or (arah == "jual" and f < 0)
    if bayar and abs(f) > 0.002:
        poin -= 15
        cat.append("arah ini membayar funding yang cukup mahal")
    elif arah and not bayar:
        poin += 10
        cat.append("arah ini menerima funding")
    if abs(selisih) > 0.3:
        poin -= 10
        cat.append("harga mark menjauh dari oracle (pasar sedang tidak seimbang)")
    return {"skor": round(max(0, min(100, poin))), "catatan": cat, "angka": {**ctx, "funding_pct_jam": f, "mark_vs_oracle_pct": selisih}}

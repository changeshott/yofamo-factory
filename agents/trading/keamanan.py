"""Sinta — penjaga keamanan memecoin. Satu syarat gagal = BLOKIR (aturan di bible/trading-bible.md).
Sumber: RugCheck (gratis) + angka pair DexScreener. Tujuannya bukan mencari koin "aman" (tidak ada yang aman), tapi
membuang yang jelas berbahaya: rug pull, honeypot, pasokan dikuasai segelintir dompet, likuiditas tipis.
"""
from __future__ import annotations

import time

import data


def _str_set(x, out: set) -> set:
    if isinstance(x, str) and len(x) >= 32:
        out.add(x)
    elif isinstance(x, dict):
        for v in x.values():
            _str_set(v, out)
    elif isinstance(x, list):
        for v in x:
            _str_set(v, out)
    return out


def periksa(pair: dict, cfg: dict) -> dict:
    """Hasil: {lolos, skor (0–100, tinggi = lebih aman), blokir[], peringatan[], rincian{}}."""
    m = cfg["meme"]
    blokir, waspada, rinci = [], [], {}
    liq = float((pair.get("liquidity") or {}).get("usd") or 0)
    umur_jam = (time.time() * 1000 - float(pair.get("pairCreatedAt") or 0)) / 3_600_000 if pair.get("pairCreatedAt") else None
    tx1 = (pair.get("txns") or {}).get("h1") or {}
    beli, jual = int(tx1.get("buys") or 0), int(tx1.get("sells") or 0)
    naik24 = float((pair.get("priceChange") or {}).get("h24") or 0)
    vol1 = float((pair.get("volume") or {}).get("h1") or 0)
    rinci.update({"likuiditas_usd": liq, "umur_jam": round(umur_jam, 1) if umur_jam is not None else None, "beli_1j": beli, "jual_1j": jual,
                  "naik_24j_pct": naik24, "volume_1j_usd": vol1})
    if liq < m["likuiditas_min_usd"]:
        blokir.append(f"likuiditas ${liq:,.0f} < ${m['likuiditas_min_usd']:,}")
    if umur_jam is not None and umur_jam < m["umur_min_jam"]:
        blokir.append(f"pair baru berumur {umur_jam:.1f} jam (< {m['umur_min_jam']} jam)")
    if vol1 < m["volume_1j_min_usd"]:
        blokir.append(f"volume 1 jam ${vol1:,.0f} terlalu sepi")
    if beli >= 25 and jual <= max(1, beli // 25):
        blokir.append(f"pola honeypot: {beli} beli vs {jual} jual dalam 1 jam")
    if naik24 > m["naik_24j_maks_pct"]:
        blokir.append(f"sudah naik {naik24:.0f}% dalam 24 jam (terlambat, rawan dibuang)")

    mint = (pair.get("baseToken") or {}).get("address", "")
    try:
        rc = data.rc_ringkas(mint)
    except data.DataGagal as err:
        rc = {}
        waspada.append(f"RugCheck tidak bisa dibaca ({err}) → keamanan tidak terverifikasi")
        blokir.append("laporan keamanan RugCheck tidak tersedia")
    skor_rc = rc.get("score_normalised")
    risiko = rc.get("risks") or []
    rinci["rugcheck_skor"] = skor_rc
    rinci["rugcheck_risiko"] = [f"{r.get('level', '?')}: {r.get('name', '')}" for r in risiko]
    for r in risiko:
        nama = str(r.get("name", ""))
        if r.get("level") == "danger":
            blokir.append(f"RugCheck bahaya: {nama}")
        elif r.get("level") == "warn":
            waspada.append(f"RugCheck: {nama}")
    if skor_rc is not None and float(skor_rc) > m["rugcheck_skor_maks"]:
        blokir.append(f"skor risiko RugCheck {skor_rc} > {m['rugcheck_skor_maks']}")
    lp = rc.get("lpLockedPct")
    rinci["lp_terkunci_pct"] = round(float(lp), 1) if lp is not None else None
    if lp is not None and float(lp) < m["lp_terkunci_min_pct"]:
        waspada.append(f"LP terkunci/terbakar hanya {float(lp):.0f}%")

    if mint:
        full = data.rc_lengkap(mint)
        if full:
            if full.get("mintAuthority"):
                blokir.append("mint authority masih aktif (pasokan bisa dicetak lagi)")
            if full.get("freezeAuthority"):
                blokir.append("freeze authority masih aktif (dompetmu bisa dibekukan)")
            if full.get("rugged"):
                blokir.append("RugCheck menandai token ini sudah di-rug")
            pasar = _str_set(full.get("markets") or [], set())
            holder = [h for h in (full.get("topHolders") or []) if h.get("address") not in pasar and h.get("owner") not in pasar]
            top10 = sum(float(h.get("pct") or 0) for h in holder[:10])
            insider = sum(1 for h in holder[:10] if h.get("insider"))
            rinci.update({"top10_holder_pct": round(top10, 1), "holder_total": full.get("totalHolders"), "insider_top10": insider})
            if top10 > m["top10_holder_maks_pct"]:
                blokir.append(f"top 10 holder menguasai {top10:.0f}% pasokan")
            if insider >= 3:
                waspada.append(f"{insider} dari 10 holder teratas ditandai insider")
    info = pair.get("info") or {}
    if not (info.get("socials") or info.get("websites")):
        waspada.append("tidak ada website/sosial media")
    if (pair.get("boosts") or {}).get("active"):
        waspada.append("sedang dipromosikan berbayar (boost DexScreener)")

    skor = 100 - 40 * len(blokir) - 8 * len(waspada)
    if skor_rc is not None:
        skor -= float(skor_rc) * 0.4
    return {"lolos": not blokir, "skor": max(0, round(skor)), "blokir": blokir, "peringatan": waspada, "rincian": rinci}

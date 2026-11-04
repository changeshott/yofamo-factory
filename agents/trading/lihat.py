#!/usr/bin/env python3
"""Lihat satu koin/gold lengkap (keamanan, teknikal, fundamental, mesin waktu, ukuran posisi) TANPA membuat sinyal.

    python agents/trading/lihat.py <alamat_token_solana>      # mis. alamat yang Zona temukan sendiri di FOMO
    python agents/trading/lihat.py gold
    python agents/trading/lihat.py <sinyal_id>                # tampilkan sinyal yang sudah ada
    ... --uji
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
if "--uji" in sys.argv:
    os.environ["YOFAMO_TRADING_UJI"] = "1"
import tanpa_jendela  # noqa: E402,F401
import data  # noqa: E402

if data.uji():
    data.TRADING = data.ROOT / "trading-uji"
    data.CACHE = data.TRADING / "cache"
import fundamental  # noqa: E402
import jurnal  # noqa: E402
import keamanan  # noqa: E402
import risiko  # noqa: E402
import simulasi  # noqa: E402
import teknikal  # noqa: E402

jurnal.F = data.TRADING / "jurnal.json"


def main() -> None:
    arg = next((a for a in sys.argv[1:] if not a.startswith("--")), "")
    if not arg:
        sys.exit(__doc__)
    c = json.loads((data.ROOT / "bible" / "trading.json").read_text(encoding="utf-8"))
    f = data.TRADING / "sinyal" / f"{arg}.json"
    if f.exists():
        s = json.loads(f.read_text(encoding="utf-8"))
        s.pop("grafik", None)
        print(json.dumps(s, ensure_ascii=False, indent=1))
        return
    j = jurnal.baca()
    if arg.lower() == "gold":
        g = c["gold"]
        coin = g["coin"]
        b5, b1h = data.hl_candle(coin, "5m", 400), data.hl_candle(coin, "1h", 200)
        if len(b5) < 60:
            coin = g["cadangan"]
            b5, b1h = data.hl_candle(coin, "5m", 400), data.hl_candle(coin, "1h", 200)
        biaya = risiko.biaya_pp(c, "gold", 10, 0)
        tek = teknikal.analisa(b5, b1h, c["min_rr"], dua_arah=True, biaya_pct=biaya)
        out = {"pasar": "gold", "coin": coin, "teknikal": tek, "fundamental": fundamental.gold(data.hl_konteks(coin, g["dex"] if coin == g["coin"] else ""),
                                                                                            tek["setup"]["arah"] if tek["setup"] else None)}
        likuid, pasar, tahan = 0, "gold", g["tahan_maks_jam"]
    else:
        pairs = [p for p in data.ds_pairs(c["meme"]["chain"], [arg]) if (p.get("baseToken") or {}).get("address") == arg] or data.ds_pairs(c["meme"]["chain"], [arg])
        if not pairs:
            sys.exit("[lihat] token tidak ditemukan di DexScreener (cek alamat kontraknya)")
        p = max(pairs, key=lambda x: float((x.get("liquidity") or {}).get("usd") or 0))
        aman = keamanan.periksa(p, c)
        likuid = float((p.get("liquidity") or {}).get("usd") or 0)
        biaya = risiko.biaya_pp(c, "meme", c["modal_usd"] * c["maks_porsi_modal"], likuid)
        b5 = data.gt_candle(c["meme"]["chain"], p["pairAddress"], "minute", 5, 300)
        b1h = data.gt_candle(c["meme"]["chain"], p["pairAddress"], "hour", 1, 72)
        tek = teknikal.analisa(b5, b1h, c["min_rr"], biaya_pct=biaya)
        out = {"pasar": "meme", "simbol": p["baseToken"].get("symbol"), "nama": p["baseToken"].get("name"), "alamat": arg, "pool": p.get("pairAddress"),
               "url": p.get("url"), "keamanan": aman, "teknikal": tek, "fundamental": fundamental.meme(p, aman)}
        pasar, tahan = "meme", c["meme"]["tahan_maks_jam"]
    if tek["setup"]:
        mc = simulasi.mesin_waktu(b5, tek["setup"], biaya, int(tahan * 12))
        out["simulasi"] = mc
        out["risiko"] = risiko.ukur(tek["setup"], mc, c, pasar, likuid, jurnal.hari_ini(j, c["mode"]), jurnal.token_terbuka(j, c["mode"]),
                                    out.get("alamat") or out.get("coin"))
    out["biaya_pp_pct"] = round(biaya, 2)
    out["mode"] = c["mode"]
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

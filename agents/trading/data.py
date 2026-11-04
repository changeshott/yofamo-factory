"""Sumber data Ruang Trading — semuanya gratis, tanpa API key, hanya MEMBACA data publik.

- DexScreener  : harga, likuiditas, volume, txns, umur pair, sosial (60–300 permintaan/menit)
- GeckoTerminal: pool trending/baru + candle OHLCV (±30 permintaan/menit → diberi jeda)
- RugCheck     : laporan keamanan token Solana (mint/freeze authority, holder, LP terkunci, risiko)
- Hyperliquid  : candle & konteks pasar gold perpetual (xyz:GOLD, cadangan PAXG)

Mode uji (YOFAMO_TRADING_UJI=1 atau --uji): baca contoh di agents/trading/contoh/ (tanpa internet).
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRADING = ROOT / "trading"
CACHE = TRADING / "cache"
CONTOH = Path(__file__).with_name("contoh")
UA = "YofamoTrading/1.0 (+analisa pribadi, hanya membaca)"
_TERAKHIR: dict[str, float] = {}
JEDA = {"api.geckoterminal.com": 2.1, "api.rugcheck.xyz": 0.6, "api.dexscreener.com": 0.25, "api.hyperliquid.xyz": 0.2}


def uji() -> bool:
    return os.environ.get("YOFAMO_TRADING_UJI") == "1"


class DataGagal(Exception):
    pass


def _jeda(host: str) -> None:
    j = JEDA.get(host, 0.3)
    t = time.time() - _TERAKHIR.get(host, 0)
    if t < j:
        time.sleep(j - t)
    _TERAKHIR[host] = time.time()


def _contoh(kunci: str):
    """Mode uji: contoh/<kunci>.json(.gz). Kunci = nama ringkas permintaan."""
    for f in (CONTOH / f"{kunci}.json", CONTOH / f"{kunci}.json.gz"):
        if f.exists():
            raw = gzip.decompress(f.read_bytes()) if f.suffix == ".gz" else f.read_bytes()
            return json.loads(raw.decode("utf-8"))
    raise DataGagal(f"contoh uji tidak ada: {kunci}")


def ambil(url: str, ttl: float = 30, data: dict | None = None, kunci_uji: str | None = None, headers: dict | None = None):
    """GET/POST JSON dengan cache disk singkat & jeda per host. Gagal → DataGagal (pemanggil memutuskan)."""
    if uji():
        return _contoh(kunci_uji or hashlib.md5(url.encode()).hexdigest()[:10])
    CACHE.mkdir(parents=True, exist_ok=True)
    kunci = hashlib.md5((url + json.dumps(data or {}, sort_keys=True)).encode()).hexdigest()
    cf = CACHE / f"{kunci}.json"
    if ttl > 0 and cf.exists() and time.time() - cf.stat().st_mtime < ttl:
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except ValueError:
            pass
    host = url.split("/")[2]
    body = json.dumps(data).encode() if data is not None else None
    h = {"User-Agent": UA, "Accept": "application/json", **(headers or {})}
    if body is not None:
        h["Content-Type"] = "application/json"
    for coba in range(3):
        _jeda(host)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=h), timeout=25) as r:
                hasil = json.loads(r.read().decode("utf-8"))
            cf.write_text(json.dumps(hasil), encoding="utf-8")
            return hasil
        except urllib.error.HTTPError as err:
            if err.code == 429 and coba < 2:
                time.sleep(6 * (coba + 1))
                continue
            if err.code == 404:
                raise DataGagal(f"{host}: tidak ditemukan") from err
            raise DataGagal(f"{host}: HTTP {err.code}") from err
        except (urllib.error.URLError, TimeoutError, ValueError) as err:
            if coba < 2:
                time.sleep(2)
                continue
            raise DataGagal(f"{host}: {err}") from err
    raise DataGagal(f"{host}: gagal")


# ------------------------------------------------------------------ DexScreener
def ds_pairs(chain: str, alamat: list[str]) -> list[dict]:
    """Pair untuk banyak token sekaligus (maks 30 per permintaan)."""
    out: list[dict] = []
    for i in range(0, len(alamat), 30):
        part = alamat[i:i + 30]
        out += ambil(f"https://api.dexscreener.com/tokens/v1/{chain}/{','.join(part)}", ttl=20,
                     kunci_uji=f"ds_pairs_{chain}") or []
        if uji():
            break
    return out


def ds_boosts() -> list[dict]:
    return ambil("https://api.dexscreener.com/token-boosts/top/v1", ttl=120, kunci_uji="ds_boosts") or []


def ds_profil() -> list[dict]:
    return ambil("https://api.dexscreener.com/token-profiles/latest/v1", ttl=120, kunci_uji="ds_profil") or []


def ds_cari(q: str) -> list[dict]:
    return (ambil(f"https://api.dexscreener.com/latest/dex/search?q={urllib.request.quote(q)}", ttl=30, kunci_uji="ds_cari") or {}).get("pairs") or []


# ------------------------------------------------------------------ GeckoTerminal
GT = {"Accept": "application/json;version=20230302"}


def gt_trending(network: str, page: int = 1) -> list[dict]:
    d = ambil(f"https://api.geckoterminal.com/api/v2/networks/{network}/trending_pools?page={page}&duration=1h", ttl=90,
              kunci_uji=f"gt_trending_{network}", headers=GT)
    return d.get("data") or []


def gt_baru(network: str) -> list[dict]:
    d = ambil(f"https://api.geckoterminal.com/api/v2/networks/{network}/new_pools?page=1", ttl=90, kunci_uji=f"gt_baru_{network}", headers=GT)
    return d.get("data") or []


def gt_candle(network: str, pool: str, tf: str = "minute", agg: int = 5, limit: int = 300) -> list[dict]:
    """Candle lama → baru: [{t,o,h,l,c,v}]. tf: minute (1,5,15) | hour (1,4,12) | day."""
    d = ambil(f"https://api.geckoterminal.com/api/v2/networks/{network}/pools/{pool}/ohlcv/{tf}?aggregate={agg}&limit={limit}&currency=usd",
              ttl=45, kunci_uji=f"gt_candle_{pool[:8]}_{tf}{agg}", headers=GT)
    rows = (((d or {}).get("data") or {}).get("attributes") or {}).get("ohlcv_list") or []
    bars = [{"t": int(r[0]), "o": float(r[1]), "h": float(r[2]), "l": float(r[3]), "c": float(r[4]), "v": float(r[5])} for r in rows if len(r) >= 6]
    return sorted(bars, key=lambda b: b["t"])


# ------------------------------------------------------------------ RugCheck
def rc_ringkas(mint: str) -> dict:
    return ambil(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary", ttl=600, kunci_uji=f"rc_{mint[:8]}") or {}


def rc_lengkap(mint: str) -> dict:
    try:
        return ambil(f"https://api.rugcheck.xyz/v1/tokens/{mint}/report", ttl=600, kunci_uji=f"rcfull_{mint[:8]}") or {}
    except DataGagal:
        return {}


# ------------------------------------------------------------------ Hyperliquid (gold)
HL = "https://api.hyperliquid.xyz/info"
INTERVAL_MS = {"5m": 300_000, "15m": 900_000, "1h": 3_600_000, "4h": 14_400_000}


def hl_candle(coin: str, interval: str = "5m", n: int = 400) -> list[dict]:
    akhir = int(time.time() * 1000)
    awal = akhir - INTERVAL_MS[interval] * n
    rows = ambil(HL, ttl=30, data={"type": "candleSnapshot", "req": {"coin": coin, "interval": interval, "startTime": awal, "endTime": akhir}},
                 kunci_uji=f"hl_{coin.replace(':', '_')}_{interval}") or []
    return [{"t": int(r["t"]) // 1000, "o": float(r["o"]), "h": float(r["h"]), "l": float(r["l"]), "c": float(r["c"]), "v": float(r.get("v", 0))} for r in rows]


def hl_konteks(coin: str, dex: str = "") -> dict:
    """funding per jam, open interest, harga mark & oracle, volume 24 jam."""
    try:
        meta, ctxs = ambil(HL, ttl=30, data={"type": "metaAndAssetCtxs", **({"dex": dex} if dex else {})}, kunci_uji=f"hlctx_{dex or 'utama'}")
    except (DataGagal, ValueError, TypeError):
        return {}
    for a, c in zip(meta.get("universe", []), ctxs):
        if a.get("name") == coin:
            return {"funding": float(c.get("funding") or 0), "oi": float(c.get("openInterest") or 0), "mark": float(c.get("markPx") or 0),
                    "oracle": float(c.get("oraclePx") or 0), "vol24": float(c.get("dayNtlVlm") or 0), "leverage_maks": a.get("maxLeverage")}
    return {}

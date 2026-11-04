#!/usr/bin/env python3
"""Meja Ruang Trading — menjalankan tim analisa dari awal sampai sinyal. Tidak pernah mengirim order.

    python agents/trading/meja.py pindai [--pasar meme|gold|semua]   # Arga → Sinta → Dimas → Nadia → Bagas → sinyal
    python agents/trading/meja.py pantau                             # Yudi: perbarui posisi, tutup latihan, peringatan nyata
    python agents/trading/meja.py loop                               # pindai tiap pantau_menit + pantau tiap menit (Studio: "Pantau otomatis")
    python agents/trading/meja.py beli <sinyal_id> --harga X --usd Y # catat pembelian NYATA yang Zona lakukan di FOMO
    python agents/trading/meja.py jual <posisi_id> --harga X         # catat penjualan NYATA (atau tutup manual)
    python agents/trading/meja.py lewati <sinyal_id>                 # Zona tidak mengambil sinyal ini
    python agents/trading/meja.py status                             # ringkasan + statistik
    ... --uji                                                        # data contoh, tanpa internet (folder trading-uji/)

Hasil: trading/papan.json (pindaian terakhir), trading/sinyal/<id>.json, trading/jurnal.json, trading/status.json (kantor).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
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
ROOT = data.ROOT
CFG = ROOT / "bible" / "trading.json"


def log(siapa: str, msg: str) -> None:
    print(f"[{siapa}] {msg}", flush=True)


def cfg() -> dict:
    return json.loads(CFG.read_text(encoding="utf-8"))


def tulis(f: Path, d) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(f)


def tahap(kunci: str | None) -> None:
    """Untuk animasi kantor: siapa yang sedang bekerja."""
    tulis(data.TRADING / "status.json", {"tahap": kunci, "pid": os.getpid(), "waktu": jurnal.sekarang()})


# ================================================================== memecoin
def kandidat_meme(c: dict) -> list[dict]:
    """Arga: kumpulkan token dari pool trending GeckoTerminal + profil/boost DexScreener, lalu saring angka dasar."""
    m, chain = c["meme"], c["meme"]["chain"]
    mints: dict[str, str] = {}
    for page in (1, 2):
        try:
            for p in data.gt_trending(chain, page):
                base = (((p.get("relationships") or {}).get("base_token") or {}).get("data") or {}).get("id", "")
                if base.startswith(chain + "_"):
                    mints.setdefault(base.split("_", 1)[1], "trending")
        except data.DataGagal as err:
            log("arga", f"GeckoTerminal trending gagal: {err}")
        if data.uji():
            break
    for sumber, f in (("profil", data.ds_profil), ("boost", data.ds_boosts)):
        try:
            for t in f():
                if t.get("chainId") == chain and t.get("tokenAddress"):
                    mints.setdefault(t["tokenAddress"], sumber)
        except data.DataGagal as err:
            log("arga", f"DexScreener {sumber} gagal: {err}")
    log("arga", f"{len(mints)} token dikumpulkan (trending + profil + boost)")
    if not mints:
        return []
    try:
        pairs = data.ds_pairs(chain, list(mints)[:90])
    except data.DataGagal as err:
        log("arga", f"DexScreener pair gagal: {err}")
        return []
    terbaik: dict[str, dict] = {}
    for p in pairs:
        mint = (p.get("baseToken") or {}).get("address")
        if not mint or p.get("chainId") != chain:
            continue
        if (p.get("quoteToken") or {}).get("symbol") not in ("SOL", "WSOL", "USDC", "USDT"):
            continue
        if float((p.get("liquidity") or {}).get("usd") or 0) > float(((terbaik.get(mint) or {}).get("liquidity") or {}).get("usd") or -1):
            terbaik[mint] = p
    lolos, buang = [], 0
    now = time.time() * 1000
    for mint, p in terbaik.items():
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        mcap = float(p.get("marketCap") or p.get("fdv") or 0)
        vol1 = float((p.get("volume") or {}).get("h1") or 0)
        umur = (now - float(p.get("pairCreatedAt") or now)) / 3_600_000
        if liq < m["likuiditas_min_usd"] or vol1 < m["volume_1j_min_usd"] or not (m["mcap_min_usd"] <= mcap <= m["mcap_maks_usd"]) or umur < m["umur_min_jam"]:
            buang += 1
            continue
        tx = (p.get("txns") or {}).get("h1") or {}
        b, s = float(tx.get("buys") or 0), float(tx.get("sells") or 0)
        h1 = float((p.get("priceChange") or {}).get("h1") or 0)
        p["_peringkat"] = (vol1 / liq) * (b / (b + s) if b + s else 0.5) * (1 + max(-0.5, min(h1, 60)) / 100)
        p["_sumber"] = mints.get(mint)
        lolos.append(p)
    lolos.sort(key=lambda p: p["_peringkat"], reverse=True)
    log("arga", f"{len(lolos)} lolos saringan angka dasar ({buang} dibuang: sepi/tipis/terlalu baru/di luar rentang market cap)")
    return lolos[: m["kandidat_maks"]]


def pindai_meme(c: dict, j: dict) -> tuple[list[dict], list[dict], list[dict]]:
    sinyal, blok, pantau = [], [], []
    tahap("t_pindai")
    kand = kandidat_meme(c)
    for p in kand:
        sim_ = (p.get("baseToken") or {}).get("symbol", "?")
        mint = p["baseToken"]["address"]
        dasar = {"simbol": sim_, "token": mint, "pool": p.get("pairAddress"), "url": p.get("url")}
        tahap("t_aman")
        aman = keamanan.periksa(p, c)
        if not aman["lolos"]:
            log("sinta", f"{sim_}: BLOKIR — {aman['blokir'][0]}")
            blok.append({**dasar, "alasan": aman["blokir"]})
            continue
        log("sinta", f"{sim_}: lolos keamanan (skor {aman['skor']})")
        tahap("t_teknikal")
        try:
            b5 = data.gt_candle(c["meme"]["chain"], p["pairAddress"], "minute", 5, 300)
            b1h = data.gt_candle(c["meme"]["chain"], p["pairAddress"], "hour", 1, 72)
        except data.DataGagal as err:
            log("dimas", f"{sim_}: candle tidak bisa dibaca ({err})")
            continue
        liq = float((p.get("liquidity") or {}).get("usd") or 0)
        biaya0 = risiko.biaya_pp(c, "meme", c["modal_usd"] * c["maks_porsi_modal"], liq)
        tek = teknikal.analisa(b5, b1h, c["min_rr"], biaya_pct=biaya0)
        tahap("t_fundamental")
        fun = fundamental.meme(p, aman)
        if not tek["setup"]:
            log("dimas", f"{sim_}: belum ada setup — {(tek['catatan'] or ['-'])[0]}")
            pantau.append({**dasar, "skor_teknikal": tek["skor"], "skor_fundamental": fun["skor"], "skor_keamanan": aman["skor"],
                           "catatan": tek["catatan"][:3], "harga": tek["data"].get("harga"), "grafik": teknikal.grafik(b5)})
            continue
        s = sinyal_dari(c, j, "meme", dasar, p, b5, tek, fun, aman, c["meme"]["tahan_maks_jam"], liq)
        (sinyal if s["risiko"]["lolos"] else blok).append(s if s["risiko"]["lolos"] else {**dasar, "alasan": s["risiko"]["blokir"], "setup": s["setup"]["jenis"]})
    return sinyal, blok, pantau


# ================================================================== gold
def pindai_gold(c: dict, j: dict) -> tuple[list[dict], list[dict], list[dict]]:
    g = c["gold"]
    tahap("t_pindai")
    coin, ctx = g["coin"], {}
    try:
        b5, b1h = data.hl_candle(coin, "5m", 400), data.hl_candle(coin, "1h", 200)
        ctx = data.hl_konteks(coin, g.get("dex", ""))
    except data.DataGagal as err:
        b5, b1h = [], []
        log("arga", f"{coin}: {err}")
    if len(b5) < 60 and g.get("cadangan"):
        log("arga", f"{coin} tidak tersedia → memakai {g['cadangan']} (token emas di Hyperliquid)")
        coin = g["cadangan"]
        try:
            b5, b1h = data.hl_candle(coin, "5m", 400), data.hl_candle(coin, "1h", 200)
            ctx = data.hl_konteks(coin)
        except data.DataGagal as err:
            log("arga", f"{coin}: {err}")
            return [], [{"simbol": "GOLD", "token": coin, "alasan": [f"data Hyperliquid tidak bisa dibaca: {err}"]}], []
    dasar = {"simbol": "GOLD", "token": coin, "coin": coin, "pool": None, "url": "https://app.hyperliquid.xyz/trade"}
    tahap("t_teknikal")
    tek = teknikal.analisa(b5, b1h, c["min_rr"], dua_arah=True, biaya_pct=risiko.biaya_pp(c, "gold", 10, 0))
    tahap("t_fundamental")
    fun = fundamental.gold(ctx, tek["setup"]["arah"] if tek["setup"] else None)
    if not tek["setup"]:
        log("dimas", f"GOLD: belum ada setup — {(tek['catatan'] or ['-'])[0]}")
        return [], [], [{**dasar, "skor_teknikal": tek["skor"], "skor_fundamental": fun["skor"], "skor_keamanan": None,
                         "catatan": tek["catatan"][:3], "harga": tek["data"].get("harga"), "grafik": teknikal.grafik(b5)}]
    aman = {"lolos": True, "skor": 90, "blokir": [], "peringatan": ["perpetual memakai leverage: rugi bisa melebihi rencana kalau harga melompat"], "rincian": {}}
    s = sinyal_dari(c, j, "gold", dasar, None, b5, tek, fun, aman, g["tahan_maks_jam"], 0)
    return ([s], [], []) if s["risiko"]["lolos"] else ([], [{**dasar, "alasan": s["risiko"]["blokir"], "setup": s["setup"]["jenis"]}], [])


# ================================================================== sinyal
def sinyal_dari(c, j, pasar, dasar, pair, b5, tek, fun, aman, tahan_jam, likuiditas) -> dict:
    setup = tek["setup"]
    tahap("t_simulasi")
    biaya0 = risiko.biaya_pp(c, pasar, c["modal_usd"] * c["maks_porsi_modal"], likuiditas)
    maks_bar = int(tahan_jam * 12)
    mc = simulasi.mesin_waktu(b5, setup, biaya0, maks_bar)
    rw = simulasi.riwayat(b5, lambda bs: teknikal.analisa(bs, [], c["min_rr"], dua_arah=setup["arah"] == "jual", biaya_pct=biaya0)["setup"], biaya0, maks_bar,
                          mulai=max(60, len(b5) - 220))
    hari = jurnal.hari_ini(j, c["mode"])
    rk = risiko.ukur(setup, mc, c, pasar, likuiditas, hari, jurnal.token_terbuka(j, c["mode"]), dasar["token"])
    peluang = mc.get("target_dulu_dari_selesai_pct", 0) if mc.get("cukup") else 0
    yakin = round(0.35 * tek["skor"] + 0.25 * fun["skor"] + 0.2 * aman["skor"] + 0.2 * min(100, peluang * 1.6))
    sid = f"{pasar}-{''.join(ch for ch in dasar['simbol'].lower() if ch.isalnum())[:12] or 'x'}-{datetime.now().strftime('%Y%m%d%H%M')}"
    nama = "Dimas" if pasar == "meme" else "Dimas (gold)"
    log("bagas", f"{dasar['simbol']} {setup['jenis']} {setup['arah']}: peluang target-dulu {peluang}% · EV {mc.get('ev_R', 0):+.2f}R · "
                 f"{'LOLOS' if rk['lolos'] else 'BLOKIR: ' + rk['blokir'][0]}")
    return {"id": sid, "pasar": pasar, **dasar, "dibuat": jurnal.sekarang(), "status": "baru", "setup": setup, "teknikal": tek,
            "fundamental": fun, "keamanan": aman, "simulasi": mc, "riwayat": rw, "risiko": rk, "keyakinan": yakin,
            "tahan_maks_jam": tahan_jam, "grafik": teknikal.grafik(b5), "oleh": nama}


def pindai(pasar: str) -> dict:
    c = cfg()
    j = jurnal.baca()
    t0 = time.time()
    hasil_s, hasil_b, hasil_p = [], [], []
    for ps in (["meme", "gold"] if pasar == "semua" else [pasar]):
        log("meja", f"pindai {ps} (mode {c['mode']})…")
        s, b, p = (pindai_meme if ps == "meme" else pindai_gold)(c, j)
        hasil_s += s
        hasil_b += b
        hasil_p += p
    tahap("t_jurnal")
    sdir = data.TRADING / "sinyal"
    baru = []
    for s in hasil_s:
        sudah = [f for f in sdir.glob(f"{s['pasar']}-*.json")] if sdir.is_dir() else []
        dobel = False
        for f in sudah:
            try:
                x = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if x.get("token") == s["token"] and time.time() - f.stat().st_mtime < 3600:
                dobel = True
        if dobel:
            log("meja", f"{s['simbol']}: sinyal serupa sudah ada < 1 jam lalu, dilewati")
            continue
        if c["mode"] == "latihan":
            pos = jurnal.buka(s, "latihan")
            s["status"] = "latihan"
            s["posisi"] = pos["id"]
            log("yudi", f"[latihan] {s['simbol']} dibuka di {pos['masuk']:.6g} (${pos['posisi_usd']})")
        tulis(sdir / f"{s['id']}.json", s)
        baru.append(s)
    papan = {"waktu": jurnal.sekarang(), "pasar": pasar, "mode": c["mode"], "detik": round(time.time() - t0),
             "sinyal": [s["id"] for s in baru], "diblokir": hasil_b[:30], "dipantau": sorted(hasil_p, key=lambda x: -x["skor_teknikal"])[:8]}
    tulis(data.TRADING / "papan.json", papan)
    tahap(None)
    log("meja", f"selesai {papan['detik']} dtk: {len(baru)} sinyal baru, {len(hasil_b)} diblokir, {len(hasil_p)} dipantau (belum ada setup)")
    return papan


def baca_sinyal(sid: str) -> tuple[Path, dict]:
    f = data.TRADING / "sinyal" / f"{sid}.json"
    if not f.exists():
        sys.exit(f"[meja] sinyal {sid} tidak ditemukan")
    return f, json.loads(f.read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Meja Ruang Trading (analisa saja, tidak pernah mengirim order)")
    ap.add_argument("perintah", choices=["pindai", "pantau", "loop", "beli", "jual", "lewati", "status"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--pasar", default="meme", choices=["meme", "gold", "semua"])
    ap.add_argument("--harga", type=float)
    ap.add_argument("--usd", type=float)
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    data.TRADING.mkdir(parents=True, exist_ok=True)
    if a.perintah == "pindai":
        from kunci import Kunci
        k = Kunci(data.TRADING / "pindai.lock", maks_jam=1)
        if not k.ambil("pindai"):
            sys.exit("[meja] pindaian lain sedang berjalan")
        try:
            pindai(a.pasar)
        finally:
            tahap(None)
            k.lepas()
    elif a.perintah == "pantau":
        for p in jurnal.pantau():
            log("yudi", p)
    elif a.perintah == "loop":
        from kunci import Kunci
        k = Kunci(data.TRADING / "loop.lock", maks_jam=24)
        if not k.ambil("loop"):
            sys.exit("[meja] pantau otomatis sudah berjalan")
        henti = data.TRADING / "berhenti"
        henti.unlink(missing_ok=True)
        log("meja", "pantau otomatis menyala (hapus dengan tombol Berhenti di Studio)")
        terakhir = 0.0
        try:
            while not henti.exists():
                c = cfg()
                if time.time() - terakhir >= c["pantau_menit"] * 60:
                    try:
                        pindai("semua")
                    except Exception as err:  # satu putaran gagal tidak mematikan loop
                        log("meja", f"pindai gagal: {err}")
                    terakhir = time.time()
                for p in jurnal.pantau():
                    log("yudi", p)
                for _ in range(60):
                    if henti.exists():
                        break
                    time.sleep(1)
        finally:
            henti.unlink(missing_ok=True)
            tahap(None)
            k.lepas()
            log("meja", "pantau otomatis berhenti")
    elif a.perintah == "beli":
        f, s = baca_sinyal(a.id or "")
        pos = jurnal.buka(s, "nyata", a.harga, a.usd)
        s["status"], s["posisi_nyata"] = "dibeli", pos["id"]
        tulis(f, s)
        log("yudi", f"[NYATA] {s['simbol']} dicatat: beli {pos['masuk']:.6g}, ${pos['posisi_usd']}, stop {pos['stop']:.6g}, target {pos['target']:.6g}")
    elif a.perintah == "jual":
        if a.harga is None:
            sys.exit("[meja] sebutkan --harga jual")
        p = jurnal.tutup(a.id or "", a.harga, "manual")
        log("yudi", f"{p['simbol']} ditutup: {p['pnl_usd']:+.2f} USD ({p['R']:+.2f}R) setelah biaya")
    elif a.perintah == "lewati":
        f, s = baca_sinyal(a.id or "")
        s["status"] = "dilewati"
        tulis(f, s)
    else:
        print(json.dumps({"statistik": jurnal.statistik(), "papan": json.loads((data.TRADING / "papan.json").read_text(encoding="utf-8"))
                          if (data.TRADING / "papan.json").exists() else None}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

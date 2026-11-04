"""Bagas — manajer risiko & ukuran posisi (metode trader-budget + trader-risk dari day-trader-skill, untuk modal kecil
di FOMO). Stop menentukan ukuran: makin jauh stop, makin kecil posisi. Biaya & slippage dihitung jujur. Hasilnya LOLOS
atau BLOKIR dengan alasan — BLOKIR final, sinyal tidak dikirim ke Zona.
"""
from __future__ import annotations


def biaya_pp(cfg: dict, pasar: str, posisi_usd: float, likuiditas_usd: float) -> float:
    """Biaya pulang-pergi (beli + jual) dalam % harga: biaya aplikasi + slippage kedua sisi."""
    if pasar == "gold":
        return 2 * (cfg.get("biaya_gold_per_sisi_pct", 0.1) + 0.02)
    slip = max(cfg["slippage_min_pct"], (posisi_usd / likuiditas_usd * 100 * 2) if likuiditas_usd else 5.0)
    return 2 * (cfg["biaya_fomo_per_sisi_pct"] + slip)


def ukur(setup: dict, sim: dict, cfg: dict, pasar: str, likuiditas_usd: float, hari: dict, terbuka: list[str], token: str) -> dict:
    """hari: {rugi_usd, trade} untuk mode aktif hari ini (WIB). terbuka: token yang posisinya masih terbuka."""
    blokir: list[str] = []
    masuk, stop, target = setup["masuk"], setup["stop"], setup["target"]
    risiko_pct = abs(masuk - stop) / masuk * 100
    target_pct = abs(target - masuk) / masuk * 100
    sisa_harian = cfg["batas_rugi_harian_usd"] - hari.get("rugi_usd", 0)
    risk_usd = min(cfg["risiko_per_trade_usd"], max(0.0, sisa_harian))
    batas_posisi = cfg["modal_usd"] * cfg["maks_porsi_modal"]
    # ukuran posisi (iterasi kecil karena slippage tergantung ukuran)
    posisi, biaya = 0.0, biaya_pp(cfg, pasar, 1.0, likuiditas_usd)
    for _ in range(3):
        posisi = risk_usd / ((risiko_pct + biaya) / 100) if risiko_pct + biaya > 0 else 0
        hasil_lev = None
        if pasar == "gold":
            lev_maks = cfg["gold"]["leverage_maks"]
            margin = min(batas_posisi, posisi)
            if posisi > margin * lev_maks:
                posisi = margin * lev_maks
            hasil_lev = posisi / margin if margin else 0
        else:
            posisi = min(posisi, batas_posisi)
        biaya = biaya_pp(cfg, pasar, posisi, likuiditas_usd)
    rugi_stop = posisi * (risiko_pct + biaya) / 100
    untung_target = posisi * (target_pct - biaya) / 100
    out = {"posisi_usd": round(posisi, 2), "rugi_di_stop_usd": round(rugi_stop, 2), "untung_di_target_usd": round(untung_target, 2),
           "biaya_pp_pct": round(biaya, 2), "risiko_pct": round(risiko_pct, 2), "target_pct": round(target_pct, 2)}
    if pasar == "gold":
        lev = hasil_lev or 1
        margin = posisi / lev if lev else posisi
        jarak_lik = 0.9 / lev * 100       # perkiraan kasar jarak likuidasi (%), sudah memberi ruang margin pemeliharaan
        out.update({"leverage": round(lev, 1), "margin_usd": round(margin, 2), "likuidasi_kira": round(masuk * (1 - jarak_lik / 100) if setup.get("arah") == "beli" else masuk * (1 + jarak_lik / 100), 2)})
        if jarak_lik <= risiko_pct * 1.2:
            blokir.append(f"likuidasi (±{jarak_lik:.1f}%) terlalu dekat dengan stop ({risiko_pct:.1f}%)")
    # aturan
    if risk_usd <= 0:
        blokir.append(f"batas rugi harian ${cfg['batas_rugi_harian_usd']} sudah tercapai — berhenti hari ini")
    if hari.get("trade", 0) >= cfg["maks_trade_harian"]:
        blokir.append(f"sudah {hari['trade']} trade hari ini (maks {cfg['maks_trade_harian']})")
    if token in terbuka:
        blokir.append("posisi token ini masih terbuka")
    if posisi < 1:
        blokir.append(f"posisi ${posisi:.2f} terlalu kecil (stop terlalu jauh untuk risiko ${risk_usd:.2f})")
    rr_bersih = (target_pct - biaya) / (risiko_pct + biaya) if risiko_pct + biaya else 0
    out["rr_bersih"] = round(rr_bersih, 2)
    if rr_bersih < cfg["min_rr"] * 0.75:
        blokir.append(f"reward:risk setelah biaya {rr_bersih:.2f} (minimal {cfg['min_rr'] * 0.75:.1f})")
    if biaya >= risiko_pct * 0.6:
        blokir.append(f"biaya {biaya:.1f}% hampir sebesar jarak stop {risiko_pct:.1f}% — tidak layak")
    if sim.get("cukup"):
        if sim["ev_R"] < cfg["min_ev_r"]:
            blokir.append(f"nilai harapan setelah biaya {sim['ev_R']:+.2f}R (minimal +{cfg['min_ev_r']}R)")
        if sim["target_dulu_dari_selesai_pct"] < cfg["min_peluang_target_pct"]:
            blokir.append(f"peluang target-dulu {sim['target_dulu_dari_selesai_pct']}% (minimal {cfg['min_peluang_target_pct']}%)")
    else:
        blokir.append("simulasi tidak bisa dijalankan (data kurang)")
    out.update({"lolos": not blokir, "blokir": blokir})
    return out

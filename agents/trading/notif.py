"""Notifikasi ke HP lewat ntfy.sh (gratis, tanpa akun): pasang aplikasi "ntfy" di HP → Subscribe ke topik yang dibuat Studio.
Dikirim saat: sinyal baru (mode nyata), posisi nyata menyentuh stop/target/batas waktu, batas rugi atau target harian tercapai.
Topik disimpan di bible/trading.json → notifikasi.ntfy_topik (kosong = mati). Isi pesan hanya data pasar, tanpa data akun.

    python agents/trading/notif.py tes        # kirim pesan uji
"""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

import data

CFG = data.ROOT / "bible" / "trading.json"


def topik() -> str:
    try:
        return str((json.loads(CFG.read_text(encoding="utf-8")).get("notifikasi") or {}).get("ntfy_topik") or "").strip()
    except (OSError, ValueError):
        return ""


def kirim(judul: str, isi: str, prioritas: int = 3, tag: str = "", klik: str = "") -> bool:
    t = topik()
    if not t or data.uji():
        if data.uji():
            print(f"[notif-uji] {judul} | {isi[:80]}", flush=True)
        return False
    body = {"topic": t, "title": judul[:120], "message": isi[:3500], "priority": max(1, min(5, prioritas))}
    if tag:
        body["tags"] = [tag]
    if klik:
        body["click"] = klik
    try:
        req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode("utf-8"),
                                     headers={"Content-Type": "application/json", "User-Agent": data.UA})
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status == 200
    except Exception as err:  # notifikasi gagal tidak boleh menghentikan pemantauan
        print(f"[notif] gagal mengirim: {err}", flush=True)
        return False


def sinyal(s: dict) -> None:
    st, r = s["setup"], s["risiko"]
    beli = st["arah"] == "beli"
    isi = (f"{'BELI' if beli else 'JUAL'} {s['simbol']} ({s['setup']['jenis']}) — ${r['posisi_usd']}\n"
           f"Masuk {st['masuk']:.6g} · Stop {st['stop']:.6g} · Target {st['target']:.6g}\n"
           f"Rugi maks ${r['rugi_di_stop_usd']} · untung di target ${r['untung_di_target_usd']} (setelah biaya)\n"
           f"Peluang target duluan {s['simulasi'].get('target_dulu_dari_selesai_pct')}% (impas {s['simulasi'].get('impas_pct')}%)\n")
    if s["pasar"] == "meme":
        isi += f"Alamat kontrak (cari di FOMO pakai ini):\n{s['token']}"
    else:
        isi += "Gold perpetual — cek ketersediaan & leverage di aplikasi."
    kirim(f"Sinyal {s['simbol']}: {'beli' if beli else 'jual'} ${r['posisi_usd']}", isi, 4, "chart_with_upwards_trend" if beli else "chart_with_downwards_trend", s.get("url") or "")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "tes":
        ok = kirim("Tes Ruang Trading", "Notifikasi Yofamo sudah tersambung. Sinyal & peringatan stop/target akan muncul di sini.", 3, "white_check_mark")
        print("[notif] terkirim" if ok else "[notif] belum terkirim (topik kosong atau tidak ada internet)")
        sys.exit(0 if ok else 1)

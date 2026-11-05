#!/usr/bin/env python3
"""Notifikasi ke HP Zona lewat bot Telegram (gratis). Tidak wajib: tanpa pengaturan, semua kabar dilewati diam-diam.

    python agents/notif.py siapkan        # setelah Zona mengirim pesan apa saja ke bot: cari chat id → simpan ke .env
    python agents/notif.py tes            # kirim pesan uji
    python agents/notif.py kirim "teks"   # kirim pesan bebas

Pengaturan di .env (dibuat sekali, lihat SETUP.md → Notifikasi Telegram):
    TELEGRAM_BOT_TOKEN=...   (dari @BotFather → /newbot)
    TELEGRAM_CHAT_ID=...     (diisi otomatis oleh `siapkan`)
Dipakai autopilot Shorts & video panjang: video dijadwalkan tayang, video menunggu Zona, autopilot berhenti
(kuota Claude habis, login kedaluwarsa, internet mati, produksi gagal). Kabar yang sama tidak dikirim ulang
dalam jeda tertentu (produksi/notif.json) supaya HP tidak berisik.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
CATATAN = ROOT / "produksi" / "notif.json"
API = "https://api.telegram.org/bot{token}/{metode}"


def _env() -> dict:
    out = {}
    try:
        for line in ENV.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return {**out, **{k: v for k, v in os.environ.items() if k.startswith("TELEGRAM_")}}


def siap() -> bool:
    e = _env()
    return bool(e.get("TELEGRAM_BOT_TOKEN") and e.get("TELEGRAM_CHAT_ID"))


def _panggil(metode: str, data: dict | None = None, timeout: int = 15) -> dict:
    token = _env().get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi di .env")
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(API.format(token=token, metode=metode), data=body)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def kirim(teks: str, kunci: str | None = None, jeda_jam: float = 6.0) -> bool:
    """Kirim kabar. `kunci`: kabar dengan kunci sama tidak dikirim ulang dalam `jeda_jam`. Tidak pernah melempar error."""
    if UJI_SENYAP or not siap():
        return False
    catatan = {}
    try:
        catatan = json.loads(CATATAN.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        pass
    if kunci and time.time() - float(catatan.get(kunci, 0)) < jeda_jam * 3600:
        return False
    try:
        r = _panggil("sendMessage", {"chat_id": _env()["TELEGRAM_CHAT_ID"], "text": teks[:3900], "disable_web_page_preview": "true"})
        if not r.get("ok"):
            return False
    except Exception as err:  # noqa: BLE001 — notifikasi tidak boleh menghentikan produksi/upload
        print(f"[notif] gagal mengirim ke Telegram: {str(err)[:120]}", flush=True)
        return False
    if kunci:
        catatan[kunci] = time.time()
        catatan = dict(sorted(catatan.items(), key=lambda kv: kv[1])[-200:])
        try:
            CATATAN.parent.mkdir(exist_ok=True)
            CATATAN.write_text(json.dumps(catatan), encoding="utf-8")
        except OSError:
            pass
    return True


UJI_SENYAP = os.environ.get("YOFAMO_NOTIF_MATI") == "1"      # tes pabrik: jangan kirim apa pun


def siapkan() -> None:
    """Cari chat id dari pesan terakhir yang Zona kirim ke bot, lalu tulis TELEGRAM_CHAT_ID ke .env (token tidak ditampilkan)."""
    if not _env().get("TELEGRAM_BOT_TOKEN"):
        sys.exit("[notif] Isi TELEGRAM_BOT_TOKEN di .env dulu (buat bot di Telegram: chat @BotFather → /newbot).")
    r = _panggil("getUpdates", {"timeout": "0"})
    chats = [u.get("message", {}).get("chat", {}) for u in r.get("result", []) if u.get("message")]
    if not chats:
        sys.exit("[notif] Belum ada pesan untuk bot. Buka bot-mu di Telegram, kirim pesan apa saja (mis. /start), lalu ulangi.")
    chat = chats[-1]
    baris = ENV.read_text(encoding="utf-8-sig").splitlines() if ENV.exists() else []
    baris = [b for b in baris if not b.strip().startswith("TELEGRAM_CHAT_ID")] + [f"TELEGRAM_CHAT_ID={chat['id']}"]
    ENV.write_text("\n".join(baris) + "\n", encoding="utf-8")
    nama = chat.get("first_name") or chat.get("title") or "kamu"
    print(f"[notif] chat dengan {nama} tersimpan. Mengirim pesan uji…", flush=True)
    sys.exit(0 if kirim("✅ Yofamo terhubung. Kabar autopilot (video terjadwal, menunggu kamu, autopilot berhenti) akan dikirim ke sini.") else 1)


def main() -> None:
    p = sys.argv[1] if len(sys.argv) > 1 else ""
    for s_ in (sys.stdout, sys.stderr):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if p == "siapkan":
        siapkan()
    elif p == "tes":
        if not siap():
            sys.exit("[notif] Belum siap: isi TELEGRAM_BOT_TOKEN di .env lalu jalankan `python agents/notif.py siapkan`.")
        ok = kirim("🔔 Tes notifikasi Yofamo: berhasil. Autopilot akan mengabari kamu di sini.")
        print("[notif] terkirim" if ok else "[notif] gagal mengirim (cek token/internet)")
        sys.exit(0 if ok else 1)
    elif p == "kirim" and len(sys.argv) > 2:
        sys.exit(0 if kirim(" ".join(sys.argv[2:])) else 1)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

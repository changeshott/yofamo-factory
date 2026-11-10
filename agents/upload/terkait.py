#!/usr/bin/env python3
"""Uli — menghubungkan video supaya penonton lanjut menonton (alur views, Nov 2026):

  versi_panjang(idea)        Short ini punya video PANJANG tentang produk yang sama (sudah diupload)? → dipakai penutup video
                             ("Versi lengkapnya ada di channel ini") dan deskripsi. 95,7% penonton datang dari Shorts;
                             jam tonton untuk monetisasi hanya dihitung dari video panjang.
  masuk_playlist(yt, c, vid, kategori)   video baru dimasukkan ke playlist kategorinya (dibuat kalau belum ada) supaya
                             YouTube memutar video kita berikutnya. Butuh izin youtube.force-ssl (izin yang sama dengan subtitle,
                             diminta saat Hubungkan YouTube); tanpa izin itu dilewati diam-diam. Hanya MENAMBAH video yang baru
                             diupload ke playlist — tidak mengubah atau menghapus video mana pun.

    python agents/upload/terkait.py <slug>      # lihat versi panjang & playlist yang akan dipakai (tanpa memanggil YouTube)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
UMUM = {"the", "and", "for", "with", "pro", "max", "plus", "mini", "ultra", "new", "smart", "robot", "phone", "edition", "gen", "series"}
NAMA_PLAYLIST = {"hp": "Gadget & HP Canggih", "robot": "Robot Canggih", "kesehatan": "Teknologi Kesehatan", "transportasi": "Kendaraan Masa Depan",
                 "game": "Teknologi Game & VR", "rumah": "Rumah Pintar", "pakaian": "Teknologi yang Bisa Dipakai", "makanan": "Makanan Masa Depan",
                 "energi": "Energi Masa Depan", "luar-angkasa": "Teknologi Antariksa",
                 "panjang": "Bedah Teknologi (Video Lengkap)"}
CACHE_PL = ROOT / "produksi" / "playlist.json"


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def inti(nama: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", str(nama).lower()) if (len(w) >= 2 or w.isdigit()) and w not in UMUM}


def versi_panjang(idea: dict) -> dict | None:
    """Video panjang (sudah diupload, tidak dibatalkan) yang produknya sama dengan Short ini. Cocok = semua kata inti nama produk
    yang lebih pendek ada di nama satunya (mis. 'Oura Ring 5' ↔ 'Oura Ring 5 smart ring')."""
    a = inti(idea.get("produk") or "")
    if len(a) < 2:
        return None
    for up_f in sorted((ROOT / "panjang").glob("*/export/upload.json"), reverse=True):
        up, vdir = rj(up_f), up_f.parents[1]
        vid = up.get("manual_videoId") or (None if up.get("dibatalkan") else up.get("videoId"))
        if not vid or vid == "UJI":
            continue
        b = inti(rj(vdir / "ide.json").get("produk") or "")
        if len(b) >= 2 and (a <= b or b <= a):
            return {"slug": vdir.name, "videoId": vid, "judul": str(rj(vdir / "naskah.json").get("judul") or up.get("judul") or vdir.name)}
    return None


def nama_playlist(kategori: str, gaya: dict) -> str | None:
    pl = gaya.get("playlist") or {}
    if pl.get("aktif", True) is False:
        return None
    return str((pl.get("nama") or {}).get(kategori) or NAMA_PLAYLIST.get(kategori) or pl.get("lainnya") or "Teknologi Unik")[:120]


def masuk_playlist(yt, creds, vid: str, kategori: str, log=print) -> dict | None:
    """Tambahkan video ke playlist kategorinya. Kembalikan {id, nama} atau None (dimatikan / tanpa izin / gagal — tidak pernah
    menggagalkan upload). Biaya kuota: 50 unit (+50 sekali saat membuat playlist baru)."""
    gaya = rj(ROOT / "bible" / "gaya-upload.json")
    nama = nama_playlist(kategori, gaya)
    if not nama:
        return None
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        import unggah
        if not unggah.bisa_subtitle(creds):
            log("playlist dilewati: login YouTube belum memberi izin kelola (Hubungkan YouTube ulang & centang semua izin)")
            return None
        from googleapiclient.errors import HttpError
    except ImportError:
        return None
    cache = rj(CACHE_PL)
    try:
        pid = cache.get(nama)
        if not pid:
            res = yt.playlists().list(part="snippet", mine=True, maxResults=50).execute()
            pid = next((p["id"] for p in res.get("items", []) if p["snippet"]["title"].strip().lower() == nama.lower()), None)
            if not pid:
                pid = yt.playlists().insert(part="snippet,status", body={
                    "snippet": {"title": nama, "description": f"{nama} — kumpulan video Yofamo Technology.", "defaultLanguage": "id"},
                    "status": {"privacyStatus": "public"}}).execute()["id"]
                log(f"playlist baru dibuat: {nama}")
            cache[nama] = pid
            CACHE_PL.parent.mkdir(parents=True, exist_ok=True)
            CACHE_PL.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        yt.playlistItems().insert(part="snippet", body={"snippet": {"playlistId": pid, "resourceId": {"kind": "youtube#video", "videoId": vid}}}).execute()
        log(f"masuk playlist: {nama}")
        return {"id": pid, "nama": nama}
    except HttpError as err:
        if "playlistNotFound" in str(err) and cache.pop(nama, None):
            CACHE_PL.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
        log(f"playlist dilewati ({str(err)[:110]})")
    except Exception as err:  # noqa: BLE001 — playlist tidak boleh menggagalkan upload
        log(f"playlist dilewati ({type(err).__name__}: {str(err)[:90]})")
    return None


if __name__ == "__main__":
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    idea = rj(ROOT / "videos" / sys.argv[1] / "idea.json")
    print("versi panjang:", versi_panjang(idea))
    print("playlist:", nama_playlist(str(idea.get("kategori") or ""), rj(ROOT / "bible" / "gaya-upload.json")))

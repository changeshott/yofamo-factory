#!/usr/bin/env python3
"""Uli — agent upload Yofamo. Mengunggah video yang SUDAH disetujui Zona ke YouTube sebagai PRIVATE,
lengkap dengan judul, deskripsi, kredit, tag, kategori, dan label konten sintetis.

    python agents/upload/unggah.py login                # sekali: izinkan akses akun YouTube (membuka browser)
    python agents/upload/unggah.py cek                  # cek login & nama channel
    python agents/upload/unggah.py unggah <slug>        # upload private (status video harus 'export')
    python agents/upload/unggah.py unggah <slug> --jadwal 2026-11-01T19:00   # private + jadwal tayang (WIB)

Butuh file OAuth client (Desktop app) dari Google Cloud di rahasia/client_secret.json (lihat SETUP.md).
Token tersimpan di rahasia/token.json. Folder rahasia/ tidak pernah di-commit.
Catatan: project Google Cloud yang belum diaudit YouTube hanya bisa upload sebagai private.
Uli tidak pernah menghapus atau mengubah video lain di channel.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("googleapiclient", "google_auth_oauthlib")

RAHASIA = ROOT / "rahasia"
CLIENT = RAHASIA / "client_secret.json"
TOKEN = RAHASIA / "token.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/yt-analytics.readonly"]
VIDEOS = ROOT / "videos"
WIB = timezone(timedelta(hours=7))


def log(msg: str) -> None:
    print(f"[uli] {msg}", flush=True)


def creds(interaktif: bool = False):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        sys.exit("[uli] Paket Google belum terpasang. Jalankan: python -m pip install -r requirements.txt")
    c = Credentials.from_authorized_user_file(str(TOKEN), SCOPES) if TOKEN.exists() else None
    if c and c.valid:
        return c
    if c and c.expired and c.refresh_token:
        try:
            c.refresh(Request())
            TOKEN.write_text(c.to_json(), encoding="utf-8")
            return c
        except Exception as err:  # token dicabut / kedaluwarsa
            log(f"token tidak bisa diperbarui ({err}); perlu login ulang")
    if not interaktif:
        sys.exit("[uli] Belum login YouTube. Klik 'Hubungkan YouTube' di Studio (atau: python agents/upload/unggah.py login).")
    if not CLIENT.exists():
        sys.exit("[uli] rahasia/client_secret.json belum ada. Ikuti SETUP.md bagian 'Upload otomatis'.")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT), SCOPES)
    c = flow.run_local_server(port=0, open_browser=True, prompt="consent",
                              success_message="Yofamo terhubung ke YouTube. Jendela ini boleh ditutup.")
    RAHASIA.mkdir(exist_ok=True)
    TOKEN.write_text(c.to_json(), encoding="utf-8")
    return c


def youtube(c):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=c, cache_discovery=False)


def channel_name(yt) -> str:
    r = yt.channels().list(part="snippet", mine=True).execute()
    items = r.get("items") or []
    return items[0]["snippet"]["title"] if items else "(tidak ada channel)"


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def status_of(slug: str) -> str | None:
    r = subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "list", "--json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
    try:
        return next((v["status"] for v in json.loads(r.stdout or "[]") if v["slug"] == slug), None)
    except ValueError:
        return None


def metadata(slug: str) -> dict:
    vdir = VIDEOS / slug
    sc, man = rj(vdir / "script.json"), rj(vdir / "aset" / "manifest.json")
    kredit = (vdir / "aset" / "kredit_deskripsi.txt").read_text(encoding="utf-8").strip() if (vdir / "aset" / "kredit_deskripsi.txt").exists() else ""
    judul = re.sub(r"[<>]", "", sc.get("judul") or slug)[:100]
    desk = "\n\n".join(x for x in [sc.get("deskripsi", "").strip(), kredit] if x)
    desk = re.sub(r"[<>]", "", desk)[:4900]
    tags, n = [], 0
    for t in sc.get("tag", []):
        t = re.sub(r"[<>,]", "", str(t)).strip()
        if t and n + len(t) + 1 <= 480:
            tags.append(t)
            n += len(t) + 1
    return {"judul": judul, "deskripsi": desk, "tag": tags, "sintetis": bool(man.get("pakai_ai"))}


def unggah(slug: str, jadwal: str | None) -> None:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    vdir = VIDEOS / slug
    final = vdir / "export" / "final.mp4"
    if not final.exists():
        sys.exit("[uli] export/final.mp4 belum ada.")
    if rj(vdir / "export" / "info.json").get("uji"):
        sys.exit("[uli] Ini video mode uji (suara/visual palsu). Tidak diupload.")
    st = status_of(slug)
    if st != "export":
        sys.exit(f"[uli] Status video '{st}'. Hanya video yang sudah kamu setujui (Siap upload) yang boleh diupload.")
    up = vdir / "export" / "upload.json"
    if rj(up).get("videoId"):
        sys.exit(f"[uli] Video ini sudah diupload: {rj(up).get('url')}")
    m = metadata(slug)
    status = {"privacyStatus": "private", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": m["sintetis"], "embeddable": True}
    if jadwal:
        try:
            t = datetime.fromisoformat(jadwal)
        except ValueError:
            sys.exit("[uli] format jadwal: 2026-11-01T19:00")
        t = t.replace(tzinfo=WIB) if t.tzinfo is None else t
        if t < datetime.now(WIB) + timedelta(minutes=15):
            sys.exit("[uli] jadwal minimal 15 menit dari sekarang")
        status["publishAt"] = t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    body = {"snippet": {"title": m["judul"], "description": m["deskripsi"], "tags": m["tag"], "categoryId": "28",
                        "defaultLanguage": "id", "defaultAudioLanguage": "id"}, "status": status}
    yt = youtube(creds())
    log(f"mengunggah ke '{channel_name(yt)}': {m['judul']}")
    log(f"private{', tayang ' + jadwal + ' WIB' if jadwal else ''}; konten sintetis: {'ya' if m['sintetis'] else 'tidak'}")
    media = MediaFileUpload(str(final), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    resp = None
    try:
        while resp is None:
            prog, resp = req.next_chunk()
            if prog:
                log(f"{int(prog.progress() * 100)}%")
    except HttpError as err:
        reason = err.reason if hasattr(err, "reason") else str(err)
        if "quotaExceeded" in str(err):
            sys.exit("[uli] Kuota upload YouTube API hari ini habis (±6 upload/hari). Coba lagi besok.")
        sys.exit(f"[uli] YouTube menolak upload: {reason}")
    vid = resp["id"]
    info = {"videoId": vid, "url": f"https://youtube.com/shorts/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
            "waktu": datetime.now(WIB).isoformat(timespec="seconds"), "jadwal": jadwal, "privasi": "private", "judul": m["judul"],
            "sintetis": m["sintetis"]}
    up.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", slug, "export", "--note", f"diupload private: {vid}"], cwd=ROOT)
    log(f"selesai: {info['url']} (private). Cek di YouTube Studio, lalu tandai terbit di Studio Yofamo setelah tayang.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Uli: upload private ke YouTube")
    ap.add_argument("perintah", choices=["login", "cek", "unggah"])
    ap.add_argument("slug", nargs="?")
    ap.add_argument("--jadwal", help="waktu tayang WIB, misalnya 2026-11-01T19:00")
    a = ap.parse_args()
    if a.perintah == "login":
        yt = youtube(creds(interaktif=True))
        log(f"terhubung ke channel: {channel_name(yt)}")
    elif a.perintah == "cek":
        yt = youtube(creds())
        log(f"login OK, channel: {channel_name(yt)}")
    else:
        if not a.slug or not re.fullmatch(r"[a-z0-9-]{3,80}", a.slug):
            sys.exit("[uli] slug tidak valid")
        unggah(a.slug, a.jadwal)


if __name__ == "__main__":
    main()

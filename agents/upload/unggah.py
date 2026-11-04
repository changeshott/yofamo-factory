#!/usr/bin/env python3
"""Uli — agent upload Yofamo. Mengunggah video yang SUDAH disetujui Zona ke YouTube sebagai PRIVATE,
lengkap dengan judul, deskripsi, kredit, tag, kategori, dan label konten sintetis.

    python agents/upload/unggah.py login                # sekali: izinkan akses akun YouTube (membuka browser)
    python agents/upload/unggah.py cek                  # cek login & nama channel
    python agents/upload/unggah.py unggah <slug>        # upload private (status video harus 'export')
    python agents/upload/unggah.py unggah <slug> --jadwal 2026-11-01T19:00   # private + jadwal tayang (WIB)
    python agents/upload/unggah.py pratinjau <slug>     # lihat judul, deskripsi & tag tanpa mengunggah

Butuh file OAuth client (Desktop app) dari Google Cloud di rahasia/client_secret.json (lihat SETUP.md).
Token tersimpan di rahasia/token.json. Folder rahasia/ tidak pernah di-commit.
Deskripsi disusun otomatis (lihat susun_deskripsi): tanpa link sumber, kredit singkat tanpa link, hashtag lengkap
(bible/gaya-upload.json). Dengan --jadwal video diunggah private lalu tayang otomatis di jam itu (dipakai autopilot).
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


URL = re.compile(r"(https?://|www\.)\S+", re.I)
HASHTAG = re.compile(r"#[^\s#]+")


def jadi_hashtag(t: str) -> str:
    """'kulit buatan' → '#kulitbuatan' (huruf kecil, tanpa spasi/tanda baca)."""
    inti = re.sub(r"[^0-9a-zà-ÿ]", "", str(t).lower().lstrip("#"))
    return f"#{inti}" if 2 <= len(inti) <= 30 and not inti.isdigit() else ""


def tanpa_link(teks: str) -> str:
    """Buang semua link dan baris 'Sumber:' (permintaan Zona: deskripsi tanpa link sumber)."""
    out = []
    for baris in str(teks).splitlines():
        if re.match(r"\s*(sumber|source|referensi|baca selengkapnya)\s*:", baris, re.I):
            continue
        b = URL.sub("", baris).rstrip(" ·-–—|,:") if URL.search(baris) else baris.rstrip()
        if b.strip() or not out or out[-1].strip():
            out.append(b)
    return "\n".join(out).strip()


def susun_deskripsi(sc: dict, kredit: str, musik: str, gaya: dict) -> str:
    """Deskripsi siap upload: isi Raka → ajakan → kredit singkat (tanpa link) → hashtag lengkap di akhir."""
    isi = tanpa_link(sc.get("deskripsi", ""))
    tag_isi = HASHTAG.findall(isi)
    isi = re.sub(r"[ \t]+\n", "\n", HASHTAG.sub("", isi)).strip()
    tags = []
    for t in tag_isi + [jadi_hashtag(x) for x in sc.get("tag", [])] + list(gaya.get("hashtag_tetap") or []):
        h = jadi_hashtag(t)
        if h and h not in tags:
            tags.append(h)
    tags = tags[: max(3, min(30, int(gaya.get("hashtag_maks", 15))))]
    bagian = [isi]
    pertanyaan = str(sc.get("komentar_pin") or "").strip()
    if pertanyaan:
        bagian.append(f"💬 {tanpa_link(pertanyaan)}")
    if gaya.get("ajakan"):
        bagian.append(f"🔔 {gaya['ajakan']}")
    if kredit:
        kredit = tanpa_link(kredit) if gaya.get("kredit_tanpa_link", True) else kredit
        bagian.append(kredit)
    if musik:
        bagian.append(f"🎵 Musik: {tanpa_link(musik) if gaya.get('kredit_tanpa_link', True) else musik}")
    bagian.append(" ".join(tags))
    return "\n\n".join(b for b in bagian if b.strip())


def metadata(slug: str) -> dict:
    vdir = VIDEOS / slug
    sc, man = rj(vdir / "script.json"), rj(vdir / "aset" / "manifest.json")
    kredit = (vdir / "aset" / "kredit_deskripsi.txt").read_text(encoding="utf-8").strip() if (vdir / "aset" / "kredit_deskripsi.txt").exists() else ""
    dari = rj(vdir / "thumbnail" / "info.json").get("dari") or {}
    if "CC BY" in str(dari.get("lisensi", "")):       # foto objek Mila dari Wikimedia CC BY → wajib dikredit
        kredit = (kredit + "\n" if kredit else "") + f"Foto objek: \"{dari.get('judul', '')}\" oleh {dari.get('pembuat', '-')} ({dari['lisensi']})"
    judul = re.sub(r"[<>]", "", sc.get("judul") or slug)[:100]
    musik = str(rj(vdir / "export" / "info.json").get("musik_kredit") or "").strip()
    desk = susun_deskripsi(sc, kredit, musik, rj(ROOT / "bible" / "gaya-upload.json"))
    desk = re.sub(r"[<>]", "", desk)[:4900]
    tags, n = [], 0
    for t in sc.get("tag", []):
        t = re.sub(r"[<>,]", "", str(t)).strip()
        if t and n + len(t) + 1 <= 480:
            tags.append(t)
            n += len(t) + 1
    ti = rj(VIDEOS / slug / "thumbnail" / "info.json")
    objek_ai = ti.get("ada_objek") and ti.get("sumber") == "ai"     # objek Mila (gambar AI) tampil di hook video
    return {"judul": judul, "deskripsi": desk, "tag": tags, "sintetis": bool(man.get("pakai_ai") or objek_ai)}


def pasang_thumbnail(yt, vid: str, vdir: Path) -> dict:
    """Thumbnail Mila (export/thumbnail.jpg) dipasang otomatis. Shorts: thumbnail khusus tampil di beranda, tab Shorts channel,
    pencarian & saat dibagikan (feed Shorts tetap memutar video, karena itu frame pembukanya dibuat sama dengan thumbnail)."""
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    f = vdir / "export" / "thumbnail.jpg"
    if not f.exists():
        return {"dipasang": False, "alasan": "belum ada export/thumbnail.jpg (Mila)"}
    try:
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(f), mimetype="image/jpeg")).execute()
        log("thumbnail Mila terpasang")
        return {"dipasang": True}
    except HttpError as err:
        teks = str(err)
        if "forbidden" in teks.lower() or getattr(err, "status_code", 0) == 403 or " 403 " in teks:
            alasan = ("YouTube belum mengizinkan thumbnail khusus untuk channel ini (perlu verifikasi nomor HP di "
                      "youtube.com/verify; thumbnail khusus Shorts dibuka bertahap). Pasang manual di YouTube Studio (desktop).")
        elif "quotaExceeded" in teks:
            alasan = "kuota YouTube API habis; pasang manual di YouTube Studio (desktop)"
        else:
            alasan = f"ditolak YouTube: {getattr(err, 'reason', teks)[:160]}"
        log(f"thumbnail tidak terpasang otomatis: {alasan} File: {f.relative_to(ROOT)}")
        return {"dipasang": False, "alasan": alasan}


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
    if not (vdir / "export" / "thumbnail.jpg").exists():      # video lama / dibuat sebelum ada Mila → thumbnail dibuat dulu
        log("thumbnail belum ada → Mila membuatnya dulu")
        try:
            subprocess.run([sys.executable, str(ROOT / "agents" / "thumbnail" / "thumbnail.py"), slug], cwd=ROOT, timeout=20 * 60)
        except (subprocess.TimeoutExpired, OSError) as err:
            log(f"thumbnail gagal dibuat ({err}); upload tetap lanjut")
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
            sys.exit("[uli] Kuota YouTube API hari ini habis. Coba lagi besok (autopilot otomatis mencoba lagi di jam berikutnya).")
        sys.exit(f"[uli] YouTube menolak upload: {reason}")
    vid = resp["id"]
    info = {"videoId": vid, "url": f"https://youtube.com/shorts/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
            "waktu": datetime.now(WIB).isoformat(timespec="seconds"), "jadwal": jadwal, "privasi": "private", "judul": m["judul"],
            "sintetis": m["sintetis"]}
    pin = str(rj(vdir / "script.json").get("komentar_pin") or "").strip()
    if pin:
        info["komentar_pin"] = pin       # API tidak bisa menyematkan komentar; Zona tempel & sematkan sendiri
    info["thumbnail"] = pasang_thumbnail(yt, vid, vdir)
    up.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", slug, "export", "--note", f"diupload private: {vid}"], cwd=ROOT)
    log(f"selesai: {info['url']} (private{', tayang ' + jadwal + ' WIB' if jadwal else ''}).")
    # hemat ruang: file besar video ini dihapus dari laptop (bible/penyimpanan.json → hapus_setelah_upload)
    subprocess.run([sys.executable, str(ROOT / "agents" / "bersih.py"), "video", slug, "--otomatis"], cwd=ROOT)
    if pin:
        log(f"komentar untuk disematkan setelah tayang: {pin}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Uli: upload private ke YouTube")
    ap.add_argument("perintah", choices=["login", "cek", "unggah", "pratinjau"])
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
        if a.perintah == "pratinjau":      # lihat judul, deskripsi & tag tanpa mengunggah
            m = metadata(a.slug)
            print(f"JUDUL: {m['judul']}\n\nDESKRIPSI:\n{m['deskripsi']}\n\nTAG: {', '.join(m['tag'])}")
            return
        unggah(a.slug, a.jadwal)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Uli untuk video panjang: unggah video berstatus export (disetujui Zona, atau autopilot video panjang yang lolos QC)
— private + jadwal tayang, dengan chapter (bab), deskripsi tanpa link, hashtag, kredit footage singkat, dan thumbnail.

    python agents/panjang/unggah_panjang.py pratinjau <slug>                     # lihat judul & deskripsi
    python agents/panjang/unggah_panjang.py unggah <slug> --jadwal 2026-11-03T19:00
    python agents/panjang/unggah_panjang.py unggah <slug>                        # jadwal: jam terbaik besok (insights/jadwal.json)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "upload"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import pakai_python  # noqa: E402

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "unggah":
    pakai_python.pastikan("googleapiclient", "google_auth_oauthlib")
import status as st_panjang  # noqa: E402
import unggah as uli  # noqa: E402

WIB = timezone(timedelta(hours=7))


def log(msg: str) -> None:
    print(f"[uli] {msg}", flush=True)


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def metadata(slug: str) -> dict:
    vdir = st_panjang.folder(slug)
    s, info = rj(vdir / "naskah.json"), rj(vdir / "export" / "info.json")
    gaya = rj(ROOT / "bible" / "gaya-upload.json")
    judul = re.sub(r"[<>]", "", re.sub(r"#\w+", "", s.get("judul") or slug)).strip()[:100]
    isi = uli.tanpa_link(s.get("deskripsi", ""))
    tag_isi = uli.HASHTAG.findall(isi)
    isi = uli.HASHTAG.sub("", isi).strip()
    bab = (vdir / "export" / "bab.txt").read_text(encoding="utf-8").strip() if (vdir / "export" / "bab.txt").exists() else ""
    tetap = [h for h in (gaya.get("hashtag_tetap") or []) if h.lower() != "#shorts"]
    tags = []
    for t in tag_isi + [uli.jadi_hashtag(x) for x in s.get("tag", [])] + tetap:
        h = uli.jadi_hashtag(t)
        if h and h not in tags:
            tags.append(h)
    bagian = [isi]
    if bab:
        bagian.append("⏱️ Isi video:\n" + bab)
    if s.get("komentar_pin"):
        bagian.append(f"💬 {uli.tanpa_link(s['komentar_pin'])}")
    if gaya.get("ajakan"):
        bagian.append(f"🔔 {gaya['ajakan']}")
    if s.get("format") == "dokumenter":
        kredit = [x.strip() for x in ((vdir / "footage" / "kredit_deskripsi.txt").read_text(encoding="utf-8").splitlines()
                                      if (vdir / "footage" / "kredit_deskripsi.txt").exists() else []) if x.strip()]
        if kredit:
            bagian.append("🎬 Footage & foto:\n" + "\n".join(uli.tanpa_link(k) for k in kredit[:25]))
    else:
        bagian.append("🎨 Animasi orisinal Yofamo Technology (ilustrasi dibantu AI).")
    if info.get("musik"):
        kredit = Path(ROOT / "musik").rglob(Path(info["musik"]).stem + ".txt")
        k = next(kredit, None)
        bagian.append(f"🎵 Musik: {uli.tanpa_link(k.read_text(encoding='utf-8-sig').strip()) if k else Path(info['musik']).stem}")
    bagian.append(" ".join(tags[:15]))
    desk = re.sub(r"[<>]", "", "\n\n".join(b for b in bagian if b.strip()))[:4900]
    tag_api, n = [], 0
    for t in s.get("tag", []):
        t = re.sub(r"[<>,]", "", str(t)).strip()
        if t and n + len(t) + 1 <= 480:
            tag_api.append(t)
            n += len(t) + 1
    return {"judul": judul, "deskripsi": desk, "tag": tag_api, "sintetis": s.get("format") != "dokumenter"}


def jadwal_bawaan() -> str:
    jd = rj(ROOT / "insights" / "jadwal.json")
    jam = max(jd.get("jam") or [{"jam": 19, "skor": 0}], key=lambda j: j.get("skor", 0))["jam"]
    besok = datetime.now(WIB).date() + timedelta(days=1)
    return f"{besok.isoformat()}T{int(jam):02d}:30"   # :30 supaya tidak bertabrakan dengan Shorts di jam yang sama


def unggah(slug: str, jadwal: str | None) -> None:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    vdir = st_panjang.folder(slug)
    exp = vdir / "export"
    if st_panjang.status(slug) != "export":
        sys.exit(f"[uli] Status video panjang '{st_panjang.status(slug)}'. Hanya video yang sudah kamu setujui yang diunggah.")
    if rj(exp / "info.json").get("uji"):
        sys.exit("[uli] Ini video mode uji. Tidak diupload.")
    if rj(exp / "upload.json").get("videoId"):
        sys.exit(f"[uli] Sudah diupload: {rj(exp / 'upload.json').get('url')}")
    jadwal = jadwal or jadwal_bawaan()
    t = datetime.fromisoformat(jadwal)
    t = t.replace(tzinfo=WIB) if t.tzinfo is None else t
    if t < datetime.now(WIB) + timedelta(minutes=15):
        sys.exit("[uli] jadwal minimal 15 menit dari sekarang")
    m = metadata(slug)
    body = {"snippet": {"title": m["judul"], "description": m["deskripsi"], "tags": m["tag"], "categoryId": "28",
                        "defaultLanguage": "id", "defaultAudioLanguage": "id"},
            "status": {"privacyStatus": "private", "publishAt": t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                       "selfDeclaredMadeForKids": False, "containsSyntheticMedia": m["sintetis"], "embeddable": True}}
    yt = uli.youtube(uli.creds())
    log(f"mengunggah video panjang ke '{uli.channel_name(yt)}': {m['judul']} (tayang {jadwal} WIB)")
    media = MediaFileUpload(str(exp / "final.mp4"), mimetype="video/mp4", chunksize=16 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media, notifySubscribers=True)
    resp = None
    try:
        while resp is None:
            prog, resp = req.next_chunk()
            if prog:
                log(f"{int(prog.progress() * 100)}%")
    except HttpError as err:
        sys.exit(f"[uli] YouTube menolak upload: {getattr(err, 'reason', err)}")
    vid = resp["id"]
    info = {"videoId": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
            "waktu": datetime.now(WIB).isoformat(timespec="seconds"), "jadwal": jadwal, "privasi": "private", "judul": m["judul"]}
    if (exp / "thumbnail.jpg").exists():
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(exp / "thumbnail.jpg"), mimetype="image/jpeg")).execute()
            info["thumbnail"] = True
        except HttpError as err:
            info["thumbnail"] = False
            log(f"thumbnail tidak bisa dipasang otomatis ({getattr(err, 'reason', err)}). Pasang manual di YouTube Studio: export/thumbnail.jpg "
                "(akun YouTube perlu verifikasi nomor HP untuk thumbnail khusus).")
    (exp / "upload.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"selesai: {info['url']} (private, tayang otomatis {jadwal} WIB). Subtitle siap di export/subtitle.srt.")
    import subprocess  # hemat ruang: file render video ini dihapus (bible/penyimpanan.json → hapus_setelah_upload)
    subprocess.run([sys.executable, str(ROOT / "agents" / "bersih.py"), "semua", "--otomatis"], cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description="Uli: upload video panjang")
    ap.add_argument("perintah", choices=["pratinjau", "unggah"])
    ap.add_argument("slug")
    ap.add_argument("--jadwal")
    a = ap.parse_args()
    if a.perintah == "pratinjau":
        m = metadata(a.slug)
        print(f"JUDUL: {m['judul']}\n\nDESKRIPSI:\n{m['deskripsi']}\n\nTAG: {', '.join(m['tag'])}\n\nJADWAL BAWAAN: {jadwal_bawaan()} WIB")
        return
    unggah(a.slug, a.jadwal)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Steve v2 — data retensi dari YouTube Analytics (butuh login yang sama dengan Uli).

    python agents/steve/analitik.py            # → insights/raw/analitik-YYYY-MM-DD.json
    python agents/steve/analitik.py --hari 60

Untuk setiap video channel: views, rata-rata durasi tonton, % ditonton, like, share, subscriber baru.
Video buatan pabrik (yang punya export/upload.json) diberi ciri produksinya: durasi, porsi gambar AI,
jumlah shot, suasana musik, kategori, teks hook, skor QC Rara. Dari sini Steve belajar resep yang menang.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "upload"))
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("googleapiclient", "google_auth_oauthlib")

RAW = ROOT / "insights" / "raw"
VIDEOS = ROOT / "videos"


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def ciri_produksi() -> dict[str, dict]:
    out = {}
    for d in VIDEOS.glob("*/export/upload.json"):
        vdir = d.parents[1]
        up, man, sc, idea = rj(d), rj(vdir / "aset" / "manifest.json"), rj(vdir / "script.json"), rj(vdir / "idea.json")
        klip = man.get("klip", [])
        total = sum(k.get("durasi", 0) for k in klip) or 1
        out[up.get("videoId", "")] = {
            "slug": vdir.name, "durasi": round(float(man.get("durasi") or 0), 1), "shot": len(klip),
            "porsi_ai": round(sum(k["durasi"] for k in klip if k.get("jenis") == "ai") / total, 2),
            "porsi_footage": round(sum(k["durasi"] for k in klip if k.get("jenis") == "footage") / total, 2),
            "kategori": idea.get("kategori"), "status_teknologi": idea.get("status_teknologi"),
            "hook_teks": sc.get("hook_teks"), "suasana": sc.get("suasana"),
            "skor_qc": rj(vdir / "export" / "qc_review.json").get("skor"),
        }
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Steve v2: retensi per video dari YouTube Analytics")
    ap.add_argument("--hari", type=int, default=120)
    a = ap.parse_args()
    import unggah  # login & token milik Uli
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    c = unggah.creds()
    yta = build("youtubeAnalytics", "v2", credentials=c, cache_discovery=False)
    yt = build("youtube", "v3", credentials=c, cache_discovery=False)
    end, start = date.today(), date.today() - timedelta(days=a.hari)
    try:
        rep = yta.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(),
                                  metrics="views,averageViewDuration,averageViewPercentage,likes,shares,subscribersGained",
                                  dimensions="video", sort="-views", maxResults=200).execute()
    except HttpError as err:
        sys.exit(f"[steve] YouTube Analytics menolak: {err}")
    cols = [h["name"] for h in rep.get("columnHeaders", [])]
    rows = [dict(zip(cols, r)) for r in rep.get("rows", [])]
    ids = [r["video"] for r in rows]
    judul = {}
    for n in range(0, len(ids), 50):
        res = yt.videos().list(part="snippet,contentDetails", id=",".join(ids[n:n + 50])).execute()
        for v in res.get("items", []):
            judul[v["id"]] = {"judul": v["snippet"]["title"], "terbit": v["snippet"]["publishedAt"][:10]}
    ciri = ciri_produksi()
    videos = [{**r, **judul.get(r["video"], {}), "pabrik": ciri.get(r["video"])} for r in rows]
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"analitik-{end.isoformat()}.json"
    out.write_text(json.dumps({"dari": start.isoformat(), "sampai": end.isoformat(), "videos": videos}, ensure_ascii=False, indent=2), encoding="utf-8")
    dari_pabrik = sum(1 for v in videos if v["pabrik"])
    print(f"[steve] {len(videos)} video ({dari_pabrik} buatan pabrik) → {out.relative_to(ROOT)}")
    if videos:
        rata = sum(v.get("averageViewPercentage", 0) for v in videos) / len(videos)
        print(f"[steve] rata-rata ditonton {rata:.0f}% durasi video")


if __name__ == "__main__":
    main()

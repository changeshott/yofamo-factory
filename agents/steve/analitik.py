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
            "eksperimen": sc.get("eksperimen"), "durasi_render": round(float(rj(vdir / "export" / "info.json").get("durasi") or 0), 1),
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

    def q(**kw) -> list[dict]:
        """Satu laporan tambahan; kalau ditolak (metrik/dimensi tidak tersedia), kembalikan [] tanpa menghentikan Steve."""
        try:
            r = yta.reports().query(ids="channel==MINE", startDate=start.isoformat(), endDate=end.isoformat(), **kw).execute()
            c = [h["name"] for h in r.get("columnHeaders", [])]
            return [dict(zip(c, x)) for x in r.get("rows", [])]
        except HttpError as err:
            print(f"[steve] laporan {kw.get('dimensions')} dilewati: {str(err)[:120]}", flush=True)
            return []

    harian = q(metrics="views,estimatedMinutesWatched,subscribersGained,subscribersLost,likes,shares", dimensions="day", sort="day")
    traffic = q(metrics="views,estimatedMinutesWatched", dimensions="insightTrafficSourceType", sort="-views")
    demografi = q(metrics="viewerPercentage", dimensions="ageGroup,gender", sort="-viewerPercentage")
    negara = q(metrics="views,averageViewPercentage", dimensions="country", sort="-views", maxResults=10)
    perangkat = q(metrics="views", dimensions="deviceType", sort="-views")
    # kurva retensi: 12 video terbaru + semua video buatan pabrik
    terbaru = sorted(videos, key=lambda v: v.get("terbit", ""), reverse=True)[:12]
    target = {v["video"] for v in terbaru} | {v["video"] for v in videos if v["pabrik"]}
    retensi = {}
    for vid in target:
        rows_r = q(metrics="audienceWatchRatio,relativeRetentionPerformance", dimensions="elapsedVideoTimeRatio", filters=f"video=={vid}")
        if rows_r:
            retensi[vid] = [[round(float(x["elapsedVideoTimeRatio"]), 3), round(float(x["audienceWatchRatio"]), 4),
                             round(float(x.get("relativeRetentionPerformance") or 0), 3)] for x in rows_r]
    RAW.mkdir(parents=True, exist_ok=True)
    out = RAW / f"analitik-{end.isoformat()}.json"
    out.write_text(json.dumps({"dari": start.isoformat(), "sampai": end.isoformat(), "videos": videos, "harian": harian,
                               "sumber_traffic": traffic, "demografi": demografi, "negara": negara, "perangkat": perangkat,
                               "retensi": retensi, "catatan_retensi": "[posisi 0–1 di video, rasio penonton yang masih menonton, performa relatif vs video sejenis (0,5 = rata-rata YouTube)]"},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[steve] harian {len(harian)} hari · sumber traffic {len(traffic)} · kurva retensi {len(retensi)} video")
    dari_pabrik = sum(1 for v in videos if v["pabrik"])
    print(f"[steve] {len(videos)} video ({dari_pabrik} buatan pabrik) → {out.relative_to(ROOT)}")
    if videos:
        rata = sum(v.get("averageViewPercentage", 0) for v in videos) / len(videos)
        print(f"[steve] rata-rata ditonton {rata:.0f}% durasi video")


if __name__ == "__main__":
    main()

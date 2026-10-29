#!/usr/bin/env python3
"""Steve: radar pasar — Shorts teknologi berbahasa Indonesia yang sedang ramai 30 hari terakhir (channel lain).
Dipakai untuk melihat topik yang terbukti diminati penonton Indonesia tapi BELUM dibahas Yofamo.

    python agents/steve/pasar.py                     # → insights/raw/pasar-YYYY-MM-DD.json
    python agents/steve/pasar.py --kata "robot canggih" --kata "gadget unik" --hari 14

Biaya kuota: ±100 unit per kata kunci (search) + 1 unit per 50 video. Default 5 kata = ±505 unit (kuota harian 10.000).
Hanya membaca data publik; tidak ada video yang diunduh.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ytdata  # noqa: E402

KATA = ["teknologi canggih", "teknologi masa depan", "inovasi teknologi unik", "gadget unik", "penemuan ilmuwan terbaru"]


def detik(iso: str) -> int:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    return sum(int(x or 0) * k for x, k in zip(m.groups(), (86400, 3600, 60, 1))) if m else 0


def main() -> None:
    ap = argparse.ArgumentParser(description="Radar Shorts teknologi Indonesia yang sedang ramai")
    ap.add_argument("--kata", action="append", help="kata kunci pencarian (boleh berulang)")
    ap.add_argument("--hari", type=int, default=30)
    a = ap.parse_args()
    ytdata.load_env()
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("[steve] YOUTUBE_API_KEY belum diisi di .env")
    own = ytdata.read(ytdata.latest()).get("channel", {}).get("id")
    since = (datetime.now(timezone.utc) - timedelta(days=a.hari)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids, asal = [], {}
    for q in a.kata or KATA:
        try:
            res = ytdata.get("search", {"part": "id", "q": q, "type": "video", "videoDuration": "short", "regionCode": "ID",
                                        "relevanceLanguage": "id", "publishedAfter": since, "order": "viewCount", "maxResults": 25}, key)
        except ytdata.YtError as err:
            if err.reason == "quotaExceeded":
                print("[steve] kuota YouTube API habis; radar pasar dihentikan", flush=True)
                break
            print(f"[steve] pencarian '{q}' gagal: {err.reason}", flush=True)
            continue
        for it in res.get("items", []):
            vid = it["id"].get("videoId")
            if vid and vid not in asal:
                ids.append(vid)
                asal[vid] = q
    now = datetime.now(timezone.utc)
    vids = []
    for n in range(0, len(ids), 50):
        try:
            res = ytdata.get("videos", {"part": "snippet,statistics,contentDetails", "id": ",".join(ids[n:n + 50])}, key)
        except ytdata.YtError as err:
            print(f"[steve] detail video gagal: {err.reason}", flush=True)
            continue
        for v in res.get("items", []):
            sn, st = v["snippet"], v.get("statistics", {})
            d = detik(v["contentDetails"].get("duration", ""))
            if sn.get("channelId") == own or not 0 < d <= 180:
                continue
            pub = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
            umur = max((now - pub).total_seconds() / 86400, 0.5)
            views = int(st.get("viewCount", 0))
            vids.append({"id": v["id"], "judul": sn["title"], "channel": sn.get("channelTitle", ""), "terbit": sn["publishedAt"][:10],
                         "durasi_s": d, "views": views, "likes": int(st.get("likeCount", 0)), "komentar": int(st.get("commentCount", 0)),
                         "views_per_hari": round(views / umur, 1), "kata": asal[v["id"]],
                         "url": f"https://www.youtube.com/shorts/{v['id']}"})
    vids.sort(key=lambda x: -x["views_per_hari"])
    chan: dict[str, int] = {}
    for v in vids:
        chan[v["channel"]] = chan.get(v["channel"], 0) + 1
    hasil = {"tanggal": now.date().isoformat(), "hari": a.hari, "kata": a.kata or KATA, "jumlah": len(vids),
             "channel_teratas": sorted(chan.items(), key=lambda x: -x[1])[:10], "video": vids[:80]}
    ytdata.RAW.mkdir(parents=True, exist_ok=True)
    f = ytdata.RAW / f"pasar-{now.date().isoformat()}.json"
    f.write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[steve] radar pasar: {len(vids)} Shorts teknologi Indonesia {a.hari} hari terakhir → {f.relative_to(ytdata.ROOT)}")
    for v in vids[:5]:
        print(f"[steve]   {v['views_per_hari']:>8.0f}/hari  {v['judul'][:70]} ({v['channel']})")


if __name__ == "__main__":
    main()

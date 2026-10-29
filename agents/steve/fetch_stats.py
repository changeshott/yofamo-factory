#!/usr/bin/env python3
"""Steve — pengambil statistik publik channel Yofamo Technology.

Hanya MEMBACA data publik lewat YouTube Data API v3 (API key, tanpa login).
Hasil: insights/raw/YYYY-MM-DD.json berisi semua video + metrik turunan
+ perubahan views sejak snapshot sebelumnya.

Pemakaian (dari root project):
    python agents/steve/fetch_stats.py
    python agents/steve/fetch_stats.py --check
    python agents/steve/fetch_stats.py --fixture agents/steve/sample_videos.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "insights" / "raw"
API = "https://www.googleapis.com/youtube/v3"
DEFAULT_HANDLE = "@yofamoo_technology"
SHORTS_MAX_SECONDS = 180


def load_env() -> None:
    """Baca .env sederhana (KEY=VALUE) tanpa dependency tambahan."""
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def api_get(endpoint: str, params: dict, key: str) -> dict:
    query = urllib.parse.urlencode({**params, "key": key})
    url = f"{API}/{endpoint}?{query}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        try:
            reason = json.loads(body)["error"]["message"]
        except (ValueError, KeyError):
            reason = body[:200]
        sys.exit(f"[steve] YouTube API error {err.code} di {endpoint}: {reason}")
    except urllib.error.URLError as err:
        sys.exit(f"[steve] Tidak bisa menghubungi YouTube API: {err.reason}")


def parse_duration(iso: str) -> int:
    """PT1M5S -> 65 detik."""
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def fetch_channel(handle: str, key: str) -> tuple[dict, list[dict]]:
    ch = api_get("channels", {"part": "snippet,statistics,contentDetails", "forHandle": handle}, key)
    if not ch.get("items"):
        sys.exit(f"[steve] Channel {handle} tidak ditemukan.")
    item = ch["items"][0]
    uploads = item["contentDetails"]["relatedPlaylists"]["uploads"]

    video_ids, page = [], None
    while True:
        params = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50}
        if page:
            params["pageToken"] = page
        res = api_get("playlistItems", params, key)
        video_ids += [i["contentDetails"]["videoId"] for i in res.get("items", [])]
        page = res.get("nextPageToken")
        if not page:
            break

    videos = []
    for start in range(0, len(video_ids), 50):
        chunk = ",".join(video_ids[start:start + 50])
        res = api_get("videos", {"part": "snippet,statistics,contentDetails", "id": chunk}, key)
        videos += res.get("items", [])

    channel = {
        "id": item["id"],
        "title": item["snippet"]["title"],
        "handle": handle,
        "subscribers": int(item["statistics"].get("subscriberCount", 0)),
        "total_views": int(item["statistics"].get("viewCount", 0)),
        "video_count": int(item["statistics"].get("videoCount", 0)),
    }
    return channel, videos


def build_rows(videos: list[dict], now: datetime) -> list[dict]:
    rows = []
    for v in videos:
        st, sn = v.get("statistics", {}), v["snippet"]
        published = datetime.fromisoformat(sn["publishedAt"].replace("Z", "+00:00"))
        age_days = max((now - published).total_seconds() / 86400, 0.5)
        views = int(st.get("viewCount", 0))
        likes = int(st.get("likeCount", 0))
        comments = int(st.get("commentCount", 0))
        seconds = parse_duration(v["contentDetails"].get("duration", ""))
        rows.append({
            "id": v["id"],
            "url": f"https://www.youtube.com/shorts/{v['id']}",
            "title": sn["title"],
            "published": published.date().isoformat(),
            "published_at": sn["publishedAt"],
            "age_days": round(age_days, 1),
            "duration_s": seconds,
            "is_short": 0 < seconds <= SHORTS_MAX_SECONDS,
            "views": views,
            "likes": likes,
            "comments": comments,
            "views_per_day": round(views / age_days, 1),
            "engagement_pct": round((likes + comments) / views * 100, 2) if views else 0.0,
        })
    rows.sort(key=lambda r: r["published"], reverse=True)
    return rows


def add_comparisons(rows: list[dict], previous: dict | None) -> dict:
    # median & tier hanya dari Shorts: video panjang/0 views (misalnya unggahan nyasar) tidak boleh menggeser patokan
    views = [r["views"] for r in rows if r["is_short"]] or [r["views"] for r in rows] or [0]
    median = statistics.median(views)
    prev_views = {v["id"]: v["views"] for v in (previous or {}).get("videos", [])}
    for r in rows:
        if not r["is_short"]:
            r.update(vs_median=None, tier="bukan-short", views_since_last=r["views"] - prev_views.get(r["id"], r["views"]),
                     is_new=r["id"] not in prev_views and previous is not None)
            continue
        r["vs_median"] = round(r["views"] / median, 2) if median else None
        r["tier"] = "menang" if median and r["views"] >= 1.5 * median else (
            "lemah" if median and r["views"] <= 0.75 * median else "rata-rata")
        r["views_since_last"] = r["views"] - prev_views[r["id"]] if r["id"] in prev_views else None
        r["is_new"] = r["id"] not in prev_views and previous is not None
    return {
        "videos": len(rows),
        "shorts": sum(1 for r in rows if r["is_short"]),
        "median_views": median,
        "mean_views": round(statistics.mean(views), 1),
        "total_views_videos": sum(views),
        "winners": [r["title"] for r in rows if r.get("tier") == "menang"],
        "previous_snapshot": (previous or {}).get("snapshot_date"),
    }


def latest_snapshot(exclude: str) -> dict | None:
    # hanya snapshot harian (YYYY-MM-DD.json), bukan analitik-/komentar-/pasar-/analisa-
    files = sorted(p for p in RAW_DIR.glob("*.json") if re.fullmatch(r"\d{4}-\d\d-\d\d", p.stem) and p.stem != exclude)
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Ambil statistik publik channel untuk Steve.")
    ap.add_argument("--handle", default=os.environ.get("YOUTUBE_CHANNEL_HANDLE", DEFAULT_HANDLE))
    ap.add_argument("--check", action="store_true", help="cek API key & channel saja")
    ap.add_argument("--fixture", help="pakai file JSON contoh (uji tanpa internet)")
    args = ap.parse_args()

    load_env()
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()

    if args.fixture:
        data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
        channel, videos = data["channel"], data["videos"]
    else:
        key = os.environ.get("YOUTUBE_API_KEY")
        if not key:
            sys.exit("[steve] YOUTUBE_API_KEY belum diisi di .env")
        if args.check:
            ch = api_get("channels", {"part": "statistics", "forHandle": args.handle}, key)
            if not ch.get("items"):
                sys.exit(f"[steve] API key OK, tapi channel {args.handle} tidak ditemukan.")
            print(f"[steve] OK — {args.handle}: {ch['items'][0]['statistics'].get('subscriberCount')} subscriber")
            return
        channel, videos = fetch_channel(args.handle, key)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rows = build_rows(videos, now)
    summary = add_comparisons(rows, latest_snapshot(exclude=today))
    snapshot = {"snapshot_date": today, "fetched_at": now.isoformat(timespec="seconds"),
                "channel": channel, "summary": summary, "videos": rows}

    out = RAW_DIR / f"{today}.json"
    out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[steve] {len(rows)} video disimpan ke {out.relative_to(ROOT)} "
          f"(median {summary['median_views']:.0f} views, {len(summary['winners'])} pemenang)")


if __name__ == "__main__":
    main()

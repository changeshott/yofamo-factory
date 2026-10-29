#!/usr/bin/env python3
"""Steve: komentar publik di Shorts channel → apa yang penonton tanyakan, minta, puji, atau keluhkan.

    python agents/steve/komentar.py            # → insights/raw/komentar-YYYY-MM-DD.json
    python agents/steve/komentar.py --video 30

Biaya kuota YouTube Data API: 1 unit per video. Hanya membaca.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ytdata  # noqa: E402

MINTA = re.compile(r"\b(bahas|bikin(in)?|buat(in)?|request|req|tolong|dong|lanjut|part\s*2|next|video tentang|review)\b", re.I)
TANYA = re.compile(r"\?|\b(apa|gimana|bagaimana|berapa|kapan|dimana|di mana|kenapa|beneran|asli|hoax|harga)\b", re.I)
KRITIK = re.compile(r"\b(hoax|bohong|salah|clickbait|ai\b|suara robot|jelek|lebay|ngarang)\b", re.I)


def main() -> None:
    ap = argparse.ArgumentParser(description="Ambil komentar publik Shorts channel")
    ap.add_argument("--video", type=int, default=30, help="jumlah Short terbaru yang dibaca")
    a = ap.parse_args()
    ytdata.load_env()
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        sys.exit("[steve] YOUTUBE_API_KEY belum diisi di .env")
    snap = ytdata.read(ytdata.latest())
    if not snap:
        sys.exit("[steve] belum ada snapshot; jalankan fetch_stats.py dulu")
    vids = [v for v in snap["videos"] if v.get("is_short") and v.get("comments", 0) > 0][: a.video]
    out, total = [], 0
    for v in vids:
        try:
            res = ytdata.get("commentThreads", {"part": "snippet", "videoId": v["id"], "maxResults": 50, "order": "relevance", "textFormat": "plainText"}, key)
        except ytdata.YtError as err:
            out.append({"id": v["id"], "judul": v["title"], "error": err.reason})
            continue
        kom = []
        for it in res.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            t = re.sub(r"\s+", " ", s.get("textDisplay", "")).strip()[:300]
            kom.append({"teks": t, "like": s.get("likeCount", 0), "balasan": it["snippet"].get("totalReplyCount", 0),
                        "waktu": s.get("publishedAt", "")[:10], "minta": bool(MINTA.search(t)), "tanya": bool(TANYA.search(t)),
                        "kritik": bool(KRITIK.search(t))})
        total += len(kom)
        out.append({"id": v["id"], "judul": v["title"], "views": v["views"], "komentar": kom})
    hasil = {"tanggal": date.today().isoformat(), "video": len(out), "komentar": total,
             "permintaan": [{"video": x["judul"][:60], **k} for x in out for k in x.get("komentar", []) if k["minta"]],
             "pertanyaan": [{"video": x["judul"][:60], **k} for x in out for k in x.get("komentar", []) if k["tanya"]][:60],
             "kritik": [{"video": x["judul"][:60], **k} for x in out for k in x.get("komentar", []) if k["kritik"]][:40],
             "per_video": out}
    ytdata.RAW.mkdir(parents=True, exist_ok=True)
    f = ytdata.RAW / f"komentar-{date.today().isoformat()}.json"
    f.write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[steve] {total} komentar dari {len(out)} Short → {f.relative_to(ytdata.ROOT)} "
          f"({len(hasil['permintaan'])} permintaan topik, {len(hasil['pertanyaan'])} pertanyaan, {len(hasil['kritik'])} kritik)")


if __name__ == "__main__":
    main()

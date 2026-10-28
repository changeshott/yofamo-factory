"""Sumber klip Bima. Semua mengembalikan kandidat dengan bentuk yang sama.

Urutan prioritas (paling akurat untuk teknologi nyata → paling umum):
    youtube  — hanya video berlisensi Creative Commons (CC BY), lewat YouTube Data API
    nasa     — NASA Image and Video Library (domain publik, tanpa API key)
    wikimedia— Wikimedia Commons, hanya domain publik / CC0 / CC BY (tanpa API key)
    pexels   — Pexels License
    pixabay  — Pixabay Content License
"""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

UA = "YofamoFactory/1.0 (+https://www.youtube.com/@yofamoo_technology)"


def http_json(url: str, headers: dict | None = None, data: bytes | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


def kandidat(**kw) -> dict:
    base = {"sumber": "", "id": "", "judul": "", "url_halaman": "", "gambar": "", "pembuat": "", "durasi": 0.0,
            "lebar": 0, "tinggi": 0, "lisensi": "", "unduh": "", "heatmap": []}
    base.update(kw)
    base["id"] = str(base["id"])
    return base


# ------------------------------------------------------------------ YouTube (CC BY saja)
def iso_seconds(iso: str) -> float:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return 0.0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return float(d * 86400 + h * 3600 + mi * 60 + s)


def youtube_cc(query: str, key: str) -> list[dict]:
    """Biaya kuota: 100 unit (search) + 1 unit (videos). Kuota harian gratis 10.000 unit."""
    params = {"part": "snippet", "q": query, "type": "video", "videoLicense": "creativeCommon",
              "videoDefinition": "high", "videoEmbeddable": "true", "maxResults": 8, "safeSearch": "strict", "key": key}
    data = http_json("https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode(params))
    ids = [it["id"]["videoId"] for it in data.get("items", []) if it.get("id", {}).get("videoId")]
    return youtube_details(ids, key) if ids else []


def youtube_details(ids: list[str], key: str) -> list[dict]:
    params = {"part": "snippet,contentDetails,status", "id": ",".join(ids), "key": key}
    data = http_json("https://www.googleapis.com/youtube/v3/videos?" + urllib.parse.urlencode(params))
    out = []
    for v in data.get("items", []):
        if (v.get("status") or {}).get("license") != "creativeCommon":
            continue                                   # periksa ulang: hanya CC BY
        dur = iso_seconds((v.get("contentDetails") or {}).get("duration", ""))
        if not 5 <= dur <= 20 * 60:
            continue                                   # terlalu pendek / terlalu panjang untuk dipotong
        sn = v.get("snippet") or {}
        th = sn.get("thumbnails") or {}
        thumb = (th.get("high") or th.get("medium") or th.get("default") or {}).get("url", "")
        out.append(kandidat(sumber="youtube", id=v["id"], judul=sn.get("title", ""), pembuat=sn.get("channelTitle", ""),
                            url_halaman=f"https://www.youtube.com/watch?v={v['id']}", gambar=thumb, durasi=dur,
                            lebar=1920, tinggi=1080, lisensi="Creative Commons Attribution (CC BY)",
                            unduh=f"https://www.youtube.com/watch?v={v['id']}"))
    return out


# ------------------------------------------------------------------ NASA
def nasa(query: str) -> list[dict]:
    data = http_json("https://images-api.nasa.gov/search?" + urllib.parse.urlencode({"q": query, "media_type": "video"}))
    out = []
    for it in (data.get("collection") or {}).get("items", [])[:6]:
        meta = (it.get("data") or [{}])[0]
        nid = meta.get("nasa_id")
        if not nid:
            continue
        prev = next((ln.get("href", "") for ln in it.get("links", []) if ln.get("rel") == "preview"), "")
        out.append(kandidat(sumber="nasa", id=nid, judul=meta.get("title", ""), pembuat=meta.get("center") or "NASA",
                            url_halaman=f"https://images.nasa.gov/details/{urllib.parse.quote(nid)}", gambar=prev,
                            lebar=1920, tinggi=1080, lisensi="NASA (domain publik; tanpa kesan didukung NASA)",
                            unduh=f"nasa:{nid}"))
    return out


WIKI_OK = re.compile(r"^(public domain|pd\b|cc0|cc[ -]by[ -]\d)", re.I)


def wikimedia(query: str) -> list[dict]:
    """Video Wikimedia Commons. CC BY-SA dan lisensi lain dilewati supaya aman dipakai ulang."""
    params = {"action": "query", "format": "json", "generator": "search", "gsrsearch": f"{query} filetype:video",
              "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|size|extmetadata",
              "iiurlwidth": 480}
    data = http_json("https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params))
    pages = sorted((data.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    out = []
    for p in pages:
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = re.sub(r"<[^>]+>", "", (meta.get("LicenseShortName") or {}).get("value", "")).strip()
        if not lic or not WIKI_OK.match(lic) or "sa" in lic.lower().split():
            continue
        if "-sa" in lic.lower() or " sa " in f" {lic.lower()} ":
            continue
        artist = re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "")).strip()[:80]
        title = re.sub(r"^File:|\.(webm|ogv|mp4|mpg|mpeg)$", "", p.get("title", ""), flags=re.I)
        out.append(kandidat(sumber="wikimedia", id=p.get("pageid", ""), judul=title, pembuat=artist or "Wikimedia Commons",
                            url_halaman=info.get("descriptionurl", ""), gambar=info.get("thumburl", ""),
                            lebar=info.get("width") or 0, tinggi=info.get("height") or 0, durasi=float(info.get("duration") or 0),
                            lisensi=f"{lic} (Wikimedia Commons)", unduh=info.get("url", "")))
        if len(out) >= 6:
            break
    return out


def nasa_file(nid: str) -> str:
    """Pilih file mp4 NASA yang cukup tajam tapi tidak raksasa."""
    data = http_json(f"https://images-api.nasa.gov/asset/{urllib.parse.quote(nid)}")
    hrefs = [i.get("href", "") for i in (data.get("collection") or {}).get("items", [])]
    mp4 = [h for h in hrefs if h.lower().endswith(".mp4")]
    for tag in ("~large", "~medium", "~orig", "~mobile"):
        for h in mp4:
            if tag in h:
                return h.replace("http://", "https://")
    if not mp4:
        raise ValueError("tidak ada file mp4")
    return mp4[0].replace("http://", "https://")


# ------------------------------------------------------------------ Pexels & Pixabay
def pexels(query: str, key: str) -> list[dict]:
    params = {"query": query, "orientation": "portrait", "per_page": 8}
    data = http_json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(params), {"Authorization": key})
    return [c for v in data.get("videos", []) if (c := from_pexels(v))]


def from_pexels(v: dict) -> dict | None:
    files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link") and f.get("height")]
    if not files:
        return None
    portrait = [f for f in files if f["height"] > (f.get("width") or 0)] or files
    good = [f for f in portrait if f["height"] >= 1280]
    f = min(good, key=lambda x: x["height"]) if good else max(portrait, key=lambda x: x["height"])
    return kandidat(sumber="pexels", id=v["id"], judul=re.sub(r"[-/]", " ", v.get("url", "").rstrip("/").rsplit("/", 1)[-1]),
                    url_halaman=v.get("url", ""), gambar=v.get("image", ""), pembuat=(v.get("user") or {}).get("name", ""),
                    durasi=float(v.get("duration") or 0), lebar=f.get("width") or 0, tinggi=f["height"], unduh=f["link"],
                    lisensi="Pexels License")


def pixabay(query: str, key: str) -> list[dict]:
    params = {"key": key, "q": query[:100], "per_page": 8, "safesearch": "true"}
    data = http_json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode(params))
    out = []
    for h in data.get("hits", []):
        vids = h.get("videos") or {}
        f = next((vids[k] for k in ("large", "medium", "small") if (vids.get(k) or {}).get("url")), None)
        if f:
            out.append(kandidat(sumber="pixabay", id=h["id"], judul=h.get("tags", ""), url_halaman=h.get("pageURL", ""),
                                gambar=f.get("thumbnail", ""), pembuat=h.get("user", ""), durasi=float(h.get("duration") or 0),
                                lebar=f.get("width") or 0, tinggi=f.get("height") or 0, unduh=f["url"],
                                lisensi="Pixabay Content License"))
    return out


# ------------------------------------------------------------------ Cloudflare Workers AI (gambar)
def flux_image(prompt: str, account: str, token: str, seed: int) -> bytes:
    """FLUX.1 schnell gratis ±170 gambar/hari (10.000 neuron). Mengembalikan JPEG."""
    import base64
    url = f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    body = json.dumps({"prompt": prompt[:2000], "steps": 6, "seed": seed}).encode()
    data = http_json(url, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, body)
    img = (data.get("result") or {}).get("image")
    if not img:
        raise ValueError(f"Cloudflare tidak mengirim gambar: {json.dumps(data.get('errors'))[:200]}")
    return base64.b64decode(img)

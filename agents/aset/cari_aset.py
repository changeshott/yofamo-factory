#!/usr/bin/env python3
"""Bima — agent pencari aset Yofamo. Mencari klip video vertikal berlisensi gratis untuk setiap kalimat naskah.

Sumber: Pexels (utama) dan Pixabay (cadangan). Keduanya boleh dipakai di YouTube tanpa bayar
dan tanpa wajib atribusi, tapi kredit tetap dicatat di aset/KREDIT.txt.

Pemakaian (dari root project):
    python agents/aset/cari_aset.py <slug>            # cari + unduh klip untuk semua kalimat
    python agents/aset/cari_aset.py <slug> --ulang 3  # ganti klip kalimat ke-3 (nomor mulai 1)
    python agents/aset/cari_aset.py <slug> --uji      # tanpa internet: pakai contoh respon, tidak mengunduh

Kata kunci pencarian dibaca dari videos/<slug>/aset/kueri.json (ditulis Bima lewat Claude, bahasa Inggris):
    {"kueri": [{"i": 0, "kata": ["robot hand touch", "robotic arm close up"]}, ...]}
Kalau file itu tidak ada, kolom "visual" naskah dipakai langsung (bahasa Indonesia, hasil biasanya kurang tepat).

Hasil di videos/<slug>/aset/: 01-pexels-123.mp4 …, manifest.json, KREDIT.txt. Status video menjadi 'aset'
kalau semua kalimat sudah punya klip.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1].parent
VIDEOS = ROOT / "videos"
FIXTURE = Path(__file__).with_name("contoh_respon.json")
UA = "YofamoFactory/1.0 (+https://www.youtube.com/@yofamoo_technology)"
MAX_BYTES = 80 * 1024 * 1024
WPS = 2.6


def load_env() -> None:
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def http_json(url: str, headers: dict | None = None) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


# ------------------------------------------------------------------ sumber
def pexels(query: str, key: str, locale: str | None) -> list[dict]:
    params = {"query": query, "orientation": "portrait", "per_page": 15}
    if locale:
        params["locale"] = locale
    data = http_json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode(params), {"Authorization": key})
    return [c for v in data.get("videos", []) if (c := from_pexels(v))]


def from_pexels(v: dict) -> dict | None:
    files = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and f.get("link") and f.get("height")]
    if not files:
        return None
    portrait = [f for f in files if f["height"] > (f.get("width") or 0)] or files
    good = [f for f in portrait if f["height"] >= 1280]
    f = min(good, key=lambda x: x["height"]) if good else max(portrait, key=lambda x: x["height"])
    return {"sumber": "pexels", "id": v["id"], "url_halaman": v.get("url", ""), "gambar": v.get("image", ""),
            "pembuat": (v.get("user") or {}).get("name", ""), "durasi": v.get("duration", 0),
            "lebar": f.get("width") or 0, "tinggi": f["height"], "unduh": f["link"], "lisensi": "Pexels License"}


def pixabay(query: str, key: str, lang: str) -> list[dict]:
    params = {"key": key, "q": query[:100], "lang": lang, "per_page": 20, "safesearch": "true"}
    data = http_json("https://pixabay.com/api/videos/?" + urllib.parse.urlencode(params))
    return [c for h in data.get("hits", []) if (c := from_pixabay(h))]


def from_pixabay(h: dict) -> dict | None:
    vids = h.get("videos") or {}
    f = next((vids[k] for k in ("large", "medium", "small") if (vids.get(k) or {}).get("url")), None)
    if not f:
        return None
    return {"sumber": "pixabay", "id": h["id"], "url_halaman": h.get("pageURL", ""), "gambar": f.get("thumbnail", ""),
            "pembuat": h.get("user", ""), "durasi": h.get("duration", 0),
            "lebar": f.get("width") or 0, "tinggi": f.get("height") or 0, "unduh": f["url"], "lisensi": "Pixabay Content License"}


def score(c: dict, need: float) -> float:
    s = 0.0
    if c["tinggi"] > c["lebar"]:
        s += 10                                   # vertikal = tidak perlu crop berat
    if c["durasi"] >= need:
        s += 5
    else:
        s -= (need - c["durasi"]) * 2
    s -= abs(c["tinggi"] - 1920) / 1000           # dekat 1080x1920
    if c["sumber"] == "pexels":
        s += 0.5
    return s


# ------------------------------------------------------------------ data video
def sentence_needs(narasi: list[dict], folder: Path) -> list[float]:
    """Durasi tiap kalimat (detik) dari words.json Dara; kalau belum ada, perkiraan dari jumlah kata."""
    try:
        w = json.loads((folder / "words.json").read_text(encoding="utf-8-sig"))
        by_i = {k["i"]: k["selesai"] - k["mulai"] for k in w.get("kalimat", [])}
    except (OSError, ValueError, KeyError):
        by_i = {}
    return [round(by_i.get(i, len(n["kalimat"].split()) / WPS) + 0.4, 2) for i, n in enumerate(narasi)]


def queries_for(folder: Path, narasi: list[dict]) -> tuple[list[list[str]], bool]:
    try:
        data = json.loads((folder / "aset" / "kueri.json").read_text(encoding="utf-8-sig"))
        by_i = {int(q["i"]): [str(k).strip() for k in q.get("kata", []) if str(k).strip()][:4] for q in data.get("kueri", [])}
        if by_i:
            return [by_i.get(i) or [n["visual"]] for i, n in enumerate(narasi)], True
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return [[n.get("visual") or n["kalimat"]] for n in narasi], False


def download(url: str, dest: Path) -> None:
    part = dest.with_suffix(".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    size = 0
    try:
        with urllib.request.urlopen(req, timeout=60) as resp, part.open("wb") as f:
            while chunk := resp.read(1 << 16):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError("file lebih dari 80 MB")
                f.write(chunk)
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)


def status_of(slug: str) -> str | None:
    out = subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "list", "--json"], capture_output=True, text=True, cwd=ROOT, encoding="utf-8")
    try:
        return next((r["status"] for r in json.loads(out.stdout) if r["slug"] == slug), None)
    except ValueError:
        return None


# ------------------------------------------------------------------ utama
def main() -> None:
    ap = argparse.ArgumentParser(description="Bima: klip video berlisensi gratis per kalimat naskah")
    ap.add_argument("slug")
    ap.add_argument("--ulang", type=int, action="append", default=[], help="nomor kalimat (mulai 1) yang klipnya diganti")
    ap.add_argument("--uji", action="store_true", help="tanpa internet: pakai contoh respon, tidak mengunduh, status tidak diubah")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9-]{3,80}", args.slug):
        sys.exit("[bima] slug tidak valid")
    folder = VIDEOS / args.slug
    try:
        script = json.loads((folder / "script.json").read_text(encoding="utf-8-sig"))
    except OSError:
        sys.exit(f"[bima] videos/{args.slug}/script.json belum ada.")
    narasi = [n for n in script.get("narasi", []) if str(n.get("kalimat", "")).strip()]
    if not narasi:
        sys.exit("[bima] naskah kosong")

    if not args.uji:
        st = status_of(args.slug)
        if st not in ("suara", "aset"):
            sys.exit(f"[bima] status video '{st}'. Aset dicari setelah suara dibuat Dara (status suara).")
        load_env()
    pex, pix = os.environ.get("PEXELS_API_KEY", ""), os.environ.get("PIXABAY_API_KEY", "")
    if not args.uji and not pex and not pix:
        sys.exit("[bima] Isi PEXELS_API_KEY (gratis di pexels.com/api) atau PIXABAY_API_KEY di .env dulu.")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8")) if args.uji else None

    aset = folder / "aset"
    aset.mkdir(parents=True, exist_ok=True)
    mpath = aset / "manifest.json"
    try:
        old = {k["i"]: k for k in json.loads(mpath.read_text(encoding="utf-8")).get("klip", [])}
    except (OSError, ValueError, KeyError):
        old = {}
    redo = {n - 1 for n in args.ulang}
    needs = sentence_needs(narasi, folder)
    queries, english = queries_for(folder, narasi)
    print(f"[bima] {len(narasi)} kalimat, kata kunci {'dari kueri.json' if english else 'dari kolom visual (bahasa Indonesia)'}")

    used = {(k["sumber"], k["id"]) for i, k in old.items() if i not in redo}
    klip, kurang = [], []
    for i, n in enumerate(narasi):
        prev = old.get(i)
        if prev and i not in redo and (args.uji or (aset / prev["file"]).exists()):
            klip.append(prev)
            print(f"[bima] {i + 1:02}. tetap: {prev['file']}")
            continue
        found: list[dict] = []
        q_used = ""
        for q in queries[i]:
            try:
                if fixture is not None:
                    found = [c for v in fixture.get("pexels", {}).get("videos", []) if (c := from_pexels(v))]
                else:
                    if pex:
                        found = pexels(q, pex, None if english else "id-ID")
                    if pix and len(found) < 3:
                        found += pixabay(q, pix, "en" if english else "id")
            except urllib.error.HTTPError as err:
                sys.exit(f"[bima] API menolak permintaan ({err.code}). Cek API key di .env.")
            except (urllib.error.URLError, TimeoutError) as err:
                sys.exit(f"[bima] Tidak bisa menghubungi Pexels/Pixabay: {err}. Cek koneksi internet.")
            found = [c for c in found if (c["sumber"], c["id"]) not in used]
            if found:
                q_used = q
                break
        if not found:
            kurang.append(i + 1)
            print(f"[bima] {i + 1:02}. TIDAK KETEMU untuk: {' / '.join(queries[i])}")
            continue
        found.sort(key=lambda c: score(c, needs[i]), reverse=True)
        best = found[0]
        name = f"{i + 1:02}-{best['sumber']}-{best['id']}.mp4"
        if fixture is None:
            try:
                download(best["unduh"], aset / name)
            except (urllib.error.URLError, OSError, ValueError, TimeoutError) as err:
                kurang.append(i + 1)
                print(f"[bima] {i + 1:02}. gagal mengunduh: {err}")
                continue
        used.add((best["sumber"], best["id"]))
        alt = [{k: c[k] for k in ("sumber", "id", "url_halaman", "gambar", "durasi")} for c in found[1:4]]
        klip.append({"i": i, "kalimat": n["kalimat"], "visual": n.get("visual", ""), "kueri": q_used,
                     "durasi_butuh": needs[i], "file": name, **{k: v for k, v in best.items() if k != "unduh"},
                     "terlalu_pendek": best["durasi"] < needs[i], "alternatif": alt})
        print(f"[bima] {i + 1:02}. {name} ({best['durasi']} dtk, {best['lebar']}x{best['tinggi']}) ← \"{q_used}\"")

    manifest = {"slug": args.slug, "dibuat": datetime.now().isoformat(timespec="seconds"), "uji": args.uji,
                "kueri_inggris": english, "klip": sorted(klip, key=lambda k: k["i"]), "kurang": kurang}
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    credits = ["Kredit klip video (lisensi gratis, atribusi tidak wajib):", ""]
    credits += [f"{k['file']}: {k['pembuat'] or 'anonim'} / {k['sumber'].title()} — {k['url_halaman']}" for k in manifest["klip"]]
    (aset / "KREDIT.txt").write_text("\n".join(credits) + "\n", encoding="utf-8")

    short = [k["i"] + 1 for k in klip if k.get("terlalu_pendek")]
    print(f"[bima] {len(klip)}/{len(narasi)} kalimat punya klip.")
    if short:
        print(f"[bima] Catatan: klip kalimat {short} lebih pendek dari durasi bicaranya; editor akan memperlambat atau mengulang.")
    if kurang:
        print(f"[bima] Kurang: kalimat {kurang}. Perbaiki kata kunci di aset/kueri.json lalu jalankan lagi, atau taruh klip sendiri.")
        return
    if args.uji:
        print("[bima] selesai (uji, tidak ada yang diunduh)")
        return
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", args.slug, "aset", "--note", "klip dicari Bima"], check=True, cwd=ROOT)
    print(f"[bima] selesai: videos/{args.slug}/aset/")


if __name__ == "__main__":
    main()

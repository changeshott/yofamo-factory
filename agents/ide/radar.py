#!/usr/bin/env python3
"""Nova: radar topik GRATIS (tanpa token Claude). Mengambil berita teknologi terbaru dari RSS sumber tepercaya
(rilis universitas/lembaga riset & media sains), memberi skor "cocok untuk Yofamo", lalu menulis daftar pendek
yang dibaca Nova. Jadi Nova tidak perlu banyak web search untuk mencari kandidat → riset jauh lebih hemat token.

    python agents/ide/radar.py               # pakai cache kalau umurnya < 12 jam
    python agents/ide/radar.py --segar       # paksa ambil ulang
    python agents/ide/radar.py --hari 45     # hanya berita ≤ 45 hari
    python agents/ide/radar.py --uji         # data contoh (tanpa internet)

Hasil: insights/radar.json (lengkap) dan insights/radar.md (30 teratas, ringkas untuk dibaca Nova).
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / "insights" / "radar.json"
OUT_MD = ROOT / "insights" / "radar.md"
CONTOH = Path(__file__).with_name("contoh_rss.xml")
UA = "Mozilla/5.0 (YofamoRadar/1.0; +https://youtube.com/@yofamoo_technology)"

# (nama, url, tier) — tier 1 = rilis resmi lembaga/universitas, 2 = media sains bereputasi
FEEDS = [
    # (Nov 2026, permintaan Zona) fokus PRODUK & teknologi yang sudah ada/dijual/dipakai dan bisa diperlihatkan — bukan riset lab/NASA.
    ("The Verge", "https://www.theverge.com/rss/index.xml", 2),
    ("Engadget", "https://www.engadget.com/rss.xml", 2),
    ("Gizmodo", "https://gizmodo.com/feed", 2),
    ("Digital Trends", "https://www.digitaltrends.com/feed/", 2),
    ("Android Authority", "https://www.androidauthority.com/feed/", 2),
    ("GSMArena", "https://www.gsmarena.com/rss-news-reviews.php3", 2),
    ("Electrek (kendaraan listrik)", "https://electrek.co/feed/", 2),
    ("Interesting Engineering", "https://interestingengineering.com/feed", 2),
    ("New Atlas", "https://newatlas.com/index.rss", 2),
    ("TechCrunch Hardware", "https://techcrunch.com/category/hardware/feed/", 2),
    ("detikInet", "https://inet.detik.com/rss", 2),
    ("TechXplore", "https://techxplore.com/rss-feed/", 2),
]

# kata yang membuat topik "dekat & bisa diperlihatkan" untuk penonton Indonesia (bobot)
DEKAT = {
    r"\bfood|meat|drink|coffee|rice|kitchen|cook": ("makanan", 3), r"\bcloth|fabric|textile|shoe|wearable|jacket|shirt": ("pakaian", 3),
    r"\bhealth|patient|medical|disease|cancer|heart|brain|tooth|teeth|skin|blood|implant|prosthe|surgery|drug": ("kesehatan", 3),
    r"\bhome|house|window|wall|furniture|air condition|cooling": ("rumah", 2), r"\bphone|smartphone|battery|charg|screen|display|laptop": ("hp", 3),
    r"\bgame|gaming|vr\b|virtual reality|augmented|ar glasses": ("game", 2), r"\bcar|vehicle|drone|plane|aircraft|train|bike|motorcycle|ship": ("transportasi", 2),
    r"\brobot|humanoid|exoskeleton|gripper": ("robot", 3), r"\bsolar|energy|power|electricity|hydrogen": ("energi", 1),
    r"\bplastic|recycl|ocean|water|pollution|climate": ("lingkungan", 1), r"\bspace|moon|mars|satellite|rocket|asteroid|nasa|telescope|orbit|planet|galaxy": ("luar-angkasa", -3),
}
WOW = (r"\bfirst\b|world'?s|record|breakthrough|self-heal|invisible|shape-shift|liquid metal|levitat|tiny|micro|nano|"
       r"\bcan now\b|without\b|instantly|in seconds|mind|thought|regrow|3d.print|transparent|stronger than|faster than|"
       r"artificial (skin|muscle|eye|leaf)|smart (contact|glass|fabric|pill)|edible|glow")
PRODUK = (r"\blaunch|unveil|release[sd]?\b|on sale|available|pre-?order|price|priced|\$\d|costs?\b|hands-on|review|announc|"
          r"now ship|buy\b|rilis|harga|dijual|resmi|gadget|smartphone|app\b|feature|update")
RISET = r"\bresearchers?\b|scientists?\b|study\b|studies|university|laborator|\blab\b|journal|paper\b|could one day|may someday|in mice|proof.of.concept"
BUKTI_DEMO = r"\bdemonstrat|prototype|tested|trial|unveil|launch|on sale|available|video|built\b|developed"
ABSTRAK = (r"\bpolicy|survey|market|stock|funding|investment|earnings|layoff|lawsuit|election|regulation|opinion|"
           r"\btheor|simulation suggests|model predicts|review of|workshop|conference|award|appoint|webinar|podcast")


def ambil(url: str, timeout: int = 15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(3_000_000)


def bersih(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()


def tanggal(raw: str) -> datetime | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        d = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        try:
            d = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def parse(xml: bytes, sumber: str, tier: int) -> list[dict]:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []
    out = []
    ns_atom = "{http://www.w3.org/2005/Atom}"
    items = root.iter("item") if root.find(".//item") is not None else root.iter(f"{ns_atom}entry")
    for it in items:
        def g(*tags: str) -> str:
            for t in tags:
                e = it.find(t)
                if e is not None:
                    return e.get("href") or (e.text or "")
            return ""
        judul = bersih(g("title", f"{ns_atom}title"))
        link = g("link", f"{ns_atom}link").strip()
        if not judul or not link.startswith("http"):
            continue
        out.append({"judul": judul, "url": link, "sumber": sumber, "tier": tier,
                    "tanggal": (tanggal(g("pubDate", f"{ns_atom}published", f"{ns_atom}updated", "{http://purl.org/dc/elements/1.1/}date")) or datetime.now(timezone.utc)).isoformat(timespec="minutes"),
                    "ringkas": bersih(g("description", f"{ns_atom}summary", f"{ns_atom}content"))[:320]})
    return out


def skor(x: dict) -> dict:
    teks = f"{x['judul']} {x['ringkas']}".lower()
    kat, s, alasan = "lainnya", 0.0, []
    for pola, (nama, bobot) in DEKAT.items():
        if re.search(pola, teks):
            if bobot < 0:                      # antariksa: penalti (penonton channel ini lebih suka teknologi yang dekat)
                kat, s = nama, s + bobot
                continue
            if bobot > s:
                kat = nama
            s = max(s, bobot)
    if s:
        alasan.append(f"dekat:{kat}")
    if re.search(WOW, teks):
        s += 3
        alasan.append("wow")
    if re.search(PRODUK, teks):
        s += 3
        alasan.append("produk nyata/dijual")
    if re.search(RISET, teks):
        s -= 3
        alasan.append("masih riset")
    if re.search(BUKTI_DEMO, teks):
        s += 1.5
        alasan.append("ada demo/prototipe")
    if re.search(ABSTRAK, teks):
        s -= 4
        alasan.append("abstrak/bisnis")
    s += 1.0 if x["tier"] == 1 else 0.5
    umur = (datetime.now(timezone.utc) - datetime.fromisoformat(x["tanggal"])).days
    s += 1.5 if umur <= 14 else 0.5 if umur <= 45 else 0
    return {**x, "kategori": kat, "skor": round(s, 1), "alasan": alasan, "umur_hari": umur}


def kunci(j: str) -> str:
    return " ".join(sorted(set(re.findall(r"[a-z]{4,}", j.lower())))[:12])


def sudah_dibahas() -> list[set[str]]:
    """Judul channel & pabrik (bahasa campur) → set kata; dipakai untuk menurunkan kandidat yang mirip."""
    sys.path.insert(0, str(Path(__file__).parent))
    try:
        import cek_topik  # noqa: E402
        return [cek_topik.tokens(v.get("judul", "")) for v in cek_topik.existing()]
    except Exception:  # snapshot belum ada, dll.
        return []


def main() -> None:
    ap = argparse.ArgumentParser(description="Radar topik gratis untuk Nova")
    ap.add_argument("--segar", action="store_true")
    ap.add_argument("--hari", type=int, default=60)
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    if not a.segar and not a.uji and OUT_JSON.exists():
        lama = json.loads(OUT_JSON.read_text(encoding="utf-8"))
        umur = datetime.now() - datetime.fromisoformat(lama.get("dibuat", "2000-01-01T00:00"))
        if umur < timedelta(hours=12) and lama.get("kandidat"):          # hasil kosong (mis. internet mati) tidak dipakai ulang
            print(f"[radar] pakai cache ({umur.seconds // 3600} jam): {len(lama.get('kandidat', []))} kandidat → insights/radar.md")
            return
    semua, gagal = [], []
    if a.uji:
        semua = parse(CONTOH.read_bytes(), "Contoh", 1)
    else:
        def kerja(f: tuple[str, str, int]):
            try:
                return parse(ambil(f[1]), f[0], f[2]), None
            except Exception as err:  # satu feed mati tidak menghentikan radar
                return [], f"{f[0]}: {str(err)[:60]}"
        with ThreadPoolExecutor(6) as ex:
            for items, err in ex.map(kerja, FEEDS):
                semua += items
                if err:
                    gagal.append(err)
    batas = datetime.now(timezone.utc) - timedelta(days=a.hari if not a.uji else 99999)
    unik, lihat = [], set()
    for x in semua:
        k = kunci(x["judul"])
        if k in lihat or datetime.fromisoformat(x["tanggal"]) < batas:
            continue
        lihat.add(k)
        unik.append(skor(x))
    lama = sudah_dibahas()
    for x in unik:
        kata = set(re.findall(r"[a-z]{4,}", x["judul"].lower()))
        if any(len(kata & t) >= 2 for t in lama if t):
            x["skor"] -= 3
            x["alasan"].append("mirip judul lama?")
    unik.sort(key=lambda x: -x["skor"])
    data = {"dibuat": datetime.now().isoformat(timespec="minutes"), "jumlah": len(unik), "gagal": gagal, "kandidat": unik[:80]}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    L = [f"# Radar topik Nova — {data['dibuat']}", "",
         f"{len(unik)} berita ≤ {a.hari} hari dari {len(FEEDS) - len(gagal)}/{len(FEEDS)} sumber. Skor = dekat + produk nyata + wow + demo + segar − riset/antariksa − abstrak.", "",
         "| # | skor | kategori | judul (sumber, tanggal) | link |", "| --- | --- | --- | --- | --- |"]
    for n, x in enumerate(unik[:30], 1):
        L.append(f"| {n} | {x['skor']} | {x['kategori']} | {x['judul'][:110]} ({x['sumber']}, T{x['tier']}, {x['tanggal'][:10]}) | {x['url']} |")
    if gagal:
        L += ["", "Feed gagal: " + "; ".join(gagal)]
    OUT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[radar] {len(unik)} kandidat ({len(gagal)} feed gagal) → insights/radar.md (30 teratas)")
    for x in unik[:5]:
        print(f"[radar]   {x['skor']:>4} {x['kategori']:<12} {x['judul'][:90]}")


if __name__ == "__main__":
    main()

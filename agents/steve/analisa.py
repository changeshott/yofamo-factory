#!/usr/bin/env python3
"""Steve: mesin analisa. Menggabungkan SEMUA data yang ada menjadi angka siap pakai, supaya laporan Steve
berbasis hitungan (bukan kira-kira) dan setiap kesimpulan punya jumlah sampel.

    python agents/steve/analisa.py        # → insights/raw/analisa-YYYY-MM-DD.json + .md (ringkasan untuk dibaca Steve)

Sumber (yang tidak ada dilewati dan dicatat di "data_kurang"):
  insights/raw/YYYY-MM-DD.json   snapshot publik harian (fetch_stats.py)  → KPI, pertumbuhan, momentum
  insights/raw/analitik-*.json   YouTube Analytics (analitik.py, butuh login Uli) → retensi, traffic, audiens
  insights/raw/komentar-*.json   komentar publik (komentar.py) → permintaan & keluhan penonton
  insights/raw/pasar-*.json      radar Shorts teknologi Indonesia (pasar.py) → peluang topik
  videos/*/                      ciri produksi video pabrik (durasi, porsi AI, suasana, skor QC, timing kalimat)
"""
from __future__ import annotations

import json
import re
import statistics as st
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "ide"))
import ytdata  # noqa: E402
from cek_topik import tokens  # noqa: E402

ROOT = ytdata.ROOT
WIB = timezone(timedelta(hours=7))
HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
KATEGORI = {
    "makanan": "daging steak makanan minum minuman air sayur kebun pertanian buah kopi susu masak nasi",
    "pakaian": "baju pakaian kain rajut sepatu jaket motif kaos",
    "kesehatan": "dokter jantung organ kulit obat medis sakit gigi tubuh darah tulang pasien rumah-sakit",
    "otak/abstrak": "mimpi pikiran telepati otak baca",
    "rumah": "rumah tanaman lampu kasur dapur hutan",
    "game": "game fps gaming main",
    "hp/gadget": "hp layar ponsel earbud headset speaker kacamata gadget retak",
    "transportasi": "mobil motor pesawat terbang kereta drone",
    "robot": "robot rangka exoskeleton terminator anjing",
    "sains/alam": "purba jurassic hewan nitrogen beku mayat benda teringan kapas",
}
FILM = re.compile(r"iron ?man|spider-?man|superhero|avatar|terminator|jurassic|cyborg|marvel|sci-?fi", re.I)


def q(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        return 0.0
    k = (len(xs) - 1) * p
    lo, hi = int(k), min(int(k) + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (k - lo)


def label(n: int) -> str:
    return "terbukti" if n >= 5 else "dugaan" if n >= 2 else "1 video"


def kategori(judul: str) -> str:
    t = tokens(judul) | set(re.findall(r"[a-z0-9]+", judul.lower()))
    best, score = "lainnya", 0
    for k, kata in KATEGORI.items():
        s = len(t & set(kata.split()))
        if s > score:
            best, score = k, s
    return best


def fitur(judul: str) -> dict[str, bool]:
    j = re.sub(r"#\w+", "", judul).strip()
    huruf = [c for c in j if c.isalpha()]
    caps = sum(c.isupper() for c in huruf) / max(1, len(huruf))
    return {"tanya_kaget (?!)": "?!" in j, "tanda tanya": "?" in j, "seru (!)": "!" in j, "ada angka": bool(re.search(r"\d", j)),
            "referensi film/superhero": bool(FILM.search(j)), "kapital dominan": caps > 0.5, "judul pendek (<55 huruf)": len(j) < 55,
            "kata 'nyata/beneran'": bool(re.search(r"nyata|beneran|asli", j, re.I))}


def ringkas(vals: list[float]) -> dict:
    return {"n": len(vals), "median": round(st.median(vals), 2) if vals else None, "label": label(len(vals))}


def main() -> None:
    snaps = ytdata.snapshots()
    if not snaps:
        sys.exit("[steve] belum ada snapshot; jalankan fetch_stats.py dulu")
    hist = [ytdata.read(p) for p in snaps]
    cur, first = hist[-1], hist[0]
    prev = hist[-2] if len(hist) > 1 else None
    shorts = [v for v in cur["videos"] if v.get("is_short")]
    kurang = []
    if len(hist) < 7:
        kurang.append(f"baru {len(hist)} snapshot harian; kurva pertumbuhan makin akurat setelah ±7 hari berturut-turut")

    # ---------------- KPI
    sub_now, sub_first = cur["channel"]["subscribers"], first["channel"]["subscribers"]
    hari_data = max(1, (date.fromisoformat(cur["snapshot_date"]) - date.fromisoformat(first["snapshot_date"])).days)
    views_sorted = sorted(shorts, key=lambda v: v["published"], reverse=True)
    terakhir = views_sorted[0]["published"] if views_sorted else None
    gap = (date.today() - date.fromisoformat(terakhir)).days if terakhir else None
    upl30 = sum(1 for v in shorts if (date.today() - date.fromisoformat(v["published"])).days <= 30)
    med_all = st.median([v["views"] for v in shorts]) if shorts else 0
    last10, prev10 = views_sorted[:10], views_sorted[10:20]
    kpi = {
        "subscriber": sub_now, "subscriber_berubah": sub_now - (prev or cur)["channel"]["subscribers"] if prev else None,
        "subscriber_per_hari": round((sub_now - sub_first) / hari_data, 2) if len(hist) > 1 else None,
        "total_views": cur["channel"]["total_views"], "shorts": len(shorts), "median_views_shorts": med_all,
        "median_10_terbaru": st.median([v["views"] for v in last10]) if last10 else None,
        "median_10_sebelumnya": st.median([v["views"] for v in prev10]) if prev10 else None,
        "upload_30_hari": upl30, "hari_sejak_upload": gap, "upload_terakhir": terakhir,
        "views_baru_sejak_snapshot_sebelumnya": sum(v.get("views_since_last") or 0 for v in shorts) if prev else None,
    }
    analitik = ytdata.read(ytdata.latest("analitik"))
    if analitik.get("harian"):
        net = [int(d.get("subscribersGained", 0)) - int(d.get("subscribersLost", 0)) for d in analitik["harian"][-28:]]
        kpi["subscriber_bersih_28_hari"] = sum(net)
        kpi["subscriber_per_hari"] = round(sum(net) / max(1, len(net)), 2)
        kpi["views_28_hari"] = sum(int(d.get("views", 0)) for d in analitik["harian"][-28:])
    rate = kpi.get("subscriber_per_hari") or 0
    kpi["proyeksi"] = {str(m): (round((m - sub_now) / rate) if rate > 0 else None) for m in (2000, 5000, 10000) if m > sub_now}

    # ---------------- momentum & pertumbuhan (dari semua snapshot)
    series: dict[str, list[tuple[str, int]]] = {}
    for h in hist:
        for v in h["videos"]:
            series.setdefault(v["id"], []).append((h["snapshot_date"], v["views"]))
    momentum = []
    for v in shorts:
        s = series.get(v["id"], [])
        if len(s) >= 2:
            d = max(1, (date.fromisoformat(s[-1][0]) - date.fromisoformat(s[0][0])).days)
            momentum.append({"judul": v["title"][:80], "views": v["views"], "tambah": s[-1][1] - s[0][1], "per_hari_periode": round((s[-1][1] - s[0][1]) / d, 1)})
    momentum.sort(key=lambda x: -x["tambah"])

    # ---------------- pola: kategori, judul, durasi, waktu upload
    for v in shorts:
        v["_kat"] = kategori(v["title"])
    kat = {}
    for k in sorted({v["_kat"] for v in shorts}):
        grp = [v for v in shorts if v["_kat"] == k]
        r = [v["vs_median"] for v in grp if v.get("vs_median") is not None]
        kat[k] = {**ringkas(r), "views_p25": round(q([v["views"] for v in grp], 0.25)), "views_median": round(st.median([v["views"] for v in grp])),
                  "views_p75": round(q([v["views"] for v in grp], 0.75)), "contoh": [v["title"][:60] for v in grp[:3]]}
    judul = {}
    for f in fitur("x"):
        ya = [v["vs_median"] for v in shorts if fitur(v["title"])[f] and v.get("vs_median") is not None]
        tidak = [v["vs_median"] for v in shorts if not fitur(v["title"])[f] and v.get("vs_median") is not None]
        if ya and tidak:
            judul[f] = {"dengan": ringkas(ya), "tanpa": ringkas(tidak),
                        "selisih": round(st.median(ya) - st.median(tidak), 2)}
    dur = {}
    for nama, lo, hi in [("<35 dtk", 0, 35), ("35–45 dtk", 35, 45), ("45–55 dtk", 45, 55), (">55 dtk", 55, 999)]:
        dur[nama] = ringkas([v["vs_median"] for v in shorts if lo <= v.get("duration_s", 0) < hi and v.get("vs_median") is not None])
    waktu = {"hari": {}, "jam": {}}
    for v in shorts:
        if not v.get("published_at"):
            continue
        t = datetime.fromisoformat(v["published_at"].replace("Z", "+00:00")).astimezone(WIB)
        waktu["hari"].setdefault(HARI[t.weekday()], []).append(v["vs_median"])
        slot = f"{(t.hour // 3) * 3:02d}–{(t.hour // 3) * 3 + 3:02d} WIB"
        waktu["jam"].setdefault(slot, []).append(v["vs_median"])
    if waktu["hari"]:
        waktu = {g: {k: ringkas([x for x in vs if x is not None]) for k, vs in d.items()} for g, d in waktu.items()}
    else:
        waktu = None
        kurang.append("jam upload belum tercatat (snapshot lama); otomatis tersedia mulai snapshot berikutnya")

    # ---------------- retensi & audiens (YouTube Analytics)
    ret = None
    if analitik.get("videos"):
        vs = analitik["videos"]
        avp = [float(v.get("averageViewPercentage", 0)) for v in vs if v.get("views", 0) >= 50]
        ret = {"rata_persen_ditonton": round(st.mean(avp), 1) if avp else None,
               "terbaik": sorted(({"judul": v.get("judul", v["video"])[:60], "persen": round(float(v.get("averageViewPercentage", 0)), 1), "views": v.get("views")} for v in vs if v.get("views", 0) >= 50), key=lambda x: -x["persen"])[:5],
               "terburuk": sorted(({"judul": v.get("judul", v["video"])[:60], "persen": round(float(v.get("averageViewPercentage", 0)), 1), "views": v.get("views")} for v in vs if v.get("views", 0) >= 50), key=lambda x: x["persen"])[:5],
               "kurva": []}
        by_id = {v["video"]: v for v in vs}
        for vid, curve in (analitik.get("retensi") or {}).items():
            if not curve:
                continue
            awal = next((c[1] for c in curve if c[0] >= 0.1), curve[0][1])
            drops = sorted(((curve[i - 1][1] - curve[i][1], curve[i][0]) for i in range(1, len(curve))), reverse=True)[:2]
            info = {"judul": by_id.get(vid, {}).get("judul", vid)[:60], "bertahan_10_persen_awal": round(awal, 2),
                    "akhir": round(curve[-1][1], 2), "drop_terbesar": [{"di": f"{d[1]:.0%}", "turun": round(d[0], 2)} for d in drops]}
            pab = (by_id.get(vid) or {}).get("pabrik")
            if pab and pab.get("slug"):
                w = ytdata.read(ROOT / "videos" / pab["slug"] / "words.json")
                dur_v = float(w.get("durasi") or 0)
                for d in info["drop_terbesar"]:
                    t = float(d["di"].rstrip("%")) / 100 * dur_v
                    k = next((x for x in w.get("kalimat", []) if x["mulai"] <= t <= x["selesai"] + 0.3), None)
                    if k:
                        d["kalimat"] = f"kalimat {k['i'] + 1}: {k['kalimat'][:70]}"
            ret["kurva"].append(info)
        tr = analitik.get("sumber_traffic") or []
        tot = sum(int(x.get("views", 0)) for x in tr) or 1
        ret["sumber_traffic"] = [{"sumber": x["insightTrafficSourceType"], "persen": round(int(x["views"]) / tot * 100, 1)} for x in tr[:6]]
        ret["demografi"] = (analitik.get("demografi") or [])[:6]
        ret["negara"] = (analitik.get("negara") or [])[:5]
        pabrik_vs = [v for v in vs if v.get("pabrik")]
        if pabrik_vs:
            ret["pabrik"] = [{"judul": v.get("judul", "")[:50], "persen": round(float(v.get("averageViewPercentage", 0)), 1), "views": v.get("views"),
                              **{k: v["pabrik"].get(k) for k in ("durasi", "porsi_ai", "porsi_footage", "shot", "suasana", "skor_qc", "kategori")}} for v in pabrik_vs]
    else:
        kurang.append("belum ada data YouTube Analytics (retensi, sumber traffic, audiens). Hubungkan YouTube di meja Uli, lalu jalankan analitik.py")

    # ---------------- suara penonton
    kom = ytdata.read(ytdata.latest("komentar"))
    komentar = None
    if kom:
        komentar = {"jumlah": kom.get("komentar"), "permintaan": sorted(kom.get("permintaan", []), key=lambda k: -k["like"])[:10],
                    "pertanyaan": sorted(kom.get("pertanyaan", []), key=lambda k: -k["like"])[:8], "kritik": sorted(kom.get("kritik", []), key=lambda k: -k["like"])[:8]}
    else:
        kurang.append("belum ada data komentar (komentar.py)")

    # ---------------- peluang pasar: ramai di channel lain, belum dibahas Yofamo
    pasar = ytdata.read(ytdata.latest("pasar"))
    peluang = None
    if pasar:
        mine = [tokens(v["title"]) for v in cur["videos"]]
        peluang = []
        for v in pasar.get("video", []):
            t = tokens(v["judul"])
            mirip = max((len(t & m) / max(1, min(len(t), len(m))) for m in mine if t & m), default=0)
            if mirip < 0.5:
                peluang.append({**{k: v[k] for k in ("judul", "channel", "views", "views_per_hari", "terbit", "url")}, "kategori": kategori(v["judul"])})
        peluang = peluang[:20]
        pk = {}
        for v in pasar.get("video", []):
            pk.setdefault(kategori(v["judul"]), []).append(v["views_per_hari"])
        pasar_kat = {k: {"n": len(x), "median_views_per_hari": round(st.median(x))} for k, x in sorted(pk.items(), key=lambda kv: -st.median(kv[1]))}
    else:
        pasar_kat = None
        kurang.append("belum ada radar pasar (pasar.py, mingguan)")

    hasil = {"tanggal": date.today().isoformat(), "snapshot": cur["snapshot_date"], "jumlah_snapshot": len(hist), "kpi": kpi,
             "momentum": momentum[:8], "kategori": kat, "judul": judul, "durasi": dur, "waktu_upload": waktu, "retensi": ret,
             "komentar": komentar, "pasar_per_kategori": pasar_kat, "peluang_pasar": peluang, "data_kurang": kurang}
    out = ytdata.RAW / f"analisa-{date.today().isoformat()}.json"
    out.write_text(json.dumps(hasil, ensure_ascii=False, indent=2), encoding="utf-8")
    (ytdata.RAW / f"analisa-{date.today().isoformat()}.md").write_text(brief(hasil), encoding="utf-8")
    print(f"[steve] analisa → {out.relative_to(ROOT)} (+ .md). Sumber kurang: {len(kurang)}")
    print(brief(hasil)[:1800])


def brief(h: dict) -> str:
    k = h["kpi"]
    L = [f"# Data brief Steve — {h['tanggal']}", "",
         f"**KPI:** {k['subscriber']} subscriber ({k['subscriber_per_hari'] if k['subscriber_per_hari'] is not None else '?'}/hari) · {k['shorts']} Shorts · "
         f"median {k['median_views_shorts']:.0f} views · upload 30 hari: {k['upload_30_hari']} · {k['hari_sejak_upload']} hari sejak upload terakhir"]
    if k.get("median_10_terbaru") is not None and k.get("median_10_sebelumnya") is not None:
        L.append(f"**Tren:** median 10 Shorts terbaru {k['median_10_terbaru']:.0f} vs 10 sebelumnya {k['median_10_sebelumnya']:.0f}")
    if k.get("proyeksi"):
        L.append("**Proyeksi subscriber:** " + ", ".join(f"{m} dalam {d} hari" if d else f"{m}: laju 0, belum bisa diproyeksi" for m, d in k["proyeksi"].items()))
    L += ["", "## Kategori (vs median channel)", "| kategori | n | median × | views p25–p75 | label |", "|---|---|---|---|---|"]
    for n, v in sorted(h["kategori"].items(), key=lambda kv: -(kv[1]["median"] or 0)):
        L.append(f"| {n} | {v['n']} | {v['median']} | {v['views_p25']}–{v['views_p75']} | {v['label']} |")
    L += ["", "## Fitur judul (median × dengan vs tanpa)"]
    for n, v in sorted(h["judul"].items(), key=lambda kv: -abs(kv[1]["selisih"])):
        L.append(f"- {n}: {v['dengan']['median']} (n={v['dengan']['n']}) vs {v['tanpa']['median']} (n={v['tanpa']['n']}) → selisih {v['selisih']:+}")
    L += ["", "## Durasi"] + [f"- {n}: median × {v['median']} (n={v['n']}, {v['label']})" for n, v in h["durasi"].items() if v["n"]]
    if h["momentum"]:
        L += ["", "## Momentum (views bertambah selama periode snapshot)"] + [f"- +{m['tambah']} {m['judul']}" for m in h["momentum"][:5]]
    if h["retensi"]:
        r = h["retensi"]
        L += ["", f"## Retensi: rata-rata ditonton {r['rata_persen_ditonton']}%"]
        L += [f"- terbaik {x['persen']}% {x['judul']}" for x in r["terbaik"][:3]] + [f"- terburuk {x['persen']}% {x['judul']}" for x in r["terburuk"][:3]]
        for c in r["kurva"][:6]:
            L.append(f"- kurva {c['judul']}: bertahan {c['bertahan_10_persen_awal']} di 10% awal; drop terbesar " + "; ".join(f"{d['di']} (-{d['turun']}){' ' + d['kalimat'] if d.get('kalimat') else ''}" for d in c["drop_terbesar"]))
        if r.get("sumber_traffic"):
            L.append("- traffic: " + ", ".join(f"{x['sumber']} {x['persen']}%" for x in r["sumber_traffic"]))
    if h["komentar"]:
        c = h["komentar"]
        L += ["", f"## Komentar ({c['jumlah']})"] + [f"- minta: \"{x['teks'][:90]}\" ({x['like']} like)" for x in c["permintaan"][:5]] + [f"- kritik: \"{x['teks'][:90]}\"" for x in c["kritik"][:3]]
    if h["peluang_pasar"]:
        L += ["", "## Peluang pasar (ramai di channel lain, belum dibahas Yofamo)"] + [f"- {p['views_per_hari']:.0f}/hari · {p['kategori']} · {p['judul'][:80]} ({p['channel']})" for p in h["peluang_pasar"][:8]]
    L += ["", "## Data yang belum ada"] + [f"- {x}" for x in h["data_kurang"]]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Steve — evaluasi pasca-tayang otomatis (tanpa kuota Claude): tiap video buatan pabrik yang sudah tayang ≥ 48 jam
dibandingkan dengan median channel, lalu dicari resep yang menang/kalah.

    python agents/steve/pascatayang.py     # → insights/pascatayang.md + insights/raw/pascatayang-YYYY-MM-DD.json + insights/bobot-ide.json

Sumber (yang tidak ada dilewati, tidak pernah dikarang):
  insights/raw/YYYY-MM-DD.json   views tiap video (snapshot terbaru Steve)
  insights/raw/analitik-*.json   % ditonton, hook (penonton di 10% awal) — kalau YouTube terhubung
  videos/<slug>/…                ciri produksi: kategori, status teknologi, produk, suara, durasi, porsi footage, skor QC, produk_terlihat

Hasil:
  pascatayang.md   daftar video terbaru vs median + pola per ciri (kategori, status, suara, porsi footage, produk terlihat).
                   Kurang dari 5 video per kelompok = "dugaan". Dibaca Nova, Raka, Bima sebelum membuat video berikutnya.
  bobot-ide.json   pengali hasil nyata per status teknologi & kategori (hanya kelompok dengan ≥ 5 video) → dipakai cek_ide.py
                   menggantikan bonus tetap, supaya skor ide mengikuti apa yang benar-benar ditonton.
"""
from __future__ import annotations

import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insights" / "raw"
MIN_N = 5            # aturan pabrik: < 5 video bukan pola
MIN_JAM = 48


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def terbaru(pola: str) -> dict:
    fs = sorted(RAW.glob(pola)) if RAW.is_dir() else []
    return rj(fs[-1]) if fs else {}


def snapshot() -> dict:
    fs = sorted(f for f in RAW.glob("20*.json")) if RAW.is_dir() else []
    return rj(fs[-1]) if fs else {}


def kelompok_footage(p: float | None) -> str | None:
    return None if p is None else ("footage ≥ 80%" if p >= 0.8 else "footage 50–79%" if p >= 0.5 else "footage < 50%")


def kumpulkan() -> list[dict]:
    snap = snapshot()
    views = {v.get("id"): v for v in snap.get("videos") or []}
    med = float((snap.get("summary") or {}).get("median_views") or 0)
    an = terbaru("analitik-*.json")
    an_v = {v.get("video"): v for v in an.get("videos") or []}
    ret = an.get("retensi") or {}
    out = []
    for up_f in sorted((ROOT / "videos").glob("*/export/upload.json")):
        vdir, up = up_f.parents[1], rj(up_f)
        vid = up.get("videoId")
        v = views.get(vid)
        if not vid or vid == "UJI" or up.get("dibatalkan") or not v:
            continue
        if float(v.get("age_days") or 0) * 24 < MIN_JAM:
            continue
        idea, sc, w = rj(vdir / "idea.json"), rj(vdir / "script.json"), rj(vdir / "words.json")
        qc, man = rj(vdir / "export" / "qc_review.json"), rj(vdir / "aset" / "manifest.json")
        klip = man.get("klip") or []
        porsi = (sum(1 for k in klip if k.get("jenis") == "footage") / len(klip)) if klip else None
        a = an_v.get(vid) or {}
        kurva = ret.get(vid) or []
        hook = next((r[1] for r in kurva if r[0] >= 0.1), None)            # rasio penonton yang masih ada di 10% awal
        suara = str(w.get("suara") or "")
        out.append({
            "slug": vdir.name, "videoId": vid, "judul": v.get("title") or sc.get("judul") or vdir.name, "umur_hari": v.get("age_days"),
            "views": int(v.get("views") or 0), "vs_median": round(int(v.get("views") or 0) / med, 2) if med else None,
            "ditonton_persen": a.get("averageViewPercentage"), "hook_10": round(hook, 3) if hook is not None else None,
            "kategori": idea.get("kategori"), "status": idea.get("status_teknologi"), "produk": idea.get("produk"),
            "suara": "William" if "William" in suara else "Emma" if "Emma" in suara else "Ardi" if "Ardi" in suara else "Gadis" if "Gadis" in suara else (suara or None),
            "durasi": w.get("durasi"), "porsi_footage": round(porsi, 2) if porsi is not None else None,
            "skor_qc": qc.get("skor"), "produk_terlihat": qc.get("produk_terlihat"),
            "antariksa": idea.get("kategori") == "luar-angkasa",
        })
    return sorted(out, key=lambda x: x.get("umur_hari") or 0)


def pola(videos: list[dict], kunci, nama: str) -> list[dict]:
    grup: dict[str, list[dict]] = {}
    for v in videos:
        k = kunci(v)
        if k is not None and k != "" and v.get("vs_median") is not None:
            grup.setdefault(str(k), []).append(v)
    out = []
    for k, vs in grup.items():
        tonton = [x["ditonton_persen"] for x in vs if x.get("ditonton_persen") is not None]
        out.append({"ciri": nama, "nilai": k, "n": len(vs), "median_x": round(statistics.median(x["vs_median"] for x in vs), 2),
                    "ditonton": round(statistics.median(tonton), 1) if tonton else None, "label": "pola" if len(vs) >= MIN_N else "dugaan"})
    return sorted(out, key=lambda r: -r["median_x"])


def main() -> None:
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    vs = kumpulkan()
    semua = (pola(vs, lambda v: v.get("kategori"), "kategori") + pola(vs, lambda v: v.get("status"), "status teknologi")
             + pola(vs, lambda v: v.get("suara"), "suara") + pola(vs, lambda v: kelompok_footage(v.get("porsi_footage")), "porsi footage")
             + pola(vs, lambda v: None if v.get("produk_terlihat") is None else ("produk terlihat ≥ 50%" if v["produk_terlihat"] >= 0.5 else "produk terlihat < 50%"), "produk terlihat")
             + pola(vs, lambda v: "ada nama produk" if v.get("produk") else "tanpa nama produk", "produk di ide"))
    RAW.mkdir(parents=True, exist_ok=True)
    hari = date.today().isoformat()
    (RAW / f"pascatayang-{hari}.json").write_text(json.dumps({"dibuat": hari, "video": vs, "pola": semua}, ensure_ascii=False, indent=1), encoding="utf-8")
    # bobot skor ide dari hasil nyata: hanya kelompok dengan cukup video
    bobot = {"dibuat": hari, "min_video": MIN_N, "status": {}, "kategori": {},
             "catatan": "pengali views vs median channel per kelompok (video buatan pabrik ≥ 48 jam tayang); dipakai agents/ide/cek_ide.py"}
    for r in semua:
        if r["n"] >= MIN_N and r["ciri"] in ("status teknologi", "kategori"):
            bobot["status" if r["ciri"] == "status teknologi" else "kategori"][r["nilai"]] = {"x": r["median_x"], "n": r["n"]}
    (ROOT / "insights" / "bobot-ide.json").write_text(json.dumps(bobot, ensure_ascii=False, indent=1), encoding="utf-8")

    L = [f"# Evaluasi pasca-tayang — {hari}", "",
         f"{len(vs)} video buatan pabrik sudah tayang ≥ {MIN_JAM} jam. Angka dari snapshot Steve & YouTube Analytics; "
         "× = views dibanding median channel. Kelompok < 5 video = **dugaan**, bukan pola.", ""]
    if not vs:
        L += ["Data belum cukup: belum ada video pabrik yang tayang ≥ 48 jam dengan data views.", ""]
    else:
        L += ["## 10 video terbaru", "", "| Video | Umur | Views | × median | Ditonton | Hook 10% | Kategori | Status | Suara | Footage | Produk terlihat |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        f = lambda x, s="": "-" if x is None else f"{x}{s}"  # noqa: E731
        for v in vs[:10]:
            L.append(f"| {str(v['judul'])[:46]} | {f(v['umur_hari'], ' hr')} | {v['views']} | {f(v['vs_median'], '×')} | {f(v['ditonton_persen'], '%')} | "
                     f"{f(None if v['hook_10'] is None else round(v['hook_10'] * 100), '%')} | {f(v['kategori'])} | {f(v['status'])} | {f(v['suara'])} | "
                     f"{f(None if v['porsi_footage'] is None else round(v['porsi_footage'] * 100), '%')} | {f(None if v['produk_terlihat'] is None else round(v['produk_terlihat'] * 100), '%')} |")
        L += ["", "## Resep: apa yang menang", "", "| Ciri | Nilai | Video | × median | Ditonton | |", "|---|---|---|---|---|---|"]
        for r in semua:
            L.append(f"| {r['ciri']} | {r['nilai']} | {r['n']} | {r['median_x']}× | {f(r['ditonton'], '%')} | {r['label']} |")
        kuat = [r for r in semua if r["label"] == "pola"]
        L += ["", "## Untuk Nova, Raka & Bima", ""]
        if kuat:
            for ciri in dict.fromkeys(r["ciri"] for r in kuat):
                g = [r for r in kuat if r["ciri"] == ciri]
                if len(g) >= 2:
                    L.append(f"- **{ciri}**: terbaik *{g[0]['nilai']}* ({g[0]['median_x']}×, n={g[0]['n']}), terlemah *{g[-1]['nilai']}* ({g[-1]['median_x']}×, n={g[-1]['n']}).")
        else:
            L.append("- Belum ada kelompok dengan ≥ 5 video: perlakukan semua baris di atas sebagai dugaan, jangan mengubah resep secara ekstrem.")
        L.append("- Video dengan × median < 0,6: cek hook 10% & porsi footage-nya dulu sebelum menyalahkan topiknya.")
    (ROOT / "insights" / "pascatayang.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"[steve] pasca-tayang: {len(vs)} video, {sum(1 for r in semua if r['label'] == 'pola')} pola (≥ {MIN_N} video) → insights/pascatayang.md, insights/bobot-ide.json")


if __name__ == "__main__":
    main()

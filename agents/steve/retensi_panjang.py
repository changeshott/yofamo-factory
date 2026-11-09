#!/usr/bin/env python3
"""Steve — retensi video panjang per BAB dan per ADEGAN (tanpa kuota Claude).

    python agents/steve/retensi_panjang.py            # → insights/panjang-retensi.md + insights/raw/retensi-panjang-YYYY-MM-DD.json

Sumber: kurva retensi YouTube Analytics di insights/raw/analitik-*.json terbaru (agents/steve/analitik.py) untuk video
yang diupload dari panjang/<slug>/ (export/upload.json). Kurva (posisi 0–1 → rasio penonton yang masih menonton) dipetakan ke
waktu tiap bab (export/info.json → bab) dan tiap adegan (info.json → mulai_adegan, cadangan: suara/waktu.json).

Hasil untuk Bayu & Citra: hook 30 detik, bab yang paling banyak ditinggal, 3 adegan dengan penurunan tercuram (jenis + kutipan
narasi), dan rata-rata penurunan per menit untuk tiap jenis adegan (footage vs motion graphic). Kurang dari 5 video = "dugaan".
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insights" / "raw"
OUT_MD = ROOT / "insights" / "panjang-retensi.md"
NAMA_JENIS = {"footage": "footage", "pembuka": "pembuka", "kata": "kata serif", "angka": "angka", "cara_kerja": "cara kerja",
              "banding": "perbandingan", "garis_waktu": "garis waktu", "objek": "objek", "hp": "mockup HP", "tv": "TV retro",
              "judul_bab": "kartu bab", "penutup": "penutup"}


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def kurva_di(kurva: list[list[float]], x: float) -> float | None:
    """Rasio penonton pada posisi x (0–1), interpolasi linear antar titik YouTube (biasanya tiap 1%)."""
    if not kurva:
        return None
    x = max(0.0, min(1.0, x))
    pts = sorted((float(p[0]), float(p[1])) for p in kurva)
    if x <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * ((x - x0) / (x1 - x0) if x1 > x0 else 0)
    return pts[-1][1]


def mulai_adegan(vdir: Path, info: dict, n: int, total: float) -> list[float]:
    m = info.get("mulai_adegan")
    if isinstance(m, list) and len(m) == n:
        return [float(x) for x in m]
    w = rj(vdir / "suara" / "waktu.json")                  # cadangan: durasi suara tiap adegan, diskalakan ke durasi video
    dur = [float((w.get(str(i)) or {}).get("durasi") or 3.0) for i in range(n)]
    k = total / (sum(dur) or 1)
    return [sum(dur[:i]) * k for i in range(n)]


def analisa_video(vid: str, kurva: list, vdir: Path, meta: dict) -> dict | None:
    info, naskah = rj(vdir / "export" / "info.json"), rj(vdir / "naskah.json")
    total = float(info.get("durasi") or 0)
    adegan = naskah.get("adegan") or []
    if total <= 0 or not adegan or not kurva:
        return None
    at = lambda t: kurva_di(kurva, t / total)  # noqa: E731
    mulai = mulai_adegan(vdir, info, len(adegan), total)
    rows = []
    for i, ad in enumerate(adegan):
        t0, t1 = mulai[i], (mulai[i + 1] if i + 1 < len(adegan) else total)
        if t1 - t0 < 1.0:
            continue
        y0, y1 = at(t0), at(t1)
        rows.append({"adegan": i + 1, "jenis": ad.get("jenis"), "mulai": round(t0, 1), "durasi": round(t1 - t0, 1),
                     "retensi_awal": round(y0, 3), "retensi_akhir": round(y1, 3), "turun": round(y0 - y1, 3),
                     "turun_per_menit": round((y0 - y1) / ((t1 - t0) / 60), 3),
                     "pergi_per_menit": round(((y0 - y1) / y0 if y0 else 0) / ((t1 - t0) / 60), 3),
                     "narasi": str(ad.get("narasi") or ad.get("judul") or ad.get("teks_layar") or "")[:110]})
    bab = info.get("bab") or [{"t": 0, "judul": "Pembuka"}]
    bab_rows = []
    for k, b in enumerate(bab):
        t0, t1 = float(b["t"]), (float(bab[k + 1]["t"]) if k + 1 < len(bab) else total)
        if t1 - t0 < 3:
            continue
        y0, y1 = at(t0), at(t1)
        bab_rows.append({"bab": b.get("judul"), "mulai": round(t0, 1), "retensi_awal": round(y0, 3), "retensi_akhir": round(y1, 3),
                         "turun": round(y0 - y1, 3), "turun_per_menit": round((y0 - y1) / ((t1 - t0) / 60), 3),
                         "pergi_per_menit": round(((y0 - y1) / y0 if y0 else 0) / ((t1 - t0) / 60), 3)})
    # adegan tercuram: abaikan 20 detik pertama (penurunan alami awal video dihitung terpisah sebagai hook)
    tengah = [r for r in rows if r["mulai"] >= 20 and r["durasi"] >= 4]
    return {"videoId": vid, "slug": vdir.name, "judul": naskah.get("judul") or vdir.name, "durasi": round(total, 1),
            "views": meta.get("views"), "rata_ditonton_persen": meta.get("averageViewPercentage"), "terbit": meta.get("terbit"),
            "hook_30_detik": round(at(min(30.0, total)), 3), "akhir": round(at(total * 0.98), 3),
            "bab": bab_rows, "adegan": rows, "tercuram": sorted(tengah, key=lambda r: -r["pergi_per_menit"])[:3]}


def main() -> None:
    files = sorted(RAW.glob("analitik-*.json"))
    if not files:
        sys.exit("[steve] belum ada insights/raw/analitik-*.json (jalankan agents/steve/analitik.py, butuh login YouTube)")
    data = rj(files[-1])
    retensi, meta = data.get("retensi") or {}, {v.get("video"): v for v in data.get("videos") or []}
    hasil = []
    for up_f in sorted((ROOT / "panjang").glob("*/export/upload.json")):
        up = rj(up_f)
        vid = up.get("manual_videoId") or (None if up.get("dibatalkan") else up.get("videoId"))
        if vid and vid in retensi:
            r = analisa_video(vid, retensi[vid], up_f.parents[1], meta.get(vid) or {})
            if r:
                hasil.append(r)
    per_jenis: dict[str, list[float]] = {}
    for v in hasil:
        for r in v["adegan"]:
            if r["mulai"] >= 20:
                per_jenis.setdefault(r["jenis"], []).append(r["pergi_per_menit"])
    ringkas_jenis = {j: {"rata_pergi_per_menit": round(sum(x) / len(x), 3), "n_adegan": len(x)} for j, x in per_jenis.items() if x}
    RAW.mkdir(parents=True, exist_ok=True)
    out = {"dibuat": date.today().isoformat(), "sumber": files[-1].name, "video": hasil, "per_jenis": ringkas_jenis}
    (RAW / f"retensi-panjang-{date.today().isoformat()}.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MD.write_text(tulis_md(out), encoding="utf-8")
    print(f"[steve] retensi video panjang: {len(hasil)} video → {OUT_MD.relative_to(ROOT)}")


def pct(x) -> str:
    return "-" if x is None else f"{x * 100:.0f}%"


def tulis_md(d: dict) -> str:
    v = d["video"]
    n = len(v)
    tag = "pola" if n >= 5 else "dugaan"
    b = [f"# Retensi video panjang — {d['dibuat']}", "",
         f"Dari {d['sumber']} (YouTube Analytics). {n} video panjang punya kurva retensi."
         + ("" if n >= 5 else " **Kurang dari 5 video: semua kesimpulan di bawah masih dugaan, bukan pola.**"), ""]
    if not v:
        b += ["Data belum cukup: kurva retensi muncul ±1–3 hari setelah video tayang dan punya cukup penonton.", ""]
        return "\n".join(b)
    if d["per_jenis"]:
        b += [f"## Jenis adegan vs penonton pergi ({tag})", "", "| Jenis adegan | Penonton yang tersisa pergi per menit | Jumlah adegan |", "|---|---|---|"]
        for j, x in sorted(d["per_jenis"].items(), key=lambda kv: kv[1]["rata_pergi_per_menit"]):
            b.append(f"| {NAMA_JENIS.get(j, j)} | {x['rata_pergi_per_menit'] * 100:.1f}% | {x['n_adegan']} |")
        b += ["", "Dihitung dari penonton yang MASIH menonton saat adegan mulai (adil untuk adegan awal maupun akhir). Makin kecil makin baik;",
              "jenis paling atas = paling menahan penonton. 20 detik pertama tidak dihitung (lihat angka detik 30).", ""]
    hooks = [x["hook_30_detik"] for x in v if x.get("hook_30_detik") is not None]
    if hooks:
        b += [f"Rata-rata penonton yang masih menonton di detik 30: **{pct(sum(hooks) / len(hooks))}**.", ""]
    for x in sorted(v, key=lambda x: x.get("terbit") or "", reverse=True):
        b += [f"## {x['judul']}", "",
              f"{x['durasi'] / 60:.1f} menit · {x.get('views') or '-'} views · rata-rata ditonton {x.get('rata_ditonton_persen') or '-'}% · "
              f"bertahan di detik 30: {pct(x['hook_30_detik'])} · sampai akhir: {pct(x['akhir'])}", "",
              "| Bab | Mulai | Penonton awal → akhir bab | Yang tersisa pergi per menit |", "|---|---|---|---|"]
        for r in x["bab"]:
            b.append(f"| {r['bab']} | {int(r['mulai'] // 60)}:{int(r['mulai'] % 60):02d} | {pct(r['retensi_awal'])} → {pct(r['retensi_akhir'])} | {r['pergi_per_menit'] * 100:.1f}% |")
        if x["tercuram"]:
            b += ["", "Adegan dengan penonton paling banyak pergi:"]
            for r in x["tercuram"]:
                b.append(f"- adegan {r['adegan']} ({NAMA_JENIS.get(r['jenis'], r['jenis'])}, {int(r['mulai'] // 60)}:{int(r['mulai'] % 60):02d}): "
                         f"{r['pergi_per_menit'] * 100:.1f}% penonton tersisa pergi per menit — \"{r['narasi']}\"")
        b.append("")
    b += ["## Untuk Bayu & Citra", "",
          "- Pakai jenis adegan yang paling menahan penonton lebih sering; kurangi yang paling banyak ditinggal.",
          "- Bab dengan angka 'pergi per menit' tertinggi: buka dengan kait baru (pertanyaan/angka mengejutkan) atau persingkat.",
          "- Kalau penonton di detik 30 < 60%: pembuka terlalu lambat — langsung ke visual paling mengejutkan.",
          f"- Ingat: {n} video {'cukup untuk pola' if n >= 5 else 'belum cukup — anggap dugaan, uji lagi'}.", ""]
    return "\n".join(b)


if __name__ == "__main__":
    main()

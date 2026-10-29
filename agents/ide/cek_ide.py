#!/usr/bin/env python3
"""Nova: validasi + skor satu ide (videos/<slug>/idea.json), seperti editor riset memeriksa pitch.

    python agents/ide/cek_ide.py <slug>            # LOLOS / GAGAL + skor & alasannya
    python agents/ide/cek_ide.py <slug> --tulis    # sekaligus simpan skor ke idea.json (dipakai Studio & produser)

Aturan keras (GAGAL kalau dilanggar):
  - field wajib lengkap; kategori & status valid; 3+ varian hook; 3+ fakta
  - setiap fakta punya URL + kutipan pendek dari sumber (bukti sudah dibaca)
  - minimal 2 domain sumber berbeda dan minimal 1 sumber tier 1 (jurnal/universitas/lembaga/rilis resmi)
  - tidak ada fakta yang hanya bersandar pada tier 3 (blog, medsos, Wikipedia)
  - status 'dijual'/'dipakai' harus didukung sumber tier 1–2
  - angka kunci harus muncul di salah satu fakta (tidak boleh angka karangan)
Skor 0–100 = rubrik Nova (wow, dekat dengan tubuh/keseharian, bukti, kebaruan, risiko) + sinyal objektif:
  ketersediaan footage (cek_visual.py), performa kategori di channel (analisa Steve), permintaan penonton & pasar.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cek_topik import tokens  # noqa: E402
from sumber_tier import domain, root, tier  # noqa: E402

KATEGORI = {"makanan", "pakaian", "kesehatan", "rumah", "game", "hp", "transportasi", "robot", "energi", "lingkungan", "luar-angkasa", "lainnya"}
STATUS = {"dijual", "dipakai", "prototipe", "riset"}
RUBRIK = {"wow": 0.25, "dekat": 0.20, "bukti": 0.15, "kebaruan": 0.10, "risiko_rendah": 0.10, "visual": 0.20}
JENIS_HOOK = {"pertanyaan", "klaim", "angka", "kamu", "kontras", "rahasia"}


def rj(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def angka(s: str) -> set[str]:
    return {re.sub(r"[.,]", "", x) for x in re.findall(r"\d[\d.,]*", s)}


def latest(prefix: str) -> dict:
    files = sorted((ROOT / "insights" / "raw").glob(f"{prefix}-*.json"))
    return rj(files[-1]) or {} if files else {}


def sinyal(idea: dict) -> tuple[float, list[str]]:
    """Bonus/penalti dari data Steve (maks ±15 poin)."""
    poin, alasan = 0.0, []
    an = latest("analisa")
    kat = idea.get("kategori", "")
    peta = {"hp": "hp/gadget", "robot": "robot", "makanan": "makanan", "pakaian": "pakaian", "kesehatan": "kesehatan", "rumah": "rumah", "game": "game", "transportasi": "transportasi"}
    k = (an.get("kategori") or {}).get(peta.get(kat, kat))
    if k and k.get("median") is not None and k.get("n", 0) >= 2:
        d = max(-6.0, min(6.0, (float(k["median"]) - 1.0) * 4))
        poin += d
        alasan.append(f"kategori {kat} di channel {k['median']}× median (n={k['n']}) → {d:+.1f}")
    t = tokens(idea.get("judul_kerja", "") + " " + idea.get("hook_ide", ""))
    pasar = latest("pasar").get("video") or []
    mirip = [v for v in pasar if len(t & tokens(v.get("judul", ""))) >= 2]
    if mirip:
        vph = statistics.median(v["views_per_hari"] for v in mirip)
        b = min(5.0, 1.5 + vph / 5000)
        poin += b
        alasan.append(f"{len(mirip)} Shorts serupa sedang ramai di pasar (median {vph:.0f} views/hari) → +{b:.1f}")
    kom = (latest("komentar").get("permintaan") or [])
    minta = [c for c in kom if len(t & tokens(c.get("teks", ""))) >= 1]
    if minta:
        poin += min(4.0, 2.0 * len(minta))
        alasan.append(f"{len(minta)} komentar penonton meminta topik serupa → +{min(4.0, 2.0 * len(minta)):.1f}")
    return poin, alasan


def periksa(slug: str) -> tuple[list[str], list[str], dict]:
    p = ROOT / "videos" / slug / "idea.json"
    idea = rj(p)
    if not isinstance(idea, dict):
        return [f"{p.relative_to(ROOT)} tidak ada atau bukan JSON valid"], [], {}
    gagal, catatan = [], []
    for f in ("judul_kerja", "kategori", "status_teknologi", "kenapa_menang", "hook_ide", "fakta", "risiko"):
        if not idea.get(f):
            gagal.append(f"field '{f}' kosong")
    if idea.get("kategori") and idea["kategori"] not in KATEGORI:
        gagal.append(f"kategori '{idea['kategori']}' tidak dikenal ({', '.join(sorted(KATEGORI))})")
    st = idea.get("status_teknologi", "")
    if st and st not in STATUS:
        gagal.append(f"status_teknologi '{st}' harus salah satu: {', '.join(sorted(STATUS))}")

    hooks = idea.get("hook_varian") or []
    if len(hooks) < 3:
        gagal.append(f"hook_varian {len(hooks)} (minimal 3, beda jenis)")
    else:
        jenis = {h.get("jenis") for h in hooks if isinstance(h, dict)}
        if len(jenis) < 2:
            gagal.append("hook_varian harus memakai minimal 2 jenis berbeda")
        for h in hooks:
            if isinstance(h, dict) and len(str(h.get("teks", "")).split()) > 9:
                catatan.append(f"hook terlalu panjang (>9 kata): {h.get('teks')}")
            if isinstance(h, dict) and h.get("jenis") not in JENIS_HOOK:
                catatan.append(f"jenis hook '{h.get('jenis')}' tidak standar ({', '.join(sorted(JENIS_HOOK))})")

    fakta = idea.get("fakta") or []
    if len(fakta) < 3:
        gagal.append(f"fakta {len(fakta)} (minimal 3)")
    doms, tiers = set(), []
    for i, f in enumerate(fakta, 1):
        url = str(f.get("sumber_url", ""))
        if not url.startswith("http"):
            gagal.append(f"fakta {i}: sumber_url tidak valid")
            continue
        t = tier(url, str(f.get("jenis_sumber", "")))
        f["_tier"] = t
        tiers.append(t)
        doms.add(root(domain(url)))
        kut = str(f.get("kutipan", "")).strip()
        if not kut:
            gagal.append(f"fakta {i}: belum ada 'kutipan' dari sumber (bukti halaman benar-benar dibaca)")
        elif len(kut.split()) > 30:
            catatan.append(f"fakta {i}: kutipan terlalu panjang (>30 kata); cukup potongan yang membuktikan klaim")
        if t == 3:
            gagal.append(f"fakta {i}: sumber {domain(url)} tier 3 (blog/medsos/Wikipedia) — cari sumber aslinya")
        tgl = str(f.get("tanggal_sumber", ""))
        if re.fullmatch(r"\d{4}(-\d\d){0,2}", tgl):
            umur = (date.today() - date(int(tgl[:4]), int(tgl[5:7] or 1) if len(tgl) >= 7 else 1, 1)).days / 365
            if umur > 3:
                catatan.append(f"fakta {i}: sumber {tgl} sudah >3 tahun; cek apakah masih berlaku")
    if len(doms) < 2:
        gagal.append(f"sumber hanya dari {len(doms)} domain (minimal 2 domain berbeda)")
    if tiers and min(tiers) > 1:
        gagal.append("belum ada sumber tier 1 (jurnal/universitas/lembaga/rilis resmi pembuatnya)")
    if st in ("dijual", "dipakai") and not any(t <= 2 for t in tiers):
        gagal.append(f"status '{st}' perlu bukti dari sumber tier 1–2")

    teks_fakta = " ".join(str(f.get("klaim", "")) + " " + str(f.get("kutipan", "")) for f in fakta)
    ada = angka(teks_fakta)
    for a in idea.get("angka_kunci") or []:
        if not (angka(str(a.get("angka", ""))) & ada):
            gagal.append(f"angka kunci '{a.get('angka')}' tidak ditemukan di fakta mana pun (jangan mengarang angka)")
    if not idea.get("kata_kunci_visual"):
        catatan.append("kata_kunci_visual (Inggris) belum diisi; Bima akan menebak")
    if not idea.get("visual"):
        catatan.append("ketersediaan footage belum dicek (python agents/ide/cek_visual.py --tulis <slug> ...)")

    # ---- skor
    rub = idea.get("rubrik") or {}
    nilai = {}
    for k in RUBRIK:
        try:
            nilai[k] = max(1, min(5, int(rub.get(k, 3))))
        except (TypeError, ValueError):
            nilai[k] = 3
    if not rub:
        catatan.append("rubrik belum diisi; skor memakai nilai tengah")
    vis = idea.get("visual") or {}
    if isinstance(vis.get("skor"), (int, float)):
        nilai["visual"] = max(1, min(5, round(vis["skor"] / 2)))     # data objektif menggantikan perkiraan Nova
    bukti = 5 if tiers and min(tiers) == 1 and len(doms) >= 3 else 4 if tiers and min(tiers) == 1 else 2
    nilai["bukti"] = min(nilai["bukti"], bukti) if rub.get("bukti") else bukti
    dasar = sum(nilai[k] * w for k, w in RUBRIK.items()) / 5 * 85
    bonus, alasan = sinyal(idea)
    total = round(max(0, min(100, dasar + bonus)))
    skor = {"total": total, "rubrik": nilai, "dasar": round(dasar, 1), "sinyal": alasan, "sumber": {"domain": len(doms), "tier": sorted(tiers)},
            "dihitung": datetime.now().isoformat(timespec="seconds")}
    return gagal, catatan, {"idea": idea, "skor": skor, "path": p}


def main() -> None:
    ap = argparse.ArgumentParser(description="Validasi & skor ide Nova")
    ap.add_argument("slug")
    ap.add_argument("--tulis", action="store_true")
    a = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9-]{3,80}", a.slug):
        sys.exit("[nova] slug tidak valid")
    gagal, catatan, h = periksa(a.slug)
    if h:
        s = h["skor"]
        print(f"[nova] skor {s['total']}/100 (rubrik {s['dasar']} + sinyal {s['total'] - s['dasar']:+.0f}) · "
              + " ".join(f"{k}={v}" for k, v in s["rubrik"].items()) + f" · sumber {s['sumber']['domain']} domain, tier {s['sumber']['tier']}")
        for x in s["sinyal"]:
            print(f"[nova]   sinyal: {x}")
    for c in catatan:
        print(f"[nova] CATATAN: {c}")
    for g in gagal:
        print(f"[nova] GAGAL: {g}")
    if h and a.tulis and not gagal:
        idea = h["idea"]
        for f in idea.get("fakta", []):
            f["tier"] = f.pop("_tier", None)
        idea["skor"] = h["skor"]
        h["path"].write_text(json.dumps(idea, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[nova] skor disimpan ke videos/{a.slug}/idea.json")
    print("[nova] LOLOS" if not gagal else f"[nova] GAGAL ({len(gagal)} masalah)")
    sys.exit(1 if gagal else 0)


if __name__ == "__main__":
    main()

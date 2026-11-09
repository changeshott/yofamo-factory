#!/usr/bin/env python3
"""Pemakaian token Claude per video (Shorts & video panjang), dari produksi/token-log.jsonl (dicatat agents/produser.py).

    python agents/pemakaian.py            # ringkasan: rata-rata per video, per langkah, 10 video terakhir
    python agents/pemakaian.py --json     # sama, JSON (dipakai Studio)

Token dihitung per VIDEO: semua langkah Claude untuk video itu dijumlah, termasuk produksi lanjutan (laptop mati lalu
dilanjutkan) dan QC visual yang menyusul. Langkah sebelum slug ada (Nova/Bayu memilih topik) dipetakan lewat catatan
produksi (produksi/<id>.json, produksi/panjang/<id>.json).
Kolom: baru = input + tulis cache (konteks yang benar-benar dibaca baru), cache = baca cache (instruksi & alat yang dipakai ulang,
jauh lebih murah), output = tulisan Claude. biaya_usd = harga setara API; langganan Claude Pro tidak ditagih per token,
tapi semua ini tetap mengurangi batas pemakaian (kuota 5 jam & mingguan).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "produksi" / "token-log.jsonl"


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def baca() -> list[dict]:
    out = []
    try:
        for line in LOG.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def slug_produksi(pid: str) -> str | None:
    if not pid:
        return None
    for f in (ROOT / "produksi" / f"{pid}.json", ROOT / "produksi" / "panjang" / f"{pid}.json"):
        s = rj(f).get("slug")
        if s:
            return s
    return None


def judul(slug: str, jenis: str) -> str:
    if jenis == "panjang":
        return str(rj(ROOT / "panjang" / slug / "naskah.json").get("judul") or slug)
    sc = rj(ROOT / "videos" / slug / "script.json")
    return str(sc.get("judul") or rj(ROOT / "videos" / slug / "idea.json").get("judul_kerja") or slug)


def total(b: dict) -> int:
    return int(b.get("input", 0)) + int(b.get("cache_tulis", 0)) + int(b.get("cache_baca", 0)) + int(b.get("output", 0))


def ringkas() -> dict:
    baris = baca()
    cache_slug: dict[str, str | None] = {}
    video: dict[str, dict] = {}
    langkah: dict[tuple[str, str], list[int]] = {}
    for b in baris:
        pid = b.get("id") or ""
        if pid not in cache_slug:
            cache_slug[pid] = slug_produksi(pid)
        slug = b.get("slug") or cache_slug[pid]
        jenis = b.get("jenis") or "shorts"
        nama = str(b.get("langkah") or "?").split()[0]
        langkah.setdefault((jenis, nama), []).append(total(b))
        if not slug:
            continue
        v = video.setdefault(slug, {"slug": slug, "jenis": jenis, "total": 0, "baru": 0, "cache": 0, "output": 0, "biaya_usd": 0.0,
                                    "langkah": {}, "mulai": b.get("waktu"), "akhir": b.get("waktu")})
        v["total"] += total(b)
        v["baru"] += int(b.get("input", 0)) + int(b.get("cache_tulis", 0))
        v["cache"] += int(b.get("cache_baca", 0))
        v["output"] += int(b.get("output", 0))
        v["biaya_usd"] = round(v["biaya_usd"] + float(b.get("biaya_usd") or 0), 4)
        v["langkah"][nama] = v["langkah"].get(nama, 0) + total(b)
        v["akhir"] = b.get("waktu")
    for v in video.values():
        v["judul"] = judul(v["slug"], v["jenis"])
    rata = {}
    for jenis in ("shorts", "panjang"):
        vs = [v for v in video.values() if v["jenis"] == jenis]
        if vs:
            rata[jenis] = {"video": len(vs), "total": round(sum(v["total"] for v in vs) / len(vs)), "baru": round(sum(v["baru"] for v in vs) / len(vs)),
                           "cache": round(sum(v["cache"] for v in vs) / len(vs)), "output": round(sum(v["output"] for v in vs) / len(vs)),
                           "biaya_usd": round(sum(v["biaya_usd"] for v in vs) / len(vs), 3)}
    per_langkah = [{"jenis": j, "langkah": n, "rata": round(sum(x) / len(x)), "kali": len(x)} for (j, n), x in langkah.items()]
    terbaru = sorted(video.values(), key=lambda v: v["akhir"] or "", reverse=True)[:10]
    return {"sejak": baris[0]["waktu"] if baris else None, "langkah_tercatat": len(baris), "rata_per_video": rata,
            "per_langkah": sorted(per_langkah, key=lambda x: (x["jenis"], -x["rata"])), "video_terbaru": terbaru}


def angka(n: float) -> str:
    return f"{n / 1e6:.2f} jt" if n >= 1e6 else f"{n / 1e3:.0f} rb" if n >= 1e3 else str(int(n))


def main() -> None:
    d = ringkas()
    if "--json" in sys.argv:
        print(json.dumps(d, ensure_ascii=False))
        return
    if not d["langkah_tercatat"]:
        print("Belum ada data token. Pencatatan mulai di produksi berikutnya (produksi/token-log.jsonl).")
        return
    print(f"Token Claude sejak {d['sejak']} ({d['langkah_tercatat']} langkah tercatat)\n")
    for jenis, r in d["rata_per_video"].items():
        print(f"Rata-rata per video {jenis} ({r['video']} video): {angka(r['total'])} token "
              f"(baru {angka(r['baru'])} · cache {angka(r['cache'])} · output {angka(r['output'])}) · setara API ${r['biaya_usd']}")
    print("\nPer langkah (rata-rata token):")
    for x in d["per_langkah"]:
        print(f"  {x['jenis']:8} {x['langkah']:16} {angka(x['rata']):>9}  ({x['kali']}x)")
    print("\nVideo terbaru:")
    for v in d["video_terbaru"]:
        print(f"  {v['jenis']:8} {angka(v['total']):>9}  {v['judul'][:60]}")


if __name__ == "__main__":
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    main()

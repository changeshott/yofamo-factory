#!/usr/bin/env python3
"""Laras — ilustrator video panjang. Gambar gaya lukis-komik (bible/gaya-animasi.json) untuk tiap adegan ilustrasi,
objek diagram 'bagian', dan thumbnail. Mesin: FLUX.2 klein-4b gratis (Cloudflare) + GAMBAR ACUAN gaya supaya semua
gambar satu video (dan antar video) terasa satu dunia.

    python agents/panjang/ilustrasi.py <slug>               # semua adegan yang butuh gambar → panjang/<slug>/ilustrasi/NN.jpg
    python agents/panjang/ilustrasi.py <slug> --ulang 4 9   # buat ulang gambar adegan tertentu (sudut & seed lain)
    python agents/panjang/ilustrasi.py <slug> --uji         # tanpa internet: gambar contoh

Prompt = gaya lukis-komik + isi adegan dari naskah (bahasa Inggris, objek/aksi spesifik) + sudut kamera + larangan
(tanpa tulisan, logo, orang sungguhan). Objek diagram dibuat di atas pink polos lalu dipotong → NN.png transparan
(melayang di motion graphic). Kuota gratis ±70 gambar/hari (reset 07:00 WIB); satu video ±10–20 gambar.
Kalau kuota habis: berhenti rapi (exit 5), gambar yang sudah jadi disimpan, lanjutkan besok dengan perintah yang sama.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import status as st_panjang  # noqa: E402
import gambar_ai  # noqa: E402

GAYA = ROOT / "bible" / "gaya-animasi.json"
ACUAN_GAYA = ROOT / "bible" / "maskot" / "acuan-gaya.jpg"
SUDUT = ["dynamic three-quarter view, dramatic perspective", "dramatic low angle hero shot", "close-up detail shot, shallow depth",
         "wide cinematic establishing shot"]


def log(msg: str) -> None:
    print(f"[laras] {msg}", flush=True)


def jenis_gambar(ad: dict) -> str | None:
    if ad.get("jenis") == "ilustrasi":
        return "adegan"
    if ad.get("jenis") == "diagram" and (ad.get("diagram") or {}).get("tipe") == "bagian":
        return "objek"
    if ad.get("jenis") == "thumbnail":
        return "thumbnail"
    return None


def prompt_untuk(ad: dict, g: dict, jenis: str, varian: int = 0, acuan: bool = False) -> str:
    il = g.get("ilustrasi", {})
    isi = str(ad.get("gambar") or ad.get("prompt") or ad.get("visual") or "").strip().rstrip(".")
    if jenis == "objek":
        bagian = ", ".join(str(b.get("label", "")) for b in (ad.get("diagram") or {}).get("bagian", [])[:6] if isinstance(b, dict))
        isi = f"{isi or (ad.get('diagram') or {}).get('pusat', '')}, clearly showing its parts ({bagian})" if bagian else isi
        bagian_akhir = [il.get("objek", ""), "bold ink outline around the whole object, painted highlights"]
    elif jenis == "thumbnail":
        bagian_akhir = ["eye-catching hero object, huge scale, dramatic rim light, high contrast, centered composition", "hot pink and cyan accents"]
    else:
        bagian_akhir = [SUDUT[varian % len(SUDUT)], "foreground, midground and background depth, atmospheric painted light"]
    teks = ", ".join(x for x in [il.get("gaya", ""), isi, *bagian_akhir, il.get("larangan", "")] if x)
    if acuan:
        teks += ". " + il.get("acuan_gaya", "")
    return teks


def main() -> None:
    ap = argparse.ArgumentParser(description="Laras: ilustrasi gaya lukis-komik")
    ap.add_argument("slug")
    ap.add_argument("--ulang", type=int, nargs="*", default=[])
    ap.add_argument("--uji", action="store_true")
    a = ap.parse_args()
    vdir = st_panjang.folder(a.slug)
    naskah = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    g = json.loads(GAYA.read_text(encoding="utf-8")) if GAYA.exists() else {}
    lebar, tinggi = (g.get("ilustrasi", {}).get("ukuran") or [1536, 864])[:2]
    idir = vdir / "ilustrasi"
    idir.mkdir(exist_ok=True)
    if not a.uji:
        acc, tok = gambar_ai.load_env()
        if not acc or not tok:
            sys.exit("[laras] CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN belum diisi di .env")
    acuan = [ACUAN_GAYA.read_bytes()] if ACUAN_GAYA.exists() else None
    catatan = json.loads((idir / "prompt.json").read_text(encoding="utf-8")) if (idir / "prompt.json").exists() else {}
    adegan = list(naskah["adegan"])
    if naskah.get("thumbnail", {}).get("prompt"):
        adegan.append({"jenis": "thumbnail", "prompt": naskah["thumbnail"]["prompt"], "_nama": "thumbnail"})
    dibuat = gagal = 0
    kuota = False
    for i, ad in enumerate(adegan):
        jenis = jenis_gambar(ad)
        if not jenis:
            continue
        nama = ad.get("_nama") or f"{i + 1:02}"
        out = idir / f"{nama}.jpg"
        ulang = (i + 1) in a.ulang
        if out.exists() and not ulang:
            continue
        varian = catatan.get(nama, {}).get("varian", -1) + 1 if ulang else i
        p = prompt_untuk(ad, g, jenis, varian, bool(acuan))
        w, h = (1024, 1024) if jenis == "objek" else (lebar, tinggi)
        try:
            if a.uji:
                gambar_ai.contoh_uji(out, p, i, w, h, pink=jenis == "objek")
            else:
                out.write_bytes(gambar_ai.gambar(p, w, h, acuan=acuan, seed=7919 * (i + 1) + varian * 131))
            if jenis == "objek":
                gambar_ai.potong_latar(out.read_bytes()).save(out.with_suffix(".png"))
            catatan[nama] = {"prompt": p, "varian": varian, "jenis": jenis}
            dibuat += 1
            log(f"{nama} ({jenis}): {str(ad.get('gambar') or ad.get('prompt') or '')[:70]}")
        except gambar_ai.KuotaGambar as err:
            kuota = True
            log(f"{nama}: {err} → berhenti, gambar yang sudah jadi disimpan. Lanjutkan setelah 07:00 WIB.")
            break
        except Exception as err:  # satu gambar gagal tidak menghentikan yang lain; animator memakai kartu cadangan
            gagal += 1
            log(f"{nama}: gagal ({str(err)[:120]})")
    (idir / "prompt.json").write_text(json.dumps(catatan, ensure_ascii=False, indent=1), encoding="utf-8")
    if kuota:
        sys.exit(5)
    st_panjang.set_status(a.slug, "ilustrasi", f"{dibuat} gambar baru, {gagal} gagal")
    log(f"selesai: {dibuat} gambar baru{f', {gagal} gagal' if gagal else ''} → panjang/{a.slug}/ilustrasi/")


if __name__ == "__main__":
    main()

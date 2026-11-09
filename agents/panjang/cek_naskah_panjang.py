#!/usr/bin/env python3
"""Validator naskah video panjang (dipakai Citra sebelum naskah diserahkan ke Gilang & Tio).

    python agents/panjang/cek_naskah_panjang.py <slug>          # LOLOS / GAGAL + daftar perbaikan
    python agents/panjang/cek_naskah_panjang.py <slug> --tulis  # + naskah.md (tabel adegan untuk Zona & tim)

Format panjang/<slug>/naskah.json:
{
  "judul": "...", "judul_alternatif": ["...", "..."], "deskripsi": "... (tanpa link)", "tag": ["..."], "suasana": "epik",
  "thumbnail": {"teks": "2–4 KATA", "ekspresi": "kaget", "prompt": "English image prompt"},
  "komentar_pin": "pertanyaan untuk penonton",
  "adegan": [
    {"jenis": "host", "narasi": "Tau nggak, ...", "ekspresi": "senang", "teks_layar": "≤ 8 kata", "kata_kunci": ["kata", "dari narasi"]},
    {"jenis": "judul_bab", "judul": "Cara kerjanya", "narasi": ""},
    {"jenis": "ilustrasi", "narasi": "...", "gambar": "English prompt: specific object/action", "teks_layar": "...", "host_kecil": false},
    {"jenis": "diagram", "narasi": "...", "diagram": {"tipe": "alur", "judul": "...", "langkah": ["...", "..."]}, "host_kecil": true},
    {"jenis": "penutup", "narasi": "...", "ekspresi": "senang"}
  ]
}
diagram.tipe: bagian {judul, bagian:[{label, ket}], + "gambar" objek di tengah} · alur {judul, langkah[2–5]} ·
perbandingan {judul, kiri:{label,nilai,ket}, kanan:{...}} · angka {angka, akhiran, label} · daftar {judul, butir[2–5]} ·
timeline {judul, butir:[{waktu, teks}]}
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents" / "penulis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import status as st_panjang  # noqa: E402
from cek_naskah import angka_digit, kata_ke_angka  # noqa: E402

JENIS = {"host", "ilustrasi", "diagram", "judul_bab", "penutup"}
EKSPRESI = {"senang", "kaget", "mikir", "serius", "tertawa"}
DIAGRAM = {"bagian": "bagian", "alur": "langkah", "perbandingan": "kiri", "angka": "angka", "daftar": "butir", "timeline": "butir"}
PEMBUKA = re.compile(r"^\s*(tau|tahu)\s+(nggak|gak|ga|enggak)\b", re.I)
WPS = 2.45   # kata per detik (Ardi +6%)


def kata(t: str) -> list[str]:
    return re.findall(r"[\w'’-]+", str(t), flags=re.UNICODE)


JENIS_DOK = {"pembuka", "footage", "kata", "angka", "cara_kerja", "banding", "garis_waktu", "objek", "hp", "tv", "judul_bab", "penutup"}
FOOTAGE_DOK = {"pembuka", "footage", "hp", "tv"}
MOGRAPH_DOK = {"kata", "angka", "cara_kerja", "banding", "garis_waktu", "objek"}
MAKS_KATA_DOK = {"pembuka": 30, "footage": 45, "hp": 40, "tv": 40, "kata": 30, "angka": 35, "cara_kerja": 60, "banding": 45,
                 "garis_waktu": 60, "objek": 40, "penutup": 45, "judul_bab": 0}


def inggris(t) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9 ,.'/&()-]{3,}", str(t).strip()))


def cek_dokumenter(s: dict, ide: dict, fails: list[str], warns: list[str]) -> dict:
    """Format 'dokumenter' (gaya Video 1): footage asli tanpa teks + selingan motion graphic, 5–12 menit."""
    ad = s.get("adegan") or []
    th = s.get("thumbnail") or {}
    if not 1 <= len(kata(th.get("teks", ""))) <= 4:
        fails.append("thumbnail.teks harus 1–4 kata")
    if not inggris(th.get("objek", "")):
        fails.append("thumbnail.objek wajib: 1 benda fisik yang dibahas, bahasa Inggris (dicari fotonya & dipotong latarnya)")
    total, n_jenis, kata_footage, kata_isi, nomor, beruntun = 0, {}, 0, 0, 0, 0
    for i, a in enumerate(ad, 1):
        j = a.get("jenis")
        n_jenis[j] = n_jenis.get(j, 0) + 1
        if j not in JENIS_DOK:
            fails.append(f"adegan {i}: jenis harus salah satu {sorted(JENIS_DOK)}")
            continue
        n = len(kata(a.get("narasi", "")))
        total += n
        if j != "judul_bab":
            kata_isi += n
            if n == 0:
                fails.append(f"adegan {i}: narasi kosong")
        if n > MAKS_KATA_DOK[j]:
            fails.append(f"adegan {i} ({j}): narasi {n} kata (maks {MAKS_KATA_DOK[j]}) — pecah jadi 2 adegan")
        if j in FOOTAGE_DOK:
            kata_footage += n
            kk = a.get("kata_kunci_visual") or []
            if not kk or not all(inggris(x) for x in kk):
                fails.append(f"adegan {i} ({j}): 'kata_kunci_visual' wajib 1–3 kata kunci bahasa Inggris yang MEMPERLIHATKAN teknologinya")
        if j in MOGRAPH_DOK:
            beruntun += 1
            if beruntun > 2:
                fails.append(f"adegan {i}: lebih dari 2 motion graphic berturut-turut — selingi footage")
        else:
            beruntun = 0
        if j == "judul_bab":
            nomor += 1
            a["nomor"] = nomor
            if not str(a.get("judul", "")).strip() or len(kata(a.get("judul"))) > 6:
                fails.append(f"adegan {i}: judul_bab butuh 'judul' ≤ 6 kata")
            if n:
                fails.append(f"adegan {i}: judul_bab tanpa narasi")
        if j in ("pembuka", "kata") and not 1 <= len(kata(a.get("teks_layar") or a.get("teks") or "")) <= 6:
            fails.append(f"adegan {i} ({j}): 'teks_layar' 1–6 kata (kata/frasa kunci yang DIUCAPKAN)")
        if j == "angka" and not re.search(r"\d", str(a.get("angka", ""))):
            fails.append(f"adegan {i}: angka butuh 'angka' (digit) + 'label'")
        if j == "cara_kerja":
            L = a.get("langkah") or []
            if not 2 <= len(L) <= 4 or not all(1 <= len(kata((x or {}).get("teks", x) if isinstance(x, dict) else x)) <= 6 for x in L):
                fails.append(f"adegan {i}: cara_kerja butuh 2–4 'langkah' (teks ≤ 6 kata, 'objek' bahasa Inggris opsional)")
        if j == "banding" and not ((a.get("kiri") or {}).get("label") and (a.get("kanan") or {}).get("label")):
            fails.append(f"adegan {i}: banding butuh kiri.label & kanan.label (+ nilai/ket)")
        if j == "garis_waktu" and not 2 <= len(a.get("butir") or []) <= 5:
            fails.append(f"adegan {i}: garis_waktu butuh 2–5 butir {{waktu, teks}}")
        if j == "objek" and (not inggris(a.get("objek", "")) or not 1 <= len(kata(a.get("label", ""))) <= 5):
            fails.append(f"adegan {i}: objek butuh 'objek' (benda fisik, bahasa Inggris) + 'label' ≤ 5 kata")
    if not ad or ad[0].get("jenis") != "pembuka" or not PEMBUKA.match(str(ad[0].get("narasi", ""))):
        fails.append("adegan 1 harus 'pembuka' yang narasinya diawali 'Tau nggak, …'")
    if ad and ad[-1].get("jenis") != "penutup":
        fails.append("adegan terakhir harus 'penutup' (teks_layar = pertanyaan untuk komentar)")
    if n_jenis.get("judul_bab", 0) < 3:
        fails.append(f"minimal 3 judul_bab (chapter YouTube), sekarang {n_jenis.get('judul_bab', 0)}")
    mg = sum(n_jenis.get(k, 0) for k in MOGRAPH_DOK)
    if mg < 4:
        fails.append(f"minimal 4 motion graphic (cara kerja, angka, perbandingan, …), sekarang {mg}")
    if kata_isi and kata_footage / kata_isi < 0.5:
        fails.append(f"footage asli hanya {kata_footage / kata_isi:.0%} narasi (min 50%) — tambah adegan footage")
    detik = total / WPS + n_jenis.get("judul_bab", 0) * 2.6 + len(ad) * 0.35
    if not 285 <= detik <= 735:
        fails.append(f"perkiraan durasi {detik / 60:.1f} menit ({total} kata); target 5–12 menit (±700–1700 kata)")
    return {"adegan": len(ad), "kata": total, "menit": round(detik / 60, 1), "jenis": n_jenis,
            "footage": round(kata_footage / max(1, kata_isi), 2)}


def cek(slug: str) -> tuple[list[str], list[str], dict, dict]:
    vdir = st_panjang.folder(slug)
    fails, warns = [], []
    try:
        s = json.loads((vdir / "naskah.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as err:
        return [f"naskah.json tidak bisa dibaca: {err}"], [], {}, {}
    ide = {}
    try:
        ide = json.loads((vdir / "ide.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        warns.append("ide.json tidak ada; angka tidak bisa dicocokkan dengan sumber")
    for k in ("judul", "deskripsi", "tag", "adegan", "thumbnail"):
        if not s.get(k):
            fails.append(f"'{k}' kosong")
    ad = s.get("adegan") or []
    if not ad:
        return fails, warns, {}, s
    if len(str(s.get("judul", ""))) > 90:
        fails.append("judul > 90 karakter")
    if re.search(r"https?://|www\.", str(s.get("deskripsi", ""))):
        fails.append("deskripsi tidak boleh memuat link")
    # kata pencarian (agents/ide/kata_cari.py --tulis): judul memuat frasa yang benar-benar dicari orang → muncul di pencarian YouTube
    try:
        kc = json.loads((vdir / "kata_cari.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        kc = None
    if kc is None:
        warns.append("kata_cari.json belum ada: jalankan python agents/ide/kata_cari.py \"<produk>\" --tulis <slug> lalu pakai frasanya di judul")
    elif kc.get("frasa"):
        jl = str(s.get("judul", "")).lower()
        top = [str(e.get("frasa", "")).lower() for e in kc["frasa"][:10]]
        inti = [f for f in top if f and all(w in jl for w in f.split()[:3])]
        if not inti:
            warns.append(f"judul belum memuat frasa pencarian teratas (mis. '{top[0]}'); masukkan secara alami di awal judul")
    if s.get("format") == "dokumenter":
        info = cek_dokumenter(s, ide, fails, warns)
        if ide:
            sumber = " ".join(str(f.get("klaim", "")) + " " + str(f.get("kutipan", "")) for f in ide.get("fakta", [])) + " " + \
                     " ".join(str(x.get("angka", "")) for x in ide.get("angka_kunci", []))
            boleh = set(angka_digit(sumber)) | set(kata_ke_angka(sumber))
            for i, a in enumerate(ad, 1):
                for n in set(angka_digit(a.get("narasi", ""))) | set(kata_ke_angka(a.get("narasi", ""))):
                    if n >= 10 and n not in boleh and not 1900 <= n <= 2100:
                        warns.append(f"adegan {i}: angka {n:g} tidak ditemukan di fakta ide.json — pastikan bersumber")
        return fails, warns, info, s
    th = s.get("thumbnail") or {}
    if not 1 <= len(kata(th.get("teks", ""))) <= 5:
        fails.append("thumbnail.teks harus 1–5 kata")
    if not str(th.get("prompt", "")).strip():
        warns.append("thumbnail.prompt kosong (ilustrasi thumbnail memakai gambar adegan)")
    total_kata, jenis_n, beruntun_host = 0, {}, 0
    for i, a in enumerate(ad, 1):
        j = a.get("jenis")
        jenis_n[j] = jenis_n.get(j, 0) + 1
        if j not in JENIS:
            fails.append(f"adegan {i}: jenis harus salah satu {sorted(JENIS)}")
            continue
        n = len(kata(a.get("narasi", "")))
        total_kata += n
        if j != "judul_bab" and n == 0:
            fails.append(f"adegan {i}: narasi kosong")
        if n > 60:
            fails.append(f"adegan {i}: narasi {n} kata (maks 60) — pecah jadi 2 adegan supaya visual berganti")
        if j == "judul_bab" and not str(a.get("judul", "")).strip():
            fails.append(f"adegan {i}: judul_bab butuh 'judul'")
        if a.get("ekspresi") and a["ekspresi"] not in EKSPRESI:
            fails.append(f"adegan {i}: ekspresi harus salah satu {sorted(EKSPRESI)}")
        if j == "ilustrasi" and len(kata(a.get("gambar", ""))) < 5:
            fails.append(f"adegan {i}: 'gambar' (prompt bahasa Inggris, objek/aksi spesifik) wajib untuk ilustrasi")
        if a.get("teks_layar") and len(kata(a["teks_layar"])) > 8:
            fails.append(f"adegan {i}: teks_layar maksimal 8 kata")
        for kk in a.get("kata_kunci") or []:
            if str(kk).split()[0].lower()[:5] not in str(a.get("narasi", "")).lower():
                warns.append(f"adegan {i}: kata_kunci '{kk}' tidak ada di narasinya (tidak akan muncul)")
        if j == "diagram":
            dg = a.get("diagram") or {}
            t = dg.get("tipe")
            if t not in DIAGRAM:
                fails.append(f"adegan {i}: diagram.tipe harus salah satu {sorted(DIAGRAM)}")
            elif not dg.get(DIAGRAM[t]):
                fails.append(f"adegan {i}: diagram {t} butuh '{DIAGRAM[t]}'")
            elif t in ("alur", "daftar", "timeline", "bagian") and not 2 <= len(dg[DIAGRAM[t]]) <= 6:
                fails.append(f"adegan {i}: diagram {t} butuh 2–6 butir")
            if t == "bagian" and len(kata(a.get("gambar", ""))) < 3:
                warns.append(f"adegan {i}: diagram bagian sebaiknya punya 'gambar' (objek di tengah)")
        beruntun_host = beruntun_host + 1 if j == "host" else 0
        if beruntun_host > 2:
            fails.append(f"adegan {i}: lebih dari 2 adegan host berturut-turut — selingi ilustrasi/diagram")
    if not PEMBUKA.match(str(ad[0].get("narasi", ""))):
        fails.append("ciri khas channel: narasi adegan 1 harus diawali 'Tau nggak, …'")
    if ad[-1].get("jenis") != "penutup":
        fails.append("adegan terakhir harus 'penutup'")
    if jenis_n.get("judul_bab", 0) < 3:
        fails.append(f"minimal 3 judul_bab (chapter YouTube), sekarang {jenis_n.get('judul_bab', 0)}")
    isi = sum(v for k, v in jenis_n.items() if k != "judul_bab") or 1
    if jenis_n.get("host", 0) / isi > 0.4:
        fails.append(f"adegan host {jenis_n.get('host', 0)}/{isi} (maks 40%) — ganti sebagian jadi ilustrasi/diagram")
    if (jenis_n.get("ilustrasi", 0) + jenis_n.get("diagram", 0)) / isi < 0.45:
        fails.append("ilustrasi + diagram minimal 45% adegan")
    if jenis_n.get("diagram", 0) < 3:
        fails.append("minimal 3 diagram (cara kerja harus digambarkan)")
    detik = total_kata / WPS + jenis_n.get("judul_bab", 0) * 2.6 + len(ad) * 0.35
    if not 270 <= detik <= 530:
        fails.append(f"perkiraan durasi {detik / 60:.1f} menit ({total_kata} kata); target 5–8 menit (±700–1150 kata)")
    # angka di narasi harus berasal dari ide.json (fakta bersumber)
    if ide:
        sumber = " ".join(str(f.get("klaim", "")) + " " + str(f.get("kutipan", "")) for f in ide.get("fakta", [])) + " " + \
                 " ".join(str(x.get("angka", "")) for x in ide.get("angka_kunci", []))
        boleh = set(angka_digit(sumber)) | set(kata_ke_angka(sumber))
        for i, a in enumerate(ad, 1):
            for n in set(angka_digit(a.get("narasi", ""))) | set(kata_ke_angka(a.get("narasi", ""))):
                if n >= 10 and n not in boleh and not 1900 <= n <= 2100:
                    warns.append(f"adegan {i}: angka {n:g} tidak ditemukan di fakta ide.json — pastikan bersumber")
    info = {"adegan": len(ad), "kata": total_kata, "menit": round(detik / 60, 1), "jenis": jenis_n}
    return fails, warns, info, s


def naskah_md(s: dict, info: dict) -> str:
    L = [f"# {s.get('judul', '')}", "", f"**Perkiraan:** {info.get('menit')} menit · {info.get('adegan')} adegan · {info.get('kata')} kata · "
         f"**Thumbnail:** {s.get('thumbnail', {}).get('teks', '')}", "", "| # | Jenis | Narasi | Visual |", "|---|---|---|---|"]
    for i, a in enumerate(s.get("adegan", []), 1):
        vis = a.get("judul") or a.get("gambar") or (a.get("diagram") or {}).get("tipe") or a.get("teks_layar") or ""
        L.append(f"| {i} | {a.get('jenis')} | {str(a.get('narasi', '')).replace('|', '/')} | {str(vis).replace('|', '/')} |")
    L += ["", f"## Deskripsi\n{s.get('deskripsi', '')}", "", f"## Tag\n{', '.join(s.get('tag', []))}"]
    return "\n".join(L) + "\n"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("pakai: cek_naskah_panjang.py <slug> [--tulis]")
    slug = sys.argv[1]
    fails, warns, info, s = cek(slug)
    for f in fails:
        print(f"GAGAL  {f}")
    for w in warns:
        print(f"PERINGATAN  {w}")
    print(f"info: {json.dumps(info, ensure_ascii=False)}")
    if fails:
        print(f"GAGAL ({len(fails)} perbaikan)")
        sys.exit(1)
    if "--tulis" in sys.argv:
        (st_panjang.folder(slug) / "naskah.md").write_text(naskah_md(s, info), encoding="utf-8")
        if s.get("format") == "dokumenter":       # nomor bab ditulis ke naskah (dipakai kartu judul bab)
            (st_panjang.folder(slug) / "naskah.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        st_panjang.set_status(slug, "naskah", f"{info.get('menit')} menit, {info.get('adegan')} adegan")
    print("LOLOS")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Raka: editor naskah otomatis. Memeriksa videos/<slug>/script.json seperti script editor profesional.

    python agents/penulis/cek_naskah.py <slug>           # LOLOS / GAGAL + saran
    python agents/penulis/cek_naskah.py <slug> --tulis   # + tulis naskah.md (versi mudah dibaca untuk Zona & tim)

Yang diperiksa:
  struktur  kalimat 1 = hook (≤ 12 kata), kalimat terakhir = penutup yang tuntas (tidak menggantung)
  durasi    jumlah kata cocok dengan target_durasi (±12%), 25–58 detik
  ritme     tiap kalimat ≤ 22 kata (rata-rata ≤ 14), ada bagian 'wow'
  fakta     setiap angka di naskah (angka atau ditulis huruf) harus ada di fakta idea.json; status teknologi jujur
  gaya      tanpa basa-basi pembuka & ajakan subscribe di narasi; judul sesuai bible
  produksi  bagian, visual, jenis visual, kata kunci visual Inggris, teks layar ≤ 4 kata, kata penekanan, komentar pin
Keluar dengan kode 0 kalau LOLOS, 1 kalau ada GAGAL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WPS = 2.3            # kata per detik, suara Ardi +15% (diukur dari video sungguhan)
BAGIAN = {"hook", "konteks", "cara_kerja", "wow", "bukti", "dampak", "penutup"}
SUASANA = {"tegang", "ceria", "misterius", "epik", "haru"}
JENIS = {"footage", "ai", "grafis"}
PENUTUP = {"loop", "pertanyaan", "kesimpulan"}
FILLER = re.compile(r"\b(halo|hai|hi) (guys|semua|teman)|di video kali ini|jangan lupa (like|subscribe|follow)|tonton sampai (habis|akhir)|"
                    r"tanpa basa.?basi|langsung saja|oke guys|nah guys", re.I)
GANTUNG = re.compile(r"(\.\.\.|…|\b(dan|tapi|karena|yang|atau|serta|lalu|kemudian|untuk|dengan|bahwa|jadi)\s*[.!?]?)\s*$", re.I)
JUAL = re.compile(r"\b(sudah|udah|bisa|sudah bisa) (dijual|dibeli|dipesan)|tersedia di (pasaran|toko)|dijual bebas", re.I)



def words(text: str) -> list[str]:
    return re.findall(r"[\w'’-]+", text)


def kata_ke_angka(text: str) -> list[float]:
    """'dua ratus empat puluh' → 240, 'seribu lima ratus' → 1500, 'nol koma satu' → 0.1."""
    toks = re.findall(r"[a-z]+", text.lower())
    satuan = {"nol": 0, "satu": 1, "dua": 2, "tiga": 3, "empat": 4, "lima": 5, "enam": 6, "tujuh": 7, "delapan": 8, "sembilan": 9}
    khusus = {"sepuluh": 10, "sebelas": 11, "seratus": 100}
    besar = {"ribu": 1000, "juta": 10 ** 6, "miliar": 10 ** 9, "triliun": 10 ** 12}
    awal_besar = {"seribu": 1000, "sejuta": 10 ** 6}
    out, i = [], 0
    while i < len(toks):
        if toks[i] not in satuan and toks[i] not in khusus and toks[i] not in awal_besar:
            i += 1
            continue
        total = seg = last = 0
        j = i
        while j < len(toks):
            w = toks[j]
            if w in satuan:
                seg += satuan[w]
                last = satuan[w]
            elif w in khusus:
                seg += khusus[w]
                last = 0
            elif w == "belas":
                seg += 10
                last = 0
            elif w == "puluh":
                seg += last * 9
                last = 0
            elif w == "ratus":
                seg += last * 99
                last = 0
            elif w in besar:
                total += (seg or 1) * besar[w]
                seg = last = 0
            elif w in awal_besar:
                total += awal_besar[w]
            else:
                break
            j += 1
        val = float(total + seg)
        if j < len(toks) - 1 and toks[j] == "koma" and toks[j + 1] in satuan:
            val = float(f"{int(val)}.{satuan[toks[j + 1]]}")
            j += 2
        out.append(val)
        i = max(j, i + 1)
    return out


def angka_digit(text: str) -> list[float]:
    out = []
    for m in re.findall(r"\d+(?:[.,]\d+)*", text):
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", m):          # 2.000 (gaya Indonesia)
            out.append(float(m.replace(".", "")))
        else:
            out.append(float(m.replace(",", ".").replace(".", ".", 1)) if m.count(",") <= 1 and m.count(".") <= 1 else float(re.sub(r"[.,]", "", m)))
    return out


def check(slug: str) -> tuple[list[str], list[str], dict, dict]:
    fails, warns, info = [], [], {}
    folder = ROOT / "videos" / slug
    path = folder / "script.json"
    if not path.exists():
        return [f"{path.relative_to(ROOT)} tidak ada"], warns, info, {}
    try:
        s = json.loads(path.read_text(encoding="utf-8-sig"))
    except ValueError as err:
        return [f"script.json bukan JSON valid: {err}"], warns, info, {}
    try:
        idea = json.loads((folder / "idea.json").read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        idea = {}
        warns.append("idea.json tidak bisa dibaca; angka & sumber tidak bisa dicocokkan")

    for key in ("judul", "hook_teks", "narasi", "deskripsi", "tag", "sumber"):
        if not s.get(key):
            fails.append(f"field '{key}' kosong atau tidak ada")
    if fails:
        return fails, warns, info, s

    # ---- judul & teks layar
    judul = s["judul"].strip()
    if not judul.endswith("#Shorts #Teknologi"):
        fails.append("judul harus diakhiri tepat '#Shorts #Teknologi'")
    if len(judul) > 100:
        fails.append(f"judul {len(judul)} karakter (maksimal 100)")
    klaim = judul.replace("#Shorts #Teknologi", "").strip()
    huruf = [c for c in re.split(r"[!?]", klaim)[0] if c.isalpha()]
    if huruf and sum(c.isupper() for c in huruf) / len(huruf) < 0.8:
        warns.append("bagian klaim judul sebaiknya HURUF KAPITAL")
    if len(s.get("judul_alternatif") or []) < 2:
        fails.append("judul_alternatif minimal 2 (untuk uji judul oleh Steve)")
    if len(words(s["hook_teks"])) > 6:
        fails.append(f"hook_teks {len(words(s['hook_teks']))} kata (maksimal 6)")
    if not str(s.get("komentar_pin", "")).strip():
        fails.append("komentar_pin kosong (pertanyaan untuk memancing komentar, dipin saat upload)")
    if s.get("suasana") not in SUASANA:
        fails.append(f"suasana harus salah satu: {', '.join(sorted(SUASANA))}")
    if s.get("penutup_tipe") not in PENUTUP:
        fails.append(f"penutup_tipe harus salah satu: {', '.join(sorted(PENUTUP))}")

    # ---- narasi
    narasi = s["narasi"]
    if not isinstance(narasi, list) or not all(isinstance(n, dict) for n in narasi):
        return fails + ["narasi harus berupa daftar objek"], warns, info, s
    if not 6 <= len(narasi) <= 14:
        fails.append(f"narasi {len(narasi)} kalimat (6–14)")
    panjang = []
    for i, n in enumerate(narasi, 1):
        k = str(n.get("kalimat", "")).strip()
        w = len(words(k))
        panjang.append(w)
        if not k:
            fails.append(f"kalimat {i} kosong")
            continue
        if w > 22:
            fails.append(f"kalimat {i} terlalu panjang ({w} kata, maks 22) — pecah supaya enak didengar")
        if n.get("bagian") not in BAGIAN:
            fails.append(f"kalimat {i}: 'bagian' harus salah satu {', '.join(sorted(BAGIAN))}")
        if len(str(n.get("visual", "")).strip()) < 8:
            fails.append(f"kalimat {i}: petunjuk visual kurang konkret")
        if n.get("jenis_visual") not in JENIS:
            fails.append(f"kalimat {i}: jenis_visual harus footage/ai/grafis")
        if n.get("jenis_visual") in ("footage", "ai") and not n.get("kata_kunci_visual"):
            fails.append(f"kalimat {i}: kata_kunci_visual (Inggris) kosong")
        tl = n.get("teks_layar")
        if tl and len(words(str(tl))) > 4:
            fails.append(f"kalimat {i}: teks_layar maksimal 4 kata")
        for p in n.get("penekanan") or []:
            if str(p).lower() not in k.lower():
                fails.append(f"kalimat {i}: kata penekanan '{p}' tidak ada di kalimatnya")
        if FILLER.search(k):
            fails.append(f"kalimat {i}: basa-basi/ajakan subscribe ('{FILLER.search(k).group(0)}') — buang, langsung ke isi")
        if re.search(r"\d{4,}|\d+[.,]\d{3}", k):
            warns.append(f"kalimat {i} memuat angka panjang; tulis dengan huruf supaya TTS membacanya benar")
    if panjang and sum(panjang) / len(panjang) > 14:
        warns.append(f"rata-rata {sum(panjang) / len(panjang):.1f} kata per kalimat; Shorts enak di 8–13")

    if narasi[0].get("bagian") != "hook":
        fails.append("kalimat 1 harus bagian 'hook'")
    if panjang and panjang[0] > 12:
        fails.append(f"hook {panjang[0]} kata; harus ≤ 12 supaya selesai dalam ±3 detik")
    akhir = str(narasi[-1].get("kalimat", "")).strip()
    if narasi[-1].get("bagian") != "penutup":
        fails.append("kalimat terakhir harus bagian 'penutup'")
    if GANTUNG.search(akhir) or not re.search(r"[.!?]$", akhir):
        fails.append(f"penutup menggantung: \"{akhir[-60:]}\" — akhiri dengan kalimat utuh (titik/tanda tanya/seru)")
    if len(words(akhir)) < 5:
        fails.append("penutup terlalu pendek; beri kesimpulan atau pertanyaan yang tuntas")
    if not any(n.get("bagian") == "wow" for n in narasi):
        fails.append("belum ada bagian 'wow' (fakta paling mengejutkan)")
    if not any(re.search(r"\b(tapi|ternyata|yang (paling|lebih)|bayangin|bukan cuma|masalahnya|anehnya)\b", str(n.get("kalimat", "")), re.I) for n in narasi[:4]):
        warns.append("belum ada 'open loop' di 4 kalimat awal (misalnya 'tapi yang paling gila…') untuk menahan penonton")

    # ---- durasi
    total = sum(panjang)
    target = s.get("target_durasi")
    info.update(kata=total, durasi_detik=round(total / WPS, 1), target=target)
    if not isinstance(target, (int, float)) or not 25 <= target <= 58:
        fails.append("target_durasi (detik) harus 25–58, dipilih sesuai kebutuhan topik")
    else:
        ideal = target * WPS
        if not ideal * 0.88 <= total <= ideal * 1.12:
            fails.append(f"{total} kata ≈ {total / WPS:.0f} detik, tidak cocok dengan target {target} detik (ideal {ideal * 0.88:.0f}–{ideal * 1.12:.0f} kata)")

    # ---- fakta: angka & status
    teks_naskah = " ".join(str(n.get("kalimat", "")) for n in narasi) + " " + str(s.get("hook_teks", "")) + " " + " ".join(str(n.get("teks_layar") or "") for n in narasi)
    sumber_angka = " ".join(str(f.get("klaim", "")) + " " + str(f.get("kutipan", "")) for f in idea.get("fakta", [])) + " " + " ".join(str(a.get("angka", "")) for a in idea.get("angka_kunci", []))
    boleh = set(angka_digit(sumber_angka)) | set(kata_ke_angka(sumber_angka))
    if idea:
        for v in set(angka_digit(teks_naskah)) | set(kata_ke_angka(teks_naskah)):
            if (v >= 10 or v != int(v)) and v not in boleh and not any(abs(v - b) / max(b, 1) < 0.01 for b in boleh):
                fails.append(f"angka {v:g} tidak ada di fakta idea.json (jangan mengarang angka)")
        if idea.get("status_teknologi") in ("prototipe", "riset"):
            for i, n in enumerate(narasi, 1):
                m = JUAL.search(str(n.get("kalimat", "")))
                if m and not re.search(r"\b(belum|tidak|nggak|gak)\b", str(n.get("kalimat", "")), re.I):
                    fails.append(f"kalimat {i}: '{m.group(0)}' padahal status teknologi {idea['status_teknologi']}")

    # ---- metadata
    tags = s["tag"]
    if not isinstance(tags, list) or not 8 <= len(tags) <= 15:
        fails.append("tag harus daftar 8–15 item")
    elif any(str(t).startswith("#") for t in tags):
        fails.append("tag ditulis tanpa '#'")
    sumber = [u for u in s["sumber"] if isinstance(u, str)]
    if len(sumber) < 2 or not all(u.startswith("http") for u in sumber):
        fails.append("minimal 2 URL sumber yang valid")
    elif idea:
        known = {f.get("sumber_url") for f in idea.get("fakta", [])}
        unknown = [u for u in sumber if u not in known]
        if unknown:
            fails.append(f"{len(unknown)} sumber tidak ada di idea.json (jangan menambah fakta baru)")
        if not any(u in s["deskripsi"] for u in sumber):
            warns.append("deskripsi sebaiknya mencantumkan URL sumber")
    return fails, warns, info, s


def naskah_md(s: dict, info: dict) -> str:
    L = [f"# {s.get('judul', '')}", "",
         f"**Hook layar:** {s.get('hook_teks', '')} · **Target:** {s.get('target_durasi')} dtk ({info.get('kata')} kata ≈ {info.get('durasi_detik')} dtk) · "
         f"**Suasana:** {s.get('suasana')} · **Penutup:** {s.get('penutup_tipe')}", "",
         "| # | Bagian | Kalimat (dibacakan) | Teks layar | Visual |", "|---|---|---|---|---|"]
    for i, n in enumerate(s.get("narasi", []), 1):
        k = str(n.get("kalimat", ""))
        for p in n.get("penekanan") or []:
            k = re.sub(re.escape(str(p)), f"**{p}**", k, count=1, flags=re.I)
        L.append(f"| {i} | {n.get('bagian', '')} | {k} | {n.get('teks_layar') or ''} | {n.get('jenis_visual', '')}: {n.get('visual', '')} |")
    L += ["", "## Judul alternatif"] + [f"- {j}" for j in s.get("judul_alternatif", [])]
    L += ["", f"## Komentar pin\n{s.get('komentar_pin', '')}", "", f"## Deskripsi\n{s.get('deskripsi', '')}", "",
          f"## Tag\n{', '.join(s.get('tag', []))}", "", f"## Catatan editor\n{s.get('catatan_editor', '-')}"]
    return "\n".join(L) + "\n"


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1:
        sys.exit("Pemakaian: python agents/penulis/cek_naskah.py <slug> [--tulis]")
    slug = args[0]
    fails, warns, info, s = check(slug)
    for f in fails:
        print(f"GAGAL  {f}")
    for w in warns:
        print(f"SARAN  {w}")
    if info:
        print(f"INFO   {info.get('kata')} kata ≈ {info.get('durasi_detik')} detik (target {info.get('target')} detik)")
    if "--tulis" in sys.argv and s and not fails:
        (ROOT / "videos" / slug / "naskah.md").write_text(naskah_md(s, info), encoding="utf-8")
        print(f"INFO   naskah.md ditulis (videos/{slug}/naskah.md)")
    print("LOLOS" if not fails else f"{len(fails)} masalah harus diperbaiki")
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()

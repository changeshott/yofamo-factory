#!/usr/bin/env python3
"""Kai v3 — lapisan HyperFrames (HTML + GSAP → video). Dipanggil oleh rakit.py, bukan dijalankan langsung.

Alur: rakit.py membuat base.mp4 (shot Bima + transisi + gerak + audio campur, TANPA teks) →
komposisi.py menulis proyek HyperFrames di videos/<slug>/export/hf/ (index.html + assets) berisi
hook bertingkat, subtitle 1 kata, grafis gerak sesuai kalimat, aksen transisi, progres, penutup →
`hyperframes render` → audio base.mp4 ditempel lagi → export/final.mp4.

Butuh Node.js 22+ dan `npm install` di folder project (paket hyperframes & gsap di package.json).
Kalau tidak ada, rakit.py otomatis memakai mesin ffmpeg (subtitle ASS).
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("hf_template.html")
HF_BIN = ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
GSAP = ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js"
FONTS = ROOT / "fonts"
WARNA_STATUS = {"riset": "7B6CFF", "prototipe": "2D8CFF", "dipakai": "13B981", "dijual": "13B981"}
LABEL_STATUS = {"riset": "MASIH RISET", "prototipe": "PROTOTIPE", "dipakai": "SUDAH DIPAKAI", "dijual": "SUDAH DIJUAL"}

# Variasi gaya gerak: tiap video memakai kombinasi berbeda supaya channel tidak terasa template yang itu-itu saja.
# Semua varian tetap halus (tanpa memantul) dan tetap di palet biru channel.
VARIAN = {
    "hook": ["naik", "skala", "geser", "ketik", "sapu"],          # cara hook bertingkat muncul
    "sub": ["naik", "pop", "geser", "sapu", "fokus"],             # cara subtitle 1 kata muncul
    "stabilo": ["blok", "garis", "miring", "teks"],               # penanda kata penekanan
    "kartu": ["kaca", "solid", "neon", "putih"],                  # kulit kartu grafis
    "masuk": ["naik", "geser", "skala", "lipat"],                 # cara kartu grafis masuk
    "layar": ["kisi", "cincin", "garis", "titik"],                # latar grafis layar penuh
    "aksen": ["sapuan", "bingkai", "garis", "denyut"],            # aksen di pergantian kalimat
    # warna aksen (utama, terang): nuansa biru khas channel + warna suasana (dipilih menurut suasana naskah, lihat PALET_SUASANA)
    "palet": ["biru", "elektrik", "langit", "samudra", "kobalt", "bara", "magma", "jeruk", "toska", "ungu", "nila", "emas", "magenta", "mint", "mawar"],
}
PALET = {"biru": ("2D8CFF", "6FD3FF"), "elektrik": ("1F6FFF", "7FD8FF"), "langit": ("3B9BFF", "9AD8FF"),
         "samudra": ("0EA5E9", "7DD3FC"), "kobalt": ("2563EB", "8EC5FF"),
         "bara": ("FF4D3D", "FFB3A6"), "magma": ("FF7A1A", "FFC78A"), "jeruk": ("FF8A1F", "FFD09A"), "toska": ("14B8A6", "7FE7DA"),
         "ungu": ("8B5CF6", "C9B8FF"), "nila": ("6366F1", "B4B8FF"), "emas": ("F59E0B", "FFD98A"), "magenta": ("EC4899", "FFB3D6"),
         "mint": ("10B981", "86EFC5"), "mawar": ("FB7185", "FFC2CB")}
# Warna mengikuti SUASANA suara & naskah (Zona, Nov 2026: gaya beraneka ragam & sesuai suara): tiap suasana punya 2 warna khas
# + 2 nuansa biru channel; yang paling jarang dipakai video lain yang dipilih.
PALET_SUASANA = {"tegang": ["bara", "magma", "kobalt", "elektrik"], "ceria": ["jeruk", "toska", "langit", "biru"],
                 "misterius": ["ungu", "nila", "kobalt", "samudra"], "epik": ["emas", "magenta", "elektrik", "biru"],
                 "haru": ["mint", "mawar", "langit", "samudra"]}
SATUAN = (r"kilowatt jam|kwh|kilowatt|watt|kw|mah|volt|ampere|persen|%|derajat|°c|km/jam|kilometer|km|meter|cm|mm|milimeter|kilogram|kg|gram|"
          r"ton|liter|jam|menit|detik|hari|minggu|bulan|tahun|juta|miliar|triliun|ribu|rupiah|dolar|megapiksel|mp|hz|hertz|gb|tb|inci|kali lipat|kali|x")


def tersedia() -> tuple[bool, str]:
    """Apakah mesin HyperFrames bisa dipakai di komputer ini."""
    node = shutil.which("node")
    if not node:
        return False, "Node.js belum terpasang"
    try:
        v = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20).stdout.strip()
        if int(re.sub(r"[^\d.]", "", v).split(".")[0]) < 22:
            return False, f"Node.js {v} terlalu lama (butuh 22+)"
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return False, "Node.js tidak bisa dijalankan"
    if not HF_BIN.exists() or not GSAP.exists():
        return False, "paket hyperframes/gsap belum terpasang (jalankan: npm install di folder project)"
    return True, "ok"


def _kunci(t: str) -> str:
    return re.sub(r"[^0-9a-z]", "", t.lower())


def pilih_gaya(slug: str, videos: Path, st: dict | None = None, suasana: str = "") -> dict:
    """Pilih kombinasi gaya gerak untuk satu video: tiap unsur memakai varian yang paling jarang dipakai video lain
    dan tidak sama dengan video sebelumnya. Video yang dirakit ulang (Rara) memakai gaya yang sama seperti sebelumnya."""
    st = st or {}
    if st.get("variasi") is False:
        return {k: v[0] for k, v in VARIAN.items()}
    lama = videos / slug / "export" / "info.json"
    try:
        g0 = json.loads(lama.read_text(encoding="utf-8")).get("gaya_gerak") if lama.exists() else None
    except (OSError, ValueError):
        g0 = None
    if isinstance(g0, dict) and all(g0.get(k) in v for k, v in VARIAN.items()):
        return {k: g0[k] for k in VARIAN} | {"transisi_acak": g0.get("transisi_acak", slug)}
    riwayat = []
    for f in videos.glob("*/export/info.json"):
        if f.parent.parent.name == slug:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(d.get("gaya_gerak"), dict):
            riwayat.append((str(d.get("dibuat", "")), d["gaya_gerak"]))
    riwayat.sort(key=lambda x: x[0])
    lalu = [g for _, g in riwayat]
    h = int(hashlib.sha1(slug.encode()).hexdigest(), 16)
    gaya = {}
    for n, (k, opsi) in enumerate(VARIAN.items()):
        if k == "palet":
            opsi = PALET_SUASANA.get(str(suasana).lower()) or ["biru", "elektrik", "langit", "samudra", "kobalt"]
        hitung = {o: sum(1 for g in lalu if g.get(k) == o) for o in opsi}
        baru = lalu[-1].get(k) if lalu else None
        gaya[k] = min(opsi, key=lambda o: (o == baru, hitung[o], ((h >> (n * 6)) + opsi.index(o) * 37) % 101))
    gaya["transisi_acak"] = slug
    return gaya


def urut_transisi(daftar: list[str], gaya: dict) -> list[str]:
    """Urutan transisi antar-kalimat diacak per video (tetap sama kalau video dirakit ulang)."""
    d = list(daftar)
    random.Random(str(gaya.get("transisi_acak", ""))).shuffle(d)
    return d


def grafis_kalimat(i: int, n: dict, kal: dict, idea: dict, senyap: list[tuple[float, float]]) -> list[dict]:
    """Grafis gerak untuk satu kalimat: dari naskah Raka (grafis_gerak), angka kunci Nova, teks layar, atau status."""
    a = float(kal["mulai"]) + 0.08
    b = min(float(kal["selesai"]) + 0.05, a + 3.6)
    if b - a < 0.9 or any(x <= (a + b) / 2 < y for x, y in senyap):
        return []
    out = []
    gg = n.get("grafis_gerak")
    teks_kal = str(n.get("kalimat", ""))
    if isinstance(gg, dict) and gg.get("tipe") in ("angka", "label", "kata", "perbandingan", "langkah", "status"):
        g = {k: v for k, v in gg.items() if isinstance(v, (str, int, float, list))}
        if g["tipe"] == "langkah":
            g["poin"] = [str(p)[:28] for p in (g.get("poin") or [])][:4]
            if len(g["poin"]) < 2:
                g = {}
        if g:
            out.append({**g, "a": a, "b": b})
    if not out:
        for ak in idea.get("angka_kunci") or []:
            angka = str(ak.get("angka", "")).strip() if isinstance(ak, dict) else ""
            if angka and re.search(rf"(?<!\d){re.escape(angka)}(?!\d)", teks_kal):
                out.append({"tipe": "angka", "angka": angka, "akhiran": str(ak.get("akhiran", "")), "label": str(ak.get("label", ""))[:48],
                            "judul": "faktanya", "a": a, "b": b})
                break
    if not out and str(n.get("teks_layar") or "").strip():
        t = str(n["teks_layar"]).strip().upper()
        out.append({"tipe": "kata" if (t.endswith("!") or len(t.split()) <= 2) else "label", "teks": t, "a": a, "b": b})
    if not out and n.get("bagian") == "konteks":
        st = str(idea.get("status_teknologi", "")).lower()
        if st in LABEL_STATUS:
            out.append({"tipe": "status", "teks": LABEL_STATUS[st], "warna": WARNA_STATUS[st], "a": a, "b": b})
    if n.get("bagian") == "konteks":
        sumber = next((f.get("sumber_nama") for f in idea.get("fakta") or [] if isinstance(f, dict) and f.get("sumber_nama")
                       and (f.get("tier") == 1 or f.get("jenis_sumber") == "resmi")), None)
        if sumber:
            out.append({"tipe": "sumber", "teks": f"Sumber: {str(sumber)[:34]}", "a": a, "b": min(b + 0.6, float(kal["selesai"]) + 0.6)})
    return out


def angka_otomatis(narasi: list[dict], kalimat: list[dict], sudah: list[dict], hook_end: float, senyap: list[tuple[float, float]]) -> list[dict]:
    """Kalimat yang menyebut ANGKA + satuan tapi belum punya grafis → kartu angka otomatis (yang didengar = yang terlihat).
    Hanya angka yang tertulis sebagai digit di naskah; maksimal satu tiap dua kalimat; tidak di hook & penutup."""
    out, terakhir = [], -9
    for k in kalimat:
        i = int(k.get("i", -1))
        if i <= 0 or i >= len(narasi) or narasi[i].get("bagian") in ("hook", "penutup") or i - terakhir < 2:
            continue
        a, b = float(k["mulai"]) + 0.08, min(float(k["selesai"]) + 0.05, float(k["mulai"]) + 3.6)
        if b - a < 1.2 or float(k["mulai"]) < hook_end or any(x <= (a + b) / 2 < y for x, y in senyap):
            continue
        if any(g["a"] < b and a < g["b"] and g.get("tipe") not in ("sumber",) for g in sudah + out):
            continue
        m = re.search(rf"(?<![\w.,])(\d{{1,3}}(?:[.,]\d{{1,3}})*)\s*({SATUAN})\b", str(narasi[i].get("kalimat", "")), re.I)
        if not m:
            continue
        sisa = str(narasi[i]["kalimat"])[m.end():].split()
        label = " ".join([m.group(2)] + [re.sub(r"[.,!?]+$", "", w) for w in sisa[:2] if not re.match(r"^(dan|yang|dengan|untuk|atau|tapi|jadi)\b", w, re.I)])
        out.append({"tipe": "angka", "angka": m.group(1), "akhiran": "", "label": label.strip()[:40], "judul": "faktanya", "a": a, "b": b, "otomatis": True})
        terakhir = i
    return out


def sinkron_kata(grafis: list[dict], kata: list[dict], kalimat: list[dict]) -> None:
    """Grafis muncul TEPAT saat kata kuncinya diucapkan (bukan di awal kalimat): kartu angka saat angkanya disebut, kata/label
    saat kata pertamanya disebut. Kalau katanya tidak ketemu atau sisa waktunya terlalu pendek, waktu awal dibiarkan."""
    for g in grafis:
        kunci = g.get("angka") if g.get("tipe") == "angka" else (str(g.get("teks") or "").split() or [""])[0] if g.get("tipe") in ("kata", "label") else ""
        kunci = _kunci(str(kunci))
        if not kunci:
            continue
        kal = next((k for k in kalimat if float(k["mulai"]) - 0.1 <= g["a"] <= float(k["selesai"])), None)
        if not kal:
            continue
        w = next((x for x in kata if float(kal["mulai"]) - 0.05 <= x["a"] <= float(kal["selesai"]) and _kunci(x["t"]).startswith(kunci[:6])), None)
        if w and g["b"] - (w["a"] - 0.1) >= 1.1 and w["a"] - 0.1 > g["a"]:
            g["a"] = round(w["a"] - 0.1, 3)
            g["sinkron"] = True


def grafis_otomatis(st: dict, idea: dict, script: dict, narasi: list[dict], kalimat: list[dict], sudah: list[dict],
                    hook_end: float, total: float, senyap: list[tuple[float, float]]) -> list[dict]:
    """Grafis yang ditambahkan Kai sendiri (tanpa menunggu naskah):
    - tanda PRODUK: nama produk (idea.json → produk) + status, tepat setelah hook — penonton langsung tahu barang apa yang dibahas;
    - ajakan KOMENTAR di kalimat penutup (kalau kalimat itu belum punya grafis)."""
    out = []
    oto = st.get("grafis_otomatis") or {}
    bentrok = lambda a, b, tipe: any(g["a"] < b and a < g["b"] and g.get("tipe") in tipe for g in sudah)  # noqa: E731
    produk = str(idea.get("produk") or "").strip()
    if oto.get("tanda_produk", True) and produk and len(produk) <= 40:
        a = max(hook_end + 0.15, 0.3)
        b = min(a + float(oto.get("tanda_produk_detik", 3.4)), total - 0.5)
        stt = str(idea.get("status_teknologi", "")).lower()
        if b - a >= 1.5 and not any(x <= a < y for x, y in senyap):
            for g in sudah:                                       # pil status di jendela yang sama digantikan tanda produk
                if g.get("tipe") == "status" and g["a"] < b and a < g["b"]:
                    g["tipe"] = "_buang"
            out.append({"tipe": "produk", "teks": produk.upper() if len(produk) <= 18 else produk, "ket": LABEL_STATUS.get(stt, ""),
                        "warna": WARNA_STATUS.get(stt, ""), "a": round(a, 3), "b": round(b, 3)})
    sudah[:] = [g for g in sudah if g.get("tipe") != "_buang"]
    if oto.get("ajakan_komentar", True):
        akhir = next((k for k in reversed(kalimat) if int(k.get("i", -1)) < len(narasi) and narasi[int(k["i"])].get("bagian") == "penutup"), None)
        if akhir:
            a, b = float(akhir["mulai"]) + 0.3, min(float(akhir["selesai"]) + 0.1, total)
            teks = str(oto.get("ajakan_teks", "Menurut kamu?"))[:28]
            if b - a >= 1.4 and not bentrok(a, b, ("angka", "label", "kata", "perbandingan", "langkah", "status", "produk")):
                out.append({"tipe": "tanya", "teks": teks, "a": round(a, 3), "b": round(b, 3)})
    return out


def layar_penuh(klip: list[dict]) -> list[dict]:
    """Kartu grafis Bima (shot jenis 'grafis') digambar ulang HyperFrames sebagai layar penuh bergerak."""
    out = []
    for k in klip:
        sp = k.get("spec") if isinstance(k.get("spec"), dict) else {"gaya": "teks", "teks": k.get("judul", "")}
        gaya = "angka" if sp.get("gaya") == "angka" and str(sp.get("angka", "")).strip() else "teks"
        teks = str(sp.get("teks") or k.get("judul") or "").strip()
        if gaya == "teks" and not teks:
            continue
        out.append({"gaya": gaya, "a": round(float(k["mulai"]), 3), "b": round(float(k["selesai"]), 3),
                    "angka": str(sp.get("angka", "")), "akhiran": str(sp.get("akhiran", "")), "label": str(sp.get("label", ""))[:60],
                    "teks": teks[:90]})
    return out


def objek_hook(png: Path | None, st: dict) -> dict | None:
    """Objek Mila (PNG transparan) di belakang tulisan hook: posisi sama persis dengan thumbnail."""
    if not png or not Path(png).exists():
        return None
    try:
        from PIL import Image
        with Image.open(png) as im:
            ukuran = im.size
    except Exception:  # noqa: BLE001
        return None
    t = st.get("thumbnail") or {}
    s = min(int(t.get("objek_lebar_maks", 900)) / ukuran[0], int(t.get("objek_tinggi_maks", 840)) / ukuran[1])
    w, h = round(ukuran[0] * s), round(ukuran[1] * s)
    cy = int(st.get("hyperframes", {}).get("hook_y", 1000)) - int(t.get("objek_naik", 290))
    return {"src": "assets/objek.png", "file": str(png), "x": (1080 - w) // 2, "y": cy - h // 2, "w": w, "h": h}


def data_video(st: dict, script: dict, idea: dict, words: dict, narasi: list[dict], total: float, akhir: float,
               senyap: list[tuple[float, float]], hook_baris: list[tuple[str, str, float]], hook_end: float,
               tekan: set[tuple[int, str]], kal_dari, klip_grafis: list[dict] | None = None, gaya: dict | None = None,
               objek: Path | None = None, shot: list[float] | None = None) -> dict:
    hf = st.get("hyperframes", {})
    gaya = gaya or {k: v[0] for k, v in VARIAN.items()}
    warna = {k: str(v).lstrip("#") for k, v in (st.get("palet") or {}).items() if k in ("utama", "terang", "gelap", "kuning")}
    utama0 = warna.get("utama", "2D8CFF").upper()
    if gaya.get("palet") in PALET and gaya["palet"] != "biru":
        warna["utama"], warna["terang"] = PALET[gaya["palet"]]
    sub, hk = st["subtitle"], st["hook"]
    kalimat = words.get("kalimat", [])
    kata = []
    ws = words.get("kata", [])
    for n, w in enumerate(ws):
        a0 = float(w["mulai"])
        if a0 < hook_end - 0.05 or any(x <= a0 + 0.05 < y for x, y in senyap):
            continue
        t = re.sub(r"[.,;:\"“”()\[\]…]+", "", str(w["kata"])).strip()
        if not t:
            continue
        t = t.upper() if sub.get("huruf_besar", True) else t
        nxt = float(ws[n + 1]["mulai"]) if n + 1 < len(ws) else None
        b0 = nxt if nxt is not None and nxt - float(w["selesai"]) < 0.4 else float(w["selesai"]) + 0.15
        b0 = min(b0, total)
        if b0 - a0 < 0.04:
            continue
        kata.append({"t": t, "a": round(a0, 3), "b": round(b0, 3), "tekan": (kal_dari(kalimat, a0), _kunci(w["kata"])) in tekan})
    grafis = []
    for k in kalimat:
        i = int(k.get("i", -1))
        if i <= 0 or i >= len(narasi) or float(k["mulai"]) < hook_end:
            continue
        grafis += grafis_kalimat(i, narasi[i], k, idea, senyap)
    potong = [{"t": round(float(k["mulai"]), 3), "wow": (narasi[int(k["i"])].get("bagian") == "wow") if int(k["i"]) < len(narasi) else False}
              for k in kalimat if int(k.get("i", 0)) > 0]
    grafis += grafis_otomatis(st, idea, script, narasi, kalimat, grafis, hook_end, total, senyap)
    layar = layar_penuh(klip_grafis or [])
    if (st.get("grafis_otomatis") or {}).get("angka", True):
        grafis += [g for g in angka_otomatis(narasi, kalimat, grafis, hook_end, senyap) if not any(L["a"] < g["b"] and g["a"] < L["b"] for L in layar)]
    sinkron_kata(grafis, kata, kalimat)
    # grafis kecil tidak boleh menimpa layar penuh (kartu grafis Bima yang digambar ulang)
    grafis = [g for g in grafis if g.get("tipe") not in ("tanya", "produk") or not any(L["a"] < g["b"] and g["a"] < L["b"] for L in layar)]
    km = st.get("kamera") or {}
    pn = dict(st.get("penutup", {}))
    try:        # ada video panjang tentang produk yang sama → penutup mengajak menonton versi lengkap (jam tonton = syarat monetisasi)
        sys.path.insert(0, str(ROOT / "agents" / "upload"))
        import terkait
        if pn.get("teks") and terkait.versi_panjang(idea):
            pn["teks"] = str(pn.get("teks_versi_panjang") or "Versi lengkapnya ada di channel ini")
    except Exception:  # noqa: BLE001
        pass
    return {
        "kamera": {"kuat": float(km.get("kuat", 1.0)), "grade": bool(km.get("warna_sinematik", True))},
        "shot": sorted({round(float(t), 3) for t in (shot or []) if 0 <= float(t) < total}),
        "total": round(total, 3), "akhir": round(akhir, 3), "handle": st.get("handle", {}).get("teks", ""),
        "warna": warna, "gaya": {k: v for k, v in gaya.items() if k in VARIAN},
        "sub": {"px": int(hf.get("subtitle_px", 104)), "min": int(hf.get("subtitle_min", 60)), "y": int(hf.get("subtitle_y", 1180))},
        "zona_grafis": int(hf.get("zona_grafis_atas", 430)),
        "hook": {"akhir": round(hook_end, 3), "y": int(hf.get("hook_y", 1000)), "rapat": float(hk.get("jarak_baris", 0.8)) + 0.12,
                 "tinggi_maks": int(hk.get("tinggi_maks", 900)), "jeda": float(hk.get("jeda_baris", 0.09)) + 0.03,
                 "baris": [{"teks": t, "warna": warna.get("utama", w) if w.upper().lstrip("#") == utama0 else w, "maks": int(float(hf.get("hook_px_maks", 230)) * sk)} for t, w, sk in hook_baris]},
        "objek": objek_hook(objek, st) if hook_baris and hook_end > 0 else None,
        "kata": kata, "grafis": grafis, "potong": potong, "layar": layar,
        "penutup": {"a": round(total, 3), "b": round(akhir, 3), "teks": str(pn.get("teks", ""))} if akhir > total + 0.05 and pn.get("teks") else None,
    }


def tulis_proyek(hf_dir: Path, base_mp4: Path, data: dict, judul: str) -> Path:
    (hf_dir / "assets" / "fonts").mkdir(parents=True, exist_ok=True)
    tujuan = hf_dir / "assets" / "base.mp4"
    tujuan.unlink(missing_ok=True)
    try:
        os.link(base_mp4, tujuan)               # tanpa menyalin kalau satu drive
    except OSError:
        shutil.copy2(base_mp4, tujuan)
    shutil.copy2(GSAP, hf_dir / "assets" / "gsap.min.js")
    ob = data.get("objek") or {}
    if ob.get("file") and Path(ob["file"]).exists():
        shutil.copy2(ob["file"], hf_dir / "assets" / "objek.png")
        data = {**data, "objek": {k: v for k, v in ob.items() if k != "file"}}
    for f in ("Poppins-Black.ttf", "Poppins-ExtraBold.ttf"):
        if (FONTS / f).exists():
            shutil.copy2(FONTS / f, hf_dir / "assets" / "fonts" / f)
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__DATA__", json.dumps(data, ensure_ascii=False))
            .replace("__AKHIR__", f"{data['akhir']:.3f}")
            .replace("__JUDUL__", re.sub(r"[<>&]", "", judul)[:80]))
    (hf_dir / "index.html").write_text(html, encoding="utf-8")
    (hf_dir / "data.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    return hf_dir / "index.html"


def render(hf_dir: Path, out_mp4: Path, log) -> None:
    node = shutil.which("node")
    env = {**os.environ, "HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1", "HYPERFRAMES_NO_UPDATE_CHECK": "1",
           "HYPERFRAMES_SKIP_SKILLS": "1"}
    args = [node, str(HF_BIN), "render", str(hf_dir), "-o", str(out_mp4), "--fps", "30", "--quality", "high", "--quiet"]
    r = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0 or not out_mp4.exists():
        pesan = (r.stderr or r.stdout or "").strip().splitlines()
        raise RuntimeError("hyperframes render gagal: " + " | ".join(pesan[-6:])[:600])
    log(f"HyperFrames selesai: {out_mp4.name}")

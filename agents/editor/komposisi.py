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

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = Path(__file__).with_name("hf_template.html")
HF_BIN = ROOT / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
GSAP = ROOT / "node_modules" / "gsap" / "dist" / "gsap.min.js"
FONTS = ROOT / "fonts"
WARNA_STATUS = {"riset": "7B6CFF", "prototipe": "2D8CFF", "dipakai": "13B981", "dijual": "13B981"}
LABEL_STATUS = {"riset": "MASIH RISET", "prototipe": "PROTOTIPE", "dipakai": "SUDAH DIPAKAI", "dijual": "SUDAH DIJUAL"}


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


def data_video(st: dict, script: dict, idea: dict, words: dict, narasi: list[dict], total: float, akhir: float,
               senyap: list[tuple[float, float]], hook_baris: list[tuple[str, str, float]], hook_end: float,
               tekan: set[tuple[int, str]], kal_dari, klip_grafis: list[dict] | None = None) -> dict:
    hf = st.get("hyperframes", {})
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
    pn = st.get("penutup", {})
    return {
        "total": round(total, 3), "akhir": round(akhir, 3), "handle": st.get("handle", {}).get("teks", ""),
        "warna": {k: str(v).lstrip("#") for k, v in (st.get("palet") or {}).items() if k in ("utama", "terang", "gelap", "kuning")},
        "sub": {"px": int(hf.get("subtitle_px", 104)), "min": int(hf.get("subtitle_min", 60)), "y": int(hf.get("subtitle_y", 1180))},
        "zona_grafis": int(hf.get("zona_grafis_atas", 430)),
        "hook": {"akhir": round(hook_end, 3), "y": int(hf.get("hook_y", 1000)), "rapat": float(hk.get("jarak_baris", 0.8)) + 0.12,
                 "tinggi_maks": int(hk.get("tinggi_maks", 900)), "jeda": float(hk.get("jeda_baris", 0.09)) + 0.03,
                 "baris": [{"teks": t, "warna": w, "maks": int(float(hf.get("hook_px_maks", 230)) * sk)} for t, w, sk in hook_baris]},
        "kata": kata, "grafis": grafis, "potong": potong, "layar": layar_penuh(klip_grafis or []),
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

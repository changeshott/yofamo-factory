#!/usr/bin/env python3
"""Dara — agent suara Yofamo. Mengubah naskah Raka menjadi voice-over (gratis, edge-tts).

Pemakaian (dari root project):
    python agents/suara/buat_suara.py <slug>
    python agents/suara/buat_suara.py <slug> --voice id-ID-GadisNeural --rate +12%
    python agents/suara/buat_suara.py <slug> --uji      # tanpa internet: timing perkiraan, tanpa audio

Hasil di videos/<slug>/:
    vo.mp3          voice-over
    words.json      timing setiap kata + setiap kalimat (dipakai editor & caption)
    captions.srt    subtitle 1–3 kata per tampilan, siap diimpor ke CapCut
Status video menjadi 'suara'.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = ROOT / "videos"
DEFAULT_VOICE = "id-ID-ArdiNeural"
DEFAULT_RATE = "+10%"
TICKS = 10_000_000  # edge-tts memakai satuan 100 ns


def tokens(text: str) -> list[str]:
    return re.findall(r"[\w'’-]+", text, flags=re.UNICODE)


def norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


async def synth(text: str, voice: str, rate: str, out: Path) -> list[dict]:
    try:
        import edge_tts  # type: ignore
    except ImportError:
        sys.exit("[dara] Paket edge-tts belum terpasang. Jalankan: python -m pip install -r requirements.txt")
    comm = edge_tts.Communicate(text, voice, rate=rate, boundary="WordBoundary")
    words: list[dict] = []
    with out.open("wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                start = chunk["offset"] / TICKS
                words.append({"kata": chunk["text"], "mulai": round(start, 3), "selesai": round(start + chunk["duration"] / TICKS, 3)})
    return words


def estimate(sentences: list[str], rate: str) -> list[dict]:
    """Timing perkiraan untuk mode uji: ±2,6 kata/detik (disesuaikan rate), jeda di akhir kalimat."""
    m = re.match(r"([+-]\d+)%", rate)
    wps = 2.6 * (1 + (int(m.group(1)) if m else 0) / 100)
    t, out = 0.1, []
    for s in sentences:
        for w in tokens(s):
            d = max(0.14, (len(w) / 6) / wps - 0.02)
            out.append({"kata": w, "mulai": round(t, 3), "selesai": round(t + d, 3)})
            t += d + 0.02
        t += 0.22
    return out


def align_sentences(narasi: list[dict], words: list[dict]) -> list[dict]:
    """Petakan kata hasil TTS ke kalimat naskah secara berurutan, berdasarkan jumlah kata tiap kalimat.
    Kalimat terakhir mengambil sisa kata, supaya pemecahan kata yang sedikit berbeda tidak menggeser akhir video."""
    out, wi = [], 0
    for i, n in enumerate(narasi):
        count = len([t for t in tokens(n.get("kalimat", "")) if norm(t)])
        if not count or wi >= len(words):
            continue
        first = wi
        wi = len(words) if i == len(narasi) - 1 else min(len(words), wi + count)
        last = max(first, wi - 1)
        out.append({"i": i, "kalimat": n.get("kalimat", ""), "visual": n.get("visual", ""),
                    "mulai": words[first]["mulai"], "selesai": words[last]["selesai"]})
    return out


def srt_time(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{sec:02},{ms:03}"


def captions(words: list[dict], max_words: int = 3, max_gap: float = 0.35) -> str:
    """Kelompokkan 1–3 kata per tampilan; putus di jeda panjang atau akhir kalimat."""
    groups, cur = [], []
    for k, w in enumerate(words):
        cur.append(w)
        nxt = words[k + 1] if k + 1 < len(words) else None
        end_sentence = bool(re.search(r"[.!?…]$", w["kata"]))
        if len(cur) >= max_words or not nxt or end_sentence or nxt["mulai"] - w["selesai"] > max_gap:
            groups.append(cur); cur = []
    lines = []
    for n, g in enumerate(groups, 1):
        end = g[-1]["selesai"]
        if n < len(groups):
            end = min(max(end, g[-1]["selesai"] + 0.05), groups[n][0]["mulai"])
        text = " ".join(x["kata"] for x in g).upper()
        lines.append(f"{n}\n{srt_time(g[0]['mulai'])} --> {srt_time(end)}\n{text}\n")
    return "\n".join(lines)


def set_status(slug: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", slug, "suara", "--note", "dibuat Dara"], check=True, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dara: naskah → voice-over + timing + subtitle")
    ap.add_argument("slug")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="id-ID-ArdiNeural (pria) atau id-ID-GadisNeural (wanita)")
    ap.add_argument("--rate", default=DEFAULT_RATE, help="kecepatan, misalnya +10%%")
    ap.add_argument("--uji", action="store_true", help="tanpa internet: timing perkiraan, tanpa audio, status tidak diubah")
    args = ap.parse_args()

    if not re.fullmatch(r"[a-z0-9-]{3,80}", args.slug):
        sys.exit("[dara] slug tidak valid")
    if not re.fullmatch(r"[+-]\d{1,2}%", args.rate):
        sys.exit("[dara] rate harus seperti +10% atau -5%")
    folder = VIDEOS / args.slug
    script_path = folder / "script.json"
    if not script_path.exists():
        sys.exit(f"[dara] {script_path.relative_to(ROOT)} belum ada. Raka harus menulis naskahnya dulu.")
    script = json.loads(script_path.read_text(encoding="utf-8-sig"))
    narasi = [n for n in script.get("narasi", []) if str(n.get("kalimat", "")).strip()]
    if not narasi:
        sys.exit("[dara] naskah kosong")
    text = " ".join(n["kalimat"].strip() for n in narasi)

    print(f"[dara] {len(tokens(text))} kata, suara {args.voice}, kecepatan {args.rate}")
    if args.uji:
        words = estimate([n["kalimat"] for n in narasi], args.rate)
        print("[dara] MODE UJI: timing perkiraan, vo.mp3 tidak dibuat")
    else:
        tmp = folder / "vo.tmp.mp3"  # vo.mp3 lama tetap utuh kalau gagal di tengah jalan
        try:
            words = asyncio.run(synth(text, args.voice, args.rate, tmp))
        except Exception as err:  # jaringan / layanan TTS
            tmp.unlink(missing_ok=True)
            sys.exit(f"[dara] Gagal membuat suara: {err}. Cek koneksi internet lalu coba lagi.")
        if not words or tmp.stat().st_size == 0:
            tmp.unlink(missing_ok=True)
            sys.exit("[dara] Layanan TTS tidak mengirim audio/timing kata. Coba lagi beberapa saat lagi.")
        tmp.replace(folder / "vo.mp3")

    durasi = words[-1]["selesai"] + 0.3
    data = {"suara": args.voice, "kecepatan": args.rate, "uji": args.uji, "durasi": round(durasi, 2),
            "kata": words, "kalimat": align_sentences(narasi, words)}
    (folder / "words.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "captions.srt").write_text(captions(words), encoding="utf-8")

    print(f"[dara] durasi {durasi:.1f} detik, {len(words)} kata bertiming, {len(data['kalimat'])} kalimat")
    if durasi < 28 or durasi > 47:
        print(f"[dara] PERHATIAN: durasi di luar target 30–45 detik. Pertimbangkan minta Raka menulis ulang.")
    if args.uji:
        print("[dara] selesai (uji)")
        return
    set_status(args.slug)
    print(f"[dara] selesai: videos/{args.slug}/vo.mp3, words.json, captions.srt")


if __name__ == "__main__":
    main()

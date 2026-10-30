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
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("edge_tts")

ROOT = Path(__file__).resolve().parents[2]
VIDEOS = ROOT / "videos"
DEFAULT_VOICE = "id-ID-ArdiNeural"
DEFAULT_RATE = "+15%"
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


# Gaya bicara per bagian naskah (edge-tts tidak punya emosi, jadi "akting" dibuat dari tempo, nada, dan jeda).
PROSODI = {
    "hook":       {"tempo": 6,  "nada": 6,  "jeda_sebelum": 0.0},   # lebih cepat & tinggi: energi pembuka "Tau nggak, …"
    "konteks":    {"tempo": -3, "nada": 0,  "jeda_sebelum": 0.22},
    "cara_kerja": {"tempo": -5, "nada": -1, "jeda_sebelum": 0.12},  # lebih tenang supaya penjelasan jelas
    "wow":        {"tempo": 3,  "nada": 5,  "jeda_sebelum": 0.38},  # jeda tegang sebelum kejutan, lalu nada naik
    "bukti":      {"tempo": -2, "nada": 1,  "jeda_sebelum": 0.14},
    "dampak":     {"tempo": 0,  "nada": 2,  "jeda_sebelum": 0.16},
    "penutup":    {"tempo": -4, "nada": -2, "jeda_sebelum": 0.3},   # melambat & turun: terasa selesai, bukan terpotong
}


def prosodi_konfig() -> dict:
    try:
        import mesin_suara  # noqa: E402
        p = mesin_suara.konfig().get("edge", {}).get("prosodi")
        if isinstance(p, dict):
            return {**PROSODI, **{k: {**PROSODI.get(k, {}), **v} for k, v in p.items() if isinstance(v, dict)}}
    except Exception:
        pass
    return PROSODI


async def synth_prosodi(narasi: list[dict], voice: str, rate: str, out: Path) -> list[dict]:
    """Rekam per kalimat dengan tempo/nada sesuai bagian naskah, lalu sambung dengan jeda yang diatur.
    Timing kata tetap akurat: offset tiap kalimat = durasi audio sebelumnya + jeda."""
    import tempfile
    try:
        import edge_tts  # type: ignore
    except ImportError:
        sys.exit("[dara] Paket edge-tts belum terpasang. Jalankan: python -m pip install -r requirements.txt")
    pr = prosodi_konfig()
    dasar = int(re.match(r"([+-]\d+)%", rate).group(1)) if re.match(r"([+-]\d+)%", rate) else 15
    sem = asyncio.Semaphore(4)
    with tempfile.TemporaryDirectory(prefix="dara-") as td:
        tdp = Path(td)

        async def satu(i: int, n: dict):
            g = pr.get(str(n.get("bagian", "")), {})
            r = max(-30, min(60, dasar + int(g.get("tempo", 0))))
            nada = int(g.get("nada", 0))
            async with sem:
                for coba in range(3):
                    try:
                        comm = edge_tts.Communicate(n["kalimat"].strip(), voice, rate=f"{r:+d}%", pitch=f"{nada:+d}Hz", boundary="WordBoundary")
                        kata, f = [], tdp / f"{i:02d}.mp3"
                        with f.open("wb") as fh:
                            async for ch in comm.stream():
                                if ch["type"] == "audio":
                                    fh.write(ch["data"])
                                elif ch["type"] == "WordBoundary":
                                    a0 = ch["offset"] / TICKS
                                    kata.append({"kata": ch["text"], "mulai": a0, "selesai": a0 + ch["duration"] / TICKS})
                        if kata and f.stat().st_size > 0:
                            return f, kata
                    except Exception as err:  # gangguan jaringan sesaat
                        if coba == 2:
                            raise RuntimeError(f"kalimat {i + 1}: {err}") from err
                    await asyncio.sleep(1.5 * (coba + 1))
            raise RuntimeError(f"kalimat {i + 1}: tidak ada audio")

        hasil = await asyncio.gather(*(satu(i, n) for i, n in enumerate(narasi)))
        args, rantai, words, t = [], [], [], 0.0
        for i, ((f, kata), n) in enumerate(zip(hasil, narasi)):
            jeda = float(pr.get(str(n.get("bagian", "")), {}).get("jeda_sebelum", 0.12)) if i > 0 else 0.0
            dur = durasi_audio(f)
            t += jeda
            args += ["-i", str(f)]
            rantai.append(f"[{i}:a]aresample=24000,aformat=channel_layouts=mono,adelay={int(jeda * 1000)}|{int(jeda * 1000)},"
                          f"atrim=duration={jeda + dur:.3f}[a{i}]")
            for w in kata:
                words.append({"kata": w["kata"], "mulai": round(t + w["mulai"], 3), "selesai": round(t + w["selesai"], 3)})
            t += dur
        k = len(hasil)
        rantai.append("".join(f"[a{i}]" for i in range(k)) + f"concat=n={k}:v=0:a=1[o]")
        r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args, "-filter_complex", ";".join(rantai),
                            "-map", "[o]", "-c:a", "libmp3lame", "-b:a", "160k", str(out)], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"ffmpeg gagal menyambung suara: {r.stderr[-200:]}")
    return words


def durasi_audio(f: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(f)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


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


def transkrip(script: dict, data: dict) -> str:
    """Transkrip bertimestamp per kalimat: untuk Zona, Rara, dan deskripsi/caption."""
    L = [f"{script.get('judul', '')}", f"Durasi {data['durasi']:.1f} detik · suara {data['suara']} {data['kecepatan']}", ""]
    narasi = [n for n in script.get("narasi", []) if str(n.get("kalimat", "")).strip()]
    for k in data.get("kalimat", []):
        n = narasi[k["i"]] if k["i"] < len(narasi) else {}
        m, s = divmod(k["mulai"], 60)
        L.append(f"[{int(m):02d}:{s:05.2f}] ({n.get('bagian', '-')}) {k['kalimat']}")
    return "\n".join(L) + "\n"


def set_status(slug: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "agents" / "pabrik.py"), "set", slug, "suara", "--note", "dibuat Dara"], check=True, cwd=ROOT)


def main() -> None:
    ap = argparse.ArgumentParser(description="Dara: naskah → voice-over + timing + subtitle")
    ap.add_argument("slug")
    ap.add_argument("--voice", default=DEFAULT_VOICE, help="id-ID-ArdiNeural (pria) atau id-ID-GadisNeural (wanita)")
    ap.add_argument("--rate", default=DEFAULT_RATE, help="kecepatan, misalnya +10%%")
    ap.add_argument("--uji", action="store_true", help="tanpa internet: timing perkiraan, tanpa audio, status tidak diubah")
    ap.add_argument("--mesin", choices=["auto", "voxcpm", "edge"], default="",
                    help="auto (default, bible/gaya-suara.json): VoxCPM2 natural kalau terpasang + GPU, kalau tidak edge-tts")
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
        sys.path.insert(0, str(Path(__file__).parent))
        import mesin_suara  # noqa: E402
        mesin = args.mesin or str(mesin_suara.konfig().get("mesin", "auto"))
        words = None
        if mesin in ("auto", "voxcpm"):
            ok, ket = mesin_suara.siap()
            if ok:
                print(f"[dara] mesin suara natural VoxCPM2 ({ket})")
                try:
                    words = mesin_suara.buat([n["kalimat"].strip() for n in narasi], args.voice, args.rate, folder / "vo.mp3")
                    args.voice = f"voxcpm2-{'wanita' if 'gadis' in args.voice.lower() else 'pria'}"
                except RuntimeError as err:
                    if mesin == "voxcpm":
                        sys.exit(f"[dara] {err}")
                    print(f"[dara] {err} → cadangan edge-tts")
            elif mesin == "voxcpm":
                sys.exit(f"[dara] VoxCPM2 belum siap: {ket}")
            else:
                print(f"[dara] suara natural belum aktif ({ket}) → edge-tts")
    if not args.uji and words is None:
        tmp = folder / "vo.tmp.mp3"  # vo.mp3 lama tetap utuh kalau gagal di tengah jalan
        try:
            words = None
            if shutil.which("ffmpeg") and any(n.get("bagian") for n in narasi):
                try:
                    words = asyncio.run(synth_prosodi(narasi, args.voice, args.rate, tmp))
                    print("[dara] edge-tts berekspresi: tempo, nada & jeda mengikuti bagian naskah (hook, wow, penutup)")
                except RuntimeError as err:
                    print(f"[dara] mode ekspresif gagal ({str(err)[:120]}), memakai rekaman satu tarikan")
                    words = None
            if words is None:
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
    (folder / "transkrip.txt").write_text(transkrip(script, data), encoding="utf-8")

    target = float(script.get("target_durasi") or 40)
    lo, hi = max(25.0, target * 0.9), min(59.0, target * 1.12)
    data["target"] = {"detik": target, "min": round(lo, 1), "maks": round(hi, 1)}
    (folder / "words.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[dara] durasi {durasi:.1f} detik (target Raka {target:.0f}), {len(words)} kata bertiming, {len(data['kalimat'])} kalimat")
    if not lo <= durasi <= hi:
        print(f"[dara] PERHATIAN: durasi di luar target {lo:.0f}–{hi:.0f} detik. Atur kecepatan (--rate) atau minta Raka memangkas.")
    if args.uji:
        print("[dara] selesai (uji)")
        return
    set_status(args.slug)
    print(f"[dara] selesai: videos/{args.slug}/vo.mp3, words.json, captions.srt")


if __name__ == "__main__":
    main()

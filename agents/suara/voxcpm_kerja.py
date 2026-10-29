#!/usr/bin/env python3
"""Pekerja suara VoxCPM2 (dijalankan Dara lewat Python khusus suara di .venv-suara, BUKAN langsung).

    <python .venv-suara> agents/suara/voxcpm_kerja.py --tugas tugas.json

tugas.json: {"kalimat": [...], "keluar": "folder", "ref_wav": "...", "ref_teks": "...", "desain": "(...)",
             "cfg": 2.0, "langkah": 10, "seed": 42, "perangkat": "auto", "selaraskan": true}
Keluar: <keluar>/NN.wav per kalimat + <keluar>/hasil.json {"sr", "kalimat": [{"file", "durasi", "kata": [[kata, mulai, selesai], ...]}]}

VoxCPM2 (OpenBMB, Apache-2.0) mendukung bahasa Indonesia. Suara khas Yofamo dibuat SEKALI dari deskripsi
(voice design) lalu disimpan sebagai referensi, supaya semua video memakai suara yang sama.
Timing kata: faster-whisper (kalau terpasang) diselaraskan dengan kata naskah; kalau tidak, dibagi menurut panjang kata.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
from pathlib import Path


def tokens(text: str) -> list[str]:
    return re.findall(r"[\w'’-]+", text, flags=re.UNICODE)


def norm(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def bagi_rata(kata: list[str], dur: float, awal: float = 0.06, akhir_diam: float = 0.08) -> list[list]:
    """Perkiraan: waktu dibagi sebanding jumlah huruf (+ bobot jeda setelah koma)."""
    bobot = [max(2, len(norm(k))) + (3 if k.endswith(",") else 0) for k in kata]
    total = sum(bobot) or 1
    ruang = max(0.2, dur - awal - akhir_diam)
    t, out = awal, []
    for k, b in zip(kata, bobot):
        d = ruang * b / total
        out.append([k, round(t, 3), round(t + d * 0.92, 3)])
        t += d
    return out


def selaraskan(wav: str, kata_naskah: list[str], dur: float, asr) -> list[list]:
    if asr is None:
        return bagi_rata(kata_naskah, dur)
    try:
        segs, _ = asr.transcribe(wav, language="id", word_timestamps=True, beam_size=1, vad_filter=False)
        dengar = [(w.word.strip(), w.start, w.end) for s in segs for w in (s.words or [])]
    except Exception:
        return bagi_rata(kata_naskah, dur)
    if not dengar:
        return bagi_rata(kata_naskah, dur)
    a = [norm(k) for k in kata_naskah]
    b = [norm(w[0]) for w in dengar]
    waktu: list[tuple[float, float] | None] = [None] * len(a)
    for blok in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for j in range(blok.size):
            _, s, e = dengar[blok.b + j]
            waktu[blok.a + j] = (float(s), float(e))
    # kata yang tidak terdengar ASR: isi celah di antara kata yang cocok, dibagi menurut panjang kata
    out: list[list] = [[k, 0.0, 0.0] for k in kata_naskah]
    i = 0
    while i < len(a):
        if waktu[i] is not None:
            out[i] = [kata_naskah[i], round(waktu[i][0], 3), round(waktu[i][1], 3)]
            i += 1
            continue
        j = i
        while j < len(a) and waktu[j] is None:
            j += 1
        kiri = waktu[i - 1][1] if i > 0 and waktu[i - 1] is not None else 0.05
        kanan = waktu[j][0] if j < len(a) and waktu[j] is not None else max(kiri + 0.1, dur - 0.08)
        isi = bagi_rata(kata_naskah[i:j], kanan - kiri + 0.14, awal=0.0, akhir_diam=0.14)
        for n, (k, m, e) in enumerate(isi):
            out[i + n] = [k, round(kiri + m, 3), round(kiri + e, 3)]
        i = j
    # pastikan urut & tidak mundur
    for i in range(1, len(out)):
        if out[i][1] < out[i - 1][1]:
            out[i][1] = out[i - 1][1] + 0.02
        out[i][2] = max(out[i][2], out[i][1] + 0.05)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tugas", required=True)
    a = ap.parse_args()
    t = json.loads(Path(a.tugas).read_text(encoding="utf-8"))
    keluar = Path(t["keluar"])
    keluar.mkdir(parents=True, exist_ok=True)
    import numpy as np  # noqa: F401
    import soundfile as sf
    import torch
    from voxcpm import VoxCPM

    perangkat = t.get("perangkat", "auto")
    if perangkat == "auto":
        perangkat = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[voxcpm] memuat model di {perangkat} (pertama kali mengunduh ±5 GB)…", flush=True)
    model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False, optimize=False, device=perangkat)
    sr = model.tts_model.sample_rate
    seed = int(t.get("seed", 42))
    ref = Path(t["ref_wav"]) if t.get("ref_wav") else None
    if ref and not ref.exists():
        print("[voxcpm] membuat suara khas Yofamo dari deskripsi (sekali saja)…", flush=True)
        ref.parent.mkdir(parents=True, exist_ok=True)
        wav = model.generate(text=f"{t['desain']}{t['ref_teks']}", cfg_value=float(t.get("cfg", 2.0)),
                             inference_timesteps=int(t.get("langkah", 10)), seed=seed)
        sf.write(str(ref), wav, sr)
    asr = None
    if t.get("selaraskan", True):
        try:
            from faster_whisper import WhisperModel
            asr = WhisperModel(t.get("model_asr", "small"), device="cuda" if perangkat.startswith("cuda") else "cpu",
                               compute_type="float16" if perangkat.startswith("cuda") else "int8")
        except Exception as err:
            print(f"[voxcpm] faster-whisper tidak tersedia ({str(err)[:80]}), timing kata diperkirakan", flush=True)
    hasil = {"sr": sr, "mesin": "voxcpm2", "kalimat": []}
    for i, kal in enumerate(t["kalimat"]):
        kw = {"text": kal, "cfg_value": float(t.get("cfg", 2.0)), "inference_timesteps": int(t.get("langkah", 10)), "seed": seed + i}
        if ref and ref.exists():
            kw["reference_wav_path"] = str(ref)
        else:
            kw["text"] = f"{t.get('desain', '')}{kal}"
        wav = model.generate(**kw)
        f = keluar / f"{i:02d}.wav"
        sf.write(str(f), wav, sr)
        dur = len(wav) / sr
        kata = selaraskan(str(f), tokens(kal), dur, asr)
        hasil["kalimat"].append({"file": f.name, "durasi": round(dur, 3), "kata": kata})
        print(f"[voxcpm] kalimat {i + 1}/{len(t['kalimat'])}: {dur:.1f} dtk", flush=True)
    (keluar / "hasil.json").write_text(json.dumps(hasil, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except ImportError as err:
        sys.exit(f"[voxcpm] paket suara belum lengkap: {err}. Jalankan setup_suara.bat")

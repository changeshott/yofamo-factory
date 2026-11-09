#!/usr/bin/env python3
"""Bima (16:9) — footage & objek ASLI untuk video panjang gaya dokumenter.

    python agents/panjang/footage_panjang.py <slug>            # semua adegan yang butuh footage/objek
    python agents/panjang/footage_panjang.py <slug> --ulang 4  # cari ulang adegan tertentu
    python agents/panjang/footage_panjang.py <slug> --uji      # tanpa internet (klip & objek contoh)
    python agents/panjang/footage_panjang.py <slug> --cadangan # adegan yang tetap tanpa footage meminjam shot adegan terdekat

Untuk tiap adegan (durasi dari suara Gilang):
  • footage / pembuka / hp / tv → shot 16:9 dari YouTube CC BY, NASA, Wikimedia (PD/CC0/CC BY), Pexels, Pixabay —
    diurutkan menurut relevansi kata kunci adegan + topik; tiap shot DICEK TEKS (deteksi_teks): klip yang ada subtitle,
    tulisan, atau watermark di dalam videonya DITOLAK lalu dicari pengganti. Gelap/beku juga ditolak.
  • objek / cara_kerja (langkah.objek) / thumbnail.objek → foto asli benda (Pexels/Pixabay/Wikimedia) atau frame footage,
    latar dihapus (rembg, hanya objek utama) → media/NN-objekK.png. Objek: latar hitam-putih dari frame footage → media/NN-latar.jpg.
  • banding → dua foto asli (kiri/kanan) → media/NN-foto0.jpg, NN-foto1.jpg (ditampilkan hitam-putih).
Hasil: panjang/<slug>/footage/NN-k.mp4 + footage/manifest.json, media/, footage/KREDIT.txt, footage/kredit_deskripsi.txt.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import time
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agents"))
sys.path.insert(0, str(ROOT / "agents" / "aset"))
sys.path.insert(0, str(ROOT / "agents" / "thumbnail"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import tanpa_jendela  # noqa: E402,F401
import pakai_python  # noqa: E402

if __name__ == "__main__":
    pakai_python.pastikan("yt_dlp")
import cari_aset as bima  # noqa: E402  (search_all, raw_footage, relevansi, kata_kunci, http_download)
import deteksi_teks  # noqa: E402
import gerak  # noqa: E402
import status as st_panjang  # noqa: E402
import sumber  # noqa: E402

BUTUH_FOOTAGE = {"footage": None, "pembuka": 1, "hp": 1, "tv": 1}
DETIK_SHOT = 6.0          # video panjang: ganti shot tiap ±6 detik (dulu 4,5: terlalu banyak unduhan → tahap footage sampai 3 jam)
ANGGARAN_MENIT = 75       # batas waktu tahap footage; sisa adegan memakai shot cadangan, bukan gagal setelah 3 jam
PRODUK_CALON: list[dict] = []   # footage produk utama (hands on/review), dicari sekali per video dan dibagi ke semua adegan


def log(m: str) -> None:
    print(f"[bima-16:9] {m}", flush=True)


def rj(p: Path, d=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {} if d is None else d


def normalisasi(src: Path, out: Path, mulai: float, dur: float) -> None:
    """Potong & isi penuh 1920x1080 (crop tengah), 30 fps, tanpa audio. Klip pendek diperlambat sedikit / diulang."""
    ada = max(0.1, gerak.duration(src) - mulai)
    lambat = min(1.35, max(1.0, dur / ada))
    vf = f"setpts={lambat:.3f}*PTS,scale=1920:1080:force_original_aspect_ratio=increase:flags=lanczos,crop=1920:1080,setsar=1,fps=30"
    args = ["-ss", f"{max(0.0, mulai):.3f}", "-i", str(src)]
    if ada * lambat < dur:
        args = ["-stream_loop", "-1", *args]
    gerak.ff(*args, "-t", f"{dur:.3f}", "-vf", vf, "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", str(out))


def landscape_pexels(q: str, key: str) -> list[dict]:
    d = sumber.http_json("https://api.pexels.com/videos/search?" + urllib.parse.urlencode({"query": q, "orientation": "landscape", "per_page": 8}),
                         {"Authorization": key})
    out = []
    for v in d.get("videos", []):
        f = [x for x in v.get("video_files", []) if x.get("file_type") == "video/mp4" and (x.get("width") or 0) >= (x.get("height") or 1) and x.get("link")]
        if not f:
            continue
        f = min([x for x in f if (x.get("height") or 0) >= 1080] or f, key=lambda x: abs((x.get("height") or 0) - 1080))
        out.append(sumber.kandidat(sumber="pexels", id=v["id"], judul=re.sub(r"[-/]", " ", v.get("url", "").rstrip("/").rsplit("/", 1)[-1]),
                                   url_halaman=v.get("url", ""), pembuat=(v.get("user") or {}).get("name", ""), durasi=float(v.get("duration") or 0),
                                   lebar=f.get("width") or 0, tinggi=f.get("height") or 0, unduh=f["link"], lisensi="Pexels License"))
    return out


def kandidat(kueri: list[str], uji: bool) -> list[dict]:
    """Kandidat footage dari semua sumber untuk beberapa kata kunci; yang landscape didahulukan."""
    semua, lihat = [], set()
    for q in kueri:
        if not q:
            continue
        hasil = bima.search_all(q, True)
        pex = os.environ.get("PEXELS_API_KEY", "")
        if pex and not uji:
            try:
                hasil = [c for c in hasil if c["sumber"] != "pexels"] + landscape_pexels(q, pex)
            except Exception as err:  # noqa: BLE001
                log(f"pexels landscape gagal: {str(err)[:80]}")
        for c in hasil:
            k = (c["sumber"], c["id"])
            if k not in lihat:
                lihat.add(k)
                semua.append({**c, "kueri": q})
    return semua


def cari_footage(vdir: Path, i: int, a: dict, dur: float, topik: set[str], dipakai: dict, uji: bool) -> list[dict]:
    n = BUTUH_FOOTAGE.get(a.get("jenis"))
    n = n or max(1, min(4, math.ceil(dur / DETIK_SHOT)))
    per = round(dur / n + 0.6, 3) if a.get("jenis") == "footage" else round(dur + 0.6, 3)
    kk = [str(x) for x in (a.get("kata_kunci_visual") or [])][:3]
    kunci = bima.kata_kunci(kk)
    calon = kandidat(kk, uji)
    lihat = {(c["sumber"], c["id"]) for c in calon}
    calon += [c for c in PRODUK_CALON if (c["sumber"], c["id"]) not in lihat]
    calon.sort(key=lambda c: (-bima.relevansi(c, kunci, topik), (c.get("lebar") or 16) < (c.get("tinggi") or 9),
                              bima.URUT_SUMBER.get(c["sumber"], 9), len(dipakai.get(f"{c['sumber']}-{c['id']}", []))))
    hasil, ditolak = [], set()
    for s in range(n):
        out = vdir / "footage" / f"{i + 1:02}-{s}.mp4"
        for c in calon:
            key = f"{c['sumber']}-{c['id']}"
            segs = dipakai.setdefault(key, [])
            if key in ditolak or len(segs) >= 3 or (c.get("lebar") and c.get("tinggi") and c["lebar"] < c["tinggi"]):
                continue
            try:
                raw, mulai = bima.raw_footage(c, per, len(segs) if c["sumber"] != "youtube" else 0, segs)
                if c["sumber"] != "youtube":
                    segs.append((mulai, mulai + per))
                normalisasi(raw, out, mulai, per)
                gelap, beku = gerak.cek_shot(out)
                if gelap > 0.35 or beku > 0.75:
                    ditolak.add(key)
                    raise RuntimeError("gelap" if gelap > 0.35 else "diam/beku")
                if not uji:
                    alasan, _ = deteksi_teks.cek_video(out, halus=True)
                    if alasan:
                        ditolak.add(key)
                        raise RuntimeError(alasan)
                hasil.append({"file": out.name, "durasi": per, **{k: c.get(k) for k in ("sumber", "id", "judul", "url_halaman", "pembuat", "lisensi", "kueri")},
                              "sumber_mulai": round(mulai, 2), "relevansi": bima.relevansi(c, kunci, topik)})
                break
            except Exception as err:  # noqa: BLE001 — satu kandidat gagal → kandidat berikutnya
                log(f"  {i + 1:02}-{s} {c['sumber']} {str(c['id'])[:12]}: {str(err)[:90]} → berikutnya")
        else:
            log(f"  {i + 1:02}-{s}: tidak ada footage bersih yang cocok")
    return hasil


def objek_asli(kueri: str, tdir: Path, frame_cadangan: list[Path], uji: bool, nama: str):
    """Foto asli → latar dihapus (objek utama saja). Kembalikan (RGBA, info) terbaik atau (None, {})."""
    import thumbnail as mila
    cutter = None if uji else mila.pemotong("isnet-general-use")
    calon: list[tuple[str, Path, dict]] = []
    if uji:
        p = tdir / f"uji-{nama}.jpg"
        import gambar_ai
        gambar_ai.contoh_uji(p, kueri, len(nama), 1280, 1280, pink=True)
        calon.append((nama, p, {"sumber": "uji"}))
    else:
        calon += mila.cari_foto(kueri, tdir, maks=6)
        calon += [(f"frame-{f.stem}", f, {"sumber": "footage"}) for f in frame_cadangan]
    terbaik = (None, {}, 0.0)
    for lab, jpg, meta in calon:
        try:
            rgba = mila.potong_asli(jpg, cutter)
        except Exception as err:  # noqa: BLE001
            log(f"  potong {lab} gagal: {str(err)[:60]}")
            continue
        skor, ket = mila.skor_objek(rgba)
        if skor > terbaik[2]:
            kb = rgba.getchannel("A").point(lambda v: 255 if v > 20 else 0).getbbox()
            terbaik = (rgba.crop((max(0, kb[0] - 8), max(0, kb[1] - 8), min(rgba.width, kb[2] + 8), min(rgba.height, kb[3] + 8))), {**meta, "dari": lab, "skor": skor, "cek": ket}, skor)
    return (terbaik[0], terbaik[1]) if terbaik[2] > 0.3 else (None, {})


def frame(src: Path, out: Path, t: float = 0.5) -> Path | None:
    d = gerak.duration(src) or 1.0
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{d * t:.2f}", "-i", str(src), "-frames:v", "1", "-q:v", "2", str(out)], capture_output=True)
    return out if out.exists() else None


def main() -> None:
    ap = argparse.ArgumentParser(description="Bima 16:9: footage & objek asli video panjang")
    ap.add_argument("slug")
    ap.add_argument("--ulang", nargs="*", type=int, default=[])
    ap.add_argument("--uji", action="store_true")
    ap.add_argument("--cadangan", action="store_true", help="adegan tanpa footage meminjam shot adegan terdekat (pilihan terakhir autopilot)")
    a = ap.parse_args()
    bima.UJI = a.uji
    bima.load_env()
    vdir = st_panjang.folder(a.slug)
    st_panjang.jaga_belum_terbit(a.slug, "bima-16:9")
    naskah, waktu, ide = rj(vdir / "naskah.json"), rj(vdir / "suara" / "waktu.json"), rj(vdir / "ide.json")
    (vdir / "footage").mkdir(exist_ok=True)
    (vdir / "media").mkdir(exist_ok=True)
    tmp = vdir / "media" / "_foto"
    tmp.mkdir(exist_ok=True)
    man = rj(vdir / "footage" / "manifest.json")
    topik = bima.kata_kunci([ide.get("judul_kerja", ""), *(ide.get("objek_visual") or []), *(ide.get("kata_kunci_visual") or [])])
    produk = bima.atur_produk(ide)
    if produk and not a.uji:
        PRODUK_CALON.extend(kandidat([f"{produk} hands on", f"{produk} review"], a.uji))
        log(f"produk utama '{produk}': {len(PRODUK_CALON)} kandidat footage produk")
    mulai_t = time.monotonic()
    dipakai: dict = {}
    for daftar in man.values():
        for s in daftar:
            dipakai.setdefault(f"{s.get('sumber')}-{s.get('id')}", []).append((float(s.get("sumber_mulai") or 0), float(s.get("sumber_mulai") or 0) + float(s.get("durasi") or 4)))
    # adegan yang diganti (--ulang, mis. permintaan Wulan karena ada watermark): klip lamanya tidak boleh dipilih lagi
    for no in a.ulang:
        for s in man.get(str(no - 1)) or []:
            if not s.get("cadangan"):
                dipakai[f"{s.get('sumber')}-{s.get('id')}"] = [(0.0, 0.0)] * 3
    adegan = naskah.get("adegan") or []
    kurang = []
    # 1. footage
    for i, ad in enumerate(adegan):
        if ad.get("jenis") not in BUTUH_FOOTAGE:
            continue
        if str(i) in man and man[str(i)] and (i + 1) not in a.ulang:
            continue
        if time.monotonic() - mulai_t > ANGGARAN_MENIT * 60:
            log(f"adegan {i + 1:02}: anggaran waktu {ANGGARAN_MENIT} menit habis → pakai shot cadangan")
            a.cadangan = True
            continue
        dur = float((waktu.get(str(i)) or {}).get("durasi") or 5)
        log(f"adegan {i + 1:02} ({ad.get('jenis')}, {dur:.1f} dtk): {', '.join(ad.get('kata_kunci_visual') or [])}")
        man[str(i)] = cari_footage(vdir, i, ad, dur, topik, dipakai, a.uji)
        if not man[str(i)]:
            kurang.append(i + 1)
        (vdir / "footage" / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    if a.cadangan:
        kurang = [no for no in range(1, len(adegan) + 1) if adegan[no - 1].get("jenis") in BUTUH_FOOTAGE and not man.get(str(no - 1))]
        ada = [k for k, v in man.items() if v and not any(s.get("cadangan") for s in v)]
        for no in list(kurang):
            dekat = sorted(ada, key=lambda k: abs(int(k) - (no - 1)))
            pinjam = [{**s, "cadangan": True} for k in dekat[:2] for s in man[k][:1]]
            if pinjam:
                man[str(no - 1)] = pinjam
                kurang.remove(no)
                log(f"adegan {no:02}: meminjam {len(pinjam)} shot adegan terdekat (cadangan)")
        (vdir / "footage" / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    # frame cadangan (untuk objek & latar): tengah tiap shot footage
    frames = []
    for daftar in man.values():
        for s in daftar[:1]:
            f = frame(vdir / "footage" / s["file"], tmp / f"f-{Path(s['file']).stem}.jpg")
            if f:
                frames.append(f)
    # 2. objek asli & foto
    info_media = rj(vdir / "media" / "info.json")
    for i, ad in enumerate(adegan):
        j, no = ad.get("jenis"), f"{i + 1:02}"
        if (i + 1) not in a.ulang and any((vdir / "media").glob(f"{no}-*")):
            continue
        if j == "objek":
            rgba, info = objek_asli(str(ad.get("objek", "")), tmp, frames[:6], a.uji, f"{no}-0")
            if rgba is not None:
                rgba.save(vdir / "media" / f"{no}-objek0.png")
                info_media[f"{no}-objek0"] = info
            if frames:
                shutil.copy2(frames[i % len(frames)], vdir / "media" / f"{no}-latar.jpg")
        elif j == "cara_kerja":
            for k, l in enumerate(ad.get("langkah") or []):
                if isinstance(l, dict) and l.get("objek"):
                    rgba, info = objek_asli(str(l["objek"]), tmp, [], a.uji, f"{no}-{k}")
                    if rgba is not None:
                        rgba.save(vdir / "media" / f"{no}-objek{k}.png")
                        info_media[f"{no}-objek{k}"] = info
        elif j == "banding":
            for k, sisi in enumerate(("kiri", "kanan")):
                q = (ad.get(sisi) or {}).get("objek")
                if q and not a.uji:
                    import thumbnail as mila
                    foto = mila.cari_foto(str(q), tmp, maks=1)
                    if foto:
                        shutil.copy2(foto[0][1], vdir / "media" / f"{no}-foto{k}.jpg")
                        info_media[f"{no}-foto{k}"] = foto[0][2]
    th = (naskah.get("thumbnail") or {}).get("objek")
    if th and (not (vdir / "media" / "thumbnail-objek.png").exists() or a.ulang):
        rgba, info = objek_asli(str(th), tmp, frames[:6], a.uji, "thumbnail")
        if rgba is not None:
            rgba.save(vdir / "media" / "thumbnail-objek.png")
            info_media["thumbnail-objek"] = info
    (vdir / "media" / "info.json").write_text(json.dumps(info_media, ensure_ascii=False, indent=1), encoding="utf-8")
    # 3. kredit (link lengkap disimpan, deskripsi YouTube tanpa link)
    kredit, desk = [], []
    for daftar in man.values():
        for s in daftar:
            if s.get("cadangan"):
                continue
            if s.get("sumber") in ("youtube", "nasa", "wikimedia") or "CC" in str(s.get("lisensi")):
                kredit.append(f"{s.get('judul')} — {s.get('pembuat') or '-'} ({s.get('lisensi') or s.get('sumber')}) {s.get('url_halaman') or ''}")
                desk.append(f"\"{s.get('judul')}\" oleh {s.get('pembuat') or '-'} ({s.get('lisensi') or s.get('sumber')})")
    for k, v in info_media.items():
        if "CC BY" in str(v.get("lisensi", "")):
            kredit.append(f"Foto: {v.get('judul')} — {v.get('pembuat')} ({v.get('lisensi')}) {v.get('halaman') or ''}")
            desk.append(f"Foto \"{v.get('judul')}\" oleh {v.get('pembuat')} ({v.get('lisensi')})")
    (vdir / "footage" / "KREDIT.txt").write_text("\n".join(dict.fromkeys(kredit)) + "\n", encoding="utf-8")
    (vdir / "footage" / "kredit_deskripsi.txt").write_text("\n".join(dict.fromkeys(desk)) + "\n", encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)
    n_shot = sum(len(v) for v in man.values())
    if kurang:
        log(f"KURANG footage di adegan {kurang} — ubah kata_kunci_visual adegan itu lalu jalankan --ulang")
        sys.exit(2)
    if not a.uji:
        st_panjang.set_status(a.slug, "ilustrasi", f"{n_shot} shot footage, {len(info_media)} objek/foto")
    log(f"selesai: {n_shot} shot footage asli (tanpa teks), {len(info_media)} objek/foto → panjang/{a.slug}/footage, media/")


if __name__ == "__main__":
    main()

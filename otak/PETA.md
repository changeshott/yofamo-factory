# PETA — pabrik konten Yofamo dalam satu halaman

Channel YouTube **Yofamo Technology** (@yofamoo_technology) milik Zona: konten faceless berbahasa Indonesia tentang teknologi nyata.
Repo `github.com/changeshott/yofamo-factory`. Berjalan di **laptop Windows Zona** (`C:\Users\zonaf\Downloads\yofamo-factory`);
Claude memakai langganan Claude Zona lewat `claude -p` (bukan API berbayar). Semua alat harus gratis.

## Dua pabrik, satu tim upload

```
SHORTS (9:16, ±30–60 dtk)  — status di state.db lewat agents/pabrik.py
  Steve(data) → Nova(ide) → [Zona setuju] → Raka(naskah) → Dara(suara) → Bima(footage) → Mila(thumbnail)
  → Rara(QC pra) → Kai(rakit) → Rara(QC akhir) → draft → [Zona setuju / autopilot lolos skor] → export → Uli(upload private+jadwal)

VIDEO PANJANG "Ruang Animasi" (16:9, 5–12 menit, gaya dokumenter) — status di panjang/<slug>/status.json
  Bayu(ide) → Citra(naskah adegan) → Gilang(suara) → Laras(footage 16:9) → Tio(render adegan) → Wulan(rakit + QC teknis + QC visual)
  → draft → [Zona setuju / autopilot lolos skor] → export → Uli(upload private+jadwal, chapter, subtitle)
```

| Agent | Skill / script utama | Hasil | Detail |
|---|---|---|---|
| Steve | `/steve-analis`, `agents/steve/kumpul.py`, `agents/steve/analisa.py` | `insights/raw/*`, laporan mingguan | `otak/steve-data.md` |
| Nova | `/ide-riset`, `agents/ide/radar.py`, `agents/ide/cek_ide.py`, `agents/ide/cek_visual.py` | `videos/<slug>/idea.json` | `otak/alur-shorts.md` |
| Raka | `/penulis`, `agents/penulis/cek_naskah.py` | `script.json`, `naskah.md` | `otak/alur-shorts.md` |
| Dara | `agents/suara/buat_suara.py` (`/suara`) | `vo.mp3`, `words.json`, `captions.srt` | `otak/alur-shorts.md` |
| Bima | `/aset`, `agents/aset/cari_aset.py` | `aset/NN-a.mp4`, `aset/manifest.json` | `otak/alur-shorts.md` |
| Mila | `agents/thumbnail/thumbnail.py` (`/thumbnail`) | `export/thumbnail.jpg` | `otak/alur-shorts.md` |
| Kai | `agents/editor/rakit.py` + `agents/editor/komposisi.py` (`/editor`) | `export/final.mp4` | `otak/alur-shorts.md` |
| Rara | `/qc`, `agents/qc/periksa.py` | `export/qc*.json` | `otak/alur-shorts.md` |
| Bayu | `/panjang-ide` | `panjang/<slug>/ide.json` | `otak/alur-panjang.md` |
| Citra | `/panjang-naskah`, `agents/panjang/cek_naskah_panjang.py` | `naskah.json` | `otak/alur-panjang.md` |
| Gilang | `agents/panjang/suara_panjang.py` | `suara/NN.mp3`, `suara/waktu.json` | `otak/alur-panjang.md` |
| Laras | `agents/panjang/footage_panjang.py` | `footage/`, `media/` | `otak/alur-panjang.md` |
| Tio | `agents/panjang/dokumenter.py` | `adegan/NN.mp4` | `otak/alur-panjang.md` |
| Wulan | `agents/panjang/rakit_panjang.py`, `agents/panjang/periksa_panjang.py`, `/qc-panjang` | `export/final.mp4`, `qc*.json` | `otak/alur-panjang.md` |
| Uli | `agents/upload/unggah.py`, `agents/panjang/unggah_panjang.py`, `agents/upload/jadwal.py` | `export/upload.json` | `otak/autopilot-upload.md` |

## Penggerak

- **Produser Shorts** `agents/produser.py` — satu klik "Buat video" di Studio → seluruh alur Shorts (Claude dipanggil per langkah
  dengan `--max-turns` & `--allowedTools` terbatas; token tiap langkah dicatat ke `produksi/token-log.jsonl`).
- **Produser panjang** `agents/panjang/produser_panjang.py` — sama untuk video panjang (`--lanjut <slug>` melanjutkan).
- **Autopilot Shorts** `agents/autopilot.py` dan **autopilot panjang** `agents/panjang/autopilot_panjang.py` — isi slot tayang
  hari ini + besok, buat video yang kurang, upload otomatis yang lolos QC. Detail: `otak/autopilot-upload.md`.
- **Studio Yofamo** `studio/` (Next.js, http://127.0.0.1:3210, `start_studio.bat`) — kantor virtual: tombol Buat, setujui, jadwal,
  log, token. Detail: `otak/studio.md`.

## Di mana keadaan disimpan (semua di laptop, tidak di-commit)

| Apa | Tempat |
|---|---|
| Status Shorts | `state.db` (hanya lewat `agents/pabrik.py`) |
| Status video panjang | `panjang/<slug>/status.json` (lewat `agents/panjang/status.py`) |
| Kemajuan produksi | `produksi/<id>.json`, `produksi/panjang/<id>.json`, kunci `produksi/*.lock` |
| Autopilot | pengaturan `bible/autopilot.json` (versi laptop, JANGAN di-commit), status `produksi/autopilot.json`, `produksi/autopilot-panjang.json` |
| Upload | `videos/<slug>/export/upload.json`, `panjang/<slug>/export/upload.json` (`videoId`, `dibatalkan`, `manual_videoId`) |
| Token Claude | `produksi/token-log.jsonl` → `python agents/pemakaian.py` |
| Data channel | `insights/raw/` (Steve), ringkasan `insights/raw/analisa-*.md` |
| Rahasia | `.env` (API key), `rahasia/` (OAuth YouTube) — tidak pernah dibaca/ditampilkan |
| Log | `logs/` |

## Aturan paling penting (lengkap di `AGENTS.md` → Aturan kerja, keputusan di `otak/keputusan.md`)

- Upload hanya oleh Uli, hanya status `export`, selalu private (+ publishAt). Tidak ada agent yang mengubah/menghapus video di YouTube.
- Footage hanya berlisensi bebas (YouTube CC BY, NASA, Wikimedia PD/CC0/CC BY, Pexels, Pixabay, AI, milik Zona).
- Angka dari `insights/raw/`, tidak dikarang; < 5 video = "dugaan".
- Agent tidak menghapus file kecuali `agents/bersih.py` (file besar video yang sudah diupload).
- Tes: `python agents/tes_pabrik.py` (68 tes; 2 tes Kai/HyperFrames hanya lolos di laptop yang punya node_modules).

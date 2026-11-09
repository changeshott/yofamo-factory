# Alur video panjang "Ruang Animasi" (16:9, 5–12 menit, gaya dokumenter modern)

Penggerak: `agents/panjang/produser_panjang.py` (`--lanjut <slug>` melanjutkan, `--uji` tanpa internet/Claude). Satu video pada satu
waktu (`produksi/panjang.lock`, maks 12 jam), prioritas CPU rendah, kemajuan `produksi/panjang/<id>.json`. Terpisah total dari Shorts:
folder `panjang/<slug>/`, status `panjang/<slug>/status.json` lewat `agents/panjang/status.py`
(`ide → naskah → suara → ilustrasi → animasi → draft → export → terbit`; untuk dokumenter "ilustrasi" = footage selesai).
Gaya: `bible/panjang-bible.md` (aturan konten), `bible/gaya-dokumenter.json` (tampilan). Format naskah `"format": "dokumenter"`;
naskah tanpa `format` = jalur kartun lama (`agents/panjang/ilustrasi.py`, `agents/panjang/animasi.py`, host Yofa) — hanya untuk
melanjutkan video lama.

## Langkah (urutan nyata di kode)

| # | Agent | Cara jalan | Batas | Hasil |
|---|---|---|---|---|
| 1 | Bayu | `/panjang-ide [tema]` | 60 mnt, 50 turn | `ide.json` (fakta bersumber, bab, `produk`, kata kunci visual) |
| 2 | Citra | `/panjang-naskah <slug>` + `agents/panjang/cek_naskah_panjang.py` | 60 mnt, 60 turn | `naskah.json`, `naskah.md` |
| 3 | Gilang | `agents/panjang/suara_panjang.py` (edge-tts) | 40 mnt, 2 coba | `suara/NN.mp3`, `suara/waktu.json` (resume per adegan: `suara/waktu.parsial.json`) |
| 4 | Laras | `agents/panjang/footage_panjang.py` | 3 jam (anggaran internal 75 mnt) | `footage/*.mp4` + `footage/manifest.json`, `media/*.png`, kredit |
| 4b | Citra | footage kurang (kode keluar 2) → `/panjang-naskah <slug> --visual N,M` lalu Laras `--ulang` | 30 mnt | kata kunci visual baru |
| 4c | Laras | masih kurang → `--cadangan` (pinjam shot adegan terdekat) | 60 mnt | |
| 5 | Tio | `agents/panjang/dokumenter.py` (HyperFrames template `dokumenter.html` + ffmpeg) | 12 jam | `adegan/NN.mp4` (yang sudah jadi tidak dirender ulang) |
| 6 | Wulan | `rakit()` → `agents/panjang/rakit_panjang.py`, `agents/panjang/thumbnail_panjang.py`, `agents/panjang/periksa_panjang.py`, `/qc-panjang <slug>` | | `export/final.mp4`, `thumbnail.jpg`, `bab.txt`, `subtitle.srt`, `qc.json`, `qc_review.json` |

Hasil: status `draft` → Zona menyetujui (`export`) atau autopilot panjang menyetujui sendiri kalau lolos QC teknis + visual dengan
skor ≥ `panjang.skor_qc_min` → Uli `agents/panjang/unggah_panjang.py` (`otak/autopilot-upload.md`).
Script yang gagal tiba-tiba dicoba ulang (`jalan_ulang`, kode keluar dicatat di log).

## Rincian penting per tahap

- **Bayu** (`.claude/skills/panjang-ide/SKILL.md`): produk/teknologi yang bisa dilihat & dipakai, bukan antariksa/riset lab
  (`otak/keputusan.md`); sumber kandidat = Shorts kita yang menang + brief Steve → radar; ≤ 4 WebSearch, ≤ 6 WebFetch;
  `cek_visual.py "<NAMA PRODUK>" "<nama produk> hands on"` skor ≥ 6; baca `insights/panjang-retensi.md` kalau ada.
- **Citra** (`.claude/skills/panjang-naskah/SKILL.md`): jenis adegan footage, pembuka, kata, angka, cara_kerja, banding,
  garis_waktu, objek, hp, tv, judul_bab, penutup; footage ≥ 50%; ≥ 3 bab. `objek`, `thumbnail.objek` & kata kunci visual memakai
  nama produk spesifik + apa yang sedang dibahas kalimat itu. Adegan `kata` wajib punya `teks_layar`.
- **Laras** (`agents/panjang/footage_panjang.py`): `DETIK_SHOT` 6 dtk (maks 4 shot/adegan), `ANGGARAN_MENIT` 75 → sisa adegan
  otomatis `--cadangan`. Footage produk utama ("`<produk>` hands on/review", `PRODUK_CALON`) dicari sekali dan ditawarkan ke semua
  adegan; urutan kandidat pakai `relevansi()` Bima (`agents/aset/cari_aset.py`). Tiap shot: dinormalisasi 1920x1080, ditolak kalau
  gelap/beku (`agents/aset/gerak.py`) atau ada tulisan (`agents/aset/deteksi_teks.py`, mode `halus`: 4 frame, 1080p, berhenti begitu
  2 frame bertulisan). `--ulang N`: klip lama adegan itu tidak boleh dipilih lagi. Objek asli: foto + rembg (`agents/thumbnail/thumbnail.py`
  fungsi `cari_foto`, `potong_asli`, `skor_objek`).
- **Tio** (`agents/panjang/dokumenter.py`): `data_adegan()` mengisi template; adegan `kata` tanpa teks memakai 5 kata pertama narasi
  (perbaikan "layar putih kosong", 9 Nov 2026). Menunggu kalau produksi Shorts sedang jalan.
- **Penjaga**: `footage_panjang.py`, `dokumenter.py`, `rakit_panjang.py` menolak jalan kalau video sudah diupload
  (`st_panjang.jaga_belum_terbit`), dan `set_status` menolak status selain `export`/`terbit` untuk video yang sudah diupload
  (lewati keduanya dengan env `YOFAMO_PAKSA=1`). Upload di luar slot autopilot → `terbit` otomatis setelah jam tayang.
- **Wulan**: cek teknis berskor 0–10 + lembar frame bernomor (`export/qc/lembar-N.jpg`), lalu QC visual Claude (maks 4 adegan diganti,
  1 putaran). Skor gabungan dipakai autopilot (`skor_qc` di `agents/panjang/autopilot_panjang.py`).

## Kecepatan (keadaan 9 Nov 2026)

Bayu/Citra/Gilang masing-masing ±2–4 menit. Laras paling lama (dulu sampai 3 jam: banyak unduhan + OCR 5 frame × 2 lintasan per shot,
satu video GRX-810 gagal karena batas 3 jam). Sudah dipercepat (shot 6 dtk, OCR 4 frame + berhenti dini, anggaran 75 menit);
dampaknya belum diukur di produksi sungguhan → cek log `logs/` produksi berikutnya.

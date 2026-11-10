# Progres

Terakhir diperbarui: 2026-11-10 (upgrade kantor Studio; berikutnya: editan Shorts, lalu alur). Sejarah lengkap: `git log`.

## Sedang dikerjakan

- **Upgrade seluruh project (permintaan Zona 2026-11-10)**, urutan pilihan Zona: (1) kantor Studio — selesai tahap 1;
  (2) editan Shorts — selesai tahap 1 (lihat Selesai), menunggu penilaian Zona pada video sungguhan;
  (3) alur untuk menaikkan views — bagian 1 selesai (data retensi harian, judul/hook produk + frasa pencarian); sisanya di Tertunda no. 9.
  CATATAN: dua perbaikan template (percikan memancar, latar penutup pekat) belum dilihat hasil render-nya — render uji dihentikan
  atas permintaan Zona; cek di Short pertama buatan pabrik setelah 10 Nov.
- **Suara**: selesai — Zona memilih William (pria, Shorts + panjang) & Emma (wanita) setelah mendengar contoh; `contoh_suara.bat`
  berjalan setelah perbaikan pemilih Python. Tinggal dinilai di video pertama bersuara baru (tempo/durasi vs target naskah).

## Tertunda (urut prioritas)

1. **Ukur hasil perubahan 9 Nov** di produksi sungguhan: token /ide-riset (sebelumnya ±1,56 jt) & /aset (±709 rb, sekarang
   dilewati kalau script lengkap), lama tahap Laras (sebelumnya sampai 3 jam), `produk_terlihat` di `qc_review.json`, adegan `kata`
   tidak putih, pelafalan nama produk, judul video panjang memuat frasa `kata_cari.json`. Sumber: `python agents/pemakaian.py`, `logs/`.
   Check-in terjadwal 2026-11-12 09:00 WIB (scheduled task `trig_01UEpVQfNLAxw1AxAuW6zrVD`) untuk analisa token.
2. **Belum terverifikasi dari Windows** (sandbox tidak punya internet ke situs ini): feed radar baru, dan layanan saran pencarian
   `suggestqueries.google.com` untuk `agents/ide/kata_cari.py` (kalau gagal: `kata_cari.json` berisi catatan "data belum cukup").
   Feed radar: Lihat bagian "Feed gagal" di `insights/radar.md`
   setelah `python agents/ide/radar.py --segar` jalan di Windows; ganti URL feed yang gagal di `FEEDS` (`agents/ide/radar.py`).
3. **Penjaga balapan (race) Shorts & Studio**: Studio belum mengunci Setujui/Unggah selama produksi slug yang sama berjalan;
   `agents/bersih.py` belum melewati video yang produksinya aktif; status belum dijaga monoton. (Video panjang sudah dijaga:
   `jaga_belum_terbit`.)
4. Pastikan `analitik-*.json` hari ini benar-benar muncul setelah Studio dibuka (perbaikan 10 Nov); kalau `analitik.py` gagal,
   lihat `logs/data-*.txt` (login/izin YouTube).
9. Belum teruji di produksi sungguhan (kode baru 10 Nov sore): aturan anti-kartu-teks Bima/Rara, playlist (butuh izin
   `youtube.force-ssl`; cek `upload.json` → `playlist`), `insights/pascatayang.md` setelah `kumpul.py` jalan.
10. Kuota YouTube 10.000/hari: 4 upload/hari ≈ 6.400 unit → sisa pencarian footage sedikit; pertimbangkan project API kedua
    khusus pencarian (kunci terpisah di `.env`).
5. Bima Shorts: kueri kalimat (`p["kata"]`) belum otomatis ditambah nama produk (Raka diminta menulisnya di `kata_kunci_visual`;
   footage topik diawali "`<produk>` hands on").
7. Kuota YouTube Data API (10.000 unit/hari, 1 pencarian = 100) dipakai bersama Shorts, video panjang, Nova/Bayu & Steve — kalau
   footage masih sering kurang, pertimbangkan kuota per pemakai atau project API kedua.
8. Rara `--akhir` (Claude) masih selalu jalan; kandidat hemat token berikutnya (mis. hanya kalau cek otomatis menemukan masalah).
6. Pendapatan: target realistis terdekat = tier fan-funding (500 subs + 3.000 jam tonton video panjang); video panjang masih 9–17
   views → fokus naikkan views video panjang (topik produk yang dicari orang).

## Masalah terbuka

- Render Shorts pernah mati diam-diam saat menunggu (penyebab belum ketemu) → sekarang dicoba ulang + kode keluar dicatat.
- 2 tes Kai (HyperFrames) gagal di sandbox karena tidak ada `node_modules` — normal; di laptop harus lolos.

## Selesai (terbaru di atas, ringkas)

- 2026-11-11 Motion graphic Shorts: warna menurut suasana, sinkron kata, kartu angka otomatis, perbaikan desimal. Kantor: Ruang
  Meeting, Ruang Istirahat, Studio Suara, Taman + rapat tim. Skor ide: bonus arah Zona tetap, data terukur hanya ±3.

- 2026-11-10 sore **Perbaikan penting: Short BLUETTI jadi kartu teks semua (0% footage).** Sebab: cek tulisan mode ketat menolak 13/14
  klip review produk, Rara menolak sisanya ("produk tidak terlihat"), pengganti = kartu teks, produser tetap merakit. Perbaikan:
  aturan anti-kartu-teks Bima (lihat `otak/alur-shorts.md`), cek tulisan mode biasa, batas tolak Rara, penjaga footage < 50%.
  Video BLUETTI itu sendiri jangan disetujui (status draft).
- 2026-11-10 Alur views bagian 2: evaluasi pasca-tayang + bobot ide terukur (`pascatayang.py`), Short → video panjang
  ("versi lengkap"), playlist per kategori (`agents/upload/terkait.py`).

- 2026-11-10 Alur views (tahap 3, bagian 1): data retensi/komentar kembali terambil tiap hari (`kumpul.py --ringan` naik lengkap
  1x/hari — akar masalah "YouTube Analytics basi"); judul & hook Shorts memakai nama produk + frasa pencarian (`kata_cari.json`,
  peringatan di `cek_naskah.py`).

- 2026-11-10 Editan Shorts (tahap 2): kamera + grade + vignet, pembuka cincin/percikan, tanda produk, ajakan komentar, momen wow,
  progres bersegmen, efek suara otomatis; perbaikan percikan (memancar) & bayangan teks di penutup. Dirender sungguhan di sandbox
  (HyperFrames) dan diperiksa lewat lembar frame. Detail: `otak/alur-shorts.md` → Kai.
- 2026-11-10 Suara: `agents/suara/tts.py` (waktu kata untuk semua jenis suara), `agents/suara/contoh_suara.py` + `contoh_suara.bat`
  (contoh & pilihan jenis suara), `bible/suara-pilihan.json` lokal.

- 2026-11-10 Upgrade kantor Studio (tahap 1 dari "upgrade seluruh project": kantor → editan Shorts → alur): gerak halus (rAF,
  jalan 4 frame), karakter 1,5x + pose baru & emote, kegiatan santai (minum, HP, ngobrol, tidur malam), sorak/kaget saat
  selesai/gagal, serah terima dokumen antar meja, jalur produksi di lantai, gelembung dengan titik tahap + waktu, papan kecil
  "Tayang berikutnya" & "Minggu ini", awan/debu/uap, robot penyedot debu, barang pribadi di meja. Detail: `otak/studio.md`.

- 2026-11-09 Video panjang tidak jadi-jadi — akar masalah GRX-810 (3 jam habis untuk 2 adegan): file NASA > 300 MB diunduh ulang
  tiap shot, YouTube API 429 (kuota). Perbaikan: `http_download` menolak dari header Content-Length + penanda `.terlalu-besar`;
  Laras mencatat kandidat gagal (`GAGAL_GLOBAL`) & cek anggaran waktu di dalam adegan (`BATAS_WAKTU`); pencarian YouTube CC
  di-cache 7 hari (`youtube_cari`, `cache/yt-cari/`, dipakai juga `cek_visual.py`) + berhenti memanggil YouTube setelah 403/429
  (`YT_MATI`). GRX-810 dipindah ke `panjang/_arsip/` (bukan dihapus), catatan macet/jeda autopilot panjang dikosongkan.
- 2026-11-09 Kata pencarian YouTube untuk judul video panjang: `agents/ide/kata_cari.py` → `panjang/<slug>/kata_cari.json`
  (Bayu; produser menjalankannya sebagai cadangan), Citra memakai frasa teratas di judul, validator memberi peringatan.
- 2026-11-09 Kamus pelafalan: `agents/suara/lafal.py` + `bible/lafal.json` + naskah → `lafal`; Dara & Gilang, timing dipulihkan.
- 2026-11-09 QC produk terlihat: Rara & Wulan mengisi `produk_terlihat`; < 0,5 → tidak lolos, autopilot tidak mengupload
  (`skor_qc` + `produk_cukup` di autopilot panjang, `skor_qc` di autopilot Shorts).
- 2026-11-09 Bima Shorts script dulu: produser menjalankan `cari_aset.py semua`; `/aset` (Claude) hanya kalau tidak lengkap.

- 2026-11-09 Status video panjang dijaga: tidak bisa mundur setelah diupload (`set_status` di `agents/panjang/status.py`); video
  yang diupload di luar slot autopilot otomatis `terbit` setelah jam tayang (`tandai_tayang`). `20261106-komputer-sel-otak-cl1`
  (draft padahal tayang 8 Nov 19:30, akibat render ulang yang selesai 26 detik setelah upload) dirapikan → `terbit` atas izin Zona.
  `python agents/panjang/status.py set` keluar dengan kode 1 (tanpa pesan "→ status") kalau perubahan ditolak penjaga.
- 2026-11-09 Otak project: `otak/`, `agents/otak.py` (indeks otomatis, data laptop, pemeriksa akurasi), `AGENTS.md` diringkas.
- 2026-11-09 Arah konten produk nyata (radar, cek_ide, cek_visual, skill Nova/Bayu/Citra), relevansi footage dari judul + produk,
  Laras lebih cepat (shot 6 dtk, OCR 4 frame + berhenti dini, anggaran 75 mnt), adegan `kata` tidak putih, penjaga video panjang
  terupload, regex slug `catat_token` (tidak lagi cocok "--otomatis"), /ide-riset 28 turn.
- 2026-11 Token per video (`produksi/token-log.jsonl`, `agents/pemakaian.py`, Meja Zona).
- 2026-11 Upload Shorts yang disetujui saat produksi berjalan (cek tiap 3 menit).
- 2026-11 Upload dobel `dibatalkan`, `manual_videoId`.
- 2026-11 Video panjang dilanjutkan setelah laptop mati (`macet`, `coba_lanjut`, suara per adegan).
- 2026-11 QC visual Wulan, subtitle otomatis, Telegram, retensi per bab & adegan.
- 2026-11 Autopilot video panjang 1/hari + jam 12:00; hitungan upload minggu ini.
- 2026-11 Gaya dokumenter jadi alur video panjang; OCR ketat label kecil & watermark pojok.

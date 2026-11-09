# Progres

Terakhir diperbarui: 2026-11-09 sore (usulan 3,4,5,7 + perbaikan video panjang macet). Sejarah lengkap: `git log`.

## Sedang dikerjakan

- (kosong)

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
4. **YouTube Analytics basi**: `analitik-*.json` terbaru 2026-10-31 → cari kenapa `kumpul.py` tidak memperbarui (login/izin/error).
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

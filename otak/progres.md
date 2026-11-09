# Progres

Terakhir diperbarui: 2026-11-09 (commit "Otak project"). Sejarah lengkap: `git log`.

## Sedang dikerjakan

- (kosong)

## Tertunda (urut prioritas)

1. **Ukur hasil perubahan 9 Nov** di produksi sungguhan: token /ide-riset (sebelumnya ±1,56 jt), lama tahap Laras (sebelumnya
   sampai 3 jam), apakah footage memperlihatkan produk, apakah adegan `kata` masih putih. Sumber: `python agents/pemakaian.py`, `logs/`.
   Check-in terjadwal 2026-11-12 09:00 WIB (scheduled task `trig_01UEpVQfNLAxw1AxAuW6zrVD`) untuk analisa token.
2. **Feed radar baru belum terverifikasi** dari laptop (dari sandbox semua 403). Lihat bagian "Feed gagal" di `insights/radar.md`
   setelah `python agents/ide/radar.py --segar` jalan di Windows; ganti URL feed yang gagal di `FEEDS` (`agents/ide/radar.py`).
3. **Penjaga balapan (race) Shorts & Studio**: Studio belum mengunci Setujui/Unggah selama produksi slug yang sama berjalan;
   `agents/bersih.py` belum melewati video yang produksinya aktif; status belum dijaga monoton. (Video panjang sudah dijaga:
   `jaga_belum_terbit`.)
4. **YouTube Analytics basi**: `analitik-*.json` terbaru 2026-10-31 → cari kenapa `kumpul.py` tidak memperbarui (login/izin/error).
5. Bima Shorts: kueri kalimat (`p["kata"]`) belum otomatis ditambah nama produk (baru footage topik yang diawali "`<produk>` hands on").
6. Pendapatan: target realistis terdekat = tier fan-funding (500 subs + 3.000 jam tonton video panjang); video panjang masih 9–17
   views → fokus naikkan views video panjang (topik produk yang dicari orang).

## Masalah terbuka

- Video panjang `20261106-komputer-sel-otak-cl1` berstatus `draft` padahal sudah di YouTube (sisa balapan lama) → status perlu
  dirapikan (oleh Zona/atas izin Zona), lalu tambahkan cek konsistensi status vs `upload.json`.

- Render Shorts pernah mati diam-diam saat menunggu (penyebab belum ketemu) → sekarang dicoba ulang + kode keluar dicatat.
- 2 tes Kai (HyperFrames) gagal di sandbox karena tidak ada `node_modules` — normal; di laptop harus lolos.

## Selesai (terbaru di atas, ringkas)

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

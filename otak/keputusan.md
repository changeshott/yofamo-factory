# Keputusan Zona (wajib diikuti)

Ditulis dengan tanggal. Keputusan baru yang menggantikan yang lama: tandai yang lama "(diganti YYYY-MM-DD)", jangan dihapus diam-diam.
Aturan tetap (upload, lisensi, hapus, rahasia) ada di `AGENTS.md` → Aturan kerja.

## Konten & arah channel

- **2026-11-09 — Teknologi yang bisa dilihat, dipakai, dibeli; bukan NASA/antariksa/riset lab.** Kata Zona: jangan terlalu banyak
  membahas planet/NASA; footage harus memperlihatkan objek yang dibahas; yang masih riset "jelek". Diterapkan: radar sumber berita
  produk, `cek_ide.py` menolak status riset & antariksa > 1 per 7 hari, skor visual produk ≥ 6, field `produk` di ide.
- **2026-11-09 — Ide dari yang sedang ramai & retensinya tinggi, pakai analisa Steve yang sudah ada** (jangan riset ulang data channel;
  hemat token). Diterapkan di skill Nova & Bayu.
- **2026-11-09 — Motion graphic harus sesuai narasi; footage sesuai yang sedang dibicarakan suara.** Diterapkan: relevansi footage dari
  judul + nama produk, Citra memakai nama produk + bagian yang dibahas kalimat.
- **2026-11-04 — Video panjang gaya dokumenter modern** (referensi "Video 1" Zona): footage asli + motion graphic tenang, bukan kartun,
  bukan gaya kayu/kuning vintage. Kartun lama hanya untuk melanjutkan video lama.

- **2026-11-09 — Pilih usulan 3, 4, 5, 7**: kata pencarian untuk judul video panjang, kamus pelafalan, QC produk terlihat
  (aturan yang dibuat: `produk_terlihat` < 0,5 = tidak lolos/tidak diupload otomatis), script dulu–Claude belakangan (Bima Shorts).

- **2026-11-10 — Upgrade seluruh project**, urutan: kantor Studio dulu (karakter lebih hidup, tampilan lebih detail, info kerja
  real-time, gaya lebih bagus) → editan (Shorts dulu) → alur untuk menaikkan views.

- **2026-11-10 — Zona minta suara lebih natural untuk bahasa Indonesia + pilihan jenis suara.** Disediakan: contoh semua suara
  gratis untuk dipilih Zona (`contoh_suara.bat`). **Pilihan Zona: `en-AU-WilliamMultilingualNeural` (pria) dan
  `en-US-EmmaMultilingualNeural` (wanita)** — disimpan di `bible/suara-pilihan.json` laptop.

- **2026-11-10 — "Lanjutkan build semuanya"**: evaluasi 48 jam, ajakan versi lengkap, playlist per kategori (playlist publik dibuat
  otomatis; hanya menambah video baru), skor ide dari hasil nyata.

## Produksi & jadwal

- **2026-11-09 — Kosongkan video panjang yang terputus, buat baru & stabil**: GRX-810 dipindah ke `panjang/_arsip/` (bisa dikembalikan).
- **2026-11-02 — Autopilot Shorts 3 video/hari**, isi stok hari ini + besok, upload otomatis yang lolos skor (`skor_qc_min`).
- **2026-11-05 — Autopilot video panjang 1 video/hari, upload otomatis.** Jam tayang diatur Zona sendiri di Studio (`panjang.jam` di
  `bible/autopilot.json` laptop): Zona sempat meminta 12:00; per 2026-11-09 file laptop berisi 17:30. Nilai yang berlaku selalu dari
  `otak/data/status.md` → Autopilot, jangan ditulis tetap di sini.
- **2026-11-09 — Video yang disetujui harus langsung terjadwal**, tidak menunggu produksi lain selesai.
- **2026-11-06 — Laptop mati di tengah produksi → lanjutkan dari tahap terakhir, jangan ulang dari awal.**
- **2026-11-09 — Video yang Zona upload manual / upload dobel**: tandai `dibatalkan` / `manual_videoId` di `upload.json`, jangan dihitung
  ganda. Video di YouTube hanya dihapus Zona sendiri.
- **2026-11-05 — Usulan fitur: Zona "tambahkan semua kecuali 2"**; yang dibuat: QC visual video panjang, Telegram, subtitle otomatis,
  retensi per bab & adegan, hitungan upload minggu ini.

## Cara kerja dengan Claude

- Jawaban & laporan dalam bahasa Indonesia, ringkas, poin terpenting dulu.
- **Konfirmasi dulu sebelum build besar** kalau Zona bilang "jangan langsung buat" / "konfirmasi dulu".
- Semua alat harus gratis. Jangan install paket tanpa diminta.
- Hemat token adalah prioritas (Nov 2026): pakai otak (`otak/`) sebelum menjelajah kode; agent tidak meriset ulang hal yang sudah ada.
- 2026-11-09 — Belum membuat project baru (mis. jasa audit website/AuditPitch); fokus menyempurnakan pabrik Yofamo dulu.

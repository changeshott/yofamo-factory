# Autopilot, upload, jadwal, notifikasi, bersih-bersih

## Autopilot Shorts — `agents/autopilot.py`

- Perintah: `jalan` (satu putaran), `status`, `nyala`, `mati`. Menyala saat Studio dibuka (`jalan_saat_studio_dibuka`), juga bisa
  lewat Windows Task Scheduler (`pasang_autopilot.bat` → `autopilot.vbs`, latar tanpa jendela `latar.vbs`).
- Pengaturan `bible/autopilot.json` (nilai bawaan di `cfg()`): `aktif` (false), `video_per_hari` (3, maks 6), `setujui_otomatis`
  (true), `skor_qc_min` (7), `maks_produksi_per_hari` (8), `mulai_produksi_jam_sebelum` (48), `isi_hari` (2), `suara`
  (pria/wanita), `visual` (teliti/cepat), `arahan_tema`. **File ini di laptop punya isi lokal Zona — jangan pernah di-commit.**
- Putaran (`putaran()`): perbarui jam tayang (`agents/upload/jadwal.py` → `insights/jadwal.json`) → isi slot hari ini + besok
  (`isi_slot()`) dengan video `export`, lalu video buatan autopilot yang lolos Rara (skor ≥ `skor_qc_min`, `skor_qc()`) → Uli
  upload private + `publishAt` → slot kosong → `produksi()` membuat video baru dari slot terdekat. Video terhenti dilanjutkan dulu
  (`macet()`, `--lanjut`). Slot hari ini yang terlewat dipindah ke jam lain hari ini (`pengganti()`). Stok lengkap → `aktif: false`.
- **Upload saat produksi berjalan**: `produksi()` memakai Popen dan tiap 180 dtk memanggil `isi_slot(..., hanya_disetujui=True)`,
  jadi video yang baru disetujui Zona langsung dijadwalkan tanpa menunggu produksi selesai.
- Juga memulai autopilot panjang di latar setiap putaran (`mulai_latar`). Status `produksi/autopilot.json`, log
  `logs/autopilot-<tanggal>.txt`, kunci `produksi/autopilot.lock`.

## Autopilot video panjang — `agents/panjang/autopilot_panjang.py`

- Bawaan (`BAWAAN`, ditimpa `bible/autopilot.json` → `panjang`): aktif true, `video_per_hari` 1, `isi_hari` 2, `setujui_otomatis`
  true, `skor_qc_min` 7, `maks_produksi_per_hari` 2, `jam` "" (otomatis 15–21 menit :30, ≥ 90 mnt dari jam Shorts). Nilai yang
  berlaku di laptop: lihat `otak/data/status.md` → Autopilot (Zona mengubahnya lewat Studio).
- Jalan: Studio dibuka, tiap ±1 jam selama Studio terbuka, dan tiap putaran autopilot Shorts. Kunci `produksi/autopilot-panjang.lock`.
- Melanjutkan video terhenti SEBELUM membuat baru: `macet(state, hanya_manual)` → `(slug, manual)`; `coba_lanjut` maks 3x hanya kalau
  tidak maju satu tahap pun; lewat batas → menunggu Zona + Telegram. Video dari tombol Buat juga dilanjutkan (id `panjang-lanjut-…`).
- Persetujuan otomatis: `skor_qc` = gabungan cek teknis + QC visual Wulan; QC visual tertunda (kuota) diulang (`perlu_tinjau`, `tinjau`).
- Subtitle yang belum terpasang disusulkan (`susul_subtitle`). Status `produksi/autopilot-panjang.json`, log `logs/autopilot-panjang-<tanggal>.txt`.

## Upload (Uli)

- Shorts: `agents/upload/unggah.py` (`login`, `cek`, `pratinjau <slug>`, `unggah <slug>`). Video panjang:
  `agents/panjang/unggah_panjang.py` (`pratinjau|unggah|subtitle <slug> [--jadwal ...]`). Hanya status `export`, selalu private,
  boleh `publishAt`. Deskripsi tanpa link sumber; kredit singkat + hashtag dari `bible/gaya-upload.json`; label konten sintetis.
- OAuth di `rahasia/` (tidak dibaca agent). Izin subtitle `youtube.force-ssl` opsional (`SCOPE_SUBTITLE`, `bisa_subtitle()`, penanda
  `produksi/youtube-izin.json`; `OAUTHLIB_RELAX_TOKEN_SCOPE` supaya login tetap berhasil tanpa centang subtitle).
- `upload.json`: `videoId`, `url`, `jadwal`; `dibatalkan: true` = upload dobel yang dibatalkan Zona (tidak dihitung jadwal/Steve);
  `manual_videoId` = video yang Zona upload sendiri.
- Jadwal tayang terbaik: `agents/upload/jadwal.py` → `insights/jadwal.json` + `.md` (tanpa kuota API, tanpa Claude).

## Notifikasi — `agents/notif.py`

Bot Telegram gratis, opsional (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` di `.env`; `siapkan|tes|kirim`). Kabar: video terjadwal,
video menunggu Zona, autopilot berhenti (kuota/login/gagal). Kabar sama tidak diulang (`produksi/notif.json`).

## Bersih-bersih — `agents/bersih.py`

Hanya video yang SUDAH diupload (`videoId` ≠ "UJI"). Shorts: hapus isi `export/` kecuali `SIMPAN_EXPORT`, isi `aset/` kecuali
`SIMPAN_ASET`, `vo.mp3`. Panjang: `adegan/`, `hf/`, `export/final.mp4`, `suara/*.mp3`, `footage/*.mp4` (manifest & kredit tetap).
Plus cache lama & file sementara (`bible/penyimpanan.json`). `--coba` = lihat dulu.

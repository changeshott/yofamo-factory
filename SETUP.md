# Setup Yofamo Shorts Factory (Windows, tanpa biaya tambahan)

- **Otak:** Claude Code, login dengan akun Claude Pro (memakai kuota langganan).
- **Tangan:** script Python gratis di `agents/`.
- **Jam:** Windows Task Scheduler.
- **Kontrol:** Studio Yofamo, kantor virtual di browser (`studio/`, Next.js + Tailwind).

## 1. Prasyarat

- Python 3.11+ dari python.org (centang **Add python.exe to PATH**).
- Claude Code CLI:
  ```powershell
  irm https://claude.ai/install.ps1 | iex
  ```
- Login sekali dengan `claude` → pilih **Claude account with subscription**. Cek `/status`: Login method harus **Claude Pro account**.
- Paket Python untuk Dara (suara), cukup sekali dari folder project:
  ```powershell
  python -m pip install -r requirements.txt
  ```
- Jangan isi variabel `ANTHROPIC_API_KEY` di komputer ini (kalau ada, Claude Code memakai API berbayar).

- **ffmpeg** (untuk Bima membentuk klip) dan **Deno** (dibutuhkan yt-dlp untuk YouTube), sekali saja:
  ```powershell
  winget install Gyan.FFmpeg
  winget install DenoLand.Deno
  ```
  Tutup lalu buka lagi PowerShell sesudahnya.

### Mesin video HyperFrames (motion graphics Kai)

Butuh **Node.js 22 atau lebih baru** (`node --version`; kalau lebih lama: `winget install OpenJS.NodeJS.LTS`). Lalu sekali saja, dari folder project:

```powershell
npm install
npx hyperframes browser ensure
```

Perintah kedua mengunduh Chrome khusus render (±150 MB). Tanpa ini, Kai tetap jalan dengan mesin ffmpeg (tanpa grafis gerak).
Cek: `python agents\suara\cek_gpu.py` → baris **Video: HyperFrames SIAP**.

### Suara natural VoxCPM2 (opsional, butuh GPU NVIDIA)

Jalankan dulu `python agents\suara\cek_gpu.py`. Kalau GPU NVIDIA terdeteksi (disarankan VRAM ≥ 8 GB):

```powershell
winget install Python.Python.3.12
setup_suara.bat
```

Ini membuat Python terpisah `.venv-suara` (PyTorch CUDA + VoxCPM2 + faster-whisper, unduhan ±8 GB). Model VoxCPM2 (±5 GB) diunduh saat pertama membuat suara, lalu suara khas Yofamo dibuat sekali dari deskripsi di `bible/gaya-suara.json` dan dipakai di semua video. Tanpa GPU NVIDIA, Dara otomatis memakai edge-tts.

## 2. Folder project

Taruh di tempat tetap, misalnya `C:\Users\zonaf\Projects\yofamo-factory`, lalu:

```powershell
copy .env.example .env
notepad .env
```

Untuk Bima, key stok **opsional** (Bima sudah cukup dengan YouTube CC, NASA, Wikimedia Commons, gambar AI, dan grafis). Kalau mau menambah Pixabay, isi `PIXABAY_API_KEY`: login gratis di https://pixabay.com, buka https://pixabay.com/api/docs/, key-mu tampil di bagian **Parameters → key**. (`PEXELS_API_KEY` opsional; Pexels sedang menghentikan pendaftaran key baru.)

**Gambar AI gratis (Cloudflare Workers AI, ±170 gambar/hari):**
1. Daftar gratis di https://dash.cloudflare.com/sign-up.
2. Account ID: buka dashboard → menu **Workers AI** (atau halaman akun) → salin **Account ID** → `CLOUDFLARE_ACCOUNT_ID=` di `.env`.
3. Token: **My Profile → API Tokens → Create Token** → klik **View all templates** → pilih **Workers AI**. Kalau tidak ada: **Start from scratch** → Permissions: `Account` · `Workers AI` · `Edit` → Continue → Create → salin → `CLOUDFLARE_API_TOKEN=` di `.env`. Jangan pilih *Full account access*.
Kalau dilewati, Bima tetap jalan tanpa gambar AI (memakai footage dan grafis saja).

Isi `YOUTUBE_API_KEY` (Google Cloud Console → YouTube Data API v3 → Credentials → API key, dibatasi hanya untuk YouTube Data API v3). Jangan pernah membagikan isi `.env`.

## 3. Buka Studio Yofamo

Butuh **Node.js LTS** (20.9 atau lebih baru) dari nodejs.org. Cek dengan `node --version`.

Klik dua kali **`start_studio.bat`**. Pertama kali, file ini memasang paket (sekitar 1 menit), lalu browser default (misalnya Brave) terbuka di http://127.0.0.1:3210. Jendela hitamnya harus tetap terbuka selama Studio dipakai.

Cara manual dari terminal VS Code:

```powershell
cd studio
npm install      # sekali saja
npm run dev
```

Studio Yofamo adalah kantor virtual tim agent, memenuhi satu layar. Klik apa saja di kantor, atau pakai dok di bawah. Scroll untuk zoom, seret untuk menggeser, klik dua kali (atau tombol FIT) untuk kembali pas layar.

- **Steve, Nova, Raka** — klik orangnya atau mejanya untuk melihat status, memberi tugas, dan membaca log kerjanya. Saat bekerja, mereka duduk di meja dengan layar menyala dan balon status di atas kepala.
- **Ruang founder** (ruang kaca kanan, kamu duduk di belakang meja kayu) — inbox keputusan: ide yang menunggu persetujuan, naskah yang siap direkam, dan target upload mingguan. Angka merah menunjukkan jumlah yang menunggu.
- **Papan tulis** — antrean semua video, dari ide sampai terbit. Ada tombol Salin untuk judul, naskah, deskripsi, dan tag.
- **Layar TV** — analitik semua Shorts (grafik dan tabel).
- **Rak buku** — channel bible yang bisa diedit (versi lama tersimpan otomatis di `bible/.history`).
- **Log kantor** — riwayat semua aktivitas agent dan keputusanmu.
- **Meja kosong berkardus** — pos untuk agent berikutnya (Suara, Pencari aset, Editor CapCut, Upload).
- **Rak server** — lampunya berkedip cepat saat agent bekerja; klik untuk melihat atau menghentikan tugas.
- **Sistem** (dok) — cek Python, Claude Code, `.env`, dan data channel, lengkap dengan cara memperbaikinya.
- Saat tugas selesai, muncul pemberitahuan di layar (dan notifikasi Windows kalau Studio sedang tidak dibuka). Agent yang berhasil akan berjalan ke ruang founder untuk melapor.
- Tugas yang sedang berjalan bisa dihentikan dengan tombol **Hentikan** di kiri atas.
- **Dok bawah** (ringkas): **+ Buat video**, **Tim** (kartu 8 agent dengan status kerja), **Meja Zona**, **Video** (galeri, antrean, kelola), **Data** (analitik, laporan, bible, log), **Sistem**.
- **Ctrl+K**: palet perintah — ketik nama agent, panel, video, atau aksi (misalnya "ide", "data", "galeri") lalu Enter.
- Saat produksi berjalan, **strip tahap produksi** muncul di atas tengah; klik untuk membuka detailnya.

Suasana kantor mengikuti jam laptop: pagi, siang, sore, dan malam dengan lampu kota di jendela.

Halaman ini hanya bisa dibuka dari laptopmu sendiri dan hanya menjalankan tugas yang sudah terdaftar.

## 4. Jadwal otomatis tiap Senin 08.00 (opsional)

Supaya Steve tetap jalan walau halaman tidak dibuka:

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 08:00 /TN "Steve Yofamo" /TR "powershell -ExecutionPolicy Bypass -File C:\Users\zonaf\Projects\yofamo-factory\run_steve.ps1"
```

Lalu di Task Scheduler → "Steve Yofamo" → tab Settings → centang **Run task as soon as possible after a scheduled start is missed**. Hasilnya muncul di Studio saat kamu membukanya.

## Catatan

- Kalau kuota Pro sedang habis, tugas Steve berstatus **Gagal** di halaman. Jalankan ulang setelah kuota reset.
- `agents/steve/sample_videos.json` hanya data uji (tanggal dan likes dikarang). Jangan dipakai untuk laporan.
- Retensi dan swipe-away butuh YouTube Analytics API (login OAuth) — ditambahkan nanti.

## Tes seluruh pabrik

Setelah semua langkah di atas, jalankan dari folder project:

```powershell
python agents/tes_pabrik.py --online
```

Semua baris harus `OK`. Kalau ada `GAGAL`, kirim seluruh keluarannya ke Claude.

## Upload otomatis & data retensi (Uli + Steve v2)

Gratis, tapi perlu satu kali menyiapkan OAuth di Google Cloud (project yang sama dengan YouTube API key boleh):

1. https://console.cloud.google.com → pilih project → **APIs & Services → Library** → aktifkan **YouTube Data API v3** dan **YouTube Analytics API**.
2. **OAuth consent screen**: User type *External*, isi nama aplikasi (misalnya "Yofamo Studio") dan email-mu, lalu di **Test users** tambahkan email akun YouTube-mu.
3. **Credentials → Create credentials → OAuth client ID** → Application type **Desktop app** → Create → **Download JSON**.
4. Simpan file itu sebagai `rahasia\client_secret.json` di folder project (buat folder `rahasia` kalau belum ada). Jangan pernah dikirim ke siapa pun.
5. `python -m pip install -r requirements.txt`, buka Studio → meja **Uli** → **Hubungkan YouTube** → login di browser yang terbuka → izinkan.

Catatan: Uli mengunggah **private**, dengan jadwal tayang kalau diberi jam (`--jadwal`, atau otomatis lewat autopilot): YouTube menayangkannya sendiri tepat di jam itu. Kuota upload YouTube Data API: 100 upload per hari, jauh di atas 3 video/hari. Kalau suatu saat video terjadwal tetap terkunci private, buka video itu di YouTube Studio; YouTube akan menjelaskan alasannya (biasanya verifikasi project API).

## Autopilot: 3 video per hari, jadwal tayang otomatis

1. Pastikan Uli sudah terhubung ke YouTube (langkah di atas) dan ada lagu di `musik/`.
2. Buka Studio (`start_studio.bat`). Autopilot langsung bekerja saat Studio dibuka, lalu tiap jam selama Studio terbuka. Opsional: klik dua kali **`pasang_autopilot.bat`** supaya tetap bekerja tiap jam walau Studio ditutup.
3. Atur di Studio → meja **Uli** → **Autopilot**: video per hari (bawaan 3), setujui otomatis kalau skor Rara ≥ 7, jadwal tayang hari ini & besok, dan log.
4. Laptop harus menyala, login, dan tidak tidur (Settings → System → Power → Sleep: Never saat dicas). Kalau laptop mati, autopilot menyusul di jam berikutnya; slot yang sudah lewat dilewati.

Cara kerjanya tiap putaran: hitung jam tayang terbaik (`insights/jadwal.md`) → video siap diunggah private + dijadwalkan → slot hari ini + besok yang belum punya video → tim membuat video baru berurutan (hari pertama 6 video; maksimal 8 produksi per hari supaya kuota Claude aman) → setelah jam tayang lewat, video ditandai terbit. Video dengan skor Rara di bawah batas tidak diunggah; kamu tonton & setujui sendiri di Studio.

Melepas penjadwal: `pasang_autopilot.bat hapus`. Mematikan sementara: tombol **Matikan** di Studio.

## Ruang Animasi: video YouTube panjang (gaya dokumenter)

Kantor kedua di Studio (sebelah kanan kantor Shorts). Tidak perlu pemasangan baru: memakai HyperFrames (`npm install`, Node 22+),
edge-tts, yt-dlp, rembg, dan kunci sumber footage yang sama dengan Shorts. Video 5–12 menit: footage asli (dicek bebas tulisan/watermark)
+ motion graphic gaya "Video 1".

1. **Autopilot video panjang** (bawaan aktif): Studio → **Ruang Animasi** → **Autopilot video panjang**. 1 video per hari, jam tayang
   tetap (mis. 12:00) atau otomatis. Video yang lolos cek teknis **dan** QC visual Wulan (skor ≥ 7) diunggah private + jadwal tayang;
   yang tidak lolos menunggu kamu. Laptop perlu menyala ±3–4 jam per video (Shorts tetap didahulukan).
2. Manual: isi arahan tema (opsional) → **Buat** → tonton → **Setujui** → **Unggah**. Terputus? **Lanjutkan** (yang sudah jadi tidak diulang).
3. **Subtitle otomatis**: klik **Hubungkan ulang YouTube** sekali (Ruang Animasi atau meja Uli) dan izinkan *mengelola video YouTube* —
   Uli lalu memasang subtitle Bahasa Indonesia di tiap video panjang (video lama disusulkan otomatis, atau tombol **Pasang subtitle**).
   Tanpa izin ini upload tetap berjalan, hanya tanpa subtitle.
4. Retensi per bab: setiap Steve mengumpulkan data (butuh YouTube terhubung), `insights/panjang-retensi.md` diperbarui — dibaca Bayu & Citra.

## Notifikasi ke HP (Telegram, gratis, opsional)

1. Di Telegram cari **@BotFather** → kirim `/newbot` → beri nama (mis. *Yofamo Studio*) dan username berakhiran `bot` → salin **token**.
2. Buka `.env` di folder project, tambahkan baris: `TELEGRAM_BOT_TOKEN=token-tadi` (jangan dibagikan ke siapa pun).
3. Buka bot barumu di Telegram → kirim `/start`.
4. Studio → **Sistem** → baris *Notifikasi ke HP* → **Hubungkan Telegram** (mengisi `TELEGRAM_CHAT_ID` otomatis & mengirim pesan uji).

Kabar yang dikirim: Shorts/video panjang terjadwal tayang, video menunggu kamu (skor QC rendah), autopilot berhenti (kuota Claude habis,
login Claude kedaluwarsa, produksi gagal). Kabar yang sama tidak diulang dalam beberapa jam.

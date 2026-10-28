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

## 2. Folder project

Taruh di tempat tetap, misalnya `C:\Users\zonaf\Projects\yofamo-factory`, lalu:

```powershell
copy .env.example .env
notepad .env
```

Untuk Bima, isi `PIXABAY_API_KEY`: login gratis di https://pixabay.com, buka https://pixabay.com/api/docs/, key-mu tampil di bagian **Parameters → key**. (`PEXELS_API_KEY` opsional; Pexels sedang menghentikan pendaftaran key baru.)

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

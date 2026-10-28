# Setup Yofamo Shorts Factory (Windows, tanpa biaya tambahan)

- **Otak:** Claude Code, login dengan akun Claude Pro (memakai kuota langganan).
- **Tangan:** script Python gratis di `agents/`.
- **Jam:** Windows Task Scheduler.
- **Kontrol:** Yofamo Control Room, halaman lokal di browser (`dashboard/`).

## 1. Prasyarat

- Python 3.11+ dari python.org (centang **Add python.exe to PATH**).
- Claude Code CLI:
  ```powershell
  irm https://claude.ai/install.ps1 | iex
  ```
- Login sekali dengan `claude` → pilih **Claude account with subscription**. Cek `/status`: Login method harus **Claude Pro account**.
- Jangan isi variabel `ANTHROPIC_API_KEY` di komputer ini (kalau ada, Claude Code memakai API berbayar).

## 2. Folder project

Taruh di tempat tetap, misalnya `C:\Users\zonaf\Projects\yofamo-factory`, lalu:

```powershell
copy .env.example .env
notepad .env
```

Isi `YOUTUBE_API_KEY` (Google Cloud Console → YouTube Data API v3 → Credentials → API key, dibatasi hanya untuk YouTube Data API v3). Jangan pernah membagikan isi `.env`.

## 3. Buka Yofamo Control Room

Klik dua kali **`start_dashboard.bat`**, atau dari terminal:

```powershell
python dashboard\server.py
```

Browser terbuka di http://127.0.0.1:8765. Jendela hitam server harus tetap terbuka selama halaman dipakai.

Di halaman itu:

- **Ambil data terbaru** — mengambil statistik semua video (tanpa AI, tanpa kuota Claude).
- **Jalankan Steve** — Steve menganalisis dan menulis laporan mingguan (memakai kuota Claude Pro, model Sonnet).
- **Performa semua Shorts** — grafik views tiap Short dengan garis median; klik batang untuk membuka videonya.
- **Pabrik agent** — tujuh pos pipeline; pos menyala kalau skill-nya sudah dibuat.
- **Laporan Steve** dan **Tugas** — baca laporan per minggu dan log setiap tugas.
- **Semua video** — tabel yang bisa diurutkan dan disaring.
- **Channel bible** — edit aturan channel; versi lama tersimpan otomatis di `bible/.history`.

Halaman ini hanya bisa dibuka dari laptopmu sendiri dan hanya menjalankan tugas yang sudah terdaftar.

## 4. Jadwal otomatis tiap Senin 08.00 (opsional)

Supaya Steve tetap jalan walau halaman tidak dibuka:

```powershell
schtasks /Create /SC WEEKLY /D MON /ST 08:00 /TN "Steve Yofamo" /TR "powershell -ExecutionPolicy Bypass -File C:\Users\zonaf\Projects\yofamo-factory\run_steve.ps1"
```

Lalu di Task Scheduler → "Steve Yofamo" → tab Settings → centang **Run task as soon as possible after a scheduled start is missed**. Hasilnya muncul di Control Room saat kamu membukanya.

## Catatan

- Kalau kuota Pro sedang habis, tugas Steve berstatus **Gagal** di halaman. Jalankan ulang setelah kuota reset.
- `agents/steve/sample_videos.json` hanya data uji (tanggal dan likes dikarang). Jangan dipakai untuk laporan.
- Retensi dan swipe-away butuh YouTube Analytics API (login OAuth) — ditambahkan nanti.

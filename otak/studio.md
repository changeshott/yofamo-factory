# Studio Yofamo (`studio/`)

Kantor virtual lokal: Next.js + TypeScript + Tailwind, hanya menerima permintaan dari `127.0.0.1:3210`/`localhost:3210`
(`studio/lib/server/guard.ts`). Buka: `start_studio.bat` atau `cd studio && npm run dev`. **Next.js versi baru dengan perubahan besar —
baca `studio/AGENTS.md` sebelum menulis kode Studio.** Aturan: jangan mengubah `studio/` kecuali diminta Zona. Cek tipe: `npx tsc --noEmit`
di folder `studio/`.

## Susunan

- `studio/app/page.tsx` → `studio/components/Studio.tsx` (kerangka: sidebar tim kiri, jadwal tayang kanan `studio/components/jadwal.tsx`,
  dok bawah, palet perintah Ctrl+K). Kantor bergambar: `studio/components/office/` (`Office.tsx`, `engine.ts`, `sprites.ts`, `world.ts`).
- **Kantor (upgrade 2026-11-10)** — kanvas isometrik pixel-art 864×560 (`BW`×`BH` di `world.ts`):
  - `Office.tsx`: kamera (zoom/geser/terbang ke objek), loop `requestAnimationFrame` — logika `eng.step()` 10x/detik, gerak `eng.advance(dt)`
    + `eng.render()` maks ±30 fps dan turun otomatis ke 20/12 fps kalau menggambar > 8/14 ms (laptop sedang merender video);
    overlay DOM: `tag` (nama), `bubble` (kerja + titik tahap `pips` + waktu berjalan `sub`), `sign` (papan kecil), `badge`.
  - `engine.ts`: `jobFor()` (siapa bekerja; `Kerja.sejak`/`pips` dari `produksi[0].tahap`), `step()` (mode aktor: idle/work/report/antar/
    ngobrol/sorak/gagal; kegiatan santai per tempat `DI_TEMPAT`; malam → tidur di meja), `serahTerima()` (tahap berganti → agent
    mengantar dokumen ke meja agent berikutnya; urutan `ALUR_SHORTS`/`ALUR_PANJANG`), `advance()` (jalan halus, robot, partikel),
    `jalurProduksi()` (garis menyala meja→meja), `awan()`, `partikel()`, `robotDebu()`, `barangMeja()`. Latar (dinding/lantai) di-cache
    per fase hari (`latar`, `latarKunci`). Karakter digambar `SKALA` 1,5x.
  - `sprites.ts`: peta karakter 12×19, pose `stand|walk(4 frame)|sit|sleep|cheer|drink|carry|phone|talk|shock`, `Look.headphone`,
    emote 7×7 (`emote()`: zzz, note, bulb, kopi, cek, seru, titik, bintang, kertas, hati).
  - Cara uji visual (sandbox): `npm ci` di `studio/`, `npx next dev`, Playwright dengan `page.route('**/api/state')` untuk memalsukan
    produksi berjalan/berganti tahap, lalu screenshot.
- Panel di `studio/components/panels.tsx`: `AgentPanel`, `VideoCard` (setujui/upload), `QueuePanel`, `FounderPanel` (Meja Zona +
  `PemakaianToken`), `AnalyticsPanel`, `ReportsPanel`, `BiblePanel`, `ActivityPanel`, `HealthPanel` (Sistem: Python, Claude, YouTube,
  Telegram), `ProduksiPanel`, `GaleriPanel`, `KelolaPanel` (hapus — hanya Zona), `MusikPanel`, `AutopilotPanel`, `AutopilotPanjang`
  (pilihan jam termasuk 12:00), `RuangAnimasiPanel`.
- Server (`studio/lib/server/`): `project.ts` (path, daftar video lewat `agents/pabrik.py`, `MANUAL_MOVES`, data Steve, produksi),
  `jobs.ts` (menjalankan tugas agent: `claude -p` dengan `TOOLS` per agent atau script Python; satu tugas pada satu waktu; antrean
  `produksi/antrean.json`), `autopilot.ts`, `jadwal.ts` (slot tayang, `mingguIni` = upload minggu ini Shorts + panjang, tayang + terjadwal,
  mengabaikan `dibatalkan`), `panjang.ts` (video panjang, `izinSubtitle`, `pasangSubtitle`).
- Rute API `studio/app/api/<nama>/route.ts`: antrean, autopilot, bible, hapus, kelola, log, media, musik, panjang, pemakaian, report,
  run, state, stop, video.

## Tugas yang bisa dijalankan dari Studio

- Shorts & agent: `startJob()` di `studio/lib/server/jobs.ts` (tugas `produksi` → `agents/produser.py`, ditolak kalau
  `produser.lock` aktif; batas 180 menit; tugas lain 30 menit; juga `pasang_rembg`, `notif_siapkan`, `notif_tes`). Daftar nama tugas =
  tipe `JobName` di `studio/lib/types.ts`.
- Video panjang: `studio/lib/server/panjang.ts` menjalankan `agents/panjang/produser_panjang.py` (tema atau `--lanjut`, plus `--id`).
- Autopilot panjang di latar: `studio/lib/server/autopilot.ts` → `agents/panjang/autopilot_panjang.py jalan`.

## Yang belum ada (lihat `otak/progres.md`)

Tombol Setujui/Unggah belum dikunci saat produksi video yang sama sedang berjalan.

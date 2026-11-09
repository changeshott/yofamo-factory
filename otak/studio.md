# Studio Yofamo (`studio/`)

Kantor virtual lokal: Next.js + TypeScript + Tailwind, hanya menerima permintaan dari `127.0.0.1:3210`/`localhost:3210`
(`studio/lib/server/guard.ts`). Buka: `start_studio.bat` atau `cd studio && npm run dev`. **Next.js versi baru dengan perubahan besar —
baca `studio/AGENTS.md` sebelum menulis kode Studio.** Aturan: jangan mengubah `studio/` kecuali diminta Zona. Cek tipe: `npx tsc --noEmit`
di folder `studio/`.

## Susunan

- `studio/app/page.tsx` → `studio/components/Studio.tsx` (kerangka: sidebar tim kiri, jadwal tayang kanan `studio/components/jadwal.tsx`,
  dok bawah, palet perintah Ctrl+K). Kantor bergambar: `studio/components/office/` (`Office.tsx`, `engine.ts`, `sprites.ts`, `world.ts`).
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

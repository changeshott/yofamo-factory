# Steve & data (tanpa kuota Claude kecuali laporan)

## Pengumpul data — `agents/steve/kumpul.py`

| Mode | Isi |
|---|---|
| `kumpul.py` | statistik publik (`agents/steve/fetch_stats.py`) + komentar (`agents/steve/komentar.py`) + YouTube Analytics kalau YouTube dihubungkan (`agents/steve/analitik.py`, butuh token di `rahasia/`) + retensi video panjang (`agents/steve/retensi_panjang.py`, kalau ada upload panjang) + radar pasar (`agents/steve/pasar.py`, kalau > 6 hari) + analisa (`agents/steve/analisa.py`) |
| `--pasar` | paksa radar pasar |
| `--ringan` | statistik + analisa saja (dipakai Studio otomatis); **sekali sehari otomatis naik jadi lengkap** kalau `analitik-*.json` terbaru bukan hari ini dan YouTube terhubung (dulu mode ini tidak pernah mengambil retensi → data berhenti di 31 Okt 2026) |

Setelah selesai memanggil `python agents/otak.py perbarui --data` → `otak/data/status.md`.

## File hasil (`insights/raw/`, jangan diedit tangan)

- `YYYY-MM-DD.json` — snapshot semua video + perubahan views (Data API v3, hanya baca).
- `analitik-*.json` — retensi, kurva retensi (`retensi`), traffic, audiens; mencakup video panjang yang diupload pabrik.
- `komentar-*.json`, `pasar-*.json` (Shorts teknologi Indonesia yang ramai 30 hari), `retensi-panjang-*.json`.
- `analisa-*.json` + **`analisa-*.md` (brief — yang dibaca Nova/Bayu/Steve, bukan JSON mentah)**: KPI, kategori menang, retensi,
  momentum, peluang pasar, `data_kurang`.
- Turunan untuk tim: `insights/pelajaran.md` (aturan terbukti/dugaan), `insights/topik_backlog.json` (Steve → Nova),
  `insights/eksperimen.md`, `insights/panjang-retensi.md` (Bayu & Citra), laporan mingguan `insights/YYYY-Www.md`.

## Evaluasi pasca-tayang — `agents/steve/pascatayang.py` (dijalankan `kumpul.py`, tanpa token)

Video pabrik ≥ 48 jam tayang: views × median, % ditonton, hook 10% (dari `analitik-*.json`), digabung ciri produksi (kategori,
status, suara, porsi footage, `produk_terlihat`). Hasil: `insights/pascatayang.md` (dibaca Nova & Raka; ≥ 5 video = pola, selain itu
dugaan), `insights/raw/pascatayang-*.json`, dan `insights/bobot-ide.json` (pengali terukur per status/kategori, hanya n ≥ 5) →
`agents/ide/cek_ide.py` → `sinyal()` memakai pengali status terukur menggantikan bonus tetap (riset tetap ditolak).

## Skill `/steve-analis`

Laporan mingguan dari data di atas (`.claude/skills/steve-analis/SKILL.md`): kesehatan channel, apa yang menang, retensi, keputusan
minggu ini; < 5 video = "dugaan". Steve tidak membuat video dan tidak mengubah YouTube.

## Retensi video panjang — `agents/steve/retensi_panjang.py`

Kurva retensi dipetakan ke bab (`export/info.json` → `bab`) & adegan (`mulai_adegan`, cadangan `suara/waktu.json`). Metrik utama
`pergi_per_menit` = penonton yang tersisa pergi per menit (adil untuk adegan awal & akhir). Video id: `manual_videoId`, kalau tidak
`videoId` yang tidak `dibatalkan`.

## Token Claude — `agents/pemakaian.py`

`agents/produser.py` → `jalan_claude()` membaca stream-json, `catat_token()` menulis per langkah ke `produksi/token-log.jsonl`
(id produksi dari env `YOFAMO_PRODUKSI_ID`/`YOFAMO_PRODUKSI_JENIS`). `pemakaian.py [--json]`: rata-rata per video, per langkah, video
terbaru (Studio → Meja Zona, komponen `PemakaianToken`, rute `studio/app/api/pemakaian/route.ts`). Kolom: baru (input + tulis cache),
cache (baca cache, murah), output.

## Angka acuan (diam, dengan tanggal — angka terkini selalu dari `otak/data/status.md` / file sumber)

- 9 Nov 2026 (brief analisa 2026-11-09): 1.400 subscriber; median 10 Shorts terbaru 1.284 vs 1.537 sebelumnya; topik antariksa 11 dari 25
  terbaru, median 1.221 vs 1.530 topik lain; retensi terbaik: baju VR game 85%, print jantung 3D 84%, baju ganti motif 78%;
  traffic Shorts 95,7%; video panjang 9–17 views.
- 9 Nov 2026 (`pemakaian.py`): Shorts rata-rata 2,72 jt token/video (baru 271 rb, cache 2,43 jt, output 18 rb); per langkah
  /ide-riset 1,56 jt, /aset 709 rb, /qc 406 rb, /thumbnail 380 rb, /penulis 291 rb.
- Analitik terbaru yang tercatat saat itu `analitik-2026-10-31` (YouTube Analytics tidak diperbarui sejak itu → lihat progres).

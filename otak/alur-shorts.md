# Alur Shorts (9:16) — dari ide sampai draft

Penggerak: `agents/produser.py` (tombol "+ Buat video" Studio, antrean `produksi/antrean.json`, satu produksi pada satu waktu
`produksi/produser.lock`, kemajuan `produksi/<id>.json`). Claude dipanggil lewat fungsi `claude()` → `claude -p --model sonnet
--max-turns N --output-format stream-json --verbose --allowedTools ...`; tiap panggilan dicatat `catat_token()` ke
`produksi/token-log.jsonl`. Kuota/login/internet habis → produksi berhenti dengan pesan jelas (`KuotaClaude`, `LoginClaude`, `Offline`).
Status video: `ide → disetujui → naskah → suara → aset → draft → export → terbit` (atau `ditolak`), hanya lewat `agents/pabrik.py`.
Folder satu video: `videos/<slug>/`.

## Langkah di produser (urutan nyata di kode)

| # | Agent | Cara jalan | Batas | Catatan |
|---|---|---|---|---|
| 0 | Steve | `agents/steve/fetch_stats.py` | 5 mnt | daftar video channel terbaru (cek duplikat topik) |
| 1 | Nova | `agents/ide/radar.py` lalu `/ide-riset --otomatis` | 45 mnt, 28 turn | langkah paling boros token (±1,6 jt/video, data 9 Nov 2026) |
| 2 | Raka | `/penulis <slug>` | 30 mnt | durasi meleset → `/penulis <slug> --pangkas` atau suara dipercepat |
| 3 | Dara | `agents/suara/buat_suara.py` (tanpa Claude) | 10 mnt | VoxCPM2 (GPU) atau edge-tts; kamus pelafalan `agents/suara/lafal.py` |
| 4 | Bima | `cari_aset.py semua` (script dulu); `/aset <slug>` hanya kalau belum lengkap | 40 + 50 mnt | kata kunci dari Raka; penilaian visual oleh Rara pra |
| 5 | Mila | `agents/thumbnail/thumbnail.py`; kalau gagal `/thumbnail` | 15 mnt, 20 turn | objek asli (rembg) di belakang hook |
| 5b | Rara pra | `agents/qc/periksa.py pra` + `/qc <slug> --pra` | 30 mnt, 30 turn | shot jelek diganti sebelum dirakit |
| 6 | Kai | `agents/editor/rakit.py` (HyperFrames, cadangan ffmpeg) | 45 mnt | gaya gerak dipilih yang paling jarang dipakai |
| 7 | Rara akhir | `periksa.py otomatis` + `/qc <slug> --akhir` | 45 mnt, 30 turn | maks 1 putaran perbaikan, skor → `export/qc_review.json` |

Hasil: status `draft`. Zona menyetujui di Studio → `export`; atau autopilot menyetujui sendiri kalau skor ≥ `skor_qc_min`
(`otak/autopilot-upload.md`).

## Aturan per agent (ringkas — rincian di SKILL.md masing-masing)

- **Nova** (`.claude/skills/ide-riset/SKILL.md`): arah konten Nov 2026 = produk/teknologi yang bisa dilihat & dibeli (lihat
  `otak/keputusan.md`). Briefing hanya `insights/pelajaran.md` + brief `insights/raw/analisa-*.md` terbaru. Radar
  (`agents/ide/radar.py`) dari RSS media produk; skor naik untuk produk nyata (`PRODUK`), turun untuk riset (`RISET`) & antariksa.
  Anggaran mode otomatis: ≤ 3 WebSearch, ≤ 4 WebFetch. `idea.json` wajib punya `produk` (nama spesifik, Inggris).
  Validasi `agents/ide/cek_ide.py --tulis`: GAGAL kalau status `riset`, antariksa > 1 dalam 7 hari (dilihat dari `videos/*/idea.json`),
  visual belum dicek, atau skor visual < 6. Bonus status: dijual +6, dipakai +4, prototipe −4, riset −10; antariksa −8.
  `agents/ide/cek_visual.py "<NAMA PRODUK>" ...`: hanya hasil yang judulnya memuat token inti kata kunci PERTAMA yang dihitung;
  bobot sumber youtube 2.0, wikimedia/pexels 0.6, pixabay 0.5, nasa 0.3. `agents/ide/cek_topik.py`: cek belum pernah dibahas.
- **Raka** (`.claude/skills/penulis/SKILL.md`): pembuka khas "Tau nggak, …", lembar produksi per kalimat (jenis visual, kata kunci
  Inggris, teks layar, penekanan), judul + 2 alternatif; validasi `agents/penulis/cek_naskah.py --tulis`. Sebelum Raka, produser
  menjalankan `agents/ide/kata_cari.py "<produk>" --shorts <slug>` → `kata_cari.json`; validator memberi peringatan kalau nama produk
  tidak ada di 2 kalimat pertama/judul atau judul tidak memuat frasa pencarian teratas.
- **Dara**: `bible/gaya-suara.json`; hasil `vo.mp3`, `words.json`, `captions.srt`, `transkrip.txt`. Mesin: VoxCPM2 kalau
  `setup_suara.bat` sudah dijalankan (GPU NVIDIA; per 2026-11-10 BELUM terpasang di laptop → semua video memakai edge-tts
  `id-ID-ArdiNeural`). Jenis suara edge-tts dipilih Zona: `agents/suara/contoh_suara.py` (`contoh_suara.bat`) membuat contoh semua
  suara id-ID + "Multilingual" ke `suara-khas/contoh/`, `--pakai <nama>` menyimpan ke `bible/suara-pilihan.json` (khusus laptop,
  tidak di-commit): `suara_pria`/`suara_wanita` = Shorts (Dara), `suara_panjang` = video panjang (Gilang, hanya dengan `--panjang`
  karena video panjang bisa terupload otomatis). Suara pilihan gagal → otomatis cadangan Ardi (`tts.rekam(cadangan=)`).
  **Pilihan Zona 2026-11-10 (setelah mendengar contoh):** pria `en-AU-WilliamMultilingualNeural` (Shorts + video panjang), wanita
  `en-US-EmmaMultilingualNeural`; keduanya mengirim waktu kata asli. Perekam bersama `agents/suara/tts.py` → `rekam()`: batas kata asli, atau perkiraan
  per suku kata dari batas kalimat untuk suara yang tidak mengirim batas kata. Pelafalan: `bible/lafal.json`
  + `script.json` → `lafal` (nama produk asing → ejaan baca Indonesia); `lafal.ucapkan()` sebelum TTS, `lafal.pulihkan()` sesudahnya
  supaya `words.json`/subtitle tetap tulisan asli.
- **Bima** (`agents/aset/cari_aset.py`): 1–3 shot per kalimat (`SHOT_MAX` 3 dtk), sumber YouTube CC BY → NASA → Wikimedia →
  Pexels/Pixabay; gambar AI maks 10% (`BATAS_AI`), hook selalu footage. Relevansi kandidat (`relevansi()`): kata yang disebut JUDUL
  kandidat (kalimat ×2, topik ×1), kata yang hanya ada di kueri ×0,5, judul menyebut produk utama +4 (`PRODUK`, diisi `atur_produk()`
  dari `idea.json` → `produk`, cadangan kata kunci visual pertama). Footage topik dicari sekali per video, diawali
  "`<produk>` hands on". Rekaman Zona di `milik-saya/` dipakai lebih dulu kalau nama file cocok. Pencarian YouTube CC lewat
  `youtube_cari()` (cache 7 hari di `cache/yt-cari/`, berhenti setelah 403/429 kuota); unduhan > 300 MB ditolak dari header dan
  ditandai `.terlalu-besar`.
- **Mila** (`agents/thumbnail/thumbnail.py`): 1080x1920 < 2 MB, objek asli tanpa latar, gaya hook sama dengan video.
- **Kai** (`agents/editor/rakit.py`, `agents/editor/komposisi.py`, template `agents/editor/hf_template.html`): palet biru
  `bible/gaya-edit.json`, subtitle 1 kata, musik ±10 dB di bawah narasi dari `musik/<suasana>/`, penutup Subscribe,
  `export/info.json` → `gaya_gerak`. **Upgrade editan 2026-11-10** (semua bisa disetel/dimatikan di `bible/gaya-edit.json`):
  - `kamera` (`kuat`, `warna_sinematik`): footage diperlakukan sebagai satu kamera — pembuka mundur cepat, tiap shot bergantian
    dekat/jauh + dorongan pelan, kata penekanan = dorongan singkat, kalimat `wow` = hentakan + garis cepat + irisan cahaya; grade
    kontras/saturasi + vignet. Data `shot` (awal tiap shot) dikirim `rakit.py` → `komposisi.data_video(..., shot=)`.
  - Pembuka: cincin denyut + percikan memancar di belakang objek Mila. Progres atas bersegmen per kalimat.
  - `grafis_otomatis` (`komposisi.grafis_otomatis()`): tanda PRODUK (nama `idea.json` → `produk` + status, tepat setelah hook) dan
    gelembung ajakan komentar di kalimat `penutup`.
  - `audio.efek` (`rakit.daftar_efek()`, `sfx_file()`): hit di pembuka & `wow` (didahului riser), pop saat grafis, ding di penutup;
    dibuat ffmpeg ke `cache/`, file sendiri di `sfx/` (nama memuat hit/pop/riser/ding) didahulukan.
  - Shot terakhir berupa kartu grafis → latar penutup dibuat pekat (tulisan kartu tidak membayang).
  - Uji render di sandbox: `npm install` di root + `HYPERFRAMES_BROWSER_PATH=<chromium Playwright>`; ±8 menit per video uji.
- **Rara** (`agents/qc/periksa.py`, `.claude/skills/qc/SKILL.md`): cek gelap/beku/durasi/LUFS/porsi AI + lihat frame;
  pendeteksi teks `agents/aset/deteksi_teks.py` menolak footage bertulisan. Wajib menilai produk terlihat: `qc_review.json` →
  `produk_terlihat` (< 0,5 = tidak lolos; `skor_qc()` di `agents/autopilot.py` ikut menolak upload otomatis).

## Setelah draft

Upload, jadwal, bersih-bersih → `otak/autopilot-upload.md`. Data hasil tayang → `otak/steve-data.md`.

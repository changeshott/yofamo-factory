# Indeks kode (DIBUAT OTOMATIS — jangan diedit tangan)

Dibuat `python agents/otak.py perbarui` dari kode saat ini: baris pertama docstring tiap script + jumlah baris.
Pakai untuk menemukan file yang tepat tanpa menjelajah folder. Isi lengkap tetap harus dibaca sebelum mengedit.

## agents/aset/

| File | Baris | Isi |
|---|---|---|
| `agents/aset/cari_aset.py` | 699 | Bima — pencari aset Yofamo. Untuk setiap kalimat naskah menyiapkan 1–3 shot vertikal 1080x1920 |
| `agents/aset/deteksi_teks.py` | 221 | Pendeteksi teks di footage (gratis, lokal): subtitle tertempel, judul, watermark, tulisan besar. |
| `agents/aset/gerak.py` | 181 | Alat ffmpeg Bima: menyeragamkan klip ke 1080x1920, membuat gerak Ken Burns untuk gambar AI, |
| `agents/aset/sumber.py` | 186 | Sumber klip Bima. Semua mengembalikan kandidat dengan bentuk yang sama. |

## agents/

| File | Baris | Isi |
|---|---|---|
| `agents/autopilot.py` | 561 | Autopilot Yofamo — tim bekerja sendiri: membuat video & menjadwalkan tayang (bawaan 3 video/hari). |
| `agents/bersih.py` | 203 | Bersih-bersih penyimpanan Yofamo (permintaan Zona): file besar yang sudah tidak diperlukan dihapus otomatis. |
| `agents/kunci.py` | 66 | Kunci proses sederhana (file berisi PID) supaya dua produksi/autopilot tidak berjalan bersamaan. |
| `agents/notif.py` | 130 | Notifikasi ke HP Zona lewat bot Telegram (gratis). Tidak wajib: tanpa pengaturan, semua kabar dilewati diam-diam. |
| `agents/otak.py` | 254 | Otak project Yofamo — ingatan ringkas supaya Claude & agent tidak membaca ulang project dari awal (hemat token). |
| `agents/pabrik.py` | 222 | Pencatat antrean video pabrik Yofamo (SQLite: state.db). |
| `agents/pakai_python.py` | 24 | Pastikan script agent berjalan di Python yang paketnya lengkap. |
| `agents/pemakaian.py` | 134 | Pemakaian token Claude per video (Shorts & video panjang), dari produksi/token-log.jsonl (dicatat agents/produser.py). |
| `agents/produser.py` | 595 | Produser Yofamo: satu permintaan Zona → satu video jadi, otomatis lewat semua agent. |
| `agents/tanpa_jendela.py` | 46 | Windows: semua proses anak (claude, python, ffmpeg, node) berjalan TANPA jendela console. |
| `agents/tes_pabrik.py` | 665 | Tes menyeluruh pabrik Yofamo. Aman: semua tes berjalan di folder sementara, project asli tidak disentuh. |

## agents/editor/

| File | Baris | Isi |
|---|---|---|
| `agents/editor/komposisi.py` | 265 | Kai v3 — lapisan HyperFrames (HTML + GSAP → video). Dipanggil oleh rakit.py, bukan dijalankan langsung. |
| `agents/editor/rakit.py` | 556 | Kai — editor Yofamo. Merakit video Short final langsung dengan ffmpeg (gratis, tanpa buka CapCut): |

## agents/ide/

| File | Baris | Isi |
|---|---|---|
| `agents/ide/cek_ide.py` | 223 | Nova: validasi + skor satu ide (videos/<slug>/idea.json), seperti editor riset memeriksa pitch. |
| `agents/ide/cek_topik.py` | 102 | Cek apakah topik sudah pernah dibahas di channel Yofamo (atau sedang dikerjakan pabrik). |
| `agents/ide/cek_visual.py` | 111 | Nova: cek ketersediaan visual LEGAL untuk satu topik SEBELUM topik itu dipilih. |
| `agents/ide/radar.py` | 226 | Nova: radar topik GRATIS (tanpa token Claude). Mengambil berita teknologi terbaru dari RSS sumber tepercaya |
| `agents/ide/sumber_tier.py` | 66 | Tingkat kepercayaan sumber untuk Nova (dipakai cek_ide.py dan Studio). |

## agents/panjang/

| File | Baris | Isi |
|---|---|---|
| `agents/panjang/animasi.py` | 203 | Tio — animator tim video panjang. Mengubah tiap adegan naskah menjadi animasi lukis-komik (HyperFrames: HTML + GSAP). |
| `agents/panjang/autopilot_panjang.py` | 577 | Autopilot video panjang — tim Ruang Animasi membuat & menjadwalkan sendiri 1 video panjang per hari (bawaan). |
| `agents/panjang/cek_naskah_panjang.py` | 269 | Validator naskah video panjang (dipakai Citra sebelum naskah diserahkan ke Gilang & Tio). |
| `agents/panjang/dokumenter.py` | 319 | Tio (gaya dokumenter modern) — merender tiap adegan video panjang 16:9 (1920x1080, 30 fps). |
| `agents/panjang/footage_panjang.py` | 318 | Bima (16:9) — footage & objek ASLI untuk video panjang gaya dokumenter. |
| `agents/panjang/gambar_ai.py` | 148 | Mesin gambar Ruang Animasi: FLUX.2 [klein] 4B di Cloudflare Workers AI (gratis 10.000 neuron/hari). |
| `agents/panjang/ilustrasi.py` | 139 | Laras — ilustrator video panjang. Gambar gaya lukis-komik (bible/gaya-animasi.json) untuk tiap adegan ilustrasi, |
| `agents/panjang/maskot.py` | 169 | Host Yofa — karakter orisinal Ruang Animasi, digambar AI dengan gaya lukis-komik (bible/gaya-animasi.json). |
| `agents/panjang/periksa_panjang.py` | 150 | Wulan (QC) — pemeriksaan otomatis video panjang sebelum ditonton Zona. |
| `agents/panjang/produser_panjang.py` | 308 | Produser Ruang Animasi: satu klik → video YouTube panjang (5–12 menit) gaya dokumenter modern: |
| `agents/panjang/rakit_panjang.py` | 190 | Wulan — editor akhir video panjang. Menyambung adegan Tio + suara Gilang + musik → export/final.mp4 (1920x1080; dokumenter 30 fps, kartun 24 fps). |
| `agents/panjang/status.py` | 87 | Status video panjang (terpisah dari pabrik Shorts supaya autopilot Shorts tidak pernah menyentuhnya). |
| `agents/panjang/suara_panjang.py` | 132 | Gilang — pengisi suara video panjang. Narasi tiap adegan → suara (edge-tts, gratis) + timing tiap kata & kalimat. |
| `agents/panjang/thumbnail_panjang.py` | 105 | Mila (16:9) — thumbnail video panjang gaya dokumenter: 1280x720 < 2 MB. |
| `agents/panjang/unggah_panjang.py` | 203 | Uli untuk video panjang: unggah video berstatus export (disetujui Zona, atau autopilot video panjang yang lolos QC) |

## agents/penulis/

| File | Baris | Isi |
|---|---|---|
| `agents/penulis/cek_naskah.py` | 300 | Raka: editor naskah otomatis. Memeriksa videos/<slug>/script.json seperti script editor profesional. |

## agents/qc/

| File | Baris | Isi |
|---|---|---|
| `agents/qc/periksa.py` | 287 | Rara — QC (quality control) Yofamo. Memeriksa video final sebelum sampai ke Zona, lalu memperbaiki sendiri. |

## agents/steve/

| File | Baris | Isi |
|---|---|---|
| `agents/steve/analisa.py` | 281 | Steve: mesin analisa. Menggabungkan SEMUA data yang ada menjadi angka siap pakai, supaya laporan Steve |
| `agents/steve/analitik.py` | 134 | Steve v2 — data retensi dari YouTube Analytics (butuh login yang sama dengan Uli). |
| `agents/steve/fetch_stats.py` | 208 | Steve — pengambil statistik publik channel Yofamo Technology. |
| `agents/steve/komentar.py` | 68 | Steve: komentar publik di Shorts channel → apa yang penonton tanyakan, minta, puji, atau keluhkan. |
| `agents/steve/kumpul.py` | 60 | Steve: kumpulkan semua data sekaligus (tanpa kuota Claude), lalu hitung analisanya. |
| `agents/steve/pasar.py` | 94 | Steve: radar pasar — Shorts teknologi berbahasa Indonesia yang sedang ramai 30 hari terakhir (channel lain). |
| `agents/steve/retensi_panjang.py` | 168 | Steve — retensi video panjang per BAB dan per ADEGAN (tanpa kuota Claude). |
| `agents/steve/ytdata.py` | 62 | Alat bersama pengumpul data Steve: baca .env, panggil YouTube Data API (API key), snapshot terbaru. |

## agents/suara/

| File | Baris | Isi |
|---|---|---|
| `agents/suara/buat_suara.py` | 318 | Dara — agent suara Yofamo. Mengubah naskah Raka menjadi voice-over (gratis, edge-tts). |
| `agents/suara/cek_gpu.py` | 45 | Dara: cek apakah laptop siap untuk suara natural VoxCPM2 (GPU NVIDIA) dan mesin video HyperFrames (Node 22). |
| `agents/suara/mesin_suara.py` | 114 | Dara: mesin suara natural (VoxCPM2) yang berjalan di Python khusus suara (.venv-suara). |
| `agents/suara/voxcpm_kerja.py` | 142 | Pekerja suara VoxCPM2 (dijalankan Dara lewat Python khusus suara di .venv-suara, BUKAN langsung). |

## agents/thumbnail/

| File | Baris | Isi |
|---|---|---|
| `agents/thumbnail/thumbnail.py` | 660 | Mila — desainer thumbnail Shorts Yofamo. |

## agents/upload/

| File | Baris | Isi |
|---|---|---|
| `agents/upload/jadwal.py` | 223 | Jadwal tayang Yofamo — mencari jam upload yang paling cocok untuk Shorts, tanpa kuota API & tanpa Claude. |
| `agents/upload/unggah.py` | 313 | Uli — agent upload Yofamo. Mengunggah video yang SUDAH disetujui Zona ke YouTube sebagai PRIVATE, |

## Skill Claude (`.claude/skills/<nama>/SKILL.md`)

| Skill | Isi |
|---|---|
| `/aset` | Bima, pencari aset Yofamo. Pakai saat diminta mencari klip/footage/b-roll/visual untuk video yang suaranya sudah dibuat Dara. Argumen slug video. Merencanakan visual per kalimat (footage CC/NASA/stok, gambar AI, atau kar |
| `/editor` | Kai, editor video Yofamo. Pakai saat diminta merakit, mengedit, atau me-render video final dari shot Bima dan suara Dara. Argumen slug video. Gratis (HyperFrames + ffmpeg), tidak butuh AI. |
| `/ide-riset` | Nova, kepala riset & ide Yofamo. Pakai saat diminta mencari ide video, topik Shorts baru, riset fakta, atau saat tombol Buat video memintanya (mode otomatis). Menghasilkan ide terverifikasi, berskor, dan siap produksi di |
| `/panjang-ide` | Bayu, showrunner & periset video panjang Yofamo (gaya dokumenter modern, 5–12 menit). Pakai saat diminta mencari topik/riset untuk video YouTube PANJANG, atau saat tombol "Buat video panjang" / autopilot video panjang me |
| `/panjang-naskah` | Citra, penulis naskah video YouTube PANJANG Yofamo (gaya dokumenter modern: footage asli + selingan motion graphic, 5–12 menit). Pakai saat diminta menulis naskah video panjang dari panjang/<slug>/ide.json. Argumen slug. |
| `/penulis` | Raka, kepala penulis naskah Shorts Yofamo. Pakai saat diminta menulis naskah, judul, hook, deskripsi, tag, atau memangkas naskah untuk ide yang sudah disetujui. Argumen opsional slug video (dan --pangkas <detik>). Mengha |
| `/qc` | Rara, quality control Yofamo. Pakai setelah Bima menyiapkan shot (mode --pra, sebelum dirakit), setelah Kai merakit video (mode --akhir), atau saat diminta memeriksa/menilai/memperbaiki kualitas video. Argumen slug video |
| `/qc-panjang` | Wulan, QC visual video panjang Yofamo (gaya dokumenter). Pakai setelah video panjang dirakit (status draft) dan sebelum disetujui/diupload otomatis, atau saat diminta memeriksa/menilai video panjang. Argumen slug video p |
| `/steve-analis` | Steve, kepala analis channel YouTube Yofamo. Pakai saat diminta "panggil Steve", analisa channel, laporan mingguan, rekomendasi topik, evaluasi video, post-mortem, atau strategi pertumbuhan berbasis data (statistik, rete |
| `/suara` | Dara, agent suara Yofamo. Pakai saat diminta membuat voice-over, suara, atau subtitle dari naskah Raka. Argumen slug video. Gratis (edge-tts), tidak butuh AI. |
| `/thumbnail` | Mila, desainer thumbnail Shorts Yofamo. Pakai saat diminta membuat, mengganti, atau memperbaiki thumbnail video Shorts, atau objek di belakang tulisan hook. Argumen slug video (opsional --pilih N / --ulang). Gratis (remb |
| `/upload` | Uli, agent upload Yofamo. Pakai saat Zona meminta mengunggah video yang SUDAH disetujui (status export) ke YouTube, mengatur jadwal tayang, atau menanyakan autopilot. Argumen slug video dan jadwal opsional. Upload selalu |

## Studio (Next.js, `studio/`)

Rute API (`studio/app/api/<nama>/route.ts`): `antrean`, `autopilot`, `bible`, `hapus`, `kelola`, `log`, `media`, `musik`, `panjang`, `pemakaian`, `report`, `run`, `state`, `stop`, `video`.

- `studio/components/`: `Studio.tsx`, `jadwal.tsx`, `panels.tsx`, `ui.tsx`
- `studio/lib/`: `format.ts`, `types.ts`
- `studio/lib/server/`: `autopilot.ts`, `guard.ts`, `jadwal.ts`, `jobs.ts`, `panjang.ts`, `project.ts`

## Aturan & gaya (`bible/`)

- `bible/autopilot.json`
- `bible/channel-bible.md`
- `bible/gaya-animasi.json`
- `bible/gaya-dokumenter.json`
- `bible/gaya-edit.json`
- `bible/gaya-suara.json`
- `bible/gaya-upload.json`
- `bible/panjang-bible.md`
- `bible/penyimpanan.json`

# Yofamo Shorts Factory

Pabrik konten otomatis untuk channel YouTube **Yofamo Technology** (@yofamoo_technology):
Shorts faceless berbahasa Indonesia tentang teknologi nyata yang terasa seperti fiksi ilmiah.
Pemilik: Zona. Semua jawaban dan laporan ditulis dalam **bahasa Indonesia**.

## Tim agent

| Nama | Peran | Skill | Status |
| --- | --- | --- | --- |
| Steve | Kepala analis: statistik, retensi & kurva penonton, komentar, radar pasar, eksperimen, post-mortem → laporan mingguan, `insights/topik_backlog.json` (dipakai Nova), `pelajaran.md`, `eksperimen.md` | `/steve-analis` | aktif |
| Nova | Kepala riset & ide: radar RSS gratis (`radar.py`, hemat token) → longlist → saring → cek ketersediaan footage (`cek_visual.py`) → verifikasi jurnalis (≥3 fakta, kutipan, sumber tier 1) → paket ide (3+ varian hook, angka kunci, salah kaprah, kata kunci visual) → `cek_ide.py` (validasi + skor 0–100); portofolio 2 andalan + 1 eksplorasi; selalu belum pernah dibahas → `videos/<slug>/idea.json` | `/ide-riset [tema]` / `/ide-riset --otomatis [arahan]` | aktif |
| Raka | Kepala penulis: target durasi sesuai topik, struktur beat (pembuka khas "Tau nggak, …" → konteks → cara kerja → wow → penutup tuntas), lembar produksi per kalimat (jenis visual, kata kunci Inggris, teks layar, penekanan), judul + 2 alternatif, komentar pin → `script.json`, `naskah.md` (divalidasi `cek_naskah.py`) | `/penulis <slug>` | aktif |
| Dara | Suara: voice-over gratis — **VoxCPM2** natural lokal (GPU NVIDIA, `setup_suara.bat`) atau cadangan edge-tts — + timing kata + subtitle + transkrip bertimestamp → `vo.mp3`, `words.json` (+ target durasi), `captions.srt`, `transkrip.txt` | `/suara <slug>` | aktif |
| Bima | Visual: 1–3 shot 1080x1920 per kalimat, **utamakan potongan YouTube CC BY yang memperlihatkan teknologi yang dibahas** (≥ 80% footage asli, kandidat diurutkan menurut relevansi kalimat + topik; kalau kurang, bagian lain dari klip topik yang sama), lalu NASA/Wikimedia Commons (Pexels/Pixabay opsional), kartu grafis, dan gambar AI hanya cadangan terakhir (**maks 10% shot**) → `aset/NN-a.mp4`, `aset/manifest.json` | `/aset <slug>` | aktif |
| Kai | Editor: rakit video final (**HyperFrames** HTML+GSAP, cadangan ffmpeg; font Poppins Black di `fonts/`) — palet biru khas channel (`bible/gaya-edit.json` → `palet`), gerak halus tanpa memantul, grafis gerak sesuai kalimat (angka, langkah, perbandingan, kata, label, sumber) + kartu grafis Bima digambar ulang sebagai layar penuh, penutup ajakan Subscribe, **gaya gerak berbeda tiap video** (kombinasi varian hook/subtitle/stabilo/kartu/latar/aksen/nuansa biru + urutan transisi, dipilih yang paling jarang dipakai → dicatat di `export/info.json` → `gaya_gerak`), gaya khas Yofamo: hook bertingkat putih/kuning/biru muncul bertahap, subtitle 1 kata di tengah (penekanan kuning), gerak keyframe, transisi antar-kalimat sinkron suara, denyut zoom, whoosh, musik per suasana (±10 dB di bawah narasi), layar penutup → `export/final.mp4` | `/editor <slug>` | aktif |
| Rara | QC: cek otomatis (gelap/beku/durasi/LUFS/porsi AI) + lihat frame tiap shot, tolak yang jelek → Bima ganti → Kai rakit ulang (maks 2 putaran) → `export/qc.json`, `qc_review.json` | `/qc <slug>` | aktif |
| Uli | Upload: video `export` → YouTube **private + jadwal tayang** di jam terbaik (`agents/upload/jadwal.py` → `insights/jadwal.md`), deskripsi otomatis **tanpa link sumber** (kredit singkat + hashtag lengkap, `bible/gaya-upload.json`), label konten sintetis → `export/upload.json`. Memimpin **Autopilot** (`agents/autopilot.py`): 3 video/hari dibuat & dijadwalkan sendiri | `/upload <slug>` | aktif |

Setiap agent adalah satu skill Claude Code di `.claude/skills/`. Kalau diminta "panggil Steve/Nova/Raka/Dara/Bima/Kai/Rara/Uli", jalankan skill-nya.

Alur saat ini: Steve (laporan) → Nova (3 ide, status `ide`) → **Zona menyetujui di Studio Yofamo** (`disetujui`) → Raka (naskah, status `naskah`) → Dara (suara + subtitle, status `suara`) → Bima (klip, status `aset`) → Kai (video final, status `draft`) → Rara (QC + perbaikan) → **Zona menonton & menyetujui** (`export`) → Uli (upload private) → Zona menayangkan di YouTube Studio → `terbit` → Steve membaca retensi → `insights/pelajaran.md` → putaran berikutnya lebih baik.

**Jalur cepat — tombol "+ Buat video" di Studio** (`agents/produser.py`): Zona cukup klik (arahan tema opsional) → Steve memperbarui daftar video channel → Nova **memilih sendiri** 1 topik yang paling berpotensi menang dan **belum pernah dibahas** di channel (cek `cek_topik.py` + penilaian Nova; kalau ternyata duplikat, ditolak dan Nova mencari lagi), tetap 2 sumber → ide otomatis disetujui karena Zona yang menekan tombol → Raka → Dara (durasi di luar target naskah diperbaiki otomatis: kecepatan suara disesuaikan atau Raka memangkas) → Bima → Kai → Rara → video `draft` yang tetap harus ditonton dan disetujui Zona. Beberapa permintaan bisa diantrekan (`produksi/antrean.json`). Kemajuan di `produksi/<id>.json`. Hanya satu produksi berjalan pada satu waktu (`produksi/produser.lock`).

**Autopilot** (`agents/autopilot.py`; **menyala otomatis saat Studio dibuka** (`jalan_saat_studio_dibuka`) dan **mati sendiri setelah stok lengkap**; opsional juga lewat Windows Task Scheduler `pasang_autopilot.bat` → `autopilot.vbs`): hitung jam tayang terbaik (`insights/jadwal.md`) → isi slot tayang **hari ini + besok** (`isi_hari: 2`; hari pertama 6 video, berikutnya menambah stok besok) dengan video siap (status `export` dulu, lalu video buatan autopilot yang lolos Rara dengan skor ≥ `skor_qc_min` → disetujui otomatis) → Uli unggah private + jadwal tayang → slot yang belum punya video → produser membuat video baru berurutan dari slot terdekat (maks `maks_produksi_per_hari`, bawaan 8) → jam tayang lewat → `terbit`. Slot hari ini yang terlewat karena video belum siap dipindah ke jam lain hari ini yang masih sempat. Stok lengkap → `aktif: false`. Kalau produksi terhenti (mis. rakit ulang Rara terputus), video itu dilanjutkan (`--lanjut`) sebelum membuat video baru. Video di bawah skor tetap `draft` menunggu Zona. Pengaturan `bible/autopilot.json`, status `produksi/autopilot.json`, log `logs/autopilot-<tanggal>.txt`.

## Struktur folder

- `bible/autopilot.json` — pengaturan autopilot (aktif, video per hari, setujui otomatis, skor QC minimal, jam tayang). `bible/gaya-upload.json` — deskripsi & hashtag Uli. `bible/penyimpanan.json` — bersih-bersih otomatis setelah upload. `insights/jadwal.json`/`.md` — jam tayang terbaik (dibuat `jadwal.py`).
- `bible/gaya-edit.json` — gaya editan Kai (font, warna & ukuran subtitle, hook bertingkat, gerak & transisi, musik).
- `fonts/` — font khas Yofamo (Poppins Black/ExtraBold, lisensi OFL).
- `package.json` — mesin video Kai (hyperframes, gsap). Pasang sekali: `npm install` di folder project (butuh Node.js 22+).
- `bible/gaya-suara.json` — gaya suara Dara (mesin, desain suara VoxCPM2, edge-tts). `suara-khas/` — referensi suara khas yang dibuat sekali (tidak di-commit). `.venv-suara/` — Python 3.12 khusus suara (dibuat `setup_suara.bat`).
- `insights/radar.md` — 30 kandidat berita teknologi terbaru (dibuat `radar.py`, tanpa token).
- `musik/<suasana>/` (tegang, ceria, misterius, epik, haru) — perpustakaan musik latar Zona (mis. dari YouTube Audio Library); dipilih otomatis sesuai suasana naskah & digilir, volume ±10 dB di bawah narasi (`bible/gaya-edit.json` → `audio.musik_di_bawah_narasi_db`); pilihan per video di `videos/<slug>/musik.json` (meja Uli di Studio); kredit lagu di `<lagu>.txt` masuk deskripsi. Jangan pernah mengambil lagu dari video YouTube biasa. `sfx/` — efek suara. Tidak di-commit.
- `bible/channel-bible.md` — aturan gaya & konten. **Wajib dibaca** sebelum membuat ide, naskah, atau menilai video.
- `agents/<nama>/` — script Python milik tiap agent. Jalankan dari root project.
- `insights/raw/` — data mentah statistik (JSON) dari script Steve. Jangan diedit manual.
- `insights/YYYY-Www.md` — laporan mingguan Steve (contoh `2026-W44.md`).
- `videos/<slug>/` — semua file satu video: `idea.json`, `script.json`, `naskah.md`, `vo.mp3`, `words.json`, `captions.srt`, `transkrip.txt`, `aset/` (`rencana.json`, `kandidat.json`, `lembar/`, `pilihan.json`, shot `NN-a.mp4`, `manifest.json`, `KREDIT.txt`, `kredit_deskripsi.txt`), `export/`.
- `state.db` — SQLite antrean & status tiap video. Diakses hanya lewat `python agents/pabrik.py`.
- `studio/` — Studio Yofamo: kantor virtual lokal (Next.js + TypeScript + Tailwind). Membaca file project dan menjalankan agent lewat `claude -p`.
- `logs/` — log setiap tugas yang dijalankan.
- `produksi/` — catatan kemajuan tiap permintaan "Buat video" (tidak di-commit).
- `milik-saya/` — rekaman Zona sendiri (layar HP, gadget, dll). Bima memakainya lebih dulu kalau nama file cocok dengan kalimat, misalnya `tangan-robot-lab.mp4`. Tidak di-commit.
- `rahasia/` — OAuth client & token YouTube (tidak pernah di-commit, jangan dibaca/ditampilkan agent).
- `insights/pelajaran.md` — aturan hasil belajar dari retensi penonton (ditulis Steve).
- `insights/topik_backlog.json` — topik berperingkat yang belum pernah dibahas (Steve → Nova).
- `insights/eksperimen.md` — uji coba aktif (Steve → Raka/Bima/Kai); Raka mencatat varian di `script.json` → `eksperimen`.
- `cache/` — unduhan mentah Bima (boleh dihapus Zona kalau penuh, tidak di-commit).

## Aturan kerja

- Angka selalu berasal dari file di `insights/raw/`, tidak pernah dikarang. Kalau data kurang, tulis "data belum cukup".
- Satu video sedikit (< 5) bukan pola. Sebut sebagai "dugaan" sampai ada minimal 5 video pendukung.
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru. Satu-satunya pengecualian: `agents/bersih.py` (permintaan Zona, `bible/penyimpanan.json`) otomatis menghapus file besar video yang **sudah diupload** (final.mp4, render, shot, suara) plus cache unduhan lama & file sementara; data kecil (naskah, timing, manifest, info, upload, QC) tetap disimpan.
- Klip hanya dari sumber berlisensi bebas: YouTube **Creative Commons (CC BY)** lewat script Bima, NASA, Wikimedia Commons (hanya PD/CC0/CC BY), Pexels, Pixabay, gambar AI, atau milik Zona. Jangan pernah mengambil video YouTube biasa, TikTok, film, atau berita.
- Hanya Uli yang boleh mengupload, hanya video berstatus `export`, dan selalu **private** (boleh dengan jadwal tayang `publishAt`, sehingga YouTube menayangkannya sendiri). Status `export` berasal dari persetujuan Zona, atau dari autopilot yang dinyalakan Zona (hanya video buatan autopilot yang lolos Rara dengan skor ≥ `skor_qc_min`). Tidak ada agent yang menghapus atau mengubah video yang sudah ada di YouTube. Steve hanya **membaca** data.
- Deskripsi YouTube tanpa link sumber. Kredit footage CC BY tetap dicantumkan singkat (judul, pembuat, lisensi) tanpa link; link lengkap tersimpan di `aset/KREDIT.txt`.
- Menghapus hasil (video, log, laporan) hanya dilakukan Zona lewat panel Kelola di Studio (`pabrik.py hapus`). Agent tidak pernah menghapus, kecuali bersih-bersih otomatis `bersih.py` di atas.
- API key ada di `.env` (dibaca script). Jangan menampilkan isi `.env` di chat atau laporan.
- Ringkasan akhir agent: maksimal sekitar 15 baris, poin terpenting dulu. Laporan dan log dibaca Zona lewat Studio Yofamo (`studio/`).
- Jangan mengubah file di `studio/` kecuali diminta.
- Status video hanya diubah lewat `agents/pabrik.py`. Agent tidak boleh menyetujui ide sendiri; persetujuan selalu dari Zona (permintaan lewat "Buat video" dihitung sebagai persetujuan Zona untuk ide itu saja). Video final ditonton & disetujui Zona, kecuali saat autopilot aktif (lihat aturan upload di atas).
- Hanya script di `agents/` yang boleh dijalankan. Jangan meng-install paket atau menjalankan perintah lain tanpa diminta.

## Perintah penting

```bash
python agents/steve/fetch_stats.py          # ambil statistik terbaru → insights/raw/
python agents/steve/fetch_stats.py --check  # cek API key & koneksi saja
python agents/pabrik.py list                # lihat antrean video
python agents/penulis/cek_naskah.py <slug> --tulis  # Raka: validasi naskah + naskah.md
python agents/suara/buat_suara.py <slug>    # Dara: vo.mp3 + words.json + captions.srt (gratis)
python agents/aset/cari_aset.py semua <slug> # Bima cepat: cari + pilih otomatis + bentuk shot
python agents/aset/cari_aset.py cari <slug>  # Bima: kandidat + lembar kontak (lalu pilihan.json → unduh)
python agents/editor/rakit.py <slug>        # Kai: rakit export/final.mp4
python agents/produser.py ["arahan tema"]  # satu klik → tim pilih topik baru → video jadi
python agents/ide/radar.py                   # Nova: kandidat topik dari RSS tepercaya, gratis tanpa token
python agents/suara/cek_gpu.py              # cek kesiapan suara natural (GPU) & mesin HyperFrames
python agents/ide/cek_topik.py "judul"      # cek topik belum pernah dibahas (--daftar: semua judul)
python agents/ide/cek_visual.py "kata"      # Nova: ada footage legal untuk topik ini? (skor 0–10)
python agents/ide/cek_ide.py <slug> --tulis # Nova: validasi sumber/kutipan/angka + skor ide 0–100
python agents/qc/periksa.py otomatis <slug> # Rara cepat: cek + ganti shot gelap/beku
python agents/upload/unggah.py login        # Uli: hubungkan YouTube (sekali)
python agents/upload/unggah.py pratinjau <slug>  # Uli: lihat judul, deskripsi (tanpa link) & hashtag tanpa upload
python agents/upload/jadwal.py              # jam tayang terbaik → insights/jadwal.md
python agents/autopilot.py status|nyala|mati|jalan  # autopilot 3 video/hari
python agents/bersih.py semua [--coba]      # hapus file besar video yang sudah diupload + cache lama (--coba: lihat dulu)
pasang_autopilot.bat                        # pasang penjadwal Windows tiap jam (sekali); "pasang_autopilot.bat hapus" untuk melepas
python agents/steve/kumpul.py [--pasar]     # Steve: semua data (statistik, komentar, analitik, pasar) + analisa, tanpa kuota Claude
python agents/steve/analisa.py              # Steve: hitung KPI, pola, retensi, peluang → insights/raw/analisa-*.json/.md
python agents/tes_pabrik.py [--online]     # tes seluruh pabrik (aman, di folder sementara)
start_studio.bat                            # buka Studio Yofamo (Windows)
cd studio && npm run dev                    # sama, manual (http://127.0.0.1:3210)
```

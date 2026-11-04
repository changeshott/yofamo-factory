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
| Mila | Thumbnail: objek ASLI yang dibahas (foto asli Pexels/Pixabay/Wikimedia PD-CC0-CC BY + frame footage Bima; latar dihapus rembg lokal gratis, hanya objek utama; 6 kandidat dinilai utuh/besar/tajam → `thumbnail/kandidat.jpg`; Mila (Claude) memilih `--pilih N` atau memotong dari frame `--potong <frame> --kotak`), latar transparan + bayangan tebal di sekelilingnya, di belakang hook bertingkat dengan font, warna & garis **sama persis dengan video** (bayangan teks tebal), latar frame shot pembuka + cahaya biru → `thumbnail/objek.png`, `export/thumbnail.jpg` (1080x1920, < 2 MB). Objek yang sama dianimasikan Kai bersama tulisan hook di detik awal video. Dipasang otomatis oleh Uli saat upload | `/thumbnail <slug>` | aktif |
| Kai | Editor: rakit video final (**HyperFrames** HTML+GSAP, cadangan ffmpeg; font Poppins Black di `fonts/`) — palet biru khas channel (`bible/gaya-edit.json` → `palet`), gerak halus tanpa memantul, grafis gerak sesuai kalimat (angka, langkah, perbandingan, kata, label, sumber) + kartu grafis Bima digambar ulang sebagai layar penuh, penutup ajakan Subscribe, **gaya gerak berbeda tiap video** (kombinasi varian hook/subtitle/stabilo/kartu/latar/aksen/nuansa biru + urutan transisi, dipilih yang paling jarang dipakai → dicatat di `export/info.json` → `gaya_gerak`), gaya khas Yofamo: hook bertingkat putih/kuning/biru muncul bertahap, subtitle 1 kata di tengah (penekanan kuning), gerak keyframe, transisi antar-kalimat sinkron suara, denyut zoom, whoosh, musik per suasana (±10 dB di bawah narasi), layar penutup → `export/final.mp4` | `/editor <slug>` | aktif |
| Rara | QC dua tahap: **pra** (sebelum Kai merakit: cek shot paralel + lihat lembar shot & thumbnail, shot jelek diganti Bima tanpa render, objek thumbnail jelek → Mila `--pilih N`) lalu **akhir** (cek otomatis gelap/beku/durasi/LUFS/porsi AI + lihat frame video jadi, ganti maks 1 putaran hanya untuk masalah berat, skor) → `export/qc_pra.json`, `qc.json`, `qc_review.json` | `/qc <slug> --pra` / `--akhir` | aktif |
| Uli | Upload: video `export` → YouTube **private + jadwal tayang** di jam terbaik (`agents/upload/jadwal.py` → `insights/jadwal.md`), deskripsi otomatis **tanpa link sumber** (kredit singkat + hashtag lengkap, `bible/gaya-upload.json`), label konten sintetis → `export/upload.json`. Memimpin **Autopilot** (`agents/autopilot.py`): 3 Shorts/hari + **1 video panjang/hari** (`agents/panjang/autopilot_panjang.py`) dibuat & dijadwalkan sendiri. Studio menghitung upload minggu ini (tayang + terjadwal, Shorts & panjang) terhadap target autopilot | `/upload <slug>` | aktif |

### Ruang Animasi — video YouTube panjang (kantor kedua, di samping kantor Shorts)

Video **5–12 menit**, 16:9, gaya **dokumenter modern** (referensi "Video 1" Zona — bukan kartun, bukan gaya kayu/kuning vintage):
sebagian besar **footage asli** teknologi yang dibahas (tanpa teks/subtitle/watermark di dalamnya — dicek pendeteksi teks), diselingi
**motion graphic** tenang: kertas abu-abu terang, serif Instrument Serif + Inter, benda asli berwarna berlatar transparan & berbayang lembut,
foto hitam-putih, mockup HP/TV, butiran film + garis VHS tipis. Footage biasa: butiran tipis + vignet, subtitle kecil di tengah bawah
(disembunyikan saat motion graphic). 1080p 30 fps. Aturan konten: `bible/panjang-bible.md`; gaya: `bible/gaya-dokumenter.json`.
Terpisah total dari pabrik Shorts (folder `panjang/<slug>/`, status `panjang/<slug>/status.json` lewat `agents/panjang/status.py`, tidak memakai `state.db`).

| Nama | Peran | Skill / script | Status |
| --- | --- | --- | --- |
| Bayu | Showrunner & riset: 1 teknologi nyata (sering dari Shorts yang menang) yang punya cukup footage (`cek_visual.py`), ≥ 5 fakta bersumber, alur 3–5 bab → `ide.json` | `/panjang-ide [tema]` | aktif |
| Citra | Naskah per adegan `"format": "dokumenter"` (pembuka "Tau nggak, …", footage ≥ 50%, motion graphic: cara_kerja/angka/banding/garis_waktu/objek/kata/hp/tv, ≥ 3 bab, penutup) → `naskah.json` (divalidasi `cek_naskah_panjang.py`). Mode `--visual N,M`: ganti kata kunci visual adegan yang tidak dapat footage | `/panjang-naskah <slug>` | aktif |
| Gilang | Narasi per adegan (edge-tts) + timing kata → `suara/NN.mp3`, `suara/waktu.json` | `agents/panjang/suara_panjang.py` | aktif |
| Laras | Footage 16:9 asli per adegan (YouTube CC BY, NASA, Wikimedia, Pexels, Pixabay) — tiap shot dicek OCR mode ketat (subtitle, tulisan besar, label nama kecil, watermark pojok → ditolak), gelap/beku ditolak; benda asli dari foto (rembg) untuk motion graphic & thumbnail; kredit → `footage/`, `media/`, `footage/kredit_deskripsi.txt`. Kurang footage → Citra ganti kata kunci → `--cadangan` (pinjam shot adegan terdekat) | `agents/panjang/footage_panjang.py` | aktif |
| Tio | Render tiap adegan (HyperFrames template `dokumenter.html` + ffmpeg untuk footage) → `adegan/NN.mp4`; `--pratinjau` foto frame tanpa render | `agents/panjang/dokumenter.py` | aktif |
| Wulan | Rakit 1080p 30 fps (bitrate dibatasi) + suara + musik, chapter, subtitle .srt, thumbnail 16:9 (`thumbnail_panjang.py`: frame hitam-putih + benda asli berwarna + 2–4 kata), QC berskor 0–10 → `export/` | `agents/panjang/rakit_panjang.py`, `periksa_panjang.py` | aktif |

Alur: tombol **Buat** di Studio → Ruang Animasi (`agents/panjang/produser_panjang.py`, kemajuan `produksi/panjang/<id>.json`) → Bayu → Citra → Gilang → Laras → Tio → Wulan → status `draft` → **Zona menonton & menyetujui** (`export`) → Uli mengunggah private + jadwal tayang (`agents/panjang/unggah_panjang.py`; chapter, deskripsi tanpa link, kredit footage singkat, thumbnail). Video kartun lama (naskah tanpa `format`) tetap bisa dilanjutkan dengan jalur lama (`ilustrasi.py`, `animasi.py`, host Yofa).

**Autopilot video panjang** (`agents/panjang/autopilot_panjang.py`, permintaan Zona Nov 2026): **1 video panjang per hari** dibuat & dijadwalkan sendiri (stok hari ini + besok). Jalan saat Studio dibuka, tiap ±1 jam selama Studio terbuka, dan setiap putaran autopilot Shorts (di latar, tidak menahan Shorts). Jam tayang: otomatis jam terbaik 15–21 menit :30, ≥ 90 menit dari jam Shorts (atau `panjang.jam`). Video buatan autopilot yang **lolos QC Wulan dengan skor ≥ `panjang.skor_qc_min`** disetujui otomatis → Uli unggah **private + publishAt**; yang tidak lolos tetap `draft` menunggu Zona. Video dari tombol Buat tetap menunggu Zona. Pengaturan `bible/autopilot.json` → `panjang` (aktif, video_per_hari, setujui_otomatis, skor_qc_min, jam; nilai bawaan di kode), status `produksi/autopilot-panjang.json`, log `logs/autopilot-panjang-<tanggal>.txt`. Tidak mengganggu Shorts: prioritas CPU rendah, tiap adegan menunggu kalau produksi Shorts sedang jalan, satu video panjang pada satu waktu (`produksi/panjang.lock`).

Setiap agent adalah satu skill Claude Code di `.claude/skills/`. Kalau diminta "panggil Steve/Nova/Raka/Dara/Bima/Mila/Kai/Rara/Uli", jalankan skill-nya.

Alur saat ini: Steve (laporan) → Nova (3 ide, status `ide`) → **Zona menyetujui di Studio Yofamo** (`disetujui`) → Raka (naskah, status `naskah`) → Dara (suara + subtitle, status `suara`) → Bima (klip, status `aset`) → Mila (thumbnail + objek hook) → Kai (video final, status `draft`) → Rara (QC + perbaikan) → **Zona menonton & menyetujui** (`export`) → Uli (upload private) → Zona menayangkan di YouTube Studio → `terbit` → Steve membaca retensi → `insights/pelajaran.md` → putaran berikutnya lebih baik.

**Jalur cepat — tombol "+ Buat video" di Studio** (`agents/produser.py`): Zona cukup klik (arahan tema opsional) → Steve memperbarui daftar video channel → Nova **memilih sendiri** 1 topik yang paling berpotensi menang dan **belum pernah dibahas** di channel (cek `cek_topik.py` + penilaian Nova; kalau ternyata duplikat, ditolak dan Nova mencari lagi), tetap 2 sumber → ide otomatis disetujui karena Zona yang menekan tombol → Raka → Dara (durasi di luar target naskah diperbaiki otomatis: kecepatan suara disesuaikan atau Raka memangkas) → Bima → Mila (thumbnail) → Rara pra-periksa (shot & thumbnail sebelum dirakit) → Kai → Rara (penilaian akhir) → video `draft` yang tetap harus ditonton dan disetujui Zona. Beberapa permintaan bisa diantrekan (`produksi/antrean.json`). Kemajuan di `produksi/<id>.json`. Hanya satu produksi berjalan pada satu waktu (`produksi/produser.lock`).

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
- `videos/<slug>/` — semua file satu video: `idea.json`, `script.json`, `naskah.md`, `vo.mp3`, `words.json`, `captions.srt`, `transkrip.txt`, `thumbnail/` (`objek.png`, `info.json`), `aset/` (`rencana.json`, `kandidat.json`, `lembar/`, `pilihan.json`, shot `NN-a.mp4`, `manifest.json`, `KREDIT.txt`, `kredit_deskripsi.txt`), `export/`.
- `state.db` — SQLite antrean & status tiap video. Diakses hanya lewat `python agents/pabrik.py`.
- `studio/` — Studio Yofamo: kantor virtual lokal (Next.js + TypeScript + Tailwind). Membaca file project dan menjalankan agent lewat `claude -p`. Sidebar kiri = tim & siapa mengerjakan apa; sidebar kanan = **jadwal tayang** (slot hari ini/besok/lusa, status tayang/terjadwal/sedang dibuat/kosong, sampul, hitung mundur; di HP lewat tombol Jadwal di dok). Juga layar jadwal di dinding kantor.
- `logs/` — log setiap tugas yang dijalankan.
- `produksi/` — catatan kemajuan tiap permintaan "Buat video" (tidak di-commit).
- `milik-saya/` — rekaman Zona sendiri (layar HP, gadget, dll). Bima memakainya lebih dulu kalau nama file cocok dengan kalimat, misalnya `tangan-robot-lab.mp4`. Tidak di-commit.
- `rahasia/` — OAuth client & token YouTube (tidak pernah di-commit, jangan dibaca/ditampilkan agent).
- `insights/pelajaran.md` — aturan hasil belajar dari retensi penonton (ditulis Steve).
- `insights/topik_backlog.json` — topik berperingkat yang belum pernah dibahas (Steve → Nova).
- `insights/eksperimen.md` — uji coba aktif (Steve → Raka/Bima/Kai); Raka mencatat varian di `script.json` → `eksperimen`.
- `panjang/<slug>/` — video panjang Ruang Animasi: `ide.json`, `naskah.json`, `naskah.md`, `suara/`, `footage/` (shot + manifest + kredit), `media/` (objek asli PNG), `hf/`, `adegan/`, `export/` (final.mp4, thumbnail.jpg, bab.txt, subtitle.srt, qc.json, upload.json). Tidak di-commit.
- `cache/` — unduhan mentah Bima (boleh dihapus Zona kalau penuh, tidak di-commit).

## Aturan kerja

- Angka selalu berasal dari file di `insights/raw/`, tidak pernah dikarang. Kalau data kurang, tulis "data belum cukup".
- Satu video sedikit (< 5) bukan pola. Sebut sebagai "dugaan" sampai ada minimal 5 video pendukung.
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru. Satu-satunya pengecualian: `agents/bersih.py` (permintaan Zona, `bible/penyimpanan.json`) otomatis menghapus file besar video yang **sudah diupload** (final.mp4, render, shot, suara) plus cache unduhan lama & file sementara; data kecil (naskah, timing, manifest, info, upload, QC) tetap disimpan.
- Klip hanya dari sumber berlisensi bebas: YouTube **Creative Commons (CC BY)** lewat script Bima, NASA, Wikimedia Commons (hanya PD/CC0/CC BY), Pexels, Pixabay, gambar AI, atau milik Zona. Jangan pernah mengambil video YouTube biasa, TikTok, film, atau berita.
- Hanya Uli yang boleh mengupload, hanya video berstatus `export`, dan selalu **private** (boleh dengan jadwal tayang `publishAt`, sehingga YouTube menayangkannya sendiri). Status `export` berasal dari persetujuan Zona, atau dari autopilot yang dinyalakan Zona (Shorts: hanya video buatan autopilot yang lolos Rara dengan skor ≥ `skor_qc_min`; video panjang: hanya video buatan autopilot video panjang yang lolos QC Wulan dengan skor ≥ `panjang.skor_qc_min`). Tidak ada agent yang menghapus atau mengubah video yang sudah ada di YouTube. Steve hanya **membaca** data.
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
python agents/thumbnail/thumbnail.py <slug> [--ulang]  # Mila: thumbnail (objek transparan di belakang hook) → export/thumbnail.jpg
python agents/qc/periksa.py pra <slug>      # Rara sebelum Kai merakit: cek shot paralel, ganti tanpa render
python agents/qc/periksa.py otomatis <slug> # Rara cepat: cek + ganti shot gelap/beku
python agents/upload/unggah.py login        # Uli: hubungkan YouTube (sekali)
python agents/upload/unggah.py pratinjau <slug>  # Uli: lihat judul, deskripsi (tanpa link) & hashtag tanpa upload
python agents/upload/jadwal.py              # jam tayang terbaik → insights/jadwal.md
python agents/autopilot.py status|nyala|mati|jalan  # autopilot 3 video/hari
python agents/bersih.py semua [--coba]      # hapus file besar video yang sudah diupload + cache lama (--coba: lihat dulu)
pasang_autopilot.bat                        # pasang penjadwal Windows tiap jam (sekali); "pasang_autopilot.bat hapus" untuk melepas
python agents/steve/kumpul.py [--pasar]     # Steve: semua data (statistik, komentar, analitik, pasar) + analisa, tanpa kuota Claude
python agents/steve/analisa.py              # Steve: hitung KPI, pola, retensi, peluang → insights/raw/analisa-*.json/.md
python agents/panjang/produser_panjang.py ["tema"]   # Ruang Animasi: video panjang gaya dokumenter (--lanjut <slug>, --uji)
python agents/panjang/autopilot_panjang.py jalan|status|nyala|mati   # autopilot video panjang 1/hari + upload private terjadwal
python agents/panjang/footage_panjang.py <slug> [--ulang N] [--cadangan]  # Laras: footage 16:9 tanpa teks + objek asli
python agents/panjang/dokumenter.py <slug> --pratinjau   # Tio: foto frame motion graphic tiap adegan (cepat, tanpa render)
python agents/aset/deteksi_teks.py <video.mp4> [--halus]   # cek ada teks/subtitle/watermark di footage (--halus: termasuk tulisan kecil)
python agents/panjang/unggah_panjang.py pratinjau|unggah <slug> [--jadwal 2026-11-03T19:30]
python agents/tes_pabrik.py [--online]     # tes seluruh pabrik (aman, di folder sementara)
start_studio.bat                            # buka Studio Yofamo (Windows)
cd studio && npm run dev                    # sama, manual (http://127.0.0.1:3210)
```

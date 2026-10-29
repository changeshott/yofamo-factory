# Yofamo Shorts Factory

Pabrik konten otomatis untuk channel YouTube **Yofamo Technology** (@yofamoo_technology):
Shorts faceless berbahasa Indonesia tentang teknologi nyata yang terasa seperti fiksi ilmiah.
Pemilik: Zona. Semua jawaban dan laporan ditulis dalam **bahasa Indonesia**.

## Tim agent

| Nama | Peran | Skill | Status |
| --- | --- | --- | --- |
| Steve | Kepala analis: statistik, retensi & kurva penonton, komentar, radar pasar, eksperimen, post-mortem → laporan mingguan, `insights/topik_backlog.json` (dipakai Nova), `pelajaran.md`, `eksperimen.md` | `/steve-analis` | aktif |
| Nova | Kepala riset & ide: longlist → saring → cek ketersediaan footage (`cek_visual.py`) → verifikasi jurnalis (≥3 fakta, kutipan, sumber tier 1) → paket ide (3+ varian hook, angka kunci, salah kaprah, kata kunci visual) → `cek_ide.py` (validasi + skor 0–100); portofolio 2 andalan + 1 eksplorasi; selalu belum pernah dibahas → `videos/<slug>/idea.json` | `/ide-riset [tema]` / `/ide-riset --otomatis [arahan]` | aktif |
| Raka | Penulis: naskah, judul, hook, deskripsi, tag → `script.json` | `/penulis <slug>` | aktif |
| Dara | Suara: voice-over gratis (edge-tts) + timing kata + subtitle → `vo.mp3`, `words.json`, `captions.srt` | `/suara <slug>` | aktif |
| Bima | Visual: 1–3 shot 1080x1920 per kalimat dari footage YouTube CC BY/NASA/Wikimedia Commons (Pexels/Pixabay opsional), gambar AI gratis (Cloudflare FLUX + Ken Burns), atau kartu grafis → `aset/NN-a.mp4`, `aset/manifest.json` | `/aset <slug>` | aktif |
| Kai | Editor: rakit video final (ffmpeg) — subtitle kata-per-kata, hook, punch zoom, whoosh, musik per suasana → `export/final.mp4` | `/editor <slug>` | aktif |
| Rara | QC: cek otomatis (gelap/beku/durasi/LUFS/porsi AI) + lihat frame tiap shot, tolak yang jelek → Bima ganti → Kai rakit ulang (maks 2 putaran) → `export/qc.json`, `qc_review.json` | `/qc <slug>` | aktif |
| Uli | Upload: video `export` → YouTube **private** (+ jadwal, kredit, label konten sintetis) → `export/upload.json` | `/upload <slug>` | aktif |

Setiap agent adalah satu skill Claude Code di `.claude/skills/`. Kalau diminta "panggil Steve/Nova/Raka/Dara/Bima/Kai/Rara/Uli", jalankan skill-nya.

Alur saat ini: Steve (laporan) → Nova (3 ide, status `ide`) → **Zona menyetujui di Studio Yofamo** (`disetujui`) → Raka (naskah, status `naskah`) → Dara (suara + subtitle, status `suara`) → Bima (klip, status `aset`) → Kai (video final, status `draft`) → Rara (QC + perbaikan) → **Zona menonton & menyetujui** (`export`) → Uli (upload private) → Zona menayangkan di YouTube Studio → `terbit` → Steve membaca retensi → `insights/pelajaran.md` → putaran berikutnya lebih baik.

**Jalur cepat — tombol "+ Buat video" di Studio** (`agents/produser.py`): Zona cukup klik (arahan tema opsional) → Steve memperbarui daftar video channel → Nova **memilih sendiri** 1 topik yang paling berpotensi menang dan **belum pernah dibahas** di channel (cek `cek_topik.py` + penilaian Nova; kalau ternyata duplikat, ditolak dan Nova mencari lagi), tetap 2 sumber → ide otomatis disetujui karena Zona yang menekan tombol → Raka → Dara (durasi di luar 28–45 dtk diperbaiki otomatis: percepat suara atau Raka memangkas) → Bima → Kai → Rara → video `draft` yang tetap harus ditonton dan disetujui Zona. Beberapa permintaan bisa diantrekan (`produksi/antrean.json`). Kemajuan di `produksi/<id>.json`.

## Struktur folder

- `bible/gaya-edit.json` — gaya editan Kai (font, warna subtitle, hook, zoom, musik).
- `musik/`, `sfx/` — musik latar & efek suara bebas royalti milik Zona (tidak di-commit).
- `bible/channel-bible.md` — aturan gaya & konten. **Wajib dibaca** sebelum membuat ide, naskah, atau menilai video.
- `agents/<nama>/` — script Python milik tiap agent. Jalankan dari root project.
- `insights/raw/` — data mentah statistik (JSON) dari script Steve. Jangan diedit manual.
- `insights/YYYY-Www.md` — laporan mingguan Steve (contoh `2026-W44.md`).
- `videos/<slug>/` — semua file satu video: `idea.json`, `script.json`, `vo.mp3`, `words.json`, `captions.srt`, `aset/` (`rencana.json`, `kandidat.json`, `lembar/`, `pilihan.json`, shot `NN-a.mp4`, `manifest.json`, `KREDIT.txt`, `kredit_deskripsi.txt`), `export/`.
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
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru.
- Klip hanya dari sumber berlisensi bebas: YouTube **Creative Commons (CC BY)** lewat script Bima, NASA, Wikimedia Commons (hanya PD/CC0/CC BY), Pexels, Pixabay, gambar AI, atau milik Zona. Jangan pernah mengambil video YouTube biasa, TikTok, film, atau berita.
- Hanya Uli yang boleh mengupload, hanya video berstatus `export` (sudah disetujui Zona), dan selalu **private**. Tidak ada agent yang menghapus atau mengubah video yang sudah ada di YouTube. Steve hanya **membaca** data.
- Menghapus hasil (video, log, laporan) hanya dilakukan Zona lewat panel Kelola di Studio (`pabrik.py hapus`). Agent tidak pernah menghapus.
- API key ada di `.env` (dibaca script). Jangan menampilkan isi `.env` di chat atau laporan.
- Ringkasan akhir agent: maksimal sekitar 15 baris, poin terpenting dulu. Laporan dan log dibaca Zona lewat Studio Yofamo (`studio/`).
- Jangan mengubah file di `studio/` kecuali diminta.
- Status video hanya diubah lewat `agents/pabrik.py`. Agent tidak boleh menyetujui ide sendiri; persetujuan selalu dari Zona (permintaan lewat "Buat video" dihitung sebagai persetujuan Zona untuk ide itu saja). Video final selalu ditonton & disetujui Zona.
- Hanya script di `agents/` yang boleh dijalankan. Jangan meng-install paket atau menjalankan perintah lain tanpa diminta.

## Perintah penting

```bash
python agents/steve/fetch_stats.py          # ambil statistik terbaru → insights/raw/
python agents/steve/fetch_stats.py --check  # cek API key & koneksi saja
python agents/pabrik.py list                # lihat antrean video
python agents/penulis/cek_naskah.py <slug>  # validasi naskah
python agents/suara/buat_suara.py <slug>    # Dara: vo.mp3 + words.json + captions.srt (gratis)
python agents/aset/cari_aset.py semua <slug> # Bima cepat: cari + pilih otomatis + bentuk shot
python agents/aset/cari_aset.py cari <slug>  # Bima: kandidat + lembar kontak (lalu pilihan.json → unduh)
python agents/editor/rakit.py <slug>        # Kai: rakit export/final.mp4
python agents/produser.py ["arahan tema"]  # satu klik → tim pilih topik baru → video jadi
python agents/ide/cek_topik.py "judul"      # cek topik belum pernah dibahas (--daftar: semua judul)
python agents/ide/cek_visual.py "kata"      # Nova: ada footage legal untuk topik ini? (skor 0–10)
python agents/ide/cek_ide.py <slug> --tulis # Nova: validasi sumber/kutipan/angka + skor ide 0–100
python agents/qc/periksa.py otomatis <slug> # Rara cepat: cek + ganti shot gelap/beku
python agents/upload/unggah.py login        # Uli: hubungkan YouTube (sekali)
python agents/steve/kumpul.py [--pasar]     # Steve: semua data (statistik, komentar, analitik, pasar) + analisa, tanpa kuota Claude
python agents/steve/analisa.py              # Steve: hitung KPI, pola, retensi, peluang → insights/raw/analisa-*.json/.md
python agents/tes_pabrik.py [--online]     # tes seluruh pabrik (aman, di folder sementara)
start_studio.bat                            # buka Studio Yofamo (Windows)
cd studio && npm run dev                    # sama, manual (http://127.0.0.1:3210)
```

# Yofamo Shorts Factory

Pabrik konten otomatis untuk channel YouTube **Yofamo Technology** (@yofamoo_technology):
Shorts faceless berbahasa Indonesia tentang teknologi nyata yang terasa seperti fiksi ilmiah.
Pemilik: Zona. Semua jawaban dan laporan ditulis dalam **bahasa Indonesia**.

## Tim agent

| Nama | Peran | Skill | Status |
| --- | --- | --- | --- |
| Steve | Analis: membaca statistik channel, menemukan pola topik/hook yang menang | `/steve-analis` | aktif |
| Nova | Ide & riset: 3 ide bersumber per putaran → `videos/<slug>/idea.json` | `/ide-riset [tema]` | aktif |
| Raka | Penulis: naskah, judul, hook, deskripsi, tag → `script.json` | `/penulis <slug>` | aktif |
| Dara | Suara: voice-over gratis (edge-tts) + timing kata + subtitle → `vo.mp3`, `words.json`, `captions.srt` | `/suara <slug>` | aktif |
| (belum) | Pencari aset | `/aset` | belum dibuat |
| (belum) | Editor CapCut (tulis file draft) | `/editor-capcut` | belum dibuat |
| (belum) | Review & upload | `/upload` | belum dibuat |

Setiap agent adalah satu skill Claude Code di `.claude/skills/`. Kalau diminta "panggil Steve/Nova/Raka/Dara", jalankan skill-nya.

Alur saat ini: Steve (laporan) → Nova (3 ide, status `ide`) → **Zona menyetujui di Studio Yofamo** (`disetujui`) → Raka (naskah, status `naskah`) → Dara (suara + subtitle, status `suara`) → Zona mengedit di CapCut dan upload manual.

## Struktur folder

- `bible/channel-bible.md` — aturan gaya & konten. **Wajib dibaca** sebelum membuat ide, naskah, atau menilai video.
- `agents/<nama>/` — script Python milik tiap agent. Jalankan dari root project.
- `insights/raw/` — data mentah statistik (JSON) dari script Steve. Jangan diedit manual.
- `insights/YYYY-Www.md` — laporan mingguan Steve (contoh `2026-W44.md`).
- `videos/<slug>/` — semua file satu video: `idea.json`, `script.json`, `vo.mp3`, `words.json`, `captions.srt`, `aset/`, `manifest.json`, `export/`.
- `state.db` — SQLite antrean & status tiap video. Diakses hanya lewat `python agents/pabrik.py`.
- `studio/` — Studio Yofamo: kantor virtual lokal (Next.js + TypeScript + Tailwind). Membaca file project dan menjalankan agent lewat `claude -p`.
- `logs/` — log setiap tugas yang dijalankan.

## Aturan kerja

- Angka selalu berasal dari file di `insights/raw/`, tidak pernah dikarang. Kalau data kurang, tulis "data belum cukup".
- Satu video sedikit (< 5) bukan pola. Sebut sebagai "dugaan" sampai ada minimal 5 video pendukung.
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru.
- Jangan mengupload, menghapus, atau mengubah apa pun di YouTube. Steve hanya **membaca** data publik.
- API key ada di `.env` (dibaca script). Jangan menampilkan isi `.env` di chat atau laporan.
- Ringkasan akhir agent: maksimal sekitar 15 baris, poin terpenting dulu. Laporan dan log dibaca Zona lewat Studio Yofamo (`studio/`).
- Jangan mengubah file di `studio/` kecuali diminta.
- Status video hanya diubah lewat `agents/pabrik.py`. Agent tidak boleh menyetujui ide sendiri; persetujuan selalu dari Zona.
- Hanya script di `agents/` yang boleh dijalankan. Jangan meng-install paket atau menjalankan perintah lain tanpa diminta.

## Perintah penting

```bash
python agents/steve/fetch_stats.py          # ambil statistik terbaru → insights/raw/
python agents/steve/fetch_stats.py --check  # cek API key & koneksi saja
python agents/pabrik.py list                # lihat antrean video
python agents/penulis/cek_naskah.py <slug>  # validasi naskah
python agents/suara/buat_suara.py <slug>    # Dara: vo.mp3 + words.json + captions.srt (gratis)
start_studio.bat                            # buka Studio Yofamo (Windows)
cd studio && npm run dev                    # sama, manual (http://127.0.0.1:3210)
```

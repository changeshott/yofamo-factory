# Yofamo Shorts Factory

Pabrik konten otomatis untuk channel YouTube **Yofamo Technology** (@yofamoo_technology):
Shorts faceless berbahasa Indonesia tentang teknologi nyata yang terasa seperti fiksi ilmiah.
Pemilik: Zona. Semua jawaban dan laporan ditulis dalam **bahasa Indonesia**.

## Tim agent

| Nama | Peran | Skill | Status |
| --- | --- | --- | --- |
| Steve | Analis: membaca statistik channel, menemukan pola topik/hook yang menang | `/steve-analis` | aktif |
| (belum) | Ide & riset | `/ide-riset` | belum dibuat |
| (belum) | Penulis naskah + metadata | `/penulis` | belum dibuat |
| (belum) | Suara (TTS + timing) | `/suara` | belum dibuat |
| (belum) | Pencari aset | `/aset` | belum dibuat |
| (belum) | Editor CapCut (tulis file draft) | `/editor-capcut` | belum dibuat |
| (belum) | Review & upload | `/upload` | belum dibuat |

Setiap agent adalah satu skill Claude Code di `.claude/skills/`. Kalau diminta "panggil Steve", jalankan skill `steve-analis`.

## Struktur folder

- `bible/channel-bible.md` — aturan gaya & konten. **Wajib dibaca** sebelum membuat ide, naskah, atau menilai video.
- `agents/<nama>/` — script Python milik tiap agent. Jalankan dari root project.
- `insights/raw/` — data mentah statistik (JSON) dari script Steve. Jangan diedit manual.
- `insights/YYYY-Www.md` — laporan mingguan Steve (contoh `2026-W44.md`).
- `videos/<slug>/` — semua file satu video: `idea.json`, `script.json`, `vo.mp3`, `words.json`, `aset/`, `manifest.json`, `export/`.
- `state.db` — SQLite status tiap video (dibuat nanti oleh agent ide).
- `dashboard/` — halaman kontrol lokal (server Python + index.html).
- `logs/` — log setiap tugas yang dijalankan.

## Aturan kerja

- Angka selalu berasal dari file di `insights/raw/`, tidak pernah dikarang. Kalau data kurang, tulis "data belum cukup".
- Satu video sedikit (< 5) bukan pola. Sebut sebagai "dugaan" sampai ada minimal 5 video pendukung.
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru.
- Jangan mengupload, menghapus, atau mengubah apa pun di YouTube. Steve hanya **membaca** data publik.
- API key ada di `.env` (dibaca script). Jangan menampilkan isi `.env` di chat atau laporan.
- Ringkasan akhir agent: maksimal sekitar 15 baris, poin terpenting dulu. Laporan dan log dibaca Zona lewat Yofamo Control Room (`dashboard/`).
- Jangan mengubah file di `dashboard/` kecuali diminta.
- Hanya script di `agents/` yang boleh dijalankan. Jangan meng-install paket atau menjalankan perintah lain tanpa diminta.

## Perintah penting

```bash
python agents/steve/fetch_stats.py          # ambil statistik terbaru → insights/raw/
python agents/steve/fetch_stats.py --check  # cek API key & koneksi saja
python dashboard/server.py                  # buka Yofamo Control Room di browser
```

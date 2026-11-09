# Yofamo Shorts Factory

Pabrik konten otomatis untuk channel YouTube **Yofamo Technology** (@yofamoo_technology): Shorts faceless + video panjang
dokumenter berbahasa Indonesia tentang teknologi nyata. Pemilik: Zona. Semua jawaban dan laporan ditulis dalam **bahasa Indonesia**.

## Otak project (baca dulu, hemat token)

File ini sengaja ringkas karena dimuat di setiap panggilan Claude. Rincian alur, keputusan, dan progres ada di `otak/`:
- **Sesi coding/perbaikan pabrik**: baca `otak/README.md` → `otak/PETA.md` → `otak/progres.md` → `otak/keputusan.md`, lalu satu
  file alur yang relevan dan `otak/indeks-kode.md` untuk menemukan file. Jangan menjelajah folder dari awal.
- **Agent produksi** (menjalankan skill): ikuti SKILL.md-mu; tidak perlu membaca `otak/`.
- **Setiap kali mengubah kode, skill, atau aturan**: perbarui `otak/` (tabel "Kapan diperbarui" di `otak/README.md`), jalankan
  `python agents/otak.py perbarui` lalu `python agents/otak.py cek` (harus lolos) sebelum commit.

## Tim agent (detail: `otak/PETA.md`)

| Shorts | Skill | Video panjang | Skill / script |
| --- | --- | --- | --- |
| Steve — analis data | `/steve-analis` | Bayu — ide & riset | `/panjang-ide` |
| Nova — ide & riset | `/ide-riset` | Citra — naskah adegan | `/panjang-naskah` |
| Raka — naskah | `/penulis` | Gilang — suara | `agents/panjang/suara_panjang.py` |
| Dara — suara | `/suara` | Laras — footage 16:9 | `agents/panjang/footage_panjang.py` |
| Bima — footage | `/aset` | Tio — render adegan | `agents/panjang/dokumenter.py` |
| Mila — thumbnail | `/thumbnail` | Wulan — rakit & QC | `agents/panjang/rakit_panjang.py`, `/qc-panjang` |
| Kai — editor | `/editor` | | |
| Rara — QC | `/qc` | | |
| Uli — upload & autopilot | `/upload` | | |

Kalau diminta "panggil <nama>", jalankan skill-nya.

## Aturan kerja

- Angka selalu berasal dari file di `insights/raw/`, tidak pernah dikarang. Kalau data kurang, tulis "data belum cukup".
- Satu video sedikit (< 5) bukan pola. Sebut sebagai "dugaan" sampai ada minimal 5 video pendukung.
- Jangan pernah menghapus file di `insights/` atau `videos/`. Tulis file baru. Satu-satunya pengecualian: `agents/bersih.py` (permintaan Zona, `bible/penyimpanan.json`) otomatis menghapus file besar video yang **sudah diupload** (final.mp4, render, shot, suara) plus cache unduhan lama & file sementara; data kecil (naskah, timing, manifest, info, upload, QC) tetap disimpan.
- Klip hanya dari sumber berlisensi bebas: YouTube **Creative Commons (CC BY)** lewat script Bima, NASA, Wikimedia Commons (hanya PD/CC0/CC BY), Pexels, Pixabay, gambar AI, atau milik Zona. Jangan pernah mengambil video YouTube biasa, TikTok, film, berita, atau lagu dari video YouTube biasa.
- Hanya Uli yang boleh mengupload, hanya video berstatus `export`, dan selalu **private** (boleh dengan jadwal tayang `publishAt`, sehingga YouTube menayangkannya sendiri). Status `export` berasal dari persetujuan Zona, atau dari autopilot yang dinyalakan Zona (Shorts: hanya video buatan autopilot yang lolos Rara dengan skor ≥ `skor_qc_min`; video panjang: hanya video buatan autopilot video panjang yang lolos QC Wulan dengan skor ≥ `panjang.skor_qc_min`). Tidak ada agent yang menghapus atau mengubah video yang sudah ada di YouTube. Steve hanya **membaca** data.
- Deskripsi YouTube tanpa link sumber. Kredit footage CC BY tetap dicantumkan singkat (judul, pembuat, lisensi) tanpa link; link lengkap tersimpan di `KREDIT.txt` folder aset video.
- Menghapus hasil (video, log, laporan) hanya dilakukan Zona lewat panel Kelola di Studio (`pabrik.py hapus`). Agent tidak pernah menghapus, kecuali bersih-bersih otomatis `bersih.py` di atas.
- API key ada di `.env` (dibaca script). Jangan menampilkan isi `.env` di chat atau laporan. `rahasia/` (OAuth YouTube) tidak pernah di-commit, dibaca, atau ditampilkan agent.
- Ringkasan akhir agent: maksimal sekitar 15 baris, poin terpenting dulu. Laporan dan log dibaca Zona lewat Studio Yofamo (`studio/`).
- Jangan mengubah file di `studio/` kecuali diminta.
- Status video hanya diubah lewat `agents/pabrik.py` (Shorts) atau `agents/panjang/status.py` (video panjang). Agent tidak boleh menyetujui ide sendiri; persetujuan selalu dari Zona (permintaan lewat "Buat video" dihitung sebagai persetujuan Zona untuk ide itu saja). Video final ditonton & disetujui Zona, kecuali saat autopilot aktif (lihat aturan upload di atas).
- Hanya script di `agents/` yang boleh dijalankan. Jangan meng-install paket atau menjalankan perintah lain tanpa diminta.
- `bible/autopilot.json` berisi pengaturan lokal Zona di laptop: jangan di-commit atau ditimpa.

## Perintah penting (daftar lengkap: `otak/indeks-kode.md`)

```bash
python agents/produser.py ["arahan tema"]                 # Shorts: satu klik → video draft
python agents/panjang/produser_panjang.py ["tema"]        # video panjang dokumenter (--lanjut <slug>, --uji)
python agents/autopilot.py status|nyala|mati|jalan        # autopilot Shorts
python agents/panjang/autopilot_panjang.py status|nyala|mati|jalan   # autopilot video panjang
python agents/pabrik.py list                              # antrean & status Shorts
python agents/steve/kumpul.py [--pasar]                   # Steve: semua data + analisa, tanpa kuota Claude
python agents/pemakaian.py                                # token Claude per video
python agents/otak.py perbarui | cek                      # otak project: perbarui / periksa akurasi
python agents/tes_pabrik.py [--online]                    # tes seluruh pabrik (aman, folder sementara)
start_studio.bat                                          # Studio Yofamo (http://127.0.0.1:3210)
```

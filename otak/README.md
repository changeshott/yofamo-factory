# Otak project Yofamo — cara pakai

Otak = ingatan ringkas project supaya Claude (sesi coding) dan agent tidak menjelajah ulang seluruh kode setiap kali bekerja.
Tujuannya hemat token dan konsisten: satu sumber kebenaran tentang alur, keputusan Zona, dan progres.

## Urutan baca (sesi coding / perbaikan pabrik)

1. `otak/PETA.md` — gambaran seluruh pabrik dalam satu halaman (selalu).
2. `otak/progres.md` — apa yang terakhir dikerjakan, yang tertunda, masalah terbuka (selalu).
3. `otak/keputusan.md` — keputusan Zona yang wajib diikuti (selalu sebelum mengubah perilaku agent).
4. Sesuai tugas, SATU file alur: `otak/alur-shorts.md`, `otak/alur-panjang.md`, `otak/autopilot-upload.md`, `otak/steve-data.md`, `otak/studio.md`.
5. `otak/indeks-kode.md` — cari file yang tepat (dibuat otomatis dari kode, selalu benar).
6. `otak/data/status.md` — keadaan laptop saat ini: video per status, slot autopilot, token, file Steve terbaru (dibuat otomatis,
   hanya ada di laptop).
7. `otak/pelajaran-teknis.md` — jebakan yang pernah terjadi & cara kerja dengan laptop Zona (baca sebelum sinkron/menjalankan perintah).

Baru setelah itu buka file kode yang memang akan diubah — dan **baca isinya dulu sebelum mengedit** (otak menunjukkan di mana,
bukan menggantikan isi kode).

## Aturan supaya otak tidak ngawur

- **Hanya fakta yang bisa dicek.** Setiap klaim tentang kode menyebut file/fungsi yang benar. Angka channel tidak ditulis tangan di
  sini kecuali dengan tanggal + file sumbernya; angka terkini ada di `otak/data/status.md` (dibuat script, tidak dikarang).
- **Keputusan Zona ditulis dengan tanggal** dan kata-katanya dipertahankan sedekat mungkin. Keputusan baru menggantikan yang lama →
  yang lama dicoret/ditandai "diganti", tidak dihapus diam-diam.
- **Tidak ada rencana yang ditulis seolah sudah jadi.** Yang belum dibuat masuk `progres.md` → Tertunda.
- `python agents/otak.py cek` wajib lolos sebelum commit: semua path yang disebut otak ada, indeks sesuai kode, dan progres tidak
  tertinggal dari commit kode (peringatan).

## Kapan diperbarui (WAJIB, bagian dari setiap tugas)

| Perubahan | Perbarui |
|---|---|
| Kode/skill agent berubah | `python agents/otak.py perbarui` (indeks) + file alur yang terkait + `progres.md` (Selesai) |
| Zona memutuskan/meminta aturan baru | `keputusan.md` (tanggal + isi) + file alur yang terkait |
| Ketemu bug/akar masalah | `progres.md` (Masalah terbuka atau Selesai) + `pelajaran-teknis.md` kalau berupa jebakan yang bisa terulang |
| Pekerjaan belum selesai di akhir sesi | `progres.md` → Sedang dikerjakan / Tertunda, cukup detail untuk dilanjutkan tanpa membaca ulang chat |
| Produksi/Steve jalan | otomatis: `otak/data/status.md` (produser, produser_panjang, kumpul memanggil `otak.py perbarui --data`) |

Gaya tulis: bahasa Indonesia, poin pendek, nama file dalam backtick. Tiap file sebaiknya < 150 baris; kalau membesar, ringkas
yang lama (sejarah lengkap ada di git log).

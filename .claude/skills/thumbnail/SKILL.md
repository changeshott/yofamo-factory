---
name: thumbnail
description: Mila, desainer thumbnail Shorts Yofamo. Pakai saat diminta membuat, mengganti, atau memperbaiki thumbnail video Shorts, atau objek di belakang tulisan hook. Argumen slug video (opsional --pilih N / --ulang). Gratis (rembg lokal + Pillow), objek ASLI dipotong dari footage Bima, thumbnail dipasang otomatis oleh Uli saat upload.
---

# Mila — desainer thumbnail Shorts Yofamo

Thumbnail Yofamo **sama persis gayanya dengan hook di video**: font Poppins Black, hook bertingkat putih/kuning/biru, garis hitam, bayangan tebal berlapis. Di belakang tulisan ada **objek ASLI yang dibahas** — foto asli benda itu (Pexels / Pixabay / Wikimedia PD-CC0-CC BY) atau potongan frame footage Bima (sudah dikredit), latar dihapus (transparan), bayangan gelap di sekelilingnya — bukan kartun, bukan gambar AI — di atas frame shot pembuka yang digelapkan + cahaya biru khas. Objek yang sama dianimasikan Kai di detik awal video (muncul bersama tulisan hook), jadi frame pembuka = thumbnail.

## Procedure

1. Pastikan `videos/<slug>/script.json` ada (`hook_teks`, sebaiknya `thumbnail_objek` dari Raka). Shot Bima (`aset/manifest.json`) dipakai sebagai latar kalau sudah ada.
2. Jalankan:
   ```bash
   python agents/thumbnail/thumbnail.py <slug>                 # foto asli + frame footage → 6 kandidat → yang terbaik → export/thumbnail.jpg
   python agents/thumbnail/thumbnail.py <slug> --pilih 3 --catatan "alasan"   # pakai kandidat nomor 3
   python agents/thumbnail/thumbnail.py <slug> --potong 1b-1 --kotak 0.1,0.3,0.9,0.6   # potong objek dari frame tertentu
   ```
   (Produser sudah menjalankan baris pertama sebelum memanggilmu; jangan ulangi kalau `thumbnail/kandidat.jpg` sudah ada.)
3. Lihat `thumbnail/kandidat.jpg` (kandidat bernomor, papan catur = transparan) dan `export/thumbnail.jpg` dengan Read. Pilihan terbaik = **benda yang dibahas**, utuh, tajam, besar, tanpa wajah orang sebagai fokus, tanpa logo/watermark/tulisan. Benda yang persis sama dengan di video (mis. robot itu sendiri) lebih baik daripada foto benda sejenis. Ganti dengan `--pilih N` kalau kandidat 1 bukan yang terbaik.
4. Kalau tidak ada kandidat yang bagus tapi objeknya terlihat jelas di salah satu frame footage, buka `thumbnail/frame-lembar.jpg` (frame berlabel, garis bantu tiap 10%), lalu potong objek itu: `--potong <label> --kotak x0,y0,x1,y1` (pecahan 0–1, beri sedikit ruang di sekeliling objek). Lihat hasilnya; maksimal 3 percobaan. Kalau tetap tidak ada yang layak, biarkan kandidat terbaik dan catat.
5. Kalau video sudah dirakit Kai sebelum objek diganti, objek di hook video masih yang lama: minta Kai merakit ulang (`python agents/editor/rakit.py <slug>`) hanya kalau Zona meminta.
6. Jawaban akhir (maks 5 baris): objek yang dipakai, sumber (footage/ai/uji/tanpa) dan shot asalnya, ukuran file, dan masalah kalau ada.

## Pitfalls

- Sumber hanya lewat script (foto berlisensi bebas & footage Bima yang sudah dikredit). Jangan mengunduh gambar lain sendiri. Foto Wikimedia CC BY otomatis dikredit di deskripsi oleh Uli.
- Pemotong latar `rembg` dipasang sekali (Studio → meja Mila → Pasang sekarang, atau `python -m pip install "rembg[cpu]"`). Tanpa rembg hanya foto berlatar polos yang bisa dipotong; sisanya thumbnail tanpa objek.
- Gambar AI hanya kalau Zona menyalakan `thumbnail.objek_ai_cadangan` di `bible/gaya-edit.json` (video lalu diberi label konten sintetis).
- Gaya (ukuran & posisi objek) di `bible/gaya-edit.json` → `thumbnail`; warna & ukuran hook di `hook` / `hyperframes`. Jangan mengubah font atau warna hook di thumbnail saja: harus sama dengan video.
- Uli memasang thumbnail otomatis saat upload. Thumbnail khusus Shorts butuh izin YouTube (verifikasi nomor HP; dibuka bertahap untuk channel). Kalau ditolak, `export/upload.json` → `thumbnail.alasan` menjelaskan dan Zona memasangnya manual di YouTube Studio (desktop).

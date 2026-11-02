# Bible video panjang Yofamo (Ruang Animasi)

Video YouTube 5–8 menit, 16:9, **full animasi gaya lukis-komik hibrida** (dari prompt gaya Zona): bentuk 3D dipahat +
tekstur lukis tangan, garis tinta tebal, bayangan dilukis, halftone & cipratan cat pink/cyan/kuning, highlight sapuan kuas,
latar studio pink. Kamera mulus 24 fps, karakter & huruf "on twos". Membahas satu teknologi nyata sampai tuntas: apa itu, kenapa penting, cara kerjanya, bukti/angka, dampak, masa depan.

## Struktur (bab = chapter YouTube)
1. **Pembuka (0:00–0:30)** — dibuka host dengan ciri khas "Tau nggak, …" + janji isi video (apa yang akan penonton pahami di akhir). Tanpa basa-basi, tanpa "halo guys".
2. **Bab 1–4** — tiap bab diawali kartu `judul_bab`, isi 4–10 adegan. Urutan wajar: Apa itu → Cara kerjanya → Bukti & angka → Dampak/masa depan.
3. **Penutup** — rangkuman 2–3 poin, pertanyaan untuk komentar, ajakan subscribe singkat (adegan `penutup`).

## Aturan adegan
- 1 adegan = 1 ide, narasi 1–4 kalimat (≤ 55 kata, ±8–22 detik). Ganti adegan sesering mungkin; jangan dua adegan host berturut-turut lebih dari 2.
- Campuran: host ≤ 35%, ilustrasi + diagram ≥ 50%. Setiap penjelasan cara kerja WAJIB pakai diagram (`bagian`, `alur`, `perbandingan`, `angka`, `daftar`, `timeline`).
- Gambar harus sesuai yang sedang diucapkan: prompt ilustrasi menyebut objek/aksi spesifik dari kalimatnya, bukan suasana umum.
- Butir diagram muncul berurutan mengikuti kalimat: jumlah butir sebaiknya = jumlah kalimat narasi adegan itu.
- Angka & klaim hanya dari `ide.json` (bersumber). Tidak ada fakta karangan.
- Bahasa: Indonesia santai-cerdas, kalimat pendek, sapaan "kamu". Istilah teknis dijelaskan dengan analogi sehari-hari.
- Gambar AI tidak boleh berisi orang sungguhan, tokoh terkenal, logo, merek, atau tulisan.

## Retensi
- Tiap 45–60 detik ada "kait" baru: pertanyaan, angka mengejutkan, atau janji ("tapi bagian paling gila ada di bab 3").
- Kata kunci penting diberi `kata_kunci` supaya muncul di layar tepat saat diucapkan.
- Judul jujur & bikin penasaran (≤ 70 karakter), thumbnail: host Yofa berekspresi + objek dramatis + 2–4 kata besar.

## Gaya gambar (prompt ilustrasi)
- `gambar` cukup menyebut ISI (objek, aksi, sudut/suasana) dalam bahasa Inggris; gaya lukis-komik ditambahkan otomatis oleh Laras
  dari `bible/gaya-animasi.json` + gambar acuan gaya. Jangan menulis nama gaya, nama film, studio, atau karakter terkenal.
- Ilustrasi = satu adegan jelas dengan objek utama besar & dramatis (bukan kolase). Objek diagram `bagian` = satu benda utuh.
- Host Yofa tidak digambar di ilustrasi (dia ditempel sebagai karakter animasi); jangan minta orang di prompt kecuali tangan/siluet anonim.

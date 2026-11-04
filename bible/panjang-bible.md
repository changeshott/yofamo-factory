# Bible video panjang Yofamo (gaya dokumenter modern)

Video YouTube **5–12 menit**, 16:9, gaya **dokumenter modern** (referensi "Video 1" Zona): sebagian besar **footage asli** teknologi
yang dibahas (YouTube CC BY, NASA, Wikimedia PD/CC0/CC BY, Pexels, Pixabay) — **tanpa teks, subtitle, atau watermark di dalam videonya**
(dicek otomatis dengan pendeteksi teks) — diselingi **motion graphic** tenang & elegan: kertas abu-abu terang, huruf serif satu-dua kata,
foto hitam-putih dengan benda berwarna, benda asli melayang berbayang lembut, mockup HP/TV, butiran film + garis VHS tipis.
Membahas satu teknologi nyata sampai tuntas: apa itu, kenapa penting, cara kerjanya, bukti/angka, dampak, masa depan.
Bukan gaya kayu/kuning vintage, bukan kartun.

## Struktur (bab = chapter YouTube)
1. **Pembuka (0:00–0:30)** — adegan `pembuka`: footage + kata hook serif, narasi diawali ciri khas "Tau nggak, …" + janji isi video.
   Tanpa basa-basi, tanpa "halo guys".
2. **Bab 1–5** — tiap bab diawali kartu `judul_bab` (minimal 3). Urutan wajar: Apa itu → Cara kerjanya → Bukti & angka → Dampak/masa depan.
3. **Penutup** — adegan `penutup`: pertanyaan untuk komentar + ajakan subscribe singkat.

## Aturan adegan
- **Footage ≥ 50% narasi.** Motion graphic hanya saat benar-benar membantu: `cara_kerja`, `angka`, `banding`, `garis_waktu`, `objek`, `kata`,
  `hp`/`tv` — minimal 4 per video, tidak lebih dari 2 berturut-turut.
- 1 adegan = 1 ide. Narasi footage ≤ 45 kata, motion graphic ≤ 35–60 kata. Ganti shot tiap ±4–5 detik (otomatis).
- Footage harus memperlihatkan teknologi yang SEDANG diucapkan: `kata_kunci_visual` = 1–3 kata kunci Inggris benda/aksi yang terlihat
  (cek `agents/ide/cek_visual.py`). Hindari kata kunci yang cenderung menghasilkan presentasi, slide, atau berita (banyak tulisan).
- Angka & klaim hanya dari `ide.json` (bersumber). Tidak ada fakta karangan.
- Bahasa: Indonesia santai-cerdas, kalimat pendek, sapaan "kamu". Istilah teknis dijelaskan dengan analogi sehari-hari.
- Subtitle kecil di tengah bawah hanya saat footage (disembunyikan saat motion graphic).

## Retensi
- Tiap 45–60 detik ada "kait" baru: pertanyaan, angka mengejutkan, atau janji ("tapi bagian paling gila ada di bab 3").
- Judul jujur & bikin penasaran (≤ 70 karakter). Thumbnail: frame footage hitam-putih gelap + **benda asli berwarna** berbayang tebal
  + 2–4 kata besar (`thumbnail.teks`, `thumbnail.objek` benda fisik Inggris).

## Objek & foto
- Benda di motion graphic & thumbnail diambil dari **foto asli** (Pexels/Pixabay/Wikimedia PD/CC0/CC BY) atau frame footage, latar dihapus
  (rembg). Bukan gambar AI. Kredit CC BY dicantumkan singkat di deskripsi (tanpa link).

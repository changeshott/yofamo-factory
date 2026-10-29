# Channel Bible — Yofamo Technology

Dibaca oleh semua agent. Kalau ada aturan yang berubah, ubah di sini saja.

## Identitas

- **Niche:** teknologi nyata yang terdengar seperti fiksi ilmiah.
- **Format:** YouTube Shorts faceless, umumnya 30–45 detik (sesuai kebutuhan topik, maksimal ±58 detik), bahasa Indonesia santai.
- **Janji ke penonton:** "selangkah lebih maju soal teknologi dunia" — kaget dulu, paham kemudian.

## Topik

Prioritaskan teknologi yang **menyentuh tubuh dan keseharian**: makanan, pakaian, kesehatan, rumah, game, HP.

Data awal (Okt 2026, 21 Shorts) yang mendukung aturan ini:

| Short | Views |
| --- | --- |
| Baju ganti ribuan motif | 7,6 rb |
| Steak dari printer 3D | 6,4 rb |
| Print jantung (printer 3D medis) | 4,9 rb |
| Baju VR yang bikin sakit | 4,1 rb |
| Jurassic Park jadi nyata | 3,9 rb |

Hindari atau batasi:

- Topik abstrak tanpa visual kuat (baca pikiran, nonton mimpi, telepati) — semuanya ±1–1,3 rb.
- Hook yang hanya mengandalkan nama superhero (Iron Man, Spider-Man) — ±1,6 rb.

## Struktur naskah

1. **Hook (0–3 detik):** **selalu diawali "Tau nggak,"** (ciri khas Yofamo, pengganti "halo guys"), lalu langsung klaim kaget/kontras ≤ 12 kata. Contoh: "Tau nggak, robot ini bisa ngerasain sakit?"
2. **Konteks:** apa itu & siapa pembuatnya, status jujur (1 kalimat).
3. **Cara kerja:** singkat, pakai analogi sehari-hari (1–3 kalimat).
4. **Wow:** fakta/angka paling mengejutkan (wajib), membayar *open loop* dari awal.
5. **Bukti/dampak** (opsional): luruskan salah kaprah atau "artinya buat kamu…".
6. **Penutup tuntas:** loop ke kalimat pertama, pertanyaan opini yang spesifik, atau kesimpulan "jadi…". Tidak boleh menggantung, tidak "part 2", tidak ajakan subscribe (ajakan follow ditampilkan Kai di layar penutup ±1,2 detik).

Durasi mengikuti kebutuhan cerita (`target_durasi` 25–58 detik): sederhana 28–34, standar 35–42, kompleks 43–52. Jumlah kata = target × 2,3 (suara Ardi +15%). Video pertama: 101 kata = 46,8 detik, kepanjangan untuk topik standar.

## Judul

- Klaim dalam HURUF KAPITAL + pertanyaan kaget, maksimal ±70 karakter.
- Selalu diakhiri `#Shorts #Teknologi`.
- Contoh gaya: `SATU BAJU BISA GANTI RIBUAN MOTIF! Teknologi Pakaian Paling Gila #Shorts #Teknologi`

## Fakta & sumber

- Setiap klaim harus punya sumber di `idea.json`. Tanpa sumber, klaim dibuang.
- Bedakan "sudah dijual" vs "masih prototipe/riset".

## Visual

- Ganti visual tiap 1,5–3 detik.
- Tanpa watermark atau logo channel lain.
- Sumber visual: footage YouTube Creative Commons (CC BY), NASA, Wikimedia Commons (PD/CC0/CC BY), Pexels/Pixabay bila ada key; gambar AI (FLUX via Cloudflare, digerakkan halus); kartu grafis buatan sendiri. Lisensi dicatat di `aset/manifest.json`, kredit CC BY masuk deskripsi.
- Ritme: maksimal 2 shot footage berturut-turut, lalu selingan gambar AI bergerak atau animasi grafis. Suara asli klip tidak pernah dipakai; hanya voice-over Dara.
- Rekaman sendiri taruh di `milik-saya/` dengan nama file deskriptif; selalu diprioritaskan.
- Campuran ideal: ±60% footage, ±25% gambar AI, ±15% grafis (angka/pertanyaan). Hook selalu footage terkuat.
- Video dengan gambar AI realistis: centang "konten diubah/sintetis" saat upload.
- Gaya editan (font, caption, hook, zoom, BGM) diatur di `bible/gaya-edit.json` dan dirakit Kai.

## Suara

- `id-ID-ArdiNeural`, kecepatan +15%. Durasi di luar target naskah (−10%/+12%) diperbaiki otomatis: kecepatan suara disesuaikan, atau Raka memangkas.

# Pelajaran teknis & cara kerja dengan laptop Zona

## Lingkungan

- Sesi Claude coding biasanya di **container cloud** (clone di `/home/claude/push`), push ke GitHub `changeshott/yofamo-factory`.
  Pabrik sungguhan berjalan di **laptop Windows** Zona (`C:\Users\zonaf\Downloads\yofamo-factory`); dari sandbox Linux laptop
  terlihat di `~/mnt/yofamo-factory` (alat device). Python Windows yang benar ada di `YOFAMO_PYTHON` (`agents/pakai_python.py`).
- Sandbox Linux laptop & container **tidak bisa** mengakses kebanyakan situs (RSS, YouTube) → tes jaringan hanya bermakna di Windows.
- Data produksi (`state.db`, `produksi/`, `insights/raw/`, `panjang/`, `videos/`) hanya ada di laptop. Baca lewat alat device,
  mulai dari `otak/data/status.md`.

## Sinkron kode ke laptop (cara yang terbukti)

1. Commit + push di container. 2. `git bundle create <nama-unik>.bundle <commit_laptop>..HEAD` (nama bundle selalu UNIK — bundle
   dengan nama sama pernah terbaca versi lama). 3. Kirim ke laptop (folder `produksi/`), lalu di laptop:
   `timeout 120 git fetch produksi/<bundle> HEAD && timeout 120 git merge --ff-only FETCH_HEAD`.
- Merge yang menyentuh file yang perlu dihapus/diganti gagal dengan "unlink: Operation not permitted" → minta izin hapus untuk folder
  project (izin berlaku per sesi), hapus `.git/index.lock` / `maintenance.lock` / `tmp_pack*` sisa, ulangi.
- **`bible/autopilot.json` di laptop punya perubahan lokal Zona — jangan pernah di-commit/ditimpa.** Perubahan pengaturan autopilot
  hanya ditulis langsung ke file laptop.
- Selalu bungkus git di laptop dengan `timeout`.

## Jebakan yang pernah terjadi

- `pgrep -f`/`pkill -f` mencocokkan dirinya sendiri (dan pernah membunuh shell sendiri) → pakai pola `[x]` (mis. `pgrep -f "[p]rodu"`).
- Proses latar dengan `&` di shell dihentikan → pakai mode latar alat, bukan `&`.
- Regex slug `[a-z0-9-]{8,80}` cocok dengan argumen "--otomatis" → slug harus diawali huruf/angka.
- Relevansi footage yang menghitung kata kueri membuat semua hasil terlihat relevan → nilai dari judul kandidat.
- Adegan `kata` tanpa `teks_layar` dirender sebagai layar putih kosong → cadangan 5 kata narasi.
- Balapan: Wulan merender ulang saat Uli mengunggah, lalu `bersih.py` menghapus adegan → video panjang yang sudah diupload tidak boleh
  dirender ulang (`jaga_belum_terbit`).
- Tes `agents/tes_pabrik.py` memakai fixture (judul kandidat tidak cocok kueri) — mengubah rumus relevansi bisa menggagalkan tes Bima;
  jalankan tes sebelum dan sesudah untuk membandingkan.

## Kebiasaan hemat token untuk Claude

- Baca `otak/` dulu (urutan di `otak/README.md`), lalu hanya file yang akan diubah. Pakai `grep -n` / baca sebagian, bukan seluruh file besar.
- Jangan memuat ulang file yang sudah dibaca di sesi yang sama kecuali berubah.
- Hasil perintah panjang: saring (`tail`, `grep`) sebelum masuk ke percakapan.

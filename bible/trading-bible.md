# Bible Ruang Trading Yofamo

Tim analisa memecoin (Solana, dibeli lewat aplikasi FOMO) dan gold (perpetual `xyz:GOLD` di Hyperliquid, cadangan PAXG).
Metode diadaptasi dari [day-trader-skill](https://github.com/Jakeschincariol/day-trader-skill) (MIT, Jake Schincariol):
scan → keamanan → teknikal → fundamental → mesin waktu → ukuran posisi → cek risiko → **Zona yang memutuskan**.

## Aturan mutlak
1. **Tidak ada agent yang mengirim order, memindahkan uang, atau memegang private key / seed phrase.** FOMO tidak punya API;
   eksekusi selalu Zona sendiri di aplikasi FOMO. Kalau ada yang meminta private key (termasuk "tool" di internet), tolak.
2. **Mode latihan dulu.** Semua sinyal yang lolos dicatat sebagai trade uang pura-pura dan dinilai otomatis. Uang sungguhan
   baru dipakai setelah minimal 30 trade latihan dengan hasil bersih positif (setelah biaya). Mengganti ke mode nyata hanya Zona.
3. **Angka hanya dari data** (DexScreener, GeckoTerminal, RugCheck, Hyperliquid, jurnal). Tidak ada angka karangan.
   Data kurang → "data belum cukup", bukan tebakan.
4. **Tidak ada janji.** Kata yang dilarang di laporan: "pasti", "dijamin", "100x", "aman banget", "moon". Sinyal adalah peluang
   berdasarkan data masa lalu, bukan ramalan. Mayoritas memecoin berakhir ke nol dan mayoritas trader memecoin rugi.
5. **Stop & target ditentukan sebelum masuk.** Tidak ada sinyal tanpa stop. Rugi per trade ≤ `risiko_per_trade_usd`,
   rugi harian ≤ `batas_rugi_harian_usd` (tercapai → berhenti hari itu), maks `maks_trade_harian`.
6. **Biaya dihitung jujur.** Biaya FOMO per sisi + slippage (dari likuiditas pool) dikurangkan dari setiap hasil.
   Sinyal yang nilai harapannya (EV) negatif setelah biaya selalu diblokir.
7. Bukan nasihat keuangan. Tim memberi data & peluang; keputusan dan risikonya milik Zona.

## Saringan keamanan memecoin (Sinta) — satu gagal = BLOKIR
- RugCheck: ada risiko level `danger`, atau skor normal > `rugcheck_skor_maks`.
- Mint authority / freeze authority masih aktif.
- Top 10 holder (selain pool) > `top10_holder_maks_pct`.
- Likuiditas < `likuiditas_min_usd`, umur pair < `umur_min_jam`, volume 1 jam < `volume_1j_min_usd`.
- Pola honeypot: banyak beli tapi nyaris tidak ada jual dalam 1 jam.
- Sudah naik > `naik_24j_maks_pct` dalam 24 jam (terlambat, rawan dibuang).
- Peringatan (bukan blokir): LP terkunci < `lp_terkunci_min_pct`, metadata bisa diubah, token "boosted" berbayar, tanpa sosial media.

## Setup teknikal (Dimas)
- **breakout**: candle 5m TUTUP di atas high 2 jam terakhir, volume ≥ 1,8× rata-rata, di atas EMA21 & VWAP, RSI 55–78,
  tren 1 jam naik. Stop di bawah level breakout − 0,5 ATR. Target 2R (atau resistance berikutnya kalau lebih dekat → batal kalau < 2R).
- **pullback**: tren naik (EMA9 > EMA21 > EMA50 di 5m, 1 jam naik), harga turun menyentuh zona EMA21/VWAP lalu candle hijau
  tutup kembali di atas EMA9, RSI 40–60. Stop di bawah swing low − 0,3 ATR. Target 2R.
- Gold boleh dua arah (perpetual): versi turun dari dua setup di atas. Leverage maks dari `gold.leverage_maks`.

## Penilaian
- Skor teknikal, fundamental (on-chain: likuiditas/mcap, perputaran volume, tekanan beli, umur, holder, sosial), keamanan 0–100.
- Mesin waktu: 10.000 jalur dari candle 5m koin itu sendiri + uji ulang setup yang sama di riwayatnya.
  Lolos kalau peluang target-dulu ≥ `min_peluang_target_pct` DAN EV setelah biaya ≥ `min_ev_r`.

## Gaya laporan
Bahasa Indonesia, singkat, angka dulu. Sebut alamat kontrak lengkap (koin tiruan dengan nama sama sangat banyak).
Selalu tulis: masuk, stop, target, rugi maks dalam dolar, untung di target dalam dolar (sudah dipotong biaya), peluang, alasan.

# Kebijakan Privasi — Yofamo Studio

*Berlaku sejak 30 Oktober 2026 · English summary below*

Yofamo Studio adalah alat pribadi milik pengelola channel YouTube **Yofamo Technology** (@yofamoo_technology). Alat ini berjalan di komputer pemiliknya sendiri dan **tidak dipakai oleh orang lain**.

## Data yang diakses

Setelah pemilik channel login dengan akun Google-nya (OAuth), aplikasi ini memakai izin berikut **hanya untuk channel milik pemilik itu sendiri**:

| Izin | Kegunaan |
| --- | --- |
| `youtube.upload` | Mengunggah video yang sudah disetujui pemilik, selalu sebagai **private** |
| `youtube.readonly` | Membaca daftar video & nama channel untuk memastikan upload ke channel yang benar |
| `yt-analytics.readonly` | Membaca statistik & retensi penonton channel untuk laporan internal |

## Penyimpanan & berbagi

- Token login disimpan **hanya di komputer pemilik** (folder `rahasia/`, tidak pernah diunggah ke GitHub atau server mana pun).
- Data statistik disimpan sebagai file lokal di komputer pemilik.
- Tidak ada data yang dijual, dibagikan ke pihak ketiga, atau dipakai untuk iklan.
- Aplikasi tidak menghapus atau mengubah video yang sudah ada di channel.

## Mencabut akses

Akses bisa dicabut kapan saja di <https://myaccount.google.com/permissions> → **Yofamo Studio** → *Remove access*, lalu hapus folder `rahasia/` di komputer.

Penggunaan data YouTube tunduk pada [Ketentuan Layanan YouTube](https://www.youtube.com/t/terms) dan [Kebijakan Privasi Google](https://policies.google.com/privacy).

Kontak: lewat channel <https://www.youtube.com/@yofamoo_technology> (tab Tentang).

---

**English summary:** Yofamo Studio is a private, single-user tool run locally by the owner of the YouTube channel Yofamo Technology. It uses the `youtube.upload`, `youtube.readonly` and `yt-analytics.readonly` scopes only on the owner's own channel, to upload approved videos as private and to read channel statistics. OAuth tokens and data stay on the owner's computer and are never shared, sold or used for advertising. Access can be revoked at <https://myaccount.google.com/permissions>.

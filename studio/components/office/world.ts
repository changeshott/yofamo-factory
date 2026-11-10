import type { Look } from "./sprites";

/** Ukuran ruangan (tile isometrik) dan buffer piksel. */
export const RW = 22, RD = 22, WALL = 112, T = 16;
/** Baris ruang depan (y ≥ SEKAT): Ruang Meeting & Ruang Istirahat (sisi Shorts), Studio Suara & Taman (sisi Animasi). */
export const SEKAT = 15.4;
/** Ruang Animasi (tim video panjang) di samping kanan kantor Shorts: x dari R2X sampai TW, dipisah dinding kaca + pintu. */
export const R2X = 22.6, PINTU: [number, number] = [6.6, 8.8];
export const TW = 36;
export const BW = 984, BH = 640, OX = 372, OY = 132;

/** Dua ruang kantor + tampilan semua. Batas x (tile) tiap ruang, dipakai kamera untuk membingkai satu ruang. */
export type Ruang = "semua" | "shorts" | "animasi";
export const RUANG: { id: Ruang; nama: string; x: [number, number]; warna: string }[] = [
  { id: "semua", nama: "Semua", x: [0, 36], warna: "#9DB4CD" },
  { id: "shorts", nama: "Shorts", x: [0, 22], warna: "#47B5FF" },
  { id: "animasi", nama: "Animasi", x: [22, 36], warna: "#FF4FA3" },
];
/** Kotak (koordinat buffer) yang memuat satu ruang lengkap dengan dinding & label di atasnya. */
export function kotakRuang(id: Ruang): [number, number, number, number] {
  const [x0, x1] = (RUANG.find((r) => r.id === id) ?? RUANG[0]).x;
  const px = (x: number, y: number) => OX + (x - y) * T, py = (x: number, y: number, z = 0) => OY + ((x + y) * T) / 2 - z;
  return [px(x0, RD) - 8, py(x0, 0, WALL) - 12, px(x1, 0) + 8, py(x1, RD) + 10];
}

export type AgentId = "steve" | "nova" | "raka" | "dara" | "bima" | "kai" | "rara" | "uli" | "mila" | "bayu" | "citra" | "gilang" | "laras" | "tio" | "wulan";
export interface AgentDef {
  id: AgentId;
  skill: string;
  job: "steve" | "ide" | "penulis" | "suara" | "aset" | "editor" | "qc" | "upload" | "thumbnail" | "panjang";
  ruang?: "animasi";
  name: string;
  role: string;
  about: string;
  desk: [number, number];
  color: string;
  look: Look;
  busy: Partial<Record<string, string>>;
}

export const TEAM: AgentDef[] = [
  {
    id: "steve", skill: "steve-analis", job: "steve", name: "Steve", role: "Kepala analis", desk: [1.6, 2.6], color: "#47B5FF",
    about: "Kepala analis: statistik, retensi & kurva penonton, komentar, radar pasar Shorts Indonesia, eksperimen, dan post-mortem tiap video. Menyusun backlog topik untuk Nova dan pelajaran untuk seluruh tim.",
    look: { skin: "#EFC6A0", hair: "#4A3426", shirt: "#3F8FD6", pants: "#2C3B57", accent: "#BFE3FF", style: "short", glasses: true },
    busy: { steve: "Menganalisis data…", fetch: "Mengambil statistik…", data: "Mengumpulkan data…" },
  },
  {
    id: "nova", skill: "ide-riset", job: "ide", name: "Nova", role: "Ide & riset", desk: [5.4, 2.6], color: "#6FD29A",
    about: "Mencari 3 ide Short dari laporan Steve. Setiap fakta diverifikasi dengan minimal 2 sumber berbeda.",
    look: { skin: "#F3CFB0", hair: "#C8462C", shirt: "#4FB883", pants: "#3A3550", accent: "#F4F1E8", style: "long" },
    busy: { ide: "Riset ide di web…" },
  },
  {
    id: "raka", skill: "penulis", job: "penulis", name: "Raka", role: "Penulis naskah", desk: [9.2, 2.6], color: "#FF9A4D",
    about: "Kepala penulis: naskah dengan pembuka khas \"Tau nggak, …\", durasi sesuai topik, penutup yang tuntas, grafis gerak per kalimat, judul + 2 alternatif, deskripsi, tag, dan komentar pin.",
    look: { skin: "#C99068", hair: "#1A1A1A", shirt: "#F08A3C", pants: "#2B2B33", accent: "#2C3B57", style: "cap" },
    busy: { penulis: "Menulis naskah…" },
  },
  {
    id: "dara", skill: "suara", job: "suara", name: "Dara", role: "Suara & subtitle", desk: [1.6, 7.0], color: "#C792EA",
    about: "Mengubah naskah Raka menjadi voice-over ekspresif (tempo, nada & jeda mengikuti bagian naskah), timing per kata, subtitle, dan transkrip. Gratis, tanpa kuota Claude.",
    look: { skin: "#E8B892", hair: "#2E2140", shirt: "#9B6BD3", pants: "#2B2B3A", accent: "#F4F1E8", style: "bun", headphone: true },
    busy: { suara: "Merekam suara…" },
  },
  {
    id: "bima", skill: "aset", job: "aset", name: "Bima", role: "Pencari aset", desk: [5.4, 7.0], color: "#4FD1C5",
    about: "Sutradara visual: tiap kalimat dapat 1–3 shot vertikal (ganti tiap ±3 detik) dari footage YouTube CC, NASA, Pexels, gambar AI gratis yang digerakkan halus, atau kartu grafis. Semua legal dan kreditnya dicatat.",
    look: { skin: "#B97D57", hair: "#2A1D14", shirt: "#2FA59A", pants: "#34404F", accent: "#F4F1E8", style: "curly" },
    busy: { aset: "Memilih visual…" },
  },
  {
    id: "kai", skill: "editor", job: "editor", name: "Kai", role: "Editor video", desk: [9.2, 7.0], color: "#F2C94C",
    about: "Merakit video final dengan HyperFrames: hook bertingkat, subtitle 1 kata, grafis gerak biru sesuai kalimat, transisi halus, musik latar volume 10, dan penutup Subscribe. Gratis, tanpa kuota Claude.",
    look: { skin: "#E0AC86", hair: "#3B2A20", shirt: "#E3B23C", pants: "#2A2F3A", accent: "#1C1C1C", style: "short", glasses: true, headphone: true },
    busy: { editor: "Merender video…" },
  },
  {
    id: "mila", skill: "thumbnail", job: "thumbnail", name: "Mila", role: "Desainer thumbnail", desk: [13.0, 2.6], color: "#FF6BCB",
    about: "Mendesain thumbnail tiap Short: objek ASLI yang dibahas dipotong dari footage (latar transparan, bayangan tebal di sekelilingnya) di belakang tulisan hook dengan font & warna yang sama persis dengan video. Objek yang sama muncul bersama hook di detik awal video. Uli memasangnya otomatis saat upload.",
    look: { skin: "#F3CFB0", hair: "#2E2140", shirt: "#FF6BCB", pants: "#2D3A52", accent: "#FFF4E6", style: "bun" },
    busy: { thumbnail: "Mendesain thumbnail…", pasang_rembg: "Memasang pemotong latar…" },
  },
  {
    id: "rara", skill: "qc", job: "qc", name: "Rara", role: "Quality control", desk: [13.0, 7.0], color: "#F07178",
    about: "Menonton setiap video sebelum sampai ke kamu: mencari shot gelap, beku, tidak sesuai kalimat, atau gambar AI dengan teks rusak. Shot jelek ditolak, Bima mengganti, Kai merakit ulang (maks 2 putaran), lalu memberi skor.",
    look: { skin: "#F1C7A5", hair: "#5A2E1E", shirt: "#E05A66", pants: "#2B2B3A", accent: "#F4F1E8", style: "long", glasses: true },
    busy: { qc: "Memeriksa video…" },
  },
  {
    id: "uli", skill: "upload", job: "upload", name: "Uli", role: "Upload YouTube", desk: [16.8, 7.0], color: "#82AAFF",
    about: "Mengunggah video ke YouTube (private + jadwal tayang di jam terbaik), dengan deskripsi tanpa link sumber, kredit singkat, dan hashtag lengkap. Memimpin Autopilot: tim membuat & menjadwalkan sampai 3 video sehari. Juga mengurus musik latar. Tidak pernah menyentuh video lain di channel.",
    look: { skin: "#C68E6A", hair: "#121212", shirt: "#4E7BD9", pants: "#30323D", accent: "#F4F1E8", style: "cap" },
    busy: { upload: "Mengunggah…", login: "Menghubungkan YouTube…" },
  },
];

/** Tim Ruang Animasi: video YouTube panjang full animasi lukis-komik (agents/panjang/). Status kerja per tahap produksi panjang. */
export const TEAM2: AgentDef[] = [
  {
    id: "bayu", skill: "panjang-ide", job: "panjang", ruang: "animasi", name: "Bayu", role: "Showrunner & riset", desk: [23.8, 2.6], color: "#FF7A2F",
    about: "Showrunner video panjang: memilih satu teknologi nyata yang layak dibahas 5–12 menit (sering dari Shorts yang menang) DAN punya cukup footage asli, meriset ≥ 5 fakta bersumber, dan menyusun alur bab yang membuat penonton bertahan. Autopilot memanggilnya 1x sehari.",
    look: { skin: "#C99068", hair: "#1A1430", shirt: "#FF7A2F", pants: "#2B2B33", accent: "#FFD23F", style: "short" },
    busy: { p_ide: "Meriset topik & alur…" },
  },
  {
    id: "citra", skill: "panjang-naskah", job: "panjang", ruang: "animasi", name: "Citra", role: "Penulis adegan", desk: [27.6, 2.6], color: "#F2385A",
    about: "Menulis naskah per adegan gaya dokumenter: footage (kata kunci visual Inggris yang memperlihatkan teknologinya) diselingi motion graphic (cara kerja, angka, perbandingan, garis waktu, objek, kata, HP/TV), kartu bab, judul, thumbnail, dan deskripsi tanpa link.",
    look: { skin: "#EFC6A0", hair: "#5A2E1E", shirt: "#F2385A", pants: "#2A2F3A", accent: "#FFF4DC", style: "long" },
    busy: { p_naskah: "Menulis adegan…" },
  },
  {
    id: "gilang", skill: "panjang-naskah", job: "panjang", ruang: "animasi", name: "Gilang", role: "Pengisi suara", desk: [31.4, 2.6], color: "#19C6C6",
    about: "Mengisi narasi per adegan (edge-tts, tempo mengikuti jenis adegan) dan mencatat waktu tiap kata untuk subtitle kecil, kata yang muncul, dan butir motion graphic.",
    look: { skin: "#B97D57", hair: "#121212", shirt: "#19C6C6", pants: "#30323D", accent: "#F4F1E8", style: "cap", headphone: true },
    busy: { p_suara: "Merekam narasi…" },
  },
  {
    id: "laras", skill: "panjang-naskah", job: "panjang", ruang: "animasi", name: "Laras", role: "Pencari footage", desk: [23.8, 7.0], color: "#FFD23F",
    about: "Mencari footage 16:9 asli (YouTube CC BY, NASA, Wikimedia, Pexels, Pixabay) yang memperlihatkan teknologi yang diucapkan; tiap klip dicek pendeteksi teks — ada subtitle, tulisan, label nama, atau watermark → ditolak. Memotong benda asli (latar transparan) untuk motion graphic & thumbnail.",
    look: { skin: "#F3CFB0", hair: "#2E2140", shirt: "#FFD23F", pants: "#3A3550", accent: "#F2385A", style: "bun" },
    busy: { p_ilustrasi: "Mencari footage…" },
  },
  {
    id: "tio", skill: "panjang-naskah", job: "panjang", ruang: "animasi", name: "Tio", role: "Motion graphic", desk: [27.6, 7.0], color: "#6B3FD4",
    about: "Merender tiap adegan dengan HyperFrames: motion graphic gaya Video 1 (kertas abu-abu, serif, benda asli melayang berbayang, foto hitam-putih, mockup HP/TV, butiran film & garis VHS tipis) dan footage berbutiran tipis + vignet dengan subtitle kecil di tengah bawah.",
    look: { skin: "#E0AC86", hair: "#3B2A20", shirt: "#6B3FD4", pants: "#2A2F3A", accent: "#19C6C6", style: "curly", glasses: true },
    busy: { p_animasi: "Menganimasikan adegan…" },
  },
  {
    id: "wulan", skill: "panjang-naskah", job: "panjang", ruang: "animasi", name: "Wulan", role: "Editor akhir & QC", desk: [31.4, 7.0], color: "#39D36B",
    about: "Menyambung adegan + suara + musik jadi video 1080p 30 fps, membuat thumbnail 16:9 (benda asli berwarna di atas footage hitam-putih), chapter (bab) & subtitle, lalu QC berskor (durasi, layar hitam, kerasnya suara, footage pinjaman) — yang lolos bisa diupload otomatis oleh autopilot.",
    look: { skin: "#D9A47E", hair: "#1C1C1C", shirt: "#39D36B", pants: "#2D3A52", accent: "#F4F1E8", style: "long", glasses: true },
    busy: { p_rakit: "Merakit & memeriksa…" },
  },
];

export const FUTURE: { key: string; name: string; role: string; desk: [number, number] }[] = [];

export const FOUNDER = {
  name: "Zona",
  desk: [18.0, 2.0] as [number, number],
  seat: [19.3, 1.45] as [number, number], // di belakang meja, menghadap ke depan
  look: { skin: "#D9A47E", hair: "#1C1C1C", shirt: "#F4F1E8", pants: "#2D3A52", accent: "#FF9A4D", style: "short" } as Look,
};

/** Tempat tujuan saat agent sedang santai. */
export const SPOTS: Record<string, [number, number]> = {
  kopi: [11.2, 12.6],
  dispenser: [14.2, 12.6],
  sofa: [2.6, 12.2],
  jendela: [1.0, 5.6],
  papan: [3.0, 1.5],
  tv: [7.6, 1.6],
  server: [13.8, 1.8],
  meja_bundar: [11.3, 11.5],
  lapor: [17.0, 4.5],
  arcade: [34.6, 1.8],
  sofa_animasi: [33.4, 12.0],
  meja_cahaya: [27.0, 11.6],
  lapor_animasi: [29.5, 9.8],
  // ruang depan
  meeting: [5.0, 20.3],
  istirahat_sofa: [13.2, 18.6],
  foosball: [17.2, 19.9],
  mesin_jajan: [20.2, 16.9],
  studio_suara: [25.6, 19.2],
  taman: [32.4, 19.0],
};
/** Kursi rapat di sekeliling meja Ruang Meeting (dipakai saat rapat tim). */
export const KURSI_RAPAT: [number, number][] = [[3.2, 17.2], [5.0, 17.2], [6.8, 17.2], [3.2, 20.2], [5.0, 20.2], [6.8, 20.2], [1.9, 18.7], [8.1, 18.7]];
/** Nama ruang yang ditampilkan sebagai papan kecil (koordinat tile). */
export const NAMA_RUANG: { nama: string; di: [number, number]; warna: string }[] = [
  { nama: "Ruang Meeting", di: [5.0, 15.6], warna: "#6FD3FF" }, { nama: "Ruang Istirahat", di: [16.0, 15.6], warna: "#FFD23F" },
  { nama: "Studio Suara", di: [25.8, 15.6], warna: "#C792EA" }, { nama: "Taman", di: [32.6, 15.6], warna: "#6FD29A" },
];

/** Area yang tidak bisa dilewati (x0, y0, x1, y1) dalam tile. */
export const BLOCKED: [number, number, number, number][] = [
  // meja agent & meja kosong
  ...[...TEAM.map((a) => a.desk), ...FUTURE.map((f) => f.desk)].map(([x, y]) => [x - 0.05, y - 0.05, x + 2.05, y + 1.05] as [number, number, number, number]),
  [18.0 - 0.05, 0.9, 20.6 + 0.05, 3.2 + 0.05], // meja & kursi founder
  [13.2, 0, 14.4, 0.95], // server
  [20.4, 0, 22, 0.9], // lemari piala
  [16.4, 0.4, 17.2, 1.2], [21.1, 2.2, 21.9, 3.0], // pot tanaman ruang founder
  [0, 9.8, 0.9, 11.6], // rak bible
  [0, 11.8, 1.5, 14.6], // sofa
  [2.6, 12.0, 4.0, 13.1], // meja kopi
  [9.0, 13.6, 13.4, 15], // meja pantry
  [13.9, 13.6, 15.3, 15], // dispenser & kulkas
  [10.7, 10.0, 11.7, 11.0], // meja bundar
  [15.6, 0, 16.4, 4.0], [15.6, 5.0, 16.4, 6.4], [15.6, 5.6, 22, 6.4], // kaca ruang founder
  // Ruang Animasi
  [22.0, 0, 22.9, PINTU[0]], [22.0, PINTU[1], 22.9, 15], // dinding kaca pemisah (pintu di tengah)
  ...TEAM2.map((a) => a.desk).map(([x, y]) => [x - 0.05, y - 0.05, x + 2.05, y + 1.05] as [number, number, number, number]),
  [34.6, 0, 36, 1.2], // mesin arcade
  [32.4, 11.4, 36, 14.6], // sofa retro
  [25.8, 10.8, 28.4, 12.2], // meja cahaya animator
  [23.0, 13.4, 25.4, 15], // rak kaset & TV CRT
  // sekat kaca ruang depan (pintu di x 4,2–5,8 · 15,2–16,8 · 25–26,4 · 31,6–33,2)
  [0, 15.1, 4.2, 15.7], [5.8, 15.1, 15.2, 15.7], [16.8, 15.1, 22.9, 15.7], [22.9, 15.1, 25.0, 15.7], [26.4, 15.1, 31.6, 15.7], [33.2, 15.1, 36, 15.7],
  [9.7, 15.7, 10.3, 22], [28.7, 15.7, 29.3, 22], [22.0, 15.7, 22.9, 22], // sekat antar ruang depan
  [2.6, 17.7, 7.4, 19.7], // meja rapat
  [10.6, 16.2, 12.2, 20.4], [10.6, 20.0, 14.4, 21.4], // sofa L ruang istirahat
  [16.4, 18.4, 18.0, 19.4], // foosball
  [20.6, 15.8, 21.9, 17.4], // mesin jajan & kulkas
  [23.2, 16.2, 24.6, 18.0], [26.8, 20.2, 28.4, 21.6], // bilik rekam & rak alat
  [34.2, 16.2, 35.8, 17.8], [29.8, 20.2, 31.4, 21.6], // pohon besar & bangku taman
];

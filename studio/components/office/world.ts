import type { Look } from "./sprites";

/** Ukuran ruangan (tile isometrik) dan buffer piksel. */
export const RW = 22, RD = 15, WALL = 112, T = 16;
export const BW = 624, BH = 446, OX = 256, OY = 132;

export type AgentId = "steve" | "nova" | "raka" | "dara" | "bima" | "kai" | "rara" | "uli";
export interface AgentDef {
  id: AgentId;
  skill: string;
  job: "steve" | "ide" | "penulis" | "suara" | "aset" | "editor" | "qc" | "upload";
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
    look: { skin: "#E8B892", hair: "#2E2140", shirt: "#9B6BD3", pants: "#2B2B3A", accent: "#F4F1E8", style: "bun" },
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
    look: { skin: "#E0AC86", hair: "#3B2A20", shirt: "#E3B23C", pants: "#2A2F3A", accent: "#1C1C1C", style: "short", glasses: true },
    busy: { editor: "Merender video…" },
  },
  {
    id: "rara", skill: "qc", job: "qc", name: "Rara", role: "Quality control", desk: [13.0, 7.0], color: "#F07178",
    about: "Menonton setiap video sebelum sampai ke kamu: mencari shot gelap, beku, tidak sesuai kalimat, atau gambar AI dengan teks rusak. Shot jelek ditolak, Bima mengganti, Kai merakit ulang (maks 2 putaran), lalu memberi skor.",
    look: { skin: "#F1C7A5", hair: "#5A2E1E", shirt: "#E05A66", pants: "#2B2B3A", accent: "#F4F1E8", style: "long", glasses: true },
    busy: { qc: "Memeriksa video…" },
  },
  {
    id: "uli", skill: "upload", job: "upload", name: "Uli", role: "Upload YouTube", desk: [16.8, 7.0], color: "#82AAFF",
    about: "Mengunggah video yang sudah kamu setujui ke YouTube sebagai PRIVATE, lengkap dengan judul, deskripsi, kredit, tag, dan label konten sintetis. Juga mengurus musik latar: memilih lagu dari perpustakaanmu sesuai suasana. Tidak pernah menyentuh video lain di channel.",
    look: { skin: "#C68E6A", hair: "#121212", shirt: "#4E7BD9", pants: "#30323D", accent: "#F4F1E8", style: "cap" },
    busy: { upload: "Mengunggah…", login: "Menghubungkan YouTube…" },
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
};

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
];

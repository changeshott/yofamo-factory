export type Tier = "menang" | "rata-rata" | "lemah";

export interface SnapshotVideo {
  id: string;
  url: string;
  title: string;
  published: string;
  age_days: number;
  views: number;
  likes: number;
  comments: number;
  views_per_day: number;
  engagement_pct: number;
  vs_median: number | null;
  tier: Tier;
  views_since_last: number | null;
  is_new: boolean;
}

export interface Snapshot {
  snapshot_date: string;
  channel: { title: string; handle: string; subscribers: number; total_views: number; video_count: number };
  summary: { videos: number; median_views: number; mean_views: number; winners: string[]; previous_snapshot: string | null };
  videos: SnapshotVideo[];
}

export type VideoStatus = "ide" | "disetujui" | "naskah" | "suara" | "aset" | "draft" | "export" | "terbit" | "ditolak";

export interface Fact { klaim: string; sumber_nama?: string; sumber_url: string; kutipan?: string; tanggal_sumber?: string; tier?: number | null }
export interface Idea {
  _error?: string;
  judul_kerja?: string;
  kategori?: string;
  status_teknologi?: string;
  kenapa_menang?: string;
  hook_ide?: string;
  fakta?: Fact[];
  visual_tersedia?: string;
  risiko?: string;
  slot?: string;
  kenapa_sekarang?: string;
  hook_varian?: { jenis: string; teks: string }[];
  angka_kunci?: { angka: string; label: string }[];
  salah_kaprah?: string;
  pertanyaan_penonton?: string[];
  visual?: { skor: number | null; jumlah?: Record<string, number> };
  skor?: { total: number; rubrik: Record<string, number>; sinyal: string[] };
}
export interface Script {
  _error?: string;
  judul?: string;
  hook_teks?: string;
  judul_alternatif?: string[];
  target_durasi?: number;
  suasana?: string;
  penutup_tipe?: string;
  komentar_pin?: string;
  narasi?: { kalimat: string; visual: string; bagian?: string; jenis_visual?: string; teks_layar?: string | null; penekanan?: string[] }[];
  deskripsi?: string;
  tag?: string[];
  sumber?: string[];
  catatan_editor?: string;
}

export interface Video {
  slug: string;
  judul_kerja: string;
  status: VideoStatus;
  dibuat: string;
  diubah: string;
  catatan: string;
  label: string;
  idea: Idea | null;
  script: Script | null;
  moves: VideoStatus[];
  media: { vo: boolean; srt: boolean; naskah?: boolean; transkrip?: boolean; durasi: number | null; uji: boolean; suara: string | null };
  aset: AsetManifest | null;
  final: { ada: boolean; durasi: number | null; musik: string | null; dibuat: string | null; uji: boolean };
  qc: { skor: number | null; lolos: boolean | null; catatan: string; saran: string[]; masalah: string[]; putaran: number; lembar: string[]; porsi: Record<string, number> | null } | null;
  upload: { videoId: string; url: string; studio: string; waktu: string; jadwal: string | null } | null;
}

export interface Klip {
  i: number; potong: number; file: string; mulai: number; selesai: number; durasi: number; kalimat: string; uji: boolean;
  jenis: "footage" | "ai" | "grafis"; sumber: string; id?: string; judul?: string; url_halaman?: string; pembuat?: string;
  lisensi?: string; kueri?: string; ada?: boolean;
}
export interface AsetManifest { _error?: string; dibuat?: string; uji?: boolean; durasi?: number; pakai_ai?: boolean; klip?: Klip[]; kurang?: number[]; kredit?: string }

export interface Activity { slug: string; dari: string | null; ke: string; waktu: string; judul_kerja: string | null }

export type JobName = "fetch" | "check" | "steve" | "ide" | "penulis" | "suara" | "aset" | "editor" | "produksi" | "qc" | "upload" | "login" | "data";
export interface JobState {
  job: JobName | null;
  arg: string | null;
  status: "idle" | "running" | "ok" | "error" | "stopped";
  started: string | null;
  finished: string | null;
  log: string | null;
}

export interface Tahap { kunci: string; job: string; nama: string; status: "menunggu" | "jalan" | "ok" | "gagal"; mulai: string | null; selesai: string | null; catatan: string }
export interface Produksi {
  id: string; permintaan: string; opsi: { suara: string; visual: string; uji?: boolean }; dibuat: string; selesai: string | null;
  status: "berjalan" | "selesai" | "gagal" | "terhenti"; slug: string | null; pesan: string; tahap: Tahap[];
}

export interface SteveInsight {
  tanggal: string | null;
  kpi: { subscriber: number; subscriber_per_hari: number | null; median_views_shorts: number; median_10_terbaru: number | null; median_10_sebelumnya: number | null;
    upload_30_hari: number; hari_sejak_upload: number | null; proyeksi: Record<string, number | null> } | null;
  retensi: { rata: number | null } | null;
  kategori: Record<string, { n: number; median: number | null; label: string }> | null;
  peluang: { judul: string; channel: string; views_per_hari: number; kategori: string; url: string }[];
  permintaan: { teks: string; like: number }[];
  kurang: string[];
  backlog: { judul_kerja: string; kategori?: string; skor?: number; alasan?: string; sudut_hook?: string }[];
  backlogTanggal: string | null;
  eksperimen: string; pelajaran: string;
}

export interface FileEntry { name: string; modified: string }

export interface StudioState {
  snapshot: Snapshot | null;
  videos: Video[];
  activity: Activity[];
  week: { since: string; published: number };
  reports: FileEntry[];
  logs: FileEntry[];
  agents: { key: string; ready: boolean }[];
  job: JobState;
  produksi: Produksi[];
  steve: SteveInsight | null;
  antrean: { id: string; teks: string; suara: string; visual: string; dibuat: string }[];
  health: { env: boolean; claude: boolean; python: boolean; pythonCmd: string; edgeTts: boolean; stockKey: boolean; ffmpeg: boolean; ytdlp: boolean; aiKey: boolean; google: boolean; ytClient: boolean; ytLogin: boolean };
}

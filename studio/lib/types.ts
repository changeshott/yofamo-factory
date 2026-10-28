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

export interface Fact { klaim: string; sumber_nama?: string; sumber_url: string }
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
}
export interface Script {
  _error?: string;
  judul?: string;
  hook_teks?: string;
  narasi?: { kalimat: string; visual: string }[];
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
  media: { vo: boolean; srt: boolean; durasi: number | null; uji: boolean; suara: string | null };
  aset: AsetManifest | null;
  final: { ada: boolean; durasi: number | null; musik: string | null; dibuat: string | null; uji: boolean };
}

export interface Klip {
  i: number; potong: number; file: string; mulai: number; selesai: number; durasi: number; kalimat: string; uji: boolean;
  jenis: "footage" | "ai" | "grafis"; sumber: string; id?: string; judul?: string; url_halaman?: string; pembuat?: string;
  lisensi?: string; kueri?: string; ada?: boolean;
}
export interface AsetManifest { _error?: string; dibuat?: string; uji?: boolean; durasi?: number; pakai_ai?: boolean; klip?: Klip[]; kurang?: number[]; kredit?: string }

export interface Activity { slug: string; dari: string | null; ke: string; waktu: string; judul_kerja: string | null }

export type JobName = "fetch" | "check" | "steve" | "ide" | "penulis" | "suara" | "aset" | "editor" | "produksi";
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
  health: { env: boolean; claude: boolean; python: boolean; pythonCmd: string; edgeTts: boolean; stockKey: boolean; ffmpeg: boolean; ytdlp: boolean; aiKey: boolean };
}

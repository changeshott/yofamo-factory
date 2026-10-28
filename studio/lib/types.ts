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
}

export interface Klip {
  i: number; kalimat: string; visual: string; kueri: string; durasi_butuh: number; file: string;
  sumber: "pexels" | "pixabay"; id: number; url_halaman: string; gambar: string; pembuat: string;
  durasi: number; lebar: number; tinggi: number; lisensi: string; terlalu_pendek: boolean; ada?: boolean;
}
export interface AsetManifest { _error?: string; dibuat?: string; uji?: boolean; kueri_inggris?: boolean; klip?: Klip[]; kurang?: number[] }

export interface Activity { slug: string; dari: string | null; ke: string; waktu: string; judul_kerja: string | null }

export type JobName = "fetch" | "check" | "steve" | "ide" | "penulis" | "suara" | "aset";
export interface JobState {
  job: JobName | null;
  arg: string | null;
  status: "idle" | "running" | "ok" | "error" | "stopped";
  started: string | null;
  finished: string | null;
  log: string | null;
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
  health: { env: boolean; claude: boolean; python: boolean; pythonCmd: string; edgeTts: boolean; stockKey: boolean };
}

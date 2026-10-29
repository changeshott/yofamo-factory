import "server-only";
import { execFile, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import type { Activity, FileEntry, Produksi, Snapshot, SteveInsight, Video, VideoStatus } from "@/lib/types";

const run = promisify(execFile);

/** Folder project yofamo-factory (studio/ berada di dalamnya). */
export const ROOT = process.env.YOFAMO_ROOT ? path.resolve(process.env.YOFAMO_ROOT) : path.resolve(process.cwd(), "..");
export const P = {
  raw: path.join(ROOT, "insights", "raw"),
  insights: path.join(ROOT, "insights"),
  logs: path.join(ROOT, "logs"),
  bible: path.join(ROOT, "bible", "channel-bible.md"),
  bibleHistory: path.join(ROOT, "bible", ".history"),
  videos: path.join(ROOT, "videos"),
  skills: path.join(ROOT, ".claude", "skills"),
  env: path.join(ROOT, ".env"),
  pabrik: path.join(ROOT, "agents", "pabrik.py"),
  produksi: path.join(ROOT, "produksi"),
  cache: path.join(ROOT, "cache"),
  rahasia: path.join(ROOT, "rahasia"),
};

/** Ukuran folder/file (byte), untuk panel Kelola hasil. */
export function sizeOf(p: string): number {
  try {
    const st = fs.statSync(p);
    if (!st.isDirectory()) return st.size;
    return fs.readdirSync(p).reduce((n, f) => n + sizeOf(path.join(p, f)), 0);
  } catch {
    return 0;
  }
}

export const SAFE_FILE = /^[\w.\-]+$/;
export const SLUG = /^[a-z0-9-]{3,80}$/;

/** Cari program di PATH (Windows: .exe/.cmd). */
export function which(name: string): string | null {
  const exts = process.platform === "win32" ? [".exe", ".cmd", ".bat", ""] : [""];
  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const full = path.join(dir.replace(/^"|"$/g, ""), name + ext);
      try {
        if (fs.statSync(full).isFile()) return full;
      } catch {
        /* lanjut */
      }
    }
  }
  return null;
}

/** Semua salinan program di PATH, berurutan. */
function whichAll(name: string): string[] {
  const exts = process.platform === "win32" ? [".exe", ""] : [""];
  const out: string[] = [];
  for (const dir of (process.env.PATH ?? "").split(path.delimiter)) {
    if (!dir) continue;
    for (const ext of exts) {
      const full = path.join(dir.replace(/^"|"$/g, ""), name + ext);
      try {
        if (fs.statSync(full).isFile() && !out.includes(full)) out.push(full);
      } catch {
        /* lanjut */
      }
    }
  }
  return out;
}

const pyPick: { exe: string | null; at: number } = { exe: null, at: 0 };

/**
 * Python untuk agent. Bukan sekadar "python" pertama di PATH: bisa saja itu venv aplikasi lain
 * (misalnya hermes-agent) yang tidak punya edge-tts/yt-dlp. Pilih yang paket pabriknya lengkap.
 * YOFAMO_PYTHON di lingkungan bisa memaksa satu Python tertentu.
 */
export function pythonCmd(): string | null {
  if (pyPick.exe && Date.now() - pyPick.at < 10 * 60_000) return pyPick.exe;
  const forced = process.env.YOFAMO_PYTHON;
  const cands = forced ? [forced] : [];
  if (process.platform === "win32") {
    cands.push(...whichAll("python"));
    try {
      const launcher = which("py");
      if (launcher) cands.push(execFileSync(launcher, ["-3", "-c", "import sys;print(sys.executable)"], { windowsHide: true, timeout: 10_000, encoding: "utf8" }).trim());
    } catch {
      /* py launcher tidak ada */
    }
  } else cands.push(...whichAll("python3"), ...whichAll("python"));
  const uniq = [...new Set(cands.filter(Boolean))];
  const ok = (exe: string) => {
    try {
      execFileSync(exe, ["-c", "import edge_tts, yt_dlp"], { windowsHide: true, timeout: 20_000, stdio: "ignore" });
      return true;
    } catch {
      return false;
    }
  };
  const exe = uniq.find(ok) ?? uniq.find((e) => !/WindowsApps/i.test(e)) ?? null;
  pyPick.exe = exe;
  pyPick.at = Date.now();
  return exe;
}

/** Lingkungan untuk proses agent: folder Python terpilih di depan PATH, supaya `python` yang
 *  dipanggil Claude (skill) dan script lain sama dengan Python yang paketnya lengkap. */
export function agentEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONIOENCODING: "utf-8" };
  const py = pythonCmd();
  if (py && path.isAbsolute(py)) {
    const key = Object.keys(env).find((k) => k.toUpperCase() === "PATH") ?? "PATH";
    const dir = path.dirname(py);
    env[key] = [dir, path.join(dir, "Scripts"), env[key] ?? ""].join(path.delimiter);
    env.YOFAMO_PYTHON ??= py; // shell Claude bisa menyusun ulang PATH; script memakai ini (agents/pakai_python.py)
  }
  return env;
}

export async function pabrik<T>(args: string[]): Promise<T> {
  const py = pythonCmd();
  if (!py) throw new Error("Python tidak ditemukan di PATH.");
  const { stdout } = await run(py, [P.pabrik, ...args], { cwd: ROOT, windowsHide: true, timeout: 20_000, encoding: "utf8" });
  return JSON.parse(stdout) as T;
}

function readJson<T>(file: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(file, "utf8").replace(/^﻿/, "")) as T;
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    return { _error: `${path.basename(file)} bukan JSON yang valid` } as T;
  }
}

export function latestSnapshot(): Snapshot | null {
  try {
    // hanya snapshot harian YYYY-MM-DD.json (bukan analisa-/analitik-/komentar-/pasar-)
    const files = fs.readdirSync(P.raw).filter((f) => /^\d{4}-\d\d-\d\d\.json$/.test(f)).sort();
    return files.length ? readJson<Snapshot>(path.join(P.raw, files[files.length - 1])) : null;
  } catch {
    return null;
  }
}

/** Wawasan Steve untuk dasbor: analisa terbaru, backlog topik, eksperimen, pelajaran. */
export function steveInsight(): SteveInsight | null {
  try {
    const an = fs.readdirSync(P.raw).filter((f) => /^analisa-\d{4}-\d\d-\d\d\.json$/.test(f)).sort().pop();
    const a = an ? readJson<Record<string, unknown>>(path.join(P.raw, an)) : null;
    const bl = readJson<{ dibuat?: string; topik?: SteveInsight["backlog"] }>(path.join(P.insights, "topik_backlog.json"));
    const txt = (f: string) => { try { return fs.readFileSync(path.join(P.insights, f), "utf8").slice(0, 6000); } catch { return ""; } };
    if (!a && !bl) return null;
    return {
      tanggal: (a?.tanggal as string) ?? null,
      kpi: (a?.kpi as SteveInsight["kpi"]) ?? null,
      retensi: a?.retensi ? { rata: (a.retensi as { rata_persen_ditonton?: number }).rata_persen_ditonton ?? null } : null,
      kategori: (a?.kategori as SteveInsight["kategori"]) ?? null,
      peluang: ((a?.peluang_pasar as SteveInsight["peluang"]) ?? []).slice(0, 6),
      permintaan: (((a?.komentar as { permintaan?: { teks: string; like: number }[] })?.permintaan) ?? []).slice(0, 4).map((k) => ({ teks: k.teks, like: k.like })),
      kurang: (a?.data_kurang as string[]) ?? [],
      backlog: (bl?.topik ?? []).slice(0, 10), backlogTanggal: bl?.dibuat ?? null,
      eksperimen: txt("eksperimen.md"), pelajaran: txt("pelajaran.md"),
    };
  } catch {
    return null;
  }
}

export function listFiles(dir: string, ext: string, limit = 40, byName = false): FileEntry[] {
  try {
    return fs
      .readdirSync(dir)
      .filter((f) => f.endsWith(ext))
      .map((name) => ({ name, mtime: fs.statSync(path.join(dir, name)).mtime }))
      .sort((a, b) => (byName ? b.name.localeCompare(a.name) : b.mtime.getTime() - a.mtime.getTime()))
      .slice(0, limit)
      .map(({ name, mtime }) => ({ name, modified: localIso(mtime) }));
  } catch {
    return [];
  }
}

export function localIso(d = new Date()): string {
  const off = d.getTimezoneOffset() * 60_000;
  return new Date(d.getTime() - off).toISOString().slice(0, 19);
}

const LABEL: Record<VideoStatus, string> = {
  ide: "Ide menunggu persetujuan",
  disetujui: "Ide disetujui",
  naskah: "Naskah siap",
  suara: "Suara siap",
  aset: "Aset siap",
  draft: "Video jadi, cek dulu",
  export: "Siap upload",
  terbit: "Sudah terbit",
  ditolak: "Ditolak",
};

/** Perubahan status yang boleh dilakukan Zona dari Studio. */
export const MANUAL_MOVES: Partial<Record<VideoStatus, VideoStatus[]>> = {
  ide: ["disetujui", "ditolak"],
  ditolak: ["ide"],
  disetujui: ["ide"],
  naskah: ["disetujui", "export", "terbit"],
  suara: ["naskah", "export", "terbit"],
  aset: ["suara", "terbit"],
  draft: ["export", "aset"],
  export: ["terbit", "draft"],
};

type Row = Omit<Video, "label" | "idea" | "script" | "moves">;

export async function videos(): Promise<Video[]> {
  const rows = await pabrik<Row[]>(["list", "--json"]);
  return rows.map((r) => ({
    ...r,
    label: LABEL[r.status] ?? r.status,
    idea: readJson(path.join(P.videos, r.slug, "idea.json")),
    script: readJson(path.join(P.videos, r.slug, "script.json")),
    moves: MANUAL_MOVES[r.status] ?? [],
    media: media(r.slug),
    aset: aset(r.slug),
    final: final(r.slug),
    qc: qc(r.slug),
    upload: readJson<NonNullable<Video["upload"]>>(path.join(P.videos, r.slug, "export", "upload.json")),
  }));
}

function qc(slug: string): Video["qc"] {
  const dir = path.join(P.videos, slug, "export");
  const q = readJson<{ masalah?: string[]; putaran?: number; lembar?: string[]; porsi?: Record<string, number> }>(path.join(dir, "qc.json"));
  const r = readJson<{ skor?: number; lolos?: boolean; catatan?: string; saran_zona?: string[] }>(path.join(dir, "qc_review.json"));
  if (!q && !r) return null;
  return { skor: r?.skor ?? null, lolos: r?.lolos ?? null, catatan: r?.catatan ?? "", saran: r?.saran_zona ?? [], masalah: q?.masalah ?? [],
    putaran: q?.putaran ?? 0, lembar: (q?.lembar ?? []).filter((x) => /^export\/qc\/lembar-\d+\.jpg$/.test(x)), porsi: q?.porsi ?? null };
}

function final(slug: string): Video["final"] {
  const dir = path.join(P.videos, slug, "export");
  const i = readJson<{ durasi?: number; musik?: string; dibuat?: string; uji?: boolean }>(path.join(dir, "info.json"));
  return { ada: fs.existsSync(path.join(dir, "final.mp4")), durasi: i?.durasi ?? null, musik: i?.musik ?? null, dibuat: i?.dibuat ?? null, uji: !!i?.uji };
}

function aset(slug: string): Video["aset"] {
  const dir = path.join(P.videos, slug, "aset");
  const m = readJson<NonNullable<Video["aset"]>>(path.join(dir, "manifest.json"));
  if (!m || m._error || !Array.isArray(m.klip)) return m;
  let kredit = "";
  try { kredit = fs.readFileSync(path.join(dir, "kredit_deskripsi.txt"), "utf8"); } catch { /* belum ada */ }
  return { ...m, kredit, klip: m.klip.map((k) => ({ ...k, ada: SAFE_FILE.test(k.file) && fs.existsSync(path.join(dir, k.file)) })) };
}

/** Apakah key ini terisi di .env? Nilainya tidak pernah dibaca keluar. */
export function envHas(...keys: string[]): boolean {
  try {
    const text = fs.readFileSync(P.env, "utf8");
    return keys.some((k) => new RegExp(`^\\s*${k}\\s*=\\s*\\S+`, "m").test(text));
  } catch {
    return false;
  }
}

function media(slug: string): Video["media"] {
  const dir = path.join(P.videos, slug);
  const w = readJson<{ durasi?: number; uji?: boolean; suara?: string }>(path.join(dir, "words.json"));
  return {
    vo: fs.existsSync(path.join(dir, "vo.mp3")),
    srt: fs.existsSync(path.join(dir, "captions.srt")),
    naskah: fs.existsSync(path.join(dir, "naskah.md")),
    transkrip: fs.existsSync(path.join(dir, "transkrip.txt")),
    durasi: w?.durasi ?? null,
    uji: !!w?.uji,
    suara: w?.suara ?? null,
  };
}

const modCache = new Map<string, { at: number; ok: boolean }>();
/** Cek paket Python terpasang (di-cache 60 detik supaya polling tetap ringan). */
export async function hasModule(mod: string): Promise<boolean> {
  const c = modCache.get(mod);
  if (c && Date.now() - c.at < 60_000) return c.ok;
  const py = pythonCmd();
  let ok = false;
  if (py) { try { await run(py, ["-c", `import ${mod}`], { windowsHide: true, timeout: 20_000 }); ok = true; } catch { ok = false; } }
  modCache.set(mod, { at: Date.now(), ok });
  return ok;
}

/** Permintaan "Buat video" terbaru (dari produksi/<id>.json). */
export function produksi(running: boolean): Produksi[] {
  try {
    return fs.readdirSync(P.produksi).filter((f) => /^[\w-]+\.json$/.test(f)).sort().reverse().slice(0, 12)
      .map((f) => readJson<Produksi>(path.join(P.produksi, f)))
      .filter((x): x is Produksi => !!x && Array.isArray(x.tahap))
      .map((x, i) => (x.status === "berjalan" && !(running && i === 0) ? { ...x, status: "terhenti" as const } : x));
  } catch {
    return [];
  }
}

export const activity = () => pabrik<Activity[]>(["history", "--limit", "40", "--json"]);
export const week = () => pabrik<{ since: string; published: number }>(["week", "--json"]);

export function readText(file: string, tail = 0): string {
  const text = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  return tail && text.length > tail ? text.slice(-tail) : text;
}

import "server-only";
import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";
import type { Activity, FileEntry, Snapshot, Video, VideoStatus } from "@/lib/types";

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
};

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

export function pythonCmd(): string | null {
  return process.platform === "win32" ? which("python") ?? which("py") : which("python3") ?? which("python");
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
    const files = fs.readdirSync(P.raw).filter((f) => f.endsWith(".json")).sort();
    return files.length ? readJson<Snapshot>(path.join(P.raw, files[files.length - 1])) : null;
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
  draft: "Draft CapCut siap",
  export: "Sudah di-export",
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
  aset: ["suara", "export", "terbit"],
  export: ["terbit"],
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
  }));
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

export const activity = () => pabrik<Activity[]>(["history", "--limit", "40", "--json"]);
export const week = () => pabrik<{ since: string; published: number }>(["week", "--json"]);

export function readText(file: string, tail = 0): string {
  const text = fs.readFileSync(file, "utf8").replace(/^﻿/, "");
  return tail && text.length > tail ? text.slice(-tail) : text;
}

import "server-only";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { JobName, JobState } from "@/lib/types";
import { P, ROOT, SLUG, agentEnv, localIso, pabrik, pythonCmd, which } from "./project";

/** Alat yang boleh dipakai Claude per agent. Selain ini otomatis ditolak. */
function scriptTools(...scripts: string[]): string[] {
  const out = ["Read", "Write", "Glob", "Grep"];
  for (const sc of scripts) {
    for (const py of ["python", "python3"]) out.push(`Bash(${py} ${sc} *)`, `Bash(${py} ${sc})`);
    out.push(`PowerShell(python ${sc} *)`, `PowerShell(python ${sc})`);
  }
  return out;
}
const TOOLS = {
  steve: scriptTools("agents/steve/kumpul.py", "agents/steve/fetch_stats.py", "agents/steve/komentar.py", "agents/steve/pasar.py", "agents/steve/analitik.py", "agents/steve/analisa.py", "agents/ide/cek_topik.py", "agents/pabrik.py"),
  ide: [...scriptTools("agents/pabrik.py", "agents/ide/radar.py", "agents/ide/cek_topik.py", "agents/ide/cek_visual.py", "agents/ide/cek_ide.py"), "WebSearch", "WebFetch"],
  penulis: scriptTools("agents/pabrik.py", "agents/penulis/cek_naskah.py"),
  aset: scriptTools("agents/pabrik.py", "agents/aset/cari_aset.py"),
  qc: scriptTools("agents/pabrik.py", "agents/qc/periksa.py"),
};

type Store = { state: JobState; child: ChildProcess | null };
const g = globalThis as unknown as { __yofamoJobs?: Store };
const store: Store = (g.__yofamoJobs ??= {
  state: { job: null, arg: null, status: "idle", started: null, finished: null, log: null },
  child: null,
});

export const jobState = (): JobState => ({ ...store.state });

async function command(job: JobName, arg: string): Promise<{ cmd: string; args: string[] } | string> {
  const py = pythonCmd();
  if (job === "data") {
    if (!py) return "Python tidak ditemukan.";
    return { cmd: py, args: ["agents/steve/kumpul.py", ...(arg === "pasar" ? ["--pasar"] : arg === "ringan" ? ["--ringan"] : [])] };
  }
  if (job === "fetch" || job === "check") {
    if (!py) return "Python tidak ditemukan. Install Python dan centang 'Add python.exe to PATH'.";
    return { cmd: py, args: ["agents/steve/fetch_stats.py", ...(job === "check" ? ["--check"] : [])] };
  }
  if (job === "suara") {
    if (!py) return "Python tidak ditemukan.";
    const [slug, voice] = arg.split("|");
    if (!SLUG.test(slug ?? "")) return "Video tidak ditemukan.";
    const rows = await pabrik<{ slug: string; status: string }[]>(["list", "--json"]);
    const v = rows.find((r) => r.slug === slug);
    if (!v) return "Video tidak ditemukan.";
    if (v.status !== "naskah" && v.status !== "suara") return "Suara hanya bisa dibuat untuk video berstatus naskah.";
    const voiceArg = voice === "wanita" ? ["--voice", "id-ID-GadisNeural"] : [];
    return { cmd: py, args: ["agents/suara/buat_suara.py", slug, ...voiceArg] };
  }
  if (job === "editor") {
    if (!py) return "Python tidak ditemukan.";
    if (!which("ffmpeg")) return "ffmpeg belum terpasang. Jalankan: winget install Gyan.FFmpeg";
    if (!SLUG.test(arg)) return "Video tidak ditemukan.";
    const rows = await pabrik<{ slug: string; status: string }[]>(["list", "--json"]);
    const v = rows.find((r) => r.slug === arg);
    if (!v) return "Video tidak ditemukan.";
    if (v.status !== "aset" && v.status !== "draft") return "Video dirakit setelah visual dari Bima siap (status aset).";
    return { cmd: py, args: ["agents/editor/rakit.py", arg] };
  }
  if (job === "qc" || job === "upload") {
    if (!py) return "Python tidak ditemukan.";
    const [slug, opsi = ""] = arg.split("|");
    if (!SLUG.test(slug ?? "")) return "Video tidak ditemukan.";
    const rows = await pabrik<{ slug: string; status: string }[]>(["list", "--json"]);
    const v = rows.find((r) => r.slug === slug);
    if (!v) return "Video tidak ditemukan.";
    if (job === "qc") {
      if (v.status !== "draft") return "Rara memeriksa video yang sudah dirakit Kai (status: video jadi).";
      if (opsi === "otomatis") return { cmd: py, args: ["agents/qc/periksa.py", "otomatis", slug] };
      const claude = which("claude");
      if (!claude) return "Perintah 'claude' tidak ditemukan.";
      return { cmd: claude, args: ["-p", `/qc ${slug}`, "--model", "sonnet", "--max-turns", "60", "--allowedTools", ...TOOLS.qc] };
    }
    if (v.status !== "export") return "Hanya video yang sudah kamu setujui (Siap upload) yang boleh diupload.";
    if (opsi && !/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(opsi)) return "Format jadwal tidak valid.";
    return { cmd: py, args: ["agents/upload/unggah.py", "unggah", slug, ...(opsi ? ["--jadwal", opsi] : [])] };
  }
  if (job === "login") return py ? { cmd: py, args: ["agents/upload/unggah.py", "login"] } : "Python tidak ditemukan.";
  if (job === "produksi") {
    if (!py) return "Python tidak ditemukan.";
    if (!which("ffmpeg")) return "ffmpeg belum terpasang. Jalankan: winget install Gyan.FFmpeg";
    if (arg.startsWith("lanjut|")) {     // lanjutkan video yang berhenti di tengah jalan
      const [, suaraL, visualL, slugL] = arg.split("|");
      if (!SLUG.test(slugL ?? "")) return "Video tidak ditemukan.";
      return { cmd: py, args: ["agents/produser.py", "--lanjut", slugL, "--suara", suaraL === "wanita" ? "wanita" : "pria", "--visual", visualL === "cepat" ? "cepat" : "teliti"] };
    }
    const [suara, visual, ...rest] = arg.split("|");
    const teks = rest.join(" ").replace(/[^\p{L}\p{N}\s,.\-?!]/gu, "").trim().slice(0, 200);
    if (!which("claude")) return "Perintah 'claude' tidak ditemukan. Install Claude Code CLI dulu.";
    return { cmd: py, args: ["agents/produser.py", ...(teks.length >= 3 ? [teks] : []), "--suara", suara === "wanita" ? "wanita" : "pria", "--visual", visual === "cepat" ? "cepat" : "teliti", ...(process.env.YOFAMO_UJI === "1" ? ["--uji"] : [])] };
  }
  let asetSlug = "";
  if (job === "aset") {
    const [slug, mode] = arg.split("|");
    if (!SLUG.test(slug ?? "")) return "Video tidak ditemukan.";
    const rows = await pabrik<{ slug: string; status: string }[]>(["list", "--json"]);
    const v = rows.find((r) => r.slug === slug);
    if (!v) return "Video tidak ditemukan.";
    if (v.status !== "suara" && v.status !== "aset") return "Aset dicari setelah Dara membuat suara (status suara).";
    if (!which("ffmpeg")) return "ffmpeg belum terpasang. Jalankan: winget install Gyan.FFmpeg";
    if (mode === "cepat") return py ? { cmd: py, args: ["agents/aset/cari_aset.py", "semua", slug] } : "Python tidak ditemukan.";
    asetSlug = slug;
  }
  const claude = which("claude");
  if (!claude) return "Perintah 'claude' tidak ditemukan. Install Claude Code CLI lalu jalankan ulang Studio.";
  const base = ["--model", "sonnet", "--max-turns", "60", "--allowedTools"];
  if (job === "steve") return { cmd: claude, args: ["-p", "/steve-analis", ...base, ...TOOLS.steve] };
  if (job === "ide") {
    const theme = arg.replace(/[^\p{L}\p{N}\s,.\-]/gu, "").trim().slice(0, 120);
    return { cmd: claude, args: ["-p", `/ide-riset ${theme}`.trim(), ...base, ...TOOLS.ide] };
  }
  if (job === "penulis") {
    if (!SLUG.test(arg)) return "Video tidak ditemukan.";
    const rows = await pabrik<{ slug: string; status: string }[]>(["list", "--json"]);
    const v = rows.find((r) => r.slug === arg);
    if (!v) return "Video tidak ditemukan.";
    if (v.status !== "disetujui") return "Hanya ide berstatus disetujui yang bisa ditulis naskahnya.";
    return { cmd: claude, args: ["-p", `/penulis ${arg}`, ...base, ...TOOLS.penulis] };
  }
  if (job === "aset") return { cmd: claude, args: ["-p", `/aset ${asetSlug}`, ...base, ...TOOLS.aset] };
  return `Tugas tidak dikenal: ${job}`;
}

const LABEL: Record<JobName, string> = {
  fetch: "Ambil data",
  check: "Cek koneksi",
  steve: "Steve",
  ide: "Nova mencari ide",
  penulis: "Raka menulis naskah",
  suara: "Dara membuat suara",
  aset: "Bima mencari klip",
  editor: "Kai merakit video",
  produksi: "Produksi video",
  qc: "Rara memeriksa video",
  data: "Steve mengumpulkan data",
  upload: "Uli mengunggah ke YouTube",
  login: "Menghubungkan YouTube",
};

export async function startJob(job: JobName, arg = ""): Promise<{ ok: boolean; message: string }> {
  if (store.state.status === "running") return { ok: false, message: `Masih ada tugas berjalan: ${LABEL[store.state.job!]}.` };
  const c = await command(job, arg);
  if (typeof c === "string") return { ok: false, message: c };

  fs.mkdirSync(P.logs, { recursive: true });
  const stamp = localIso().replace(/:/g, "").replace("T", "_");
  const logName = `${job}-${stamp}.txt`;
  const out = fs.openSync(path.join(P.logs, logName), "w");
  fs.writeSync(out, `# ${LABEL[job]} — ${localIso().replace("T", " ").slice(0, 16)}\n\n`);

  const isCmd = /\.(cmd|bat)$/i.test(c.cmd);
  const child = spawn(c.cmd, c.args, {
    cwd: ROOT,
    stdio: ["ignore", out, out],
    windowsHide: true,
    shell: isCmd, // .cmd di Windows butuh shell; argumen sudah disaring
    env: agentEnv(),
    detached: process.platform !== "win32", // supaya Hentikan juga mematikan proses anak (claude, ffmpeg)
  });
  store.child = child;
  store.state = { job, arg: arg || null, status: "running", started: localIso(), finished: null, log: logName };

  const timer = setTimeout(() => child.kill(), (job === "produksi" ? 180 : 30) * 60_000);
  const done = (status: JobState["status"], note?: string) => {
    clearTimeout(timer);
    if (note) fs.writeSync(out, `\n[studio] ${note}\n`);
    if (job === "produksi" && status !== "ok") tandaiProduksiTerhenti(store.state.status === "stopped" ? "Dihentikan Zona." : note ?? "Proses berhenti.");
    fs.closeSync(out);
    store.child = null;
    if (store.state.log === logName) store.state = { ...store.state, status: store.state.status === "stopped" ? "stopped" : status, finished: localIso() };
    // antrean produksi: lanjut ke permintaan berikutnya (kecuali dihentikan Zona)
    if (store.state.status !== "stopped") setTimeout(() => { void nextInQueue(); }, 1500);
  };
  child.on("error", (err) => done("error", `Gagal menjalankan: ${err.message}`));
  child.on("exit", (code) => done(code === 0 ? "ok" : "error", code === 0 ? undefined : `Selesai dengan kode ${code}`));
  return { ok: true, message: "Dimulai." };
}

/** Produser yang dimatikan paksa (Hentikan, Studio ditutup) tidak sempat menulis status akhir: tandai di sini. */
function tandaiProduksiTerhenti(pesan: string) {
  try {
    for (const f of fs.readdirSync(P.produksi).filter((n) => /^\d{8}-\d{6}\.json$/.test(n))) {
      const fp = path.join(P.produksi, f);
      const d = JSON.parse(fs.readFileSync(fp, "utf-8")) as { status?: string; pesan?: string; selesai?: string | null; tahap?: { status: string; catatan?: string }[] };
      if (d.status !== "berjalan") continue;
      for (const t of d.tahap ?? []) if (t.status === "jalan") { t.status = "gagal"; t.catatan = pesan; }
      Object.assign(d, { status: "gagal", pesan, selesai: localIso() });
      fs.writeFileSync(fp, JSON.stringify(d, null, 2), "utf-8");
    }
  } catch { /* folder belum ada */ }
}

/* ------------------------------------------------------------ antrean produksi */
export interface QueueItem { id: string; teks: string; suara: string; visual: string; dibuat: string }
const QFILE = () => path.join(P.produksi, "antrean.json");

export function readQueue(): QueueItem[] {
  try { return JSON.parse(fs.readFileSync(QFILE(), "utf8")) as QueueItem[]; } catch { return []; }
}
function writeQueue(q: QueueItem[]) {
  fs.mkdirSync(P.produksi, { recursive: true });
  fs.writeFileSync(QFILE(), JSON.stringify(q, null, 2));
}
export async function enqueue(teks: string, suara: string, visual: string): Promise<{ ok: boolean; message: string }> {
  const clean = teks.replace(/[^\p{L}\p{N}\s,.\-?!]/gu, "").trim().slice(0, 200);
  const q = readQueue();
  if (q.length >= 20) return { ok: false, message: "Antrean penuh (maksimal 20)." };
  q.push({ id: `${Date.now()}`, teks: clean, suara: suara === "wanita" ? "wanita" : "pria", visual: visual === "cepat" ? "cepat" : "teliti", dibuat: localIso() });
  writeQueue(q);
  if (store.state.status !== "running") { await nextInQueue(); return { ok: true, message: "Produksi dimulai." }; }
  return { ok: true, message: `Masuk antrean (urutan ${q.length}).` };
}
export function dequeue(id: string): boolean {
  const q = readQueue(), n = q.filter((x) => x.id !== id);
  writeQueue(n);
  return n.length !== q.length;
}
async function nextInQueue() {
  if (store.state.status === "running") return;
  const q = readQueue();
  const it = q.shift();
  if (!it) return;
  writeQueue(q);
  const r = await startJob("produksi", `${it.suara}|${it.visual}|${it.teks}`);
  if (!r.ok) { fs.appendFileSync(path.join(P.logs, "antrean-gagal.txt"), `${localIso()} ${it.teks}: ${r.message}\n`); setTimeout(() => { void nextInQueue(); }, 1000); }
}

export function stopJob(): { ok: boolean; message: string } {
  if (store.state.status !== "running" || !store.child) return { ok: false, message: "Tidak ada tugas yang berjalan." };
  store.state = { ...store.state, status: "stopped" };
  if (process.platform === "win32" && store.child.pid) {
    spawn("taskkill", ["/pid", String(store.child.pid), "/T", "/F"], { windowsHide: true });
  } else if (store.child.pid) {
    try { process.kill(-store.child.pid, "SIGTERM"); } catch { store.child.kill(); }
  } else store.child.kill();
  return { ok: true, message: "Tugas dihentikan." };
}

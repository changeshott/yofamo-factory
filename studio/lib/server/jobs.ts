import "server-only";
import { spawn, type ChildProcess } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import type { JobName, JobState } from "@/lib/types";
import { P, ROOT, SLUG, localIso, pabrik, pythonCmd, which } from "./project";

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
  steve: scriptTools("agents/steve/fetch_stats.py"),
  ide: [...scriptTools("agents/pabrik.py"), "WebSearch", "WebFetch"],
  penulis: scriptTools("agents/pabrik.py", "agents/penulis/cek_naskah.py"),
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
  if (job === "fetch" || job === "check") {
    if (!py) return "Python tidak ditemukan. Install Python dan centang 'Add python.exe to PATH'.";
    return { cmd: py, args: ["agents/steve/fetch_stats.py", ...(job === "check" ? ["--check"] : [])] };
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
  return `Tugas tidak dikenal: ${job}`;
}

const LABEL: Record<JobName, string> = {
  fetch: "Ambil data",
  check: "Cek koneksi",
  steve: "Steve",
  ide: "Nova mencari ide",
  penulis: "Raka menulis naskah",
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
    env: { ...process.env, PYTHONIOENCODING: "utf-8" },
  });
  store.child = child;
  store.state = { job, arg: arg || null, status: "running", started: localIso(), finished: null, log: logName };

  const timer = setTimeout(() => child.kill(), 30 * 60_000);
  const done = (status: JobState["status"], note?: string) => {
    clearTimeout(timer);
    if (note) fs.writeSync(out, `\n[studio] ${note}\n`);
    fs.closeSync(out);
    store.child = null;
    if (store.state.log === logName) store.state = { ...store.state, status: store.state.status === "stopped" ? "stopped" : status, finished: localIso() };
  };
  child.on("error", (err) => done("error", `Gagal menjalankan: ${err.message}`));
  child.on("exit", (code) => done(code === 0 ? "ok" : "error", code === 0 ? undefined : `Selesai dengan kode ${code}`));
  return { ok: true, message: "Dimulai." };
}

export function stopJob(): { ok: boolean; message: string } {
  if (store.state.status !== "running" || !store.child) return { ok: false, message: "Tidak ada tugas yang berjalan." };
  store.state = { ...store.state, status: "stopped" };
  if (process.platform === "win32" && store.child.pid) {
    spawn("taskkill", ["/pid", String(store.child.pid), "/T", "/F"], { windowsHide: true });
  } else store.child.kill();
  return { ok: true, message: "Tugas dihentikan." };
}

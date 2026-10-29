import fs from "node:fs";
import path from "node:path";
import { jobState, readQueue, startJob } from "@/lib/server/jobs";
import { json } from "@/lib/server/guard";
import { P, activity, envHas, hasModule, latestSnapshot, listFiles, localIso, produksi, steveInsight, pythonCmd, videos, week, which } from "@/lib/server/project";
import type { StudioState } from "@/lib/types";

export const dynamic = "force-dynamic";
const AGENTS = ["steve-analis", "ide-riset", "penulis", "suara", "aset", "editor", "upload"];

const auto = globalThis as unknown as { __yofamoAutoData?: string };

/** Sekali sehari saat Studio terbuka & kantor kosong: Steve memperbarui statistik (tanpa kuota Claude). */
async function dataHarian(py: string | null) {
  const hariIni = localIso().slice(0, 10);
  if (!py || auto.__yofamoAutoData === hariIni || jobState().status === "running" || !fs.existsSync(P.env)) return;
  if (new Date().getHours() < 6) return;
  const snap = latestSnapshot();
  auto.__yofamoAutoData = hariIni;
  if (snap?.snapshot_date === hariIni) return;
  await startJob("data", "ringan").catch(() => {});
}

export async function GET() {
  const py = pythonCmd();
  await dataHarian(py);
  let vids: StudioState["videos"] = [], act: StudioState["activity"] = [], wk = { since: "", published: 0 };
  if (py) {
    try { [vids, act, wk] = await Promise.all([videos(), activity(), week()]); } catch { /* state.db belum ada / python error */ }
  }
  const state: StudioState = {
    snapshot: latestSnapshot(),
    videos: vids,
    activity: act,
    week: wk,
    reports: listFiles(P.insights, ".md", 30, true),
    logs: listFiles(P.logs, ".txt", 25),
    agents: AGENTS.map((key) => ({ key, ready: fs.existsSync(path.join(P.skills, key, "SKILL.md")) })),
    job: jobState(),
    antrean: readQueue(),
    steve: steveInsight(),
    produksi: produksi(jobState().status === "running" && jobState().job === "produksi"),
    health: { env: fs.existsSync(P.env), claude: which("claude") !== null, python: py !== null, pythonCmd: py ? path.basename(py) : "", edgeTts: py ? await hasModule("edge_tts") : false,
      stockKey: envHas("PIXABAY_API_KEY", "PEXELS_API_KEY", "YOUTUBE_API_KEY"), ffmpeg: which("ffmpeg") !== null,
      ytdlp: py ? await hasModule("yt_dlp") : false, aiKey: envHas("CLOUDFLARE_API_TOKEN") && envHas("CLOUDFLARE_ACCOUNT_ID"),
      google: py ? await hasModule("googleapiclient") : false, ytClient: fs.existsSync(path.join(P.rahasia, "client_secret.json")), ytLogin: fs.existsSync(path.join(P.rahasia, "token.json")) },
  };
  return json(state);
}

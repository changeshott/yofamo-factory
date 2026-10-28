import fs from "node:fs";
import path from "node:path";
import { jobState } from "@/lib/server/jobs";
import { json } from "@/lib/server/guard";
import { P, activity, hasEdgeTts, hasStockKey, latestSnapshot, listFiles, pythonCmd, videos, week, which } from "@/lib/server/project";
import type { StudioState } from "@/lib/types";

export const dynamic = "force-dynamic";
const AGENTS = ["steve-analis", "ide-riset", "penulis", "suara", "aset", "editor-capcut", "upload"];

export async function GET() {
  const py = pythonCmd();
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
    health: { env: fs.existsSync(P.env), claude: which("claude") !== null, python: py !== null, pythonCmd: py ? path.basename(py) : "", edgeTts: py ? await hasEdgeTts() : false, stockKey: hasStockKey() },
  };
  return json(state);
}

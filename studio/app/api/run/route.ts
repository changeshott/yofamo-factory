import { guard, json } from "@/lib/server/guard";
import { startJob } from "@/lib/server/jobs";
import type { JobName } from "@/lib/types";

const JOBS: JobName[] = ["fetch", "check", "steve", "ide", "penulis", "suara"];

export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const body = (await req.json().catch(() => ({}))) as { job?: string; arg?: string };
  if (!JOBS.includes(body.job as JobName)) return json({ ok: false, message: "Tugas tidak dikenal." }, 400);
  const r = await startJob(body.job as JobName, String(body.arg ?? ""));
  return json(r, r.ok ? 200 : 409);
}

import { guard, json } from "@/lib/server/guard";
import { stopJob } from "@/lib/server/jobs";

export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const r = stopJob();
  return json(r, r.ok ? 200 : 409);
}

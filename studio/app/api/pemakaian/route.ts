import { spawnSync } from "node:child_process";
import { json } from "@/lib/server/guard";
import { ROOT, pythonCmd } from "@/lib/server/project";

/** Pemakaian token Claude per video (agents/pemakaian.py --json, dari produksi/token-log.jsonl). */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const py = pythonCmd();
  if (!py) return json({ ok: false, message: "Python tidak ditemukan." });
  const r = spawnSync(py, ["agents/pemakaian.py", "--json"], { cwd: ROOT, windowsHide: true, encoding: "utf-8", timeout: 20_000 });
  try { return json({ ok: true, ...JSON.parse(r.stdout || "{}") }); } catch { return json({ ok: false, message: (r.stderr || "gagal membaca pemakaian").slice(0, 200) }); }
}

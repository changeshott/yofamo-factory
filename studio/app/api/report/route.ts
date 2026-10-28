import path from "node:path";
import { json } from "@/lib/server/guard";
import { P, SAFE_FILE, readText } from "@/lib/server/project";

export async function GET(req: Request) {
  const name = new URL(req.url).searchParams.get("name") ?? "";
  if (!SAFE_FILE.test(name) || !name.endsWith(".md")) return json({ error: "laporan tidak ditemukan" }, 404);
  try { return json({ name, text: readText(path.join(P.insights, name)) }); }
  catch { return json({ error: "laporan tidak ditemukan" }, 404); }
}

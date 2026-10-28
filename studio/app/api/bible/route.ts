import fs from "node:fs";
import path from "node:path";
import { guard, json } from "@/lib/server/guard";
import { P, localIso, readText } from "@/lib/server/project";

export async function GET() {
  try { return json({ text: readText(P.bible) }); } catch { return json({ text: "" }); }
}

export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const { text } = (await req.json().catch(() => ({}))) as { text?: unknown };
  if (typeof text !== "string" || !text.trim() || text.length > 200_000) return json({ ok: false, message: "Isi bible kosong, tidak disimpan." }, 400);
  if (fs.existsSync(P.bible)) {
    fs.mkdirSync(P.bibleHistory, { recursive: true });
    fs.copyFileSync(P.bible, path.join(P.bibleHistory, `channel-bible-${localIso().replace(/[-:]/g, "").replace("T", "-")}.md`));
  }
  fs.writeFileSync(P.bible, text, "utf8");
  return json({ ok: true, message: "Bible disimpan." });
}

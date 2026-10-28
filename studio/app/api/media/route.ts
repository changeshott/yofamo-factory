import fs from "node:fs";
import path from "node:path";
import { P, SLUG } from "@/lib/server/project";

const TYPES: Record<string, string> = { "vo.mp3": "audio/mpeg", "captions.srt": "application/x-subrip; charset=utf-8", "words.json": "application/json; charset=utf-8" };

/** File hasil agent untuk satu video (audio, subtitle, timing). Hanya file yang terdaftar. */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const q = new URL(req.url).searchParams, slug = q.get("slug") ?? "", file = q.get("file") ?? "";
  if (!SLUG.test(slug) || !TYPES[file]) return new Response("tidak ditemukan", { status: 404 });
  const full = path.join(P.videos, slug, file);
  try {
    const data = await fs.promises.readFile(full);
    const headers: Record<string, string> = { "Content-Type": TYPES[file], "Cache-Control": "no-store" };
    if (q.get("unduh")) headers["Content-Disposition"] = `attachment; filename="${slug}-${file}"`;
    return new Response(data, { headers });
  } catch {
    return new Response("tidak ditemukan", { status: 404 });
  }
}

import fs from "node:fs";
import path from "node:path";
import { P, SLUG } from "@/lib/server/project";

const TYPES: Record<string, string> = { "vo.mp3": "audio/mpeg", "captions.srt": "application/x-subrip; charset=utf-8", "words.json": "application/json; charset=utf-8" };
const CLIP = /^aset\/\d{2}-(pexels|pixabay|manual)-[\w-]{1,40}\.mp4$/;

/** File hasil agent untuk satu video (audio, subtitle, timing, klip aset). Hanya nama file yang terdaftar. */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const q = new URL(req.url).searchParams, slug = q.get("slug") ?? "", file = q.get("file") ?? "";
  const type = TYPES[file] ?? (CLIP.test(file) ? "video/mp4" : null);
  if (!SLUG.test(slug) || !type) return new Response("tidak ditemukan", { status: 404 });
  const full = path.join(P.videos, slug, ...file.split("/"));
  let size: number;
  try { size = (await fs.promises.stat(full)).size; } catch { return new Response("tidak ditemukan", { status: 404 }); }

  const headers: Record<string, string> = { "Content-Type": type, "Cache-Control": "no-store", "Accept-Ranges": "bytes" };
  if (q.get("unduh")) headers["Content-Disposition"] = `attachment; filename="${slug}-${path.basename(file)}"`;
  const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.get("range") ?? "");
  if (range && size > 0) {
    // video/audio perlu Range supaya bisa digeser
    let start = range[1] ? +range[1] : size - +range[2], end = range[1] && range[2] ? +range[2] : size - 1;
    if (!range[1]) end = size - 1;
    if (start < 0 || start >= size || end < start) return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
    end = Math.min(end, size - 1, start + 8 * 1024 * 1024 - 1); // potongan maksimal 8 MB
    const body = await readSlice(full, start, end);
    return new Response(body, { status: 206, headers: { ...headers, "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(end - start + 1) } });
  }
  return new Response(await fs.promises.readFile(full), { headers: { ...headers, "Content-Length": String(size) } });
}

async function readSlice(file: string, start: number, end: number): Promise<Uint8Array<ArrayBuffer>> {
  const len = end - start + 1;
  const buf = new Uint8Array(new ArrayBuffer(len));
  const fh = await fs.promises.open(file, "r");
  try { await fh.read(buf, 0, len, start); } finally { await fh.close(); }
  return buf;
}

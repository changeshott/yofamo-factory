import fs from "node:fs";
import path from "node:path";
import { guard, json } from "@/lib/server/guard";
import { P, ROOT, SLUG } from "@/lib/server/project";

const DIR = path.join(ROOT, "musik");
const EXT: Record<string, string> = { ".mp3": "audio/mpeg", ".m4a": "audio/mp4", ".wav": "audio/wav", ".ogg": "audio/ogg", ".aac": "audio/aac", ".flac": "audio/flac" };
const SUASANA = ["tegang", "ceria", "misterius", "epik", "haru"];

function daftar() {
  const out: { file: string; nama: string; suasana: string; mb: number; kredit: boolean }[] = [];
  const jalan = (d: string) => {
    let ents: fs.Dirent[] = [];
    try { ents = fs.readdirSync(d, { withFileTypes: true }); } catch { return; }
    for (const e of ents) {
      const full = path.join(d, e.name);
      if (e.isDirectory()) { jalan(full); continue; }
      const ext = path.extname(e.name).toLowerCase();
      if (!EXT[ext]) continue;
      const rel = path.relative(DIR, full).split(path.sep).join("/");
      const folder = rel.includes("/") ? rel.split("/")[0].toLowerCase() : "";
      out.push({ file: rel, nama: path.basename(e.name, ext), suasana: SUASANA.includes(folder) ? folder : SUASANA.find((s) => e.name.toLowerCase().includes(s)) ?? "lainnya",
        mb: Math.round((fs.statSync(full).size / 1048576) * 10) / 10, kredit: fs.existsSync(full.slice(0, -ext.length) + ".txt") });
    }
  };
  jalan(DIR);
  return out.sort((a, b) => a.suasana.localeCompare(b.suasana) || a.nama.localeCompare(b.nama));
}

function aman(rel: string): string | null {
  const full = path.resolve(DIR, rel);
  return full.startsWith(path.resolve(DIR) + path.sep) && EXT[path.extname(full).toLowerCase()] && fs.existsSync(full) ? full : null;
}

/** Perpustakaan musik latar (folder musik/): daftar lagu & putar pratinjau. */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const q = new URL(req.url).searchParams, file = q.get("file");
  if (!file) {
    const pilihan: Record<string, string> = {};
    try {
      for (const s of fs.readdirSync(P.videos)) {
        try { const m = JSON.parse(fs.readFileSync(path.join(P.videos, s, "musik.json"), "utf-8")); if (m.file) pilihan[s] = m.file; } catch { /* belum memilih */ }
      }
    } catch { /* folder videos belum ada */ }
    return json({ lagu: daftar(), pilihan, ada_folder: fs.existsSync(DIR) });
  }
  const full = aman(file);
  if (!full) return new Response("tidak ditemukan", { status: 404 });
  const size = fs.statSync(full).size, type = EXT[path.extname(full).toLowerCase()];
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.get("range") ?? "");
  if (m && size > 0) {
    const start = m[1] ? +m[1] : Math.max(0, size - +m[2]);
    const end = Math.min(m[1] && m[2] ? +m[2] : size - 1, start + 4 * 1024 * 1024 - 1, size - 1);
    const buf = Buffer.alloc(end - start + 1);
    const fh = await fs.promises.open(full, "r");
    try { await fh.read(buf, 0, buf.length, start); } finally { await fh.close(); }
    return new Response(new Uint8Array(buf), { status: 206, headers: { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(buf.length), "Cache-Control": "no-store" } });
  }
  return new Response(new Uint8Array(await fs.promises.readFile(full)), { headers: { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Length": String(size), "Cache-Control": "no-store" } });
}

/** Pilih lagu untuk satu video (videos/<slug>/musik.json). file: path lagu, "tanpa" (tanpa musik), atau "" (otomatis). */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const { slug = "", file = "" } = (await req.json().catch(() => ({}))) as { slug?: string; file?: string };
  if (!SLUG.test(slug) || !fs.existsSync(path.join(P.videos, slug))) return json({ ok: false, message: "Video tidak ditemukan." }, 404);
  const tujuan = path.join(P.videos, slug, "musik.json");
  if (!file) { try { fs.unlinkSync(tujuan); } catch { /* sudah otomatis */ } return json({ ok: true, message: "Musik dipilih otomatis sesuai suasana naskah." }); }
  if (file !== "tanpa" && !aman(file)) return json({ ok: false, message: "Lagu tidak ditemukan di folder musik/." }, 404);
  fs.writeFileSync(tujuan, JSON.stringify({ file, dipilih: new Date().toISOString() }, null, 2), "utf-8");
  return json({ ok: true, message: file === "tanpa" ? "Video ini tanpa musik." : "Lagu dipilih. Rakit ulang video supaya musiknya terpakai." });
}

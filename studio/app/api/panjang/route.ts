import fs from "node:fs";
import path from "node:path";
import { guard, json } from "@/lib/server/guard";
import { PJ, berjalanPanjang, buatPanjang, daftarPanjang, produksiPanjang, setStatus, unggahPanjang } from "@/lib/server/panjang";

const SLUG = /^[a-z0-9-]{3,80}$/;
const FILE: Record<string, string> = { "export/final.mp4": "video/mp4", "export/thumbnail.jpg": "image/jpeg", "export/lembar.jpg": "image/jpeg", "naskah.md": "text/markdown; charset=utf-8" };

/** Ruang Animasi: daftar video panjang + produksi, atau satu file (video/thumbnail/lembar/naskah). */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const q = new URL(req.url).searchParams, slug = q.get("slug") ?? "", file = q.get("file") ?? "";
  if (!file) return json({ videos: daftarPanjang(), produksi: produksiPanjang(), berjalan: !!berjalanPanjang() });
  if (!SLUG.test(slug) || !FILE[file]) return new Response("tidak ditemukan", { status: 404 });
  const full = path.join(PJ, slug, file);
  if (!fs.existsSync(full)) return new Response("tidak ditemukan", { status: 404 });
  const size = fs.statSync(full).size, type = FILE[file];
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.get("range") ?? "");
  if (m && size > 0) {
    const start = m[1] ? +m[1] : Math.max(0, size - +m[2]);
    const end = Math.min(m[1] && m[2] ? +m[2] : size - 1, start + 4 * 1024 * 1024 - 1, size - 1);
    const buf = Buffer.alloc(end - start + 1);
    const fh = await fs.promises.open(full, "r");
    try { await fh.read(buf, 0, buf.length, start); } finally { await fh.close(); }
    return new Response(new Uint8Array(buf), { status: 206, headers: { "Content-Type": type, "Accept-Ranges": "bytes", "Content-Range": `bytes ${start}-${end}/${size}`, "Content-Length": String(buf.length), "Cache-Control": "no-store" } });
  }
  return new Response(new Uint8Array(await fs.promises.readFile(full)), { headers: { "Content-Type": type, "Content-Length": String(size), "Cache-Control": "no-store" } });
}

/** aksi: buat {tema} · lanjut {slug} · setujui {slug} · tolak {slug} · unggah {slug, jadwal?} */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const b = (await req.json().catch(() => ({}))) as { aksi?: string; tema?: string; slug?: string; jadwal?: string };
  const slug = b.slug ?? "";
  try {
    if (b.aksi === "buat") return json(buatPanjang(String(b.tema ?? "")));
    if (!SLUG.test(slug) || !fs.existsSync(path.join(PJ, slug))) return json({ ok: false, message: "Video tidak ditemukan." }, 404);
    const v = daftarPanjang().find((x) => x.slug === slug);
    if (b.aksi === "lanjut") return json(buatPanjang("", slug));
    if (b.aksi === "setujui") {
      if (v?.status !== "draft" || !v.final) return json({ ok: false, message: "Hanya video jadi (draft) yang bisa disetujui." });
      setStatus(slug, "export", "disetujui Zona di Studio"); return json({ ok: true, message: "Disetujui. Uli bisa mengunggahnya." });
    }
    if (b.aksi === "tolak") { setStatus(slug, "ditolak", "ditolak Zona di Studio"); return json({ ok: true, message: "Video ditandai ditolak." }); }
    if (b.aksi === "unggah") {
      if (v?.status !== "export") return json({ ok: false, message: "Setujui videonya dulu." });
      const jadwal = String(b.jadwal ?? "");
      if (jadwal && !/^\d{4}-\d\d-\d\dT\d\d:\d\d$/.test(jadwal)) return json({ ok: false, message: "Format jadwal: 2026-11-03T19:30" });
      return json(unggahPanjang(slug, jadwal));
    }
    return json({ ok: false, message: "Aksi tidak dikenal." }, 400);
  } catch (e) {
    return json({ ok: false, message: (e as Error).message.slice(0, 200) }, 500);
  }
}

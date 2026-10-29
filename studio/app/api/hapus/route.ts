import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { jobState } from "@/lib/server/jobs";
import { guard, json } from "@/lib/server/guard";
import { P, ROOT, SAFE_FILE, SLUG, pabrik, pythonCmd } from "@/lib/server/project";

type Body = { jenis?: string; nama?: string; laporan?: boolean };

/** Kontrol Zona: hapus hasil karyawan. Tidak bisa dibatalkan, jadi UI selalu minta konfirmasi dulu. */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const { jenis = "", nama = "", laporan = false } = (await req.json().catch(() => ({}))) as Body;
  const job = jobState(), running = job.status === "running";
  const py = pythonCmd();
  const busyWith = (slug: string) => running && (job.arg ?? "").split("|")[0] === slug;
  const hapusVideo = (slug: string) => execFileSync(py!, [P.pabrik, "hapus", slug, "--ya"], { cwd: ROOT, windowsHide: true });

  try {
    if (jenis === "video") {
      if (!py) return json({ ok: false, message: "Python tidak ditemukan." }, 500);
      if (!SLUG.test(nama)) return json({ ok: false, message: "Video tidak ditemukan." }, 404);
      if (busyWith(nama) || (running && job.job === "produksi")) return json({ ok: false, message: "Video ini sedang dikerjakan. Hentikan tugasnya dulu." }, 409);
      hapusVideo(nama);
      return json({ ok: true, message: "Video dan semua filenya dihapus." });
    }
    if (jenis === "produksi") {
      if (!/^[\w-]{3,40}$/.test(nama)) return json({ ok: false, message: "Catatan tidak ditemukan." }, 404);
      if (running && job.job === "produksi") return json({ ok: false, message: "Produksi sedang berjalan. Hentikan dulu." }, 409);
      fs.rmSync(path.join(P.produksi, `${nama}.json`), { force: true });
      return json({ ok: true, message: "Catatan produksi dihapus." });
    }
    if (jenis === "log") {
      if (nama === "*") {
        for (const f of fs.readdirSync(P.logs)) if (f.endsWith(".txt") && !(running && f === job.log)) fs.rmSync(path.join(P.logs, f), { force: true });
        return json({ ok: true, message: "Semua log dihapus." });
      }
      if (!SAFE_FILE.test(nama) || !nama.endsWith(".txt")) return json({ ok: false, message: "Log tidak ditemukan." }, 404);
      if (running && nama === job.log) return json({ ok: false, message: "Log ini sedang ditulis." }, 409);
      fs.rmSync(path.join(P.logs, nama), { force: true });
      return json({ ok: true, message: "Log dihapus." });
    }
    if (jenis === "laporan") {
      if (!SAFE_FILE.test(nama) || !nama.endsWith(".md")) return json({ ok: false, message: "Laporan tidak ditemukan." }, 404);
      fs.rmSync(path.join(P.insights, nama), { force: true });
      return json({ ok: true, message: "Laporan Steve dihapus." });
    }
    if (jenis === "cache") {
      fs.rmSync(P.cache, { recursive: true, force: true });
      return json({ ok: true, message: "Cache unduhan dikosongkan." });
    }
    if (jenis === "semua") {
      if (running) return json({ ok: false, message: "Masih ada tugas berjalan. Hentikan dulu." }, 409);
      if (!py) return json({ ok: false, message: "Python tidak ditemukan." }, 500);
      const rows = await pabrik<{ slug: string }[]>(["list", "--json"]).catch(() => []);
      for (const r of rows) hapusVideo(r.slug);
      for (const d of fs.existsSync(P.videos) ? fs.readdirSync(P.videos) : []) if (SLUG.test(d)) fs.rmSync(path.join(P.videos, d), { recursive: true, force: true });
      for (const dir of [P.produksi]) for (const f of fs.existsSync(dir) ? fs.readdirSync(dir) : []) fs.rmSync(path.join(dir, f), { recursive: true, force: true });
      for (const f of fs.existsSync(P.logs) ? fs.readdirSync(P.logs) : []) if (f.endsWith(".txt")) fs.rmSync(path.join(P.logs, f), { force: true });
      fs.rmSync(P.cache, { recursive: true, force: true });
      if (laporan) for (const f of fs.readdirSync(P.insights)) if (f.endsWith(".md")) fs.rmSync(path.join(P.insights, f), { force: true });
      return json({ ok: true, message: `Semua hasil dihapus (${rows.length} video).` });
    }
    return json({ ok: false, message: "Jenis tidak dikenal." }, 400);
  } catch (e) {
    return json({ ok: false, message: `Gagal menghapus: ${(e as Error).message.slice(0, 200)}` }, 500);
  }
}

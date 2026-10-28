import { execFileSync } from "node:child_process";
import { guard, json } from "@/lib/server/guard";
import { MANUAL_MOVES, P, ROOT, SLUG, pabrik, pythonCmd } from "@/lib/server/project";
import type { VideoStatus } from "@/lib/types";

/** Ubah status video (setujui, tolak, tandai terbit, dst). */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const { slug = "", status = "" } = (await req.json().catch(() => ({}))) as { slug?: string; status?: string };
  const py = pythonCmd();
  if (!py) return json({ ok: false, message: "Python tidak ditemukan." }, 500);
  if (!SLUG.test(slug)) return json({ ok: false, message: "Video tidak ditemukan." }, 404);
  const rows = await pabrik<{ slug: string; status: VideoStatus }[]>(["list", "--json"]);
  const v = rows.find((r) => r.slug === slug);
  if (!v) return json({ ok: false, message: "Video tidak ditemukan." }, 404);
  if (!(MANUAL_MOVES[v.status] ?? []).includes(status as VideoStatus))
    return json({ ok: false, message: `Tidak bisa mengubah ${v.status} menjadi ${status}.` }, 409);
  execFileSync(py, [P.pabrik, "set", slug, status, "--note", "diubah dari Studio"], { cwd: ROOT, windowsHide: true });
  return json({ ok: true, message: "Tersimpan." });
}

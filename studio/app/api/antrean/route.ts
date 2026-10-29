import { guard, json } from "@/lib/server/guard";
import { dequeue, enqueue } from "@/lib/server/jobs";

/** Antrean "Buat video": tambah permintaan (langsung jalan kalau kantor sedang kosong) atau hapus dari antrean. */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const b = (await req.json().catch(() => ({}))) as { aksi?: string; teks?: string; suara?: string; visual?: string; id?: string };
  if (b.aksi === "tambah") {
    const r = await enqueue(String(b.teks ?? ""), String(b.suara ?? ""), String(b.visual ?? ""));
    return json(r, r.ok ? 200 : 400);
  }
  if (b.aksi === "hapus") return json({ ok: dequeue(String(b.id ?? "")), message: "Dihapus dari antrean." });
  return json({ ok: false, message: "Aksi tidak dikenal." }, 400);
}

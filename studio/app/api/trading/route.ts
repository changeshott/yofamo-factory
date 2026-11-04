import { guard, json } from "@/lib/server/guard";
import { analisaDalam, bacaAnalisa, beli, jual, lewati, loop, pindai, simpanAturan, statusTrading } from "@/lib/server/trading";

export const dynamic = "force-dynamic";

/** Ruang Trading: status (sinyal, posisi, statistik) atau satu analisa mendalam (?analisa=<id>). */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const id = new URL(req.url).searchParams.get("analisa");
  if (id) return json({ teks: bacaAnalisa(id) });
  return json(statusTrading());
}

/** aksi: pindai {pasar} · loop {nyala} · beli {sinyal, harga, usd} · jual {posisi, harga} · lewati {sinyal} · analisa {id} · aturan {...} */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const b = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  try {
    switch (b.aksi) {
      case "pindai": return json(pindai(String(b.pasar ?? "meme")));
      case "loop": return json(loop(!!b.nyala));
      case "beli": return json(beli(String(b.sinyal ?? ""), b.harga, b.usd));
      case "jual": return json(jual(String(b.posisi ?? ""), b.harga));
      case "lewati": return json(lewati(String(b.sinyal ?? "")));
      case "analisa": return json(analisaDalam(String(b.id ?? "")));
      case "aturan": return json(simpanAturan((b.aturan ?? {}) as Record<string, unknown>));
      default: return json({ ok: false, message: "Aksi tidak dikenal." }, 400);
    }
  } catch (e) {
    return json({ ok: false, message: (e as Error).message.slice(0, 220) }, 500);
  }
}

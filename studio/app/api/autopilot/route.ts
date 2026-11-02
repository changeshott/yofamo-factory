import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { guard, json } from "@/lib/server/guard";
import { P, ROOT } from "@/lib/server/project";
import { autopilotBerjalan, jalankanAutopilot } from "@/lib/server/autopilot";

const CONFIG = path.join(ROOT, "bible", "autopilot.json");
const STATE = path.join(P.produksi, "autopilot.json");
const JADWAL = path.join(ROOT, "insights", "jadwal.json");

const baca = (f: string) => { try { return JSON.parse(fs.readFileSync(f, "utf-8")); } catch { return null; } };
const hariIni = () => new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 10);

let tugasCache: { ada: boolean | null; at: number } = { ada: null, at: 0 };
function tugasTerpasang(): boolean | null {
  if (process.platform !== "win32") return null;
  if (Date.now() - tugasCache.at < 60_000) return tugasCache.ada;
  const r = spawnSync("schtasks", ["/Query", "/TN", "Yofamo Autopilot"], { windowsHide: true, encoding: "utf-8" });
  tugasCache = { ada: r.status === 0, at: Date.now() };
  return tugasCache.ada;
}

const berjalan = autopilotBerjalan;

/** Status autopilot: pengaturan, jadwal tayang (hari ini & besok), slot yang sudah terisi, log terakhir. */
export async function GET(req: Request) {
  if (!["127.0.0.1:3210", "localhost:3210"].includes(req.headers.get("host") ?? "")) return new Response("ditolak", { status: 403 });
  const cfg = baca(CONFIG) ?? {}, st = baca(STATE) ?? {}, jd = baca(JADWAL) ?? {};
  const hari = hariIni(), besok = new Date(Date.now() + 31 * 3600_000).toISOString().slice(0, 10);
  const slot = [hari, besok].map((d) => ({
    tanggal: d,
    slot: ((jd.slot ?? {})[d] ?? []).slice(0, cfg.video_per_hari ?? 3).map((s: { jam: string; eksplorasi: boolean; alasan: string }) => ({ ...s, isi: (st.slot ?? {})[`${d} ${s.jam}`] ?? null })),
  }));
  let log: string[] = [];
  try { log = fs.readFileSync(path.join(P.logs, `autopilot-${hari}.txt`), "utf-8").trim().split("\n").slice(-14); } catch { /* belum ada putaran hari ini */ }
  return json({
    config: cfg, slot, catatan: jd.catatan ?? [], jadwal_dibuat: jd.dibuat ?? null,
    produksi_hari_ini: (st.produksi ?? {})[hari] ?? 0, putaran_terakhir: st.putaran_terakhir ?? null, jeda_sampai: st.jeda_sampai ?? null,
    menunggu_zona: st.menunggu_zona ?? {}, berjalan: berjalan(), tugas: tugasTerpasang(), log,
  });
}

/** Ubah pengaturan autopilot (aktif, video per hari, setujui otomatis, skor minimal) atau jalankan satu putaran sekarang. */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const b = (await req.json().catch(() => ({}))) as { aktif?: boolean; video_per_hari?: number; isi_hari?: number; setujui_otomatis?: boolean; skor_qc_min?: number; jalan?: boolean };
  if (b.jalan) return json(jalankanAutopilot());
  const cfg = baca(CONFIG) ?? {};
  if (typeof b.aktif === "boolean") cfg.aktif = b.aktif;
  if (typeof b.video_per_hari === "number") cfg.video_per_hari = Math.max(1, Math.min(6, Math.round(b.video_per_hari)));
  if (typeof b.isi_hari === "number") cfg.isi_hari = Math.max(1, Math.min(3, Math.round(b.isi_hari)));
  if (typeof b.setujui_otomatis === "boolean") cfg.setujui_otomatis = b.setujui_otomatis;
  if (typeof b.skor_qc_min === "number") cfg.skor_qc_min = Math.max(5, Math.min(10, Math.round(b.skor_qc_min)));
  fs.writeFileSync(CONFIG, JSON.stringify(cfg, null, 2) + "\n", "utf-8");
  if (b.aktif === true) jalankanAutopilot();
  return json({ ok: true, message: typeof b.aktif === "boolean" ? (b.aktif ? "Autopilot aktif dan mulai bekerja." : "Autopilot dimatikan (putaran yang sedang jalan diselesaikan dulu).") : "Pengaturan autopilot disimpan." });
}

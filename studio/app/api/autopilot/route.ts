import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { guard, json } from "@/lib/server/guard";
import { P, ROOT } from "@/lib/server/project";
import { autopilotBerjalan, autopilotPanjangBerjalan, jalankanAutopilot, jalankanAutopilotPanjang } from "@/lib/server/autopilot";

const CONFIG = path.join(ROOT, "bible", "autopilot.json");
const STATE = path.join(P.produksi, "autopilot.json");
const JADWAL = path.join(ROOT, "insights", "jadwal.json");
const STATE_PJ = path.join(P.produksi, "autopilot-panjang.json");
const BAWAAN_PJ = { aktif: true, video_per_hari: 1, isi_hari: 2, setujui_otomatis: true, skor_qc_min: 7, maks_produksi_per_hari: 2, jam: "", arahan_tema: "" };

/** Status autopilot video panjang untuk panel Ruang Animasi. */
function statusPanjang(cfg: { panjang?: Record<string, unknown> }) {
  const st = baca(STATE_PJ) ?? {}, hari = hariIni();
  let log: string[] = [];
  try { log = fs.readFileSync(path.join(P.logs, `autopilot-panjang-${hari}.txt`), "utf-8").trim().split("\n").slice(-10); } catch { /* belum ada putaran hari ini */ }
  return {
    config: { ...BAWAAN_PJ, ...(cfg.panjang ?? {}) },
    slot: ((st.jadwal ?? []) as string[]).map((w) => ({ waktu: w, isi: (st.slot ?? {})[w] ?? null })),
    produksi_hari_ini: (st.produksi ?? {})[hari] ?? 0, putaran_terakhir: st.putaran_terakhir ?? null, jeda_sampai: st.jeda_sampai ?? null,
    masalah: st.masalah ?? null, menunggu_zona: st.menunggu_zona ?? {}, berjalan: autopilotPanjangBerjalan(), log,
  };
}

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
    slot: ((jd.slot ?? {})[d] ?? []).slice(0, cfg.video_per_hari ?? 3).map((s: { jam: string; eksplorasi: boolean; alasan: string }) => {
      const ganti: string | undefined = (st.pengganti ?? {})[`${d} ${s.jam}`];
      return ganti ? { ...s, jam: ganti.slice(11), alasan: `pengganti jam ${s.jam} yang terlewat`, isi: (st.slot ?? {})[ganti] ?? null } : { ...s, isi: (st.slot ?? {})[`${d} ${s.jam}`] ?? null };
    }),
  }));
  let log: string[] = [];
  try { log = fs.readFileSync(path.join(P.logs, `autopilot-${hari}.txt`), "utf-8").trim().split("\n").slice(-14); } catch { /* belum ada putaran hari ini */ }
  return json({
    config: cfg, slot, catatan: jd.catatan ?? [], jadwal_dibuat: jd.dibuat ?? null,
    produksi_hari_ini: (st.produksi ?? {})[hari] ?? 0, putaran_terakhir: st.putaran_terakhir ?? null, jeda_sampai: st.jeda_sampai ?? null, masalah: st.masalah ?? null,
    menunggu_zona: st.menunggu_zona ?? {}, berjalan: berjalan(), tugas: tugasTerpasang(), log, selesai: st.selesai ?? null,
    panjang: statusPanjang(cfg),
  });
}

/** Ubah pengaturan autopilot (aktif, video per hari, setujui otomatis, skor minimal) atau jalankan satu putaran sekarang. */
export async function POST(req: Request) {
  const denied = guard(req); if (denied) return denied;
  const b = (await req.json().catch(() => ({}))) as { aktif?: boolean; video_per_hari?: number; isi_hari?: number; setujui_otomatis?: boolean; skor_qc_min?: number; jalan?: boolean; jalan_saat_studio_dibuka?: boolean;
    panjang?: { aktif?: boolean; video_per_hari?: number; setujui_otomatis?: boolean; skor_qc_min?: number; jam?: string; jalan?: boolean } };
  if (b.jalan) return json(jalankanAutopilot(true));
  const cfg = baca(CONFIG) ?? {};
  if (b.panjang) {
    const q = b.panjang, pj = { ...BAWAAN_PJ, ...(cfg.panjang ?? {}) };
    if (q.jalan) return json(jalankanAutopilotPanjang(true));
    if (typeof q.aktif === "boolean") pj.aktif = q.aktif;
    if (typeof q.video_per_hari === "number") pj.video_per_hari = Math.max(1, Math.min(2, Math.round(q.video_per_hari)));
    if (typeof q.setujui_otomatis === "boolean") pj.setujui_otomatis = q.setujui_otomatis;
    if (typeof q.skor_qc_min === "number") pj.skor_qc_min = Math.max(5, Math.min(10, Math.round(q.skor_qc_min)));
    if (typeof q.jam === "string" && (q.jam === "" || /^([01]\d|2[0-3]):[0-5]\d$/.test(q.jam))) pj.jam = q.jam;
    cfg.panjang = pj;
    fs.writeFileSync(CONFIG, JSON.stringify(cfg, null, 2) + "\n", "utf-8");
    if (q.aktif === true) jalankanAutopilotPanjang(true);
    return json({ ok: true, message: typeof q.aktif === "boolean" ? (q.aktif ? "Autopilot video panjang aktif: 1 video panjang per hari dibuat & dijadwalkan otomatis." : "Autopilot video panjang dimatikan (video yang sedang dibuat diselesaikan dulu).") : "Pengaturan video panjang disimpan." });
  }
  if (typeof b.aktif === "boolean") cfg.aktif = b.aktif;
  if (typeof b.video_per_hari === "number") cfg.video_per_hari = Math.max(1, Math.min(6, Math.round(b.video_per_hari)));
  if (typeof b.isi_hari === "number") cfg.isi_hari = Math.max(1, Math.min(3, Math.round(b.isi_hari)));
  if (typeof b.setujui_otomatis === "boolean") cfg.setujui_otomatis = b.setujui_otomatis;
  if (typeof b.jalan_saat_studio_dibuka === "boolean") cfg.jalan_saat_studio_dibuka = b.jalan_saat_studio_dibuka;
  if (typeof b.skor_qc_min === "number") cfg.skor_qc_min = Math.max(5, Math.min(10, Math.round(b.skor_qc_min)));
  fs.writeFileSync(CONFIG, JSON.stringify(cfg, null, 2) + "\n", "utf-8");
  if (b.aktif === true) jalankanAutopilot(true);
  return json({ ok: true, message: typeof b.aktif === "boolean" ? (b.aktif ? "Autopilot aktif dan mulai bekerja." : "Autopilot dimatikan: video yang sedang dibuat diselesaikan dulu, lalu berhenti.") : "Pengaturan autopilot disimpan." });
}

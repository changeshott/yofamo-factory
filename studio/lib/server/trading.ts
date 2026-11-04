import "server-only";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { ROOT, agentEnv, jalankanLatar, pythonCmd } from "./project";
import { pidHidup } from "./autopilot";

/** Ruang Trading: analisa memecoin (FOMO) & gold. Hanya membaca & mencatat — tidak pernah mengirim order. */
export const TR = path.join(ROOT, "trading");
const CFG = path.join(ROOT, "bible", "trading.json");
const baca = <T = Record<string, unknown>>(f: string): T | null => { try { return JSON.parse(fs.readFileSync(f, "utf-8")) as T; } catch { return null; } };

export interface Posisi {
  id: string; sinyal: string; pasar: string; simbol: string; token: string; arah: string; mode: "latihan" | "nyata"; dibuka: string; masuk: number; stop: number; target: number;
  posisi_usd: number; biaya_pp_pct: number; rugi_di_stop_usd: number; status: string; harga_kini?: number; pnl_kini_usd?: number; keluar?: number; ditutup?: string; pnl_usd?: number; R?: number;
}
export interface Jurnal { posisi: Posisi[]; peringatan: { waktu: string; posisi: string; jenis: string; teks: string }[] }

const kunciHidup = (nama: string) => { const k = baca<{ pid?: number }>(path.join(TR, nama)); return !!k && pidHidup(Number(k.pid)); };
export const pindaiBerjalan = () => kunciHidup("pindai.lock");
export const loopBerjalan = () => kunciHidup("loop.lock");

export function statusKantorTrading(): { tahap: string | null } | null {
  const s = baca<{ tahap?: string | null; pid?: number }>(path.join(TR, "status.json"));
  return s?.tahap && pidHidup(Number(s.pid)) ? { tahap: s.tahap } : null;
}

const WIB = () => new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 10);

function statistik(j: Jurnal) {
  const out: Record<string, unknown> = {};
  for (const mode of ["latihan", "nyata"] as const) {
    const ps = j.posisi.filter((p) => p.mode === mode && p.status !== "terbuka");
    const menang = ps.filter((p) => (p.pnl_usd ?? 0) > 0).length, total = ps.reduce((s, p) => s + (p.pnl_usd ?? 0), 0);
    const hari = new Set(ps.map((p) => (p.ditutup ?? "").slice(0, 10)));
    out[mode] = {
      trade: ps.length, menang, kalah: ps.length - menang, winrate: ps.length ? Math.round((menang / ps.length) * 1000) / 10 : null,
      rataR: ps.length ? Math.round((ps.reduce((s, p) => s + (p.R ?? 0), 0) / ps.length) * 100) / 100 : null,
      pnl: Math.round(total * 100) / 100, hariIni: Math.round(ps.filter((p) => (p.ditutup ?? "").startsWith(WIB())).reduce((s, p) => s + (p.pnl_usd ?? 0), 0) * 100) / 100,
      perHari: hari.size ? Math.round((total / hari.size) * 100) / 100 : null, hariAktif: hari.size,
      terbuka: j.posisi.filter((p) => p.mode === mode && p.status === "terbuka").length,
    };
  }
  return out;
}

export function statusTrading() {
  const j = baca<Jurnal>(path.join(TR, "jurnal.json")) ?? { posisi: [], peringatan: [] };
  const sdir = path.join(TR, "sinyal");
  let files: string[] = [];
  try { files = fs.readdirSync(sdir).filter((f) => /^[\w-]+\.json$/.test(f)); } catch { /* belum ada */ }
  const sinyal = files.map((f) => ({ f, t: fs.statSync(path.join(sdir, f)).mtimeMs })).sort((a, b) => b.t - a.t).slice(0, 12)
    .map(({ f }) => baca(path.join(sdir, f))).filter(Boolean);
  let analisa: string[] = [];
  try { analisa = fs.readdirSync(path.join(TR, "analisa")).filter((f) => f.endsWith(".md")).map((f) => f.slice(0, -3)); } catch { /* belum ada */ }
  return {
    cfg: baca(CFG), papan: baca(path.join(TR, "papan.json")), sinyal, analisa,
    posisi: [...j.posisi].reverse().slice(0, 40), peringatan: [...(j.peringatan ?? [])].reverse().slice(0, 8), statistik: statistik(j),
    pindai: pindaiBerjalan(), loop: loopBerjalan(), kantor: statusKantorTrading(),
  };
}

const stamp = () => new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");
const ID = /^[\w:-]{3,80}$/;

export function pindai(pasar: string) {
  if (pindaiBerjalan()) return { ok: false, message: "Pindaian sedang berjalan." };
  const p = ["meme", "gold", "semua"].includes(pasar) ? pasar : "meme";
  const r = jalankanLatar(["agents/trading/meja.py", "pindai", "--pasar", p], `trading-pindai-${stamp()}.txt`);
  return r.ok ? { ok: true, message: p === "gold" ? "Tim memindai gold…" : "Tim memindai memecoin… (±1–2 menit)" } : r;
}

function ubahCfg(f: (c: Record<string, unknown>) => void) {
  const c = baca<Record<string, unknown>>(CFG);
  if (!c) return;
  f(c);
  fs.writeFileSync(CFG, JSON.stringify(c, null, 2), "utf-8");
}

const gt = globalThis as unknown as { __yofamoTrading?: number };
/** Studio dibuka/terbuka → pantau otomatis menyala sendiri (kalau Zona tidak mematikannya). Dicoba paling sering tiap 5 menit. */
export function tradingOtomatis(): void {
  const c = baca<{ otomatis_saat_studio_dibuka?: boolean }>(CFG);
  if (!c?.otomatis_saat_studio_dibuka || loopBerjalan()) return;
  if (gt.__yofamoTrading && Date.now() - gt.__yofamoTrading < 5 * 60_000) return;
  gt.__yofamoTrading = Date.now();
  try { fs.rmSync(path.join(TR, "berhenti"), { force: true }); } catch { /* tidak apa */ }
  jalankanLatar(["agents/trading/meja.py", "loop"], `trading-loop-${stamp()}.txt`);
}

export function loop(nyala: boolean) {
  ubahCfg((c) => { c.otomatis_saat_studio_dibuka = nyala; });
  if (!nyala) { fs.mkdirSync(TR, { recursive: true }); fs.writeFileSync(path.join(TR, "berhenti"), "1"); return { ok: true, message: "Pantau otomatis dimatikan (juga tidak menyala sendiri saat Studio dibuka)." }; }
  if (loopBerjalan()) return { ok: false, message: "Pantau otomatis sudah menyala." };
  const r = jalankanLatar(["agents/trading/meja.py", "loop"], `trading-loop-${stamp()}.txt`);
  return r.ok ? { ok: true, message: "Pantau otomatis menyala: pindai tiap beberapa menit & memantau posisi selama Studio/laptop hidup." } : r;
}

function meja(args: string[]) {
  const py = pythonCmd();
  if (!py) throw new Error("Python tidak ditemukan.");
  const r = spawnSync(py, ["agents/trading/meja.py", ...args], { cwd: ROOT, env: agentEnv(), windowsHide: true, encoding: "utf-8", timeout: 60_000 });
  if (r.status !== 0) throw new Error(String(r.stderr || r.stdout || "gagal").trim().split("\n").slice(-2).join(" ").slice(0, 220));
  return String(r.stdout || "").trim().split("\n").slice(-1)[0]?.replace(/^\[\w+\]\s*/, "") ?? "";
}

const angka = (x: unknown) => { const n = Number(String(x ?? "").replace(",", ".")); return Number.isFinite(n) && n > 0 ? n : null; };

export function beli(sinyal: string, harga: unknown, usd: unknown) {
  const h = angka(harga), u = angka(usd);
  if (!ID.test(sinyal) || !h || !u) return { ok: false, message: "Isi harga beli & jumlah dolar dari FOMO." };
  return { ok: true, message: meja(["beli", sinyal, "--harga", String(h), "--usd", String(u)]) };
}
export function jual(posisi: string, harga: unknown) {
  const h = angka(harga);
  if (!ID.test(posisi) || !h) return { ok: false, message: "Isi harga jual dari FOMO." };
  return { ok: true, message: meja(["jual", posisi, "--harga", String(h)]) };
}
export function lewati(sinyal: string) {
  if (!ID.test(sinyal)) return { ok: false, message: "Sinyal tidak dikenal." };
  meja(["lewati", sinyal]); return { ok: true, message: "Sinyal dilewati." };
}
export function notifikasi(aksi: "buat" | "hapus" | "tes") {
  if (aksi === "buat") {
    const huruf = "abcdefghijkmnpqrstuvwxyz23456789";
    const topik = "yofamo-" + Array.from({ length: 20 }, () => huruf[Math.floor(Math.random() * huruf.length)]).join("");
    ubahCfg((c) => { c.notifikasi = { ...(c.notifikasi as object ?? {}), ntfy_topik: topik }; });
    return { ok: true, message: `Topik dibuat: ${topik}. Pasang aplikasi ntfy di HP → + → Subscribe → isi topik ini.` };
  }
  if (aksi === "hapus") { ubahCfg((c) => { c.notifikasi = { ntfy_topik: "" }; }); return { ok: true, message: "Notifikasi HP dimatikan." }; }
  const py = pythonCmd();
  if (!py) return { ok: false, message: "Python tidak ditemukan." };
  const r = spawnSync(py, ["agents/trading/notif.py", "tes"], { cwd: ROOT, env: agentEnv(), windowsHide: true, encoding: "utf-8", timeout: 30_000 });
  return { ok: r.status === 0, message: r.status === 0 ? "Pesan tes terkirim. Cek HP-mu." : "Belum terkirim: cek internet & topik." };
}

export function analisaDalam(id: string) {
  if (!ID.test(id)) return { ok: false, message: "Tidak dikenal." };
  const r = jalankanLatar(["agents/trading/analisa_dalam.py", id], `trading-analisa-${stamp()}.txt`);
  return r.ok ? { ok: true, message: "Nadia menganalisa narasi, berita & tanda bahaya (±3–6 menit, memakai kuota Claude)." } : r;
}
export function bacaAnalisa(id: string): string | null {
  if (!ID.test(id)) return null;
  try { return fs.readFileSync(path.join(TR, "analisa", `${id}.md`), "utf-8"); } catch { return null; }
}

/** Aturan yang boleh diubah Zona dari Studio, dengan batas aman. */
const BATAS: Record<string, [number, number]> = {
  modal_usd: [5, 100000], risiko_per_trade_usd: [0.1, 1000], batas_rugi_harian_usd: [0.1, 5000], maks_trade_harian: [1, 20],
  maks_porsi_modal: [0.05, 1], min_peluang_target_pct: [20, 90], target_harian_usd: [0.1, 10000], min_ev_r: [0, 2], pantau_menit: [3, 120], biaya_fomo_per_sisi_pct: [0, 5],
};
export function simpanAturan(ubah: Record<string, unknown>) {
  const c = baca<Record<string, unknown>>(CFG);
  if (!c) return { ok: false, message: "bible/trading.json tidak terbaca." };
  for (const [k, [lo, hi]] of Object.entries(BATAS)) {
    if (ubah[k] === undefined || ubah[k] === "") continue;
    const n = Number(ubah[k]);
    if (!Number.isFinite(n) || n < lo || n > hi) return { ok: false, message: `${k} harus antara ${lo} dan ${hi}.` };
    c[k] = n;
  }
  if (ubah.mode === "nyata" || ubah.mode === "latihan") {
    if (ubah.mode === "nyata" && ubah.konfirmasi !== "SAYA PAHAM RISIKONYA") return { ok: false, message: "Ketik SAYA PAHAM RISIKONYA untuk mode nyata." };
    c.mode = ubah.mode;
  }
  if (Number(c.risiko_per_trade_usd) > Number(c.batas_rugi_harian_usd)) return { ok: false, message: "Risiko per trade tidak boleh lebih besar dari batas rugi harian." };
  fs.writeFileSync(CFG, JSON.stringify(c, null, 2), "utf-8");
  return { ok: true, message: "Aturan disimpan." };
}

import "server-only";
import fs from "node:fs";
import path from "node:path";
import { P, ROOT, jalankanLatar } from "./project";

const g = globalThis as unknown as { __yofamoAutopilot?: number; __yofamoPoll?: number; __yofamoPanjang?: number };
const DIBUKA = 10 * 60_000;   // tidak ada yang membuka Studio selama ≥ 10 menit → permintaan berikutnya = "Studio dibuka"
const JEDA = 55 * 60_000;

const baca = (f: string) => { try { return JSON.parse(fs.readFileSync(f, "utf-8")); } catch { return null; } };

/** Proses dengan PID ini masih hidup? (Node: sinyal 0 hanya mengecek, tidak mematikan, juga di Windows.) */
export function pidHidup(pid: number): boolean {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; } catch (e) { return (e as NodeJS.ErrnoException).code === "EPERM"; }
}

/** Kunci file Python (agents/kunci.py) masih dipegang proses yang hidup? */
export function kunciAktif(nama: string): { pid: number; nama: string } | null {
  const k = baca(path.join(P.produksi, nama));
  return k && pidHidup(Number(k.pid)) ? { pid: Number(k.pid), nama: String(k.nama ?? "") } : null;
}

export const autopilotBerjalan = () => kunciAktif("autopilot.lock") !== null;

/** Untuk kantor: autopilot sedang mengerjakan apa (ditulis agents/autopilot.py ke produksi/autopilot-kerja.json). */
export function statusKantorAutopilot(): { berjalan: boolean; kerja: string; slug: string | null } | null {
  if (!autopilotBerjalan()) return null;
  const k = baca(path.join(P.produksi, "autopilot-kerja.json"));
  return { berjalan: true, kerja: typeof k?.kerja === "string" ? k.kerja : "", slug: typeof k?.slug === "string" ? k.slug : null };
}

export function jalankanAutopilot(manual = false): { ok: boolean; message: string } {
  if (autopilotBerjalan()) return { ok: false, message: "Autopilot sedang bekerja. Tunggu putaran ini selesai." };
  const tgl = new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 10);
  const r = jalankanLatar(["agents/autopilot.py", "jalan", ...(manual ? ["--mulai"] : [])], `autopilot-latar-${tgl}.txt`);
  if (!r.ok) return r;
  g.__yofamoAutopilot = Date.now();
  return { ok: true, message: "Autopilot mulai bekerja. Kemajuan muncul di log dan di Produksi." };
}

export const autopilotPanjangBerjalan = () => kunciAktif("autopilot-panjang.lock") !== null;

/** Autopilot video panjang (agents/panjang/autopilot_panjang.py): 1 video panjang/hari, punya kunci & putaran sendiri. */
export function jalankanAutopilotPanjang(manual = false): { ok: boolean; message: string } {
  if (autopilotPanjangBerjalan()) return { ok: false, message: "Autopilot video panjang sedang bekerja. Tunggu putaran ini selesai." };
  const tgl = new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 10);
  const r = jalankanLatar(["agents/panjang/autopilot_panjang.py", "jalan", ...(manual ? ["--mulai"] : [])], `autopilot-panjang-latar-${tgl}.txt`);
  if (!r.ok) return r;
  g.__yofamoPanjang = Date.now();
  return { ok: true, message: "Autopilot video panjang mulai bekerja: mengisi slot tayang hari ini & besok." };
}

/** Video panjang: saat Studio dibuka & tiap ±1 jam selama terbuka, satu putaran. Autopilot aktif → isi jadwal & lanjutkan yang terhenti;
 *  autopilot mati → hanya melanjutkan video dari tombol Buat yang terhenti (mis. laptop dimatikan di tengah proses). */
function autopilotPanjangOtomatis(_cfg: { panjang?: { aktif?: boolean } }, dibuka: boolean): void {
  if (autopilotPanjangBerjalan()) return;
  if (!dibuka && g.__yofamoPanjang && Date.now() - g.__yofamoPanjang < JEDA) return;
  jalankanAutopilotPanjang();
}

/** Dipanggil tiap Studio memuat status.
 *  - Studio DIBUKA (permintaan pertama, atau setelah ≥ 10 menit tidak dibuka): autopilot dinyalakan & mulai mengisi stok
 *    (hari ini + besok). Setelah stok lengkap, autopilot mematikan dirinya sendiri.
 *  - Selama Studio terbuka & autopilot masih aktif (mis. terhenti karena kuota Claude): dicoba lagi tiap ±1 jam. */
export function autopilotOtomatis(): void {
  const file = path.join(ROOT, "bible", "autopilot.json");
  const cfg = baca(file);
  if (!cfg) return;
  const sekarang = Date.now(), dibuka = !g.__yofamoPoll || sekarang - g.__yofamoPoll > DIBUKA;
  g.__yofamoPoll = sekarang;
  try { autopilotPanjangOtomatis(cfg, dibuka); } catch { /* video panjang tidak boleh mengganggu Shorts */ }
  if (dibuka && cfg.jalan_saat_studio_dibuka !== false) {
    if (autopilotBerjalan()) { g.__yofamoAutopilot = sekarang; return; }
    if (!cfg.aktif) { cfg.aktif = true; try { fs.writeFileSync(file, JSON.stringify(cfg, null, 2) + "\n", "utf-8"); } catch { return; } }
    jalankanAutopilot();
    return;
  }
  if (!cfg.aktif) return;
  if (g.__yofamoAutopilot && sekarang - g.__yofamoAutopilot < JEDA) return;
  if (autopilotBerjalan()) { g.__yofamoAutopilot = sekarang; return; }
  jalankanAutopilot();
}

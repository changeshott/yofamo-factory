import "server-only";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { P, ROOT, agentEnv, pythonCmd } from "./project";

const g = globalThis as unknown as { __yofamoAutopilot?: number; __yofamoPoll?: number };
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

export function jalankanAutopilot(): { ok: boolean; message: string } {
  const py = pythonCmd();
  if (!py) return { ok: false, message: "Python tidak ditemukan." };
  if (autopilotBerjalan()) return { ok: false, message: "Autopilot sedang bekerja. Tunggu putaran ini selesai." };
  const child = spawn(py, ["agents/autopilot.py", "jalan"], { cwd: ROOT, env: agentEnv(), detached: true, stdio: "ignore", windowsHide: true });
  child.on("error", () => {});
  child.unref();
  g.__yofamoAutopilot = Date.now();
  return { ok: true, message: "Autopilot mulai bekerja. Kemajuan muncul di log dan di Produksi." };
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

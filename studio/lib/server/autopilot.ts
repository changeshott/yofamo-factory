import "server-only";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { P, ROOT, agentEnv, pythonCmd } from "./project";

const g = globalThis as unknown as { __yofamoAutopilot?: number };
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

/** Dipanggil tiap Studio memuat status: saat Studio dibuka & tiap ±1 jam selama terbuka, jalankan satu putaran autopilot. */
export function autopilotOtomatis(): void {
  const cfg = baca(path.join(ROOT, "bible", "autopilot.json"));
  if (!cfg?.aktif) return;
  if (g.__yofamoAutopilot && Date.now() - g.__yofamoAutopilot < JEDA) return;
  if (autopilotBerjalan()) { g.__yofamoAutopilot = Date.now(); return; }
  jalankanAutopilot();
}

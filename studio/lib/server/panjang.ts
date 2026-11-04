import "server-only";
import fs from "node:fs";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { P, ROOT, jalankanLatar, pythonCmd } from "./project";
import { kunciAktif } from "./autopilot";

/** Ruang Animasi: video YouTube panjang (agents/panjang/). Proses berjalan terpisah dari tugas Studio & autopilot Shorts. */
export const PJ = path.join(ROOT, "panjang");
const PROD = path.join(P.produksi, "panjang");
const baca = <T = Record<string, unknown>>(f: string): T | null => { try { return JSON.parse(fs.readFileSync(f, "utf-8")) as T; } catch { return null; } };

export interface TahapPanjang { kunci: string; job: string; nama: string; status: string; mulai: string | null; selesai: string | null; catatan: string }
export interface ProduksiPanjang { id: string; permintaan: string; dibuat: string; selesai: string | null; status: string; slug: string | null; pesan: string; tahap: TahapPanjang[] }
export interface VideoPanjang {
  slug: string; status: string; diubah: string | null; judul: string; judul_kerja: string;
  adegan: number; menit: number | null; ilustrasi: number; dirender: number;
  final: boolean; thumbnail: boolean; lembar: boolean; info: Record<string, unknown> | null; qc: Record<string, unknown> | null;
  upload: { url?: string; studio?: string; jadwal?: string } | null;
}

export const berjalanPanjang = () => kunciAktif("panjang.lock");

/** Produksi panjang yang sedang berjalan (untuk animasi kantor & panel). */
export function produksiPanjang(): ProduksiPanjang[] {
  const jalan = berjalanPanjang();
  let files: string[] = [];
  try { files = fs.readdirSync(PROD).filter((f) => /^[\w-]+\.json$/.test(f)); } catch { return []; }
  return files.map((f) => ({ f, t: fs.statSync(path.join(PROD, f)).mtimeMs })).sort((a, b) => b.t - a.t).slice(0, 8)
    .map(({ f }) => baca<ProduksiPanjang>(path.join(PROD, f)))
    .filter((x): x is ProduksiPanjang => !!x && Array.isArray(x.tahap))
    .map((x) => (x.status === "berjalan" && x.id !== jalan?.nama ? { ...x, status: "terhenti" } : x));
}

export function statusKantorPanjang(): { id: string; tahap: string | null; slug: string | null } | null {
  const p = produksiPanjang().find((x) => x.status === "berjalan");
  if (!p) return null;
  return { id: p.id, tahap: p.tahap.find((t) => t.status === "jalan")?.job ?? null, slug: p.slug };
}

export function daftarPanjang(): VideoPanjang[] {
  let dirs: string[] = [];
  try { dirs = fs.readdirSync(PJ).filter((d) => /^[a-z0-9-]{3,80}$/.test(d) && fs.existsSync(path.join(PJ, d, "status.json"))); } catch { return []; }
  return dirs.map((slug) => {
    const v = path.join(PJ, slug), st = baca<{ status?: string; riwayat?: { waktu: string }[] }>(path.join(v, "status.json")) ?? {};
    const naskah = baca<{ judul?: string; adegan?: unknown[] }>(path.join(v, "naskah.json")), ide = baca<{ judul_kerja?: string }>(path.join(v, "ide.json"));
    const waktu = baca<Record<string, { durasi: number }>>(path.join(v, "suara", "waktu.json"));
    const hitung = (d: string, re: RegExp) => { try { return fs.readdirSync(path.join(v, d)).filter((f) => re.test(f)).length; } catch { return 0; } };
    const exp = path.join(v, "export");
    return {
      slug, status: st.status ?? "ide", diubah: st.riwayat?.at(-1)?.waktu ?? null, judul: naskah?.judul ?? "", judul_kerja: ide?.judul_kerja ?? slug,
      adegan: naskah?.adegan?.length ?? 0, menit: waktu ? Math.round(Object.values(waktu).reduce((s, x) => s + (x.durasi || 0), 0) / 6) / 10 : null,
      ilustrasi: hitung("ilustrasi", /^\d\d\.jpg$/), dirender: hitung("adegan", /^\d\d\.mp4$/),
      final: fs.existsSync(path.join(exp, "final.mp4")), thumbnail: fs.existsSync(path.join(exp, "thumbnail.jpg")), lembar: fs.existsSync(path.join(exp, "lembar.jpg")),
      info: baca(path.join(exp, "info.json")), qc: baca(path.join(exp, "qc.json")), upload: baca(path.join(exp, "upload.json")),
    };
  }).sort((a, b) => (b.diubah ?? "").localeCompare(a.diubah ?? ""));
}

const jalankan = (args: string[], log: string) => jalankanLatar(args, log);

const stamp = () => new Date(Date.now() + 7 * 3600_000).toISOString().slice(0, 19).replace(/[-:]/g, "").replace("T", "-");

export function buatPanjang(tema: string, lanjut = ""): { ok: boolean; message: string } {
  if (berjalanPanjang()) return { ok: false, message: "Masih ada video panjang yang sedang dibuat. Tunggu selesai." };
  const id = `panjang-${stamp()}`;
  const args = ["agents/panjang/produser_panjang.py", ...(lanjut ? ["--lanjut", lanjut] : [tema.replace(/[^\p{L}\p{N}\s,.\-?!]/gu, "").slice(0, 200)]), "--id", id];
  const r = jalankan(args, `${id}.txt`);
  return r.ok ? { ok: true, message: lanjut ? "Tim Ruang Animasi melanjutkan video ini." : "Tim Ruang Animasi mulai membuat video panjang. Shorts tetap didahulukan." } : r;
}

export function setStatus(slug: string, ke: string, catatan: string): void {
  const py = pythonCmd();
  if (!py) throw new Error("Python tidak ditemukan.");
  const r = spawnSync(py, ["agents/panjang/status.py", "set", slug, ke, catatan], { cwd: ROOT, windowsHide: true, encoding: "utf-8" });
  if (r.status !== 0) throw new Error(String(r.stderr || "gagal mengubah status").slice(0, 200));
}

export function unggahPanjang(slug: string, jadwal: string): { ok: boolean; message: string } {
  const args = ["agents/panjang/unggah_panjang.py", "unggah", slug, ...(jadwal ? ["--jadwal", jadwal] : [])];
  const r = jalankan(args, `upload-panjang-${stamp()}.txt`);
  return r.ok ? { ok: true, message: "Uli mulai mengunggah video panjang (private + jadwal tayang). Lihat log di Kelola." } : r;
}

/* ---------------- host Yofa & gaya (agents/panjang/maskot.py) ---------------- */
export const MASKOT = path.join(ROOT, "bible", "maskot");
export const FILE_MASKOT = /^(kandidat\/k[1-4]\.(jpg|png)|pose\/[a-z]{3,12}\.png|utama\.(jpg|png)|acuan-gaya\.jpg)$/;

export interface StatusMaskot { kandidat: number[]; pose: string[]; utama: boolean; acuan: boolean; versi: number; berjalan: boolean; status: string; pesan: string }

export function statusMaskot(): StatusMaskot {
  const ada = (f: string) => fs.existsSync(path.join(MASKOT, f));
  let pose: string[] = [];
  try { pose = fs.readdirSync(path.join(MASKOT, "pose")).filter((f) => /^[a-z]{3,12}\.png$/.test(f)).map((f) => f.slice(0, -4)).sort(); } catch { /* belum ada */ }
  let versi = 0;
  try { versi = Math.round(fs.statSync(path.join(MASKOT, "pose")).mtimeMs); } catch { /* belum ada */ }
  try { versi = Math.max(versi, Math.round(fs.statSync(path.join(MASKOT, "kandidat")).mtimeMs)); } catch { /* belum ada */ }
  const st = baca<{ status?: string; pesan?: string }>(path.join(P.produksi, "maskot.json")) ?? {};
  const berjalan = !!kunciAktif("maskot.lock");
  return { kandidat: [1, 2, 3, 4].filter((i) => ada(`kandidat/k${i}.jpg`)), pose, utama: ada("utama.png"), acuan: ada("acuan-gaya.jpg"), versi,
    berjalan, status: berjalan ? "berjalan" : st.status === "berjalan" ? "terhenti" : st.status ?? "", pesan: st.pesan ?? "" };
}

export function jalankanMaskot(perintah: "kandidat" | "pakai" | "acuan-gaya", nomor = 1): { ok: boolean; message: string } {
  if (kunciAktif("maskot.lock")) return { ok: false, message: "Host sedang digambar. Tunggu selesai." };
  const args = ["agents/panjang/maskot.py", perintah, ...(perintah === "pakai" ? [String(Math.max(1, Math.min(4, nomor)))] : [])];
  const r = jalankan(args, `maskot-${stamp()}.txt`);
  return r.ok ? { ok: true, message: perintah === "kandidat" ? "Laras menggambar 4 kandidat host (±1–2 menit)." : perintah === "acuan-gaya" ? "Laras menggambar ulang acuan gaya tanpa orang (±30 detik)." : "Laras menggambar 7 pose host + acuan gaya (±3 menit)." } : r;
}

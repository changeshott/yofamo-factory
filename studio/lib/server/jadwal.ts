import "server-only";
import fs from "node:fs";
import path from "node:path";
import { P, ROOT, SLUG } from "./project";
import type { JadwalItem, JadwalTayang } from "@/lib/types";

const baca = <T,>(f: string): T | null => { try { return JSON.parse(fs.readFileSync(f, "utf-8")) as T; } catch { return null; } };
const WIB = 7 * 3600_000;
const tglWIB = (ms: number) => new Date(ms + WIB).toISOString().slice(0, 10);
const NAMA_HARI = ["Minggu", "Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu"];
const NAMA_BULAN = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"];

/** Judul pendek untuk sidebar: judul YouTube tanpa hashtag, cadangan judul kerja Nova. */
function judulVideo(slug: string): string {
  const sc = baca<{ judul?: string }>(path.join(P.videos, slug, "script.json"));
  const t = (sc?.judul ?? "").replace(/#\S+/g, "").replace(/\s+/g, " ").trim();
  if (t) return t;
  const id = baca<{ judul_kerja?: string }>(path.join(P.videos, slug, "idea.json"));
  return id?.judul_kerja ?? slug;
}

function gambar(slug: string): JadwalItem["gambar"] {
  const exp = path.join(P.videos, slug, "export");
  if (fs.existsSync(path.join(exp, "thumbnail.jpg"))) return "export/thumbnail.jpg";
  if (fs.existsSync(path.join(exp, "sampul.jpg"))) return "export/sampul.jpg";
  return null;
}

/** Jadwal tayang untuk sidebar kanan Studio: slot autopilot (insights/jadwal.json + produksi/autopilot.json),
 *  upload manual berjadwal (export/upload.json → jadwal), video panjang berjadwal, dan yang baru tayang. */
export function jadwalTayang(produksiAutopilotBerjalan: boolean): JadwalTayang {
  const cfg = baca<{ video_per_hari?: number; aktif?: boolean }>(path.join(ROOT, "bible", "autopilot.json")) ?? {};
  const jd = baca<{ slot?: Record<string, { jam: string; eksplorasi?: boolean }[]> }>(path.join(P.insights, "jadwal.json")) ?? {};
  const st = baca<{ slot?: Record<string, { slug?: string; url?: string; status?: string }>; pengganti?: Record<string, string> }>(path.join(P.produksi, "autopilot.json")) ?? {};
  const now = Date.now(), kini = new Date(now + WIB).toISOString().slice(0, 16).replace("T", " ");
  const hari = [0, 1, 2].map((n) => tglWIB(now + n * 86400_000));
  const item = new Map<string, JadwalItem>();
  const isi = (waktu: string, slug: string | undefined, url: string | null, jenis: JadwalItem["jenis"], extra: Partial<JadwalItem> = {}) => {
    const sudah = waktu <= kini;
    item.set(`${waktu}|${slug ?? ""}`, {
      waktu, jam: waktu.slice(11, 16), tanggal: waktu.slice(0, 10), jenis, slug: slug ?? null, url,
      judul: slug ? (jenis === "panjang" ? (baca<{ judul?: string }>(path.join(ROOT, "panjang", slug, "naskah.json"))?.judul ?? slug) : judulVideo(slug)) : null,
      gambar: slug && jenis === "shorts" ? gambar(slug) : null,
      status: slug ? (sudah ? "tayang" : "terjadwal") : (sudah ? "terlewat" : "kosong"), eksplorasi: false, ...extra,
    });
  };
  // 1. slot autopilot (jam terbaik) — terisi atau kosong
  const nPerHari = cfg.video_per_hari ?? 3;
  for (const d of hari) {
    for (const s of (jd.slot?.[d] ?? []).slice(0, nPerHari)) {
      const asli = `${d} ${s.jam}`, waktu = st.pengganti?.[asli] ?? asli, x = st.slot?.[waktu];
      isi(waktu, x?.slug, x?.url ?? null, "shorts", { eksplorasi: !!s.eksplorasi });
    }
  }
  // 2. slot terisi lain (mis. hari sebelumnya untuk "baru tayang") & upload manual berjadwal
  for (const [waktu, x] of Object.entries(st.slot ?? {})) if (x?.slug && !item.has(`${waktu}|${x.slug}`) && waktu.slice(0, 10) >= tglWIB(now - 2 * 86400_000)) isi(waktu, x.slug, x.url ?? null, "shorts");
  const sudahAda = new Set([...item.values()].map((i) => i.slug).filter(Boolean));
  try {
    for (const slug of fs.readdirSync(P.videos)) {
      if (!SLUG.test(slug) || sudahAda.has(slug)) continue;
      const up = baca<{ jadwal?: string | null; url?: string; waktu?: string }>(path.join(P.videos, slug, "export", "upload.json"));
      if (!up) continue;
      const w = (up.jadwal ?? up.waktu ?? "").replace("T", " ").slice(0, 16);
      if (w && w.slice(0, 10) >= tglWIB(now - 2 * 86400_000)) isi(w, slug, up.url ?? null, "shorts");
    }
  } catch { /* belum ada video */ }
  try {
    for (const slug of fs.readdirSync(path.join(ROOT, "panjang"))) {
      const up = baca<{ jadwal?: string | null; url?: string; waktu?: string }>(path.join(ROOT, "panjang", slug, "export", "upload.json"));
      const w = (up?.jadwal ?? up?.waktu ?? "").replace("T", " ").slice(0, 16);
      if (w && w.slice(0, 10) >= tglWIB(now - 2 * 86400_000)) isi(w, slug, up?.url ?? null, "panjang");
    }
  } catch { /* belum ada video panjang */ }

  const semua = [...item.values()].sort((a, b) => a.waktu.localeCompare(b.waktu));
  // slot kosong terdekat sedang dikerjakan autopilot
  if (produksiAutopilotBerjalan) { const k = semua.find((i) => i.status === "kosong"); if (k) k.status = "dibuat"; }
  const label = (d: string, i: number) => {
    if (i === 0) return "Hari ini";
    if (i === 1) return "Besok";
    const t = new Date(`${d}T00:00:00Z`);
    return `${NAMA_HARI[t.getUTCDay()]}, ${t.getUTCDate()} ${NAMA_BULAN[t.getUTCMonth()]}`;
  };
  const akanDatang = semua.filter((i) => i.tanggal >= hari[0] && (i.status !== "terlewat"));
  const berikut = akanDatang.find((i) => i.status === "terjadwal") ?? null;
  return {
    kini,
    hari: hari.map((d, i) => ({ tanggal: d, label: label(d, i), item: akanDatang.filter((x) => x.tanggal === d) })),
    baruTayang: semua.filter((i) => i.status === "tayang").slice(-4).reverse(),
    berikut, autopilotAktif: !!cfg.aktif,
  };
}

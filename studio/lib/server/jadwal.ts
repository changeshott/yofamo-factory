import "server-only";
import fs from "node:fs";
import path from "node:path";
import { P, ROOT, SLUG } from "./project";
import type { JadwalItem, JadwalTayang, MingguIni } from "@/lib/types";

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
export function jadwalTayang(produksiAutopilotBerjalan: boolean, produksiPanjangBerjalan = false): JadwalTayang {
  const cfg = baca<{ video_per_hari?: number; aktif?: boolean; panjang?: { aktif?: boolean } }>(path.join(ROOT, "bible", "autopilot.json")) ?? {};
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
      gambarUrl: slug && jenis === "panjang" && fs.existsSync(path.join(ROOT, "panjang", slug, "export", "thumbnail.jpg")) ? `/api/panjang?slug=${slug}&file=export/thumbnail.jpg` : null,
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
      const up = baca<{ jadwal?: string | null; url?: string; waktu?: string; dibatalkan?: boolean }>(path.join(P.videos, slug, "export", "upload.json"));
      if (!up || up.dibatalkan) continue;
      const w = (up.jadwal ?? up.waktu ?? "").replace("T", " ").slice(0, 16);
      if (w && w.slice(0, 10) >= tglWIB(now - 2 * 86400_000)) isi(w, slug, up.url ?? null, "shorts");
    }
  } catch { /* belum ada video */ }
  try {
    for (const slug of fs.readdirSync(path.join(ROOT, "panjang"))) {
      const up = baca<{ jadwal?: string | null; url?: string; waktu?: string; dibatalkan?: boolean }>(path.join(ROOT, "panjang", slug, "export", "upload.json"));
      if (up?.dibatalkan) continue;            // salinan dobel yang dibatalkan Zona (mis. sudah diupload manual)
      const w = (up?.jadwal ?? up?.waktu ?? "").replace("T", " ").slice(0, 16);
      if (w && w.slice(0, 10) >= tglWIB(now - 2 * 86400_000)) isi(w, slug, up?.url ?? null, "panjang");
    }
  } catch { /* belum ada video panjang */ }

  // 3. slot autopilot video panjang (1/hari): terisi atau kosong
  const sp = baca<{ jadwal?: string[]; slot?: Record<string, { slug?: string; url?: string }> }>(path.join(P.produksi, "autopilot-panjang.json")) ?? {};
  const pjAktif = cfg.panjang?.aktif !== false;
  if (pjAktif) for (const waktu of sp.jadwal ?? []) {
    if (!hari.includes(waktu.slice(0, 10))) continue;
    const x = sp.slot?.[waktu];
    if (x?.slug && [...item.values()].some((i) => i.slug === x.slug)) continue;
    isi(waktu, x?.slug, x?.url ?? null, "panjang");
  }

  const semua = [...item.values()].sort((a, b) => a.waktu.localeCompare(b.waktu));
  // slot kosong terdekat sedang dikerjakan autopilot
  if (produksiAutopilotBerjalan) { const k = semua.find((i) => i.status === "kosong" && i.jenis === "shorts"); if (k) k.status = "dibuat"; }
  if (produksiPanjangBerjalan) { const k = semua.find((i) => i.status === "kosong" && i.jenis === "panjang"); if (k) k.status = "dibuat"; }
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
    berikut, autopilotAktif: !!cfg.aktif, autopilotPanjangAktif: pjAktif,
  };
}

/** Senin minggu ini (WIB), format YYYY-MM-DD. */
export function seninIni(now = Date.now()): string {
  const w = new Date(now + WIB), hari = (w.getUTCDay() + 6) % 7;
  return new Date(now + WIB - hari * 86400_000).toISOString().slice(0, 10);
}

/** Hitung upload minggu ini (Shorts + video panjang). Sumber: export/upload.json (jadwal tayang / waktu upload) + status terbit.
 *  Video dengan jadwal yang sudah lewat = tayang; jadwal minggu ini yang belum lewat = terjadwal.
 *  Target = autopilot: Shorts video_per_hari × 7 + video panjang panjang.video_per_hari × 7 (kalau aktif). */
export function mingguIni(terbitShorts: string[] = []): MingguIni {
  const now = Date.now(), senin = seninIni(now), seninDepan = new Date(Date.parse(`${senin}T00:00:00Z`) + 7 * 86400_000).toISOString().slice(0, 10);
  const kini = new Date(now + WIB).toISOString().slice(0, 16).replace("T", " ");
  const hitung = (dir: string, terbit: Set<string>, stateAutopilot: string) => {
    const tayang = new Set<string>(terbit), terjadwal = new Set<string>();
    // slot autopilot yang sudah diisi (diupload private + jadwal) — sumber kedua kalau upload.json tidak ada
    const sa = baca<{ slot?: Record<string, { slug?: string; videoId?: string }> }>(path.join(P.produksi, stateAutopilot)) ?? {};
    for (const [w, x] of Object.entries(sa.slot ?? {})) {
      if (!x?.slug || !x.videoId || x.videoId === "UJI" || w.slice(0, 10) < senin || w.slice(0, 10) >= seninDepan) continue;
      if (w <= kini) tayang.add(x.slug); else terjadwal.add(x.slug);
    }
    let slugs: string[] = [];
    try { slugs = fs.readdirSync(dir).filter((x) => SLUG.test(x)); } catch { /* belum ada */ }
    for (const slug of slugs) {
      const up = baca<{ videoId?: string; jadwal?: string | null; waktu?: string; dibatalkan?: boolean }>(path.join(dir, slug, "export", "upload.json"));
      if (!up?.videoId || up.videoId === "UJI" || up.dibatalkan) continue;
      const w = (up.jadwal ?? "").replace("T", " ").slice(0, 16);
      if (!w) continue;                                              // tanpa jadwal: private sampai Zona menayangkan (status terbit)
      if (w.slice(0, 10) < senin || w.slice(0, 10) >= seninDepan) continue;
      if (w <= kini) { tayang.add(slug); terjadwal.delete(slug); } else if (!tayang.has(slug)) terjadwal.add(slug);
    }
    for (const x of tayang) terjadwal.delete(x);
    return { tayang: tayang.size, terjadwal: terjadwal.size };
  };
  // video panjang yang ditandai terbit minggu ini (status.json → riwayat)
  const pj = path.join(ROOT, "panjang"), terbitPanjang = new Set<string>();
  try {
    for (const slug of fs.readdirSync(pj)) {
      const st = baca<{ riwayat?: { ke?: string; waktu?: string }[] }>(path.join(pj, slug, "status.json"));
      if (st?.riwayat?.some((r) => r.ke === "terbit" && (r.waktu ?? "") >= senin)) terbitPanjang.add(slug);
    }
  } catch { /* belum ada video panjang */ }
  const cfg = baca<{ video_per_hari?: number; panjang?: { aktif?: boolean; video_per_hari?: number } }>(path.join(ROOT, "bible", "autopilot.json")) ?? {};
  const s = hitung(P.videos, new Set(terbitShorts), "autopilot.json"), p = hitung(pj, terbitPanjang, "autopilot-panjang.json");
  const tS = (cfg.video_per_hari ?? 3) * 7, tP = cfg.panjang?.aktif === false ? 0 : (cfg.panjang?.video_per_hari ?? 1) * 7;
  return {
    since: senin, published: s.tayang + p.tayang, terjadwal: s.terjadwal + p.terjadwal, target: tS + tP,
    shorts: { ...s, target: tS }, panjang: { ...p, target: tP },
  };
}

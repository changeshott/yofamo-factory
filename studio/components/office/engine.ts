import type { StudioState } from "@/lib/types";
import { emote, shade, sprite, type Emote, type Look, type Pose } from "./sprites";
import { activeStage, kerjaShorts, kerjaShortsSemua, tugasAgent } from "@/lib/format";
import { BH, BLOCKED, BW, FOUNDER, FUTURE, KURSI_RAPAT, NAMA_RUANG, OX, OY, PINTU, R2X, RD, RW, SEKAT, SPOTS, T, TEAM, TEAM2, TW, WALL, type AgentDef } from "./world";

type Pt = [number, number];
type BBox = [number, number, number, number];
export interface Hit { id: string; label: string; bbox: BBox; person: boolean }
export interface OverlayItem { kind: "tag" | "bubble" | "badge" | "sign"; x: number; y: number; text: string; tone?: string; sub?: string; pips?: [number, number] }
export interface Kerja { kind: "busy" | "ok" | "err" | "stopped"; text: string; sejak?: string | null; pips?: [number, number] }

const P = (x: number, y: number, z = 0): Pt => [Math.round(OX + (x - y) * T), Math.round(OY + ((x + y) * T) / 2 - z)];
const bboxOf = (pts: Pt[]): BBox => { const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]); return [Math.min(...xs), Math.min(...ys), Math.max(...xs), Math.max(...ys)]; };

/* ------------------------------------------------------------ waktu */
interface Phase { name: string; sky: [string, string]; tint: string | null; night: number; city: string }
export function dayPhase(d = new Date()): Phase {
  const h = d.getHours() + d.getMinutes() / 60;
  if (h >= 5 && h < 7) return { name: "pagi", sky: ["#F6B48E", "#A8CBEA"], tint: "rgba(255,170,110,.06)", night: 0.15, city: "#8E8AA6" };
  if (h >= 7 && h < 16) return { name: "siang", sky: ["#6FBDF0", "#D3ECFB"], tint: null, night: 0, city: "#9DB4CD" };
  if (h >= 16 && h < 18.5) return { name: "sore", sky: ["#EE8F62", "#F7D39C"], tint: "rgba(255,130,70,.08)", night: 0.35, city: "#7B6782" };
  return { name: "malam", sky: ["#0A1430", "#253862"], tint: "rgba(8,14,40,.32)", night: 1, city: "#16213D" };
}

/* ------------------------------------------------------------ jalan (BFS grid 0,5 tile) */
const G = 2, GW = TW * G, GH = RD * G;
const SEMUA = [...TEAM, ...TEAM2];
const ruangDi = (x: number) => (x > R2X ? "animasi" : "");
const blocked = new Uint8Array(GW * GH);
for (let gx = 0; gx < GW; gx++) for (let gy = 0; gy < GH; gy++) {
  const cx = (gx + 0.5) / G, cy = (gy + 0.5) / G;
  if (cx < 0.4 || cy < 0.4) blocked[gy * GW + gx] = 1;
  for (const [x0, y0, x1, y1] of BLOCKED) if (cx > x0 && cx < x1 && cy > y0 && cy < y1) blocked[gy * GW + gx] = 1;
}
function findPath(from: Pt, to: Pt): Pt[] {
  const s = [Math.min(GW - 1, Math.max(0, Math.floor(from[0] * G))), Math.min(GH - 1, Math.max(0, Math.floor(from[1] * G)))];
  const e = [Math.min(GW - 1, Math.max(0, Math.floor(to[0] * G))), Math.min(GH - 1, Math.max(0, Math.floor(to[1] * G)))];
  const prev = new Int32Array(GW * GH).fill(-1), si = s[1] * GW + s[0], ei = e[1] * GW + e[0];
  const q = [si]; prev[si] = si;
  while (q.length) {
    const i = q.shift()!; if (i === ei) break;
    const x = i % GW, y = (i / GW) | 0;
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const nx = x + dx, ny = y + dy, ni = ny * GW + nx;
      if (nx < 0 || ny < 0 || nx >= GW || ny >= GH || prev[ni] !== -1) continue;
      if (blocked[ni] && ni !== ei) continue;
      prev[ni] = i; q.push(ni);
    }
  }
  if (prev[ei] === -1) return [to];
  const cells: Pt[] = [];
  for (let i = ei; i !== si; i = prev[i]) cells.push([(i % GW + 0.5) / G, (((i / GW) | 0) + 0.5) / G]);
  cells.reverse();
  // ambil titik belok saja
  const out: Pt[] = [];
  for (let k = 0; k < cells.length; k++) {
    const a = cells[k - 1], b = cells[k], c = cells[k + 1];
    if (!a || !c || (b[0] - a[0]) * (c[1] - b[1]) !== (b[1] - a[1]) * (c[0] - b[0])) out.push(b);
  }
  out.push(to);
  return out;
}

/* ------------------------------------------------------------ aktor */
type Kegiatan = "" | "minum" | "hp" | "lihat" | "pikir" | "musik" | "tidur" | "ngobrol";
interface Actor {
  def: AgentDef; x: number; y: number; path: Pt[]; wait: number; frame: number; langkah: number;
  pose: Pose; facing: "front" | "back"; mode: "idle" | "work" | "report" | "antar" | "ngobrol" | "sorak" | "gagal" | "rapat"; sitIdle: boolean; screen?: Pt;
  reportedAt?: string | null; failedAt?: string | null;
  act: Kegiatan; actT: number; emo: Emote | null; next: { act: Kegiatan; emo: Emote | null; t: number; facing?: "front" | "back" } | null; teman: Actor | null; bicara: boolean;
}
const seatOf = (d: AgentDef): Pt => [d.desk[0] + 1, d.desk[1] + 1.55];
/** Karakter digambar 1,5x (blok piksel 3:2) supaya proporsinya pas dengan meja & posenya terbaca. */
const SKALA = 1.5;
/** Urutan kerja tiap pabrik (untuk jalur produksi di lantai & serah terima dokumen). */
const ALUR_SHORTS: [string, string][] = [["fetch", "steve"], ["ide", "nova"], ["penulis", "raka"], ["suara", "dara"], ["aset", "bima"], ["thumbnail", "mila"], ["editor", "kai"], ["qc", "rara"], ["upload", "uli"]];
const ALUR_PANJANG: [string, string][] = [["p_ide", "bayu"], ["p_naskah", "citra"], ["p_suara", "gilang"], ["p_ilustrasi", "laras"], ["p_animasi", "tio"], ["p_rakit", "wulan"]];
/** Kegiatan di tiap tempat santai: pose, emote, lama (tick 0,1 dtk), arah hadap. */
const DI_TEMPAT: Record<string, { act: Kegiatan; emo: Emote | null; t: [number, number]; facing?: "front" | "back" }> = {
  kopi: { act: "minum", emo: "kopi", t: [60, 110] }, dispenser: { act: "minum", emo: null, t: [40, 70] }, sofa: { act: "hp", emo: null, t: [80, 160] },
  jendela: { act: "lihat", emo: null, t: [60, 120], facing: "back" }, papan: { act: "pikir", emo: "bulb", t: [50, 90], facing: "back" },
  tv: { act: "pikir", emo: "bulb", t: [50, 90], facing: "back" }, server: { act: "lihat", emo: null, t: [40, 70], facing: "back" },
  meja_bundar: { act: "hp", emo: null, t: [60, 120] }, arcade: { act: "musik", emo: "note", t: [80, 150], facing: "back" },
  sofa_animasi: { act: "hp", emo: null, t: [80, 160] }, meja_cahaya: { act: "pikir", emo: "bulb", t: [60, 110] },
  meeting: { act: "pikir", emo: "bulb", t: [50, 90], facing: "back" }, istirahat_sofa: { act: "hp", emo: null, t: [100, 200] },
  foosball: { act: "musik", emo: "bintang", t: [90, 160], facing: "back" }, mesin_jajan: { act: "minum", emo: "kopi", t: [50, 90] },
  studio_suara: { act: "musik", emo: "note", t: [90, 160], facing: "back" }, taman: { act: "lihat", emo: "hati", t: [90, 170] },
};
const acak = (a: number, b: number) => a + Math.floor(Math.random() * (b - a + 1));
const mmss = (iso?: string | null) => { const d = iso ? Math.max(0, Date.now() - Date.parse(iso)) / 1000 : NaN; return Number.isFinite(d) && d < 86400 ? `${String(Math.floor(d / 60)).padStart(2, "0")}:${String(Math.floor(d % 60)).padStart(2, "0")}` : ""; };

export class OfficeEngine {
  private buf = document.createElement("canvas");
  private topeng: HTMLCanvasElement | null = null;
  private latar = document.createElement("canvas");   // ruangan (dinding, lantai, jendela) digambar sekali per fase hari
  private latarKunci = "";
  private g: CanvasRenderingContext2D;
  private tick = 0;
  private waktu = 0;                                   // detik sejak mulai (animasi halus: awan, debu, jalur)
  private actors: Actor[];
  private tahapLalu = { shorts: "", panjang: "" };
  private rapat = { lagi: 500, peserta: [] as Actor[] };     // rapat tim berkala di Ruang Meeting (tick 0,1 dtk)
  private robot = { x: 8.5, y: 10.5, path: [] as Pt[], wait: 30, arah: 1 };
  private debu = Array.from({ length: 26 }, (_, i) => ({ x: 0.3 + ((i * 37) % 30) / 10, y: 1 + ((i * 53) % 86) / 10, z: 6 + ((i * 29) % 60), v: 0.6 + ((i * 7) % 5) / 5, f: i * 1.7 }));
  private uap = Array.from({ length: 5 }, (_, i) => ({ t: i * 0.9 }));
  state: StudioState | null = null;
  hits: Hit[] = [];
  hoverId: string | null = null;
  overlay: OverlayItem[] = [];
  reduced = false;

  constructor() {
    this.buf.width = BW; this.buf.height = BH;
    this.g = this.buf.getContext("2d")!;
    this.g.imageSmoothingEnabled = false;
    this.actors = SEMUA.map((def, i) => {
      const [x, y] = seatOf(def);
      return { def, x, y, path: [], wait: 30 + i * 25, frame: i * 7, langkah: 0, pose: "sit", facing: "back", mode: "idle", sitIdle: true, reportedAt: undefined,
        act: "", actT: 0, emo: null, next: null, teman: null, bicara: false };
    });
    this.latar.width = BW; this.latar.height = BH;
  }
  get canvas() { return this.buf; }

  jobFor(def: AgentDef): Kerja | null {
    if (def.ruang === "animasi") {   // tim video panjang: status dari produksi panjang yang sedang berjalan
      const tahap = this.state?.panjang?.tahap;
      if (!tahap || !def.busy[tahap]) return null;
      const i = ALUR_PANJANG.findIndex(([k]) => k === tahap);
      return { kind: "busy", text: def.busy[tahap]!, pips: i >= 0 ? [i + 1, ALUR_PANJANG.length] : undefined };
    }
    const kini = kerjaShortsSemua(this.state);   // tombol Studio, antrean, ATAU autopilot di latar
    if (kini.length) {
      const t = tugasAgent(def.busy, kini);
      if (!t) return null;
      const p = this.state?.produksi?.[0], aktif = p?.status === "berjalan" ? activeStage(this.state) : "";
      if (p && aktif && def.busy[aktif]) {       // agent ini yang memegang tahap produksi sekarang → tampilkan waktu & tahap ke-n
        const i = p.tahap.findIndex((x) => x.status === "jalan");
        return { kind: "busy", text: t, sejak: i >= 0 ? p.tahap[i].mulai : null, pips: i >= 0 ? [i + 1, p.tahap.length] : undefined };
      }
      return { kind: "busy", text: t };
    }
    const j = this.state?.job;
    const key = j?.job === "produksi" ? activeStage(this.state) : j?.job;
    if (!j?.job || !key || !def.busy[key]) return null;
    const fin = j.finished ? Date.parse(j.finished) : 0;
    if (!fin || Date.now() - fin > 3 * 60_000) return null;
    if (j.status === "ok") return { kind: "ok", text: "Selesai! Cek hasilnya" };
    if (j.status === "stopped") return { kind: "stopped", text: "Dihentikan" };
    return { kind: "err", text: "Gagal, cek log" };
  }

  private go(a: Actor, to: Pt) {
    a.path = findPath([a.x, a.y], to);
    if (this.reduced) { a.x = to[0]; a.y = to[1]; a.path = []; }
  }

  /** Lepaskan teman ngobrol (dipanggil saat salah satu dipanggil bekerja atau obrolan selesai). */
  private lepas(a: Actor) {
    const b = a.teman;
    a.teman = null; a.bicara = false;
    if (b) { b.teman = null; b.bicara = false; if (b.mode === "ngobrol") { b.mode = "idle"; b.wait = acak(20, 60); b.emo = null; b.act = ""; } }
  }
  private bebas(a: Actor) { return a.mode === "idle" && !a.path.length && !a.teman && a.act !== "tidur"; }

  /** Tahap produksi berganti → agent yang baru selesai mengantar dokumen ke meja agent berikutnya. */
  private serahTerima() {
    const st = this.state;
    const kini = { shorts: st?.produksi?.[0]?.status === "berjalan" ? activeStage(st) : "", panjang: st?.panjang?.tahap ?? "" };
    for (const [ruang, alur] of [["shorts", ALUR_SHORTS], ["panjang", ALUR_PANJANG]] as const) {
      const lalu = this.tahapLalu[ruang], baru = kini[ruang];
      if (lalu && baru && lalu !== baru) {
        const dari = this.actors.find((a) => a.def.id === alur.find(([k]) => k === lalu)?.[1]);
        const ke = this.actors.find((a) => a.def.id === alur.find(([k]) => k === baru)?.[1]);
        if (dari && ke && dari !== ke) {
          this.lepas(dari);
          const [sx, sy] = seatOf(ke.def);
          dari.mode = "antar"; dari.act = ""; dari.next = null; dari.emo = "kertas"; dari.wait = 28; dari.sitIdle = false;
          this.go(dari, [sx + 0.75, sy + 0.2]);
        }
      }
      this.tahapLalu[ruang] = baru;
    }
  }

  /** Logika 10x per detik: siapa bekerja, siapa santai, kegiatan apa. Gerak halusnya di advance(). */
  step() {
    this.tick++;
    const malam = dayPhase().night === 1;
    this.serahTerima();
    for (const a of this.actors) {
      a.frame++;
      const st = this.jobFor(a.def), seat = seatOf(a.def), selesai = this.state?.job.finished;
      if (st?.kind === "busy" && a.mode !== "work" && a.mode !== "antar") {
        this.lepas(a); a.mode = "work"; a.sitIdle = true; a.act = ""; a.actT = 0; a.emo = null; a.next = null; this.go(a, seat);
      }
      if (st?.kind === "ok" && a.mode === "work" && a.reportedAt !== selesai) { a.mode = "sorak"; a.reportedAt = selesai; a.wait = 24; a.path = []; a.emo = "bintang"; a.sitIdle = false; }
      if (st?.kind === "err" && a.mode === "work" && a.failedAt !== selesai) { a.mode = "gagal"; a.failedAt = selesai; a.wait = 45; a.path = []; a.emo = "seru"; a.sitIdle = false; }
      if ((!st || st.kind !== "busy") && a.mode === "work") { a.mode = "idle"; a.wait = 40; }
      if (a.path.length) { a.pose = "walk"; continue; }
      const atSeat = Math.hypot(a.x - seat[0], a.y - seat[1]) < 0.06;
      if (a.next) { a.act = a.next.act; a.actT = a.next.t; a.emo = a.next.emo; if (a.next.facing) a.facing = a.next.facing; else if (!atSeat) a.facing = "front"; a.next = null; }
      else if (!atSeat && !a.act && a.mode === "idle") a.facing = "front";
      // pose saat diam
      a.pose = atSeat && a.sitIdle ? (a.act === "tidur" ? "sleep" : "sit")
        : a.mode === "sorak" ? "cheer" : a.mode === "gagal" ? "shock" : a.mode === "antar" ? "carry"
        : a.act === "minum" ? "drink" : a.act === "hp" ? "phone" : (a.mode === "ngobrol" || a.mode === "rapat") && a.bicara ? "talk" : "stand";
      if (a.pose !== "sit" && a.pose !== "sleep" && a.pose !== "stand" && a.pose !== "talk") a.facing = "front";
      if (a.mode === "sorak") { if (--a.wait <= 0) { a.mode = "report"; a.emo = null; this.go(a, a.def.ruang ? SPOTS.lapor_animasi : SPOTS.lapor); a.wait = 50; } continue; }
      if (a.mode === "gagal") { if (--a.wait <= 0) { a.mode = "idle"; a.emo = null; a.wait = 30; } continue; }
      if (a.mode === "report") { a.facing = "back"; if (--a.wait <= 0) { a.mode = "idle"; a.sitIdle = true; this.go(a, seat); } continue; }
      if (a.mode === "antar") { if (a.wait === 14) a.emo = "cek"; if (--a.wait <= 0) { a.mode = "idle"; a.emo = null; a.sitIdle = true; a.wait = acak(60, 120); this.go(a, seat); } continue; }
      if (a.mode === "ngobrol") {
        const b = a.teman;
        if (!b || b.mode !== "ngobrol") { this.lepas(a); a.mode = "idle"; a.wait = 30; continue; }
        if (!b.path.length) {   // dua-duanya sudah sampai: bergantian bicara
          const giliran = ((this.tick >> 4) % 2 === 0) === (a.def.id < b.def.id);
          a.bicara = giliran; a.emo = giliran ? "titik" : null;
          if (--a.wait <= 0) { this.lepas(a); a.mode = "idle"; a.emo = null; a.wait = acak(30, 80); }
        }
        continue;
      }
      if (a.mode === "rapat") {
        const ps = this.rapat.peserta, k = ps.indexOf(a), siap = ps.every((b) => !b.path.length);
        if (k < 0) { a.mode = "idle"; a.wait = 30; continue; }
        if (siap) {
          a.bicara = ((this.tick >> 5) % ps.length) === k; a.emo = a.bicara ? "titik" : ((this.tick >> 6) + k) % 5 === 0 ? "bulb" : null;
          if (--a.wait <= 0) { a.mode = "idle"; a.emo = null; a.bicara = false; a.wait = acak(20, 80); this.rapat.peserta = ps.filter((b) => b !== a); }
        }
        continue;
      }
      if (a.mode === "work") continue;
      if (a.actT > 0) { if (--a.actT <= 0) { a.act = ""; a.emo = null; a.wait = acak(10, 40); } continue; }
      if (--a.wait > 0) continue;
      // pilih kegiatan santai berikutnya
      const ruang = a.def.ruang ?? "", r = Math.random();
      if (malam && r < 0.45) { a.sitIdle = true; this.go(a, seat); a.next = { act: "tidur", emo: "zzz", t: acak(250, 500) }; a.wait = 0; continue; }
      if (r < 0.34) { a.sitIdle = true; this.go(a, seat); a.wait = acak(80, 220); continue; }
      const teman = r < 0.56 ? this.actors.filter((b) => b !== a && (b.def.ruang ?? "") === ruang && this.bebas(b)) : [];
      if (teman.length) {
        const b = teman[Math.floor(Math.random() * teman.length)], t = ruang ? SPOTS.lapor_animasi : [[11.3, 11.9], [7.8, 5.3], [4.2, 9.4], [12.4, 5.2]][Math.floor(Math.random() * 4)];
        a.mode = b.mode = "ngobrol"; a.teman = b; b.teman = a; a.wait = b.wait = acak(70, 130); a.sitIdle = b.sitIdle = false; a.act = b.act = ""; b.next = null;
        this.go(a, [t[0], t[1]]); this.go(b, [t[0] + 0.45, t[1] + 0.45]);
        a.next = { act: "", emo: null, t: 0, facing: "front" }; b.next = { act: "", emo: null, t: 0, facing: "back" };
        continue;
      }
      const names = Object.keys(SPOTS).filter((k) => !k.startsWith("lapor") && ruangDi(SPOTS[k][0]) === ruang);
      const nama = names[Math.floor(Math.random() * names.length)], sp = SPOTS[nama], k = DI_TEMPAT[nama];
      a.sitIdle = false; this.go(a, [sp[0] + (Math.random() - 0.5) * 0.4, sp[1] + (Math.random() - 0.5) * 0.3]);
      if (k) a.next = { act: k.act, emo: k.emo, t: acak(k.t[0], k.t[1]), facing: k.facing };
      a.wait = acak(40, 120);
    }
    // rapat tim: tiap beberapa menit, agent Shorts yang sedang santai berkumpul di Ruang Meeting (tidak saat produksi berjalan)
    this.rapat.peserta = this.rapat.peserta.filter((b) => b.mode === "rapat");
    if (--this.rapat.lagi <= 0) {
      const calon = this.actors.filter((b) => !b.def.ruang && this.bebas(b) && !b.act).slice(0, KURSI_RAPAT.length);
      if (calon.length >= 3 && !kerjaShortsSemua(this.state).length && !malam) {
        calon.forEach((b, k) => {
          const [kx, ky] = KURSI_RAPAT[k];
          b.mode = "rapat"; b.wait = acak(220, 300); b.sitIdle = false; b.act = ""; b.emo = null; b.bicara = false;
          b.next = { act: "", emo: null, t: 0, facing: ky < 18.7 ? "front" : "back" };
          this.go(b, [kx, ky]);
        });
        this.rapat.peserta = calon; this.rapat.lagi = acak(3000, 4200);
      } else this.rapat.lagi = 300;
    }
    // robot penyedot debu: keliling kantor Shorts, menunggu sebentar di tiap titik
    const rb = this.robot;
    if (!rb.path.length && --rb.wait <= 0) {
      for (let coba = 0; coba < 12; coba++) {
        const tx = 1 + Math.random() * 14, ty = 1.2 + Math.random() * 11.5;
        if (!blocked[Math.floor(ty * G) * GW + Math.floor(tx * G)]) { rb.path = findPath([rb.x, rb.y], [tx, ty]); break; }
      }
      rb.wait = acak(20, 60);
    }
  }

  /** Gerak halus tiap frame (dt detik): jalan mengikuti jalur, ayunan langkah, partikel. */
  advance(dt: number) {
    this.waktu += dt;
    const jalan = (o: { x: number; y: number; path: Pt[] }, kec: number) => {
      let sisa = kec * dt;
      while (o.path.length && sisa > 0) {
        const [tx, ty] = o.path[0], dx = tx - o.x, dy = ty - o.y, dist = Math.hypot(dx, dy);
        if (dist <= sisa) { o.x = tx; o.y = ty; o.path.shift(); sisa -= dist; } else { o.x += (dx / dist) * sisa; o.y += (dy / dist) * sisa; sisa = 0; }
        if (dist > 0.001) return [dx, dy] as const;
      }
      return null;
    };
    for (const a of this.actors) {
      if (!a.path.length) continue;
      const d = jalan(a, a.mode === "antar" || a.mode === "report" ? 1.25 : a.mode === "work" ? 1.4 : 0.95);
      a.langkah += dt * 7.5; a.pose = "walk";
      if (d) a.facing = d[1] < -0.01 || (Math.abs(d[1]) < 0.01 && d[0] < 0) ? "back" : "front";
    }
    const d = jalan(this.robot, 0.7); if (d) this.robot.arah = d[0] - d[1] >= 0 ? 1 : -1;
    for (const p of this.debu) { p.z += p.v * dt * 1.6; p.x += Math.sin(this.waktu * 0.4 + p.f) * dt * 0.05; if (p.z > 70) p.z = 4; }
    for (const u of this.uap) { u.t += dt; if (u.t > 4.5) u.t = 0; }
  }

  /* ============================================================ menggambar */
  private poly(pts: Pt[], fill?: string | CanvasGradient, stroke?: string) {
    const g = this.g; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath();
    if (fill) { g.fillStyle = fill; g.fill(); }
    if (stroke) { g.strokeStyle = stroke; g.lineWidth = 1; g.stroke(); }
  }
  private px(x: number, y: number, w: number, h: number, c: string) { this.g.fillStyle = c; this.g.fillRect(Math.round(x), Math.round(y), w, h); }
  private box(x: number, y: number, w: number, d: number, h: number, col: string, z = 0): Pt[] {
    const top: Pt[] = [P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)];
    this.poly([P(x, y + d, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x, y + d, z)], shade(col, 0.8));
    this.poly([P(x + w, y, z + h), P(x + w, y + d, z + h), P(x + w, y + d, z), P(x + w, y, z)], shade(col, 0.64));
    this.poly(top, col);
    // garis terang di tepi depan atas
    const g = this.g; g.strokeStyle = shade(col, 1.12); g.lineWidth = 1; g.beginPath();
    const a = P(x, y + d, z + h), b = P(x + w, y + d, z + h), c = P(x + w, y, z + h);
    g.moveTo(a[0], a[1] + 0.5); g.lineTo(b[0], b[1] + 0.5); g.lineTo(c[0], c[1] + 0.5); g.stroke();
    return top;
  }
  private qx = (x: number, y0: number, y1: number, z0: number, z1: number): Pt[] => [P(x, y0, z0), P(x, y1, z0), P(x, y1, z1), P(x, y0, z1)];
  private qy = (y: number, x0: number, x1: number, z0: number, z1: number): Pt[] => [P(x0, y, z0), P(x1, y, z0), P(x1, y, z1), P(x0, y, z1)];

  private sky(q: Pt[], ph: Phase, seed: number) {
    const g = this.g, [x0, y0, x1, y1] = bboxOf(q);
    g.save(); g.beginPath(); q.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.clip();
    const gr = g.createLinearGradient(0, y0, 0, y1); gr.addColorStop(0, ph.sky[0]); gr.addColorStop(1, ph.sky[1]);
    g.fillStyle = gr; g.fillRect(x0, y0, x1 - x0, y1 - y0);
    if (ph.night > 0.5) for (let i = 0; i < 14; i++) this.px(x0 + ((i * 37 + seed * 11) % (x1 - x0)), y0 + ((i * 23 + seed * 7) % 20), 1, 1, "#FDF3C6");
    let x = x0 - 6, k = seed * 5;
    while (x < x1) {
      const w = 6 + ((k * 7) % 11), h = 14 + ((k * 13) % 40), base = y1 + 8;
      this.px(x, base - h, w, h, ph.city);
      this.px(x, base - h, w, 1, shade(ph.city, 1.2));
      if (ph.night) for (let yy = base - h + 3; yy < base - 2; yy += 4) for (let xx = x + 1; xx < x + w - 1; xx += 3) if ((xx * 7 + yy * 13 + k) % 10 < ph.night * 6) this.px(xx, yy, 1, 2, "#FFD98A");
      x += w + 1; k++;
    }
    g.restore();
  }

  private room(ph: Phase) {
    // dinding: putih kebiruan + panel bawah navy (warna khas Yofamo)
    this.poly([P(0, 0), P(0, RD), P(0, RD, WALL), P(0, 0, WALL)], "#E4EAF2");
    this.poly([P(0, 0), P(RW, 0), P(RW, 0, WALL), P(0, 0, WALL)], "#D3DCE8");
    this.poly([P(0, 0), P(0, RD), P(0, RD, 30), P(0, 0, 30)], "#22355A");
    this.poly([P(0, 0), P(16, 0), P(16, 0, 30), P(0, 0, 30)], "#1C2E50");
    this.poly([P(0, 0, 30), P(0, RD, 30), P(0, RD, 32), P(0, 0, 32)], "#6FD3FF");
    this.poly([P(0, 0, 30), P(16, 0, 30), P(16, 0, 32), P(0, 0, 32)], "#4FB9F0");
    this.poly([P(16, 0), P(RW, 0), P(RW, 0, WALL), P(16, 0, WALL)], "#16233B"); // dinding ruang founder (navy gelap)
    this.poly([P(0, 0, WALL), P(0, RD, WALL), P(-0.35, RD, WALL), P(-0.35, -0.35, WALL), P(RW, -0.35, WALL), P(RW, 0, WALL)], "#7F93AE");
    // panel kayu bilah di belakang neon
    this.poly(this.qy(0, 9.8, 13.1, 32, 104), "#3B2A22");
    for (let x = 9.86; x < 13.05; x += 0.16) this.poly(this.qy(0, x, x + 0.09, 33, 103), (Math.round(x * 10) % 3) ? "#6B4A35" : "#5E402E");
    // jendela kiri
    [[1.0, 3.6], [4.2, 6.8], [7.4, 9.6]].forEach(([y0, y1], i) => {
      const q = this.qx(0, y0, y1, 38, 100); this.sky(q, ph, i + 1);
      this.poly(this.qx(0, y0 - 0.06, y1 + 0.06, 34, 38), "#9FB2C8");
      this.poly(q, undefined, "#5E7390");
      const m = (y0 + y1) / 2, g = this.g; g.strokeStyle = "#5E7390"; g.beginPath(); g.moveTo(...P(0, m, 38)); g.lineTo(...P(0, m, 100)); g.moveTo(...P(0, y0, 70)); g.lineTo(...P(0, y1, 70)); g.stroke();
      g.strokeStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.moveTo(...P(0, y0 + 0.25, 46)); g.lineTo(...P(0, y0 + 0.75, 92)); g.stroke();
    });
    // jendela ruang founder
    [[16.8, 18.8], [19.2, 21.2]].forEach(([x0, x1], i) => {
      const q = this.qy(0, x0, x1, 40, 98); this.sky(q, ph, i + 7);
      this.poly(q, undefined, "#0B1424");
      this.poly(this.qy(0, x0 - 0.06, x1 + 0.06, 36, 40), "#101B2E");
    });
    // lantai: kayu walnut (kerja), karpet navy (founder), marmer (pantry)
    const KAYU = ["#C9A27C", "#C39B74", "#CEA986", "#BF966E", "#C7A07A"];
    const kayu = (i: number, j: number) => !(i >= 16 && j < 6) && !(j >= 13 && j < 15 && i >= 8 && i < 16) && !(j >= 16 && i < 10);
    for (let i = 0; i < RW; i++) for (let j = 0; j < RD; j++) {
      let c: string;
      if (i >= 16 && j < 6) c = "#1D2C47";
      else if (j >= 13 && j < 15 && i >= 8 && i < 16) c = (i + j) % 2 ? "#E8EDF3" : "#DFE6EE";      // marmer pantry, kotak-kotak halus
      else if (j >= 16 && i < 10) c = (i + j) % 2 ? "#2B3A5C" : "#304166";                // karpet Ruang Meeting
      else c = KAYU[(i * 31 + Math.floor((j + (i % 2) * 1.5) / 3) * 17) % KAYU.length]; // kayu bilah memanjang, sambungan berselang
      this.poly([P(i - 0.02, j - 0.02), P(i + 1.02, j - 0.02), P(i + 1.02, j + 1.02), P(i - 0.02, j + 1.02)], c);
    }
    const g = this.g;
    // garis sambungan bilah kayu (tipis, hangat)
    g.strokeStyle = "rgba(96,62,34,.22)"; g.lineWidth = 1;
    g.beginPath();
    for (let i = 1; i < RW; i++) for (let j = 0; j < RD; j++) if (kayu(i, j) && kayu(i - 1, j)) { g.moveTo(...P(i, j)); g.lineTo(...P(i, j + 1)); }
    for (let i = 0; i < RW; i++) for (let j = 1; j < RD; j++) if (kayu(i, j) && (j + (i % 2) * 1.5) % 3 < 1 && kayu(i, j - 1)) { g.moveTo(...P(i, j)); g.lineTo(...P(i + 1, j)); }
    g.stroke();
    // kilap lantai (pantulan cahaya jendela & lampu)
    { const [cx, cy] = P(6, 5), gr = g.createRadialGradient(cx, cy, 4, cx, cy, 190);
      gr.addColorStop(0, ph.night ? "rgba(255,214,150,.10)" : "rgba(255,255,255,.12)"); gr.addColorStop(1, "rgba(255,255,255,0)");
      this.poly([P(0, 0), P(16, 0), P(16, 13), P(0, 13)], gr); }
    // cahaya ruangan: terang di tengah, meredup ke tepi (tanpa garis)
    { const [cx, cy] = P(8, 6.5), gr = g.createRadialGradient(cx, cy, 10, cx, cy, 330);
      gr.addColorStop(0, "rgba(255,244,226,.20)"); gr.addColorStop(0.6, "rgba(255,244,226,.04)"); gr.addColorStop(1, "rgba(40,24,10,.16)");
      this.poly([P(0, 0), P(16, 0), P(16, 6), P(RW, 6), P(RW, RD), P(0, RD)], gr); }
    // bayangan lembut di pertemuan dinding & lantai (ambient occlusion)
    const ao = (pts: Pt[], x0: Pt, x1: Pt) => { const gr = g.createLinearGradient(x0[0], x0[1], x1[0], x1[1]); gr.addColorStop(0, "rgba(10,18,34,.32)"); gr.addColorStop(1, "rgba(10,18,34,0)"); this.poly(pts, gr); };
    ao([P(0, 0), P(0, RD), P(0.9, RD), P(0.9, 0)], P(0, 7), P(0.9, 7));
    ao([P(0, 0), P(RW, 0), P(RW, 0.9), P(0, 0.9)], P(8, 0), P(8, 0.9));
    // cahaya matahari dari jendela kiri (siang/sore)
    if (ph.night < 0.6) {
      const a = ph.name === "sore" ? "rgba(255,190,120,.16)" : "rgba(255,246,214,.14)";
      [[1.0, 3.6], [4.2, 6.8], [7.4, 9.6]].forEach(([y0, y1]) => this.poly([P(0, y0), P(0, y1), P(3.4, y1 + 1.6), P(3.4, y0 + 1.6)], a));
    }
    // karpet lounge (biru-ungu)
    this.poly([P(1.6, 10.8), P(7.0, 10.8), P(7.0, 14.6), P(1.6, 14.6)], "#2C3F78");
    this.poly([P(1.9, 11.1), P(6.7, 11.1), P(6.7, 14.3), P(1.9, 14.3)], undefined, "#6FD3FF");
    this.poly([P(2.3, 11.5), P(6.3, 11.5), P(6.3, 13.9), P(2.3, 13.9)], undefined, "#4A62B0");
    // karpet founder
    this.poly([P(17.0, 1.0), P(21.4, 1.0), P(21.4, 5.4), P(17.0, 5.4)], "#24375C");
    this.poly([P(17.3, 1.3), P(21.1, 1.3), P(21.1, 5.1), P(17.3, 5.1)], undefined, "#2D8CFF");
  }

  /* ---------- Ruang Animasi (kanan): nuansa kartun & arcade 80-an ---------- */
  private room2(ph: Phase) {
    const x0 = 22, g = this.g;
    this.poly([P(x0, 0), P(TW, 0), P(TW, 0, WALL), P(x0, 0, WALL)], "#3B1F6E");
    this.poly([P(x0, 0), P(TW, 0), P(TW, 0, 30), P(x0, 0, 30)], "#1B1440");
    this.poly([P(x0, 0, 30), P(TW, 0, 30), P(TW, 0, 32), P(x0, 0, 32)], "#FF4FA3");
    this.poly([P(x0, 0, WALL), P(TW, 0, WALL), P(TW, -0.35, WALL), P(x0, -0.35, WALL)], "#7F5BB0");
    // garis-garis retro di dinding
    [["#FFD23F", 74], ["#FF7A2F", 69], ["#F2385A", 64]].forEach(([c, z]) => this.poly(this.qy(0, x0 + 0.3, TW, (z as number) - 3, z as number), c as string));
    // poster kartun
    ([[23.0, "#19C6C6", "#FFD23F"], [33.0, "#FFD23F", "#F2385A"]] as [number, string, string][]).forEach(([x, bg, fg]) => {
      this.poly(this.qy(0, x, x + 1.6, 40, 96), "#14101F"); this.poly(this.qy(0, x + 0.08, x + 1.52, 43, 93), bg);
      const [cx, cy] = P(x + 0.8, 0, 72); g.fillStyle = fg; g.beginPath(); g.ellipse(cx, cy, 9, 10, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = "#14101F"; g.lineWidth = 2; g.stroke();
      this.poly(this.qy(0, x + 0.3, x + 1.3, 50, 56), "#14101F");
    });
    // lantai kotak-kotak ungu-toska
    for (let i = x0; i < TW; i++) for (let j = 0; j < RD; j++) {
      const c = j >= 16 ? (i < 29 ? ((i + j) % 2 ? "#231A3F" : "#2A2050") : ((i + j) % 2 ? "#3F8F5A" : "#479A63")) : (i + j) % 2 ? "#2B2F66" : "#33407A";
      this.poly([P(i - 0.02, j - 0.02), P(i + 1.02, j - 0.02), P(i + 1.02, j + 1.02), P(i - 0.02, j + 1.02)], c);
    }
    { const [cx, cy] = P(29, 7), gr = g.createRadialGradient(cx, cy, 10, cx, cy, 260);
      gr.addColorStop(0, "rgba(255,120,200,.16)"); gr.addColorStop(1, "rgba(20,10,40,.18)");
      this.poly([P(x0, 0), P(TW, 0), P(TW, RD), P(x0, RD)], gr); }
    const ao = (pts: Pt[], a: Pt, b: Pt) => { const gr = g.createLinearGradient(a[0], a[1], b[0], b[1]); gr.addColorStop(0, "rgba(10,6,30,.4)"); gr.addColorStop(1, "rgba(10,6,30,0)"); this.poly(pts, gr); };
    ao([P(x0, 0), P(TW, 0), P(TW, 0.9), P(x0, 0.9)], P(29, 0), P(29, 0.9));
    // karpet bintang di area santai
    this.poly([P(31.8, 10.6), P(35.8, 10.6), P(35.8, 14.8), P(31.8, 14.8)], "#F2385A");
    this.poly([P(32.1, 10.9), P(35.5, 10.9), P(35.5, 14.5), P(32.1, 14.5)], undefined, "#FFD23F");
    // neon ANIMASI
    const glyph: Record<string, string[]> = {
      A: ["010", "101", "111", "101", "101"], N: ["101", "111", "111", "111", "101"], I: ["111", "010", "010", "010", "111"],
      M: ["101", "111", "111", "101", "101"], S: ["111", "100", "111", "001", "111"],
    };
    g.save(); g.shadowColor = "#FF4FA3"; g.shadowBlur = ph.night ? 12 : 6;
    let x = 26.2;
    for (const ch of "ANIMASI") {
      glyph[ch].forEach((row, r) => [...row].forEach((b, c) => { if (b === "1") this.poly(this.qy(0, x + c * 0.13, x + c * 0.13 + 0.1, 92 - r * 3.4, 94.6 - r * 3.4), "#FFC2E2"); }));
      x += 0.52;
    }
    g.restore();
  }
  private partisi() {
    // dinding kaca pemisah kantor Shorts ↔ Ruang Animasi, dengan pintu
    const kaca = (y0: number, y1: number) => {
      this.poly(this.qx(22.3, y0, y1, 0, 70), "rgba(255,170,230,.18)"); this.poly(this.qx(22.3, y0, y1, 66, 72), "#8F6BB8"); this.poly(this.qx(22.3, y0, y1, 0, 4), "#8F6BB8");
    };
    for (let y = 0; y < PINTU[0]; y += 1.1) kaca(y, Math.min(PINTU[0], y + 1.1));
    for (let y = PINTU[1]; y < RD; y += 1.1) kaca(y, Math.min(RD, y + 1.1));
    this.poly(this.qx(22.3, PINTU[0], PINTU[1], 70, 80), "#14101F");
    this.poly(this.qx(22.3, PINTU[0] + 0.2, PINTU[1] - 0.2, 72, 78), "#FFD23F");
  }
  private arcade(): BBox {
    const top = this.box(34.7, 0.15, 1.1, 0.9, 72, "#6B3FD4");
    this.poly(this.qy(1.05, 34.8, 35.7, 40, 64), "#14101F");
    const on = (this.tick >> 3) % 2;
    this.poly(this.qy(1.05, 34.86, 35.64, 43, 61), on ? "#19C6C6" : "#39D36B");
    this.poly(this.qy(1.05, 35.0, 35.5, 50, 54), "#FFD23F");
    this.box(34.75, 1.05, 1.0, 0.25, 4, "#F2385A", 30);
    return bboxOf([...top, P(34.7, 1.05), P(35.8, 1.05)]);
  }
  private crt() {
    this.box(23.1, 13.5, 2.2, 1.3, 20, "#5B3A28");
    [[23.25, 0], [24.25, 0], [23.75, 20]].forEach(([x, z], i) => {
      this.box(x, 13.65, 0.9, 0.9, 18, "#2A2440", 20 + z);
      this.poly(this.qy(14.55, x + 0.1, x + 0.8, 24 + z, 35 + z), ["#19C6C6", "#F2385A", "#FFD23F"][(i + (this.tick >> 4)) % 3]);
    });
  }
  private mejaCahaya() {
    this.box(25.9, 10.9, 2.4, 1.2, 22, "#E8E1F2");
    this.poly([P(26.1, 11.05, 22.5), P(28.1, 11.05, 22.5), P(28.1, 11.95, 22.5), P(26.1, 11.95, 22.5)], "#FFF8D8");
    const [cx, cy] = P(27.1, 11.5, 23); this.g.strokeStyle = "#14101F"; this.g.lineWidth = 1.5; this.g.beginPath(); this.g.ellipse(cx, cy - 2, 6, 4, 0, 0, Math.PI * 2); this.g.stroke();
    this.mug(27.9, 11.2, 25, "#FF4FA3");
  }
  private sofaRetro() {
    this.box(32.6, 13.4, 3.2, 1.0, 10, "#F2385A"); this.box(32.6, 14.1, 3.2, 0.35, 26, "#C42A4A");
    this.box(32.6, 11.6, 0.9, 2.5, 18, "#C42A4A"); this.box(32.6, 11.6, 0.4, 2.5, 26, "#C42A4A");
    this.box(33.6, 13.5, 0.7, 0.6, 5, "#FFD23F", 10); this.box(34.5, 13.5, 0.7, 0.6, 5, "#19C6C6", 10);
  }

  /* ---------- objek dinding ---------- */
  private whiteboard(): Hit {
    const st = this.state, q = this.qy(0, 1.0, 5.4, 44, 96);
    this.poly(this.qy(0, 0.9, 5.5, 42, 98), "#55687F"); this.poly(q, "#F8FAFD");
    const cols = [["ide", "#FF9A4D"], ["disetujui", "#47B5FF"], ["naskah", "#6FD29A"], ["terbit", "#F2C94C"]] as const;
    cols.forEach(([status, color], ci) => {
      const x0 = 1.0 + ci * 1.1, n = (st?.videos ?? []).filter((v) => v.status === status).length;
      if (ci) { const g = this.g; g.strokeStyle = "#D2DAE6"; g.beginPath(); g.moveTo(...P(x0, 0, 48)); g.lineTo(...P(x0, 0, 90)); g.stroke(); }
      this.poly(this.qy(0, x0 + 0.12, x0 + 0.98, 89, 93), color);
      for (let k = 0; k < Math.min(n, 8); k++) {
        const r = Math.floor(k / 2), c = k % 2, z1 = 85 - r * 10;
        this.poly(this.qy(0, x0 + 0.1 + c * 0.47, x0 + 0.5 + c * 0.47, z1 - 7, z1), color);
        this.poly(this.qy(0, x0 + 0.14 + c * 0.47, x0 + 0.42 + c * 0.47, z1 - 3, z1 - 2), shade(color, 0.7));
      }
    });
    this.poly(this.qy(0, 1.0, 5.4, 42, 44), "#8494AA");
    this.poly(this.qy(0, 4.6, 5.0, 44, 46), "#F07178"); this.poly(this.qy(0, 4.1, 4.5, 44, 46), "#2C3B57");
    return { id: "queue", label: "Papan antrean video", bbox: bboxOf(q), person: false };
  }
  /** Layar "Jadwal tayang" di dinding kiri (di atas sofa): tiap baris = satu slot (hari ini → besok), warna = status. */
  private layarJadwal(ph: Phase): Hit {
    const st = this.state, q = this.qx(0, 11.95, 14.6, 46, 98), g = this.g;
    this.poly(this.qx(0, 11.85, 14.7, 44, 100), "#141B27"); this.poly(q, ph.night ? "#081426" : "#0A1828");
    this.poly(this.qx(0, 11.95, 14.6, 92, 98), "#2D8CFF");                                     // kepala layar biru khas
    for (let k = 0; k < 4; k++) this.poly(this.qx(0, 12.1 + k * 0.32, 12.32 + k * 0.32, 93.5, 96.5), "#E8F2FF");   // "tulisan" judul
    const warna: Record<string, string> = { tayang: "#6FD29A", terjadwal: "#47B5FF", dibuat: "#FF9A4D", kosong: "#33445E", terlewat: "#F07178" };
    const items = (st?.jadwal?.hari ?? []).flatMap((h) => h.item).filter((i) => i.status !== "terlewat").slice(0, 6);
    items.forEach((it, r) => {
      const z1 = 89 - r * 7, z0 = z1 - 5, kedip = it.status === "dibuat" && (this.tick >> 3) % 2 === 0;
      this.poly(this.qx(0, 12.05, 12.55, z0, z1), "#C9D6E8");                                   // jam
      this.poly(this.qx(0, 12.7, 13.0, z0 - 0.5, z1 + 0.5), it.slug ? "#7FA6D6" : "#1C2A40");   // sampul kecil
      this.poly(this.qx(0, 13.15, 14.45, z0 + 1, z1 - 1), kedip ? "#FFD3A8" : warna[it.status] ?? "#33445E");
    });
    if (!items.length) this.poly(this.qx(0, 12.6, 14.0, 66, 72), "#1E3A5A");
    this.poly(this.qx(0, 11.95, 14.6, 44, 46), "#2A3446");
    if (ph.night) { const [cx, cy] = P(0.2, 13.3, 70), gr = g.createRadialGradient(cx, cy, 2, cx, cy, 60);
      gr.addColorStop(0, "rgba(70,150,255,.16)"); gr.addColorStop(1, "rgba(70,150,255,0)"); g.fillStyle = gr; g.fillRect(cx - 60, cy - 60, 120, 120); }
    return { id: "jadwal", label: "Layar jadwal tayang", bbox: bboxOf(q), person: false };
  }
  private tv(): Hit {
    const st = this.state, q = this.qy(0, 6.2, 9.4, 50, 88);
    this.poly(this.qy(0, 6.1, 9.5, 48, 90), "#141B27"); this.poly(q, "#0A1828");
    const vids = st?.snapshot ? [...st.snapshot.videos].sort((a, b) => a.published.localeCompare(b.published)).slice(-16) : [];
    if (vids.length) {
      const mx = Math.max(...vids.map((v) => v.views)), step = 3.0 / vids.length;
      vids.forEach((v, i) => { const x0 = 6.3 + i * step, h = 4 + (28 * v.views) / mx;
        this.poly(this.qy(0, x0, x0 + step * 0.72, 54, 54 + h), v.tier === "menang" ? "#FF9A4D" : v.tier === "lemah" ? "#5A7393" : "#47B5FF"); });
      const mz = 54 + (28 * st!.snapshot!.summary.median_views) / mx, g = this.g;
      g.strokeStyle = "#ECF2F8"; g.setLineDash([2, 2]); g.beginPath(); g.moveTo(...P(6.3, 0, mz)); g.lineTo(...P(9.3, 0, mz)); g.stroke(); g.setLineDash([]);
    } else this.poly(this.qy(0, 7.4, 8.2, 64, 72), "#1E3A5A");
    this.px(P(9.2, 0, 52)[0] - 1, P(9.2, 0, 52)[1] - 1, 2, 2, "#6FD29A");
    return { id: "analytics", label: "Layar analitik Shorts", bbox: bboxOf(q), person: false };
  }
  private neon(ph: Phase) {
    const glyph: Record<string, string[]> = {
      Y: ["101", "101", "010", "010", "010"], O: ["111", "101", "101", "101", "111"], F: ["111", "100", "110", "100", "100"],
      A: ["010", "101", "111", "101", "101"], M: ["101", "111", "111", "101", "101"],
    };
    const g = this.g; g.save();
    g.shadowColor = "#2D8CFF"; g.shadowBlur = ph.night ? 10 : 5;
    let x = 10.15;
    for (const ch of "YOFAMO") {
      glyph[ch].forEach((row, r) => [...row].forEach((b, c) => { if (b === "1") this.poly(this.qy(0, x + c * 0.13, x + c * 0.13 + 0.1, 90 - r * 3.4, 92.6 - r * 3.4), "#BFEAFF"); }));
      x += 0.5;
    }
    g.restore();
    // rak dinding kecil + plakat channel di bawah neon
    this.poly(this.qy(0, 10.2, 12.8, 56, 58), "#2A1C15");
    this.poly(this.qy(0, 10.45, 11.15, 58, 70), "#F2C94C"); this.poly(this.qy(0, 10.55, 11.05, 60, 68), "#1C2E50");
    this.poly([P(10.72, 0, 61), P(10.72, 0, 67), P(10.92, 0, 64)], "#6FD3FF");
    this.poly(this.qy(0, 11.5, 11.8, 58, 66), "#6FD3FF"); this.poly(this.qy(0, 12.0, 12.5, 58, 63), "#ECF2F8");
    this.poly(this.qy(0, 10.4, 12.6, 36, 50), "#0E1A30"); this.poly(this.qy(0, 10.5, 12.5, 38, 48), ph.night ? "#16305A" : "#1C3A6C");
    for (let k = 0; k < 6; k++) this.poly(this.qy(0, 10.6 + k * 0.32, 10.8 + k * 0.32, 40, 41 + ((k * 3 + this.tick) % 6)), "#6FD3FF");
  }
  private door() {
    this.poly(this.qy(0, 14.6, 15.7, 0, 76), "#7C5233"); this.poly(this.qy(0, 14.72, 15.58, 4, 72), "#9C6A42");
    this.poly(this.qy(0, 14.8, 15.5, 40, 68), "#A9774D"); this.poly(this.qy(0, 14.8, 15.5, 8, 36), "#A9774D");
    this.poly(this.qy(0, 15.4, 15.5, 36, 40), "#F2C94C");
    this.poly(this.qy(0, 14.7, 15.6, 80, 88), "#121A26"); this.poly(this.qy(0, 14.8, 15.5, 82, 86), "#6FD29A");
    const [x, y] = P(15.15, 0, 100), g = this.g, d = new Date();
    g.fillStyle = "#F7F9FC"; g.beginPath(); g.ellipse(x, y, 6, 7, 0, 0, Math.PI * 2); g.fill(); g.strokeStyle = "#4A5A70"; g.stroke();
    const hA = (((d.getHours() % 12) + d.getMinutes() / 60) / 12) * Math.PI * 2, mA = (d.getMinutes() / 60) * Math.PI * 2;
    g.strokeStyle = "#1A2638"; g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.sin(hA) * 3, y - Math.cos(hA) * 3.5); g.moveTo(x, y); g.lineTo(x + Math.sin(mA) * 4.5, y - Math.cos(mA) * 5); g.stroke();
  }

  /* ---------- objek lantai ---------- */
  private monitor(mx: number, y: number, w: number, screen: string, art?: (x0: number, x1: number) => void) {
    this.poly([P(mx + w / 2 - 0.05, y + 0.38, 25), P(mx + w / 2 + 0.05, y + 0.38, 25), P(mx + w / 2 + 0.05, y + 0.38, 31), P(mx + w / 2 - 0.05, y + 0.38, 31)], "#3B4759");
    this.box(mx + w / 2 - 0.15, y + 0.3, 0.3, 0.2, 1, "#4A5668", 25);
    this.poly(this.qy(y + 0.32, mx, mx + w, 30, 47), "#1F2938");
    this.poly(this.qy(y + 0.32, mx + 0.05, mx + w - 0.05, 32, 45), screen);
    art?.(mx + 0.08, mx + w - 0.08);
  }
  private desk(x: number, y: number, o: { w?: number; d?: number; top?: string; legs?: string; screens: number; screen: (i: number) => string; art?: (i: number, x0: number, x1: number) => void; extra?: () => void; glow?: string }) {
    const w = o.w ?? 2, d = o.d ?? 1, legs = o.legs ?? "#E5EAF0";
    { const g = this.g, [cx, cy] = P(x + w / 2 + 0.1, y + d / 2 + 0.15), gr = g.createRadialGradient(cx, cy, 4, cx, cy, 30 + w * 8);   // bayangan lembut di lantai
      gr.addColorStop(0, "rgba(28,18,8,.26)"); gr.addColorStop(1, "rgba(28,18,8,0)");
      this.poly([P(x - 0.25, y - 0.1), P(x + w + 0.3, y - 0.1), P(x + w + 0.3, y + d + 0.4), P(x - 0.25, y + d + 0.4)], gr); }
    if (o.glow) { const g = this.g, [cx, cy] = P(x + w / 2, y + d / 2), gr = g.createRadialGradient(cx, cy, 2, cx, cy, 34); gr.addColorStop(0, o.glow + "55"); gr.addColorStop(1, o.glow + "00"); g.fillStyle = gr; g.fillRect(cx - 34, cy - 34, 68, 68); }
    for (const [a, b] of [[0.06, 0.06], [w - 0.16, 0.06], [0.06, d - 0.16], [w - 0.16, d - 0.16]]) this.box(x + a, y + b, 0.1, 0.1, 22, legs);
    this.box(x + 0.1, y + 0.08, w - 0.2, 0.06, 8, shade(legs, 0.9), 14);
    const top = this.box(x, y, w, d, 3, o.top ?? "#E9EDF2", 22);
    if (o.glow) this.poly([P(x, y + d, 21), P(x + w, y + d, 21), P(x + w, y + d, 22), P(x, y + d, 22)], o.glow);
    for (let i = 0; i < o.screens; i++) {
      const mw = 0.78, mx = x + (w - o.screens * mw - (o.screens - 1) * 0.08) / 2 + i * (mw + 0.08);
      this.monitor(mx, y, mw, o.screen(i), o.art ? (a, b) => o.art!(i, a, b) : undefined);
    }
    this.poly([P(x + w / 2 - 0.38, y + 0.62, 25.5), P(x + w / 2 + 0.38, y + 0.62, 25.5), P(x + w / 2 + 0.38, y + 0.84, 25.5), P(x + w / 2 - 0.38, y + 0.84, 25.5)], "#2F3A4B");
    this.poly([P(x + w / 2 - 0.34, y + 0.65, 26), P(x + w / 2 + 0.34, y + 0.65, 26), P(x + w / 2 + 0.34, y + 0.8, 26), P(x + w / 2 - 0.34, y + 0.8, 26)], "#4C596C");
    o.extra?.();
    return bboxOf([...top, P(x, y + d), P(x + w, y + d), P(x, y + 0.3, 47), P(x + w, y + 0.3, 47)]);
  }
  private mug(x: number, y: number, z: number, c: string) { this.box(x, y, 0.14, 0.14, 5, c, z); const [a, b] = P(x + 0.14, y + 0.07, z + 3); this.px(a, b - 1, 2, 2, shade(c, 0.7)); }
  private chairBase(x: number, y: number) {
    const [cx, cy] = P(x, y); this.px(cx - 6, cy - 1, 12, 2, "#2A3240"); this.px(cx - 1, cy - 4, 2, 4, "#3B4556");
    this.box(x - 0.24, y - 0.24, 0.48, 0.48, 3, "#2F3B4F", 9);
  }
  private chairBack(x: number, y: number, c: string) { this.box(x - 0.28, y + 0.2, 0.56, 0.09, 14, c, 13); this.box(x - 0.2, y + 0.2, 0.4, 0.09, 3, shade(c, 1.25), 27); this.box(x - 0.03, y + 0.22, 0.06, 0.06, 4, "#3B4556", 9); }
  /** Barang pribadi di meja tiap agent (kecil, khas pekerjaannya). */
  private barangMeja(id: string, x: number, y: number) {
    const z = 25, buku = (bx: number, by: number, cols: string[]) => cols.forEach((c, k) => this.box(bx, by, 0.3, 0.2, 2, c, z + k * 2));
    switch (id) {
      case "steve": this.box(x + 0.52, y + 0.6, 0.28, 0.22, 1, "#FDFBF4", z); { const [a, b] = P(x + 0.58, y + 0.78, z + 1); this.px(a, b - 2, 1, 2, "#47B5FF"); this.px(a + 2, b - 3, 1, 3, "#FF9A4D"); this.px(a + 4, b - 1, 1, 1, "#47B5FF"); } break;
      case "nova": buku(x + 0.5, y + 0.62, ["#6FD29A", "#F2C94C", "#F07178"]); break;
      case "raka": this.box(x + 0.5, y + 0.6, 0.3, 0.22, 1, "#FFE9B8", z); this.box(x + 0.84, y + 0.62, 0.04, 0.2, 1, "#FF9A4D", z); break;
      case "bima": this.box(x + 0.5, y + 0.62, 0.26, 0.18, 5, "#2A3240", z); this.box(x + 0.58, y + 0.8, 0.1, 0.04, 3, "#4FD1C5", z + 1); break;
      case "mila": this.box(x + 0.48, y + 0.58, 0.36, 0.26, 1, "#2A3240", z); this.box(x + 0.51, y + 0.6, 0.3, 0.2, 1, "#FF6BCB", z + 0.5); break;
      case "kai": this.box(x + 0.52, y + 0.62, 0.22, 0.16, 4, "#1A1F2B", z); this.box(x + 0.52, y + 0.62, 0.05, 0.16, 7, "#F2C94C", z); this.box(x + 0.69, y + 0.62, 0.05, 0.16, 7, "#F2C94C", z); break;
      case "rara": this.box(x + 0.52, y + 0.62, 0.3, 0.2, 1, "#FDFBF4", z); this.box(x + 0.6, y + 0.66, 0.12, 0.1, 5, "#E05A66", z + 1); break;
      case "uli": this.box(x + 0.58, y + 0.64, 0.1, 0.1, 9, "#ECF2F8", z); this.box(x + 0.58, y + 0.64, 0.1, 0.1, 3, "#FF4D4D", z + 9); this.box(x + 0.54, y + 0.62, 0.18, 0.14, 2, "#4E7BD9", z); break;
      case "dara": buku(x + 0.5, y + 0.62, ["#C792EA", "#F4F1E8"]); break;
      case "bayu": buku(x + 0.5, y + 0.62, ["#FF7A2F", "#FFD23F", "#19C6C6"]); break;
      case "citra": this.box(x + 0.5, y + 0.6, 0.3, 0.22, 1, "#FFF4DC", z); this.box(x + 0.84, y + 0.62, 0.04, 0.2, 1, "#F2385A", z); break;
      case "laras": this.box(x + 0.5, y + 0.62, 0.26, 0.18, 5, "#2A2440", z); this.box(x + 0.58, y + 0.8, 0.1, 0.04, 3, "#FFD23F", z + 1); break;
      case "tio": this.box(x + 0.48, y + 0.58, 0.36, 0.26, 1, "#2A2440", z); this.box(x + 0.51, y + 0.6, 0.3, 0.2, 1, "#6B3FD4", z + 0.5); break;
      case "wulan": this.box(x + 0.52, y + 0.62, 0.3, 0.2, 1, "#FDFBF4", z); this.box(x + 0.6, y + 0.66, 0.12, 0.1, 5, "#39D36B", z + 1); break;
      case "gilang": this.box(x + 0.6, y + 0.3, 0.06, 0.06, 12, "#2A3240", z); this.box(x + 0.55, y + 0.25, 0.16, 0.12, 6, "#14101F", z + 12); break;
    }
  }
  private plant(x: number, y: number, s = 1) {
    this.box(x - 0.2 * s, y - 0.2 * s, 0.4 * s, 0.4 * s, 12 * s, "#C2734F");
    const [cx, cy] = P(x, y, 12 * s), g = this.g;
    [[0, -12, "#2F7D4C", 7], [-6, -8, "#3E9A5E", 6], [6, -9, "#3E9A5E", 6], [-3, -17, "#4DB36E", 6], [4, -16, "#4DB36E", 6], [0, -22, "#6FD29A", 5], [-7, -14, "#5CC77E", 4], [7, -15, "#2F7D4C", 4]].forEach(([dx, dy, c, r]) => {
      g.fillStyle = c as string; g.beginPath(); g.ellipse(cx + (dx as number) * s, cy + (dy as number) * s, (r as number) * s, (r as number) * 1.1 * s, 0, 0, Math.PI * 2); g.fill();
    });
  }
  private shelf(): BBox {
    const top = this.box(0.05, 9.9, 0.75, 1.6, 60, "#6E4A30"), cols = ["#47B5FF", "#FF9A4D", "#6FD29A", "#F2C94C", "#C76BD9", "#F07178", "#ECF2F8"];
    for (let r = 0; r < 4; r++) {
      this.poly(this.qx(0.8, 9.92, 11.48, 4 + r * 14, 5 + r * 14), "#4E3422");
      for (let b = 0; b < 8; b++) { const y0 = 9.98 + b * 0.18, h = 9 + ((b * 3 + r) % 4); this.poly(this.qx(0.8, y0, y0 + 0.14, 5 + r * 14, 5 + r * 14 + h), cols[(b + r * 2) % cols.length]); }
    }
    return bboxOf([...top, P(0.8, 11.5), P(0.05, 11.5)]);
  }
  private server(): BBox {
    const top = this.box(13.25, 0.1, 1.05, 0.8, 78, "#1E2633");
    const busy = !!kerjaShorts(this.state);
    for (let r = 0; r < 9; r++) {
      const z = 8 + r * 8; this.poly(this.qy(0.9, 13.3, 14.25, z, z + 6), "#2A3444");
      for (let l = 0; l < 4; l++) { const on = (this.tick + r * 3 + l * 5) % (busy ? 4 : 11) < 2; this.poly(this.qy(0.9, 13.4 + l * 0.12, 13.47 + l * 0.12, z + 2, z + 4), on ? (l % 2 ? "#6FD29A" : "#47B5FF") : "#3A4658"); }
    }
    return bboxOf([...top, P(13.25, 0.9), P(14.3, 0.9)]);
  }
  private sofa() {
    this.box(0.25, 11.9, 1.15, 2.6, 10, "#5B6FD6");
    this.box(0.25, 11.9, 0.35, 2.6, 26, "#4A5CC0");
    this.box(0.25, 11.9, 1.15, 0.3, 18, "#4A5CC0"); this.box(0.25, 14.2, 1.15, 0.3, 18, "#4A5CC0");
    this.box(0.62, 12.25, 0.7, 0.9, 4, "#6F82E6", 10); this.box(0.62, 13.2, 0.7, 0.9, 4, "#6F82E6", 10);
    this.box(0.62, 12.6, 0.25, 0.4, 7, "#F2C94C", 14);
  }
  private coffeeTable() {
    this.box(2.7, 12.1, 1.2, 0.9, 10, "#3A2A20"); this.box(2.65, 12.05, 1.3, 1.0, 2, "#8A5A36", 10);
    this.box(2.95, 12.3, 0.4, 0.3, 2, "#F4F1E8", 12); this.mug(3.5, 12.6, 12, "#FF9A4D");
  }
  private beanbag(x: number, y: number, c: string) {
    const [cx, cy] = P(x, y), g = this.g;
    g.fillStyle = shade(c, 0.75); g.beginPath(); g.ellipse(cx, cy - 4, 12, 7, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = c; g.beginPath(); g.ellipse(cx, cy - 7, 10, 6, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = shade(c, 1.15); g.fillRect(cx - 4, cy - 10, 4, 1);
  }
  private pantry() {
    this.box(9.1, 13.7, 4.2, 1.2, 26, "#E8ECF2"); this.box(9.05, 13.65, 4.3, 1.3, 3, "#5A6B80", 26);
    for (let i = 0; i < 4; i++) this.poly(this.qy(14.9, 9.3 + i * 1.02, 10.2 + i * 1.02, 4, 22), "#D3DAE3");
    // mesin kopi
    this.box(10.6, 13.85, 0.6, 0.5, 18, "#2A3240", 29); this.box(10.7, 13.95, 0.4, 0.3, 4, "#FF9A4D", 47);
    this.mug(10.85, 14.15, 29, "#F4F1E8");
    this.box(12.0, 13.9, 0.8, 0.6, 3, "#C9A06B", 29);
    for (let k = 0; k < 4; k++) { const [a, b] = P(12.2 + k * 0.14, 14.15, 33); this.px(a, b, 3, 2, ["#C8462C", "#F2C94C", "#6FD29A", "#C8462C"][k]); }
  }
  private cooler() {
    this.box(13.95, 13.8, 0.55, 0.55, 30, "#E6EBF2");
    const [cx, cy] = P(14.22, 14.08, 30), g = this.g;
    g.fillStyle = "#7CC6F2"; g.beginPath(); g.ellipse(cx, cy - 8, 6, 9, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "rgba(255,255,255,.5)"; g.fillRect(cx - 3, cy - 13, 1, 7);
    this.px(cx - 2, cy - 18, 4, 2, "#3C8FC2");
    this.box(14.65, 13.7, 0.65, 0.75, 52, "#DDE3EA");
    this.poly(this.qx(15.3, 13.8, 14.4, 30, 31), "#9AA8BA"); this.poly(this.qx(15.3, 13.82, 13.9, 34, 46), "#9AA8BA");
  }
  private roundTable() {
    const [cx, cy] = P(11.2, 10.5), g = this.g;
    this.px(cx - 1, cy - 20, 2, 20, "#3B4556");
    g.fillStyle = "#9C6A42"; g.beginPath(); g.ellipse(cx, cy - 21, 16, 8, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#B98A5C"; g.beginPath(); g.ellipse(cx, cy - 22, 15, 7, 0, 0, Math.PI * 2); g.fill();
    this.px(cx - 6, cy - 25, 5, 3, "#F4F1E8"); this.px(cx + 3, cy - 26, 3, 4, "#47B5FF");
  }
  private glassX(y0: number, y1: number) {
    this.poly(this.qx(16, y0, y1, 0, 64), "rgba(170,215,245,.22)"); this.poly(this.qx(16, y0, y1, 62, 66), "#8FA3BA");
    this.poly(this.qx(16, y0, y1, 0, 4), "#8FA3BA");
    const g = this.g; g.strokeStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.moveTo(...P(16, y0 + 0.2, 12)); g.lineTo(...P(16, y0 + 0.5, 50)); g.stroke();
  }
  private glassY(x0: number, x1: number) {
    this.poly(this.qy(6, x0, x1, 0, 64), "rgba(170,215,245,.22)"); this.poly(this.qy(6, x0, x1, 62, 66), "#8FA3BA");
    this.poly(this.qy(6, x0, x1, 0, 4), "#8FA3BA");
    const g = this.g; g.strokeStyle = "rgba(255,255,255,.35)"; g.beginPath(); g.moveTo(...P(x0 + 0.2, 6, 12)); g.lineTo(...P(x0 + 0.5, 6, 50)); g.stroke();
  }
  private trophyCabinet() {
    const subs = this.state?.snapshot?.channel.subscribers ?? 0;
    this.box(20.5, 0.15, 1.3, 0.65, 34, "#6E4A30");
    this.box(20.7, 0.3, 0.3, 0.3, 10, subs >= 1000 ? "#F2C94C" : "#7B8798", 34);
    this.box(21.2, 0.3, 0.3, 0.3, 14, subs >= 10000 ? "#F2C94C" : "#3B4556", 34);
    this.poly(this.qy(0, 20.6, 21.6, 58, 80), "#F2C94C"); this.poly(this.qy(0, 20.7, 21.5, 61, 77), "#1E2633");
    this.poly([P(20.95, 0, 64), P(20.95, 0, 74), P(21.25, 0, 69)], "#FF5C5C");
  }

  private person(look: Look, id: string, x: number, y: number, pose: Pose, facing: "front" | "back", frame: number, lift = 0, emo: Emote | null = null): BBox {
    const [sx, sy] = P(x, y), g = this.g, duduk = pose === "sit" || pose === "sleep", K = SKALA;
    const lompat = pose === "cheer" ? (frame % 2 ? 4 : 1) : 0;
    g.fillStyle = "rgba(0,0,0,.24)"; g.beginPath(); g.ellipse(sx, sy, (lompat ? 5 : 6.5) * K * 0.8, (lompat ? 2 : 2.6) * K * 0.8, 0, 0, Math.PI * 2); g.fill();
    const img = sprite(look, id, pose, facing, frame), w = 12 * K, h = img.height * K;
    const goyang = pose === "walk" ? (frame % 2 ? -1 : 0) : pose === "sleep" ? 2 : 0;
    const top = Math.round((duduk ? sy - h - 9 : sy - h) + goyang - lift - lompat);
    g.drawImage(img, Math.round(sx - w / 2), top, w, h);
    if (emo) {
      const e = emote(emo, Math.floor(this.tick / 4)), naik = emo === "zzz" || emo === "note" ? Math.round(Math.sin(this.waktu * 2.2 + sx) * 1.5) : emo === "bintang" ? -(frame % 2) * 2 : 0;
      g.drawImage(e, Math.round(sx + (emo === "zzz" ? 4 : -9)), top - 19 + naik, 18, 18);
    }
    return [sx - w / 2 - 1, top - 1, sx + w / 2 + 1, sy + 2];
  }

  /* ---------- ruang depan: Meeting, Istirahat, Studio Suara, Taman ---------- */
  private kacaY(y: number, x0: number, x1: number, warna = "rgba(170,215,245,.22)", rangka = "#8FA3BA") {
    this.poly(this.qy(y, x0, x1, 0, 60), warna); this.poly(this.qy(y, x0, x1, 58, 62), rangka); this.poly(this.qy(y, x0, x1, 0, 4), rangka);
    const g = this.g; g.strokeStyle = "rgba(255,255,255,.3)"; g.beginPath(); g.moveTo(...P(x0 + 0.2, y, 12)); g.lineTo(...P(x0 + 0.5, y, 46)); g.stroke();
  }
  private kacaX(x: number, y0: number, y1: number, warna = "rgba(170,215,245,.2)", rangka = "#8FA3BA") {
    this.poly(this.qx(x, y0, y1, 0, 60), warna); this.poly(this.qx(x, y0, y1, 58, 62), rangka); this.poly(this.qx(x, y0, y1, 0, 4), rangka);
  }
  /** Layar presentasi di dinding kiri Ruang Meeting: grafik views (naik-turun pelan). */
  private layarRapat() {
    const q = this.qx(0, 16.6, 20.6, 44, 96);
    this.poly(this.qx(0, 16.5, 20.7, 42, 98), "#141B27"); this.poly(q, "#0B1A30");
    this.poly(this.qx(0, 16.6, 20.6, 90, 96), "#2D8CFF");
    for (let k = 0; k < 9; k++) { const h = 8 + ((k * 7 + (this.tick >> 4)) % 5) * 2 + k * 3.2; this.poly(this.qx(0, 16.9 + k * 0.4, 17.15 + k * 0.4, 50, 50 + h), k === 8 ? "#FF9A4D" : "#6FD3FF"); }
  }
  private ruangDepan(objs: { key: number; draw: () => BBox | void }[]) {
    const push = (key: number, draw: () => void) => objs.push({ key, draw });
    // sekat kaca di sepanjang y = SEKAT (pintu: celah) + sekat antar ruang
    const ruas: [number, number, string, string][] = [[0, 4.2, "rgba(170,215,245,.22)", "#8FA3BA"], [5.8, 15.2, "rgba(170,215,245,.22)", "#8FA3BA"], [16.8, 22, "rgba(170,215,245,.22)", "#8FA3BA"],
      [22.6, 25.0, "rgba(255,170,230,.18)", "#8F6BB8"], [26.4, 31.6, "rgba(255,170,230,.18)", "#8F6BB8"], [33.2, 36, "rgba(255,170,230,.18)", "#8F6BB8"]];
    for (const [x0, x1, w, r] of ruas) for (let x = x0; x < x1 - 0.01; x += 1) { const b = Math.min(x1, x + 1); push(x + (b - x) / 2 + SEKAT + 0.01, () => this.kacaY(SEKAT, x, b, w, r)); }
    for (const [x, w, r] of [[10, "rgba(170,215,245,.2)", "#8FA3BA"], [29, "rgba(255,170,230,.16)", "#8F6BB8"]] as [number, string, string][])
      for (let y = SEKAT; y < RD - 0.01; y += 1.1) { const b = Math.min(RD, y + 1.1); push(x + y + (b - y) / 2 + 0.01, () => this.kacaX(x, y, b, w, r)); }
    // Ruang Meeting: meja panjang, laptop, kursi
    push(5 + 18.7 + 0.6, () => {
      const g = this.g, [cx, cy] = P(5.1, 18.9), gr = g.createRadialGradient(cx, cy, 4, cx, cy, 70); gr.addColorStop(0, "rgba(10,14,30,.3)"); gr.addColorStop(1, "rgba(10,14,30,0)");
      this.poly([P(2.2, 17.4), P(7.9, 17.4), P(7.9, 20.2), P(2.2, 20.2)], gr);
      for (const [a, b] of [[2.9, 17.95], [6.9, 17.95], [2.9, 19.3], [6.9, 19.3]]) this.box(a, b, 0.14, 0.14, 20, "#2A2F3A");
      this.box(2.7, 17.8, 4.6, 1.8, 3, "#9C6A42", 20);
      for (let k = 0; k < 3; k++) { this.box(3.3 + k * 1.5, 18.0, 0.5, 0.34, 1, "#C9D3E0", 23); this.box(3.3 + k * 1.5, 18.0, 0.5, 0.05, 6, "#2A3444", 24); this.box(3.5 + k * 1.5, 19.0, 0.4, 0.3, 1, "#FDFBF4", 23); }
      this.mug(4.4, 18.8, 23, "#47B5FF"); this.mug(6.2, 18.5, 23, "#FF9A4D");
    });
    KURSI_RAPAT.forEach(([x, y], k) => { push(x + y - 0.05, () => this.chairBase(x, y)); if (y > 18.7) push(x + y + 0.06, () => this.chairBack(x, y, ["#2D5FA8", "#3F8FD6"][k % 2])); });
    push(1.0 + 16.2, () => this.plant(1.0, 16.3, 1.1)); push(9.2 + 21.3, () => this.plant(9.2, 21.3, 1.0));
    // Ruang Istirahat: sofa L kuning, karpet, meja, foosball, mesin jajan
    push(10.5 + 15.9, () => { this.poly([P(12.4, 16.4), P(15.6, 16.4), P(15.6, 19.9), P(12.4, 19.9)], "#C2553F"); this.poly([P(12.7, 16.7), P(15.3, 16.7), P(15.3, 19.6), P(12.7, 19.6)], undefined, "#FFD23F"); });
    push(10.7 + 18.4, () => { this.box(10.7, 16.3, 1.3, 4.0, 10, "#F0B24A"); this.box(10.7, 16.3, 0.4, 4.0, 26, "#D9962E"); this.box(11.1, 16.6, 0.8, 1.1, 4, "#F7C566", 10); this.box(11.1, 17.9, 0.8, 1.1, 4, "#F7C566", 10); this.box(11.15, 19.1, 0.5, 0.5, 6, "#2D8CFF", 14); });
    push(12.5 + 21.0, () => { this.box(10.7, 20.2, 3.6, 1.1, 10, "#F0B24A"); this.box(10.7, 21.0, 3.6, 0.35, 26, "#D9962E"); this.box(12.2, 20.35, 0.9, 0.6, 4, "#F7C566", 10); this.box(13.3, 20.35, 0.9, 0.6, 4, "#F7C566", 10); });
    push(13.9 + 18.2, () => { this.box(13.4, 17.7, 1.1, 0.9, 9, "#3A2A20"); this.box(13.35, 17.65, 1.2, 1.0, 2, "#8A5A36", 9); this.mug(13.6, 18.0, 11, "#F07178"); this.box(14.0, 18.0, 0.35, 0.25, 2, "#FDFBF4", 11); });
    push(17.2 + 19.0, () => {
      for (const [a, b] of [[16.55, 18.55], [17.75, 18.55], [16.55, 19.2], [17.75, 19.2]]) this.box(a, b, 0.1, 0.1, 16, "#3B2A20");
      this.box(16.45, 18.45, 1.5, 0.95, 5, "#6E4A30", 16); this.box(16.55, 18.55, 1.3, 0.75, 1, "#2F9D5C", 20);
      for (let k = 0; k < 4; k++) { const x = 16.7 + k * 0.33, geser = Math.sin(this.waktu * 3 + k) * 0.08; this.box(x, 18.4, 0.03, 1.05, 1, "#C9D3E0", 23); this.box(x - 0.03, 18.75 + geser, 0.09, 0.12, 4, k % 2 ? "#F2385A" : "#2D8CFF", 21); }
    });
    push(21.2 + 16.6, () => {
      this.box(20.7, 15.9, 1.1, 1.0, 58, "#D8403A"); this.poly(this.qy(16.9, 20.8, 21.5, 16, 52), "#1A2233");
      for (let r = 0; r < 4; r++) for (let c = 0; c < 3; c++) this.poly(this.qy(16.9, 20.86 + c * 0.2, 21.0 + c * 0.2, 20 + r * 8, 25 + r * 8), ["#FFD23F", "#6FD3FF", "#6FD29A", "#FF9A4D"][(r + c) % 4]);
      this.poly(this.qy(16.9, 21.55, 21.72, 30, 40), (this.tick >> 3) % 2 ? "#6FD29A" : "#2F7D4C");
    });
    push(19.6 + 20.6, () => this.beanbag(19.6, 20.6, "#19C6C6")); push(18.6 + 21.2, () => this.beanbag(18.6, 21.2, "#FF6BCB")); push(21.2 + 21.2, () => this.plant(21.2, 21.2, 1.2));
    // Studio Suara: bilik rekam berlapis busa, lampu ON AIR, mikrofon, rak alat
    push(23.9 + 17.9, () => {
      this.box(23.3, 16.3, 1.2, 1.6, 56, "#3B2A5E");
      for (let r = 0; r < 5; r++) for (let c = 0; c < 3; c++) this.poly(this.qy(17.9, 23.4 + c * 0.36, 23.7 + c * 0.36, 6 + r * 9, 13 + r * 9), (r + c) % 2 ? "#4B3878" : "#5A4590");
      this.poly(this.qx(24.5, 16.6, 17.5, 26, 46), "rgba(170,215,245,.35)");
      const on = (this.tick >> 4) % 2 === 0; this.poly(this.qy(17.9, 23.5, 24.3, 58, 64), on ? "#FF4D4D" : "#7A2E2E");
    });
    push(25.6 + 18.6, () => { this.box(25.55, 18.55, 0.1, 0.1, 30, "#2A3240"); this.box(25.4, 18.4, 0.4, 0.4, 2, "#2A3240"); this.box(25.47, 18.47, 0.26, 0.26, 9, "#1A1F2B", 30); this.poly(this.qy(18.73, 25.5, 25.7, 32, 37), "#C792EA"); });
    push(27.6 + 21.4, () => { this.box(26.9, 20.3, 1.4, 1.2, 30, "#2A2440"); for (let r = 0; r < 3; r++) { this.poly(this.qy(21.5, 27.0, 28.2, 5 + r * 9, 11 + r * 9), "#1B1430"); for (let l = 0; l < 5; l++) this.poly(this.qy(21.5, 27.1 + l * 0.2, 27.2 + l * 0.2, 7 + r * 9, 9 + r * 9), (this.tick + r * 2 + l) % 7 < 3 ? "#39D36B" : "#3A3560"); } });
    push(24.4 + 21.0, () => this.beanbag(24.4, 21.0, "#6B3FD4"));
    // Taman: pohon, bangku, kolam kecil, batu pijak
    push(30.2 + 17.3, () => { const g = this.g, [cx, cy] = P(31.0, 17.6); g.fillStyle = "#2E7BB8"; g.beginPath(); g.ellipse(cx, cy, 26, 11, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = "#6FC3F0"; g.beginPath(); g.ellipse(cx - 2, cy - 1, 21, 8, 0, 0, Math.PI * 2); g.fill();
      g.strokeStyle = "rgba(255,255,255,.55)"; g.beginPath(); g.ellipse(cx + Math.sin(this.waktu) * 4, cy, 6 + (this.waktu * 4) % 8, 2.5 + ((this.waktu * 4) % 8) / 3, 0, 0, Math.PI * 2); g.stroke(); });
    for (const [x, y] of [[32.2, 16.6], [32.6, 17.6], [32.3, 18.5], [32.8, 19.6]]) push(x + y - 0.5, () => { const g = this.g, [cx, cy] = P(x, y); g.fillStyle = "#C9D3E0"; g.beginPath(); g.ellipse(cx, cy, 6, 3, 0, 0, Math.PI * 2); g.fill(); });
    push(35.0 + 17.0, () => this.plant(35.0, 17.0, 1.9)); push(29.8 + 16.4, () => this.plant(29.8, 16.4, 1.2)); push(35.2 + 21.0, () => this.plant(35.2, 21.0, 1.4)); push(33.6 + 21.3, () => this.plant(33.6, 21.3, 0.9));
    push(30.6 + 21.0, () => { this.box(29.9, 20.4, 1.4, 0.5, 9, "#8A5E3F"); this.box(29.9, 20.85, 1.4, 0.1, 20, "#6E4A30"); this.box(30.0, 20.45, 0.1, 0.4, 9, "#3B2A20"); });
  }

  /** Awan bergerak pelan di balik jendela (siang & sore). */
  private awan(ph: Phase) {
    if (ph.night > 0.6) return;
    const g = this.g, warna = ph.name === "sore" ? "rgba(255,226,196,.75)" : "rgba(255,255,255,.8)";
    const jendela: Pt[][] = [...[[1.0, 3.6], [4.2, 6.8], [7.4, 9.6]].map(([y0, y1]) => this.qx(0, y0, y1, 38, 100)), ...[[16.8, 18.8], [19.2, 21.2]].map(([x0, x1]) => this.qy(0, x0, x1, 40, 98))];
    jendela.forEach((q, i) => {
      const [x0, y0, x1] = bboxOf(q), w = x1 - x0 + 40;
      g.save(); g.beginPath(); q.forEach(([x, y], k) => (k ? g.lineTo(x, y) : g.moveTo(x, y))); g.closePath(); g.clip();
      g.fillStyle = warna;
      for (let c = 0; c < 2; c++) {
        const cx = x0 - 20 + ((this.waktu * (2.2 + c) + i * 31 + c * 47) % w), cy = y0 + 8 + c * 9 + (i % 2) * 4;
        g.beginPath(); g.ellipse(Math.round(cx), cy, 9, 3, 0, 0, Math.PI * 2); g.ellipse(Math.round(cx) + 6, cy - 2, 6, 3, 0, 0, Math.PI * 2); g.fill();
      }
      g.restore();
    });
  }

  /** Jalur produksi menyala di lantai: meja ke meja sesuai urutan kerja. Hijau = selesai, garis berjalan = sedang dikerjakan. */
  private jalurProduksi() {
    const st = this.state, g = this.g;
    const gambar = (alur: [string, string][], aktif: string, warna: string) => {
      const kini = alur.findIndex(([k]) => k === aktif);
      if (kini < 0) return;
      const titik = alur.map(([, id]) => { const d = SEMUA.find((x) => x.id === id)!; const [sx, sy] = seatOf(d); return P(sx, sy + 0.25); });
      g.save(); g.lineWidth = 2; g.lineCap = "round";
      for (let i = 1; i < titik.length; i++) {
        const [a, b] = [titik[i - 1], titik[i]];
        g.setLineDash(i <= kini ? (i === kini ? [5, 4] : []) : [1, 5]);
        g.lineDashOffset = i === kini ? -this.waktu * 14 : 0;
        g.strokeStyle = i < kini ? "rgba(111,210,154,.55)" : i === kini ? warna : "rgba(255,255,255,.16)";
        g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(b[0], b[1]); g.stroke();
      }
      g.setLineDash([]);
      titik.forEach(([x, y], i) => {
        const r = i === kini ? 5 + Math.sin(this.waktu * 4) * 1.5 : 2.5;
        g.fillStyle = i < kini ? "rgba(111,210,154,.8)" : i === kini ? warna : "rgba(255,255,255,.22)";
        g.beginPath(); g.ellipse(x, y, r, r / 2, 0, 0, Math.PI * 2); g.fill();
        if (i === kini) { g.strokeStyle = warna; g.lineWidth = 1; g.globalAlpha = 0.5; g.beginPath(); g.ellipse(x, y, r + 5, (r + 5) / 2, 0, 0, Math.PI * 2); g.stroke(); g.globalAlpha = 1; }
      });
      g.restore();
    };
    if (st?.produksi?.[0]?.status === "berjalan") gambar(ALUR_SHORTS, activeStage(st), "rgba(111,211,255,.95)");
    if (st?.panjang?.tahap) gambar(ALUR_PANJANG, st.panjang.tahap, "rgba(255,79,163,.95)");
  }

  /** Robot penyedot debu kecil yang berkeliling (lampu berkedip, sedikit jejak bersih). */
  private robotDebu() {
    const rb = this.robot, [x, y] = P(rb.x, rb.y), g = this.g;
    g.fillStyle = "rgba(0,0,0,.25)"; g.beginPath(); g.ellipse(x, y + 1, 7, 3.2, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#1E2633"; g.beginPath(); g.ellipse(x, y - 1, 6.5, 3.2, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#3B4A62"; g.beginPath(); g.ellipse(x, y - 2.5, 6, 2.8, 0, 0, Math.PI * 2); g.fill();
    g.fillStyle = "#566A8A"; g.beginPath(); g.ellipse(x, y - 3, 3.2, 1.4, 0, 0, Math.PI * 2); g.fill();
    this.px(x + rb.arah * 3 - 1, y - 3, 2, 1, (this.tick >> 2) % 2 ? "#6FD3FF" : "#2D8CFF");
  }

  /** Debu di sinar matahari (siang/sore) & uap mesin kopi. */
  private partikel(ph: Phase) {
    const g = this.g;
    if (ph.night < 0.6) {
      for (const p of this.debu) {
        if (p.y > 9.6 || (p.y > 3.6 && p.y < 4.2) || (p.y > 6.8 && p.y < 7.4)) continue;
        const [x, y] = P(p.x, p.y + p.x * 0.47, p.z), a = 0.25 + 0.35 * Math.abs(Math.sin(this.waktu * 0.9 + p.f));
        g.fillStyle = ph.name === "sore" ? `rgba(255,214,160,${a})` : `rgba(255,252,236,${a})`; g.fillRect(x, y, 1, 1);
      }
    }
    for (const u of this.uap) {
      const k = u.t / 4.5, [x, y] = P(10.9, 14.1, 52 + k * 14);
      g.fillStyle = `rgba(255,255,255,${0.32 * (1 - k)})`; g.fillRect(x + Math.round(Math.sin(u.t * 2.4) * 1.5), y, 1 + (k > 0.5 ? 1 : 0), 1);
    }
  }

  render(): void {
    const ph = dayPhase(), g = this.g, st = this.state;
    g.clearRect(0, 0, BW, BH);
    if (this.latarKunci !== ph.name) {            // dinding, lantai & jendela: digambar ulang hanya saat fase hari berganti
      const lg = this.latar.getContext("2d")!; lg.imageSmoothingEnabled = false; lg.clearRect(0, 0, BW, BH);
      this.g = lg; this.room(ph); this.room2(ph); this.g = g; this.latarKunci = ph.name;
    }
    g.drawImage(this.latar, 0, 0);
    this.awan(ph);
    this.jalurProduksi();
    const hits: Hit[] = [this.whiteboard(), this.tv(), this.layarJadwal(ph)];
    this.layarRapat();
    this.neon(ph); this.door(); this.trophyCabinet();

    type Obj = { key: number; draw: () => BBox | void; id?: string; label?: string; person?: boolean };
    const objs: Obj[] = [];
    const tk = this.tick;

    for (const def of SEMUA) {
      const [x, y] = def.desk, on = this.jobFor(def)?.kind === "busy";
      objs.push({ key: x + 1 + y + 0.5, id: `agent:${def.id}`, label: `Meja ${def.name}`, draw: () => this.desk(x, y, {
        screens: 2, screen: (i) => (on ? (i ? "#1B4F78" : "#2A7DB8") : "#1C2B40"),
        art: (i, x0, x1) => {
          const yy = y + 0.32, w = x1 - x0;
          if (!on) { if (i === 0) this.poly(this.qy(yy, x0 + w * 0.4, x0 + w * 0.6, 37, 40), shade(def.color, 0.6)); return; }
          if (def.id === "dara") { for (let b = 0; b < 9; b++) { const h = 1 + Math.abs(Math.round(Math.sin((b + tk * 0.9 + i * 4) * 1.3) * 5)); this.poly(this.qy(yy, x0 + b * w / 9 + 0.01, x0 + (b + 0.6) * w / 9, 38 - h / 2, 38 + h / 2), b % 3 ? "#E6D2FF" : "#C792EA"); } return; }
          if (def.id === "rara") { for (let r = 0; r < 2; r++) for (let c = 0; c < 3; c++) { const a0 = x0 + c * w / 3 + 0.02, a1 = a0 + w / 3 - 0.04, bad = (c + r * 3 + tk) % 5 === 0; this.poly(this.qy(yy, a0, a1, 34 + r * 6, 39 + r * 6), bad ? "#F07178" : "#BFE3FF"); } return; }
          if (def.id === "uli") { const pct = (tk % 24) / 24; this.poly(this.qy(yy, x0 + 0.04, x1 - 0.04, 37, 40), "#2A3B5C"); this.poly(this.qy(yy, x0 + 0.04, x0 + 0.04 + (w - 0.08) * pct, 37, 40), "#FF4D4D"); this.poly(this.qy(yy, x0 + w * 0.4, x0 + w * 0.6, 42, 46), "#FFFFFF"); return; }
          if (def.id === "kai") { const cols = ["#F2C94C", "#47B5FF", "#C792EA", "#6FD29A"]; for (let r = 0; r < 3; r++) { let p = x0 + 0.02; for (let c = 0; c < 4 && p < x1 - 0.05; c++) { const len = (((c * 5 + r * 3 + tk + i) % 4) + 1) * w / 12; this.poly(this.qy(yy, p, Math.min(p + len, x1 - 0.02), 35 + r * 3, 37 + r * 3), cols[(c + r) % 4]); p += len + 0.03; } } const ph = x0 + ((tk % 20) / 20) * w; this.poly(this.qy(yy, ph, ph + 0.02, 33, 45), "#FFFFFF"); return; }
          if (def.id === "bima") { for (let c = 0; c < 3; c++) { const a = x0 + c * w / 3 + 0.02, b = x0 + (c + 1) * w / 3 - 0.02, lit = (c + tk + i) % 3 === 0; this.poly(this.qy(yy, a, b, 35, 41), lit ? "#4FD1C5" : "#BFEFEA"); this.poly(this.qy(yy, a + 0.03, a + (b - a) * 0.5, 36, 37), "#1E5E59"); } return; }
          if (def.id === "mila") { const m = x0 + w * .3, n = x0 + w * .7, k = (tk + i * 5) % 16 < 8; this.poly(this.qy(yy, m, n, 33, 46), "#0B1F3F"); this.poly(this.qy(yy, m + .05, n - .05, 39, 44), k ? "#FF6BCB" : "#6FD3FF"); this.poly(this.qy(yy, m + .03, n - .03, 36, 37.6), "#FFFFFF"); this.poly(this.qy(yy, m + .06, n - .06, 34.2, 35.6), "#2D8CFF"); return; }
          if (def.ruang) { const cols = ["#FFD23F", "#F2385A", "#19C6C6", "#FF7A2F"]; for (let c = 0; c < 3; c++) { const a = x0 + c * w / 3 + 0.02, b = x0 + (c + 1) * w / 3 - 0.02; this.poly(this.qy(yy, a, b, 34, 44), cols[(c + tk + i) % 4]); this.poly(this.qy(yy, a + 0.04, b - 0.04, 38, 40), "#14101F"); } return; }
          if (def.id === "steve") for (let b = 0; b < 5; b++) { const h = 3 + ((b * 5 + tk + i * 3) % 8); this.poly(this.qy(yy, x0 + b * w / 5 + 0.02, x0 + (b + 0.7) * w / 5, 34, 34 + h), b === 2 ? "#FF9A4D" : "#BFE3FF"); }
          else for (let l = 0; l < 4; l++) { const len = (((l * 3 + tk + i * 2) % 6) + 2) / 8 * w; this.poly(this.qy(yy, x0 + 0.02, x0 + Math.min(len, w), 42 - l * 3, 43 - l * 3), def.id === "nova" && l === 0 ? "#6FD29A" : "#DCEBFA"); }
        },
        glow: on ? def.color : undefined,
        extra: () => {
          this.mug(x + 1.62, y + 0.55, 25, def.color); this.box(x + 0.15, y + 0.55, 0.32, 0.24, 1, "#F4F1E8", 25);
          if (def.id === "dara") { this.box(x + 1.72, y + 0.2, 0.06, 0.06, 14, "#2A3240", 25); this.box(x + 1.66, y + 0.14, 0.18, 0.14, 7, "#1A1F2B", 39); this.poly(this.qy(y + 0.14, x + 1.68, x + 1.82, 41, 44), "#C792EA"); }
          else { this.box(x + 0.08, y + 0.12, 0.08, 0.08, 1, "#2A3240", 25); this.box(x + 0.1, y + 0.14, 0.04, 0.04, 12, "#3B4556", 26); this.box(x + 0.04, y + 0.1, 0.2, 0.12, 3, on ? "#FFE7A8" : "#C9D3E0", 37); }
          this.barangMeja(def.id, x, y);
        },
      }) });
      const [sx, sy] = seatOf(def);
      objs.push({ key: sx + sy - 0.05, draw: () => this.chairBase(sx, sy) });
      objs.push({ key: sx + sy + 0.06, draw: () => this.chairBack(sx, sy, shade(def.color, 0.55)) });
    }
    for (const f of FUTURE) {
      const [x, y] = f.desk;
      objs.push({ key: x + 1 + y + 0.5, id: `future:${f.key}`, label: `Meja kosong: ${f.name}`, draw: () => this.desk(x, y, {
        top: "#CDB596", screens: 1, screen: () => "#121A26",
        extra: () => { this.box(x + 1.25, y + 0.45, 0.55, 0.42, 10, "#C9A06B", 25); this.poly(this.qy(y + 0.87, x + 1.3, x + 1.75, 31, 33), "#9B7646"); },
      }) });
    }
    // ruang founder
    const [fx, fy] = FOUNDER.desk, [zx, zy] = FOUNDER.seat;
    objs.push({ key: fx + 1.3 + fy + 0.6, id: "founder", label: "Meja founder (kamu)", draw: () => this.desk(fx, fy, {
      w: 2.6, d: 1.2, top: "#8A5E3F", legs: "#2A2F3A", screens: 2, screen: () => "#2B3546",
      art: (_i, x0, x1) => { const yy = fy + 0.32; this.poly(this.qy(yy, (x0 + x1) / 2 - 0.08, (x0 + x1) / 2 + 0.08, 37, 40), "#2D8CFF"); },
      extra: () => { const [bx, by] = P(fx + 0.3, fy + 0.85, 25); this.px(bx - 3, by - 7, 6, 6, "#F2C94C"); this.px(bx - 2, by - 8, 4, 1, "#F2C94C"); this.px(bx, by - 1, 1, 1, "#8A6A1E"); this.mug(fx + 2.2, fy + 0.7, 25, "#ECF2F8"); },
    }) });
    objs.push({ key: zx + zy - 0.08, draw: () => { this.box(zx - 0.3, zy - 0.4, 0.6, 0.12, 34, "#7A2E2E", 10); this.chairBase(zx, zy); } });
    for (let k = 0; k < 4; k++) objs.push({ key: 16 + k + 0.5 + 0.01, draw: () => this.glassX(k, k + 1) });
    objs.push({ key: 16 + 5.5 + 0.01, draw: () => this.glassX(5, 6) });
    for (let k = 16; k < 22; k++) objs.push({ key: k + 0.5 + 6 + 0.01, draw: () => this.glassY(k, k + 1) });
    objs.push({ key: 16.8 + 0.8, draw: () => this.plant(16.8, 0.8, 1.2) }, { key: 21.5 + 2.6, draw: () => this.plant(21.5, 2.6, 0.9) });
    // dekor & fasilitas
    objs.push({ key: 10.7, id: "bible", label: "Rak channel bible", draw: () => this.shelf() });
    objs.push({ key: 14.3, id: "server", label: "Server agent", draw: () => this.server() });
    objs.push({ key: 13.2, draw: () => this.sofa() }, { key: 15.9, draw: () => this.coffeeTable() });
    objs.push({ key: 5.2 + 12.0, draw: () => this.beanbag(5.2, 12.0, "#2D8CFF") }, { key: 5.6 + 13.4, draw: () => this.beanbag(5.6, 13.4, "#47B5FF") });
    objs.push({ key: 11.2 + 10.5, draw: () => this.roundTable() });
    objs.push({ key: 26.0, draw: () => this.pantry() }, { key: 28.8, draw: () => this.cooler() });
    // Ruang Animasi
    objs.push({ key: 22.3 + 0.01, draw: () => this.partisi() });
    objs.push({ key: 35.8 + 1.05, id: "animasi", label: "Ruang Animasi: video panjang", draw: () => this.arcade() });
    objs.push({ key: 24.2 + 14.2, draw: () => this.crt() }, { key: 27.1 + 11.5, draw: () => this.mejaCahaya() }, { key: 34.2 + 13.9, draw: () => this.sofaRetro() });
    objs.push({ key: 35.4 + 9.6, draw: () => this.plant(35.4, 9.6, 1.1) }, { key: 22.9 + 0.7, draw: () => this.plant(22.9, 0.7, 1.0) });
    objs.push({ key: 1.2, draw: () => this.plant(0.6, 0.6, 1.3) }, { key: 15.4 + 6.7, draw: () => this.plant(15.4, 6.7, 1.1) }, { key: 7.4 + 10.8, draw: () => this.plant(7.4, 10.8) }, { key: 0.6 + 7.0, draw: () => this.plant(0.6, 7.0, 0.9) });

    for (const a of this.actors) {
      objs.push({ key: a.x + a.y + (a.pose === "sit" ? 0.02 : 0.3), id: `agent:${a.def.id}`, label: a.def.name, person: true, draw: () => {
        const fr = a.pose === "walk" ? Math.floor(a.langkah) : Math.floor(a.frame / 3);
        const b = this.person(a.def.look, a.def.id, a.x, a.y, a.pose, a.pose === "sit" || a.pose === "sleep" ? "back" : a.facing, fr, 0, a.emo);
        a.screen = [ (b[0] + b[2]) / 2, b[1] ]; return b; } });
    }
    { const rb = this.robot; objs.push({ key: rb.x + rb.y - 0.2, draw: () => this.robotDebu() }); }
    this.ruangDepan(objs);
    objs.push({ key: 99, draw: () => this.partikel(ph) });
    let zonaTop: Pt = [0, 0];
    objs.push({ key: zx + zy + 0.02, id: "founder", label: "Zona (kamu)", person: true, draw: () => { const b = this.person(FOUNDER.look, "zona", zx, zy, "stand", "front", Math.floor(tk / 6), 12); zonaTop = [(b[0] + b[2]) / 2, b[1]]; return b; } });

    objs.sort((a, b) => a.key - b.key).forEach((o) => { const bb = o.draw(); if (o.id && bb) hits.push({ id: o.id, label: o.label!, bbox: bb, person: !!o.person }); });

    // cahaya malam & warna suasana: hanya di dalam ruangan (bagian kosong di sekitar kantor tetap transparan,
    // supaya tidak muncul "kotak" di latar)
    const topeng = this.topeng ??= document.createElement("canvas");
    topeng.width = BW; topeng.height = BH;
    const tg = topeng.getContext("2d")!;
    tg.clearRect(0, 0, BW, BH); tg.drawImage(this.buf, 0, 0);
    if (ph.night) {
      const glow = (x: number, y: number, r: number, c: string) => { const [lx, ly] = P(x, y); const gr = g.createRadialGradient(lx, ly, 2, lx, ly, r); gr.addColorStop(0, c); gr.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = gr; g.fillRect(lx - r, ly - r, r * 2, r * 2); };
      if (ph.tint) { g.fillStyle = ph.tint; g.fillRect(0, 0, BW, BH); }
      g.globalCompositeOperation = "lighter";
      for (const d of SEMUA) glow(d.desk[0] + 1, d.desk[1] + 0.9, 40, d.ruang ? "rgba(255,120,200,.15)" : "rgba(255,214,150,.15)");
      glow(28.5, 1.5, 70, "rgba(255,80,170,.14)");
      glow(11.5, 1.5, 70, "rgba(80,170,255,.14)");
      glow(fx + 1.3, fy + 1.0, 50, "rgba(255,190,120,.16)"); glow(4, 12.6, 60, "rgba(200,140,255,.10)"); glow(11.2, 13.6, 50, "rgba(255,220,160,.12)");
      g.globalCompositeOperation = "source-over";
    } else if (ph.tint) { g.fillStyle = ph.tint; g.fillRect(0, 0, BW, BH); }
    g.globalCompositeOperation = "destination-in"; g.drawImage(topeng, 0, 0); g.globalCompositeOperation = "source-over";

    const h = hits.find((z) => z.id === this.hoverId);
    if (h) { const [x0, y0, x1, y1] = h.bbox; g.strokeStyle = "#FFE3A6"; g.setLineDash([3, 2]); g.strokeRect(x0 - 2.5, y0 - 2.5, x1 - x0 + 5, y1 - y0 + 5); g.setLineDash([]); }
    this.hits = hits;

    // overlay
    const ov: OverlayItem[] = [];
    for (const a of this.actors) {
      if (!a.screen) continue;
      const s = this.jobFor(a.def);
      ov.push({ kind: "tag", x: a.screen[0], y: a.screen[1] - 2, text: a.def.name, tone: a.def.color });
      if (s && !(a.mode === "report" && s.kind === "ok" && a.path.length) && a.mode !== "antar") {
        const lapor = a.mode === "report" && !a.path.length, sorak = a.mode === "sorak";
        ov.push({ kind: "bubble", x: a.screen[0], y: a.screen[1] - (a.emo ? 24 : 15), text: lapor ? "Bos, sudah selesai!" : sorak ? "Yes, beres!" : s.text, tone: s.kind,
          sub: s.kind === "busy" ? mmss(s.sejak) : undefined, pips: s.kind === "busy" ? s.pips : undefined });
      } else if (a.mode === "antar" && !a.path.length) ov.push({ kind: "bubble", x: a.screen[0], y: a.screen[1] - 24, text: "Ini, lanjutkan ya", tone: "ok" });
    }
    // papan kecil: tayang berikutnya (di atas layar jadwal) & hitungan minggu ini (di atas papan antrean)
    const brk = st?.jadwal?.berikut;
    if (brk?.waktu) {
      const sisa = Math.max(0, Date.parse(brk.waktu) - Date.now()) / 60000, [jx, jy] = P(0, 13.3, 106);
      ov.push({ kind: "sign", x: jx, y: jy, text: `Tayang ${brk.jam}`, sub: sisa >= 60 ? `${Math.floor(sisa / 60)}j ${Math.floor(sisa % 60)}m lagi` : `${Math.ceil(sisa)} menit lagi`, tone: "#47B5FF" });
    }
    for (const r of NAMA_RUANG) { const [rx, ry] = P(r.di[0], r.di[1], 74); ov.push({ kind: "sign", x: rx, y: ry, text: r.nama, tone: r.warna }); }
    if (this.rapat.peserta.length >= 3 && this.rapat.peserta.every((b) => !b.path.length)) { const [rx, ry] = P(5, 18.7, 60); ov.push({ kind: "bubble", x: rx, y: ry, text: "Rapat tim", tone: "ok" }); }
    if (st?.week) { const [wx, wy] = P(3.2, 0, 104); ov.push({ kind: "sign", x: wx, y: wy, text: `Minggu ini ${st.week.published + st.week.terjadwal}/${st.week.target}`, tone: "#6FD29A" }); }
    ov.push({ kind: "tag", x: zonaTop[0], y: zonaTop[1] - 2, text: "Zona · founder", tone: "founder" });
    const n = (st?.videos ?? []).filter((v) => v.status === "ide" || v.status === "naskah").length;
    if (n) { const [bx, by] = P(fx + 0.3, fy + 0.85, 36); ov.push({ kind: "badge", x: bx, y: by - 6, text: String(n) }); }
    this.overlay = ov;
  }

  /** Titik tengah objek (koordinat buffer) untuk transisi zoom kamera ke agent/meja yang dibuka. */
  anchor(id: string): Pt | null {
    const hs = this.hits.filter((h) => h.id === id);
    const h = hs.find((x) => x.person) ?? hs[0];
    if (!h) return null;
    const desk = hs.find((x) => !x.person);
    const b = desk && h.person ? [Math.min(h.bbox[0], desk.bbox[0]), Math.min(h.bbox[1], desk.bbox[1]), Math.max(h.bbox[2], desk.bbox[2]), Math.max(h.bbox[3], desk.bbox[3])] : h.bbox;
    return [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];
  }

  hitAt(x: number, y: number): Hit | undefined {
    const inside = (z: Hit) => x >= z.bbox[0] - 2 && x <= z.bbox[2] + 2 && y >= z.bbox[1] - 2 && y <= z.bbox[3] + 2;
    return [...this.hits].reverse().find((z) => z.person && inside(z)) ?? [...this.hits].reverse().find(inside);
  }
}

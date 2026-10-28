import type { StudioState } from "@/lib/types";
import { shade, sprite, type Look, type Pose } from "./sprites";
import { BH, BLOCKED, BW, FOUNDER, FUTURE, OX, OY, RD, RW, SPOTS, T, TEAM, WALL, type AgentDef } from "./world";

type Pt = [number, number];
type BBox = [number, number, number, number];
export interface Hit { id: string; label: string; bbox: BBox; person: boolean }
export interface OverlayItem { kind: "tag" | "bubble" | "badge"; x: number; y: number; text: string; tone?: string }

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
const G = 2, GW = RW * G, GH = RD * G;
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
interface Actor {
  def: AgentDef; x: number; y: number; path: Pt[]; wait: number; frame: number;
  pose: Pose; facing: "front" | "back"; mode: "idle" | "work" | "report"; sitIdle: boolean; screen?: Pt; reportedAt?: string | null;
}
const seatOf = (d: AgentDef): Pt => [d.desk[0] + 1, d.desk[1] + 1.55];

export class OfficeEngine {
  private buf = document.createElement("canvas");
  private g: CanvasRenderingContext2D;
  private tick = 0;
  private actors: Actor[];
  state: StudioState | null = null;
  hits: Hit[] = [];
  hoverId: string | null = null;
  overlay: OverlayItem[] = [];
  reduced = false;

  constructor() {
    this.buf.width = BW; this.buf.height = BH;
    this.g = this.buf.getContext("2d")!;
    this.g.imageSmoothingEnabled = false;
    this.actors = TEAM.map((def, i) => {
      const [x, y] = seatOf(def);
      return { def, x, y, path: [], wait: 30 + i * 25, frame: i * 7, pose: "sit", facing: "back", mode: "idle", sitIdle: true, reportedAt: undefined };
    });
  }
  get canvas() { return this.buf; }

  jobFor(def: AgentDef): { kind: "busy" | "ok" | "err" | "stopped"; text: string } | null {
    const j = this.state?.job;
    if (!j?.job || !def.busy[j.job]) return null;
    if (j.status === "running") return { kind: "busy", text: def.busy[j.job]! };
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

  step() {
    this.tick++;
    for (const a of this.actors) {
      a.frame++;
      const st = this.jobFor(a.def), seat = seatOf(a.def);
      if (st?.kind === "busy" && a.mode !== "work") { a.mode = "work"; a.sitIdle = true; this.go(a, seat); }
      if (st?.kind === "ok" && a.mode === "work" && a.reportedAt !== this.state?.job.finished) {
        a.mode = "report"; a.reportedAt = this.state?.job.finished; this.go(a, SPOTS.lapor); a.wait = 50;
      }
      if (!st || (st.kind !== "busy" && a.mode === "work")) { if (a.mode === "work") { a.mode = "idle"; a.wait = 40; } }
      if (a.path.length) {
        const [tx, ty] = a.path[0], dx = tx - a.x, dy = ty - a.y, dist = Math.hypot(dx, dy), sp = 0.085;
        if (dist <= sp) { a.x = tx; a.y = ty; a.path.shift(); } else { a.x += (dx / dist) * sp; a.y += (dy / dist) * sp; }
        a.pose = "walk"; a.facing = dy < -0.01 || (Math.abs(dy) < 0.01 && dx < 0) ? "back" : "front";
        continue;
      }
      const atSeat = Math.hypot(a.x - seat[0], a.y - seat[1]) < 0.06;
      a.pose = atSeat && a.sitIdle ? "sit" : "stand";
      if (a.mode === "report") { a.facing = "back"; if (--a.wait <= 0) { a.mode = "idle"; a.sitIdle = true; this.go(a, seat); } continue; }
      if (!atSeat) a.facing = "front";
      if (a.mode === "work") continue;
      if (--a.wait > 0) continue;
      const names = Object.keys(SPOTS).filter((k) => k !== "lapor");
      if (Math.random() < 0.45) { a.sitIdle = true; this.go(a, seat); }
      else { a.sitIdle = false; const s = SPOTS[names[Math.floor(Math.random() * names.length)]]; this.go(a, [s[0] + (Math.random() - 0.5) * 0.4, s[1] + (Math.random() - 0.5) * 0.3]); }
      a.wait = 80 + Math.floor(Math.random() * 140);
    }
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
    // dinding
    this.poly([P(0, 0), P(0, RD), P(0, RD, WALL), P(0, 0, WALL)], "#DCE5EF");
    this.poly([P(0, 0), P(RW, 0), P(RW, 0, WALL), P(0, 0, WALL)], "#C9D5E3");
    this.poly([P(0, 0), P(0, RD), P(0, RD, 36), P(0, 0, 36)], "#C5D3E2");
    this.poly([P(0, 0), P(16, 0), P(16, 0, 36), P(0, 0, 36)], "#B6C5D7");
    this.poly([P(16, 0), P(RW, 0), P(RW, 0, WALL), P(16, 0, WALL)], "#2E3C55"); // dinding ruang founder (aksen gelap)
    this.poly([P(0, 0, WALL), P(0, RD, WALL), P(-0.35, RD, WALL), P(-0.35, -0.35, WALL), P(RW, -0.35, WALL), P(RW, 0, WALL)], "#8EA0B6");
    // jendela kiri
    [[1.0, 3.6], [4.2, 6.8], [7.4, 9.6]].forEach(([y0, y1], i) => {
      const q = this.qx(0, y0, y1, 34, 96); this.sky(q, ph, i + 1);
      this.poly(this.qx(0, y0 - 0.06, y1 + 0.06, 30, 34), "#9AAABD");
      this.poly(q, undefined, "#6F8299");
      const m = (y0 + y1) / 2, g = this.g; g.strokeStyle = "#6F8299"; g.beginPath(); g.moveTo(...P(0, m, 34)); g.lineTo(...P(0, m, 96)); g.moveTo(...P(0, y0, 66)); g.lineTo(...P(0, y1, 66)); g.stroke();
    });
    // jendela ruang founder
    [[16.8, 18.8], [19.2, 21.2]].forEach(([x0, x1], i) => {
      const q = this.qy(0, x0, x1, 40, 98); this.sky(q, ph, i + 7);
      this.poly(q, undefined, "#11192A");
      this.poly(this.qy(0, x0 - 0.06, x1 + 0.06, 36, 40), "#1B2638");
    });
    // plint
    this.poly([P(0, 0), P(0, RD), P(0, RD, 4), P(0, 0, 4)], "#8C9CB0");
    this.poly([P(0, 0), P(RW, 0), P(RW, 0, 4), P(0, 0, 4)], "#7D8DA2");
    // lantai: kayu (kerja), karpet (founder), lantai keramik (pantry)
    for (let i = 0; i < RW; i++) for (let j = 0; j < RD; j++) {
      let c: string;
      if (i >= 16 && j < 6) c = (i + j) % 2 ? "#3A4C6B" : "#36486A";
      else if (j >= 13 && i >= 8 && i < 16) c = (i + j) % 2 ? "#E7EBF0" : "#D3DAE3";
      else { const plank = (i + (j >> 1)) % 2; c = plank ? "#C9965F" : "#C08C57"; if ((i * 7 + j * 3) % 6 === 0) c = "#BA854F"; }
      this.poly([P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1)], c);
    }
    const g = this.g; g.globalAlpha = 0.16; g.strokeStyle = "#6E4A2B";
    for (let i = 0; i <= 16; i++) { g.beginPath(); g.moveTo(...P(i, i >= 16 ? 6 : 0)); g.lineTo(...P(i, 13)); g.stroke(); }
    g.globalAlpha = 1;
    // karpet lounge
    this.poly([P(1.6, 10.8), P(7.0, 10.8), P(7.0, 14.6), P(1.6, 14.6)], "#7A4E8C");
    this.poly([P(1.9, 11.1), P(6.7, 11.1), P(6.7, 14.3), P(1.9, 14.3)], undefined, "#E4B5F0");
    this.poly([P(2.3, 11.5), P(6.3, 11.5), P(6.3, 13.9), P(2.3, 13.9)], undefined, "#A673B8");
    // karpet founder
    this.poly([P(17.0, 1.0), P(21.4, 1.0), P(21.4, 5.4), P(17.0, 5.4)], "#22324C");
    this.poly([P(17.3, 1.3), P(21.1, 1.3), P(21.1, 5.1), P(17.3, 5.1)], undefined, "#FF9A4D");
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
    g.shadowColor = "#FF9A4D"; g.shadowBlur = ph.night ? 8 : 3;
    let x = 10.15;
    for (const ch of "YOFAMO") {
      glyph[ch].forEach((row, r) => [...row].forEach((b, c) => { if (b === "1") this.poly(this.qy(0, x + c * 0.13, x + c * 0.13 + 0.1, 90 - r * 3.4, 92.6 - r * 3.4), "#FFB070"); }));
      x += 0.5;
    }
    g.restore();
    // poster
    this.poly(this.qy(0, 10.4, 11.5, 40, 70), "#20304A"); this.poly(this.qy(0, 10.55, 11.35, 44, 66), "#FF5C5C");
    this.poly([P(10.85, 0, 50), P(10.85, 0, 60), P(11.1, 0, 55)], "#FFFFFF");
    this.poly(this.qy(0, 11.9, 12.9, 40, 70), "#20304A"); this.poly(this.qy(0, 12.05, 12.75, 44, 66), "#47B5FF");
    this.poly(this.qy(0, 12.2, 12.6, 56, 62), "#F2C94C"); this.poly(this.qy(0, 12.3, 12.5, 48, 54), "#F4F1E8");
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
  private desk(x: number, y: number, o: { w?: number; d?: number; top?: string; legs?: string; screens: number; screen: (i: number) => string; art?: (i: number, x0: number, x1: number) => void; extra?: () => void }) {
    const w = o.w ?? 2, d = o.d ?? 1, legs = o.legs ?? "#E5EAF0";
    for (const [a, b] of [[0.06, 0.06], [w - 0.16, 0.06], [0.06, d - 0.16], [w - 0.16, d - 0.16]]) this.box(x + a, y + b, 0.1, 0.1, 22, legs);
    this.box(x + 0.1, y + 0.08, w - 0.2, 0.06, 8, shade(legs, 0.9), 14);
    const top = this.box(x, y, w, d, 3, o.top ?? "#B98A5C", 22);
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
  private chairBack(x: number, y: number, c: string) { this.box(x - 0.24, y + 0.18, 0.48, 0.08, 9, c, 13); this.box(x - 0.03, y + 0.2, 0.06, 0.06, 4, "#3B4556", 9); }
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
    const busy = this.state?.job.status === "running";
    for (let r = 0; r < 9; r++) {
      const z = 8 + r * 8; this.poly(this.qy(0.9, 13.3, 14.25, z, z + 6), "#2A3444");
      for (let l = 0; l < 4; l++) { const on = (this.tick + r * 3 + l * 5) % (busy ? 4 : 11) < 2; this.poly(this.qy(0.9, 13.4 + l * 0.12, 13.47 + l * 0.12, z + 2, z + 4), on ? (l % 2 ? "#6FD29A" : "#FF9A4D") : "#3A4658"); }
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

  private person(look: Look, id: string, x: number, y: number, pose: Pose, facing: "front" | "back", frame: number, lift = 0): BBox {
    const [sx, sy] = P(x, y), g = this.g;
    g.fillStyle = "rgba(0,0,0,.2)"; g.beginPath(); g.ellipse(sx, sy, 6, 2.5, 0, 0, Math.PI * 2); g.fill();
    const img = sprite(look, id, pose, facing, frame);
    const top = (pose === "sit" ? sy - img.height - 13 : sy - img.height + (pose === "walk" && frame % 2 ? -1 : 0)) - lift;
    g.drawImage(img, sx - 6, top);
    return [sx - 7, top - 1, sx + 7, sy + 2];
  }

  render(): void {
    const ph = dayPhase(), g = this.g, st = this.state;
    const bg = g.createLinearGradient(0, 0, 0, BH); bg.addColorStop(0, "#0C1728"); bg.addColorStop(1, "#13243A"); g.fillStyle = bg; g.fillRect(0, 0, BW, BH);
    this.room(ph);
    const hits: Hit[] = [this.whiteboard(), this.tv()];
    this.neon(ph); this.door(); this.trophyCabinet();

    type Obj = { key: number; draw: () => BBox | void; id?: string; label?: string; person?: boolean };
    const objs: Obj[] = [];
    const tk = this.tick;

    for (const def of TEAM) {
      const [x, y] = def.desk, on = this.jobFor(def)?.kind === "busy";
      objs.push({ key: x + 1 + y + 0.5, id: `agent:${def.id}`, label: `Meja ${def.name}`, draw: () => this.desk(x, y, {
        screens: 2, screen: (i) => (on ? (i ? "#1B4F78" : "#2A7DB8") : "#1C2B40"),
        art: (i, x0, x1) => {
          const yy = y + 0.32, w = x1 - x0;
          if (!on) { if (i === 0) this.poly(this.qy(yy, x0 + w * 0.4, x0 + w * 0.6, 37, 40), shade(def.color, 0.6)); return; }
          if (def.id === "dara") { for (let b = 0; b < 9; b++) { const h = 1 + Math.abs(Math.round(Math.sin((b + tk * 0.9 + i * 4) * 1.3) * 5)); this.poly(this.qy(yy, x0 + b * w / 9 + 0.01, x0 + (b + 0.6) * w / 9, 38 - h / 2, 38 + h / 2), b % 3 ? "#E6D2FF" : "#C792EA"); } return; }
          if (def.id === "kai") { const cols = ["#F2C94C", "#47B5FF", "#C792EA", "#6FD29A"]; for (let r = 0; r < 3; r++) { let p = x0 + 0.02; for (let c = 0; c < 4 && p < x1 - 0.05; c++) { const len = (((c * 5 + r * 3 + tk + i) % 4) + 1) * w / 12; this.poly(this.qy(yy, p, Math.min(p + len, x1 - 0.02), 35 + r * 3, 37 + r * 3), cols[(c + r) % 4]); p += len + 0.03; } } const ph = x0 + ((tk % 20) / 20) * w; this.poly(this.qy(yy, ph, ph + 0.02, 33, 45), "#FFFFFF"); return; }
          if (def.id === "bima") { for (let c = 0; c < 3; c++) { const a = x0 + c * w / 3 + 0.02, b = x0 + (c + 1) * w / 3 - 0.02, lit = (c + tk + i) % 3 === 0; this.poly(this.qy(yy, a, b, 35, 41), lit ? "#4FD1C5" : "#BFEFEA"); this.poly(this.qy(yy, a + 0.03, a + (b - a) * 0.5, 36, 37), "#1E5E59"); } return; }
          if (def.id === "steve") for (let b = 0; b < 5; b++) { const h = 3 + ((b * 5 + tk + i * 3) % 8); this.poly(this.qy(yy, x0 + b * w / 5 + 0.02, x0 + (b + 0.7) * w / 5, 34, 34 + h), b === 2 ? "#FF9A4D" : "#BFE3FF"); }
          else for (let l = 0; l < 4; l++) { const len = (((l * 3 + tk + i * 2) % 6) + 2) / 8 * w; this.poly(this.qy(yy, x0 + 0.02, x0 + Math.min(len, w), 42 - l * 3, 43 - l * 3), def.id === "nova" && l === 0 ? "#6FD29A" : "#DCEBFA"); }
        },
        extra: () => { this.mug(x + 1.62, y + 0.55, 25, def.color); this.box(x + 0.15, y + 0.55, 0.32, 0.24, 1, "#F4F1E8", 25); },
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
      art: (_i, x0, x1) => { const yy = fy + 0.32; this.poly(this.qy(yy, (x0 + x1) / 2 - 0.08, (x0 + x1) / 2 + 0.08, 37, 40), "#FF9A4D"); },
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
    objs.push({ key: 5.2 + 12.0, draw: () => this.beanbag(5.2, 12.0, "#FF9A4D") }, { key: 5.6 + 13.4, draw: () => this.beanbag(5.6, 13.4, "#47B5FF") });
    objs.push({ key: 11.2 + 10.5, draw: () => this.roundTable() });
    objs.push({ key: 26.0, draw: () => this.pantry() }, { key: 28.8, draw: () => this.cooler() });
    objs.push({ key: 1.2, draw: () => this.plant(0.6, 0.6, 1.3) }, { key: 15.4 + 6.7, draw: () => this.plant(15.4, 6.7, 1.1) }, { key: 7.4 + 10.8, draw: () => this.plant(7.4, 10.8) }, { key: 0.6 + 7.0, draw: () => this.plant(0.6, 7.0, 0.9) });

    for (const a of this.actors) {
      objs.push({ key: a.x + a.y + (a.pose === "sit" ? 0.02 : 0.3), id: `agent:${a.def.id}`, label: a.def.name, person: true, draw: () => {
        const b = this.person(a.def.look, a.def.id, a.x, a.y, a.pose, a.pose === "sit" ? "back" : a.facing, Math.floor(a.frame / 3));
        a.screen = [ (b[0] + b[2]) / 2, b[1] ]; return b; } });
    }
    let zonaTop: Pt = [0, 0];
    objs.push({ key: zx + zy + 0.02, id: "founder", label: "Zona (kamu)", person: true, draw: () => { const b = this.person(FOUNDER.look, "zona", zx, zy, "stand", "front", Math.floor(tk / 6), 12); zonaTop = [(b[0] + b[2]) / 2, b[1]]; return b; } });

    objs.sort((a, b) => a.key - b.key).forEach((o) => { const bb = o.draw(); if (o.id && bb) hits.push({ id: o.id, label: o.label!, bbox: bb, person: !!o.person }); });

    // cahaya malam
    if (ph.night) {
      const glow = (x: number, y: number, r: number, c: string) => { const [lx, ly] = P(x, y); const gr = g.createRadialGradient(lx, ly, 2, lx, ly, r); gr.addColorStop(0, c); gr.addColorStop(1, "rgba(0,0,0,0)"); g.fillStyle = gr; g.fillRect(lx - r, ly - r, r * 2, r * 2); };
      if (ph.tint) { g.fillStyle = ph.tint; g.fillRect(0, 0, BW, BH); }
      g.globalCompositeOperation = "lighter";
      for (const d of TEAM) glow(d.desk[0] + 1, d.desk[1] + 0.9, 40, "rgba(255,210,140,.16)");
      glow(fx + 1.3, fy + 1.0, 50, "rgba(255,190,120,.16)"); glow(4, 12.6, 60, "rgba(200,140,255,.10)"); glow(11.2, 13.6, 50, "rgba(255,220,160,.12)");
      g.globalCompositeOperation = "source-over";
    } else if (ph.tint) { g.fillStyle = ph.tint; g.fillRect(0, 0, BW, BH); }

    const h = hits.find((z) => z.id === this.hoverId);
    if (h) { const [x0, y0, x1, y1] = h.bbox; g.strokeStyle = "#FFE3A6"; g.setLineDash([3, 2]); g.strokeRect(x0 - 2.5, y0 - 2.5, x1 - x0 + 5, y1 - y0 + 5); g.setLineDash([]); }
    this.hits = hits;

    // overlay
    const ov: OverlayItem[] = [];
    for (const a of this.actors) {
      if (!a.screen) continue;
      const s = this.jobFor(a.def);
      ov.push({ kind: "tag", x: a.screen[0], y: a.screen[1] - 2, text: a.def.name, tone: a.def.color });
      if (s && !(a.mode === "report" && s.kind === "ok" && a.path.length)) ov.push({ kind: "bubble", x: a.screen[0], y: a.screen[1] - 15, text: a.mode === "report" && !a.path.length ? "Bos, sudah selesai!" : s.text, tone: s.kind });
    }
    ov.push({ kind: "tag", x: zonaTop[0], y: zonaTop[1] - 2, text: "Zona · founder", tone: "founder" });
    const n = (st?.videos ?? []).filter((v) => v.status === "ide" || v.status === "naskah").length;
    if (n) { const [bx, by] = P(fx + 0.3, fy + 0.85, 36); ov.push({ kind: "badge", x: bx, y: by - 6, text: String(n) }); }
    this.overlay = ov;
  }

  hitAt(x: number, y: number): Hit | undefined {
    const inside = (z: Hit) => x >= z.bbox[0] - 2 && x <= z.bbox[2] + 2 && y >= z.bbox[1] - 2 && y <= z.bbox[3] + 2;
    return [...this.hits].reverse().find((z) => z.person && inside(z)) ?? [...this.hits].reverse().find(inside);
  }
}

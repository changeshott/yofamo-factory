/* Sprite karakter pixel-art, digambar dari peta karakter (12 × 19 px).
   Kunci warna: O garis, H rambut, h rambut gelap, S kulit, s kulit gelap, E mata, M mulut,
   T baju, t baju gelap, L baju terang, P celana, p celana gelap, B sepatu, C topi, G kacamata, A aksen,
   W putih (kertas/cangkir), K gelap (HP/headphone). */

export type HairStyle = "short" | "long" | "cap" | "bun" | "curly";
export interface Look {
  skin: string;
  hair: string;
  shirt: string;
  pants: string;
  accent: string;
  style: HairStyle;
  glasses?: boolean;
  headphone?: boolean;
}

const FRONT = [
  "....OOOO....",
  "...OHHHHO...",
  "..OHHHHHHO..",
  "..OHHSSSHO..",
  "..OHSSSSSO..",
  "..OSESSESO..",
  "..OSSSSSSO..",
  "...OSssSO...",
  "...OOSSOO...",
  "..OTTAATTO..",
  ".OTLTTTTTTO.",
  ".OTtTTTTtTO.",
  ".OTtTTTTtTO.",
  ".OSOTTTTOSO.",
  "..OPPPPPPO..",
  "..OPPOOPPO..",
  "..OpPOOPpO..",
  "..OBBOOBBO..",
  "..OOOOOOOO..",
];
const BACK = [
  "....OOOO....",
  "...OHHHHO...",
  "..OHHHHHHO..",
  "..OHHHHHHO..",
  "..OHHHHHHO..",
  "..OHHHHHHO..",
  "..OhHHHHhO..",
  "...OhhhhO...",
  "...OOSSOO...",
  "..OTTTTTTO..",
  ".OTTTTTTTTO.",
  ".OTtTTTTtTO.",
  ".OTtTTTTtTO.",
  ".OSOTTTTOSO.",
  "..OPPPPPPO..",
  "..OPPOOPPO..",
  "..OpPOOPpO..",
  "..OBBOOBBO..",
  "..OOOOOOOO..",
];
/* Jalan 4 frame: kaki bergantian + tangan berayun (baris 11–13 = lengan, 14–18 = kaki). */
const WALK_ARMS = [
  [".OTtTTTTtTO.", ".OStTTTTtTO.", ".OOOTTTTOSO."],   // tangan kiri ke depan (naik), kanan ke belakang
  [".OTtTTTTtTO.", ".OTtTTTTtTO.", ".OSOTTTTOSO."],
  [".OTtTTTTtTO.", ".OTtTTTTtSO.", ".OSOTTTTOOO."],   // sebaliknya
  [".OTtTTTTtTO.", ".OTtTTTTtTO.", ".OSOTTTTOSO."],
];
const WALK_LEGS = [
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OBBOOPpO..", "..OOOOOBBO..", "......OOO..."],
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OpPOOPpO..", "..OBBOOBBO..", "..OOOOOOOO.."],
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OpPOOBBO..", "..OBBOOOOO..", "...OOO......"],
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OpPOOPpO..", "..OBBOOBBO..", "..OOOOOOOO.."],
];
const SIT_BACK = [...BACK.slice(0, 13), ".OTOTTTTOTO.", "..OPPPPPPO..", "..OOOOOOOO.."];
const TYPE_ARMS = [".OTtTTTTtTO.", ".OtTTTTTTtO."];
/* Pose khusus (tampak depan): baris yang diganti dari FRONT. */
const CHEER: Record<number, string>[] = [
  { 6: ".SOSSSSSSOS.", 7: ".OOOSssSOOO.", 9: "..OTTAATTO..", 10: "..OTLTTTTO..", 11: "..OTtTTtTO..", 12: "..OTtTTtTO..", 13: "..OOTTTTOO.." },
  { 5: ".SOSESSESOS.", 6: ".OOSSSSSSOO.", 9: "..OTTAATTO..", 10: "..OTLTTTTO..", 11: "..OTtTTtTO..", 12: "..OTtTTtTO..", 13: "..OOTTTTOO.." },
];
const DRINK: Record<number, string>[] = [
  { 12: ".OTtTTTWWSO.", 13: ".OSOTTTOOOO." },                                     // cangkir di depan dada
  { 7: "...OSssWWO..", 8: "...OOSSOSO..", 12: ".OTtTTTTtOO.", 13: ".OSOTTTTOO.." }, // cangkir di mulut
];
const CARRY: Record<number, string> = { 11: ".OTtWWWWtTO.", 12: ".OTSWWWWSTO.", 13: ".OOOTTTTOOO." };
const PHONE: Record<number, string> = { 5: "..OSSSSSSO..", 6: "..OSEEESSO..".replace("EEE", "ESE"), 11: ".OTtTKKTtTO.", 12: ".OTtSKKStTO.", 13: ".OOOTTTTOOO." };
const TALK: Record<number, string> = { 7: "...OSMMSO..." };
const SHOCK: Record<number, string> = { 5: "..OSEsSESO..".replace("s", "S"), 7: "...OSMMSO...", 12: ".OStTTTTtSO.", 13: ".OOOTTTTOOO." };

function shade(hex: string, f: number): string {
  const n = parseInt(hex.slice(1), 16);
  const ch = (v: number) => Math.max(0, Math.min(255, Math.round(v * f)));
  return "#" + ((1 << 24) + (ch(n >> 16) << 16) + (ch((n >> 8) & 255) << 8) + ch(n & 255)).toString(16).slice(1);
}
export { shade };

function withStyle(rows: string[], look: Look, view: "front" | "back"): string[] {
  const r = rows.map((x) => x.split(""));
  const set = (y: number, x: number, c: string) => { if (r[y] && x >= 0 && x < 12) r[y][x] = c; };
  if (look.style === "long") {
    for (let y = 3; y <= 11; y++) { if (r[y]?.[1] === "S" || r[y]?.[10] === "S") continue; set(y, 1, "O"); set(y, 2, "H"); set(y, 9, "H"); set(y, 10, "O"); }
    if (view === "back") for (let y = 7; y <= 10; y++) for (let x = 3; x <= 8; x++) set(y, x, y === 10 ? "h" : "H");
  }
  if (look.style === "bun") { set(0, 4, "H"); set(0, 5, "H"); set(0, 6, "H"); set(0, 7, "H"); r.unshift("....OHHO....".split("")); r.pop(); }
  if (look.style === "curly") { for (const [y, x] of [[1, 2], [1, 9], [2, 1], [2, 10], [3, 1], [3, 10]]) set(y, x, "H"); }
  if (look.style === "cap") {
    r[0] = "...OOOOOO...".split(""); r[1] = "..OCCCCCCO..".split(""); r[2] = "..OCCACCCO..".split("");
    if (view === "front") r[3] = "OOOCCCCCCO..".split(""); else r[3] = "..OCCCCCCO..".split("");
  }
  const o = look.style === "bun" ? 1 : 0;   // sanggul menggeser semua baris 1 px ke bawah
  if (look.glasses && view === "front" && /E/.test(r[5 + o]?.join("") ?? "")) { const row = r[5 + o]; for (let x = 3; x <= 8; x++) if (row[x] === "S") row[x] = "G"; }
  if (look.headphone) { set(1 + o, 2, "K"); set(1 + o, 9, "K"); for (let y = 3; y <= 5; y++) { set(y + o, 1, "K"); set(y + o, 10, "K"); } set(0 + o, 3, "K"); set(0 + o, 8, "K"); }
  return r.map((x) => x.join(""));
}

const cache = new Map<string, HTMLCanvasElement>();
function bake(key: string, rows: string[], look: Look): HTMLCanvasElement {
  const hit = cache.get(key);
  if (hit) return hit;
  const c = document.createElement("canvas");
  c.width = 12; c.height = rows.length;
  const g = c.getContext("2d")!;
  const pal: Record<string, string> = {
    O: "#1B1626", H: look.hair, h: shade(look.hair, 0.72), S: look.skin, s: shade(look.skin, 0.8), E: "#1B1626", M: "#7A2E2E",
    T: look.shirt, t: shade(look.shirt, 0.78), L: shade(look.shirt, 1.18), P: look.pants, p: shade(look.pants, 0.75), B: "#2A2733",
    C: look.accent, A: look.accent, G: "#1B1626", W: "#FDFBF4", K: "#232A3A",
  };
  rows.forEach((row, y) => [...row].forEach((ch, x) => { if (pal[ch]) { g.fillStyle = pal[ch]; g.fillRect(x, y, 1, 1); } }));
  // kilau rambut
  g.fillStyle = "rgba(255,255,255,.2)"; g.fillRect(4, rows.length > 19 ? 2 : 1, 2, 1);
  cache.set(key, c);
  return c;
}

const apply = (base: string[], patch: Record<number, string>) => base.map((row, y) => patch[y] ?? row);

export type Pose = "stand" | "walk" | "sit" | "sleep" | "cheer" | "drink" | "carry" | "phone" | "talk" | "shock";
export function sprite(look: Look, id: string, pose: Pose, facing: "front" | "back", frame: number): HTMLCanvasElement {
  if (pose === "sit" || pose === "sleep") {
    const rows = withStyle(SIT_BACK, look, "back");
    if (pose === "sleep") { rows[11] = TYPE_ARMS[1]; rows[12] = TYPE_ARMS[1]; return bake(`${id}:sleep`, rows, look); }
    const f = frame % 2;
    rows[11] = TYPE_ARMS[f]; rows[12] = TYPE_ARMS[1 - f];
    return bake(`${id}:sit:${f}`, rows, look);
  }
  const base = facing === "front" ? FRONT : BACK;
  if (pose === "walk") {
    const f = ((frame % 4) + 4) % 4, rows = [...base.slice(0, 11), ...WALK_ARMS[f], ...WALK_LEGS[f]];
    return bake(`${id}:walk:${facing}:${f}`, withStyle(rows, look, facing), look);
  }
  if (facing === "front") {
    if (pose === "cheer") { const f = frame % 2; return bake(`${id}:cheer:${f}`, withStyle(apply(FRONT, CHEER[f]), look, "front"), look); }
    if (pose === "drink") { const f = frame % 6 < 2 ? 1 : 0; return bake(`${id}:drink:${f}`, withStyle(apply(FRONT, DRINK[f]), look, "front"), look); }
    if (pose === "carry") return bake(`${id}:carry`, withStyle(apply(FRONT, CARRY), look, "front"), look);
    if (pose === "phone") return bake(`${id}:phone`, withStyle(apply(FRONT, PHONE), look, "front"), look);
    if (pose === "shock") return bake(`${id}:shock`, withStyle(apply(FRONT, SHOCK), look, "front"), look);
    if (pose === "talk" && frame % 2) return bake(`${id}:talk`, withStyle(apply(FRONT, TALK), look, "front"), look);
  }
  const blink = frame % 37 === 0 && facing === "front";
  const rows = withStyle(base, look, facing);
  if (blink) { const k = look.style === "bun" ? 6 : 5; rows[k] = rows[k].replace(/E/g, "S"); }
  return bake(`${id}:stand:${facing}:${blink ? 1 : 0}`, rows, look);
}

/** Emote piksel 7×7 di atas kepala. # = warna utama, + = warna kedua, o = garis gelap. */
export type Emote = "zzz" | "note" | "bulb" | "kopi" | "cek" | "seru" | "titik" | "bintang" | "kertas" | "hati";
const EMOTE: Record<Emote, { c: [string, string]; rows: string[] }> = {
  zzz: { c: ["#BFE3FF", "#7FB6E6"], rows: ["..###..", "....#..", "...#...", "..###..", "+++....", ".+.....", "+++...."] },
  note: { c: ["#FFD23F", "#FF9A4D"], rows: ["..####.", "..#..#.", "..#..#.", "..#..#.", ".##.##.", "###.##.", ".#....."] },
  bulb: { c: ["#FFE27A", "#C9D3E0"], rows: ["..###..", ".#####.", ".#####.", ".#####.", "..###..", "..+++..", "...+..."] },
  kopi: { c: ["#FDFBF4", "#C98B5A"], rows: [".+..+..", "..+..+.", ".......", "#####..", "#####+.", "#####+.", ".###..."] },
  cek: { c: ["#6FD29A", "#2F7D4C"], rows: [".......", "......#", ".....##", "#...##.", "##.##..", ".###...", "..#...."] },
  seru: { c: ["#FF6B6B", "#FFE4E4"], rows: ["..###..", "..###..", "..###..", "..###..", "...#...", ".......", "..###.."] },
  titik: { c: ["#FDFBF4", "#9DB4CD"], rows: [".......", ".......", ".......", "#..#..#", ".......", ".......", "......."] },
  bintang: { c: ["#FFD23F", "#FFF4B8"], rows: ["...#...", "...#...", ".#####.", "#######", ".#####.", ".##.##.", "##...##"] },
  kertas: { c: ["#FDFBF4", "#7FA6D6"], rows: [".####..", ".#####.", ".#+++#.", ".#####.", ".#+++#.", ".#####.", ".#####."] },
  hati: { c: ["#FF6BCB", "#FFC2E2"], rows: [".......", ".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."] },
};
const emoteCache = new Map<string, HTMLCanvasElement>();
export function emote(kind: Emote, frame = 0): HTMLCanvasElement {
  const tampil = kind === "titik" ? (frame % 4) : kind === "zzz" ? (frame % 3) : 0, key = `${kind}:${tampil}`;
  const hit = emoteCache.get(key);
  if (hit) return hit;
  const c = document.createElement("canvas"); c.width = 9; c.height = 9;
  const g = c.getContext("2d")!, e = EMOTE[kind];
  const lit = (x: number, y: number, ch: string) => {
    if (kind === "titik") return x <= tampil * 3 && tampil > 0 ? ch === "#" : false;      // titik muncul satu per satu
    if (kind === "zzz" && ch === "+") return tampil >= 1;                                   // z kecil menyusul
    return ch === "#" || ch === "+";
  };
  // garis gelap di sekeliling supaya terbaca di latar apa pun
  g.fillStyle = "rgba(10,16,30,.85)";
  e.rows.forEach((row, y) => [...row].forEach((ch, x) => { if (lit(x, y, ch)) g.fillRect(x, y, 3, 3); }));
  e.rows.forEach((row, y) => [...row].forEach((ch, x) => { if (lit(x, y, ch)) { g.fillStyle = ch === "#" ? e.c[0] : e.c[1]; g.fillRect(x + 1, y + 1, 1, 1); } }));
  emoteCache.set(key, c);
  return c;
}

/** Avatar 16×16 untuk panel. */
export function drawAvatar(canvas: HTMLCanvasElement, look: Look, id: string) {
  const g = canvas.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, canvas.width, canvas.height);
  const s = sprite(look, id, "stand", "front", 1);
  g.drawImage(s, 0, 0, 12, 13, 2, 3, 12, 13);
}

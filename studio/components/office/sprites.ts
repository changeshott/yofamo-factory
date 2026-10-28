/* Sprite karakter pixel-art, digambar dari peta karakter (12 × 19 px).
   Kunci warna: O garis, H rambut, h rambut gelap, S kulit, s kulit gelap, E mata,
   T baju, t baju gelap, P celana, p celana gelap, B sepatu, C topi, G kacamata, A aksen. */

export type HairStyle = "short" | "long" | "cap" | "bun" | "curly";
export interface Look {
  skin: string;
  hair: string;
  shirt: string;
  pants: string;
  accent: string;
  style: HairStyle;
  glasses?: boolean;
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
const WALK_LEGS = [
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OBBOOPpO..", "..OOOOOBBO..", "......OOO..."],
  ["..OPPPPPPO..", "..OPPOOPPO..", "..OpPOOBBO..", "..OBBOOOOO..", "...OOO......"],
];
const SIT_BACK = [...BACK.slice(0, 13), ".OTOTTTTOTO.", "..OPPPPPPO..", "..OOOOOOOO.."];
const TYPE_ARMS = [".OTtTTTTtTO.", ".OtTTTTTTtO."];

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
    for (let y = 3; y <= 11; y++) { set(y, 1, "O"); set(y, 2, "H"); set(y, 9, "H"); set(y, 10, "O"); }
    if (view === "back") for (let y = 7; y <= 10; y++) for (let x = 3; x <= 8; x++) set(y, x, y === 10 ? "h" : "H");
  }
  if (look.style === "bun") { set(0, 4, "H"); set(0, 5, "H"); set(0, 6, "H"); set(0, 7, "H"); r.unshift("....OHHO....".split("")); r.pop(); }
  if (look.style === "curly") { for (const [y, x] of [[1, 2], [1, 9], [2, 1], [2, 10], [3, 1], [3, 10]]) set(y, x, "H"); }
  if (look.style === "cap") {
    r[0] = "...OOOOOO...".split(""); r[1] = "..OCCCCCCO..".split(""); r[2] = "..OCCACCCO..".split("");
    if (view === "front") r[3] = "OOOCCCCCCO..".split(""); else r[3] = "..OCCCCCCO..".split("");
  }
  if (look.glasses && view === "front") { r[5] = "..OGEGGEGO..".split(""); }
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
    O: "#1B1626", H: look.hair, h: shade(look.hair, 0.72), S: look.skin, s: shade(look.skin, 0.8), E: "#1B1626",
    T: look.shirt, t: shade(look.shirt, 0.78), P: look.pants, p: shade(look.pants, 0.75), B: "#2A2733",
    C: look.accent, A: look.accent, G: "#1B1626",
  };
  rows.forEach((row, y) => [...row].forEach((ch, x) => { if (pal[ch]) { g.fillStyle = pal[ch]; g.fillRect(x, y, 1, 1); } }));
  // kilau rambut & baju
  g.fillStyle = "rgba(255,255,255,.18)"; g.fillRect(4, 1, 2, 1);
  cache.set(key, c);
  return c;
}

export type Pose = "stand" | "walk" | "sit";
export function sprite(look: Look, id: string, pose: Pose, facing: "front" | "back", frame: number): HTMLCanvasElement {
  if (pose === "sit") {
    const f = frame % 2, rows = withStyle(SIT_BACK, look, "back");
    rows[11] = TYPE_ARMS[f]; rows[12] = TYPE_ARMS[1 - f];
    return bake(`${id}:sit:${f}`, rows, look);
  }
  const base = facing === "front" ? FRONT : BACK;
  if (pose === "walk") {
    const f = frame % 2, legs = WALK_LEGS[f], rows = [...base.slice(0, 14), ...legs];
    return bake(`${id}:walk:${facing}:${f}`, withStyle(rows, look, facing), look);
  }
  const blink = frame % 37 === 0 && facing === "front";
  const rows = withStyle(base, look, facing);
  if (blink) rows[5] = rows[5].replace(/E/g, "S");
  return bake(`${id}:stand:${facing}:${blink ? 1 : 0}`, rows, look);
}

/** Avatar 16×16 untuk panel. */
export function drawAvatar(canvas: HTMLCanvasElement, look: Look, id: string) {
  const g = canvas.getContext("2d")!;
  g.imageSmoothingEnabled = false;
  g.clearRect(0, 0, canvas.width, canvas.height);
  const s = sprite(look, id, "stand", "front", 1);
  g.drawImage(s, 0, 0, 12, 13, 2, 3, 12, 13);
}

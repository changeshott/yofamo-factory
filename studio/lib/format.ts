export const fmt = (n: number | null | undefined) => (n == null ? "–" : Number(n).toLocaleString("id-ID"));
export const dec = (n: number | null | undefined) => (n == null ? "–" : Number(n).toLocaleString("id-ID", { maximumFractionDigits: 2 }));
export const short = (n: number) => (n >= 1000 ? (n / 1000).toLocaleString("id-ID", { maximumFractionDigits: 1 }) + " rb" : String(Math.round(n)));
export const cleanTitle = (t: string) => t.replace(/#\S+/g, "").replace(/\s{2,}/g, " ").trim();
export const daysSince = (iso: string) => Math.floor((Date.now() - Date.parse(iso + "T00:00:00")) / 864e5);

const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
export const when = (iso?: string | null) => {
  if (!iso) return "";
  const d = iso.slice(0, 10), t = iso.slice(11, 16);
  return d === today() ? `hari ini ${t}` : `${d.slice(8, 10)}/${d.slice(5, 7)} ${t}`;
};

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);
function inline(t: string) {
  return esc(t)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[\s(])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
}
/** Markdown kecil untuk laporan Steve (judul, daftar, tabel, kutipan, kode). Semua teks di-escape. */
export function md(text: string): string {
  const L = text.replace(/\r/g, "").split("\n"), out: string[] = [];
  const cells = (l: string) => l.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
  let i = 0;
  while (i < L.length) {
    const l = L[i];
    if (/^```/.test(l)) { const b: string[] = []; i++; while (i < L.length && !/^```/.test(L[i])) b.push(L[i++]); i++; out.push(`<pre>${esc(b.join("\n"))}</pre>`); continue; }
    const h = l.match(/^(#{1,4})\s+(.*)/);
    if (h) { const n = Math.min(h[1].length, 3); out.push(`<h${n}>${inline(h[2])}</h${n}>`); i++; continue; }
    if (/^\s*\|/.test(l) && /^\s*\|?\s*:?-{2,}/.test(L[i + 1] ?? "")) {
      const hd = cells(l); i += 2; const bd: string[][] = [];
      while (i < L.length && /^\s*\|/.test(L[i])) bd.push(cells(L[i++]));
      out.push(`<table><thead><tr>${hd.map((c) => `<th>${inline(c)}</th>`).join("")}</tr></thead><tbody>${bd.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join("")}</tr>`).join("")}</tbody></table>`);
      continue;
    }
    if (/^\s*([-*]|\d+\.)\s+/.test(l)) {
      const ol = /^\s*\d+\./.test(l), it: string[] = [];
      while (i < L.length && /^\s*([-*]|\d+\.)\s+/.test(L[i])) it.push(L[i++].replace(/^\s*([-*]|\d+\.)\s+/, ""));
      out.push(`<${ol ? "ol" : "ul"}>${it.map((x) => `<li>${inline(x)}</li>`).join("")}</${ol ? "ol" : "ul"}>`); continue;
    }
    if (/^>\s?/.test(l)) { out.push(`<blockquote>${inline(l.replace(/^>\s?/, ""))}</blockquote>`); i++; continue; }
    if (!l.trim()) { i++; continue; }
    const p: string[] = [];
    while (i < L.length && L[i].trim() && !/^(#{1,4}\s|```|\s*\||\s*([-*]|\d+\.)\s|>)/.test(L[i])) p.push(L[i++]);
    if (!p.length) p.push(L[i++]);
    out.push(`<p>${inline(p.join(" "))}</p>`);
  }
  return out.join("");
}

export async function api<T = { ok: boolean; message: string }>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(path, body === undefined ? { cache: "no-store" } : {
    method: "POST", headers: { "Content-Type": "application/json", "X-Yofamo": "1" }, body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { message?: string; error?: string }).message ?? (data as { error?: string }).error ?? `HTTP ${res.status}`);
  return data as T;
}

/** Saat produksi berjalan: job agent yang sedang bekerja (dipakai kantor & dok). */
export function activeStage(state: { produksi?: { status: string; tahap: { status: string; job: string }[] }[] } | null): string {
  const p = state?.produksi?.[0];
  if (!p) return "";
  const t = p.tahap.find((x) => x.status === "jalan") ?? [...p.tahap].reverse().find((x) => x.status !== "menunggu");
  return t?.job ?? "";
}

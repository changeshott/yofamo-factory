"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/format";
import { Btn, CopyBtn, H3, Muted, Pill } from "./ui";
import type { AgentDef } from "./office/world";
import type { PanelCtx } from "./panels";

/* ---------------------------------------------------------------- tipe data dari /api/trading */
type Bar = [number, number, number, number, number];
interface Setup { jenis: string; arah: "beli" | "jual"; masuk: number; stop: number; target: number; rr_kotor?: number }
interface Sinyal {
  id: string; pasar: "meme" | "gold"; simbol: string; token: string; url?: string; dibuat: string; status: string; keyakinan: number; tahan_maks_jam: number;
  setup: Setup; grafik?: Bar[]; posisi?: string; posisi_nyata?: string;
  teknikal: { skor: number; data: Record<string, number | string | boolean>; catatan: string[] };
  fundamental: { skor: number; catatan: string[] };
  keamanan: { skor: number; peringatan: string[]; rincian: Record<string, unknown> };
  simulasi: { cukup: boolean; target_dulu_dari_selesai_pct: number; impas_pct: number; ev_R: number; vonis: string; peluang_stop_pct: number };
  riwayat: { muncul: number; target: number; stop: number; waktu_habis: number; catatan: string };
  risiko: { posisi_usd: number; rugi_di_stop_usd: number; untung_di_target_usd: number; biaya_pp_pct: number; risiko_pct: number; target_pct: number; leverage?: number; margin_usd?: number; likuidasi_kira?: number };
}
interface Posisi { id: string; simbol: string; token: string; pasar: string; arah: string; mode: "latihan" | "nyata"; dibuka: string; masuk: number; stop: number; target: number; posisi_usd: number; status: string; harga_kini?: number; pnl_kini_usd?: number; keluar?: number; ditutup?: string; pnl_usd?: number; R?: number }
interface Stat { trade: number; menang: number; kalah: number; winrate: number | null; rataR: number | null; pnl: number; hariIni: number; perHari: number | null; hariAktif: number; terbuka: number }
interface Papan { waktu: string; pasar: string; mode: string; detik: number; sinyal: string[]; diblokir: { simbol: string; token: string; alasan: string[]; setup?: string }[]; dipantau: { simbol: string; token: string; skor_teknikal: number; skor_fundamental: number; skor_keamanan: number | null; catatan: string[]; harga?: number }[] }
interface Cfg { mode: "latihan" | "nyata"; modal_usd: number; risiko_per_trade_usd: number; batas_rugi_harian_usd: number; maks_trade_harian: number; maks_porsi_modal: number; target_harian_usd: number; min_peluang_target_pct: number; pantau_menit: number; biaya_fomo_per_sisi_pct: number }
interface Data { cfg: Cfg | null; papan: Papan | null; sinyal: Sinyal[]; analisa: string[]; posisi: Posisi[]; peringatan: { waktu: string; posisi: string; jenis: string; teks: string }[]; statistik: { latihan: Stat; nyata: Stat }; pindai: boolean; loop: boolean }

/* ---------------------------------------------------------------- format */
const SUB = "₀₁₂₃₄₅₆₇₈₉";
export function harga(x?: number | null): string {
  if (x === undefined || x === null || !Number.isFinite(x)) return "–";
  if (x >= 1000) return x.toLocaleString("en-US", { maximumFractionDigits: 2 });
  if (x >= 1) return x.toFixed(4);
  const s = x.toFixed(20), m = /^0\.(0*)(\d{4})/.exec(s);
  if (!m) return x.toPrecision(4);
  const nol = m[1].length;
  return nol >= 4 ? `0.0${String(nol).split("").map((d) => SUB[+d]).join("")}${m[2]}` : `0.${m[1]}${m[2]}`;
}
const usd = (x?: number | null) => (x === undefined || x === null ? "–" : `${x < 0 ? "−" : ""}$${Math.abs(x).toFixed(2)}`);
const pct = (a: number, b: number) => ((b - a) / a) * 100;
const tanda = (x: number) => `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(1)}%`;

/* ---------------------------------------------------------------- grafik mini */
function Grafik({ bars, s }: { bars: Bar[]; s?: Setup }) {
  const b = bars.slice(-72);
  if (b.length < 5) return null;
  const nilai = b.flatMap((x) => [x[2], x[3]]).concat(s ? [s.stop, s.target, s.masuk] : []);
  const lo = Math.min(...nilai), hi = Math.max(...nilai), W = 300, H = 96, y = (v: number) => H - 4 - ((v - lo) / (hi - lo || 1)) * (H - 8), w = W / b.length;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="mt-2 h-24 w-full rounded-md border border-line bg-[#06100B]" role="img" aria-label="Grafik candle 5 menit terakhir">
      {b.map((x, i) => { const naik = x[4] >= x[1], c = naik ? "#39D36B" : "#F2385A"; return (
        <g key={i}><line x1={i * w + w / 2} x2={i * w + w / 2} y1={y(x[2])} y2={y(x[3])} stroke={c} strokeWidth={0.8} />
          <rect x={i * w + w * 0.18} width={w * 0.64} y={y(Math.max(x[1], x[4]))} height={Math.max(0.8, Math.abs(y(x[1]) - y(x[4])))} fill={c} /></g>); })}
      {s && ([["masuk", s.masuk, "#F4F1E8"], ["stop", s.stop, "#F2385A"], ["target", s.target, "#39D36B"]] as const).map(([n, v, c]) => (
        <g key={n}><line x1={0} x2={W} y1={y(v)} y2={y(v)} stroke={c} strokeWidth={0.8} strokeDasharray="4 3" /><text x={W - 3} y={y(v) - 2} textAnchor="end" fontSize={8} fill={c}>{n}</text></g>))}
    </svg>
  );
}

function Angka({ label, nilai, sub, tone }: { label: string; nilai: string; sub?: string; tone?: "naik" | "turun" }) {
  return (
    <div className="rounded-md border border-line/70 bg-ink-950/60 px-2 py-1.5">
      <div className="text-[11px] text-faint uppercase">{label}</div>
      <div className={`font-mono text-[14px] ${tone === "naik" ? "text-leaf" : tone === "turun" ? "text-bad" : ""}`}>{nilai}</div>
      {sub && <div className="text-[11px] text-muted">{sub}</div>}
    </div>
  );
}

/* ---------------------------------------------------------------- kartu sinyal */
function KartuSinyal({ s, cfg, adaAnalisa, aksi }: { s: Sinyal; cfg: Cfg; adaAnalisa: boolean; aksi: (b: Record<string, unknown>) => Promise<void> }) {
  const [form, setForm] = useState(false), [h, setH] = useState(""), [u, setU] = useState(""), [teks, setTeks] = useState<string | null>(null);
  const st = s.setup, r = s.risiko, m = s.simulasi, beli = st.arah === "beli";
  const kotor = (x: number) => tanda(beli ? pct(st.masuk, x) : -pct(st.masuk, x));
  const baca = async () => setTeks((await api<{ teks: string | null }>(`/api/trading?analisa=${encodeURIComponent(s.id)}`)).teks ?? "Belum ada analisa.");
  return (
    <li className="rounded-xl border border-line/70 bg-ink-950/50 p-3">
      <div className="flex items-start justify-between gap-2">
        <span className="min-w-0"><b className="font-pixel text-[15px]">{s.simbol}</b> <span className="text-sm text-muted">· {s.pasar === "gold" ? "gold perpetual" : "memecoin Solana"} · {st.jenis} · <span className={beli ? "text-leaf" : "text-bad"}>{beli ? "BELI" : "JUAL (short)"}</span></span>
          <small className="block text-faint">{s.dibuat.replace("T", " ").slice(0, 16)} WIB · oleh tim · keyakinan {s.keyakinan}/100</small></span>
        <Pill tone={s.status === "latihan" ? "default" : s.status === "dibeli" ? "ok" : s.status === "dilewati" ? "stopped" : "running"}>{({ latihan: "latihan", baru: "menunggu kamu", dibeli: "kamu beli", dilewati: "dilewati" } as Record<string, string>)[s.status] ?? s.status}</Pill>
      </div>
      {s.pasar === "meme" && <div className="mt-2 flex items-center gap-2 rounded-md border border-line bg-ink-950 px-2 py-1"><code className="min-w-0 flex-1 truncate text-[12px]">{s.token}</code><CopyBtn text={s.token} label="Salin alamat" /></div>}
      {s.grafik && <Grafik bars={s.grafik} s={st} />}
      <div className="mt-2 grid grid-cols-3 gap-1.5">
        <Angka label="Masuk" nilai={harga(st.masuk)} />
        <Angka label="Stop" nilai={harga(st.stop)} sub={kotor(st.stop)} tone="turun" />
        <Angka label="Target" nilai={harga(st.target)} sub={kotor(st.target)} tone="naik" />
        <Angka label="Posisi" nilai={usd(r.posisi_usd)} sub={r.leverage ? `leverage ${r.leverage}× · margin ${usd(r.margin_usd)}` : `${Math.round((r.posisi_usd / cfg.modal_usd) * 100)}% modal`} />
        <Angka label="Rugi di stop" nilai={usd(-r.rugi_di_stop_usd)} sub={`biaya ${r.biaya_pp_pct}% sudah dihitung`} tone="turun" />
        <Angka label="Untung di target" nilai={usd(r.untung_di_target_usd)} sub="bersih setelah biaya" tone="naik" />
      </div>
      <div className="mt-2 rounded-md border border-line/70 bg-ink-950/60 p-2 text-sm">
        <b>Mesin waktu 10.000×:</b> target duluan <b>{m.target_dulu_dari_selesai_pct}%</b> (impas butuh {m.impas_pct}%) · EV {m.ev_R >= 0 ? "+" : ""}{m.ev_R}R — {m.vonis}
        <div className="text-muted">Riwayat setup yang sama: muncul {s.riwayat.muncul}× → {s.riwayat.target} target, {s.riwayat.stop} stop, {s.riwayat.waktu_habis} waktu habis{s.riwayat.catatan ? ` (${s.riwayat.catatan})` : ""}.</div>
      </div>
      <ul className="mt-2 list-disc space-y-0.5 pl-5 text-sm text-muted">
        <li>Teknikal {s.teknikal.skor}/100: tren 1 jam {String(s.teknikal.data.tren_1j)}, RSI {String(s.teknikal.data.rsi)}, volume {String(s.teknikal.data.volume_x)}× rata-rata, ATR {String(s.teknikal.data.atr_pct)}%.</li>
        <li>Fundamental {s.fundamental.skor}/100: {s.fundamental.catatan.slice(0, 2).join("; ")}.</li>
        <li>Keamanan {s.keamanan.skor}/100{s.keamanan.peringatan.length ? `: ${s.keamanan.peringatan.slice(0, 3).join("; ")}` : ""}.</li>
        {r.likuidasi_kira ? <li>Perkiraan harga likuidasi ±{harga(r.likuidasi_kira)} (cek angka pasti di aplikasi sebelum masuk).</li> : null}
      </ul>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        {s.status === "baru" && cfg.mode === "nyata" && <Btn size="sm" tone="primary" onClick={() => { setForm(!form); setH(String(st.masuk)); setU(String(r.posisi_usd)); }}>Saya beli di FOMO</Btn>}
        {s.status === "baru" && <Btn size="sm" tone="ghost" onClick={() => void aksi({ aksi: "lewati", sinyal: s.id })}>Lewati</Btn>}
        <Btn size="sm" tone="ghost" onClick={() => void aksi({ aksi: "analisa", id: s.id })}>Analisa mendalam (Nadia)</Btn>
        {adaAnalisa && <Btn size="sm" tone="ghost" onClick={() => void baca()}>Baca analisa</Btn>}
        {s.url && <a className="text-sm text-muted underline" href={s.url} target="_blank" rel="noopener noreferrer">{s.pasar === "gold" ? "Hyperliquid" : "DexScreener"}</a>}
        {s.pasar === "meme" && <a className="text-sm text-muted underline" href={`https://rugcheck.xyz/tokens/${s.token}`} target="_blank" rel="noopener noreferrer">RugCheck</a>}
      </div>
      {form && (
        <div className="mt-2 rounded-md border border-brand/50 bg-ink-950 p-2 text-sm">
          <Muted>Isi sesuai yang benar-benar terjadi di FOMO (harga rata-rata beli & jumlah dolar). Stop & target ikut bergeser kalau harga belimu beda.</Muted>
          <div className="mt-1.5 flex flex-wrap gap-2">
            <label className="flex items-center gap-1">Harga <input value={h} onChange={(e) => setH(e.target.value)} inputMode="decimal" className="w-36 rounded border border-line bg-ink-900 px-2 py-1 font-mono" /></label>
            <label className="flex items-center gap-1">Dolar <input value={u} onChange={(e) => setU(e.target.value)} inputMode="decimal" className="w-20 rounded border border-line bg-ink-900 px-2 py-1 font-mono" /></label>
            <Btn size="sm" tone="primary" onClick={() => { void aksi({ aksi: "beli", sinyal: s.id, harga: h, usd: u }); setForm(false); }}>Catat</Btn>
          </div>
        </div>
      )}
      {teks && <pre className="mt-2 max-h-80 overflow-auto rounded-md border border-line bg-ink-950 p-2 text-[12.5px] whitespace-pre-wrap">{teks}</pre>}
    </li>
  );
}

function BarisPosisi({ p, aksi }: { p: Posisi; aksi: (b: Record<string, unknown>) => Promise<void> }) {
  const [h, setH] = useState(""), [buka, setBuka] = useState(false);
  const terbuka = p.status === "terbuka", pnl = terbuka ? p.pnl_kini_usd : p.pnl_usd;
  return (
    <li className="rounded-lg border border-line/70 bg-ink-950/50 p-2 text-sm">
      <div className="flex items-center justify-between gap-2">
        <span><b>{p.simbol}</b> <span className="text-muted">· {p.mode} · {p.arah}</span></span>
        <span className={`font-mono ${(pnl ?? 0) >= 0 ? "text-leaf" : "text-bad"}`}>{usd(pnl)}{!terbuka && p.R !== undefined ? ` (${p.R >= 0 ? "+" : ""}${p.R}R)` : ""}</span>
      </div>
      <div className="font-mono text-[12px] text-muted">masuk {harga(p.masuk)} · {terbuka ? `kini ${harga(p.harga_kini)}` : `keluar ${harga(p.keluar)} (${p.status})`} · stop {harga(p.stop)} · target {harga(p.target)} · {usd(p.posisi_usd)}</div>
      {terbuka && p.mode === "nyata" && (
        <div className="mt-1.5 flex flex-wrap items-center gap-2">
          {!buka ? <Btn size="sm" onClick={() => { setBuka(true); setH(String(p.harga_kini ?? p.masuk)); }}>Saya sudah jual</Btn> : (<>
            <input value={h} onChange={(e) => setH(e.target.value)} inputMode="decimal" aria-label="Harga jual" className="w-36 rounded border border-line bg-ink-900 px-2 py-1 font-mono" />
            <Btn size="sm" tone="primary" onClick={() => void aksi({ aksi: "jual", posisi: p.id, harga: h })}>Catat jual</Btn></>)}
        </div>
      )}
    </li>
  );
}

function Aturan({ cfg, aksi }: { cfg: Cfg; aksi: (b: Record<string, unknown>) => Promise<void> }) {
  const kunci: [keyof Cfg, string][] = [["modal_usd", "Modal ($)"], ["risiko_per_trade_usd", "Rugi maks per trade ($)"], ["batas_rugi_harian_usd", "Batas rugi harian ($)"],
    ["maks_trade_harian", "Maks trade per hari"], ["maks_porsi_modal", "Posisi maks (porsi modal, 0–1)"], ["min_peluang_target_pct", "Peluang target minimal (%)"],
    ["pantau_menit", "Pindai otomatis tiap (menit)"], ["biaya_fomo_per_sisi_pct", "Biaya FOMO per transaksi (%)"]];
  const [v, setV] = useState<Record<string, string>>(() => Object.fromEntries(kunci.map(([k]) => [k, String(cfg[k])])));
  const [konf, setKonf] = useState("");
  return (
    <details className="mt-2 rounded-lg border border-line/70 bg-ink-950/50 p-2">
      <summary className="cursor-pointer text-sm">Ubah aturan & mode</summary>
      <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
        {kunci.map(([k, l]) => <label key={k} className="flex flex-col gap-0.5"><span className="text-muted">{l}</span>
          <input value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} inputMode="decimal" className="rounded border border-line bg-ink-900 px-2 py-1 font-mono" /></label>)}
      </div>
      <Btn size="sm" tone="primary" className="mt-2" onClick={() => void aksi({ aksi: "aturan", aturan: v })}>Simpan aturan</Btn>
      <div className="mt-3 border-t border-line/60 pt-2 text-sm">
        Mode sekarang: <b>{cfg.mode}</b>.{" "}
        {cfg.mode === "latihan" ? (<>
          <Muted className="mt-1">Mode nyata: sinyal tidak dicatat otomatis; kamu beli/jual sendiri di FOMO lalu mencatatnya di sini. Saran tim: baru pindah setelah ≥ 30 trade latihan dengan hasil bersih positif.</Muted>
          <div className="mt-1.5 flex flex-wrap items-center gap-2"><input value={konf} onChange={(e) => setKonf(e.target.value)} placeholder="ketik: SAYA PAHAM RISIKONYA" className="min-w-0 flex-1 rounded border border-line bg-ink-900 px-2 py-1" />
            <Btn size="sm" tone="danger" disabled={konf !== "SAYA PAHAM RISIKONYA"} onClick={() => void aksi({ aksi: "aturan", aturan: { mode: "nyata", konfirmasi: konf } })}>Pindah ke mode nyata</Btn></div></>)
          : <Btn size="sm" className="mt-1.5" onClick={() => void aksi({ aksi: "aturan", aturan: { mode: "latihan" } })}>Kembali ke mode latihan</Btn>}
      </div>
    </details>
  );
}

/* ---------------------------------------------------------------- panel utama */
export function RuangTradingPanel({ ctx, def }: { ctx: PanelCtx; def?: AgentDef }) {
  void ctx;
  const [d, setD] = useState<Data | null>(null);
  const [pesan, setPesan] = useState("");
  const muat = () => fetch("/api/trading", { cache: "no-store" }).then((r) => r.json()).then(setD).catch(() => {});
  useEffect(() => { void muat(); const t = setInterval(() => void muat(), 6000); return () => clearInterval(t); }, []);
  const aksi = async (body: Record<string, unknown>) => {
    try { const r = await api<{ message: string }>("/api/trading", body); setPesan(r.message); } catch (e) { setPesan((e as Error).message); }
    void muat();
  };
  if (!d) return <Muted>Memuat Ruang Trading…</Muted>;
  if (!d.cfg) return <Muted>bible/trading.json belum ada. Perbarui project (git pull) lalu buka lagi.</Muted>;
  const c = d.cfg, st = d.statistik[c.mode], terbuka = d.posisi.filter((p) => p.status === "terbuka"), selesai = d.posisi.filter((p) => p.status !== "terbuka").slice(0, 10);
  const persenTarget = (c.target_harian_usd / c.modal_usd) * 100;
  return (<>
    {def ? <p>{def.about}</p> : <p>Tim analisa memecoin Solana (kamu beli sendiri di <b>FOMO</b>) dan gold. Arga memindai → Sinta membuang yang berbahaya → Dimas membaca chart → Nadia menilai fundamental → Bagas memutar 10.000 kemungkinan & mengukur risiko → Yudi mencatat. <b>Tidak ada order yang dikirim agent</b>; FOMO tidak punya API dan private key tidak pernah diminta.</p>}
    <div className="mt-2 rounded-lg border border-[#F2C94C]/50 bg-[#F2C94C]/10 p-2.5 text-sm">
      <b>Jujur soal target:</b> ${c.target_harian_usd}/hari dari modal ${c.modal_usd} = <b>{persenTarget.toFixed(0)}% per hari</b>. Biaya FOMO + slippage ±{(2 * (c.biaya_fomo_per_sisi_pct + 0.4)).toFixed(1)}% tiap beli-jual.
      Dengan aturan sekarang, rugi maks {usd(c.risiko_per_trade_usd)}/trade dan berhenti kalau rugi {usd(c.batas_rugi_harian_usd)}/hari. Nilai realistis dilihat dari hasil latihan, bukan dari target. Bukan nasihat keuangan.
    </div>

    <H3>Kendali</H3>
    <div className="flex flex-wrap items-center gap-2">
      <Pill tone={c.mode === "nyata" ? "error" : "default"}>mode {c.mode}</Pill>
      <Btn tone="primary" disabled={d.pindai} onClick={() => void aksi({ aksi: "pindai", pasar: "meme" })}>{d.pindai ? "Memindai…" : "Pindai memecoin"}</Btn>
      <Btn disabled={d.pindai} onClick={() => void aksi({ aksi: "pindai", pasar: "gold" })}>Pindai gold</Btn>
      <Btn tone={d.loop ? "danger" : "ghost"} onClick={() => void aksi({ aksi: "loop", nyala: !d.loop })}>{d.loop ? "Matikan pantau otomatis" : "Pantau otomatis"}</Btn>
    </div>
    <Muted className="mt-1.5">{d.loop ? `Pantau otomatis menyala: pindai memecoin & gold tiap ${c.pantau_menit} menit dan cek posisi tiap menit (selama laptop & Studio hidup).` : "Pantau otomatis: tim memindai sendiri tiap beberapa menit dan memantau posisi selama laptop hidup."}</Muted>
    {pesan && <Muted className="mt-1 text-leaf">{pesan}</Muted>}

    {d.peringatan.length > 0 && (<>
      <H3>Peringatan posisi nyata</H3>
      <ul className="space-y-1.5">{d.peringatan.slice(0, 4).map((w, i) => <li key={i} className={`rounded-md border p-2 text-sm ${w.jenis === "stop" ? "border-bad/60 bg-bad/10" : "border-leaf/60 bg-leaf/10"}`}>{w.teks}<small className="block text-faint">{w.waktu.replace("T", " ").slice(0, 16)}</small></li>)}</ul>
    </>)}

    <H3>Sinyal terbaru ({d.sinyal.length})</H3>
    {d.sinyal.length === 0 && <Muted>Belum ada sinyal yang lolos semua saringan. Itu normal: kebanyakan koin diblokir atau belum memberi setup. Tekan Pindai atau nyalakan pantau otomatis.</Muted>}
    <ul className="space-y-3">{d.sinyal.map((s) => <KartuSinyal key={s.id} s={s} cfg={c} adaAnalisa={d.analisa.includes(s.id)} aksi={aksi} />)}</ul>

    <H3>Posisi terbuka ({terbuka.length})</H3>
    {terbuka.length === 0 ? <Muted>Tidak ada posisi terbuka.</Muted> : <ul className="space-y-1.5">{terbuka.map((p) => <BarisPosisi key={p.id} p={p} aksi={aksi} />)}</ul>}

    <H3>Hasil (setelah biaya)</H3>
    <div className="grid grid-cols-2 gap-2 text-sm">
      {(["latihan", "nyata"] as const).map((m) => { const x = d.statistik[m]; return (
        <div key={m} className={`rounded-lg border p-2 ${m === c.mode ? "border-brand/60" : "border-line/70"} bg-ink-950/50`}>
          <b className="capitalize">{m}</b>
          <div className="font-mono text-[13px]">{x.trade} trade · menang {x.winrate ?? "–"}%</div>
          <div className={`font-mono text-[13px] ${x.pnl >= 0 ? "text-leaf" : "text-bad"}`}>total {usd(x.pnl)} · hari ini {usd(x.hariIni)}</div>
          <div className="text-[12px] text-muted">rata-rata {x.rataR ?? "–"}R · {x.perHari !== null ? `${usd(x.perHari)}/hari aktif` : "belum ada hari aktif"}</div>
        </div>); })}
    </div>
    <Muted className="mt-1">{st.trade < 30 ? `Mode ${c.mode}: ${st.trade}/30 trade — belum cukup untuk menilai sistem ini.` : `Mode ${c.mode}: ${st.trade} trade tercatat.`} Hari ini {usd(st.hariIni)} dari target {usd(c.target_harian_usd)} (batas rugi {usd(-c.batas_rugi_harian_usd)}).</Muted>
    {selesai.length > 0 && <ul className="mt-2 space-y-1.5">{selesai.map((p) => <BarisPosisi key={p.id} p={p} aksi={aksi} />)}</ul>}

    {d.papan && (<>
      <H3>Pindaian terakhir</H3>
      <Muted>{d.papan.waktu.replace("T", " ").slice(0, 16)} WIB · {d.papan.pasar} · {d.papan.detik} dtk · {d.papan.sinyal.length} sinyal · {d.papan.diblokir.length} diblokir · {d.papan.dipantau.length} dipantau</Muted>
      {d.papan.dipantau.length > 0 && <ul className="mt-1.5 space-y-1 text-sm">{d.papan.dipantau.map((x) => (
        <li key={x.token} className="rounded-md border border-line/60 bg-ink-950/40 px-2 py-1"><b>{x.simbol}</b> <span className="text-muted">teknikal {x.skor_teknikal} · fundamental {x.skor_fundamental}{x.skor_keamanan !== null ? ` · keamanan ${x.skor_keamanan}` : ""}</span>
          <span className="block text-[12px] text-faint">menunggu: {x.catatan[0] ?? "-"}</span></li>))}</ul>}
      {d.papan.diblokir.length > 0 && <details className="mt-1.5 text-sm"><summary className="cursor-pointer text-muted">Diblokir ({d.papan.diblokir.length})</summary>
        <ul className="mt-1 space-y-1">{d.papan.diblokir.map((x, i) => <li key={i}><b>{x.simbol}</b> <span className="text-muted">— {x.alasan.slice(0, 2).join("; ")}</span></li>)}</ul></details>}
    </>)}

    <H3>Aturan</H3>
    <Muted>Modal {usd(c.modal_usd)} · rugi maks {usd(c.risiko_per_trade_usd)}/trade · batas rugi harian {usd(c.batas_rugi_harian_usd)} · maks {c.maks_trade_harian} trade/hari · posisi maks {Math.round(c.maks_porsi_modal * 100)}% modal · peluang minimal {c.min_peluang_target_pct}%.</Muted>
    <Aturan key={JSON.stringify(c)} cfg={c} aksi={aksi} />
    <details className="mt-2 rounded-lg border border-line/70 bg-ink-950/50 p-2 text-sm">
      <summary className="cursor-pointer">Cara pakai dengan FOMO (mode nyata)</summary>
      <ol className="mt-1.5 list-decimal space-y-1 pl-5 text-muted">
        <li>Tunggu kartu sinyal berstatus <b>menunggu kamu</b>. Baca angka & peringatannya; kalau ragu, tekan Analisa mendalam.</li>
        <li>Salin <b>alamat kontrak</b> → buka FOMO → cari dengan alamat itu (bukan nama; koin tiruan dengan nama sama sangat banyak).</li>
        <li>Beli sejumlah dolar di kartu (jangan lebih). Tekan <b>Saya beli di FOMO</b> dan isi harga & dolar yang sebenarnya.</li>
        <li>Memecoin spot tidak punya stop otomatis: Yudi memberi peringatan di sini saat harga menyentuh stop/target. Jual di FOMO, lalu tekan <b>Saya sudah jual</b>.</li>
        <li>Batas rugi harian tercapai → tim berhenti memberi sinyal sampai besok. Jangan menambah modal untuk mengejar kerugian.</li>
      </ol>
    </details>
  </>);
}

"use client";

import { useEffect, useMemo, useState } from "react";
import type { Produksi, StudioState, Video, VideoStatus } from "@/lib/types";
import { api, cleanTitle, dec, daysSince, fmt, md, short, when } from "@/lib/format";
import { Btn, Copy, CopyBtn, H3, Muted, Pill } from "./ui";
import { FUTURE, TEAM, type AgentDef } from "./office/world";

export interface PanelCtx {
  state: StudioState;
  run: (job: string, arg?: string) => Promise<void>;
  move: (slug: string, status: VideoStatus) => Promise<void>;
  open: (id: string) => void;
  target: number;
  setTarget: (n: number) => void;
  stop: () => Promise<void>;
  hapus: (jenis: string, nama: string, judul: string, laporan?: boolean) => void;
  kelolaTick: number;
}

const busy = (s: StudioState) => s.job.status === "running";
const STATUS_TXT = { idle: "Siap", running: "Bekerja", ok: "Selesai", error: "Gagal", stopped: "Dihentikan" } as const;

/* ---------------------------------------------------------------- log */
export function LogView({ name, live }: { name: string | null; live?: boolean }) {
  const [text, setText] = useState("");
  useEffect(() => {
    if (!name) return;
    let stop = false;
    const load = () => api<{ text: string }>(`/api/log?name=${encodeURIComponent(name)}`).then((r) => !stop && setText(r.text || "(log masih kosong)")).catch(() => {});
    load();
    const t = live ? setInterval(load, 2500) : undefined;
    return () => { stop = true; if (t) clearInterval(t); };
  }, [name, live]);
  if (!name) return null;
  return <pre className="mt-3 max-h-80 overflow-auto rounded-lg border border-line bg-ink-950 p-2.5 font-mono text-[12.5px] leading-relaxed whitespace-pre-wrap break-words text-[#C9D6E4]">{text}</pre>;
}

/* ---------------------------------------------------------------- agent */
export function AgentPanel({ def, ctx }: { def: AgentDef; ctx: PanelCtx }) {
  const { state } = ctx, j = state.job, mine = j.job && def.busy[j.job], st = mine ? j.status : "idle";
  const [theme, setTheme] = useState("");
  const [log, setLog] = useState<string | null>(mine ? j.log : null);
  useEffect(() => { if (mine && j.log) setLog(j.log); }, [mine, j.log]);
  const logs = state.logs.filter((l) => l.name.startsWith(def.job + "-") || (def.id === "steve" && l.name.startsWith("fetch-"))).slice(0, 6);
  const noClaude = !state.health.claude;
  return (
    <div>
      <p>{def.about}</p>
      <dl className="mt-3 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5 text-sm">
        <dt className="text-muted">Status</dt>
        <dd className="flex items-center gap-2"><Pill tone={st === "idle" ? "default" : st}>{STATUS_TXT[st]}</Pill>{mine && j.arg && <span className="text-muted">{j.arg}</span>}</dd>
        <dt className="text-muted">Skill</dt><dd><code className="rounded bg-ink-950 px-1.5">/{def.skill}</code></dd>
      </dl>
      <H3>Tugas</H3>
      {def.id === "steve" && (<>
        <div className="flex flex-wrap gap-2">
          <Btn tone="primary" disabled={busy(state) || noClaude} onClick={() => ctx.run("steve")}>Jalankan Steve</Btn>
          <Btn disabled={busy(state)} onClick={() => ctx.run("fetch")}>Ambil data terbaru</Btn>
        </div>
        <Muted className="mt-2">Ambil data tidak memakai kuota Claude. Jalankan Steve memakai kuota Pro (model Sonnet).</Muted>
      </>)}
      {def.id === "nova" && (<>
        <label className="text-sm text-muted" htmlFor="theme">Arahan tema (opsional)</label>
        <input id="theme" value={theme} onChange={(e) => setTheme(e.target.value)} maxLength={120} placeholder="misalnya makanan masa depan"
          className="mt-1 w-full rounded-lg border border-line bg-ink-950 px-3 py-2 text-sm placeholder:text-faint" />
        <div className="mt-2.5"><Btn tone="primary" disabled={busy(state) || noClaude} onClick={() => ctx.run("ide", theme)}>Cari 3 ide</Btn></div>
        <Muted className="mt-2">Nova membaca banyak halaman web, jadi ini tugas paling boros kuota. Satu putaran cukup untuk beberapa hari.</Muted>
      </>)}
      {def.id === "raka" && (() => {
        const ok = state.videos.filter((v) => v.status === "disetujui");
        return ok.length ? (
          <ul className="divide-y divide-line">{ok.map((v) => (
            <li key={v.slug} className="flex items-center justify-between gap-3 py-2 text-sm"><span>{v.judul_kerja}</span>
              <Btn size="sm" tone="primary" disabled={busy(state) || noClaude} onClick={() => ctx.run("penulis", v.slug)}>Tulis naskah</Btn></li>))}
          </ul>
        ) : (<><Muted>Belum ada ide yang disetujui. Setujui ide Nova di meja Zona dulu.</Muted><Btn className="mt-2" onClick={() => ctx.open("founder")}>Ke meja Zona</Btn></>);
      })()}
      {def.id === "dara" && (() => {
        const ok = state.videos.filter((v) => v.status === "naskah" || v.status === "suara");
        return (<>
          <div className="mb-2 flex items-center gap-2 text-sm"><label className="text-muted" htmlFor="voice">Suara</label>
            <select id="voice" value={theme || "pria"} onChange={(e) => setTheme(e.target.value)} className="rounded-lg border border-line bg-ink-950 px-2 py-1.5">
              <option value="pria">Ardi (pria)</option><option value="wanita">Gadis (wanita)</option></select></div>
          {ok.length ? (
            <ul className="divide-y divide-line">{ok.map((v) => (
              <li key={v.slug} className="flex items-center justify-between gap-3 py-2 text-sm"><span>{v.judul_kerja}{v.media.durasi != null && <small className="block text-faint">{v.media.durasi.toFixed(1)} detik{v.media.uji ? " (uji)" : ""}</small>}</span>
                <Btn size="sm" tone="primary" disabled={busy(state) || !state.health.edgeTts} onClick={() => ctx.run("suara", `${v.slug}|${theme === "wanita" ? "wanita" : "pria"}`)}>{v.media.vo ? "Buat ulang" : "Buat suara"}</Btn></li>))}
            </ul>
          ) : <Muted>Belum ada naskah siap. Minta Raka menulis dulu.</Muted>}
          {!state.health.edgeTts && <Muted className="mt-2 text-signal">Paket edge-tts belum terpasang. Jalankan sekali: <code>python -m pip install -r requirements.txt</code></Muted>}
          <Muted className="mt-2">Gratis, tidak memakai kuota Claude. Butuh internet.</Muted>
        </>);
      })()}
      {def.id === "rara" && (() => {
        const ok = state.videos.filter((v) => v.status === "draft");
        return (<>
          {ok.length ? (
            <ul className="divide-y divide-line">{ok.map((v) => (
              <li key={v.slug} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"><span>{v.judul_kerja}<small className="block text-faint">{v.qc?.skor != null ? `skor ${v.qc.skor}/10` : v.qc ? "sudah dicek otomatis" : "belum diperiksa"}</small></span>
                <span className="flex gap-2">
                  <Btn size="sm" tone="primary" disabled={busy(state) || noClaude} onClick={() => ctx.run("qc", v.slug)}>Periksa teliti</Btn>
                  <Btn size="sm" disabled={busy(state)} onClick={() => ctx.run("qc", `${v.slug}|otomatis`)}>Cepat</Btn>
                </span></li>))}
            </ul>
          ) : <Muted>Belum ada video jadi yang menunggu diperiksa.</Muted>}
          <Muted className="mt-2">Periksa teliti: Rara melihat frame tiap shot (kuota Claude) dan mengganti shot yang tidak sesuai, teks rusak, atau jelek. Cepat: hanya cek otomatis (gelap/beku/durasi/suara), tanpa kuota. Di Buat video, Rara selalu jalan otomatis.</Muted>
        </>);
      })()}
      {def.id === "uli" && (() => {
        const h = state.health, ok = state.videos.filter((v) => v.status === "export");
        return (<>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-muted">Paket Google</dt><dd>{h.google ? "terpasang" : "belum (pip install -r requirements.txt)"}</dd>
            <dt className="text-muted">OAuth client</dt><dd>{h.ytClient ? "ada" : "belum: rahasia/client_secret.json (lihat SETUP.md)"}</dd>
            <dt className="text-muted">YouTube</dt><dd>{h.ytLogin ? "terhubung" : "belum terhubung"}</dd>
          </dl>
          <Btn className="mt-2" size="sm" disabled={busy(state) || !h.google || !h.ytClient} onClick={() => ctx.run("login")}>{h.ytLogin ? "Hubungkan ulang YouTube" : "Hubungkan YouTube"}</Btn>
          <H3>Siap upload ({ok.length})</H3>
          {ok.length ? ok.map((v) => <VideoCard key={v.slug} v={v} ctx={ctx} />) : <Muted>Belum ada video yang kamu setujui.</Muted>}
          <Muted className="mt-2">Upload selalu PRIVATE. Project Google Cloud yang belum diaudit YouTube memang hanya boleh private; kamu mengubahnya ke publik/terjadwal di YouTube Studio. Kuota API ±6 upload per hari.</Muted>
        </>);
      })()}
      {def.id === "kai" && (() => {
        const ok = state.videos.filter((v) => v.status === "aset" || v.status === "draft");
        return (<>
          {ok.length ? (
            <ul className="divide-y divide-line">{ok.map((v) => (
              <li key={v.slug} className="flex items-center justify-between gap-3 py-2 text-sm"><span>{v.judul_kerja}<small className="block text-faint">{v.final.ada ? `final ${v.final.durasi?.toFixed(1)} dtk` : `${v.aset?.klip?.length ?? 0} shot siap dirakit`}</small></span>
                <Btn size="sm" tone="primary" disabled={busy(state) || !state.health.ffmpeg} onClick={() => ctx.run("editor", v.slug)}>{v.final.ada ? "Rakit ulang" : "Rakit video"}</Btn></li>))}
            </ul>
          ) : <Muted>Belum ada video yang visualnya sudah disiapkan Bima.</Muted>}
          <Muted className="mt-2">Gratis, tanpa kuota Claude. Gaya editan (font, warna subtitle, hook, musik) diatur di <code>bible/gaya-edit.json</code>. Musik latar: taruh lagu bebas royalti di folder <code>musik/</code>.</Muted>
        </>);
      })()}
      {def.id === "bima" && (() => {
        const asetReady = state.health.ffmpeg && state.health.stockKey;
        const ok = state.videos.filter((v) => v.status === "suara" || v.status === "aset");
        return (<>
          {ok.length ? (
            <ul className="divide-y divide-line">{ok.map((v) => {
              const n = v.aset?.klip?.length ?? 0;
              return (
                <li key={v.slug} className="flex flex-wrap items-center justify-between gap-2 py-2 text-sm"><span>{v.judul_kerja}<small className="block text-faint">{n ? `${n} shot${v.aset?.uji ? " (uji)" : ""}${v.aset?.kurang?.length ? `, kurang ${v.aset.kurang.length}` : ""}` : "belum ada visual"}</small></span>
                  <span className="flex gap-2">
                    <Btn size="sm" tone="primary" disabled={busy(state) || noClaude || !asetReady} onClick={() => ctx.run("aset", v.slug)}>Siapkan visual</Btn>
                    <Btn size="sm" disabled={busy(state) || !asetReady} onClick={() => ctx.run("aset", `${v.slug}|cepat`)}>Cepat</Btn>
                  </span></li>);
            })}</ul>
          ) : <Muted>Belum ada video yang suaranya sudah dibuat Dara.</Muted>}
          {!asetReady && <Muted className="mt-2 text-signal">Belum siap: {[!state.health.ffmpeg && "ffmpeg", !state.health.stockKey && "PIXABAY_API_KEY"].filter(Boolean).join(", ")}. Lihat menu Sistem.</Muted>}
          {asetReady && (!state.health.ytdlp || !state.health.aiKey) && <Muted className="mt-2">Sumber nonaktif: {[!state.health.ytdlp && "YouTube CC (yt-dlp)", !state.health.aiKey && "gambar AI (Cloudflare)"].filter(Boolean).join(", ")}. Bima tetap jalan dengan sumber lain.</Muted>}
          <Muted className="mt-2">Siapkan visual: Bima merencanakan tiap kalimat, melihat kandidat satu per satu, lalu memilih yang paling cocok (memakai kuota Claude, paling akurat). Cepat: pilih otomatis tanpa kuota.</Muted>
        </>);
      })()}
      {noClaude && !["dara", "kai", "uli"].includes(def.id) && <Muted className="mt-2 text-signal">Perintah claude tidak ditemukan, jadi tugas AI belum bisa dijalankan.</Muted>}
      <H3>Pekerjaan terakhir</H3>
      {logs.length ? (
        <ul className="divide-y divide-line text-sm">{logs.map((l) => (
          <li key={l.name} className="flex justify-between gap-3 py-2"><button className="text-left text-circuit hover:underline" onClick={() => setLog(l.name)}>{l.name.replace(/\.txt$/, "")}</button><span className="shrink-0 text-faint">{when(l.modified)}</span></li>))}
        </ul>
      ) : <Muted>Belum pernah bekerja dari kantor ini.</Muted>}
      <LogView name={log} live={!!log && log === j.log && j.status === "running"} />
    </div>
  );
}

export function FuturePanel({ k }: { k: string }) {
  const f = FUTURE.find((x) => x.key === k)!;
  return (<>
    <p>Meja ini disiapkan untuk agent <strong>{f.name}</strong>: {f.role}. Agent-nya belum dibuat, jadi mejanya masih berisi kardus.</p>
    <Muted className="mt-2">Begitu skill <code>/{f.key}</code> ada di <code>.claude/skills</code>, pos ini menyala di Studio.</Muted>
  </>);
}

/* ---------------------------------------------------------------- video */
const MOVE: Record<string, string> = { disetujui: "Setujui ide", ditolak: "Tolak", ide: "Kembalikan ke ide", naskah: "Kembali ke naskah", suara: "Kembali ke suara", aset: "Rakit ulang (kembali ke aset)", draft: "Batalkan, cek lagi", export: "Setujui video", terbit: "Tandai terbit" };
const STEP: Record<string, string> = { ide: "bg-signal/20 text-signal", disetujui: "bg-circuit/15 text-circuit", naskah: "bg-leaf/15 text-leaf", suara: "bg-[#C792EA]/15 text-[#C792EA]", aset: "bg-[#4FD1C5]/15 text-[#4FD1C5]", draft: "bg-gold/20 text-gold", export: "bg-leaf/25 text-leaf", terbit: "bg-signal text-[#24140A]", ditolak: "text-faint line-through" };

export function VideoCard({ v, ctx, defaultOpen }: { v: Video; ctx: PanelCtx; defaultOpen?: boolean }) {
  const i = v.idea, sc = v.script;
  const words = (sc?.narasi ?? []).reduce((n, x) => n + String(x.kalimat ?? "").split(/\s+/).filter(Boolean).length, 0);
  return (
    <details className="group my-2 rounded-lg border border-line bg-ink-800 open:border-ink-600" open={defaultOpen}>
      <summary className="grid cursor-pointer list-none grid-cols-[auto_1fr_auto] items-center gap-3 px-3 py-2.5 [&::-webkit-details-marker]:hidden">
        <span className={`rounded px-2 py-1 font-pixel text-[11px] leading-none whitespace-nowrap ${STEP[v.status] ?? "bg-ink-700 text-muted"}`}>{v.label}</span>
        <span><strong className="block text-sm leading-snug">{v.judul_kerja}</strong><small className="text-xs text-faint">{when(v.diubah)}</small></span>
        <span className="text-faint transition group-open:rotate-90" aria-hidden>›</span>
      </summary>
      <div className="border-t border-line px-3 pb-3">
        {i?._error && <Muted className="mt-2">{i._error}</Muted>}
        {i && !i._error && (<>
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Ide dari Nova</h4>
          <p className="font-pixel text-lg leading-tight font-bold text-signal">{i.hook_ide}</p>
          <p className="mt-1 text-sm">{i.kenapa_menang}</p>
          <Muted className="mt-1">{i.kategori ?? "–"} · {i.status_teknologi ?? "–"}{i.risiko ? ` · Risiko: ${i.risiko}` : ""}</Muted>
          {!!i.fakta?.length && (<>
            <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Fakta & sumber</h4>
            <ul className="list-disc space-y-1 pl-5 text-sm">{i.fakta.map((f, k) => <li key={k}>{f.klaim} <a className="text-circuit hover:underline" href={f.sumber_url} target="_blank" rel="noopener noreferrer">{f.sumber_nama ?? "sumber"}</a></li>)}</ul>
          </>)}
        </>)}
        {sc && !sc._error && (<>
          <Copy label="Judul" text={sc.judul ?? ""} />
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Teks hook di layar</h4>
          <p className="font-pixel text-lg leading-tight font-bold text-signal">{sc.hook_teks}</p>
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Naskah ({words} kata, ±{Math.round(words / 2.6)} detik)</h4>
          <ol className="list-decimal space-y-1.5 pl-5 text-sm">{(sc.narasi ?? []).map((n, k) => <li key={k}>{n.kalimat}<span className="block text-[13px] text-faint">Visual: {n.visual}</span></li>)}</ol>
          <div className="mt-2"><CopyBtn label="Salin naskah" text={(sc.narasi ?? []).map((n) => n.kalimat).join(" ")} /></div>
          <Copy label="Deskripsi" text={sc.deskripsi ?? ""} />
          <Copy label="Tag" text={(sc.tag ?? []).join(", ")} />
          {sc.catatan_editor && (<><h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Catatan editor</h4><p className="text-sm">{sc.catatan_editor}</p></>)}
        </>)}
        {(v.media.vo || v.media.srt) && (<>
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Suara dari Dara{v.media.durasi != null ? ` (${v.media.durasi.toFixed(1)} detik)` : ""}</h4>
          {v.media.vo && <audio controls preload="none" className="w-full" src={`/api/media?slug=${v.slug}&file=vo.mp3&v=${encodeURIComponent(v.diubah)}`} />}
          {v.media.uji && <Muted>Mode uji: timing perkiraan, belum ada audio.</Muted>}
          <div className="mt-2 flex flex-wrap gap-2">
            {v.media.vo && <a className="text-sm text-circuit hover:underline" href={`/api/media?slug=${v.slug}&file=vo.mp3&unduh=1`}>Unduh vo.mp3</a>}
            {v.media.srt && <a className="text-sm text-circuit hover:underline" href={`/api/media?slug=${v.slug}&file=captions.srt&unduh=1`}>Unduh subtitle (.srt)</a>}
          </div>
        </>)}
        {v.final.ada && (<>
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Video final dari Kai{v.final.durasi ? ` (${v.final.durasi.toFixed(1)} detik)` : ""}{v.final.uji ? " · uji" : ""}</h4>
          <video controls playsInline preload="metadata" className="mx-auto aspect-[9/16] max-h-[520px] rounded-lg border border-line bg-black"
            poster={`/api/media?slug=${v.slug}&file=export/sampul.jpg&v=${encodeURIComponent(v.final.dibuat ?? "")}`}
            src={`/api/media?slug=${v.slug}&file=export/final.mp4&v=${encodeURIComponent(v.final.dibuat ?? "")}`} />
          <div className="mt-2 flex flex-wrap gap-3 text-sm">
            <a className="text-circuit hover:underline" href={`/api/media?slug=${v.slug}&file=export/final.mp4&unduh=1`}>Unduh final.mp4</a>
            <span className="text-faint">{v.final.musik ? `Musik: ${v.final.musik}` : "Tanpa musik (isi folder musik/)"}</span>
          </div>
          {v.status === "draft" && <Muted className="mt-1">Tonton dulu sampai habis. Kalau sudah pas, klik Setujui video. Kalau ada shot yang kurang cocok, ganti di Bima lalu rakit ulang.</Muted>}
        </>)}
        {v.qc && (<>
          <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Pemeriksaan Rara{v.qc.putaran ? ` · ${v.qc.putaran} putaran perbaikan` : ""}</h4>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            {v.qc.skor != null && <span className={`rounded px-2 py-1 font-pixel ${v.qc.skor >= 8 ? "bg-leaf/20 text-leaf" : v.qc.skor >= 6 ? "bg-gold/20 text-gold" : "bg-bad/20 text-bad"}`}>Skor {v.qc.skor}/10</span>}
            {v.qc.porsi && <span className="text-muted">footage {Math.round((v.qc.porsi.footage ?? 0) * 100)}% · AI {Math.round((v.qc.porsi.ai ?? 0) * 100)}% · grafis {Math.round((v.qc.porsi.grafis ?? 0) * 100)}%</span>}
          </div>
          {v.qc.catatan && <p className="mt-1 text-sm">{v.qc.catatan}</p>}
          {[...v.qc.masalah, ...v.qc.saran].map((m, k) => <Muted key={k} className="text-signal">• {m}</Muted>)}
          {v.qc.lembar.map((l) => <a key={l} href={`/api/media?slug=${v.slug}&file=${l}`} target="_blank" rel="noopener noreferrer"><img alt="Frame tiap shot" loading="lazy" className="mt-2 w-full rounded-md border border-line" src={`/api/media?slug=${v.slug}&file=${l}&v=${encodeURIComponent(v.final.dibuat ?? "")}`} /></a>)}
        </>)}
        {v.status === "export" && (<UploadBox v={v} ctx={ctx} />)}
        {v.upload && (<p className="mt-3 text-sm">Sudah diupload (private): <a className="text-circuit hover:underline" href={v.upload.studio} target="_blank" rel="noopener noreferrer">buka di YouTube Studio</a>{v.upload.jadwal ? ` · tayang ${v.upload.jadwal.replace("T", " ")} WIB` : ""}</p>)}
        {v.aset && !v.aset._error && !!v.aset.klip?.length && (() => {
          const kl = v.aset.klip!, n = (j: string) => kl.filter((k) => k.jenis === j).length;
          return (<>
            <h4 className="mt-3 mb-1 font-pixel text-sm text-muted">Visual dari Bima: {kl.length} shot{v.aset.uji ? " · uji" : ""}</h4>
            <Muted>{n("footage")} footage · {n("ai")} gambar AI · {n("grafis")} grafis · rata-rata {((v.aset.durasi ?? 0) / kl.length).toFixed(1)} dtk per shot</Muted>
            {!!v.aset.kurang?.length && <Muted className="text-signal">Belum ada visual untuk kalimat {v.aset.kurang.join(", ")}.</Muted>}
            {v.aset.pakai_ai && <Muted className="text-signal">Ada gambar AI realistis: saat upload, centang &quot;konten diubah/sintetis&quot; di YouTube Studio.</Muted>}
            <ul className="mt-2 grid grid-cols-4 gap-1.5 sm:grid-cols-5">{kl.map((k) => (
              <li key={k.file} className="overflow-hidden rounded-md border border-line bg-ink-950 text-[11px]" title={k.kalimat}>
                <div className="relative aspect-[9/16] bg-ink-900">
                  {k.ada ? <video className="size-full object-cover" src={`/api/media?slug=${v.slug}&file=aset/${k.file}`} muted loop playsInline preload="metadata" onMouseEnter={(e) => e.currentTarget.play().catch(() => {})} onMouseLeave={(e) => e.currentTarget.pause()} />
                    : <span className="grid size-full place-items-center p-1 text-center text-faint">file hilang</span>}
                  <b className="absolute top-1 left-1 rounded bg-ink-950/80 px-1">{k.i + 1}{"abc"[k.potong]}</b>
                  <b className={`absolute right-1 bottom-1 rounded px-1 ${k.jenis === "ai" ? "bg-[#C792EA] text-[#1B1030]" : k.jenis === "grafis" ? "bg-signal text-[#24140A]" : "bg-ink-950/80"}`}>{k.jenis === "footage" ? k.sumber : k.jenis}</b>
                </div>
                {k.url_halaman ? <a className="block truncate px-1 py-0.5 text-circuit hover:underline" href={k.url_halaman} target="_blank" rel="noopener noreferrer">{k.durasi.toFixed(1)} dtk · {k.pembuat || k.sumber}</a>
                  : <span className="block truncate px-1 py-0.5 text-faint">{k.durasi.toFixed(1)} dtk</span>}
              </li>))}</ul>
            {!!v.aset.kredit && <Copy label="Kredit untuk deskripsi" text={v.aset.kredit} />}
            <Muted className="mt-1">Arahkan kursor ke shot untuk memutar. Ganti visual satu kalimat: <code>python agents/aset/cari_aset.py unduh {v.slug} --ulang &lt;nomor&gt;</code></Muted>
          </>);
        })()}
        {!i && !sc && <Muted className="mt-2">Belum ada file untuk video ini.</Muted>}
        <div className="mt-3 flex flex-wrap gap-2">
          {(v.status === "naskah" || v.status === "suara") && <Btn size="sm" tone="primary" disabled={busy(ctx.state) || !ctx.state.health.edgeTts} onClick={() => ctx.run("suara", v.slug)}>{v.media.vo ? "Buat ulang suara" : "Buat suara (gratis)"}</Btn>}
          {(v.status === "suara" || v.status === "aset") && <Btn size="sm" tone="primary" disabled={busy(ctx.state) || !ctx.state.health.claude || !ctx.state.health.stockKey || !ctx.state.health.ffmpeg} onClick={() => ctx.run("aset", v.slug)}>{v.aset?.klip?.length ? "Siapkan ulang visual" : "Siapkan visual dengan Bima"}</Btn>}
          {v.status === "draft" && <Btn size="sm" disabled={busy(ctx.state) || !ctx.state.health.claude} onClick={() => ctx.run("qc", v.slug)}>Periksa dengan Rara</Btn>}
          {(v.status === "aset" || v.status === "draft") && <Btn size="sm" tone="primary" disabled={busy(ctx.state) || !ctx.state.health.ffmpeg} onClick={() => ctx.run("editor", v.slug)}>{v.final.ada ? "Rakit ulang dengan Kai" : "Rakit video dengan Kai"}</Btn>}
          {v.status === "disetujui" && <Btn size="sm" tone="primary" disabled={busy(ctx.state) || !ctx.state.health.claude} onClick={() => ctx.run("penulis", v.slug)}>Tulis naskah dengan Raka</Btn>}
          <Btn size="sm" tone="danger" className="ml-auto" onClick={() => ctx.hapus("video", v.slug, `Video "${v.judul_kerja}" beserta ide, naskah, suara, klip, dan video finalnya.`)}>Hapus video</Btn>
          {v.moves.map((m) => <Btn key={m} size="sm" tone={(m === "disetujui" && v.status === "ide") || (m === "export" && v.status === "draft") ? "primary" : "ghost"} onClick={() => ctx.move(v.slug, m)}>{(v.status === "naskah" || v.status === "suara") && m === "disetujui" ? "Minta tulis ulang" : MOVE[m]}</Btn>)}
        </div>
      </div>
    </details>
  );
}

export function QueuePanel({ ctx }: { ctx: PanelCtx }) {
  const order = ["ide", "draft", "export", "aset", "suara", "naskah", "disetujui", "export", "terbit", "ditolak"];
  const vids = [...ctx.state.videos].sort((a, b) => order.indexOf(a.status) - order.indexOf(b.status));
  if (!vids.length) return (<><Muted>Antrean masih kosong. Minta Nova mencari ide dulu.</Muted><Btn className="mt-3" tone="primary" onClick={() => ctx.open("agent:nova")}>Ke meja Nova</Btn></>);
  return <>{vids.map((v) => <VideoCard key={v.slug} v={v} ctx={ctx} />)}</>;
}

export function FounderPanel({ ctx }: { ctx: PanelCtx }) {
  const { state, target } = ctx, v = state.videos, ideas = v.filter((x) => x.status === "ide"), ready = v.filter((x) => ["disetujui", "naskah", "suara", "aset"].includes(x.status)), cek = v.filter((x) => x.status === "draft"), up = v.filter((x) => x.status === "export");
  const wk = state.week.published, lu = state.snapshot?.videos.reduce((a, x) => (x.published > a ? x.published : a), ""), gap = lu ? daysSince(lu) : null;
  return (<>
    <H3>Target minggu ini</H3>
    <p className="text-sm">{wk} dari {target} video terbit sejak Senin.</p>
    <div className="mt-2 h-3 overflow-hidden rounded-sm border border-line bg-ink-950" role="progressbar" aria-label="Target terbit minggu ini" aria-valuemin={0} aria-valuemax={target} aria-valuenow={wk}>
      <i className="block h-full bg-[repeating-linear-gradient(90deg,var(--color-leaf)_0_8px,#5BBE86_8px_10px)]" style={{ width: `${Math.min(100, (wk / target) * 100)}%` }} />
    </div>
    <div className="mt-2.5 flex flex-wrap items-center gap-3 text-sm">
      <label className="text-muted" htmlFor="tgt">Target per minggu</label>
      <select id="tgt" value={target} onChange={(e) => ctx.setTarget(+e.target.value)} className="rounded-lg border border-line bg-ink-950 px-2 py-1.5">{[1, 2, 3, 4, 5, 7, 10, 14].map((n) => <option key={n}>{n}</option>)}</select>
      {gap != null && <span className={gap > 7 ? "text-signal" : "text-muted"}>Upload terakhir {gap} hari lalu.</span>}
    </div>
    <H3>Perlu keputusanmu ({ideas.length})</H3>
    {ideas.length ? ideas.map((x) => <VideoCard key={x.slug} v={x} ctx={ctx} />) : <Muted>Tidak ada ide yang menunggu.</Muted>}
    <H3>Video jadi, perlu kamu tonton ({cek.length})</H3>
    {cek.length ? cek.map((x) => <VideoCard key={x.slug} v={x} ctx={ctx} />) : <Muted>Belum ada video yang selesai dirakit.</Muted>}
    <H3>Siap upload ({up.length})</H3>
    {up.length ? up.map((x) => <VideoCard key={x.slug} v={x} ctx={ctx} />) : <Muted>Belum ada video yang disetujui.</Muted>}
    <H3>Sedang diproses ({ready.length})</H3>
    {ready.length ? ready.map((x) => <VideoCard key={x.slug} v={x} ctx={ctx} />) : <Muted>Tidak ada.</Muted>}
    <H3>Langkah cepat</H3>
    <div className="flex flex-wrap gap-2"><Btn onClick={() => ctx.open("agent:nova")}>Minta ide ke Nova</Btn><Btn onClick={() => ctx.open("reports")}>Laporan Steve</Btn><Btn onClick={() => ctx.open("health")}>Cek sistem</Btn></div>
  </>);
}

/* ---------------------------------------------------------------- analitik */
export function AnalyticsPanel({ ctx }: { ctx: PanelCtx }) {
  const s = ctx.state.snapshot;
  const [filter, setFilter] = useState<"all" | "menang" | "rata-rata" | "lemah">("all");
  const [sort, setSort] = useState<{ k: "title" | "views" | "vs_median" | "views_per_day" | "published"; d: 1 | -1 }>({ k: "published", d: -1 });
  const rows = useMemo(() => !s ? [] : s.videos.filter((v) => filter === "all" || v.tier === filter).sort((a, b) => ((a[sort.k] ?? 0) > (b[sort.k] ?? 0) ? 1 : (a[sort.k] ?? 0) < (b[sort.k] ?? 0) ? -1 : 0) * sort.d), [s, filter, sort]);
  if (!s?.videos.length) return (<><Muted>Belum ada data. Buka meja Steve lalu klik Ambil data terbaru.</Muted><Btn className="mt-3" onClick={() => ctx.open("agent:steve")}>Ke meja Steve</Btn></>);
  const vids = [...s.videos].sort((a, b) => a.published.localeCompare(b.published)), W = 480, H = 220, pl = 34, pb = 22, pt = 8, n = vids.length;
  const max = Math.max(...vids.map((v) => v.views)) * 1.08, med = s.summary.median_views, step = (W - pl) / n, bw = Math.max(3, Math.min(22, step * 0.7)), y = (v: number) => pt + (H - pt - pb) * (1 - v / max);
  const col = { menang: "#FF9A4D", "rata-rata": "#47B5FF", lemah: "#5A7393" } as const;
  const th = (k: typeof sort.k, l: string, num = false) => (
    <th className={`border-b border-line px-1.5 py-1.5 font-bold whitespace-nowrap text-muted ${num ? "text-right" : "text-left"}`} aria-sort={sort.k === k ? (sort.d > 0 ? "ascending" : "descending") : "none"}>
      <button onClick={() => setSort({ k, d: sort.k === k ? (-sort.d as 1 | -1) : k === "title" ? 1 : -1 })}>{l}{sort.k === k ? (sort.d > 0 ? " ↑" : " ↓") : ""}</button></th>);
  return (<>
    <Muted>{fmt(s.summary.videos)} video, median {fmt(Math.round(med))} views. Data per {s.snapshot_date}. Klik batang untuk membuka videonya.</Muted>
    <div className="mt-2 rounded-lg border border-line bg-ink-800 p-2.5">
      <div className="mb-1.5 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted">
        <span><i className="mr-1.5 inline-block size-2.5 rounded-sm bg-signal align-[-1px]" />Menang ≥ 1,5× median</span>
        <span><i className="mr-1.5 inline-block size-2.5 rounded-sm bg-circuit align-[-1px]" />Rata-rata</span>
        <span><i className="mr-1.5 inline-block size-2.5 rounded-sm bg-[#5A7393] align-[-1px]" />Lemah ≤ 0,75×</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full" role="img" aria-label={`Views ${n} Shorts, median ${Math.round(med)}`}>
        {[0, max / 2].map((t) => <g key={t}><line x1={pl} x2={W} y1={y(t)} y2={y(t)} stroke="#2A4868" /><text x={pl - 5} y={y(t) + 4} fill="#66809D" fontSize="10" textAnchor="end">{short(t)}</text></g>)}
        {vids.map((v, i) => <a key={v.id} href={v.url} target="_blank" rel="noopener noreferrer"><rect x={pl + i * step + (step - bw) / 2} y={y(v.views)} width={bw} height={H - pb - y(v.views)} rx="2" fill={col[v.tier]}><title>{`${cleanTitle(v.title)}: ${fmt(v.views)} views`}</title></rect></a>)}
        <line x1={pl} x2={W} y1={y(med)} y2={y(med)} stroke="#ECF2F8" strokeDasharray="4 4" />
        <text x={W - 2} y={y(med) - 4} fill="#ECF2F8" fontSize="10" textAnchor="end">median {short(med)}</text>
        <text x={pl} y={H - 6} fill="#66809D" fontSize="10">{vids[0].published}</text><text x={W} y={H - 6} fill="#66809D" fontSize="10" textAnchor="end">{vids[n - 1].published}</text>
      </svg>
    </div>
    <H3>Semua video</H3>
    <div className="mb-2 flex flex-wrap gap-1.5" role="group" aria-label="Saring video">
      {([["all", "Semua"], ["menang", "Menang"], ["rata-rata", "Rata-rata"], ["lemah", "Lemah"]] as const).map(([k, l]) => (
        <button key={k} aria-pressed={filter === k} onClick={() => setFilter(k)} className={`rounded-md border px-2.5 py-1 text-[13px] ${filter === k ? "border-circuit text-ink-50" : "border-line text-muted"}`}>{l}</button>))}
    </div>
    <table className="w-full border-collapse text-[13px]">
      <thead><tr>{th("title", "Video")}{th("views", "Views", true)}{th("vs_median", "× med", true)}{th("views_per_day", "/hari", true)}{th("published", "Terbit", true)}</tr></thead>
      <tbody>{rows.map((v) => (
        <tr key={v.id} className="border-b border-line align-top">
          <td className="px-1.5 py-2"><a className="hover:text-circuit" href={v.url} target="_blank" rel="noopener noreferrer">{cleanTitle(v.title)}</a><br />
            <span className={`mt-1 inline-block rounded px-1.5 py-0.5 font-pixel text-[11px] ${v.tier === "menang" ? "bg-signal/20 text-signal" : v.tier === "lemah" ? "bg-[#5A7393]/30 text-[#B9C7D8]" : "bg-circuit/15 text-circuit"}`}>{v.tier}</span></td>
          <td className="px-1.5 py-2 text-right tabular-nums">{fmt(v.views)}</td><td className="px-1.5 py-2 text-right tabular-nums">{dec(v.vs_median)}</td>
          <td className="px-1.5 py-2 text-right tabular-nums">{fmt(v.views_per_day)}</td><td className="px-1.5 py-2 text-right tabular-nums">{v.published.slice(5)}</td>
        </tr>))}</tbody>
    </table>
  </>);
}

/* ---------------------------------------------------------------- laporan, bible, log, sistem */
export function ReportsPanel({ ctx }: { ctx: PanelCtx }) {
  const list = ctx.state.reports, [name, setName] = useState(list[0]?.name ?? ""), [html, setHtml] = useState("Memuat…");
  useEffect(() => { if (name) api<{ text: string }>(`/api/report?name=${encodeURIComponent(name)}`).then((r) => setHtml(md(r.text))).catch((e) => setHtml(String(e.message))); }, [name]);
  if (!list.length) return (<><Muted>Belum ada laporan. Buka meja Steve lalu klik Jalankan Steve.</Muted><Btn className="mt-3" tone="primary" onClick={() => ctx.open("agent:steve")}>Ke meja Steve</Btn></>);
  return (<>
    <div className="flex items-center gap-2 text-sm"><label className="text-muted" htmlFor="rep">Minggu</label>
      <select id="rep" value={name} onChange={(e) => setName(e.target.value)} className="rounded-lg border border-line bg-ink-950 px-2 py-1.5">{list.map((r) => <option key={r.name} value={r.name}>{r.name.replace(".md", "")}</option>)}</select></div>
    <div className="prose-studio mt-3" dangerouslySetInnerHTML={{ __html: html }} />
  </>);
}

export function BiblePanel() {
  const [text, setText] = useState<string | null>(null), [msg, setMsg] = useState("");
  useEffect(() => { api<{ text: string }>("/api/bible").then((r) => setText(r.text)).catch((e) => setMsg(e.message)); }, []);
  return (<>
    <Muted>Aturan yang dibaca semua agent. Versi lama tersimpan otomatis di <code>bible/.history</code>.</Muted>
    <textarea value={text ?? "Memuat…"} onChange={(e) => setText(e.target.value)} disabled={text === null} spellCheck={false} aria-label="Isi channel bible"
      className="mt-2 min-h-[60vh] w-full resize-y rounded-lg border border-line bg-ink-950 p-3 font-mono text-[13px] leading-relaxed" />
    <div className="mt-2.5 flex items-center gap-3"><Btn tone="primary" disabled={text === null} onClick={async () => { try { setMsg((await api("/api/bible", { text })).message); } catch (e) { setMsg((e as Error).message); } }}>Simpan bible</Btn><span className="text-sm text-muted" role="status">{msg}</span></div>
  </>);
}

const EVT: Record<string, string> = { disetujui: "Zona menyetujui", ditolak: "Zona menolak", naskah: "Raka menyelesaikan naskah", suara: "Suara siap:", aset: "Aset siap:", draft: "Draft CapCut siap:", export: "Di-export:", terbit: "Terbit:", ide: "Dikembalikan ke ide:" };
const JOBN: Record<string, string> = { steve: "Steve membuat laporan", fetch: "Steve mengambil data", check: "Cek koneksi YouTube", ide: "Nova mencari ide", penulis: "Raka menulis naskah" };
export function ActivityPanel({ ctx }: { ctx: PanelCtx }) {
  const [log, setLog] = useState<string | null>(null);
  const ev = [
    ...ctx.state.activity.map((r) => ({ t: r.waktu, key: `a${r.slug}${r.waktu}${r.ke}`, node: <span>{r.dari === null ? "Nova mengusulkan ide" : EVT[r.ke] ?? r.ke} <strong>{r.judul_kerja ?? r.slug}</strong></span> })),
    ...ctx.state.logs.map((l) => ({ t: l.modified, key: `l${l.name}`, node: <span>{JOBN[l.name.split("-")[0]] ?? l.name} · <button className="text-circuit hover:underline" onClick={() => setLog(l.name)}>lihat log</button></span> })),
  ].sort((a, b) => b.t.localeCompare(a.t)).slice(0, 40);
  if (!ev.length) return <Muted>Kantor masih sepi. Aktivitas agent dan keputusanmu akan muncul di sini.</Muted>;
  return (<>
    <ul className="divide-y divide-line text-sm">{ev.map((e) => <li key={e.key} className="flex justify-between gap-3 py-2">{e.node}<span className="shrink-0 text-faint">{when(e.t)}</span></li>)}</ul>
    <LogView name={log} />
  </>);
}

export function HealthPanel({ ctx }: { ctx: PanelCtx }) {
  const h = ctx.state.health;
  const rows = [
    { ok: h.python, name: "Python", fix: "Install Python 3.11+ dari python.org dan centang 'Add python.exe to PATH'." , good: `Ditemukan (${h.pythonCmd}).` },
    { ok: h.claude, name: "Claude Code CLI", fix: "Install dengan: irm https://claude.ai/install.ps1 | iex, lalu login dengan akun Claude Pro.", good: "Ditemukan. Pastikan login dengan akun langganan (cek /status)." },
    { ok: h.env, name: "File .env", fix: "Salin .env.example menjadi .env lalu isi YOUTUBE_API_KEY.", good: "Ada." },
    { ok: h.edgeTts, name: "edge-tts (suara Dara)", fix: "Jalankan sekali dari folder project: python -m pip install -r requirements.txt", good: "Terpasang." },
    { ok: h.ffmpeg, name: "ffmpeg (Bima)", fix: "Jalankan di PowerShell: winget install Gyan.FFmpeg, lalu tutup dan buka lagi start_studio.bat.", good: "Ditemukan." },
    { ok: h.stockKey, name: "API key sumber klip (Bima)", fix: "Login gratis di pixabay.com, buka pixabay.com/api/docs, salin key-nya ke PIXABAY_API_KEY= di .env. (Pexels sedang menutup pendaftaran API key baru.)", good: "Ada di .env." },
    { ok: h.ytdlp, name: "yt-dlp (footage YouTube CC)", fix: "python -m pip install -r requirements.txt, lalu winget install DenoLand.Deno (dibutuhkan yt-dlp untuk YouTube).", good: "Terpasang." },
    { ok: h.aiKey, name: "Gambar AI gratis (Cloudflare)", fix: "Isi CLOUDFLARE_ACCOUNT_ID dan CLOUDFLARE_API_TOKEN di .env (lihat SETUP.md).", good: "Ada di .env." },
    { ok: h.google && h.ytClient && h.ytLogin, name: "Upload & analitik YouTube (Uli, Steve v2)", fix: !h.google ? "python -m pip install -r requirements.txt" : !h.ytClient ? "Buat OAuth client (Desktop) di Google Cloud, simpan sebagai rahasia/client_secret.json (lihat SETUP.md)." : "Buka meja Uli lalu klik Hubungkan YouTube.", good: "Terhubung." },
    { ok: !!ctx.state.snapshot, name: "Data channel", fix: "Buka meja Steve lalu klik Ambil data terbaru.", good: `Data per ${ctx.state.snapshot?.snapshot_date}.` },
  ];
  return (<>
    <ul className="space-y-2">{rows.map((r) => (
      <li key={r.name} className="rounded-lg border border-line bg-ink-800 p-3 text-sm">
        <div className="flex items-center gap-2 font-pixel"><span className={`size-2.5 rounded-sm ${r.ok ? "bg-leaf" : "bg-bad"}`} aria-hidden />{r.name}<span className="sr-only">{r.ok ? "beres" : "bermasalah"}</span></div>
        <p className="mt-1 text-muted">{r.ok ? r.good : r.fix}</p>
      </li>))}</ul>
    <div className="mt-3"><Btn disabled={busy(ctx.state) || !h.env} onClick={() => ctx.run("check")}>Uji koneksi YouTube</Btn></div>
  </>);
}

/* ---------------------------------------------------------------- buat video */
const TAHAP_AGENT: Record<string, string> = { steve: "steve", nova: "nova", raka: "raka", dara: "dara", bima: "bima", kai: "kai", rara: "rara" };
const PROD_TONE = { berjalan: "running", selesai: "ok", gagal: "error", terhenti: "stopped" } as const;
const PROD_TXT = { berjalan: "Sedang dibuat", selesai: "Video jadi", gagal: "Gagal", terhenti: "Terhenti" } as const;
const TEMA = ["makanan", "pakaian", "kesehatan", "rumah", "HP & gadget", "game", "transportasi", "energi"];

function durasi(a: string | null, b: string | null): string {
  if (!a) return "";
  const s = Math.max(0, Math.round(((b ? Date.parse(b) : Date.now()) - Date.parse(a)) / 1000));
  return s < 60 ? `${s} dtk` : `${Math.floor(s / 60)} mnt ${s % 60} dtk`;
}

function Stepper({ p }: { p: Produksi }) {
  return (
    <ol className="mt-2 space-y-1.5">{p.tahap.map((t) => {
      const def = TAHAP_AGENT[t.kunci] ? TEAM.find((x) => x.id === TAHAP_AGENT[t.kunci]) : null;
      const live = t.status === "jalan" && p.status === "berjalan";
      const dot = t.status === "ok" ? "bg-leaf" : t.status === "gagal" ? "bg-bad" : live ? "bg-signal animate-pulse motion-reduce:animate-none" : "bg-ink-600";
      return (
        <li key={t.kunci} className={`flex items-start gap-2.5 rounded-lg border px-3 py-2 text-sm ${live ? "border-signal/50 bg-signal/5" : "border-line bg-ink-800"}`}>
          <span className={`mt-1.5 size-2.5 shrink-0 rounded-sm ${dot}`} aria-hidden />
          <span className="min-w-0 flex-1">
            <span className="flex flex-wrap items-baseline justify-between gap-x-2">
              <strong style={def ? { color: def.color } : undefined}>{t.nama}</strong>
              <small className="text-faint">{t.status === "menunggu" ? "menunggu" : live ? `berjalan ${durasi(t.mulai, null)}` : durasi(t.mulai, t.selesai)}</small>
            </span>
            {t.catatan && <span className={`block text-[13px] ${t.status === "gagal" ? "text-bad" : "text-muted"}`}>{t.catatan}</span>}
          </span>
        </li>);
    })}</ol>
  );
}

function UploadBox({ v, ctx }: { v: Video; ctx: PanelCtx }) {
  const [jadwal, setJadwal] = useState("");
  const h = ctx.state.health;
  if (v.upload) return null;
  const siap = h.google && h.ytClient && h.ytLogin;
  return (
    <div className="mt-3 rounded-lg border border-[#82AAFF]/40 bg-[#82AAFF]/5 p-3 text-sm">
      <strong className="font-pixel">Upload ke YouTube (private)</strong>
      <label className="mt-2 flex flex-wrap items-center gap-2"><span className="text-muted">Jadwal tayang (opsional, WIB)</span>
        <input type="datetime-local" value={jadwal} onChange={(e) => setJadwal(e.target.value)} className="rounded-md border border-line bg-ink-950 px-2 py-1" /></label>
      <div className="mt-2 flex flex-wrap gap-2">
        <Btn size="sm" tone="primary" disabled={busy(ctx.state) || !siap} onClick={() => ctx.run("upload", `${v.slug}${jadwal ? `|${jadwal.slice(0, 16)}` : ""}`)}>Upload dengan Uli</Btn>
        {!siap && <Btn size="sm" onClick={() => ctx.open("agent:uli")}>Siapkan koneksi YouTube</Btn>}
      </div>
      {v.aset?.pakai_ai && <Muted className="mt-1">Label &quot;konten sintetis&quot; dicentang otomatis karena ada gambar AI.</Muted>}
    </div>
  );
}

export function ProduksiPanel({ ctx }: { ctx: PanelCtx }) {
  const { state } = ctx;
  const [teks, setTeks] = useState("");
  const [suara, setSuara] = useState<"pria" | "wanita">("pria");
  const [visual, setVisual] = useState<"teliti" | "cepat">("teliti");
  const [err, setErr] = useState("");
  const list = state.produksi;
  const cur = list[0]?.status === "berjalan" ? list[0] : null;
  const h = state.health;
  const kurang = [!h.python && "Python", !h.claude && "Claude Code", !h.ffmpeg && "ffmpeg", !h.edgeTts && "edge-tts"].filter(Boolean);
  const vidOf = (p: Produksi) => (p.slug ? state.videos.find((v) => v.slug === p.slug) : undefined);
  const go = async () => {
    setErr("");
    try { await api("/api/antrean", { aksi: "tambah", teks, suara, visual }); setTeks(""); } catch (e) { setErr((e as Error).message); }
    ctx.open("produksi");
  };
  const antre = state.antrean;
  return (<>
    {cur && (<>
      <H3>Sedang dibuat</H3>
      <p className="text-[15px]">&ldquo;{cur.permintaan}&rdquo;</p>
      <Muted>Mulai {when(cur.dibuat)} · {durasi(cur.dibuat, null)} · suara {cur.opsi.suara}, visual {cur.opsi.visual}</Muted>
      <Stepper p={cur} />
      <div className="mt-3 flex gap-2"><Btn size="sm" tone="danger" onClick={() => ctx.stop()}>Hentikan produksi</Btn><Btn size="sm" onClick={() => ctx.open("activity")}>Log kantor</Btn></div>
      <LogView name={state.job.job === "produksi" ? state.job.log : null} live={state.job.status === "running"} />
    </>)}
    {antre.length > 0 && (<>
      <H3>Antrean ({antre.length})</H3>
      <ol className="divide-y divide-line">{antre.map((q, k) => (
        <li key={q.id} className="flex items-center justify-between gap-2 py-2 text-sm"><span>{k + 1}. {q.teks ? <>&ldquo;{q.teks}&rdquo;</> : "Topik dipilih tim"} <small className="text-faint">{q.suara} · {q.visual}</small></span>
          <Btn size="sm" tone="ghost" onClick={async () => { await api("/api/antrean", { aksi: "hapus", id: q.id }).catch(() => {}); ctx.open("produksi"); }}>Batal</Btn></li>))}
      </ol>
    </>)}
    {(<>
      {cur && <H3>Tambah permintaan</H3>}
      <p className="text-[15px]">Tim yang memilih topiknya: Steve memperbarui daftar video channel, lalu Nova mencari teknologi nyata yang paling berpotensi menang dan <strong>belum pernah dibahas</strong> di channel.</p>
      <label htmlFor="minta" className="mt-3 block font-pixel text-sm text-muted">Arahan tema (opsional)</label>
      <textarea id="minta" value={teks} onChange={(e) => setTeks(e.target.value)} maxLength={200} rows={2}
        placeholder="Kosongkan saja supaya tim bebas memilih. Atau beri arah, misalnya: kesehatan"
        className="mt-1.5 w-full resize-none rounded-lg border border-line bg-ink-950 px-3 py-2.5 text-[15px] placeholder:text-faint focus:border-signal focus:outline-none" />
      <div className="mt-1.5 flex flex-wrap gap-1.5">{TEMA.map((x) => (
        <button key={x} onClick={() => setTeks(x)} className="rounded-full border border-line px-2.5 py-1 text-xs text-muted hover:border-signal hover:text-signal">{x}</button>))}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <label className="flex flex-col gap-1"><span className="text-muted">Suara</span>
          <select value={suara} onChange={(e) => setSuara(e.target.value as "pria" | "wanita")} className="rounded-lg border border-line bg-ink-950 px-2 py-2">
            <option value="pria">Ardi (pria)</option><option value="wanita">Gadis (wanita)</option></select></label>
        <label className="flex flex-col gap-1"><span className="text-muted">Visual</span>
          <select value={visual} onChange={(e) => setVisual(e.target.value as "teliti" | "cepat")} className="rounded-lg border border-line bg-ink-950 px-2 py-2">
            <option value="teliti">Teliti (Bima memilih satu per satu)</option><option value="cepat">Cepat (pilih otomatis)</option></select></label>
      </div>
      <Btn tone="primary" className="mt-3 w-full justify-center py-3 text-base" disabled={kurang.length > 0} onClick={go}>{busy(state) ? "Tambah ke antrean" : teks.trim() ? "Buat video dengan arahan ini" : "Buat video (tim pilih topik)"}</Btn>
      {kurang.length > 0 && <Muted className="mt-2 text-signal">Belum siap: {kurang.join(", ")}. <button className="underline" onClick={() => ctx.open("health")}>Cek sistem</button></Muted>}
      {err && <Muted className="mt-2 text-bad">{err}</Muted>}
      {busy(state) && <Muted className="mt-2">Kantor sedang bekerja; permintaanmu masuk antrean dan dikerjakan berurutan otomatis (bisa ditinggal tidur).</Muted>}
      <Muted className="mt-2">Nova memilih 1 topik baru (dicek tidak mirip video lama, wajib 2 sumber), lalu Raka, Dara, Bima, dan Kai bekerja berurutan, dan Rara memeriksa serta memperbaiki shot yang jelek. Perkiraan 15–35 menit; memakai kuota Claude Pro untuk ide, naskah, dan visual teliti. Hasilnya muncul di sini dan di Galeri. Kamu tetap menonton dan menyetujui video sebelum di-upload.</Muted>
    </>)}


    {list.filter((p) => p !== cur).length > 0 && <H3>Permintaan sebelumnya</H3>}
    {list.filter((p) => p !== cur).map((p, i) => {
      const v = vidOf(p);
      return (
        <section key={p.id} className="mb-3 rounded-lg border border-line bg-ink-800 p-3">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <p className="text-[15px]">&ldquo;{p.permintaan}&rdquo;</p>
            <Pill tone={PROD_TONE[p.status]}>{PROD_TXT[p.status]}</Pill>
          </div>
          <Muted>{when(p.dibuat)}{p.selesai ? ` · ${durasi(p.dibuat, p.selesai)}` : ""}{p.opsi.uji ? " · uji" : ""}</Muted>
          <div className="mt-1 flex flex-wrap gap-2">
            <Btn size="sm" tone="ghost" onClick={() => ctx.hapus("produksi", p.id, `Catatan permintaan "${p.permintaan}" (videonya tetap ada).`)}>Hapus catatan</Btn>
            {v && <Btn size="sm" tone="danger" onClick={() => ctx.hapus("video", v.slug, `Video "${v.judul_kerja}" dan semua filenya.`)}>Hapus videonya</Btn>}
          </div>
          {p.status !== "selesai" && <><Stepper p={p} />{p.pesan && <Muted className="mt-1">{p.pesan}</Muted>}</>}
          {v && <VideoCard v={v} ctx={ctx} defaultOpen={i === 0 && p.status === "selesai"} />}
        </section>);
    })}
  </>);
}

/* ---------------------------------------------------------------- galeri */
export function GaleriPanel({ ctx }: { ctx: PanelCtx }) {
  const vids = ctx.state.videos.filter((v) => v.final.ada).sort((a, b) => (b.final.dibuat ?? "").localeCompare(a.final.dibuat ?? ""));
  const [sel, setSel] = useState<string | null>(null);
  const chosen = vids.find((v) => v.slug === sel);
  if (!vids.length) return (<><Muted>Belum ada video jadi. Klik Buat video untuk membuat yang pertama.</Muted><Btn className="mt-3" tone="primary" onClick={() => ctx.open("produksi")}>Buat video</Btn></>);
  return (<>
    {chosen && (<><Btn size="sm" onClick={() => setSel(null)}>← Semua video</Btn><VideoCard v={chosen} ctx={ctx} defaultOpen /></>)}
    {!chosen && (
      <ul className="grid grid-cols-2 gap-3 sm:grid-cols-3">{vids.map((v) => (
        <li key={v.slug} className="overflow-hidden rounded-lg border border-line bg-ink-800">
          <video className="aspect-[9/16] w-full bg-black object-cover" controls playsInline preload="none"
            poster={`/api/media?slug=${v.slug}&file=export/sampul.jpg&v=${encodeURIComponent(v.final.dibuat ?? "")}`}
            src={`/api/media?slug=${v.slug}&file=export/final.mp4&v=${encodeURIComponent(v.final.dibuat ?? "")}`} />
          <button onClick={() => setSel(v.slug)} className="block w-full px-2.5 py-2 text-left hover:bg-ink-700">
            <strong className="line-clamp-2 text-[13px] leading-snug">{v.judul_kerja}</strong>
            <small className="text-faint">{v.label} · {v.final.durasi?.toFixed(0)} dtk</small>
          </button>
          <button onClick={() => ctx.hapus("video", v.slug, `Video "${v.judul_kerja}" dan semua filenya.`)} className="block w-full border-t border-line px-2.5 py-1.5 text-left text-xs text-bad hover:bg-bad/10">Hapus</button>
        </li>))}
      </ul>)}
  </>);
}

/* ---------------------------------------------------------------- kelola hasil */
type Kelola = { videos: { slug: string; bytes: number }[]; logs: { name: string; modified: string; bytes: number }[]; laporan: { name: string; modified: string }[]; cache: number; total: number };
const mb = (b: number) => (b >= 1e9 ? `${(b / 1e9).toFixed(1)} GB` : b >= 1e6 ? `${(b / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`);

export function KelolaPanel({ ctx }: { ctx: PanelCtx }) {
  const [d, setD] = useState<Kelola | null>(null);
  const [lapor, setLapor] = useState(false);
  useEffect(() => { api<Kelola>("/api/kelola").then(setD).catch(() => setD(null)); }, [ctx.kelolaTick, ctx.state.videos.length, ctx.state.produksi.length]);
  if (!d) return <Muted>Memuat…</Muted>;
  const judul = (slug: string) => ctx.state.videos.find((v) => v.slug === slug)?.judul_kerja ?? slug;
  const row = "flex items-center justify-between gap-3 py-2 text-sm";
  return (<>
    <p className="text-[15px]">Semua hasil karyawanmu memakai <strong>{mb(d.total)}</strong>.</p>
    <Muted>Hapus permanen, tidak bisa dibatalkan. Bible, gaya edit, musik, dan rekaman milik-saya tidak pernah ikut terhapus.</Muted>

    <H3>Video ({d.videos.length})</H3>
    {d.videos.length ? <ul className="divide-y divide-line">{d.videos.map((v) => (
      <li key={v.slug} className={row}><span className="min-w-0"><span className="block truncate">{judul(v.slug)}</span><small className="text-faint">{ctx.state.videos.find((x) => x.slug === v.slug)?.label ?? "tanpa catatan"} · {mb(v.bytes)}</small></span>
        <Btn size="sm" tone="danger" onClick={() => ctx.hapus("video", v.slug, `Video "${judul(v.slug)}" dan semua filenya (${mb(v.bytes)}).`)}>Hapus</Btn></li>))}</ul> : <Muted>Tidak ada.</Muted>}

    <H3>Catatan produksi ({ctx.state.produksi.length})</H3>
    {ctx.state.produksi.length ? <ul className="divide-y divide-line">{ctx.state.produksi.map((p) => (
      <li key={p.id} className={row}><span className="min-w-0 truncate">&ldquo;{p.permintaan}&rdquo; <small className="text-faint">{when(p.dibuat)}</small></span>
        <Btn size="sm" tone="ghost" disabled={p.status === "berjalan"} onClick={() => ctx.hapus("produksi", p.id, `Catatan permintaan "${p.permintaan}".`)}>Hapus</Btn></li>))}</ul> : <Muted>Tidak ada.</Muted>}

    <H3>Laporan Steve ({d.laporan.length})</H3>
    {d.laporan.length ? <ul className="divide-y divide-line">{d.laporan.map((r) => (
      <li key={r.name} className={row}><span>{r.name.replace(/\.md$/, "")} <small className="text-faint">{when(r.modified)}</small></span>
        <Btn size="sm" tone="ghost" onClick={() => ctx.hapus("laporan", r.name, `Laporan Steve ${r.name}.`)}>Hapus</Btn></li>))}</ul> : <Muted>Tidak ada.</Muted>}

    <H3>Log ({d.logs.length}) · Cache {mb(d.cache)}</H3>
    <div className="flex flex-wrap gap-2">
      <Btn size="sm" disabled={!d.logs.length} onClick={() => ctx.hapus("log", "*", `Semua ${d.logs.length} log kerja.`)}>Hapus semua log</Btn>
      <Btn size="sm" disabled={!d.cache} onClick={() => ctx.hapus("cache", "", `Cache unduhan Bima (${mb(d.cache)}). Video yang sudah jadi tidak terpengaruh.`)}>Kosongkan cache</Btn>
    </div>

    <H3>Mulai dari nol</H3>
    <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={lapor} onChange={(e) => setLapor(e.target.checked)} /> Ikut hapus laporan Steve</label>
    <Btn tone="danger" className="mt-2" disabled={busy(ctx.state)} onClick={() => ctx.hapus("semua", "", `SEMUA hasil: ${d.videos.length} video, catatan produksi, log, dan cache${lapor ? ", plus laporan Steve" : ""}.`, lapor)}>Hapus semua hasil</Btn>
    {busy(ctx.state) && <Muted className="mt-1">Hentikan tugas yang sedang berjalan dulu.</Muted>}
  </>);
}

export const agentById = (id: string) => TEAM.find((t) => t.id === id);

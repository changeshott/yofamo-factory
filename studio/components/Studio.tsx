"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { StudioState, VideoStatus } from "@/lib/types";
import { activeStage, api, daysSince, fmt } from "@/lib/format";
import Office from "./office/Office";
import { drawAvatar } from "./office/sprites";
import { FOUNDER, TEAM } from "./office/world";
import { Btn } from "./ui";
import {
  ActivityPanel, AgentPanel, AnalyticsPanel, BiblePanel, FounderPanel, FuturePanel, GaleriPanel, HealthPanel, KelolaPanel, ProduksiPanel, QueuePanel, ReportsPanel, agentById, type PanelCtx,
} from "./panels";

const TITLES: Record<string, string> = {
  founder: "Meja Zona", queue: "Papan antrean video", analytics: "Analitik Shorts", reports: "Laporan Steve",
  bible: "Channel bible", activity: "Log kantor", health: "Cek sistem", server: "Server agent", produksi: "Buat video", galeri: "Galeri video", kelola: "Kelola hasil",
};
const FOKUS = /^(agent:|founder$|queue$|analytics$|bible$|server$)/;
const JOB_TXT: Record<string, string> = { steve: "Steve menganalisis", fetch: "Steve mengambil data", check: "Cek koneksi YouTube", ide: "Nova mencari ide", penulis: "Raka menulis naskah", suara: "Dara membuat suara", aset: "Bima mencari klip", editor: "Kai merakit video", produksi: "Produksi video", qc: "Rara memeriksa video", data: "Steve mengumpulkan data", upload: "Uli mengunggah", login: "Menghubungkan YouTube" };

interface Toast { id: number; text: string; tone: "ok" | "err" | "info" }

export default function Studio() {
  const [state, setState] = useState<StudioState | null>(null);
  const [offline, setOffline] = useState(false);
  const [panel, setPanel] = useState<string | null>(null);
  const [target, setTargetState] = useState(3);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [konfirmasi, setKonfirmasi] = useState<{ judul: string; aksi: () => Promise<void> } | null>(null);
  const [kelolaTick, setKelolaTick] = useState(0);
  const [palette, setPalette] = useState(false);
  const [lipat, setLipat] = useState(false);
  useEffect(() => { try { setLipat(localStorage.getItem("yofamo.sidebar") === "lipat"); } catch { /* abaikan */ } }, []);
  const setLipatSimpan = (v: boolean) => { setLipat(v); try { localStorage.setItem("yofamo.sidebar", v ? "lipat" : "buka"); } catch { /* abaikan */ } };
  const [lebar, setLebar] = useState(1600);
  useEffect(() => { const f = () => setLebar(window.innerWidth); f(); window.addEventListener("resize", f); return () => window.removeEventListener("resize", f); }, []);
  const sidebarW = lebar < 1024 ? 0 : lipat ? 64 : 252;
  const prevJob = useRef<string>("");
  const avatar = useRef<HTMLCanvasElement>(null);
  const closeBtn = useRef<HTMLButtonElement>(null);
  const lastFocus = useRef<HTMLElement | null>(null);

  const toast = useCallback((text: string, tone: Toast["tone"] = "info") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, text, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000);
  }, []);

  const refresh = useCallback(async () => {
    try {
      const s = await api<StudioState>("/api/state");
      setState(s); setOffline(false);
      const sig = `${s.job.log}:${s.job.status}`;
      if (prevJob.current && prevJob.current !== sig && prevJob.current.endsWith(":running") && s.job.status !== "running" && prevJob.current.startsWith(`${s.job.log}:`)) {
        const what = JOB_TXT[s.job.job ?? ""] ?? "Tugas";
        const text = s.job.status === "ok" ? `${what}: selesai.` : s.job.status === "stopped" ? `${what}: dihentikan.` : `${what}: gagal. Cek log di meja agent.`;
        toast(text, s.job.status === "ok" ? "ok" : "err");
        if (document.hidden && "Notification" in window && Notification.permission === "granted") new Notification("Studio Yofamo", { body: text, icon: "/favicon.svg" });
      }
      prevJob.current = sig;
    } catch { setOffline(true); }
  }, [toast]);

  useEffect(() => {
    try { setTargetState(Number(localStorage.getItem("yofamo.target")) || 3); } catch { /* abaikan */ }
    refresh();
  }, [refresh]);
  useEffect(() => {
    const t = setTimeout(refresh, state?.job.status === "running" ? 2500 : 10000);
    return () => clearTimeout(t);
  }, [state, refresh]);

  const open = useCallback((id: string) => { if (!panel) lastFocus.current = document.activeElement as HTMLElement; setPanel(id); }, [panel]);
  const close = useCallback(() => { setPanel(null); lastFocus.current?.focus?.(); }, []);
  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((v) => !v); return; }
      if (e.key === "Escape") { setPalette(false); close(); }
    };
    window.addEventListener("keydown", k); return () => window.removeEventListener("keydown", k);
  }, [close]);
  useEffect(() => { if (panel) setTimeout(() => closeBtn.current?.focus(), 60); }, [panel]);

  const run = useCallback(async (job: string, arg = "") => {
    try {
      if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {});
      await api("/api/run", { job, arg });
      toast(`${JOB_TXT[job] ?? "Tugas"} dimulai.`);
    } catch (e) { toast((e as Error).message, "err"); }
    refresh();
  }, [refresh, toast]);
  const stop = useCallback(async () => { try { toast((await api("/api/stop", {})).message); } catch (e) { toast((e as Error).message, "err"); } refresh(); }, [refresh, toast]);
  const move = useCallback(async (slug: string, status: VideoStatus) => {
    try { await api("/api/video", { slug, status }); toast(status === "disetujui" ? "Ide disetujui. Raka bisa mulai menulis." : status === "terbit" ? "Mantap, video ditandai terbit!" : "Status diperbarui.", "ok"); }
    catch (e) { toast((e as Error).message, "err"); }
    refresh();
  }, [refresh, toast]);
  const setTarget = (n: number) => { setTargetState(n); try { localStorage.setItem("yofamo.target", String(n)); } catch { /* abaikan */ } };

  // avatar di header panel
  const agent = panel?.startsWith("agent:") ? agentById(panel.slice(6)) : undefined;
  const look = agent?.look ?? (panel === "founder" ? FOUNDER.look : null);
  useEffect(() => { if (avatar.current && look) drawAvatar(avatar.current, look, agent?.id ?? "zona"); }, [look, agent]);

  const hapus = useCallback((jenis: string, nama: string, judul: string, laporan = false) => {
    setKonfirmasi({ judul, aksi: async () => {
      try { toast((await api<{ message: string }>("/api/hapus", { jenis, nama, laporan })).message, "ok"); }
      catch (e) { toast((e as Error).message, "err"); }
      setKelolaTick((n) => n + 1); refresh();
    } });
  }, [refresh, toast]);
  const ctx: PanelCtx | null = state ? { state, run, move, open, target, setTarget, stop, hapus, kelolaTick } : null;
  const busyKey = state?.job.job === "produksi" ? activeStage(state) : state?.job.job ?? "";
  const prodStage = state?.job.job === "produksi" ? state.produksi[0]?.tahap.find((t) => t.status === "jalan")?.nama : null;
  const inbox = state ? state.videos.filter((v) => v.status === "ide" || v.status === "draft").length : 0;
  const ideas = state?.videos.filter((v) => v.status === "ide").length ?? 0, ready = state?.videos.filter((v) => v.status === "draft").length ?? 0;
  const lastUp = state?.snapshot?.videos.reduce((a, v) => (v.published > a ? v.published : a), "") ?? "";
  const gap = lastUp ? daysSince(lastUp) : null;
  const h = new Date().getHours(), sapa = h < 11 ? "Selamat pagi" : h < 15 ? "Selamat siang" : h < 18 ? "Selamat sore" : "Selamat malam";
  const todo = [ideas && `${ideas} ide menunggu persetujuanmu`, ready && `${ready} video menunggu kamu tonton`].filter(Boolean).join(", ");
  const problems = state ? [!state.health.python && "Python", !state.health.claude && "Claude Code", !state.health.env && ".env"].filter(Boolean) : [];

  const title = agent ? `${agent.name} · ${agent.role}` : panel?.startsWith("future:") ? "Meja kosong" : panel ? TITLES[panel] ?? "" : "";

  return (
    <main className="fixed inset-0 overflow-hidden bg-ink-900">
      <Office state={state} onOpen={open} fokus={panel && FOKUS.test(panel) ? panel : null} kiri={sidebarW + 24} kanan={panel ? 540 : 0} />

      {/* HUD kiri atas */}
      <div className="pointer-events-none absolute top-3 bottom-[88px] left-3 z-[25] flex max-w-[min(560px,calc(100vw-24px))] flex-col gap-3">
      <header>
        <div className="pointer-events-auto rounded-xl border border-line/80 bg-ink-800/85 px-4 py-3 shadow-xl backdrop-blur-md">
          <h1 className="font-pixel text-[22px] leading-none font-bold tracking-wide">Studio <span className="text-brand">Yofamo</span></h1>
          <p className="mt-1.5 text-sm text-muted" aria-live="polite">
            {offline ? "Server Studio tidak menjawab. Pastikan jendela start_studio masih terbuka." : state ? `${sapa}, Zona. ${todo ? todo + "." : "Tidak ada yang menunggu keputusanmu."}` : "Memuat kantor…"}
          </p>
          {state?.job.status === "running" && (
            <div className="mt-2 flex items-center gap-2 text-sm">
              <span className="size-2 animate-pulse rounded-full bg-signal motion-reduce:animate-none" aria-hidden />
              <button className="text-left hover:underline" onClick={() => state.job.job === "produksi" && open("produksi")}>{prodStage ? `Produksi: ${prodStage}` : JOB_TXT[state.job.job ?? ""] ?? "Tugas berjalan"}…</button>
              <Btn size="sm" tone="danger" onClick={stop}>Hentikan</Btn>
            </div>
          )}
          {problems.length > 0 && (
            <button onClick={() => open("health")} className="mt-2 block text-left text-sm text-signal hover:underline">Perlu disiapkan: {problems.join(", ")}. Buka cek sistem</button>
          )}
        </div>
      </header>
      {state && <TimSidebar state={state} open={open} panel={panel} busyKey={busyKey} inbox={inbox} lipat={lipat} setLipat={setLipatSimpan} />}
      </div>

      {/* statistik kanan atas */}
      {state && (
        <div className="pointer-events-none absolute top-3 right-3 z-10 flex max-w-[50vw] flex-wrap justify-end gap-2 max-md:top-auto max-md:right-auto max-md:bottom-[84px] max-md:left-3 max-md:max-w-[calc(100vw-24px)] max-md:justify-start">
          {state.snapshot && (<>
            <Stat value={fmt(state.snapshot.channel.subscribers)} label="subscriber" />
            <Stat value={fmt(Math.round(state.snapshot.summary.median_views))} label="median views" />
          </>)}
          {gap != null && <Stat value={String(gap)} label="hari sejak upload" warn={gap > 7} />}
          <Stat value={`${state.week.published}/${target}`} label="terbit minggu ini" good={state.week.published >= target} />
        </div>
      )}

      {/* pipeline produksi langsung (atas tengah) */}
      {state && <PipelineStrip state={state} onOpen={() => open("produksi")} />}

      {/* dok bawah: ringkas, dikelompokkan */}
      <Dock state={state} open={open} inbox={inbox} busyKey={busyKey} problems={problems.length} onPalette={() => setPalette(true)} />

      {palette && ctx && <CommandPalette ctx={ctx} onClose={() => setPalette(false)} />}

      {konfirmasi && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4" role="alertdialog" aria-modal="true" aria-labelledby="konf-judul">
          <div className="w-full max-w-sm rounded-xl border border-bad/50 bg-ink-800 p-5 shadow-2xl">
            <h2 id="konf-judul" className="font-pixel text-lg font-bold text-bad">Hapus permanen?</h2>
            <p className="mt-2 text-[15px]">{konfirmasi.judul}</p>
            <p className="mt-1 text-sm text-muted">File yang dihapus tidak bisa dikembalikan.</p>
            <div className="mt-4 flex justify-end gap-2">
              <Btn autoFocus onClick={() => setKonfirmasi(null)}>Batal</Btn>
              <Btn tone="danger" onClick={async () => { const k = konfirmasi; setKonfirmasi(null); await k.aksi(); }}>Ya, hapus</Btn>
            </div>
          </div>
        </div>
      )}
      {/* toast */}
      <div className="pointer-events-none absolute top-3 left-1/2 z-30 flex -translate-x-1/2 flex-col items-center gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`rounded-lg border px-3.5 py-2 text-sm shadow-xl backdrop-blur-md ${t.tone === "ok" ? "border-leaf/50 bg-[#123527]/95" : t.tone === "err" ? "border-bad/60 bg-[#3a1820]/95" : "border-line bg-ink-800/95"}`}>{t.text}</div>
        ))}
      </div>

      {/* panel kanan */}
      <div className={`absolute inset-0 z-20 bg-[#050a12]/20 transition-opacity ${panel ? "opacity-100" : "pointer-events-none opacity-0"}`} onClick={close} aria-hidden />
      <aside aria-labelledby="panel-title" aria-hidden={!panel} inert={!panel}
        className={`absolute top-0 right-0 bottom-0 z-20 flex w-[min(540px,100vw)] flex-col border-l-2 border-ink-950 bg-ink-800 shadow-2xl transition-transform duration-200 ${panel ? "translate-x-0" : "translate-x-full"}`}>
        <div className="flex items-center gap-3 border-b border-line px-4 py-3.5">
          <canvas ref={avatar} width={16} height={16} className={`size-12 rounded-lg border border-line bg-ink-700 [image-rendering:pixelated] ${look ? "" : "hidden"}`} aria-hidden />
          <h2 id="panel-title" className="flex-1 font-pixel text-xl font-bold">{title}</h2>
          <button ref={closeBtn} onClick={close} aria-label="Tutup panel" className="grid size-9 place-items-center rounded-md border border-line text-lg hover:border-circuit">×</button>
        </div>
        <div className="flex-1 overflow-y-auto px-4 pt-4 pb-10">
          {ctx && panel && (
            agent ? <AgentPanel key={panel} def={agent} ctx={ctx} />
            : panel.startsWith("future:") ? <FuturePanel k={panel.slice(7)} />
            : panel === "founder" ? <FounderPanel ctx={ctx} />
            : panel === "queue" ? <QueuePanel ctx={ctx} />
            : panel === "produksi" ? <ProduksiPanel ctx={ctx} />
            : panel === "galeri" ? <GaleriPanel ctx={ctx} />
            : panel === "kelola" ? <KelolaPanel ctx={ctx} />
            : panel === "analytics" ? <AnalyticsPanel ctx={ctx} />
            : panel === "reports" ? <ReportsPanel ctx={ctx} />
            : panel === "bible" ? <BiblePanel />
            : panel === "activity" ? <ActivityPanel ctx={ctx} />
            : panel === "server" ? <ServerPanel ctx={ctx} />
            : <HealthPanel ctx={ctx} />
          )}
        </div>
      </aside>
    </main>
  );
}

function ServerPanel({ ctx }: { ctx: PanelCtx }) {
  const j = ctx.state.job;
  return (<>
    <p>Rak server ini tempat agent bekerja. Lampunya berkedip lebih cepat saat ada tugas berjalan.</p>
    <p className="mt-2 text-sm text-muted">{j.status === "running" ? `Sedang berjalan: ${JOB_TXT[j.job ?? ""] ?? j.job}, mulai ${j.started?.slice(11, 16)}.` : "Tidak ada tugas berjalan."}</p>
    {j.status === "running" && <Btn className="mt-3" tone="danger" onClick={async () => { await api("/api/stop", {}).catch(() => {}); }}>Hentikan tugas</Btn>}
    <div className="mt-3"><Btn onClick={() => ctx.open("health")}>Cek sistem</Btn></div>
  </>);
}

function Stat({ value, label, warn, good }: { value: string; label: string; warn?: boolean; good?: boolean }) {
  return (
    <div className={`pointer-events-auto flex items-baseline gap-1.5 rounded-lg border bg-ink-800/85 px-2.5 py-1.5 text-[13px] text-muted shadow-lg backdrop-blur-md ${warn ? "border-signal" : "border-line/80"}`}>
      <b className={`font-pixel text-base leading-none ${warn ? "text-signal" : good ? "text-leaf" : "text-ink-50"}`}>{value}</b>{label}
    </div>
  );
}

/* ---------------------------------------------------------------- dok bawah */
const ICON = {
  tim: "M16 11a3 3 0 1 0-3-3 3 3 0 0 0 3 3Zm-8 0a3 3 0 1 0-3-3 3 3 0 0 0 3 3Zm0 2c-2.7 0-6 1.3-6 3.5V19h12v-2.5C14 14.3 10.7 13 8 13Zm8 0c-.3 0-.7 0-1.1.1A4.2 4.2 0 0 1 16 16.5V19h6v-2.5c0-2.2-3.3-3.5-6-3.5Z",
  zona: "M4 5h16v10H4zM2 17h20v2H2z",
  video: "M4 6h11a2 2 0 0 1 2 2v1.5l4-2.5v10l-4-2.5V16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2Z",
  data: "M4 19V9h3v10H4Zm6 0V5h3v14h-3Zm6 0v-7h3v7h-3Z",
  sistem: "M12 8a4 4 0 1 0 4 4 4 4 0 0 0-4-4Zm8.9 3-1.6-.3a7.5 7.5 0 0 0-.9-2.1l.9-1.4-1.5-1.5-1.4.9a7.5 7.5 0 0 0-2.1-.9L14 4h-2l-.3 1.6a7.5 7.5 0 0 0-2.1.9l-1.4-.9-1.5 1.5.9 1.4a7.5 7.5 0 0 0-.9 2.1L5 11v2l1.6.3c.2.7.5 1.5.9 2.1l-.9 1.4 1.5 1.5 1.4-.9c.6.4 1.4.7 2.1.9L12 20h2l.3-1.6c.7-.2 1.5-.5 2.1-.9l1.4.9 1.5-1.5-.9-1.4c.4-.6.7-1.4.9-2.1L20.9 13Z",
  cari: "M10 4a6 6 0 1 0 3.7 10.7l4.8 4.8 1.4-1.4-4.8-4.8A6 6 0 0 0 10 4Zm0 2a4 4 0 1 1-4 4 4 4 0 0 1 4-4Z",
};
const Ico = ({ d, className = "size-[18px]" }: { d: string; className?: string }) => <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden><path d={d} /></svg>;

function Dock({ state, open, inbox, busyKey, problems, onPalette }: { state: StudioState | null; open: (id: string) => void; inbox: number; busyKey: string; problems: number; onPalette: () => void }) {
  const [menu, setMenu] = useState<null | "tim" | "video" | "data">(null);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!menu) return;
    const f = (e: PointerEvent) => { if (!ref.current?.contains(e.target as Node)) setMenu(null); };
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") setMenu(null); };
    window.addEventListener("pointerdown", f); window.addEventListener("keydown", k);
    return () => { window.removeEventListener("pointerdown", f); window.removeEventListener("keydown", k); };
  }, [menu]);
  const go = (id: string) => { setMenu(null); open(id); };
  const running = state?.job.status === "running";
  const sibuk = TEAM.filter((t) => running && !!t.busy[busyKey]);
  const ideas = state?.videos.filter((v) => v.status === "ide").length ?? 0;
  const drafts = state?.videos.filter((v) => v.status === "draft").length ?? 0;
  const toggle = (m: "tim" | "video" | "data") => setMenu((x) => (x === m ? null : m));
  return (
    <nav aria-label="Navigasi kantor" className="absolute inset-x-0 bottom-3 z-10 flex justify-center px-3">
      <div ref={ref} className="relative flex items-center gap-1 rounded-2xl border border-line/70 bg-ink-800/80 p-1.5 shadow-[0_18px_50px_rgba(0,0,0,.45)] backdrop-blur-xl">
        <button onClick={() => go("produksi")} className="flex items-center gap-2 rounded-xl bg-gradient-to-b from-brand-2 to-brand px-3.5 py-2.5 font-pixel text-sm leading-none font-bold text-[#06132B] shadow-[0_6px_20px_rgba(61,155,255,.35)] hover:brightness-110">
          <span className="text-base leading-none">+</span><span className="max-sm:hidden">Buat video</span>
        </button>
        <span className="mx-1 h-7 w-px bg-line/70" aria-hidden />
        <DockIcon label="Tim" className="lg:hidden" active={menu === "tim"} onClick={() => toggle("tim")} expanded={menu === "tim"}>
          <span className="flex -space-x-1.5">{TEAM.slice(0, 4).map((t) => <i key={t.id} className="block size-2.5 rounded-full ring-2 ring-ink-800" style={{ background: t.color }} />)}</span>
          {sibuk.length > 0 && <span className="absolute -top-1 -right-1 size-2.5 animate-pulse rounded-full bg-brand ring-2 ring-ink-800 motion-reduce:animate-none" aria-label="ada yang bekerja" />}
        </DockIcon>
        <DockIcon label="Meja Zona" onClick={() => go("founder")} count={inbox}><Ico d={ICON.zona} /></DockIcon>
        <DockIcon label="Video" active={menu === "video"} onClick={() => toggle("video")} expanded={menu === "video"} count={drafts}><Ico d={ICON.video} /></DockIcon>
        <DockIcon label="Data" active={menu === "data"} onClick={() => toggle("data")} expanded={menu === "data"}><Ico d={ICON.data} /></DockIcon>
        <DockIcon label="Sistem" onClick={() => go("health")} dot={problems ? "#F07178" : "#6FD29A"}><Ico d={ICON.sistem} /></DockIcon>
        <span className="mx-1 h-7 w-px bg-line/70 max-sm:hidden" aria-hidden />
        <button onClick={onPalette} className="flex items-center gap-2 rounded-xl px-2.5 py-2 text-sm text-muted hover:bg-ink-700 hover:text-ink-50 max-sm:hidden" aria-label="Cari perintah (Ctrl+K)">
          <Ico d={ICON.cari} className="size-4" /><span className="kbd">Ctrl K</span>
        </button>

        {menu && (
          <div className="dock-pop absolute bottom-[calc(100%+10px)] left-1/2 w-[min(560px,calc(100vw-24px))] -translate-x-1/2 rounded-2xl border border-line/70 bg-ink-800/95 p-3 shadow-[0_24px_70px_rgba(0,0,0,.55)] backdrop-blur-xl">
            {menu === "tim" && (<>
              <div className="mb-2 flex items-baseline justify-between px-1"><h3 className="font-pixel text-sm text-muted">Tim agent</h3><span className="text-xs text-faint">{sibuk.length ? `${sibuk.map((t) => t.name).join(", ")} sedang bekerja` : "semua siap"}</span></div>
              <div className="grid grid-cols-4 gap-2 max-sm:grid-cols-2">
                {TEAM.map((t) => {
                  const on = sibuk.includes(t);
                  return (
                    <button key={t.id} onClick={() => go(`agent:${t.id}`)} className={`group flex flex-col items-start gap-1 rounded-xl border p-2.5 text-left transition hover:-translate-y-0.5 hover:border-brand/60 ${on ? "border-brand/50 bg-brand/10" : "border-line/60 bg-ink-900/60"}`}>
                      <span className="flex w-full items-center gap-2">
                        <AgentAvatar id={t.id} />
                        <span className={`ml-auto size-2 rounded-full ${on ? "animate-pulse bg-brand motion-reduce:animate-none" : "bg-leaf/70"}`} aria-hidden />
                      </span>
                      <b className="font-pixel text-sm leading-none" style={{ color: t.color }}>{t.name}</b>
                      <span className="text-[12px] leading-tight text-muted">{on ? t.busy[busyKey] : t.role}</span>
                    </button>);
                })}
              </div>
            </>)}
            {menu === "video" && <MenuGrid items={[
              ["produksi", "Buat video", "Tim memilih topik & membuat video"], ["galeri", "Galeri", drafts ? `${drafts} video menunggu kamu tonton` : "Semua video jadi"],
              ["queue", "Antrean", "Papan ide → terbit"], ["kelola", "Kelola", "Hapus hasil & bersihkan"],
            ]} go={go} />}
            {menu === "data" && <MenuGrid items={[
              ["analytics", "Analitik", "Grafik & tabel semua Shorts"], ["reports", "Laporan", "Laporan mingguan Steve"],
              ["bible", "Channel bible", "Aturan gaya & konten"], ["activity", "Log kantor", ideas ? `${ideas} ide baru tercatat` : "Riwayat aktivitas"],
            ]} go={go} />}
          </div>
        )}
      </div>
    </nav>
  );
}

function MenuGrid({ items, go }: { items: [string, string, string][]; go: (id: string) => void }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map(([id, t, d]) => (
        <button key={id} onClick={() => go(id)} className="rounded-xl border border-line/60 bg-ink-900/60 p-3 text-left transition hover:-translate-y-0.5 hover:border-brand/60">
          <b className="block font-pixel text-[15px] leading-none">{t}</b><span className="mt-1 block text-[12.5px] text-muted">{d}</span>
        </button>))}
    </div>
  );
}

function DockIcon({ children, label, onClick, count, dot, active, expanded, className = "" }: { children: React.ReactNode; label: string; onClick: () => void; count?: number; dot?: string; active?: boolean; expanded?: boolean; className?: string }) {
  return (
    <button onClick={onClick} aria-expanded={expanded} className={`${className} group relative flex items-center gap-2 rounded-xl px-3 py-2.5 font-pixel text-sm leading-none transition ${active ? "bg-ink-700 text-ink-50" : "text-muted hover:bg-ink-700 hover:text-ink-50"}`}>
      <span className="relative grid place-items-center">{children}</span>
      <span className="max-md:hidden">{label}</span>
      {dot && <span className="size-2 rounded-full" style={{ background: dot }} aria-hidden />}
      {!!count && <span className="rounded-full bg-bad px-1.5 py-0.5 text-[11px] text-white" aria-label={`${count} perlu perhatian`}>{count}</span>}
      <span className="pointer-events-none absolute -top-8 left-1/2 hidden -translate-x-1/2 rounded-md border border-line bg-ink-800 px-2 py-1 text-xs whitespace-nowrap text-ink-50 max-md:group-hover:block">{label}</span>
    </button>
  );
}

function AgentAvatar({ id }: { id: string }) {
  const c = useRef<HTMLCanvasElement>(null);
  const a = agentById(id);
  useEffect(() => { if (c.current && a) drawAvatar(c.current, a.look, a.id); }, [a]);
  return <canvas ref={c} width={16} height={16} className="size-9 rounded-lg border border-line/60 bg-ink-700 [image-rendering:pixelated]" aria-hidden />;
}

/* ---------------------------------------------------------------- pipeline produksi langsung */
function PipelineStrip({ state, onOpen }: { state: StudioState; onOpen: () => void }) {
  const p = state.produksi[0];
  if (!p || p.status !== "berjalan" || state.job.status !== "running" || state.job.job !== "produksi") return null;
  const done = p.tahap.filter((t) => t.status === "ok").length, cur = p.tahap.find((t) => t.status === "jalan");
  const warna: Record<string, string> = { steve: "#47B5FF", nova: "#6FD29A", setuju: "#F4F1E8", raka: "#FF9A4D", dara: "#C792EA", bima: "#4FD1C5", kai: "#F2C94C", rara: "#F07178" };
  return (
    <button onClick={onOpen} className="absolute top-3 left-1/2 z-10 -translate-x-1/2 rounded-2xl border border-line/70 bg-ink-800/85 px-4 py-2.5 text-left shadow-xl backdrop-blur-xl hover:border-brand/60 max-lg:top-auto max-lg:bottom-[86px]">
      <div className="flex items-center gap-1.5" aria-hidden>
        {p.tahap.map((t) => (
          <span key={t.kunci} title={t.nama} className={`h-2 rounded-full transition-all ${t.status === "jalan" ? "w-8 animate-pulse motion-reduce:animate-none" : "w-4"} ${t.status === "menunggu" ? "opacity-25" : t.status === "gagal" ? "!bg-bad" : ""}`}
            style={{ background: t.status === "menunggu" ? "#66809d" : warna[t.kunci] ?? "#3D9BFF" }} />))}
      </div>
      <p className="mt-1.5 text-[13px] leading-none"><b className="font-pixel">{cur?.nama ?? "Menyiapkan"}</b><span className="text-muted"> · tahap {Math.min(done + 1, p.tahap.length)}/{p.tahap.length}{p.slug ? "" : ""}</span></p>
    </button>
  );
}

/* ---------------------------------------------------------------- palet perintah (Ctrl+K) */
function CommandPalette({ ctx, onClose }: { ctx: PanelCtx; onClose: () => void }) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const inp = useRef<HTMLInputElement>(null);
  useEffect(() => { inp.current?.focus(); }, []);
  const running = ctx.state.job.status === "running";
  const items: { t: string; d: string; run: () => void; grup: string }[] = [
    { grup: "Aksi", t: "Buat video baru", d: "Tim memilih topik sendiri", run: () => ctx.open("produksi") },
    { grup: "Aksi", t: "Cari 3 ide (Nova)", d: "Riset ide untuk kamu pilih", run: () => { if (!running) void ctx.run("ide"); } },
    { grup: "Aksi", t: "Kumpulkan data (Steve)", d: "Statistik, komentar, retensi — tanpa kuota Claude", run: () => { if (!running) void ctx.run("data"); } },
    { grup: "Aksi", t: "Analisa lengkap (Steve)", d: "Laporan mingguan", run: () => { if (!running) void ctx.run("steve"); } },
    ...(running ? [{ grup: "Aksi", t: "Hentikan tugas yang berjalan", d: "", run: () => void ctx.stop() }] : []),
    ...TEAM.map((a) => ({ grup: "Tim", t: `${a.name} · ${a.role}`, d: "Buka meja", run: () => ctx.open(`agent:${a.id}`) })),
    ...([["founder", "Meja Zona"], ["galeri", "Galeri video"], ["queue", "Papan antrean"], ["kelola", "Kelola hasil"], ["analytics", "Analitik"], ["reports", "Laporan Steve"], ["bible", "Channel bible"], ["activity", "Log kantor"], ["health", "Cek sistem"]] as const)
      .map(([id, t]) => ({ grup: "Buka", t, d: "", run: () => ctx.open(id) })),
    ...ctx.state.videos.slice(0, 30).map((v) => ({ grup: "Video", t: v.judul_kerja, d: v.label, run: () => ctx.open("queue") })),
  ];
  const f = q.trim().toLowerCase();
  const list = f ? items.filter((x) => `${x.t} ${x.d} ${x.grup}`.toLowerCase().includes(f)) : items.slice(0, 14);
  const pick = (i: number) => { const x = list[i]; if (x) { onClose(); x.run(); } };
  return (
    <div className="fixed inset-0 z-40 grid place-items-start justify-center bg-black/50 px-3 pt-[12vh]" onClick={onClose}>
      <div role="dialog" aria-modal="true" aria-label="Palet perintah" onClick={(e) => e.stopPropagation()} className="dock-pop w-full max-w-xl overflow-hidden rounded-2xl border border-line bg-ink-800 shadow-2xl">
        <div className="flex items-center gap-2 border-b border-line px-4">
          <Ico d={ICON.cari} className="size-4 text-muted" />
          <input ref={inp} value={q} onChange={(e) => { setQ(e.target.value); setSel(0); }} placeholder="Cari agent, panel, video, atau aksi…"
            onKeyDown={(e) => { if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, list.length - 1)); } else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); } else if (e.key === "Enter") pick(sel); }}
            className="h-12 flex-1 bg-transparent text-[15px] outline-none placeholder:text-faint focus-visible:outline-none" />
          <span className="kbd">Esc</span>
        </div>
        <ul className="max-h-[50vh] overflow-y-auto p-1.5" role="listbox">
          {list.length === 0 && <li className="px-3 py-4 text-sm text-muted">Tidak ada yang cocok.</li>}
          {list.map((x, i) => (
            <li key={`${x.grup}-${x.t}-${i}`} role="option" aria-selected={i === sel}>
              <button onMouseEnter={() => setSel(i)} onClick={() => pick(i)} className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left ${i === sel ? "bg-ink-700" : ""}`}>
                <span className="w-12 shrink-0 text-[11px] tracking-wide text-faint uppercase">{x.grup}</span>
                <span className="flex-1 truncate text-[14.5px]">{x.t}</span>
                {x.d && <span className="truncate text-xs text-muted">{x.d}</span>}
              </button>
            </li>))}
        </ul>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- sidebar tim (kiri) */
function TimSidebar({ state, open, panel, busyKey, inbox, lipat, setLipat }: { state: StudioState; open: (id: string) => void; panel: string | null; busyKey: string; inbox: number; lipat: boolean; setLipat: (v: boolean) => void }) {
  const running = state.job.status === "running";
  const urut = ["steve", "nova", "raka", "dara", "bima", "kai", "rara", "uli"];
  const tahap = state.produksi[0]?.status === "berjalan" ? state.produksi[0].tahap : [];
  const statusTahap = (id: string) => tahap.find((t) => t.kunci === id)?.status;
  return (
    <aside aria-label="Tim agent" className={`pointer-events-auto flex min-h-0 flex-col overflow-hidden rounded-2xl border border-line/70 bg-ink-800/75 shadow-[0_18px_50px_rgba(0,0,0,.4)] backdrop-blur-xl transition-[width] duration-300 max-lg:hidden ${lipat ? "w-[64px]" : "w-[252px]"}`}>
      <div className={`flex items-center border-b border-line/60 px-3 py-2.5 ${lipat ? "justify-center" : "justify-between"}`}>
        {!lipat && <h2 className="font-pixel text-sm tracking-wide text-muted">Tim · {running ? "bekerja" : "siap"}</h2>}
        <button onClick={() => setLipat(!lipat)} aria-label={lipat ? "Lebarkan sidebar" : "Ciutkan sidebar"} className="grid size-7 place-items-center rounded-lg text-muted hover:bg-ink-700 hover:text-ink-50">
          <svg viewBox="0 0 24 24" className={`size-4 transition-transform ${lipat ? "rotate-180" : ""}`} fill="currentColor" aria-hidden><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z" /></svg>
        </button>
      </div>
      <ul className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
        {urut.map((id) => {
          const t = agentById(id)!;
          const on = running && !!t.busy[busyKey];
          const st = statusTahap(id), sel = panel === `agent:${id}`;
          const sub = on ? t.busy[busyKey] : st === "ok" ? "Selesai ✓" : st === "gagal" ? "Gagal, cek log" : t.role;
          return (
            <li key={id}>
              <button onClick={() => open(`agent:${id}`)} title={lipat ? `${t.name} · ${sub}` : undefined}
                className={`group relative flex w-full items-center gap-2.5 rounded-xl p-1.5 text-left transition ${sel ? "bg-ink-700 ring-1 ring-brand/70" : "hover:bg-ink-700/70"} ${lipat ? "justify-center" : ""}`}>
                {on && <span className="absolute inset-0 rounded-xl ring-1 ring-brand/60 shadow-[0_0_18px_rgba(61,155,255,.35)]" aria-hidden />}
                <span className="relative shrink-0">
                  <AgentAvatar id={id} />
                  <span className={`absolute -right-0.5 -bottom-0.5 size-2.5 rounded-full ring-2 ring-ink-800 ${on ? "animate-pulse bg-brand motion-reduce:animate-none" : st === "gagal" ? "bg-bad" : "bg-leaf"}`} aria-hidden />
                </span>
                {!lipat && (
                  <span className="min-w-0 flex-1">
                    <b className="block font-pixel text-[14px] leading-tight" style={{ color: t.color }}>{t.name}</b>
                    <span className={`block truncate text-[12px] leading-tight ${on ? "text-brand-2" : "text-muted"}`}>{sub}</span>
                    {on && <span className="mt-1 block h-1 overflow-hidden rounded-full bg-ink-600"><i className="block h-full w-1/3 animate-[geser_1.4s_ease-in-out_infinite] rounded-full bg-brand motion-reduce:animate-none" /></span>}
                  </span>
                )}
              </button>
            </li>);
        })}
      </ul>
      <button onClick={() => open("founder")} className={`flex items-center gap-2.5 border-t border-line/60 p-2.5 text-left hover:bg-ink-700/70 ${lipat ? "justify-center" : ""} ${panel === "founder" ? "bg-ink-700" : ""}`}>
        <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-gradient-to-b from-brand-2 to-brand font-pixel text-sm font-bold text-[#06132B]">Z</span>
        {!lipat && <span className="min-w-0 flex-1"><b className="block font-pixel text-[14px] leading-tight">Meja Zona</b><span className="block text-[12px] text-muted">{inbox ? `${inbox} menunggu keputusanmu` : "Tidak ada yang menunggu"}</span></span>}
        {!!inbox && <span className="rounded-full bg-bad px-1.5 py-0.5 font-pixel text-[11px] text-white">{inbox}</span>}
      </button>
    </aside>
  );
}


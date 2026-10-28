"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { StudioState, VideoStatus } from "@/lib/types";
import { api, daysSince, fmt } from "@/lib/format";
import Office from "./office/Office";
import { drawAvatar } from "./office/sprites";
import { FOUNDER, TEAM } from "./office/world";
import { Btn } from "./ui";
import {
  ActivityPanel, AgentPanel, AnalyticsPanel, BiblePanel, FounderPanel, FuturePanel, HealthPanel, QueuePanel, ReportsPanel, agentById, type PanelCtx,
} from "./panels";

const TITLES: Record<string, string> = {
  founder: "Meja Zona", queue: "Papan antrean video", analytics: "Analitik Shorts", reports: "Laporan Steve",
  bible: "Channel bible", activity: "Log kantor", health: "Cek sistem", server: "Server agent",
};
const JOB_TXT: Record<string, string> = { steve: "Steve menganalisis", fetch: "Steve mengambil data", check: "Cek koneksi YouTube", ide: "Nova mencari ide", penulis: "Raka menulis naskah", suara: "Dara membuat suara", aset: "Bima mencari klip" };

interface Toast { id: number; text: string; tone: "ok" | "err" | "info" }

export default function Studio() {
  const [state, setState] = useState<StudioState | null>(null);
  const [offline, setOffline] = useState(false);
  const [panel, setPanel] = useState<string | null>(null);
  const [target, setTargetState] = useState(3);
  const [toasts, setToasts] = useState<Toast[]>([]);
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
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
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

  const ctx: PanelCtx | null = state ? { state, run, move, open, target, setTarget } : null;
  const inbox = state ? state.videos.filter((v) => v.status === "ide" || v.status === "naskah").length : 0;
  const ideas = state?.videos.filter((v) => v.status === "ide").length ?? 0, ready = state?.videos.filter((v) => v.status === "naskah").length ?? 0;
  const lastUp = state?.snapshot?.videos.reduce((a, v) => (v.published > a ? v.published : a), "") ?? "";
  const gap = lastUp ? daysSince(lastUp) : null;
  const h = new Date().getHours(), sapa = h < 11 ? "Selamat pagi" : h < 15 ? "Selamat siang" : h < 18 ? "Selamat sore" : "Selamat malam";
  const todo = [ideas && `${ideas} ide menunggu persetujuanmu`, ready && `${ready} naskah siap direkam`].filter(Boolean).join(", ");
  const problems = state ? [!state.health.python && "Python", !state.health.claude && "Claude Code", !state.health.env && ".env"].filter(Boolean) : [];

  const title = agent ? `${agent.name} · ${agent.role}` : panel?.startsWith("future:") ? "Meja kosong" : panel ? TITLES[panel] ?? "" : "";

  return (
    <main className="fixed inset-0 overflow-hidden bg-ink-900">
      <Office state={state} onOpen={open} />

      {/* HUD kiri atas */}
      <header className="pointer-events-none absolute top-3 left-3 z-10 max-w-[min(560px,calc(100vw-24px))]">
        <div className="pointer-events-auto rounded-xl border border-line/80 bg-ink-800/85 px-4 py-3 shadow-xl backdrop-blur-md">
          <h1 className="font-pixel text-[22px] leading-none font-bold tracking-wide">Studio <span className="text-signal">Yofamo</span></h1>
          <p className="mt-1.5 text-sm text-muted" aria-live="polite">
            {offline ? "Server Studio tidak menjawab. Pastikan jendela start_studio masih terbuka." : state ? `${sapa}, Zona. ${todo ? todo + "." : "Tidak ada yang menunggu keputusanmu."}` : "Memuat kantor…"}
          </p>
          {state?.job.status === "running" && (
            <div className="mt-2 flex items-center gap-2 text-sm">
              <span className="size-2 animate-pulse rounded-full bg-signal motion-reduce:animate-none" aria-hidden />
              <span>{JOB_TXT[state.job.job ?? ""] ?? "Tugas berjalan"}…</span>
              <Btn size="sm" tone="danger" onClick={stop}>Hentikan</Btn>
            </div>
          )}
          {problems.length > 0 && (
            <button onClick={() => open("health")} className="mt-2 block text-left text-sm text-signal hover:underline">Perlu disiapkan: {problems.join(", ")}. Buka cek sistem</button>
          )}
        </div>
      </header>

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

      {/* dok bawah */}
      <nav aria-label="Bagian kantor" className="absolute inset-x-0 bottom-3 z-10 flex justify-center px-3">
        <div className="flex max-w-full gap-1.5 overflow-x-auto rounded-xl border border-line/80 bg-ink-800/85 p-1.5 shadow-xl backdrop-blur-md">
          <DockBtn onClick={() => open("founder")} color="#F4F1E8" count={inbox}>Meja Zona</DockBtn>
          {TEAM.map((t) => <DockBtn key={t.id} onClick={() => open(`agent:${t.id}`)} color={t.color} busy={!!state && state.job.status === "running" && !!t.busy[state.job.job ?? ""]}>{t.name}</DockBtn>)}
          <span className="mx-1 w-px shrink-0 bg-line" aria-hidden />
          <DockBtn onClick={() => open("queue")}>Antrean</DockBtn>
          <DockBtn onClick={() => open("analytics")}>Analitik</DockBtn>
          <DockBtn onClick={() => open("reports")}>Laporan</DockBtn>
          <DockBtn onClick={() => open("bible")}>Bible</DockBtn>
          <DockBtn onClick={() => open("activity")}>Log</DockBtn>
          <DockBtn onClick={() => open("health")} dot={problems.length ? "#F07178" : "#6FD29A"}>Sistem</DockBtn>
        </div>
      </nav>

      {/* toast */}
      <div className="pointer-events-none absolute top-3 left-1/2 z-30 flex -translate-x-1/2 flex-col items-center gap-2" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`rounded-lg border px-3.5 py-2 text-sm shadow-xl backdrop-blur-md ${t.tone === "ok" ? "border-leaf/50 bg-[#123527]/95" : t.tone === "err" ? "border-bad/60 bg-[#3a1820]/95" : "border-line bg-ink-800/95"}`}>{t.text}</div>
        ))}
      </div>

      {/* panel kanan */}
      <div className={`absolute inset-0 z-20 bg-[#050a12]/45 transition-opacity ${panel ? "opacity-100" : "pointer-events-none opacity-0"}`} onClick={close} aria-hidden />
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

function DockBtn({ children, onClick, color, count, busy, dot }: { children: React.ReactNode; onClick: () => void; color?: string; count?: number; busy?: boolean; dot?: string }) {
  return (
    <button onClick={onClick} className="flex shrink-0 items-center gap-2 rounded-lg border border-transparent px-3 py-2 font-pixel text-sm leading-none hover:border-line hover:bg-ink-700">
      {color && <span className={`size-2.5 rounded-[2px] ${busy ? "animate-pulse motion-reduce:animate-none" : ""}`} style={{ background: color }} aria-hidden />}
      {dot && <span className="size-2 rounded-full" style={{ background: dot }} aria-hidden />}
      {children}
      {!!count && <span className="rounded-full bg-bad px-1.5 py-0.5 text-[11px] text-white" aria-label={`${count} perlu keputusan`}>{count}</span>}
    </button>
  );
}

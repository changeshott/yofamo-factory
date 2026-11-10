"use client";

import { useEffect, useRef, useState } from "react";
import type { StudioState } from "@/lib/types";
import { OfficeEngine } from "./engine";
import { BH, BW, kotakRuang, type Ruang } from "./world";

interface Cam { s: number; x: number; y: number; fit: number }

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

export default function Office({ state, onOpen, fokus = null, kiri = 0, kanan = 0, kananTetap = 0, ruang: ruangAktif = "semua", atas = 0 }: { state: StudioState | null; onOpen: (id: string) => void; fokus?: string | null; kiri?: number; kanan?: number; kananTetap?: number; ruang?: Ruang; atas?: number }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const engine = useRef<OfficeEngine | null>(null);
  const cam = useRef<Cam>({ s: 1, x: 0, y: 0, fit: 1 });
  const openRef = useRef(onOpen);
  const ruang = useRef({ kiri, kanan, kananTetap, nama: ruangAktif, atas });
  ruang.current = { kiri, kanan, kananTetap, nama: ruangAktif, atas };
  const api = useRef<{ fokus: (id: string | null) => void } | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  openRef.current = onOpen;

  useEffect(() => {
    if (engine.current) engine.current.state = state;
  }, [state]);
  useEffect(() => { const t = setTimeout(() => api.current?.fokus(fokus), 30); return () => clearTimeout(t); }, [fokus, kiri, kananTetap, ruangAktif]);

  useEffect(() => {
    const eng = new OfficeEngine();
    eng.reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    engine.current = eng;
    const cv = canvas.current!, ctx = cv.getContext("2d")!, el = wrap.current!, ov = overlay.current!;
    let w = 0, h = 0, dpr = 1, userZoomed = false, anim = 0;
    const bokeh = Array.from({ length: 14 }, (_, i) => ({ x: ((i * 97) % 100) / 100, y: ((i * 61 + 17) % 100) / 100, r: 40 + ((i * 37) % 90), a: 0.03 + ((i * 13) % 5) / 100 }));

    /** Skala & posisi kamera yang membingkai ruang aktif di area yang tidak tertutup sidebar, HUD atas, dan dok bawah. */
    const bingkai = () => {
      const L = w < 1024 ? 0 : ruang.current.kiri, R = w < 1024 ? 0 : ruang.current.kananTetap, T0 = ruang.current.atas, B = w < 700 ? 150 : 96;
      const [x0, y0, x1, y1] = kotakRuang(ruang.current.nama), bw = x1 - x0, bh = y1 - y0, aw = w - L - R - 16, ah = Math.max(120, h - T0 - B);
      const s = Math.min(aw / bw, ah / bh, ruang.current.nama === "semua" ? 4 : 1.9);
      return { s, x: L + 8 + (aw - bw * s) / 2 - x0 * s, y: T0 + (ah - bh * s) / 2 - y0 * s };
    };
    const fit = () => {
      const r = el.getBoundingClientRect();
      w = r.width; h = r.height; dpr = window.devicePixelRatio || 1;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      const b = bingkai(), c = cam.current;
      if (!userZoomed && !anim) { c.s = b.s; c.x = b.x; c.y = b.y; }
      c.fit = b.s;
    };
    const draw = () => {
      const c = cam.current;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const bg = ctx.createRadialGradient(cv.width / 2, cv.height * 0.45, 0, cv.width / 2, cv.height * 0.45, Math.max(cv.width, cv.height) * 0.7);
      bg.addColorStop(0, "#15284A"); bg.addColorStop(0.55, "#0D1A30"); bg.addColorStop(1, "#070E1B");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, cv.width, cv.height);
      for (const b of bokeh) {   // cahaya lembut melayang di latar (tanpa garis)
        const bx = b.x * cv.width, by = b.y * cv.height, r = b.r * dpr, gr = ctx.createRadialGradient(bx, by, 0, bx, by, r);
        gr.addColorStop(0, `rgba(80,160,255,${b.a})`); gr.addColorStop(1, "rgba(80,160,255,0)"); ctx.fillStyle = gr; ctx.fillRect(bx - r, by - r, r * 2, r * 2);
      }
      { // bayangan & pantulan di bawah ruangan
        const c0 = cam.current, cx = (c0.x + (BW / 2) * c0.s) * dpr, cy = (c0.y + (BH * 0.86) * c0.s) * dpr, rx = BW * 0.46 * c0.s * dpr;
        ctx.save(); ctx.translate(cx, cy); ctx.scale(1, 0.32);
        const gr = ctx.createRadialGradient(0, 0, 0, 0, 0, rx); gr.addColorStop(0, "rgba(0,0,0,.45)"); gr.addColorStop(0.7, "rgba(20,60,140,.10)"); gr.addColorStop(1, "rgba(0,0,0,0)");
        ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(0, 0, rx, 0, Math.PI * 2); ctx.fill(); ctx.restore();
      }
      ctx.imageSmoothingEnabled = false;
      ctx.setTransform(dpr * c.s, 0, 0, dpr * c.s, dpr * c.x, dpr * c.y);
      ctx.drawImage(eng.canvas, 0, 0);
      // overlay: posisi buffer → CSS px
      let html = "";
      for (const o of eng.overlay) {
        const x = c.x + o.x * c.s, y = c.y + o.y * c.s;
        if (o.kind === "tag") {
          const founder = o.tone === "founder";
          html += `<div class="pointer-events-none absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded px-1.5 pt-[3px] pb-[2px] font-pixel text-[11px] leading-none tracking-wide shadow ${founder ? "bg-signal text-[#24140A]" : "bg-[#08121F]/85 text-ink-50"}" style="left:${x}px;top:${y}px">${founder ? "" : `<span class="mr-1 inline-block size-[7px] rounded-[1px] align-[0px]" style="background:${o.tone}"></span>`}${esc(o.text)}</div>`;
        } else if (o.kind === "bubble") {
          const tone = o.tone === "ok" ? "bg-[#E3F8EC]" : o.tone === "err" ? "bg-[#FFE4E4]" : o.tone === "stopped" ? "bg-[#EEF1F5]" : "bg-[#FDFBF6]";
          const pips = o.pips ? `<span class="mt-[3px] flex items-center gap-[2px]">${Array.from({ length: o.pips[1] }, (_, i) => `<i class="block h-[4px] w-[7px] rounded-[1px] ${i + 1 < o.pips![0] ? "bg-[#3FAE74]" : i + 1 === o.pips![0] ? "bg-[#2D8CFF] animate-pulse motion-reduce:animate-none" : "bg-[#C9D3E0]"}"></i>`).join("")}${o.sub ? `<b class="ml-1 font-pixel text-[10px] font-normal text-[#51627C] tabular-nums">${esc(o.sub)}</b>` : ""}</span>` : "";
          html += `<div class="bubble pointer-events-none absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border-2 border-[#1A2638] px-2 py-1 font-pixel text-[12px] leading-tight text-[#1A2638] shadow-[2px_2px_0_rgba(0,0,0,.35)] ${tone}" style="left:${x}px;top:${y}px">${esc(o.text)}${pips}</div>`;
        } else if (o.kind === "sign") {
          html += `<div class="pointer-events-none absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-[3px] border border-white/10 bg-[#08121F]/90 px-1.5 pt-[3px] pb-[2px] text-center font-pixel text-[10px] leading-tight tracking-wide shadow" style="left:${x}px;top:${y}px;color:${o.tone ?? "#BFE3FF"}"><span class="mr-1 inline-block size-[5px] rounded-full align-[1px] animate-pulse motion-reduce:animate-none" style="background:${o.tone ?? "#BFE3FF"}"></span>${esc(o.text)}${o.sub ? `<span class="ml-1 text-ink-50/70">${esc(o.sub)}</span>` : ""}</div>`;
        } else {
          html += `<div class="pointer-events-none absolute grid h-5 min-w-5 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-bad px-1.5 font-pixel text-xs text-white ring-2 ring-[#08121F] animate-pulse motion-reduce:animate-none" style="left:${x}px;top:${y}px">${esc(o.text)}</div>`;
        }
      }
      if (ov.dataset.html !== html) { ov.innerHTML = html; ov.dataset.html = html; }
    };
    // Logika 10x/detik; gerak & gambar mengikuti layar (maks ±30 fps, turun otomatis kalau laptop sedang berat merender video).
    let lalu = performance.now(), sisaLogika = 0, sisaGambar = 0, jeda = 1000 / 30, berat = 0, raf = 0;
    const frame = (now: number) => {
      raf = requestAnimationFrame(frame);
      if (document.hidden) { lalu = now; return; }
      const dt = Math.min(250, now - lalu); lalu = now;
      sisaLogika += dt; sisaGambar += dt;
      while (sisaLogika >= 100) { eng.step(); sisaLogika -= 100; }
      if (sisaGambar < jeda) return;
      eng.advance(Math.min(0.25, sisaGambar / 1000)); sisaGambar = 0;
      const t0 = performance.now();
      eng.render(); if (!anim) draw();
      const lama = performance.now() - t0;
      berat = berat * 0.9 + lama * 0.1;
      jeda = eng.reduced ? 250 : berat > 14 ? 1000 / 12 : berat > 8 ? 1000 / 20 : 1000 / 30;
    };
    fit(); eng.step(); eng.render(); draw();
    raf = requestAnimationFrame(frame);
    const timer = 0;
    const ro = new ResizeObserver(() => { fit(); draw(); });
    ro.observe(el);

    const toBuf = (e: { clientX: number; clientY: number }) => {
      const r = cv.getBoundingClientRect(), c = cam.current;
      return [(e.clientX - r.left - c.x) / c.s, (e.clientY - r.top - c.y) / c.s] as const;
    };
    let drag: { x: number; y: number; cx: number; cy: number; moved: boolean } | null = null;
    const jari = new Map<number, { x: number; y: number }>();
    let cubit: { d: number; s: number; mx: number; my: number; cx: number; cy: number } | null = null;
    const down = (e: PointerEvent) => {
      jari.set(e.pointerId, { x: e.clientX, y: e.clientY });
      cv.setPointerCapture(e.pointerId);
      if (jari.size === 2) {
        const [a, b] = [...jari.values()], r = cv.getBoundingClientRect();
        cubit = { d: Math.hypot(a.x - b.x, a.y - b.y) || 1, s: cam.current.s, mx: (a.x + b.x) / 2 - r.left, my: (a.y + b.y) / 2 - r.top, cx: cam.current.x, cy: cam.current.y };
        drag = null; return;
      }
      drag = { x: e.clientX, y: e.clientY, cx: cam.current.x, cy: cam.current.y, moved: false };
    };
    const move = (e: PointerEvent) => {
      if (jari.has(e.pointerId)) jari.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (cubit && jari.size === 2) {
        const [a, b] = [...jari.values()], c = cam.current;
        const ns = Math.min(c.fit * 4, Math.max(c.fit * 0.5, cubit.s * (Math.hypot(a.x - b.x, a.y - b.y) / cubit.d)));
        c.x = cubit.mx - ((cubit.mx - cubit.cx) * ns) / cubit.s; c.y = cubit.my - ((cubit.my - cubit.cy) * ns) / cubit.s; c.s = ns; userZoomed = true; draw(); return;
      }
      if (drag) {
        const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (Math.hypot(dx, dy) > 4) drag.moved = true;
        if (drag.moved) { userZoomed = true; cam.current.x = drag.cx + dx; cam.current.y = drag.cy + dy; cv.style.cursor = "grabbing"; draw(); setTip(null); return; }
      }
      const [bx, by] = toBuf(e), hit = eng.hitAt(bx, by);
      eng.hoverId = hit?.id ?? null;
      cv.style.cursor = hit ? "pointer" : "grab";
      const r = el.getBoundingClientRect();
      setTip(hit ? { x: e.clientX - r.left, y: e.clientY - r.top, text: hit.label + (hit.id.startsWith("future:") ? " · belum dibuat" : "") } : null);
    };
    const up = (e: PointerEvent) => {
      jari.delete(e.pointerId);
      if (cubit) { if (jari.size < 2) cubit = null; drag = null; return; }
      const wasDrag = drag?.moved; drag = null; cv.style.cursor = "grab";
      if (wasDrag) return;
      const [bx, by] = toBuf(e), hit = eng.hitAt(bx, by);
      if (hit) openRef.current(hit.id);
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const c = cam.current, r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      const ns = Math.min(c.fit * 4, Math.max(c.fit * 0.5, c.s * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
      c.x = mx - ((mx - c.x) * ns) / c.s; c.y = my - ((my - c.y) * ns) / c.s; c.s = ns; userZoomed = true; draw();
    };
    const leave = () => { eng.hoverId = null; setTip(null); };
    const reset = () => { userZoomed = false; fit(); draw(); };
    const zoomBy = (f: number) => { const c = cam.current, mx = w / 2, my = h / 2, ns = Math.min(c.fit * 4, Math.max(c.fit * 0.5, c.s * f)); c.x = mx - ((mx - c.x) * ns) / c.s; c.y = my - ((my - c.y) * ns) / c.s; c.s = ns; userZoomed = true; draw(); };
    (el as unknown as { __zoom: (f: number) => void; __reset: () => void }).__zoom = zoomBy;
    // transisi zoom halus ke objek yang dibuka (dan kembali saat ditutup)
    const terbang = (ts: number, tx: number, ty: number) => {
      cancelAnimationFrame(anim);
      const c = cam.current, s0 = c.s, x0 = c.x, y0 = c.y, t0 = performance.now(), dur = eng.reduced ? 1 : 700;
      const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
      const langkah = (now: number) => {
        const k = Math.min(1, (now - t0) / dur), e = ease(k);
        c.s = s0 + (ts - s0) * e; c.x = x0 + (tx - x0) * e; c.y = y0 + (ty - y0) * e; draw();
        anim = k < 1 ? requestAnimationFrame(langkah) : 0;
      };
      anim = requestAnimationFrame(langkah);
    };
    api.current = {
      fokus: (id) => {
        const c = cam.current, L = w < 1024 ? 0 : ruang.current.kiri;
        if (!id) { userZoomed = false; const b = bingkai(); c.fit = b.s; terbang(b.s, b.x, b.y); return; }
        const p = eng.anchor(id);
        if (!p) return;
        const R = w < 700 ? 0 : Math.min(ruang.current.kanan, w * 0.6), vw = w - L - R, ts = Math.min(c.fit * 4, c.fit * (id.startsWith("agent:") || id === "founder" ? 2.3 : 1.8));
        userZoomed = true; terbang(ts, L + vw / 2 - p[0] * ts, h * 0.46 - p[1] * ts);
      },
    };
    (el as unknown as { __reset: () => void }).__reset = reset;

    cv.addEventListener("pointerdown", down); cv.addEventListener("pointermove", move); cv.addEventListener("pointerup", up); cv.addEventListener("pointercancel", up);
    cv.addEventListener("wheel", wheel, { passive: false }); cv.addEventListener("pointerleave", leave); cv.addEventListener("dblclick", reset);
    return () => {
      window.clearInterval(timer); cancelAnimationFrame(raf); ro.disconnect(); cancelAnimationFrame(anim);
      cv.removeEventListener("pointerdown", down); cv.removeEventListener("pointermove", move); cv.removeEventListener("pointerup", up); cv.removeEventListener("pointercancel", up);
      cv.removeEventListener("wheel", wheel); cv.removeEventListener("pointerleave", leave); cv.removeEventListener("dblclick", reset);
    };
  }, []);

  const zoom = (f: number) => (wrap.current as unknown as { __zoom?: (f: number) => void })?.__zoom?.(f);
  const reset = () => (wrap.current as unknown as { __reset?: () => void })?.__reset?.();

  return (
    <div ref={wrap} className="absolute inset-0 overflow-hidden">
      <canvas ref={canvas} className="absolute inset-0 size-full cursor-grab touch-none [image-rendering:pixelated]" role="img"
        aria-label="Kantor virtual Studio Yofamo. Pakai tombol di dok bawah untuk membuka setiap meja dan papan." />
      <div ref={overlay} className="pointer-events-none absolute inset-0" aria-hidden="true" />
      {tip && (
        <div className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[130%] whitespace-nowrap rounded-md border border-line bg-ink-800/95 px-2.5 py-1 text-[13px] text-ink-50 shadow-lg" style={{ left: tip.x, top: tip.y }}>
          {tip.text}
        </div>
      )}
      <div className="absolute right-3 bottom-24 z-10 flex flex-col overflow-hidden rounded-lg border border-line bg-ink-800/90 shadow-lg backdrop-blur max-md:bottom-[150px]">
        <button className="grid size-9 place-items-center font-pixel text-lg hover:bg-ink-700" onClick={() => zoom(1.25)} aria-label="Perbesar">+</button>
        <button className="grid size-9 place-items-center border-y border-line font-pixel text-lg hover:bg-ink-700" onClick={() => zoom(0.8)} aria-label="Perkecil">−</button>
        <button className="grid size-9 place-items-center font-pixel text-[11px] hover:bg-ink-700" onClick={reset} aria-label="Pas layar">FIT</button>
      </div>
    </div>
  );
}

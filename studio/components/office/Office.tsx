"use client";

import { useEffect, useRef, useState } from "react";
import type { StudioState } from "@/lib/types";
import { OfficeEngine } from "./engine";
import { BH, BW } from "./world";

interface Cam { s: number; x: number; y: number; fit: number }

const esc = (s: string) => s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]!);

export default function Office({ state, onOpen }: { state: StudioState | null; onOpen: (id: string) => void }) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const overlay = useRef<HTMLDivElement>(null);
  const engine = useRef<OfficeEngine | null>(null);
  const cam = useRef<Cam>({ s: 1, x: 0, y: 0, fit: 1 });
  const openRef = useRef(onOpen);
  const [tip, setTip] = useState<{ x: number; y: number; text: string } | null>(null);
  openRef.current = onOpen;

  useEffect(() => {
    if (engine.current) engine.current.state = state;
  }, [state]);

  useEffect(() => {
    const eng = new OfficeEngine();
    eng.reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    engine.current = eng;
    const cv = canvas.current!, ctx = cv.getContext("2d")!, el = wrap.current!, ov = overlay.current!;
    let w = 0, h = 0, dpr = 1, userZoomed = false;

    const fit = () => {
      const r = el.getBoundingClientRect();
      w = r.width; h = r.height; dpr = window.devicePixelRatio || 1;
      cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr);
      let f = Math.min(w / BW, (h - 8) / BH);
      if (w < 700) f = Math.max(f, Math.min((w * 1.7) / BW, (h * 0.62) / BH)); // HP: tampilkan lebih dekat, geser untuk melihat sisanya
      const c = cam.current;
      if (!userZoomed) { c.s = f; c.x = (w - BW * f) / 2; c.y = (h - BH * f) / 2 + 4; }
      c.fit = f;
    };
    const draw = () => {
      const c = cam.current;
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      const bg = ctx.createRadialGradient(cv.width / 2, cv.height * 0.45, 0, cv.width / 2, cv.height * 0.45, Math.max(cv.width, cv.height) * 0.7);
      bg.addColorStop(0, "#15284A"); bg.addColorStop(0.55, "#0D1A30"); bg.addColorStop(1, "#070E1B");
      ctx.fillStyle = bg; ctx.fillRect(0, 0, cv.width, cv.height);
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
          html += `<div class="bubble pointer-events-none absolute -translate-x-1/2 -translate-y-full whitespace-nowrap rounded-md border-2 border-[#1A2638] px-2 py-1 font-pixel text-[12px] leading-tight text-[#1A2638] shadow-[2px_2px_0_rgba(0,0,0,.35)] ${tone}" style="left:${x}px;top:${y}px">${esc(o.text)}</div>`;
        } else {
          html += `<div class="pointer-events-none absolute grid h-5 min-w-5 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-bad px-1.5 font-pixel text-xs text-white ring-2 ring-[#08121F] animate-pulse motion-reduce:animate-none" style="left:${x}px;top:${y}px">${esc(o.text)}</div>`;
        }
      }
      if (ov.dataset.html !== html) { ov.innerHTML = html; ov.dataset.html = html; }
    };
    const loop = () => { eng.step(); eng.render(); draw(); };

    fit(); loop();
    const timer = window.setInterval(() => { if (!document.hidden) loop(); }, 100);
    const ro = new ResizeObserver(() => { fit(); draw(); });
    ro.observe(el);

    const toBuf = (e: { clientX: number; clientY: number }) => {
      const r = cv.getBoundingClientRect(), c = cam.current;
      return [(e.clientX - r.left - c.x) / c.s, (e.clientY - r.top - c.y) / c.s] as const;
    };
    let drag: { x: number; y: number; cx: number; cy: number; moved: boolean } | null = null;
    const down = (e: PointerEvent) => { drag = { x: e.clientX, y: e.clientY, cx: cam.current.x, cy: cam.current.y, moved: false }; cv.setPointerCapture(e.pointerId); };
    const move = (e: PointerEvent) => {
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
      const wasDrag = drag?.moved; drag = null; cv.style.cursor = "grab";
      if (wasDrag) return;
      const [bx, by] = toBuf(e), hit = eng.hitAt(bx, by);
      if (hit) openRef.current(hit.id);
    };
    const wheel = (e: WheelEvent) => {
      e.preventDefault();
      const c = cam.current, r = cv.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
      const ns = Math.min(c.fit * 4, Math.max(c.fit * 0.85, c.s * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
      c.x = mx - ((mx - c.x) * ns) / c.s; c.y = my - ((my - c.y) * ns) / c.s; c.s = ns; userZoomed = true; draw();
    };
    const leave = () => { eng.hoverId = null; setTip(null); };
    const reset = () => { userZoomed = false; fit(); draw(); };
    const zoomBy = (f: number) => { const c = cam.current, mx = w / 2, my = h / 2, ns = Math.min(c.fit * 4, Math.max(c.fit * 0.85, c.s * f)); c.x = mx - ((mx - c.x) * ns) / c.s; c.y = my - ((my - c.y) * ns) / c.s; c.s = ns; userZoomed = true; draw(); };
    (el as unknown as { __zoom: (f: number) => void; __reset: () => void }).__zoom = zoomBy;
    (el as unknown as { __reset: () => void }).__reset = reset;

    cv.addEventListener("pointerdown", down); cv.addEventListener("pointermove", move); cv.addEventListener("pointerup", up);
    cv.addEventListener("wheel", wheel, { passive: false }); cv.addEventListener("pointerleave", leave); cv.addEventListener("dblclick", reset);
    return () => {
      window.clearInterval(timer); ro.disconnect();
      cv.removeEventListener("pointerdown", down); cv.removeEventListener("pointermove", move); cv.removeEventListener("pointerup", up);
      cv.removeEventListener("wheel", wheel); cv.removeEventListener("pointerleave", leave); cv.removeEventListener("dblclick", reset);
    };
  }, []);

  const zoom = (f: number) => (wrap.current as unknown as { __zoom?: (f: number) => void })?.__zoom?.(f);
  const reset = () => (wrap.current as unknown as { __reset?: () => void })?.__reset?.();

  return (
    <div ref={wrap} className="absolute inset-0 overflow-hidden">
      <canvas ref={canvas} className="absolute inset-0 size-full cursor-grab [image-rendering:pixelated]" role="img"
        aria-label="Kantor virtual Studio Yofamo. Pakai tombol di dok bawah untuk membuka setiap meja dan papan." />
      <div ref={overlay} className="pointer-events-none absolute inset-0" aria-hidden="true" />
      {tip && (
        <div className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-[130%] whitespace-nowrap rounded-md border border-line bg-ink-800/95 px-2.5 py-1 text-[13px] text-ink-50 shadow-lg" style={{ left: tip.x, top: tip.y }}>
          {tip.text}
        </div>
      )}
      <div className="absolute right-4 bottom-24 z-10 flex flex-col overflow-hidden rounded-lg border border-line bg-ink-800/90 shadow-lg backdrop-blur max-sm:bottom-28">
        <button className="grid size-9 place-items-center font-pixel text-lg hover:bg-ink-700" onClick={() => zoom(1.25)} aria-label="Perbesar">+</button>
        <button className="grid size-9 place-items-center border-y border-line font-pixel text-lg hover:bg-ink-700" onClick={() => zoom(0.8)} aria-label="Perkecil">−</button>
        <button className="grid size-9 place-items-center font-pixel text-[11px] hover:bg-ink-700" onClick={reset} aria-label="Pas layar">FIT</button>
      </div>
    </div>
  );
}

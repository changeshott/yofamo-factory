"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

export function Btn({ tone = "default", size = "md", className = "", ...p }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "default" | "primary" | "ghost" | "danger"; size?: "sm" | "md" }) {
  const tones = {
    default: "border-line bg-ink-700 hover:border-circuit",
    primary: "border-signal bg-signal text-[#24140A] font-bold hover:brightness-110",
    ghost: "border-line bg-transparent hover:border-circuit",
    danger: "border-bad/60 bg-bad/15 text-bad hover:bg-bad/25",
  };
  const sizes = { sm: "px-2.5 py-1.5 text-[13px]", md: "px-3.5 py-2 text-sm" };
  return <button {...p} className={`inline-flex items-center gap-2 rounded-lg border font-pixel leading-none transition disabled:cursor-not-allowed disabled:opacity-45 ${tones[tone]} ${sizes[size]} ${className}`} />;
}

export function H3({ children }: { children: ReactNode }) {
  return <h3 className="mt-6 mb-2 font-pixel text-[16px] font-bold tracking-wide first:mt-0">{children}</h3>;
}

export function Muted({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <p className={`text-sm text-muted ${className}`}>{children}</p>;
}

export function Pill({ children, tone = "default" }: { children: ReactNode; tone?: "default" | "running" | "ok" | "error" | "stopped" }) {
  const t = { default: "bg-ink-700 text-muted", running: "bg-signal/20 text-signal", ok: "bg-leaf/15 text-leaf", error: "bg-bad/15 text-bad", stopped: "bg-ink-600 text-muted" }[tone];
  return <span className={`inline-block rounded px-2 py-1 font-pixel text-xs leading-none ${t}`}>{children}</span>;
}

export function Copy({ label, text }: { label: string; text: string }) {
  return (
    <div className="mt-3">
      <h4 className="mb-1.5 font-pixel text-sm text-muted">{label}</h4>
      <div className="flex items-start gap-2">
        <div className="flex-1 whitespace-pre-wrap break-words rounded-md border border-line bg-ink-950 px-2.5 py-2 text-sm">{text}</div>
        <CopyBtn text={text} />
      </div>
    </div>
  );
}

export function CopyBtn({ text, label = "Salin" }: { text: string; label?: string }) {
  return (
    <Btn size="sm" onClick={async (e) => {
      const b = e.currentTarget, old = b.textContent;
      try { await navigator.clipboard.writeText(text); b.textContent = "Disalin"; } catch { b.textContent = "Gagal menyalin"; }
      setTimeout(() => (b.textContent = old), 1200);
    }}>{label}</Btn>
  );
}

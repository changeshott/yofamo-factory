"use client";
import { useEffect, useState } from "react";
import type { JadwalItem, StudioState } from "@/lib/types";

const GAYA: Record<JadwalItem["status"], { teks: string; cls: string }> = {
  tayang: { teks: "Tayang", cls: "bg-leaf/15 text-leaf ring-leaf/40" },
  terjadwal: { teks: "Terjadwal", cls: "bg-brand/15 text-brand-2 ring-brand/40" },
  dibuat: { teks: "Sedang dibuat", cls: "bg-signal/15 text-signal ring-signal/40 animate-pulse motion-reduce:animate-none" },
  kosong: { teks: "Kosong", cls: "bg-ink-700 text-muted ring-line/60" },
  terlewat: { teks: "Terlewat", cls: "bg-bad/10 text-bad ring-bad/40" },
};

/** "dalam 3 jam 20 mnt" dari waktu WIB "YYYY-MM-DD HH:MM". */
function hitungMundur(waktu: string, kini: number): string {
  const t = Date.parse(waktu.replace(" ", "T") + ":00+07:00") - kini;
  if (t <= 0) return "sekarang";
  const m = Math.round(t / 60000), j = Math.floor(m / 60), h = Math.floor(j / 24);
  if (h >= 1) return `dalam ${h} hari ${j % 24} jam`;
  if (j >= 1) return `dalam ${j} jam ${m % 60} mnt`;
  return `dalam ${m} mnt`;
}

function Gambar({ it }: { it: JadwalItem }) {
  if (it.slug && it.gambarUrl) {
    return <img src={it.gambarUrl} alt="" loading="lazy" className="h-[60px] w-[34px] shrink-0 rounded-md object-cover object-[70%_50%] ring-1 ring-[#FF4FA3]/50" />;
  }
  if (it.slug && it.gambar) {
    return <img src={`/api/media?slug=${it.slug}&file=${it.gambar}`} alt="" loading="lazy" className="h-[60px] w-[34px] shrink-0 rounded-md object-cover ring-1 ring-line/70" />;
  }
  return (
    <span className={`grid h-[60px] w-[34px] shrink-0 place-items-center rounded-md text-[15px] ring-1 ${it.status === "dibuat" ? "bg-signal/10 text-signal ring-signal/40" : "border border-dashed border-line/70 bg-ink-800/40 text-faint ring-transparent"}`} aria-hidden>
      {it.jenis === "panjang" ? "▶" : it.status === "dibuat" ? "⚙" : "+"}
    </span>
  );
}

function Baris({ it, open }: { it: JadwalItem; open: (id: string) => void }) {
  const g = GAYA[it.status];
  const judul = it.judul ?? (it.status === "dibuat" ? (it.jenis === "panjang" ? "Tim Ruang Animasi sedang membuat video panjang" : "Tim sedang membuat video untuk jam ini")
    : it.jenis === "panjang" ? "Slot video panjang · autopilot mengisi" : "Slot kosong · autopilot mengisi");
  const isi = (
    <>
      <span className="w-[42px] shrink-0 pt-0.5 font-pixel text-[15px] leading-none tabular-nums">{it.jam}</span>
      <Gambar it={it} />
      <span className="min-w-0 flex-1">
        <span className={`line-clamp-2 text-[12.5px] leading-snug ${it.judul ? "" : "text-muted"}`}>{judul}</span>
        <span className="mt-1 flex flex-wrap items-center gap-1">
          <span className={`rounded-full px-1.5 py-0.5 text-[10.5px] leading-none ring-1 ${g.cls}`}>{g.teks}</span>
          {it.jenis === "panjang" && <span className="rounded-full bg-[#FF4FA3]/15 px-1.5 py-0.5 text-[10.5px] leading-none text-[#FFC2E2] ring-1 ring-[#FF4FA3]/40">Video panjang</span>}
          {it.eksplorasi && !it.slug && <span className="text-[10.5px] text-faint" title="Jam baru yang sedang diuji">uji jam</span>}
        </span>
      </span>
    </>
  );
  const cls = "flex w-full items-start gap-2 rounded-xl p-1.5 text-left transition hover:bg-ink-700/70 focus-visible:outline-2 focus-visible:outline-brand";
  return it.url
    ? <a href={it.url} target="_blank" rel="noreferrer" className={cls} title="Buka di YouTube">{isi}</a>
    : <button onClick={() => open(it.jenis === "panjang" ? "animasi" : it.slug ? "galeri" : "agent:uli")} className={cls}>{isi}</button>;
}

/** Isi jadwal (dipakai sidebar kanan di desktop & panel di HP). */
export function JadwalIsi({ state, open, ringkas = false }: { state: StudioState; open: (id: string) => void; ringkas?: boolean }) {
  const J = state.jadwal;
  const [kini, setKini] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => setKini(Date.now()), 30_000); return () => clearInterval(t); }, []);
  if (!J) return <p className="p-3 text-sm text-muted">Jadwal tayang belum ada. Nyalakan autopilot di meja Uli untuk menghitung jam tayang terbaik.</p>;
  const siap = state.videos.filter((v) => v.status === "export" && !v.upload).length;
  const cek = state.videos.filter((v) => v.status === "draft").length;
  const hariIni = J.hari[0]?.tanggal ?? "";
  const lalu = J.baruTayang.filter((i) => i.tanggal < hariIni).slice(0, ringkas ? 2 : 3);
  return (
    <div className="flex flex-col gap-3">
      {J.berikut ? (
        <div className="rounded-xl border border-brand/40 bg-gradient-to-br from-brand/20 to-transparent p-2.5">
          <p className="font-pixel text-[11px] tracking-wide text-brand-2 uppercase">Tayang berikutnya</p>
          <p className="mt-1 font-pixel text-[20px] leading-none">{J.berikut.tanggal === hariIni ? "Hari ini" : J.hari.find((h) => h.tanggal === J.berikut!.tanggal)?.label ?? J.berikut.tanggal} · {J.berikut.jam}</p>
          <p className="mt-1 line-clamp-2 text-[12.5px] leading-snug">{J.berikut.judul}</p>
          <p className="mt-1 text-[11.5px] text-muted">{hitungMundur(J.berikut.waktu, kini)} · otomatis tayang di YouTube</p>
        </div>
      ) : (
        <div className="rounded-xl border border-line/70 bg-ink-800/60 p-2.5 text-[12.5px] text-muted">Belum ada video terjadwal. {J.autopilotAktif ? "Autopilot sedang mengisi." : "Autopilot menyala saat Studio dibuka."}</div>
      )}
      {J.hari.map((h) => {
        const terisi = h.item.filter((i) => i.slug).length;
        if (!h.item.length) return null;
        return (
          <section key={h.tanggal} aria-label={`Jadwal ${h.label}`}>
            <h3 className="mb-1 flex items-baseline justify-between px-1.5 font-pixel text-[12px] tracking-wide text-muted uppercase">
              <span>{h.label}</span><span className="text-[11px] normal-case">{terisi}/{h.item.length} terisi</span>
            </h3>
            <ul className="space-y-0.5">{h.item.map((it) => <li key={it.waktu + (it.slug ?? "")}><Baris it={it} open={open} /></li>)}</ul>
          </section>
        );
      })}
      {lalu.length > 0 && (
        <section aria-label="Baru tayang">
          <h3 className="mb-1 px-1.5 font-pixel text-[12px] tracking-wide text-muted uppercase">Baru tayang</h3>
          <ul className="space-y-0.5 opacity-80">{lalu.map((it) => <li key={it.waktu + (it.slug ?? "")}><Baris it={it} open={open} /></li>)}</ul>
        </section>
      )}
      <div className="grid grid-cols-2 gap-1.5 text-center">
        <button onClick={() => open("agent:uli")} className="rounded-lg bg-ink-700/70 px-2 py-1.5 hover:bg-ink-600"><b className="block font-pixel text-[16px] leading-none">{siap}</b><span className="text-[11px] text-muted">siap upload</span></button>
        <button onClick={() => open("founder")} className="rounded-lg bg-ink-700/70 px-2 py-1.5 hover:bg-ink-600"><b className="block font-pixel text-[16px] leading-none">{cek}</b><span className="text-[11px] text-muted">menunggu dicek</span></button>
      </div>
    </div>
  );
}

/** Sidebar kanan (desktop): jadwal tayang & posting. */
export function JadwalSidebar({ state, open, lipat, setLipat }: { state: StudioState; open: (id: string) => void; lipat: boolean; setLipat: (v: boolean) => void }) {
  const J = state.jadwal;
  return (
    <aside aria-label="Jadwal tayang" className={`pointer-events-auto flex min-h-0 flex-col overflow-hidden rounded-2xl border border-line/70 bg-ink-800/75 shadow-[0_18px_50px_rgba(0,0,0,.4)] backdrop-blur-xl transition-[width] duration-300 ${lipat ? "w-[64px]" : "w-[280px]"}`}>
      <div className={`flex items-center gap-2 border-b border-line/60 px-3 py-2.5 ${lipat ? "justify-center" : ""}`}>
        <button onClick={() => setLipat(!lipat)} aria-label={lipat ? "Lebarkan jadwal" : "Ciutkan jadwal"} className="grid size-7 place-items-center rounded-lg text-muted hover:bg-ink-700 hover:text-ink-50">
          <svg viewBox="0 0 24 24" className={`size-4 transition-transform ${lipat ? "" : "rotate-180"}`} fill="currentColor" aria-hidden><path d="M15.4 7.4 14 6l-6 6 6 6 1.4-1.4L10.8 12z" /></svg>
        </button>
        {!lipat && <h2 className="font-pixel text-sm tracking-wide text-muted">Jadwal tayang</h2>}
        {!lipat && state.jadwal?.autopilotAktif && <span className="ml-auto rounded-full bg-leaf/15 px-2 py-0.5 text-[10.5px] text-leaf ring-1 ring-leaf/40">autopilot</span>}
      </div>
      {lipat ? (
        <ul className="tanpa-scroll flex flex-1 flex-col items-center gap-2 overflow-y-auto py-2">
          {(J?.hari ?? []).flatMap((h) => h.item).filter((i) => i.status !== "tayang").slice(0, 8).map((it) => (
            <li key={it.waktu + (it.slug ?? "")} title={`${it.tanggal} ${it.jam} · ${it.judul ?? "kosong"}`} className="flex flex-col items-center gap-1">
              <Gambar it={it} />
              <span className="font-pixel text-[11px] leading-none tabular-nums">{it.jam}</span>
            </li>))}
        </ul>
      ) : (
        <div className="tanpa-scroll min-h-0 flex-1 overflow-y-auto p-2.5"><JadwalIsi state={state} open={open} /></div>
      )}
    </aside>
  );
}

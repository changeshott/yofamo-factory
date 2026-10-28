import "server-only";
import { NextResponse } from "next/server";

const ALLOWED = new Set(["127.0.0.1:3210", "localhost:3210"]);

/** Studio hanya untuk laptop sendiri: tolak permintaan tulis dari situs lain. */
export function guard(req: Request): NextResponse | null {
  const host = req.headers.get("host") ?? "";
  const origin = req.headers.get("origin");
  const originHost = origin ? origin.replace(/^https?:\/\//, "") : null;
  if (!ALLOWED.has(host) || (originHost && !ALLOWED.has(originHost)) || req.headers.get("x-yofamo") !== "1") {
    return NextResponse.json({ ok: false, message: "Permintaan ditolak." }, { status: 403 });
  }
  return null;
}

export const json = (data: unknown, status = 200) => NextResponse.json(data, { status, headers: { "Cache-Control": "no-store" } });

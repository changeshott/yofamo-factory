import fs from "node:fs";
import path from "node:path";
import { json } from "@/lib/server/guard";
import { P, SLUG, listFiles, sizeOf } from "@/lib/server/project";

export const dynamic = "force-dynamic";

/** Ringkasan semua hasil karyawan + ukurannya, untuk panel Kelola hasil. */
export async function GET() {
  const vids = (fs.existsSync(P.videos) ? fs.readdirSync(P.videos) : []).filter((d) => SLUG.test(d))
    .map((slug) => ({ slug, bytes: sizeOf(path.join(P.videos, slug)) }));
  return json({
    videos: vids,
    logs: listFiles(P.logs, ".txt", 500).map((f) => ({ ...f, bytes: sizeOf(path.join(P.logs, f.name)) })),
    laporan: listFiles(P.insights, ".md", 200, true),
    cache: sizeOf(P.cache),
    total: vids.reduce((n, v) => n + v.bytes, 0) + sizeOf(P.cache) + sizeOf(P.logs) + sizeOf(P.produksi),
  });
}

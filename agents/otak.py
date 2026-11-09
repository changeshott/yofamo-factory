#!/usr/bin/env python3
"""Otak project Yofamo — ingatan ringkas supaya Claude & agent tidak membaca ulang project dari awal (hemat token).

    python agents/otak.py perbarui        # tulis otak/indeks-kode.md (dari kode) + otak/data/status.md (keadaan laptop saat ini)
    python agents/otak.py perbarui --data # hanya otak/data/status.md (dipanggil otomatis produser, produser_panjang, kumpul)
    python agents/otak.py cek             # pastikan otak AKURAT: semua path yang disebut ada, indeks sesuai kode,
                                          # catatan tidak tertinggal dari perubahan kode (keluar 1 kalau ada path/indeks salah)

Bagian otak:
- tulisan tangan (Claude memperbarui setiap kali mengubah sesuatu): otak/PETA.md, alur-*.md, keputusan.md, progres.md, ...
- dibuat script ini (tanpa token, tidak pernah dikarang): otak/indeks-kode.md (di-commit), otak/data/status.md (tidak di-commit).
Tidak membaca .env atau rahasia/.
"""
from __future__ import annotations

import ast
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OTAK = ROOT / "otak"
INDEKS = OTAK / "indeks-kode.md"
DATA = OTAK / "data" / "status.md"
# folder yang isinya dibuat saat produksi (tidak ada di repo bersih) → path di dalamnya tidak dicek keberadaannya
RUNTIME = ("produksi/", "insights/", "videos/", "panjang/", "logs/", "cache/", "rahasia/", "otak/data/", "musik/", "sfx/",
           "milik-saya/", "suara-khas/", ".venv-suara/", "node_modules/", "state.db", ".env", "bible/maskot/", "fonts/",
           # path relatif di dalam folder SATU video (videos/<slug>/ atau panjang/<slug>/)
           "aset/", "export/", "footage/", "media/", "suara/", "adegan/", "hf/", "thumbnail/", "naskah.json", "ide.json")
KODE = ("agents", ".claude/skills", "studio/app", "studio/lib", "studio/components", "bible/channel-bible.md", "bible/panjang-bible.md")


def rj(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}


def ringkas_doc(p: Path) -> str:
    try:
        d = ast.get_docstring(ast.parse(p.read_text(encoding="utf-8"))) or ""
    except (OSError, SyntaxError, ValueError):
        return ""
    baris = d.strip().splitlines()
    return baris[0].strip() if baris else ""


def skill_desc(p: Path) -> str:
    try:
        m = re.search(r"^description:\s*(.+)$", p.read_text(encoding="utf-8"), re.M)
    except OSError:
        return ""
    return m.group(1).strip() if m else ""


def buat_indeks() -> str:
    """Daftar SEMUA script, skill, rute Studio & file aturan — dibuat dari kode, jadi selalu benar."""
    b = ["# Indeks kode (DIBUAT OTOMATIS — jangan diedit tangan)", "",
         "Dibuat `python agents/otak.py perbarui` dari kode saat ini: baris pertama docstring tiap script + jumlah baris.",
         "Pakai untuk menemukan file yang tepat tanpa menjelajah folder. Isi lengkap tetap harus dibaca sebelum mengedit.", ""]
    grup: dict[str, list[Path]] = {}
    for p in sorted((ROOT / "agents").rglob("*.py")):
        if "__pycache__" in p.parts:
            continue
        rel = p.relative_to(ROOT)
        grup.setdefault(str(rel.parent).replace("\\", "/"), []).append(p)
    for folder, files in grup.items():
        b += [f"## {folder}/", "", "| File | Baris | Isi |", "|---|---|---|"]
        for p in files:
            n = sum(1 for _ in p.open(encoding="utf-8", errors="replace"))
            b.append(f"| `{p.relative_to(ROOT).as_posix()}` | {n} | {ringkas_doc(p).replace('|', '/')} |")
        b.append("")
    b += ["## Skill Claude (`.claude/skills/<nama>/SKILL.md`)", "", "| Skill | Isi |", "|---|---|"]
    for p in sorted((ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        b.append(f"| `/{p.parent.name}` | {skill_desc(p)[:220].replace('|', '/')} |")
    b += ["", "## Studio (Next.js, `studio/`)", "", "Rute API (`studio/app/api/<nama>/route.ts`): "
          + ", ".join(f"`{p.parent.name}`" for p in sorted((ROOT / "studio" / "app" / "api").glob("*/route.ts"))) + ".", ""]
    for d in ("studio/components", "studio/lib", "studio/lib/server"):
        fs = sorted(x.relative_to(ROOT).as_posix() for x in (ROOT / d).glob("*.ts*")) if (ROOT / d).is_dir() else []
        if fs:
            b.append(f"- `{d}/`: " + ", ".join(f"`{Path(f).name}`" for f in fs))
    b += ["", "## Aturan & gaya (`bible/`)", ""]
    for p in sorted((ROOT / "bible").glob("*")):
        if p.is_file():
            b.append(f"- `{p.relative_to(ROOT).as_posix()}`")
    return "\n".join(b) + "\n"


# ------------------------------------------------------------------ data keadaan laptop (tidak di-commit)
def status_shorts() -> dict[str, list[str]]:
    db = ROOT / "state.db"
    out: dict[str, list[str]] = {}
    if not db.exists():
        return out
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        kol = [r[1] for r in con.execute("PRAGMA table_info(videos)")]
        judul = next((k for k in ("judul_kerja", "judul", "title") if k in kol), None)
        q = f"SELECT slug, status{', ' + judul if judul else ''} FROM videos ORDER BY slug DESC"
        for r in con.execute(q):
            out.setdefault(r[1], []).append(f"{r[0]}" + (f" — {r[2]}" if judul and r[2] else ""))
        con.close()
    except sqlite3.Error as err:
        out["(gagal membaca state.db)"] = [str(err)[:80]]
    return out


def status_panjang() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for f in sorted((ROOT / "panjang").glob("*/status.json"), reverse=True):
        st = rj(f).get("status") or "?"
        up = rj(f.parent / "export" / "upload.json")
        judul = rj(f.parent / "naskah.json").get("judul") or rj(f.parent / "ide.json").get("judul_kerja") or ""
        tanda = " (upload dibatalkan)" if up.get("dibatalkan") else (" (sudah di YouTube)" if up.get("videoId") else "")
        out.setdefault(st, []).append(f"{f.parent.name}{' — ' + judul if judul else ''}{tanda}")
    return out


def buat_data() -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    b = [f"# Keadaan pabrik saat ini (DIBUAT OTOMATIS {now})", "",
         "Dari file di laptop (state.db, panjang/*/status.json, produksi/, insights/raw/). Tidak di-commit. Angka di sini tidak dikarang;",
         "kalau perlu angka lebih rinci, buka file sumber yang disebut.", ""]
    s = status_shorts()
    b += ["## Shorts (state.db)", ""]
    if s:
        for st, vs in s.items():
            b.append(f"- **{st}** ({len(vs)}): " + "; ".join(vs[:6]) + (" …" if len(vs) > 6 else ""))
    else:
        b.append("- belum ada state.db")
    p = status_panjang()
    b += ["", "## Video panjang (panjang/*/status.json)", ""]
    b += [f"- **{st}** ({len(vs)}): " + "; ".join(vs[:5]) + (" …" if len(vs) > 5 else "") for st, vs in p.items()] or ["- belum ada"]
    b += ["", "## Autopilot", ""]
    for nama, f in (("Shorts", ROOT / "bible" / "autopilot.json"),):
        c = rj(f)
        if c:
            pj = c.get("panjang") or {}
            b.append(f"- Pengaturan {nama}: aktif={c.get('aktif')}, video_per_hari={c.get('video_per_hari')}, setujui_otomatis={c.get('setujui_otomatis')}, "
                     f"skor_qc_min={c.get('skor_qc_min')}; panjang: aktif={pj.get('aktif')}, video_per_hari={pj.get('video_per_hari')}, jam={pj.get('jam')}")
    for nama, f in (("Shorts", ROOT / "produksi" / "autopilot.json"), ("panjang", ROOT / "produksi" / "autopilot-panjang.json")):
        st = rj(f)
        slot = st.get("slot") or {}
        if slot:
            akhir = sorted(slot.items())[-6:]
            b.append(f"- Slot {nama} terakhir: " + "; ".join(f"{k} {v.get('status')} {v.get('slug') or ''}".strip() for k, v in akhir))
    b += ["", "## Token Claude per video (produksi/token-log.jsonl)", ""]
    try:
        sys.path.insert(0, str(ROOT / "agents"))
        import pemakaian
        r = pemakaian.ringkas()
        for jenis, x in (r.get("rata_per_video") or {}).items():
            b.append(f"- {jenis}: rata-rata {pemakaian.angka(x['total'])} token/video dari {x['video']} video (setara API ${x['biaya_usd']})")
        top = [x for x in r.get("per_langkah") or [] if x["kali"] >= 1][:6]
        if top:
            b.append("- langkah terboros: " + "; ".join(f"{x['jenis']} {x['langkah']} {pemakaian.angka(x['rata'])}" for x in top))
        if not r.get("rata_per_video"):
            b.append("- data belum cukup")
    except Exception as err:  # noqa: BLE001
        b.append(f"- tidak terbaca: {str(err)[:80]}")
    b += ["", "## Data Steve terbaru (insights/raw/)", ""]
    raw = ROOT / "insights" / "raw"
    for pola, ket in (("analisa-*.md", "brief analisa (baca ini, bukan JSON mentah)"), ("analitik-*.json", "retensi YouTube Analytics"),
                      ("komentar-*.json", "komentar"), ("pasar-*.json", "radar pasar"), ("retensi-panjang-*.json", "retensi video panjang")):
        fs = sorted(raw.glob(pola)) if raw.is_dir() else []
        b.append(f"- {ket}: `{fs[-1].relative_to(ROOT).as_posix()}`" if fs else f"- {ket}: belum ada")
    snaps = sorted(f for f in raw.glob("20*.json")) if raw.is_dir() else []
    if snaps:
        d = rj(snaps[-1])
        ch = d.get("channel") or {}
        b.append(f"- snapshot statistik: `{snaps[-1].relative_to(ROOT).as_posix()}` — subscriber {ch.get('subscribers', ch.get('subscriberCount', '-'))}, "
                 f"{len(d.get('videos') or [])} video")
    laporan = sorted((ROOT / "insights").glob("20*-W*.md"))
    if laporan:
        b.append(f"- laporan mingguan terbaru: `{laporan[-1].relative_to(ROOT).as_posix()}`")
    return "\n".join(b) + "\n"


# ------------------------------------------------------------------ pemeriksa akurasi
def path_disebut(teks: str) -> set[str]:
    out = set()
    for m in re.findall(r"`([^`\s]+)`", teks):
        m = m.strip().rstrip(".,:;")
        if any(c in m for c in "<>*{}$|") or "YYYY" in m or m.startswith(("-", "/", "http")) or "/" not in m:
            continue
        if not re.search(r"\.(py|md|json|ts|tsx|html|bat|vbs|ps1|sh|txt|css)$|/$", m):
            continue
        out.add(m)
    return out


def waktu_git(paths: list[str]) -> int:
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%ct", "--", *paths], cwd=ROOT, capture_output=True, text=True, timeout=30)
        return int(r.stdout.strip() or 0)
    except (OSError, ValueError, subprocess.SubprocessError):
        return 0


def cek() -> int:
    salah, peringatan = [], []
    docs = sorted(OTAK.glob("*.md")) + [ROOT / "AGENTS.md"]
    for f in docs:
        if f == INDEKS or not f.exists():
            continue
        for p in sorted(path_disebut(f.read_text(encoding="utf-8"))):
            if p.startswith(RUNTIME):
                continue
            if not (ROOT / p.rstrip("/")).exists():
                salah.append(f"{f.relative_to(ROOT).as_posix()}: menyebut `{p}` yang tidak ada")
    if not INDEKS.exists() or INDEKS.read_text(encoding="utf-8") != buat_indeks():
        salah.append("otak/indeks-kode.md tidak sesuai kode saat ini → jalankan: python agents/otak.py perbarui")
    for wajib in ("PETA.md", "progres.md", "keputusan.md"):
        if not (OTAK / wajib).exists():
            salah.append(f"otak/{wajib} belum ada")
    t_kode, t_otak = waktu_git(list(KODE)), waktu_git(["otak/progres.md"])
    if t_kode and t_otak and t_kode > t_otak:
        peringatan.append("kode di-commit SETELAH otak/progres.md terakhir diperbarui → perbarui progres.md (dan file alur yang terkait)")
    for s in salah:
        print(f"SALAH  {s}")
    for s in peringatan:
        print(f"PERINGATAN  {s}")
    if not salah and not peringatan:
        print("otak OK: semua path benar, indeks sesuai kode, catatan tidak tertinggal")
    return 1 if salah else 0


def main() -> None:
    for s_ in (sys.stdout,):
        try:
            s_.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    perintah = sys.argv[1] if len(sys.argv) > 1 else "cek"
    if perintah == "perbarui":
        (OTAK / "data").mkdir(parents=True, exist_ok=True)
        if "--data" not in sys.argv:
            INDEKS.write_text(buat_indeks(), encoding="utf-8")
            print(f"[otak] {INDEKS.relative_to(ROOT).as_posix()} diperbarui")
        DATA.write_text(buat_data(), encoding="utf-8")
        print(f"[otak] {DATA.relative_to(ROOT).as_posix()} diperbarui")
    elif perintah == "cek":
        sys.exit(cek())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()

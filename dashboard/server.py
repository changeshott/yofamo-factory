#!/usr/bin/env python3
"""Yofamo Control Room — halaman kontrol lokal untuk pabrik Shorts.

Jalankan dari root project:
    python dashboard/server.py
Lalu buka http://127.0.0.1:8765 (otomatis terbuka).

Hanya bisa diakses dari komputer ini (127.0.0.1). Hanya menjalankan
perintah yang sudah terdaftar di JOBS, tidak menerima perintah bebas.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "agents"))
import pabrik  # noqa: E402  (antrean video, state.db)

HERE = Path(__file__).resolve().parent
HOST, PORT = "127.0.0.1", 8765
RAW_DIR = ROOT / "insights" / "raw"
INSIGHTS = ROOT / "insights"
LOGS = ROOT / "logs"
BIBLE = ROOT / "bible" / "channel-bible.md"
SKILLS = ROOT / ".claude" / "skills"

# Urutan pabrik. "skill" = nama folder di .claude/skills (status dihitung dari situ).
PIPELINE = [
    {"key": "steve-analis", "name": "Steve", "role": "Analis statistik"},
    {"key": "ide-riset", "name": "Nova", "role": "Ide + fakta bersumber"},
    {"key": "penulis", "name": "Raka", "role": "Naskah, judul, tag"},
    {"key": "suara", "name": "Suara", "role": "TTS + timing kata"},
    {"key": "aset", "name": "Pencari aset", "role": "Klip berlisensi"},
    {"key": "editor-capcut", "name": "Editor CapCut", "role": "Tulis file draft"},
    {"key": "upload", "name": "Upload", "role": "Terbit terjadwal"},
]

STEVE_TOOLS = [
    "Bash(python agents/steve/fetch_stats.py *)", "Bash(python agents/steve/fetch_stats.py)",
    "Bash(python3 agents/steve/fetch_stats.py *)", "Bash(python3 agents/steve/fetch_stats.py)",
    "PowerShell(python agents/steve/fetch_stats.py *)", "PowerShell(python agents/steve/fetch_stats.py)",
    "Read", "Write", "Glob", "Grep",
]


def tools_for(*scripts: str) -> list[str]:
    out = ["Read", "Write", "Glob", "Grep"]
    for sc in scripts:
        for py in ("python", "python3"):
            out += [f"Bash({py} {sc} *)", f"Bash({py} {sc})"]
        out += [f"PowerShell(python {sc} *)", f"PowerShell(python {sc})"]
    return out


IDE_TOOLS = tools_for("agents/pabrik.py") + ["WebSearch", "WebFetch"]
PENULIS_TOOLS = tools_for("agents/pabrik.py", "agents/penulis/cek_naskah.py")
SLUG = re.compile(r"^[a-z0-9-]{3,80}$")


def claude_cmd(prompt: str, tools: list[str]) -> list[str] | str:
    claude = shutil.which("claude")
    if not claude:
        return "Perintah 'claude' tidak ditemukan. Install Claude Code CLI lalu buka ulang halaman ini."
    return [claude, "-p", prompt, "--model", "sonnet", "--max-turns", "60", "--allowedTools", *tools]


def job_command(job: str, arg: str = "") -> list[str] | str:
    """Kembalikan argumen perintah, atau string pesan error."""
    if job == "fetch":
        return [sys.executable, str(ROOT / "agents" / "steve" / "fetch_stats.py")]
    if job == "check":
        return [sys.executable, str(ROOT / "agents" / "steve" / "fetch_stats.py"), "--check"]
    if job == "steve":
        return claude_cmd("/steve-analis", STEVE_TOOLS)
    if job == "ide":
        theme = re.sub(r"[^\w\s,.\-]", "", arg, flags=re.UNICODE).strip()[:120]
        return claude_cmd(f"/ide-riset {theme}".strip(), IDE_TOOLS)
    if job == "penulis":
        v = pabrik.get(arg) if SLUG.match(arg or "") else None
        if not v:
            return "Video tidak ditemukan."
        if v["status"] != "disetujui":
            return "Hanya ide berstatus disetujui yang bisa ditulis naskahnya."
        return claude_cmd(f"/penulis {arg}", PENULIS_TOOLS)
    return f"Tugas tidak dikenal: {job}"


JOB_LABELS = {"fetch": "Ambil data", "check": "Cek koneksi", "steve": "Steve",
              "ide": "Nova mencari ide", "penulis": "Raka menulis naskah"}

_lock = threading.Lock()
_current: dict = {"job": None, "arg": None, "status": "idle", "started": None, "finished": None,
                  "log": None, "exit": None}


def run_job(job: str, argv: list[str], log_path: Path) -> None:
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"# {JOB_LABELS.get(job, job)} — {datetime.now():%Y-%m-%d %H:%M}\n\n")
        log.flush()
        try:
            proc = subprocess.run(argv, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, timeout=1800)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            log.write("\n[dashboard] Dihentikan: lebih dari 30 menit.\n")
            code = -1
        except OSError as err:
            log.write(f"\n[dashboard] Gagal menjalankan: {err}\n")
            code = -1
    with _lock:
        _current.update(status="ok" if code == 0 else "error", exit=code,
                        finished=datetime.now().isoformat(timespec="seconds"))


def start_job(job: str, arg: str = "") -> tuple[bool, str]:
    argv = job_command(job, arg)
    if isinstance(argv, str):
        return False, argv
    with _lock:
        if _current["status"] == "running":
            return False, f"Masih ada tugas berjalan: {JOB_LABELS.get(_current['job'], _current['job'])}."
        LOGS.mkdir(exist_ok=True)
        log_path = LOGS / f"{job}-{datetime.now():%Y-%m-%d_%H%M%S}.txt"
        _current.update(job=job, arg=arg or None, status="running", exit=None, finished=None,
                        started=datetime.now().isoformat(timespec="seconds"),
                        log=log_path.name)
    threading.Thread(target=run_job, args=(job, argv, log_path), daemon=True).start()
    return True, "Dimulai."


def read_tail(path: Path, limit: int = 12000) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    return text[-limit:]


def latest_snapshot() -> dict | None:
    files = sorted(RAW_DIR.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except ValueError:
        return None


def snapshot_history() -> list[dict]:
    out = []
    for f in sorted(RAW_DIR.glob("*.json"))[-26:]:
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            out.append({"date": d["snapshot_date"], "subscribers": d["channel"]["subscribers"],
                        "median": d["summary"]["median_views"]})
        except (ValueError, KeyError):
            continue
    return out


def report_list() -> list[dict]:
    files = sorted(INSIGHTS.glob("*.md"), reverse=True)
    return [{"name": f.name, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes")}
            for f in files]


def agent_list() -> list[dict]:
    return [{**a, "ready": (SKILLS / a["key"] / "SKILL.md").exists()} for a in PIPELINE]


def last_logs() -> list[dict]:
    files = sorted(LOGS.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)[:15]
    return [{"name": f.name, "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="minutes")}
            for f in files]


SAFE_NAME = re.compile(r"^[\w.\-]+$")

# Perubahan status yang boleh dilakukan Zona dari halaman.
MANUAL_MOVES = {
    "ide": {"disetujui", "ditolak"},
    "ditolak": {"ide"},
    "naskah": {"disetujui", "export", "terbit"},
    "disetujui": {"ide"},
    "export": {"terbit"},
}


def video_list() -> list[dict]:
    out = []
    for v in pabrik.all_videos():
        out.append({**v, "label": pabrik.STATUS_LABEL.get(v["status"], v["status"]),
                    "idea": pabrik.read_json(v["slug"], "idea.json"),
                    "script": pabrik.read_json(v["slug"], "script.json"),
                    "moves": sorted(MANUAL_MOVES.get(v["status"], set()))})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "YofamoControlRoom/1.0"

    def log_message(self, fmt, *args):  # tenang di terminal
        pass

    # ---- helpers
    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, ctype: str):
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def same_origin(self) -> bool:
        host_ok = self.headers.get("Host", "") in (f"{HOST}:{PORT}", f"localhost:{PORT}")
        origin = self.headers.get("Origin")
        origin_ok = origin in (None, f"http://{HOST}:{PORT}", f"http://localhost:{PORT}")
        return host_ok and origin_ok and self.headers.get("X-Yofamo") == "1"

    def read_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or 0)
        if length > 2_000_000:
            return {}
        try:
            return json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            return {}

    # ---- routes
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        if self.headers.get("Host", "") not in (f"{HOST}:{PORT}", f"localhost:{PORT}"):
            return self.send_json({"error": "host tidak diizinkan"}, HTTPStatus.FORBIDDEN)

        if url.path in ("/", "/index.html"):
            return self.send_file(HERE / "index.html", "text/html; charset=utf-8")
        if url.path == "/api/state":
            with _lock:
                job = dict(_current)
            return self.send_json({
                "snapshot": latest_snapshot(),
                "history": snapshot_history(),
                "reports": report_list(),
                "agents": agent_list(),
                "logs": last_logs(),
                "videos": video_list(),
                "job": job,
                "env_ready": (ROOT / ".env").exists(),
                "claude_ready": shutil.which("claude") is not None,
            })
        if url.path == "/api/report":
            name = (q.get("name") or [""])[0]
            path = INSIGHTS / name
            if not SAFE_NAME.match(name) or not name.endswith(".md") or not path.exists():
                return self.send_json({"error": "laporan tidak ditemukan"}, HTTPStatus.NOT_FOUND)
            return self.send_json({"name": name, "text": path.read_text(encoding="utf-8-sig")})
        if url.path == "/api/log":
            name = (q.get("name") or [""])[0]
            path = LOGS / name
            if not SAFE_NAME.match(name) or not name.endswith(".txt"):
                return self.send_json({"error": "log tidak ditemukan"}, HTTPStatus.NOT_FOUND)
            return self.send_json({"name": name, "text": read_tail(path)})
        if url.path == "/api/bible":
            return self.send_json({"text": BIBLE.read_text(encoding="utf-8-sig") if BIBLE.exists() else ""})
        return self.send_json({"error": "tidak ada"}, HTTPStatus.NOT_FOUND)

    def do_POST(self):
        if not self.same_origin():
            return self.send_json({"error": "permintaan ditolak"}, HTTPStatus.FORBIDDEN)
        url = urlparse(self.path)
        body = self.read_body()

        if url.path == "/api/run":
            ok, msg = start_job(str(body.get("job", "")), str(body.get("arg", "") or ""))
            return self.send_json({"ok": ok, "message": msg},
                                  HTTPStatus.OK if ok else HTTPStatus.CONFLICT)
        if url.path == "/api/video/status":
            slug, to = str(body.get("slug", "")), str(body.get("status", ""))
            v = pabrik.get(slug) if SLUG.match(slug) else None
            if not v:
                return self.send_json({"ok": False, "message": "Video tidak ditemukan."}, HTTPStatus.NOT_FOUND)
            if to not in MANUAL_MOVES.get(v["status"], set()):
                return self.send_json({"ok": False, "message": f"Tidak bisa mengubah {v['status']} menjadi {to}."},
                                      HTTPStatus.CONFLICT)
            pabrik.set_status(slug, to, "diubah dari Control Room")
            return self.send_json({"ok": True, "message": pabrik.STATUS_LABEL.get(to, to)})
        if url.path == "/api/bible":
            text = body.get("text")
            if not isinstance(text, str) or not text.strip():
                return self.send_json({"ok": False, "message": "Isi bible kosong, tidak disimpan."},
                                      HTTPStatus.BAD_REQUEST)
            if BIBLE.exists():  # simpan versi lama dulu
                hist = BIBLE.parent / ".history"
                hist.mkdir(exist_ok=True)
                shutil.copy2(BIBLE, hist / f"channel-bible-{datetime.now():%Y%m%d-%H%M%S}.md")
            BIBLE.write_text(text, encoding="utf-8")
            return self.send_json({"ok": True, "message": "Bible disimpan."})
        return self.send_json({"error": "tidak ada"}, HTTPStatus.NOT_FOUND)


def main() -> None:
    try:
        httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        sys.exit(f"[dashboard] Port {PORT} sudah dipakai. Mungkin halaman ini sudah berjalan: http://{HOST}:{PORT}")
    url = f"http://{HOST}:{PORT}"
    print(f"[dashboard] Yofamo Control Room berjalan di {url}  (tutup jendela ini untuk berhenti)")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[dashboard] Berhenti.")


if __name__ == "__main__":
    main()

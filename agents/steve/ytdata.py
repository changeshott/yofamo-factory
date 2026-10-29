"""Alat bersama pengumpul data Steve: baca .env, panggil YouTube Data API (API key), snapshot terbaru."""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "insights" / "raw"
API = "https://www.googleapis.com/youtube/v3"


def load_env() -> None:
    f = ROOT / ".env"
    if f.exists():
        for line in f.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


class YtError(Exception):
    def __init__(self, code: int, reason: str):
        super().__init__(f"{code}: {reason}")
        self.code, self.reason = code, reason


def get(endpoint: str, params: dict, key: str) -> dict:
    url = f"{API}/{endpoint}?" + urllib.parse.urlencode({**params, "key": key})
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")
        try:
            reason = json.loads(body)["error"]["errors"][0].get("reason") or json.loads(body)["error"]["message"]
        except (ValueError, KeyError, IndexError):
            reason = body[:200]
        raise YtError(err.code, reason) from None


def snapshots() -> list[Path]:
    return sorted(p for p in RAW.glob("*.json") if re.fullmatch(r"\d{4}-\d\d-\d\d", p.stem))


def latest(prefix: str = "") -> Path | None:
    files = snapshots() if not prefix else sorted(RAW.glob(f"{prefix}-*.json"))
    return files[-1] if files else None


def read(p: Path | None) -> dict:
    if not p:
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return {}

#!/usr/bin/env python3
"""Board CB — capture reader.

Every artefact published by this board is derived from the gzip bytes committed under
data/session-3a7bd9bb/capture/<stamp>/ (fetched by .github/workflows/cb-3a7bd9bb.yml), so a
rebuild is reproducible from the repository alone and every value can be traced back to a
sha256 that the manifest records.

    from capio import Capture
    cap = Capture()                     # newest committed capture
    cap.text("ehfcl_men_standings")     # stripped text of one target
    cap.json("el_games")               # parsed JSON of one target
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP_ROOT = ROOT / "data" / "session-3a7bd9bb" / "capture"


def _strip(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<br\s*/?>", "\n", raw)
    raw = re.sub(r"(?s)</(p|div|tr|li|h[1-6]|td|th)>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    raw = re.sub(r"[ \t\u00a0]+", " ", raw)
    return raw.strip()


class Capture:
    def __init__(self, root: Path | None = None, stamp: str | None = None):
        root = Path(os.environ.get("CB_CAPTURE_ROOT", root or CAP_ROOT))
        stamps = sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []
        if not stamps:
            raise SystemExit(f"no capture under {root}")
        self.stamp = stamp or stamps[-1]
        self.dir = root / self.stamp
        self.manifest = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self.by_id = {r["id"]: r for r in self.manifest["records"]}
        self._cache: dict[str, str] = {}

    # -- metadata ---------------------------------------------------------
    @property
    def captured_utc(self) -> str:
        return self.manifest["finished_utc"]

    def record(self, tid: str) -> dict:
        return self.by_id[tid]

    def url(self, tid: str) -> str:
        return self.by_id[tid]["url"]

    def sha256(self, tid: str) -> str:
        return self.by_id[tid]["sha256"]

    def ok(self, tid: str) -> bool:
        r = self.by_id.get(tid)
        return bool(r and r.get("status") == 200 and r.get("file"))

    def ids(self, prefix: str = "") -> list[str]:
        return [t for t in self.by_id if t.startswith(prefix) and self.ok(t)]

    # -- payloads ---------------------------------------------------------
    def raw(self, tid: str) -> str:
        if tid not in self._cache:
            rec = self.by_id[tid]
            if not rec.get("file"):
                raise KeyError(f"{tid} was not captured (status {rec.get('status')})")
            with gzip.open(self.dir / rec["file"], "rt", encoding="utf-8", errors="replace") as fh:
                self._cache[tid] = fh.read()
        return self._cache[tid]

    def text(self, tid: str) -> str:
        return _strip(self.raw(tid))

    def json(self, tid: str):
        return json.loads(self.raw(tid))


def captured_date(cap: Capture) -> datetime:
    return datetime.strptime(cap.captured_utc, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


if __name__ == "__main__":
    cap = Capture()
    print("capture", cap.stamp, "finished", cap.captured_utc)
    print("targets", len(cap.by_id), "ok", sum(1 for t in cap.by_id if cap.ok(t)))
    for tid in sorted(cap.by_id):
        r = cap.by_id[tid]
        print(f"{str(r['status'] or 0):>4} {r['bytes']:>9}  {tid}")

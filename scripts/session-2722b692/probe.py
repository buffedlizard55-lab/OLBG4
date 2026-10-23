#!/usr/bin/env python3
"""Board AJ (arena/2722b692-olbg4) — endpoint probe for the sports that are still unpriced.

Fetches a small list of candidate official endpoints, stores every response byte-for-byte in
data/session-2722b692/probe/<stamp>/ (gzip, sha256) and writes a compact triage file
probe_summary.json (status, size, content-type, first 400 characters) so the desk can decide
which feeds to wire in without re-reading whole payloads.
"""
from __future__ import annotations

import gzip
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch  # noqa: E402

def snippet(path: Path) -> str:
    try:
        raw = gzip.decompress(path.read_bytes())
    except OSError:
        raw = path.read_bytes()
    try:
        text = raw.decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""
    text = " ".join(text.split())
    return text[:400]

def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else
               f"data/session-2722b692/probe/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    out.mkdir(parents=True, exist_ok=True)
    targets = json.loads((Path(__file__).resolve().parent / "probe_urls.json").read_text())
    print(f"[probe] {len(targets)} candidates -> {out}", flush=True)
    rows = []
    for i, t in enumerate(targets, 1):
        _, rec = fetch.process_target(i, t, str(out))
        snip = snippet(out / rec["file"]) if rec.get("file") else ""
        rows.append({k: rec.get(k) for k in ("id", "url", "status", "content_type", "bytes",
                                             "sha256", "file", "error")} | {"snippet": snip})
    (out / "probe_summary.json").write_text(json.dumps(
        {"probed_utc": datetime.now(timezone.utc).isoformat(), "results": rows},
        indent=1, sort_keys=True))
    print(f"[probe] ok={sum(1 for r in rows if r['status'] == 200)}/{len(rows)}", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

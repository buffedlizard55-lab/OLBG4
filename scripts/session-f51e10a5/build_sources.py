#!/usr/bin/env python3
"""Turn the capture manifest into the sources.json the site renders."""
from __future__ import annotations

import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-f51e10a5")


def latest_capture() -> str:
    dirs = sorted(glob.glob(os.path.join(DATA, "capture", "20*")))
    return dirs[-1] if dirs else ""


def main() -> None:
    cap = latest_capture()
    if not cap:
        raise SystemExit("no capture directory")
    man = json.load(open(os.path.join(cap, "manifest.json")))
    doc = {
        "schema": "fi-sources-1",
        "capture_id": os.path.basename(cap),
        "started_utc": man.get("started_utc"),
        "finished_utc": man.get("finished_utc"),
        "targets": man.get("targets"),
        "ok": man.get("ok"),
        "failed": man.get("failed"),
        "records": [{k: r.get(k) for k in ("id", "url", "status", "bytes", "sha256", "content_type")}
                    for r in man.get("records", [])],
        "failures": man.get("failures", []),
    }
    json.dump(doc, open(os.path.join(DATA, "sources.json"), "w"), indent=1, sort_keys=True)
    print(f"sources: {doc['ok']} ok / {doc['failed']} failed -> {doc['capture_id']}")


if __name__ == "__main__":
    main()

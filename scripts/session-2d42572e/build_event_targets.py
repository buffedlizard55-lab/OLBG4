#!/usr/bin/env python3
"""Turn the captured OLBG hub pages into event-page targets.

OLBG's sport hubs are SvelteKit pages: the rendered rows carry
`https://www.olbg.com/betting-tips/<Sport>/<Competition>/<Competition>/<Event>/<id>?event_id=<n>`
and the hydration payload carries the same events with a start timestamp.  This
script reads the committed hub bytes only (no network) and emits a target list
for the second capture pass, so the desk records the *complete* market list of
every match OLBG is currently offering instead of only the tipped selection.

Usage: python3 build_event_targets.py CAPTURE_DIR OUT_JSON [LIMIT] [AFTER_ISO]
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

EVENT_HREF = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"]+?event_id=(\d+))"')
START = re.compile(r'itemprop="startDate"\s+datetime="([^"]+)"')
FIELD = re.compile(r'(\w+):(?:"((?:[^"\\]|\\.)*)"|(-?\d+(?:\.\d+)?)|null)')


def payload_starts(body: str) -> dict[str, str]:
    """event_id -> ISO start, read from the SvelteKit hydration payload."""
    out: dict[str, str] = {}
    for marker in ("data:{tips:[", "tips:[{"):
        start = body.find(marker)
        if start < 0:
            continue
        blob = body[start + len(marker):]
        end = blob.find("]}")
        if end < 0:
            continue
        for raw in blob[:end].split("},{"):
            rec = {k: (s or n) for k, s, n in FIELD.findall(raw)}
            url = rec.get("eventUrl") or ""
            ts = rec.get("event_start_unix_timestamp")
            if "event_id=" in url and ts:
                try:
                    iso = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime(
                        "%Y-%m-%dT%H:%M:%SZ")
                except (TypeError, ValueError):
                    continue
                out[url.split("event_id=")[-1]] = iso
        break
    return out


def hub_paths(capture_dir: str) -> list[str]:
    cache: dict[str, str] = {}
    for name in os.listdir(capture_dir):
        if name.startswith("hub_") and name.endswith(".gz"):
            cache[name] = os.path.join(capture_dir, name)
    return list(cache.values())


def read_gz(path: str) -> str:
    import gzip

    with gzip.open(path, "rb") as fh:
        return fh.read().decode("utf-8", "replace")


def main() -> int:
    capture_dir, out_json = sys.argv[1], sys.argv[2]
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 220
    after = sys.argv[4] if len(sys.argv) > 4 else datetime.now(timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")

    found: dict[str, dict] = {}
    for path in hub_paths(capture_dir):
        name = os.path.basename(path)[4:]
        key = name.split(".")[0]
        body = read_gz(path)
        starts = payload_starts(body)
        dom_starts: dict[str, str] = {}
        for href, eid in EVENT_HREF.findall(body):
            if eid not in dom_starts:
                dom_starts[eid] = ""
        # DOM rows carry itemprop startDate in document order; pair by position
        for (href, eid), m in zip(EVENT_HREF.findall(body), START.findall(body)):
            dom_starts[eid] = m
        for href, eid in EVENT_HREF.findall(body):
            start = starts.get(eid) or dom_starts.get(eid, "")
            if not start or start < after:
                continue
            found[eid] = {"id": f"ev_{eid}", "url": href, "group": "events",
                          "sport": key, "start_utc": start, "delay": 0.35,
                          "timeout": 45}

    rows = sorted(found.values(), key=lambda r: (r["start_utc"], r["id"]))[:limit]
    with open(out_json, "w", encoding="utf-8") as fh:
        json.dump(rows, fh, indent=1, sort_keys=True)
        fh.write("\n")
    by_sport: dict[str, int] = {}
    for r in rows:
        by_sport[r["sport"]] = by_sport.get(r["sport"], 0) + 1
    print(f"event targets: {len(rows)} (after {after})")
    for k, v in sorted(by_sport.items()):
        print(f"  {k:16} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

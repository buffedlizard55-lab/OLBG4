#!/usr/bin/env python3
"""Reverse-engineer the OLBG sport hubs.

Each hub page ships a SvelteKit data payload. Every tip in it carries the event name,
the market alias, the listed price in decimal / American / fractional, the event start
timestamp, the tip counts and OLBG's own "confidence" percentage. We extract those
fields verbatim (never derived) into data/session-2c05e0b2/olbg_inventory.json and
record which hub URL each row came from.

Usage: python3 scripts/session-2c05e0b2/re_olbg.py
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.path.join(ROOT, "data", "session-2c05e0b2", "capture")
OUT = os.path.join(ROOT, "data", "session-2c05e0b2", "olbg_inventory.json")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]

FIELD = re.compile(r'(?:^|[{,])\s*([a-z_]+):\s*(?:"([^"]*)"|(-?\d+(?:\.\d+)?)|null)')


def latest_capture() -> str:
    dirs = sorted(glob.glob(os.path.join(CAP, "*", "manifest.json")))
    return os.path.dirname(dirs[-1])


def parse_hub(path: str) -> list[dict]:
    raw = gzip.open(path, "rb").read().decode("utf-8", "replace")
    m = re.search(r"tips:\[", raw)
    if not m:
        return []
    body = raw[m.end() - 1:]
    rows: list[dict] = []
    # Tip objects all start with {id:"...",selection:"
    for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
        chunk = body[tm.start(): tm.start() + 1400]
        end = chunk.find("}")
        chunk = chunk[:end + 1]
        rec: dict[str, str] = {}
        for fm in FIELD.finditer(chunk):
            key, sval, nval = fm.group(1), fm.group(2), fm.group(3)
            rec[key] = sval if sval is not None else nval
        if rec.get("selection") and rec.get("event_name_alias"):
            rows.append(rec)
    return rows


def main() -> int:
    cap = latest_capture()
    manifest = json.load(open(os.path.join(cap, "manifest.json")))
    by_id = {t["id"]: t for t in manifest["targets"]}
    out = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_id": manifest["capture_id"],
        "method": "SvelteKit tips payload on each OLBG sport hub, fields copied verbatim; no value derived",
        "sports": {},
        "totals": {},
    }
    total_events = total_tips = 0
    for sport in SPORTS:
        files = sorted(glob.glob(os.path.join(cap, "olbg-*.gz")))
        match = None
        for f in files:
            tid = os.path.basename(f)[:-3]
            tgt = by_id.get(tid)
            if tgt and tgt["sport"] == sport:
                # prefer the hub path (contains a numeric sport id), not a bare sport slug
                if re.search(r"/\d+$", tgt["url"]):
                    match = (f, tgt)
                    break
        if not match:
            out["sports"][sport] = {"hub_url": "", "events": [], "tips": [], "note": "no hub captured"}
            continue
        f, tgt = match
        tips = parse_hub(f)
        events: dict[str, dict] = {}
        for t in tips:
            ev = t["event_name_alias"].strip()
            ts = int(t.get("event_start_unix_timestamp") or 0)
            e = events.setdefault(ev, {
                "event": ev,
                "start_utc": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else "",
                "start_local_label": "",
                "markets": [],
            })
            e["markets"].append({
                "market": t.get("market_alias", ""),
                "selection": t.get("selection", ""),
                "decimal": t.get("odds", ""),
                "american": t.get("american_odds", ""),
                "fractional": t.get("fractional_odds", ""),
                "win_tips": t.get("win_tips", ""),
                "win_tips_count": t.get("win_tips_count", ""),
                "confidence_pct": t.get("confidence", ""),
                "comments": t.get("comments_count", ""),
            })
        out["sports"][sport] = {
            "hub_url": tgt["url"],
            "capture_file": os.path.basename(f),
            "sha256": tgt["sha256"],
            "events": sorted(events.values(), key=lambda e: (e["start_utc"], e["event"])),
            "event_count": len(events),
            "market_count": len(tips),
        }
        total_events += len(events)
        total_tips += len(tips)
        print(f"{sport:14s} events={len(events):3d} markets={len(tips):3d}  {tgt['url']}")
    out["totals"] = {"events": total_events, "markets": total_tips, "sports": len(SPORTS)}
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(json.dumps(out["totals"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board EZ (session arena/0ed96fe7-olbg4) — reverse-engineer the OLBG sport hubs.

Each OLBG hub page ships a SvelteKit data payload whose `tips:[...]` array carries,
verbatim: the selection, the market alias, the listed price in decimal / American /
fractional, the event start timestamp, the tip counts, OLBG's own confidence percent,
the event name and the event URL (with its event_id). Every field is copied exactly
as published — nothing is derived here.

Output: data/session-0ed96fe7/olbg_inventory.json
"""
from __future__ import annotations

import glob
import gzip
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.path.join(ROOT, "data", "session-0ed96fe7", "capture")
OUT = os.path.join(ROOT, "data", "session-0ed96fe7", "olbg_inventory.json")

# the 15 sports in the brief, with their OLBG hub targets captured by fetch.py
HUBS = [
    ("Golf", "olbg_golf_5"),
    ("Volleyball", "olbg_volleyball_21"),
    ("Rugby Union", "olbg_rugby_union_9"),
    ("Cricket", "olbg_cricket_7"),
    ("Snooker", "olbg_snooker_8"),
    ("Darts", "olbg_darts_15"),
    ("Baseball", "olbg_baseball_12"),
    ("Gaelic Sports", "olbg_gaelic_25"),
    ("Greyhounds", "olbg_greyhounds_28"),
    ("Tennis", "olbg_tennis_3"),
    ("Motor Racing", "olbg_motor_racing_14"),
    ("Handball", "olbg_handball_20"),
    ("Ice Hockey", "olbg_ice_hockey_13"),
    ("Basketball", "olbg_basketball_4"),
    ("Rugby League", "olbg_rugby_league_10"),
]

FIELD = re.compile(r'(?:^|[{,])\s*([a-zA-Z_]+):\s*(?:"([^"]*)"|(-?\d+(?:\.\d+)?)|null)')


def latest_stamp() -> str:
    # pinned primary stamp (same contract as originate_desk): archived extra bot
    # stamps exist under capture/ but the inventory is rebuilt from the primary one.
    return os.path.join(CAP, "20261023T193627Z")


def read_capture(stamp: str, target_id: str) -> str | None:
    for cand in (f"{target_id}.html.gz", f"{target_id}.html", f"{target_id}.json"):
        p = os.path.join(stamp, cand)
        if os.path.exists(p):
            raw = open(p, "rb").read()
            if raw[:2] == b"\x1f\x8b":
                raw = gzip.decompress(raw)
            return raw.decode("utf-8", "ignore")
    return None


def parse_tips(html: str) -> list[dict]:
    """Extract every tip object from the SvelteKit `tips:[{id:"..40hex..",selection:"` stream."""
    m = re.search(r"tips:\[", html)
    if not m:
        return []
    body = html[m.end() - 1:]
    out: list[dict] = []
    for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
        chunk = body[tm.start(): tm.start() + 1600]
        end = chunk.find("}")
        chunk = chunk[: end + 1]
        rec: dict = {}
        for fm in FIELD.finditer(chunk):
            k, sval, nval = fm.group(1), fm.group(2), fm.group(3)
            rec[k] = sval if sval is not None else nval
        if rec.get("selection") and rec.get("event_name_alias"):
            out.append(rec)
    return out


def main() -> int:
    stamp = latest_stamp()
    if not stamp:
        raise SystemExit("no capture found under data/session-0ed96fe7/capture/")
    manifest = json.load(open(os.path.join(stamp, "manifest.json")))
    recs = {r["id"]: r for r in manifest["records"]}
    out = {
        "session": "arena/0ed96fe7-olbg4",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_stamp": os.path.basename(stamp),
        "method": "SvelteKit tips payload on each OLBG sport hub; every field copied verbatim, none derived",
        "sports": {},
        "totals": {},
    }
    total_events = total_tips = 0
    for sport, tid in HUBS:
        html = read_capture(stamp, tid)
        rec = recs.get(tid, {})
        if html is None or rec.get("status") != 200:
            out["sports"][sport] = {"hub_target": tid, "hub_url": rec.get("url", ""),
                                    "events": [], "event_count": 0, "market_count": 0,
                                    "note": f"hub not captured (status {rec.get('status')})"}
            continue
        tips = parse_tips(html)
        events: dict[str, dict] = {}
        for t in tips:
            ev = t["event_name_alias"].strip()
            ts = int(t.get("event_start_unix_timestamp") or 0)
            eid = ""
            m = re.search(r"event_id=(\d+)", t.get("eventUrl", "") or "")
            if m:
                eid = m.group(1)
            e = events.setdefault(eid or ev, {
                "event": ev,
                "event_id": eid,
                "start_utc": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else "",
                "event_url": "https://www.olbg.com" + t["eventUrl"] if t.get("eventUrl", "").startswith("/") else t.get("eventUrl", ""),
                "expired": t.get("expired", ""),
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
            "hub_target": tid,
            "hub_url": rec.get("url", ""),
            "capture_file": rec.get("file", ""),
            "sha256": rec.get("sha256", ""),
            "events": sorted(events.values(), key=lambda e: (e["start_utc"], e["event"])),
            "event_count": len(events),
            "market_count": len(tips),
        }
        total_events += len(events)
        total_tips += len(tips)
        print(f"{sport:14s} events={len(events):3d} tips={len(tips):3d}  {rec.get('url','')}")
    out["totals"] = {"events": total_events, "tips": total_tips, "hubs": len(HUBS)}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"[board-ez] olbg_inventory: {total_events} events, {total_tips} priced tips -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board ED — reverse-engineer the OLBG sport hubs.

Every OLBG tips page ships a SvelteKit payload whose tip objects carry the event
name, market alias, listed price (decimal / American / fractional), event start
timestamp, tip counts and OLBG's own confidence percentage. Nothing is derived
here: each field is copied verbatim from the captured bytes, and the file the
value came from is recorded with its SHA-256 so any line can be re-checked.

Output: data/session-ed4c358c/olbg_inventory.json
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP = ROOT / "data" / "session-ed4c358c" / "capture"
OUT = ROOT / "data" / "session-ed4c358c" / "olbg_inventory.json"

SPORTS = [
    ("Golf", "olbg_golf_5"),
    ("Volleyball", "olbg_volleyball_21"),
    ("Rugby Union", "olbg_rugby_union_9"),
    ("Cricket", "olbg_cricket_7"),
    ("Snooker", "olbg_snooker_8"),
    ("Darts", "olbg_darts_15"),
    ("Baseball", "olbg_baseball_12"),
    ("Gaelic Sports", "olbg_gaelic_football_25"),
    ("Greyhounds", "olbg_greyhounds_28"),
    ("Tennis", "olbg_tennis_3"),
    ("Motor Racing", "olbg_motor_racing_14"),
    ("Handball", "olbg_handball_20"),
    ("Ice Hockey", "olbg_ice_hockey_13"),
    ("Basketball", "olbg_basketball_4"),
    ("Rugby League", "olbg_rugby_league_10"),
]

FIELD = re.compile(r'(?:^|[{,])\s*([a-z_]+):\s*(?:"([^"]*)"|(-?\d+(?:\.\d+)?)|null)')


def latest_capture() -> Path:
    return sorted(p.parent for p in CAP.glob("*/manifest.json"))[-1]


def parse_hub(path: Path) -> list[dict]:
    raw = gzip.decompress(path.read_bytes()).decode("utf-8", "replace")
    m = re.search(r"tips:\[", raw)
    if not m:
        return []
    body = raw[m.end() - 1:]
    rows: list[dict] = []
    for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
        chunk = body[tm.start(): tm.start() + 2000]
        chunk = chunk[: chunk.find("}") + 1]
        rec = {}
        for fm in FIELD.finditer(chunk):
            key, sval, nval = fm.groups()
            rec[key] = sval if sval is not None else nval
        if rec.get("selection") and rec.get("event_name_alias"):
            rows.append(rec)
    return rows


def main() -> int:
    cap = latest_capture()
    manifest = json.loads((cap / "manifest.json").read_text())
    recs = {r["id"]: r for r in manifest["records"]}
    out = {
        "capture_stamp": cap.name,
        "capture_finished_utc": manifest["finished_utc"],
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": (
            "SvelteKit tips payload on each OLBG sport hub. selection / market_alias / odds / "
            "american_odds / fractional_odds / event_start_unix_timestamp / confidence are copied "
            "verbatim; no value is derived or inferred."
        ),
        "sports": {},
        "totals": {},
    }
    ev_total = tip_total = 0
    for sport, tid in SPORTS:
        rec = recs.get(tid)
        if not rec or not rec.get("file"):
            out["sports"][sport] = {"hub_url": rec["url"] if rec else "", "status": rec.get("status") if rec else None,
                                    "events": [], "tips": [], "note": "hub not captured"}
            continue
        path = cap / rec["file"]
        body = gzip.decompress(path.read_bytes())
        if hashlib.sha256(body).hexdigest() != rec["sha256"]:
            raise SystemExit(f"SHA-256 mismatch for {tid}")
        tips = parse_hub(path)
        events: dict[str, dict] = {}
        for t in tips:
            ev = t["event_name_alias"].strip()
            ts = int(t.get("event_start_unix_timestamp") or 0)
            e = events.setdefault(ev, {
                "event": ev,
                "start_utc": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else "",
                "start_unix": ts,
                "league": t.get("menu_league", ""),
                "event_url": "https://www.olbg.com" + t.get("eventUrl", "") if t.get("eventUrl") else "",
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
        evs = sorted(events.values(), key=lambda e: (e["start_utc"], e["event"]))
        out["sports"][sport] = {
            "hub_url": rec["url"],
            "capture_file": rec["file"],
            "sha256": rec["sha256"],
            "http_status": rec["status"],
            "events": evs,
            "event_count": len(evs),
            "market_count": len(tips),
        }
        ev_total += len(evs)
        tip_total += len(tips)
        print(f"{sport:15s} events={len(evs):3d} markets={len(tips):3d} {rec['url']}")
    out["totals"] = {"events": ev_total, "markets": tip_total, "sports": len(SPORTS)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(out["totals"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board AR — reverse-engineer the OLBG sport hubs.

Each OLBG hub ships a SvelteKit data payload. Every tip object in it carries the event
name, the market alias, the listed price in decimal / American / fractional form, the
event start timestamp, the tip counts and OLBG's own confidence percentage. Board AR
copies those fields verbatim (never derives them) into
`data/session-405e9797/olbg_inventory.json` and records the exact hub URL and the
SHA-256 of the captured bytes for every row.

OLBG is used as a *listing / taxonomy* source only. No OLBG price is ever reused as one
of our own lines; the prices here exist so a reviewer can see what the market was doing
and so the coverage table can prove which sports OLBG was actually listing today.
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-405e9797")
CAP = os.path.join(DATA, "capture")
OUT = os.path.join(DATA, "olbg_inventory.json")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]

# hub target id -> brief sport
HUB_FOR_SPORT = {
    "Golf": ["olbg_golf_5", "olbg_golf_pga"],
    "Volleyball": ["olbg_volleyball_21", "olbg_volleyball_italy"],
    "Rugby Union": ["olbg_rugby_union_9", "olbg_rugby_union_urc"],
    "Cricket": ["olbg_cricket_7", "olbg_cricket_test"],
    "Snooker": ["olbg_snooker_8", "olbg_snooker_wst"],
    "Darts": ["olbg_darts_15", "olbg_darts_pdc"],
    "Baseball": ["olbg_baseball_12", "olbg_baseball_mlb"],
    "Gaelic Sports": ["olbg_gaelic_25", "olbg_gaelic_football"],
    "Greyhounds": ["olbg_greyhounds_28", "olbg_greyhounds_today"],
    "Tennis": ["olbg_tennis_3", "olbg_tennis_atp"],
    "Motor Racing": ["olbg_motor_racing_14", "olbg_motor_racing_hub"],
    "Handball": ["olbg_handball_20", "olbg_handball_ehf"],
    "Ice Hockey": ["olbg_ice_hockey_13", "olbg_ice_hockey_nhl", "olbg_ice_hockey_nhl_2"],
    "Basketball": ["olbg_basketball_4", "olbg_basketball_nba"],
    "Rugby League": ["olbg_rugby_league_10", "olbg_rugby_league_nrl"],
}

FIELD = re.compile(r'(?:^|[{,])\s*([a-z_]+):\s*(?:"((?:[^"\\]|\\.)*)"|(-?\d+(?:\.\d+)?)|null)')


def latest_capture() -> str:
    dirs = sorted(glob.glob(os.path.join(CAP, "*", "manifest.json")))
    return os.path.dirname(dirs[-1])


def load_manifest() -> tuple[str, dict]:
    cap = latest_capture()
    return cap, json.load(open(os.path.join(cap, "manifest.json")))


def read_payload(cap: str, rec: dict) -> bytes:
    path = os.path.join(cap, rec["file"])
    raw = open(path, "rb").read()
    body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    if hashlib.sha256(body).hexdigest() != rec["sha256"]:
        raise RuntimeError(f"sha256 mismatch for {rec['id']}")
    return body


def parse_hub(raw: str) -> list[dict]:
    m = re.search(r"tips:\[", raw)
    if not m:
        return []
    body = raw[m.end() - 1:]
    rows: list[dict] = []
    for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
        chunk = body[tm.start(): tm.start() + 1600]
        chunk = chunk[:chunk.find("}") + 1]
        rec: dict[str, str] = {}
        for fm in FIELD.finditer(chunk):
            key, sval, nval = fm.group(1), fm.group(2), fm.group(3)
            rec[key] = (sval if sval is not None else nval) or ""
        if rec.get("selection") and rec.get("event_name_alias"):
            rows.append(rec)
    return rows


def main() -> int:
    cap, manifest = load_manifest()
    by_id = {r["id"]: r for r in manifest["records"]}
    out = {
        "schema": "board-ar-olbg-inventory/1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_id": os.path.basename(cap),
        "method": ("SvelteKit `tips:[...]` payload on each OLBG sport hub; fields copied verbatim. "
                   "OLBG is a listing/taxonomy source only: no OLBG price is reused as an originated line."),
        "sports": {},
        "totals": {},
    }
    total_events = total_tips = total_sports = 0
    for sport in SPORTS:
        chosen = None
        for tid in HUB_FOR_SPORT[sport]:
            rec = by_id.get(tid)
            if rec and rec.get("status") == 200 and rec.get("file"):
                chosen = rec
                break
        if not chosen:
            out["sports"][sport] = {"hub_url": "", "events": [], "event_count": 0,
                                    "market_count": 0, "note": "no hub captured"}
            continue
        raw = read_payload(cap, chosen).decode("utf-8", "replace")
        tips = parse_hub(raw)
        events: dict[str, dict] = {}
        for t in tips:
            ev = (t.get("event_name_alias") or "").strip()
            if not ev:
                continue
            try:
                ts = int(t.get("event_start_unix_timestamp") or 0)
            except ValueError:
                ts = 0
            e = events.setdefault(ev, {
                "event": ev,
                "start_utc": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else "",
                "event_url": t.get("eventUrl", ""),
                "competition": t.get("menu_league", ""),
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
                "experts": t.get("experts_count", ""),
            })
        out["sports"][sport] = {
            "hub_url": chosen["url"],
            "capture_file": chosen["file"],
            "sha256": chosen["sha256"],
            "captured_utc": manifest["finished_utc"],
            "events": sorted(events.values(), key=lambda e: (e["start_utc"], e["event"])),
            "event_count": len(events),
            "market_count": len(tips),
        }
        total_events += len(events)
        total_tips += len(tips)
        total_sports += 1 if events else 0
        print(f"{sport:14s} events={len(events):3d} markets={len(tips):4d}  {chosen['url']}")
    out["totals"] = {"events": total_events, "markets": total_tips,
                     "sports_with_listings": total_sports, "sports_checked": len(SPORTS)}
    json.dump(out, open(OUT, "w"), indent=1, sort_keys=True)
    print(f"totals: {out['totals']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

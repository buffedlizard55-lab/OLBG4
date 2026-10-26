#!/usr/bin/env python3
"""Board AN — OLBG.com reverse engineering.

OLBG's sport hubs are SvelteKit apps.  Each hub ships its whole tip feed inside the
server-rendered HTML as a JavaScript object literal:

    {type:"data",data:{tips:[{id:"...",selection:"Ann Li",market_alias:"Win Match",
      odds:"1.75",american_odds:"-133",fractional_odds:"3/4",
      event_start_unix_timestamp:1792722600,eventUrl:"/betting-tips/...",
      event_name_alias:"Ann Li vs Lilli Tagger",win_tips:6,win_tips_count:7,
      confidence:86,...}]}}

There is no public OLBG JSON API for a hub, so this module reads the embedded payload
directly instead of the rendered rows: the payload carries the full feed (the DOM only
renders a slice of it), the quoted decimal *and* American price, and OLBG's own
confidence figure.  Every value published downstream is read from that payload; nothing
is inferred here.

Usage: python3 olbg.py CAPTURE_DIR OUT_JSON
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

# OLBG sport hub -> (OLBG sport label, sport id, our canonical sport)
HUBS = {
    "golf": ("Golf", 5, "Golf"),
    "volleyball": ("Volleyball", 21, "Volleyball"),
    "rugbyunion": ("Rugby Union", 9, "Rugby Union"),
    "cricket": ("Cricket", 7, "Cricket"),
    "snooker": ("Snooker", 8, "Snooker"),
    "darts": ("Darts", 15, "Darts"),
    "baseball": ("Baseball", 12, "Baseball"),
    "gaelicfootball": ("Gaelic Football", 25, "Gaelic Sports"),
    "hurling": ("Hurling", 26, "Gaelic Sports"),
    "greyhounds": ("Greyhounds", 28, "Greyhounds"),
    "tennis": ("Tennis", 3, "Tennis"),
    "motorracing": ("Motor Racing", 14, "Motor Racing"),
    "handball": ("Handball", 20, "Handball"),
    "icehockey": ("Ice Hockey", 13, "Ice Hockey"),
    "basketball": ("Basketball", 4, "Basketball"),
    "rugbyleague": ("Rugby League", 10, "Rugby League"),
}

STR = r'"((?:[^"\\]|\\.)*)"'


def _slice_balanced(text: str, start: int, open_ch: str = "[", close_ch: str = "]") -> str:
    """Return text[start:] up to the matching close_ch, string/escape aware."""
    assert text[start] == open_ch
    depth, i, n = 0, start, len(text)
    in_str = False
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return text[start : i + 1]
        i += 1
    raise ValueError("unbalanced payload")


def extract_tips(html: str) -> list[dict]:
    """Pull the embedded tip feed out of a hub page."""
    idx = html.find("tips:[")
    if idx < 0:
        return []
    arr = _slice_balanced(html, idx + len("tips:"))
    tips = []
    for m in re.finditer(r"\{id:", arr):
        try:
            obj = _slice_balanced(arr, m.start(), "{", "}")
        except ValueError:
            continue
        tips.append(parse_tip(obj))
    return tips


def _num(obj: str, key: str):
    """Numbers appear both bare (event_start_unix_timestamp:1792722600) and quoted
    as strings (odds:"1.75", american_odds:"-133"), so accept either spelling."""
    m = re.search(rf"[{{,]{key}:\"(-?\d+(?:\.\d+)?)\"", obj) or re.search(
        rf"[{{,]{key}:(-?\d+(?:\.\d+)?)", obj
    )
    return float(m.group(1)) if m else None


def _str(obj: str, key: str):
    m = re.search(rf"[{{,]{key}:{STR}", obj)
    if not m:
        return None
    return m.group(1).encode().decode("unicode_escape", errors="ignore")


def parse_tip(obj: str) -> dict:
    odds = _num(obj, "odds")
    american = _num(obj, "american_odds")
    return {
        "id": _str(obj, "id"),
        "selection": _str(obj, "selection"),
        "market_alias": _str(obj, "market_alias"),
        "odds": odds,
        "american_odds": american,
        "fractional_odds": _str(obj, "fractional_odds"),
        "start_unix": _num(obj, "event_start_unix_timestamp"),
        "event": _str(obj, "event_name_alias"),
        "event_url": _str(obj, "eventUrl"),
        "confidence": _num(obj, "confidence"),
        "win_tips": _num(obj, "win_tips"),
        "win_tips_count": _num(obj, "win_tips_count"),
        "expired": bool(_num(obj, "expired")),
    }


def american_from_decimal(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def load_hub(path: str) -> list[dict]:
    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as fh:
        return extract_tips(fh.read())


def main() -> int:
    capdir, out = sys.argv[1], sys.argv[2]
    now = datetime.now(timezone.utc).timestamp()
    manifest_path = os.path.join(capdir, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {"records": []}
    by_id = {r["id"]: r for r in manifest.get("records", [])}

    hubs, events, all_tips = [], {}, []
    for key, (label, sid, sport) in HUBS.items():
        tid = f"olbg_hub_{key}"
        rec = by_id.get(tid)
        row = {
            "key": key,
            "olbg_sport": label,
            "olbg_sport_id": sid,
            "sport": sport,
            "hub_url": f"https://www.olbg.com/betting-tips/{label.replace(' ', '_')}/{sid}",
            "captured": bool(rec),
            "bytes": rec["bytes"] if rec else None,
            "sha256": rec["sha256"] if rec else None,
            "tips": 0,
            "events": 0,
            "upcoming_events": 0,
            "market_aliases": [],
        }
        path = os.path.join(capdir, f"{tid}.gz")
        if rec and os.path.exists(path):
            tips = load_hub(path)
            row["tips"] = len(tips)
            aliases = sorted({t["market_alias"] for t in tips if t["market_alias"]})
            row["market_aliases"] = aliases
            for t in tips:
                t["sport"] = sport
                t["olbg_sport"] = label
                t["hub_key"] = key
                all_tips.append(t)
                if not t["event"]:
                    continue
                ev = events.setdefault(
                    (sport, t["event"]),
                    {
                        "sport": sport,
                        "olbg_sport": label,
                        "event": t["event"],
                        "start_unix": t["start_unix"],
                        "event_url": (
                            "https://www.olbg.com" + t["event_url"]
                            if t["event_url"] and t["event_url"].startswith("/")
                            else t["event_url"]
                        ),
                        "hub_url": row["hub_url"],
                        "selections": [],
                    },
                )
                ev["selections"].append(
                    {
                        "selection": t["selection"],
                        "market_alias": t["market_alias"],
                        "decimal": t["odds"],
                        "american": t["american_odds"],
                        "olbg_confidence": t["confidence"],
                        "win_tips": t["win_tips"],
                        "win_tips_count": t["win_tips_count"],
                    }
                )
            row["events"] = sum(1 for e in events.values() if e["olbg_sport"] == label)
            row["upcoming_events"] = sum(
                1
                for e in events.values()
                if e["olbg_sport"] == label and (e["start_unix"] or 0) > now
            )
        hubs.append(row)

    for ev in events.values():
        ev["start_utc"] = (
            datetime.fromtimestamp(ev["start_unix"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if ev["start_unix"]
            else None
        )
        ev["upcoming"] = bool(ev["start_unix"] and ev["start_unix"] > now)
        ev["selections"].sort(key=lambda s: (s["market_alias"] or "", s["selection"] or ""))

    out_events = sorted(events.values(), key=lambda e: (e["start_unix"] or 0, e["sport"], e["event"]))
    payload = {
        "schema": "olbg4.board-an.olbg/1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_dir": capdir,
        "hubs": hubs,
        "counts": {
            "hubs": len(hubs),
            "hubs_captured": sum(1 for h in hubs if h["captured"]),
            "tips": len(all_tips),
            "events": len(out_events),
            "upcoming_events": sum(1 for e in out_events if e["upcoming"]),
            "by_sport": {
                s: {
                    "tips": sum(1 for t in all_tips if t["sport"] == s),
                    "events": sum(1 for e in out_events if e["sport"] == s),
                    "upcoming": sum(1 for e in out_events if e["sport"] == s and e["upcoming"]),
                }
                for s in sorted({h["sport"] for h in hubs})
            },
        },
        "events": out_events,
        "tips": all_tips,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(json.dumps(payload["counts"], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

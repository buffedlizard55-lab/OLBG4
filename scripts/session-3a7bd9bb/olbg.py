#!/usr/bin/env python3
"""Board CB — read OLBG's own 15-sport board out of the committed capture.

Output: data/session-3a7bd9bb/olbg_board.json

Every event name, start time, selection label, market label, listed price and tip count is read
verbatim from OLBG's server-rendered cards (schema.org SportsEvent microdata plus the
data-decimal / data-american / data-fractional attributes). Nothing is inferred; an event with no
odds attribute keeps an empty price.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from capio import Capture, ROOT

OUT = ROOT / "data" / "session-3a7bd9bb" / "olbg_board.json"

# capture-id prefix -> (sport label, OLBG sport id)
HUB_SPORT = [
    ("olbg_golf", "Golf"),
    ("olbg_volleyball", "Volleyball"),
    ("olbg_rugby_union", "Rugby Union"),
    ("olbg_cricket", "Cricket"),
    ("olbg_snooker", "Snooker"),
    ("olbg_darts", "Darts"),
    ("olbg_baseball", "Baseball"),
    ("olbg_gaelic", "Gaelic Sports"),
    ("olbg_hurling", "Gaelic Sports"),
    ("olbg_greyhounds", "Greyhounds"),
    ("olbg_tennis", "Tennis"),
    ("olbg_motor", "Motor Racing"),
    ("olbg_handball", "Handball"),
    ("olbg_ice_hockey", "Ice Hockey"),
    ("olbg_ih_", "Ice Hockey"),
    ("olbg_basketball", "Basketball"),
    ("olbg_bb_", "Basketball"),
    ("olbg_rugby_league", "Rugby League"),
    ("olbg_mlb", "Baseball"),
    ("olbg_all_", "PLACEHOLDER"),
    ("olbg_probe_", "Tennis"),
]

URL = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"?]*)\?event_id=(\d+)"')
NAME = re.compile(r'itemprop="name">([^<]+)</h5>')
START = re.compile(r'itemprop="startDate" datetime="([^"]+)"')
LOC = re.compile(r'itemprop="location">([^<]*)<')
SEL = re.compile(r"<h4[^>]*>([^<]+)</h4>")
MKT = re.compile(r'<p class="truncate text-sm">([^<]*)</p>')
ODDS = re.compile(r'data-decimal="([\d.]+)" data-american="([+\-]?\d+)" data-fractional="([^"]*)"')
TIPS = re.compile(r'<b class="text-xs truncate">([^<]*)</b>')
CONF = re.compile(r"--confidence:\s*(\d+)%")


def decimals_to_american(dec: float) -> int | None:
    if not dec or dec <= 1.0:
        return None
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def parse_cards(html: str) -> list[dict]:
    """One record per selection card; several cards share an event."""
    out: list[dict] = []
    for block in html.split('class="grd tip')[1:]:
        m_url = URL.search(block)
        m_name = NAME.search(block)
        if not (m_url and m_name):
            continue
        start = START.search(block)
        loc = LOC.search(block)
        sel = SEL.search(block)
        mkt = MKT.search(block)
        odds = ODDS.search(block)
        tips = TIPS.search(block)
        conf = CONF.search(block)
        dec = float(odds.group(1)) if odds else None
        out.append({
            "event_url": m_url.group(1),
            "event_id": int(m_url.group(2)),
            "event_name": m_name.group(1).strip(),
            "start_utc": start.group(1).replace(".000Z", "Z") if start else None,
            "venue": (loc.group(1).strip() if loc and loc.group(1) else ""),
            "selection": sel.group(1).strip() if sel else "",
            "market": mkt.group(1).strip() if mkt and mkt.group(1) else "",
            "decimal_odds": dec,
            "american_odds": (int(odds.group(2)) if odds else decimals_to_american(dec) if dec else None),
            "fractional_odds": odds.group(3) if odds else "",
            "tips_label": tips.group(1).strip() if tips else "",
            "tipster_confidence_pct": int(conf.group(1)) if conf else None,
        })
    return out


def group_events(cards: list[dict]) -> list[dict]:
    events: dict[tuple, dict] = {}
    for c in cards:
        key = (c["event_name"], c["start_utc"] or "", c["event_url"])
        ev = events.setdefault(key, {
            "event_id": c["event_id"],
            "name": c["event_name"],
            "start_utc": c["start_utc"],
            "url": c["event_url"],
            "venue": c["venue"],
            "listed": [],
        })
        ev["listed"].append({k: c[k] for k in (
            "selection", "market", "decimal_odds", "american_odds",
            "fractional_odds", "tips_label", "tipster_confidence_pct")})
    return list(events.values())


def sport_for(tid: str) -> str | None:
    for prefix, sport in HUB_SPORT:
        if tid.startswith(prefix):
            return sport
    return None


def build(cap: Capture) -> dict:
    sports: dict[str, dict] = {}
    pages: list[dict] = []
    for tid in sorted(cap.by_id):
        if not tid.startswith("olbg_"):
            continue
        if "robots" in tid or "sitemap" in tid or tid == "olbg_home":
            continue
        sport = sport_for(tid)
        if not cap.ok(tid):
            pages.append({"capture_id": tid, "sport": sport, "url": cap.url(tid),
                          "status": cap.record(tid).get("status"),
                          "cards": 0, "error": cap.record(tid).get("error")})
            continue
        cards = parse_cards(cap.raw(tid))
        events = group_events(cards)
        pages.append({"capture_id": tid, "sport": sport, "url": cap.url(tid),
                      "status": 200, "sha256": cap.sha256(tid), "cards": len(cards),
                      "events": len(events)})
        if sport in (None, "PLACEHOLDER"):
            continue
        bucket = sports.setdefault(sport, {"sport": sport, "pages": [], "events": []})
        bucket["pages"].append({"capture_id": tid, "url": cap.url(tid),
                                "sha256": cap.sha256(tid), "cards": len(cards)})
        seen = {(e["name"], e["start_utc"]) for e in bucket["events"]}
        for ev in events:
            if (ev["name"], ev["start_utc"]) not in seen:
                bucket["events"].append(ev)
                seen.add((ev["name"], ev["start_utc"]))

    for bucket in sports.values():
        bucket["events"].sort(key=lambda e: (e["start_utc"] or "", e["name"]))
        bucket["events_total"] = len(bucket["events"])

    payload = {
        "schema": "olbg4.board-cb.olbg-board/1",
        "board": "CB",
        "session": "arena/3a7bd9bb-olbg4",
        "capture_id": cap.stamp,
        "captured_utc": cap.captured_utc,
        "sports_in_scope": ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts",
                            "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing",
                            "Handball", "Ice Hockey", "Basketball", "Rugby League"],
        "totals": {
            "pages": len(pages),
            "events_all": sum(len(b["events"]) for b in sports.values()),
        },
        "pages": pages,
        "sports": sports,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"olbg_board.json: {payload['totals']['events_all']} events across {len(sports)} sports")
    for s, b in sorted(sports.items()):
        print(f"  {s:15s} {b['events_total']:3d} events")
    return payload


if __name__ == "__main__":
    build(Capture())

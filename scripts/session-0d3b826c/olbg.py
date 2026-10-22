#!/usr/bin/env python3
"""Read public OLBG SvelteKit hubs without touching robots-disallowed APIs.

Only fixture structure is retained. Tip counts, tipster identities, comments and
bookmaker prices are deliberately discarded. OLBG is never an official fixture
or form source; unmatched rows are routed to Flagged for Review.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any

from common import Capture

SPORTS = {
    3: "Tennis",
    4: "Basketball",
    5: "Golf",
    7: "Cricket",
    8: "Snooker",
    9: "Rugby Union",
    10: "Rugby League",
    12: "Baseball",
    13: "Ice Hockey",
    14: "Motor Racing",
    15: "Darts",
    20: "Handball",
    21: "Volleyball",
    22: "Aussie Rules",
    23: "Esports",
    25: "Gaelic Football",
    28: "Greyhounds",
}

FIELDS = {
    "start": r"event_start_unix_timestamp:(\d+)",
    "url": r'eventUrl:"((?:[^"\\]|\\.)*)"',
    "name": r'event_name_alias:"((?:[^"\\]|\\.)*)"',
    "league": r'menu_league:(?:"((?:[^"\\]|\\.)*)"|null)',
    "market": r'market_alias:"((?:[^"\\]|\\.)*)"',
    "selection": r'selection:"((?:[^"\\]|\\.)*)"',
    "expired": r"expired:(\d)",
}


def objects(html: str, key: str) -> list[str]:
    marker = key + ":[{id:"
    pos = html.find(marker)
    if pos < 0:
        return []
    i = pos + len(key) + 1
    depth = 0
    start = None
    result = []
    in_string = False
    escaped = False
    while i < len(html):
        ch = html[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    result.append(html[start:i + 1])
                    start = None
            elif ch == "]" and depth == 0:
                break
        i += 1
    return result


def js_string(value: str | None) -> str:
    if value is None:
        return ""
    return json.loads('"' + value + '"')


def parse(cap: Capture) -> dict[str, Any]:
    hubs = []
    grouped: dict[tuple, dict[str, Any]] = {}
    menu_links: set[str] = set()
    for item in cap.manifest["items"]:
        source_id = item["id"]
        if source_id == "olbg_all" and cap.usable(source_id):
            html = cap.text(source_id)
            menu_links.update(re.findall(r"/betting-tips/[A-Za-z0-9_]+/\d+", html))
            continue
        match = re.fullmatch(r"olbg_(.+)_(\d+)", source_id)
        if not match:
            continue
        sport_id = int(match.group(2))
        if sport_id not in SPORTS:
            continue
        sport = SPORTS[sport_id]
        html = cap.text(source_id) if item.get("bytes") else ""
        match_objects = objects(html, "tips")
        tournament_objects = objects(html, "tournaments")
        hubs.append({
            "sport": sport,
            "sport_id": sport_id,
            "hub_url": item["url"],
            "source_id": source_id,
            "http_status": item["status"],
            "embedded_match_rows": len(match_objects),
            "embedded_tournament_rows": len(tournament_objects),
            "load_more_present": "Load More Tips" in html,
            "sha256": item["sha256"],
        })
        for kind, raw_objects in (("match", match_objects), ("outright", tournament_objects)):
            for raw in raw_objects:
                values: dict[str, str] = {}
                for key, pattern in FIELDS.items():
                    found = re.search(pattern, raw)
                    values[key] = js_string(found.group(1)) if found else ""
                event_url = values["url"]
                id_match = re.search(r"event_id=(\d+)", event_url)
                event_id = int(id_match.group(1)) if id_match else None
                timestamp = int(values["start"]) if values["start"] else None
                start = datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if timestamp else ""
                actual_kind = "daily-race" if sport_id == 28 and values["market"] == "Daily Races" else kind
                name = values["name"] or (values["selection"] if actual_kind != "match" else "")
                key = (sport_id, event_id, actual_kind, name, start)
                row = grouped.setdefault(key, {
                    "listing_id": f"olbg-{sport_id}-{event_id if event_id is not None else len(grouped) + 1}",
                    "sport": sport,
                    "sport_id": sport_id,
                    "kind": actual_kind,
                    "event_id": event_id,
                    "listed_name": name,
                    "listed_start_utc": start,
                    "listed_competition": values["league"],
                    "olbg_url": "https://www.olbg.com" + event_url if event_url.startswith("/") else event_url,
                    "market_labels": set(),
                    "source_ids": set(),
                    "listed_expired": values["expired"] == "1",
                })
                if values["market"]:
                    row["market_labels"].add(values["market"])
                row["source_ids"].add(source_id)
    events = []
    for row in grouped.values():
        row["market_labels"] = sorted(row["market_labels"])
        row["source_ids"] = sorted(row["source_ids"])
        row["upcoming_at_capture"] = bool(row["listed_start_utc"] and row["listed_start_utc"] > cap.cutoff and not row["listed_expired"])
        row["official_reconciliation"] = "unmatched"
        row["official_url"] = ""
        events.append(row)
    events.sort(key=lambda r: (r["sport"], r["listed_start_utc"], r["listed_name"]))
    return {
        "schema": "olbg4.board-af.olbg-listing/v1",
        "capture_id": cap.capture_id,
        "captured_utc": cap.cutoff,
        "sports": SPORTS,
        "discovered_menu_links": sorted(menu_links),
        "robots_policy": {
            "robots_url": "https://www.olbg.com/robots.txt",
            "public_paths_read": ["/betting-tips", "/betting-tips/<Sport>/<id>"],
            "disallowed_paths_not_read": ["/api/", "/sports/", "/events.php", "/tips/hot", "/tipster/"],
            "completeness_note": "Only server-rendered rows are inventoried. Load More uses a robots-disallowed API, so absence from this listing is not evidence that OLBG lacks an event.",
        },
        "hubs": hubs,
        "events": events,
    }

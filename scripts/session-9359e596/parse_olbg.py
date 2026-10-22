#!/usr/bin/env python3
"""Board Z (session arena/9359e596-olbg4) - parse live OLBG hub captures into structural inventory.

Reads byte-exact gzip captures from data/session-9359e596/capture/<STAMP>/raw/olbg_*.html.gz,
verifies every SHA-256 digest against manifest.json, and extracts the server-rendered
SvelteKit hydration arrays (`tips:[...]` and `tournaments:[...]`).

Extracted fields (structural & market-price reference only):
  - event_id, event_name, olbg_url, region/competition path, menu_league
  - UTC start derived strictly from `event_start_unix_timestamp` (seconds since epoch)
  - market_label, featured_selection, featured_price_decimal, featured_price_american
  - expired_flag, venue, hub_sha256, captured_utc

Explicitly excluded (never copied or stored):
  - tipster consensus counts, tip percentages, star/value ratings, tipster comments, tipster names.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

SPORTS = {
    3: ("Tennis", True, ""),
    4: ("Basketball", True, ""),
    5: ("Golf", True, ""),
    7: ("Cricket", True, ""),
    8: ("Snooker", True, ""),
    9: ("Rugby Union", True, ""),
    10: ("Rugby League", True, ""),
    12: ("Baseball", True, ""),
    13: ("Ice Hockey", True, ""),
    14: ("Motor Racing", True, ""),
    15: ("Darts", True, ""),
    20: ("Handball", True, ""),
    21: ("Volleyball", True, ""),
    22: ("Aussie Rules", True, ""),
    23: ("Esports", True, ""),
    25: (
        "Gaelic Football",
        True,
        "Scope-ambiguous: prompt excludes 'football'; OLBG separates Gaelic Football (sport_id=25) "
        "from Association Football (sport_id=1) and American Football (sport_id=11). Retained in OLBG "
        "inventory and quarantined on Flagged for Review with blank lines.",
    ),
    28: ("Greyhounds", True, ""),
}

EXCLUDED_OLBG_SPORTS = {
    1: "Football (Soccer)",
    2: "Horse Racing",
    11: "American Football",
    16: "Boxing",
    17: "Cycling",
    26: "Hurling",
}

FIELD_RE = {
    "selection": r'selection:"((?:[^"\\]|\\.)*)"',
    "market_alias": r'market_alias:"((?:[^"\\]|\\.)*)"',
    "odds": r'odds:"([^"]*)"',
    "american_odds": r'american_odds:"([^"]*)"',
    "event_start_unix_timestamp": r"event_start_unix_timestamp:(\d+)",
    "eventUrl": r'eventUrl:"((?:[^"\\]|\\.)*)"',
    "leagueUrl": r'leagueUrl:"((?:[^"\\]|\\.)*)"',
    "event_name_alias": r'event_name_alias:"((?:[^"\\]|\\.)*)"',
    "menu_league": r'menu_league:(?:"((?:[^"\\]|\\.)*)"|null)',
    "expired": r"expired:(\d)",
    "venue": r'venue:(?:"((?:[^"\\]|\\.)*)"|null)',
}


def extract_array_objects(html: str, key: str) -> list[str]:
    marker = key + ":[{id:"
    pos = html.find(marker)
    if pos < 0:
        return []
    i = pos + len(key + ":[")
    depth, start, objs, in_str, esc = 0, None, [], False, False
    while i < len(html):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(html[start : i + 1])
                    start = None
            elif ch == "]" and depth == 0:
                break
        i += 1
    return objs


def unescape_js_str(val: str | None) -> str | None:
    if val is None:
        return None
    return json.loads('"' + val + '"')


def parse_capture(cap_dir: str, out_path: str) -> dict:
    manifest = json.load(open(os.path.join(cap_dir, "manifest.json"), encoding="utf-8"))
    hubs, rows = [], []
    all_hub_menu_links = []

    for item in manifest["items"]:
        if item["id"] == "olbg_all" and item.get("status") == 200:
            raw_bytes = gzip.open(os.path.join(cap_dir, item["file"])).read()
            assert hashlib.sha256(raw_bytes).hexdigest() == item["sha256"]
            html_all = raw_bytes.decode("utf-8", "replace")
            all_hub_menu_links = sorted(set(re.findall(r"/betting-tips/[A-Za-z0-9_]+/\d+", html_all)))
            continue

        m = re.match(r"olbg_(.+)_(\d+)$", item["id"])
        if not m:
            continue
        sport_id = int(m.group(2))
        sport_name, in_scope, scope_note = SPORTS.get(
            sport_id, (m.group(1).replace("_", " ").title(), False, "Out of scope")
        )
        raw_bytes = gzip.open(os.path.join(cap_dir, item["file"])).read()
        calc_sha = hashlib.sha256(raw_bytes).hexdigest()
        if calc_sha != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch on {item['id']}: {calc_sha} != {item['sha256']}")
        html = raw_bytes.decode("utf-8", "replace")

        match_objs = extract_array_objects(html, "tips")
        tournament_objs = extract_array_objects(html, "tournaments")
        has_load_more = "Load More Tips" in html
        api_match = re.search(r'tipsApiUrl:"([^"]*)"', html)
        disallowed_api = unescape_js_str(api_match.group(1)).split("&ti=")[0] if api_match else None

        hubs.append(
            {
                "sport": sport_name,
                "olbg_sport_id": sport_id,
                "hub_url": item["url"],
                "http_status": item["status"],
                "sha256": item["sha256"],
                "fetched_utc": item["fetched_utc"],
                "embedded_match_rows": len(match_objs),
                "embedded_tournament_rows": len(tournament_objs),
                "load_more_present": has_load_more,
                "disallowed_internal_api": disallowed_api,
                "in_scope": in_scope,
                "scope_note": scope_note,
            }
        )

        combined = [("match", x) for x in match_objs] + [("outright", x) for x in tournament_objs]
        for kind, raw_obj in combined:
            parsed = {}
            for fk, rx in FIELD_RE.items():
                mm = re.search(rx, raw_obj)
                parsed[fk] = unescape_js_str(mm.group(1)) if (mm and mm.group(1) is not None) else None
            ev_url = parsed["eventUrl"] or ""
            ev_id_m = re.search(r"event_id=(\d+)", ev_url)
            ts = int(parsed["event_start_unix_timestamp"]) if parsed["event_start_unix_timestamp"] else None
            parts = ev_url.split("?")[0].strip("/").split("/")
            region = parts[2].replace("_", " ") if len(parts) > 5 else ""
            comp = parts[3].replace("_", " ") if len(parts) > 5 else ""
            # Note: OLBG stores UK Greyhound daily races inside `tournaments:[...]` with market_alias="Daily Races"
            actual_kind = "daily_race" if (sport_id == 28 and parsed["market_alias"] == "Daily Races") else kind
            rows.append(
                {
                    "sport": sport_name,
                    "olbg_sport_id": sport_id,
                    "in_scope": in_scope,
                    "row_kind": actual_kind,
                    "sveltek_array": "tips" if kind == "match" else "tournaments",
                    "event_id": int(ev_id_m.group(1)) if ev_id_m else None,
                    "event_name": parsed["event_name_alias"],
                    "olbg_url": "https://www.olbg.com" + ev_url if ev_url.startswith("/") else ev_url,
                    "olbg_region_path": region,
                    "olbg_competition_path": comp,
                    "olbg_menu_league": parsed["menu_league"],
                    "start_unix": ts,
                    "start_utc": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None,
                    "market_label": parsed["market_alias"] or "",
                    "featured_selection": parsed["selection"],
                    "featured_price_decimal": float(parsed["odds"]) if parsed["odds"] and parsed["odds"] not in ("", "SP", "-") else None,
                    "featured_price_raw": parsed["odds"],
                    "featured_price_american": int(float(parsed["american_odds"])) if parsed["american_odds"] and re.match(r"^[+-]?\d+(\.\d+)?$", parsed["american_odds"]) else None,
                    "expired_flag": int(parsed["expired"]) if parsed["expired"] is not None else 0,
                    "venue": parsed["venue"],
                    "hub_sha256": item["sha256"],
                    "captured_utc": item["fetched_utc"],
                }
            )

    seen, deduped = set(), []
    for r in rows:
        key = (r["olbg_sport_id"], r["event_id"], r["market_label"], r["featured_selection"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    payload = {
        "schema": "olbg4.board-z.olbg_inventory/v1",
        "capture_dir": cap_dir,
        "manifest_generated_utc": manifest["generated_utc"],
        "robots_txt_policy": {
            "url": "https://www.olbg.com/robots.txt",
            "allowed_fetched": ["/betting-tips", "/betting-tips/<Sport>/<id>"],
            "disallowed_never_called": ["/api/svelte", "/sports/<Sport>/top_tips", "/events.php", "/tips/hot", "/tipster/"],
        },
        "reverse_engineering_findings": [
            "OLBG sport hubs are SvelteKit SSR pages embedding two JS object literals in hydration script blocks: `tips:[...]` (individual fixtures) and `tournaments:[...]` (antepost outrights, plus UK Greyhound daily races).",
            "Machine-readable UTC start time is embedded as `event_start_unix_timestamp` (Unix epoch seconds), whereas visible HTML clock strings render in the client/proxy timezone (observed EDT UTC-4 on US-proxied fetches, e.g. 14:45 display for 18:45Z Darts).",
            "Clicking 'Load More Tips' calls `/api/svelte` backed by `/sports/<Sport>/top_tips?paginate=1-100&include_expired=1`; both paths are disallowed for all user-agents in OLBG's robots.txt and were strictly not requested.",
            "Greyhounds daily races (e.g. 11:14 Kinsley, 11:36 Sheffield) are serialized inside `tournaments:[...]` with `market_alias:\"Daily Races\"` and `odds:\"SP\"` rather than inside `tips:[...]`.",
            "Sports menu on `/betting-tips` exposes 21 top-level sport links; 6 are explicitly excluded by brief (Football/Soccer id=1, Horse Racing id=2, American Football id=11, Boxing id=16, Cycling id=17, Hurling id=26), while UFC/MMA and Specials are non-top-level/absent and also excluded. Badminton and Table Tennis have no top-level OLBG hub link on 2026-10-22 and are supplemented directly from official BWF and ITTF/WTT calendars.",
        ],
        "discovered_sports_menu_links": all_hub_menu_links,
        "excluded_sport_ids": EXCLUDED_OLBG_SPORTS,
        "hubs": hubs,
        "events": deduped,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return payload


if __name__ == "__main__":
    cap = sys.argv[1] if len(sys.argv) > 1 else "data/session-9359e596/capture/20261022T073346Z"
    out = sys.argv[2] if len(sys.argv) > 2 else "data/session-9359e596/olbg_inventory.json"
    res = parse_capture(cap, out)
    print(f"Parsed {len(res['hubs'])} hubs -> {len(res['events'])} unique in-scope OLBG rows")

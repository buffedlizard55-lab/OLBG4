#!/usr/bin/env python3
"""Board W - parse OLBG hub captures into a structural event inventory.

Reads only the bytes committed by the runner under
data/session-c4fda15e/capture/<stamp>/raw/olbg_*.html.gz (manifest lists URL,
HTTP status and SHA-256). Each hub page embeds its SvelteKit hydration data,
which contains a `tips:[{...}]` array; every element describes one listed event
with a machine timestamp (`event_start_unix_timestamp`, seconds since epoch, UTC).

Kept per event (structure + market reference only): event_id, event name,
OLBG event URL, competition/league path, UTC start, market label, the featured
selection's displayed price (decimal + American) and whether OLBG marks it expired.
NOT kept: tip counts, tip percentages, star ratings, comments, tipster data.

The "Load More Tips" button fetches further rows from https://www.olbg.com/api/svelte,
a path disallowed for all agents by OLBG's robots.txt; it is therefore not called,
and the inventory is limited to the rows each hub embeds server-side.

Usage: python3 parse_olbg.py <capture_dir> <out_json>
"""
from __future__ import annotations

import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

SPORTS = {  # OLBG sport id -> (display name, in_scope, scope_note)
    3: ("Tennis", True, ""), 4: ("Basketball", True, ""), 5: ("Golf", True, ""),
    7: ("Cricket", True, ""), 8: ("Snooker", True, ""), 9: ("Rugby Union", True, ""),
    10: ("Rugby League", True, ""), 12: ("Baseball", True, ""), 13: ("Ice Hockey", True, ""),
    14: ("Motor Racing", True, ""), 15: ("Darts", True, ""), 20: ("Handball", True, ""),
    21: ("Volleyball", True, ""), 22: ("Aussie Rules", True, ""), 23: ("eSports", True, ""),
    25: ("Gaelic Football", True, "scope-ambiguous: the brief excludes 'football'; OLBG files Gaelic Football "
         "(id 25) separately from Football (id 1). Included and flagged for the owner's decision."),
    28: ("Greyhounds", True, ""),
}

FIELD_RE = {
    "selection": r'selection:"((?:[^"\\]|\\.)*)"',
    "market_alias": r'market_alias:"((?:[^"\\]|\\.)*)"',
    "odds": r'odds:"([^"]*)"',
    "american_odds": r'american_odds:"([^"]*)"',
    "event_start_unix_timestamp": r'event_start_unix_timestamp:(\d+)',
    "eventUrl": r'eventUrl:"((?:[^"\\]|\\.)*)"',
    "leagueUrl": r'leagueUrl:"((?:[^"\\]|\\.)*)"',
    "event_name_alias": r'event_name_alias:"((?:[^"\\]|\\.)*)"',
    "menu_league": r'menu_league:(?:"((?:[^"\\]|\\.)*)"|null)',
    "expired": r'expired:(\d)',
    "venue": r'venue:(?:"((?:[^"\\]|\\.)*)"|null)',
}


def tips_objects(html: str, key: str = "tips") -> list[str]:
    """Return the raw text of each object in the first `<key>:[` array of the hydration script."""
    k = html.find(key + ":[{id:")
    if k < 0:
        return []
    i = k + len(key + ":[")
    depth, start, objs, in_str, esc = 0, None, [], False, False
    while i < len(html):
        c = html[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                if depth == 0:
                    start = i
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0 and start is not None:
                    objs.append(html[start:i + 1])
                    start = None
            elif c == "]" and depth == 0:
                break
        i += 1
    return objs


def unesc(s: str | None) -> str | None:
    if s is None:
        return None
    return json.loads('"' + s + '"')


def main() -> int:
    cap, out = sys.argv[1], sys.argv[2]
    man = json.load(open(os.path.join(cap, "manifest.json"), encoding="utf-8"))
    rows, hubs = [], []
    for it in man["items"]:
        m = re.match(r"olbg_(.+)_(\d+)$", it["id"])
        if not m:
            continue
        sid = int(m.group(2))
        name, in_scope, note = SPORTS.get(sid, (m.group(1), False, "not an in-scope OLBG sport id"))
        html = gzip.open(os.path.join(cap, it["file"])).read().decode("utf-8", "replace")
        match_objs = tips_objects(html, "tips")
        outright_objs = tips_objects(html, "tournaments")
        rendered_more = "Load More Tips" in html
        api = re.search(r'tipsApiUrl:"([^"]*)"', html)
        api_path = unesc(api.group(1)).split("&ti=")[0] if api else None
        hubs.append({"sport": name, "olbg_sport_id": sid, "hub_url": it["url"], "http_status": it["status"],
                     "sha256": it["sha256"], "fetched_utc": it["fetched_utc"],
                     "embedded_match_rows": len(match_objs), "embedded_outright_rows": len(outright_objs),
                     "load_more_button": rendered_more, "tips_api_path_disallowed": api_path,
                     "in_scope": in_scope, "scope_note": note})
        for kind, o in [("match", x) for x in match_objs] + [("outright", x) for x in outright_objs]:
            f = {}
            for key, rx in FIELD_RE.items():
                mm = re.search(rx, o)
                f[key] = unesc(mm.group(1)) if (mm and mm.group(1) is not None) else None
            eu = f["eventUrl"] or ""
            em = re.search(r"event_id=(\d+)", eu)
            ts = int(f["event_start_unix_timestamp"]) if f["event_start_unix_timestamp"] else None
            parts = eu.split("?")[0].strip("/").split("/")
            # /betting-tips/<Sport>/<Region>/<Competition>/<Event>/<sid>
            region = parts[2] if len(parts) > 5 else ""
            comp = parts[3] if len(parts) > 5 else ""
            rows.append({
                "sport": name, "olbg_sport_id": sid, "in_scope": in_scope, "row_kind": kind,
                "event_id": int(em.group(1)) if em else None,
                "event_name": f["event_name_alias"],
                "olbg_url": "https://www.olbg.com" + eu if eu.startswith("/") else eu,
                "olbg_region_path": region.replace("_", " "),
                "olbg_competition_path": comp.replace("_", " "),
                "olbg_menu_league": f["menu_league"],
                "start_utc": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None,
                "market_label": f["market_alias"],
                "featured_selection": f["selection"],
                "featured_price_decimal": f["odds"],
                "featured_price_american": f["american_odds"],
                "expired_flag": f["expired"],
                "venue": f["venue"],
                "hub_sha256": it["sha256"],
                "captured_utc": it["fetched_utc"],
            })
    # de-duplicate (the all-sports hub repeats events from sport hubs)
    seen, uniq = set(), []
    for r in rows:
        key = (r["olbg_sport_id"], r["event_id"], r["market_label"], r["featured_selection"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    json.dump({"capture_dir": cap, "manifest_generated_utc": man["generated_utc"], "hubs": hubs,
               "events": uniq}, open(out, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"{len(hubs)} hubs, {len(uniq)} unique rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

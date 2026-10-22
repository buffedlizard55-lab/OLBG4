#!/usr/bin/env python3
"""Board AF (session arena/ddbcc895-olbg4) — OLBG reverse-engineering parser.

Reads the byte-exact gzip captures committed by `.github/workflows/af-ddbcc895.yml`
and extracts the server-rendered SvelteKit hydration data from every OLBG hub page:

  * `tips:[...]`        individual fixture rows (one object per market selection)
  * `tournaments:[...]` antepost outrights, plus UK greyhound "Daily Races" rows

Every digest is re-checked against `manifest.json` before a file is parsed. OLBG is
used only for (a) the sport taxonomy, (b) the live match list and (c) a reference
price. It is never the source of a published own-line: that comes from the official
governing-body page recorded on each desk row.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

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
    18: "Badminton",
    20: "Handball",
    21: "Volleyball",
    22: "Aussie Rules",
    23: "eSports",
    24: "Table Tennis",
    25: "Gaelic Football",
    28: "Greyhounds",
}

EXCLUDED = {
    1: "Football (association / soccer)",
    2: "Horse Racing",
    11: "American Football",
    16: "Boxing, UFC & MMA",
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
    """Return every top-level object literal inside `key:[ ... ]` (string-aware)."""
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


def unescape(val: str | None) -> str | None:
    if val is None:
        return None
    try:
        return json.loads('"' + val + '"')
    except Exception:
        return val


def parse(cap_dir: Path) -> dict:
    manifest = json.loads((cap_dir / "manifest.json").read_text(encoding="utf-8"))
    hubs, events, outrights = [], [], []
    menu_links: list[str] = []

    for item in manifest["items"]:
        if not item["id"].startswith("olbg_"):
            continue
        if item.get("status") != 200 or not item.get("file"):
            hubs.append(
                {
                    "id": item["id"],
                    "url": item["url"],
                    "http_status": item.get("status"),
                    "error": item.get("error", ""),
                    "in_scope": None,
                }
            )
            continue

        raw = gzip.open(cap_dir / item["file"], "rb").read()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != item["sha256"]:
            raise ValueError(f"SHA-256 mismatch on {item['id']}: {digest} != {item['sha256']}")
        html = raw.decode("utf-8", "replace")

        if item["id"] == "olbg_all":
            menu_links = sorted(set(re.findall(r"/betting-tips/([A-Za-z0-9_]+)/(\d+)", html)))
            hubs.append({"id": "olbg_all", "url": item["url"], "http_status": 200, "sha256": digest})
            continue

        m = re.match(r"olbg_(.+)_(\d+)$", item["id"])
        if not m:
            # Named sub-hubs (olbg_nba, olbg_nhl, ...) carry the sport id in the URL.
            sm = re.search(r"/(\d+)$", item["url"])
            if not sm:
                continue
            sport_id = int(sm.group(1))
            sport_name = SPORTS.get(sport_id)
            if not sport_name:
                continue
            hub_kind = "sub"
        else:
            sport_id = int(m.group(2))
            sport_name = SPORTS.get(sport_id)
            if not sport_name:
                continue
            hub_kind = "top"

        scope = "in" if sport_id in SPORTS and sport_id != 25 else ("ambiguous" if sport_id == 25 else "out")
        match_objs = extract_array_objects(html, "tips")
        tour_objs = extract_array_objects(html, "tournaments")
        hubs.append(
            {
                "id": item["id"],
                "sport": sport_name,
                "olbg_sport_id": sport_id,
                "hub_kind": hub_kind,
                "url": item["url"],
                "http_status": 200,
                "sha256": digest,
                "fetched_utc": item.get("fetched_utc"),
                "bytes": item.get("bytes"),
                "embedded_match_rows": len(match_objs),
                "embedded_tournament_rows": len(tour_objs),
                "in_scope": scope,
            }
        )

        for kind, raw_obj in [("match", x) for x in match_objs] + [("outright", x) for x in tour_objs]:
            f = {}
            for fk, rx in FIELD_RE.items():
                mm = re.search(rx, raw_obj)
                f[fk] = unescape(mm.group(1)) if (mm and mm.group(1) is not None) else None
            ev_url = f["eventUrl"] or ""
            ev_id_m = re.search(r"event_id=(\d+)", ev_url)
            ts = int(f["event_start_unix_timestamp"]) if f["event_start_unix_timestamp"] else None
            parts = ev_url.split("?")[0].strip("/").split("/")
            region = parts[2].replace("_", " ") if len(parts) > 5 else ""
            comp = parts[3].replace("_", " ") if len(parts) > 5 else ""
            actual = kind
            if sport_id == 28 and f["market_alias"] == "Daily Races":
                actual = "daily_race"
            rec = {
                "sport": sport_name,
                "olbg_sport_id": sport_id,
                "in_scope": scope,
                "row_kind": actual,
                "event_id": int(ev_id_m.group(1)) if ev_id_m else None,
                "event_name": f["event_name_alias"],
                "olbg_url": ("https://www.olbg.com" + ev_url) if ev_url.startswith("/") else ev_url,
                "olbg_region_path": region,
                "olbg_competition_path": comp,
                "olbg_menu_league": f["menu_league"],
                "start_utc": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else None,
                "market_label": f["market_alias"] or "",
                "featured_selection": f["selection"],
                "featured_price_decimal": float(f["odds"]) if f["odds"] and re.match(r"^\d+(\.\d+)?$", f["odds"]) else None,
                "featured_price_raw": f["odds"],
                "venue": f["venue"],
                "expired": int(f["expired"]) if f["expired"] is not None else 0,
                "hub_sha256": digest,
                "captured_utc": item.get("fetched_utc"),
            }
            (events if actual in ("match", "daily_race") else outrights).append(rec)

    # Collapse the one-object-per-selection rows into one row per OLBG event.
    def collapse(rows: list[dict]) -> list[dict]:
        by_id: dict[tuple, dict] = {}
        for r in rows:
            key = (r["olbg_sport_id"], r["event_id"] or r["olbg_url"] or r["event_name"])
            cur = by_id.get(key)
            if cur is None:
                rec = dict(r)
                rec["markets_seen"] = [r["market_label"]] if r["market_label"] else []
                rec["selections_seen"] = 1
                by_id[key] = rec
            else:
                if r["market_label"] and r["market_label"] not in cur["markets_seen"]:
                    cur["markets_seen"].append(r["market_label"])
                cur["selections_seen"] += 1
        out = list(by_id.values())
        for r in out:
            r["markets_seen"] = sorted(set(x for x in r["markets_seen"] if x))
        out.sort(key=lambda x: (x["sport"], x["start_utc"] or "", x["event_name"] or ""))
        return out

    return {
        "schema": "olbg4.board-af.olbg_inventory/1",
        "capture_dir": str(cap_dir.relative_to(ROOT)) if cap_dir.is_relative_to(ROOT) else str(cap_dir),
        "manifest_generated_utc": manifest.get("generated_utc"),
        "taxonomy_source": "https://www.olbg.com/betting-tips",
        "excluded_sports": EXCLUDED,
        "sport_menu_links": [{"path": f"/betting-tips/{a}/{b}", "sport": a, "olbg_id": int(b)} for a, b in menu_links],
        "hubs": hubs,
        "events": collapse(events),
        "outrights": collapse(outrights),
    }


if __name__ == "__main__":
    cap = Path(sys.argv[1])
    out = Path(sys.argv[2])
    payload = parse(cap)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"hubs={len(payload['hubs'])} events={len(payload['events'])} outrights={len(payload['outrights'])}")

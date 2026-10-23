#!/usr/bin/env python3
"""Board AT — reverse-engineer the OLBG.com public sport hubs.

OLBG renders each sport hub as a SvelteKit page whose inlined data payload carries, verbatim:

  * ``megaMenu:[{title,url,type,sportId,rank,hasItems},…]`` — the full sport taxonomy, i.e. every
    sport OLBG covers with its hub URL and numeric ``sportId``;
  * ``tips:[{…},…]`` — one object per **listed event/market**, carrying the selection, the market
    alias, the price in decimal / American / fractional form, the event start unix timestamp, the
    event name, the event URL (with its ``event_id``), the league URL, tip counts, OLBG's own
    confidence percent and star rating;
  * ``sportId`` / ``sportName`` / ``pageType`` for the hub itself.

ROLE LIMIT — this is important and is enforced downstream. OLBG is a tipster community, not a
league, tour or federation. Under this repo's verification rule these payloads are used **only**
to (a) reverse-engineer OLBG's sport and market taxonomy, (b) enumerate which events OLBG lists
for the 15 in-scope sports and (c) cross-check that a fixture we verified from an official source
is actually bettable on OLBG. No published start time, team, price, statistic or confidence grade
on this desk is taken from OLBG. Every one of those comes from an official source capture, and the
OLBG listing is recorded alongside as ``olbg_listed`` with its own URL.

Output: data/session-086e616f/olbg_taxonomy.json and data/session-086e616f/olbg_inventory.json
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from capture_lib import OUT_ROOT, Capture, write_json  # noqa: E402

# sport label on this desk -> the OLBG hub capture target id (pass-1 names)
HUBS = {
    "Golf": "olbg_golf",
    "Volleyball": "olbg_volleyball",
    "Rugby Union": "olbg_rugby_union",
    "Cricket": "olbg_cricket",
    "Snooker": "olbg_snooker",
    "Darts": "olbg_darts",
    "Baseball": "olbg_baseball",
    "Gaelic Sports": "olbg_gaelic_football",
    "Greyhounds": "olbg_greyhounds",
    "Tennis": "olbg_tennis",
    "Motor Racing": "olbg_motor_racing",
    "Handball": "olbg_handball",
    "Ice Hockey": "olbg_ice_hockey",
    "Basketball": "olbg_basketball",
    "Rugby League": "olbg_rugby_league",
}
# OLBG calls this sport "Gaelic Football"; the brief calls it "Gaelic Sports".
OLBG_TITLE_FOR_SCOPE = {sport: sport for sport in HUBS}
OLBG_TITLE_FOR_SCOPE["Gaelic Sports"] = "Gaelic Football"
SUB_HUBS = {
    "olbg_sub_basketball_nba_4": ("Basketball", "NBA"),
    "olbg_sub_basketball_european_euroleague_4": ("Basketball", "Euroleague"),
    "olbg_sub_basketball_other_4": ("Basketball", "Other"),
    "olbg_sub_ice_hockey_nhl_13": ("Ice Hockey", "NHL"),
    "olbg_sub_ice_hockey_other_13": ("Ice Hockey", "Other"),
}

VALUE = r'(?:"((?:[^"\\]|\\.)*)"|(-?\d+(?:\.\d+)?)|(null)|(void 0)|(true|false))'
FIELD = re.compile(r"([a-zA-Z_][a-zA-Z0-9_]*):" + VALUE)


def split_objects(blob: str) -> list[str]:
    """Split a ``[{…},{…}]`` body into its top-level object bodies."""
    out, depth, start = [], 0, None
    in_str = False
    i = 0
    while i < len(blob):
        ch = blob[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch in "{[":
                depth += 1
                if depth == 1 and ch == "{":
                    start = i + 1
            elif ch in "}]":
                depth -= 1
                if depth == 0 and ch == "}" and start is not None:
                    out.append(blob[start:i])
                    start = None
                if depth < 0:
                    break
        i += 1
    return out


def parse_object(body: str) -> dict:
    rec: dict = {}
    for m in FIELD.finditer(body):
        key = m.group(1)
        if key in rec:
            continue
        if m.group(2) is not None:
            val: object = m.group(2)
        elif m.group(3) is not None:
            val = int(m.group(3)) if re.fullmatch(r"-?\d+", m.group(3)) else float(m.group(3))
        elif m.group(4) is not None:
            val = None
        elif m.group(5) is not None:
            val = None
        else:
            val = m.group(6) == "true"
        rec[key] = val
    return rec


def array_after(html_text: str, key: str) -> list[dict]:
    m = re.search(re.escape(key) + r":\[", html_text)
    if not m:
        return []
    depth = 0
    i = m.end() - 1
    in_str = False
    while i < len(html_text):
        ch = html_text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_str = False
        else:
            if ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return [parse_object(b) for b in split_objects(html_text[m.end():i])]
        i += 1
    return []


def scalar(html_text: str, key: str):
    m = re.search(re.escape(key) + r":" + VALUE, html_text)
    if not m:
        return None
    if m.group(1) is not None:
        return m.group(1)
    if m.group(2) is not None:
        return m.group(2)
    return None


def start_iso(ts) -> str | None:
    if ts in (None, "", "null"):
        return None
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def build() -> tuple[dict, dict]:
    cap = Capture()
    taxonomy_rows: list[dict] = []
    events: list[dict] = []
    hubs: list[dict] = []

    # ---- the whole OLBG sport taxonomy, from any hub's megaMenu (identical across hubs)
    mega: list[dict] = []
    mega_source: str | None = None
    for target in list(HUBS.values()) + list(SUB_HUBS):
        if not cap.have(target):
            continue
        mega = array_after(cap.text(target), "megaMenu")
        if mega:
            mega_source = target
            break
    in_scope_titles = set(OLBG_TITLE_FOR_SCOPE.values())
    for row in mega:
        taxonomy_rows.append(
            {
                "title": row.get("title"),
                "sport_id": row.get("sportId"),
                "hub_url": ("https://www.olbg.com" + row["url"]) if row.get("url") else None,
                "type": row.get("type"),
                "rank": row.get("rank"),
                "in_scope": row.get("title") in in_scope_titles,
                "listed_in": "megaMenu",
                "source_url": cap.url(mega_source) if mega_source else None,
            }
        )

    # ---- the complete OLBG sport list, from the public betting-tips sitemap
    sitemap: list[dict] = []
    if cap.have("olbg_sitemap_tips"):
        body = cap.text("olbg_sitemap_tips")
        seen = set()
        for loc in re.findall(r"<loc>\s*(.*?)\s*</loc>", body, flags=re.S):
            m = re.match(r"https://www\.olbg\.com/betting-tips/([A-Za-z_]+)/(\d+)$", loc)
            if not m or m.group(1) in seen:
                continue
            seen.add(m.group(1))
            title = m.group(1).replace("_", " ")
            sitemap.append(
                {
                    "title": title,
                    "slug": m.group(1),
                    "sport_id": int(m.group(2)),
                    "hub_url": loc,
                    "listed_in": "sitemap-betting-tips.xml",
                    "in_scope": title in in_scope_titles,
                    "source_url": cap.url("olbg_sitemap_tips"),
                }
            )
        sitemap.sort(key=lambda r: r["slug"])

    # ---- per-hub listings
    for sport, target in sorted(HUBS.items()):
        hub: dict = {
            "sport": sport,
            "hub_capture_id": target,
            "captured": cap.have(target),
        }
        if cap.have(target):
            text = cap.text(target)
            tips = array_after(text, "tips")
            hub.update(
                {
                    "hub_url": cap.url(target),
                    "olbg_sport_id": scalar(text, "sportId"),
                    "olbg_sport_name": scalar(text, "sportName"),
                    "page_type": scalar(text, "pageType"),
                    "listed_events": len(tips),
                    "capture": cap.provenance(target),
                }
            )
            for tip in tips:
                events.append(_event(sport, target, tip, hub_only=False))
        else:
            hub.update({"hub_url": None, "listed_events": 0, "capture": None})
        hubs.append(hub)

    for target, (sport, label) in sorted(SUB_HUBS.items()):
        if not cap.have(target):
            continue
        text = cap.text(target)
        tips = array_after(text, "tips")
        hubs.append(
            {
                "sport": sport,
                "competition_label": label,
                "hub_capture_id": target,
                "captured": True,
                "hub_url": cap.url(target),
                "olbg_sport_id": scalar(text, "sportId"),
                "listed_events": len(tips),
                "capture": cap.provenance(target),
            }
        )
        for tip in tips:
            events.append(_event(sport, target, tip, hub_only=False, competition_label=label))

    taxonomy = {
        "schema": "olbg4.board-at.olbg-taxonomy/1",
        "board": "AT",
        "session": "arena/086e616f-olbg4",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role_limit": (
            "OLBG is a tipster community, not a governing body. These payloads are used only to "
            "reverse-engineer OLBG's sport/market taxonomy, to enumerate which events OLBG lists "
            "for the 15 in-scope sports, and to cross-check that an officially verified fixture is "
            "bettable on OLBG. No start time, team, price, statistic or confidence grade published "
            "on this desk is taken from OLBG."
        ),
        "capture_summary": cap.summary(),
        "sports_on_olbg": taxonomy_rows,
        "sports_from_sitemap": sitemap,
        "hubs": hubs,
        "market_aliases": sorted({e["market_alias"] for e in events if e.get("market_alias")}),
        "markets_by_sport": {},
        "counts": {
            "olbg_sports_megamenu": len(taxonomy_rows),
            "olbg_sports_sitemap": len(sitemap),
            "olbg_sports_in_scope": sum(1 for r in sitemap if r["in_scope"]),
            "hubs_captured": sum(1 for h in hubs if h.get("captured")),
            "listed_event_markets": len(events),
            "listed_events_distinct": len({e["event_url"] for e in events if e.get("event_url")}),
        },
    }
    per_sport_markets: dict[str, set] = {}
    for e in events:
        if e.get("market_alias"):
            per_sport_markets.setdefault(e["sport"], set()).add(e["market_alias"])
    taxonomy["markets_by_sport"] = {k: sorted(v) for k, v in sorted(per_sport_markets.items())}

    inventory = {
        "schema": "olbg4.board-at.olbg-inventory/1",
        "board": "AT",
        "session": "arena/086e616f-olbg4",
        "role_limit": taxonomy["role_limit"],
        "events": sorted(events, key=lambda e: (e["sport"], e.get("start_utc") or "", e.get("event_name") or "")),
    }
    return taxonomy, inventory


def _event(sport: str, target: str, tip: dict, hub_only: bool = False, competition_label: str | None = None) -> dict:
    ev = tip.get("eventUrl") or ""
    event_id = None
    m = re.search(r"event_id=(\d+)", ev)
    if m:
        event_id = m.group(1)
    return {
        "sport": sport,
        "competition_label": competition_label or tip.get("menu_league"),
        "event_name": tip.get("event_name_alias"),
        "event_id": event_id,
        "event_url": ("https://www.olbg.com" + ev) if ev else None,
        "league_url": ("https://www.olbg.com" + tip["leagueUrl"]) if tip.get("leagueUrl") else None,
        "category_url": ("https://www.olbg.com" + tip["categoryUrl"]) if tip.get("categoryUrl") else None,
        "market_alias": tip.get("market_alias"),
        "selection": tip.get("selection"),
        "olbg_decimal": tip.get("odds"),
        "olbg_american": tip.get("american_odds"),
        "olbg_fractional": tip.get("fractional_odds"),
        "start_unix": tip.get("event_start_unix_timestamp"),
        "start_utc": start_iso(tip.get("event_start_unix_timestamp")),
        "olbg_confidence": tip.get("confidence"),
        "stars_rating": tip.get("stars_rating"),
        "win_tips": tip.get("win_tips"),
        "win_tips_count": tip.get("win_tips_count"),
        "experts_count": tip.get("experts_count"),
        "comments_count": tip.get("comments_count"),
        "expired": tip.get("expired"),
        "venue": tip.get("venue"),
        "vc_sport_id": tip.get("vc_sport_id"),
        "vc_outcome_id": tip.get("vc_outcome_id"),
        "hub_capture_id": target,
    }


def main() -> int:
    taxonomy, inventory = build()
    write_json(OUT_ROOT / "olbg_taxonomy.json", taxonomy)
    write_json(OUT_ROOT / "olbg_inventory.json", inventory)
    c = taxonomy["counts"]
    print(
        f"OLBG taxonomy: {c['olbg_sports_sitemap']} sports in sitemap-betting-tips.xml "
        f"({c['olbg_sports_megamenu']} of them surfaced in the hub megaMenu), "
        f"{c['olbg_sports_in_scope']} of them in the requested 15-sport scope; "
        f"{c['hubs_captured']} hubs captured; {c['listed_events_distinct']} distinct listed events "
        f"across {c['listed_event_markets']} listed event/markets."
    )
    print("market aliases:", ", ".join(taxonomy["market_aliases"]))
    per_sport: dict[str, int] = {}
    for ev in inventory["events"]:
        per_sport[ev["sport"]] = per_sport.get(ev["sport"], 0) + 1
    for sport in sorted(per_sport):
        print(f"  {sport:<15} {per_sport[sport]:>4} listed event/markets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

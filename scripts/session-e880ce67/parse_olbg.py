#!/usr/bin/env python3
"""Parse the committed OLBG hub captures into a fixture inventory.

Two sources exist in the same response and both are used:

1. **The SvelteKit hydration payload.**  Each hub embeds
   `data:{tips:[{id, selection, market_alias, odds, american_odds, fractional_odds,
   event_start_unix_timestamp, eventUrl, event_name_alias, win_tips, win_tips_count,
   confidence, experts_count, venue, expired}, ...]}`.  This is the complete tipped-event
   feed the page was rendered from - it includes events that the visible list lazily
   renders, and it carries the price OLBG quotes for the tipped selection.
2. **The rendered rows**, used only to attach the competition name where OLBG prints one
   (the payload's `menu_league` is null on these pages).

Nothing is inferred: an event without a payload record is published without a price, and
an event whose start timestamp is absent is published with a blank start.

OLBG only renders events that carry at least one public tip, so this inventory means
"events OLBG currently offers with tipster coverage", not every fixture in world sport.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "data", "session-e880ce67", "raw", "olbg")
OUT = os.path.join(ROOT, "data", "session-e880ce67", "olbg.json")
sys.path.insert(0, HERE)
from spec import OLBG, OLBG_URLS  # noqa: E402

SPORT_LABEL = {
    "golf": "Golf", "volleyball": "Volleyball", "rugby_union": "Rugby Union",
    "cricket": "Cricket", "snooker": "Snooker", "darts": "Darts",
    "baseball": "Baseball", "gaelic_football": "Gaelic Football", "hurling": "Hurling",
    "greyhounds": "Greyhounds", "tennis": "Tennis", "motor_racing": "Motor Racing",
    "handball": "Handball", "ice_hockey": "Ice Hockey", "basketball": "Basketball",
    "rugby_league": "Rugby League",
}

ROW = re.compile(r'<li class="min-h-\[\d+px\]">(?:(?!<li class="min-h-\[\d+px\]">).)*', re.S)
EVENT_HREF = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"]+?event_id=(\d+))"')
COMPETITION = re.compile(r'<p class="text-sm truncate"><i class="i-ui-trophy[^"]*"></i>\s*(.*?)</p>', re.S)
START = re.compile(r'itemprop="startDate"\s+datetime="([^"]+)"')
FIELD = re.compile(r'(\w+):(?:"((?:[^"\\]|\\.)*)"|(-?\d+(?:\.\d+)?)|null)')


def text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def dom_rows(body: str) -> list[dict]:
    rows = []
    for block in ROW.finditer(body):
        chunk = block.group(0)
        href = EVENT_HREF.search(chunk)
        if not href:
            continue
        start = START.search(chunk)
        comp = COMPETITION.search(chunk)
        rows.append({"event_id": href.group(2), "olbg_url": href.group(1),
                     "start_utc": start.group(1) if start else "",
                     "competition": text(comp.group(1)) if comp else ""})
    return rows


def payload(row_html: str) -> list[dict]:
    """Every tip object in the page's hydration payload."""
    out = []
    for marker in ("data:{tips:[", "tips:[{"):
        start = row_html.find(marker)
        if start < 0:
            continue
        body = row_html[start + len(marker):]
        # objects are flat, so the array ends at the first "]}"
        end = body.find("]}")
        if end < 0:
            continue
        blob = body[:end]
        for raw in blob.split("},{"):
            rec = {}
            for key, sval, nval in FIELD.findall(raw):
                rec[key] = sval if sval else (float(nval) if "." in nval else int(nval)) \
                    if nval else None
            if rec.get("eventUrl"):
                out.append(rec)
        if out:
            break
    return out


def _num(value):
    """Odds are usually a decimal string; some rows quote 'SP' (starting price)."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value):
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def iso(ts) -> str:
    if not isinstance(ts, (int, float)):
        return ""
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_hub(key: str) -> tuple[list[dict], list[dict]]:
    path = os.path.join(RAW, f"hub_{key}.html")
    if not os.path.exists(path):
        return [], []
    body = open(path, encoding="utf-8", errors="replace").read()
    dom = dom_rows(body)
    comp_by_event = {r["event_id"]: r["competition"] for r in dom if r["competition"]}
    start_by_event = {r["event_id"]: r["start_utc"] for r in dom if r["start_utc"]}
    tips = payload(body)
    rows, seen = [], set()
    for tip in tips:
        url = tip.get("eventUrl") or ""
        eid = url.split("event_id=")[-1] if "event_id=" in url else ""
        if not eid:
            continue
        start = iso(tip.get("event_start_unix_timestamp")) or start_by_event.get(eid, "")
        rows.append({
            "sport_key": key, "sport": SPORT_LABEL[key], "sport_id": OLBG[key][0],
            "olbg_url": "https://www.olbg.com" + url if url.startswith("/") else url,
            "event_id": eid,
            "event_name": tip.get("event_name_alias") or "",
            "start_utc": start,
            "selection": tip.get("selection") or "",
            "market": tip.get("market_alias") or "",
            "olbg_decimal": _num(tip.get("odds")),
            "olbg_american": _int(tip.get("american_odds")),
            "olbg_fractional": tip.get("fractional_odds") or "",
            "tips_won": tip.get("win_tips"), "tips_total": tip.get("win_tips_count"),
            "tip_pct": tip.get("confidence"),
            "experts": tip.get("experts_count"),
            "venue": tip.get("venue") or "",
            "competition": comp_by_event.get(eid, ""),
            "expired": bool(tip.get("expired")),
        })
        seen.add(eid)
    # events rendered in the DOM but missing from the payload are kept, unpriced
    for row in dom:
        if row["event_id"] in seen:
            continue
        seen.add(row["event_id"])
        rows.append({
            "sport_key": key, "sport": SPORT_LABEL[key], "sport_id": OLBG[key][0],
            "olbg_url": row["olbg_url"], "event_id": row["event_id"], "event_name": "",
            "start_utc": row["start_utc"], "selection": "", "market": "",
            "olbg_decimal": None, "olbg_american": None, "olbg_fractional": "",
            "tips_won": None, "tips_total": None, "tip_pct": None, "experts": None,
            "venue": "", "competition": row["competition"], "expired": False,
        })
    return rows, tips


def main() -> int:
    manifest = json.load(open(os.path.join(ROOT, "data", "session-e880ce67", "raw",
                                           "manifest.json"), encoding="utf-8"))
    out = {"schema": "olbg4.ds.olbg/1",
           "source": "OLBG.com sport hub pages (SvelteKit hydration payload + rendered rows), "
                     "fetched and committed by the Board DS runner",
           "captured_utc": manifest["captured_utc"],
           "hub_urls": {k: v for k, v in OLBG_URLS.items() if k.startswith("hub_")},
           "sports": {}, "events": [], "rows": [], "payload_counts": {}}
    for key in OLBG:
        rows, tips = parse_hub(key)
        events = {}
        for row in rows:
            ev = events.setdefault(row["event_id"], {
                "sport": row["sport"], "sport_key": key, "sport_id": row["sport_id"],
                "event_id": row["event_id"], "event_name": row["event_name"],
                "start_utc": row["start_utc"], "olbg_url": row["olbg_url"],
                "competition": row["competition"], "selections": [], "markets": [],
            })
            if row["selection"]:
                ev["selections"].append(row["selection"])
            if row["market"] and row["market"] not in ev["markets"]:
                ev["markets"].append(row["market"])
            if not ev["event_name"] and row["event_name"]:
                ev["event_name"] = row["event_name"]
        out["sports"][key] = {"label": SPORT_LABEL[key], "sport_id": OLBG[key][0],
                              "hub_url": OLBG_URLS[f"hub_{key}"],
                              "tip_rows": len(rows), "events": len(events),
                              "payload_records": len(tips)}
        out["events"].extend(events.values())
        out["rows"].extend(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    total = 0
    for key, meta in out["sports"].items():
        print(f"{meta['label']:16} events={meta['events']:3} tips={meta['tip_rows']:3}"
              f" payload={meta['payload_records']:3}")
        total += meta["events"]
    print(f"TOTAL events={total} tips={len(out['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

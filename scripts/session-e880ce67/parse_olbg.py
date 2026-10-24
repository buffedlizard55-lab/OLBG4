#!/usr/bin/env python3
"""Parse the committed OLBG hub captures into a fixture inventory.

Input : data/session-e880ce67/raw/olbg/hub_*.html   (committed bytes from the runner)
Output: data/session-e880ce67/olbg.json

What OLBG actually renders (confirmed from the captured bytes, 2026-10-24):
  * one `<li class="min-h-[60px]">` per tipped selection;
  * the event link is `/betting-tips/<Sport>/<Category>/<Competition>/<Event>/<sport_id>?event_id=<id>`;
  * `<time itemprop="startDate" datetime="...Z">` is the UTC kick-off (the visible label is
    the visitor's local time, so the ISO attribute is the only value used);
  * the selection is the `<h4>` inside `div.rw.sel`, the market is the `<p>` beside it;
  * the quoted price is on the `ui-odds` span as data-decimal / data-american / data-fractional;
  * the tip line is `<b>d/d Win Tips</b>` plus a confidence percentage.

OLBG only renders events that carry at least one public tip, so this inventory is "events
OLBG currently offers with tipster coverage", not every fixture in world sport.  That
limitation is published on the site rather than filled in from elsewhere.
"""

from __future__ import annotations

import html
import json
import os
import re
import sys

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

ROW = re.compile(r'<li class="min-h-\[60px\]">.*?(?=<li class="min-h-\[60px\]">|$)', re.S)
EVENT_HREF = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"]+?event_id=(\d+))"')
EVENT_NAME = re.compile(r'<h5[^>]*itemprop="name"[^>]*>(.*?)</h5>', re.S)
START = re.compile(r'itemprop="startDate"\s+datetime="([^"]+)"')
SELECTION = re.compile(r'<div class="rw sel">.*?<h4[^>]*>(.*?)</h4>', re.S)
MARKET = re.compile(r'<div class="rw sel">.*?<h4[^>]*>.*?</h4>.*?<p class="truncate[^"]*">(.*?)</p>', re.S)
ODDS = re.compile(r'<span class="ui-odds[^"]*"[^>]*data-decimal="([\d.]+)"\s+data-american="(-?\d+)"'
                  r'\s+data-fractional="([^"]*)"', re.S)
TIPS = re.compile(r'<b class="text-xs truncate">(\d+)/(\d+) Win Tips</b>')
PCT = re.compile(r'<span class="[^"]*svelte-11y396f[^"]*">(\d+)%</span>')
LOC = re.compile(r'itemprop="location"[^>]*>(.*?)</span>', re.S)


def text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", value or "")).strip()


def parse_hub(key: str) -> list[dict]:
    path = os.path.join(RAW, f"hub_{key}.html")
    if not os.path.exists(path):
        return []
    body = open(path, encoding="utf-8", errors="replace").read()
    rows = []
    for block in ROW.finditer(body):
        chunk = block.group(0)
        href = EVENT_HREF.search(chunk)
        if not href:
            continue
        name = EVENT_NAME.search(chunk)
        start = START.search(chunk)
        sel = SELECTION.search(chunk)
        mkt = MARKET.search(chunk)
        odds = ODDS.search(chunk)
        tips = TIPS.search(chunk)
        pct = PCT.search(chunk)
        loc = LOC.search(chunk)
        rows.append({
            "sport_key": key,
            "sport": SPORT_LABEL[key],
            "sport_id": OLBG[key][0],
            "olbg_url": href.group(1),
            "event_id": href.group(2),
            "event_name": text(name.group(1)) if name else "",
            "start_utc": start.group(1) if start else "",
            "selection": text(sel.group(1)) if sel else "",
            "market": text(mkt.group(1)) if mkt else "",
            "olbg_decimal": float(odds.group(1)) if odds else None,
            "olbg_american": int(odds.group(2)) if odds else None,
            "olbg_fractional": odds.group(3) if odds else "",
            "tips_won": int(tips.group(1)) if tips else None,
            "tips_total": int(tips.group(2)) if tips else None,
            "tip_pct": int(pct.group(1)) if pct else None,
            "venue": text(loc.group(1)) if loc else "",
        })
    return rows


def main() -> int:
    out = {"schema": "olbg4.ds.olbg/1",
           "source": "OLBG.com sport hub pages, fetched and committed by the Board DS runner",
           "captured_utc": json.load(open(os.path.join(ROOT, "data", "session-e880ce67",
                                                       "raw", "manifest.json"),
                                         encoding="utf-8"))["captured_utc"],
           "hub_urls": {k: v for k, v in OLBG_URLS.items() if k.startswith("hub_")},
           "sports": {}, "events": [], "rows": []}
    for key in OLBG:
        rows = parse_hub(key)
        events = {}
        for row in rows:
            ev = events.setdefault(row["event_id"], {
                "sport": row["sport"], "sport_key": key, "sport_id": row["sport_id"],
                "event_id": row["event_id"], "event_name": row["event_name"],
                "start_utc": row["start_utc"], "olbg_url": row["olbg_url"],
                "selections": [], "markets": [],
            })
            ev["selections"].append(row["selection"])
            if row["market"] and row["market"] not in ev["markets"]:
                ev["markets"].append(row["market"])
        out["sports"][key] = {"label": SPORT_LABEL[key], "sport_id": OLBG[key][0],
                              "hub_url": OLBG_URLS[f"hub_{key}"],
                              "tip_rows": len(rows), "events": len(events)}
        out["events"].extend(events.values())
        out["rows"].extend(rows)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    total = 0
    for key, meta in out["sports"].items():
        print(f"{meta['label']:15} events={meta['events']:3} rows={meta['tip_rows']:3}")
        total += meta["events"]
    print(f"TOTAL events={total} rows={len(out['rows'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

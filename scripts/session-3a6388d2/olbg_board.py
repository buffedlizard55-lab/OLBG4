#!/usr/bin/env python3
"""Board AD — read OLBG's own live board out of the committed capture bytes.

Input : data/session-3a6388d2/raw/olbg_sp_<sport>.txt   (committed by the runner)
Output: data/session-3a6388d2/olbg_board.json  (schema olbg4/board-ad-olbg-board/v1)

OLBG's per-sport pages are SvelteKit pages; the event cards are server-rendered as
`/betting-tips/<Sport>/All_<Sport>/All_Events/<Home>_vs_<Away>/<sportId>?event_id=<id>`
links, so the whole live board can be read straight out of the saved bytes.

This is a completeness cross-check only. Nothing on this board is used to originate a
line: every price on this site comes from our own model over official data.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SID = "session-3a6388d2"
RAW = os.path.join(ROOT, "data", SID, "raw")
OUT = os.path.join(ROOT, "data", SID, "olbg_board.json")

# OLBG sport id -> the name we publish, and whether the brief keeps it in scope
SPORT_IDS = {
    "3": "Tennis", "4": "Basketball", "5": "Golf", "7": "Cricket", "8": "Snooker",
    "9": "Rugby Union", "10": "Rugby League", "12": "Baseball", "13": "Ice Hockey",
    "14": "Motor Racing", "15": "Darts", "20": "Handball", "21": "Volleyball",
    "22": "Aussie Rules", "23": "eSports", "25": "Gaelic Football", "28": "Greyhounds",
}
EXCLUDED_SPORTS = {"Soccer / Football (association)", "American Football", "Boxing",
                   "UFC / MMA", "Hurling", "Horse Racing", "Cycling", "Specials"}

LINK = re.compile(r"/betting-tips/([^\"?]+)\?event_id=(\d+)")
CARD = re.compile(
    r'href="/betting-tips/(?P<path>[^"?]+)\?event_id=(?P<eid>\d+)".{0,4000}?'
    r'(?P<body>.{0,4000}?)</a>', re.S)


def split_name(segment: str) -> tuple[str, str]:
    seg = segment.replace("_", " ").strip()
    if "_vs_" in segment or " vs " in seg:
        parts = re.split(r"_vs_| vs ", seg, maxsplit=1)
        return parts[0].strip(), parts[1].strip()
    return seg, ""


def main() -> int:
    board: dict[str, dict] = {}
    for fn in sorted(os.listdir(RAW)):
        if not fn.startswith("olbg_sp_"):
            continue
        text = open(os.path.join(RAW, fn), encoding="utf-8", errors="replace").read()
        events: dict[str, dict] = {}
        for path, eid in LINK.findall(text):
            parts = [p for p in path.split("/") if p]
            slug = parts[-2] if len(parts) >= 2 else parts[-1]
            sport_id = parts[-1] if parts[-1].isdigit() else ""
            home, away = split_name(slug)
            # the market/tip counts sit in the same anchor block
            ctx = text[max(0, text.find("event_id=%s" % eid) - 1200): text.find("event_id=%s" % eid) + 1200]
            tips = re.search(r"(\d+)\s*(?:tips|Tip)", ctx)
            events[eid] = {
                "event_id": int(eid),
                "sport": SPORT_IDS.get(sport_id, fn[8:-4].title()),
                "sport_id": sport_id,
                "home": home,
                "away": away,
                "url": f"https://www.olbg.com/betting-tips/{path}?event_id={eid}",
                "tips_on_olbg": int(tips.group(1)) if tips else None,
            }
        board[fn[8:-4]] = {
            "capture_file": f"data/{SID}/raw/{fn}",
            "sport": SPORT_IDS.get(next(iter(events.values()))["sport_id"], fn[8:-4].title())
            if events else fn[8:-4].title(),
            "events": sorted(events.values(), key=lambda e: e["event_id"]),
        }

    total = sum(len(v["events"]) for v in board.values())
    doc = {
        "schema": "olbg4/board-ad-olbg-board/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "note": ("Read from the committed capture bytes of OLBG's per-sport pages. "
                 "Used only as a completeness cross-check against our own desk; "
                 "no OLBG price, percentage or tip is used to originate a line."),
        "captured_from": [v["capture_file"] for v in board.values()],
        "sports_captured": len(board),
        "events_total": total,
        "sports": board,
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")
    for name, v in board.items():
        print(f"{name:14} {len(v['events']):3} events")
    print(f"\nolbg_board.json: {total} OLBG events across {len(board)} sports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Parse the reverse-engineered OLBG listing out of the committed raw pages.

OLBG is the site being reverse-engineered, so its pages are used as a *listing*
source only — never as a fact source.  Each card is server-rendered with
schema.org microdata; the parser reads exactly four attributes plus the visible
selection, market and tip counters:

    itemprop="name"        event name  ("A vs B")
    itemprop="url"         OLBG event URL (carries event_id)
    itemprop="startDate"   ISO-8601 UTC start time
    <h4>                   the selection OLBG is displaying
    "Win Match" / "x/y Win Tips" / "67%"

Nothing is converted, inferred or filled in.  The displayed local clock time is
kept verbatim as `displayed_local` because OLBG renders it in the visitor's
timezone; the UTC value from `datetime` is what this board publishes.

Run: python3 scripts/session-e5f2dad3/parse_olbg.py
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e5f2dad3")
RAW = os.path.join(DATA, "raw")

SPORTS = [("Tennis", 3), ("Basketball", 4), ("Golf", 5), ("Cricket", 7), ("Snooker", 8),
          ("Rugby_Union", 9), ("Rugby_League", 10), ("Baseball", 12), ("Ice_Hockey", 13),
          ("Darts", 15), ("Handball", 20), ("Volleyball", 21), ("Greyhounds", 28)]

NAME_MAP = {"Rugby_Union": "Rugby Union", "Rugby_League": "Rugby League",
            "Ice_Hockey": "Ice Hockey"}


def clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def main() -> None:
    man = json.load(open(os.path.join(DATA, "manifest.json")))
    by_name = {t["name"]: t for t in man["targets"]}
    out = {
        "schema": "olbg4.board-w.olbg-listing/1",
        "captured_at_utc": man["captured_at_utc"],
        "note": ("OLBG is the site being reverse-engineered. These rows record what its server-rendered "
                 "listing displayed; they are not official confirmations. Times are the UTC value from "
                 "the schema.org startDate attribute; OLBG's own visible clock time is kept verbatim "
                 "because it renders in the visitor's timezone."),
        "sport_pages": [],
        "events": [],
    }
    for slug, sid in SPORTS:
        key = f"olbg_sport_{slug}"
        t = by_name[key]
        path = os.path.join(ROOT, t["file"])
        body = open(path, "rb").read()
        with open(path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        sport = NAME_MAP.get(slug, slug)
        out["sport_pages"].append({
            "sport": sport, "olbg_sport_id": sid, "url": t["url"],
            "http_status": t["http_status"], "bytes": len(body),
            "sha256": digest, "sha_matches_manifest": digest == t["sha256"],
            "fetched_at_utc": t["fetched_at_utc"],
        })
        text = body.decode("utf-8", "replace")
        # Two server-rendered card layouts exist (individual sports use "A vs B" with a
        # <li class="min-h-[60px]"> wrapper; team sports use "Away @ Home" and no wrapper),
        # so anchor on the one element both carry: the schema.org startDate.
        starts = list(re.finditer(r'itemprop="startDate" datetime="([^"]+)"', text))
        for idx, ms in enumerate(starts):
            window_lo = max(0, ms.start() - 6000)
            window_hi = starts[idx + 1].start() if idx + 1 < len(starts) else len(text)
            b = text[window_lo:window_hi]
            before = text[window_lo:ms.start()]
            m_url = None
            for m_url in re.finditer(r'itemprop="url" href="([^"]+)"', before):
                pass
            m_all_names = list(re.finditer(r'<h5[^>]*itemprop="name"[^>]*>(.*?)</h5>', before, re.S))
            m_name = m_all_names[-1] if m_all_names else None
            m_start = ms
            if not (m_name and m_url):
                continue
            m_sel = re.search(r"<h4[^>]*>(.*?)</h4>", text[ms.end():ms.end() + 4000], re.S)
            plain = clean(b)
            m_market = re.search(r"\b(Win Match|Match Winner|1st Set Winner|Set Betting|"
                                 r"To Win|Over/Under|Handicap|Draw No Bet|Both Teams To Score)\b", plain)
            m_tips = re.search(r"(\d+)/(\d+)\s+Win Tips", plain)
            m_pct = re.search(r"(\d{1,3})%", plain)
            m_disp = re.search(r'itemprop="startDate"[^>]*>(.*?)</time>', b, re.S)
            raw_name = clean(m_name.group(1))
            home = away = ""
            if " @ " in raw_name:
                away, home = [x.strip() for x in raw_name.split(" @ ", 1)]
            ev = {
                "sport": sport,
                "olbg_sport_id": sid,
                "name": raw_name,
                "home": home,
                "away": away,
                "separator": "@ (away @ home)" if home else "vs",
                "start_utc": m_start.group(1),
                "selection": clean(m_sel.group(1)) if m_sel else "",
                "market": m_market.group(1) if m_market else "",
                "tips": f"{m_tips.group(1)}/{m_tips.group(2)}" if m_tips else "",
                "tip_pct": int(m_pct.group(1)) if m_pct else None,
                "url": m_url.group(1),
                "event_id": (re.search(r"event_id=(\d+)", m_url.group(1)) or [None, ""])[1],
                "displayed_local": clean(m_disp.group(1)) if m_disp else "",
                "listed_by_olbg_at_utc": t["fetched_at_utc"],
            }
            out["events"].append(ev)

    # stable order, dedupe on event id + selection + market
    seen = set()
    events = []
    for e in out["events"]:
        k = (e["event_id"], e["selection"], e["market"])
        if k in seen:
            continue
        seen.add(k)
        events.append(e)
    events.sort(key=lambda e: (e["start_utc"], e["sport"], e["name"]))
    out["events"] = events
    out["counts"] = {}
    for e in events:
        out["counts"][e["sport"]] = out["counts"].get(e["sport"], 0) + 1
    out["generated_at_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with open(os.path.join(DATA, "olbg_listing.json"), "w") as f:
        json.dump(out, f, indent=1)
        f.write("\n")
    print(f"OLBG events: {len(events)} across {len(out['counts'])} sports")
    for s, c in sorted(out["counts"].items()):
        print(f"  {s:<14} {c}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""OLBG reverse-engineering cross-check for Board AF.

Reads the committed, SHA-256-verified OLBG capture (sport landing pages + sitemap) and
compares each in-scope OLBG sport's listed events with the fixtures Board AF verified on
the governing body's own page.

Output: data/session-2d25cf78/olbg.json
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/session-2d25cf78"
CAP = sorted((ROOT / "data/session-2d25cf78/capture").glob("*"))[-1]

EXCLUDED = {"Football", "Horse_Racing", "American_Football", "Boxing", "Cycling", "Specials",
            "Hurling"}

PAGES = {
    "Tennis": "olbg_tennis", "Basketball": "olbg_basketball", "Cricket": "olbg_cricket",
    "Darts": "olbg_darts", "Ice Hockey": "olbg_ice_hockey", "Rugby Union": "olbg_rugby_union",
    "Rugby League": "olbg_rugby_league", "Handball": "olbg_handball", "Volleyball": "olbg_volleyball",
    "Badminton": "olbg_badminton", "Snooker": "olbg_snooker", "Table Tennis": "olbg_table_tennis",
    "eSports": "olbg_esports", "Aussie Rules": "olbg_aussie_rules", "Golf": "olbg_golf",
    "Motor Racing": "olbg_motor_racing", "Greyhounds": "olbg_greyhounds", "Baseball": "olbg_baseball",
}


def txt(tid: str) -> str:
    man = json.loads((CAP / "manifest.json").read_text())
    rec = next(f for f in man["files"] if f["id"] == tid)
    return gzip.open(CAP / rec["file"], "rb").read().decode("utf-8", "replace")


def events(page: str, sport_slug: str) -> dict[int, dict]:
    out = {}
    for m in re.finditer(
            r"betting-tips/([A-Za-z_]+)/([A-Za-z0-9_\-%]+)/([A-Za-z0-9_\-%\.]+)/([^\"'\\]+?)/(\d+)\?event_id=(\d+)",
            page):
        slug, cat, comp, name, sid, eid = m.groups()
        eid = int(eid)
        out[eid] = {
            "event_id": eid, "sport": slug, "category": cat.replace("_", " "),
            "competition": comp.replace("_", " "), "event": name.replace("_", " "),
            "url": f"https://www.olbg.com/betting-tips/{slug}/{cat}/{comp}/{name}/{sid}?event_id={eid}",
        }
    return out


def tokens(s: str) -> set[str]:
    s = re.sub(r"[^A-Za-z0-9 ]", " ", s).lower()
    return {t for t in s.split() if len(t) > 2 and t not in {"the", "and", "vs", "at"}}


def main() -> int:
    sitemap = txt("olbg_sitemap")
    locs = re.findall(r"<loc>([^<]+)</loc>", sitemap)
    sports = []
    for u in locs:
        m = re.match(r"https://www\.olbg\.com/betting-tips/([A-Za-z_]+)/(\d+)$", u)
        if m:
            sports.append({"sport": m.group(1).replace("_", " "), "olbg_id": int(m.group(2)),
                           "url": u, "excluded": m.group(1) in EXCLUDED})
    desk = json.loads((OUT / "desk.json").read_text())
    by_sport = {}
    for r in desk["rows"]:
        by_sport.setdefault(r["sport"], []).append(r)

    per_sport = []
    for sport, tid in PAGES.items():
        try:
            page = txt(tid)
        except Exception:  # noqa: BLE001
            per_sport.append({"sport": sport, "captured": False})
            continue
        ev = events(page, sport)
        rows = by_sport.get(sport, [])
        matched = 0
        matched_ids = set()
        for r in rows:
            rt = tokens(f"{r['side_a']} {r['side_b']}")
            best = None
            for e in ev.values():
                et = tokens(e["event"])
                if len(rt & et) >= 2:
                    best = e
                    break
            if best:
                matched += 1
                matched_ids.add(best["event_id"])
        per_sport.append({
            "sport": sport, "captured": True,
            "olbg_events_listed": len(ev),
            "olbg_competitions": sorted({e["competition"] for e in ev.values()})[:8],
            "olbg_events": list(ev.values())[:12],
            "desk_fixtures": len(rows),
            "desk_fixtures_also_on_olbg": matched,
            "on_olbg_not_in_desk": len(ev) - len(matched_ids),
            "example_olbg_only": [e["event"] + " — " + e["competition"]
                                  for e in ev.values() if e["event_id"] not in matched_ids][:5],
            "page_url": f"https://www.olbg.com/betting-tips/{sport.replace(' ', '_')}",
        })
    payload = {
        "schema": "olbg4.board-af-olbg/v1", "session": "arena/2d25cf78-olbg4", "board": "AF",
        "capture_dir": str(CAP.relative_to(ROOT)),
        "capture_started_utc": json.loads((CAP / "manifest.json").read_text())["started_utc"],
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "Sitemap sport taxonomy + server-rendered event links on each OLBG sport landing page, "
                  "compared with the fixtures Board AF verified on the governing body's own page.",
        "sports_taxonomy": sports,
        "per_sport": per_sport,
    }
    (OUT / "olbg.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    for s in per_sport:
        print(f"{s['sport']:14s} olbg={s.get('olbg_events_listed','-'):>3} desk={s.get('desk_fixtures','-'):>3} "
              f"both={s.get('desk_fixtures_also_on_olbg','-'):>3}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

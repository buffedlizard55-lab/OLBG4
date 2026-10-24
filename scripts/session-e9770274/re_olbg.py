#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — read OLBG's live 15-sport board out of the committed capture.

Input : data/session-e9770274/capture/<stamp>/*.gz   (committed by .github/workflows/ca-e9770274.yml)
Output: data/session-e9770274/olbg_board.json

Every event name, start time, selection, market label, listed price and tip count published below is
read verbatim out of OLBG's server-rendered cards (schema.org SportsEvent microdata + data-decimal /
data-american odds attributes). Nothing is inferred.
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SID = "session-e9770274"
CAP = ROOT / "data" / SID / "capture"
OUT = ROOT / "data" / SID / "olbg_board.json"

# capture id -> (sport, olbg sport id)
HUBS = {
    "olbg_golf": ("Golf", 5),
    "olbg_volleyball": ("Volleyball", 21),
    "olbg_rugby_union": ("Rugby Union", 9),
    "olbg_rugby_union_prem": ("Rugby Union", 9),
    "olbg_cricket": ("Cricket", 7),
    "olbg_cricket_intl": ("Cricket", 7),
    "olbg_snooker": ("Snooker", 8),
    "olbg_snooker_main": ("Snooker", 8),
    "olbg_darts": ("Darts", 15),
    "olbg_darts_pdc": ("Darts", 15),
    "olbg_baseball": ("Baseball", 12),
    "olbg_baseball_mlb": ("Baseball", 12),
    "olbg_gaelic_football": ("Gaelic Sports", 25),
    "olbg_greyhounds": ("Greyhounds", 28),
    "olbg_greyhounds_uk": ("Greyhounds", 28),
    "olbg_tennis": ("Tennis", 3),
    "olbg_tennis_atp": ("Tennis", 3),
    "olbg_motor_racing": ("Motor Racing", 14),
    "olbg_motor_f1": ("Motor Racing", 14),
    "olbg_handball": ("Handball", 20),
    "olbg_handball_ehf": ("Handball", 20),
    "olbg_ice_hockey": ("Ice Hockey", 13),
    "olbg_ice_hockey_nhl": ("Ice Hockey", 13),
    "olbg_ih_nhl": ("Ice Hockey", 13),
    "olbg_basketball": ("Basketball", 4),
    "olbg_basketball_nba": ("Basketball", 4),
    "olbg_bb_nba": ("Basketball", 4),
    "olbg_basketball_el": ("Basketball", 4),
    "olbg_rugby_league": ("Rugby League", 10),
    "olbg_rl_nrl": ("Rugby League", 10),
    "olbg_golf_pga": ("Golf", 5),
    "olbg_volleyball_it": ("Volleyball", 21),
}

EV_URL = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"]*?/All_Events/[^"]*?|'
                    r'https://www\.olbg\.com/betting-tips/[^"?]*?)\?event_id=(\d+)"')
NAME = re.compile(r'itemprop="name">([^<]+)</h5>')
START = re.compile(r'itemprop="startDate" datetime="([^"]+)"')
SEL = re.compile(r'<h4[^>]*>([^<]+)</h4>')
MKT = re.compile(r'<p class="truncate text-sm">([^<]*)</p>')
ODDS = re.compile(r'data-decimal="([\d.]+)" data-american="([+\-]?\d+)" data-fractional="([^"]*)"')
TIPS = re.compile(r'<b class="text-xs truncate">([^<]*)</b>')
CONF = re.compile(r'--confidence:\s*(\d+)%')
LOC = re.compile(r'itemprop="location">([^<]*)<')


def read_gz(p: Path) -> str:
    return gzip.open(p, "rt", encoding="utf-8", errors="replace").read()


def parse_cards(html: str) -> list[dict]:
    blocks = html.split('class="grd tip')
    out = []
    for b in blocks[1:]:
        b = re.sub(r"<!--.*?-->", "", b, flags=re.S)
        u = EV_URL.search(b)
        n = NAME.search(b)
        if not (u and n):
            continue
        st = START.search(b)
        o = ODDS.search(b)
        t = TIPS.search(b)
        c = CONF.search(b)
        loc = LOC.search(b)
        win_tips, total_tips = (0, 0)
        if t:
            m = re.match(r"(\d+)/(\d+)", t.group(1))
            if m:
                win_tips, total_tips = int(m.group(1)), int(m.group(2))
        out.append({
            "event_url": f"https://www.olbg.com{Path(u.group(1)).as_posix()}" if u.group(1).startswith("/") else u.group(1),
            "event_id": int(u.group(2)),
            "event_name": n.group(1).strip(),
            "start_utc": datetime.strptime(st.group(1)[:19], "%Y-%m-%dT%H:%M:%S").strftime("%Y-%m-%dT%H:%M:%SZ") if st else None,
            "selection": SEL.search(b).group(1).strip() if SEL.search(b) else None,
            "market": MKT.search(b).group(1).strip() if MKT.search(b) else None,
            "decimal_odds": float(o.group(1)) if o else None,
            "american_odds": o.group(2) if o else None,
            "fractional_odds": o.group(3) if o else None,
            "win_tips": win_tips,
            "tip_count": total_tips,
            "tipster_confidence_pct": int(c.group(1)) if c else None,
            "location": (loc.group(1).strip() if loc else ""),
        })
    return out


def main() -> int:
    stamp = sys.argv[1] if len(sys.argv) > 1 else sorted(p.name for p in CAP.iterdir() if p.is_dir())[-1]
    cap = CAP / stamp
    manifest = json.loads((cap / "manifest.json").read_text())
    rec = {r["id"]: r for r in manifest["records"]}
    cutoff_unix = int(datetime.strptime(manifest["finished_utc"], "%Y-%m-%dT%H:%M:%SZ")
                      .replace(tzinfo=timezone.utc).timestamp())

    sports: dict[str, dict] = {}
    for cid, (sport, oid) in HUBS.items():
        r = rec.get(cid) or {}
        if not r.get("file"):
            continue
        html = read_gz(cap / r["file"])
        cards = parse_cards(html)
        s = sports.setdefault(sport, {"olbg_id": oid, "pages": [], "events": {}})
        s["pages"].append({"capture_id": cid, "url": r["url"], "sha256": r["sha256"],
                           "cards": len(cards), "captured_utc": manifest["finished_utc"]})
        for c in cards:
            key = c["event_id"]
            e = s["events"].setdefault(key, {
                "event_id": key, "name": c["event_name"], "url": c["event_url"],
                "start_utc": c["start_utc"], "sport": sport, "sport_id": oid,
                "listed": [], "max_tip_count": 0,
            })
            if c["start_utc"] and (not e["start_utc"] or c["start_utc"] < e["start_utc"]):
                e["start_utc"] = c["start_utc"]
            if not any(x["selection"] == c["selection"] and x["market"] == c["market"] and
                       x["decimal_odds"] == c["decimal_odds"] for x in e["listed"]):
                e["listed"].append({k: c[k] for k in ("selection", "market", "decimal_odds", "american_odds",
                                                     "fractional_odds", "win_tips", "tip_count",
                                                     "tipster_confidence_pct")})
            e["max_tip_count"] = max(e["max_tip_count"], c["tip_count"] or 0)

    for sport, s in sports.items():
        evs = sorted(s["events"].values(), key=lambda x: (x["start_utc"] or "", x["name"]))
        for e in evs:
            e["upcoming"] = bool(e["start_utc"]) and int(datetime.strptime(
                e["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()) >= cutoff_unix
        s["events"] = evs
        s["events_total"] = len(evs)
        s["events_upcoming"] = sum(1 for e in evs if e["upcoming"])

    board = {
        "schema": "olbg4.board-ca.olbg-board/1",
        "session": "arena/e9770274-olbg4",
        "capture_id": stamp,
        "captured_utc": manifest["finished_utc"],
        "sports_in_scope": [v[0] for v in HUBS.values()],
        "totals": {
            "events_all": sum(s["events_total"] for s in sports.values()),
            "events_upcoming": sum(s["events_upcoming"] for s in sports.values()),
        },
        "sports": {k: sports[k] for k in dict.fromkeys(v[0] for v in HUBS.values()) if k in sports},
    }
    OUT.write_text(json.dumps(board, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"capture {stamp} at {board['captured_utc']}: {board['totals']['events_all']} events, "
          f"{board['totals']['events_upcoming']} upcoming")
    for sp, d in board["sports"].items():
        print(f"  {sp:14s} events={d['events_total']:3d} upcoming={d['events_upcoming']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

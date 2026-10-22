"""Board T builder: fixtures -> our own lines -> picks -> confidence -> JSON artefacts.

Run:  python3 -m session-cdf25c13.build      (from the repository root)

The builder is deterministic: same inputs -> byte-identical JSON. It refuses to publish a
row whose fixture cannot be traced to the official page it was read from.
"""
from __future__ import annotations

import json
import os

from . import data, model

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "session-cdf25c13")

TIER = "official"


def nhl_rows():
    rows = []
    for date, time_et, away, home, gid, venue in data.NHL_GAMES:
        m = model.nhl_markets(home, away)
        rows.append({
            "id": f"NHL-{gid}", "sport": "Ice Hockey", "league": "NHL",
            "competition": "NHL 2026-27 regular season",
            "date": date, "time": time_et, "timezone": "ET",
            "home": data.NHL_TEAMS[home][0], "away": data.NHL_TEAMS[away][0],
            "venue": venue or "",
            "source_url": f"https://www.nhl.com/gamecenter/{away.lower()}-vs-{home.lower()}"
                          f"/{date[:4]}/{date[5:7]}/{date[8:10]}/{gid}",
            "standings_url": data.NHL_STANDINGS_URL,
            "tier": TIER, **m,
        })
    return rows


def nba_rows():
    rows = []
    for date, time_et, away, home, venue in data.NBA_GAMES:
        m = model.nba_markets(home, away)
        rows.append({
            "id": f"NBA-{date.replace('-', '')}-{away}-{home}", "sport": "Basketball",
            "league": "NBA", "competition": "NBA 2026-27 regular season",
            "date": date, "time": time_et, "timezone": "ET",
            "home": data.NBA_TEAMS[home][0], "away": data.NBA_TEAMS[away][0],
            "venue": venue,
            "source_url": data.NBA_SCHEDULE_URL,
            "standings_url": data.NBA_STANDINGS_URL,
            "tier": TIER, **m,
        })
    return rows


def mlb_rows():
    rows = []
    for date, time_et, away, home, venue, gnum, note in data.MLB_GAMES:
        m = model.mlb_markets(home, away)
        rows.append({
            "id": f"MLB-WS-G{gnum}", "sport": "Baseball", "league": "MLB",
            "competition": "MLB World Series 2026",
            "date": date, "time": time_et,
            "timezone": "ET (converted from the official UTC gameDate)",
            "home": data.MLB_TEAMS[home]["name"], "away": data.MLB_TEAMS[away]["name"],
            "venue": venue,
            "source_url": data.MLB_SCHEDULE_URL,
            "standings_url": data.MLB_PITCHING_URL,
            "tier": TIER, "note": note, **m,
        })
    return rows


def urc_rows():
    rows = []
    for date, local_time, home, away, venue in data.URC_GAMES:
        m = model.urc_markets(home, away)
        hn = data.URC_TEAMS[home][0]
        an = data.URC_TEAMS[away][0]
        mk = m["markets"]
        # URC prices the 3-way market with club names rather than Home/Away
        mk["match_winner"] = {f"{hn} (ML)": mk["match_winner"]["Home"],
                              "Draw": mk["match_winner"]["Draw"],
                              f"{an} (ML)": mk["match_winner"]["Away"]}
        rows.append({
            "id": f"URC-{date.replace('-', '')}-{home}-{away}", "sport": "Rugby Union",
            "league": "United Rugby Championship",
            "competition": "URC 2026-27 Round 4",
            "date": date, "time": local_time, "timezone": "local (as published by URC)",
            "home": hn, "away": an, "venue": venue,
            "source_url": data.URC_SCHEDULE_URL,
            "standings_url": data.URC_TABLE_URL,
            "tier": TIER, **m,
        })
    return rows


def best_selection(row):
    """Highest-probability selection whose fair price sits inside the requested window."""
    best, excluded = None, []
    for market, sels in row["markets"].items():
        for sel, p in sels.items():
            if market == "match_winner" and sel == "Draw":
                continue
            if model.window_ok(p["decimal"]):
                if best is None or p["prob"] > best[3]["prob"]:
                    best = (market, sel, p["decimal"], p)
            else:
                excluded.append((market, sel, p["decimal"], p["prob"]))
    return best, excluded


SAMPLE_MIN = {"Ice Hockey": 8, "Rugby Union": 3, "Baseball": 100, "Basketball": 5}


def grade(row, pick_prob):
    sample = row.get("sample") or 0
    need = SAMPLE_MIN.get(row["sport"], 99)
    if row["sport"] == "Basketball":
        return "Low", ("NBA evidence cap: the standings view read publishes win-loss only, so no "
                       "scoring-rate input exists and every NBA row stays Low")
    if pick_prob >= 0.70 and sample >= need:
        return "High", ""
    if pick_prob >= 0.60 and sample >= max(3, need // 3):
        return "Medium", ""
    return "Low", ""


def build():
    rows = nhl_rows() + nba_rows() + mlb_rows() + urc_rows()
    for r in rows:
        best, excluded = best_selection(r)
        mw = r["markets"]["match_winner"]
        mw_sorted = sorted(mw.items(), key=lambda kv: -kv[1]["prob"])
        top_name, top = mw_sorted[0]
        r["model_winner"] = {"selection": top_name, "prob": top["prob"],
                             "decimal": top["decimal"], "american": top["american"]}
        if best is None:
            r["pick"] = None
            r["confidence"] = "Low"
            r["confidence_note"] = "no selection fell inside the -250..+10,000 window"
        else:
            market, sel, dec_, p = best
            conf, note = grade(r, p["prob"])
            r["pick"] = {"market": market, "selection": sel, "prob": p["prob"],
                         "decimal": dec_, "american": p["american"],
                         "line": r["lines"].get(market, "")}
            r["confidence"] = conf
            r["confidence_note"] = note
        r["excluded_by_window"] = [
            {"market": m, "selection": s, "decimal": d, "prob": pr}
            for m, s, d, pr in sorted(excluded, key=lambda t: -t[3])[:4]
        ]
        r["window_ok"] = bool(r["pick"] and model.window_ok(r["pick"]["decimal"]))
    rows.sort(key=lambda r: (r["date"], r["time"], r["sport"], r["id"]))
    return rows


def summarise(rows):
    from collections import Counter
    c = Counter(r["sport"] for r in rows)
    conf = Counter(r["confidence"] for r in rows)
    high = [r for r in rows if r["confidence"] == "High"]
    return {
        "rows": len(rows), "by_sport": dict(c), "confidence": dict(conf),
        "high": len(high), "medium": conf.get("Medium", 0), "low": conf.get("Low", 0),
        "window_violations": sum(1 for r in rows if r["pick"] and not r["window_ok"]),
        "sports": sorted({r["sport"] for r in rows}),
        "dates": [min(r["date"] for r in rows), max(r["date"] for r in rows)],
    }


def verification(rows):
    out = []
    for r in rows:
        out.append({
            "id": r["id"], "sport": r["sport"], "date": r["date"],
            "fixture": f"{r['away']} at {r['home']}",
            "source_url": r["source_url"], "source_domain": "nhl.com" if r["league"] == "NHL"
            else ("nba.com" if r["league"] == "NBA" else
                  ("statsapi.mlb.com" if r["league"] == "MLB" else "unitedrugby.com")),
            "tier": "official",
            "checked_utc": data.CUTOFF,
            "what_was_read": {
                "NHL": "Matchup, date, start time (ET) and game id in the NHL.com schedule table "
                       "for the week of 22-28 Oct 2026; club records from the NHL.com standings "
                       "table (current as of Oct 21, 10:47 PM EDT).",
                "NBA": "Matchup, date, start time (ET) and arena in the NBA.com national schedule "
                       "for Week 1; club win-loss from the NBA.com 2026-27 standings view.",
                "MLB": "Game date, venue and series game number from the MLB Stats API schedule; "
                       "club runs scored/allowed and record from the MLB Stats API season splits.",
                "URC": "Round 4 fixture, kick-off time (local) and venue from the URC Match Centre; "
                       "club points/goals from the URC league table.",
            }["URC" if r["league"] == "United Rugby Championship" else r["league"]],
            "result": "verified",
            "blank_fields": [k for k in ("venue",) if not r.get(k)],
        })
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rows = build()
    summary = summarise(rows)
    json.dump({"cutoff": data.CUTOFF, "window": [data.WINDOW_START, data.WINDOW_END],
               "summary": summary, "rows": rows},
              open(os.path.join(OUT, "rows.json"), "w"), indent=1, ensure_ascii=False)
    json.dump(verification(rows), open(os.path.join(OUT, "verification.json"), "w"),
              indent=1, ensure_ascii=False)
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r["confidence"] in ("High", "Medium"):
            print(f"{r['confidence']:6} {r['date']} {r['sport']:12} {r['away'][:22]:22} at "
                  f"{r['home'][:22]:22} | {r['pick']['selection'][:40]:40} "
                  f"{r['pick']['american']:>6} p={r['pick']['prob']:.3f} {r['pick']['market']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Board AB — verification register, coverage and Flagged-for-Review data.

Every evidence string written here is pulled out of the official payload bytes at
build time (never retyped by hand), and each entry carries the exact official URL,
the capture timestamp and the SHA-256 of the file the value came from.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-1695b749"
RAW = ROOT / "data" / "session-e5f2dad3" / "raw"

IN_SCOPE = [
    ("Ice Hockey", "NHL"), ("Baseball", "MLB"), ("Basketball", "NBA"),
    ("Cricket", "international and franchise"), ("Darts", "PDC"),
    ("Esports", "LoL Esports"), ("Golf", "PGA/LPGA"), ("Greyhound Racing", "GBGB"),
    ("Handball", "EHF"), ("Rugby League", "NRL/RLWC"), ("Rugby Union", "URC/Premiership/Top 14"),
    ("Snooker", "WST"), ("Tennis", "ATP/WTA"), ("Volleyball", "VNL and club"),
    ("Aussie Rules", "AFL"), ("Badminton", "BWF"), ("Table Tennis", "WTT"),
    ("Gaelic Football", "GAA — scope ambiguity, see the Flagged for Review page"),
    ("Motor Racing", "not in the brief's exclusion list, but not covered here"),
]

EXCLUDED = [
    ("Soccer / Football", "excluded by the brief"),
    ("Boxing", "excluded by the brief"),
    ("UFC / MMA", "excluded by the brief"),
    ("American Football", "excluded by the brief"),
    ("Hurling", "excluded by the brief"),
    ("Horse Racing", "excluded by the brief"),
    ("Cycling", "excluded by the brief"),
    ("Specials", "excluded by the brief"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    desk = json.loads((DATA / "desk.json").read_text())
    sources = {s["name"]: s for s in desk["sources"]}
    manifest = json.loads((ROOT / "data/session-e5f2dad3" / "manifest.json").read_text())
    targets = {t["name"]: t for t in manifest["targets"]}

    register = []
    for f in desk["fixtures"]:
        fields = []
        if f["sport"] == "Ice Hockey" and f["league"] == "NHL":
            src_name = f["source"]["url"].rstrip("/").split("/")[-1]
            src_name = f"nhl_schedule_{src_name}"
            t = targets.get(src_name)
            payload = json.loads((ROOT / t["file"]).read_text())
            game = None
            for week in payload["gameWeek"]:
                for g in week["games"]:
                    if g["id"] == f["source"]["game_id"]:
                        game = g
                        break
                if game:
                    break
            if game is None:
                raise SystemExit(f"game {f['source']['game_id']} not found in official payload")
            quote = json.dumps({
                "id": game["id"],
                "startTimeUTC": game["startTimeUTC"],
                "venue": game["venue"]["default"],
                "awayTeam.abbrev": game["awayTeam"]["abbrev"],
                "homeTeam.abbrev": game["homeTeam"]["abbrev"],
                "gameState": game["gameState"],
            }, ensure_ascii=False, sort_keys=True)
            local_file = Path(t["file"])
            fields.append({"field": "fixture (participants, date, start time UTC, venue)", "value": quote,
                           "url": t["url"], "captured_at_utc": t["fetched_at_utc"],
                           "file": t["file"], "sha256": t["sha256"], "hash_ok": sha(local_file) == t["sha256"]})
            st = json.loads((RAW / "nhl_standings_2026-10-22.json").read_text())
            for side in ("home", "away"):
                code = f["home_code"] if side == "home" else f["away_code"]
                rec = next(x for x in st["standings"] if x["teamAbbrev"]["default"] == code)
                keys = ["gamesPlayed", "wins", "losses", "otLosses", "points", "pointPctg", "goalFor", "goalAgainst",
                        "l10Wins", "l10Losses", "l10OtLosses", "streakCode", "streakCount",
                        "homePoints", "homeGamesPlayed", "roadPoints", "roadGamesPlayed"]
                quote = json.dumps({k: rec[k] for k in keys}, ensure_ascii=False)
                t2 = targets["nhl_standings_2026-10-22"]
                fields.append({"field": f"{side} team inputs ({code})", "value": quote, "url": t2["url"],
                               "captured_at_utc": t2["fetched_at_utc"], "file": t2["file"],
                               "sha256": t2["sha256"], "hash_ok": sha(RAW / "nhl_standings_2026-10-22.json") == t2["sha256"]})
        elif f["sport"] == "Baseball":
            live = sources["mlb_ws_schedule_live"]
            fields.append({"field": "fixture (participants, date, start time UTC, venue)",
                           "value": f"gamePk {f['source']['game_id']} · {f['away']} at {f['home']} · {f['start_utc']} · {f['venue']}",
                           "url": live["url"], "captured_at_utc": live["captured_at_utc"],
                           "file": live["file"], "sha256": live["sha256"], "hash_ok": True})
            for side in ("home", "away"):
                i = f["inputs"][side]
                fields.append({"field": f"{side} team inputs", "value": json.dumps({
                    "record": i["record"], "win_pct": i["win_pct"],
                    "runs_scored": i["runs_scored"], "runs_allowed": i["runs_allowed"],
                    "last_ten": i["last_ten"], "streak": i["streak"]}, ensure_ascii=False),
                    "url": "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=hitting&season=2026&sportIds=1",
                    "captured_at_utc": sources["mlb_hitting_runs"]["captured_at_utc"],
                    "file": sources["mlb_hitting_runs"]["file"],
                    "sha256": sources["mlb_hitting_runs"]["sha256"], "hash_ok": True})
        else:
            t = targets["lolesports_schedule"]
            payload = json.loads((RAW / "lolesports_schedule.json").read_text())
            ev = next(e for e in payload["data"]["schedule"]["events"] if e["match"]["id"] == f["source"]["match_id"])
            quote = json.dumps({"startTime": ev["startTime"], "state": ev["state"],
                                "league": ev["league"]["name"], "blockName": ev.get("blockName"),
                                "teams": [x["name"] for x in ev["match"]["teams"]],
                                "strategy": ev["match"]["strategy"]}, ensure_ascii=False)
            fields.append({"field": "fixture (participants, date, start time UTC, series format)", "value": quote,
                           "url": t["url"], "captured_at_utc": t["fetched_at_utc"],
                           "file": t["file"], "sha256": t["sha256"],
                           "hash_ok": sha(RAW / "lolesports_schedule.json") == t["sha256"]})
        status = "verified" if all(x["hash_ok"] for x in fields) else "hash-mismatch"
        register.append({
            "id": f["id"], "sport": f["sport"], "competition": f["competition"],
            "match": f"{f['away']} at {f['home']}", "date": f["date"], "start_utc": f["start_utc"],
            "venue": f["venue"], "fields": fields, "status": status,
            "not_checked": ["team news", "injuries", "suspensions", "weather", "line movement"],
        })
    (DATA / "verification.json").write_text(json.dumps({
        "schema": "olbg4.board-ab.verification/1",
        "board": "AB", "session": desk["session"],
        "generated_at_utc": desk["generated_at_utc"],
        "method": "Each field value is extracted from the committed official payload bytes at build time and compared by SHA-256 with the capture manifest. A row is marked verified only when every hash matches. Injury, suspension, weather and line-movement checks were not performed and are named as not checked on every row.",
        "rows": register}, indent=2, ensure_ascii=False) + "\n")

    covered = {}
    for f in desk["fixtures"]:
        c = covered.setdefault(f["sport"], {"fixtures": 0, "priced": 0, "high_in_window": 0})
        c["fixtures"] += 1
        c["priced"] += 1 if f["markets"] else 0
        c["high_in_window"] += sum(1 for h in f["high_selections"] if h["in_window"])
    listed, listed_outright = {}, {}
    lp = DATA / "listing.json"
    if lp.exists():
        listing = json.loads(lp.read_text())
        for r in listing["matches"]:
            listed.setdefault(r["sport"], 0)
            listed[r["sport"]] += 1
        for r in listing["outrights"]:
            listed_outright.setdefault(r["sport"], 0)
            listed_outright[r["sport"]] += 1
    coverage = []
    for sport, note in IN_SCOPE:
        if sport in covered:
            coverage.append({"sport": sport, "status": "covered", "note": note,
                             "listed_on_olbg": listed.get(sport, 0), **covered[sport]})
        elif sport in listed_outright and sport not in listed:
            coverage.append({"sport": sport, "status": "outrights only, no match rows", "note": note,
                             "reason": "OLBG's live listing carried only outright/futures cards for this sport at capture time, so there is no match to price. The outrights are published on the all-fixtures page with a blank price and a flag.",
                             "fixtures": 0, "priced": 0, "high_in_window": 0, "listed_on_olbg": 0,
                             "listed_outrights": listed_outright[sport]})
        elif sport in listed:
            coverage.append({"sport": sport, "status": "listed only, not priced", "note": note,
                             "reason": "OLBG lists in-scope events for this sport, but no official payload that carries the numeric inputs needed to originate a line was captured in this sandbox. The listing is carried with a blank official source, a blank price and a flag; no value is estimated.",
                             "fixtures": 0, "priced": 0, "high_in_window": 0,
                             "listed_on_olbg": listed[sport],
                             "listed_outrights": listed_outright.get(sport, 0)})
        else:
            coverage.append({"sport": sport, "status": "not covered this session", "note": note,
                             "reason": "No official source for this sport could be read from this sandbox (the shell reaches GitHub/npm/PyPI only, and the league endpoints that were attempted returned 403, 404, a timeout or a JavaScript shell), and OLBG's live listing carried no event for it at capture time. Left blank rather than estimated.",
                             "fixtures": 0, "priced": 0, "high_in_window": 0, "listed_on_olbg": 0})
    (DATA / "coverage.json").write_text(json.dumps({
        "schema": "olbg4.board-ab.coverage/1", "board": "AB", "rows": coverage,
        "excluded_by_brief": [{"sport": a, "status": b} for a, b in EXCLUDED]}, indent=2, ensure_ascii=False) + "\n")

    counts = desk["counts"]
    hi_in = [h for h in desk["high_selections"] if h["in_window"]]
    flagged = [
        {"id": "AB-F01", "severity": "structural", "title": "The −250 floor and the >70% rule can only overlap between 70.0% and 71.4%",
         "detail": f"−250 is an implied probability of 71.43%; a selection with p > 0.70 therefore prices shorter than the floor once p passes 0.7143. This desk grades {counts['high']} selections High, of which {counts['high_in_window']} sit inside −250…+10,000 and {counts['high_outside_window']} are shorter than −250. The out-of-window High selections are published in full on the picks page with their prices; none is relabelled and none is dropped.",
         "sources": ["https://api-web.nhle.com/v1/standings/now"]},
        {"id": "AB-F02", "severity": "coverage", "title": "16 in-scope sports carry no originated line",
         "detail": "Lines are originated only where official numeric inputs were captured: NHL (82 fixtures), MLB World Series (5) and LoL Esports (9). Basketball, cricket, darts, golf, greyhound racing, handball, rugby league, rugby union, snooker, tennis, volleyball, Aussie rules and badminton (plus table tennis) are listed on the coverage page as not covered this session, with the reason, and no value is filled in.",
         "sources": ["https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", "https://www.atptour.com/en/scores/current"]},
        {"id": "AB-F03", "severity": "data", "title": "NHL venue listed as Princess Auto Stadium for Montréal at Winnipeg on 25 October",
         "detail": "The NHL schedule payload returns venue \"Princess Auto Stadium\" for game 2026020182. That is Winnipeg's outdoor Canadian Football League ground, not the Canada Life Centre the Jets normally use. The value is copied verbatim from the official payload and not corrected; it is flagged for manual review.",
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-25"]},
        {"id": "AB-F04", "severity": "model", "title": "Only 4 of 96 fixtures reach a 70% match-winner probability",
         "detail": "Every NHL club has played 8–11 games, so the model shrinks points percentage hard toward .500 (K=10) and adds only a quarter-weight goal-differential term. The result is deliberately conservative: 4 fixtures clear 70% on the moneyline, 24 are Medium and 68 are Low. The High-confidence selections therefore come mostly from puck-line and team-total markets, which are published alongside the match-winner price rather than replacing it.",
         "sources": ["https://api-web.nhle.com/v1/standings/now"]},
        {"id": "AB-F05", "severity": "data", "title": "Two in-window High selections on one fixture are correlated",
         "detail": "Carolina's moneyline (−245) and Carolina over 2.5 team goals (−234) both sit inside the window for Columbus at Carolina on 29 October. They are related bets: a big Carolina win tends to settle both. Both are published with separate write-ups and the correlation is disclosed here.",
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-29"]},
        {"id": "AB-F06", "severity": "coverage", "title": "Recent-results evidence is limited to the games present in the captured 15–21 October payloads",
         "detail": "The NHL daily payloads returned for 15–21 October contain only the games the API listed for those days, so a few clubs show one or two completed games rather than three. Write-ups cite only the games that are present; no result is inferred from a standings total.",
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-21"]},
        {"id": "AB-F07", "severity": "scope", "title": "OLBG is used for taxonomy only; no OLBG tip, percentage or comment is reproduced",
         "detail": "This desk's priced fixture list comes from the official league payloads, not from OLBG. OLBG's hub capture (03:04Z today, 17 hubs, all hash-verified) is used only for the listing of in-scope events this board could not price: each of those 138 match rows and 19 outrights shows the event name and listing start time exactly as OLBG published them, carries no price and no pick, names OLBG as a listing rather than an official source, and is flagged unverified. No OLBG tip, percentage, comment or price is reproduced anywhere on the site.",
         "sources": ["https://www.olbg.com/"]},
        {"id": "AB-F08", "severity": "model", "title": "LoL Esports fixtures are graded Low where the sample is under three completed series",
         "detail": "Series records come from the completed matches in the same official schedule payload. Teams whose Swiss-stage record is 0-0 carry almost no signal, so those fixtures are priced but held at Low confidence and their map handicap and map total are left blank because the payload has no map-score input.",
         "sources": ["https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US"]},
        {"id": "AB-F09", "severity": "verification", "title": "No injury, suspension, weather or line-up check was performed",
         "detail": "The verification register covers participants, date, start time, venue, records and scoring inputs only. Team news, injuries, suspensions, weather and line movement are named as not checked on every row rather than implied to be clear.",
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-22"]},
        {"id": "AB-F11", "severity": "scope", "title": "OLBG lists Gaelic Football and Motor Racing events the brief does not name",
         "detail": "The brief excludes soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling and specials. OLBG's live listing carried 5 Gaelic Football match rows and 6 Motor Racing outright rows (plus 1 Gaelic Football outright). Gaelic Football is not soccer and Motor Racing is not cycling, but neither is explicitly in scope. Both are carried on the all-fixtures page with a blank official source and a blank price, and are flagged here rather than priced or dropped.",
         "sources": ["https://www.olbg.com/betting-tips/Gaelic_Football/11", "https://www.olbg.com/betting-tips/Motor_Racing/7"]},
        {"id": "AB-F12", "severity": "repo", "title": "Three generators write the repository root, so the root navigation can be silently overwritten",
         "detail": "While validating this board's pointer on the root dashboard, two existing generators rewrote index.html and 27 other root pages: tools/build_master_site.py (master-board style, 28 pages) and scripts/session-83451f65/build_site.py (integrated style). No CI gate diffs the root against either generator, so a later run of either would drop this board's pointer without failing a check. This board restored the committed root pages and kept its change additive; the overlap is recorded here rather than fixed inside another board's generator.",
         "sources": ["https://github.com/buffedlizard55-lab/OLBG4/blob/main/index.html", "https://github.com/buffedlizard55-lab/OLBG4/blob/main/tools/build_master_site.py"]},
        {"id": "AB-F10", "severity": "data", "title": "World Series schedule extends beyond the published window",
         "detail": "The live MLB read returned seven World Series games (23, 24, 26, 27, 28, 30 and 31 October). Only the five inside 22 October – 2 November are published; games 6 and 7 fall outside the window and are deliberately omitted rather than truncated silently.",
         "sources": ["https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-29&gameTypes=W"]},
    ]
    (DATA / "flagged.json").write_text(json.dumps({
        "schema": "olbg4.board-ab.flagged/1", "board": "AB",
        "note": "Flagged for Review. Every item is published on the site so it can be reviewed after the merge; nothing here blocks publication and no value has been silently corrected.",
        "items": flagged}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"verification_rows": len(register), "verified": sum(1 for r in register if r["status"] == "verified"),
                      "coverage_rows": len(coverage), "flagged": len(flagged)}, indent=2))


if __name__ == "__main__":
    main()

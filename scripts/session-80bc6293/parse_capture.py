#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) — parse the committed capture into structured JSON.

Everything here reads ONLY the bytes committed by the capture workflow
(data/session-80bc6293/capture/<stamp>/raw/*) plus the official pages transcribed by hand
into data/session-80bc6293/official_*.json (each of which records the exact URL, the fetch
time and the fact that it was read from the rendered official page).

No number is invented here: a field that the source does not print is left out.
"""
from __future__ import annotations

import glob
import gzip
import hashlib
import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")


def capture_dir() -> str:
    dirs = sorted(glob.glob(os.path.join(DATA, "capture", "2*")))
    if not dirs:
        raise SystemExit("no capture directory found under data/session-80bc6293/capture/")
    return dirs[-1]


def raw_bytes(path: str) -> bytes:
    b = open(path, "rb").read()
    if b[:2] == b"\x1f\x8b":
        try:
            b = gzip.decompress(b)
        except OSError:
            pass
    return b


def rd(path: str) -> str:
    return raw_bytes(path).decode("utf-8", "replace")


def sha(path: str) -> str:
    return hashlib.sha256(raw_bytes(path)).hexdigest()


def strip_tags(s: str) -> str:
    s = re.sub(r"<script[^>]*>.*?</script>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<style[^>]*>.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


# ---------------------------------------------------------------- NHL
def parse_nhl(cdir: str) -> dict:
    sched = {}
    for wk in ("1022", "1029", "1105"):
        f = os.path.join(cdir, "raw", f"nhl_schedule_week_{wk}.bin")
        if os.path.exists(f):
            sched[wk] = json.loads(rd(f))
    st_file = os.path.join(cdir, "raw", "nhl_standings_now.bin")
    standings = json.loads(rd(st_file))
    teams = {}
    for r in standings["standings"]:
        ab = r["teamAbbrev"]["default"]
        teams[ab] = {
            "abbrev": ab,
            "name": r["teamName"]["default"],
            "common": r["teamCommonName"]["default"],
            "gamesPlayed": r["gamesPlayed"],
            "wins": r["wins"], "losses": r["losses"], "otLosses": r["otLosses"],
            "points": r["points"], "pointPctg": r["pointPctg"],
            "goalFor": r["goalFor"], "goalAgainst": r["goalAgainst"],
            "goalDifferential": r["goalDifferential"],
            "regulationPlusOtWins": r["regulationPlusOtWins"],
            "homeGamesPlayed": r["homeGamesPlayed"], "homeWins": r["homeWins"],
            "homeLosses": r["homeLosses"], "homeOtLosses": r["homeOtLosses"],
            "homeGoalsFor": r["homeGoalsFor"], "homeGoalsAgainst": r["homeGoalsAgainst"],
            "roadGamesPlayed": r["roadGamesPlayed"], "roadWins": r["roadWins"],
            "roadLosses": r["roadLosses"], "roadOtLosses": r["roadOtLosses"],
            "roadGoalsFor": r["roadGoalsFor"], "roadGoalsAgainst": r["roadGoalsAgainst"],
            "l10Wins": r["l10Wins"], "l10Losses": r["l10Losses"], "l10OtLosses": r["l10OtLosses"],
            "l10GoalsFor": r["l10GoalsFor"], "l10GoalsAgainst": r["l10GoalsAgainst"],
            "streakCode": r.get("streakCode", ""), "streakCount": r.get("streakCount", ""),
            "division": r["divisionName"], "conference": r["conferenceName"],
            "leagueSequence": r["leagueSequence"],
        }
    games = []
    for wk, doc in sched.items():
        for day in doc["gameWeek"]:
            for g in day.get("games", []):
                odds = {}
                for side in ("awayTeam", "homeTeam"):
                    vals = []
                    for o in g.get(side, {}).get("odds", []):
                        vals.append(str(o.get("value", "")))
                    odds[side] = vals
                games.append({
                    "id": g["id"], "date": day["date"], "startTimeUTC": g["startTimeUTC"],
                    "gameState": g["gameState"], "venue": g["venue"].get("default", ""),
                    "awayAbbrev": g["awayTeam"]["abbrev"],
                    "away": g["awayTeam"]["placeName"]["default"] + " " + g["awayTeam"]["commonName"]["default"],
                    "homeAbbrev": g["homeTeam"]["abbrev"],
                    "home": g["homeTeam"]["placeName"]["default"] + " " + g["homeTeam"]["commonName"]["default"],
                    "odds_away": odds["awayTeam"], "odds_home": odds["homeTeam"],
                    "gameCenterLink": "https://www.nhl.com" + g.get("gameCenterLink", ""),
                })
    return {
        "source_schedule": ["https://api-web.nhle.com/v1/schedule/2026-10-22",
                            "https://api-web.nhle.com/v1/schedule/2026-10-29",
                            "https://api-web.nhle.com/v1/schedule/2026-11-05"],
        "source_standings": "https://api-web.nhle.com/v1/standings/now",
        "standings_as_of_utc": standings["standingsDateTimeUtc"],
        "sha256_standings": sha(st_file),
        "teams": teams, "games": games,
    }


# ---------------------------------------------------------------- MLB
def parse_mlb(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "mlb_schedule_ws.bin")
    s = json.loads(rd(f))
    games = []
    for d in s["dates"]:
        for g in d["games"]:
            games.append({
                "gamePk": g["gamePk"], "officialDate": g["officialDate"], "gameDate": g["gameDate"],
                "description": g.get("description", ""), "seriesDescription": g.get("seriesDescription", ""),
                "seriesGameNumber": g.get("seriesGameNumber"), "gamesInSeries": g.get("gamesInSeries"),
                "ifNecessary": g.get("ifNecessary"), "status": g["status"]["detailedState"],
                "venue": g["venue"]["name"],
                "away": g["teams"]["away"]["team"]["name"], "awayId": g["teams"]["away"]["team"]["id"],
                "home": g["teams"]["home"]["team"]["name"], "homeId": g["teams"]["home"]["team"]["id"],
                "link": "https://www.mlb.com/gameday/" + str(g["gamePk"]),
            })
    sf = os.path.join(cdir, "raw", "mlb_standings_2026.bin")
    st = json.loads(rd(sf))
    teams = {}
    for rec in st["records"]:
        for tr in rec.get("teamRecords", []):
            t = tr["team"]
            teams[t["name"]] = {
                "id": t["id"], "wins": tr["wins"], "losses": tr["losses"],
                "winningPercentage": tr.get("winningPercentage"),
                "gamesBack": tr.get("gamesBack"), "divisionRank": tr.get("divisionRank"),
                "leagueRank": tr.get("leagueRank"),
                "runsScored": tr.get("runsScored"), "runsAllowed": tr.get("runsAllowed"),
                "lastUpdated": tr.get("lastUpdated"),
                "records_split": {k: (v.get("wins"), v.get("losses"))
                                  for k, v in (tr.get("records", {}).get("splitRecords") and
                                               {x["type"]: x for x in tr["records"]["splitRecords"]}.items() or {})},
            }
    return {"source_schedule": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-01&hydrate=team,venue",
            "source_standings": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason&hydrate=team",
            "sha256_schedule": sha(f), "games": games, "teams": teams}


# ---------------------------------------------------------------- PlusLiga (Polish men's volleyball)
def parse_plusliga(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "plusliga_table.bin")
    s = rd(f)
    title = re.search(r"<title>(.*?)</title>", s, re.S)
    out = {"title": html.unescape(title.group(1)).strip() if title else "", "rows": [],
           "source": "https://www.plusliga.pl/table.html", "sha256": sha(f)}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        cells = [c for c in cells if c != ""]
        if len(cells) >= 8 and re.search(r"\d", cells[0]):
            out["rows"].append(cells)
    return out


# ---------------------------------------------------------------- LegaVolley (Italian SuperLega)
def parse_legavolley(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "legavolley_calendario.bin")
    s = rd(f)
    txt = strip_tags(s)
    pairs = re.findall(r"([A-Z][A-Za-z\.&' ]{2,34})\s*-\s*([A-Z][A-Za-z\.&' ]{2,34})", txt)
    return {"source": "https://www.legavolley.it/calendario/", "sha256": sha(f),
            "visible_text_len": len(txt), "pairs_sample": [list(p) for p in pairs[:40]],
            "text_head": txt[:1200]}


# ---------------------------------------------------------------- RLWC 2026
def parse_rlwc(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "rlwc_official.bin")
    s = rd(f)
    unesc = s.replace('\\"', '"').replace("\\\\", "\\")
    teams = sorted(set(re.findall(r'"teamName":"([^"]{2,45})"', unesc)))
    dates = sorted(set(re.findall(r'"(?:date|matchTime|kickOff[A-Za-z]*)":"(20[0-9\-T:\.Z+]{8,40})"', unesc)))
    venues = sorted(set(re.findall(r'"(?:venueName|stadiumName|venue)":"([^"]{2,60})"', unesc)))
    return {"source": "https://www.rlwc2026.com/", "sha256": sha(f),
            "teams": teams, "dates_found": dates[:40], "venues_found": venues[:40],
            "keys": sorted(set(re.findall(r'"([a-zA-Z]{3,24})":', unesc)))[:200]}


# ---------------------------------------------------------------- Motor racing
def parse_motor(cdir: str) -> dict:
    out = {}
    for key, fname, anchor in (("f1", "f1_racing_2026.bin", "Race Calendar"),
                               ("f1_results", "f1_results.bin", "Results"),
                               ("motogp", "motogp_calendar.bin", "Calendar")):
        f = os.path.join(cdir, "raw", fname)
        if not os.path.exists(f):
            continue
        txt = strip_tags(rd(f))
        i = txt.find(anchor)
        out[key] = {"source": {"f1": "https://www.formula1.com/en/racing/2026",
                               "f1_results": "https://www.formula1.com/en/results/2026/drivers",
                               "motogp": "https://www.motogp.com/en/calendar"}[key],
                    "sha256": sha(f), "text": txt[max(0, i - 60): i + 1600]}
    return out


# ---------------------------------------------------------------- PGA Tour
def parse_pgatour(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "pgatour_schedule.bin")
    s = rd(f)
    i = s.find("__NEXT_DATA__")
    out = {"source": "https://www.pgatour.com/schedule", "sha256": sha(f), "tournaments": []}
    if i < 0:
        return out
    j = s.find(">", i) + 1
    k = s.find("</script>", j)
    try:
        nd = json.loads(s[j:k])
    except json.JSONDecodeError:
        return out
    blob = json.dumps(nd)
    out["next_data_bytes"] = len(blob)
    for m in re.finditer(r'"tournamentName"\s*:\s*"([^"]{3,80})"', blob):
        out["tournaments"].append(m.group(1))
    for key in ("season", "schedule", "tournaments"):
        if key in blob:
            out.setdefault("keys_seen", []).append(key)
    out["tournaments"] = sorted(set(out["tournaments"]))[:60]
    return out


# ---------------------------------------------------------------- WST snooker rankings (Nuxt state)
def parse_wst(cdir: str) -> dict:
    f = os.path.join(cdir, "raw", "wst_rankings.bin")
    s = rd(f)
    names = re.findall(r'"(?:firstName|lastName|playerName|name)":"([A-Z][A-Za-z\'\-\. ]{1,30})"', s)
    ranks = re.findall(r'"(?:rank|position|ranking)":(\d{1,3})', s)
    return {"source": "https://wst.tv/rankings", "sha256": sha(f),
            "names_sample": sorted(set(names))[:40], "ranks_sample": ranks[:40],
            "len": len(s)}


# ---------------------------------------------------------------- BWF badminton
def parse_bwf(cdir: str) -> dict:
    out = {}
    for key, fname in (("rankings", "bwf_rankings.bin"), ("calendar", "bwf_calendar.bin")):
        f = os.path.join(cdir, "raw", fname)
        if not os.path.exists(f):
            continue
        s = rd(f)
        txt = strip_tags(s)
        out[key] = {"source": {"rankings": "https://bwfbadminton.com/rankings/",
                               "calendar": "https://bwfbadminton.com/calendar/"}[key],
                    "sha256": sha(f), "text_head": txt[:1500], "len": len(txt)}
    return out


# ---------------------------------------------------------------- OLBG listings (reverse-engineered inventory)
SPORT_HUBS = {
    "Tennis": 3, "Basketball": 4, "Golf": 5, "Cricket": 7, "Snooker": 8, "Rugby Union": 9,
    "Rugby League": 10, "Baseball": 12, "Ice Hockey": 13, "Motor Racing": 14, "Darts": 15,
    "Handball": 20, "Volleyball": 21, "Aussie Rules": 22, "Esports": 23, "Gaelic Football": 25,
    "Greyhounds": 28,
    "Football": 1, "Horse Racing": 2, "Specials": 6, "American Football": 11, "Boxing": 16,
    "Cycling": 17, "Hurling": 26,
}


def parse_olbg(cdir: str) -> dict:
    out = {"sports": {}, "source_pattern": "https://www.olbg.com/betting-tips/<Sport>/<sport_id>"}
    for sport, sid in SPORT_HUBS.items():
        slug = {"Rugby Union": "Rugby_Union", "Rugby League": "Rugby_League", "Ice Hockey": "Ice_Hockey",
                "Motor Racing": "Motor_Racing", "Aussie Rules": "Aussie_Rules", "Gaelic Football": "Gaelic_Football",
                "American Football": "American_Football", "Horse Racing": "Horse_Racing",
                "Esports": "eSports"}.get(sport, sport)
        f = os.path.join(cdir, "raw", f"olbg_hub_{slug.lower()}_{sid}.bin")
        if not os.path.exists(f):
            continue
        s = rd(f)
        events = {}
        for m in re.finditer(r'href="(https://www\.olbg\.com/betting-tips/[^"]*?/([^/"]+)/(\d+))(?:\?event_id=(\d+))?"', s):
            url, evname, sport_id, evid = m.group(1), m.group(2), m.group(3), m.group(4)
            if evid:
                events[evid] = {"event": evname.replace("_", " "), "url": url + f"?event_id={evid}",
                                "olbg_sport_id": int(sport_id)}
        markets = sorted(set(re.findall(r'(?:Win Match(?: 2-way)?|Money Line|Full Time Result|Handicap(?: 2-way)?|'
                                        r'Total (?:Legs|Goals|Points|Runs|Sets|Games|Frames)|Outright Winner|'
                                        r'Set Betting|Games Won|Match Betting|To Win|Daily Racing|Man Of The Match|'
                                        r'Draw No Bet|Double Chance|Correct Score|Over/Under|Each Way|Winner|'
                                        r'Top Batter|Top Bowler|Race Winner|Frame Handicap|First Goalscorer)', s)))
        comp_paths = sorted(set(re.findall(r'/betting-tips/' + slug + r'/([A-Za-z_0-9]+)/([A-Za-z_0-9]+)/', s)))[:40]
        out["sports"][sport] = {
            "sport_id": sid, "hub_url": f"https://www.olbg.com/betting-tips/{slug}/{sid}",
            "sha256": sha(f), "events_listed": len(events),
            "events": sorted(events.values(), key=lambda e: e["event"]),
            "markets_seen": markets, "competition_paths": comp_paths,
        }
    return out


def main() -> int:
    cdir = capture_dir()
    print("capture:", cdir)
    os.makedirs(os.path.join(DATA, "parsed"), exist_ok=True)
    jobs = [("nhl", parse_nhl), ("mlb", parse_mlb), ("plusliga", parse_plusliga),
            ("legavolley", parse_legavolley), ("rlwc", parse_rlwc), ("motor", parse_motor),
            ("pgatour", parse_pgatour), ("wst", parse_wst), ("bwf", parse_bwf), ("olbg", parse_olbg)]
    summary = {}
    for name, fn in jobs:
        try:
            d = fn(cdir)
        except Exception as exc:
            print(f"  {name}: FAILED {type(exc).__name__}: {exc}")
            summary[name] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        p = os.path.join(DATA, "parsed", f"{name}.json")
        json.dump(d, open(p, "w"), indent=1)
        size = os.path.getsize(p)
        summary[name] = {"file": p, "bytes": size}
        if name == "nhl":
            summary[name].update(games=len(d["games"]), teams=len(d["teams"]), as_of=d["standings_as_of_utc"])
        elif name == "mlb":
            summary[name].update(games=len(d["games"]), teams=len(d["teams"]))
        elif name == "plusliga":
            summary[name].update(rows=len(d["rows"]), title=d["title"][:80])
        elif name == "rlwc":
            summary[name].update(teams=len(d["teams"]), dates=len(d["dates_found"]), venues=len(d["venues_found"]))
        elif name == "pgatour":
            summary[name].update(tournaments=len(d["tournaments"]), next_data_bytes=d.get("next_data_bytes", 0))
        elif name == "olbg":
            summary[name].update(sports=len(d["sports"]),
                                 events={k: v["events_listed"] for k, v in d["sports"].items()})
        print(f"  {name}: {json.dumps({k: v for k, v in summary[name].items() if k != 'file'})[:300]}")
    json.dump(summary, open(os.path.join(DATA, "parsed", "_summary.json"), "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())

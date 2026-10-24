#!/usr/bin/env python3
"""Evidence loaders and reproducible fair-price calculations for Board A172."""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-a172d5b9"
SITE = ROOT / "session-a172d5b9"
SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]
SLUGS = {
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball",
    "Gaelic Sports": "gaelic-sports", "Greyhounds": "greyhounds", "Tennis": "tennis",
    "Motor Racing": "motor-racing", "Handball": "handball", "Ice Hockey": "ice-hockey",
    "Basketball": "basketball", "Rugby League": "rugby-league",
}


def utc(value: str) -> str:
    if not value:
        return ""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()


def is_olbg(url: str) -> bool:
    return (urlparse(url or "").hostname or "").lower().endswith("olbg.com")


def american(prob: float) -> int:
    if prob >= 0.5:
        return -int(round(100 * prob / (1 - prob)))
    return int(round(100 * (1 - prob) / prob))


def price(prob: float) -> dict:
    p = round(float(prob), 4)
    if not 0 < p < 1:
        raise ValueError(f"probability outside (0,1): {prob}")
    return {"fair_prob": p, "fair_decimal": round(1 / p, 2), "fair_american": american(p)}


def market(name: str, line, legs: list[tuple[str, float]], note: str = "") -> dict:
    selections = [{"label": label, **price(p)} for label, p in legs]
    return {
        "market_name": name, "line": line, "note": note, "selections": selections,
        "probability_sum": round(sum(s["fair_prob"] for s in selections), 4),
    }


class Evidence:
    def __init__(self, capture_dir: str | Path):
        self.dir = Path(capture_dir)
        self.manifest = json.loads((self.dir / "manifest.json").read_text(encoding="utf-8"))
        self.records = {r["id"]: r for r in self.manifest["records"]}

    def raw(self, record_id: str) -> bytes:
        record = self.records[record_id]
        blob = (self.dir / record["file"]).read_bytes()
        return gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob

    def text(self, record_id: str) -> str:
        return self.raw(record_id).decode("utf-8", "replace")

    def json(self, record_id: str):
        return json.loads(self.raw(record_id))

    def url(self, record_id: str) -> str:
        return self.records[record_id]["url"]

    def sha(self, record_id: str) -> str:
        return hashlib.sha256(self.raw(record_id)).hexdigest()

    def exists(self, record_id: str) -> bool:
        return record_id in self.records


def nhl_standings(ev: Evidence) -> dict[str, dict]:
    out = {}
    for team in ev.json("nhl_standings")["standings"]:
        code = team["teamAbbrev"]["default"]
        gp = team["gamesPlayed"]
        if not gp:
            continue
        out[code] = {
            "code": code, "team": team["teamName"]["default"], "gp": gp,
            "w": team["wins"], "l": team["losses"], "otl": team["otLosses"],
            "pts": team["points"], "gf": team["goalFor"], "ga": team["goalAgainst"],
            "gf_pg": team["goalFor"] / gp, "ga_pg": team["goalAgainst"] / gp,
            "l10": f"{team['l10Wins']}-{team['l10Losses']}-{team['l10OtLosses']}",
            "streak": f"{team['streakCode']}{team['streakCount']}",
            "home": f"{team['homeWins']}-{team['homeLosses']}-{team['homeOtLosses']}",
            "road": f"{team['roadWins']}-{team['roadLosses']}-{team['roadOtLosses']}",
        }
    return out


def nhl_games(ev: Evidence) -> dict[str, dict]:
    games = {}
    for record in ev.manifest["records"]:
        if not record["id"].startswith("nhl_sched_"):
            continue
        payload = ev.json(record["id"])
        for week in payload.get("gameWeek", []):
            for game in week.get("games", []):
                item = dict(game)
                item["_capture_id"] = record["id"]
                item["_source_url"] = record["url"]
                games[str(game["id"])] = item
    return games


def nhl_recent(ev: Evidence, code: str, before: str, limit: int = 3) -> list[dict]:
    found = []
    for game in nhl_games(ev).values():
        if game.get("gameState") not in ("OFF", "FINAL"):
            continue
        if game.get("startTimeUTC", "") >= before:
            continue
        away, home = game.get("awayTeam") or {}, game.get("homeTeam") or {}
        if code not in (away.get("abbrev"), home.get("abbrev")):
            continue
        if away.get("score") is None or home.get("score") is None:
            continue
        is_home = home.get("abbrev") == code
        own, opp = (home, away) if is_home else (away, home)
        result = "W" if own["score"] > opp["score"] else "L"
        found.append({
            "game_id": str(game["id"]), "start_utc": utc(game["startTimeUTC"]),
            "text": f"{result} {own['score']}-{opp['score']} {'vs' if is_home else 'at'} {opp.get('commonName', {}).get('default', opp.get('abbrev', ''))}",
            "source_url": game["_source_url"], "capture_id": game["_capture_id"],
        })
    return sorted(found, key=lambda x: x["start_utc"], reverse=True)[:limit]


def nhl_lambdas(away: dict, home: dict, league_goals: float) -> tuple[float, float]:
    home_att = 0.7 * (home["gf_pg"] / (league_goals / 2)) + 0.3
    away_att = 0.7 * (away["gf_pg"] / (league_goals / 2)) + 0.3
    home_def = 0.7 * (home["ga_pg"] / (league_goals / 2)) + 0.3
    away_def = 0.7 * (away["ga_pg"] / (league_goals / 2)) + 0.3
    lh = max(0.8, min(5.2, (league_goals / 2) * home_att * away_def * 1.06))
    la = max(0.8, min(5.2, (league_goals / 2) * away_att * home_def * 0.94))
    return lh, la


def pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def probabilities(lam: float, max_goals: int = 18) -> list[float]:
    values = [pmf(k, lam) for k in range(max_goals + 1)]
    return [v / sum(values) for v in values]


def grid(lh: float, la: float, max_goals: int = 18):
    ph, pa = probabilities(lh, max_goals), probabilities(la, max_goals)
    cells = [(h, a, ph[h] * pa[a]) for h in range(max_goals + 1) for a in range(max_goals + 1)]
    return ph, pa, cells


def shrink(p: float, k: float = 0.88) -> float:
    return 0.5 + k * (p - 0.5)


def nhl_markets(away_name: str, home_name: str, lh: float, la: float, expanded: bool = False) -> dict:
    ph, pa, cells = grid(lh, la)
    home_reg = sum(p for h, a, p in cells if h > a)
    tie = sum(p for h, a, p in cells if h == a)
    away_reg = sum(p for h, a, p in cells if h < a)
    p_home = min(0.82, max(0.18, shrink(home_reg + 0.5 * tie)))
    p_away = 1 - p_home
    margin = lambda predicate: sum(p for h, a, p in cells if predicate(h - a))
    total = lambda predicate: sum(p for h, a, p in cells if predicate(h + a))
    base_total = round(lh + la) + 0.5
    over = total(lambda n: n > base_total)
    markets = {
        "match_winner": market("Money Line (incl. OT/SO)", None, [
            (f"{away_name} (away)", p_away), (f"{home_name} (home)", p_home)]),
        "handicap": market("Puck Line 1.5 (regulation)", -1.5, [
            (f"{home_name} -1.5", margin(lambda m: m >= 2)),
            (f"{away_name} +1.5", margin(lambda m: m <= 1))]),
        "total": market(f"Total Goals {base_total} (regulation)", base_total, [
            (f"Under {base_total}", 1 - over), (f"Over {base_total}", over)]),
    }
    if not expanded:
        return markets
    markets["regulation_3way"] = market("Regulation 3-way", None, [
        (home_name, home_reg), ("Draw", tie), (away_name, away_reg)])
    markets["regulation_handicap"] = market("Regulation Handicap 0.5", -0.5, [
        (f"{home_name} -0.5", home_reg), (f"{away_name} +0.5", away_reg + tie)],
        "Home -0.5 needs a regulation home win; away +0.5 covers an away win or draw.")
    for line in (0.5, 1.5, 2.5, 3.5):
        p = margin(lambda m, line=line: m + line > 0)
        markets[f"home_plus_{str(line).replace('.', '_')}"] = market(
            f"Puck Line {line} (regulation)", line,
            [(f"{home_name} +{line}", p), (f"{away_name} -{line}", 1 - p)])
    for line in (4.5, 5.5, 6.5, 7.5, 8.5, 9.5):
        p = total(lambda n, line=line: n > line)
        markets[f"total_{str(line).replace('.', '_')}"] = market(
            f"Total Goals {line} (regulation)", line,
            [(f"Under {line}", 1 - p), (f"Over {line}", p)])
    for side, name, probs in (("home", home_name, ph), ("away", away_name, pa)):
        for line in (1.5, 2.5, 3.5, 4.5, 5.5):
            p = sum(v for goals, v in enumerate(probs) if goals > line)
            markets[f"{side}_team_total_{str(line).replace('.', '_')}"] = market(
                f"{name} Team Total {line} (regulation)", line,
                [(f"{name} under {line}", 1 - p), (f"{name} over {line}", p)])
    return markets


NHL_ALIASES = {
    "LAK": ("LA", "LAK"), "NJD": ("NJ", "NJD"), "VGK": ("VGS", "VGK"),
    "SJS": ("SJ", "SJS"), "NYR": ("NY", "NYR"), "NYI": ("NYI",),
    "TBL": ("TB", "TBL"), "WSH": ("WAS", "WSH"), "UTA": ("UTA",),
    "CBJ": ("CLB", "CBJ"),
}
NBA_ALIASES = {
    "NOP": ("NO", "NOP"), "SAS": ("SA", "SAS"), "GSW": ("GS", "GSW"),
    "PHX": ("PHX",), "BKN": ("BKN",), "NYK": ("NY", "NYK"), "UTA": ("UTA",),
}
MLB_ALIASES = {
    "Tampa Bay Rays": ("TB", "Rays"), "Milwaukee Brewers": ("MIL", "Brewers"),
    "Los Angeles Dodgers": ("LA", "LAD", "Dodgers"), "Toronto Blue Jays": ("TOR", "Blue Jays"),
    "New York Yankees": ("NY", "NYY", "Yankees"), "New York Mets": ("NYM", "Mets"),
    "Boston Red Sox": ("BOS", "Red Sox"), "Chicago Cubs": ("CHC", "Cubs"),
    "Chicago White Sox": ("CWS", "CHI", "White Sox"), "Philadelphia Phillies": ("PHI", "Phillies"),
    "Atlanta Braves": ("ATL", "Braves"), "Houston Astros": ("HOU", "Astros"),
    "Seattle Mariners": ("SEA", "Mariners"), "San Diego Padres": ("SD", "Padres"),
    "San Francisco Giants": ("SF", "Giants"), "St. Louis Cardinals": ("STL", "Cardinals"),
    "Detroit Tigers": ("DET", "Tigers"), "Cleveland Guardians": ("CLE", "Guardians"),
    "Cincinnati Reds": ("CIN", "Reds"), "Pittsburgh Pirates": ("PIT", "Pirates"),
    "Baltimore Orioles": ("BAL", "Orioles"), "Minnesota Twins": ("MIN", "Twins"),
    "Kansas City Royals": ("KC", "Royals"), "Texas Rangers": ("TEX", "Rangers"),
    "Athletics": ("ATH", "OAK", "Athletics"), "Los Angeles Angels": ("LAA", "LA", "Angels"),
    "Miami Marlins": ("MIA", "Marlins"), "Washington Nationals": ("WSH", "WAS", "Nationals"),
    "Arizona Diamondbacks": ("AZ", "ARI", "Diamondbacks"), "Colorado Rockies": ("COL", "Rockies"),
}


def alias_label_match(event_name: str, away_aliases: list[str], away_suffix: str,
                      home_aliases: list[str], home_suffix: str, separator: str = "@") -> bool:
    target = clean(event_name).casefold()
    for away in away_aliases:
        for home in home_aliases:
            expected = f"{away} {away_suffix} {separator} {home} {home_suffix}"
            if clean(expected).casefold() == target:
                return True
    return False


def player_facts(ev: Evidence) -> dict[str, dict]:
    facts = {}
    if ev.exists("nhl_skaters"):
        for category, records in ev.json("nhl_skaters").items():
            for item in records:
                name = f"{item['firstName']['default']} {item['lastName']['default']}"
                facts.setdefault(name, {"team": item["teamAbbrev"]})[category] = item["value"]
    if ev.exists("nhl_goalies"):
        for category, records in ev.json("nhl_goalies").items():
            for item in records:
                name = f"{item['firstName']['default']} {item['lastName']['default']}"
                facts.setdefault(name, {"team": item["teamAbbrev"]})[category] = item["value"]
    return facts


def nba_official_rows(ev: Evidence) -> list[dict]:
    if not ev.exists("nba_schedule_full"):
        return []
    payload = ev.json("nba_schedule_full")
    schedule = payload.get("leagueSchedule") or {}
    games = [g for block in schedule.get("gameDates", []) for g in block.get("games", [])]
    records, recent = {}, {}
    for game in games:
        if game.get("gameStatus") != 3 or not str(game.get("gameId", "")).startswith("002"):
            continue
        home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
        if home.get("score") is None or away.get("score") is None:
            continue
        for own, opp, is_home in ((home, away, True), (away, home, False)):
            code = own.get("teamTricode", "")
            rec = records.setdefault(code, {"w": 0, "l": 0})
            rec["w" if own["score"] > opp["score"] else "l"] += 1
            recent.setdefault(code, []).append({
                "start_utc": utc(game.get("gameDateTimeUTC") or game.get("gameDateTimeEst") or ""),
                "text": f"{'W' if own['score'] > opp['score'] else 'L'} {own['score']}-{opp['score']} {'vs' if is_home else 'at'} {opp.get('teamName', '')}",
                "source_url": ev.url("nba_schedule_full"), "capture_id": "nba_schedule_full",
            })
    rows = []
    for game in games:
        if game.get("gameStatus") != 1 or not str(game.get("gameId", "")).startswith("002"):
            continue
        start = utc(game.get("gameDateTimeUTC") or game.get("gameDateTimeEst") or "")
        if not start:
            continue
        home, away = game.get("homeTeam") or {}, game.get("awayTeam") or {}
        ac, hc = away.get("teamTricode", ""), home.get("teamTricode", "")
        ar, hr = records.get(ac, {"w": 0, "l": 0}), records.get(hc, {"w": 0, "l": 0})
        sample = min(ar["w"] + ar["l"], hr["w"] + hr["l"])
        rows.append({
            "id": f"fx_nba_{game['gameId']}", "sport": "Basketball", "sport_slug": "basketball",
            "competition": "NBA 2026-27 Regular Season",
            "side_a": f"{away.get('teamCity', '')} {away.get('teamName', '')}".strip(),
            "side_b": f"{home.get('teamCity', '')} {home.get('teamName', '')}".strip(),
            "a_code": ac, "b_code": hc, "start_utc": start, "venue": game.get("arenaName") or "",
            "capture_id": "nba_schedule_full", "official_url": ev.url("nba_schedule_full"),
            "official_source_name": "NBA official full-season schedule (cdn.nba.com)",
            "extra": {"nba_id": str(game["gameId"]), "away_name": away.get("teamName", ""), "home_name": home.get("teamName", "")},
            "evidence": {"away_record": f"{ar['w']}-{ar['l']}", "home_record": f"{hr['w']}-{hr['l']}", "standings_source": ev.url("nba_schedule_full")},
            "form": {"away": f"{ar['w']}-{ar['l']}", "home": f"{hr['w']}-{hr['l']}"},
            "recent": {"away": sorted(recent.get(ac, []), key=lambda x: x["start_utc"], reverse=True)[:3],
                       "home": sorted(recent.get(hc, []), key=lambda x: x["start_utc"], reverse=True)[:3]},
            "sample": f"{sample} completed regular-season games (minimum of the two clubs)",
            "model": {}, "markets": {}, "pick": None,
            "flags": [f"Only {sample} completed regular-season games for at least one club; winner, spread and total prices withheld below the 20-game evidence threshold."],
        })
    return rows


def _dk_cell(block: str, cls: str) -> str:
    match = re.search(r"match-program__row__" + cls + r"\">(.*?)</div>", block, re.S)
    return clean(match.group(1)) if match else ""


def danish_programme(ev: Evidence) -> list[dict]:
    if not ev.exists("dk_herreligaen_program"):
        return []
    rows = []
    for block in re.split(r"match-program__row\s*\">", ev.text("dk_herreligaen_program"))[1:]:
        date = _dk_cell(block, "date")
        teams = [clean(x) for x in re.findall(r"match-program__row__team\">(.*?)</div>", block, re.S)]
        score = _dk_cell(block, "score")
        match = re.match(r"(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2})$", date)
        if not match or len(teams) != 2:
            continue
        dd, mm, yy, hh, mi = (int(x) for x in match.groups())
        local = datetime(2000 + yy, mm, dd, hh, mi, tzinfo=ZoneInfo("Europe/Copenhagen"))
        result = re.match(r"^(\d{2,3})-(\d{2,3})$", score)
        rows.append({
            "start_utc": local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": teams[0], "away": teams[1],
            "home_goals": int(result.group(1)) if result else None,
            "away_goals": int(result.group(2)) if result else None,
            "source_url": ev.url("dk_herreligaen_program"), "capture_id": "dk_herreligaen_program",
        })
    return rows


def danish_recent(games: list[dict], team: str, before: str, limit: int = 3) -> list[dict]:
    found = []
    for game in games:
        if game["home_goals"] is None or game["start_utc"] >= before or team not in (game["home"], game["away"]):
            continue
        is_home = game["home"] == team
        own = game["home_goals"] if is_home else game["away_goals"]
        opp = game["away_goals"] if is_home else game["home_goals"]
        opponent = game["away"] if is_home else game["home"]
        result = "W" if own > opp else "D" if own == opp else "L"
        found.append({**game, "text": f"{result} {own}-{opp} {'vs' if is_home else 'at'} {opponent}"})
    return sorted(found, key=lambda x: x["start_utc"], reverse=True)[:limit]

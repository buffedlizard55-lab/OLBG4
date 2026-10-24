#!/usr/bin/env python3
"""Shared, read-only evidence loaders and transparent NHL calculations for Board RI."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SID = "session-11927acd"
DATA = ROOT / "data" / SID
SITE = ROOT / SID
BASE_SID = "session-b6643783"
BASE_DATA = ROOT / "data" / BASE_SID
CAPTURE_ID = "20261024T173907Z"
CAPTURE = BASE_DATA / "capture" / CAPTURE_ID
MANIFEST = json.loads((CAPTURE / "manifest.json").read_text())
RECORDS = {r["id"]: r for r in MANIFEST["records"]}
BASE_DESK = json.loads((BASE_DATA / "desk.json").read_text())
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

# The event ids are read from the captured OLBG cards. The assertions in build_data.py
# check both club abbreviations and the event URL before any crosswalk is published.
NHL_OLBG = {
    "fx_nhl_2026020169": 200000, "fx_nhl_2026020174": 200001,
    "fx_nhl_2026020175": 200002, "fx_nhl_2026020173": 200003,
    "fx_nhl_2026020178": 200004, "fx_nhl_2026020179": 200005,
    "fx_nhl_2026020172": 200006, "fx_nhl_2026020170": 200007,
    "fx_nhl_2026020171": 200008, "fx_nhl_2026020177": 200009,
    "fx_nhl_2026020176": 200010,
}
NHL_CODES = {
    "fx_nhl_2026020169": ("LA", "NJ"), "fx_nhl_2026020174": ("VGS", "CLB"),
    "fx_nhl_2026020175": ("CAR", "STL"), "fx_nhl_2026020173": ("BUF", "WAS"),
    "fx_nhl_2026020178": ("DET", "CGY"), "fx_nhl_2026020179": ("MIN", "SEA"),
    "fx_nhl_2026020172": ("NSH", "PIT"), "fx_nhl_2026020170": ("SJ", "BOS"),
    "fx_nhl_2026020171": ("NY", "OTT"), "fx_nhl_2026020177": ("TB", "UTA"),
    "fx_nhl_2026020176": ("TOR", "EDM"),
}


def generated_utc() -> str:
    return os.environ.get("RI_GENERATED_UTC") or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def raw(record_id: str) -> bytes:
    record = RECORDS[record_id]
    blob = (CAPTURE / record["file"]).read_bytes()
    return gzip.decompress(blob) if blob[:2] == b"\x1f\x8b" else blob


def raw_json(record_id: str):
    return json.loads(raw(record_id))


def actual_sha(record_id: str) -> str:
    return hashlib.sha256(raw(record_id)).hexdigest()


def is_olbg(url: str) -> bool:
    return (urlparse(url or "").hostname or "").lower().endswith("olbg.com")


def american(prob: float) -> int:
    if prob >= 0.5:
        return -int(round(100 * prob / (1 - prob)))
    return int(round(100 * (1 - prob) / prob))


def price(prob: float) -> dict:
    p = round(prob, 4)
    if not 0 < p < 1:
        raise ValueError(f"probability outside (0,1): {prob}")
    return {
        "fair_prob": p,
        "fair_decimal": round(1 / p, 2),
        "fair_american": american(p),
        "implied_prob_sum": 1.0,
    }


def make_market(name: str, line, legs: list[tuple[str, float]], note: str = "") -> dict:
    return {
        "market_name": name,
        "line": line,
        "note": note,
        "selections": [{"label": label, **price(p)} for label, p in legs],
    }


def pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def probabilities(lam: float, max_goals: int = 18) -> list[float]:
    values = [pmf(k, lam) for k in range(max_goals + 1)]
    total = sum(values)
    return [v / total for v in values]


def grid(lh: float, la: float, max_goals: int = 18):
    ph, pa = probabilities(lh, max_goals), probabilities(la, max_goals)
    return ph, pa, [(h, a, ph[h] * pa[a]) for h in range(max_goals + 1) for a in range(max_goals + 1)]


def nhl_standings() -> dict[str, dict]:
    out = {}
    for team in raw_json("nhl_standings")["standings"]:
        code = team["teamAbbrev"]["default"]
        gp = team["gamesPlayed"]
        out[code] = {
            "code": code,
            "team": team["teamName"]["default"],
            "gp": gp,
            "w": team["wins"], "l": team["losses"], "otl": team["otLosses"],
            "pts": team["points"], "gf": team["goalFor"], "ga": team["goalAgainst"],
            "gf_pg": team["goalFor"] / gp, "ga_pg": team["goalAgainst"] / gp,
            "l10": f"{team['l10Wins']}-{team['l10Losses']}-{team['l10OtLosses']}",
            "streak": f"{team['streakCode']}{team['streakCount']}",
            "home": f"{team['homeWins']}-{team['homeLosses']}-{team['homeOtLosses']}",
            "road": f"{team['roadWins']}-{team['roadLosses']}-{team['roadOtLosses']}",
        }
    return out


def nhl_fixtures() -> dict[str, dict]:
    out = {}
    for record in MANIFEST["records"]:
        if not record["id"].startswith("nhl_sched_"):
            continue
        payload = raw_json(record["id"])
        for week in payload.get("gameWeek", []):
            for game in week.get("games", []):
                gid = str(game["id"])
                out[gid] = {
                    "game_id": gid,
                    "capture_id": record["id"],
                    "official_url": record["url"],
                    "sha256": record["sha256"],
                    "start_utc": game["startTimeUTC"],
                    "venue": (game.get("venue") or {}).get("default", ""),
                    "away_code": game["awayTeam"]["abbrev"],
                    "home_code": game["homeTeam"]["abbrev"],
                    "game_state": game.get("gameState", ""),
                }
    return out


def nhl_lambdas(away: dict, home: dict, league_goals: float) -> tuple[float, float]:
    """Correct attack/opp-defence pairing with the published pooling and clamps."""
    home_att = 0.7 * (home["gf_pg"] / (league_goals / 2)) + 0.3
    away_att = 0.7 * (away["gf_pg"] / (league_goals / 2)) + 0.3
    home_def = 0.7 * (home["ga_pg"] / (league_goals / 2)) + 0.3
    away_def = 0.7 * (away["ga_pg"] / (league_goals / 2)) + 0.3
    lh = max(0.8, min(5.2, (league_goals / 2) * home_att * away_def * 1.06))
    la = max(0.8, min(5.2, (league_goals / 2) * away_att * home_def * 0.94))
    return lh, la


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
        "match_winner": make_market("Money Line (incl. OT/SO)", None, [
            (f"{away_name} (away)", p_away), (f"{home_name} (home)", p_home)]),
        "handicap": make_market("Puck Line 1.5 (regulation)", -1.5, [
            (f"{home_name} -1.5", margin(lambda m: m >= 2)),
            (f"{away_name} +1.5", margin(lambda m: m <= 1))]),
        "total": make_market(f"Total Goals {base_total}", base_total, [
            (f"Under {base_total}", 1 - over), (f"Over {base_total}", over)]),
    }
    if not expanded:
        return markets
    markets["regulation_winner"] = make_market("Regulation Winner", -0.5, [
        (f"{home_name} -0.5", home_reg), (f"{away_name} -0.5", away_reg)],
        "Draw is a separate possible result; this is not the moneyline including overtime.")
    markets["regulation_3way"] = make_market("Regulation 3-way", None, [
        (home_name, home_reg), ("Draw", tie), (away_name, away_reg)])
    for line in (0.5, 1.5, 2.5, 3.5):
        p = margin(lambda m, line=line: m + line > 0)
        markets[f"home_plus_{str(line).replace('.', '_')}"] = make_market(
            f"Puck Line {line} (regulation)", line,
            [(f"{home_name} +{line}", p), (f"{away_name} -{line}", 1 - p)])
    for line in (4.5, 5.5, 6.5, 7.5, 8.5, 9.5):
        p = total(lambda n, line=line: n > line)
        markets[f"total_{str(line).replace('.', '_')}"] = make_market(
            f"Total Goals {line} (regulation)", line,
            [(f"Under {line}", 1 - p), (f"Over {line}", p)])
    for side, name, probs in (("home", home_name, ph), ("away", away_name, pa)):
        for line in (1.5, 2.5, 3.5, 4.5, 5.5):
            p = sum(v for goals, v in enumerate(probs) if goals > line)
            markets[f"{side}_team_total_{str(line).replace('.', '_')}"] = make_market(
                f"{name} Team Total {line} (regulation)", line,
                [(f"{name} under {line}", 1 - p), (f"{name} over {line}", p)])
    return markets


def olbg_nhl_events() -> dict[int, dict]:
    text = raw("olbg_icehockey").decode("utf-8", "replace")
    pattern = re.compile(
        r'<a itemprop="url" href="(?P<url>[^"]*event_id=(?P<id>\d+))"[^>]*>.*?'
        r'<h5[^>]*itemprop="name"[^>]*>(?P<name>.*?)</h5>.*?'
        r'<time[^>]*datetime="(?P<start>[^"]+)"', re.S)
    events = {}
    for match in pattern.finditer(text):
        name = re.sub(r"<[^>]+>", "", match.group("name")).strip()
        eid = int(match.group("id"))
        events[eid] = {
            "event_id": eid, "url": match.group("url"), "name": name,
            "start_utc": match.group("start").replace(".000Z", "Z"),
            "capture_id": "olbg_icehockey", "sha256": RECORDS["olbg_icehockey"]["sha256"],
        }
    return events


def player_facts() -> dict[str, dict]:
    facts = {}
    for category, records in raw_json("nhl_skaters").items():
        for item in records:
            name = f"{item['firstName']['default']} {item['lastName']['default']}"
            facts.setdefault(name, {"team": item["teamAbbrev"]})[category] = item["value"]
    for category, records in raw_json("nhl_goalies").items():
        for item in records:
            name = f"{item['firstName']['default']} {item['lastName']['default']}"
            facts.setdefault(name, {"team": item["teamAbbrev"]})[category] = item["value"]
    return facts

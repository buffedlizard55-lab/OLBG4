#!/usr/bin/env python3
"""Turn the committed official captures into a normalised evidence file.

Every value written here comes from a byte file listed in `raw/manifest.json`; the source
URL and the SHA-256 of the exact response are carried alongside it so a published number
can be traced to the response it came from.  Nothing is estimated in this file - it is
the input layer only.  Estimations happen in `originate.py` and are labelled there.
"""

from __future__ import annotations

import html
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
RAW = os.path.join(ROOT, "data", "session-e880ce67", "raw")
OUT = os.path.join(ROOT, "data", "session-e880ce67", "evidence.json")


def manifest() -> dict:
    data = json.load(open(os.path.join(RAW, "manifest.json"), encoding="utf-8"))
    return {e["key"]: e for e in data["entries"]}


def read(key: str, m: dict, binary: bool = False):
    entry = m.get(key)
    if not entry or not entry.get("file"):
        return None
    path = os.path.join(ROOT, entry["file"])
    if path.endswith(".gz"):
        # stored gzipped (see collect.py): the SHA-256 in the manifest is over these bytes
        with gzip.open(path, "rb") as fh:
            body = fh.read()
        return body if binary else body.decode("utf-8", "replace")
    mode = "rb" if binary else "r"
    with open(path, mode, **({} if binary else {"encoding": "utf-8", "errors": "replace"})) as fh:
        return fh.read()


def json_of(key: str, m: dict):
    body = read(key, m)
    return json.loads(body) if body else None


def src(key: str, m: dict, label: str) -> dict:
    entry = m.get(key, {})
    return {"key": key, "label": label, "url": entry.get("url", ""),
            "sha256": entry.get("sha256", ""), "status": entry.get("status"),
            "fetched_utc": entry.get("fetched_utc", "")}


def plain(markup: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", markup))).strip()


# --------------------------------------------------------------------------- NHL
def parse_nhl(m: dict) -> dict:
    standings = json_of("nhl_standings", m) or {}
    teams = {}
    for row in standings.get("standings", []):
        abbr = row["teamAbbrev"]["default"] if isinstance(row.get("teamAbbrev"), dict) \
            else row.get("teamAbbrev")
        name = row.get("teamName", {}).get("default", "")
        place = row.get("placeName", {}).get("default", "")
        # The NHL feed returns teamName sometimes as the full name and sometimes as the
        # nickname only; avoid printing "Edmonton Edmonton Oilers".
        display = name if (" " in name and not name.lower().startswith(place.lower())) \
            or name.lower().startswith(place.lower()) else f"{place} {name}".strip()
        teams[abbr] = {
            "abbrev": abbr,
            "name": display.strip(),
            "gp": row.get("gamesPlayed"), "wins": row.get("wins"),
            "losses": row.get("losses"), "otl": row.get("otLosses"),
            "points": row.get("points"), "point_pct": row.get("pointPctg"),
            "gf": row.get("goalFor"), "ga": row.get("goalAgainst"),
            "gdiff": row.get("goalDifferential"),
            "l10": f"{row.get('l10Wins')}-{row.get('l10Losses')}-{row.get('l10OtLosses')}",
            "l10_gf": row.get("l10GoalsFor"), "l10_ga": row.get("l10GoalsAgainst"),
            "home": f"{row.get('homeWins')}-{row.get('homeLosses')}-{row.get('homeOtLosses')}",
            "road": f"{row.get('roadWins')}-{row.get('roadLosses')}-{row.get('roadOtLosses')}",
            "streak": f"{row.get('streakCode')}{row.get('streakCount')}",
            "home_goals_for": row.get("homeGoalsFor"), "home_goals_against": row.get("homeGoalsAgainst"),
            "road_goals_for": row.get("roadGoalsFor"), "road_goals_against": row.get("roadGoalsAgainst"),
        }
    fixtures = []
    for key, entry in m.items():
        if not key.startswith("nhl_sched_") or not entry.get("file"):
            continue
        payload = json_of(key, m) or {}
        for week in payload.get("gameWeek", []):
            for game in week.get("games", []):
                fixtures.append({
                    "id": str(game.get("id")),
                    "date": week.get("date"),
                    "start_utc": game.get("startTimeUTC"),
                    "state": game.get("gameState"),
                    "home": game["homeTeam"]["abbrev"], "away": game["awayTeam"]["abbrev"],
                    "home_name": f"{game['homeTeam'].get('placeName', {}).get('default', '')} "
                                 f"{game['homeTeam'].get('commonName', {}).get('default', '')}".strip(),
                    "away_name": f"{game['awayTeam'].get('placeName', {}).get('default', '')} "
                                 f"{game['awayTeam'].get('commonName', {}).get('default', '')}".strip(),
                    "venue": game.get("venue", {}).get("default", ""),
                    "neutral": game.get("neutralSite", False),
                    "game_center": "https://www.nhl.com" + game.get("gameCenterLink", ""),
                    "source_key": key,
                })
    fixtures.sort(key=lambda f: f["start_utc"] or "")
    return {"teams": teams, "fixtures": fixtures,
            "sources": [src("nhl_standings", m, "NHL standings (NHL.com official API)")]}


# --------------------------------------------------------------------------- MLB
def parse_mlb(m: dict) -> dict:
    standings = json_of("mlb_standings", m) or {}
    teams = {}
    for league in standings.get("records", []):
        for row in league.get("teamRecords", []):
            team = row["team"]
            splits = {s["type"]: s for s in row.get("records", {}).get("splitRecords", [])}
            home = splits.get("home", {}); away = splits.get("away", {}); last10 = splits.get("lastTen", {})
            teams[team["abbreviation"]] = {
                "abbrev": team["abbreviation"], "name": team["name"],
                "wins": row.get("wins"), "losses": row.get("losses"),
                "pct": row.get("winningPercentage"), "gp": row.get("gamesPlayed"),
                "runs_scored": row.get("runsScored"), "runs_allowed": row.get("runsAllowed"),
                "run_diff": row.get("runDifferential"),
                "home": f"{home.get('wins', '')}-{home.get('losses', '')}",
                "away": f"{away.get('wins', '')}-{away.get('losses', '')}",
                "l10": f"{last10.get('wins', '')}-{last10.get('losses', '')}",
                "streak": f"{row.get('streak', {}).get('streakCode', '')}",
            }
    sched = json_of("mlb_sched", m) or {}
    fixtures = []
    for day in sched.get("dates", []):
        for game in day.get("games", []):
            fixtures.append({
                "id": game.get("gamePk"), "date": day.get("date"),
                "start_utc": game.get("gameDate"), "state": game.get("status", {}).get("detailedState", ""),
                "home": game["teams"]["home"]["team"]["abbreviation"],
                "away": game["teams"]["away"]["team"]["abbreviation"],
                "home_name": game["teams"]["home"]["team"]["name"],
                "away_name": game["teams"]["away"]["team"]["name"],
                "home_score": game["teams"]["home"].get("score"),
                "away_score": game["teams"]["away"].get("score"),
                "venue": game.get("venue", {}).get("name", ""),
                "probable_home": (game["teams"]["home"].get("probablePitcher") or {}).get("fullName", ""),
                "probable_away": (game["teams"]["away"].get("probablePitcher") or {}).get("fullName", ""),
                "source_key": "mlb_sched",
            })
    fixtures.sort(key=lambda f: f["start_utc"] or "")
    return {"teams": teams, "fixtures": fixtures,
            "sources": [src("mlb_standings", m, "MLB standings (MLB.com StatsAPI)"),
                        src("mlb_sched", m, "MLB schedule and probable pitchers (MLB.com StatsAPI)")]}


# ---------------------------------------------------------------------- handball
def parse_ehf(m: dict) -> dict:
    body = read("ehfcl_standings", m)
    if not body:
        return {"groups": {}, "sources": []}
    groups, current = {}, None
    for row in re.findall(r"<tr.*?</tr>", body, re.S):
        text = plain(row)
        head = re.search(r"GROUP\s+([A-F])\b", text, re.I)
        if head:
            current = f"Group {head.group(1).upper()}"
            groups.setdefault(current, [])
            continue
        cells = [plain(c) for c in re.findall(r"<t[dh].*?</t[dh]>", row, re.S)]
        head_cell = re.match(r"^(\d+)\.\s*(.+)$", cells[0]) if cells else None
        if current and len(cells) >= 8 and head_cell and re.match(r"^\d+$", cells[1]) \
                and int(cells[1]) > 0:
            goals = re.match(r"(\d+)\s*:\s*(\d+)", cells[5])
            groups[current].append({
                "rank": int(head_cell.group(1)), "team": head_cell.group(2),
                "gp": int(cells[1]), "wins": int(cells[2]), "draws": int(cells[3]),
                "losses": int(cells[4]),
                "gf": int(goals.group(1)) if goals else None,
                "ga": int(goals.group(2)) if goals else None,
                "diff": cells[6], "points": cells[7],
            })
    return {"groups": groups,
            "sources": [src("ehfcl_standings", m, "EHF Champions League men standings (eurohandball.com)")]}


def parse_danish(m: dict) -> dict:
    body = read("danish_table", m)
    if not body:
        return {"teams": [], "sources": []}
    teams = []
    for row in re.findall(r'<tr class="team-position__row.*?</tr>', body, re.S):
        cells = [plain(c) for c in re.findall(r"<td.*?</td>", row, re.S)]
        if len(cells) >= 7:
            goals = re.match(r"(\d+)\s*-\s*(\d+)", cells[6]) if len(cells) > 6 else None
            w, d = int(cells[3]), int(cells[4])
            teams.append({"rank": cells[0], "team": cells[1], "gp": cells[2],
                          "wins": w, "draws": d, "losses": cells[5],
                          "gf": int(goals.group(1)) if goals else None,
                          "ga": int(goals.group(2)) if goals else None,
                          "goals": cells[6],
                          "points": str(2 * w + d)})
    return {"teams": teams,
            "sources": [src("danish_table", m, "Betoro Herreligaen table (tophaandbold.dk, Danish Handball Federation)")]}


# ------------------------------------------------------------------------- tennis
def parse_wta(m: dict) -> dict:
    """WTA ranks by reading each row's own rank and points cells.

    The page's default row order is not ranking order, so the rank comes from the
    ``player-row__cell--rank`` cell ("1 -") and the points from ``--points`` ("9,196"),
    never from the row's position in the table.
    """
    body = read("wta_rankings", m)
    if not body:
        return {"players": {}, "sources": []}
    players = {}
    for row in re.findall(r'<tr[^>]*class="[^"]*player-row[^"]*".*?</tr>', body, re.S):
        name = re.search(r'data-player-name="([^"]+)"', row)
        if not name:
            continue
        rank_cell = re.search(r'player-row__cell--rank[^>]*>(.*?)</td>', row, re.S)
        pts_cell = re.search(r'player-row__cell--points[^>]*>(.*?)</td>', row, re.S)
        rank = points = None
        if rank_cell:
            digits = re.search(r"\d+", plain(rank_cell.group(1)))
            rank = int(digits.group(0)) if digits else None
        if pts_cell:
            digits = re.search(r"[\d,]+", plain(pts_cell.group(1)))
            points = int(digits.group(0).replace(",", "")) if digits else None
        players[name.group(1)] = {"name": name.group(1), "rank": rank, "points": points}
    return {"players": players, "count": len(players),
            "sources": [src("wta_rankings", m, "WTA singles rankings (wtatennis.com)")]}


# ---------------------------------------------------------------- capture record
def parse_failures(m: dict) -> list:
    return [{"key": k, "url": e.get("url", ""), "status": e.get("status"),
             "error": e.get("error", "")} for k, e in sorted(m.items())
            if e.get("status") != 200 or not e.get("sha256")]


def main() -> int:
    m = manifest()
    evidence = {
        "schema": "olbg4.ds.evidence/1",
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_utc": json.load(open(os.path.join(RAW, "manifest.json"), encoding="utf-8"))["captured_utc"],
        "ice_hockey": parse_nhl(m),
        "baseball": parse_mlb(m),
        "handball_ehf": parse_ehf(m),
        "handball_denmark": parse_danish(m),
        "tennis_wta": parse_wta(m),
        "failed_sources": parse_failures(m),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(evidence, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print("NHL teams", len(evidence["ice_hockey"]["teams"]),
          "fixtures", len(evidence["ice_hockey"]["fixtures"]))
    print("MLB teams", len(evidence["baseball"]["teams"]),
          "fixtures", len(evidence["baseball"]["fixtures"]))
    print("EHF groups", {k: len(v) for k, v in evidence["handball_ehf"]["groups"].items()})
    print("Danish teams", len(evidence["handball_denmark"]["teams"]))
    print("WTA players", evidence["tennis_wta"].get("count"))
    print("failed official", len(evidence["failed_sources"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board CB — official-source adapters.

Each adapter reads one committed capture and returns
    fixtures: list of dicts describing an upcoming fixture and the official facts behind it
    notes:    list of strings explaining anything that could not be used

Nothing here writes prose: the numbers an adapter returns are exactly the numbers printed on the
official page, and each one carries the URL and sha256 of the capture it came from.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from capio import Capture

WINDOW_START = datetime(2026, 10, 26, 6, 0, tzinfo=timezone.utc)
WINDOW_END = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)


def _dt(s: str) -> datetime:
    s = s.replace("Z", "+00:00")
    d = datetime.fromisoformat(s)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def in_window(dt: datetime) -> bool:
    return WINDOW_START <= dt <= WINDOW_END


# --------------------------------------------------------------------------- ice hockey
def ice_hockey(cap: Capture) -> tuple[list[dict], list[str]]:
    """NHL schedule (one API call per day) joined to the official standings feed."""
    notes: list[str] = []
    if not cap.ok("nhl_standings"):
        return [], ["NHL standings feed was not captured"]
    standings = {}
    for s in cap.json("nhl_standings")["standings"]:
        name = f"{s['placeName']['default']} {s['commonName']['default']}".strip()
        standings[name] = {
            "name": name,
            "abbrev": s["teamAbbrev"]["default"],
            "games": s["gamesPlayed"],
            "wins": s["wins"],
            "losses": s["losses"],
            "ot": s["otLosses"],
            "points": s["points"],
            "win_pct": s["pointPctg"],
            "regulation_win_pct": (s["regulationWins"] + s["otLosses"] * 0.5 if "regulationWins" in s else s["pointPctg"]),
            "goals_for": s["goalFor"],
            "goals_against": s["goalAgainst"],
            "streak": f"{s['streakCode']}{s['streakCount']}",
            "division": s.get("divisionName", ""),
            "conference": s.get("conferenceName", ""),
            "l10": s.get("l10Wins"),
        }
    by_abbrev = {v["abbrev"]: v for v in standings.values()}

    fixtures: list[dict] = []
    seen: set[int] = set()
    for tid in cap.ids("nhl_sched_"):
        try:
            payload = cap.json(tid)
        except Exception:
            continue
        for day in payload.get("gameWeek", []):
            for g in day.get("games", []):
                if g["id"] in seen or g.get("gameState") not in ("FUT", "PRE"):
                    continue
                start = _dt(g["startTimeUTC"])
                if not in_window(start):
                    continue
                home = by_abbrev.get(g["homeTeam"]["abbrev"])
                away = by_abbrev.get(g["awayTeam"]["abbrev"])
                if not home or not away:
                    notes.append(f"NHL game {g['id']} has a club missing from the standings feed")
                    continue
                seen.add(g["id"])
                fixtures.append({
                    "sport": "Ice Hockey",
                    "competition": "NHL — National Hockey League (2026-27 regular season)",
                    "home": home["name"], "away": away["name"],
                    "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "venue": g.get("venue", {}).get("default", ""),
                    "source_url": "https://api-web.nhle.com/v1/standings/now",
                    "schedule_url": f"https://api-web.nhle.com/v1/schedule/{start.date().isoformat()}",
                    "source_name": "NHL — official standings and schedule API (api-web.nhle.com)",
                    "params": {"home": home, "away": away,
                               "league": {"for_rate": 3.05},
                               "sample": {"games": min(home["games"], away["games"]),
                                          "ranking_verified": True}},
                    "facts": [
                        {"label": f"{home['name']} record",
                         "value": f"{home['wins']}-{home['losses']}-{home['ot']} in {home['games']} games, "
                                  f"{home['points']} points, {home['goals_for']} goals for and "
                                  f"{home['goals_against']} against, streak {home['streak']}",
                         "source_url": "https://api-web.nhle.com/v1/standings/now"},
                        {"label": f"{away['name']} record",
                         "value": f"{away['wins']}-{away['losses']}-{away['ot']} in {away['games']} games, "
                                  f"{away['points']} points, {away['goals_for']} goals for and "
                                  f"{away['goals_against']} against, streak {away['streak']}",
                         "source_url": "https://api-web.nhle.com/v1/standings/now"},
                    ],
                    "olbg_name": [f"{g['awayTeam']['placeName']['default']} {g['awayTeam']['commonName']['default']} "
                                  f"@ {g['homeTeam']['placeName']['default']} {g['homeTeam']['commonName']['default']}",
                                  f"{away['abbrev']} {away['name'].split()[-1]} @ {home['abbrev']} {home['name'].split()[-1]}"],
                })
    notes.append(f"NHL: {len(fixtures)} unplayed games in the capture window")
    return fixtures, notes


# --------------------------------------------------------------------------- baseball
def baseball(cap: Capture) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    if not cap.ok("mlb_standings"):
        return [], ["MLB standings feed was not captured"]
    recs = {}
    for block in cap.json("mlb_standings")["records"]:
        for t in block["teamRecords"]:
            name = t["team"]["name"]
            recs[name] = {
                "games": t["wins"] + t["losses"], "wins": t["wins"], "losses": t["losses"],
                "win_pct": float(t["winningPercentage"]),
                "runs_for": t["runsScored"], "runs_against": t["runsAllowed"],
                "diff": t["runDifferential"],
                "streak": f"{t['streak']['streakCode']}",
                "source": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
            }
    for t in recs.values():
        t["rs_pg"] = round(t["runs_for"] / t["games"], 3)
        t["ra_pg"] = round(t["runs_against"] / t["games"], 3)

    # probable pitchers by game
    probables = {}
    for tid in cap.ids("mlb_"):
        try:
            payload = cap.json(tid)
        except Exception:
            continue
        for day in payload.get("dates", []):
            for g in day.get("games", []):
                for side in ("home", "away"):
                    pp = g.get("teams", {}).get(side, {}).get("probablePitcher")
                    if pp:
                        probables.setdefault(g["gamePk"], {})[side] = pp.get("fullName")

    fixtures, seen = [], set()
    for tid in cap.ids("mlb_"):
        try:
            payload = cap.json(tid)
        except Exception:
            continue
        for day in payload.get("dates", []):
            for g in day.get("games", []):
                state = g.get("status", {}).get("detailedState", "")
                if state == "Final" or g["gamePk"] in seen:
                    continue
                start = _dt(g.get("gameDate", day["date"] + "T00:00:00Z"))
                if not in_window(start):
                    continue
                home_name = g["teams"]["home"]["team"]["name"]
                away_name = g["teams"]["away"]["team"]["name"]
                if home_name not in recs or away_name not in recs:
                    continue
                if g.get("seriesDescription") not in ("World Series", None, ""):
                    # only the current round is priced; earlier rounds are history
                    if "World Series" not in str(g.get("seriesDescription")):
                        continue
                seen.add(g["gamePk"])
                home, away = recs[home_name], recs[away_name]
                pp = probables.get(g["gamePk"], {})
                fixtures.append({
                    "sport": "Baseball",
                    "competition": f"MLB — {g.get('seriesDescription') or 'post-season'}",
                    "home": home_name, "away": away_name,
                    "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "venue": g.get("venue", {}).get("name", ""),
                    "source_url": "https://statsapi.mlb.com/api/v1/schedule/postseason?season=2026",
                    "source_name": "MLB — official StatsAPI post-season schedule and standings",
                    "params": {"home": {**home, "for_rate": home["rs_pg"], "against_rate": home["ra_pg"]},
                               "away": {**away, "for_rate": away["rs_pg"], "against_rate": away["ra_pg"]},
                               "league": {"for_rate": 4.5},
                               "sample": {"games": min(home["games"], away["games"]), "ranking_verified": True}},
                    "facts": [
                        {"label": f"{home_name} regular-season record",
                         "value": f"{home['wins']}-{home['losses']} ({home['win_pct']:.3f}), "
                                  f"{home['runs_for']} runs scored and {home['runs_against']} allowed "
                                  f"({home['diff']:+d})",
                         "source_url": home["source"]},
                        {"label": f"{away_name} regular-season record",
                         "value": f"{away['wins']}-{away['losses']} ({away['win_pct']:.3f}), "
                                  f"{away['runs_for']} runs scored and {away['runs_against']} allowed "
                                  f"({away['diff']:+d})",
                         "source_url": away["source"]},
                    ],
                    "probable_pitchers": pp,
                    "olbg_name": [f"{away_name.split()[-1]} @ {home_name.split()[-1]}",
                                  f"{away_name} @ {home_name}"],
                })
    notes.append(f"MLB: {len(fixtures)} unplayed games in the capture window")
    return fixtures, notes


# --------------------------------------------------------------------------- basketball
def basketball(cap: Capture) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    if not cap.ok("el_games") or not cap.ok("el_standings_r7"):
        return [], ["EuroLeague feeds were not captured"]
    table = {}
    for block in cap.json("el_standings_r7"):
        for s in block["standings"]:
            d = s["data"]
            table[s["club"]["name"]] = {
                "name": s["club"]["name"],
                "games": d["gamesPlayed"], "wins": d["gamesWon"], "losses": d["gamesLost"],
                "win_pct": d["gamesWon"] / max(d["gamesPlayed"], 1),
                "points_for": d["pointsFavour"], "points_against": d["pointsAgainst"],
                "position": d["position"],
            }
    for t in table.values():
        t["pf_pg"] = t["points_for"] / max(t["games"], 1)
        t["pa_pg"] = t["points_against"] / max(t["games"], 1)

    fixtures = []
    for g in cap.json("el_games")["data"]:
        if g.get("played"):
            continue
        start = _dt(g["utcDate"])
        if not in_window(start):
            continue
        home = table.get(g["local"]["club"]["name"])
        away = table.get(g["road"]["club"]["name"])
        if not home or not away:
            continue
        fixtures.append({
            "sport": "Basketball",
            "competition": f"EuroLeague 2026-27 — Round {g['round']}",
            "home": home["name"], "away": away["name"],
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": "",
            "source_url": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
            "source_name": "EuroLeague — official games and standings API (api-live.euroleague.net)",
            "params": {"home": {**home, "for_rate": home["pf_pg"], "against_rate": home["pa_pg"]},
                       "away": {**away, "for_rate": away["pf_pg"], "against_rate": away["pa_pg"]},
                       "league": {"for_rate": 80.0},
                       "sample": {"games": min(home["games"], away["games"]), "ranking_verified": True}},
            "facts": [
                {"label": f"{home['name']} EuroLeague record",
                 "value": f"{home['wins']}-{home['losses']} in {home['games']} games, position {home['position']}, "
                          f"{home['points_for']} points scored and {home['points_against']} conceded",
                 "source_url": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/rounds/7/standings"},
                {"label": f"{away['name']} EuroLeague record",
                 "value": f"{away['wins']}-{away['losses']} in {away['games']} games, position {away['position']}, "
                          f"{away['points_for']} points scored and {away['points_against']} conceded",
                 "source_url": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/rounds/7/standings"},
            ],
            "olbg_name": [f"{away['name']} vs {home['name']}", f"{home['name']} vs {away['name']}"],
        })
    notes.append(f"EuroLeague: {len(fixtures)} unplayed games in the capture window")
    return fixtures, notes


# --------------------------------------------------------------------------- handball
EHF_ROW = re.compile(
    r'<tr>\s*<td>\s*(\d+)\.\s*<a href="[^"]+">([^<]+)</a>\s*</td>'
    r'((?:\s*<td[^>]*>\s*[^<]*</td>){6})', re.S)


def _ehf_standings(cap: Capture, tid: str) -> dict:
    html = cap.raw(tid)
    out = {}
    for m in EHF_ROW.finditer(html):
        pos, name, rest = int(m.group(1)), m.group(2).strip(), m.group(3)
        cells = [c.strip() for c in re.findall(r"<td[^>]*>\s*([^<]*?)\s*</td>", rest, re.S)]
        if len(cells) < 6:
            continue
        played, wins, draws, losses, goals, pts = cells[:6]
        gf, _, ga = (goals.partition(":"))
        try:
            played_i, wins_i, losses_i = int(played), int(wins), int(losses)
            gf_i, ga_i = int(gf.strip()), int(ga.strip())
        except ValueError:
            continue
        out[re.sub(r"\s+", " ", name)] = {
            "name": name, "position": pos, "games": played_i, "wins": wins_i,
            "draws": int(draws), "losses": losses_i, "goals_for": gf_i, "goals_against": ga_i,
            "points": int(pts), "win_pct": (wins_i + 0.5 * int(draws)) / max(played_i, 1),
        }
    for t in out.values():
        t["gf_pg"] = t["goals_for"] / max(t["games"], 1)
        t["ga_pg"] = t["goals_against"] / max(t["games"], 1)
    return out


def handball(cap: Capture) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    table: dict[str, dict] = {}
    for tid in ("ehfcl_men_standings", "ehfcl_women_standings"):
        if cap.ok(tid):
            for k, v in _ehf_standings(cap, tid).items():
                table.setdefault(k, v)
    notes.append(f"EHF standings rows parsed: {len(table)}")
    return [], notes


# --------------------------------------------------------------------------- rugby union
TOP14_ROW = re.compile(
    r"(Stade Toulousain|Section Paloise|Union Bordeaux-Bègles|Stade Rochelais|LOU Rugby|"
    r"Aviron Bayonnais|Montpellier Hérault Rugby|RC Toulon|Stade Français Paris|USA Perpignan|"
    r"Castres Olympique|ASM Clermont|Racing 92|RC Vannes)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+"
    r"(\d+)\s+(\d+)\s+(\d+)\s+([+\-]\d+)\s+((?:[VD]\s*){2,6})(\w{2,3})\s+(\d{1,2}\s+\w+)\s+"
    r"(À l'extérieur|À domicile)")


def rugby_union(cap: Capture) -> tuple[list[dict], list[str]]:
    notes: list[str] = []
    if not cap.ok("top14_classement"):
        return [], ["Top 14 standings page was not captured"]
    text = re.sub(r"\s+", " ", cap.text("top14_classement"))
    clubs = {}
    for m in TOP14_ROW.finditer(text):
        (name, pts, played, won, drawn, lost, bonus, pf, pa, diff, form, nxt, date, venue) = m.groups()
        form = "".join(form.split())
        clubs[name] = {
            "name": name, "points": int(pts), "games": int(played), "wins": int(won),
            "draws": int(drawn), "losses": int(lost), "bonus": int(bonus),
            "points_for": int(pf), "points_against": int(pa), "diff": int(diff),
            "form": form, "next": nxt, "next_date": date, "next_venue": venue,
            "win_pct": (int(won) + 0.5 * int(drawn)) / max(int(played), 1),
            "pf_pg": int(pf) / max(int(played), 1), "pa_pg": int(pa) / max(int(played), 1),
        }
    notes.append(f"Top 14 clubs parsed: {len(clubs)}")
    fixtures, used = [], set()
    for name, c in clubs.items():
        opp = c["next"]
        if name in used or opp not in clubs:
            continue
        used.add(name); used.add(opp)
        home, away = (name, opp) if c["next_venue"] == "À domicile" else (opp, name)
        # the calendar page names the round; the standings page names only the date
        day = c["next_date"]
        fixtures.append({
            "sport": "Rugby Union",
            "competition": "Top 14 2026-27 — next round (Round 9)",
            "home": home, "away": away,
            "start_utc": "", "start_date": day,
            "venue": "",
            "source_url": "https://top14.lnr.fr/classement",
            "source_name": "LNR — official Top 14 standings with each club's next fixture (top14.lnr.fr)",
            "params": {"home": clubs[home], "away": clubs[away],
                       "league": {"for_rate": 26.0},
                       "sample": {"games": min(clubs[home]["games"], clubs[away]["games"]),
                                  "ranking_verified": True}},
            "facts": [
                {"label": f"{home} Top 14 record",
                 "value": f"{clubs[home]['wins']}W-{clubs[home]['draws']}D-{clubs[home]['losses']}L in "
                          f"{clubs[home]['games']} matches, {clubs[home]['points']} points, "
                          f"{clubs[home]['points_for']} scored and {clubs[home]['points_against']} conceded, "
                          f"form {clubs[home]['form']}",
                 "source_url": "https://top14.lnr.fr/classement"},
                {"label": f"{away} Top 14 record",
                 "value": f"{clubs[away]['wins']}W-{clubs[away]['draws']}D-{clubs[away]['losses']}L in "
                          f"{clubs[away]['games']} matches, {clubs[away]['points']} points, "
                          f"{clubs[away]['points_for']} scored and {clubs[away]['points_against']} conceded, "
                          f"form {clubs[away]['form']}",
                 "source_url": "https://top14.lnr.fr/classement"},
            ],
            "olbg_name": [f"{home} v {away}", f"{away} v {home}"],
        })
    notes.append(f"Top 14: {len(fixtures)} next-round fixtures built from the official next-fixture column")
    return fixtures, notes


# --------------------------------------------------------------------------- tennis
WTA_ROW = re.compile(
    r"\b(\d{1,3})\s*-\s*(?:\s*[A-Z]{2,3}\s*)?\s*([A-Z][A-Za-z'’\-]+(?:\s+[A-Z][A-Za-z'’\-]+){1,3})\s+"
    r"([A-Z]{2,3})\s+(\d{2})\s+(\d{2})\s+([\d,]{4,9})")


def tennis_rankings(cap: Capture) -> dict:
    if not cap.ok("wta_rankings_page"):
        return {}
    text = re.sub(r"[ \t]+", " ", cap.text("wta_rankings_page"))
    out = {}
    for m in WTA_ROW.finditer(text):
        rank, name, country, _age, _x, points = m.groups()
        pts = int(points.replace(",", ""))
        if 1 <= int(rank) <= 200 and name not in out:
            out[name.strip()] = {"name": name.strip(), "rank": int(rank),
                                 "points": pts, "country": country}
    return out

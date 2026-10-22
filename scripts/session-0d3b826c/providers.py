#!/usr/bin/env python3
"""Official-feed fixture providers for Board AF.

A provider may confirm a fixture but still decline to price it.  Absence of
numeric evidence is a valid, published outcome.  Names, starts, venues, form and
recent results below are read directly from the captured official payloads.
"""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any

from common import DATA, Capture, in_window, iso_z, load, norm, price
from model import (attach_pick, basketball_markets, investigated, moneyline_only,
                   normal_cdf, score_grid, scoring_markets, two_way)

SOURCE_NAMES = {
    "nhl": "National Hockey League official web API",
    "liiga": "Finnish Liiga official API",
    "euroleague": "EuroLeague Basketball official games feed",
    "eurocup": "EuroCup Basketball official games feed",
    "mlb": "Major League Baseball official Stats API",
    "wta": "Women's Tennis Association official tournament and rankings API",
    "lol": "Riot Games LoL Esports official schedule API",
}


def base_row(cap: Capture, row_id: str, provider: str, sport: str, competition: str,
             side_a: str, side_b: str, start: str, venue: str,
             source_ids: list[str]) -> dict[str, Any]:
    evidence = cap.evidence(*source_ids)
    return {
        "id": row_id,
        "provider": provider,
        "sport": sport,
        "competition": competition,
        "side_a": side_a,
        "side_b": side_b,
        "start_utc": start,
        "venue": venue,
        "verification": "Official fixture confirmed from captured bytes",
        "official_url": evidence[0]["url"],
        "official_source_name": SOURCE_NAMES[provider],
        "evidence": evidence,
        "form": {},
        "recent_results": [],
        "player_facts": [],
        "inputs": {},
        "aliases_a": [side_a],
        "aliases_b": [side_b],
        "markets": {},
        "model": None,
        "pick": None,
        "prediction": None,
        "flags": ([{"code": "VENUE_UNCONFIRMED",
                    "reason": "The captured official payload does not confirm a venue; the venue field is intentionally blank."}] if not venue else []),
        "olbg_listing_id": "",
        "olbg_url": "",
    }


def tag_team(records: list[dict[str, str]], team: str) -> list[dict[str, str]]:
    return [{**record, "team": team} for record in records]


def unpriced(row: dict[str, Any], reason: str) -> dict[str, Any]:
    row["flags"].append({"code": "UNPRICED", "reason": reason})
    row["markets"] = {}
    row["pick"] = None
    row["model"] = {"name": "Not originated", "reason": reason}
    row["investigated_markets"] = investigated(row["sport"], [], reason)
    return row


def latest_by_team(games: list[dict[str, Any]], team_keys: dict[str, str],
                   cutoff: str, source_id: str, url: str) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for game in sorted(games, key=lambda g: g.get("start", ""), reverse=True):
        if not game.get("start") or game["start"] >= cutoff:
            continue
        for side in ("a", "b"):
            key = game.get(f"{side}_key", "")
            if not key or key not in team_keys or result[key]:
                continue
            result[key].append({
                "text": game["text"],
                "date": game["start"][:10],
                "source_id": source_id,
                "url": url,
            })
    return result


def nhl(cap: Capture) -> list[dict[str, Any]]:
    standings_id = "nhl_standings_now" if cap.usable("nhl_standings_now") else "nhl_standings_2026_10_22"
    standings_doc = cap.json(standings_id)
    stats = {s["teamAbbrev"]["default"]: s for s in standings_doc["standings"]}
    league_avg = sum(s["goalFor"] for s in stats.values()) / sum(s["gamesPlayed"] for s in stats.values())

    leaders = cap.json("nhl_skater_leaders")
    player_by_team: dict[str, dict[str, Any]] = {}
    for category in ("points", "goals"):
        for player in leaders.get(category, []):
            player_by_team.setdefault(player["teamAbbrev"], {
                "name": f"{player['firstName']['default']} {player['lastName']['default']}",
                "text": f"{player['firstName']['default']} {player['lastName']['default']} — {player['value']} {category} in the official current-season leaders snapshot",
                "source_id": "nhl_skater_leaders",
                "url": cap.url("nhl_skater_leaders"),
            })

    recent_by_team: dict[str, list[dict[str, str]]] = defaultdict(list)
    for source_id in ("nhl_score_2026_10_22", "nhl_score_2026_10_21", "nhl_score_2026_10_20", "nhl_score_2026_10_19", "nhl_score_2026_10_18"):
        if not cap.usable(source_id):
            continue
        for game in cap.json(source_id).get("games", []):
            away, home = game.get("awayTeam", {}), game.get("homeTeam", {})
            if ("score" not in away or "score" not in home or iso_z(game["startTimeUTC"]) >= cap.cutoff
                    or game.get("gameState") not in ("OFF", "FINAL")):
                continue
            away_name = (stats.get(away.get("abbrev"), {}).get("teamName", {}).get("default")
                         or away.get("name", {}).get("default") or away.get("abbrev") or "")
            home_name = (stats.get(home.get("abbrev"), {}).get("teamName", {}).get("default")
                         or home.get("name", {}).get("default") or home.get("abbrev") or "")
            if not away_name or not home_name:
                continue
            for team in (away, home):
                abbr = team.get("abbrev")
                if not recent_by_team[abbr]:
                    recent_by_team[abbr].append({
                        "text": f"{away_name} {away['score']}–{home['score']} {home_name} (final)",
                        "date": game.get("gameDate") or iso_z(game["startTimeUTC"])[:10],
                        "source_id": source_id,
                        "url": cap.url(source_id),
                    })

    games: dict[int, tuple[str, dict[str, Any]]] = {}
    for source_id in ("nhl_sched_2026_10_22", "nhl_sched_2026_10_29"):
        for day in cap.json(source_id).get("gameWeek", []):
            for game in day.get("games", []):
                games.setdefault(game["id"], (source_id, game))
    rows = []
    for game_id, (schedule_id, game) in sorted(games.items()):
        start = iso_z(game["startTimeUTC"])
        if not in_window(start, cap.cutoff):
            continue
        away_raw, home_raw = game["awayTeam"], game["homeTeam"]
        away_abbr, home_abbr = away_raw["abbrev"], home_raw["abbrev"]
        if away_abbr not in stats or home_abbr not in stats:
            continue
        away_name = f"{away_raw['placeName']['default']} {away_raw['commonName']['default']}"
        home_name = f"{home_raw['placeName']['default']} {home_raw['commonName']['default']}"
        source_ids = [schedule_id, standings_id, "nhl_skater_leaders"]
        for rec in recent_by_team.get(away_abbr, []) + recent_by_team.get(home_abbr, []):
            if rec["source_id"] not in source_ids:
                source_ids.append(rec["source_id"])
        row = base_row(cap, f"nhl-{game_id}", "nhl", "Ice Hockey", "NHL Regular Season",
                       home_name, away_name, start, game.get("venue", {}).get("default", ""), source_ids)
        # base_row uses side_a=home for scoring providers.
        a, b = stats[home_abbr], stats[away_abbr]
        for side, team, abbr in (("side_a", a, home_abbr), ("side_b", b, away_abbr)):
            row["form"][side] = {
                "text": f"{team['wins']}-{team['losses']}-{team['otLosses']}, {team['goalFor']} GF / {team['goalAgainst']} GA in {team['gamesPlayed']} games; last 10: {team['l10Wins']}-{team['l10Losses']}-{team['l10OtLosses']}",
                "games": team["gamesPlayed"], "wins": team["wins"], "losses": team["losses"],
                "ot_losses": team["otLosses"], "goals_for": team["goalFor"], "goals_against": team["goalAgainst"],
            }
            if abbr in player_by_team:
                row["player_facts"].append({**player_by_team[abbr], "team": row[side] if side in row else ""})
        row["recent_results"] = (tag_team(recent_by_team.get(home_abbr, []), home_name)
                                 + tag_team(recent_by_team.get(away_abbr, []), away_name))
        row["aliases_a"] = [home_name, home_raw["commonName"]["default"]]
        row["aliases_b"] = [away_name, away_raw["commonName"]["default"]]
        shrink = 8.0
        home_attack = (a["goalFor"] + shrink * league_avg) / (a["gamesPlayed"] + shrink)
        home_defence = (a["goalAgainst"] + shrink * league_avg) / (a["gamesPlayed"] + shrink)
        away_attack = (b["goalFor"] + shrink * league_avg) / (b["gamesPlayed"] + shrink)
        away_defence = (b["goalAgainst"] + shrink * league_avg) / (b["gamesPlayed"] + shrink)
        home_lambda = home_attack * away_defence / league_avg * 1.04
        away_lambda = away_attack * home_defence / league_avg / 1.04
        grid = score_grid(home_lambda, away_lambda)
        p_home = sum(p for h, aw, p in grid if h > aw) + 0.5 * sum(p for h, aw, p in grid if h == aw)
        row["markets"] = scoring_markets(home_name, away_name, home_lambda, away_lambda, p_home,
                                         "Puck Line (regulation margin)", "Match Total Goals")
        row["inputs"] = {"league_goals_per_team_game": round(league_avg, 6),
                         "home_expected_goals": round(home_lambda, 6), "away_expected_goals": round(away_lambda, 6)}
        row["model"] = {"name": "Shrunk independent-Poisson goals", "shrinkage_games": 8,
                        "home_multiplier": 1.04,
                        "assumptions": ["Team GF/GA rates shrink toward the current NHL mean over eight pseudo-games.",
                                        "Regulation ties are split equally for the including-overtime match-winner estimate.",
                                        "The puck line uses regulation margin; overtime wins cannot cover -1.5.",
                                        "No goalie, injury, rest or travel adjustment is applied."]}
        row["investigated_markets"] = investigated("Ice Hockey", ["Match Winner", "Handicap", "Match Total"])
        attach_pick(row, min(a["gamesPlayed"], b["gamesPlayed"]) >= 8)
        rows.append(row)
    return rows


def liiga(cap: Capture) -> list[dict[str, Any]]:
    games = cap.json("liiga_games_2027")
    standings = cap.json("liiga_standings_2027")["season"]
    stats = {s["teamId"]: s for s in standings}
    league_avg = sum(s["goals"] for s in stats.values()) / sum(s["games"] for s in stats.values())
    recent: dict[str, list[dict[str, str]]] = defaultdict(list)
    scorer: dict[str, dict[str, str]] = {}
    for game in sorted(games, key=lambda g: g.get("start", ""), reverse=True):
        if not game.get("ended") or not game.get("start") or game["start"] >= cap.cutoff:
            continue
        home, away = game["homeTeam"], game["awayTeam"]
        text = f"{home['teamName']} {home['goals']}–{away['goals']} {away['teamName']} (final)"
        for team, opponent_goals in ((home, away["goals"]), (away, home["goals"])):
            team_id = team["teamId"]
            if not recent[team_id]:
                recent[team_id].append({"text": text, "date": game["start"][:10],
                                        "source_id": "liiga_games_2027", "url": cap.url("liiga_games_2027")})
            if team_id not in scorer:
                for event in team.get("goalEvents", []):
                    player = event.get("scorerPlayer") or {}
                    if player.get("firstName") and player.get("lastName"):
                        name = f"{player['firstName']} {player['lastName']}"
                        scorer[team_id] = {"name": name,
                                           "text": f"{name} is listed as a scorer for {team['teamName']} in {text}",
                                           "source_id": "liiga_games_2027", "url": cap.url("liiga_games_2027")}
                        break
    rows = []
    for game in games:
        start = game.get("start", "")
        if not in_window(start, cap.cutoff) or game.get("ended"):
            continue
        home, away = game["homeTeam"], game["awayTeam"]
        a, b = stats.get(home["teamId"]), stats.get(away["teamId"])
        if not a or not b:
            continue
        row = base_row(cap, f"liiga-{game['id']}", "liiga", "Ice Hockey", "Finnish Liiga — Regular Season",
                       home["teamName"], away["teamName"], start,
                       (game.get("iceRink") or {}).get("name", ""), ["liiga_games_2027", "liiga_standings_2027"])
        for side, team in (("side_a", a), ("side_b", b)):
            row["form"][side] = {"text": f"{team['points']} points in {team['games']} games, {team['goals']} GF / {team['goalsAgainst']} GA",
                                 "games": team["games"], "points": team["points"],
                                 "goals_for": team["goals"], "goals_against": team["goalsAgainst"]}
        row["recent_results"] = (tag_team(recent.get(home["teamId"], []), home["teamName"])
                                 + tag_team(recent.get(away["teamId"], []), away["teamName"]))
        for team_id, team_name in ((home["teamId"], home["teamName"]), (away["teamId"], away["teamName"])):
            if team_id in scorer:
                row["player_facts"].append({**scorer[team_id], "team": team_name})
        shrink = 8.0
        home_attack = (a["goals"] + shrink * league_avg) / (a["games"] + shrink)
        home_defence = (a["goalsAgainst"] + shrink * league_avg) / (a["games"] + shrink)
        away_attack = (b["goals"] + shrink * league_avg) / (b["games"] + shrink)
        away_defence = (b["goalsAgainst"] + shrink * league_avg) / (b["games"] + shrink)
        home_lambda = home_attack * away_defence / league_avg * 1.04
        away_lambda = away_attack * home_defence / league_avg / 1.04
        grid = score_grid(home_lambda, away_lambda)
        p_home = sum(p for h, aw, p in grid if h > aw) + 0.5 * sum(p for h, aw, p in grid if h == aw)
        row["markets"] = scoring_markets(home["teamName"], away["teamName"], home_lambda, away_lambda,
                                         p_home, "Puck Line (regulation margin)", "Match Total Goals")
        row["inputs"] = {"league_goals_per_team_game": round(league_avg, 6),
                         "home_expected_goals": round(home_lambda, 6), "away_expected_goals": round(away_lambda, 6)}
        row["model"] = {"name": "Shrunk independent-Poisson goals", "shrinkage_games": 8,
                        "home_multiplier": 1.04,
                        "assumptions": ["Official Liiga table GF/GA rates shrink toward the league mean over eight pseudo-games.",
                                        "Regulation ties are split equally for the including-overtime match-winner estimate.",
                                        "Bookmaker fields embedded in the Liiga payload are ignored.",
                                        "No goalie, injury, rest or travel adjustment is applied."]}
        row["investigated_markets"] = investigated("Ice Hockey", ["Match Winner", "Handicap", "Match Total"])
        attach_pick(row, min(a["games"], b["games"]) >= 8)
        rows.append(row)
    return rows


def basketball_feed(cap: Capture, source_id: str, provider: str, competition: str) -> list[dict[str, Any]]:
    games = cap.json(source_id)["data"]
    stats: dict[str, dict[str, Any]] = defaultdict(lambda: {"games": 0, "wins": 0, "pf": 0, "pa": 0, "name": ""})
    margins, totals = [], []
    recent: dict[str, list[dict[str, str]]] = defaultdict(list)
    for game in sorted(games, key=lambda item: item.get("utcDate", ""), reverse=True):
        if not game.get("played") or not game.get("utcDate") or game["utcDate"] >= cap.cutoff:
            continue
        home, away = game["local"], game["road"]
        hs, aws = home.get("score", 0), away.get("score", 0)
        if not isinstance(hs, int) or not isinstance(aws, int) or hs + aws <= 0:
            continue
        hc, ac = home["club"]["code"], away["club"]["code"]
        for code, club, pf, pa, won in ((hc, home["club"], hs, aws, hs > aws),
                                        (ac, away["club"], aws, hs, aws > hs)):
            s = stats[code]
            s["games"] += 1; s["wins"] += int(won); s["pf"] += pf; s["pa"] += pa; s["name"] = club["name"]
        margins.append(hs - aws); totals.append(hs + aws)
        text = f"{home['club']['name']} {hs}–{aws} {away['club']['name']} (final)"
        for code in (hc, ac):
            if not recent[code]:
                recent[code].append({"text": text, "date": game["utcDate"][:10],
                                     "source_id": source_id, "url": cap.url(source_id)})
    if not stats:
        return []
    league_ppg = sum(s["pf"] for s in stats.values()) / sum(s["games"] for s in stats.values())
    home_court = statistics.fmean(margins) if margins else 0.0
    margin_sigma = max(8.0, statistics.stdev(margins) if len(margins) > 1 else 11.0)
    total_sigma = max(10.0, statistics.stdev(totals) if len(totals) > 1 else 14.0)
    rows = []
    for game in games:
        start = game.get("utcDate", "")
        if game.get("played") or not in_window(start, cap.cutoff):
            continue
        home, away = game["local"], game["road"]
        a, b = stats.get(home["club"]["code"]), stats.get(away["club"]["code"])
        if not a or not b or not a["games"] or not b["games"]:
            continue
        home_name, away_name = home["club"]["name"], away["club"]["name"]
        row = base_row(cap, f"{provider}-{game['identifier']}", provider, "Basketball",
                       f"{competition} — {game.get('roundName') or game.get('roundAlias') or game.get('phaseType', {}).get('name', '')}",
                       home_name, away_name, start, (game.get("venue") or {}).get("name", ""), [source_id])
        for side, club, s in (("side_a", home["club"], a), ("side_b", away["club"], b)):
            row["form"][side] = {"text": f"{s['wins']}-{s['games'] - s['wins']}, {s['pf']} points for / {s['pa']} against in {s['games']} official games",
                                 "games": s["games"], "wins": s["wins"], "points_for": s["pf"], "points_against": s["pa"]}
        row["recent_results"] = (tag_team(recent.get(home["club"]["code"], []), home_name)
                                 + tag_team(recent.get(away["club"]["code"], []), away_name))
        row["aliases_a"] = list(dict.fromkeys([home_name, home["club"].get("abbreviatedName", ""), home["club"].get("editorialName", "")]))
        row["aliases_b"] = list(dict.fromkeys([away_name, away["club"].get("abbreviatedName", ""), away["club"].get("editorialName", "")]))
        k = 5.0
        rates = {}
        for key, s in (("a", a), ("b", b)):
            rates[key] = {"pf": (s["pf"] + k * league_ppg) / (s["games"] + k),
                          "pa": (s["pa"] + k * league_ppg) / (s["games"] + k)}
        home_points = (rates["a"]["pf"] + rates["b"]["pa"]) / 2 + home_court / 2
        away_points = (rates["b"]["pf"] + rates["a"]["pa"]) / 2 - home_court / 2
        margin, total = home_points - away_points, home_points + away_points
        row["markets"] = basketball_markets(home_name, away_name, margin, total, margin_sigma, total_sigma)
        row["inputs"] = {"league_points_per_team_game": round(league_ppg, 6),
                         "home_court_margin": round(home_court, 6), "expected_margin": round(margin, 6),
                         "expected_total": round(total, 6), "margin_sigma": round(margin_sigma, 6),
                         "total_sigma": round(total_sigma, 6)}
        row["model"] = {"name": "Shrunk scoring rates with Normal score distributions", "shrinkage_games": 5,
                        "assumptions": ["Official played-game PF/PA rates shrink toward the league mean over five pseudo-games.",
                                        "Home-court margin and both distribution sigmas are estimated from captured completed games.",
                                        "No injury, roster, travel or rest adjustment is applied."]}
        row["investigated_markets"] = investigated("Basketball", ["Match Winner", "Handicap", "Match Total"])
        attach_pick(row, min(a["games"], b["games"]) >= 6)
        rows.append(row)
    return rows


def mlb(cap: Capture) -> list[dict[str, Any]]:
    schedule = cap.json("mlb_ws_schedule")
    standings_doc = cap.json("mlb_standings_2026")
    stats = {t["team"]["id"]: t for record in standings_doc["records"] for t in record["teamRecords"]}
    hitting = {s["team"]["id"]: s["stat"] for block in cap.json("mlb_hitting_2026")["stats"] for s in block["splits"]}
    pitching = {s["team"]["id"]: s["stat"] for block in cap.json("mlb_pitching_2026")["stats"] for s in block["splits"]}
    all_games = [game for day in schedule.get("dates", []) for game in day.get("games", [])]
    recent: dict[int, list[dict[str, str]]] = defaultdict(list)
    for game in sorted(all_games, key=lambda g: g["gameDate"], reverse=True):
        if game["gameDate"] >= cap.cutoff or game["status"]["abstractGameState"] != "Final":
            continue
        away, home = game["teams"]["away"], game["teams"]["home"]
        if "score" not in away or "score" not in home:
            continue
        text = f"{away['team']['name']} {away['score']}–{home['score']} {home['team']['name']} (final)"
        for side in (away, home):
            tid = side["team"]["id"]
            if not recent[tid]:
                recent[tid].append({"text": text, "date": game["officialDate"],
                                    "source_id": "mlb_ws_schedule", "url": cap.url("mlb_ws_schedule")})
    rows = []
    for game in all_games:
        start = iso_z(game["gameDate"])
        if not in_window(start, cap.cutoff) or game["status"]["abstractGameState"] == "Final":
            continue
        home, away = game["teams"]["home"], game["teams"]["away"]
        a, b = stats.get(home["team"]["id"]), stats.get(away["team"]["id"])
        if not a or not b:
            continue
        row = base_row(cap, f"mlb-{game['gamePk']}", "mlb", "Baseball",
                       game.get("description") or game.get("seriesDescription") or "MLB",
                       home["team"]["name"], away["team"]["name"], start,
                       (game.get("venue") or {}).get("name", ""),
                       ["mlb_ws_schedule", "mlb_standings_2026", "mlb_hitting_2026", "mlb_pitching_2026"])
        for side, team in (("side_a", a), ("side_b", b)):
            tid = team["team"]["id"]
            era = pitching.get(tid, {}).get("era", "")
            ops = hitting.get(tid, {}).get("ops", "")
            row["form"][side] = {"text": f"{team['wins']}-{team['losses']}, {team['runsScored']} runs scored / {team['runsAllowed']} allowed in {team['gamesPlayed']} regular-season games; team ERA {era}; OPS {ops}",
                                 "games": team["gamesPlayed"], "wins": team["wins"], "losses": team["losses"],
                                 "runs_for": team["runsScored"], "runs_against": team["runsAllowed"],
                                 "era": era, "ops": ops}
        for side, team in (("side_a", home), ("side_b", away)):
            probable = team.get("probablePitcher")
            if probable:
                row["player_facts"].append({"name": probable["fullName"],
                                            "text": f"{probable['fullName']} is listed by MLB as the probable pitcher for {team['team']['name']} in this game",
                                            "source_id": "mlb_ws_schedule", "url": cap.url("mlb_ws_schedule"),
                                            "team": team["team"]["name"]})
        row["recent_results"] = (tag_team(recent.get(home["team"]["id"], []), home["team"]["name"])
                                 + tag_team(recent.get(away["team"]["id"], []), away["team"]["name"]))
        wa = float(a["winningPercentage"]); wb = float(b["winningPercentage"])
        p_home = (wa * (1 - wb)) / (wa * (1 - wb) + (1 - wa) * wb)
        p_home = min(0.95, max(0.05, p_home + 0.015))
        home_lambda = ((a["runsScored"] / a["gamesPlayed"]) + (b["runsAllowed"] / b["gamesPlayed"])) / 2 * 1.02
        away_lambda = ((b["runsScored"] / b["gamesPlayed"]) + (a["runsAllowed"] / a["gamesPlayed"])) / 2 * 0.98
        row["markets"] = scoring_markets(home["team"]["name"], away["team"]["name"], home_lambda, away_lambda,
                                         p_home, "Run Line", "Match Total Runs")
        row["inputs"] = {"home_expected_runs": round(home_lambda, 6), "away_expected_runs": round(away_lambda, 6),
                         "log5_home_before_adjustment": round((wa * (1 - wb)) / (wa * (1 - wb) + (1 - wa) * wb), 6)}
        row["model"] = {"name": "Regular-season log5 plus independent-Poisson runs", "home_probability_adjustment": 0.015,
                        "assumptions": ["Match-winner probability uses official 162-game winning percentages in a log5 calculation with +1.5 percentage points for home field.",
                                        "Run expectations average one club's runs scored with the opponent's runs allowed.",
                                        "Independent Poisson is a simplifying approximation for baseball scoring and extra innings.",
                                        "Probable pitchers are reported when listed but no individual-pitcher adjustment is inferred."]}
        row["investigated_markets"] = investigated("Baseball", ["Match Winner", "Handicap", "Match Total"])
        attach_pick(row, min(a["gamesPlayed"], b["gamesPlayed"]) >= 100)
        rows.append(row)
    return rows


def set_wins(match: dict[str, Any]) -> tuple[int, int]:
    a = b = 0
    for i in range(1, 6):
        sa, sb = match.get(f"ScoreSet{i}A", ""), match.get(f"ScoreSet{i}B", "")
        if sa in ("", None) or sb in ("", None):
            continue
        try:
            ai, bi = int(sa), int(sb)
        except (TypeError, ValueError):
            continue
        if ai > bi: a += 1
        elif bi > ai: b += 1
    return a, b


def wta(cap: Capture) -> list[dict[str, Any]]:
    rankings: dict[int, dict[str, Any]] = {}
    ranking_source_by_id: dict[int, str] = {}
    ranking_sources = []
    for i in range(4):
        source_id = f"wta_rankings_{i}"
        if not cap.usable(source_id):
            continue
        ranking_sources.append(source_id)
        for entry in cap.json(source_id):
            player_id = int(entry["player"]["id"])
            rankings[player_id] = entry
            ranking_source_by_id[player_id] = source_id
    rows = []
    for event_id in ("2092", "405"):
        source_id = f"wta_{event_id}_matches"
        doc = cap.json(source_id)
        tournament = doc["tournament"]
        completed = [m for m in doc["matches"] if m.get("MatchState") == "F" and m.get("DrawLevelType") == "M" and m.get("DrawMatchType") == "S"]
        form: dict[int, dict[str, int]] = defaultdict(lambda: {"wins": 0, "losses": 0})
        recent: dict[int, list[dict[str, str]]] = defaultdict(list)
        for match in sorted(completed, key=lambda m: m.get("MatchTimeStamp", ""), reverse=True):
            wa, wb = set_wins(match)
            if wa == wb:
                continue
            a_id, b_id = int(match["PlayerIDA"]), int(match["PlayerIDB"])
            winner, loser = (a_id, b_id) if wa > wb else (b_id, a_id)
            form[winner]["wins"] += 1; form[loser]["losses"] += 1
            for player_id in (a_id, b_id):
                if not recent[player_id] and match.get("ResultString"):
                    recent[player_id].append({"text": match["ResultString"], "date": iso_z(match["MatchTimeStamp"])[:10],
                                              "source_id": source_id, "url": cap.url(source_id)})
        for match in doc["matches"]:
            if match.get("MatchState") != "U" or match.get("DrawLevelType") != "M" or match.get("DrawMatchType") != "S":
                continue
            if not match.get("PlayerIDA") or not match.get("PlayerIDB"):
                continue
            a_id, b_id = int(match["PlayerIDA"]), int(match["PlayerIDB"])
            a_name = f"{match.get('PlayerNameFirstA', '')} {match.get('PlayerNameLastA', '')}".strip()
            b_name = f"{match.get('PlayerNameFirstB', '')} {match.get('PlayerNameLastB', '')}".strip()
            if not a_name or not b_name or "TBD" in (a_name, b_name):
                continue
            start = "" if match.get("Unscheduled") else iso_z(match["MatchTimeStamp"])
            if start and not in_window(start, cap.cutoff):
                continue
            if not start and not (cap.cutoff[:10] <= tournament["endDate"] <= "2026-11-08"):
                continue
            evidence_ids = [source_id] + ranking_sources
            row = base_row(cap, f"wta-{event_id}-{match['MatchID']}", "wta", "Tennis", tournament["title"],
                           a_name, b_name, start, "", evidence_ids)
            if not start:
                row["flags"].append({"code": "START_UNCONFIRMED", "reason": "The official feed lists the pairing as unscheduled; start and court are blank."})
            ra, rb = rankings.get(a_id), rankings.get(b_id)
            for side, name, ranking, f in (("side_a", a_name, ra, form[a_id]), ("side_b", b_name, rb, form[b_id])):
                rank_text = f"WTA #{ranking['ranking']} with {ranking['points']} points dated {ranking['rankedAt'][:10]}" if ranking else "ranking unavailable"
                row["form"][side] = {"text": f"{rank_text}; current tournament: {f['wins']}-{f['losses']}",
                                     "wins": f["wins"], "losses": f["losses"],
                                     "rank": ranking["ranking"] if ranking else None,
                                     "points": ranking["points"] if ranking else None}
                if ranking:
                    player_source = ranking_source_by_id[int(ranking["player"]["id"])]
                    row["player_facts"].append({"name": name, "text": f"{name} is {rank_text}",
                                                "source_id": player_source, "url": cap.url(player_source), "team": name})
            row["recent_results"] = (tag_team(recent.get(a_id, []), a_name)
                                     + tag_team(recent.get(b_id, []), b_name))
            row["aliases_a"] = [a_name, match.get("PlayerNameLastA", "")]
            row["aliases_b"] = [b_name, match.get("PlayerNameLastB", "")]
            if not ra or not rb or not ra["points"] or not rb["points"]:
                rows.append(unpriced(row, "Both players need an official WTA ranking and ranking points before a line can be originated."))
                continue
            weight_a, weight_b = math.sqrt(ra["points"]), math.sqrt(rb["points"])
            p_a = weight_a / (weight_a + weight_b)
            row["markets"] = moneyline_only(a_name, b_name, p_a)
            row["inputs"] = {"ranking_points_a": ra["points"], "ranking_points_b": rb["points"],
                             "ranked_at": ra["rankedAt"]}
            row["model"] = {"name": "Square-root WTA ranking-points share",
                            "assumptions": ["Each side's weight is the square root of official WTA ranking points; the two weights are normalised to sum to one.",
                                            "The transformation is our modelling choice, not a WTA win-probability publication.",
                                            "Current-tournament results are evidence for grading, not an extra probability adjustment.",
                                            "Game handicap and total games are not originated without official game-level inputs."]}
            row["investigated_markets"] = investigated("Tennis", ["Match Winner"],
                                                       "Only match winner is priced; ranking points alone do not substantiate a game handicap or total-games distribution.")
            attach_pick(row, min(form[a_id]["wins"] + form[a_id]["losses"], form[b_id]["wins"] + form[b_id]["losses"]) >= 1)
            rows.append(row)
    return rows


def lol(cap: Capture) -> list[dict[str, Any]]:
    source_id = "lolesports_schedule"
    events = cap.json(source_id)["data"]["schedule"]["events"]
    stats: dict[tuple[str, str], dict[str, Any]] = defaultdict(lambda: {"games": 0, "wins": 0})
    recent: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for event in sorted(events, key=lambda e: e.get("startTime", ""), reverse=True):
        if event.get("state") != "completed" or event.get("startTime", "") >= cap.cutoff or event.get("type") != "match":
            continue
        league = event["league"]["slug"]
        teams = event.get("match", {}).get("teams", [])
        if len(teams) != 2 or not teams[0].get("result") or not teams[1].get("result"):
            continue
        outcomes = [team["result"].get("outcome") for team in teams]
        if "win" not in outcomes:
            continue
        text = f"{teams[0]['name']} {teams[0]['result']['gameWins']}–{teams[1]['result']['gameWins']} {teams[1]['name']} (official series result)"
        for index, team in enumerate(teams):
            key = (league, team["name"])
            stats[key]["games"] += 1
            stats[key]["wins"] += int(outcomes[index] == "win")
            if not recent[key]:
                recent[key].append({"text": text, "date": event["startTime"][:10],
                                    "source_id": source_id, "url": cap.url(source_id)})
    rows = []
    for event in events:
        start = event.get("startTime", "")
        if event.get("state") != "unstarted" or event.get("type") != "match" or not in_window(start, cap.cutoff):
            continue
        teams = event.get("match", {}).get("teams", [])
        if len(teams) != 2 or any(not t.get("name") or t["name"] == "TBD" for t in teams):
            continue
        league = event["league"]["slug"]
        a_name, b_name = teams[0]["name"], teams[1]["name"]
        row = base_row(cap, f"lol-{event['match']['id']}", "lol", "Esports",
                       f"{event['league']['name']} — {event.get('blockName', '')} (best of {event['match']['strategy']['count']})",
                       a_name, b_name, start, "", [source_id])
        a, b = stats[(league, a_name)], stats[(league, b_name)]
        for side, name, s in (("side_a", a_name, a), ("side_b", b_name, b)):
            row["form"][side] = {"text": f"{s['wins']}-{s['games'] - s['wins']} in captured official {event['league']['name']} series",
                                 "games": s["games"], "wins": s["wins"]}
        row["recent_results"] = (tag_team(recent.get((league, a_name), []), a_name)
                                 + tag_team(recent.get((league, b_name), []), b_name))
        row["aliases_a"] = [a_name, teams[0].get("code", "")]
        row["aliases_b"] = [b_name, teams[1].get("code", "")]
        if min(a["games"], b["games"]) < 3:
            rows.append(unpriced(row, "Both teams need at least three completed series in the captured official competition feed; current records are insufficient."))
            continue
        wa, wb = (a["wins"] + 1) / (a["games"] + 2), (b["wins"] + 1) / (b["games"] + 2)
        p_a = (wa * (1 - wb)) / (wa * (1 - wb) + (1 - wa) * wb)
        row["markets"] = moneyline_only(a_name, b_name, p_a, "Series Winner")
        row["inputs"] = {"series_a": a["games"], "series_b": b["games"],
                         "shrunk_win_rate_a": round(wa, 6), "shrunk_win_rate_b": round(wb, 6)}
        row["model"] = {"name": "Shrunk official series-record log5",
                        "assumptions": ["Each team's captured competition record receives two prior series, split 1–1, before log5.",
                                        "Only the official schedule page is used; missing earlier rounds are not reconstructed from memory.",
                                        "Map handicap and map total are not originated without a complete map-level history."]}
        row["investigated_markets"] = investigated("Esports", ["Match Winner"],
                                                   "Only series winner is priced; the capture does not contain enough map-level history for a map line or total.")
        attach_pick(row, min(a["games"], b["games"]) >= 5)
        rows.append(row)
    return rows


def enrich_official_page_checks(rows: list[dict[str, Any]]) -> None:
    """Attach manually read official-page evidence without hiding runner 429s."""
    path = DATA / "live_checks.json"
    if not path.exists():
        return
    doc = load(path)
    checks = {check["id"]: check for check in doc["checks"]}
    mapping = {
        "euroleague-E2026_76": [("euroleague-panathinaikos-roster", 0, "Sylvain Francisco", "Panathinaikos AKTOR Athens")],
        "euroleague-E2026_92": [("euroleague-fenerbahce-roster", 0, "Wade Baldwin IV", "Fenerbahce Tarfin Istanbul"),
                                  ("euroleague-player-stats", 1, "Wade Baldwin IV", "Fenerbahce Tarfin Istanbul")],
        "euroleague-E2026_90": [("euroleague-olympiacos-roster", 0, "Jean Montero", "Olympiacos Piraeus"),
                                  ("euroleague-player-stats", 0, "Jean Montero", "Olympiacos Piraeus")],
    }
    for row in rows:
        for check_id, fact_index, name, team in mapping.get(row["id"], []):
            check = checks[check_id]
            fact = check["facts"][fact_index]
            row["player_facts"].append({"name": name, "team": team, "text": fact["text"],
                                        "source_id": check_id, "url": check["url"],
                                        "retrieved_utc": doc["retrieved_utc"], "live_page_check": True})


def collect_rows(cap: Capture) -> list[dict[str, Any]]:
    rows = []
    rows.extend(nhl(cap))
    rows.extend(liiga(cap))
    rows.extend(basketball_feed(cap, "euroleague_games_E2026", "euroleague", "EuroLeague"))
    rows.extend(basketball_feed(cap, "eurocup_games_U2026", "eurocup", "EuroCup"))
    rows.extend(mlb(cap))
    rows.extend(wta(cap))
    rows.extend(lol(cap))
    enrich_official_page_checks(rows)
    rows.sort(key=lambda r: (r["sport"], r["start_utc"] or "9999", r["id"]))
    return rows


def phrase_in(phrase: str, text: str) -> bool:
    p, t = norm(phrase), norm(text)
    return len(p) >= 3 and f" {p} " in f" {t} "


def reconcile(rows: list[dict[str, Any]], listing: dict[str, Any]) -> None:
    """Conservative participant-name join; ambiguous candidates stay unmatched."""
    events = [e for e in listing["events"] if e["kind"] == "match" and e["upcoming_at_capture"]]
    used: set[str] = set()
    for row in rows:
        candidates = []
        for event in events:
            if event["sport"] != row["sport"] or event["listing_id"] in used:
                continue
            name = event["listed_name"]
            a = any(phrase_in(alias, name) for alias in row["aliases_a"] if alias)
            b = any(phrase_in(alias, name) for alias in row["aliases_b"] if alias)
            if a and b:
                candidates.append(event)
        if len(candidates) == 1:
            event = candidates[0]
            used.add(event["listing_id"])
            row["olbg_listing_id"] = event["listing_id"]
            row["olbg_url"] = event["olbg_url"]
            event["official_reconciliation"] = "matched"
            event["official_url"] = row["official_url"]
            event["official_fixture_id"] = row["id"]
        elif len(candidates) > 1:
            row["flags"].append({"code": "OLBG_MATCH_AMBIGUOUS", "reason": "More than one OLBG listing matched the participant aliases; no listing link was asserted."})

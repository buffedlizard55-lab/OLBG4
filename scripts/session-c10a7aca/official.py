#!/usr/bin/env python3
"""Parsers for Board C10's captured official competition data.

No parser manufactures a missing value.  Each fixture carries the official URL
and the exact evidence citations used for both fixture and statistical fields.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re

from common import EvidenceStore, fixture, iso, team_side, utc


def _summary_stats(gp: int, wins: int, losses: int, pf: float, pa: float, **extra) -> dict:
    return {"gp": gp, "wins": wins, "losses": losses, "pf": round(pf, 3),
            "pa": round(pa, 3), "win_pct": round(wins / gp, 5) if gp else None,
            "pf_pg": round(pf / gp, 3) if gp else None, "pa_pg": round(pa / gp, 3) if gp else None,
            "net_pg": round((pf - pa) / gp, 3) if gp else None, **extra}


def parse_nhl(store: EvidenceStore) -> list[dict]:
    schedule_targets = ["nhl_sched_2026_10_22", "nhl_sched_2026_10_23",
                        "nhl_sched_2026_10_29", "nhl_sched_2026_11_05"]
    schedules = [(target, store.get(target)) for target in schedule_targets]
    schedules = [(target, ev) for target, ev in schedules if ev]
    standings_ev = store.get("nhl_standings_now") or store.get("nhl_standings_2026_10_23")
    if not schedules or not standings_ev:
        return []
    standings = {}
    for row in standings_ev.json()["standings"]:
        abbr = row["teamAbbrev"]["default"]
        gp = int(row["gamesPlayed"])
        stats = _summary_stats(gp, int(row["wins"]), int(row["losses"]),
                               float(row["goalFor"]), float(row["goalAgainst"]),
                               ot_losses=int(row.get("otLosses", 0)), points=row.get("points"),
                               streak=f"{row.get('streakCode', '')}{row.get('streakCount', '')}",
                               last10={"wins": row.get("l10Wins"), "losses": row.get("l10Losses"),
                                       "ot_losses": row.get("l10OtLosses"), "goals_for": row.get("l10GoalsFor"),
                                       "goals_against": row.get("l10GoalsAgainst")},
                               home_record=f"{row.get('homeWins')}-{row.get('homeLosses')}-{row.get('homeOtLosses')}",
                               road_record=f"{row.get('roadWins')}-{row.get('roadLosses')}-{row.get('roadOtLosses')}")
        standings[abbr] = (row, stats)
    games: dict[int, tuple[dict, str, object]] = {}
    recent: dict[str, list[dict]] = defaultdict(list)
    for target, ev in schedules:
        payload = ev.json()
        week_games = [game for day in payload.get("gameWeek", []) for game in day.get("games", [])]
        # Some score-style responses use a flat games array; accept both while
        # retaining the schedule endpoint's official week structure.
        week_games += payload.get("games", [])
        for game in week_games:
            games[int(game["id"])] = (game, target, ev)
            if game.get("gameState") in {"OFF", "FINAL"} and utc(game["startTimeUTC"]) <= store.cutoff:
                for side, opponent in (("awayTeam", "homeTeam"), ("homeTeam", "awayTeam")):
                    team, other = game[side], game[opponent]
                    if "score" not in team or "score" not in other:
                        continue
                    abbr = team["abbrev"]
                    recent[abbr].append({"date": game.get("gameDate", game["startTimeUTC"][:10]), "opponent": other.get("commonName", {}).get("default"),
                                         "team_score": team["score"], "opponent_score": other["score"],
                                         "result": "W" if team["score"] > other["score"] else "L",
                                         "game_id": game["id"], "evidence_target": target})
    for values in recent.values():
        values.sort(key=lambda r: (r["date"], r["game_id"]), reverse=True)
        del values[5:]
    out = []
    for game_id, (game, target, ev) in sorted(games.items()):
        if game.get("gameState") not in {"FUT", "PRE"} or utc(game["startTimeUTC"]) <= store.cutoff:
            continue
        away, home = game["awayTeam"], game["homeTeam"]
        aa, ha = away["abbrev"], home["abbrev"]
        if aa not in standings or ha not in standings:
            continue
        ar, astat = standings[aa]
        hr, hstat = standings[ha]
        a = team_side(ar["teamName"]["default"], [aa, {"TBL": "TB", "SJS": "SJ", "NJD": "NJ", "LAK": "LA"}.get(aa, aa)],
                      ar["teamCommonName"]["default"], stats=astat, recent=recent.get(aa, []))
        h = team_side(hr["teamName"]["default"], [ha, {"TBL": "TB", "SJS": "SJ", "NJD": "NJ", "LAK": "LA"}.get(ha, ha)],
                      hr["teamCommonName"]["default"], stats=hstat, recent=recent.get(ha, []))
        path = game.get("gameCenterLink") or f"/gamecenter/{aa}-vs-{ha}/{game_id}"
        url = "https://www.nhl.com" + path if path.startswith("/") else path
        citations = [ev.citation(), standings_ev.citation()]
        out.append(fixture(f"nhl:{game_id}", "Ice Hockey", "NHL", iso(utc(game["startTimeUTC"])), url,
                           h, a, citations,
                           {"venue": game.get("venue", {}).get("default"), "away": aa, "home": ha,
                            "league": "NHL", "margin_sd": 1.45, "total_sd": 1.65,
                            "home_advantage_logit": 0.16, "home_advantage_points": 0.18,
                            "model_family": "nhl_goals"},
                           {"side1": hstat, "side2": astat, "recent1": recent.get(ha, []),
                            "recent2": recent.get(aa, []), "standings_date": standings_ev.json().get("standingsDateTimeUtc")}))
    return out


def parse_mlb(store: EvidenceStore) -> list[dict]:
    schedule_ev = store.get("mlb_ws_schedule") or store.get("mlb_ws_probables")
    standings_ev = store.get("mlb_standings_2026")
    if not schedule_ev or not standings_ev:
        return []
    standings = {}
    for division in standings_ev.json().get("records", []):
        for row in division.get("teamRecords", []):
            league = row["leagueRecord"]
            splits = {s["type"]: s for s in row.get("records", {}).get("splitRecords", [])}
            gp = int(row["gamesPlayed"])
            # MLB's standings payload exposes runs in the expectedRecords block
            # only indirectly, so use the explicit runs fields when present and
            # otherwise leave scoring inputs unavailable rather than infer them.
            rs, ra = row.get("runsScored"), row.get("runsAllowed")
            if rs is None or ra is None:
                # Current MLB standings responses include these under teamRecord
                # in some seasons; the captured response may omit them.  A neutral
                # run environment is explicitly identified in model metadata.
                rs = ra = None
            stats = _summary_stats(gp, int(league["wins"]), int(league["losses"]),
                                   float(rs) if rs is not None else 0.0,
                                   float(ra) if ra is not None else 0.0,
                                   last10=splits.get("lastTen"), streak=row.get("streak", {}).get("streakCode"),
                                   division_rank=row.get("divisionRank"),
                                   home_record=splits.get("home"), road_record=splits.get("away"),
                                   scoring_available=rs is not None and ra is not None)
            if rs is None:
                stats.update(pf=None, pa=None, pf_pg=None, pa_pg=None, net_pg=None)
            standings[int(row["team"]["id"])] = stats
    out = []
    for date in schedule_ev.json().get("dates", []):
        for game in date.get("games", []):
            start = utc(game["gameDate"])
            if start <= store.cutoff or game.get("status", {}).get("abstractGameState") != "Preview":
                continue
            home, away = game["teams"]["home"], game["teams"]["away"]
            hid, aid = int(home["team"]["id"]), int(away["team"]["id"])
            if hid not in standings or aid not in standings:
                continue
            ht, at = home["team"], away["team"]
            h = team_side(ht["name"], [ht.get("abbreviation", "")], ht.get("teamName", ht["name"].split()[-1]),
                          stats=standings[hid], probable_pitcher=home.get("probablePitcher", {}).get("fullName"))
            a = team_side(at["name"], [at.get("abbreviation", "")], at.get("teamName", at["name"].split()[-1]),
                          stats=standings[aid], probable_pitcher=away.get("probablePitcher", {}).get("fullName"))
            url = f"https://www.mlb.com/gameday/{game['gamePk']}"
            detail = {"venue": game.get("venue", {}).get("name"), "description": game.get("description"),
                      "game_type": game.get("gameType"), "league": "MLB", "margin_sd": 4.1,
                      "total_sd": 3.2, "home_advantage_logit": 0.10, "home_advantage_points": 0.12,
                      "model_family": "mlb_runs", "series_game_number": game.get("seriesGameNumber")}
            out.append(fixture(f"mlb:{game['gamePk']}", "Baseball", game.get("description") or "MLB",
                               iso(start), url, h, a, [schedule_ev.citation(), standings_ev.citation()], detail,
                               {"side1": standings[hid], "side2": standings[aid],
                                "side1_probable_pitcher": h.get("probable_pitcher"),
                                "side2_probable_pitcher": a.get("probable_pitcher")}))
    return out


def parse_nba(store: EvidenceStore) -> list[dict]:
    ev = store.get("nba_cdn_schedule")
    if not ev:
        return []
    games = []
    for date in ev.json()["leagueSchedule"]["gameDates"]:
        games.extend(date.get("games", []))
    totals: dict[int, dict] = defaultdict(lambda: {"gp": 0, "wins": 0, "losses": 0, "pf": 0.0, "pa": 0.0})
    recent: dict[int, list[dict]] = defaultdict(list)
    for game in games:
        if not str(game.get("gameId", "")).startswith("00226") or game.get("gameStatus") != 3:
            continue
        if utc(game["gameDateTimeUTC"]) > store.cutoff:
            continue
        home, away = game["homeTeam"], game["awayTeam"]
        if not home.get("score") or not away.get("score"):
            continue
        for team, other, location in ((home, away, "home"), (away, home, "away")):
            tid = int(team["teamId"])
            t = totals[tid]
            t["gp"] += 1
            t["pf"] += float(team["score"])
            t["pa"] += float(other["score"])
            won = team["score"] > other["score"]
            t["wins" if won else "losses"] += 1
            recent[tid].append({"date": game["gameDateTimeUTC"], "opponent": f"{other['teamCity']} {other['teamName']}",
                                "team_score": team["score"], "opponent_score": other["score"],
                                "result": "W" if won else "L", "location": location, "game_id": game["gameId"]})
    for values in recent.values():
        values.sort(key=lambda r: r["date"], reverse=True)
        del values[5:]
    out = []
    for game in games:
        if not str(game.get("gameId", "")).startswith("00226") or game.get("gameStatus") != 1:
            continue
        start = utc(game["gameDateTimeUTC"])
        if start <= store.cutoff:
            continue
        home, away = game["homeTeam"], game["awayTeam"]
        hid, aid = int(home["teamId"]), int(away["teamId"])
        if hid not in totals or aid not in totals:
            continue
        hstat = _summary_stats(**totals[hid], recent=recent[hid])
        astat = _summary_stats(**totals[aid], recent=recent[aid])
        h = team_side(f"{home['teamCity']} {home['teamName']}", [home["teamTricode"]], home["teamName"], stats=hstat)
        a = team_side(f"{away['teamCity']} {away['teamName']}", [away["teamTricode"]], away["teamName"], stats=astat)
        game_url = f"https://www.nba.com/game/{away['teamTricode'].lower()}-vs-{home['teamTricode'].lower()}-{game['gameId']}"
        detail = {"venue": game.get("arenaName"), "city": game.get("arenaCity"),
                  "league": "NBA", "margin_sd": 12.0, "total_sd": 18.0,
                  "home_advantage_logit": 0.18, "home_advantage_points": 2.1,
                  "model_family": "nba_points", "early_season": True}
        out.append(fixture(f"nba:{game['gameId']}", "Basketball", "NBA", iso(start), game_url,
                           h, a, [ev.citation()], detail,
                           {"side1": hstat, "side2": astat, "recent1": recent[hid], "recent2": recent[aid]}))
    return out


def parse_euroleague(store: EvidenceStore, competition: str = "E") -> list[dict]:
    season = "E2026" if competition == "E" else "U2026"
    target = f"euroleague_games_{season}"
    ev = store.get(target)
    if not ev:
        return []
    games = ev.json().get("data", [])
    totals: dict[str, dict] = defaultdict(lambda: {"gp": 0, "wins": 0, "losses": 0, "pf": 0.0, "pa": 0.0})
    clubs: dict[str, dict] = {}
    recent: dict[str, list[dict]] = defaultdict(list)
    for game in games:
        local, road = game.get("local", {}), game.get("road", {})
        if not local.get("club") or not road.get("club"):
            continue
        lc, rc = local["club"], road["club"]
        clubs[lc["code"]] = lc
        clubs[rc["code"]] = rc
        if not game.get("played") or utc(game["date"]) > store.cutoff:
            continue
        if local.get("score") is None or road.get("score") is None:
            continue
        for club, other, own, opp in ((lc, rc, local["score"], road["score"]),
                                      (rc, lc, road["score"], local["score"])):
            code = club["code"]
            t = totals[code]
            t["gp"] += 1
            t["pf"] += float(own)
            t["pa"] += float(opp)
            won = own > opp
            t["wins" if won else "losses"] += 1
            recent[code].append({"date": game["date"], "opponent": other.get("name"),
                                 "team_score": own, "opponent_score": opp,
                                 "result": "W" if won else "L", "game_code": game.get("gameCode")})
    for values in recent.values():
        values.sort(key=lambda r: r["date"], reverse=True)
        del values[5:]
    out = []
    for game in games:
        if game.get("played") or utc(game["date"]) <= store.cutoff:
            continue
        local, road = game.get("local", {}), game.get("road", {})
        if not local.get("club") or not road.get("club"):
            continue
        hc, ac = local["club"], road["club"]
        if hc["code"] not in totals or ac["code"] not in totals:
            continue
        def side(club):
            aliases = [club.get("abbreviatedName", ""), club.get("tvCode", ""), club.get("code", "")]
            if club.get("code") == "ASV":
                aliases.append("ASVEL Lyon Villeurbanne")
            return team_side(club["name"], aliases, club.get("editorialName") or club.get("abbreviatedName"),
                             stats=_summary_stats(**totals[club["code"]], recent=recent[club["code"]]))
        h, a = side(hc), side(ac)
        # OLBG often uses the short editorial name (Zalgiris rather than Zalgiris Kaunas).
        h["aliases"] = sorted(set(h["aliases"] + [club.lower() for club in []]))
        name = "EuroLeague" if competition == "E" else "EuroCup"
        round_value = game.get("round")
        if isinstance(round_value, dict):
            round_value = round_value.get("round")
        detail = {"venue": local.get("venue", {}).get("name"), "round": round_value,
                  "league": name, "margin_sd": 11.0, "total_sd": 16.0,
                  "home_advantage_logit": 0.20, "home_advantage_points": 2.6,
                  "model_family": "euro_points"}
        out.append(fixture(f"{name}:{game.get('gameCode')}", "Basketball", name, iso(utc(game["date"])),
                           ev.url, h, a, [ev.citation()], detail,
                           {"side1": h["stats"], "side2": a["stats"],
                            "recent1": recent[hc["code"]], "recent2": recent[ac["code"]]}))
    return out


def parse_wta(store: EvidenceStore) -> list[dict]:
    rankings: dict[int, dict] = {}
    ranking_citations = []
    for page in range(4):
        ev = store.get(f"wta_rankings_{page}")
        if not ev:
            continue
        ranking_citations.append(ev.citation())
        for row in ev.json():
            rankings[int(row["player"]["id"])] = row
    out = []
    for target in ("wta_2092_matches", "wta_405_matches"):
        ev = store.get(target)
        if not ev:
            continue
        payload = ev.json()
        tournament = payload["tournament"]
        completed: dict[int, list[dict]] = defaultdict(list)
        all_matches = payload.get("matches", [])
        for match in all_matches:
            if (match.get("MatchState") != "F" or match.get("DrawMatchType") != "S"
                    or match.get("DrawLevelType") != "M"):
                continue
            result_text = match.get("ResultString") or ""
            winner_prefix = result_text.split(" d ", 1)[0].lower()
            last_a = (match.get("PlayerNameLastA") or "").lower()
            last_b = (match.get("PlayerNameLastB") or "").lower()
            winner_id = None
            if last_a and last_a in winner_prefix and last_b not in winner_prefix:
                winner_id = int(match["PlayerIDA"])
            elif last_b and last_b in winner_prefix and last_a not in winner_prefix:
                winner_id = int(match["PlayerIDB"])
            for suffix in ("A", "B"):
                pid = match.get(f"PlayerID{suffix}")
                if pid:
                    other = 'B' if suffix == 'A' else 'A'
                    opponent = " ".join(filter(None, [match.get(f"PlayerNameFirst{other}"),
                                                       match.get(f"PlayerNameLast{other}")]))
                    result = None
                    if winner_id is not None:
                        result = "W" if int(pid) == winner_id else "L"
                    completed[int(pid)].append({"match_id": match.get("MatchID"), "round_id": match.get("RoundID"),
                                                "opponent": opponent, "score": match.get("ScoreString"),
                                                "result": result, "timestamp": match.get("MatchTimeStamp")})
        for values in completed.values():
            values.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
            del values[5:]
        for match in all_matches:
            if match.get("MatchState") != "U" or match.get("DrawMatchType") != "S":
                continue
            if not match.get("MatchTimeStamp") or match.get("Unscheduled"):
                continue
            start = utc(match["MatchTimeStamp"])
            if start <= store.cutoff:
                continue
            aid, bid = int(match["PlayerIDA"]), int(match["PlayerIDB"])
            if aid not in rankings or bid not in rankings:
                continue
            ar, br = rankings[aid], rankings[bid]
            def player(row, seed):
                p = row["player"]
                return team_side(p["fullName"], [], p["lastName"], player_id=p["id"],
                                 ranking=row["ranking"], points=row["points"],
                                 tournaments_played=row["tournamentsPlayed"], seed=seed or None,
                                 country=p.get("countryCode"), recent=completed.get(p["id"], []))
            a, b = player(ar, match.get("SeedA")), player(br, match.get("SeedB"))
            # OLBG lists A vs B; no home/away orientation exists in tennis.
            url = f"https://www.wtatennis.com/tournament/{tournament['tournamentGroup']['id']}/scores"
            detail = {"round_id": match.get("RoundID"), "surface": tournament.get("surface"),
                      "court": match.get("CourtName"), "not_before": match.get("NotBefore"),
                      "tournament": tournament.get("title"), "level": tournament.get("level"),
                      "model_family": "wta_ranking_points", "best_of": 3}
            citations = [ev.citation()] + ranking_citations
            out.append(fixture(f"wta:{match['EventID']}:{match['MatchID']}", "Tennis",
                               tournament["title"], iso(start), url, a, b, citations, detail,
                               {"side1": {"ranking": ar["ranking"], "points": ar["points"],
                                          "tournaments_played": ar["tournamentsPlayed"], "recent": completed.get(aid, [])},
                                "side2": {"ranking": br["ranking"], "points": br["points"],
                                          "tournaments_played": br["tournamentsPlayed"], "recent": completed.get(bid, [])},
                                "ranked_at": ar["rankedAt"]}))
    return out


def parse_snooker(store: EvidenceStore) -> list[dict]:
    ranking_ev = store.get("wst_rankings_api")
    rankings: dict[str, dict] = {}
    ranking_citation = []
    if ranking_ev:
        ranking_citation = [ranking_ev.citation()]
        tables = ranking_ev.json().get("data", [])
        # Published two-year prize-money table, not the live provisional list.
        choices = [t for t in tables if t.get("attributes", {}).get("name") == "World Rankings"
                   and t.get("attributes", {}).get("rankingType") == "prizeMoney"
                   and not t.get("attributes", {}).get("live")]
        if not choices:
            choices = [t for t in tables if t.get("attributes", {}).get("name") == "World Rankings"]
        if choices:
            for position in choices[0]["attributes"].get("positions", []):
                pid = position.get("player", {}).get("playerID")
                if pid:
                    rankings[pid] = {"position": position.get("position"), "prize_money": position.get("prizeMoney")}
    out = []
    for target in ("wst_match_gilbert_williams", "wst_match_jones_donaldson"):
        ev = store.get(target)
        if not ev:
            continue
        data = ev.json()["data"]
        a = data["attributes"]
        if a.get("status") != "Scheduled" or utc(a["startDateTime"]) <= store.cutoff:
            continue
        def player(key):
            p = a[key]
            seasons = {int(s["season"]): s for s in p.get("seasonStats", [])}
            current = seasons.get(2026)
            name = f"{p['firstName']} {p['surname']}"
            return team_side(name, [], p["surname"], player_id=p["playerID"],
                             season_stats=current, previous_seasons=[seasons[y] for y in sorted(seasons, reverse=True) if y < 2026],
                             ranking=rankings.get(p["playerID"], {}).get("position"),
                             ranking_points=rankings.get(p["playerID"], {}).get("prize_money"))
        home, away = player("homePlayer"), player("awayPlayer")
        if not home.get("season_stats") or not away.get("season_stats"):
            continue
        match_url = f"https://www.wst.tv/match-centre/{data['id']}"
        detail = {"round": a.get("round"), "number_of_frames": a.get("numberOfFrames"),
                  "tournament": a.get("tournament", {}).get("name"), "model_family": "wst_season_stats",
                  "best_of": a.get("numberOfFrames")}
        out.append(fixture(f"wst:{data['id']}", "Snooker", a["tournament"]["name"],
                           iso(utc(a["startDateTime"])), match_url, home, away,
                           [ev.citation()] + ranking_citation, detail,
                           {"side1": home["season_stats"], "side2": away["season_stats"]}))
    return out


def parse_all(store: EvidenceStore) -> list[dict]:
    fixtures = []
    fixtures += parse_nhl(store)
    fixtures += parse_mlb(store)
    fixtures += parse_nba(store)
    fixtures += parse_euroleague(store, "E")
    fixtures += parse_euroleague(store, "U")
    fixtures += parse_wta(store)
    fixtures += parse_snooker(store)
    return fixtures

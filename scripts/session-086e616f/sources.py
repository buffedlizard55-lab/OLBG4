#!/usr/bin/env python3
"""Board AT — read every verified input out of the committed capture bytes.

Nothing in here touches the network and nothing is inferred: a value is only returned if it was
read out of a payload whose SHA-256 matches the committed capture manifest. Each returned object
carries the ``source_url`` (the URL the bytes came from) and the ``capture`` provenance block so
every desk row can be traced back to the exact official page it was read from.

Sources that a peer board or this board could not reach are *not* substituted with anything: the
caller publishes the fixture with blank values and a flag instead.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from capture_lib import Capture, html_tables, strip_scripts, to_text

WINDOW_START = "2026-10-23T21:35:00Z"  # board claim time — nothing already started is published
WINDOW_END = "2026-11-08T23:59:59Z"


def in_window(iso_utc: str | None) -> bool:
    if not iso_utc:
        return False
    return WINDOW_START <= iso_utc <= WINDOW_END


# ============================================================== ice hockey — NHL
def nhl(cap: Capture) -> dict:
    """NHL fixtures from the official schedule API, standings + team form from the same API."""
    standings_src = "nhl_standings_now"
    prov = cap.provenance(standings_src)
    payload = cap.json(standings_src)
    teams: dict[str, dict] = {}
    for row in payload["standings"]:
        abbrev = (row.get("teamAbbrev") or {}).get("default")
        if not abbrev:
            continue
        teams[abbrev] = {
            "abbrev": abbrev,
            "name": _nhl_name({"placeName": row.get("placeName"), "commonName": row.get("commonName")}),
            "gamesPlayed": row.get("gamesPlayed"),
            "wins": row.get("wins"),
            "losses": row.get("losses"),
            "otLosses": row.get("otLosses"),
            "points": row.get("points"),
            "pointPctg": row.get("pointPctg"),
            "goalFor": row.get("goalFor"),
            "goalAgainst": row.get("goalAgainst"),
            "goalDifferential": row.get("goalDifferential"),
            "goalsForPctg": row.get("goalsForPctg"),
            "goalsAgainstPctg": row.get("goalsAgainstPctg"),
            "l10_wins": (row.get("l10Wins") or 0),
            "l10_losses": (row.get("l10Losses") or 0),
            "l10_ot": (row.get("l10OtLosses") or 0),
            "home_wins": row.get("homeWins"),
            "home_losses": row.get("homeLosses"),
            "home_ot": row.get("homeOtLosses"),
            "road_wins": row.get("roadWins"),
            "road_losses": row.get("roadLosses"),
            "road_ot": row.get("roadOtLosses"),
            "streak": (row.get("streakCode") or "") + str(row.get("streakCount") or ""),
            "source_url": prov["source_url"],
            "standings_as_of": payload.get("standingsDateTimeUtc"),
        }
    fixtures = []
    completed: list[dict] = []
    for day in sorted(cap.ids()):
        if not day.startswith("nhl_sched_"):
            continue
        data = cap.json(day)
        p = cap.provenance(day)
        for week in data.get("gameWeek", []):
            for g in week.get("games", []):
                rec = {
                    "id": f"nhl-{g['id']}",
                    "provider_game_id": g["id"],
                    "start_utc": g["startTimeUTC"],
                    "date": week["date"],
                    "venue": (g.get("venue") or {}).get("default"),
                    "game_state": g.get("gameState"),
                    "schedule_state": g.get("gameScheduleState"),
                    "home_abbr": (g.get("homeTeam") or {}).get("abbrev"),
                    "away_abbr": (g.get("awayTeam") or {}).get("abbrev"),
                    "home_name": _nhl_name(g.get("homeTeam")),
                    "away_name": _nhl_name(g.get("awayTeam")),
                    "home_score": (g.get("homeTeam") or {}).get("score"),
                    "away_score": (g.get("awayTeam") or {}).get("score"),
                    "source_url": "https://www.nhl.com" + (g.get("gameCenterLink") or ""),
                    "feed_url": p["source_url"],
                    "capture": p,
                }
                if g.get("gameState") == "OFF" or g.get("gameState") == "FINAL":
                    completed.append(rec)
                fixtures.append(rec)
    # recent form per team, from the completed games in the captured window
    form: dict[str, list[str]] = {}
    for rec in sorted(completed, key=lambda r: r["start_utc"]):
        hs, as_ = rec["home_score"], rec["away_score"]
        if hs is None or as_ is None:
            continue
        h, a = rec["home_abbr"], rec["away_abbr"]
        form.setdefault(h, []).append(f"{'W' if hs > as_ else 'L'} {hs}-{as_} v {a} ({rec['date']})")
        form.setdefault(a, []).append(f"{'W' if as_ > hs else 'L'} {as_}-{hs} @ {h} ({rec['date']})")
    return {
        "teams": teams,
        "fixtures": fixtures,
        "form": {k: v[-5:] for k, v in form.items()},
        "standings_source": prov,
    }


def _nhl_name(team: dict | None) -> str:
    if not team:
        return ""
    place = (team.get("placeName") or {}).get("default", "")
    common = (team.get("commonName") or {}).get("default", "")
    return f"{place} {common}".strip()


# ============================================================== ice hockey — Liiga
def liiga(cap: Capture) -> dict:
    prov = cap.provenance("liiga_standings")
    data = cap.json("liiga_standings")
    teams = {}
    for row in data.get("season", []):
        name = row.get("teamName")
        games = row.get("games") or 0
        gf, ga = row.get("goals") or 0, row.get("goalsAgainst") or 0
        teams[name] = {
            "name": name,
            "games": games,
            "wins": row.get("wins"),
            "ot_wins": row.get("overtimeWins"),
            "losses": row.get("losses"),
            "ot_losses": row.get("overtimeLosses"),
            "ties": row.get("ties"),
            "points": row.get("points"),
            "goals_for": gf,
            "goals_against": ga,
            "ranking": row.get("ranking"),
            "points_pctg": (row.get("points") / games) if games else None,
            "gf_per_game": (gf / games) if games else None,
            "ga_per_game": (ga / games) if games else None,
            "source_url": prov["source_url"],
        }
    games_payload = cap.json("liiga_games")
    gprov = cap.provenance("liiga_games")
    fixtures = []
    completed: list[dict] = []
    games = games_payload if isinstance(games_payload, list) else games_payload.get("games", [])
    for g in games:
        home = g.get("homeTeam") or {}
        away = g.get("awayTeam") or {}
        if not home.get("teamName") or not away.get("teamName"):
            continue
        rec = {
            "id": f"liiga-{g.get('id')}",
            "start_utc": g.get("start"),
            "home": home["teamName"],
            "away": away["teamName"],
            "home_score": home.get("goals"),
            "away_score": away.get("goals"),
            "ended": g.get("ended"),
            "started": g.get("started"),
            "finished_type": g.get("finishedType"),
            "arena": (g.get("iceRink") or {}).get("name") if isinstance(g.get("iceRink"), dict) else g.get("iceRink"),
            "series": g.get("serie"),
            "source_url": "https://liiga.fi/",
            "feed_url": gprov["source_url"],
            "capture": gprov,
        }
        fixtures.append(rec)
        if rec["ended"] and isinstance(rec["home_score"], int) and isinstance(rec["away_score"], int):
            completed.append(rec)
    form: dict[str, list[str]] = {}
    for rec in sorted(completed, key=lambda r: r["start_utc"] or ""):
        hs, as_ = rec["home_score"], rec["away_score"]
        h, a = rec["home"], rec["away"]
        day = (rec["start_utc"] or "")[:10]
        form.setdefault(h, []).append(f"{'W' if hs > as_ else 'L'} {hs}-{as_} v {a} ({day})")
        form.setdefault(a, []).append(f"{'W' if as_ > hs else 'L'} {as_}-{hs} @ {h} ({day})")
    return {"teams": teams, "fixtures": fixtures, "completed": completed,
            "form": {k: v[-5:] for k, v in form.items()}, "standings_source": prov}


def _iso_from_local(value: str) -> str | None:
    value = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone(timedelta(hours=3)))  # EEST/EET host local time
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return None


# ============================================================== ice hockey — SHL
def shl(cap: Capture) -> dict:
    if not cap.have("shl_overview"):
        return {"fixtures": [], "table": []}
    prov = cap.provenance("shl_overview")
    tables = html_tables(cap.text("shl_overview"))
    rows = []
    for tbl in tables:
        for r in tbl:
            rows.append(r)
    return {"tables": tables, "source_url": prov["source_url"], "capture": prov, "row_count": len(rows)}


# ============================================================== basketball — EuroLeague / EuroCup
def euroleague(cap: Capture, target: str, competition: str) -> dict:
    if not cap.have(target):
        return {"fixtures": [], "ratings": {}, "competition": competition}
    prov = cap.provenance(target)
    payload = cap.json(target)
    games = payload.get("data") or []
    ratings: dict[str, dict] = {}
    fixtures = []
    for g in games:
        home = (g.get("local") or {}).get("club") or {}
        away = (g.get("road") or {}).get("club") or {}
        if not home.get("name") or not away.get("name"):
            continue
        iso = (g.get("utcDate") or "").replace("Z", "") + ("Z" if g.get("utcDate") else "")
        iso = g.get("utcDate")
        entry = {
            "id": f"{competition.lower()}-{g.get('gameCode')}",
            "start_utc": iso,
            "round": g.get("roundAlias") or g.get("roundName"),
            "home": home["name"],
            "away": away["name"],
            "home_code": home.get("code"),
            "away_code": away.get("code"),
            "home_score": (g.get("local") or {}).get("score"),
            "away_score": (g.get("road") or {}).get("score"),
            "played": g.get("played"),
            "status": (g.get("status") or {}).get("name") if isinstance(g.get("status"), dict) else g.get("status"),
            "arena": (g.get("arena") or {}).get("name") if isinstance(g.get("arena"), dict) else g.get("arena"),
            "city": (g.get("arena") or {}).get("city") if isinstance(g.get("arena"), dict) else None,
            "competition": competition,
            "source_url": prov["source_url"],
            "capture": prov,
        }
        fixtures.append(entry)
        if g.get("played") and isinstance(entry["home_score"], int) and isinstance(entry["away_score"], int):
            for name, pf, pa in ((home["name"], entry["home_score"], entry["away_score"]),
                                 (away["name"], entry["away_score"], entry["home_score"])):
                r = ratings.setdefault(name, {"name": name, "played": 0, "wins": 0, "losses": 0, "pf": 0, "pa": 0,
                                              "source_url": prov["source_url"]})
                r["played"] += 1
                r["pf"] += pf
                r["pa"] += pa
                r["wins"] += 1 if pf > pa else 0
                r["losses"] += 1 if pf <= pa else 0
    for r in ratings.values():
        n = r["played"]
        r["pf_pg"] = r["pf"] / n if n else None
        r["pa_pg"] = r["pa"] / n if n else None
        r["diff_pg"] = (r["pf"] - r["pa"]) / n if n else None
        r["win_pct"] = r["wins"] / n if n else None
    return {"fixtures": fixtures, "ratings": ratings, "competition": competition, "source": prov}


# ============================================================== baseball — MLB
def mlb(cap: Capture) -> dict:
    sched_prov = cap.provenance("mlb_ws_schedule")
    sched = cap.json("mlb_ws_schedule")
    fixtures = []
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            teams = g.get("teams") or {}
            home = (teams.get("home") or {}).get("team") or {}
            away = (teams.get("away") or {}).get("team") or {}
            fixtures.append(
                {
                    "id": f"mlb-{g['gamePk']}",
                    "game_pk": g["gamePk"],
                    "start_utc": g.get("gameDate"),
                    "official_date": g.get("officialDate"),
                    "status": (g.get("status") or {}).get("detailedState"),
                    "abstract_state": (g.get("status") or {}).get("abstractGameState"),
                    "game_type": g.get("gameType"),
                    "series": g.get("seriesDescription"),
                    "series_game_number": g.get("seriesGameNumber"),
                    "if_necessary": g.get("ifNecessary"),
                    "venue": (g.get("venue") or {}).get("name"),
                    "home": home.get("name"),
                    "away": away.get("name"),
                    "home_id": home.get("id"),
                    "away_id": away.get("id"),
                    "source_url": f"https://www.mlb.com/game/{g.get('gameDate','')[:10].replace('-','/')}/{g['gamePk']}",
                    "games_page": f"https://www.mlb.com/postseason",
                    "feed_url": sched_prov["source_url"],
                    "capture": sched_prov,
                }
            )
    # season team stats — runs scored / allowed per game, from the official teams/stats endpoint
    ratings: dict[str, dict] = {}
    for target, group in (("mlb_hitting_2026", "hitting"), ("mlb_pitching_2026", "pitching")):
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        data = cap.json(target)
        for split in data.get("stats", []):
            for team in split.get("splits", []):
                name = (team.get("team") or {}).get("name")
                if not name:
                    continue
                r = ratings.setdefault(name, {"name": name, "source_url": prov["source_url"]})
                s = team.get("stat") or {}
                if group == "hitting":
                    r["runs"] = _num(s.get("runs"))
                    r["games_hitting"] = _num(s.get("gamesPlayed"))
                    r["hitting_rank"] = team.get("rank")
                    r["avg"] = s.get("avg")
                    r["obp"] = s.get("obp")
                    r["slg"] = s.get("slg")
                    r["ops"] = s.get("ops")
                    r["home_runs"] = _num(s.get("homeRuns"))
                else:
                    r["runs_allowed"] = _num(s.get("runs"))
                    r["era"] = s.get("era")
                    r["whip"] = s.get("whip")
                    r["games_pitching"] = _num(s.get("gamesPlayed"))
                    r["strikeouts_per9"] = s.get("strikeOutsPer9Inn")
    if cap.have("mlb_standings_2026"):
        prov = cap.provenance("mlb_standings_2026")
        for rec in cap.json("mlb_standings_2026").get("records", []):
            for row in rec.get("teamRecords", []):
                name = (row.get("team") or {}).get("name")
                if not name:
                    continue
                r = ratings.setdefault(name, {"name": name, "source_url": prov["source_url"]})
                r["wins"] = row.get("wins")
                r["losses"] = row.get("losses")
                r["win_pct"] = _num((row.get("winPercentage") or "").lstrip("."))
                r["runs_diff"] = row.get("runDifferential")
                r["division"] = (rec.get("division") or {}).get("name")
                r["league"] = (rec.get("league") or {}).get("name")
                r["standings_url"] = prov["source_url"]
    return {"fixtures": fixtures, "ratings": ratings, "schedule_source": sched_prov}


def _num(value):
    try:
        if value is None or value == "":
            return None
        f = float(value)
        return int(f) if f == int(f) else f
    except (TypeError, ValueError):
        return None


# ============================================================== tennis — WTA official feed
def wta(cap: Capture) -> dict:
    out = []
    for target in cap.ids():
        m = re.fullmatch(r"wta_(\d+)_matches", target)
        if not m:
            continue
        payload = cap.json(target)
        matches = payload.get("matches") or []
        if not matches:
            continue
        prov = cap.provenance(target)
        tour = payload.get("tournament") or {}
        tg = tour.get("tournamentGroup") or {}
        for mt in matches:
            if mt.get("DrawMatchType") != "S":
                continue
            state = mt.get("MatchState")
            if state not in ("U", "I", "S"):
                continue
            first_a, last_a = mt.get("PlayerNameFirstA") or "", mt.get("PlayerNameLastA") or ""
            first_b, last_b = mt.get("PlayerNameFirstB") or "", mt.get("PlayerNameLastB") or ""
            pa = f"{first_a} {last_a}".strip()
            pb = f"{first_b} {last_b}".strip()
            if not pa or not pb or pa.lower() in ("bye", "tbd") or pb.lower() in ("bye", "tbd"):
                continue
            ts = mt.get("MatchTimeStamp") or ""
            out.append(
                {
                    "id": f"wta-{tg.get('id')}-{mt.get('MatchID')}",
                    "tournament": tour.get("title") or tg.get("name"),
                    "tournament_id": tg.get("id"),
                    "level": tg.get("level") or tour.get("level"),
                    "city": tour.get("city"),
                    "country": tour.get("country"),
                    "surface": tour.get("surface"),
                    "event_start": tour.get("startDate"),
                    "event_end": tour.get("endDate"),
                    "start_raw": ts,
                    "start_utc": _iso_from_offset(ts),
                    "round": "Qualifying" if mt.get("DrawLevelType") == "Q" else "Main draw",
                    "round_id": mt.get("RoundID"),
                    "player_a": pa,
                    "player_b": pb,
                    "seed_a": mt.get("SeedA") or None,
                    "seed_b": mt.get("SeedB") or None,
                    "country_a": mt.get("PlayerCountryA"),
                    "country_b": mt.get("PlayerCountryB"),
                    "court": mt.get("CourtName"),
                    "not_before": mt.get("NotBefore"),
                    "source_url": f"https://www.wtatennis.com/tournaments/{tg.get('name','').lower().replace(' ','-')}",
                    "feed_url": prov["source_url"],
                    "capture": prov,
                }
            )
    return {"matches": out}


def _iso_from_offset(value: str) -> str | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================== volleyball — Lega Serie A
def legavolley(cap: Capture) -> dict:
    """Italian SuperLega table, decoded cell-by-cell from the official Lega Pallavolo Serie A page."""
    prov = cap.provenance("legavolley_classifica")
    tables = html_tables(cap.text("legavolley_classifica"))
    standings = []
    for tbl in tables:
        for row in tbl:
            if len(row) < 15 or not re.match(r"^\d+\s+\S", row[0]):
                continue
            head = row[0].split(" ", 1)
            rank = _num(head[0])
            team = head[1].strip() if len(head) > 1 else ""
            if not team:
                continue
            standings.append(
                {
                    "rank": rank,
                    "team": team,
                    "points": _num(row[1]),
                    "played": _num(row[2]),
                    "won": _num(row[3]),
                    "lost": _num(row[4]),
                    "won_3_0": _num(row[5]),
                    "won_3_1": _num(row[6]),
                    "won_3_2": _num(row[7]),
                    "lost_2_3": _num(row[8]),
                    "lost_1_3": _num(row[9]),
                    "lost_0_3": _num(row[10]),
                    "sets_won": _num(row[11]),
                    "sets_lost": _num(row[12]),
                    "points_for": _num(row[13]),
                    "points_against": _num(row[14]),
                    "source_url": prov["source_url"],
                }
            )
        if standings:
            break
    for r in standings:
        n = r["played"] or 0
        r["points_for_pg"] = (r["points_for"] / n) if n and r["points_for"] is not None else None
        r["points_against_pg"] = (r["points_against"] / n) if n and r["points_against"] is not None else None
        r["sets_won_pg"] = (r["sets_won"] / n) if n and r["sets_won"] is not None else None
        r["sets_lost_pg"] = (r["sets_lost"] / n) if n and r["sets_lost"] is not None else None
    updated = None
    m = re.search(r"Classifica aggiornata al (\d{2}/\d{2}/\d{4})", to_text(cap.text("legavolley_classifica")))
    if m:
        updated = m.group(1)
    grid = _legavolley_grid(cap, standings)
    return {
        "standings": standings,
        "table_updated": updated,
        "table_source": prov,
        "grid": grid["fixtures"],
        "grid_results": grid["results"],
        "short_to_full": grid["short_to_full"],
        "grid_source": grid["source"],
    }


def _match_short(short: str, standings: list[dict]) -> str | None:
    """Map the grid's one-word club alias (``Civitanova``) onto the official table name
    (``Cucine Lube Civitanova``) by matching a single distinctive word, case-insensitively."""
    if not short:
        return None
    low = short.lower()
    for row in standings:
        name = row.get("team") or ""
        words = [w for w in re.split(r"[\s'\u2019\-]+", name.lower()) if len(w) > 3]
        if low in name.lower() or any(w == low for w in words):
            return name
    return None


# the Lega grid prints dates with ENGLISH three-letter month names, the rest of the site is Italian
MONTHS_IT = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    "gen": 1, "mag": 5, "giu": 6, "lug": 7, "ago": 8, "set": 9, "ott": 10, "dic": 12,
}


def _legavolley_grid(cap: Capture, standings: list[dict]) -> dict:
    """The official `Griglia Campionato` matrix: rows = home side, columns = away side, each cell
    holds either the played score (e.g. ``3-0``) or the scheduled date (e.g. ``25 oct``)."""
    out = {"fixtures": [], "results": [], "short_to_full": {}, "source": None}
    for target in ("legavolley_risultati", "legavolley_classifica"):
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        out["source"] = prov
        header = None
        rows = None
        for tbl in html_tables(cap.text(target)):
            if len(tbl) < 3:
                continue
            flat = " ".join(c for r in tbl[:2] for c in r).lower()
            if "griglia" not in flat:
                continue
            for cand in tbl[:4]:
                if len(cand) < 8:
                    continue
                # the header row is the one whose cells are club aliases, not scores or dates
                hits = sum(1 for c in cand[1:] if _match_short(c.strip(), standings))
                if hits >= 8:
                    header = cand
                    rows = [r for r in tbl if len(r) >= len(cand)]
                    break
            if header:
                break
        if not header:
            continue
        away_names = [c.strip() for c in header[1:] if c.strip()]
        shorts = set(away_names)
        short_to_full = {short: _match_short(short, standings) for short in shorts}
        # "Trento" is the city the club is known by locally; the official table calls it Itas Trentino
        for short, full in list(short_to_full.items()):
            if full is None:
                for row in standings:
                    if short.lower() in (row.get("team") or "").lower():
                        short_to_full[short] = row["team"]
                        break
        out["short_to_full"] = short_to_full
        for row in rows:
            home_short = row[0].strip()
            if home_short not in shorts:
                continue
            for j, away_short in enumerate(away_names):
                cell = row[j + 1].strip() if j + 1 < len(row) else ""
                if not cell or home_short == away_short:
                    continue
                entry = {
                    "home_short": home_short,
                    "away_short": away_short,
                    "home": short_to_full.get(home_short) or home_short,
                    "away": short_to_full.get(away_short) or away_short,
                    "source_url": prov["source_url"],
                    "capture": prov,
                }
                score = re.fullmatch(r"(\d)\s*-\s*(\d)", cell)
                if score:
                    entry.update({"sets_home": int(score.group(1)), "sets_away": int(score.group(2)),
                                  "played": True})
                    out["results"].append(entry)
                    continue
                dm = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3})", cell)
                if dm:
                    mon = MONTHS_IT.get(dm.group(2).lower())
                    if mon:
                        # 2026/27 season: Jul-Dec cells are 2026, Jan-Jun cells are 2027
                        year = 2027 if mon <= 6 else 2026
                        entry.update({"date": f"{year}-{mon:02d}-{int(dm.group(1)):02d}", "played": False})
                        out["fixtures"].append(entry)
        if out["fixtures"] or out["results"]:
            break
    return out


# ============================================================== handball — Danish league + EHF CL
def handball_denmark(cap: Capture) -> dict:
    prov = cap.provenance("tophaandbold_herreligaen")
    tables = html_tables(cap.text("tophaandbold_herreligaen"))
    standings = []
    for tbl in tables:
        if not tbl or len(tbl) < 5:
            continue
        head = " ".join(tbl[0]).lower()
        if "klub" not in head or "point" not in head:
            continue
        for row in tbl[1:]:
            if len(row) < 7:
                continue
            goal = row[6].replace(" ", "")
            gf, _, ga = goal.partition("-")
            standings.append(
                {
                    "rank": _num(row[0]),
                    "team": row[1].strip(),
                    "played": _num(row[2]),
                    "wins": _num(row[3]),
                    "draws": _num(row[4]),
                    "losses": _num(row[5]),
                    "goals_for": _num(gf),
                    "goals_against": _num(ga),
                    "points": _num(row[7]),
                    "form": row[8] if len(row) > 8 else None,
                    "source_url": prov["source_url"],
                    "raw_row": row,
                }
            )
        if standings:
            break
    return {"standings": standings, "source": prov}


def handball_ehfcl(cap: Capture) -> dict:
    out = {"matches": [], "source": None}
    for target in ("ehfcl_matches_m", "ehfcl_matches_w"):
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        text = cap.text(target)
        out["source"] = prov
        # EHF renders match cards server-side with team names and dates
        for m in re.finditer(
            r'(<div[^>]*class="[^"]*match[^"]*"[^>]*>.*?</div>\s*</div>)', strip_scripts(text), flags=re.S
        ):
            out["matches"].append(to_text(m.group(1))[:200])
        break
    return out


# ============================================================== rugby union — URC article
def urc(cap: Capture) -> dict:
    prov = cap.provenance("urc_fixtures_in_full")
    text = to_text(cap.text("urc_fixtures_in_full"), keep_newlines=True)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    rounds: dict[str, list[dict]] = {}
    current_round = None
    current_day = None
    i = 0
    round_re = re.compile(r"^ROUND (\d+)$", re.I)
    day_re = re.compile(r"^(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s+([A-Z]+)\s+(\d{1,2})$", re.I)
    months = {m: n + 1 for n, m in enumerate(
        ["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"])}
    while i < len(lines):
        line = lines[i]
        m = round_re.match(line)
        if m:
            current_round = f"Round {m.group(1)}"
            rounds.setdefault(current_round, [])
            i += 1
            continue
        m = day_re.match(line)
        if m:
            month = months.get(m.group(2).upper())
            current_day = f"2026-{month:02d}-{int(m.group(3)):02d}" if month else None
            i += 1
            continue
        if current_round and current_day and " v " in line and not line.lower().startswith("live on"):
            home, away = [s.strip() for s in line.split(" v ", 1)]
            venue = lines[i + 1] if i + 1 < len(lines) else ""
            ko = None
            km = re.search(r"KO\s+(\d{1,2}[.:]\d{2})", venue)
            if km:
                ko = km.group(1).replace(".", ":")
            venue_name = venue.split(", KO")[0].strip()
            rounds[current_round].append(
                {
                    "round": current_round,
                    "date": current_day,
                    "home": home,
                    "away": away,
                    "venue": venue_name,
                    "ko_local": ko,
                    "ko_timezone": "IRE & UK local" if ko else None,
                    "source_url": prov["source_url"],
                    "capture": prov,
                }
            )
            i += 2
            continue
        i += 1
    return {"rounds": rounds, "source": prov}


# ============================================================== rugby league — RLWC 2026
def rlwc_games(cap: Capture, target: str = "rlwc_draws") -> list[dict]:
    """Read every fixture out of the official RLWC26 fixture blob embedded in rlwc2026.com.

    The page ships `fixturesByComp` as an escaped JSON string. Each game carries gameId, round,
    pool, both team names, the UTC start, venue, city, the match-centre URL, the ticket URL and the
    broadcast list. There is deliberately no score field, so this source cannot produce a rating.
    """
    if not cap.have(target):
        return []
    prov = cap.provenance(target)
    text = cap.text(target)
    body = text
    for _ in range(5):
        nxt = body.replace("\\\\\"", '"').replace('\\"', '"').replace('\\"', '"')
        if nxt == body:
            break
        body = nxt
    out: list[dict] = []
    seen = set()
    # split the blob into one segment per game so no field can bleed into the next fixture
    starts = [m.start() for m in re.finditer(r'\{"gameId":"\d+"', body)]
    if not starts:
        starts = [m.start() for m in re.finditer(r'"gameId":"\d+"', body)]
    for i, pos in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(body)
        seg = body[pos:end]
        gid_m = re.search(r'"gameId":"(\d+)"', seg)
        if not gid_m:
            continue
        gid = gid_m.group(1)
        if gid in seen:
            continue

        def field(name: str) -> str | None:
            fm = re.search(r'"%s":"([^"]*)"' % name, seg)
            return fm.group(1) if fm else None

        start = field("startTimeUTC") or field("startTime")
        venue = field("venueName")
        city = field("city")
        rnd = field("roundName")
        state = field("gameStateName")
        mc = field("matchCentreUrl")
        ticket = field("ticketUrl")
        described = field("game")
        home_flag = re.findall(r'"isHomeTeam":(true|false),"teamId":"\d+","teamName":"([^"]+)"', seg)
        home = away = None
        for is_home, name in home_flag[:2]:
            if is_home == "true":
                home = name
            else:
                away = name
        if not home:
            names = re.findall(r'"teamName":"([^"]+)"', seg)
            if len(names) >= 2:
                home, away = names[0], names[1]
        if not (home and away and start):
            continue
        # the team names are authoritative: the organiser labels wheelchair and women's sides explicitly
        joined = f"{home} {away} {described or ''}"
        if "wheelchair" in joined.lower():
            comp = "RLWC26 Wheelchair"
        elif (mc and "/women/" in mc) or re.search(r"\bWomen\b", described or ""):
            comp = "RLWC26 Women"
        else:
            comp = "RLWC26 Men"
        seen.add(gid)
        out.append({
            "game_id": gid, "competition": comp, "round": rnd, "pool": _group(seg),
            "home": home, "away": away, "start_utc": start.replace(".000Z", "Z"),
            "venue": venue, "city": city, "state": state, "event_name": f"{home} v {away}",
            "match_centre_url": ("https://www.rlwc2026.com" + mc) if mc else None,
            "ticket_url": (ticket or "").replace("\\u0026", "&"), "organiser_description": described,
            "broadcasters": re.findall(r'"channelName":"([^"]+)"', seg)[:6],
            "source_url": prov["source_url"], "capture": prov,
        })
    return out


def _group(seg: str) -> str | None:
    m = re.search(r'"group":(\d+)', seg)
    return f"Pool {m.group(1)}" if m else None


# ============================================================== snooker — draw sheets
SNOOKER_EVENT_TARGETS = sorted({f"snooker_org_{n}" for n in range(2536, 2561)})


def snooker_events(cap: Capture, season: str = "2026/2027") -> list[dict]:
    """Parse every 2026/27 event sheet on snooker.org for the matches still to be played.

    A sheet publishes the stage ("Final (Best of 17; Winner: GBP100,000 ...)"), each pairing with
    the official world-ranking seed in brackets, the score where the match is complete and the UTC
    start where one is scheduled.
    """
    out = []
    for target in SNOOKER_EVENT_TARGETS:
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        text = cap.text(target)
        title = _snooker_title(text)
        if not title:
            continue
        if season not in text:
            continue
        dates = None  # the sheet prints other events' date ranges in its sidebar; not published here
        tables = [t for t in html_tables(text) if len(t) > 6]
        if not tables:
            continue
        upcoming, completed = [], []
        current_stage: dict = {"stage": None, "best_of": None, "prize": None}
        # a sheet holds the main draw and, on the same page, the qualifying draw; parse every table
        for draw in tables:
          for row in draw:
            joined = " ".join(row)
            sm = re.search(r"^(Final|Semi-?finals?|Quarter-?finals?|Round \d+|Last \d+)\s*\(([^)]*)\)",
                           joined, flags=re.I)
            if sm:
                stage = sm.group(1)
                bm = re.search(r"Best of (\d+)", sm.group(2), flags=re.I)
                best_of = bm.group(1) if bm else None
                prize = None
                pm = re.search(r"Winner:\s*\u00a3?([\d,]+)", sm.group(2))
                if pm:
                    prize = pm.group(1)
                current_stage = {"stage": stage, "best_of": best_of, "prize": prize}
                continue
            if len(row) < 4:
                continue
            # snooker.org prints a match to be played as  [blank, blank, PLAYER A, blank, "v", blank,
            # blank, PLAYER B, blank, ISO times] and a completed match as
            # [blank, blank, PLAYER A, frames, "-", frames, blank, PLAYER B, blank, blank].
            cells = [(i, c.strip()) for i, c in enumerate(row) if c.strip()]
            named = [(i, c) for i, c in cells if _snooker_is_player(c)]
            if len(named) < 2:
                continue
            ia, pa_raw = named[0]
            ib, pb_raw = named[1]
            between = [c for i, c in cells if ia < i < ib]
            dash = next((k for k, c in enumerate(between) if c == "-"), None)
            if not between or not all(re.fullmatch(r"\d{1,3}|-", c) for c in between):
                between_are_score = False
            else:
                between_are_score = True
            vi = next((i for i, c in cells if c.lower() == "v"), None)
            score = None
            if between_are_score and dash is not None:
                score = f"{between[dash - 1]}-{between[dash + 1]}"
            times = [c for i, c in cells if re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}Z", c)]
            if not times and not score:
                continue
            pa = _snooker_player(row, ia)
            pb = _snooker_player(row, ib)
            if not pa["name"] or not pb["name"]:
                continue
            if "to be decided" in f'{pa["name"]} {pb["name"]}'.lower():
                continue  # the sheet has not resolved this pairing yet
            entry = {
                "stage": current_stage.get("stage"),
                "best_of": current_stage.get("best_of"),
                "prize": current_stage.get("prize"),
                "player_a": pa["name"], "seed_a": pa["seed"], "country_a": pa["country"],
                "player_b": pb["name"], "seed_b": pb["seed"], "country_b": pb["country"],
                "score": score,
                "start_utc": times[0].replace(" ", "T") if times else None,
                "local_start": times[1].replace(" ", "T") if len(times) > 1 else None,
                "path_a": [], "path_b": [],
            }
            if times and not score:
                upcoming.append(entry)
            elif score:
                completed.append(entry)
        # each player's route to this round, from the same official sheet
        for entry in upcoming:
            entry["path_a"] = _snooker_path(entry["player_a"], completed)
            entry["path_b"] = _snooker_path(entry["player_b"], completed)
        if not upcoming:
            continue
        out.append({
            "event_target": target, "event_name": title, "dates": dates,
            "venue": _snooker_venue(text), "upcoming": upcoming, "completed": completed,
            "source_url": prov["source_url"], "capture": prov,
        })
    return out


def _snooker_dates(text: str) -> str | None:
    """The event's own date range, taken from the sheet's info block rather than the site navigation."""
    plain = to_text(text)
    for pattern in (r"Dates?\s*[:\-]\s*(\d{1,2}\s+[A-Z][a-z]+\s*[-\u2013]\s*\d{1,2}\s+[A-Z][a-z]+\s+\d{4})",
                    r"(\d{1,2}\s+[A-Z][a-z]+\s*[-\u2013]\s*\d{1,2}\s+[A-Z][a-z]+\s+\d{4})"):
        for m in re.finditer(pattern, plain):
            candidate = m.group(1)
            if "Jun" in candidate or "Jul" in candidate or "Sep" in candidate:
                continue  # the site sidebar lists other events' dates first
            return candidate
    return None


def _snooker_title(text: str) -> str | None:
    m = re.search(r"<title>\s*(.*?)\s*-\s*snooker\.org", text, flags=re.S)
    if not m:
        return None
    return html_unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()


def html_unescape(value: str) -> str:
    return (value.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8209;", "-")
            .replace("&pound;", "\u00a3").replace("&#8217;", "'").replace("\xa0", " "))


def _snooker_is_player(cell: str) -> bool:
    """True for a cell that holds a competitor name rather than a score, a seed or a timestamp."""
    if not cell or re.fullmatch(r"[\d\s\-]+", cell):
        return False
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2}Z)?", cell):
        return False
    if len(cell) <= 2:
        return False
    return bool(re.search(r"[A-Za-z]", cell))


def _snooker_player(row: list[str], index: int) -> dict:
    if index >= len(row):
        return {"name": None, "seed": None, "country": None}
    raw = (row[index] or "").strip()
    m = re.match(r"^(.*?)\s*\[(\d+)\]\s*$", raw)
    country = None
    for back in range(index - 1, max(index - 3, -1), -1):
        cand = (row[back] or "").strip()
        if cand and len(cand) <= 4 and cand.isalpha():
            country = cand
            break
    if m:
        return {"name": m.group(1).strip(), "seed": int(m.group(2)), "country": country}
    return {"name": raw or None, "seed": None, "country": country}


def _snooker_path(player: str, completed: list[dict]) -> list[str]:
    out = []
    for m in completed:
        if m["player_a"] == player:
            out.append(f'{m["stage"]}: {m["score"]} v {m["player_b"]}')
        elif m["player_b"] == player:
            out.append(f'{m["stage"]}: {m["score"]} (as second listed) v {m["player_a"]}')
    return out


def _snooker_venue(text: str) -> str | None:
    plain = to_text(text)
    m = re.search(r"(Waterfront Hall[^.\n]{0,60}|Venue[:\s]+[^\n]{3,80})", plain)
    return m.group(1).strip() if m else None


# ============================================================== golf — PGA Tour leaderboard
def golf_pga(cap: Capture, target: str) -> dict:
    """The PGA Tour leaderboard page embeds a schema.org/csvw dataset with the exact leaderboard:
    POS, PLAYER, TOT, THRU, R1, R2, R3, R4. Every value below is read out of that dataset."""
    if not cap.have(target):
        return {}
    prov = cap.provenance(target)
    text = cap.text(target)
    m = re.search(r'<script id="leaderboard-seo-data" type="application/ld\+json">(.*?)</script>', text, flags=re.S)
    rows: list[dict] = []
    description = None
    name = None
    if m:
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            data = None
        if data:
            description = data.get("description")
            name = data.get("name")
            cols = (((data.get("mainEntity") or {}).get("csvw:tableSchema") or {}).get("csvw:columns")) or []
            table = {c.get("csvw:name"): [x.get("csvw:value") for x in (c.get("csvw:cells") or [])] for c in cols}
            n = max((len(v) for v in table.values()), default=0)
            for i in range(n):
                row = {k: (v[i] if i < len(v) else None) for k, v in table.items()}
                rows.append(row)
    # tournament metadata from the Next.js page props
    meta = {}
    nm = re.search(r'"tournamentName":"([^"]+)"', text)
    if nm:
        meta["tournamentName"] = nm.group(1)
    for key in ("tournamentLocation", "tournamentStatus", "tournamentId", "roundNumber", "courseName"):
        km = re.search(r'"%s":"?([^",}]+)' % key, text)
        if km:
            meta[key] = km.group(1)
    return {"rows": rows, "meta": meta, "dataset_name": name, "dataset_description": description,
            "source_url": prov["source_url"], "capture": prov, "raw_len": len(text)}


# ============================================================== motor racing — F1
F1_MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
             "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}


def f1_calendar(cap: Capture) -> list[dict]:
    """The official 2026 race index: ROUND n / country / date range, plus its Upcoming marker."""
    if not cap.have("f1_racing_2026"):
        return []
    prov = cap.provenance("f1_racing_2026")
    body = re.sub(r"<script\b.*?</script>", " ", cap.text("f1_racing_2026"), flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = body.replace("&nbsp;", " ").replace("&amp;", "&").replace("\xa0", " ")
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    out = []
    for i, line in enumerate(lines):
        m = re.fullmatch(r"ROUND (\d{1,2})", line)
        if not m:
            continue
        window = lines[i + 1:i + 6]
        # the race index prints two listings; the authoritative one carries the FIA event name
        fi = next((k for k, w in enumerate(window) if re.match(r"^FORMULA 1\b", w)), None)
        if fi is None:
            continue
        full = window[fi]
        span = next((w for w in window if re.match(r"^\d{2}\s*-\s*\d{2}", w)), None)
        country = next((w for w in window[:fi] if w and not w.startswith("Flag of")), None)
        if not (country and span):
            continue
        end_mon = end_day = None
        for tok in re.finditer(r"(?:(\d{2})\s+)?(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)", span):
            end_mon = F1_MONTHS.get(tok.group(2))
            end_day = int(tok.group(1)) if tok.group(1) else None
        if end_day is None:
            dm = re.match(r"(\d{2})", span)
            end_day = int(dm.group(1)) if dm else None
        status = None
        for back in range(i - 1, max(i - 5, -1), -1):
            if lines[back] in ("Previous", "Current", "Upcoming"):
                status = lines[back]
                break
        out.append({
            "round": int(m.group(1)), "country": country, "event_name": full, "date_span": span,
            "end_date": f"2026-{end_mon:02d}-{end_day:02d}" if end_mon and end_day else None,
            "status": status,
            "source_url": prov["source_url"], "capture": prov,
        })
    deduped = {}
    for r in out:
        deduped.setdefault(r["round"], r)
    return [deduped[k] for k in sorted(deduped)]


def f1_standings(cap: Capture, target: str) -> dict:
    """formula1.com renders its championship tables server-side."""
    if not cap.have(target):
        return {"rows": []}
    prov = cap.provenance(target)
    rows = []
    for tbl in html_tables(cap.text(target)):
        if not tbl:
            continue
        head = [h.strip().lower() for h in tbl[0]]
        if "pts." not in head:
            continue
        for r in tbl[1:]:
            if len(r) < len(head):
                continue
            rec = dict(zip(head, [c.strip() for c in r]))
            if rec.get("pos."):
                rows.append(rec)
        if rows:
            break
    return {"rows": rows, "source_url": prov["source_url"], "capture": prov}


# ============================================================== darts — PDC sitemap (only server-rendered PDC asset)
def pdc_sitemap(cap: Capture) -> dict:
    if not cap.have("pdc_sitemap_news"):
        return {"urls": []}
    prov = cap.provenance("pdc_sitemap_news")
    urls = re.findall(r"<loc>\s*(.*?)\s*</loc>", cap.text("pdc_sitemap_news"), flags=re.S)
    return {"urls": urls, "source": prov}


# ============================================================== greyhounds — GBGB Cat-1 schedule
def gbgb_schedule(cap: Capture) -> dict:
    prov = cap.provenance("gbgb_cat1_schedule")
    text = cap.text("gbgb_cat1_schedule")
    body = strip_scripts(text)
    # each meeting is rendered as: <strong>Day DD Mon</strong> · Track · Race · Distance Type
    entries = []
    for m in re.finditer(
        r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        r"[\s·|]+([^<·|]{2,40})[\s·|]+([^<·|]{2,80})[\s·|]+(\d{2,4}m)\s*(Flat|Hurdles|Steeple|AOC|OR)?",
        to_text(body),
    ):
        entries.append(
            {
                "day": m.group(1),
                "date": m.group(2),
                "month": m.group(3),
                "track": m.group(4).strip(),
                "race": m.group(5).strip(),
                "distance": m.group(6).strip(),
                "type": (m.group(7) or "").strip(),
                "source_url": prov["source_url"],
                "capture": prov,
            }
        )
    return {"entries": entries, "text": to_text(body), "source": prov}


def gbgb_results(cap: Capture, target: str = "gbgb_results_api") -> dict:
    if not cap.have(target):
        return {"items": []}
    prov = cap.provenance(target)
    payload = cap.json(target)
    return {"items": payload.get("items", []), "source": prov}


# ============================================================== gaelic — county boards
GAA_COUNTIES = {
    "mayogaa_fixtures": ("Mayo", "https://mayogaa.com/fixtures/"),
    "claregaa_fixtures": ("Clare", "https://clare.gaa.ie/fixtures-results/"),
    "leitrimgaa_fixtures": ("Leitrim", "https://www.leitrimgaa.ie/fixtures-next-10-days/"),
    "ulstergaa_fixtures": ("Ulster", "https://ulster.gaa.ie/fixtures/"),
    "kilkennygaa_fixtures": ("Kilkenny", "https://kilkennygaa.ie/fixtures-results/"),
    "gaacork_fixtures": ("Cork", "https://gaacork.ie/fixtures"),
    "gaakerry_fixtures": ("Kerry", "https://kerrygaa.ie/fixtures"),
}


def gaa(cap: Capture) -> dict:
    out = []
    for target, (county, url) in GAA_COUNTIES.items():
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        text = strip_scripts(cap.text(target))
        # common county-board pattern: a fixture block with two club names and a date/time
        rows = []
        for tbl in html_tables(text):
            for row in tbl:
                if len(row) >= 3:
                    rows.append(row)
        out.append({"county": county, "page_url": url, "capture": prov, "table_rows": rows,
                    "text": to_text(text)[:20000], "raw_len": len(text)})
    return {"boards": out}


# ============================================================== cricket
def cricket_boards(cap: Capture) -> dict:
    wanted = {
        "eci_fixtures": ("Cricket Ireland", "https://www.cricketireland.ie/fixtures"),
        "ecb_england_fixtures": ("England & Wales Cricket Board", "https://www.ecb.co.uk/england/men/fixtures"),
        "cwi_fixtures": ("Cricket West Indies", "https://www.windiescricket.com/fixtures/"),
        "icc_fixtures_results": ("International Cricket Council", "https://www.icc-cricket.com/fixtures-results"),
        "bcci_fixtures": ("Board of Control for Cricket in India", "https://www.bcci.tv/international/fixtures"),
        "nzc_matches": ("New Zealand Cricket", "https://www.nzc.nz/matches"),
        "cricket_au_fixtures": ("Cricket Australia", "https://www.cricket.com.au/fixtures"),
        "ca_series": ("Cricket Australia", "https://www.cricket.com.au/series"),
    }
    out = []
    for target, (org, url) in wanted.items():
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        text = cap.text(target)
        out.append({
            "target": target,
            "organisation": org,
            "page_url": url,
            "capture": prov,
            "raw_len": len(text),
            "text": to_text(text)[:30000],
            "tables": [t for t in html_tables(text) if len(t) > 2][:6],
        })
    return {"boards": out}


def load_all(cap: Capture) -> dict:
    return {
        "nhl": nhl(cap),
        "liiga": liiga(cap),
        "shl": shl(cap),
        "euroleague": euroleague(cap, "euroleague_games_E2026", "EuroLeague"),
        "eurocup": euroleague(cap, "eurocup_games_U2026", "EuroCup"),
        "mlb": mlb(cap),
        "wta": wta(cap),
        "legavolley": legavolley(cap),
        "handball_denmark": handball_denmark(cap),
        "handball_ehfcl": handball_ehfcl(cap),
        "urc": urc(cap),
        "rlwc": rlwc(cap),
        "pga_bermuda": golf_pga(cap, "pgatour_bermuda"),
        "pga_leaderboard": golf_pga(cap, "pgatour_leaderboard"),
        "dpwt_leaderboard": golf_pga(cap, "dpwt_leaderboard"),
        "f1_drivers": f1_standings(cap, "f1_drivers_2026"),
        "f1_constructors": f1_standings(cap, "f1_constructors_2026"),
        "gbgb_schedule": gbgb_schedule(cap),
        "gbgb_results": gbgb_results(cap),
        "gaa": gaa(cap),
        "cricket": cricket_boards(cap),
    }


# ============================================================== fixture readers for the boards that
# ============================================================== publish their lists server-side
GAA_FIXTURE_BOARDS = {
    "mayogaa_fixtures": ("Mayo GAA", "https://mayogaa.com/fixtures/"),
    "claregaa_fixtures": ("Clare GAA", "https://clare.gaa.ie/fixtures-results/"),
    "leitrimgaa_fixtures": ("Leitrim GAA", "https://www.leitrimgaa.ie/fixtures-next-10-days/"),
    "ulstergaa_fixtures": ("Ulster GAA", "https://ulster.gaa.ie/fixtures/"),
    "kilkennygaa_fixtures": ("Kilkenny GAA", "https://kilkennygaa.ie/fixtures-results/"),
    "gaacork_fixtures": ("Cork GAA", "https://gaacork.ie/fixtures"),
    "gaakerry_fixtures": ("Kerry GAA", "https://kerrygaa.ie/fixtures"),
}

GAA_MONTHS = {m: n + 1 for n, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def _gaa_lines(text: str) -> list[str]:
    body = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    body = re.sub(r"<style\b.*?</style>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", "\n", body)
    body = (body.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'")
            .replace("\xa0", " "))
    return [l.strip() for l in body.split("\n") if l.strip()]


def gaa_fixtures(cap: Capture) -> list[dict]:
    """Read the fixture blocks a county board renders server-side.

    The block layout on every board tested is:
    ``<competition>`` / ``<DD Mon YYYY>`` / ``<HH:MM>`` / ``<home>`` / ``V`` / ``<away>`` /
    ``<venue>`` / ``Time: HH:MM`` / ``Venue: <ground>`` / ``Referee: <name>`` / ``Comment: <round>``.
    """
    out = []
    seen = set()
    for target, (org, url) in sorted(GAA_FIXTURE_BOARDS.items()):
        if not cap.have(target):
            continue
        prov = cap.provenance(target)
        lines = _gaa_lines(cap.text(target))
        for i, line in enumerate(lines):
            if line != "V":
                continue
            home = lines[i - 1] if i >= 1 else None
            away = lines[i + 1] if i + 1 < len(lines) else None
            if not home or not away or len(home) < 2 or len(away) < 2:
                continue
            if home in ("Team1", "Home") or away in ("Team2", "Away"):
                continue
            date = time = competition = venue = referee = comment = None
            for back in range(i - 2, max(i - 9, -1), -1):
                cand = lines[back]
                dm = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", cand)
                if dm and date is None:
                    mon = GAA_MONTHS.get(dm.group(2))
                    if mon:
                        date = f"{dm.group(3)}-{mon:02d}-{int(dm.group(1)):02d}"
                        if back - 1 >= 0 and competition is None:
                            competition = lines[back - 1]
                    continue
                tm = re.fullmatch(r"\d{2}:\d{2}", cand)
                if tm and time is None and date is not None:
                    time = cand
            for fwd in range(i + 2, min(i + 12, len(lines))):
                cand = lines[fwd]
                if cand.startswith("Time:") and time is None:
                    time = cand.split(":", 1)[1].strip()
                elif cand.startswith("Venue:"):
                    venue = cand.split(":", 1)[1].strip() or None
                elif cand.startswith("Referee:"):
                    referee = cand.split(":", 1)[1].strip() or None
                elif cand.startswith("Comment:"):
                    comment = cand.split(":", 1)[1].strip() or None
                elif venue is None and not cand.startswith("More") and cand != "-->":
                    venue = cand
            if not date:
                continue
            start = f"{date}T{time}:00Z" if time else None
            key = (org, date, home, away)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "county": org, "organisation": f"{org} (official county board)",
                "competition": competition, "event": f"{home} v {away}",
                "home": home, "away": away, "date": date, "time_local": time,
                "start_utc": None, "local_start": start, "venue": venue,
                "referee": referee, "round": comment,
                "source_url": url, "capture": prov,
                "timezone_note": "the county board publishes the throw-in in Irish local time; it does not "
                                 "publish a UTC time, so the UTC column is left empty rather than converted",
            })
    return out


def cricket_fixtures(cap: Capture) -> list[dict]:
    """Cricket fixture facts that are actually printed in the committed bytes of an official board page.

    Every board fixture list tested (icc-cricket.com, nzc.nz, cricket.com.au, ecb.co.uk, bcci.tv,
    cricketireland.ie, windiescricket.com) renders its match cards client-side, so the cards are not
    in the bytes the runner received. What IS in the bytes is the board's own editorial text, and
    that is what is published here, with the sentence it came from, so a reviewer can check it.
    """
    out = []
    if cap.have("nzc_matches"):
        prov = cap.provenance("nzc_matches")
        lines = _gaa_lines(cap.text("nzc_matches"))
        joined = " ".join(lines)
        found = set()
        for m in re.finditer(r"([^.\n]*(?:BLACKCAPS v India|BLACKCAPS\s+v\s+India|India T20Is)[^.\n]*)", joined):
            sentence = re.sub(r"\s+", " ", m.group(1)).strip()
            sentence = re.sub(r"^(?:\d{1,2} \w+, \d{4} in [\w ]+ )+(?:International News\s*)*", "", sentence).strip()
            sentence = sentence.replace("&#x2019;", "'").replace("&#8217;", "'")
            if len(sentence) < 40 or sentence[:120] in found:
                continue
            found.add(sentence[:120])
            venues = sorted({v for v in ("Hagley Oval", "Seddon Park", "Eden Park") if v in sentence})
            out.append({
                "competition": "BLACKCAPS v India T20I series 2026", "organisation": "New Zealand Cricket",
                "event": "BLACKCAPS v India — T20I series", "home": "New Zealand", "away": "India",
                "format": "T20I", "date": None, "start_utc": None,
                "venue": ", ".join(venues) if venues else None,
                "official_sentence": sentence[:400],
                "source_url": prov["source_url"], "capture": prov,
                "why_unpriced": "New Zealand Cricket renders its match cards client-side, so the per-match date, "
                                "start time and venue are not in the captured bytes; the series itself and its "
                                "venues are confirmed by NZC's own news items on that page. The ICC team-rating "
                                "endpoint was unreachable (icc-cricket.com/rankings/* is also a client-side app), "
                                "so there is no official rating input for a line either.",
            })
    return out


def gbgb_meetings(cap: Capture) -> list[dict]:
    """The Greyhound Board of Great Britain's own Category One calendar, as published."""
    out = []
    if not cap.have("gbgb_cat1_schedule"):
        return out
    prov = cap.provenance("gbgb_cat1_schedule")
    lines = _gaa_lines(cap.text("gbgb_cat1_schedule"))
    month_at = None
    for i, line in enumerate(lines):
        mm = re.fullmatch(r"(January|February|March|April|May|June|July|August|September|October|November|December)", line)
        if mm:
            month_at = mm.group(1)
            continue
        dm = re.fullmatch(r"(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+(\d{1,2})\s+([A-Za-z]{3})", line)
        if not dm:
            continue
        track = lines[i + 1] if i + 1 < len(lines) else None
        race = lines[i + 2] if i + 2 < len(lines) else None
        spec = lines[i + 3] if i + 3 < len(lines) else None
        if not track or not race:
            continue
        mon = GAA_MONTHS.get(dm.group(3))
        if not mon:
            continue
        date = f"2026-{mon:02d}-{int(dm.group(2)):02d}"
        distance = None
        rtype = None
        if spec:
            sm = re.match(r"(\d{2,4})m\s*(.*)", spec)
            if sm:
                distance, rtype = f"{sm.group(1)}m", sm.group(2).strip() or None
        out.append({
            "competition": "GBGB Category One open racing 2026",
            "event": f"{race} — {track}", "track": track, "race": race, "day": dm.group(1),
            "date": date, "start_utc": None, "distance": distance, "type": rtype,
            "month_heading": month_at,
            "source_url": prov["source_url"], "capture": prov,
        })
    return [m for m in out if "2026-10-23" <= m["date"] <= "2026-11-08"]

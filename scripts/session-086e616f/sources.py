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
def rlwc(cap: Capture) -> dict:
    prov = cap.provenance("rlwc_draws")
    text = cap.text("rlwc_draws")
    body = strip_scripts(text)
    plain = to_text(body)
    return {"text": plain, "source_url": prov["source_url"], "capture": prov, "html": body}


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

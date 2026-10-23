#!/usr/bin/env python3
"""Board AJ — feed parsers.

Each parser reads committed capture bytes and returns a list of fixture dicts:

    {sport, competition, start_utc, home, away, venue, source_url, source_id,
     inputs: {...}, tags: [...]}

Only values present in the captured official response are emitted. A field the feed does not
state is left as "" (never inferred), and the fixture is dropped if either side or the start
time cannot be read: a match we cannot date is not published as an upcoming fixture.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone

from models import Capture, parse_iso, utc_now

IN_WINDOW_END = datetime(2026, 11, 8, 23, 59, tzinfo=timezone.utc)


def _keep(start: datetime | None, now: datetime) -> bool:
    return bool(start) and now - timedelta(hours=6) <= start <= IN_WINDOW_END


# ----------------------------------------------------------------------------- OLBG taxonomy
def olbg_inventory(cap: Capture) -> dict:
    """Reverse-engineer the OLBG hub payload: events, market aliases and listed prices."""
    FIELD = re.compile(r'(?:^|[{,])\s*([a-z_]+):\s*(?:"([^"]*)"|(-?\d+(?:\.\d+)?)|null)')
    hubs = []
    for rec in cap.manifest["records"]:
        if rec.get("kind") != "listing" or not rec.get("file"):
            continue
        raw = cap.text(rec["id"])
        if not raw:
            continue
        m = re.search(r"tips:\[", raw)
        tips = []
        if m:
            body = raw[m.end() - 1:]
            for tm in re.finditer(r'\{id:"[0-9a-f]{40}",selection:"', body):
                chunk = body[tm.start(): tm.start() + 1800]
                chunk = chunk[:chunk.find("}") + 1]
                row = {}
                for fm in FIELD.finditer(chunk):
                    k, s, n = fm.group(1), fm.group(2), fm.group(3)
                    row[k] = s if s is not None else n
                if row.get("event_name_alias") and row.get("market_alias"):
                    tips.append(row)
        events: dict[str, dict] = {}
        for t in tips:
            name = t["event_name_alias"].strip()
            ev = events.setdefault(name, {"event": name, "start_utc": "", "markets": [], "tips": 0})
            ts = int(t.get("event_start_unix_timestamp") or 0)
            if ts:
                ev["start_utc"] = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            ev["markets"].append({
                "market": t.get("market_alias", ""),
                "selection": t.get("selection", ""),
                "decimal": t.get("odds", ""),
                "american": t.get("american_odds", ""),
                "win_tips": t.get("win_tips", ""),
                "confidence_pct": t.get("confidence", ""),
            })
            ev["tips"] += 1
        hubs.append({
            "sport": rec.get("sport", ""),
            "label": rec.get("label", ""),
            "hub_url": rec["url"],
            "capture_file": rec.get("file", ""),
            "sha256": rec.get("sha256", ""),
            "status": rec.get("status"),
            "events": sorted(events.values(), key=lambda e: (e["start_utc"], e["event"])),
            "event_count": len(events),
            "tip_count": len(tips),
            "market_aliases": sorted({t.get("market_alias", "") for t in tips}),
        })
    return {"hubs": hubs,
            "totals": {"hubs": len(hubs),
                       "events": sum(h["event_count"] for h in hubs),
                       "tips": sum(h["tip_count"] for h in hubs)}}


# ----------------------------------------------------------------------------- NHL
def nhl_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    standings = cap.json("nhl_standings_now") or {}
    teams: dict[str, dict] = {}
    for t in standings.get("standings", []):
        ab = t.get("teamAbbrev", {}).get("default") or t.get("teamAbbrev")
        name = t.get("teamName", {}).get("default") or t.get("teamName")
        if not ab:
            continue
        gp = max(t.get("gamesPlayed", 0), 1)
        teams[ab] = {
            "abbrev": ab, "name": name, "gp": t.get("gamesPlayed", 0),
            "w": t.get("wins", 0), "l": t.get("losses", 0), "otl": t.get("otLosses", 0),
            "pts": t.get("points", 0),
            "pts_pct": round(t.get("pointPctg", 0), 4),
            "gf": t.get("goalFor", 0), "ga": t.get("goalAgainst", 0),
            "gf_pg": round(t.get("goalFor", 0) / gp, 3),
            "ga_pg": round(t.get("goalAgainst", 0) / gp, 3),
            "l10_pts_pct": round((t.get("l10Points", 0) or 0) / max(2 * (t.get("l10GamesPlayed", 0) or 1), 1), 4),
            "home_record": f"{t.get('homeWins',0)}-{t.get('homeLosses',0)}-{t.get('homeOtLosses',0)}",
            "road_record": f"{t.get('roadWins',0)}-{t.get('roadLosses',0)}-{t.get('roadOtLosses',0)}",
            "source": cap.url("nhl_standings_now"),
        }
    now = utc_now()
    fixtures, used, skipped = [], [], []
    for rec in cap.manifest["records"]:
        if not rec["id"].startswith("nhl_sched_") or not rec.get("file"):
            continue
        data = cap.json(rec["id"])
        if not data:
            continue
        for week in data.get("gameWeek", []):
            for g in week.get("games", []):
                start = parse_iso(g.get("startTimeUTC", ""))
                if not _keep(start, now):
                    continue
                if g.get("gameState") not in ("FUT", "PRE"):
                    continue
                home, away = g["homeTeam"], g["awayTeam"]
                if home["abbrev"] not in teams or away["abbrev"] not in teams:
                    skipped.append(f"{rec['id']}: {away['abbrev']} @ {home['abbrev']} (no standings row)")
                    continue
                fixture = {
                    "sport": "Ice Hockey", "competition": "NHL",
                    "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "home": home["placeName"]["default"] + " " + home["commonName"]["default"],
                    "away": away["placeName"]["default"] + " " + away["commonName"]["default"],
                    "home_code": home["abbrev"], "away_code": away["abbrev"],
                    "venue": g.get("venue", {}).get("default", ""),
                    "source_url": "https://www.nhl.com" + g.get("gameCenterLink", ""),
                    "source_id": str(g.get("id", "")),
                    "inputs": {"home": teams[home["abbrev"]], "away": teams[away["abbrev"]],
                               "model": "nhl_goal_poisson", "standings_source": cap.url("nhl_standings_now"),
                               "schedule_source": rec["url"]},
                    "tags": ["regular-season"],
                }
                fixtures.append(fixture)
    return fixtures, teams, skipped


# ----------------------------------------------------------------------------- MLB
def mlb_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    standings = cap.json("mlb_standings") or {}
    teams: dict[int, dict] = {}
    for rec in standings.get("records", []):
        for t in rec.get("teamRecords", []):
            tid = t["team"]["id"]
            gp = max(t.get("gamesPlayed", 0), 1)
            teams[tid] = {
                "id": tid, "name": t["team"]["name"], "gp": t.get("gamesPlayed", 0),
                "w": t.get("wins", 0), "l": t.get("losses", 0),
                "pct": t.get("winningPercentage", ""),
                "rs": t.get("runsScored", 0), "ra": t.get("runsAllowed", 0),
                "rs_pg": round(t.get("runsScored", 0) / gp, 3),
                "ra_pg": round(t.get("runsAllowed", 0) / gp, 3),
                "diff": t.get("run differential", ""),
                "streak": (t.get("streak") or {}).get("streakCode", ""),
                "source": cap.url("mlb_standings"),
            }
    for tid, key in (("mlb_hitting", "hitting"), ("mlb_pitching", "pitching")):
        data = cap.json(tid) or {}
        for s in data.get("stats", []):
            for split in s.get("splits", []):
                idn = split["team"]["id"]
                if idn in teams:
                    teams[idn][key] = split.get("stat", {})
    now = utc_now()
    fixtures, skipped = [], []
    data = cap.json("mlb_sched") or {}
    for day in data.get("dates", []):
        for g in day.get("games", []):
            start = parse_iso(g.get("gameDate", ""))
            if not _keep(start, now):
                continue
            state = (g.get("status") or {}).get("detailedState", "")
            if state not in ("Scheduled", "Pre-Game", "Warmup"):
                continue
            hid, aid = g["teams"]["home"]["team"]["id"], g["teams"]["away"]["team"]["id"]
            if hid not in teams or aid not in teams:
                skipped.append(f"MLB {aid}@{hid}: no standings row")
                continue
            fixtures.append({
                "sport": "Baseball", "competition": "MLB World Series",
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": teams[hid]["name"], "away": teams[aid]["name"],
                "home_code": "", "away_code": "",
                "venue": (g.get("venue") or {}).get("name", ""),
                "source_url": f"https://www.mlb.com/gameday/{g.get('gamePk','')}",
                "source_id": str(g.get("gamePk", "")),
                "inputs": {"home": teams[hid], "away": teams[aid], "model": "mlb_run_poisson",
                           "probable_home": ((g["teams"]["home"].get("probablePitcher") or {}).get("fullName", "")),
                           "probable_away": ((g["teams"]["away"].get("probablePitcher") or {}).get("fullName", "")),
                           "standings_source": cap.url("mlb_standings"),
                           "schedule_source": cap.url("mlb_sched"),
                           "series_game": g.get("seriesGameNumber", ""),
                           "series_status": (g.get("seriesStatus") or {}).get("description", "")},
                "tags": ["playoff", "world-series"],
            })
    return fixtures, teams, skipped


# ----------------------------------------------------------------------------- EuroLeague / EuroCup
def euroleague_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    now = utc_now()
    fixtures, teams, skipped = [], {}, []
    for tid, comp_name in (("euroleague_games_E2026", "EuroLeague"),
                           ("euroleague_games_U2026", "EuroCup")):
        data = cap.json(tid) or {}
        games = data.get("data", [])
        for g in games:
            local = (g.get("local") or {}).get("club") or {}
            road = (g.get("road") or {}).get("club") or {}
            lname = local.get("name") or ""
            rname = road.get("name") or ""
            if not lname or not rname:
                continue
            lg, rg = local.get("results") or {}, road.get("results") or {}
            if g.get("played") and lg.get("score") is not None:
                for club, code, pts, opp in ((local, lname, lg.get("score", 0), rg.get("score", 0)),
                                             (road, rname, rg.get("score", 0), lg.get("score", 0))):
                    t = teams.setdefault(code, {"name": code, "code": club.get("code", ""),
                                                "gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0,
                                                "competition": comp_name,
                                                "source": cap.url(tid)})
                    t["gp"] += 1
                    t["pf"] += int(pts or 0)
                    t["pa"] += int(opp or 0)
                    t["w" if int(pts or 0) > int(opp or 0) else "l"] += 1
            start = parse_iso(g.get("utcDate", "") or g.get("date", ""))
            if g.get("played") or not _keep(start, now):
                continue
            fixtures.append({
                "sport": "Basketball", "competition": f"{comp_name} regular season",
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": lname, "away": rname, "home_code": local.get("code", ""),
                "away_code": road.get("code", ""),
                "venue": (g.get("venue") or {}).get("name", ""),
                "source_url": "https://www.euroleaguebasketball.net/euroleague/game-center/",
                "source_id": g.get("identifier", ""),
                "inputs": {"home_name": lname, "away_name": rname,
                           "round": g.get("roundAlias", ""), "model": "basket_point_normal",
                           "schedule_source": cap.url(tid)},
                "tags": ["regular-season"],
            })
    for t in teams.values():
        t["pf_pg"] = round(t["pf"] / t["gp"], 2) if t["gp"] else 0
        t["pa_pg"] = round(t["pa"] / t["gp"], 2) if t["gp"] else 0
    return fixtures, teams, skipped


# ----------------------------------------------------------------------------- Liiga (Finland)
def liiga_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    games = cap.json("liiga_games") or []
    now = utc_now()
    teams: dict[str, dict] = {}
    out = []
    for g in games:
        home, away = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        hn, an = home.get("teamName"), away.get("teamName")
        if not hn or not an:
            continue
        finished = bool(g.get("end")) and home.get("goals") is not None
        if finished:
            for name, gf, ga in ((hn, home.get("goals", 0), away.get("goals", 0)),
                                 (an, away.get("goals", 0), home.get("goals", 0))):
                t = teams.setdefault(name, {"name": name, "gp": 0, "w": 0, "l": 0,
                                            "gf": 0, "ga": 0, "source": cap.url("liiga_games")})
                t["gp"] += 1
                t["gf"] += int(gf or 0)
                t["ga"] += int(ga or 0)
                t["w" if int(gf or 0) > int(ga or 0) else "l"] += 1
            continue
        start = parse_iso(g.get("start", ""))
        if not _keep(start, now):
            continue
        out.append({
            "sport": "Ice Hockey", "competition": "Liiga (Finland) regular season",
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": hn, "away": an, "home_code": "", "away_code": "",
            "venue": (g.get("venue") or {}).get("name", "") if isinstance(g.get("venue"), dict) else "",
            "source_url": "https://liiga.fi/fi/ottelut",
            "source_id": str(g.get("id", "")),
            "inputs": {"home_name": hn, "away_name": an, "model": "nhl_goal_poisson",
                       "schedule_source": cap.url("liiga_games")},
            "tags": ["regular-season"],
        })
    for t in teams.values():
        gp = max(t["gp"], 1)
        t["gf_pg"] = round(t["gf"] / gp, 3)
        t["ga_pg"] = round(t["ga"] / gp, 3)
        t["pts_pct"] = round(t["w"] / gp, 4)
    return out, teams, []


# ----------------------------------------------------------------------------- WTA
def wta_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    rankings = cap.json("wta_rankings") or []
    if isinstance(rankings, dict):
        rankings = rankings.get("content") or rankings.get("data") or []
    players: dict[str, dict] = {}
    for row in rankings:
        pl = row.get("player") or {}
        pid = str(pl.get("id") or row.get("id") or "")
        name = pl.get("fullName") or f"{pl.get('firstName','')} {pl.get('lastName','')}".strip()
        if pid and name:
            players[pid] = {"id": pid, "name": name, "rank": row.get("ranking", ""),
                            "points": row.get("points", ""), "country": pl.get("countryCode", ""),
                            "tournaments": row.get("tournamentsPlayed", ""),
                            "ranked_at": row.get("rankedAt", ""),
                            "source": cap.url("wta_rankings")}
    now = utc_now()
    fixtures, skipped = [], []
    for rec in cap.manifest["records"]:
        if not rec["id"].startswith("wta_matches_") or not rec.get("file"):
            continue
        data = cap.json(rec["id"]) or {}
        tour = data.get("tournament") or {}
        title = tour.get("title", "")
        if not title:
            continue
        for m in data.get("matches", []):
            if m.get("MatchState") != "U":
                continue
            start = parse_iso(m.get("NotBeforeISOTime", "") or m.get("MatchTimeStamp", ""))
            if start is None:
                # Non-ISO local stamp (e.g. 2026-10-24T15:00+08:00) still carries an offset
                stamp = m.get("MatchTimeStamp", "")
                if "+" in stamp or "Z" in stamp:
                    start = parse_iso(stamp)
            if not _keep(start, now):
                continue
            if m.get("DrawMatchType") != "S":  # doubles skipped: no verified ranking input
                continue
            aid, bid = str(m.get("PlayerIDA", "")), str(m.get("PlayerIDB", ""))
            aname = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            bname = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            fixtures.append({
                "sport": "Tennis", "competition": title,
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": aname, "away": bname, "home_code": "", "away_code": "",
                "venue": m.get("CourtName", ""),
                "source_url": cap.url(rec["id"]),
                "source_id": f"{m.get('EventID','')}:{m.get('MatchID','')}",
                "inputs": {"a": {"name": aname, "id": aid, "rank": players.get(aid, {}).get("rank", ""),
                                 "points": players.get(aid, {}).get("points", ""),
                                 "country": m.get("PlayerCountryA", "")},
                           "b": {"name": bname, "id": bid, "rank": players.get(bid, {}).get("rank", ""),
                                 "points": players.get(bid, {}).get("points", ""),
                                 "country": m.get("PlayerCountryB", "")},
                           "model": "tennis_set_model", "round": m.get("RoundID", ""),
                           "seed_a": m.get("SeedA", ""), "seed_b": m.get("SeedB", ""),
                           "schedule_source": cap.url(rec["id"]),
                           "tournament_start": tour.get("startDate", ""),
                           "tournament_end": tour.get("endDate", ""),
                           "surface": tour.get("surface", "")},
                "tags": ["singles"],
            })
    return fixtures, players, skipped

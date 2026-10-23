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
            "l10_record": f"{t.get('l10Wins',0)}-{t.get('l10Losses',0)}-{t.get('l10OtLosses',0)}",
            "l10_points": t.get("l10Points", ""),
            "home_record": f"{t.get('homeWins',0)}-{t.get('homeLosses',0)}-{t.get('homeOtLosses',0)}",
            "road_record": f"{t.get('roadWins',0)}-{t.get('roadLosses',0)}-{t.get('roadOtLosses',0)}",
            "source": cap.url("nhl_standings_now"),
        }
    now = utc_now()
    fixtures, used, skipped = [], [], []
    seen_games: set[str] = set()
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
                gid = str(g.get("id", ""))
                if gid and gid in seen_games:
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
                if gid:
                    seen_games.add(gid)
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
            lside, rside = g.get("local") or {}, g.get("road") or {}
            local = lside.get("club") or {}
            road = rside.get("club") or {}
            lname = local.get("name") or ""
            rname = road.get("name") or ""
            if not lname or not rname:
                continue
            lg = {"score": lside.get("score")}
            rg = {"score": rside.get("score")}
            if g.get("played") and lside.get("score") is not None:
                for club, code, pts, opp in ((local, lname, lside.get("score", 0), rside.get("score", 0)),
                                             (road, rname, rside.get("score", 0), lside.get("score", 0))):
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


# ----------------------------------------------------------------------------- generic HTML text
def visible_lines(raw: str) -> list[str]:
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    t = re.sub(r"(?s)<[^>]+>", "\n", t)
    return [l.strip() for l in re.sub(r"\n+", "\n", html.unescape(t)).split("\n") if l.strip()]


MONTHS_FR = {"janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4, "mai": 5,
             "juin": 6, "juillet": 7, "aout": 8, "août": 8, "septembre": 9, "octobre": 10,
             "novembre": 11, "decembre": 12, "décembre": 12}


def lnr_fixtures(cap: Capture, tid: str, competition: str) -> list[dict]:
    """LNR Top 14 / Pro D2: server-rendered round list (home, rank, time, away, rank)."""
    raw = cap.text(tid)
    if not raw:
        return []
    lines = visible_lines(raw)
    out = []
    current_date = None
    i = 0
    while i < len(lines) - 6:
        m = re.match(r"(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\s+(\d{1,2})\s+([a-zéûôà]+)",
                     lines[i], re.I)
        if m and m.group(3).lower() in MONTHS_FR:
            current_date = (2026, MONTHS_FR[m.group(3).lower()], int(m.group(2)))
            i += 1
            continue
        # block: home, rank, "e", HHhMM, away, rank, "e"
        if (current_date and re.match(r"^\d{1,2}$", lines[i + 1])
                and lines[i + 2] in ("e", "e.") and re.match(r"^\d{1,2}h\d{2}$", lines[i + 3])
                and re.match(r"^\d{1,2}$", lines[i + 5])):
            hh, mm = lines[i + 3].split("h")
            # French local time (CEST, UTC+2) unless November (CET, UTC+1)
            offset = 2 if current_date[1] <= 10 else 1
            try:
                start = datetime(*current_date, int(hh) - offset, int(mm), tzinfo=timezone.utc)
            except ValueError:
                i += 1
                continue
            out.append({
                "sport": "Rugby Union", "competition": f"{competition} (LNR)",
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": lines[i], "away": lines[i + 4], "home_code": "", "away_code": "",
                "venue": "",
                "source_url": cap.url(tid),
                "source_id": f"{lines[i]}|{lines[i+4]}|{start.isoformat()}",
                "inputs": {"home_rank": lines[i + 1], "away_rank": lines[i + 5],
                           "model": "rugby_point_normal",
                           "time_note": "published kick-off is French local; converted with the "
                                        "French summer/winter offset",
                           "schedule_source": cap.url(tid)},
                "tags": ["league"],
            })
            i += 6
            continue
        i += 1
    return out


def lnr_table(cap: Capture, tid: str, url_id: str | None = None) -> dict:
    """LNR standings: team, Pts, M, G, N, P, Bonus, PF, PA, Diff, form letters."""
    raw = cap.text(url_id or tid)
    if not raw:
        return {}
    lines = visible_lines(raw)
    table: dict[str, dict] = {}
    for i in range(len(lines) - 10):
        if re.match(r"^\d{2,3}$", lines[i + 1]) and re.match(r"^\d{1,2}$", lines[i + 2]) \
                and re.match(r"^[+-]?\d{1,3}$", lines[i + 9]):
            nums = lines[i + 1:i + 10]
            if all(re.match(r"^[+-]?\d{1,3}$", n) for n in nums):
                team = lines[i]
                table[team] = {"name": team, "pts": int(nums[0]), "played": int(nums[1]),
                               "w": int(nums[2]), "d": int(nums[3]), "l": int(nums[4]),
                               "bonus": int(nums[5]), "pf": int(nums[6]), "pa": int(nums[7]),
                               "diff": int(nums[8]),
                               "source": cap.url(url_id or tid)}
    return table


# ----------------------------------------------------------------------------- SHL
def shl_fixtures(cap: Capture) -> tuple[list[dict], dict]:
    raw = cap.text("swehockey_shl")
    if not raw:
        return [], {}
    lines = visible_lines(raw)
    teams: dict[str, dict] = {}
    for i in range(len(lines) - 12):
        if (re.match(r"^\d{1,2}$", lines[i]) and re.match(r"^\d{1,2}$", lines[i + 2])
                and re.match(r"^\d{1,2}$", lines[i + 3]) and re.match(r"^\d{1,2}$", lines[i + 4])
                and re.match(r"^\d{1,3}:\d{1,3}\s*\(", lines[i + 5])):
            gf, ga = re.match(r"^(\d{1,3}):(\d{1,3})", lines[i + 5]).groups()
            teams[lines[i + 1]] = {"name": lines[i + 1], "gp": int(lines[i + 2]),
                                   "w": int(lines[i + 3]), "t": int(lines[i + 4]),
                                   "l": int(lines[i + 3 + 1]) if False else None,
                                   "gf": int(gf), "ga": int(ga),
                                   "source": cap.url("swehockey_shl")}
    # The standings row order is RK, Team, GP, W, T, L, GF:GA, GD, TP, OTW, OTL, GWSW, GWSL
    teams = {}
    for i in range(len(lines) - 12):
        if (re.match(r"^\d{1,2}$", lines[i]) and re.match(r"^\d{1,2}$", lines[i + 2])
                and re.match(r"^\d{1,2}$", lines[i + 3]) and re.match(r"^\d{1,2}$", lines[i + 4])
                and re.match(r"^\d{1,2}$", lines[i + 5])
                and re.match(r"^\d{1,3}:\d{1,3}\s*\(-?\d+\)$", lines[i + 6])):
            gf, ga = re.match(r"^(\d{1,3}):(\d{1,3})", lines[i + 6]).groups()
            gp = int(lines[i + 2])
            teams[lines[i + 1]] = {"name": lines[i + 1], "gp": gp,
                                   "w": int(lines[i + 3]), "t": int(lines[i + 4]),
                                   "l": int(lines[i + 5]), "points": int(lines[i + 8]),
                                   "gf": int(gf), "ga": int(ga),
                                   "gf_pg": round(int(gf) / gp, 3) if gp else 0,
                                   "ga_pg": round(int(ga) / gp, 3) if gp else 0,
                                   "pts_pct": round(int(lines[i + 8]) / (3 * gp), 4) if gp else 0,
                                   "source": cap.url("swehockey_shl")}
    fixtures = []
    for i in range(len(lines) - 5):
        m = re.match(r"^(2026-\d{2}-\d{2})\s+(\d{2}):(\d{2})$", lines[i])
        if m and lines[i + 2] == "-" and lines[i + 4] not in ("-", ""):
            # published in Swedish local time (CEST to 25 Oct, then CET)
            date = m.group(1)
            offset = 2 if date <= "2026-10-25" else 1
            start = datetime(int(date[:4]), int(date[5:7]), int(date[8:10]),
                             int(m.group(2)) - offset, int(m.group(3)), tzinfo=timezone.utc)
            fixtures.append({
                "sport": "Ice Hockey", "competition": "SHL (Sweden) regular season",
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": lines[i + 1], "away": lines[i + 3], "home_code": "", "away_code": "",
                "venue": lines[i + 4] if i + 4 < len(lines) else "",
                "source_url": cap.url("swehockey_shl"),
                "source_id": f"{lines[i+1]}|{lines[i+3]}|{date}",
                "inputs": {"model": "nhl_goal_poisson",
                           "time_note": "published in Swedish local time; converted with the "
                                        "Swedish summer/winter offset",
                           "schedule_source": cap.url("swehockey_shl")},
                "tags": ["league"],
            })
    return fixtures, teams


# ----------------------------------------------------------------------------- PlusLiga
def plusliga_table(cap: Capture) -> dict:
    """PlusLiga standings from the official table page.

    The page renders one row per played matchday with cumulative figures, under a two-row header
    (Drużyna | Punkty | Mecze | Sety | Punkty | Stosunek): rank, team, points, played, won, lost,
    sets won, sets lost, points won, points lost. The last row for a team is its current total.
    """
    raw = cap.text("plusliga_table")
    if not raw:
        return {}
    table: dict[str, dict] = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", raw, re.S):
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, re.S)]
        cells = [c for c in cells if c]
        if len(cells) < 10 or not cells[0].isdigit():
            continue
        try:
            points, played, won, lost, sets_w, sets_l = (int(cells[i]) for i in (2, 3, 4, 5, 6, 7))
        except (ValueError, IndexError):
            continue
        table[cells[1]] = {"name": cells[1], "played": played, "points": points,
                           "won": won, "lost": lost,
                           "sets_won": sets_w, "sets_lost": sets_l,
                           "source": cap.url("plusliga_table")}
    return table


def plusliga_fixtures(cap: Capture) -> list[dict]:
    raw = cap.text("plusliga_table")
    if not raw:
        return []
    lines = visible_lines(raw)
    out = []
    months = {"sty": 1, "lut": 2, "mar": 3, "kwi": 4, "maj": 5, "cze": 6, "lip": 7,
              "sie": 8, "wrz": 9, "paź": 10, "paz": 10, "lis": 11, "gru": 12}
    for i, line in enumerate(lines[:-14]):
        m = re.match(r"^(poniedziałek|wtorek|środa|czwartek|piątek|sobota|niedziela),\s*(\d{1,2})\s*([a-ząćęłńóśźż]+),\s*(\d{1,2}):(\d{2})$",
                     line, re.I)
        if not m:
            continue
        mon = months.get(m.group(3).lower()[:3])
        if not mon:
            continue
        if lines[i + 1] != "Trwa":
            continue
        home, away = lines[i + 2], None
        for k in range(i + 3, min(i + 16, len(lines))):
            if lines[k] not in ("···", "0", "") and not re.match(r"^[\d\.·]+$", lines[k]) and len(lines[k]) > 4:
                away = lines[k]
                break
        if not away:
            continue
        # Polish local time: CEST (UTC+2) to 25 Oct, CET (UTC+1) after
        offset = 2 if (mon, int(m.group(2))) <= (10, 25) else 1
        try:
            start = datetime(2026, mon, int(m.group(2)), int(m.group(4)) - offset,
                             int(m.group(5)), tzinfo=timezone.utc)
        except ValueError:
            continue
        out.append({
            "sport": "Volleyball", "competition": "PlusLiga (Poland) regular season",
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": home, "away": away, "home_code": "", "away_code": "",
            "venue": "",
            "source_url": cap.url("plusliga_table"),
            "source_id": f"{home}|{away}|{start.isoformat()}",
            "inputs": {"model": "volley_set_model",
                       "side_note": "the official page lists the pair in this order but does not "
                                    "label home/away; no home advantage is applied",
                       "time_note": "published in Polish local time; converted to UTC",
                       "schedule_source": cap.url("plusliga_table")},
            "tags": ["league"],
        })
    return out


# ----------------------------------------------------------------------------- Formula 1
def f1_calendar(cap: Capture) -> list[dict]:
    raw = cap.text("f1_season")
    if not raw:
        return []
    text = " ".join(visible_lines(raw))
    month_map = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6, "JUL": 7,
                 "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}
    races = []
    tokens = list(re.finditer(
        r"ROUND (\d{1,2}) ([A-Za-z][A-Za-z\s’']{2,28}?) "
        r"(?:(\d{1,2}) ([A-Z]{3}) - (\d{1,2}) ([A-Z]{3})|(\d{1,2}) - (\d{1,2}) ([A-Z]{3}))", text))
    for m in tokens:
        num, name = m.group(1), m.group(2).strip()
        if m.group(3):
            d1, mon_s, d2 = m.group(3), m.group(6), m.group(5)
        else:
            d1, d2, mon_s = m.group(7), m.group(8), m.group(9)
        mon = month_map.get(mon_s)
        if not mon:
            continue
        try:
            start = datetime(2026, mon, int(d1), 12, 0, tzinfo=timezone.utc)
            end = datetime(2026, mon, int(d2), 18, 0, tzinfo=timezone.utc)
        except ValueError:
            continue
        if end < utc_now() - timedelta(days=1):
            continue
        name = name.replace("Chequered Flag", "").strip()
        races.append({
            "sport": "Motor Racing", "competition": f"Formula 1 — {name} Grand Prix",
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": f"{name} Grand Prix", "away": "Field",
            "home_code": "", "away_code": "",
            "venue": "",
            "source_url": cap.url("f1_season"),
            "source_id": f"round-{num}",
            "inputs": {"model": "outright_from_standings_order", "round": num,
                       "date_range": f"{d1}-{d2} {mon_s}",
                       "schedule_source": cap.url("f1_season")},
            "tags": ["race"],
        })
    return races


def f1_driver_order(cap: Capture) -> list[str]:
    raw = cap.text("f1_drivers")
    if not raw:
        return []
    lines = visible_lines(raw)
    out = []
    i = 0
    while i < len(lines) - 5:
        if re.match(r"^\d{1,2}$", lines[i]) and re.match(r"^[A-Z]{3}$", lines[i + 3] or ""):
            out.append(f"{lines[i + 1]} {lines[i + 2]}")
            i += 6
            continue
        i += 1
    return out


# ----------------------------------------------------------------------------- Golf
def dpwt_event(cap: Capture) -> dict:
    raw = cap.text("dpwt_genesis_tee")
    if not raw:
        return {}
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', raw, re.S)
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return {}
    loc = (data.get("Location") or [{}])[0]
    performers = [p.get("name", "") for p in data.get("Performer", []) if p.get("name")]
    return {
        "sport": "Golf", "competition": "DP World Tour — Genesis Championship",
        "start_utc": (data.get("StartDate", "") or "").replace("+00:00", "Z"),
        "home": "Genesis Championship", "away": f"{len(performers)}-player field",
        "home_code": "", "away_code": "",
        "venue": loc.get("name", ""),
        "source_url": cap.url("dpwt_genesis_tee"),
        "source_id": "genesis-championship-2026",
        "inputs": {"model": "outright_from_owgr", "field": performers[:80],
                   "event_end": data.get("EndDate", ""),
                   "schedule_source": cap.url("dpwt_genesis_tee")},
        "tags": ["tournament"],
    }


def owgr_strengths(cap: Capture) -> list[tuple[str, float]]:
    raw = cap.text("owgr")
    if not raw or "Scheffler" not in raw:
        return []
    rows = re.findall(r'<a href="https://www\.owgr\.com/playerprofile/[^"]+">([^<]+)</a>.*?'
                      r'\|?\s*([\d.]+)\s*\|', raw, re.S)
    out = []
    for name, pts in rows:
        try:
            out.append((html.unescape(name), float(pts)))
        except ValueError:
            continue
    return out


# ----------------------------------------------------------------------------- Rugby League (RLWC)
def rlwc_fixtures(cap: Capture) -> tuple[list[dict], dict, list[str]]:
    data = cap.json("rlwc_api") or {}
    rounds = ((data.get("result") or {}).get("roundFixtures")) or []
    now = utc_now()
    form: dict[str, dict] = {}
    fixtures, skipped = [], []
    for r in rounds:
        for g in r.get("gameFixtures", []):
            teams = g.get("teams") or []
            if len(teams) != 2 or any(t.get("teamName") == "TBA" for t in teams):
                continue
            state = (g.get("gameStateName") or "").lower()
            start = parse_iso(g.get("startTimeUTC", ""))
            if state in ("final", "fulltime", "completed") and start and start < now:
                for t in teams:
                    name = t.get("teamName")
                    pf, pa = t.get("teamFinalScore"), next(
                        (x.get("teamFinalScore") for x in teams if x is not t), None)
                    if pf is None or pa is None:
                        continue
                    rec = form.setdefault(name, {"name": name, "gp": 0, "w": 0, "l": 0,
                                                 "pf": 0, "pa": 0,
                                                 "source": cap.url("rlwc_api")})
                    rec["gp"] += 1
                    rec["pf"] += int(pf)
                    rec["pa"] += int(pa)
                    rec["w" if int(pf) > int(pa) else "l"] += 1
                continue
            if not start or start < now - timedelta(hours=3):
                continue
            home = next((t for t in teams if t.get("isHomeTeam")), teams[0])
            away = next((t for t in teams if t is not home), teams[1])
            fixtures.append({
                "sport": "Rugby League",
                "competition": f"Rugby League World Cup 2026 — {r.get('roundName','')}".strip(),
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": home.get("teamName", ""), "away": away.get("teamName", ""),
                "home_code": home.get("teamAbbr", ""), "away_code": away.get("teamAbbr", ""),
                "venue": g.get("venueName", ""),
                "source_url": cap.url("rlwc_api"),
                "source_id": str(g.get("gameId", "")),
                "inputs": {"model": "league_points_normal", "round": r.get("roundName", ""),
                           "group": g.get("groupName", ""),
                           "listed_home_price": home.get("teamHeadToHeadOdds", ""),
                           "listed_away_price": away.get("teamHeadToHeadOdds", ""),
                           "schedule_source": cap.url("rlwc_api")},
                "tags": ["international", "world-cup"],
            })
    for t in form.values():
        t["pf_pg"] = round(t["pf"] / t["gp"], 2) if t["gp"] else 0
        t["pa_pg"] = round(t["pa"] / t["gp"], 2) if t["gp"] else 0
    return fixtures, form, skipped

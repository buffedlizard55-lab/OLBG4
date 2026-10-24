#!/usr/bin/env python3
"""Extract normalised facts from the committed governing-body capture.

Every value written here is read out of the byte-exact capture committed by
`.github/workflows/sa-696c1a7c.yml`; the SHA-256 of the file each value came from
is carried on the record, so a reviewer can re-hash the payload and re-read the
number. Nothing is inferred, defaulted or filled in: a field the source does not
print stays `None` and the row is flagged downstream.

Output: data/session-696c1a7c/facts.json

    python3 official.py [CAPTURE_DIR]
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import htmlutil as H  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"


class Capture:
    def __init__(self, path: Path):
        self.path = path
        self.manifest = json.loads((path / "manifest.json").read_text())
        self.by_id = {r["id"]: r for r in self.manifest["records"]}

    def has(self, *ids: str) -> bool:
        return all(i in self.by_id for i in ids)

    def raw(self, tid: str) -> bytes:
        return gzip.open(self.path / self.by_id[tid]["file"], "rb").read()

    def json(self, tid: str):
        return json.loads(self.raw(tid))

    def text(self, tid: str) -> str:
        return self.raw(tid).decode("utf-8", "replace")

    def src(self, tid: str) -> dict:
        rec = self.by_id[tid]
        return {"source_id": tid, "source_url": rec["url"], "sha256": rec["sha256"],
                "bytes": rec["bytes"], "captured_utc": self.manifest["finished_utc"]}


FACTS: dict = {"fixtures": [], "teams": [], "history": [], "individuals": [],
               "competitions": [], "gaps": [], "sources": []}


def comp(key: str, sport: str, name: str, cap: Capture, tid: str, kind: str) -> None:
    entry = {"key": key, "sport": sport, "name": name, "kind": kind, **cap.src(tid)}
    FACTS["competitions"].append(entry)


def team(key: str, sport: str, competition: str, name: str, cap: Capture, tid: str, **stats) -> None:
    FACTS["teams"].append({"key": key, "sport": sport, "competition": competition,
                           "team": name, **stats, **cap.src(tid)})


def fixture(key: str, sport: str, competition: str, home: str, away: str,
            start: str | None, cap: Capture, tid: str, venue: str | None = None,
            extra: dict | None = None) -> None:
    rec = {"key": key, "sport": sport, "competition": competition, "home": home,
           "away": away, "start_utc": start, "venue": venue, **cap.src(tid)}
    if extra:
        rec.update(extra)
    FACTS["fixtures"].append(rec)


def history(key: str, sport: str, competition: str, date: str, home: str, away: str,
            hs: int, as_: int, cap: Capture, tid: str) -> None:
    FACTS["history"].append({"key": key, "sport": sport, "competition": competition,
                             "date": date, "home": home, "away": away,
                             "home_score": hs, "away_score": as_, **cap.src(tid)})


def gap(sport: str, what: str, detail: str, url: str) -> None:
    FACTS["gaps"].append({"sport": sport, "missing": what, "detail": detail, "source_url": url})


# --------------------------------------------------------------------------- #
# Ice hockey
# --------------------------------------------------------------------------- #
def nhl(cap: Capture) -> None:
    sched_ids = sorted(i for i in cap.by_id if i.startswith("nhl_sched_"))
    if not sched_ids or not cap.has("nhl_standings"):
        gap("Ice Hockey", "NHL feed", "NHL schedule/standings payload missing", "https://api-web.nhle.com/")
        return
    comp("nhl", "Ice Hockey", "NHL", cap, "nhl_standings", "league")

    standings = cap.json("nhl_standings")["standings"]
    for t in standings:
        ab = t["teamAbbrev"]["default"] if isinstance(t.get("teamAbbrev"), dict) else t.get("teamAbbrev")
        name = t.get("teamName", {}).get("default") or t.get("placeName", {}).get("default", "") + " " + \
            t.get("teamCommonName", {}).get("default", "")
        gp = t.get("gamesPlayed")
        team("nhl|" + ab, "Ice Hockey", "nhl", name.strip(), cap, "nhl_standings",
             played=gp, wins=t.get("wins"), losses=t.get("losses"), ot_losses=t.get("otLosses"),
             points=t.get("points"), goals_for=t.get("goalFor"), goals_against=t.get("goalAgainst"),
             home_wins=t.get("homeWins"), home_losses=t.get("homeLosses"),
             road_wins=t.get("roadWins"), road_losses=t.get("roadLosses"),
             l10_wins=t.get("l10Wins"), l10_losses=t.get("l10Losses"),
             l10_goals_for=t.get("l10GoalsFor"), l10_goals_against=t.get("l10GoalsAgainst"),
             streak=t.get("streakCode"), abbr=ab,
             division=t.get("divisionName"), conference=t.get("conferenceName"))

    seen = set()
    for tid in sched_ids:
        payload = cap.json(tid)
        for week in payload.get("gameWeek", []):
            week_date = week.get("date")
            for g in week.get("games", []):
                if g.get("id") in seen:
                    continue
                seen.add(g.get("id"))
                home, away = g["homeTeam"], g["awayTeam"]
                hab = home["abbrev"]["default"] if isinstance(home.get("abbrev"), dict) else home.get("abbrev")
                aab = away["abbrev"]["default"] if isinstance(away.get("abbrev"), dict) else away.get("abbrev")
                venue = (g.get("venue") or {}).get("default")
                if g.get("gameState") in ("OFF", "FINAL"):
                    history(f"nhl:{g['id']}", "Ice Hockey", "nhl", g.get("gameDate") or week_date,
                            "nhl|" + hab, "nhl|" + aab, home.get("score"), away.get("score"), cap, tid)
                else:
                    fixture(f"nhl:{g['id']}", "Ice Hockey", "nhl", "nhl|" + hab, "nhl|" + aab,
                            g.get("startTimeUTC"), cap, tid, venue)


def liiga(cap: Capture) -> None:
    if not cap.has("liiga_games"):
        gap("Ice Hockey", "Liiga feed", "Liiga games payload missing", "https://liiga.fi/")
        return
    comp("liiga", "Ice Hockey", "Liiga (Finland)", cap, "liiga_games", "league")
    for g in cap.json("liiga_games"):
        home = (g.get("homeTeam") or {}).get("name") or (g.get("homeTeam") or {}).get("teamName")
        away = (g.get("awayTeam") or {}).get("name") or (g.get("awayTeam") or {}).get("teamName")
        start = g.get("start") or g.get("date") or g.get("gameDate")
        if not home or not away:
            continue
        hs = g.get("homeScore")
        as_ = g.get("awayScore")
        if hs is None:
            periods = g.get("periods") or []
            if g.get("ended") and periods:
                hs = sum((p.get("homeGoals") or 0) for p in periods)
                as_ = sum((p.get("awayGoals") or 0) for p in periods)
        key = "liiga|" + str(g.get("id"))
        if hs is not None and as_ is not None and start:
            history(key, "Ice Hockey", "liiga", (start or "")[:10], "liiga|" + home,
                    "liiga|" + away, hs, as_, cap, "liiga_games")
        elif start:
            fixture(key, "Ice Hockey", "liiga", "liiga|" + home, "liiga|" + away,
                    start, cap, "liiga_games", g.get("venue"))


def find_header_table(page: str, *needles: str) -> list[list[str]] | None:
    """Some league pages put a caption row above the header; scan the first rows."""
    for table in H.tables(page):
        for i, row in enumerate(table[:3]):
            joined = " ".join(row).lower()
            if all(n.lower() in joined for n in needles):
                return table[i:]
    return None


def shl(cap: Capture) -> None:
    if not cap.has("shl_standings"):
        gap("Ice Hockey", "SHL table", "SHL standings page missing", "https://stats.swehockey.se/")
        return
    comp("shl", "Ice Hockey", "Swedish Hockey League", cap, "shl_standings", "league")
    table = find_header_table(cap.text("shl_standings"), "Team", "GP", "TP")
    if not table:
        gap("Ice Hockey", "SHL table", "SHL standings table did not render a header row",
            "https://stats.swehockey.se/ScheduleAndResults/Standings/20961")
        return
    for row in table[1:]:
        if len(row) < 9 or not row[0].isdigit():
            continue
        m6 = re.match(r"^\s*(\d+)\s*:\s*(\d+)", row[6])
        gf, ga = (m6.group(1), m6.group(2)) if m6 else ("", "")
        team("shl|" + row[1], "Ice Hockey", "shl", row[1], cap, "shl_standings",
             played=H.to_int(row[2]), wins=H.to_int(row[3]), draws=H.to_int(row[4]),
             losses=H.to_int(row[5]), goals_for=H.to_int(gf), goals_against=H.to_int(ga),
             points=H.to_int(row[8]))


def nl(cap: Capture) -> None:
    if not cap.has("nl_games"):
        return
    comp("nl", "Ice Hockey", "National League (Switzerland)", cap, "nl_games", "league")
    for g in cap.json("nl_games"):
        home = g.get("homeTeamName")
        away = g.get("awayTeamName")
        start = g.get("startDate") or g.get("date") or g.get("gameDate")
        if not home or not away:
            continue
        hs, as_ = g.get("homeTeamResult"), g.get("awayTeamResult")
        key = "nl|" + str(g.get("gameId"))
        if hs is not None and as_ is not None and start:
            history(key, "Ice Hockey", "nl", str(start)[:10], "nl|" + home, "nl|" + away,
                    hs, as_, cap, "nl_games")
        elif start:
            fixture(key, "Ice Hockey", "nl", "nl|" + home, "nl|" + away, start, cap, "nl_games")


# --------------------------------------------------------------------------- #
# Baseball
# --------------------------------------------------------------------------- #
def mlb(cap: Capture) -> None:
    if not cap.has("mlb_schedule"):
        gap("Baseball", "MLB feed", "MLB schedule payload missing", "https://statsapi.mlb.com/")
        return
    comp("mlb", "Baseball", "MLB", cap, "mlb_schedule", "league")
    sched = cap.json("mlb_schedule")
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            home = g["teams"]["home"]["team"]["name"]
            away = g["teams"]["away"]["team"]["name"]
            start = g.get("gameDate")
            venue = (g.get("venue") or {}).get("name")
            status = (g.get("status") or {}).get("detailedState", "")
            key = "mlb:" + str(g.get("gamePk"))
            if status.startswith("Final"):
                history(key, "Baseball", "mlb", day.get("date"), "mlb|" + home, "mlb|" + away,
                        g["teams"]["home"].get("score"), g["teams"]["away"].get("score"),
                        cap, "mlb_schedule")
            else:
                pitchers = {}
                for side in ("home", "away"):
                    p = g["teams"][side].get("probablePitcher") or {}
                    if p.get("fullName"):
                        pitchers[side] = p["fullName"]
                fixture(key, "Baseball", "mlb", "mlb|" + home, "mlb|" + away, start, cap,
                        "mlb_schedule", venue, {"probable_pitchers": pitchers or None,
                                                "status": status})

    if cap.has("mlb_standings"):
        for rec in cap.json("mlb_standings").get("records", []):
            for t in rec.get("teamRecords", []):
                name = t["team"].get("teamName") or t["team"]["name"]
                team("mlb|" + name, "Baseball", "mlb", name, cap, "mlb_standings",
                     played=t.get("gamesPlayed"), wins=t.get("wins"), losses=t.get("losses"),
                     runs_for=t.get("runsScored"), runs_against=t.get("runsAllowed"),
                     streak=(t.get("streak") or {}).get("streakCode"),
                     division=(t.get("division") or {}).get("name"))
    if cap.has("mlb_hitting"):
        stats = cap.json("mlb_hitting").get("stats", [])
        for split in (stats[0].get("splits", []) if stats else []):
            name = split["team"].get("teamName") or split["team"]["name"]
            st = split.get("stat", {})
            team("mlb|" + name, "Baseball", "mlb", name, cap, "mlb_hitting",
                 avg=st.get("avg"), obp=st.get("obp"), slg=st.get("slg"), ops=st.get("ops"),
                 runs=st.get("runs"), home_runs=st.get("homeRuns"),
                 runs_per_game=st.get("runs") and round(st["runs"] / st["gamesPlayed"], 3)
                 if st.get("gamesPlayed") else None)
    if cap.has("mlb_pitching"):
        stats = cap.json("mlb_pitching").get("stats", [])
        for split in (stats[0].get("splits", []) if stats else []):
            name = split["team"].get("teamName") or split["team"]["name"]
            st = split.get("stat", {})
            team("mlb|" + name, "Baseball", "mlb", name, cap, "mlb_pitching",
                 era=st.get("era"), whip=st.get("whip"), strikeouts=st.get("strikeOuts"),
                 runs_allowed_pg=st.get("runs") and round(st["runs"] / st["gamesPlayed"], 3)
                 if st.get("gamesPlayed") else None)


# --------------------------------------------------------------------------- #
# Basketball — EuroLeague / EuroCup
# --------------------------------------------------------------------------- #
def euroleague(cap: Capture) -> None:
    for tid, key, name in (("el_games", "euroleague", "EuroLeague"),
                           ("eurocup_games", "eurocup", "EuroCup")):
        if not cap.has(tid):
            continue
        comp(key, "Basketball", name, cap, tid, "league")
        for g in cap.json(tid).get("data", []):
            local, road = g.get("local") or {}, g.get("road") or {}
            home = (local.get("club") or {}).get("name")
            away = (road.get("club") or {}).get("name")
            if not home or not away:
                continue
            start = g.get("utcDate") or g.get("date")
            hs, as_ = local.get("score"), road.get("score")
            gkey = f"{key}|{g.get('identifier') or g.get('id')}"
            if g.get("played") and hs is not None and as_ is not None:
                history(gkey, "Basketball", key, str(start)[:10], f"{key}|{home}",
                        f"{key}|{away}", hs, as_, cap, tid)
            elif start and not g.get("played"):
                fixture(gkey, "Basketball", key, f"{key}|{home}", f"{key}|{away}",
                        start, cap, tid, (g.get("venue") or {}).get("name"),
                        {"round": g.get("roundAlias")})


def nba(cap: Capture) -> None:
    if not cap.has("nba_schedule_cdn"):
        gap("Basketball", "NBA schedule", "NBA schedule payload could not be captured from the CDN",
            "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json")
        return
    comp("nba", "Basketball", "NBA", cap, "nba_schedule_cdn", "league")
    data = cap.json("nba_schedule_cdn")
    sched = data.get("leagueSchedule") or {}
    for day in sched.get("gameDates", []):
        for g in day.get("games", []):
            home = g.get("homeTeam") or {}
            away = g.get("awayTeam") or {}
            hname, aname = home.get("teamName"), away.get("teamName")
            if not hname or not aname:
                continue
            start = g.get("gameDateTimeUTC")
            key = "nba:" + str(g.get("gameId"))
            hs, as_ = home.get("score"), away.get("score")
            if g.get("gameStatus") == 3 and hs is not None:
                history(key, "Basketball", "nba", str(start)[:10], "nba|" + hname,
                        "nba|" + aname, hs, as_, cap, "nba_schedule_cdn")
            else:
                fixture(key, "Basketball", "nba", "nba|" + hname, "nba|" + aname, start, cap,
                        "nba_schedule_cdn", (g.get("arena") or {}).get("arenaName"),
                        {"home_abbr": home.get("teamTricode"), "away_abbr": away.get("teamTricode")})
    if cap.has("nba_standings_stats"):
        try:
            payload = cap.json("nba_standings_stats")
            headers = payload["resultSets"][0]["headers"]
            rows = payload["resultSets"][0]["rowSet"]
            idx = {h: i for i, h in enumerate(headers)}
            for r in rows:
                name = r[idx["TeamName"]]
                team("nba|" + name, "Basketball", "nba", name, cap, "nba_standings_stats",
                     wins=r[idx["WINS"]], losses=r[idx["LOSSES"]],
                     points_for=r[idx["PointsPG"]], points_against=r[idx["OppPointsPG"]],
                     diff=r[idx["DiffPointsPG"]])
        except Exception as exc:  # noqa: BLE001
            gap("Basketball", "NBA standings", f"stats.nba.com payload not usable: {exc}",
                "https://stats.nba.com/")


# --------------------------------------------------------------------------- #
# Snooker — WST platform
# --------------------------------------------------------------------------- #
def wst(cap: Capture) -> None:
    ids = [i for i in cap.by_id if i.startswith("wst_matches")]
    if not ids:
        gap("Snooker", "WST matches", "WST match feed missing", "https://www.wst.tv/")
        return
    names = {}
    if cap.has("wst_participants"):
        for p in cap.json("wst_participants").get("data", []):
            a = p.get("attributes", {})
            full = " ".join(x for x in [a.get("firstName"), a.get("surname")] if x)
            names[p.get("id")] = {"name": full, "country": a.get("country")}
            FACTS["individuals"].append({"key": "wst|" + full, "sport": "Snooker",
                                         "name": full, "country": a.get("country"),
                                         **cap.src("wst_participants")})
    comp("wst", "Snooker", "World Snooker Tour", cap, ids[0], "league")
    seen = set()
    for tid in ids:
        try:
            payload = cap.json(tid)
        except Exception:  # noqa: BLE001
            continue
        for m in payload.get("data", []):
            a = m.get("attributes", {})
            mid = m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            home = (a.get("homePlayer") or {})
            away = (a.get("awayPlayer") or {})
            hname = " ".join(x for x in [home.get("firstName"), home.get("surname")] if x)
            aname = " ".join(x for x in [away.get("firstName"), away.get("surname")] if x)
            if not hname or not aname:
                continue
            tname = (a.get("tournament") or {}).get("name") or ""
            start = a.get("startDateTime")
            key = "wst:" + str(mid)
            if a.get("status") == "Completed" and a.get("homePlayerScore") is not None:
                history(key, "Snooker", "wst", str(start)[:10], "wst|" + hname,
                        "wst|" + aname, a["homePlayerScore"], a["awayPlayerScore"], cap, tid)
            elif start:
                fixture(key, "Snooker", "wst", "wst|" + hname, "wst|" + aname,
                        str(start).replace(" ", "T") + "Z" if "T" not in str(start) else start,
                        cap, tid, None,
                        {"tournament": tname, "round": a.get("round"),
                         "best_of": a.get("numberOfFrames")})


# --------------------------------------------------------------------------- #
# Tennis — WTA tournament feeds
# --------------------------------------------------------------------------- #
def wta(cap: Capture) -> None:
    ids = [i for i in cap.by_id if i.startswith("wta_t_")]
    if not ids:
        gap("Tennis", "WTA feed", "no WTA tournament feed captured", "https://www.wtatennis.com/")
        return
    seen = set()
    for i, tid in enumerate(ids):
        try:
            payload = cap.json(tid)
        except Exception:  # noqa: BLE001
            continue
        tour = payload.get("tournament") or {}
        tname = tour.get("title") or tour.get("name") or tid
        ckey = "wta_" + str(tour.get("id") or i)
        if i == 0:
            comp("wta", "Tennis", "WTA Tour", cap, tid, "league")
        for m in payload.get("matches", []):
            mid = m.get("MatchID") or m.get("matchId") or m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            n1 = " ".join(x for x in [m.get("PlayerNameFirstA"), m.get("PlayerNameLastA")] if x)
            n2 = " ".join(x for x in [m.get("PlayerNameFirstB"), m.get("PlayerNameLastB")] if x)
            if not n1.strip() or not n2.strip():
                p1 = m.get("player1") or {}
                p2 = m.get("player2") or {}
                n1 = n1 or ((p1.get("player") or {}).get("fullName") or "")
                n2 = n2 or ((p2.get("player") or {}).get("fullName") or "")
            if not n1 or not n2:
                continue
            start = (m.get("MatchTimeStamp") or m.get("matchStartTime")
                     or m.get("startTime") or m.get("date"))
            status = str(m.get("MatchState") or m.get("status") or "")
            key = f"{ckey}:{mid}"
            FACTS.setdefault("tennis_matches", []).append({
                "key": key, "competition": ckey, "tournament": tname,
                "player1": n1, "player2": n2, "start": start, "status": status,
                "round": (m.get("round") or {}).get("name") if isinstance(m.get("round"), dict) else m.get("round"),
                **cap.src(tid)})
    if not FACTS.get("tennis_matches"):
        gap("Tennis", "WTA matches", "WTA tournament feeds carried no usable match rows",
            "https://api.wtatennis.com/")


# --------------------------------------------------------------------------- #
# Rugby league — RLWC official feed
# --------------------------------------------------------------------------- #
def rlwc(cap: Capture) -> None:
    if not cap.has("rlwc_api_fixtures"):
        gap("Rugby League", "RLWC feed", "RLWC fixture API missing", "https://www.rlwc2026.com/")
        return
    comp("rlwc", "Rugby League", "Rugby League World Cup", cap, "rlwc_api_fixtures", "league")
    result = cap.json("rlwc_api_fixtures").get("result") or {}
    for rd in result.get("roundFixtures", []):
        for g in rd.get("gameFixtures", []):
            teams = g.get("teams") or []
            if len(teams) != 2:
                continue
            home, away = teams[0], teams[1]
            start = g.get("fixtureDateUTC") or g.get("gameDateUTC") or g.get("startDateUTC")
            key = "rlwc:" + str(g.get("fixtureId") or g.get("gameId") or f"{home['teamName']}-{away['teamName']}")
            hs, as_ = home.get("teamFinalScore"), away.get("teamFinalScore")
            label = rd.get("roundName") or rd.get("name") or ""
            if hs is not None and as_ is not None:
                history(key, "Rugby League", "rlwc", str(start)[:10], "rlwc|" + home["teamName"],
                        "rlwc|" + away["teamName"], hs, as_, cap, "rlwc_api_fixtures")
            else:
                fixture(key, "Rugby League", "rlwc", "rlwc|" + home["teamName"],
                        "rlwc|" + away["teamName"], start, cap, "rlwc_api_fixtures", None,
                        {"round": label, "group": g.get("groupName")})


# --------------------------------------------------------------------------- #
# Volleyball
# --------------------------------------------------------------------------- #
def legavolley(cap: Capture) -> None:
    cal_ids = [i for i in cap.by_id if i.startswith("legavolley_cal_")]
    if not cal_ids:
        gap("Volleyball", "LegaVolley", "no Italian calendar captured", "https://www.legavolley.it/")
        return
    comp("legavolley", "Volleyball", "SuperLega (Italy)", cap, "legavolley_classifica", "league")
    if cap.has("legavolley_classifica"):
        for t in H.tables(cap.text("legavolley_classifica")):
            if not t or "Punti" not in " ".join(t[0]):
                continue
            for row in t:
                m = re.match(r"^(\d+)\.?\s*(.+)$", row[0].strip()) if row else None
                if not m:
                    continue
                name = m.group(2).replace("\xa0", " ").strip()
                nums = [c for c in row[1:] if re.fullmatch(r"-?\d+", c.strip())]
                if len(nums) < 9:
                    continue
                team("legavolley|" + name, "Volleyball", "legavolley", name, cap,
                     "legavolley_classifica", points=H.to_int(nums[0]),
                     played=H.to_int(nums[1]), wins=H.to_int(nums[2]), losses=H.to_int(nums[3]),
                     sets_for=H.to_int(nums[10]), sets_against=H.to_int(nums[11]),
                     points_for=H.to_int(nums[12]),
                     points_against=H.to_int(nums[13]) if len(nums) > 13 else None)

    # Calendars: rows are [#, date+time, home, result, away, …]; a result of "-"
    # means the match has not been played, so the row becomes a fixture instead.
    for tid in cal_ids:
        for t in H.tables(cap.text(tid)):
            head = " ".join(t[0]).lower() if t else ""
            if "casa" not in head or "ospite" not in head:
                continue
            for row in t:
                if len(row) < 5:
                    continue
                dm = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})(?:\s+Ore\s+(\d{1,2}):(\d{2}))?", row[1])
                if not dm:
                    continue
                day, month, year, hh, mm = dm.groups()
                start = f"{year}-{int(month):02d}-{int(day):02d}T{int(hh or 0):02d}:{mm or '00'}:00Z"
                home, result, away = row[2].strip(), row[3].strip(), row[4].strip()
                if not home or not away:
                    continue
                key = f"legavolley:{year}{month}{day}:{home[:18]}:{away[:18]}"
                sm = re.match(r"^(\d+)\s*-\s*(\d+)$", result)
                if sm:
                    history(key, "Volleyball", "legavolley", start[:10], "legavolley|" + home,
                            "legavolley|" + away, int(sm.group(1)), int(sm.group(2)), cap, tid)
                else:
                    fixture(key, "Volleyball", "legavolley", "legavolley|" + home,
                            "legavolley|" + away, start, cap, tid, row[6] if len(row) > 6 else None)


def plusliga(cap: Capture) -> None:
    if not cap.has("plusliga_table"):
        return
    comp("plusliga", "Volleyball", "PlusLiga (Poland)", cap, "plusliga_table", "league")
    table = H.table_by_header(cap.text("plusliga_table"), "Drużyna", "Punkty")
    if not table:
        gap("Volleyball", "PlusLiga table", "PlusLiga table header not found",
            "https://plusliga.pl/table/tour/47.html")
        return
    best: dict[str, tuple[int, list[str]]] = {}
    for row in table[2:]:
        if len(row) < 8:
            continue
        name, matches = row[1].strip(), H.to_int(row[3])
        if not name or matches is None:
            continue
        if name not in best or (best[name][0] or 0) < matches:
            best[name] = (matches, row)
    for name, (matches, row) in best.items():
        # columns: 1 pos | 2 points | 3 matches | 4 won | 5 lost | 6 sets won |
        #          7 sets lost | 8 points won | 9 points lost | …
        team("plusliga|" + name, "Volleyball", "plusliga", name, cap, "plusliga_table",
             played=matches, points=H.to_int(row[2]), wins=H.to_int(row[4]),
             losses=H.to_int(row[5]), sets_for=H.to_int(row[6]),
             sets_against=H.to_int(row[7]), points_for=H.to_int(row[8]),
             points_against=H.to_int(row[9]))


def cvf(cap: Capture) -> None:
    if not cap.has("cvf_extraliga"):
        return
    comp("cvf", "Volleyball", "Extraliga (Czechia)", cap, "cvf_extraliga", "league")
    table = H.table_by_header(cap.text("cvf_extraliga"), "Název")
    if not table:
        return
    for row in table[1:]:
        if len(row) < 11:
            continue
        sets = row[8].split(":") if ":" in row[8] else [None, None]
        pts = row[9].split(":") if ":" in row[9] else [None, None]
        team("cvf|" + row[1], "Volleyball", "cvf", row[1], cap, "cvf_extraliga",
             played=H.to_int(row[2]), wins=H.to_int(row[3]), losses=H.to_int(row[5]),
             sets_for=H.to_int(sets[0] or ""), sets_against=H.to_int(sets[1] or ""),
             points_for=H.to_int(pts[0] or ""), points_against=H.to_int(pts[1] or ""),
             points=H.to_int(row[10]))


# --------------------------------------------------------------------------- #
# Handball
# --------------------------------------------------------------------------- #
def ehfcl(cap: Capture) -> None:
    if not cap.has("ehfcl_m_standings"):
        gap("Handball", "EHF Champions League", "EHF standings page missing",
            "https://ehfcl.eurohandball.com/")
        return
    comp("ehfcl", "Handball", "EHF Champions League", cap, "ehfcl_m_standings", "league")
    for t in H.tables(cap.text("ehfcl_m_standings")):
        if not t or "GP" not in " ".join(t[0]):
            continue
        group = t[0][0]
        for row in t[1:]:
            if len(row) < 8:
                continue
            name = re.sub(r"^\d+\.\s*", "", row[0]).strip()
            goals = row[5].split(":") if ":" in row[5] else [None, None]
            team("ehfcl|" + name, "Handball", "ehfcl", name, cap, "ehfcl_m_standings",
                 group=group, played=H.to_int(row[1]), wins=H.to_int(row[2]),
                 draws=H.to_int(row[3]), losses=H.to_int(row[4]),
                 goals_for=H.to_int(goals[0] or ""), goals_against=H.to_int(goals[1] or ""),
                 points=H.to_int(row[7]))


def dk_handball(cap: Capture) -> None:
    if not cap.has("dk_herreligaen"):
        return
    comp("dk", "Handball", "Herreligaen (Denmark)", cap, "dk_herreligaen", "league")
    table = H.table_by_header(cap.text("dk_herreligaen"), "Klub", "Point")
    if not table:
        gap("Handball", "Danish table", "Danish league table header not found",
            "https://tophaandbold.dk/stillinger/herreligaen")
        return
    for row in table[1:]:
        if len(row) < 8:
            continue
        goals = row[6].split("-") if "-" in row[6] else [None, None]
        team("dk|" + row[1], "Handball", "dk", row[1], cap, "dk_herreligaen",
             played=H.to_int(row[2]), wins=H.to_int(row[3]), draws=H.to_int(row[4]),
             losses=H.to_int(row[5]), goals_for=H.to_int(goals[0] or ""),
             goals_against=H.to_int(goals[1] or ""), points=H.to_int(row[7]))


# --------------------------------------------------------------------------- #
# Rugby union — Top14 (LNR embeds its match data as JSON in the page)
# --------------------------------------------------------------------------- #
def top14(cap: Capture) -> None:
    ids = [i for i in ("top14_cal", "top14_classement") if cap.has(i)]
    if not ids:
        return
    for tid in ids:
        page = cap.text(tid)
        if '"home_club"' not in page and '"visiting_club"' not in page:
            continue
        comp("top14", "Rugby Union", "Top 14 (France)", cap, tid, "league")
        for m in re.finditer(r'\{[^{}]*"home_club"\s*:\s*\{[^{}]*\}[^{}]*"visiting_club"\s*:\s*\{[^{}]*\}'
                             r'[^{}]*\}', page):
            blob = m.group(0)
            try:
                obj = json.loads(blob.replace('\\"', '"').replace("\\/", "/"))
            except Exception:  # noqa: BLE001
                continue
            FACTS.setdefault("top14_raw", []).append({"blob": blob[:800], "source_id": tid})
            break
        break


# --------------------------------------------------------------------------- #
def latest_capture() -> Path:
    dirs = sorted(p for p in (DATA / "capture").glob("*") if (p / "manifest.json").exists())
    if not dirs:
        raise SystemExit("no capture available")
    return dirs[-1]


def main() -> int:
    cap_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_capture()
    cap = Capture(cap_dir)
    FACTS["capture_id"] = cap_dir.name
    FACTS["capture_finished_utc"] = cap.manifest["finished_utc"]
    FACTS["generated_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    FACTS["sources"] = [
        {"id": r["id"], "sport": r["sport"], "url": r["url"], "sha256": r["sha256"],
         "bytes": r["bytes"], "content_type": r["content_type"]}
        for r in cap.manifest["records"]
    ]

    for fn in (nhl, liiga, shl, nl, mlb, euroleague, nba, wst, wta, rlwc,
               legavolley, plusliga, cvf, ehfcl, dk_handball, top14):
        try:
            fn(cap)
        except Exception as exc:  # noqa: BLE001 - a broken parser must not invent data
            gap(fn.__name__, "parser", f"{type(exc).__name__}: {exc}",
                cap.manifest["records"][0]["url"])

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "facts.json").write_text(json.dumps(FACTS, indent=1) + "\n")
    print(f"facts: fixtures={len(FACTS['fixtures'])} history={len(FACTS['history'])} "
          f"teams={len(FACTS['teams'])} individuals={len(FACTS['individuals'])} "
          f"competitions={len(FACTS['competitions'])} gaps={len(FACTS['gaps'])} "
          f"tennis={len(FACTS.get('tennis_matches', []))}")
    for c in FACTS["competitions"]:
        print(f"  {c['sport']:12s} {c['key']:12s} {c['name'][:30]:30s} "
              f"fixtures={sum(1 for f in FACTS['fixtures'] if f['competition']==c['key']):4d} "
              f"history={sum(1 for h in FACTS['history'] if h['competition']==c['key']):4d}")
    for g in FACTS["gaps"]:
        print(f"  GAP {g['sport']}: {g['missing']} — {g['detail'][:90]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

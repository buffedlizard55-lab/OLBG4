#!/usr/bin/env python3
"""Board FX source readers.

Every reader takes the *committed capture directory* and returns fixtures whose
every numeric input is copied from an official response.  Nothing is estimated
here: estimation lives in originate.py and is labelled as our own model.
"""
from __future__ import annotations

import gzip
import html
import json
import os
import re
from datetime import datetime, timezone


class Capture:
    """Read-only view over one capture stamp (handles .gz and plain payloads)."""

    def __init__(self, path: str):
        self.path = path
        man = os.path.join(path, "manifest.json")
        self.manifest = json.load(open(man)) if os.path.exists(man) else {"records": []}
        self.by_id = {r["id"]: r for r in self.manifest.get("records", [])}

    def exists(self, tid: str) -> bool:
        return tid in self.by_id

    def raw(self, tid: str):
        rec = self.by_id.get(tid)
        if not rec:
            raise KeyError(tid)
        p = os.path.join(self.path, rec["file"])
        blob = open(p, "rb").read()
        if blob[:2] == b"\x1f\x8b":
            blob = gzip.decompress(blob)
        return blob

    def text(self, tid: str) -> str:
        return self.raw(tid).decode("utf-8", errors="replace")

    def json(self, tid: str):
        return json.loads(self.raw(tid))

    def url(self, tid: str) -> str:
        return self.by_id[tid]["url"]


def _clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _utc(date_str: str) -> str:
    """Normalise an ISO timestamp to ...Z; returns '' when unusable."""
    if not date_str:
        return ""
    s = date_str.replace(" ", "T")
    if s.endswith("Z"):
        return s
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------- ice hockey
def read_nhl(cap: Capture):
    """NHL official schedule API (api-web.nhle.com) + official standings."""
    out = []
    ids = sorted(i for i in cap.by_id if re.match(r"nhl_sched_2026_\d\d_\d\d$", i))
    seen = set()
    for tid in ids:
        data = cap.json(tid)
        for week in data.get("gameWeek", []):
            for g in week.get("games", []):
                if g.get("id") in seen:
                    continue
                if g.get("gameState") not in ("FUT", "PRE"):
                    continue
                seen.add(g.get("id"))
                away, home = g["awayTeam"], g["homeTeam"]
                out.append(
                    {
                        "id": f"fx_nhl_{g['id']}",
                        "sport": "Ice Hockey",
                        "sport_slug": "ice-hockey",
                        "competition": "NHL 2026-27 Regular Season",
                        "side_a": f"{away['placeName']['default']} {away['commonName']['default']}",
                        "side_b": f"{home['placeName']['default']} {home['commonName']['default']}",
                        "a_code": away.get("abbrev", ""),
                        "b_code": home.get("abbrev", ""),
                        "start_utc": _utc(g.get("startTimeUTC", "")),
                        "venue": (g.get("venue") or {}).get("default", ""),
                        "source_id": tid,
                        "source_url": cap.url(tid),
                        "source_name": "NHL official schedule API (api-web.nhle.com)",
                        "extra": {"game_type": g.get("gameType"), "nhl_id": g.get("id")},
                    }
                )
    return out


def read_nhl_standings(cap: Capture) -> dict:
    """abbrev -> official standings row (points %, GF/GP, GA/GP, L10, streak)."""
    tid = "nhl_standings_now" if cap.exists("nhl_standings_now") else "nhl_standings_2026_10_22"
    data = cap.json(tid)
    out = {}
    for r in data.get("standings", []):
        gp = r.get("gamesPlayed") or 0
        if not gp:
            continue
        out[r["teamAbbrev"]["default"]] = {
            "team": f"{r['teamName']['default']}",
            "gp": gp,
            "w": r.get("wins", 0),
            "l": r.get("losses", 0),
            "otl": r.get("otLosses", 0),
            "pts": r.get("points", 0),
            "pts_pct": r.get("pointPctg", 0),
            "gf": r.get("goalFor", 0),
            "ga": r.get("goalAgainst", 0),
            "gf_pg": round((r.get("goalFor") or 0) / gp, 3),
            "ga_pg": round((r.get("goalAgainst") or 0) / gp, 3),
            "l10": f"{r.get('l10Wins', 0)}-{r.get('l10Losses', 0)}-{r.get('l10OtLosses', 0)}",
            "streak": r.get("streakCode", ""),
            "home": f"{r.get('homeWins',0)}-{r.get('homeLosses',0)}-{r.get('homeOtLosses',0)}",
            "road": f"{r.get('roadWins',0)}-{r.get('roadLosses',0)}-{r.get('roadOtLosses',0)}",
            "source_id": tid,
            "source_url": cap.url(tid),
        }
    return out


def read_liiga(cap: Capture):
    """Liiga (Finnish elite league) official API v2 games + standings."""
    if not cap.exists("liiga_games"):
        return [], {}
    games = cap.json("liiga_games")
    rows = games if isinstance(games, list) else games.get("games", [])
    out = []
    for g in rows:
        home_t, away_t = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        home = home_t.get("teamName") or ""
        away = away_t.get("teamName") or ""
        start = g.get("start") or ""
        if not home or not away or not start:
            continue
        if g.get("ended"):
            continue
        out.append(
            {
                "id": f"fx_liiga_{g.get('id')}",
                "sport": "Ice Hockey",
                "sport_slug": "ice-hockey",
                "competition": "Liiga 2026-27 (Finland)",
                "side_a": away,
                "side_b": home,
                "start_utc": _utc(start),
                "venue": "",
                "source_id": "liiga_games",
                "source_url": cap.url("liiga_games"),
                "source_name": "Liiga official API v2 (liiga.fi)",
                "extra": {},
            }
        )
    table = {}
    if cap.exists("liiga_standings"):
        st = cap.json("liiga_standings")
        for r in st if isinstance(st, list) else (st.get("season") or st.get("standings") or []):
            name = r.get("team") or r.get("name") or r.get("teamName")
            if not name:
                continue
            table[name] = {
                "gp": r.get("games") or r.get("played") or 0,
                "w": r.get("wins", 0),
                "otw": r.get("overtimeWins", 0),
                "t": r.get("ties", 0),
                "otl": r.get("overtimeLosses", 0),
                "l": r.get("losses", 0),
                "pts": r.get("points", 0),
                "gf": r.get("goals") or r.get("goalsFor") or 0,
                "ga": r.get("goalsAgainst") or 0,
                "source_id": "liiga_standings",
                "source_url": cap.url("liiga_standings"),
            }
    return out, table


def read_shl(cap: Capture):
    """Swedish Hockey League official stats site (swehockey.se) tables."""
    if not cap.exists("shl_overview"):
        return [], {}
    s = cap.text("shl_overview")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S)
    fixtures, table = [], {}
    for r in rows:
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
        if len(cells) < 4:
            continue
        # schedule rows look like: date | time | home | - | away | result
        m = re.match(r"(\d{4}-\d{2}-\d{2})", cells[0])
        if m and len(cells) >= 5:
            home = cells[2] if cells[2] not in ("-", "") else cells[3]
            away = cells[4] if len(cells) > 4 else ""
            fixtures.append(
                {
                    "id": "fx_shl_" + re.sub(r"\W+", "_", f"{cells[0]}_{home}_{away}")[:60],
                    "sport": "Ice Hockey",
                    "sport_slug": "ice-hockey",
                    "competition": "SHL 2026-27 (Sweden)",
                    "side_a": away,
                    "side_b": home,
                    "start_utc": _utc(m.group(1) + "T" + (cells[1] if re.match(r"\d\d:\d\d", cells[1]) else "00:00")),
                    "venue": "",
                    "source_id": "shl_overview",
                    "source_url": cap.url("shl_overview"),
                    "source_name": "SHL official schedule (stats.swehockey.se)",
                    "extra": {},
                }
            )
    return fixtures, table


# ------------------------------------------------------------------- baseball
def read_mlb(cap: Capture):
    tid = "mlb_schedule" if cap.exists("mlb_schedule") else "mlb_ws_schedule"
    data = cap.json(tid)
    out = []
    for day in data.get("dates", []):
        for g in day.get("games", []):
            st = g.get("status", {})
            if st.get("abstractGameState") == "Final":
                continue
            away, home = g["teams"]["away"], g["teams"]["home"]
            out.append(
                {
                    "id": f"fx_mlb_{g['gamePk']}",
                    "sport": "Baseball",
                    "sport_slug": "baseball",
                    "competition": "MLB " + ("World Series" if g.get("gameType") == "W" else "2026 Postseason"),
                    "side_a": away["team"]["name"],
                    "side_b": home["team"]["name"],
                    "start_utc": _utc(g.get("gameDate", "")),
                    "venue": (g.get("venue") or {}).get("name", ""),
                    "source_id": tid,
                    "source_url": cap.url(tid),
                    "source_name": "MLB official Stats API (statsapi.mlb.com)",
                    "extra": {
                        "game_pk": g.get("gamePk"),
                        "series_game": g.get("seriesGameNumber"),
                        "if_necessary": g.get("ifNecessary"),
                        "away_record": away.get("leagueRecord", {}),
                        "home_record": home.get("leagueRecord", {}),
                        "away_id": away["team"].get("id"),
                        "home_id": home["team"].get("id"),
                        "away_pitcher": (away.get("probablePitcher") or {}).get("fullName", ""),
                        "home_pitcher": (home.get("probablePitcher") or {}).get("fullName", ""),
                    },
                }
            )
    return out


def read_mlb_standings(cap: Capture) -> dict:
    tid = "mlb_standings" if cap.exists("mlb_standings") else "mlb_standings_2026"
    data = cap.json(tid)
    out = {}
    for rec in data.get("records", []):
        for t in rec.get("teamRecords", []):
            name = t["team"]["name"]
            gp = t.get("gamesPlayed") or 0
            entry = {
                "w": t.get("wins", 0),
                "l": t.get("losses", 0),
                "pct": t.get("winningPercentage", ""),
                "rs": t.get("runsScored", 0),
                "ra": t.get("runsAllowed", 0),
                "rs_pg": round((t.get("runsScored") or 0) / gp, 3) if gp else 0,
                "ra_pg": round((t.get("runsAllowed") or 0) / gp, 3) if gp else 0,
                "gp": gp,
                "source_id": tid,
                "source_url": cap.url(tid),
            }
            out[name] = entry
            out[f"id:{t['team'].get('id')}"] = entry
    return out


# ----------------------------------------------------------------- basketball
def read_euroleague(cap: Capture, tid: str, comp: str):
    if not cap.exists(tid):
        return []
    data = cap.json(tid).get("data", [])
    out = []
    for g in data:
        if g.get("played"):
            continue
        local, road = g.get("local", {}), g.get("road", {})
        lc = local.get("club", {}).get("name")
        rc = road.get("club", {}).get("name")
        if not lc or not rc:
            continue
        out.append(
            {
                "id": f"fx_{tid}_{g.get('identifier')}",
                "sport": "Basketball",
                "sport_slug": "basketball",
                "competition": comp,
                "side_a": rc,
                "side_b": lc,
                "start_utc": _utc(g.get("utcDate", "")),
                "venue": "",
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "EuroLeague official API (api-live.euroleague.net)",
                "extra": {"round": g.get("round"), "identifier": g.get("identifier")},
            }
        )
    return out


def euroleague_table(cap: Capture, tid: str) -> dict:
    """Standings computed only from official completed-game scores in the payload."""
    if not cap.exists(tid):
        return {}
    data = cap.json(tid).get("data", [])
    tab = {}
    for g in data:
        if not g.get("played"):
            continue
        lc = g.get("local", {})
        rc = g.get("road", {})
        lname = lc.get("club", {}).get("name")
        rname = rc.get("club", {}).get("name")
        ls, rs = lc.get("score"), rc.get("score")
        if not lname or not rname or ls is None or rs is None:
            continue
        for name, pf, pa in ((lname, ls, rs), (rname, rs, ls)):
            t = tab.setdefault(name, {"gp": 0, "w": 0, "l": 0, "pf": 0, "pa": 0})
            t["gp"] += 1
            t["pf"] += pf
            t["pa"] += pa
            if pf > pa:
                t["w"] += 1
            else:
                t["l"] += 1
    for name, t in tab.items():
        t["pf_pg"] = round(t["pf"] / t["gp"], 3)
        t["pa_pg"] = round(t["pa"] / t["gp"], 3)
        t["source_id"] = tid
        t["source_url"] = cap.url(tid)
    return tab


# ------------------------------------------------------------------ OLBG tips
OLBG_SPORT = {
    "olbg_baseball_12": "Baseball",
    "olbg_basketball_4": "Basketball",
    "olbg_basketball_nba": "Basketball",
    "olbg_basketball_euroleague": "Basketball",
    "olbg_cricket_7": "Cricket",
    "olbg_darts_15": "Darts",
    "olbg_gaelic_25": "Gaelic Sports",
    "olbg_golf_5": "Golf",
    "olbg_greyhounds_28": "Greyhounds",
    "olbg_handball_20": "Handball",
    "olbg_ice_hockey_13": "Ice Hockey",
    "olbg_ice_hockey_nhl": "Ice Hockey",
    "olbg_motor_racing_14": "Motor Racing",
    "olbg_rugby_league_10": "Rugby League",
    "olbg_rugby_union_9": "Rugby Union",
    "olbg_snooker_8": "Snooker",
    "olbg_tennis_3": "Tennis",
    "olbg_volleyball_21": "Volleyball",
}
_TIP_FIELDS = ("selection", "market_alias", "odds", "american_odds", "event_name_alias",
               "eventUrl", "leagueUrl", "event_start_unix_timestamp", "confidence", "expired")


def _tips(text: str):
    """Pull the SvelteKit tip objects out of an OLBG hub page (JS object literals)."""
    out = []
    for m in re.finditer(r'\{id:"[0-9a-f]{40}"', text):
        chunk = text[m.start(): m.start() + 1600]
        rec = {}
        for f in _TIP_FIELDS:
            mm = re.search(rf'{f}:"([^"]*)"', chunk) or re.search(rf'{f}:(\d+)', chunk)
            rec[f] = mm.group(1) if mm else ""
        if rec.get("event_name_alias"):
            out.append(rec)
    return out


def read_olbg(cap: Capture):
    """OLBG sport-hub listings: taxonomy + the events OLBG actually lists."""
    events = {}
    for tid, sport in OLBG_SPORT.items():
        if not cap.exists(tid):
            continue
        for t in _tips(cap.text(tid)):
            key = (sport, t["event_name_alias"], t["eventUrl"].split("?")[0])
            ev = events.setdefault(
                key,
                {
                    "sport": sport,
                    "event": t["event_name_alias"],
                    "event_url": "https://www.olbg.com" + t["eventUrl"] if t["eventUrl"].startswith("/") else t["eventUrl"],
                    "event_id": (re.search(r"event_id=(\d+)", t["eventUrl"]) or [None, ""])[1],
                    "start_utc": _utc(datetime.fromtimestamp(int(t["event_start_unix_timestamp"]), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")) if t["event_start_unix_timestamp"].isdigit() else "",
                    "hub": tid,
                    "hub_url": cap.url(tid),
                    "tips": [],
                },
            )
            ev["tips"].append(
                {
                    "selection": t["selection"],
                    "market": t["market_alias"],
                    "decimal": t["odds"],
                    "american": t["american_odds"],
                    "confidence": t["confidence"],
                }
            )
    return list(events.values())


# ---------------------------------------------------------------------- tennis
def read_wta(cap: Capture, tid: str):
    if not cap.exists(tid):
        return []
    data = cap.json(tid)
    out = []
    for m in data.get("matches", []):
        if m.get("MatchState") == "F" or m.get("Winner"):
            continue
        a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
        b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
        if not a or not b:
            continue
        out.append(
            {
                "id": f"fx_{tid}_{m.get('MatchID')}",
                "sport": "Tennis",
                "sport_slug": "tennis",
                "competition": data.get("tournament", {}).get("title", tid),
                "side_a": a,
                "side_b": b,
                "start_utc": "",
                "venue": data.get("tournament", {}).get("city", ""),
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "WTA official tournament match feed (api.wtatennis.com)",
                "extra": {"round": m.get("RoundID"), "seed_a": m.get("SeedA", ""), "seed_b": m.get("SeedB", ""),
                          "draw": m.get("DrawLevelType"), "match_type": m.get("DrawMatchType")},
            }
        )
    return out


def read_atp_pdf(cap: Capture, tid: str):
    """ATP order-of-play PDF -> scheduled matches (pypdf)."""
    if not cap.exists(tid):
        return []
    try:
        import io

        from pypdf import PdfReader
    except Exception:  # noqa: BLE001
        return []
    try:
        reader = PdfReader(io.BytesIO(cap.raw(tid)))
        text = "\n".join((p.extract_text() or "") for p in reader.pages[:6])
    except Exception:  # noqa: BLE001
        return []
    out = []
    # lines such as "Jannik Sinner (1) v Alexander Zverev (2)" or "Sinner J. v Zverev A."
    for m in re.finditer(r"^(.{3,40}?)\s+v\s+(.{3,40}?)$", text, re.M):
        a, b = _clean(m.group(1)), _clean(m.group(2))
        if not a or not b or "doubles" in a.lower():
            continue
        out.append(
            {
                "id": "fx_" + tid + "_" + re.sub(r"\W+", "_", a + "_" + b)[:50],
                "sport": "Tennis",
                "sport_slug": "tennis",
                "competition": "ATP " + tid,
                "side_a": a,
                "side_b": b,
                "start_utc": "",
                "venue": "",
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "ATP official order of play (protennislive.com)",
                "extra": {},
            }
        )
    return out


# --------------------------------------------------------------------- snooker
def read_snooker_org(cap: Capture, tid: str = "snooker_org_2548"):
    if not cap.exists(tid):
        return []
    s = cap.text(tid)
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) >= 7:
            rows.append(cells)
    out, round_name, best_of = [], "", ""
    for cells in rows:
        joined = " ".join(cells)
        m = re.search(r"(Final|Semi-?finals?|Quarter-?finals?|Round \d+|Last \d+)\s*\(?\s*Best of (\d+)", joined, re.I)
        if m:
            round_name, best_of = m.group(1), m.group(2)
            continue
        p1 = next((c for c in cells if re.search(r"[A-Za-z]", c) and " v " not in c and c not in ("v",)), "")
        p2 = ""
        for i, c in enumerate(cells):
            if c.strip().lower() == "v" and i > 0:
                back = [x for x in cells[:i] if re.search(r"[A-Za-z]", x)]
                fwd = [x for x in cells[i + 1:] if re.search(r"[A-Za-z]", x) and not re.match(r"^(Sat|Sun|Fri|Mon|Tue|Wed|Thu|\d{4}-)", x)]
                p1 = back[-1] if back else ""
                p2 = fwd[-1] if fwd else ""
                break
        if not p1 or not p2:
            continue
        p1, p2 = _clean(p1), _clean(p2)
        if "/" in p1 or "/" in p2:  # unresolved feeder match
            continue
        date = next((c for c in cells if re.search(r"\d{4}-\d{2}-\d{2}|\b(Sat|Sun|Fri|Mon)\b", c)), "")
        out.append(
            {
                "id": "fx_" + tid + "_" + re.sub(r"\W+", "_", p1 + "_" + p2)[:60],
                "sport": "Snooker",
                "sport_slug": "snooker",
                "competition": "BetVictor Northern Ireland Open 2026",
                "side_a": p1,
                "side_b": p2,
                "start_utc": "",
                "venue": "",
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "snooker.org official event results/schedule (event 2548)",
                "extra": {"round": round_name, "best_of": best_of, "date_text": date},
            }
        )
    return out


# --------------------------------------------------------------------- cricket
def read_cricket_au(cap: Capture, tid: str = "cricket_au_fixtures"):
    if not cap.exists(tid):
        return []
    s = cap.text(tid)
    m = re.search(r"window\.FIXTURES_DATA\s*=\s*JSON\.parse\('(.*?)'\);", s, re.S)
    if not m:
        return []
    blob = m.group(1)
    blob = blob.encode().decode("unicode_escape")
    data = json.loads(blob)
    out = []
    for f in data:
        if f.get("isCompleted"):
            continue
        home, away = f.get("homeTeam", {}), f.get("awayTeam", {})
        out.append(
            {
                "id": f"fx_ca_{f.get('id')}",
                "sport": "Cricket",
                "sport_slug": "cricket",
                "competition": f.get("competition", {}).get("name", ""),
                "side_a": away.get("name", ""),
                "side_b": home.get("name", ""),
                "start_utc": _utc(f.get("startDateTime", "")),
                "venue": ", ".join(x for x in (f.get("venue", {}).get("name", ""), f.get("venue", {}).get("location", "")) if x),
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "Cricket Australia official fixtures (cricket.com.au)",
                "extra": {"game_type": f.get("gameType", ""), "match_name": f.get("name", "")},
            }
        )
    return out


# ------------------------------------------------------------------ gaelic games
def read_gaa(cap: Capture, tid: str = "gaa_fixtures"):
    if not cap.exists(tid):
        return []
    s = cap.text(tid)
    out = []
    for m in re.finditer(r'matchId\\":\\"([0-9a-f\-]{36})\\"(.{0,4000}?)(?=\\"url\\":|$)', s, re.S):
        chunk = m.group(0)

        def grab(field):
            pattern = field + r'\\\":\{\\\"id\\\":\\"[^"]*\\",\\"name\\\":\\"([^"\\]+)'
            mm = re.search(pattern, chunk)
            return _clean(mm.group(1)) if mm else ""

        home, away = grab("homeTeam"), grab("awayTeam")
        rnd = re.search(r'roundName\\":\\"([^"\\]+)', chunk)
        grp = re.search(r'groupName\\":\\"([^"\\]+)', chunk)
        date = re.search(r'matchStartDate\\":\\"([0-9T:+\-]+)', chunk)
        time = re.search(r'matchStartTime\\":\\"([0-9:]+)', chunk)
        stadium = re.search(r'stadiumName\\":\\"([^"\\]+)', chunk)
        tbc = re.search(r'isTbc\\":(true|false)', chunk)
        if home and away:
            start = ""
            if date and time:
                start = _utc(date.group(1)[:10] + "T" + time.group(1))
            out.append(
                {
                    "id": "fx_gaa_" + m.group(1),
                    "sport": "Gaelic Sports",
                    "sport_slug": "gaelic-sports",
                    "competition": _clean(grp.group(1)) if grp else "GAA",
                    "side_a": away,
                    "side_b": home,
                    "start_utc": start,
                    "venue": _clean(stadium.group(1)) if stadium else "",
                    "source_id": tid,
                    "source_url": cap.url(tid),
                    "source_name": "GAA official fixtures (gaa.ie)",
                    "extra": {"round": _clean(rnd.group(1)) if rnd else "",
                              "tbc": (tbc.group(1) == "true") if tbc else None},
                }
            )
    return out


# ------------------------------------------------------------------- rugby union
_URC_MONTH = {m: i for i, m in enumerate(["JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE", "JULY",
                                           "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"], 1)}


def read_urc(cap: Capture, tid: str = "urc_fixtures_in_full"):
    if not cap.exists(tid):
        return []
    s = cap.text(tid)
    t = re.sub(r"<script.*?</script>", "", s, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    t = html.unescape(t)
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in t.split("\n")]
    lines = [ln for ln in lines if ln]
    out, rnd, day = [], "", ""
    i = 0
    while i < len(lines):
        ln = lines[i]
        if re.fullmatch(r"ROUND \d+", ln):
            rnd = ln.title()
        elif re.fullmatch(r"(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY), [A-Z]+ \d{1,2}", ln):
            day = ln
        elif " v " in ln and len(ln) < 70 and not ln.startswith("Live"):
            venue_line = lines[i + 1] if i + 1 < len(lines) else ""
            if "KO" in venue_line:
                a, b = [x.strip() for x in ln.split(" v ", 1)]
                ko = re.search(r"KO (\d{1,2})\.(\d{2})", venue_line)
                venue = venue_line.split(", KO")[0]
                start = ""
                if day:
                    dm = re.match(r"(?:[A-Z]+), ([A-Z]+) (\d{1,2})", day)
                    if dm and dm.group(1) in _URC_MONTH and ko:
                        start = f"2026-{_URC_MONTH[dm.group(1)]:02d}-{int(dm.group(2)):02d}T{int(ko.group(1)):02d}:{ko.group(2)}:00Z"
                out.append(
                    {
                        "id": "fx_urc_" + re.sub(r"\W+", "_", f"{rnd}_{a}_{b}")[:60],
                        "sport": "Rugby Union",
                        "sport_slug": "rugby-union",
                        "competition": "United Rugby Championship 2026-27",
                        "side_a": a,
                        "side_b": b,
                        "start_utc": start,
                        "venue": venue,
                        "source_id": tid,
                        "source_url": cap.url(tid),
                        "source_name": "URC official 2026/27 fixtures in full (unitedrugby.com)",
                        "extra": {"round": rnd, "day_text": day, "ko_text": ko.group(0) if ko else ""},
                    }
                )
                i += 1
        i += 1
    return out


# ------------------------------------------------------------------ volleyball
def read_legavolley(cap: Capture, tid: str):
    """SuperLega official calendar (legavolley.it): fixture rows + published table."""
    if not cap.exists(tid):
        return [], {}
    s = cap.text(tid)
    fixtures = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 5:
            continue
        date_m = re.match(r"[A-Za-zì]+\s+(\d{1,2})/(\d{1,2})/(\d{4})\s+Ore\s+(\d{1,2}):(\d{2})", cells[1])
        if not date_m:
            continue
        home, result, away = cells[2], cells[3], cells[4]
        if not home or not away:
            continue
        fixtures.append(
            {
                "id": "fx_lv_" + re.sub(r"\W+", "_", f"{cells[0]}_{home}_{away}")[:60],
                "sport": "Volleyball",
                "sport_slug": "volleyball",
                "competition": "SuperLega Credem Banca 2026-27 (Italy)",
                "side_a": away,
                "side_b": home,
                "start_utc": f"{date_m.group(3)}-{int(date_m.group(2)):02d}-{int(date_m.group(1)):02d}T{int(date_m.group(4)):02d}:{date_m.group(5)}:00Z",
                "venue": cells[6] if len(cells) > 6 else "",
                "source_id": tid,
                "source_url": cap.url(tid),
                "source_name": "Lega Pallavolo Serie A official calendar (legavolley.it)",
                "extra": {"round": cells[0], "result": result, "played": bool(result and re.match(r"\d-\d", result))},
            }
        )
    table = {}
    if cap.exists("legavolley_classifica"):
        s2 = cap.text("legavolley_classifica")
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s2, re.S):
            cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) < 15:
                continue
            m = re.match(r"(\d+)\s+(.+)", cells[0])
            if not m:
                continue
            try:
                table[m.group(2)] = {
                    "rank": int(m.group(1)),
                    "pts": int(cells[1]),
                    "gp": int(cells[2]),
                    "w": int(cells[3]),
                    "l": int(cells[4]),
                    "sw": int(cells[11]),
                    "sl": int(cells[12]),
                    "pw": int(cells[13]),
                    "pl": int(cells[14]),
                    "source_id": "legavolley_classifica",
                    "source_url": cap.url("legavolley_classifica"),
                }
            except (ValueError, IndexError):
                continue
    return fixtures, table


def read_plusliga(cap: Capture, tid: str = "plusliga_table"):
    """PlusLiga official table: one row per club per matchday, latest row wins."""
    if not cap.exists(tid):
        return {}
    s = cap.text(tid)
    table = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 10:
            continue
        team = cells[1]
        try:
            played = int(cells[4])
            sw, sl = int(cells[6]), int(cells[7])
            pw, pl = int(cells[8]), int(cells[9])
            pts = int(cells[2])
        except (ValueError, IndexError):
            continue
        prev = table.get(team)
        if prev and prev["gp"] >= played:
            continue
        table[team] = {"gp": played, "pts": pts, "sw": sw, "sl": sl, "pw": pw, "pl": pl,
                       "source_id": tid, "source_url": cap.url(tid)}
    return table


def read_cvf(cap: Capture, tid: str = "cvf_extraliga"):
    """Czech Extraliga official table (sets + ball points)."""
    if not cap.exists(tid):
        return {}
    s = cap.text(tid)
    table = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 10 or not cells[0].endswith("."):
            continue
        team = cells[1]
        try:
            gp, v3, v2, p1, p0 = (int(cells[2]), int(cells[3]), int(cells[4]), int(cells[5]), int(cells[6]))
            sw, sl = [int(x) for x in cells[8].split(":")]
            pw, pl = [int(x) for x in cells[9].split(":")]
        except (ValueError, IndexError):
            continue
        table[team] = {"gp": gp, "pts": 3 * v3 + 2 * v2 + p1, "sw": sw, "sl": sl, "pw": pw, "pl": pl,
                       "source_id": tid, "source_url": cap.url(tid)}
    return table


# -------------------------------------------------------------------- handball
def read_herreligaen(cap: Capture, tid: str = "dk_herreligaen"):
    if not cap.exists(tid):
        return {}
    s = cap.text(tid)
    table = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
        cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 8:
            continue
        try:
            gf, ga = [int(x) for x in cells[6].split("-")]
            table[cells[1]] = {"gp": int(cells[2]), "w": int(cells[3]), "d": int(cells[4]), "l": int(cells[5]),
                               "gf": gf, "ga": ga, "pts": int(cells[7]),
                               "source_id": tid, "source_url": cap.url(tid)}
        except (ValueError, IndexError):
            continue
    return table


# ------------------------------------------------------------------------- golf
def read_pga(cap: Capture, tid: str):
    """PGA Tour official tournament page -> tournament meta + live leaderboard."""
    if not cap.exists(tid):
        return None
    s = cap.text(tid)
    i = s.find("__NEXT_DATA__")
    if i < 0:
        return None
    j = s.find(">", i) + 1
    k = s.find("</script>", j)
    try:
        d = json.loads(s[j:k])
    except json.JSONDecodeError:
        return None
    queries = d.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
    lb = None
    tour = None
    for q in queries:
        key = q.get("queryKey") or []
        if key and key[0] == "leaderboard":
            lb = q.get("state", {}).get("data")
        if key and key[0] == "tournament" and isinstance(q.get("state", {}).get("data"), dict):
            tour = q["state"]["data"]
    if not lb:
        return None
    players = []
    for p in lb.get("players", []):
        sc = p.get("scoringData", {})
        players.append(
            {
                "name": p.get("player", {}).get("displayName", ""),
                "position": sc.get("position", ""),
                "total": sc.get("total", ""),
                "total_sort": sc.get("totalSort"),
                "thru": sc.get("thru", ""),
                "rounds": sc.get("rounds", []),
            }
        )
    return {
        "tournament": (tour or {}).get("tournamentName", ""),
        "status": (tour or {}).get("tournamentStatus", ""),
        "current_round": (tour or {}).get("currentRound"),
        "display_date": (tour or {}).get("displayDate", ""),
        "location": (tour or {}).get("tournamentLocation", ""),
        "tournament_id": (tour or {}).get("id", ""),
        "players": players,
        "source_id": tid,
        "source_url": cap.url(tid),
    }


# ------------------------------------------------------------------ motor sport
def read_f1(cap: Capture):
    s = cap.text("f1_drivers") if cap.exists("f1_drivers") else ""
    standings = []
    if s:
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", s, re.S):
            cells = [_clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(cells) >= 5 and cells[0].isdigit():
                standings.append({"pos": int(cells[0]), "driver": cells[1], "nationality": cells[2],
                                  "team": cells[3], "pts": int(re.sub(r"\D", "", cells[4]) or 0)})
    races = []
    if cap.exists("f1_racing_2026"):
        t = re.sub(r"<script.*?</script>", "", cap.text("f1_racing_2026"), flags=re.S)
        t = re.sub(r"<[^>]+>", "\n", t)
        t = html.unescape(t)
        lines = [re.sub(r"\s+", " ", x).strip() for x in t.split("\n")]
        lines = [x for x in lines if x]
        for i, ln in enumerate(lines):
            if re.fullmatch(r"ROUND \d+", ln) and i >= 3:
                races.append({"round": ln, "name": lines[i - 2], "dates": lines[i - 1]})
    return {"standings": standings, "races": races,
            "source_id": "f1_drivers", "source_url": cap.url("f1_drivers") if cap.exists("f1_drivers") else ""}


# --------------------------------------------------------------------- greyhound
def read_gbgb(cap: Capture, tid: str = "gbgb_results_api"):
    if not cap.exists(tid):
        return []
    data = cap.json(tid)
    return data.get("items", [])


# ------------------------------------------------------------------ WST snooker
def read_wst(cap: Capture):
    """Official World Snooker Tour match API + official world ranking positions."""
    if not cap.exists("wst_matches_api"):
        return [], {}
    ranks = {}
    if cap.exists("wst_rankings_api"):
        for block in cap.json("wst_rankings_api").get("data", []):
            a = block.get("attributes", {})
            if a.get("rankingType") not in ("livePrizeMoney", "prizeMoney"):
                continue
            for pos in a.get("positions", []):
                pid = pos.get("playerID")
                if pid and pid not in ranks:
                    ranks[pid] = pos.get("position")
    out = []
    for m in cap.json("wst_matches_api").get("data", []):
        a = m.get("attributes", {})
        name = a.get("name", "")
        if not name or "Winner of" in name or "TBD" in name:
            continue
        if a.get("status") not in ("Scheduled", "Live", "In Progress"):
            continue
        if a.get("homePlayerScore") or a.get("awayPlayerScore"):
            continue
        parts = [p.strip() for p in re.split(r"\s+vs\s+", name)]
        if len(parts) != 2:
            continue
        start = a.get("startDateTime", "")
        start_utc = ""
        if start:
            try:
                from datetime import datetime as _dt
                from zoneinfo import ZoneInfo
                local = _dt.strptime(start, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Europe/London"))
                start_utc = local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:  # noqa: BLE001
                start_utc = ""
        out.append(
            {
                "id": "fx_wst_" + m.get("id", "")[:18],
                "sport": "Snooker",
                "sport_slug": "snooker",
                "competition": (a.get("tournament") or {}).get("name", "World Snooker Tour"),
                "side_a": parts[1],
                "side_b": parts[0],
                "start_utc": start_utc,
                "venue": "",
                "source_id": "wst_matches_api",
                "source_url": cap.url("wst_matches_api"),
                "source_name": "WST official match API (matches.snooker.web.gc.wstservices.co.uk)",
                "extra": {"round": a.get("round", ""), "best_of": a.get("numberOfFrames"),
                          "rank_a": ranks.get(a.get("awayPlayerID")), "rank_b": ranks.get(a.get("homePlayerID")),
                          "local_uk": start, "match_id": m.get("id")},
            }
        )
    return out, ranks


# ------------------------------------------------------------------ rugby league
def read_rlwc(cap: Capture):
    if not cap.exists("rlwc_api_fixtures"):
        return []
    data = cap.json("rlwc_api_fixtures").get("result", {})
    out = []
    for rnd in data.get("roundFixtures", []):
        for g in rnd.get("gameFixtures", []):
            teams = g.get("teams") or []
            if len(teams) != 2:
                continue
            home = next((t for t in teams if t.get("isHomeTeam")), teams[0])
            away = next((t for t in teams if t is not home), teams[1])
            out.append(
                {
                    "id": f"fx_rlwc_{g.get('gameId')}",
                    "sport": "Rugby League",
                    "sport_slug": "rugby-league",
                    "competition": f"Rugby League World Cup 2026 - {rnd.get('roundName','')}".strip(" -"),
                    "side_a": away.get("teamName", ""),
                    "side_b": home.get("teamName", ""),
                    "start_utc": _utc(g.get("startTimeUTC", "")),
                    "venue": ", ".join(x for x in (g.get("venueName", ""), g.get("city", "")) if x),
                    "source_id": "rlwc_api_fixtures",
                    "source_url": cap.url("rlwc_api_fixtures"),
                    "source_name": "RLWC 2026 official fixtures API (rlwc2026.com)",
                    "extra": {"round": rnd.get("roundName", ""), "group": g.get("groupName", ""),
                              "state": g.get("gameStateName", ""),
                              "home_score": home.get("teamFinalScore"),
                              "away_score": away.get("teamFinalScore"),
                              "line": g.get("teamLineAmount")},
                }
            )
    return out

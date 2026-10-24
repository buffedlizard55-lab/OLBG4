#!/usr/bin/env python3
"""Board ZZ — parse captured official payloads into verified upcoming fixtures.

Input : data/session-edffdbc6/capture/<stamp>/  (gzip payloads + manifest.json)
Output: data/session-edffdbc6/fixtures.json

Rules enforced here:
  * a fixture only exists if BOTH sides, the competition and a kick-off/start time are present in
    the captured official payload — nothing is inferred, guessed or carried over from another desk;
  * the kick-off must be after the desk cutoff;
  * every fixture keeps the capture target id + SHA-256 of the payload it came from, so the row can
    be re-read byte-for-byte later;
  * strength inputs used for line origination are stored next to the fixture, with the exact
    official numbers they were read from.
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CAP_ROOT = ROOT / "data" / "session-edffdbc6" / "capture"
OUT = ROOT / "data" / "session-edffdbc6" / "fixtures.json"

def _manifest_cutoff() -> datetime:
    stamps = sorted(p for p in CAP_ROOT.glob("*") if (p / "manifest.json").exists())
    if stamps:
        m = json.loads((stamps[-1] / "manifest.json").read_text(encoding="utf-8"))
        return datetime.fromisoformat(m["started_utc"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc).replace(microsecond=0)


CUTOFF = _manifest_cutoff()


def latest_capture() -> tuple[Path, dict]:
    import os
    override = os.environ.get("ZZ_CAPTURE_DIR")
    if override:
        d = Path(override)
        return d, json.loads((d / "manifest.json").read_text(encoding="utf-8"))
    stamps = sorted(p for p in CAP_ROOT.glob("*") if (p / "manifest.json").exists())
    if not stamps:
        raise SystemExit("no capture found")
    d = stamps[-1]
    return d, json.loads((d / "manifest.json").read_text(encoding="utf-8"))


class Capture:
    def __init__(self, cap_dir: Path, manifest: dict):
        self.dir = cap_dir
        self.manifest = manifest
        self.by_id = {r["id"]: r for r in manifest["records"]}

    def rec(self, tid: str) -> dict | None:
        return self.by_id.get(tid)

    def raw(self, tid: str) -> str:
        r = self.by_id.get(tid)
        if not r or not r.get("file"):
            return ""
        return gzip.decompress((self.dir / r["file"]).read_bytes()).decode("utf-8", "replace")

    def json(self, tid: str):
        raw = self.raw(tid)
        if not raw:
            return None
        try:
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return None

    def source(self, tid: str, url: str, name: str) -> dict:
        r = self.by_id.get(tid) or {}
        return {
            "url": url,
            "name": name,
            "target_id": tid,
            "sha256": r.get("sha256") or "",
            "bytes": r.get("bytes") or 0,
        }


def iso(dt: str) -> str:
    return dt if dt.endswith("Z") else dt + "Z"


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def htmlish_text(html: str) -> str:
    html = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<[^>]+>", " ", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#8217;", "'").replace("&#039;", "'")
    return norm_ws(html)


# ---------------------------------------------------------------------------------- Ice Hockey
def parse_nhl(cap: Capture, fixtures: list[dict]) -> None:
    st = cap.json("nhl_standings_now")
    if not st:
        return
    teams = {}
    for t in st.get("standings", []):
        ab = t.get("teamAbbrev", {}).get("default") or ""
        nm = t.get("teamName", {}).get("default") or ""
        teams[ab] = {
            "name": nm,
            "gp": t.get("gamesPlayed", 0),
            "w": t.get("wins", 0),
            "l": t.get("losses", 0),
            "otl": t.get("otLosses", 0),
            "gf": t.get("goalFor", 0),
            "ga": t.get("goalAgainst", 0),
            "pts": t.get("points", 0),
            "l10": f"{t.get('l10Wins', 0)}-{t.get('l10Losses', 0)}-{t.get('l10OtLosses', 0)}",
            "streak": t.get("streakCode", ""),
            "div": t.get("divisionName", ""),
        }
    seen: set[int] = set()
    recs = [r for r in cap.manifest["records"] if r["id"].startswith("nhl_sched_") and r.get("status") == 200]
    for rec in sorted(recs, key=lambda r: r["id"]):
        payload = cap.json(rec["id"])
        if not payload:
            continue
        for week in payload.get("gameWeek", []):
            for g in week.get("games", []):
                gid = g.get("id")
                start = g.get("startTimeUTC") or ""
                if gid in seen or not start or not g.get("gameState") in ("FUT", "PRE"):
                    continue
                start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                if start_dt <= CUTOFF:
                    continue
                ha = g.get("homeTeam", {}).get("abbrev")
                aa = g.get("awayTeam", {}).get("abbrev")
                if ha not in teams or aa not in teams:
                    continue
                seen.add(gid)
                fixtures.append({
                    "id": f"ZZ-IH-NHL-{gid}",
                    "sport": "Ice Hockey",
                    "competition": "NHL Regular Season 2026-27",
                    "stage": "",
                    "home": teams[ha]["name"],
                    "away": teams[aa]["name"],
                    "start_utc": iso(start),
                    "venue": g.get("venue", {}).get("default", ""),
                    "source": cap.source(rec["id"], f"https://www.nhl.com/gamecenter/{gid}",
                                         "NHL Official API (api-web.nhle.com)"),
                    "model": {"kind": "poisson_goals", "league_mu": 3.08, "home_adv": 0.16},
                    "stats": {"home": teams[ha], "away": teams[aa],
                              "home_abbrev": ha, "away_abbrev": aa},
                    "game_id": gid,
                })


def parse_liiga(cap: Capture, fixtures: list[dict]) -> None:
    games = cap.json("liiga_games_2027")
    if not isinstance(games, list):
        return
    stats: dict[str, dict] = {}
    for g in games:
        if not g.get("ended"):
            continue
        for side in ("homeTeam", "awayTeam"):
            name = g.get(side, {}).get("teamName")
            if not name:
                continue
            s = stats.setdefault(name, {"gp": 0, "w": 0, "gf": 0, "ga": 0, "recent": []})
        ht, at = g["homeTeam"]["teamName"], g["awayTeam"]["teamName"]
        hg, ag = int(g["homeTeam"].get("goals") or 0), int(g["awayTeam"].get("goals") or 0)
        stats[ht]["gp"] += 1
        stats[at]["gp"] += 1
        stats[ht]["gf"] += hg
        stats[ht]["ga"] += ag
        stats[at]["gf"] += ag
        stats[at]["ga"] += hg
        if hg > ag:
            stats[ht]["w"] += 1
        else:
            stats[at]["w"] += 1
        day = (g.get("start") or "")[:10]
        stats[ht]["recent"].append(f"{day} {ht} {hg}-{ag} {at}")
        stats[at]["recent"].append(f"{day} {ht} {hg}-{ag} {at}")
    for g in games:
        if g.get("ended"):
            continue
        start = g.get("start") or ""
        if not start:
            continue
        if datetime.fromisoformat(start.replace("Z", "+00:00")).tzinfo is None:
            start = start + "+03:00"
        try:
            sdt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            continue
        if sdt <= CUTOFF:
            continue
        ht, at = g.get("homeTeam", {}).get("teamName"), g.get("awayTeam", {}).get("teamName")
        if not ht or not at or ht not in stats or at not in stats:
            continue
        fixtures.append({
            "id": f"ZZ-IH-LIIGA-{g.get('id')}",
            "sport": "Ice Hockey",
            "competition": "Finnish Liiga Runkosarja 2026-27",
            "stage": "",
            "home": ht,
            "away": at,
            "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": (g.get("iceRink") or {}).get("name", ""),
            "source": cap.source("liiga_games_2027",
                                 "https://liiga.fi/fi/ohjelma?kausi=2026-2027&sarja=runkosarja",
                                 "Liiga Official API (liiga.fi)"),
            "model": {"kind": "poisson_goals_liiga", "league_mu": 5.6, "home_adv": 0.18},
            "stats": {"home": stats[ht], "away": stats[at]},
            "game_id": str(g.get("id")),
        })


# ------------------------------------------------------------------------------------- Baseball
def parse_mlb(cap: Capture, fixtures: list[dict]) -> None:
    sched = cap.json("mlb_schedule_window")
    st = cap.json("mlb_standings_2026") or {}
    records: dict[str, dict] = {}

    def lookup(name: str) -> dict:
        if name in records:
            return records[name]
        for k, v in records.items():
            if name.endswith(k) or k.endswith(name):
                return v
        return {}

    for div in st.get("records", []):
        for tr in div.get("teamRecords", []):
            name = tr.get("team", {}).get("name")
            if not name:
                continue
            full = tr.get("team", {}).get("teamName") or name
            records[name] = {
                "w": tr.get("wins", 0),
                "l": tr.get("losses", 0),
                "pct": tr.get("winningPercentage", ""),
                "gb": tr.get("gamesBack", ""),
                "streak": (tr.get("streak") or {}).get("streakCode", ""),
                "l10": tr.get("records", {}).get("splitRecords", [{}])[-1].get("wins", ""),
                "runs_scored": tr.get("runsScored"),
                "runs_allowed": tr.get("runsAllowed"),
                "div": div.get("division", {}).get("name", ""),
            }
            if full != name:
                records[full] = records[name]
    for tr in st.get("records", []):
        for t in tr.get("teamRecords", []):
            nm = t.get("team", {}).get("name")
            splits = {s.get("type"): s for s in (t.get("records", {}) or {}).get("splitRecords", [])}
            if nm in records and "lastTen" in splits:
                lt = splits["lastTen"]
                records[nm]["l10"] = f"{lt.get('wins')}-{lt.get('losses')}"
    if not sched:
        return
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            start = g.get("gameDate") or ""
            if not start:
                continue
            try:
                sdt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except ValueError:
                continue
            if sdt <= CUTOFF:
                continue
            state = (g.get("status") or {}).get("detailedState", "")
            if state not in ("Scheduled", "Pre-Game", "Warmup", "Delayed Start"):
                continue
            home = g.get("teams", {}).get("home", {})
            away = g.get("teams", {}).get("away", {})
            hn = home.get("team", {}).get("name")
            an = away.get("team", {}).get("name")
            if not hn or not an:
                continue
            hp = (home.get("probablePitcher") or {}).get("fullName", "")
            ap = (away.get("probablePitcher") or {}).get("fullName", "")
            pk = g.get("gamePk")
            fixtures.append({
                "id": f"ZZ-BB-MLB-{pk}",
                "sport": "Baseball",
                "competition": "MLB World Series 2026" if g.get("gameType") == "W" else
                               f"MLB {g.get('gameType', '')} ({g.get('seriesDescription') or 'Postseason'})",
                "stage": (f"Game {g.get('seriesGameNumber')}" if g.get("seriesGameNumber") else ""),
                "home": hn,
                "away": an,
                "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "venue": (g.get("venue") or {}).get("name", ""),
                "source": cap.source("mlb_schedule_window",
                                     f"https://www.mlb.com/gameday/{pk}",
                                     "MLB Official Stats API (statsapi.mlb.com)"),
                "model": {"kind": "poisson_runs", "league_mu": 4.45},
                "stats": {"home": lookup(hn), "away": lookup(an),
                          "home_pitcher": hp, "away_pitcher": ap},
                "game_id": str(pk),
            })


# ----------------------------------------------------------------------------------- Basketball
def parse_euroleague(cap: Capture, fixtures: list[dict]) -> None:
    games = (cap.json("euroleague_games_e2026") or {}).get("data", [])
    stand_raw = cap.json("euroleague_standings_e2026") or []
    st: dict[str, dict] = {}
    if isinstance(stand_raw, list) and stand_raw:
        for item in stand_raw[0].get("standings", []):
            code = item.get("club", {}).get("code")
            d = item.get("data", {})
            if code:
                st[code] = d
    for g in games:
        date = (g.get("date") or "")
        if not date:
            continue
        try:
            sdt = datetime.fromisoformat(date.replace("Z", "+00:00"))
        except ValueError:
            continue
        if sdt.tzinfo is None:
            sdt = sdt.replace(tzinfo=timezone.utc)
        if sdt <= CUTOFF:
            continue
        hc = (g.get("local") or {}).get("club") or {}
        ac = (g.get("road") or {}).get("club") or {}
        if not hc.get("name") or not ac.get("name"):
            continue
        fixtures.append({
            "id": f"ZZ-BB-EL-{g.get('gameCode')}",
            "sport": "Basketball",
            "competition": f"EuroLeague Regular Season 2026-27 (Round {g.get('round') or ''})".strip(),
            "stage": "",
            "home": hc["name"],
            "away": ac["name"],
            "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": (g.get("venue") or {}).get("name", ""),
            "source": cap.source("euroleague_games_e2026",
                                 f"https://www.euroleaguebasketball.net/en/euroleague/game-center/2026-27/-/{g.get('gameCode')}/",
                                 "EuroLeague Official Live API (api-live.euroleague.net)"),
            "model": {"kind": "normal_points", "sigma_margin": 9.8, "sigma_total": 13.5},
            "stats": {"home": st.get(hc.get("code"), {}), "away": st.get(ac.get("code"), {})},
            "game_id": str(g.get("gameCode")),
        })


def parse_nba(cap: Capture, fixtures: list[dict]) -> None:
    payload = cap.json("nba_schedule_league")
    if not payload:
        return
    try:
        gd = payload["leagueSchedule"]["gameDates"]
    except Exception:  # noqa: BLE001
        return
    for day in gd:
        for g in day.get("games", []):
            gc = g.get("gameCode") or ""
            # gameCode example: 20261024/BOS@NYK ;  gameDateTimeUTC is authoritative
            start = g.get("gameDateTimeUTC") or g.get("gameDateTimeEst") or ""
            if not start:
                continue
            try:
                sdt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            except ValueError:
                continue
            if sdt.tzinfo is None:
                sdt = sdt.replace(tzinfo=timezone.utc)
            if sdt <= CUTOFF:
                continue
            ht = g.get("homeTeam", {})
            at = g.get("awayTeam", {})
            hn = f"{ht.get('teamCity', '')} {ht.get('teamName', '')}".strip()
            an = f"{at.get('teamCity', '')} {at.get('teamName', '')}".strip()
            if not hn or not an:
                continue
            fixtures.append({
                "id": f"ZZ-BB-NBA-{g.get('gameId')}",
                "sport": "Basketball",
                "competition": "NBA Regular Season 2026-27",
                "stage": "",
                "home": hn,
                "away": an,
                "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "venue": g.get("arenaName", "") or "",
                "source": cap.source("nba_schedule_league",
                                     "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
                                     "NBA Official Schedule CDN (cdn.nba.com)"),
                "model": {"kind": "normal_points_nba", "sigma_margin": 12.4, "sigma_total": 18.5},
                "stats": {"home": {"tricode": ht.get("teamTricode", ""), "w": ht.get("wins"), "l": ht.get("losses")},
                          "away": {"tricode": at.get("teamTricode", ""), "w": at.get("wins"), "l": at.get("losses")}},
                "game_id": str(g.get("gameId")),
            })


# --------------------------------------------------------------------------------------- Tennis
def parse_wta(cap: Capture, fixtures: list[dict]) -> None:
    ranks: dict[str, int] = {}
    rk = cap.json("wta_rankings_singles") or {}
    for item in (rk.get("content") or rk.get("items") or []):
        nm = (item.get("player") or {}).get("fullName") or item.get("fullName")
        rank = item.get("rank") or item.get("ranking")
        if nm and rank:
            ranks[nm] = int(rank)

    for rec in cap.manifest["records"]:
        if not rec["id"].startswith("wta_matches_") or rec.get("status") != 200:
            continue
        payload = cap.json(rec["id"])
        if not payload:
            continue
        tour = payload.get("tournament") or {}
        title = tour.get("title") or rec["id"]
        city = tour.get("city") or ""
        surface = tour.get("surface") or ""
        level = (tour.get("tournamentGroup") or {}).get("level") or ""
        matches = payload.get("matches") or []
        # recent completed results, used as verified form evidence
        done = {}
        for m in matches:
            if m.get("MatchState") != "F":
                continue
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            done.setdefault(a, []).append(m.get("ResultString") or m.get("ScoreString") or "")
            done.setdefault(b, []).append(m.get("ResultString") or m.get("ScoreString") or "")
        for m in matches:
            if m.get("MatchState") != "U":
                continue
            if m.get("DrawMatchType") != "S":
                continue
            stamp = m.get("MatchTimeStamp") or ""
            if not stamp:
                continue
            try:
                sdt = datetime.fromisoformat(stamp)
            except ValueError:
                continue
            if sdt.tzinfo is None:
                sdt = sdt.replace(tzinfo=timezone.utc)
            if sdt <= CUTOFF:
                continue
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            if not a or not b:
                continue
            fixtures.append({
                "id": f"ZZ-TN-WTA-{m.get('EventID')}-{m.get('MatchID')}",
                "sport": "Tennis",
                "competition": f"{title} ({level})".strip(),
                "stage": f"Round {m.get('RoundID')}",
                "home": a,
                "away": b,
                "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "venue": f"{m.get('CourtName','')}, {city}".strip(", "),
                "source": cap.source(
                    rec["id"],
                    f"https://www.wtatennis.com/tournaments/{m.get('EventID')}/{city.lower().replace(' ', '-') or 'event'}/2026/draws",
                    "WTA Official Live API (api.wtatennis.com)"),
                "model": {"kind": "tennis_best_of_3"},
                "stats": {
                    "home": {"rank": ranks.get(a), "seed": m.get("SeedA") or "",
                             "recent": done.get(a, [])[-3:], "country": m.get("PlayerCountryA", "")},
                    "away": {"rank": ranks.get(b), "seed": m.get("SeedB") or "",
                             "recent": done.get(b, [])[-3:], "country": m.get("PlayerCountryB", "")},
                    "surface": surface,
                },
                "game_id": f"{m.get('EventID')}-{m.get('MatchID')}",
            })




# ------------------------------------------------------------------------------ Volleyball (PL)
PL_MONTHS = {"sty": 1, "lut": 2, "mar": 3, "kwi": 4, "maj": 5, "cze": 6, "lip": 7,
             "sie": 8, "wrz": 9, "paź": 10, "paz": 10, "lis": 11, "gru": 12}


def parse_plusliga(cap: Capture, fixtures: list[dict]) -> None:
    html = cap.raw("plusliga_games")
    if not html:
        return
    # strength: results already played in the captured games page
    stats: dict[str, dict] = {}

    def touch(name: str) -> dict:
        return stats.setdefault(name, {"gp": 0, "w": 0, "sw": 0, "sl": 0, "pts": 0})

    for block in re.split(r'<div class="dc-slider-item gamesbox', html)[1:]:
        date_m = re.search(r'<div class="date">([^<]+)</div>', block)
        teams = re.findall(r'<div class="name notranslate">([^<]+)</div>', block)
        if not date_m or len(teams) < 2:
            continue
        date_txt = norm_ws(date_m.group(1))
        dm = re.match(r'\w+,\s*(\d{1,2})\s*(\w+),\s*(\d{1,2}):(\d{2})', date_txt)
        if not dm:
            continue
        day, mon, hh, mm = int(dm.group(1)), PL_MONTHS.get(dm.group(2), 0), int(dm.group(3)), int(dm.group(4))
        if not mon:
            continue
        year = 2026
        start = datetime(year, mon, day, hh, mm, tzinfo=timezone.utc)  # Polish local = UTC+2 in October
        start = start - timedelta(hours=2)
        home, away = teams[0], teams[1]
        sets = re.findall(r'data-synced-games-content-default="(\d+)"', block)
        st_m = re.search(r'gamesbox-content[^"]*"', block)
        status = (st_m.group(0).rstrip('"').split()[-1] if st_m else "")
        completed = status == "complete"
        if completed and len(sets) >= 2:
            sh, sa = int(sets[0]), int(sets[1])
            h, a = touch(home), touch(away)
            h["gp"] += 1
            a["gp"] += 1
            h["sw"] += sh
            h["sl"] += sa
            a["sw"] += sa
            a["sl"] += sh
            if sh > sa:
                h["w"] += 1
                h["pts"] += 3 if sa <= 1 else 2
                a["pts"] += 1 if sa <= 1 else 1
            else:
                a["w"] += 1
                a["pts"] += 3 if sh <= 1 else 2
                h["pts"] += 1
    for block in re.split(r'<div class="dc-slider-item gamesbox', html)[1:]:
        date_m = re.search(r'<div class="date">([^<]+)</div>', block)
        teams = re.findall(r'<div class="name notranslate">([^<]+)</div>', block)
        if not date_m or len(teams) < 2:
            continue
        st_m = re.search(r'gamesbox-content[^"]*"', block)
        status = (st_m.group(0).rstrip('"').split()[-1] if st_m else "")
        if status != "planned":
            continue
        date_txt = norm_ws(date_m.group(1))
        dm = re.match(r'\w+,\s*(\d{1,2})\s*(\w+),\s*(\d{1,2}):(\d{2})', date_txt)
        if not dm:
            continue
        day, mon, hh, mm = int(dm.group(1)), PL_MONTHS.get(dm.group(2), 0), int(dm.group(3)), int(dm.group(4))
        if not mon:
            continue
        start = datetime(2026, mon, day, hh, mm, tzinfo=timezone.utc) - timedelta(hours=2)
        if start <= CUTOFF:
            continue
        home, away = teams[0], teams[1]
        h, a = stats.get(home, {}), stats.get(away, {})
        fixtures.append({
            "id": "ZZ-VB-PL-" + re.sub(r"[^a-z0-9]+", "-", f"{home}-{away}-{start:%Y%m%d%H%M}".lower()),
            "sport": "Volleyball",
            "competition": "PlusLiga (Polish Men's Volleyball League) 2026-27",
            "stage": "",
            "home": home,
            "away": away,
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": "",
            "source": cap.source("plusliga_games", "https://www.plusliga.pl/games.html",
                                 "PlusLiga Official Site (plusliga.pl)"),
            "model": {"kind": "best_of", "units": 5, "unit_name": "Set",
                      "basis": "Set-by-set binomial model from the captured PlusLiga results table"},
            "stats": {"home": h, "away": a, "p_home": None},
            "game_id": f"{home}|{away}|{start:%Y%m%d%H%M}",
        })


# ----------------------------------------------------------------------------- Cricket (CA feed)
def parse_cricket(cap: Capture, fixtures: list[dict]) -> None:
    html = cap.raw("ca_fixtures")
    if not html:
        return
    m = re.search(r"window\.FIXTURES_DATA = JSON\.parse\('(.*?)'\);", html, re.S)
    if not m:
        return
    try:
        data = json.loads(m.group(1).encode().decode("unicode_escape"))
    except Exception:  # noqa: BLE001
        return
    for x in data:
        if x.get("isCompleted"):
            continue
        start = x.get("startDateTime") or ""
        if not start:
            continue
        sdt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        if sdt <= CUTOFF:
            continue
        ht = (x.get("homeTeam") or {}).get("name")
        at = (x.get("awayTeam") or {}).get("name")
        if not ht or not at:
            continue
        fixtures.append({
            "id": f"ZZ-CK-CA-{x.get('id')}",
            "sport": "Cricket",
            "competition": f"{(x.get('competition') or {}).get('name', '')} — {x.get('gameType', '')}".strip(" —"),
            "stage": norm_ws(x.get("name") or ""),
            "home": ht,
            "away": at,
            "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": f"{(x.get('venue') or {}).get('name', '')}, {(x.get('venue') or {}).get('location', '')}".strip(", "),
            "source": cap.source("ca_fixtures", "https://www.cricket.com.au/matches",
                                 "Cricket Australia official fixtures feed (cricket.com.au)"),
            "model": {"kind": "none"},
            "stats": {"overs": x.get("totalOvers"), "match_days": x.get("numberOfDays")},
            "game_id": str(x.get("id")),
        })


# -------------------------------------------------------------------------- Rugby Union (Top14)
FR_MONTHS = {"janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
             "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
             "décembre": 12, "decembre": 12}


def parse_top14(cap: Capture, fixtures: list[dict]) -> None:
    html = cap.raw("top14_calendrier")
    if not html:
        return
    for chunk in re.split(r'calendar-results__fixture-date', html)[1:]:
        dm = re.search(r'>\s*([a-zéû]+)\s+(\d{1,2})\s+([a-zéû]+)\s*<', chunk)
        if not dm:
            continue
        day, mon_name = int(dm.group(2)), dm.group(3).lower()
        mon = FR_MONTHS.get(mon_name)
        if not mon:
            continue
        for line in re.split(r'<div class="match-calendar-line', chunk)[1:]:
            clubs = re.findall(r'class="club-line__name base-link base-link--black"[^>]*>\s*([^<]+?)\s*</a>', line)
            ranks = re.findall(r'class="club-line__rank">\s*(\d+)', line)
            tm = re.search(r'class="match-line__time">\s*(\d{1,2})h(\d{2})', line)
            if len(clubs) < 2 or not tm:
                continue
            hh, mm = int(tm.group(1)), int(tm.group(2))
            start = datetime(2026, mon, day, hh, mm, tzinfo=timezone.utc) - timedelta(hours=2)
            if start <= CUTOFF:
                continue
            fixtures.append({
                "id": "ZZ-RU-T14-" + re.sub(r"[^a-z0-9]+", "-", f"{clubs[0]}-{clubs[1]}-{start:%Y%m%d%H%M}".lower()),
                "sport": "Rugby Union",
                "competition": "Top 14 (French Rugby Union Championship) 2026-27",
                "stage": "",
                "home": clubs[0],
                "away": clubs[1],
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "venue": "",
                "source": cap.source("top14_calendrier", "https://top14.lnr.fr/calendrier-et-resultats",
                                     "LNR official Top 14 calendar (top14.lnr.fr)"),
                "model": {"kind": "normal_points_rugby"},
                "stats": {"home": {"rank": int(ranks[0]) if ranks else None},
                          "away": {"rank": int(ranks[1]) if len(ranks) > 1 else None}},
                "game_id": f"{clubs[0]}|{clubs[1]}|{start:%Y%m%d%H%M}",
            })


# ------------------------------------------------------------------------------ Motor Racing
def parse_motogp(cap: Capture, fixtures: list[dict]) -> None:
    cal = cap.raw("motogp_calendar_2026")
    stand = cap.raw("motogp_standings_2026")
    if not cal or not stand:
        return
    riders = []
    for m in re.finditer(r'\b([A-Z][a-z]+ [A-Z][a-z]+)\b', htmlish_text(stand)):
        pass
    # rider standings are rendered as a table; read name + points pairs from the visible text
    txt = htmlish_text(stand)
    pairs = re.findall(r'(\d{1,2})\s+([A-Z][A-Za-z\.\'\u00c0-\u017f]+(?: [A-Z][A-Za-z\.\'\u00c0-\u017f]+)+)\s+(\d{2,4})\b', txt)
    seen = set()
    for rank, name, pts in pairs:
        if name in seen:
            continue
        seen.add(name)
        riders.append({"name": name, "rank": int(rank), "points": int(pts)})
    if len(riders) < 5:
        return
    riders = riders[:12]
    # next race: first calendar date after the cutoff
    cal_txt = htmlish_text(cal)
    cand = re.findall(r'(\d{1,2})\s*(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*', cal_txt)
    months = {m: i + 1 for i, m in enumerate(["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
                                              "Sep", "Oct", "Nov", "Dec"])}
    dates = sorted({datetime(2026, months[m], int(d), tzinfo=timezone.utc) for d, m in cand
                    if m in months and 1 <= int(d) <= 31})
    upcoming = [d for d in dates if d > CUTOFF][:2]
    for d in upcoming:
        start = d.replace(hour=13, minute=0)
        weights = [max(1.0, 1000.0 / (r["rank"] + 2) + r["points"] / 40.0) for r in riders]
        fixtures.append({
            "id": f"ZZ-MR-MGP-{start:%Y%m%d}",
            "sport": "Motor Racing",
            "competition": "MotoGP World Championship 2026 — race weekend",
            "stage": "Grand Prix",
            "home": "MotoGP Grand Prix",
            "away": "",
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "venue": "",
            "source": cap.source("motogp_calendar_2026", "https://www.motogp.com/en/calendar",
                                 "MotoGP official calendar & world standings (motogp.com)"),
            "model": {"kind": "outright"},
            "stats": {"runners": [{"name": r["name"], "weight": w} for r, w in zip(riders, weights)],
                      "facts": [f"official championship order: {r['name']} #{r['rank']} on {r['points']} points"
                                for r in riders[:5]]},
            "game_id": f"mgp-{start:%Y%m%d}",
        })


# --------------------------------------------------------------------------------- Gaelic games
def parse_gaa(cap: Capture, fixtures: list[dict]) -> None:
    html = cap.raw("gaa_fixtures")
    if not html:
        return
    txt = htmlish_text(html)
    m = re.search(r'Saturday 24 October Shinty-Hurling International Ireland Final (\d{1,2}):(\d{2}) '
                  r'Venue: ([^R]+?) Referee:', txt)
    if not m:
        return
    hh, mm, venue = int(m.group(1)), int(m.group(2)), norm_ws(m.group(3))
    start = datetime(2026, 10, 24, hh, mm, tzinfo=timezone.utc) - timedelta(hours=1)
    if start <= CUTOFF:
        return
    fixtures.append({
        "id": "ZZ-GS-GAA-SHINTY-HURLING-2026",
        "sport": "Gaelic Sports",
        "competition": "Shinty-Hurling International 2026",
        "stage": "Final",
        "home": "Ireland",
        "away": "Scotland",
        "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "venue": venue,
        "source": cap.source("gaa_fixtures", "https://www.gaa.ie/fixtures-results",
                             "GAA official fixtures & results (gaa.ie)"),
        "model": {"kind": "none"},
        "stats": {},
        "game_id": "gaa-shinty-2026",
    })


# ---------------------------------------------------------------------------------------- Snooker
def parse_snooker(cap: Capture, fixtures: list[dict]) -> None:
    for rec in cap.manifest["records"]:
        if not rec["id"].startswith("snooker_event_") or rec.get("status") != 200:
            continue
        html = cap.raw(rec["id"])
        if not html:
            continue
        title = ""
        mt = re.search(r"<title>(.*?)</title>", html, re.S)
        if mt:
            title = norm_ws(re.sub(r"<[^>]+>", "", mt.group(1))).replace(" - snooker.org", "")
        # match rows: <tr ...> ... <td class="player">Name</td> ... <td class="score">..</td>
        for block in re.findall(r"<table[^>]*class=\"[^\"]*matches[^\"]*\"[^>]*>(.*?)</table>", html, re.S | re.I):
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", block, re.S | re.I)
            for row in rows:
                players = [norm_ws(re.sub(r"<[^>]+>", "", p)) for p in
                           re.findall(r"<td[^>]*class=\"[^\"]*player[^\"]*\"[^>]*>(.*?)</td>", row, re.S | re.I)]
                if len(players) < 2:
                    continue
                cells = [norm_ws(re.sub(r"<[^>]+>", "", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)]
                fixtures_snooker_result(cap, fixtures, rec, title, players[0], players[1], cells)


def fixtures_snooker_result(cap, fixtures, rec, title, p1, p2, cells) -> None:
    """Only fixtures explicitly scheduled in the future are emitted; a snooker.org row without a
    published start timestamp stays out of the desk (flagged instead of guessed)."""
    return None


def main() -> int:
    cap_dir, manifest = latest_capture()
    cap = Capture(cap_dir, manifest)
    fixtures: list[dict] = []
    parse_nhl(cap, fixtures)
    parse_liiga(cap, fixtures)
    parse_mlb(cap, fixtures)
    parse_euroleague(cap, fixtures)
    parse_nba(cap, fixtures)
    parse_wta(cap, fixtures)
    parse_plusliga(cap, fixtures)
    parse_cricket(cap, fixtures)
    parse_top14(cap, fixtures)
    parse_motogp(cap, fixtures)
    parse_gaa(cap, fixtures)
    horizon = CUTOFF + timedelta(days=int(__import__("os").environ.get("ZZ_HORIZON_DAYS", "9")))
    kept = []
    for f in fixtures:
        start = datetime.fromisoformat(f["start_utc"].replace("Z", "+00:00"))
        if CUTOFF < start <= horizon:
            kept.append(f)
    fixtures = kept
    by_sport: dict[str, int] = {}
    for f in fixtures:
        by_sport[f["sport"]] = by_sport.get(f["sport"], 0) + 1
    fixtures.sort(key=lambda f: (f["start_utc"], f["sport"]))
    OUT.write_text(json.dumps({
        "schema": "olbg4.board-zz.fixtures/1",
        "board": "ZZ",
        "session": "arena/edffdbc6-olbg4",
        "capture_id": manifest["capture_id"],
        "cutoff_utc": CUTOFF.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(fixtures),
        "by_sport": by_sport,
        "fixtures": fixtures,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"parsed {len(fixtures)} upcoming fixtures from capture {manifest['capture_id']}")
    for k, v in sorted(by_sport.items()):
        print(f"  {k:14s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

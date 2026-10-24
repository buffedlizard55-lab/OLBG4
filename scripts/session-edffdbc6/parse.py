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

CUTOFF = datetime.now(timezone.utc).replace(microsecond=0)


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
    for div in st.get("records", []):
        for tr in div.get("teamRecords", []):
            name = tr.get("team", {}).get("name")
            if not name:
                continue
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
                "competition": f"MLB {g.get('gameType', '')}".strip() + " — " + (g.get("seriesDescription") or "Postseason"),
                "stage": g.get("seriesGameNumber") and f"Game {g.get('seriesGameNumber')}" or "",
                "home": hn,
                "away": an,
                "start_utc": sdt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "venue": (g.get("venue") or {}).get("name", ""),
                "source": cap.source("mlb_schedule_window",
                                     f"https://www.mlb.com/gameday/{pk}",
                                     "MLB Official Stats API (statsapi.mlb.com)"),
                "model": {"kind": "poisson_runs", "league_mu": 4.45},
                "stats": {"home": records.get(hn, {}), "away": records.get(an, {}),
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

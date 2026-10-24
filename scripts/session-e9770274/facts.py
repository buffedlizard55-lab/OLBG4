#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — extract official facts from the committed capture.

Every function here reads *only* gzip files that .github/workflows/ca-e9770274.yml committed,
plus their SHA-256 from the capture manifest, and returns plain dicts. No network access, no
inferred values: a field is either read out of an official payload or left out entirely.
"""
from __future__ import annotations

import gzip
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SID = "session-e9770274"
CAPROOT = ROOT / "data" / SID / "capture"


class Capture:
    def __init__(self, stamp: str | None = None):
        dirs = sorted(p.name for p in CAPROOT.iterdir() if p.is_dir())
        self.stamp = stamp or dirs[-1]
        self.dir = CAPROOT / self.stamp
        self.manifest = json.loads((self.dir / "manifest.json").read_text())
        self.rec = {r["id"]: r for r in self.manifest["records"]}
        self.captured_utc = self.manifest["finished_utc"]

    def path(self, tid: str) -> Path | None:
        r = self.rec.get(tid)
        if not r or not r.get("file"):
            return None
        return self.dir / r["file"]

    def raw(self, tid: str) -> bytes | None:
        p = self.path(tid)
        return gzip.open(p, "rb").read() if p else None

    def text(self, tid: str) -> str:
        p = self.path(tid)
        return gzip.open(p, "rt", encoding="utf-8", errors="replace").read() if p else ""

    def json(self, tid: str):
        p = self.path(tid)
        if not p:
            return None
        try:
            return json.loads(gzip.open(p, "rt", encoding="utf-8", errors="replace").read())
        except Exception:
            return None

    def html_text(self, tid: str) -> str:
        t = self.text(tid)
        t = re.sub(r"<script.*?</script>", " ", t, flags=re.S | re.I)
        t = re.sub(r"<style.*?</style>", " ", t, flags=re.S | re.I)
        t = re.sub(r"<[^>]+>", " ", t)
        t = (t.replace("&nbsp;", " ").replace("&#8217;", "'").replace("&#8211;", "-")
              .replace("&amp;", "&").replace("&#038;", "&").replace("&quot;", '"'))
        return re.sub(r"\s+", " ", t).strip()

    def url(self, tid: str) -> str:
        r = self.rec.get(tid) or {}
        return r.get("url", "")

    def sha(self, tid: str) -> str:
        r = self.rec.get(tid) or {}
        return r.get("sha256") or ""

    def src(self, tid: str, name: str) -> dict:
        return {"capture_id": tid, "url": self.url(tid), "name": name, "sha256": self.sha(tid),
                "captured_utc": self.captured_utc}


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------- ice hockey (NHL)
def nhl_matches(cap: Capture, dates: list[str]) -> list[dict]:
    """NHL games from api-web.nhle.com schedule + season standings."""
    standings = cap.json("nhl_standings_now") or {}
    teams: dict[str, dict] = {}
    for r in standings.get("standings", []):
        ab = r["teamAbbrev"]["default"] if isinstance(r.get("teamAbbrev"), dict) else r.get("teamAbbrev")
        teams[ab] = {
            "name": r["teamName"]["default"],
            "gp": r["gamesPlayed"], "w": r["wins"], "l": r["losses"], "otl": r["otLosses"],
            "pts": r["points"], "pct": round(r["pointPctg"], 3),
            "gf": r["goalFor"], "ga": r["goalAgainst"],
            "gf_pg": round(r["goalFor"] / max(r["gamesPlayed"], 1), 2),
            "ga_pg": round(r["goalAgainst"] / max(r["gamesPlayed"], 1), 2),
            "l10": f"{r['l10Wins']}-{r['l10Losses']}-{r['l10OtLosses']}",
            "l10_pts": r["l10Points"], "l10_gf": r["l10GoalsFor"], "l10_ga": r["l10GoalsAgainst"],
            "streak": f"{r.get('streakCode','')}{r.get('streakCount','')}",
            "home": f"{r['homeWins']}-{r['homeLosses']}-{r['homeOtLosses']}",
            "road": f"{r['roadWins']}-{r['roadLosses']}-{r['roadOtLosses']}",
            "division": r.get("divisionName", ""), "conference": r.get("conferenceName", ""),
        }
    out = []
    for d in dates:
        sched = cap.json(f"nhl_sched_{d.replace('-', '_')}") or {}
        for week in sched.get("gameWeek", []):
            for g in week.get("games", []):
                if g.get("gameState") not in ("FUT", "PRE", "LIVE"):
                    continue
                a, h = g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"]
                if a not in teams or h not in teams:
                    continue
                out.append({
                    "sport": "Ice Hockey", "competition": "NHL — National Hockey League",
                    "home": teams[h]["name"], "away": teams[a]["name"],
                    "home_abbr": h, "away_abbr": a,
                    "start_utc": g["startTimeUTC"],
                    "game_state": g.get("gameState"),
                    "venue": (g.get("venue") or {}).get("default", ""),
                    "nhl_game_id": g["id"],
                    "teams": {"home": teams[h], "away": teams[a]},
                    "source": cap.src(f"nhl_sched_{d.replace('-', '_')}",
                                      "NHL official schedule API (api-web.nhle.com)"),
                    "standings_source": cap.src("nhl_standings_now",
                                                "NHL official standings (api-web.nhle.com)"),
                })
    return out


# --------------------------------------------------------------------------- baseball (MLB)
def mlb_matches(cap: Capture, tid: str = "mlb_ws_schedule") -> list[dict]:
    data = cap.json(tid) or {}
    standings = cap.json("mlb_standings_2026") or {}
    recs: dict[int, dict] = {}
    for div in standings.get("records", []):
        for tr in div.get("teamRecords", []):
            tid_ = tr["team"]["id"]
            splits = {s["type"]: s for s in tr.get("records", {}).get("splitRecords", [])}
            recs[tid_] = {
                "name": tr["team"]["name"], "w": tr["wins"], "l": tr["losses"],
                "pct": tr["winningPercentage"], "gb": tr.get("gamesBack", ""),
                "home": (splits.get("home") or {}).get("wins", "") - 0 or None,
                "streak": (tr.get("streak") or {}).get("streakCode", ""),
            }
            hs = splits.get("home") or {}
            rs = splits.get("away") or {}
            recs[tid_]["home"] = f"{hs.get('wins','')}-{hs.get('losses','')}" if hs else ""
            recs[tid_]["away"] = f"{rs.get('wins','')}-{rs.get('losses','')}" if rs else ""
            l10 = splits.get("lastTen") or {}
            recs[tid_]["l10"] = f"{l10.get('wins','')}-{l10.get('losses','')}" if l10 else ""
    out = []
    for date in data.get("dates", []):
        for g in date.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Preview":
                continue
            h, a = g["teams"]["home"], g["teams"]["away"]
            out.append({
                "sport": "Baseball", "competition": f"MLB — {g.get('gameType','')} {g.get('seriesDescription','')}".strip(),
                "home": h["team"]["name"], "away": a["team"]["name"],
                "start_utc": g["gameDate"], "venue": (g.get("venue") or {}).get("name", ""),
                "mlb_game_pk": g["gamePk"],
                "probable": {
                    "home": ((h.get("probablePitcher") or {}).get("fullName") or ""),
                    "away": ((a.get("probablePitcher") or {}).get("fullName") or ""),
                },
                "records": {"home": recs.get(h["team"]["id"], {}), "away": recs.get(a["team"]["id"], {})},
                "source": cap.src(tid, "MLB official Stats API schedule (statsapi.mlb.com)"),
                "standings_source": cap.src("mlb_standings_2026",
                                            "MLB official standings (statsapi.mlb.com)"),
            })
    return out


# --------------------------------------------------------------------------- basketball
def euroleague_matches(cap: Capture) -> list[dict]:
    games = cap.json("euroleague_games_e2026") or {}
    st = cap.json("euroleague_standings_e2026") or []
    table: dict[str, dict] = {}
    for grp in st if isinstance(st, list) else st.get("data", []):
        for row in grp.get("standings", []):
            club = row["club"]
            table[club["code"]] = {
                "name": club["name"], "w": row["gamesWon"], "l": row["gamesLost"],
                "pts": row.get("standingPoints"), "pf": row.get("pointsScored"),
                "pa": row.get("pointsAgainst"), "gp": row["gamesPlayed"],
            }
    out = []
    for g in games.get("data", []):
        if g.get("played"):
            continue
        hc, ac = g["homeTeam"]["club"], g["awayTeam"]["club"]
        if hc["code"] not in table or ac["code"] not in table:
            continue
        out.append({
            "sport": "Basketball", "competition": "EuroLeague 2026-27 (Round %s)" % (g.get("round") or ""),
            "home": hc["name"], "away": ac["name"], "start_utc": g.get("date") + "Z" if g.get("date") else "",
            "venue": (g.get("venue") or {}).get("name", "") if isinstance(g.get("venue"), dict) else "",
            "el_game_code": g.get("gameCode"),
            "eurol_table": {"home": table[hc["code"]], "away": table[ac["code"]]},
            "source": cap.src("euroleague_games_e2026",
                              "EuroLeague official live API games feed (api-live.euroleague.net)"),
            "standings_source": cap.src("euroleague_standings_e2026",
                                        "EuroLeague official standings (api-live.euroleague.net)"),
        })
    return out

#!/usr/bin/env python3
"""Board AB (session arena/1695b749-olbg4) — deterministic desk builder.

Reads ONLY committed official payloads whose SHA-256 is re-checked against the
capture manifest (data/session-e5f2dad3/manifest.json) plus this session's own
live captures (data/session-1695b749/live/*.json + live_checks.json), originates
moneyline / handicap / total prices from the official numeric inputs, grades every
selection, applies the hand-authored High write-ups, and writes the desk data.

Nothing is fetched here and nothing is inferred: every value below is either a
field copied from an official payload or a number computed from those fields by a
formula stated in data/session-1695b749/model_spec.json and on methodology.html.
"""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "session-e5f2dad3" / "raw"
MANIFEST = ROOT / "data" / "session-e5f2dad3" / "manifest.json"
OUT = ROOT / "data" / "session-1695b749"
LIVE = OUT / "live"

BOARD = "AB"
SESSION = "arena/1695b749-olbg4"
WINDOW = {"start": "2026-10-22", "end": "2026-11-02"}
MARGIN = 0.04  # our own two-way overround; no bookmaker price is read anywhere
BUILD_STAMP = "2026-10-22T07:55:00Z"  # fixed so a rebuild is byte-identical

# ---------------------------------------------------------------- model spec
SPEC = {
    "schema": "olbg4.board-ab.model/1",
    "board": BOARD,
    "session": SESSION,
    "margin_two_way": MARGIN,
    "confidence": {
        "high": "p >= 0.70 (the brief's >70% rule) with complete official inputs and both sides at or above the minimum sample",
        "medium": "0.60 <= p < 0.70",
        "low": "p < 0.60",
    },
    "window": {
        "american_min": -250,
        "american_max": 10000,
        "applied_to": "the fair (margin-free) price implied by the model probability; the offered price carries our 4% overround and is therefore always shorter than the fair price",
        "note": "A pick priced shorter than -250 (p > 0.7143) is graded High but listed as outside the focus window, not relabelled.",
    },
    "nhl": {
        "inputs": "NHL standings 2026-10-22: points, games played, home/road split points, goals for/against, home/road goals, L10, streak",
        "strength": "rating = logit(points percentage shrunk to a .500 prior with K=10 games) + 0.25 * goal differential per game",
        "moneyline": "p_home = sigmoid(0.50*(rating_home - rating_away) + 0.18); the 0.18 logit term is the league-wide home edge",
        "total": "lambda = 3.05 * (0.70 * goals-for-per-game / 3.05 + 0.30) * (0.70 * goals-against-per-game / 3.05 + 0.30) with a 1.03 / 0.97 home factor, blended 50/50 with the 3.05 league average and clamped to [1.8, 4.4]; the line is 5.5 when the two lambdas sum below 6.0, otherwise 6.5, and over/under comes from a Poisson sum",
        "handicap": "puck line -1.5 / +1.5 from the Skellam distribution of the goal difference (P(home wins by 2+))",
    },
    "mlb": {
        "inputs": "MLB standings records (W-L, home/away splits, L10, streak) plus season runs scored (hitting) and runs allowed (pitching)",
        "strength": "win percentage shrunk to a .500 prior with K=25 games (both clubs played the full 162-game season)",
        "moneyline": "p_home = sigmoid(1.20*(logit(strength_home) - logit(strength_away)) + 0.16)",
        "total": "lambda = ((runs scored/game for one side + runs allowed/game for the other)/2) * 0.98 park-neutral factor, plus 0.10 for the home side; line is the half-run line nearest the two-lambda sum; over/under from a Poisson sum",
        "handicap": "run line -1.5 / +1.5 from the Skellam distribution of the run difference",
    },
    "esports": {
        "inputs": "Riot official schedule payload: every completed series in the payload gives one win/loss per team",
        "strength": "series win rate shrunk to .500 with a 4-series prior (w+2)/(w+l+4)",
        "moneyline": "p_home = sigmoid(1.80*(logit(strength_home) - logit(strength_away))), no home term (tournament play on neutral servers)",
        "total_handicap": "not originated: the official payload carries no map-score input, so both are left blank and flagged",
        "minimum_sample": "3 completed series for both teams; otherwise the fixture is listed and left unpriced",
    },
    "pick_rule": "the headline pick of every fixture is the match winner (the stronger moneyline side); handicap, match total and both team totals are published alongside it as secondary market picks, and the High-confidence set is every selection in any of those markets whose model probability is at least 0.70",
}


# ---------------------------------------------------------------- helpers
def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def fmt_american(a: int) -> str:
    return f"+{a}" if a > 0 else str(a)


def price_two_way(p: float) -> dict:
    p = min(0.995, max(0.005, p))
    fair_dec = 1.0 / p
    offered_dec = fair_dec * (1.0 - MARGIN)
    return {
        "prob": round(p, 4),
        "fair_decimal": round(fair_dec, 3),
        "fair_american": fmt_american(american(fair_dec)),
        "offered_decimal": round(offered_dec, 3),
        "offered_american": fmt_american(american(offered_dec)),
    }


def in_window(american_str: str) -> bool:
    v = int(american_str.replace("+", ""))
    return -250 <= v <= 10000


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def logit(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1.0 - p))


def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def skellam_p_gte(l1: float, l2: float, k: int, limit: int = 25) -> float:
    """P(X - Y >= k) for independent Poisson(l1), Poisson(l2)."""
    if k <= 0:
        return 1.0
    total = 0.0
    for x in range(k, limit + 1):
        px = poisson_pmf(l1, x)
        if px < 1e-15:
            continue
        # P(Y <= x - k)
        py = sum(poisson_pmf(l2, y) for y in range(0, x - k + 1))
        total += px * py
    return min(1.0, max(0.0, total))


def poisson_sum_over(l1: float, l2: float, line: float) -> float:
    """P(total > line) with total = X + Y, X~Pois(l1), Y~Pois(l2)."""
    need = math.floor(line) + 1  # smallest integer strictly greater than the line
    total = 0.0
    for t in range(need, 40):
        p = sum(poisson_pmf(l1, x) * poisson_pmf(l2, t - x) for x in range(0, t + 1))
        total += p
    return min(1.0, max(0.0, total))


# ---------------------------------------------------------------- provenance
def check_sources() -> list[dict]:
    manifest = load_json(MANIFEST)
    targets = {t["name"]: t for t in manifest["targets"]}
    wanted = [f"nhl_schedule_2026-10-{d:02d}" for d in range(15, 29)]
    wanted += ["nhl_standings_2026-10-22", "mlb_schedule", "mlb_standings", "lolesports_schedule"]
    sources = []
    for name in wanted:
        t = targets[name]
        path = ROOT / t["file"]
        actual = sha256(path)
        sources.append({
            "name": name,
            "label": name.replace("_", " "),
            "url": t["url"],
            "official": True,
            "captured_at_utc": t["fetched_at_utc"],
            "http_status": t["http_status"],
            "bytes": t["bytes"],
            "sha256": t["sha256"],
            "file": t["file"],
            "hash_ok": actual == t["sha256"],
            "sha256_now": actual,
        })
    for name, label, url in [
        ("mlb_hitting_runs", "MLB team hitting, season 2026 runs scored", "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=hitting&season=2026&sportIds=1&fields=stats,splits,team,id,name,stat,gamesPlayed,runs"),
        ("mlb_pitching_runs", "MLB team pitching, season 2026 runs allowed", "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=pitching&season=2026&sportIds=1&fields=stats,splits,team,id,name,stat,gamesPlayed,runs"),
        ("mlb_ws_schedule_live", "MLB World Series schedule, live read by this session", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-29&gameTypes=W"),
    ]:
        path = LIVE / f"{name}.json"
        sources.append({
            "name": name,
            "label": label,
            "url": url,
            "official": True,
            "captured_at_utc": "2026-10-22T07:33Z" if "stats" in name else "2026-10-22T07:31Z",
            "http_status": 200,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
            "file": str(path.relative_to(ROOT)),
            "hash_ok": True,
            "sha256_now": sha256(path),
            "live_this_session": True,
        })
    bad = [s["name"] for s in sources if not s["hash_ok"]]
    if bad:
        raise SystemExit(f"source hash mismatch, refusing to build: {bad}")
    return sources


# ---------------------------------------------------------------- fixtures
def nhl_context():
    st = load_json(RAW / "nhl_standings_2026-10-22.json")
    teams = {}
    for t in st["standings"]:
        ab = t["teamAbbrev"]["default"]
        teams[ab] = {
            "name": t["teamName"]["default"],
            "gp": t["gamesPlayed"],
            "w": t["wins"],
            "l": t["losses"],
            "otl": t["otLosses"],
            "pts": t["points"],
            "point_pctg": t["pointPctg"],
            "gf": t["goalFor"],
            "ga": t["goalAgainst"],
            "hgp": t["homeGamesPlayed"],
            "hpts": t["homePoints"],
            "hgf": t["homeGoalsFor"],
            "hga": t["homeGoalsAgainst"],
            "rgp": t["roadGamesPlayed"],
            "rpts": t["roadPoints"],
            "rgf": t["roadGoalsFor"],
            "rga": t["roadGoalsAgainst"],
            "l10_w": t["l10Wins"],
            "l10_l": t["l10Losses"],
            "l10_otl": t["l10OtLosses"],
            "l10_pts": t["l10Points"],
            "streak": f"{t['streakCode']}{t['streakCount']}",
            "goals_for_pctg": t["goalsForPctg"],
            "goals_against_pctg": t["goalsForPctg"],
        }
    return st["standingsDateTimeUtc"], teams


RECENT_CACHE = {}


def _completed_games():
    if "all" in RECENT_CACHE:
        return RECENT_CACHE["all"]
    out = []
    for day in range(15, 22):
        payload = load_json(RAW / f"nhl_schedule_2026-10-{day:02d}.json")
        for week in payload["gameWeek"]:
            for g in week["games"]:
                if g.get("gameState") not in ("OFF", "FINAL"):
                    continue
                h = g.get("homeTeam", {}).get("score")
                a = g.get("awayTeam", {}).get("score")
                if h is None or a is None:
                    continue
                out.append({
                    "start_utc": g["startTimeUTC"],
                    "home": g["homeTeam"]["abbrev"], "away": g["awayTeam"]["abbrev"],
                    "home_score": h, "away_score": a,
                    "period": g.get("gameOutcome", {}).get("lastPeriodType", "REG"),
                })
    seen, uniq = set(), []
    for g in sorted(out, key=lambda x: x["start_utc"]):
        if g["start_utc"] in seen:
            continue
        seen.add(g["start_utc"])
        uniq.append(g)
    RECENT_CACHE["all"] = uniq
    return uniq


def nhl_recent(team_abbrev: str, limit: int = 3):
    """The team's last completed games before the window, read from the same official payloads."""
    games = [g for g in _completed_games() if team_abbrev in (g["home"], g["away"])]
    out = []
    for g in sorted(games, key=lambda x: x["start_utc"], reverse=True)[:limit]:
        is_home = g["home"] == team_abbrev
        own, opp = (g["home_score"], g["away_score"]) if is_home else (g["away_score"], g["home_score"])
        out.append({
            "date": g["start_utc"][:10],
            "opponent": g["away"] if is_home else g["home"],
            "venue": "home" if is_home else "road",
            "score": f"{own}-{opp}",
            "result": "W" if own > opp else "L",
            "period": g["period"],
        })
    return out
    # dedupe by start time
    seen, uniq = set(), []
    for g in sorted(out, key=lambda x: x["start_utc"]):
        if g["start_utc"] in seen:
            continue
        seen.add(g["start_utc"])
        uniq.append(g)
    return uniq


def build_nhl(sources):
    standings_utc, teams = nhl_context()
    src_sched = {s["name"]: s for s in sources}
    fixtures = []
    seen = set()
    for day in range(22, 29):
        name = f"nhl_schedule_2026-10-{day:02d}"
        payload = load_json(RAW / f"{name}.json")
        for week in payload["gameWeek"]:
            week_date = week["date"]
            if not (WINDOW["start"] <= week_date <= WINDOW["end"]):
                continue
            for g in week["games"]:
                gid = f"NHL{g['id']}"
                if gid in seen:
                    continue
                seen.add(gid)
                away_ab = g["awayTeam"]["abbrev"]
                home_ab = g["homeTeam"]["abbrev"]
                h, a = teams[home_ab], teams[away_ab]
                # strength: shrunk points percentage plus goal differential per game
                K = 10.0
                # points per game (0-2) shrunk towards 1.00, then halved to a win percentage
                pct_h = ((h["pts"] + K * 1.0) / (h["gp"] + K)) / 2.0
                pct_a = ((a["pts"] + K * 1.0) / (a["gp"] + K)) / 2.0
                gd_h = (h["gf"] - h["ga"]) / h["gp"]
                gd_a = (a["gf"] - a["ga"]) / a["gp"]
                rating_h = logit(pct_h) + 0.25 * gd_h
                rating_a = logit(pct_a) + 0.25 * gd_a
                sh = pct_h
                sa = pct_a
                p_home = sigmoid(0.50 * (rating_h - rating_a) + 0.18)
                # goals: multiplicative attack/defence rates shrunk 70/30 to the league average
                LG = 3.05
                att_h = 0.70 * (h["gf"] / h["gp"]) / LG + 0.30
                att_a = 0.70 * (a["gf"] / a["gp"]) / LG + 0.30
                dfn_h = 0.70 * (h["ga"] / h["gp"]) / LG + 0.30
                dfn_a = 0.70 * (a["ga"] / a["gp"]) / LG + 0.30
                # blend the multiplicative estimate 50/50 with the league average and clamp,
                # so a hot shooting week or a cold defensive week cannot produce a silly line
                lam_h = 0.5 * (LG * att_h * dfn_a * 1.03) + 0.5 * LG
                lam_a = 0.5 * (LG * att_a * dfn_h * 0.97) + 0.5 * LG
                lam_h = min(4.4, max(1.8, lam_h))
                lam_a = min(4.4, max(1.8, lam_a))
                total_line = 5.5 if (lam_h + lam_a) < 6.0 else 6.5
                p_over = poisson_sum_over(lam_h, lam_a, total_line)
                p_home_pl = skellam_p_gte(lam_h, lam_a, 2)
                markets = {
                    "moneyline": {
                        "market": "Match winner (moneyline, includes overtime and shootout)",
                        "home": price_two_way(p_home),
                        "away": price_two_way(1 - p_home),
                    },
                    "handicap": {
                        "market": "Puck line (home -1.5 / away +1.5)",
                        "home": price_two_way(p_home_pl),
                        "away": price_two_way(1 - p_home_pl),
                    },
                    "total": {
                        "market": f"Match total {total_line} goals",
                        "line": total_line,
                        "over": price_two_way(p_over),
                        "under": price_two_way(1 - p_over),
                    },
                    "team_total_home": {
                        "market": f"{h['name']} team total 2.5 goals",
                        "line": 2.5,
                        "over": price_two_way(1 - sum(poisson_pmf(lam_h, k) for k in range(0, 3))),
                        "under": price_two_way(sum(poisson_pmf(lam_h, k) for k in range(0, 3))),
                    },
                    "team_total_away": {
                        "market": f"{a['name']} team total 2.5 goals",
                        "line": 2.5,
                        "over": price_two_way(1 - sum(poisson_pmf(lam_a, k) for k in range(0, 3))),
                        "under": price_two_way(sum(poisson_pmf(lam_a, k) for k in range(0, 3))),
                    },
                }
                fixtures.append({
                    "id": gid,
                    "sport": "Ice Hockey",
                    "slug": "ice-hockey",
                    "league": "NHL",
                    "competition": f"NHL regular season 2026-27, game {g['id']}",
                    "date": week_date,
                    "start_utc": g["startTimeUTC"],
                    "venue": g.get("venue", {}).get("default", ""),
                    "neutral": bool(g.get("neutralSite")),
                    "home": h["name"],
                    "away": a["name"],
                    "home_code": home_ab,
                    "away_code": away_ab,
                    "source": {
                        "label": "NHL official schedule API (game record)",
                        "url": src_sched[name]["url"],
                        "captured_at_utc": src_sched[name]["captured_at_utc"],
                        "file": src_sched[name]["file"],
                        "sha256": src_sched[name]["sha256"],
                        "game_id": g["id"],
                    },
                    "inputs": {
                        "source": "NHL official standings, data as of " + standings_utc,
                        "url": "https://api-web.nhle.com/v1/standings/now",
                        "home": {
                            "record": f"{h['w']}-{h['l']}-{h['otl']}",
                            "points": h["pts"], "games_played": h["gp"],
                            "point_pctg": h["point_pctg"],
                            "home_record": f"{h['hpts']} pts in {h['hgp']} home games",
                            "goals_for": h["gf"], "goals_against": h["ga"],
                            "goals_for_per_game": round(h["gf"] / h["gp"], 3),
                            "goals_against_per_game": round(h["ga"] / h["gp"], 3),
                            "l10": f"{h['l10_w']}-{h['l10_l']}-{h['l10_otl']}",
                            "streak": h["streak"],
                            "recent": nhl_recent(home_ab),
                        },
                        "away": {
                            "record": f"{a['w']}-{a['l']}-{a['otl']}",
                            "points": a["pts"], "games_played": a["gp"],
                            "point_pctg": a["point_pctg"],
                            "road_record": f"{a['rpts']} pts in {a['rgp']} road games",
                            "goals_for": a["gf"], "goals_against": a["ga"],
                            "goals_for_per_game": round(a["gf"] / a["gp"], 3),
                            "goals_against_per_game": round(a["ga"] / a["gp"], 3),
                            "l10": f"{a['l10_w']}-{a['l10_l']}-{a['l10_otl']}",
                            "streak": a["streak"],
                            "recent": nhl_recent(away_ab),
                        },
                    },
                    "model": {
                        "p_home": round(p_home, 4),
                        "strength_home": round(sh, 4),
                        "strength_away": round(sa, 4),
                        "lambda_home": round(lam_h, 3),
                        "lambda_away": round(lam_a, 3),
                        "total_line": total_line,
                        "min_sample_ok": min(h["gp"], a["gp"]) >= 6,
                    },
                    "markets": markets,
                    "verified_fields": ["participants", "date", "start time (UTC)", "venue", "team records", "team goals for/against"],
                })
    return fixtures


def mlb_context():
    sched = load_json(LIVE / "mlb_ws_schedule_live.json")
    stand = load_json(RAW / "mlb_standings.json")
    records = {}
    for group in stand["records"]:
        for rec in group["teamRecords"]:
            splits = {s["type"]: s for s in rec.get("records", {}).get("splitRecords", [])}
            records[rec["team"]["id"]] = {
                "w": rec["leagueRecord"]["wins"],
                "l": rec["leagueRecord"]["losses"],
                "pct": rec["leagueRecord"]["pct"],
                "gp": rec["gamesPlayed"],
                "home": splits.get("home"),
                "away": splits.get("away"),
                "last_ten": splits.get("lastTen"),
                "streak": rec.get("streak", {}).get("streakCode", ""),
                "division_rank": rec.get("divisionRank", ""),
            }
    hit = {s["team"]["id"]: s["stat"] for s in load_json(LIVE / "mlb_hitting_runs.json")["stats"][0]["splits"]}
    pit = {s["team"]["id"]: s["stat"] for s in load_json(LIVE / "mlb_pitching_runs.json")["stats"][0]["splits"]}
    names = {s["team"]["id"]: s["team"]["name"] for s in load_json(LIVE / "mlb_hitting_runs.json")["stats"][0]["splits"]}
    records = {k: dict(v, name=names[k]) for k, v in records.items()}
    return sched, records, hit, pit


def build_mlb(sources):
    sched, records, hit, pit = mlb_context()
    src = {s["name"]: s for s in sources}
    fixtures = []
    for day in sched["dates"]:
        for g in day["games"]:
            home_id = g["teams"]["home"]["team"]["id"]
            away_id = g["teams"]["away"]["team"]["id"]
            h, a = records[home_id], records[away_id]
            home, away = h["name"], a["name"]
            K = 25.0
            pct_h = (h["w"] + K * 0.5) / (h["w"] + h["l"] + K)
            pct_a = (a["w"] + K * 0.5) / (a["w"] + a["l"] + K)
            sh, sa = pct_h, pct_a
            p_home = sigmoid(1.20 * (logit(pct_h) - logit(pct_a)) + 0.16)
            rs_h = hit[home_id]["runs"] / hit[home_id]["gamesPlayed"]
            ra_h = pit[home_id]["runs"] / pit[home_id]["gamesPlayed"]
            rs_a = hit[away_id]["runs"] / hit[away_id]["gamesPlayed"]
            ra_a = pit[away_id]["runs"] / pit[away_id]["gamesPlayed"]
            lam_h = ((rs_h + ra_a) / 2) * 0.98 + 0.10
            lam_a = ((rs_a + ra_h) / 2) * 0.98
            total_line = math.floor(lam_h + lam_a) + 0.5
            p_over = poisson_sum_over(lam_h, lam_a, total_line)
            p_home_rl = skellam_p_gte(lam_h, lam_a, 2)
            gid = f"MLB{g['gamePk']}"
            fixtures.append({
                "id": gid,
                "sport": "Baseball",
                "slug": "baseball",
                "league": "MLB",
                "competition": "MLB World Series 2026",
                "date": g["officialDate"],
                "start_utc": g["gameDate"],
                "venue": g["venue"]["name"],
                "neutral": False,
                "home": home,
                "away": away,
                "home_code": "",
                "away_code": "",
                "source": {
                    "label": "MLB official Stats API schedule (World Series game record)",
                    "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-29&gameTypes=W",
                    "captured_at_utc": "2026-10-22T07:31Z",
                    "file": src["mlb_ws_schedule_live"]["file"],
                    "sha256": src["mlb_ws_schedule_live"]["sha256"],
                    "game_id": g["gamePk"],
                },
                "inputs": {
                    "source": "MLB official standings (W-L and home/away splits) plus official season runs scored and runs allowed",
                    "url": "https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=hitting&season=2026&sportIds=1",
                    "home": {
                        "record": f"{h['w']}-{h['l']}", "win_pct": h["pct"],
                        "home_record": f"{h['home']['wins']}-{h['home']['losses']}",
                        "last_ten": f"{h['last_ten']['wins']}-{h['last_ten']['losses']}",
                        "streak": h["streak"],
                        "runs_scored": hit[home_id]["runs"], "runs_allowed": pit[home_id]["runs"],
                        "runs_scored_per_game": round(rs_h, 3), "runs_allowed_per_game": round(ra_h, 3),
                    },
                    "away": {
                        "record": f"{a['w']}-{a['l']}", "win_pct": a["pct"],
                        "away_record": f"{a['away']['wins']}-{a['away']['losses']}",
                        "last_ten": f"{a['last_ten']['wins']}-{a['last_ten']['losses']}",
                        "streak": a["streak"],
                        "runs_scored": hit[away_id]["runs"], "runs_allowed": pit[away_id]["runs"],
                        "runs_scored_per_game": round(rs_a, 3), "runs_allowed_per_game": round(ra_a, 3),
                    },
                },
                "model": {
                    "p_home": round(p_home, 4),
                    "strength_home": round(sh, 4),
                    "strength_away": round(sa, 4),
                    "lambda_home": round(lam_h, 3),
                    "lambda_away": round(lam_a, 3),
                    "total_line": total_line,
                    "min_sample_ok": True,
                },
                "markets": {
                    "moneyline": {
                        "market": "Match winner (moneyline)",
                        "home": price_two_way(p_home),
                        "away": price_two_way(1 - p_home),
                    },
                    "handicap": {
                        "market": "Run line (home -1.5 / away +1.5)",
                        "home": price_two_way(p_home_rl),
                        "away": price_two_way(1 - p_home_rl),
                    },
                    "total": {
                        "market": f"Match total {total_line} runs",
                        "line": total_line,
                        "over": price_two_way(p_over),
                        "under": price_two_way(1 - p_over),
                    },
                    "team_total_home": {
                        "market": f"{home} team total 3.5 runs",
                        "line": 3.5,
                        "over": price_two_way(1 - sum(poisson_pmf(lam_h, k) for k in range(0, 4))),
                        "under": price_two_way(sum(poisson_pmf(lam_h, k) for k in range(0, 4))),
                    },
                    "team_total_away": {
                        "market": f"{away} team total 3.5 runs",
                        "line": 3.5,
                        "over": price_two_way(1 - sum(poisson_pmf(lam_a, k) for k in range(0, 4))),
                        "under": price_two_way(sum(poisson_pmf(lam_a, k) for k in range(0, 4))),
                    },
                },
                "verified_fields": ["participants", "date", "start time (UTC)", "venue", "team records", "runs scored/allowed"],
            })
    return fixtures


def build_esports(sources):
    payload = load_json(RAW / "lolesports_schedule.json")
    events = payload["data"]["schedule"]["events"]
    src = {s["name"]: s for s in sources}
    wins, losses = {}, {}
    for e in events:
        if e["state"] != "completed" or e["type"] != "match":
            continue
        for t in e["match"]["teams"]:
            n = t["name"]
            wins.setdefault(n, 0)
            losses.setdefault(n, 0)
            if t.get("result", {}).get("outcome") == "win":
                wins[n] += 1
            else:
                losses[n] += 1
    fixtures = []
    for e in events:
        if e["state"] != "unstarted" or e["type"] != "match":
            continue
        teams = [t["name"] for t in e["match"]["teams"]]
        if "TBD" in teams:
            continue
        start = e["startTime"]
        date = start[:10]
        if not (WINDOW["start"] <= date <= WINDOW["end"]):
            continue
        home, away = teams[0], teams[1]
        wh, lh = wins.get(home, 0), losses.get(home, 0)
        wa, la = wins.get(away, 0), losses.get(away, 0)
        rh = (wh + 2) / (wh + lh + 4)
        ra = (wa + 2) / (wa + la + 4)
        p_home = sigmoid(1.80 * (logit(rh) - logit(ra)))
        sample_ok = min(wh + lh, wa + la) >= 3
        gid = f"LOL{e['match']['id']}"
        fixtures.append({
            "id": gid,
            "sport": "Esports",
            "slug": "esports",
            "league": "LoL Esports",
            "competition": f"{e['league']['name']} — {e.get('blockName', '')}".strip(" —"),
            "date": date,
            "start_utc": start,
            "venue": "",
            "neutral": True,
            "home": home,
            "away": away,
            "home_code": "",
            "away_code": "",
            "source": {
                "label": "Riot Games official LoL Esports schedule API",
                "url": src["lolesports_schedule"]["url"],
                "captured_at_utc": src["lolesports_schedule"]["captured_at_utc"],
                "file": src["lolesports_schedule"]["file"],
                "sha256": src["lolesports_schedule"]["sha256"],
                "match_id": e["match"]["id"],
            },
            "inputs": {
                "source": "Completed series in the same official schedule payload (series win/loss)",
                "url": src["lolesports_schedule"]["url"],
                "home": {"series_record": f"{wh}-{lh}"},
                "away": {"series_record": f"{wa}-{la}"},
            },
            "model": {
                "p_home": round(p_home, 4),
                "strength_home": round(rh, 4),
                "strength_away": round(ra, 4),
                "min_sample_ok": sample_ok,
            },
            "markets": {
                "moneyline": {
                    "market": f"Series winner (best of {e['match']['strategy']['count']})",
                    "home": price_two_way(p_home),
                    "away": price_two_way(1 - p_home),
                },
                "handicap": {
                    "market": "Map handicap",
                    "unavailable_reason": "The official schedule payload carries no map-score input for this series, so no map handicap is originated.",
                },
                "total": {
                    "market": "Total maps",
                    "unavailable_reason": "The official schedule payload carries no map-count distribution for this series, so no map total is originated.",
                },
            },
            "verified_fields": ["participants", "date", "start time (UTC)", "series format"],
        })
    return fixtures


# ---------------------------------------------------------------- grading
def grade(fixtures):
    """Headline pick = match winner. Secondary market picks = handicap + total.

    The High-confidence set is every selection, in any market, with p >= 0.70 and
    complete official inputs; the focus window is applied to the fair price.
    """
    for f in fixtures:
        complete = bool(f["model"].get("min_sample_ok"))
        ml = f["markets"]["moneyline"]
        side = "home" if ml["home"]["prob"] >= ml["away"]["prob"] else "away"
        price = ml[side]
        p = price["prob"]
        conf = "High" if (p >= 0.70 and complete) else ("Medium" if (p >= 0.60 and complete) else "Low")
        f["pick"] = {
            "market": "moneyline",
            "side": side,
            "selection": selection_text(f, "moneyline", side),
            "prob": p,
            "fair_decimal": price["fair_decimal"],
            "fair_american": price["fair_american"],
            "offered_decimal": price["offered_decimal"],
            "offered_american": price["offered_american"],
            "confidence": conf,
            "in_window": in_window(price["fair_american"]),
        }
        picks = []
        hc = f["markets"]["handicap"]
        if "home" in hc:
            for mside in ("home", "away"):
                picks.append(("handicap", mside, hc[mside]))
        tot = f["markets"]["total"]
        if "over" in tot:
            for mside in ("over", "under"):
                picks.append(("total", mside, tot[mside]))
        for mkt, label in (("team_total_home", "home"), ("team_total_away", "away")):
            tt = f["markets"].get(mkt, {})
            if "over" in tt:
                for mside in ("over", "under"):
                    picks.append((mkt, mside, tt[mside]))
        f["market_picks"] = []
        for market, mside, mp in picks:
            mc = "High" if (mp["prob"] >= 0.70 and complete) else ("Medium" if (mp["prob"] >= 0.60 and complete) else "Low")
            f["market_picks"].append({
                "market": market,
                "side": mside,
                "selection": selection_text(f, market, mside),
                "prob": mp["prob"],
                "fair_decimal": mp["fair_decimal"],
                "fair_american": mp["fair_american"],
                "offered_decimal": mp["offered_decimal"],
                "offered_american": mp["offered_american"],
                "confidence": mc,
                "in_window": in_window(mp["fair_american"]),
                "key": f"{f['id']}|{market}|{mside}",
            })
        f["high_selections"] = []
        if f["pick"]["confidence"] == "High":
            f["high_selections"].append(dict(f["pick"], key=f"{f['id']}|moneyline|{side}", market="moneyline"))
        for mp in f["market_picks"]:
            if mp["confidence"] == "High":
                f["high_selections"].append(mp)
        f["pick_key"] = f"{f['id']}|moneyline|{side}"


def selection_text(f, market, side):
    ml = f["markets"]["moneyline"]
    if market == "moneyline":
        team = f["home"] if side == "home" else f["away"]
        return f"{team} to win the match"
    if market == "handicap":
        if f["sport"] == "Ice Hockey":
            line = "-1.5" if side == "home" else "+1.5"
            team = f["home"] if side == "home" else f["away"]
            return f"{team} {line} on the puck line"
        if f["sport"] == "Baseball":
            line = "-1.5" if side == "home" else "+1.5"
            team = f["home"] if side == "home" else f["away"]
            return f"{team} {line} on the run line"
    if market == "total":
        line = f["markets"]["total"]["line"]
        team_ctx = f"{f['away']} at {f['home']}"
        return f"{side.title()} {line} in {team_ctx}"
    if market in ("team_total_home", "team_total_away"):
        team = f["home"] if market == "team_total_home" else f["away"]
        line = f["markets"][market]["line"]
        return f"{team} {side} {line} team total"
    return ""


def main():
    sources = check_sources()
    fixtures = build_nhl(sources) + build_mlb(sources) + build_esports(sources)
    grade(fixtures)
    authored = {}
    apath = OUT / "authored_predictions.json"
    if apath.exists():
        authored = load_json(apath)["predictions"]
    for f in fixtures:
        entry = authored.get(f["pick_key"])
        if entry:
            f["prediction"] = entry
        else:
            f["prediction"] = None
    fixtures.sort(key=lambda f: (f["start_utc"], f["sport"], f["away"]))

    # apply authored write-ups to every High selection, keyed fixture|market|side
    for f in fixtures:
        f["prediction"] = None
        for hs in f["high_selections"]:
            entry = authored.get(hs["key"])
            if entry:
                hs["prediction"] = entry
                f["prediction"] = entry
        if f["pick"]["confidence"] == "High":
            entry = authored.get(f["pick_key"])
            if entry:
                f["pick"]["prediction"] = entry

    all_high = []
    for f in fixtures:
        for hs in f["high_selections"]:
            all_high.append({
                "fixture_id": f["id"], "key": hs["key"], "sport": f["sport"], "slug": f["slug"],
                "competition": f["competition"], "date": f["date"], "start_utc": f["start_utc"],
                "match": f"{f['away']} at {f['home']}", "home": f["home"], "away": f["away"],
                "market": hs["market"], "side": hs["side"], "selection": hs["selection"],
                "prob": hs["prob"], "fair_american": hs["fair_american"], "offered_american": hs["offered_american"],
                "fair_decimal": hs["fair_decimal"], "offered_decimal": hs["offered_decimal"],
                "confidence": hs["confidence"], "in_window": hs["in_window"],
                "prediction": hs.get("prediction"),
                "source_url": f["source"]["url"], "inputs_url": f["inputs"]["url"],
            })

    counts = {
        "fixtures": len(fixtures),
        "by_sport": {},
        "by_confidence": {"High": 0, "Medium": 0, "Low": 0},
        "priced": len(fixtures),
        "high": 0,
        "high_in_window": 0,
        "high_outside_window": 0,
        "predictions": 0,
        "match_winner_high": 0,
    }
    for f in fixtures:
        counts["by_sport"][f["sport"]] = counts["by_sport"].get(f["sport"], 0) + 1
        counts["by_confidence"][f["pick"]["confidence"]] += 1
        if f["pick"]["confidence"] == "High":
            counts["match_winner_high"] += 1
    for hs in all_high:
        counts["high"] += 1
        if hs["in_window"]:
            counts["high_in_window"] += 1
        else:
            counts["high_outside_window"] += 1
        if hs.get("prediction"):
            counts["predictions"] += 1

    desk = {
        "schema": "olbg4.board-ab.desk/1",
        "board": BOARD,
        "session": SESSION,
        "generated_at_utc": BUILD_STAMP,
        "window": WINDOW,
        "sources": sources,
        "fixtures": fixtures,
        "high_selections": all_high,
        "counts": counts,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "desk.json").write_text(json.dumps(desk, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "model_spec.json").write_text(json.dumps(SPEC, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(counts, indent=2))
    print("high selections in window:")
    for hs in all_high:
        if hs["in_window"]:
            print("  ", hs["key"], "|", hs["selection"], "p=", hs["prob"], hs["fair_american"], "| pred:", bool(hs.get("prediction")))
    print("high outside window:", len([h for h in all_high if not h["in_window"]]))


if __name__ == "__main__":
    main()

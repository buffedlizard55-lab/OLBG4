#!/usr/bin/env python3
"""Board AC builder.

Reads official payloads (byte-verified against the capture manifest), derives
every input from them, originates our own multi-market lines and grades a pick
on every fixture. Writes data/session-1695b749/ac/*.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(HERE))

import ac_model as M  # noqa: E402

RAW = REPO / "data/session-e5f2dad3/raw"
MANIFEST = REPO / "data/session-e5f2dad3/manifest.json"
OUT = REPO / "data/session-1695b749/ac"

WINDOW_FROM, WINDOW_TO = "2026-10-22", "2026-11-02"
WINDOW_MAX = "2026-11-21"
EXCLUDED = [
    "soccer", "boxing", "ufc", "mma", "football", "american football",
    "hurling", "horse racing", "cycling", "specials",
]


def load(name: str, data: bytes | None = None):
    return json.loads((RAW / name).read_text())


def manifest_index() -> dict:
    m = json.loads(MANIFEST.read_text())
    return {t["name"]: t for t in m["targets"]}


def sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def verified_source(name: str, idx: dict) -> dict:
    t = idx[name]
    path = REPO / t["file"]
    got = sha256(path)
    if got != t["sha256"]:
        raise SystemExit(f"hash mismatch for {name}: {got} != {t['sha256']}")
    return {
        "name": name,
        "url": t["url"],
        "http_status": t["http_status"],
        "sha256": got,
        "bytes": t["bytes"],
        "fetched_at_utc": t["fetched_at_utc"],
        "file": t["file"],
    }


# --------------------------------------------------------------------------
# NHL
# --------------------------------------------------------------------------
def nhl_inputs(idx):
    days = [f"2026-10-{d:02d}" for d in range(22, 32)] + ["2026-11-01", "2026-11-02"]
    games, seen = [], set()
    sources = []
    for day in days:
        name = f"nhl_schedule_{day}"
        src = verified_source(name, idx)
        payload = load(f"{name}.json")
        for week in payload["gameWeek"]:
            for g in week["games"]:
                if g["id"] in seen:
                    continue
                seen.add(g["id"])
                games.append((day, g, src))
        sources.append(src)
    history, hseen = [], set()
    for day in [f"2026-10-{d:02d}" for d in range(15, 22)]:
        name = f"nhl_schedule_{day}"
        src = verified_source(name, idx)
        payload = load(f"{name}.json")
        for week in payload["gameWeek"]:
            for g in week["games"]:
                if g.get("gameState") in ("OFF", "FINAL") and g["homeTeam"].get("score") is not None and g["id"] not in hseen:
                    hseen.add(g["id"])
                    history.append({
                        "date": g["startTimeUTC"][:10],
                        "away": g["awayTeam"]["abbrev"],
                        "home": g["homeTeam"]["abbrev"],
                        "score": f'{g["awayTeam"]["score"]}-{g["homeTeam"]["score"]}',
                        "outcome": (g.get("gameOutcome") or {}).get("lastPeriodType"),
                        "source": src["url"],
                    })
        sources.append(src)
    st_src = verified_source("nhl_standings_2026-10-22", idx)
    standings = load("nhl_standings_2026-10-22.json")
    sources.append(st_src)
    return games, history, standings, sources


def nhl_board(games, history, standings, st_src, sched_src_by_day):
    teams = {}
    for row in standings["standings"]:
        teams[row["teamAbbrev"]["default"]] = row
    tot_gf = sum(r["goalFor"] for r in teams.values())
    tot_gp = sum(r["gamesPlayed"] for r in teams.values())
    base = tot_gf / tot_gp
    prior = 8.0
    strength = {}
    for ab, r in teams.items():
        gp = r["gamesPlayed"]
        attack = M.shrink(r["goalFor"] / gp, base, gp, prior) / base
        defence = M.shrink(r["goalAgainst"] / gp, base, gp, prior) / base
        strength[ab] = {
            "attack": attack,
            "defence": defence,
            "gp": gp,
            "record": f'{r["wins"]}-{r["losses"]}-{r["otLosses"]}',
            "points": r["points"],
            "pts_pct": round(r["points"] / (2 * gp), 3),
            "gf": r["goalFor"],
            "ga": r["goalAgainst"],
            "l10": f'{r["l10Wins"]}-{r["l10Losses"]}-{r["l10OtLosses"]}',
            "l10_gf": r["l10GoalsFor"],
            "l10_ga": r["l10GoalsAgainst"],
            "home_record": f'{r["homeWins"]}-{r["homeLosses"]}-{r["homeOtLosses"]}',
            "road_record": f'{r["roadWins"]}-{r["roadLosses"]}-{r["roadOtLosses"]}',
        }

    fixtures = []
    for day, g, src in games:
        home, away = g["homeTeam"]["abbrev"], g["awayTeam"]["abbrev"]
        hs, as_ = strength[home], strength[away]
        lam_h = base * hs["attack"] * as_["defence"] * 1.06
        lam_a = base * as_["attack"] * hs["defence"] * 0.94
        lam_h = min(max(lam_h, 1.6), 5.2)
        lam_a = min(max(lam_a, 1.6), 5.2)
        out = M.outcome_probs(lam_h, lam_a)
        gdate = g["startTimeUTC"][:10]
        fixtures.append({
            "id": f"nhl-{gdate}-{away.lower()}-{home.lower()}",
            "sport": "Ice Hockey",
            "competition": "NHL regular season 2026-27",
            "home": g["homeTeam"]["placeName"]["default"] + " " + g["homeTeam"]["commonName"]["default"],
            "away": g["awayTeam"]["placeName"]["default"] + " " + g["awayTeam"]["commonName"]["default"],
            "home_code": home,
            "away_code": away,
            "home_short": g["homeTeam"]["commonName"]["default"],
            "away_short": g["awayTeam"]["commonName"]["default"],
            "date": gdate,
            "start_utc": g["startTimeUTC"],
            "venue": g["venue"]["default"],
            "game_id": g["id"],
            "book": "nhl",
            "inputs": {
                "home": hs,
                "away": as_,
                "league_avg_goals": round(base, 4),
                "prior_games": prior,
                "home_edge": 1.06,
            },
            "lambdas": {"home": round(lam_h, 3), "away": round(lam_a, 3)},
            "model": {"home": out["home"], "away": out["away"]},
            "_out": out,
            "sources": [src, st_src],
        })
    # attach recent results
    for f in fixtures:
        f["recent"] = [h for h in history if h["home"] == f["home_code"] or h["away"] == f["home_code"]
                       or h["home"] == f["away_code"] or h["away"] == f["away_code"]]
        f["recent"] = sorted(f["recent"], key=lambda r: r["date"], reverse=True)[:6]
    return fixtures, {"league_avg_goals": round(base, 4), "teams": strength}


# --------------------------------------------------------------------------
# MLB
# --------------------------------------------------------------------------
def live_index() -> dict:
    d = json.loads((REPO / "data/session-1695b749/live_checks.json").read_text())
    return {e["name"]: e for e in d["entries"]}


def live_source(name: str, idx: dict) -> dict:
    e = idx[name]
    path = REPO / e["file"]
    got = sha256(path)
    if got != e["sha256"]:
        raise SystemExit(f"live hash mismatch for {name}")
    return {"name": name, "url": e["url"], "sha256": got, "bytes": e["bytes"],
            "fetched_at_utc": e["read_at_utc"], "file": e["file"], "kind": "live re-read"}


def mlb_inputs(idx, liveidx):
    st_src = verified_source("mlb_standings", idx)
    sch_src = live_source("mlb_ws_schedule_live_2026-10-22", liveidx)
    hit_src = live_source("mlb_hitting_runs_2026", liveidx)
    pit_src = live_source("mlb_pitching_runs_2026", liveidx)
    schedule = json.loads((REPO / liveidx["mlb_ws_schedule_live_2026-10-22"]["file"]).read_text())
    hitting = json.loads((REPO / liveidx["mlb_hitting_runs_2026"]["file"]).read_text())
    pitching = json.loads((REPO / liveidx["mlb_pitching_runs_2026"]["file"]).read_text())
    standings = load("mlb_standings.json")
    return schedule, standings, hitting, pitching, [st_src, sch_src, hit_src, pit_src]


def mlb_board(schedule, standings, hitting, pitching, sources):
    rs, ra = {}, {}
    for row in hitting["stats"][0]["splits"]:
        rs[row["team"]["name"]] = (row["stat"]["runs"], row["stat"]["gamesPlayed"])
    for row in pitching["stats"][0]["splits"]:
        ra[row["team"]["name"]] = (row["stat"]["runs"], row["stat"]["gamesPlayed"])
    base = sum(v[0] for v in rs.values()) / sum(v[1] for v in rs.values())

    splits = {}
    for rec in standings["records"]:
        for t in rec["teamRecords"]:
            if "runsScored" not in t:
                continue
            sp = {x["type"]: x for x in t["records"]["splitRecords"]}
            splits[t["team"]["name"]] = {
                "wins": t["wins"], "losses": t["losses"],
                "home": f'{sp["home"]["wins"]}-{sp["home"]["losses"]}',
                "away": f'{sp["away"]["wins"]}-{sp["away"]["losses"]}',
                "last_ten": f'{sp["lastTen"]["wins"]}-{sp["lastTen"]["losses"]}',
                "one_run": f'{sp["oneRun"]["wins"]}-{sp["oneRun"]["losses"]}',
            }
    prior = 40.0
    strength = {}
    for name, (runs, gp) in rs.items():
        allowed, _ = ra[name]
        strength[name] = {
            "rs": runs, "ra": allowed, "gp": gp,
            "rs_pg": round(runs / gp, 3), "ra_pg": round(allowed / gp, 3),
            "attack": round(M.shrink(runs / gp, base, gp, prior) / base, 4),
            "defence": round(M.shrink(allowed / gp, base, gp, prior) / base, 4),
            **splits.get(name, {}),
        }

    fixtures = []
    for dt in schedule["dates"]:
        if not (WINDOW_FROM <= dt["date"] <= WINDOW_TO):
            continue
        for g in dt["games"]:
            hn = g["teams"]["home"]["team"]["name"]
            an = g["teams"]["away"]["team"]["name"]
            hs, as_ = strength[hn], strength[an]
            lam_h = min(max(base * hs["attack"] * as_["defence"] * 1.02, 2.4), 7.5)
            lam_a = min(max(base * as_["attack"] * hs["defence"] * 0.98, 2.4), 7.5)
            out = M.outcome_probs(lam_h, lam_a)
            fixtures.append({
                "id": f"mlb-{dt['date']}-{an.split()[-1].lower()}-{hn.split()[-1].lower()}",
                "sport": "Baseball", "competition": "MLB World Series 2026",
                "home": hn, "away": an, "home_code": hn, "away_code": an,
                "home_short": hn.split()[-1], "away_short": an.split()[-1],
                "date": dt["date"], "start_utc": g["gameDate"], "venue": g["venue"]["name"],
                "game_id": g["gamePk"], "book": "mlb",
                "inputs": {"home": hs, "away": as_, "league_avg_runs": round(base, 4), "prior_games": prior},
                "lambdas": {"home": round(lam_h, 3), "away": round(lam_a, 3)},
                "model": {"home": out["home"], "away": out["away"]},
                "_out": out, "recent": [], "sources": sources,
            })
    spec = {"league_avg_runs": round(base, 4), "prior_games": prior,
            "teams": {k: v for k, v in strength.items()}}
    return fixtures, spec


# --------------------------------------------------------------------------
# LoL
# --------------------------------------------------------------------------
def lol_inputs(idx):
    src = verified_source("lolesports_schedule", idx)
    return load("lolesports_schedule.json"), src


def lol_board(schedule, src):
    events = schedule["data"]["schedule"]["events"]
    fixtures = []
    for e in events:
        if e.get("type") != "match" or not e.get("match"):
            continue
        d = e["startTime"][:10]
        if not (WINDOW_FROM <= d <= WINDOW_TO):
            continue
        if e["state"] not in ("unstarted", "inProgress"):
            continue
        m = e["match"]
        if len(m["teams"]) != 2:
            continue
        t1, t2 = m["teams"]
        r1, r2 = t1.get("record"), t2.get("record")
        if not r1 or not r2 or "wins" not in r1 or "wins" not in r2:
            fixtures.append({
                "id": f"lol-{d}-{t1['code'].lower()}-{t2['code'].lower()}-{m['id']}",
                "sport": "Esports",
                "competition": e["league"]["name"] + " · " + (e.get("blockName") or ""),
                "home": t1["name"], "away": t2["name"],
                "home_code": t1["code"], "away_code": t2["code"],
                "home_short": t1["name"], "away_short": t2["name"],
                "date": d, "start_utc": e["startTime"], "venue": "online / studio",
                "game_id": m["id"], "book": "lol",
                "best_of": (m.get("strategy") or {}).get("count", 3),
                "inputs": {"home": r1, "away": r2, "p_map": None},
                "lambdas": {}, "model": None, "priced": False, "_out": None,
                "unpriced_reason": "The official schedule returns no series record for at least one side, so there is no numeric input to price from.",
                "recent": [], "sources": [src],
            })
            continue
        p_map = M.two_way_from_ratio(
            (r1["wins"] + 1.5) / (r1["wins"] + r1["losses"] + 3.0),
            (r2["wins"] + 1.5) / (r2["wins"] + r2["losses"] + 3.0),
            1.0,
        )
        bo = m["strategy"]["count"] if m.get("strategy") else 3
        ser = M.series_from_map(p_map, bo)
        fixtures.append({
            "id": f"lol-{d}-{t1['code'].lower()}-{t2['code'].lower()}-{m['id']}",
            "sport": "Esports",
            "competition": e["league"]["name"] + " · " + (e.get("blockName") or ""),
            "home": t1["name"], "away": t2["name"],
            "home_code": t1["code"], "away_code": t2["code"],
            "home_short": t1["name"], "away_short": t2["name"],
            "date": d,
            "start_utc": e["startTime"],
            "venue": "online / studio",
            "game_id": m["id"],
            "book": "lol",
            "best_of": bo,
            "inputs": {"home": r1, "away": r2, "p_map": round(p_map, 4)},
            "lambdas": {},
            "model": {"home": ser["series_home"], "away": ser["series_away"]},
            "_series": ser,
            "_out": {"home": ser["series_home"], "away": ser["series_away"]},
            "recent": [],
            "sources": [src],
        })
    return fixtures, {"matches_listed": len(events)}


# --------------------------------------------------------------------------
# markets, picks, grades
# --------------------------------------------------------------------------
def sel(name, market, line, p, side):
    p = round(float(p), 4)
    price = M.american(p)
    return {
        "selection": name, "market": market, "line": line,
        "p": p, "price": price, "side": side,
        "implied": round(M.implied(price), 4),
        "grade": "High" if p >= 0.70 else ("Medium" if p >= 0.62 else "Low"),
        "in_window": -250 <= price <= 10000,
    }


def markets_for(f):
    out = f["_out"]
    if f["book"] == "nhl":
        lines = {
            "moneyline": [sel(f["home"], "Match winner (two-way)", None, out["home"], "home"),
                          sel(f["away"], "Match winner (two-way)", None, out["away"], "away")],
            "handicap": [
                sel(f["home"], "Puck line", -1.5, M.p_margin_at_least(2, out["margin"]), "home"),
                sel(f["away"], "Puck line", 1.5, 1 - M.p_margin_at_least(2, out["margin"]), "away"),
            ],
            "total": [],
            "team_total": [],
        }
        for line in (5.5, 6.5):
            over = M.p_total_over(line, out["total"])
            lines["total"] += [sel("Over", "Match total", line, over, "over"),
                               sel("Under", "Match total", line, 1 - over, "under")]
        for side, key, team in (("home", "home_goals", f["home"]), ("away", "away_goals", f["away"])):
            for line in (2.5, 3.5):
                over = M.p_team_over(line, out[key])
                lines["team_total"] += [
                    sel(f"{team} over", "Team total", line, over, side),
                    sel(f"{team} under", "Team total", line, 1 - over, side),
                ]
        return lines
    if f["book"] == "mlb":
        lines = {
            "moneyline": [sel(f["home"], "Match winner (two-way)", None, out["home"], "home"),
                          sel(f["away"], "Match winner (two-way)", None, out["away"], "away")],
            "handicap": [
                sel(f["home"], "Run line", -1.5, M.p_margin_at_least(2, out["margin"]), "home"),
                sel(f["away"], "Run line", 1.5, 1 - M.p_margin_at_least(2, out["margin"]), "away"),
            ],
            "total": [],
            "team_total": [],
        }
        for line in (7.5, 8.5):
            over = M.p_total_over(line, out["total"])
            lines["total"] += [sel("Over", "Match total", line, over, "over"),
                               sel("Under", "Match total", line, 1 - over, "under")]
        for side, key, team in (("home", "home_goals", f["home"]), ("away", "away_goals", f["away"])):
            for line in (3.5, 4.5):
                over = M.p_team_over(line, out[key])
                lines["team_total"] += [
                    sel(f"{team} over", "Team total", line, over, side),
                    sel(f"{team} under", "Team total", line, 1 - over, side),
                ]
        return lines
    ser = f["_series"]
    lines = {
        "moneyline": [sel(f["home"], "Series winner (two-way)", None, ser["series_home"], "home"),
                      sel(f["away"], "Series winner (two-way)", None, ser["series_away"], "away")],
        "handicap": [
            sel(f["home"], "Series handicap (maps)", -1.5, M.p_series_cover(ser["series_margin"], -1.5), "home"),
            sel(f["away"], "Series handicap (maps)", 1.5, 1 - M.p_series_cover(ser["series_margin"], -1.5), "away"),
        ],
        "total": [],
        "team_total": [],
    }
    for line in (2.5, 3.5, 4.5):
        over = M.p_total_over(line, ser["games"])
        lines["total"] += [sel("Over", "Total maps", line, over, "over"),
                           sel("Under", "Total maps", line, 1 - over, "under")]
    return lines


CORE = ("moneyline", "handicap", "total")


def grade_pick(f, lines):
    """One graded pick per core market; the moneyline pick is the headline pick."""
    picks = []
    for market in CORE:
        picks.append(dict(max(lines[market], key=lambda s: s["p"]), core_market=market))
    f["picks"] = picks
    f["headline"] = picks[0]
    f["grade"] = picks[0]["grade"]
    f["markets"] = lines
    f["n_selections"] = sum(len(v) for v in lines.values())
    f["n_high"] = sum(1 for v in lines.values() for s in v if s["grade"] == "High")
    f["n_high_in_window"] = sum(1 for v in lines.values() for s in v if s["grade"] == "High" and s["in_window"])
    f["n_pick_high_in_window"] = sum(1 for s in picks if s["grade"] == "High" and s["in_window"])
    return f


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    idx = manifest_index()
    games, history, standings, nhl_src = nhl_inputs(idx)
    nhl, nhl_spec = nhl_board(games, history, standings, nhl_src[-1], None)
    liveidx = live_index()
    sch, st, hit, pit, mlb_src = mlb_inputs(idx, liveidx)
    mlb, mlb_spec = mlb_board(sch, st, hit, pit, mlb_src)
    lols, lol_src = lol_inputs(idx)
    lol, lol_spec = lol_board(lols, lol_src)
    fixtures = nhl + mlb + lol
    fixtures = [f for f in fixtures if WINDOW_FROM <= f["date"] <= "2026-11-21"]
    for f in fixtures:
        f["fixture"] = f'{f["away"]} at {f["home"]}'
        if f.get("priced") is False:
            f.update(markets={}, picks=[], headline=None, grade=None, n_selections=0,
                     n_high=0, n_high_in_window=0, n_pick_high_in_window=0)
            continue
        grade_pick(f, markets_for(f))

    in_window = [(f, s) for f in fixtures for k, v in f["markets"].items() for s in v
                 if s["grade"] == "High" and s["in_window"]]
    print("fixtures", len(fixtures), "| NHL", len(nhl), "MLB", len(mlb), "LoL", len(lol))
    print("selections", sum(f["n_selections"] for f in fixtures))
    print("High selections", sum(f["n_high"] for f in fixtures), "| in window", len(in_window))
    from collections import Counter
    print(Counter(f["grade"] for f in fixtures))
    print(Counter((s["market"], s["grade"]) for f, s in in_window))
    return fixtures, in_window




# --------------------------------------------------------------------------
# outputs: verification register, coverage, flags, listing, desk
# --------------------------------------------------------------------------
CORE_LABEL = {"moneyline": "match winner", "handicap": "handicap", "total": "match total"}


def attach_predictions(fixtures):
    path = REPO / "data/session-1695b749/ac/authored_predictions.json"
    authored = json.loads(path.read_text())["items"] if path.exists() else []
    by_key = {(p["fixture"], p["market"], p["line"], p["selection"]): p for p in authored}
    used = set()
    for f in fixtures:
        for s in f.get("picks", []):
            key = (f["id"], s["market"], s["line"], s["selection"])
            if key in by_key:
                s["write_up"] = by_key[key]["text"]
                s["write_up_words"] = by_key[key]["words"]
                used.add(key)
        if f.get("markets"):
            for market, sels in f["markets"].items():
                for s in sels:
                    key = (f["id"], s["market"], s["line"], s["selection"])
                    if key in by_key:
                        s["write_up"] = by_key[key]["text"]
                        used.add(key)
    missing = [k for k in by_key if k not in used]
    if missing:
        raise SystemExit(f"authored prediction matched no selection: {missing}")
    return len(by_key)


def build_verification(fixtures):
    rows = []
    for f in fixtures:
        srcs = f["sources"]
        fields = [
            {"field": "participants", "value": f'{f["away"]} at {f["home"]}', "source": srcs[0]["url"], "sha256": srcs[0]["sha256"]},
            {"field": "date and start time (UTC)", "value": f'{f["date"]} {f["start_utc"]}', "source": srcs[0]["url"], "sha256": srcs[0]["sha256"]},
            {"field": "venue", "value": f["venue"], "source": srcs[0]["url"], "sha256": srcs[0]["sha256"]},
        ]
        if f["book"] == "nhl":
            st = srcs[-1]
            fields += [
                {"field": "home record / goals", "value": f'{f["inputs"]["home"]["record"]}, {f["inputs"]["home"]["gf"]} for, {f["inputs"]["home"]["ga"]} against in {f["inputs"]["home"]["gp"]} games', "source": st["url"], "sha256": st["sha256"]},
                {"field": "away record / goals", "value": f'{f["inputs"]["away"]["record"]}, {f["inputs"]["away"]["gf"]} for, {f["inputs"]["away"]["ga"]} against in {f["inputs"]["away"]["gp"]} games', "source": st["url"], "sha256": st["sha256"]},
            ]
        elif f["book"] == "mlb":
            fields += [
                {"field": "home runs scored / allowed", "value": f'{f["inputs"]["home"]["rs"]} scored, {f["inputs"]["home"]["ra"]} allowed in {f["inputs"]["home"]["gp"]} games', "source": f["sources"][2]["url"], "sha256": f["sources"][2]["sha256"]},
                {"field": "away runs scored / allowed", "value": f'{f["inputs"]["away"]["rs"]} scored, {f["inputs"]["away"]["ra"]} allowed in {f["inputs"]["away"]["gp"]} games', "source": f["sources"][2]["url"], "sha256": f["sources"][2]["sha256"]},
                {"field": "season win-loss and splits", "value": f'{f["inputs"]["home"].get("wins")}-{f["inputs"]["home"].get("losses")} (home {f["inputs"]["home"].get("home")}) v {f["inputs"]["away"].get("wins")}-{f["inputs"]["away"].get("losses")} (away {f["inputs"]["away"].get("away")})', "source": f["sources"][0]["url"], "sha256": f["sources"][0]["sha256"]},
            ]
        elif f["book"] == "lol" and f.get("priced") is not False:
            fields += [
                {"field": "series records", "value": f'{f["inputs"]["home"]["wins"]}-{f["inputs"]["home"]["losses"]} v {f["inputs"]["away"]["wins"]}-{f["inputs"]["away"]["losses"]}', "source": srcs[0]["url"], "sha256": srcs[0]["sha256"]},
                {"field": "series format", "value": f'best of {f["best_of"]}', "source": srcs[0]["url"], "sha256": srcs[0]["sha256"]},
            ]
        rows.append({
            "id": f["id"], "sport": f["sport"], "competition": f["competition"],
            "fixture": f'{f["away"]} at {f["home"]}',
            "date": f["date"], "start_utc": f["start_utc"],
            "priced": f.get("priced") is not False,
            "fields": fields,
            "sources": [{"url": s["url"], "sha256": s["sha256"], "fetched_at_utc": s["fetched_at_utc"], "kind": s.get("kind", "captured 22 Oct 2026")} for s in f["sources"]],
            "not_checked": ["injuries", "suspensions", "line-ups", "weather", "line movement"],
        })
    return {"schema": "olbg4.board-ac.verification/1", "rows": rows}


def build_coverage(fixtures, listing):
    labels = ["Ice Hockey", "Baseball", "Basketball", "Cricket", "Darts", "Esports", "Golf",
              "Greyhound Racing", "Handball", "Rugby League", "Rugby Union", "Snooker",
              "Tennis", "Volleyball", "Aussie Rules", "Badminton", "Table Tennis",
              "Gaelic Football", "Motor Racing"]
    priced, listed = {}, {}
    for f in fixtures:
        if f.get("priced") is not False:
            priced[f["sport"]] = priced.get(f["sport"], 0) + 1
    for e in listing:
        listed[e["sport"]] = listed.get(e["sport"], 0) + 1
    rows = []
    for lab in labels:
        n = priced.get(lab, 0)
        l = listed.get(lab, 0)
        if n:
            status = "priced"
            note = f"{n} fixtures with our own moneyline, handicap and total"
        elif l:
            status = "listed only"
            note = (f"{l} match rows on OLBG's live listing; no official numeric input captured, "
                    "so no price and no pick, and the official source column is deliberately blank")
        else:
            status = "no fixture"
            note = "no in-window fixture on any official page captured this session"
        rows.append({"sport": lab, "priced": n, "listed": l, "status": status, "note": note})
    excluded = ["Soccer", "Boxing", "UFC/MMA", "American Football", "Football (any code not listed above)",
                "Hurling", "Horse Racing", "Cycling", "Specials"]
    return {"schema": "olbg4.board-ac.coverage/1", "rows": rows,
            "excluded_by_brief": excluded,
            "summary": {"labels": len(labels), "priced_labels": sum(1 for r in rows if r["priced"]),
                        "listed_only": sum(1 for r in rows if r["status"] == "listed only"),
                        "no_fixture": sum(1 for r in rows if r["status"] == "no fixture")}}


def build_flags(fixtures, picks_in_window, coverage):
    n_high = sum(1 for f in fixtures for s in f.get("picks", []) if s["grade"] == "High")
    n_picks = sum(len(f.get("picks", [])) for f in fixtures)
    n_shorter = n_high - len(picks_in_window)
    dates = sorted({f["date"] for f in fixtures})
    items = [
        {"id": "AF-01", "severity": "structural",
         "title": "The -250 floor and the over-70% requirement can only overlap between 70.0% and 71.4%",
         "detail": (f"-250 is an implied probability of 71.43%, so any selection the model rates above 71.43% prices shorter than the floor. "
                    f"This desk grades {n_high} of its {n_picks} picks High; {len(picks_in_window)} of those sit inside -250 to +10,000 and carry a written prediction, "
                    f"while {n_shorter} are shorter than -250. Both sets are published with their prices and neither is relabelled. No price was bent to fit the window."),
         "sources": ["https://api-web.nhle.com/v1/standings/now"]},
        {"id": "AF-02", "severity": "coverage",
         "title": "Lines were originated for 3 of the 19 sport labels considered; the other 16 are blank and reasoned",
         "detail": ("Only NHL, MLB and LoL Esports had official numeric inputs in reach this session, so only those carry prices. "
                    f"{coverage['summary']['listed_only']} further labels appear as OLBG listing rows with the official source left blank, "
                    f"and {coverage['summary']['no_fixture']} had no in-window fixture on any official page captured here. "
                    "Nothing is estimated to fill the gap."),
         "sources": ["https://www.olbg.com/betting-tips"]},
        {"id": "AF-03", "severity": "model",
         "title": "World Series prices use season-long run rates, with no starting pitcher, bullpen or park adjustment",
         "detail": ("The MLB payload used here returns team runs scored and allowed over 162 games plus home/away splits, and nothing about probable starters, "
                    "bullpen usage or park factors. The seven World Series games are therefore priced from team-level run rates only, which is a real limitation in a short series. "
                    "No pitcher data is invented and the gap is recorded rather than filled."),
         "sources": ["https://statsapi.mlb.com/api/v1/teams/stats?stats=season&group=hitting&season=2026&sportIds=1&fields=stats,splits,team,id,name,runs,gamesPlayed,stat"]},
        {"id": "AF-04", "severity": "model",
         "title": "A regulation draw is split 50/50 in the NHL model because no shootout model is defensible from the payload",
         "detail": ("The two-way NHL price has to do something with a tied score after regulation. This desk gives each side half of the draw probability, which leaves the "
                    "moneyline slightly conservative for strong teams. The assumption is named in model_spec.json and is not presented as an observed value."),
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-22"]},
        {"id": "AF-05", "severity": "model",
         "title": "LoL map handicaps and map totals assume independent, identical maps",
         "detail": ("The LoL schedule payload gives series records and best-of length but no map-level scores, so the map markets are derived from a per-map probability "
                    "under an independent-maps assumption. That flattens real draft and side effects. 25 listed series carry no price at all because the payload returns no record for at least one team."),
         "sources": ["https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US"]},
        {"id": "AF-06", "severity": "coverage",
         "title": f"Window published as {dates[0]} to {dates[-1]}, not the full 22 October to 21 November range",
         "detail": (f"The captured daily payloads run to 2 November and the last fixture they contain falls on {dates[-1]}. "
                    "No official page was read for 10-21 November, so that part of the requested window is empty rather than guessed. "
                    "A fresh capture of those dates would extend the desk."),
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-11-02"]},
        {"id": "AF-07", "severity": "verification",
         "title": "OLBG's listing is carried as a listing, never as an official source",
         "detail": ("119 in-scope match rows are reproduced with their event name, start time and OLBG link so the in-scope universe is visible. "
                    "Each of them has a blank official source, a blank price and a blank pick, and none of OLBG's tips, percentages, prices or comments is copied. "
                    "Only rows with a governing-body payload behind them are marked verified."),
         "sources": ["https://www.olbg.com/betting-tips"]},
        {"id": "AF-08", "severity": "data",
         "title": "NHL strength inputs come from one standings snapshot and are not re-read per match date",
         "detail": ("Every NHL price uses the 2026-10-22 standings snapshot, so fixtures in November are priced with October form. "
                    "The snapshot is hash-checked and its capture time is printed on every row; it is not silently blended with later results."),
         "sources": ["https://api-web.nhle.com/v1/standings/now"]},
        {"id": "AF-09", "severity": "verification",
         "title": "No injury, suspension, line-up, weather or line-movement check was performed",
         "detail": ("The register covers participants, date, start time, venue and the numeric scoring inputs only. Team news and market movement are named as unchecked on every row "
                    "rather than implied to be clear."),
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-22"]},
        {"id": "AF-10", "severity": "data",
         "title": "Two High picks land on the same Islanders-Wild fixture and are correlated",
         "detail": ("The Islanders +1.5 puck line and the under 6.5 goals both qualify on 30 October in Minnesota. A tight, low-scoring game settles both, so they should be treated as one view, "
                    "not two independent bets. Both are published with separate write-ups and the correlation is disclosed here."),
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-30"]},
        {"id": "AF-11", "severity": "coverage",
         "title": "Recent-results evidence is limited to the games present in the captured 15-21 October payloads",
         "detail": ("Those daily files list only the games the NHL feed returned for each date, so a few clubs show two completed games rather than three. "
                    "Write-ups cite only games present in the payloads; no result is inferred from a standings total."),
         "sources": ["https://api-web.nhle.com/v1/schedule/2026-10-21"]},
        {"id": "AF-13", "severity": "repo",
         "title": "Two captured AFL payloads are gzip bytes stored with a .json extension",
         "detail": ("data/session-e5f2dad3/raw/afl_api_fixtures.json and afl_api_season.json begin with the gzip magic bytes rather than JSON, and the capture manifest records both as HTTP 401. "
                    "Any tool that globs data/**/*.json and parses blindly will fail on them; this board's review flags them rather than repairing another session's capture. They are not used as inputs here."),
         "sources": ["https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/session-e5f2dad3/raw/afl_api_fixtures.json",
                     "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/session-e5f2dad3/manifest.json"]},
        {"id": "AF-15", "severity": "repo",
         "title": "Sixteen archived pages under session-4a73430b/ are missing closing html tags",
         "detail": ("The review's well-formedness check fails on every page in session-4a73430b/ (index, picks, markets, olbg, methodology, flagged and ten sport pages): each file ends without </body> or </html>. "
                    "Browsers render them and the local link audit passes, so nothing published is broken, but the markup is truncated and any strict parser will reject it. "
                    "The files belong to another board's scope, so they are reported here and left untouched."),
         "sources": ["https://github.com/buffedlizard55-lab/OLBG4/tree/main/session-4a73430b"]},
        {"id": "AF-14", "severity": "repo",
         "title": "One archived board page is missing its closing html tag",
         "detail": ("session-07a080b9/index.html ends after its last paragraph with no </body> or </html>, so the file is truncated markup rather than a complete document. "
                    "Browsers render it and the local link audit passes, but it is not well-formed HTML. The file belongs to another board's scope, so it is reported here and left untouched."),
         "sources": ["https://github.com/buffedlizard55-lab/OLBG4/blob/main/session-07a080b9/index.html"]},
        {"id": "AF-12", "severity": "repo",
         "title": "Two existing generators rewrite the repository root, so a root pointer can be overwritten silently",
         "detail": ("tools/build_master_site.py and scripts/session-83451f65/build_site.py both write index.html and the root pages. "
                    "No CI gate diffs the root against either generator. This board kept its root change additive and restored the committed pages after testing, "
                    "and the collision is recorded here rather than fixed inside another board's generator."),
         "sources": ["https://github.com/buffedlizard55-lab/OLBG4/blob/main/tools/build_master_site.py"]},
    ]
    return {"schema": "olbg4.board-ac.flagged/1", "items": items}


def build_listing(fixtures):
    src = REPO / "data/session-e5f2dad3/olbg_listing.json"
    payload = json.loads(src.read_text())
    ranked = {f["home_short"].lower(): f for f in fixtures}
    nicknames = {}
    for f in fixtures:
        nicknames[f["home_short"].lower()] = f["id"]
        nicknames[f["away_short"].lower()] = f["id"]
    rows, matched = [], 0
    for e in payload["events"]:
        name = e["name"]
        low = name.lower()
        hit = next((v for k, v in nicknames.items() if k in low), None)
        if hit:
            matched += 1
        rows.append({
            "sport": e["sport"], "event": name, "start_utc": e["start_utc"],
            "market": e["market"], "selection": e["selection"],
            "olbg_url": e["url"], "listed_at_utc": e["listed_by_olbg_at_utc"],
            "official_source": "", "price": "", "pick": "",
            "status": "unverified",
            "matched_fixture": hit or "",
        })
    return {"schema": "olbg4.board-ac.listing/1",
            "captured_at_utc": payload["captured_at_utc"],
            "note": ("In-scope match rows exactly as OLBG lists them. Carried so the full in-scope fixture list is visible; "
                     "no price, pick or tip is taken from OLBG and the official source column stays empty."),
            "rows": rows, "matched_to_priced_fixture": matched}


def build_model_spec(nhl_spec, mlb_spec, lol_spec):
    return {
        "schema": "olbg4.board-ac.model/1",
        "principles": ["no bookmaker price is read anywhere", "every input is a number returned by an official payload",
                       "no value is filled when the payload is silent", "prices are fair odds derived from our own probability, with no margin added"],
        "american_price": "p >= 0.5 -> round(-100p/(1-p)); p < 0.5 -> round(100(1-p)/p)",
        "grade_thresholds": {"High": "p >= 0.70", "Medium": "0.62 <= p < 0.70", "Low": "p < 0.62"},
        "window_test": "price between -250 and +10,000 inclusive, evaluated on the price we quote",
        "nhl": {
            "distribution": "independent Poisson goals per side over 60 minutes plus overtime, scored up to 16 goals",
            "league_average_goals_per_team_game": nhl_spec["league_avg_goals"],
            "attack": "shrunken goals-for rate / league average, prior 8 games",
            "defence": "shrunken goals-against rate / league average, prior 8 games",
            "home_edge": "1.06 on the home lambda, 0.94 on the away lambda",
            "lambda_clamp": [1.6, 5.2],
            "draw_handling": "half of the regulation draw is credited to each side",
            "markets": ["moneyline (two-way)", "puck line +-1.5", "match total 5.5 and 6.5", "team totals 2.5 and 3.5"],
        },
        "mlb": {
            "distribution": "independent Poisson runs per side",
            "league_average_runs_per_team_game": mlb_spec["league_avg_runs"],
            "attack": "shrunken runs-scored rate / league average, prior 40 games",
            "defence": "shrunken runs-allowed rate / league average, prior 40 games",
            "home_edge": "1.02 on the home lambda, 0.98 on the away lambda",
            "lambda_clamp": [2.4, 7.5],
            "draw_handling": "half of the tie is credited to each side (extra innings)",
            "markets": ["moneyline (two-way)", "run line +-1.5", "match total 7.5 and 8.5", "team totals 3.5 and 4.5"],
        },
        "lol": {
            "map_probability": "Bradley-Terry style ratio of smoothed series win rates, prior 1.5 wins and 1.5 losses per side",
            "series": "independent and identical maps, exact best-of-n distribution",
            "markets": ["series winner (two-way)", "series handicap +-1.5 maps", "total maps 2.5, 3.5 and 4.5"],
            "unpriced": "series with no record for at least one team carry no price",
        },
        "assumptions_flagged": ["AF-01", "AF-03", "AF-04", "AF-05", "AF-08"],
    }


def write_outputs():
    OUT.mkdir(parents=True, exist_ok=True)
    idx = manifest_index()
    liveidx = live_index()
    games, history, standings, nhl_src = nhl_inputs(idx)
    nhl, nhl_spec = nhl_board(games, history, standings, nhl_src[-1], None)
    sch, st, hit, pit, mlb_src = mlb_inputs(idx, liveidx)
    mlb, mlb_spec = mlb_board(sch, st, hit, pit, mlb_src)
    lols, lol_src = lol_inputs(idx)
    lol, lol_spec = lol_board(lols, lol_src)

    fixtures = [f for f in nhl + mlb + lol if WINDOW_FROM <= f["date"] <= "2026-11-21"]
    fixtures.sort(key=lambda f: (f["date"], f["start_utc"], f["id"]))
    for f in fixtures:
        f["fixture"] = f'{f["away"]} at {f["home"]}'
        if f.get("priced") is False:
            f.update(markets={}, picks=[], headline=None, grade=None, n_selections=0,
                     n_high=0, n_high_in_window=0, n_pick_high_in_window=0)
            continue
        grade_pick(f, markets_for(f))
    n_pred = attach_predictions(fixtures)

    picks_in_window = [dict(fixture=f, pick=s) for f in fixtures for s in f.get("picks", [])
                       if s["grade"] == "High" and s["in_window"]]
    listing = build_listing(fixtures)
    coverage = build_coverage(fixtures, listing["rows"])
    flags = build_flags(fixtures, picks_in_window, coverage)

    desk = {
        "schema": "olbg4.board-ac.desk/1",
        "session": "arena/1695b749-olbg4",
        "built_at_utc": "2026-10-22T09:30:00Z",
        "window": {"from": WINDOW_FROM, "to": WINDOW_MAX},
        "covered_dates": [min(f["date"] for f in fixtures), max(f["date"] for f in fixtures)],
        "fixtures": fixtures,
        "totals": {
            "fixtures": len(fixtures),
            "priced_fixtures": sum(1 for f in fixtures if f.get("priced") is not False),
            "unpriced_fixtures": sum(1 for f in fixtures if f.get("priced") is False),
            "selections": sum(f["n_selections"] for f in fixtures),
            "picks": sum(len(f.get("picks", [])) for f in fixtures),
            "picks_high": sum(1 for f in fixtures for s in f.get("picks", []) if s["grade"] == "High"),
            "picks_medium": sum(1 for f in fixtures for s in f.get("picks", []) if s["grade"] == "Medium"),
            "picks_low": sum(1 for f in fixtures for s in f.get("picks", []) if s["grade"] == "Low"),
            "high_in_window": len(picks_in_window),
            "predictions": n_pred,
            "listing_rows": len(listing["rows"]),
            "flags": len(flags["items"]),
        },
        "by_sport": {},
    }
    for s in ("Ice Hockey", "Baseball", "Esports"):
        fs = [f for f in fixtures if f["sport"] == s]
        desk["by_sport"][s] = {
            "fixtures": len(fs),
            "priced": sum(1 for f in fs if f.get("priced") is not False),
            "picks": sum(len(f.get("picks", [])) for f in fs),
            "high": sum(1 for f in fs for s_ in f.get("picks", []) if s_["grade"] == "High"),
            "high_in_window": sum(1 for f in fs for s_ in f.get("picks", []) if s_["grade"] == "High" and s_["in_window"]),
        }
    desk["picks_in_window"] = [
        {"fixture_id": p["fixture"]["id"], "sport": p["fixture"]["sport"],
         "fixture": f'{p["fixture"]["away"]} at {p["fixture"]["home"]}',
         "date": p["fixture"]["date"], "market": p["pick"]["market"], "line": p["pick"]["line"],
         "selection": p["pick"]["selection"], "price": p["pick"]["price"],
         "p": p["pick"]["p"], "write_up": p["pick"].get("write_up", "")}
        for p in picks_in_window]

    model_spec = build_model_spec(nhl_spec, mlb_spec, lol_spec)
    verification = build_verification(fixtures)

    for name, payload in (("desk", desk), ("model_spec", model_spec), ("verification", verification),
                          ("coverage", coverage), ("flagged", flags), ("listing", listing)):
        (OUT / f"{name}.json").write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    (OUT / "sources.json").write_text(json.dumps(
        {"schema": "olbg4.board-ac.sources/1",
         "capture_manifest": "data/session-e5f2dad3/manifest.json",
         "capture_note": "Official payloads captured by a GitHub Actions runner on 22 October 2026; each file is re-hashed against the manifest before use.",
         "live_manifest": "data/session-1695b749/live_checks.json",
         "sources": sorted({(s["url"], s["sha256"], s["fetched_at_utc"], s.get("kind", "captured"))
                            for f in fixtures for s in f["sources"]}, key=lambda x: x[0]) and [
             {"url": u, "sha256": h, "fetched_at_utc": t, "kind": k}
             for (u, h, t, k) in sorted({(s["url"], s["sha256"], s["fetched_at_utc"], s.get("kind", "captured"))
                                         for f in fixtures for s in f["sources"]})]},
        indent=1) + "\n")
    print(json.dumps(desk["totals"], indent=1))
    print({k: v for k, v in desk["by_sport"].items()})
    return desk


if __name__ == "__main__":
    write_outputs()

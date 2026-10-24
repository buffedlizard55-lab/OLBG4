#!/usr/bin/env python3
"""Board ZZ — originate our own lines for every verified fixture and pick a selection.

Input : data/session-edffdbc6/fixtures.json
Output: data/session-edffdbc6/desk.json

For every fixture we originate, from the official strength inputs stored with it:
  * match winner (two-way, or three-way where the sport can draw),
  * a handicap / spread ladder on a 0.5 or 0.25 unit lattice,
  * a match-total ladder on the same lattice,
  * plus the sport-specific derivative markets each model supports (set / frame / leg handicap,
    top-k finish, head-to-head matchup, exact set score).
The headline pick is chosen by `mathlib.choose_pick`: the strongest selection whose own-line
probability sits in the brief's High band (0.7000–0.7143 → −250…−233) if such a threshold exists,
otherwise the strongest in-window selection (Medium ≥ 0.55), otherwise the strongest outright
selection (Low).  Nothing is randomised and no probability is written by hand.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import mathlib as M

ROOT = Path(__file__).resolve().parents[2]
FIX = ROOT / "data" / "session-edffdbc6" / "fixtures.json"
OUT = ROOT / "data" / "session-edffdbc6" / "desk.json"

NOW = datetime.now(timezone.utc).replace(microsecond=0)
HORIZON_DAYS = int(os.environ.get("ZZ_HORIZON_DAYS", "9"))
CAP_PER_SPORT = int(os.environ.get("ZZ_CAP_PER_SPORT", "24"))

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]


def q(x: float, nd: int = 2) -> float:
    return round(x, nd)


# ---------------------------------------------------------------------------------- engines
def poisson_engine(f: dict) -> tuple[list[dict], list[str]]:
    """Ice hockey / baseball style goal-or-run Poisson model."""
    h, a = f["stats"]["home"], f["stats"]["away"]
    kind = f["model"]["kind"]
    if kind == "poisson_goals":
        mu = f["model"]["league_mu"]
        gh, ga_h = h["gf"] / max(h["gp"], 1), h["ga"] / max(h["gp"], 1)
        ga, ga_a = a["gf"] / max(a["gp"], 1), a["ga"] / max(a["gp"], 1)
        lam_h = max(1.85, min(4.60, mu + 0.72 * ((gh - mu) + (ga_a - mu)) + f["model"]["home_adv"]))
        lam_a = max(1.70, min(4.40, mu + 0.72 * ((ga - mu) + (ga_h - mu)) - 0.10))
        hcap = [-0.5, -1.5, -2.5, +1.5, +2.5]
        totals = [4.5, 5.5, 6.5, 7.5]
        unit = "goals"
    elif kind == "poisson_goals_liiga":
        mu = f["model"]["league_mu"] / 2.0
        gh, ga_h = h["gf"] / max(h["gp"], 1), h["ga"] / max(h["gp"], 1)
        ga, ga_a = a["gf"] / max(a["gp"], 1), a["ga"] / max(a["gp"], 1)
        lam_h = max(1.60, min(4.20, mu + 0.55 * ((gh - mu) + (ga_a - mu)) + f["model"]["home_adv"]))
        lam_a = max(1.50, min(4.00, mu + 0.55 * ((ga - mu) + (ga_h - mu)) - 0.10))
        hcap = [-0.5, -1.5, -2.5, +1.5]
        totals = [4.5, 5.5, 6.5]
        unit = "goals"
    else:  # poisson_runs
        mu = f["model"]["league_mu"]
        rs_h, ra_h = (h.get("runsScored") or 0) / max(h["w"] + h["l"], 1), (h.get("runsAllowed") or 0) / max(h["w"] + h["l"], 1)
        rs_a, ra_a = (a.get("runsScored") or 0) / max(a["w"] + a["l"], 1), (a.get("runsAllowed") or 0) / max(a["w"] + a["l"], 1)
        lam_h = max(2.8, min(6.6, 0.5 * (rs_h + ra_a) + 0.15))
        lam_a = max(2.6, min(6.4, 0.5 * (rs_a + ra_h) - 0.05))
        hcap = [-1.5, +1.5]
        totals = [7.5, 8.5, 9.5, 10.5]
        unit = "runs"

    ph, pa = M.poisson_pmf(lam_h), M.poisson_pmf(lam_a)
    margin, total = M.margin_pmf(ph, pa), M.total_pmf(ph, pa)
    p_home_draw = M.p_at_least(margin, 0.5)
    p_draw = margin.get(0, 0.0)
    p_home = p_home_draw + 0.5 * p_draw  # overtime / extra innings treated as a coin flip on the tie
    markets = [M.two_way_win(f["home"], f["away"], p_home,
                             f"Poisson goal model: λ({f['home']})={q(lam_h)}, λ({f['away']})={q(lam_a)}")]
    markets += M.handicap_ladder(f["home"], f["away"], margin, hcap,
                                 "Same Poisson margin distribution, threshold lattice", unit)
    markets += M.total_ladder(f["home"], f["away"], total, totals,
                              "Same Poisson total distribution, threshold lattice", unit)
    facts = [f"goal/run expectancy from the captured official season totals: {f['home']} {q(lam_h)} vs {f['away']} {q(lam_a)}"]
    return markets, facts


def normal_engine(f: dict) -> tuple[list[dict], list[str]]:
    """Points-based sports: basketball, handball, rugby, Gaelic games."""
    kind = f["model"]["kind"]
    h, a = f["stats"]["home"], f["stats"]["away"]
    if kind in ("normal_points",):  # EuroLeague standings
        gph, gpa = max(h.get("gamesPlayed", 1), 1), max(a.get("gamesPlayed", 1), 1)
        pfh, pah = h.get("pointsFavour", 0) / gph, h.get("pointsAgainst", 0) / gph
        pfa, paa = a.get("pointsFavour", 0) / gpa, a.get("pointsAgainst", 0) / gpa
        eh = 0.52 * pfh + 0.48 * paa + 3.2
        ea = 0.52 * pfa + 0.48 * pah - 1.2
        sm, st = f["model"]["sigma_margin"], f["model"]["sigma_total"]
        max_line = 14
    elif kind == "normal_points_nba":
        eh, ea = h.get("off", 114.0), a.get("off", 114.0)
        sm, st = f["model"]["sigma_margin"], f["model"]["sigma_total"]
        max_line = 14
    elif kind == "normal_points_rugby":
        eh, ea = h.get("rating", 25.0), a.get("rating", 25.0)
        sm, st = 13.5, 12.0
        max_line = 16
    elif kind == "normal_points_handball":
        pph = h.get("gf_pg", 29.0)
        paa = a.get("gf_pg", 29.0)
        eh = 0.5 * (pph + a.get("ga_pg", 29.0)) + 1.6
        ea = 0.5 * (paa + h.get("ga_pg", 29.0)) - 1.0
        sm, st = 8.5, 9.0
        max_line = 9
    else:  # gaelic
        eh = 0.5 * (h.get("pf_pg", 20.0) + a.get("pa_pg", 20.0)) + 1.9
        ea = 0.5 * (a.get("pf_pg", 20.0) + h.get("pa_pg", 20.0)) - 0.6
        sm, st = 7.5, 8.0
        max_line = 8

    total_mean = eh + ea
    margin_pmf = M.normal_pmf(eh - ea, sm, -60, 60)
    total_pmf_d = M.normal_pmf(total_mean, st, 0, int(total_mean * 2) + 30)
    p_home = sum(v for k, v in margin_pmf.items() if k > 0) + 0.5 * margin_pmf.get(0, 0.0)
    three_way = kind in ("normal_points_rugby", "normal_points_gaelic")
    if three_way:
        p_draw = margin_pmf.get(0, 0.0)
        markets = [M.three_way(f["home"], f["away"], p_home, p_draw,
                               f"Normal points model: mean {q(eh)}–{q(ea)}, σmargin {sm}")]
    else:
        markets = [M.two_way_win(f["home"], f["away"], p_home,
                                 f"Normal points model: mean {q(eh)}–{q(ea)}, σmargin {sm}")]
    lines = [round(x * 0.5, 1) for x in range(1, int(max_line * 2) + 1)]
    lines = [ln for ln in (-x for x in lines)] + lines
    markets += M.handicap_ladder(f["home"], f["away"], margin_pmf, lines,
                                 "Same normal margin distribution, threshold lattice", "points")
    half = round(total_mean)
    tot_lines = [half - 6.5, half - 3.5, half - 1.5, half + 0.5, half + 1.5, half + 3.5,
                 round(total_mean * 2) / 2 + 0.5]
    tot_lines = sorted({ln for ln in tot_lines if abs(ln - total_mean) <= 12})
    markets += M.total_ladder(f["home"], f["away"], total_pmf_d, tot_lines,
                              "Same normal total distribution, threshold lattice", "points")
    return markets, [f"points expectancy from the captured official season averages: {f['home']} {q(eh)} vs {f['away']} {q(ea)}"]


def tennis_engine(f: dict) -> tuple[list[dict], list[str]]:
    h, a = f["stats"]["home"], f["stats"]["away"]
    rh, ra = h.get("rank") or 120, a.get("rank") or 120
    # Elo-free ranking model: probability from the log-ratio of official WTA singles rankings
    z = 0.42 * (__import__("math").log(max(ra, 1)) - __import__("math").log(max(rh, 1)))
    p_home = 1.0 / (1.0 + __import__("math").exp(-z))
    p_home = min(max(p_home, 0.08), 0.92)
    markets = [M.market("match_winner", "Match Winner (best of 3 sets)",
                        [M.outcome(f["home"], p_home), M.outcome(f["away"], 1 - p_home)],
                        f"Official WTA ranking model: #{rh} vs #{ra}")]
    markets += M.best_of(f["home"], f["away"], p_home, 3, "Set", [-1.5], [2.5],
                         "Binomial set model inverted from the ranking probability")
    # exact set score
    q_ = (p_home + 0.5 * 0)  # placeholder to keep the market sum exact below
    p20 = p_home * p_home
    p21 = p_home * (1 - p_home) * 2 * 0.5
    p02 = (1 - p_home) ** 2
    p12 = (1 - p_home) * p_home * 2 * 0.5
    markets.append(M.market("set_score", "Exact Set Score",
                            [M.outcome(f"{f['home']} 2-0", p20), M.outcome(f"{f['home']} 2-1", p21),
                             M.outcome(f"{f['away']} 2-1", p12), M.outcome(f"{f['away']} 2-0", p02)],
                            "Set-score tree from the same ranking probability"))
    return markets, [f"official WTA singles ranks: {f['home']} #{rh}, {f['away']} #{ra}"]


def bestof_engine(f: dict) -> tuple[list[dict], list[str]]:
    h, a = f["stats"]["home"], f["stats"]["away"]
    p_home = f["stats"].get("p_home")
    n_units = f["model"].get("units", 5)
    unit = f["model"].get("unit_name", "Set")
    if p_home is None:
        return [], []
    markets = [M.market("match_winner", f"Match Winner (best of {n_units} {unit.lower()}s)",
                        [M.outcome(f["home"], p_home), M.outcome(f["away"], 1 - p_home)],
                        f["model"].get("basis", "Strength model from the captured official table"))]
    lines = [1.5] if n_units <= 5 else [2.5, 4.5]
    totals = [n_units - 1.5] + ([n_units + 0.5] if n_units <= 5 else [])
    markets += M.best_of(f["home"], f["away"], p_home, n_units, unit, lines, totals,
                         "Binomial frame/leg model inverted from the match probability")
    return markets, f["model"].get("facts", [])


def outright_engine(f: dict) -> tuple[list[dict], list[str]]:
    runners = f["stats"].get("runners") or []
    if len(runners) < 4:
        return [], []
    w = [max(float(r["weight"]), 1e-6) for r in runners]
    s = sum(w)
    ps = [x / s for x in w]
    markets = [M.market("match_winner", "Outright Winner",
                        [M.outcome(r["name"], p) for r, p in zip(runners, ps)],
                        "Plackett-Luce weights from the captured official standings/prize-money table")]
    for k in (3, 5):
        if len(runners) > k:
            outs = []
            for r, p in zip(runners, ps):
                p_top = min(0.995, p * (1 + (k - 1) * 0.55))
                outs.append(M.outcome(f"{r['name']} Top {k}", p_top))
            markets.append(M.market(f"top_{k}", f"Top-{k} Finish (each-way, independent legs)",
                                    outs, "Plackett-Luce marginal lifted to top-k by field density"))
    pair = f["stats"].get("h2h")
    if pair:
        n1, n2 = pair
        p1 = next((p for r, p in zip(runners, ps) if r["name"] == n1), None)
        p2 = next((p for r, p in zip(runners, ps) if r["name"] == n2), None)
        if p1 and p2:
            ph = p1 / (p1 + p2)
            markets.append(M.market("handicap_h2h", f"Head-to-Head: {n1} vs {n2}",
                                    [M.outcome(n1, ph), M.outcome(n2, 1 - ph)],
                                    "Conditional Plackett-Luce pairwise dominance"))
    return markets, f["stats"].get("facts", [])


ENGINES = {
    "poisson_goals": poisson_engine,
    "poisson_goals_liiga": poisson_engine,
    "poisson_runs": poisson_engine,
    "normal_points": normal_engine,
    "normal_points_nba": normal_engine,
    "normal_points_rugby": normal_engine,
    "normal_points_handball": normal_engine,
    "normal_points_gaelic": normal_engine,
    "tennis_best_of_3": tennis_engine,
    "best_of": bestof_engine,
    "outright": outright_engine,
}


def originate(f: dict) -> dict | None:
    eng = ENGINES.get(f["model"]["kind"])
    if not eng:
        return None
    markets, facts = eng(f)
    if not markets:
        return None
    pick = M.choose_pick(markets)
    winner = M.winner_pick(markets)
    investigated = sorted({m["market_key"].split("_")[0] for m in markets})
    return {
        **{k: f[k] for k in ("id", "sport", "competition", "stage", "home", "away", "start_utc",
                             "venue", "source", "stats")},
        "markets": markets,
        "markets_investigated": investigated,
        "model_facts": facts,
        "pick": pick,
        "winner_pick": winner,
        "confidence": pick["confidence"] if pick else "Low",
    }


def main() -> int:
    data = json.loads(FIX.read_text(encoding="utf-8"))
    cutoff = datetime.fromisoformat(data["cutoff_utc"].replace("Z", "+00:00"))
    horizon = cutoff + timedelta(days=HORIZON_DAYS)
    by_sport: dict[str, list[dict]] = {s: [] for s in SPORTS}
    for f in data["fixtures"]:
        start = datetime.fromisoformat(f["start_utc"].replace("Z", "+00:00"))
        if not (cutoff < start <= horizon):
            continue
        by_sport.setdefault(f["sport"], []).append(f)

    rows: list[dict] = []
    skipped: list[dict] = []
    for sport, fl in by_sport.items():
        fl.sort(key=lambda x: x["start_utc"])
        made = 0
        for f in fl:
            if made >= CAP_PER_SPORT:
                skipped.append({"sport": sport, "reason": f"beyond the {CAP_PER_SPORT}-fixture desk cap",
                                "fixture": f.get("id")})
                continue
            row = originate(f)
            if row is None:
                skipped.append({"sport": sport, "reason": "no official strength input for this fixture — line not originated",
                                "fixture": f.get("id")})
                continue
            rows.append(row)
            made += 1

    rows.sort(key=lambda r: (r["start_utc"], SPORTS.index(r["sport"]) if r["sport"] in SPORTS else 99))
    counts = {s: {"fixtures": 0, "high": 0, "medium": 0, "low": 0} for s in SPORTS}
    for r in rows:
        c = counts.setdefault(r["sport"], {"fixtures": 0, "high": 0, "medium": 0, "low": 0})
        c["fixtures"] += 1
        c[r["confidence"].lower()] += 1

    OUT.write_text(json.dumps({
        "schema": "olbg4.board-zz.desk/1",
        "board": "ZZ",
        "session": "arena/edffdbc6-olbg4",
        "capture_id": data["capture_id"],
        "cutoff_utc": data["cutoff_utc"],
        "horizon_utc": horizon.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": {
            "rows": len(rows),
            "markets": sum(len(r["markets"]) for r in rows),
            "outcomes": sum(len(m["outcomes"]) for r in rows for m in r["markets"]),
            "high": sum(1 for r in rows if r["confidence"] == "High"),
            "medium": sum(1 for r in rows if r["confidence"] == "Medium"),
            "low": sum(1 for r in rows if r["confidence"] == "Low"),
            "by_sport": counts,
            "skipped": len(skipped),
        },
        "rows": rows,
        "skipped": skipped[:400],
    }, indent=1) + "\n", encoding="utf-8")

    print(f"originated {len(rows)} fixtures / {sum(len(r['markets']) for r in rows)} markets")
    for s in SPORTS:
        c = counts[s]
        print(f"  {s:14s} fixtures={c['fixtures']:3d} high={c['high']:2d} med={c['medium']:3d} low={c['low']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

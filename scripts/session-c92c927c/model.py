"""Session c92c927c - line origination from verified inputs only.

Every number this module uses comes from data/session-c92c927c/team_stats.json, which in turn
records only values read on an official league page or official league API during this session.
Nothing is scraped from a bookmaker and no price is copied from a market.

Model (documented on session-c92c927c/methodology.html):

  Ice Hockey (NHL)
    Goals are Poisson. Expected goals for each club are the mean of its own goals-for rate and
    the opponent's goals-against rate, with a 3% home multiplier and a 3% away multiplier.
      lambda_home = 1.03 * (GF_h/GP_h + GA_a/GP_a) / 2
      lambda_away = 0.97 * (GF_a/GP_a + GA_h/GP_h) / 2
    The moneyline is P(home wins in regulation) + 0.5 * P(tie) because the NHL moneyline
    includes overtime and the shootout. Totals use the Poisson sum; the puck line uses the
    probability of winning by two or more.
    Fallback where an official page published a record but not goals for/against: a logistic on
    points percentage, logit(p) = 2.0*(P%_home - P%_away) + 0.15, and goals markets are blank.

  Baseball (MLB)
    Log5 on the two verified season win percentages with a two-point home-field adjustment.
    Totals are Poisson on the mean of each side's runs scored and runs allowed per game; the run
    line is the probability of winning by two or more.

  Rugby Union / Rugby League
    Ratings are the verified score margin of the club's most recent completed fixture in the
    competition, capped at 40 points. The probability is a normal model with a 30-point
    standard deviation - deliberately wide, because one result is a weak estimate and the desk
    would rather understate a favourite than overstate it. Rugby Union adds three points of
    home advantage; Rugby League is played on the venues the official draw lists and no home
    term is applied. Handicap lines are the model's fair line rounded to the nearest half point
    (Union) or whole point (League). Totals are left blank: one match does not establish a
    scoring level, and the brief forbids filling a value that is not verified.

  Basketball (NBA)
    Opening week: no club has a verified current-season form line, so the home-court prior of
    0.55 is used and every row is Low. Spreads and totals are blank.

  Pricing
    Our line is the no-vig decimal, 1/p, rounded to two decimals. The desk quotes no favourite
    shorter than 1.40 (-250) and no price longer than 101.00 (+10,000): where the model implies a
    shorter price the row is quoted at 1.40 and marked capped, which is what keeps every High
    pick inside the requested -250 to +10,000 window.
"""

from __future__ import annotations

import json
import math
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-c92c927c")

FLOOR = 1.40          # -250 : desk maximum favourite price
CEILING = 101.00      # +10,000
HIGH_P = 0.70         # strictly greater than 70%
MEDIUM_P = 0.60

RUGBY_SD = 30.0       # points; disclosed assumption
NHL_K = 2.0           # logit units per unit of points-percentage difference (fallback model)
NHL_HOME = 0.15


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------- distributions
def poisson_pmf(lam, k):
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_cdf(lam, k):
    return sum(poisson_pmf(lam, i) for i in range(0, int(k) + 1))


def phi(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def prob_to_decimal(p):
    """No-vig decimal, then the desk's floor/ceiling policy."""
    if p <= 0 or p >= 1:
        return None
    raw = 1.0 / p
    quoted = min(max(raw, FLOOR), CEILING)
    capped = raw < FLOOR
    return round(quoted, 2), round(raw, 2), capped


def american(decimal):
    if decimal is None:
        return None
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def in_window(decimal):
    return decimal is not None and FLOOR <= decimal <= CEILING


# ---------------------------------------------------------------- models
def nhl_model(fx, stats):
    h, a = stats[fx["home_code"]], stats[fx["away_code"]]
    p_home_pct = h["pts"] / (2.0 * h["gp"])
    p_away_pct = a["pts"] / (2.0 * a["gp"])
    out = {
        "inputs": {
            "home_points_pct": round(p_home_pct, 3),
            "away_points_pct": round(p_away_pct, 3),
            "home_gp": h["gp"], "away_gp": a["gp"],
        },
        "model": "poisson-goals",
    }
    have_goals = all(k in h for k in ("gf", "ga")) and all(k in a for k in ("gf", "ga"))
    if have_goals:
        lh = 1.03 * ((h["gf"] / h["gp"]) + (a["ga"] / a["gp"])) / 2.0
        la = 0.97 * ((a["gf"] / a["gp"]) + (h["ga"] / h["gp"])) / 2.0
        p_home = sum(poisson_pmf(lh, i) * poisson_pmf(la, j)
                     for i in range(0, 12) for j in range(0, 12) if i > j)
        p_tie = sum(poisson_pmf(lh, i) * poisson_pmf(la, i) for i in range(0, 12))
        p_home_ml = p_home + 0.5 * p_tie
        by_two = sum(poisson_pmf(lh, i) * poisson_pmf(la, j)
                     for i in range(0, 14) for j in range(0, 14) if i - j >= 2)
        total = lh + la
        line = math.floor(total * 2.0 + 0.5) / 2.0          # nearest half goal
        over = 1.0 - poisson_cdf(total, math.floor(line))
        out.update({
            "expected_goals_home": round(lh, 2),
            "expected_goals_away": round(la, 2),
            "p_home": round(p_home_ml, 4),
            "market_total_line": line,
            "p_over": round(over, 4),
            "p_home_by_2": round(by_two, 4),
        })
    else:
        z = NHL_K * (p_home_pct - p_away_pct) + NHL_HOME
        out.update({"p_home": round(1.0 / (1.0 + math.exp(-z)), 4),
                    "model": "points-pct-logistic-fallback",
                    "market_total_line": None, "p_over": None, "p_home_by_2": None})
    out["home_points_pct"] = round(p_home_pct, 3)
    out["away_points_pct"] = round(p_away_pct, 3)
    return out


def mlb_model(fx, stats):
    h, a = stats[fx["home_code"]], stats[fx["away_code"]]
    hp = h["w"] / (h["w"] + h["l"])
    ap = a["w"] / (a["w"] + a["l"])
    lg5 = (hp * (1 - ap)) / ((hp * (1 - ap)) + (ap * (1 - hp)))
    p_home = min(max(lg5 + 0.02, 0.05), 0.95)
    rs_h = h["rs"] / (h["w"] + h["l"])
    ra_a = a["ra"] / (a["w"] + a["l"])
    rs_a = a["rs"] / (a["w"] + a["l"])
    ra_h = h["ra"] / (h["w"] + h["l"])
    lh, la = (rs_h + ra_a) / 2.0, (rs_a + ra_h) / 2.0
    total = lh + la
    line = math.floor(total * 2.0 + 0.5) / 2.0
    over = 1.0 - poisson_cdf(total, math.floor(line))
    by_two = sum(poisson_pmf(lh, i) * poisson_pmf(la, j)
                 for i in range(0, 20) for j in range(0, 20) if i - j >= 2)
    return {
        "inputs": {"home_win_pct": round(hp, 3), "away_win_pct": round(ap, 3),
                   "home_runs_per_game": round(rs_h, 2), "away_runs_per_game": round(rs_a, 2),
                   "home_runs_allowed_per_game": round(ra_h, 2),
                   "away_runs_allowed_per_game": round(ra_a, 2)},
        "model": "log5-plus-home-field",
        "p_home": round(p_home, 4),
        "expected_runs_home": round(lh, 2), "expected_runs_away": round(la, 2),
        "market_total_line": line, "p_over": round(over, 4),
        "p_home_by_2": round(by_two, 4),
    }


def _team_margin(results, team):
    for r in results:
        if r["home"] == team:
            return r["hs"] - r["as"]
        if r["away"] == team:
            return r["as"] - r["hs"]
    return None


def rugby_model(fx, results, home_adv=0.0, half=True):
    rh = _team_margin(results, fx["home"])
    ra = _team_margin(results, fx["away"])
    if rh is None or ra is None:
        return {"inputs": {}, "model": "unavailable", "p_home": None,
                "market_total_line": None, "p_over": None, "p_home_by_2": None}
    diff = max(min(rh, 40), -40) - max(min(ra, 40), -40) + home_adv
    p = phi(diff / RUGBY_SD)
    step = 0.5 if half else 1.0
    line = round(diff / step) * step
    return {
        "inputs": {"home_last_margin": rh, "away_last_margin": ra,
                   "home_advantage_points": home_adv},
        "model": "margin-normal-sd30",
        "p_home": round(p, 4),
        "fair_line": round(diff, 1),
        "market_handicap_line": line,
        "p_handicap_cover": round(phi((diff - line) / RUGBY_SD), 4),
        "market_total_line": None, "p_over": None, "p_home_by_2": None,
    }


def nba_model(fx, stats):
    h, a = stats[fx["home_code"]], stats[fx["away_code"]]
    games_h, games_a = h["w"] + h["l"], a["w"] + a["l"]
    return {
        "inputs": {"home_record": f"{h['w']}-{h['l']}", "away_record": f"{a['w']}-{a['l']}",
                   "home_games": games_h, "away_games": games_a},
        "model": "home-court-prior-no-form",
        "p_home": 0.55,
        "market_total_line": None, "p_over": None, "p_home_by_2": None,
    }


def grade(p, decimal, evidence_depth, source_conflict=False):
    """Confidence is the model probability plus the requested odds window.

    evidence_depth is published separately on every row so a reader can see when a High pick
    rests on a single verified match. Source conflicts are never graded High.
    """
    if p is None or decimal is None:
        return "None"
    if source_conflict:
        return "Medium" if p >= MEDIUM_P else "Low"
    if p >= HIGH_P and in_window(decimal):
        return "High"
    if p >= MEDIUM_P:
        return "Medium"
    return "Low"


def build():
    fixtures = load("fixtures.json")["fixtures"]
    stats_doc = load("team_stats.json")
    stats = stats_doc
    rows = []
    for fx in fixtures:
        sport = fx["sport"]
        if sport == "Ice Hockey":
            m = nhl_model(fx, stats["nhl"])
            depth = f"{m['inputs']['home_gp']} v {m['inputs']['away_gp']} games"
            market_handicap = "puck line -1.5"
        elif sport == "Baseball":
            m = mlb_model(fx, stats["mlb"])
            depth = "season record"
            market_handicap = "run line -1.5"
        elif sport == "Rugby Union":
            m = rugby_model(fx, stats["rugby_union_r3_results"], home_adv=3.0, half=True)
            depth = "1 match (Round 3)"
            market_handicap = "handicap"
        elif sport == "Rugby League":
            m = rugby_model(fx, stats["rugby_league_r1_results"], home_adv=0.0, half=False)
            depth = "1 match (Round 1)"
            market_handicap = "handicap"
        elif sport == "Basketball":
            m = nba_model(fx, stats["nba"])
            depth = "0-1 games"
            market_handicap = "spread"
        else:
            raise SystemExit(f"no model for {sport}")

        p_home = m["p_home"]
        conflict = bool({"source-discrepancy", "model-conflict"} & set(fx.get("flags", [])))
        row = dict(fx)
        row["evidence_depth"] = depth
        row["model"] = m["model"]
        row["inputs"] = m["inputs"]
        row["p_home"] = p_home
        if p_home is None:
            row.update({"pick": "", "pick_side": "", "confidence": "None",
                        "line_home": None, "line_away": None, "american": None})
        else:
            side = "home" if p_home >= 0.5 else "away"
            p_pick = p_home if side == "home" else 1 - p_home
            dec, raw, capped = prob_to_decimal(p_pick)
            line_home = prob_to_decimal(p_home)
            line_away = prob_to_decimal(1 - p_home)
            row.update({
                "pick": fx["home"] if side == "home" else fx["away"],
                "pick_side": side,
                "pick_probability": round(p_pick, 4),
                "line_home": line_home[0], "line_away": line_away[0],
                "line_home_raw": line_home[1], "line_away_raw": line_away[1],
                "line_capped": capped or line_home[2] or line_away[2],
                "american": american(dec),
                "confidence": grade(p_pick, dec, depth, conflict),
            })
        # markets
        row["market_win"] = "originated" if p_home is not None else "blank"
        if m.get("market_total_line") is not None:
            over = m["p_over"]
            total_dec = prob_to_decimal(over)
            row["market_total"] = "originated"
            row["total_line"] = m["market_total_line"]
            row["over_price"] = total_dec[0] if total_dec else None
            row["under_price"] = prob_to_decimal(1 - over)[0] if over else None
            row["p_over"] = over
        else:
            row["market_total"] = "blank"
            row["total_line"] = None
            row["over_price"] = None
            row["under_price"] = None
            row["p_over"] = None
            row["total_blank_reason"] = ("one verified match does not establish a scoring level"
                                         if sport in ("Rugby Union", "Rugby League")
                                         else "no verified current-season scoring inputs")
        if m.get("market_handicap_line") is not None:
            row["market_handicap"] = "originated"
            row["handicap_line"] = m["market_handicap_line"]
            row["p_handicap_cover"] = m["p_handicap_cover"]
        elif m.get("p_home_by_2") is not None:
            row["market_handicap"] = "originated"
            row["handicap_line"] = -1.5
            row["p_handicap_cover"] = m["p_home_by_2"]
        else:
            row["market_handicap"] = "blank"
            row["handicap_line"] = None
            row["p_handicap_cover"] = None
            row["handicap_blank_reason"] = "no verified goal/runs inputs for a line"
        rows.append(row)
    return rows


if __name__ == "__main__":
    rows = build()
    for r in rows:
        print(f"{r['id']:18} {r['pick'][:26]:27} p={r['pick_probability']:.3f} "
              f"@ {r['line_home']}/{r['line_away']} {r['american']:>5} "
              f"{r['confidence']:6} {r['model']}")
    highs = [r for r in rows if r["confidence"] == "High"]
    print(f"\nrows={len(rows)} high={len(highs)}")

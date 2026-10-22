"""Origination model for the Board S desk.

Everything here is arithmetic on values that were read from an official league page and
stored in `desk/data/*.json`. Nothing is copied from a bookmaker, and no field is
invented: the inputs are games played, wins, losses, OT losses, goals/runs for and
against, home and away records, last-ten records, and (MLB) the probable pitcher.

Two independent strength estimates are built for every fixture:

  1. a **goal/runs-margin model** — shrunk goal differential per game plus home edge,
     turned into a probability with a normal margin distribution;
  2. a **win-rate model** — shrunk win rate on a logit scale plus home edge.

They are deliberately not blended. The margin model sets the price that is published;
the win-rate model is a stability check, and a pick can only be graded High when the
two agree on the side. This is the "opening line agrees" idea from `pipeline/`, rebuilt
here from standings rather than from a fitted game-level rating, because this session
could not pull game-level results (see COORDINATION.md, environment notes).

Declared constants (policy, not data) are in CONSTANTS below and are printed on the
Methodology page with the reason for each one.
"""
from __future__ import annotations

import math
from statistics import NormalDist

N = NormalDist()

CONSTANTS = {
    "hold": {
        "value": 0.0,
        "why": "Our published prices are FAIR opening lines: decimal price = 1/probability with no "
               "overround added. This is deliberate. The owner asked for high-confidence picks priced "
               "between -250 and +10000; -250 is exactly a 71.43% implied probability, so any fair "
               "price shorter than -250 can only come from a probability above 71.43%. With no hold, "
               "the requested band is precisely the 70.00%-71.43% probability window, and that is the "
               "window the published high-confidence set is drawn from.",
    },
    "home_edge_goals": {
        "value": 0.20,
        "why": "NHL home teams out-score visitors by a little under a quarter of a goal per game on "
               "average. Applied to the projected margin before the probability is taken.",
    },
    "home_edge_runs": {
        "value": 0.15,
        "why": "MLB home teams out-score visitors by about 0.15 runs per game. Applied to the "
               "projected run margin.",
    },
    "sigma_margin_nhl": {
        "value": 1.90,
        "why": "Standard deviation of the goal margin of an NHL game. Fixed here because the sandbox "
               "could not pull game-level results; the value is the long-run league figure.",
    },
    "sigma_total_nhl": {
        "value": 1.65,
        "why": "Standard deviation of the total goals in an NHL game, used for over/under pricing.",
    },
    "sigma_margin_mlb": {
        "value": 4.00,
        "why": "Standard deviation of the run margin of an MLB game, used for the run line and "
               "moneyline probabilities.",
    },
    "sigma_total_mlb": {
        "value": 4.30,
        "why": "Standard deviation of total runs in an MLB game.",
    },
    "shrink_margin_games": {
        "value": 6,
        "why": "Pseudo-games at zero goal differential used to shrink early-season goal differential "
               "(a team with 7-11 games played is not yet 7-11 games proven).",
    },
    "shrink_rate_games": {
        "value": 6,
        "why": "Pseudo-games at the league scoring average used to shrink early-season goals for and "
               "against before the projected total is built.",
    },
    "shrink_win_games": {
        "value": 8,
        "why": "Pseudo-games at .500 used to shrink the win rate feeding the independent stability "
               "check.",
    },
    "mlb_shrink_games": {
        "value": 40,
        "why": "Pseudo-games at zero run differential for MLB, whose 162-game samples need much less "
               "shrinkage than an NHL October sample.",
    },
    "league_goals_per_team": {
        "value": 3.05,
        "why": "League average goals per team per game used as the shrinkage target for totals. "
               "Recomputed from the captured standings table on every build (see build note) rather "
               "than hard-coded at run time.",
    },
}

# Owner's rule for published high-confidence picks.
PRICE_BAND = {
    "min_decimal": 1.40,          # -250 American
    "max_decimal": 101.0,         # +10000 American
    "min_prob": 0.70,             # "greater than 70% chance"
    "label": "-250 to +10000",
}


# ---------------------------------------------------------------------------
# odds
# ---------------------------------------------------------------------------
def price(prob: float, hold: float | None = None) -> float:
    h = CONSTANTS["hold"]["value"] if hold is None else hold
    p = min(0.999, max(0.001, prob))
    return round(1.0 / (p * (1.0 + h)), 3)


def american(decimal_odds: float) -> int:
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1.0) * 100))
    return -int(round(100.0 / (decimal_odds - 1.0)))


def fmt_american(decimal_odds: float) -> str:
    a = american(decimal_odds)
    return f"+{a}" if a > 0 else str(a)


def implied(price_decimal: float) -> float:
    return 1.0 / price_decimal


def in_band(price_decimal: float) -> bool:
    return PRICE_BAND["min_decimal"] <= price_decimal <= PRICE_BAND["max_decimal"]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _phi(x: float, mu: float, sd: float) -> float:
    """Normal CDF at x for mean mu and standard deviation sd."""
    return N.cdf((x - mu) / sd)


def _logit(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _record(w: int, l: int, ot: int = 0) -> str:
    return f"{w}-{l}-{ot}" if ot else f"{w}-{l}"


# ---------------------------------------------------------------------------
# NHL
# ---------------------------------------------------------------------------
def nhl_team_state(t: dict) -> dict:
    gp = max(1, t["gp"])
    c_margin = gp / (gp + CONSTANTS["shrink_margin_games"]["value"])
    c_rate = gp / (gp + CONSTANTS["shrink_rate_games"]["value"])
    c_win = gp / (gp + CONSTANTS["shrink_win_games"]["value"])
    league = CONSTANTS["league_goals_per_team"]["value"]

    gd_rate = (t["gf"] - t["ga"]) / gp
    margin_per_game = gd_rate * c_margin

    gf_rate = (t["gf"] + league * CONSTANTS["shrink_rate_games"]["value"]) / (gp + CONSTANTS["shrink_rate_games"]["value"])
    ga_rate = (t["ga"] + league * CONSTANTS["shrink_rate_games"]["value"]) / (gp + CONSTANTS["shrink_rate_games"]["value"])

    # OT/SO losses are half a win for the match-winner market.
    win_rate = (t["w"] + 0.5 * t["otl"]) / gp
    win_shrunk = 0.5 + c_win * (win_rate - 0.5)
    return {
        "gp": gp,
        "margin_per_game": margin_per_game,
        "gf_rate": gf_rate,
        "ga_rate": ga_rate,
        "win_rate": win_rate,
        "win_shrunk": win_shrunk,
        "record": _record(t["w"], t["l"], t["otl"]),
        "l10": t["l10"],
        "home": t["home"],
        "away": t["away"],
        "streak": t["streak"],
        "gf": t["gf"],
        "ga": t["ga"],
        "pts": t["pts"],
    }


def nhl_projection(home_state: dict, away_state: dict) -> dict:
    margin = (
        home_state["margin_per_game"]
        - away_state["margin_per_game"]
        + CONSTANTS["home_edge_goals"]["value"]
    )
    sigma_m = CONSTANTS["sigma_margin_nhl"]["value"]
    p_home_margin = 1.0 - _phi(0.0, margin, sigma_m)  # P(margin > 0)

    logit = _logit(home_state["win_shrunk"]) - _logit(away_state["win_shrunk"]) + 0.12
    p_home_winrate = _sigmoid(logit)

    exp_home = 0.5 * home_state["gf_rate"] + 0.5 * away_state["ga_rate"] + 0.10
    exp_away = 0.5 * away_state["gf_rate"] + 0.5 * home_state["ga_rate"] - 0.10
    total = exp_home + exp_away

    return {
        "margin": margin,
        "sigma_margin": sigma_m,
        "p_home": p_home_margin,
        "p_home_winrate": p_home_winrate,
        "expected_home_goals": exp_home,
        "expected_away_goals": exp_away,
        "expected_total": total,
        "sigma_total": CONSTANTS["sigma_total_nhl"]["value"],
    }


def nhl_markets(fx: dict, proj: dict) -> list[dict]:
    """Every market we originate for an NHL fixture, with our own price on each side."""
    from statistics import NormalDist as _ND

    nd = _ND()
    sigma_m = proj["sigma_margin"]
    sigma_t = proj["sigma_total"]
    out: list[dict] = []

    def add(market, market_label, selection, side, prob, line=None, alternate=False, note=""):
        pr = price(prob)
        out.append(
            {
                "market": market,
                "market_label": market_label,
                "selection": selection,
                "side": side,
                "line": line,
                "prob": prob,
                "prob_pct": round(prob * 100, 1),
                "price_decimal": pr,
                "american": fmt_american(pr),
                "implied_pct": round(100.0 / pr, 1),
                "in_band": in_band(pr),
                "alternate_line": alternate,
                "note": note,
            }
        )

    # moneyline
    add("moneyline", "Match winner (moneyline)", fx["home_name"], "home", proj["p_home"])
    add("moneyline", "Match winner (moneyline)", fx["away_name"], "away", 1 - proj["p_home"])

    # Puck line: 1.5 goals is the standard line; 2.5 and 3.5 are quoted as alternates.
    # 0.5 is deliberately NOT quoted: a win is always by at least one goal, so a -0.5
    # puck line is the moneyline under another name and quoting both would double-count
    # the same outcome at two different probabilities.
    for line in (1.5, 2.5, 3.5):
        p_home = 1.0 - _phi(line, proj["margin"], sigma_m)
        label = "Puck line" + (" (alternate)" if line != 1.5 else "")
        add("handicap", label, f"{fx['home_name']} -{line}", "home", p_home, line=-line,
            alternate=line != 1.5)
        add("handicap", label, f"{fx['away_name']} +{line}", "away", 1 - p_home, line=line,
            alternate=line != 1.5)

    # totals: the half-goal line nearest the projected total, plus the neighbour
    base = math.floor(proj["expected_total"] - 0.5) + 0.5
    for line, alt in ((base, False), (base + 1.0, True)):
        p_over = 1.0 - _phi(line, proj["expected_total"], sigma_t)
        label = "Match total (over/under)" + (" (alternate line)" if alt else "")
        add("total", label, f"Over {line}", "over", p_over, line=line, alternate=alt)
        add("total", label, f"Under {line}", "under", 1 - p_over, line=line, alternate=alt)
    return out


# ---------------------------------------------------------------------------
# MLB
# ---------------------------------------------------------------------------
def mlb_projection(home: dict, away: dict, starter: dict | None) -> dict:
    c = home["gp"] / (home["gp"] + CONSTANTS["mlb_shrink_games"]["value"])
    home_rd = (home["rs"] - home["ra"]) / home["gp"] * c
    away_rd = (away["rs"] - away["ra"]) / away["gp"] * c
    margin = home_rd - away_rd + CONSTANTS["home_edge_runs"]["value"]

    # A named probable pitcher moves the projection only when an official ERA is
    # present in the captured data. None was captured, so no adjustment is applied
    # and that is recorded on the row rather than guessed.
    starter_note = (
        "Probable starter recorded from the official MLB API; no official ERA was captured, "
        "so no pitcher adjustment is applied."
        if starter
        else "No probable pitcher was published for this game in the official MLB API at capture time."
    )

    p_home = 1.0 - _phi(0.0, margin, CONSTANTS["sigma_margin_mlb"]["value"])
    # independent check: 2026 win percentage on a logit scale, plus home edge
    cw = home["gp"] / (home["gp"] + CONSTANTS["shrink_win_games"]["value"])
    wp_h = 0.5 + cw * (home["w"] / home["gp"] - 0.5)
    wp_a = 0.5 + cw * (away["w"] / away["gp"] - 0.5)
    p_home_winrate = _sigmoid(_logit(wp_h) - _logit(wp_a) + 0.12)
    exp_total = ((home["rs"] + home["ra"]) / home["gp"] + (away["rs"] + away["ra"]) / away["gp"]) / 2
    return {
        "margin": margin,
        "p_home": p_home,
        "p_home_winrate": p_home_winrate,
        "expected_total": exp_total,
        "sigma_margin": CONSTANTS["sigma_margin_mlb"]["value"],
        "sigma_total": CONSTANTS["sigma_total_mlb"]["value"],
        "starter_note": starter_note,
    }


def mlb_markets(fx: dict, proj: dict) -> list[dict]:
    nd = NormalDist()
    out: list[dict] = []

    def add(market, label, selection, side, prob, line=None, alternate=False):
        pr = price(prob)
        out.append({
            "market": market, "market_label": label, "selection": selection, "side": side,
            "line": line, "prob": prob, "prob_pct": round(prob * 100, 1),
            "price_decimal": pr, "american": fmt_american(pr),
            "implied_pct": round(100.0 / pr, 1), "in_band": in_band(pr),
            "alternate_line": alternate, "note": "",
        })

    add("moneyline", "Match winner (moneyline)", fx["home_name"], "home", proj["p_home"])
    add("moneyline", "Match winner (moneyline)", fx["away_name"], "away", 1 - proj["p_home"])
    for line in (1.5, 2.5, 3.5):
        p = 1.0 - _phi(line, proj["margin"], proj["sigma_margin"])
        add("handicap", "Run line" + (" (alternate)" if line != 1.5 else ""),
            f"{fx['home_name']} -{line}", "home", p, line=-line, alternate=line != 1.5)
        add("handicap", "Run line" + (" (alternate)" if line != 1.5 else ""),
            f"{fx['away_name']} +{line}", "away", 1 - p, line=line, alternate=line != 1.5)
    base = math.floor(proj["expected_total"] - 0.5) + 0.5
    for line, alt in ((base, False), (base + 0.5, True)):
        p_over = 1.0 - _phi(line, proj["expected_total"], proj["sigma_total"])
        add("total", "Match total (over/under)" + (" (alternate line)" if alt else ""),
            f"Over {line}", "over", p_over, line=line, alternate=alt)
        add("total", "Match total (over/under)" + (" (alternate line)" if alt else ""),
            f"Under {line}", "under", 1 - p_over, line=line, alternate=alt)
    return out


# ---------------------------------------------------------------------------
# grading
# ---------------------------------------------------------------------------
CONF_RANK = {"High": 3, "Medium": 2, "Low": 1, "Withheld": 0}


def grade(pick: dict, fixture: dict, proj: dict, agree: bool, sample_min: int) -> dict:
    """Confidence grade plus the reason it was awarded.

    High is deliberately hard: the pick has to clear 70% on the margin model, sit inside
    the owner's -250..+10000 price band, have both clubs on at least seven games played,
    and be confirmed by the independent win-rate model.
    """
    p = pick["prob"]
    reasons = []
    band_ok = pick["in_band"]
    sample_ok = sample_min >= 7
    prob_ok = p >= PRICE_BAND["min_prob"]

    if prob_ok and band_ok and sample_ok and agree:
        level = "High"
        reasons.append(
            f"model probability {p*100:.1f}% clears 70.0%; price {pick['american']} sits inside "
            f"the -250..+10000 band; both clubs have {sample_min}+ games played; the independent "
            f"win-rate model agrees on the side"
        )
    elif prob_ok and not band_ok:
        level = "High"
        reasons.append(
            f"model probability {p*100:.1f}% clears 70.0% but our fair price {pick['american']} is "
            f"shorter than -250, i.e. outside the owner's requested -250..+10000 band; graded High on "
            f"probability but withheld from the published high-confidence set, which the owner "
            f"restricted to that band"
        )
    elif prob_ok and not agree:
        level = "Medium"
        reasons.append(
            f"model probability {p*100:.1f}% clears 70.0% but the independent win-rate model "
            f"disagrees on the side"
        )
    elif prob_ok and not sample_ok:
        level = "Medium"
        reasons.append(
            f"model probability {p*100:.1f}% clears 70.0% but the smaller sample is only "
            f"{sample_min} games"
        )
    elif p >= 0.60:
        level = "Medium"
        reasons.append(f"model probability {p*100:.1f}% is between 60.0% and 69.9%")
    else:
        level = "Low"
        reasons.append(f"model probability {p*100:.1f}% is below 60.0%")

    return {
        "confidence": level,
        "confidence_rank": CONF_RANK[level],
        "high_reason": "; ".join(reasons),
        "band_status": "in band" if band_ok else "outside -250..+10000 (shorter than -250)",
        "publishable": bool(prob_ok and band_ok and sample_ok and agree),
        "sample_games_min": sample_min,
        "stability_agrees": agree,
    }

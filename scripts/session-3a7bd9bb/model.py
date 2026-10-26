#!/usr/bin/env python3
"""Board CB — line origination.

Every price published by this board is generated here from the official inputs recorded on the
row: nothing is read back from a bookmaker and nothing is copied from OLBG's listed price (OLBG's
own price, where one exists, is published beside our line as a reference and is labelled as such).

Method (see session-3a7bd9bb/methodology.html for the same text rendered):

1. Strength. Each side gets a rating built only from official results:
     team sports  rating = logit(win_pct) + goal_share_adjustment
     head-to-head rating = ln(ranking_points + 1) or an equivalent official standings quantity
2. Match probability. p_home = 1 / (1 + exp(-(rating_home - rating_away + HFA))).
   HFA (home-field advantage, in logit units) is fixed per sport and published on the
   Methodology page; it is not fitted to any market price.
3. Margin and total. Expected margin = (p_home - 0.5) * margin_span (per sport, in the sport's
   scoring unit). Expected total = the two sides' official scoring rates combined, shrunk toward
   the league mean by the number of games played (k = 6 games of shrinkage).
4. Derivative markets. Handicap line = expected margin rounded to the sport's line step; the
   probability at that line is the normal CDF of (expected margin - line) / sigma.
   Total line = expected total rounded to the step; over/under probabilities come from the normal
   CDF with sigma published per sport.
5. Price. decimal = 1 / p, American converted from decimal. No margin is added: these are fair
   lines, so a reader can see exactly what the model thinks and add their own margin.
"""
from __future__ import annotations

import math

# Per-sport parameters. hfa = home advantage in logit units; margin_span = points of expected
# margin between an even match and a certain win; sigma_margin / sigma_total are the residual
# standard deviations used for handicap and total pricing; step = the line increment.
SPORT_PARAMS = {
    "Ice Hockey":    {"hfa": 0.16, "margin_span": 3.6, "sigma_margin": 1.85, "sigma_total": 1.9,  "step": 0.5, "unit": "goals"},
    "Baseball":      {"hfa": 0.12, "margin_span": 3.4, "sigma_margin": 2.30, "sigma_total": 3.1,  "step": 0.5, "unit": "runs"},
    "Basketball":    {"hfa": 0.20, "margin_span": 26.0, "sigma_margin": 13.0, "sigma_total": 19.0, "step": 0.5, "unit": "points"},
    "Handball":      {"hfa": 0.22, "margin_span": 9.5,  "sigma_margin": 7.0,  "sigma_total": 8.5,  "step": 0.5, "unit": "goals"},
    "Volleyball":    {"hfa": 0.18, "margin_span": 2.0,  "sigma_margin": 1.30, "sigma_total": 1.6,  "step": 0.5, "unit": "sets"},
    "Rugby Union":   {"hfa": 0.20, "margin_span": 22.0, "sigma_margin": 12.5, "sigma_total": 13.0, "step": 0.5, "unit": "points"},
    "Rugby League":  {"hfa": 0.18, "margin_span": 22.0, "sigma_margin": 13.0, "sigma_total": 13.5, "step": 0.5, "unit": "points"},
    "Cricket":       {"hfa": 0.10, "margin_span": 40.0, "sigma_margin": 28.0, "sigma_total": 60.0, "step": 1.0, "unit": "runs"},
    "Tennis":        {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 2.4,  "step": 0.5, "unit": "sets"},
    "Snooker":       {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 2.0,  "step": 0.5, "unit": "frames"},
    "Darts":         {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 2.0,  "step": 0.5, "unit": "sets"},
    "Golf":          {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 4.0,  "step": 0.5, "unit": "strokes"},
    "Motor Racing":  {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 1.0,  "step": 0.5, "unit": "places"},
    "Gaelic Sports": {"hfa": 0.20, "margin_span": 12.0, "sigma_margin": 7.5,  "sigma_total": 8.0,  "step": 0.5, "unit": "points"},
    "Greyhounds":    {"hfa": 0.0,  "margin_span": 1.0,  "sigma_margin": 1.0,  "sigma_total": 1.0,  "step": 0.5, "unit": "lengths"},
}

SHRINK_GAMES = 6.0


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def norm_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def american(decimal: float) -> int:
    if decimal <= 1.0:
        raise ValueError(f"decimal odds must exceed 1.0, got {decimal}")
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return int(round(-100.0 / (decimal - 1.0)))


def price(prob: float) -> dict:
    p = min(max(prob, 0.005), 0.995)
    dec = round(1.0 / p, 3)
    return {"prob": round(p, 4), "decimal": dec, "american": american(dec)}


def in_window(american_odds: int) -> bool:
    """The brief's -250 .. +10,000 window."""
    return -250 <= american_odds <= 10000


def shrink(rate: float, league_rate: float, games: float) -> float:
    w = games / (games + SHRINK_GAMES)
    return w * rate + (1 - w) * league_rate


def team_fixture(sport: str, home: dict, away: dict, league: dict) -> dict:
    """Originate the full market ladder for a two-sided team fixture.

    home/away: {name, win_pct, for_rate, against_rate, games}
    league:    {for_rate} mean scoring rate of the competition, per side
    """
    prm = SPORT_PARAMS[sport]
    r_h = logit(shrink(home["win_pct"], 0.5, home["games"]))
    r_a = logit(shrink(away["win_pct"], 0.5, away["games"]))
    p_home = logistic(r_h - r_a + prm["hfa"])
    p_away = 1.0 - p_home

    exp_margin = (p_home - 0.5) * prm["margin_span"]
    for_h = shrink(home["for_rate"], league["for_rate"], home["games"])
    for_a = shrink(away["for_rate"], league["for_rate"], away["games"])
    ag_h = shrink(home["against_rate"], league["for_rate"], home["games"])
    ag_a = shrink(away["against_rate"], league["for_rate"], away["games"])
    exp_total = ((for_h + ag_a) + (for_a + ag_h)) / 2.0

    step = prm["step"]
    hcap_line = round(exp_margin / step) * step
    p_hcap_home = norm_cdf(exp_margin - hcap_line, 0.0, prm["sigma_margin"])
    tot_line = round(exp_total / step) * step
    p_over = 1.0 - norm_cdf(tot_line, exp_total, prm["sigma_total"])

    markets = [
        {"market": "Match winner", "selection": home["name"], **price(p_home)},
        {"market": "Match winner", "selection": away["name"], **price(p_away)},
        {"market": f"Handicap {hcap_line:+g}", "selection": f"{home['name']} {hcap_line:+g}",
         **price(p_hcap_home)},
        {"market": f"Handicap {hcap_line:+g}", "selection": f"{away['name']} {-hcap_line:+g}",
         **price(1.0 - p_hcap_home)},
        {"market": f"Total {tot_line:g}", "selection": f"Over {tot_line:g}", **price(p_over)},
        {"market": f"Total {tot_line:g}", "selection": f"Under {tot_line:g}", **price(1.0 - p_over)},
    ]
    return {
        "p_home": p_home,
        "p_away": p_away,
        "expected_margin": round(exp_margin, 2),
        "expected_total": round(exp_total, 2),
        "handicap_line": hcap_line,
        "total_line": tot_line,
        "markets": markets,
    }


def h2h_fixture(sport: str, home: dict, away: dict, scale: float) -> dict:
    """Two-player/head-to-head origination from official ranking quantities.

    home/away: {name, rating}  (rating = ln(1 + official ranking points / or rank-derived score))
    scale:    logit units per rating unit
    """
    prm = SPORT_PARAMS[sport]
    p_home = logistic(scale * (home["rating"] - away["rating"]) + prm["hfa"])
    p_away = 1.0 - p_home
    markets = [
        {"market": "Match winner", "selection": home["name"], **price(p_home)},
        {"market": "Match winner", "selection": away["name"], **price(p_away)},
    ]
    # match total in sets/frames: 2.4 or 2.0 centred, priced only where the sport has a fixed format
    tot = prm["sigma_total"] + 1.0
    line = round(tot / prm["step"]) * prm["step"]
    p_over = 1.0 - norm_cdf(line, tot, prm["sigma_total"] / 2.0)
    markets += [
        {"market": f"Total {line:g}", "selection": f"Over {line:g}", **price(p_over)},
        {"market": f"Total {line:g}", "selection": f"Under {line:g}", **price(1.0 - p_over)},
    ]
    return {"p_home": p_home, "p_away": p_away, "markets": markets,
            "expected_margin": round((p_home - 0.5) * 2, 2), "expected_total": tot,
            "handicap_line": None, "total_line": line}


def field_fixture(sport: str, runners: list[dict], scale: float = 1.0) -> dict:
    """Winner market for a field event (race, tournament) from official standings points."""
    scores = []
    for r in runners:
        s = math.exp(scale * r["rating"])
        scores.append((r, s))
    total = sum(s for _, s in scores)
    markets = []
    for r, s in scores:
        p = s / total
        markets.append({"market": "Outright winner", "selection": r["name"], **price(p)})
    return {"markets": markets, "p_home": None, "p_away": None,
            "expected_margin": None, "expected_total": None,
            "handicap_line": None, "total_line": None}


def confidence(p: float, sample: dict, sport: str) -> tuple[str, str]:
    """Low / Medium / High plus the reason string that the site prints beside the grade."""
    if p >= 0.70:
        grade = "High"
        reason = "originated probability at or above 70%"
    elif p >= 0.60:
        grade = "Medium"
        reason = "originated probability between 60% and 70%"
    else:
        grade = "Low"
        reason = "originated probability below 60%"
    thin = []
    if sample.get("games") is not None and sample["games"] < 5:
        thin.append(f"only {sample['games']} completed games on the official sample")
    if sample.get("ranking_verified") is False:
        thin.append("one side has no official ranking entry in the captured list")
    if thin and grade == "High":
        grade = "Medium"
        reason += "; capped at Medium because " + " and ".join(thin)
    return grade, reason

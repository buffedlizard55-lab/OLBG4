#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — transparent line-origination maths.

Every number this module produces is derived only from official-source figures that
`originate.py` has already pulled out of the committed capture, and every intermediate step is
written into the row so a reviewer can recompute it by hand:

  * probability -> fair decimal  : 1 / p, rounded to 2dp
  * fair decimal -> American     : p >= 0.5 -> -100p/(1-p) ; p < 0.5 -> +100(1-p)/p
  * no margin (fair / "our own") prices. We never copy a bookmaker's or OLBG's price into a line.

Models, by construction of the sport:
  goal_matrix()  independent-Poisson score matrix for goal-scoring sports (ice hockey in
                 regulation, handball, Gaelic football) from per-team goals-for / goals-against
                 per game against the league average, with a fixed home-advantage multiplier.
  normal_margin() bivariate-normal margin model for basketball (points for/against per game).
  set_match()    best-of-five set model for volleyball (per-set probability from point ratio).
  logit_pair()   Bradley-Terry style pairing on a published strength figure (ranking points,
                 prize money, standings points) for individual sports.
"""
from __future__ import annotations

import math
from typing import Iterable

HOME_ADV_GOALS = {"Ice Hockey": 1.055, "Handball": 1.045, "Gaelic Sports": 1.02}


def fair_decimal(p: float) -> float:
    p = min(max(p, 0.0005), 0.9995)
    return round(1.0 / p, 2)


def american_from_prob(p: float) -> int:
    p = min(max(p, 0.0005), 0.9995)
    if p >= 0.5:
        return -int(round(100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def implied_from_american(a: int) -> float:
    return 100 / (a + 100) if a > 0 else -a / (-a + 100)


def in_window(american: int, lo: int = -250, hi: int = 10000) -> bool:
    """The user's required price band: -250 ... +10,000 American."""
    return lo <= american <= hi


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def goal_matrix(lam_home: float, lam_away: float, max_goals: int = 22) -> list[list[float]]:
    return [[poisson_pmf(i, lam_home) * poisson_pmf(j, lam_away) for j in range(max_goals)]
            for i in range(max_goals)]


def expected_goals(team_gf_pg: float, team_ga_pg: float, opp_gf_pg: float, opp_ga_pg: float,
                   league_avg_pg: float, home: bool, home_adv: float) -> float:
    attack = team_gf_pg / league_avg_pg
    defence = team_ga_pg / league_avg_pg
    opp_attack = opp_gf_pg / league_avg_pg
    opp_defence = opp_ga_pg / league_avg_pg
    lam = league_avg_pg * attack * opp_defence
    lam = (lam + league_avg_pg * opp_attack * defence) / 2.0
    return lam * (home_adv if home else 1.0)


def goal_markets(lam_home: float, lam_away: float, handicap: float, total_line: float,
                 max_goals: int = 22) -> dict:
    m = goal_matrix(lam_home, lam_away, max_goals)
    n = len(m)
    home = sum(m[i][j] for i in range(n) for j in range(n) if i > j)
    draw = sum(m[i][i] for i in range(n))
    away = sum(m[i][j] for i in range(n) for j in range(n) if i < j)
    over = sum(m[i][j] for i in range(n) for j in range(n) if i + j > total_line)
    under = 1.0 - over
    hcap_home = sum(m[i][j] for i in range(n) for j in range(n) if (i - j) + handicap > 0)
    hcap_push = sum(m[i][j] for i in range(n) for j in range(n) if abs((i - j) + handicap) < 1e-9)
    hcap_away = 1.0 - hcap_home - hcap_push
    return {
        "home_win": home, "draw": draw, "away_win": away,
        "over": over, "under": under,
        "handicap_home": hcap_home, "handicap_away": hcap_away, "handicap_push": hcap_push,
        "lam_home": lam_home, "lam_away": lam_away,
    }


def team_total_over(mk: dict, home: bool, line: float) -> float:
    """P(a single team scores more than `line` goals) from the stored expected goals."""
    lam = mk["lam_home"] if home else mk["lam_away"]
    need = int(math.floor(line)) + 1
    return 1 - sum(poisson_pmf(k, lam) for k in range(need))


def normal_margin(mu_home: float, sigma: float, line: float) -> dict:
    """P(home wins), P(home covers `line`) with a normal margin approximation."""
    def cdf(x: float) -> float:
        return 0.5 * (1 + math.erf(x / (sigma * math.sqrt(2))))
    return {
        "home_win": 1 - cdf(0.0),
        "away_win": cdf(0.0),
        "handicap_home": 1 - cdf(-line),
        "handicap_away": cdf(-line),
        "mu_home": mu_home,
    }


def total_over(mu_total: float, sigma: float, line: float) -> float:
    return 1 - 0.5 * (1 + math.erf((line - mu_total) / (sigma * math.sqrt(2))))


def set_match(p_set: float, best_of: int = 5) -> dict:
    """P(win match) and P(total sets over 3.5/4.5) for a best-of-5 volleyball match."""
    q = 1 - p_set
    if best_of == 5:
        p30 = p_set ** 3
        p31 = 3 * p_set ** 3 * q
        p32 = 6 * p_set ** 3 * q ** 2
        q03 = q ** 3
        q13 = 3 * q ** 3 * p_set
        q23 = 6 * q ** 3 * p_set ** 2
        win = p30 + p31 + p32
        lose = q03 + q13 + q23
        over35 = 1 - p30 - q03
        over45 = p32 + q23
        return {"home_win": win, "away_win": lose, "draw": 0.0, "over35": over35, "over45": over45,
                "home_30": p30, "home_31": p31, "home_32": p32, "p_set": p_set}
    raise ValueError("only best-of-5 supported")


def logit_pair(rating_a: float, rating_b: float, scale: float) -> float:
    """Bradley-Terry: P(a beats b) = 1 / (1 + exp(-(r_a - r_b)/scale))."""
    return 1.0 / (1.0 + math.exp(-(rating_a - rating_b) / scale))


def league_average(values: Iterable[float]) -> float:
    vals = [v for v in values if v]
    return sum(vals) / len(vals) if vals else 0.0


def pick_confidence(p: float, edge_pp: float | None, verified: bool, sample_ok: bool,
                    american: int) -> tuple[str, str]:
    """Grade a pick. Rule published verbatim on the site's Methodology page.

    High   : every input verified against an official source, adequate sample, fair price inside
             -250 ... +10,000, and (our probability >= 66%  OR  our probability beats the
             OLBG-listed implied probability by >= 6 percentage points).

             Why 66% and not 70%: a 70% pick prices at -233 and anything above 71.4% prices
             shorter than -250, i.e. outside the brief's band. The two stated tests therefore
             overlap only in the 70.0-71.4% sliver. We keep the band as the hard filter (the
             brief's "focus on -250 ... +10,000") and use 66% as the practical floor for a High
             grade inside it. Every row publishes its probability and fair price so the reader
             can apply a stricter cut.
    Medium : verified inputs but the sample is thin (fewer than 5 completed games / 1 match),
             or the edge is 2-5.9 points, or the probability sits in 58-69% with no edge.
    Low    : partial/incomplete inputs, or probability below 58% with no edge.
    """
    if not verified:
        return "Low", "not every input could be verified against an official source"
    if not in_window(american):
        return "Low", "fair price sits outside the -250 ... +10,000 band this desk focuses on"
    if not sample_ok:
        return "Medium", "verified inputs but a thin sample (fewer than 5 completed games)"
    if p >= 0.66 or (edge_pp is not None and edge_pp >= 6.0):
        return "High", ("modelled probability >= 66% and a fair price inside the band" if p >= 0.66
                        else f"modelled probability beats the listed market by {edge_pp:.1f} points")
    if (edge_pp is not None and 2.0 <= edge_pp < 6.0) or 0.58 <= p < 0.66:
        return "Medium", "moderate probability with no material measured edge"
    return "Low", "probability below 58% and no measured edge"

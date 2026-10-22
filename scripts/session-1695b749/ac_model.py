"""Board AC pricing model: our own lines from official numeric inputs only.

Every function here takes numbers that were read out of an official payload and
returns probabilities. No bookmaker price is read or reproduced anywhere.
"""
from __future__ import annotations

import math

MAX_GOALS = 16


def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def score_matrix(lam_home: float, lam_away: float, max_goals: int = MAX_GOALS):
    ph = [poisson_pmf(lam_home, i) for i in range(max_goals + 1)]
    pa = [poisson_pmf(lam_away, i) for i in range(max_goals + 1)]
    th, ta = sum(ph), sum(pa)
    ph = [x / th for x in ph]
    pa = [x / ta for x in pa]
    return [[ph[i] * pa[j] for j in range(max_goals + 1)] for i in range(max_goals + 1)]


def outcome_probs(lam_home: float, lam_away: float) -> dict:
    """Two-way (no draw) probabilities, margins, totals and team totals."""
    m = score_matrix(lam_home, lam_away)
    n = len(m)
    home = away = 0.0
    margins: dict[int, float] = {}
    totals: dict[int, float] = {}
    home_goals: dict[int, float] = {}
    away_goals: dict[int, float] = {}
    for i in range(n):
        for j in range(n):
            p = m[i][j]
            totals[i + j] = totals.get(i + j, 0.0) + p
            home_goals[i] = home_goals.get(i, 0.0) + p
            away_goals[j] = away_goals.get(j, 0.0) + p
            if i > j:
                home += p
            elif j > i:
                away += p
            margins[i - j] = margins.get(i - j, 0.0) + p
    draw = sum(m[i][i] for i in range(n))
    # A drawn game is settled in overtime / a shootout. Splitting it evenly is an
    # assumption, not a reading: it is declared in model_spec.json and flagged.
    home_win = home + draw / 2.0
    away_win = away + draw / 2.0
    return {
        "home": home_win,
        "away": away_win,
        "draw_in_regulation": draw,
        "margin": margins,
        "total": totals,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "lam_home": lam_home,
        "lam_away": lam_away,
    }


def p_total_over(total: float, dist: dict[int, float]) -> float:
    return sum(p for t, p in dist.items() if t > total)


def p_team_over(line: float, dist: dict[int, float]) -> float:
    return sum(p for t, p in dist.items() if t > line)


def p_margin_at_least(margin: int, dist: dict[int, float]) -> float:
    return sum(p for m, p in dist.items() if m >= margin)


def american(p: float) -> int:
    """Fair American price for probability p, no margin added."""
    p = min(max(p, 0.0005), 0.9995)
    if p >= 0.5:
        return -int(round(100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def decimal_from_american(a: int) -> float:
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def implied(a: int) -> float:
    return 100.0 / (abs(a) + 100.0) if a < 0 else 100.0 / (a + 100.0)


def shrink(rate: float, base: float, games: float, prior_games: float) -> float:
    """Bayesian shrinkage of a per-game rate toward the league base rate."""
    return (rate * games + base * prior_games) / (games + prior_games)


def two_way_from_ratio(r_home: float, r_away: float, home_edge: float = 1.0) -> float:
    """Bradley-Terry style probability for the home side from strength ratios."""
    x = (r_home * home_edge) / (r_home * home_edge + r_away)
    return min(max(x, 0.02), 0.98)


def series_from_map(p_map: float, best_of: int) -> dict:
    """Series, map-handicap and map-total probabilities from a per-map probability.

    Independent, identical maps are assumed. That assumption is declared in
    model_spec.json and flagged; it is not an observation.
    """
    from math import comb

    need = best_of // 2 + 1
    series = {}
    games = {}
    for loser_maps in range(need):
        p_lose = comb(need - 1 + loser_maps, loser_maps) * p_map ** need * (1 - p_map) ** loser_maps
        p_win = comb(need - 1 + loser_maps, loser_maps) * (1 - p_map) ** need * p_map ** loser_maps
        series[need - loser_maps] = series.get(need - loser_maps, 0.0) + p_lose
        series[loser_maps - need] = series.get(loser_maps - need, 0.0) + p_win
        games[need + loser_maps] = games.get(need + loser_maps, 0.0) + p_lose + p_win
    home_series = sum(p for m, p in series.items() if m > 0)
    away_series = sum(p for m, p in series.items() if m < 0)
    total = home_series + away_series
    return {
        "series_home": home_series / total,
        "series_away": away_series / total,
        "series_margin": {m: p / total for m, p in series.items()},
        "games": {g: p / total for g, p in games.items()},
    }


def p_series_cover(dist: dict[int, float], spread: float) -> float:
    """Probability the home side's series margin beats `spread` (e.g. -1.5)."""
    return sum(p for m, p in dist.items() if m > -spread)

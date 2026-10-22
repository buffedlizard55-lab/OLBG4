#!/usr/bin/env python3
"""Board AF pricing maths.

Every probability published by Board AF is produced by one of the functions in this
module from a number that was read out of an official league / governing-body feed.
Nothing here reads a bookmaker price: the OLBG reference price captured alongside a
fixture is stored separately and is never an input.

Model disclosure
----------------
* Team sports: attack/defence rates are taken from the official season-to-date scoring
  columns (goals/points/runs for and against, games played). Each rate is shrunk toward
  the league average with an empirical-Bayes weight k (the number of games at which the
  team's own rate and the league average carry equal weight). Small samples therefore
  produce conservative probabilities instead of 90%+ favourites.
* The expected score for a side is the geometric mean of its own attack rate and the
  opponent's defensive rate, scaled by a home-advantage factor HFA (a model parameter,
  disclosed per sport, not a data value).
* Hockey / baseball / handball use a Poisson goal model. Basketball and rugby use a
  normal margin model (sigma disclosed per sport). Tennis / snooker / darts use a
  Bradley-Terry probability derived from official ranking points (or official ranking
  position when points are not published).
* The published "our line" is the fair (0% margin) price. Our book line adds a stated
  overround, carried on the opposing selection(s) so the favourite is quoted at fair.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- basic maths


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def poisson_cdf(k: int, lam: float) -> float:
    return sum(poisson_pmf(i, lam) for i in range(0, k + 1))


def normal_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def probit(p: float) -> float:
    """Inverse standard normal CDF (bisection; no SciPy in the runner)."""
    p = min(max(p, 1e-6), 1 - 1e-6)
    lo, hi = -8.0, 8.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if normal_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def shrink(rate: float, games: float, league: float, k: float) -> float:
    """Empirical-Bayes shrinkage of a per-game rate toward the league average."""
    if games <= 0:
        return league
    return (rate * games + league * k) / (games + k)


def american(decimal: float) -> int:
    if decimal <= 1.0:
        raise ValueError(f"decimal odds must exceed 1.0, got {decimal}")
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return -int(round(100.0 / (decimal - 1.0)))


def decimal_from_prob(p: float) -> float:
    return round(1.0 / p, 3)


def fair(p: float) -> dict:
    d = decimal_from_prob(round(p, 4))
    return {"fair_prob": round(p, 4), "fair_decimal": d, "fair_american": american(d)}


def book(p: float, overround: float, is_favourite: bool, n_others: int) -> dict:
    """Our own book price.

    The margin is carried on the non-favourite selection(s), so the side we publish as
    a pick is quoted at its fair price and its American odds therefore stay inside the
    same window as the fair line. Total overround over the market = `overround`.
    """
    if is_favourite:
        d = decimal_from_prob(p)
    else:
        shifted = p * (1.0 + overround / max(n_others, 1))
        d = decimal_from_prob(min(shifted, 0.999))
    return {"book_decimal": d, "book_american": american(d)}


# ---------------------------------------------------------------- market builders


def two_way(name: str, label_a: str, label_b: str, p_a: float, overround: float = 0.02) -> dict:
    p_a = min(max(p_a, 1e-4), 1 - 1e-4)
    p_b = 1.0 - p_a
    fav_a = p_a >= p_b
    return {
        "market": name,
        "line": None,
        "selections": [
            dict(label=label_a, side="A", **fair(p_a), **book(p_a, overround, fav_a, 1)),
            dict(label=label_b, side="B", **fair(p_b), **book(p_b, overround, not fav_a, 1)),
        ],
    }


def three_way(name: str, labels: list[str], ps: list[float], overround: float = 0.03) -> dict:
    total = sum(ps)
    ps = [p / total for p in ps]
    fav_i = max(range(len(ps)), key=lambda i: ps[i])
    sels = []
    for i, (lab, p) in enumerate(zip(labels, ps)):
        sels.append(dict(label=lab, side="ABD"[i], **fair(p), **book(p, overround, i == fav_i, len(ps) - 1)))
    return {"market": name, "line": None, "selections": sels}


def margin_market(name: str, label_a: str, label_b: str, mean_margin: float, sigma: float,
                  line: float, overround: float = 0.02) -> dict:
    """Two-way handicap on the margin (side A margin = A score - B score).

    A covers the line L when (A - B) + L > 0, so
        P(A covers) = P(margin > -L) = 1 - Phi((-L - mu) / sigma).
    (The previous revision used 1 - Phi(L); that inverted the sign of the line and was
    caught by the consistency check in verify.py: a team cannot be more likely to cover
    -4.5 than to win the match outright.)
    """
    p_a = 1.0 - normal_cdf(-line, mean_margin, sigma)

    def price(p, lab, side, fav):
        return dict(label=lab, side=side, **fair(p), **book(p, overround, fav, 1))

    fav_a = p_a >= 0.5
    return {
        "market": name,
        "line": line,
        "selections": [price(p_a, label_a, "A", fav_a), price(1 - p_a, label_b, "B", not fav_a)],
    }


def total_market(name: str, mean_total: float, sigma: float, line: float,
                 poisson_lambda: float | None = None, overround: float = 0.02) -> dict:
    if poisson_lambda is not None:
        # P(total > line) for a half-line under a Poisson total
        k = int(math.floor(line))
        p_over = 1.0 - poisson_cdf(k, poisson_lambda)
    else:
        p_over = 1.0 - normal_cdf(line, mean_total, sigma)
    p_over = min(max(p_over, 1e-4), 1 - 1e-4)
    fav_over = p_over >= 0.5
    return {
        "market": name,
        "line": line,
        "selections": [
            dict(label=f"Over {line}", side="O", **fair(p_over), **book(p_over, overround, fav_over, 1)),
            dict(label=f"Under {line}", side="U", **fair(1 - p_over), **book(1 - p_over, overround, not fav_over, 1)),
        ],
    }


def poisson_two_way(name: str, label_a: str, label_b: str, lam_a: float, lam_b: float,
                    max_goals: int = 15, draw_split: float = 0.5, overround: float = 0.02) -> dict:
    p_a = p_b = p_draw = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            pr = poisson_pmf(i, lam_a) * poisson_pmf(j, lam_b)
            if i > j:
                p_a += pr
            elif i < j:
                p_b += pr
            else:
                p_draw += pr
    return two_way(name, label_a, label_b, p_a + draw_split * p_draw, overround)


def poisson_totals(prefix: str, lam_total: float, lines: list[float]) -> list[dict]:
    return [total_market(f"{prefix} {line}", lam_total, 0, line, poisson_lambda=lam_total) for line in lines]


def poisson_handicap(name: str, label_a: str, label_b: str, lam_a: float, lam_b: float,
                     line: float, max_goals: int = 15) -> dict:
    """Handicap on the goal margin, Poisson difference distribution (draw handled as push-free half line)."""
    p_a = 0.0
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            pr = poisson_pmf(i, lam_a) * poisson_pmf(j, lam_b)
            if (i - j) + line > 0:
                p_a += pr
    p_a = min(max(p_a, 1e-4), 1 - 1e-4)
    fav_a = p_a >= 0.5
    return {
        "market": name,
        "line": line,
        "selections": [
            dict(label=label_a, side="A", **fair(p_a), **book(p_a, 0.02, fav_a, 1)),
            dict(label=label_b, side="B", **fair(1 - p_a), **book(1 - p_a, 0.02, not fav_a, 1)),
        ],
    }


def best_of(name: str, label_a: str, label_b: str, p_a: float, frames: int,
            overround: float = 0.02) -> dict:
    return two_way(name, label_a, label_b, p_a, overround)


def confidence(p: float, min_games: int | None = None, required_games: int = 5) -> str:
    """The published confidence rule (also printed on the methodology page)."""
    label = "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")
    if min_games is not None and min_games < required_games:
        # never label a pick High off a sample smaller than the disclosure threshold
        label = "Medium" if label == "High" else label
    return label


WINDOW_LOW = 1.400      # -250 American
WINDOW_HIGH = 101.0     # +10,000 American
CONFIDENCE_FLOOR = 0.70
BAND_LOW = CONFIDENCE_FLOOR              # 0.7000
BAND_HIGH = 1.0 / WINDOW_LOW             # 0.714285... -> the only overlap of the two rules


def in_window(decimal_odds: float) -> bool:
    return WINDOW_LOW <= decimal_odds <= WINDOW_HIGH


def in_band(p: float) -> bool:
    """Where '>= 70%' and 'no shorter than -250' overlap."""
    return BAND_LOW - 1e-9 <= p <= BAND_HIGH + 1e-9

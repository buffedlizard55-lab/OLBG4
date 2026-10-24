#!/usr/bin/env python3
"""Board EC — own-line maths.

Every number that reaches the site is produced here from inputs that were copied
out of an official response by ``parse.py``.  Nothing in this module looks at a
bookmaker price: the lines we publish are ours, and the OLBG price (when we have
one) is stored separately so the two can be compared rather than conflated.

House conventions, all documented so a reviewer can re-derive them:

* decimal  = 1 / p, rounded to 2dp;  american = -100*p/(1-p) when p > 0.5,
  otherwise +100*(1-p)/p.  Both are re-derived in verify.py from the stored p.
* Home edge is only ever applied when the official table we fitted from is a
  home-and-away league table; the size of the edge is a fixed, documented
  constant per sport, never fitted to the fixtures we are pricing.
* Confidence, per the brief: High = our own line implies p >= 0.70 for the
  selection AND the fair price sits inside -250 ... +10,000.  A sport whose
  only input is a ranking list is capped at Medium; a sport with fewer than
  three completed matches of sample behind it is capped at Low.
"""
from __future__ import annotations

import math

MAXG = 22  # Poisson truncation: P(>22 goals) is far below the rounding we print


# ------------------------------------------------------------------ pricing
def american(dec: float) -> int:
    """American odds from decimal odds (used only for display)."""
    if dec is None or dec <= 1.0:
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def dec_from_p(p: float) -> float:
    p = min(max(p, 0.0001), 0.9999)
    return round(1.0 / p, 2)


def fair(p: float) -> dict:
    d = dec_from_p(p)
    return {"p": round(p, 4), "decimal": d, "american": american(d)}


def in_price_window(dec: float) -> bool:
    """The brief's window: -250 ... +10,000 American.

    -250 American == decimal 1.40;  +10,000 American == decimal 101.00.
    """
    return dec is not None and 1.40 <= dec <= 101.0


def confidence(p: float, cap: str = "High", sample_games: int = 99) -> str:
    """High / Medium / Low from our own probability, then capped by evidence.

    Cap ladder: 10+ completed games behind the input keeps the sport's cap, 4-9
    drops it to Medium, fewer than 4 drops it to Low.
    """
    base = "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")
    order = {"Low": 0, "Medium": 1, "High": 2}
    sc = cap
    if sample_games < 4:
        sc = "Low"
    elif sample_games < 10:
        sc = "Medium" if order[cap] > 1 else cap
    return base if order[base] <= order[sc] else sc


# ------------------------------------------------------------------- maths
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_grid(lh: float, la: float) -> dict[tuple[int, int], float]:
    ph = [poisson_pmf(k, lh) for k in range(MAXG + 1)]
    pa = [poisson_pmf(k, la) for k in range(MAXG + 1)]
    total = sum(ph) * sum(pa)
    return {(i, j): ph[i] * pa[j] / total for i in range(MAXG + 1) for j in range(MAXG + 1)}


def goal_markets(lh: float, la: float, line: float, handicap: float, draw_ok: bool = True) -> dict:
    """Win / handicap / total from a bivariate-independent Poisson grid."""
    grid = poisson_grid(lh, la)
    home = sum(p for (i, j), p in grid.items() if i > j)
    draw = sum(p for (i, j), p in grid.items() if i == j)
    away = sum(p for (i, j), p in grid.items() if i < j)
    # Two-way market when the sport cannot draw; the drawn mass is re-split in
    # proportion to the decisive results, which is the standard shut-out rule.
    if not draw_ok and (home + away) > 0:
        home, away = home / (home + away), away / (home + away)
        draw = 0.0
    over = sum(p for (i, j), p in grid.items() if i + j > line)
    hcov = sum(p for (i, j), p in grid.items() if (i - j) + handicap > 0)
    return {
        "home": home,
        "draw": draw,
        "away": away,
        "over": over,
        "under": 1.0 - over,
        "handicap_home": hcov,
        "handicap_away": 1.0 - hcov,
        "exp_total": lh + la,
    }


def normal_markets(mu: float, sd: float, line: float, handicap: float) -> dict:
    """Two-way margin market for sports with no draw (basketball, sets)."""
    p_home = 1.0 - norm_cdf((0.0 - mu) / sd)          # P(margin > 0)
    p_over = 1.0 - norm_cdf((line - mu) / sd)
    p_hcov = 1.0 - norm_cdf((0.0 - (mu + handicap)) / sd)
    return {
        "home": p_home,
        "away": 1.0 - p_home,
        "over": p_over,
        "under": 1.0 - p_over,
        "handicap_home": p_hcov,
        "handicap_away": 1.0 - p_hcov,
        "exp_total": mu,
    }


def best_of_n(p: float, n: int) -> float:
    """P(win a first-to-(n//2+1) match) where p is the per-frame/leg chance."""
    need = n // 2 + 1
    return sum(math.comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(need, n + 1))


def best_of_n_margins(p: float, n: int) -> dict[int, float]:
    need = n // 2 + 1
    out: dict[int, float] = {}
    for k in range(need, n + 1):
        m = k - (n - k)
        out[m] = out.get(m, 0.0) + math.comb(n, k) * p ** k * (1 - p) ** (n - k)
    return out


def volleyball_dist(p_set: float) -> dict[str, float]:
    """Best-of-five from a per-set probability (sets treated as independent)."""

    def win_from(i: int, j: int) -> float:
        if i == 3:
            return 1.0
        if j == 3:
            return 0.0
        return p_set * win_from(i + 1, j) + (1 - p_set) * win_from(i, j + 1)

    p_match = win_from(0, 0)
    p_five = math.comb(4, 2) * p_set ** 2 * (1 - p_set) ** 2  # 2-2 after four sets
    return {"home": p_match, "away": 1 - p_match, "five_sets": p_five, "p_set": p_set}


def plackett_luce(scores: list[float], tau: float) -> list[float]:
    """Share of a title market from a score list (points, world ranking points)."""
    if not scores:
        return []
    e = [math.exp(s / tau) for s in scores]
    s = sum(e)
    return [x / s for x in e]


def elo_p(ra: float, rb: float, scale: float) -> float:
    """Logistic on a rating gap.  ``scale`` is the points-per-10x factor."""
    return 1.0 / (1.0 + 10 ** ((rb - ra) / scale))


def shrink(p: float, k: float = 0.97) -> float:
    """Pull an extreme probability back towards 50% before pricing it."""
    return 0.5 + (p - 0.5) * k


def round_market(markets: dict) -> dict:
    """Re-round every probability to 4dp and attach decimal + American."""
    out = {}
    for name, mk in markets.items():
        sel = []
        for s in mk["selections"]:
            f = fair(s["p"])
            sel.append({**s, **f})
        out[name] = {"line": mk.get("line"), "note": mk.get("note", ""), "selections": sel}
    return out

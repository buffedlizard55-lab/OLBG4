#!/usr/bin/env python3
"""Board W - line-origination maths (no data access; pure functions).

Every price produced here is a *fair* price (no bookmaker margin) derived only from
official numeric inputs supplied by the caller (ranking points, prize-money order of
merit, standings goals/points for and against, run differential). Nothing is inferred
when an input is missing: callers must pass None and the functions return None.
"""
from __future__ import annotations

import math
from typing import Optional

# --------------------------------------------------------------------------- odds


def american(p: Optional[float]) -> Optional[int]:
    """Fair American odds for probability p (0<p<1)."""
    if p is None or p <= 0 or p >= 1:
        return None
    if p >= 0.5:
        return -int(round(100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def decimal(p: Optional[float]) -> Optional[float]:
    if p is None or p <= 0 or p >= 1:
        return None
    return round(1 / p, 2)


def in_window(american_price: Optional[int], lo: int = -250, hi: int = 10000) -> Optional[bool]:
    """True when an American price lies inside the brief's High window (-250 ... +10000).

    -250 means implied probability 71.43%; anything shorter (e.g. -300) is outside.
    """
    if american_price is None:
        return None
    if american_price < 0:
        return american_price >= lo
    return american_price <= hi


def clamp(p: float, lo: float = 0.03, hi: float = 0.97) -> float:
    return max(lo, min(hi, p))


# --------------------------------------------------------------------------- strength ratios


def power_ratio(a: Optional[float], b: Optional[float], alpha: float) -> Optional[float]:
    """P(A beats B) = a^alpha / (a^alpha + b^alpha) for positive strength measures."""
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    x, y = a ** alpha, b ** alpha
    return clamp(x / (x + y))


# --------------------------------------------------------------------------- race-to-N (sets/legs/frames)


def race_win(q: float, n: int) -> float:
    """P(player with per-unit win prob q is first to n units) (units independent)."""
    tot = 0.0
    for k in range(n):  # opponent wins k units before our n-th
        tot += math.comb(n - 1 + k, k) * q ** n * (1 - q) ** k
    return tot


def solve_unit(p_match: float, n: int) -> float:
    """Invert race_win: per-unit probability q giving match probability p_match."""
    lo, hi = 1e-6, 1 - 1e-6
    for _ in range(80):
        mid = (lo + hi) / 2
        if race_win(mid, n) < p_match:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def race_score_dist(q: float, n: int) -> dict:
    """Distribution of final scores in a race to n: {(a,b): prob} with a==n or b==n."""
    out = {}
    for k in range(n):
        out[(n, k)] = math.comb(n - 1 + k, k) * q ** n * (1 - q) ** k
        out[(k, n)] = math.comb(n - 1 + k, k) * (1 - q) ** n * q ** k
    return out


def race_markets(p_match: float, n: int, handicaps=(1.5, 2.5, 3.5), totals=None) -> dict:
    """Derived handicap / total-units / correct-score markets from a match probability."""
    q = solve_unit(p_match, n)
    dist = race_score_dist(q, n)
    res = {"unit_prob_A": round(q, 4), "correct_score": {f"{a}-{b}": round(v, 4) for (a, b), v in sorted(dist.items(), key=lambda kv: -kv[1])}}
    hc = {}
    for h in handicaps:
        p_cover = sum(v for (a, b), v in dist.items() if a - b > h)  # A -h
        hc[f"A -{h}"] = round(p_cover, 4)
        hc[f"B +{h}"] = round(1 - p_cover, 4)
    res["handicap"] = hc
    if totals is None:
        exp_units = sum((a + b) * v for (a, b), v in dist.items())
        line = math.floor(exp_units) + 0.5
        totals = (line,)
    tt = {}
    for t in totals:
        p_over = sum(v for (a, b), v in dist.items() if a + b > t)
        tt[f"Over {t}"] = round(p_over, 4)
        tt[f"Under {t}"] = round(1 - p_over, 4)
    res["total_units"] = tt
    res["expected_units"] = round(sum((a + b) * v for (a, b), v in dist.items()), 2)
    return res


# --------------------------------------------------------------------------- normal-margin sports


def norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def margin_markets(exp_margin: float, sd: float, exp_total: Optional[float] = None, sd_total: Optional[float] = None,
                   draw_band: float = 0.0) -> dict:
    """Markets from a normal model of (home - away) margin.

    draw_band>0 => three-way market: P(draw) = P(|margin| < draw_band) (e.g. 0.5 for integer scores).
    Spread line = expected margin rounded to the nearest .5 (no inference beyond the model output).
    """
    if draw_band > 0:
        p_home = 1 - norm_cdf((draw_band - exp_margin) / sd)
        p_away = norm_cdf((-draw_band - exp_margin) / sd)
        p_draw = 1 - p_home - p_away
    else:
        p_home = 1 - norm_cdf((0 - exp_margin) / sd)
        p_away = 1 - p_home
        p_draw = 0.0
    line = round(exp_margin * 2) / 2
    if line == int(line):
        line += 0.5 if exp_margin >= line else -0.5
    # home -line covers when margin > line
    p_cover_home = 1 - norm_cdf((line - exp_margin) / sd)
    res = {"p_home": round(p_home, 4), "p_away": round(p_away, 4), "p_draw": round(p_draw, 4),
           "exp_margin_home": round(exp_margin, 2), "spread_home": -line,
           "p_home_cover": round(p_cover_home, 4), "p_away_cover": round(1 - p_cover_home, 4)}
    if exp_total is not None and sd_total:
        tl = math.floor(exp_total) + 0.5
        p_over = 1 - norm_cdf((tl - exp_total) / sd_total)
        res.update({"exp_total": round(exp_total, 1), "total_line": tl, "p_over": round(p_over, 4), "p_under": round(1 - p_over, 4)})
    return res


# --------------------------------------------------------------------------- poisson (hockey)


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_markets(lam_home: float, lam_away: float, total_lines=(4.5, 5.5, 6.5), puck=1.5, ot_home_share=0.5) -> dict:
    """Independent-Poisson regulation score model; two-way ML splits regulation draws by ot_home_share."""
    mx = 15
    ph = pa = pd = 0.0
    cover_home = 0.0
    tot = {t: 0.0 for t in total_lines}
    for i in range(mx):
        for j in range(mx):
            p = poisson_pmf(i, lam_home) * poisson_pmf(j, lam_away)
            if i > j:
                ph += p
            elif j > i:
                pa += p
            else:
                pd += p
            if i - j > puck:
                cover_home += p
            for t in total_lines:
                if i + j > t:
                    tot[t] += p
    ml_home = ph + pd * ot_home_share
    res = {"reg_home": round(ph, 4), "reg_draw": round(pd, 4), "reg_away": round(pa, 4),
           "p_home": round(ml_home, 4), "p_away": round(1 - ml_home, 4),
           "puck_line": {f"home -{puck}": round(cover_home, 4), f"away +{puck}": round(1 - cover_home, 4)},
           "exp_total": round(lam_home + lam_away, 2),
           "totals": {f"Over {t}": round(v, 4) for t, v in tot.items()}}
    return res


# --------------------------------------------------------------------------- confidence


def grade(p_pick: Optional[float], data_complete: bool, pick_price: Optional[int], market_price_for_pick: Optional[int],
          high_floor: float = 0.60) -> tuple[str, str]:
    """Confidence label + reason.

    High   : model p >= high_floor, fair price inside -250...+10000, complete official inputs for
             both sides, and (if a market price for the same selection is displayed) that market
             price is also inside the window.
    Medium : model p >= 0.56 with complete inputs but not High (incl. outside-window favourites).
    Low    : everything else (coin-flip edges or partial inputs).
    """
    if p_pick is None:
        return "", "no line (missing official inputs)"
    if not data_complete:
        return "Low", "partial official inputs"
    win_ok = in_window(pick_price)
    mkt_ok = True if market_price_for_pick is None else in_window(market_price_for_pick)
    if p_pick >= high_floor and win_ok and mkt_ok:
        return "High", "model p>=%.2f, fair price %s in window" % (high_floor, pick_price)
    if p_pick >= 0.56:
        if p_pick >= high_floor and not win_ok:
            return "Medium", "outside window: fair price %s shorter than -250" % pick_price
        if p_pick >= high_floor and not mkt_ok:
            return "Medium", "outside window: market price %s shorter than -250" % market_price_for_pick
        return "Medium", "model edge moderate"
    return "Low", "close contest"

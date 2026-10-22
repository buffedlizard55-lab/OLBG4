#!/usr/bin/env python3
"""Board Z (session arena/9359e596-olbg4) - independent multi-market line origination engine.

Pure deterministic functions operating solely on verified governing-body numerical inputs
(official ranking points, order-of-merit positions, standings wins/losses/points/goals/runs
for and against, set/point quotients).

Zero vig (fair 100% book) is reported alongside American and Decimal representations so every
originated price can be audited directly against the brief's -250 to +10000 High-confidence
focus window (1.40 <= fair_decimal <= 101.00, i.e. 0.99% <= p <= 71.4286%).
"""
from __future__ import annotations

import math
from typing import Optional


def clamp(p: float, lo: float = 0.02, hi: float = 0.98) -> float:
    return max(lo, min(hi, p))


def fair_decimal(p: Optional[float]) -> Optional[float]:
    if p is None or p <= 0.0 or p >= 1.0:
        return None
    return round(1.0 / p, 2)


def fair_american(p: Optional[float]) -> Optional[int]:
    if p is None or p <= 0.0 or p >= 1.0:
        return None
    if p >= 0.5:
        return -int(round(100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def fmt_american(am: Optional[int]) -> str:
    if am is None:
        return "—"
    return f"+{am}" if am > 0 else str(am)


def in_high_window(am: Optional[int], lo: int = -250, hi: int = 10000) -> bool:
    """True iff American odds sit strictly inside [-250, +10000] (decimal ~1.40 to 101.00)."""
    if am is None or am == 0:
        return False
    if am < 0:
        return am >= lo
    return am <= hi


def price_pair(p_a: float) -> dict:
    p_a = round(clamp(p_a), 4)
    p_b = round(1.0 - p_a, 4)
    return {
        "p_a": p_a,
        "p_b": p_b,
        "dec_a": fair_decimal(p_a),
        "dec_b": fair_decimal(p_b),
        "am_a": fair_american(p_a),
        "am_b": fair_american(p_b),
    }


def power_ratio(strength_a: Optional[float], strength_b: Optional[float], alpha: float, home_boost: float = 1.0) -> Optional[float]:
    if strength_a is None or strength_b is None or strength_a <= 0 or strength_b <= 0:
        return None
    xa = (strength_a ** alpha) * home_boost
    xb = strength_b ** alpha
    return clamp(xa / (xa + xb))


# ---------------------------------------------------------------------------
# Discrete race-to-N model (Tennis sets, Snooker frames, Darts legs, Volleyball sets, Badminton games)
# ---------------------------------------------------------------------------

def race_win_prob(q: float, n: int) -> float:
    total = 0.0
    for k in range(n):
        total += math.comb(n - 1 + k, k) * (q ** n) * ((1.0 - q) ** k)
    return total


def invert_race_unit(p_match: float, n: int) -> float:
    lo, hi = 1e-6, 1.0 - 1e-6
    for _ in range(70):
        mid = 0.5 * (lo + hi)
        if race_win_prob(mid, n) < p_match:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def race_markets(
    p_match_a: float,
    first_to_n: int,
    unit_name: str,
    label_a: str,
    label_b: str,
    handicap_line: Optional[float] = None,
    total_line: Optional[float] = None,
    pts_per_unit: Optional[float] = None,
) -> dict:
    p_a = clamp(p_match_a)
    q = invert_race_unit(p_a, first_to_n)
    dist = {}
    for k in range(first_to_n):
        dist[(first_to_n, k)] = math.comb(first_to_n - 1 + k, k) * (q ** first_to_n) * ((1.0 - q) ** k)
        dist[(k, first_to_n)] = math.comb(first_to_n - 1 + k, k) * ((1.0 - q) ** first_to_n) * (q ** k)

    exp_units = sum((a + b) * v for (a, b), v in dist.items())
    exp_margin = sum((a - b) * v for (a, b), v in dist.items())

    if handicap_line is None:
        if first_to_n == 2:
            handicap_line = -1.5 if p_a >= 0.5 else 1.5
        else:
            raw_h = round(abs(exp_margin) - 0.25) + 0.5
            raw_h = max(1.5, min(first_to_n - 0.5, raw_h))
            handicap_line = -raw_h if p_a >= 0.5 else raw_h

    # P(A + handicap_line > B) <=> A - B > -handicap_line
    p_hc_a = clamp(sum(v for (a, b), v in dist.items() if (a + handicap_line) > b), 0.03, 0.97)

    if total_line is None:
        total_line = math.floor(exp_units) + 0.5
        total_line = max(first_to_n + 0.5, min(2 * first_to_n - 1.5, total_line))
    p_over = clamp(sum(v for (a, b), v in dist.items() if (a + b) > total_line), 0.04, 0.96)

    top_scores = sorted(dist.items(), key=lambda kv: -kv[1])[:4]
    ml = price_pair(p_a)
    hc = price_pair(p_hc_a)
    tot = price_pair(p_over)

    out = {
        "format": f"First to {first_to_n} {unit_name}",
        "moneyline": {
            "type": "2-way",
            "a_label": label_a,
            "b_label": label_b,
            **ml,
        },
        "handicap": {
            "unit": unit_name,
            "line_a": handicap_line,
            "line_b": -handicap_line,
            "a_label": f"{label_a} {handicap_line:+.1f} {unit_name}",
            "b_label": f"{label_b} {-handicap_line:+.1f} {unit_name}",
            **hc,
        },
        "total": {
            "unit": unit_name,
            "line": total_line,
            "expected": round(exp_units, 2),
            "over_label": f"Over {total_line:.1f} {unit_name}",
            "under_label": f"Under {total_line:.1f} {unit_name}",
            "p_over": tot["p_a"],
            "p_under": tot["p_b"],
            "dec_over": tot["dec_a"],
            "dec_under": tot["dec_b"],
            "am_over": tot["am_a"],
            "am_under": tot["am_b"],
        },
        "correct_score_top": [
            {"score": f"{a}-{b}", "p": round(v, 4), "dec": fair_decimal(v), "am": fair_american(v)}
            for (a, b), v in top_scores
        ],
    }
    if pts_per_unit is not None:
        exp_pts = round(exp_units * pts_per_unit, 1)
        pts_line = math.floor(exp_pts) + 0.5
        out["secondary_total_points"] = {"line": pts_line, "expected": exp_pts}
    return out


# ---------------------------------------------------------------------------
# Normal margin & total model (Basketball, Handball, Rugby Union, Rugby League, AFLW, Baseball, Cricket)
# ---------------------------------------------------------------------------

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_markets(
    exp_margin_home: float,
    sd_margin: float,
    exp_total: Optional[float],
    sd_total: Optional[float],
    home_label: str,
    away_label: str,
    unit_name: str = "pts",
    draw_band: float = 0.0,
) -> dict:
    if draw_band > 0.0:
        p_home_reg = clamp(1.0 - norm_cdf((draw_band - exp_margin_home) / sd_margin), 0.02, 0.96)
        p_away_reg = clamp(norm_cdf((-draw_band - exp_margin_home) / sd_margin), 0.02, 0.96)
        p_draw_reg = max(0.01, round(1.0 - p_home_reg - p_away_reg, 4))
        norm_s = p_home_reg + p_away_reg + p_draw_reg
        p_home_reg = round(p_home_reg / norm_s, 4)
        p_away_reg = round(p_away_reg / norm_s, 4)
        p_draw_reg = round(1.0 - p_home_reg - p_away_reg, 4)
        p_home_2way = clamp(p_home_reg / (p_home_reg + p_away_reg))
    else:
        p_home_2way = clamp(1.0 - norm_cdf(-exp_margin_home / sd_margin))
        p_home_reg, p_away_reg, p_draw_reg = round(p_home_2way, 4), round(1.0 - p_home_2way, 4), 0.0

    # Half-point spread centered near -exp_margin_home
    raw_line = math.floor(abs(exp_margin_home)) + 0.5
    if abs(exp_margin_home) < 0.5:
        raw_line = 0.5
    line_home = -raw_line if exp_margin_home >= 0 else raw_line
    # Home covers line_home when (H - A) + line_home > 0 <=> (H - A) > -line_home
    p_cover_home = clamp(1.0 - norm_cdf((-line_home - exp_margin_home) / sd_margin), 0.04, 0.96)

    ml2 = price_pair(p_home_2way)
    hc = price_pair(p_cover_home)

    res = {
        "expected_margin_home": round(exp_margin_home, 2),
        "moneyline": {
            "type": "3-way" if draw_band > 0.0 else "2-way",
            "a_label": home_label,
            "b_label": away_label,
            **ml2,
        },
        "handicap": {
            "unit": unit_name,
            "line_a": line_home,
            "line_b": -line_home,
            "a_label": f"{home_label} {line_home:+.1f} {unit_name}",
            "b_label": f"{away_label} {-line_home:+.1f} {unit_name}",
            **hc,
        },
    }
    if draw_band > 0.0:
        res["three_way"] = {
            "p_home": p_home_reg,
            "p_draw": p_draw_reg,
            "p_away": p_away_reg,
            "dec_home": fair_decimal(p_home_reg),
            "dec_draw": fair_decimal(p_draw_reg),
            "dec_away": fair_decimal(p_away_reg),
            "am_home": fair_american(p_home_reg),
            "am_draw": fair_american(p_draw_reg),
            "am_away": fair_american(p_away_reg),
        }
    if exp_total is not None and sd_total is not None and sd_total > 0:
        t_line = math.floor(exp_total) + 0.5
        p_over = clamp(1.0 - norm_cdf((t_line - exp_total) / sd_total), 0.04, 0.96)
        tot = price_pair(p_over)
        res["total"] = {
            "unit": unit_name,
            "line": t_line,
            "expected": round(exp_total, 1),
            "over_label": f"Over {t_line:.1f} {unit_name}",
            "under_label": f"Under {t_line:.1f} {unit_name}",
            "p_over": tot["p_a"],
            "p_under": tot["p_b"],
            "dec_over": tot["dec_a"],
            "dec_under": tot["dec_b"],
            "am_over": tot["am_a"],
            "am_under": tot["am_b"],
        }
    else:
        res["total"] = None
    return res


# ---------------------------------------------------------------------------
# Bivariate-independent Poisson model (Ice Hockey: Moneyline incl. OT/SO, 1X2, Puck Line, Totals)
# ---------------------------------------------------------------------------

def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def hockey_poisson_markets(lam_home: float, lam_away: float, home_label: str, away_label: str) -> dict:
    lam_h = max(1.2, min(5.5, lam_home))
    lam_a = max(1.2, min(5.5, lam_away))
    max_g = 15
    ph = [poisson_pmf(k, lam_h) for k in range(max_g + 1)]
    pa = [poisson_pmf(k, lam_a) for k in range(max_g + 1)]

    p_reg_h, p_reg_a, p_tie = 0.0, 0.0, 0.0
    p_h_m15, p_a_m15 = 0.0, 0.0
    totals_over = {5.5: 0.0, 6.5: 0.0}

    for h in range(max_g + 1):
        for a in range(max_g + 1):
            pr = ph[h] * pa[a]
            if h > a:
                p_reg_h += pr
            elif a > h:
                p_reg_a += pr
            else:
                p_tie += pr
            if h - a >= 2:
                p_h_m15 += pr
            if a - h >= 2:
                p_a_m15 += pr
            for tl in totals_over:
                if h + a > tl:
                    totals_over[tl] += pr

    # OT/SO win share slightly tilted toward higher scoring rate side
    ot_share_h = lam_h / (lam_h + lam_a)
    p_ml_h = clamp(p_reg_h + p_tie * ot_share_h)
    ml = price_pair(p_ml_h)

    fav_home = p_ml_h >= 0.5
    if fav_home:
        line_h = -1.5
        hc = price_pair(clamp(p_h_m15, 0.05, 0.95))
    else:
        line_h = 1.5
        hc = price_pair(clamp(1.0 - p_a_m15, 0.05, 0.95))

    exp_tot = lam_h + lam_a
    # Include expected ~0.22 goal probability for OT winner in 2-way total settlement
    tl = 5.5 if exp_tot < 6.0 else 6.5
    p_over = clamp(totals_over[tl] + (p_tie * 0.65 if tl == 5.5 else p_tie * 0.35), 0.05, 0.95)
    tot = price_pair(p_over)

    return {
        "lambda_home": round(lam_h, 2),
        "lambda_away": round(lam_a, 2),
        "moneyline": {
            "type": "2-way (incl. OT/SO)",
            "a_label": home_label,
            "b_label": away_label,
            **ml,
        },
        "three_way": {
            "p_home": round(p_reg_h, 4),
            "p_draw": round(p_tie, 4),
            "p_away": round(p_reg_a, 4),
            "dec_home": fair_decimal(p_reg_h),
            "dec_draw": fair_decimal(p_tie),
            "dec_away": fair_decimal(p_reg_a),
            "am_home": fair_american(p_reg_h),
            "am_draw": fair_american(p_tie),
            "am_away": fair_american(p_reg_a),
        },
        "handicap": {
            "unit": "goals",
            "line_a": line_h,
            "line_b": -line_h,
            "a_label": f"{home_label} {line_h:+.1f} goals",
            "b_label": f"{away_label} {-line_h:+.1f} goals",
            **hc,
        },
        "total": {
            "unit": "goals",
            "line": tl,
            "expected": round(exp_tot, 2),
            "over_label": f"Over {tl:.1f} goals",
            "under_label": f"Under {tl:.1f} goals",
            "p_over": tot["p_a"],
            "p_under": tot["p_b"],
            "dec_over": tot["dec_a"],
            "dec_under": tot["dec_b"],
            "am_over": tot["am_a"],
            "am_under": tot["am_b"],
        },
    }

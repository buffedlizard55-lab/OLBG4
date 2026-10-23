#!/usr/bin/env python3
"""Board AT — market mathematics.

Everything on the desk is priced with one of three distributions applied to a rating difference
that was computed from official results. Nothing is invented: if a distribution parameter cannot be
estimated from official data in the capture, the caller passes `None` and the market is published
unpriced with a flag.

Conventions
-----------
* ``p`` is always the probability of the **pick** winning the market as stated.
* Prices are published in decimal and American form, derived from ``p`` after the market's
  own overround-free normalisation (these are *our* lines, not a bookmaker's).
* The requested focus band is -250 to +10,000 American. For a two-way market that band is
  exactly p in [0.7000, 0.7143]; for any market priced at +100 or longer the band is wide.
  Both the band membership and the high-confidence gate (p >= 0.70) are reported separately so
  the reader can see which picks satisfy both.
"""
from __future__ import annotations

import math
from statistics import NormalDist

_N = NormalDist()

# ---------------------------------------------------------------- distribution helpers
SQRT2 = math.sqrt(2.0)


def norm_cdf(x: float) -> float:
    return _N.cdf(x)


def p_margin_gt(k: float, mu: float, sigma: float) -> float:
    """P(margin > k) for margin ~ Normal(mu, sigma)."""
    if sigma is None or sigma <= 0:
        raise ValueError("sigma must be positive")
    return norm_cdf((mu - k) / sigma)


def p_two_way(mu: float, sigma: float, push: bool = False) -> float:
    """P(side A wins outright). With ``push`` a margin of exactly 0 is split 50/50."""
    p_win = norm_cdf(mu / sigma)
    if push:
        # a normal is continuous, so the tie mass is 0; kept explicit for integer-scored sports
        return p_win
    return p_win


def p_total_over(line: float, mu_total: float, sigma_total: float) -> float:
    return norm_cdf((mu_total - line) / sigma_total)


# ---------------------------------------------------------------- odds conversions
def american_to_decimal(a: int | float) -> float:
    a = float(a)
    return 1 + 100.0 / abs(a) if a < 0 else 1 + a / 100.0


def decimal_to_american(d: float) -> int:
    if d <= 1.0:
        raise ValueError("decimal odds must exceed 1.0")
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))


def prob_to_decimal(p: float) -> float:
    if not 0 < p < 1:
        raise ValueError("probability must be strictly between 0 and 1")
    return 1.0 / p


def prob_to_american(p: float) -> int:
    return decimal_to_american(prob_to_decimal(p))


def prob_to_fractional(p: float, max_denominator: int = 1000) -> str:
    """Nearest simple fractional price, the way a bookmaker would quote it."""
    d = prob_to_decimal(p)
    stake = 1.0
    num = d - 1.0
    best = None
    for den in range(1, max_denominator + 1):
        n = round(num * den)
        if n < 1:
            continue
        err = abs(n / den - num)
        if best is None or err < best[0] - 1e-12:
            best = (err, n, den)
        if err < 1e-6:
            break
    if best is None:
        return ""
    return f"{best[1]}/{best[2]}"


def in_focus_band(american: int | None, lo: int = -250, hi: int = 10000) -> bool:
    """The requested price window: -250 .. +10000 American."""
    if american is None:
        return False
    if american < 0:
        return american >= lo
    return american <= hi


def band_probability_range(lo: int = -250, hi: int = 10000) -> tuple[float, float]:
    """Two-way win-probability range implied by the focus band."""
    p_short = 1 / american_to_decimal(lo)
    p_long = 1 / american_to_decimal(hi)
    return (p_short, p_long)


# ---------------------------------------------------------------- multi-outcome (Plackett-Luce)
def plackett_luce(strengths: dict[str, float]) -> dict[str, float]:
    """Win probabilities for one winner out of N from relative strengths (all > 0)."""
    total = sum(strengths.values())
    if total <= 0:
        raise ValueError("strengths must sum to a positive value")
    return {k: v / total for k, v in strengths.items()}


def strengths_from_gaps(gaps: dict[str, float], scale: float) -> dict[str, float]:
    """Turn a gap-to-leader (0 for the leader, larger = further behind) into a relative strength.

    ``scale`` is the gap that makes a competitor exactly half as likely as the leader.
    """
    if scale <= 0:
        raise ValueError("scale must be positive")
    return {k: 0.5 ** (max(0.0, g) / scale) for k, g in gaps.items()}


# ---------------------------------------------------------------- rating helpers
def mean_sd(values: list[float]) -> tuple[float | None, float | None]:
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return None, None
    mu = sum(vals) / n
    if n < 2:
        return mu, None
    var = sum((v - mu) ** 2 for v in vals) / (n - 1)
    return mu, math.sqrt(var)


def logistic(x: float, k: float) -> float:
    """P from a rating difference ``x`` where ``k`` is the difference worth a 73.1% chance."""
    return 1.0 / (1.0 + math.exp(-x / k))


def pythagorean(pf: float, pa: float, exponent: float) -> float:
    if pf <= 0 or pa <= 0:
        raise ValueError("points for/against must be positive")
    return pf ** exponent / (pf ** exponent + pa ** exponent)


def price_row(prob: float, market: str, pick: str, lo: int = -250, hi: int = 10000) -> dict:
    """The published price block for one pick at one probability."""
    if not 0 < prob < 1:
        return {"pick": pick, "market": market, "prob": prob, "priceable": False}
    dec = prob_to_decimal(prob)
    amer = prob_to_american(prob)
    return {
        "pick": pick,
        "market": market,
        "our_prob": round(prob, 4),
        "our_decimal": round(dec, 3),
        "our_american": amer,
        "our_fractional": prob_to_fractional(prob),
        "implied_prob_of_our_price": round(1 / dec, 4),
        "in_focus_band": in_focus_band(amer, lo, hi),
        "priceable": True,
    }


def grade(prob: float | None, sample: int, min_sample: int, model_sigma_ok: bool = True) -> tuple[str, list[str]]:
    """Confidence grade plus every reason the grade was held back."""
    reasons: list[str] = []
    if prob is None:
        return "Unpriced", ["no line could be originated from official data"]
    if sample < min_sample:
        reasons.append(f"rating sample {sample} official games is below the {min_sample}-game floor")
    if not model_sigma_ok:
        reasons.append("margin dispersion could not be estimated from official results")
    if prob >= 0.70 and not reasons:
        return "High", reasons
    if prob >= 0.70:
        return "Medium", reasons + ["win chance clears 70% but the sample gate held it back"]
    if prob >= 0.55:
        return "Medium", reasons
    return "Low", reasons


# ---------------------------------------------------------------- small-sample discipline
def shrink(diff_per_game: float, games: int, k: float) -> float:
    """Shrink an observed per-game differential toward zero.

    Early in a season a 7-game differential is mostly noise, and publishing a line straight off it
    is exactly the kind of over-confidence this desk refuses to print. ``k`` is the number of games
    at which the observed differential and a zero differential carry equal weight.
    """
    if games <= 0:
        return 0.0
    return diff_per_game * (games / (games + k))


def sigma_with_rating_error(sigma_margin: float, unit_sd: float, games: int, k: float) -> float:
    """Widen the match-margin dispersion to cover the uncertainty in the two ratings themselves.

    Each rating is a mean over ``games`` official results, so its standard error is
    ``unit_sd / sqrt(games)``; the two ratings enter the margin with opposite signs, and the
    shrinkage weight ``games / (games + k)`` scales that error down in step with the shrinkage.
    """
    if games <= 0:
        return sigma_margin
    weight = games / (games + k)
    se = (unit_sd / (games ** 0.5)) * weight * (2 ** 0.5)
    return (sigma_margin ** 2 + se ** 2) ** 0.5


def ladder(prob_fn, lines: list[float], market: str, label: str) -> list[dict]:
    """Publish a full ladder of handicap / total lines rather than a single arbitrary one."""
    out = []
    for line in lines:
        p = prob_fn(line)
        if p is None or not (0.001 < p < 0.999):
            continue
        out.append(price_row(p, market, label.format(line=line)))
    return out

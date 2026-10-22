#!/usr/bin/env python3
"""Board AF — line-origination maths.

Everything here is deterministic arithmetic on probabilities that were themselves
derived from numbers printed on an official page. No bookmaker price and no OLBG
price is used to set a line.

Conventions
-----------
* `p_a` is the probability that side A wins the match, after the sample-size
  shrinkage described in `shrink`.
* The winning margin M of side A is modelled as Normal(mu, sigma) with
  mu = sigma * Phi^-1(p_a), so the match-winner probability and the handicap
  probabilities are two views of the same distribution.
* Handicap line L is applied to side A in the usual bookmaker sense: "A -L"
  wins when M > L. Negative L therefore means A receives a start.
* Totals are Normal(total_mu, sigma_total).
"""
from __future__ import annotations

import math


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Acklam's inverse normal CDF, refined with one Newton step."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = [-3.969683028665376e01, 2.209460984245205e02, -2.759285104469687e02,
         1.383577518672690e02, -3.066479806614716e01, 2.506628277459239e00]
    b = [-5.447609879822406e01, 1.615858368580409e02, -1.556989798598866e02,
         6.680131188771972e01, -1.328068155288572e01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e00,
         -2.549732539343734e00, 4.374664141464968e00, 2.938163982698783e00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e00,
         3.754408661907416e00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    elif p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    else:
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)
    e = norm_cdf(x) - p
    u = e * math.sqrt(2 * math.pi) * math.exp(x * x / 2)
    return x - u / (1 + x * u / 2)


def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)


def logit(p: float) -> float:
    return math.log(p / (1 - p))


def shrink(p: float, n: float, k: float) -> float:
    """Shrink a raw rate towards 0.5 in proportion to its sample size.

    n games (or ranking-equivalent evidence) with prior weight k. This is the
    standard empirical-Bayes style correction used so that a 2-0 record cannot
    masquerade as a 100% team.
    """
    n = max(0.0, float(n))
    return 0.5 + (p - 0.5) * (n / (n + k))


def american_from_decimal(dec: float) -> int:
    dec = max(dec, 1.0001)
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def decimal_from_american(am: int) -> float:
    am = int(am)
    if am > 0:
        return 1.0 + am / 100.0
    return 1.0 + 100.0 / abs(am)


def fair(prob: float) -> dict:
    p = min(max(prob, 0.0101), 0.9899)
    dec = 1.0 / p
    return {
        "prob": round(p, 6),
        "fair_decimal": round(dec, 3),
        "fair_american": american_from_decimal(dec),
    }


def book(prob: float, overround: float) -> dict:
    """Our published price: fair price with the stated over-round folded in.

    A two-way market published this way sums to 1 + overround in implied
    probability, which is exactly the margin a bookmaker keeps. The fair price
    (1/p) is published alongside so the margin is visible.
    """
    p = min(max(prob, 0.0101), 0.9899)
    dec = (1.0 + overround) / p
    return {
        "fair_prob": round(p, 6),
        "fair_decimal": round(1.0 / p, 3),
        "fair_american": american_from_decimal(1.0 / p),
        "book_decimal": round(dec, 3),
        "book_american": american_from_decimal(dec),
        "implied_prob": round(p / (1.0 + overround), 6),
    }


def two_way(p_a: float, overround: float) -> list[dict]:
    p_a = min(max(p_a, 0.0101), 0.9899)
    return [book(p_a, overround), book(1.0 - p_a, overround)]


def three_way(p_a: float, p_draw: float, overround: float) -> list[dict]:
    p_b = max(0.0101, 1.0 - p_a - p_draw)
    return [book(p_a, overround), book(p_draw, overround), book(p_b, overround)]


def total_over_prob(line: float, mean: float, sigma: float) -> float:
    return 1.0 - norm_cdf((line - mean) / sigma)


def handicap_cover_prob(line: float, mu: float, sigma: float) -> float:
    """P(margin > line) — the probability that the side giving `line` covers."""
    return 1.0 - norm_cdf((line - mu) / sigma)


def margin_mu(p_a: float, sigma: float) -> float:
    return sigma * norm_ppf(min(max(p_a, 0.0101), 0.9899))


def in_window(fair_american: int) -> bool:
    """The brief's requested band: -250 to +10,000 American."""
    return -250 <= fair_american <= 10000


def confidence(prob: float, sample_ok: bool, verified: bool, in_win: bool) -> str:
    """Low / Medium / High under the printed rule.

    High  = model probability >= 70.0%, verified official inputs, adequate
            sample, and the fair price inside the requested -250..+10,000 band.
    Medium= model probability >= 60.0%, or a High-grade probability that fails
            one of the three gates (published with the failing gate named).
    Low   = everything else.
    """
    if prob >= 0.70 and sample_ok and verified and in_win:
        return "High"
    if prob >= 0.60:
        return "Medium"
    return "Low"

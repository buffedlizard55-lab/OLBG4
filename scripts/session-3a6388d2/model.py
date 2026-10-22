"""Board AD — line-origination mathematics (shared by every sport).

Every number produced here is derived *only* from values that were read out of an
official league / federation response committed under data/session-3a6388d2/raw/.
No market price, tipster percentage or third-party rating is used anywhere.

The published "fair" price is the model's own probability expressed as odds.  The
published "book" price is the same probability with a 4.2% (two-way) / 5.2% (three-way)
over-round applied proportionally, i.e. what our own book would show a customer.
"""
from __future__ import annotations

import math

# --------------------------------------------------------------------------- odds maths
def dec_to_americain(d: float) -> int:
    if d <= 1.0000001:
        return -100000
    if d >= 2.0:
        return int(round((d - 1.0) * 100))
    return int(round(-100.0 / (d - 1.0)))


def american_to_dec(a: int) -> float:
    a = float(a)
    return 1.0 + (a / 100.0 if a > 0 else 100.0 / abs(a))


def prob_to_american(p: float) -> int:
    if p <= 0:
        return 100000
    if p >= 1:
        return -100000
    return dec_to_americain(1.0 / p)


def apply_margin(p: float, margin: float) -> float:
    """Proportional over-round: p_book = p * (1 + margin), clipped to a valid price."""
    return min(max(p * (1.0 + margin), 1e-6), 0.999999)


def price(p: float, margin: float = 0.042):
    """Return (fair_decimal, fair_american, book_decimal, book_american)."""
    if p <= 0 or p >= 1:
        return None, None, None, None
    fd = 1.0 / p
    pb = apply_margin(p, margin)
    bd = 1.0 / pb
    return round(fd, 4), prob_to_american(p), round(bd, 4), prob_to_american(pb)


# --------------------------------------------------------------------------- distributions
def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * (lam ** k) / math.factorial(k) if lam > 0 else (1.0 if k == 0 else 0.0)


def score_grid(lam_home: float, lam_away: float, n: int = 14):
    """Independent-Poisson joint distribution of two scores."""
    ph = [poisson_pmf(i, lam_home) for i in range(n + 1)]
    pa = [poisson_pmf(i, lam_away) for i in range(n + 1)]
    return ph, pa


def poisson_probs(lam_home: float, lam_away: float, n: int = 14, ot_share_home: float = 0.52):
    """Return (p_home_ml, p_away_ml, p_home_minus_1_5, p_away_plus_1_5, exp_total).

    p_home_ml includes the shootout/overtime tie-break: tied games after regulation are
    split with `ot_share_home` going to the home side (NHL home teams win ~52% of games
    that reach OT/SO).  The -1.5 / +1.5 handicap is settled on the regulation margin,
    which is exactly how a puck line behaves: an OT/SO win is still a one-goal game.
    """
    ph, pa = score_grid(lam_home, lam_away, n)
    p_hw = p_aw = p_tie = 0.0
    p_h_cap = 0.0            # margin >= 2 (home -1.5)
    p_a_cap = 0.0            # margin >= 2 (away -1.5)
    for i, x in enumerate(ph):
        for j, y in enumerate(pa):
            p = x * y
            m = i - j
            if m > 0:
                p_hw += p
            elif m < 0:
                p_aw += p
            else:
                p_tie += p
            if m >= 2:
                p_h_cap += p
            if m <= -2:
                p_a_cap += p
    p_home_ml = p_hw + ot_share_home * p_tie
    p_away_ml = 1.0 - p_home_ml
    return p_home_ml, p_away_ml, p_h_cap, p_a_cap, lam_home + lam_away, p_tie


def over_prob(lam_total: float, line: float, n: int = 20) -> float:
    """P(total goals/runs > line) under a Poisson with mean lam_total."""
    return 1.0 - sum(poisson_pmf(k, lam_total) for k in range(int(math.floor(line)) + 1))


def normal_cdf(x: float, mu: float = 0.0, sd: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sd * math.sqrt(2.0))))


def margin_probs(mu: float, sd: float, line: float):
    """P(favourite covers -line) / P(underdog covers +line) under a normal margin."""
    p_cover = 1.0 - normal_cdf(line, mu, sd)      # margin > line
    return p_cover, 1.0 - p_cover


# --------------------------------------------------------------------------- helpers
def nearest_half(x: float) -> float:
    return round(x * 2.0) / 2.0


def shrink(value: float, mean: float, weight: float) -> float:
    """Regression to the mean: `weight` is the confidence in `value` (0..1)."""
    return weight * value + (1.0 - weight) * mean


def pythagorean(scored: float, allowed: float, exponent: float) -> float:
    if scored + allowed <= 0:
        return 0.5
    return scored ** exponent / (scored ** exponent + allowed ** exponent)


def log5(pa: float, pb: float) -> float:
    pa = min(max(pa, 1e-6), 1 - 1e-6)
    pb = min(max(pb, 1e-6), 1 - 1e-6)
    num = pa * (1.0 - pb)
    den = num + (1.0 - pa) * pb
    return num / den if den else 0.5

#!/usr/bin/env python3
"""Board ZZ — own-line mathematics.

Every function is deterministic and pure: given a strength input read from a captured official
payload, it returns selection probabilities that sum to exactly 1 within their market, and the
fair decimal/American price derived from that probability (decimal = 1/p, American re-derived
from the decimal, never hand-typed).

The brief's High-confidence test is applied in `grade()`:
    High  ⇔ p >= 0.70 AND -250 <= American <= +10000
Because p >= 0.70 implies American <= -233.33, the two conditions only overlap for
p in [0.7000, 0.7143] (-250 … -233).  Lines are therefore originated on a fine threshold
lattice (0.25 increments) and the band is searched explicitly rather than assumed.
"""
from __future__ import annotations

import math
from statistics import NormalDist

ND = NormalDist()

HIGH_P_FLOOR = 0.70
WINDOW_LO = -250
WINDOW_HI = 10000


# --------------------------------------------------------------------------------- prices
def prob_to_decimal(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return round(1.0 / p, 3)


def prob_to_american(p: float) -> int:
    p = min(max(p, 1e-6), 1 - 1e-6)
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


def fmt_american(a: int) -> str:
    return f"+{a}" if a > 0 else f"{a}"


def in_window(american: int) -> bool:
    return WINDOW_LO <= american <= WINDOW_HI


def implied(american: int) -> float:
    if american <= -100:
        return (-american) / ((-american) + 100.0)
    return 100.0 / (american + 100.0)


def outcome(selection: str, p: float) -> dict:
    d = prob_to_decimal(p)
    a = prob_to_american(p)
    return {
        "selection": selection,
        "fair_prob": round(p, 4),
        "fair_decimal": d,
        "fair_american": a,
        "fair_american_str": fmt_american(a),
        "in_window": in_window(a),
    }


def market(key: str, label: str, outcomes: list[dict], basis: str) -> dict:
    total = sum(o["fair_prob"] for o in outcomes)
    assert abs(total - 1.0) < 0.02, f"{key}: probabilities sum to {total}"
    return {"market_key": key, "market_label": label, "basis": basis, "outcomes": outcomes}


# ---------------------------------------------------------------------------------- pmfs
def poisson_pmf(lam: float, k_max: int = 30) -> list[float]:
    lam = max(lam, 0.05)
    out, acc = [], 0.0
    for k in range(k_max + 1):
        v = math.exp(-lam) * lam**k / math.factorial(k)
        out.append(v)
        acc += v
    return [v / acc for v in out]


def normal_pmf(mean: float, sd: float, lo: int, hi: int) -> dict[int, float]:
    """Discrete pmf on integers lo..hi from a normal with continuity correction."""
    sd = max(sd, 1e-3)
    vals = {k: ND.cdf((k + 0.5 - mean) / sd) - ND.cdf((k - 0.5 - mean) / sd) for k in range(lo, hi + 1)}
    s = sum(vals.values())
    return {k: v / s for k, v in vals.items()}


def margin_pmf(pmf_a: list[float], pmf_b: list[float]) -> dict[int, float]:
    out: dict[int, float] = {}
    for i, pa in enumerate(pmf_a):
        for j, pb in enumerate(pmf_b):
            out[i - j] = out.get(i - j, 0.0) + pa * pb
    return out


def total_pmf(pmf_a: list[float], pmf_b: list[float]) -> dict[int, float]:
    out: dict[int, float] = {}
    for i, pa in enumerate(pmf_a):
        for j, pb in enumerate(pmf_b):
            out[i + j] = out.get(i + j, 0.0) + pa * pb
    return out


def p_at_least(pmf: dict[int, float], k: float) -> float:
    """P(X >= k) for integer-ish pmf and half/quarter lines (quarter lines split)."""
    if abs(k - round(k)) < 1e-9:
        kk = int(round(k))
        return sum(v for x, v in pmf.items() if x >= kk)
    lo = math.floor(k)
    frac = k - lo
    return sum(v for x, v in pmf.items() if x >= lo + 1) + frac * pmf.get(lo, 0.0)


def p_over(pmf: dict[int, float], line: float) -> float:
    return p_at_least(pmf, line + (0.0 if abs(line - round(line)) > 1e-9 else 0.5))


# --------------------------------------------------------------- generic market constructors
def three_way(home: str, away: str, p_home: float, p_draw: float, basis: str) -> dict:
    p_away = max(0.0, 1.0 - p_home - p_draw)
    return market("match_winner", "Match Winner (90/60-minute three-way)",
                  [outcome(home, p_home), outcome("Draw", p_draw), outcome(away, p_away)], basis)


def two_way_win(home: str, away: str, p_home: float, basis: str) -> dict:
    return market("match_winner", "Match Winner (incl. overtime / deciding set)",
                  [outcome(home, p_home), outcome(away, 1.0 - p_home)], basis)


def handicap_ladder(home: str, away: str, margin: dict[int, float], lines: list[float],
                    basis: str, unit: str) -> list[dict]:
    out = []
    for line in lines:
        # home line = -line means home must win by more than `line`
        p_home = 1.0 - p_at_least(margin, line + 0.5)
        p_home = min(max(p_home, 0.005), 0.995)
        sign = f"{-line:+g}"
        out.append(market(f"handicap_{line:+g}", f"{home} {sign} ({unit} handicap)",
                          [outcome(f"{home} {sign}", p_home), outcome(f"{away} {-line:+g}", 1 - p_home)],
                          basis))
    return out


def total_ladder(home: str, away: str, total: dict[int, float], lines: list[float],
                 basis: str, label_unit: str) -> list[dict]:
    out = []
    for line in lines:
        p_over = 1.0 - p_at_least(total, math.floor(line) + 1)
        if abs(line - round(line)) < 1e-9:
            p_over = 1.0 - p_at_least(total, int(round(line)) + 1)
            p_over += 0.0
        p_over = min(max(p_over, 0.005), 0.995)
        out.append(market(f"total_{line:+g}", f"Match Total {line:g} {label_unit}",
                          [outcome(f"Over {line:g}", p_over), outcome(f"Under {line:g}", 1 - p_over)],
                          basis))
    return out


def best_of(winner_name: str, loser_name: str, p_win: float, n_units: int,
            unit_name: str, handicap_lines: list[float], total_lines: list[float],
            basis: str) -> list[dict]:
    """Best-of-N binary unit model (frames / legs / sets) from a single match-win probability.

    Derives per-unit probability q from p_win by inverting the binomial tail, then prices
    winner, unit-handicap and total-units markets.  No external data needed beyond p_win.
    """
    need = n_units // 2 + 1

    def win_prob(q: float) -> float:
        return sum(math.comb(n_units, k) * q**k * (1 - q) ** (n_units - k) for k in range(need, n_units + 1))

    lo, hi = 0.001, 0.999
    for _ in range(80):
        mid = (lo + hi) / 2
        if win_prob(mid) < p_win:
            lo = mid
        else:
            hi = mid
    q = (lo + hi) / 2

    markets = [market("match_winner", f"Match Winner (best of {n_units} {unit_name}s)",
                      [outcome(winner_name, p_win), outcome(loser_name, 1 - p_win)], basis)]

    # distribution of total units played
    tot: dict[int, float] = {}
    for w in range(need, n_units + 1):
        for l in range(0, need):
            if max(w, l) < need or (w < need and l < need):
                continue
            if not (w == need or l == need):
                continue
            games = w + l
            p = (math.comb(games - 1, w - 1) * q**w * (1 - q) ** l if w == need
                 else math.comb(games - 1, l - 1) * (1 - q) ** l * q**w)
            tot[games] = tot.get(games, 0.0) + p
    s = sum(tot.values())
    tot = {k: v / s for k, v in tot.items()}

    for line in total_lines:
        p_over = 1.0 - p_at_least(tot, math.floor(line) + 1)
        p_over = min(max(p_over, 0.005), 0.995)
        markets.append(market(f"total_{line:+g}", f"Total {unit_name}s {line:g}",
                              [outcome(f"Over {line:g} {unit_name}s", p_over),
                               outcome(f"Under {line:g} {unit_name}s", 1 - p_over)], basis))

    for line in handicap_lines:
        # P(winner wins by strictly more than line units)
        p_cov = 0.0
        for games, p in tot.items():
            won = need
            lost = games - need
            if won - lost > line:
                p_cov += p * ((q**need * (1 - q) ** lost * math.comb(games - 1, need - 1)) /
                              max(p, 1e-12))
        p_cov = min(max(p_cov, 0.005), 0.995)
        markets.append(market(f"handicap_{line:+g}", f"{winner_name} {-line:+g} {unit_name} handicap",
                              [outcome(f"{winner_name} {-line:+g} {unit_name}s", p_cov),
                               outcome(f"{loser_name} {line:+g} {unit_name}s", 1 - p_cov)], basis))
    return markets


# --------------------------------------------------------------------------------- grading
def grade(p: float, american: int) -> str:
    if p >= HIGH_P_FLOOR and in_window(american):
        return "High"
    if p >= 0.55 and in_window(american):
        return "Medium"
    return "Low"


def in_high_band(p: float) -> bool:
    return HIGH_P_FLOOR <= p <= (250.0 / 350.0) and in_window(prob_to_american(p))


def choose_pick(markets: list[dict]) -> dict | None:
    """Pick, in priority order:
       1. any selection with p in the High band [0.700, 0.7143] and a window price;
       2. else the in-window selection with the highest p (Medium if p >= 0.55);
       3. else the highest-p selection at all (graded Low, out of window).
    Excludes draws and field/other-runner buckets from being the headline pick.
    """
    cands: list[tuple[dict, dict]] = []
    for mkt in markets:
        for o in mkt["outcomes"]:
            if o["selection"] in ("Draw", "Regulation Draw") or "All Other" in o["selection"] or "Field" in o["selection"]:
                continue
            cands.append((mkt, o))
    if not cands:
        return None

    band = [(m, o) for m, o in cands if in_high_band(o["fair_prob"]) and o["in_window"]]
    if band:
        m, o = max(band, key=lambda x: x[1]["fair_prob"])
    else:
        win = [(m, o) for m, o in cands if o["in_window"]]
        pool = win or cands
        m, o = max(pool, key=lambda x: x[1]["fair_prob"])
    return {
        "market_key": m["market_key"],
        "market_label": m["market_label"],
        "selection": o["selection"],
        "fair_prob": o["fair_prob"],
        "fair_decimal": o["fair_decimal"],
        "fair_american": o["fair_american"],
        "fair_american_str": o["fair_american_str"],
        "in_window": o["in_window"],
        "confidence": grade(o["fair_prob"], o["fair_american"]),
    }


def winner_pick(markets: list[dict]) -> dict | None:
    """The outright match-winner pick (always reported, whatever its grade)."""
    for mkt in markets:
        if mkt["market_key"] == "match_winner":
            outs = [o for o in mkt["outcomes"] if o["selection"] != "Draw"]
            if not outs:
                return None
            o = max(outs, key=lambda x: x["fair_prob"])
            return {
                "selection": o["selection"],
                "fair_prob": o["fair_prob"],
                "fair_american_str": o["fair_american_str"],
                "confidence": grade(o["fair_prob"], o["fair_american"]),
            }
    return None

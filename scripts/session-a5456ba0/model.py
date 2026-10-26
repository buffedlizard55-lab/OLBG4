#!/usr/bin/env python3
"""Board AN — pricing library.

Everything here is arithmetic on inputs that were read from a committed official
capture.  Nothing is scraped, nothing is guessed from a bookmaker price: the only
free parameters are the documented model constants in `CONST`, and every constant is
printed on the Method page next to the rows it produced.

Conventions
-----------
* `p` is a probability in (0, 1).
* A *fair* price carries no margin: decimal = 1/p, American derived from that decimal.
  The desk publishes fair prices; it never quotes a bookmaker price as its own.
* American odds are quoted in the standard form: -250 means stake 250 to win 100.
"""
from __future__ import annotations

import math
import random

CONST = {
    # shrinkage: pseudo-games added at the league mean before a rate is used
    "shrink_games": 8.0,
    # standard deviation of a match margin, by scoring family (documented assumptions)
    "margin_sd": {
        "basketball": 12.0,
        "rugby_union": 13.0,
        "rugby_league": 14.0,
        "baseball_runs": 4.2,
    },
    # a High grade needs this many completed matches behind the weaker side
    "min_sample_high": 5,
    "min_sample_medium": 3,
    # operator's price window for a High pick
    "window_american": (-250, 10000),
    "high_p": 0.70,
    "medium_p": 0.60,
}


# ------------------------------------------------------------------ price maths
def decimal_from_p(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return round(1.0 / p, 3)


def american_from_decimal(dec: float) -> int:
    if dec <= 1.0:
        raise ValueError("decimal odds must exceed 1")
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def american_from_p(p: float) -> int:
    return american_from_decimal(decimal_from_p(p))


def p_from_american(american: float) -> float:
    a = float(american)
    return 100.0 / (a + 100.0) if a > 0 else abs(a) / (abs(a) + 100.0)


def in_window(american: int) -> bool:
    lo, hi = CONST["window_american"]
    return lo <= american <= hi


def confidence(p: float, american: int, sample: int | None, cap: str | None = None) -> str:
    """Grade a selection.

    High  = p >= 0.70 AND the fair price sits inside the operator window (-250..+10,000)
            AND at least `min_sample_high` completed matches sit behind the weaker side.
    Medium= p >= 0.60, or a High-probability pick whose price is outside the window,
            or a High-probability pick on a thin sample (capped).
    Low   = everything else.
    """
    band_p = p >= CONST["high_p"]
    band_window = in_window(american)
    thin = sample is not None and sample < CONST["min_sample_high"]
    grade = "High" if (band_p and band_window and not thin) else (
        "Medium" if p >= CONST["medium_p"] else "Low"
    )
    if cap == "Medium" and grade == "High":
        grade = "Medium"
    if cap == "Low" and grade in ("High", "Medium"):
        grade = "Low"
    if thin and sample is not None and sample < CONST["min_sample_medium"] and grade == "High":
        grade = "Medium"
    return grade


# --------------------------------------------------------------------- Poisson
def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def poisson_grid(lh: float, la: float, top: int = 15):
    grid = [[poisson_pmf(lh, i) * poisson_pmf(la, j) for j in range(top + 1)] for i in range(top + 1)]
    total = sum(sum(row) for row in grid)
    return [[v / total for v in row] for row in grid]


def poisson_markets(lh: float, la: float, lines=(-1.5, -0.5, 0.5, 1.5)) -> dict:
    """3-way winner, Asian-style handicap (no push: only .5 lines are quoted) and total."""
    grid = poisson_grid(lh, la)
    home = sum(grid[i][j] for i in range(len(grid)) for j in range(len(grid)) if i > j)
    draw = sum(grid[i][i] for i in range(len(grid)))
    away = 1.0 - home - draw
    out = {
        "match_winner": [
            {"name": "home", "p": home},
            {"name": "draw", "p": draw},
            {"name": "away", "p": away},
        ],
        "handicap": [],
        "total": [],
    }
    for line in lines:
        hp = sum(
            grid[i][j]
            for i in range(len(grid))
            for j in range(len(grid))
            if (i - j) + line > 0
        )
        out["handicap"].append({"line": line, "home": hp, "away": 1.0 - hp})
    base = round(lh + la)
    for line in (base - 1.5, base - 0.5, base + 0.5, base + 1.5):
        over = sum(
            grid[i][j]
            for i in range(len(grid))
            for j in range(len(grid))
            if i + j > line
        )
        out["total"].append({"line": line, "over": over, "under": 1.0 - over})
    return out


# ------------------------------------------------------------- normal margins
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_markets(mu_margin: float, mu_total: float, family: str = "basketball",
                   sd_margin: float | None = None, sd_total: float | None = None,
                   lines=None) -> dict:
    """2-way margin/total markets for score-based sports; the line is the home margin."""
    sd_margin = sd_margin or CONST["margin_sd"][family]
    sd_total = sd_total or sd_margin
    if lines is None:
        lines = (-1.5, -2.5, -3.5, -5.5, -6.5, -7.5, -9.5)
    out = {
        "match_winner": [
            {"name": "home", "p": phi(mu_margin / sd_margin)},
            {"name": "away", "p": 1.0 - phi(mu_margin / sd_margin)},
        ],
        "handicap": [],
        "total": [],
    }
    for line in lines:
        hp = phi((mu_margin - line) / sd_margin)
        out["handicap"].append({"line": line, "home": hp, "away": 1.0 - hp})
    base = round(mu_total * 2) / 2  # nearest half point
    for line in (base - 3.0, base - 1.5, base, base + 1.5, base + 3.0):
        over = 1.0 - phi((line - mu_total) / sd_total)
        out["total"].append({"line": line, "over": over, "under": 1.0 - over})
    return out


# ------------------------------------------------------- series (frames/legs)
def comb(n: int, k: int) -> int:
    return math.comb(n, k) if 0 <= k <= n else 0


def series_win_prob(p_unit: float, need: int) -> float:
    """Probability of being first to `need` units in a race."""
    return sum(comb(need + i - 1, i) * p_unit**need * (1 - p_unit) ** i for i in range(need))


def unit_prob_from_match(p_match: float, need: int) -> float:
    """Invert `series_win_prob` for a best-of-(2*need-1) series (bisection, i.i.d. units)."""
    lo, hi = 1e-4, 1 - 1e-4
    for _ in range(80):
        mid = (lo + hi) / 2
        if series_win_prob(mid, need) < p_match:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def series_markets(p_match: float, need: int) -> dict:
    """Match winner, units handicap and total units for a race to `need` units.

    The per-unit probability is the unique value whose i.i.d. series probability equals
    the match probability we priced, so the three markets are internally consistent:
    they are three views of one model, not three unrelated guesses.
    """
    p = unit_prob_from_match(p_match, need)
    q = 1.0 - p

    def p_margin(m: int) -> float:
        """P(the match ends with a signed unit margin of exactly m)."""
        if m > 0:
            j = need - m  # units the loser took
            return comb(need + j - 1, j) * p**need * q**j if j >= 0 else 0.0
        if m < 0:
            i = need + m  # units the winner conceded
            return comb(need + i - 1, i) * q**need * p**i if i >= 0 else 0.0
        return 0.0

    out = {
        "match_winner": [{"name": "home", "p": p_match}, {"name": "away", "p": 1 - p_match}],
        "handicap": [],
        "total": [],
    }
    for line in (-1.5, -2.5, -3.5):
        if abs(line) - 0.5 >= need:
            continue
        cover = sum(p_margin(m) for m in range(int(abs(line) - 0.5) + 1, need + 1))
        out["handicap"].append({"line": line, "home": cover, "away": 1.0 - cover})
    tot = {}
    for k in range(need, 2 * need):
        tot[k] = comb(k - 1, need - 1) * (p**need * q ** (k - need) + q**need * p ** (k - need))
    norm = sum(tot.values())
    for k in tot:
        tot[k] /= norm
    for line in (need + 0.5, need + 1.5, 2 * need - 0.5):
        if line <= need or line >= 2 * need - 0.5:
            continue
        over = sum(v for k, v in tot.items() if k > line)
        out["total"].append({"line": line, "over": over, "under": 1.0 - over})
    return out


# ------------------------------------------------------------ Plackett-Luce
def plackett_luce(weights: dict[str, float], top_k: int = 10, sims: int = 20000,
                  seed: int = 20261026) -> dict[str, dict]:
    """Win and top-k probabilities for a multi-runner field.

    Plackett-Luce is the standard ranking model: each runner's win probability is
    w_i / sum(w), and repeated draws without replacement give the placing distribution.
    Weights are read from the official ranking/points table, never from a price.
    """
    names = list(weights)
    w = [max(float(weights[n]), 1e-9) for n in names]
    total = sum(w)
    rng = random.Random(seed)
    wins = {n: 0 for n in names}
    top = {n: 0 for n in names}
    for _ in range(sims):
        pool = list(range(len(names)))
        alive = total
        order = []
        for _pos in range(min(top_k, len(names))):
            r = rng.random() * alive
            acc = 0.0
            pick = pool[-1]
            for idx in pool:
                acc += w[idx]
                if r <= acc:
                    pick = idx
                    break
            order.append(pick)
            alive -= w[pick]
            pool.remove(pick)
        wins[names[order[0]]] += 1
        for idx in order[:top_k]:
            top[names[idx]] += 1
    return {
        n: {"win": wins[n] / sims, "top": top[n] / sims}
        for n in names
    }


# --------------------------------------------------------- Bradley-Terry fit
def fit_bradley_terry(games: list[dict], l2: float = 1.0, iters: int = 400,
                      home_adv: bool = True, lr: float = 0.35):
    """Fit a logistic (Bradley-Terry) strength model by gradient descent.

    `games` is a list of {home, away, home_score, away_score}.  Returns
    (rating dict centred on 0, home advantage in log-odds, games per team).
    Only completed official matches are passed in, so the fit is a real maximum
    likelihood estimate rather than a hand-picked ranking.
    """
    teams = sorted({g["home"] for g in games} | {g["away"] for g in games})
    idx = {t: i for i, t in enumerate(teams)}
    r = [0.0] * len(teams)
    h = 0.0
    counts = {t: 0 for t in teams}
    for g in games:
        counts[g["home"]] += 1
        counts[g["away"]] += 1
    for _ in range(iters):
        gr = [0.0] * len(teams)
        gh = 0.0
        n = 0
        for g in games:
            i, j = idx[g["home"]], idx[g["away"]]
            if g["home_score"] == g["away_score"]:
                continue  # draws carry no BT information
            y = 1.0 if g["home_score"] > g["away_score"] else 0.0
            z = r[i] - r[j] + (h if home_adv else 0.0)
            p = 1.0 / (1.0 + math.exp(-z))
            err = y - p
            gr[i] += err
            gr[j] -= err
            if home_adv:
                gh += err
            n += 1
        if not n:
            break
        for i in range(len(teams)):
            r[i] += lr * (gr[i] / n - l2 * r[i] / n)
        if home_adv:
            h += lr * gh / n
        norm = sum(r) / len(r)
        r = [x - norm for x in r]
    return {t: r[idx[t]] for t in teams}, h, counts

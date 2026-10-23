#!/usr/bin/env python3
"""Board FB (arena/48de8c1d-olbg4) — Pure closed-form multi-market origination math.

Zero probability overrides, zero artificial clamping into narrow bands.
Every market normalizes to exact Σ fair_prob = 1.0000 (4 d.p.) and derives
fair_decimal = round(1 / p, 3) and exact American odds from the same fair_prob.
"""
from __future__ import annotations

import math
from typing import Iterable


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def prob_to_decimal(p: float) -> float:
    p_c = min(max(p, 1e-4), 1.0 - 1e-4)
    return round(1.0 / p_c, 3)


def prob_to_american(p: float) -> int:
    p_c = min(max(p, 1e-4), 1.0 - 1e-4)
    if abs(p_c - 0.5) < 1e-9:
        return 100
    if p_c > 0.5:
        am = -int(round(100.0 * p_c / (1.0 - p_c)))
        return min(am, -100)
    am = int(round(100.0 * (1.0 - p_c) / p_c))
    return max(am, 100)


def fmt_american(am: int) -> str:
    return f"+{am}" if am > 0 else str(am)


def in_actionable_window(am: int) -> bool:
    """True iff American odds sit in [-250, +10000] (valid American odds exclude (-100, +100))."""
    return (-250 <= am <= -100) or (100 <= am <= 10000)


def make_market(market_key: str, market_label: str, raw_outcomes: Iterable[tuple[str, float]], basis: str = "") -> dict:
    items = [(label, max(float(w), 1e-6)) for label, w in raw_outcomes]
    total_w = sum(w for _, w in items)
    probs = [round(w / total_w, 4) for _, w in items]
    probs = [min(max(p, 0.0001), 0.9998) for p in probs]
    drift = round(1.0 - sum(probs), 4)
    if drift != 0.0:
        idx_max = max(range(len(probs)), key=lambda i: probs[i])
        probs[idx_max] = round(probs[idx_max] + drift, 4)

    outcomes = []
    for (label, _), p in zip(items, probs):
        am = prob_to_american(p)
        outcomes.append(
            {
                "selection": label,
                "fair_prob": p,
                "fair_decimal": prob_to_decimal(p),
                "fair_american": am,
                "fair_american_str": fmt_american(am),
                "in_window": in_actionable_window(am),
            }
        )
    return {
        "market_key": market_key,
        "market_label": market_label,
        "prob_sum": round(sum(o["fair_prob"] for o in outcomes), 4),
        "basis": basis,
        "outcomes": outcomes,
    }


def poisson_pmf(lam: float, k_max: int = 24) -> list[float]:
    lam = max(lam, 0.05)
    pmf = [math.exp(-lam)]
    for k in range(1, k_max + 1):
        pmf.append(pmf[-1] * lam / k)
    s = sum(pmf)
    return [x / s for x in pmf]


def poisson_game_markets(
    home: str,
    away: str,
    lam_home: float,
    lam_away: float,
    *,
    sport: str,
    spread_line: float = 1.5,
    total_line: float | None = None,
    f5_fraction: float = 0.56,
) -> list[dict]:
    """Exact bivariate independent Poisson pricing for Ice Hockey and Baseball."""
    ph = poisson_pmf(lam_home, 24)
    pa = poisson_pmf(lam_away, 24)

    p_reg_h = 0.0
    p_reg_d = 0.0
    p_reg_a = 0.0
    fav_is_home = lam_home >= lam_away

    if total_line is None:
        raw_tot = lam_home + lam_away
        total_line = math.floor(raw_tot) + 0.5
        if abs((total_line - 1.0) - raw_tot) < abs(total_line - raw_tot):
            total_line -= 1.0
        total_line = max(3.5, total_line)

    p_over = 0.0
    p_fav_cover = 0.0

    for h_g, p_h in enumerate(ph):
        for a_g, p_a in enumerate(pa):
            p_ij = p_h * p_a
            if h_g > a_g:
                p_reg_h += p_ij
            elif h_g == a_g:
                p_reg_d += p_ij
            else:
                p_reg_a += p_ij

            if h_g + a_g > total_line:
                p_over += p_ij

            margin_fav = (h_g - a_g) if fav_is_home else (a_g - h_g)
            if margin_fav > spread_line:
                p_fav_cover += p_ij

    ot_share_h = lam_home / (lam_home + lam_away)
    p_ml_h = p_reg_h + p_reg_d * ot_share_h
    p_ml_a = 1.0 - p_ml_h

    fav_name = home if fav_is_home else away
    dog_name = away if fav_is_home else home
    unit_name = "Puck Line" if sport == "Ice Hockey" else "Run Line"
    tot_label = "Total Goals" if sport == "Ice Hockey" else "Total Runs"

    markets = [
        make_market(
            "match_winner",
            "Moneyline (Incl. OT/Extra)" if sport == "Ice Hockey" else "Moneyline",
            [(home, p_ml_h), (away, p_ml_a)],
            f"Bivariate Poisson (λ_home={lam_home:.2f}, λ_away={lam_away:.2f}) + OT share",
        ),
        make_market(
            "handicap",
            f"{unit_name} ({spread_line:.1f})",
            [(f"{fav_name} -{spread_line:.1f}", p_fav_cover), (f"{dog_name} +{spread_line:.1f}", 1.0 - p_fav_cover)],
            f"Exact Skellam tail P(margin >= {int(spread_line)+1})",
        ),
        make_market(
            "total",
            f"{tot_label} ({total_line:.1f})",
            [(f"Over {total_line:.1f}", p_over), (f"Under {total_line:.1f}", 1.0 - p_over)],
            f"Convolved Poisson sum (E[T]={lam_home + lam_away:.2f})",
        ),
    ]

    if sport == "Ice Hockey":
        markets.append(
            make_market(
                "derivative",
                "60-Minute Regulation 1X2",
                [(f"{home} (60m)", p_reg_h), ("Regulation Draw", p_reg_d), (f"{away} (60m)", p_reg_a)],
                "Exact 60-minute regulation Poisson outcome matrix",
            )
        )
    else:
        ph5 = poisson_pmf(lam_home * f5_fraction, 18)
        pa5 = poisson_pmf(lam_away * f5_fraction, 18)
        p5_h = sum(ph5[i] * pa5[j] for i in range(19) for j in range(19) if i > j)
        p5_d = sum(ph5[i] * pa5[i] for i in range(19))
        p5_a = 1.0 - p5_h - p5_d
        markets.append(
            make_market(
                "derivative",
                "First 5 Innings Draw-No-Bet",
                [(f"{home} F5 DNB", p5_h / max(p5_h + p5_a, 1e-6)), (f"{away} F5 DNB", p5_a / max(p5_h + p5_a, 1e-6))],
                f"First-5-innings Poisson ({f5_fraction*100:.0f}% starter run share)",
            )
        )
    return markets


def normal_points_markets(
    home: str,
    away: str,
    exp_home: float,
    exp_away: float,
    sigma_margin: float,
    sigma_total: float,
    *,
    allow_draw: bool = False,
    draw_half_width: float = 0.5,
    unit: str = "Points",
    spread_override: float | None = None,
    total_override: float | None = None,
) -> list[dict]:
    """Gaussian margin & total origination for Basketball, Rugby, Handball, Cricket, Gaelic."""
    mu_m = exp_home - exp_away
    mu_t = exp_home + exp_away

    if allow_draw:
        p_h = 1.0 - norm_cdf((draw_half_width - mu_m) / sigma_margin)
        p_a = norm_cdf((-draw_half_width - mu_m) / sigma_margin)
        p_d = max(0.005, 1.0 - p_h - p_a)
        mw = make_market(
            "match_winner",
            "Match Result (1X2)",
            [(home, p_h), ("Draw", p_d), (away, p_a)],
            f"Normal margin μ={mu_m:+.2f}, σ={sigma_margin:.2f}",
        )
    else:
        p_h = norm_cdf(mu_m / sigma_margin)
        mw = make_market(
            "match_winner",
            "Match Winner (2-Way)",
            [(home, p_h), (away, 1.0 - p_h)],
            f"Normal margin μ={mu_m:+.2f}, σ={sigma_margin:.2f}",
        )

    fav_is_home = mu_m >= 0.0
    fav_margin = abs(mu_m)
    if spread_override is not None:
        line_s = abs(spread_override)
    else:
        line_s = max(0.5, math.floor(max(0.5, fav_margin - 0.15 * sigma_margin)) + 0.5)

    p_fav_cov = 1.0 - norm_cdf((line_s - fav_margin) / sigma_margin)
    fav_name = home if fav_is_home else away
    dog_name = away if fav_is_home else home
    hc = make_market(
        "handicap",
        f"{unit} Handicap ({line_s:.1f})",
        [(f"{fav_name} -{line_s:.1f}", p_fav_cov), (f"{dog_name} +{line_s:.1f}", 1.0 - p_fav_cov)],
        f"Normal handicap around E[margin]={mu_m:+.2f}",
    )

    if total_override is not None:
        line_t = total_override
    else:
        line_t = math.floor(mu_t - 0.10 * sigma_total) + 0.5
    p_over = 1.0 - norm_cdf((line_t - mu_t) / sigma_total)
    tot = make_market(
        "total",
        f"Total {unit} ({line_t:.1f})",
        [(f"Over {line_t:.1f}", p_over), (f"Under {line_t:.1f}", 1.0 - p_over)],
        f"Normal total E[T]={mu_t:.1f}, σ_T={sigma_total:.1f}",
    )

    home_line = math.floor(exp_home - 0.08 * (sigma_total / math.sqrt(2.0))) + 0.5
    sigma_team = max(2.5, sigma_total / math.sqrt(2.0))
    p_home_over = 1.0 - norm_cdf((home_line - exp_home) / sigma_team)
    deriv = make_market(
        "derivative",
        f"{home} Team {unit} ({home_line:.1f})",
        [(f"{home} Over {home_line:.1f}", p_home_over), (f"{home} Under {home_line:.1f}", 1.0 - p_home_over)],
        f"Team scoring projection E[{home}]={exp_home:.1f}",
    )
    return [mw, hc, tot, deriv]


def best_of_n_markets(
    side_a: str,
    side_b: str,
    unit_prob_a: float,
    best_of: int,
    *,
    unit_name: str,
    handicap_line: float | None = None,
    total_line: float | None = None,
) -> list[dict]:
    """Exact negative-binomial score matrix for Tennis (Bo3), Volleyball (Bo5), Snooker, and Darts."""
    assert best_of % 2 == 1 and best_of >= 3
    target = (best_of + 1) // 2
    q = min(max(unit_prob_a, 0.08), 0.92)

    score_probs: list[tuple[int, int, float]] = []
    for b_won in range(target):
        comb = math.comb(target - 1 + b_won, b_won)
        score_probs.append((target, b_won, comb * (q ** target) * ((1.0 - q) ** b_won)))
    for a_won in range(target):
        comb = math.comb(target - 1 + a_won, a_won)
        score_probs.append((a_won, target, comb * ((1.0 - q) ** target) * (q ** a_won)))

    p_a_win = sum(p for a, b, p in score_probs if a > b)
    fav_is_a = p_a_win >= 0.5
    fav = side_a if fav_is_a else side_b
    dog = side_b if fav_is_a else side_a

    if handicap_line is None:
        if best_of == 3:
            handicap_line = 1.5
        elif best_of == 5:
            handicap_line = 1.5
        else:
            exp_diff = abs(sum((a - b) * p for a, b, p in score_probs))
            handicap_line = max(1.5, math.floor(exp_diff) + 0.5)

    p_fav_cov = sum(
        p
        for a, b, p in score_probs
        if ((a - b) if fav_is_a else (b - a)) > handicap_line
    )

    if total_line is None:
        if best_of == 3:
            total_line = 2.5
        elif best_of == 5:
            total_line = 3.5
        else:
            exp_tot = sum((a + b) * p for a, b, p in score_probs)
            total_line = math.floor(exp_tot) + 0.5
            total_line = min(max(total_line, target + 0.5), best_of - 0.5)

    p_over = sum(p for a, b, p in score_probs if (a + b) > total_line)

    mw = make_market(
        "match_winner",
        "Match Winner (2-Way)",
        [(side_a, p_a_win), (side_b, 1.0 - p_a_win)],
        f"Exact Bo{best_of} {unit_name.lower()} Markov chain (q={q:.3f})",
    )
    hc = make_market(
        "handicap",
        f"{unit_name} Handicap ({handicap_line:.1f})",
        [(f"{fav} -{handicap_line:.1f} {unit_name}s", p_fav_cov), (f"{dog} +{handicap_line:.1f} {unit_name}s", 1.0 - p_fav_cov)],
        f"Exact Bo{best_of} scoreline tail P(diff > {handicap_line:.1f})",
    )
    tot = make_market(
        "total",
        f"Total {unit_name}s ({total_line:.1f})",
        [(f"Over {total_line:.1f} {unit_name}s", p_over), (f"Under {total_line:.1f} {unit_name}s", 1.0 - p_over)],
        f"Exact Bo{best_of} length distribution",
    )
    deriv = make_market(
        "derivative",
        f"Opening {unit_name} Winner",
        [(f"{side_a} {unit_name} 1", q), (f"{side_b} {unit_name} 1", 1.0 - q)],
        f"Single-{unit_name.lower()} win probability q={q:.3f}",
    )
    return [mw, hc, tot, deriv]


def plackett_luce_markets(
    event_title: str,
    runners: list[tuple[str, float]],
    *,
    h2h_pair: tuple[int, int] = (0, 1),
    total_label: str = "Winning Margin / Time",
    total_outcomes: tuple[tuple[str, float], tuple[str, float]] = (("Over Line", 0.52), ("Under Line", 0.48)),
    top_k_label: str = "Top-2 / Podium Finish (Yes/No)",
    focus_idx: int = 0,
    top_k: int = 3,
) -> list[dict]:
    """Exact Plackett-Luce multi-runner origination for Greyhounds, Golf, and Motor Racing."""
    weights = [max(float(w), 1e-5) for _, w in runners]
    names = [n for n, _ in runners]
    mw = make_market(
        "match_winner",
        f"{event_title} — Outright Winner",
        list(zip(names, weights)),
        "Plackett-Luce normalized strength ratings (Σp = 1.0000)",
    )

    i, j = h2h_pair
    wi, wj = weights[i], weights[j]
    h2h = make_market(
        "handicap",
        f"Head-to-Head Matchup: {names[i]} vs {names[j]}",
        [(names[i], wi / (wi + wj)), (names[j], wj / (wi + wj))],
        "Conditional Plackett-Luce pairwise dominance w_i / (w_i + w_j)",
    )

    tot = make_market("total", total_label, list(total_outcomes), "Official pace / scoring dispersion")

    total_w = sum(weights)
    wf = weights[focus_idx]
    p_top = wf / total_w
    if top_k >= 2:
        for a in range(len(weights)):
            if a == focus_idx:
                continue
            rem1 = total_w - weights[a]
            p_2nd_given_a = (weights[a] / total_w) * (wf / rem1)
            p_top += p_2nd_given_a
            if top_k >= 3:
                for b in range(len(weights)):
                    if b in (focus_idx, a):
                        continue
                    rem2 = rem1 - weights[b]
                    p_top += (weights[a] / total_w) * (weights[b] / rem1) * (wf / rem2)
    p_top = min(max(p_top, 0.05), 0.95)
    deriv = make_market(
        "derivative",
        f"{names[focus_idx]} — {top_k_label}",
        [(f"{names[focus_idx]} Yes", p_top), (f"{names[focus_idx]} No", 1.0 - p_top)],
        f"Exact Plackett-Luce Top-{top_k} integral without replacement",
    )
    return [mw, h2h, tot, deriv]

#!/usr/bin/env python3
"""Transparent, margin-free line origination for Board AF.

These are model estimates, not observed bookmaker prices.  No OLBG or bookmaker
price enters any calculation.  Each provider supplies official numeric inputs;
this module only performs disclosed mathematics on those inputs.
"""
from __future__ import annotations

import math
from typing import Any

from common import focus_price, price


def selection(label: str, probability: float) -> dict[str, Any]:
    return {"label": label, **price(probability)}


def two_way(name: str, first: str, second: str, p_first: float, **extra: Any) -> dict[str, Any]:
    p_first = min(0.985, max(0.015, p_first))
    return {
        "market": name,
        **extra,
        "selections": [selection(first, p_first), selection(second, 1.0 - p_first)],
    }


def poisson(lam: float, k: int) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def score_grid(home_lambda: float, away_lambda: float, limit: int = 20) -> list[tuple[int, int, float]]:
    grid = [(h, a, poisson(home_lambda, h) * poisson(away_lambda, a))
            for h in range(limit + 1) for a in range(limit + 1)]
    total = sum(p for _, _, p in grid)
    return [(h, a, p / total) for h, a, p in grid]


def scoring_markets(
    home: str,
    away: str,
    home_lambda: float,
    away_lambda: float,
    p_home_match: float,
    handicap_name: str,
    total_name: str,
) -> dict[str, Any]:
    grid = score_grid(home_lambda, away_lambda)
    p_home_less_1_5 = sum(p for h, a, p in grid if h - a >= 2)
    total_lambda = home_lambda + away_lambda
    total_line = math.floor(total_lambda) + 0.5
    p_over = sum(p for h, a, p in grid if h + a > total_line)
    return {
        "match_winner": two_way("Match Winner (including extra time)", home, away, p_home_match),
        "handicap": two_way(handicap_name, f"{home} -1.5", f"{away} +1.5", p_home_less_1_5, line=-1.5),
        "total": two_way(total_name, f"Over {total_line}", f"Under {total_line}", p_over, line=total_line),
    }


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def basketball_markets(home: str, away: str, margin: float, total: float,
                       margin_sigma: float, total_sigma: float) -> dict[str, Any]:
    p_home = normal_cdf(margin / margin_sigma)
    spread = -(math.floor(abs(margin)) + 0.5) if margin >= 0 else math.floor(abs(margin)) + 0.5
    p_home_cover = normal_cdf((margin + spread) / margin_sigma)
    total_line = math.floor(total) + 0.5
    p_over = normal_cdf((total - total_line) / total_sigma)
    return {
        "match_winner": two_way("Match Winner (including overtime)", home, away, p_home),
        "handicap": two_way("Point Spread", f"{home} {spread:+.1f}", f"{away} {-spread:+.1f}", p_home_cover, line=spread),
        "total": two_way("Match Total Points", f"Over {total_line}", f"Under {total_line}", p_over, line=total_line),
    }


def moneyline_only(home: str, away: str, p_home: float, market_name: str = "Match Winner") -> dict[str, Any]:
    return {"match_winner": two_way(market_name, home, away, p_home)}


def attach_pick(row: dict[str, Any], high_evidence: bool) -> None:
    row["high_evidence"] = bool(high_evidence)
    market = row.get("markets", {}).get("match_winner")
    if not market:
        row["pick"] = None
        return
    home, away = market["selections"]
    chosen = max((home, away), key=lambda item: item["probability"])
    p = chosen["probability"]
    if p >= 0.70 and high_evidence:
        confidence = "High"
    elif p >= 0.58:
        confidence = "Medium"
    else:
        confidence = "Low"
    row["pick"] = {
        "market": "Match Winner",
        "selection": chosen["label"],
        "probability": p,
        "decimal": chosen["decimal"],
        "american": chosen["american"],
        "confidence": confidence,
        "focus_eligible": confidence == "High" and focus_price(chosen),
        "high_evidence": high_evidence,
    }


def investigated(sport: str, originated: list[str], reason: str = "") -> list[dict[str, str]]:
    core = ["Match Winner", "Handicap / Spread", "Match Total", "Sport-specific derivatives"]
    result = []
    for name in core:
        done = any(name.split(" /")[0].lower() in item.lower() or item.lower() in name.lower() for item in originated)
        result.append({
            "market": name,
            "status": "originated" if done else "investigated — not originated",
            "reason": "" if done else (reason or "The captured official evidence does not support a defensible two-sided price; left blank."),
        })
    return result

"""Market construction, odds conversion and pick grading.

All probabilities are produced by pipeline.model from official results. Prices are our
own: fair decimal odds (1/p) with a fixed 4.5% theoretical hold applied across the two
sides of each market (see config.THEORETICAL_HOLD).
"""
from __future__ import annotations

import math

from . import config
from .model import Fit, EDGE_THRESHOLDS

MARKET_LABELS = {
    "moneyline": "Match winner (moneyline)",
    "handicap": "Handicap",
    "total": "Match total (over/under)",
}

SPORT_HANDICAP_NAME = {
    "basketball": "Point spread",
    "ice_hockey": "Puck line",
    "baseball": "Run line",
}

SPORT_UNIT = {"basketball": "pts", "ice_hockey": "goals", "baseball": "runs"}


# ---------------------------------------------------------------------------
# odds helpers
# ---------------------------------------------------------------------------
def price_from_prob(prob: float, hold: float = config.THEORETICAL_HOLD) -> float:
    """Decimal price for one side of a two-way market carrying `hold` overround."""
    p = min(0.999, max(0.001, prob))
    # A decimal price below 1.01 is not a real market; cap the quote.
    return round(max(1.01, 1.0 / (p * (1.0 + hold))), 3)


def fair_from_prob(prob: float) -> float:
    p = min(0.999, max(0.001, prob))
    return round(1.0 / p, 3)


def american(decimal_odds: float) -> int:
    if decimal_odds >= 2.0:
        return int(round((decimal_odds - 1.0) * 100))
    return -int(round(100.0 / (decimal_odds - 1.0)))


def fmt_american(decimal_odds: float) -> str:
    a = american(decimal_odds)
    return f"+{a}" if a > 0 else str(a)


def round_half(value: float) -> float:
    """Nearest half-point, always on a half so the market cannot push."""
    sign = -1.0 if value < 0 else 1.0
    return sign * (math.floor(abs(value)) + 0.5)


def total_line(value: float) -> float:
    return math.floor(value) + 0.5


# ---------------------------------------------------------------------------
# market construction
# ---------------------------------------------------------------------------
def _selection(name: str, side: str, prob: float) -> dict:
    price = price_from_prob(prob)
    return {
        "name": name,
        "side": side,
        "prob": round(prob, 4),
        "prob_pct": round(prob * 100, 1),
        "fair_decimal": fair_from_prob(prob),
        "price_decimal": price,
        "american": fmt_american(price),
        "implied_pct": round(100.0 / price, 1),
    }


def _opening_adjusted(opening: Fit, current: Fit) -> Fit:
    """When the opener is neutral, borrow league scoring levels from the current fit."""
    if opening.kind == "opening" and not opening.ratings:
        opening.league_total = current.league_total
        opening.sigma_total = current.sigma_total
        opening.resid_total = current.resid_total
        opening.resid_margin = current.resid_margin
    return opening


def build_markets(fixture: dict, current: Fit, opening: Fit, form: dict) -> dict:
    sport = fixture["sport"]
    home_id, away_id = fixture["home"]["id"], fixture["away"]["id"]
    home_name, away_name = fixture["home"]["name"], fixture["away"]["name"]

    cur = current.expected(home_id, away_id)
    opening = _opening_adjusted(opening, current)
    opn = opening.expected(home_id, away_id)

    p_home = current.p_margin_gt(cur["margin"], 0.0)
    p_away = 1.0 - p_home
    ml_home = _selection(home_name, "home", p_home)
    ml_away = _selection(away_name, "away", p_away)

    # ---- handicap ------------------------------------------------------
    cur_line_home = -round_half(cur["margin"])
    open_line_home = -round_half(opn["margin"])
    p_home_cur = current.p_margin_gt(cur["margin"], -cur_line_home)
    hcap = {
        "line_home": cur_line_home,
        "line_away": -cur_line_home,
        "opening_line_home": open_line_home,
        "opening_line_away": -open_line_home,
        "name": SPORT_HANDICAP_NAME[sport],
        "selections": [
            _selection(f"{home_name} {cur_line_home:+.1f}", "home", p_home_cur),
            _selection(f"{away_name} {-cur_line_home:+.1f}", "away", 1.0 - p_home_cur),
        ],
        "opening_selections": [
            _selection(
                f"{home_name} {open_line_home:+.1f}",
                "home",
                current.p_margin_gt(cur["margin"], -open_line_home),
            ),
            _selection(
                f"{away_name} {-open_line_home:+.1f}",
                "away",
                1.0 - current.p_margin_gt(cur["margin"], -open_line_home),
            ),
        ],
        "alternates": _handicap_alternates(current, cur, cur_line_home, home_name, away_name),
    }

    # ---- total ---------------------------------------------------------
    cur_total = total_line(cur["total"])
    open_total = total_line(opn["total"])
    p_over_cur = current.p_total_gt(cur["total"], cur_total)
    total = {
        "line": cur_total,
        "opening_line": open_total,
        "name": "Match total",
        "selections": [
            _selection(f"Over {cur_total}", "over", p_over_cur),
            _selection(f"Under {cur_total}", "under", 1.0 - p_over_cur),
        ],
        "opening_selections": [
            _selection(f"Over {open_total}", "over", current.p_total_gt(cur["total"], open_total)),
            _selection(
                f"Under {open_total}", "under", 1.0 - current.p_total_gt(cur["total"], open_total)
            ),
        ],
        "alternates": _total_alternates(current, cur, cur_total),
    }

    markets = {
        "moneyline": {
            "label": MARKET_LABELS["moneyline"],
            "line": None,
            "selections": [ml_home, ml_away],
        },
        "handicap": {"label": f"{SPORT_HANDICAP_NAME[sport]} ({MARKET_LABELS['handicap']})", **hcap},
        "total": {"label": MARKET_LABELS["total"], **total},
    }

    # ---- picks ---------------------------------------------------------
    winner = "home" if p_home >= p_away else "away"
    winner_pick = _grade_winner(
        fixture, current, markets["moneyline"]["selections"], winner, opn, bool(opening.ratings)
    )

    edges = _market_edges(sport, cur, opn, current, opening)
    market_picks = []
    neutral_opener = not bool(opening.ratings)
    for pick in (
        _handicap_pick(fixture, current, markets["handicap"], edges, form, neutral_opener),
        _total_pick(fixture, current, markets["total"], edges, form, neutral_opener),
    ):
        if pick:
            market_picks.append(pick)

    for pick in [winner_pick] + market_picks:
        pick["confidence_rank"] = CONFIDENCE_RANK[pick["confidence"]]
    all_picks = [winner_pick] + market_picks
    headline = max(all_picks, key=lambda p: (p["confidence_rank"], p["prob"]))
    return {
        "expected": {
            "current": {k: round(v, 2) for k, v in cur.items()},
            "opening": {k: round(v, 2) for k, v in opn.items()},
        },
        "se": {
            "margin": round(current.se_margin(), 2),
            "total": round(current.se_total(), 2),
        },
        "markets": markets,
        "winner_pick": winner_pick,
        "market_picks": market_picks,
        "headline_pick": headline,
        "edge": edges,
    }


def _handicap_alternates(current: Fit, cur: dict, line_home: float, home: str, away: str) -> list:
    out = []
    for delta in (-1.0, 1.0):
        lh = line_home + delta
        p = current.p_margin_gt(cur["margin"], -lh)
        out.append(
            {
                "line_home": lh,
                "selections": [
                    _selection(f"{home} {lh:+.1f}", "home", p),
                    _selection(f"{away} {-lh:+.1f}", "away", 1.0 - p),
                ],
            }
        )
    return out


def _total_alternates(current: Fit, cur: dict, line: float) -> list:
    out = []
    for delta in (-1.0, 1.0):
        lt = line + delta
        p = current.p_total_gt(cur["total"], lt)
        out.append(
            {
                "line": lt,
                "selections": [
                    _selection(f"Over {lt}", "over", p),
                    _selection(f"Under {lt}", "under", 1.0 - p),
                ],
            }
        )
    return out


def _market_edges(sport: str, cur: dict, opn: dict, current: Fit, opening: Fit) -> dict:
    return {
        "margin": round(cur["margin"] - opn["margin"], 2),
        "total": round(cur["total"] - opn["total"], 2),
        "threshold_handicap": EDGE_THRESHOLDS[sport]["handicap"],
        "threshold_total": EDGE_THRESHOLDS[sport]["total"],
        "opening_basis": opening.notes[-1] if opening.notes else "previous season",
    }


def _grade_winner(fixture, current: Fit, selections, winner: str, opn: dict,
                  opening_has_ratings: bool) -> dict:
    pick = next(s for s in selections if s["side"] == winner)
    prob = pick["prob"]
    home_id, away_id = fixture["home"]["id"], fixture["away"]["id"]
    n_home = current.games_per_team.get(str(home_id), 0)
    n_away = current.games_per_team.get(str(away_id), 0)
    n = min(n_home, n_away)

    # stability: does the opening model agree on the same winner?
    op_winner = "home" if opn["margin"] >= 0 else "away"
    stable = bool(opening_has_ratings) and op_winner == winner

    conf = _grade(prob, n, stable)
    return {
        "market": "moneyline",
        "market_label": MARKET_LABELS["moneyline"],
        "selection": pick["name"],
        "side": winner,
        "line": None,
        "prob": pick["prob"],
        "prob_pct": pick["prob_pct"],
        "price_decimal": pick["price_decimal"],
        "american": pick["american"],
        "fair_decimal": pick["fair_decimal"],
        "confidence": conf,
        "sample_games_min": n,
        "sample_home": n_home,
        "sample_away": n_away,
        "opening_agrees": stable,
        "rationale_key": "winner",
    }


def _grade(prob: float, n: int, stable: bool) -> str:
    high = config.CONFIDENCE["high"]
    med = config.CONFIDENCE["medium"]
    if prob >= high["min_prob"] and n >= high["min_games"] and stable:
        return "high"
    if prob >= med["min_prob"] and n >= med["min_games"]:
        return "medium"
    return "low"


def _handicap_pick(fixture, current: Fit, market: dict, edges: dict, form: dict,
                   neutral_opener: bool = False) -> dict | None:
    edge = edges["margin"]
    if abs(edge) < edges["threshold_handicap"]:
        return None
    side = "home" if edge > 0 else "away"
    sel = next(s for s in market["opening_selections"] if s["side"] == side)
    home_id, away_id = fixture["home"]["id"], fixture["away"]["id"]
    n = min(current.games_per_team.get(str(home_id), 0), current.games_per_team.get(str(away_id), 0))
    ratio = abs(edge) / edges["threshold_handicap"]
    conf = _grade_market(sel["prob"], n, ratio, neutral_opener)
    return {
        "market": "handicap",
        "market_label": market["name"],
        "selection": sel["name"],
        "side": side,
        "line": market["opening_line_home"] if side == "home" else market["opening_line_away"],
        "prob": sel["prob"],
        "prob_pct": sel["prob_pct"],
        "price_decimal": sel["price_decimal"],
        "american": sel["american"],
        "fair_decimal": sel["fair_decimal"],
        "confidence": conf,
        "sample_games_min": n,
        "edge": edge,
        "threshold": edges["threshold_handicap"],
        "current_line": market["line_home"] if side == "home" else market["line_away"],
        "rationale_key": "handicap_moved",
    }


def _total_pick(fixture, current: Fit, market: dict, edges: dict, form: dict,
                neutral_opener: bool = False) -> dict | None:
    edge = edges["total"]
    if abs(edge) < edges["threshold_total"]:
        return None
    side = "over" if edge > 0 else "under"
    sel = next(s for s in market["opening_selections"] if s["side"] == side)
    home_id, away_id = fixture["home"]["id"], fixture["away"]["id"]
    n = min(current.games_per_team.get(str(home_id), 0), current.games_per_team.get(str(away_id), 0))
    ratio = abs(edge) / edges["threshold_total"]
    conf = _grade_market(sel["prob"], n, ratio, neutral_opener)
    return {
        "market": "total",
        "market_label": market["name"],
        "selection": sel["name"],
        "side": side,
        "line": market["opening_line"],
        "prob": sel["prob"],
        "prob_pct": sel["prob_pct"],
        "price_decimal": sel["price_decimal"],
        "american": sel["american"],
        "fair_decimal": sel["fair_decimal"],
        "confidence": conf,
        "sample_games_min": n,
        "edge": edge,
        "threshold": edges["threshold_total"],
        "current_line": market["line"],
        "rationale_key": "total_moved",
    }


def _grade_market(prob: float, n: int, ratio: float, neutral_opener: bool = False) -> str:
    if (not neutral_opener and ratio >= 2.0 and prob >= 0.60
            and n >= config.CONFIDENCE["high"]["min_games"]):
        return "high"
    if ratio >= 1.0 and prob >= 0.55 and n >= config.CONFIDENCE["medium"]["min_games"]:
        return "medium"
    return "low"


CONFIDENCE_RANK = {"high": 3, "medium": 2, "low": 1}


def add_ranks(result: dict) -> dict:
    for key in ("winner_pick", "headline_pick"):
        pick = result.get(key)
        if pick:
            pick["confidence_rank"] = CONFIDENCE_RANK[pick["confidence"]]
    for pick in result.get("market_picks", []):
        pick["confidence_rank"] = CONFIDENCE_RANK[pick["confidence"]]
    return result

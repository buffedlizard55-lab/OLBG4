"""Snooker origination: strength, frame distribution, markets and grading.

Inputs are the season figures the WST Match Centre publishes for each player — matches
played, match win rate, points scored, 50+ breaks, 100+ breaks, average shot time — plus,
where the player appears on it, the WST world-ranking position and prize money. Nothing
here is guessed: a player with no captured stats (Jordan Brown and Scott Donaldson) gets a
50/50 projection, blank inputs and an explicit flag.

Model
-----
1.  **Win-rate model (publishes the price).** Season match win rate is shrunk toward 50%
    with ``SHRINK_MATCHES`` pseudo-matches, converted to a logit, and the two logits are
    differenced Bradley-Terry style:  p = sigmoid(theta_home - theta_away).
2.  **Scoring model (stability check only).** Points scored per match, shrunk toward the
    mean of the captured players, has to agree on the side. It is a different statistic
    from the win rate, so agreement is evidence the win rate is not noise.

The match price is a first-to-four market, so the moneyline is exact. Frame handicap and
total-frames markets are priced from the implied per-frame probability, found by
inverting the best-of-seven binomial so that the frame-level model reproduces the match
probability exactly. That keeps every market internally consistent with the headline.
"""
from __future__ import annotations

import math
from statistics import NormalDist

CONSTANTS = {
    "shrink_matches": {
        "value": 8,
        "why": "Pseudo-matches at .500 added to each player's season record. An 18-match "
               "sample is informative but not conclusive, so a 43% record is pulled up and "
               "a 69% record pulled down before the logit is taken.",
    },
    "shrink_points": {
        "value": 8,
        "why": "Pseudo-matches at the captured-player mean points-per-match, used only for "
               "the independent scoring check.",
    },
    "best_of": {
        "value": 7,
        "why": "First to four frames, as observed from every completed match on the official "
               "WST matches page for this event (see desk/data/snooker_fixtures.json, "
               "format_note, and flagged item S-14).",
    },
    "hold": {
        "value": 0.0,
        "why": "Fair opening lines, same policy as the team sports: decimal price = 1/probability.",
    },
}


def _logit(p: float) -> float:
    return math.log(p / (1 - p))


def _sigmoid(x: float) -> float:
    return 1 / (1 + math.exp(-x))


def _binomial(n: int, k: int) -> int:
    return math.comb(n, k)


def frame_distribution(p_frame: float, best_of: int = 7) -> dict:
    """Exact distribution of the completed match under a fixed per-frame probability."""
    need = (best_of + 1) // 2
    # winner's frames are always `need`; the loser's frame count carries the information
    a_win = {}
    b_win = {}
    for j in range(need):
        pa = _binomial(need - 1 + j, j) * p_frame ** need * (1 - p_frame) ** j
        pb = _binomial(need - 1 + j, j) * (1 - p_frame) ** need * p_frame ** j
        a_win[j] = pa
        b_win[j] = pb
    totals: dict[int, float] = {}
    for j, pa in a_win.items():
        totals[need + j] = totals.get(need + j, 0.0) + pa
    for j, pb in b_win.items():
        totals[need + j] = totals.get(need + j, 0.0) + pb
    return {"a_win_by_loser_frames": a_win, "b_win_by_loser_frames": b_win, "totals": totals,
            "p_a": sum(a_win.values())}


def implied_frame_prob(p_match: float, best_of: int = 7) -> float:
    """Per-frame probability whose best-of-N match probability equals `p_match`."""
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if frame_distribution(mid, best_of)["p_a"] < p_match:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def player_strength(stats: dict | None, mean_ppm: float) -> dict:
    if not stats:
        return {"matches": 0, "wr_shrunk": 0.5, "theta": 0.0, "ppm_shrunk": mean_ppm,
                "available": False}
    m = stats["matches"]
    w = stats["win_pct"] / 100.0
    wr = (w * m + 0.5 * CONSTANTS["shrink_matches"]["value"]) / (m + CONSTANTS["shrink_matches"]["value"])
    ppm = stats["points"] / m
    k = CONSTANTS["shrink_points"]["value"]
    ppm_s = (ppm * m + mean_ppm * k) / (m + k)
    return {"matches": m, "win_pct": stats["win_pct"], "wr_shrunk": wr, "theta": _logit(wr),
            "points": stats["points"], "ppm": round(ppm, 1), "ppm_shrunk": ppm_s,
            "fifties": stats["fifties"], "hundreds": stats["hundreds"],
            "ast": stats["ast"], "rank": stats["rank"], "prize": stats["prize"],
            "available": True}


def mean_points_per_match(fixtures: list[dict]) -> float:
    tot = n = 0
    for fx in fixtures:
        for side in ("home_stats", "away_stats"):
            s = fx.get(side)
            if s:
                tot += s["points"]
                n += s["matches"]
    return tot / n if n else 6000 / 20


def projection(fx: dict, home: dict, away: dict) -> dict:
    p_home = _sigmoid(home["theta"] - away["theta"])
    p_frame = implied_frame_prob(p_home, CONSTANTS["best_of"]["value"])
    dist = frame_distribution(p_frame, CONSTANTS["best_of"]["value"])
    scoring_agrees = (home["ppm_shrunk"] > away["ppm_shrunk"]) == (p_home > 0.5)
    return {
        "p_home": p_home,
        "p_frame": p_frame,
        "dist": dist,
        "expected_frames": sum(k * v for k, v in dist["totals"].items()),
        "scoring_agrees": scoring_agrees if (home["available"] and away["available"]) else False,
        "available": home["available"] and away["available"],
    }


def price(prob: float) -> float:
    return round(1.0 / prob, 3)


def fmt_american(decimal_odds: float) -> str:
    if decimal_odds >= 2.0:
        return f"+{round((decimal_odds - 1) * 100)}"
    return f"{round(-100 / (decimal_odds - 1))}"


def in_band(decimal_odds: float) -> bool:
    return 1.40 <= decimal_odds <= 101.0


def markets(fx: dict, proj: dict) -> list[dict]:
    out: list[dict] = []

    def add(market, label, selection, side, prob, line=None, alternate=False):
        pr = price(prob) if prob > 0 else 101.0
        out.append({
            "market": market, "market_label": label, "selection": selection, "side": side,
            "line": line, "prob": prob, "prob_pct": round(prob * 100, 1),
            "price_decimal": pr, "american": fmt_american(pr),
            "implied_pct": round(100.0 / pr, 1), "in_band": in_band(pr),
            "alternate_line": alternate, "note": "",
        })

    p_home = proj["p_home"]
    add("moneyline", "Match winner (moneyline)", fx["home"], "home", p_home)
    add("moneyline", "Match winner (moneyline)", fx["away"], "away", 1 - p_home)

    # frame handicap: probability of covering, taken from the exact distribution
    for line in (1.5, 2.5):
        cover_home = sum(
            v for j, v in proj["dist"]["a_win_by_loser_frames"].items() if (4 - j) > line
        )
        label = "Frame handicap" + (" (alternate)" if line != 1.5 else "")
        add("handicap", label, f"{fx['home']} -{line}", "home", cover_home, line=-line,
            alternate=line != 1.5)
        add("handicap", label, f"{fx['away']} +{line}", "away", 1 - cover_home, line=line,
            alternate=line != 1.5)

    for line, alt in ((4.5, False), (5.5, True)):
        over = sum(v for k, v in proj["dist"]["totals"].items() if k > line)
        label = "Total frames (over/under)" + (" (alternate line)" if alt else "")
        add("total", label, f"Over {line}", "over", over, line=line, alternate=alt)
        add("total", label, f"Under {line}", "under", 1 - over, line=line, alternate=alt)
    return out


def grade(sel: dict, sample_min: int, agree: bool, available: bool) -> dict:
    p = sel["prob"]
    prob_ok = p >= 0.70
    if not available:
        return {"confidence": "Low", "confidence_rank": 1,
                "high_reason": "no season stats captured for one of the two players, so no strength "
                               "estimate is published and the line is a 50/50 baseline",
                "band_status": "in band" if sel["in_band"] else "outside -250..+10000",
                "publishable": False, "sample_games_min": sample_min, "stability_agrees": False}
    if prob_ok and sel["in_band"] and sample_min >= 10 and agree:
        return {"confidence": "High", "confidence_rank": 3,
                "high_reason": f"model probability {p*100:.1f}% clears 70.0%; price {sel['american']} "
                               f"sits inside the -250..+10000 band; both players have {sample_min}+ "
                               f"matches this season; the independent points-per-match check agrees",
                "band_status": "in band", "publishable": True,
                "sample_games_min": sample_min, "stability_agrees": True}
    if prob_ok and not sel["in_band"]:
        return {"confidence": "High", "confidence_rank": 3,
                "high_reason": f"model probability {p*100:.1f}% clears 70.0% but the fair price "
                               f"{sel['american']} is shorter than -250 and is withheld from the "
                               f"published set",
                "band_status": "outside -250..+10000 (shorter than -250)", "publishable": False,
                "sample_games_min": sample_min, "stability_agrees": agree}
    if prob_ok and not agree:
        return {"confidence": "Medium", "confidence_rank": 2,
                "high_reason": f"model probability {p*100:.1f}% clears 70.0% but the independent "
                               f"points-per-match check disagrees",
                "band_status": "in band" if sel["in_band"] else "outside -250..+10000",
                "publishable": False, "sample_games_min": sample_min, "stability_agrees": False}
    if prob_ok and sample_min < 10:
        return {"confidence": "Medium", "confidence_rank": 2,
                "high_reason": f"model probability {p*100:.1f}% clears 70.0% but the smaller sample "
                               f"is only {sample_min} matches",
                "band_status": "in band" if sel["in_band"] else "outside -250..+10000",
                "publishable": False, "sample_games_min": sample_min, "stability_agrees": agree}
    level = "Medium" if p >= 0.60 else "Low"
    return {"confidence": level, "confidence_rank": 2 if level == "Medium" else 1,
            "high_reason": f"model probability {p*100:.1f}% is {'between 60.0% and 69.9%' if level == 'Medium' else 'below 60.0%'}",
            "band_status": "in band" if sel["in_band"] else "outside -250..+10000",
            "publishable": False, "sample_games_min": sample_min, "stability_agrees": agree}

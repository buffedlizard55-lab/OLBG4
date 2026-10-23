#!/usr/bin/env python3
"""Independent fair-price origination for officially reconciled C10 fixtures.

OLBG selections and prices never enter a probability calculation.  They are
compared only after the fair price and match-winner selection have been fixed.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
import hashlib
import math
import re

from common import american, decimal, logistic, norm, normal_cdf, odds_american, split_olbg_sides, utc, words

HIGH_MIN_PROBABILITY = 0.70
HIGH_MIN_AMERICAN = -250
HIGH_MAX_AMERICAN = 10000
SHORTLIST_HOURS = 36


def price(probability: float) -> dict:
    probability = max(0.001, min(0.999, probability))
    return {"probability": round(probability, 5), "fair_american": american(probability),
            "fair_decimal": decimal(probability)}


def market_row(market: str, selection: str, probability: float, line: str = "") -> dict:
    return {"market": market, "selection": selection, "line": line, **price(probability)}


def _recent_form(rows: list[dict]) -> str:
    return "-".join(str(r.get("result") or "?") for r in rows[:5]) if rows else ""


def _recent_sentence(name: str, rows: list[dict]) -> str:
    if not rows:
        return f"No completed-match sequence was available for {name} in the captured schedule window"
    latest = rows[0]
    score = f"{latest.get('team_score')}–{latest.get('opponent_score')}"
    return f"{name}'s latest captured result was {latest.get('result') or 'an ungraded result'} {score} against {latest.get('opponent')}"


def _listed_comparison(event: dict, selection: str) -> dict:
    """Compare only an exact OLBG match-winner selection, never a spread/total."""
    result = {"listed_selection": "", "listed_american": None, "implied_probability": None,
              "probability_edge": None, "comparison": "No exact captured OLBG match-winner price for this selection."}
    market = (event.get("olbg_market") or "").lower()
    tip = event.get("olbg_tip") or ""
    if not event.get("on_olbg") or not tip or not any(k in market for k in ("win match", "match winner", "moneyline", "to win")):
        return result
    sides = split_olbg_sides(event)
    selected_raw = None
    if sides:
        if selection == event.get("official_side1"):
            selected_raw = sides[0] if event.get("official_orientation") == "same" else sides[1]
        elif selection == event.get("official_side2"):
            selected_raw = sides[1] if event.get("official_orientation") == "same" else sides[0]
    exact = norm(tip) == norm(selected_raw or selection)
    if not exact or event.get("olbg_american") is None:
        return result
    listed = int(event["olbg_american"])
    implied = (-listed) / ((-listed) + 100) if listed < 0 else 100 / (listed + 100)
    result.update(listed_selection=tip, listed_american=listed, implied_probability=round(implied, 5),
                  probability_edge=round(event["predicted_probability"] - implied, 5),
                  comparison="Exact captured OLBG match-winner selection; prices are not an input to the fair line.")
    return result


def _team_baselines(events: list[dict]) -> dict[str, float]:
    teams: dict[str, dict[str, dict]] = defaultdict(dict)
    for event in events:
        stats = event.get("official_stats") or {}
        competition = event.get("competition", "")
        for side_key, name_key in (("side1", "official_side1"), ("side2", "official_side2")):
            row = stats.get(side_key) or {}
            if row.get("gp") and row.get("pf") is not None and row.get("pa") is not None:
                teams[competition][event.get(name_key, "")] = row
    result = {}
    for competition, rows in teams.items():
        values = [(r["pf"] + r["pa"]) / r["gp"] for r in rows.values() if r.get("gp")]
        if values:
            result[competition] = sum(values) / len(values)
    return result


def _team_analysis(event: dict, side1: str, side2: str, s1: dict, s2: dict,
                   selection: str, total: float | None, spread_text: str, total_unit: str) -> str:
    p = event["predicted_probability"]
    fair = event["fair_american"]
    variant = int(hashlib.sha256(str(event["event_id"]).encode()).hexdigest()[:4], 16) % 4
    r1, r2 = event["official_stats"].get("recent1", []), event["official_stats"].get("recent2", [])
    form1, form2 = _recent_form(r1), _recent_form(r2)
    rec1, rec2 = f"{s1['wins']}-{s1['losses']}", f"{s2['wins']}-{s2['losses']}"
    scoring1 = f"{s1['pf_pg']:.1f} scored and {s1['pa_pg']:.1f} conceded per game"
    scoring2 = f"{s2['pf_pg']:.1f} scored and {s2['pa_pg']:.1f} conceded per game"
    latest = _recent_sentence(side1 if selection == side1 else side2, r1 if selection == side1 else r2)
    if "World Series" in event.get("competition", ""):
        home = event["official_detail"].get("home", "")
        pitchers = []
        # Probable pitchers are attached by the builder when present; absent names
        # are not replaced with speculative starters.
        if event["official_stats"].get("side1_probable_pitcher"):
            pitchers.append(f"{side1} list {event['official_stats']['side1_probable_pitcher']}")
        if event["official_stats"].get("side2_probable_pitcher"):
            pitchers.append(f"{side2} list {event['official_stats']['side2_probable_pitcher']}")
        pitcher_text = "; ".join(pitchers) if pitchers else "No probable pitcher is named for both sides in the captured feed"
        return (f"{selection} is the match-winner selection at {p:.1%}, equivalent to fair American odds {fair:+d}. "
                f"{side1} own a {rec1} season record and {side2} stand at {rec2}; the official run returns are "
                f"{s1['pf']}–{s1['pa']} and {s2['pf']}–{s2['pa']}, respectively. {pitcher_text}. "
                f"The projected total is {total:.1f} runs, with {spread_text} as the separate run-line assessment.")
    if variant == 0:
        return (f"{selection} gets the match-winner call, priced independently at {p:.1%} ({fair:+d} American). "
                f"{side1} are {rec1} with {scoring1}, while {side2} are {rec2} with {scoring2}. "
                f"{latest}. Recent captured form reads {form1 or 'unavailable'} for {side1} and {form2 or 'unavailable'} for {side2}. "
                f"The combined-{total_unit} projection is {total:.1f}; {spread_text} completes the handicap assessment.")
    if variant == 1:
        return (f"The official scoring and results point to {selection} at {p:.1%}; the corresponding fair price is {fair:+d}. "
                f"For context, {side1}'s {rec1} record accompanies {scoring1}. {side2} counter at {rec2} and {scoring2}. "
                f"{latest}. The total projection is {total:.1f}, while {spread_text} is the handicap position.")
    if variant == 2:
        return (f"At fair American odds {fair:+d}, {selection} carries a {p:.1%} match-win estimate. "
                f"The two official returns are {rec1} and {scoring1} for {side1}, against {rec2} and {scoring2} for {side2}. "
                f"{latest}. Those same scoring inputs produce a {total:.1f} total; {spread_text} is kept as a distinct handicap market.")
    return (f"{selection} is preferred at {p:.1%}, or {fair:+d} on the fair American scale. "
            f"{side1} have gone {rec1}, compared with {rec2} for {side2}; their respective per-game scoring balances are "
            f"{s1['net_pg']:+.1f} and {s2['net_pg']:+.1f}. {latest}. "
            f"The scoring projection settles at {total:.1f} total {total_unit}, with {spread_text} for the separate handicap.")


def originate_team(event: dict, baseline: float | None) -> bool:
    stats = event.get("official_stats") or {}
    s1, s2 = stats.get("side1"), stats.get("side2")
    detail = event.get("official_detail") or {}
    if not s1 or not s2 or not s1.get("gp") or not s2.get("gp"):
        return False
    if s1.get("pf") is None or s2.get("pf") is None:
        return False
    league = detail.get("league", "")
    prior = {"NBA": 12.0, "EuroLeague": 8.0, "EuroCup": 8.0, "NHL": 5.0, "MLB": 6.0}.get(league, 8.0)
    net_coef = {"NBA": 0.045, "EuroLeague": 0.055, "EuroCup": 0.055,
                "NHL": 0.32, "MLB": 0.16}.get(league, 0.05)
    def rating(s):
        gp = float(s["gp"])
        shrunk_win = (float(s["wins"]) + prior * 0.5) / (gp + prior)
        shrunk_net = float(s["net_pg"]) * gp / (gp + prior)
        return 3.0 * (shrunk_win - 0.5) + net_coef * shrunk_net
    logit = rating(s1) - rating(s2) + float(detail.get("home_advantage_logit", 0.0))
    p1 = logistic(logit)
    side1, side2 = event["official_side1"], event["official_side2"]
    selection = side1 if p1 >= 0.5 else side2
    p = max(p1, 1 - p1)
    event.update(prediction=selection, predicted_probability=round(p, 5),
                 opponent_probability=round(1 - p, 5), fair_american=american(p),
                 fair_decimal=decimal(p), side1_probability=round(p1, 5),
                 side2_probability=round(1 - p1, 5))
    markets = [market_row("Match winner", side1, p1), market_row("Match winner", side2, 1 - p1)]
    # Expected margin uses the same shrunk official scoring differential and a
    # disclosed competition home-court/ice/field constant.
    def shrunk_net(s):
        return float(s["net_pg"]) * float(s["gp"]) / (float(s["gp"]) + prior)
    mu = shrunk_net(s1) - shrunk_net(s2) + float(detail.get("home_advantage_points", 0.0))
    sd = float(detail.get("margin_sd", 10.0))
    if league in {"NHL", "MLB"}:
        handicap = 1.5
    else:
        handicap = max(0.5, math.floor(abs(mu)) + 0.5)
    if mu >= 0:
        favorite, underdog, sign = side1, side2, -1
        favorite_mu = mu
    else:
        favorite, underdog, sign = side2, side1, 1
        favorite_mu = -mu
    cover = 1 - normal_cdf((handicap - favorite_mu) / sd)
    unit = "goals" if league == "NHL" else "runs" if league == "MLB" else "points"
    markets += [market_row("Handicap", f"{favorite} -{handicap:.1f}", cover, f"-{handicap:.1f}"),
                market_row("Handicap", f"{underdog} +{handicap:.1f}", 1 - cover, f"+{handicap:.1f}")]
    total1 = (float(s1["pf"]) + float(s1["pa"])) / float(s1["gp"])
    total2 = (float(s2["pf"]) + float(s2["pa"])) / float(s2["gp"])
    observed = (total1 + total2) / 2
    min_gp = min(float(s1["gp"]), float(s2["gp"]))
    total_weight = min_gp / (min_gp + (10.0 if league == "NBA" else 6.0))
    base = baseline if baseline is not None else observed
    expected_total = total_weight * observed + (1 - total_weight) * base
    total_line = round(expected_total * 2) / 2
    if float(total_line).is_integer():
        total_line += 0.5
    total_sd = float(detail.get("total_sd", 15.0))
    over = 1 - normal_cdf((total_line - expected_total) / total_sd)
    total_unit = "goals" if league == "NHL" else "runs" if league == "MLB" else "points"
    markets += [market_row("Total", f"Over {total_line:.1f} {total_unit}", over, f"{total_line:.1f}"),
                market_row("Total", f"Under {total_line:.1f} {total_unit}", 1 - over, f"{total_line:.1f}")]
    spread_text = f"{favorite} -{handicap:.1f} {unit}"
    event.update(markets=markets, projected_margin=round(mu, 3), projected_total=round(expected_total, 3),
                 market_review=[
                     {"market": "Match winner", "status": "Originated from two-sided official records and scoring."},
                     {"market": "Handicap/spread", "status": f"Originated at {spread_text}."},
                     {"market": "Total", "status": f"Originated at {total_line:.1f} {total_unit}."},
                     {"market": "Player props", "status": "Investigated; no two-sided official player-prop inputs captured, so no price published."},
                 ])
    min_sample = {"NBA": 8, "NHL": 8, "EuroLeague": 6, "EuroCup": 6, "MLB": 30}.get(league, 8)
    recent_ok = all(stats.get(key) or (stats.get(stat_key) or {}).get("last10")
                    for key, stat_key in (("recent1", "side1"), ("recent2", "side2")))
    enough = min_gp >= min_sample and recent_ok
    if p >= HIGH_MIN_PROBABILITY and enough:
        confidence = "High"
    elif p >= 0.59:
        confidence = "Medium"
    else:
        confidence = "Low"
    if league == "NBA" and min_gp < 8:
        confidence = "Low"
        event.setdefault("flags", []).append("Early-season sample below eight games for at least one side; confidence capped at Low.")
    event["confidence"] = confidence
    event["analysis"] = _team_analysis(event, side1, side2, s1, s2, selection, expected_total, spread_text, total_unit)
    return True


def _solve_unit_probability(match_probability: float, wins_needed: int) -> float:
    def match_p(q):
        return sum(math.comb(wins_needed + k - 1, k) * q ** wins_needed * (1 - q) ** k
                   for k in range(wins_needed))
    lo, hi = 0.0, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if match_p(mid) < match_probability:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _tennis_analysis(event: dict, a: dict, b: dict) -> str:
    side1, side2 = event["official_side1"], event["official_side2"]
    p, fair = event["predicted_probability"], event["fair_american"]
    r1, r2 = a.get("recent", []), b.get("recent", [])
    def form(rows):
        wins = sum(r.get("result") == "W" for r in rows)
        latest = rows[0] if rows else None
        return wins, latest
    w1, l1 = form(r1)
    w2, l2 = form(r2)
    latest = l1 if event["prediction"] == side1 else l2
    latest_text = (f"The selected player's latest completed main-draw match was a "
                   f"{'win' if latest.get('result') == 'W' else 'loss'}, {latest.get('score')}, against {latest.get('opponent')}" if latest else
                   "The captured main-draw feed has no completed match for the selected player")
    return (f"{event['prediction']} is the match-winner selection at {p:.1%}, giving fair American odds {fair:+d}. "
            f"The 19 October official rankings place {side1} No. {a['ranking']} on {a['points']} points and {side2} "
            f"No. {b['ranking']} on {b['points']}. {side1} has {w1} main-draw wins in the captured tournament; "
            f"{side2} has {w2}. {latest_text}. This is {event['official_detail'].get('surface')} court at "
            f"{event['official_detail'].get('tournament')}; set and total-set prices remain separate from the winner call.")


def originate_wta(event: dict) -> bool:
    stats = event.get("official_stats") or {}
    a, b = stats.get("side1"), stats.get("side2")
    if not a or not b or not a.get("points") or not b.get("points"):
        return False
    pa = float(a["points"]) ** 0.75
    pb = float(b["points"]) ** 0.75
    p1 = pa / (pa + pb)
    side1, side2 = event["official_side1"], event["official_side2"]
    selection = side1 if p1 >= 0.5 else side2
    p = max(p1, 1 - p1)
    event.update(prediction=selection, predicted_probability=round(p, 5), opponent_probability=round(1 - p, 5),
                 fair_american=american(p), fair_decimal=decimal(p),
                 side1_probability=round(p1, 5), side2_probability=round(1 - p1, 5))
    q = _solve_unit_probability(p1, 2)
    a20 = q * q
    a21 = 2 * q * q * (1 - q)
    b20 = (1 - q) ** 2
    b21 = 2 * q * (1 - q) ** 2
    third = 2 * q * (1 - q)
    markets = [market_row("Match winner", side1, p1), market_row("Match winner", side2, 1 - p1),
               market_row("Set handicap", f"{side1} -1.5 sets", a20, "-1.5"),
               market_row("Set handicap", f"{side2} +1.5 sets", 1 - a20, "+1.5"),
               market_row("Total sets", "Over 2.5 sets", third, "2.5"),
               market_row("Total sets", "Under 2.5 sets", 1 - third, "2.5"),
               market_row("Correct set score", f"{side1} 2–0", a20, "2–0"),
               market_row("Correct set score", f"{side1} 2–1", a21, "2–1"),
               market_row("Correct set score", f"{side2} 2–0", b20, "0–2"),
               market_row("Correct set score", f"{side2} 2–1", b21, "1–2")]
    event["markets"] = markets
    event["market_review"] = [
        {"market": "Match winner", "status": "Originated from official ranking points dated 2026-10-19."},
        {"market": "Set handicap / correct score", "status": "Originated from the implied independent-set probability."},
        {"market": "Total sets", "status": "Originated; total games is not represented as the same market."},
        {"market": "Game handicap / total games", "status": "Investigated; no official point- or game-level rating inputs captured, so left blank."},
    ]
    enough = len(a.get("recent", [])) >= 2 and len(b.get("recent", [])) >= 2
    event["confidence"] = "High" if p >= HIGH_MIN_PROBABILITY and enough else "Medium" if p >= 0.58 else "Low"
    event["analysis"] = _tennis_analysis(event, a, b)
    return True


def _snooker_analysis(event: dict, a: dict, b: dict) -> str:
    side1, side2 = event["official_side1"], event["official_side2"]
    p, fair = event["predicted_probability"], event["fair_american"]
    variant = int(hashlib.sha256(str(event["event_id"]).encode()).hexdigest()[:4], 16) % 2
    common = (f"{side1}'s official 2026 season return is {a['matchesWon']} wins from {a['matchesPlayed']} matches, "
              f"with {a['pointsScored']} points, {a['fiftyPlusBreaks']} breaks over fifty and a highest break of {a['highestBreak']}. "
              f"{side2} has {b['matchesWon']} wins from {b['matchesPlayed']}, {b['pointsScored']} points, "
              f"{b['fiftyPlusBreaks']} fifty-plus breaks and a {b['highestBreak']} best. ")
    if variant == 0:
        return (f"{event['prediction']} is the match-winner selection at {p:.1%}, or fair American odds {fair:+d}. " + common +
                f"The quarter-final is over {event['official_detail'].get('number_of_frames')} frames. "
                f"Frame-handicap and total-frame prices use the same season evidence but are separate markets; no prior result is invented.")
    return (f"Fair odds of {fair:+d} accompany the {p:.1%} call for {event['prediction']}. " + common +
            f"The official season rankings attached to this match are No. {a.get('ranking') or 'unlisted'} "
            f"and No. {b.get('ranking') or 'unlisted'}. The frame markets are derived independently of OLBG's displayed price.")


def originate_snooker(event: dict) -> bool:
    stats = event.get("official_stats") or {}
    a, b = stats.get("side1"), stats.get("side2")
    if not a or not b or not a.get("matchesPlayed") or not b.get("matchesPlayed"):
        return False
    def logit_rate(s):
        rate = (float(s["matchesWon"]) + 4) / (float(s["matchesPlayed"]) + 8)
        return math.log(rate / (1 - rate))
    ppm_a = float(a["pointsScored"]) / float(a["matchesPlayed"])
    ppm_b = float(b["pointsScored"]) / float(b["matchesPlayed"])
    rank_a = stats.get("side1_ranking") or a.get("ranking") or 80
    rank_b = stats.get("side2_ranking") or b.get("ranking") or 80
    x = logit_rate(a) - logit_rate(b) + 0.0025 * (ppm_a - ppm_b) + 0.002 * (float(rank_b) - float(rank_a))
    p1 = logistic(x)
    side1, side2 = event["official_side1"], event["official_side2"]
    p = max(p1, 1 - p1)
    event.update(prediction=side1 if p1 >= 0.5 else side2, predicted_probability=round(p, 5),
                 opponent_probability=round(1 - p, 5), fair_american=american(p), fair_decimal=decimal(p),
                 side1_probability=round(p1, 5), side2_probability=round(1 - p1, 5))
    frames = int(event["official_detail"].get("number_of_frames") or 11)
    needed = frames // 2 + 1
    q = _solve_unit_probability(p1, needed)
    a_scores = {k: math.comb(needed + k - 1, k) * q ** needed * (1 - q) ** k for k in range(needed)}
    b_scores = {k: math.comb(needed + k - 1, k) * (1 - q) ** needed * q ** k for k in range(needed)}
    a_minus = sum(v for k, v in a_scores.items() if needed - k >= 2)
    over95 = sum(v for k, v in a_scores.items() if needed + k >= 10) + sum(v for k, v in b_scores.items() if needed + k >= 10)
    best_a = max(a_scores, key=a_scores.get)
    best_b = max(b_scores, key=b_scores.get)
    if a_scores[best_a] >= b_scores[best_b]:
        correct_selection, correct_p = f"{side1} {needed}–{best_a}", a_scores[best_a]
    else:
        correct_selection, correct_p = f"{side2} {needed}–{best_b}", b_scores[best_b]
    event["markets"] = [market_row("Match winner", side1, p1), market_row("Match winner", side2, 1 - p1),
                        market_row("Frame handicap", f"{side1} -1.5 frames", a_minus, "-1.5"),
                        market_row("Frame handicap", f"{side2} +1.5 frames", 1 - a_minus, "+1.5"),
                        market_row("Total frames", "Over 9.5 frames", over95, "9.5"),
                        market_row("Total frames", "Under 9.5 frames", 1 - over95, "9.5"),
                        market_row("Correct frame score", correct_selection, correct_p)]
    event["market_review"] = [
        {"market": "Match winner", "status": "Originated from official current-season wins, scoring and rankings."},
        {"market": "Frame handicap / correct score", "status": "Originated from the best-of-11 frame distribution."},
        {"market": "Total frames", "status": "Originated at 9.5; century and maximum-break props not priced without dedicated official prop inputs."},
    ]
    enough = min(int(a["matchesPlayed"]), int(b["matchesPlayed"])) >= 15
    event["confidence"] = "High" if p >= HIGH_MIN_PROBABILITY and enough else "Medium" if p >= 0.58 else "Low"
    event["analysis"] = _snooker_analysis(event, a, b)
    return True


def originate(events: list[dict], cutoff) -> None:
    baselines = _team_baselines(events)
    for event in events:
        event.setdefault("prediction", None)
        event.setdefault("predicted_probability", None)
        event.setdefault("fair_american", None)
        event.setdefault("fair_decimal", None)
        event.setdefault("confidence", None)
        event.setdefault("analysis", "")
        event.setdefault("markets", [])
        event.setdefault("market_review", [])
        event.setdefault("flags", [])
        event["high_focus"] = False
        event["shortlist"] = False
        if event.get("kind") != "match":
            event["market_review"] = [{"market": "Outright", "status": "Listed only; no official two-sided match or full-field official market captured."}]
            continue
        if not event.get("official"):
            event["market_review"] = [{"market": "Match winner / handicap / total", "status": "Not originated: official two-sided reconciliation or required inputs unavailable."}]
            continue
        family = (event.get("official_detail") or {}).get("model_family")
        ok = False
        if family in {"nhl_goals", "mlb_runs", "nba_points", "euro_points"}:
            ok = originate_team(event, baselines.get(event.get("competition", "")))
        elif family == "wta_ranking_points":
            ok = originate_wta(event)
        elif family == "wst_season_stats":
            ok = originate_snooker(event)
        if not ok:
            event["market_review"] = [{"market": "Match winner / handicap / total", "status": "Not originated: required official two-sided statistical fields are incomplete."}]
            event.setdefault("flags", []).append("Official fixture found, but required pricing inputs are incomplete.")
            continue
        event["analysis_word_count"] = len(words(event["analysis"]))
        event["listed_comparison"] = _listed_comparison(event, event["prediction"])
        fair = event.get("fair_american")
        event["high_focus"] = bool(event["confidence"] == "High" and fair is not None
                                   and HIGH_MIN_AMERICAN <= fair <= HIGH_MAX_AMERICAN)
        if event["confidence"] == "High" and not event["high_focus"]:
            event["flags"].append("High confidence, but fair American odds fall outside the requested focus range.")
    # Strongest qualifying matches per covered sport in the daily 36-hour window.
    horizon = cutoff + timedelta(hours=SHORTLIST_HOURS)
    for sport in sorted({e["sport"] for e in events}):
        candidates = [e for e in events if e["sport"] == sport and e["high_focus"]
                      and e.get("start_utc") and utc(e["start_utc"]) <= horizon]
        candidates.sort(key=lambda e: (-e["predicted_probability"], e["start_utc"], str(e["event_id"])))
        for event in candidates[:5]:
            event["shortlist"] = True

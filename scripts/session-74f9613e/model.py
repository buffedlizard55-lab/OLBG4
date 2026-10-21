#!/usr/bin/env python3
"""Originate betting lines from verified inputs and select a pick per match.

The model is deterministic and deliberately simple. Every coefficient is a stated
assumption (documented in METHODOLOGY.md); the *inputs* are verified facts from
official sources. Nothing is fitted to bookmaker prices, because no bookmaker
prices were read.

Run: python3 scripts/model.py
Outputs: data/session-74f9613e/matches.json
"""
import json
import math
import os
from statistics import NormalDist

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
INPUTS = os.path.join(ROOT, "data", "session-74f9613e", "inputs.json")
OUTPUT = os.path.join(ROOT, "data", "session-74f9613e", "matches.json")

def n_cdf(x, mu=0.0, sd=1.0):
    return NormalDist(mu, sd).cdf(x)


def n_inv(p, mu=0.0, sd=1.0):
    return NormalDist(mu, sd).inv_cdf(p)

# Market margins (overround). Applied proportionally to the model probability.
MARGIN_2WAY = 1.04
MARGIN_3WAY = 1.05

# Confidence bands on the model probability of the selected pick.
HIGH = 0.65
MEDIUM = 0.57


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def sigmoid(x):
    return 1.0 / (1.0 + math.exp(-x))


def odds(prob, overround):
    """Decimal odds for a selection with model probability `prob`."""
    implied = clamp(prob * overround, 1e-6, 0.999)
    return round(1.0 / implied, 2)


def nearest_half(x):
    return round(x * 2.0) / 2.0


def two_way(name_a, p_a, name_b, p_b):
    return [
        {"market": "moneyline", "selection": name_a, "prob": round(p_a, 4),
         "odds": odds(p_a, MARGIN_2WAY)},
        {"market": "moneyline", "selection": name_b, "prob": round(p_b, 4),
         "odds": odds(p_b, MARGIN_2WAY)},
    ]


# --------------------------------------------------------------------------
# Sport models
# --------------------------------------------------------------------------
def model_nhl(m):
    hi, ai = m["inputs"]["home"], m["inputs"]["away"]
    ratings = {}
    for side, i in (("home", hi), ("away", ai)):
        pct = i["pts"] / (2.0 * i["gp"])
        shrunk = 0.5 + (pct - 0.5) * i["gp"] / (i["gp"] + 12.0)
        gd = (i["gf"] - i["ga"]) / i["gp"]
        ratings[side] = shrunk + gd * 0.012
    p_home = clamp(0.5 + (ratings["home"] - ratings["away"]) * 0.80 + 0.035, 0.08, 0.92)

    def gpg(goals, gp, league=3.05, k=10.0):
        """Shrink an early-season goals rate toward the league average."""
        return (goals / gp * gp + league * k) / (gp + k)

    exp_h = (gpg(hi["gf"], hi["gp"]) + gpg(ai["ga"], ai["gp"])) / 2.0
    exp_a = (gpg(ai["gf"], ai["gp"]) + gpg(hi["ga"], hi["gp"])) / 2.0
    total_mean = clamp(exp_h + exp_a, 4.5, 8.5)
    total_line = nearest_half(total_mean)
    p_over = 1.0 - n_cdf(total_line, total_mean, 1.9)
    diff = exp_h - exp_a
    p_home_pl = 1.0 - n_cdf(1.5, diff, 2.0)

    sels = two_way(m["home"]["name"], p_home, m["away"]["name"], 1 - p_home)
    sels += [
        {"market": "handicap", "selection": f"{m['home']['name']} -1.5", "prob": round(p_home_pl, 4),
         "odds": odds(p_home_pl, MARGIN_2WAY), "line": -1.5},
        {"market": "handicap", "selection": f"{m['away']['name']} +1.5", "prob": round(1 - p_home_pl, 4),
         "odds": odds(1 - p_home_pl, MARGIN_2WAY), "line": 1.5},
        {"market": "total", "selection": f"Over {total_line}", "prob": round(p_over, 4),
         "odds": odds(p_over, MARGIN_2WAY), "line": total_line},
        {"market": "total", "selection": f"Under {total_line}", "prob": round(1 - p_over, 4),
         "odds": odds(1 - p_over, MARGIN_2WAY), "line": total_line},
    ]
    return {
        "selections": sels,
        "model_view": {
            "expected_goals_home": round(exp_h, 2),
            "expected_goals_away": round(exp_a, 2),
            "expected_total": round(total_mean, 2),
            "home_win_prob": round(p_home, 4),
        },
    }


def nba_strength(prior, current):
    pw, pl = prior
    prior_pct = pw / float(pw + pl)
    cw, cl = current
    gp = cw + cl
    cur_pct = (cw / float(gp)) if gp else 0.5
    return 0.75 * (prior_pct - 0.5) + 0.25 * (cur_pct - 0.5) * (gp / (gp + 20.0))


def model_nba(m):
    sh = nba_strength(m["inputs"]["home"]["prior"], m["inputs"]["home"]["current"])
    sa = nba_strength(m["inputs"]["away"]["prior"], m["inputs"]["away"]["current"])
    r_h = math.log((0.5 + sh) / (0.5 - sh))
    r_a = math.log((0.5 + sa) / (0.5 - sa))
    p_home = clamp(sigmoid(r_h - r_a + 0.24), 0.05, 0.95)

    sd = 11.5
    margin = n_inv(p_home) * sd
    line = -nearest_half(margin)          # negative = home favoured
    p_home_cover = 1.0 - n_cdf(-line, margin, sd)

    sels = two_way(m["home"]["name"], p_home, m["away"]["name"], 1 - p_home)
    sels += [
        {"market": "handicap", "selection": f"{m['home']['name']} {line:+.1f}",
         "prob": round(p_home_cover, 4), "odds": odds(p_home_cover, MARGIN_2WAY), "line": line},
        {"market": "handicap", "selection": f"{m['away']['name']} {-line:+.1f}",
         "prob": round(1 - p_home_cover, 4), "odds": odds(1 - p_home_cover, MARGIN_2WAY),
         "line": -line},
    ]
    return {
        "selections": sels,
        "model_view": {
            "home_win_prob": round(p_home, 4),
            "model_spread_home": round(-margin, 1),
            "note": "Totals not originated (no official pace/efficiency inputs captured).",
        },
    }


def model_mlb(m):
    hi, ai = m["inputs"]["home"], m["inputs"]["away"]

    def rate(t):
        pct = t["w"] / float(t["w"] + t["l"])
        return 0.5 + (pct - 0.5) * 162.0 / 202.0

    rh, ra = rate(hi), rate(ai)
    r_h = math.log(rh / (1 - rh))
    r_a = math.log(ra / (1 - ra))
    p_home = clamp(sigmoid(r_h - r_a + 0.17), 0.10, 0.90)

    exp_h = (hi["rs"] / 162.0 + ai["ra"] / 162.0) / 2.0 + 0.12
    exp_a = (ai["rs"] / 162.0 + hi["ra"] / 162.0) / 2.0 - 0.12
    total_mean = exp_h + exp_a
    total_line = nearest_half(total_mean)
    p_over = 1.0 - n_cdf(total_line, total_mean, 4.2)
    diff = exp_h - exp_a
    p_home_rl = 1.0 - n_cdf(1.5, diff, 4.2)

    sels = two_way(m["home"]["name"], p_home, m["away"]["name"], 1 - p_home)
    sels += [
        {"market": "handicap", "selection": f"{m['home']['name']} -1.5", "prob": round(p_home_rl, 4),
         "odds": odds(p_home_rl, MARGIN_2WAY), "line": -1.5},
        {"market": "handicap", "selection": f"{m['away']['name']} +1.5", "prob": round(1 - p_home_rl, 4),
         "odds": odds(1 - p_home_rl, MARGIN_2WAY), "line": 1.5},
        {"market": "total", "selection": f"Over {total_line}", "prob": round(p_over, 4),
         "odds": odds(p_over, MARGIN_2WAY), "line": total_line},
        {"market": "total", "selection": f"Under {total_line}", "prob": round(1 - p_over, 4),
         "odds": odds(1 - p_over, MARGIN_2WAY), "line": total_line},
    ]
    return {
        "selections": sels,
        "model_view": {
            "expected_runs_home": round(exp_h, 2),
            "expected_runs_away": round(exp_a, 2),
            "expected_total": round(total_mean, 2),
            "home_win_prob": round(p_home, 4),
        },
    }


def model_urc(m):
    hi, ai = m["inputs"]["home"], m["inputs"]["away"]

    def rating(t):
        win_rate = (t["w"] + 0.5 * t["d"]) / float(t["pl"])
        pd_pg = (t["pf"] - t["pa"]) / float(t["pl"])
        raw = win_rate + pd_pg * 0.010
        return 0.5 + (raw - 0.5) * t["pl"] / (t["pl"] + 6.0)

    p_home_raw = clamp(0.5 + (rating(hi) - rating(ai)) * 0.90 + 0.05, 0.05, 0.90)
    p_draw = 0.055
    p_home = p_home_raw * (1 - p_draw)
    p_away = (1 - p_home_raw) * (1 - p_draw)

    def ppg(t, league=47.5, k=6.0):
        return ((t["pf"] + t["pa"]) / float(t["pl"]) * t["pl"] + league * k) / (t["pl"] + k)

    exp_total = (ppg(hi) + ppg(ai)) / 2.0
    total_line = nearest_half(exp_total)
    p_over = 1.0 - n_cdf(total_line, exp_total, 12.0)

    sd = 13.0
    margin = n_inv(p_home_raw) * sd
    line = -nearest_half(margin)
    p_home_cover = 1.0 - n_cdf(-line, margin, sd)

    sels = [
        {"market": "moneyline", "selection": m["home"]["name"], "prob": round(p_home, 4),
         "odds": odds(p_home, MARGIN_3WAY)},
        {"market": "moneyline", "selection": "Draw", "prob": round(p_draw, 4),
         "odds": odds(p_draw, MARGIN_3WAY)},
        {"market": "moneyline", "selection": m["away"]["name"], "prob": round(p_away, 4),
         "odds": odds(p_away, MARGIN_3WAY)},
        {"market": "handicap", "selection": f"{m['home']['name']} {line:+.1f}",
         "prob": round(p_home_cover, 4), "odds": odds(p_home_cover, MARGIN_2WAY), "line": line},
        {"market": "handicap", "selection": f"{m['away']['name']} {-line:+.1f}",
         "prob": round(1 - p_home_cover, 4), "odds": odds(1 - p_home_cover, MARGIN_2WAY),
         "line": -line},
        {"market": "total", "selection": f"Over {total_line}", "prob": round(p_over, 4),
         "odds": odds(p_over, MARGIN_2WAY), "line": total_line},
        {"market": "total", "selection": f"Under {total_line}", "prob": round(1 - p_over, 4),
         "odds": odds(1 - p_over, MARGIN_2WAY), "line": total_line},
    ]
    return {
        "selections": sels,
        "model_view": {
            "expected_total_points": round(exp_total, 2),
            "home_win_prob": round(p_home, 4),
            "draw_prob": p_draw,
        },
    }


def model_snooker(m):
    hm, am = m["inputs"]["home"]["money"], m["inputs"]["away"]["money"]
    k = 0.45
    q = sigmoid(k * (math.log(hm) - math.log(am)))
    q = clamp(q, 0.15, 0.85)

    p40 = q ** 4
    p41 = 4 * q ** 4 * (1 - q)
    p42 = 10 * q ** 4 * (1 - q) ** 2
    p43 = 20 * q ** 4 * (1 - q) ** 3
    p_win = p40 + p41 + p42 + p43
    p_away = 1 - p_win

    exp_frames = 4 * p40 + 5 * p41 + 6 * p42 + 7 * p43
    total_line = nearest_half(exp_frames)
    # exact distribution over completed frame counts 4,5,6,7
    p_over = sum(p for frames, p in ((4, p40), (5, p41), (6, p42), (7, p43)) if frames > total_line)
    p_home_hcp = p40 + p41 + p42  # wins by two frames or more

    sels = two_way(m["home"]["name"], p_win, m["away"]["name"], p_away)
    sels += [
        {"market": "handicap", "selection": f"{m['home']['name']} -1.5 frames",
         "prob": round(p_home_hcp, 4), "odds": odds(p_home_hcp, MARGIN_2WAY), "line": -1.5},
        {"market": "handicap", "selection": f"{m['away']['name']} +1.5 frames",
         "prob": round(1 - p_home_hcp, 4), "odds": odds(1 - p_home_hcp, MARGIN_2WAY), "line": 1.5},
        {"market": "total", "selection": f"Over {total_line} frames", "prob": round(p_over, 4),
         "odds": odds(p_over, MARGIN_2WAY), "line": total_line},
        {"market": "total", "selection": f"Under {total_line} frames", "prob": round(1 - p_over, 4),
         "odds": odds(1 - p_over, MARGIN_2WAY), "line": total_line},
    ]
    return {
        "selections": sels,
        "model_view": {
            "per_frame_win_prob_home": round(q, 4),
            "match_win_prob_home": round(p_win, 4),
            "expected_frames": round(exp_frames, 2),
        },
    }


MODELS = {
    "nhl_amount": model_nhl,
    "nba": model_nba,
    "mlb": model_mlb,
    "urc": model_urc,
    "snooker": model_snooker,
}


def confidence_for(prob, market, inputs_verified):
    if not inputs_verified:
        return "low"
    if market == "moneyline" and prob >= HIGH:
        return "high"
    if market == "handicap" and prob >= HIGH:
        return "high"
    if market == "total" and prob >= HIGH:
        return "high"
    if prob >= MEDIUM:
        return "medium"
    return "low"


def main():
    with open(INPUTS, encoding="utf-8") as fh:
        data = json.load(fh)

    out = []
    for m in data["matches"]:
        record = dict(m)
        if not m.get("inputs_verified"):
            record.update({
                "priced": False,
                "market_status": "not originated - verified inputs incomplete",
                "selections": [],
                "pick": None,
                "confidence": "unrated",
            })
            out.append(record)
            continue

        result = MODELS[m["model"]](m)
        sels = result["selections"]
        wnrs = [s for s in sels if s["market"] == "moneyline"
                and s["selection"] in (m["home"]["name"], m["away"]["name"])]
        best = max(wnrs, key=lambda s: s["prob"])
        conf = confidence_for(best["prob"], "moneyline", True)
        record.update({
            "priced": True,
            "selections": sels,
            "model_view": result["model_view"],
            "pick": {
                "market": best["market"],
                "selection": best["selection"],
                "prob": best["prob"],
                "odds": best["odds"],
            },
            "confidence": conf,
            "market_status": "originated from verified inputs",
        })
        out.append(record)

    payload = {
        "meta": {
            "generated_by": "scripts/model.py",
            "generated_at_utc": "2026-10-21T09:00:00Z",
            "margins": {"two_way_overround": MARGIN_2WAY, "three_way_overround": MARGIN_3WAY},
            "confidence_bands": {"high": HIGH, "medium": MEDIUM},
            "disclaimer": "Model output for research and comparison only. Not betting advice.",
        },
        "matches": out,
    }
    with open(OUTPUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
        fh.write("\n")

    priced = [r for r in out if r["priced"]]
    print(f"wrote {OUTPUT}: {len(out)} matches, {len(priced)} priced")
    for r in priced:
        print(f"  {r['sport_slug']:12s} {r['away']['name'][:22]:22s} @ {r['home']['name'][:22]:22s} "
              f"-> {r['pick']['selection'][:34]:34s} p={r['pick']['prob']:.3f} "
              f"odds={r['pick']['odds']:.2f} {r['confidence']}")


if __name__ == "__main__":
    main()

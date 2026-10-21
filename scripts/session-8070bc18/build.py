#!/usr/bin/env python3
"""Build the session-8070bc18 verified line desk.

Pipeline:
  1. turn the verified source_data module into fixture records
  2. originate moneyline / handicap / total prices from a declared model
  3. assign a pick and a confidence band from an explicit evidence rule
  4. validate every published field (sources, blanks, predictions, links)
  5. write data/session-8070bc18/desk.json and the docs/desk/ pages

Run: python3 scripts/session-8070bc18/build.py
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_data as S  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA_OUT = ROOT / "data" / "session-8070bc18"
SITE_OUT = ROOT / "docs" / "desk"

MODEL = dict(
    version="desk-v1",
    margin=0.96,                 # 4% theoretical margin on every originated price
    nhl_weight=0.55,             # weight on points-percentage gap
    nba_prior_games=6.0,         # shrinkage: (W + 3) / (GP + 6)
    mlb_weight=1.0,              # log5 on final regular-season win%
    other_weight=0.60,           # weight for event-form gaps (snooker)
    home_edge=0.03,              # probability added to the home side
    nhl_puck_sigma=2.4,          # goal margin sd for the -1.5 puck line
    nhl_total_sigma=2.0,         # total goals sd
    nhl_home_goals=0.03,         # home side scores 3% more than its rate, away 3% less
    high_edge=0.12,              # |p - 0.5| needed for a High band
    medium_edge=0.07,
)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def price(p: float) -> float:
    """Decimal price for probability p with the declared margin."""
    p = min(max(p, 0.01), 0.99)
    return round(min(1.0 / (p * MODEL["margin"]), 20.0), 2)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# 1. fixture records
# ---------------------------------------------------------------------------

def nhl_rows():
    rows = []
    for date, time_label, away, home, note in S.NHL_FIXTURES:
        h, a = S.NHL[home], S.NHL[away]
        p = clamp(0.5 + MODEL["nhl_weight"] * (h["pct"] - a["pct"]) + MODEL["home_edge"], 0.05, 0.95)
        # Puck line and total come from the two clubs' own scoring rates, not from the
        # moneyline probability: expected goals for each side = league goals per team per
        # game x that club's offence x the opponent's defence x a 3% home factor.
        lg = NHL_AVG["goals_per_game"] / 2.0
        xgf_h = lg * ((h["gf"] / h["gp"]) / lg) * ((a["ga"] / a["gp"]) / lg) * (1 + MODEL["nhl_home_goals"])
        xgf_a = lg * ((a["gf"] / a["gp"]) / lg) * ((h["ga"] / h["gp"]) / lg) * (1 - MODEL["nhl_home_goals"])
        margin = xgf_h - xgf_a
        # the handicap is quoted on the favourite, and the line moves with the projection
        fav_home = margin >= 0
        absm = abs(margin)
        puck = 1.5
        while puck < 4.5 and (1 - norm_cdf((puck - absm) / MODEL["nhl_puck_sigma"])) > 0.88:
            puck += 1.0
        p_fav = 1 - norm_cdf((puck - absm) / MODEL["nhl_puck_sigma"])
        p_home_cover = p_fav if fav_home else 1 - p_fav
        exp_total = xgf_h + xgf_a
        line = min(max(round(exp_total * 2) / 2, 4.5), 8.5)
        p_over = 1 - norm_cdf((line - exp_total) / MODEL["nhl_total_sigma"])
        fact = S.NHL_PLAYER_FACTS.get(home) or S.NHL_PLAYER_FACTS.get(away)
        rows.append(dict(
            sport="Ice Hockey", league="NHL", round="Regular season 2026-27",
            date=date, time=time_label, time_note="",
            home=S.NHL_TEAM_NAMES[home], away=S.NHL_TEAM_NAMES[away],
            venue="", venue_note=("NHL.com schedule page does not list the arena; "
                                  "left blank rather than inferred (game page not captured).")
            if not note else note,
            source_id="nhl_schedule", match_url="https://www.nhl.com/schedule",
            rating_home=h["pct"], rating_away=a["pct"],
            rating_basis=f"NHL points % (GP {h['gp']} v {a['gp']}, 21 Oct standings)",
            evidence=2, p_home=p,
            handicap=dict(
                line=(f"home -{puck:g} / away +{puck:g}" if fav_home
                      else f"home +{puck:g} / away -{puck:g}"),
                home_price=price(p_home_cover), away_price=price(1 - p_home_cover),
                home_prob=round(p_home_cover, 4),
                note=(f"Expected goal margin {margin:+.2f}; quoted on the favourite at {puck:g} with normal sd "
                      f"{MODEL['nhl_puck_sigma']}."),
            ),
            total=dict(
                line=f"{line:g}",
                over_price=price(p_over), under_price=price(1 - p_over),
                over_prob=round(p_over, 4),
                note=(f"Expected goals {xgf_h:.2f} v {xgf_a:.2f} from each club's GF/GP and GA/GP "
                      f"(league {lg:.2f} per team); model sd {MODEL['nhl_total_sigma']}."),
            ),
            xgf_home=round(xgf_h, 3), xgf_away=round(xgf_a, 3),
            expected_margin=round(margin, 3), expected_total=round(exp_total, 3),
            player_fact=fact,
            player_fact_team=home if S.NHL_PLAYER_FACTS.get(home) else (away if S.NHL_PLAYER_FACTS.get(away) else ""),
            flags=[],
        ))
    return rows


def nba_rows():
    rows = []
    for date, time_label, away, home, venue in S.NBA_FIXTURES:
        wh, lh = S.NBA.get(home, (0, 0))
        wa, la = S.NBA.get(away, (0, 0))
        rh = (wh + MODEL["nba_prior_games"] / 2) / (wh + lh + MODEL["nba_prior_games"])
        ra = (wa + MODEL["nba_prior_games"] / 2) / (wa + la + MODEL["nba_prior_games"])
        p = clamp(0.5 + MODEL["nhl_weight"] * (rh - ra) + MODEL["home_edge"], 0.05, 0.95)
        evidence = int(wh + lh > 0) + int(wa + la > 0)
        rows.append(dict(
            sport="Basketball", league="NBA", round="Regular season 2026-27",
            date=date, time=time_label, time_note="",
            home=home, away=away, venue=venue, venue_note="",
            source_id="nba_schedule", match_url="https://www.nba.com/schedule?date=2026-10-21",
            rating_home=round(rh, 3), rating_away=round(ra, 3),
            rating_basis=f"2026-27 W-L with a {MODEL['nba_prior_games']:g}-game prior: {wh}-{lh} v {wa}-{la}",
            evidence=evidence, p_home=p,
            handicap=None,
            total=None,
            handicap_note="Not originated: no official league scoring average or margin input was captured for NBA this pass.",
            total_note="Not originated: no official league scoring average was captured for NBA this pass.",
            player_fact=None, player_fact_team="",
            flags=["prior-only"] if evidence == 0 else [],
        ))
    return rows


def mlb_rows():
    rows = []
    for date, time_label, away, home, gid, gnum in S.MLB_FIXTURES:
        wh, lh = S.MLB[home]
        wa, la = S.MLB[away]
        rh, ra = wh / (wh + lh), wa / (wa + la)
        # log5 with the declared home edge
        p_neutral = (rh - rh * ra) / (rh + ra - 2 * rh * ra)
        p = clamp(p_neutral + 0.02, 0.05, 0.95)
        rows.append(dict(
            sport="Baseball", league="MLB", round=f"World Series {gnum}",
            date=date, time=time_label, time_note="",
            home=home, away=away, venue="",
            venue_note="MLB.com postseason page lists no ballpark; left blank rather than inferred.",
            source_id="mlb_postseason",
            match_url=f"https://www.mlb.com/gameday/{gid}/preview",
            rating_home=round(rh, 3), rating_away=round(ra, 3),
            rating_basis=f"Final 2026 regular-season W-L: {wh}-{lh} v {wa}-{la}",
            evidence=2, p_home=p, handicap=None, total=None,
            handicap_note="Not originated: no official run-scoring average captured.",
            total_note="Not originated: no official run environment captured.",
            player_fact=None, player_fact_team="", flags=[],
        ))
    return rows


def pdc_rows():
    rows = []
    for i, (date, session, p1, p2) in enumerate(S.PDC_FIXTURES, start=1):
        rows.append(dict(
            sport="Darts", league="PDC", round="European Championship, round one (best of 11 legs)",
            date=date, time=session, time_note="Session window as published by the PDC; per-match throw times are not published.",
            home=p1, away=p2, venue="Westfalenhalle, Dortmund", venue_note="",
            source_id="pdc_schedule",
            match_url="https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/",
            rating_home=0.5, rating_away=0.5,
            rating_basis="No verified ranking or form feed captured; 50/50 prior.",
            evidence=0, p_home=0.5, handicap=None, total=None,
            handicap_note="Not originated: no leg/set model inputs captured.",
            total_note="Not originated: no 180/leg total inputs captured.",
            player_fact=None, player_fact_team="", flags=["prior-only"],
        ))
    return rows


def ehf_rows():
    rows = []
    for date, time_label, home, away, mid in S.EHF_FIXTURES:
        p = 0.5 + MODEL["home_edge"]
        rows.append(dict(
            sport="Handball", league="EHF Champions League Men", round="2026-27 group phase",
            date=date, time=time_label,
            time_note="Throw-off time exactly as published on the EHF match list (page states no timezone).",
            home=home, away=away, venue="",
            venue_note="EHF match list does not show the hall; left blank rather than inferred.",
            source_id="ehf_matches",
            match_url=f"https://ehfcl.eurohandball.com/men/2026-27/matches/details/{mid}/",
            rating_home=0.5, rating_away=0.5,
            rating_basis="No verified EHF team-strength input captured; 50/50 prior plus declared home edge.",
            evidence=0, p_home=p, handicap=None, total=None,
            handicap_note="Not originated: no verified goal-average input captured.",
            total_note="Not originated: no verified goals-per-match input captured.",
            player_fact=None, player_fact_team="", flags=["prior-only"],
        ))
    return rows


def wst_rows():
    rows = []
    for date, home, away, mnum, mid in S.WST_FIXTURES:
        fh, fah = S.SNOOKER_R1.get(home, None), S.SNOOKER_R1.get(away, None)
        rh = 0.5 + 0.04 * (fh[0] - fh[1]) if fh else 0.5
        ra = 0.5 + 0.04 * (fah[0] - fah[1]) if fah else 0.5
        evidence = int(fh is not None) + int(fah is not None)
        p = clamp(0.5 + MODEL["other_weight"] * (rh - ra), 0.05, 0.95)
        basis = "Round-one frames this event: " + ", ".join(
            f"{n} {v[0]}-{v[1]}" for n, v in ((home, fh), (away, fah)) if v
        ) if (fh or fah) else "No round-one frame data for either player; 50/50 prior."
        rows.append(dict(
            sport="Snooker", league="WST", round=("Northern Ireland Open 2026, " + (mnum if mnum.startswith("Match") else "round two")),
            date=date, time="",
            time_note="WST list page renders clock times in the reader's locale and the venue-local time was not published; start time left blank.",
            home=home, away=away, venue="",
            venue_note="WST list page does not name the venue; left blank rather than inferred.",
            source_id="wst_matches",
            match_url=f"https://www.wst.tv/match-centre/{mid}",
            rating_home=round(rh, 3), rating_away=round(ra, 3),
            rating_basis=basis, evidence=evidence, p_home=p, handicap=None, total=None,
            handicap_note="Not originated: no verified frame-handicap model inputs captured.",
            total_note="Not originated: no verified total-frames input captured.",
            player_fact=None, player_fact_team="",
            flags=["prior-only"] if evidence == 0 else [],
        ))
    return rows


# league scoring average for NHL, computed from the captured standings
_sum_gf = sum(v["gf"] for v in S.NHL.values())
_sum_gp = sum(v["gp"] for v in S.NHL.values())
NHL_AVG = {"goals_per_game": 2 * _sum_gf / _sum_gp, "gf": _sum_gf, "gp": _sum_gp}


# ---------------------------------------------------------------------------
# 2. pick + confidence
# ---------------------------------------------------------------------------

def assign(rows):
    for i, r in enumerate(rows, start=1):
        prefix = {"Ice Hockey": "NHL", "Basketball": "NBA", "Baseball": "MLB",
                  "Darts": "DAR", "Handball": "EHF", "Snooker": "WST"}[r["sport"]]
        r["id"] = f"{prefix}-{i:02d}"
        r["p_away"] = round(1 - r["p_home"], 4)
        r["p_home"] = round(r["p_home"], 4)
        r["ml_home"] = price(r["p_home"])
        r["ml_away"] = price(r["p_away"])
        home_fav = r["p_home"] >= r["p_away"]
        r["pick"] = dict(
            side="home" if home_fav else "away",
            team=r["home"] if home_fav else r["away"],
            opponent=r["away"] if home_fav else r["home"],
            prob=max(r["p_home"], r["p_away"]),
            price=r["ml_home"] if home_fav else r["ml_away"],
            label="Moneyline (match winner)",
        )
        r["edge"] = round(abs(r["p_home"] - 0.5), 4)
        d = r["edge"]
        player_ok = bool(r.get("player_fact"))
        if r["evidence"] == 2 and d >= MODEL["high_edge"] and player_ok:
            band = "High"
        elif (r["evidence"] == 2 and d >= MODEL["medium_edge"]) or (r["evidence"] >= 1 and d >= MODEL["high_edge"]):
            band = "Medium"
        else:
            band = "Low"
        r["confidence"] = band
        r["confidence_note"] = confidence_note(r, d, player_ok)
        if band == "High" and not r.get("prediction_id"):
            r["prediction_required"] = True
    return rows


SPORT_INPUT = {
    "Ice Hockey": "NHL points % from the 21 Oct standings (all 32 clubs)",
    "Basketball": "2026-27 W-L with a 6-game shrinkage prior",
    "Baseball": "Final 2026 regular-season records, combined with log5",
    "Darts": "No verified ranking feed captured — 50/50 prior",
    "Handball": "No verified strength feed captured — 50/50 prior + home edge",
    "Snooker": "Round-one frame scores where published, else 50/50",
}


def confidence_note(r, d, player_ok):
    if r["edge"] == 0:
        return ("Model has no edge (50/50 prior); the pick is the first-listed side only and carries no model edge."
                if r["sport"] in ("Darts", "Snooker")
                else "Model has no edge; the pick is the home side on the declared home edge only.")
    if r["evidence"] == 0:
        return "Prior only: no verified strength input for either side."
    if r["evidence"] == 1:
        return "One side has a verified strength sample; the other is on the 50/50 prior."
    if d >= MODEL["high_edge"] and not player_ok:
        return "Strength gap is large but no verified player-level evidence was captured, so the pick is capped at Medium."
    if d >= MODEL["high_edge"]:
        return "Both sides have a verified strength sample, the model edge clears the High threshold, and player-level evidence is recorded."
    return "Both sides have a verified strength sample but the model edge is below the High threshold."


# ---------------------------------------------------------------------------
# 3. predictions
# ---------------------------------------------------------------------------

PREDICTIONS = [
    dict(
        fixture_id="NHL-08",  # LAK @ NYI, 22 Oct
        headline="Islanders moneyline against a Kings side stuck on a .286 points percentage",
        text=("New York Islanders to win on the moneyline. The Islanders are 5-3-1 (.611) with 27 goals scored and only 20 conceded, "
              "and they beat Anaheim 3-2 on 20 October, S. Holmstrom scoring the game-winner and I. Sorokin the winning goalie. "
              "Los Angeles are 1-4-2 (.286) with 17 goals in seven games and a minus-ten goal difference, and this is the middle game of three on the road in five nights. "
              "Their 5-2 win in Washington on 20 October, with E. Gustafsson scoring the winner and D. Kuemper in goal, is the only bright spot in the sample. "
              "Back the Islanders on the moneyline at our price."),
        facts=[
            "NHL.com standings, 21 Oct: NYI 5-3-1, .611 P%, 27 GF / 20 GA; LAK 1-4-2, .286 P%, 17 GF / 27 GA.",
            "NHL.com schedule: Los Angeles play at Washington on 20 Oct, at the Islanders on 22 Oct and at New Jersey on 24 Oct.",
            "NHL.com schedule, 20 Oct: Islanders 3-2 Anaheim (S. Holmstrom GWG, I. Sorokin W); Los Angeles 5-2 at Washington (E. Gustafsson GWG, D. Kuemper W).",
        ],
        sources=["nhl_standings", "nhl_schedule"],
    ),
    dict(
        fixture_id="NHL-18",  # LAK @ NJD, 24 Oct
        headline="Devils moneyline as Los Angeles close a three-game road trip",
        text=("New Jersey Devils to win on the moneyline. The Devils are 5-4-0 with a .556 points percentage and a 29-30 goal split after beating Colorado 4-3 on 20 October, "
              "when J. Boqvist scored the game-winning goal and J. Allen was the winning goalie. Los Angeles are 1-4-2 for a .286 points percentage, have scored only 17 goals in seven games "
              "and were out-scored 27-17. They won 5-2 in Washington on 20 October behind E. Gustafsson's winner and D. Kuemper in net, "
              "but that is their only win in seven games and this is the last of three road games in five nights. "
              "Back New Jersey at our originated price, with the -1.5 puck line as the secondary angle."),
        facts=[
            "NHL.com standings, 21 Oct: NJD 5-4-0, .556 P%, 29 GF / 30 GA; LAK 1-4-2, .286 P%, 17 GF / 27 GA.",
            "NHL.com schedule, 20 Oct: New Jersey 4-3 Colorado (J. Boqvist GWG, J. Allen W); Los Angeles 5-2 at Washington (E. Gustafsson GWG, D. Kuemper W).",
        ],
        sources=["nhl_standings", "nhl_schedule"],
    ),
    dict(
        fixture_id="NHL-25",  # TOR @ EDM, 24 Oct
        headline="Oilers moneyline: the league's best points percentage meets a Leafs side shipping goals",
        text=("Edmonton Oilers to win on the moneyline. Edmonton own the best points percentage in the league at .833 (7-1-1) with 41 goals scored and 27 conceded, "
              "and they beat Minnesota 4-3 in overtime on 20 October through E. Bouchard's game-winner with D. Levi in goal. "
              "Toronto are 5-4-2 (.545) with 38 goals scored and 35 conceded in 11 games, and they won 6-2 in Columbus on 20 October in which A. Matthews scored the winner "
              "and A. Stolarz was the winning goalie. Take Edmonton on the moneyline and consider the -1.5 puck line."),
        facts=[
            "NHL.com standings, 21 Oct: EDM 7-1-1, .833 P%, 41 GF / 27 GA; TOR 5-4-2, .545 P%, 38 GF / 35 GA.",
            "NHL.com schedule, 20 Oct: Edmonton 4-3 Minnesota OT (E. Bouchard GWG, D. Levi W); Toronto 6-2 at Columbus (A. Matthews GWG, A. Stolarz W).",
        ],
        sources=["nhl_standings", "nhl_schedule"],
    ),
    dict(
        fixture_id="NHL-19",  # SJS @ BOS, 24 Oct
        headline="Bruins moneyline against a San Jose side without a regulation win",
        text=("Boston Bruins to win on the moneyline. Boston are 7-2-1 for a .750 points percentage, have scored 36 and allowed 22, and they are 7-2-1 across their last ten, most recently a 3-2 overtime loss in Dallas on 20 October in which M. Rantanen scored the winner. "
              "San Jose are 5-4-1 but have zero regulation wins in ten games and a minus-eight goal difference (27 for, 35 against), even though they won 4-3 in overtime in Montréal on 20 October through M. Celebrini's winner and A. Nedeljkovic in net. "
              "The Bruins at home are the selection, with the -1.5 puck line as an alternative."),
        facts=[
            "NHL.com standings, 21 Oct: BOS 7-2-1, .750 P%, 36 GF / 22 GA, RW 6; SJS 5-4-1, .550 P%, 27 GF / 35 GA, RW 0.",
            "NHL.com schedule, 20 Oct: Dallas 3-2 Boston OT (M. Rantanen GWG, J. Oettinger W); San Jose 4-3 Montréal OT (M. Celebrini GWG, A. Nedeljkovic W).",
        ],
        sources=["nhl_standings", "nhl_schedule"],
    ),
    dict(
        fixture_id="NHL-24",  # CAR @ STL, 24 Oct
        headline="Hurricanes moneyline: a .773 side against a .500 Blues team",
        text=("Carolina Hurricanes to win on the moneyline. Carolina are 8-2-1 (.773), have scored 42 goals, second only to Vegas in these standings, and conceded 27, and they won 6-3 in Vancouver on 20 October with N. Deslauriers scoring the winner and P. Kochetkov in goal. "
              "St. Louis are 4-4-1 (.500) with a level 29-29 goal record and won only 2-1 at home to Winnipeg on 20 October, P. Broberg scoring the game-winner and J. Hofer the winning goalie. "
              "Back Carolina on the moneyline at our price, and the -1.5 puck line for the bigger return."),
        facts=[
            "NHL.com standings, 21 Oct: CAR 8-2-1, .773 P%, 42 GF / 27 GA; STL 4-4-1, .500 P%, 29 GF / 29 GA.",
            "NHL.com schedule, 20 Oct: Carolina 6-3 at Vancouver (N. Deslauriers GWG, P. Kochetkov W); St. Louis 2-1 Winnipeg (P. Broberg GWG, J. Hofer W).",
        ],
        sources=["nhl_standings", "nhl_schedule"],
    ),
]


def attach_predictions(rows):
    by_id = {r["id"]: r for r in rows}
    out = []
    for p in PREDICTIONS:
        row = by_id.get(p["fixture_id"])
        if row is None:
            raise SystemExit(f"prediction references unknown fixture {p['fixture_id']}")
        if row["confidence"] != "High":
            raise SystemExit(f"prediction on non-High row {row['id']} ({row['confidence']})")
        words = len(re.findall(r"[\w'’-]+", p["text"]))
        out.append(dict(
            **p,
            prediction_id=f"P-{len(out)+1:02d}",
            sport=row["sport"], match=f"{row['away']} @ {row['home']}",
            date=row["date"], pick=row["pick"], confidence=row["confidence"],
            word_count=words,
        ))
        row["prediction_id"] = out[-1]["prediction_id"]
    high = [r for r in rows if r["confidence"] == "High"]
    missing = [r["id"] for r in high if not r.get("prediction_id")]
    if missing:
        raise SystemExit(f"High-confidence rows without a prediction: {missing}")
    return out


# ---------------------------------------------------------------------------
# 4. validation
# ---------------------------------------------------------------------------

OFFICIAL_DOMAINS = {"nhl.com", "nba.com", "mlb.com", "pdc.tv",
                    "ehfcl.eurohandball.com", "wst.tv", "bwfbadminton.com"}


def validate(rows, preds, sources):
    errors, checks = [], []
    src_by_id = {s["id"]: s for s in sources}
    ids = [r["id"] for r in rows]
    checks.append(("fixture ids unique", len(ids) == len(set(ids))))
    for r in rows:
        if r["source_id"] not in src_by_id:
            errors.append(f"{r['id']}: unknown source id")
        else:
            if src_by_id[r["source_id"]]["domain"] not in OFFICIAL_DOMAINS:
                errors.append(f"{r['id']}: source domain not on the official allowlist")
        for f in ("date", "home", "away", "pick"):
            if not r.get(f):
                errors.append(f"{r['id']}: missing {f}")
        if r["confidence"] not in ("High", "Medium", "Low"):
            errors.append(f"{r['id']}: bad confidence")
        if r["handicap"] is None and not r.get("handicap_note"):
            errors.append(f"{r['id']}: handicap blank without a reason")
        if r["total"] is None and not r.get("total_note"):
            errors.append(f"{r['id']}: total blank without a reason")
        if r["ml_home"] and not (1.01 <= r["ml_home"] <= 30):
            errors.append(f"{r['id']}: moneyline price out of range")
    checks.append(("every row has a fixture, a pick and a price", not errors))

    bodies = [re.sub(r"\s+", " ", p["text"]).strip() for p in preds]
    checks.append(("predictions are unique", len(bodies) == len(set(bodies))))
    checks.append(("predictions >= 30 words", all(p["word_count"] >= 30 for p in preds)))
    for p in preds:
        if p["pick"]["team"].split()[-1].lower() not in p["text"].lower():
            errors.append(f"{p['fixture_id']}: prediction does not name the selection")
        if not any(k in p["text"].lower() for k in ("moneyline", "to win")):
            errors.append(f"{p['fixture_id']}: prediction does not state the market")
        if "moneyline" not in p["text"].lower():
            errors.append(f"{p['fixture_id']}: prediction does not say moneyline")
    checks.append(("every prediction states the selection and the market", not errors))
    return errors, checks


# ---------------------------------------------------------------------------
# 5. audit of the pre-existing builds (mechanical facts only)
# ---------------------------------------------------------------------------

def _audit_team_names():
    names = set(S.NHL_TEAM_NAMES.values())
    for _d, _t, a, h, _v in S.NBA_FIXTURES:
        names.add(a); names.add(h)
    names.update(S.MLB)
    return names


AUDIT_DATASETS = [
    ("Build A — data/rows.json", "data/rows.json"),
    ("Build B — data/board.json", "data/board.json"),
    ("Build D — data/matches.json", "data/matches.json"),
]


def audit_existing():
    """Row counts, source-domain mix and same-fixture pick conflicts in earlier builds.

    Only values literally present in those files are counted or compared. A row is
    paired with another only when both club names are recognised and the pick names
    one of them; rows that are not winner markets are skipped.
    """
    official = OFFICIAL_DOMAINS | {"world.rugby", "nrl.com", "icc-cricket.com", "atptour.com",
                                   "volleyballworld.com", "bwfbadminton.com", "wtt.com",
                                   "europeantour.com", "pga.com", "formula1.com", "gbgb.org.uk"}
    teams = _audit_team_names()
    table, by_pair = [], defaultdict(lambda: defaultdict(set))

    for label, rel in AUDIT_DATASETS:
        path = ROOT / rel
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        rows = (data.get("rows") or data.get("matches") or data.get("fixtures") or []) \
            if isinstance(data, dict) else data
        n_src = n_off = n_olbg = 0
        for r in rows:
            url = (r.get("sourceUrl") or r.get("source") or r.get("source_url")
                   or r.get("olbg_url") or "")
            if url:
                n_src += 1
                dom = re.sub(r"^https?://(www\.)?", "", url).split("/")[0].lower()
                if dom in official:
                    n_off += 1
                elif "olbg.com" in dom:
                    n_olbg += 1
            if r.get("market_type") and r["market_type"] != "winner":
                continue
            blob = " ".join(str(r.get(k, "")) for k in ("home", "away", "match", "teamA", "teamB"))
            found = sorted({t for t in teams if t.lower() in blob.lower()})
            pick = r.get("pick") or (r.get("selection") or {}).get("team") or ""
            if len(found) == 2 and pick:
                chosen = next((t for t in found if t.lower() in str(pick).lower()), "")
                if chosen:
                    by_pair[tuple(found)][label.split(" — ")[0]].add(chosen)
        table.append(dict(dataset=label, rows=len(rows), sourced=n_src, official=n_off, olbg=n_olbg))

    conflicts = []
    for pair, entries in by_pair.items():
        picks = set().union(*entries.values()) if entries else set()
        if len(picks) > 1:
            conflicts.append(dict(
                date="", pair=" v ".join(pair),
                entries=[f"{lab}: {' / '.join(sorted(v))}" for lab, v in sorted(entries.items())],
            ))
    conflicts.sort(key=lambda c: c["pair"])
    return table, conflicts


# ---------------------------------------------------------------------------
# 6. site
# ---------------------------------------------------------------------------

CSS = """
:root{--ink:#0f172a;--muted:#5b6478;--line:#e3e7ef;--bg:#f6f8fb;--card:#fff;
--brand:#14532d;--brand2:#166534;--accent:#b45309;--high:#15803d;--med:#b45309;--low:#475569;
--link:#1d4ed8;--chip:#eef2f7}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
header.top{background:linear-gradient(135deg,#0b3b22,#14532d 60%,#166534);color:#fff;padding:22px 20px 18px}
header.top .wrap{max-width:1180px;margin:0 auto}
header.top h1{margin:0 0 4px;font-size:22px;letter-spacing:.2px}
header.top p{margin:0;color:#d7e7db;font-size:13.5px}
nav.main{background:#0b2e1b;position:sticky;top:0;z-index:10;border-bottom:1px solid #0a2a19}
nav.main .wrap{max-width:1180px;margin:0 auto;display:flex;flex-wrap:wrap;gap:2px;padding:0 12px}
nav.main a{color:#e6efe8;padding:11px 12px;font-size:14px;border-bottom:3px solid transparent}
nav.main a:hover{background:#12401f;text-decoration:none}
nav.main a.on{border-bottom-color:#86efac;background:#12401f;font-weight:600}
main{max-width:1180px;margin:0 auto;padding:22px 16px 60px}
h1.page{font-size:26px;margin:6px 0 6px}
p.lede{color:var(--muted);margin:0 0 18px;max-width:80ch}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:0 0 22px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.card .k{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted)}
.card .v{font-size:24px;font-weight:700;margin-top:4px}
.card .s{font-size:12.5px;color:var(--muted);margin-top:2px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 20px;overflow:hidden}
.panel h2{margin:0 0 10px;font-size:17px}
.panel h3{margin:18px 0 8px;font-size:15px}
.tablewrap{overflow:auto;border:1px solid var(--line);border-radius:10px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:13.2px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f2f5f9;font-size:11.6px;text-transform:uppercase;letter-spacing:.05em;color:#3f4a5f;position:sticky;top:0;z-index:1}
tbody tr:hover{background:#fafcff}
tbody tr:last-child td{border-bottom:none}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:700;letter-spacing:.02em}
.badge.High{background:#dcfce7;color:var(--high)}
.badge.Medium{background:#fef3c7;color:var(--med)}
.badge.Low{background:#e2e8f0;color:var(--low)}
.chip{display:inline-block;background:var(--chip);border:1px solid var(--line);color:#334155;padding:1px 7px;border-radius:6px;font-size:11.5px}
.chip.warn{background:#fff7ed;border-color:#fed7aa;color:#9a3412}
.chip.ok{background:#f0fdf4;border-color:#bbf7d0;color:#166534}
.src{font-size:12px;color:var(--muted)}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:0 0 12px}
.toolbar input,.toolbar select{padding:8px 10px;border:1px solid #cfd6e2;border-radius:8px;font:inherit;background:#fff}
.toolbar input{min-width:220px}
.muted{color:var(--muted)}
.small{font-size:12.5px}
.pred{border:1px solid var(--line);border-radius:12px;padding:16px;margin:0 0 14px;background:#fff}
.pred h3{margin:0 0 6px;font-size:16.5px}
.pred .meta{font-size:12.5px;color:var(--muted);margin:0 0 10px}
.pred p.body{margin:0 0 10px}
.pred ul{margin:0;padding-left:18px;font-size:13px;color:#334155}
footer{max-width:1180px;margin:0 auto;padding:20px 16px 40px;color:var(--muted);font-size:12.5px;border-top:1px solid var(--line)}
.note{border-left:4px solid var(--accent);background:#fffbeb;padding:10px 14px;border-radius:8px;margin:0 0 16px;font-size:13.5px}
.kv{display:grid;grid-template-columns:220px 1fr;gap:6px 16px;font-size:13.5px}
@media(max-width:700px){.kv{grid-template-columns:1fr}}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:12.5px}
"""

JS = """
(function(){
  var rows=[].slice.call(document.querySelectorAll('table[data-filter] tbody tr'));
  if(!rows.length) return;
  var q=document.getElementById('q'), c=document.getElementById('conf'), s=document.getElementById('sport');
  function apply(){
    var qv=(q&&q.value||'').toLowerCase(), cv=(c&&c.value||''), sv=(s&&s.value||'');
    rows.forEach(function(tr){
      var text=tr.innerText.toLowerCase();
      var ok=(!qv||text.indexOf(qv)>-1)&&(!cv||tr.dataset.conf===cv)&&(!sv||tr.dataset.sport===sv);
      tr.style.display=ok?'':'none';
    });
    var shown=rows.filter(function(tr){return tr.style.display!=='none'}).length;
    var out=document.getElementById('count');
    if(out) out.textContent=shown+' of '+rows.length+' rows';
  }
  [q,c,s].forEach(function(el){ if(el){ el.addEventListener('input',apply); el.addEventListener('change',apply);} });
  apply();
})();
"""

NAV = [("index.html", "Overview"), ("picks.html", "Picks"), ("predictions.html", "Predictions"),
       ("nhl.html", "Ice Hockey"), ("nba.html", "Basketball"), ("mlb.html", "Baseball"),
       ("darts.html", "Darts"), ("handball.html", "Handball"), ("snooker.html", "Snooker"),
       ("coverage.html", "Coverage"), ("flagged.html", "Flagged for Review"),
       ("methodology.html", "Methodology"), ("sources.html", "Sources")]


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def page(title, body, current, root=""):
    nav = "".join(
        f'<a class="{"on" if href == current else ""}" href="{root}{href}">{label}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 verified desk</title>
<meta name="description" content="Official-source verified fixtures, independently originated lines and confidence-labelled picks.">
<link rel="stylesheet" href="{root}style.css">
</head><body>
<header class="top"><div class="wrap">
<h1>OLBG4 — Verified Line Desk</h1>
<p>Session <code>arena/8070bc18-olbg4</code> · captured {S.CAPTURED_AT} · every row cites the official page it came from</p>
</div></header>
<nav class="main"><div class="wrap">{nav}</div></nav>
<main>
{body}
</main>
<footer>
Built by <code>scripts/session-8070bc18/build.py</code> from <code>data/session-8070bc18/desk.json</code>.
Prices are our own originated prices, not bookmaker prices. Nothing here is betting advice.
Unverified values are left blank and listed on the <a href="{root}flagged.html">Flagged for Review</a> page.
</footer>
<script src="{root}app.js"></script>
</body></html>
"""


def badge(conf):
    return f'<span class="badge {conf}">{conf}</span>'


def market_cells(r):
    hc = r.get("handicap")
    tt = r.get("total")
    hcell = (f'<span title="{esc(hc["note"])}">{esc(hc["line"])}</span>'
             f'<br><span class="num">{hc["home_price"]} / {hc["away_price"]}</span>'
             if hc else '<span class="chip" title="' + esc(r.get("handicap_note", "")) + '">blank — no input</span>')
    tcell = (f'<span title="{esc(tt["note"])}">O/U {esc(tt["line"])}</span>'
             f'<br><span class="num">{tt["over_price"]} / {tt["under_price"]}</span>'
             if tt else '<span class="chip" title="' + esc(r.get("total_note", "")) + '">blank — no input</span>')
    return hcell, tcell


def fixture_table(rows, sources):
    src = {s["id"]: s for s in sources}
    head = ("<tr><th>Date</th><th>Time</th><th>Competition / round</th><th>Match</th><th>Venue</th>"
            "<th>Moneyline (home / away)</th><th>Handicap</th><th>Total</th><th>Pick</th>"
            "<th>Conf.</th><th>Evidence</th><th>Source</th></tr>")
    body = []
    for r in rows:
        hc, tt = market_cells(r)
        venue = (esc(r["venue"]) if r["venue"]
                 else '<span class="chip" title="' + esc(r["venue_note"]) + '">blank — not published</span>')
        time = (esc(r["time"]) if r["time"]
                else '<span class="chip" title="' + esc(r["time_note"]) + '">blank — see note</span>')
        ev = {2: "Both sides", 1: "One side", 0: "Prior only"}[r["evidence"]]
        body.append(
            f'<tr data-conf="{r["confidence"]}" data-sport="{esc(r["sport"])}">'
            f'<td class="num">{esc(r["date"])}</td><td class="num">{time}</td>'
            f'<td>{esc(r["league"])} — {esc(r["round"])}</td>'
            f'<td><strong>{esc(r["away"])}</strong> @ <strong>{esc(r["home"])}</strong></td>'
            f'<td>{venue}</td>'
            f'<td class="num">{r["ml_home"]:.2f} / {r["ml_away"]:.2f}</td>'
            f'<td>{hc}</td><td>{tt}</td>'
            f'<td><strong>{esc(r["pick"]["team"])}</strong><br><span class="num">@ {r["pick"]["price"]:.2f}</span></td>'
            f'<td>{badge(r["confidence"])}</td><td class="small">{ev}</td>'
            f'<td class="src"><a href="{esc(src[r["source_id"]]["url"])}" target="_blank" rel="noopener">{esc(src[r["source_id"]]["domain"])}</a>'
            + ('<br><a href="' + esc(r["match_url"]) + '" target="_blank" rel="noopener">match page</a>'
               if r["match_url"] != src[r["source_id"]]["url"] else "")
            + '</td></tr>'
        )
    return (f'<div class="toolbar"><input id="q" type="search" placeholder="Search team, date, competition…" aria-label="Search">'
            f'<select id="conf" aria-label="Confidence"><option value="">All confidence</option>'
            f'<option>High</option><option>Medium</option><option>Low</option></select>'
            f'<span id="count" class="muted small"></span></div>'
            f'<div class="tablewrap"><table data-filter="1"><thead>{head}</thead><tbody>{"".join(body)}</tbody></table></div>')


def stat_cards(rows, preds):
    c = Counter(r["confidence"] for r in rows)
    sports = sorted({r["sport"] for r in rows})
    return f"""<div class="cards">
<div class="card"><div class="k">Fixtures</div><div class="v">{len(rows)}</div><div class="s">{"1 sport" if len(sports) == 1 else str(len(sports)) + " sports"}, 21–27 Oct 2026</div></div>
<div class="card"><div class="k">High confidence</div><div class="v">{c['High']}</div><div class="s">each with a written prediction</div></div>
<div class="card"><div class="k">Medium</div><div class="v">{c['Medium']}</div><div class="s">verified inputs, thinner edge</div></div>
<div class="card"><div class="k">Low</div><div class="v">{c['Low']}</div><div class="s">prior-only or no edge</div></div>
<div class="card"><div class="k">Predictions</div><div class="v">{len(preds)}</div><div class="s">min {min((p['word_count'] for p in preds), default=0)} words</div></div>
<div class="card"><div class="k">Official sources</div><div class="v">{len(S.SOURCES)}</div><div class="s">league / governing body pages</div></div>
</div>"""


def write_site(rows, preds, sources, stats, checks, conflicts, counts):
    SITE_OUT.mkdir(parents=True, exist_ok=True)
    (SITE_OUT / "style.css").write_text(CSS.strip() + "\n")
    (SITE_OUT / "app.js").write_text(JS.strip() + "\n")

    src = {s["id"]: s for s in sources}
    by_sport = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)

    # ---- overview -----------------------------------------------------
    top = sorted([r for r in rows if r["confidence"] == "High"], key=lambda r: -r["edge"])
    top_rows = "".join(
        f'<tr><td class="num">{esc(r["date"])}</td><td>{esc(r["away"])} @ {esc(r["home"])}</td>'
        f'<td><strong>{esc(r["pick"]["team"])}</strong></td><td class="num">@ {r["pick"]["price"]:.2f}</td>'
        f'<td>{badge(r["confidence"])}</td>'
        f'<td><a href="predictions.html#{esc(r["prediction_id"])}">read prediction</a></td></tr>'
        for r in top)
    seen, srows = set(), []
    for r in rows:
        if r["sport"] in seen:
            continue
        seen.add(r["sport"])
        rs = by_sport[r["sport"]]
        srows.append(
            f'<tr><td><a href="{sport_page(r["sport"])}">{esc(r["sport"])}</a></td><td>{esc(rs[0]["league"])}</td>'
            f'<td class="num">{len(rs)}</td>'
            f'<td class="num">{sum(1 for x in rs if x["confidence"]=="High")}</td>'
            f'<td class="num">{sum(1 for x in rs if x["confidence"]=="Medium")}</td>'
            f'<td class="num">{sum(1 for x in rs if x["confidence"]=="Low")}</td>'
            f'<td class="small">{esc(SPORT_INPUT.get(r["sport"], rs[0]["rating_basis"]))}</td></tr>')
    body = f"""<h1 class="page">Overview</h1>
<p class="lede">A single verified desk: {len(rows)} fixtures in the 21–27 October 2026 window across {len(by_sport)} sports,
each traced to the official league or governing-body page it was read from. Lines are ours, produced by the documented
model on the <a href="methodology.html">methodology</a> page. Where a value could not be confirmed it is blank and listed
on <a href="flagged.html">Flagged for Review</a>.</p>
{stat_cards(rows, preds)}
<div class="panel"><h2>What is different about this desk</h2>
<div class="kv">
<div>Sources</div><div>Only league and governing-body pages (NHL.com, NBA.com, MLB.com, PDC, EHF, WST, BWF). No tipster
consensus and no aggregator is used as a source for any published value.</div>
<div>Prices</div><div>Every price is ours: <code>1 / (p × {MODEL['margin']})</code>. No bookmaker or OLBG price is read.</div>
<div>Blanks</div><div>Venue, start time, handicap and total are blank wherever the official page did not publish the input.
Each blank carries the reason in the cell and, where relevant, a row on the flagged page.</div>
<div>Confidence</div><div>High needs both sides on a verified strength sample, a model edge of at least
{MODEL['high_edge']:.2f} in probability, and recorded player-level evidence. Medium and Low are defined the same way on the
methodology page.</div>
<div>Predictions</div><div>{len(preds)} written selections, one per High row, each ≥30 words with an explicit market and
selection and with the verified facts listed underneath.</div>
</div></div>
<div class="panel"><h2>High-confidence picks</h2>
<div class="tablewrap"><table><thead><tr><th>Date</th><th>Match</th><th>Selection</th><th>Our price</th><th>Band</th><th>Prediction</th></tr></thead>
<tbody>{top_rows}</tbody></table></div></div>
<div class="panel"><h2>By sport</h2>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>League</th><th>Rows</th><th>High</th><th>Medium</th><th>Low</th><th>Strength input</th></tr></thead>
<tbody>{"".join(srows)}</tbody></table></div></div>
<div class="grid2">
<div class="panel"><h2>Where the evidence is strong</h2>
<p class="small">Ice hockey carries the deepest verified sample: {NHL_AVG['gp']} team-games of 2026-27 standings, giving a
points percentage for all 32 clubs and a league scoring average of {NHL_AVG['goals_per_game']:.2f} goals per game computed
from the same table. That is why handicap and total markets are originated for NHL rows and left blank elsewhere.</p></div>
<div class="panel"><h2>Where it is thin</h2>
<p class="small">NBA has one game per club at capture, so the model shrinks hard toward .500 and no NBA row clears the High
threshold. Darts, handball and the hand-timed snooker list carry prior-only lines. All of this is stated per row and
summarised on the flagged page rather than dressed up as form.</p></div>
</div>"""
    (SITE_OUT / "index.html").write_text(page("Overview", body, "index.html"))

    # ---- per sport ----------------------------------------------------
    for sport, rs in by_sport.items():
        slug = sport_slug(sport)
        srcs = sorted({r["source_id"] for r in rs})
        body = f"""<h1 class="page">{esc(sport)}</h1>
<p class="lede">{len(rs)} fixture{'s' if len(rs)!=1 else ''} from {esc(rs[0]['league'])} in the 21–27 October 2026 window.
Lines are model output; the evidence column says whether both sides, one side, or neither side had a verified strength
input.</p>
{stat_cards(rs, [p for p in preds if p['sport'] == sport])}
<div class="panel"><h2>Fixtures and originated markets</h2>
{fixture_table(rs, sources)}
<p class="small muted">Prices are home/away for the moneyline; handicap and total are shown as the price for the
home line / away line. “blank” means the input needed to originate that market was not on an official page.</p></div>
<div class="panel"><h2>Sources for these rows</h2>
<ul class="small">{"".join(f'<li><a href="{esc(src[i]["url"])}" target="_blank" rel="noopener">{esc(src[i]["name"])}</a></li>' for i in srcs)}</ul>
</div>"""
        (SITE_OUT / f"{slug}.html").write_text(page(sport, body, f"{slug}.html"))

    # ---- picks --------------------------------------------------------
    order = {"High": 0, "Medium": 1, "Low": 2}
    picks = sorted(rows, key=lambda r: (order[r["confidence"]], -r["edge"]))
    body = [f'<h1 class="page">Picks</h1><p class="lede">All {len(picks)} picks, strongest model edge first within each band. '
            f'The pick is the side with the higher originated probability; the edge column is '
            f'<code>|p − 0.5|</code>.</p>',
            '<div class="panel"><h2>Model picks</h2>',
            '<div class="toolbar"><input id="q" type="search" placeholder="Search team, league, date…" aria-label="Search">'
            '<select id="conf" aria-label="Confidence"><option value="">All confidence</option><option>High</option>'
            '<option>Medium</option><option>Low</option></select>'
            '<select id="sport" aria-label="Sport"><option value="">All sports</option>'
            + "".join(f"<option>{esc(s)}</option>" for s in sorted(by_sport))
            + '</select><span id="count" class="muted small"></span></div>',
            '<div class="tablewrap"><table data-filter="1"><thead><tr><th>Date</th><th>Sport</th><th>Match</th>'
            '<th>Selection</th><th>Price</th><th>p</th><th>Edge</th><th>Conf.</th><th>Why</th><th>Source</th></tr></thead><tbody>']
    for r in picks:
        body.append(
            f'<tr data-conf="{r["confidence"]}" data-sport="{esc(r["sport"])}"><td class="num">{esc(r["date"])}</td>'
            f'<td>{esc(r["sport"])}</td><td>{esc(r["away"])} @ {esc(r["home"])}</td>'
            f'<td><strong>{esc(r["pick"]["team"])}</strong></td><td class="num">{r["pick"]["price"]:.2f}</td>'
            f'<td class="num">{r["pick"]["prob"]:.3f}</td><td class="num">{r["edge"]:.3f}</td>'
            f'<td>{badge(r["confidence"])}</td><td class="small">{esc(r["confidence_note"])}</td>'
            f'<td class="src"><a href="{esc(src[r["source_id"]]["url"])}" target="_blank" rel="noopener">'
            f'{esc(src[r["source_id"]]["domain"])}</a></td></tr>')
    body.append("</tbody></table></div></div>")
    (SITE_OUT / "picks.html").write_text(page("Picks", "".join(body), "picks.html"))

    # ---- predictions ---------------------------------------------------
    pbody = [f'<h1 class="page">Predictions</h1><p class="lede">One written selection per High-confidence row, '
             f'{len(preds)} in total. Each names the selection, the market, the verified current form and the most recent '
             f'official result, and lists the official facts it relies on.</p>']
    for p in preds:
        facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
        slist = "".join(
            f'<li><a href="{esc(src[s]["url"])}" target="_blank" rel="noopener">{esc(src[s]["name"])}</a></li>'
            for s in p["sources"])
        pbody.append(f"""<article class="pred" id="{esc(p['prediction_id'])}">
<p class="meta">{esc(p['prediction_id'])} · {esc(p['date'])} · {esc(p['match'])} · {esc(p['sport'])} · {p['word_count']} words · {badge(p['confidence'])}</p>
<h3>{esc(p['headline'])}</h3>
<p class="body">{esc(p['text'])}</p>
<p class="small"><strong>Selection:</strong> {esc(p['pick']['team'])} to win — moneyline @ {p['pick']['price']:.2f}
(originated probability {p['pick']['prob']:.3f}).</p>
<p class="small muted" style="margin:10px 0 4px">Verified facts used</p>
<ul>{facts}</ul>
<p class="small muted" style="margin:10px 0 4px">Official sources</p>
<ul class="small">{slist}</ul>
</article>""")
    (SITE_OUT / "predictions.html").write_text(page("Predictions", "".join(pbody), "predictions.html"))

    # ---- coverage ------------------------------------------------------
    crow = "".join(
        f'<tr><td><strong>{esc(c["sport"])}</strong></td>'
        f'<td><span class="chip {"ok" if c["status"]=="covered" else "warn"}">{esc(c["status"])}</span></td>'
        f'<td class="num">{c["fixtures"]}</td><td class="small">{esc(c["source"])}</td><td class="small">{esc(c["note"])}</td></tr>'
        for c in S.COVERAGE)
    covered = sum(1 for c in S.COVERAGE if c["status"] == "covered")
    body = f"""<h1 class="page">Coverage</h1>
<p class="lede">The OLBG sport universe after applying the brief's exclusions, with the decision for every sport. {covered} sports
carry published rows; the rest are shown with the reason no verified row exists. Nothing is silently dropped.</p>
<div class="panel"><h2>Sport-by-sport decision</h2>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Status</th><th>Rows</th><th>Source</th><th>Note</th></tr></thead>
<tbody>{crow}</tbody></table></div></div>
<div class="panel"><h2>Exclusions applied</h2>
<p class="small">Excluded by the brief and therefore absent from every table: soccer, boxing, UFC/MMA, American football,
hurling, horse racing, cycling, specials. Gaelic games are Gaelic football, which the brief does not exclude, but no
official fixture page was captured this pass, so no Gaelic rows are published.</p></div>"""
    (SITE_OUT / "coverage.html").write_text(page("Coverage", body, "coverage.html"))

    # ---- flagged -------------------------------------------------------
    fbody = [f'<h1 class="page">Flagged for Review</h1>',
             '<p class="lede">Everything that could not be verified, had to be left blank, or is inconsistent in the wider '
             'repository. Each item carries the source link or file path needed to check it. None of these block '
             'publication.</p>',
             '<div class="panel"><h2>Open items</h2><div class="tablewrap"><table><thead><tr>'
             '<th>ID</th><th>Severity</th><th>Area</th><th>Item</th><th>Detail</th><th>Evidence checked</th>'
             '<th>Source / file</th></tr></thead><tbody>']
    for i, f in enumerate(FLAGGED, start=1):
        sev = f["sev"]
        cls = {"high": "warn", "medium": "warn", "low": ""}.get(sev, "")
        link = (f'<a href="{esc(f["url"])}" target="_blank" rel="noopener">{esc(f["url"])}</a>'
                if f.get("url") else f'<code>{esc(f.get("path",""))}</code>')
        fbody.append(
            f'<tr><td class="num">F-{i:02d}</td><td><span class="chip {cls}">{esc(sev)}</span></td>'
            f'<td>{esc(f["area"])}</td><td>{esc(f["item"])}</td><td class="small">{esc(f["detail"])}</td>'
            f'<td class="small">{esc(f.get("evidence", ""))}</td>'
            f'<td class="src">{link}</td></tr>')
    fbody.append("</tbody></table></div></div>")
    ds_rows = "".join(
        "<tr><td>{}</td><td class=\"num\">{}</td><td class=\"num\">{}</td>"
        "<td class=\"num\">{}</td><td class=\"num\">{}</td></tr>".format(
            esc(c["dataset"]), c["rows"], c["sourced"], c["official"], c["olbg"])
        for c in counts)
    cf_rows = "".join(
        "<tr><td>{}</td><td class=\"small\">{}</td></tr>".format(
            esc(c["pair"]), esc("; ".join(c["entries"])))
        for c in conflicts)
    fbody.append("""<div class="panel"><h2>Mechanical audit of the builds already in this repository</h2>
<p class="small">Read-only scan of the three fixture files committed by earlier sessions. Counts and domain classes are
computed from those files at build time; no value from them is republished here.</p>
<div class="tablewrap"><table><thead><tr><th>Dataset</th><th>Rows</th><th>Rows with a source URL</th>
<th>Source on an official league / governing-body domain</th><th>Source on OLBG.com</th></tr></thead><tbody>
""" + ds_rows + """</tbody></table></div>
<p class="small" style="margin-top:14px">Same fixture, different pick across builds — matched on both club names, because
the earlier builds do not share a comparable date field: <strong>""" + str(len(conflicts)) + """</strong></p>
<div class="tablewrap"><table><thead><tr><th>Fixture</th><th>Picks recorded</th></tr></thead><tbody>
""" + cf_rows + """</tbody></table></div>
<p class="small" style="margin-top:12px">Consequence: the repository publishes several independent, non-reconciled tables
for overlapping windows. This desk is one more, deliberately separate, dataset; retiring or merging the older builds needs
a decision from the repository owner, so it is flagged rather than done unilaterally.</p></div>""")
    (SITE_OUT / "flagged.html").write_text(page("Flagged for Review", "".join(fbody), "flagged.html"))

    # ---- methodology ---------------------------------------------------
    body = f"""<h1 class="page">Methodology</h1>
<p class="lede">Everything needed to reproduce or challenge a price: the inputs, the formulas, the constants and the
thresholds. The build refuses to publish if a row loses its source, its pick, or its blank-value reason.</p>
<div class="panel"><h2>1. Verified inputs</h2>
<div class="kv">
<div>Ice hockey</div><div>NHL.com standings, all 32 clubs: games played, points percentage, goals for and against
(21 October, 03:10 EDT). League scoring average <code>2 × ΣGF / ΣGP = {NHL_AVG['goals_per_game']:.2f}</code> goals per game
from the same table (ΣGF {NHL_AVG['gf']}, ΣGP {NHL_AVG['gp']}).</div>
<div>Basketball</div><div>NBA.com 2026-27 standings: six clubs had played one game at capture, the rest none. Ratings use a
{MODEL['nba_prior_games']:g}-game shrinkage prior, so a 1-0 club rates {(1+3)/7:.3f} and a 0-1 club {(0+3)/7:.3f}.</div>
<div>Baseball</div><div>MLB.com final 2026 regular-season records for the two World Series clubs
(Milwaukee {S.MLB['Milwaukee Brewers'][0]}-{S.MLB['Milwaukee Brewers'][1]}, Tampa Bay {S.MLB['Tampa Bay Rays'][0]}-{S.MLB['Tampa Bay Rays'][1]}).</div>
<div>Snooker</div><div>WST round-one frame scores for the players whose result appears on the match list; a player with no
captured score sits on a 0.5 prior and the row says so.</div>
<div>Darts, handball</div><div>No verified strength or ranking feed was captured, so these rows use a 0.5 prior (handball
adds the declared home edge) and are marked prior-only.</div>
</div></div>
<div class="panel"><h2>2. Originated prices</h2>
<div class="kv">
<div>Moneyline</div><div><code>p_home = 0.5 + {MODEL['nhl_weight']} × (rating_home − rating_away) + {MODEL['home_edge']}</code>,
clamped to [0.05, 0.95]; prices are <code>1 / (p × {MODEL['margin']})</code> — a {int((1-MODEL['margin'])*100)}% theoretical margin.</div>
<div>Baseball</div><div>Ratings are final-season win percentages combined with log5, plus a 0.02 home edge.</div>
<div>Puck line</div><div>Expected goals for each club are built from its own GF/GP and the opponent's GA/GP,
scaled to the league rate and shifted by ±{int(MODEL['nhl_home_goals']*100)}% for home ice; the margin is the difference.
P(win by 2+) comes from a normal distribution with sd {MODEL['nhl_puck_sigma']}, priced at ±1.5. So a high-scoring club
gets a bigger projected margin than a low-scoring one with the same points percentage.</div>
<div>Total</div><div>The expected total is the sum of the two expected-goals figures above (league
{NHL_AVG['goals_per_game']:.2f} goals per game), rounded to the nearest half goal and held between 4.5 and 8.5;
over/under comes from a normal distribution with sd {MODEL['nhl_total_sigma']}. Two defensive clubs therefore get a
lower line than two offensive ones.</div>
<div>Other markets</div><div>No handicap or total is originated where the necessary input (a scoring average, a leg model, a
run environment) was not on an official page. The cell says “blank” and names the missing input.</div>
</div></div>
<div class="panel"><h2>3. Confidence rule</h2>
<table><thead><tr><th>Band</th><th>Requirement</th></tr></thead><tbody>
<tr><td>{badge('High')}</td><td>Both competitors have a verified strength sample <em>and</em> the model edge
<code>|p − 0.5| ≥ {MODEL['high_edge']:.2f}</code> <em>and</em> verified player-level evidence is recorded for the fixture.
Every High row carries a written prediction.</td></tr>
<tr><td>{badge('Medium')}</td><td>Both sides sampled with edge ≥ {MODEL['medium_edge']:.2f}, or one side sampled with edge
≥ {MODEL['high_edge']:.2f}, or a large edge that is capped because no player-level evidence exists.</td></tr>
<tr><td>{badge('Low')}</td><td>Everything else, including prior-only rows and rows where the model shows no edge.</td></tr>
</tbody></table></div>
<div class="panel"><h2>4. Reproduce it</h2>
<p class="small"><code>python3 scripts/session-8070bc18/build.py</code> rebuilds <code>data/session-8070bc18/desk.json</code>
and every page in <code>docs/desk/</code>, and fails the build if a row has no official source, no pick, no price, a blank
market without a reason, a prediction under 30 words, a duplicate prediction, a prediction that does not name its
selection, or a High row without a prediction.</p></div>
<div class="panel"><h2>5. Known limits</h2>
<ul class="small">
<li>Standings are a snapshot: {S.CAPTURED_AT}. Later games change every rating.</li>
<li>NHL venues and MLB ballparks are blank because the schedule pages used do not publish them.</li>
<li>The WST list page renders clock times in the reader's locale, so snooker start times are blank.</li>
<li>NBA, darts and handball samples are too thin for High confidence; that is a property of the data, not of the picks.</li>
<li>No closing-line comparison is possible: no bookmaker or OLBG price is read anywhere in this build.</li>
</ul></div>"""
    (SITE_OUT / "methodology.html").write_text(page("Methodology", body, "methodology.html"))

    # ---- sources -------------------------------------------------------
    rows_html = "".join(
        f'<tr><td>{esc(s["name"])}</td><td><a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["domain"])}</a></td>'
        f'<td class="small">{esc(s["used_for"])}</td><td class="num small">{esc(s["captured"])}</td></tr>'
        for s in sources)
    body = f"""<h1 class="page">Sources</h1>
<p class="lede">Every published value traces to one of these pages, all on a league or governing-body domain. They were read
in this session with the agent web-fetch tool; direct <code>curl</code> to these hosts is blocked by the sandbox egress
allowlist, which is why the captured timestamps matter.</p>
<div class="panel"><div class="tablewrap"><table><thead><tr><th>Page</th><th>Domain</th><th>What it verified</th>
<th>Captured (UTC)</th></tr></thead><tbody>{rows_html}</tbody></table></div></div>
<div class="panel"><h2>Not used as sources</h2>
<p class="small">OLBG.com, ESPNcricinfo, Sky Sports, Sporting News, Wikipedia and any tipster or aggregator page. They were
not used for any published value, because the brief requires official sources only. Where a fixture list only existed on
such a site, the sport appears on the coverage page as a gap instead of as rows.</p></div>"""
    (SITE_OUT / "sources.html").write_text(page("Sources", body, "sources.html"))

    # ---- link check ----------------------------------------------------
    return check_links()


SPORT_PAGES = {"Ice Hockey": "nhl", "Basketball": "nba", "Baseball": "mlb",
               "Darts": "darts", "Handball": "handball", "Snooker": "snooker"}


def sport_slug(sport):
    return SPORT_PAGES.get(sport, sport.lower().replace(" ", "-"))


def sport_page(sport):
    return f"{sport_slug(sport)}.html"


def pairs_text(conflicts):
    if not conflicts:
        return ""
    bits = []
    for c in conflicts[:6]:
        bits.append(" · ".join(f"{lab}: {pick}" for lab, pick in c))
    return "Examples: " + "; ".join(bits) + "."


def check_links():
    broken, total = [], 0
    for f in sorted(SITE_OUT.glob("*.html")):
        text = f.read_text()
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            total += 1
            target = (f.parent / href.split("#")[0]).resolve()
            if not target.exists():
                broken.append((f.name, href))
    return total, broken


# ---------------------------------------------------------------------------
# flagged items
# ---------------------------------------------------------------------------

FLAGGED = [
    dict(sev="high", area="Coverage",
         item="Nine in-scope sports publish no match rows",
         detail="Tennis, cricket, rugby union, rugby league, volleyball, badminton, table tennis, esports and "
                "greyhound racing are in the sport list but have no row here. Each needs a governing-body fixture "
                "page with a per-match URL; no aggregator fixture is substituted.",
         evidence="atptour.com, icc-cricket.com, world.rugby, volleyballworld.com, bwfbadminton.com and "
                  "worldtabletennis.com either failed to load from this environment (TLS/egress) or listed no "
                  "fixture inside 21-27 Oct 2026 with a match-level source link. Rechecked 21 Oct 08:05Z.",
         url="https://www.atptour.com/en/scores/current"),
    dict(sev="high", area="Repository",
         item="Parallel fixture tables coexist and disagree",
         detail="Earlier sessions committed whole boards of their own. The mechanical audit below counts them and "
                "names the fixtures that carry different winners in different builds. Reconciling or retiring those "
                "tables is an owner decision, so nothing of theirs is deleted here.",
         evidence="Counts and conflicts are recomputed at build time from data/rows.json, data/board.json and "
                  "data/matches.json; a conflict is only reported when both club names match and the picks differ.",
         path="data/rows.json, data/board.json, data/matches.json"),
    dict(sev="high", area="Publication",
         item="Two generators wrote the root pages, so the Pages deploy gate was red",
         detail="Root, sports/ and the topic pages are generated by scripts/session-83451f65, but pages.yml "
                "regenerated them with tools/build_master*.py and failed its staleness check on every push, so its "
                "deploy step never ran and the live site kept serving an older artefact. Board P resolved it by "
                "pointing the master tools at their own board/ directory; recorded here because it explains why "
                "published pages can lag the repository.",
         evidence="A clean checkout of main plus the three session-83451f65 scripts leaves no diff; the master tools "
                  "changed 12 tracked files and reordered data/master.json between runs. Rechecked after Board P's "
                  "PR #47.",
         path=".github/workflows/pages.yml"),
    dict(sev="medium", area="Snooker",
         item="Northern Ireland Open start times are blank",
         detail="The WST match list prints clock times in the reader's locale and does not state a venue-local "
                "start, so dates are reproduced and times are left blank rather than converted.",
         evidence="wst.tv/matches shows 05:00, 08:00 and 10:00 tags on the same session block, which cannot be a "
                  "single local clock; no timezone is printed on the page.",
         url="https://www.wst.tv/matches"),
    dict(sev="medium", area="Venues",
         item="NHL arenas, MLB ballparks and EHF halls are blank",
         detail="The schedule pages used for these rows do not print the venue, and opening every game page was "
                "outside this pass. Venues stay blank rather than being inferred from the home club.",
         evidence="Checked on nhl.com/schedule (date, matchup, result only), mlb.com/postseason (date, time, "
                  "broadcaster) and ehfcl.eurohandball.com match list (time and pairing only).",
         url="https://www.nhl.com/schedule"),
    dict(sev="medium", area="NBA",
         item="The NBA sample is one game per club, so no NBA row can reach High",
         detail="On 21 Oct only four clubs had a 2026-27 result. The model shrinks each club toward .500, so every "
                "NBA line is Low or Medium and no NBA prediction is published.",
         evidence="nba.com/standings shows 26 clubs at 0-0 with a single game played; the shrinkage weight is "
                  "declared on the methodology page.",
         url="https://www.nba.com/standings"),
    dict(sev="medium", area="Darts",
         item="Darts lines are prior-only",
         detail="The 16 ties, venue and session windows are verified, but the PDC rankings page is behind a consent "
                "wall here, so no ranking or form input was captured and every darts line is 50/50. The PDC does not "
                "publish per-match throw times, only the session window.",
         evidence="pdc.tv/rankings returned only the CookieYes dialog on 21 Oct; the dated PDC news article gave the "
                  "draw, the venue and the session times.",
         url="https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/"),
    dict(sev="medium", area="Handball",
         item="Handball lines are prior-only and the timezone is unstated",
         detail="The EHF match list prints 18:45 and 20:45 without a timezone, so times are reproduced verbatim with "
                "that warning. No EHF strength table was captured, so the line is a 50/50 prior plus the declared "
                "home edge.",
         evidence="ehfcl.eurohandball.com/men/2026-27/matches/ prints the times and pairings with per-match links "
                  "but no zone label and no standings for these clubs.",
         url="https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    dict(sev="low", area="Model",
         item="The constants are declared assumptions, not fitted values",
         detail="Weights, home edge, puck-line and total dispersions, the shrinkage prior and the confidence "
                "thresholds are listed on the methodology page. None is calibrated against closing prices, because "
                "no market price is read anywhere in this build.",
         evidence="Every constant appears in scripts/session-8070bc18/build.py under MODEL and NHL_TOTAL.",
         path="scripts/session-8070bc18/build.py"),
    dict(sev="low", area="Prediction evidence",
         item="Player names appear as initial plus surname",
         detail="NHL.com publishes the winning goalie and the game-winning scorer in that form, so the predictions "
                "reproduce it instead of expanding first names.",
         evidence="For example 'M. Celebrini' and 'A. Nedeljkovic' on the 20 Oct result lines.",
         url="https://www.nhl.com/schedule"),
]


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

EXPECTED = {
    "Ice Hockey": {"2026-10-21": 2, "2026-10-22": 12, "2026-10-23": 2, "2026-10-24": 12, "2026-10-25": 5},
    "Basketball": {"2026-10-21": 11, "2026-10-22": 2, "2026-10-23": 12, "2026-10-24": 8, "2026-10-25": 7},
    "Baseball": {"2026-10-23": 1, "2026-10-24": 1, "2026-10-26": 1, "2026-10-27": 1},
    "Darts": {"2026-10-22": 8, "2026-10-23": 8},
    "Handball": {"2026-10-22": 5},
    "Snooker": {"2026-10-21": 10},
}


def check_counts(rows):
    """Assert the row count per sport and date against the counts printed on the
    official pages (NHL "N Games" headers, NBA "N Games", PDC 8+8 ties, etc.)."""
    seen = defaultdict(int)
    for r in rows:
        seen[(r["sport"], r["date"])] += 1
    problems = []
    for sport, dates in EXPECTED.items():
        for d, n in dates.items():
            if seen.get((sport, d), 0) != n:
                problems.append(f"{sport} {d}: expected {n}, found {seen.get((sport, d), 0)}")
    return problems


def main():
    rows = nhl_rows() + nba_rows() + mlb_rows() + pdc_rows() + ehf_rows() + wst_rows()
    problems = check_counts(rows)
    if problems:
        print("COUNT MISMATCH vs official page totals:")
        for p in problems:
            print(" -", p)
        raise SystemExit(1)
    rows = assign(rows)
    # attach results across all rows through one shared table
    preds = attach_predictions(rows)
    errors, checks = validate(rows, preds, S.SOURCES)
    if errors:
        print("VALIDATION ERRORS:")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)

    counts, conflicts = audit_existing()
    links_total, broken = write_site(rows, preds, S.SOURCES, None, checks, conflicts, counts)
    if broken:
        print("BROKEN LINKS:")
        for b in broken:
            print(" -", b)
        raise SystemExit(1)

    desk = dict(
        meta=dict(session="arena/8070bc18-olbg4", captured_at=S.CAPTURED_AT,
                  window="2026-10-21..2026-10-27", model=MODEL,
                  nhl_league_average=round(NHL_AVG["goals_per_game"], 4),
                  generator="scripts/session-8070bc18/build.py"),
        sources=S.SOURCES,
        fixtures=rows,
        predictions=preds,
        coverage=S.COVERAGE,
        flagged=FLAGGED,
        audit=dict(counts=counts, conflicts=conflicts),
        validation=dict(checks=[(n, bool(ok)) for n, ok in checks], local_links=links_total, broken_links=0),
        stats=dict(
            fixtures=len(rows), predictions=len(preds),
            confidence=dict(Counter(r["confidence"] for r in rows)),
            sports=len({r["sport"] for r in rows}),
            priced=sum(1 for r in rows if r["ml_home"]),
            handicap=sum(1 for r in rows if r["handicap"]),
            total=sum(1 for r in rows if r["total"]),
        ),
    )
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    (DATA_OUT / "desk.json").write_text(json.dumps(desk, indent=2, ensure_ascii=False) + "\n")

    c = Counter(r["confidence"] for r in rows)
    print(f"fixtures {len(rows)} across {len({r['sport'] for r in rows})} sports")
    print(f"confidence: High {c['High']} · Medium {c['Medium']} · Low {c['Low']}")
    print(f"predictions: {len(preds)} (words {min(p['word_count'] for p in preds)}–{max(p['word_count'] for p in preds)})")
    print(f"markets: moneyline {sum(1 for r in rows if r['ml_home'])}, handicap {sum(1 for r in rows if r['handicap'])}, "
          f"total {sum(1 for r in rows if r['total'])}")
    print(f"local links checked: {links_total}, broken 0")
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


if __name__ == "__main__":
    main()

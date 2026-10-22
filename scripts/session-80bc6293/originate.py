#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) — originate our own lines, pick a winner, grade confidence.

Inputs (all committed bytes / verified transcriptions):
  data/session-80bc6293/parsed/nhl.json        NHL official API schedule + standings
  data/session-80bc6293/parsed/mlb.json        MLB Stats API World Series schedule + 2026 standings
  data/session-80bc6293/official_urc.json      URC official Match Centre (rendered page transcription)
  data/session-80bc6293/parsed/motor.json      formula1.com + motogp.com official calendars
  data/session-80bc6293/parsed/plusliga.json   plusliga.pl official table
  data/session-80bc6293/parsed/olbg.json       OLBG.com sport hubs (reverse-engineered inventory)
  data/session-80bc6293/model_assumptions.json every modelling constant, with its justification

No bookmaker price is used to build a line: every fair price here is 1 / model probability.
Where an official league feed publishes market prices (NHL.com's odds feed) the median of those
prices is recorded separately and used only for the brief's -250...+10000 window test.
"""
from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")
CUTOFF = "2026-10-22T13:00:00Z"          # anything already in play / finished at claim time is excluded
WINDOW_MIN_AMERICAN = -250
WINDOW_MAX_AMERICAN = 10000


# ------------------------------------------------------------------ pricing maths
def fair_decimal(p: float) -> float:
    return 1.0 / p if p > 0 else float("inf")


def to_american(dec: float) -> int:
    if dec is None or not math.isfinite(dec) or dec <= 1.0:
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def american_from_prob(p: float) -> int:
    return to_american(fair_decimal(p))


def american_to_decimal(a: str | float) -> float | None:
    """NHL's feed mixes decimal ('2.26') and American ('+130', '-155') strings."""
    try:
        v = float(str(a).replace("+", ""))
    except (TypeError, ValueError):
        return None
    if abs(v) < 1.05:            # decimal odds are always >= 1.01
        return None
    if abs(v) <= 25 and v > 0 and "." in str(a):   # e.g. 2.26 / 1.67
        return v
    if abs(v) >= 100:            # american
        return 1 + v / 100.0 if v > 0 else 1 + 100.0 / abs(v)
    return v if v > 1.0 else None


def in_window(american: int) -> bool:
    return american != 0 and WINDOW_MIN_AMERICAN <= american <= WINDOW_MAX_AMERICAN


def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_matrix(lh: float, la: float, maxg: int = 12):
    ph = [poisson_pmf(lh, i) for i in range(maxg + 1)]
    pa = [poisson_pmf(la, j) for j in range(maxg + 1)]
    return ph, pa


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def confidence(p: float, sample_ok: bool, window_ok: bool) -> str:
    """Documented grading rule (see model_assumptions.json)."""
    if p >= 0.70 and sample_ok and window_ok:
        return "High"
    if p >= 0.70:
        return "Medium"          # probability is there but evidence sample or price window is not
    if p >= 0.55:
        return "Medium"
    return "Low"


# ------------------------------------------------------------------ NHL
def build_nhl(rows: list, flagged: list, assumptions: dict) -> None:
    doc = json.load(open(os.path.join(DATA, "parsed", "nhl.json"), encoding="utf-8"))
    teams, games = doc["teams"], doc["games"]
    gp_all = sum(t["gamesPlayed"] for t in teams.values())
    gf_all = sum(t["goalFor"] for t in teams.values())
    lam_league = gf_all / gp_all if gp_all else 3.0
    hgf = sum(t["homeGoalsFor"] for t in teams.values())
    hgp = sum(t["homeGamesPlayed"] for t in teams.values())
    rgf = sum(t["roadGoalsFor"] for t in teams.values())
    rgp = sum(t["roadGamesPlayed"] for t in teams.values())
    hfa_mult = math.sqrt((hgf / hgp) / (rgf / rgp)) if (hgp and rgp and rgf) else 1.0
    home_ot_wins = sum(t["regulationPlusOtWins"] - t.get("homeRegulationWins", 0) if False else 0 for t in teams.values())
    # OT/SO decisions: regulationPlusOtWins - regulationWins, split home/road
    home_otso = sum(t.get("homeRegulationPlusOtWins", 0) - t.get("homeRegulationWins", 0) for t in teams.values())
    road_otso = sum(t.get("roadRegulationPlusOtWins", 0) - t.get("roadRegulationWins", 0) for t in teams.values())
    p_home_ot = home_otso / (home_otso + road_otso) if (home_otso + road_otso) else 0.5
    K = assumptions["nhl"]["shrinkage_games"]
    maxg = assumptions["nhl"]["poisson_max_goals"]

    def shrunk_rate(num: float, den: float, k: float) -> float:
        """Shrink an official per-game rate toward the official league rate by its own sample size."""
        if not den:
            return lam_league
        raw = num / den
        w = den / (den + k)
        return lam_league + (raw - lam_league) * w

    W_SEASON, W_VENUE, W_L10 = 0.45, 0.30, 0.25
    K_SEASON, K_VENUE, K_L10 = K, K, 8

    def attack_rate(t: dict, at_home: bool) -> float:
        season = shrunk_rate(t["goalFor"], t["gamesPlayed"], K_SEASON)
        venue = shrunk_rate(t["homeGoalsFor"] if at_home else t["roadGoalsFor"],
                            t["homeGamesPlayed"] if at_home else t["roadGamesPlayed"], K_VENUE)
        l10 = shrunk_rate(t["l10GoalsFor"], t.get("l10GamesPlayed", t["gamesPlayed"]), K_L10)
        return W_SEASON * season + W_VENUE * venue + W_L10 * l10

    def concede_rate(t: dict, at_home: bool) -> float:
        season = shrunk_rate(t["goalAgainst"], t["gamesPlayed"], K_SEASON)
        venue = shrunk_rate(t["homeGoalsAgainst"] if at_home else t["roadGoalsAgainst"],
                            t["homeGamesPlayed"] if at_home else t["roadGamesPlayed"], K_VENUE)
        l10 = shrunk_rate(t["l10GoalsAgainst"], t.get("l10GamesPlayed", t["gamesPlayed"]), K_L10)
        return W_SEASON * season + W_VENUE * venue + W_L10 * l10

    n_priced = 0
    for g in sorted(games, key=lambda x: x["startTimeUTC"]):
        if g["startTimeUTC"] <= CUTOFF or g["gameState"] != "FUT":
            continue
        h, a = teams.get(g["homeAbbrev"]), teams.get(g["awayAbbrev"])
        if not h or not a:
            flagged.append({"id": f"AF-NHL-{g['id']}", "sport": "Ice Hockey",
                            "issue": "NHL game listed on the official schedule but a team is missing from the official standings",
                            "fixture": f"{g['away']} @ {g['home']}", "date": g["date"],
                            "action": "published with blank line", "source_url": g["gameCenterLink"]})
            continue
        lh = lam_league * (attack_rate(h, True) / lam_league) * (concede_rate(a, False) / lam_league) * hfa_mult
        la = lam_league * (attack_rate(a, False) / lam_league) * (concede_rate(h, True) / lam_league) / hfa_mult
        ph, pa = poisson_matrix(lh, la, maxg)
        p_home_reg = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if i > j)
        p_away_reg = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if j > i)
        p_tie = sum(ph[i] * pa[i] for i in range(maxg + 1))
        p_home = p_home_reg + p_tie * p_home_ot
        p_away = 1.0 - p_home
        p_home_minus15 = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if i - j >= 2)
        p_away_minus15 = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if j - i >= 2)
        tot = round(2 * lam_league * 2) / 2 if assumptions["nhl"]["total_line"] == "auto" else assumptions["nhl"]["total_line"]
        tot = tot + 0.5 if float(tot).is_integer() else tot
        p_over = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if i + j > tot)
        p_over_hi = sum(ph[i] * pa[j] for i in range(maxg + 1) for j in range(maxg + 1) if i + j > tot + 1)
        # official market price (NHL.com odds feed) — median across the providers NHL publishes
        decs = [d for d in (american_to_decimal(x) for x in g["odds_home"]) if d] + \
               [d for d in (american_to_decimal(x) for x in g["odds_away"]) if d]
        market = {}
        if decs:
            ds = sorted(decs)
            mid = ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2
            market = {"median_decimal_all_sides": round(mid, 4), "providers_read": len(decs),
                      "raw_home": g["odds_home"], "raw_away": g["odds_away"]}
        home_market_am = None
        home_decs = [d for d in (american_to_decimal(x) for x in g["odds_home"]) if d]
        if home_decs:
            ds = sorted(home_decs)
            mid = ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2
            home_market_am = to_american(mid)
        away_decs = [d for d in (american_to_decimal(x) for x in g["odds_away"]) if d]
        away_market_am = None
        if away_decs:
            ds = sorted(away_decs)
            mid = ds[len(ds) // 2] if len(ds) % 2 else (ds[len(ds) // 2 - 1] + ds[len(ds) // 2]) / 2
            away_market_am = to_american(mid)

        sample_ok = min(h["gamesPlayed"], a["gamesPlayed"]) >= assumptions["min_games_for_high"]
        pick_home = p_home >= p_away
        pick_p = p_home if pick_home else p_away
        pick_name = g["home"] if pick_home else g["away"]
        pick_am = american_from_prob(pick_p)
        pick_market_am = home_market_am if pick_home else away_market_am
        window_ok = in_window(pick_am) or (pick_market_am is not None and in_window(pick_market_am))
        conf = confidence(pick_p, sample_ok, window_ok)

        markets = [
            {"market": "Match Winner (incl. OT/SO)", "selection": g["home"], "line": "",
             "p": round(p_home, 4), "fair_dec": round(fair_decimal(p_home), 4), "fair_american": to_american(fair_decimal(p_home)),
             "official_market_american": home_market_am,
             "official_market_raw": g["odds_home"]},
            {"market": "Match Winner (incl. OT/SO)", "selection": g["away"], "line": "",
             "p": round(p_away, 4), "fair_dec": round(fair_decimal(p_away), 4), "fair_american": to_american(fair_decimal(p_away)),
             "official_market_american": away_market_am,
             "official_market_raw": g["odds_away"]},
            {"market": f"Puck Line {h['abbrev']} -1.5", "selection": f"{g['home']} -1.5", "line": "-1.5",
             "p": round(p_home_minus15, 4), "fair_dec": round(fair_decimal(p_home_minus15), 4),
             "fair_american": to_american(fair_decimal(p_home_minus15))},
            {"market": f"Puck Line {a['abbrev']} +1.5", "selection": f"{g['away']} +1.5", "line": "+1.5",
             "p": round(1 - p_home_minus15, 4), "fair_dec": round(fair_decimal(1 - p_home_minus15), 4),
             "fair_american": to_american(fair_decimal(1 - p_home_minus15))},
            {"market": f"Puck Line {a['abbrev']} -1.5", "selection": f"{g['away']} -1.5", "line": "-1.5",
             "p": round(p_away_minus15, 4), "fair_dec": round(fair_decimal(p_away_minus15), 4),
             "fair_american": to_american(fair_decimal(p_away_minus15))},
            {"market": f"Puck Line {h['abbrev']} +1.5", "selection": f"{g['home']} +1.5", "line": "+1.5",
             "p": round(1 - p_away_minus15, 4), "fair_dec": round(fair_decimal(1 - p_away_minus15), 4),
             "fair_american": to_american(fair_decimal(1 - p_away_minus15))},
            {"market": f"Total Goals Over {tot}", "selection": f"Over {tot}", "line": str(tot),
             "p": round(p_over, 4), "fair_dec": round(fair_decimal(p_over), 4), "fair_american": to_american(fair_decimal(p_over))},
            {"market": f"Total Goals Under {tot}", "selection": f"Under {tot}", "line": str(tot),
             "p": round(1 - p_over, 4), "fair_dec": round(fair_decimal(1 - p_over), 4),
             "fair_american": to_american(fair_decimal(1 - p_over))},
            {"market": f"Total Goals Over {tot + 1}", "selection": f"Over {tot + 1}", "line": str(tot + 1),
             "p": round(p_over_hi, 4), "fair_dec": round(fair_decimal(p_over_hi), 4),
             "fair_american": to_american(fair_decimal(p_over_hi))},
            {"market": f"Total Goals Under {tot + 1}", "selection": f"Under {tot + 1}", "line": str(tot + 1),
             "p": round(1 - p_over_hi, 4), "fair_dec": round(fair_decimal(1 - p_over_hi), 4),
             "fair_american": to_american(fair_decimal(1 - p_over_hi))},
        ]
        rows.append({
            "sport": "Ice Hockey", "competition": "NHL 2026-27 Regular Season",
            "date": g["date"], "time_utc": g["startTimeUTC"], "venue": g["venue"],
            "home": g["home"], "away": g["away"],
            "source_url": g["gameCenterLink"],
            "source_name": "NHL.com official game centre (schedule + standings + published odds feed from the NHL official API)",
            "source_evidence": {"schedule_api": doc["source_schedule"], "standings_api": doc["source_standings"],
                                "standings_as_of_utc": doc["standings_as_of_utc"], "sha256_standings": doc["sha256_standings"]},
            "model": "Poisson goal model on official NHL 2026-27 per-game scoring rates, shrunk to the league mean, "
                     "with home-ice advantage derived from the official home/road scoring splits; OT/SO resolved with the "
                     "official home share of overtime/shootout decisions.",
            "model_inputs": {
                "league_goals_per_team_game": round(lam_league, 4),
                "home_ice_multiplier": round(hfa_mult, 4),
                "p_home_wins_ot_or_so": round(p_home_ot, 4),
                "shrinkage_games_K": K,
                "home": {"gamesPlayed": h["gamesPlayed"], "points": h["points"], "pointPctg": h["pointPctg"],
                         "goalFor": h["goalFor"], "goalAgainst": h["goalAgainst"],
                         "last10": f"{h['l10Wins']}-{h['l10Losses']}-{h['l10OtLosses']}",
                         "streak": f"{h['streakCode']}{h['streakCount']}",
                         "home_record": f"{h['homeWins']}-{h['homeLosses']}-{h['homeOtLosses']}",
                         "lambda": round(lh, 4)},
                "away": {"gamesPlayed": a["gamesPlayed"], "points": a["points"], "pointPctg": a["pointPctg"],
                         "goalFor": a["goalFor"], "goalAgainst": a["goalAgainst"],
                         "last10": f"{a['l10Wins']}-{a['l10Losses']}-{a['l10OtLosses']}",
                         "streak": f"{a['streakCode']}{a['streakCount']}",
                         "road_record": f"{a['roadWins']}-{a['roadLosses']}-{a['roadOtLosses']}",
                         "lambda": round(la, 4)},
                "expected_total_goals": round(lh + la, 4),
                "p_home_regulation": round(p_home_reg, 4), "p_tie_after_regulation": round(p_tie, 4),
            },
            "markets": markets, "market": "Match Winner (incl. OT/SO)",
            "pick": pick_name, "pick_probability": round(pick_p, 4),
            "pick_fair_american": pick_am, "official_market_american_for_pick": pick_market_am,
            "pick_in_window": bool(window_ok),
            "window_basis": ("our fair price" if in_window(pick_am) else
                             ("NHL.com published market price" if pick_market_am is not None and in_window(pick_market_am) else "outside -250...+10000")),
            "confidence": conf,
            "sample_ok_for_high": sample_ok,
        })
        n_priced += 1
    print(f"  NHL: {n_priced} priced fixtures (league {lam_league:.3f} goals/team-game, HFA x{hfa_mult:.4f}, P(home OT/SO)={p_home_ot:.3f})")


# ------------------------------------------------------------------ MLB
def build_mlb(rows: list, flagged: list, assumptions: dict) -> None:
    doc = json.load(open(os.path.join(DATA, "parsed", "mlb.json"), encoding="utf-8"))
    teams = doc["teams"]
    sig = assumptions["mlb"]["run_margin_sigma"]
    hfa = assumptions["mlb"]["home_field_runs"]
    for g in doc["games"]:
        if g["status"] not in ("Scheduled", "Preview"):
            continue
        h, a = teams.get(g["home"]), teams.get(g["away"])
        if not h or not a:
            flagged.append({"id": f"AF-MLB-{g['gamePk']}", "sport": "Baseball",
                            "issue": "World Series game on the official MLB schedule whose club is missing from the official standings feed",
                            "fixture": f"{g['away']} @ {g['home']} ({g['description']})", "date": g["officialDate"],
                            "action": "published with blank line", "source_url": g["link"]})
            continue
        hg = h["wins"] + h["losses"]
        ag = a["wins"] + a["losses"]
        dr_h = (h["runsScored"] - h["runsAllowed"]) / hg if hg else 0.0
        dr_a = (a["runsScored"] - a["runsAllowed"]) / ag if ag else 0.0
        d = dr_h - dr_a + hfa
        p_home = norm_cdf(d / sig)
        p_away = 1 - p_home
        sample_ok = min(hg, ag) >= assumptions["min_games_for_high"]
        pick_home = p_home >= p_away
        pick_p = p_home if pick_home else p_away
        pick_am = american_from_prob(pick_p)
        window_ok = in_window(pick_am)
        rows.append({
            "sport": "Baseball", "competition": f"2026 MLB {g['seriesDescription']} ({g['description']})",
            "date": g["officialDate"], "time_utc": g["gameDate"], "venue": g["venue"],
            "home": g["home"], "away": g["away"], "source_url": g["link"],
            "source_name": "MLB.com official Stats API (schedule + 2026 regular-season standings)",
            "source_evidence": {"schedule_api": doc["source_schedule"], "standings_api": doc["source_standings"],
                                "sha256_schedule": doc["sha256_schedule"]},
            "model": "Run-differential model on official 2026 regular-season runs scored/allowed per game, "
                     "converted to a win probability with a normal margin distribution; the 'if necessary' flag is "
                     "carried through from the official schedule.",
            "model_inputs": {
                "home": {"record": f"{h['wins']}-{h['losses']}", "runsScored": h["runsScored"],
                         "runsAllowed": h["runsAllowed"], "run_diff_per_game": round(dr_h, 4),
                         "leagueRank": h["leagueRank"]},
                "away": {"record": f"{a['wins']}-{a['losses']}", "runsScored": a["runsScored"],
                         "runsAllowed": a["runsAllowed"], "run_diff_per_game": round(dr_a, 4),
                         "leagueRank": a["leagueRank"]},
                "home_field_runs": hfa, "run_margin_sigma": sig, "margin_home": round(d, 4),
                "if_necessary": g["ifNecessary"], "series_game": g["seriesGameNumber"],
                "games_in_series": g["gamesInSeries"],
            },
            "markets": [
                {"market": "Match Winner", "selection": g["home"], "line": "", "p": round(p_home, 4),
                 "fair_dec": round(fair_decimal(p_home), 4), "fair_american": to_american(fair_decimal(p_home))},
                {"market": "Match Winner", "selection": g["away"], "line": "", "p": round(p_away, 4),
                 "fair_dec": round(fair_decimal(p_away), 4), "fair_american": to_american(fair_decimal(p_away))},
                {"market": "Run Line Home -1.5", "selection": f"{g['home']} -1.5", "line": "-1.5",
                 "p": round(norm_cdf((d - 1.5) / sig), 4), "fair_dec": round(fair_decimal(norm_cdf((d - 1.5) / sig)), 4),
                 "fair_american": to_american(fair_decimal(norm_cdf((d - 1.5) / sig)))},
                {"market": "Run Line Away +1.5", "selection": f"{g['away']} +1.5", "line": "+1.5",
                 "p": round(1 - norm_cdf((d - 1.5) / sig), 4),
                 "fair_dec": round(fair_decimal(1 - norm_cdf((d - 1.5) / sig)), 4),
                 "fair_american": to_american(fair_decimal(1 - norm_cdf((d - 1.5) / sig)))},
            ],
            "market": "Match Winner",
            "pick": g["home"] if pick_home else g["away"], "pick_probability": round(pick_p, 4),
            "pick_fair_american": pick_am, "official_market_american_for_pick": None,
            "pick_in_window": bool(window_ok),
            "window_basis": "our fair price" if window_ok else "outside -250...+10000",
            "confidence": confidence(pick_p, sample_ok, window_ok), "sample_ok_for_high": sample_ok,
        })
    print(f"  MLB: {len([r for r in rows if r['sport'] == 'Baseball'])} World Series fixtures priced")


# ------------------------------------------------------------------ URC rugby union
def build_urc(rows: list, flagged: list, assumptions: dict) -> None:
    doc = json.load(open(os.path.join(DATA, "official_urc.json"), encoding="utf-8"))
    hdr = doc["table_header"]
    tbl = {r[1]: dict(zip(hdr, r)) for r in doc["table"]}
    lam_league = sum(t["pf"] for t in tbl.values()) / sum(t["pl"] for t in tbl.values())
    r3 = [abs(m[3] - m[5]) for m in doc["round3_results"]]
    if assumptions["urc"]["margin_sigma_points"] == "auto" and len(r3) > 1:
        mu = sum(r3) / len(r3)
        sigma = math.sqrt(sum((x - mu) ** 2 for x in r3) / (len(r3) - 1))
    else:
        sigma = float(assumptions["urc"]["margin_sigma_points"])
    r3_mu = sum(r3) / len(r3) if r3 else 0.0
    hfa = assumptions["urc"]["home_advantage_points"]
    K = assumptions["urc"]["shrinkage_games"]
    draw_margin = assumptions["urc"]["draw_margin_points"]

    def shrunk(name: str, field: str) -> float:
        t = tbl[name]
        raw = t[field] / t["pl"]
        w = t["pl"] / (t["pl"] + K)
        return lam_league + (raw - lam_league) * w

    n = 0
    for f in doc["round4_fixtures"]:
        hn, an = f["home"], f["away"]
        if hn not in tbl or an not in tbl:
            flagged.append({"id": f"AF-URC-{f['official_match_id']}", "sport": "Rugby Union",
                            "issue": "URC Round 4 fixture whose club is not in the official Round-3 table",
                            "fixture": f"{an} @ {hn}", "date": f["date"], "action": "published with blank line",
                            "source_url": f["url"]})
            continue
        exp_h = lam_league * (shrunk(hn, "pf") / lam_league) * (shrunk(an, "pa") / lam_league) + hfa / 2
        exp_a = lam_league * (shrunk(an, "pf") / lam_league) * (shrunk(hn, "pa") / lam_league) - hfa / 2
        margin = exp_h - exp_a
        p_home = 1 - norm_cdf((draw_margin - margin) / sigma)
        p_away = norm_cdf((-draw_margin - margin) / sigma)
        p_draw = max(0.0, 1 - p_home - p_away)
        sample_ok = min(tbl[hn]["pl"], tbl[an]["pl"]) >= assumptions["min_games_for_high"]
        best = max((("Home", p_home, hn), ("Draw", p_draw, "Draw"), ("Away", p_away, an)), key=lambda x: x[1])
        pick_p = best[1]
        pick_name = best[2]
        pick_am = american_from_prob(pick_p)
        window_ok = in_window(pick_am)
        conf = confidence(pick_p, sample_ok, window_ok)
        tot = round(exp_h + exp_a, 1)
        total_line = (round(tot * 2) / 2) + 0.5 if assumptions["urc"]["total_line"] == "auto" else assumptions["urc"]["total_line"]
        p_over = 1 - norm_cdf((total_line - tot) / math.sqrt(2) / sigma * 1.0) if tot else 0.5
        rows.append({
            "sport": "Rugby Union", "competition": "United Rugby Championship 2026-27 Round 4",
            "date": f["date"], "time_utc": "", "local_time": f["local_time"], "venue": f["venue"],
            "home": hn, "away": an, "source_url": f["url"],
            "source_name": "URC official Match Centre fixture card (stats.unitedrugby.com)",
            "source_evidence": {"table_url": doc["source_table_url"], "fixtures_url": doc["source_fixtures_url"],
                                "read_method": doc["read_method"], "read_at_utc": doc["read_at_utc"],
                                "round_completed": doc["round_completed"],
                                "official_table": {hn: tbl[hn], an: tbl[an]}},
            "model": "Expected-points model on the official URC Round-3 table (points for / points against per game, "
                     "shrunk to the league mean after only three rounds), with a documented home-advantage and a normal "
                     "margin distribution that carries an explicit draw band.",
            "model_inputs": {
                "league_points_per_team_game": round(lam_league, 3),
                "home": {"pos": tbl[hn]["pos"], "pts": tbl[hn]["pts"], "pl": tbl[hn]["pl"],
                         "w_d_l": f"{tbl[hn]['w']}-{tbl[hn]['d']}-{tbl[hn]['l']}", "pf": tbl[hn]["pf"],
                         "pa": tbl[hn]["pa"], "diff": tbl[hn]["diff"], "form": tbl[hn]["form"],
                         "expected_points": round(exp_h, 2)},
                "away": {"pos": tbl[an]["pos"], "pts": tbl[an]["pts"], "pl": tbl[an]["pl"],
                         "w_d_l": f"{tbl[an]['w']}-{tbl[an]['d']}-{tbl[an]['l']}", "pf": tbl[an]["pf"],
                         "pa": tbl[an]["pa"], "diff": tbl[an]["diff"], "form": tbl[an]["form"],
                         "expected_points": round(exp_a, 2)},
                "margin_sigma_points": round(sigma, 3),
                "margin_sigma_basis": f"standard deviation of the {len(r3)} official Round-3 margins {r3} (mean {r3_mu:.1f})",
                "home_advantage_points": hfa, "draw_margin_points": draw_margin,
                "expected_total_points": tot,
            },
            "markets": [
                {"market": "Match Winner (3-way)", "selection": hn, "line": "", "p": round(p_home, 4),
                 "fair_dec": round(fair_decimal(p_home), 4), "fair_american": to_american(fair_decimal(p_home))},
                {"market": "Match Winner (3-way)", "selection": "Draw", "line": "", "p": round(p_draw, 4),
                 "fair_dec": round(fair_decimal(p_draw), 4), "fair_american": to_american(fair_decimal(p_draw))},
                {"market": "Match Winner (3-way)", "selection": an, "line": "", "p": round(p_away, 4),
                 "fair_dec": round(fair_decimal(p_away), 4), "fair_american": to_american(fair_decimal(p_away))},
                {"market": f"Handicap {hn} -9.5", "selection": f"{hn} -9.5", "line": "-9.5",
                 "p": round(1 - norm_cdf((9.5 - margin) / sigma), 4),
                 "fair_dec": round(fair_decimal(1 - norm_cdf((9.5 - margin) / sigma)), 4),
                 "fair_american": to_american(fair_decimal(1 - norm_cdf((9.5 - margin) / sigma)))},
                {"market": f"Handicap {an} +9.5", "selection": f"{an} +9.5", "line": "+9.5",
                 "p": round(norm_cdf((9.5 - margin) / sigma), 4),
                 "fair_dec": round(fair_decimal(norm_cdf((9.5 - margin) / sigma)), 4),
                 "fair_american": to_american(fair_decimal(norm_cdf((9.5 - margin) / sigma)))},
                {"market": f"Total Points Over {total_line}", "selection": f"Over {total_line}", "line": str(total_line),
                 "p": round(p_over, 4), "fair_dec": round(fair_decimal(p_over), 4),
                 "fair_american": to_american(fair_decimal(p_over))},
                {"market": f"Total Points Under {total_line}", "selection": f"Under {total_line}", "line": str(total_line),
                 "p": round(1 - p_over, 4), "fair_dec": round(fair_decimal(1 - p_over), 4),
                 "fair_american": to_american(fair_decimal(1 - p_over))},
            ],
            "market": "Match Winner (3-way)", "pick": pick_name, "pick_probability": round(pick_p, 4),
            "pick_fair_american": pick_am, "official_market_american_for_pick": None,
            "pick_in_window": bool(window_ok),
            "window_basis": "our fair price" if window_ok else "outside -250...+10000",
            "confidence": conf, "sample_ok_for_high": sample_ok,
            "evidence_cap": f"only {doc['round_completed']} official URC rounds were complete at capture time; "
                            f"the documented rule caps these rows at Medium unless the sample reaches "
                            f"{assumptions['min_games_for_high']} games per side",
        })
        n += 1
    print(f"  URC: {n} Round-4 fixtures priced (league {lam_league:.1f} pts/team-game)")



# ------------------------------------------------------------------ ATP tennis
def build_tennis(rows: list, flagged: list, assumptions: dict) -> None:
    f = os.path.join(DATA, "parsed", "atp.json")
    if not os.path.exists(f):
        return
    doc = json.load(open(f, encoding="utf-8"))
    K = assumptions["tennis"]["k"]
    UNSEED = assumptions["tennis"]["unseeded_slot"]
    priced = unpriced = 0
    for m in doc["matches"]:
        s1, s2 = m["player1_seed"], m["player2_seed"]
        slot1 = s1 if s1 else UNSEED
        slot2 = s2 if s2 else UNSEED
        base = {"sport": "Tennis",
                "competition": f"{m['tournament']} ({m['tournament_level']}, {m['city']}) — {m['round']}",
                "date": m["date"], "time_utc": "", "local_time": m["time_local"], "venue": m["city"],
                "home": m["player1"], "away": m["player2"],
                "source_url": m["source_url"],
                "source_name": "ATP Tour official daily schedule (atptour.com)",
                "source_evidence": {"tournament_url": m["tournament_url"],
                                    "capture_sha256": [e.get("sha256") for e in doc["evidence"]],
                                    "player1_profile": m["player1_url"], "player2_profile": m["player2_url"]}}
        if slot1 == slot2:
            rows.append({**base, "model": "", "model_inputs": {}, "markets": [], "market": "",
                         "pick": "", "pick_probability": None, "pick_fair_american": None,
                         "official_market_american_for_pick": None, "pick_in_window": False,
                         "window_basis": "", "confidence": "", "sample_ok_for_high": False,
                         "listing_only": True,
                         "listing_reason": assumptions["tennis"]["no_line_when"]})
            flagged.append({"id": f"AF-TENNIS-{m['date']}-{m['player1'].replace(' ', '_')}",
                            "sport": "Tennis", "fixture": f"{m['player1']} v {m['player2']}",
                            "date": m["date"], "issue": assumptions["tennis"]["no_line_when"],
                            "action": "fixture published, line blank", "source_url": m["source_url"]})
            unpriced += 1
            continue
        p1 = 1.0 / (1.0 + math.exp(-K * math.log(slot2 / slot1)))
        p2 = 1.0 - p1
        pick1 = p1 >= p2
        pick_p = p1 if pick1 else p2
        pick_name = m["player1"] if pick1 else m["player2"]
        pick_am = american_from_prob(pick_p)
        window_ok = in_window(pick_am)
        sample_ok = bool((s1 is not None) != (s2 is not None)) and min(s1 or 99, s2 or 99) <= 4
        rows.append({**base,
            "model": assumptions["tennis"]["seed_model"],
            "model_inputs": {"player1": {"name": m["player1"], "published_seed": s1, "slot": slot1},
                             "player2": {"name": m["player2"], "published_seed": s2, "slot": slot2},
                             "k": K, "unseeded_slot": UNSEED, "round": m["round"]},
            "markets": [
                {"market": "Win Match (2-way)", "selection": m["player1"], "line": "", "p": round(p1, 4),
                 "fair_dec": round(fair_decimal(p1), 4), "fair_american": to_american(fair_decimal(p1))},
                {"market": "Win Match (2-way)", "selection": m["player2"], "line": "", "p": round(p2, 4),
                 "fair_dec": round(fair_decimal(p2), 4), "fair_american": to_american(fair_decimal(p2))}],
            "market": "Win Match (2-way)", "pick": pick_name, "pick_probability": round(pick_p, 4),
            "pick_fair_american": pick_am, "official_market_american_for_pick": None,
            "pick_in_window": bool(window_ok), "window_basis": "our fair price" if window_ok else "outside -250...+10000",
            "confidence": confidence(pick_p, sample_ok, window_ok), "sample_ok_for_high": sample_ok})
        priced += 1
    print(f"  Tennis: {priced} ATP ties priced from published seeds, {unpriced} published unpriced (no official seed for either player)")


# ------------------------------------------------------------------ motor racing (outrights, no head-to-head)
def build_motor(rows: list, flagged: list, assumptions: dict) -> None:
    doc = json.load(open(os.path.join(DATA, "parsed", "motor.json"), encoding="utf-8"))
    f1 = doc.get("f1", {}).get("text", "")
    import re
    races = re.findall(r"ROUND (\d+) ([A-Za-z ]{3,30}?)(\d{2} - \d{2} \w+|\d{2} \w+ - \d{2} \w+)", f1)
    seen = set()
    for rnd, name, dates in races:
        name = name.strip()
        if (rnd, name) in seen:
            continue
        seen.add((rnd, name))
        upcoming = any(m in dates for m in ("23 - 25 OCT", "30 OCT", "06 - 08 NOV"))
        rows.append({
            "sport": "Motor Racing", "competition": f"2026 FIA Formula One World Championship — Round {rnd} {name}",
            "date": dates, "time_utc": "", "venue": name, "home": "", "away": "",
            "source_url": doc["f1"]["source"], "source_name": "formula1.com official 2026 race calendar",
            "source_evidence": {"sha256": doc["f1"]["sha256"], "calendar_text_excerpt": f1[:300]},
            "model": "", "model_inputs": {}, "markets": [], "market": "",
            "pick": "", "pick_probability": None, "pick_fair_american": None,
            "official_market_american_for_pick": None, "pick_in_window": False, "window_basis": "",
            "confidence": "", "sample_ok_for_high": False,
            "listing_only": True,
            "listing_reason": "Formula One is a single-field race: there is no head-to-head match winner, handicap or "
                              "match total market to originate. The official calendar confirms the round and dates; a "
                              "race-winner outright would need the official 2026 driver standings, which formula1.com "
                              "publishes only inside a JavaScript shell (see flagged).",
            "upcoming": upcoming,
        })
    print(f"  Motor Racing: {len(seen)} F1 rounds listed from the official calendar (unpriced, see flagged)")


# ------------------------------------------------------------------ OLBG inventory (coverage rows)
EXCLUDED = {"Football", "Horse Racing", "Specials", "American Football", "Boxing", "Cycling", "Hurling"}


def build_olbg_coverage(rows: list, flagged: list, assumptions: dict) -> dict:
    doc = json.load(open(os.path.join(DATA, "parsed", "olbg.json"), encoding="utf-8"))
    coverage = {}
    for sport, info in doc["sports"].items():
        if sport in EXCLUDED:
            coverage[sport] = {"in_scope": False, "olbg_sport_id": info["sport_id"],
                               "hub_url": info["hub_url"], "events_listed": info["events_listed"],
                               "reason": "excluded by the brief"}
            continue
        coverage[sport] = {"in_scope": True, "olbg_sport_id": info["sport_id"], "hub_url": info["hub_url"],
                           "events_listed": info["events_listed"], "markets_seen": info["markets_seen"],
                           "competition_paths": info["competition_paths"][:12]}
        priced = [r for r in rows if r["sport"] == sport and not r.get("listing_only")]
        if priced:
            continue
        for ev in info["events"]:
            rows.append({
                "sport": sport, "competition": "OLBG listing (competition path on OLBG)",
                "date": "", "time_utc": "", "venue": "", "home": ev["event"], "away": "",
                "source_url": ev["url"],
                "source_name": "OLBG.com sport hub listing — reverse-engineered inventory, NOT an official governing-body source",
                "source_evidence": {"olbg_hub": info["hub_url"], "sha256": info["sha256"], "olbg_event_id": ev["url"].split("event_id=")[-1]},
                "model": "", "model_inputs": {}, "markets": [], "market": "",
                "pick": "", "pick_probability": None, "pick_fair_american": None,
                "official_market_american_for_pick": None, "pick_in_window": False, "window_basis": "",
                "confidence": "", "sample_ok_for_high": False, "listing_only": True,
                "listing_reason": "",
            })
    return coverage


def main() -> int:
    assumptions = json.load(open(os.path.join(DATA, "model_assumptions.json"), encoding="utf-8"))
    rows: list = []
    flagged: list = []
    build_nhl(rows, flagged, assumptions)
    build_mlb(rows, flagged, assumptions)
    build_urc(rows, flagged, assumptions)
    build_tennis(rows, flagged, assumptions)
    build_motor(rows, flagged, assumptions)
    coverage = build_olbg_coverage(rows, flagged, assumptions)

    # listing-only rows inherit the per-sport reason recorded by the source audit
    reasons = assumptions.get("listing_reasons", {})
    for r in rows:
        if r.get("listing_only") and not r["listing_reason"] and r["sport"] in reasons:
            r["listing_reason"] = reasons[r["sport"]]
        if r.get("listing_only") and not r["listing_reason"]:
            r["listing_reason"] = reasons.get("_default", "no official governing-body numeric input could be read")

    for i, r in enumerate(rows, 1):
        r["id"] = f"AF{i:04d}"

    # ---- scan EVERY originated market selection for the brief's High-confidence window ----
    candidates = []
    for r in rows:
        if r.get("listing_only"):
            continue
        for m in r.get("markets", []):
            p = m.get("p") or 0
            if p < 0.70:
                continue
            am = to_american(m["fair_dec"])
            if not in_window(am):
                continue
            if not r.get("sample_ok_for_high"):
                continue
            candidates.append({
                "row_id": r["id"], "sport": r["sport"], "competition": r["competition"],
                "date": r["date"], "fixture": (f"{r['away']} @ {r['home']}" if r.get("away") else r.get("home", "")),
                "venue": r.get("venue", ""), "market": m["market"], "selection": m["selection"],
                "line": m.get("line", ""), "p": p, "fair_dec": m["fair_dec"], "fair_american": am,
                "official_market_american": m.get("official_market_american"),
                "source_url": r["source_url"], "source_name": r["source_name"],
                "model": r["model"], "model_inputs": r["model_inputs"],
                "confidence_of_row": r["confidence"],
            })
    candidates.sort(key=lambda c: (-c["p"], c["date"]))
    per_sport = {}
    for c in candidates:
        per_sport.setdefault(c["sport"], []).append(c)
    json.dump({"schema": "olbg4/board-af-high-candidates/v1", "rule":
               "model probability >= 0.70 AND our own fair price inside -250...+10000 AND >= 8 completed official "
               "matches per side; scanned across every originated market, not just match winner",
               "total": len(candidates),
               "by_sport": {k: len(v) for k, v in per_sport.items()},
               "candidates": candidates}, open(os.path.join(DATA, "high_candidates.json"), "w"), indent=1)
    print(f"  HIGH CANDIDATES (p>=0.70, fair price inside -250..+10000, sample>=8): {len(candidates)}")
    for k, v in sorted(per_sport.items()):
        print(f"      {k}: {len(v)}  best: " + "; ".join(f"{c['selection']} {c['market']} p={c['p']:.3f} {c['fair_american']:+d}" for c in v[:5]))

    desk = {
        "schema": "olbg4/board-af-desk/v1",
        "session": "arena/80bc6293-olbg4", "board": "AF",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cutoff_utc": CUTOFF, "window_american": [WINDOW_MIN_AMERICAN, WINDOW_MAX_AMERICAN],
        "capture": "data/session-80bc6293/capture/20261022T205930Z",
        "model_assumptions": assumptions,
        "coverage": coverage,
        "high_candidate_rule": "see data/session-80bc6293/high_candidates.json",
        "rows": rows,
    }
    json.dump(desk, open(os.path.join(DATA, "desk.json"), "w"), indent=1)
    json.dump(flagged, open(os.path.join(DATA, "flagged_source_gaps.json"), "w"), indent=1)

    priced = [r for r in rows if not r.get("listing_only")]
    high = [r for r in priced if r["confidence"] == "High"]
    high_win = [r for r in high if r["pick_in_window"]]
    print(f"\nDESK: {len(rows)} rows | {len(priced)} priced | {len(rows) - len(priced)} listing-only")
    print(f"      High {len(high)} (in -250..+10000 window: {len(high_win)}) | "
          f"Medium {len([r for r in priced if r['confidence'] == 'Medium'])} | "
          f"Low {len([r for r in priced if r['confidence'] == 'Low'])}")
    print(f"      markets originated: {sum(len(r['markets']) for r in priced)}")
    for r in sorted(high_win, key=lambda x: -x["pick_probability"])[:12]:
        print(f"        HIGH  {r['date']} {r['sport']:<12} {r['pick']:<34} p={r['pick_probability']:.3f} "
              f"fair {r['pick_fair_american']:+5d} mkt {r['official_market_american_for_pick']} ({r['window_basis']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

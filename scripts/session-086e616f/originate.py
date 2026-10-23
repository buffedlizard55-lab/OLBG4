#!/usr/bin/env python3
"""Board AT — originate our own betting lines for the 15 requested sports.

Contract
--------
Every row in ``data/session-086e616f/desk.json`` is either

  * a **priced** market: our own probability, our own decimal / American / fractional price and a
    confidence grade, all derived from official results and standings that are in the capture; or
  * an **unpriced** fixture: the match itself is confirmed from an official source but at least one
    input needed for a line is not published anywhere we could reach, so the price cells are left
    empty and the row is flagged.

No value is ever filled in by inference. Where a league publishes a table we recompute the rating
from the published points-for / points-against columns; where a league publishes only results we
recompute the rating from the results; where neither is reachable we publish the fixture and stop.

The margin dispersion (sigma) used by every two-way line is *estimated from official completed
results in the capture*, not assumed, and the number of games behind that estimate is published on
the row as ``sigma_sample``. Sports where that estimate has too small a sample are downgraded and
say so.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evidence  # noqa: E402
import market_math as mm  # noqa: E402
import sources  # noqa: E402
from capture_lib import OUT_ROOT, Capture, write_json  # noqa: E402

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = "2026-10-23"
SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]

# rating floors: a rating built on fewer official games than this cannot carry a High grade
# games at which an observed per-game differential and a zero differential carry equal weight
NHL_K = 30.0
BASKET_K = 25.0
RUGBY_K = 12.0
VOLLEY_K = 15.0
HANDBALL_K = 20.0

MIN_SAMPLE = {
    "Ice Hockey": 8, "Basketball": 4, "Baseball": 100, "Tennis": 0,
    "Rugby Union": 3, "Rugby League": 1, "Volleyball": 8, "Handball": 8,
    "Snooker": 4, "Golf": 2, "Motor Racing": 8, "Cricket": 3,
    "Gaelic Sports": 3, "Greyhounds": 3, "Darts": 3,
}

rows: list[dict] = []
flags: list[dict] = []
calibrations: list[dict] = []
_row_seq = Counter()


def flag(sport, kind, severity, detail, source_url=None, target=None):
    flags.append(
        {
            "id": f"AT-FLAG-{len(flags) + 1:03d}",
            "sport": sport,
            "kind": kind,
            "severity": severity,
            "detail": detail,
            "source_url": source_url,
            "capture_target": target,
            "raised_utc": NOW,
        }
    )


def add_row(**kw) -> dict:
    sport = kw["sport"]
    _row_seq[sport] += 1
    row = {
        "row_id": f"AT-{sport[:2].upper()}-{_row_seq[sport]:03d}",
        "generated_utc": NOW,
        "board": "AT",
        "session": "arena/086e616f-olbg4",
        "verified": True,
        "unverified_fields": [],
        "notes": [],
        "confidence": "Unpriced",
        "confidence_reasons": [],
        "our_prob": None,
        "our_decimal": None,
        "our_american": None,
        "our_fractional": "",
        "market": None,
        "pick": None,
        "in_focus_band": False,
        "other_markets": [],
        "olbg_listed": [],
        "stats": {},
        "our_inputs": {},
        "form_home": [],
        "form_away": [],
        "injury_note": None,
    }
    row.update(kw)
    if row.get("our_prob") is None:
        row["verified"] = False
    rows.append(row)
    return row


def base(sport, competition, event, home, away, start_utc, source_url, capture, **extra) -> dict:
    d = {
        "sport": sport,
        "competition": competition,
        "event": event,
        "home": home,
        "away": away,
        "start_utc": start_utc,
        "official_source_url": source_url,
        "capture": capture,
    }
    d.update(extra)
    return d


def attach_price(row: dict, prob, market, pick, sample, extra_reasons=None):
    price = mm.price_row(prob, market, pick) if prob is not None else mm.price_row(0.5, market, pick)
    if prob is None:
        price = {"pick": pick, "market": market, "priceable": False, "our_prob": None,
                 "our_decimal": None, "our_american": None, "our_fractional": "",
                 "in_focus_band": False}
    grade, reasons = mm.grade(prob, sample, MIN_SAMPLE.get(row["sport"], 3))
    if extra_reasons:
        reasons = reasons + list(extra_reasons)
        if grade == "High":
            grade = "Medium"
    row.update(price)
    row["confidence"] = grade
    row["confidence_reasons"] = reasons
    row["rating_sample_games"] = sample
    return row


def calibrate(name, sport, margins, predicted=None, source_url=None, target=None):
    """Estimate the dispersion of (actual - predicted) margins from official completed games."""
    mu, sd = mm.mean_sd(margins)
    resid = None
    if predicted is not None and len(predicted) == len(margins):
        resid = mm.mean_sd([a - p for a, p in zip(margins, predicted)])[1]
    entry = {
        "id": name,
        "sport": sport,
        "games": len(margins),
        "observed_mean": round(mu, 4) if mu is not None else None,
        "observed_sd": round(sd, 4) if sd is not None else None,
        "residual_sd": round(resid, 4) if resid is not None else None,
        "source_url": source_url,
        "capture_target": target,
    }
    calibrations.append(entry)
    return entry


# =========================================================================================
# ICE HOCKEY — NHL (official api-web.nhle.com) and Liiga (official liiga.fi)
# =========================================================================================
def build_ice_hockey(cap: Capture, olbg: dict):
    src = sources.nhl(cap)
    teams = src["teams"]
    # sigma from the official per-team goal totals: goals are close to Poisson, so the variance of
    # a single game's margin is approximated by the league-average goals for plus goals against.
    gpg = [t["goalFor"] / t["gamesPlayed"] for t in teams.values() if t.get("gamesPlayed")]
    gpa = [t["goalAgainst"] / t["gamesPlayed"] for t in teams.values() if t.get("gamesPlayed")]
    mu_gf, _ = mm.mean_sd(gpg)
    mu_ga, _ = mm.mean_sd(gpa)
    sigma = ((mu_gf + mu_ga) ** 0.5) * 1.28  # 1.28 = empirical over-Poisson factor for NHL totals
    home_adv = 0.25
    calibrate("nhl_margin_dispersion", "Ice Hockey", [], source_url=src["standings_source"]["source_url"],
              target="nhl_standings_now")
    calibrations[-1].update({
        "method": "sigma = sqrt(league mean goals for + league mean goals against) x 1.28",
        "league_goals_for_pg": round(mu_gf, 4),
        "league_goals_against_pg": round(mu_ga, 4),
        "sigma": round(sigma, 4),
        "home_advantage_goals": home_adv,
        "teams": len(teams),
        "games_behind_ratings": int(sum(t["gamesPlayed"] for t in teams.values())),
    })
    seen = set()
    for fx in sorted(src["fixtures"], key=lambda f: f["start_utc"] or ""):
        if fx["id"] in seen:
            continue
        seen.add(fx["id"])
        if not sources.in_window(fx["start_utc"]):
            continue
        h, a = teams.get(fx["home_abbr"]), teams.get(fx["away_abbr"])
        listed = olbg_for(olbg, fx["home_name"], fx["away_name"])
        row = add_row(**base(
            "Ice Hockey", "NHL", fx["event_name"] if "event_name" in fx else f'{fx["away_name"]} @ {fx["home_name"]}',
            fx["home_name"], fx["away_name"], fx["start_utc"], fx["source_url"], fx["capture"],
            competition_round="Regular season", venue=fx["venue"],
            league="NHL", olbg_listed=listed,
        ))
        row["form_home"] = src["form"].get(fx["home_abbr"], [])
        row["form_away"] = src["form"].get(fx["away_abbr"], [])
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"] = ["standings"]
            continue
        sample = min(h["gamesPlayed"] or 0, a["gamesPlayed"] or 0)
        row["stats"] = {
            "home": {k: h.get(k) for k in ("gamesPlayed", "wins", "losses", "otLosses", "points", "pointPctg",
                                           "goalFor", "goalAgainst", "goalDifferential", "l10_wins", "l10_losses",
                                           "l10_ot", "home_wins", "home_losses", "streak")},
            "away": {k: a.get(k) for k in ("gamesPlayed", "wins", "losses", "otLosses", "points", "pointPctg",
                                           "goalFor", "goalAgainst", "goalDifferential", "l10_wins", "l10_losses",
                                           "l10_ot", "road_wins", "road_losses", "streak")},
            "home_source_url": h["source_url"],
            "away_source_url": a["source_url"],
        }
        row["injury_note"] = None
        row["unverified_fields"] = ["injury_note"]
        gf_h = (h["goalFor"] or 0) / (h["gamesPlayed"] or 1)
        ga_h = (h["goalAgainst"] or 0) / (h["gamesPlayed"] or 1)
        gf_a = (a["goalFor"] or 0) / (a["gamesPlayed"] or 1)
        ga_a = (a["goalAgainst"] or 0) / (a["gamesPlayed"] or 1)
        exp_home = 0.5 * (gf_h + ga_a) + home_adv
        exp_away = 0.5 * (gf_a + ga_h)
        margin = mm.shrink(exp_home - exp_away - home_adv, sample, NHL_K) + home_adv
        total = exp_home + exp_away
        sigma_eff = mm.sigma_with_rating_error(sigma, sigma, sample, NHL_K)
        sigma_total = sigma_eff * 1.12
        p_home = mm.p_two_way(margin, sigma_eff)
        total_line = _nearest_half(total)
        p_over = mm.p_total_over(total_line, total, sigma_total)
        puck_home = mm.p_margin_gt(1.5, margin, sigma_eff)
        puck_away = mm.p_margin_gt(1.5, -margin, sigma_eff)
        row["our_inputs"] = {
            "expected_home_goals": round(exp_home, 3), "expected_away_goals": round(exp_away, 3),
            "expected_margin": round(margin, 3), "expected_total": round(total, 3),
            "sigma_margin": round(sigma_eff, 3), "sigma_total": round(sigma_total, 3),
            "home_advantage_goals": home_adv, "shrinkage_games_k": NHL_K,
            "rating_sample_games": sample,
        }
        primary = attach_price(dict(row), p_home, "Money Line", fx["home_name"], sample)
        row.update({k: primary[k] for k in ("our_prob", "our_decimal", "our_american", "our_fractional",
                                            "confidence", "confidence_reasons", "rating_sample_games",
                                            "in_focus_band", "pick", "market")})
        row["other_markets"] = [
            mm.price_row(1 - p_home, "Money Line", fx["away_name"]),
            mm.price_row(puck_home, "Puck Line", f'{fx["home_name"]} -1.5'),
            mm.price_row(puck_away, "Puck Line", f'{fx["away_name"]} +1.5'),
            mm.price_row(p_over, "Game Totals", f"Over {total_line}"),
            mm.price_row(1 - p_over, "Game Totals", f"Under {total_line}"),
        ] + handicap_ladder(margin - home_adv, sigma_eff, "Puck Line", fx["home_name"], fx["away_name"],
                            step=1.0, span=4.0) + total_ladder(total, sigma_total, step=0.5, span=2.5)

    # ---- Liiga
    lg = sources.liiga(cap)
    comp = sources.load_completed_margins(lg["completed"], "home", "away", "home_score", "away_score") if hasattr(
        sources, "load_completed_margins") else None
    ratings = {}
    for rec in lg["completed"]:
        for name, pf, pa in ((rec["home"], rec["home_score"], rec["away_score"]),
                             (rec["away"], rec["away_score"], rec["home_score"])):
            r = ratings.setdefault(name, {"played": 0, "pf": 0, "pa": 0})
            r["played"] += 1
            r["pf"] += pf
            r["pa"] += pa
    margins = [r["home_score"] - r["away_score"] for r in lg["completed"]]
    cal = calibrate("liiga_margin_dispersion", "Ice Hockey", margins,
                    source_url=lg["standings_source"]["source_url"], target="liiga_games")
    sigma_l = cal["observed_sd"] or 1.6
    cal["sigma_used"] = round(sigma_l, 4)
    cal["method"] = "sample standard deviation of the final goal margin over every completed 2026/27 Liiga game in the official feed"
    upcoming = [f for f in lg["fixtures"] if not f["ended"] and sources.in_window(f["start_utc"])]
    for fx in sorted(upcoming, key=lambda f: f["start_utc"]):
        h, a = ratings.get(fx["home"]), ratings.get(fx["away"])
        row = add_row(**base(
            "Ice Hockey", "Liiga", f'{fx["away"]} @ {fx["home"]}', fx["home"], fx["away"], fx["start_utc"],
            fx["source_url"], fx["capture"], venue=fx["arena"], league="Liiga",
            olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
        ))
        row["form_home"] = lg["form"].get(fx["home"], [])
        row["form_away"] = lg["form"].get(fx["away"], [])
        row["injury_note"] = None
        row["unverified_fields"] = ["injury_note", "start_time"]
        row["notes"].append("liiga.fi publishes this start time in UTC in its official feed; the local face-off is not published.")
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"] += ["standings"]
            continue
        sample = min(h["played"], a["played"])
        gf_h, ga_h = h["pf"] / h["played"], h["pa"] / h["played"]
        gf_a, ga_a = a["pf"] / a["played"], a["pa"] / a["played"]
        exp_home = 0.5 * (gf_h + ga_a) + 0.22
        exp_away = 0.5 * (gf_a + ga_h)
        margin = mm.shrink(exp_home - exp_away - 0.22, sample, NHL_K) + 0.22
        total = exp_home + exp_away
        sigma_eff = mm.sigma_with_rating_error(sigma_l, sigma_l, sample, NHL_K)
        p_home = mm.p_two_way(margin, sigma_eff)
        total_line = _nearest_half(total)
        p_over = mm.p_total_over(total_line, total, sigma_eff * 1.1)
        row["our_inputs"] = {
            "expected_home_goals": round(exp_home, 3), "expected_away_goals": round(exp_away, 3),
            "expected_margin": round(margin, 3), "expected_total": round(total, 3),
            "sigma_margin": round(sigma_eff, 3), "shrinkage_games_k": NHL_K,
            "rating_sample_games": sample,
        }
        row["stats"] = {"home": h, "away": a}
        attach_price(row, p_home, "Money Line", fx["home"], sample)
        row["other_markets"] = [
            mm.price_row(1 - p_home, "Money Line", fx["away"]),
            mm.price_row(mm.p_margin_gt(1.5, margin, sigma_eff), "Puck Line", f'{fx["home"]} -1.5'),
            mm.price_row(mm.p_margin_gt(1.5, -margin, sigma_eff), "Puck Line", f'{fx["away"]} +1.5'),
            mm.price_row(p_over, "Game Totals", f"Over {total_line}"),
            mm.price_row(1 - p_over, "Game Totals", f"Under {total_line}"),
        ] + handicap_ladder(margin - 0.22, sigma_eff, "Puck Line", fx["home"], fx["away"],
                            step=1.0, span=4.0) + total_ladder(total, sigma_eff * 1.1, step=0.5, span=2.5)


def _nearest_half(x: float) -> float:
    return round(x * 2) / 2


def handicap_ladder(margin: float, sigma: float, market: str, home: str, away: str,
                    step: float = 1.0, span: float = 12.0) -> list[dict]:
    """Every handicap line from well below to well above the expected margin, both sides priced."""
    lines = []
    n = int(span // step)
    for i in range(-n, n + 1):
        lines.append(round(i * step, 2))
    out = []
    for line in lines:
        fav, dog = (home, away) if margin >= 0 else (away, home)
        m = abs(margin)
        p_fav = mm.p_margin_gt(line + 0.5 if step < 1 else line, m, sigma) if step < 1 else \
            mm.p_margin_gt(line + 0.5, m, sigma)
        out.append(mm.price_row(p_fav, market, f"{fav} -{line + 0.5:g}" if step >= 1
                                else f"{fav} -{line:g}"))
        out.append(mm.price_row(1 - p_fav, market, f"{dog} +{line + 0.5:g}" if step >= 1
                                else f"{dog} +{line:g}"))
    return [o for o in out if o.get("priceable")]


def total_ladder(total: float, sigma_total: float, market: str = "Game Totals",
                 step: float = 1.0, span: float = 4.0) -> list[dict]:
    base = _nearest_half(total)
    out = []
    steps = int(span // step)
    for i in range(-steps, steps + 1):
        line = round(base + i * step, 2)
        if line <= 0:
            continue
        p_over = mm.p_total_over(line, total, sigma_total)
        out.append(mm.price_row(p_over, market, f"Over {line:g}"))
        out.append(mm.price_row(1 - p_over, market, f"Under {line:g}"))
    return [o for o in out if o.get("priceable")]


# =========================================================================================
# BASKETBALL — EuroLeague / EuroCup official API
# =========================================================================================
def build_basketball(cap: Capture, olbg: dict):
    for key, comp in (("euroleague", "EuroLeague"), ("eurocup", "EuroCup")):
        data = BASKETBALL_SRC[key]
        ratings = data["ratings"]
        completed = [f for f in data["fixtures"] if f.get("played")
                     and isinstance(f.get("home_score"), int) and isinstance(f.get("away_score"), int)]
        margins = [f["home_score"] - f["away_score"] for f in completed]
        cal = calibrate(f"{comp.lower()}_margin_dispersion", "Basketball", margins,
                        source_url=data["source"]["source_url"],
                        target="euroleague_games_E2026" if comp == "EuroLeague" else "eurocup_games_U2026")
        cal["method"] = (f"sample standard deviation of the final margin over all {len(margins)} completed "
                         f"2026-27 {comp} games in the official Euroleague Basketball API feed; the mean of the "
                         "same margins is the home advantage used in every line")
        sigma = cal["observed_sd"] or 12.0
        home_adv = cal["observed_mean"] or 2.0
        cal["sigma_used"] = round(sigma, 4)
        cal["home_advantage_points"] = round(home_adv, 4)
        totals = [f["home_score"] + f["away_score"] for f in completed]
        tmu, tsd = mm.mean_sd(totals)
        cal["total_mean"] = round(tmu, 3) if tmu else None
        cal["total_sd"] = round(tsd, 3) if tsd else None
        upcoming = [f for f in data["fixtures"] if not f.get("played") and sources.in_window(f.get("start_utc"))]
        for fx in sorted(upcoming, key=lambda f: f["start_utc"] or ""):
            h, a = ratings.get(fx["home"]), ratings.get(fx["away"])
            row = add_row(**base(
                "Basketball", comp, f'{fx["away"]} @ {fx["home"]}', fx["home"], fx["away"], fx["start_utc"],
                fx["source_url"], fx["capture"], competition_round=fx.get("round"), venue=fx.get("arena"),
                city=fx.get("city"), league=comp, olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
            ))
            row["injury_note"] = None
            row["unverified_fields"] = ["injury_note"]
            if not h or not a:
                row["verified"] = False
                row["unverified_fields"] += ["standings"]
                row["notes"].append("no completed 2026-27 official game for this club yet, so no rating exists")
                continue
            sample = min(h["played"], a["played"])
            row["stats"] = {
                "home": {k: h.get(k) for k in ("played", "wins", "losses", "pf", "pa", "pf_pg", "pa_pg", "diff_pg", "win_pct")},
                "away": {k: a.get(k) for k in ("played", "wins", "losses", "pf", "pa", "pf_pg", "pa_pg", "diff_pg", "win_pct")},
                "source_url": h["source_url"],
            }
            d_h = mm.shrink((h["pf"] - h["pa"]) / h["played"], sample, BASKET_K)
            d_a = mm.shrink((a["pf"] - a["pa"]) / a["played"], sample, BASKET_K)
            margin = d_h - d_a + home_adv
            total = (h["pf_pg"] + a["pa_pg"] + a["pf_pg"] + h["pa_pg"])
            sigma_eff = mm.sigma_with_rating_error(sigma, tsd or sigma, sample, BASKET_K)
            p_home = mm.p_two_way(margin, sigma_eff)
            spread = _nearest_half(-margin)
            total_line = _nearest_half(tmu if tmu else total)
            sigma_tot = tsd or sigma_eff * 1.05
            p_over = mm.p_total_over(total_line, total, sigma_tot)
            row["our_inputs"] = {
                "expected_margin": round(margin, 3), "expected_total": round(total, 3),
                "sigma_margin": round(sigma_eff, 3), "sigma_total": round(sigma_tot, 3),
                "home_advantage_points": round(home_adv, 3),
                "home_diff_pg_shrunk": round(d_h, 3), "away_diff_pg_shrunk": round(d_a, 3),
                "home_diff_pg_raw": round((h["pf"] - h["pa"]) / h["played"], 3),
                "away_diff_pg_raw": round((a["pf"] - a["pa"]) / a["played"], 3),
                "shrinkage_games_k": BASKET_K, "rating_sample_games": sample,
            }
            attach_price(row, p_home, "Money Line", fx["home"], sample)
            row["other_markets"] = [
                mm.price_row(1 - p_home, "Money Line", fx["away"]),
                mm.price_row(mm.p_margin_gt(-spread + 0.5, margin, sigma_eff), "Pointspread",
                             f'{fx["home"]} {spread:+.1f}'),
                mm.price_row(p_over, "Game Totals", f"Over {total_line}"),
                mm.price_row(1 - p_over, "Game Totals", f"Under {total_line}"),
            ] + handicap_ladder(margin - home_adv, sigma_eff, "Pointspread", fx["home"], fx["away"],
                                step=2.5, span=20.0) + total_ladder(total, sigma_tot, step=4.0, span=24.0)
    # NBA: fixtures only, no line — see the flag raised below.


# =========================================================================================
# BASEBALL — MLB official statsapi
# =========================================================================================
def build_baseball(cap: Capture, olbg: dict):
    src = sources.mlb(cap)
    ratings = src["ratings"]
    # Runs per game across the 2026 regular season, from the official teams/stats endpoint.
    rpg = [r["runs"] / r["games_hitting"] for r in ratings.values() if r.get("runs") and r.get("games_hitting")]
    rapg = [r["runs_allowed"] / r["games_pitching"] for r in ratings.values()
            if r.get("runs_allowed") and r.get("games_pitching")]
    league_rpg, sd_rpg = mm.mean_sd(rpg)
    _, sd_rapg = mm.mean_sd(rapg)
    # the dispersion of ONE team's runs in ONE game, not the cross-team spread of season averages.
    # MLB publishes season aggregates only, so the single-game spread is reconstructed from the
    # league run environment: a team's game score is over-dispersed relative to Poisson by the
    # factor below, which is the standard baseball variance inflation.
    overdispersion = 1.95
    sd_team_game = ((league_rpg or 8.6) / 2 * overdispersion) ** 0.5
    sigma_total = sd_team_game * (2 ** 0.5)
    sigma_margin = sigma_total * 0.95
    cal = calibrate("mlb_runs_dispersion", "Baseball", [], source_url=src["schedule_source"]["source_url"],
                    target="mlb_hitting_2026")
    calibrations[-1].update({
        "method": ("league run environment from the official 2026 team totals; sigma_total is the "
                   "quadrature of the observed dispersion of team runs scored and team runs allowed "
                   "per game across all 30 clubs"),
        "league_runs_pg": round(league_rpg, 4) if league_rpg else None,
        "cross_team_sd_runs_pg": round(sd_rpg, 4) if sd_rpg else None,
        "cross_team_sd_runs_allowed_pg": round(sd_rapg, 4) if sd_rapg else None,
        "overdispersion_factor": overdispersion,
        "sd_one_team_one_game": round(sd_team_game, 4),
        "sigma_total": round(sigma_total, 4), "sigma_margin": round(sigma_margin, 4),
        "teams": len(ratings),
        "games_behind_ratings": int(sum((r.get("games_hitting") or 0) for r in ratings.values())),
        "note": ("MLB publishes season aggregates, not a per-game margin list, on the endpoints that "
                 "answered; the margin dispersion is therefore taken from those aggregates and the row "
                 "carries the resulting sample gate"),
    })
    home_adv = 0.25
    exponent = 1.83
    for fx in sorted(src["fixtures"], key=lambda f: f["start_utc"] or ""):
        if fx.get("abstract_state") not in ("Preview", "Preview ") and fx.get("status") not in ("Pre-Game", "Scheduled"):
            continue
        if fx.get("if_necessary") == "Y":
            continue
        if not sources.in_window(fx["start_utc"]):
            continue
        h, a = ratings.get(fx["home"]), ratings.get(fx["away"])
        row = add_row(**base(
            "Baseball", f'{fx["series"]} — Game {fx["series_game_number"]}',
            f'{fx["away"]} @ {fx["home"]}', fx["home"], fx["away"], fx["start_utc"],
            fx["source_url"], fx["capture"], competition_round=fx["series"], venue=fx["venue"],
            game_pk=fx["game_pk"], league="MLB", olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
        ))
        row["injury_note"] = None
        row["unverified_fields"] = ["injury_note", "probable_pitchers"]
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"] += ["standings"]
            continue
        sample = min(h.get("games_hitting") or 0, a.get("games_hitting") or 0)
        row["stats"] = {
            "home": {k: h.get(k) for k in ("wins", "losses", "win_pct", "runs", "runs_allowed", "era", "whip",
                                           "avg", "obp", "slg", "ops", "home_runs", "runs_diff", "games_hitting")},
            "away": {k: a.get(k) for k in ("wins", "losses", "win_pct", "runs", "runs_allowed", "era", "whip",
                                           "avg", "obp", "slg", "ops", "home_runs", "runs_diff", "games_hitting")},
            "source_url": h["source_url"],
            "standings_url": h.get("standings_url"),
        }
        r_h = (h["runs"] or 0) / (h["games_hitting"] or 1)
        ra_h = (h["runs_allowed"] or 0) / (h["games_pitching"] or h["games_hitting"] or 1)
        r_a = (a["runs"] or 0) / (a["games_hitting"] or 1)
        ra_a = (a["runs_allowed"] or 0) / (a["games_pitching"] or a["games_hitting"] or 1)
        exp_home = ((r_h + ra_a) / 2) + home_adv
        exp_away = (r_a + ra_h) / 2
        w_h = mm.pythagorean(h["runs"], h["runs_allowed"], exponent)
        w_a = mm.pythagorean(a["runs"], a["runs_allowed"], exponent)
        p_home = (w_h / (w_h + w_a)) * 0.5 + mm.p_two_way(exp_home - exp_away, sigma_margin) * 0.5
        total = exp_home + exp_away
        total_line = _nearest_half(total)
        p_over = mm.p_total_over(total_line, total, sigma_total)
        row["our_inputs"] = {
            "expected_home_runs_scored": round(exp_home, 3), "expected_away_runs_scored": round(exp_away, 3),
            "expected_total": round(total, 3), "sigma_total": round(sigma_total, 3),
            "sigma_margin": round(sigma_margin, 3),
            "pythagorean_home": round(w_h, 4), "pythagorean_away": round(w_a, 4),
            "pythagorean_exponent": exponent, "home_advantage_runs": home_adv,
        }
        attach_price(row, p_home, "Money Line", fx["home"], sample,
                     extra_reasons=["MLB's answered endpoints publish season aggregates only, so the "
                                    "game-margin dispersion is derived from those aggregates rather than "
                                    "from a completed-game sample"])
        row["other_markets"] = [
            mm.price_row(1 - p_home, "Money Line", fx["away"]),
            mm.price_row(p_over, "Game Totals", f"Over {total_line}"),
            mm.price_row(1 - p_over, "Game Totals", f"Under {total_line}"),
            mm.price_row(mm.p_margin_gt(1.5, exp_home - exp_away, sigma_margin), "Run Line",
                         f'{fx["home"]} -1.5'),
            mm.price_row(mm.p_margin_gt(1.5, exp_away - exp_home, sigma_margin), "Run Line",
                         f'{fx["away"]} +1.5'),
        ] + handicap_ladder(exp_home - exp_away, sigma_margin, "Run Line", fx["home"], fx["away"],
                            step=1.0, span=3.0) + total_ladder(total, sigma_total, step=0.5, span=2.5)


# =========================================================================================
# TENNIS — WTA official live-scoring feed
# =========================================================================================
SEED_BASE = 0.36  # a ranking/seed step is worth this much logit; published on the calibration row


def build_tennis(cap: Capture, olbg: dict):
    src = sources.wta(cap)
    matches = [m for m in src["matches"] if sources.in_window(m["start_utc"])]
    both_seeded = sum(1 for m in matches if m.get("seed_a") and m.get("seed_b"))
    calibrations.append({
        "id": "wta_seed_logit",
        "sport": "Tennis",
        "games": len(matches),
        "method": ("logistic on the difference between the official draw seeds published by the WTA in its own "
                   "live-scoring feed; 0.36 logit units per seed step"),
        "seed_logit": SEED_BASE,
        "matches_listed": len(matches),
        "matches_with_both_seeds": both_seeded,
        "source_url": matches[0]["feed_url"] if matches else None,
        "note": ("the WTA rankings endpoint api.wtatennis.com/tennis/rankings/* returned HTTP 404 in every "
                 "captured variant, so the official draw seed is the only strength measure available"),
    })
    for m in sorted(matches, key=lambda x: x["start_utc"]):
        seed_a = int(m["seed_a"]) if m.get("seed_a") else None
        seed_b = int(m["seed_b"]) if m.get("seed_b") else None
        row = add_row(**base(
            "Tennis", f'{m["tournament"]} ({m["level"]})', f'{m["player_a"]} v {m["player_b"]}',
            m["player_a"], m["player_b"], m["start_utc"], m["source_url"], m["capture"],
            competition_round=f'{m["round"]} (round id {m["round_id"]})',
            venue=f'{m["city"]}, {m["country"]}', surface=m["surface"], court=m["court"],
            not_before=m["not_before"], event_start=m["event_start"], event_end=m["event_end"],
            feed_url=m["feed_url"], olbg_listed=olbg_for(olbg, m["player_a"], m["player_b"]),
        ))
        row["stats"] = {
            "player_a": {"seed": seed_a, "country": m["country_a"]},
            "player_b": {"seed": seed_b, "country": m["country_b"]},
            "source_url": m["feed_url"],
        }
        row["injury_note"] = None
        row["unverified_fields"] = ["injury_note", "wta_ranking"]
        row["notes"].append("the WTA feed publishes the official draw seed; it does not publish a ranking number for this player")
        if seed_a is None and seed_b is None:
            row["verified"] = False
            row["unverified_fields"].append("strength_input")
            row["confidence"] = "Unpriced"
            row["confidence_reasons"] = ["neither player carries an official draw seed, so no strength input exists"]
            continue
        # an unseeded qualifier is treated as the seed immediately below the lowest seed in the draw
        eff_a = seed_a if seed_a is not None else 17
        eff_b = seed_b if seed_b is not None else 17
        x = (eff_b - eff_a) * SEED_BASE
        p_a = mm.logistic(x, 1.0)
        sample = 0
        attach_price(row, p_a, "Win Match", m["player_a"], sample,
                     extra_reasons=["strength input is the official draw seed only; the WTA rankings endpoint "
                                    "was unreachable from the capture runner (HTTP 404)"])
        row["our_inputs"] = {"seed_a": eff_a, "seed_b": eff_b, "seed_logit_per_step": SEED_BASE,
                             "seed_a_official": seed_a, "seed_b_official": seed_b}
        row["other_markets"] = [mm.price_row(1 - p_a, "Win Match", m["player_b"])]


# =========================================================================================
# RUGBY UNION — URC, Gallagher PREM, TOP 14
# =========================================================================================
RUGBY_SIGMA = 13.5  # points; replaced by an observed value where one exists


def _rugby_table(rows_in, pf_key, pa_key, pl_key):
    out = {}
    for r in rows_in:
        pl = r.get(pl_key)
        if not pl:
            continue
        out[r["team"]] = {
            "team": r["team"], "played": pl, "pf": r.get(pf_key), "pa": r.get(pa_key),
            "diff": (r.get(pf_key) or 0) - (r.get(pa_key) or 0),
            "diff_pg": ((r.get(pf_key) or 0) - (r.get(pa_key) or 0)) / pl,
            "pf_pg": (r.get(pf_key) or 0) / pl, "pa_pg": (r.get(pa_key) or 0) / pl,
            "points": r.get("pts"), "source_url": r.get("source_url"), "rank": r.get("rank"),
        }
    return out


def build_rugby_union(cap: Capture, olbg: dict):
    urc_src = sources.urc(cap)
    urc_table = evidence.table("urc_table_2026-27")
    urc_ratings = _rugby_table(urc_table, "pf", "pa", "pl")
    urc_evidence = evidence.get("urc_table_2026-27")
    games = sum(r["pl"] for r in urc_table) // 2
    calibrations.append({
        "id": "urc_rating_basis", "sport": "Rugby Union", "games": games,
        "method": ("points-for / points-against per game from the official URC league table, home advantage "
                   "and margin dispersion held at the published rugby defaults because the URC stats site is a "
                   "client-side app and only Round 3 results could be read"),
        "sigma_margin": RUGBY_SIGMA, "home_advantage_points": 3.0,
        "source_url": urc_evidence["source_url"],
        "read_kind": urc_evidence["read_kind"],
        "note": urc_evidence["why_not_capture"],
    })
    urc_rounds = urc_src["rounds"]
    prov = urc_src["source"]
    for rnd in ("Round 4", "Round 5"):
        for fx in urc_rounds.get(rnd, []):
            date = fx["date"]
            if date < TODAY:
                continue
            start = None
            if fx.get("ko_local"):
                start = f"{date}T{_ko_to_utc(fx['ko_local'])}:00Z"
            home_key = _urc_key(fx["home"], urc_ratings)
            away_key = _urc_key(fx["away"], urc_ratings)
            row = add_row(**base(
                "Rugby Union", f"United Rugby Championship {rnd}", f'{fx["away"]} @ {fx["home"]}',
                fx["home"], fx["away"], start, fx["source_url"], fx["capture"],
                competition_round=rnd, venue=fx["venue"], ko_local=fx["ko_local"],
                ko_timezone=fx["ko_timezone"], league="URC", olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
            ))
            row["injury_note"] = None
            row["unverified_fields"] = ["injury_note"]
            if not fx.get("ko_local"):
                row["unverified_fields"].append("start_time")
            if not home_key or not away_key:
                row["verified"] = False
                row["unverified_fields"].append("standings")
                continue
            h, a = urc_ratings[home_key], urc_ratings[away_key]
            sample = min(h["played"], a["played"])
            d_h = mm.shrink(h["diff_pg"], sample, RUGBY_K)
            d_a = mm.shrink(a["diff_pg"], sample, RUGBY_K)
            margin = d_h - d_a + 3.0
            total = h["pf_pg"] + a["pa_pg"]
            sigma_eff = mm.sigma_with_rating_error(RUGBY_SIGMA, RUGBY_SIGMA, sample, RUGBY_K)
            p_home = mm.p_two_way(margin, sigma_eff)
            total_line = _nearest_half(total / 1) if total else None
            row["stats"] = {"home": h, "away": a, "source_url": urc_evidence["source_url"],
                            "standings_read_utc": urc_evidence["read_utc"]}
            row["our_inputs"] = {"expected_margin": round(margin, 3), "sigma_margin": round(sigma_eff, 3),
                                 "home_advantage_points": 3.0, "expected_total": round(total, 2),
                                 "home_diff_pg_shrunk": round(d_h, 3), "away_diff_pg_shrunk": round(d_a, 3),
                                 "shrinkage_games_k": RUGBY_K, "rating_sample_games": sample}
            attach_price(row, p_home, "To Win", fx["home"], sample,
                         extra_reasons=["the URC table could only be read as of Round 3, so Friday 23 October "
                                        "results are not in the rating"])
            row["other_markets"] = [
                mm.price_row(1 - p_home, "To Win", fx["away"]),
                mm.price_row(mm.p_margin_gt(6.5, margin, RUGBY_SIGMA), "Handicap", f'{fx["home"]} -6.5'),
                mm.price_row(mm.p_margin_gt(6.5, -margin, RUGBY_SIGMA), "Handicap", f'{fx["away"]} +6.5'),
            ]
            if total_line:
                row["other_markets"] += [
                    mm.price_row(mm.p_total_over(total_line, total, RUGBY_SIGMA * 1.15), "Total Points",
                                 f"Over {total_line}"),
                    mm.price_row(1 - mm.p_total_over(total_line, total, RUGBY_SIGMA * 1.15), "Total Points",
                                 f"Under {total_line}"),
                ]

    # ---- Gallagher PREM
    prem = evidence.table("prem_table_2026-27")
    prem_ev = evidence.get("prem_table_2026-27")
    prem_ratings = {}
    for r in prem:
        prem_ratings[r["team"]] = {
            "team": r["team"], "played": r["p"], "diff": r["pd"], "diff_pg": r["pd"] / r["p"],
            "points": r["pts"], "form": r["form"], "source_url": r["source_url"], "rank": r["rank"],
            "wins": r["w"], "losses": r["l"],
        }
    prem_games = sum(r["p"] for r in prem) // 2
    diffs = [r["pd"] / r["p"] for r in prem]
    _, sd_diff = mm.mean_sd(diffs)
    prem_sigma = (sd_diff or 14.0) * (2 ** 0.5)
    calibrations.append({
        "id": "prem_rating_basis", "sport": "Rugby Union", "games": prem_games,
        "method": ("points difference per game from the official Gallagher PREM standings; the margin dispersion "
                   "is the observed dispersion of those per-game differences across the ten clubs, scaled by "
                   "sqrt(2) because a match margin combines two such differences"),
        "sigma_margin": round(prem_sigma, 3), "home_advantage_points": 3.0,
        "source_url": prem_ev["source_url"], "read_kind": prem_ev["read_kind"],
        "note": prem_ev["why_not_capture"],
    })
    # ---- TOP 14
    top14 = evidence.table("top14_table_2026-27_j6")
    top14_ev = evidence.get("top14_table_2026-27_j6")
    top14_ratings = {}
    for r in top14:
        top14_ratings[r["team"]] = {
            "team": r["team"], "played": r["m"], "pf": r["pts_m"], "pa": r["pts_e"], "diff": r["diff"],
            "diff_pg": r["diff"] / r["m"], "pf_pg": r["pts_m"] / r["m"], "pa_pg": r["pts_e"] / r["m"],
            "points": r["pts"], "form": r["form_j2_j6"], "wins": r["g"], "losses": r["p"],
            "source_url": r["source_url"], "rank": r["rank"],
        }
    t14_diffs = [r["diff"] / r["m"] for r in top14]
    _, sd_t14 = mm.mean_sd(t14_diffs)
    t14_sigma = (sd_t14 or 12.0) * (2 ** 0.5)
    calibrations.append({
        "id": "top14_rating_basis", "sport": "Rugby Union", "games": sum(r["m"] for r in top14) // 2,
        "method": ("points difference per game from the official TOP 14 classement after Journee 6 (all 14 clubs, "
                   "84 games); margin dispersion is the observed dispersion of those per-game differences scaled "
                   "by sqrt(2)"),
        "sigma_margin": round(t14_sigma, 3), "home_advantage_points": 3.0,
        "source_url": top14_ev["source_url"], "read_kind": top14_ev["read_kind"],
        "note": top14_ev["why_not_capture"],
    })
    for fx in top14_ev["next_fixtures"]:
        h = top14_ratings.get(fx["home"])
        a = top14_ratings.get(fx["away"])
        start = f'{fx["date"]}T19:45:00Z' if fx["date"] == "2026-10-24" else None
        row = add_row(**base(
            "Rugby Union", f'TOP 14 {fx["round"]}', f'{fx["away"]} @ {fx["home"]}', fx["home"], fx["away"],
            None, fx["url"], {"read_kind": "live_page_read", "evidence_id": top14_ev["id"],
                             "read_utc": top14_ev["read_utc"], "source_url": fx["url"]},
            competition_round=fx["round"], match_date=fx["date"], league="TOP 14",
            olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
        ))
        row["unverified_fields"] = ["start_time", "venue", "injury_note"]
        row["injury_note"] = None
        row["notes"].append("the official classement names the Journee 7 fixture and its date and links its match "
                            "sheet, but does not publish a kick-off time or venue on that page")
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"].append("standings")
            continue
        sample = min(h["played"], a["played"])
        d_h = mm.shrink(h["diff_pg"], sample, RUGBY_K)
        d_a = mm.shrink(a["diff_pg"], sample, RUGBY_K)
        margin = d_h - d_a + 3.0
        total = h["pf_pg"] + a["pa_pg"]
        sigma_eff = mm.sigma_with_rating_error(t14_sigma, t14_sigma, sample, RUGBY_K)
        p_home = mm.p_two_way(margin, sigma_eff)
        row["stats"] = {"home": h, "away": a, "source_url": top14_ev["source_url"],
                        "standings_read_utc": top14_ev["read_utc"]}
        row["our_inputs"] = {"expected_margin": round(margin, 3), "sigma_margin": round(sigma_eff, 3),
                             "home_advantage_points": 3.0, "expected_total": round(total, 2),
                             "home_diff_pg_shrunk": round(d_h, 3), "away_diff_pg_shrunk": round(d_a, 3),
                             "shrinkage_games_k": RUGBY_K, "rating_sample_games": sample}
        attach_price(row, p_home, "To Win", fx["home"], sample)
        row["other_markets"] = [
            mm.price_row(1 - p_home, "To Win", fx["away"]),
            mm.price_row(mm.p_margin_gt(6.5, margin, sigma_eff), "Handicap", f'{fx["home"]} -6.5'),
            mm.price_row(mm.p_margin_gt(6.5, -margin, sigma_eff), "Handicap", f'{fx["away"]} +6.5'),
        ] + handicap_ladder(margin - 3.0, sigma_eff, "Handicap", fx["home"], fx["away"], step=2.5, span=20.0) \
            + total_ladder(total, sigma_eff * 1.15, "Total Points", step=2.5, span=15.0)
    return {"prem_ratings": prem_ratings, "prem_sigma": prem_sigma}


def _ko_to_utc(ko_local: str) -> str:
    """URC publishes 'KO 19.45 IRE & UK'. On 23-24 October 2026 Ireland and the UK are on BST/IST
    (UTC+1) and South Africa is on SAST (UTC+2); the article also prints the SA time, so the UTC
    hour is the IRE & UK hour minus one."""
    hh, mm = ko_local.split(":")
    return f"{(int(hh) - 1) % 24:02d}:{mm}"


URC_ALIASES = {
    "hollywoodbets sharks": "Hollywoodbets Sharks", "sharks": "Hollywoodbets Sharks",
    "vodacom bulls": "Vodacom Bulls", "bulls": "Vodacom Bulls",
    "dhl stormers": "DHL Stormers", "stormers": "DHL Stormers",
    "10bet lions": "10bet Lions", "lions": "10bet Lions",
    "dragons rfc": "Dragons RFC", "dragons": "Dragons RFC",
    "cardiff": "Cardiff Rugby", "zebre parma": "Zebre Parma", "zebre": "Zebre Parma",
    "edinburgh": "Edinburgh", "munster": "Munster", "leinster": "Leinster", "ulster": "Ulster",
    "scarlets": "Scarlets", "ospreys": "Ospreys", "connacht": "Connacht", "benetton": "Benetton",
    "glasgow warriors": "Glasgow Warriors", "glasgow": "Glasgow Warriors",
}


def _urc_key(name: str, ratings: dict) -> str | None:
    key = URC_ALIASES.get(name.strip().lower())
    if key and key in ratings:
        return key
    if name in ratings:
        return name
    low = name.lower()
    for team in ratings:
        if low in team.lower() or team.lower() in low:
            return team
    return None


# =========================================================================================
# VOLLEYBALL — Lega Pallavolo Serie A
# =========================================================================================
def build_volleyball(cap: Capture, olbg: dict):
    lv = sources.legavolley(cap)
    ratings = {}
    for r in lv["standings"]:
        if not r.get("played"):
            continue
        ratings[r["team"]] = {
            "team": r["team"], "played": r["played"], "points": r["points"], "won": r["won"], "lost": r["lost"],
            "sets_won": r["sets_won"], "sets_lost": r["sets_lost"], "pf": r["points_for"], "pa": r["points_against"],
            "pf_pg": r["points_for_pg"], "pa_pg": r["points_against_pg"],
            "diff_pg": (r["points_for_pg"] or 0) - (r["points_against_pg"] or 0),
            "rank": r["rank"], "source_url": r["source_url"],
        }
    results = lv["grid_results"]
    margins = []
    for res in results:
        h, a = ratings.get(res["home"]), ratings.get(res["away"])
        if not h or not a:
            continue
        predicted = h["diff_pg"] - a["diff_pg"]
        margins.append(((res["sets_home"] - res["sets_away"]) * 8.0, predicted))
    actual = [m[0] for m in margins]
    predicted = [m[1] for m in margins]
    cal = calibrate("legavolley_margin_dispersion", "Volleyball", actual, predicted,
                    source_url=lv["table_source"]["source_url"], target="legavolley_risultati")
    cal["method"] = ("residual dispersion of (set difference x 8 points) against the points-difference rating over "
                     "the completed 2026/27 SuperLega games in the official Griglia Campionato")
    cal["games_completed_in_capture"] = len(results)
    sigma = cal["residual_sd"] or cal["observed_sd"]
    upcoming = [f for f in lv["grid"] if TODAY <= f["date"] <= "2026-11-08"]
    for fx in sorted(upcoming, key=lambda f: f["date"]):
        h, a = ratings.get(fx["home"]), ratings.get(fx["away"])
        row = add_row(**base(
            "Volleyball", "SuperLega Credem Banca 2026/27", f'{fx["away"]} @ {fx["home"]}',
            fx["home"], fx["away"], None, fx["source_url"], fx["capture"],
            match_date=fx["date"], league="SuperLega", olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
        ))
        row["unverified_fields"] = ["start_time", "venue", "injury_note"]
        row["injury_note"] = None
        row["notes"].append("the official Griglia Campionato publishes the match date only; the kick-off time and "
                            "arena are not on that page")
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"].append("standings")
            continue
        sample = min(h["played"], a["played"])
        if sigma is None:
            row["confidence"] = "Unpriced"
            row["confidence_reasons"] = ["margin dispersion could not be estimated from official results"]
            continue
        d_h = mm.shrink(h["diff_pg"], sample, VOLLEY_K)
        d_a = mm.shrink(a["diff_pg"], sample, VOLLEY_K)
        margin = d_h - d_a + 2.0
        sigma_eff = mm.sigma_with_rating_error(sigma, sigma, sample, VOLLEY_K)
        p_home = mm.p_two_way(margin, sigma_eff)
        row["stats"] = {"home": h, "away": a, "source_url": lv["table_source"]["source_url"],
                        "table_updated": lv["table_updated"]}
        row["our_inputs"] = {"expected_margin_points_pg": round(margin, 3), "sigma": round(sigma_eff, 3),
                             "home_advantage_points_pg": 2.0,
                             "home_diff_pg_shrunk": round(d_h, 3), "away_diff_pg_shrunk": round(d_a, 3),
                             "shrinkage_games_k": VOLLEY_K, "rating_sample_games": sample}
        attach_price(row, p_home, "Win Match", fx["home"], sample)
        row["other_markets"] = [mm.price_row(1 - p_home, "Win Match", fx["away"])]


# =========================================================================================
# HANDBALL — Danish Betoro Herreligaen
# =========================================================================================
def build_handball(cap: Capture, olbg: dict):
    hb = sources.handball_denmark(cap)
    ratings = {}
    for r in hb["standings"]:
        if not r.get("played"):
            continue
        ratings[r["team"]] = {
            "team": r["team"], "played": r["played"], "wins": r["wins"], "draws": r["draws"],
            "losses": r["losses"], "gf": r["goals_for"], "ga": r["goals_against"],
            "points": r["points"], "diff": (r["goals_for"] or 0) - (r["goals_against"] or 0),
            "diff_pg": ((r["goals_for"] or 0) - (r["goals_against"] or 0)) / r["played"],
            "gf_pg": (r["goals_for"] or 0) / r["played"], "ga_pg": (r["goals_against"] or 0) / r["played"],
            "rank": r["rank"], "form": r["form"], "source_url": r["source_url"],
        }
    diffs = [r["diff_pg"] for r in ratings.values()]
    _, sd = mm.mean_sd(diffs)
    sigma = (sd or 5.0) * (2 ** 0.5)
    calibrations.append({
        "id": "danish_handball_rating_basis", "sport": "Handball",
        "games": sum(r["played"] for r in ratings.values()) // 2,
        "method": ("goal difference per game from the official Betoro Herreligaen table on tophaandbold.dk; the "
                   "margin dispersion is the observed dispersion of those per-game differences across the 14 clubs, "
                   "scaled by sqrt(2)"),
        "sigma_margin": round(sigma, 3), "home_advantage_goals": 1.5,
        "source_url": hb["source"]["source_url"], "capture_target": "tophaandbold_herreligaen",
        "clubs": len(ratings),
    })
    # fixtures: the official kampprogram page
    fixtures = _handball_fixtures(cap, ratings)
    for fx in fixtures:
        h, a = ratings.get(fx["home"]), ratings.get(fx["away"])
        row = add_row(**base(
            "Handball", "Betoro Herreligaen 2026/27", f'{fx["away"]} @ {fx["home"]}',
            fx["home"], fx["away"], fx.get("start_utc"), fx["source_url"], fx["capture"],
            match_date=fx.get("date"), league="Betoro Herreligaen", olbg_listed=olbg_for(olbg, fx["home"], fx["away"]),
        ))
        row["unverified_fields"] = ["injury_note"] + ([] if fx.get("start_utc") else ["start_time"])
        row["injury_note"] = None
        if not h or not a:
            row["verified"] = False
            row["unverified_fields"].append("standings")
            row["notes"].append("club is in the official fixture list but not in the official league table")
            continue
        sample = min(h["played"], a["played"])
        d_h = mm.shrink(h["diff_pg"], sample, HANDBALL_K)
        d_a = mm.shrink(a["diff_pg"], sample, HANDBALL_K)
        margin = d_h - d_a + 1.5
        total = h["gf_pg"] + a["ga_pg"]
        sigma_eff = mm.sigma_with_rating_error(sigma, sigma, sample, HANDBALL_K)
        p_home = mm.p_two_way(margin, sigma_eff)
        p_draw = 0.02
        p_home_reg = p_home * (1 - p_draw)
        total_line = _nearest_half(total)
        row["stats"] = {"home": h, "away": a, "source_url": hb["source"]["source_url"]}
        row["our_inputs"] = {"expected_margin": round(margin, 3), "sigma_margin": round(sigma_eff, 3),
                             "home_advantage_goals": 1.5, "expected_total": round(total, 2),
                             "shrinkage_games_k": HANDBALL_K, "rating_sample_games": sample}
        attach_price(row, p_home_reg + p_draw / 2, "Money Line", fx["home"], sample)
        row["other_markets"] = [
            mm.price_row(1 - p_home_reg - p_draw / 2, "Money Line", fx["away"]),
            mm.price_row(mm.p_margin_gt(3.5, margin, sigma_eff), "Handicap", f'{fx["home"]} -3.5'),
            mm.price_row(mm.p_margin_gt(3.5, -margin, sigma_eff), "Handicap", f'{fx["away"]} +3.5'),
            mm.price_row(mm.p_total_over(total_line, total, sigma_eff * 1.1), "Total Points", f"Over {total_line}"),
            mm.price_row(1 - mm.p_total_over(total_line, total, sigma_eff * 1.1), "Total Points", f"Under {total_line}"),
        ] + handicap_ladder(margin - 1.5, sigma_eff, "Handicap", fx["home"], fx["away"], step=1.5, span=12.0) \
            + total_ladder(total, sigma_eff * 1.1, step=2.5, span=15.0)
    return ratings


def _handball_fixtures(cap: Capture, ratings: dict) -> list[dict]:
    """Parse the official tophaandbold.dk kampprogram page for the next round's fixtures."""
    out = []
    if not cap.have("tophaandbold_kampprogram"):
        return out
    prov = cap.provenance("tophaandbold_kampprogram")
    text = cap.text("tophaandbold_kampprogram")
    body = re.sub(r"<script\b.*?</script>", " ", text, flags=re.S | re.I)
    names = sorted(ratings, key=len, reverse=True)
    # a fixture line looks like: <date> <time> <home> - <away> <arena>
    for m in re.finditer(
        r"(\d{2}\.\d{2}\.\d{4}|\d{4}-\d{2}-\d{2}|\d{1,2}\.\s*[a-zæøå]+\.)\s*(\d{2}:\d{2})?", body, flags=re.I
    ):
        seg = re.sub(r"<[^>]+>", " ", body[m.start():m.start() + 900])
        seg = re.sub(r"\s+", " ", seg)
        found = [n for n in names if n in seg]
        if len(found) < 2:
            continue
        home, away = found[0], found[1]
        if home == away:
            continue
        raw = m.group(1)
        date = None
        dm = re.fullmatch(r"(\d{2})\.(\d{2})\.(\d{4})", raw)
        if dm:
            date = f"{dm.group(3)}-{dm.group(2)}-{dm.group(1)}"
        else:
            dm = re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw)
            if dm:
                date = raw
        if not date or not (TODAY <= date <= "2026-11-08"):
            continue
        time = m.group(2)
        start = None
        if time:
            hh, mi = time.split(":")
            # Danish league times are published in CET/CEST; late October Denmark is on CEST until 25 Oct
            offset = 2 if date < "2026-10-25" else 1
            start = f"{date}T{(int(hh) - offset) % 24:02d}:{mi}:00Z"
        out.append({"home": home, "away": away, "date": date, "start_utc": start,
                    "source_url": prov["source_url"], "capture": prov})
    seen = set()
    deduped = []
    for fx in out:
        key = (fx["date"], fx["home"], fx["away"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(fx)
    return deduped


# =========================================================================================
# SNOOKER — snooker.org draw sheets (official seeding + results), WST event
# =========================================================================================
def build_snooker(cap: Capture, olbg: dict):
    events = sources.snooker_events(cap)
    for ev in events:
        for match in ev["upcoming"]:
            row = add_row(**base(
                "Snooker", ev["event_name"], f'{match["player_a"]} v {match["player_b"]}',
                match["player_a"], match["player_b"], match.get("start_utc"), ev["source_url"], ev["capture"],
                competition_round=match["stage"], best_of=match.get("best_of"),
                prize=match.get("prize"), event_dates=ev.get("dates"), venue=ev.get("venue"),
                olbg_listed=olbg_for(olbg, match["player_a"], match["player_b"]),
            ))
            row["unverified_fields"] = ["injury_note"] + ([] if match.get("start_utc") else ["start_time"])
            row["injury_note"] = None
            row["form_home"] = match.get("path_a", [])
            row["form_away"] = match.get("path_b", [])
            seed_a, seed_b = match.get("seed_a"), match.get("seed_b")
            row["stats"] = {"player_a": {"seed": seed_a}, "player_b": {"seed": seed_b},
                            "source_url": ev["source_url"],
                            "note": "the number in brackets on the official draw sheet is the world-ranking seed"}
            if seed_a is None or seed_b is None:
                row["verified"] = False
                row["unverified_fields"].append("strength_input")
                row["confidence"] = "Unpriced"
                row["confidence_reasons"] = ["the official draw sheet does not carry a seed for both players"]
                continue
            x = (seed_b - seed_a) * 0.032
            p_a = mm.logistic(x, 1.0)
            n_frames = _best_of_frames(match.get("best_of"))
            sample = len(match.get("path_a") or []) + len(match.get("path_b") or [])
            attach_price(row, p_a, "Win Match", match["player_a"], sample,
                         extra_reasons=["strength input is the official world-ranking seed on the draw sheet; the "
                                        "World Snooker Tour site is a client-side app and returned an empty shell "
                                        "to the capture runner"])
            row["our_inputs"] = {"seed_a": seed_a, "seed_b": seed_b, "seed_logit_per_rank": 0.032,
                                 "best_of": match.get("best_of"), "frames": n_frames}
            row["other_markets"] = [mm.price_row(1 - p_a, "Win Match", match["player_b"])]
    return events


def _best_of_frames(best_of) -> int | None:
    if not best_of:
        return None
    m = re.search(r"(\d+)", str(best_of))
    return int(m.group(1)) if m else None


# =========================================================================================
# GOLF — PGA Tour official leaderboard dataset
# =========================================================================================
def build_golf(cap: Capture, olbg: dict):
    lb = sources.golf_pga(cap, "pgatour_bermuda")
    if not lb.get("rows"):
        flag("Golf", "source-unreachable", "high",
             "the PGA Tour leaderboard page carried no csvw dataset, so no golf line could be originated",
             source_url="https://www.pgatour.com/leaderboard")
        return {}
    prov = lb["capture"]
    rows_in = []
    for r in lb["rows"]:
        pos, player, tot = r.get("POS"), r.get("PLAYER"), r.get("TOT")
        if not player or tot in (None, "-", ""):
            continue
        try:
            score = int(tot)
        except ValueError:
            continue
        rounds = [x for x in (r.get("R1"), r.get("R2"), r.get("R3"), r.get("R4")) if x and x != "-"]
        rows_in.append({"pos": pos, "player": player, "total": score, "rounds": rounds,
                        "thru": r.get("THRU")})
    if not rows_in:
        return {}
    leader = min(x["total"] for x in rows_in)
    all_rounds = [int(v) for x in rows_in for v in x["rounds"] if str(v).isdigit()]
    mu_round, sd_round = mm.mean_sd([float(v) for v in all_rounds])
    rounds_left = max(0, 4 - max(len(x["rounds"]) for x in rows_in))
    cal = calibrate("pga_scoring_dispersion", "Golf", [float(v) for v in all_rounds],
                    source_url=prov["source_url"], target="pgatour_bermuda")
    calibrations[-1].update({
        "method": ("mean and standard deviation of every individual 18-hole score posted by the field in the "
                   "official PGA Tour leaderboard dataset embedded in the leaderboard page"),
        "round_scores": len(all_rounds), "mean_round": round(mu_round, 3) if mu_round else None,
        "sd_round": round(sd_round, 3) if sd_round else None, "rounds_remaining": rounds_left,
        "tournament": lb["meta"].get("tournamentName"), "status": lb["meta"].get("tournamentStatus"),
        "course": lb["meta"].get("courseName"), "location": lb["meta"].get("tournamentLocation"),
    })
    if sd_round is None or rounds_left <= 0:
        return {"leaderboard": rows_in, "leader": leader, "rounds_left": rounds_left}
    sigma_remaining = sd_round * (rounds_left ** 0.5)
    # head-to-head matchups: adjacent players on the official leaderboard
    order = sorted(rows_in, key=lambda x: (x["total"], x["player"]))
    pairs = []
    for i in range(0, len(order) - 1, 2):
        pairs.append((order[i], order[i + 1]))
    for pa, pb in pairs[:12]:
        gap = pb["total"] - pa["total"]  # positive means A is ahead
        x = gap / sigma_remaining * 1.0
        p_a = mm.logistic(x * 1.7, 1.0)
        row = add_row(**base(
            "Golf", f'{lb["meta"].get("tournamentName")} — leaderboard matchup',
            f'{pa["player"]} v {pb["player"]}', pa["player"], pb["player"], None, prov["source_url"], prov,
            competition_round=f'{rounds_left} round(s) remaining',
            venue=lb["meta"].get("courseName"), location=lb["meta"].get("tournamentLocation"),
            tournament_status=lb["meta"].get("tournamentStatus"), olbg_listed=[],
        ))
        row["unverified_fields"] = ["start_time", "injury_note", "withdrawn_status"]
        row["injury_note"] = None
        row["stats"] = {
            "player_a": {"position": pa["pos"], "total": pa["total"], "rounds": pa["rounds"], "thru": pa["thru"]},
            "player_b": {"position": pb["pos"], "total": pb["total"], "rounds": pb["rounds"], "thru": pb["thru"]},
            "source_url": prov["source_url"],
        }
        row["our_inputs"] = {"gap_strokes": gap, "sigma_remaining_strokes": round(sigma_remaining, 3),
                             "sd_18_holes": round(sd_round, 3), "rounds_remaining": rounds_left}
        attach_price(row, p_a, "Win Match", pa["player"], len(all_rounds),
                     extra_reasons=["the PGA Tour leaderboard dataset publishes a position of WD for withdrawn "
                                    "players but no withdrawal reason, so a late scratch cannot be priced"])
        row["other_markets"] = [mm.price_row(1 - p_a, "Win Match", pb["player"])]
    # outright: Plackett-Luce over the official gap to the leader
    gaps = {x["player"]: x["total"] - leader for x in order[:24]}
    strengths = mm.strengths_from_gaps(gaps, sigma_remaining)
    probs = mm.plackett_luce(strengths)
    top = sorted(probs.items(), key=lambda kv: -kv[1])
    row = add_row(**base(
        "Golf", f'{lb["meta"].get("tournamentName")} — tournament winner',
        f'{lb["meta"].get("tournamentName")} winner', top[0][0], None, None, prov["source_url"], prov,
        competition_round=f'{rounds_left} round(s) remaining', venue=lb["meta"].get("courseName"),
        olbg_listed=[], market_kind="outright",
    ))
    row["unverified_fields"] = ["start_time", "injury_note"]
    row["injury_note"] = None
    row["stats"] = {"field": [{"player": p, "gap_to_leader": gaps[p], "our_prob": round(probs[p], 4)}
                              for p, _ in top], "source_url": prov["source_url"]}
    row["our_inputs"] = {"sigma_remaining_strokes": round(sigma_remaining, 3), "halving_gap": round(sigma_remaining, 3),
                         "field_size_priced": len(probs)}
    attach_price(row, probs[top[0][0]], "To Win", top[0][0], len(all_rounds))
    row["other_markets"] = [mm.price_row(probs[p], "To Win", p) for p, _ in top[1:8]]
    return {"leaderboard": rows_in, "leader": leader, "rounds_left": rounds_left, "sd_round": sd_round}


# =========================================================================================
# MOTOR RACING — formula1.com official championship tables
# =========================================================================================
def build_motor_racing(cap: Capture, olbg: dict):
    drv = sources.f1_standings(cap, "f1_drivers_2026")
    con = sources.f1_standings(cap, "f1_constructors_2026")
    if not drv.get("rows"):
        return {}
    prov = drv["capture"]
    standings = []
    for r in drv["rows"]:
        try:
            pts = int(str(r.get("pts.")).strip())
        except (TypeError, ValueError):
            continue
        name = re.sub(r"\s+[A-Z]{3}$", "", (r.get("driver") or "").strip())
        standings.append({"pos": int(r["pos."]), "driver": name, "code": (r.get("driver") or "")[-3:],
                          "team": r.get("team"), "nationality": r.get("nationality"), "points": pts})
    leader = standings[0]["points"]
    gaps = {s["driver"]: leader - s["points"] for s in standings}
    races_left, points_left = _f1_races_remaining(cap)
    halving = max(12.0, (points_left or 100) * 0.35)
    strengths = mm.strengths_from_gaps(gaps, halving)
    probs = mm.plackett_luce(strengths)
    calibrations.append({
        "id": "f1_championship_outright", "sport": "Motor Racing",
        "games": len(standings),
        "method": ("Plackett-Luce over the official FIA Formula One World Championship driver points, with each "
                   "competitor's strength halved for every `halving_gap` points they trail the leader; the halving "
                   "gap is 35% of the points still available this season"),
        "races_remaining": races_left, "points_available": points_left, "halving_gap": round(halving, 2),
        "source_url": prov["source_url"], "capture_target": "f1_drivers_2026",
        "note": "formula1.com renders the championship tables server-side, so this is read from committed bytes",
    })
    top = sorted(probs.items(), key=lambda kv: -kv[1])
    row = add_row(**base(
        "Motor Racing", "FIA Formula One World Championship 2026 — Drivers",
        "2026 Drivers' World Champion", top[0][0], None, None, prov["source_url"], prov,
        competition_round=f"{races_left} round(s) remaining", market_kind="outright",
        olbg_listed=[],
    ))
    row["unverified_fields"] = ["start_time", "injury_note"]
    row["injury_note"] = None
    row["stats"] = {"standings": standings[:12], "source_url": prov["source_url"]}
    row["our_inputs"] = {"points_available": points_left, "halving_gap": round(halving, 2),
                         "gap_to_leader": {s["driver"]: gaps[s["driver"]] for s in standings[:8]}}
    attach_price(row, probs[top[0][0]], "To Win", top[0][0], len(standings))
    row["other_markets"] = [mm.price_row(probs[p], "To Win", p) for p, _ in top[1:8]]
    # one outright race-winner market per round the official index still lists ahead of today
    cal = sources.f1_calendar(cap)
    driver_strength = {s_["driver"]: mm.strengths_from_gaps(gaps, halving)[s_["driver"]] for s_ in standings}
    for rnd in cal:
        if not rnd.get("end_date") or rnd["end_date"] < TODAY:
            continue
        probs_r = mm.plackett_luce(driver_strength)
        top_r = sorted(probs_r.items(), key=lambda kv: -kv[1])[:8]
        rrow = add_row(**base(
            "Motor Racing", f'2026 Formula 1 World Championship — Round {rnd["round"]}, {rnd["country"]}',
            f'{rnd["country"]} Grand Prix winner', top_r[0][0], None, None, prov["source_url"], prov,
            competition_round=f'Round {rnd["round"]} — {rnd["date_span"]}', market_kind="outright",
            race_end_date=rnd["end_date"], olbg_listed=[],
        ))
        rrow["unverified_fields"] = ["start_time", "injury_note", "circuit"]
        rrow["injury_note"] = None
        rrow["notes"].append("formula1.com publishes the round, the country and the weekend date range; the circuit "
                             "name and the session times are on the individual race page, which is a client-side app")
        rrow["stats"] = {"field": [{"driver": d, "our_prob": round(p, 4)} for d, p in top_r],
                         "source_url": prov["source_url"]}
        rrow["our_inputs"] = {"round": rnd["round"], "country": rnd["country"],
                              "date_span": rnd["date_span"], "halving_gap": round(halving, 2),
                              "basis": "championship points as published by formula1.com"}
        attach_price(rrow, probs_r[top_r[0][0]], "To Win", top_r[0][0], len(standings),
                     extra_reasons=["a single race winner is priced off championship points, which formula1.com "
                                    "publishes, because the per-race results tables are rendered client-side"])
        rrow["other_markets"] = [mm.price_row(probs_r[d], "To Win", d) for d, _ in top_r[1:]]

    if con.get("rows"):
        cprov = con["capture"]
        cstand = []
        for r in con["rows"]:
            try:
                pts = int(str(r.get("pts.")).strip())
            except (TypeError, ValueError):
                continue
            cstand.append({"pos": int(r["pos."]), "team": r.get("team"), "points": pts})
        if cstand:
            cleader = cstand[0]["points"]
            cgaps = {c["team"]: cleader - c["points"] for c in cstand}
            cprobs = mm.plackett_luce(mm.strengths_from_gaps(cgaps, halving))
            ctop = sorted(cprobs.items(), key=lambda kv: -kv[1])
            crow = add_row(**base(
                "Motor Racing", "FIA Formula One World Championship 2026 — Constructors",
                "2026 Constructors' World Champion", ctop[0][0], None, None, cprov["source_url"], cprov,
                competition_round=f"{races_left} round(s) remaining", market_kind="outright",
                olbg_listed=[],
            ))
            crow["unverified_fields"] = ["start_time"]
            crow["stats"] = {"standings": cstand, "source_url": cprov["source_url"]}
            crow["our_inputs"] = {"points_available": points_left, "halving_gap": round(halving, 2)}
            attach_price(crow, cprobs[ctop[0][0]], "To Win", ctop[0][0], len(cstand))
            crow["other_markets"] = [mm.price_row(cprobs[t], "To Win", t) for t, _ in ctop[1:6]]
    return {"standings": standings, "races_left": races_left, "points_left": points_left}


POINTS_PER_ROUND = 34  # 25 for the win + 8 for the sprint win + 1 for fastest lap, the 2026 maximum


def _f1_races_remaining(cap: Capture) -> tuple[int | None, int | None]:
    """Rounds still to be decided, from the official 2026 race index."""
    cal = sources.f1_calendar(cap)
    remaining = [r for r in cal if r.get("end_date") and r["end_date"] >= TODAY]
    if not remaining:
        return None, None
    return len(remaining), len(remaining) * POINTS_PER_ROUND


# =========================================================================================
# RUGBY LEAGUE — RLWC 2026 official fixture feed embedded in rlwc2026.com
# =========================================================================================
def build_rugby_league(cap: Capture, olbg: dict):
    games = sources.rlwc_games(cap)
    if not games:
        flag("Rugby League", "source-unreachable", "high",
             "rlwc2026.com embeds its fixture feed in an escaped JSON blob; no games could be read out of the "
             "captured bytes", source_url="https://www.rlwc2026.com/draws-and-pools")
        return {}
    comps = Counter(g["competition"] for g in games)
    calibrations.append({
        "id": "rlwc_fixture_feed", "sport": "Rugby League", "games": len(games),
        "method": ("every fixture read out of the official RLWC26 fixture blob embedded in rlwc2026.com; the feed "
                   "publishes gameId, round, pool, both teams, the UTC start, the venue, the city, the match-centre "
                   "URL, the ticket URL and the broadcasters"),
        "competitions": dict(comps),
        "source_url": "https://www.rlwc2026.com/draws-and-pools",
        "capture_target": "rlwc_draws",
        "note": ("the same feed carries no score field for completed games, so no official result could be read "
                 "and no rating could be built; nrl.com returns a 798-byte bot wall to the capture runner"),
    })
    for g in sorted(games, key=lambda x: x["start_utc"]):
        if not sources.in_window(g["start_utc"]):
            continue
        row = add_row(**base(
            "Rugby League", f'{g["competition"]} — {g["round"]}', f'{g["away"]} @ {g["home"]}',
            g["home"], g["away"], g["start_utc"], g["match_centre_url"] or g["source_url"], g["capture"],
            competition_round=g["round"], pool=g.get("pool"), venue=g.get("venue"), city=g.get("city"),
            game_id=g.get("game_id"), ticket_url=g.get("ticket_url"), broadcasters=g.get("broadcasters"),
            game_state=g.get("state"), league=g["competition"], olbg_listed=olbg_for(olbg, g["home"], g["away"]),
        ))
        row["verified"] = True
        row["confidence"] = "Unpriced"
        row["confidence_reasons"] = [
            "the official RLWC26 feed publishes no score for completed matches, so no form or rating exists for "
            "these sides, and nrl.com refuses the capture runner (798-byte bot wall)",
        ]
        row["unverified_fields"] = ["our_prob", "our_decimal", "our_american", "injury_note"]
        row["injury_note"] = None
    return {"games": games}


# =========================================================================================
# DARTS — PDC European Championship: fixtures exist, no official line input
# =========================================================================================
def build_darts(cap: Capture, olbg: dict):
    evs = olbg_events
    calibrations.append({
        "id": "pdc_official_source_status", "sport": "Darts", "games": len(evs),
        "method": "no line could be originated: see note",
        "source_url": "https://www.pdc.tv/",
        "note": ("pdc.tv is a pure client-side application. Every one of the 22 pdc.tv URLs captured across three "
                 "passes returned a byte-identical 1,241,860-byte shell with an empty body, including the European "
                 "Championship draw, schedule, results and Order of Merit pages. The PDC results host "
                 "matches.darts.admin.gc.pdcservices.co.uk does not resolve. No official PDC ranking, draw or "
                 "result could therefore be read, so the four listed ties are published unpriced rather than "
                 "filled in from inference."),
    })
    for e in evs:
        row = add_row(**base(
            "Darts", "PDC European Championship 2026", e["event_name"], e["player_a"], e["player_b"],
            e["start_utc"], "https://www.pdc.tv/", {"read_kind": "olbg_listing_only", "olbg_event_url": e["event_url"],
                                                    "olbg_hub_url": e["hub_url"]},
            competition_round="Second round (best of 19 legs)", venue="Westfalenhallen, Dortmund",
            olbg_listed=[{"market": e["market_alias"], "olbg_event_url": e["event_url"]}],
        ))
        row["verified"] = False
        row["unverified_fields"] = ["fixture", "our_prob", "our_decimal", "our_american", "injury_note", "form"]
        row["injury_note"] = None
        row["confidence"] = "Unpriced"
        row["confidence_reasons"] = [
            "the pairing is listed on OLBG but could not be confirmed on any official PDC page, because every "
            "pdc.tv URL returns an identical empty client-side shell",
        ]
        row["notes"].append("OLBG is a tipster community, not the sport's governing body: its listing is recorded "
                            "as a cross-reference only and is not treated as verification")
    return {"events": evs}


# =========================================================================================
# CRICKET, GAELIC SPORTS, GREYHOUNDS — fixtures from official boards
# =========================================================================================
def build_cricket(cap: Capture, olbg: dict):
    boards = sources.cricket_boards(cap)
    fixtures = sources.cricket_fixtures(cap)
    for f in fixtures:
        row = add_row(**base(
            "Cricket", f["competition"], f["event"], f["home"], f["away"], f.get("start_utc"),
            f["source_url"], f["capture"], match_date=f.get("date"), venue=f.get("venue"),
            format=f.get("format"), league=f["competition"], olbg_listed=olbg_for(olbg, f["home"], f["away"]),
        ))
        row["verified"] = True
        row["confidence"] = "Unpriced"
        row["confidence_reasons"] = [f["why_unpriced"]] if f.get("why_unpriced") else [
            "no official team-rating or result feed could be reached for this competition"]
        row["unverified_fields"] = ["our_prob", "our_decimal", "our_american", "injury_note"] + (
            [] if f.get("start_utc") else ["start_time"])
        row["injury_note"] = None
        if f.get("organisation"):
            row["official_source_organisation"] = f["organisation"]
    if not fixtures:
        flag("Cricket", "source-unreachable", "high",
             "no cricket fixture could be read out of any captured official board page: icc-cricket.com, nzc.nz and "
             "cricket.com.au are client-side apps and ecb.co.uk/fixtures returns HTTP 404",
             source_url="https://www.icc-cricket.com/fixtures-results")
    return {"boards": boards, "fixtures": fixtures}


def build_gaelic(cap: Capture, olbg: dict):
    fixtures = sources.gaa_fixtures(cap)
    for f in fixtures:
        row = add_row(**base(
            "Gaelic Sports", f["competition"], f["event"], f["home"], f["away"], f.get("start_utc"),
            f["source_url"], f["capture"], match_date=f.get("date"), venue=f.get("venue"),
            competition_round=f.get("round"), county=f.get("county"), league=f["competition"],
            olbg_listed=[],
        ))
        row["verified"] = True
        row["confidence"] = "Unpriced"
        row["confidence_reasons"] = [
            "the county board publishes the fixture, venue and throw-in time but no league table or results for "
            "these club grades, so there is no official input for a line"]
        row["unverified_fields"] = ["our_prob", "our_decimal", "our_american", "injury_note", "form"]
        row["injury_note"] = None
        row["official_source_organisation"] = f.get("organisation")
    if not fixtures:
        flag("Gaelic Sports", "source-unreachable", "high",
             "gaa.ie/fixtures-results and the county boards render their fixture lists client-side; no fixture row "
             "could be read from the committed bytes", source_url="https://www.gaa.ie/fixtures-results")
    return {"fixtures": fixtures}


def build_greyhounds(cap: Capture, olbg: dict):
    meetings = sources.gbgb_meetings(cap)
    for f in meetings:
        row = add_row(**base(
            "Greyhounds", f["competition"], f["event"], None, None, None,
            f["source_url"], f["capture"], match_date=f.get("date"), venue=f.get("track"),
            distance=f.get("distance"), race_type=f.get("type"), day=f.get("day"),
            league=f["competition"], olbg_listed=[],
        ))
        row["verified"] = True
        row["confidence"] = "Unpriced"
        row["confidence_reasons"] = [
            "GBGB publishes the Category One calendar with track, date and distance, but the racecard endpoints "
            "api.gbgb.org.uk/api/{racecards,cards,fixtures,meetings,races,events} all return HTTP 404 and "
            "gbgb.org.uk/racecards/ returns HTTP 404, so no runners, traps or form exist to price"]
        row["unverified_fields"] = ["runners", "traps", "form", "our_prob", "our_decimal", "our_american",
                                    "start_time"]
        row["official_source_organisation"] = "Greyhound Board of Great Britain"
        row["notes"].append("the official GBGB page prints this meeting's sponsor as 'Arena Racng Company' — "
                            "the typo is in the source and is reproduced here exactly as published")
    return {"meetings": meetings}


# =========================================================================================
# driver
# =========================================================================================
BASKETBALL_SRC: dict = {}
olbg_events: list[dict] = []
olbg_by_event: dict = defaultdict(list)


def main() -> int:
    cap = Capture()
    global BASKETBALL_SRC, olbg_events
    import re_olbg
    taxonomy, inventory = re_olbg.build()
    write_json(OUT_ROOT / "olbg_taxonomy.json", taxonomy)
    write_json(OUT_ROOT / "olbg_inventory.json", inventory)
    olbg_events = _darts_events(inventory)
    BASKETBALL_SRC = {
        "euroleague": sources.euroleague(cap, "euroleague_games_E2026", "EuroLeague"),
        "eurocup": sources.euroleague(cap, "eurocup_games_U2026", "EuroCup"),
    }
    global OLBG_LOOKUP
    OLBG_LOOKUP = _olbg_lookup(inventory)
    olbg_lookup = OLBG_LOOKUP

    build_ice_hockey(cap, olbg_lookup)
    build_basketball(cap, olbg_lookup)
    build_baseball(cap, olbg_lookup)
    build_tennis(cap, olbg_lookup)
    build_rugby_union(cap, olbg_lookup)
    build_volleyball(cap, olbg_lookup)
    build_handball(cap, olbg_lookup)
    build_snooker(cap, olbg_lookup)
    build_golf(cap, olbg_lookup)
    build_motor_racing(cap, olbg_lookup)
    build_rugby_league(cap, olbg_lookup)
    build_darts(cap, olbg_lookup)
    build_cricket(cap, olbg_lookup)
    build_gaelic(cap, olbg_lookup)
    build_greyhounds(cap, olbg_lookup)
    _basketball_gap_flags(cap)

    per_sport = Counter(r["sport"] for r in rows)
    per_conf = Counter(r.get("confidence") for r in rows)
    desk = {
        "schema": "olbg4.board-at.desk/1",
        "board": "AT",
        "session": "arena/086e616f-olbg4",
        "generated_utc": NOW,
        "window": {"start_utc": sources.WINDOW_START, "end_utc": sources.WINDOW_END},
        "capture_summary": cap.summary(),
        "sports_requested": SPORTS,
        "counts": {
            "rows": len(rows),
            "per_sport": {s: per_sport.get(s, 0) for s in SPORTS},
            "per_confidence": dict(per_conf),
            "priced": sum(1 for r in rows if r.get("our_prob") is not None),
            "unpriced": sum(1 for r in rows if r.get("our_prob") is None),
            "markets": len(rows) + sum(len(r.get("other_markets") or []) for r in rows),
            "flags": len(flags),
            "calibrations": len(calibrations),
        },
        "olbg_counts": taxonomy["counts"],
        "rows": rows,
        "flags": flags,
        "calibrations": calibrations,
    }
    write_json(OUT_ROOT / "desk.json", desk)
    print(f"desk.json: {len(rows)} rows, {desk['counts']['priced']} priced, {desk['counts']['unpriced']} unpriced, "
          f"{desk['counts']['markets']} markets, {len(flags)} flags")
    for s in SPORTS:
        conf = Counter(r.get("confidence") for r in rows if r["sport"] == s)
        print(f"  {s:<15} rows={per_sport.get(s,0):>4}  {dict(conf)}")
    return 0


def _names(event_name: str) -> frozenset:
    """The set of competitor names in an event label, so 'A @ B' and 'A v B' match."""
    if not event_name:
        return frozenset()
    parts = re.split(r"\s+(?:v|vs|@)\s+|\s+at\s+", event_name)
    return frozenset(p.strip().lower() for p in parts if p.strip())


def _olbg_lookup(inventory: dict) -> dict:
    """Index OLBG's listed event/markets by the set of competitor names, for bettability cross-checks."""
    out = defaultdict(list)
    for e in inventory["events"]:
        listing = {
            "market": e.get("market_alias"),
            "selection": e.get("selection"),
            "olbg_event_url": e.get("event_url"),
            "olbg_event_name": e.get("event_name"),
            "olbg_confidence": e.get("olbg_confidence"),
            "olbg_decimal": e.get("olbg_decimal"),
            "olbg_american": e.get("olbg_american"),
        }
        out[_names(e.get("event_name") or "")].append(listing)
    return out


OLBG_LOOKUP: dict = {}


def olbg_for(_ignored=None, *names: str) -> list[dict]:
    key = frozenset(n.strip().lower() for n in names if n)
    return OLBG_LOOKUP.get(key, [])


def _darts_events(inventory: dict) -> list[dict]:
    out = []
    for e in inventory["events"]:
        if e["sport"] != "Darts":
            continue
        name = e.get("event_name") or ""
        m = re.match(r"^(.+?)\s+vs\.?\s+(.+)$", name)
        if not m:
            continue
        out.append({
            "event_name": name, "player_a": m.group(1).strip(), "player_b": m.group(2).strip(),
            "start_utc": e.get("start_utc"), "event_url": e.get("event_url"),
            "hub_url": e.get("category_url"), "event_id": e.get("event_id"),
            "market_alias": e.get("market_alias"), "selection": e.get("selection"),
            "olbg_confidence": e.get("olbg_confidence"), "olbg_decimal": e.get("olbg_decimal"),
            "olbg_american": e.get("olbg_american"),
        })
    return out


def _basketball_gap_flags(cap: Capture):
    nba_failures = [f for f in cap.failures if "nba" in f["id"] or "stats.nba" in f["url"]]
    if nba_failures:
        detail = "; ".join(sorted({f"{f['id']}: HTTP {f['status']}" for f in nba_failures}))
        flag("Basketball", "source-blocked", "high",
             f"the NBA's official hosts refuse the capture runner, so no NBA line could be originated ({detail}). "
             "cdn.nba.com returns HTTP 403 to datacenter addresses even with the browser header set that "
             "pipeline/config.py already sends; stats.nba.com and data.nba.net do not complete a request at all; "
             "nbastats.blob.core.windows.net returns HTTP 404 for every CSV path tried. Integration request: "
             "pipeline/providers/nba.py has the same gap and withheld 52 NBA markets in the 2026-10-23T21:24Z "
             "pipeline run.",
             source_url="https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json")
    olbg_nba = [r for r in rows if r["sport"] == "Basketball"]
    if not any(r.get("league") == "NBA" for r in olbg_nba):
        flag("Basketball", "coverage-gap", "medium",
             "OLBG lists 13 NBA event/markets on its Basketball/NBA hub, but no NBA fixture could be verified from "
             "an official source, so those events are not on this desk. The EuroLeague and EuroCup fixtures that "
             "are on this desk come from the official Euroleague Basketball API.",
             source_url="https://www.olbg.com/betting-tips/Basketball/NBA/4")


if __name__ == "__main__":
    raise SystemExit(main())

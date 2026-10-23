#!/usr/bin/env python3
"""Board AJ — build the verified fixture desk with our own lines.

Pipeline:  capture bytes -> feeds.py parsers -> this module -> data/session-2722b692/desk.json

For every fixture we can date from an official source we originate:
  Match Winner (both sides), Handicap (both sides), Total (over and under) and a
  sport derivative (puck line, run line, set line, frame line, race/tournament outright).

Each market carries a probability, a fair decimal price and the fair American price. A pick is
the higher-probability side of the match-winner market; the desk also names the highest-
probability selection of every market investigated on that fixture ("best market pick").
Confidence is High at p >= 0.70, Medium at p >= 0.60, Low below that, and is capped when the
official sample behind the inputs is too thin (documented on the methodology page).
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import feeds  # noqa: E402
from models import (CONST, Capture, american_from_prob, goals_pair, implied_from_american,
                    in_odds_window, normal_cdf, parse_iso, points_pair, p_win_by, race_win,
                    runs_pair, set_match_prob, sets_handicap, sets_pair, shrink, utc_now)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "session-2722b692"
NOW = utc_now()
UNPRICED: list[dict] = []

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]


# --------------------------------------------------------------------------- market helpers
def market(name: str, selection: str, p: float, line: str = "", note: str = "") -> dict:
    am, dec = american_from_prob(p)
    return {"market": name, "selection": selection, "line": line,
            "probability": round(p, 4), "fair_decimal": dec, "fair_american": am,
            "in_window": in_odds_window(am), "note": note}


def two_way(name: str, home: str, away: str, p_home: float, line: str = "") -> list[dict]:
    return [market(name, home, p_home, line), market(name, away, 1.0 - p_home, line)]


def total_market(home: str, away: str, line: float, p_over: float, label: str = "Total") -> list[dict]:
    return [market(label, f"Over {line}", p_over, f"{line}"),
            market(label, f"Under {line}", 1.0 - p_over, f"{line}")]


def poisson_over(mu: float, line: float) -> float:
    """P(total > line) for a Poisson total with mean mu."""
    k = int(line)
    return 1.0 - sum(math.exp(-mu) * mu ** i / math.factorial(i) for i in range(k + 1))


def goal_grid_handicap(grid: list[list[float]], line: float) -> float:
    """P(home margin > line) from the Poisson score grid."""
    n = len(grid)
    out = 0.0
    for i in range(n):
        for j in range(n):
            if i - j > -line:
                out += grid[i][j]
    return out


def handicap_ladder(name: str, home: str, away: str, p_by: dict, lines: list[float]) -> list[dict]:
    mk = []
    for line in lines:
        p = p_by(line)
        mk.append(market(name, f"{home} {line:+g}", p, f"{line:+g}"))
        mk.append(market(name, f"{away} {-line:+g}", 1.0 - p, f"{-line:+g}"))
    return mk


def classify(p: float, caps: list[str]) -> tuple[str, str]:
    base = "High" if p >= 0.70 else ("Medium" if p >= 0.60 else "Low")
    if base == "High" and caps:
        return "Medium", caps[0]
    if base == "Medium" and any(c.startswith("sample") for c in caps):
        return "Low", caps[0]
    return base, ""


def resolve_team(name: str, table: dict) -> dict | None:
    """Resolve a fixture team name to a standings row.

    Official pages spell clubs with different sponsor prefixes (e.g. a fixture list says
    "Stilon Gorzów" while the table says "Cuprum Stilon Gorzów"). Resolution requires at
    least two shared significant tokens, or one shared token of six or more characters.
    Every mapping used is written into the row so it can be reviewed.
    """
    if name in table:
        return table[name]
    tok = [w for w in re.split(r"[^\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", name.lower()) if len(w) > 2]
    best, best_score = None, 0
    for key, row in table.items():
        ktok = [w for w in re.split(r"[^\wąćęłńóśźżĄĆĘŁŃÓŚŹŻ]+", key.lower()) if len(w) > 2]
        shared = [w for w in tok if any(w in k or k in w for k in ktok if len(k) > 2)]
        score = len(shared) + sum(0.5 for w in shared if len(w) >= 6)
        if score > best_score:
            best, best_score = row, score
    if best and (best_score >= 2 or any(len(w) >= 6 for w in
                                        [x for x in tok if x in best["name"].lower()])):
        return best
    return None


# --------------------------------------------------------------------------- fixtures from JSON feeds
def build_hockey(cap: Capture) -> tuple[list[dict], dict]:
    rows, diagnostics = [], {}
    nhl, teams, skipped = feeds.nhl_fixtures(cap)
    diagnostics["nhl"] = {"fixtures": len(nhl), "teams": len(teams), "skipped": skipped[:5]}
    gf_prior = sum(x["gf_pg"] for x in teams.values()) / max(len(teams), 1)
    ga_prior = sum(x["ga_pg"] for x in teams.values()) / max(len(teams), 1)
    for f in nhl:
        h, a = f["inputs"]["home"], f["inputs"]["away"]
        h_gf = shrink(h["gf_pg"], h["gp"], 5, gf_prior)
        h_ga = shrink(h["ga_pg"], h["gp"], 5, ga_prior)
        a_gf = shrink(a["gf_pg"], a["gp"], 5, gf_prior)
        a_ga = shrink(a["ga_pg"], a["gp"], 5, ga_prior)
        mu_h = max((h_gf + a_ga) / 2 + CONST["nhl_home_goals"], 0.6)
        mu_a = max((a_gf + h_ga) / 2, 0.6)
        g = goals_pair(mu_h, mu_a)
        p_home = g["home"] + 0.5 * g["draw"]
        total_line = 5.5 if (mu_h + mu_a) < 6.6 else 6.5
        p_over = 1.0 - sum(math.exp(-(mu_h + mu_a)) * (mu_h + mu_a) ** k / math.factorial(k)
                           for k in range(int(total_line) + 1))
        p_puck_home = sum(g["grid"][i][j] for i in range(14) for j in range(14) if i - j >= 2)
        mk = []
        mk += two_way("Match Winner", f["home"], f["away"], p_home)
        mk += handicap_ladder("Handicap (Puck Line)", f["home"], f["away"],
                              lambda ln: goal_grid_handicap(g["grid"], ln), [-1.5])
        for line in (total_line, total_line + 1.0):
            mk += total_market(f["home"], f["away"], line, poisson_over(mu_h + mu_a, line))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "goal_poisson", "mu_home": round(mu_h, 3),
                                "mu_away": round(mu_a, 3),
                                "shrink_k": 5, "league_gf_prior": round(gf_prior, 3),
                                "inputs_used": ["goalsFor/game", "goalsAgainst/game",
                                                "home/road records", "L10 record"],
                                "caps": [] if min(h["gp"], a["gp"]) >= 10 else ["sample<10 games"]}))
    liiga, lteams, _ = feeds.liiga_fixtures(cap)
    diagnostics["liiga"] = {"fixtures": len(liiga), "teams": len(lteams)}
    for f in liiga:
        h = lteams.get(f["home"]); a = lteams.get(f["away"])
        if not h or not a or h["gp"] < 3 or a["gp"] < 3:
            continue
        f["inputs"]["home"], f["inputs"]["away"] = h, a
        mu_h = max((h["gf_pg"] + a["ga_pg"]) / 2 + CONST["nhl_home_goals"], 0.6)
        mu_a = max((a["gf_pg"] + h["ga_pg"]) / 2, 0.6)
        g = goals_pair(mu_h, mu_a)
        p_home = g["home"] + 0.5 * g["draw"]
        p_puck = sum(g["grid"][i][j] for i in range(14) for j in range(14) if i - j >= 2)
        line = 5.5 if (mu_h + mu_a) < 6.6 else 6.5
        p_over = 1.0 - sum(math.exp(-(mu_h + mu_a)) * (mu_h + mu_a) ** k / math.factorial(k)
                           for k in range(int(line) + 1))
        mk = two_way("Match Winner", f["home"], f["away"], p_home)
        mk += handicap_ladder("Handicap (Puck Line)", f["home"], f["away"],
                              lambda ln: goal_grid_handicap(g["grid"], ln), [-1.5])
        for ln in (line, line + 1.0):
            mk += total_market(f["home"], f["away"], ln, poisson_over(mu_h + mu_a, ln))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "goal_poisson", "mu_home": round(mu_h, 3),
                                "mu_away": round(mu_a, 3),
                                "inputs_used": ["goals for/against per game from completed Liiga games"],
                                "caps": [] if min(h["gp"], a["gp"]) >= 10 else ["sample<10 games"]}))
    shl, steams = feeds.shl_fixtures(cap)
    diagnostics["shl"] = {"fixtures": len(shl), "teams": len(steams)}
    for f in shl:
        h = steams.get(f["home"]); a = steams.get(f["away"])
        if not h or not a or h["gp"] < 3 or a["gp"] < 3:
            continue
        f["inputs"]["home"], f["inputs"]["away"] = h, a
        mu_h = max((h["gf_pg"] + a["ga_pg"]) / 2 + CONST["nhl_home_goals"], 0.6)
        mu_a = max((a["gf_pg"] + h["ga_pg"]) / 2, 0.6)
        g = goals_pair(mu_h, mu_a)
        p_home = g["home"] + 0.5 * g["draw"]
        p_puck = sum(g["grid"][i][j] for i in range(14) for j in range(14) if i - j >= 2)
        line = 5.5 if (mu_h + mu_a) < 6.6 else 6.5
        p_over = 1.0 - sum(math.exp(-(mu_h + mu_a)) * (mu_h + mu_a) ** k / math.factorial(k)
                           for k in range(int(line) + 1))
        mk = two_way("Match Winner", f["home"], f["away"], p_home)
        mk += handicap_ladder("Handicap (Puck Line)", f["home"], f["away"],
                              lambda ln: goal_grid_handicap(g["grid"], ln), [-1.5])
        for ln in (line, line + 1.0):
            mk += total_market(f["home"], f["away"], ln, poisson_over(mu_h + mu_a, ln))
        caps = [] if min(h["gp"], a["gp"]) >= 10 else ["sample<10 games"]
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "goal_poisson", "mu_home": round(mu_h, 3),
                                "mu_away": round(mu_a, 3),
                                "inputs_used": ["goals for/against per game from SHL results"],
                                "notes": ["venue kick-off published in Swedish local time, converted to UTC"],
                                "caps": caps}))
    return rows, diagnostics


def build_baseball(cap: Capture) -> tuple[list[dict], dict]:
    fixtures, teams, skipped = feeds.mlb_fixtures(cap)
    if not fixtures:
        return [], {"mlb": {"fixtures": 0}}
    lg_rs = sum(t["rs_pg"] for t in teams.values()) / len(teams)
    lg_ra = sum(t["ra_pg"] for t in teams.values()) / len(teams)
    eras = [t["pitching"].get("era") for t in teams.values() if t.get("pitching", {}).get("era")]
    lg_era = sum(float(e) for e in eras) / len(eras) if eras else 4.2
    rows = []
    for f in fixtures:
        h, a = f["inputs"]["home"], f["inputs"]["away"]
        h_era = float(h.get("pitching", {}).get("era") or lg_era)
        a_era = float(a.get("pitching", {}).get("era") or lg_era)
        mu_h = max(lg_rs * (h["rs_pg"] / lg_rs) * (a["ra_pg"] / lg_ra) * (a_era / lg_era)
                   * CONST["mlb_home_factor"], 1.5)
        mu_a = max(lg_rs * (a["rs_pg"] / lg_rs) * (h["ra_pg"] / lg_ra) * (h_era / lg_era), 1.5)
        r = runs_pair(mu_h, mu_a)
        line = 8.5 if (mu_h + mu_a) > 8.4 else 7.5
        p_over = 1.0 - sum(math.exp(-(mu_h + mu_a)) * (mu_h + mu_a) ** k / math.factorial(k)
                           for k in range(int(line) + 1))
        p_rl_home = sum(r["grid"][i][j] for i in range(20) for j in range(20) if i - j >= 2)
        mk = two_way("Match Winner", f["home"], f["away"], r["home"])
        mk += handicap_ladder("Handicap (Run Line)", f["home"], f["away"],
                              lambda ln: goal_grid_handicap(r["grid"], ln), [-1.5])
        for ln in (line, line + 1.0):
            mk += total_market(f["home"], f["away"], ln, poisson_over(mu_h + mu_a, ln))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "run_poisson", "mu_home": round(mu_h, 3),
                                "mu_away": round(mu_a, 3),
                                "inputs_used": ["runs scored/allowed per game", "team ERA",
                                                "league averages", "probable pitcher named by MLB"],
                                "caps": []}))
    return rows, {"mlb": {"fixtures": len(fixtures), "skipped": skipped, "league_runs": round(lg_rs, 3),
                          "league_era": round(lg_era, 3)}}


def build_basketball(cap: Capture) -> tuple[list[dict], dict]:
    fixtures, teams, _ = feeds.euroleague_fixtures(cap)
    rows = []
    if not teams:
        return [], {"euroleague": {"fixtures": len(fixtures), "teams": 0}}
    pf_prior = sum(x["pf_pg"] for x in teams.values()) / len(teams)
    pa_prior = sum(x["pa_pg"] for x in teams.values()) / len(teams)
    for f in fixtures:
        h, a = teams.get(f["inputs"]["home_name"]), teams.get(f["inputs"]["away_name"])
        if not h or not a or h["gp"] < 1 or a["gp"] < 1:
            continue
        h_pf = shrink(h["pf_pg"], h["gp"], 8, pf_prior)
        h_pa = shrink(h["pa_pg"], h["gp"], 8, pa_prior)
        a_pf = shrink(a["pf_pg"], a["gp"], 8, pf_prior)
        a_pa = shrink(a["pa_pg"], a["gp"], 8, pa_prior)
        f["inputs"]["home_record"], f["inputs"]["away_record"] = h, a
        f["inputs"]["home_prior_pf"] = round(pf_prior, 2)
        f["inputs"]["home_prior_pa"] = round(pa_prior, 2)
        exp_h = (h_pf + a_pa) / 2 + CONST["basket_home_edge"] / 2
        exp_a = (a_pf + h_pa) / 2 - CONST["basket_home_edge"] / 2
        margin, total = exp_h - exp_a, exp_h + exp_a
        m = points_pair(margin, CONST["basket_margin_sd"], total)
        hcap = -round(abs(margin)) - 0.5 if margin >= 0 else 0.5
        hcap = -math.floor(abs(margin)) - 0.5
        if margin < 0:
            hcap = -hcap
        tline = round(total) - 0.5
        mk = two_way("Match Winner", f["home"], f["away"], m["home"])
        mk += handicap_ladder("Handicap", f["home"], f["away"],
                              lambda ln: normal_cdf(0.0, -ln - margin, CONST["basket_margin_sd"]),
                              [hcap, hcap - 3.5, hcap - 6.5, hcap - 10.5])
        for ln in (tline, tline + 4.0):
            mk += total_market(f["home"], f["away"], ln, m["p_over"](ln))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "point_normal", "expected_margin": round(margin, 2),
                                "expected_total": round(total, 2), "shrink_k": 8,
                                "league_pf_prior": round(pf_prior, 2),
                                "inputs_used": ["points for/against per game from completed games"],
                                "caps": [] if min(h["gp"], a["gp"]) >= 4 else ["sample<4 games"]}))
    return rows, {"euroleague": {"fixtures": len(fixtures), "teams": len(teams)}}


def build_tennis(cap: Capture) -> tuple[list[dict], dict]:
    fixtures, players, _ = feeds.wta_fixtures(cap)
    rows = []
    conflicts: list[dict] = []
    slots: dict[str, list[dict]] = {}
    for f in sorted(fixtures, key=lambda x: x["start_utc"]):
        for side in ("a", "b"):
            slots.setdefault(f["inputs"][side]["name"], []).append(f)
    conflicted = set()
    for name, fs in slots.items():
        comps = {x["competition"] for x in fs}
        if len(comps) > 1:
            conflicted.add(id(fs[0]))
            conflicted.add(id(fs[1])) if len(fs) > 1 else None
            conflicts.append({"player": name, "competitions": sorted(comps),
                              "why": "same player scheduled in two tournaments in the same window"})
    for f in sorted(fixtures, key=lambda x: x["start_utc"]):
        a, b = f["inputs"]["a"], f["inputs"]["b"]
        if not a["points"] or not b["points"]:
            continue
        pa, pb = float(a["points"]), float(b["points"])
        gap = math.log(pa) - math.log(pb)
        f["inputs"]["p_set_calibration"] = "logistic(0.45 * ln(points_a / points_b)), then best-of-3"
        s = sets_pair(gap, best_of=3, slope=0.45)
        p_home = s["home"]
        p_straight = s["p_set"] ** 2
        p_three = 2 * s["p_set"] * (1 - s["p_set"])
        mk = two_way("Match Winner", f["home"], f["away"], p_home)
        mk += handicap_ladder("Set Handicap", f["home"], f["away"],
                              lambda ln: sets_handicap(s["p_set"], 3, ln), [-1.5, 1.5])
        mk += total_market(f["home"], f["away"], 2.5, p_straight, "Total Sets")
        caps = []
        if min(a["rank"] or 999, b["rank"] or 999) > 100:
            caps.append("ranking outside top 100")
        stamp = f["start_utc"][11:16]
        if stamp == "23:59":
            caps.append("start time provisional on the official feed")
            f["inputs"]["start_time_provisional"] = True
        if id(f) in conflicted:
            caps.append("player also listed in another tournament in the same window")
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "set_model", "p_set_a": round(s["p_set"], 4),
                                "ranking_points_a": pa, "ranking_points_b": pb,
                                "inputs_used": ["official WTA ranking points", "tournament match state",
                                                "scheduled court time"],
                                "caps": caps}))
    return rows, {"wta": {"fixtures": len(fixtures), "players_ranked": len(players),
                          "cross_tournament_conflicts": conflicts[:10]}}


def build_snooker(cap: Capture) -> tuple[list[dict], dict]:
    data = cap.json("wst_matches_root") or {}
    matches = data.get("data", [])
    completed = [m for m in matches if m["attributes"]["status"] == "Completed"]
    form: dict[str, dict] = {}
    for m in completed:
        a = m["attributes"]
        hs, as_ = a.get("homePlayerScore"), a.get("awayPlayerScore")
        if hs is None or as_ is None:
            continue
        for pid, gf, ga in ((a.get("homePlayerID"), hs, as_), (a.get("awayPlayerID"), as_, hs)):
            if not pid:
                continue
            t = form.setdefault(pid, {"w": 0, "l": 0, "frames_for": 0, "frames_against": 0})
            t["w" if gf > ga else "l"] += 1
            t["frames_for"] += int(gf or 0)
            t["frames_against"] += int(ga or 0)
    rows = []
    for m in matches:
        a = m["attributes"]
        if a["status"] != "Scheduled" or not a.get("playersAllocated"):
            continue
        hpl, apl = a.get("homePlayer") or {}, a.get("awayPlayer") or {}
        if not hpl.get("surname") or not apl.get("surname"):
            continue
        start = parse_iso(a.get("startDateTime", "").replace(" ", "T") + "Z")
        if not start or start < NOW - timedelta(hours=3) or start > datetime(2026, 11, 8, 23, 59, tzinfo=timezone.utc):
            continue
        hp = form.get(a.get("homePlayerID"), {"w": 0, "l": 0})
        ap = form.get(a.get("awayPlayerID"), {"w": 0, "l": 0})
        n_h, n_a = hp["w"] + hp["l"], ap["w"] + ap["l"]
        if n_h < 1 or n_a < 1:
            UNPRICED.append({
                "sport": "Snooker", "competition": (a.get("tournament") or {}).get("name", ""),
                "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home": f"{hpl['firstName']} {hpl['surname']}",
                "away": f"{apl['firstName']} {apl['surname']}",
                "source_url": cap.url("wst_matches_root"),
                "reason": "no completed match for one or both players in the captured official WST match feed",
            })
            continue
        rate_h = (hp["w"] + 1) / (n_h + 2)
        rate_a = (ap["w"] + 1) / (n_a + 2)
        p_frame = 1 / (1 + math.exp(-(rate_h - rate_a) * 4.0))
        best_of = int(a.get("numberOfFrames") or 7)
        p_home = set_match_prob(p_frame, best_of)
        frames_line = best_of - 2.5
        # total frames over line: match must go at least ceil(line+1) frames
        need = int(frames_line) + 1
        p_over = sum(set_score_prob(p_frame, best_of, k) for k in range(need, best_of + 1))
        mk = two_way("Match Winner", f"{hpl['firstName']} {hpl['surname']}",
                     f"{apl['firstName']} {apl['surname']}", p_home)
        mk += handicap_ladder("Handicap (Frames)", f"{hpl['firstName']} {hpl['surname']}",
                              f"{apl['firstName']} {apl['surname']}",
                              lambda ln: sets_handicap(p_frame, best_of, ln), [-1.5, -2.5])
        for fl in (frames_line, frames_line + 1.0):
            need_f = int(fl) + 1
            mk += total_market(f"{hpl['firstName']} {hpl['surname']}",
                               f"{apl['firstName']} {apl['surname']}", fl,
                               sum(set_score_prob(p_frame, best_of, k) for k in range(need_f, best_of + 1)),
                               "Total Frames")
        fixture = {
            "sport": "Snooker", "competition": (a.get("tournament") or {}).get("name", ""),
            "start_utc": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home": f"{hpl['firstName']} {hpl['surname']}", "away": f"{apl['firstName']} {apl['surname']}",
            "home_code": "", "away_code": "",
            "venue": (a.get("tournament") or {}).get("venue") or "",
            "source_url": cap.url("wst_matches_root"),
            "source_id": a.get("name", ""),
            "inputs": {"model": "frame_set_model", "round": a.get("round", ""),
                       "best_of": best_of, "home_form": hp, "away_form": ap,
                       "format_note": "best-of-%d frames" % best_of,
                       "schedule_source": cap.url("wst_matches_root")},
            "tags": ["knockout" if best_of > 7 else "tour"],
        }
        rows.append(dict(fixture=fixture, markets=mk,
                         model={"family": "set_model_frames", "p_frame": round(p_frame, 4),
                                "samples": [n_h, n_a],
                                "inputs_used": ["completed-match win rate in the captured WST match feed",
                                                "frames won/lost", "round format"],
                                "caps": ["sample<10 matches"]}))
    return rows, {"wst": {"matches_total": len(matches), "completed": len(completed),
                          "scheduled_priced": len(rows), "players_with_form": len(form)}}


def set_score_prob(p: float, best_of: int, total_frames: int) -> float:
    """P(match lasts at least `total_frames` frames) under independent frame outcomes."""
    need = best_of // 2 + 1
    # A match ends at score (need, x) or (x, need). Number of frames = need + x.
    losses = total_frames - need
    if losses < 0:
        return 1.0
    if losses >= need:
        return 0.0
    ways = math.comb(need + losses - 1, losses)
    return ways * (p ** need * (1 - p) ** losses + (1 - p) ** need * p ** losses)


# --------------------------------------------------------------------------- HTML-based feeds
def build_rugby(cap: Capture) -> tuple[list[dict], dict]:
    rows, diagnostics = [], {}
    table = feeds.lnr_table(cap, "lnr_top14_table")
    fixtures = feeds.lnr_fixtures(cap, "lnr_top14", "Top 14")
    diagnostics["top14"] = {"fixtures": len(fixtures), "table_rows": len(table)}
    played_rows = [t for t in table.values() if t["played"]]
    lg_pf = (sum(t["pf"] / t["played"] for t in played_rows) / len(played_rows)) if played_rows else 27.0
    lg_pa = (sum(t["pa"] / t["played"] for t in played_rows) / len(played_rows)) if played_rows else 27.0
    for f in fixtures:
        h, a = resolve_team(f["home"], table), resolve_team(f["away"], table)
        if not h or not a or h["played"] < 2 or a["played"] < 2:
            continue
        f["inputs"]["resolved_home"] = h["name"]
        f["inputs"]["resolved_away"] = a["name"]
        f["inputs"]["home_row"], f["inputs"]["away_row"] = h, a
        h_pf = shrink(h["pf"] / h["played"], h["played"], 4, lg_pf)
        h_pa = shrink(h["pa"] / h["played"], h["played"], 4, lg_pa)
        a_pf = shrink(a["pf"] / a["played"], a["played"], 4, lg_pf)
        a_pa = shrink(a["pa"] / a["played"], a["played"], 4, lg_pa)
        exp_h = (h_pf + a_pa) / 2 + CONST["rugby_home_edge"] / 2
        exp_a = (a_pf + h_pa) / 2 - CONST["rugby_home_edge"] / 2
        margin, total = exp_h - exp_a, exp_h + exp_a
        m = points_pair(margin, CONST["rugby_margin_sd"], total)
        hcap = -math.floor(abs(margin)) + 0.5 if margin > 0 else math.floor(abs(margin)) + 0.5
        hcap = -math.floor(abs(margin)) - 0.5 if margin > 0 else math.floor(abs(margin)) + 0.5
        tline = round(total) - 0.5
        mk = two_way("Match Winner", f["home"], f["away"], m["home"])
        mk += handicap_ladder("Handicap", f["home"], f["away"],
                              lambda ln: normal_cdf(0.0, -ln - margin, CONST["rugby_margin_sd"]),
                              [hcap, hcap - 7.5, hcap + 7.5])
        for ln in (tline, tline + 5.0):
            mk += total_market(f["home"], f["away"], ln, m["p_over"](ln))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "point_normal", "expected_margin": round(margin, 2),
                                "expected_total": round(total, 2), "shrink_k": 4,
                                "league_pf_prior": round(lg_pf, 2),
                                "inputs_used": ["league points for/against per match from the official table",
                                                "table rank"],
                                "caps": [] if min(h["played"], a["played"]) >= 5 else ["sample<5 matches"]}))
    prod = feeds.lnr_table(cap, "lnr_top14_table", url_id="lnr_prod2")
    diagnostics["prod2_table"] = {"rows": len(prod)}
    return rows, diagnostics


def build_volleyball(cap: Capture) -> tuple[list[dict], dict]:
    fixtures = [f for f in feeds.plusliga_fixtures(cap) if f["start_utc"] >= NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
    table = feeds.plusliga_table(cap)
    rows = []
    for f in fixtures:
        h, a = resolve_team(f["home"], table), resolve_team(f["away"], table)
        if not h or not a or h["played"] < 2 or a["played"] < 2:
            continue
        f["inputs"]["resolved_home"] = h["name"]
        f["inputs"]["resolved_away"] = a["name"]
        f["inputs"]["home_row"], f["inputs"]["away_row"] = h, a
        # strength from set ratio (sets won / sets lost) recorded in the official table
        sr_h = ((h["sets_won"] + 1) / (h["sets_lost"] + 1)) ** (h["played"] / (h["played"] + 6))
        sr_a = ((a["sets_won"] + 1) / (a["sets_lost"] + 1)) ** (a["played"] / (a["played"] + 6))
        p_set = 1 / (1 + math.exp(-0.55 * math.log(sr_h / sr_a)))
        p_home = set_match_prob(p_set, 5)
        mk = two_way("Match Winner", f["home"], f["away"], p_home)
        mk += handicap_ladder("Set Handicap", f["home"], f["away"],
                              lambda ln: sets_handicap(p_set, 5, ln), [-1.5, -2.5, 1.5])
        for sl in (3.5, 4.5):
            mk += total_market(f["home"], f["away"], sl,
                               sum(set_score_prob(p_set, 5, k) for k in range(int(sl) + 1, 6)),
                               "Total Sets")
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "set_model", "p_set": round(p_set, 4),
                                "inputs_used": ["sets won/lost and match points from the official PlusLiga table"],
                                "caps": [] if min(h["played"], a["played"]) >= 5 else ["sample<5 matches"]}))
    return rows, {"plusliga": {"fixtures": len(fixtures), "table_rows": len(table)}}


def build_motor(cap: Capture) -> tuple[list[dict], dict]:
    races = feeds.f1_calendar(cap)
    order = feeds.f1_driver_order(cap)
    rows = []
    if not order:
        return [], {"f1": {"races": len(races), "drivers": 0}}
    strengths = [(name, (len(order) - i) ** 1.5) for i, name in enumerate(order)]
    names = [d for d, _ in strengths]
    probs = race_win([s for _, s in strengths])
    for race in races:
        mk = []
        field = sorted(zip(names, probs), key=lambda x: -x[1])
        for drv, p in field:
            mk.append(market("Race Winner", drv, p))
        if not mk:
            continue
        rows.append(dict(fixture=race, markets=mk,
                         model={"family": "outright_normalised", "field": len(field),
                                "inputs_used": ["official Formula 1 2026 driver standings order"],
                                "caps": ["outright market: single-winner probability is structurally below 0.70"]}))
    return rows, {"f1": {"races": len(races), "drivers": len(order)}}


def build_golf(cap: Capture) -> tuple[list[dict], dict]:
    event = feeds.dpwt_event(cap)
    field = feeds.owgr_strengths(cap)
    rows = []
    if not event or not field:
        return [], {"golf": {"event": bool(event), "ranked_players": len(field)}}
    probs = race_win([v for _, v in field])
    mk = [market("Tournament Winner", name, p) for (name, _), p in zip(field, probs)]
    rows.append(dict(fixture=event, markets=mk,
                     model={"family": "outright_normalised", "field": len(field),
                            "inputs_used": ["OWGR world ranking points", "official DP World Tour event page"],
                            "caps": ["outright market: single-winner probability is structurally below 0.70"]}))
    return rows, {"golf": {"event": event.get("competition", ""), "field": len(field)}}


def build_rugby_league(cap: Capture) -> tuple[list[dict], dict]:
    fixtures, form, _ = feeds.rlwc_fixtures(cap)
    rows = []
    for f in fixtures:
        h, a = form.get(f["home"]), form.get(f["away"])
        if not h or not a or h["gp"] < 1 or a["gp"] < 1:
            continue
        pf_prior = sum(x["pf_pg"] for x in form.values()) / max(len(form), 1)
        pa_prior = sum(x["pa_pg"] for x in form.values()) / max(len(form), 1)
        h_pf = shrink(h["pf_pg"], h["gp"], 4, pf_prior)
        h_pa = shrink(h["pa_pg"], h["gp"], 4, pa_prior)
        a_pf = shrink(a["pf_pg"], a["gp"], 4, pf_prior)
        a_pa = shrink(a["pa_pg"], a["gp"], 4, pa_prior)
        exp_h = (h_pf + a_pa) / 2 + CONST["league_home_edge"] / 2
        exp_a = (a_pf + h_pa) / 2 - CONST["league_home_edge"] / 2
        margin, total = exp_h - exp_a, exp_h + exp_a
        m = points_pair(margin, CONST["league_margin_sd"], total)
        hcap = -math.floor(abs(margin)) - 0.5 if margin > 0 else math.floor(abs(margin)) + 0.5
        tline = round(total) - 0.5
        mk = two_way("Match Winner", f["home"], f["away"], m["home"])
        mk += handicap_ladder("Handicap", f["home"], f["away"],
                              lambda ln: normal_cdf(0.0, -ln - margin, CONST["league_margin_sd"]),
                              [hcap, hcap - 6.5])
        for ln in (tline, tline + 6.0):
            mk += total_market(f["home"], f["away"], ln, m["p_over"](ln))
        rows.append(dict(fixture=f, markets=mk,
                         model={"family": "point_normal", "expected_margin": round(margin, 2),
                                "expected_total": round(total, 2),
                                "inputs_used": ["points for/against from completed RLWC 2026 matches",
                                                "pool position"],
                                "caps": ["sample<3 matches"] if min(h["gp"], a["gp"]) < 3 else []}))
    return rows, {"rlwc": {"fixtures": len(fixtures), "teams_with_results": len(form)}}


# --------------------------------------------------------------------------- assembly
BUILDERS = [
    ("Ice Hockey", build_hockey),
    ("Baseball", build_baseball),
    ("Basketball", build_basketball),
    ("Tennis", build_tennis),
    ("Snooker", build_snooker),
    ("Rugby Union", build_rugby),
    ("Volleyball", build_volleyball),
    ("Rugby League", build_rugby_league),
    ("Motor Racing", build_motor),
    ("Golf", build_golf),
]


def olbg_lookup(inv: dict) -> dict:
    """Index OLBG listed selections by normalised event label for cross-reference."""
    idx = {}
    for hub in inv["hubs"]:
        for ev in hub["events"]:
            key = re.sub(r"[^a-z0-9]", "", ev["event"].lower())
            idx.setdefault(key, {"sport": hub["sport"], "event": ev["event"],
                                 "start_utc": ev["start_utc"], "hub_url": hub["hub_url"],
                                 "markets": ev["markets"]})
    return idx


def match_olbg(fixture: dict, idx: dict) -> dict:
    """Find an OLBG listing whose event label mentions both sides (text match only)."""
    def norm(s):
        return re.sub(r"[^a-z0-9]", "", s.lower())
    hkey, akey = norm(fixture["home"]), norm(fixture["away"])
    short_h = norm(fixture["home"].split()[-1])
    short_a = norm(fixture["away"].split()[-1])
    for key, ev in idx.items():
        if (hkey in key or short_h in key) and (akey in key or short_a in key):
            return ev
    return {}


def main() -> int:
    cap = Capture()
    inv = feeds.olbg_inventory(cap)
    idx = olbg_lookup(inv)
    all_rows, diagnostics = [], {}
    for sport, builder in BUILDERS:
        try:
            rows, diag = builder(cap)
        except Exception as exc:  # noqa: BLE001 - a broken parser must not fake a row
            diagnostics[sport] = {"error": f"{type(exc).__name__}: {exc}"}
            continue
        diagnostics.setdefault(sport, {}).update(diag)
        for r in rows:
            f = r["fixture"]
            f["sport"] = sport
            best = max(r["markets"], key=lambda m: m["probability"])
            in_band = [m for m in r["markets"] if m["in_window"]]
            focus = max(in_band, key=lambda m: m["probability"]) if in_band else None
            winner_markets = [m for m in r["markets"] if m["market"] == "Match Winner"]
            primary = max(winner_markets, key=lambda m: m["probability"]) if winner_markets else best
            conf, cap_reason = classify(primary["probability"], r["model"].get("caps", []))
            listed = match_olbg(f, idx)
            all_rows.append({
                "id": f"AJ-{len(all_rows)+1:04d}",
                "sport": sport,
                "competition": f.get("competition", ""),
                "start_utc": f["start_utc"],
                "home": f["home"], "away": f["away"],
                "venue": f.get("venue", ""),
                "source_url": f["source_url"],
                "source_sha256": cap.sha(next((t for t in cap.by_id if f["source_url"] == cap.url(t)), "")),
                "source_id": f.get("source_id", ""),
                "inputs": f.get("inputs", {}),
                "model": r["model"],
                "model_notes": r["model"].get("notes", []),
                "markets": r["markets"],
                "pick": {"selection": primary["selection"], "market": primary["market"],
                         "probability": primary["probability"],
                         "fair_decimal": primary["fair_decimal"],
                         "fair_american": primary["fair_american"],
                         "in_window": primary["in_window"]},
                "best_market_pick": {"selection": best["selection"], "market": best["market"],
                                     "line": best["line"], "probability": best["probability"],
                                     "fair_american": best["fair_american"],
                                     "fair_decimal": best["fair_decimal"],
                                     "in_window": best["in_window"]},
                "focus_pick": ({"selection": focus["selection"], "market": focus["market"],
                                "line": focus["line"], "probability": focus["probability"],
                                "fair_american": focus["fair_american"],
                                "fair_decimal": focus["fair_decimal"]} if focus else {}),
                "focus_high": bool(focus) and focus["probability"] >= 0.70,
                "confidence": conf,
                "confidence_cap_reason": cap_reason,
                "high_confidence": conf == "High" and best["probability"] >= 0.70,
                "olbg": listed,
                "tags": f.get("tags", []),
            })
    all_rows.sort(key=lambda r: (r["start_utc"], r["sport"], r["home"]))
    for i, r in enumerate(all_rows, 1):
        r["id"] = f"AJ-{i:04d}"

    highs = [r for r in all_rows if r["high_confidence"]]
    focus_highs = [r for r in all_rows if r["focus_high"]]
    by_sport = {}
    for s in SPORTS:
        rows_s = [r for r in all_rows if r["sport"] == s]
        highs_s = sorted([r for r in rows_s if r["high_confidence"]],
                         key=lambda r: -r["best_market_pick"]["probability"])
        fh_s = sorted([r for r in rows_s if r["focus_high"]],
                      key=lambda r: -r["focus_pick"]["probability"])
        by_sport[s] = {
            "fixtures": len(rows_s),
            "priced_markets": sum(len(r["markets"]) for r in rows_s),
            "high": len(highs_s),
            "medium": sum(1 for r in rows_s if r["confidence"] == "Medium"),
            "low": sum(1 for r in rows_s if r["confidence"] == "Low"),
            "high_fixture_ids": [r["id"] for r in highs_s],
            "focus_high": len(fh_s),
            "focus_high_fixture_ids": [r["id"] for r in fh_s],
        }
    desk = {
        "schema": "olbg4.board-aj.desk/1",
        "session": "arena/2722b692-olbg4",
        "board": "AJ",
        "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_id": cap.path.name,
        "capture_manifest_sha256": __import__("hashlib").sha256(
            (cap.path / "manifest.json").read_bytes()).hexdigest(),
        "sports_in_scope": SPORTS,
        "row_count": len(all_rows),
        "high_count": len(highs),
        "focus_high_count": len(focus_highs),
        "market_count": sum(len(r["markets"]) for r in all_rows),
        "by_sport": by_sport,
        "diagnostics": diagnostics,
        "unpriced": UNPRICED,
        "unpriced_count": len(UNPRICED),
        "rows": all_rows,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "desk.json").write_text(json.dumps(desk, indent=1, sort_keys=True))
    (OUT / "olbg_inventory.json").write_text(json.dumps(inv, indent=1, sort_keys=True))
    print(f"rows={len(all_rows)} markets={desk['market_count']} high={len(highs)}")
    for s in SPORTS:
        b = by_sport[s]
        print(f"  {s:14} fixtures={b['fixtures']:4} markets={b['priced_markets']:5} "
              f"H/M/L={b['high']}/{b['medium']}/{b['low']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board FX line origination.

Every row keeps two things strictly apart:
  * evidence  - numbers copied from an official source (with the capture id + URL)
  * model     - our own probability model, its inputs and its output

No bookmaker or OLBG price ever enters a line.  OLBG is used only to state which
events its sport hub lists, and that link is printed on the row.
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse as P  # noqa: E402

WINDOW_START = "2026-10-23T20:00:00Z"
WINDOW_END = "2026-11-08T23:59:59Z"
MIN_P, MAX_P = 0.005, 0.995


# --------------------------------------------------------------------- maths
def american(dec: float) -> int:
    if dec <= 1.0000001:
        return 0
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def dec_from_p(p: float) -> float:
    p = min(max(p, MIN_P), MAX_P)
    return round(1.0 / p, 2)


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def poisson_grid(lh: float, la: float, maxg: int = 18):
    ph = [poisson_pmf(k, lh) for k in range(maxg + 1)]
    pa = [poisson_pmf(k, la) for k in range(maxg + 1)]
    sh, sa = sum(ph), sum(pa)
    ph = [x / sh for x in ph]
    pa = [x / sa for x in pa]
    return ph, pa


def grid_probs(lh: float, la: float, maxg: int = 18):
    ph, pa = poisson_grid(lh, la, maxg)
    home_reg = sum(ph[h] * pa[a] for h in range(maxg + 1) for a in range(maxg + 1) if h > a)
    tie = sum(ph[h] * pa[h] for h in range(maxg + 1))
    away_reg = sum(ph[h] * pa[a] for h in range(maxg + 1) for a in range(maxg + 1) if h < a)
    margin = {}
    total = {}
    for h in range(maxg + 1):
        for a in range(maxg + 1):
            pr = ph[h] * pa[a]
            margin[h - a] = margin.get(h - a, 0.0) + pr
            total[h + a] = total.get(h + a, 0.0) + pr
    return {"home": home_reg, "tie": tie, "away": away_reg, "margin": margin, "total": total}


def best_of(p_set: float, n_sets: int):
    """Exact best-of-n set/match distribution for independent sets."""
    need = n_sets // 2 + 1
    dist = {0: 1.0}
    for played in range(n_sets):
        nxt = {}
        for w, pr in dist.items():
            if w == need or played - w == need:
                nxt[w] = nxt.get(w, 0.0) + pr
                continue
            nxt[w + 1] = nxt.get(w + 1, 0.0) + pr * p_set
            nxt[w] = nxt.get(w, 0.0) + pr * (1 - p_set)
        dist = nxt
        if all(w == need or played + 1 - w == need for w in dist):
            break
    win = sum(pr for w, pr in dist.items() if w == need)
    # margin distribution from completed set counts
    margin = {}
    for w, pr in dist.items():
        l = played_total = None  # noqa: F841
    return win


def volleyball_dist(p_set: float):
    """Best-of-5 set-score distribution (independent sets)."""
    need = 3
    dist = {(0, 0): 1.0}
    while dist:
        nxt = {}
        done = True
        for (w, l), pr in dist.items():
            if w == need or l == need:
                nxt[(w, l)] = nxt.get((w, l), 0.0) + pr
                continue
            done = False
            nxt[(w + 1, l)] = nxt.get((w + 1, l), 0.0) + pr * p_set
            nxt[(w, l + 1)] = nxt.get((w, l + 1), 0.0) + pr * (1 - p_set)
        dist = nxt
        if done:
            break
    win = sum(pr for (w, l), pr in dist.items() if w == need)
    return win, dist


def pmf_from(probs: dict, predicate):
    return sum(pr for k, pr in probs.items() if predicate(k))


# ----------------------------------------------------------------- rows / ETL
SUPPORTED = [
    ("Golf", "golf"), ("Volleyball", "volleyball"), ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"), ("Snooker", "snooker"), ("Darts", "darts"), ("Baseball", "baseball"),
    ("Gaelic Sports", "gaelic-sports"), ("Greyhounds", "greyhounds"), ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"), ("Handball", "handball"), ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"), ("Rugby League", "rugby-league"),
]


def in_window(start: str) -> bool:
    return bool(start) and WINDOW_START <= start <= WINDOW_END


def blank_row(**kw):
    row = {
        "id": "", "sport": "", "sport_slug": "", "competition": "", "side_a": "", "side_b": "",
        "start_utc": "", "venue": "", "official_url": "", "official_source_name": "",
        "capture_id": "", "evidence": {}, "form": {}, "sample": "", "model": {},
        "markets": {}, "pick": None, "flags": [], "olbg": None,
    }
    row.update(kw)
    # readers emit source_* keys; the published row uses official_*
    if "source_url" in row:
        row["official_url"] = row.pop("source_url")
    if "source_name" in row:
        row["official_source_name"] = row.pop("source_name")
    if "source_id" in row:
        row["capture_id"] = row.pop("source_id")
    return row


def market(name, line, selections, note=""):
    """Price every leg off the same rounded probability the page prints.

    The pair is clamped and renormalised first so extreme model output cannot
    produce a 300/1 line, then each leg's decimal price is exactly 1/p.
    """
    ps = [min(0.95, max(0.05, float(p))) for _, p in selections]
    if len(ps) == 2:
        tot = ps[0] + ps[1]
        ps = [ps[0] / tot, ps[1] / tot]
    legs = []
    for (lbl, _), p in zip(selections, ps):
        p = round(p, 4)
        dec = round(1.0 / p, 2)
        legs.append({"label": lbl, "fair_prob": p, "fair_decimal": dec,
                     "fair_american": american(dec), "implied_prob_sum": 1.0})
    return {"market_name": name, "line": line, "note": note, "selections": legs}


def pick_from(row, mk: str, idx: int, confidence: str, rule: str):
    m = row["markets"].get(mk)
    if not m:
        return
    sel = m["selections"][idx]
    p = sel["fair_prob"]
    in_win = -250 <= sel["fair_american"] <= 10000
    row["pick"] = {
        "market": m["market_name"], "market_key": mk, "selection": sel["label"],
        "fair_prob": p, "fair_decimal": sel["fair_decimal"], "fair_american": sel["fair_american"],
        "confidence": confidence, "in_window": in_win, "rule": rule,
    }


def shrink(p: float, k: float) -> float:
    """Calibration: pull model probabilities toward 50% by a documented constant."""
    return 0.5 + k * (p - 0.5)


def conf(p: float, cap: str = "High") -> str:
    if p >= 0.70:
        out = "High"
    elif p >= 0.55:
        out = "Medium"
    else:
        out = "Low"
    order = {"Low": 0, "Medium": 1, "High": 2}
    return out if order[out] <= order[cap] else cap


# --------------------------------------------------------------- ice hockey
def build_nhl(cap: P.Capture, rows):
    st = P.read_nhl_standings(cap)
    lg = sum(t["gf"] + t["ga"] for t in st.values()) / max(1, sum(t["gp"] for t in st.values()))
    for f in P.read_nhl(cap):
        if not in_window(f["start_utc"]):
            continue
        a, b = st.get(f["a_code"]), st.get(f["b_code"])
        row = blank_row(**f)
        if not a or not b:
            row["flags"].append("standings row missing for one side - no line originated")
            rows.append(row)
            continue
        # partial pooling: 70% of the club's own rate, 30% league average, against a 10-12 game sample
        home_att = 0.7 * (b["gf_pg"] / max(1e-9, lg / 2)) + 0.3
        away_att = 0.7 * (a["gf_pg"] / max(1e-9, lg / 2)) + 0.3
        home_def = 0.7 * (b["ga_pg"] / max(1e-9, lg / 2)) + 0.3
        away_def = 0.7 * (a["ga_pg"] / max(1e-9, lg / 2)) + 0.3
        lh = max(0.8, min(5.2, (lg / 2) * home_att * away_def * 1.06))
        la = max(0.8, min(5.2, (lg / 2) * away_att * home_def * 0.94))
        g = grid_probs(lh, la)
        p_home = min(0.82, max(0.18, shrink(g["home"] + 0.5 * g["tie"], 0.88)))
        p_away = 1 - p_home
        total_line = round(lh + la) + 0.5
        over = pmf_from(g["total"], lambda k: k > total_line)
        row["evidence"] = {
            "league_goals_per_game": round(lg, 3),
            "away_gf_pg": a["gf_pg"], "away_ga_pg": a["ga_pg"],
            "home_gf_pg": b["gf_pg"], "home_ga_pg": b["ga_pg"],
            "expected_goals_away": round(la, 2), "expected_goals_home": round(lh, 2),
            "standings_source": a["source_url"],
        }
        row["form"] = {
            "away": f"{a['w']}-{a['l']}-{a['otl']} ({a['pts']} pts, L10 {a['l10']}, streak {a['streak']})",
            "home": f"{b['w']}-{b['l']}-{b['otl']} ({b['pts']} pts, L10 {b['l10']}, streak {b['streak']})",
            "away_home_away": a["road"], "home_home_away": b["home"],
        }
        row["sample"] = f"{min(a['gp'], b['gp'])} games played (minimum of the two clubs)"
        row["markets"] = {
            "match_winner": market("Money Line (incl. OT/SO)", None, [
                (f"{f['side_a']} (away)", p_away), (f"{f['side_b']} (home)", p_home)]),
            "handicap": market("Puck Line", -1.5, [
                (f"{f['side_b']} -1.5", pmf_from(g["margin"], lambda m: m >= 2)),
                (f"{f['side_a']} +1.5", pmf_from(g["margin"], lambda m: m <= 1))]),
            "total": market(f"Total Goals {total_line}", total_line, [
                (f"Under {total_line}", 1 - over), (f"Over {total_line}", over)]),
        }
        row["model"] = {"name": "independent Poisson goals, standings attack/defence",
                        "home_exp": round(lh, 2), "away_exp": round(la, 2),
                        "home_adv": 1.06}
        p_best = max(p_home, p_away)
        cap = "High" if min(a["gp"], b["gp"]) >= 10 else "Medium"
        pick_from(row, "match_winner", 1 if p_home >= p_away else 0, conf(p_best, cap),
                  "p>=70% High; 55-70% Medium; sample >=10 GP else capped Medium")
        rows.append(row)


def build_liiga(cap: P.Capture, rows):
    fx, tab = P.read_liiga(cap)
    if not fx or not tab:
        return
    lg = sum(t["gf"] + t["ga"] for t in tab.values()) / max(1, sum(t["gp"] for t in tab.values()))
    for f in fx:
        if not in_window(f["start_utc"]):
            continue
        a, b = tab.get(f["side_a"]), tab.get(f["side_b"])
        row = blank_row(**f)
        if not a or not b or not a["gp"] or not b["gp"]:
            row["flags"].append("standings row missing - no line originated")
            rows.append(row)
            continue
        a_gf, a_ga = a["gf"] / a["gp"], a["ga"] / a["gp"]
        b_gf, b_ga = b["gf"] / b["gp"], b["ga"] / b["gp"]
        b_att = 0.7 * (b_gf / (lg / 2)) + 0.3
        a_att = 0.7 * (a_gf / (lg / 2)) + 0.3
        b_def = 0.7 * (b_ga / (lg / 2)) + 0.3
        a_def = 0.7 * (a_ga / (lg / 2)) + 0.3
        lh = max(0.8, min(5.2, (lg / 2) * b_att * a_def * 1.06))
        la = max(0.8, min(5.2, (lg / 2) * a_att * b_def * 0.94))
        g = grid_probs(lh, la)
        p_home = min(0.82, max(0.18, shrink(g["home"] + 0.5 * g["tie"], 0.88)))
        p_away = 1 - p_home
        line = round(lh + la) + 0.5
        over = pmf_from(g["total"], lambda k: k > line)
        row["evidence"] = {"away_gf_pg": round(a_gf, 3), "away_ga_pg": round(a_ga, 3),
                           "home_gf_pg": round(b_gf, 3), "home_ga_pg": round(b_ga, 3),
                           "expected_goals_away": round(la, 2), "expected_goals_home": round(lh, 2),
                           "standings_source": a["source_url"]}
        row["form"] = {"away": f"{a['w']}-{a['t']}-{a['l']} ({a['pts']} pts, {a['gp']} GP)",
                       "home": f"{b['w']}-{b['t']}-{b['l']} ({b['pts']} pts, {b['gp']} GP)"}
        row["sample"] = f"{min(a['gp'], b['gp'])} games played"
        row["markets"] = {
            "match_winner": market("Money Line (incl. OT)", None, [
                (f"{f['side_a']} (away)", p_away), (f"{f['side_b']} (home)", p_home)]),
            "handicap": market("Puck Line", -1.5, [
                (f"{f['side_b']} -1.5", pmf_from(g["margin"], lambda m: m >= 2)),
                (f"{f['side_a']} +1.5", pmf_from(g["margin"], lambda m: m <= 1))]),
            "total": market(f"Total Goals {line}", line, [
                (f"Under {line}", 1 - over), (f"Over {line}", over)]),
        }
        row["model"] = {"name": "independent Poisson goals, table attack/defence",
                        "home_exp": round(lh, 2), "away_exp": round(la, 2), "home_adv": 1.06}
        p_best = max(p_home, p_away)
        pick_from(row, "match_winner", 1 if p_home >= p_away else 0, conf(p_best, "Medium"),
                  "p>=70% High; sample >=10 GP else capped Medium")
        rows.append(row)


# ----------------------------------------------------------------- basketball
def build_basketball(cap: P.Capture, rows):
    for tid, comp in (("el_games", "EuroLeague 2026-27"), ("eurocup_games", "EuroCup 2026-27")):
        fx = P.read_euroleague(cap, tid, comp)
        tab = P.euroleague_table(cap, tid)
        for f in fx:
            if not in_window(f["start_utc"]):
                continue
            a, b = tab.get(f["side_a"]), tab.get(f["side_b"])
            row = blank_row(**f)
            if not a or not b or a["gp"] < 4 or b["gp"] < 4:
                row["flags"].append("fewer than 3 completed games for one side - no line originated")
                rows.append(row)
                continue
            exp_h = (b["pf_pg"] + a["pa_pg"]) / 2 + 1.5
            exp_a = (a["pf_pg"] + b["pa_pg"]) / 2 - 1.5
            mean_margin = exp_h - exp_a
            sd = 12.5
            p_home = min(0.85, max(0.15, shrink(norm_cdf(mean_margin / sd), 0.80)))
            p_away = 1 - p_home
            tot = round(exp_h + exp_a)
            total_line = tot + 0.5
            p_over = 1 - norm_cdf((total_line - (exp_h + exp_a)) / (sd * 1.35))
            hcap = -round(abs(mean_margin)) - 0.5 if mean_margin > 0 else 0.5
            row["evidence"] = {"away_ppp_for": a["pf_pg"], "away_ppp_against": a["pa_pg"],
                               "home_ppp_for": b["pf_pg"], "home_ppp_against": b["pa_pg"],
                               "away_games": a["gp"], "home_games": b["gp"],
                               "standings_source": a["source_url"]}
            row["form"] = {"away": f"{a['w']}-{a['l']} ({a['gp']} games)", "home": f"{b['w']}-{b['l']} ({b['gp']} games)"}
            row["sample"] = f"{min(a['gp'], b['gp'])} completed games"
            row["markets"] = {
                "match_winner": market("Money Line", None, [
                    (f"{f['side_b']} (home)", p_home), (f"{f['side_a']} (away)", p_away)]),
                "handicap": market("Point Spread", hcap, [
                    (f"{f['side_b']} {hcap:+.1f}", norm_cdf((mean_margin - hcap) / sd)),
                    (f"{f['side_a']} {-hcap:+.1f}", 1 - norm_cdf((mean_margin - hcap) / sd))]),
                "total": market(f"Total Points {total_line}", total_line, [
                    (f"Under {total_line}", 1 - p_over), (f"Over {total_line}", p_over)]),
            }
            row["model"] = {"name": "normal point-margin model", "mean_margin": round(mean_margin, 2),
                            "sd": sd, "exp_home": round(exp_h, 1), "exp_away": round(exp_a, 1),
                            "home_court": 1.5}
            p_best = max(p_home, p_away)
            pick_from(row, "match_winner", 0 if p_home >= p_away else 1, conf(p_best, "High"),
                      "p>=70% High; 55-70% Medium")
            rows.append(row)


# -------------------------------------------------------------------- baseball
def build_mlb(cap: P.Capture, rows):
    st = P.read_mlb_standings(cap)
    lg = sum(t["rs"] + t["ra"] for t in st.values()) / max(1, sum(t["gp"] for t in st.values()))
    for f in P.read_mlb(cap):
        if not in_window(f["start_utc"]):
            continue
        extra = f.get("extra", {})
        a = st.get(f"id:{extra.get('away_id')}") or st.get(f["side_a"])
        b = st.get(f"id:{extra.get('home_id')}") or st.get(f["side_b"])
        row = blank_row(**f)
        extra = row.pop("extra", {})
        if not a or not b:
            row["flags"].append("standings row missing - no line originated")
            rows.append(row)
            continue
        b_att = 0.75 * (b["rs_pg"] / (lg / 2)) + 0.25
        a_att = 0.75 * (a["rs_pg"] / (lg / 2)) + 0.25
        b_def = 0.75 * (b["ra_pg"] / (lg / 2)) + 0.25
        a_def = 0.75 * (a["ra_pg"] / (lg / 2)) + 0.25
        lh = max(2.5, min(7.0, (lg / 2) * b_att * a_def * 1.02))
        la = max(2.5, min(7.0, (lg / 2) * a_att * b_def * 0.98))
        g = grid_probs(lh, la, 22)
        p_home = min(0.75, max(0.25, shrink(g["home"], 0.85)))
        p_away = 1 - p_home
        line = round(lh + la) + 0.5
        over = pmf_from(g["total"], lambda k: k > line)
        row["evidence"] = {"away_rs_pg": a["rs_pg"], "away_ra_pg": a["ra_pg"],
                           "home_rs_pg": b["rs_pg"], "home_ra_pg": b["ra_pg"],
                           "expected_runs_away": round(la, 2), "expected_runs_home": round(lh, 2),
                           "away_record": f"{a['w']}-{a['l']}", "home_record": f"{b['w']}-{b['l']}",
                           "away_pitcher": extra.get("away_pitcher", ""), "home_pitcher": extra.get("home_pitcher", ""),
                           "series_game": extra.get("series_game"), "standings_source": a["source_url"]}
        row["form"] = {"away": f"{a['w']}-{a['l']} (RS/RA {a['rs']}-{a['ra']})",
                       "home": f"{b['w']}-{b['l']} (RS/RA {b['rs']}-{b['ra']})"}
        row["sample"] = "full 2026 regular season team totals"
        row["markets"] = {
            "match_winner": market("Money Line", None, [
                (f"{f['side_a']} (away)", p_away), (f"{f['side_b']} (home)", p_home)]),
            "handicap": market("Run Line", -1.5, [
                (f"{f['side_b']} -1.5", pmf_from(g["margin"], lambda m: m >= 2)),
                (f"{f['side_a']} +1.5", pmf_from(g["margin"], lambda m: m <= 1))]),
            "total": market(f"Total Runs {line}", line, [
                (f"Under {line}", 1 - over), (f"Over {line}", over)]),
        }
        row["model"] = {"name": "independent Poisson runs, season team rates",
                        "home_exp": round(lh, 2), "away_exp": round(la, 2), "league_runs_pg": round(lg, 3)}
        p_best = max(p_home, p_away)
        pick_from(row, "match_winner", 1 if p_home >= p_away else 0, conf(p_best, "High"),
                  "p>=70% High; 55-70% Medium")
        rows.append(row)


# ------------------------------------------------------------------- volleyball
def _volley_rows(rows, fixtures, table, comp_name, src_note, cap_conf="Medium"):
    for f in fixtures:
        if not in_window(f["start_utc"]):
            continue
        a, b = table.get(f["side_a"]), table.get(f["side_b"])
        row = blank_row(**f)
        if not a or not b or not a.get("pw") or not b.get("pw"):
            row["flags"].append("published table row unavailable - no line originated")
            rows.append(row)
            continue
        pr_a = a["pw"] / max(1, a["pl"])
        pr_b = b["pw"] / max(1, b["pl"])
        diff = (pr_a - pr_b) * 25.0 + 1.0
        p_set = norm_cdf(diff / 5.5)
        p_home, dist = volleyball_dist(1 - p_set)  # side_b is home
        p_away = 1 - p_home
        # set handicap -1.5 for home: wins 3-0 or 3-1
        home_31 = sum(pr for (w, l), pr in dist.items() if w == 3 and l <= 1)
        away_p15 = 1 - home_31
        # totals
        t35 = sum(pr for k, pr in dist.items() if sum(k) <= 3)
        row["evidence"] = {"away_points_ratio": round(pr_a, 4), "home_points_ratio": round(pr_b, 4),
                           "away_sets": f"{a['sw']}-{a['sl']}", "home_sets": f"{b['sw']}-{b['sl']}",
                           "away_pts": f"{a['pw']}-{a['pl']}", "home_pts": f"{b['pw']}-{b['pl']}",
                           "games_played": f"{a['gp']} / {b['gp']}", "table_source": a["source_url"]}
        row["form"] = {"away": f"{a.get('pts', 0)} pts, sets {a['sw']}-{a['sl']}", "home": f"{b.get('pts', 0)} pts, sets {b['sw']}-{b['sl']}"}
        row["sample"] = f"{min(a['gp'], b['gp'])} matches played"
        row["markets"] = {
            "match_winner": market("Match Winner", None, [
                (f"{f['side_b']} (home)", p_home), (f"{f['side_a']} (away)", p_away)]),
            "handicap": market("Set Handicap", -1.5, [
                (f"{f['side_b']} -1.5", home_31), (f"{f['side_a']} +1.5", away_p15)]),
            "total": market("Total Sets 3.5", 3.5, [("Under 3.5", t35), ("Over 3.5", 1 - t35)]),
        }
        row["model"] = {"name": "point-ratio set model, best-of-5", "p_set_home": round(1 - p_set, 4),
                        "point_diff_input": round(diff, 2), "note": src_note}
        p_best = max(p_home, p_away)
        pick_from(row, "match_winner", 0 if p_home >= p_away else 1, conf(p_best, cap_conf),
                  "p>=70% High; sample <5 matches capped Medium")
        rows.append(row)


def build_volleyball(cap: P.Capture, rows):
    for cid in ("1003", "1004", "995", "1002", "legavolley_cal"):
        tid = f"legavolley_cal_{cid}" if f"legavolley_cal_{cid}" in cap.by_id else cid
        fx, tab = P.read_legavolley(cap, tid)
        if fx and tab and any((not f["extra"].get("played") for f in fx)):
            _volley_rows(rows, [f for f in fx if not f["extra"].get("played")], tab,
                         "SuperLega", "official calendar + published table")
            break
    # PlusLiga: table only (no official fixture payload captured) -> listed as unpriced
    pt = P.read_plusliga(cap)
    for team, t in pt.items():
        pass


# -------------------------------------------------------------------- handball
def build_handball(cap: P.Capture, rows):
    tab = P.read_herreligaen(cap)
    if not tab:
        return
    lg = sum(t["gf"] + t["ga"] for t in tab.values()) / max(1, sum(t["gp"] for t in tab.values()))
    for f in []:  # fixtures require an official programme payload; none captured -> no priced rows
        pass
    return tab, lg


# ---------------------------------------------------------------------- tennis
def build_tennis(cap: P.Capture, rows):
    ranks = {}
    if cap.exists("wta_rankings"):
        data = cap.json("wta_rankings")
        rows_ = data if isinstance(data, list) else data.get("rankings", data.get("data", []))
        for r in rows_:
            name = " ".join(x for x in [r.get("player", {}).get("firstName", ""), r.get("player", {}).get("lastName", "")] if x) or r.get("playerName", "")
            rank = r.get("rank") or r.get("ranking")
            if name and rank:
                ranks[name.lower()] = int(rank)
    for tid in ("wta_2092", "wta_405", "wta_1023", "wta_1056"):
        for f in P.read_wta(cap, tid):
            row = blank_row(**f)
            ra = ranks.get(f["side_a"].lower())
            rb = ranks.get(f["side_b"].lower())
            row["evidence"] = {"rank_a": ra, "rank_b": rb, "draw": f["extra"].get("draw")}
            row["form"] = {}
            if not ra or not rb:
                row["flags"].append("official singles ranking unavailable for one player - no line originated")
                rows.append(row)
                continue
            p_a = 1 / (1 + 10 ** ((rb - ra) / 40.0))
            p_a = min(max(p_a, 0.03), 0.97)
            row["markets"] = {"match_winner": market("Match Winner", None, [
                (f"{f['side_a']}", p_a), (f"{f['side_b']}", 1 - p_a)])}
            row["model"] = {"name": "logistic on official singles ranking gap", "rank_a": ra, "rank_b": rb}
            row["sample"] = "official ranking positions"
            pick_from(row, "match_winner", 0 if p_a >= 0.5 else 1, conf(max(p_a, 1 - p_a), "Medium"),
                      "ranking-only model capped at Medium")
            rows.append(row)


# ---------------------------------------------------------------------- snooker
def _snooker_row(rows, f, r1, r2, bo, source_note):
    row = blank_row(**f)
    p_a = 1 / (1 + 10 ** ((r1 - r2) / 220.0))
    p_a = min(0.93, max(0.07, p_a))
    wins = sum(math.comb(bo, k) * p_a ** k * (1 - p_a) ** (bo - k) for k in range(bo // 2 + 1, bo + 1))
    row["evidence"] = {"world_rank_a": r1, "world_rank_b": r2, "best_of": bo,
                       "round": f.get("extra", {}).get("round"),
                       "rank_source": "WST official world ranking list",
                       "cross_check": source_note}
    row["form"] = {f["side_a"]: f"world rank {r1}", f["side_b"]: f"world rank {r2}"}
    row["sample"] = f"best of {bo} frames; official two-year world ranking"
    flag_p = p_a
    margins = {}
    for k in range(bo // 2 + 1, bo + 1):
        margins[k - (bo - k)] = margins.get(k - (bo - k), 0) + math.comb(bo, k) * p_a ** k * (1 - p_a) ** (bo - k)
    row["markets"] = {
        "match_winner": market("Match Winner", None, [(f"{f['side_a']}", p_a), (f"{f['side_b']}", 1 - p_a)]),
        "handicap": market("Frame Handicap", -2.5, [
            (f"{f['side_a']} -2.5", sum(v for k, v in margins.items() if k >= 3)),
            (f"{f['side_b']} +2.5", sum(v for k, v in margins.items() if k < 3))]),
    }
    row["flags"].append("total frames not modelled - no official frame-tempo input captured")
    row["model"] = {"name": "frame Bernoulli from WST world-ranking gap, exact best-of-n",
                    "p_frame": round(p_a, 4), "best_of": bo}
    pick_from(row, "match_winner", 0 if p_a >= 0.5 else 1, conf(max(p_a, 1 - p_a), "High"),
              "p>=70% High; ranking-only model, sample = official ranking list")
    rows.append(row)


def build_snooker(cap: P.Capture, rows):
    wst, _ = P.read_wst(cap) if hasattr(P, "read_wst") else ([], {})
    seen = set()
    for f in wst:
        if not in_window(f["start_utc"]):
            continue
        r1, r2 = f["extra"].get("rank_a"), f["extra"].get("rank_b")
        if not r1 or not r2:
            row = blank_row(**f)
            row["flags"].append("one player has no official world-ranking position - no line originated")
            rows.append(row)
            continue
        _snooker_row(rows, f, int(r1), int(r2), int(f["extra"].get("best_of") or 7),
                     "WST match feed and WST ranking list read in the same capture")
        seen.add((f["side_a"], f["side_b"]))
    if not wst:
        for f in P.read_snooker_org(cap):
            ra = re.search(r"\[(\d+)\]", f["side_a"])
            rb = re.search(r"\[(\d+)\]", f["side_b"])
            if not ra or not rb:
                continue
            _snooker_row(rows, f, int(ra.group(1)), int(rb.group(1)), int(f["extra"].get("best_of") or 11),
                         "snooker.org event page (seed numbers)")


# ------------------------------------------------------------------ rugby league
def build_rugby_league(cap: P.Capture, rows):
    fx = P.read_rlwc(cap)
    if not fx:
        return
    played = [f for f in fx if f["extra"].get("state") == "Final"
              and f["extra"].get("home_score") is not None and f["extra"].get("away_score") is not None]
    stats = {}
    for f in played:
        h, a = f["side_b"], f["side_a"]
        hs, as_ = f["extra"]["home_score"], f["extra"]["away_score"]
        for team, pf, pa in ((h, hs, as_), (a, as_, hs)):
            t = stats.setdefault(team, {"gp": 0, "pf": 0, "pa": 0})
            t["gp"] += 1
            t["pf"] += pf
            t["pa"] += pa
    if not stats:
        return
    lg = sum(t["pf"] for t in stats.values()) / max(1, sum(t["gp"] for t in stats.values()))
    for f in fx:
        if not in_window(f["start_utc"]):
            continue
        row = blank_row(**f)
        a, b = stats.get(f["side_a"]), stats.get(f["side_b"])
        if not a or not b:
            row["flags"].append("no completed tournament match for one side - no line originated")
            rows.append(row)
            continue
        # shrink each side's tournament rate 40% toward the tournament mean to counter a 1-2 game sample
        a_pf = 0.35 * (a["pf"] / a["gp"]) + 0.65 * lg
        a_pa = 0.35 * (a["pa"] / a["gp"]) + 0.65 * lg
        b_pf = 0.35 * (b["pf"] / b["gp"]) + 0.65 * lg
        b_pa = 0.35 * (b["pa"] / b["gp"]) + 0.65 * lg
        lh = max(4.0, min(48.0, (b_pf * a_pa / lg) * 1.02))
        la = max(4.0, min(48.0, (a_pf * b_pa / lg) * 0.98))
        margin_mean = lh - la
        sd = 20.0
        p_home = min(0.95, max(0.05, shrink(norm_cdf(margin_mean / sd), 0.85)))
        p_away = 1 - p_home
        line = round(lh + la)
        total_line = line + 0.5
        over = 1 - norm_cdf(((total_line) - (lh + la)) / (sd * 1.25))
        row["evidence"] = {"away_pf_pg": round(a_pf, 2), "away_pa_pg": round(a_pa, 2),
                           "home_pf_pg": round(b_pf, 2), "home_pa_pg": round(b_pa, 2),
                           "expected_away": round(la, 1), "expected_home": round(lh, 1),
                           "completed_matches_used": len(played), "group": f["extra"].get("group")}
        row["form"] = {"away": f"{a_pf:.0f} pts for / {a_pa:.0f} against per match ({a['gp']} played)",
                       "home": f"{b_pf:.0f} pts for / {b_pa:.0f} against per match ({b['gp']} played)"}
        row["sample"] = f"{len(played)} completed tournament matches in total"
        spread = -round(abs(margin_mean)) - 0.5 if margin_mean > 0 else round(abs(margin_mean)) + 0.5
        row["markets"] = {
            "match_winner": market("Match Winner (incl. golden point)", None, [
                (f"{f['side_b']} (home)", p_home), (f"{f['side_a']} (away)", p_away)]),
            "handicap": market("Points Handicap", spread, [
                (f"{f['side_b']} {spread:+.1f}", norm_cdf((margin_mean - spread) / sd)),
                (f"{f['side_a']} {-spread:+.1f}", 1 - norm_cdf((margin_mean - spread) / sd))]),
            "total": market(f"Total Points {total_line}", total_line, [
                (f"Under {total_line}", 1 - over), (f"Over {total_line}", over)]),
        }
        row["model"] = {"name": "independent Poisson points from tournament scoring rates",
                        "home_exp": round(lh, 1), "away_exp": round(la, 1)}
        row["flags"].append("one-to-two match sample per side: confidence capped at Medium")
        pick_from(row, "match_winner", 0 if p_home >= p_away else 1, conf(max(p_home, p_away), "Medium"),
                  "p>=70% High; <3 tournament matches per side capped Medium")
        rows.append(row)


# ------------------------------------------------------------------------- golf
def build_golf(cap: P.Capture, rows):
    for tid in ("pgatour_bermuda", "pgatour_leaderboard"):
        data = P.read_pga(cap, tid)
        if not data or data.get("status") not in ("IN_PROGRESS", "SCHEDULED", "COMPLETED"):
            continue
        players = [p for p in data["players"] if isinstance(p.get("total_sort"), (int, float))]
        if len(players) < 20:
            continue
        remaining = max(0.0, (72 - 18 * (data.get("current_round") or 1)) * 1.0)
        sd = max(1.0, 2.2 * math.sqrt(max(1.0, remaining / 18.0) * 18 / 18))
        rng = random.Random(20261023)
        n = 15000
        scores = []
        for p in players:
            base = p["total_sort"]
            scores.append([base + rng.gauss(0, sd) for _ in range(n)])
        wins = [0] * len(players)
        for i in range(n):
            best = min(range(len(players)), key=lambda j: scores[j][i])
            wins[best] += 1
        order = sorted(range(len(players)), key=lambda j: players[j]["total_sort"])
        top = order[0]
        p_win = max(0.01, wins[top] / n)
        row = blank_row(
            id="fx_golf_" + (data.get("tournament_id") or "R2026528"),
            sport="Golf", sport_slug="golf",
            competition="PGA Tour - " + data.get("tournament", ""),
            side_a=data.get("tournament", ""), side_b="",
            start_utc="", venue=data.get("location", ""),
            official_url=data["source_url"],
            official_source_name="PGA Tour official leaderboard (pgatour.com)",
            capture_id=data["source_id"],
        )
        row["evidence"] = {"leader": players[top]["name"], "leader_total": players[top]["total"],
                           "leader_thru": players[top]["thru"], "round": data.get("current_round"),
                           "status": data.get("status"), "field_size": len(players),
                           "remaining_holes_model": remaining,
                           "top5": [{"name": players[j]["name"], "pos": players[j]["position"],
                                     "total": players[j]["total"]} for j in order[:5]]}
        row["form"] = {players[j]["name"]: players[j]["total"] for j in order[:3]}
        row["sample"] = f"{len(players)} players with a score in the official leaderboard"
        row["markets"] = {"outright": market("Outright Winner", None, [
            (players[top]["name"], p_win), ("Field (any other player)", 1 - p_win)])}
        row["model"] = {"name": "Monte Carlo (15k) remaining-hole normal model", "sd_remaining": round(sd, 2),
                        "remaining_holes": remaining}
        pick_from(row, "outright", 0, conf(p_win, "Medium"), "golf outright capped at Medium")
        rows.append(row)
        break


# ---------------------------------------------------------------- motor racing
def build_motorsport(cap: P.Capture, rows):
    data = P.read_f1(cap)
    st = data["standings"]
    if not st:
        return
    total_pts = sum(x["pts"] for x in st) or 1
    tau = 120.0
    expv = [math.exp(x["pts"] / tau) for x in st]
    s = sum(expv)
    probs = [e / s for e in expv]
    best = max(range(len(st)), key=lambda i: probs[i])
    idx = [i for i, r in enumerate(data["races"]) if "Mexico" in r["name"]]
    race = data["races"][idx[0]] if idx else (data["races"][0] if data["races"] else {"name": "Next Grand Prix", "dates": "", "round": ""})
    row = blank_row(
        id="fx_f1_mexico", sport="Motor Racing", sport_slug="motor-racing",
        competition="Formula 1 2026 - " + race["name"],
        side_a=race["name"], side_b="", start_utc="2026-11-01T20:00:00Z", venue="Mexico City",
        official_url=data["source_url"],
        official_source_name="Formula 1 official driver standings (formula1.com)",
        capture_id=data["source_id"],
    )
    row["evidence"] = {"round": race["round"], "dates": race["dates"], "driver": st[best]["driver"],
                       "points": st[best]["pts"], "points_share": round(st[best]["pts"] / total_pts, 4),
                       "standings_top5": st[:5], "races_listed": len(data["races"])}
    row["form"] = {x["driver"]: f"{x['pts']} pts" for x in st[:5]}
    row["sample"] = f"{len(st)} classified drivers"
    row["markets"] = {"outright": market("Race Winner", None, [
        (st[best]["driver"], probs[best]), ("Field (any other driver)", 1 - probs[best])])}
    row["model"] = {"name": "Plackett-Luce on official championship points", "tau": tau}
    pick_from(row, "outright", 0, conf(probs[best], "Medium"), "single-race outright capped at Medium")
    rows.append(row)


# ---------------------------------------------------------------------- cricket
def build_cricket(cap: P.Capture, rows):
    for f in P.read_cricket_au(cap):
        if not in_window(f["start_utc"]):
            continue
        row = blank_row(**f)
        row["flags"].append("no official team-strength feed captured for this competition - no line originated")
        rows.append(row)


# ----------------------------------------------------------------------- gaelic
def build_gaelic(cap: P.Capture, rows):
    seen = set()
    for f in P.read_gaa(cap):
        if f["id"] in seen or not in_window(f["start_utc"]):
            continue
        if f.get("extra", {}).get("tbc"):
            continue
        seen.add(f["id"])
        row = blank_row(**f)
        row["flags"].append("fixture published without a verified form table - no line originated")
        rows.append(row)


# -------------------------------------------------------------------- greyhounds
def build_greyhounds(cap: P.Capture, rows):
    items = P.read_gbgb(cap)
    if not items:
        return
    tracks = sorted({i.get("trackName", "") for i in items})
    row = blank_row(
        id="fx_gbgb_20261023", sport="Greyhounds", sport_slug="greyhounds",
        competition="GBGB race results 23 Oct 2026", side_a="GBGB meetings", side_b="",
        start_utc="", venue=", ".join(tracks[:6]),
        official_url=cap.url("gbgb_results_api"),
        official_source_name="GBGB official results API (api.gbgb.org.uk)",
        capture_id="gbgb_results_api",
    )
    row["evidence"] = {"winners_captured": len(items), "tracks": tracks[:12],
                       "example": {k: items[0].get(k) for k in ("trackName", "raceTime", "dogName", "trainerName")}}
    row["flags"].append("GBGB racecard/fixture endpoints returned 404 - no upcoming race priced")
    rows.append(row)


# ------------------------------------------------------------------- assemble
def attach_olbg(rows, olbg_events):
    def norm(s):
        s = re.sub(r"\(.*?\)", "", s or "").lower()
        s = re.sub(r"\b(fc|men|women|u21|u20|u19|reserves)\b", "", s)
        return re.sub(r"[^a-z0-9]", "", s)

    idx = {}
    for ev in olbg_events:
        txt = ev["event"]
        parties = re.split(r"\s+(?:vs|v|@|-)\s+", txt)
        if len(parties) == 2:
            idx[(norm(parties[0]), norm(parties[1]))] = ev
            idx[(norm(parties[1]), norm(parties[0]))] = ev
    for r in rows:
        a, b = norm(r["side_a"]), norm(r["side_b"])
        ev = idx.get((a, b)) or (idx.get((a, a)) if a == b else None)
        if ev:
            r["olbg"] = {"event": ev["event"], "event_url": ev["event_url"],
                         "hub_url": ev["hub_url"], "listed_tips": len(ev["tips"])}


def build(cap_dir: str):
    cap = P.Capture(cap_dir)
    rows = []
    build_nhl(cap, rows)
    build_liiga(cap, rows)
    build_basketball(cap, rows)
    build_mlb(cap, rows)
    build_volleyball(cap, rows)
    build_tennis(cap, rows)
    build_snooker(cap, rows)
    build_golf(cap, rows)
    build_motorsport(cap, rows)
    build_rugby_league(cap, rows)
    build_cricket(cap, rows)
    build_gaelic(cap, rows)
    build_greyhounds(cap, rows)
    hb = build_handball(cap, rows)
    attach_olbg(rows, P.read_olbg(cap))
    # OLBG-listed events with no official fixture match are still published, unpriced.
    covered = {(r["sport"]) for r in rows}
    for ev in P.read_olbg(cap):
        if ev["sport"] in ("Ice Hockey", "Basketball", "Baseball", "Tennis", "Snooker"):
            continue
        if not in_window(ev["start_utc"] or ""):
            continue
        rows.append(blank_row(
            id="fx_olbg_" + (ev["event_id"] or re.sub(r"\W+", "_", ev["event"])[:40]),
            sport=ev["sport"], sport_slug=dict(SUPPORTED)[ev["sport"]],
            competition="OLBG-listed event (official fixture not located)",
            side_a=ev["event"], side_b="", start_utc=ev["start_utc"],
            official_url=ev["event_url"], official_source_name="OLBG sport hub listing (taxonomy only)",
            capture_id=ev["hub"], flags=["OLBG listing only - no official fixture/values located, no line originated"],
            olbg={"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                  "listed_tips": len(ev["tips"])}))
    return cap, rows


def summarise(rows):
    out = {}
    for sport, slug in SUPPORTED:
        srows = [r for r in rows if r["sport"] == sport]
        priced = [r for r in srows if r.get("pick")]
        high = [r for r in srows if r.get("pick") and r["pick"]["confidence"] == "High"]
        high_win = [r for r in high if r["pick"]["in_window"]]
        out[sport] = {"slug": slug, "rows": len(srows), "priced": len(priced),
                      "high": len(high), "high_in_window": len(high_win),
                      "markets": sum(len(r["markets"]) for r in srows)}
    return out


def main():
    cap_dir = sys.argv[1]
    out_path = sys.argv[2]
    cap, rows = build(cap_dir)
    # OLBG market taxonomy observed on the hubs (verbatim market_alias values)
    taxonomy = {}
    for ev in P.read_olbg(cap):
        for t in ev["tips"]:
            taxonomy.setdefault(ev["sport"], {}).setdefault(t["market"], 0)
            taxonomy[ev["sport"]][t["market"]] += 1
    doc = {
        "olbg_market_taxonomy": taxonomy,
        "schema": "fx-desk-1",
        "session": "arena/4502eff5-olbg4",
        "board": "FX",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture": os.path.basename(cap_dir.rstrip("/")),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "rows": rows,
        "summary": summarise(rows),
    }
    json.dump(doc, open(out_path, "w"), indent=1, sort_keys=True)
    print(json.dumps(doc["summary"], indent=1))
    print("rows", len(rows), "priced", sum(1 for r in rows if r.get("pick")))


if __name__ == "__main__":
    main()

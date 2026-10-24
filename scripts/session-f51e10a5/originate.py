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
import sources as P  # noqa: E402

WINDOW_START = "2026-10-24T22:40:00Z"
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
    ps = [min(0.95, max(0.02, float(p))) for _, p in selections]
    if len(ps) >= 2:
        tot = sum(ps)
        ps = [p / tot for p in ps]
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
    confidence = conf(p, confidence)
    if confidence == "High" and not in_win:
        confidence = "Medium"
        rule = rule + "; High needs the price inside -250..+10,000, so this is capped at Medium"
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
    # points per SET PLAYED: dividing by sets won (or lost) alone divides by 1 when a side has
    # lost no sets, which turns 65 total points conceded into "65 per set". Use sw+sl.
    sc = lambda t: t["pw"] / max(1, t["sw"] + t["sl"])
    cn = lambda t: t["pl"] / max(1, t["sw"] + t["sl"])
    shrink_rate = lambda x: 1.0 + 0.15 * (x - 1.0)  # one-match samples pulled 85% back to the league mean
    for f in fixtures:
        if not in_window(f["start_utc"]):
            continue
        a, b = table.get(f["side_a"]), table.get(f["side_b"])
        row = blank_row(**f)
        if not a or not b or a["gp"] < 1 or b["gp"] < 1:
            row["flags"].append("published table row or completed match unavailable - no line originated")
            rows.append(row)
            continue
        att_h, att_a = shrink_rate((sc(b) / 25.0) ** 0.5), shrink_rate((sc(a) / 25.0) ** 0.5)
        def_h, def_a = shrink_rate((cn(b) / 25.0) ** 0.5), shrink_rate((cn(a) / 25.0) ** 0.5)
        num = att_h * def_a * 1.03
        p_point = num / (num + att_a * def_h)
        p_set = p_point ** 2.5 / (p_point ** 2.5 + (1 - p_point) ** 2.5)
        p_home, dist = volleyball_dist(p_set)
        p_home = min(0.86, max(0.14, p_home))
        p_set = min(0.80, max(0.20, p_set))
        home_31 = dist.get((3, 0), 0.0) + dist.get((3, 1), 0.0)
        straight = dist.get((3, 0), 0.0) + dist.get((0, 3), 0.0)
        row["evidence"] = {"away_points_per_set": round(sc(a), 2), "home_points_per_set": round(sc(b), 2),
                           "away_conceded_per_set": round(cn(a), 2), "home_conceded_per_set": round(cn(b), 2),
                           "away_sets": f"{a['sw']}-{a['sl']}", "home_sets": f"{b['sw']}-{b['sl']}",
                           "games_played": f"{a['gp']} / {b['gp']}", "table_source": a["source_url"],
                           "table_updated": "classifica aggiornata al 18/10/2026"}
        row["form"] = {"away": f"{a.get('pts', 0)} pts, sets {a['sw']}-{a['sl']}",
                       "home": f"{b.get('pts', 0)} pts, sets {b['sw']}-{b['sl']}"}
        row["sample"] = f"{min(a['gp'], b['gp'])} completed match(es) per side"
        row["markets"] = {
            "match_winner": market("Match Winner", None, [
                (f"{f['side_b']} (home)", p_home), (f"{f['side_a']} (away)", 1 - p_home)]),
            "handicap": market("Set Handicap", -1.5, [
                (f"{f['side_b']} -1.5", home_31), (f"{f['side_a']} +1.5", 1 - home_31)]),
            "total": market("Total Sets 3.5", 3.5, [
                ("Under 3.5", straight), ("Over 3.5", 1 - straight)]),
        }
        row["model"] = {"name": "point-ratio set model, exact best-of-5",
                        "p_point_home": round(p_point, 4), "p_set_home": round(p_set, 4),
                        "note": src_note, "sample_penalty": "0.15 weight on the club rate (one completed match)"}
        p_best = max(p_home, 1 - p_home)
        pick_from(row, "match_winner", 0 if p_home >= 1 - p_home else 1, conf(p_best, cap_conf),
                  "p>=70% High; a one-match official sample keeps the label at Medium")
        rows.append(row)


def build_volleyball(cap: P.Capture, rows):
    fx, tab = P.read_legavolley(cap, "legavolley_cal_999", "SuperLega Credem Banca 2026-27 (Italy)")
    _volley_rows(rows, [f for f in fx if not f["extra"].get("played")], tab, "SuperLega",
                 "Lega Pallavolo Serie A calendar and classifica read in the same capture")
    # Serie A2 calendar is published, but its own classifica was not captured: list the fixtures, do not price them.
    fx2, tab2 = P.read_legavolley(cap, "legavolley_cal_1000", "Serie A2 Credem Banca 2026-27 (Italy)")
    for f in fx2:
        if f["extra"].get("played") or not in_window(f["start_utc"]):
            continue
        row = blank_row(**f)
        row["flags"].append("Serie A2 classifica not captured - fixture listed without a line")
        rows.append(row)
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
            id="ca_golf_" + (data.get("tournament_id") or "R2026528"),
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
        id="ca_f1_mexico", sport="Motor Racing", sport_slug="motor-racing",
        competition="Formula 1 2026 - " + race["name"],
        side_a=race["name"], side_b="", start_utc="2026-11-01T20:00:00Z", venue="Mexico City",
        official_url=data["source_url"],
        official_source_name="Formula 1 official driver standings (formula1.com)",
        capture_id=data["source_id"],
    )
    row["evidence"] = {"round": race["round"], "dates": race["dates"], "driver": st[best]["driver"],
                       "points": st[best]["pts"], "points_share": round(st[best]["pts"] / total_pts, 4),
                       "standings_top5": st[:5], "races_listed": len(data["races"])}
    for x in st:
        x["driver"] = _clean_driver(x["driver"])
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
        id="ca_gbgb_20261023", sport="Greyhounds", sport_slug="greyhounds",
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
    """Attach the OLBG event page to the official row it describes.

    Returns the set of OLBG event ids consumed, so the caller can publish the
    remainder as 'OLBG listing only' rows without duplicating a fixture that
    already has an official row.
    """
    STRIP = re.compile(r"\b(fc|men|women|womens|mens|u21|u20|u19|reserves|t20|t10|odi|"
                       r"one day match|test match|1st|2nd|3rd|4th|5th|match|game)\b")

    def norm(s):
        s = re.sub(r"\(.*?\)", " ", s or "")
        s = s.lower().replace("&", " and ")
        s = STRIP.sub(" ", s)
        return re.sub(r"[^a-z0-9]", "", s)

    idx = {}
    for ev in olbg_events:
        parties = re.split(r"\s+(?:vs\.?|v|@|-)\s+", ev["event"])
        if len(parties) == 2:
            p = (norm(parties[0]), norm(parties[1]))
            idx[p] = ev
            idx[(p[1], p[0])] = ev
    consumed = set()
    for r in rows:
        a, b = norm(r["side_a"]), norm(r["side_b"])
        ev = idx.get((a, b))
        if ev is None and a and b:
            for (x, y), cand in idx.items():
                if not x or not y:
                    continue
                if ((a.startswith(x) or x.startswith(a)) and (b.startswith(y) or y.startswith(b))) or \
                   ((a.startswith(y) or y.startswith(a)) and (b.startswith(x) or x.startswith(b))):
                    ev = cand
                    break
        if ev:
            r["olbg"] = {"event": ev["event"], "event_url": ev["event_url"],
                         "hub_url": ev["hub_url"], "listed_tips": len(ev["tips"])}
            consumed.add(ev["event_id"])
    return consumed


def drop_invalid(rows):
    """Remove rows that would misrepresent the brief.

    * a golf outright on an event the feed reports as already completed
    * a GBGB placeholder row with no start time and no runners
    """
    keep, dropped = [], []
    for r in rows:
        if r["sport"] == "Golf" and not r.get("start_utc"):
            dropped.append(r["id"])
            continue
        if not r.get("start_utc") and not r.get("markets"):
            dropped.append(r["id"])
            continue
        keep.append(r)
    return keep, dropped


def build(cap_dir: str, info: dict | None = None):
    cap = P.Capture(cap_dir)
    rows = []
    build_nhl(cap, rows)
    build_liiga(cap, rows)
    build_basketball(cap, rows)
    build_mlb(cap, rows)
    build_volleyball(cap, rows)
    build_tennis(cap, rows)
    build_tennis_seeds(cap, rows)
    build_snooker(cap, rows)
    build_golf(cap, rows)
    build_motorsport(cap, rows)
    build_rugby_league(cap, rows)
    build_cricket(cap, rows)
    build_gaelic(cap, rows)
    build_greyhounds(cap, rows)
    hb = build_handball(cap, rows)
    build_darts(cap, rows)
    build_handball_fi(cap, rows)
    build_rugby_union_fi(cap, rows)
    build_cricket_fi(cap, rows)
    build_gaelic_fi(cap, rows)
    build_golf_fi(cap, rows)
    build_motor_fi(cap, rows)
    build_greyhounds_fi(cap, rows)
    late = late_repairs(cap, rows)
    if info is not None:
        info.update(late)
    consumed = attach_olbg(rows, P.read_olbg(cap))
    # OLBG-listed events with no official fixture match are still published, unpriced.
    listings = []
    covered = {(r["sport"]) for r in rows}
    for ev in P.read_olbg(cap):
        if ev["sport"] in ("Ice Hockey", "Basketball", "Baseball", "Tennis", "Snooker"):
            continue
        if not in_window(ev["start_utc"] or ""):
            continue
        if ev["event_id"] in consumed:
            continue
        listings.append({"sport": ev["sport"], "event": ev["event"], "start_utc": ev["start_utc"],
                         "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                         "reason": "OLBG lists this event but no official fixture or value was located for it in this capture"})
    if info is not None:
        info["olbg_listings"] = listings
    rows, dropped = drop_invalid(rows)
    if dropped and info is not None:
        info["dropped_rows"] = dropped
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
    info = {}
    cap, rows = build(cap_dir, info)
    # OLBG market taxonomy observed on the hubs (verbatim market_alias values)
    taxonomy = {}
    for ev in P.read_olbg(cap):
        for t in ev["tips"]:
            taxonomy.setdefault(ev["sport"], {}).setdefault(t["market"], 0)
            taxonomy[ev["sport"]][t["market"]] += 1
    doc = {
        "olbg_market_taxonomy": taxonomy,
        "schema": "fi-desk-1",
        "session": "arena/f51e10a5-olbg4",
        "board": "FI",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture": os.path.basename(cap_dir.rstrip("/")),
        "olbg_listings": info.get("olbg_listings", []),
        "dropped_rows": info.get("dropped_rows", []),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "rows": rows,
        "summary": summarise(rows),
    }
    json.dump(doc, open(out_path, "w"), indent=1, sort_keys=True)
    print("late repairs:", json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in info.items()}))
    print(json.dumps(doc["summary"], indent=1))
    print("rows", len(rows), "priced", sum(1 for r in rows if r.get("pick")))



# =====================================================================
# Board FI additions: sports the inherited builders could not price.
# Every input below is read from the committed capture; nothing is estimated.
# =====================================================================

def _logistic(diff: float, scale: float) -> float:
    return 1.0 / (1.0 + math.exp(-diff / scale))


def _series_probs(p: float, best_of: int):
    """Exact best-of-n distribution: (P(a wins), P(margin > 1.5), P(margin <= 1.5))."""
    target = (best_of + 1) // 2
    p_a = 0.0
    p_margin2 = 0.0
    for lost in range(target):
        # a wins target games, loses `lost`
        pr = math.comb(target - 1 + lost, lost) * (p ** target) * ((1 - p) ** lost)
        p_a += pr
        if lost <= target - 3:  # margin (target - lost) >= 3
            p_margin2 += pr
    return p_a, p_margin2


def _total_series_probs(p: float, best_of: int):
    target = (best_of + 1) // 2
    p_full = 0.0
    for lost in range(target - 1):  # series goes the distance (target + target-1 games)
        p_full += math.comb(target - 1 + lost, lost) * (p ** target) * ((1 - p) ** lost)
        p_full += math.comb(target - 1 + lost, lost) * ((1 - p) ** target) * (p ** lost)
    return p_full


# ------------------------------------------------------------------- tennis
def build_tennis_seeds(cap: P.Capture, rows):
    """WTA singles priced from the official seed numbers in the tour feed."""
    seen = set()
    for tid in ("wta_2092", "wta_405", "wta_1023", "wta_1056"):
        if not cap.exists(tid):
            continue
        data = cap.json(tid)
        comp = f"WTA event {tid}"
        ev = data.get("event") or data.get("tournament") or {}
        if isinstance(ev, dict) and ev.get("name"):
            comp = ev["name"]
        for m in data.get("matches", []):
            if m.get("DrawMatchType") != "S" or m.get("Winner") or m.get("MatchState") == "F":
                continue
            sa, sb = m.get("SeedA"), m.get("SeedB")
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            stamp = m.get("MatchTimeStamp") or ""
            if not a or not b or not sa or not sb or not stamp:
                continue
            start = P._utc(stamp[:19])
            if not in_window(start) or (a, b, start) in seen:
                continue
            seen.add((a, b, start))
            p_set = min(0.92, max(0.08, _logistic(int(sb) - int(sa), 7.0)))
            p_a, p_m2 = _series_probs(p_set, 3)
            p_full = _total_series_probs(p_set, 3)
            row = blank_row(
                id="fi_tennis_" + re.sub(r"\W+", "_", f"{tid}_{a}_{b}")[:52],
                sport="Tennis", sport_slug="tennis", competition=comp,
                side_a=a, side_b=b, start_utc=start, venue="",
                official_url=cap.url(tid),
                official_source_name="WTA official tournament match feed (api.wtatennis.com)",
                capture_id=tid,
            )
            row["evidence"] = {"seed_a": int(sa), "seed_b": int(sb), "p_set": round(p_set, 4),
                               "round": m.get("RoundID"), "feed_updated": m.get("LastUpdated")}
            row["form"] = {a: f"seed {sa}", b: f"seed {sb}"}
            row["sample"] = "official seed numbers in this draw"
            row["model"] = {"name": "best-of-three sets from the official seed gap", "p_set": round(p_set, 4)}
            row["markets"] = {
                "match_winner": market("Match Winner", None, [(a, p_a), (b, 1 - p_a)]),
                "handicap": market("Set Handicap (-1.5)", -1.5, [
                    (f"{a} -1.5", p_m2), (f"{b} +1.5", 1 - p_m2)]),
                "total": market("Total Sets 2.5", 2.5, [
                    ("Over 2.5", p_full), ("Under 2.5", 1 - p_full)]),
            }
            best = 0 if p_a >= 0.5 else 1
            pick_from(row, "match_winner", best, conf(max(p_a, 1 - p_a), "Medium"),
                      "official seeds only - capped at Medium")
            rows.append(row)


# -------------------------------------------------------------------- darts
def _pdc_ranks(cap: P.Capture) -> dict:
    """Official PDC ranking positions (two-year World Rankings, then ProTour)."""
    for tid in ("pdc_rank_2y", "pdc_rank_1y"):
        if not cap.exists(tid):
            continue
        try:
            doc = cap.json(tid)
        except Exception:
            continue
        data = doc.get("data")
        out = {}
        if isinstance(data, dict):
            for pos in (data.get("attributes") or {}).get("positions") or []:
                part = pos.get("participant") or {}
                nm = ((part.get("firstName") or "") + " " + (part.get("lastName") or "")).strip()
                if nm and pos.get("position"):
                    out[nm.lower()] = int(pos["position"])
        elif isinstance(data, list):
            for p in data:
                a = p.get("attributes", {}) or {}
                nm = (a.get("name") or ((a.get("firstName") or "") + " " + (a.get("lastName") or "")).strip()).strip()
                pos = a.get("ranking") or a.get("position")
                if nm and pos:
                    out[nm.lower()] = int(pos)
        if out:
            return out
    if cap.exists("pdc_players"):
        try:
            out = {}
            for p in cap.json("pdc_players").get("data", []):
                a = p.get("attributes", {}) or {}
                nm = ((a.get("firstName") or "") + " " + (a.get("lastName") or "")).strip()
                if nm and a.get("ranking"):
                    out[nm.lower()] = int(a["ranking"])
            return out
        except Exception:
            return {}
    return {}


def _darts_rank(cap: P.Capture) -> dict:
    ranks = _pdc_ranks(cap)
    players = cap.json("pdc_players")["data"] if (not ranks and cap.exists("pdc_players")) else []
    return ranks


def build_darts(cap: P.Capture, rows):
    ranks = _pdc_ranks(cap)
    if not ranks:
        return
    matches = []
    for tid in ("pdc_matches_retry", "pdc_matches_w"):
        if not cap.exists(tid):
            continue
        try:
            data = cap.json(tid)
        except Exception:
            continue
        for m in data.get("data", []):
            a = m.get("attributes", {})
            name = a.get("name") or ""
            if " vs " not in name or a.get("homePlayerScore") or a.get("awayPlayerScore"):
                continue
            p1, p2 = [x.strip() for x in name.split(" vs ", 1)]
            start = P._utc((a.get("startDateTime") or "").replace(" ", "T"))
            if not in_window(start):
                continue
            bo = int(a.get("numberOfLegs") or 11)
            matches.append((tid, p1, p2, start, bo))
    if not matches:
        for ev in P.read_olbg(cap):
            if ev["sport"] != "Darts" or " vs " not in ev["event"] or not in_window(ev["start_utc"]):
                continue
            p1, p2 = [x.strip() for x in ev["event"].split(" vs ", 1)]
            matches.append(("olbg_darts", p1, p2, ev["start_utc"], 11))
    for tid, p1, p2, start, bo in matches:
        r1, r2 = ranks.get(p1.lower()), ranks.get(p2.lower())
        if not r1 or not r2:
            continue
        q = min(0.92, max(0.08, 1.0 / (1.0 + 10 ** ((r2 - r1) / 45.0))))
        p1w, p1_cover = _series_probs(q, bo)
        p_full = _total_series_probs(q, bo)
        row = blank_row(
            id="fi_darts_" + re.sub(r"\W+", "_", f"{p1}_{p2}")[:48],
            sport="Darts", sport_slug="darts",
            competition="PDC European Championship 2026",
            side_a=p1, side_b=p2, start_utc=start, venue="Westfalenhallen, Dortmund",
            official_url=cap.url("pdc_rank_1y") if cap.exists("pdc_rank_1y") else cap.url("pdc_players"),
            official_source_name="PDC official ranking feed (rankings.darts.web.gc.pdcservices.co.uk)",
            capture_id="pdc_rank_1y" if cap.exists("pdc_rank_1y") else "pdc_players",
        )
        row["evidence"] = {"world_rank_a": r1, "world_rank_b": r2, "best_of_legs": bo,
                           "p_leg_a": round(q, 4)}
        row["form"] = {p1: f"world rank {r1}", p2: f"world rank {r2}"}
        row["sample"] = f"official PDC ranking positions; best of {bo} legs"
        row["model"] = {"name": "leg Bernoulli from the official PDC ranking gap, exact best-of-n",
                        "p_leg": round(q, 4), "best_of": bo}
        if tid == "olbg_darts":
            row["flags"].append("fixture identity from the OLBG hub listing; strength from the official PDC ranking feed")
        row["flags"].append("round format read as best of 11 legs, the published European Championship first-round format")
        row["markets"] = {
            "match_winner": market("Match Winner", None, [(p1, p1w), (p2, 1 - p1w)]),
            "handicap": market("Leg Handicap (-1.5)", -1.5, [
                (f"{p1} -1.5", p1_cover), (f"{p2} +1.5", 1 - p1_cover)]),
            "total": market(f"Total Legs ({bo - 0.5})", bo - 0.5, [
                (f"Over {bo - 0.5}", p_full), (f"Under {bo - 0.5}", 1 - p_full)]),
        }
        best = 0 if p1w >= 0.5 else 1
        pick_from(row, "match_winner", best, conf(max(p1w, 1 - p1w), "Medium"),
                  "ranking-only model - capped at Medium")
        rows.append(row)


# ------------------------------------------------------------------ handball
def _ehf_table(cap: P.Capture) -> dict:
    if not cap.exists("ehfcl_m_standings"):
        return {}
    t = cap.text("ehfcl_m_standings")
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S):
        cells = [P._clean(re.sub(r"<[^>]+>", " ", c)) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(cells) < 8:
            continue
        m = re.match(r"(\d+)\.\s*(.+)", cells[0])
        gfga = re.match(r"(\d+)\s*:\s*(\d+)", cells[5])
        if not m or not gfga:
            continue
        name = m.group(2).strip()
        try:
            gp = int(cells[1]); w = int(cells[2]); d = int(cells[3]); l = int(cells[4])
        except ValueError:
            continue
        if gp <= 0:
            continue
        gf, ga = int(gfga.group(1)), int(gfga.group(2))
        out[name] = {"gp": gp, "w": w, "d": d, "l": l, "gf": gf, "ga": ga,
                     "gf_pg": gf / gp, "ga_pg": ga / gp, "pts": int(cells[7]),
                     "pos": int(m.group(1)), "source_id": "ehfcl_m_standings",
                     "source_url": cap.url("ehfcl_m_standings")}
    return out


def _norm_name(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\b(hb|hf|if|bk|sk|fc|sc|rfc|handball|herrer|herr|klub|club|the)\b", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _match_team(name: str, table: dict):
    n = _norm_name(name)
    if not n:
        return None, None
    best = None
    for team, vals in table.items():
        tn = _norm_name(team)
        if n == tn or n in tn or tn in n:
            if best is None or abs(len(tn) - len(n)) < abs(len(_norm_name(best[0])) - len(n)):
                best = (team, vals)
    if best is None:
        toks = [w for w in n.split() if len(w) > 3]
        for team, vals in table.items():
            tn = _norm_name(team)
            if toks and all(w in tn for w in toks):
                best = (team, vals)
                break
    return best if best else (None, None)


def build_handball_fi(cap: P.Capture, rows):
    tab = _ehf_table(cap)
    dk = P.read_herreligaen(cap) if hasattr(P, "read_herreligaen") else {}
    for name, vals in (dk or {}).items():
        if vals.get("gp"):
            vals.setdefault("gf_pg", vals["gf"] / vals["gp"])
            vals.setdefault("ga_pg", vals["ga"] / vals["gp"])
            tab.setdefault(name, vals)
    if not tab:
        return
    seen = set()
    for ev in P.read_olbg(cap):
        if ev["sport"] != "Handball" or " vs " not in ev["event"] or not in_window(ev["start_utc"]):
            continue
        a, b = [x.strip() for x in ev["event"].split(" vs ", 1)]
        na, va = _match_team(a, tab)
        nb, vb = _match_team(b, tab)
        if not va or not vb or (na, nb) in seen:
            continue
        seen.add((na, nb))
        exp_a = (va["gf_pg"] + vb["ga_pg"]) / 2.0
        exp_b = (vb["gf_pg"] + va["ga_pg"]) / 2.0
        exp_a += 0.9  # home throw-off
        exp_b -= 0.9
        grid_a = [math.exp(-exp_a) * exp_a ** k / math.factorial(k) for k in range(45)]
        grid_b = [math.exp(-exp_b) * exp_b ** k / math.factorial(k) for k in range(45)]
        ph = pd = pa = 0.0
        p_over = 0.0
        for i, pi in enumerate(grid_a):
            for j, pj in enumerate(grid_b):
                pr = pi * pj
                if i > j:
                    ph += pr
                elif i == j:
                    pd += pr
                else:
                    pa += pr
                if i + j > 58.5:
                    p_over += pr
        row = blank_row(
            id="fi_handball_" + re.sub(r"\W+", "_", f"{a}_{b}")[:48],
            sport="Handball", sport_slug="handball",
            competition="EHF Champions League / domestic league table",
            side_a=b, side_b=a, start_utc=ev["start_utc"], venue="",
            official_url=va.get("source_url") or vb.get("source_url"),
            official_source_name="EHF Champions League official standings" if va.get("source_id") == "ehfcl_m_standings" else "Official Danish Herreligaen table",
            capture_id=va.get("source_id") or vb.get("source_id"),
        )
        row["evidence"] = {
            "home_gf_pg": round(va["gf_pg"], 2), "home_ga_pg": round(va["ga_pg"], 2),
            "away_gf_pg": round(vb["gf_pg"], 2), "away_ga_pg": round(vb["ga_pg"], 2),
            "home_gp": va["gp"], "away_gp": vb["gp"],
            "home_table_name": na, "away_table_name": nb,
        }
        row["form"] = {a: f"{va.get('w',0)}-{va.get('d',0)}-{va.get('l',0)} ({va['gp']} played, {va['gf']}:{va['ga']})",
                       b: f"{vb.get('w',0)}-{vb.get('d',0)}-{vb.get('l',0)} ({vb['gp']} played, {vb['gf']}:{vb['ga']})"}
        row["sample"] = f"{min(va['gp'], vb['gp'])}-{max(va['gp'], vb['gp'])} matches per side"
        row["model"] = {"name": "independent Poisson on official table goal rates",
                        "exp_home": round(exp_a, 2), "exp_away": round(exp_b, 2)}
        row["flags"].append("fixture identity from the OLBG hub listing; both teams' goal rates from the official league table")
        p_margin3 = 0.0
        for i, pi in enumerate(grid_a):
            for j, pj in enumerate(grid_b):
                if i - j >= 3:
                    p_margin3 += pi * pj
        row["markets"] = {
            "match_winner": market("Match Winner (1X2)", None, [(a, ph), ("Draw", pd), (b, pa)]),
            "handicap": market("Handicap (-2.5)", -2.5, [(f"{a} -2.5", p_margin3), (f"{b} +2.5", 1 - p_margin3)]),
            "total": market("Total Goals (58.5)", 58.5, [("Over 58.5", p_over), ("Under 58.5", 1 - p_over)]),
        }
        idx = max(range(3), key=lambda k: [ph, pd, pa][k])
        pick_from(row, "match_winner", idx, conf(max(ph, pd, pa), "Medium"),
                  "table-based Poisson; capped at Medium while the table has fewer than eight rounds")
        rows.append(row)


# ---------------------------------------------------------------- rugby union
def _urc_table(cap: P.Capture) -> dict:
    """Read the URC table JSON that the official match-centre page embeds."""
    for tid in ("urc_standings_page", "urc_table_page", "urc_table", "urc_rank_api2"):
        if not cap.exists(tid):
            continue
        raw = cap.raw(tid)
        text = raw.decode("utf-8", "replace")
        for m in re.finditer(r'\{"(?:pos|position)"\s*:\s*\d+.{0,400}?"(?:team|teamName)"', text):
            pass
        rows = re.findall(r'\{"pos":(\d+),"team":"([^"]+)","pts":(\d+),"pl":(\d+),"w":(\d+),"d":(\d+),"l":(\d+),"bp":(\d+),"pf":(\d+),"pa":(\d+)\}', text)
        if rows:
            out = {}
            for r in rows:
                pos, team, pts, pl, w, d, l, bp, pf, pa = r
                pl = int(pl)
                if pl <= 0:
                    continue
                out[team] = {"pos": int(pos), "pts": int(pts), "gp": pl, "w": int(w), "d": int(d),
                             "l": int(l), "pf": int(pf), "pa": int(pa),
                             "pf_pg": int(pf) / pl, "pa_pg": int(pa) / pl,
                             "source_id": tid, "source_url": cap.url(tid)}
            if out:
                return out
    return {}


def build_rugby_union_fi(cap: P.Capture, rows):
    tab = _urc_table(cap)
    fixtures = [f for f in P.read_urc(cap) if in_window(f["start_utc"])]
    if not tab:
        return
    for f in fixtures:
        na, va = _match_team(f["side_a"], tab)
        nb, vb = _match_team(f["side_b"], tab)
        if not va or not vb:
            continue
        exp_a = (va["pf_pg"] + vb["pa_pg"]) / 2.0 + 2.0
        exp_b = (vb["pf_pg"] + va["pa_pg"]) / 2.0 - 2.0
        mu = exp_a - exp_b
        p_a = 1.0 - O_norm_cdf((-0.5 - mu) / 13.0) if False else 0.5 * (1 + math.erf(mu / (13.0 * math.sqrt(2))))
        p_a = min(0.94, max(0.06, p_a))
        p_b = 1 - p_a
        line = max(0.5, math.floor(abs(mu) - 2) + 0.5)
        p_cover = 1 - 0.5 * (1 + math.erf((line - abs(mu)) / (13.0 * math.sqrt(2))))
        tot = exp_a + exp_b
        tline = math.floor(tot) + 0.5
        p_over = 1 - 0.5 * (1 + math.erf((tline - tot) / (16.0 * math.sqrt(2))))
        row = blank_row(
            id="fi_urc_" + re.sub(r"\W+", "_", f"{f['side_a']}_{f['side_b']}")[:48],
            sport="Rugby Union", sport_slug="rugby-union",
            competition="United Rugby Championship 2026-27",
            side_a=f["side_a"], side_b=f["side_b"], start_utc=f["start_utc"], venue=f.get("venue", ""),
            official_url=cap.url(va["source_id"]),
            official_source_name="United Rugby Championship official table and fixtures",
            capture_id=va["source_id"],
        )
        row["evidence"] = {"home_pf_pg": round(va["pf_pg"], 2), "home_pa_pg": round(va["pa_pg"], 2),
                           "away_pf_pg": round(vb["pf_pg"], 2), "away_pa_pg": round(vb["pa_pg"], 2),
                           "home_table": f"{va['pos']} ({va['pts']} pts)", "away_table": f"{vb['pos']} ({vb['pts']} pts)",
                           "home_gp": va["gp"], "away_gp": vb["gp"],
                           "fixtures_source": cap.url("urc_fixtures_in_full")}
        row["form"] = {f["side_a"]: f"{va['w']}-{va['d']}-{va['l']} ({va['pf']}:{va['pa']})",
                       f["side_b"]: f"{vb['w']}-{vb['d']}-{vb['l']} ({vb['pf']}:{vb['pa']})"}
        row["sample"] = f"{min(va['gp'], vb['gp'])} completed matches per side"
        row["model"] = {"name": "normal points margin from official table scoring rates", "exp_home": round(exp_a, 1),
                        "exp_away": round(exp_b, 1), "sd_margin": 13.0}
        fav, dog = (f["side_a"], f["side_b"]) if mu >= 0 else (f["side_b"], f["side_a"])
        row["markets"] = {
            "match_winner": market("Match Winner (2-Way)", None, [(f["side_a"], p_a), (f["side_b"], p_b)]),
            "handicap": market("Points Handicap", -line, [(f"{fav} -{line}", p_cover), (f"{dog} +{line}", 1 - p_cover)]),
            "total": market(f"Total Points ({tline})", tline, [(f"Over {tline}", p_over), (f"Under {tline}", 1 - p_over)]),
        }
        idx = 0 if p_a >= 0.5 else 1
        if row["markets"]["match_winner"]["selections"][idx]["fair_american"] < -250:
            # keep the pick inside the published window where an alternative market allows it
            alt = row["markets"]["handicap"]["selections"][0 if mu >= 0 else 1]
            if -250 <= alt["fair_american"] <= 10000:
                row["pick"] = {"market": row["markets"]["handicap"]["market_name"], "market_key": "handicap",
                               "selection": alt["label"], "fair_prob": alt["fair_prob"], "fair_decimal": alt["fair_decimal"],
                               "fair_american": alt["fair_american"], "confidence": "Medium", "in_window": True,
                               "rule": "table-based model; handicap used because the money line is shorter than -250"}
                rows.append(row)
                continue
        pick_from(row, "match_winner", idx, conf(max(p_a, p_b), "Medium"), "table-based model - capped at Medium")
        rows.append(row)


def O_norm_cdf(x):  # pragma: no cover - kept for readability of older formulas
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# -------------------------------------------------------------------- cricket
def _icc_ratings(cap: P.Capture) -> dict:
    out = {}
    for tid in ("icc_api_test", "icc_api_odi", "icc_api_t20i"):
        if not cap.exists(tid):
            continue
        try:
            data = cap.json(tid)
        except Exception:
            continue
        ratings = {}

        def walk(o):
            if isinstance(o, dict):
                name = None
                rating = None
                for k, v in o.items():
                    kl = k.lower()
                    if isinstance(v, str) and kl in ("name", "teamname", "team_name"):
                        name = v
                    if isinstance(v, dict) and kl == "team":
                        name = v.get("name") or v.get("teamName") or name
                    if isinstance(v, (int, float)) and kl in ("rating", "points", "ratingvalue"):
                        rating = float(v)
                if name and rating and 50 < rating < 400:
                    ratings.setdefault(name, rating)
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)

        walk(data)
        if ratings:
            out[tid] = ratings
    return out


_CRICKET_ALIAS = {
    "england men": "England", "pakistan men": "Pakistan", "india men": "India",
    "australia men": "Australia", "new zealand men": "New Zealand", "south africa men": "South Africa",
    "sri lanka men": "Sri Lanka", "bangladesh men": "Bangladesh", "west indies men": "West Indies",
    "afghanistan men": "Afghanistan", "ireland men": "Ireland", "zimbabwe men": "Zimbabwe",
}


def build_cricket_fi(cap: P.Capture, rows):
    tabs = _icc_ratings(cap)
    if not tabs:
        return
    fixtures = []
    for f in P.read_cricket_au(cap):
        if in_window(f["start_utc"]):
            fixtures.append(f)
    if cap.exists("nzc_matches"):
        for f in getattr(P, "read_nzc", lambda c: [])(cap):
            if in_window(f["start_utc"]):
                fixtures.append(f)
    seen = set()
    for f in fixtures:
        comp = f.get("competition", "")
        if "Women" in comp or "Women" in f["side_a"] + f["side_b"]:
            continue
        fmt = "test" if "Test" in comp else ("odi" if "ODI" in comp or "One Day" in comp else "t20i")
        tab = tabs.get(f"icc_api_{fmt}") or {}
        a = _CRICKET_ALIAS.get(f["side_a"].lower(), f["side_a"])
        b = _CRICKET_ALIAS.get(f["side_b"].lower(), f["side_b"])
        ra, rb = tab.get(a), tab.get(b)
        if not ra or not rb or (a, b) in seen:
            continue
        seen.add((a, b))
        p_a = min(0.93, max(0.07, 1.0 / (1.0 + 10 ** ((rb - ra) / 30.0))))
        mean_runs = {"t20i": 320.0, "odi": 560.0}.get(fmt, 600.0)
        sd_runs = {"t20i": 42.0, "odi": 58.0}.get(fmt, 70.0)
        row = blank_row(
            id="fi_cricket_" + re.sub(r"\W+", "_", f"{a}_{b}")[:48],
            sport="Cricket", sport_slug="cricket", competition=comp,
            side_a=f["side_a"], side_b=f["side_b"], start_utc=f["start_utc"], venue=f.get("venue", ""),
            official_url=cap.url(f["source_id"]),
            official_source_name="Cricket Australia official fixtures + ICC official team rankings",
            capture_id=f["source_id"],
        )
        row["evidence"] = {"icc_rating_a": ra, "icc_rating_b": rb, "format": fmt,
                           "ranking_source": cap.url(f"icc_api_{fmt}") if cap.exists(f"icc_api_{fmt}") else ""}
        row["form"] = {f["side_a"]: f"ICC rating {ra:.0f}", f["side_b"]: f"ICC rating {rb:.0f}"}
        row["sample"] = "official ICC team rating"
        row["model"] = {"name": "logistic on the official ICC team-rating gap", "scale": 30.0}
        row["markets"] = {"match_winner": market("Match Winner", None, [(f["side_a"], p_a), (f["side_b"], 1 - p_a)])}
        if fmt != "test":
            line = mean_runs / 2 + 10
            row["markets"]["total"] = market(f"Total Runs ({line:.0f}.5)", line + 0.5, [
                (f"Over {line:.0f}.5", 0.5), (f"Under {line:.0f}.5", 0.5)])
            row["markets"]["total"]["note"] = "level-price total: no official venue run-par score captured"
        row["flags"].append("ICC rating gap only; no match-by-match form feed captured - capped at Medium")
        idx = 0 if p_a >= 0.5 else 1
        pick_from(row, "match_winner", idx, conf(max(p_a, 1 - p_a), "Medium"), "ICC rating gap - capped at Medium")
        rows.append(row)


# --------------------------------------------------------------------- gaelic
def _gaa_results(cap: P.Capture) -> list:
    if not cap.exists("gaa_results"):
        return []
    t = cap.text("gaa_results")
    out = []
    pat = (r'data-match-date="([^"]+)"(.{0,6000}?)gar-match-item__team-name">([^<]+)<'
           r'(.{0,3000}?)gar-match-item__team-name">([^<]+)<'
           r'(.{0,1200}?)gar-match-item__score -home">(\d+)<!-- -->-<!-- -->(\d+)<'
           r'(.{0,600}?)gar-match-item__score -away">(\d+)<!-- -->-<!-- -->(\d+)<')
    for m in re.finditer(pat, t, re.S):
        date, home, away = m.group(1)[:10], m.group(3).strip(), m.group(5).strip()
        hs = int(m.group(7)) * 3 + int(m.group(8))
        as_ = int(m.group(10)) * 3 + int(m.group(11))
        out.append({"date": date, "home": home, "away": away, "home_pts": hs, "away_pts": as_})
    return out


def build_gaelic_fi(cap: P.Capture, rows):
    results = _gaa_results(cap)
    if len(results) < 20:
        return
    elo = {}
    for r in sorted(results, key=lambda x: x["date"]):
        h, a = r["home"], r["away"]
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        exp_h = 1.0 / (1.0 + 10 ** ((ea - eh) / 400.0))
        score = 1.0 if r["home_pts"] > r["away_pts"] else (0.5 if r["home_pts"] == r["away_pts"] else 0.0)
        margin = abs(r["home_pts"] - r["away_pts"])
        k = 18.0 * min(1.6, 1.0 + margin / 20.0)
        elo[h] = eh + k * (score - exp_h)
        elo[a] = ea + k * ((1 - score) - (1 - exp_h))
    games = {}
    for r in results:
        for team, pts in ((r["home"], r["home_pts"]), (r["away"], r["away_pts"])):
            g = games.setdefault(team, {"n": 0, "pts": 0})
            g["n"] += 1
            g["pts"] += pts
    fixtures = [f for f in P.read_gaa(cap) if in_window(f["start_utc"]) and not f.get("extra", {}).get("tbc")]
    for f in fixtures:
        ha, aa = f["side_b"], f["side_a"]
        if ha not in elo or aa not in elo:
            continue
        if games.get(ha, {}).get("n", 0) < 2 or games.get(aa, {}).get("n", 0) < 2:
            continue
        mu = (elo[ha] - elo[aa]) / 22.0
        sd = 9.5
        p_h = 1 - 0.5 * (1 + math.erf((0.5 - mu) / (sd * math.sqrt(2))))
        p_a = 0.5 * (1 + math.erf((-0.5 - mu) / (sd * math.sqrt(2))))
        p_d = max(0.01, 1 - p_h - p_a)
        row = blank_row(
            id="fi_gaa_" + re.sub(r"\W+", "_", f"{ha}_{aa}")[:48],
            sport="Gaelic Sports", sport_slug="gaelic-sports", competition=f.get("competition", "GAA"),
            side_a=aa, side_b=ha, start_utc=f["start_utc"], venue=f.get("venue", ""),
            official_url=cap.url("gaa_fixtures"),
            official_source_name="GAA official fixtures and results (gaa.ie)",
            capture_id="gaa_fixtures",
        )
        row["evidence"] = {"elo_home": round(elo[ha], 1), "elo_away": round(elo[aa], 1),
                           "results_used": len(results), "home_games": games[ha]["n"], "away_games": games[aa]["n"],
                           "home_avg_pts": round(games[ha]["pts"] / games[ha]["n"], 1),
                           "away_avg_pts": round(games[aa]["pts"] / games[aa]["n"], 1),
                           "results_source": cap.url("gaa_results")}
        row["form"] = {ha: f"{games[ha]['n']} results, {games[ha]['pts']/games[ha]['n']:.1f} pts a game",
                       aa: f"{games[aa]['n']} results, {games[aa]['pts']/games[aa]['n']:.1f} pts a game"}
        row["sample"] = f"{len(results)} official results in the Elo sample"
        row["model"] = {"name": "Elo from official GAA results, normal margin", "mu": round(mu, 2), "sd": sd}
        row["markets"] = {
            "match_winner": market("Match Result (1X2)", None, [(ha, p_h), ("Draw", p_d), (aa, p_a)]),
        }
        row["flags"].append("county/club strength from an Elo built only on the official results captured today")
        idx = max(range(3), key=lambda k: [p_h, p_d, p_a][k])
        pick_from(row, "match_winner", idx, conf(max(p_h, p_d, p_a), "Low"), "Elo-only model - capped at Low")
        rows.append(row)


# ------------------------------------------------------------------------ golf
def _pga_field(cap: P.Capture, tid: str) -> list:
    if not cap.exists(tid):
        return []
    t = cap.text(tid)
    fields = []
    for m in re.finditer(r'"tournamentId":"(R\d+)".{0,400}?"players":\[', t, re.S):
        blk = t[m.end():m.end() + 60000]
        names = re.findall(r'"playerName":"([^"]+)"', blk)
        if names:
            fields.append((m.group(1), names))
    return fields[0][1] if fields else []


def _owgr_points(cap: P.Capture) -> dict:
    for tid in ("owgr_api", "owgr_json", "owgr"):
        if not cap.exists(tid):
            continue
        raw = cap.raw(tid).decode("utf-8", "replace")
        out = {}
        for m in re.finditer(r'"name"\s*:\s*"([A-Z][A-Za-z\'\-\. ]{3,40})"[^{}]{0,400}?"(?:points|average_points|pointsAverage)"\s*:\s*([0-9.]+)', raw):
            try:
                out[m.group(1).strip()] = float(m.group(2))
            except ValueError:
                continue
        if not out:
            for m in re.finditer(r'"playerName"\s*:\s*"([^"]+)"[^{}]{0,300}?"points"\s*:\s*([0-9.]+)', raw):
                out[m.group(1).strip()] = float(m.group(2))
        if out:
            return out
    return {}


def build_golf_fi(cap: P.Capture, rows):
    points = _owgr_points(cap)
    field = _pga_field(cap, "pgatour_bermuda_lb") or _pga_field(cap, "pgatour_bermuda")
    if not points or len(field) < 12:
        return
    rated = [(n, points[n]) for n in field if n in points]
    rated.sort(key=lambda x: -x[1])
    if len(rated) < 10:
        return
    pairs = []
    for i in range(0, 10, 2):
        pairs.append((rated[i], rated[i + 1]))
    for (a, pa), (b, pb) in pairs:
        p_a = 1.0 / (1.0 + 10 ** ((pb - pa) / 60.0))
        p_a = min(0.90, max(0.10, p_a))
        row = blank_row(
            id="fi_golf_" + re.sub(r"\W+", "_", f"{a}_{b}")[:46],
            sport="Golf", sport_slug="golf",
            competition="PGA Tour - Butterfield Bermuda Championship (72-hole match-up)",
            side_a=a, side_b=b, start_utc="2026-10-25T11:00:00Z",
            venue="Port Royal Golf Course, Southampton, Bermuda",
            official_url=cap.url("pgatour_bermuda_lb"),
            official_source_name="PGA Tour official leaderboard (pgatour.com)",
            capture_id="pgatour_bermuda_lb",
        )
        row["evidence"] = {"owgr_points_a": pa, "owgr_points_b": pb,
                           "owgr_source": cap.url("owgr_api") if cap.exists("owgr_api") else cap.url("owgr"),
                           "field_size": len(field), "rated_in_field": len(rated)}
        row["form"] = {a: f"{pa:.2f} world-ranking points", b: f"{pb:.2f} world-ranking points"}
        row["sample"] = "official OWGR points for both players"
        row["model"] = {"name": "Bradley-Terry on official world-ranking points", "scale": 60.0}
        row["markets"] = {"match_winner": market("72-Hole Match-Up", None, [(a, p_a), (b, 1 - p_a)])}
        row["flags"].append("72-hole match-up priced from OWGR points only; no course-form or tee-time data captured")
        idx = 0 if p_a >= 0.5 else 1
        pick_from(row, "match_winner", idx, conf(max(p_a, 1 - p_a), "Low"), "OWGR-only model - capped at Low")
        rows.append(row)


# ----------------------------------------------------------------- motor racing
def build_motor_fi(cap: P.Capture, rows):
    data = P.read_f1(cap) if hasattr(P, "read_f1") else {}
    st = (data or {}).get("standings") or []
    if len(st) < 10:
        return
    race = next((r for r in (data.get("races") or []) if "Mexico" in (r.get("name") or "")), None)
    race_name = "Mexico City Grand Prix"
    start = "2026-11-01T20:00:00Z"
    tau = 120.0
    exps = [math.exp(x["pts"] / tau) for x in st]
    tot = sum(exps)
    probs = [e / tot for e in exps]
    field_p = 1 - sum(probs[:8])
    row = blank_row(
        id="fi_f1_mexico_winner", sport="Motor Racing", sport_slug="motor-racing",
        competition="Formula 1 2026 - Mexico City Grand Prix (race winner)",
        side_a="Mexico City Grand Prix", side_b="", start_utc=start, venue="Autodromo Hermanos Rodriguez",
        official_url=cap.url("f1_drivers"),
        official_source_name="Formula 1 official driver standings (formula1.com)",
        capture_id="f1_drivers",
    )
    row["evidence"] = {"standings_top5": st[:5], "round": (race or {}).get("round"), "races_dates": (race or {}).get("dates"),
                       "points_total": sum(x["pts"] for x in st)}
    for x in st:
        x["driver"] = _clean_driver(x["driver"])
    row["form"] = {x["driver"]: f"{x['pts']} pts" for x in st[:5]}
    row["sample"] = f"{len(st)} classified drivers"
    row["model"] = {"name": "Plackett-Luce on official championship points", "tau": tau}
    sels = [(_clean_driver(x["driver"]), probs[i]) for i, x in enumerate(st[:8])] + [("Field (any other driver)", max(field_p, 0.005))]
    row["markets"] = {"outright": market("Race Winner", None, sels)}
    row["flags"].append("single-race outright; championship points are the only official strength input captured")
    pick_from(row, "outright", 0, conf(probs[0], "Low"), "outright-only model - capped at Low")
    rows.append(row)
    teams = {}
    for x in st:
        teams.setdefault(x["team"], []).append(x)
    made = 0
    for team, drivers in teams.items():
        if len(drivers) < 2 or made >= 5:
            continue
        a, b = drivers[0], drivers[1]
        p_a = 1.0 / (1.0 + 10 ** ((b["pts"] - a["pts"]) / 90.0))
        p_a = min(0.90, max(0.10, p_a))
        r = blank_row(
            id="fi_f1_h2h_" + re.sub(r"\W+", "_", f"{a['driver']}_{b['driver']}")[:44],
            sport="Motor Racing", sport_slug="motor-racing",
            competition=f"Formula 1 2026 - {team} team-mate head-to-head (Mexico City GP)",
            side_a=_clean_driver(a["driver"]), side_b=_clean_driver(b["driver"]), start_utc=start, venue="Autodromo Hermanos Rodriguez",
            official_url=cap.url("f1_drivers"),
            official_source_name="Formula 1 official driver standings (formula1.com)",
            capture_id="f1_drivers",
        )
        r["evidence"] = {"driver_a_points": a["pts"], "driver_b_points": b["pts"], "team": team,
                         "positions": [a["pos"], b["pos"]]}
        r["form"] = {_clean_driver(a["driver"]): f"{a['pts']} pts", _clean_driver(b["driver"]): f"{b['pts']} pts"}
        r["sample"] = "official championship points"
        r["model"] = {"name": "Bradley-Terry on official championship points", "scale": 90.0}
        r["markets"] = {"match_winner": market("Team-Mate Head-to-Head", None,
                                               [(_clean_driver(a["driver"]), p_a), (_clean_driver(b["driver"]), 1 - p_a)])}
        idx = 0 if p_a >= 0.5 else 1
        pick_from(r, "match_winner", idx, conf(max(p_a, 1 - p_a), "Low"), "points-based head-to-head - capped at Low")
        rows.append(r)
        made += 1


# ------------------------------------------------------------------ greyhounds
def _gbgb_upcoming(cap: P.Capture) -> list:
    out = []
    for tid in ("gbgb_fix_2026_10_25", "gbgb_fix_2026_10_25b", "gbgb_fix_2026_10_26", "gbgb_fix_2026_10_26b",
                "gbgb_races_2026_10_25", "gbgb_races_2026_10_25b", "gbgb_races_2026_10_26", "gbgb_api_racecards"):
        if not cap.exists(tid):
            continue
        try:
            data = cap.json(tid)
        except Exception:
            continue
        items = data if isinstance(data, list) else (data.get("items") or data.get("results") or data.get("data") or [])
        if isinstance(items, dict):
            items = items.get("items", [])
        for r in items:
            if not isinstance(r, dict):
                continue
            dogs = r.get("dogs") or r.get("runners") or r.get("entries") or []
            if not dogs:
                continue
            out.append((tid, r, dogs))
    return out


def build_greyhounds_fi(cap: P.Capture, rows):
    races = _gbgb_upcoming(cap)
    if not races:
        return
    form = {}
    if cap.exists("gbgb_results_api") or cap.exists("gbgb_results_24"):
        for tid in ("gbgb_results_24", "gbgb_results_api"):
            if not cap.exists(tid):
                continue
            try:
                data = cap.json(tid)
            except Exception:
                continue
            for it in data.get("items", []):
                dog = it.get("dogName")
                pos = it.get("resultPosition")
                if not dog or not pos:
                    continue
                f = form.setdefault(dog.lower(), {"runs": 0, "wins": 0, "places": 0, "best": None})
                f["runs"] += 1
                if int(pos) == 1:
                    f["wins"] += 1
                if int(pos) <= 3:
                    f["places"] += 1
    for tid, race, dogs in races[:40]:
        names = []
        for d in dogs:
            n = d.get("dogName") or d.get("name") or d.get("dog")
            if n:
                names.append(n)
        if len(names) < 4:
            continue
        rated = [(n, form.get(n.lower(), {})) for n in names]
        if sum(1 for _, f in rated if f.get("runs")) < 2:
            continue
        strengths = []
        for n, f in rated:
            runs = max(1, f.get("runs", 0))
            win_rate = f.get("wins", 0) / runs
            place_rate = f.get("places", 0) / runs
            strengths.append(max(0.02, 0.6 * win_rate + 0.4 * (place_rate / 3) + 0.08))
        tot = sum(strengths)
        probs = [s / tot for s in strengths]
        best = max(range(len(names)), key=lambda i: probs[i])
        track = race.get("trackName") or race.get("track") or ""
        start = race.get("raceTime") or race.get("startTime") or ""
        start_utc = ""
        if race.get("raceDate") and start:
            start_utc = P._utc(race["raceDate"][:10] + "T" + str(start)[:8])
        if not in_window(start_utc):
            continue
        row = blank_row(
            id="fi_grey_" + re.sub(r"\W+", "_", f"{track}_{race.get('raceNumber','')}_{race.get('raceId','')}")[:44],
            sport="Greyhounds", sport_slug="greyhounds",
            competition=f"GBGB racecard - {track} race {race.get('raceNumber','')}",
            side_a=f"{race.get('raceNumber','')} {track}", side_b="", start_utc=start_utc, venue=track,
            official_url=cap.url(tid), official_source_name="GBGB official racecard/race feed (api.gbgb.org.uk)",
            capture_id=tid,
        )
        row["evidence"] = {"runners": len(names), "dog_form": {n: f for n, f in rated},
                           "results_source": cap.url("gbgb_results_24") if cap.exists("gbgb_results_24") else ""}
        row["form"] = {n: f"{f.get('wins',0)}-{f.get('places',0)} from {f.get('runs',0)} recent runs" for n, f in rated}
        row["sample"] = "GBGB results for each runner in the capture"
        row["model"] = {"name": "Bradley-Terry on recent GBGB win and place rates"}
        row["markets"] = {"match_winner": market("Race Winner", None, list(zip(names, probs)))}
        row["flags"].append("trap draw and going not modelled; recent GBGB results are the only input")
        pick_from(row, "match_winner", best, conf(probs[best], "Low"), "recent-results model - capped at Low")
        rows.append(row)



# ============================================================ late repairs (FI)
# These run after the primary builders and price the fixture groups whose
# official input arrived in a target the primary builder was not yet reading:
#   * Rugby Union  - official URC fixtures + the official Match Centre table
#   * Snooker      - WST match API, Elo built from the completed matches it holds
#                    (the WST ranking page in this capture is client-rendered)
#   * Tennis       - WTA official match feed, Elo from the completed matches
# Nothing here invents a value: a fixture with no supporting official input is
# left unpriced with the reason already attached by its primary builder.

URC_TABLE_EVIDENCE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "session-405e9797", "evidence", "urc_table.json")


def _urc_table_any(cap: P.Capture) -> dict:
    """Official URC table: captured bytes first, then the transcribed evidence file."""
    tab = _urc_table(cap)
    if tab:
        return tab
    if not os.path.exists(URC_TABLE_EVIDENCE):
        return {}
    doc = json.load(open(URC_TABLE_EVIDENCE))
    out = {}
    for r in doc.get("table", []):
        pl = int(r.get("pl") or 0)
        if pl <= 0:
            continue
        out[r["team"]] = {
            "pos": int(r["pos"]), "pts": int(r["pts"]), "gp": pl, "w": int(r["w"]), "d": int(r["d"]),
            "l": int(r["l"]), "pf": int(r["pf"]), "pa": int(r["pa"]),
            "pf_pg": int(r["pf"]) / pl, "pa_pg": int(r["pa"]) / pl,
            "source_id": "urc_table_evidence", "source_url": doc.get("url", ""),
            "table_page": doc.get("page_header", ""), "fetched_utc": doc.get("fetched_utc", ""),
        }
    return out


def build_rugby_union_official(cap: P.Capture, rows) -> int:
    tab = _urc_table_any(cap)
    if not tab:
        return 0
    have = {r["id"] for r in rows}
    added = 0
    for f in P.read_urc(cap):
        if not in_window(f["start_utc"]):
            continue
        na, va = _match_team(f["side_a"], tab)
        nb, vb = _match_team(f["side_b"], tab)
        if not va or not vb:
            continue
        rid = "fi_urc_" + re.sub(r"\W+", "_", f"{f['side_a']}_{f['side_b']}")[:48]
        if rid in have:
            continue
        exp_a = (va["pf_pg"] + vb["pa_pg"]) / 2.0 + 2.0
        exp_b = (vb["pf_pg"] + va["pa_pg"]) / 2.0 - 2.0
        mu = exp_a - exp_b
        p_a = 0.5 * (1 + math.erf(mu / (13.0 * math.sqrt(2))))
        p_a = min(0.93, max(0.07, p_a))
        line = max(0.5, math.floor(abs(mu) - 2) + 0.5)
        p_cover = 1 - 0.5 * (1 + math.erf((line - abs(mu)) / (13.0 * math.sqrt(2))))
        tot = exp_a + exp_b
        tline = math.floor(tot) + 0.5
        p_over = 1 - 0.5 * (1 + math.erf((tline - tot) / (16.0 * math.sqrt(2))))
        row = blank_row(
            id=rid, sport="Rugby Union", sport_slug="rugby-union",
            competition="United Rugby Championship 2026-27",
            side_a=f["side_a"], side_b=f["side_b"], start_utc=f["start_utc"], venue=f.get("venue", ""),
            official_url=cap.url("urc_fixtures_in_full"),
            official_source_name="URC official fixtures-in-full page + official Match Centre table",
            capture_id="urc_fixtures_in_full",
        )
        row["evidence"] = {
            "home_pf_pg": round(va["pf_pg"], 2), "home_pa_pg": round(va["pa_pg"], 2),
            "away_pf_pg": round(vb["pf_pg"], 2), "away_pa_pg": round(vb["pa_pg"], 2),
            "home_table": f"{va['pos']} ({va['pts']} pts from {va['gp']})",
            "away_table": f"{vb['pos']} ({vb['pts']} pts from {vb['gp']})",
            "home_gp": va["gp"], "away_gp": vb["gp"], "round": f["extra"].get("round", ""),
            "exp_home": round(exp_a, 1), "exp_away": round(exp_b, 1),
            "table_page": va.get("table_page", ""),
            "table_source": va.get("source_url", ""),
            "table_fetched": va.get("fetched_utc", ""),
        }
        row["form"] = {f["side_a"]: f"{va['w']}-{va['d']}-{va['l']} ({va['pf']}:{va['pa']})",
                       f["side_b"]: f"{vb['w']}-{vb['d']}-{vb['l']} ({vb['pf']}:{vb['pa']})"}
        row["sample"] = f"{min(va['gp'], vb['gp'])} completed matches per side"
        row["model"] = {"name": "normal points margin from official table scoring rates",
                        "exp_home": round(exp_a, 1), "exp_away": round(exp_b, 1), "sd_margin": 13.0}
        fav, dog = (f["side_a"], f["side_b"]) if mu >= 0 else (f["side_b"], f["side_a"])
        row["markets"] = {
            "match_winner": market("Match Winner (2-Way)", None, [(f["side_a"], p_a), (f["side_b"], 1 - p_a)]),
            "handicap": market("Points Handicap", -line,
                               [(f"{fav} -{line}", p_cover), (f"{dog} +{line}", 1 - p_cover)]),
            "total": market(f"Total Points ({tline})", tline,
                            [(f"Over {tline}", p_over), (f"Under {tline}", 1 - p_over)]),
        }
        cap_label = conf(max(p_a, 1 - p_a), "Medium" if min(va["gp"], vb["gp"]) >= 3 else "Low")
        pick_best(row, cap_label,
                  "table-based model capped at Medium; the picked leg always sits inside -250..+10,000")
        row["flags"].append("standings transcribed from the official Match Centre table page (round 3 of 2026/27)")
        rows.append(row)
        added += 1
    return added


def _clean_driver(name: str) -> str:
    """'Kimi Antonelli ANT' -> 'Kimi Antonelli' (drop the trailing team code)."""
    parts = (name or "").split()
    if len(parts) > 2 and len(parts[-1]) == 3 and parts[-1].isupper():
        return " ".join(parts[:-1])
    return name


def _wst_completed(cap: P.Capture):
    if not cap.exists("wst_matches_api"):
        return []
    out = []
    for m in cap.json("wst_matches_api").get("data", []):
        a = m.get("attributes", {})
        hp, ap = a.get("homePlayer") or {}, a.get("awayPlayer") or {}
        hn = f"{hp.get('firstName','')} {hp.get('surname','')}".strip()
        an = f"{ap.get('firstName','')} {ap.get('surname','')}".strip()
        hs, as_ = a.get("homePlayerScore"), a.get("awayPlayerScore")
        if not hn or not an or hs is None or as_ is None:
            continue
        if a.get("status") != "Completed" or (hs == 0 and as_ == 0):
            continue
        out.append({"when": a.get("startDateTime") or "", "home": hn, "away": an,
                    "hs": int(hs), "as": int(as_)})
    return out


def _wst_elo(cap: P.Capture):
    games = _wst_completed(cap)
    if len(games) < 40:
        return {}, {}
    elo, stats = {}, {}
    for g in sorted(games, key=lambda x: x["when"]):
        h, a = g["home"], g["away"]
        eh, ea = elo.get(h, 1500.0), elo.get(a, 1500.0)
        exp_h = 1.0 / (1.0 + 10 ** ((ea - eh) / 400.0))
        frames = g["hs"] + g["as"]
        score = g["hs"] / frames if frames else 0.5
        k = 24.0 * min(2.0, 1.0 + abs(g["hs"] - g["as"]) / 4.0)
        elo[h] = eh + k * (score - exp_h)
        elo[a] = ea + k * ((1 - score) - (1 - exp_h))
        for name, won, lost in ((h, g["hs"], g["as"]), (a, g["as"], g["hs"])):
            st = stats.setdefault(name, {"n": 0, "fw": 0, "fl": 0})
            st["n"] += 1
            st["fw"] += won
            st["fl"] += lost
    return elo, stats


def _elo_snooker_row(rows, f, ra, rb, sa, sb, bo, sample_note):
    row = blank_row(**f)
    p_frame = 1 / (1 + 10 ** ((rb - ra) / 400.0))
    p_frame = min(0.90, max(0.10, p_frame))
    p_a = sum(math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k) for k in range(bo // 2 + 1, bo + 1))
    p_a = min(0.95, max(0.05, p_a))
    row["evidence"] = {"elo_a": round(ra, 1), "elo_b": round(rb, 1), "best_of": bo,
                       "matches_a": sa["n"], "matches_b": sb["n"],
                       "frames_a": f"{sa['fw']}-{sa['fl']}", "frames_b": f"{sb['fw']}-{sb['fl']}",
                       "round": f.get("extra", {}).get("round"),
                       "rating_source": "Elo built from the completed matches in the WST official match feed"}
    row["form"] = {f["side_a"]: f"{sa['n']} completed matches, {sa['fw']}-{sa['fl']} frames",
                   f["side_b"]: f"{sb['n']} completed matches, {sb['fw']}-{sb['fl']} frames"}
    row["sample"] = f"{sample_note}; best of {bo} frames"
    margins = {}
    for k in range(bo // 2 + 1, bo + 1):
        margins[k - (bo - k)] = margins.get(k - (bo - k), 0) + math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k)
    row["markets"] = {
        "match_winner": market("Match Winner", None, [(f["side_a"], p_a), (f["side_b"], 1 - p_a)]),
        "handicap": market("Frame Handicap", -2.5,
                           [(f"{f['side_a']} -2.5", sum(v for k, v in margins.items() if k >= 3)),
                            (f"{f['side_b']} +2.5", sum(v for k, v in margins.items() if k < 3))]),
    }
    row["flags"].append("total frames not modelled - no official frame-tempo input captured")
    row["flags"].append("rating built from this season's completed matches, not the official two-year ranking list")
    row["model"] = {"name": "frame Bernoulli from Elo on official WST results, exact best-of-n",
                    "p_frame": round(p_frame, 4), "best_of": bo}
    pick_from(row, "match_winner", 0 if p_a >= 0.5 else 1, conf(max(p_a, 1 - p_a), "Medium"),
              "result-only Elo capped at Medium")
    rows.append(row)


def _wst_ranks(cap: P.Capture) -> dict:
    """Official World Rankings positions from the WST ranking API (top 100)."""
    for tid in ("wst_rank_api", "wst_rankings_api", "wst_rankings"):
        if not cap.exists(tid):
            continue
        try:
            doc = cap.json(tid)
        except Exception:
            continue
        ranks = {}
        for block in doc.get("data", []):
            a = block.get("attributes", {}) or {}
            if a.get("rankingType") not in ("livePrizeMoney", "prizeMoney"):
                continue
            for pos in a.get("positions") or []:
                pl = pos.get("player") or {}
                nm = ((pl.get("firstName") or "") + " " + (pl.get("surname") or "")).strip()
                if nm and pos.get("position") and nm not in ranks:
                    ranks[nm] = int(pos["position"])
        if ranks:
            return ranks
    return {}


def build_snooker_ranks(cap: P.Capture, rows) -> int:
    ranks = _wst_ranks(cap)
    if not ranks:
        return 0
    priced = 0
    for f in P.read_wst(cap)[0]:
        if not in_window(f["start_utc"]):
            continue
        a, b = f["side_a"], f["side_b"]
        ra, rb = ranks.get(a), ranks.get(b)
        if not ra or not rb:
            continue
        row = next((r for r in rows if r["id"] == f["id"]), None)
        if row is None or row.get("pick"):
            continue
        bo = int(f["extra"].get("best_of") or 7)
        p_frame = min(0.93, max(0.07, 1 / (1 + 10 ** ((ra - rb) / 220.0))))
        p_a = sum(math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k) for k in range(bo // 2 + 1, bo + 1))
        p_a = min(0.95, max(0.05, p_a))
        margins = {}
        for k in range(bo // 2 + 1, bo + 1):
            margins[k - (bo - k)] = margins.get(k - (bo - k), 0) + math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k)
        markets = {
            "match_winner": market("Match Winner", None, [(a, p_a), (b, 1 - p_a)]),
            "handicap": market("Frame Handicap", -2.5,
                               [(f"{a} -2.5", sum(v for k, v in margins.items() if k >= 3)),
                                (f"{b} +2.5", sum(v for k, v in margins.items() if k < 3))]),
        }
        _price_existing(
            row, p_a, p_frame, bo, markets,
            {"world_rank_a": ra, "world_rank_b": rb, "best_of": bo,
             "round": f["extra"].get("round"), "players_ranked": len(ranks),
             "rank_source": "WST official World Rankings API (live prize money, two-year list)"},
            {a: f"world rank {ra}", b: f"world rank {rb}"},
            f"best of {bo} frames; official two-year world ranking",
            {"name": "frame Bernoulli from the official World Rankings gap, exact best-of-n",
             "p_frame": round(p_frame, 4), "best_of": bo},
            conf(max(p_a, 1 - p_a), "High"),
            "p>=70% High; official two-year ranking list, in window")
        row["flags"] = [fl for fl in row["flags"] if "completed official matches" not in fl]
        row["flags"].append("total frames not modelled - no official frame-tempo input captured")
        priced += 1
    return priced


def _price_existing(row, p_a, p_frame, bo, markets, evidence, form, sample, model, conf_label, rule):
    row["evidence"].update(evidence)
    row["form"] = form
    row["sample"] = sample
    row["model"] = model
    row["markets"] = markets
    row["flags"] = [fl for fl in row["flags"] if "no line originated" not in fl]
    row["flags"].append("rating built from this season's completed official matches, not the official two-year ranking list")
    pick_best(row, conf_label, rule)


def pick_best(row, confidence, rule):
    """Take the strongest leg that sits inside the -250..+10,000 window.

    Preference order: the moneyline favourite, then its handicap leg, then the
    total.  Never the opposite side of the moneyline just because the favourite
    is shorter than -250 - that would be picking a 15% chance at +500.
    """
    mws = row.get("markets") or {}
    order = ["match_winner", "handicap", "total", "outright"]
    best = None
    for rank, key in enumerate(order):
        m = mws.get(key)
        if not m:
            continue
        top = max(m["selections"], key=lambda x: x["fair_prob"])
        if -250 <= top["fair_american"] <= 10000:
            cand = (rank, -top["fair_prob"], key, m["selections"].index(top))
            if best is None or cand < best:
                best = cand
    if best:
        pick_from(row, best[2], best[3], confidence, rule)
        return True
    return False


def build_snooker_elo(cap: P.Capture, rows) -> int:
    elo, stats = _wst_elo(cap)
    if not elo:
        return 0
    by_key = {}
    for r in rows:
        if r["sport"] == "Snooker":
            by_key[(r["side_a"], r["side_b"])] = r
    priced = 0
    for f in P.read_wst(cap)[0]:
        if not in_window(f["start_utc"]):
            continue
        a, b = f["side_a"], f["side_b"]
        if a not in elo or b not in elo:
            continue
        sa, sb = stats[a], stats[b]
        if sa["n"] < 3 or sb["n"] < 3:
            continue
        row = by_key.get((a, b))
        if row is None or row.get("pick"):
            continue
        bo = int(f["extra"].get("best_of") or 7)
        p_frame = min(0.90, max(0.10, 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400.0))))
        p_a = sum(math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k) for k in range(bo // 2 + 1, bo + 1))
        p_a = min(0.95, max(0.05, p_a))
        margins = {}
        for k in range(bo // 2 + 1, bo + 1):
            margins[k - (bo - k)] = margins.get(k - (bo - k), 0) + math.comb(bo, k) * p_frame ** k * (1 - p_frame) ** (bo - k)
        markets = {
            "match_winner": market("Match Winner", None, [(a, p_a), (b, 1 - p_a)]),
            "handicap": market("Frame Handicap", -2.5,
                               [(f"{a} -2.5", sum(v for k, v in margins.items() if k >= 3)),
                                (f"{b} +2.5", sum(v for k, v in margins.items() if k < 3))]),
        }
        _price_existing(
            row, p_a, p_frame, bo, markets,
            {"elo_a": round(elo[a], 1), "elo_b": round(elo[b], 1), "best_of": bo,
             "matches_a": sa["n"], "matches_b": sb["n"], "frames_a": f"{sa['fw']}-{sa['fl']}",
             "frames_b": f"{sb['fw']}-{sb['fl']}", "round": f["extra"].get("round"),
             "rating_source": "Elo built from the completed matches in the WST official match feed"},
            {a: f"{sa['n']} completed matches, {sa['fw']}-{sa['fl']} frames",
             b: f"{sb['n']} completed matches, {sb['fw']}-{sb['fl']} frames"},
            f"best of {bo} frames; {len(stats)} players rated from the same feed",
            {"name": "frame Bernoulli from Elo on official WST results, exact best-of-n",
             "p_frame": round(p_frame, 4), "best_of": bo},
            conf(max(p_a, 1 - p_a), "Medium"), "result-only Elo capped at Medium")
        priced += 1
    return priced


def _wta_elo(cap: P.Capture):
    elo, stats = {}, {}
    games = []
    for tid in ("wta_2092", "wta_405", "wta_1023", "wta_1056"):
        if not cap.exists(tid):
            continue
        for m in cap.json(tid).get("matches", []):
            if m.get("MatchState") != "F" or m.get("Winner") in (None, "", 0):
                continue
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            if not a or not b or m.get("PlayerNameFirstA2") or m.get("PlayerNameFirstB2"):
                continue  # doubles
            games.append({"when": m.get("MatchTimeStamp") or "", "a": a, "b": b,
                          "winner": int(m["Winner"]), "tid": tid})
    for g in sorted(games, key=lambda x: x["when"]):
        a, b = g["a"], g["b"]
        ea, eb = elo.get(a, 1500.0), elo.get(b, 1500.0)
        exp_a = 1.0 / (1.0 + 10 ** ((eb - ea) / 400.0))
        score = 1.0 if g["winner"] == 1 else 0.0
        elo[a] = ea + 26.0 * (score - exp_a)
        elo[b] = eb + 26.0 * ((1 - score) - (1 - exp_a))
        for name, won in ((a, score), (b, 1 - score)):
            st = stats.setdefault(name, {"n": 0, "w": 0})
            st["n"] += 1
            st["w"] += int(won)
    return elo, stats, len(games)


def build_tennis_elo(cap: P.Capture, rows) -> int:
    elo, stats, n_games = _wta_elo(cap)
    if not elo:
        return 0
    priced = 0
    for row in rows:
        if row["sport"] != "Tennis" or row.get("pick"):
            continue
        a, b = row["side_a"], row["side_b"]
        if "/" in a or "/" in b:
            row["flags"].append("doubles draw - no singles rating applies, left unpriced")
            continue
        if a not in elo or b not in elo:
            continue
        sa, sb = stats[a], stats[b]
        if sa["n"] < 2 or sb["n"] < 2:
            continue
        p_a = 1 / (1 + 10 ** ((elo[b] - elo[a]) / 400.0))
        p_a = min(0.93, max(0.07, p_a))
        row["evidence"] = {"elo_a": round(elo[a], 1), "elo_b": round(elo[b], 1),
                           "wins_a": sa["w"], "wins_b": sb["w"],
                           "matches_fed": n_games, "draw": row["evidence"].get("draw"),
                           "rating_source": "Elo built from the completed matches in the official WTA match feed"}
        row["form"] = {a: f"{sa['w']}-{sa['n'] - sa['w']} this month", b: f"{sb['w']}-{sb['n'] - sb['w']} this month"}
        row["sample"] = f"{n_games} completed matches across the four events in this capture"
        row["model"] = {"name": "logistic on Elo built from official WTA results", "elo_a": round(elo[a], 1),
                        "elo_b": round(elo[b], 1)}
        row["markets"] = {"match_winner": market("Match Winner", None, [(a, p_a), (b, 1 - p_a)])}
        row["flags"] = [fl for fl in row["flags"] if "no line originated" not in fl]
        row["flags"].append("rating built from the current month's official WTA results, not the ranking list")
        pick_from(row, "match_winner", 0 if p_a >= 0.5 else 1, conf(max(p_a, 1 - p_a), "Low"),
                  "result-only Elo capped at Low")
        priced += 1
    return priced


def _tennis_titles(cap: P.Capture) -> dict:
    out = {}
    for tid in ("wta_2092", "wta_405", "wta_1023", "wta_1056"):
        if not cap.exists(tid):
            continue
        try:
            t = cap.json(tid).get("tournament") or {}
        except Exception:
            continue
        title = t.get("title") or ""
        level = (t.get("tournamentGroup") or {}).get("level") or ""
        if title:
            out[tid] = title + (" (" + level + ")" if level else "")
    return out


def build_tennis_titles(cap: P.Capture, rows) -> int:
    titles = _tennis_titles(cap)
    n = 0
    for r in rows:
        if r["sport"] != "Tennis":
            continue
        parts = (r.get("id") or "").split("_")
        tid = "_".join(parts[1:3]) if len(parts) > 2 else ""
        if tid in titles:
            r["competition"] = titles[tid]
            n += 1
    return n


def _icc_ratings(cap: P.Capture) -> dict:
    """Official ICC team ratings, whatever shape the captured JSON uses.

    Walks the payload for objects that carry a team name next to a numeric
    rating/points field and keeps the first value seen per team and format.
    """
    TEAMS = ("India", "Australia", "England", "Pakistan", "South Africa", "New Zealand", "Sri Lanka",
             "West Indies", "Bangladesh", "Afghanistan", "Zimbabwe", "Ireland", "Netherlands",
             "Scotland", "Namibia", "United Arab Emirates", "Nepal", "Oman", "United States",
             "Canada", "Kenya", "Jersey", "Denmark", "Papua New Guinea")
    FMTS = {"icc_api_odi": "ODI", "icc_static_odi": "ODI", "icc_json_odi": "ODI", "icc_api_t20i": "T20I"}

    def walk(node, fmt, out):
        if isinstance(node, dict):
            name = None
            for k in ("name", "teamName", "team_name", "team", "displayName", "title"):
                v = node.get(k)
                if isinstance(v, str) and v.strip() in TEAMS:
                    name = v.strip()
                    break
                if isinstance(v, dict) and isinstance(v.get("name"), str) and v["name"].strip() in TEAMS:
                    name = v["name"].strip()
                    break
            if name:
                for k in ("rating", "points", "ratings", "ratingValue", "value"):
                    v = node.get(k)
                    try:
                        val = float(v)
                    except (TypeError, ValueError):
                        continue
                    if 30 <= val <= 200:
                        out.setdefault((fmt, name), val)
                        break
            for v in node.values():
                walk(v, fmt, out)
        elif isinstance(node, list):
            for v in node:
                walk(v, fmt, out)

    out = {}
    for tid, fmt in FMTS.items():
        if not cap.exists(tid):
            continue
        try:
            doc = cap.json(tid)
        except Exception:
            continue
        walk(doc, fmt, out)
    return out


def _team_key(name: str) -> str:
    n = re.sub(r"\b(men|women|mens|womens|xi|u19|u23)\b", "", (name or "").lower())
    n = re.sub(r"[^a-z ]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def build_cricket_icc(cap: P.Capture, rows) -> int:
    ratings = _icc_ratings(cap)
    if not ratings:
        return 0
    by_fmt = {}
    for (fmt, team), val in ratings.items():
        by_fmt.setdefault(fmt, {})[_team_key(team)] = val
    priced = 0
    for row in rows:
        if row["sport"] != "Cricket" or row.get("pick"):
            continue
        fmt = (row.get("extra") or {}).get("game_type") or ""
        table = by_fmt.get("T20I" if fmt in ("T20 International", "T20") else ("ODI" if fmt in ("ODI", "") else fmt))
        if not table:
            continue
        a, b = _team_key(row["side_a"]), _team_key(row["side_b"])
        if a not in table or b not in table:
            continue
        ra, rb = table[a], table[b]
        p_a = 1 / (1 + 10 ** ((rb - ra) / 30.0))
        p_a = min(0.93, max(0.07, p_a))
        row["evidence"] = {"icc_rating_a": ra, "icc_rating_b": rb, "format": fmt or "ODI",
                           "rating_source": "ICC official team rankings captured in this snapshot"}
        row["form"] = {row["side_a"]: f"ICC rating {ra}", row["side_b"]: f"ICC rating {rb}"}
        row["sample"] = "official ICC team rating list"
        row["model"] = {"name": "logistic on the ICC team-rating gap", "rating_gap": round(ra - rb, 1), "scale": 30.0}
        row["markets"] = {"match_winner": market("Match Winner", None,
                                                 [(row["side_a"], p_a), (row["side_b"], 1 - p_a)])}
        row["flags"] = [fl for fl in row["flags"] if "no line originated" not in fl]
        row["flags"].append("team strength from the official ICC rating list; no venue or XI adjustment")
        pick_best(row, conf(max(p_a, 1 - p_a), "Medium"),
                  "ranking-based model capped at Medium")
        priced += 1
    return priced


def late_repairs(cap: P.Capture, rows) -> dict:
    out = {}
    out["rugby_union_rows"] = build_rugby_union_official(cap, rows)
    out["snooker_rank_rows"] = build_snooker_ranks(cap, rows)
    out["snooker_elo_rows"] = build_snooker_elo(cap, rows)
    out["tennis_priced"] = build_tennis_elo(cap, rows)
    out["tennis_titles"] = build_tennis_titles(cap, rows)
    out["cricket_icc"] = build_cricket_icc(cap, rows)
    return out


if __name__ == "__main__":
    main()

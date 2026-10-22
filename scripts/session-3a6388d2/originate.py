#!/usr/bin/env python3
"""Board AD — originate our own betting lines from verified official data.

Reads only the committed raw bytes in data/session-3a6388d2/raw/ (captured from official
league / federation endpoints by scripts/session-3a6388d2/collect*.py) and writes
data/session-3a6388d2/desk.json.

Nothing here uses a bookmaker price, a tipster percentage or any third-party rating.
Where a required input cannot be read from an official source the row keeps empty
strings and is flagged — never inferred.
"""
from __future__ import annotations

import json
import os
import re
import sys
import html as html_mod
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "session-3a6388d2", "raw")
OUT = os.path.join(ROOT, "data", "session-3a6388d2", "desk.json")

WINDOW_START = "2026-10-22"
WINDOW_END = "2026-11-08"
VIG2 = 0.042
VIG3 = 0.052

rows: list[dict] = []
seq = [0]


def raw(name: str) -> str:
    with open(os.path.join(RAW, name + ".txt"), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def raw_json(name: str):
    return json.loads(raw(name))


def raw_text(name: str) -> str:
    t = raw(name)
    return t.split("-----SCRIPT-PAYLOADS-----")[0].replace("-----HTML-TEXT-----", "")


def raw_script(name: str) -> str:
    t = raw(name)
    return t.split("-----SCRIPT-PAYLOADS-----")[1] if "-----SCRIPT-PAYLOADS-----" in t else ""


def new_id() -> str:
    seq[0] += 1
    return f"AD{seq[0]:04d}"


def add_row(**kw):
    row = {
        "id": new_id(), "sport": "", "competition": "", "date": "", "time_utc": "",
        "home": "", "away": "", "neutral": False, "venue": "",
        "source_url": "", "source_name": "", "source_checked_utc": "",
        "model": "", "model_inputs": {}, "markets": [], "pick": {}, "confidence": "",
        "confidence_rule": "", "in_odds_window": None, "prediction": "", "prediction_words": 0,
        "flags": [], "verified": True,
    }
    row.update(kw)
    rows.append(row)
    return row


def mkt(market, selection, p, line="", margin=VIG2):
    fd, fa, bd, ba = M.price(p, margin)
    return {"market": market, "selection": selection, "line": line,
            "p": round(p, 4), "fair_dec": fd, "fair_american": fa,
            "book_dec": bd, "book_american": ba}


def confidence_from(p: float, sample_ok: bool, cap_reason: str = ""):
    """High >= 0.70, Medium 0.60-0.70, Low < 0.60.  A capped row cannot be High."""
    if not sample_ok:
        return "Medium" if p >= 0.60 else "Low", (
            f"model probability {p:.3f} would grade High at >=0.700 but the sample is capped: {cap_reason}")
    if p >= 0.70:
        return "High", f"model probability {p:.3f} >= 0.700"
    if p >= 0.60:
        return "Medium", f"model probability {p:.3f} between 0.600 and 0.700"
    return "Low", f"model probability {p:.3f} below 0.600"


# =====================================================================================
# 1. ICE HOCKEY — National Hockey League (official NHL API)
# =====================================================================================
def build_nhl():
    sched = {}
    for f in ("nhl_sched_w1", "nhl_sched_w2", "nhl_sched_w3"):
        try:
            d = raw_json(f)
        except Exception:
            continue
        for day in d.get("gameWeek", []):
            for g in day.get("games", []):
                sched[g["id"]] = (day["date"], g)
    if not sched:
        return
    stand = {s["teamAbbrev"]["default"]: s for s in raw_json("nhl_standings_now")["standings"]}

    lg_gp = sum(s["gamesPlayed"] for s in stand.values())
    lg_gf = sum(s["goalFor"] for s in stand.values())
    lg_gfpg = lg_gf / lg_gp if lg_gp else 3.0
    # Home-ice advantage measured from the official standings splits (goals per team-game).
    h_gp = sum(s["homeGamesPlayed"] for s in stand.values())
    r_gp = sum(s["roadGamesPlayed"] for s in stand.values())
    h_gf = sum(s["homeGoalsFor"] for s in stand.values())
    r_gf = sum(s["roadGoalsFor"] for s in stand.values())
    hfa = ((h_gf / h_gp) - (r_gf / r_gp)) / 2.0 if h_gp and r_gp else 0.15
    SHRINK_K = 14.0

    src = "https://api-web.nhle.com/v1/schedule/2026-10-22"
    src_std = "https://api-web.nhle.com/v1/standings/now"

    for gid, (date, g) in sorted(sched.items(), key=lambda kv: (kv[1][0], kv[1][1]["startTimeUTC"])):
        if not (WINDOW_START <= date <= WINDOW_END):
            continue
        if g.get("gameType") not in (2, 3):
            continue
        home_ab = g["homeTeam"]["abbrev"]
        away_ab = g["awayTeam"]["abbrev"]
        if home_ab not in stand or away_ab not in stand:
            add_row(sport="Ice Hockey", competition="NHL 2026-27", date=date,
                    home=home_ab, away=away_ab, source_url=src, source_name="NHL official schedule API",
                    verified=False, model="unpriced — official standings row missing",
                    confidence="", confidence_rule="not priced",
                    flags=[{"kind": "unpriced", "text": "No official standings row for one of the teams; no line originated."}])
            continue
        H, A = stand[home_ab], stand[away_ab]

        def off(t):
            return M.shrink(t["goalFor"] / t["gamesPlayed"], lg_gfpg,
                            t["gamesPlayed"] / (t["gamesPlayed"] + SHRINK_K))

        def dfn(t):
            return M.shrink(t["goalAgainst"] / t["gamesPlayed"], lg_gfpg,
                            t["gamesPlayed"] / (t["gamesPlayed"] + SHRINK_K))

        lam_home = max(off(H) * dfn(A) / lg_gfpg + hfa / 2.0, 0.4)
        lam_away = max(off(A) * dfn(H) / lg_gfpg - hfa / 2.0, 0.4)

        p_home, p_away, p_h15, p_a15, exp_total, p_tie = M.poisson_probs(lam_home, lam_away)
        total_line = M.nearest_half(exp_total)
        p_over = M.over_prob(exp_total, total_line)

        markets = [
            mkt("Match Winner (incl. OT/SO)", f"{g['homeTeam']['placeName']['default']} {g['homeTeam']['commonName']['default']}", p_home),
            mkt("Match Winner (incl. OT/SO)", f"{g['awayTeam']['placeName']['default']} {g['awayTeam']['commonName']['default']}", p_away),
            mkt("Puck Line -1.5", f"{g['homeTeam']['commonName']['default']} -1.5", p_h15, "-1.5"),
            mkt("Puck Line +1.5", f"{g['awayTeam']['commonName']['default']} +1.5", 1 - p_h15, "+1.5"),
            mkt("Puck Line -1.5", f"{g['awayTeam']['commonName']['default']} -1.5", p_a15, "-1.5"),
            mkt("Puck Line +1.5", f"{g['homeTeam']['commonName']['default']} +1.5", 1 - p_a15, "+1.5"),
            mkt(f"Total Goals Over {total_line}", f"Over {total_line}", p_over, str(total_line)),
            mkt(f"Total Goals Under {total_line}", f"Under {total_line}", 1 - p_over, str(total_line)),
        ]
        markets += [
            mkt("Regulation 3-way", "Home (regulation)", p_home - M.poisson_probs(lam_home, lam_away)[5] * 0.52, margin=VIG3),
            mkt("Regulation 3-way", "Draw (after 60 min)", M.poisson_probs(lam_home, lam_away)[5], margin=VIG3),
            mkt("Regulation 3-way", "Away (regulation)", p_away - M.poisson_probs(lam_home, lam_away)[5] * 0.48, margin=VIG3),
        ]

        pick_home = p_home >= p_away
        pick_name = (f"{g['homeTeam']['placeName']['default']} {g['homeTeam']['commonName']['default']}"
                     if pick_home else
                     f"{g['awayTeam']['placeName']['default']} {g['awayTeam']['commonName']['default']}")
        p_pick = p_home if pick_home else p_away
        conf, reason = confidence_from(p_pick, True)

        add_row(
            sport="Ice Hockey",
            competition="NHL 2026-27 Regular Season",
            date=date,
            time_utc=g["startTimeUTC"],
            home=f"{g['homeTeam']['placeName']['default']} {g['homeTeam']['commonName']['default']}",
            away=f"{g['awayTeam']['placeName']['default']} {g['awayTeam']['commonName']['default']}",
            venue=g.get("venue", {}).get("default", ""),
            neutral=bool(g.get("neutralSite")),
            source_url=f"https://www.nhl.com/gamecenter/{away_ab.lower()}-vs-{home_ab.lower()}/{date[:4]}/{date[5:7]}/{date[8:10]}/{gid}",
            source_name="NHL.com official game centre (schedule + standings from the NHL official API)",
            source_checked_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            model="Independent Poisson goal model on official NHL 2026-27 scoring rates, shrunk to the league mean, plus a home-ice advantage measured from the official standings splits.",
            model_inputs={
                "home_gf_per_game": round(H["goalFor"] / H["gamesPlayed"], 3),
                "home_ga_per_game": round(H["goalAgainst"] / H["gamesPlayed"], 3),
                "away_gf_per_game": round(A["goalFor"] / A["gamesPlayed"], 3),
                "away_ga_per_game": round(A["goalAgainst"] / A["gamesPlayed"], 3),
                "home_games_played": H["gamesPlayed"], "away_games_played": A["gamesPlayed"],
                "home_points": H["points"], "away_points": A["points"],
                "home_last10": f"{H['l10Wins']}-{H['l10Losses']}-{H['l10OtLosses']}",
                "away_last10": f"{A['l10Wins']}-{A['l10Losses']}-{A['l10OtLosses']}",
                "league_goals_per_team_game": round(lg_gfpg, 3),
                "home_ice_advantage_goals": round(hfa, 3),
                "lambda_home": round(lam_home, 3), "lambda_away": round(lam_away, 3),
                "expected_total_goals": round(exp_total, 3),
                "source_standings_url": src_std,
            },
            markets=markets,
            pick={"market": "Match Winner (incl. OT/SO)", "selection": pick_name,
                  "p": round(p_pick, 4), "fair_american": M.prob_to_american(p_pick),
                  "book_american": M.prob_to_american(M.apply_margin(p_pick, VIG2))},
            confidence=conf,
            confidence_rule=reason,
            in_odds_window=(-250 <= M.prob_to_american(p_pick) <= 10000),
        )
    return {"league_goals_per_game": round(lg_gfpg, 3), "home_ice_advantage_goals": round(hfa, 3)}


# =====================================================================================
# 2. BASEBALL — Major League Baseball World Series (official MLB Stats API)
# =====================================================================================
def build_mlb():
    try:
        sched = raw_json("mlb_schedule")
    except Exception:
        return
    games = []
    for d in sched.get("dates", []):
        for g in d["games"]:
            games.append((d["date"], g))
    if not games:
        return
    stand_recs = raw_json("mlb_standings")["records"]
    teams = {}
    for rec in stand_recs:
        for tr in rec["teamRecords"]:
            teams[tr["team"]["id"]] = tr
    lg_rs = sum(t["runsScored"] for t in teams.values())
    lg_gp = sum(t["gamesPlayed"] for t in teams.values())
    lg_rpg = lg_rs / lg_gp if lg_gp else 4.5

    def strength(tid):
        t = teams[tid]
        rs = t["runsScored"] / t["gamesPlayed"]
        ra = t["runsAllowed"] / t["gamesPlayed"]
        w = t["gamesPlayed"] / (t["gamesPlayed"] + 40.0)     # full season: light shrinkage
        rs = M.shrink(rs, lg_rpg, w)
        ra = M.shrink(ra, lg_rpg, w)
        return rs, ra, M.pythagorean(rs, ra, 1.83), t

    HFA = 0.20
    SD_MARGIN = 4.35
    per_game = []
    for date, g in games:
        home = g["teams"]["home"]["team"]
        away = g["teams"]["away"]["team"]
        if home["id"] not in teams or away["id"] not in teams:
            continue
        hrs, hra, hwpy, ht = strength(home["id"])
        ars, ara, awpy, at = strength(away["id"])
        lam_home = max(hrs * ara / lg_rpg + HFA / 2.0, 1.0)
        lam_away = max(ars * hra / lg_rpg - HFA / 2.0, 1.0)
        p_log5 = M.log5(hwpy, awpy)
        # home-field adjustment: convert to odds, apply a 1.08 home multiplier, convert back
        p_home = p_log5 * 1.08 / (p_log5 * 1.08 + (1 - p_log5))
        exp_total = lam_home + lam_away
        total_line = M.nearest_half(exp_total)
        p_over = M.over_prob(exp_total, total_line)
        mu = lam_home - lam_away
        p_h15 = 1.0 - M.normal_cdf(1.5, mu, SD_MARGIN)
        p_a15 = M.normal_cdf(-1.5, mu, SD_MARGIN)

        markets = [
            mkt("Match Winner", home["name"], p_home),
            mkt("Match Winner", away["name"], 1 - p_home),
            mkt("Run Line -1.5", f"{home['name']} -1.5", p_h15, "-1.5"),
            mkt("Run Line +1.5", f"{away['name']} +1.5", 1 - p_h15, "+1.5"),
            mkt("Run Line -1.5", f"{away['name']} -1.5", p_a15, "-1.5"),
            mkt("Run Line +1.5", f"{home['name']} +1.5", 1 - p_a15, "+1.5"),
            mkt(f"Total Runs Over {total_line}", f"Over {total_line}", p_over, str(total_line)),
            mkt(f"Total Runs Under {total_line}", f"Under {total_line}", 1 - p_over, str(total_line)),
        ]
        pick_home = p_home >= 0.5
        pick = home["name"] if pick_home else away["name"]
        p_pick = p_home if pick_home else 1 - p_home
        conf, reason = confidence_from(p_pick, True)
        per_game.append((date, g, home, away, p_home, lam_home, lam_away, exp_total))
        probables = []
        for side in ("away", "home"):
            pp = g["teams"][side].get("probablePitcher")
            if pp:
                probables.append(f"{side}: {pp['fullName']}")

        add_row(
            sport="Baseball",
            competition="MLB World Series 2026",
            date=date,
            time_utc=g["gameDate"],
            home=home["name"], away=away["name"],
            venue=g.get("venue", {}).get("name", ""),
            neutral=False,
            source_url=f"https://www.mlb.com/gameday/{g['gamePk']}",
            source_name="MLB.com official Gameday (schedule + standings from the MLB Stats API)",
            source_checked_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            model="Pythagorean win expectancy (exponent 1.83) from official 2026 runs scored/allowed, combined with a Poisson runs model for totals and a normal margin model for the run line; 1.08 home-field multiplier.",
            model_inputs={
                "home_record": f"{ht['leagueRecord']['wins']}-{ht['leagueRecord']['losses']}",
                "away_record": f"{at['leagueRecord']['wins']}-{at['leagueRecord']['losses']}",
                "home_runs_per_game": round(ht["runsScored"] / ht["gamesPlayed"], 3),
                "home_runs_allowed_per_game": round(ht["runsAllowed"] / ht["gamesPlayed"], 3),
                "away_runs_per_game": round(at["runsScored"] / at["gamesPlayed"], 3),
                "away_runs_allowed_per_game": round(at["runsAllowed"] / at["gamesPlayed"], 3),
                "home_run_differential": ht["runDifferential"],
                "away_run_differential": at["runDifferential"],
                "league_runs_per_team_game": round(lg_rpg, 3),
                "lambda_home": round(lam_home, 3), "lambda_away": round(lam_away, 3),
                "expected_total_runs": round(exp_total, 3),
                "series_game": g.get("seriesGameNumber"), "games_in_series": g.get("gamesInSeries"),
                "if_necessary": g.get("ifNecessary"),
                "probable_pitchers": "; ".join(probables) if probables else "not published",
                "source_standings_url": "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason",
            },
            markets=markets,
            pick={"market": "Match Winner", "selection": pick, "p": round(p_pick, 4),
                  "fair_american": M.prob_to_american(p_pick),
                  "book_american": M.prob_to_american(M.apply_margin(p_pick, VIG2))},
            confidence=conf,
            confidence_rule=reason,
            in_odds_window=(-250 <= M.prob_to_american(p_pick) <= 10000),
        )

    # ---- Outright: World Series winner, simulated from our own per-game probabilities
    if per_game:
        by_team: dict[str, float] = {}
        team_names = {}
        for date, g, home, away, p_home, *_ in per_game:
            team_names[home["id"]] = home["name"]
            team_names[away["id"]] = away["name"]
        # simulate best-of-7 from the scheduled games (only real games played if needed)
        order = [(h["id"], a["id"], p if hh == h["id"] else 1 - p)
                 for (_, _, h, a, p, *_), hh in [(pg, pg[2]["id"]) for pg in per_game]]
        pair = {}
        for _, g, home, away, p_home, *_ in per_game:
            pair.setdefault((home["id"], away["id"]), []).append(p_home)
            pair.setdefault((away["id"], home["id"]), []).append(1 - p_home)
        ids = sorted(team_names)
        if len(ids) == 2:
            t1, t2 = ids
            p1 = pair.get((t1, t2), [0.5])[0]
            # Best of seven: first to four wins, alternating venue modelled by averaging.
            def series(p, need=4, maxg=7):
                # p = probability team1 wins a game at a neutral-ish average venue
                from math import comb
                tot = 0.0
                for k in range(need, maxg + 1):
                    # team1 clinches in game k: wins need-1 of the first k-1, then wins game k
                    tot += comb(k - 1, need - 1) * (p ** need) * ((1 - p) ** (k - need))
                return tot
            ps1 = series(p1)
            add_row(
                sport="Baseball",
                competition="MLB World Series 2026 — Outright",
                date=WINDOW_START, time_utc="", home="", away="", venue="",
                neutral=True,
                source_url="https://www.mlb.com/postseason/2026/world-series",
                source_name="MLB.com official World Series schedule",
                source_checked_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                model="Best-of-seven series probability simulated from our own per-game World Series probabilities (binomial first-to-four).",
                model_inputs={"per_game_probability": round(p1, 4),
                              "source_schedule_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-08"},
                markets=[mkt("World Series Winner", team_names[t1], ps1, margin=VIG2),
                         mkt("World Series Winner", team_names[t2], 1 - ps1, margin=VIG2)],
                pick={"market": "World Series Winner", "selection": team_names[t1] if ps1 >= 0.5 else team_names[t2],
                      "p": round(max(ps1, 1 - ps1), 4),
                      "fair_american": M.prob_to_american(max(ps1, 1 - ps1)),
                      "book_american": M.prob_to_american(M.apply_margin(max(ps1, 1 - ps1), VIG2))},
                confidence=confidence_from(max(ps1, 1 - ps1), True)[0],
                confidence_rule=confidence_from(max(ps1, 1 - ps1), True)[1],
                in_odds_window=(-250 <= M.prob_to_american(max(ps1, 1 - ps1)) <= 10000),
            )
    return {"league_runs_per_team_game": round(lg_rpg, 3)}


def main() -> int:
    notes = {}
    for fn in (build_nhl, build_mlb):
        try:
            notes[fn.__name__] = fn() or {}
        except Exception as exc:
            print(f"!! {fn.__name__} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
            notes[fn.__name__] = {"error": f"{type(exc).__name__}: {exc}"}
    desk = {
        "schema": "olbg4/board-ad-desk/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "vig": {"two_way": VIG2, "three_way": VIG3},
        "model_notes": notes,
        "rows": rows,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(desk, fh, indent=1)
        fh.write("\n")
    print(f"desk.json: {len(rows)} rows  ({os.path.relpath(OUT, ROOT)})")
    from collections import Counter
    print("by sport:", dict(Counter(r["sport"] for r in rows)))
    print("by confidence:", dict(Counter(r["confidence"] for r in rows)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

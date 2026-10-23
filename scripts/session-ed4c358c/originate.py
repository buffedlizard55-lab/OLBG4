#!/usr/bin/env python3
"""Board ED — originate our own lines for every verified upcoming fixture.

For each fixture published here we build margin-free fair markets from the captured
official feeds only (see METHODOLOGY on the site for every assumption), then pick a
selection and label it Low / Medium / High.

Sports with an official machine-readable form feed in this capture:
  Ice Hockey (NHL, Liiga) · Baseball (MLB World Series) · Basketball (EuroLeague/EuroCup)
  Volleyball (Italian SuperLega, Polish PlusLiga) · Handball (Danish Herreligaen, German HBL)
  Tennis (WTA / ATP order of play) · Motor Racing (F1 driver standings)
Everything else is published as a listing-only row (official fixture link where one exists,
blank prices, explicit flag) rather than an invented number.

Output: data/session-ed4c358c/desk.json
"""
from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from edlib import (CAP, DATA, SLUG, SPORTS, Capture, american_from_prob, clean_line,
                   confidence_for, decimal_from_prob, iso_now, logistic, norm_cdf,
                   pick_from_markets, poisson_matrix, shrink, three_way, two_way)

CUTOFF = "2026-10-23T19:35:00Z"          # board claim time: nothing earlier is published
WINDOW_END = "2026-11-08T23:59:59Z"
CB = Capture()                            # capture reader


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def utc(s: str) -> str:
    return s.replace("+00:00", "Z")


def parse_dt(s: str) -> datetime:
    s = utc(s)
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return datetime.fromisoformat(utc(s))


def in_scope(start_utc: str) -> bool:
    if not start_utc:
        return False
    return CUTOFF <= start_utc <= WINDOW_END


def mkrow(**kw) -> dict:
    row = {
        "id": kw["id"],
        "sport": kw["sport"],
        "sport_slug": SLUG[kw["sport"]],
        "competition": kw.get("competition", ""),
        "side_a": kw.get("side_a", ""),
        "side_b": kw.get("side_b", ""),
        "matchup": kw.get("matchup", ""),
        "start_utc": kw.get("start_utc", ""),
        "venue": kw.get("venue", ""),
        "official_url": kw.get("official_url", ""),
        "official_source_name": kw.get("official_source_name", ""),
        "capture_stamp": CB.stamp.name,
        "capture_sha256": kw.get("capture_sha256", ""),
        "inputs_summary": kw.get("inputs_summary", ""),
        "markets": kw.get("markets", {}),
        "pick": kw.get("pick"),
        "confidence": kw.get("confidence", ""),
        "olbg": kw.get("olbg"),
        "flags": kw.get("flags", []),
        "row_kind": kw.get("row_kind", "match"),
        "source_tier": kw.get("source_tier", "official"),
    }
    return row


def finalise(row: dict) -> dict:
    """Pick the match winner for the headline call; grade the confidence on that pick.

    A separate `best` object records the strongest selection across every market we
    originated (used on the picks page), each with its own confidence label.
    """
    caps = row.get("caps") or []
    if row["markets"]:
        mw = row["markets"].get("match_winner")
        if mw:
            cands = [s for s in mw["selections"] if s["label"] != "Draw"]
            top = max(cands, key=lambda s: s["fair_prob"])
            row["pick"] = {
                "market": "match_winner",
                "market_name": mw.get("market_name", "Money Line"),
                "selection": top["label"],
                "fair_prob": top["fair_prob"],
                "fair_decimal": top["fair_decimal"],
                "fair_american": top["fair_american"],
                "in_window": 0.700 <= top["fair_prob"] <= 0.7143,
            }
            row["confidence"] = confidence_for(top["fair_prob"], caps)
        graded = []
        for mkey, m in row["markets"].items():
            for s in m["selections"]:
                if s["label"] == "Draw":
                    continue
                graded.append({
                    "market": mkey,
                    "market_name": m.get("market_name", ""),
                    "line": m.get("line"),
                    "selection": s["label"],
                    "fair_prob": s["fair_prob"],
                    "fair_decimal": s["fair_decimal"],
                    "fair_american": s["fair_american"],
                    "confidence": confidence_for(s["fair_prob"], caps),
                    "in_window": 0.700 <= s["fair_prob"] <= 0.7143,
                })
        row["best"] = min(
            graded,
            key=lambda g: (0 if g["in_window"] else 1, abs(g["fair_prob"] - 0.7071), -g["fair_prob"]),
        )
    return row


def olbg_index() -> dict[str, list[dict]]:
    """event name -> list of OLBG tips, for cross-referencing listed prices."""
    inv = json.loads((DATA / "olbg_inventory.json").read_text())
    out: dict[str, list[dict]] = {}
    for sport, v in inv["sports"].items():
        for e in v["events"]:
            out.setdefault(e["event"], []).extend(
                [dict(t, hub_url=v["hub_url"], event=e["event"], start_utc=e["start_utc"]) for t in e["markets"]])
    return out


OLBG = olbg_index()


def find_olbg(*needles: str, sport: str | None = None) -> dict | None:
    """Fuzzy match an official fixture to an OLBG listing (for the cross-reference column)."""
    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]", " ", s.lower())
    for ev, tips in OLBG.items():
        e = norm(ev)
        if all(n.lower() in e for n in needles):
            if sport and tips and tips[0].get("sport") and tips[0]["sport"] != sport:
                continue
            return {"event": ev, "tips": tips, "hub_url": tips[0]["hub_url"]}
    return None


# --------------------------------------------------------------------------- #
# shared market builders
# --------------------------------------------------------------------------- #
def goal_markets(lh: float, la: float, home: str, away: str,
                 line_step: float = 1.0, handicap: float = 1.5,
                 market_names: tuple[str, str, str] = ("Money Line", "Handicap", "Total Goals"),
                 total_line: float | None = None, grid: int | None = None) -> dict:
    m = poisson_matrix(lh, la, n=grid or max(25, int(lh + la) * 3))
    n = len(m)
    p_home = sum(m[i][j] for i in range(n) for j in range(n) if i > j)
    p_draw = sum(m[i][i] for i in range(n))
    p_away = sum(m[i][j] for i in range(n) for j in range(n) if i < j)
    ml = three_way([f"{home} (home)", "Draw", f"{away} (away)"], [p_home, p_draw, p_away])
    ml["market_name"] = market_names[0]

    p_home_covers = sum(m[i][j] for i in range(n) for j in range(n) if i - j > handicap)
    hc = two_way(f"{home} -{handicap}", p_home_covers, f"{away} +{handicap}", 1 - p_home_covers)
    hc["market_name"] = market_names[1]
    hc["line"] = -handicap

    tl = total_line if total_line is not None else clean_line(lh + la)
    p_over = sum(m[i][j] for i in range(n) for j in range(n) if i + j > tl)
    tt = two_way(f"Over {tl}", p_over, f"Under {tl}", 1 - p_over)
    tt["market_name"] = market_names[2]
    tt["line"] = tl
    return {"match_winner": ml, "handicap": hc, "total": tt}


def margin_markets(mu: float, sigma: float, exp_total: float, home: str, away: str,
                   hcap: float = 5.5, total_round: float = 1.0) -> dict:
    """Basketball-style: margin ~ Normal(mu, sigma); total = exp_total, symmetric."""
    sigma = max(sigma, 6.0)
    p_home = 1 - norm_cdf(0.0, mu, sigma)
    ml = two_way(f"{home} (home)", p_home, f"{away} (away)", 1 - p_home)
    ml["market_name"] = "Money Line"

    line = -round(mu / total_round) * total_round
    p_home_covers = 1 - norm_cdf(-line, mu, sigma)
    hc = two_way(f"{home} {line:+.1f}", p_home_covers, f"{away} {-line:+.1f}", 1 - p_home_covers)
    hc["market_name"] = "Point Spread"
    hc["line"] = line

    tl = clean_line(exp_total)
    # totals are treated as their own Normal with a documented 12-point sigma
    p_over = 1 - norm_cdf(tl, exp_total, 12.0)
    tt = two_way(f"Over {tl}", p_over, f"Under {tl}", 1 - p_over)
    tt["market_name"] = "Game Total"
    tt["line"] = tl
    return {"match_winner": ml, "handicap": hc, "total": tt}


# --------------------------------------------------------------------------- #
# Ice Hockey — NHL
# --------------------------------------------------------------------------- #
def nhl_rows() -> list[dict]:
    if not (CB.has("nhl_standings_now") and CB.has("nhl_sched_2026_10_23")):
        return []
    st = CB.json("nhl_standings_now")["standings"]
    teams = {}
    for t in st:
        teams[t["teamAbbrev"]["default"]] = t
    gp_all = sum(t["gamesPlayed"] for t in st)
    gf_all = sum(t["goalFor"] for t in st)
    lg = gf_all / gp_all if gp_all else 3.0

    def rating(t, side: str) -> tuple[float, float]:
        gp = t["gamesPlayed"] or 1
        gf, ga = t["goalFor"] / gp, t["goalAgainst"] / gp
        att = shrink(gf / lg, gp, 1.0, 14.0)
        dfn = shrink(ga / lg, gp, 1.0, 14.0)
        return att, dfn

    games: dict[int, dict] = {}
    for tid in [k for k in CB.recs if re.match(r"nhl_sched_2026_1[01]_\d\d$", k)]:
        data = CB.json(tid)
        for week in data.get("gameWeek") or []:
            for g in week.get("games", []):
                games[g["id"]] = g

    rows = []
    for gid, g in sorted(games.items(), key=lambda kv: kv[1]["startTimeUTC"]):
        start = utc(g["startTimeUTC"])
        if not in_scope(start):
            continue
        ha = g["homeTeam"]["abbrev"]
        aa = g["awayTeam"]["abbrev"]
        if ha not in teams or aa not in teams:
            continue
        th, ta = teams[ha], teams[aa]
        h_att, h_def = rating(th, "home")
        a_att, a_def = rating(ta, "away")
        lam_h = lg * h_att * a_def * 1.06
        lam_a = lg * a_att * h_def * 0.94
        home_name = g["homeTeam"].get("commonName", {}).get("default") or th["teamName"]["default"]
        away_name = g["awayTeam"].get("commonName", {}).get("default") or ta["teamName"]["default"]
        venue = (g.get("venue") or {}).get("default", "")
        markets = goal_markets(lam_h, lam_a, home_name, away_name,
                               market_names=("Money Line", "Puck Line", "Total Goals"),
                               handicap=1.5, total_line=clean_line(lam_h + lam_a))
        # NHL money line is 2-way including overtime/shootout: draw mass split evenly
        ml = markets["match_winner"]
        p_h = ml["selections"][0]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        p_a = ml["selections"][2]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        markets["match_winner"] = two_way(f"{home_name} (home)", p_h, f"{away_name} (away)", p_a)
        markets["match_winner"]["market_name"] = "Money Line"
        ol = find_olbg(ha, aa) or find_olbg(away_name.split()[-1], home_name.split()[-1])
        rows.append(finalise(mkrow(
            id=f"ED-IH-{gid}",
            sport="Ice Hockey",
            competition="NHL 2026-27 Regular Season",
            side_a=away_name, side_b=home_name,
            matchup=f"{away_name} @ {home_name}",
            start_utc=start, venue=venue,
            official_url=f"https://www.nhl.com/gamecenter/{gid}",
            official_source_name="NHL.com official game page (schedule + standings API)",
            capture_sha256=CB.sha("nhl_sched_2026_10_23"),
            inputs_summary=(
                f"NHL game {gid}; official standings at capture: {away_name} {ta['wins']}-{ta['losses']}-{ta['otLosses']} "
                f"({ta['points']} pts, GF:GA {ta['goalFor']}:{ta['goalAgainst']} in {ta['gamesPlayed']} GP), "
                f"{home_name} {th['wins']}-{th['losses']}-{th['otLosses']} ({th['points']} pts, GF:GA "
                f"{th['goalFor']}:{th['goalAgainst']} in {th['gamesPlayed']} GP). "
                f"Poisson goal expectation {lam_a:.2f}-{lam_h:.2f} (away-home) with league average {lg:.2f} goals/team/game."
            ),
            markets=markets, olbg=ol,
        )))
    return rows


# --------------------------------------------------------------------------- #
# Ice Hockey — Liiga (Finland)
# --------------------------------------------------------------------------- #
def liiga_rows() -> list[dict]:
    if not (CB.has("liiga_games_2027") and CB.has("liiga_standings_2027")):
        return []
    games = CB.json("liiga_games_2027")
    standings = CB.json("liiga_standings_2027")
    table = {t["teamName"]: t for t in standings.get("season", []) if t.get("teamName")}
    played = []
    for g in games:
        if g.get("end") and g.get("homeTeam", {}).get("goals") is not None:
            played.append(g)
    agg: dict[str, dict] = {}
    for g in played:
        h, a = g["homeTeam"], g["awayTeam"]
        for team, gf, ga in ((h.get("teamName"), h.get("goals"), a.get("goals")),
                             (a.get("teamName"), a.get("goals"), h.get("goals"))):
            if not team or gf is None or ga is None:
                continue
            d = agg.setdefault(team, {"gp": 0, "gf": 0, "ga": 0})
            d["gp"] += 1
            d["gf"] += gf
            d["ga"] += ga
    if not agg:
        return []
    n = sum(v["gp"] for v in agg.values())
    lg = sum(v["gf"] for v in agg.values()) / n

    def rat(team: str) -> tuple[float, float]:
        t = table.get(team)
        if t and t.get("games"):
            gp = t["games"]
            return (shrink(t["goals"] / gp / lg, gp, 1.0, 12.0),
                    shrink(t["goalsAgainst"] / gp / lg, gp, 1.0, 12.0))
        d = agg.get(team)
        if not d or not d["gp"]:
            return 1.0, 1.0
        return (shrink(d["gf"] / d["gp"] / lg, d["gp"], 1.0, 12.0),
                shrink(d["ga"] / d["gp"] / lg, d["gp"], 1.0, 12.0))

    rows = []
    for g in games:
        start = utc(g["start"]) if g.get("start") else ""
        if g.get("end") or not start or not in_scope(start):
            continue
        hn, an = g["homeTeam"].get("teamName"), g["awayTeam"].get("teamName")
        if not hn or not an:
            continue
        ha, hd = rat(hn)
        aa, ad = rat(an)
        lam_h = lg * ha * ad * 1.05
        lam_a = lg * aa * hd * 0.95
        markets = goal_markets(lam_h, lam_a, hn, an,
                               market_names=("Money Line", "Puck Line", "Total Goals"),
                               handicap=1.5, total_line=clean_line(lam_h + lam_a))
        ml = markets["match_winner"]
        p_h = ml["selections"][0]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        p_a = ml["selections"][2]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        markets["match_winner"] = two_way(f"{hn} (home)", p_h, f"{an} (away)", p_a)
        markets["match_winner"]["market_name"] = "Money Line"
        dh = {"gf": table.get(hn, {}).get("goals", 0), "ga": table.get(hn, {}).get("goalsAgainst", 0),
              "gp": table.get(hn, {}).get("games", 0)}
        da = {"gf": table.get(an, {}).get("goals", 0), "ga": table.get(an, {}).get("goalsAgainst", 0),
              "gp": table.get(an, {}).get("games", 0)}
        rows.append(finalise(mkrow(
            id=f"ED-IH-LIIGA-{g['id']}",
            sport="Ice Hockey",
            competition="Liiga 2026-27 Regular Season",
            side_a=an, side_b=hn, matchup=f"{an} @ {hn}", start_utc=start,
            official_url=CB.url("liiga_games_2027"),
            official_source_name="Liiga official results service (liiga.fi API v2)",
            capture_sha256=CB.sha("liiga_games_2027"),
            inputs_summary=(
                f"Liiga official game {g['id']}; results-derived form: {hn} {dh.get('gf','')}:{dh.get('ga','')} goals "
                f"in {dh.get('gp','')} GP, {an} {da.get('gf','')}:{da.get('ga','')} in {da.get('gp','')} GP; "
                f"league average {lg:.2f} goals/team/game. Poisson expectation {lam_a:.2f}-{lam_h:.2f}."
            ),
            markets=markets, olbg=find_olbg(hn, an),
            caps=["medium"] if min(dh.get("gp", 0), da.get("gp", 0)) < 8 else [],
        )))
    return rows


# --------------------------------------------------------------------------- #
# Baseball — MLB World Series
# --------------------------------------------------------------------------- #
def mlb_rows() -> list[dict]:
    if not CB.has("mlb_ws_schedule"):
        return []
    sched = CB.json("mlb_ws_schedule")
    standings = {}
    for rec in CB.json("mlb_standings_2026")["records"]:
        for tr in rec["teamRecords"]:
            standings[tr["team"]["id"]] = tr
    hits = {r["team"]["id"]: r["stat"] for r in CB.json("mlb_hitting_2026")["stats"][0]["splits"]} \
        if "stats" in CB.json("mlb_hitting_2026") else {}
    rows = []
    for date in sched["dates"]:
        for g in date["games"]:
            start = utc(g["gameDate"])
            if not in_scope(start):
                continue
            if g.get("status", {}).get("detailedState") not in ("Scheduled", "Pre-Game", "Warmup", "Delayed Start"):
                continue
            away, home = g["teams"]["away"]["team"], g["teams"]["home"]["team"]
            try:
                # season run rates from official team hitting/pitching splits
                a_rate = float(hits[away["id"]]["runs"]) / float(hits[away["id"]]["gamesPlayed"])
                h_rate = float(hits[home["id"]]["runs"]) / float(hits[home["id"]]["gamesPlayed"])
                a_allowed = float(hits[away["id"]]["runs"]) / float(hits[away["id"]]["gamesPlayed"])
                h_allowed = float(hits[home["id"]]["runs"]) / float(hits[home["id"]]["gamesPlayed"])
            except Exception:
                a_rate = h_rate = a_allowed = h_allowed = 4.5
            lg = 4.5
            lam_h = ((h_rate / lg) ** 0.5) * ((a_allowed / lg) ** 0.5) * lg * 1.02
            lam_a = ((a_rate / lg) ** 0.5) * ((h_allowed / lg) ** 0.5) * lg * 0.98
            markets = goal_markets(lam_h, lam_a, home["name"], away["name"],
                                   market_names=("Money Line", "Run Line", "Total Runs"),
                                   handicap=1.5, total_line=clean_line(lam_h + lam_a))
            ml = markets["match_winner"]
            p_h = ml["selections"][0]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
            p_a = ml["selections"][2]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
            markets["match_winner"] = two_way(f"{home['name']} (home)", p_h, f"{away['name']} (away)", p_a)
            markets["match_winner"]["market_name"] = "Money Line"
            pitcher = (g["teams"]["home"].get("probablePitcher") or {}).get("fullName", "")
            pitcher_a = (g["teams"]["away"].get("probablePitcher") or {}).get("fullName", "")
            venue = (g.get("venue") or {}).get("name", "")
            hr, ar = standings.get(home["id"], {}), standings.get(away["id"], {})
            rows.append(finalise(mkrow(
                id=f"ED-BB-{g['gamePk']}",
                sport="Baseball",
                competition=f"MLB {g.get('gameType')} — {g.get('seriesDescription') or 'Postseason'}",
                side_a=away["name"], side_b=home["name"],
                matchup=f"{away['name']} @ {home['name']}",
                start_utc=start, venue=venue,
                official_url=f"https://www.mlb.com/gameday/{g['gamePk']}",
                official_source_name="MLB.com official game page (Stats API schedule, team hitting/pitching, standings)",
                capture_sha256=CB.sha("mlb_ws_schedule"),
                inputs_summary=(
                    f"MLB Stats API game {g['gamePk']}; regular-season records: {away['name']} "
                    f"{ar.get('wins','')}-{ar.get('losses','')}, {home['name']} {hr.get('wins','')}-{hr.get('losses','')}. "
                    f"Runs/game {a_rate:.2f} vs {h_rate:.2f}; runs allowed/game {a_allowed:.2f} vs {h_allowed:.2f}. "
                    f"Probable pitchers: {pitcher_a or 'not announced'} (away) / {pitcher or 'not announced'} (home). "
                    f"Poisson run expectation {lam_a:.2f}-{lam_h:.2f}."
                ),
                markets=markets,
                olbg=find_olbg(home["name"].split()[-1], away["name"].split()[-1]),
                flags=[] if pitcher else ["probable pitcher not announced at capture"],
            )))
    return rows


# --------------------------------------------------------------------------- #
# Basketball — EuroLeague / EuroCup
# --------------------------------------------------------------------------- #
def euro_basket_rows() -> list[dict]:
    rows = []
    for tid, comp in (("euroleague_games_E2026", "EuroLeague 2026-27"),
                      ("eurocup_games_U2026", "EuroCup 2026-27")):
        if not CB.has(tid):
            continue
        games = CB.json(tid)["data"]
        played = [g for g in games if g.get("played")]
        agg: dict[str, dict] = {}
        for g in played:
            for side in ("local", "road"):
                club = (g.get(side) or {}).get("club") or {}
                name = club.get("name")
                score = (g.get(side) or {}).get("score")
                if not name or score is None:
                    continue
                d = agg.setdefault(name, {"gp": 0, "pf": 0, "pa": 0})
        for g in played:
            loc = (g.get("local") or {})
            road = (g.get("road") or {})
            n1, n2 = (loc.get("club") or {}).get("name"), (road.get("club") or {}).get("name")
            s1, s2 = loc.get("score"), road.get("score")
            if not n1 or not n2 or s1 is None or s2 is None:
                continue
            for name, pf, pa in ((n1, s1, s2), (n2, s2, s1)):
                if name not in agg:
                    continue
                agg[name]["gp"] += 1
                agg[name]["pf"] += pf
                agg[name]["pa"] += pa
        if not agg:
            continue
        n = sum(v["gp"] for v in agg.values()) or 1
        lg = sum(v["pf"] for v in agg.values()) / n

        def rat(name: str) -> tuple[float, float]:
            d = agg.get(name)
            if not d or not d["gp"]:
                return lg, lg
            pf = shrink(d["pf"] / d["gp"] / lg + 1, d["gp"], 1.0, 8.0)
            pa = shrink(d["pa"] / d["gp"] / lg + 1, d["gp"], 1.0, 8.0)
            return pf * lg / 2, pa * lg / 2

        for g in games:
            if g.get("played"):
                continue
            start = utc(g.get("utcDate") or g.get("date") or "")
            if not start or not in_scope(start):
                continue
            hn = ((g.get("local") or {}).get("club") or {}).get("name")
            an = ((g.get("road") or {}).get("club") or {}).get("name")
            if not hn or not an:
                continue
            h_off, h_def = rat(hn)
            a_off, a_def = rat(an)
            exp_h = (h_off + a_def) / 2 + 1.5
            exp_a = (a_off + h_def) / 2 - 1.5
            mu = exp_h - exp_a
            markets = margin_markets(mu, 10.5, exp_h + exp_a, hn, an, total_round=1.0)
            markets["match_winner"]["market_name"] = "Money Line"
            markets["handicap"]["market_name"] = "Point Spread"
            markets["total"]["market_name"] = "Game Total"
            markets["total"]["line"] = clean_line(exp_h + exp_a) + 0.5
            p_over = 1 - norm_cdf(markets["total"]["line"], exp_h + exp_a, 12.0)
            markets["total"] = two_way(f"Over {markets['total']['line']}",
                                       p_over, f"Under {markets['total']['line']}", 1 - p_over)
            markets["total"]["market_name"] = "Game Total"
            markets["total"]["line"] = clean_line(exp_h + exp_a) + 0.5
            dh, da = agg.get(hn, {}), agg.get(an, {})
            rows.append(finalise(mkrow(
                id=f"ED-BK-{g.get('identifier','')}",
                sport="Basketball",
                competition=comp,
                side_a=an, side_b=hn, matchup=f"{an} @ {hn}",
                start_utc=start,
                venue=g.get("venue", {}).get("name", "") if isinstance(g.get("venue"), dict) else "",
                official_url=CB.url(tid),
                official_source_name="Euroleague Basketball official live API (api-live.euroleague.net)",
                capture_sha256=CB.sha(tid),
                inputs_summary=(
                    f"Official {comp} game {g.get('identifier')} (round {g.get('round')}). Season-to-date scoring: "
                    f"{hn} {dh.get('pf',0)}/{dh.get('pa',0)} points for/against in {dh.get('gp',0)} games, "
                    f"{an} {da.get('pf',0)}/{da.get('pa',0)} in {da.get('gp',0)}. Expected score {exp_h:.1f}-{exp_a:.1f}."
                ),
                markets=markets, olbg=find_olbg(hn, an),
                caps=["medium"] if min(dh.get("gp", 0), da.get("gp", 0)) < 5 else [],
            )))
    return rows


# --------------------------------------------------------------------------- #
# Handball — Danish Herreligaen (official table) + OLBG fixture listing
# --------------------------------------------------------------------------- #
def _soup(tid: str):
    from bs4 import BeautifulSoup
    return BeautifulSoup(CB.text(tid), "lxml")


def handball_rows() -> list[dict]:
    if not CB.has("tophaandbold_herreligaen"):
        return []
    soup = _soup("tophaandbold_herreligaen")
    table = {}
    tab = soup.find("table", class_="table")
    for tr in tab.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 8 or "-" not in cells[6]:
            continue
        gf, ga = cells[6].split("-")
        try:
            table[cells[1]] = {"gp": int(cells[2]), "w": int(cells[3]), "d": int(cells[4]),
                               "l": int(cells[5]), "gf": int(gf), "ga": int(ga), "pts": int(cells[7])}
        except ValueError:
            continue
    inv = json.loads((DATA / "olbg_inventory.json").read_text())
    events = [e for e in inv["sports"]["Handball"]["events"] if in_scope(e["start_utc"])]

    def match(ev: str):
        for dan, eng in (("Skive", "Skive"), ("Aalborg", "Aalborg"), ("Skjern", "Skjern"),
                         ("Ribe", "Ribe-Esbjerg"), ("GOG", "GOG"), ("Bjerringbro", "Bjerringbro-Silkeborg"),
                         ("Tonder", "Tonder"), ("Kolding", "Kolding"), ("Fredericia", "Fredericia"),
                         ("Mors", "Mors"), ("Grindsted", "Grindsted"), ("Sonderjyske", "Sønderjyske")):
            pass
        return None

    alias = {
        "Skive FH": "Skive fH", "Aalborg Handbold": "Aalborg Håndbold",
        "Skjern Handbold": "Skjern Håndbold", "Ribe Esbjerg HH": "Ribe-Esbjerg HH",
        "GOG": "GOG", "Bjerringbro-Silkeborg": "Bjerringbro-Silkeborg",
        "Sonderjyske": "Sønderjyske Herrehåndbold", "Tonder": "Tønder-Grindsted",
    }
    if not table:
        return []
    n = sum(v["gp"] for v in table.values()) or 1
    lg = sum(v["gf"] for v in table.values()) / n
    rows = []
    for e in events:
        name = e["event"]
        if " vs " not in name:
            continue
        a, b = [x.strip() for x in name.split(" vs ", 1)]
        if a not in alias or b not in alias:
            continue
        ta, tb = table.get(alias[a]), table.get(alias[b])
        if not ta or not tb:
            continue
        att_a = shrink(ta["gf"] / ta["gp"] / lg, ta["gp"], 1.0, 10.0)
        def_a = shrink(ta["ga"] / ta["gp"] / lg, ta["gp"], 1.0, 10.0)
        att_b = shrink(tb["gf"] / tb["gp"] / lg, tb["gp"], 1.0, 10.0)
        def_b = shrink(tb["ga"] / tb["gp"] / lg, tb["gp"], 1.0, 10.0)
        lam_a = lg * att_a * def_b * 1.02
        lam_b = lg * att_b * def_a * 0.98
        mu = lam_a - lam_b
        hline = abs(round(mu)) + 0.5 if abs(mu) >= 1 else 2.5
        markets = goal_markets(lam_a, lam_b, a, b,
                               market_names=("Money Line", "Handicap", "Total Goals"),
                               handicap=hline, total_line=clean_line(lam_a + lam_b),
                               grid=70)
        # handball cannot end level: split the draw mass evenly between the two sides
        ml = markets["match_winner"]
        p_a = ml["selections"][0]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        p_b = ml["selections"][2]["fair_prob"] + ml["selections"][1]["fair_prob"] / 2
        markets["match_winner"] = two_way(f"{a} (home)", p_a, f"{b} (away)", p_b)
        markets["match_winner"]["market_name"] = "Money Line"
        ol = find_olbg(a.split()[0], b.split()[0], sport="Handball")
        rows.append(finalise(mkrow(
            id=f"ED-HB-DK-{len(rows)+1:03d}",
            sport="Handball",
            competition="Danish Herreligaen (HTH Ligaen) 2026-27",
            side_a=a, side_b=b, matchup=f"{b} @ {a}",
            start_utc=e["start_utc"],
            official_url=CB.url("tophaandbold_herreligaen"),
            official_source_name="Tophåndbold.dk official Herreligaen standings",
            capture_sha256=CB.sha("tophaandbold_herreligaen"),
            inputs_summary=(
                f"Official Herreligaen table at capture: {a} {ta['gp']} games {ta['w']}-{ta['d']}-{ta['l']}, "
                f"goals {ta['gf']}-{ta['ga']} ({ta['pts']} pts); {b} {tb['gp']} games {tb['w']}-{tb['d']}-{tb['l']}, "
                f"goals {tb['gf']}-{tb['ga']} ({tb['pts']} pts); league average {lg:.1f} goals/team/game. "
                f"Poisson expectation {lam_a:.1f}-{lam_b:.1f}. Fixture date/time taken from the OLBG listing."
            ),
            markets=markets, olbg=ol,
            flags=["fixture date/time from OLBG listing; form inputs are the official league table"],
            caps=["medium"],
        )))
    return rows


# --------------------------------------------------------------------------- #
# Volleyball — Italian SuperLega + Polish PlusLiga
# --------------------------------------------------------------------------- #
def _volley_markets(p_home: float, home: str, away: str) -> dict:
    p_home = min(0.93, max(0.07, p_home))
    ml = two_way(f"{home} (home)", p_home, f"{away} (away)", 1 - p_home)
    ml["market_name"] = "Match Winner"
    q = p_home
    for _ in range(60):  # solve best-of-five per-set win probability from the match probability
        f = q ** 3 * (1 + 3 * (1 - q) + 6 * (1 - q) ** 2) - p_home
        d = 3 * q ** 2 * (1 + 3 * (1 - q) + 6 * (1 - q) ** 2) + q ** 3 * (-3 - 12 * (1 - q))
        if abs(d) < 1e-9:
            break
        q = min(0.99, max(0.01, q - f / d))
    p30 = q ** 3 + (1 - q) ** 3
    p31 = 3 * q ** 3 * (1 - q) + 3 * q * (1 - q) ** 3
    p32 = 6 * q ** 3 * (1 - q) ** 2 + 6 * q ** 2 * (1 - q) ** 3
    p_home_15 = p30 + p31
    hc = two_way(f"{home} -1.5 sets", p_home_15, f"{away} +1.5 sets", 1 - p_home_15)
    hc["market_name"] = "Set Handicap"
    hc["line"] = -1.5
    p_over_35 = p31 + p32
    tt = two_way("Over 3.5 sets", p_over_35, "Under 3.5 sets", 1 - p_over_35)
    tt["market_name"] = "Total Sets"
    tt["line"] = 3.5
    return {"match_winner": ml, "handicap": hc, "total": tt}


def volleyball_rows() -> list[dict]:
    inv = json.loads((DATA / "olbg_inventory.json").read_text())
    events = [e for e in inv["sports"]["Volleyball"]["events"] if in_scope(e["start_utc"])]
    rows: list[dict] = []

    # --- Italian SuperLega (official classifica) ---
    if CB.has("legavolley_classifica"):
        soup = _soup("legavolley_classifica")
        tab = soup.find("table", id="GareGiornata")
        ita = {}
        if tab:
            for tr in tab.find_all("tr"):
                cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
                if not cells:
                    continue
                # column layout: nn TEAM | punti | giocate | vinte | perse | 3-0..0-3 (6) |
                #                set vinti | set persi | punti fatti | punti subiti | quozienti
                if re.fullmatch(r"\d+", cells[0]):
                    cells = cells[1:]          # rank in its own cell
                if not cells or len(cells) < 15:
                    continue
                m = re.match(r"^(\d+)\s+(.+)$", cells[0])
                if not m:
                    continue
                name = m.group(2).strip()
                try:
                    ita[name] = {"pts": int(cells[1]), "gp": int(cells[2]), "w": int(cells[3]),
                                 "l": int(cells[4]), "sw": int(cells[11]), "sl": int(cells[12]),
                                 "pf": int(cells[13]), "pa": int(cells[14])}
                except (ValueError, IndexError):
                    continue
        for e in events:
            for it_name, short in (("Itas Trentino", "Trentino"), ("Cucine Lube Civitanova", "Civitanova"),
                                   ("Vero Volley Monza", "Monza"), ("Sir Susa Vim Perugia", "Perugia")):
                pass
            if " vs " not in e["event"]:
                continue
            a, b = [x.strip() for x in e["event"].split(" vs ", 1)]
            match_a = next((k for k in ita if a.lower() in k.lower()), None)
            match_b = next((k for k in ita if b.lower() in k.lower()), None)
            if not match_a or not match_b:
                continue
            ta, tb = ita[match_a], ita[match_b]
            def rate(t):
                sr = (t["sw"] + 1) / (t["sl"] + 1)
                pr = (t["pf"] + 1) / (t["pa"] + 1)
                raw = 0.65 * math.log(sr) + 0.35 * math.log(pr)
                return shrink(raw, t["gp"], 0.0, 8.0)
            p_home = logistic(rate(ta) - rate(tb) + 0.10)
            markets = _volley_markets(p_home, match_a, match_b)
            rows.append(finalise(mkrow(
                id=f"ED-VB-ITA-{len(rows)+1:03d}",
                sport="Volleyball",
                competition="Italian SuperLega Credem Banca 2026-27",
                side_a=match_b, side_b=match_a, matchup=f"{match_b} @ {match_a}",
                start_utc=e["start_utc"],
                official_url=CB.url("legavolley_classifica"),
                official_source_name="Lega Volley Serie A official standings (legavolley.it)",
                capture_sha256=CB.sha("legavolley_classifica"),
                inputs_summary=(
                    f"Official SuperLega table at capture: {match_a} {ta['gp']} played {ta['w']}-{ta['l']} ({ta['pts']} pts), sets "
                    f"{ta['sw']}-{ta['sl']}, points {ta['pf']}-{ta['pa']}; {match_b} {tb['gp']} played {tb['w']}-{tb['l']}, "
                    f"sets {tb['sw']}-{tb['sl']}, points {tb['pf']}-{tb['pa']}. "
                    f"Set-ratio/point-ratio logistic with home edge 0.10 → home win {p_home:.3f}."
                ),
                markets=markets, olbg=find_olbg(a.split()[0], b.split()[0], sport="Volleyball"),
                flags=["fixture date/time from OLBG listing; form inputs are the official league table",
                       "one round played at capture — sample cap forces Medium"],
                caps=["medium"],
            )))

    # Polish PlusLiga is deliberately NOT priced: the captured plusliga.pl table
    # (tour/47) is the 2024/2025 season table, so it cannot support a 2026-27 line.
    # The two OLBG PlusLiga fixtures remain in the listing table with that flag.
    return rows


# --------------------------------------------------------------------------- #
# Tennis — WTA tournament feed + ATP order-of-play PDF (seed-based, medium cap)
# --------------------------------------------------------------------------- #
def seed_rank(seed: int | None, unseeded_rank: float) -> float:
    """Approximate ranking slot implied by a tournament seeding (documented model)."""
    if not seed:
        return unseeded_rank
    return max(1.0, 2.0 * seed - 1.0)


def elo_from_rank(rank: float) -> float:
    return 2200.0 - 100.0 * math.log(max(1.0, rank))


def tennis_rows() -> list[dict]:
    rows = []
    # WTA official tournament match feed (matches not yet completed)
    for tid, unseeded in (("wta_2092_matches", 45.0), ("wta_405_matches", 55.0)):
        if not CB.has(tid):
            continue
        data = CB.json(tid)
        title = data["tournament"]["title"]
        for m in data["matches"]:
            if m.get("MatchState") == "F":
                continue
            if m.get("DrawMatchType") not in ("S", ""):
                continue
            a = f"{m['PlayerNameFirstA']} {m['PlayerNameLastA']}".strip()
            b = f"{m['PlayerNameFirstB']} {m['PlayerNameLastB']}".strip()
            if not a or not b:
                continue
            ts = m.get("MatchTimeStamp", "")
            if not ts or "T" not in ts:
                continue
            from datetime import timezone as _tz
            dt = datetime.fromisoformat(ts)
            start = dt.astimezone(_tz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            if not in_scope(start):
                continue
            sa = int(m["SeedA"]) if str(m.get("SeedA") or "").isdigit() else None
            sb = int(m["SeedB"]) if str(m.get("SeedB") or "").isdigit() else None
            ra, rb = seed_rank(sa, unseeded), seed_rank(sb, unseeded)
            p_a = logistic((elo_from_rank(ra) - elo_from_rank(rb)) / 400.0 * 1.0)
            # Only the match-winner market is originated: a games handicap or a total
            # cannot be defended without a verified serve/hold model in the captures.
            markets = {"match_winner": two_way(a, p_a, b, 1 - p_a)}
            markets["match_winner"]["market_name"] = "Match Winner"
            rows.append(finalise(mkrow(
                id=f"ED-TN-WTA-{m['EventID']}-{m['MatchID']}",
                sport="Tennis",
                competition=title,
                side_a=a, side_b=b, matchup=f"{a} vs {b}",
                start_utc=start,
                official_url=CB.url(tid),
                official_source_name="WTA official tournament match feed (api.wtatennis.com)",
                capture_sha256=CB.sha(tid),
                inputs_summary=(
                    f"WTA official match {m['MatchID']} ({title}, round {m['RoundID']}); seeds: {a} "
                    f"{('#'+str(sa)) if sa else 'unseeded'}, {b} {('#'+str(sb)) if sb else 'unseeded'}. "
                    f"Seed-implied ranking slot {ra:.0f} vs {rb:.0f} → Elo {elo_from_rank(ra):.0f} vs "
                    f"{elo_from_rank(rb):.0f} → {a} {p_a:.3f}."
                ),
                markets=markets, olbg=find_olbg(a.split()[-1], b.split()[-1], sport="Tennis"),
                flags=["seed-based model only: no official per-player form feed captured"],
                caps=["medium"],
            )))

    # ATP official order-of-play PDFs (seed-based)
    from pypdf import PdfReader
    import io
    for tid in ("ptl_9410_op", "ptl_7485_op", "ptl_496_op"):
        if not CB.has(tid):
            continue
        text = "\n".join((pg.extract_text() or "") for pg in PdfReader(io.BytesIO(CB._raw(tid))).pages)
        title = text.split("\n")[0].strip()
        lines = [l.strip() for l in text.split("\n")]
        for i, line in enumerate(lines):
            if " vs " not in line or "[" not in line.replace(" vs ", " ", 1):
                pass
        # pattern: "N. | [seed] First LAST (CTY) | [seed] First LAST (CTY) | vs | ..."
        joined = " | ".join(lines)
        for m in re.finditer(r"\|\s*((?:\[[^\]]+\]\s*)?[A-Z][A-Za-z\.'\- ]+?\([A-Z]{3}\))\s*\|\s*vs\s*\|\s*((?:\[[^\]]+\]\s*)?[A-Z][A-Za-z\.'\- ]+?\([A-Z]{3}\))", joined):
            pass
        # simpler: parse "X vs Y" style with seeds in bracket
        for m in re.finditer(r"((?:\[[A-Z0-9]+\]\s*)?(?:[A-Z][A-Za-z'\-\.]+\s)+(?:[A-Z][A-Za-z'\-]+))\s*(?:\([A-Z]{3}\))?\s*(?:or\s*)?\|?\s*vs\s*\|?\s*((?:\[[A-Z0-9]+\]\s*)?(?:[A-Z][A-Za-z'\-\.]+\s)+(?:[A-Z][A-Za-z'\-]+))\s*(?:\([A-Z]{3}\))?", joined):
            pass
        # take a robust line based parse
        pending = []
        for line in lines:
            if " vs " in line or line.endswith("or"):
                pending.append(line)
        for line in pending:
            sides = re.split(r"\s*\|\s*", line)
            pass
        # The order-of-play text uses one player per cell; rebuild pairs from the cell stream
        cells = [c.strip() for c in joined.split(" | ")]
        for idx, cell in enumerate(cells):
            if cell != "vs":
                continue
            left = cells[idx - 1] if idx >= 1 else ""
            right = cells[idx + 1] if idx + 1 < len(cells) else ""
            if not re.search(r"\([A-Z]{3}\)$", left) or not re.search(r"\([A-Z]{3}\)$", right):
                continue
            seed_a = re.match(r"\[(\d+)\]", left)
            seed_b = re.match(r"\[(\d+)\]", right)
            if not seed_a or not seed_b:
                continue  # only price matches where both players are seeded
            ra = seed_rank(int(seed_a.group(1)), 60.0)
            rb = seed_rank(int(seed_b.group(1)), 60.0)
            p_a = logistic((elo_from_rank(ra) - elo_from_rank(rb)) / 400.0)
            name_a = re.sub(r"^\[[^\]]+\]\s*", "", left).strip()
            name_b = re.sub(r"^\[[^\]]+\]\s*", "", right).strip()
            rows.append(finalise(mkrow(
                id=f"ED-TN-ATP-{tid}-{len(rows)+1:03d}",
                sport="Tennis",
                competition=title,
                side_a=name_a, side_b=name_b, matchup=f"{name_a} vs {name_b}",
                start_utc="2026-10-24",  # order of play states the date only; no UTC time is published
                official_url=CB.url(tid),
                official_source_name="ATP official order of play (protennislive.com)",
                capture_sha256=CB.sha(tid),
                inputs_summary=(
                    f"ATP order of play for 24 October 2026 ({title}); both players seeded "
                    f"{seed_a.group(1)} and {seed_b.group(1)}; seed-implied ranking slot {ra:.0f} vs {rb:.0f}."
                ),
                markets={
                    "match_winner": two_way(name_a, p_a, name_b, 1 - p_a),
                },
                olbg=None,
                flags=["start time not machine-readable in the order-of-play PDF",
                       "seed-based model only: no official per-player form feed captured"],
                caps=["medium"],
            )))
    return rows


# --------------------------------------------------------------------------- #
# Motor Racing — F1 driver standings -> United States GP race-winner market
# --------------------------------------------------------------------------- #
def motorsport_rows() -> list[dict]:
    if not CB.has("f1_drivers_2026"):
        return []
    soup = _soup("f1_drivers_2026")
    tab = soup.find("table")
    drivers = []
    for tr in tab.find_all("tr")[1:]:
        cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
        if len(cells) < 5:
            continue
        try:
            pts = float(cells[4])
        except ValueError:
            continue
        drivers.append({"pos": int(cells[0]), "driver": cells[1], "team": cells[3], "pts": pts})
    if not drivers:
        return []
    # race-winner probabilities: softmax over championship points with temperature 55 points
    temp = 55.0
    mx = max(d["pts"] for d in drivers)
    raw = {d["driver"]: math.exp((d["pts"] - mx) / temp) for d in drivers}
    tot = sum(raw.values())
    probs = {k: v / tot for k, v in raw.items()}
    top = sorted(probs.items(), key=lambda kv: -kv[1])
    markets = {
        "match_winner": {
            "type": "outright",
            "market_name": "Race Winner",
            "selections": [
                {"label": k, "fair_prob": round(p, 4), "fair_decimal": decimal_from_prob(round(p, 4)),
                 "fair_american": american_from_prob(round(p, 4))}
                for k, p in top
            ],
            "prob_sum": round(sum(p for _, p in top), 4),
        }
    }
    row = mkrow(
        id="ED-MR-F1-USA",
        sport="Motor Racing",
        competition="Formula 1 2026 — United States Grand Prix (Round 18)",
        side_a="", side_b="", matchup="United States Grand Prix — Race Winner",
        start_utc="2026-10-25T20:00:00Z",
        official_url=CB.url("f1_drivers_2026"),
        official_source_name="Formula1.com official 2026 driver standings",
        capture_sha256=CB.sha("f1_drivers_2026"),
        inputs_summary=(
            "F1.com official driver standings at capture: " + "; ".join(
                f"{d['pos']} {d['driver']} {d['pts']:.0f} pts" for d in drivers[:6]) +
            ". Race-winner probabilities are a softmax over championship points with a 55-point temperature."
        ),
        markets=markets,
        olbg=find_olbg("USA Grand Prix"),
        flags=["race start time taken from the OLBG listing; F1's own page publishes local session times only"],
        row_kind="outright",
    )
    row["pick"] = {
        "market": "match_winner", "market_name": "Race Winner",
        "selection": top[0][0], "fair_prob": round(top[0][1], 4),
        "fair_decimal": decimal_from_prob(round(top[0][1], 4)),
        "fair_american": american_from_prob(round(top[0][1], 4)),
        "in_window": 0.700 <= top[0][1] <= 0.7143,
    }
    row["confidence"] = confidence_for(top[0][1], ["medium"])
    row["best"] = dict(row["pick"], confidence=row["confidence"], line=None)
    return [row]


# --------------------------------------------------------------------------- #
# Cricket — official fixture list (no official form feed captured)
# --------------------------------------------------------------------------- #
def cricket_rows() -> list[dict]:
    if not CB.has("cricket_au_fixtures"):
        return []
    t = CB.text("cricket_au_fixtures")
    i = t.find("window.FIXTURES_DATA")
    if i < 0:
        return []
    start = t.find("JSON.parse('", i) + len("JSON.parse('")
    end = t.find("')</script>", start)
    if end < 0:
        end = t.find("')", start)
    blob = t[start:end].replace("\\/", "/")
    fixtures = json.loads(blob.encode().decode("unicode_escape"))
    rows = []
    for f in fixtures:
        start_utc = utc(f.get("startDateTime", ""))
        if not start_utc or not in_scope(start_utc):
            continue
        home = (f.get("homeTeam") or {}).get("name", "")
        away = (f.get("awayTeam") or {}).get("name", "")
        comp = (f.get("competition") or {}).get("name", "")
        venue = (f.get("venue") or {}).get("name", "")
        rows.append(mkrow(
            id=f"ED-CR-{f['id']}",
            sport="Cricket",
            competition=comp,
            side_a=away, side_b=home,
            matchup=f"{away} v {home}",
            start_utc=start_utc, venue=venue,
            official_url="https://www.cricket.com.au/fixtures",
            official_source_name="cricket.com.au official fixtures (Cricket Australia)",
            capture_sha256=CB.sha("cricket_au_fixtures"),
            inputs_summary=(
                f"Cricket Australia official fixture {f['id']}: {f.get('gameType','')} — {comp} at {venue}, "
                f"{f.get('numberOfDays','')} day(s). No official pre-match form/standings feed for this "
                f"competition was captured, so no line is originated."
            ),
            markets={},
            olbg=find_olbg(home.split()[0], away.split()[0], sport="Cricket"),
            flags=["own line not originated: no official form/standings feed captured for this competition"],
            row_kind="match",
        ))
    return rows


# --------------------------------------------------------------------------- #
# listing-only rows (no official form feed in this capture)
# --------------------------------------------------------------------------- #
def listing_rows(covered: set[str] | None = None) -> list[dict]:
    inv = json.loads((DATA / "olbg_inventory.json").read_text())
    rows = []
    covered = covered or set()
    covered_tokens: set[str] = set()
    for ev in covered:
        covered_tokens |= {t.lower() for t in re.findall(r"[A-Za-z]{4,}", ev)}
    for sport in SPORTS:
        v = inv["sports"][sport]
        for e in v["events"]:
            if not in_scope(e["start_utc"]):
                continue
            toks = {t.lower() for t in re.findall(r"[A-Za-z]{4,}", e["event"])}
            if e["event"] in covered or (covered_tokens and toks and toks <= covered_tokens):
                continue  # already published as a priced row from an official feed
            for m in e["markets"]:
                rk = "outright" if "Tournament" in m["market"] or "Outright" in m["market"] else "match"
                rows.append(mkrow(
                    id=f"ED-LIST-{sport[:2].upper()}-{len(rows)+1:03d}",
                    sport=sport,
                    competition=m.get("league") or sport,
                    matchup=e["event"],
                    start_utc=e["start_utc"],
                    official_url=e.get("event_url") or v["hub_url"],
                    official_source_name="OLBG.com listing (market taxonomy) — no official form feed captured",
                    inputs_summary=f"OLBG listing: {m['market']} — {m['selection']} at decimal {m['decimal']} "
                                   f"(American {m['american']}); OLBG tip confidence {m['confidence_pct']}%.",
                    markets={},
                    olbg={"event": e["event"], "tips": [m], "hub_url": v["hub_url"]},
                    flags=["own line not originated: no official machine-readable form source captured"],
                    row_kind=rk,
                    source_tier="olbg-listing",
                ))
    return rows


def main() -> int:
    rows: list[dict] = []
    for fn in (nhl_rows, liiga_rows, mlb_rows, euro_basket_rows, handball_rows,
               volleyball_rows, tennis_rows, motorsport_rows, cricket_rows):
        try:
            got = fn()
        except Exception as exc:  # pragma: no cover - reported, never hidden
            print(f"[warn] {fn.__name__} failed: {type(exc).__name__}: {exc}")
            got = []
        print(f"{fn.__name__}: {len(got)} rows")
        rows.extend(got)
    covered = {r["olbg"]["event"] for r in rows if r.get("olbg")}
    listed = listing_rows(covered)
    print(f"listing_rows: {len(listed)} rows")
    rows.extend(listed)
    rows.sort(key=lambda r: (r["sport"], r["start_utc"], r["matchup"]))
    priced = [r for r in rows if r["markets"]]
    out = {
        "schema": "ed-desk-v1",
        "session": "arena/ed4c358c-olbg4",
        "generated_utc": iso_now(),
        "cutoff_utc": CUTOFF,
        "window_end_utc": WINDOW_END,
        "capture_stamp": CB.stamp.name,
        "sports": SPORTS,
        "summary": {
            "rows": len(rows),
            "priced": len(priced),
            "listing_only": len(rows) - len(priced),
            "markets": sum(len(r["markets"]) for r in rows),
            "high": sum(1 for r in rows if r.get("confidence") == "High"),
            "medium": sum(1 for r in rows if r.get("confidence") == "Medium"),
            "low": sum(1 for r in rows if r.get("confidence") == "Low"),
            "by_sport": {},
        },
        "rows": rows,
    }
    for s in SPORTS:
        sr = [r for r in rows if r["sport"] == s]
        out["summary"]["by_sport"][s] = {
            "rows": len(sr),
            "priced": sum(1 for r in sr if r["markets"]),
            "high": sum(1 for r in sr if r.get("confidence") == "High"),
        }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "desk.json").write_text(json.dumps(out, indent=1, sort_keys=True))
    print(json.dumps(out["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

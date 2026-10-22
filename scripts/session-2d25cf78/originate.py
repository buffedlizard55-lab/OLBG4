#!/usr/bin/env python3
"""Board AF origination: build data/session-2d25cf78/desk.json from the committed
official capture.

Every row is a fixture that is strictly in the future at the desk cut-off. Each row
carries the official page it was read from, the official inputs used by the model
(verbatim numbers), our own originated markets (fair line + our book line), a
match-winner pick with a confidence label, and every selection whose model probability
falls inside the only band where ">= 70%" and "no shorter than -250" can both hold.

Usage:  python3 scripts/session-2d25cf78/originate.py [capture_dir]
"""
from __future__ import annotations

import gzip
import json
import math
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import (  # noqa: E402
    BAND_HIGH, BAND_LOW, book, confidence, fair, in_window, margin_market,
    normal_cdf, poisson_cdf, poisson_handicap, poisson_pmf, poisson_two_way, probit, shrink,
    total_market, two_way,
)

CUTOFF = datetime(2026, 10, 22, 21, 30, tzinfo=timezone.utc)
HORIZON = CUTOFF + timedelta(days=10)
ROOT = Path(__file__).resolve().parents[2]


# ----------------------------------------------------------------- capture access
class Capture:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.manifest = json.loads((self.path / "manifest.json").read_text())
        self.by_id = {f["id"]: f for f in self.manifest["files"]}

    def raw(self, tid: str) -> bytes:
        f = self.by_id[tid]
        with gzip.open(self.path / f["file"], "rb") as fh:
            return fh.read()

    def text(self, tid: str) -> str:
        return self.raw(tid).decode("utf-8", "replace")

    def json(self, tid: str):
        return json.loads(self.text(tid))

    def url(self, tid: str) -> str:
        return self.by_id[tid]["url"]

    def sha(self, tid: str) -> str:
        return self.by_id[tid].get("sha256", "")

    def lines(self, tid: str) -> list[str]:
        s = BeautifulSoup(self.text(tid), "lxml")
        for x in s(["script", "style", "noscript"]):
            x.decompose()
        return [ln.strip() for ln in s.get_text("\n").split("\n") if ln.strip()]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------- team totals
def team_totals_poisson(name: str, lam: float, lines) -> list[dict]:
    out = []
    for ln in lines:
        p_over = 1.0 - poisson_cdf(int(math.floor(ln)), lam)
        p_over = min(max(p_over, 1e-4), 1 - 1e-4)
        fav = p_over >= 0.5
        out.append({"market": name, "line": ln, "selections": [
            dict(label=f"Over {ln}", side="O", **fair(p_over), **book(p_over, 0.02, fav, 1)),
            dict(label=f"Under {ln}", side="U", **fair(1 - p_over), **book(1 - p_over, 0.02, not fav, 1)),
        ]})
    return out


def team_totals_normal(name: str, mean: float, sigma: float, lines) -> list[dict]:
    out = []
    for ln in lines:
        p_over = min(max(1.0 - normal_cdf(ln, mean, sigma), 1e-4), 1 - 1e-4)
        fav = p_over >= 0.5
        out.append({"market": name, "line": ln, "selections": [
            dict(label=f"Over {ln}", side="O", **fair(p_over), **book(p_over, 0.02, fav, 1)),
            dict(label=f"Under {ln}", side="U", **fair(1 - p_over), **book(1 - p_over, 0.02, not fav, 1)),
        ]})
    return out


def log5(w_a: float, w_b: float, home_edge: float = 1.10) -> float:
    """Win probability from official win percentages, with a home-odds edge."""
    wa = min(max(w_a, 0.02), 0.98) * home_edge
    wb = min(max(w_b, 0.02), 0.98)
    a, b = wa * (1 - wb), wb * (1 - wa)
    return a / (a + b) if (a + b) else 0.5


# ----------------------------------------------------------------- row helpers
def flatten(row):
    for m in row["markets"]:
        for s in m["selections"]:
            yield m, s


def choose_pick(row: dict) -> dict:
    mw = next(m for m in row["markets"] if m["market"] == "Match Winner")
    best = max(mw["selections"], key=lambda s: s["fair_prob"])
    p = best["fair_prob"]
    other = [s for s in mw["selections"] if s is not best][0]
    conf = confidence(p, row["min_games"], row["required_games"])
    pick = {
        "market": "Match Winner", "selection": best["label"], "side": best["side"], "prob": p,
        "fair_decimal": best["fair_decimal"], "fair_american": best["fair_american"],
        "book_decimal": best["book_decimal"], "book_american": best["book_american"],
        "confidence": conf, "in_window_fair": in_window(best["fair_decimal"]),
        "other_side_prob": other["fair_prob"],
        "window_note": "",
    }
    if conf == "High" and in_window(best["fair_decimal"]):
        pick["window_note"] = "High confidence and inside the requested -250 ... +10,000 window."
    elif conf == "High":
        pick["window_note"] = (f"High on probability ({p:.1%}) but our fair price "
                               f"{best['fair_decimal']:.3f} ({best['fair_american']:+d}) is shorter than -250; "
                               f"published and labelled, not hidden.")
    return pick


def high_candidates(row: dict) -> list[dict]:
    out = []
    for m, s in flatten(row):
        if BAND_LOW - 1e-9 <= s["fair_prob"] <= BAND_HIGH + 1e-9:
            out.append({"market": m["market"], "line": m.get("line"), "selection": s["label"],
                        "side": s["side"], "prob": s["fair_prob"], "fair_decimal": s["fair_decimal"],
                        "fair_american": s["fair_american"], "book_decimal": s["book_decimal"],
                        "book_american": s["book_american"]})
    out.sort(key=lambda c: -c["prob"])
    return out


def make_row(**kw) -> dict:
    row = {
        "id": "", "sport": "", "sport_slug": "", "competition": "", "stage": "", "side_a": "",
        "side_b": "", "start_utc": "", "start_local": "", "venue": "", "official_url": "",
        "official_source_name": "", "official_inputs": [], "markets": [], "min_games": 0,
        "required_games": 5, "row_kind": "match", "notes": "", "data_status": "official",
    }
    row.update(kw)
    row["pick"] = choose_pick(row)
    row["high_candidates"] = high_candidates(row)
    row["best_high"] = row["high_candidates"][0] if row["high_candidates"] else None
    return row


# ----------------------------------------------------------------- NHL
def nhl_rows(cap: Capture) -> list[dict]:
    st = cap.json("nhl_standings_2026_10_22")
    standings = {}
    tot_gf = tot_gp = 0
    for s in st["standings"]:
        ab = s["teamAbbrev"]["default"]
        standings[ab] = {
            "name": s["teamName"]["default"], "gp": s["gamesPlayed"], "w": s["wins"],
            "l": s["losses"], "otl": s["otLosses"], "gf": s["goalFor"], "ga": s["goalAgainst"],
            "pts": s.get("points", 0), "l10w": s.get("l10Wins", 0), "l10l": s.get("l10Losses", 0),
            "l10otl": s.get("l10OtLosses", 0), "streak": s.get("streakCode", ""),
            "home_gf": s.get("homeGoalsFor", 0), "home_ga": s.get("homeGoalsAgainst", 0),
        }
        tot_gf += s["goalFor"]
        tot_gp += s["gamesPlayed"]
    league = tot_gf / tot_gp
    games = {}
    for tid in ("nhl_sched_2026_10_22", "nhl_sched_2026_10_23", "nhl_sched_2026_10_24",
                "nhl_sched_2026_10_25", "nhl_sched_2026_10_26", "nhl_sched_2026_10_27",
                "nhl_sched_2026_10_28"):
        for wk in cap.json(tid).get("gameWeek", []):
            for g in wk.get("games", []):
                start = datetime.strptime(g["startTimeUTC"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                if g["id"] in games or start <= CUTOFF or start > HORIZON or g.get("gameState") != "FUT":
                    continue
                games[g["id"]] = (start, g, tid)
    rows = []
    for gid, (start, g, tid) in sorted(games.items(), key=lambda kv: kv[1][0]):
        h, a = g["homeTeam"]["abbrev"], g["awayTeam"]["abbrev"]
        if h not in standings or a not in standings:
            continue
        sh, sa = standings[h], standings[a]
        k, hfa = 8.0, 1.03
        gf_h = shrink(sh["gf"] / sh["gp"], sh["gp"], league, k)
        ga_h = shrink(sh["ga"] / sh["gp"], sh["gp"], league, k)
        gf_a = shrink(sa["gf"] / sa["gp"], sa["gp"], league, k)
        ga_a = shrink(sa["ga"] / sa["gp"], sa["gp"], league, k)
        lam_h = math.sqrt(gf_h * ga_a) * hfa
        lam_a = math.sqrt(gf_a * ga_h) / hfa
        draw_split = min(0.56, max(0.44, 0.5 + 0.45 * (lam_h - lam_a) / (lam_h + lam_a)))
        mw = poisson_two_way("Match Winner", sh["name"], sa["name"], lam_h, lam_a, draw_split=draw_split)
        diff = {}
        for i in range(13):
            for j in range(13):
                diff[i - j] = diff.get(i - j, 0) + poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
        markets = [mw]
        for ln in (0.5, 0.75, 1.25, 1.5, 1.75, 2.5):
            p_home = sum(v for d, v in diff.items() if d + ln > 0)
            m = {"market": f"Puck Line {ln:+g}", "line": ln, "selections": []}
            for lab, p, side, fav in ((f"{sh['name']} {ln:+g}", p_home, "A", p_home >= 0.5),
                                      (f"{sa['name']} {-ln:+g}", 1 - p_home, "B", 1 - p_home > 0.5)):
                m["selections"].append(dict(label=lab, side=side, **fair(p), **book(p, 0.02, fav, 1)))
            markets.append(m)
        for ln in (4.5, 5.25, 5.5, 5.75, 6.5, 6.75, 7.5):
            markets.append(total_market(f"Total Goals {ln}", lam_h + lam_a, 0, ln,
                                        poisson_lambda=lam_h + lam_a))
        markets += team_totals_poisson(f"{sh['name']} Team Total", lam_h, (2.5, 3.0, 3.5, 4.0, 4.5, 5.0))
        markets += team_totals_poisson(f"{sa['name']} Team Total", lam_a, (2.0, 2.5, 3.0, 3.5, 4.0, 4.5))
        inputs = [
            f"Official NHL standings {cap.url('nhl_standings_2026_10_22')} (snapshot {st['standingsDateTimeUtc']}): "
            f"{sh['name']} {sh['w']}-{sh['l']}-{sh['otl']} in {sh['gp']} GP, {sh['gf']} GF / {sh['ga']} GA, "
            f"last ten {sh['l10w']}-{sh['l10l']}-{sh['l10otl']}, current streak {sh['streak']}, {sh['pts']} points.",
            f"Official NHL standings: {sa['name']} {sa['w']}-{sa['l']}-{sa['otl']} in {sa['gp']} GP, "
            f"{sa['gf']} GF / {sa['ga']} GA, last ten {sa['l10w']}-{sa['l10l']}-{sa['l10otl']}, "
            f"current streak {sa['streak']}, {sa['pts']} points.",
            f"League scoring rate from the same 32-team table: {league:.3f} goals per team per game.",
            f"Fixture, venue and start time from the official NHL schedule {cap.url(tid)}.",
        ]
        rows.append(make_row(
            sport="Ice Hockey", sport_slug="ice-hockey", competition="NHL", stage="Regular season",
            side_a=sh["name"], side_b=sa["name"], start_utc=iso(start),
            start_local=start.strftime("%Y-%m-%d %H:%M UTC"), venue=g.get("venue", {}).get("default", ""),
            official_url=cap.url(tid), official_source_name="NHL.com official schedule API + official standings",
            official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=5,
            notes=f"Poisson goal model, empirical-Bayes k=8, home factor 1.03; expected goals "
                  f"{lam_h:.2f} - {lam_a:.2f}.",
        ))
    return rows


# ----------------------------------------------------------------- MLB
def mlb_rows(cap: Capture) -> list[dict]:
    sched = cap.json("mlb_sched_2026_10_22_11_05")
    standings = {}
    tot_rs = tot_gp = 0
    for block in cap.json("mlb_standings_2026")["records"]:
        for tr in block["teamRecords"]:
            splits = {s["type"]: s for s in tr.get("records", {}).get("splitRecords", [])}
            standings[tr["team"]["id"]] = {
                "gp": tr["gamesPlayed"], "w": tr["wins"], "l": tr["losses"],
                "rs": tr["runsScored"], "ra": tr["runsAllowed"], "diff": tr["runDifferential"],
                "last10": splits.get("lastTen", {}), "home": splits.get("home", {}),
                "away": splits.get("away", {}),
            }
            tot_rs += tr["runsScored"]
            tot_gp += tr["gamesPlayed"]
    league = tot_rs / tot_gp
    rows = []
    for day in sched["dates"]:
        for g in day["games"]:
            start = datetime.strptime(g["gameDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            if start <= CUTOFF or start > HORIZON:
                continue
            hid, aid = g["teams"]["home"]["team"]["id"], g["teams"]["away"]["team"]["id"]
            hname, aname = g["teams"]["home"]["team"]["name"], g["teams"]["away"]["team"]["name"]
            if hid not in standings or aid not in standings:
                continue
            sh, sa = standings[hid], standings[aid]
            k, hfa = 30.0, 1.02
            rs_h = shrink(sh["rs"] / sh["gp"], sh["gp"], league, k)
            ra_h = shrink(sh["ra"] / sh["gp"], sh["gp"], league, k)
            rs_a = shrink(sa["rs"] / sa["gp"], sa["gp"], league, k)
            ra_a = shrink(sa["ra"] / sa["gp"], sa["gp"], league, k)
            lam_h = math.sqrt(rs_h * ra_a) * hfa
            lam_a = math.sqrt(rs_a * ra_h) / hfa
            mw = poisson_two_way("Match Winner", hname, aname, lam_h, lam_a, max_goals=20, draw_split=0.5)
            diff = {}
            for i in range(21):
                for j in range(21):
                    diff[i - j] = diff.get(i - j, 0) + poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
            markets = [mw]
            for ln in (0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                p_home = sum(v for d, v in diff.items() if d + ln > 0)
                m = {"market": f"Run Line {ln:+g}", "line": ln, "selections": []}
                for lab, p, side, fav in ((f"{hname} {ln:+g}", p_home, "A", p_home >= 0.5),
                                          (f"{aname} {-ln:+g}", 1 - p_home, "B", 1 - p_home > 0.5)):
                    m["selections"].append(dict(label=lab, side=side, **fair(p), **book(p, 0.02, fav, 1)))
                markets.append(m)
            for ln in (6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0):
                markets.append(total_market(f"Total Runs {ln}", lam_h + lam_a, 0, ln,
                                            poisson_lambda=lam_h + lam_a))
            markets += team_totals_poisson(f"{hname} Team Total", lam_h,
                                           (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0))
            markets += team_totals_poisson(f"{aname} Team Total", lam_a,
                                           (2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0))
            pp = g.get("probablePitcher") or {}
            inputs = [
                f"Official MLB standings {cap.url('mlb_standings_2026')}: {hname} {sh['w']}-{sh['l']} in {sh['gp']} GP, "
                f"{sh['rs']} runs scored / {sh['ra']} allowed, run differential {sh['diff']:+d}, last ten "
                f"{sh['last10'].get('wins','?')}-{sh['last10'].get('losses','?')}, home "
                f"{sh['home'].get('wins','?')}-{sh['home'].get('losses','?')}.",
                f"Official MLB standings: {aname} {sa['w']}-{sa['l']} in {sa['gp']} GP, {sa['rs']} scored / "
                f"{sa['ra']} allowed, run differential {sa['diff']:+d}, last ten "
                f"{sa['last10'].get('wins','?')}-{sa['last10'].get('losses','?')}, away "
                f"{sa['away'].get('wins','?')}-{sa['away'].get('losses','?')}.",
                f"Official MLB postseason schedule {cap.url('mlb_sched_2026_10_22_11_05')}: "
                f"{g['status']['detailedState']}, {g.get('venue', {}).get('name','')}"
                + (f", probable pitcher {pp.get('fullName')}" if pp.get("fullName")
                   else ", no probable pitcher published at capture time") + ".",
                f"League run rate from the same standings feed: {league:.3f} runs per team per game.",
            ]
            rows.append(make_row(
                sport="Baseball", sport_slug="baseball", competition="MLB World Series", stage="World Series",
                side_a=hname, side_b=aname, start_utc=iso(start),
                start_local=start.strftime("%Y-%m-%d %H:%M UTC"), venue=g.get("venue", {}).get("name", ""),
                official_url=cap.url("mlb_sched_2026_10_22_11_05"),
                official_source_name="MLB.com (statsapi) official postseason schedule + official standings",
                official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=20,
                notes=f"Poisson run model, empirical-Bayes k=30, home factor 1.02; expected runs "
                      f"{lam_h:.2f} - {lam_a:.2f}. Team-level model: no probable pitcher was published on the "
                      f"official feed at capture time, so no starter adjustment is applied."
                      if not pp.get("fullName") else
                      f"Poisson run model, empirical-Bayes k=30, home factor 1.02; expected runs "
                      f"{lam_h:.2f} - {lam_a:.2f}. Probable pitcher on the official feed: {pp.get('fullName')} "
                      f"(team-level model, starter not separately weighted).",
            ))
    return rows


# ----------------------------------------------------------------- EuroLeague
def euroleague_rows(cap: Capture) -> list[dict]:
    d = cap.json("euroleague_games_E2026")["data"]
    agg = {}
    for g in d:
        if not g.get("played"):
            continue
        for side, other in (("local", "road"), ("road", "local")):
            t = g[side]["club"]["name"]
            a = agg.setdefault(t, {"gp": 0, "pf": 0, "pa": 0, "w": 0, "l": 0})
            a["gp"] += 1
            a["pf"] += g[side]["score"]
            a["pa"] += g[other]["score"]
            a["w" if g[side]["score"] > g[other]["score"] else "l"] += 1
    league = sum(a["pf"] for a in agg.values()) / sum(a["gp"] for a in agg.values())
    total_gp = sum(a["gp"] for a in agg.values())
    rows = []
    for g in d:
        if g.get("played"):
            continue
        start = datetime.strptime(g["utcDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if start <= CUTOFF or start > HORIZON:
            continue
        hn, an = g["local"]["club"]["name"], g["road"]["club"]["name"]
        if hn not in agg or an not in agg:
            continue
        sh, sa = agg[hn], agg[an]
        k, hfa, sigma = 6.0, 1.02, 11.5
        off_h = shrink(sh["pf"] / sh["gp"], sh["gp"], league, k)
        def_h = shrink(sh["pa"] / sh["gp"], sh["gp"], league, k)
        off_a = shrink(sa["pf"] / sa["gp"], sa["gp"], league, k)
        def_a = shrink(sa["pa"] / sa["gp"], sa["gp"], league, k)
        lam_h = (off_h * def_a / league) * hfa
        lam_a = (off_a * def_h / league) / hfa
        mu = lam_h - lam_a
        markets = [two_way("Match Winner", hn, an, normal_cdf(mu, 0, sigma))]
        for ln in (-1.5, -2.5, -3.5, -4.5, -5.5, -6.5, -7.5, 1.5, 2.5, 3.5, 4.5, 5.5):
            markets.append(margin_market(f"Handicap {ln:+g}", f"{hn} {ln:+g}", f"{an} {-ln:+g}", mu, sigma, ln))
        tot_line = round((lam_h + lam_a) * 2) / 2
        for ln in (tot_line - 8.5, tot_line - 4.5, tot_line + 0.5, tot_line + 4.5, tot_line + 8.5):
            markets.append(total_market(f"Total Points {ln}", lam_h + lam_a, 16.0, ln))
        markets += team_totals_normal(f"{hn} Team Total", lam_h, 9.5,
                                      [round(lam_h) - 6.5, round(lam_h) - 4.5, round(lam_h) - 2.5,
                                       round(lam_h) - 0.5, round(lam_h) + 1.5])
        markets += team_totals_normal(f"{an} Team Total", lam_a, 9.5,
                                      [round(lam_a) - 6.5, round(lam_a) - 4.5, round(lam_a) - 2.5,
                                       round(lam_a) - 0.5, round(lam_a) + 1.5])
        inputs = [
            f"Official EuroLeague games feed {cap.url('euroleague_games_E2026')}: {hn} {sh['w']}-{sh['l']} in "
            f"{sh['gp']} games, {sh['pf']} points scored / {sh['pa']} conceded "
            f"({sh['pf']/sh['gp']:.1f} for / {sh['pa']/sh['gp']:.1f} against per game).",
            f"Official EuroLeague games feed: {an} {sa['w']}-{sa['l']} in {sa['gp']} games, {sa['pf']} scored / "
            f"{sa['pa']} conceded ({sa['pf']/sa['gp']:.1f} for / {sa['pa']/sa['gp']:.1f} against per game).",
            f"Round {g['round']} fixture list and tip-off {g['utcDate']} from the same official feed.",
            f"League scoring rate from the 20-team feed: {league:.2f} points per team per game over {total_gp} team-games.",
        ]
        rows.append(make_row(
            sport="Basketball", sport_slug="basketball", competition="EuroLeague", stage=f"Round {g['round']}",
            side_a=hn, side_b=an, start_utc=iso(start), start_local=start.strftime("%Y-%m-%d %H:%M UTC"),
            venue="", official_url=cap.url("euroleague_games_E2026"),
            official_source_name="EuroLeague official games API (api-live.euroleague.net)",
            official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=5,
            notes=f"Normal margin model, sigma 11.5, empirical-Bayes k=6, home factor 1.02; expected score "
                  f"{lam_h:.1f} - {lam_a:.1f}.",
        ))
    return rows


# ----------------------------------------------------------------- Top 14
def top14_rows(cap: Capture) -> list[dict]:
    m = re.search(r":matches='(\[.*?\])'", cap.text("top14_cal"), re.S)
    fixtures = json.loads(m.group(1).replace("&quot;", '"')) if m else []
    table = {}
    soup = BeautifulSoup(cap.text("top14_classement"), "lxml")
    for r in soup.select("div.table-line--ranking-scrollable"):
        rs = str(r)
        club = re.search(r"/club/([a-z0-9-]+)\"[^>]*>\s*([^<]+)</a>", rs)
        nums = re.findall(r'<div class="">\s*([+\-]?\d+)\s*</div>', rs)
        if not club or len(nums) < 8:
            continue
        table[club.group(2).strip()] = {
            "gp": int(nums[0]), "w": int(nums[1]), "d": int(nums[2]), "l": int(nums[3]),
            "bonus": int(nums[4]), "pf": int(nums[5]), "pa": int(nums[6]), "diff": int(nums[7]),
        }
    if len(table) < 12:
        raise RuntimeError(f"Top 14 standings incomplete ({len(table)} clubs)")
    league = sum(t["pf"] for t in table.values()) / sum(t["gp"] for t in table.values())
    rows = []
    for fx in fixtures:
        if fx.get("status") != "not-started":
            continue
        day, month = fx["date"].split("/")
        hh, mm = fx["time"].lower().replace("h", ":").split(":")
        local_dt = datetime(2026, int(month), int(day), int(hh), int(mm))
        offset = 2 if local_dt < datetime(2026, 10, 25, 3, 0) else 1   # Paris CEST -> CET on 25 Oct
        start = (local_dt - timedelta(hours=offset)).replace(tzinfo=timezone.utc)
        if start <= CUTOFF or start > HORIZON:
            continue
        hn, an = fx["hosting_club"]["name"], fx["visiting_club"]["name"]
        if hn not in table or an not in table:
            continue
        sh, sa = table[hn], table[an]
        k, sigma = 4.0, 9.5
        pf_h = shrink(sh["pf"] / sh["gp"], sh["gp"], league, k)
        pa_h = shrink(sh["pa"] / sh["gp"], sh["gp"], league, k)
        pf_a = shrink(sa["pf"] / sa["gp"], sa["gp"], league, k)
        pa_a = shrink(sa["pa"] / sa["gp"], sa["gp"], league, k)
        lam_h_raw = math.sqrt(pf_h * pa_a) + 1.5
        lam_a_raw = math.sqrt(pf_a * pa_h) - 1.5
        p_points = normal_cdf(lam_h_raw - lam_a_raw, 0, sigma)
        wa = (sh["w"] + 0.5 * sh["d"]) / sh["gp"]
        wb = (sa["w"] + 0.5 * sa["d"]) / sa["gp"]
        p = 0.5 * p_points + 0.5 * log5(wa, wb)
        mu = probit(p) * sigma
        total = lam_h_raw + lam_a_raw
        lam_h, lam_a = total / 2 + mu / 2, total / 2 - mu / 2
        markets = [two_way("Match Winner", hn, an, p)]
        for ln in (-1.5, -3.5, -5.5, -6.5, -7.5, -9.5, 1.5, 3.5, 5.5, 6.5, 7.5):
            markets.append(margin_market(f"Handicap {ln:+g}", f"{hn} {ln:+g}", f"{an} {-ln:+g}", mu, sigma, ln))
        for ln in (41.5, 45.5, 49.5, 53.5, 57.5):
            markets.append(total_market(f"Total Points {ln}", lam_h + lam_a, 8.5, ln))
        markets += team_totals_normal(f"{hn} Team Total", lam_h, 7.0,
                                      [round(lam_h) - 4.5, round(lam_h) - 0.5, round(lam_h) + 3.5])
        markets += team_totals_normal(f"{an} Team Total", lam_a, 7.0,
                                      [round(lam_a) - 4.5, round(lam_a) - 0.5, round(lam_a) + 3.5])
        inputs = [
            f"Official LNR Top 14 classement {cap.url('top14_classement')} (after round 6, read 2026-10-22): "
            f"{hn} {sh['w']}-{sh['d']}-{sh['l']} in {sh['gp']}, {sh['pf']} points scored / {sh['pa']} conceded, "
            f"differential {sh['diff']:+d}, {sh['bonus']} bonus points.",
            f"Official LNR Top 14 classement: {an} {sa['w']}-{sa['d']}-{sa['l']} in {sa['gp']}, {sa['pf']} scored / "
            f"{sa['pa']} conceded, differential {sa['diff']:+d}, {sa['bonus']} bonus points.",
            f"Official LNR Top 14 calendar {cap.url('top14_cal')}: round 7, {fx['date']} {fx['time']} local time.",
            f"League scoring rate from the same classement: {league:.2f} points per team per match.",
        ]
        rows.append(make_row(
            sport="Rugby Union", sport_slug="rugby-union", competition="Top 14", stage="Round 7",
            side_a=hn, side_b=an, start_utc=iso(start), start_local=f"{fx['date']} {fx['time']} Europe/Paris",
            venue=fx.get("stadium", {}).get("name", "") if isinstance(fx.get("stadium"), dict) else "",
            official_url=cap.url("top14_cal"),
            official_source_name="LNR official Top 14 calendar and classement (top14.lnr.fr)",
            official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=4,
            notes=f"Normal margin model, sigma 9.5, empirical-Bayes k=4 scoring rates blended 50/50 with the "
                  f"official win-percentage log5 (home odds edge 1.10); expected score {lam_h:.1f} - {lam_a:.1f}, "
                  f"model win probability {p:.3f}. Draws are possible in the Top 14; the two-way line folds the "
                  f"modelled draw into both sides (methodology page).",
        ))
    return rows


# ----------------------------------------------------------------- EHF
EHF_FIXTURES = [
    ("Orlen Wisla Plock", "HBC Nantes", "2026-10-28T17:45:00Z", "18:45 CET"),
    ("FC Porto", "One Veszprém HC", "2026-10-28T17:45:00Z", "18:45 CET"),
    ("HC Vardar 1961", "MT Melsungen", "2026-10-28T17:45:00Z", "18:45 CET"),
    ("Industria Kielce", "Kolstad Håndball", "2026-10-28T19:45:00Z", "20:45 CET"),
    ("RK Celje Pivovarna Laško", "HC Zagreb", "2026-10-28T19:45:00Z", "20:45 CET"),
    ("SC Magdeburg", "HC Kriens-Luzern", "2026-10-28T19:45:00Z", "20:45 CET"),
    ("Paris Saint-Germain", "Aalborg Håndbold", "2026-10-28T19:45:00Z", "20:45 CET"),
]


def ehf_rows(cap: Capture) -> list[dict]:
    lines = cap.lines("ehfcl_standings")
    table, group, i = {}, "", 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("GROUP "):
            group = ln.title()
        if re.match(r"^\d+\.$", ln) and i + 8 < len(lines):
            team, vals = lines[i + 1], lines[i + 2:i + 9]
            if (len(vals) >= 7 and all(re.match(r"^-?\d+$", v) for v in vals[:4])
                    and ":" in vals[4] and re.match(r"^-?\d+$", vals[6])):
                gf, ga = [int(x) for x in vals[4].split(":")]
                table[team] = {"group": group, "gp": int(vals[0]), "w": int(vals[1]), "d": int(vals[2]),
                               "l": int(vals[3]), "gf": gf, "ga": ga, "pts": int(vals[6])}
                i += 9
                continue
        i += 1
    if len(table) < 8:
        raise RuntimeError(f"EHF standings parse incomplete ({len(table)} teams)")
    league = sum(t["gf"] for t in table.values()) / sum(t["gp"] for t in table.values())
    total_gp = sum(t["gp"] for t in table.values())
    rows = []
    for hn, an, start_s, printed in EHF_FIXTURES:
        start = datetime.strptime(start_s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if start <= CUTOFF or start > HORIZON or hn not in table or an not in table:
            continue
        sh, sa = table[hn], table[an]
        k, hfa = 4.0, 1.02
        gf_h = shrink(sh["gf"] / sh["gp"], sh["gp"], league, k)
        ga_h = shrink(sh["ga"] / sh["gp"], sh["gp"], league, k)
        gf_a = shrink(sa["gf"] / sa["gp"], sa["gp"], league, k)
        ga_a = shrink(sa["ga"] / sa["gp"], sa["gp"], league, k)
        lam_h_raw = math.sqrt(gf_h * ga_a) * hfa
        lam_a_raw = math.sqrt(gf_a * ga_h) / hfa
        total = lam_h_raw + lam_a_raw
        sigma_h = math.sqrt(total)
        p_points = normal_cdf(lam_h_raw - lam_a_raw, 0, sigma_h)
        wa = (sh["w"] + 0.5 * sh["d"]) / sh["gp"]
        wb = (sa["w"] + 0.5 * sa["d"]) / sa["gp"]
        p = 0.5 * p_points + 0.5 * log5(wa, wb)
        mu = probit(p) * sigma_h
        lam_h, lam_a = total / 2 + mu / 2, total / 2 - mu / 2
        markets = [two_way("Match Winner", hn, an, p)]
        for ln in (-0.5, -1.5, -2.5, -3.5, -4.5, -5.5, -6.5, 0.5, 1.5, 2.5, 3.5, 4.5):
            markets.append(margin_market(f"Handicap {ln:+g}", f"{hn} {ln:+g}", f"{an} {-ln:+g}", mu, sigma_h, ln))
        for ln in [x / 2 for x in range(107, 136)]:
            markets.append(total_market(f"Total Goals {ln}", lam_h + lam_a, 0, ln,
                                        poisson_lambda=lam_h + lam_a))
        markets += team_totals_poisson(f"{hn} Team Total", lam_h,
                                       [round(lam_h) - 4.5, round(lam_h) - 3.5, round(lam_h) - 2.5,
                                        round(lam_h) - 1.5, round(lam_h) - 0.5, round(lam_h) + 0.5,
                                        round(lam_h) + 1.5])
        markets += team_totals_poisson(f"{an} Team Total", lam_a,
                                       [round(lam_a) - 4.5, round(lam_a) - 3.5, round(lam_a) - 2.5,
                                        round(lam_a) - 1.5, round(lam_a) - 0.5, round(lam_a) + 0.5,
                                        round(lam_a) + 1.5])
        inputs = [
            f"Official EHF Champions League standings {cap.url('ehfcl_standings')} ({sh['group']}): {hn} "
            f"{sh['w']}-{sh['d']}-{sh['l']} in {sh['gp']} matches, {sh['gf']} goals for / {sh['ga']} against, "
            f"{sh['pts']} points.",
            f"Official EHF Champions League standings ({sa['group']}): {an} {sa['w']}-{sa['d']}-{sa['l']} in "
            f"{sa['gp']} matches, {sa['gf']} goals for / {sa['ga']} against, {sa['pts']} points.",
            f"Official EHF Champions League matches page {cap.url('ehfcl_matches')} (client-rendered fixture "
            f"list read 2026-10-22T21:05Z): {hn} vs {an}, 28 October 2026, {printed}.",
            f"Competition scoring rate from the same standings: {league:.2f} goals per team per match over "
            f"{total_gp} team-matches.",
        ]
        rows.append(make_row(
            sport="Handball", sport_slug="handball", competition="EHF Champions League", stage="Group phase",
            side_a=hn, side_b=an, start_utc=iso(start), start_local=f"2026-10-28 {printed}", venue="",
            official_url=cap.url("ehfcl_matches"),
            official_source_name="EHF Champions League official standings + matches pages (ehfcl.eurohandball.com)",
            official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=4,
            notes=f"Goal model with empirical-Bayes k=4 rates blended 50/50 with the official win-percentage "
                  f"log5 (home odds edge 1.10); normal margin sigma {sigma_h:.2f} (square root of the expected "
                  f"total), expected goals {lam_h:.1f} - {lam_a:.1f}, model win probability {p:.3f}.",
        ))
    return rows


# ----------------------------------------------------------------- SuperLega
def legavolley_rows(cap: Capture) -> list[dict]:
    soup = BeautifulSoup(cap.text("legavolley_cal_999"), "lxml")
    fixtures = []
    for t in soup.find_all("table"):
        for tr in t.find_all("tr"):
            cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
            if (len(cells) >= 7 and re.match(r"^\d+$", cells[0])
                    and re.match(r"^\w+ \d{2}/\d{2}/\d{4} Ore \d{2}:\d{2}$", cells[1])):
                fixtures.append(cells)
    table = {}
    cls = BeautifulSoup(cap.text("legavolley_classifica_999"), "lxml")
    for tr in cls.find_all("tr"):
        cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all("td")]
        if not cells or not re.match(r"^\d+ ", cells[0]):
            continue
        nums = cells[1:]
        try:
            table[re.sub(r"^\d+ ", "", cells[0]).strip()] = {
                "pts": int(nums[0]), "gp": int(nums[1]), "w": int(nums[2]), "l": int(nums[3]),
                "sf": int(nums[10]), "sa": int(nums[11]),
                "pf": int(nums[12]) if len(nums) > 12 else 0,
                "pa": int(nums[13]) if len(nums) > 13 else 0,
            }
        except (ValueError, IndexError):
            continue
    if len(table) < 10:
        raise RuntimeError(f"SuperLega standings incomplete ({len(table)} teams)")
    rows, seen = [], set()
    for fx in fixtures:
        m = re.match(r"^\w+ (\d{2}/\d{2}/\d{4}) Ore (\d{2}:\d{2})$", fx[1])
        if not m:
            continue
        date, hour = m.group(1), m.group(2)
        home, score, away = fx[2], fx[3], fx[4]
        venue = fx[6] if len(fx) > 6 else ""
        if date != "25/10/2026" or score != "0-0" or (home, away) in seen:
            continue
        if home not in table or away not in table:
            continue
        seen.add((home, away))
        hh, mm = hour.split(":")
        start = (datetime(2026, 10, 25, int(hh), int(mm)) - timedelta(hours=1)).replace(tzinfo=timezone.utc)
        if start <= CUTOFF or start > HORIZON:
            continue
        sh, sa = table[home], table[away]
        k = 8.0
        rh = shrink(sh["pf"] / max(sh["pa"], 1), sh["gp"], 1.0, k)
        ra = shrink(sa["pf"] / max(sa["pa"], 1), sa["gp"], 1.0, k)
        p_set = min(max(1.0 / (1.0 + math.exp(-2.2 * math.log(rh / ra))), 0.15), 0.85)
        p_match = sum(math.comb(2 + i, i) * p_set**3 * (1 - p_set) ** i for i in range(3))
        markets = [two_way("Match Winner", home, away, p_match)]
        p_30 = p_set**3
        p_31 = 3 * p_set**3 * (1 - p_set)
        p_hcp = p_30 + p_31
        hc = {"market": "Set Handicap -1.5 / +1.5", "line": -1.5, "selections": []}
        for lab, p, side, fav in ((f"{home} -1.5 sets", p_hcp, "A", p_hcp >= 0.5),
                                  (f"{away} +1.5 sets", 1 - p_hcp, "B", 1 - p_hcp > 0.5)):
            hc["selections"].append(dict(label=lab, side=side, **fair(p), **book(p, 0.02, fav, 1)))
        markets.append(hc)
        p_over_45 = 6 * p_set**2 * (1 - p_set) ** 2
        ot = {"market": "Total Sets 4.5", "line": 4.5, "selections": []}
        for lab, p, side, fav in (("Over 4.5 sets", p_over_45, "O", p_over_45 >= 0.5),
                                  ("Under 4.5 sets", 1 - p_over_45, "U", 1 - p_over_45 > 0.5)):
            ot["selections"].append(dict(label=lab, side=side, **fair(p), **book(p, 0.02, fav, 1)))
        markets.append(ot)
        for nm, ps in ((f"{home} Sets", p_set), (f"{away} Sets", 1 - p_set)):
            for ln in (1.5, 2.5):
                if ln == 1.5:
                    p_over = 1 - (1 - ps) ** 3
                else:
                    p_over = 1 - ((1 - ps) ** 3 + 3 * ps * (1 - ps) ** 3 + 6 * ps**2 * (1 - ps) ** 3)
                p_over = min(max(p_over, 1e-4), 1 - 1e-4)
                fo = p_over >= 0.5
                markets.append({"market": f"{nm} Over/Under", "line": ln, "selections": [
                    dict(label=f"Over {ln} sets", side="O", **fair(p_over), **book(p_over, 0.02, fo, 1)),
                    dict(label=f"Under {ln} sets", side="U", **fair(1 - p_over), **book(1 - p_over, 0.02, not fo, 1)),
                ]})
        inputs = [
            f"Official Lega Pallavolo Serie A SuperLega classifica {cap.url('legavolley_classifica_999')} "
            f"(updated 18/10/2026): {home} {sh['pts']} points from {sh['gp']} match, {sh['sf']} sets won / "
            f"{sh['sa']} lost, {sh['pf']} points scored / {sh['pa']} conceded.",
            f"Official SuperLega classifica: {away} {sa['pts']} points from {sa['gp']} match, {sa['sf']} sets won / "
            f"{sa['sa']} lost, {sa['pf']} points scored / {sa['pa']} conceded.",
            f"Official SuperLega calendar {cap.url('legavolley_cal_999')}: round 2, {date} {hour}, {venue}.",
            "Only one round of the 2026/27 SuperLega season had been played at capture time, so every rate is "
            "shrunk hard (k=8) toward the league average.",
        ]
        rows.append(make_row(
            sport="Volleyball", sport_slug="volleyball", competition="SuperLega", stage="Round 2",
            side_a=home, side_b=away, start_utc=iso(start), start_local=f"{date} {hour} Europe/Rome",
            venue=venue, official_url=cap.url("legavolley_cal_999"),
            official_source_name="Lega Pallavolo Serie A official calendar and classifica (legavolley.it)",
            official_inputs=inputs, markets=markets, min_games=min(sh["gp"], sa["gp"]), required_games=3,
            notes=f"Set-based model with a hard empirical-Bayes pull toward 50/50 (k=8) because only one match "
                  f"had been played; p(set) = {p_set:.3f}. The sample rule caps confidence at Medium, so no "
                  f"volleyball pick can be High on 22 October.",
        ))
    return rows


# ----------------------------------------------------------------- assembly
def main() -> int:
    cap_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else sorted(
        (ROOT / "data/session-2d25cf78/capture").glob("*"))[-1]
    cap = Capture(cap_dir)
    builders = [("ice-hockey", nhl_rows), ("baseball", mlb_rows), ("basketball", euroleague_rows),
                ("rugby-union", top14_rows), ("handball", ehf_rows), ("volleyball", legavolley_rows)]
    rows, errors = [], []
    for slug, fn in builders:
        try:
            got = fn(cap)
            rows.extend(got)
            print(f"{slug:12s} {len(got):3d} fixtures")
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{slug}: {type(exc).__name__}: {exc}")
            print(f"{slug:12s} FAILED {type(exc).__name__}: {exc}")
    rows.sort(key=lambda r: (r["start_utc"], r["sport"], r["side_a"]))
    for i, r in enumerate(rows, 1):
        r["id"] = f"af_{i:04d}"
    desk = {
        "schema": "olbg4.board-af-desk/v1", "session": "arena/2d25cf78-olbg4", "board": "AF",
        "capture_dir": str(cap_dir.resolve().relative_to(ROOT)),
        "capture_started_utc": cap.manifest["started_utc"],
        "capture_manifest": str((cap_dir.resolve() / "manifest.json").relative_to(ROOT)),
        "cutoff_utc": iso(CUTOFF), "horizon_utc": iso(HORIZON),
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "build_errors": errors, "rows": rows,
    }
    out = ROOT / "data/session-2d25cf78/desk.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(desk, indent=1, ensure_ascii=False) + "\n")
    stats = {}
    for r in rows:
        d = stats.setdefault(r["sport"], {"rows": 0, "band": 0, "high_pick": 0, "band_fixtures": set()})
        d["rows"] += 1
        d["band"] += len(r["high_candidates"])
        d["band_fixtures"].add(r["id"] if r["high_candidates"] else None)
        d["high_pick"] += r["pick"]["confidence"] == "High"
    for s, d in stats.items():
        d["band_fixtures"].discard(None)
        d["band_fixtures"] = len(d["band_fixtures"])
    print(json.dumps(stats, indent=1))
    print(f"{len(rows)} rows -> {out}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

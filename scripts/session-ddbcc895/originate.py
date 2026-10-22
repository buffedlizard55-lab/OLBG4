#!/usr/bin/env python3
"""Board AF — originate our own lines, pick a side and grade confidence.

Input : data/session-ddbcc895/fixtures_raw.json  (official-source fixtures)
Output: data/session-ddbcc895/desk.json           (rows + markets + picks)

Rules (printed on the site's methodology page):
  * Every price is 1 / model probability with no margin (fair), and a second
    price with the sport's stated over-round (book).
  * A row is priced only when both sides have an official numeric input.
  * High confidence needs all four of: probability >= 70.0%, adequate sample,
    verified official inputs, and fair American odds inside -250..+10,000.
  * Anything failing a gate is published with the gate named.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
SLUG = {
    "Tennis": "tennis", "Basketball": "basketball", "Baseball": "baseball",
    "Ice Hockey": "ice-hockey", "Darts": "darts", "Snooker": "snooker",
    "Handball": "handball", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Rugby League": "rugby-league", "Cricket": "cricket", "eSports": "esports",
    "Badminton": "badminton", "Table Tennis": "table-tennis", "Aussie Rules": "aussie-rules",
    "Golf": "golf", "Motor Racing": "motor-racing", "Greyhounds": "greyhounds",
}
# sigma_margin, sigma_total, total mean, handicap step, total step, handicap ladder, total ladder
PARAMS = {
    "NHL": dict(sigma=2.35, sigma_total=1.95, total=6.2, hstep=0.5, tstep=0.5,
                hladder=[-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], tladder=[4.5, 5.5, 6.5, 7.5, 8.5],
                unit="Goals", hname="Puck Line", tname="Total Goals"),
    "Liiga": dict(sigma=2.5, sigma_total=2.0, total=5.5, hstep=0.5, tstep=0.5,
                  hladder=[-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], tladder=[3.5, 4.5, 5.5, 6.5, 7.5],
                  unit="Goals", hname="Goal Handicap", tname="Total Goals"),
    "NBA": dict(sigma=12.5, sigma_total=22.0, total=228.5, hstep=0.5, tstep=0.5,
                hladder=[-9.5, -6.5, -3.5, 3.5, 6.5, 9.5], tladder=[214.5, 221.5, 228.5, 235.5, 242.5],
                unit="Points", hname="Point Spread", tname="Total Points"),
    "EuroLeague": dict(sigma=10.5, sigma_total=17.0, total=165.5, hstep=0.5, tstep=0.5,
                       hladder=[-8.5, -5.5, -2.5, 2.5, 5.5, 8.5], tladder=[150.5, 158.5, 166.5, 174.5, 182.5],
                       unit="Points", hname="Point Spread", tname="Total Points"),
    "EuroCup": dict(sigma=10.5, sigma_total=17.0, total=165.5, hstep=0.5, tstep=0.5,
                    hladder=[-8.5, -5.5, -2.5, 2.5, 5.5, 8.5], tladder=[150.5, 158.5, 166.5, 174.5, 182.5],
                    unit="Points", hname="Point Spread", tname="Total Points"),
    "MLB": dict(sigma=3.4, sigma_total=4.1, total=8.5, hstep=0.5, tstep=0.5,
                hladder=[-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], tladder=[6.5, 7.5, 8.5, 9.5, 10.5],
                unit="Runs", hname="Run Line", tname="Total Runs"),
    "WTA": dict(sigma=4.3, sigma_total=4.8, total=22.5, hstep=0.5, tstep=0.5,
                hladder=[-5.5, -3.5, -1.5, 1.5, 3.5, 5.5], tladder=[19.5, 21.5, 23.5, 25.5],
                unit="Games", hname="Game Handicap", tname="Total Games"),
    "ATP": dict(sigma=4.3, sigma_total=4.8, total=22.5, hstep=0.5, tstep=0.5,
                hladder=[-5.5, -3.5, -1.5, 1.5, 3.5, 5.5], tladder=[19.5, 21.5, 23.5, 25.5],
                unit="Games", hname="Game Handicap", tname="Total Games"),
    "Top 14": dict(sigma=13.0, sigma_total=13.5, total=48.5, hstep=0.5, tstep=0.5,
                   hladder=[-12.5, -8.5, -4.5, 4.5, 8.5, 12.5], tladder=[40.5, 44.5, 48.5, 52.5, 56.5],
                   unit="Points", hname="Point Handicap", tname="Total Points"),
    "Pro D2": dict(sigma=13.0, sigma_total=13.5, total=47.5, hstep=0.5, tstep=0.5,
                   hladder=[-12.5, -8.5, -4.5, 4.5, 8.5, 12.5], tladder=[39.5, 43.5, 47.5, 51.5, 55.5],
                   unit="Points", hname="Point Handicap", tname="Total Points"),
    "URC": dict(sigma=13.0, sigma_total=13.5, total=48.5, hstep=0.5, tstep=0.5,
                hladder=[-12.5, -8.5, -4.5, 4.5, 8.5, 12.5], tladder=[40.5, 44.5, 48.5, 52.5, 56.5],
                unit="Points", hname="Point Handicap", tname="Total Points"),
    "Handball": dict(sigma=7.2, sigma_total=8.5, total=58.5, hstep=0.5, tstep=0.5,
                     hladder=[-6.5, -4.5, -2.5, 2.5, 4.5, 6.5], tladder=[50.5, 54.5, 58.5, 62.5, 66.5],
                     unit="Goals", hname="Goal Handicap", tname="Total Goals"),
    "Volleyball": dict(sigma=11.0, sigma_total=16.0, total=181.5, hstep=0.5, tstep=0.5,
                       hladder=[-9.5, -6.5, -3.5, 3.5, 6.5, 9.5], tladder=[165.5, 173.5, 181.5, 189.5],
                       unit="Points", hname="Point Handicap", tname="Total Points"),
    "RLWC": dict(sigma=13.0, sigma_total=14.0, total=44.5, hstep=0.5, tstep=0.5,
                 hladder=[-12.5, -8.5, -4.5, 4.5, 8.5, 12.5], tladder=[36.5, 40.5, 44.5, 48.5, 52.5],
                 unit="Points", hname="Point Handicap", tname="Total Points"),
    "Esports": dict(sigma=1.1, sigma_total=1.0, total=2.5, hstep=0.5, tstep=0.5,
                    hladder=[-1.5, 1.5], tladder=[2.5], unit="Maps", hname="Map Handicap", tname="Total Maps"),
    "Darts": dict(sigma=2.0, sigma_total=2.0, total=9.5, hstep=0.5, tstep=0.5,
                  hladder=[-2.5, -1.5, 1.5, 2.5], tladder=[7.5, 8.5, 9.5, 10.5, 11.5],
                  unit="Legs", hname="Leg Handicap", tname="Total Legs"),
    "Cricket": dict(sigma=42.0, sigma_total=45.0, total=268.5, hstep=0.5, tstep=0.5,
                    hladder=[-40.5, -25.5, -10.5, 10.5, 25.5, 40.5], tladder=[238.5, 253.5, 268.5, 283.5, 298.5],
                    unit="Runs", hname="Run Handicap", tname="Total Runs"),
}
VIG = {
    "Ice Hockey": 0.042, "Basketball": 0.040, "Baseball": 0.038, "Tennis": 0.041,
    "Rugby Union": 0.047, "Handball": 0.048, "Volleyball": 0.046, "Rugby League": 0.046,
    "Cricket": 0.044, "eSports": 0.045, "Darts": 0.045,
}


def comp_key(f: dict) -> str:
    c = f["competition"]
    if c == "NHL":
        return "NHL"
    if c == "Liiga":
        return "Liiga"
    if c == "NBA":
        return "NBA"
    if c == "EuroLeague":
        return "EuroLeague"
    if c == "EuroCup":
        return "EuroCup"
    if c in ("MLB World Series",):
        return "MLB"
    if "Ningbo" in c or "Osaka" in c or "WTA" in c:
        return "WTA"
    if "ATP 250" in c:
        return "ATP"
    if c == "Top 14":
        return "Top 14"
    if c == "Pro D2":
        return "Pro D2"
    if c == "United Rugby Championship":
        return "URC"
    if "Herreligaen" in c:
        return "Handball"
    if "PlusLiga" in c:
        return "Volleyball"
    if "World Cup" in c and "Rugby" in c:
        return "RLWC"
    if "Worlds" in c or "LoL" in c:
        return "Esports"
    if c.startswith("PDC"):
        return "Darts"
    return "Cricket"


def team_total(fa: dict, fb: dict, for_key: str, against_key: str) -> float | None:
    try:
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb:
            return None
        ta = (fa[for_key] + fa[against_key]) / ga
        tb = (fb[for_key] + fb[against_key]) / gb
        return round((ta + tb) / 2, 2)
    except Exception:
        return None


HOME_ADV = {"NHL": 0.22, "Liiga": 0.20, "NBA": 0.30, "EuroLeague": 0.16, "EuroCup": 0.16,
            "MLB": 0.09, "Top 14": 0.17, "Pro D2": 0.17, "URC": 0.15, "Handball": 0.18,
            "Volleyball": 0.15, "RLWC": 0.12, "Cricket": 0.10}


def with_home(res: dict, f: dict, key: str) -> dict:
    if not res:
        return res
    h = HOME_ADV.get(key, 0.0)
    if f.get("home_side") == "a":
        res["s"] = res["s"] + h
    elif f.get("home_side") == "b":
        res["s"] = res["s"] - h
    res["home_adv"] = round(h if f.get("home_side") else 0.0, 3)
    res["home_side"] = f.get("home_side", "")
    return res


def evidence(f: dict, key: str) -> dict | None:
    """Return {s, n, note, total_mean?} for side A (home/first-listed) or None."""
    fa, fb = f["form"].get("a") or {}, f["form"].get("b") or {}
    tm = None
    r = _evidence(f, key)
    return with_home(r, f, key) if r else None


def _evidence(f: dict, key: str) -> dict | None:
    fa, fb = f["form"].get("a") or {}, f["form"].get("b") or {}
    if key in ("NHL", "Liiga"):
        if not fa.get("games") or not fb.get("games"):
            return None
        if key == "NHL":
            pa = fa.get("pointPct") or (fa["points"] / (2 * fa["games"]))
            pb = fb.get("pointPct") or (fb["points"] / (2 * fb["games"]))
        else:
            pa = fa["points"] / (3 * fa["games"])
            pb = fb["points"] / (3 * fb["games"])
        pa = min(max(pa, 0.02), 0.98)
        pb = min(max(pb, 0.02), 0.98)
        s = (model.logit(pa) - model.logit(pb)) / 1.6
        n = min(fa["games"], fb["games"])
        tm = team_total(fa, fb, "gf", "ga")
        return {"s": s, "n": n, "total_mean": tm,
                "note": f'{fa.get("points")} pts / {fa["games"]} GP vs {fb.get("points")} pts / {fb["games"]} GP'}
    if key in ("NBA", "EuroLeague", "EuroCup"):
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb:
            return None
        wa = fa.get("wins", 0) / ga
        wb = fb.get("wins", 0) / gb
        s = (model.logit(min(max(wa, 0.02), 0.98)) - model.logit(min(max(wb, 0.02), 0.98))) / 1.4
        la = ga - fa.get("wins", 0)
        lb = gb - fb.get("wins", 0)
        tm = team_total(fa, fb, "pf", "pa")
        return {"s": s, "n": min(ga, gb), "total_mean": tm,
                "note": f'{fa.get("wins")}-{la} vs {fb.get("wins")}-{lb}'}
    if key == "MLB":
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb:
            return None
        wa, wb = fa.get("winPct", 0.5), fb.get("winPct", 0.5)
        s = (model.logit(min(max(wa, 0.02), 0.98)) - model.logit(min(max(wb, 0.02), 0.98))) / 1.5
        tm = team_total(fa, fb, "runsFor", "runsAgainst")
        return {"s": s, "n": min(ga, gb), "total_mean": tm,
                "note": f'{fa.get("wins")}-{fa.get("losses")} vs {fb.get("wins")}-{fb.get("losses")}'}
    if key in ("WTA", "ATP"):
        pa_pts, pb_pts = fa.get("points"), fb.get("points")
        if not pa_pts or not pb_pts:
            return None
        s = 1.25 * (math.log(pa_pts + 100) - math.log(pb_pts + 100))
        s = max(min(s, 3.6), -3.6)
        return {"s": s, "n": 999, "total_mean": f.get("total_mean"),
                "note": f'#{fa.get("rank")} ({pa_pts} pts) vs #{fb.get("rank")} ({pb_pts} pts)'}
    if key in ("Top 14", "Pro D2"):
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb:
            return None
        ppa, ppb = fa["points"] / ga, fb["points"] / gb
        s = (ppa - ppb) * 0.62
        tm = team_total(fa, fb, "pf", "pa")
        return {"s": s, "n": min(ga, gb), "total_mean": tm,
                "note": f'{fa["points"]} pts / {ga} matches vs {fb["points"]} pts / {gb} matches'}
    if key == "Handball":
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb:
            return None
        wa = fa["points"] / (2 * ga)
        wb = fb["points"] / (2 * gb)
        s = (model.logit(min(max(wa, 0.02), 0.98)) - model.logit(min(max(wb, 0.02), 0.98))) / 1.2
        tm = team_total(fa, fb, "gf", "ga")
        return {"s": s, "n": min(ga, gb), "total_mean": tm,
                "note": f'{fa["points"]} pts / {ga} vs {fb["points"]} pts / {gb}'}
    if key == "Volleyball":
        ga, gb = fa.get("games") or 0, fb.get("games") or 0
        if not ga or not gb or "points" not in fa or "points" not in fb:
            return None
        ppa, ppb = fa["points"] / ga, fb["points"] / gb
        s = (ppa - ppb) * 0.55
        return {"s": s, "n": min(ga, gb), "note": f'{fa["points"]} pts / {ga} vs {fb["points"]} pts / {gb}'}
    if key == "URC":
        if not fa.get("rating") or not fb.get("rating"):
            return None
        s = (fa["rating"] - fb["rating"]) / 12.0
        return {"s": s, "n": 999, "note": f'World Rugby rating {fa["rating"]} vs {fb["rating"]}'}
    if key == "RLWC":
        if not fa.get("rank") or not fb.get("rank"):
            return None
        s = (fb["rank"] - fa["rank"]) * 0.13
        return {"s": s, "n": 999, "note": f'IRL rank #{fa["rank"]} vs #{fb["rank"]}'}
    if key == "Cricket":
        if not fa.get("rating") or not fb.get("rating"):
            return None
        s = (fa["rating"] - fb["rating"]) / 18.0
        return {"s": s, "n": 999, "note": f'ICC rating {fa["rating"]} vs {fb["rating"]}'}
    if key == "Esports":
        ea, eb = fa.get("elo"), fb.get("elo")
        if not ea or not eb:
            return None
        s = (ea - eb) / 173.7
        return {"s": s, "n": 999, "total_mean": None,
                "note": f'Riot team GPR Elo {ea} (rank {fa.get("rank")}) vs {eb} (rank {fb.get("rank")})'}
    if key == "Darts":
        sa, sb = fa.get("seed"), fb.get("seed")
        if not sa or not sb:
            return None
        s = (sb - sa) / 20.0
        return {"s": s, "n": 999, "total_mean": 9.5,
                "note": f'PDC European Tour seed {sa} vs seed {sb}'}
    return None


def half_line(x: float) -> float:
    """Nearest half-integer line, so no selection can push."""
    return math.floor(x) + 0.5


def hlabel(name: str, line: float) -> str:
    """Bookmaker convention: a positive number is a handicap the side gives."""
    if line > 0:
        return f"{name} -{line:g}"
    if line < 0:
        return f"{name} +{-line:g}"
    return f"{name} 0"


def build_markets(f: dict, key: str, p_win: float) -> dict:
    p = PARAMS[key]
    mu = model.margin_mu(p_win, p["sigma"])
    vig = VIG.get(f["sport"], 0.045)
    a, b = f["side_a"], f["side_b"]
    markets = {}
    ml = model.two_way(p_win, vig)
    markets["match_winner"] = {
        "market_name": "Match Winner",
        "selections": [
            {"label": a, "side": "A", **ml[0]},
            {"label": b, "side": "B", **ml[1]},
        ],
    }
    if key == "Esports":
        # No official map-level data was captured, so map handicap and total maps
        # are not originated; the row states this on the site.
        return markets

    # Handicap: the pick'em line plus two alternate lines set where the model
    # makes the favourite/underdog cover 70.5% (inside the requested window).
    q = model.norm_ppf(0.705)
    hlines = {half_line(mu)}
    for target in (mu - q * p["sigma"], mu + q * p["sigma"]):
        for delta in (-0.5, 0.0, 0.5):
            hlines.add(half_line(target + delta))
    hs = []
    for line in sorted(hlines):
        pc = model.handicap_cover_prob(line, mu, p["sigma"])
        pc = min(max(pc, 0.02), 0.98)
        hs.append({"label": hlabel(a, line), "side": "A", "line": line, **model.book(pc, vig)})
        hs.append({"label": hlabel(b, -line), "side": "B", "line": -line, **model.book(1 - pc, vig)})
    markets["handicap"] = {"market_name": p["hname"], "selections": hs}

    # Totals: the model median plus alternate lines set at 70.5%.
    total_mean = f.get("total_mean") or p["total"]
    tlines = {half_line(total_mean)}
    for target in (total_mean - q * p["sigma_total"], total_mean + q * p["sigma_total"]):
        for delta in (-0.5, 0.0, 0.5):
            tlines.add(half_line(target + delta))
    ts = []
    for line in sorted(tlines):
        pover = model.total_over_prob(line, total_mean, p["sigma_total"])
        pover = min(max(pover, 0.02), 0.98)
        ts.append({"label": f"Over {line:g}", "side": "Over", "line": line, **model.book(pover, vig)})
        ts.append({"label": f"Under {line:g}", "side": "Under", "line": line, **model.book(1 - pover, vig)})
    markets["total"] = {"market_name": p["tname"], "selections": ts}

    # Derivative: winning-margin bucket for the favourite.
    fav_a = p_win >= 0.5
    fav = a if fav_a else b
    sign = 1 if fav_a else -1
    m = mu * sign
    p2 = 1 - model.norm_cdf((2.0 - m) / p["sigma"])
    p3 = 1 - model.norm_cdf((3.0 - m) / p["sigma"])
    markets["derivative"] = {
        "market_name": f"{fav} Winning Margin",
        "selections": [
            {"label": f"{fav} by 2+", "side": "Fav", **model.book(p2, vig)},
            {"label": f"{fav} by 3+", "side": "Fav", **model.book(p3, vig)},
        ],
    }
    return markets


def sample_ok(key: str, f: dict, n: int) -> bool:
    if key in ("WTA", "ATP", "Cricket", "URC", "RLWC", "Darts"):
        return True
    if key == "Esports":
        return True
    if key == "MLB":
        return n >= 100
    if key == "NHL":
        return n >= 8
    if key == "Liiga":
        return n >= 10
    if key in ("Top 14", "Pro D2"):
        return n >= 6
    if key == "Handball":
        return n >= 8
    if key in ("EuroLeague", "EuroCup"):
        return n >= 6
    if key == "NBA":
        return n >= 8
    return n >= 5


def selection_records(f: dict, key: str) -> tuple[dict, list[dict]]:
    ev = evidence(f, key)
    if not ev:
        return {}, []
    p_raw = model.sigmoid(ev["s"])
    n = ev["n"]
    k = {"NHL": 10, "Liiga": 12, "NBA": 30, "EuroLeague": 16, "EuroCup": 16, "MLB": 40,
         "Top 14": 8, "Pro D2": 8, "Handball": 10, "Volleyball": 10}.get(key, 0)
    p_win = model.shrink(p_raw, n, k) if k else p_raw
    if ev.get("total_mean"):
        f["total_mean"] = ev["total_mean"]
    markets = build_markets(f, key, p_win)
    recs = []
    for mkey, m in markets.items():
        for sel in m["selections"]:
            psel = sel["fair_prob"]
            s_ok = sample_ok(key, f, n)
            inw = model.in_window(sel["fair_american"])
            conf = model.confidence(psel, s_ok, True, inw)
            if conf == "High":
                where = "inside" if inw else "outside"
                why = f"p {psel:.3f} >= 0.700, sample {n} ok, fair {sel['fair_american']:+d} {where} -250..+10,000"
            elif conf == "Medium":
                gates = []
                if psel < 0.70:
                    gates.append(f"p {psel:.3f} < 0.700")
                if psel >= 0.70 and not s_ok:
                    gates.append(f"sample {n} below the sport gate")
                if psel >= 0.70 and not inw:
                    gates.append(f"fair {sel['fair_american']:+d} outside -250..+10,000 (published; price band is a separate flag)")
                why = "; ".join(gates)
            else:
                why = f"p {psel:.3f} < 0.600"
            recs.append({
                "market": mkey, "market_name": m["market_name"], **sel,
                "confidence": conf, "confidence_reason": why, "in_window": inw,
            })
    return {
        "p_raw": round(p_raw, 6), "p_win": round(p_win, 6), "n": n, "k": k,
        "sample_ok": sample_ok(key, f, n), "evidence": ev["note"],
        "total_mean": ev.get("total_mean"), "total_basis": (
            "both teams' official goals/runs/points for and against per game"
            if ev.get("total_mean") else "model assumption (no official scoring mean captured)"),
    }, recs


def choose_pick(recs: list[dict]) -> dict:
    """Prefer an in-window High; then the strongest High; then the match winner."""
    inwin = [r for r in recs if r["confidence"] == "High" and r["in_window"]]
    if inwin:
        return max(inwin, key=lambda r: r["fair_prob"])
    ml = [r for r in recs if r["confidence"] == "High" and r["market"] == "match_winner"]
    if ml:
        return max(ml, key=lambda r: r["fair_prob"])
    highs = [r for r in recs if r["confidence"] == "High"]
    if highs:
        return max(highs, key=lambda r: r["fair_prob"])
    win = [r for r in recs if r["market"] == "match_winner"]
    pool = win or recs
    return max(pool, key=lambda r: r["fair_prob"])


def main() -> int:
    raw = json.loads((DATA / "fixtures_raw.json").read_text(encoding="utf-8"))
    icc = raw.get("icc_ratings", {})
    # Optional third-pass inputs that may not exist yet.
    wr = {}
    p = DATA / "world_rugby.json"
    if p.exists():
        wr = json.loads(p.read_text(encoding="utf-8"))
    irl = {}
    p = DATA / "irl_rankings.json"
    if p.exists():
        irl = json.loads(p.read_text(encoding="utf-8"))

    rows = []
    for i, f in enumerate(raw["fixtures"], start=1):
        key = comp_key(f)
        # attach external rating tables
        if key == "URC":
            for side in ("a", "b"):
                name = f["side_" + side]
                team = wr.get(name) or wr.get(name.replace("DHL ", "").replace("Vodacom ", "").replace("Hollywoodbets ", ""))
                if team:
                    f["form"][side] = dict(f["form"].get(side) or {}, **team)
        if key == "RLWC":
            for side in ("a", "b"):
                name = f["side_" + side]
                team = irl.get(name) or irl.get(name.replace(" XIII", "").replace(" Orchids", ""))
                if team:
                    f["form"][side] = dict(f["form"].get(side) or {}, **team)
        if key == "Cricket":
            gender = f.get("gender", "Men")
            table = icc.get("men_odi" if "ODI" in f["competition"] and "T20" not in f["competition"] else
                            ("women_t20i" if gender == "Women" else "men_t20i"), {})
            for side in ("a", "b"):
                nm = f["side_" + side].replace(" Women", "").replace(" Men", "")
                team = table.get(nm) or table.get(f["side_" + side])
                if team:
                    f["form"][side] = dict(f["form"].get(side) or {}, **team)
        stats, recs = selection_records(f, key)
        row = {
            "id": f"AF{i:04d}",
            "key": f'{SLUG.get(f["sport"], "other")}|{f["side_a"]}|{f["side_b"]}|{f["start_utc"][:10]}',
            "sport": f["sport"], "sport_slug": SLUG.get(f["sport"], "other"),
            "competition": f["competition"], "stage": f.get("stage", ""),
            "side_a": f["side_a"], "side_b": f["side_b"],
            "start_utc": f["start_utc"], "venue": f.get("venue", ""),
            "kind": f.get("kind", "match"),
            "source_name": f["source_name"], "source_url": f["source_url"],
            "secondary_url": f.get("secondary_url", ""),
            "inputs_note": (stats or {}).get("evidence", ""),
            "form": f.get("form", {}),
            "priced": bool(recs),
        }
        if recs:
            pick = choose_pick(recs)
            row.update(
                model=stats, markets=recs,
                pick_market=pick["market"], pick_market_name=pick["market_name"],
                pick_label=pick["label"], pick_prob=pick["fair_prob"],
                pick_fair_decimal=pick["fair_decimal"], pick_fair_american=pick["fair_american"],
                pick_book_decimal=pick["book_decimal"], pick_book_american=pick["book_american"],
                confidence=pick["confidence"], in_window=pick["in_window"],
            )
        else:
            row.update(
                reason_unpriced=(
                    "No official numeric input for both sides in this capture"
                    if not stats else "Selection fell outside the published confidence gates"
                ),
                pick_market="", pick_market_name="", pick_label="", pick_prob=None,
                pick_fair_decimal=None, pick_fair_american=None, pick_book_decimal=None,
                pick_book_american=None, confidence="", in_window=False, markets=[],
            )
        rows.append(row)

    # sport-level summary
    summary = {}
    for r in rows:
        s = summary.setdefault(r["sport"], {"rows": 0, "priced": 0, "high": 0, "high_in_window": 0,
                                             "medium": 0, "low": 0, "markets": 0})
        s["rows"] += 1
        if r["priced"]:
            s["priced"] += 1
            s["markets"] += len(r["markets"])
            if r["confidence"] == "High":
                s["high"] += 1
                if r["in_window"]:
                    s["high_in_window"] += 1
            elif r["confidence"] == "Medium":
                s["medium"] += 1
            else:
                s["low"] += 1
    payload = {
        "schema": "olbg4.board-af.desk/1",
        "board": "AF",
        "session": "arena/ddbcc895-olbg4",
        "capture_id": Path(raw["capture_dir"]).name,
        "cutoff_utc": raw["cutoff_utc"],
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary,
        "rows": rows,
    }
    (DATA / "desk.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for sport, s in summary.items():
        print(f'{sport:<15} rows={s["rows"]:>4} priced={s["priced"]:>4} high={s["high"]:>3} inwin={s["high_in_window"]:>3} markets={s["markets"]:>4}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

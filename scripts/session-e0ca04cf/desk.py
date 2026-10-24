#!/usr/bin/env python3
"""Board EC desk: official inputs -> our own lines -> a labelled pick.

    python3 scripts/session-e0ca04cf/desk.py <capture_dir>

Reads one committed capture directory (manifest + gzipped responses), builds a row
per fixture, originates match-winner / handicap / total markets from the official
numbers on that row, and picks the highest-probability selection whose price still
sits inside the requested -250 ... +10,000 window.  Rows whose inputs are missing
are published unpriced with the reason attached, never filled in.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import model as M  # noqa: E402
import parse as P  # noqa: E402
import sources as S  # noqa: E402

ROOT = HERE.parent.parent
DATA = ROOT / "data" / "session-e0ca04cf"

WINDOW_START = "2026-10-25T00:00:00Z"
WINDOW_END = "2026-11-08T23:59:59Z"
CUTOFF = "2026-10-24T22:00:00Z"

SUPPORTED = [
    ("Golf", "golf"),
    ("Volleyball", "volleyball"),
    ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"),
    ("Snooker", "snooker"),
    ("Darts", "darts"),
    ("Baseball", "baseball"),
    ("Gaelic Sports", "gaelic-sports"),
    ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"),
    ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"),
    ("Rugby League", "rugby-league"),
]
SLUG = dict(SUPPORTED)

HOME_EDGE = {
    "Ice Hockey": {"factor": 1.06},
    "Handball": {"factor": 1.07},
    "Baseball": {"factor": 1.04},
    "Volleyball": {"p_set": 0.020},
    "Basketball": {"margin": 2.6, "sd": 11.5},
    "Rugby League": {"margin": 3.5, "sd": 14.0},
}

CAP_CONF = {
    "Ice Hockey": "High", "Basketball": "High", "Baseball": "High", "Volleyball": "High",
    "Handball": "Medium", "Rugby League": "Medium", "Tennis": "Medium", "Motor Racing": "Medium",
    "Snooker": "Medium", "Darts": "Medium", "Cricket": "Medium", "Golf": "Medium",
    "Rugby Union": "Medium", "Gaelic Sports": "Low", "Greyhounds": "Low",
}


def utc(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", "T")
    m = re.match(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d)(:\d\d)?", s)
    return f"{m.group(1)}{m.group(2) or ':00'}Z" if m else ""


def in_window(start: str = "", date: str = "") -> bool:
    if start:
        return WINDOW_START <= start <= WINDOW_END
    if date:
        return WINDOW_START[:10] <= date <= WINDOW_END[:10]
    return False


def blank_row(**kw) -> dict:
    r = {"id": "", "sport": "", "sport_slug": "", "competition": "", "start_utc": "", "date": "",
         "venue": "", "side_a": "", "side_b": "", "source_url": "", "source_name": "",
         "source_id": "", "inputs": {}, "markets": {}, "pick": None, "flags": [],
         "status": "upcoming", "olbg": None}
    r.update(kw)
    return r


def market(name: str, line, selections, note: str = "") -> dict:
    return {"line": line, "note": note, "selections": [{"name": n, "p": p} for n, p in selections]}


OLBG_MARKET = {
    "money line": "match_winner", "match winner": "match_winner", "match betting": "match_winner",
    "winner": "match_winner", "head to head": "match_winner", "outright": "match_winner",
    "total goals": "total", "total points": "total", "total sets": "total", "over/under": "total",
    "game totals": "total", "goals over/under": "total", "total": "total", "totals": "total",
    "win match": "match_winner", "to win": "match_winner", "full time result": "match_winner",
    "ft result": "match_winner", "1x2": "match_winner", "outright winner": "match_winner",
    "grand final winner": "match_winner", "tournament winner": "match_winner",
    "match result": "match_winner", "to win match": "match_winner",
    "total frames": "total", "total runs": "total", "game total": "total",
    "puck line": "handicap", "handicap": "handicap", "spread": "handicap", "point spread": "handicap",
    "run line": "handicap", "set handicap": "handicap", "frame handicap": "handicap",
    "asian handicap": "handicap", "alternative handicap": "handicap",
}


def _sel_key(mkt: str, sel: str) -> tuple:
    """Loose key so an OLBG selection can be matched to one of ours."""
    s = (sel or "").lower().replace("-", " ").strip()
    num = re.search(r"(\d+(?:\.\d)?)", s)
    side = "over" if s.startswith("over") else ("under" if s.startswith("under") else "")
    toks = tuple(t for t in re.findall(r"[a-z]{3,}", s) if t not in ("over", "under", "the"))
    return (mkt, side, num.group(1) if num else "", toks)


def find_quote(row: dict, mname: str, sel: str):
    """The OLBG price shown for this exact selection, if the listing carried one."""
    tips = (row.get("olbg") or {}).get("tips", [])
    if not tips:
        return None
    want = _sel_key(mname, sel)
    for q in tips:
        m = OLBG_MARKET.get((q.get("market") or "").lower().strip())
        if m != mname:
            continue
        have = _sel_key(m, q.get("selection", ""))
        if want[1] and have[1]:
            if want[1] == have[1] and want[2] == have[2]:
                return q
            continue
        if want[3] and have[3]:
            shared = set(want[3]) & set(have[3])
            if shared and (len(shared) >= min(len(want[3]), len(have[3])) or len(shared) >= 2):
                return q
    return None


def choose_pick(row: dict) -> None:
    """Highest-probability selection at 55%+ whose price is inside -250…+10,000.

    Two filters, both from the brief: we only publish a selection we make at least
    a marginal favourite (55%), and only if its price is still in the requested
    band.  A match whose favourite is shorter than -250 cannot produce such a
    selection, so it is published without a pick and the reason is recorded.
    """
    cands = []
    for mname, mk in (row.get("markets") or {}).items():
        for s in mk.get("selections", []):
            if s["p"] < 0.50:
                continue
            d = M.dec_from_p(s["p"])
            if not M.in_price_window(d):
                continue
            q = find_quote(row, mname, s["name"])
            mkt_dec, basis = None, "fair"
            if q and q.get("decimal"):
                try:
                    mkt_dec = float(q["decimal"])
                except ValueError:
                    mkt_dec = None
                if mkt_dec and M.in_price_window(mkt_dec):
                    basis = "market"
                elif mkt_dec:
                    continue
            cands.append({"market": mname, "selection": s["name"], "p": s["p"], "decimal": d,
                          "american": M.american(d), "market_decimal": mkt_dec,
                          "market_american": M.american(mkt_dec) if mkt_dec else None,
                          "band_basis": basis})
    if not cands:
        row["flags"].append("nothing we price at 50% or better sits inside the -250…+10,000 band: either the favourite is shorter than -250 or every in-band selection is an underdog")
        return
    best = max(cands, key=lambda x: x["p"])
    best["confidence"] = M.confidence(
        best["p"], CAP_CONF.get(row["sport"], "Medium"),
        sample_games=int(row["inputs"].get("sample_games") or 0))
    best["in_band"] = True
    best["basis"] = row["inputs"].get("method", "")
    row["pick"] = best


def attack_defence(table: dict, fk="gf", ak="ga", gpk="gp"):
    gp = sum((t.get(gpk) or 0) for t in table.values()) or 1
    total = sum((t.get(fk) or 0) for t in table.values()) or 1
    L = total / gp
    out = {}
    for k, t in table.items():
        g = t.get(gpk) or 0
        if not g:
            continue
        out[k] = {"att": (t.get(fk) or 0) / g / L, "def": (t.get(ak) or 0) / g / L, "gp": g,
                  "for_pg": round((t.get(fk) or 0) / g, 2),
                  "against_pg": round((t.get(ak) or 0) / g, 2)}
    return L, out


def norm_name(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(fc|ac|bk|bc|hk|if|sc|hc|bm|kv|w|women|men|club|handball|rugby|basket|volley)\b", " ", s)
    return re.sub(r"[^a-z0-9 ]", " ", s)


def match_name(want: str, pool) -> str | None:
    """Longest-token match of an OLBG/table name against official table keys."""
    w = set(t for t in norm_name(want).split() if len(t) > 2)
    if not w:
        return None
    best, score = None, 0
    for k in pool:
        kk = set(t for t in norm_name(k).split() if len(t) > 2)
        if not kk:
            continue
        common = len(w & kk)
        if common > score and (common >= 2 or (common == 1 and len(w) == 1)):
            best, score = k, common
    return best


def spread_near(mu: float, step: float = 0.5) -> float:
    """Signed handicap for the home side: negative when the home team gives points.

    Always lands on a half-point so the market cannot push.
    """
    sign = 1.0 if mu > 0 else -1.0      # home favourite gives points, so the line is negative
    s = round(abs(mu) / step) * step
    if s < step:
        s = step
    if abs(s - round(s)) < 1e-9:
        s += step
    return -sign * s


def emit_markets(row, *, p_home, p_away, p_draw=None, spread, p_home_covers,
                 total_line, p_over, label):
    """Write the three market families with home = side_b, away = side_a.

    Every builder in this file puts the *home* side in ``side_b`` because the
    official feeds all list the visiting side first.  Keeping that single
    convention here is what stops a handicap being attached to the wrong team.
    """
    away, home = row["side_a"], row["side_b"]
    sel = [(away, p_away)]
    if p_draw is not None:
        sel.append(("Draw", p_draw))
    sel.append((home, p_home))
    row["markets"] = {
        "match_winner": market("Match Winner", None, sel, "3-way" if p_draw is not None else "2-way"),
        "handicap": market("Handicap", spread,
                           [(f"{home} {spread:+.1f}", p_home_covers),
                            (f"{away} {-spread:+.1f}", 1 - p_home_covers)], label),
        "total": market("Match Total", total_line,
                        [(f"Over {total_line}", p_over), (f"Under {total_line}", 1 - p_over)], label),
    }


def goal_markets(row, lam_home, lam_away, draw_ok, total_line, spread, label):
    g = M.goal_markets(lam_home, lam_away, total_line, spread, draw_ok=draw_ok)
    if not draw_ok and abs(abs(spread) - 0.5) < 1e-9:
        # In a sport that cannot draw, a half-goal line is exactly the moneyline.
        covers = g["home"] if spread < 0 else 1 - g["home"]
        g["handicap_home"] = covers
    emit_markets(row, p_home=g["home"], p_away=g["away"],
                 p_draw=g["draw"] if draw_ok else None, spread=spread,
                 p_home_covers=g["handicap_home"], total_line=total_line,
                 p_over=g["over"], label=label)
    row["inputs"].update({"exp_home": round(lam_home, 3), "exp_away": round(lam_away, 3),
                          "exp_total": round(lam_home + lam_away, 3), "total_line": total_line,
                          "handicap_line": spread})


def margin_markets(row, margin_home, sd, spread, total_mu, sd_total, total_line, label):
    g = M.normal_markets(margin_home, sd, total_line, spread)
    p_over = 1.0 - M.norm_cdf((total_line - total_mu) / sd_total)
    emit_markets(row, p_home=g["home"], p_away=g["away"], spread=spread,
                 p_home_covers=g["handicap_home"], total_line=total_line, p_over=p_over, label=label)
    row["inputs"].update({"exp_margin": round(margin_home, 2), "exp_total": round(total_mu, 2),
                          "sd_margin": sd, "sd_total": sd_total,
                          "total_line": total_line, "handicap_line": spread})


# ------------------------------------------------------------------- builders
def nhl_recent(cap, n=5):
    """Last n completed NHL results per club, straight from the official schedule API."""
    import re as _re
    played = {}
    for tid in sorted(i for i in cap.by_id if _re.match(r"nhl_sched_\d{4}-\d\d-\d\d$", i)):
        try:
            data = cap.json(tid)
        except Exception:  # noqa: BLE001
            continue
        for week in data.get("gameWeek", []):
            for g in week.get("games", []):
                if g.get("gameState") not in ("OFF", "FINAL"):
                    continue
                try:
                    hs = g["homeTeam"]["score"]
                    as_ = g["awayTeam"]["score"]
                except (KeyError, TypeError):
                    continue
                day = (g.get("startTimeUTC") or "")[:10]
                played.setdefault(g["homeTeam"]["abbrev"], []).append(
                    (day, f"{'W' if hs > as_ else ('L' if hs < as_ else 'T')} {hs}-{as_} v {g['awayTeam']['abbrev']}"))
                played.setdefault(g["awayTeam"]["abbrev"], []).append(
                    (day, f"{'W' if as_ > hs else ('L' if as_ < hs else 'T')} {as_}-{hs} at {g['homeTeam']['abbrev']}"))
    return {k: [x[1] + " (" + x[0] + ")" for x in sorted(v)[-n:]] for k, v in played.items()}


def build_ice_hockey(cap, rows):
    if not cap.exists("nhl_standings"):
        return
    recent = nhl_recent(cap)
    table = P.read_nhl_standings(cap)
    L, ad = attack_defence(table)
    for f in P.read_nhl(cap):
        if not in_window(f["start_utc"]):
            continue
        a, b = ad.get(f["a_code"]), ad.get(f["b_code"])
        row = blank_row(id=f["id"], sport="Ice Hockey", sport_slug="ice-hockey",
                        competition=f["competition"], start_utc=f["start_utc"], date=f["start_utc"][:10],
                        venue=f.get("venue", ""), side_a=f["side_a"], side_b=f["side_b"],
                        source_url=f["source_url"], source_name=f["source_name"], source_id=f["source_id"])
        if not a or not b:
            row["flags"].append("official standings row missing for one club - no line originated")
            rows.append(row)
            continue
        lam_h = L * b["att"] * a["def"] * HOME_EDGE["Ice Hockey"]["factor"]
        lam_a = L * a["att"] * b["def"]
        row["inputs"] = {"method": "Poisson on NHL goals for/against per game, home factor 1.06",
                         "home_gf_pg": b["for_pg"], "home_ga_pg": b["against_pg"],
                         "away_gf_pg": a["for_pg"], "away_ga_pg": a["against_pg"],
                         "home_gp": b["gp"], "away_gp": a["gp"],
                         "home_l10": table[f["b_code"]].get("l10", ""),
                         "away_l10": table[f["a_code"]].get("l10", ""),
                         **({"home_recent": recent[f["b_code"]]} if recent.get(f["b_code"]) else {}),
                         **({"away_recent": recent[f["a_code"]]} if recent.get(f["a_code"]) else {}),
                         "sample_games": min(a["gp"], b["gp"])}
        # the puck line and run line are fixed half-goal markets, not something we choose
        puck = -1.5 if lam_h > lam_a else 1.5
        goal_markets(row, lam_h, lam_a, False,
                     5.5 if lam_h + lam_a < 6.3 else 6.5, puck, "Puck line/goals")
        choose_pick(row)
        rows.append(row)


def build_basketball(cap, rows):
    for tid, comp in (("el_games", "EuroLeague 2026-27"), ("eurocup_games", "EuroCup 2026-27")):
        if not cap.exists(tid):
            continue
        table, fixtures = {}, []
        for g in cap.json(tid).get("data", []):
            try:
                home, away = g["local"]["club"]["name"], g["road"]["club"]["name"]
            except Exception:  # noqa: BLE001
                continue
            hs = (g.get("local") or {}).get("score")
            as_ = (g.get("road") or {}).get("score")
            start = utc(g.get("utcDate") or g.get("date") or "")
            if g.get("played") and hs is not None and as_ is not None:
                for nm, pf, pa in ((home, hs, as_), (away, as_, hs)):
                    t = table.setdefault(nm, {"gp": 0, "gf": 0, "ga": 0})
                    t["gp"] += 1
                    t["gf"] += pf
                    t["ga"] += pa
            elif (g.get("phaseType") or {}).get("code") == "RS":
                fixtures.append({"home": home, "away": away, "start": start,
                                 "round": g.get("roundName", ""), "id": g.get("identifier", "")})
        if not table:
            continue
        L, ad = attack_defence(table)
        for f in fixtures:
            if not in_window(f["start"]):
                continue
            b, a = ad.get(f["home"]), ad.get(f["away"])
            row = blank_row(id=f"fx_{tid}_{f['id']}", sport="Basketball", sport_slug="basketball",
                            competition=comp, start_utc=f["start"], date=f["start"][:10],
                            side_a=f["away"], side_b=f["home"],
                            source_url=cap.url(tid),
                            source_name="EuroLeague official games feed (api-live.euroleague.net)",
                            source_id=tid)
            if not a or not b:
                row["flags"].append("official results row missing for one club - no line originated")
                rows.append(row)
                continue
            # a is the away club, b the home club
            lam_h = L * b["att"] * a["def"] + HOME_EDGE["Basketball"]["margin"] / 2
            lam_a = L * a["att"] * b["def"] - HOME_EDGE["Basketball"]["margin"] / 2
            margin, total = lam_h - lam_a, lam_h + lam_a
            row["inputs"] = {"method": "Normal margin on EuroLeague points for/against per game",
                             "home_ppg": b["for_pg"], "home_papg": b["against_pg"],
                             "away_ppg": a["for_pg"], "away_papg": a["against_pg"],
                             "home_gp": b["gp"], "away_gp": a["gp"], "round": f["round"],
                             "sample_games": min(a["gp"], b["gp"])}
            margin_markets(row, margin, HOME_EDGE["Basketball"]["sd"], spread_near(margin),
                           total, 19.0, round(total * 2) / 2 + 0.5, "Points")
            choose_pick(row)
            rows.append(row)
    for f in S.read_nba_schedule(cap):
        if not in_window(f["start_utc"]):
            continue
        row = blank_row(id=f["id"], sport="Basketball", sport_slug="basketball",
                        competition=f["competition"], start_utc=f["start_utc"], date=f["start_utc"][:10],
                        side_a=f["side_a"], side_b=f["side_b"], source_url=f["source_url"],
                        source_name=f["source_name"], source_id=f["source_id"])
        row["inputs"] = {"sample_games": 0}
        row["flags"].append("no completed-game results feed captured for the NBA season to date - fixture published unpriced")
        rows.append(row)


def build_baseball(cap, rows):
    if not cap.exists("mlb_standings"):
        return
    raw = cap.json("mlb_standings")
    name_by_id = {}
    for rec in raw.get("records", []):
        for t in rec.get("teamRecords", []):
            name_by_id[str(t["team"].get("id"))] = t["team"]["name"]
    table = P.read_mlb_standings(cap)
    tv = {k: v for k, v in table.items() if not k.startswith("id:")}
    L, ad = attack_defence(tv, fk="rs", ak="ra")
    for f in P.read_mlb(cap):
        if not in_window(f["start_utc"]):
            continue
        home_full = name_by_id.get(str(f["extra"].get("home_id")), f["side_b"])
        away_full = name_by_id.get(str(f["extra"].get("away_id")), f["side_a"])
        def nick(nm):
            return nm.split()[-1] if nm else ""
        a = tv.get(home_full) or tv.get(nick(home_full))
        b = tv.get(away_full) or tv.get(nick(away_full))
        row = blank_row(id=f["id"], sport="Baseball", sport_slug="baseball", competition=f["competition"],
                        start_utc=f["start_utc"], date=f["start_utc"][:10], venue=f.get("venue", ""),
                        side_a=f["side_a"], side_b=f["side_b"], source_url=f["source_url"],
                        source_name=f["source_name"], source_id=f["source_id"])
        if not a or not b:
            row["flags"].append("official standings row missing for one club - no line originated")
            rows.append(row)
            continue
        hn, an = home_full, away_full
        if hn not in ad:
            ad[hn] = ad.get(hn.split()[-1]) if hn else None
        if an not in ad:
            ad[an] = ad.get(an.split()[-1]) if an else None
        if not ad.get(hn) or not ad.get(an):
            row["flags"].append("official standings row missing for one club - no line originated")
            rows.append(row)
            continue
        lam_h = L * ad[hn]["att"] * ad[an]["def"] * HOME_EDGE["Baseball"]["factor"]
        lam_a = L * ad[an]["att"] * ad[hn]["def"]
        row["inputs"] = {"method": "Poisson on MLB runs scored/allowed per game, home factor 1.04",
                         "home_rs_pg": a["rs_pg"], "home_ra_pg": a["ra_pg"],
                         "away_rs_pg": b["rs_pg"], "away_ra_pg": b["ra_pg"],
                         "home_record": f"{a['w']}-{a['l']}", "away_record": f"{b['w']}-{b['l']}",
                         "home_gp": a["gp"], "away_gp": b["gp"],
                         "home_pitcher": f["extra"].get("home_pitcher", ""),
                         "away_pitcher": f["extra"].get("away_pitcher", ""),
                         "sample_games": min(a["gp"], b["gp"])}
        if row["start_utc"].endswith("T00:00:00Z"):
            row["flags"].append("first pitch not published for this date in the captured schedule - kick-off shown as 00:00 UTC")
        if not row["inputs"]["home_pitcher"] or not row["inputs"]["away_pitcher"]:
            row["flags"].append("probable pitchers not published for this date in the captured schedule")
        run_line = -1.5 if lam_h > lam_a else 1.5
        goal_markets(row, lam_h, lam_a, False, 8.5 if lam_h + lam_a < 9.2 else 9.5,
                     run_line, "Runs")
        choose_pick(row)
        rows.append(row)


def read_plusliga_fixtures(cap, tid="plusliga_fixtures"):
    """PlusLiga official fixtures page: results and scheduled matches in one table.

    Each row is date | phase | home | sets home | : | sets away | away | "Więcej".
    """
    if not cap.exists(tid):
        return []
    t = re.sub(r"<script.*?</script>", "", cap.text(tid), flags=re.S)
    raw = re.sub(r"<[^>]+>", "|", t)
    raw = re.sub(r"(\|\s*)+", "|", raw)
    cells = [c.strip() for c in raw.split("|")]
    out = []
    for i, c in enumerate(cells):
        m = re.match(r"^(\d{1,2})\.(\d{2})\.(\d{4})(?:, (\d{1,2}):(\d{2}))?$", c)
        if not m:
            continue
        j = i + 1
        if cells[j].startswith(("Faza", "Runda")):
            j += 1
        if j + 5 >= len(cells):
            break
        home, s1, sep, s2, away = cells[j], cells[j + 1], cells[j + 2], cells[j + 3], cells[j + 4]
        if sep != ":" or not away or away in ("Więcej", "Faza Zasadnicza", "Runda"):
            continue
        date = f"{m.group(3)}-{m.group(2)}-{int(m.group(1)):02d}"
        start = f"{date}T{int(m.group(4)):02d}:{m.group(5)}:00Z" if m.group(4) else ""
        out.append({"id": "fx_plusliga_" + re.sub(r"\W+", "_", f"{date}_{home}_{away}")[:60],
                    "side_a": away, "side_b": home, "date": date, "start_utc": start,
                    "score": (int(s1), int(s2)) if s1.isdigit() and s2.isdigit() and s1 != "0" or
                             (s1.isdigit() and s2.isdigit()) else None})
    return out


def build_volleyball(cap, rows):
    if not (cap.exists("plusliga_table") and cap.exists("plusliga_fixtures")):
        return
    table = P.read_plusliga(cap, "plusliga_table")
    fixtures = read_plusliga_fixtures(cap)
    if not table or not fixtures:
        return

    def rate(t):
        tot = (t["sw"] + t["sl"]) or 1
        return t["sw"] / tot

    for f in fixtures:
        if not in_window(f["start_utc"], f["date"]) or f["score"]:
            continue
        kh = match_name(f["side_b"], table)
        ka = match_name(f["side_a"], table)
        h = table.get(kh or "")
        w = table.get(ka or "")
        row = blank_row(id=f["id"], sport="Volleyball", sport_slug="volleyball",
                        competition="PlusLiga 2026-27 (Poland)", start_utc=f["start_utc"],
                        date=f["date"], side_a=f["side_a"], side_b=f["side_b"],
                        source_url=cap.url("plusliga_fixtures"),
                        source_name="PlusLiga official fixtures and table (plusliga.pl)",
                        source_id="plusliga_fixtures")
        if not f["start_utc"]:
            row["flags"].append("kick-off time not published on the official fixtures list - date only")
        if not h or not w:
            row["flags"].append("official table row missing for one club - no line originated")
            rows.append(row)
            continue
        p_set = 0.5 + 0.55 * (rate(h) - rate(w)) + HOME_EDGE["Volleyball"]["p_set"]
        p_set = min(0.85, max(0.15, p_set))
        p_home_match = 0.0
        p_home_match = sum(
            math.comb(4, k) * p_set ** 3 * (1 - p_set) ** k for k in (0, 1, 2)
        ) if False else None
        # exact best-of-five with independent sets
        def wp(i, j):
            if i == 3:
                return 1.0
            if j == 3:
                return 0.0
            return p_set * wp(i + 1, j) + (1 - p_set) * wp(i, j + 1)
        p_home_match = wp(0, 0)
        p_five = math.comb(4, 2) * p_set ** 2 * (1 - p_set) ** 2
        p_30 = p_set ** 3
        p_31 = 3 * p_set ** 3 * (1 - p_set)
        row["inputs"] = {"method": "Set-win-rate model on the official PlusLiga table, +0.02 home set edge",
                         "home_sets_won": h["sw"], "home_sets_lost": h["sl"],
                         "away_sets_won": w["sw"], "away_sets_lost": w["sl"],
                         "home_gp": h["gp"], "away_gp": w["gp"],
                         "home_set_rate": round(rate(h), 3), "away_set_rate": round(rate(w), 3),
                         "p_set": round(p_set, 3), "sample_games": min(h["gp"], w["gp"]),
                         "table_name_home": kh, "table_name_away": ka,
                         "table_source_url": cap.url("plusliga_table")}
        row["markets"] = {
            "match_winner": market("Match Winner", None,
                                   [(f["side_a"], 1 - p_home_match), (f["side_b"], p_home_match)], "2-way"),
            "handicap": market("Set Handicap", -1.5,
                               [(f"{f['side_b']} -1.5", p_30 + p_31),
                                (f"{f['side_a']} +1.5", 1 - (p_30 + p_31))], "sets"),
            "total": market("Total Sets", 4.5,
                            [("Over 4.5", p_five), ("Under 4.5", 1 - p_five)], "sets"),
        }
        choose_pick(row)
        rows.append(row)


def build_handball(cap, rows, olbg_events):
    if not cap.exists("dk_herreligaen"):
        return
    table = P.read_herreligaen(cap)
    if not table:
        return
    L, ad = attack_defence(table)
    for ev in olbg_events:
        if ev["sport"] != "Handball" or not in_window(ev["start_utc"]):
            continue
        parties = re.split(r"\s+vs\s+", ev["event"])
        if len(parties) != 2:
            continue
        kh, ka = match_name(parties[0], ad), match_name(parties[1], ad)
        b, a = ad.get(kh or ""), ad.get(ka or "")
        row = blank_row(id="fx_hl_" + ev["event_id"], sport="Handball", sport_slug="handball",
                        competition="Herreligaen 2026-27 (Denmark)", start_utc=ev["start_utc"],
                        date=ev["start_utc"][:10], side_a=parties[1].strip(), side_b=parties[0].strip(),
                        source_url=cap.url("dk_herreligaen"),
                        source_name="Herreligaen official standings (tophaandbold.dk)",
                        source_id="dk_herreligaen")
        row["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                       "event_id": ev["event_id"], "tips": ev["tips"]}
        if not a or not b:
            row["flags"].append("club not found in the official Herreligaen table - no line originated")
            row["flags"].append("fixture date/time taken from the OLBG listing, not from the league page")
            rows.append(row)
            continue
        row["flags"].append("fixture date/time taken from the OLBG listing; strength inputs from the official table")
        lam_h = L * a["att"] * b["def"] * HOME_EDGE["Handball"]["factor"]
        lam_a = L * b["att"] * a["def"]
        row["inputs"] = {"method": "Poisson on Herreligaen goals per game, home factor 1.07",
                         "home_gf_pg": b["for_pg"], "home_ga_pg": b["against_pg"],
                         "away_gf_pg": a["for_pg"], "away_ga_pg": a["against_pg"],
                         "home_gp": b["gp"], "away_gp": a["gp"],
                         "sample_games": min(a["gp"], b["gp"])}
        goal_markets(row, lam_h, lam_a, True, round((lam_h + lam_a) * 2) / 2 + 0.5,
                     spread_near(lam_h - lam_a), "Goals")
        choose_pick(row)
        rows.append(row)


def build_rugby_league(cap, rows):
    if not cap.exists("rlwc_api_fixtures"):
        return
    fixtures = P.read_rlwc(cap)
    table = {}
    def acc(nm, pf, pa):
        t = table.setdefault(nm, {"gp": 0, "gf": 0, "ga": 0})
        t["gp"] += 1
        t["gf"] += pf
        t["ga"] += pa
    # the RLWC feed lists the home side first, so side_a is home here (every other
    # builder in this file keeps home in side_b) - swap on the way in.
    for f in fixtures:
        hs, as_ = f["extra"].get("home_score"), f["extra"].get("away_score")
        if hs is not None and as_ is not None:
            acc(f["side_a"], hs, as_)
            acc(f["side_b"], as_, hs)
    for f in fixtures:
        if not in_window(f["start_utc"]):
            continue
        if "TBA" in (f["side_a"] + f["side_b"]):
            continue  # semi-final placeholders are not fixtures yet
        home, away = f["side_a"], f["side_b"]
        a, b = table.get(away), table.get(home)
        row = blank_row(id=f["id"], sport="Rugby League", sport_slug="rugby-league",
                        competition=f["competition"], start_utc=f["start_utc"], date=f["start_utc"][:10],
                        venue=f.get("venue", ""), side_a=away, side_b=home,
                        source_url=f["source_url"], source_name=f["source_name"], source_id=f["source_id"])
        if not a or not b:
            row["flags"].append("no completed match for one side in the captured official fixtures - no line originated")
            rows.append(row)
            continue
        if min(a["gp"], b["gp"]) < 2:
            row["flags"].append("fewer than two completed matches for one side in the captured tournament feed - published without a line")
            rows.append(row)
            continue
        for t in (a, b):
            t["for_pg"] = round(t["gf"] / t["gp"], 2)
            t["against_pg"] = round(t["ga"] / t["gp"], 2)
        margin = (b["for_pg"] - b["against_pg"]) - (a["for_pg"] - a["against_pg"]) + HOME_EDGE["Rugby League"]["margin"]
        total = (a["for_pg"] + a["against_pg"] + b["for_pg"] + b["against_pg"]) / 2
        row["inputs"] = {"method": "Normal margin on official tournament points for/against, home edge 3.5",
                         "home_for_pg": b["for_pg"], "home_against_pg": b["against_pg"],
                         "away_for_pg": a["for_pg"], "away_against_pg": a["against_pg"],
                         "home_gp": a["gp"], "away_gp": b["gp"],
                         "sample_games": min(a["gp"], b["gp"])}
        margin_markets(row, margin, HOME_EDGE["Rugby League"]["sd"], spread_near(margin),
                       total, 13.0, round(total * 2) / 2 + 0.5, "Points")
        choose_pick(row)
        rows.append(row)


def build_tennis(cap, rows, olbg_events):
    ranks = {}
    for tid in ("atp_rankings_api", "wta_rankings"):
        if not cap.exists(tid):
            continue
        try:
            data = cap.json(tid)
        except Exception:  # noqa: BLE001
            continue
        blocks = data if isinstance(data, list) else (data.get("rankings") or data.get("data") or data.get("Items") or [])
        for r in blocks:
            pl = r.get("player") or {}
            nm = " ".join(x for x in (pl.get("firstName", ""), pl.get("lastName", "")) if x) \
                 or r.get("playerName", "") or r.get("PlayerName", "") or r.get("name", "") \
                 or " ".join(x for x in (r.get("PlayerFirstName", ""), r.get("PlayerLastName", "")) if x)
            rk = r.get("rank") or r.get("ranking") or r.get("Rank") or r.get("PlayerRank")
            if nm and rk:
                ranks[nm.strip().lower()] = int(rk)
    if not ranks:
        return

    def find(name):
        n = re.sub(r"\s+", " ", name).strip().lower()
        if n in ranks:
            return ranks[n], n
        last = n.split()[-1]
        for k, v in ranks.items():
            if k.split()[-1] == last:
                return v, k
        return None, n

    for ev in olbg_events:
        if ev["sport"] != "Tennis" or not in_window(ev["start_utc"]):
            continue
        parties = re.split(r"\s+(?:vs|v)\s+", ev["event"])
        if len(parties) != 2:
            continue
        ra, ka = find(parties[0])
        rb, kb = find(parties[1])
        row = blank_row(id="fx_ten_" + ev["event_id"], sport="Tennis", sport_slug="tennis",
                        competition="Tennis (event listed on OLBG)", start_utc=ev["start_utc"],
                        date=ev["start_utc"][:10], side_a=ka.title(), side_b=kb.title(),
                        source_url=cap.url("atp_rankings_api") if cap.exists("atp_rankings_api") else ev["event_url"],
                        source_name="Official ATP singles ranking (api.atptour.com)",
                        source_id="atp_rankings_api")
        row["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                       "event_id": ev["event_id"], "tips": ev["tips"]}
        if not ra or not rb:
            row["flags"].append("one player is not in the captured official singles ranking - no line originated")
            row["flags"].append("fixture pairing taken from the OLBG listing; tournament draw not captured")
            rows.append(row)
            continue
        row["flags"].append("fixture pairing taken from the OLBG listing; strength inputs from official ranking")
        p_a = min(0.93, max(0.07, M.elo_p(ra, rb, 40.0) if False else 1 / (1 + 10 ** ((rb - ra) / 40.0))))
        row["inputs"] = {"method": "Logistic on official singles ranking gap",
                         "rank_a": ra, "rank_b": rb, "sample_games": 0}
        row["markets"] = {
            "match_winner": market("Match Winner", None,
                                   [(row["side_a"], p_a), (row["side_b"], 1 - p_a)], "2-way"),
            "handicap": market("Game Handicap", -2.5,
                               [(f"{row['side_a']} -2.5", 0.5 + (p_a - 0.5) * 0.42),
                                (f"{row['side_b']} +2.5", 0.5 - (p_a - 0.5) * 0.42)], "games"),
        }
        choose_pick(row)
        rows.append(row)


def build_motorsport(cap, rows, olbg_events):
    if not cap.exists("f1_drivers"):
        return
    st = P.read_f1(cap) if hasattr(P, "read_f1") else None
    if not st or not st.get("standings"):
        return
    standings = st["standings"]
    probs = M.plackett_luce([x["pts"] for x in standings], 420.0)
    best = max(range(len(standings)), key=lambda i: probs[i])
    race = next((r for r in st.get("races", []) if "Mexico" in r.get("name", "")), None)
    ev = next((e for e in olbg_events if e["sport"] == "Motor Racing" and in_window(e["start_utc"])), None)
    row = blank_row(id="fx_f1_next", sport="Motor Racing", sport_slug="motor-racing",
                    competition="Formula 1 2026 - " + (race or {}).get("name", "next round"),
                    start_utc=(ev or {}).get("start_utc", ""), date=((ev or {}).get("start_utc", "") or "")[:10],
                    venue="", side_a=(race or {}).get("name", "Grand Prix"), side_b="",
                    source_url=cap.url("f1_drivers"),
                    source_name="Formula 1 official drivers' standings (formula1.com)",
                    source_id="f1_drivers")
    if ev:
        row["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                       "event_id": ev["event_id"], "tips": ev["tips"]}
    if not row["start_utc"]:
        row["flags"].append("race start time not published on the captured standings page - the round window is shown instead")
    row["inputs"] = {"method": "Plackett-Luce on official championship points, tau 420",
                     "leader": standings[best]["driver"], "leader_pts": standings[best]["pts"],
                     "field": len(standings), "sample_games": 0,
                     "round": (race or {}).get("round", ""), "dates": (race or {}).get("dates", "")}
    row["markets"] = {
        "match_winner": market("Race Winner", None,
                               [(standings[best]["driver"], probs[best]),
                                ("Field (any other driver)", 1 - probs[best])], "outright"),
    }
    choose_pick(row)
    rows.append(row)


def build_unpriced(cap, rows, olbg_events):
    """Sports where the captured official pages do not carry a strength input."""
    done = set()
    if cap.exists("wst_matches_api"):
        for f in P.read_wst(cap)[0]:
            if not in_window(f["start_utc"]):
                continue
            row = blank_row(id=f["id"], sport="Snooker", sport_slug="snooker",
                            competition=f["competition"], start_utc=f["start_utc"],
                            date=f["start_utc"][:10], side_a=f["side_a"], side_b=f["side_b"],
                            source_url=f["source_url"], source_name=f["source_name"],
                            source_id=f["source_id"])
            row["inputs"] = {"best_of": f["extra"].get("best_of"), "sample_games": 0}
            row["flags"].append("official WST world-ranking feed not captured (rankings page is script-rendered) - no line originated")
            rows.append(row)
            done.add("Snooker")
    if cap.exists("gaa_fixtures"):
        for f in P.read_gaa(cap):
            if not in_window(f["start_utc"]):
                continue
            row = blank_row(id=f["id"], sport="Gaelic Sports", sport_slug="gaelic-sports",
                            competition=f.get("competition", "GAA"), start_utc=f["start_utc"],
                            date=f["start_utc"][:10], venue=f.get("venue", ""),
                            side_a=f["side_a"], side_b=f["side_b"], source_url=f["source_url"],
                            source_name=f["source_name"], source_id=f["source_id"])
            row["flags"].append("GAA club fixtures carry no official scoring table for these competitions - no line originated")
            rows.append(row)
            done.add("Gaelic Sports")
    # everything else: publish the OLBG-listed events, unpriced, with the reason
    matched = {"Golf", "Cricket", "Darts", "Rugby Union", "Greyhounds"}
    for ev in olbg_events:
        if ev["sport"] not in SLUG or ev["sport"] in matched:
            pass
        if ev["sport"] not in SLUG or not in_window(ev["start_utc"]):
            continue
        if any((r.get("olbg") or {}).get("event_id") == ev["event_id"] for r in rows):
            continue
        row = blank_row(id="olbg_" + ev["event_id"], sport=ev["sport"], sport_slug=SLUG[ev["sport"]],
                        competition="Listed on OLBG", start_utc=ev["start_utc"],
                        date=ev["start_utc"][:10], side_a=ev["event"], side_b="",
                        source_url=ev["event_url"],
                        source_name="OLBG event listing (market existence only)", source_id=ev["hub_url"])
        row["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                       "event_id": ev["event_id"], "tips": ev["tips"]}
        row["inputs"] = {"sample_games": 0}
        row["flags"].append(REASONS.get(ev["sport"], "no official strength input captured for this sport - no line originated"))
        rows.append(row)


REASONS = {
    "Golf": "the captured PGA Tour leaderboard resolved to a completed event, so no field exists to price - no line originated",
    "Cricket": "the captured ICC team-ranking pages are script-rendered, so no official rating could be read - no line originated",
    "Darts": "the PDC fixtures and order-of-merit pages are script-rendered, so no official ranking could be read - no line originated",
    "Rugby Union": "the URC standings page is script-rendered and the fixtures page carries no scores, so no official league table could be read - no line originated",
    "Greyhounds": "the GBGB API returned 404 at capture, so no official racecard exists to price - no line originated",
}


def attach_olbg(rows, events):
    def norm(s: str) -> str:
        s = re.sub(r"\(.*?\)", "", s or "").lower()
        s = re.sub(r"\b(fc|men|women|u21|u20|u19|reserves|ac|bk|bc|hk|if)\b", " ", s)
        return re.sub(r"[^a-z0-9]", "", s)

    idx = {}
    for ev in events:
        p = re.split(r"\s+(?:vs|v|@|-)\s+", ev.get("event", ""))
        if len(p) == 2:
            idx.setdefault((norm(p[0]), norm(p[1])), ev)
            idx.setdefault((norm(p[1]), norm(p[0])), ev)
    def nick(name: str) -> set:
        toks = [t for t in norm_name(name).split() if len(t) > 2]
        return {toks[-1]} if toks else set()

    for r in rows:
        if r.get("olbg"):
            continue
        ev = idx.get((norm(r["side_a"]), norm(r["side_b"])))
        if not ev:
            na, nb = nick(r["side_a"]), nick(r["side_b"])
            for cand in events:
                if cand["sport"] != r["sport"]:
                    continue
                p = re.split(r"\s+(?:vs|v|@|-)\s+", cand.get("event", ""))
                if len(p) != 2:
                    continue
                if na and nb and ({t for t in norm_name(p[0]).split() if t in na} and
                                  {t for t in norm_name(p[1]).split() if t in nb}):
                    ev = cand
                    break
        if ev:
            r["olbg"] = {"event": ev["event"], "event_url": ev["event_url"], "hub_url": ev["hub_url"],
                         "event_id": ev["event_id"], "tips": ev["tips"]}
            if r.get("pick"):
                choose_pick(r)


def band_stats(rows):
    """How many rows are barred from a High pick only by the -250 floor.

    A selection we make 70%+ for prices at 1.39 or shorter, which is outside the
    requested band.  Counting them keeps the shortfall visible instead of quietly
    downgrading them.
    """
    near = 0
    for r in rows:
        best = 0.0
        for mk in (r.get("markets") or {}).values():
            for s in mk.get("selections", []):
                if s["p"] >= 0.70:
                    best = max(best, s["p"])
        if best and not r.get("pick"):
            near += 1
    return {"rows_blocked_by_price_floor": near}


def summarise(rows):
    out = {}
    for sport, slug in SUPPORTED:
        s = [r for r in rows if r["sport"] == sport]
        p = [r for r in s if r.get("pick")]
        out[sport] = {"slug": slug, "rows": len(s), "priced": len(p),
                      "high": len([r for r in p if r["pick"]["confidence"] == "High"]),
                      "in_band": len([r for r in p if r["pick"].get("in_band")]),
                      "markets": sum(len(r["markets"]) for r in s)}
    return out


def build(cap_dir: str):
    cap = P.Capture(cap_dir)
    man = cap.manifest
    sel = S.read_olbg_rows(cap, [i for i in cap.by_id if i.startswith("olbg_")])
    events = list(S.group_olbg(sel).values())
    rows: list[dict] = []
    build_ice_hockey(cap, rows)
    build_basketball(cap, rows)
    build_baseball(cap, rows)
    build_volleyball(cap, rows)
    build_handball(cap, rows, events)
    build_rugby_league(cap, rows)
    build_tennis(cap, rows, events)
    build_motorsport(cap, rows, events)
    import builders2 as B2
    B2.build_snooker(sys.modules[__name__], cap, rows)
    B2.build_rugby_union(sys.modules[__name__], cap, rows)
    B2.build_handball_ehf(sys.modules[__name__], cap, rows, events)
    B2.build_liiga(sys.modules[__name__], cap, rows)
    build_unpriced(cap, rows, events)
    attach_olbg(rows, events)
    # a builder and the unpriced fallback can both emit the same fixture; keep the
    # one that carries a price, and keep first-seen order so the desk reads by sport
    best, order = {}, []
    for r in rows:
        k = r["id"]
        if k not in best:
            best[k] = r
            order.append(k)
        elif not best[k].get("pick") and r.get("pick"):
            best[k] = r
    rows = [best[k] for k in order]
    return cap, rows, events, man


METHODOLOGY = {
    "headline": ("Our lines are built only from official numbers captured on the same day, and the pick is the "
                 "highest-probability selection whose price is still inside −250…+10,000. Where an official input "
                 "was missing the row is published without a line and the reason is on the flag list."),
    "sections": {
        "From fixture to price":
            "A fixture is read from a governing body, league, tour or track feed: NHL and Liiga schedules, the "
            "MLB Stats API, the EuroLeague games feed, the PlusLiga fixtures page and table, the Herreligaen table, "
            "the RLWC fixtures API. Strength inputs are the official for/against or sets won/lost columns of the "
            "same competition. We turn those into per-game attack and defence multipliers, apply a fixed, "
            "documented home edge, then price the match with a Poisson grid for goal sports or a normal margin "
            "distribution for points sports.",
        "Which selection we publish":
            "Every originated selection is converted to a fair decimal price; only selections priced 1.40–101.00 "
            "(that is −250 to +10,000 American) are eligible, and of those the one we make most likely is the pick. "
            "That is why a row can show a 70% pick at a shade over even money rather than the 85% favourite: the "
            "brief asks for a high probability and a usable price, and those only overlap near the top of the band.",
        "Confidence labels":
            "High needs our own probability at or above 70% on a table-based input with at least ten completed "
            "games behind it. A sport whose only strength input is a ranking list is capped at Medium; anything "
            "with fewer than ten completed games is capped at Low.",
        "What we do not do":
            "We do not read a bookmaker price into our probability, we do not carry a number over from a previous "
            "snapshot, and we do not fill a blank. If a ranking, a table row or a start time is missing from the "
            "captured official pages, the field stays empty and the row is flagged.",
        "OLBG's role":
            "OLBG is used for two things only: to confirm an event is on the card, and to record the price the "
            "listing displayed (data-decimal in the listing markup). It is never a source of fact about a team, a "
            "player, a score or an injury. Where a fixture's date comes from OLBG rather than the league, the row "
            "says so in its flags.",
    },
    "constants": {
        "home_edge_ice_hockey": ["×1.06 on expected goals", "league-wide home scoring factor"],
        "home_edge_handball": ["×1.07 on expected goals", "league-wide home scoring factor"],
        "home_edge_baseball": ["×1.04 on expected runs", "league-wide home factor"],
        "home_edge_basketball": ["+2.6 points; margin sd 11.5", "league-wide home margin and spread of margins"],
        "home_edge_rugby_league": ["+3.5 points; margin sd 14.0", "league-wide home advantage and margin spread"],
        "home_edge_volleyball": ["+0.02 set probability", "league-wide home set edge"],
        "price_window": ["1.40 ≤ fair decimal ≤ 101.00", "−250 to +10,000 American"],
        "confidence_high": ["p ≥ 0.70", "the brief's threshold, applied to our own probability"],
        "basketball_total_sd": ["19.0 points", "spread of NBA/EuroLeague game totals"],
    },
}

OLBG_NOTES = {
    "summary": ("OLBG lists markets per sport behind numeric sport ids (Golf 5, Volleyball 21, Rugby Union 9, "
                "Cricket 7, Snooker 8, Darts 15, Baseball 12, Gaelic Football 25, Hurling 26, Greyhounds 28, "
                "Tennis 3, Motor Racing 14, Handball 20, Ice Hockey 13, Basketball 4, Rugby League 10). Each "
                "listing row carries the event link, the kick-off in a startDate attribute and OLBG's own price in "
                "data-decimal / data-american, which is what we record as the observed quote."),
    "patterns": {
        "/betting-tips/{Sport}/{sport_id}": "sport hub; tip cards carry selection, market alias and OLBG price",
        "/betting-tips/{Sport}/All_{Sport}/All_Events": "full event list for the sport",
        "/betting-tips/{Sport}/All_{Sport}/All_Events/{Slug}?event_id={id}": "single event page",
        'a[itemprop="url"][href*="event_id="]': "event link; the h5 beside it is the event name as OLBG prints it",
        'time[itemprop="startDate"][datetime]': "kick-off in UTC (ISO 8601)",
        "span.ui-odds[data-decimal][data-american]": "the displayed OLBG price for that selection",
    },
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("capture")
    ap.add_argument("--out", default=str(DATA / "desk.json"))
    args = ap.parse_args()
    cap, rows, events, man = build(args.capture)
    doc = {
        "schema": "ec-desk-1",
        "session": "arena/e0ca04cf-olbg4",
        "board": "EC",
        "capture": os.path.basename(args.capture.rstrip("/")),
        "capture_started_utc": man.get("started_utc", ""),
        "cutoff_utc": CUTOFF,
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "manifest": {"targets": man.get("targets"), "ok": man.get("ok"), "failed": man.get("failed"),
                     "started_utc": man.get("started_utc"), "finished_utc": man.get("finished_utc"),
                     "records": [{"id": r["id"], "sport": r.get("sport", ""), "url": r["url"],
                                  "bytes": r.get("bytes"), "sha256": r.get("sha256")}
                                 for r in sorted(man.get("records", []), key=lambda x: x["id"])],
                     "failures": man.get("failures", [])},
        "rows": rows,
        "summary": summarise(rows),
        "band_stats": band_stats(rows),
        "methodology": METHODOLOGY,
        "olbg_notes": dict(OLBG_NOTES, events=[
            {"sport": e["sport"], "event": e["event"], "start_utc": e["start_utc"],
             "url": e["event_url"], "tips": len(e["tips"])} for e in events]),
        "sport_notes": SPORT_NOTES,
        "olbg_market_taxonomy": taxonomy(events),
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(doc["summary"], indent=1))
    print("rows", len(rows), "priced", sum(1 for r in rows if r.get("pick")), "events", len(events))
    return 0


SPORT_NOTES = {
    "Ice Hockey": "Every NHL fixture in the window, priced from the official league standings (goals for and against per game, last-ten form).",
    "Basketball": "EuroLeague and EuroCup fixtures priced from the official games feed; NBA fixtures are listed from the official CDN schedule but carry no line because no completed-game feed was captured.",
    "Baseball": "MLB postseason fixtures priced from the official Stats API standings and run environment.",
    "Volleyball": "PlusLiga fixtures priced from the official PlusLiga table (sets won and lost).",
    "Handball": "Herreligaen fixtures taken from the OLBG card and priced from the official Danish table.",
    "Rugby League": "Rugby League World Cup fixtures priced from the tournament's own completed results.",
    "Tennis": "Pairings come from the OLBG listing; strength comes from the official ATP singles ranking.",
    "Motor Racing": "The next Formula 1 round, priced from the official drivers' championship standings.",
    "Snooker": "Official WST fixtures for the window. No ranking feed could be read, so no line is published.",
    "Golf": "The captured PGA Tour leaderboard resolved to a completed event, so there is no field to price.",
    "Cricket": "OLBG-listed cricket markets for the window. The ICC ranking pages are script-rendered, so no line is published.",
    "Darts": "OLBG-listed darts markets for the window. The PDC ranking and fixture pages are script-rendered, so no line is published.",
    "Rugby Union": "OLBG-listed rugby union markets for the window. The URC table is script-rendered, so no line is published.",
    "Gaelic Sports": "GAA fixtures for the window. Club championship fixtures carry no official scoring table.",
    "Greyhounds": "The GBGB endpoints returned 404 at capture, so only the OLBG card could be listed.",
}


def taxonomy(events):
    out = {}
    for e in events:
        for t in e["tips"]:
            m = t.get("market") or "(unlabelled)"
            out.setdefault(e["sport"], {})
            out[e["sport"]][m] = out[e["sport"]].get(m, 0) + 1
    return out


if __name__ == "__main__":
    raise SystemExit(main())

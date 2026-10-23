"""Board BW (session arena/343754f2-olbg4) — TOP 14 (Rugby Union) origination.

Inputs (both read from the committed capture, SHA-256 re-checked by the caller):
  * top14_classement  — top14.lnr.fr official league table (ranked 14 clubs, M / W / D / L /
                        bonus / points-for / points-against / difference at the time of capture)
  * top14_cal          — top14.lnr.fr official calendar page for the current round; the page's
                        score-slider component carries one JSON object per fixture with
                        hosting/visiting club, status and an exact ISO kickoff
                        (e.g. 2026-10-24T14:30:00+02:00), so start_utc is never inferred.

Model (published parameters, no hidden fitted constants):
  league_mean  = mean over the 14 clubs of points-for per match
  attack(x)    = (points-for / matches) / league_mean
  defence(x)   = (points-against / matches) / league_mean
  lambda_home  = league_mean * attack(home) * defence(away) * HFA
  lambda_away  = league_mean * attack(away) * defence(home) / HFA          HFA = 1.08
  Score distributions are independent Poisson. Draw mass is folded into a two-way
  market by renormalising P(home win) / (P(home win) + P(away win)) — the published
  probability is "home win in the two-way market", not "home win including the draw".
  Handicap: home -3.5 / -6.5 / -10.5 and the mirror lines, priced from the same joint
  distribution. Total: line = nearest half point to the modelled expected total,
  over/under from the joint distribution.

Sample gate: both clubs must have >= 5 completed league matches in the official table
(otherwise the row is published unpriced and flagged).
"""
from __future__ import annotations

import html
import json
import math
import re


def _pois(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _distribution(lh: float, la: float, cap: int = 110):
    ph = [_pois(lh, i) for i in range(cap + 1)]
    pa = [_pois(la, i) for i in range(cap + 1)]
    ph = [x / sum(ph) for x in ph]
    pa = [x / sum(pa) for x in pa]
    return ph, pa


def _joint(lh, la, cap=110):
    ph, pa = _distribution(lh, la, cap)
    home_win = sum(ph[i] * pa[j] for i in range(len(ph)) for j in range(len(pa)) if i > j)
    away_win = sum(ph[i] * pa[j] for i in range(len(ph)) for j in range(len(pa)) if i < j)
    draw = sum(ph[i] * pa[i] for i in range(min(len(ph), len(pa))))
    return ph, pa, home_win, away_win, draw


def _cover(ph, pa, line: float, side: str) -> float:
    """P(home covers line) where line is the home handicap (negative = gives points)."""
    p = 0.0
    for i in range(len(ph)):
        for j in range(len(pa)):
            d = (i - j) + line
            if side == "home" and d > 0:
                p += ph[i] * pa[j]
            elif side == "away" and d < 0:
                p += ph[i] * pa[j]
    return p


def _over(ph, pa, line: float) -> float:
    p = 0.0
    for i in range(len(ph)):
        for j in range(len(pa)):
            if i + j > line:
                p += ph[i] * pa[j]
    return p


def _parse_table(raw: str) -> dict:
    fixed = re.findall(
        r'<div class="table-line table-line--ranking-full table-line--ranking-fixed">(.*?)'
        r'(?=<div class="table-line table-line--ranking-full table-line--ranking-fixed">|</div>\s*</div>\s*</div>)',
        raw, flags=re.S)
    scroll = re.findall(
        r'<div class="table-line table-line--ranking-full table-line--ranking-scrollable">(.*?)'
        r'(?=<div class="table-line table-line--ranking-full table-line--ranking-scrollable">|</div>\s*</div>\s*</div>)',
        raw, flags=re.S)
    rows = []
    for f, s in zip(fixed, scroll):
        name_m = re.search(r'alt="([^"]+)"', f)
        rank_m = re.search(r'table-line__cell-wrapper--rank-(\d+)', f)
        cells = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip()
                 for c in re.findall(r'table-line__cell-wrapper--small">(.*?)</div>\s*</div>', s, flags=re.S)]
        if not (name_m and len(cells) >= 9):
            continue
        try:
            pts, m, w, d, l, bonus, pf, pa_, diff = (cells[0], int(cells[1]), int(cells[2]),
                                                      int(cells[3]), int(cells[4]), int(cells[5]),
                                                      int(cells[6]), int(cells[7]), cells[8])
        except ValueError:
            continue
        rows.append({"rank": int(rank_m.group(1)) if rank_m else None,
                     "club": html.unescape(name_m.group(1)), "pts": pts, "m": m, "w": w,
                     "d": d, "l": l, "bonus": bonus, "pf": pf, "pa": pa_, "diff": diff})
    return {r["club"]: r for r in rows}


def _parse_calendar(raw: str) -> list[dict]:
    m = re.search(r":matches='(\[\{.*?\}\])'", raw, flags=re.S)
    if not m:
        return []
    payload = html.unescape(m.group(1)).replace("\\/", "/")
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return []
    out = []
    for d in data:
        home = d.get("hosting_club", {}).get("name")
        away = d.get("visiting_club", {}).get("name")
        start = ((d.get("timer") or {}).get("firstPeriodStartDate") or "")
        out.append({"home": home, "away": away, "status": d.get("status", ""),
                    "start": start, "link": d.get("link", ""), "week": d.get("week_id")})
    return out


def parse_top14(reader, new_row, sel_row, two_way_market, finish_pick, flag):
    from datetime import datetime, timezone

    if not (reader.has("top14_classement") and reader.has("top14_cal")):
        flag("BW-F-RU-10", "review", "Rugby Union",
             "TOP 14 official table/calendar not captured",
             "top14.lnr.fr table and calendar are required to originate TOP 14 lines; one of the two "
             "captures is missing in this stamp, so no TOP 14 row is published.",
             "https://top14.lnr.fr/classement")
        return
    table = _parse_table(reader.read_text("top14_classement"))
    fixtures = _parse_calendar(reader.read_text("top14_cal"))
    url_t = reader.source_url("top14_classement")
    url_c = reader.source_url("top14_cal")
    stamp_t = reader.capture_stamp("top14_classement")
    stamp_c = reader.capture_stamp("top14_cal")
    if len(table) != 14 or not fixtures:
        flag("BW-F-RU-11", "review", "Rugby Union", "TOP 14 table/calendar shape unexpected",
             f"Parsed {len(table)} clubs (expected 14) and {len(fixtures)} fixture objects from the "
             f"official LNR pages; no TOP 14 row is published from an unexpected shape.",
             url_t)
        return
    league_mean = sum(r["pf"] / r["m"] for r in table.values() if r["m"]) / len(table)
    HFA = 1.08
    # current round label: read from the calendar page's own filter payload
    round_m = re.search(r'"name":"Journ\\u00e9e (\d+)"', reader.read_text("top14_cal"))
    rnd = round_m.group(1) if round_m else ""
    published = 0
    for fx in fixtures:
        home, away = fx["home"], fx["away"]
        th, ta = table.get(home), table.get(away)
        if not (th and ta):
            continue
        start = fx["start"]
        if not start or not start.startswith("2026-1"):
            continue
        dt = datetime.fromisoformat(start).astimezone(timezone.utc)
        start_utc = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        if not ("2026-10-23T00:00:00Z" <= start_utc < "2026-11-09T00:00:00Z"):
            continue
        comp = f"TOP 14 2026-27 — Journée {rnd}" if rnd else "TOP 14 2026-27"
        base = (f"Official LNR TOP 14 table (captured {stamp_t}): {home} {th['pts']} pts after {th['m']} "
                f"matches ({th['w']}W-{th['d']}D-{th['l']}L), {th['pf']} points for / {th['pa']} against; "
                f"{away} {ta['pts']} pts after {ta['m']} matches ({ta['w']}W-{ta['d']}D-{ta['l']}L), "
                f"{ta['pf']} for / {ta['pa']} against. Official fixture: {start} (LNR calendar, captured {stamp_c}).")
        gate_ok = th["m"] >= 5 and ta["m"] >= 5
        atk_h = (th["pf"] / th["m"]) / league_mean
        def_h = (th["pa"] / th["m"]) / league_mean
        atk_a = (ta["pf"] / ta["m"]) / league_mean
        def_a = (ta["pa"] / ta["m"]) / league_mean
        lh = league_mean * atk_h * def_a * HFA
        la = league_mean * atk_a * def_h / HFA
        ph, pa, hw, aw, dr = _joint(lh, la)
        p_home = hw / (hw + aw) if (hw + aw) else 0.5
        exp_total = lh + la
        total_line = math.floor(exp_total * 2) / 2 + 0.5
        p_over = _over(ph, pa, total_line)
        markets = {
            "match_winner": {"market_name": "Match Winner (two-way, draw removed)", "line": None,
                             "prob_sum": 1.0, "book_margin": 0.0,
                             "selections": [sel_row(f"{home} (home)", max(0.001, min(0.999, p_home))),
                                            sel_row(f"{away} (away)", 1 - max(0.001, min(0.999, p_home)))]},
            "total": {},
        }
        # handicap ladder around the modelled margin
        margin = lh - la
        lines = sorted({round(x * 2) / 2 for x in (margin - 6.5, margin - 3.5, margin - 0.5,
                                                   margin + 3.5, margin + 6.5)})
        primary = None
        for ln in lines:
            if ln == 0:
                continue
            p_hc = _cover(ph, pa, -ln, "home")
            p_hc = max(0.001, min(0.999, p_hc))
            mk = {
                "market_name": "Handicap", "line": -ln, "prob_sum": 1.0, "book_margin": 0.0,
                "selections": [sel_row(f"{home} {-ln:+g}", p_hc),
                               sel_row(f"{away} {ln:+g}", 1 - p_hc)],
            }
            markets[f"handicap_{ln:+g}"] = mk
            if primary is None or abs(ln - margin) < abs(primary["line"] + margin):
                primary = mk
        if "handicap" in markets and isinstance(markets["handicap"], dict):
            pass
        markets["handicap"] = primary or {"market_name": "Handicap", "line": None,
                                          "prob_sum": 1.0, "book_margin": 0.0, "selections": []}
        p_o = max(0.001, min(0.999, p_over))
        markets["total"] = {
            "market_name": "Match Total Points", "line": total_line, "prob_sum": 1.0,
            "book_margin": 0.0,
            "selections": [sel_row(f"Over {total_line}", p_o),
                           sel_row(f"Under {total_line}", 1 - p_o)],
        }
        summary = (base + f" Derived expectations: {lh:.2f} / {la:.2f} points "
                          f"(league mean {league_mean:.2f}, home factor {HFA}); win {p_home:.4f}, "
                          f"draw mass {dr:.4f}, expected total {exp_total:.2f} -> line {total_line}. "
                          f"Markets investigated: match winner, handicap ({len(markets['handicap'])} lines), "
                          f"match total. Injuries: no official LNR injury report was captured for this round, "
                          f"so none is claimed.")
        if not gate_ok:
            new_row(sport="Rugby Union", competition=comp, side_a=home, side_b=away,
                    matchup=f"{home} v {away}", start_utc=start_utc, venue="",
                    official_url=url_c,
                    official_source_name="LNR TOP 14 official calendar + league table",
                    capture_stamp=stamp_c, inputs_summary=summary + " Sample gate failed (a club has "
                                                                    "fewer than 5 completed matches) — unpriced, flagged.")
            flag("BW-F-RU-12", "review", "Rugby Union", "TOP 14 row unpriced — sample gate failed",
                 f"{home} v {away}: fewer than 5 completed league matches for at least one club.",
                 url_t)
            continue
        row = new_row(sport="Rugby Union", competition=comp, side_a=home, side_b=away,
                      matchup=f"{home} v {away}", start_utc=start_utc, venue="",
                      official_url=url_c,
                      official_source_name="LNR TOP 14 official calendar + league table",
                      capture_stamp=stamp_c, inputs_summary=summary, markets=markets)
        # choose the best in-window selection across the originated markets
        best = None
        order = {"match_winner": 0, "handicap": 1, "total": 2}
        for key, mk in markets.items():
            if not isinstance(mk, dict) or "selections" not in mk:
                continue
            for s in mk["selections"]:
                am = s["fair_american"]
                if not (-250 <= am <= 10000):
                    continue
                k = (s["fair_prob"], -order.get(key, 9))
                if best is None or k > best[0]:
                    best = (k, mk["market_name"], s)
        if best is None:
            continue
        _, mk_name, s = best
        finish_pick(row, mk_name, s["label"], s["fair_prob"], gate_ok)
        published += 1
    flag("BW-F-RU-13", "info", "Rugby Union",
         f"TOP 14 Journée {rnd}: {published} fixture(s) originated from the official LNR table + calendar",
         f"Model: independent Poisson on points scored with league mean {league_mean:.2f}, home factor "
         f"{HFA}, attack/defence from the official table; two-way win probability excludes draw mass; "
         f"handicap ladder and total line derived from the same joint distribution. Team news and "
         f"injury reports were not published in the captured official pages and are therefore not claimed.",
         url_c, manual_url=url_t)

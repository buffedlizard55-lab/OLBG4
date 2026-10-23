#!/usr/bin/env python3
"""Board AJ — handball origination from the two official tables that are readable today.

Readable: Liga ASOBAL (16 clubs, Spanish top division) and the Danish Betoro Herreligaen
(13 clubs). Both publish played / won / drawn / lost / goals for / goals against, so a
goal-based point model can be fitted exactly as for the other goal sports.

Not readable (each recorded in data/session-2722b692/desk.json -> unpriced): the German HBL
table endpoint answers with an empty Angular shell, the French LNH calendar is a 404, the EHF
Champions League endpoints are 404/403, and no official per-team feed exists in this snapshot
for the women's internationals.

Kick-off times for the ASOBAL and Danish fixtures come from the OLBG market listing (the brief
takes the fixture list from OLBG); the strength inputs come only from the official tables, and
the row records that provenance split explicitly.
"""
from __future__ import annotations

import math
import re

CONST = {
    "asobal_home_edge": 1.6,     # goals; Spanish top division home scoring edge
    "den_home_edge": 1.5,
    "margin_sd": 8.2,            # standard deviation of the goal margin
    "shrink_k": 5,
}


def _cells(row_html: str) -> list[str]:
    cells = [re.sub(r"<[^>]+>", "", c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)]
    return [c.strip() for c in cells if c.strip()]


def asobal_table(cap) -> dict:
    raw = cap.raw("asobal_table")
    if not raw:
        return {}
    html = raw.decode("iso-8859-1", "replace")
    table = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = _cells(row)
        if len(cells) < 9 or not cells[0].isdigit():
            continue
        name = cells[1].strip()
        try:
            played, w, d, l, gf, gc = (int(cells[i]) for i in (3, 4, 5, 6, 7, 8))
        except (ValueError, IndexError):
            continue
        table[name] = {"name": name, "played": played, "w": w, "d": d, "l": l,
                       "gf": gf, "gc": gc, "pts": int(cells[2]), "competition": "Liga ASOBAL",
                       "source": cap.url("asobal_table"), "source_sha256": cap.sha("asobal_table")}
    return table


def danish_table(cap) -> dict:
    raw = cap.raw("dk_liga_table")
    if not raw:
        return {}
    html = raw.decode("utf-8", "replace")
    table = {}
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = _cells(row)
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        goals = re.match(r"(\d+)\D+(\d+)", cells[6])
        if not goals:
            continue
        try:
            played, w, d, l = (int(cells[i]) for i in (2, 3, 4, 5))
            pts = int(cells[7])
        except (ValueError, IndexError):
            continue
        table[cells[1]] = {"name": cells[1], "played": played, "w": w, "d": d, "l": l,
                           "gf": int(goals.group(1)), "gc": int(goals.group(2)), "pts": pts,
                           "competition": "Betoro Herreligaen",
                           "source": cap.url("dk_liga_table"), "source_sha256": cap.sha("dk_liga_table")}
    return table


def _tokens(name: str) -> list[str]:
    return [w for w in re.split(r"[^0-9a-zà-ÿ]+", name.lower()) if len(w) > 2]


def resolve(name: str, table: dict) -> tuple[dict | None, float]:
    best, best_score = None, 0.0
    ntok = _tokens(name)
    for key, row in table.items():
        ktok = _tokens(key)
        shared = [t for t in ntok if t in ktok]
        score = len(shared) + 0.5 * sum(1 for t in shared if len(t) >= 6)
        if score > best_score:
            best, best_score = row, score
    return (best, best_score) if best_score >= 1.0 else (None, best_score)


def build(cap, events: list[dict]) -> tuple[list[dict], dict, list[dict]]:
    """Price every OLBG handball fixture whose two clubs are both in a readable official table."""
    tables = [("at_a", asobal_table(cap), "Liga ASOBAL", CONST["asobal_home_edge"]),
              ("dk_a", danish_table(cap), "Betoro Herreligaen", CONST["den_home_edge"])]
    rows, unpriced = [], []
    for ev in events:
        if " vs " not in ev["event"]:
            unpriced.append({**{k: ev.get(k) for k in ("start_utc", "event")},
                             "sport": "Handball", "source_url": ev.get("hub_url", ""),
                             "reason": "market listing is not a two-team fixture"})
            continue
        home_raw, away_raw = [p.strip() for p in ev["event"].split(" vs ", 1)]
        choice = None
        for tid, table, label, edge in tables:
            if not table:
                continue
            h, hs = resolve(home_raw, table)
            a, as_ = resolve(away_raw, table)
            if h and a and h["played"] >= 4 and a["played"] >= 4:
                choice = (tid, table, label, edge, h, a, hs, as_)
                break
        if not choice:
            resolved_any = False
            for tid, table, label, edge in tables:
                if table and (resolve(home_raw, table)[0] or resolve(away_raw, table)[0]):
                    resolved_any = True
            unpriced.append({
                "sport": "Handball", "competition": "", "start_utc": ev["start_utc"],
                "home": home_raw, "away": away_raw, "source_url": ev.get("hub_url", ""),
                "reason": ("one or both clubs are absent from the readable official tables "
                           "(ASOBAL 16 clubs, Danish Herreligaen 13 clubs)" if resolved_any else
                           "competition has no readable official results/standings feed in this "
                           "snapshot (HBL shell, LNH 404, EHF 404/403, no women's international feed)"),
                "olbg_event": ev["event"]})
            continue
        tid, table, label, edge, h, a, hs, as_ = choice
        played_rows = [t for t in table.values() if t["played"]]
        lg = sum(t["gf"] / t["played"] for t in played_rows) / len(played_rows)
        k = CONST["shrink_k"]
        def rate(row, key):
            per = row[key] / max(row["played"], 1)
            return (per * row["played"] + lg * k) / (row["played"] + k)
        mu_h = lg * (rate(h, "gf") / lg) * (rate(a, "gc") / lg) * (1 + edge / (2 * lg)) + edge / 2
        mu_a = lg * (rate(a, "gf") / lg) * (rate(h, "gc") / lg) * (1 - edge / (2 * lg)) - edge / 2
        mu_h, mu_a = max(mu_h, lg * 0.55), max(mu_a, lg * 0.55)
        margin, total = mu_h - mu_a, mu_h + mu_a
        sd = CONST["margin_sd"]
        p_home = 1 - 0.5 * (1 + math.erf(((0.5 - margin) / sd) / math.sqrt(2)))
        p_draw = (0.5 * (1 + math.erf(((0.5 - margin) / sd) / math.sqrt(2)))
                  - 0.5 * (1 + math.erf(((-0.5 - margin) / sd) / math.sqrt(2))))
        p_away = 0.5 * (1 + math.erf(((-0.5 - margin) / sd) / math.sqrt(2)))
        p_home_dnb = p_home / (p_home + p_away) if (p_home + p_away) else 0.5
        markets = []
        for sel, p in ((h["name"], p_home), ("Draw", p_draw), (a["name"], p_away)):
            markets.append({"market": "Match Winner (3-way)", "selection": sel, "line": "",
                            "probability": round(p, 4)})
        markets.append({"market": "Draw No Bet", "selection": h["name"], "line": "",
                        "probability": round(p_home_dnb, 4)})
        markets.append({"market": "Draw No Bet", "selection": a["name"], "line": "",
                        "probability": round(1 - p_home_dnb, 4)})
        for line in (-9.5, -6.5, -3.5, -1.5, 1.5, 3.5, 6.5, 9.5):
            # home covers line L when margin > -L
            ph = 1 - 0.5 * (1 + math.erf(((-line - margin) / sd) / math.sqrt(2)))
            markets.append({"market": "Handicap", "selection": f"{h['name']} {line:+.1f}",
                            "line": f"{line:+.1f}", "probability": round(ph, 4)})
            markets.append({"market": "Handicap", "selection": f"{a['name']} {-line:+.1f}",
                            "line": f"{-line:+.1f}", "probability": round(1 - ph, 4)})
        for line in (round(total) - 1.5, round(total) + 1.5):
            p_over = 1 - 0.5 * (1 + math.erf(((line - total) / CONST["margin_sd"]) / math.sqrt(2)))
            markets.append({"market": "Total Goals", "selection": f"Over {line}", "line": f"{line}",
                            "probability": round(p_over, 4)})
            markets.append({"market": "Total Goals", "selection": f"Under {line}", "line": f"{line}",
                            "probability": round(1 - p_over, 4)})
        for m in markets:
            m["fair_decimal"] = round(1 / m["probability"], 3) if m["probability"] else ""
            p = m["probability"]
            m["fair_american"] = (f"-{round(100 * p / (1 - p))}" if p > 0.5 else f"+{round(100 * (1 - p) / p)}")
            m["in_window"] = bool(m["fair_american"].startswith("-")) and int(m["fair_american"]) >= -250
        rows.append({
            "fixture": {
                "competition": label, "start_utc": ev["start_utc"],
                "home": h["name"], "away": a["name"], "venue": "",
                "source_url": h["source"], "source_id": ev.get("event", ""),
                "inputs": {
                    "model": "handball_goal_normal", "table": tid,
                    "home_record": h, "away_record": a,
                    "listed_event": ev["event"], "listed_hub": ev.get("hub_url", ""),
                    "time_source": "OLBG market listing (official fixture list not readable)",
                    "name_resolution": {"listed_home": home_raw, "listed_away": away_raw,
                                        "table_home": h["name"], "table_away": a["name"],
                                        "score_home": hs, "score_away": as_},
                },
                "tags": ["league"],
            },
            "markets": markets,
            "model": {"family": "goal_normal", "expected_margin": round(margin, 2),
                      "expected_total": round(total, 2), "mu_home": round(mu_h, 2),
                      "mu_away": round(mu_a, 2), "margin_sd": sd,
                      "league_goals_prior": round(lg, 2),
                      "inputs_used": ["goals for/against per game from the official table",
                                      "played/won/drawn/lost record"],
                      "notes": ["kick-off time comes from the OLBG listing, not from an official "
                                "fixture list"],
                      "caps": (["sample<5 matches"] if min(h["played"], a["played"]) < 5 else [])},
        })
    diag = {"asobal_teams": len(tables[0][1]), "danish_teams": len(tables[1][1]),
            "olbg_events": len(events)}
    return rows, diag, unpriced

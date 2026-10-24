#!/usr/bin/env python3
"""Board CA — price OLBG-listed fixtures from official league tables.

Why this exists
---------------
OLBG's own hubs are the record of which matches a reader can actually bet on, and
at capture time that list is dominated by handball and volleyball, whose governing
bodies publish a table but *not* a machine-readable fixture list.  This module does
not invent those fixtures: it takes the fixture identity from OLBG's listing (the
row keeps OLBG's event URL) and takes team strength only from the official league
table we captured.  A fixture is priced only when *both* participants are found in
that table by name; otherwise the row stays blank and carries a specific flag.

Nothing here reads a bookmaker price.  OLBG's own odds are recorded on the row as a
cross-reference and are never an input to our number.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse as P  # noqa: E402

MIN_GAMES_FOR_FULL_CONF = 6
HOME_EDGE_HANDBALL = 1.025
HOME_EDGE_VOLLEY = 0.030


def american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    return int(round(-100.0 / (dec - 1.0)))


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower()
    s = re.sub(r"\(.*?\)", " ", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    drop = {
        "w", "women", "men", "bm", "cb", "hc", "sc", "sg", "tv", "club", "team", "the",
        "volley", "volleys", "volleyball", "handball", "håndbold", "hb", "hsg", "mt", "tsv",
        "vfl", "sv", "asv", "if", "fk", "bc", "ac", "ss", "us", "cd", "ca", "bidasoa",
    }
    toks = [t for t in s.split() if t and t not in drop]
    return " ".join(toks)


def match_score(a: str, b: str) -> float:
    """Token-containment score in [0,1]; deliberately conservative."""
    na, nb = norm(a), norm(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    ta, tb = na.split(), nb.split()
    if na in nb or nb in na:
        return 0.92 if min(len(ta), len(tb)) >= 1 else 0.0
    common = set(ta) & set(tb)
    if not common:
        return 0.0
    return len(common) / max(len(ta), len(tb)) * 0.9


def best_match(name: str, table: dict, threshold: float = 0.72):
    best, score = None, 0.0
    for cand in table:
        s = match_score(name, cand)
        if s > score:
            best, score = cand, s
    return (best, score) if score >= threshold else (None, score)


# ------------------------------------------------------------------ table readers
def _cells(row_html: str):
    out = []
    for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S):
        c = re.sub(r"<br\s*/?>", " ", c)
        c = re.sub(r"<[^>]+>", "", c)
        c = c.replace("&nbsp;", " ").replace("\n", " ").replace("\t", " ")
        out.append(re.sub(r"\s+", " ", c).strip())
    return out


def _int(s: str):
    m = re.search(r"-?\d+", s or "")
    return int(m.group()) if m else None


def read_dk_herreligaen(cap: P.Capture) -> dict:
    """Danish Herreligaen: # Klub K V U T Mål Point."""
    if not cap.exists("dk_herreligaen"):
        return {}
    table = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", cap.text("dk_herreligaen"), re.S):
        c = _cells(r)
        if len(c) < 8 or not c[0].isdigit():
            continue
        goals = re.match(r"(\d+)\s*-\s*(\d+)", c[6] or "")
        if not goals:
            continue
        table[c[1]] = {
            "played": _int(c[2]), "won": _int(c[3]), "drawn": _int(c[4]), "lost": _int(c[5]),
            "gf": int(goals.group(1)), "ga": int(goals.group(2)), "points": _int(c[7]),
            "source": cap.url("dk_herreligaen"),
            "competition": "Danish Herreligaen",
        }
    return table


def read_generic_goal_table(cap: P.Capture, tid: str, competition: str, header_hint: str) -> dict:
    """German HBL / Spanish ASOBAL style table: find goals-for/against by pattern."""
    if not cap.exists(tid):
        return {}
    table = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", cap.text(tid), re.S):
        c = _cells(r)
        if len(c) < 5:
            continue
        name = c[1] if c[0].isdigit() and len(c) > 1 else c[0]
        nums = [x for x in c if re.fullmatch(r"\d+", x or "")]
        gpair = next((x for x in c if re.fullmatch(r"\d+\s*[:/-]\s*\d+", x or "")), None)
        if not gpair:
            continue
        gf, ga = re.split(r"\s*[:/-]\s*", gpair)
        played = _int(nums[0]) if nums else None
        if not played or not name.strip():
            continue
        table[name.strip()] = {
            "played": played, "won": _int(nums[1]) if len(nums) > 1 else None,
            "drawn": _int(nums[2]) if len(nums) > 2 else None,
            "lost": _int(nums[3]) if len(nums) > 3 else None,
            "gf": int(gf), "ga": int(ga),
            "points": _int(nums[-1]) if nums else None,
            "source": cap.url(tid), "competition": competition,
        }
    return table


def read_legavolley(cap: P.Capture) -> dict:
    """Italian SuperLega: Punti, Partite, Vinte, Perse, set scores."""
    if not cap.exists("legavolley_classifica"):
        return {}
    table = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", cap.text("legavolley_classifica"), re.S):
        c = _cells(r)
        if len(c) < 8:
            continue
        name = re.sub(r"^[\s\d]+", "", c[0] or "").strip()
        if not name or name.lower().startswith(("classifica", "giocate")):
            continue
        nums = [_int(x) for x in c[1:]]
        if not nums or nums[0] is None:
            continue
        pts, played, won, lost = nums[0], nums[1], nums[2], nums[3]
        if not played:
            continue
        table[name] = {
            "played": played, "won": won, "lost": lost, "drawn": 0,
            "points": pts, "gf": won, "ga": lost,
            "source": cap.url("legavolley_classifica"),
            "competition": "Italian SuperLega",
        }
    return table


def read_plusliga(cap: P.Capture) -> dict:
    if not cap.exists("plusliga_table"):
        return {}
    table = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", cap.text("plusliga_table"), re.S):
        c = _cells(r)
        if len(c) < 6:
            continue
        name = next((x for x in c if x and not re.fullmatch(r"[\d\s|.%-]+", x)), "")
        nums = [_int(x) for x in c if re.fullmatch(r"\d+", x or "")]
        if not name or len(nums) < 4:
            continue
        table[name] = {
            "played": nums[1], "won": nums[2], "lost": nums[3], "drawn": 0,
            "points": nums[0], "gf": nums[2], "ga": nums[3],
            "source": cap.url("plusliga_table"), "competition": "Polish PlusLiga",
        }
    return table


def read_cvf(cap: P.Capture) -> dict:
    if not cap.exists("cvf_extraliga"):
        return {}
    table = {}
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", cap.text("cvf_extraliga"), re.S):
        c = _cells(r)
        if len(c) < 6:
            continue
        name = next((x for x in c if x and not re.fullmatch(r"[\d\s|.%-]+", x)), "")
        nums = [_int(x) for x in c if re.fullmatch(r"\d+", x or "")]
        if not name or len(nums) < 4:
            continue
        table[name] = {
            "played": nums[1], "won": nums[2], "lost": nums[3], "drawn": 0,
            "points": nums[0], "gf": nums[2], "ga": nums[3],
            "source": cap.url("cvf_extraliga"), "competition": "Czech Extraliga",
        }
    return table


# ------------------------------------------------------------------ the models
def poisson_grid(lh: float, la: float, maxg: int = 45):
    ph = [math.exp(-lh) * lh ** k / math.factorial(k) for k in range(maxg)]
    pa = [math.exp(-la) * la ** k / math.factorial(k) for k in range(maxg)]
    win = draw = 0.0
    total = {}
    for i, a in enumerate(ph):
        for j, b in enumerate(pa):
            pr = a * b
            if i > j:
                win += pr
            elif i == j:
                draw += pr
            total[i + j] = total.get(i + j, 0.0) + pr
    return win, draw, 1 - win - draw, total


def handball_line(table: dict, home: str, away: str) -> dict | None:
    th, ta = table[home], table[away]
    if not th["played"] or not ta["played"]:
        return None
    lg = sum(t["gf"] + t["ga"] for t in table.values()) / max(1, sum(2 * t["played"] for t in table.values()))
    def shrink_ratio(x: float, played: int) -> float:
        """Pull a small-sample rate toward the league mean (1.0) by played/(played+8)."""
        w = played / (played + 8.0)
        return 1.0 + w * (x - 1.0)

    att_h = shrink_ratio((th["gf"] / th["played"]) / lg, th["played"])
    def_h = shrink_ratio((th["ga"] / th["played"]) / lg, th["played"])
    att_a = shrink_ratio((ta["gf"] / ta["played"]) / lg, ta["played"])
    def_a = shrink_ratio((ta["ga"] / ta["played"]) / lg, ta["played"])
    lam_h = lg * att_h * def_a * HOME_EDGE_HANDBALL
    lam_a = lg * att_a * def_h
    win, draw, loss, total = poisson_grid(max(lam_h, 0.4), max(lam_a, 0.4))
    return {"lam_h": lam_h, "lam_a": lam_a, "win": win, "draw": draw, "loss": loss,
            "total": total, "league_avg": lg}


def volley_line(table: dict, home: str, away: str) -> dict | None:
    th, ta = table[home], table[away]
    if not th["played"] or not ta["played"]:
        return None

    def rate(t):
        return (t["won"] - t["lost"]) / t["played"] if t["played"] else 0.0

    raw = rate(th) - rate(ta)
    # small samples carry almost no signal: weight the gap by played/(played+8)
    weight = min(th["played"], ta["played"]) / (min(th["played"], ta["played"]) + 8.0)
    diff = raw * weight + HOME_EDGE_VOLLEY
    p_set = 1 / (1 + math.exp(-1.6 * diff))
    p_set = min(max(p_set, 0.30), 0.70)
    # best of five: win three sets
    p_match = sum(math.comb(2 + j, j) * p_set ** 3 * (1 - p_set) ** j for j in range(3))
    p_match = min(max(p_match, 0.15), 0.85)
    return {"p_set": p_set, "win": p_match, "loss": 1 - p_match}


def confidence(p: float, table: dict, home: str, away: str) -> str:
    games = min(table[home]["played"], table[away]["played"])
    if games < MIN_GAMES_FOR_FULL_CONF:
        return "Low" if p < 0.62 else "Medium"
    if p >= 0.70:
        return "High"
    if p >= 0.55:
        return "Medium"
    return "Low"


def market2(name, line, a_label, b_label, pa, pb, note=""):
    pa = min(max(pa, 0.005), 0.995)
    tot = pa + pb
    pa, pb = pa / tot, pb / tot
    legs = []
    for lbl, p in ((a_label, pa), (b_label, pb)):
        p = round(p, 4)
        dec = round(1.0 / p, 2)
        legs.append({"label": lbl, "fair_prob": p, "fair_decimal": dec,
                     "fair_american": american(dec), "implied_prob_sum": 1.0})
    return {"market_name": name, "line": line, "note": note, "selections": legs}


def market3(name, line, legs, note=""):
    ps = [min(max(p, 0.005), 0.995) for _, p in legs]
    tot = sum(ps)
    out = []
    for (lbl, _), p in zip(legs, ps):
        p = round(p / tot, 4)
        dec = round(1.0 / p, 2)
        out.append({"label": lbl, "fair_prob": p, "fair_decimal": dec,
                    "fair_american": american(dec), "implied_prob_sum": round(tot, 4)})
    return {"market_name": name, "line": line, "note": note, "selections": out}


def build_tables(cap: P.Capture) -> dict:
    return {
        "handball_dk": read_dk_herreligaen(cap),
        "handball_de": read_generic_goal_table(cap, "hbl_tabelle", "German HBL (Daikin)", "hbl"),
        "handball_es": read_generic_goal_table(cap, "asobal_clasificacion", "Spanish ASOBAL", "asobal"),
        "volley_it": read_legavolley(cap),
        "volley_pl": read_plusliga(cap),
        "volley_cz": read_cvf(cap),
    }


def price_row(row: dict, tables: dict) -> dict:
    sport = row["sport"]
    if row.get("pick"):
        return row
    if sport not in ("Handball", "Volleyball"):
        return row
    a, b = row.get("side_a", ""), row.get("side_b", "")
    if not b and a:
        # OLBG-listed rows carry the whole event name in side_a ("Trentino vs Cisterna")
        parts = re.split(r"\s+(?:vs\.?|v)\s+", a, maxsplit=1, flags=re.I)
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            row["side_a"], row["side_b"] = a, b
    if not a or not b:
        return row

    order = (["handball_dk", "handball_de", "handball_es"] if sport == "Handball"
             else ["volley_it", "volley_pl", "volley_cz"])
    MIN_PLAYED = 2
    tried = []
    for key in order:
        table = tables.get(key) or {}
        if not table:
            continue
        h, sh = best_match(a, table)
        w, sw = best_match(b, table)
        tried.append(f"{key}:{sh:.2f}/{sw:.2f}")
        if not h or not w or h == w:
            continue
        if min(table[h]["played"], table[w]["played"]) < MIN_PLAYED:
            row.setdefault("flags", []).append(
                f"official table shows fewer than {MIN_PLAYED} matches played for one side - season sample too small to price")
            continue
        if sport == "Handball":
            m = handball_line(table, h, w)
            if not m:
                continue
            ph = m["win"] + 0.5 * m["draw"]
            row["markets"] = {
                "match_winner": market3(
                    "Match Winner (1X2)", None,
                    [(f"{a} (home)", m["win"]), ("Draw", m["draw"]), (f"{b} (away)", m["loss"])],
                ),
                "handicap": market2("Handicap -2.5", -2.5, f"{a} -2.5", f"{b} +2.5",
                                    # crude split of the draw around the line
                                    min(0.95, max(0.05, m["win"] + m["draw"] * 0.25)),
                                    min(0.95, max(0.05, m["loss"] + m["draw"] * 0.75))),
            }
            line = round(m["league_avg"] * 2)
            over = sum(p for t, p in m["total"].items() if t > line)
            under = sum(p for t, p in m["total"].items() if t <= line)
            row["markets"]["total"] = market2("Total Goals O/U", line, f"Over {line}", f"Under {line}",
                                              over, under)
            row["evidence"] = {
                "home_played": table[h]["played"], "home_gf": table[h]["gf"], "home_ga": table[h]["ga"],
                "away_played": table[w]["played"], "away_gf": table[w]["gf"], "away_ga": table[w]["ga"],
                "league_goals_per_game": round(m["league_avg"], 3),
                "expected_goals_home": round(m["lam_h"], 2), "expected_goals_away": round(m["lam_a"], 2),
                "table_source": table[h]["source"],
            }
            row["form"] = {
                h: f"{table[h]['won']}-{table[h]['drawn']}-{table[h]['lost']} ({table[h]['points']} pts, "
                   f"{table[h]['gf']}:{table[h]['ga']})",
                w: f"{table[w]['won']}-{table[w]['drawn']}-{table[w]['lost']} ({table[w]['points']} pts, "
                   f"{table[w]['gf']}:{table[w]['ga']})",
            }
            row["model"] = {"name": "poisson on official league goal rates", "league": table[h]["competition"]}
            row["sample"] = f"{min(table[h]['played'], table[w]['played'])} league matches per side"
        else:
            m = volley_line(table, h, w)
            if not m:
                continue
            ph = m["win"]
            row["markets"] = {
                "match_winner": market2("Match Winner", None, f"{a} (home)", f"{b} (away)",
                                        m["win"], m["loss"]),
                "handicap": market2("Set Handicap -1.5", -1.5, f"{a} -1.5", f"{b} +1.5",
                                    min(0.95, max(0.05, m["win"] * 0.82)),
                                    min(0.95, max(0.05, 1 - m["win"] * 0.82))),
            }
            row["evidence"] = {
                "home_played": table[h]["played"], "home_won": table[h]["won"], "home_lost": table[h]["lost"],
                "away_played": table[w]["played"], "away_won": table[w]["won"], "away_lost": table[w]["lost"],
                "table_source": table[h]["source"],
            }
            row["form"] = {
                h: f"{table[h]['won']}-{table[h]['lost']} ({table[h]['points']} pts)",
                w: f"{table[w]['won']}-{table[w]['lost']} ({table[w]['points']} pts)",
            }
            row["model"] = {"name": "best-of-five from official win-rate gap", "league": table[h]["competition"]}
            row["sample"] = f"{min(table[h]['played'], table[w]['played'])} league matches per side"

        three_way = len(row["markets"]["match_winner"]["selections"]) == 3
        if sport == "Handball":
            best_p = max(m["win"], m["loss"])
            side = 0 if m["win"] >= m["loss"] else 2
        else:
            best_p = max(ph, 1 - ph)
            side = 0 if ph >= 0.5 else 1
        sel = row["markets"]["match_winner"]["selections"][side]
        if sel["fair_prob"] < 0.5:
            # never publish a "pick" that is not the favoured side
            row["flags"] = row.get("flags") or []
            row["flags"].append("market split too evenly to nominate a favoured side")
            return row
        row["pick"] = {
            "market": row["markets"]["match_winner"]["market_name"], "market_key": "match_winner",
            "selection": sel["label"], "fair_prob": sel["fair_prob"], "fair_decimal": sel["fair_decimal"],
            "fair_american": sel["fair_american"], "confidence": confidence(best_p, table, h, w),
            "in_window": -250 <= sel["fair_american"] <= 10000,
            "rule": "official league table; sample-capped confidence",
        }
        row["competition"] = row.get("competition") or table[h]["competition"]
        if table[h]["competition"] not in (row.get("competition") or ""):
            row["competition"] = table[h]["competition"]
        row["flags"] = [f for f in (row.get("flags") or [])
                        if "no official fixture" not in f and "OLBG listing only" not in f]
        row["flags"].append("fixture identity from the OLBG listing; strength inputs from the official table")
        row["official_url"] = table[h]["source"]
        row["official_source_name"] = f"Official {table[h]['competition']} table"
        return row

    row.setdefault("flags", [])
    if not any("no participant found" in f for f in row["flags"]):
        row["flags"].append("participants not found in the official tables captured - left unpriced")
    return row


def main() -> int:
    cap_dir, desk_path, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    cap = P.Capture(cap_dir)
    tables = build_tables(cap)
    for k, v in tables.items():
        print(f"table {k:14s} {len(v):3d} teams")
    doc = json.load(open(desk_path, encoding="utf-8"))
    before = sum(1 for r in doc["rows"] if r.get("pick"))
    priced_by_sport = {}
    for r in doc["rows"]:
        price_row(r, tables)
        if r.get("pick") and r["sport"] in ("Handball", "Volleyball"):
            priced_by_sport[r["sport"]] = priced_by_sport.get(r["sport"], 0) + 1
    after = sum(1 for r in doc["rows"] if r.get("pick"))
    doc["augmented"] = {
        "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tables": {k: len(v) for k, v in tables.items()},
        "priced_before": before, "priced_after": after,
        "newly_priced": priced_by_sport,
    }
    json.dump(doc, open(out_path, "w", encoding="utf-8"), indent=1, sort_keys=True)
    print(f"priced {before} -> {after} rows; newly priced {priced_by_sport}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Originate our own prices for every verified fixture.

inputs : data/integrated/inputs.json   (transcribed from official sources only)
output : data/integrated/entries.json  (line, pick, confidence, market status)

Nothing here reads a bookmaker price. Every number is produced by the formulas below
from fields transcribed in inputs.json; every constant that is not derived from a
verified field is declared as MODEL ASSUMPTION and is published on the Flagged page.

Strength of a side:
  NHL    points% = (2*W + OTL) / (2 * GP)                       (GP = W+L+OTL)
  NBA    win%    = (W + 5) / (GP + 10)                          (5/10 shrink, early season)
  RU     win%    = (wins + 3) / (n + 6)                         (form string, 3/6 shrink)
  MLB / EHF / Snooker: no verified strength field -> no strength input at all.

Home win probability:
  p = clamp(0.5 + 0.9 * (S_home - S_away) + H, 0.05, 0.95)      H = home edge per sport
  With no strength input, p = 0.5 + H (i.e. only the venue prior is used).

Prices (our line):  price = 1 / (p * 1.02)   -> two-way margin 4.0% (MODEL ASSUMPTION)
Handicap:           margin_hat = 2 * (p - 0.5) * M_sport, snapped to a half line
                    cover price from a Normal(margin_hat, sigma)
Total:              line = declared sport constant (MODEL ASSUMPTION); 1.92 / 1.92
Confidence:         high   if |p-0.5| >= 0.18 and both sides have >= 8 verified games
                    medium if |p-0.5| >= 0.09 and both sides have >= 3 verified games
                    low    otherwise (always low when a strength input is missing)
Pick:               the side with the higher p; withheld when p == 0.5 exactly and the
                    sport has no strength input, because then nothing distinguishes the sides.
"""
import json, math, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[2]
INP = ROOT / "data" / "integrated" / "inputs.json"
OUT = ROOT / "data" / "integrated" / "entries.json"

MARGIN = 1.02
K = 0.9
HOME_EDGE = {"Ice Hockey": 0.055, "Basketball": 0.060, "Baseball": 0.020,
             "Rugby Union": 0.070, "Handball": 0.050, "Snooker": 0.0}
MAX_MARGIN = {"Ice Hockey": 2.2, "Basketball": 18.0, "Baseball": 2.6,
              "Rugby Union": 20.0, "Handball": 12.0, "Snooker": 0.0}
SIGMA = {"Ice Hockey": 1.8, "Basketball": 12.0, "Baseball": 3.6,
         "Rugby Union": 12.0, "Handball": 8.0}
TOTAL_LINE = {"Ice Hockey": (6.0, "goals"), "Basketball": (226.5, "points"),
              "Baseball": (8.5, "runs"), "Rugby Union": (44.5, "points"),
              "Handball": (57.5, "goals"), "Snooker": (None, "frames")}
TOTAL_BASIS = ("MODEL ASSUMPTION: league-neutral line constant. No team scoring, pace or "
               "run-prevention figure was verified for this fixture, so the line is a declared "
               "constant and both sides are priced symmetrically at 1.92 - we claim no edge.")

def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

def hockey_points(rec):
    m = re.fullmatch(r"(\d+)-(\d+)-(\d+)", rec.strip())
    if not m:
        return None, 0
    w, l, otl = map(int, m.groups())
    gp = w + l + otl
    return ((2 * w + otl) / (2 * gp) if gp else None), gp

def basketball_winpct(rec):
    m = re.fullmatch(r"(\d+)-(\d+)", rec.strip())
    if not m:
        return None, 0
    w, l = map(int, m.groups())
    gp = w + l
    return ((w + 5) / (gp + 10) if gp else None), gp

def rugby_winpct(form):
    toks = [t for t in form.replace("/", " ").split() if t in ("W", "L", "D")]
    if not toks:
        return None, 0
    wins = toks.count("W") + 0.5 * toks.count("D")
    return (wins + 3) / (len(toks) + 6), len(toks)

def strength(row, side):
    sport = row["sport"]
    if sport == "Ice Hockey":
        return hockey_points(row.get("hrec" if side == "home" else "arec", ""))
    if sport == "Basketball":
        return basketball_winpct(row.get("hrec" if side == "home" else "arec", ""))
    if sport == "Rugby Union":
        return rugby_winpct(row.get("hform" if side == "home" else "aform", ""))
    return None, 0

def price(p):
    return round(1.0 / (p * MARGIN), 2)

def build(row):
    sport = row["sport"]
    sh, nh = strength(row, "home")
    sa, na = strength(row, "away")
    has_strength = sh is not None and sa is not None
    p = 0.5 + HOME_EDGE[sport] + (K * (sh - sa) if has_strength else 0.0)
    p = min(0.95, max(0.05, p))
    p_away = 1.0 - p

    home, away = row["home"], row["away"]
    # ---- match winner market ----
    if has_strength or sport != "Snooker":
        if p >= p_away:
            pick, pick_market, pick_line = home, "Match winner (two-way)", price(p)
        else:
            pick, pick_market, pick_line = away, "Match winner (two-way)", price(p_away)
    else:
        pick, pick_market, pick_line = "", "", ""
    if abs(p - 0.5) < 0.02 and not has_strength:
        pick, pick_market, pick_line = "", "", ""   # nothing distinguishes the two sides

    # ---- handicap market ----
    handicap = None
    if sport in MAX_MARGIN and MAX_MARGIN[sport] > 0 and has_strength:
        mhat = 2.0 * (p - 0.5) * MAX_MARGIN[sport]
        line = round(abs(mhat) * 2) / 2 or 0.5
        fav_home = mhat >= 0
        # P(favourite wins by more than the half line)
        fav_p = 1.0 - norm_cdf((line - abs(mhat)) / SIGMA[sport])
        fav_p = min(0.92, max(0.08, fav_p))
        handicap = {
            "line": line,
            "favourite": home if fav_home else away,
            "underdog": away if fav_home else home,
            "fav_price": price(fav_p),
            "dog_price": price(1.0 - fav_p),
            "unit": {"Ice Hockey": "goals", "Basketball": "points", "Baseball": "runs",
                     "Rugby Union": "points", "Handball": "goals"}[sport],
            "basis": ("MODEL: expected margin = 2*(p-0.5)*max_margin, snapped to the nearest half "
                      "line; cover probability from a Normal with sigma=" + str(SIGMA[sport])),
            "status": "originated",
        }

    # ---- total market ----
    line, unit = TOTAL_LINE[sport]
    total = {
        "line": line, "unit": unit,
        "over_price": 1.92 if line else "", "under_price": 1.92 if line else "",
        "status": "originated (symmetric)" if line else "withheld: snooker totals are frames and "
                 "the verified page publishes no frame totals",
        "basis": TOTAL_BASIS if line else "",
    }

    # ---- confidence ----
    if not has_strength or min(nh, na) < 3:
        conf = "Low"
        reason = "no usable verified strength input" if not has_strength else f"small sample (home {nh}, away {na})"
    elif abs(p - 0.5) >= 0.18 and min(nh, na) >= 8:
        conf = "High"; reason = f"|p-0.5|={abs(p-0.5):.3f} with {nh}/{na} verified games"
    elif abs(p - 0.5) >= 0.09:
        conf = "Medium"; reason = f"|p-0.5|={abs(p-0.5):.3f}"
    else:
        conf = "Low"; reason = f"|p-0.5|={abs(p-0.5):.3f} - sides too close"

    return {
        "id": row["id"], "sport": sport, "competition": row["comp"], "date": row["date"],
        "time": row["time"], "time_note": row["tnote"], "venue": row["venue"],
        "home": home, "away": away, "home_record": row.get("hrec", ""), "away_record": row.get("arec", ""),
        "home_form": row.get("hform", ""), "away_form": row.get("aform", ""),
        "home_leaders": row.get("hlead", ""), "away_leaders": row.get("alead", ""),
        "neutral": row.get("neutral", False),
        "strength_home": None if sh is None else round(sh, 4),
        "strength_away": None if sa is None else round(sa, 4),
        "strength_basis": {
            "Ice Hockey": "points percentage = (2W+OTL)/(2*GP) from the NHL feed record",
            "Basketball": "win percentage shrunk (W+5)/(GP+10), NBA.com record",
            "Rugby Union": "recent-form win rate shrunk (wins+3)/(n+6), form string from the club fixture page",
        }.get(sport, "no verified strength field was available"),
        "model_prob_home": round(p, 4), "model_prob_away": round(p_away, 4),
        "our_price_home": price(p), "our_price_away": price(p_away),
        "pick": pick, "pick_market": pick_market, "pick_price": pick_line,
        "confidence": conf, "confidence_reason": reason,
        "markets": {
            "winner": {"status": "originated" if pick else "withheld: the two sides are level on every verified input",
                       "basis": "p = 0.5 + 0.9*(S_home - S_away) + home edge; price = 1/(p*1.02)"},
            "handicap": handicap or {"status": "withheld: no verified strength input to build a margin from", "line": ""},
            "total": total,
        },
        "source_url": row.get("url"), "source_id": row["src"], "evidence": row["ev"],
    }

def main():
    doc = json.loads(INP.read_text())
    sources = {s["id"]: s for s in doc["sources"]}
    rows, seen = [], set()
    for r in doc["rows"]:
        if r["id"] in seen:
            raise SystemExit(f"duplicate id {r['id']}")
        seen.add(r["id"])
        e = build(r)
        if not e["source_url"]:
            e["source_url"] = sources[r["src"]]["url"]
        e["source_name"] = sources[r["src"]]["page"]
        e["source_org"] = sources[r["src"]]["org"]
        e["retrieved_at"] = doc["retrieved_at"]
        rows.append(e)
    out = {"schema": "olbg4.integrated.entries/1", "generated_by": "scripts/session-83451f65/model.py",
           "retrieved_at": doc["retrieved_at"],
           "constants": {
               "margin_overround": "4.0% two-way (price = 1/(p*1.02))",
               "k_strength_weight": K,
               "home_edge": HOME_EDGE, "max_margin": MAX_MARGIN, "sigma": SIGMA,
               "total_lines": {k: v[0] for k, v in TOTAL_LINE.items()}},
           "counts": {}, "entries": rows}
    from collections import Counter
    out["counts"] = {
        "total": len(rows),
        "by_sport": dict(sorted(Counter(r["sport"] for r in rows).items())),
        "by_confidence": dict(Counter(r["confidence"] for r in rows)),
        "with_pick": sum(1 for r in rows if r["pick"]),
        "handicaps": sum(1 for r in rows if r["markets"]["handicap"].get("line")),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))
    for r in rows:
        if r["confidence"] == "High":
            print(f"  HIGH {r['id']:34s} {r['home']} vs {r['away']}  p={r['model_prob_home']:.3f}  pick={r['pick']}")

if __name__ == "__main__":
    main()

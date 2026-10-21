#!/usr/bin/env python3
"""Originate our own lines, picks and confidence labels from the OLBG inventory.

Method (all constants live in data/model_config.json, each with a basis string):

  1. consensus share   p_c = tips_for / tips_total            (printed by OLBG)
  2. our probability   p   = (n*p_c + k*0.5) / (n + k)        k = 2  (shrinkage)
  3. own price         1 / (p * (1 - margin))                 margin = 0.04
  4. own handicap      round(avg_margin * (2p - 1), 1)        avg_margin cited per sport
  5. own total         the sport's cited/assumed average total
  6. confidence        HIGH  p >= .75 and n >= 4
                       MEDIUM p >= .60 and n >= 2
                       LOW   everything else (including rows with no consensus)

Nothing is copied from a bookmaker. Where a sport has no published average the
constant is labelled MODEL ASSUMPTION and also written to data/flagged.json.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

inv = json.loads((DATA / "match_inventory.json").read_text())
cfg = json.loads((DATA / "model_config.json").read_text())

K = cfg["shrinkage_k"]
MARGIN = cfg["margin"]
ATT = cfg["handicap_attenuation"]
CONF = cfg["confidence"]


def price(p, margin=MARGIN):
    p = min(max(p, 0.01), 0.99)
    return round(1.0 / (p * (1 - margin)), 2)


def shrink(p_c, n):
    return (n * p_c + K * 0.5) / (n + K)


def market_type(market, selection):
    m = (market or "").lower()
    s = (selection or "").lower()
    if "total" in m or s.startswith("over") or s.startswith("under") or "total legs" in m:
        return "total"
    if "handicap" in m or "puck line" in m or "run line" in m or re.search(r"[+-]\d+\.\d", s):
        return "handicap"
    if "set betting" in m or "set score" in m or "1st set" in m:
        return "prop"
    return "winner"


def split_sides(match):
    if " vs " in match:
        a, b = match.split(" vs ", 1)
        return a.strip(), b.strip(), None
    if " @ " in match:
        away, home = match.split(" @ ", 1)
        return home.strip(), away.strip(), "@"
    return None, None, None


def norm(t):
    return re.sub(r"[^a-z0-9]", "", (t or "").lower())


def confidence(p, n):
    if p is None or n is None:
        return "low", "no consensus rendered by OLBG, so no model probability exists"
    if p >= CONF["high"]["min_p"] and n >= CONF["high"]["min_tips"]:
        return "high", f"p={p:.3f} >= {CONF['high']['min_p']} and {n} tips >= {CONF['high']['min_tips']}"
    if p >= CONF["medium"]["min_p"] and n >= CONF["medium"]["min_tips"]:
        return "medium", f"p={p:.3f} >= {CONF['medium']['min_p']} and {n} tips >= {CONF['medium']['min_tips']}"
    return "low", "below the medium floor (p < 0.60 or fewer than 2 tips)"


def three_way_split(p_sel, side_index, base):
    """side_index 0=home 1=away 2=draw; returns dict of outcome probabilities."""
    h, a, d = base["home"], base["away"], base["draw"]
    tot = h + a + d
    h, a, d = h / tot, a / tot, d / tot
    remaining = max(0.0, 1.0 - p_sel)
    keys = ["home", "away", "draw"]
    base_vals = {"home": h, "away": a, "draw": d}
    others = [k for i, k in enumerate(keys) if i != side_index]
    mass = base_vals[others[0]] + base_vals[others[1]]
    out = {keys[side_index]: p_sel}
    for k in others:
        out[k] = remaining * (base_vals[k] / mass) if mass > 0 else remaining / 2
    return out


rows = []
for m in inv["matches"]:
    s = cfg["sports"][m["sport"]]
    n = m.get("tips_total")
    tf = m.get("tips_for")
    p_c = (tf / n) if (n and tf is not None) else None
    p = shrink(p_c, n) if p_c is not None else None
    mtype = market_type(m["market"], m["selection"])
    conf, conf_reason = confidence(p, n)

    home, away, sep = split_sides(m["match"])
    p_win = None
    if p is not None:
        p_win = p if mtype == "winner" else 0.5 + (p - 0.5) * ATT

    # outright match winner
    outright = ""
    outright_prob = None
    outright_basis = ""
    sel_n = norm(m["selection"])
    if m["sport"] != "Greyhounds":
        if mtype == "winner" and home and away:
            if sel_n and (sel_n in norm(home) or norm(home) in sel_n):
                outright, outright_prob = home, p_win
            elif sel_n and (sel_n in norm(away) or norm(away) in sel_n):
                outright, outright_prob = away, p_win
            outright_basis = "highest model probability on the two-way winner market" if outright else ""
        elif mtype == "handicap" and home and away:
            mm = re.search(r"([+-])(\d+\.\d+)", m["selection"])
            if mm:
                tipped_underdog = mm.group(1) == "+"
                if sel_n and norm(home) in sel_n:
                    outright = away if tipped_underdog else home
                elif norm(away) in sel_n:
                    outright = home if tipped_underdog else away
                outright_prob = None
                outright_basis = ("read from the handicap direction (a '+' start implies the tipped side is the underdog); "
                                  "no independent probability is claimed")
        else:
            if home and away:
                outright = home if (p_win is not None and p_win >= 0.5) else away
                outright_prob = p_win if p_win is not None else None
                outright_basis = "direction only: a total/prop market does not separate the two sides, so no probability is claimed"
            if mtype == "total" and home and away:
                outright, outright_prob, outright_basis = "", None, "not applicable to a total market"
        if m["sport"] in ("Rugby Union", "Rugby League", "Handball") and mtype != "handicap":
            base = s["base_rates"]
            idx = 2 if m["selection"] == "Tie" else (0 if (home and norm(home) in sel_n) else 1)
            if p is None:
                probs = None
            else:
                probs = three_way_split(p, idx, base)
            rows_probs = probs
            if probs and home and away:
                best = max(probs.items(), key=lambda kv: kv[1])
                label = {"home": home, "away": away, "draw": "Draw"}[best[0]]
                if mtype == "winner":
                    outright, outright_prob = label, best[1]
                    outright_basis = "highest of our 3-way (home/draw/away) probabilities"

    # own handicap line
    hcap = None
    if s["supports_handicap"] and p is not None:
        margin_pts = s["avg_margin"]
        edge = (2 * p - 1) * ATT
        line = round(margin_pts * edge, 1)
        hcap = {"line": line if line >= 0 else line, "basis": s["margin_basis"], "for": m["selection"]}

    # own total line
    total = None
    if s["supports_total"] and s["avg_total"] is not None:
        pick_side = ""
        if mtype == "total":
            pick_side = "Over" if m["selection"].lower().startswith("over") else (
                "Under" if m["selection"].lower().startswith("under") else "")
        total = {"line": s["avg_total"], "unit": s["points_unit"], "basis": s["total_basis"], "pick": pick_side}

    rows.append({
        "id": m["id"],
        "sport": m["sport"],
        "competition": m.get("competition", ""),
        "match": m["match"],
        "home": home or "",
        "away": away or "",
        "neutral_venue": sep is None,
        "time_label": m["time_label"],
        "market": m["market"],
        "market_type": mtype,
        "selection": m["selection"],
        "tips_for": tf,
        "tips_total": n,
        "consensus_pct": m.get("pct"),
        "consensus_prob": None if p_c is None else round(p_c, 4),
        "our_prob": None if p is None else round(p, 4),
        "our_price": None if p is None else price(p),
        "opp_price": None if p is None else price(1 - p),
        "own_handicap": hcap,
        "own_total": total,
        "pick": m["selection"],
        "pick_market": m["market"],
        "confidence": conf,
        "confidence_reason": conf_reason,
        "outright_winner": outright,
        "outright_prob": None if outright_prob is None else round(outright_prob, 4),
        "outright_basis": outright_basis,
        "olbg_url": m["url"],
        "flag": m.get("flag", "")
    })

out = {
    "schema": "olbg4.board/1",
    "captured_at": inv["captured_at"],
    "generated_by": "scripts/build_model.py",
    "model_config": "data/model_config.json",
    "counts": {
        "matches": len(rows),
        "high": sum(1 for r in rows if r["confidence"] == "high"),
        "medium": sum(1 for r in rows if r["confidence"] == "medium"),
        "low": sum(1 for r in rows if r["confidence"] == "low"),
        "priced": sum(1 for r in rows if r["our_prob"] is not None),
    },
    "rows": rows,
}
(DATA / "board.json").write_text(json.dumps(out, indent=1) + "\n")

# flag every model assumption so it lands on the Flagged for Review page
flags = []
for sport, s in cfg["sports"].items():
    for key in ("total_basis", "margin_basis", "base_rates_basis"):
        basis = s.get(key, "")
        if "MODEL ASSUMPTION" in basis:
            flags.append({
                "type": "model_assumption",
                "sport": sport,
                "what": f"{sport}: {key}",
                "detail": basis,
                "source": "data/model_config.json",
            })
(DATA / "model_assumptions.json").write_text(json.dumps({"schema": "olbg4.assumptions/1", "flags": flags}, indent=1) + "\n")

print(json.dumps(out["counts"], indent=1))
for r in rows:
    if r["confidence"] == "high":
        print(r["id"], r["sport"], "|", r["match"], "|", r["pick"], "| p=", r["our_prob"])

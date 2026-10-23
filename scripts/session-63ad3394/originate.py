#!/usr/bin/env python3
"""Board AK — originate our own lines for every verified fixture.

Every number here is derived from the committed official payloads (see
``parse_official.py``); no bookmaker price, no OLBG price and no external model
output is read. The method is deliberately small and inspectable:

  strength      win_pct and scoring margin per game, straight off the official
                standings / per-game results (no shrinkage, no imputation).
  money line    p(home) = logistic(k1*(win_pct_h - win_pct_a)
                                   + k2*(margin_h - margin_a) + hfa)
  handicap      expected margin = 0.6*(margin_h - margin_a) + hfa_points;
                line snapped to the nearest half point; cover probability from a
                normal with the sport's margin sigma.
  totals        expected total = mean of the two cross-matchup scoring rates;
                line snapped to the nearest half point; over probability from a
                normal with the sport's total sigma.
  golf          outright win from a Plackett-Luce over strokes behind the leader
                (theta per remaining round) and a top-10 finish from a normal
                threshold against the 10th-placed total.
  Formula 1     constructors' win probability from the share of championship
                points in the official standings.

Fair odds are 1/p with no margin. Confidence is an evidence rule, not a feeling:
High needs p >= 0.70, at least five verified games for both sides and a fair
American price inside the brief's -250 ... +10,000 window; Medium needs
p >= 0.60 with at least three games; everything else is Low, and a market with
missing inputs is left unpriced rather than guessed.
"""
from __future__ import annotations

import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SPORT_CFG = {
    # k1 win_pct weight, k2 margin weight, hfa (logit), hfa_points, sigma_margin,
    # sigma_total, totals line step, min sample for High, min sample for any price
    "Ice Hockey":   dict(k1=2.2, k2=0.055, hfa=0.18, hfa_pts=0.18, sg_m=1.85, sg_t=1.90, step=0.5, hi_n=3, lo_n=3, shrink=8),
    "Basketball":   dict(k1=2.2, k2=0.015, hfa=0.22, hfa_pts=2.6, sg_m=11.5, sg_t=17.0, step=0.5, hi_n=3, lo_n=3, shrink=4),
    "Baseball":     dict(k1=3.6, k2=0.045, hfa=0.10, hfa_pts=0.10, sg_m=2.30, sg_t=4.30, step=0.5, hi_n=3, lo_n=3),
    "Rugby Union":  dict(k1=3.4, k2=0.010, hfa=0.14, hfa_pts=2.8, sg_m=13.0, sg_t=13.0, step=1.0, hi_n=3, lo_n=3, shrink=4),
    "Rugby League": dict(k1=3.0, k2=0.012, hfa=0.14, hfa_pts=3.0, sg_m=14.0, sg_t=14.0, step=1.0, hi_n=3, lo_n=1, shrink=2),
    "Volleyball":   dict(k1=3.4, k2=0.055, hfa=0.16, hfa_pts=0.09, sg_m=0.85, sg_t=0.85, step=0.5, hi_n=3, lo_n=1, shrink=2,
                        totals=False, pick_markets=("match_winner",)),
    "Darts":        dict(k1=3.0, k2=0.030, hfa=0.00, hfa_pts=0.0, sg_m=2.10, sg_t=2.40, step=2.0, hi_n=3, lo_n=1, totals=False, half_lines=True,
                        pick_markets=("match_winner",)),
    "Snooker":      dict(k1=2.8, k2=0.040, hfa=0.00, hfa_pts=0.0, sg_m=2.00, sg_t=2.20, step=2.0, hi_n=3, lo_n=1, totals=False, half_lines=True,
                        pick_markets=("match_winner",)),
    "Tennis":       dict(k1=4.0, k2=0.000, hfa=0.00, hfa_pts=0.0, sg_m=3.20, sg_t=3.40, step=0.5, hi_n=3, lo_n=3),
    "Cricket":      dict(k1=3.0, k2=0.030, hfa=0.10, hfa_pts=2.0, sg_m=18.0, sg_t=18.0, step=1.0, hi_n=5, lo_n=3),
    "Gaelic Sports": dict(k1=3.0, k2=0.030, hfa=0.12, hfa_pts=1.5, sg_m=5.0, sg_t=5.0, step=1.0, hi_n=3, lo_n=2),
}

WINDOW = (-250.0, 10000.0)


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def american(p: float) -> int | None:
    if p is None or p <= 0.0 or p >= 1.0:
        return None
    p = round(p, 4)  # price the rounded probability, so 0.49997 and 0.5. cannot disagree
    d = 1.0 / p
    if abs(d - 2.0) < 1e-9:
        return -100  # a coin flip is quoted at -100, never +100
    return int(round(-100.0 / (d - 1.0))) if d < 2.0 else int(round((d - 1.0) * 100.0))


def decimal(p: float) -> float | None:
    return round(1.0 / p, 3) if p and 0 < p < 1 else None


def snap(x: float, step: float) -> float:
    return round(x / step) * step


def in_window(am: int | None) -> bool:
    return am is not None and WINDOW[0] <= am <= WINDOW[1]


def market(label: str, p: float) -> dict:
    # a selection that rounds to zero probability still needs a printable price
    p = min(max(p, 1e-4), 1 - 1e-4)
    return {"label": label, "fair_prob": round(p, 4), "fair_decimal": decimal(p),
            "fair_american": american(p), "in_window": in_window(american(p))}


def two_way(name: str, line: float | None, a_label: str, b_label: str,
            p_a: float, p_b: float, note: str | None = None) -> dict:
    return {"market_name": name, "line": line, "selections": [market(a_label, p_a), market(b_label, p_b)],
            "prob_sum": round(p_a + p_b, 6), "note": note}


def team_markets(ev: dict) -> dict | None:
    cfg = SPORT_CFG.get(ev["sport"])
    form = ev.get("form")
    if not cfg or not form:
        return None
    a, b = form.get("a"), form.get("b")
    if not a or not b:
        return None
    wa, wb = a.get("win_pct"), b.get("win_pct")
    ma, mb = a.get("margin", 0.0) or 0.0, b.get("margin", 0.0) or 0.0
    if wa is None or wb is None:
        return None
    n_a, n_b = a.get("n", 0), b.get("n", 0)
    if n_a < cfg["lo_n"] or n_b < cfg["lo_n"]:
        return None
    # Small-sample shrinkage toward .500: a 4-0 start is not a 100% team.
    K = cfg.get("shrink", 6)

    def shrink(pct: float, n: int) -> float:
        return 0.5 + (pct - 0.5) * (n / (n + K))

    wa, wb = shrink(wa, n_a), shrink(wb, n_b)
    p_b = logistic(cfg["k1"] * (wb - wa) + cfg["k2"] * (mb - ma) + cfg["hfa"])
    p_a = 1.0 - p_b

    exp_margin = 0.6 * (mb - ma) + cfg["hfa_pts"]
    step = cfg["step"]
    if cfg.get("half_lines"):
        # leg/frame sports: whole-number lines can push, and a 0.5-leg line is not a
        # real handicap, so open at 1.5 and grow a full rung at a time
        import math as _m
        mag = max(1.5, _m.floor(abs(exp_margin)) + 1.5)
        primary = _m.copysign(mag, exp_margin or 1.0)
    else:
        primary = snap(exp_margin, step)

    markets = {"match_winner": two_way(
        "Match winner" if ev["sport"] not in ("Ice Hockey", "Baseball") else "Money line",
        None, f"{ev['side_a']} (away)", f"{ev['side_b']} (home)", p_a, p_b)}

    # Primary handicap at the fair line, plus a ladder used only to document the
    # alternate lines we looked at (the ladder never sets the published pick).
    p_home_cover = 1.0 - norm_cdf((primary - exp_margin) / cfg["sg_m"])
    markets["handicap"] = two_way("Handicap", primary, f"{ev['side_a']} {primary:+g}",
                                  f"{ev['side_b']} {-primary:+g}", 1.0 - p_home_cover, p_home_cover)
    ladder = {"market_name": "Handicap ladder", "line": primary, "selections": [], "prob_sum": None,
              "note": "Alternate rungs at +/-%g around the fair line; investigated, not selected." % step}
    for rung in (-2, -1, 1, 2):
        line = primary + rung * step
        pc = 1.0 - norm_cdf((line - exp_margin) / cfg["sg_m"])
        ladder["selections"].append(market(f"{ev['side_b']} {-line:+g}", pc))
        ladder["selections"].append(market(f"{ev['side_a']} {line:+g}", 1.0 - pc))
    markets["handicap_ladder"] = ladder

    pf_a, pa_a = a.get("pf_pg"), a.get("pa_pg")
    pf_b, pa_b = b.get("pf_pg"), b.get("pa_pg")
    if None not in (pf_a, pa_a, pf_b, pa_b) and cfg.get("totals", True):
        exp_total = (pf_a + pa_b) / 2 + (pf_b + pa_a) / 2
        base = snap(exp_total, step)
        if base <= exp_total:
            base += step
        p_over = 1.0 - norm_cdf((base - exp_total) / cfg["sg_t"])
        markets["total"] = two_way("Match total", base, f"Under {base:g}", f"Over {base:g}",
                                   1.0 - p_over, p_over)
        tot_lad = {"market_name": "Total ladder", "line": base, "selections": [], "prob_sum": None,
                   "note": "Expected total %.2f; alternate rungs investigated, not selected." % exp_total}
        for rung in (-1, 1, 2):
            line = base + rung * step
            po = 1.0 - norm_cdf((line - exp_total) / cfg["sg_t"])
            tot_lad["selections"].append(market(f"Over {line:g}", po))
            tot_lad["selections"].append(market(f"Under {line:g}", 1.0 - po))
        markets["total_ladder"] = tot_lad
        markets["_exp_total"] = round(exp_total, 3)
        markets["_base_total"] = base
    markets["_exp_margin"] = round(exp_margin, 3)
    return markets


def golf_markets(ev: dict) -> dict:
    out = ev["outright"]
    players = out["field"]
    if not players:
        return {}
    best = min(p["total"] for p in players)
    remaining = 2.0  # R3 and R4 remain after the captured R2 board
    theta = 2.35 * math.sqrt(remaining / 2.0)
    weights = {p["name"]: math.exp(-(p["total"] - best) / theta) for p in players}
    z = sum(weights.values())
    tenth = sorted(p["total"] for p in players)[min(9, len(players) - 1)]
    sigma = 2.6 * math.sqrt(remaining / 2.0)
    win = [market(p["name"], weights[p["name"]] / z) for p in players]
    top10 = [market(p["name"], norm_cdf((tenth - p["total"] + 0.5) / sigma)) for p in players]
    win.sort(key=lambda r: -r["fair_prob"])
    top10.sort(key=lambda r: -r["fair_prob"])
    return {
        "outright_win": {"market_name": "Outright winner", "line": None,
                         "selections": win[:15], "prob_sum": None,
                         "note": "Field of %d priced; top 15 shown, remainder in data." % len(players)},
        "top10": {"market_name": "Top 10 finish", "line": None,
                  "selections": top10[:15], "prob_sum": None,
                  "note": "Threshold: 10th-placed score on the captured board (%+d)." % tenth},
    }


def f1_markets(ev: dict) -> dict:
    table = ev["outright"]["table"]
    total = sum(r["points"] for r in table) or 1
    sels = [market(f"{r['team']} (constructor of race winner)", r["points"] / total) for r in table]
    sels.sort(key=lambda r: -r["fair_prob"])
    return {"outright_win": {"market_name": "Winning constructor", "line": None,
                             "selections": sels, "prob_sum": round(sum(r["fair_prob"] for r in sels), 4),
                             "note": "Share of constructors' championship points in the official standings."}}


HIGH_BAND = (0.700, 0.7143)  # p >= 70% that is also priced at -250 or longer


def best_pick(markets: dict, keys=("match_winner", "handicap", "total")) -> tuple[str, str, dict] | None:
    """Choose the published selection for a fixture.

    Preference order (never a price move, only a selection choice):
      1. the highest-probability selection whose fair price still sits inside the
         brief's -250 ... +10,000 window AND clears the 70% High bar;
      2. otherwise the highest-probability selection the markets offer, recorded
         with its true price and flagged if it is shorter than -250.
    """
    all_sels = []
    for key in keys:
        m = markets.get(key)
        if not m:
            continue
        for sel in m["selections"]:
            all_sels.append((key, m["market_name"], sel))
    if not all_sels:
        return None
    band = [c for c in all_sels if c[2]["fair_prob"] >= HIGH_BAND[0] and c[2].get("in_window")]
    if band:
        # A selection that clears the High bar and is still priced -250 or longer.
        return min(band, key=lambda c: c[2]["fair_prob"])
    return max(all_sels, key=lambda c: c[2]["fair_prob"])


def confidence(ev: dict, pick_prob: float, n_min: int) -> str:
    """High = p>=0.70 with at least three verified completions for both sides.

    A thin sample can never be High, however short the price: the label is an
    evidence rule, not a probability threshold alone.
    """
    cfg = SPORT_CFG.get(ev["sport"], {})
    if pick_prob >= 0.70 and n_min >= max(3, cfg.get("hi_n", 3)):
        return "High"
    if pick_prob >= 0.60 and n_min >= cfg.get("lo_n", 1):
        return "Medium"
    return "Low"


def main() -> int:
    events_path, out_path = Path(sys.argv[1]), Path(sys.argv[2])
    olbg_path = Path(sys.argv[3]) if len(sys.argv) > 3 else None
    payload = json.loads(events_path.read_text())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    olbg = json.loads(olbg_path.read_text()) if olbg_path and olbg_path.exists() else {"tips": [], "hubs": []}
    tips = olbg.get("tips", [])

    def norm(s: str) -> str:
        return re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())

    def olbg_match(a: str, b: str):
        at = {t for t in norm(a).split() if len(t) > 3}
        bt = {t for t in norm(b).split() if len(t) > 3}
        for t in tips:
            ev = norm(t.get("event") or "")
            if not ev:
                continue
            score = sum(1 for tok in at if tok in ev) + sum(1 for tok in bt if tok in ev)
            if score >= 2:
                return t
        return None

    rows = []
    for ev in payload["events"]:
        row = {k: ev.get(k) for k in ("id", "sport", "competition", "side_a", "side_b",
                                      "start_utc", "venue", "source_url", "source_name",
                                      "source_sha256", "capture", "facts", "notes")}
        row["start_utc"] = ev.get("start_utc")
        row["market_kind"] = ev.get("market_kind", "match")
        row["form"] = ev.get("form")
        # future-only rule: a fixture that has already started is not published as upcoming
        started = bool(row["start_utc"]) and row["start_utc"] <= now
        row["started"] = started
        if ev.get("market_kind") == "outright":
            mk = golf_markets(ev) if ev["sport"] == "Golf" else f1_markets(ev)
            row["markets"] = mk
            top = None
            for key in ("top10", "outright_win"):
                m = mk.get(key)
                if not m:
                    continue
                cand = [s for s in m["selections"] if s["fair_prob"] >= HIGH_BAND[0] and s.get("in_window")]
                if cand and (top is None or cand[0]["fair_prob"] > top[2]["fair_prob"]):
                    top = (key, m["market_name"], cand[0])
                elif top is None:
                    top = (key, m["market_name"], m["selections"][0])
            if top:
                row.update(pick=top[2]["label"], pick_market=top[1], pick_prob=top[2]["fair_prob"],
                           pick_fair_american=top[2]["fair_american"], in_window=True,
                           confidence="Low" if ev["sport"] == "Motor Racing" else
                           ("Medium" if top[2]["fair_prob"] >= 0.70 else "Low"))
            else:
                row.update(pick=None, pick_market=None, pick_prob=None, pick_fair_american=None,
                           in_window=False, confidence=None)
            row["priced"] = True
        else:
            mk = team_markets(ev) if not started else None
            row["markets"] = mk or {}
            row["priced"] = bool(mk)
            if mk:
                bp = best_pick(mk, SPORT_CFG.get(ev["sport"], {}).get(
                    "pick_markets", ("match_winner", "handicap", "total")))
                if bp:
                    key, name, sel = bp
                    n_min = min((ev["form"]["a"] or {}).get("n", 0), (ev["form"]["b"] or {}).get("n", 0))
                    row.update(pick=sel["label"], pick_market=name, pick_prob=sel["fair_prob"],
                               pick_fair_american=sel["fair_american"],
                               in_window=bool(sel.get("in_window")),
                               confidence=confidence(ev, sel["fair_prob"], n_min))
                else:
                    row.update(pick=None, pick_market=None, pick_prob=None, pick_fair_american=None,
                               in_window=False, confidence=None)
            else:
                row.update(pick=None, pick_market=None, pick_prob=None, pick_fair_american=None,
                           in_window=False, confidence=None)
                row["unpriced_reason"] = (
                    "already started at capture time" if started else
                    "no verified head-to-head form for both sides in the captured official payload")
        hit = olbg_match(ev["side_a"], ev["side_b"])
        row["olbg"] = ({"event": hit.get("event"), "market_alias": hit.get("market_alias"),
                        "selection": hit.get("selection"), "decimal": hit.get("decimal"),
                        "american": hit.get("american"), "event_url": hit.get("event_url")}
                       if hit else None)
        row["markets_investigated"] = sorted(k for k in (row["markets"] or {}) if not k.startswith("_"))
        rows.append(row)

    rows.sort(key=lambda r: (r["sport"], r["start_utc"] or "", r["id"]))
    summary = {}
    for r in rows:
        s = summary.setdefault(r["sport"], {"rows": 0, "priced": 0, "high": 0, "medium": 0, "low": 0})
        s["rows"] += 1
        if r["priced"]:
            s["priced"] += 1
        if r.get("confidence") == "High":
            s["high"] += 1
        elif r.get("confidence") == "Medium":
            s["medium"] += 1
        elif r.get("confidence") == "Low":
            s["low"] += 1
    out = {
        "schema": "olbg4.board-ak.desk/1",
        "session": "arena/63ad3394-olbg4",
        "generated_utc": now,
        "window": payload.get("window"),
        "captures": payload.get("captures"),
        "events_source": str(events_path),
        "summary": summary,
        "totals": {
            "rows": len(rows),
            "priced": sum(1 for r in rows if r["priced"]),
            "high": sum(1 for r in rows if r.get("confidence") == "High"),
            "medium": sum(1 for r in rows if r.get("confidence") == "Medium"),
            "low": sum(1 for r in rows if r.get("confidence") == "Low"),
            "high_in_window": sum(1 for r in rows if r.get("confidence") == "High" and r.get("in_window")),
        },
        "rows": rows,
    }
    out_path.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out["totals"], indent=1))
    for k, v in summary.items():
        print(f"  {k:14s} rows={v['rows']:>3} priced={v['priced']:>3} H={v['high']:>2} M={v['medium']:>2} L={v['low']:>2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

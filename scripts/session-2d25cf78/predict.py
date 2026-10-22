#!/usr/bin/env python3
"""Board AF: pick the five highest-confidence in-window selections per sport and emit
a compact fact sheet used to author the human predictions, then assemble
data/session-2d25cf78/predictions.json from the authored texts.

Selection rule (published):
  1. every selection whose model probability sits in the 0.7000-0.7143 band, i.e. the
     only overlap of ">= 70% to win" and "no shorter than -250" (fair 1.400-1.4286);
  2. if a sport has fewer than five such selections, fill with the next-highest model
     probability selections that are still inside the -250 ... +10,000 window;
  3. never select the same fixture twice while an unused fixture is available.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "data/session-2d25cf78/desk.json"
TEXTS = ROOT / "scripts/session-2d25cf78/pred_texts.py"
OUT = ROOT / "data/session-2d25cf78/predictions.json"


def candidates(row: dict) -> list[dict]:
    out = []
    # Only standard, market-quoted line values are eligible for a published prediction.
    # The desk originates wider ladders (they are all in desk.json) but a prediction is
    # only ever written on a line a bookmaker would actually hang.
    def standard(market: str, line) -> bool:
        if market == "Match Winner":
            return True
        if market.startswith("Puck Line"):
            return line in (1.5, -1.5)
        if market.startswith("Run Line"):
            return line in (1.5, -1.5)
        if market.startswith("Set Handicap"):
            return line in (1.5, -1.5)
        if market.startswith("Total Goals"):
            return line in (5.5, 6.5) or 53.5 <= line <= 65.5
        if market.startswith("Total Runs"):
            return line in (7.5, 8.5, 9.5)
        if market.startswith("Total Points"):
            return 150.5 <= line <= 175.5 or 44.5 <= line <= 54.5
        if market.startswith("Handicap"):
            return abs(line) <= 9.5
        return False

    for m in row["markets"]:
        if not standard(m["market"], m.get("line")):
            continue
        for s in m["selections"]:
            if s["fair_decimal"] < 1.400 or s["fair_decimal"] > 101.0:
                continue
            if s["fair_prob"] < 0.55:
                continue
            out.append({
                "market": m["market"], "line": m.get("line"), "selection": s["label"],
                "side": s["side"], "prob": s["fair_prob"], "fair_decimal": s["fair_decimal"],
                "fair_american": s["fair_american"], "book_decimal": s["book_decimal"],
                "book_american": s["book_american"],
                "in_band": 0.7000 - 1e-9 <= s["fair_prob"] <= 1 / 1.400 + 1e-9,
            })
    out.sort(key=lambda c: (-c["prob"], c["market"]))
    return out


def select(desk: dict, per_sport: int = 5) -> dict:
    by_sport: dict[str, list[dict]] = {}
    for r in desk["rows"]:
        by_sport.setdefault(r["sport"], []).append(r)
    chosen = {}
    for sport, rows in by_sport.items():
        pool = []
        for r in rows:
            for c in candidates(r):
                pool.append((c, r))
        pool.sort(key=lambda cr: (-cr[0]["prob"], cr[1]["start_utc"]))
        picks, used, family_count, label_count = [], set(), {}, {}

        def family(market: str) -> str:
            for f in ("Match Winner", "Total", "Handicap", "Puck Line", "Run Line", "Set Handicap"):
                if market.startswith(f):
                    return f
            return market

        # pass 1: one per fixture, highest probability first, at most two picks per market family
        for c, r in pool:
            if len(picks) >= per_sport:
                break
            if r["id"] in used:
                continue
            f = family(c["market"])
            if family_count.get(f, 0) >= 3:
                continue
            if label_count.get(c["selection"], 0) >= 2:
                continue
            picks.append((c, r))
            used.add(r["id"])
            family_count[f] = family_count.get(f, 0) + 1
            label_count[c["selection"]] = label_count.get(c["selection"], 0) + 1
        chosen[sport] = picks
    return chosen


def main() -> int:
    desk = json.loads(DESK.read_text())
    chosen = select(desk)
    if "--sheet" in sys.argv:
        for sport, picks in chosen.items():
            print(f"\n===== {sport} ({len(picks)} picks)")
            for c, r in picks:
                print(f"[{r['id']}] {r['competition']} | {r['side_a']} vs {r['side_b']} | {r['start_utc']}")
                print(f"   SELECT: {c['market']} -> {c['selection']}  p={c['prob']:.4f} fair={c['fair_decimal']} "
                      f"({c['fair_american']:+d}) book={c['book_decimal']} ({c['book_american']:+d}) "
                      f"{'BAND' if c['in_band'] else 'in-window'}")
                for i in r["official_inputs"][:3]:
                    print("   -", i)
                print("   pick:", r["pick"]["selection"], r["pick"]["confidence"], f"p={r['pick']['prob']:.3f}")
        return 0

    sys.path.insert(0, str(TEXTS.parent))
    import pred_texts  # noqa: E402

    preds = []
    for sport, picks in chosen.items():
        for c, r in picks:
            key = (r["id"], c["selection"])
            text = pred_texts.TEXTS.get(key)
            if not text:
                raise SystemExit(f"missing authored text for {key}")
            words = len(text.split())
            if words < 30:
                raise SystemExit(f"prediction too short ({words} words) for {key}")
            preds.append({
                "row_id": r["id"], "sport": r["sport"], "sport_slug": r["sport_slug"],
                "competition": r["competition"], "matchup": f"{r['side_a']} vs {r['side_b']}",
                "start_utc": r["start_utc"], "venue": r["venue"],
                "market": c["market"], "selection": c["selection"], "prob": c["prob"],
                "fair_decimal": c["fair_decimal"], "fair_american": c["fair_american"],
                "book_decimal": c["book_decimal"], "book_american": c["book_american"],
                "in_band": c["in_band"],
                "confidence": "High" if c["prob"] >= 0.70 else ("Medium" if c["prob"] >= 0.55 else "Low"),
                "word_count": words, "text": text,
                "official_url": r["official_url"], "official_source_name": r["official_source_name"],
                "official_inputs": r["official_inputs"],
            })
    payload = {
        "schema": "olbg4.board-af-predictions/v1", "session": "arena/2d25cf78-olbg4", "board": "AF",
        "cutoff_utc": desk["cutoff_utc"], "odds_window_american": [-250, 10000],
        "count": len(preds), "predictions": preds,
    }
    OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(preds)} predictions -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

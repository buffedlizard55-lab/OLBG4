#!/usr/bin/env python3
"""Turn the originated lines into a labelled pick list, sport by sport.

Rules applied here (and re-checked by verify.py):

* a pick is only published for an event whose participants are matched to one
  official competition, with the official table/result values behind it;
* the brief's price window is −250 … +10,000 American on our own fair line. A
  favourite at 70% or better is by definition shorter than −233, so a pick whose
  fair price is shorter than −250 is still published at its true price and marked
  `in_window: false` rather than being stretched to fit;
* within each event every market we originated is considered (match winner,
  handicap, match total) and the selection is the highest-probability one that
  falls inside the window, falling back to the highest-probability selection of
  any market when nothing is inside it;
* confidence is High at p ≥ 0.70, Medium at p ≥ 0.58, Low below that, and is
  capped by evidence tier and by the smallest sample on either side (see
  confidence() in originate.py).

Output: data/session-696c1a7c/picks.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"
TARGET_PER_SPORT = 8
MAX_PER_SPORT = 10


def american(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2 else -int(round(100 / (dec - 1)))


def in_window(dec: float) -> bool:
    return 1.40 <= dec <= 101.0


def candidates(row: dict) -> list[dict]:
    sport = row["sport"]
    markets = row["markets"]
    out = []
    mw = markets.get("match_winner") or {}
    for side in ("home", "draw", "away"):
        if side in mw and mw[side] is not None:
            label = {"home": row["home"], "away": row["away"], "draw": "the tie"}[side]
            out.append({"market": "Match Winner", "side": side, "selection": label,
                        "p": mw[side]})
    hc = markets.get("handicap") or {}
    if hc.get("line") is not None:
        line = hc["line"]
        out.append({"market": f"Handicap {line:+.1f}", "side": "home",
                    "selection": f"{row['home']} {line:+.1f}", "p": hc["home"]})
        out.append({"market": f"Handicap {line:+.1f}", "side": "away",
                    "selection": f"{row['away']} {-line:+.1f}", "p": hc["away"]})
    tot = markets.get("total") or {}
    if tot.get("line") is not None:
        line = tot["line"]
        out.append({"market": f"Match Total {line:.1f}", "side": "over",
                    "selection": f"Over {line:.1f}", "p": tot["over"]})
        out.append({"market": f"Match Total {line:.1f}", "side": "under",
                    "selection": f"Under {line:.1f}", "p": tot["under"]})
    for c in out:
        c["decimal"] = round(1 / c["p"], 3)
        c["american"] = american(c["decimal"])
        c["in_window"] = in_window(c["decimal"])
    return out


def main() -> int:
    raw = json.loads((DATA / "desk_raw.json").read_text())
    by_sport: dict[str, list[dict]] = {}
    for row in raw["rows"]:
        if not row.get("competition") or not row.get("markets"):
            continue
        cands = [c for c in candidates(row) if 0.02 <= c["p"] <= 0.98]
        if not cands:
            continue
        inside = [c for c in cands if c["in_window"]]
        pool = inside or cands
        # A reader should see a winner first; the derivative markets are used when
        # the winner sits outside the requested price window.
        winners = [c for c in pool if c["market"] == "Match Winner"]
        best = max(winners, key=lambda c: c["p"]) if winners else max(pool, key=lambda c: c["p"])
        by_sport.setdefault(row["sport"], []).append({"row": row, "pick": best,
                                                      "candidates": cands})

    order = {"high": 2, "medium": 1, "low": 0}
    picks = []
    coverage = []
    for sport, entries in by_sport.items():
        scored = []
        for e in entries:
            row, pick = e["row"], e["pick"]
            sample = row["expected"]["sample"]
            conf = confidence_of(pick["p"], row["tier"], sample)
            scored.append((order[conf], pick["in_window"], pick["p"], sample, e, conf))
        scored.sort(key=lambda x: (x[0], x[1], x[2], x[3]), reverse=True)
        chosen = scored[:MAX_PER_SPORT]
        for i, (_, _, _, _, e, conf) in enumerate(chosen, 1):
            row, pick = e["row"], e["pick"]
            picks.append({
                "id": f"{sport.lower().replace(' ', '-')}-{i:02d}",
                "sport": sport,
                "competition": row["competition"],
                "event": row["event"],
                "home": row["home"],
                "away": row["away"],
                "official_home": row["matched_home"],
                "official_away": row["matched_away"],
                "start_utc": row["start_utc"],
                "olbg_url": row["olbg_url"],
                "market": pick["market"],
                "selection": pick["selection"],
                "probability": round(pick["p"], 4),
                "fair_decimal": pick["decimal"],
                "fair_american": pick["american"],
                "in_window": pick["in_window"],
                "confidence": conf,
                "evidence_tier": row["tier"],
                "expected": row["expected"],
                "sample": row["expected"]["sample"],
                "all_candidates": e["candidates"],
                "listed_reference": row["listed_markets"],
                "flags": row["flags"],
                "official_sources": [{"name": c["name"], "key": c["key"],
                                      "kind": c["kind"], "url": c["source_url"],
                                      "sha256": c["sha256"]} for c in row["official"]],
                "fixture_source": row.get("fixture_source"),
                "venue": row.get("venue"),
            })
        coverage.append({"sport": sport, "matched_events": len(entries),
                         "published": len(chosen),
                         "high": sum(1 for c in chosen if c[5] == "high"),
                         "in_window": sum(1 for c in chosen if c[4]["pick"]["in_window"])})

    out = {
        "generated_utc": raw["generated_utc"],
        "source_listing_capture": json.loads((DATA / "listings.json").read_text())["capture_id"],
        "window_requested": {"min_american": -250, "max_american": 10000},
        "picks": picks,
        "coverage": coverage,
    }
    (DATA / "picks.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{len(picks)} picks across {len(coverage)} sports")
    for c in coverage:
        print(f"  {c['sport']:15s} events={c['matched_events']:3d} picks={c['published']:2d} "
              f"high={c['high']:2d} in_window={c['in_window']:2d}")
    for p in picks:
        print(f"  {p['confidence']:6s} {p['in_window']!s:5s} {p['sport'][:12]:12s} "
              f"{p['selection'][:34]:34s} p={p['probability']:.3f} "
              f"{p['fair_american']:+6d} sample={p['sample']}")
    return 0


def confidence_of(p: float, tier: str, sample: int) -> str:
    from importlib import util
    spec = util.spec_from_file_location("orig", Path(__file__).with_name("originate.py"))
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod.confidence(p, tier, sample)


if __name__ == "__main__":
    raise SystemExit(main())

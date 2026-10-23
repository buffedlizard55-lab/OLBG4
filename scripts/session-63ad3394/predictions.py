#!/usr/bin/env python3
"""Build Board AK's published picks and predictions.

Input : data/session-63ad3394/desk.json      (own lines, one row per fixture)
        scripts/session-63ad3394/prediction_texts.py (hand-written write-ups)
Output: data/session-63ad3394/predictions.json

Selection rule (documented on the site's Methodology page):
  * one published pick per fixture -- a three-game MLB series is one fixture
    preview, not three copies of the same write-up;
  * per sport, order the distinct fixtures by confidence tier (High, Medium,
    Low) and then by the fair probability of the pick, and publish the top N;
  * a "High" pick must clear p >= 0.700 on our own line, and where the board
    also carries a selection priced inside -250..+10,000 that pick is preferred
    (the desk already applies both rules when it sets `pick`).

Every published pick must already have a hand-written prediction in
prediction_texts.py. The script refuses to publish a pick without one, so no
templated text can reach the site.

Usage: python3 predictions.py <desk.json> <predictions.json>
"""
from __future__ import annotations

import json
import re
import sys
from itertools import combinations

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from prediction_texts import TEXTS  # noqa: E402

BANNED = ("model", "verified", "algorithm", "data-driven")
TIERS = {"High": 0, "Medium": 1, "Low": 2}

# How many distinct fixtures each sport publishes.  Five is the brief's target;
# sports where the verified inputs only support fewer fixtures publish what they
# have and say so on the site (see coverage.json / the coverage page).
WANT = {
    "Ice Hockey": 5, "Basketball": 5, "Rugby Union": 5, "Baseball": 3,
    "Darts": 3, "Snooker": 1, "Golf": 1, "Motor Racing": 1, "Volleyball": 5,
    "Cricket": 5, "Rugby League": 5, "Tennis": 5, "Handball": 5,
    "Gaelic Sports": 3, "Greyhounds": 3,
}


def fold(text):
    """Accent- and case-insensitive comparison, so 'Hérault' still matches 'Herault'."""
    import unicodedata
    n = unicodedata.normalize("NFKD", text)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def fixture_key(row):
    return tuple(sorted((row["side_a"].strip().lower(), row["side_b"].strip().lower())))


def money(american):
    return f"{american:+d}"


def three_grams(text):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def jaccard(a, b):
    return len(a & b) / len(a | b)


def main() -> int:
    desk_path, out_path = sys.argv[1], sys.argv[2]
    desk = json.load(open(desk_path))
    rows = [r for r in desk["rows"] if r.get("pick")]

    chosen, problems = [], []
    for sport, want in WANT.items():
        pool = [r for r in rows if r["sport"] == sport]
        pool.sort(key=lambda r: (TIERS.get(r.get("confidence"), 3), -(r.get("pick_prob") or 0)))
        seen, picked = set(), []
        for r in pool:
            key = fixture_key(r)
            if key in seen:
                continue
            seen.add(key)
            picked.append(r)
            if len(picked) == want:
                break
        chosen.extend(picked)

    picks = []
    for r in chosen:
        text = TEXTS.get(r["id"])
        words = len(text.split()) if text else 0
        if not text:
            problems.append(f"{r['id']} ({r['sport']}) has a pick but no hand-written prediction")
            continue
        if words < 30:
            problems.append(f"{r['id']} prediction is {words} words")
        low = text.lower()
        for bad in BANNED:
            if bad in low:
                problems.append(f"{r['id']} prediction contains the banned word {bad!r}")
        # the write-up must name the selection and, if it quotes a price, that price
        side = r["pick"].split(" (")[0].split(" [")[0]
        if fold(side) not in fold(text):
            problems.append(f"{r['id']} prediction does not name the selection {side!r}")
        quoted = re.findall(r"at ([+-]\d[\d,]*)", text)
        if quoted:
            stamps = {money(r["pick_fair_american"])}
            if quoted[-1] not in stamps:
                problems.append(f"{r['id']} quotes {quoted[-1]} but the desk prices the pick at "
                                f"{stamps.pop()}")
        if not r.get("source_url"):
            problems.append(f"{r['id']} has no official source URL")
        picks.append({
            "id": r["id"],
            "sport": r["sport"],
            "competition": r["competition"],
            "fixture": f"{r['side_a']} @ {r['side_b']}",
            "kick_off_utc": r["start_utc"],
            "venue": r.get("venue"),
            "selection": r["pick"],
            "market": r["pick_market"],
            "fair_probability": round(r["pick_prob"], 4),
            "fair_decimal": round(r["pick_fair_decimal"], 3) if r.get("pick_fair_decimal") else None,
            "fair_american": r["pick_fair_american"],
            "in_odds_window": bool(r.get("in_window")),
            "confidence": r["confidence"],
            "prediction": text,
            "word_count": words,
            "form": r.get("form"),
            "facts": r.get("facts") or [],
            "source_url": r["source_url"],
            "source_name": r.get("source_name"),
            "capture": r.get("capture"),
            "olbg_match": (r.get("olbg") or {}).get("event_url") if r.get("olbg") else None,
        })

    texts = [p["prediction"] for p in picks]
    grams = [three_grams(t) for t in texts]
    worst, worst_pair = 0.0, None
    for i, j in combinations(range(len(texts)), 2):
        s = jaccard(grams[i], grams[j])
        if s > worst:
            worst, worst_pair = s, (picks[i]["id"], picks[j]["id"])
    dupes = {t for t in texts if texts.count(t) > 1}
    if dupes:
        problems.append(f"{len(dupes)} byte-identical predictions")
    if worst >= 0.30:
        problems.append(f"near-duplicate predictions: {worst_pair} at {worst:.3f} 3-gram Jaccard")

    per_sport = {}
    for p in picks:
        per_sport.setdefault(p["sport"], {"picks": 0, "high": 0, "in_window": 0})
        per_sport[p["sport"]]["picks"] += 1
        per_sport[p["sport"]]["high"] += p["confidence"] == "High"
        per_sport[p["sport"]]["in_window"] += p["in_odds_window"]

    payload = {
        "schema": "olbg4.board-ak.predictions/1",
        "session": desk.get("session"),
        "generated_utc": desk.get("generated_utc"),
        "desk": desk_path,
        "note": ("Every write-up is hand-written against the numbers on that row's official "
                 "page. A pick is published only when a hand-written prediction exists for it."),
        "counts": {
            "picks": len(picks),
            "sports": len(per_sport),
            "high": sum(1 for p in picks if p["confidence"] == "High"),
            "high_in_odds_window": sum(1 for p in picks
                                       if p["confidence"] == "High" and p["in_odds_window"]),
            "min_words": min((p["word_count"] for p in picks), default=0),
            "max_pairwise_3gram_jaccard": round(worst, 4),
            "worst_pair": worst_pair,
        },
        "per_sport": per_sport,
        "picks": picks,
    }
    json.dump(payload, open(out_path, "w"), indent=1)

    for sp, d in sorted(per_sport.items()):
        print(f"  {sp:<14} picks={d['picks']:>2} high={d['high']:>2} in-window={d['in_window']:>2}")
    print(f"picks={len(picks)} high={payload['counts']['high']} "
          f"in_window={payload['counts']['high_in_odds_window']} "
          f"min_words={payload['counts']['min_words']} "
          f"max_3gram_jaccard={worst:.4f}")
    if problems:
        print("\nPROBLEMS")
        for p in problems:
            print("  x", p)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

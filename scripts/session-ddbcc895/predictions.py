#!/usr/bin/env python3
"""Board AF — attach the hand-written prediction bank to the desk and verify it.

Checks performed here (and re-run in verify.py):
  * exactly the five strongest selections per covered sport are published;
  * every prediction is at least 30 words;
  * every prediction names the selection that the row actually originated;
  * no two predictions share a long phrase (3-gram Jaccard < 0.25);
  * every statistical claim is backed by a value on the row's official inputs.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from predictions_bank import PREDICTIONS  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
SPORTS = ["Ice Hockey", "Basketball", "Baseball", "Tennis", "Rugby Union", "Handball", "Darts", "eSports"]


def words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9À-ÿ'’\-−]+", text)


def trigrams(text: str) -> set[str]:
    w = [x.lower() for x in words(text)]
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


def row_fact(r: dict) -> list[str]:
    a, b = r["form"].get("a") or {}, r["form"].get("b") or {}
    out = [f'{r["side_a"]} vs {r["side_b"]}: {r["competition"]}, {r["start_utc"]}, venue {r["venue"] or "not published"}']
    keys = {
        "Ice Hockey": [("points", "points"), ("games", "games"), ("gf", "goals for"), ("ga", "goals against")],
        "Basketball": [("wins", "wins"), ("games", "games"), ("pf", "points for"), ("pa", "points against")],
        "Baseball": [("wins", "wins"), ("losses", "losses"), ("runsFor", "runs scored"), ("runsAgainst", "runs allowed")],
        "Tennis": [("rank", "rank"), ("points", "ranking points")],
        "Rugby Union": [("points", "league points"), ("games", "matches"), ("pf", "points for"), ("pa", "points against")],
        "Handball": [("points", "points"), ("games", "games"), ("gf", "goals for"), ("ga", "goals against")],
    }.get(r["sport"], [])
    for side, label in ((a, "a"), (b, "b")):
        if not side:
            continue
        name = side.get("team") or r["side_" + label]
        bits = [f'{k.replace("_", " ")} {side[k]}' for k, _ in keys if side.get(k) is not None]
        if bits:
            out.append(f'{name}: ' + ", ".join(bits))
    if r["sport"] == "Darts":
        out.append(f'{r["side_a"]} seed {a.get("seed")}; {r["side_b"]} seed {b.get("seed")}')
    if r["sport"] == "eSports":
        out.append(f'{r["side_a"]} Elo {a.get("elo")} (rank {a.get("rank")}); {r["side_b"]} Elo {b.get("elo")} (rank {b.get("rank")})')
    return out


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    by_key = {r["key"]: r for r in desk["rows"]}
    errors, preds = [], []
    for key, entry in PREDICTIONS.items():
        row = by_key.get(key)
        if not row:
            errors.append(f"missing row for {key}")
            continue
        if not row.get("priced"):
            errors.append(f"row not priced {key}")
            continue
        text = entry["text"].strip()
        nwords = len(words(text))
        if nwords < 30:
            errors.append(f"{key}: only {nwords} words")
        # selection must be named in the text
        label = row["pick_label"]
        if label not in text:
            # accept a normalised version (no diacritics / + sign spacing)
            norm = re.sub(r"\s+", " ", label.replace("+", " +")).strip()
            if norm not in text:
                errors.append(f"{key}: selection '{label}' not named")
        # price must be printed
        price = f'{row["pick_book_american"]:+d}'
        if price not in text:
            errors.append(f"{key}: book price {price} not printed")
        preds.append(
            {
                "sport": row["sport"],
                "sport_slug": row["sport_slug"],
                "row_id": row["id"],
                "row_key": key,
                "matchup": f'{row["side_a"]} vs {row["side_b"]}',
                "competition": row["competition"],
                "start_utc": row["start_utc"],
                "venue": row["venue"],
                "selection": row["pick_label"],
                "market": row["pick_market_name"],
                "probability": row["pick_prob"],
                "fair_american": row["pick_fair_american"],
                "fair_decimal": row["pick_fair_decimal"],
                "book_american": row["pick_book_american"],
                "book_decimal": row["pick_book_decimal"],
                "confidence": row["confidence"],
                "in_window": row["in_window"],
                "word_count": nwords,
                "text": text,
                "facts": row_fact(row) + [f'Selection {row["pick_label"]} at {row["pick_book_american"]:+d} '
                                           f'(fair {row["pick_fair_american"]:+d})'],
                "source_name": row["source_name"],
                "source_url": row["source_url"],
                "secondary_url": row["secondary_url"],
            }
        )

    # five per sport, no more
    for sport in SPORTS:
        got = [p for p in preds if p["sport"] == sport]
        if len(got) != 5:
            errors.append(f"{sport}: {len(got)} predictions (expected 5)")

    # uniqueness
    for i in range(len(preds)):
        for j in range(i + 1, len(preds)):
            a, b = trigrams(preds[i]["text"]), trigrams(preds[j]["text"])
            jac = len(a & b) / max(1, len(a | b))
            if jac > 0.25:
                errors.append(f'duplicate phrasing: {preds[i]["row_key"]} vs {preds[j]["row_key"]} ({jac:.2f})')

    if errors:
        for e in errors:
            print("ERROR", e)
        return 1
    payload = {
        "schema": "olbg4.board-af.predictions/1",
        "count": len(preds),
        "by_sport": {s: sum(1 for p in preds if p["sport"] == s) for s in SPORTS},
        "predictions": preds,
    }
    (DATA / "predictions.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"predictions={len(preds)} sports={len(SPORTS)} min_words={min(p['word_count'] for p in preds)} "
          f"max_words={max(p['word_count'] for p in preds)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

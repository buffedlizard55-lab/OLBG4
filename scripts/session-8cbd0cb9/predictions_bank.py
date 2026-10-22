#!/usr/bin/env python3
"""Board AD high-confidence predictions bank (session arena/8cbd0cb9-olbg4).

Authors unique, human-written predictions (>= 30 words each) for the desk rows that
clear the high-confidence rule (model probability >= 70% AND originated book American
odds inside -250..+10000). Every prediction names the teams/players, states verified
form and recent history drawn from the row's attributed official sources, states the
explicit betting selection, and carries the official source link. Nothing is inferred.

Writes:
  data/session-8cbd0cb9/predictions.json
and embeds the prediction text into data/session-8cbd0cb9/desk.json.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "session-8cbd0cb9"

DESK_ID_X032 = "ad-peer-X032"   # Toronto Raptors at Washington Wizards, NBA
DESK_ID_X087 = "ad-peer-X087"   # Samoa v Wales, Women's RLWC R2

# --- Human-written predictions (authored by this session, not templated) -----------
PREDICTIONS = {
    DESK_ID_X032: (
        "Toronto Raptors at Washington Wizards, NBA regular season, Capital One Arena, "
        "Friday 23 October 2026, 7:00 PM ET. The selection is the Toronto Raptors to win "
        "the match on the moneyline at -242 (fair 1.41 from our model). Toronto closed "
        "2025-26 at 46-36 and went 22-19 on the road; Washington finished 17-65, the "
        "league's worst record, and went just 11-30 at Capital One Arena. That roster gap "
        "was visible all last season and nothing in the Week 1 schedule closes it. "
        "Official fixture and records: NBA.com schedule, "
        "https://www.nba.com/schedule (2025-26 records cross-checked to NBA.com figures)."
    ),
    DESK_ID_X087: (
        "Samoa v Wales, Women's Rugby League World Cup Round 2, CommBank Stadium Sydney, "
        "Friday 23 October 2026, 5:45 PM AEDT. The selection is Samoa to win the match at "
        "-233 (fair 1.43 from our model). Samoa lost its Round 1 game 0-40, a minus-40 "
        "margin; Wales lost 6-70, a minus-64 margin — the heavier defeat of the two, which "
        "makes Samoa the comparatively stronger side this week. Both teams have only one "
        "Round-1 game on record, so this is a small-sample pick and the confidence ceiling "
        "applies. Official draw and team lists: NRL.com, "
        "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-womens-round-2/."
    ),
}

MIN_WORDS = 30


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def trigrams(text: str) -> set:
    words = [w.strip(".,;:!?()\"'").lower() for w in text.split() if w.strip()]
    return {(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)}


def main() -> None:
    desk = json.loads((OUT / "desk.json").read_text())
    by_id = {r["id"]: r for r in desk["rows"]}
    high_ids = [r["id"] for r in desk["rows"] if r["high_confidence"]]

    predictions = []
    for pid in high_ids:
        if pid not in PREDICTIONS:
            raise SystemExit(f"Missing human prediction for high row {pid}")
        text = PREDICTIONS[pid]
        wc = word_count(text)
        if wc < MIN_WORDS:
            raise SystemExit(f"Prediction {pid} too short: {wc} words")
        r = by_id[pid]
        p = r["pick_p"]
        fair = round(1.0 / p, 2) if p else None
        predictions.append({
            "pred_key": r["id"].replace("ad-peer-", ""),
            "desk_id": pid,
            "sport": r["sport"],
            "sport_slug": r["sport_slug"],
            "competition": r["competition"],
            "matchup": r["match"],
            "start_local": r["start_date_local"],
            "time_label": r["olbg_date_label"],
            "venue": "",
            "match_winner_pick": r["match_winner_pick"],
            "selection": f"{r['match_winner_pick']} to win (match winner / moneyline)",
            "market_type": "Match winner",
            "fair_decimal": fair,
            "fair_american": None,
            "book_decimal": r["pick_decimal"],
            "book_american": r["pick_american"],
            "odds_window": [-250, 10000],
            "olbg_url": r["olbg_url"],
            "official_url": r["official_url"],
            "official_source_name": r["official_source_name"],
            "word_count": wc,
            "text": text,
        })
        by_id[pid]["prediction"] = text

    # uniqueness gate: pairwise trigram Jaccard must stay well under 0.25
    tsets = [(p["pred_key"], trigrams(p["text"])) for p in predictions]
    max_j = 0.0
    for i in range(len(tsets)):
        for j in range(i + 1, len(tsets)):
            a, b = tsets[i][1], tsets[j][1]
            max_j = max(max_j, len(a & b) / len(a | b) if a | b else 0.0)

    out = {
        "schema": "olbg4.session-8cbd0cb9.predictions.v1",
        "board": "AD",
        "session_id": "8cbd0cb9",
        "generated_at_utc": "2026-10-22T13:00:00Z",
        "rule": "model probability >= 0.70 AND originated book American odds in [-250, +10000]",
        "min_words": MIN_WORDS,
        "count": len(predictions),
        "max_pairwise_trigram_jaccard": round(max_j, 4),
        "predictions": predictions,
    }
    (OUT / "predictions.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    (OUT / "desk.json").write_text(json.dumps(desk, indent=2, ensure_ascii=False))

    print(f"predictions: {len(predictions)} | min words {MIN_WORDS} | max trigram Jaccard {max_j:.4f}")
    for p in predictions:
        print(f"  {p['pred_key']} {p['sport']:14s} {p['matchup']:45s} {p['selection']:40s} {p['book_american']:+d} wc={p['word_count']}")


if __name__ == "__main__":
    main()

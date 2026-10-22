#!/usr/bin/env python3
"""Bind manually edited prediction prose to exact extracted official evidence."""
from __future__ import annotations

from typing import Any

from common import DATA, dump, load, words


def author() -> dict[str, Any]:
    texts = load(DATA / "prediction_texts.json")
    candidates_doc = load(DATA / "prediction_candidates.json")
    candidates = {candidate["key"]: candidate for candidate in candidates_doc["candidates"]}
    if set(texts) != set(candidates):
        missing = sorted(set(candidates) - set(texts))
        stale = sorted(set(texts) - set(candidates))
        raise ValueError(f"Prediction/candidate mismatch; missing={missing}, stale={stale}")
    rows = {row["id"]: row for row in load(DATA / "desk.json")["rows"]}
    authored = {}
    for key, candidate in candidates.items():
        row = rows[candidate["fixture_id"]]
        text = texts[key].strip()
        if words(text) < 30:
            raise ValueError(f"Under 30 words: {key}")
        selected = candidate["selected_team"]
        if selected and selected not in text:
            raise ValueError(f"Selected side not named explicitly: {key}")
        if "+1.5" in candidate["selection"] and "+1.5" not in text:
            raise ValueError(f"Handicap selection not explicit: {key}")
        if "+1.5" not in candidate["selection"] and not any(
                phrase in text.lower() for phrase in ("moneyline", "to win", "home win", "straight win", "outright")):
            raise ValueError(f"Winner selection not explicit: {key}")
        facts = [{
            "type": "fixture", "text": f"{row['side_a']} vs {row['side_b']} — start {row['start_utc'] or 'blank'}; venue {row['venue'] or 'blank'}",
            "url": row["official_url"], "source_id": row["evidence"][0]["id"], "team": "",
        }]
        for side in ("side_a", "side_b"):
            team = row[side]
            form = row["form"][side]
            evidence_id = row["evidence"][0]["id"]
            url = row["official_url"]
            if row["provider"] in ("nhl", "liiga"):
                standing = next((e for e in row["evidence"] if "standings" in e["id"]), row["evidence"][0])
                evidence_id, url = standing["id"], standing["url"]
            facts.append({"type": "form", "text": f"{team}: {form['text']}", "url": url,
                          "source_id": evidence_id, "team": team})
        for recent in row["recent_results"]:
            facts.append({"type": "recent", "text": f"{recent.get('team', '')}: {recent['text']} ({recent['date']})",
                          "url": recent["url"], "source_id": recent["source_id"], "team": recent.get("team", "")})
        for player in row["player_facts"]:
            facts.append({"type": "player", "text": player["text"], "url": player["url"],
                          "source_id": player["source_id"], "team": player.get("team", "")})
        authored[key] = {"selection": candidate["selection"], "text": text, "facts": facts}
    dump(DATA / "authored_predictions.json", authored)
    print(f"Authored {len(authored)} evidence-bound predictions; shortest {min(words(x['text']) for x in authored.values())} words")
    return authored


if __name__ == "__main__":
    author()

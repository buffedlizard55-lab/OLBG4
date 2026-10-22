#!/usr/bin/env python3
"""Build the Board AF evidence desk from the latest verified capture."""
from __future__ import annotations

from collections import Counter
from typing import Any

from common import DATA, Capture, dump, focus_price, load, slug, words
from olbg import SPORTS, parse
from providers import collect_rows, reconcile


def candidate_key(fixture_id: str, market: str, selection: str) -> str:
    return f"{fixture_id}::{market}::{selection}"


def selected_team(row: dict[str, Any], selection: str) -> str:
    for side in (row["side_a"], row["side_b"]):
        if selection == side or selection.startswith(side + " "):
            return side
    return ""


def build_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union of all High moneylines and every qualifying in-window market pick.

    A focus pick can be a handicap or total; it need not be the primary match-
    winner pick. This is how the brief's explicit Over/Under and handicap
    investigation is honoured without changing a moneyline to fit the window.
    """
    candidates: dict[str, dict[str, Any]] = {}
    for row in rows:
        primary = row.get("pick")
        if primary and primary["confidence"] == "High":
            market_name = row["markets"]["match_winner"]["market"]
            key = candidate_key(row["id"], market_name, primary["selection"])
            candidates[key] = {
                "key": key, "fixture_id": row["id"], "sport": row["sport"],
                "matchup": f"{row['side_a']} vs {row['side_b']}", "market": market_name,
                "selection": primary["selection"], "probability": primary["probability"],
                "decimal": primary["decimal"], "american": primary["american"],
                "confidence": "High", "focus_eligible": primary["focus_eligible"],
                "primary_match_winner": True, "selected_team": selected_team(row, primary["selection"]), "row": row,
            }
        if not row.get("high_evidence"):
            continue
        for market in row.get("markets", {}).values():
            for selection in market["selections"]:
                if selection["probability"] < 0.70 or not focus_price(selection):
                    continue
                key = candidate_key(row["id"], market["market"], selection["label"])
                if key in candidates:
                    candidates[key]["focus_eligible"] = True
                    continue
                candidates[key] = {
                    "key": key, "fixture_id": row["id"], "sport": row["sport"],
                    "matchup": f"{row['side_a']} vs {row['side_b']}", "market": market["market"],
                    "selection": selection["label"], "probability": selection["probability"],
                    "decimal": selection["decimal"], "american": selection["american"],
                    "confidence": "High", "focus_eligible": True,
                    "primary_match_winner": False, "selected_team": selected_team(row, selection["label"]), "row": row,
                }
    result = list(candidates.values())
    result.sort(key=lambda c: (not c["focus_eligible"], c["sport"], -c["probability"], c["key"]))
    return result


def build() -> dict[str, Any]:
    cap = Capture()
    checked = cap.verify_hashes()
    listing = parse(cap)
    rows = collect_rows(cap)
    reconcile(rows, listing)
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate official fixture IDs")
    candidates = build_candidates(rows)

    authored_path = DATA / "authored_predictions.json"
    authored = load(authored_path) if authored_path.exists() else {}
    predictions = []
    for candidate in candidates:
        item = authored.get(candidate["key"])
        if not item:
            continue
        if item["selection"] != candidate["selection"]:
            raise ValueError(f"Prediction selection mismatch: {candidate['key']}")
        text = item["text"].strip()
        if words(text) < 30:
            raise ValueError(f"Prediction under 30 words: {candidate['key']}")
        row = candidate["row"]
        prediction = {key: value for key, value in candidate.items() if key != "row"}
        prediction.update({
            "text": text, "word_count": words(text), "facts": item.get("facts", []),
            "official_url": row["official_url"],
        })
        predictions.append(prediction)
    prediction_keys = {p["key"] for p in predictions}
    for row in rows:
        row["prediction_keys"] = sorted(p["key"] for p in predictions if p["fixture_id"] == row["id"])

    coverage = []
    for sport_id, sport in SPORTS.items():
        sport_rows = [r for r in rows if r["sport"] == sport]
        sport_candidates = [c for c in candidates if c["sport"] == sport]
        focus = [c for c in sport_candidates if c["focus_eligible"]]
        focus_written = [p for p in predictions if p["sport"] == sport and p["focus_eligible"]]
        listed = [e for e in listing["events"] if e["sport"] == sport and e["upcoming_at_capture"]]
        coverage.append({
            "sport": sport, "sport_id": sport_id, "slug": slug(sport),
            "olbg_upcoming_listed": len(listed), "official_fixtures": len(sport_rows),
            "priced": sum(bool(r.get("markets")) for r in sport_rows),
            "high": len(sport_candidates), "focus_high": len(focus),
            "written_predictions": len([p for p in predictions if p["sport"] == sport]),
            "five_pick_target_shortfall": max(0, 5 - len({p["fixture_id"] for p in focus_written})),
            "coverage_status": "priced from official evidence" if any(r.get("markets") for r in sport_rows) else "coverage gap — no defensible originated lines",
        })

    flags: list[dict[str, Any]] = []

    def flag(code: str, title: str, detail: str, url: str = "", row_id: str = "", sport: str = "") -> None:
        flags.append({"id": f"AF-{len(flags) + 1:03d}", "code": code, "title": title,
                      "detail": detail, "url": url, "row_id": row_id, "sport": sport, "status": "needs review"})

    for item in cap.manifest["items"]:
        if item["status"] != 200 or not item["bytes"]:
            flag("SOURCE_UNAVAILABLE", f"Source unavailable: {item['id']}",
                 f"HTTP {item['status']}; {item['error'] or 'empty response'}. No value from this response is used.", item["url"])
    for event in listing["events"]:
        if event["upcoming_at_capture"] and event["official_reconciliation"] != "matched":
            flag("OLBG_UNMATCHED", f"Unverified OLBG listing: {event['listed_name'] or event['listing_id']}",
                 "Participants, start and venue are not promoted into the official fixture table because no unique official fixture match was established. Official-source field intentionally blank.",
                 event["olbg_url"], event["listing_id"], event["sport"])
    for row in rows:
        for item in row["flags"]:
            flag(item["code"], f"{row['side_a']} vs {row['side_b']}", item["reason"], row["official_url"], row["id"], row["sport"])
    for candidate in candidates:
        row = candidate["row"]
        if not candidate["focus_eligible"]:
            flag("OUTSIDE_FOCUS_WINDOW", f"High pick outside −250…+10,000: {candidate['selection']}",
                 f"Our fair price is {candidate['decimal']:.3f} ({candidate['american']:+d}) at {candidate['probability']:.1%}. It remains visible but is not a focus pick.",
                 row["official_url"], row["id"], row["sport"])
        if candidate["key"] not in prediction_keys:
            missing = []
            if not any(r.get("team") == candidate.get("selected_team") for r in row["recent_results"]):
                missing.append("recent-result evidence for the selected side")
            if not row["player_facts"]: missing.append("relevant player evidence")
            if not missing: missing.append("authored prediction pending line-by-line editorial review")
            flag("PREDICTION_NOT_PUBLISHED", f"High prediction withheld: {candidate['selection']}",
                 "Missing: " + ", ".join(missing) + ". No generic replacement text was generated.",
                 row["official_url"], candidate["key"], row["sport"])
    for item in coverage:
        if item["five_pick_target_shortfall"]:
            flag("FIVE_PICK_SHORTFALL", f"{item['sport']}: fewer than five qualifying written focus matches",
                 f"Only {5 - item['five_pick_target_shortfall']} of the requested five are supported by fresh evidence and the odds/probability rules. The shortfall is not padded with weaker selections.",
                 "", "", item["sport"])
    flag("MODEL_LIMIT", "Model probabilities are estimates, not observed market prices",
         "All prices are margin-free 1/p calculations from the disclosed models. No injury, lineup, weather, goalie, rest or travel adjustment is inferred. Markets without adequate official inputs stay blank.")
    flag("LISTING_COMPLETENESS", "OLBG Load More cannot be used for an exhaustive crawl",
         listing["robots_policy"]["completeness_note"], "https://www.olbg.com/robots.txt")
    flag("GAELIC_SCOPE", "Gaelic Football retained only in the structural review queue",
         "OLBG separates Gaelic Football from association Football and American Football. The brief's word 'football' is ambiguous for this distinct sport, so no Gaelic line or pick is originated pending review.",
         "", "", "Gaelic Football")

    verification = []
    for row in rows:
        verification.append({
            "fixture_id": row["id"], "sport": row["sport"], "matchup": f"{row['side_a']} vs {row['side_b']}",
            "start_utc": row["start_utc"], "venue": row["venue"], "verification": row["verification"],
            "official_url": row["official_url"], "evidence_ids": [e["id"] for e in row["evidence"]],
            "sha256": [e["sha256"] for e in row["evidence"]], "priced": bool(row["markets"]),
            "pick": row["pick"]["selection"] if row.get("pick") else "",
            "confidence": row["pick"]["confidence"] if row.get("pick") else "",
            "flags": [f["code"] for f in row["flags"]],
        })
    public_candidates = [{key: value for key, value in c.items() if key != "row"} |
                         {"form": c["row"]["form"], "recent_results": c["row"]["recent_results"],
                          "player_facts": c["row"]["player_facts"], "official_url": c["row"]["official_url"],
                          "evidence": c["row"]["evidence"]} for c in candidates]
    summary = {
        "capture_id": cap.capture_id, "capture_generated_utc": cap.cutoff,
        "raw_responses_hash_verified": checked,
        "olbg_listed_upcoming": sum(e["upcoming_at_capture"] for e in listing["events"]),
        "official_fixtures": len(rows), "priced_fixtures": sum(bool(r["markets"]) for r in rows),
        "unpriced_official_fixtures": sum(not r["markets"] for r in rows),
        "match_winner_picks": sum(bool(r.get("pick")) for r in rows),
        "confidence": dict(Counter(r["pick"]["confidence"] for r in rows if r.get("pick"))),
        "high_selections": len(candidates), "high_focus": sum(c["focus_eligible"] for c in candidates),
        "written_predictions": len(predictions), "sports_priced": len({r["sport"] for r in rows if r["markets"]}),
        "sports_in_olbg_taxonomy": len(SPORTS), "flags": len(flags),
    }
    desk = {"schema": "olbg4.board-af.desk/v1", "board": "AF", "session": "0d3b826c",
            "capture_id": cap.capture_id, "generated_from_capture_utc": cap.cutoff,
            "window_end_utc": "2026-11-08T23:59:59Z", "summary": summary, "rows": rows}
    dump(DATA / "desk.json", desk)
    dump(DATA / "olbg_listing.json", listing)
    dump(DATA / "predictions.json", {"schema": "olbg4.board-af.predictions/v1", "count": len(predictions), "predictions": predictions})
    dump(DATA / "prediction_candidates.json", {"count": len(public_candidates), "candidates": public_candidates})
    dump(DATA / "coverage.json", {"coverage": coverage})
    dump(DATA / "flagged.json", {"count": len(flags), "flags": flags})
    dump(DATA / "verification.json", {"capture_id": cap.capture_id, "hash_verified_responses": checked, "rows": verification})
    dump(DATA / "sources.json", {"capture_id": cap.capture_id, "sources": cap.source_rows()})
    print(f"Board AF: {len(rows)} official fixtures; {summary['priced_fixtures']} priced; "
          f"{len(candidates)} High selections; {summary['high_focus']} focus; {len(predictions)} predictions; {len(flags)} flags; {checked} hashes")
    return desk


if __name__ == "__main__":
    build()

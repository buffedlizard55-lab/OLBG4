#!/usr/bin/env python3
"""Build the isolated Board AH desk from the latest committed official capture.

This script deliberately reads, but never rewrites, peer-session files.  The input is
Board AG's committed evidence-first desk.  Board AH narrows that desk to the exact
15 sports requested by the brief, keeps a blank/flagged record for categories where
no active qualified row was captured, and writes a deterministic machine-readable
snapshot for the static site.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "session-6846f1ab"
SOURCE_DIR = ROOT / "data" / "session-4885d641"
CAPTURE_DIR = SOURCE_DIR / "capture" / "20261022T210026Z"

# Keep this order equal to the user's requested list.  "Gaelic Sports" is a
# presentation label: the source capture calls the observed OLBG category Gaelic
# Football, while Hurling is separately listed and was excluded by the source desk.
REQUESTED_SPORTS = [
    "Golf",
    "Volleyball",
    "Rugby Union",
    "Cricket",
    "Snooker",
    "Darts",
    "Baseball",
    "Gaelic Sports",
    "Greyhounds",
    "Tennis",
    "Motor Racing",
    "Handball",
    "Ice Hockey",
    "Basketball",
    "Rugby League",
]

SOURCE_SPORTS = {
    "Golf",
    "Volleyball",
    "Rugby Union",
    "Cricket",
    "Snooker",
    "Darts",
    "Baseball",
    "Tennis",
    "Motor Racing",
    "Handball",
    "Ice Hockey",
    "Basketball",
    "Rugby League",
}

SOURCE_ALIASES = {
    "Gaelic Sports": ["Gaelic Football", "Hurling / GAA Hurling"],
    "Greyhounds": ["Greyhounds"],
}

SPORT_SLUGS = {
    "Golf": "golf",
    "Volleyball": "volleyball",
    "Rugby Union": "rugby-union",
    "Cricket": "cricket",
    "Snooker": "snooker",
    "Darts": "darts",
    "Baseball": "baseball",
    "Gaelic Sports": "gaelic-sports",
    "Greyhounds": "greyhounds",
    "Tennis": "tennis",
    "Motor Racing": "motor-racing",
    "Handball": "handball",
    "Ice Hockey": "ice-hockey",
    "Basketball": "basketball",
    "Rugby League": "rugby-league",
}

# OLBG sport IDs are taken from the captured inventory, not inferred from a row.
SPORT_IDS = {
    "Golf": 5,
    "Volleyball": 21,
    "Rugby Union": 9,
    "Cricket": 7,
    "Snooker": 8,
    "Darts": 15,
    "Baseball": 12,
    "Gaelic Sports": 25,
    "Greyhounds": 28,
    "Tennis": 3,
    "Motor Racing": 14,
    "Handball": 20,
    "Ice Hockey": 13,
    "Basketball": 4,
    "Rugby League": 10,
}


def load(name: str):
    return json.loads((SOURCE_DIR / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def domain(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def official_link(url: str) -> bool:
    # A source is a candidate governing-body/organiser link only if it is HTTPS
    # and not OLBG.  Host allowlisting is performed by verify.py against the
    # captured source registry; this lightweight predicate is for build labels.
    return bool(url.startswith("https://") and "olbg.com" not in domain(url))


def row_slug(row: dict) -> str:
    return row.get("sport_slug", row.get("sport", "").lower().replace(" ", "-"))


def normalise_flag(flag: dict, requested: str | None = None) -> dict:
    f = copy.deepcopy(flag)
    source_sport = f.get("sport", "")
    if source_sport.startswith("Gaelic Football"):
        target_sport = "Gaelic Sports"
    elif source_sport.startswith("Greyhound"):
        target_sport = "Greyhounds"
    else:
        target_sport = requested or source_sport
    return {
        "id": f.get("id", ""),
        "record_kind": "withheld_event",
        "sport": target_sport,
        "source_sport_label": source_sport,
        "competition": f.get("competition", ""),
        "event": f.get("event", ""),
        "start_utc": f.get("start_utc", ""),
        "category": f.get("category", ""),
        "verification_status": f.get("verification_status", ""),
        "match_winner_pick": "",
        "confidence": "",
        "originated_odds": "",
        "reason": f.get("reason", ""),
        "official_url": f.get("official_url", ""),
        "olbg_url": f.get("olbg_url", ""),
    }


def make_greyhound_gap(official_sources: dict, inventory: dict) -> dict:
    by_id = {item.get("id"): item for item in official_sources.get("items", [])}
    gbgb = by_id.get("gbgb_results", {})
    olbg = by_id.get("olbg_greyhounds_28", {})
    return {
        "id": "ah_gap_greyhounds_001",
        "record_kind": "scope_gap",
        "sport": "Greyhounds",
        "source_sport_label": "Greyhounds",
        "competition": "OLBG Greyhounds daily card",
        "event": "No qualifying upcoming race card parsed from the captured official feed",
        "start_utc": "",
        "category": "no_qualified_fixture",
        "verification_status": "official_page_captured_no_card_rows",
        "match_winner_pick": "",
        "confidence": "",
        "originated_odds": "",
        "reason": (
            "The OLBG Greyhounds hub was captured with zero event cards. The GBGB results page was also captured, "
            "but the committed source desk did not produce a dated upcoming card with runners and therefore publishes "
            "no race, line, pick, or confidence. This is intentionally blank rather than inferred from tips."
        ),
        "official_url": gbgb.get("final_url") or gbgb.get("url", "https://www.gbgb.org.uk/results/"),
        "olbg_url": olbg.get("final_url") or olbg.get("url", "https://www.olbg.com/betting-tips/Greyhounds/28"),
        "official_capture_status": gbgb.get("status"),
        "olbg_capture_status": olbg.get("status"),
        "olbg_card_count": next(
            (
                h.get("total_cards")
                for h in inventory.get("hub_summaries", [])
                if h.get("hub_id") == "olbg_greyhounds_28"
            ),
            0,
        ),
    }


def make_gaelic_gaps(flags: list[dict]) -> list[dict]:
    out = [normalise_flag(f, "Gaelic Sports") for f in flags if "Gaelic Football" in f.get("sport", "")]
    # If a future source capture removes the six event flags, preserve a single
    # explicit blank category record so the 15-sport site never silently drops it.
    if not out:
        out.append(
            {
                "id": "ah_gap_gaelic_001",
                "record_kind": "scope_gap",
                "sport": "Gaelic Sports",
                "source_sport_label": "Gaelic Football",
                "competition": "GAA fixtures",
                "event": "No active row retained",
                "start_utc": "",
                "category": "scope_ambiguity_or_no_qualified_fixture",
                "verification_status": "blank_pending_scope_review",
                "match_winner_pick": "",
                "confidence": "",
                "originated_odds": "",
                "reason": "No qualifying row was retained; the source desk quarantined the observed Gaelic Football listings under the prompt's football/hurling scope rule.",
                "official_url": "https://www.gaa.ie/fixtures-results/",
                "olbg_url": "https://www.olbg.com/betting-tips/Gaelic_Football/25",
            }
        )
    return out


def build() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    ag_desk = load("desk.json")
    ag_predictions = load("predictions.json")
    ag_flags = load("flagged.json")
    official_sources = load("official_sources.json")
    inventory = load("olbg_inventory.json")

    rows: list[dict] = []
    for source_row in ag_desk.get("rows", []):
        if source_row.get("sport") not in SOURCE_SPORTS:
            continue
        row = copy.deepcopy(source_row)
        row["requested_sport"] = row["sport"]
        row["requested_sport_slug"] = SPORT_SLUGS[row["sport"]]
        row["source_qualification"] = {
            "official_url_present": official_link(row.get("official_url", "")),
            "official_source_name": row.get("official_source_name", ""),
            "olbg_listing_matched": bool(row.get("olbg", {}).get("olbg_url")),
            "olbg_url": row.get("olbg", {}).get("olbg_url", ""),
        }
        rows.append(row)

    # Preserve the source prediction text and facts, but add the requested-sport
    # label.  A prediction is withheld if its prose explicitly recommends the
    # opposite side of the published selection.  The source text is not silently
    # rewritten: the conflict is published on Flagged for Review.
    row_by_id = {row.get("id"): row for row in rows}
    predictions: list[dict] = []
    withheld_predictions: list[dict] = []
    for source_prediction in ag_predictions.get("predictions", []):
        if source_prediction.get("sport") not in SOURCE_SPORTS:
            continue
        p = copy.deepcopy(source_prediction)
        selection = str(p.get("selection", ""))
        text = str(p.get("text", ""))
        selection_match = re.match(r"^(Over|Under)\s+([0-9]+(?:\.[0-9]+)?)", selection, re.I)
        conflict_reason = ""
        if selection_match:
            side = selection_match.group(1).lower()
            line = selection_match.group(2)
            opposite = "under" if side == "over" else "over"
            same_phrase = f"{side} {line}"
            opposite_phrase = f"{opposite} {line}"
            if same_phrase not in text.lower() and opposite_phrase in text.lower():
                conflict_reason = f"Published selection is {selection}, but the authored text explicitly says {opposite_phrase.title()}; the text was not rewritten."
        if conflict_reason:
            source_row = row_by_id.get(p.get("row_id"), {})
            withheld_predictions.append(
                {
                    "id": f"ah_prediction_conflict_{p.get('pred_key','unknown')}",
                    "record_kind": "prediction_quality",
                    "sport": p.get("sport", ""),
                    "source_sport_label": p.get("sport", ""),
                    "competition": p.get("competition", ""),
                    "event": p.get("matchup", ""),
                    "start_utc": p.get("start_utc", ""),
                    "category": "prediction_selection_conflict",
                    "verification_status": "withheld_from_publication",
                    "match_winner_pick": "",
                    "confidence": "",
                    "originated_odds": "",
                    "reason": conflict_reason,
                    "official_url": p.get("official_url", "") or source_row.get("official_url", ""),
                    "olbg_url": source_row.get("olbg", {}).get("olbg_url", ""),
                    "row_id": p.get("row_id", ""),
                    "pred_key": p.get("pred_key", ""),
                }
            )
            continue
        p["requested_sport"] = p["sport"]
        p["requested_sport_slug"] = SPORT_SLUGS[p["sport"]]
        predictions.append(p)

    rows_by_sport = defaultdict(list)
    for row in rows:
        rows_by_sport[row["sport"]].append(row)
    predictions_by_sport = Counter(p["sport"] for p in predictions)

    flags: list[dict] = []
    for flag in ag_flags.get("event_flags", []):
        source_label = flag.get("sport", "")
        if "Gaelic Football" in source_label:
            flags.append(normalise_flag(flag, "Gaelic Sports"))
        elif source_label in SOURCE_SPORTS:
            flags.append(normalise_flag(flag, source_label))
    flags.extend(withheld_predictions)
    flags.extend(make_gaelic_gaps(ag_flags.get("event_flags", [])))
    flags.append(make_greyhound_gap(official_sources, inventory))

    # A separate audit finding records official-only rows.  They remain in the
    # desk because the requested scope is the OLBG sport category, while the
    # underlying fixture is sourced from the governing body.  No value is copied
    # into an OLBG field when the listing was not in the capture.
    for row in rows:
        if not row.get("olbg", {}).get("olbg_url"):
            flags.append(
                {
                    "id": f"ah_olbg_gap_{row['id']}",
                    "record_kind": "audit_finding",
                    "sport": row["sport"],
                    "source_sport_label": row["sport"],
                    "competition": row.get("competition", ""),
                    "event": row.get("matchup", ""),
                    "start_utc": row.get("start_utc", ""),
                    "category": "official_row_not_matched_to_olbg_card",
                    "verification_status": "official_schedule_only_in_capture",
                    "match_winner_pick": "",
                    "confidence": "",
                    "originated_odds": "",
                    "reason": "The official schedule row is retained, but no matching OLBG event URL was present in the captured OLBG inventory; the blank OLBG link is intentional.",
                    "official_url": row.get("official_url", ""),
                    "olbg_url": "",
                    "row_id": row["id"],
                }
            )

    coverage = []
    for sport in REQUESTED_SPORTS:
        sport_rows = rows_by_sport.get(sport, [])
        # The two presentation categories do not have active source rows in AG.
        if sport in ("Gaelic Sports", "Greyhounds"):
            sport_flags = [f for f in flags if f["sport"] == sport]
        else:
            sport_flags = [f for f in flags if f["sport"] == sport]
        match_rows = [r for r in sport_rows if r.get("row_kind") == "match"]
        outright_rows = [r for r in sport_rows if r.get("row_kind") == "outright"]
        with_markets = [r for r in sport_rows if r.get("markets")]
        high = predictions_by_sport.get(sport, 0)
        coverage.append(
            {
                "sport": sport,
                "slug": SPORT_SLUGS[sport],
                "olbg_sport_id": SPORT_IDS[sport],
                "source_labels": [sport] if sport in SOURCE_SPORTS else SOURCE_ALIASES.get(sport, []),
                "rows": len(sport_rows),
                "match_rows": len(match_rows),
                "outright_rows": len(outright_rows),
                "priced_rows": len(with_markets),
                "high_predictions": high,
                "target_high_predictions": 5,
                "high_target_status": "met" if high >= 5 else "no qualifying five-pick set captured",
                "official_rows": sum(bool(r.get("official_url")) for r in sport_rows),
                "olbg_matched_rows": sum(bool(r.get("olbg", {}).get("olbg_url")) for r in sport_rows),
                "flagged_records": len(sport_flags),
                "status": "active desk" if sport_rows else "blank and flagged",
            }
        )

    # The reverse-engineering layer is sourced from captured OLBG hub bytes.
    hubs = []
    requested_ids = set(SPORT_IDS.values())
    for hub in inventory.get("hub_summaries", []):
        # Keep all hubs because the page documents the observed URL/market
        # surface, while marking the requested sport hubs separately.
        hubs.append(
            {
                **hub,
                "requested_sport": next(
                    (s for s, sid in SPORT_IDS.items() if sid == _hub_sport_id(hub.get("hub_id", ""))),
                    "",
                ),
            }
        )

    taxonomy = {
        "schema": "olbg4.board-ah.taxonomy/1",
        "source_session": "arena/4885d641-olbg4",
        "capture_stamp": inventory.get("capture_stamp", ""),
        "capture_cutoff_utc": inventory.get("cutoff_utc", ""),
        "requested_sports": REQUESTED_SPORTS,
        "sport_ids": SPORT_IDS,
        "source_aliases": SOURCE_ALIASES,
        "observed_market_types": inventory.get("market_types_observed", {}),
        "hub_summaries": hubs,
        "excluded_sport_taxonomy": inventory.get("excluded_sport_taxonomy", []),
        "gaelic_football_quarantined_count": len(inventory.get("gaelic_football_quarantined", [])),
    }

    official_records = []
    seen_official = set()
    for row in rows:
        url = row.get("official_url", "")
        if url in seen_official or not url:
            continue
        seen_official.add(url)
        official_records.append(
            {
                "url": url,
                "domain": domain(url),
                "source_name": row.get("official_source_name", ""),
                "row_count": sum(r.get("official_url") == url for r in rows),
                "sports": sorted({r["sport"] for r in rows if r.get("official_url") == url}),
            }
        )
    official_records.sort(key=lambda x: (x["domain"], x["url"]))

    sources = {
        "schema": "olbg4.board-ah.sources/1",
        "source_session": "arena/4885d641-olbg4",
        "capture_cutoff_utc": inventory.get("cutoff_utc", ""),
        "official_sources_used_by_rows": official_records,
        "olbg_hubs": hubs,
        "capture_manifest_items": [
            {
                "id": item.get("id", ""),
                "url": item.get("url", ""),
                "final_url": item.get("final_url", ""),
                "status": item.get("status"),
                "bytes": item.get("bytes", 0),
                "sha256": item.get("sha256", ""),
                "fetched_utc": item.get("fetched_utc", ""),
            }
            for item in official_sources.get("items", [])
        ],
    }

    desk = {
        "schema": "olbg4.board-ah.desk/1",
        "source_session": "arena/4885d641-olbg4",
        "source_capture_stamp": inventory.get("capture_stamp", ""),
        "source_cutoff_utc": inventory.get("cutoff_utc", ""),
        "requested_sports": REQUESTED_SPORTS,
        "summary": {
            "rows": len(rows),
            "match_rows": sum(r.get("row_kind") == "match" for r in rows),
            "outright_rows": sum(r.get("row_kind") == "outright" for r in rows),
            "priced_rows": sum(bool(r.get("markets")) for r in rows),
            "markets_in_rows": sum(len(r.get("markets", {})) for r in rows),
            "predictions": len(predictions),
            "flagged_records": len(flags),
            "sports_with_rows": sum(bool(rows_by_sport.get(s)) for s in REQUESTED_SPORTS),
            "sports_requested": len(REQUESTED_SPORTS),
        },
        "rows": rows,
    }
    prediction_payload = {
        "schema": "olbg4.board-ah.predictions/1",
        "source_session": "arena/4885d641-olbg4",
        "source_cutoff_utc": inventory.get("cutoff_utc", ""),
        "rules": {
            "minimum_words": 30,
            "required_confidence": "High",
            "american_odds_window": [-250, 10000],
            "daily_target_per_requested_sport": 5,
            "note": "A category with fewer than five qualifying source predictions is shown as a shortfall; no text is invented.",
        },
        "count": len(predictions),
        "by_sport": dict(predictions_by_sport),
        "withheld": withheld_predictions,
        "predictions": predictions,
    }
    coverage_payload = {
        "schema": "olbg4.board-ah.coverage/1",
        "source_session": "arena/4885d641-olbg4",
        "source_cutoff_utc": inventory.get("cutoff_utc", ""),
        "sports": coverage,
    }
    flagged_payload = {
        "schema": "olbg4.board-ah.flagged/1",
        "source_session": "arena/4885d641-olbg4",
        "source_cutoff_utc": inventory.get("cutoff_utc", ""),
        "blank_rule": "Withheld events have blank pick, confidence, and originated odds. Audit findings do not alter active desk rows.",
        "count": len(flags),
        "by_category": dict(Counter(f.get("category", "") for f in flags)),
        "items": flags,
    }

    inputs = [
        SOURCE_DIR / "desk.json",
        SOURCE_DIR / "predictions.json",
        SOURCE_DIR / "flagged.json",
        SOURCE_DIR / "official_sources.json",
        SOURCE_DIR / "olbg_inventory.json",
        CAPTURE_DIR / "manifest.json",
    ]
    manifest = {
        "schema": "olbg4.board-ah.manifest/1",
        "session": "arena/6846f1ab-olbg4",
        "source_session": "arena/4885d641-olbg4",
        "source_capture_stamp": inventory.get("capture_stamp", ""),
        "source_cutoff_utc": inventory.get("cutoff_utc", ""),
        "requested_sports": REQUESTED_SPORTS,
        "input_files": [
            {"path": str(p.relative_to(ROOT)), "sha256": sha256(p), "bytes": p.stat().st_size}
            for p in inputs
        ],
        "capture_manifest_target_count": len(
            json.loads((CAPTURE_DIR / "manifest.json").read_text(encoding="utf-8")).get("items", [])
        ),
        "capture_manifest_http_200_nonempty": official_sources.get("http_200_nonempty", 0),
        "published_rows": len(rows),
        "published_predictions": len(predictions),
        "published_flagged_records": len(flags),
    }

    outputs = {
        "desk.json": desk,
        "predictions.json": prediction_payload,
        "coverage.json": coverage_payload,
        "flagged.json": flagged_payload,
        "taxonomy.json": taxonomy,
        "sources.json": sources,
        "manifest.json": manifest,
    }
    for name, payload in outputs.items():
        (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "status": "built",
                "rows": len(rows),
                "predictions": len(predictions),
                "flagged": len(flags),
                "sports_with_rows": sum(bool(rows_by_sport.get(s)) for s in REQUESTED_SPORTS),
            },
            indent=2,
        )
    )
    return outputs


def _hub_sport_id(hub_id: str) -> int | None:
    # Hub IDs are captured as olbg_<name>_<numeric id>; sub-hubs may have a
    # non-numeric suffix and are intentionally left without a sport mapping.
    tail = hub_id.rsplit("_", 1)[-1]
    return int(tail) if tail.isdigit() else None


if __name__ == "__main__":
    build()

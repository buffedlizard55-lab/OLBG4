#!/usr/bin/env python3
"""Build an evidence-first audit of the most recent committed 15-sport desk.

This intentionally does not upgrade historical claims into live recommendations. It
checks snapshot hashes and arithmetic, filters by a fixed UTC review time, and only
attaches a governing-body URL to an OLBG event when the participants/time were checked
against that official event page during this session.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data" / "session-48de8c1d"
CAPTURE_DIR = SOURCE_DIR / "capture" / "20261023T213547Z"
OUT = ROOT / "data" / "session-265b28e5" / "audit.json"

# Freeze the review instant so a rebuild is deterministic and can be independently checked.
AS_OF_UTC = "2026-10-24T17:10:06Z"
CUTOFF_UTC = "2026-10-23T21:40:00Z"
SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts",
    "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing",
    "Handball", "Ice Hockey", "Basketball", "Rugby League",
]

# These four current OLBG event IDs were individually cross-checked against the
# corresponding official source pages on 2026-10-24. The URLs are not bookmaker feeds.
MANUAL_CROSSWALKS = {
    "188838": {
        "url": "https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-england-for-t20is-odi-tri-series-and-tests.html",
        "source_name": "Pakistan Cricket Board (PCB)",
        "row_id": "FB-CRK-PAKENG-OD4",
        "official_start_time_confirmed": False,
        "note": "PCB's 2026 tri-series schedule lists Pakistan v England as the fourth ODI on 25 October at Gaddafi Stadium, Lahore; it does not state a start time in the fetched schedule. The official PCB result article also reports Pakistan's 87-run win over England on 20 October and Arafat Minhas's 6-40 and 59.",
        "additional_urls": [
            "https://www.pcb.com.pk/news-detail/arafat-minhas-6-40-and-59-sink-england-as-pakistan-win-consecutive-games-in-odi-tri-series.html"
        ],
    },
    "3530": {
        "url": "https://gaacork.ie/event/mccarthy-insurance-group-premier-senior-football-championship-final/",
        "source_name": "Cork GAA",
        "row_id": "FB-GAA-CORK-SFC",
        "official_start_time_confirmed": True,
        "note": "Cork GAA's event page lists Nemo Rangers v St Finbarrs on 25 October at 16:00 at SuperValu Páirc Uí Chaoimh and gives both teams' route to the final and recent knockout scores.",
        "additional_urls": [],
    },
    "714": {
        "url": "https://kilkennygaa.ie/clubs/ballyhale-shamrocks/",
        "source_name": "Kilkenny GAA",
        "row_id": "FB-GAA-KK-SHC",
        "official_start_time_confirmed": True,
        "note": "Kilkenny GAA's fixture page lists Shamrocks Ballyhale v Tullaroan on 25 October at 13:45 at UPMC Nowlan Park.",
        "additional_urls": [],
    },
    "12133": {
        "url": "https://ehfcl.eurohandball.com/men/2026-27/matches/details/202711020101055/MontpellierHandball-DinamoBucuresti/",
        "source_name": "European Handball Federation (EHF)",
        "row_id": "FB-HB-EHF-04",
        "official_start_time_confirmed": True,
        "note": "EHF's match detail page lists Montpellier Handball v Dinamo Bucuresti on 29 October at 20:45 CET at FDI Stadium, Montpellier (19:45Z).",
        "additional_urls": [
            "https://ehfcl.eurohandball.com/men/2026-27/standings/"
        ],
    },
}

# This is not an official-source allowlist proof. It only highlights a known provenance
# defect in which the cited governing-body URL was paired with an OLBG capture target.
OLBG_CAPTURE_TARGETS = {"olbg_rugby_union", "olbg_cricket"}
LIVE_HUB_SPOT_CHECKS = [
    {
        "sport": "Volleyball", "url": "https://www.olbg.com/betting-tips/Volleyball/21",
        "checked_date_utc": "2026-10-24", "exact_fetch_time_available": False,
        "note": "Fetched hub HTML lists current-day events and tipster selections, including UVC Graz W v Sportunion St Polten W, SWD Duren v WWK Volleys Munchen and additional event IDs. Relative time labels are not normalized to a precise UTC time in this audit.",
    },
    {
        "sport": "Cricket", "url": "https://www.olbg.com/betting-tips/Cricket/7",
        "checked_date_utc": "2026-10-24", "exact_fetch_time_available": False,
        "note": "Fetched hub HTML lists Toronto Kings v Vancouver Guardians T20 and Pakistan v England One Day Match with tipster-consensus summaries, plus later fixtures. The page's Today/Tomorrow labels are not persisted as a UTC-timestamped capture.",
    },
    {
        "sport": "Handball", "url": "https://www.olbg.com/betting-tips/Handball/20",
        "checked_date_utc": "2026-10-24", "exact_fetch_time_available": False,
        "note": "Fetched hub HTML lists current-day and later handball events, including HBW Balingen-Weilstetten v MT Melsungen and Montpellier v Dinamo Bucuresti. Relative time labels are not saved as exact UTC observations.",
    },
]
BANNED_PREDICTION_WORDS = re.compile(r"\b(model\w*|verif\w*)\b", re.I)


def parse_utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def event_id_from_url(url: str) -> str:
    return parse_qs(urlsplit(url).query).get("event_id", [""])[0]


def american_from_probability(p: float) -> float:
    if p < 0.5:
        return 100.0 * (1.0 - p) / p
    return -100.0 * p / (1.0 - p)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    desk = read_json(SOURCE_DIR / "desk.json")
    predictions_doc = read_json(SOURCE_DIR / "predictions.json")
    taxonomy = read_json(SOURCE_DIR / "olbg_taxonomy.json")
    manifest = read_json(CAPTURE_DIR / "manifest.json")
    now = parse_utc(AS_OF_UTC)

    capture_by_id = {record["id"]: record for record in manifest["records"]}
    capture_checks = []
    for record in manifest["records"]:
        if record.get("status") != 200:
            continue
        path = CAPTURE_DIR / record["file"]
        if not path.exists():
            capture_checks.append({"id": record["id"], "status": "missing", "expected_sha256": record["sha256"]})
            continue
        with gzip.open(path, "rb") as payload:
            digest = hashlib.sha256(payload.read()).hexdigest()
        capture_checks.append({
            "id": record["id"], "url": record.get("url", ""), "http_status": record.get("status"),
            "status": "pass" if digest == record["sha256"] else "hash_mismatch",
            "expected_sha256": record["sha256"], "actual_sha256": digest,
        })

    # Index OLBG observations by exact event ID; do not use fuzzy participant matching.
    olbg_events_by_id = {}
    olbg_events = []
    for hub in taxonomy.get("in_scope_hubs", []):
        sport = hub.get("sport", "")
        for event in hub.get("events", []):
            item = dict(event)
            item["sport"] = sport
            olbg_events_by_id.setdefault(str(event.get("event_id", "")), []).append(item)
            olbg_events.append(item)

    current_olbg = []
    stale_olbg_unexpired = []
    for event in olbg_events:
        if event.get("expired_flag") != "0":
            continue
        if parse_utc(event["start_utc"]) > now:
            event_id = str(event.get("event_id", ""))
            crosswalk = MANUAL_CROSSWALKS.get(event_id)
            official_source = ""
            crosswalk_status = "not independently matched"
            row_id = ""
            if crosswalk:
                official_row = next((r for r in desk["rows"] if r["id"] == crosswalk["row_id"]), None)
                matches_time = bool(official_row and official_row.get("start_utc") == event.get("start_utc"))
                matches_sport = bool(official_row and official_row.get("sport") == event.get("sport"))
                if matches_time and matches_sport:
                    official_source = crosswalk["url"]
                    crosswalk_status = "official participants/date checked; official start time confirmed" if crosswalk.get("official_start_time_confirmed") else "official participants/date checked; official start time not stated on page"
                    row_id = crosswalk["row_id"]
                else:
                    crosswalk_status = "crosswalk failed sport/time comparison"
            item = {
                "sport": event["sport"],
                "event_id": event_id,
                "event_name": event.get("event_name", ""),
                "start_utc": event.get("start_utc", ""),
                "market_alias": event.get("market_alias", ""),
                "selection": event.get("selection", ""),
                "olbg_decimal_odds": event.get("decimal_odds"),
                "olbg_american_odds": event.get("american_odds"),
                "tipster_consensus": f"{event.get('win_tips', '')}/{event.get('win_tips_count', '')} ({event.get('tipster_consensus_pct', '')}%)",
                "olbg_url": event.get("event_url", ""),
                "official_source_url": official_source,
                "official_source_name": crosswalk["source_name"] if official_source else "",
                "official_start_time_confirmed": bool(crosswalk and official_source and crosswalk.get("official_start_time_confirmed")),
                "crosswalk_status": crosswalk_status,
                "matched_desk_row_id": row_id,
                "capture_cutoff_utc": taxonomy.get("captured_utc", ""),
                "flag_id": "" if official_source else "GF-F06",
            }
            current_olbg.append(item)
        else:
            stale_olbg_unexpired.append(event)

    desk_rows = []
    row_by_id = {}
    market_rows = []
    arithmetic_errors = []
    olbg_refs_total = 0
    olbg_refs_future = 0
    olbg_ref_mismatches = []
    olbg_capture_mismatch_rows = []
    for row in desk["rows"]:
        row_by_id[row["id"]] = row
        record = capture_by_id.get(row.get("capture_target_id", ""), {})
        capture_valid = bool(record and record.get("status") == 200 and record.get("sha256") == row.get("capture_sha256"))
        started = parse_utc(row["start_utc"]) <= now
        ref = row.get("olbg_ref")
        manual_match = next((item for item in MANUAL_CROSSWALKS.values() if item["row_id"] == row["id"]), None)
        ref_id = event_id_from_url(ref["event_url"]) if ref and ref.get("event_url") else ""
        ref_event_candidates = olbg_events_by_id.get(ref_id, [])
        ref_event = ref_event_candidates[0] if ref_event_candidates else None
        ref_time_match = bool(ref_event and row.get("start_utc") == ref_event.get("start_utc"))
        if ref:
            olbg_refs_total += 1
            if not started:
                olbg_refs_future += 1
            if not ref_event or not ref_time_match:
                olbg_ref_mismatches.append({
                    "row_id": row["id"], "sport": row["sport"], "start_utc": row["start_utc"],
                    "row_match": row["match"], "event_id": ref_id,
                    "olbg_event_name": ref_event.get("event_name", "") if ref_event else "",
                    "olbg_start_utc": ref_event.get("start_utc", "") if ref_event else "",
                    "olbg_url": ref.get("event_url", ""), "official_source_url": row.get("official_source_url", ""),
                })
        if row.get("capture_target_id") in OLBG_CAPTURE_TARGETS:
            olbg_capture_mismatch_rows.append({
                "row_id": row["id"], "sport": row["sport"], "match": row["match"],
                "official_source_url": row.get("official_source_url", ""),
                "capture_target_id": row.get("capture_target_id"),
                "capture_url": record.get("url", ""),
            })

        active = row.get("actionable_pick") or {}
        p = active.get("fair_prob")
        prob_tier = "ungraded"
        if isinstance(p, (int, float)):
            prob_tier = "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")
        desk_item = {
            "id": row["id"], "sport": row["sport"], "competition": row["competition"],
            "match": row["match"], "start_utc": row["start_utc"], "date_utc": row["date_utc"],
            "venue": row.get("venue", ""), "time_status": "started_or_elapsed" if started else "future_at_review_time",
            "verification_status_in_source_desk": row.get("verification_status", ""),
            "official_source_url": row.get("official_source_url", ""),
            "official_source_name": row.get("official_source_name", ""),
            "manual_match_source_url": manual_match["url"] if manual_match else "",
            "manual_match_source_name": manual_match["source_name"] if manual_match else "",
            "manual_source_start_time_confirmed": bool(manual_match and manual_match.get("official_start_time_confirmed")),
            "manual_crosswalk_status": "manually matched to an official fixture source" if manual_match else "not manually matched to a current OLBG event",
            "manual_crosswalk_note": manual_match.get("note", "") if manual_match else "",
            "capture_target_id": row.get("capture_target_id", ""),
            "capture_target_url": record.get("url", ""),
            "capture_sha256_matches": capture_valid,
            "capture_sha256": row.get("capture_sha256", ""),
            "olbg_candidate_ref": ref,
            "olbg_candidate_event_id": ref_id,
            "olbg_candidate_start_matches": ref_time_match,
            "match_winner_pick_in_source_desk": row.get("match_winner_pick", ""),
            "match_winner_prob_in_source_desk": row.get("match_winner_prob"),
            "match_winner_fair_american_in_source_desk": row.get("match_winner_american"),
            "actionable_selection_in_source_desk": active.get("selection", ""),
            "actionable_market_in_source_desk": active.get("market_label", ""),
            "actionable_fair_prob_in_source_desk": p,
            "actionable_fair_american_in_source_desk": active.get("fair_american_str", ""),
            "original_confidence_label": row.get("confidence", ""),
            "probability_tier_at_70_55_rules": prob_tier,
            "market_count_in_source_desk": len(row.get("markets", [])),
            "source_facts_and_model_inputs_independently_reconciled": False,
            "row_evidence_status": "official event source manually checked" if manual_match else "prior citation carried forward; event content not rechecked",
            "flag_id": "GF-F07" if row.get("capture_target_id") in OLBG_CAPTURE_TARGETS else ("GF-F01" if not manual_match else ""),
        }
        desk_rows.append(desk_item)

        for market in row.get("markets", []):
            for outcome in market.get("outcomes", []):
                prob = outcome.get("fair_prob")
                decimal = outcome.get("fair_decimal")
                american = outcome.get("fair_american")
                if isinstance(prob, (int, float)) and prob > 0:
                    expected_decimal = 1.0 / prob
                    expected_american = american_from_probability(prob)
                    decimal_ok = isinstance(decimal, (int, float)) and abs(decimal - expected_decimal) <= 0.002
                    american_ok = isinstance(american, (int, float)) and abs(american - expected_american) <= 1.5
                    # At exactly p=.5, +100 and -100 are the same fair decimal price.
                    if abs(prob - 0.5) < 1e-12 and american == 100:
                        american_ok = True
                    if not (decimal_ok and american_ok):
                        arithmetic_errors.append({"row_id": row["id"], "market_key": market.get("market_key"), "selection": outcome.get("selection"), "probability": prob, "decimal": decimal, "american": american})
                market_rows.append({
                    "row_id": row["id"], "sport": row["sport"], "match": row["match"],
                    "start_utc": row["start_utc"], "time_status": "started_or_elapsed" if started else "future_at_review_time",
                    "market_key": market.get("market_key", ""), "market_label": market.get("market_label", ""),
                    "basis_in_source_desk": market.get("basis", ""),
                    "selection": outcome.get("selection", ""), "fair_probability": prob,
                    "fair_decimal": decimal, "fair_american": outcome.get("fair_american_str", ""),
                    "official_source_url": row.get("official_source_url", ""),
                    "source_capture_cutoff_utc": desk.get("generated_from_capture_utc", ""),
                    "status": "historical estimate; assumptions not independently reconciled",
                })

    predictions = predictions_doc.get("predictions", [])
    pred_texts = [p.get("prediction_text", "") for p in predictions]
    seen_texts = set()
    pred_audit = []
    numeric_candidates = []
    prediction_start_past = 0
    high_below_70 = 0
    high_ge_70 = 0
    prediction_math_window = 0
    for prediction in predictions:
        row = row_by_id.get(prediction.get("row_id", ""), {})
        future = parse_utc(prediction["start_utc"]) > now
        if not future:
            prediction_start_past += 1
        probability = prediction.get("fair_prob")
        odds = prediction.get("fair_american")
        in_window = isinstance(odds, (int, float)) and -250 <= odds <= 10000
        ge70 = isinstance(probability, (int, float)) and probability >= 0.70
        if prediction.get("confidence") == "High" and not ge70:
            high_below_70 += 1
        if prediction.get("confidence") == "High" and ge70:
            high_ge_70 += 1
        if in_window:
            prediction_math_window += 1
        text = prediction.get("prediction_text", "")
        unique = text not in seen_texts
        seen_texts.add(text)
        link = prediction.get("official_source_url", "")
        row_ref = row.get("olbg_ref")
        crosswalked = bool(row_ref and row_ref.get("event_url") and row.get("start_utc") == next((e.get("start_utc") for e in olbg_events_by_id.get(event_id_from_url(row_ref["event_url"]), [])), None))
        numeric = bool(future and ge70 and in_window)
        item = {
            "prediction_id": prediction.get("prediction_id", ""), "row_id": prediction.get("row_id", ""),
            "sport": prediction.get("sport", ""), "match": prediction.get("match", ""),
            "start_utc": prediction.get("start_utc", ""), "future_at_review_time": future,
            "market": prediction.get("market", ""), "selection": prediction.get("selection", ""),
            "fair_probability_in_source_desk": probability, "fair_american_in_source_desk": odds,
            "american_price_in_requested_window": in_window, "probability_at_least_70_percent": ge70,
            "source_desk_label": prediction.get("confidence", ""),
            "word_count": len(text.split()), "unique_text": unique,
            "banned_internal_term_present": bool(BANNED_PREDICTION_WORDS.search(text)),
            "official_source_url": link,
            "olbg_match_crosswalked": crosswalked,
            "text_claims_independently_reconciled": False,
            "injury_or_availability_claim_individually_sourced": False,
            "numeric_screen_candidate": numeric,
            "release_ready": False,
            "release_block_reason": "No current OLBG event crosswalk for this selection and prediction claims/line inputs have not been independently reconciled.",
        }
        pred_audit.append(item)
        if numeric:
            numeric_candidates.append(item)

    # Construct 15-sport counts, including explicit zero-coverage rows.
    sports_rows = []
    olbg_hub_by_sport = {hub.get("sport"): hub.get("hub_url", "") for hub in taxonomy.get("in_scope_hubs", [])}
    for sport in SPORTS:
        desk_sport = [r for r in desk_rows if r["sport"] == sport]
        olbg_sport = [e for e in current_olbg if e["sport"] == sport]
        pred_sport = [p for p in pred_audit if p["sport"] == sport]
        sports_rows.append({
            "sport": sport,
            "olbg_hub_url": olbg_hub_by_sport.get(sport, ""),
            "slug": re.sub(r"[^a-z0-9]+", "-", sport.lower()).strip("-"),
            "olbg_future_event_rows_in_snapshot": len(olbg_sport),
            "olbg_future_unique_events_in_snapshot": len({e["event_id"] for e in olbg_sport}),
            "source_desk_rows": len(desk_sport),
            "source_desk_rows_future_at_review_time": sum(r["time_status"] == "future_at_review_time" for r in desk_sport),
            "source_desk_rows_started_or_elapsed": sum(r["time_status"] == "started_or_elapsed" for r in desk_sport),
            "original_predictions": len(pred_sport),
            "numeric_screen_candidates": sum(p["numeric_screen_candidate"] for p in pred_sport),
            "release_ready_predictions": 0,
        })

    # Exact IDs and counts are an audit output, not user-facing recommendations.
    current_event_ids = {e["event_id"] for e in current_olbg}
    current_sports_with_events = {e["sport"] for e in current_olbg}
    exact_crosswalk_count = sum(bool(e["official_source_url"]) for e in current_olbg)
    stale_official_rows = sum(r["time_status"] == "started_or_elapsed" for r in desk_rows)
    future_official_rows = sum(r["time_status"] == "future_at_review_time" for r in desk_rows)
    capture_pass = sum(c["status"] == "pass" for c in capture_checks)
    capture_fail = [c for c in capture_checks if c["status"] != "pass"]

    findings = [
        {
            "id": "GF-F01", "severity": "critical", "title": "The latest full-scope capture is not live/current",
            "status": "needs_review", "affected_count": len(current_olbg),
            "detail": f"OLBG and official data were captured at {taxonomy.get('captured_utc')} / {desk.get('generated_from_capture_utc')}. This review is frozen at {AS_OF_UTC}; an OLBG row with a future timestamp is not proof that the market is still open now.",
            "official_source_urls": ["https://www.olbg.com/betting-tips"],
            "evidence_file": "data/session-48de8c1d/capture/20261023T213547Z/manifest.json",
        },
        {
            "id": "GF-F02", "severity": "critical", "title": "Most source-desk High labels do not meet the 70% screen",
            "status": "needs_review", "affected_count": high_below_70,
            "detail": f"Of {len(predictions)} prediction cards labelled High, {high_below_70} have a stated selection probability below 70%; {high_ge_70} reach 70%. The source script grades a composite confidence index, not the selected outcome probability.",
            "official_source_urls": ["https://www.pgatour.com/leaderboard", "https://api-web.nhle.com/v1/standings/now"],
            "evidence_file": "scripts/session-48de8c1d/originate.py",
        },
        {
            "id": "GF-F03", "severity": "critical", "title": "Old prediction cards include matches that had already started",
            "status": "needs_review", "affected_count": prediction_start_past,
            "detail": f"{prediction_start_past} of {len(predictions)} prediction start times are at or before the review time {AS_OF_UTC}; they must not appear as upcoming picks.",
            "official_source_urls": ["https://www.nhl.com/schedule", "https://www.nba.com/games"],
            "evidence_file": "data/session-48de8c1d/predictions.json",
        },
        {
            "id": "GF-F04", "severity": "critical", "title": "No prediction passes the complete release gate",
            "status": "needs_review", "affected_count": len(numeric_candidates),
            "detail": f"{len(numeric_candidates)} future text cards pass the numeric p≥70% and American-odds window screen, but {sum(p['olbg_match_crosswalked'] for p in numeric_candidates)} have an exact current OLBG crosswalk. Prediction claims and line inputs were not independently reconciled, so 0 are release-ready.",
            "official_source_urls": ["https://www.olbg.com/betting-tips"],
            "evidence_file": "data/session-48de8c1d/predictions.json",
        },
        {
            "id": "GF-F05", "severity": "high", "title": "The captured OLBG fixture list has no future rows in six requested categories",
            "status": "needs_review", "affected_count": len(SPORTS) - len(current_sports_with_events),
            "detail": f"Only {len(current_sports_with_events)} of the 15 requested sports have a row with a start time after the review instant in the 23 October OLBG capture. Zero does not prove that OLBG has no such market today; it means this snapshot supplies no future row.",
            "official_source_urls": ["https://www.olbg.com/betting-tips"],
            "evidence_file": "data/session-48de8c1d/olbg_taxonomy.json",
        },
        {
            "id": "GF-F06", "severity": "high", "title": "Most official schedule rows are not reconciled to an OLBG event",
            "status": "needs_review", "affected_count": len(desk_rows) - olbg_refs_total,
            "detail": f"The source desk contains {len(desk_rows)} schedule rows, but only {olbg_refs_total} have an OLBG reference, and the reference-generation routine uses first-word substring checks. One explicit future reference is wrong: {next((m['row_id'] for m in olbg_ref_mismatches if m['row_id'] == 'FB-CRK-NZIND-T3'), 'the New Zealand v India 3rd-T20 row')} points to event 188832, whose OLBG timestamp is 24 October rather than the desk row's 27 October.",
            "official_source_urls": ["https://www.olbg.com/betting-tips/Cricket/All_Cricket/All_Events/New_Zealand_vs_India_2nd_T20_Match/7?event_id=188832", "https://www.nzc.nz/"],
            "evidence_file": "data/session-48de8c1d/olbg_taxonomy.json",
        },
        {
            "id": "GF-F07", "severity": "high", "title": "Some official citations are paired with an OLBG capture as their evidence",
            "status": "needs_review", "affected_count": len(olbg_capture_mismatch_rows),
            "detail": "Three United Rugby Championship rows and one Pakistan v England cricket row point to an OLBG hub capture target rather than a captured governing-body event source. A source URL string and a capture hash do not establish that the captured bytes support the cited row. The PCB's official schedule is linked on the current OLBG list for Pakistan v England; the three URC rows remain unreconciled.",
            "official_source_urls": ["https://www.pcb.com.pk/press-release-detail/pakistan-to-host-sri-lanka-and-england-for-t20is-odi-tri-series-and-tests.html", "https://www.unitedrugby.com/fixtures-and-results"],
            "evidence_file": "data/session-48de8c1d/desk.json",
        },
        {
            "id": "GF-F08", "severity": "high", "title": "The 452 reported fair-line families are not current offered prices",
            "status": "needs_review", "affected_count": len(market_rows),
            "detail": "All 452 market families and 997 outcomes are internally normalized and their displayed decimal/American conversions were rechecked. The file contains no live bookmaker quote, and this audit did not independently reconcile the hard-coded means, sigmas, runner strengths, injury assumptions, or all source facts used as inputs. These are historical desk estimates, not prices currently offered on OLBG.",
            "official_source_urls": ["https://www.olbg.com/betting-tips"],
            "evidence_file": "data/session-48de8c1d/desk.json",
        },
        {
            "id": "GF-F09", "severity": "high", "title": "Injury and availability statements are not individually evidenced in the prediction cards",
            "status": "needs_review", "affected_count": len(predictions),
            "detail": "The prediction records contain one match-source URL and an injury-note field, but no per-claim evidence pointer. Absence of a roster entry is not proof of fitness or non-injury; no such statement is promoted here.",
            "official_source_urls": ["https://official.nba.com/nba-injury-report-2026-27-season/", "https://www.nhl.com/schedule"],
            "evidence_file": "data/session-48de8c1d/predictions.json",
        },
        {
            "id": "GF-F10", "severity": "high", "title": "Three OLBG hub pages were spot-checked but not saved as reproducible live captures",
            "status": "needs_review", "affected_count": len(LIVE_HUB_SPOT_CHECKS),
            "detail": "Live hub HTML was fetched for Volleyball, Cricket and Handball during this audit. The page bodies use relative Today/Tomorrow time labels and the fetch tool did not provide an exact retrieval timestamp or raw response file. These observations confirm that a live refresh is feasible, but are not used as an updated fixture dataset or as proof of event time/market availability.",
            "official_source_urls": [item["url"] for item in LIVE_HUB_SPOT_CHECKS],
            "evidence_file": "data/session-265b28e5/audit.json",
        },
    ]

    by_sport_event_rows = Counter(e["sport"] for e in current_olbg)
    summary = {
        "review_as_of_utc": AS_OF_UTC,
        "latest_full_scope_capture_utc": taxonomy.get("captured_utc", ""),
        "source_desk_cutoff_utc": desk.get("cutoff_utc", ""),
        "covered_sports": len(SPORTS),
        "olbg_future_event_observations": len(current_olbg),
        "olbg_future_unique_event_ids": len(current_event_ids),
        "olbg_future_sports_with_rows": len(current_sports_with_events),
        "olbg_future_sports_without_rows": len(SPORTS) - len(current_sports_with_events),
        "official_desk_rows_total": len(desk_rows),
        "official_desk_rows_future_at_review_time": future_official_rows,
        "official_desk_rows_started_or_elapsed": stale_official_rows,
        "olbg_references_in_source_desk": olbg_refs_total,
        "olbg_references_future_in_source_desk": olbg_refs_future,
        "olbg_references_without_time_match": len(olbg_ref_mismatches),
        "future_olbg_events_with_manual_official_crosswalk": exact_crosswalk_count,
        "future_olbg_events_with_official_start_time_confirmed": sum(bool(e["official_start_time_confirmed"]) for e in current_olbg),
        "source_desk_predictions_labelled_high": sum(p.get("confidence") == "High" for p in predictions),
        "high_prediction_cards_below_70_percent": high_below_70,
        "high_prediction_cards_at_least_70_percent": high_ge_70,
        "prediction_cards_started_or_elapsed": prediction_start_past,
        "future_numeric_candidates_p_ge_70_in_price_window": len(numeric_candidates),
        "release_ready_predictions": 0,
        "source_desk_market_families": len(market_rows) and sum(len(r.get("markets", [])) for r in desk["rows"]),
        "source_desk_market_outcomes": len(market_rows),
        "math_conversion_errors": len(arithmetic_errors),
        "capture_payloads_hash_checked": len(capture_checks),
        "capture_payloads_hash_pass": capture_pass,
        "capture_payloads_hash_fail": len(capture_fail),
        "capture_http_200": manifest.get("http_200_count", 0),
        "capture_non_200": manifest.get("failed_count", 0),
        "explicit_olbg_capture_target_rows": len(olbg_capture_mismatch_rows),
        "live_olbg_hub_pages_spot_checked_without_timestamped_capture": len(LIVE_HUB_SPOT_CHECKS),
    }

    output = {
        "schema": "olbg4.session-265b28e5.audit/1",
        "session": "arena/265b28e5-olbg4",
        "as_of_utc": AS_OF_UTC,
        "source_capture": {
            "capture_id": manifest.get("capture_id", ""),
            "started_utc": manifest.get("started_utc", ""),
            "finished_utc": manifest.get("finished_utc", ""),
            "manifest_path": "data/session-48de8c1d/capture/20261023T213547Z/manifest.json",
            "manifest_sha256": hashlib.sha256((CAPTURE_DIR / "manifest.json").read_bytes()).hexdigest(),
        },
        "summary": summary,
        "sports": sports_rows,
        "official_fixture_rows": desk_rows,
        "current_olbg_events": sorted(current_olbg, key=lambda e: (e["start_utc"], e["sport"], e["event_name"])),
        "stale_olbg_unexpired_count": len(stale_olbg_unexpired),
        "olbg_reference_mismatches": olbg_ref_mismatches,
        "olbg_capture_target_mismatches": olbg_capture_mismatch_rows,
        "prediction_audit": pred_audit,
        "numeric_prediction_candidates": sorted(numeric_candidates, key=lambda p: (-p["fair_probability_in_source_desk"], p["start_utc"])),
        "market_rows": market_rows,
        "arithmetic_errors": arithmetic_errors,
        "capture_checks": capture_checks,
        "capture_failures": capture_fail,
        "manual_official_crosswalks": MANUAL_CROSSWALKS,
        "manual_olbg_hub_spot_checks": LIVE_HUB_SPOT_CHECKS,
        "findings": findings,
        "checks": {
            "all_http_200_capture_payload_hashes_match": len(capture_fail) == 0 and capture_pass == manifest.get("http_200_count"),
            "all_displayed_market_conversions_recomputed": len(arithmetic_errors) == 0,
            "all_requested_sports_in_coverage_matrix": {s["sport"] for s in sports_rows} == set(SPORTS),
            "all_current_olbg_rows_have_olbg_source_link": all(e["olbg_url"].startswith("https://") for e in current_olbg),
            "unmatched_current_olbg_rows_have_blank_governing_source": all(bool(e["official_source_url"]) or e["crosswalk_status"] == "not independently matched" for e in current_olbg),
            "no_release_ready_prediction_claimed": summary["release_ready_predictions"] == 0,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT)), "summary": summary, "checks": output["checks"]}, indent=2))
    if capture_fail or arithmetic_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

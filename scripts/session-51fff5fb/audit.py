#!/usr/bin/env python3
"""Independent acceptance audit of the latest merged OLBG4 desk.

This script reads committed capture/desk/prediction files and writes only
`data/session-51fff5fb/audit.json`. It does not fetch sources or modify shared
site outputs. Source URLs and capture hashes are retained so a reviewer can
follow every finding to the primary source or to the OLBG event listing.
"""
from __future__ import annotations

import gzip
import hashlib
import html
import itertools
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "data" / "session-b6643783"
OUT_DIR = ROOT / "data" / "session-51fff5fb"
SPORTS = [
    ("Golf", "golf"),
    ("Volleyball", "volleyball"),
    ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"),
    ("Snooker", "snooker"),
    ("Darts", "darts"),
    ("Baseball", "baseball"),
    ("Gaelic Sports", "gaelic-sports"),
    ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"),
    ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"),
    ("Rugby League", "rugby-league"),
]
SPORT_SLUG = dict(SPORTS)
BANNED = re.compile(r"\b(model|models|modelled|modeled|modelling|verif\w*)\b", re.I)


def read_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def norm_url(url: str | None) -> str:
    if not url:
        return ""
    bits = urlsplit(url.strip())
    host = bits.netloc.lower()
    path = bits.path.rstrip("/") or "/"
    return urlunsplit((bits.scheme.lower(), host, path, bits.query, ""))


def american_from_decimal(decimal: float) -> int:
    if decimal >= 2:
        return int(round((decimal - 1) * 100))
    return int(round(-100 / (decimal - 1)))


def text_grams(text: str) -> set[tuple[str, ...]]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {tuple(words[i:i + 3]) for i in range(max(0, len(words) - 2))}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b) if a or b else 0.0


def price_band(american: int | None) -> bool:
    return american is not None and -250 <= int(american) <= 10000


def has_match_by_match_history(value) -> bool:
    """Detect an explicit per-game recent log, not just a W-L or L10 summary."""
    keys = {"recent_results", "recent_matches", "match_history", "game_log", "last_games", "last_five_results", "last_ten_results"}
    if isinstance(value, dict):
        return any(str(k).lower() in keys and bool(v) for k, v in value.items()) or any(has_match_by_match_history(v) for v in value.values())
    if isinstance(value, list):
        return any(has_match_by_match_history(v) for v in value)
    return False


def base_row(row: dict, prediction: dict | None, captured_at: datetime | None) -> dict:
    pick = row.get("pick") or {}
    start = utc(row.get("start_utc"))
    olbg = row.get("olbg") or {}
    selection = pick.get("selection") or ""
    official_url = row.get("official_url") or ""
    source_name = row.get("official_source_name") or "Source not named in row"
    source_kind = "OLBG listing only" if "olbg.com" in official_url.lower() or source_name.lower().startswith("olbg") else "Official competition / governing-body source"
    return {
        "id": row.get("id", ""),
        "sport": row.get("sport", ""),
        "competition": row.get("competition", ""),
        "match": " v ".join(part for part in (row.get("side_a", ""), row.get("side_b", "")) if part).strip(),
        "start_utc": row.get("start_utc", ""),
        "starts_after_capture": bool(start and captured_at and start > captured_at),
        "market": pick.get("market", ""),
        "selection": selection,
        "confidence": pick.get("confidence", "") if pick else "",
        "fair_probability": pick.get("fair_prob"),
        "fair_american": pick.get("fair_american"),
        "fair_decimal": pick.get("fair_decimal"),
        "probability_at_least_70": bool(pick and pick.get("fair_prob", 0) >= 0.70),
        "inside_american_price_focus": bool(pick and price_band(pick.get("fair_american"))),
        "passes_numeric_high_focus": bool(pick and pick.get("fair_prob", 0) >= 0.70 and price_band(pick.get("fair_american"))),
        "has_written_prediction": prediction is not None,
        "prediction_words": prediction.get("words") if prediction else None,
        "olbg_event_url": olbg.get("event_url", ""),
        "official_source_name": source_name,
        "official_source_url": official_url,
        "source_kind": source_kind,
        "capture_id": row.get("capture_id", ""),
        "flags": list(row.get("flags") or []),
    }


def root_summary(rows: list[dict], predictions: list[dict], captured_at: datetime | None) -> dict:
    """Compare the first card under the root page's 'Next up' label with the data.

    This is only a clarity signal: the page may intentionally sort those cards by
    confidence, so a mismatch is not treated as a bad fixture or price.
    """
    path = ROOT / "index.html"
    if not path.is_file():
        return {"available": False, "root_page": "../index.html"}
    page_text = path.read_text(encoding="utf-8")
    stamp_match = re.search(r'<span class="stamp">Data read\s+(.*?)</span>', page_text, re.S)
    section_at = page_text.find("Next up: highest-confidence picks")
    grid_at = page_text.find('<div class="pickgrid">', section_at) if section_at >= 0 else -1
    first_card = {}
    if grid_at >= 0:
        article_match = re.search(r'<article class="pick">(.*?)</article>', page_text[grid_at:], re.S)
        if article_match:
            article = article_match.group(1)
            def card_text(pattern: str) -> str:
                m = re.search(pattern, article, re.S)
                if not m:
                    return ""
                value = re.sub(r"<[^>]+>", " ", m.group(1))
                return re.sub(r"\s+", " ", html.unescape(value)).strip()
            first_card = {
                "sport": card_text(r'<div class="sport">(.*?)</div>'),
                "match": card_text(r'<div class="match">(.*?)</div>'),
                "date_label": card_text(r'<div class="meta">(.*?)</div>'),
                "selection": card_text(r'<div class="val">(.*?)</div>'),
            }
            source = re.search(r'<div class="src">.*?<a href="([^"]+)"', article, re.S)
            first_card["official_source_url"] = html.unescape(source.group(1)) if source else ""
    future = [p for p in predictions if (utc(p.get("start_utc")) and captured_at and utc(p.get("start_utc")) > captured_at)]
    earliest = min(future, key=lambda p: str(p.get("start_utc", ""))) if future else None
    earliest_item = None
    if earliest:
        source_url = next((s.get("url", "") for s in (earliest.get("sources") or []) if "olbg.com" not in str(s.get("url", "")).lower()), "")
        earliest_item = {
            "row_id": earliest.get("row_id", ""),
            "sport": earliest.get("sport", ""),
            "match": earliest.get("match", ""),
            "start_utc": earliest.get("start_utc", ""),
            "selection": earliest.get("selection", ""),
            "official_source_url": source_url,
            "olbg_event_url": next((s.get("url", "") for s in (earliest.get("sources") or []) if "olbg.com" in str(s.get("url", "")).lower()), ""),
        }
    first_match = first_card.get("match", "")
    is_earliest = bool(earliest_item and first_match and first_match.casefold() == earliest_item["match"].casefold())
    return {
        "available": True,
        "root_page": "../index.html",
        "data_read_label": html.unescape(stamp_match.group(1).strip()) if stamp_match else "",
        "next_up_heading_present": section_at >= 0,
        "first_displayed_card": first_card,
        "earliest_future_written_prediction": earliest_item,
        "first_card_is_earliest_written_prediction": is_earliest,
        "clarity_note": "The landing page labels this grid 'Next up' but its first card is not the earliest written fixture; the cards appear confidence-ranked. Clarify the sort or rename the section so users do not mistake the top card for the next start.",
    }


def handball_copy_audit(capture_dir: Path, manifest: dict, rows: list[dict], predictions_by_id: dict) -> dict:
    """Recheck the Danish handball average phrasing against the captured table.

    The official standings list each club's games played and goals for/against.
    Summing team goals and dividing by completed fixtures yields the match-total
    average; dividing by team-games yields the per-side scoring rate.
    """
    record = next((r for r in manifest.get("records", []) if r.get("id") == "dk_herreligaen" and int(r.get("status") or 0) == 200), None)
    if not record:
        return {"checked": False, "issue": "Official Danish standings capture is not present."}
    path = capture_dir / str(record.get("file", ""))
    if not path.is_file():
        return {"checked": False, "issue": "Official Danish standings payload is missing."}
    try:
        raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
        source_text = raw.decode("utf-8", "replace")
    except (OSError, UnicodeDecodeError) as exc:
        return {"checked": False, "issue": f"Official Danish standings payload could not be read: {exc}"}

    table = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", source_text, re.S):
        cells = []
        for cell in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S):
            value = re.sub(r"<[^>]+>", "", cell)
            cells.append(re.sub(r"\s+", " ", html.unescape(value)).strip())
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        score = re.fullmatch(r"(\d+)\s*-\s*(\d+)", cells[6])
        if not score or not cells[2].isdigit():
            continue
        table.append({
            "team": cells[1], "played": int(cells[2]),
            "gf": int(score.group(1)), "ga": int(score.group(2)),
        })
    if not table or sum(r["played"] for r in table) % 2:
        return {"checked": False, "issue": "Danish standings did not yield a complete fixture denominator."}

    total_team_games = sum(r["played"] for r in table)
    matches = total_team_games // 2
    total_goals = sum(r["gf"] for r in table)
    per_team_game = total_goals / total_team_games
    per_match = total_goals / matches
    rid = "ca_olbg_12078"
    row = next((r for r in rows if str(r.get("id")) == rid), {})
    prediction = predictions_by_id.get(rid) or {}
    text = str(prediction.get("text", ""))
    claimed = "31.66 goals a match" in text
    issue = claimed and abs(per_team_game - 31.66) < 0.01 and abs(per_match - 31.66) > 0.1
    return {
        "checked": True,
        "row_id": rid,
        "official_source_url": record.get("url", ""),
        "capture_file": str(record.get("file", "")),
        "capture_sha256": record.get("sha256", ""),
        "clubs_in_table": len(table),
        "team_games": total_team_games,
        "completed_matches_from_standings": matches,
        "total_goals_for": total_goals,
        "mean_goals_per_team_game": round(per_team_game, 2),
        "mean_total_goals_per_match": round(per_match, 2),
        "prediction_claim_phrase_present": claimed,
        "issue": issue,
        "recommended_wording": f"{per_team_game:.2f} goals per team per game" if issue else "",
        "official_fixture_url": row.get("olbg", {}).get("event_url", ""),
    }


def check_capture(capture_dir: Path, manifest: dict) -> dict:
    checked = 0
    bad = []
    missing = []
    status_ok = 0
    for rec in manifest.get("records", []):
        if int(rec.get("status") or 0) != 200:
            continue
        status_ok += 1
        rel = rec.get("file") or ""
        path = capture_dir / rel
        if not path.is_file():
            missing.append({"record_id": rec.get("id", ""), "file": rel, "url": rec.get("url", "")})
            continue
        stored = path.read_bytes()
        try:
            raw = gzip.decompress(stored) if path.suffix == ".gz" else stored
        except OSError as exc:
            bad.append({"record_id": rec.get("id", ""), "file": rel, "reason": f"gzip read failed: {exc}"})
            continue
        checked += 1
        actual = hashlib.sha256(raw).hexdigest()
        expected = rec.get("sha256", "")
        if not expected or actual != expected:
            bad.append({"record_id": rec.get("id", ""), "file": rel, "expected_sha256": expected, "actual_sha256": actual})
    return {
        "manifest_targets": int(manifest.get("targets", 0)),
        "http_200_records": status_ok,
        "payload_hashes_checked": checked,
        "missing_payloads": missing,
        "hash_mismatches": bad,
        "capture_failures": [
            {
                "id": f.get("id", ""),
                "status": int(f.get("status") or 0),
                "url": f.get("url", ""),
                "error": f.get("error", ""),
            }
            for f in manifest.get("failures", [])
        ],
    }


def main() -> int:
    desk = read_json(SOURCE_DIR / "desk.json")
    preds_doc = read_json(SOURCE_DIR / "predictions.json")
    meta = read_json(SOURCE_DIR / "meta.json")
    capture_id = str(meta.get("capture_id", ""))
    capture_dir = SOURCE_DIR / "capture" / capture_id
    manifest = read_json(capture_dir / "manifest.json")
    rows = desk.get("rows") or []
    predictions = preds_doc.get("predictions") or []
    by_id = {str(p.get("row_id", "")): p for p in predictions}
    captured_at = utc(meta.get("capture_utc"))
    cutoff = utc(desk.get("cutoff_utc"))

    source_records = manifest.get("records", [])
    by_capture_id = {str(r.get("id", "")): r for r in source_records}
    by_url: dict[str, dict] = {}
    for record in source_records:
        for url in (record.get("url"), record.get("final_url")):
            key = norm_url(url)
            if key:
                by_url[key] = record

    # Verify the immutable capture bundle at the byte level, without internet access.
    capture_integrity = check_capture(capture_dir, manifest)
    handball_copy = handball_copy_audit(capture_dir, manifest, rows, by_id)
    handball_row = next((r for r in rows if str(r.get("id")) == str(handball_copy.get("row_id", ""))), {})
    handball_copy_item = base_row(handball_row, by_id.get(str(handball_row.get("id", ""))), captured_at) if handball_row else {}

    high_rows: list[dict] = []
    numeric_candidates: list[dict] = []
    bad_price_math = []
    bad_market_sums = []
    market_families: Counter = Counter()
    market_selections = 0
    picked_rows = 0
    olbg_crosswalk_rows = 0
    priced_with_olbg = 0
    no_official_url = []
    olbg_listing_only = 0
    source_unmapped = []
    source_map_counts = Counter()
    rows_not_future = []
    missing_high_writeups = []

    for row in rows:
        pred = by_id.get(str(row.get("id", "")))
        item = base_row(row, pred, captured_at)
        official_url = row.get("official_url") or ""
        olbg_url = (row.get("olbg") or {}).get("event_url", "")
        if not official_url:
            no_official_url.append(item)
        if "olbg.com" in official_url.lower() or (row.get("official_source_name") or "").lower().startswith("olbg"):
            olbg_listing_only += 1
        if olbg_url:
            olbg_crosswalk_rows += 1

        mapped = by_url.get(norm_url(official_url)) if official_url else None
        capture_ref = by_capture_id.get(str(row.get("capture_id", "")))
        if mapped and int(mapped.get("status") or 0) == 200:
            source_map_counts["source_url_matches_successful_capture"] += 1
        elif capture_ref and int(capture_ref.get("status") or 0) == 200:
            source_map_counts["capture_id_matches_successful_capture"] += 1
        elif official_url:
            source_map_counts["source_link_not_matched_to_successful_manifest_record"] += 1
            source_unmapped.append(item)

        start = utc(row.get("start_utc"))
        if start and captured_at and start <= captured_at:
            rows_not_future.append(item)
        pick = row.get("pick") or {}
        if not pick:
            continue
        picked_rows += 1
        if olbg_url:
            priced_with_olbg += 1

        probability = float(pick.get("fair_prob", 0) or 0)
        decimal = float(pick.get("fair_decimal", 0) or 0)
        american = pick.get("fair_american")
        try:
            derived_decimal = round(1 / probability, 2)
            if abs(derived_decimal - decimal) > 0.02 or american_from_decimal(decimal) != int(american):
                bad_price_math.append({**item, "derived_decimal": derived_decimal})
        except (ZeroDivisionError, TypeError, ValueError):
            bad_price_math.append(item)

        for family, market in (row.get("markets") or {}).items():
            market_families[family] += 1
            selections = market.get("selections") or []
            market_selections += len(selections)
            if selections:
                total = sum(float(sel.get("fair_prob", 0) or 0) for sel in selections)
                if abs(total - 1.0) > 0.002:
                    bad_market_sums.append({"row_id": row.get("id", ""), "market": family, "probability_sum": round(total, 6)})

        if pick.get("confidence") == "High":
            high_rows.append(item)
            if not price_band(american):
                pass
            if probability >= 0.70 and price_band(american):
                numeric_candidates.append(item)
            if pred is None:
                missing_high_writeups.append(item)

    # Check every written prediction independently of the pre-generated `words` field.
    word_counts = []
    word_count_issues = []
    banned_predictions = []
    missing_prediction_sources = []
    selection_not_in_text = []
    missing_prediction_row = []
    for pred in predictions:
        rid = str(pred.get("row_id", ""))
        row = next((r for r in rows if str(r.get("id", "")) == rid), None)
        text = str(pred.get("text", ""))
        words = len(text.split())
        word_counts.append(words)
        if words < 30 or int(pred.get("words", 0) or 0) != words:
            item = base_row(row, pred, captured_at) if row else {"id": rid, "sport": pred.get("sport", "")}
            item["actual_word_count"] = words
            item["stored_word_count"] = pred.get("words")
            word_count_issues.append(item)
        if BANNED.search(text):
            banned_predictions.append({"row_id": rid, "match": pred.get("match", ""), "terms": sorted(set(m.group(0) for m in BANNED.finditer(text))), "sources": pred.get("sources", [])})
        if not row:
            missing_prediction_row.append({"row_id": rid, "match": pred.get("match", "")})
        selection = re.sub(r"\s*\((home|away)\)$", "", str(pred.get("selection", "")), flags=re.I).strip()
        # F1 driver rows may append the official three-letter code (e.g. ANT) to
        # the named driver. It is a display suffix, not part of the person's name.
        if selection and re.search(r"\s+[A-Z]{3}$", selection):
            selection = re.sub(r"\s+[A-Z]{3}$", "", selection).strip()
        selection_tokens = [t.casefold() for t in re.findall(r"[A-Za-z0-9]+", selection)]
        prediction_tokens = {t.casefold() for t in re.findall(r"[A-Za-z0-9]+", text)}
        if selection_tokens and not all(token in prediction_tokens for token in selection_tokens):
            selection_not_in_text.append({"row_id": rid, "match": pred.get("match", ""), "selection": selection, "sources": pred.get("sources", [])})
        source_list = pred.get("sources") or []
        if not any(str(src.get("url", "")).startswith("https://") for src in source_list):
            missing_prediction_sources.append({"row_id": rid, "match": pred.get("match", "")})

    # Distinct, reproducible text-similarity check.
    grams = {str(p.get("row_id", "")): text_grams(str(p.get("text", ""))) for p in predictions}
    max_similarity = 0.0
    max_pair = []
    for a, b in itertools.combinations(predictions, 2):
        aid, bid = str(a.get("row_id", "")), str(b.get("row_id", ""))
        score = jaccard(grams.get(aid, set()), grams.get(bid, set()))
        if score > max_similarity:
            max_similarity = score
            max_pair = [aid, bid]

    prediction_counts = Counter(str(p.get("sport", "")) for p in predictions)
    fixture_counts = Counter(str(r.get("sport", "")) for r in rows)
    priced_counts = Counter(str(r.get("sport", "")) for r in rows if r.get("pick"))
    high_counts = Counter(str(r.get("sport", "")) for r in rows if (r.get("pick") or {}).get("confidence") == "High")
    eligible_counts = Counter(str(x.get("sport", "")) for x in numeric_candidates)

    # Age is a snapshot property, not a live feed. Keep capture/read and generation times separate.
    sport_rows = []
    gap_by_sport = {str(g.get("sport", "")): g for g in (meta.get("gaps") or [])}
    for sport, slug in SPORTS:
        srows = [r for r in rows if r.get("sport") == sport]
        source_url = ""
        source_name = ""
        for r in srows:
            url = r.get("official_url") or ""
            name = r.get("official_source_name") or ""
            if url and "olbg.com" not in url.lower() and not name.lower().startswith("olbg"):
                source_url, source_name = url, name
                break
        gap = gap_by_sport.get(sport) or {}
        if not source_url:
            source_url = gap.get("source_url", "")
            source_name = "Official source / coverage gap" if source_url else ""
        sport_rows.append({
            "sport": sport,
            "slug": slug,
            "fixture_rows": fixture_counts.get(sport, 0),
            "priced_rows": priced_counts.get(sport, 0),
            "high_labels": high_counts.get(sport, 0),
            "numeric_high_candidates": eligible_counts.get(sport, 0),
            "written_predictions": prediction_counts.get(sport, 0),
            "prediction_target": 5,
            "shortfall": max(0, 5 - prediction_counts.get(sport, 0)),
            "coverage_gap": gap.get("reason", ""),
            "official_source_name": source_name,
            "official_source_url": source_url,
            "category_page": f"../desk/sports/{slug}.html",
        })

    # Map findings to records. Each affected fixture carries its primary source URL and OLBG link.
    high_outside_band = [x for x in high_rows if not x.get("inside_american_price_focus")]
    high_no_prediction = [x for x in high_rows if not x.get("has_written_prediction")]
    priced_no_olbg = [
        base_row(r, by_id.get(str(r.get("id", ""))), captured_at)
        for r in rows if r.get("pick") and not (r.get("olbg") or {}).get("event_url")
    ]
    predictions_no_olbg = [
        {**base_row(next((r for r in rows if str(r.get("id", "")) == str(p.get("row_id", ""))), {}), p, captured_at),
         "prediction_text": p.get("text", "")}
        for p in predictions
        if not ((next((r for r in rows if str(r.get("id", "")) == str(p.get("row_id", ""))), {}).get("olbg") or {}).get("event_url"))
    ]
    outside_after_capture = rows_not_future

    eligible_records = []
    for item in numeric_candidates:
        row = next(r for r in rows if str(r.get("id", "")) == item["id"])
        pred = by_id.get(str(item["id"]))
        enriched = dict(item)
        enriched["prediction_text"] = pred.get("text", "") if pred else ""
        enriched["prediction_sources"] = pred.get("sources", []) if pred else []
        enriched["olbg_event_name"] = (row.get("olbg") or {}).get("event", "")
        enriched["venue"] = row.get("venue", "")
        enriched["form"] = row.get("form") or {}
        enriched["sample"] = row.get("sample", "")
        enriched["evidence"] = row.get("evidence") or {}
        enriched["has_olbg_event"] = bool((row.get("olbg") or {}).get("event_url"))
        # Injury evidence is considered present only if a captured field explicitly names it.
        combined = json.dumps({"row": row, "prediction": pred or {}}, ensure_ascii=False).lower()
        enriched["injury_input_present"] = any(term in combined for term in ("injury", "injured", "suspended", "ruled out", "availability"))
        enriched["match_by_match_history_present"] = has_match_by_match_history({"row": row, "prediction": pred or {}})
        enriched["prediction_statistic_wording_issue"] = bool(handball_copy.get("issue") and str(row.get("id")) == str(handball_copy.get("row_id")))
        eligible_records.append(enriched)

    market_family_totals = {family: int(count) for family, count in sorted(market_families.items())}
    high_predictions = [p for p in predictions if p.get("confidence") == "High"]
    capture_failures = capture_integrity["capture_failures"]
    injury_input_rows = []
    match_history_rows = []
    current_form_rows = []
    for pred in predictions:
        row = next((r for r in rows if str(r.get("id", "")) == str(pred.get("row_id", ""))), {})
        combined = json.dumps({"row": row, "prediction": pred}, ensure_ascii=False).lower()
        if any(term in combined for term in ("injury", "injured", "suspended", "ruled out", "availability")):
            injury_input_rows.append(str(pred.get("row_id", "")))
        if has_match_by_match_history({"row": row, "prediction": pred}):
            match_history_rows.append(str(pred.get("row_id", "")))
        if pred.get("form") or row.get("form"):
            current_form_rows.append(str(pred.get("row_id", "")))
    root_check = root_summary(rows, predictions, captured_at)
    quote_fields = {"bookmaker_odds", "market_odds", "olbg_odds", "quoted_odds", "source_odds", "odds_quote"}
    def has_external_quote(value) -> bool:
        if isinstance(value, dict):
            return any(str(k).lower() in quote_fields or has_external_quote(v) for k, v in value.items())
        if isinstance(value, list):
            return any(has_external_quote(v) for v in value)
        return False
    rows_with_external_quotes = sum(1 for row in rows if has_external_quote(row))

    findings = [
        {
            "id": "QF-F01", "severity": "high", "title": "High labels outside the requested fair-price band",
            "summary": f"{len(high_outside_band)} of {len(high_rows)} rows labelled High have a fair American price outside −250…+10,000. The source desk's High label is probability-based; this audit keeps the label intact but excludes those rows from the price-focused shortlist.",
            "affected_count": len(high_outside_band), "affected_rows": high_outside_band,
        },
        {
            "id": "QF-F02", "severity": "high", "title": "High rows without a full written prediction",
            "summary": f"{len(high_no_prediction)} of {len(high_rows)} High rows have no prediction text. The full desk has {len(predictions)} authored write-ups; absent copy is left blank, not filled with a winner-only template.",
            "affected_count": len(high_no_prediction), "affected_rows": high_no_prediction,
        },
        {
            "id": "QF-F03", "severity": "high", "title": "Most originated fixtures lack an OLBG event cross-reference",
            "summary": f"{len(priced_no_olbg)} of {picked_rows} priced rows and {len(predictions_no_olbg)} of {len(predictions)} written predictions have no OLBG event URL. An official league fixture is not treated as proof that an OLBG market is currently available.",
            "affected_count": len(priced_no_olbg), "affected_rows": priced_no_olbg,
        },
        {
            "id": "QF-F04", "severity": "high", "title": "Some listed starts are not in the future at the capture time",
            "summary": f"{len(outside_after_capture)} rows start at or before the capture timestamp {meta.get('capture_utc', '')}. They cannot be presented as upcoming from that snapshot; retain them only with an explicit stale/in-play flag.",
            "affected_count": len(outside_after_capture), "affected_rows": outside_after_capture,
        },
        {
            "id": "QF-F05", "severity": "medium", "title": "Five-write-up-per-sport target is not met",
            "summary": "Only sports with researched, supported write-ups count toward the target; missing sports are not padded. The full per-sport shortfall matrix is on Coverage.",
            "affected_count": sum(x["shortfall"] for x in sport_rows), "affected_rows": [],
        },
        {
            "id": "QF-F06", "severity": "medium", "title": "No injury or availability feed is present in the written-pick inputs",
            "summary": "The captured prediction inputs contain no explicit injury, suspension or availability field. Blank means unknown, not that a team has no absences. Do not add injury claims without an official team/league source.",
            "affected_count": len(predictions), "affected_rows": [],
        },
        {
            "id": "QF-F07", "severity": "medium", "title": "The published prices are our fair lines, not captured OLBG quotes",
            "summary": "The row market objects contain fair probabilities and derived fair prices; no event-level OLBG/bookmaker quote field is stored. The desk therefore cannot establish that every quoted market is currently offered at the shown price.",
            "affected_count": picked_rows, "affected_rows": [],
        },
        {
            "id": "QF-F08", "severity": "medium", "title": "Official source URLs do not replace event-level OLBG confirmation",
            "summary": f"{olbg_listing_only} rows use an OLBG listing as their source (listing-only) rather than a governing-body fixture feed. Those rows remain flagged where the fixture, participants, time or racecard could not be confirmed independently.",
            "affected_count": olbg_listing_only, "affected_rows": [base_row(r, by_id.get(str(r.get("id", ""))), captured_at) for r in rows if "olbg.com" in str(r.get("official_url", "")).lower()],
        },
        {
            "id": "QF-F09", "severity": "medium", "title": "Clarify how the root 'Next up' cards are sorted",
            "summary": root_check.get("clarity_note", "The root executive pick order could not be compared with the underlying prediction timestamps."),
            "affected_count": int(bool(root_check.get("available") and not root_check.get("first_card_is_earliest_written_prediction"))),
            "affected_rows": [],
        },
        {
            "id": "QF-F10", "severity": "medium", "title": "Recent form is aggregate; no per-match result log is in the prediction inputs",
            "summary": f"{len(current_form_rows)} of {len(predictions)} write-ups include a form summary, but {len(match_history_rows)} include an explicit recent match-by-match log. This report does not fill in missing opponents or scores.",
            "affected_count": len(predictions) - len(match_history_rows), "affected_rows": [],
        },
        {
            "id": "QF-F11", "severity": "high", "title": "Handball prediction describes a team scoring rate as a match-total average",
            "summary": f"The Ringsted–GOG text calls 31.66 'goals a match'. Recounting the captured Danish table gives {handball_copy.get('mean_goals_per_team_game', '')} goals per team-game but {handball_copy.get('mean_total_goals_per_match', '')} total goals per match. Correct or remove the phrase before treating the write-up as final.",
            "affected_count": int(bool(handball_copy.get("issue"))), "affected_rows": [handball_copy_item] if handball_copy.get("issue") else [],
        },
    ]

    audit = {
        "schema": "qf-acceptance-audit-1",
        "board": "QF",
        "session": "arena/51fff5fb-olbg4",
        "source_board": "CA",
        "source_session": desk.get("session", ""),
        "source_paths": {
            "desk": "data/session-b6643783/desk.json",
            "predictions": "data/session-b6643783/predictions.json",
            "metadata": "data/session-b6643783/meta.json",
            "capture_manifest": f"data/session-b6643783/capture/{capture_id}/manifest.json",
        },
        "capture": {
            "id": capture_id,
            "captured_utc": meta.get("capture_utc", ""),
            "capture_started_utc": manifest.get("started_utc", ""),
            "capture_finished_utc": manifest.get("finished_utc", ""),
            "desk_cutoff_utc": desk.get("cutoff_utc", ""),
            "desk_generated_utc": desk.get("generated_utc", ""),
            "window_start_utc": meta.get("window_start", ""),
            "window_end_utc": meta.get("window_end", ""),
            "manifest_targets": int(manifest.get("targets", 0)),
            "successful_targets": int(manifest.get("ok", 0)),
            "failed_targets": int(manifest.get("failed", 0)),
            "manifest_file_sha256": hashlib.sha256((capture_dir / "manifest.json").read_bytes()).hexdigest(),
        },
        "rules": {
            "high_probability_floor": 0.70,
            "american_price_min": -250,
            "american_price_max": 10000,
            "prediction_min_words": 30,
            "predictions_per_sport_target": 5,
            "upcoming_means_start_strictly_after_capture_utc": True,
            "note": "The price is an internally originated fair price, not an observed bookmaker or OLBG quote.",
        },
        "summary": {
            "sports_in_brief": len(SPORTS),
            "sports_with_fixture_rows": len({r.get("sport") for r in rows}),
            "fixture_rows": len(rows),
            "priced_rows": picked_rows,
            "written_predictions": len(predictions),
            "written_high_predictions": len(high_predictions),
            "high_label_rows": len(high_rows),
            "high_rows_inside_numeric_focus": len(numeric_candidates),
            "high_rows_inside_focus_with_prediction": sum(bool(x.get("has_written_prediction")) for x in numeric_candidates),
            "high_rows_inside_focus_with_prediction_and_olbg_event": sum(bool(x.get("has_written_prediction")) and bool(x.get("olbg_event_url")) for x in numeric_candidates),
            "high_rows_outside_price_focus": len(high_outside_band),
            "high_rows_missing_prediction": len(high_no_prediction),
            "olbg_event_crosswalk_rows": olbg_crosswalk_rows,
            "priced_rows_with_olbg_event": priced_with_olbg,
            "priced_rows_without_olbg_event": len(priced_no_olbg),
            "predictions_without_olbg_event": len(predictions_no_olbg),
            "rows_started_at_or_before_capture": len(rows_not_future),
            "rows_missing_official_source_url": len(no_official_url),
            "rows_with_olbg_listing_only_source": olbg_listing_only,
            "official_source_links_not_matched_to_manifest": len(source_unmapped),
            "market_families_by_row": market_family_totals,
            "market_family_instances": sum(market_family_totals.values()),
            "priced_selection_count": market_selections,
            "prediction_words_min": min((len(str(p.get("text", "")).split()) for p in predictions), default=0),
            "prediction_words_max": max((len(str(p.get("text", "")).split()) for p in predictions), default=0),
            "prediction_similarity_max_3gram_jaccard": round(max_similarity, 4),
            "prediction_similarity_max_pair": max_pair,
            "prediction_has_banned_internal_terms": len(banned_predictions) > 0,
            "prediction_has_injury_input": bool(injury_input_rows),
            "prediction_rows_with_injury_input": len(injury_input_rows),
            "prediction_rows_with_current_form_summary": len(current_form_rows),
            "prediction_rows_with_match_by_match_history": len(match_history_rows),
            "prediction_rows_missing_match_by_match_history": len(predictions) - len(match_history_rows),
            "prediction_statistic_wording_issues": int(bool(handball_copy.get("issue"))),
            "rows_with_observed_external_quote_fields": rows_with_external_quotes,
            "capture_payload_hashes_passed": capture_integrity["payload_hashes_checked"] - len(capture_integrity["hash_mismatches"]),
            "capture_payload_hashes_checked": capture_integrity["payload_hashes_checked"],
            "capture_hash_mismatch_count": len(capture_integrity["hash_mismatches"]),
            "capture_missing_payload_count": len(capture_integrity["missing_payloads"]),
            "capture_failure_count": len(capture_failures),
        },
        "source_integrity": capture_integrity,
        "source_map_counts": dict(source_map_counts),
        "root_summary_check": root_check,
        "handball_copy_audit": handball_copy,
        "prediction_checks": {
            "under_30_or_stored_count_mismatch": word_count_issues,
            "banned_terms": banned_predictions,
            "missing_official_source": missing_prediction_sources,
            "selection_not_explicit": selection_not_in_text,
            "prediction_without_fixture_row": missing_prediction_row,
            "max_pairwise_3gram_jaccard": round(max_similarity, 4),
            "max_pair": max_pair,
        },
        "market_checks": {
            "bad_price_math": bad_price_math,
            "bad_two_way_or_three_way_probability_sums": bad_market_sums,
        },
        "sports": sport_rows,
        "high_rows": sorted(high_rows, key=lambda x: (x.get("start_utc", ""), x.get("sport", ""), x.get("id", ""))),
        "numeric_high_candidates": sorted(eligible_records, key=lambda x: (x.get("start_utc", ""), x.get("sport", ""), x.get("id", ""))),
        "high_outside_price_focus": sorted(high_outside_band, key=lambda x: (x.get("sport", ""), x.get("start_utc", ""), x.get("id", ""))),
        "high_missing_prediction": sorted(high_no_prediction, key=lambda x: (x.get("sport", ""), x.get("start_utc", ""), x.get("id", ""))),
        "priced_without_olbg_event": sorted(priced_no_olbg, key=lambda x: (x.get("sport", ""), x.get("start_utc", ""), x.get("id", ""))),
        "predictions_without_olbg_event": sorted(predictions_no_olbg, key=lambda x: (x.get("sport", ""), x.get("start_utc", ""), x.get("id", ""))),
        "not_future_at_capture": sorted(rows_not_future, key=lambda x: (x.get("start_utc", ""), x.get("sport", ""), x.get("id", ""))),
        "unmapped_source_rows": sorted(source_unmapped, key=lambda x: (x.get("sport", ""), x.get("id", ""))),
        "sports_short_of_five": [x for x in sport_rows if x["shortfall"] > 0],
        "coverage_gaps": meta.get("gaps", []),
        "predictions": [
            {
                "row_id": p.get("row_id", ""),
                "sport": p.get("sport", ""),
                "match": p.get("match", ""),
                "start_utc": p.get("start_utc", ""),
                "market": p.get("market", ""),
                "selection": p.get("selection", ""),
                "confidence": p.get("confidence", ""),
                "fair_probability": p.get("fair_prob"),
                "fair_american": p.get("fair_american"),
                "word_count": len(str(p.get("text", "")).split()),
                "text": p.get("text", ""),
                "official_source_url": next((s.get("url", "") for s in (p.get("sources") or []) if "olbg.com" not in str(s.get("url", "")).lower()), ""),
                "olbg_event_url": next((s.get("url", "") for s in (p.get("sources") or []) if "olbg.com" in str(s.get("url", "")).lower()), ""),
            }
            for p in predictions
        ],
        "findings": findings,
        "links": {
            "root_overview": "../index.html",
            "picks": "../desk/picks.html",
            "matches": "../desk/matches.html",
            "flagged": "../desk/flagged.html",
            "methodology": "../desk/methodology.html",
            "sources": "../desk/sources.html",
        },
    }

    # Add summary-driven state without inventing an overall accuracy claim.
    prediction_rule_failures = (
        len(audit["prediction_checks"]["under_30_or_stored_count_mismatch"])
        + len(banned_predictions)
        + len(missing_prediction_sources)
        + len(selection_not_in_text)
        + len(missing_prediction_row)
    )
    audit["summary"]["prediction_rule_failure_count"] = prediction_rule_failures
    audit["summary"]["market_math_failure_count"] = len(bad_price_math) + len(bad_market_sums)
    audit["summary"]["source_integrity_pass"] = not capture_integrity["hash_mismatches"] and not capture_integrity["missing_payloads"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "audit.json"
    out_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = audit["summary"]
    print(
        f"QF audit written: {out_path.relative_to(ROOT)}\n"
        f"  {summary['fixture_rows']} rows / {summary['priced_rows']} priced / "
        f"{summary['high_label_rows']} High labels / {summary['high_rows_inside_numeric_focus']} inside numeric focus\n"
        f"  {summary['written_predictions']} predictions; {summary['rows_started_at_or_before_capture']} starts at/before capture\n"
        f"  capture payload hashes: {summary['capture_payload_hashes_passed']}/{summary['capture_payload_hashes_checked']} pass"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

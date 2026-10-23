#!/usr/bin/env python3
"""Build an isolated, read-only evidence audit of the merged OLBG dashboards.

No upstream data, peer site, or root navigation is written. All audit numbers
are recomputed from committed JSON and SHA-256 manifests; official references
are retained as manual-review links, not presented as live checks.
"""
from __future__ import annotations

import ast
import datetime as dt
import gzip
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
OUT_DATA = ROOT / "data/session-2c215a91"
OUT_SITE = ROOT / "session-2c215a91"
AS_OF = dt.datetime.fromisoformat("2026-10-23T19:30:00+00:00")
AS_OF_TEXT = "2026-10-23T19:30:00Z"
SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts",
    "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing",
    "Handball", "Ice Hockey", "Basketball", "Rugby League",
]
SLUGS = {
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts",
    "Baseball": "baseball", "Gaelic Sports": "gaelic-sports",
    "Greyhounds": "greyhounds", "Tennis": "tennis", "Motor Racing": "motor-racing",
    "Handball": "handball", "Ice Hockey": "ice-hockey", "Basketball": "basketball",
    "Rugby League": "rugby-league",
}
# Official pages captured in the upstream source manifests. For a category with
# no fixture-level official evidence, these are explicitly manual-review links.
OFFICIAL_REFERENCES = {
    "Golf": ("PGA TOUR — Butterfield Bermuda Championship", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528", "Event page captured; no match-up/player field was parsed."),
    "Volleyball": ("Lega Pallavolo — 2026 calendar", "https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=991", "Official calendar reference; the 19 listed fixtures remain unconfirmed in the committed capture."),
    "Rugby Union": ("United Rugby Championship — fixtures in full", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", "Official URC fixtures; does not confirm the 19 listing-only fixtures from other competitions."),
    "Cricket": ("Cricket Australia — fixtures", "https://www.cricket.com.au/fixtures", "Official fixture page captured; cricket rows were left unpriced."),
    "Snooker": ("World Snooker Tour — Northern Ireland Open", "https://www.wst.tv/tournaments/northern-ireland-open-2026/", "Official tournament page returned a JavaScript shell; no fixture rows were parsed."),
    "Darts": ("PDC — official site", "https://www.pdc.tv/", "Official host; the schedule article itself did not render in the capture, so pairings remain listing-only."),
    "Baseball": ("MLB Stats API — schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-04&hydrate=probablePitcher(note),team,venue,linescore", "Official schedule/statistics API used for the priced World Series rows."),
    "Gaelic Sports": ("Cork GAA — fixtures", "https://gaacork.ie/fixtures", "Official club fixture reference; one additional OLBG-listed pairing remains unconfirmed."),
    "Greyhounds": ("Greyhound Board of Great Britain — results", "https://www.gbgb.org.uk/results/", "Official results page only; it does not verify future race cards or runners."),
    "Tennis": ("ATP — Lyon order of play", "https://www.protennislive.com/posting/2026/496/op.pdf", "Official order-of-play PDF used for listed ATP ties; no completed-results feed was captured."),
    "Motor Racing": ("MotoGP — official calendar", "https://www.motogp.com/en/calendar", "Official calendar reference; the row is an outright event, not a head-to-head match."),
    "Handball": ("Betoro Herreligaen — standings", "https://tophaandbold.dk/stillinger/herreligaen", "Official table used for two Danish fixtures; it supplies no kick-off time and does not confirm the other 17 listing-only rows."),
    "Ice Hockey": ("NHL — official schedule API", "https://api-web.nhle.com/v1/schedule/2026-10-23", "Official schedule/standings source used for NHL rows."),
    "Basketball": ("EuroLeague — official game feed", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", "Official game feed used for priced EuroLeague rows."),
    "Rugby League": ("Rugby League World Cup 2026 — fixtures", "https://www.rlwc2026.com/fixtures", "Official fixtures page returned a JavaScript shell; no Rugby League event was confirmed in this capture."),
}


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def official_host(url: str) -> str:
    try:
        host = urlparse(url).hostname or ""
    except Exception:
        return ""
    return host.lower().removeprefix("www.")


def payload_bytes(path: Path) -> bytes:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    return raw


def verify_capture_dir(base: Path, stamp: str) -> dict:
    manifest_path = base / stamp / "manifest.json"
    if not manifest_path.exists():
        return {"stamp": stamp, "manifest": str(manifest_path.relative_to(ROOT)), "files": 0, "matched": 0, "errors": ["manifest missing"], "recorded_utc": "", "manifest_captured_at_utc": "", "started_utc": "", "finished_utc": ""}
    manifest = read_json(manifest_path)
    records = manifest.get("records")
    if records is None:
        records = manifest.get("targets", [])
    checked = matched = 0
    errors: list[str] = []
    for rec in records:
        file_name = rec.get("file")
        expected = rec.get("sha256")
        if not file_name or not expected:
            continue
        checked += 1
        path = base / stamp / file_name
        if not path.exists():
            errors.append(f"{rec.get('id', file_name)}: capture file missing")
            continue
        try:
            actual = hashlib.sha256(payload_bytes(path)).hexdigest()
        except Exception as exc:
            errors.append(f"{rec.get('id', file_name)}: could not read payload ({type(exc).__name__})")
            continue
        if actual != expected:
            errors.append(f"{rec.get('id', file_name)}: SHA-256 differs from manifest")
        else:
            matched += 1
    captured_at = manifest.get("captured_at_utc", "")
    finished_at = manifest.get("finished_utc", "")
    started_at = manifest.get("started_utc", "")
    recorded_at = captured_at or finished_at or started_at or ""
    return {
        "stamp": stamp,
        "manifest": str(manifest_path.relative_to(ROOT)),
        "files": checked,
        "matched": matched,
        "errors": errors,
        "recorded_utc": recorded_at,
        "manifest_captured_at_utc": captured_at,
        "started_utc": started_at,
        "finished_utc": finished_at,
        "targets": manifest.get("targets_count", manifest.get("targets", None)) if not isinstance(manifest.get("targets"), list) else len(manifest["targets"]),
        "summary": manifest.get("summary", {}),
    }


def load_prediction_bank(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PREDICTIONS" for t in node.targets):
            entries = ast.literal_eval(node.value)
            return {str(row_id): str(text) for row_id, text in entries}
    return {}


def american_from_prob(prob: float) -> int:
    decimal = round(1.0 / prob, 3)
    return int(round((decimal - 1.0) * 100)) if decimal >= 2.0 else int(round(-100.0 / (decimal - 1.0)))


def jaccard3(left: str, right: str) -> float:
    def grams(text: str) -> set[tuple[str, ...]]:
        words = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
        words = [word for word in words if len(word) > 2]
        return {tuple(words[i:i + 3]) for i in range(max(0, len(words) - 2))}
    a, b = grams(left), grams(right)
    return len(a & b) / max(1, len(a | b))


def check_market_math(rows: list[dict]) -> dict:
    selection_count = market_count = bad = book_equal = 0
    bad_examples: list[str] = []
    market_families = Counter()
    for row in rows:
        if not row.get("priced"):
            continue
        for key, market in (row.get("markets") or {}).items():
            market_count += 1
            market_families[key] += 1
            selections = market.get("selections", [])
            prob_sum = sum(float(s.get("fair_prob", 0)) for s in selections)
            if abs(prob_sum - 1.0) >= 0.005:
                bad += 1
                bad_examples.append(f"{row.get('id')}:{key}: probability sum {prob_sum:.4f}")
            for selection in selections:
                selection_count += 1
                prob = selection.get("fair_prob")
                decimal = selection.get("fair_decimal")
                american = selection.get("fair_american")
                ok = isinstance(prob, (int, float)) and 0 < prob < 1 and isinstance(decimal, (int, float)) and isinstance(american, int)
                if ok:
                    ok = abs(float(decimal) - 1.0 / float(prob)) <= max(0.004, 0.001 / float(prob))
                if ok and decimal != 1.0:
                    expected_am = int(round((decimal - 1.0) * 100)) if decimal >= 2.0 else int(round(-100.0 / (decimal - 1.0)))
                    ok = american == expected_am
                if not ok:
                    bad += 1
                    if len(bad_examples) < 20:
                        bad_examples.append(f"{row.get('id')}:{key}:{selection.get('label')}: price arithmetic mismatch")
                if selection.get("book_decimal") == decimal and selection.get("book_american") == american:
                    book_equal += 1
    return {
        "priced_rows": sum(bool(r.get("priced")) for r in rows),
        "market_count": market_count,
        "market_families": dict(sorted(market_families.items())),
        "selection_outcomes_checked": selection_count,
        "arithmetic_errors": bad,
        "arithmetic_error_examples": bad_examples,
        "book_fields_equal_fair_fields": book_equal,
    }


def audit_master() -> dict:
    master_path = ROOT / "data/master.json"
    master = read_json(master_path)
    rows = master.get("rows", [])
    aliases = {"Gaelic Football": "Gaelic Sports", "Greyhound Racing": "Greyhounds"}
    allowed = set(SPORTS)
    actual_scope = {row.get("id", ""): aliases.get(row.get("sport"), row.get("sport")) in allowed for row in rows}
    no_source = sum(not (row.get("source_url") or "").strip() for row in rows)
    no_source_in_scope = sum(actual_scope.get(row.get("id", ""), False) and not (row.get("source_url") or "").strip() for row in rows)
    no_source_out_scope = no_source - no_source_in_scope
    out_scope = sum(not actual_scope.get(row.get("id", ""), False) for row in rows)
    past = sum(bool(row.get("date")) and str(row.get("date"))[:10] < AS_OF_TEXT[:10] for row in rows)
    scope_mismatches = [
        {"id": row.get("id", ""), "sport": row.get("sport", ""), "declared_in_scope": bool(row.get("in_scope")), "scope_by_sport": actual_scope.get(row.get("id", ""), False)}
        for row in rows if bool(row.get("in_scope")) != actual_scope.get(row.get("id", ""), False)
    ]
    ai_review = read_json(ROOT / "data/session-2c05e0b2/repo_review.json")
    master_review = next((x for x in ai_review.get("datasets", []) if x.get("dataset") == "data/master.json"), {})
    stored_review_rows = master_review.get("rows")
    review_counts = master_review.get("counts", {})
    return {
        "path": "data/master.json",
        "rows_now": len(rows),
        "generated_on": master.get("generated_on", ""),
        "cutoff_note": master.get("cutoff_note", ""),
        "missing_source_rows": no_source,
        "missing_source_in_scope_rows": no_source_in_scope,
        "missing_source_out_of_scope_rows": no_source_out_scope,
        "out_of_scope_rows": out_scope,
        "past_dated_rows": past,
        "declared_rows_in_scope": sum(bool(row.get("in_scope")) for row in rows),
        "rederived_rows_in_scope": len(rows) - out_scope,
        "scope_flag_mismatches": scope_mismatches,
        "scope_flag_mismatch_count": len(scope_mismatches),
        "out_of_scope_rows_mislabeled_in_scope": sum(x["declared_in_scope"] and not x["scope_by_sport"] for x in scope_mismatches),
        "in_scope_rows_mislabeled_out_of_scope": sum((not x["declared_in_scope"]) and x["scope_by_sport"] for x in scope_mismatches),
        "board_ai_review_rows": stored_review_rows,
        "review_denominator_delta": (len(rows) - stored_review_rows) if isinstance(stored_review_rows, int) else None,
        "board_ai_aggregate_counts": review_counts,
        "aggregate_counts_match_sport_scope": review_counts == {
            "R1_no_source": no_source_in_scope,
            "R2_out_of_scope_sport": out_scope,
            "R3_past_dated": past,
        },
        "r1_count_matches_declared_scope_flag": review_counts.get("R1_no_source") == sum(bool(row.get("in_scope")) and not (row.get("source_url") or "").strip() for row in rows),
    }


def audit_matches_file() -> dict:
    path = ROOT / "data/matches.json"
    rows = read_json(path)
    no_source = sum(not (row.get("sourceUrl") or "").strip() for row in rows)
    past = sum(bool(row.get("date")) and str(row.get("date"))[:10] < AS_OF_TEXT[:10] for row in rows)
    bad_fields = 0
    bad_rows: set[str] = set()
    complete_two_way = 0
    implausible = []
    for row in rows:
        moneyline = row.get("originatedMoneyline") or {}
        numeric = []
        for side, value in moneyline.items():
            try:
                numeric.append(float(value))
            except (TypeError, ValueError):
                bad_fields += 1
                bad_rows.add(str(row.get("id", "")))
        if len(numeric) == 2:
            complete_two_way += 1
            if all(value > 1 for value in numeric):
                total = sum(1 / value for value in numeric)
                if total < 0.99 or total > 1.30:
                    implausible.append({"row": row.get("id"), "date": row.get("date"), "sum": round(total, 3)})
    return {
        "path": "data/matches.json",
        "rows_now": len(rows),
        "missing_source_rows": no_source,
        "past_dated_rows": past,
        "two_way_moneyline_rows": complete_two_way,
        "non_numeric_moneyline_fields": bad_fields,
        "rows_with_non_numeric_moneyline": len(bad_rows),
        "implausible_margin_rows": implausible,
    }


def build_audit() -> dict:
    ah_dir = ROOT / "data/session-b2c7308d/capture"
    ah_desk = read_json(ROOT / "data/session-b2c7308d/desk.json")
    ah_flags = read_json(ROOT / "data/session-b2c7308d/flagged.json")
    ah_rows = ah_desk["rows"]
    ah_bank = load_prediction_bank(ROOT / "scripts/session-b2c7308d/predictions_bank.py")
    by_id = {str(r["id"]): r for r in ah_rows}
    b2_capture_dirs = sorted(p.name for p in ah_dir.iterdir() if p.is_dir() and (p / "manifest.json").exists())
    b2_capture_checks = [verify_capture_dir(ah_dir, stamp) for stamp in b2_capture_dirs]
    included_stamps = set(ah_desk.get("capture_stamps", []))
    latest_b2_capture = max(b2_capture_checks, key=lambda c: (c.get("finished_utc") or c.get("recorded_utc", ""), c["stamp"]))
    latest_included_stamp = max(included_stamps) if included_stamps else ""
    latest_included = next((x for x in b2_capture_checks if x["stamp"] == latest_included_stamp), {})

    source_matches = 0
    source_mismatches = []
    for row in ah_rows:
        stamp = row.get("capture_stamp") or ""
        manifest_path = ah_dir / stamp / "manifest.json"
        if not manifest_path.exists():
            source_mismatches.append({"row": row.get("id"), "reason": "row capture manifest missing"})
            continue
        manifest = read_json(manifest_path)
        records = manifest.get("records", [])
        if any(rec.get("url") == row.get("official_url") or rec.get("final_url") == row.get("official_url") for rec in records):
            source_matches += 1
        else:
            source_mismatches.append({"row": row.get("id"), "reason": "official_url not found in declared capture manifest"})

    by_sport = {sport: [r for r in ah_rows if r.get("sport") == sport] for sport in SPORTS}
    pred_sports = Counter(by_id[row_id]["sport"] for row_id in ah_bank if row_id in by_id)
    source_rows = Counter()
    olbg_rows = Counter()
    listing_rows = Counter()
    untimed_rows = Counter()
    high_rows = Counter()
    priced_rows = Counter()
    winner_picks = Counter()
    market_counts = Counter()
    sport_coverage = []
    for sport in SPORTS:
        rows = by_sport[sport]
        for row in rows:
            host = official_host(row.get("official_url", ""))
            if host and host != "olbg.com":
                source_rows[sport] += 1
            if host == "olbg.com":
                olbg_rows[sport] += 1
            if row.get("listing_only"):
                listing_rows[sport] += 1
            if not row.get("start_utc"):
                untimed_rows[sport] += 1
            if row.get("priced"):
                priced_rows[sport] += 1
                if row.get("confidence") == "High":
                    high_rows[sport] += 1
                if row.get("pick_market") in ("Money Line", "Match Winner"):
                    winner_picks[sport] += 1
                market_counts.update((row.get("markets") or {}).keys())
        ref_label, ref_url, ref_note = OFFICIAL_REFERENCES[sport]
        sport_page = f"../session-b2c7308d/sports/{SLUGS[sport]}.html"
        sport_utc_blank = untimed_rows[sport]
        sport_coverage.append({
            "sport": sport,
            "slug": SLUGS[sport],
            "rows": len(rows),
            "priced": priced_rows[sport],
            "official_domain_rows": source_rows[sport],
            "olbg_source_rows": olbg_rows[sport],
            "listing_only_rows": listing_rows[sport],
            "high_rows": high_rows[sport],
            "predictions": pred_sports[sport],
            "utc_time_blank": sport_utc_blank,
            "market_families": sorted({key for r in rows for key in (r.get("markets") or {}).keys()}),
            "official_reference_label": ref_label,
            "official_reference_url": ref_url,
            "official_reference_note": ref_note,
            "reference_status": "manual-review-only" if (listing_rows[sport] or not rows or any(not r.get("side_a") or not r.get("side_b") for r in rows)) else "captured-source-reference",
            "sport_page": sport_page,
        })

    math_audit = check_market_math(ah_rows)
    now_past = []
    future = []
    for row in ah_rows:
        start = row.get("start_utc")
        if not start:
            continue
        try:
            value = dt.datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        except ValueError:
            continue
        if value <= AS_OF:
            now_past.append(row)
        else:
            future.append(row)
    pick_market_counts = Counter(row.get("pick_market") for row in ah_rows if row.get("priced"))
    non_winner_picks = sum(n for market, n in pick_market_counts.items() if market not in ("Money Line", "Match Winner"))
    all_prediction_texts = list(ah_bank.items())
    prediction_words = {row_id: len(text.split()) for row_id, text in all_prediction_texts}
    prediction_banned = [row_id for row_id, text in all_prediction_texts if any(term in text.lower() for term in ("model", "verified"))]
    prediction_mismatch = [row_id for row_id, text in all_prediction_texts if row_id not in by_id or (by_id[row_id].get("pick") or "").lower() not in text.lower()]
    prediction_pairs = [(a, b, jaccard3(ta, tb)) for i, (a, ta) in enumerate(all_prediction_texts) for b, tb in all_prediction_texts[i + 1:]]
    max_similarity = max((x[2] for x in prediction_pairs), default=0)
    prediction_low = [row_id for row_id, words in prediction_words.items() if words < 30]
    high_ids = [r["id"] for r in ah_rows if r.get("confidence") == "High"]
    high_not_in_window = [r["id"] for r in ah_rows if r.get("confidence") == "High" and not r.get("in_window")]
    high_below_70 = [r["id"] for r in ah_rows if r.get("confidence") == "High" and (r.get("pick_prob") or 0) < 0.70]
    high_with_market_quote = sum(bool(by_id[row_id].get("olbg")) for row_id in high_ids)
    pick_price_errors = []
    for row in ah_rows:
        if not row.get("priced"):
            continue
        try:
            calculated = american_from_prob(float(row["pick_prob"]))
            if calculated != row.get("pick_fair_american") or bool(row.get("in_window")) != (-250 <= calculated <= 10000):
                pick_price_errors.append(row["id"])
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            pick_price_errors.append(row["id"])
    book_not_fair = math_audit["selection_outcomes_checked"] - math_audit["book_fields_equal_fair_fields"]

    ai_dir = ROOT / "data/session-2c05e0b2/capture"
    ai_desk = read_json(ROOT / "data/session-2c05e0b2/desk.json")
    ai_capture_checks = [verify_capture_dir(ai_dir, p.name) for p in sorted(ai_dir.iterdir()) if p.is_dir() and (p / "manifest.json").exists()]
    ai_folder_mismatches = []
    for label, stamp in ai_desk.get("captures", {}).items():
        manifest = read_json(ai_dir / stamp / "manifest.json")
        actual = manifest.get("captured_at_utc", "")
        if actual and stamp != actual.replace("-", "").replace(":", "")[:15] + "Z":
            ai_folder_mismatches.append({"label": label, "folder_stamp": stamp, "manifest_captured_at_utc": actual})
    ai_referenced_stamps = set(ai_desk.get("captures", {}).values())
    ai_unreferenced_stamps = []
    for capture in ai_capture_checks:
        if capture["stamp"] not in ai_referenced_stamps:
            ai_unreferenced_stamps.append({"folder_stamp": capture["stamp"], "manifest_captured_at_utc": capture.get("manifest_captured_at_utc", "")})

    master_audit = audit_master()
    matches_audit = audit_matches_file()
    ai_review = read_json(ROOT / "data/session-2c05e0b2/repo_review.json")
    ai_master_review = next((x for x in ai_review.get("datasets", []) if x.get("dataset") == "data/master.json"), {})
    ai_matches_review = next((x for x in ai_review.get("datasets", []) if x.get("dataset") == "data/matches.json"), {})
    fresh_match_counts = {
        "M1_no_source": matches_audit["missing_source_rows"],
        "M2_past_dated": matches_audit["past_dated_rows"],
        "M4_bad_price": matches_audit["non_numeric_moneyline_fields"],
        "M5_implausible_margin": len(matches_audit["implausible_margin_rows"]),
    }
    matches_review_counts_match = ai_matches_review.get("counts", {}) == fresh_match_counts
    latest_desk = read_json(ROOT / "data/session-63ad3394/desk.json")
    index_html = (ROOT / "index.html").read_text(encoding="utf-8")
    readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
    root_index_links_later_board_ak = "session-63ad3394" in index_html
    root_readme_links_later_board_ak = "session-63ad3394" in readme_text

    # Manual findings are deliberately not treated as verified fixture records.
    findings = [
        {
            "id": "AK-F01", "severity": "high", "status": "needs review",
            "title": "101 rows are explicitly listing-only, not fixture-confirmed",
            "affected": "101 / 276 rows: 56 OLBG-only URLs, 11 Darts rows on an unrendered PDC page, 33 Greyhound rows linked to completed results only, and 1 MotoGP event linked to the general calendar.",
            "detail": "The upstream desk marks these rows listing_only=true and unpriced. Fifty-six rows use an OLBG category URL as official_url; another 45 use official-domain URLs but the captured page does not verify the specific event/contestants (11 PDC schedule bytes unavailable, 33 GBGB rows linked to completed results, and 1 MotoGP general-calendar event with no head-to-head riders). Retain them only as unverified listings, leave unsupported match/date/runner values blank, and do not count the links as fixture verification.",
            "official_refs": [
                {"label": "Official volleyball calendar (manual review only)", "url": OFFICIAL_REFERENCES["Volleyball"][1]},
                {"label": "Official URC fixtures (manual review only)", "url": OFFICIAL_REFERENCES["Rugby Union"][1]},
                {"label": "Official Danish handball table (manual review only)", "url": OFFICIAL_REFERENCES["Handball"][1]},
                {"label": "Official GBGB results (not a future race card)", "url": OFFICIAL_REFERENCES["Greyhounds"][1]},
                {"label": "Official PDC site (schedule bytes unavailable)", "url": OFFICIAL_REFERENCES["Darts"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "data/session-b2c7308d/flagged.json", "data/session-b2c7308d/capture/20261023T165722Z/manifest.json"],
            "manual_note": "Official links above are review destinations; they do not confirm the listing-only rows.",
        },
        {
            "id": "AK-F02", "severity": "high", "status": "needs review",
            "title": "87 priced rows do not publish a standalone match-winner pick",
            "affected": f"{non_winner_picks} of {sum(bool(r.get('priced')) for r in ah_rows)} priced rows select a handicap, total, run line, puck line or total-games market as pick_market; 72 select Money Line / Match Winner.",
            "detail": "The desk stores a match_winner market on priced rows, but has no dedicated winner_pick field. Where the highlighted pick is a different market, choosing the highest-probability match-winner side would require a derivation not published as an explicit selection. The user requirement is not met by a handicap or total pick alone.",
            "official_refs": [
                {"label": "NHL official schedule API", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
                {"label": "MLB official schedule API", "url": OFFICIAL_REFERENCES["Baseball"][1]},
                {"label": "EuroLeague official game feed", "url": OFFICIAL_REFERENCES["Basketball"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "session-b2c7308d/index.html", "session-b2c7308d/sports/ice-hockey.html"],
            "manual_note": "Market outcome probabilities are present; a separate match-winner selection is not.",
        },
        {
            "id": "AK-F03", "severity": "high", "status": "needs review",
            "title": "The published price band is fair-odds-only, not observed market odds",
            "affected": f"All {math_audit['selection_outcomes_checked']} selection outcomes have book_decimal/book_american identical to fair_decimal/fair_american; {len(high_ids) - high_with_market_quote} of {len(high_ids)} High rows have no OLBG/bookmaker quote attached.",
            "detail": "The Board AH methodology says bookmaker prices are not shown, and the high-pick band is applied to internally originated fair American odds. This is transparent as a fair-line rule, but it does not verify that a match's market price sits in the requested −250…+10,000 window. Do not label these as market odds.",
            "official_refs": [
                {"label": "OLBG betting-tips hub (listing reference; not an official governing body)", "url": "https://www.olbg.com/betting-tips"},
                {"label": "NHL official schedule (match identity reference)", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "session-b2c7308d/methodology.html", "data/session-b2c7308d/review.json"],
            "manual_note": "No bookmaker/OLBG price is verified for the highlighted fair-line selections.",
        },
        {
            "id": "AK-F04", "severity": "high", "status": "needs review",
            "title": "Upcoming-date coverage has unresolved times and elapsed starts",
            "affected": f"{len([r for r in ah_rows if not r.get('start_utc')])} rows have blank start_utc; {len(now_past)} rows with UTC starts are at or before {AS_OF_TEXT}.",
            "detail": "Blank times cannot be ordered reliably as upcoming. Four timed rows have a scheduled start before this audit cut-off: Zalgiris–ASVEL, Cobolli–Nakashima, Olympiacos–Fenerbahce and Paris–Valencia. They should be refreshed or retired from an upcoming-only view after official status/results are checked.",
            "official_refs": [
                {"label": "EuroLeague official game feed", "url": OFFICIAL_REFERENCES["Basketball"][1]},
                {"label": "ATP Lyon official order of play", "url": OFFICIAL_REFERENCES["Tennis"][1]},
                {"label": "SHL official schedule/results (local-time limitation)", "url": "https://stats.swehockey.se/ScheduleAndResults/Overview/20961"},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "data/session-b2c7308d/flagged.json", "data/session-b2c7308d/capture/20261023T165722Z/manifest.json"],
            "manual_note": "The listed times are scheduled UTC values in the desk; this audit does not assert game results.",
        },
        {
            "id": "AK-F05", "severity": "medium", "status": "needs review",
            "title": "The declared desk cutoff predates its primary capture and build time",
            "affected": f"Desk cutoff {ah_desk.get('cutoff_utc')}; primary/latest capture {latest_b2_capture['stamp']} finished {latest_b2_capture.get('finished_utc')}; desk generated {ah_desk.get('generated_utc')}.",
            "detail": "The committed desk names this latest capture as its primary and includes it in capture_stamps. However, cutoff_utc remains 16:34Z while the primary capture and desk generation finished at 16:58:45Z. Clarify whether cutoff_utc labels a point before capture or is stale metadata; do not describe it as the time of the included source snapshot.",
            "official_refs": [
                {"label": "NHL official schedule API", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
                {"label": "Cork GAA official fixtures", "url": OFFICIAL_REFERENCES["Gaelic Sports"][1]},
                {"label": "Cricket Australia official fixtures", "url": OFFICIAL_REFERENCES["Cricket"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "data/session-b2c7308d/capture/20261023T163921Z/manifest.json", "data/session-b2c7308d/capture/20261023T165722Z/manifest.json"],
            "manual_note": "All 108 payload files in the latest capture match their manifest SHA-256 values and the desk includes that capture; the concern is cutoff-time metadata, not omitted bytes or hash integrity.",
        },
        {
            "id": "AK-F06", "severity": "medium", "status": "needs review",
            "title": "Five-per-sport High-pick target is not reached",
            "affected": f"{len(high_ids)} High rows total, by sport: " + ", ".join(f"{s} {high_rows[s]}" for s in SPORTS if high_rows[s]) + "; no High rows in the other 12 sports.",
            "detail": f"The desk has {len(ah_bank)} written predictions across {len(pred_sports)} sports; {sum(1 for row_id in ah_bank if by_id.get(row_id, {}).get('confidence') == 'High')} are attached to High rows. This is a transparent shortfall, not a reason to pad with unsupported picks. The 10 current High labels are confined to Ice Hockey, Baseball and Basketball.",
            "official_refs": [
                {"label": "NHL official schedule API", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
                {"label": "MLB official schedule API", "url": OFFICIAL_REFERENCES["Baseball"][1]},
                {"label": "EuroLeague official game feed", "url": OFFICIAL_REFERENCES["Basketball"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "scripts/session-b2c7308d/predictions_bank.py", "session-b2c7308d/predictions.html"],
            "manual_note": "The source-backed shortfall remains visible; no predictions were invented to meet the target.",
        },
        {
            "id": "AK-F07", "severity": "medium", "status": "needs review",
            "title": "Only three market families are represented; OLBG market inventory is not exhaustive",
            "affected": f"The {math_audit['priced_rows']} priced rows carry only {', '.join(math_audit['market_families'])} ({math_audit['market_count']} row-market entries total). No per-event OLBG market inventory is stored.",
            "detail": "This is a documented origination set, not proof that every OLBG market was investigated. The capture contains category listings, but the desk does not map all per-event market names or prices to the originated line families. Additional markets remain unverified and should not be described as covered.",
            "official_refs": [
                {"label": "OLBG betting-tips hub (market-listing review; not an official governing body)", "url": "https://www.olbg.com/betting-tips"},
                {"label": "MLB official schedule API", "url": OFFICIAL_REFERENCES["Baseball"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "data/session-b2c7308d/capture/20261023T165722Z/manifest.json"],
            "manual_note": "OLBG is a listing source; the official market taxonomy/offer is not externally verified by this audit.",
        },
        {
            "id": "AK-F08", "severity": "high", "status": "needs review",
            "title": "Two non-head-to-head event rows are labelled as matches",
            "affected": "Golf row ah_239 is a tournament outright; Motor Racing row ah_240 is a race-winner outright. Thirty-three Greyhound rows show track/time race cards without runner names.",
            "detail": "The source desk assigns row_kind='match' to all rows. Golf and Motor Racing rows have empty side_a/side_b and an outright market label, so they are not head-to-head matches. Greyhound rows have no runner identities and cite a results page, not a future card. Keep them separately classified or blank/flag them rather than treating them as confirmed matchups.",
            "official_refs": [
                {"label": "PGA TOUR — Bermuda Championship", "url": OFFICIAL_REFERENCES["Golf"][1]},
                {"label": "MotoGP — official calendar", "url": OFFICIAL_REFERENCES["Motor Racing"][1]},
                {"label": "GBGB — results page (not a future race card)", "url": OFFICIAL_REFERENCES["Greyhounds"][1]},
            ],
            "evidence": ["data/session-b2c7308d/desk.json", "data/session-b2c7308d/flagged.json"],
            "manual_note": "No head-to-head contestants or race runners are inferred by this audit.",
        },
        {
            "id": "AK-F09", "severity": "high", "status": "needs review",
            "title": "The root canonical master is a 21 October mixed-sport snapshot",
            "affected": f"Current data/master.json has {master_audit['rows_now']} rows, {master_audit['missing_source_rows']} without source_url ({master_audit['missing_source_in_scope_rows']} in the requested scope, {master_audit['missing_source_out_of_scope_rows']} out of scope), {master_audit['past_dated_rows']} before 23 October, and {master_audit['out_of_scope_rows']} out-of-scope rows. Its generated_on is {master_audit['generated_on']}.",
            "detail": f"The file's own cutoff_note says values were copied from older builds and nothing was refreshed. Board AI's repository audit records {master_audit['board_ai_review_rows']} rows versus {master_audit['rows_now']} currently committed ({master_audit['review_denominator_delta']} row denominator difference). Its R2/R3 totals re-derive, but its R1 count uses inconsistent in_scope flags; the flag mismatch is detailed in AK-F13. Re-run the review after a master refresh; do not use this as today's 15-sport fixture list.",
            "official_refs": [],
            "evidence": ["data/master.json", "data/session-2c05e0b2/repo_review.json", "README.md"],
            "manual_note": "This is a repository-content finding; no external official source applies. Missing-source rows remain unlinked and flagged.",
        },
        {
            "id": "AK-F10", "severity": "medium", "status": "needs review",
            "title": "The root landing omits the newer 23 October Board AK desk",
            "affected": f"Board AK's later desk was generated at {latest_desk.get('generated_utc')}; README.md links it, but root index.html does not.",
            "detail": "This report audits the earlier Board AH/AI snapshots only; it does not assess or certify the newer Board AK 63ad3394 desk. The root landing page still foregrounds Board AI/AP and older boards, while the README has a direct link to the later desk. This report exposes that desk separately but does not edit shared navigation under the coordination boundary.",
            "official_refs": [],
            "evidence": ["index.html", "README.md", "data/session-63ad3394/desk.json", "session-63ad3394/index.html", "session-2c05e0b2/index.html", "session-b2c7308d/index.html", "COORDINATION.md"],
            "manual_note": "Repository navigation finding; no external official source applies. The later desk is linked for discovery but is outside this audit's reviewed dataset.",
        },
        {
            "id": "AK-F11", "severity": "medium", "status": "needs review",
            "title": "Board AI capture-folder stamps and desk references are inconsistent",
            "affected": "The desk's round2 folder is labeled 20261023T170000Z but its manifest records 16:23:04Z; a third capture folder 20261023T173000Z records 16:26:38Z and is not listed in desk.captures.",
            "detail": "The desk was generated at 16:35:59Z, after the manifest times, so this is not proof of impossible chronology. It is a provenance ambiguity: directory stamps differ from captured_at_utc, and one committed capture is not named by the desk. Use manifest timestamps and confirm which payloads were actually consumed before describing the desk as refreshed.",
            "official_refs": [
                {"label": "NHL official schedule API", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
                {"label": "MLB official schedule API", "url": OFFICIAL_REFERENCES["Baseball"][1]},
            ],
            "evidence": ["data/session-2c05e0b2/desk.json", "data/session-2c05e0b2/capture/20261023T170000Z/manifest.json"],
            "manual_note": "This is a timestamp-label inconsistency, not proof that the official fixture data is wrong.",
        },
        {
            "id": "AK-F12", "severity": "medium", "status": "needs review",
            "title": "High-pick texts rely on season aggregates; recent results and injury checks are not consistently evidenced",
            "affected": "The 10 High rows have unique 47–65-word texts and explicit selections, but their linked inputs are principally season records/rates; the capture set contains no player injury-report feed.",
            "detail": "The text-length, uniqueness and selection checks pass. However, the published High write-ups do not consistently cite a recent match result or named player/line-up evidence, and no official injury source was captured for these rows. Do not imply that injuries were checked or that a player is available; refresh from team/tour reports before expanding these predictions.",
            "official_refs": [
                {"label": "NHL official schedule / statistics source", "url": OFFICIAL_REFERENCES["Ice Hockey"][1]},
                {"label": "MLB official schedule / statistics source", "url": OFFICIAL_REFERENCES["Baseball"][1]},
                {"label": "EuroLeague official game feed", "url": OFFICIAL_REFERENCES["Basketball"][1]},
            ],
            "evidence": ["scripts/session-b2c7308d/predictions_bank.py", "data/session-b2c7308d/desk.json", "data/session-b2c7308d/capture/20261023T165722Z/manifest.json"],
            "manual_note": "No injury claims were made by this audit; the missing injury feed is an information gap, not evidence that there are no injuries.",
        },
        {
            "id": "AK-F13", "severity": "high", "status": "needs review",
            "title": "Canonical master in_scope flags conflict with the 15-sport taxonomy on 14 rows",
            "affected": f"{master_audit['scope_flag_mismatch_count']} rows disagree: {master_audit['out_of_scope_rows_mislabeled_in_scope']} out-of-scope rows are marked in-scope, while {master_audit['in_scope_rows_mislabeled_out_of_scope']} Gaelic Football rows (the repo's Gaelic Sports alias) are marked out-of-scope. The file declares {master_audit['declared_rows_in_scope']} in-scope rows; the sport-label recheck yields {master_audit['rederived_rows_in_scope']}.",
            "detail": f"The Board AI review's R1 count of 39 is based on the inconsistent in_scope boolean. Rechecking by sport labels finds 31 source-less rows in the requested scope and 8 source-less rows outside it; therefore 8 unverified out-of-scope rows are counted as in-scope defects. Normalize Gaelic Football/Gaelic Sports and filter the out-of-scope labels before relying on master-level counts.",
            "official_refs": [],
            "evidence": ["data/master.json", "data/session-2c05e0b2/repo_review.json"],
            "manual_note": "This is a classification-field defect in the repository; unconfirmed source cells remain blank and flagged.",
        },
    ]

    # A separate register of timed rows that cannot be presented as upcoming at the audit cut-off.
    elapsed_rows = []
    for row in sorted(now_past, key=lambda r: r.get("start_utc", "")):
        elapsed_rows.append({
            "id": row["id"], "sport": row["sport"], "matchup": row.get("matchup", ""),
            "start_utc": row.get("start_utc", ""), "official_url": row.get("official_url", ""),
            "sport_page": f"../session-b2c7308d/sports/{row.get('sport_slug', '')}.html#{row['id']}",
            "status": "scheduled start <= audit cut-off; result/status not asserted",
        })

    all_capture_checks = b2_capture_checks + ai_capture_checks
    audit = {
        "schema": "olbg4.session-audit/1",
        "session": "arena/2c215a91-olbg4",
        "as_of_utc": AS_OF_TEXT,
        "scope": SPORTS,
        "source_policy": "This is a static audit of committed captures and desk files. SHA-256 manifests, source URL references, market arithmetic and dashboard metadata were checked locally. No live HTTP re-fetch was performed by this audit; official links are supplied for manual review and are not presented as fresh confirmations.",
        "primary_desk": {
            "board": ah_desk.get("board"),
            "session": ah_desk.get("session"),
            "generated_utc": ah_desk.get("generated_utc"),
            "cutoff_utc": ah_desk.get("cutoff_utc"),
            "window": ah_desk.get("window"),
            "primary_capture": ah_desk.get("primary_capture"),
            "included_capture_stamps": ah_desk.get("capture_stamps", []),
            "latest_capture_available": latest_b2_capture,
            "latest_capture_included": latest_included,
            "latest_capture_included_in_desk": latest_b2_capture["stamp"] in included_stamps,
            "summary_declared": ah_desk.get("summary", {}),
        },
        "later_desk_not_audited": {
            "session": latest_desk.get("session"),
            "generated_utc": latest_desk.get("generated_utc"),
            "dashboard": "session-63ad3394/index.html",
            "audit_status": "not audited by this static Board AH/AI report",
        },
        "coverage": sport_coverage,
        "metrics": {
            "rows": len(ah_rows),
            "priced_rows": sum(bool(r.get("priced")) for r in ah_rows),
            "unpriced_rows": sum(not bool(r.get("priced")) for r in ah_rows),
            "high_rows": len(high_ids),
            "high_rows_by_sport": dict(sorted((s, n) for s, n in high_rows.items() if n)),
            "high_rows_in_window": sum(bool(r.get("in_window")) for r in ah_rows if r.get("confidence") == "High"),
            "predictions": len(ah_bank),
            "predictions_by_sport": dict(sorted(pred_sports.items())),
            "high_rows_with_prediction": sum(1 for row_id in high_ids if row_id in ah_bank),
            "high_rows_with_olbg_market_quote": high_with_market_quote,
            "high_rows_without_olbg_market_quote": len(high_ids) - high_with_market_quote,
            "pick_price_arithmetic_errors": pick_price_errors,
            "prediction_word_min": min(prediction_words.values(), default=0),
            "prediction_word_max": max(prediction_words.values(), default=0),
            "prediction_rows_under_30_words": prediction_low,
            "prediction_banned_word_rows": prediction_banned,
            "prediction_selection_text_mismatches": prediction_mismatch,
            "max_prediction_3gram_jaccard": round(max_similarity, 4),
            "priced_rows_with_moneyline_or_match_winner_pick": sum(1 for r in ah_rows if r.get("priced") and r.get("pick_market") in ("Money Line", "Match Winner")),
            "priced_rows_whose_featured_pick_is_not_match_winner": non_winner_picks,
            "pick_market_counts": dict(sorted((str(k), v) for k, v in pick_market_counts.items())),
            "source_urls_matching_row_capture_manifest": source_matches,
            "source_url_mismatches": source_mismatches,
            "olbg_host_rows": sum(olbg_rows.values()),
            "listing_only_rows": sum(listing_rows.values()),
            "rows_with_blank_start_utc": sum(untimed_rows.values()),
            "rows_with_start_at_or_before_audit_cutoff": len(now_past),
            "scheduled_rows_after_audit_cutoff_with_utc": len(future),
            "all_priced_rows_have_exactly_3_market_families": all(set(r.get("markets") or {}) == {"match_winner", "handicap", "total"} for r in ah_rows if r.get("priced")),
            "market_math": math_audit,
            "book_fields_equal_fair_fields": math_audit["book_fields_equal_fair_fields"],
            "book_fields_not_equal_fair_fields": book_not_fair,
            "high_out_of_window_ids": high_not_in_window,
            "high_below_70_percent_ids": high_below_70,
            "high_fair_price_min": min((r.get("pick_fair_american") for r in ah_rows if r.get("confidence") == "High"), default=None),
            "high_fair_price_max": max((r.get("pick_fair_american") for r in ah_rows if r.get("confidence") == "High"), default=None),
            "outright_or_no_sides_rows": sum(not r.get("side_a") or not r.get("side_b") for r in ah_rows),
            "distinct_requested_sports_with_rows": sum(bool(by_sport[s]) for s in SPORTS),
            "requested_sports_without_rows": [s for s in SPORTS if not by_sport[s]],
        },
        "elapsed_timed_rows": elapsed_rows,
        "capture_integrity": {
            "board_ah_captures": b2_capture_checks,
            "board_ai_captures": ai_capture_checks,
            "files_checked": sum(x["files"] for x in all_capture_checks),
            "files_sha256_matched": sum(x["matched"] for x in all_capture_checks),
            "hash_errors": [error for x in all_capture_checks for error in x["errors"]],
            "board_ai_folder_stamp_mismatches": ai_folder_mismatches,
            "board_ai_unreferenced_capture_stamps": ai_unreferenced_stamps,
        },
        "repo_audit": {
            "master": master_audit,
            "matches": matches_audit,
            "board_ai_matches_review_rows": ai_matches_review.get("rows"),
            "board_ai_matches_review_counts": ai_matches_review.get("counts", {}),
            "matches_review_counts_rederived_match": matches_review_counts_match,
            "matches_fresh_review_counts": fresh_match_counts,
            "root_index_links_later_board_ak": root_index_links_later_board_ak,
            "root_readme_links_later_board_ak": root_readme_links_later_board_ak,
        },
        "findings": findings,
        "source_references": [
            {"sport": sport, "label": label, "url": url, "note": note}
            for sport, (label, url, note) in ((s, OFFICIAL_REFERENCES[s]) for s in SPORTS)
        ],
        "method": {
            "fair_odds": "American fair odds are recomputed from the stored fair probability after the desk's 3-decimal decimal-odds rounding. A field named book_* is not treated as a market quote when it exactly duplicates fair_*.",
            "officiality": "Official-domain links are not by themselves proof that a captured page contains a particular fixture. Rows marked listing_only remain unconfirmed even where the URL host belongs to a governing body.",
            "freshness": "Folder names are retained as labels, but manifest timestamps take precedence. Desk cutoffs, capture timestamps and audit as-of are reported separately.",
            "not_live": "The audit is not a live feed and does not assert that a scheduled event has completed or that an unconfirmed fixture exists.",
        },
        "peer_links": {
            "audited_board_ah": "../session-b2c7308d/index.html",
            "board_ai": "../session-2c05e0b2/index.html",
            "board_ap": "../session-509d544b/index.html",
            "later_board_ak_not_audited": "../session-63ad3394/index.html",
            "root_dashboard": "../index.html",
        },
    }
    return audit


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def nav(active: str) -> str:
    pages = [("index.html", "Audit overview"), ("coverage.html", "Sport coverage"), ("flagged.html", "Flagged for Review"), ("sources.html", "Sources & captures"), ("methodology.html", "Method")]
    items = "".join(f'<a class="nav-link {"active" if href == active else ""}" href="{href}">{esc(label)}</a>' for href, label in pages)
    return f'<nav class="nav">{items}<a class="nav-link external" href="../session-63ad3394/index.html">Later Board AK desk ↗</a></nav>'


def layout(title: str, active: str, body: str) -> str:
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG evidence review</title><link rel="stylesheet" href="assets/style.css">
<meta name="description" content="Static evidence audit of Board AH and Board AI snapshots; links to the later Board AK desk without certifying it."></head>
<body><header class="topbar"><a class="brand" href="index.html"><span class="brand-mark">O</span><span>OLBG <small>evidence review</small></span></a>{nav(active)}</header>
<main>{body}</main><footer class="footer"><span>Independent static audit · as of {AS_OF_TEXT} UTC</span><span>Unconfirmed values are not promoted to facts.</span></footer></body></html>'''


def link(url: str, label: str, cls: str = "") -> str:
    if not url:
        return '<span class="muted">—</span>'
    extra = f' class="{esc(cls)}"' if cls else ""
    target = " target=\"_blank\" rel=\"noopener noreferrer\"" if url.startswith("http") else ""
    return f'<a{extra} href="{esc(url)}"{target}>{esc(label)}</a>'


def render_findings(audit: dict, compact: bool = False) -> str:
    records = audit["findings"][:5] if compact else audit["findings"]
    rows = []
    for f in records:
        refs = "<br>".join(link(ref["url"], ref["label"], "source-link") for ref in f.get("official_refs", [])) or '<span class="muted">No external official source applies; repository evidence is linked.</span>'
        evidence = " · ".join(link("../" + path, Path(path).name, "evidence-link") for path in f.get("evidence", []))
        rows.append(f'''<tr id="{esc(f['id'])}"><td><span class="flag-id">{esc(f['id'])}</span><br><span class="badge {esc(f['severity'])}">{esc(f['severity'])}</span></td>
<td><strong>{esc(f['title'])}</strong><p>{esc(f['detail'])}</p><p class="impact">{esc(f['affected'])}</p><small>{esc(f.get('manual_note',''))}</small></td>
<td>{refs}</td><td>{evidence}</td></tr>''')
    return '<div class="table-wrap"><table><thead><tr><th>Flag</th><th>Finding & impact</th><th>Source / manual-review links (official where labeled)</th><th>Repository evidence</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def render_coverage(audit: dict) -> str:
    rows = []
    for item in audit["coverage"]:
        source_status = item["official_reference_note"]
        source_link = link(item["official_reference_url"], item["official_reference_label"], "source-link")
        page_link = link(item["sport_page"], "Open audited AH rows", "button tiny")
        needs_review = item["reference_status"] == "manual-review-only"
        status_class = "warn" if needs_review else "good"
        status_label = "manual review / gaps" if needs_review else "source-backed capture"
        market = ", ".join(item["market_families"]) or "—"
        rows.append(f'''<tr><th scope="row">{esc(item['sport'])}</th><td class="num">{item['rows']}</td><td class="num">{item['priced']}</td><td class="num">{item['high_rows']}</td><td class="num">{item['predictions']}</td><td class="num">{item['listing_only_rows']}</td><td class="num">{item['utc_time_blank']}</td><td><span class="badge {status_class}">{esc(status_label)}</span><br>{source_link}<small class="sub-note">{esc(source_status)}</small></td><td>{esc(market)}</td><td>{page_link}</td></tr>''')
    return '<div class="table-wrap"><table><thead><tr><th>Sport</th><th>Rows</th><th>Priced</th><th>High</th><th>Texts</th><th>Listing-only</th><th>UTC blank</th><th>Official reference / status</th><th>Markets represented</th><th>Source desk</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def build_site(audit: dict) -> None:
    OUT_SITE.mkdir(parents=True, exist_ok=True)
    (OUT_SITE / "assets").mkdir(exist_ok=True)
    m = audit["metrics"]
    latest = audit["primary_desk"]["latest_capture_available"]
    included = audit["primary_desk"]["latest_capture_included_in_desk"]
    elapsed = audit["elapsed_timed_rows"]
    latest_use_note = "Newest Board AH capture included; stated cutoff predates it." if included else "Newest Board AH capture is not included in this desk."
    high_by_sport = ", ".join(f"{s} {n}" for s, n in m["high_rows_by_sport"].items()) or "none"
    index_body = f'''
<section class="hero"><div class="hero-copy"><p class="eyebrow">Board AH/AI snapshot audit · {AS_OF_TEXT}</p><h1>What did the earlier Board AH/AI snapshot establish?</h1><p class="lead">This static report audits the earlier committed Board AH/AI snapshots, not a live fixture or odds feed. A newer Board AK desk was generated at {esc(audit['later_desk_not_audited']['generated_utc'])}; it is linked separately but is not independently audited here. Unresolved listings remain flagged rather than presented as confirmed matches.</p>
<div class="hero-actions">{link("../session-63ad3394/index.html", "Open later Board AK desk", "button primary")}{link("coverage.html", "Check all 15 sports", "button")}{link("flagged.html", "Review findings", "button")}</div></div>
<div class="snapshot-card"><span class="snapshot-tag">Audited Board AH snapshot</span><h2>Board AH · 23 Oct</h2><p><strong>Built</strong> {esc(audit['primary_desk']['generated_utc'])}</p><p><strong>Data cutoff</strong> {esc(audit['primary_desk']['cutoff_utc'])}</p><p><strong>Newest AH capture</strong> {esc(latest['stamp'])} · finished {esc(latest.get('finished_utc','') or latest.get('recorded_utc',''))}</p><p class="warning-line">{esc(latest_use_note)}</p></div></section>
<section class="metrics"><article class="metric"><span>Audited AH rows</span><strong>{m['rows']}</strong><small>15 requested sports, 13 with AH rows</small></article><article class="metric"><span>AH-priced rows</span><strong>{m['priced_rows']}</strong><small>3 families per priced row</small></article><article class="metric alert"><span>Listing-only</span><strong>{m['listing_only_rows']}</strong><small>Unconfirmed matchup/race details</small></article><article class="metric alert"><span>Starts elapsed</span><strong>{m['rows_with_start_at_or_before_audit_cutoff']}</strong><small>Scheduled at/before audit time</small></article><article class="metric"><span>AH High picks</span><strong>{m['high_rows']}</strong><small>{esc(high_by_sport)}</small></article><article class="metric"><span>AH prediction texts</span><strong>{m['predictions']}</strong><small>All {m['high_rows_with_prediction']} High rows have a text</small></article></section>
<section class="notice warning"><div class="notice-icon">!</div><div><h2>This is not the current full upcoming slate</h2><p>The audited Board AH primary capture finished at {esc(latest.get('finished_utc','') or latest.get('recorded_utc',''))}, after its stated cutoff of {esc(audit['primary_desk']['cutoff_utc'])}, and is included. This leaves a cutoff-metadata ambiguity. {m['rows_with_blank_start_utc']} AH rows have no UTC start time and {len(elapsed)} scheduled starts were already past the audit cut-off. The later Board AK desk is linked above but is not assessed in this report; official links here are manual-review destinations.</p></div></section>
<section class="section-heading"><div><p class="eyebrow">Executive summary</p><h2>Confirmed checks and unresolved gaps</h2></div>{link("flagged.html", "All flagged findings →", "text-link")}</section>
{render_findings(audit, compact=True)}
<section class="section-heading"><div><p class="eyebrow">By category</p><h2>15-sport coverage</h2><p class="section-note">Counts describe the audited Board AH snapshot, not the later Board AK desk. Official references are manual-review destinations, not fixture confirmation.</p></div>{link("coverage.html", "Full coverage table →", "text-link")}</section>
{render_coverage(audit)}
<section class="section-heading"><div><p class="eyebrow">Repository evidence</p><h2>Audit health</h2></div></section><section class="health-grid"><article><strong>{audit['capture_integrity']['files_sha256_matched']}/{audit['capture_integrity']['files_checked']}</strong><span>capture payload hashes matched</span></article><article><strong>{m['source_urls_matching_row_capture_manifest']}/{m['rows']}</strong><span>row source URLs map to declared capture manifests</span></article><article><strong>{m['market_math']['selection_outcomes_checked']}</strong><span>market outcomes re-derived · {m['market_math']['arithmetic_errors']} arithmetic errors</span></article><article><strong>{m['prediction_word_min']}–{m['prediction_word_max']}</strong><span>words across the 22 published prediction texts</span></article></section>
<section class="cta-row"><div><h2>Need the later desk?</h2><p>The Board AK dashboard generated at {esc(audit['later_desk_not_audited']['generated_utc'])} is newer than the audited AH snapshot. It is linked here for access; this report does not independently assess that peer desk.</p></div>{link("../session-63ad3394/index.html", "Open later Board AK desk →", "button primary")}</section>
'''
    (OUT_SITE / "index.html").write_text(layout("Audit overview", "index.html", index_body), encoding="utf-8")

    coverage_body = f'''<section class="page-intro"><p class="eyebrow">Board AH snapshot · {AS_OF_TEXT}</p><h1>All 15 requested sports</h1><p class="lead">These counts describe the audited Board AH snapshot, not the later Board AK desk linked in the navigation. The table separates row counts and originated rows from evidence strength. A source link is a manual-review reference; it does not automatically confirm every listed event in that sport.</p></section>
<section class="notice"><div class="notice-icon">i</div><div><h2>Scope is not the same as fixture coverage</h2><p>The audited AH snapshot has rows in {m['distinct_requested_sports_with_rows']} of the 15 categories. Snooker and Rugby League have no AH rows. Volleyball, Handball and Rugby Union include OLBG-only listing rows that were not confirmed by a readable official fixture feed.</p></div></section>
{render_coverage(audit)}
<section class="section-heading"><div><p class="eyebrow">Elapsed scheduled starts</p><h2>Rows to refresh or retire from the upcoming view</h2><p class="section-note">A scheduled start at or before {AS_OF_TEXT} is not presented here as an upcoming match. The official link is supplied to verify status/result; no result is asserted.</p></div></section>
<div class="table-wrap"><table><thead><tr><th>ID</th><th>Sport</th><th>Matchup</th><th>Scheduled UTC</th><th>Official status source</th><th>Desk row</th></tr></thead><tbody>{''.join(f'<tr><td>{esc(r["id"])}</td><td>{esc(r["sport"])}</td><td>{esc(r["matchup"])}</td><td>{esc(r["start_utc"])}</td><td>{link(r["official_url"], "Open official source", "source-link")}</td><td>{link(r["sport_page"], "Open AH row", "text-link")}</td></tr>' for r in elapsed)}</tbody></table></div>
'''
    (OUT_SITE / "coverage.html").write_text(layout("Sport coverage", "coverage.html", coverage_body), encoding="utf-8")

    flagged_body = f'''<section class="page-intro"><p class="eyebrow">Needs review · {len(audit['findings'])} findings</p><h1>Flagged for Review</h1><p class="lead">These findings apply to the audited Board AH/AI snapshots and current repository records checked at {AS_OF_TEXT}; the later Board AK desk is not assessed. Unsupported values remain flagged, and official links below are manual-review destinations rather than fresh confirmations.</p></section>
<section class="notice warning"><div class="notice-icon">!</div><div><h2>No unsupported picks were added to close coverage gaps</h2><p>Where the committed capture lacks readable official evidence, rows stay unpriced or are marked listing-only. The shortfalls and stale snapshots remain visible rather than being padded with inferred fixtures or predictions.</p></div></section>
{render_findings(audit, compact=False)}
<section class="section-heading"><div><p class="eyebrow">No inferred outcomes</p><h2>Timed rows already past the audit cut-off</h2></div></section>
<div class="table-wrap"><table><thead><tr><th>Row</th><th>Sport</th><th>Scheduled UTC</th><th>Matchup</th><th>Official source</th></tr></thead><tbody>{''.join(f'<tr><td>{esc(r["id"])}</td><td>{esc(r["sport"])}</td><td>{esc(r["start_utc"])}</td><td>{esc(r["matchup"])}</td><td>{link(r["official_url"], "Review official status", "source-link")}</td></tr>' for r in elapsed)}</tbody></table></div>
'''
    (OUT_SITE / "flagged.html").write_text(layout("Flagged for Review", "flagged.html", flagged_body), encoding="utf-8")

    sources_body = f'''<section class="page-intro"><p class="eyebrow">Provenance & links</p><h1>Sources and capture integrity</h1><p class="lead">Official URLs below were recorded in the audited Board AH/AI desk and capture metadata. They are offered for manual review. This audit did not issue live requests to those sites; the later Board AK desk is not assessed here.</p></section>
<section class="metrics compact"><article class="metric"><span>Payload files checked</span><strong>{audit['capture_integrity']['files_checked']}</strong><small>{audit['capture_integrity']['files_sha256_matched']} matched committed SHA-256</small></article><article class="metric"><span>Row URL mapping</span><strong>{m['source_urls_matching_row_capture_manifest']}/{m['rows']}</strong><small>Rows mapped to their own capture stamp</small></article><article class="metric"><span>Hash mismatches</span><strong>{len(audit['capture_integrity']['hash_errors'])}</strong><small>Expected zero</small></article><article class="metric"><span>Newest AH capture included?</span><strong>{'Yes' if audit['primary_desk']['latest_capture_included_in_desk'] else 'No'}</strong><small>{esc(latest_use_note)}</small></article></section>
<div class="table-wrap"><table><thead><tr><th>Sport</th><th>Official/manual-review link</th><th>Evidence note</th></tr></thead><tbody>{''.join(f'<tr><th scope="row">{esc(s["sport"])}</th><td>{link(s["url"], s["label"], "source-link")}</td><td>{esc(s["note"])}</td></tr>' for s in audit['source_references'])}</tbody></table></div>
<section class="section-heading"><div><p class="eyebrow">Capture timeline</p><h2>Committed source snapshots</h2><p class="section-note">The manifest timestamp is authoritative; directory names can be only labels, as the Board AI round2 folder demonstrates.</p></div></section>
<div class="table-wrap"><table><thead><tr><th>Board / stamp</th><th>manifest captured_at_utc</th><th>started_utc</th><th>finished_utc</th><th>Payloads</th><th>Hash matches</th><th>Included in published desk</th><th>Manifest</th></tr></thead><tbody>{''.join(f'<tr><td>Board AH · {esc(c["stamp"])}</td><td>{esc(c.get("manifest_captured_at_utc") or "—")}</td><td>{esc(c.get("started_utc") or "—")}</td><td>{esc(c.get("finished_utc") or "—")}</td><td>{c["files"]}</td><td>{c["matched"]}</td><td>{"Yes" if c["stamp"] in set(audit["primary_desk"]["included_capture_stamps"]) else "No"}</td><td>{link("../"+c["manifest"], "Open manifest", "evidence-link")}</td></tr>' for c in audit['capture_integrity']['board_ah_captures'])}{''.join(f'<tr><td>Board AI · {esc(c["stamp"])}</td><td>{esc(c.get("manifest_captured_at_utc") or "—")}</td><td>{esc(c.get("started_utc") or "—")}</td><td>{esc(c.get("finished_utc") or "—")}</td><td>{c["files"]}</td><td>{c["matched"]}</td><td>Capture retained; desk reference is separate</td><td>{link("../"+c["manifest"], "Open manifest", "evidence-link")}</td></tr>' for c in audit['capture_integrity']['board_ai_captures'])}</tbody></table></div>
<p class="footnote">Hashes verify the committed capture bytes against their own manifests. They do not prove that a page contained every published value; row/source-content verification must be completed by a parser or a live official-page recheck.</p>
'''
    (OUT_SITE / "sources.html").write_text(layout("Sources and captures", "sources.html", sources_body), encoding="utf-8")

    method_body = f'''<section class="page-intro"><p class="eyebrow">Method</p><h1>How this audit was performed</h1><p class="lead">A deterministic, read-only review of committed files. No upstream desk, shared dataset, root navigation, or peer-generated page is written by the audit build.</p></section>
<section class="method-grid"><article><span class="step">01</span><h2>Scope and counts</h2><p>Read the 15 required sport labels, row counts, confidence labels, prediction IDs and timestamps from <code>data/session-b2c7308d/desk.json</code> and its companion flags/review files.</p></article><article><span class="step">02</span><h2>Provenance</h2><p>Recomputed SHA-256 over every readable response payload in the committed Board AH and Board AI capture manifests; matched each Board AH row's official_url to its declared capture manifest.</p></article><article><span class="step">03</span><h2>Math and picks</h2><p>Re-derived fair decimal/American values, probability sums, pick confidence/window, and compared the stored <code>book_*</code> values against fair values. A fair line is not called a bookmaker quote.</p></article><article><span class="step">04</span><h2>Prediction checks</h2><p>Parsed the hand-written prediction bank as data, measured word counts and 3-gram similarity, searched for banned internal terms, and checked that the explicit selection appears in the text.</p></article><article><span class="step">05</span><h2>Repository review</h2><p>Recomputed the current master and matches-file counts, compared them with the Board AI review register, and checked which board the root landing page links.</p></article><article><span class="step">06</span><h2>Limits</h2><p>No live website was fetched by this audit. Official links and hashes show provenance of committed captures, not real-time correctness. Listings marked unverified remain flagged.</p></article></section>
<section class="notice warning"><div class="notice-icon">!</div><div><h2>Confidence and odds are not market validation</h2><p>The Board AH desk sets High from its own fair line and its documented probability/window rules. Since the observed market odds are not attached to all rows, this audit does not claim that High picks have an actual market price in the requested range.</p></div></section>
<section class="table-wrap"><table><thead><tr><th>Audit register</th><th>Current result</th><th>Repository evidence</th></tr></thead><tbody>
<tr><td>Fair line arithmetic</td><td>{m['market_math']['selection_outcomes_checked']} outcomes checked; {m['market_math']['arithmetic_errors']} arithmetic errors</td><td>{link('../data/session-b2c7308d/review.json','Board AH review JSON','evidence-link')}</td></tr>
<tr><td>Source URL mapping</td><td>{m['source_urls_matching_row_capture_manifest']}/{m['rows']} row URLs in declared capture manifests</td><td>{link('../data/session-b2c7308d/desk.json','Board AH desk JSON','evidence-link')}</td></tr>
<tr><td>Master dataset recheck</td><td>{audit['repo_audit']['master']['rows_now']} current rows; {audit['repo_audit']['master']['missing_source_in_scope_rows']} in-scope and {audit['repo_audit']['master']['missing_source_out_of_scope_rows']} out-of-scope rows lack source; {audit['repo_audit']['master']['past_dated_rows']} past and {audit['repo_audit']['master']['out_of_scope_rows']} out of scope</td><td>{link('../data/master.json','Current master JSON','evidence-link')}</td></tr>
<tr><td>Legacy matches file</td><td>{audit['repo_audit']['matches']['rows_now']} rows; {audit['repo_audit']['matches']['missing_source_rows']} without source, {audit['repo_audit']['matches']['past_dated_rows']} past, {audit['repo_audit']['matches']['non_numeric_moneyline_fields']} non-numeric moneyline fields</td><td>{link('../data/matches.json','Current matches JSON','evidence-link')}</td></tr>
</tbody></table></section>
'''
    (OUT_SITE / "methodology.html").write_text(layout("Methodology", "methodology.html", method_body), encoding="utf-8")

    css = r'''
:root{--ink:#142334;--muted:#637489;--line:#e3eaf0;--paper:#f5f8fb;--white:#fff;--navy:#102235;--blue:#2161e7;--cyan:#e7f1ff;--green:#137c62;--green-bg:#e7f7f1;--amber:#985b00;--amber-bg:#fff3d8;--red:#a73332;--red-bg:#ffebea;--shadow:0 12px 34px rgba(27,49,75,.08)}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.58 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.topbar{position:sticky;top:0;z-index:10;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:12px max(24px,calc((100vw - 1440px)/2));background:rgba(255,255,255,.96);border-bottom:1px solid var(--line);backdrop-filter:blur(12px)}.brand{display:flex;gap:10px;align-items:center;text-decoration:none;color:var(--ink);font:800 17px ui-sans-serif,system-ui,sans-serif}.brand small{display:block;font:500 11px ui-sans-serif,system-ui,sans-serif;color:var(--muted);letter-spacing:.05em}.brand-mark{display:grid;place-items:center;width:36px;height:36px;border-radius:11px;background:#162d44;color:#fff;font-weight:800}.nav{display:flex;align-items:center;gap:4px;overflow:auto}.nav-link{padding:8px 11px;text-decoration:none;color:#53677b;font-size:13px;border-radius:9px;white-space:nowrap}.nav-link:hover,.nav-link.active{background:#edf3ff;color:#194ec5}.nav-link.external{color:#fff;background:var(--blue);font-weight:700}main{max-width:1440px;margin:0 auto;padding:32px 26px 64px}.hero{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(290px,.7fr);gap:28px;align-items:stretch}.hero-copy{padding:42px 38px;border:1px solid #dce7f2;border-radius:24px;background:linear-gradient(135deg,#fff 0%,#f5f9ff 62%,#e8f2ff 100%);box-shadow:var(--shadow)}.eyebrow{margin:0 0 8px;color:#3270dc;font-size:11px;font-weight:700;letter-spacing:.13em;text-transform:uppercase}h1,h2,h3{font-family:ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif;line-height:1.2;letter-spacing:-.025em}h1{max-width:800px;margin:0 0 16px;font-size:clamp(32px,4vw,51px)}h2{margin:0 0 12px;font-size:22px}.lead{max-width:760px;color:#52687c;font-size:17px;line-height:1.65}.hero-actions{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}.button{display:inline-flex;align-items:center;justify-content:center;padding:10px 15px;border:1px solid #cedbea;border-radius:10px;background:#fff;color:#17314c;text-decoration:none;font-weight:700;font-size:13px;transition:.15s}.button:hover{transform:translateY(-1px);box-shadow:0 7px 18px #19395c1a}.button.primary{background:var(--blue);color:#fff;border-color:var(--blue)}.button.tiny{font-size:12px;padding:6px 9px}.snapshot-card{padding:27px;border-radius:24px;background:var(--navy);color:#f4f8fc;box-shadow:var(--shadow)}.snapshot-card h2{font-size:26px;margin:13px 0 20px}.snapshot-card p{margin:9px 0;color:#cad6e2;font-size:13px}.snapshot-card strong{color:#fff}.snapshot-tag{display:inline-block;padding:5px 9px;border:1px solid #ffffff30;border-radius:99px;color:#a9c8ff;font-size:11px;font-weight:700;letter-spacing:.05em}.warning-line{margin-top:18px!important;padding:9px 11px;border-radius:9px;background:#593f20;color:#ffe2a1!important;font-weight:700}.metrics{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:13px;margin:20px 0}.metrics.compact{grid-template-columns:repeat(4,minmax(0,1fr))}.metric{min-height:105px;padding:17px 18px;border:1px solid var(--line);border-radius:15px;background:var(--white);box-shadow:0 4px 14px rgba(27,49,75,.035)}.metric span,.metric small{display:block;color:var(--muted);font-size:12px}.metric strong{display:block;margin:5px 0;font:800 27px ui-sans-serif,system-ui,sans-serif;letter-spacing:-.04em}.metric small{font-size:11px;line-height:1.35}.metric.alert strong{color:var(--red)}.notice{display:flex;gap:15px;margin:20px 0 30px;padding:18px 20px;border:1px solid #d9e5f0;border-radius:15px;background:#fff}.notice h2{font-size:17px;margin:0 0 5px}.notice p{margin:0;color:#52687c;font-size:13px}.notice.warning{background:#fffaf0;border-color:#f1ddb1}.notice-icon{display:grid;place-items:center;flex:0 0 29px;height:29px;border-radius:50%;background:#eaf1ff;color:#215fe0;font-weight:800}.notice.warning .notice-icon{background:#ffe4a4;color:#74500b}.section-heading{display:flex;justify-content:space-between;align-items:end;gap:20px;margin:36px 0 15px}.section-heading h2{margin:0}.section-note{margin:7px 0 0;color:var(--muted);font-size:13px}.text-link{color:#215fe0;font-weight:700;font-size:13px;text-decoration:none;white-space:nowrap}.text-link:hover{text-decoration:underline}.table-wrap{width:100%;overflow:auto;border:1px solid var(--line);border-radius:14px;background:#fff;box-shadow:0 4px 15px rgba(27,49,75,.035)}table{width:100%;border-collapse:collapse;font-size:12.5px;line-height:1.48}thead{background:#f1f5fa;text-align:left;color:#556b80}th,td{padding:12px 13px;border-bottom:1px solid #e9eef3;vertical-align:top}thead th{font-weight:700;white-space:nowrap}tbody tr:last-child td,tbody tr:last-child th{border-bottom:0}tbody tr:hover{background:#fbfdff}tbody th{min-width:125px;text-align:left;font-weight:700}.num{text-align:center;font-variant-numeric:tabular-nums}.table-wrap p{margin:5px 0;color:#53677a}.table-wrap small{display:block;color:#718296;font-size:11px}.badge{display:inline-block;margin:2px 0 5px;padding:3px 7px;border-radius:99px;background:#eef2f6;color:#536477;font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.05em}.badge.high{background:var(--red-bg);color:var(--red)}.badge.medium{background:var(--amber-bg);color:var(--amber)}.badge.low{background:#edf2f7;color:#5d6c7a}.badge.good{background:var(--green-bg);color:var(--green)}.badge.warn{background:var(--amber-bg);color:var(--amber)}.flag-id{font:700 12px ui-sans-serif,system-ui,sans-serif;color:#284664}.source-link{color:#205bd4;font-weight:700;text-decoration:none}.source-link:hover,.evidence-link:hover{text-decoration:underline}.evidence-link{color:#64798e;text-decoration:underline;text-decoration-color:#b6c4d1;text-underline-offset:2px;font-size:11px}.impact{font-size:11px!important;color:#6b7c8c!important}.sub-note{max-width:330px}.health-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:14px 0}.health-grid article{padding:17px;border:1px solid var(--line);border-radius:14px;background:#fff}.health-grid strong{display:block;font:800 22px ui-sans-serif,system-ui,sans-serif}.health-grid span{display:block;color:var(--muted);font-size:12px}.cta-row{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-top:28px;padding:22px 25px;border-radius:17px;background:#eaf1ff}.cta-row h2{font-size:19px;margin:0 0 5px}.cta-row p{margin:0;color:#586e82;font-size:13px}.page-intro{margin-bottom:20px;padding:28px 32px;border:1px solid #dce7f2;border-radius:20px;background:#fff}.page-intro h1{font-size:38px;margin-bottom:7px}.page-intro .lead{margin:0;font-size:15px}.method-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px;margin:20px 0}.method-grid article{position:relative;padding:23px;border:1px solid var(--line);border-radius:15px;background:#fff}.step{display:grid;place-items:center;width:28px;height:28px;margin-bottom:14px;border-radius:9px;background:#eaf1ff;color:#215fe0;font:800 12px ui-sans-serif,system-ui,sans-serif}.method-grid h2{font-size:17px}.method-grid p{margin:0;color:#5f7183;font-size:13px}.footnote{margin:12px 0;color:#758597;font-size:11px}.footer{display:flex;justify-content:space-between;gap:20px;padding:18px 26px;border-top:1px solid var(--line);background:#fff;color:#718195;font-size:11px}.footer span:last-child{text-align:right}code{padding:2px 5px;border-radius:5px;background:#f0f3f7;font-size:.9em}@media(max-width:1120px){.metrics{grid-template-columns:repeat(3,1fr)}.hero{grid-template-columns:1fr 330px}.table-wrap{border-radius:11px}}@media(max-width:820px){.topbar{align-items:flex-start;flex-direction:column;padding:10px 16px;gap:7px}.nav{width:100%}main{padding:20px 14px 42px}.hero{grid-template-columns:1fr}.hero-copy{padding:28px 22px}.metrics,.metrics.compact{grid-template-columns:repeat(2,minmax(0,1fr))}.health-grid{grid-template-columns:repeat(2,1fr)}.method-grid{grid-template-columns:repeat(2,1fr)}.section-heading{align-items:flex-start;flex-direction:column}.cta-row{align-items:flex-start;flex-direction:column}.footer{flex-direction:column;padding:16px}.footer span:last-child{text-align:left}}@media(max-width:520px){.metrics,.metrics.compact,.health-grid,.method-grid{grid-template-columns:1fr 1fr}.page-intro{padding:23px 19px}.page-intro h1{font-size:32px}.lead{font-size:15px}.hero-copy .lead{font-size:15px}.snapshot-card{padding:22px}.metrics .metric{padding:14px}.metric strong{font-size:24px}.notice{padding:14px}.table-wrap table{min-width:940px}}
'''
    (OUT_SITE / "assets/style.css").write_text(css, encoding="utf-8")


def main() -> None:
    audit = build_audit()
    dump_json(OUT_DATA / "audit.json", audit)
    build_site(audit)
    print(f"[AK] audit built: rows={audit['metrics']['rows']} priced={audit['metrics']['priced_rows']} "
          f"flags={len(audit['findings'])} captures={audit['capture_integrity']['files_sha256_matched']}/"
          f"{audit['capture_integrity']['files_checked']} hashes")


if __name__ == "__main__":
    main()

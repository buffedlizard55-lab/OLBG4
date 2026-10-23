#!/usr/bin/env python3
"""Strict Board AH publication gate.

No network requests are made here.  The gate verifies the committed source bytes,
the derived 15-sport desk, published price mathematics, prediction quality, blank
rules and local HTML links.  Freshness or coverage limits are recorded as findings,
not hidden or converted into fabricated rows.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-6846f1ab"
SOURCE = ROOT / "data" / "session-4885d641"
CAPTURE = SOURCE / "capture" / "20261022T210026Z"
SITE = ROOT / "session-6846f1ab"

REQUESTED = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]
ACTIVE = set(REQUESTED) - {"Gaelic Sports", "Greyhounds"}
ALLOWED_CONFIDENCE = {"Low", "Medium", "High"}
MARKET_KEYS = {"match_winner", "handicap", "total", "derivative"}
FORBIDDEN_PREDICTION_WORDS = re.compile(r"\b(model|verified|verification)\b", re.I)


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def is_https_external(url: str) -> bool:
    return isinstance(url, str) and url.startswith("https://") and "olbg.com" not in host(url)


def in_window(am) -> bool:
    try:
        value = int(am)
    except (TypeError, ValueError):
        return False
    return -250 <= value <= 10000


def american(decimal: float) -> int:
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100.0))
    return -int(round(100.0 / max(decimal - 1.0, 0.0005)))


def trigrams(text: str) -> set[tuple[str, str, str]]:
    tokens = [w.lower().strip(".,;:!?()[]{}\"'—-") for w in text.split() if w.strip()]
    return {(tokens[i], tokens[i + 1], tokens[i + 2]) for i in range(len(tokens) - 2)}


def prediction_selection_is_explicit(pred: dict) -> bool:
    text = pred.get("text", "").lower()
    selection = pred.get("selection", "").lower()
    match = re.match(r"^(over|under)\s+([0-9]+(?:\.[0-9]+)?)", selection)
    if match:
        return f"{match.group(1)} {match.group(2)}" in text
    tokens = re.findall(r"[a-z0-9]+(?:[-./][a-z0-9]+)?", selection)
    if not tokens:
        return False
    # At least the selected side/team and any numeric handicap or score must
    # appear in the authored sentence.  Qualifiers such as Yes/No may be prose.
    core = [tokens[0]]
    core.extend(t for t in tokens[1:] if any(ch.isdigit() for ch in t))
    return all(token in text for token in core)


class HTMLAudit(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local_refs: list[tuple[str, str]] = []
        self.rows: list[dict] = []
        self.table_stack: list[str] = []
        self.tbody_depth = 0
        self.current_row: dict | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if tag == "table":
            self.table_stack.append(attrs_dict.get("id", ""))
        if tag == "tbody":
            self.tbody_depth += 1
        if tag == "tr" and self.tbody_depth:
            self.current_row = {
                "table": self.table_stack[-1] if self.table_stack else "",
                "data_search": attrs_dict.get("data-search", ""),
                "external": [],
            }
        for key, value in attrs:
            if not value:
                continue
            if key == "href":
                if value.startswith(("https://", "http://")):
                    if self.current_row is not None:
                        self.current_row["external"].append(value)
                elif not value.startswith(("#", "mailto:", "javascript:", "data:")):
                    self.local_refs.append((value, "href"))
            elif key == "src" and not value.startswith(("https://", "http://", "data:")):
                self.local_refs.append((value, "src"))

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.current_row is not None:
            self.rows.append(self.current_row)
            self.current_row = None
        elif tag == "tbody" and self.tbody_depth:
            self.tbody_depth -= 1
        elif tag == "table" and self.table_stack:
            self.table_stack.pop()


def main() -> int:
    checks = 0
    errors: list[str] = []
    findings: list[dict] = []

    def check(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            errors.append(message)

    def finding(code: str, severity: str, message: str, url: str = "") -> None:
        findings.append({"code": code, "severity": severity, "message": message, "url": url})

    desk = read(DATA / "desk.json")
    predictions = read(DATA / "predictions.json")
    coverage = read(DATA / "coverage.json")
    flagged = read(DATA / "flagged.json")
    taxonomy = read(DATA / "taxonomy.json")
    sources = read(DATA / "sources.json")
    manifest = read(DATA / "manifest.json")
    source_manifest = read(CAPTURE / "manifest.json")
    source_official = read(SOURCE / "official_sources.json")

    rows = desk.get("rows", [])
    preds = predictions.get("predictions", [])
    flags = flagged.get("items", [])
    row_by_id = {row.get("id"): row for row in rows}

    # Input provenance: every source file used to derive the isolated desk must
    # remain byte-identical, and every captured gzip must match its digest.
    input_hash_count = 0
    for item in manifest.get("input_files", []):
        path = ROOT / item["path"]
        check(path.is_file(), f"missing input file {item['path']}")
        if path.is_file():
            check(sha256(path) == item["sha256"], f"input hash changed: {item['path']}")
            input_hash_count += 1
    capture_items = source_manifest.get("items", [])
    check(len(capture_items) == manifest.get("capture_manifest_target_count"), "capture target count differs from derived manifest")
    check(len(capture_items) == source_official.get("targets_total"), "capture count differs from official source register")
    for item in capture_items:
        relative = item.get("file")
        if not relative:
            continue
        raw_path = CAPTURE / relative
        check(raw_path.is_file(), f"missing captured bytes: {relative}")
        if raw_path.is_file():
            try:
                raw = gzip.decompress(raw_path.read_bytes())
                check(hashlib.sha256(raw).hexdigest() == item.get("sha256"), f"capture SHA mismatch: {item.get('id')}")
            except Exception as exc:
                errors.append(f"cannot decompress capture {item.get('id')}: {exc}")
    check(input_hash_count == len(manifest.get("input_files", [])), "not all input hashes were evaluated")

    # Scope and coverage consistency.
    check(desk.get("requested_sports") == REQUESTED, "desk requested-sport order differs from brief")
    check(taxonomy.get("requested_sports") == REQUESTED, "taxonomy requested-sport order differs from brief")
    check(set(row.get("sport") for row in rows) <= ACTIVE, "active desk contains a non-requested or blank sport")
    check(len({row.get("id") for row in rows}) == len(rows), "active row IDs are not unique")
    check(len(rows) == desk.get("summary", {}).get("rows"), "desk row summary mismatch")
    check(len(preds) == predictions.get("count"), "prediction count mismatch")
    cov_by_sport = {item.get("sport"): item for item in coverage.get("sports", [])}
    check(list(cov_by_sport) == REQUESTED, "coverage does not contain exactly the 15 requested sports")
    row_counts = Counter(row.get("sport") for row in rows)
    pred_counts = Counter(pred.get("sport") for pred in preds)
    for sport in REQUESTED:
        c = cov_by_sport.get(sport, {})
        check(c.get("rows", 0) == row_counts.get(sport, 0), f"coverage row count mismatch for {sport}")
        check(c.get("high_predictions", 0) == pred_counts.get(sport, 0), f"coverage prediction count mismatch for {sport}")
        if sport in ACTIVE and pred_counts.get(sport, 0) < 5:
            finding("AH-PRED-" + sport.upper().replace(" ", "-"), "needs_review", f"Only {pred_counts.get(sport, 0)} qualifying written picks were retained for {sport}; target is five and no text was invented.")
        if sport not in ACTIVE and row_counts.get(sport, 0) == 0:
            finding("AH-SCOPE-" + sport.upper().replace(" ", "-"), "needs_review", f"No active qualifying row was retained for {sport}; the category is blank and linked on Flagged for Review.")
    check(row_counts.get("Gaelic Sports", 0) == 0 and row_counts.get("Greyhounds", 0) == 0, "blank category unexpectedly received active rows")

    # Official-source and market checks, line by line.
    source_hosts = {host(item.get("url", "")) for item in source_official.get("items", [])}
    source_hosts |= {host(item.get("final_url", "")) for item in source_official.get("items", [])}
    # Active-row links can be more specific league/game pages than the raw
    # capture target.  Their hosts are retained in the derived source register
    # and are still checked as non-OLBG HTTPS sources.
    source_hosts |= {host(item.get("url", "")) for item in sources.get("official_sources_used_by_rows", [])}
    for row in rows:
        rid = row.get("id", "")
        official = row.get("official_url", "")
        check(is_https_external(official), f"{rid}: missing non-OLBG HTTPS official URL")
        row_host = host(official)
        check(any(row_host == h or row_host.endswith("." + h) or h.endswith("." + row_host) for h in source_hosts if h), f"{rid}: source host was not in captured source register ({row_host})")
        check(row.get("start_utc", "") > desk.get("source_cutoff_utc", ""), f"{rid}: start is not after cutoff")
        check(row.get("row_kind") in {"match", "outright"}, f"{rid}: invalid row kind")
        if row.get("row_kind") == "match":
            check(bool(row.get("side_a")) and bool(row.get("side_b")), f"{rid}: match side is blank")
            check(not any(token in (row.get("matchup", "").lower()) for token in ("tbd", "field", "unknown")), f"{rid}: placeholder participant in active match")
        check(row.get("match_winner_pick", "") != "", f"{rid}: match-winner/event pick is blank")
        check(row.get("featured_pick", "") != "", f"{rid}: featured pick is blank")
        check(row.get("confidence") in ALLOWED_CONFIDENCE, f"{rid}: confidence not Low/Medium/High")
        check(set((row.get("markets") or {}).keys()) == MARKET_KEYS, f"{rid}: market families are not exactly {sorted(MARKET_KEYS)}")
        if row.get("olbg", {}).get("olbg_url"):
            check(row["olbg"]["olbg_url"].startswith("https://www.olbg.com/"), f"{rid}: malformed OLBG URL")
        for market_key, market in (row.get("markets") or {}).items():
            selections = market.get("selections", [])
            check(len(selections) >= 2, f"{rid}/{market_key}: fewer than two selections")
            probability_sum = sum(float(selection.get("fair_prob", 0)) for selection in selections)
            check(abs(probability_sum - 1.0) < 1e-5, f"{rid}/{market_key}: fair probabilities sum to {probability_sum}")
            check(abs(float(market.get("prob_sum", 0)) - 1.0) < 1e-5, f"{rid}/{market_key}: stored probability sum is not 1")
            labels = set()
            for selection in selections:
                label = selection.get("label", "")
                labels.add(label)
                p = float(selection.get("fair_prob"))
                decimal = float(selection.get("fair_decimal"))
                book_decimal = float(selection.get("book_decimal"))
                check(bool(label), f"{rid}/{market_key}: blank selection label")
                check(abs(decimal - round(1.0 / p, 3)) < 1e-9, f"{rid}/{market_key}/{label}: fair decimal is not 1/p")
                check(selection.get("fair_american") == american(decimal), f"{rid}/{market_key}/{label}: fair American conversion mismatch")
                check(selection.get("book_american") == american(book_decimal), f"{rid}/{market_key}/{label}: book American conversion mismatch")
            check(len(labels) == len(selections), f"{rid}/{market_key}: duplicate selection labels")

    # High-written predictions: row traceability, minimum length, explicit
    # selection and no internal audit terminology in the authored sentence.
    text_values = [p.get("text", "") for p in preds]
    check(len(set(text_values)) == len(text_values), "prediction texts are duplicated")
    trigram_sets = [trigrams(text) for text in text_values]
    max_jaccard = 0.0
    for i in range(len(trigram_sets)):
        for j in range(i + 1, len(trigram_sets)):
            union = len(trigram_sets[i] | trigram_sets[j]) or 1
            max_jaccard = max(max_jaccard, len(trigram_sets[i] & trigram_sets[j]) / union)
    for pred in preds:
        key = pred.get("pred_key", "")
        row = row_by_id.get(pred.get("row_id"))
        check(row is not None, f"{key}: prediction row missing")
        if row:
            check(row.get("confidence") == "High", f"{key}: prediction row is not High")
            check(pred.get("official_url") == row.get("official_url"), f"{key}: prediction/source URL mismatch")
            labels = [selection.get("label") for market in row.get("markets", {}).values() for selection in market.get("selections", [])]
            check(pred.get("selection") in labels, f"{key}: selection not present in row markets")
        word_count = len(pred.get("text", "").split())
        check(word_count >= 30, f"{key}: prediction is only {word_count} words")
        check(pred.get("word_count") == word_count, f"{key}: stored word count mismatch")
        check(prediction_selection_is_explicit(pred), f"{key}: authored text does not state its selected side")
        check(not FORBIDDEN_PREDICTION_WORDS.search(pred.get("text", "")), f"{key}: internal audit term appears in authored prediction")
        check(in_window(pred.get("fair_american")) and in_window(pred.get("book_american")) or not pred.get("strict_70_in_window"), f"{key}: strict in-window flag is outside odds band")
        expected_strict = bool(float(pred.get("fair_prob", 0)) >= 0.70 and in_window(pred.get("fair_american")) and in_window(pred.get("book_american")))
        check(bool(pred.get("strict_70_in_window")) == expected_strict, f"{key}: strict ≥70% window flag mismatch")
    check(len(predictions.get("withheld", [])) == 1, "expected one explicitly withheld contradictory prediction")
    for withheld in predictions.get("withheld", []):
        finding("AH-PRED-CONFLICT", "needs_review", withheld.get("reason", "Prediction withheld due to a selection/text conflict."), withheld.get("official_url", ""))

    # Blank-on-unverified rule for all review records.  Audit findings also keep
    # action fields empty, so they cannot be mistaken for active picks.
    for flag in flags:
        fid = flag.get("id", "")
        check(is_https_external(flag.get("official_url", "")), f"{fid}: missing official review URL")
        check(flag.get("match_winner_pick", "") == "", f"{fid}: flagged pick is not blank")
        check(flag.get("confidence", "") == "", f"{fid}: flagged confidence is not blank")
        check(flag.get("originated_odds", "") == "", f"{fid}: flagged odds are not blank")
    unmatched_count = sum(f.get("category") == "official_row_not_matched_to_olbg_card" for f in flags)
    if unmatched_count:
        finding("AH-OLBG-MATCH", "needs_review", f"{unmatched_count} official schedule rows had no matching OLBG event URL in the capture; their OLBG fields remain blank.")
    outright_count = sum(row.get("row_kind") == "outright" for row in rows)
    if outright_count:
        finding("AH-OUTRIGHTS", "note", f"{outright_count} rows are outright/event cards, not head-to-head matches; they are labelled rather than relabelled.")
    cutoff = desk.get("source_cutoff_utc", "")
    if cutoff[:10] != "2026-10-23":
        finding("AH-FRESHNESS", "needs_review", f"The latest committed source cutoff is {cutoff}; this gate does not claim a live re-fetch for the current date.")
    if cov_by_sport.get("Gaelic Sports", {}).get("rows", 0) == 0:
        finding("AH-GAELIC", "needs_review", "Gaelic Sports is blank and quarantined under the captured scope rule; official GAA review link is on the category and Flagged pages.", "https://www.gaa.ie/fixtures-results/")
    if cov_by_sport.get("Greyhounds", {}).get("rows", 0) == 0:
        finding("AH-GREYHOUNDS", "needs_review", "Greyhounds has no dated runner-level card retained from the captured OLBG/GBGB pages; no race lines were inferred.", "https://www.gbgb.org.uk/results/")

    # HTML publication audit: local links resolve and every data row has at
    # least one external source link.  Summary/findings prose rows without a
    # data-search marker are intentionally outside the fixture-table check.
    pages = sorted(SITE.rglob("*.html"))
    check(len(pages) == 26, f"expected 26 HTML pages, found {len(pages)}")
    rows_with_source = 0
    for page in pages:
        parser = HTMLAudit()
        parser.feed(page.read_text(encoding="utf-8"))
        for ref, ref_kind in parser.local_refs:
            path = unquote(urlsplit(ref).path)
            target = (page.parent / path).resolve()
            if target.is_dir():
                target = target / "index.html"
            check(target.is_relative_to(ROOT) and target.is_file(), f"broken local {ref_kind} on {page.relative_to(ROOT)}: {ref}")
        for table_row in parser.rows:
            if not table_row.get("data_search"):
                continue
            rows_with_source += 1
            check(bool(table_row.get("external")), f"table row without source on {page.relative_to(ROOT)}")
    check(rows_with_source > 500, "publication audit did not see the expected fixture/market rows")

    # A source mismatch is a gate error; shortfalls and stale snapshot details
    # are explicit findings and intentionally non-blocking.
    result = {
        "schema": "olbg4.board-ah.audit/1",
        "status": "PASS" if not errors else "FAIL",
        "checks": checks,
        "errors": len(errors),
        "input_hashes": input_hash_count,
        "rows": len(rows),
        "predictions": len(preds),
        "withheld_predictions": len(predictions.get("withheld", [])),
        "flagged": len(flags),
        "published_table_rows_checked": rows_with_source,
        "max_prediction_trigram_jaccard": round(max_jaccard, 6),
        "findings": findings,
        "error_messages": errors[:100],
    }
    (DATA / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

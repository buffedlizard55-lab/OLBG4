#!/usr/bin/env python3
"""Structural/source-gate checks for the Board GF static dashboard."""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "session-265b28e5"
AUDIT = json.loads((ROOT / "data/session-265b28e5/audit.json").read_text(encoding="utf-8"))
errors: list[str] = []
checks = 0


def check(ok: bool, message: str):
    global checks
    checks += 1
    if not ok:
        errors.append(message)


class Inspect(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables = {}
        self.current_table = None
        self.rows = 0
        self.links = []
        self.ids = set()
        self.scripts = []
        self.styles = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "table":
            self.current_table = attrs.get("id", f"table_{len(self.tables)}")
            self.tables[self.current_table] = 0
        elif tag == "tr" and self.current_table:
            self.tables[self.current_table] += 1
        elif tag == "a":
            self.links.append(attrs.get("href", ""))
        elif tag == "script" and attrs.get("src"):
            self.scripts.append(attrs["src"])
        elif tag == "link" and attrs.get("rel") == "stylesheet":
            self.styles.append(attrs.get("href", ""))

    def handle_endtag(self, tag):
        if tag == "table":
            self.current_table = None


def parse(path: Path):
    parser = Inspect()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


# Core audit invariants.
summary = AUDIT["summary"]
check(summary["covered_sports"] == 15, "Expected exactly 15 sports")
check(len(AUDIT["sports"]) == 15, "Coverage matrix must contain exactly 15 sports")
check(summary["olbg_future_unique_event_ids"] == 58, "Expected 58 future OLBG event IDs in fixed snapshot")
check(summary["future_olbg_events_with_manual_official_crosswalk"] == 4, "Expected four individually checked official fixture crosswalks")
check(summary["future_olbg_events_with_official_start_time_confirmed"] == 3, "Expected three crosswalk sources to state the official start time")
check(len(AUDIT.get("manual_olbg_hub_spot_checks", [])) == 3, "Expected three live OLBG hub spot-checks with explicit timestamp caveats")
check(all(sport.get("olbg_hub_url", "").startswith("https://www.olbg.com/") for sport in AUDIT["sports"]), "Every sport coverage row needs its OLBG hub source")
check(summary["release_ready_predictions"] == 0, "No prediction may pass the release gate in this audit")
check(summary["math_conversion_errors"] == 0, "Displayed historical line conversions must be arithmetically consistent")
check(summary["capture_payloads_hash_fail"] == 0, "No successful capture hash may fail")
check(len(AUDIT["current_olbg_events"]) == 58, "OLBG table row count changed")
check(all(event["olbg_url"].startswith("https://") for event in AUDIT["current_olbg_events"]), "Every OLBG event row needs its event link")
check(all(event["official_source_url"] or event["crosswalk_status"] == "not independently matched" for event in AUDIT["current_olbg_events"]), "Unmatched official-source values must remain explicitly blank")
check(all(not p["release_ready"] for p in AUDIT["numeric_prediction_candidates"]), "Numeric candidates must remain unreleased")
check(all(p["official_source_url"].startswith("https://") for p in AUDIT["numeric_prediction_candidates"]), "Every numeric candidate row requires its carried official URL")
check(len(AUDIT["market_rows"]) == 997, "Market outcomes count changed")
check(len(AUDIT["findings"]) == 10, "Expected ten explicit findings")
check(len(AUDIT["official_fixture_rows"]) == 114, "Expected 114 source-desk fixture rows")
DASHBOARD = json.loads((ROOT / "data/session-265b28e5/dashboard.json").read_text(encoding="utf-8"))
check(DASHBOARD.get("session") == "arena/265b28e5-olbg4", "Machine-readable dashboard manifest has the wrong session")
check(len(DASHBOARD.get("sports", [])) == 15, "Machine-readable dashboard manifest must link exactly 15 sport pages")
check(DASHBOARD.get("freshness") == "historical snapshot; not live refreshed", "Dashboard manifest must preserve historical freshness status")

# Every requested sport has a dedicated, linked static subpage.
for sport in AUDIT["sports"]:
    path = SITE / "sports" / f"{sport['slug']}.html"
    check(path.is_file(), f"Missing sport page: {path.relative_to(ROOT)}")
    if path.is_file():
        page = parse(path)
        check("../style.css" in page.styles, f"Sport page stylesheet missing: {sport['sport']}")
        check("../app.js" in page.scripts, f"Sport page script missing: {sport['sport']}")

# Required landing pages and generated table rows.
expected_pages = {
    "index.html": "index", "olbg.html": "olbg", "fixtures.html": "fixtures",
    "picks.html": "picks", "markets.html": "markets", "sources.html": "sources",
    "flagged.html": "flagged", "methodology.html": "methodology", "coverage.html": "coverage",
}
for name in expected_pages:
    path = SITE / name
    check(path.is_file(), f"Missing dashboard page {name}")
    if not path.is_file():
        continue
    text = path.read_text(encoding="utf-8")
    parser = parse(path)
    check("<!doctype html>" in text.lower(), f"Invalid HTML document shell: {name}")
    check("Flagged for Review" in text, f"Missing review-page reference in {name}")
    check("localhost" not in text.lower() and "127.0.0.1" not in text.lower(), f"Localhost URL found in {name}")
    check("style.css" in ''.join(parser.styles), f"Stylesheet not included in {name}")
    check("app.js" in ''.join(parser.scripts), f"Script not included in {name}")

# High-value table integrity checks (tr includes header row).
for file_name, table_id, expected_data_rows in [
    ("olbg.html", "olbgEvents", 58),
    ("fixtures.html", "fixtureRows", 114),
    ("picks.html", "candidateRows", 5),
    ("markets.html", "marketRows", 997),
    ("sources.html", "crosswalkRows", 4),
    ("sources.html", "captureTable", 128),
    ("coverage.html", "coverageTable", 15),
    ("flagged.html", "flagRows", 10),
    ("flagged.html", "mismatchRows", 5),
]:
    parser = parse(SITE / file_name)
    actual = parser.tables.get(table_id, 0)
    check(actual == expected_data_rows + 1, f"{file_name}#{table_id}: expected {expected_data_rows} data + 1 header rows, got {actual}")

# Check every OLBG row has an OLBG link and has no invented governing source.
olbg_html = (SITE / "olbg.html").read_text(encoding="utf-8")
for event in AUDIT["current_olbg_events"]:
    check(event["olbg_url"] in olbg_html, f"OLBG listing link absent from rendered table: {event['event_id']}")
    if not event["official_source_url"]:
        # The unmatched badge is rendered instead of a fabricated governing-body link.
        event_row = next((r for r in AUDIT["current_olbg_events"] if r["event_id"] == event["event_id"]), None)
        check(event_row is not None and event_row["crosswalk_status"] == "not independently matched", f"Unmatched event should remain flagged: {event['event_id']}")

# Resolve every local HTML hyperlink and static asset in the new site.
for html_path in sorted(SITE.rglob("*.html")):
    parser = parse(html_path)
    for asset in parser.scripts + parser.styles:
        local_asset = (html_path.parent / asset).resolve()
        check(local_asset.exists(), f"Missing asset in {html_path.relative_to(ROOT)}: {asset}")
    for href in parser.links:
        if not href or href.startswith("#"):
            continue
        parts = urlsplit(href)
        if parts.scheme or parts.netloc:
            continue
        local_path = (html_path.parent / parts.path).resolve()
        check(local_path.exists(), f"Broken local link in {html_path.relative_to(ROOT)}: {href}")

# Check every retained fixture and market row displays its carried source link.
for row in AUDIT["official_fixture_rows"]:
    check(row["official_source_url"].startswith("https://"), f"Fixture row has no HTTPS carried citation: {row['id']}")
    if row["manual_match_source_url"]:
        check(row["manual_match_source_url"].startswith("https://"), f"Manual crosswalk missing HTTPS source: {row['id']}")
for capture in AUDIT["capture_checks"]:
    check(capture.get("url", "").startswith("https://"), f"Capture row missing its source URL: {capture['id']}")
for outcome in AUDIT["market_rows"]:
    check(outcome["official_source_url"].startswith("https://"), f"Market row has no carried source URL: {outcome['row_id']}")

# The independently served GF landing page must own the executive summary and review route;
# the shared root dashboard is generated by another board and is intentionally read-only.
landing = (SITE / "index.html").read_text(encoding="utf-8")
check("EXECUTIVE SUMMARY" in landing and "Coverage by sport" in landing, "Board GF landing page is missing its summary or sport index")
check('href="flagged.html"' in landing, "Board GF landing page is missing its Flagged for Review route")

# User-facing prediction content must not call the unreleased records forecasts.
picks = (SITE / "picks.html").read_text(encoding="utf-8")
check("0 current High-confidence picks" in picks or "No High-confidence picks" in picks, "Pick gate is not explicit on the pick page")
check("not approved picks" in picks.lower(), "Pick screen must explicitly state candidates are not approved")
check(not re.search(r"<article[^>]*class=\"prediction", picks), "Unverified prediction cards should not be published")

if errors:
    print(f"FAIL: {len(errors)} issues across {checks} checks")
    for message in errors:
        print(" -", message)
    raise SystemExit(1)
print(f"PASS: {checks} structural, scope, source-link, gate, and page checks")

#!/usr/bin/env python3
"""Independent, offline validation for Board AH."""
from __future__ import annotations

import argparse
import collections
import html.parser
import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SESSION = "session-8860f8f7"
DATA = ROOT / "data" / SESSION
SITE = ROOT / SESSION
SCOPE = DATA / "target_scope.json"
LISTINGS = DATA / "listing_observations.json"
LEDGER = DATA / "source_ledger.json"
DESK = DATA / "desk.json"
AUDIT = DATA / "market_audit.json"
PREDICTIONS = DATA / "predictions.json"
HISTORY = DATA / "history.json"
COVERAGE = DATA / "coverage.json"
FLAGS = DATA / "flags.json"
REPORT = DATA / "verification.json"


def read(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def american_value(p: float) -> float:
    if p >= 0.5:
        return -100 * p / (1 - p)
    return 100 * (1 - p) / p


def close(a: float, b: float, tol: float = 0.0011) -> bool:
    return abs(a - b) <= tol


class LinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.in_table = False
        self.row_links = []
        self.table_rows = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and "href" in d:
            self.links.append(d["href"])
        if tag == "table":
            self.in_table = True
        if tag == "tr" and self.in_table:
            self.row_links = []

    def handle_endtag(self, tag):
        if tag == "tr" and self.in_table:
            self.table_rows.append(self.row_links)
            self.row_links = []
        if tag == "table":
            self.in_table = False

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)


class TableRowLinkParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.row_has_official = False
        self.table_rows = []
        self.current_href = None
        self.row_text = ""
        self.rows_with_data = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "table":
            self.in_table = True
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.row_has_official = False
            self.row_text = ""
        elif tag == "a" and self.in_row:
            self.current_href = d.get("href")

    def handle_data(self, data):
        if self.in_row:
            self.row_text += data

    def handle_endtag(self, tag):
        if tag == "a" and self.in_row:
            if self.current_href:
                host = urlparse(self.current_href).hostname or ""
                if any(d in host for d in ("nba.com", "nhl.com", "mlb.com", "gaa.ie")):
                    self.row_has_official = True
            self.current_href = None
        elif tag == "tr" and self.in_row:
            if self.row_text.strip():
                self.rows_with_data.append((self.row_has_official, self.row_text.strip()))
            self.in_row = False
        elif tag == "table":
            self.in_table = False


def run_checks() -> list[dict]:
    scope = read(SCOPE)
    listings = read(LISTINGS)
    ledger = read(LEDGER)
    desk = read(DESK)
    audit = read(AUDIT)
    predictions = read(PREDICTIONS)
    history = read(HISTORY)
    coverage = read(COVERAGE)
    flags = read(FLAGS)
    checks: list[dict] = []

    def check(name: str, ok: bool, detail: str):
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Scope and source-ledger integrity.
    categories = scope.get("categories", [])
    slugs = [c.get("slug") for c in categories]
    labels = [c.get("label") for c in categories]
    check("Exactly 15 in-scope categories", len(categories) == 15, f"Found {len(categories)}.")
    check("Unique scope identifiers", len(set(slugs)) == len(slugs) and len(set(labels)) == len(labels), "Category slugs and labels are unique.")
    priced_categories = {c["slug"] for c in categories if c["slug"] not in {"gaelic-sports", "greyhounds"}}
    check("13 priced-capable + Gaelic + Greyhounds scope", len(priced_categories) == 13 and {c["slug"] for c in categories} - priced_categories == {"gaelic-sports", "greyhounds"}, "Scope includes the exact 15-category interpretation.")
    check("Gaelic Sports includes both OLBG hubs", len(next(c for c in categories if c["slug"] == "gaelic-sports")["olbg_hubs"]) == 2, "Gaelic Football ID 25 and Hurling ID 26 are present.")
    check("16 live hub rechecks recorded", len(listings["latest_hub_recheck"]["results"]) == 16, f"Found {len(listings['latest_hub_recheck']['results'])} separately checked hubs.")
    check("Current page-reader hash limitation disclosed", listings.get("raw_page_bytes_saved") is False and ledger.get("extracted_page_response_hashes") is None, "No unsupported raw-response hash claim.")
    check("Source-ledger current reads have direct URLs", all(x.get("url", "").startswith("https://") for x in ledger["current_checks"]), "All current official checks link to HTTPS sources.")
    snapshot_entries = ledger.get("provider_snapshot_2026_10_23T11_35Z", [])
    snapshot_meta_ok = False
    snapshot_detail = "Provider fetch metadata could not be reconciled."
    try:
        snapshot_paths = {x.get("snapshot_file") for x in snapshot_entries}
        if len(snapshot_paths) == 1 and None not in snapshot_paths:
            snapshot_data = read(ROOT / next(iter(snapshot_paths)))
            fetches = [r for sport in snapshot_data.get("providers", {}).values() if isinstance(sport, dict) for r in sport.get("fetch_log", [])]
            missing_meta = []
            for entry in snapshot_entries:
                retrieved = entry.get("retrieved_utc", "").replace("Z", "+00:00")
                matched = [r for r in fetches if r.get("sha256") == entry.get("reported_sha256") and r.get("url") == entry.get("url")]
                if not any(
                    r.get("status") == entry.get("http_status")
                    and r.get("bytes") == entry.get("bytes")
                    and r.get("retrieved_utc") == retrieved
                    for r in matched
                ):
                    missing_meta.append(entry.get("id", "unknown"))
            snapshot_meta_ok = len(snapshot_entries) == 5 and not missing_meta
            snapshot_detail = f"Checked {len(snapshot_entries)} ledger entries against snapshot providers.fetch_log; missing or mismatched: {missing_meta}."
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    check("Provider snapshot byte counts and hashes reconciled", snapshot_meta_ok, snapshot_detail)

    events = desk.get("events", [])
    provider = [e for e in events if e.get("provider_fixture_id")]
    listing_only = [e for e in events if not e.get("provider_fixture_id")]
    per_sport = collections.Counter(e["sport"] for e in provider)
    check("16 event observations persisted", len(events) == 16, f"Found {len(events)} rows.")
    check("15 provider crossmatches; 1 listing-only row", len(provider) == 15 and len(listing_only) == 1, f"Found {len(provider)} and {len(listing_only)}.")
    check("Crossmatches are exactly 12 NBA, 2 NHL, 1 MLB", per_sport == {"Basketball": 12, "Ice Hockey": 2, "Baseball": 1}, f"Counts: {dict(per_sport)}.")
    check("Every event row carries an official review URL", all(e.get("official_source_url", "").startswith("https://") for e in events), "All published rows carry an official-source/manual-review URL.")
    check("Every crossmatch has an official schedule URL", all(e.get("official_schedule_url", "").startswith("https://") for e in provider), "All provider rows carry a second official schedule/API reference.")
    check("All current event source URLs use the expected governing-body domains", all(
        (e["sport"] == "Basketball" and (urlparse(e["official_source_url"]).hostname or "").endswith("nba.com"))
        or (e["sport"] == "Ice Hockey" and (urlparse(e["official_source_url"]).hostname or "").endswith("nhl.com"))
        or (e["sport"] == "Baseball" and (urlparse(e["official_source_url"]).hostname or "").endswith("mlb.com"))
        for e in provider), "NBA, NHL and MLB rows link to their governing bodies.")
    check("All OLBG event references use OLBG", all((urlparse(e.get("olbg_url", "")).hostname or "").endswith("olbg.com") for e in events), "Every event row has an OLBG review link.")
    check("OLBG recheck discrepancy is retained", all("not reproduced" in e.get("olbg_latest_status", "").lower() or e["sport"] == "Gaelic Sports" for e in provider), "No earlier card is presented as a reaffirmed active listing.")

    # NBA withheld purity and explicit mapping.
    nba = [e for e in provider if e["sport"] == "Basketball"]
    expected_nba = {
        "nba-0022600099", "nba-0022600008", "nba-0022600097", "nba-0022600094",
        "nba-0022600096", "nba-0022600095", "nba-0022600009", "nba-0022600098",
        "nba-0022600100", "nba-0022600101", "nba-0022600102", "nba-0022600103",
    }
    check("NBA event-ID map matches the 12 observed cards", {e["id"] for e in nba} == expected_nba, "Exact provider fixture IDs are used.")
    check("All 12 NBA markets and picks are withheld", all(e["market_status"] == "withheld" and not e["own_markets"] and not e["winner_pick"] for e in nba), "No NBA price, market or pick was inferred.")
    check("NBA sample gate is under 20 games", all(e["minimum_training_sample"] is not None and e["minimum_training_sample"] < e["required_training_sample"] == 20 for e in nba), "Sample minimum is below the stated 20-game requirement.")

    # Listing-only Gaelic row must not acquire an inferred start time, side orientation or pick.
    gaelic = listing_only[0] if listing_only else {}
    check("Gaelic listing-only row remains unconfirmed and unpriced", bool(gaelic) and gaelic.get("sport") == "Gaelic Sports" and gaelic.get("official_fixture_status") == "unconfirmed; listing-only row" and gaelic.get("start_utc") is None and not gaelic.get("own_markets") and gaelic.get("winner_pick") is None, "Exact Hurling club fixture was not confirmed.")
    check("Gaelic listing does not infer home/away orientation", bool(gaelic) and gaelic.get("home") is None and gaelic.get("away") is None and gaelic.get("teams") == ["Ballyhale Shamrocks", "Tullaroan"], "Only the OLBG-listed pairing order is retained.")

    # Pricing integrity: recompute fair and margin prices; probabilities sum to one per market line.
    all_markets = [m for e in events for m in e.get("own_markets", [])]
    check("42 originated selections from 3 fixtures", len(all_markets) == 42 and audit.get("selection_count") == 42, f"Found {len(all_markets)} selection rows.")
    priced_events = [e for e in events if e["market_status"] == "priced"]
    check("Only the two NHL and one MLB fixtures are priced", {e["id"] for e in priced_events} == {"nhl-2026020166", "nhl-2026020167", "mlb-849805"}, f"Priced fixtures: {[e['id'] for e in priced_events]}.")
    check("Every published market probability is valid", all(0 < m["probability"] < 1 for m in all_markets), "All probabilities are inside (0,1).")
    check("Fair decimal prices re-derived as 1/p", all(close(m["fair_decimal"], 1 / m["probability"]) for m in all_markets), "All fair decimal odds recomputed.")
    check("Fair American prices re-derived from probability", all(close(m["fair_american_value"], american_value(m["probability"])) for m in all_markets), "All fair American prices recomputed.")
    check("Margin price uses 4.5% hold and is separate", all(m["margin_assumption"] == 0.045 and close(m["margin_decimal"], 1 / (m["probability"] * 1.045), 0.0012) for m in all_markets), "Margin-adjusted decimal prices recomputed independently.")
    check("Fair-odds-band flags re-derived correctly", all(m["fair_in_band"] == (-250 <= american_value(m["probability"]) <= 10000) for m in all_markets), "The band test uses fair American prices, not margin prices.")
    family_counts = collections.Counter(m["family"] for m in all_markets)
    check("All three market families explored", family_counts == {"moneyline": 6, "handicap": 18, "total": 18}, f"Family counts: {dict(family_counts)}.")
    sums = collections.defaultdict(float)
    for m in all_markets:
        sums[(m["fixture_id"], m["family"], m.get("line_group"))] += m["probability"]
    check("Every two-outcome market line sums to one", bool(sums) and all(close(value, 1.0, 0.0002) for value in sums.values()), f"Checked {len(sums)} line groups.")
    check("Exactly two ≥70% selections are outside the fair window", audit.get("high_probability_outside_window_count") == 2 and len(audit.get("high_probability_outside_window", [])) == 2, "Both candidates remain visible as outside-window values.")
    expected_high = {("nhl-2026020166", "Over 5.5"), ("nhl-2026020167", "Under 8.5")}
    actual_high = {(m["fixture_id"], m["selection"]) for m in audit.get("high_probability_outside_window", [])}
    check("Outside-window candidates are the two audited NHL totals", actual_high == expected_high, f"Candidates: {sorted(actual_high)}.")
    check("No ≥70% selection passes the fair odds window", audit.get("high_probability_in_window_count") == 0 and not audit.get("eligible_high_selections"), "No in-window High selection.")
    check("No High prediction text is published", predictions.get("eligible_count") == 0 and predictions.get("written_prediction_count") == 0 and predictions.get("items") == [], "Empty because no selection qualifies; no old text reused.")
    check("Match-winner leans are three Medium selections", len(audit.get("match_winner_picks", [])) == 3 and all(p.get("confidence") == "Medium" and p.get("probability") < 0.70 for p in audit["match_winner_picks"]), "No winner is labelled High below 70%.")
    check("Pipeline confidence labels are not adopted", all(e.get("winner_pick", {}).get("pipeline_tag_adopted") is False for e in priced_events), "User threshold controls the published grade.")

    # Historical boundary and coverage.
    check("Historical slice recomputes to 253 rows and 68 texts", history.get("fixture_rows") == 253 and history.get("prediction_texts") == 68, f"Found {history.get('fixture_rows')} rows / {history.get('prediction_texts')} texts.")
    check("Historical events stay outside current desk", not any(e.get("source_snapshot_utc") == "2026-10-22T21:15:00Z" for e in events), "No Board AG row is re-labelled as current.")
    check("Coverage page includes all 15 categories", coverage.get("scope_count") == 15 and len(coverage.get("categories", [])) == 15, "All requested categories have a row.")
    check("All categories publish five-pick shortfall", all(c.get("five_pick_shortfall") == 5 for c in coverage.get("categories", [])), "Shortfalls are visible; no quota is manufactured.")
    check("Flag register has source links for manual review", bool(flags) and all(f.get("official_url", "").startswith("https://") and f.get("olbg_url", "").startswith("https://") for f in flags), f"{len(flags)} flagged issues include official and OLBG review URLs.")
    check("NHL current-season records are not confused with 91-game form", all(e.get("home_record") not in {"32-59", "60-32"} and e.get("away_record") not in {"52-39", "57-34"} for e in provider if e["sport"] == "Ice Hockey"), "Published records are sourced from current-season standings fields.")

    # Generated website and local-link integrity.
    html_files = sorted(SITE.rglob("*.html"))
    sport_files = sorted((SITE / "sports").glob("*.html")) if (SITE / "sports").exists() else []
    check("All required dashboard pages exist", all((SITE / name).is_file() for name in ["index.html", "entries.html", "markets.html", "picks.html", "coverage.html", "sources.html", "methodology.html", "olbg.html", "flagged.html", "verification.html", "history.html"]), "Core static pages are present.")
    check("Exactly 15 sport subpages exist", len(sport_files) == 15, f"Found {len(sport_files)}.")
    broken = []
    for path in html_files:
        parser = LinkParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for href in parser.links:
            parsed = urlparse(href)
            if parsed.scheme in {"http", "https", "mailto", "data"} or href.startswith("#"):
                continue
            rel = href.split("#", 1)[0].split("?", 1)[0]
            if not rel:
                continue
            target = (path.parent / rel).resolve()
            if not target.exists():
                broken.append((str(path.relative_to(ROOT)), href))
    check("All local HTML links resolve", not broken, f"{len(broken)} broken local link(s)." + (f" First: {broken[:3]}" if broken else ""))
    table_missing = []
    entries_path = SITE / "entries.html"
    parser = TableRowLinkParser()
    parser.feed(entries_path.read_text(encoding="utf-8"))
    # The first entries table has a header row followed by one row per current entry.
    data_rows = [(ok, text) for ok, text in parser.rows_with_data if "Official start" not in text]
    for ok, text in data_rows:
        if not ok:
            table_missing.append(text[:100])
    check("Every entries-table data row links an official source", len(data_rows) >= 16 and not table_missing, f"Checked {len(data_rows)} rows; missing official link in {len(table_missing)}.")
    combined_html = "\n".join(p.read_text(encoding="utf-8") for p in html_files)
    stale_form_tokens = [x for x in ("32-59", "52-39", "60-32", "57-34", "210-131", "182-151") if x in combined_html]
    check("NHL stale 91/92-game form records are not published", not stale_form_tokens, f"Unexpected stale tokens: {stale_form_tokens}.")
    check("No draft placeholder remains in Board AH", all("TODO" not in p.read_text(encoding="utf-8") for p in html_files), "No draft marker in rendered pages.")
    check("Prediction copy does not contain banned words", all(not re.search(r"\b(model|verified)\b", item.get("text", ""), re.I) and len(re.findall(r"\b\w+\b", item.get("text", ""))) >= 30 for item in predictions.get("items", [])), "No high-confidence prose is present; any future item must satisfy lint.")
    check("Generated page links to no remote fonts or scripts", "fonts.googleapis.com" not in combined_html and "fonts.googleapis.com" not in (SITE / "assets/site.css").read_text(encoding="utf-8"), "Site uses local assets and system fonts.")
    return checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate the committed verification report without rewriting it")
    args = ap.parse_args()
    checks = run_checks()
    failed = [c for c in checks if c["status"] != "PASS"]
    status = "FAIL" if failed else "PASS"
    summary = f"{len(checks)} automated checks; {len(failed)} failure(s)."
    report = {
        "schema": "olbg4.board-ah.verification.v1",
        "board": "AH",
        "generated_utc": "2026-10-23T16:32:06Z",
        "status": status,
        "check_count": len(checks),
        "failure_count": len(failed),
        "summary": summary,
        "checks": checks,
    }
    if args.check:
        if not REPORT.is_file():
            print("FAIL: verification.json is missing", file=sys.stderr)
            return 1
        saved = read(REPORT)
        if saved != report:
            print("FAIL: committed verification.json is stale; run verify.py, then rebuild the site.", file=sys.stderr)
            return 1
        verify_page = (SITE / "verification.html").read_text(encoding="utf-8") if (SITE / "verification.html").exists() else ""
        if "Gate status: PASS" not in verify_page:
            print("FAIL: verification.html does not show PASS; rebuild the site.", file=sys.stderr)
            return 1
    else:
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print(f"{c['status']:4}  {c['name']}: {c['detail']}")
    print(summary)
    if failed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

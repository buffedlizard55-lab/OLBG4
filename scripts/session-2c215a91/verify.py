#!/usr/bin/env python3
"""Gate the isolated Board AK audit report and its static site."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2c215a91/audit.json"
SITE = ROOT / "session-2c215a91"
EXPECTED_SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts",
    "Baseball", "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing",
    "Handball", "Ice Hockey", "Basketball", "Rugby League",
]


def main() -> int:
    failures: list[str] = []
    if not DATA.exists():
        print("[AK] missing audit.json; run build.py first", file=sys.stderr)
        return 1
    audit = json.loads(DATA.read_text(encoding="utf-8"))
    metrics = audit["metrics"]

    def check(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    check(audit.get("schema") == "olbg4.session-audit/1", "unexpected audit schema")
    check(audit.get("scope") == EXPECTED_SPORTS, "scope is not the exact 15-sport brief")
    check([r["sport"] for r in audit.get("coverage", [])] == EXPECTED_SPORTS, "coverage does not contain exactly 15 sports")
    check(len(audit.get("findings", [])) >= 1, "Flagged for Review register is empty")
    check(all(f.get("status") == "needs review" and f.get("evidence") for f in audit["findings"]), "a finding lacks status or repository evidence")
    check(all(r.get("official_reference_url", "").startswith("https://") for r in audit["coverage"]), "a sport has no official manual-review reference")
    check(all(r.get("sport_page") and (ROOT / "session-2c215a91" / r["sport_page"].replace("../session-b2c7308d/", "../session-b2c7308d/")).exists() for r in audit["coverage"]), "a category link is missing")

    integrity = audit["capture_integrity"]
    latest_capture = audit["primary_desk"]["latest_capture_available"]
    check(bool(latest_capture.get("recorded_utc") and latest_capture.get("finished_utc")), "latest capture timestamp fields are incomplete")
    check(audit["primary_desk"]["latest_capture_included_in_desk"] and latest_capture.get("stamp") == audit["primary_desk"].get("primary_capture"), "primary desk no longer includes its latest available capture; revisit the freshness finding")
    check(integrity["files_checked"] == integrity["files_sha256_matched"], "one or more capture payload hashes do not match")
    check(not integrity["hash_errors"], "capture hash errors were recorded")
    check(metrics["source_urls_matching_row_capture_manifest"] == metrics["rows"], "a desk row source URL is not in its capture manifest")
    check(not metrics["source_url_mismatches"], "source URL mismatch list is not empty")
    check(metrics["market_math"]["arithmetic_errors"] == 0, "market probability/decimal/American math failed")
    check(metrics["market_math"]["selection_outcomes_checked"] == 954, "unexpected number of market outcomes checked")
    check(not metrics["pick_price_arithmetic_errors"], "featured-pick prices do not reconcile")
    check(not metrics["high_out_of_window_ids"], "a High pick lies outside the declared fair-price window")
    check(not metrics["high_below_70_percent_ids"], "a High pick is below 70%")
    check(metrics["high_rows_with_prediction"] == metrics["high_rows"], "a High row lacks a prediction text")
    check(not metrics["prediction_rows_under_30_words"], "a prediction is under 30 words")
    check(not metrics["prediction_banned_word_rows"], "a prediction contains restricted internal vocabulary")
    check(not metrics["prediction_selection_text_mismatches"], "a prediction does not state its stored selection")
    check(metrics["max_prediction_3gram_jaccard"] < 0.30, "prediction texts are too similar")
    check(metrics["rows"] == 276 and metrics["priced_rows"] == 159, "unexpected latest-desk row/priced counts")
    check(metrics["listing_only_rows"] == 101 and metrics["olbg_host_rows"] == 56, "listing-only source inventory changed")
    check(metrics["priced_rows_with_moneyline_or_match_winner_pick"] == 72, "standalone winner-pick count changed")
    check(metrics["priced_rows_whose_featured_pick_is_not_match_winner"] == 87, "non-winner featured pick count changed")
    check(metrics["high_rows"] == 10 and metrics["high_rows_by_sport"] == {"Baseball": 3, "Basketball": 2, "Ice Hockey": 5}, "High-pick coverage changed")
    check(metrics["rows_with_blank_start_utc"] == 128 and metrics["rows_with_start_at_or_before_audit_cutoff"] == 4, "date/time quality counts changed")
    check(metrics["book_fields_equal_fair_fields"] == 954 and metrics["book_fields_not_equal_fair_fields"] == 0, "book/fair field audit changed")
    master_audit = audit["repo_audit"]["master"]
    check(master_audit["rows_now"] == 354 and master_audit["review_denominator_delta"] == 18, "master review denominator mismatch changed")
    check(master_audit["scope_flag_mismatch_count"] == 14 and master_audit["missing_source_in_scope_rows"] == 31 and master_audit["missing_source_out_of_scope_rows"] == 8, "master scope-field audit changed")
    check(audit["repo_audit"]["matches_review_counts_rederived_match"], "legacy matches.json review counts do not match a fresh local recomputation")
    later_desk = audit["later_desk_not_audited"]
    check(later_desk["session"] == "arena/63ad3394-olbg4" and later_desk["audit_status"] == "not audited by this static Board AH/AI report", "the newer peer desk is not clearly labeled as outside this audit")
    check(not audit["repo_audit"]["root_index_links_later_board_ak"] and audit["repo_audit"]["root_readme_links_later_board_ak"], "root navigation/README status for the later desk changed")

    html_pages = sorted(SITE.rglob("*.html"))
    check(len(html_pages) == 5, f"expected 5 local pages, found {len(html_pages)}")
    page_text = {path: path.read_text(encoding="utf-8") for path in html_pages}
    for page, text in page_text.items():
        if "TODO" in text:
            failures.append(f"{page.relative_to(ROOT)} contains TODO")
        for href in re.findall(r'href=[\"\']([^\"\']+)[\"\']', text):
            href = html_unescape(href)
            parts = urlsplit(href)
            if parts.scheme in ("http", "https", "mailto", "tel") or href.startswith("//"):
                continue
            target_path = unquote(parts.path)
            if not target_path:
                target = page
            else:
                target = (page.parent / target_path).resolve()
            if not target.exists():
                failures.append(f"{page.relative_to(ROOT)}: broken link {href}")
                continue
            if parts.fragment and target.suffix in (".html", ""):
                target_text = target.read_text(encoding="utf-8", errors="replace")
                if not re.search(r'\b(?:id|name)=[\"\']' + re.escape(unquote(parts.fragment)) + r'[\"\']', target_text):
                    failures.append(f"{page.relative_to(ROOT)}: missing anchor #{parts.fragment} in {target.relative_to(ROOT)}")
    check(sum(1 for r in audit["coverage"] if r["official_reference_url"].startswith("https://")) == 15, "sport coverage table lacks 15 HTTPS source references")

    # The committed audit and HTML are deterministic given the immutable source captures.
    before = {path: path.read_bytes() for path in [DATA, *html_pages, SITE / "assets/style.css"]}
    build_script = ROOT / "scripts/session-2c215a91/build.py"
    result = subprocess.run([sys.executable, str(build_script)], cwd=ROOT, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode:
        failures.append("deterministic rebuild failed: " + result.stderr[-1000:])
    else:
        for path, old in before.items():
            if path.read_bytes() != old:
                failures.append(f"non-deterministic rebuild changed {path.relative_to(ROOT)}")

    print(f"[AK] verify: pages={len(html_pages)} rows={metrics['rows']} priced={metrics['priced_rows']} "
          f"prices={metrics['market_math']['selection_outcomes_checked']} predictions={metrics['predictions']} "
          f"capture_hashes={integrity['files_sha256_matched']}/{integrity['files_checked']} failures={len(failures)}")
    for failure in failures[:60]:
        print("  FAIL", failure)
    return 1 if failures else 0


def html_unescape(text: str) -> str:
    import html
    return html.unescape(text)


if __name__ == "__main__":
    raise SystemExit(main())

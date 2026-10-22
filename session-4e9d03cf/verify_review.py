#!/usr/bin/env python3
"""Deterministic gate for session S1's freshness-review output."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SESSION = ROOT / "session-4e9d03cf"
REPORT = ROOT / "data/session-4e9d03cf/review.json"
REVIEW_DATE = "2026-10-22"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"a", "link", "script"}:
            attributes = dict(attrs)
            url = attributes.get("href") or attributes.get("src")
            if url:
                self.links.append(url)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def american_in_focus(value) -> bool:
    try:
        price = int(str(value).strip())
    except (TypeError, ValueError):
        return False
    return -250 <= price <= 10000


def check_link(origin: Path, href: str, failures: list[str]) -> None:
    if href.startswith(("http://", "https://", "mailto:", "data:", "#")):
        return
    target = href.split("#", 1)[0]
    if not target:
        return
    path = (origin.parent / target).resolve()
    if not path.exists():
        failures.append(f"broken local link in {origin.relative_to(ROOT)}: {href}")


def main() -> int:
    failures: list[str] = []

    # Regenerate twice: outputs must be byte-for-byte stable for unchanged inputs.
    command = [sys.executable, str(SESSION / "build_review.py")]
    subprocess.run(command, check=True, cwd=ROOT)
    first = {p: digest(p) for p in [REPORT, SESSION / "index.html", SESSION / "flagged.html"]}
    subprocess.run(command, check=True, cwd=ROOT)
    second = {p: digest(p) for p in first}
    if first != second:
        failures.append("review outputs are not deterministic across two rebuilds")

    master = load(ROOT / "data/master.json")
    review = load(REPORT)
    snapshot = load(ROOT / "session-4afef1af/data/snapshot.json")
    predictions = load(ROOT / "session-4afef1af/data/predictions.json")
    master_rows = {row["id"]: row for row in master["rows"]}
    review_rows = review["rows"]

    if review["review_date"] != REVIEW_DATE:
        failures.append(f"review date is {review['review_date']!r}, expected {REVIEW_DATE!r}")
    if len(review_rows) != len(master_rows):
        failures.append(f"row count differs: review={len(review_rows)}, master={len(master_rows)}")
    if len({row["id"] for row in review_rows}) != len(review_rows):
        failures.append("review has duplicate IDs")
    if set(row["id"] for row in review_rows) != set(master_rows):
        failures.append("review IDs do not exactly cover canonical master IDs")
    if review["master_generated_on"] != master["generated_on"]:
        failures.append("master generated-on value was not preserved")
    if review["pipeline_generated_utc"] != snapshot["generated_utc"]:
        failures.append("pipeline generated timestamp was not preserved")

    strict = []
    current = []
    for reviewed in review_rows:
        source = master_rows[reviewed["id"]]
        official = source.get("source_tier") == "official" and bool(source.get("source_url"))
        expected_url = source.get("source_url", "") if official else ""
        if reviewed["official_source_url"] != expected_url:
            failures.append(f"{reviewed['id']}: displayed official URL does not match canonical tier/url")
        if reviewed["review_status"] == "carried-current":
            strict.append(reviewed)
            if not (reviewed["in_scope"] and reviewed["row_type"] == "fixture" and
                    reviewed["date"] >= REVIEW_DATE and reviewed["official_source_url"] and
                    reviewed["original_build_verified"]):
                failures.append(f"{reviewed['id']}: strict carried row violates source/current gate")
            if reviewed["confidence"] == "High" and reviewed["prediction_style"] != "written":
                failures.append(f"{reviewed['id']}: templated high copy was promoted")
        if reviewed["in_scope"] and reviewed["row_type"] == "fixture" and reviewed["date"] >= REVIEW_DATE:
            current.append(reviewed)

    # No high-confidence templated text can be presented as a compliant carried row.
    templated_high = [
        row for row in review_rows
        if row["confidence"] == "High" and row["prediction_style"] != "written"
    ]
    if len(templated_high) != 3:
        failures.append(f"expected 3 canonical templated high rows, found {len(templated_high)}")
    promoted = [row["id"] for row in templated_high if row["review_status"] == "carried-current"]
    if promoted:
        failures.append(f"templated high rows promoted: {promoted}")

    # S1's high-focus statement must come directly from the committed pipeline data.
    focused = [
        pred for pred in predictions
        if str(pred.get("start_utc", ""))[:10] >= REVIEW_DATE and
        float(pred.get("prob_pct") or 0) >= 70 and american_in_focus(pred.get("american"))
    ]
    focus_finding = next((f for f in review["findings"] if f["id"] == "S1-F05"), None)
    if not focus_finding:
        failures.append("missing S1-F05 focus finding")
    elif f"{len(focused)} have both" not in focus_finding["detail"]:
        failures.append("S1-F05 focus finding does not reflect committed pipeline values")

    expected_summary = {
        "total_rows": len(review_rows),
        "current_fixture_rows": len(current),
        "carried_current": len(strict),
        "held_current": sum(row["review_status"] in {"held-source", "held-verification", "held-copy"} for row in current),
        "high_written": sum(row["confidence"] == "High" and row["prediction_style"] == "written" for row in review_rows),
        "high_templated": len(templated_high),
    }
    for key, value in expected_summary.items():
        if review["summary"].get(key) != value:
            failures.append(f"summary {key}={review['summary'].get(key)!r}, expected {value!r}")

    # Static output may link elsewhere in the repo, but no relative target can be broken.
    for page in [SESSION / "index.html", SESSION / "flagged.html"]:
        text = page.read_text(encoding="utf-8")
        for bad in ("TODO", "Lorem ipsum", "undefined</", "NaN"):
            if bad in text:
                failures.append(f"{page.name} contains placeholder {bad!r}")
        parser = Links()
        parser.feed(text)
        for href in parser.links:
            check_link(page, href, failures)
    for asset in [SESSION / "assets/review.css", SESSION / "assets/review.js"]:
        if not asset.exists() or not asset.read_text(encoding="utf-8").strip():
            failures.append(f"missing or empty asset: {asset.relative_to(ROOT)}")

    print(
        f"S1 review: rows={len(review_rows)} current={len(current)} strict={len(strict)} "
        f"held={expected_summary['held_current']} high-written={expected_summary['high_written']} "
        f"focus={len(focused)}"
    )
    if failures:
        print(f"FAILED ({len(failures)} issue(s))")
        for failure in failures:
            print(" -", failure)
        return 1
    print("OK — S1 review is deterministic, source-conservative, and locally linked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

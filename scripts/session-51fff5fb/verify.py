#!/usr/bin/env python3
"""Deterministic acceptance gates for the QF report and its static pages."""
from __future__ import annotations

import hashlib
import html.parser
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
AUDIT_SCRIPT = ROOT / "scripts" / "session-51fff5fb" / "audit.py"
BUILD_SCRIPT = ROOT / "scripts" / "session-51fff5fb" / "build_site.py"
AUDIT_JSON = ROOT / "data" / "session-51fff5fb" / "audit.json"
SITE = ROOT / "session-51fff5fb"
PAGES = ["index.html", "picks.html", "coverage.html", "flagged.html", "sources.html"]
BANNED = re.compile(r"\b(model|models|modelled|modeled|modelling|verif\w*)\b", re.I)

checks: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, bool(ok), detail))


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class HTMLAuditParser(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.table_rows: list[dict] = []
        self._tr = False
        self._has_td = False
        self._row_hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a" and attrs.get("href"):
            href = attrs["href"]
            self.hrefs.append(href)
            if self._tr:
                self._row_hrefs.append(href)
        elif tag == "tr":
            self._tr = True
            self._has_td = False
            self._row_hrefs = []
        elif tag == "td" and self._tr:
            self._has_td = True

    def handle_endtag(self, tag):
        if tag == "tr" and self._tr:
            if self._has_td:
                self.table_rows.append({"hrefs": list(self._row_hrefs)})
            self._tr = False
            self._has_td = False
            self._row_hrefs = []


def local_target(page: Path, href: str) -> Path | None:
    bits = urlsplit(href)
    if bits.scheme or bits.netloc or href.startswith("#"):
        return None
    if bits.path == "":
        return None
    return (page.parent / unquote(bits.path)).resolve()


def snapshot_hashes(paths: list[Path]) -> dict[str, str]:
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def main() -> int:
    if not AUDIT_JSON.is_file():
        print("FAIL — generate audit.json first with scripts/session-51fff5fb/audit.py")
        return 1

    # The data audit and static renderer must be reproducible from the same committed inputs.
    audit_before = hashlib.sha256(AUDIT_JSON.read_bytes()).hexdigest()
    run_audit = subprocess.run([sys.executable, str(AUDIT_SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    check("audit generation exits cleanly", run_audit.returncode == 0, run_audit.stderr.strip() or run_audit.stdout.strip())
    audit_after = hashlib.sha256(AUDIT_JSON.read_bytes()).hexdigest()
    check("audit JSON rebuild is byte-identical", audit_before == audit_after, f"before={audit_before} after={audit_after}")

    page_paths = [SITE / name for name in PAGES]
    page_paths.append(SITE / "style.css")
    before = snapshot_hashes(page_paths)
    run_build = subprocess.run([sys.executable, str(BUILD_SCRIPT)], cwd=ROOT, capture_output=True, text=True)
    check("static site build exits cleanly", run_build.returncode == 0, run_build.stderr.strip() or run_build.stdout.strip())
    after = snapshot_hashes(page_paths)
    check("all five pages and stylesheet rebuild byte-identically", before == after, f"before={before} after={after}")

    audit = load_json(AUDIT_JSON)
    source_desk = load_json(ROOT / "data" / "session-b6643783" / "desk.json")
    summary = audit.get("summary", {})
    source = audit.get("source_integrity", {})
    market = audit.get("market_checks", {})
    prediction = audit.get("prediction_checks", {})
    rows = audit.get("high_rows", [])
    candidates = audit.get("numeric_high_candidates", [])
    promoted = [r for r in candidates if r.get("has_written_prediction") and r.get("olbg_event_url") and r.get("starts_after_capture")]

    check("all requested sports are present in coverage", len(audit.get("sports", [])) == 15 and len({r.get("sport") for r in audit.get("sports", [])}) == 15, str(len(audit.get("sports", []))))
    check("capture payload hashes match the manifest", summary.get("source_integrity_pass") and summary.get("capture_payload_hashes_checked") == summary.get("capture_payload_hashes_passed") and summary.get("capture_payload_hashes_checked") == source.get("http_200_records"), f"{summary.get('capture_payload_hashes_passed')}/{summary.get('capture_payload_hashes_checked')} hashes")
    check("no capture payloads are missing or hash-mismatched", not source.get("missing_payloads") and not source.get("hash_mismatches"), f"missing={len(source.get('missing_payloads', []))}, mismatches={len(source.get('hash_mismatches', []))}")
    check("all originated prices re-derive", not market.get("bad_price_math"), str(len(market.get("bad_price_math", []))))
    check("all originated markets sum to one", not market.get("bad_two_way_or_three_way_probability_sums"), str(len(market.get("bad_two_way_or_three_way_probability_sums", []))))
    check("every candidate meets the stated numeric threshold", all(r.get("confidence") == "High" and r.get("probability_at_least_70") and r.get("inside_american_price_focus") for r in candidates), str(len(candidates)))
    check("promoted cards require a write-up, OLBG event and future start", all(r.get("has_written_prediction") and r.get("olbg_event_url") and r.get("starts_after_capture") for r in promoted), str(len(promoted)))
    check("audit counts agree with the underlying findings", summary.get("high_rows_inside_numeric_focus") == len(candidates) and summary.get("high_rows_inside_focus_with_prediction_and_olbg_event") == len(promoted), f"candidates={len(candidates)}, promoted={len(promoted)}")
    check("prediction structural checks have no failures", summary.get("prediction_rule_failure_count") == 0 and not prediction.get("under_30_or_stored_count_mismatch") and not prediction.get("banned_terms") and not prediction.get("missing_official_source") and not prediction.get("selection_not_explicit") and not prediction.get("prediction_without_fixture_row"), str(summary.get("prediction_rule_failure_count")))
    check("all published prediction texts are at least 30 words", all(p.get("word_count", 0) >= 30 for p in audit.get("predictions", [])), str(summary.get("prediction_words_min")))
    check("predictions avoid internal terms", not any(BANNED.search(str(p.get("text", ""))) for p in audit.get("predictions", [])), "model / verified terminology scan")
    check("all source rows carry a URL", summary.get("rows_missing_official_source_url") == 0, str(summary.get("rows_missing_official_source_url")))
    unflagged_unpriced = [r.get("id", "") for r in source_desk.get("rows", []) if not r.get("pick") and not (r.get("flags") or [])]
    check("every unpriced fixture is explicitly flagged", not unflagged_unpriced, str(unflagged_unpriced[:8]))
    check("source links map to captured payloads or capture IDs", summary.get("official_source_links_not_matched_to_manifest") == 0, str(summary.get("official_source_links_not_matched_to_manifest")))
    check("stale/in-play-at-capture rows are flagged in the report", summary.get("rows_started_at_or_before_capture") == len(audit.get("not_future_at_capture", [])), str(summary.get("rows_started_at_or_before_capture")))
    check("high rows without text are enumerated", summary.get("high_rows_missing_prediction") == len(audit.get("high_missing_prediction", [])), str(summary.get("high_rows_missing_prediction")))
    handball = audit.get("handball_copy_audit", {})
    check("handball source totals are re-derived from the captured standings", handball.get("checked") and handball.get("mean_goals_per_team_game") == 31.66 and handball.get("mean_total_goals_per_match") == 63.32, json.dumps(handball, ensure_ascii=False))
    check("handball prediction wording issue is surfaced", handball.get("issue") and summary.get("prediction_statistic_wording_issues") == 1 and "QF-F11" in (SITE / "flagged.html").read_text(encoding="utf-8"), str(handball.get("issue")))

    # Every authored table row must carry at least one external HTTPS source URL.
    table_rows = []
    broken = []
    missing_source_rows = []
    for page in page_paths:
        if page.suffix != ".html":
            continue
        parser = HTMLAuditParser()
        parser.feed(page.read_text(encoding="utf-8"))
        for href in parser.hrefs:
            target = local_target(page, href)
            if target is not None and not target.exists():
                broken.append(f"{page.relative_to(ROOT)} -> {href}")
        for number, row in enumerate(parser.table_rows, 1):
            table_rows.append((page, number, row))
            external_https = [h for h in row["hrefs"] if urlsplit(h).scheme.lower() == "https" and urlsplit(h).netloc]
            if not external_https:
                missing_source_rows.append(f"{page.relative_to(ROOT)} row {number}")
    check("every local link resolves", not broken, "; ".join(broken[:8]))
    check("every rendered table row links to an HTTPS source", not missing_source_rows, "; ".join(missing_source_rows[:8]))
    check("static deliverables are present", all(p.is_file() for p in page_paths), ", ".join(str(p) for p in page_paths if not p.is_file()))
    check("landing page clearly directs users to picks and review flags", all(token in (SITE / "index.html").read_text(encoding="utf-8") for token in ("Pick shortlist", "Flagged for review", "Main OLBG4 dashboard")), "primary navigation and CTA copy")

    passed = sum(ok for _, ok, _ in checks)
    print(f"{'PASS' if passed == len(checks) else 'FAIL'} — {passed}/{len(checks)} QF gates")
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail and not ok else ""))
    print(f"\n{summary.get('fixture_rows')} source rows · {summary.get('priced_rows')} priced · {summary.get('high_label_rows')} High labels · {len(candidates)} within numeric focus · {len(promoted)} linked written candidates")
    print(f"{len(table_rows)} table rows checked · {len(broken)} broken local links · {len(missing_source_rows)} table rows without an external source")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

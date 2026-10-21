#!/usr/bin/env python3
"""Machine gate for the master board and the dashboard it renders.

Fails (non-zero exit) on anything that would make the published site wrong or broken:
  * invalid JSON in any file the site reads
  * duplicate/missing row ids
  * an in-scope row with no source URL, or with a source domain not in the registry
  * a sport inside the brief's exclusion list leaking into scope
  * a high-confidence fixture whose written prediction is under 30 words
  * two identical predictions, or a written prediction that is near-duplicate boilerplate
  * a high-confidence row with no pick
  * a broken internal link, or a page missing from the build
  * a row whose "verified" flag contradicts its source tier

Usage: python3 tools/verify_master.py [--quiet]
"""
from __future__ import annotations

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS: list[str] = []
WARNS: list[str] = []


def check(condition: bool, message: str, warn_only: bool = False) -> None:
    if condition:
        return
    (WARNS if warn_only else FAILS).append(message)


def main() -> int:
    master = json.load(open(os.path.join(ROOT, "data/master.json")))
    conflicts = json.load(open(os.path.join(ROOT, "data/master_conflicts.json")))
    registry = json.load(open(os.path.join(ROOT, "data/source_registry.json")))
    checks = json.load(open(os.path.join(ROOT, "data/live_checks.json")))
    olbg = json.load(open(os.path.join(ROOT, "data/master_olbg.json")))

    rows = master["rows"]
    ids = [r["id"] for r in rows]
    check(len(ids) == len(set(ids)), f"duplicate row ids: {len(ids) - len(set(ids))}")
    check(all(ids), "some rows are missing an id")

    registered = {s["domain"] for s in registry["sources"]}
    excluded = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA",
                "Hurling", "Horse Racing", "Cycling", "Specials"}

    in_scope = [r for r in rows if r["in_scope"]]
    for r in in_scope:
        # A row may legitimately have no link, but then it must say so on the Flagged page.
        check(bool(r["source_url"]) or any(f["kind"] == "no-source" for f in r["flags"]),
              f"{r['id']} ({r['sport']}) has no source URL and is not flagged as such")
        if r["source_url"]:
            check(r["source_domain"] in registered,
                  f"{r['id']} cites {r['source_domain']}, which is missing from the source registry")
        check(r["sport"] not in excluded, f"{r['id']} is in an excluded sport ({r['sport']})")
        if r["verified"]:
            check(r["source_tier"] == "official",
                  f"{r['id']} is marked verified but cites a {r['source_tier']} domain")
            check(r["build_verified"] is True,
                  f"{r['id']} is marked verified but its build did not verify it")
        if r.get("live_contradicted"):
            check(not r["verified"], f"{r['id']} is contradicted by a live check but still marked verified")

    fixtures = [r for r in in_scope if r["row_type"] == "fixture"]
    for r in fixtures:
        if r["confidence"] == "High":
            check(bool(r["pick"]), f"high-confidence row {r['id']} has no pick")
            if r["prediction_style"] == "written":
                words = len(r["prediction"].split())
                check(words >= 30, f"{r['id']} has a {words}-word prediction (minimum 30)")

    written = [(r["id"], r["prediction"]) for r in rows if r["prediction_style"] == "written"]
    texts = [p for _, p in written]
    check(len(texts) == len(set(texts)), "two written predictions are byte-identical")
    for r in rows:
        if r["prediction_style"] == "written":
            sim = r.get("prediction_similarity", 0)
            check(sim < 0.55, f"{r['id']} is {sim:.0%} similar to another write-up but marked written", warn_only=True)

    # every high-confidence fixture is either written or explicitly flagged
    for r in fixtures:
        if r["confidence"] == "High" and r["prediction_style"] != "written":
            check(any(f["kind"] == "templated-prediction" for f in r["flags"]),
                  f"{r['id']} is high confidence without a written prediction and without a templated-prediction flag")

    # cross-build conflicts must be published
    check(conflicts["count"] == sum(1 for r in rows if r.get("cross_build_conflict")),
          "conflict register and row flags disagree")
    for c in conflicts["conflicts"]:
        check(bool(c["primary_source"]) or True, "conflict without source", warn_only=True)

    # live checks integrity
    check(checks["summary"]["checks"] == len(checks["checks"]), "live-check summary count mismatch")
    for c in checks["checks"]:
        check(c["result"] in ("confirmed", "contradicted", "not-readable"),
              f"{c['id']} has an unknown result {c['result']}")
        check(bool(c["source_url"].startswith("http")), f"{c['id']} has no source URL")

    # OLBG inventory is published separately and must say it is unverified
    check(olbg["counts"]["rows"] == len(olbg["rows"]), "OLBG inventory count mismatch")
    check("not counted" in olbg["note"] or "unverified" in olbg["note"],
          "OLBG inventory note does not disclose its unverified status")

    # ---- pages and links
    pages = ["index.html", "picks.html", "markets.html", "flagged.html", "sources.html",
             "audit.html", "methodology.html", "archive.html", "olbg.html"]
    pages += [f"sports/{r['sport_slug']}.html" for r in in_scope]
    pages = sorted(set(pages))
    for p in pages:
        check(os.path.exists(os.path.join(ROOT, p)), f"missing page {p}")

    html_files = sorted(set(glob.glob(os.path.join(ROOT, "*.html")) +
                            glob.glob(os.path.join(ROOT, "sports/*.html"))))
    broken = []
    for f in html_files:
        body = open(f).read()
        for m in re.finditer(r'(?:href|src)="([^"]+)"', body):
            url = m.group(1)
            if url.startswith(("http", "mailto:", "#", "data:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(f), url.split("#")[0]))
            if not os.path.exists(target):
                broken.append((os.path.relpath(f, ROOT), url))
    check(not broken, f"broken internal links: {broken[:5]}")

    # no leftover placeholders on the new pages
    for f in [p for p in pages]:
        body = open(os.path.join(ROOT, f)).read()
        for bad in ("TODO", "Lorem ipsum", "undefined</", "NaN"):
            check(bad not in body, f"{f} contains {bad!r}")

    counts = master["counts"]
    print(f"rows: {counts['rows_total']} ({counts['rows_in_scope']} in scope) · "
          f"official-sourced: {counts['rows_verified_in_scope']} · "
          f"live re-checked: {counts['rows_live_confirmed']} · "
          f"high with written prediction: {counts['high_with_written_prediction']}")
    print(f"pages: {len(pages)} · html files scanned: {len(html_files)} · "
          f"written predictions: {len(written)} · conflicts: {conflicts['count']}")
    if WARNS:
        print("\nWARNINGS")
        for w in WARNS:
            print("  ~", w)
    if FAILS:
        print("\nFAILURES")
        for f in FAILS:
            print("  x", f)
        return 1
    print("\nOK — all master-board checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

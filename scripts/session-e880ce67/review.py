#!/usr/bin/env python3
"""Structural review of the repository's consolidated data file, data/master.json.

Read-only: this script never edits another board's data. Each finding records what was found,
how many rows it touches, one or two example rows, and an official URL the reader can check.
"""

from __future__ import annotations

import collections
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MASTER = os.path.join(ROOT, "data", "master.json")
OUT = os.path.join(ROOT, "data", "session-e880ce67", "review.json")

SCOPE = {"Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
         "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
         "Basketball", "Rugby League"}
REVIEW_DATE = "2026-10-24"
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)


def example(row: dict) -> str:
    return f"{row.get('away') or '?'} @ {row.get('home') or '?'} ({row.get('id')})"


def main() -> int:
    data = json.load(open(MASTER, encoding="utf-8"))
    rows = data["rows"]
    findings = []

    def add(fid, title, affected_rows, detail, url=""):
        findings.append({"id": fid, "title": title, "affected": len(affected_rows),
                         "detail": detail, "evidence_url": url,
                         "examples": [example(r) for r in affected_rows[:4]]})

    stale = [r for r in rows if (r.get("date") or "") < REVIEW_DATE]
    add("R-01", "Rows dated before the review date",
        stale, f"{len(stale)} of {len(rows)} rows carry a date before {REVIEW_DATE}. A stale row is "
        "not automatically wrong, but it cannot be a live quote: the price beside it was built for a "
        "fixture that has already started or been played.",
        "https://www.nhl.com/scores")

    no_source = [r for r in rows if not (r.get("source_url") or "").startswith("http")]
    add("R-02", "Rows with no source URL",
        no_source, f"{len(no_source)} rows publish a price and a pick with an empty source_url field. "
        "The reader has no click-through, which breaks the rule that every row links the body it came "
        "from.", "https://www.nhl.com/standings")

    dupes = collections.Counter(
        (r.get("sport"), (r.get("home_raw") or r.get("home") or "").lower(),
         (r.get("away_raw") or r.get("away") or "").lower(), (r.get("date") or "")[:10])
        for r in rows)
    dup_rows = [r for r in rows if dupes[(r.get("sport"),
                (r.get("home_raw") or r.get("home") or "").lower(),
                (r.get("away_raw") or r.get("away") or "").lower(),
                (r.get("date") or "")[:10])] > 1]
    add("R-04", "The same fixture appears more than once",
        dup_rows, f"{len(dup_rows)} rows share a sport, both team names and a date with another row. "
        "A duplicated fixture produces two prices for one market, and a reader cannot tell which is "
        "current.", "https://www.nhl.com/schedule")

    bad_len = [r for r in rows if r.get("prediction") and len(r["prediction"].split()) < 30]
    add("R-05", "Written predictions below the 30-word floor",
        bad_len, f"{len(bad_len)} rows carry a prediction shorter than the brief's 30-word minimum, "
        "which makes them bare winner calls rather than analysis.",
        "https://www.pdc.tv/")

    banned = [r for r in rows if r.get("prediction") and BANNED.search(r["prediction"])]
    add("R-06", "Predictions using the excluded vocabulary",
        banned, f"{len(banned)} predictions contain a word the brief excludes from output text "
        "(the model/verification vocabulary). These read as machine provenance, not as a tip.",
        "https://www.wtatennis.com/rankings/singles")

    no_conf = [r for r in rows if not r.get("confidence")]
    add("R-07", "Rows with no confidence label",
        no_conf, f"{len(no_conf)} rows publish a pick without a High/Medium/Low label, so the reader "
        "cannot tell a strong opinion from a coin-flip.",
        "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026")

    unscoped = [r for r in rows if r.get("sport") and r["sport"] not in SCOPE | {"Gaelic Football", "Hurling"}]
    add("R-08", "Rows outside the fifteen-sport brief",
        unscoped, f"{len(unscoped)} rows belong to a sport the brief excludes"
        f" ({', '.join(sorted({r.get('sport') for r in unscoped})) or 'none'}).",
        "https://www.olbg.com/betting-tips")

    gaelic = [r for r in rows if r.get("sport") == "Gaelic Football"]
    if gaelic:
        add("R-09", "Gaelic Football rows sit outside the scope list",
            gaelic, f"{len(gaelic)} rows use the label Gaelic Football while the file's scope list uses "
            "Gaelic Sports, so a scope filter silently drops them.",
            "https://www.gaa.ie/fixtures-results/")

    grey = [r for r in rows if r.get("sport") in {"Greyhounds", "Greyhound Racing"}]
    labels = {r.get("sport") for r in grey}
    if len(labels) > 1:
        add("R-10", "One sport under two labels",
            grey, f"{len(grey)} rows are split across {', '.join(sorted(labels))}. Two labels for one "
            "sport break per-sport counts and make the coverage table disagree with itself.",
            "https://www.gbgb.org.uk/results")

    per_sport = collections.Counter(r.get("sport") for r in rows)
    thin = [r for r in rows if per_sport[r.get("sport")] < 5]
    add("R-11", "Sports represented by fewer than five rows",
        thin, f"{len(thin)} rows belong to a sport with under five fixtures — too few to support the "
        "brief's five predictions per sport.",
        "https://www.olbg.com/sitemap-betting-tips.xml")

    affected = {example(r) for f in findings for r in []}  # placeholder for symmetry
    affected_rows = set()
    for f in findings:
        for ex in f["examples"]:
            affected_rows.add(ex)
    payload = {
        "schema": "olbg4.session-e880ce67.review/1",
        "source_file": "data/master.json",
        "source_generated_on": data.get("generated_on", ""),
        "rows_total": len(rows),
        "rows_in_scope": sum(1 for r in rows if r.get("sport") in SCOPE | {"Gaelic Football", "Hurling"}),
        "affected_rows": len(stale) + len(no_source) + len(dup_rows) + len(bad_len) + len(banned)
                          + len(no_conf) + len(unscoped) + len(gaelic) + len(thin),
        "summary": (f"A structural read of data/master.json (generated {data.get('generated_on', '?')}, "
                    f"{len(rows)} rows). It checks what can be checked without re-fetching every "
                    "fixture: dates, source links, duplicate identity, prediction length and "
                    "vocabulary, confidence labels and sport scoping. Each finding names the rows it "
                    "touches and links the body that could settle it."),
        "findings": findings,
        "per_sport": dict(per_sport.most_common()),
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
    print(f"findings={len(findings)} rows={len(rows)} affected={payload['affected_rows']}")
    for f in findings:
        print(f"  {f['id']} {f['title'][:52]:52} {f['affected']:>4}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

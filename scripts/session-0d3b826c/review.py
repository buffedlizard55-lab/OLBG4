#!/usr/bin/env python3
"""Line-by-line, read-only audit of the shared master and freshest peer desks.

This is deliberately scoped: structural/math checks are reproduced for every
row, but they are not misrepresented as a fresh official re-read of every peer
claim. Direct source comparisons belong to Board AF's own evidence desk.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from common import DATA, ROOT, dump, load, words

CUTOFF_DATE = "2026-10-22"


def review() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    counts: dict[str, Counter] = {}

    def add(dataset: str, row_id: str, code: str, detail: str, url: str = "") -> None:
        findings.append({"dataset": dataset, "row_id": row_id, "code": code,
                         "detail": detail, "manual_review_url": url, "status": "needs review"})
        counts.setdefault(dataset, Counter())[code] += 1

    master_path = ROOT / "data" / "master.json"
    master = load(master_path)
    dataset = "data/master.json"
    for index, row in enumerate(master["rows"], 1):
        row_id = row.get("id") or f"master-row-{index}"
        url = row.get("source_url") or ""
        date = (row.get("date") or "")[:10]
        if row.get("in_scope") and date and date < CUTOFF_DATE:
            add(dataset, row_id, "STALE_FOR_CURRENT_UPCOMING_BOARD",
                f"Stored date {date} precedes the 22 Oct current-board cutoff; this historical master row is not a current upcoming fixture.", url)
        if not url:
            add(dataset, row_id, "SOURCE_URL_MISSING",
                "No source URL is stored; independent manual review has no row-level source link.")
        if not row.get("verified"):
            populated = [field for field in ("pick", "win", "handicap", "total", "prediction") if row.get(field) not in (None, "", [], {})]
            if populated:
                add(dataset, row_id, "UNVERIFIED_VALUES_POPULATED",
                    "The row is not verified but still publishes: " + ", ".join(populated) + ". The brief requires blank unconfirmed values.", url)
        if row.get("confidence") == "High" and row.get("prediction_style") == "templated":
            add(dataset, row_id, "TEMPLATED_HIGH_PREDICTION",
                "A High row is tagged as templated rather than unique human analysis.", url)
        if row.get("in_scope") and row.get("source_tier") not in ("official", "official-live", "official_live") and url:
            add(dataset, row_id, "SOURCE_TIER_NOT_OFFICIAL",
                f"Stored source tier is {row.get('source_tier')!r}; do not present it as official verification.", url)

    for session, cutoff_key in (("22ca2e95", "cutoff_utc"), ("f0622b6e", "cutoff_utc")):
        path = DATA.parent / f"session-{session}" / "desk.json"
        if not path.exists():
            continue
        desk = load(path)
        dataset = f"data/session-{session}/desk.json"
        manifest_path = DATA.parent / f"session-{session}" / "capture" / desk.get("capture_id", "") / "manifest.json"
        captured_urls = set()
        if manifest_path.exists():
            manifest = load(manifest_path)
            captured_urls = {item["url"] for item in manifest.get("items", [])}
        for index, row in enumerate(desk["rows"], 1):
            row_id = row.get("id", f"row-{index}")
            url = row.get("official_url") or ""
            if row.get("confidence") == "High":
                prediction = row.get("prediction") or {}
                probability = prediction.get("fair_prob", row.get("featured_fair_prob", row.get("match_winner_prob")))
                if isinstance(probability, (int, float)) and probability < 0.70:
                    add(dataset, row_id, "HIGH_BELOW_70_PERCENT",
                        f"High label/prediction is attached to {probability:.4%}, below the stated 70% floor.", url)
                if prediction:
                    text = prediction.get("text", "")
                    if words(text) < 30:
                        add(dataset, row_id, "PREDICTION_UNDER_30_WORDS",
                            f"Prediction has {words(text)} words by the repository tokeniser.", url)
                    american = prediction.get("fair_american")
                    if isinstance(american, int) and not (-250 <= american <= -100 or 100 <= american <= 10000):
                        add(dataset, row_id, "PREDICTION_OUTSIDE_FOCUS_WINDOW",
                            f"Published fair American price {american:+d} is outside −250…+10,000.", url)
                else:
                    add(dataset, row_id, "HIGH_WITHOUT_PREDICTION",
                        "High confidence is assigned without a written prediction.", url)
            if captured_urls and url and url not in captured_urls:
                add(dataset, row_id, "ROW_URL_NOT_IN_RAW_CAPTURE",
                    "The row's displayed official URL is not a target in its own raw-capture manifest. This is a reproducibility gap, not proof the fixture is false.", url)
            start = row.get("start_utc") or ""
            if start and start < "2026-10-22T20:56:17Z":
                add(dataset, row_id, "STARTED_BEFORE_AF_REVIEW",
                    "The fixture start predates Board AF's 20:56 UTC review; do not carry it forward as upcoming.", url)

    # An exact, official-source-backed example is called out separately from structural checks.
    ae_path = DATA.parent / "session-22ca2e95" / "desk.json"
    if ae_path.exists():
        ae = load(ae_path)
        for row in ae["rows"]:
            if row.get("id") == "ae_038" and row.get("match_winner_prob") == 0.592:
                add("official-cross-check", "ae_038", "DIRECT_RULE_CONTRADICTION",
                    "Board AE labels Milwaukee High at 0.592 (59.2%). Its cited MLB fixture is real, but that probability cannot satisfy a ≥70% High rule.",
                    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-02&hydrate=team")

    summary = {dataset: dict(counter) for dataset, counter in counts.items()}
    payload = {
        "schema": "olbg4.board-af.repo-review/v1",
        "method": "Every row in the named datasets is checked mechanically. Structural findings are not represented as fresh factual verification of every peer claim.",
        "datasets": [str(master_path.relative_to(ROOT)), "data/session-22ca2e95/desk.json", "data/session-f0622b6e/desk.json"],
        "rows_checked": {"data/master.json": len(master["rows"])},
        "finding_count": len(findings), "summary": summary, "findings": findings,
    }
    for session in ("22ca2e95", "f0622b6e"):
        path = DATA.parent / f"session-{session}" / "desk.json"
        if path.exists():
            payload["rows_checked"][f"data/session-{session}/desk.json"] = len(load(path)["rows"])
    dump(DATA / "repo_review.json", payload)
    print(f"Repo review: {len(findings)} findings across {payload['rows_checked']}")
    return payload


if __name__ == "__main__":
    review()

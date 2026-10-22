#!/usr/bin/env python3
"""Board AD repo review (session arena/8cbd0cb9-olbg4, AD4).

Line-by-line structural review of data/master.json (336 rows) and of every committed
peer-session desk.json, against what can be checked offline from committed data only
(no network: OLBG.com and governing-body domains are unreachable from this sandbox).

Nothing is inferred. Rows are reported as-is with the exact fields found; defects are
logged for manual review on the Flagged-for-Review page (non-blocking).

Writes data/session-8cbd0cb9/repo_review.json.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "session-8cbd0cb9"

EXCLUDED_SPORTS = {
    "soccer", "football", "boxing", "ufc", "mma", "american football",
    "hurling", "horse racing", "cycling", "specials",
}
VALID_CONFIDENCE = {"Low", "Medium", "High", ""}


def review_master() -> list[dict]:
    m = json.loads((ROOT / "data" / "master.json").read_text())
    rows = m.get("rows", [])
    defects: list[dict] = []
    stats = {"rows": len(rows), "excluded_sport_rows": 0, "no_source_url": 0,
             "dated_before_cutoff": 0, "pick_without_confidence": 0,
             "prediction_under_30_words": 0, "outrights": len(m.get("outrights", []))}
    for r in rows:
        rid = r.get("id", "")
        sport = r.get("sport", "")
        findings: list[str] = []
        if sport.lower() in EXCLUDED_SPORTS:
            stats["excluded_sport_rows"] += 1
            findings.append(f"Excluded sport '{sport}' appears in master board")
        src = r.get("source_url") or ""
        if not src:
            stats["no_source_url"] += 1
            findings.append("No source_url recorded on row")
        date = r.get("date") or ""
        if date and date[:10] < "2026-10-21":
            stats["dated_before_cutoff"] += 1
            findings.append(f"Date {date[:10]} precedes the 2026-10-21 cutoff — historical snapshot, not a verified upcoming fixture")
        pick = r.get("pick") or ""
        conf = r.get("confidence") or ""
        if pick and not conf:
            stats["pick_without_confidence"] += 1
            findings.append("Pick recorded but confidence blank")
        pred = r.get("prediction") or ""
        if pred and len(pred.split()) < 30:
            stats["prediction_under_30_words"] += 1
            findings.append(f"Prediction present but only {len(pred.split())} words (< 30)")
        if conf and conf not in VALID_CONFIDENCE:
            findings.append(f"Invalid confidence value '{conf}'")
        if findings:
            defects.append({"id": rid, "sport": sport, "match": f'{r.get("home","")} vs {r.get("away","")}',
                            "date": date, "source_url": src, "findings": findings})
    stats["defect_rows"] = len(defects)
    return {"dataset": "data/master.json", "schema": m.get("schema"), "generated_on": m.get("generated_on"),
            "stats": stats, "defects": defects}


def review_session_desks() -> list[dict]:
    reviews = []
    for d in sorted((ROOT / "data").glob("session-*")):
        desk_path = d / "desk.json"
        if not desk_path.exists():
            continue
        try:
            desk = json.loads(desk_path.read_text())
        except Exception as exc:  # noqa: BLE001
            reviews.append({"session": d.name, "error": f"desk.json unreadable: {exc}"})
            continue
        rows = desk.get("rows", [])
        issues = []
        n_missing_source = 0
        n_no_pick = 0
        n_bad_conf = 0
        for r in rows:
            rid = r.get("id", "")
            source_url = r.get("official_url") or r.get("source_url") or ""
            pick = r.get("match_winner_pick") or r.get("pick") or ""
            conf = r.get("confidence")
            row_issues = []
            if not source_url.startswith("https://"):
                n_missing_source += 1
                row_issues.append("no https source_url/official_url")
            if not pick:
                n_no_pick += 1
                row_issues.append("no match winner pick")
            if conf not in ("Low", "Medium", "High"):
                n_bad_conf += 1
                row_issues.append(f"confidence not Low/Medium/High: {conf!r}")
            if row_issues:
                issues.append({"id": rid, "sport": r.get("sport"), "match": r.get("match"), "findings": row_issues})
        field_set: set[str] = set()
        for r in rows[:50]:
            field_set.update(r.keys())
        notes: list[str] = []
        if d.name == "session-19b8e377":
            notes.append("Board Z desk (board.json-derived): carries source_url and pick; confidence is not a desk field — 'invalid confidence' count reflects schema variant, not missing values")
        if d.name == "session-c4fda15e":
            notes.append("OLBG event inventory (row_kind inventory entries): picks and confidences are not expected on inventory rows")
        reviews.append({
            "session": d.name,
            "desk_file": str(desk_path.relative_to(ROOT)),
            "rows": len(rows),
            "sample_fields": sorted(field_set),
            "missing_official_url": n_missing_source,
            "no_pick": n_no_pick,
            "invalid_confidence": n_bad_conf,
            "notes": notes,
            "issues": issues[:25],  # cap per session for readability
        })
    return reviews


def main() -> None:
    report = {
        "schema": "olbg4.session-8cbd0cb9.repo_review.v1",
        "board": "AD",
        "session_id": "8cbd0cb9",
        "generated_at_utc": "2026-10-22T13:00:00Z",
        "note": "Offline structural review only; no network access to official domains from this sandbox, so no row is re-verified against a live governing-body page. All defects flagged for manual review, non-blocking.",
        "master": review_master(),
        "session_desks": review_session_desks(),
    }
    (OUT / "repo_review.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    ms = report["master"]["stats"]
    print(f"master.json: {ms['rows']} rows, {ms['defect_rows']} defect rows "
          f"(excluded-sport {ms['excluded_sport_rows']}, no-source {ms['no_source_url']}, "
          f"pre-cutoff {ms['dated_before_cutoff']}, pick-no-conf {ms['pick_without_confidence']}, "
          f"short-pred {ms['prediction_under_30_words']})")
    for s in report["session_desks"]:
        print(f"  {s['session']}: {s['rows']} rows, missing source {s['missing_official_url']}, "
              f"no pick {s['no_pick']}, bad conf {s['invalid_confidence']}")


if __name__ == "__main__":
    main()

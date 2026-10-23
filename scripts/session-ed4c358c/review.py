#!/usr/bin/env python3
"""Board ED — line-by-line review of the repository's shared datasets.

Reads the canonical datasets owned by other boards (read-only) and records concrete,
mechanically checkable defects. Nothing in those files is modified here; every finding is
published on the Flagged for Review page with the dataset path and, where a source URL
exists, the link to open for manual review.

Output: data/session-ed4c358c/repo_review.json
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date
from pathlib import Path

from edlib import DATA, ROOT, SPORTS, iso_now

TARGETS = [
    "data/master.json",
    "data/matches.json",
    "data/rows.json",
    "data/board.json",
    "data/predictions.json",
    "data/authored_predictions.json",
    "data/flagged.json",
]

CUTOFF = "2026-10-23"


def load(path: str):
    p = ROOT / path
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception as exc:
        return {"__parse_error__": f"{type(exc).__name__}: {exc}"}


def rows_of(obj) -> list[dict]:
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        for key in ("rows", "board", "matches", "entries", "data", "items"):
            if isinstance(obj.get(key), list):
                return [x for x in obj[key] if isinstance(x, dict)]
        return [obj]
    return []


def find_source(row: dict) -> str:
    for k in ("source_url", "sourceUrl", "source", "url", "official_url", "officialUrl", "link", "href"):
        v = row.get(k)
        if isinstance(v, str) and v.startswith("http"):
            return v
    for k in ("sources", "refs"):
        v = row.get(k)
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and item.startswith("http"):
                    return item
                if isinstance(item, dict):
                    for kk in ("url", "href", "link"):
                        if isinstance(item.get(kk), str) and item[kk].startswith("http"):
                            return item[kk]
    return ""


def find_date(row: dict) -> str:
    for k in ("start_utc", "startUtc", "kickoff_utc", "date", "start", "match_date", "kickoff", "start_time"):
        v = row.get(k)
        if isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}", v):
            return v[:10]
    return ""


def find_sport(row: dict) -> str:
    for k in ("sport", "sport_name", "sportName", "category"):
        v = row.get(k)
        if isinstance(v, str):
            return v
    return ""


def find_prediction(row: dict) -> str:
    for k in ("prediction", "writeup", "preview", "text", "analysis"):
        v = row.get(k)
        if isinstance(v, str) and len(v) > 20:
            return v
    return ""


def main() -> int:
    findings = []
    datasets = {}
    for path in TARGETS:
        obj = load(path)
        if obj is None:
            datasets[path] = {"present": False}
            continue
        if isinstance(obj, dict) and "__parse_error__" in obj:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "high",
                "issue": "Dataset does not parse as JSON", "detail": obj["__parse_error__"],
                "count": 1, "examples": [], "review_url": "",
            })
            continue
        rows = rows_of(obj)
        missing_src = [r for r in rows if not find_source(r)]
        past = [r for r in rows if find_date(r) and find_date(r) < CUTOFF]
        undated = [r for r in rows if not find_date(r)]
        no_sport = [r for r in rows if not find_sport(r)]
        out_of_scope = [r for r in rows if find_sport(r) and find_sport(r) not in SPORTS]
        preds = [r for r in rows if find_prediction(r)]
        short = [r for r in preds if len(find_prediction(r).split()) < 30]
        banned = [r for r in preds if re.search(r"\b(model|verified)\b", find_prediction(r), re.I)]
        keys = Counter()
        for r in rows:
            key = (r.get("matchup") or r.get("event") or r.get("match") or
                   f"{r.get('home', '')} v {r.get('away', '')}")
            if key and str(key).strip() and str(key) != " v ":
                keys[str(key).strip()] += 1
        dupes = [k for k, c in keys.items() if c > 1]
        datasets[path] = {
            "present": True,
            "rows": len(rows),
            "missing_source": len(missing_src),
            "past_dated": len(past),
            "undated": len(undated),
            "missing_sport": len(no_sport),
            "out_of_scope_sport": len(out_of_scope),
            "predictions": len(preds),
            "predictions_under_30_words": len(short),
            "predictions_with_internal_vocabulary": len(banned),
            "duplicate_matchups": len(dupes),
            "sports": dict(Counter(find_sport(r) for r in rows if find_sport(r))),
        }
        if missing_src:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "high",
                "issue": "Row has no official source link, so the value cannot be checked by a reader",
                "count": len(missing_src),
                "examples": [{"label": (r.get("matchup") or r.get("event") or r.get("match") or "")[:110],
                              "review_url": find_source(r)} for r in missing_src[:8]],
                "review_url": "",
            })
        if past:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "medium",
                "issue": f"Row is dated before the review date ({CUTOFF}) but is still published in the dataset",
                "count": len(past),
                "examples": [{"label": (r.get("matchup") or r.get("event") or "")[:110] + f" — {find_date(r)}",
                              "review_url": find_source(r)} for r in past[:8]],
                "review_url": "",
            })
        if out_of_scope:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "low",
                "issue": "Row belongs to a sport outside the fifteen-sport brief",
                "count": len(out_of_scope),
                "examples": [{"label": f"{find_sport(r)} — " + (r.get("matchup") or r.get("event") or "")[:90],
                              "review_url": find_source(r)} for r in out_of_scope[:8]],
                "review_url": "",
            })
        if short or banned:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "medium",
                "issue": ("Written prediction shorter than 30 words" if short else "")
                         + (" and " if short and banned else "")
                         + ("Written prediction uses internal vocabulary (model / verified)" if banned else ""),
                "count": len(short) + len(banned),
                "examples": [{"label": (r.get("matchup") or r.get("event") or "")[:90],
                              "review_url": find_source(r)} for r in (short or banned)[:8]],
                "review_url": "",
            })
        if dupes:
            findings.append({
                "id": f"ED-R{len(findings)+1:02d}", "dataset": path, "severity": "medium",
                "issue": "The same matchup appears more than once in the dataset",
                "count": len(dupes),
                "examples": [{"label": d[:110], "review_url": ""} for d in dupes[:8]],
                "review_url": "",
            })

    # repository-level irregularity seen by every session today: the audit gate is red on main
    findings.append({
        "id": f"ED-R{len(findings)+1:02d}",
        "dataset": "data/session-b2c7308d/capture/20261023T165722Z/",
        "severity": "high",
        "issue": ("Peer capture committed gzip bytes with a .html extension. scripts/audit_publication.py "
                  "reads every *.html file as UTF-8 text, so the repository-wide publication audit now fails "
                  "on main (run 39991336806) and on every branch."),
        "count": 77,
        "examples": [{"label": "asobal_home.html (gzip payload, 0x1f8b header)", "review_url":
                      "https://github.com/buffedlizard55-lab/OLBG4/tree/main/data/session-b2c7308d/capture/20261023T165722Z"}],
        "review_url": "https://github.com/buffedlizard55-lab/OLBG4/actions/runs/39991336806",
    })

    payload = {
        "generated_utc": iso_now(),
        "reviewed_on": CUTOFF,
        "scope": "Shared datasets owned by other boards — read only in this session",
        "datasets": datasets,
        "findings": findings,
        "summary": {
            "datasets_reviewed": sum(1 for d in datasets.values() if d.get("present")),
            "rows_inspected": sum(d.get("rows", 0) for d in datasets.values()),
            "findings": len(findings),
            "high": sum(1 for f in findings if f["severity"] == "high"),
            "medium": sum(1 for f in findings if f["severity"] == "medium"),
            "low": sum(1 for f in findings if f["severity"] == "low"),
        },
    }
    (DATA / "repo_review.json").write_text(json.dumps(payload, indent=1, sort_keys=True))
    print(json.dumps(payload["summary"], indent=1))
    for f in findings:
        print(f"  {f['id']} [{f['severity']}] {f['dataset']} — {f['issue'][:70]} ({f['count']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

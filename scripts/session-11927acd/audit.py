#!/usr/bin/env python3
"""RI1: audit committed source bytes and enumerate legacy numerical candidates.

This deliberately does not promote a numerical candidate. OLBG availability, an official
fixture crosswalk, sample sufficiency and calculation integrity are separate gates.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import ri


def sample_number(row: dict) -> int:
    text = row.get("sample") or ""
    try:
        return int(str(text).split()[0])
    except (ValueError, IndexError):
        return 0


def legacy_candidates() -> list[dict]:
    found = []
    for row in ri.BASE_DESK["rows"]:
        for market_key, market in (row.get("markets") or {}).items():
            for selection in market.get("selections", []):
                p = selection.get("fair_prob")
                a = selection.get("fair_american")
                if p is None or a is None or not (p > 0.70 and -250 <= a <= 10000):
                    continue
                reasons = []
                if not row.get("olbg") and row["id"] not in ri.NHL_OLBG:
                    reasons.append("no captured OLBG event crosswalk")
                if not row.get("official_url") or ri.is_olbg(row.get("official_url", "")) or row.get("capture_id", "").startswith("olbg_"):
                    reasons.append("fixture identity is not established by an official programme")
                if row["sport"] == "Ice Hockey" and sample_number(row) < 10:
                    reasons.append("fewer than ten games played for at least one club")
                caveat = " ".join(row.get("flags") or []).lower()
                rule = (row.get("pick") or {}).get("rule", "").lower()
                if "cap" in caveat or "cap" in rule and "capped medium" in rule:
                    reasons.append("published sample/confidence cap")
                found.append({
                    "row_id": row["id"], "sport": row["sport"],
                    "match": f"{row['side_a']} at {row['side_b']}", "start_utc": row["start_utc"],
                    "market_key": market_key, "market": market["market_name"],
                    "selection": selection["label"], "fair_prob": p, "fair_american": a,
                    "decision": "rejected" if reasons else "needs-raw-recalculation",
                    "reasons": reasons,
                    "official_url": row.get("official_url") or "",
                    "olbg_url": (row.get("olbg") or {}).get("url", ""),
                })
    return found


def main() -> int:
    payload_audit = []
    for record in ri.MANIFEST["records"]:
        actual = ri.actual_sha(record["id"])
        payload_audit.append({
            "id": record["id"], "url": record["url"], "status": record["status"],
            "file": record["file"], "manifest_sha256": record["sha256"],
            "actual_sha256": actual, "sha_match": actual == record["sha256"],
            "bytes": record["bytes"],
        })
    failures = []
    for failure in ri.MANIFEST.get("failures", []):
        failures.append({k: failure.get(k) for k in ("id", "sport", "url", "status", "error")})

    row_audit = []
    for row in ri.BASE_DESK["rows"]:
        capture_id = row.get("capture_id") or ""
        record = ri.RECORDS.get(capture_id)
        official_url = row.get("official_url") or ""
        fixture_from_olbg = capture_id.startswith("olbg_")
        source_kind = ("official-stats-only-olbg-fixture" if fixture_from_olbg and official_url and not ri.is_olbg(official_url)
                       else "missing" if not official_url
                       else ("olbg-not-official" if ri.is_olbg(official_url) or fixture_from_olbg else "official"))
        issues = []
        if not record:
            issues.append("capture id absent from manifest")
        elif not ri.actual_sha(capture_id) == record["sha256"]:
            issues.append("payload hash mismatch")
        if source_kind != "official":
            issues.append("no official fixture-source URL; OLBG listing is not an official league source")
        row_audit.append({
            "row_id": row["id"], "sport": row["sport"], "capture_id": capture_id,
            "manifest_present": bool(record), "payload_sha_match": bool(record and ri.actual_sha(capture_id) == record["sha256"]),
            "source_kind": source_kind, "official_url": official_url if source_kind == "official" else "",
            "review_url": official_url or (row.get("olbg") or {}).get("url", ""),
            "issues": issues,
        })

    candidates = legacy_candidates()
    audit = {
        "schema": "olbg4.board-ri.audit/1",
        "generated_utc": ri.generated_utc(),
        "base_desk": f"data/{ri.BASE_SID}/desk.json",
        "capture_id": ri.CAPTURE_ID,
        "scope_note": "Raw bytes, hashes, row source types and legacy numerical candidates audited. The four published NHL selections are separately recomputed from raw standings and schedules in build_data.py.",
        "summary": {
            "payloads_ok": sum(x["sha_match"] and x["status"] == 200 for x in payload_audit),
            "payloads_total": len(payload_audit),
            "capture_failures": len(failures),
            "rows": len(row_audit),
            "rows_official_source": sum(x["source_kind"] == "official" for x in row_audit),
            "rows_olbg_mislabeled_as_official": sum(x["source_kind"] == "olbg-not-official" for x in row_audit),
            "rows_official_stats_only_olbg_fixture": sum(x["source_kind"] == "official-stats-only-olbg-fixture" for x in row_audit),
            "row_hash_mismatches": sum(not x["payload_sha_match"] for x in row_audit),
            "legacy_numeric_candidates": len(candidates),
        },
        "payloads": payload_audit,
        "capture_failures": failures,
        "rows": row_audit,
        "known_defects": [
            {
                "id": "CA-E977-NHL-LAMBDA-PAIRING",
                "severity": "critical",
                "where": "scripts/session-e9770274/originate.py:build_nhl",
                "detail": "The earlier NHL build passed the home club's attack/defence figures to both expected-goals calls. Its probabilities are not eligible for RI publication; RI uses the corrected away-attack/home-defence pairing and recomputes from raw standings.",
            },
            {
                "id": "CA-B664-OLBG-OFFICIAL-LABEL",
                "severity": "major",
                "where": "data/session-b6643783/desk.json",
                "detail": "Rows sourced only from OLBG carried an official_url pointing to OLBG after augmentation. RI clears that official-source label and flags the affected rows for manual official-programme review.",
            },
        ],
    }
    ri.dump(ri.DATA / "audit.json", audit)
    ri.dump(ri.DATA / "candidates.json", {
        "schema": "olbg4.board-ri.candidates/1",
        "rule": "Strictly greater than 70%; fair American price from -250 through +10000. Numerical status alone never approves a pick.",
        "legacy": candidates,
        "ri": [],
    })
    print(f"RI1 PASS: {len(payload_audit)} payload hashes; {len(row_audit)} row provenance records; {len(candidates)} legacy numerical candidates")
    print("Source kinds:", dict(Counter(x["source_kind"] for x in row_audit)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

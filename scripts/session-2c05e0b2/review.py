#!/usr/bin/env python3
"""Board AI — line-by-line review of the repository's shared datasets.

Checks performed on every row of data/master.json (the consolidated board other desks
publish into) and on data/matches.json:

  R1  in-scope row with no official source URL
  R2  row outside the 15-sport brief (recorded, not treated as a defect)
  R3  fixture dated before the 2026-10-23 review date
  R4  High-confidence row with no pick
  R5  High-confidence row whose prediction is empty or under 30 words
  R6  two rows sharing an identical prediction text
  R7  decimal / American price pair that does not agree
  R8  row whose own "verified" flag contradicts an empty source URL

Nothing is corrected: the output is a register for manual review, with the URL a
reviewer should open for each finding.

Usage: python3 scripts/session-2c05e0b2/review.py
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "session-2c05e0b2")
TODAY = "2026-10-23"
SCOPE = {"Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
         "Gaelic Sports", "Gaelic Football", "Greyhounds", "Greyhound Racing", "Tennis",
         "Motor Racing", "Handball", "Ice Hockey", "Basketball", "Rugby League"}


def am_from_dec(dec: float) -> str:
    if dec <= 1.0001:
        return ""
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"-{round(100 / (dec - 1))}"


def prices(odds: dict) -> list[tuple[str, float]]:
    """Pull (side, decimal) pairs out of the many shapes the board uses."""
    out = []
    if not isinstance(odds, dict):
        return out
    for side, v in odds.items():
        if isinstance(v, (int, float)):
            if 1.0 < float(v) < 1000:
                out.append((side, float(v)))
        elif isinstance(v, dict):
            for k in ("decimal", "price", "dec"):
                if isinstance(v.get(k), (int, float)) and 1.0 < float(v[k]) < 1000:
                    out.append((side, float(v[k])))
                    break
        elif isinstance(v, str) and re.fullmatch(r"\d+\.\d+", v):
            out.append((side, float(v)))
    return out


def review_master() -> dict:
    path = os.path.join(ROOT, "data", "master.json")
    data = json.load(open(path))
    rows = data["rows"]
    findings = defaultdict(list)
    pred_texts = defaultdict(list)
    for r in rows:
        rid = r.get("id", "")
        sport = r.get("sport", "")
        src = r.get("source_url", "")
        conf = (r.get("confidence") or "").strip()
        pred = (r.get("prediction") or "").strip()
        if r.get("in_scope") and not src:
            findings["R1_no_source"].append({
                "row": rid, "sport": sport, "date": r.get("date", ""),
                "detail": "in-scope row has no source URL",
                "manual_review": "",
            })
        if sport and sport not in SCOPE:
            findings["R2_out_of_scope_sport"].append({
                "row": rid, "sport": sport, "date": r.get("date", ""),
                "detail": "sport is outside the 15-sport brief",
                "manual_review": src,
            })
        if r.get("date", "") and r["date"] < TODAY:
            findings["R3_past_dated"].append({
                "row": rid, "sport": sport, "date": r["date"],
                "detail": "fixture date is before the review date",
                "manual_review": src,
            })
        if conf == "High" and not (r.get("pick") or "").strip():
            findings["R4_high_no_pick"].append({
                "row": rid, "sport": sport, "date": r.get("date", ""),
                "detail": "High confidence with no pick", "manual_review": src})
        if conf == "High" and len(pred.split()) < 30:
            findings["R5_high_short_prediction"].append({
                "row": rid, "sport": sport, "date": r.get("date", ""),
                "detail": f"High confidence prediction has {len(pred.split())} words",
                "manual_review": src})
        if pred:
            pred_texts[pred].append(rid)
        for side, dec in prices(r.get("win", {}).get("odds", {}) if isinstance(r.get("win"), dict) else {}):
            am = (r.get("win", {}).get("american", {}) or {}).get(side)
            if isinstance(am, str) and re.fullmatch(r"[+-]\d+", am.strip()):
                if am_from_dec(dec) != am.strip():
                    findings["R7_price_math"].append({
                        "row": rid, "sport": sport, "date": r.get("date", ""),
                        "detail": f"{side}: decimal {dec} -> {am_from_dec(dec)}, row says {am}",
                        "manual_review": src})
        if r.get("verified") and not src:
            findings["R8_verified_without_source"].append({
                "row": rid, "sport": sport, "date": r.get("date", ""),
                "detail": "row is flagged verified but carries no source URL",
                "manual_review": ""})
    for text, ids in pred_texts.items():
        if len(ids) > 1:
            findings["R6_duplicate_prediction"].append({
                "row": ", ".join(ids[:6]) + (" ..." if len(ids) > 6 else ""),
                "sport": "", "date": "",
                "detail": f"{len(ids)} rows share an identical prediction: {text[:90]}",
                "manual_review": ""})
    checks = Counter({"rows": len(rows)})
    for r in rows:
        w = r.get("win") if isinstance(r.get("win"), dict) else {}
        odds = w.get("odds") if isinstance(w.get("odds"), dict) else {}
        for side, v in odds.items():
            if isinstance(v, (int, float)) or (isinstance(v, str) and re.fullmatch(r"\d+\.\d+", v)):
                checks["numeric_prices"] += 1
    return {
        "dataset": "data/master.json",
        "rows": len(rows),
        "checks_run": dict(checks),
        "findings": {k: v for k, v in sorted(findings.items())},
        "counts": {k: len(v) for k, v in sorted(findings.items())},
        "by_sport": dict(Counter(r.get("sport", "") for r in rows).most_common()),
    }


def review_matches() -> dict:
    path = os.path.join(ROOT, "data", "matches.json")
    if not os.path.exists(path):
        return {"dataset": "data/matches.json", "rows": 0, "counts": {}, "findings": {}}
    data = json.load(open(path))
    rows = [r for r in data if isinstance(r, dict)]
    findings = defaultdict(list)
    checks = Counter()
    for r in rows:
        rid, sport, date = r.get("id", ""), r.get("sport", ""), r.get("date", "")
        src = r.get("sourceUrl") or r.get("source_url") or ""
        pred = (r.get("prediction") or "").strip()
        conf = (r.get("confidence") or "").strip()
        checks["rows"] += 1
        if not src:
            findings["M1_no_source"].append({"row": rid, "sport": sport, "date": date,
                "detail": "row carries no sourceUrl", "manual_review": ""})
        if date and date < TODAY:
            findings["M2_past_dated"].append({"row": rid, "sport": sport, "date": date,
                "detail": "fixture date is before the review date", "manual_review": src})
        if conf == "High" and len(pred.split()) < 30:
            findings["M3_high_short_prediction"].append({"row": rid, "sport": sport, "date": date,
                "detail": f"High confidence prediction has {len(pred.split())} words",
                "manual_review": src})
        ml = r.get("originatedMoneyline") or {}
        if isinstance(ml, dict) and ml:
            decs = []
            for side, v in ml.items():
                try:
                    decs.append(float(v))
                except (TypeError, ValueError):
                    findings["M4_bad_price"].append({"row": rid, "sport": sport, "date": date,
                        "detail": f"side {side} has a non-numeric price {v!r}",
                        "manual_review": src})
            if len(decs) == 2:
                checks["two_way_moneylines"] += 1
                overround = sum(1 / d for d in decs)
                if overround < 0.99 or overround > 1.30:
                    findings["M5_implausible_margin"].append({
                        "row": rid, "sport": sport, "date": date,
                        "detail": f"two-way implied probability sums to {overround:.3f}",
                        "manual_review": src})
    return {"dataset": "data/matches.json", "rows": len(rows),
            "checks_run": dict(checks),
            "counts": {k: len(v) for k, v in sorted(findings.items())},
            "findings": {k: v for k, v in sorted(findings.items())}}


def main() -> int:
    doc = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "review_date": TODAY,
        "scope_note": "The 15-sport brief is narrower than data/master.json, which also carries "
                      "Aussie Rules, Badminton, Table Tennis and Esports rows. Those rows are "
                      "recorded under R2 and are not published on this board.",
        "datasets": [review_master(), review_matches()],
    }
    json.dump(doc, open(os.path.join(OUT, "repo_review.json"), "w"), indent=1, sort_keys=True)
    for d in doc["datasets"]:
        print(d["dataset"], d["rows"], json.dumps(d["counts"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) - line-by-line review of the shared repo datasets.

Reads the canonical shared board and every peer desk (all read-only for Board AF), re-checks
each row against the rules the brief sets, re-derives every price from its own probability and
publishes exact findings with the URL a reviewer should open. Nothing here is edited: findings
that would need another owner's file are recorded as integration requests.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")
CUTOFF_DATE = "2026-10-22"
OFFICIAL_HINTS = re.compile(
    r"(nhl\.com|api-web\.nhle\.com|mlb\.com|statsapi\.mlb\.com|nba\.com|stats\.nba\.com|atptour\.com|wtatennis\.com|"
    r"icc-cricket\.com|ecb\.co\.uk|bcci\.tv|cricket\.com\.au|blackcaps\.co\.nz|unitedrugby\.com|premierrugby\.com|"
    r"epcrugby\.com|world\.rugby|lnr\.fr|nrl\.com|rlwc2026\.com|superleague\.co\.uk|internationalrugbyleague\.com|"
    r"pdc\.tv|wst\.tv|wpbsa\.com|owgr\.com|pgatour\.com|dpworldtour\.com|lpga\.com|cev\.eu|volleyballworld\.com|"
    r"plusliga\.pl|legavolley\.it|eurohandball\.com|ehfcl\.|worldtabletennis\.com|ittf\.com|bwfbadminton\.com|"
    r"afl\.com\.au|lolesports\.com|formula1\.com|motogp\.com|wrc\.com|gbgb\.org\.uk|gaa\.ie|olbg\.com|fifa\.com|"
    r"premierleague\.com|uefa\.com|espn|bbc|skysports|flashscore|sofascore|bet365|wikipedia)", re.I)
EXCLUDED_SPORTS = {"soccer", "football", "boxing", "ufc", "mma", "american football", "hurling",
                   "horse racing", "cycling", "specials", "association football"}


def american_from_p(p):
    if not p or p <= 0 or p >= 1:
        return None
    dec = 1.0 / p
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def review_rows(rows, dataset, findings, url_for=lambda r: r.get("source_url") or r.get("sourceUrl") or ""):
    for i, r in enumerate(rows, 1):
        rid = str(r.get("id") or r.get("row_id") or i)
        loc = f"{dataset}:{rid}"
        sport = str(r.get("sport") or r.get("Sport") or "").strip()
        if sport and sport.lower() in EXCLUDED_SPORTS:
            findings.append({"severity": "scope", "where": loc, "sport": sport,
                             "finding": f"row carries an excluded sport ('{sport}') but is published in the shared board",
                             "rule": "brief excludes soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling, specials",
                             "review_url": url_for(r)})
        date = str(r.get("date") or r.get("start_date") or r.get("kickoff") or "")[:10]
        if date and date < CUTOFF_DATE:
            findings.append({"severity": "stale", "where": loc, "sport": sport,
                             "finding": f"fixture dated {date} is before the {CUTOFF_DATE} cut-off, so it cannot be an upcoming match",
                             "rule": "brief asks for updated/upcoming matches only", "review_url": url_for(r)})
        if not url_for(r):
            findings.append({"severity": "no-source", "where": loc, "sport": sport,
                             "finding": "row publishes a fixture, pick or price with no source URL at all",
                             "rule": "every table row must carry an official source link", "review_url": ""})
        elif "olbg.com" in url_for(r).lower() and str(r.get("verification") or r.get("verified") or "").lower() in ("official", "verified", "true", "yes"):
            findings.append({"severity": "source-tier", "where": loc, "sport": sport,
                             "finding": f"row is marked verified but its only link is OLBG ({url_for(r)}), which is the site being reverse-engineered, not a governing body",
                             "rule": "official = league / tour / federation / organiser / regulator", "review_url": url_for(r)})
        elif url_for(r) and not OFFICIAL_HINTS.search(url_for(r)):
            findings.append({"severity": "source-tier", "where": loc, "sport": sport,
                             "finding": f"source URL is not a recognised official domain: {url_for(r)}",
                             "rule": "official = league / tour / federation / organiser / regulator", "review_url": url_for(r)})
        # price arithmetic
        for m in (r.get("markets") or ([r] if r.get("p") else [])):
            if not isinstance(m, dict):
                continue
            p = m.get("p") or m.get("probability")
            dec = m.get("fair_dec") or m.get("fair_decimal") or m.get("decimal")
            am = m.get("fair_american") or m.get("american")
            if not isinstance(p,(int,float)) or not isinstance(dec,(int,float)):
                continue
            if p and dec:
                if abs(dec - 1 / p) > 0.01:
                    findings.append({"severity": "maths", "where": loc, "sport": sport,
                                     "finding": f"published decimal {dec} does not equal 1/p for p={p} (expected {1/p:.4f})",
                                     "rule": "fair price = 1 / model probability", "review_url": url_for(r)})
            if p and isinstance(am,(int,float)):
                exp = american_from_p(p)
                if exp is not None and abs(int(am) - exp) > 2:
                    findings.append({"severity": "maths", "where": loc, "sport": sport,
                                     "finding": f"published American {am} does not match p={p} (expected {exp})",
                                     "rule": "decimal<->American conversion", "review_url": url_for(r)})
        # predictions
        for key in ("prediction", "prediction_text", "text", "write_up"):
            t = r.get(key)
            if isinstance(t, str) and t.strip():
                words = len(t.split())
                if words < 30:
                    findings.append({"severity": "prediction-length", "where": loc, "sport": sport,
                                     "finding": f"prediction is {words} words, below the 30-word minimum",
                                     "rule": "each prediction at least 30 words", "review_url": url_for(r)})
                break


def main() -> int:
    findings: list = []
    datasets: list = []
    targets = [("data/master.json", "rows"), ("data/master_olbg.json", "rows"),
               ("data/authored_predictions.json", "predictions"), ("data/predictions.json", "predictions"),
               ("data/integrated/entries.json", "entries"), ("data/integrated/predictions.json", "predictions"),
               ("data/board.json", "rows")]
    for path, key in targets:
        fp = os.path.join(ROOT, path)
        if not os.path.exists(fp):
            continue
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception as exc:
            findings.append({"severity": "unreadable", "where": path, "sport": "",
                             "finding": f"file could not be parsed as JSON: {exc}", "rule": "shared data must be machine-readable",
                             "review_url": ""})
            continue
        rows = doc.get(key) if isinstance(doc, dict) else doc
        if isinstance(rows, dict):
            for k, v in rows.items():
                if isinstance(v, list):
                    rows = v
                    break
        if not isinstance(rows, list):
            continue
        datasets.append({"path": path, "key": key, "rows": len(rows)})
        review_rows(rows, path, findings)
    # peer desks
    for desk in sorted(glob.glob(os.path.join(ROOT, "data", "session-*", "desk.json"))) + \
               sorted(glob.glob(os.path.join(ROOT, "data", "board_*", "*.json"))):
        try:
            doc = json.load(open(desk, encoding="utf-8"))
        except Exception:
            continue
        rows = doc.get("rows") if isinstance(doc, dict) else doc
        if isinstance(rows, list) and rows:
            rel = os.path.relpath(desk, ROOT)
            datasets.append({"path": rel, "key": "rows", "rows": len(rows)})
            review_rows(rows, rel, findings)
    # templated / duplicated prediction text across the repo
    texts = {}
    for ds in datasets:
        fp = os.path.join(ROOT, ds["path"])
        if not os.path.exists(fp):
            continue
        try:
            doc = json.load(open(fp, encoding="utf-8"))
        except Exception:
            continue
        rows = (doc.get("rows") or doc.get("predictions") or doc.get("entries") or []) if isinstance(doc, dict) else doc
        if isinstance(rows, dict):
            rows = next((v for v in rows.values() if isinstance(v, list)), [])
        for r in rows if isinstance(rows, list) else []:
            if not isinstance(r, dict):
                continue
            for key in ("prediction", "prediction_text", "text", "write_up"):
                t = r.get(key)
                if isinstance(t, str) and len(t.split()) >= 8:
                    texts.setdefault(re.sub(r"\s+", " ", t.strip().lower()), []).append(ds["path"])
    dupes = {k: v for k, v in texts.items() if len(v) > 1}
    for t, where in list(dupes.items())[:40]:
        findings.append({"severity": "templated", "where": ",".join(sorted(set(where))), "sport": "",
                         "finding": f"identical prediction text reused {len(where)} times: \"{t[:110]}...\"",
                         "rule": "predictions must be unique and not repetitive", "review_url": ""})

    out = {"schema": "olbg4/board-af-review/v1",
           "reviewed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "cut_off": CUTOFF_DATE, "datasets": datasets,
           "rows_reviewed": sum(d["rows"] for d in datasets),
           "findings_total": len(findings),
           "by_severity": {s: len([f for f in findings if f["severity"] == s])
                           for s in sorted({f["severity"] for f in findings})},
           "duplicate_prediction_texts": len(dupes),
           "findings": findings,
           "integration_requests": [
               {"request": "Add a Board AF pointer (session-80bc6293/index.html) to the root README.md and root index.html once an integration owner next claims those files.",
                "why": "root README.md and root index.html are owned by earlier boards and are read-only for Board AF"},
               {"request": "Do not merge Board AF rows into data/master.json: Board AF's desk keeps its own official source and verification trail per row, and its findings on master.json are advisory.",
                "why": "matches the instruction that shared outputs are only changed by a final integration session"}]}
    json.dump(out, open(os.path.join(DATA, "review.json"), "w"), indent=1)
    print(f"review: {out['rows_reviewed']} rows across {len(datasets)} datasets -> {len(findings)} findings")
    print("  by severity:", json.dumps(out["by_severity"]))
    for d in datasets:
        print(f"    {d['rows']:>5} rows  {d['path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

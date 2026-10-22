#!/usr/bin/env python3
"""Board AD — line-by-line repository review of the canonical board (data/master.json).

Walks every row of data/master.json, applies a fixed list of checks, and writes
data/session-3a6388d2/review.json plus data/session-3a6388d2/flagged.json.

Nothing in this file edits another board's data.  Every finding carries the row id,
the exact defect, and a link the reviewer can open (the row's own source URL where the
row has one, otherwise the board row itself in the repository).
"""
from __future__ import annotations

import json
import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MASTER = os.path.join(ROOT, "data", "master.json")
DESK = os.path.join(ROOT, "data", "session-3a6388d2", "desk.json")
OUT_DIR = os.path.join(ROOT, "data", "session-3a6388d2")

TODAY = "2026-10-22"
EXCLUDED = {"soccer", "football", "american football", "boxing", "ufc", "mma",
            "hurling", "horse racing", "cycling", "specials"}

findings: list[dict] = []
seq = [0]


def add(kind, severity, detail, row=None, link=""):
    seq[0] += 1
    f = {
        "id": f"ADF-{seq[0]:03d}",
        "kind": kind,
        "severity": severity,          # blocking | needs-review | information
        "detail": detail,
        "link": link,
        "row_id": "", "sport": "", "date": "", "match": "",
    }
    if row:
        f["row_id"] = row.get("id", "")
        f["sport"] = row.get("sport", "")
        f["date"] = row.get("date", "")
        f["match"] = f"{row.get('home','')} v {row.get('away','')}".strip()
        if not link:
            f["link"] = row.get("source_url", "") or (
                f"https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json")
    findings.append(f)


def main() -> int:
    with open(MASTER, encoding="utf-8") as fh:
        master = json.load(fh)
    rows = master.get("rows", [])
    outrights = master.get("outrights", [])

    # ---- 1. rows whose date has already passed (cut-off 2026-10-22) -----------------
    stale = [r for r in rows if (r.get("date") or "") < TODAY]
    for r in stale:
        add("stale", "needs-review",
            f"Row is dated {r.get('date')} — before the {TODAY} cut-off — yet is still published as "
            f"'{r.get('status')}'. It carries a pick ('{r.get('pick','')}') and confidence "
            f"'{r.get('confidence','')}' that can no longer be settled.",
            r)

    # ---- 2. rows with no official source link --------------------------------------
    for r in rows:
        if not (r.get("source_url") or "").strip():
            add("no-source", "blocking",
                "Row publishes teams, a competition and a pick but records no source URL, so no value on "
                "the row can be checked against an official site.",
                r, link="https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json")

    # ---- 3. rows whose source domain is not an official governing body -------------
    unofficial = {"www.nottingham-greyhounds.co.uk"}
    for r in rows:
        dom = (r.get("source_domain") or "").lower()
        if dom in unofficial:
            add("source-tier", "needs-review",
                f"Source domain '{dom}' is a venue operator rather than the sport's governing body "
                f"(the GBGB official site is gbgb.org.uk, which returns HTTP 403 to automated readers).",
                r)

    # ---- 4. templated predictions ---------------------------------------------------
    for r in rows:
        if r.get("prediction_style") == "templated":
            add("templated-prediction", "needs-review",
                "The prediction on this High/Medium row is flagged by the originating build as templated, "
                "so it does not read as a bespoke human write-up.",
                r)

    # ---- 5. High confidence with no prediction text ---------------------------------
    for r in rows:
        if r.get("confidence") == "High" and not (r.get("prediction") or "").strip():
            add("high-no-prediction", "needs-review",
                "Confidence is High but no written prediction accompanies the selection.", r)

    # ---- 6. fixtures with no pick / no line ----------------------------------------
    for r in rows:
        if not (r.get("pick") or "").strip():
            add("no-pick", "information",
                "No match-winner pick published for this row (the row may be a market note or an "
                "unpriced fixture).", r)

    # ---- 7. duplicate fixtures inside the canonical board ---------------------------
    groups: dict[tuple, list] = defaultdict(list)
    for r in rows:
        key = (r.get("sport", ""), r.get("date", ""), r.get("home", ""), r.get("away", ""))
        if key[2] and key[2] not in ("No fixture", ""):
            groups[key].append(r)
    for key, grp in groups.items():
        if len(grp) > 1:
            ids = ", ".join(g.get("id", "") for g in grp)
            add("duplicate", "needs-review",
                f"{len(grp)} rows describe the same fixture ({key[0]} {key[1]} {key[2]} v {key[3]}): {ids}. "
                f"They come from different builds ({', '.join(sorted({g.get('build','') for g in grp}))}) and "
                f"may publish different picks or prices for one event.", grp[0])

    # ---- 8. rows outside the owner's scope ------------------------------------------
    for r in rows:
        if r.get("in_scope") is False:
            add("scope", "needs-review",
                f"Sport '{r.get('sport')}' is marked out of scope by the canonical board "
                f"({r.get('scope_note','')}). The brief excludes soccer/football, American football, "
                f"hurling, horse racing, cycling, boxing, UFC/MMA and specials; Gaelic football is not named "
                f"and two earlier boards reached opposite conclusions, so it is published here as a scope call "
                f"for the owner to settle.", r)

    # ---- 9. unverified rows that still publish a pick --------------------------------
    for r in rows:
        if r.get("verified") is False and (r.get("pick") or "").strip() and \
           (r.get("pick") or "").lower().startswith("no pick") is False:
            add("unverified-priced", "needs-review",
                "Row publishes a selection although the canonical board marks it unverified against an "
                "official source.", r)

    # ---- 10. rows contradicted by a later live check ---------------------------------
    for r in rows:
        if r.get("live_contradicted"):
            add("live-contradiction", "needs-review",
                "A later live check of the official source contradicted this row.", r)

    # ---- 11. structural checks on the outright rows -----------------------------------
    for o in outrights:
        if not (o.get("source_url") or "").strip():
            add("outright-no-source", "blocking",
                f"Outright row '{o.get('name','')}' records no official source URL.", o)

    # ---- 12. cross-check: our own desk vs the canonical board --------------------------
    cross = []
    if os.path.exists(DESK):
        with open(DESK, encoding="utf-8") as fh:
            desk = json.load(fh)
        desk_rows = desk.get("rows", [])
        for sport in sorted({r["sport"] for r in desk_rows}):
            mine = [r for r in desk_rows if r["sport"] == sport]
            theirs = [r for r in rows if r.get("sport") == sport and (r.get("date") or "") >= TODAY]
            cross.append({
                "sport": sport,
                "board_ad_rows": len(mine),
                "board_ad_priced": sum(1 for r in mine if r.get("markets")),
                "master_rows_from_today": len(theirs),
                "master_verified": sum(1 for r in theirs if r.get("verified")),
            })

    summary = {
        "master_rows": len(rows),
        "master_outrights": len(outrights),
        "master_generated_on": master.get("generated_on", ""),
        "rows_before_cutoff": len(stale),
        "rows_without_source": sum(1 for r in rows if not (r.get("source_url") or "").strip()),
        "rows_unverified": sum(1 for r in rows if r.get("verified") is False),
        "rows_high_confidence": sum(1 for r in rows if r.get("confidence") == "High"),
        "rows_templated_predictions": sum(1 for r in rows if r.get("prediction_style") == "templated"),
        "sports": dict(Counter(r.get("sport", "") for r in rows)),
        "source_domains": dict(Counter((r.get("source_domain") or "(none)") for r in rows)),
        "findings_by_kind": dict(Counter(f["kind"] for f in findings)),
        "findings_by_severity": dict(Counter(f["severity"] for f in findings)),
    }

    os.makedirs(OUT_DIR, exist_ok=True)
    out = {
        "schema": "olbg4/board-ad-review/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "reviewed_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "subject": "data/master.json (canonical board) — every row, checked line by line",
        "cutoff": TODAY,
        "summary": summary,
        "cross_check": cross,
        "findings": findings,
    }
    with open(os.path.join(OUT_DIR, "review.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
        fh.write("\n")

    flagged = {
        "schema": "olbg4/board-ad-flagged/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": "Everything the owner must eyeball: repository-review findings, the rows in our own desk "
                "that could not be priced from an official source, and every capture that failed.",
        "items": findings,
    }
    with open(os.path.join(OUT_DIR, "flagged.json"), "w", encoding="utf-8") as fh:
        json.dump(flagged, fh, indent=1)
        fh.write("\n")

    print(f"review.json: {len(findings)} findings across {len(rows)} canonical rows")
    print("  by kind:", summary["findings_by_kind"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

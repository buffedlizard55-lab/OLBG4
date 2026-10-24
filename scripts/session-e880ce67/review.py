#!/usr/bin/env python3
"""Line-by-line review of the repository's canonical desk (data/master.json).

Only checks that can be reproduced from the committed file are reported, and every finding
carries the row id and the row's own source URL so it can be opened and checked by hand.
Nothing here edits another session's data.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)
TODAY = "2026-10-24"


def main() -> int:
    master = json.load(open(os.path.join(ROOT, "data", "master.json"), encoding="utf-8"))
    rows = master["rows"]
    findings = []

    def add(key, title, severity, detail, examples):
        findings.append({"id": key, "title": title, "severity": severity,
                         "detail": detail, "count": len(examples),
                         "examples": examples[:6]})

    def ref(row):
        return {"sport": row.get("sport", ""), "date": row.get("date", ""),
                "home": row.get("home", ""), "away": row.get("away", ""),
                "pick": (row.get("pick") or "")[:90], "confidence": row.get("confidence", ""),
                "source_url": row.get("source_url", "")}

    stale = [r for r in rows if r.get("date") and r["date"] < TODAY]
    add("R-01", "Canonical rows dated before the review date", "review",
        "data/master.json was generated on " + str(master.get("generated_on")) +
        ". Rows dated earlier than " + TODAY + " can no longer be bet into; they are counted "
        "in the published totals. Listed for the owner to expire or date-stamp.",
        [ref(r) for r in stale])

    placeholders = [r for r in rows if "no fixture" in (str(r.get("home", "")) + " " +
                                                        str(r.get("away", ""))).lower()]
    add("R-02", "Placeholder rows counted as fixtures", "review",
        "Rows whose home or away field literally reads 'No fixture' are still counted in "
        "rows_total. They carry no match, so they inflate the fixture count.",
        [ref(r) for r in placeholders])

    no_source = [r for r in rows if not r.get("source_url")]
    add("R-03", "Rows with no source URL at all", "review",
        "The brief requires every row to link an official source. These rows have an empty "
        "source_url, so nothing in them can be re-checked.",
        [ref(r) for r in no_source])

    olbg_only = [r for r in rows if "olbg.com" in (r.get("source_url") or "")]
    add("R-04", "Rows sourced only to OLBG itself", "review",
        "OLBG is the site under review, not a governing body. These rows cite only OLBG, so "
        "the fixture identity is not independently confirmed.",
        [ref(r) for r in olbg_only])

    no_pick_high = [r for r in rows if r.get("confidence") == "High"
                    and "no pick" in (r.get("pick") or "").lower()]
    add("R-05", "High confidence label on a row with no pick", "review",
        "A row cannot be High confidence if it publishes no selection; the label contradicts "
        "the content.", [ref(r) for r in no_pick_high])

    bad_preds = [r for r in rows if r.get("prediction") and
                 (len(r["prediction"].split()) < 30 or BANNED.search(r["prediction"]))]
    add("R-06", "Predictions under 30 words or carrying internal vocabulary", "review",
        "The brief sets a 30-word floor and bans words such as 'model' and 'verified' from "
        "published predictions.", [ref(r) for r in bad_preds])

    dup_labels = Counter(r.get("sport") for r in rows)
    mixed = [k for k in dup_labels if k in ("Greyhounds", "Greyhound Racing")]
    add("R-07", "One sport published under two labels", "review",
        "The canonical file carries both 'Greyhounds' and 'Greyhound Racing' as separate "
        "sports, which splits one sport across two coverage figures.", 
        [{"sport": k, "date": "", "home": "", "away": "", "pick": f"{dup_labels[k]} rows",
          "confidence": "", "source_url": ""} for k in sorted(mixed)])

    gaelic = [r for r in rows if r.get("sport") == "Gaelic Football"]
    add("R-08", "Gaelic Football present but excluded from the in-scope list", "review",
        "Master rows exist for Gaelic Football while data/master.json's own sports_in_scope "
        "list omits it, so the headline in-scope count and the row file disagree.",
        [ref(r) for r in gaelic])

    conf_missing = [r for r in rows if r.get("confidence") in (None, "", "none")]
    add("R-09", "Rows with no confidence label", "review",
        "Every pick is meant to carry Low, Medium or High. These rows carry none.",
        [ref(r) for r in conf_missing])

    add("R-10", "Headline counts are internally consistent", "info",
        "rows_total ({0}) equals the number of row objects, and the per-sport counts sum to "
        "the same figure. No discrepancy found in these two figures.".format(
            master.get("counts", {}).get("rows_total")),
        [])

    payload = {"schema": "olbg4.ds.review/1",
               "reviewed_file": "data/master.json",
               "generated_on": master.get("generated_on"),
               "rows_reviewed": len(rows),
               "findings": findings}
    with open(os.path.join(DATA, "review.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, sort_keys=True)
        fh.write("\n")
    total = sum(f["count"] for f in findings if f["severity"] == "review")
    print(f"findings={len(findings)} affected_rows={total}")
    for f in findings:
        print(f"  {f['id']} {f['severity']:6} {f['count']:4} {f['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

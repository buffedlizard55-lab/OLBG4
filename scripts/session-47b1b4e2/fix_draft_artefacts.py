#!/usr/bin/env python3
"""Board K, finding K-F14 (NEW - not reported by Boards F, I or J):
unfinished draft text is published in Build D's data fields.

`data/matches.json` contains unresolved self-corrections of the form "X? Actually Y" in
fields that the site renders directly - including `teamB`, `pick`, `competition` and
`originatedSpread` - so the published dashboard shows strings like:

    competition      : "WTT Youth/Feeder Concurrent — Chengdu? Actually Chennai"
    originatedSpread : "Game Handicap: MS -? Actually badminton: -6.5 points handicap @ 1.91"
    teamB            : "Course: El Tigre? Actually Vidanta Vallarta — par 71, wide fairways"

Board J caught one instance of this in a prediction (EL02) but not the others, and not the
data fields. Separately, eight predictions on Low/Medium rows are not predictions at all but
working notes to the author ("Wait for Saturday's averages before committing outright",
"monitor net run-rate", "wait for upper bracket semis Oct 18-19 before pricing handicaps"),
several carrying statistics with no source at all.

Action taken, per the brief ("if a value can't be confirmed from an official source, leave it
blank and flag it as unverified - never infer or fill in values"):

  * a field containing an unresolved self-correction is BLANKED. The "Actually ..." answer is
    NOT adopted, because adopting it would be choosing between two values the author never
    reconciled and this session cannot confirm from a governing body. The original string is
    preserved on the row under k_unverified_values.
  * a prediction that is a working note rather than a selection is withdrawn and preserved
    under k_withdrawn.
  * a `pick` that says no selection was made is restated plainly as "No selection originated"
    with the original wording preserved, so the table no longer reads like a to-do list.
  * every affected row is flagged and appears on the Flagged for Review page.

Run: python3 scripts/session-47b1b4e2/fix_draft_artefacts.py   (after remediate.py)
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATCHES = os.path.join(ROOT, "data", "matches.json")
LOG = os.path.join(ROOT, "data", "session-47b1b4e2", "remediation.json")

SELF = re.compile(r"\?\s*Actually", re.I)
INSTR = re.compile(r"\bwait for\b|\bwait until\b|\bmonitor\b|check \w+ rules|before committing|"
                   r"before pricing|Verify tip|post-Bermuda|after weather forecast|until FedEx", re.I)
NO_PICK = re.compile(r"^\s*(no pick|no favourite|no outright pick|no match markets)", re.I)

# Fields the site renders verbatim. flagReason and the k_* audit fields are ours, so skip them.
SKIP = {"flagReason"}
NOW = "2026-10-21T08:30Z"
FINDING = "K-F14"
REASON_BASE = ("Board K finding %s: the published value contains unfinished draft text, so it cannot "
               "be relied on. " % FINDING)


def main():
    with open(MATCHES, encoding="utf-8") as f:
        rows = json.load(f)

    changes = []
    n_fields = n_preds = n_picks = 0

    for r in rows:
        rid = r["id"]
        touched = []

        for k, v in list(r.items()):
            if not isinstance(v, str) or k in SKIP or k.startswith("k_"):
                continue

            # ---- 1. unresolved self-correction in any rendered field
            if SELF.search(v):
                if k == "prediction":
                    r["k_withdrawn"] = {
                        "prediction": v, "confidence": r.get("confidence"),
                        "reason": (REASON_BASE + "It contains an unresolved self-correction "
                                   "('... after Boston? Actually Toronto rested; but ...'), so it was "
                                   "never a finished write-up. No replacement was invented."),
                        "withdrawn_utc": NOW, "finding": FINDING}
                    r["prediction"] = ""
                    n_preds += 1
                    touched.append(dict(field=k, before=v, after="", action="prediction withdrawn"))
                else:
                    r.setdefault("k_unverified_values", {})[k] = {
                        "value": v,
                        "removed_because": ("unresolved self-correction ('X? Actually Y') published in a "
                                            "rendered field; the two candidate values were never reconciled "
                                            "and neither is confirmable here from a governing body, so the "
                                            "field is blanked rather than guessed"),
                        "finding": FINDING}
                    r[k] = ""
                    n_fields += 1
                    touched.append(dict(field=k, before=v, after="", action="blanked (self-correction)"))
                continue

            # ---- 2. a working note published as a prediction
            if k == "prediction" and INSTR.search(v):
                r["k_withdrawn"] = {
                    "prediction": v, "confidence": r.get("confidence"),
                    "reason": (REASON_BASE + "This is a note to the author rather than a selection "
                               "(it tells the reader to wait for, or monitor, a future input before "
                               "committing), and several of its statistics carry no source. The brief "
                               "requires a prediction to state a clear betting selection, so it is "
                               "withdrawn rather than published."),
                    "withdrawn_utc": NOW, "finding": FINDING}
                r["prediction"] = ""
                n_preds += 1
                touched.append(dict(field=k, before=v, after="", action="prediction withdrawn (working note)"))
                continue

            # ---- 3. a pick/market cell that reads as a to-do
            if k in ("pick", "marketFocus") and INSTR.search(v) and NO_PICK.search(v):
                r.setdefault("k_unverified_values", {})[k] = {
                    "value": v,
                    "removed_because": ("phrased as a working note ('monitor ...', 'wait until ...'); "
                                        "restated plainly so the table does not read as a to-do list. "
                                        "The substance is unchanged: no selection was originated."),
                    "finding": FINDING}
                r[k] = ("No selection originated" if k == "pick"
                        else "No market originated")
                n_picks += 1
                touched.append(dict(field=k, before=v, after=r[k], action="restated as 'no selection'"))

        if touched:
            r["flagged"] = True
            note = (REASON_BASE + "%d field(s) affected: %s. Original values are preserved on this row "
                    "under k_unverified_values / k_withdrawn. Nothing was inferred or substituted with a "
                    "guessed value." % (len(touched), ", ".join(t["field"] for t in touched)))
            r["flagReason"] = (r.get("flagReason") + " | " + note) if r.get("flagReason") else note
            # A row whose rendered FIXTURE fields were blanked cannot claim to be verified. Withdrawing
            # only a prediction does not make the fixture itself unverified, so leave `verified` alone then.
            if any(t["action"].startswith("blanked") for t in touched):
                r["verified"] = False
            changes.append(dict(id=rid, finding=FINDING, sport=r.get("sport"),
                                match=r.get("match"), fields=touched))

    with open(MATCHES, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # append to the shared remediation log so the report page picks it up
    with open(LOG, encoding="utf-8") as f:
        log = json.load(f)
    if not any(c.get("finding") == FINDING for c in log["changes"]):
        log["findings_addressed"].append(FINDING)
        log["changes"].extend(
            dict(id=c["id"], finding=FINDING, action="draft text removed from published fields",
                 what_was_wrong="; ".join("%s: %r" % (t["field"], t["before"][:110]) for t in c["fields"]),
                 fields=[dict(field=t["field"], before=t["before"], after=t["after"]) for t in c["fields"]],
                 official_source="", prediction_withdrawn=any("prediction" in t["action"] for t in c["fields"]))
            for c in changes)
        log["summary"]["k_f14_rows"] = len(changes)
        log["summary"]["k_f14_fields_blanked"] = n_fields
        log["summary"]["k_f14_predictions_withdrawn"] = n_preds
        log["summary"]["k_f14_picks_restated"] = n_picks
        log["summary"]["flagged_rows"] = sum(1 for r in rows if r.get("flagged"))
        log["summary"]["verified_rows"] = sum(1 for r in rows if r.get("verified"))
        log["k_f14"] = {
            "title": "Unfinished draft text published in rendered data fields",
            "discovered_by": "arena/47b1b4e2-olbg4 (Board K) while writing the artefact check in check_all.py",
            "not_reported_by": "Boards F (07a080b9, 5fd34d30), G (ef72af9b), I (5e6c545d) and J (e1e0c27e)",
            "note": ("Board J caught one instance in a prediction (EL02). This pass found five more "
                     "self-corrections, including in fields the table renders directly, plus eight "
                     "predictions that are working notes rather than selections."),
            "rows": changes,
        }
        with open(LOG, "w", encoding="utf-8") as f:
            json.dump(log, f, indent=1, ensure_ascii=False)
            f.write("\n")
    else:
        print("K-F14 already recorded in the remediation log; data pass re-applied only")

    print("rows affected           :", len(changes))
    print("fields blanked          :", n_fields)
    print("predictions withdrawn   :", n_preds)
    print("picks restated          :", n_picks)
    for c in changes:
        print("  %-6s %-13s %s" % (c["id"], (c["sport"] or "")[:13],
                                   ", ".join(t["field"] for t in c["fields"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

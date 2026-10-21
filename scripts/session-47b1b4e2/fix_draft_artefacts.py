#!/usr/bin/env python3
"""Board R (session 47b1b4e2), finding R-F14 - unfinished draft text published in rendered fields.

Originally raised as "K-F14" while this session still held the letter K; three sessions
independently claimed Board K (`83451f65`, `5838b25d` and this one), so this board's record is
renamed R to disambiguate, following the precedent Board L set for the same collision.

THE DEFECT. `data/matches.json` publishes unresolved self-corrections of the form "X? Actually Y"
in fields the site renders directly, and working notes to the author in fields presented as picks:

    competition      "WTT Youth/Feeder Concurrent — Chengdu? Actually Chennai"
    originatedSpread "Game Handicap: MS -? Actually badminton: -6.5 points handicap @ 1.91"
    teamB            "Course: El Tigre? Actually Vidanta Vallarta — par 71, wide fairways"
    pick             "No pick yet — monitor entry lists (Alcaraz/Sinner expected in Basel/Vienna)"
    marketFocus      "No match markets until draw — monitor pools"

`assets/js/main.js` renders `competition`, `pick`, `originatedSpread` and `marketFocus` on the hub
category pages, and `tools/build_master.py` reads `pick`, `competition`, `teamB` and
`originatedSpread` into the consolidated board at `/board/`, so the artefacts are live in both places.
Boards F, G, I, J, K(83451f65), L, M, N, P and Q all audited or re-verified this dataset without
reporting it; Board J caught one instance, in EL02's prediction text only.

ACTION, per the brief ("if a value can't be confirmed from an official source, leave it blank and
flag it as unverified - never infer or fill in values"):

  * a field containing an unresolved self-correction is BLANKED. The "Actually ..." answer is NOT
    adopted: choosing between two values the author never reconciled, with no governing-body page
    behind either, would be inference.
  * a `pick`/`marketFocus` cell that says no selection was made is restated plainly as
    "No selection originated", so the table stops reading like a to-do list. The substance is
    unchanged - no selection was made either way.
  * every affected row is flagged, and the original string is preserved on the row under
    `r_f14_removed` so nothing is lost and the change is auditable.
  * fields another board deliberately blanked during its own verification cycle are left alone.

This script is schema-agnostic and idempotent: it adds only the `r_f14_removed` key, appends to
`flagReason`, and sets `flagged`. It never touches `verification`, `priorSourceUrl`, `verified` or
`confidence`, which are owned by the board that wrote them.

Run: python3 scripts/session-47b1b4e2/fix_draft_artefacts.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATCHES = os.path.join(ROOT, "data", "matches.json")
OUT = os.path.join(ROOT, "data", "session-47b1b4e2", "draft_artefacts.json")

# An unresolved self-correction: the author wrote a value, doubted it, wrote another, and published both.
SELF = re.compile(r"\?\s*Actually", re.I)
# An instruction to the author, or a deferral, published where a value belongs.
INSTR = re.compile(r"\bwait for\b|\bwait until\b|\bmonitor\b|check \w+ rules|before committing|"
                   r"before pricing|Verify tip|post-Bermuda|after weather forecast|until FedEx", re.I)
NO_PICK = re.compile(r"^\s*(no pick|no favourite|no outright pick|no match markets)", re.I)

# Keys this board owns, plus audit keys written by other boards - never rewrite those.
SKIP = {"flagReason", "verification", "priorSourceUrl", "priorSourceName", "facts", "r_f14_removed"}
NOW = "2026-10-21T09:40Z"
FINDING = "R-F14"


def main():
    with open(MATCHES, encoding="utf-8") as f:
        rows = json.load(f)

    changes = []
    n_blank = n_restate = 0

    for r in rows:
        if not isinstance(r, dict):
            continue
        removed = dict(r.get("r_f14_removed") or {})
        touched = []

        for k, v in list(r.items()):
            if k in SKIP or k.startswith(("k_", "r_f14")) or not isinstance(v, str) or not v.strip():
                continue

            if SELF.search(v):
                removed[k] = {"value": v,
                              "why": ("unresolved self-correction ('X? Actually Y') published in a rendered "
                                      "field. Neither candidate value is confirmable here from a governing "
                                      "body, so the field is blanked rather than guessed - the brief forbids "
                                      "inferring values."),
                              "finding": FINDING}
                r[k] = ""
                n_blank += 1
                touched.append((k, "blanked"))
            elif k in ("pick", "marketFocus") and INSTR.search(v) and NO_PICK.search(v):
                removed[k] = {"value": v,
                              "why": ("phrased as a working note ('monitor ...', 'wait until ...'). Restated "
                                      "plainly; the substance is unchanged - no selection was originated."),
                              "finding": FINDING}
                r[k] = "No selection originated" if k == "pick" else "No market originated"
                n_restate += 1
                touched.append((k, "restated"))

        if touched:
            r["r_f14_removed"] = removed
            r["flagged"] = True
            note = ("Board R finding %s: unfinished draft text was published in %s. The original strings are "
                    "preserved on this row under r_f14_removed. Nothing was inferred or substituted with a "
                    "guessed value." % (FINDING, ", ".join("%s (%s)" % t for t in touched)))
            r["flagReason"] = (r.get("flagReason") + " | " + note) if r.get("flagReason") else note
            changes.append(dict(id=r.get("id"), sport=r.get("sport"), fields=touched,
                                originals={k: v["value"] for k, v in removed.items()}))

    with open(MATCHES, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)
        f.write("\n")

    # Derive the log from the rows themselves, not from this run's delta, so re-running is idempotent
    # and the committed record always describes the whole remediation rather than the last invocation.
    all_changes = []
    for r in rows:
        rem = r.get("r_f14_removed") if isinstance(r, dict) else None
        if not rem:
            continue
        all_changes.append(dict(
            id=r.get("id"), sport=r.get("sport"),
            fields=[(k, "restated" if r.get(k) in ("No selection originated", "No market originated")
                     else "blanked") for k in rem],
            originals={k: v["value"] for k, v in rem.items()},
            reasons={k: v["why"] for k, v in rem.items()}))
    n_all_restate = sum(1 for c in all_changes for k, a in c["fields"] if a == "restated")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"schema": "olbg4.boardr-draft-artefacts/1", "finding": FINDING, "run_utc": NOW,
                   "dataset": "data/matches.json", "rows_in_dataset": len(rows),
                   "rows_affected": len(all_changes),
                   "fields_blanked": sum(len(c["fields"]) for c in all_changes) - n_all_restate,
                   "fields_restated": n_all_restate,
                   "changed_this_run": len(changes), "changes": all_changes}, f, indent=1, ensure_ascii=False)
        f.write("\n")

    print("rows in dataset      :", len(rows))
    print("rows affected (total):", len(all_changes), "| changed this run:", len(changes))
    for c in all_changes:
        print("  %-7s %-13s %s" % (c["id"], (c["sport"] or "")[:13],
                                   ", ".join("%s(%s)" % t for t in c["fields"])))
    print("wrote", os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main())

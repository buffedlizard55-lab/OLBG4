#!/usr/bin/env python3
"""Board K repair of the root hub data (data/matches.json).

Idempotent. Only touches rows whose published claims were contradicted by an official
page fetched on 2026-10-21. Nothing is deleted; the original pick and the reason stay
visible, the unsupported write-up is withdrawn and the row is downgraded.
"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(ROOT, "data", "matches.json")

REPAIRS = {
    "NBA02": {
        "flag": "Withdrawn prediction (Board K K-02): the write-up's roster claim is not supported by the "
                "official game page. NBA.com 2026-10-20: Philadelphia 106-100 New York, Tyrese Maxey 28 points.",
        "src": "https://www.nba.com/games?date=2026-10-20",
    },
    "NHL01": {
        "flag": "Withdrawn prediction (Board K K-03): the write-up says San Jose were 0-4; the NHL score payload "
                "shows San Jose winning 4-3 in overtime at Montreal on 2026-10-20 and sitting 5-4-1 on 22 Oct.",
        "src": "https://api-web.nhle.com/v1/score/2026-10-20",
    },
    "NHL06": {
        "flag": "Withdrawn prediction (Board K K-04): the write-up says Boston were 1-3 and without Marchand; the "
                "NHL score payload lists Boston at 7-2-1 with Jeremy Swayman on six wins.",
        "src": "https://api-web.nhle.com/v1/score/2026-10-22",
    },
    "EL02": {
        "flag": "Withdrawn prediction (Board K K-05): the text contains two different scores for the same game and "
                "an unedited drafting fragment ('Actually'), and its only source is a Wikipedia page.",
        "src": "https://www.olbg.com/",
    },
    "MLB01": {
        "flag": "Withdrawn prediction (Board K K-06): venue, date and both records are confirmed (MIL 103-59, TB "
                "98-64, Game 1 on 23 Oct at American Family Field), but the 'seven-game ALCS', the 52-29 home "
                "record and the bullpen ERAs appear on no official page read today.",
        "src": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-21&endDate=2026-10-27",
    },
}

rows = json.load(open(PATH))
changed = []
for r in rows:
    rep = REPAIRS.get(r.get("id"))
    if not rep:
        continue
    before = (r.get("prediction"), r.get("verified"), r.get("flagged"), r.get("confidence"))
    r["verified"] = False
    r["flagged"] = True
    r["flagReason"] = rep["flag"] + " Evidence: " + rep["src"]
    if r.get("prediction"):
        r["predictionWithdrawn"] = r["prediction"]
    r["prediction"] = ""
    r["confidenceOriginal"] = r.get("confidence")
    r["confidence"] = "Low"
    r["status"] = "Needs review"
    r["repairedBy"] = "Board K / session 6b8d2d5f / 2026-10-21"
    after = (r.get("prediction"), r.get("verified"), r.get("flagged"), r.get("confidence"))
    if before != after:
        changed.append(r["id"])

if changed:
    json.dump(rows, open(PATH, "w"), indent=1, ensure_ascii=False)
print("repaired:", changed or "already applied")
print("verified rows:", sum(1 for r in rows if r.get("verified")),
      "| flagged rows:", sum(1 for r in rows if r.get("flagged")))

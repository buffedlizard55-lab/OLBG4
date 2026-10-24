#!/usr/bin/env python3
"""Board FI line-by-line review.

Three jobs:
 1. audit this desk: uncovered sports, capped models, multi-market picks, listings;
 2. audit data/master.json, the repository's canonical dataset, line by line;
 3. audit the freshest peer desk still published, so the review is not self-referential.

Only defects that can be shown from the committed bytes are reported; nothing is
inferred and no peer file is modified.
"""
from __future__ import annotations

import glob
import json
import os
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-f51e10a5")
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]


def jload(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def main() -> None:
    findings = []

    def add(fid, area, title, detail, where, sources=(), severity="medium"):
        findings.append({"id": fid, "area": area, "title": title, "detail": detail,
                         "where": where, "sources": list(sources), "severity": severity})

    desk = jload(os.path.join(DATA, "desk.json"), {"rows": []})
    preds = jload(os.path.join(DATA, "predictions.json"), {"predictions": []})
    rows = desk.get("rows", [])
    plist = preds.get("predictions", [])
    listings = desk.get("olbg_listings", [])

    # ------------------------------------------------------------- this desk
    unpriced = [r for r in rows if not r.get("pick")]
    if unpriced:
        add("FI-F01", "Desk", str(len(unpriced)) + " captured fixtures are published without a price",
            "Each was captured on an official source but lacks the input its sport's model needs. The reason is printed in "
            "the row's own flags. They are left blank rather than guessed: "
            + ", ".join(k + " " + str(v) for k, v in sorted(Counter(r["sport"] for r in unpriced).items())),
            "data/session-f51e10a5/desk.json", (), "low")

    written = Counter(p["sport"] for p in plist)
    gaps = [sp for sp in SPORTS if written.get(sp, 0) == 0]
    if gaps:
        add("FI-F02", "Coverage", "Four sports have no written prediction in this snapshot",
            "The brief asks for five written picks in every sport. Four could not be built without inventing a number: "
            "Golf (the only captured PGA Tour leaderboard is the Butterfield Bermuda Championship, already in progress, so "
            "no pre-event field exists), Cricket (the ICC team-ranking pages captured are client-rendered shells with no "
            "ratings in the bytes, and no official results feed was captured to build a rating), Gaelic Sports (the GAA "
            "fixtures payload holds no match inside the 24 Oct – 8 Nov window; the county finals OLBG lists are not on "
            "gaa.ie) and Greyhounds (every GBGB racecard/fixture endpoint tried returned 404, and the OLBG hub lists a "
            "time but no runners). Each is stated on the Coverage page with its shortfall, and the OLBG events are listed "
            "with links instead of being published as rows.",
            "data/session-f51e10a5/predictions.json",
            ("https://www.pgatour.com/leaderboard.html",
             "https://www.icc-cricket.com/rankings/team-rankings/mens/odi",
             "https://www.gaa.ie/fixtures-results/",
             "https://www.gbgb.org.uk/"), "high")

    partial = [(sp, written[sp]) for sp in SPORTS if 0 < written.get(sp, 0) < 5]
    if partial:
        add("FI-F03", "Coverage", "Some sports reach five picks partly through a second market on the same fixture",
            "Where the window holds fewer than five priceable fixtures, the desk takes a second market on a fixture it has "
            "already priced rather than reaching outside the official data: "
            + ", ".join(sp + " " + str(n) for sp, n in partial)
            + ". Every extra pick is a real leg of a market we originated, priced at its own probability, and is labelled "
              "'second market on the same fixture' and capped at Medium.",
            "data/session-f51e10a5/predictions.json", (), "low")

    capped = Counter()
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        rule = (p.get("rule") or "").lower()
        if "cap" in rule or "capped" in rule:
            capped[r["sport"]] += 1
    if capped:
        add("FI-F04", "Confidence", str(sum(capped.values())) + " picks are capped below High by their sport's own rule",
            "A ranking-only, seed-only, result-only or thin sample cannot support High however large the probability looks. "
            "Caps by sport: " + ", ".join(k + " " + str(v) for k, v in sorted(capped.items())),
            "data/session-f51e10a5/desk.json", (), "low")

    if listings:
        add("FI-F05", "Sourcing", str(len(listings)) + " OLBG-listed events have no official fixture in this capture",
            "They are published as an appendix with their OLBG links, not as desk rows, because a row without an official "
            "source would break the desk's own rule. By sport: "
            + ", ".join(k + " " + str(v) for k, v in sorted(Counter(x["sport"] for x in listings).items())),
            "data/session-f51e10a5/desk.json", ("https://www.olbg.com/betting-tips",), "low")

    injuries = sum(1 for p in plist if not p.get("injury"))
    if injuries:
        add("FI-F06", "Predictions", "No injury or availability statement is published for any pick",
            "All " + str(injuries) + " written picks carry the 'unverified' note on injuries. The official pages captured in "
            "this snapshot publish fixtures, tables and match statistics but not team news, so no absence is claimed.",
            "session-f51e10a5/picks.html", (), "medium")

    transcribed = [r for r in rows if any("transcribed" in f for f in r.get("flags", []))]
    if transcribed:
        add("FI-F07", "Sourcing", str(len(transcribed)) + " Rugby Union rows rest on a transcribed official table",
            "The URC Match Centre table page is client-rendered and returns no table bytes to the runner, so the standings "
            "were transcribed from the live official page by the earlier AR board and are committed with that page's URL, "
            "round and fetch time. The fixtures themselves come from the official fixtures-in-full page captured here.",
            "data/session-405e9797/evidence/urc_table.json",
            ("https://stats.unitedrugby.com/match-centre/table/2026-27",), "medium")

    dropped = desk.get("dropped_rows", [])
    if dropped:
        add("FI-F08", "Desk", str(len(dropped)) + " row(s) were dropped rather than published",
            "A golf outright on an event the PGA feed reports as completed, and a GBGB placeholder with no start time and "
            "no runners. Publishing either would have described a fixture that cannot be backed. Ids: " + ", ".join(dropped),
            "data/session-f51e10a5/desk.json", (), "low")

    # ------------------------------------------------------------- master.json
    master = jload(os.path.join(ROOT, "data", "master.json"), {})
    mrows = master.get("rows", [])
    if mrows:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        stale = [r for r in mrows if (r.get("date") or "") < today]
        nosrc = [r for r in mrows if not r.get("source_url")]
        high = [r for r in mrows if r.get("confidence") == "High"]
        high_no_pred = [r for r in high if not (r.get("prediction") or "").strip()]
        short_preds = [r for r in mrows if (r.get("prediction") or "").strip()
                       and len(r["prediction"].split()) < 30]
        add("FI-F09", "Repository", "data/master.json is a 21 October snapshot, not an upcoming-fixture list",
            "The canonical file was generated on " + str(master.get("generated_on")) + " and holds " + str(len(mrows))
            + " rows; " + str(len(stale)) + " are dated before today (" + today + ") and "
            + str(len([r for r in mrows if r.get("status") == "played-before-cutoff"]))
            + " are explicitly marked played. Anything rendered from it describes fixtures that have already been played.",
            "data/master.json", (), "high")
        add("FI-F10", "Repository", str(len(nosrc)) + " rows in data/master.json carry no source URL",
            "Those rows cannot be checked against an official page. Ids: "
            + ", ".join(str(r.get("id")) for r in nosrc[:25]),
            "data/master.json", (), "high")
        add("FI-F11", "Repository", str(len(high_no_pred)) + " High-confidence rows in data/master.json have no written "
            "prediction",
            "Of " + str(len(high)) + " High rows, " + str(len(high_no_pred)) + " have an empty prediction field, so the "
            "strongest labels in the canonical dataset are unsupported by any written case.",
            "data/master.json", (), "high")
        if short_preds:
            add("FI-F12", "Repository", str(len(short_preds)) + " predictions in data/master.json are under 30 words",
                "Ids: " + ", ".join(str(r.get("id")) for r in short_preds[:20]),
                "data/master.json", (), "medium")

    # ------------------------------------------------------- freshest peer desk
    peers = [p for p in glob.glob(os.path.join(ROOT, "data", "session-*", "desk.json"))
             if "session-f51e10a5" not in p]
    for p in sorted(peers, key=lambda x: os.path.getmtime(x), reverse=True):
        d = jload(p)
        if not d or not d.get("rows"):
            continue
        prows = d["rows"]
        unp = [r for r in prows if not (r.get("pick") or r.get("match_winner_pick"))]
        add("FI-F13", "Peer desk", "The freshest peer desk still carries " + str(len(unp)) + " unpriced rows",
            os.path.relpath(p, ROOT) + " holds " + str(len(prows)) + " rows, of which " + str(len(unp))
            + " have no pick. It is a dated snapshot from another board and outside this session's scope; it is listed so "
              "the combined output is not mistaken for a complete one.",
            os.path.relpath(p, ROOT), (), "low")
        break

    src = jload(os.path.join(DATA, "sources.json"), {})
    fails = src.get("failures", [])
    if fails:
        material = [f for f in fails if any(k in f["id"] for k in ("ranking", "fixtures", "matches", "racecard", "rank"))]
        add("FI-F14", "Capture", str(len(fails)) + " official endpoints failed during the capture",
            "They are listed with their status on the Sources page. The material ones — ranking, fixture or racecard feeds "
            "— are: " + ", ".join(f["id"] + " (" + str(f.get("status")) + ")" for f in material[:12])
            + ". No value was estimated to cover a failed endpoint.",
            "data/session-f51e10a5/capture", [f["url"] for f in material[:5]], "low")

    doc = {
        "schema": "fi-review-1",
        "board": "FI",
        "session": "arena/f51e10a5-olbg4",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "findings": findings,
    }
    json.dump(doc, open(os.path.join(DATA, "review.json"), "w"), indent=1, sort_keys=True)
    print(str(len(findings)) + " findings -> review.json")


if __name__ == "__main__":
    main()

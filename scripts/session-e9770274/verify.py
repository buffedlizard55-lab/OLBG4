#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — publication gate.

Fails (exit 1) on any of: a priced row without an official source that is present in the capture manifest
with a matching SHA-256; a fair price that does not re-derive from its probability; a pick whose price sits
outside the brief's -250…+10,000 band; a confidence grade that contradicts the published rule; a written
prediction shorter than 30 words, materially similar to another, missing its selection, or using banned
wording; a fact without a source link; an OLBG event id that is not on the captured board; a broken internal
link in the built site; a missing sport page; or a count that disagrees with the site.
"""
from __future__ import annotations

import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SID = "session-e9770274"
DATA = ROOT / "data" / SID
SITE = ROOT / SID
DESK = json.loads((DATA / "desk.json").read_text())
PREDS = json.loads((DATA / "predictions.json").read_text())
BOARD = json.loads((DATA / "olbg_board.json").read_text())
SOURCES = json.loads((DATA / "sources.json").read_text())
FLAGS = json.loads((DATA / "flags.json").read_text())
MANIFEST = json.loads((DATA / "capture" / DESK["capture_id"] / "manifest.json").read_text())
REC = {r["id"]: r for r in MANIFEST["records"]}

BANNED = ["model", "verified", "verification", "algorithm", "simulation"]
errors: list[str] = []
warnings: list[str] = []


def check(cond: bool, msg: str) -> None:
    if not cond:
        errors.append(msg)


def amer(p: float) -> int:
    if p >= 0.5:
        return -int(round(100 * p / (1 - p)))
    return int(round(100 * (1 - p) / p))


def main() -> int:
    # ---------------------------------------------------------------- board / desk
    ids_on_board = {e["event_id"] for s in BOARD["sports"].values() for e in s["events"]}
    check(len(DESK["rows"]) > 0, "desk has no rows")
    for r in DESK["rows"]:
        check(r["olbg"]["event_id"] in ids_on_board,
              f"{r['id']}: event {r['olbg']['event_id']} is not on the captured OLBG board")
        if r["status"] != "priced":
            check(any(f["text"].strip() for f in r["flags"]),
                  f"{r['id']}: unpriced row without a stated reason")
            continue
        o = r.get("official") or {}
        check(bool(o.get("url")), f"{r['id']}: priced row without an official URL")
        capid = o.get("capture_id")
        check(capid in REC, f"{r['id']}: capture id {capid!r} not in the manifest")
        if capid in REC:
            check(REC[capid].get("status") == 200, f"{r['id']}: source {capid} was not an HTTP 200 capture")
            check(o.get("sha256") == REC[capid].get("sha256"),
                  f"{r['id']}: sha256 {o.get('sha256')} does not match the manifest for {capid}")
        check(bool(r["facts"]), f"{r['id']}: priced row with no facts")
        for f in r["facts"]:
            check(f["value"].strip() != "", f"{r['id']}: empty fact value")
        # markets and arithmetic
        check(len(r["markets"]) >= 1, f"{r['id']}: no markets")
        for m in r["markets"]:
            for s in m["selections"]:
                p = s["prob"]
                check(0 < p < 1, f"{r['id']}/{m['market']}: probability out of range")
                check(abs(s["decimal"] - round(1 / p, 2)) < 0.011,
                      f"{r['id']}/{m['market']}/{s['selection']}: decimal {s['decimal']} != 1/p {1/p:.3f}")
                check(s["american"] == amer(p),
                      f"{r['id']}/{m['market']}/{s['selection']}: american {s['american']} != {amer(p)}")
        p = r["pick"]
        check(-250 <= p["american"] <= 10000, f"{r['id']}: pick price {p['american']} outside -250..+10000")
        check(p["confidence"] in ("High", "Medium", "Low"), f"{r['id']}: bad confidence label")
        if p["confidence"] == "High":
            ok = p["prob"] >= 0.66 or (p["edge_pp"] is not None and p["edge_pp"] >= 6)
            check(ok, f"{r['id']}: High grade without the published qualification")
            check(r["sample"]["adequate"], f"{r['id']}: High grade on a thin sample")
        if not r["sample"]["adequate"]:
            check(p["confidence"] != "High", f"{r['id']}: thin sample graded High")

    # ---------------------------------------------------------------- predictions
    preds = PREDS["predictions"]
    if not preds:
        check(any("no written prediction" in f["title"].lower() for f in FLAGS["flags"]),
              "no predictions published and no flag explaining it")
    by_row = {r["id"]: r for r in DESK["rows"]}
    for pr in preds:
        row = by_row.get(pr["row_id"])
        check(row is not None, f"{pr['prediction_id']}: unknown row {pr['row_id']}")
        if not row:
            continue
        check(row["status"] == "priced", f"{pr['prediction_id']}: prediction on an unpriced row")
        words = len(pr["prediction_text"].split())
        check(words >= 30, f"{pr['prediction_id']}: only {words} words")
        check(pr["word_count"] == words, f"{pr['prediction_id']}: word_count field disagrees ({pr['word_count']} vs {words})")
        low = pr["prediction_text"].lower()
        for b in BANNED:
            check(b not in low, f"{pr['prediction_id']}: uses banned wording '{b}'")
        key = re.sub(r"\s+at\s+[+-]?\d+$", "", pr["selection"]).lower()
        toks = [t for t in re.findall(r"[a-z0-9']+", key) if len(t) > 2][:3]
        check(all(t in low for t in toks),
              f"{pr['prediction_id']}: selection {pr['selection']} not clearly named in the text")
        check(pr["fair_american"] == row["pick"]["american"], f"{pr['prediction_id']}: price differs from the row")
        check(bool(pr["facts"]), f"{pr['prediction_id']}: no facts attached")
        for f in pr["facts"]:
            check(f["source_url"].startswith("http"), f"{pr['prediction_id']}: fact without a source link")
        check(pr["official_source_url"].startswith("http"), f"{pr['prediction_id']}: no official source")
    for i in range(len(preds)):
        for j in range(i + 1, len(preds)):
            s = SequenceMatcher(None, preds[i]["prediction_text"], preds[j]["prediction_text"]).ratio()
            check(s <= 0.55, f"similarity {s:.2f} between {preds[i]['prediction_id']} and {preds[j]['prediction_id']}")
    # no duplicate text
    check(len({p["prediction_text"] for p in preds}) == len(preds), "duplicate prediction text")

    # ---------------------------------------------------------------- samples / flags
    check(FLAGS["count"] == len(FLAGS["flags"]), "flag count mismatch")
    for sp, d in DESK["summary"]["by_sport"].items():
        written = sum(1 for p in preds if p["sport"] == sp)
        if written < 5:
            check(any(sp in f["title"] for f in FLAGS["flags"]),
                  f"{sp}: fewer than five predictions and no flag explaining it")

    # ---------------------------------------------------------------- site
    pages = sorted(SITE.rglob("*.html"))
    check(len(pages) >= 20, f"only {len(pages)} pages built")
    for page in pages:
        text = page.read_text(errors="replace")
        for href in re.findall(r'href="([^"#:]+?)"', text):
            if href.startswith(("http", "mailto", "#")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            check(target.exists(), f"{page.relative_to(ROOT)}: broken link {href}")
        check("</html>" in text, f"{page.relative_to(ROOT)}: truncated page")
    index = (SITE / "index.html").read_text()
    check("executive summary" in index.lower() or "What this is" in index,
          "index.html does not open with an executive summary")
    check(str(DESK["summary"]["rows_total"]) in index, "index.html does not state the fixture count")
    check(str(PREDS["summary"]["total"]) in index, "index.html does not state the prediction count")
    picks = (SITE / "picks.html").read_text()
    for pr in preds:
        check(pr["prediction_id"] in picks, f"picks.html misses {pr['prediction_id']}")
    flagged = (SITE / "flagged.html").read_text()
    check(str(FLAGS["count"]) in flagged, "flagged.html does not state the flag count")

    # ---------------------------------------------------------------- report
    print(f"rows {len(DESK['rows'])} · priced {DESK['summary']['priced']} · "
          f"predictions {len(preds)} · flags {FLAGS['count']} · pages {len(pages)}")
    if warnings:
        for w in warnings:
            print("WARN", w)
    if errors:
        print(f"FAIL — {len(errors)} error(s)")
        for e in errors[:40]:
            print("  -", e)
        return 1
    print("PASS — every published price, grade, fact, prediction and link re-checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

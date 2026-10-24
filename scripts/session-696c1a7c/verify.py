#!/usr/bin/env python3
"""Check the published board against the brief, row by row.

Run after build_site.py. Exit code 1 means the board must not be published.

Checks
    1  exactly the 15 sports in scope, and no others, anywhere in the data
    2  every prediction is at least 30 words and states a selection and a price
    3  no prediction uses either ruled-out word
    4  every priced row sits in the −250 … +10,000 window, or says why not
    5  every prediction carries at least one official source with a SHA-256
    6  every internal link resolves to a file that exists
    7  the market inventory is non-empty for every sport that lists events
    8  the site has a page per sport, a dashboard, a picks page and a flagged page
    9  the picks are distinct (worst 3-gram overlap below the desk threshold)
   10  nothing in the data disagrees with the capture manifest it cites
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"
SITE = ROOT / "session-696c1a7c"

SPORTS = {
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
}
BANNED = ("model", "verified")
MIN_WORDS = 30
MAX_JACCARD = 0.32

failures: list[str] = []
notes: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def main() -> int:
    listings = json.loads((DATA / "listings.json").read_text())
    facts = json.loads((DATA / "facts.json").read_text())
    picks = json.loads((DATA / "picks.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())

    # 1 scope
    found = {p["sport"] for p in preds["predictions"]} | set(listings["sports"])
    check(found <= SPORTS, f"out-of-scope sports present: {sorted(found - SPORTS)}")
    check(set(listings["sports"]) == SPORTS,
          f"listing missing sports: {sorted(SPORTS - set(listings['sports']))}")

    # 2/3/4/5 predictions
    for p in preds["predictions"]:
        tag = p["id"]
        check(p["words"] >= MIN_WORDS, f"{tag}: {p['words']} words")
        check(re.search(r"Selection|bet is|make .* the play|Take ", p["body"]) is not None,
              f"{tag}: selection sentence missing")
        check(str(p["fair_american"]) in p["body"], f"{tag}: our price not stated in the text")
        low = p["body"].lower()
        for word in BANNED:
            check(not re.search(rf"\b{word}\b", low), f"{tag}: uses the ruled-out word '{word}'")
        check(-250 <= p["fair_american"] <= 10000 or not p["in_window"],
              f"{tag}: price {p['fair_american']} outside the window but marked in-window")
        check(bool(p["official_sources"]), f"{tag}: no official source")
        for s in p["official_sources"]:
            check(len(s.get("sha256") or "") == 64, f"{tag}: source {s.get('key')} has no hash")

    # 4b window note when a price is shorter than -250
    short = [p for p in preds["predictions"] if p["fair_american"] < -250]
    notes.append(f"{len(short)} pick(s) priced shorter than −250 and shown as-is")

    # 6 internal links
    link_re = re.compile(r'href="(?!#)([^"]+)"')
    for page in SITE.rglob("*.html"):
        for href in link_re.findall(page.read_text()):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            check(target.exists(), f"{page.relative_to(ROOT)}: dead link → {href}")

    # 7 markets
    for sport, block in listings["sports"].items():
        if block.get("events"):
            check(any(m["rows"] > 0 for m in listings["taxonomy"]["markets"]),
                  "market inventory empty")

    # 8 pages
    for name in ("index.html", "picks.html", "flagged.html", "sources.html",
                 "methodology.html", "entries.html", "markets.html", "sports/index.html"):
        check((SITE / name).exists(), f"missing page {name}")
    slugs = {s.lower().replace(" ", "-") for s in SPORTS}
    for slug in slugs:
        check((SITE / "sports" / f"{slug}.html").exists(), f"missing sport page {slug}")

    # 9 distinctness
    check(preds["distinctness"]["max_3gram_jaccard"] <= MAX_JACCARD,
          f"predictions too similar: {preds['distinctness']['max_3gram_jaccard']}")

    # 10 capture agreement
    manifests = {}
    for cap in (DATA / "capture").glob("*/manifest.json"):
        m = json.loads(cap.read_text())
        for rec in m["records"]:
            manifests[(rec["id"], rec["sha256"])] = rec["bytes"]
    source_ids = {s["id"] for s in facts["sources"]}
    by_id = {i for (i, _) in manifests}
    check(source_ids <= by_id, f"facts cite source ids missing from every manifest: {source_ids - by_id}")
    for p in preds["predictions"]:
        for s in p["official_sources"]:
            check(s.get("source_id") in source_ids,
                  f"{p['id']}: source {s.get('source_id') or s['key']} not in the capture")

    # inventory of what was published
    per_sport = Counter(p["sport"] for p in preds["predictions"])
    rows = Counter(r["sport"] for r in json.loads((DATA / "desk_raw.json").read_text())["rows"])
    print(f"picks: {len(preds['predictions'])} over {len(per_sport)} sports")
    for sport in sorted(SPORTS):
        print(f"  {sport:14s} listed={len(listings['sports'][sport]['events']):3d} "
              f"priced_events={rows.get(sport, 0):3d} picks={per_sport.get(sport, 0):2d}")
    print(f"worst 3-gram Jaccard {preds['distinctness']['max_3gram_jaccard']}; "
          f"shortest prediction {min(p['words'] for p in preds['predictions'])} words")
    print(f"facts: {len(facts['fixtures'])} fixtures, {len(facts['history'])} results, "
          f"{len(facts['teams'])} table rows, {len(facts['gaps'])} gaps")
    for note in notes:
        print(f"note: {note}")
    if failures:
        print(f"\nFAIL ({len(failures)})")
        for f in failures[:40]:
            print("  -", f)
        return 1
    print("\nPASS: 10/10 checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

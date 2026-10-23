#!/usr/bin/env python3
"""Board AR publication gate.

Runs before the site is committed and again in CI. Any failure exits non-zero so a broken
board can never be merged.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-405e9797"
SITE = ROOT / "session-405e9797"
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}
BANNED = ("model", "verified", "verify")


def words(t: str) -> int:
    return len([w for w in re.split(r"\s+", t.strip()) if w])


def main() -> int:
    errs, warns = [], []
    desk = json.loads((DATA / "desk.json").read_text())
    flg = json.loads((DATA / "flagged.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    rows = desk["rows"]

    # 1. every sport in scope is represented in the counts
    for s in SPORTS:
        if s not in desk["counts"]["by_sport"]:
            errs.append(f"sport missing from counts: {s}")

    # 2. priced rows must carry a pick and an https official source
    for r in rows:
        if r.get("priced"):
            if not r.get("pick"):
                errs.append(f"{r['id']}: priced row without a pick")
            u = r.get("official_url", "")
            if urlparse(u).scheme not in ("http", "https"):
                errs.append(f"{r['id']}: priced row without an official URL")
            if not r.get("inputs_summary"):
                errs.append(f"{r['id']}: priced row without inputs")
        else:
            if r.get("pick"):
                errs.append(f"{r['id']}: unpriced row carries a pick")
            if not r.get("listing_only"):
                warns.append(f"{r['id']}: unpriced and not marked listing-only")

    # 3. listing-only rows must point back to the OLBG listing
    for r in rows:
        if r.get("listing_only") and not (r.get("olbg") or {}).get("event_url"):
            warns.append(f"{r['id']}: listing row without an OLBG link")

    # 4. High picks need a compliant note
    notes = preds["notes"]
    highs = [r for r in rows if (r.get("pick") or {}).get("confidence") == "High"]
    for r in highs:
        if not r["pick"].get("in_window"):
            continue
        n = notes.get(r["id"])
        if not n:
            errs.append(f"{r['id']}: High pick without a prediction")
            continue
        if words(n["text"]) < 30:
            errs.append(f"{r['id']}: prediction shorter than 30 words ({words(n['text'])})")
        low = n["text"].lower()
        for w in BANNED:
            if w in low:
                errs.append(f"{r['id']}: prediction contains '{w}'")
        if r["pick"]["selection"].split()[0].lower() not in low:
            errs.append(f"{r['id']}: prediction does not name the selection")
        if urlparse(n.get("source_url", "")).scheme not in ("http", "https"):
            errs.append(f"{r['id']}: prediction without a source URL")
    if preds.get("problems"):
        errs.append(f"prediction bank reports problems: {preds['problems']}")

    texts = [n["text"] for n in notes.values()]
    if len(set(texts)) != len(texts):
        errs.append("duplicate prediction text")

    # 5. duplicates
    seen = {}
    for r in rows:
        key = (r["sport"], r["matchup"], (r.get("start_utc") or "")[:10])
        if key in seen:
            errs.append(f"duplicate row {key}")
        seen[key] = r["id"]

    # 6. flags: each row flag id must exist in the register
    ids = {f["id"] for f in flg["flags"]}
    for r in rows:
        for fid in r.get("flags", []):
            if fid not in ids:
                errs.append(f"{r['id']}: row flag {fid} missing from the register")

    # 7. site files and links
    need = ["index.html", "coverage.html", "picks.html", "flagged.html", "review.html",
            "methodology.html", "data.json", "assets/site.css"]
    for f in need:
        if not (SITE / f).exists():
            errs.append(f"site file missing: {f}")
    for s in SPORTS:
        p = SITE / "sports" / f"{SLUG[s]}.html"
        if not p.exists():
            errs.append(f"sport page missing: {p.name}")
            continue
        body = p.read_text()
        for href in re.findall(r'href="([^"#:]+\.html)"', body):
            target = (p.parent / href).resolve()
            if not target.exists():
                errs.append(f"{p.name}: broken link {href}")

    # 8. published notes must be present inside the sport pages
    for s in SPORTS:
        p = SITE / "sports" / f"{SLUG[s]}.html"
        if not p.exists():
            continue
        body = p.read_text()
        for r in rows:
            if r["sport"] != s or r["id"] not in notes:
                continue
            if (r.get("pick") or {}).get("confidence") != "High":
                continue
            if notes[r["id"]]["text"][:60] not in body:
                errs.append(f"{p.name}: High note for {r['id']} not published")

    print(json.dumps({
        "rows": len(rows), "priced": desk["counts"]["priced"], "high": len(highs),
        "notes": len(notes), "flags": len(flg["flags"]),
        "errors": errs, "warnings": warns,
    }, indent=1))
    return 0 if not errs else 1


if __name__ == "__main__":
    raise SystemExit(main())

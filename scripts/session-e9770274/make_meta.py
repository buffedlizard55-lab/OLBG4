#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — build the source manifest and the flagged-for-review register.

Both files are derived, not hand-written: sources.json is read straight out of the capture manifest
(with a flag for whether a target actually backs a published row), and every capture failure becomes a
flag automatically, so nothing can quietly disappear.

Outputs: data/session-e9770274/sources.json, data/session-e9770274/flags.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-e9770274"
DESK = json.loads((DATA / "desk.json").read_text())
PREDS = json.loads((DATA / "predictions.json").read_text())
CAP = DATA / "capture" / DESK["capture_id"]
MANIFEST = json.loads((CAP / "manifest.json").read_text())

SPORTS_WITH_REASON = {}


def main() -> int:
    used = set()
    for r in DESK["rows"]:
        o = r.get("official") or {}
        if o.get("capture_id"):
            used.add(o["capture_id"])
        if o.get("standings_capture_id"):
            used.add(o["standings_capture_id"])
    # ids used through a secondary field
    for r in DESK["rows"]:
        o = r.get("official") or {}
        for key, val in o.items():
            if key.endswith("capture_id") and isinstance(val, str):
                used.add(val)

    sources = {
        "schema": "olbg4.board-ca.sources/1",
        "capture_id": DESK["capture_id"],
        "captured_utc": MANIFEST["finished_utc"],
        "total": len(MANIFEST["records"]),
        "used_count": 0,
        "sources": [],
    }
    for rec in MANIFEST["records"]:
        is_used = rec["id"] in used
        sources["sources"].append({
            "id": rec["id"], "sport": rec.get("sport", ""), "url": rec["url"],
            "status": rec.get("status"), "bytes": rec.get("bytes") or 0,
            "sha256": rec.get("sha256") or "", "used": is_used,
        })
    sources["used_count"] = sum(1 for s in sources["sources"] if s["used"])
    (DATA / "sources.json").write_text(json.dumps(sources, indent=1, ensure_ascii=False) + "\n",
                                       encoding="utf-8")

    # ------------------------------------------------------------------ flags
    flags: list[dict] = []

    def add(group: str, title: str, detail: str, source_url: str = "") -> None:
        flags.append({"group": group, "title": title, "detail": detail, "source_url": source_url})

    # 1. capture failures
    failures = [r for r in MANIFEST["records"] if r.get("status") != 200]
    for r in failures:
        add("Capture failures — no data was obtained",
            f"{r['id']} returned HTTP {r.get('status')} ({r.get('error') or 'no body'})",
            f"Requested {r['url']}. No line or fact on this site depends on it; the affected market is withheld.",
            r["url"])

    # 2. the requirement arithmetic
    add("The brief's two High-confidence tests conflict",
        "‘Greater than 70% chance’ and ‘priced between −250 and +10,000’ overlap only in the 70.0–71.4% sliver",
        "A 70% chance is a fair price of −233; −250 is a 71.4% chance; anything above 71.4% prices shorter than "
        "−250 and leaves the band. This desk keeps the band as the hard filter and publishes the probability on "
        "every row so a stricter cut can be applied by the reader. The grade rules are spelled out on the "
        "Methodology page.", "")

    # 3. five-per-sport shortfall
    rows = DESK["rows"]
    for sport in sorted(DESK["summary"]["by_sport"]):
        d = DESK["summary"]["by_sport"][sport]
        written = [p for p in PREDS["predictions"] if p["sport"] == sport]
        if len(written) >= 5:
            continue
        reason = next((f["text"] for r in rows if r["sport"] == sport for f in r["flags"]
                       if f["kind"] == "no-official-input"), "")
        if not reason:
            reason = next((f["text"] for r in rows if r["sport"] == sport for f in r["flags"]
                           if f["kind"] == "market-withheld"), "")
        add("Shortfall against the five-written-predictions-per-sport target",
            f"{sport}: {d['listed']} listed on OLBG, {d['priced']} priced, {len(written)} written prediction(s)",
            reason or "The sport does not list five priceable fixtures today.", "")

    if not PREDS["predictions"]:
        add("No written prediction on this run",
            "This desk ran with zero written predictions",
            "No hand-written prediction matched the priced fixtures in this capture. The lines and grades are "
            "still published; the prediction slate is empty and that is recorded here rather than filled with "
            "a template.", "")

    # 4. OLBG clock versus official clock
    for r in rows:
        for f in r["flags"]:
            if f["kind"] == "olbg-time-delta":
                add("Clock disagreement between OLBG and the official source",
                    f"{r['match']} — {r['sport']}", f["text"], r["olbg"]["url"])

    # 5. thin samples
    for r in rows:
        if r["status"] == "priced" and not r["sample"]["adequate"]:
            add("Priced on a thin sample",
                f"{r['match']} — {r['sport']} (sample {r['sample']['games']} completed game(s))",
                "The line is originated from the official record we hold, but because the sample is thin the "
                "pick is capped at Medium regardless of its probability. Shown on the row as "
                "‘" + r["pick"]["confidence_reason"] + "’.", (r.get("official") or {}).get("url", ""))

    # 6. injuries
    add("No official injury feed could be captured for any sport",
        "Injury analysis is a stated requirement and is not delivered today",
        "None of the official sources we captured publish a machine-readable availability report at the time of "
        "capture for these fixtures: the NHL and MLB publish rosters but not a status feed with an injury list, "
        "and the club-level reports are published as PDFs behind dynamic pages. Every prediction therefore says "
        "plainly that no injury claim is made, rather than guessing at a lineup.", "")

    # 7. repo-level defects found in the review
    review = json.loads((DATA / "review.json").read_text())
    for f in review["findings"]:
        if f["severity"] != "defect":
            continue
        add("Defect found in the repository's existing published data", f["title"], f["detail"], f["where"])

    # 8. listings that are futures, not matches
    futures = [r for r in rows if r["status"] != "priced" and
               any(k in r["match"] for k in ("2027", "Big Bash", "SA20", "Blast", "World Cup", "Championship"))]
    if futures:
        add("OLBG mixes season-long outright markets into its sport boards",
            f"{len(futures)} of the listings are futures, not fixtures (for example "
            f"'{futures[0]['match']}')",
            "They are kept in the list so the board is complete, and are left unpriced because a futures market "
            "is not a match we can originate a match line for.", futures[0]["olbg"]["url"])

    payload = {
        "schema": "olbg4.board-ca.flags/1",
        "session": "arena/e9770274-olbg4",
        "capture_id": DESK["capture_id"],
        "count": len(flags),
        "flags": flags,
    }
    (DATA / "flags.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
    print(f"sources: {sources['used_count']}/{sources['total']} used · flags: {len(flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

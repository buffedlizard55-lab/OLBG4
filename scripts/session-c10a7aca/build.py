#!/usr/bin/env python3
"""Build the complete C10 desk from committed evidence; never fetch the network."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

from common import DATA, ROOT, SPORTS, EvidenceStore, add_official_only, iso, olbg_events, reconcile
from model import originate
from official import parse_all
from review import FALLBACK_LINKS, write as write_review


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def official_link(event: dict) -> str:
    return event.get("official_url") or FALLBACK_LINKS.get(event.get("sport", ""), "https://www.olbg.com/betting-tips")


def public_event(event: dict) -> dict:
    """Add explicit public fields without discarding raw OLBG audit values."""
    detail = event.get("official_detail") or {}
    event["manual_review_url"] = official_link(event)
    event["olbg_start_utc"] = event.get("start_utc")
    if event.get("official") and not detail.get("start_timezone_unverified"):
        event["published_start_utc"] = event.get("official_start_utc") or ""
        event["published_date"] = (event.get("official_start_utc") or "")[:10]
        event["published_time_note"] = "UTC from the official feed"
    elif event.get("official"):
        exact_clock_match = bool(event.get("olbg_start_utc") and event.get("official_start_utc")
                                 and event["olbg_start_utc"] == event["official_start_utc"])
        event["published_start_utc"] = event.get("official_start_utc") or "" if exact_clock_match else ""
        event["published_date"] = detail.get("start_date") or (event.get("official_start_utc") or "")[:10]
        event["published_time_note"] = ("Official clock value agrees exactly with OLBG's Unix timestamp" if exact_clock_match
                                        else "Official date/time retained without a timezone; UTC left blank")
    else:
        event["published_start_utc"] = ""
        event["published_date"] = ""
        event["published_time_note"] = "Blank pending official confirmation"
    event["published_venue"] = detail.get("venue", "") if event.get("official") else ""
    event["official_local_time"] = detail.get("start_time_local", "") if event.get("official") else ""
    event["is_flagged"] = bool(event.get("flags")) or not event.get("official") or not event.get("prediction")
    event["flag_summary"] = " ".join(event.get("flags") or ([] if event.get("prediction") else ["No originated selection meets the evidence gates."]))
    return event


def source_rows(store: EvidenceStore, events: list[dict], olbg_audit: dict) -> list[dict]:
    used = {t for t in olbg_audit.get("hub_counts", {}) if store.get(t)}
    for event in events:
        for citation in event.get("official_evidence") or []:
            if citation.get("target"):
                used.add(citation["target"])
    rows = []
    for item in store.inventory():
        status = item.get("status")
        if item["id"] in used:
            disposition = "Parsed into the desk"
        elif status != 200 or not item.get("bytes"):
            disposition = "Unavailable or failed; not used"
        else:
            disposition = "Captured; not required by the current parsers"
        rows.append({
            "target": item["id"], "url": item["url"], "status": status, "bytes": item.get("bytes") or 0,
            "captured_utc": item.get("fetched_utc"), "capture": item.get("capture"),
            "sha256": item.get("sha256") or "", "evidence_file": item.get("file") or "",
            "host": urlparse(item["url"]).netloc, "disposition": disposition,
            "used": item["id"] in used, "error": item.get("error") or "",
        })
    return rows


def build() -> dict:
    store = EvidenceStore()
    events, olbg_audit = olbg_events(store)
    official = parse_all(store)
    reconcile(events, official, "Captured official competition source")
    added = add_official_only(events, official, store.cutoff)
    originate(events, store.cutoff)
    events = [public_event(e) for e in events]
    sources = source_rows(store, events, olbg_audit)
    review = write_review()

    coverage = []
    for sport in SPORTS:
        rows = [e for e in events if e["sport"] == sport]
        coverage.append({
            "sport": sport, "rows": len(rows), "olbg_rows": sum(e.get("on_olbg") for e in rows),
            "official_rows": sum(e.get("official") for e in rows), "official_only": sum(not e.get("on_olbg") for e in rows),
            "priced": sum(bool(e.get("prediction")) for e in rows),
            "high": sum(e.get("confidence") == "High" for e in rows),
            "high_focus": sum(bool(e.get("high_focus")) for e in rows),
            "shortlist": sum(bool(e.get("shortlist")) for e in rows),
            "next_36h_focus": sum(bool(e.get("within_36h")) and bool(e.get("high_focus")) for e in rows),
            "flagged": sum(bool(e.get("is_flagged")) for e in rows),
            "unresolved_olbg": sum(e.get("on_olbg") and not e.get("official") for e in rows),
        })
    predictions = [e for e in events if e.get("prediction")]
    high = [e for e in predictions if e.get("confidence") == "High"]
    shortlist = sorted((e for e in predictions if e.get("shortlist")),
                       key=lambda e: (SPORTS.index(e["sport"]), -e["predicted_probability"], e["event_id"]))
    next_36h = sorted((e for e in predictions if e.get("within_36h") and e.get("high_focus")),
                      key=lambda e: (-e["predicted_probability"], e.get("start_utc") or "", e["event_id"]))
    upcoming = sorted((e for e in events if e.get("official") and e.get("published_start_utc")),
                      key=lambda e: (e["published_start_utc"], SPORTS.index(e["sport"]), e["event_id"]))
    markets = []
    for event in predictions:
        for index, market in enumerate(event.get("markets") or [], 1):
            markets.append({
                "event_id": event["event_id"], "sport": event["sport"], "competition": event.get("competition", ""),
                "matchup": event["event"], "start_utc": event["published_start_utc"], "official_url": event["manual_review_url"],
                "market_index": index, **market,
            })
    flagged = [{
        "event_id": e["event_id"], "sport": e["sport"], "matchup": e["event"], "competition": e.get("competition", ""),
        "official": bool(e.get("official")), "priced": bool(e.get("prediction")), "reason": e["flag_summary"],
        "flags": e.get("flags") or [], "manual_url": e["manual_review_url"], "olbg_url": e.get("olbg_url") or "",
    } for e in events if e.get("is_flagged")]
    summary = {
        "sports": len(SPORTS), "rows": len(events), "olbg_rows": sum(e.get("on_olbg") for e in events),
        "official_rows": sum(e.get("official") for e in events), "official_only_additions": added,
        "priced_rows": len(predictions), "high": len(high), "high_focus": sum(e.get("high_focus") for e in events),
        "shortlist": len(shortlist), "next_36h_focus": len(next_36h), "flagged_rows": len(flagged),
        "market_selections": len(markets), "source_targets": len(sources),
        "source_targets_used": sum(s["used"] for s in sources),
        "repository_records_reviewed": review["summary"]["records_reviewed"],
        "repository_findings": review["summary"]["findings"],
        "sports_without_a_qualifying_shortlist_pick": [c["sport"] for c in coverage if not c["shortlist"]],
    }
    desk = {
        "schema": "c10-independent-olbg-desk/v1", "board": "C10", "session": "arena/c10a7aca-olbg4",
        "evidence_cutoff_utc": iso(store.cutoff), "publication_window_days": 7,
        "scope": SPORTS, "method": {
            "fixture_gate": "Only unambiguous official two-sided reconciliation receives originated prices.",
            "independence": "OLBG selections and prices never enter probability calculations; comparisons occur afterwards.",
            "high_gate": "High requires at least 70% estimated probability plus the sport-specific evidence-depth gate.",
            "focus_gate": "High focus additionally requires fair American odds from -250 through +10000.",
            "shortlist_gate": "Up to five strongest qualifying High-focus matches per sport in the seven-day publication window; no quota filling.",
            "unresolved": "Unconfirmed public fields are blank and the row is linked for official manual review.",
            "coverage": olbg_audit["coverage_limit"],
        },
        "summary": summary, "coverage": coverage, "events": events, "olbg_audit": olbg_audit,
        "capture_manifests": [{k: v for k, v in m.items() if k != "items" and not k.startswith("_")} for m in store.manifests],
    }
    dump(DATA / "desk.json", desk)
    dump(DATA / "summary.json", {"schema": desk["schema"], "evidence_cutoff_utc": desk["evidence_cutoff_utc"],
                                  "summary": summary, "coverage": coverage})
    dump(DATA / "predictions.json", {"schema": "c10-predictions/v1", "evidence_cutoff_utc": desk["evidence_cutoff_utc"],
                                      "next_36h": [e["event_id"] for e in next_36h], "shortlist": [e["event_id"] for e in shortlist],
                                      "predictions": predictions})
    dump(DATA / "markets.json", {"schema": "c10-markets/v1", "evidence_cutoff_utc": desk["evidence_cutoff_utc"], "rows": markets})
    dump(DATA / "flagged.json", {"schema": "c10-flagged/v1", "evidence_cutoff_utc": desk["evidence_cutoff_utc"],
                                  "note": "Flagged rows are disclosed for manual review and do not by themselves make the build unhealthy.",
                                  "rows": flagged, "repository_findings": review["findings"]})
    dump(DATA / "sources.json", {"schema": "c10-sources/v1", "evidence_cutoff_utc": desk["evidence_cutoff_utc"], "rows": sources})
    dump(DATA / "upcoming.json", {"schema": "c10-upcoming/v1", "evidence_cutoff_utc": desk["evidence_cutoff_utc"],
                                   "rows": upcoming[:100]})
    print(json.dumps(summary, indent=2))
    return desk


if __name__ == "__main__":
    build()

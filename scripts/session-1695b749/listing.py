#!/usr/bin/env python3
"""Board AB — carry OLBG's live listing as a listing only, with its capture verified.

The brief starts from OLBG: a full, current list of in-scope matches. This board's
originated lines come from official league payloads, but the *listing* comes from the
committed OLBG hub capture (2026-10-22T03:04Z UTC). Nothing here is treated as a fact:
every carried row is written with no official source, no price and no pick, and is
flagged as unverified on the site.

Integrity check performed here: each hub's captured bytes are gunzipped and hashed and
must equal the SHA-256 recorded for that hub in the capture manifest; rows from a hub
that fails are dropped rather than published.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INV = ROOT / "data" / "session-c4fda15e" / "olbg_inventory.json"
OUT = ROOT / "data" / "session-1695b749" / "listing.json"


def main():
    inv = json.loads(INV.read_text())
    cap = ROOT / inv["capture_dir"]
    manifest = json.loads((cap / "manifest.json").read_text())
    by_url = {i["url"]: i for i in manifest["items"]}

    verified_hubs, failed_hubs = {}, []
    for hub in inv["hubs"]:
        item = by_url.get(hub["hub_url"])
        if not item:
            failed_hubs.append({"url": hub["hub_url"], "reason": "hub not present in the capture manifest"})
            continue
        path = cap / item["file"]
        try:
            payload = gzip.decompress(path.read_bytes())
        except OSError:
            failed_hubs.append({"url": hub["hub_url"], "reason": "capture file could not be decompressed"})
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if digest != hub["sha256"]:
            failed_hubs.append({"url": hub["hub_url"], "reason": f"sha256 mismatch: manifest {digest}"})
            continue
        verified_hubs[hub["hub_url"]] = {
            "url": hub["hub_url"], "sha256": hub["sha256"], "fetched_utc": hub["fetched_utc"],
            "http_status": hub["http_status"], "sport": hub["sport"],
        }

    rows, dropped = [], 0
    for e in inv["events"]:
        if e["event_id"] is None:
            continue
        hub_url = f"https://www.olbg.com/betting-tips/{e['sport'].replace(' ', '_')}/{e['olbg_sport_id']}"
        if hub_url not in verified_hubs:
            dropped += 1
            continue
        rows.append({
            "id": f"OLBG{e['event_id']}",
            "sport": e["sport"],
            "competition": e.get("olbg_competition_path") or "",
            "event_name": e["event_name"],
            "start_utc": e["start_utc"],
            "market_label_on_listing": e.get("market_label") or "",
            "olbg_url": e["olbg_url"],
            "hub_url": hub_url,
            "hub_sha256": verified_hubs[hub_url]["sha256"],
            "captured_at_utc": e.get("captured_utc") or verified_hubs[hub_url]["fetched_utc"],
            "row_kind": e["row_kind"],
            "in_scope_on_olbg": e["in_scope"],
            "official_source": None,
            "official_source_status": "not verified by this board",
            "price": None,
            "pick": None,
            "status": "listed only",
        })

    matches = [r for r in rows if r["row_kind"] == "match"]
    outrights = [r for r in rows if r["row_kind"] == "outright"]
    OUT.write_text(json.dumps({
        "schema": "olbg4.board-ab.listing/1",
        "board": "AB",
        "generated_at_utc": "2026-10-22T07:55:00Z",
        "source_inventory": str(INV.relative_to(ROOT)),
        "note": "OLBG's live listing, carried as a listing only. No OLBG price, tip, percentage or comment is reproduced. Every row is published with a blank official source and a blank price, and is flagged for review. Times are the listing's own UTC start values; OLBG renders visible times in the visitor's timezone and those are not used.",
        "hubs_verified": len(verified_hubs),
        "hubs_failed": failed_hubs,
        "dropped_rows": dropped,
        "counts": {"match_rows": len(matches), "outright_rows": len(outrights)},
        "matches": matches,
        "outrights": outrights,
    }, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"hubs_verified": len(verified_hubs), "hubs_failed": len(failed_hubs),
                      "match_rows": len(matches), "outright_rows": len(outrights), "dropped": dropped}, indent=2))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Parse OLBG sport-hub listings into a fixture + market inventory.

Board SA (session 696c1a7c). Input is the byte-exact capture committed by
`.github/workflows/sa-696c1a7c.yml`; nothing here re-fetches the network.

Two structures carry the listing on a hub page:

* **rendered rows** — `<li class="min-h-[NNpx]">` blocks with `itemprop="name"`,
  `itemprop="startDate"`, the selection in an `<h4>`, the market label in
  `<p class="truncate text-sm">` and the price in `data-decimal` / `data-american`;
* **the embedded tips array** — the same facts plus event/league URLs and a Unix
  start timestamp, in the page's own Svelte payload (`{id:"…",selection:"…",…}`).

The embedded array is the superset (it currently carries 25 basketball tips where
the rendered list shows 10), so it is primary and the rendered rows are kept as a
cross-check. The listing is used for three things only:

1. the **fixture list** — every event OLBG currently has open for a brief sport,
2. the **market taxonomy** — which market labels OLBG shows for each sport,
3. a **reference quote** recorded beside, never instead of, our own line.

No OLBG price is used as a model input.

Usage: python3 parse_listings.py [CAPTURE_DIR]
"""
from __future__ import annotations

import gzip
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"

SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]

ROW_SPLIT = re.compile(r'<li class="min-h-\[\d+px\]">')
RE_ROW_URL = re.compile(r'href="(https://www\.olbg\.com/betting-tips/[^"]*?event_id=\d+)"')
RE_ROW_NAME = re.compile(r'itemprop="name">([^<]*)<')
RE_ROW_START = re.compile(r'itemprop="startDate" datetime="([^"]+)"')
RE_ROW_SELECTION = re.compile(r'<h4[^>]*>\s*([^<]*?)\s*</h4>')
RE_ROW_MARKET = re.compile(r'<p class="truncate text-sm">\s*([^<]*?)\s*</p>')
RE_ROW_ODDS = re.compile(r'data-decimal="([0-9.]+)"\s+data-american="([-+0-9]+)"')

TIP = re.compile(
    r'\{id:"(?P<id>[0-9a-f]+)",'
    r'selection:"(?P<selection>(?:[^"\\]|\\.)*)",'
    r'market_alias:"(?P<market>(?:[^"\\]|\\.)*)",'
    r'odds:"(?P<decimal>[^"]*)",'
    r'american_odds:"(?P<american>[^"]*)",'
    r'fractional_odds:"(?P<fractional>[^"]*)",'
    r'event_start_unix_timestamp:(?P<ts>\d+),'
    r'categoryUrl:"(?P<category>[^"]*)",'
    r'eventUrl:"(?P<event_url>[^"]*)",'
    r'leagueUrl:"(?P<league>[^"]*)",'
    r'event_name_alias:"(?P<event>(?:[^"\\]|\\.)*)"'
)


def unescape(value: str) -> str:
    return (value.replace('\\"', '"').replace("\\u0026", "&").replace("\\\\", "\\")).strip()


def american_to_decimal(american: int) -> float:
    return round(1 + (american / 100.0 if american > 0 else 100.0 / abs(american)), 4)


def decimal_to_american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1) * 100))
    return -int(round(100 / (dec - 1)))


def url_bits(url: str) -> dict:
    parts = [p for p in urlsplit(url).path.split("/") if p]
    q = parse_qs(urlsplit(url).query)
    return {
        "sport_slug": parts[1] if len(parts) > 1 else "",
        "region": parts[2] if len(parts) >= 5 else "",
        "competition": parts[3] if len(parts) >= 5 else "",
        "event_slug": parts[4] if len(parts) >= 5 else (parts[2] if len(parts) == 4 else ""),
        "event_id": (q.get("event_id") or [""])[0],
    }


def iso(ts: int) -> str:
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_embedded(html: str, sport: str, hub_url: str) -> list[dict]:
    rows = []
    for m in TIP.finditer(html):
        url = unescape(m.group("event_url"))
        bits = url_bits(url)
        dec_raw = m.group("decimal").strip()
        am_raw = m.group("american").strip()
        try:
            dec = float(dec_raw) if dec_raw else None
        except ValueError:
            dec = None
        try:
            am = int(am_raw) if am_raw else None
        except ValueError:
            am = None
        rows.append(
            {
                "sport": sport,
                "source": "olbg_embedded",
                "tip_id": m.group("id"),
                "event": unescape(m.group("event")),
                "event_id": bits["event_id"],
                "olbg_url": url,
                "league_url": unescape(m.group("league")),
                "region": bits["region"],
                "competition_slug": bits["competition"],
                "start_utc": iso(m.group("ts")),
                "selection": unescape(m.group("selection")),
                "market": unescape(m.group("market")),
                "listed_decimal": dec,
                "listed_american": am,
                "listed_fractional": m.group("fractional").strip(),
                "hub_url": hub_url,
            }
        )
    return rows


def parse_rendered(html: str, sport: str, hub_url: str) -> list[dict]:
    rows = []
    for block in ROW_SPLIT.split(html)[1:]:
        url_m, name_m = RE_ROW_URL.search(block), RE_ROW_NAME.search(block)
        if not url_m or not name_m:
            continue
        url = url_m.group(1)
        bits = url_bits(url)
        sel, mkt = RE_ROW_SELECTION.search(block), RE_ROW_MARKET.search(block)
        odds, start = RE_ROW_ODDS.search(block), RE_ROW_START.search(block)
        rows.append(
            {
                "sport": sport,
                "source": "olbg_rendered",
                "tip_id": "",
                "event": name_m.group(1).strip(),
                "event_id": bits["event_id"],
                "olbg_url": url,
                "league_url": "",
                "region": bits["region"],
                "competition_slug": bits["competition"],
                "start_utc": (start.group(1).replace(".000Z", "Z") if start else ""),
                "selection": sel.group(1).strip() if sel else "",
                "market": mkt.group(1).strip() if mkt else "",
                "listed_decimal": float(odds.group(1)) if odds else None,
                "listed_american": int(odds.group(2)) if odds else None,
                "listed_fractional": "",
                "hub_url": hub_url,
            }
        )
    return rows


def group_events(rows: list[dict]) -> list[dict]:
    events: dict[str, dict] = {}
    for r in rows:
        key = r["event_id"] or r["event"]
        ev = events.setdefault(
            key,
            {
                "sport": r["sport"],
                "event_id": r["event_id"],
                "event": r["event"],
                "olbg_url": r["olbg_url"],
                "league_url": r["league_url"],
                "region": r["region"],
                "competition_slug": r["competition_slug"],
                "start_utc": r["start_utc"],
                "hub_url": r["hub_url"],
                "listed_markets": [],
            },
        )
        for field in ("start_utc", "olbg_url", "league_url", "region", "competition_slug"):
            if not ev.get(field) and r.get(field):
                ev[field] = r[field]
        entry = {
            "selection": r["selection"],
            "market": r["market"],
            "decimal": r["listed_decimal"],
            "american": r["listed_american"],
            "fractional": r["listed_fractional"],
            "from": r["source"],
        }
        if entry not in ev["listed_markets"]:
            ev["listed_markets"].append(entry)
    return sorted(events.values(), key=lambda e: (e["start_utc"] or "9999", e["event"]))


def all_captures() -> list[Path]:
    return sorted((p for p in (DATA / "capture").glob("*") if (p / "manifest.json").exists()),
                  reverse=True)


def hub_pool(dirs: list[Path]) -> tuple[dict[str, tuple[Path, dict]], str]:
    """Newest capture per sport, across every capture on disk.

    Each capture run fetches a different slice of targets, so the listing has to be
    assembled from all of them: the newest hub wins for its sport and the rest are
    kept as cross-checks. The capture id recorded in the JSON is the newest run that
    contributed a hub.
    """
    pool: dict[str, tuple[Path, dict]] = {}
    for path in dirs:
        manifest = json.loads((path / "manifest.json").read_text())
        for rec in manifest["records"]:
            if rec["sport"] not in SPORTS or "betting-tips/" not in rec["url"]:
                continue
            segs = [s for s in urlsplit(rec["url"]).path.split("/") if s]
            if len(segs) != 3:
                continue
            if rec["sport"] in pool:
                continue
            pool[rec["sport"]] = (path, rec)
    newest = dirs[0].name if dirs else ""
    for path in dirs:
        pool_dir = {p.name for p, _ in pool.values()}
        if path.name in pool_dir:
            newest = path.name
            break
    return pool, newest


def main() -> int:
    if len(sys.argv) > 1:
        dirs = [Path(sys.argv[1])]
    else:
        dirs = all_captures()
    if not dirs:
        raise SystemExit("no capture directory with a manifest yet")
    cap = dirs[0]
    manifest = json.loads((cap / "manifest.json").read_text())

    hubs: dict[str, dict] = {}
    hub_dir: dict[str, Path] = {}
    extras: list[dict] = []
    for path in dirs:
        man = json.loads((path / "manifest.json").read_text())
        for rec in man["records"]:
            if rec["sport"] not in SPORTS or "betting-tips/" not in rec["url"]:
                continue
            segs = [s for s in urlsplit(rec["url"]).path.split("/") if s]
            if len(segs) == 3:
                if rec["sport"] not in hubs:
                    hubs[rec["sport"]] = rec
                    hub_dir[rec["sport"]] = path
            elif len(segs) >= 4 and "event_id=" not in rec["url"]:
                extras.append({**rec, "_dir": str(path)})

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = {
        "capture_id": cap.name,
        "captured_utc": manifest.get("finished_utc"),
        "parsed_utc": now,
        "session": manifest.get("session"),
        "sports": {},
        "taxonomy": {},
        "counts": {},
    }
    market_counter: Counter = Counter()
    competition_counter: Counter = Counter()

    for sport in SPORTS:
        rec = hubs.get(sport)
        if not rec:
            out["sports"][sport] = {"sport": sport, "hub_url": "", "events": [],
                                    "note": "no hub page captured", "rows_embedded": 0,
                                    "rows_rendered": 0}
            continue
        html = gzip.open(hub_dir[sport] / rec["file"], "rt", encoding="utf-8",
                         errors="replace").read()
        emb = parse_embedded(html, sport, rec["url"])
        rend = parse_rendered(html, sport, rec["url"])
        merged = emb + rend
        events = group_events(merged)
        out["sports"][sport] = {
            "sport": sport,
            "hub_url": rec["url"],
            "hub_sha256": rec["sha256"],
            "hub_bytes": rec["bytes"],
            "hub_final_url": rec.get("final_url", rec["url"]),
            "rows_embedded": len(emb),
            "rows_rendered": len(rend),
            "events": events,
        }
        for ev in events:
            competition_counter[(sport, ev["competition_slug"] or ev["region"] or "unknown")] += 1
            for mk in ev["listed_markets"]:
                market_counter[(sport, mk["market"] or "(unlabelled)")] += 1

    # Competition-level pages captured for shape comparison are parsed too, so the
    # schema check records what they add rather than guessing.
    shape = []
    for rec in extras:
        html = gzip.open(Path(rec["_dir"]) / rec["file"], "rt", encoding="utf-8",
                         errors="replace").read()
        sport = rec["sport"]
        evs = group_events(parse_embedded(html, sport, rec["url"]) +
                           parse_rendered(html, sport, rec["url"]))
        shape.append({"url": rec["url"], "sport": sport, "events": len(evs)})

    out["taxonomy"] = {
        "markets": [
            {"sport": s, "market": m, "rows": n}
            for (s, m), n in sorted(market_counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "competitions": [
            {"sport": s, "competition": c, "events": n}
            for (s, c), n in sorted(competition_counter.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        "extra_listing_pages": shape,
    }
    out["counts"] = {
        "events_total": sum(len(v["events"]) for v in out["sports"].values()),
        "events_by_sport": {s: len(out["sports"][s]["events"]) for s in SPORTS},
        "upcoming_by_sport": {
            s: sum(1 for e in out["sports"][s]["events"] if (e["start_utc"] or "9") >= now)
            for s in SPORTS
        },
    }

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "listings.json").write_text(json.dumps(out, indent=1) + "\n")

    print(f"capture {cap.name} parsed at {now}")
    for sport in SPORTS:
        v = out["sports"][sport]
        dates = sorted({e["start_utc"][:10] for e in v["events"] if e["start_utc"]})
        print(f"  {sport:15s} events={len(v['events']):4d} "
              f"emb={v.get('rows_embedded', 0):4d} rend={v.get('rows_rendered', 0):4d} "
              f"{dates[0] if dates else '-'}..{dates[-1] if dates else '-'}")
    print(f"total events {out['counts']['events_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

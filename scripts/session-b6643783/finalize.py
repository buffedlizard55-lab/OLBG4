#!/usr/bin/env python3
"""Board CA — finalise the desk, the coverage record and the flag register.

    python3 finalize.py <capture_dir>

Outputs into data/session-b6643783/:
    desk.json   every row, priced or blank
    meta.json   capture stamp, window, per-sport gaps, archive links
    flags.json  one record per irregularity, with the source that shows it
"""
from __future__ import annotations

import glob
import json
import os
import tempfile
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import augment  # noqa: E402
import parse as P  # noqa: E402

DATA = os.path.join(ROOT, "data", "session-b6643783")
CUTOFF = "2026-10-24T17:30:00Z"
WINDOW_END = "2026-11-08T23:59:59Z"

GAPS = [
    ("Gaelic Sports",
     "gaa.ie serves a client-side app: the captured page carries no fixture list, so GAA club and county "
     "matches are listed from OLBG only and cannot be priced from an official table.",
     "https://www.gaa.ie/fixtures"),
    ("Greyhounds",
     "The Greyhound Board of Great Britain results API returns completed races; no forward racecard with "
     "traps, going and runners was retrievable, so no greyhound line is originated.",
     "https://www.gbgb.org.uk/racecards/"),
    ("Cricket",
     "ICC publishes team rankings on a client-rendered page and no machine-readable fixture list; domestic "
     "boards (Cricket Australia, NZC, ECB, BCCI) likewise serve app shells. Fixtures appear from OLBG only.",
     "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i"),
    ("Rugby League",
     "rlwc2026.com and nrl.com return app shells with no fixture JSON; no league table was retrievable to "
     "build a strength input from.",
     "https://www.rlwc2026.com/fixtures"),
    ("Rugby Union",
     "unitedrugby.com and premiershiprugby.com return client-rendered match centres (5.7 KB shell); no table "
     "or fixture array was captured, so URC and Premiership fixtures stay unpriced.",
     "https://stats.unitedrugby.com/match-centre/table/2026-27"),
    ("Darts",
     "pdc.tv returns the same 1.24 MB JavaScript shell for every route, so the draw is not machine-readable. "
     "The PDC participant API gives Order of Merit rankings but not tonight's pairings, so no line is made "
     "from ranking alone.",
     "https://www.pdc.tv/"),
    ("Handball",
     "EHF Champions League and the German/Spanish/French leagues render fixtures client-side; the Danish "
     "Herreligaen table is machine-readable but no OLBG-listed fixture in the window involved two Danish "
     "sides, so the handball rows stay unpriced.",
     "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    ("Volleyball",
     "Italian SuperLega, Polish PlusLiga and Czech Extraliga tables were captured, but the Italian season is "
     "one match old and the Polish table could not be reconciled to a single fixture in the window, so only "
     "rows with a reliable sample are priced.",
     "https://www.legavolley.it/classifica/"),
    ("Golf",
     "Golf is an outright tournament market, not a two-sided match. OLBG closes its golf tip markets when "
     "round one starts, so in-play weeks show no OLBG listing; the outright shown comes from the PGA Tour "
     "leaderboard only.",
     "https://www.pgatour.com/leaderboard"),
    ("Motor Racing",
     "Formula 1 and MotoGP publish a round-by-round calendar but not a machine-readable outright market; the "
     "race outright is derived from the official drivers' championship only.",
     "https://www.formula1.com/en/results/2026/drivers"),
    ("Tennis",
     "The WTA API returns match objects; where an official singles ranking is missing for either player the "
     "row is left unpriced rather than guessed.",
     "https://www.wtatennis.com/rankings/singles"),
    ("Basketball",
     "NBA.com and the NBA CDN return HTTP 403 to this capture, so only EuroLeague and EuroCup fixtures are "
     "priced from official data.",
     "https://www.nba.com/schedule"),
    ("Snooker",
     "snooker.org carries the draw and WST publishes rankings, but the Northern Ireland Open was in play at "
     "capture, so only matches with both players ranked are priced.",
     "https://www.snooker.org/"),
]

PEERS = [
    ("session-edffdbc6/index.html", "Board ZZ — peer 24 Oct clarity desk, 75 own-line rows, 30 High picks (still reachable)"),
    ("session-937ee172/index.html", "Board BZ — 24 Oct NHL-only desk, three Medium write-ups (peer, still reachable)"),
    ("board/index.html", "Consolidated board (Board P)"),
    ("entries.html", "Legacy root entries table (21 Oct snapshot)"),
    ("picks.html", "Legacy root picks page (21 Oct snapshot)"),
    ("predictions.html", "Legacy root predictions (21 Oct snapshot)"),
    ("coverage.html", "Legacy root coverage page"),
    ("flagged.html", "Legacy root flagged page"),
    ("verification.html", "Board K verification register"),
    ("session-4502eff5/index.html", "Board FX — 23 Oct 21:50Z 15-sport desk (the capture this desk reuses)"),
    ("session-48de8c1d/index.html", "Board FB — 23 Oct 21:40Z desk with 75 written predictions"),
    ("session-2722b692/index.html", "Board AJ — 23 Oct 15-sport desk, 2,589 market selections"),
    ("session-49866065/index.html", "Board FA — evidence-gated desk"),
    ("session-4885d641/index.html", "Board AG — 21:15Z 18-sport desk"),
    ("session-6846f1ab/index.html", "Board AH — requested 15-sport snapshot"),
    ("session-22ca2e95/index.html", "Board AE — 22 Oct afternoon refresh"),
    ("session-0d3b826c/index.html", "Board AF — evidence desk"),
    ("session-343754f2/index.html", "Board BW — 23 Oct 15-sport desk"),
    ("session-543dca7d/index.html", "Board AS — 15-sport desk"),
    ("session-2c05e0b2/index.html", "Board AI — 15-sport OLBG desk"),
    ("session-509d544b/index.html", "Board AP — 15-sport final"),
    ("session-ed4c358c/index.html", "Board ED — 23 Oct desk"),
    ("session-405e9797/index.html", "Board AR — 23 Oct desk"),
    ("session-3a6388d2/index.html", "Board AD — 22 Oct desk"),
    ("session-19b8e377/index.html", "Board Z — 91 fixtures"),
    ("session-9359e596/index.html", "Board Z — 22 Oct live OLBG desk"),
    ("archive.html", "Full archive index"),
]


def main() -> int:
    cap_dir = sys.argv[1]
    cap_id = os.path.basename(cap_dir.rstrip("/"))
    cap = P.Capture(cap_dir)
    manifest = cap.manifest

    tmp_desk = os.path.join(tempfile.gettempdir(), "ca_originated.json")
    os.system(f'python3 "{os.path.join(HERE, "originate.py")}" "{cap_dir}" "{tmp_desk}" > /dev/null')
    doc = json.load(open(tmp_desk, encoding="utf-8"))

    tables = augment.build_tables(cap)
    for r in doc["rows"]:
        augment.price_row(r, tables)

    rows = [r for r in doc["rows"] if (r.get("start_utc") or "") >= CUTOFF]
    # OLBG lists greyhound race MEETINGS ("6:30 Central Park"), not matchups, and GBGB served no
    # runner card at capture, so those rows carry no participants. Collapse them to one record.
    meeting = [r for r in rows if r["sport"] == "Greyhounds" and not r.get("pick")
               and re.match(r"^\d{1,2}:\d{2}\s", r.get("side_a") or "")]
    if meeting:
        rows = [r for r in rows if r not in meeting]
        first = meeting[0]
        rows.append({
            "id": "ca_greyhounds_meetings", "sport": "Greyhounds", "sport_slug": "greyhounds",
            "competition": "OLBG greyhound meetings (no runner card retrieved)",
            "side_a": f"{len(meeting)} OLBG-listed greyhound races", "side_b": "",
            "start_utc": first["start_utc"], "venue": "", "official_url": first.get("official_url", ""),
            "official_source_name": "OLBG greyhound hub (meeting listings only)",
            "capture_id": first.get("capture_id", ""), "evidence": {}, "form": {}, "sample": "",
            "model": {}, "markets": {}, "pick": None,
            "flags": ["OLBG lists the race meetings but GBGB returned no forward racecard, so no runner, "
                      "trap or form data exists to originate a line from"],
            "olbg": first.get("olbg"),
        })
    rows.sort(key=lambda r: (r.get("start_utc") or "9999", r.get("sport") or ""))
    for r in rows:
        r.setdefault("sport_slug", dict(
            (s, s.lower().replace(" ", "-")) for s, _ in
            [(x, y) for x, y in [
                ("Golf", "golf"), ("Volleyball", "volleyball"), ("Rugby Union", "rugby-union"),
                ("Cricket", "cricket"), ("Snooker", "snooker"), ("Darts", "darts"),
                ("Baseball", "baseball"), ("Gaelic Sports", "gaelic-sports"), ("Greyhounds", "greyhounds"),
                ("Tennis", "tennis"), ("Motor Racing", "motor-racing"), ("Handball", "handball"),
                ("Ice Hockey", "ice-hockey"), ("Basketball", "basketball"), ("Rugby League", "rugby-league"),
            ]]).get(r.get("sport"), ""))

    summary = {}
    for r in rows:
        s = summary.setdefault(r["sport"], {"rows": 0, "priced": 0, "olbg": 0})
        s["rows"] += 1
        s["priced"] += 1 if r.get("pick") else 0
        s["olbg"] += 1 if (r.get("olbg") or {}).get("event_url") else 0

    doc["rows"] = rows
    doc["summary"] = summary
    doc["capture"] = cap_id
    doc["cutoff_utc"] = CUTOFF
    doc["window"] = {"start": CUTOFF, "end": WINDOW_END}
    with open(os.path.join(DATA, "desk.json"), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1, sort_keys=True)

    # ---------------------------------------------------------------- flags
    flags = []
    n = 0
    for r in rows:
        for f in (r.get("flags") or []):
            if not f:
                continue
            n += 1
            flags.append({
                "id": f"CA-F{n:03d}",
                "sport": r["sport"],
                "match": f'{r.get("side_a","")} {("v " + r["side_b"]) if r.get("side_b") else ""}'.strip(),
                "issue": "row published without a price" if not r.get("pick") else "pricing caveat",
                "detail": f,
                "source_url": r.get("official_url") or (r.get("olbg") or {}).get("event_url", ""),
                "severity": "high" if not r.get("official_url") else "medium",
            })
    for sport, reason, url in GAPS:
        n += 1
        flags.append({"id": f"CA-G{n:03d}", "sport": sport, "match": "(sport coverage)",
                      "issue": "official source does not publish a machine-readable fixture list",
                      "detail": reason, "source_url": url, "severity": "medium"})
    # capture-level failures are evidence, not silence
    for f in manifest.get("failures", []):
        n += 1
        flags.append({"id": f"CA-C{n:03d}", "sport": f.get("sport", ""), "match": "(capture target)",
                      "issue": f"source unavailable at capture (HTTP {f.get('status') or 'error'})",
                      "detail": (f.get("error") or "")[:300], "source_url": f.get("url", ""),
                      "severity": "low"})
    json.dump({"flags": flags, "count": len(flags)}, open(os.path.join(DATA, "flags.json"), "w",
                                                         encoding="utf-8"), indent=1)

    meta = {
        "capture_id": cap_id,
        "capture_utc": manifest.get("finished_utc", ""),
        "window_start": CUTOFF,
        "window_end": WINDOW_END,
        "targets": manifest.get("targets"),
        "ok": manifest.get("ok"),
        "failed": manifest.get("failed"),
        "gaps": [{"sport": s, "reason": r, "source_url": u} for s, r, u in GAPS],
        "peers": [{"href": h, "label": l} for h, l in PEERS],
    }
    json.dump(meta, open(os.path.join(DATA, "meta.json"), "w", encoding="utf-8"), indent=1)

    priced = sum(1 for r in rows if r.get("pick"))
    print(f"desk.json: {len(rows)} rows, {priced} priced, {len(flags)} flags, capture {cap_id}")
    for s, v in sorted(summary.items(), key=lambda kv: -kv[1]["rows"]):
        print(f"   {s:14s} rows={v['rows']:3d} priced={v['priced']:3d} olbg={v['olbg']:3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

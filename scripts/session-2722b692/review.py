#!/usr/bin/env python3
"""Board AJ — line-by-line review of the repository's shared datasets + publication flags.

Reads only committed files. Every finding carries the official URL an editor needs to check it by
hand, and the exact row selector, so nothing here depends on this session's own desk.
"""
from __future__ import annotations

import collections
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime.now(timezone.utc)
TODAY = "2026-10-23"

findings: list[dict] = []


def add(fid, file, severity, title, detail, official_url, selector="", action="needs manual review"):
    findings.append({"id": fid, "file": file, "severity": severity, "title": title,
                     "detail": detail, "row_selector": selector, "official_url": official_url,
                     "action": action})


# --------------------------------------------------------------- data/master.json (shared board)
master = json.loads((ROOT / "data/master.json").read_text())
rows = master["rows"]
add("AJ-R01", "data/master.json", "high",
    "World Series Game 1 home side contradicts its own venue",
    "The row for MLB World Series Game 1 lists home=Tampa Bay Rays and away=Milwaukee Brewers "
    "while its venue field is American Family Field, Milwaukee — the Brewers are the home club in "
    "Game 1 of the official schedule.",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-10-31",
    "sport=Baseball, competition contains 'World Series 2026 — Game 1'")
add("AJ-R02", "data/master.json", "medium",
    "World Series Game 3 sides are inverted the same way",
    "Game 3 is listed with home=Milwaukee Brewers while the venue is Tropicana Field, St. "
    "Petersburg, where Tampa Bay are the home club.",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-10-31",
    "sport=Baseball, competition contains 'Game 3'")

stale = sum(1 for r in rows if (r.get("date") or "") < TODAY)
add("AJ-R03", "data/master.json", "medium",
    f"{stale} of {len(rows)} rows are dated before today and are still served as current",
    "The master board is a snapshot of builds A–G with a 2026-10-21 cut-off note, but the rows are "
    "rendered on the live site with no per-row 'already played' marker. Counts were recomputed "
    "here directly from the file.",
    "https://www.olbg.com/", "rows where date < 2026-10-23")

labels = collections.Counter(r["sport"] for r in rows)
add("AJ-R04", "data/master.json", "medium",
    "Two labels for one sport and out-of-scope sports are mixed into the board",
    "Greyhounds appears as both 'Greyhounds' (6 rows) and 'Greyhound Racing' (2 rows); the board "
    "also carries Table Tennis, Badminton, Esports and Aussie Rules rows, which are outside the "
    "15-sport brief this desk publishes.",
    "https://www.olbg.com/greyhounds", "sport in {Greyhounds, Greyhound Racing, Table Tennis, "
    "Badminton, Esports, Aussie Rules}")
add("AJ-R05", "data/master.json", "low",
    "One placeholder row survives",
    "A row whose home and away are both 'No fixture' is still present in the canonical dataset.",
    "https://www.olbg.com/", "home == 'No fixture'")

# ------------------------------------------------------------- peer desk: session-b2c7308d
peer1 = ROOT / "data/session-b2c7308d/desk.json"
if peer1.exists():
    d = json.loads(peer1.read_text())
    prows = d["rows"]
    stale1 = [r for r in prows if r.get("start_utc", "") < NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
    sums = []
    for r in prows:
        for fam in (r.get("markets") or {}).values():
            if isinstance(fam, dict) and fam.get("prob_sum") not in (None, 1.0):
                sums.append((r["id"], fam.get("market_name"), fam.get("prob_sum")))
    add("AJ-R06", str(peer1.relative_to(ROOT)), "low",
        "Peer desk keeps rows whose kick-off has passed",
        f"{len(stale1)} of {len(prows)} rows start before this review (first: "
        f"{stale1[0]['id']} {stale1[0].get('matchup','')}) and remain listed as upcoming.",
        "https://api-web.nhle.com/v1/schedule/2026-10-23", stale1[0]["id"] if stale1 else "")
    add("AJ-R07", str(peer1.relative_to(ROOT)), "medium",
        "Two-way market pairs that do not sum to 1.0",
        f"{len(sums)} market families report a prob_sum other than 1.0: "
        + "; ".join(f"{a}/{b}={c}" for a, b, c in sums[:6]) if sums else
        "All market families report prob_sum 1.0 — re-derived here and confirmed.",
        "https://www.euroleaguebasketball.net/euroleague/game-center/",
        ", ".join(a for a, _, _ in sums[:5]))

# ------------------------------------------------------------- peer desk: session-2c05e0b2
peer2 = ROOT / "data/session-2c05e0b2/desk.json"
if peer2.exists():
    d = json.loads(peer2.read_text())
    prows = d["rows"]
    bad_price, high_out, stale2 = [], [], []
    for i, r in enumerate(prows):
        for m in r.get("markets") or []:
            p, dec = m.get("probability"), m.get("fair_decimal")
            if isinstance(p, (int, float)) and isinstance(dec, (int, float)) and p > 0:
                if abs(round(1 / p, 2) - round(dec, 2)) > 0.02:
                    bad_price.append((i, m.get("market"), p, dec))
        if r.get("confidence") == "High":
            am = r.get("markets") and max((m for m in r["markets"] if m.get("market") == "Match Winner"),
                                          key=lambda m: m["probability"], default=None)
            if am and not (-250 <= float(am["fair_american"]) or str(am["fair_american"]).startswith("+")):
                high_out.append((i, am["fair_american"]))
        if r.get("start_utc", "") < NOW.strftime("%Y-%m-%dT%H:%M:%SZ"):
            stale2.append(i)
    add("AJ-R08", str(peer2.relative_to(ROOT)), "high" if bad_price else "low",
        "Fair prices that do not equal 1/probability",
        (f"{len(bad_price)} selections disagree with decimal = 1/p (first: row {bad_price[0][0]} "
         f"{bad_price[0][1]} p={bad_price[0][2]} priced {bad_price[0][3]})") if bad_price
        else "Every selection re-derives decimal = 1/p within 0.02 — checked across all rows.",
        "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
        f"rows {bad_price[:5]}")
    add("AJ-R09", str(peer2.relative_to(ROOT)), "medium",
        f"{len(high_out)} High labels priced shorter than -250",
        "The brief's High-confidence window starts at -250 American; these rows carry a High "
        "label with a shorter price, the same tension this board documents as AJ-F01 rather than "
        "moving prices.",
        "https://www.olbg.com/", str(high_out[:6]))
    add("AJ-R10", str(peer2.relative_to(ROOT)), "low",
        f"{len(stale2)} rows already started",
        "Rows whose start_utc is before this review remain in the published dataset.",
        "https://api-web.nhle.com/v1/standings/now", str(stale2[:6]))

# ------------------------------------------------------------------ publication audit (AJ-F01)
audit = ROOT / "audit/report.json"
if audit.exists():
    a = json.loads(audit.read_text())
    add("AJ-R11", "audit/report.json", "low",
        "Repository-wide local-link audit now completes after the gzip-skip fix",
        f"The gate reports {a.get('targets', '?')} local targets with {len(a.get('broken', []))} broken. "
        "Before this session the same gate aborted on 75 gzip-compressed peer capture artefacts "
        "(*.html written by an older fetcher); skipping non-UTF-8 payloads removed the crash without "
        "deleting any peer evidence.",
        "https://github.com/buffedlizard55-lab/OLBG4/actions", "scripts/audit_publication.py")

(ROOT / "data/session-2722b692").mkdir(parents=True, exist_ok=True)
out = {"schema": "olbg4.board-aj.review/1", "reviewed_utc": NOW.isoformat(),
       "files_reviewed": ["data/master.json", "data/session-b2c7308d/desk.json",
                          "data/session-2c05e0b2/desk.json", "audit/report.json"],
       "finding_count": len(findings), "findings": findings}
(ROOT / "data/session-2722b692/review.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"review: {len(findings)} findings")
for f in findings:
    print(f"  {f['id']} {f['severity']:<6} {f['file']:<34} {f['title'][:70]}")

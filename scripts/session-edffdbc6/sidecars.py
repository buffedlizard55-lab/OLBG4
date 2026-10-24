#!/usr/bin/env python3
"""Board ZZ — sidecars: OLBG reverse-engineering index, repo line-by-line review, flagged register."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-edffdbc6"
def _capture_time() -> datetime:
    stamps = sorted(p for p in (ROOT / "data" / "session-edffdbc6" / "capture").glob("*/manifest.json"))
    if stamps:
        m = json.loads(stamps[-1].read_text(encoding="utf-8"))
        return datetime.fromisoformat(m["started_utc"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


NOW = _capture_time()

SPORT_LABEL = {
    "olbg_golf": "Golf", "olbg_volleyball": "Volleyball", "olbg_rugby_union": "Rugby Union",
    "olbg_cricket": "Cricket", "olbg_snooker": "Snooker", "olbg_darts": "Darts",
    "olbg_baseball": "Baseball", "olbg_gaelic_football": "Gaelic Sports", "olbg_hurling": "Gaelic Sports",
    "olbg_greyhounds": "Greyhounds", "olbg_tennis": "Tennis", "olbg_motor_racing": "Motor Racing",
    "olbg_handball": "Handball", "olbg_ice_hockey": "Ice Hockey", "olbg_basketball": "Basketball",
    "olbg_rugby_league": "Rugby League", "olbg_ice_hockey_nhl": "Ice Hockey",
    "olbg_basketball_nba": "Basketball", "olbg_basketball_el": "Basketball", "olbg_baseball_mlb": "Baseball",
}


def read_gz(path: Path) -> str:
    import gzip
    return gzip.decompress(path.read_bytes()).decode("utf-8", "replace")


def build_olbg(manifest: dict, cap_dir: Path, fixtures: list[dict]) -> dict:
    hubs, unverified = [], []
    fixture_names = {f"{f['home']} {f['away']}".lower(): f for f in fixtures}
    for rec in manifest["records"]:
        if not rec["id"].startswith("olbg_") or rec["id"] in ("olbg_robots", "olbg_sitemap", "olbg_home"):
            continue
        sport = SPORT_LABEL.get(rec["id"], rec.get("sport", ""))
        entry = {"sport": sport, "url": rec["url"], "status": rec.get("status"),
                 "matches_listed": 0, "upcoming_listed": 0, "sample": ""}
        if rec.get("status") == 200 and rec.get("file"):
            html = read_gz(cap_dir / rec["file"])
            events = {}
            for m in re.finditer(r'<a itemprop="url" href="([^"]+)"[^>]*>.*?itemprop="name">([^<]+)</h5>.*?'
                                 r'itemprop="startDate" datetime="([^"]+)"', html, re.S):
                url, name, start = m.group(1), m.group(2).strip(), m.group(3)
                events[url] = {"name": name, "start": start, "url": url}
            entry["matches_listed"] = len(events)
            up = [e for e in events.values() if e["start"] > NOW.strftime("%Y-%m-%dT%H:%M:%SZ")]
            entry["upcoming_listed"] = len(up)
            entry["sample"] = up[0]["name"] if up else (next(iter(events.values()))["name"] if events else "")
            for e in up:
                key = e["name"].lower().replace(" vs ", " ")
                parts = [p.strip() for p in re.split(r"\s+vs\s+", e["name"], flags=re.I)]
                verified = any(
                    (len(parts) == 2 and parts[0].lower() in (f["home"] + " " + f["away"]).lower()
                     and parts[1].lower() in (f["home"] + " " + f["away"]).lower())
                    or any(p.lower() in n for n in fixture_names for p in parts)
                    for f in fixtures
                )
                if not verified:
                    unverified.append({"sport": sport, "name": e["name"],
                                       "start_utc": e["start"].replace(".000Z", "Z"), "url": e["url"]})
        hubs.append(entry)
    return {
        "schema": "olbg4.board-zz.olbg/1",
        "capture_id": manifest["capture_id"],
        "hubs": hubs,
        "unverified_matches": sorted(unverified, key=lambda x: x["start_utc"])[:120],
    }


def build_review() -> dict:
    datasets, findings = [], []
    candidates = [
        ("data/master.json", lambda d: d.get("rows", [])),
        ("data/rows.json", lambda d: d.get("rows", []) if isinstance(d, dict) else d),
        ("data/board.json", lambda d: d.get("rows", []) if isinstance(d, dict) else d),
        ("data/matches.json", lambda d: d.get("matches", []) if isinstance(d, dict) else d),
        ("data/session-48de8c1d/desk.json", lambda d: d.get("rows", [])),
        ("data/session-e1161e0e/board.json", lambda d: d.get("rows", []) if isinstance(d, dict) else d),
        ("data/session-343754f2/desk.json", lambda d: d.get("rows", [])),
        ("data/session-0ed96fe7/desk.json", lambda d: d.get("rows", [])),
    ]
    today = NOW.strftime("%Y-%m-%d")
    for rel, getter in candidates:
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            doc = json.loads(p.read_text(encoding="utf-8"))
            rows = getter(doc) or []
        except Exception:  # noqa: BLE001
            findings.append({"id": f"ZZ-REV-{len(findings) + 1:02d}", "finding": f"{rel} is not parseable JSON",
                             "url": f"https://github.com/buffedlizard55-lab/OLBG4/blob/main/{rel}"})
            continue
        missing_src = stale = high_no_pred = 0
        sample_missing = sample_stale = None
        for r in rows:
            if not isinstance(r, dict):
                continue
            src = r.get("source")
            url = (r.get("source_url") or r.get("official_source_url")
                   or (src.get("url") if isinstance(src, dict) else "") or "")
            if not url:
                missing_src += 1
                sample_missing = sample_missing or r.get("id") or r.get("match")
            date = (r.get("date") or r.get("date_utc") or (r.get("start_utc") or "")[:10] or "")[:10]
            if date and date < today:
                stale += 1
                sample_stale = sample_stale or f"{r.get('id') or r.get('match')} ({date})"
            if (r.get("confidence") or "").lower() == "high" and not (r.get("prediction") or r.get("prediction_text")):
                high_no_pred += 1
        datasets.append({
            "dataset": rel, "rows": len(rows), "missing_source_url": missing_src,
            "stale_date": stale, "missing_prediction_on_high": high_no_pred,
            "note": (f"first row without an official URL: {sample_missing}" if sample_missing else
                     (f"first past-dated row: {sample_stale}" if sample_stale else "no defect of these kinds found")),
        })

    # targeted findings that a reader can verify by hand
    m = ROOT / "data/master.json"
    if m.exists():
        doc = json.loads(m.read_text(encoding="utf-8"))
        rows = doc.get("rows", [])
        nofix = sum(1 for r in rows if (r.get("home") or "") == "No fixture")
        past = sum(1 for r in rows if (r.get("date") or "") < today)
        unver = sum(1 for r in rows if r.get("build_verified") is False)
        missing_pred = sum(1 for r in rows if (r.get("confidence") or "").lower() == "high" and not r.get("prediction"))
        findings.append({
            "id": "ZZ-REV-01",
            "finding": f"data/master.json holds {len(rows)} rows; {nofix} are placeholder 'No fixture' rows, {past} are dated before "
                       f"today ({today}), {unver} are marked build_verified=false, and {missing_pred} High-confidence rows carry no prediction text.",
            "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json",
        })
        gen = doc.get("generated_on")
        findings.append({
            "id": "ZZ-REV-02",
            "finding": f"data/master.json declares generated_on {gen}; its row dates run past that stamp, so the file is a merged build "
                       f"rather than a single dated desk. Readers should treat the date column, not generated_on, as the fixture date.",
            "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/master.json",
        })
    findings.append({
        "id": "ZZ-REV-03",
        "finding": "Boards FB/EZ/BN grade their top five rows per sport as 'High' from a composite index, not from the brief's ≥70% "
                   "probability test; published examples sit at 55–69% (e.g. FB-PRED-01 is p=0.5942, −146). Their High labels are therefore "
                   "not comparable with the High labels on this desk, which enforce ≥70% and the −250…+10,000 window together.",
        "url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/data/session-48de8c1d/predictions.json",
    })
    findings.append({
        "id": "ZZ-REV-04",
        "finding": "Several session desks publish fixture rows whose start time has already passed relative to the repository snapshot "
                   "(2026-10-24T15:56Z), including golf and darts rows dated 24 Oct. This desk rebuilds its window from a fresh capture "
                   "instead of carrying them, and lists them here rather than editing another owner's file.",
        "url": "https://github.com/buffedlizard55-lab/OLBG4/tree/main/data",
    })
    return {"schema": "olbg4.board-zz.review/1", "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "datasets": datasets, "findings": findings}


CAPTURE_FLAGS = [
    ("ZZ-F01", "info", "High-confidence band arithmetic",
     "The brief asks for picks at ≥70% probability AND inside −250…+10,000. 70% is −233 and −250 is 71.43%, so both can only hold for "
     "probabilities in 70.00–71.43%. High picks on this desk are selected inside that band; every other row is graded Medium/Low. "
     "If the intended floor was −250 with no probability floor, say so and the grading rule can be relaxed to p ≥ 55% for the window.",
     "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/methodology.html"),
    ("ZZ-F02", "gap", "NBA fixture feed blocked",
     "cdn.nba.com returned HTTP 403 for both schedule endpoints and data.nba.com returned a redirect shell, so no NBA fixture could be "
     "verified from an official feed. No NBA row, price or prediction is published.",
     "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"),
    ("ZZ-F03", "gap", "Rugby Union: URC feed unavailable",
     "unitedrugby.com returned HTTP 404 on /fixtures-and-results, /standings, /fixtures and /match-centre; premiershiprugby.com renders "
     "fixtures client-side. Only the two Top 14 fixtures on top14.lnr.fr could be verified, so Rugby Union has 2 picks, not 5.",
     "https://www.unitedrugby.com/fixtures-and-results"),
    ("ZZ-F04", "gap", "Darts and snooker official pages are JavaScript shells",
     "pdc.tv returned the same 1,241,860-byte shell for six different URLs, and wst.tv/matches contains no fixture data in HTML. "
     "The OLBG darts listings observed in this capture are published on the OLBG page but carry no price and no pick.",
     "https://www.pdc.tv/tournament-hub/10870"),
    ("ZZ-F05", "gap", "Cricket has verified fixtures but no strength input",
     "Cricket Australia's official feed supplied 14 upcoming fixtures with start times, but the ICC team-ranking endpoints returned 404, "
     "so no team strength could be read from an official page. The fixtures are listed on Matches with no line and no pick.",
     "https://www.cricket.com.au/matches"),
    ("ZZ-F06", "gap", "Golf, Gaelic, Greyhounds, Handball, Motor Racing, Rugby League not priced",
     "Each sport's official fixture/strength feed was client-side rendered or returned an error in this capture (details on Coverage). "
     "Nothing was estimated to fill the gap.",
     "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/coverage.html"),
    ("ZZ-F07", "note", "MLB start times are stored as 00:00Z",
     "The MLB Stats API returns World Series games with gameDate 2026-10-25T00:00:00Z, which is the US evening of 24 October in UTC terms. "
     "Kick-off times for baseball rows should be read as the API value, which is the official field, not as a local first-pitch clock.",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-24&endDate=2026-11-09"),
    ("ZZ-F08", "note", "No official injury feed captured",
     "No roster/injury endpoint was part of this capture, so predictions make no injury claim. Where an official feed does name a probable "
     "pitcher (MLB) it is quoted; otherwise the text says nothing rather than guessing.",
     "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/predictions.html"),
    ("ZZ-F09", "note", "Coverage is 9 of 15 sports with fixtures and 7 with own lines",
     "Ice Hockey, Basketball, Baseball, Tennis, Volleyball, Rugby Union and (fixtures only) Cricket, plus the OLBG listing for the rest. "
     "Five written predictions exist only where five High picks exist; Rugby Union has two.",
     "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/coverage.html"),
]


def build_flags(desk: dict, predictions: dict, review: dict, olbg: dict, manifest: dict) -> dict:
    items = [{"id": i, "severity": s, "item": t, "detail": d, "url": u} for i, s, t, d, u in CAPTURE_FLAGS]

    for rec in manifest["records"]:
        if rec.get("status") == 200:
            continue
        items.append({
            "id": f"ZZ-CAP-{rec['id'][:24]}",
            "severity": "capture",
            "item": f"{rec['sport']} target {rec['id']} returned {rec.get('status')}",
            "detail": (rec.get("error") or "no payload") + f" — {rec['url']}",
            "url": rec["url"],
        })

    for s, rs in sorted(desk["summary"]["by_sport"].items()):
        if rs["fixtures"] and rs["high"] < 5:
            items.append({
                "id": f"ZZ-HIGH-{s.replace(' ', '').upper()}",
                "severity": "coverage",
                "item": f"{s}: {rs['high']} High picks (brief target 5 per sport)",
                "detail": f"{rs['fixtures']} fixtures priced, but only {rs['high']} landed in the 70.00–71.43% band that satisfies both of "
                          f"the brief's High tests. The rest are Medium/Low and receive no written prediction.",
                "url": "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/coverage.html",
            })

    for sk in predictions.get("skipped", [])[:20]:
        items.append({
            "id": f"ZZ-PRED-{sk['row'][:24]}",
            "severity": "note",
            "item": f"High row without a prediction: {sk['row']}",
            "detail": sk["reason"],
            "url": "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/predictions.html",
        })

    if olbg.get("unverified_matches"):
        items.append({
            "id": "ZZ-OLBG-01",
            "severity": "unverified",
            "item": f"{len(olbg['unverified_matches'])} OLBG-listed matches have no official verification",
            "detail": "The pairing and kick-off come from OLBG's own hub page. No official feed in this capture confirms them, so they are "
                      "published on the OLBG page without a price or a pick.",
            "url": "https://buffedlizard55-lab.github.io/OLBG4/session-edffdbc6/olbg.html",
        })

    for f in review["findings"][:6]:
        items.append({"id": f["id"] + "-REPO", "severity": "repo-defect", "item": f["finding"][:110] + "…",
                      "detail": f["finding"], "url": f.get("url", "")})

    return {"schema": "olbg4.board-zz.flagged/1", "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": items}


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    preds = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    fixtures = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))["fixtures"]
    cap_dir = DATA / "capture" / desk["capture_id"]
    manifest = json.loads((cap_dir / "manifest.json").read_text(encoding="utf-8"))

    olbg = build_olbg(manifest, cap_dir, fixtures)
    (DATA / "olbg.json").write_text(json.dumps(olbg, indent=1) + "\n", encoding="utf-8")

    review = build_review()
    (DATA / "review.json").write_text(json.dumps(review, indent=1) + "\n", encoding="utf-8")

    flags = build_flags(desk, preds, review, olbg, manifest)
    (DATA / "flagged.json").write_text(json.dumps(flags, indent=1) + "\n", encoding="utf-8")

    print(f"olbg: {len(olbg['hubs'])} hubs, {sum(h['matches_listed'] for h in olbg['hubs'])} match objects, "
          f"{len(olbg['unverified_matches'])} unverified upcoming")
    print(f"review: {len(review['datasets'])} datasets, {len(review['findings'])} findings")
    print(f"flags: {len(flags['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Read-only, row-by-row audit of the canonical and current peer datasets."""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from common import DATA, ROOT, EvidenceStore, american, norm


def load_json(path: Path):
    return json.loads(path.read_text())


def dump_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

OFFICIAL_HOSTS = {
    "www.nba.com", "cdn.nba.com", "stats.nba.com", "api-web.nhle.com", "www.nhl.com",
    "statsapi.mlb.com", "www.mlb.com", "www.atptour.com", "www.protennislive.com",
    "www.wtatennis.com", "api.wtatennis.com", "wtafiles.wtatennis.com",
    "www.icc-cricket.com", "www.cricket.com.au", "www.cricket.co.za", "www.ecb.co.uk",
    "cricketireland.ie", "www.nzc.nz", "www.pdc.tv", "participants.darts.web.gc.pdcservices.co.uk",
    "matches.darts.web.gc.pdcservices.co.uk", "www.wst.tv", "www.world.rugby",
    "rankings.snooker.web.gc.wstservices.co.uk", "matches.snooker.web.gc.wstservices.co.uk",
    "events.snooker.web.gc.wstservices.co.uk", "www.unitedrugby.com", "stats.unitedrugby.com",
    "www.premiershiprugby.com", "premrugby.com", "www.premrugby.com", "www.nrl.com", "top14.lnr.fr",
    "prod2.lnr.fr", "ehfcl.eurohandball.com", "www.eurohandball.com", "www.ihf.info",
    "www.euroleaguebasketball.net", "api-live.euroleague.net", "www.championsleague.basketball",
    "www.fivb.com", "en.volleyballworld.com", "www.legavolley.it", "www.legavolleyfemminile.it",
    "www.plusliga.pl", "www.tauron1liga.pl", "www.shl.se", "www.ice.hockey", "www.pgatour.com",
    "www.lpga.com", "www.formula1.com", "www.motogp.com", "gaacork.ie", "www.galwaygaa.ie",
    "munster.gaa.ie", "www.gbgb.org.uk", "www.nottingham-greyhounds.co.uk",
    "www.icc-cricket.com", "www.pcb.com.pk", "www.worldathletics.org", "www.superleague.co.uk",
}

FALLBACK_LINKS = {
    "Golf": "https://www.pgatour.com/schedule", "Volleyball": "https://www.fivb.com/volleyball-calendar/",
    "Rugby Union": "https://www.world.rugby/fixtures-results", "Cricket": "https://www.icc-cricket.com/fixtures-results",
    "Snooker": "https://www.wst.tv/match-centre", "Darts": "https://www.pdc.tv/tournaments",
    "Baseball": "https://www.mlb.com/schedule", "Gaelic Football": "https://gaacork.ie/fixtures/",
    "Gaelic Sports": "https://gaacork.ie/fixtures/", "Greyhounds": "https://www.gbgb.org.uk/racing/",
    "Tennis": "https://www.atptour.com/en/scores/current", "Motor Racing": "https://www.formula1.com/en/racing/2026",
    "Handball": "https://ehfcl.eurohandball.com/", "Ice Hockey": "https://www.nhl.com/schedule",
    "Basketball": "https://www.nba.com/schedule", "Rugby League": "https://www.superleague.co.uk/fixtures",
}


def words(text: object) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", str(text or ""), re.UNICODE))


def start_value(row: dict, dataset: str) -> str:
    if dataset == "integrated":
        return str(row.get("start_utc") or "")
    return str(row.get("date") or row.get("time_label") or "")


def source_value(row: dict, dataset: str) -> str:
    if dataset == "integrated":
        return str(row.get("official_url") or row.get("olbg", {}).get("olbg_url") or "")
    if dataset == "board":
        return str(row.get("olbg_url") or "")
    return str(row.get("source_url") or row.get("olbg_url") or "")


def matchup(row: dict, dataset: str) -> str:
    if dataset == "integrated":
        return str(row.get("matchup") or f"{row.get('side_a','')} vs {row.get('side_b','')}")
    return str(row.get("match") or f"{row.get('home','')} vs {row.get('away','')}")


def prediction_value(row: dict) -> str:
    p = row.get("prediction") or ""
    if isinstance(p, dict):
        return str(p.get("text") or p.get("prediction") or "")
    return str(p)


def confidence_value(row: dict) -> str:
    return str(row.get("confidence") or "").strip().title()


def add(rec: dict, code: str, severity: str, message: str, url: str = "") -> None:
    rec["issues"].append({"code": code, "severity": severity, "message": message, "manual_url": url or rec["manual_url"]})


def close(a: float, b: float, tolerance: float = .015) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance


def audit_integrated_markets(row: dict, rec: dict) -> None:
    for key, market in (row.get("markets") or {}).items():
        if not isinstance(market, dict):
            add(rec, "market-schema", "high", f"Market {key} is not an object.")
            continue
        selections = market.get("selections") or []
        if len(selections) != 2:
            add(rec, "market-two-sided", "high", f"Market {key} does not contain exactly two selections.")
            continue
        probs = []
        for sel in selections:
            try:
                p = float(sel.get("fair_prob")); dec = float(sel.get("fair_decimal")); am = float(sel.get("fair_american"))
            except (TypeError, ValueError):
                add(rec, "market-missing-value", "high", f"Market {key} has a selection without complete fair-price fields.")
                continue
            probs.append(p)
            if not 0 < p < 1:
                add(rec, "market-probability", "high", f"Market {key} has probability {p} outside (0,1).")
                continue
            if not close(dec, 1 / p):
                add(rec, "market-decimal", "high", f"Market {key} decimal {dec} does not reconcile to probability {p}.")
            if abs(am - american(p)) > 2:
                add(rec, "market-american", "high", f"Market {key} American price {am} does not reconcile to probability {p}.")
        if len(probs) == 2 and not close(sum(probs), 1.0, 1e-6):
            add(rec, "market-prob-sum", "high", f"Market {key} probabilities sum to {sum(probs):.6f}, not 1.")


def run(cutoff: datetime | None = None) -> dict:
    cutoff = cutoff or EvidenceStore().cutoff
    datasets = [
        ("master", "data/master.json", "rows"),
        ("board", "data/board.json", "rows"),
        ("integrated", "data/session-509d544b/desk.json", "rows"),
    ]
    records = []
    seen_ids = defaultdict(list)
    seen_matches = defaultdict(list)
    prose = defaultdict(list)
    for dataset, path, key in datasets:
        doc = load_json(ROOT / path)
        for position, row in enumerate(doc.get(key, []), 1):
            rid = str(row.get("id") or f"{dataset}-line-{position}")
            sport = str(row.get("sport") or "")
            url = source_value(row, dataset)
            rec = {
                "dataset": dataset, "dataset_path": path, "row_number": position, "row_id": rid,
                "sport": sport, "matchup": matchup(row, dataset), "start": start_value(row, dataset),
                "manual_url": url or FALLBACK_LINKS.get(sport, "https://www.olbg.com/betting-tips"),
                "source_url": url, "issues": [], "checks": 0,
            }
            records.append(rec)
            seen_ids[(dataset, rid)].append(rec)
            seen_matches[(dataset, sport, norm(matchup(row, dataset)), start_value(row, dataset)[:10])].append(rec)
            rec["checks"] += 4
            if not row.get("id"):
                add(rec, "missing-id", "high", "Record has no stable identifier.")
            if not sport:
                add(rec, "missing-sport", "high", "Record has no sport classification.")
            if not url:
                add(rec, "missing-source-link", "high", "No official or source URL is attached; use the supplied governing-body review link.")
            else:
                host = urlparse(url).netloc.lower()
                if dataset == "integrated" and host not in OFFICIAL_HOSTS:
                    add(rec, "source-domain-review", "high", f"Integrated desk source host {host or '(missing)'} is not in the official-host audit registry.")
                if dataset == "master" and row.get("verified") and host not in OFFICIAL_HOSTS:
                    add(rec, "official-claim-source", "high", f"Official-source status is attached to non-registry host {host or '(missing)'}.")
            conf = confidence_value(row)
            pred = prediction_value(row)
            if conf == "High":
                rec["checks"] += 4
                if not pred:
                    add(rec, "high-without-prose", "high", "High-confidence record has no written prediction.")
                elif words(pred) < 30:
                    add(rec, "high-short-prose", "high", f"High-confidence prediction has {words(pred)} words; minimum is 30.")
                if re.search(r"\b(model|verified)\b", pred, re.I):
                    add(rec, "public-prose-term", "medium", "Public prediction contains an internal-only term.")
                if not (row.get("pick") or row.get("match_winner_pick") or row.get("featured_pick")):
                    add(rec, "high-without-pick", "high", "High-confidence record has no explicit selection.")
            if pred:
                prose[(dataset, re.sub(r"\s+", " ", pred.strip().lower()))].append(rec)
            start = start_value(row, dataset)
            if re.match(r"^2026-\d\d-\d\dT", start):
                try:
                    dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    if dt < cutoff and dataset == "integrated":
                        add(rec, "started-before-cutoff", "medium", f"Integrated upcoming-desk start {start} precedes the C10 evidence cutoff.")
                except ValueError:
                    add(rec, "invalid-start", "high", f"Start value {start!r} is not parseable.")
            if dataset == "board":
                rec["checks"] += 2
                try:
                    p = float(row.get("our_prob")); dec = float(row.get("our_price"))
                    if not 0 < p < 1 or not close(dec, 1 / p):
                        add(rec, "board-price-math", "high", f"Board probability {p} and decimal price {dec} do not reconcile.")
                except (TypeError, ValueError):
                    if row.get("our_prob") is not None or row.get("our_price") is not None:
                        add(rec, "board-price-missing", "high", "Board price fields are incomplete or non-numeric.")
                if conf == "High" and url and "olbg.com" in urlparse(url).netloc:
                    add(rec, "high-olbg-only", "high", "High-confidence selection is supported only by an OLBG link in this record.")
            if dataset == "integrated":
                rec["checks"] += 1
                audit_integrated_markets(row, rec)
    for group in seen_ids.values():
        if len(group) > 1:
            for rec in group:
                add(rec, "duplicate-id", "high", f"Identifier occurs {len(group)} times in its dataset.")
    for group in seen_matches.values():
        if len(group) > 1 and group[0]["matchup"].strip(" vs"):
            for rec in group:
                add(rec, "duplicate-match-day", "medium", f"Same normalized matchup/date occurs {len(group)} times; inspect for a genuine doubleheader or duplication.")
    for group in prose.values():
        if len(group) > 1:
            for rec in group:
                add(rec, "duplicate-prose", "high", f"Identical prediction text occurs {len(group)} times in its dataset.")
    findings = [dict(issue, dataset=r["dataset"], dataset_path=r["dataset_path"], row_number=r["row_number"],
                     row_id=r["row_id"], sport=r["sport"], matchup=r["matchup"], start=r["start"])
                for r in records for issue in r["issues"]]
    counts = Counter(x["code"] for x in findings)
    severities = Counter(x["severity"] for x in findings)
    return {
        "schema": "c10-repository-review/v1", "generated_from_cutoff": cutoff.isoformat().replace("+00:00", "Z"),
        "method": "Read-only mechanical audit of every record in the canonical master, legacy board and current integrated peer desk. Links are manual-review destinations, not claims that a remote page was re-fetched.",
        "datasets": [{"name": n, "path": p, "records": sum(r["dataset"] == n for r in records)} for n, p, _ in datasets],
        "summary": {"records_reviewed": len(records), "clean_records": sum(not r["issues"] for r in records),
                    "records_with_findings": sum(bool(r["issues"]) for r in records), "findings": len(findings),
                    "by_code": dict(sorted(counts.items())), "by_severity": dict(sorted(severities.items()))},
        "records": records, "findings": findings,
        "sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for _, p, _ in datasets},
    }


def write() -> dict:
    review = run()
    dump_json(DATA / "review.json", review)
    print(f"reviewed {review['summary']['records_reviewed']} records; {review['summary']['findings']} findings")
    return review


if __name__ == "__main__":
    write()

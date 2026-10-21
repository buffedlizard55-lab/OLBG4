"""Verification gate.

Nothing reaches the published JSON unless it passes through here. The rules are the
ones the owner asked for:

* every row needs at least one source link on an official league domain, otherwise the
  row is dropped and an item is raised on the Flagged for Review page;
* values that cannot be confirmed are left blank and flagged — never inferred;
* every published probability, price and confidence grade is range-checked;
* every high-confidence prediction is linted for length, explicit selection, banned
  language and cross-prediction similarity.

`run.py --strict` exits non-zero when a hard check fails (missing official source,
malformed row, out-of-range probability). Soft findings (missing optional context,
stale-but-official data, provider coverage gaps) are published on the review page and
never block the build.
"""
from __future__ import annotations

import urllib.parse
from collections import Counter
from datetime import datetime

from . import config
from .predictions import lint
from .records import validate_game


CONF_RANK = {"high": 3, "medium": 2, "low": 1}


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, *, severity: str, category: str, detail: str, fixture: dict | None = None,
            field: str | None = None, value=None, source_urls: list[str] | None = None,
            action: str = "published") -> None:
        item = {
            "id": f"flag-{len(self.items) + 1:03d}",
            "severity": severity,
            "category": category,
            "detail": detail,
            "field": field,
            "value": value,
            "action": action,
            "source_urls": source_urls or (fixture.get("source_urls") if fixture else []) or [],
            "sport": (fixture or {}).get("sport"),
            "fixture_id": (fixture or {}).get("id"),
            "match": f"{fixture['away']['name']} at {fixture['home']['name']}" if fixture else None,
            "start_utc": (fixture or {}).get("start_utc"),
        }
        self.items.append(item)


def _host(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower()
    except Exception:  # noqa: BLE001
        return ""


def is_official(url: str, sport: str) -> bool:
    host = _host(url)
    if not host:
        return False
    for domain in config.SPORTS[sport]["official_domains"]:
        d = domain.lower()
        if host == d or host.endswith("." + d):
            return True
    return False


def official_sources(fixture: dict) -> list[str]:
    return [u for u in fixture.get("source_urls", []) if is_official(u, fixture["sport"])]


def check_fixtures(fixtures: list[dict], findings: Findings) -> list[dict]:
    """Drop rows without an official source; flag incomplete optional fields."""
    kept: list[dict] = []
    seen_ids: set[str] = set()
    seen_slots: dict[str, str] = {}
    for fx in fixtures:
        problems = validate_game(fx)
        if fx["id"] in seen_ids:
            findings.add(severity="error", category="duplicate_fixture",
                         detail=f"duplicate fixture id {fx['id']} discarded", fixture=fx,
                         action="excluded")
            continue
        if problems:
            findings.add(severity="error", category="malformed_row",
                         detail="; ".join(problems), fixture=fx, action="excluded")
            continue
        off = official_sources(fx)
        if config.REQUIRE_OFFICIAL_SOURCE and not off:
            findings.add(severity="error", category="unverified_source",
                         detail="no source URL on an official league domain; row excluded",
                         fixture=fx, action="excluded")
            continue
        slot = f"{fx['home']['id']}|{fx['away']['id']}|{fx['start_utc']}"
        if slot in seen_slots:
            findings.add(severity="warning", category="duplicate_slot",
                         detail=f"same teams and start time as {seen_slots[slot]}", fixture=fx)
        seen_slots[slot] = fx["id"]
        seen_ids.add(fx["id"])
        fx["official_source_urls"] = off
        fx["primary_source"] = off[0]

        if not fx["home"].get("record") or not fx["away"].get("record"):
            findings.add(severity="warning", category="missing_record",
                         detail="league did not publish a win-loss record for one or both teams; "
                                "field left blank", fixture=fx, field="record",
                         action="published_blank")
        if not fx.get("venue"):
            findings.add(severity="warning", category="missing_venue",
                         detail="venue not published by the league feed; field left blank",
                         fixture=fx, field="venue", action="published_blank")
        ctx = fx.get("context") or {}
        if fx["sport"] == "baseball" and not (
            ctx.get("home_probable_pitcher") and ctx.get("away_probable_pitcher")
        ):
            findings.add(severity="info", category="missing_probable_pitcher",
                         detail="probable pitchers not yet announced; left blank rather than guessed",
                         fixture=fx, field="probable_pitcher", action="published_blank")
        status = str(fx.get("status") or "").lower()
        if any(word in status for word in ("postpon", "suspend", "cancel")):
            findings.add(severity="warning", category="irregular_status",
                         detail=f"league status is {fx['status']!r}", fixture=fx, field="status")
        if ctx.get("double_header"):
            findings.add(severity="info", category="doubleheader",
                         detail="part of a doubleheader; game number recorded", fixture=fx)
        kept.append(fx)
    return kept


def check_analysis(analysis: list[dict], findings: Findings) -> list[dict]:
    valid: list[dict] = []
    for row in analysis:
        fx = row["fixture"]
        markets = row.get("analysis", {}).get("markets", {})
        ok = True
        for mkey, market in markets.items():
            sels = market.get("selections") or []
            if len(sels) < 2:
                findings.add(severity="error", category="incomplete_market",
                             detail=f"{mkey} has fewer than two selections", fixture=fx,
                             action="excluded")
                ok = False
                continue
            total = sum(s["prob"] for s in sels)
            if abs(total - 1.0) > 0.01:
                findings.add(severity="error", category="probability_sum",
                             detail=f"{mkey} probabilities sum to {total:.4f}", fixture=fx,
                             action="excluded")
                ok = False
            for s in sels:
                if not 0.0 < s["prob"] < 1.0:
                    findings.add(severity="error", category="probability_range",
                                 detail=f"{mkey}/{s['name']} probability {s['prob']}", fixture=fx,
                                 action="excluded")
                    ok = False
                if s["price_decimal"] <= 1.0:
                    findings.add(severity="error", category="price_range",
                                 detail=f"{mkey}/{s['name']} price {s['price_decimal']}", fixture=fx,
                                 action="excluded")
                    ok = False
        picks = [row.get("analysis", {}).get("winner_pick")] + \
                row.get("analysis", {}).get("market_picks", [])
        for pick in picks:
            if not pick:
                continue
            if pick.get("confidence") not in ("low", "medium", "high"):
                findings.add(severity="error", category="confidence_value",
                             detail=f"bad confidence {pick.get('confidence')!r}", fixture=fx,
                             action="excluded")
                ok = False
            if not pick.get("selection"):
                findings.add(severity="error", category="pick_without_selection",
                             detail="pick has no selection", fixture=fx, action="excluded")
                ok = False
        if ok:
            valid.append(row)
    return valid


def check_predictions(predictions: list[dict], findings: Findings,
                      fixtures_by_id: dict[str, dict]) -> list[dict]:
    problems = lint(predictions)
    bad_ids = set()
    for problem in problems:
        fid = problem.split(":", 1)[0]
        fx = fixtures_by_id.get(fid)
        findings.add(severity="warning", category="prediction_lint", detail=problem, fixture=fx,
                     action="prediction withdrawn")
        bad_ids.add(fid)
    kept = []
    for p in predictions:
        if p["fixture_id"] in bad_ids:
            # keep the pick, withdraw the written prediction rather than publish poor copy
            p["text"] = ""
            p["withdrawn"] = True
            p["withdrawn_reason"] = "failed prediction lint; see Flagged for Review"
        kept.append(p)
    return kept


def check_schedule_horizon(analysis: list[dict], start: datetime, end: datetime,
                           findings: Findings) -> None:
    for row in analysis:
        fx = row["fixture"]
        from .records import parse_iso
        try:
            dt = parse_iso(fx["start_utc"])
        except Exception:  # noqa: BLE001
            findings.add(severity="error", category="unparseable_start",
                         detail="start_utc could not be parsed", fixture=fx, action="excluded")
            continue
        if not (start <= dt < end):
            findings.add(severity="error", category="outside_window",
                         detail=f"start {fx['start_utc']} outside publishing window", fixture=fx,
                         action="excluded")


def summary(findings: Findings, fixtures: list[dict], analysis: list[dict],
            predictions: list[dict]) -> dict:
    counts = Counter(f["category"] for f in findings.items)
    by_severity = Counter(f["severity"] for f in findings.items)
    excluded = [f for f in findings.items if f.get("action") == "excluded"]
    unresolved = [
        f for f in findings.items
        if f["severity"] == "error" and f.get("action") != "excluded"
    ]
    return {
        "fixtures_checked": len(fixtures),
        "markets_checked": sum(len(r["analysis"]["markets"]) for r in analysis),
        "predictions_checked": len(predictions),
        "predictions_published": sum(1 for p in predictions if not p.get("withdrawn")),
        "findings": len(findings.items),
        "findings_by_severity": dict(by_severity),
        "findings_by_category": dict(counts),
        "rows_excluded": len(excluded),
        "excluded_ratio": round(len(excluded) / max(1, len(fixtures) + len(excluded)), 4),
        "hard_failures": len(unresolved),
    }

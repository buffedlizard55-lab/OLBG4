#!/usr/bin/env python3
"""Fail-closed verification for Board AF data, prose, sources and static pages."""
from __future__ import annotations

import hashlib
import itertools
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from author import author
from build import build, build_candidates
from common import DATA, ROOT, SITE, Capture, american, focus_price, load, slug, words
from render import render
from review import review

OFFICIAL_HOSTS = {
    "api-web.nhle.com", "liiga.fi", "api-live.euroleague.net", "statsapi.mlb.com",
    "api.wtatennis.com", "esports-api.lolesports.com", "www.euroleaguebasketball.net",
}
EXCLUDED = {"soccer", "boxing", "ufc", "mma", "football", "american football",
            "hurling", "horse racing", "cycling", "specials"}


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        for key in ("href", "src"):
            if values.get(key):
                self.links.append(values[key])


def trigrams(text: str) -> set[tuple[str, str, str]]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return set(zip(tokens, tokens[1:], tokens[2:]))


def verify() -> None:
    checks = 0

    def require(condition: bool, message: str) -> None:
        nonlocal checks
        checks += 1
        if not condition:
            raise AssertionError(message)

    cap = Capture()
    require(cap.verify_hashes() == len(cap.items), "Not every capture response hash-verified")
    desk = load(DATA / "desk.json")
    rows = desk["rows"]
    predictions = load(DATA / "predictions.json")["predictions"]
    candidates_doc = load(DATA / "prediction_candidates.json")["candidates"]
    candidates = build_candidates(rows)
    coverage = load(DATA / "coverage.json")["coverage"]
    listing = load(DATA / "olbg_listing.json")
    flagged = load(DATA / "flagged.json")["flags"]
    sources = load(DATA / "sources.json")["sources"]
    verification = load(DATA / "verification.json")["rows"]
    review_doc = load(DATA / "repo_review.json")
    live_doc = load(DATA / "live_checks.json")
    by_id = {row["id"]: row for row in rows}
    require(len(by_id) == len(rows), "Duplicate fixture IDs")
    require(len(verification) == len(rows), "Verification register row mismatch")
    require(len(sources) == len(cap.items), "Source registry incomplete")
    require(desk["capture_id"] == cap.capture_id, "Desk is not from latest capture")
    require(listing["capture_id"] == cap.capture_id, "OLBG listing is not from latest capture")

    for row in rows:
        require(row["sport"].lower() not in EXCLUDED, f"Excluded sport published: {row['sport']}")
        require(bool(row["official_url"]), f"Missing official URL: {row['id']}")
        require(urlparse(row["official_url"]).netloc in OFFICIAL_HOSTS, f"Non-official row source: {row['id']}")
        require(row["verification"].startswith("Official fixture confirmed"), f"Bad verification state: {row['id']}")
        require(not row["venue"] or isinstance(row["venue"], str), f"Bad venue: {row['id']}")
        if not row["venue"]:
            require(any(f["code"] == "VENUE_UNCONFIRMED" for f in row["flags"]), f"Blank venue not flagged: {row['id']}")
        if row["start_utc"]:
            require(cap.cutoff < row["start_utc"] <= desk["window_end_utc"], f"Stale/out-of-window fixture: {row['id']}")
        else:
            require(any(f["code"] == "START_UNCONFIRMED" for f in row["flags"]), f"Blank start not flagged: {row['id']}")
        evidence_ids = set()
        for evidence in row["evidence"]:
            evidence_ids.add(evidence["id"])
            require(evidence["http_status"] == 200, f"Failed source used: {row['id']} {evidence['id']}")
            require(evidence["sha256"] == cap.items[evidence["id"]]["sha256"], f"Evidence hash mismatch: {row['id']}")
            require((cap.path / cap.items[evidence["id"]]["file"]).exists(), f"Raw evidence missing: {evidence['id']}")
        for fact_type in ("recent_results", "player_facts"):
            for fact in row[fact_type]:
                require(bool(fact["url"]), f"Fact URL missing: {row['id']}")
                require(urlparse(fact["url"]).netloc in OFFICIAL_HOSTS, f"Fact source not official: {row['id']}")
                if not fact.get("live_page_check"):
                    require(fact["source_id"] in evidence_ids or fact["source_id"] in cap.items,
                            f"Fact not tied to capture/live evidence: {row['id']}")
        if not row["markets"]:
            require(row["pick"] is None, f"Unpriced row has pick: {row['id']}")
            require(not row["prediction_keys"], f"Unpriced row has prediction: {row['id']}")
            require(bool(row["flags"]), f"Unpriced row not flagged: {row['id']}")
            continue
        require(bool(row["pick"]), f"Priced row has no match-winner pick: {row['id']}")
        for key, market in row["markets"].items():
            require(len(market["selections"]) == 2, f"Non-two-way market: {row['id']} {key}")
            probability_sum = sum(s["probability"] for s in market["selections"])
            require(abs(probability_sum - 1.0) < 0.00001, f"Probability sum != 1: {row['id']} {key}")
            for selection in market["selections"]:
                require(0 < selection["probability"] < 1, f"Bad probability: {row['id']}")
                require(selection["decimal"] == round(1 / selection["probability"], 3), f"Bad fair decimal: {row['id']}")
                require(selection["american"] == american(selection["decimal"]), f"Bad American price: {row['id']}")
        pick = row["pick"]
        chosen = max(row["markets"]["match_winner"]["selections"], key=lambda s: s["probability"])
        require(pick["selection"] == chosen["label"], f"Wrong match-winner selection: {row['id']}")
        expected = "High" if chosen["probability"] >= 0.70 and row["high_evidence"] else ("Medium" if chosen["probability"] >= 0.58 else "Low")
        require(pick["confidence"] == expected, f"Confidence mismatch: {row['id']}")
        require(pick["focus_eligible"] == (expected == "High" and focus_price(chosen)), f"Primary focus mismatch: {row['id']}")

    require(len(candidates) == len(candidates_doc), "Candidate count changed between builds")
    candidate_keys = {c["key"] for c in candidates}
    require(candidate_keys == {c["key"] for c in candidates_doc}, "Candidate keys changed between builds")
    require(candidate_keys == {p["key"] for p in predictions}, "Every High candidate must have one prediction")
    require(len(predictions) == len(candidate_keys), "Duplicate prediction keys")
    require(sum(c["focus_eligible"] for c in candidates) == desk["summary"]["high_focus"], "Focus summary mismatch")
    for candidate in candidates:
        require(candidate["probability"] >= 0.70, f"High candidate below 70%: {candidate['key']}")
        if candidate["focus_eligible"]:
            require(focus_price(candidate), f"Focus candidate outside price window: {candidate['key']}")
        else:
            require(not focus_price(candidate), f"Non-focus candidate inside price window: {candidate['key']}")

    texts = set()
    for prediction in predictions:
        row = by_id[prediction["fixture_id"]]
        market = next(m for m in row["markets"].values() if m["market"] == prediction["market"])
        source_selection = next(s for s in market["selections"] if s["label"] == prediction["selection"])
        require(source_selection["probability"] == prediction["probability"], f"Prediction probability drift: {prediction['key']}")
        require(source_selection["decimal"] == prediction["decimal"], f"Prediction decimal drift: {prediction['key']}")
        require(source_selection["american"] == prediction["american"], f"Prediction American drift: {prediction['key']}")
        require(prediction["word_count"] == words(prediction["text"]) and prediction["word_count"] >= 30,
                f"Prediction word count: {prediction['key']}")
        require(prediction["text"] not in texts, f"Duplicate prose: {prediction['key']}")
        texts.add(prediction["text"])
        selected_team = next(c["selected_team"] for c in candidates if c["key"] == prediction["key"])
        require(selected_team and selected_team in prediction["text"], f"Selected side absent from prose: {prediction['key']}")
        if "+1.5" in prediction["selection"]:
            require("+1.5" in prediction["text"], f"Handicap not explicit: {prediction['key']}")
        else:
            require(any(x in prediction["text"].lower() for x in ("moneyline", "to win", "home win", "straight win", "outright")),
                    f"Winner not explicit: {prediction['key']}")
        require(any(r.get("team") == selected_team for r in row["recent_results"]), f"Selected-side recent result absent: {prediction['key']}")
        require(bool(row["player_facts"]), f"Player evidence absent: {prediction['key']}")
        require(len(prediction["facts"]) >= 4, f"Fact panel incomplete: {prediction['key']}")
        evidence_text = ' '.join(f["text"] for f in prediction["facts"]) + ' ' + prediction["selection"]
        normalised = evidence_text.lower().replace(",", "")
        for token in re.findall(r'(?<![\w+])\d[\d,]*(?:\.\d+)?', prediction["text"]):
            require(token.replace(",", "") in normalised, f"Numeric claim not in evidence: {prediction['key']} -> {token}")
        for fact in prediction["facts"]:
            require(bool(fact["text"]) and bool(fact["url"]), f"Blank fact/source: {prediction['key']}")
            require(urlparse(fact["url"]).netloc in OFFICIAL_HOSTS, f"Non-official prediction fact: {prediction['key']}")
    for a, b in itertools.combinations(predictions, 2):
        ga, gb = trigrams(a["text"]), trigrams(b["text"])
        similarity = len(ga & gb) / max(1, len(ga | gb))
        require(similarity < 0.25, f"Repetitive prediction pair: {a['key']} / {b['key']} = {similarity:.3f}")

    upcoming = [e for e in listing["events"] if e["upcoming_at_capture"]]
    unmatched = {e["listing_id"] for e in upcoming if e["official_reconciliation"] != "matched"}
    flagged_unmatched = {f["row_id"] for f in flagged if f["code"] == "OLBG_UNMATCHED"}
    require(unmatched == flagged_unmatched, "Unmatched OLBG/flag set mismatch")
    unpriced = {r["id"] for r in rows if not r["markets"]}
    require(unpriced <= {f["row_id"] for f in flagged if f["code"] == "UNPRICED"}, "Unpriced row missing flag")
    require(not any(f["code"] == "PREDICTION_NOT_PUBLISHED" for f in flagged), "High prediction missing")
    require(len(coverage) == 17, "OLBG sport category count mismatch")
    for item in coverage:
        sport_rows = [r for r in rows if r["sport"] == item["sport"]]
        require(item["official_fixtures"] == len(sport_rows), f"Coverage fixture count: {item['sport']}")
        require(item["priced"] == sum(bool(r["markets"]) for r in sport_rows), f"Coverage priced count: {item['sport']}")
        focus_written = {p["fixture_id"] for p in predictions if p["sport"] == item["sport"] and p["focus_eligible"]}
        require(item["five_pick_target_shortfall"] == max(0, 5 - len(focus_written)), f"Five-pick shortfall: {item['sport']}")

    require(review_doc["rows_checked"] == {"data/master.json": 336,
            "data/session-22ca2e95/desk.json": 246, "data/session-f0622b6e/desk.json": 233}, "Peer review row inventory changed")
    require(any(f["code"] == "DIRECT_RULE_CONTRADICTION" and f["row_id"] == "ae_038" for f in review_doc["findings"]),
            "Direct peer probability contradiction missing")
    live_ids = {c["id"] for c in live_doc["checks"]}
    for row in rows:
        for fact in row["player_facts"]:
            if fact.get("live_page_check"):
                require(fact["source_id"] in live_ids, f"Live page fact not registered: {row['id']}")

    expected_pages = {"index.html", "entries.html", "markets.html", "predictions.html", "coverage.html",
                      "verification.html", "sources.html", "olbg.html", "flagged.html", "review.html",
                      "analysis.html", "methodology.html"} | {f"sports/{c['slug']}.html" for c in coverage}
    for relative in sorted(expected_pages):
        path = SITE / relative
        require(path.exists() and path.stat().st_size > 1000, f"Missing/thin page: {relative}")
        parser = Links()
        content = path.read_text(encoding="utf-8")
        parser.feed(content)
        require("TODO" not in content and "PLACEHOLDER" not in content, f"Placeholder text: {relative}")
        require("main" in parser.ids, f"Main landmark missing: {relative}")
        for target in parser.links:
            if target.startswith(("https://", "http://", "mailto:", "data:", "javascript:")):
                continue
            if target.startswith("#"):
                require(target[1:] in parser.ids, f"Broken fragment {relative} -> {target}")
                continue
            clean = unquote(target.split("#")[0].split("?")[0])
            if not clean:
                continue
            resolved = (path.parent / clean).resolve()
            require(resolved.exists(), f"Broken local link {relative} -> {target} ({resolved})")
            require(ROOT in resolved.parents or resolved == ROOT, f"Link escapes repository: {relative} -> {target}")
    require((SITE / "assets" / "style.css").exists(), "Stylesheet missing")
    require((SITE / "assets" / "app.js").exists(), "Filter script missing")

    summary = desk["summary"]
    require(summary["official_fixtures"] == len(rows), "Summary fixture mismatch")
    require(summary["priced_fixtures"] == sum(bool(r["markets"]) for r in rows), "Summary priced mismatch")
    require(summary["written_predictions"] == len(predictions), "Summary prediction mismatch")
    require(summary["flags"] == len(flagged), "Summary flag mismatch")
    from common import dump
    dump(DATA / "verify_report.json", {"status": "PASS", "checks": checks,
         "fixtures": len(rows), "predictions": len(predictions), "pages": len(expected_pages),
         "capture_id": cap.capture_id, "raw_responses_hash_verified": len(cap.items)})
    print(f"BOARD AF VERIFY PASS — {checks:,} checks · {len(rows)} fixtures · {len(predictions)} predictions · {len(expected_pages)} pages")


def deterministic_rebuild() -> None:
    outputs = [p for p in DATA.glob("*.json") if p.name not in {"prediction_texts.json", "live_checks.json"}]
    outputs += list(SITE.rglob("*.html")) + [SITE / "assets" / "summary.json"]
    before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs if p.exists()}
    build(); review(); author(); build(); render()
    after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in outputs if p.exists()}
    changed = [p for p in before if before[p] != after.get(p)]
    if changed:
        raise AssertionError("Non-deterministic outputs: " + ", ".join(changed[:10]))
    print(f"BOARD AF REBUILD PASS — {len(before)} output files byte-identical")


if __name__ == "__main__":
    verify()
    deterministic_rebuild()
    verify()

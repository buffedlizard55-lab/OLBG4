#!/usr/bin/env python3
"""Independent release gate for the A172 data, predictions and static pages."""
from __future__ import annotations

import json
import math
import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

import engine
import parse as P

ERRORS: list[str] = []
CHECKS = 0


def check(condition: bool, message: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        ERRORS.append(message)


def capture_from_meta() -> Path:
    override = os.environ.get("A172_CAPTURE_DIR")
    if override:
        return Path(override)
    meta = json.loads((engine.DATA / "meta.json").read_text())
    return engine.DATA / "capture" / meta["capture_id"]


def independent_nhl_probability(row: dict, selection: dict, standings: dict, games: dict) -> float:
    game = games[str((row.get("extra") or {}).get("nhl_id") or row["id"].rsplit("_", 1)[-1])]
    away, home = standings[game["awayTeam"]["abbrev"]], standings[game["homeTeam"]["abbrev"]]
    league = sum(t["gf"] + t["ga"] for t in standings.values()) / sum(t["gp"] for t in standings.values())

    def lam(a: float, b: float) -> float:
        return math.exp(-a) * a**b / math.factorial(b)

    def rates(team: dict) -> tuple[float, float]:
        return team["gf"] / team["gp"], team["ga"] / team["gp"]

    hgf, hga = rates(home)
    agf, aga = rates(away)
    lh = max(0.8, min(5.2, (league / 2) * (0.7 * hgf / (league / 2) + 0.3) * (0.7 * aga / (league / 2) + 0.3) * 1.06))
    la = max(0.8, min(5.2, (league / 2) * (0.7 * agf / (league / 2) + 0.3) * (0.7 * hga / (league / 2) + 0.3) * 0.94))
    ph = [lam(lh, k) for k in range(19)]
    pa = [lam(la, k) for k in range(19)]
    ph, pa = [x / sum(ph) for x in ph], [x / sum(pa) for x in pa]
    cells = [(h, a, ph[h] * pa[a]) for h in range(19) for a in range(19)]
    home_reg = sum(p for h, a, p in cells if h > a)
    tie = sum(p for h, a, p in cells if h == a)
    away_reg = sum(p for h, a, p in cells if h < a)
    key = selection["market_key"]
    label = selection["selection"]
    if key == "match_winner":
        p_home = min(0.82, max(0.18, 0.5 + 0.88 * ((home_reg + 0.5 * tie) - 0.5)))
        return p_home if label.startswith(row["side_b"]) else 1 - p_home
    if key == "regulation_3way":
        if label == "Draw":
            return tie
        return home_reg if label == row["side_b"] else away_reg
    if key == "regulation_handicap":
        return home_reg if label.startswith(row["side_b"]) else away_reg + tie
    if key == "handicap":
        return sum(p for h, a, p in cells if h - a >= 2) if label.startswith(row["side_b"]) else sum(p for h, a, p in cells if h - a <= 1)
    if key.startswith("home_plus_"):
        line = float(key.removeprefix("home_plus_").replace("_", "."))
        p = sum(p for h, a, p in cells if h - a + line > 0)
        return p if f"+{line}" in label else 1 - p
    if key == "total" or key.startswith("total_"):
        line = float(selection["line"])
        over = sum(p for h, a, p in cells if h + a > line)
        return over if label.lower().startswith("over") else 1 - over
    team = re.match(r"(home|away)_team_total_(.+)", key)
    if team:
        line = float(team.group(2).replace("_", "."))
        probs = ph if team.group(1) == "home" else pa
        over = sum(v for goals, v in enumerate(probs) if goals > line)
        return over if "over" in label.lower() and "under" not in label.lower() else 1 - over
    raise ValueError(f"Unknown NHL market {key}")


def main() -> int:
    cap_dir = capture_from_meta()
    ev = engine.Evidence(cap_dir)
    desk = json.loads((engine.DATA / "desk.json").read_text())
    rows = desk["rows"]
    preds = json.loads((engine.DATA / "predictions.json").read_text())["predictions"]
    flags_doc = json.loads((engine.DATA / "flags.json").read_text())
    flags = flags_doc["flags"]
    candidates = json.loads((engine.DATA / "candidates.json").read_text())["candidates"]
    sources = json.loads((engine.DATA / "sources.json").read_text())
    audit = json.loads((engine.DATA / "audit.json").read_text())
    by_id = {r["id"]: r for r in rows}
    manifest_urls = {r["url"] for r in ev.manifest["records"]}
    olbg_events = {e["event_url"]: e for e in P.read_olbg(P.Capture(str(cap_dir)))}

    check(desk["capture_id"] == cap_dir.name, "desk capture ID mismatch")
    check(audit["summary"]["payloads_ok"] == audit["summary"]["payloads_total"] == len(ev.manifest["records"]), "payload audit incomplete")
    for record in ev.manifest["records"]:
        check(ev.sha(record["id"]) == record["sha256"], f"payload hash mismatch: {record['id']}")
        check(record["url"].startswith("https://"), f"non-HTTPS source: {record['id']}")
    check(sources["total"] == len(ev.manifest["records"]), "source register count mismatch")
    check(sources["failure_count"] == len(ev.manifest.get("failures", [])), "capture failure count mismatch")

    expected_candidates = set()
    for row in rows:
        rid = row["id"]
        check(row["sport"] in engine.SPORTS, f"{rid}: out-of-scope sport")
        check(desk["olbg_cutoff_utc"] <= row["start_utc"] <= desk["window_end_utc"], f"{rid}: start outside snapshot window")
        event = olbg_events.get(row["olbg"]["url"])
        check(event is not None, f"{rid}: OLBG event absent from raw hub")
        if event:
            check(event["sport"] == row["sport"], f"{rid}: OLBG sport mismatch")
            check(event["start_utc"] == row["olbg"]["start_utc"], f"{rid}: OLBG timestamp mismatch")
        check(row["olbg"]["capture_id"] in ev.records and row["olbg"]["capture_id"].startswith("olbg_"), f"{rid}: OLBG capture missing")
        if row["source_status"] == "official":
            check(bool(row["official_url"]) and not engine.is_olbg(row["official_url"]), f"{rid}: invalid official URL")
            check(row["capture_id"] in ev.records and not row["capture_id"].startswith("olbg_"), f"{rid}: official capture missing")
            check(row["official_sha256"] == ev.sha(row["capture_id"]), f"{rid}: official payload digest mismatch")
            check(row["capture_id"] in [r["id"] for r in ev.manifest["records"] if r["url"] == row["official_url"]], f"{rid}: official URL/capture mismatch")
        else:
            check(not row["official_url"] and not row["official_sha256"], f"{rid}: unsupported official value not blank")
            check(not row["markets"] and not row.get("pick"), f"{rid}: unconfirmed row was priced")
            check("official fixture" in row["unverified"] and bool(row["flags"]), f"{rid}: unconfirmed row not flagged")
        if not row.get("venue"):
            check("venue" in row["unverified"], f"{rid}: blank venue not marked unsupported")
            check(any(f["row_id"] == rid and f["kind"] in ("unverified-field", "unverified-fixture") for f in flags), f"{rid}: blank venue lacks review flag")
        for key, market in (row.get("markets") or {}).items():
            check(abs(market["probability_sum"] - 1.0) <= 0.0002, f"{rid}/{key}: market does not sum to one")
            check(market["probability_sum"] == round(sum(s["fair_prob"] for s in market["selections"]), 4), f"{rid}/{key}: stored market sum mismatch")
            for selection in market["selections"]:
                p = selection["fair_prob"]
                check(0 < p < 1, f"{rid}/{key}: probability out of range")
                check(selection["fair_decimal"] == round(1 / p, 2), f"{rid}/{key}: decimal mismatch")
                check(selection["fair_american"] == engine.american(p), f"{rid}/{key}: American mismatch")
                if row["source_status"] == "official" and not row.get("sample_cap") and p > 0.70 and -250 <= selection["fair_american"] <= 10000:
                    expected_candidates.add((rid, key, selection["label"]))
        pick = row.get("pick")
        if pick:
            market = row["markets"].get("match_winner")
            check(market is not None and any(s["label"] == pick["selection"] for s in market["selections"]), f"{rid}: primary pick absent from match-winner market")
            check(pick["fair_prob"] > 0.70 or pick["confidence"] != "High", f"{rid}: High below probability threshold")
            if pick["confidence"] == "High":
                check(-250 <= pick["fair_american"] <= 10000, f"{rid}: High outside price band")
                check(any(p["row_id"] == rid and p["selection"] == pick["selection"] for p in preds), f"{rid}: High primary pick lacks its own analysis")
            if pick["confidence"] == "Low":
                check(pick["fair_prob"] < 0.55, f"{rid}: Low label inconsistent with probability")
            if pick["confidence"] == "Medium":
                check(pick["fair_prob"] >= 0.55, f"{rid}: Medium label inconsistent with probability")

    actual_candidates = {(c["row_id"], c["market_key"], c["selection"]) for c in candidates}
    check(actual_candidates == expected_candidates, f"candidate ledger mismatch: missing={sorted(expected_candidates-actual_candidates)} extra={sorted(actual_candidates-expected_candidates)}")
    published = [c for c in candidates if c["decision"] == "published"]
    check(len({c["row_id"] for c in published}) == len(published) == len(preds), "published candidate/prediction count mismatch")
    for c in candidates:
        if c["decision"] == "eligible-evidence-incomplete":
            check(any(f["kind"] == "eligible-evidence-incomplete" and f["row_id"] == c["row_id"] for f in flags), f"candidate gap not flagged: {c['row_id']}")

    standings = engine.nhl_standings(ev) if ev.exists("nhl_standings") else {}
    games = engine.nhl_games(ev)
    seen_text = set()
    for pred in preds:
        pid = pred["prediction_id"]
        row = by_id.get(pred["row_id"])
        check(row is not None, f"{pid}: row missing")
        if not row:
            continue
        check(pred["confidence"] == "High" and pred["prob"] > 0.70, f"{pid}: not a strict High probability")
        check(-250 <= pred["fair_american"] <= 10000, f"{pid}: outside fair-price band")
        check(row["source_status"] == "official" and not row.get("sample_cap"), f"{pid}: source/sample gate failed")
        check(pred["official_sha256"] == ev.sha(row["capture_id"]), f"{pid}: fixture digest mismatch")
        check(pred["olbg_url"] in olbg_events, f"{pid}: OLBG event absent")
        candidate = next((c for c in published if c["row_id"] == pred["row_id"]), None)
        check(candidate is not None and candidate["selection"] == pred["selection"] and candidate["market_key"] == pred["market_key"], f"{pid}: published candidate mismatch")
        check(row["analysis_status"] == "fully written prediction", f"{pid}: row analysis status mismatch")
        check(bool((row.get("recent") or {}).get("away")) and bool((row.get("recent") or {}).get("home")), f"{pid}: recent-result evidence missing")
        text = pred["prediction_text"]
        check(len(text.split()) >= 30 and len(text.split()) == pred["word_count"], f"{pid}: invalid word count")
        check(text not in seen_text, f"{pid}: duplicate prose")
        seen_text.add(text)
        check(pred["selection"].lower() in text.lower(), f"{pid}: exact selection absent from prose")
        check(not re.search(r"\bmodels?\b|\bverified\b", text, re.I), f"{pid}: internal wording in public prediction")
        if "moneyline" in text.lower():
            check("incl. OT/SO" in pred["market"] or "Money Line" in pred["market"], f"{pid}: moneyline prose tied to wrong market")
        if "regulation" in text.lower() and "team total" not in pred["market"].lower():
            check("Total Goals" not in pred["market"] or "regulation" in pred["market"].lower(), f"{pid}: regulation market ambiguity")
        labels = {f["label"] for f in pred["facts"]}
        check("Official fixture" in labels, f"{pid}: fixture fact missing")
        check(any("current form" in x for x in labels), f"{pid}: current form missing")
        check(sum("recent results" in x for x in labels) == 2, f"{pid}: both recent-result logs required")
        check(any("scoring calculation" in x.lower() for x in labels), f"{pid}: scoring calculation missing")
        if pred["sport"] == "Ice Hockey":
            check(sum("official season leaders" in x for x in labels) >= 2, f"{pid}: player evidence missing")
            independent = independent_nhl_probability(row, {**pred, "line": row["markets"][pred["market_key"]]["line"]}, standings, games)
            check(round(independent, 4) == pred["prob"], f"{pid}: independent probability {independent:.8f} != {pred['prob']}")
            check(row["form"]["away"].split(" (")[0] in text and row["form"]["home"].split(" (")[0] in text, f"{pid}: current records absent from prose")
            for side in ("away", "home"):
                recent_text = "; ".join(x["text"] for x in row["recent"][side][:2])
                check(recent_text in text, f"{pid}: {side} recent results absent from prose")
        for fact in pred["facts"]:
            check(fact["source_url"].startswith("https://") and not engine.is_olbg(fact["source_url"]), f"{pid}: non-official fact source")
            check(fact["source_url"] in manifest_urls, f"{pid}: fact source not in pinned manifest: {fact['source_url']}")
        check(pred["fair_decimal"] == round(1 / pred["prob"], 2), f"{pid}: decimal mismatch")
        check(pred["fair_american"] == engine.american(pred["prob"]), f"{pid}: American mismatch")
    for i, first in enumerate(preds):
        for second in preds[i + 1:]:
            similarity = SequenceMatcher(None, first["prediction_text"], second["prediction_text"]).ratio()
            check(similarity <= 0.68, f"prediction prose too similar: {first['prediction_id']} / {second['prediction_id']} = {similarity:.3f}")

    summary = desk["summary"]
    check(summary["rows_total"] == len(rows) == summary["olbg_listed"], "row summary mismatch")
    check(summary["official_sourced"] == sum(r["source_status"] == "official" for r in rows), "official summary mismatch")
    check(summary["priced"] == sum(bool(r.get("pick")) for r in rows), "priced summary mismatch")
    check(summary["predictions"] == len(preds), "prediction summary mismatch")
    check(set(summary["by_sport"]) == set(engine.SPORTS), "15-sport summary mismatch")
    for sport in engine.SPORTS:
        sport_rows = [r for r in rows if r["sport"] == sport]
        count = sum(p["sport"] == sport for p in preds)
        entry = summary["by_sport"][sport]
        check(entry["rows"] == len(sport_rows), f"{sport}: row count mismatch")
        check(entry["official_sourced"] == sum(r["source_status"] == "official" for r in sport_rows), f"{sport}: official count mismatch")
        check(entry["priced"] == sum(bool(r.get("pick")) for r in sport_rows), f"{sport}: priced count mismatch")
        check(entry["written_high"] == count and entry["shortfall"] == max(0, 5 - count), f"{sport}: prediction target mismatch")
        if count < 5:
            check(any(f["kind"] == "shortfall" and f["title"].startswith(sport + ":") for f in flags), f"{sport}: shortfall not flagged")
    check(flags_doc["count"] == len(flags), "flag count mismatch")

    pages = sorted(engine.SITE.rglob("*.html"))
    check(len(pages) == 25, f"expected 25 pages, got {len(pages)}")
    for sport in engine.SPORTS:
        check((engine.SITE / "sports" / f"{engine.SLUGS[sport]}.html").exists(), f"missing sport page: {sport}")
    for page in pages:
        text = page.read_text(encoding="utf-8")
        check("</html>" in text and "Executive summary" in text, f"{page.name}: incomplete page or summary")
        check("TODO" not in text, f"{page.name}: placeholder found")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            check(target.exists(), f"{page.relative_to(engine.ROOT)}: broken link {href}")
    index = (engine.SITE / "index.html").read_text()
    picks = (engine.SITE / "picks.html").read_text()
    for pred in preds:
        check(pred["prediction_id"] in index and pred["prediction_id"] in picks, f"{pred['prediction_id']:s}: missing index or picks location")
        check(pred["selection"] in index and pred["selection"] in picks, f"{pred['prediction_id']:s}: exact selection not obvious")
        check(pred["prediction_text"] in picks, f"{pred['prediction_id']:s}: full prose absent from picks page")
        sport_page = (engine.SITE / "sports" / f"{engine.SLUGS[pred['sport']]}.html").read_text()
        check(pred["prediction_text"] in sport_page, f"{pred['prediction_id']:s}: full prose absent from sport page")
    check(str(len(flags)) in (engine.SITE / "flagged.html").read_text(), "flag count absent from review page")

    if ERRORS:
        print(f"FAIL — {len(ERRORS)} errors across {CHECKS} checks")
        for error in ERRORS[:100]:
            print(" -", error)
        return 1
    max_similarity = max((SequenceMatcher(None, a["prediction_text"], b["prediction_text"]).ratio() for i, a in enumerate(preds) for b in preds[i + 1:]), default=0)
    print(f"PASS — {CHECKS:,} checks; {len(rows)} OLBG rows; {len(preds)} written High picks; {len(flags)} flags; {len(pages)} pages")
    print(f"PASS — {len(ev.manifest['records'])}/{len(ev.manifest['records'])} raw hashes; {len(candidates)} candidates; max prose similarity {max_similarity:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

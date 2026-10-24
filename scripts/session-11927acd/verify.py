#!/usr/bin/env python3
"""RI5 publication gate: independent arithmetic, provenance, writing and site checks."""
from __future__ import annotations

import html
import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

import ri

ERRORS: list[str] = []


def check(condition: bool, message: str) -> None:
    if not condition:
        ERRORS.append(message)


def american(p: float) -> int:
    return -int(round(100 * p / (1 - p))) if p >= 0.5 else int(round(100 * (1 - p) / p))


def pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam**k / math.factorial(k)


def independent_nhl_probability(row: dict, pred: dict, standings: dict, league: float) -> float:
    game = None
    numeric_id = int(row["id"].rsplit("_", 1)[1])
    for week in ri.raw_json(row["capture_id"])["gameWeek"]:
        for candidate in week["games"]:
            if candidate["id"] == numeric_id:
                game = candidate
                break
    check(game is not None, f"{pred['prediction_id']}: official game not found")
    away, home = standings[game["awayTeam"]["abbrev"]], standings[game["homeTeam"]["abbrev"]]
    base = league / 2
    home_attack = 0.7 * (home["gf_pg"] / base) + 0.3
    away_attack = 0.7 * (away["gf_pg"] / base) + 0.3
    home_defence = 0.7 * (home["ga_pg"] / base) + 0.3
    away_defence = 0.7 * (away["ga_pg"] / base) + 0.3
    lh = min(5.2, max(0.8, base * home_attack * away_defence * 1.06))
    la = min(5.2, max(0.8, base * away_attack * home_defence * 0.94))
    ph = [pmf(k, lh) for k in range(19)]
    pa = [pmf(k, la) for k in range(19)]
    ph, pa = [x / sum(ph) for x in ph], [x / sum(pa) for x in pa]
    cells = [(h, a, ph[h] * pa[a]) for h in range(19) for a in range(19)]
    key = pred["market_key"]
    label = pred["selection"]
    if key == "regulation_winner":
        check(label.endswith("-0.5"), f"{pred['prediction_id']}: unexpected regulation label")
        return sum(p for h, a, p in cells if h > a) if label.startswith(row["side_b"]) else sum(p for h, a, p in cells if h < a)
    if key.startswith("home_plus_"):
        line = float(key.removeprefix("home_plus_").replace("_", "."))
        return sum(p for h, a, p in cells if h - a + line > 0)
    if key.startswith("total_"):
        line = float(key.removeprefix("total_").replace("_", "."))
        over = sum(p for h, a, p in cells if h + a > line)
        return over if label.lower().startswith("over") else 1 - over
    team = re.match(r"(home|away)_team_total_(.+)", key)
    if team:
        line = float(team.group(2).replace("_", "."))
        probs = ph if team.group(1) == "home" else pa
        over = sum(v for goals, v in enumerate(probs) if goals > line)
        return 1 - over if "under" in label.lower() else over
    raise ValueError(f"Unknown selection calculation: {key}")


def main() -> int:
    desk = json.loads((ri.DATA / "desk.json").read_text())
    pred_doc = json.loads((ri.DATA / "predictions.json").read_text())
    flags = json.loads((ri.DATA / "flags.json").read_text())
    audit = json.loads((ri.DATA / "audit.json").read_text())
    candidates = json.loads((ri.DATA / "candidates.json").read_text())
    rows, preds = desk["rows"], pred_doc["predictions"]
    by_id = {r["id"]: r for r in rows}

    check(desk["summary"]["rows_total"] == len(rows) == 401, "desk row count mismatch")
    check(set(desk["summary"]["by_sport"]) == set(ri.SPORTS), "sport summary does not contain exactly the 15 sports")
    check(audit["summary"]["row_hash_mismatches"] == 0, "source payload hash mismatch")
    check(audit["summary"]["payloads_ok"] == audit["summary"]["payloads_total"] == 137, "payload audit incomplete")
    check(len(candidates["legacy"]) == 17 and all(c["decision"] == "rejected" for c in candidates["legacy"]), "legacy candidate was not rejected")
    check(not any(c["decision"] == "eligible-needs-analysis" for c in candidates["ri"]), "a corrected eligible candidate lacks a written-analysis decision")

    for row in rows:
        check(row["sport"] in ri.SPORTS, f"{row['id']}: invalid sport")
        check(bool(row["start_utc"]), f"{row['id']}: blank start")
        if row["source_status"] == "official":
            check(bool(row["official_url"]) and not ri.is_olbg(row["official_url"]), f"{row['id']}: invalid official fixture URL")
            check(row["capture_id"] in ri.RECORDS, f"{row['id']}: official capture absent")
            check(not row["capture_id"].startswith("olbg_"), f"{row['id']}: OLBG capture used as official fixture")
        else:
            check(not row["official_url"], f"{row['id']}: unsupported official field not blank")
            check(bool(row["flags"]), f"{row['id']}: review row has no flag")
            check(bool(row["review_url"] or row.get("olbg")), f"{row['id']}: no manual review link")
        for market_key, market in (row.get("markets") or {}).items():
            for selection in market["selections"]:
                p = selection["fair_prob"]
                check(0 < p < 1, f"{row['id']}/{market_key}: probability out of range")
                check(selection["fair_decimal"] == round(1 / p, 2), f"{row['id']}/{market_key}: decimal mismatch")
                check(selection["fair_american"] == american(p), f"{row['id']}/{market_key}: American mismatch")
        pick = row.get("pick")
        if pick:
            market = row["markets"][pick["market_key"]]
            check(any(s["label"] == pick["selection"] for s in market["selections"]), f"{row['id']}: primary pick absent from market")
            check(pick["fair_prob"] > 0.70 or pick["confidence"] != "High", f"{row['id']}: High not strictly above 70%")
            if pick["confidence"] == "High":
                check(-250 <= pick["fair_american"] <= 10000, f"{row['id']}: High price outside band")
                check(row["source_status"] == "official" and row.get("olbg"), f"{row['id']}: High lacks source/OLBG")

    standings = ri.nhl_standings()
    league = sum(t["gf"] + t["ga"] for t in standings.values()) / sum(t["gp"] for t in standings.values())
    olbg_events = ri.olbg_nhl_events()
    check(len(preds) == 4, "expected four strict written predictions")
    check([p["prob"] for p in preds] == sorted([p["prob"] for p in preds], reverse=True), "predictions not sorted strongest first")
    seen_text = set()
    for pred in preds:
        pid = pred["prediction_id"]
        row = by_id.get(pred["row_id"])
        check(row is not None, f"{pid}: missing row")
        if not row:
            continue
        check(pred["confidence"] == "High", f"{pid}: not High")
        check(pred["prob"] > 0.70, f"{pid}: probability is not strictly above 70%")
        check(-250 <= pred["fair_american"] <= 10000, f"{pid}: price outside band")
        check(pred["sample_games"] >= 10, f"{pid}: sample below ten")
        check(row["source_status"] == "official" and bool(row.get("olbg")), f"{pid}: source or OLBG gate failed")
        check(pred["olbg_event_id"] in olbg_events, f"{pid}: OLBG event absent from raw hub")
        check(pred["official_sha256"] == ri.actual_sha(row["capture_id"]), f"{pid}: official payload digest mismatch")
        independent = independent_nhl_probability(row, pred, standings, league)
        check(round(independent, 4) == pred["prob"], f"{pid}: independent probability {independent:.8f} != published {pred['prob']}")
        check(pred["fair_decimal"] == round(1 / pred["prob"], 2), f"{pid}: fair decimal mismatch")
        check(pred["fair_american"] == american(pred["prob"]), f"{pid}: fair American mismatch")
        text = pred["prediction_text"]
        words = len(text.split())
        check(words >= 30 and words == pred["word_count"], f"{pid}: word count mismatch")
        check(text not in seen_text, f"{pid}: duplicate prediction text")
        seen_text.add(text)
        check(pred["selection"].lower() in text.lower(), f"{pid}: exact selection absent from prose")
        check(not re.search(r"\bmodel\b|\bmodels\b|\bverified\b|\bverification\b", text, re.I), f"{pid}: banned wording in prediction prose")
        labels = {f["label"] for f in pred["facts"]}
        check("Official fixture" in labels and "Season scoring rates" in labels and "Scoring calculation" in labels, f"{pid}: required facts absent")
        check(any("current form" in label for label in labels), f"{pid}: current form absent")
        check(any("official season leaders" in label for label in labels), f"{pid}: player context absent")
        for fact in pred["facts"]:
            check(fact["source_url"].startswith("https://") and not ri.is_olbg(fact["source_url"]), f"{pid}: fact lacks official source")
        check(row["analysis_status"] == "fully written prediction", f"{pid}: row analysis status mismatch")
    for i, first in enumerate(preds):
        for second in preds[i + 1:]:
            similarity = SequenceMatcher(None, first["prediction_text"], second["prediction_text"]).ratio()
            check(similarity <= 0.55, f"prediction similarity too high: {first['prediction_id']} / {second['prediction_id']} = {similarity:.3f}")
    check(sum(r["analysis_status"] == "fully written prediction" for r in rows) == len(preds), "written row count mismatch")

    for sport in ri.SPORTS:
        count = sum(p["sport"] == sport for p in preds)
        if count < 5:
            check(any(f["kind"] == "shortfall" and f["title"].startswith(sport + ":") for f in flags["flags"]), f"{sport}: shortfall not explained")
    check(flags["count"] == len(flags["flags"]), "flag count mismatch")

    pages = sorted(ri.SITE.rglob("*.html"))
    check(len(pages) == 24, f"expected 24 HTML pages, got {len(pages)}")
    for sport in ri.SPORTS:
        check((ri.SITE / "sports" / f"{ri.SLUGS[sport]}.html").exists(), f"missing sport page: {sport}")
    for page in pages:
        text = page.read_text(encoding="utf-8")
        check("</html>" in text, f"{page}: truncated HTML")
        check("Executive summary" in text or "<section class=\"exec\">" in text, f"{page}: no executive summary section")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("https://", "http://", "#", "mailto:")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            check(target.exists(), f"{page.relative_to(ri.ROOT)}: broken internal link {href}")
    index = (ri.SITE / "index.html").read_text()
    picks = (ri.SITE / "picks.html").read_text()
    flagged = (ri.SITE / "flagged.html").read_text()
    check("Executive summary" in index and "Exact selection" in index, "dashboard does not open with obvious picks")
    for pred in preds:
        check(pred["prediction_id"] in index and pred["prediction_id"] in picks, f"{pred['prediction_id']}: missing dashboard or picks location")
        check(html.escape(pred["prediction_text"]) in picks, f"{pred['prediction_id']}: full text absent from picks page")
    check(str(flags["count"]) in flagged, "flag count absent from flagged page")

    if ERRORS:
        print(f"FAIL — {len(ERRORS)} publication errors")
        for error in ERRORS[:80]:
            print(" -", error)
        return 1
    print(f"PASS — {len(rows)} rows, {len(preds)} independent written High picks, {flags['count']} flags, {len(pages)} pages")
    print("PASS — raw fixture/OLBG gates, independent probabilities, fair prices, prose, shortfalls and internal links")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Build the strict RI desk and fully written predictions from committed evidence."""
from __future__ import annotations

import copy
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

import ri

SHORTFALL = {
    "Golf": "The current OLBG golf hub contains no upcoming event card, so no fixture or selection can be supported.",
    "Volleyball": "Official Italian fixtures are available, but the one-match samples retain a Medium cap and no strict High selection survives.",
    "Rugby Union": "No OLBG-linked match with both an official fixture and sufficient official scoring inputs passes every strict gate.",
    "Cricket": "No OLBG-linked match has a complete official fixture and form crosswalk in the pinned capture.",
    "Snooker": "No strict High selection has both an OLBG event crosswalk and sufficient official match/statistical evidence.",
    "Darts": "Official PDC match-statistic support is incomplete in the pinned capture; no line is promoted to High.",
    "Baseball": "The OLBG-listed postseason game has official inputs, but no market lands inside the strict probability and price band.",
    "Gaelic Sports": "Official scoring and fixture support is incomplete for the OLBG-listed events; no High selection is published.",
    "Greyhounds": "The current capture has no upcoming OLBG greyhound card with official runner-level form suitable for a High pick.",
    "Tennis": "No OLBG-linked singles match has the complete official rankings, draw and match evidence required for a strict High pick.",
    "Motor Racing": "The available outright line does not satisfy the strict probability/price overlap with adequate session-specific evidence.",
    "Handball": "The numerical Danish candidate is rejected because its fixture identity comes from OLBG rather than an official programme.",
    "Ice Hockey": "Four selections pass every gate. Two other adequately sampled OLBG games have no supported market in the narrow band; the ten-game cut is not relaxed to force a fifth.",
    "Basketball": "Future official EuroLeague candidates have no captured OLBG event crosswalk, while current OLBG NBA cards lack the required official team-statistics payload.",
    "Rugby League": "The numerical Samoa–Tonga candidate retains a Medium cap because the sides have only one or two tournament matches in the sample.",
}

SELECTIONS = json_texts = None


def game_from_capture(capture_id: str, row_id: str) -> dict:
    numeric_id = int(row_id.rsplit("_", 1)[1])
    for week in ri.raw_json(capture_id).get("gameWeek", []):
        for game in week.get("games", []):
            if game["id"] == numeric_id:
                return game
    raise ValueError(f"{row_id}: game missing from {capture_id}")


def confidence(row: dict, prob: float, american: int, sample_ok: bool, official_ok: bool) -> tuple[str, str]:
    if prob > 0.70 and -250 <= american <= 10000 and sample_ok and official_ok and row.get("olbg"):
        return "High", "strictly above 70%, fair price in band, official fixture, OLBG card and adequate sample"
    if prob >= 0.55:
        return "Medium", "playable lean, but at least one strict High/source/sample/price gate is not met"
    return "Low", "estimated probability below 55% or incomplete support"


def build_rows():
    standings = ri.nhl_standings()
    league_goals = sum(t["gf"] + t["ga"] for t in standings.values()) / sum(t["gp"] for t in standings.values())
    olbg_events = ri.olbg_nhl_events()
    rows = []
    nhl_internal = {}
    for original in ri.BASE_DESK["rows"]:
        row = copy.deepcopy(original)
        # RI fair American prices always come directly from probability, never from an
        # already rounded decimal. Keep the published probability but correct both prices.
        for market in (row.get("markets") or {}).values():
            for selection in market.get("selections", []):
                selection.update(ri.price(selection["fair_prob"]))
        if row.get("pick"):
            original_pick = row["pick"]
            original_market = (row.get("markets") or {}).get(original_pick.get("market_key"), {})
            matched = next((s for s in original_market.get("selections", []) if s["label"] == original_pick["selection"]), None)
            if matched:
                original_pick["fair_prob"] = matched["fair_prob"]
                original_pick["fair_decimal"] = matched["fair_decimal"]
                original_pick["fair_american"] = matched["fair_american"]
        original_rule = (original.get("pick") or {}).get("rule", "").lower()
        original_sample = (original.get("sample") or "").lower()
        original_flags = " ".join(original.get("flags") or []).lower()
        row["sample_cap"] = bool(("cap" in original_rule and "medium" in original_rule) or "one-match" in original_rule or "one-match" in original_sample or "confidence capped" in original_flags)
        original_official = row.get("official_url") or ""
        fixture_from_olbg = (row.get("capture_id") or "").startswith("olbg_")
        row["official_stats_url"] = original_official if fixture_from_olbg and original_official and not ri.is_olbg(original_official) else ""
        if fixture_from_olbg or not original_official or ri.is_olbg(original_official):
            row["official_url"] = ""
            row["official_source_name"] = ""
            row["source_status"] = "review-required"
            row["review_url"] = original_official or (row.get("olbg") or {}).get("url", "")
            row["unverified"] = True
            note = "Official statistics are linked, but they do not establish this fixture on an official programme." if row["official_stats_url"] else "Official fixture programme not captured; OLBG is not an official league source."
            row["flags"] = list(row.get("flags") or []) + [note]
        else:
            row["source_status"] = "official"
            row["review_url"] = original_official
            row["unverified"] = False
        row["match"] = f"{row['side_a']} at {row['side_b']}"
        row["analysis_status"] = "winner lean only — no write-up"
        if row["sport"] == "Ice Hockey" and row["id"].startswith("fx_nhl_"):
            game = game_from_capture(row["capture_id"], row["id"])
            away = standings[game["awayTeam"]["abbrev"]]
            home = standings[game["homeTeam"]["abbrev"]]
            lh, la = ri.nhl_lambdas(away, home, league_goals)
            event = None
            if row["id"] in ri.NHL_OLBG:
                eid = ri.NHL_OLBG[row["id"]]
                event = olbg_events.get(eid)
                if not event:
                    raise ValueError(f"{row['id']}: OLBG event {eid} absent from captured hub")
                away_code, home_code = ri.NHL_CODES[row["id"]]
                expected = f"{away_code} "
                if not event["name"].startswith(expected) or f"@ {home_code} " not in event["name"] + " ":
                    raise ValueError(f"{row['id']}: OLBG crosswalk name mismatch: {event['name']}")
                row["olbg"] = event
                if event["start_utc"] != row["start_utc"]:
                    row["flags"] = list(row.get("flags") or []) + [
                        f"OLBG displays {event['start_utc']}; official NHL schedule displays {row['start_utc']}. Official time published."
                    ]
            sample_ok = min(away["gp"], home["gp"]) >= 10
            row["sample_cap"] = not sample_ok
            expanded = bool(event and sample_ok and game.get("gameState") == "FUT")
            row["markets"] = ri.nhl_markets(row["side_a"], row["side_b"], lh, la, expanded=expanded)
            row["evidence"] = {
                "league_goals_per_game": round(league_goals, 3),
                "away_gf_pg": round(away["gf_pg"], 3), "away_ga_pg": round(away["ga_pg"], 3),
                "home_gf_pg": round(home["gf_pg"], 3), "home_ga_pg": round(home["ga_pg"], 3),
                "expected_goals_away": round(la, 2), "expected_goals_home": round(lh, 2),
                "standings_source": "https://api-web.nhle.com/v1/standings/now",
            }
            row["form"] = {
                "away": f"{away['w']}-{away['l']}-{away['otl']} ({away['pts']} pts, L10 {away['l10']}, streak {away['streak']})",
                "home": f"{home['w']}-{home['l']}-{home['otl']} ({home['pts']} pts, L10 {home['l10']}, streak {home['streak']})",
                "away_home_away": away["road"], "home_home_away": home["home"],
            }
            row["sample"] = f"{min(away['gp'], home['gp'])} games played (minimum of the two clubs)"
            row["model"] = {
                "name": "independent Poisson goals; 70% club-rate pooling plus 30% league prior",
                "home_exp": round(lh, 2), "away_exp": round(la, 2), "home_adv": 1.06,
                "away_location_factor": 0.94, "moneyline_shrinkage": 0.88,
            }
            winner = row["markets"]["match_winner"]["selections"]
            best = max(winner, key=lambda s: s["fair_prob"])
            conf, reason = confidence(row, best["fair_prob"], best["fair_american"], sample_ok, row["source_status"] == "official")
            row["pick"] = {
                "market": "Money Line (incl. OT/SO)", "market_key": "match_winner",
                "selection": best["label"], "fair_prob": best["fair_prob"],
                "fair_decimal": best["fair_decimal"], "fair_american": best["fair_american"],
                "confidence": conf, "in_window": -250 <= best["fair_american"] <= 10000,
                "rule": reason,
            }
            nhl_internal[row["id"]] = {"away": away, "home": home, "lh": lh, "la": la, "sample_ok": sample_ok, "expanded": expanded}
        elif row.get("pick"):
            pick = row["pick"]
            sample_ok = not row["sample_cap"]
            conf, reason = confidence(row, pick["fair_prob"], pick["fair_american"], sample_ok, row["source_status"] == "official")
            pick["confidence"] = conf
            pick["rule"] = reason
            pick["in_window"] = -250 <= pick["fair_american"] <= 10000
        rows.append(row)
    return rows, nhl_internal


def build_predictions(rows, internal):
    texts = json_texts
    players = ri.player_facts()
    by_id = {r["id"]: r for r in rows}
    predictions = []
    for row_id, spec in texts.items():
        row = by_id[row_id]
        market = row["markets"][spec["market_key"]]
        selection = next(s for s in market["selections"] if s["label"] == spec["selection_label"])
        p = selection["fair_prob"]
        a = selection["fair_american"]
        if not (p > 0.70 and -250 <= a <= 10000):
            raise ValueError(f"{spec['prediction_id']}: selection fails strict band: {p}, {a}")
        if not internal[row_id]["sample_ok"] or not row.get("olbg") or row["source_status"] != "official":
            raise ValueError(f"{spec['prediction_id']}: eligibility gate failed")
        facts = [
            {"label": "Official fixture", "value": f"{row['match']}, {row['start_utc']}, {row['venue']}", "source_url": row["official_url"]},
            {"label": f"{row['side_a']} current form", "value": row["form"]["away"] + f"; away record {row['form']['away_home_away']}", "source_url": row["evidence"]["standings_source"]},
            {"label": f"{row['side_b']} current form", "value": row["form"]["home"] + f"; home record {row['form']['home_home_away']}", "source_url": row["evidence"]["standings_source"]},
            {"label": "Season scoring rates", "value": f"{row['side_a']} {row['evidence']['away_gf_pg']:.3f} for / {row['evidence']['away_ga_pg']:.3f} against; {row['side_b']} {row['evidence']['home_gf_pg']:.3f} for / {row['evidence']['home_ga_pg']:.3f} against", "source_url": row["evidence"]["standings_source"]},
            {"label": "Scoring calculation", "value": f"Expected regulation goals: {row['side_a']} {row['evidence']['expected_goals_away']:.2f}, {row['side_b']} {row['evidence']['expected_goals_home']:.2f}", "source_url": row["evidence"]["standings_source"]},
        ]
        for name in spec["players"]:
            item = players[name]
            parts = []
            if "goals" in item: parts.append(f"{item['goals']} goals")
            if "points" in item: parts.append(f"{item['points']} points")
            if "goalsAgainstAverage" in item: parts.append(f"{item['goalsAgainstAverage']:.2f} GAA")
            if "savePctg" in item: parts.append(f"{item['savePctg']:.3f} save percentage")
            source = ri.RECORDS["nhl_goalies" if "goalsAgainstAverage" in item or "savePctg" in item else "nhl_skaters"]["url"]
            facts.append({"label": f"{name} ({item['team']}) official season leaders", "value": ", ".join(parts), "source_url": source})
        text = spec["prediction_text"]
        row["analysis_status"] = "fully written prediction"
        predictions.append({
            "prediction_id": spec["prediction_id"], "row_id": row_id, "sport": row["sport"],
            "competition": row["competition"], "match": row["match"], "start_utc": row["start_utc"],
            "venue": row["venue"], "market": market["market_name"], "market_key": spec["market_key"],
            "selection": selection["label"], "prob": p, "fair_decimal": selection["fair_decimal"],
            "fair_american": a, "confidence": "High",
            "confidence_reason": "Strictly above 70%, fair American price in the required band, ten-game minimum, official fixture and captured OLBG event.",
            "prediction_text": text, "selection_language": selection["label"], "word_count": len(text.split()),
            "facts": facts, "official_source_url": row["official_url"],
            "official_source_name": row["official_source_name"], "official_capture_id": row["capture_id"],
            "official_sha256": ri.RECORDS[row["capture_id"]]["sha256"], "olbg_url": row["olbg"]["url"],
            "olbg_event_id": row["olbg"]["event_id"], "sample_games": int(row["sample"].split()[0]),
            "availability_note": "No official injury or team-news report is present in the pinned capture; no availability claim is made.",
        })
    predictions.sort(key=lambda p: (-p["prob"], p["prediction_id"]))
    return predictions


def make_flags(rows, predictions, candidates):
    flags = []
    for sport in ri.SPORTS:
        count = sum(p["sport"] == sport for p in predictions)
        if count < 5:
            flags.append({"group": "Daily target shortfalls", "kind": "shortfall", "title": f"{sport}: {count} of five written High predictions", "detail": SHORTFALL[sport], "source_url": "", "row_id": ""})
    for row in rows:
        if row["source_status"] != "official":
            flags.append({"group": "Official fixture source required", "kind": "unverified-fixture", "title": row["match"], "detail": "The event is listed by OLBG, but the pinned capture does not establish it on an official programme. Unsupported official fields remain blank.", "source_url": row["review_url"], "row_id": row["id"]})
    audit = __import__("json").loads((ri.DATA / "audit.json").read_text())
    for failure in audit["capture_failures"]:
        flags.append({"group": "Capture failures", "kind": "capture-failure", "title": failure.get("id") or "Unnamed source", "detail": f"HTTP {failure.get('status')}: {failure.get('error') or 'capture failed'}", "source_url": failure.get("url") or "", "row_id": ""})
    for defect in audit["known_defects"]:
        flags.append({"group": "Calculation and provenance defects", "kind": "defect", "title": defect["id"], "detail": defect["detail"] + f" Location: {defect['where']}", "source_url": "https://github.com/buffedlizard55-lab/OLBG4/blob/main/" + defect["where"].split(":")[0], "row_id": ""})
    eligible_without = sorted({c["row_id"] for c in candidates if c["decision"] == "no-qualifying-market"})
    by_id = {r["id"]: r for r in rows}
    for row_id in eligible_without:
        row = by_id[row_id]
        flags.append({"group": "Daily target shortfalls", "kind": "no-market-in-band", "title": f"No strict selection: {row['match']}", "detail": "Official fixture, OLBG card and ten-game sample are present, but none of the tested winner, regulation, puck-line, game-total or team-total markets lands inside the strict band.", "source_url": row["official_url"], "row_id": row_id})
    flags.append({"group": "Availability information", "kind": "team-news-not-captured", "title": "NHL injury and team-news reports not captured", "detail": "The four predictions use official fixture, standings and player-statistics payloads only. No injury or lineup availability claim is made.", "source_url": "https://www.nhl.com/news/", "row_id": ""})
    return flags


def main() -> int:
    global SELECTIONS, json_texts
    json_texts = __import__("json").loads((ri.DATA / "prediction_texts.json").read_text())
    SELECTIONS = json_texts
    rows, internal = build_rows()
    predictions = build_predictions(rows, internal)
    by_id = {r["id"]: r for r in rows}

    candidates = []
    for row_id, info in internal.items():
        if not info["expanded"]:
            continue
        row = by_id[row_id]
        found = []
        for market_key, market in row["markets"].items():
            for selection in market["selections"]:
                p, a = selection["fair_prob"], selection["fair_american"]
                if p > 0.70 and -250 <= a <= 10000:
                    spec = json_texts.get(row_id)
                    published = bool(spec and spec["market_key"] == market_key and spec["selection_label"] == selection["label"])
                    item = {
                        "row_id": row_id, "sport": row["sport"], "match": row["match"], "start_utc": row["start_utc"],
                        "market_key": market_key, "market": market["market_name"], "selection": selection["label"],
                        "fair_prob": p, "fair_american": a, "decision": "published" if published else "eligible-alternate-not-selected",
                        "reasons": [] if published else ["another selection was chosen for the single written analysis on this event"],
                        "official_url": row["official_url"], "olbg_url": row["olbg"]["url"],
                    }
                    candidates.append(item)
                    found.append(item)
        if not found:
            candidates.append({"row_id": row_id, "sport": row["sport"], "match": row["match"], "start_utc": row["start_utc"], "market_key": "", "market": "", "selection": "", "fair_prob": None, "fair_american": None, "decision": "no-qualifying-market", "reasons": ["no tested market satisfies both numerical tests"], "official_url": row["official_url"], "olbg_url": row["olbg"]["url"]})
    # Re-scan every corrected market, not only the expanded NHL set. Any newly eligible
    # selection must stop verification for explicit analysis rather than slip through.
    for row in rows:
        if internal.get(row["id"], {}).get("expanded"):
            continue
        for market_key, market in (row.get("markets") or {}).items():
            for selection in market["selections"]:
                p, a = selection["fair_prob"], selection["fair_american"]
                if not (p > 0.70 and -250 <= a <= 10000):
                    continue
                reasons = []
                if not row.get("olbg"):
                    reasons.append("no captured OLBG event crosswalk")
                if row["source_status"] != "official":
                    reasons.append("official fixture programme not established")
                if row["sample_cap"]:
                    reasons.append("published sample/confidence cap")
                candidates.append({
                    "row_id": row["id"], "sport": row["sport"], "match": row["match"], "start_utc": row["start_utc"],
                    "market_key": market_key, "market": market["market_name"], "selection": selection["label"],
                    "fair_prob": p, "fair_american": a,
                    "decision": "rejected" if reasons else "eligible-needs-analysis", "reasons": reasons,
                    "official_url": row["official_url"] or row.get("official_stats_url", ""),
                    "olbg_url": (row.get("olbg") or {}).get("url", (row.get("olbg") or {}).get("event_url", "")),
                })
    candidate_doc = __import__("json").loads((ri.DATA / "candidates.json").read_text())
    candidate_doc["ri"] = candidates
    ri.dump(ri.DATA / "candidates.json", candidate_doc)

    sport_summary = {}
    for sport in ri.SPORTS:
        sr = [r for r in rows if r["sport"] == sport]
        sp = [p for p in predictions if p["sport"] == sport]
        sport_summary[sport] = {
            "rows": len(sr), "olbg_listed": sum(bool(r.get("olbg")) for r in sr),
            "official_sourced": sum(r["source_status"] == "official" for r in sr),
            "priced": sum(bool(r.get("pick")) for r in sr), "written_high": len(sp),
            "target": 5, "shortfall": max(0, 5 - len(sp)), "shortfall_reason": SHORTFALL[sport] if len(sp) < 5 else "",
        }
    desk = {
        "schema": "olbg4.board-ri.desk/1", "session": "arena/11927acd-olbg4",
        "capture_id": ri.CAPTURE_ID, "captured_utc": ri.MANIFEST["finished_utc"],
        "generated_utc": ri.generated_utc(),
        "olbg_cutoff_utc": ri.BASE_DESK["cutoff_utc"],
        "summary": {
            "rows_total": len(rows), "olbg_listed": sum(bool(r.get("olbg")) for r in rows),
            "official_sourced": sum(r["source_status"] == "official" for r in rows),
            "review_required": sum(r["source_status"] != "official" for r in rows),
            "priced": sum(bool(r.get("pick")) for r in rows), "predictions": len(predictions),
            "high_predictions": len(predictions), "by_sport": sport_summary,
        },
        "confidence_rule": "Written High: probability strictly greater than .70, fair American from -250 through +10000, official fixture, captured OLBG event, no sample cap, and at least ten games per NHL club.",
        "inventory_rule": "The all-matches inventory includes OLBG listings plus clearly labelled official-schedule supplements. Only rows with a captured OLBG event are eligible for written predictions.",
        "rows": rows,
    }
    ri.dump(ri.DATA / "desk.json", desk)
    similarities = [SequenceMatcher(None, a["prediction_text"], b["prediction_text"]).ratio() for i, a in enumerate(predictions) for b in predictions[i + 1:]]
    ri.dump(ri.DATA / "predictions.json", {
        "schema": "olbg4.board-ri.predictions/1", "predictions": predictions,
        "summary": {"total": len(predictions), "confidence_counts": {"High": len(predictions), "Medium": 0, "Low": 0}, "min_words": min(p["word_count"] for p in predictions), "max_words": max(p["word_count"] for p in predictions), "max_similarity": max(similarities, default=0), "sports_covered": len({p["sport"] for p in predictions})},
    })
    flags = make_flags(rows, predictions, candidates)
    ri.dump(ri.DATA / "flags.json", {"schema": "olbg4.board-ri.flags/1", "count": len(flags), "flags": flags})
    ri.dump(ri.DATA / "sources.json", {
        "schema": "olbg4.board-ri.sources/1", "capture_id": ri.CAPTURE_ID,
        "started_utc": ri.MANIFEST["started_utc"], "finished_utc": ri.MANIFEST["finished_utc"],
        "sources": ri.MANIFEST["records"], "failures": ri.MANIFEST.get("failures", []),
        "total": len(ri.MANIFEST["records"]), "failure_count": len(ri.MANIFEST.get("failures", [])),
    })
    ri.dump(ri.DATA / "meta.json", {
        "schema": "olbg4.board-ri.meta/1", "release": "strict-integrity-1",
        "generated_utc": desk["generated_utc"], "capture_id": ri.CAPTURE_ID,
        "base_commit_note": "Built only from committed CA captures and desks; no peer files modified.",
        "counts": desk["summary"], "prediction_ids": [p["prediction_id"] for p in predictions],
    })
    print(f"Built {len(rows)} rows, {len(predictions)} written High predictions, {len(candidates)} RI candidate records, {len(flags)} flags")
    for p in predictions:
        print(p["prediction_id"], p["match"], "|", p["selection"], f"{p['prob']:.4%}", p["fair_american"], f"{p['word_count']} words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

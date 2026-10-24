#!/usr/bin/env python3
"""Build a complete OLBG-event desk from one pinned raw-evidence capture."""
from __future__ import annotations

import copy
import json
import math
import os
import re
import sys
from collections import Counter
from pathlib import Path

import engine
import prose


def latest_capture() -> Path:
    root = engine.DATA / "capture"
    found = sorted(p for p in root.glob("*") if (p / "manifest.json").exists())
    if not found:
        raise SystemExit("No A172 capture found; pass a capture directory explicitly")
    return found[-1]


def parties(name: str) -> tuple[str, str]:
    bits = re.split(r"\s+(?:vs\.?|v|@)\s+", name or "", maxsplit=1, flags=re.I)
    return (bits[0].strip(), bits[1].strip()) if len(bits) == 2 else ((name or "").strip(), "")


def base_event(event: dict) -> dict:
    first, second = parties(event["event"])
    eid = event.get("event_id") or re.sub(r"\W+", "-", event["event"]).strip("-").lower()
    olbg = {
        "event_id": eid, "event": event["event"], "url": event["event_url"],
        "event_url": event["event_url"], "hub_url": event["hub_url"],
        "capture_id": event["hub"], "start_utc": event["start_utc"],
        "listed_tips": len(event.get("tips") or []),
        "observed_markets": sorted({t.get("market", "") for t in event.get("tips") or [] if t.get("market")}),
    }
    return {
        "id": f"olbg_{eid}", "sport": event["sport"], "sport_slug": engine.SLUGS[event["sport"]],
        "competition": "", "side_a": first, "side_b": second,
        "match": event["event"], "start_utc": event["start_utc"], "venue": "",
        "official_url": "", "official_source_name": "", "capture_id": event["hub"],
        "official_sha256": "", "source_status": "review-required", "review_url": event["event_url"],
        "unverified": ["official fixture", "competition", "venue"],
        "evidence": {}, "form": {}, "recent": {}, "sample": "", "sample_cap": True,
        "model": {}, "markets": {}, "pick": None, "analysis_status": "no pick — insufficient official inputs",
        "flags": ["Official fixture programme not matched in this capture; OLBG listing retained and all prices left blank."],
        "olbg": olbg,
    }


def reprice(row: dict) -> None:
    markets = {}
    for key, old in (row.get("markets") or {}).items():
        markets[key] = engine.market(
            old["market_name"], old.get("line"),
            [(s["label"], s["fair_prob"]) for s in old.get("selections", [])], old.get("note", ""),
        )
    row["markets"] = markets


def sample_cap(row: dict) -> bool:
    text = " ".join((row.get("flags") or []) + [(row.get("pick") or {}).get("rule", ""), row.get("sample", "")]).lower()
    if row["sport"] == "Basketball" and row["id"].startswith("fx_nba_"):
        try:
            return int(row["sample"].split()[0]) < 20
        except (ValueError, IndexError):
            return True
    return ("confidence capped" in text or "capped medium" in text or "one-match" in text
            or "one-to-two" in text or "sample too small" in text or "withheld below" in text)


def primary_pick(row: dict) -> None:
    market = (row.get("markets") or {}).get("match_winner")
    if not market or row["source_status"] != "official":
        row["pick"] = None
        return
    choices = [s for s in market["selections"] if s["label"].casefold() != "draw"]
    if not choices:
        row["pick"] = None
        return
    best = max(choices, key=lambda s: s["fair_prob"])
    p, american = best["fair_prob"], best["fair_american"]
    eligible = p > 0.70 and -250 <= american <= 10000 and not row.get("sample_cap")
    if eligible:
        confidence = "High"
        reason = "above 70%, fair price in band, official fixture and adequate sample; written-copy gate still required"
    elif p >= 0.55:
        confidence = "Medium"
        reason = "playable lean, but at least one strict High price/sample/written-copy gate is not met"
    else:
        confidence = "Low"
        reason = "estimated match-winner probability below 55%"
    row["pick"] = {
        "market": market["market_name"], "market_key": "match_winner", "selection": best["label"],
        **{k: best[k] for k in ("fair_prob", "fair_decimal", "fair_american")},
        "confidence": confidence, "in_window": -250 <= american <= 10000, "rule": reason,
    }
    if p > 0.70 and american < -250:
        row["flags"].append("Above 70% but shorter than -250; retained as Medium under the requested price focus.")


def merge_event(event: dict, official: dict | None) -> dict:
    row = base_event(event)
    if not official:
        return row
    inherited_flags = list(official.get("flags") or [])
    olbg = row["olbg"]
    olbg_start = row["start_utc"]
    row.update(copy.deepcopy(official))
    row["olbg"] = olbg
    neutral = row["sport"] in {"Tennis", "Snooker", "Darts", "Cricket", "Gaelic Sports"}
    row["match"] = (f"{row['side_a']} vs {row['side_b']}" if neutral else f"{row['side_a']} at {row['side_b']}") if row.get("side_b") else row["side_a"]
    row["source_status"] = "official"
    row["review_url"] = row["official_url"]
    row["official_sha256"] = ""
    row["unverified"] = ["venue"] if not row.get("venue") else []
    row["flags"] = inherited_flags
    if olbg_start and row.get("start_utc") and olbg_start != row["start_utc"]:
        row["flags"].append(f"OLBG displays {olbg_start}; official programme displays {row['start_utc']}. Official time is published.")
    row["analysis_status"] = "winner lean only — no write-up"
    reprice(row)
    row["sample_cap"] = sample_cap(row)
    return row


def nhl_match(event: dict, rows: list[dict], games: dict) -> dict | None:
    if event["sport"] != "Ice Hockey" or " @ " not in event["event"]:
        return None
    for row in rows:
        if row["sport"] != "Ice Hockey" or not row["id"].startswith("fx_nhl_"):
            continue
        game = games.get(str((row.get("extra") or {}).get("nhl_id") or row["id"].rsplit("_", 1)[-1]))
        if not game:
            continue
        ac, hc = game["awayTeam"]["abbrev"], game["homeTeam"]["abbrev"]
        aa = list(engine.NHL_ALIASES.get(ac, (ac,)))
        ha = list(engine.NHL_ALIASES.get(hc, (hc,)))
        if engine.alias_label_match(event["event"], aa, game["awayTeam"]["commonName"]["default"],
                                    ha, game["homeTeam"]["commonName"]["default"]):
            return row
    return None


def nba_match(event: dict, rows: list[dict]) -> dict | None:
    if event["sport"] != "Basketball" or " @ " not in event["event"]:
        return None
    for row in rows:
        if not row["id"].startswith("fx_nba_"):
            continue
        ac, hc = row["a_code"], row["b_code"]
        aa = list(engine.NBA_ALIASES.get(ac, (ac,)))
        ha = list(engine.NBA_ALIASES.get(hc, (hc,)))
        if engine.alias_label_match(event["event"], aa, row["extra"]["away_name"],
                                    ha, row["extra"]["home_name"]):
            return row
    return None


def mlb_match(event: dict, rows: list[dict]) -> dict | None:
    if event["sport"] != "Baseball" or " @ " not in event["event"]:
        return None
    for row in rows:
        if row["sport"] != "Baseball" or row["side_a"] not in engine.MLB_ALIASES or row["side_b"] not in engine.MLB_ALIASES:
            continue
        away, home = engine.MLB_ALIASES[row["side_a"]], engine.MLB_ALIASES[row["side_b"]]
        if engine.alias_label_match(event["event"], list(away[:-1]), away[-1], list(home[:-1]), home[-1]):
            return row
    return None


def handball_match(event: dict, rows: list[dict], augment) -> dict | None:
    if event["sport"] != "Handball":
        return None
    first, second = parties(event["event"])
    if not second:
        return None
    for row in rows:
        if row["sport"] != "Handball" or not row["id"].startswith("fx_dk_"):
            continue
        # OLBG's 'vs' order is home first; desk rows use away first.
        if (augment.match_score(first, row["side_b"]) >= 0.72
                and augment.match_score(second, row["side_a"]) >= 0.72):
            return row
    return None


def handball_rows(ev: engine.Evidence, cap, augment, cutoff: str, end: str) -> list[dict]:
    table = augment.read_dk_herreligaen(cap)
    programme = engine.danish_programme(ev)
    if not table or not programme:
        return []
    rows = []
    for game in programme:
        if game["home_goals"] is not None or not (cutoff <= game["start_utc"] <= end):
            continue
        home_key, home_score = augment.best_match(game["home"], table)
        away_key, away_score = augment.best_match(game["away"], table)
        if not home_key or not away_key or home_key == away_key:
            continue
        home, away = table[home_key], table[away_key]
        if min(home["played"], away["played"]) < 2:
            continue
        calc = augment.handball_line(table, home_key, away_key)
        if not calc:
            continue
        lh, la = max(calc["lam_h"], 0.4), max(calc["lam_a"], 0.4)
        ph = [engine.pmf(k, lh) for k in range(81)]
        pa = [engine.pmf(k, la) for k in range(81)]
        ph, pa = [p / sum(ph) for p in ph], [p / sum(pa) for p in pa]
        cells = [(h, a, ph[h] * pa[a]) for h in range(81) for a in range(81)]
        hw = sum(p for h, a, p in cells if h > a)
        draw = sum(p for h, a, p in cells if h == a)
        aw = sum(p for h, a, p in cells if h < a)
        if lh >= la:
            handicap = engine.market("Handicap 2.5 (regulation)", -2.5, [
                (f"{game['away']} +2.5", sum(p for h, a, p in cells if h - a < 3)),
                (f"{game['home']} -2.5", sum(p for h, a, p in cells if h - a >= 3))])
        else:
            handicap = engine.market("Handicap 2.5 (regulation)", 2.5, [
                (f"{game['away']} -2.5", sum(p for h, a, p in cells if a - h >= 3)),
                (f"{game['home']} +2.5", sum(p for h, a, p in cells if a - h < 3))])
        total_line = round(calc["league_avg"] * 2) + 0.5
        over = sum(p for h, a, p in cells if h + a > total_line)
        row = {
            "id": "fx_dk_" + re.sub(r"\W+", "_", f"{game['start_utc'][:10]}_{game['away']}_{game['home']}"),
            "sport": "Handball", "sport_slug": "handball",
            "competition": "Danish Herreligaen 2026-27", "side_a": game["away"], "side_b": game["home"],
            "start_utc": game["start_utc"], "venue": "", "official_url": game["source_url"],
            "official_source_name": "Tophaandbold official Herreligaen match programme",
            "capture_id": "dk_herreligaen_program", "evidence": {
                "away_played": away["played"], "away_gf": away["gf"], "away_ga": away["ga"],
                "home_played": home["played"], "home_gf": home["gf"], "home_ga": home["ga"],
                "league_goals_per_team_game": round(calc["league_avg"], 3),
                "expected_goals_away": round(la, 2), "expected_goals_home": round(lh, 2),
                "table_source": away["source"],
            },
            "form": {
                "away": f"{away['won']}-{away['drawn']}-{away['lost']} ({away['points']} pts, {away['gf']}:{away['ga']})",
                "home": f"{home['won']}-{home['drawn']}-{home['lost']} ({home['points']} pts, {home['gf']}:{home['ga']})",
            },
            "recent": {"away": engine.danish_recent(programme, game["away"], game["start_utc"]),
                       "home": engine.danish_recent(programme, game["home"], game["start_utc"])},
            "sample": f"{min(home['played'], away['played'])} league matches per side",
            "sample_cap": min(home["played"], away["played"]) < 6,
            "model": {"name": "independent Poisson goals with played/(played+8) rate pooling", "home_exp": round(lh, 2), "away_exp": round(la, 2)},
            "markets": {
                "match_winner": engine.market("Match Result (1X2, regulation)", None, [
                    (f"{game['home']} (home)", hw), ("Draw", draw), (f"{game['away']} (away)", aw)]),
                "handicap": handicap,
                "total": engine.market(f"Total Goals {total_line} (regulation)", total_line, [
                    (f"Over {total_line}", over), (f"Under {total_line}", 1 - over)]),
            },
            "pick": None, "flags": [],
            "extra": {"home_table_name": home_key, "away_table_name": away_key},
        }
        rows.append(row)
    return rows


def enrich_nhl(row: dict, ev: engine.Evidence, standings: dict, games: dict) -> None:
    game = games[str((row.get("extra") or {}).get("nhl_id") or row["id"].rsplit("_", 1)[-1])]
    away, home = standings[game["awayTeam"]["abbrev"]], standings[game["homeTeam"]["abbrev"]]
    league_goals = sum(t["gf"] + t["ga"] for t in standings.values()) / sum(t["gp"] for t in standings.values())
    lh, la = engine.nhl_lambdas(away, home, league_goals)
    sample_ok = min(away["gp"], home["gp"]) >= 10 and game.get("gameState") in ("FUT", "PRE")
    row["a_code"], row["b_code"] = away["code"], home["code"]
    row["evidence"] = {
        "league_goals_per_game": round(league_goals, 3),
        "away_gf_pg": round(away["gf_pg"], 3), "away_ga_pg": round(away["ga_pg"], 3),
        "home_gf_pg": round(home["gf_pg"], 3), "home_ga_pg": round(home["ga_pg"], 3),
        "expected_goals_away": round(la, 2), "expected_goals_home": round(lh, 2),
        "standings_source": ev.url("nhl_standings"),
    }
    row["form"] = {
        "away": f"{away['w']}-{away['l']}-{away['otl']} ({away['pts']} pts, L10 {away['l10']}, streak {away['streak']})",
        "home": f"{home['w']}-{home['l']}-{home['otl']} ({home['pts']} pts, L10 {home['l10']}, streak {home['streak']})",
        "away_home_away": away["road"], "home_home_away": home["home"],
    }
    row["recent"] = {"away": engine.nhl_recent(ev, away["code"], row["start_utc"]),
                     "home": engine.nhl_recent(ev, home["code"], row["start_utc"])}
    row["sample"] = f"{min(away['gp'], home['gp'])} games played (minimum of the two clubs)"
    row["sample_cap"] = not sample_ok
    row["model"] = {"name": "independent Poisson goals; 70% club-rate pooling plus 30% league prior",
                    "home_exp": round(lh, 2), "away_exp": round(la, 2), "home_adv": 1.06,
                    "away_location_factor": 0.94, "moneyline_shrinkage": 0.88}
    row["markets"] = engine.nhl_markets(row["side_a"], row["side_b"], lh, la, expanded=sample_ok)


def flag_records(rows: list[dict], predictions: list[dict], candidates: list[dict], ev: engine.Evidence) -> list[dict]:
    flags = []
    for row in rows:
        if row["source_status"] != "official":
            flags.append({"group": "Official fixture source required", "kind": "unverified-fixture",
                          "title": row["match"], "detail": "OLBG listing observed, but no matching official programme was captured. Official fields and prices remain blank.",
                          "source_url": row["olbg"]["url"], "row_id": row["id"], "sport": row["sport"]})
        elif not row.get("pick"):
            flags.append({"group": "No originated winner line", "kind": "unpriced",
                          "title": row["match"], "detail": "; ".join(row.get("flags") or ["Official fixture confirmed, but the captured inputs do not support a responsible winner, handicap and total line."]),
                          "source_url": row["official_url"], "row_id": row["id"], "sport": row["sport"]})
        if row["source_status"] == "official":
            for field in row.get("unverified") or []:
                flags.append({"group": "Unsupported fields left blank", "kind": "unverified-field",
                              "title": f"{row['match']} — {field}", "detail": f"The captured official payload does not confirm {field}; the value remains blank.",
                              "source_url": row["official_url"], "row_id": row["id"], "sport": row["sport"]})
        for note in row.get("flags") or []:
            if "displays" in note or "venue" in note.lower():
                flags.append({"group": "Row irregularities", "kind": "row-note", "title": row["match"],
                              "detail": note, "source_url": row["official_url"] or row["olbg"]["url"],
                              "row_id": row["id"], "sport": row["sport"]})
    for failure in ev.manifest.get("failures", []):
        flags.append({"group": "Capture failures", "kind": "capture-failure", "title": failure.get("id") or "Unnamed source",
                      "detail": f"HTTP {failure.get('status')}: {failure.get('error') or 'capture failed'}",
                      "source_url": failure.get("url") or "", "row_id": "", "sport": failure.get("sport") or ""})
    for candidate in candidates:
        if candidate["decision"] == "eligible-evidence-incomplete":
            flags.append({"group": "Written-pick evidence gaps", "kind": "eligible-evidence-incomplete",
                          "title": f"{candidate['match']} — {candidate['selection']}",
                          "detail": "The numerical and source gates passed, but recent-result/player evidence or a sport-specific natural write-up is incomplete; not promoted to High.",
                          "source_url": candidate["official_url"], "row_id": candidate["row_id"], "sport": candidate["sport"]})
    for sport in engine.SPORTS:
        count = sum(p["sport"] == sport for p in predictions)
        if count < 5:
            numeric = len({c["row_id"] for c in candidates if c["sport"] == sport})
            flags.append({"group": "Daily target shortfalls", "kind": "shortfall",
                          "title": f"{sport}: {count} of five written High predictions",
                          "detail": f"{numeric} event(s) produced a numerical candidate in the strict band. No quota padding: unavailable official fixtures, samples, recent form, player evidence or qualifying prices keep the remaining slots blank.",
                          "source_url": "", "row_id": "", "sport": sport})
    flags.append({"group": "Availability information", "kind": "team-news-not-captured",
                  "title": "No official injury or lineup report captured",
                  "detail": "Written picks use official fixture, standings, results and player-statistics payloads only. No injury or lineup availability claim is made.",
                  "source_url": "https://www.nhl.com/news/", "row_id": "", "sport": ""})
    return flags


def main() -> int:
    cap_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_capture()
    ev = engine.Evidence(cap_dir)
    cutoff = ev.manifest["started_utc"]
    end = "2026-11-08T23:59:59Z"
    os.environ["A172_WINDOW_START"] = cutoff
    os.environ["A172_WINDOW_END"] = end
    import parse as P
    import originate
    import augment

    cap = P.Capture(str(cap_dir))
    events = [e for e in P.read_olbg(cap) if e["sport"] in engine.SPORTS and cutoff <= (e.get("start_utc") or "") <= end]
    events.sort(key=lambda e: (e["start_utc"], e["sport"], e["event"], e["event_url"]))
    _, base_rows = originate.build(str(cap_dir))
    tables = augment.build_tables(cap)
    for row in base_rows:
        augment.price_row(row, tables)
    official = [r for r in base_rows if r.get("start_utc") and cutoff <= r["start_utc"] <= end
                and not (r.get("capture_id") or "").startswith("olbg_") and not r["id"].startswith("ca_olbg")]
    official.extend(engine.nba_official_rows(ev))
    official.extend(handball_rows(ev, cap, augment, cutoff, end))
    attached = {r["olbg"]["event_url"]: r for r in official if (r.get("olbg") or {}).get("event_url")}
    games = engine.nhl_games(ev)
    standings = engine.nhl_standings(ev) if ev.exists("nhl_standings") else {}
    nhl_base = [r for r in official if r["sport"] == "Ice Hockey"]
    nba_base = [r for r in official if r["id"].startswith("fx_nba_")]
    mlb_base = [r for r in official if r["sport"] == "Baseball"]
    dk_base = [r for r in official if r["id"].startswith("fx_dk_")]

    rows, duplicates = [], set()
    for event in events:
        source = attached.get(event["event_url"])
        source = source or nhl_match(event, nhl_base, games) or nba_match(event, nba_base)
        source = source or mlb_match(event, mlb_base) or handball_match(event, dk_base, augment)
        row = merge_event(event, source)
        if source and row["id"] in duplicates:
            row["id"] = row["id"] + "_" + str(event["event_id"])
            row["flags"].append("Multiple OLBG cards reference one official event; retained as separate listing observations.")
        if source:
            duplicates.add(row["id"])
            row["official_sha256"] = ev.sha(row["capture_id"])
        if row["sport"] == "Ice Hockey" and row["source_status"] == "official" and row["id"].startswith("fx_nhl_"):
            enrich_nhl(row, ev, standings, games)
        primary_pick(row)
        row["unverified"] = list(row.get("unverified") or [])
        rows.append(row)

    rows.sort(key=lambda r: (r["start_utc"], r["sport"], r["match"], r["id"]))
    candidates = []
    for row in rows:
        if row["source_status"] != "official" or row.get("sample_cap"):
            continue
        for market_key, market in row["markets"].items():
            for selection in market["selections"]:
                p, a = selection["fair_prob"], selection["fair_american"]
                if p > 0.70 and -250 <= a <= 10000:
                    candidates.append({"row_id": row["id"], "sport": row["sport"], "match": row["match"],
                                       "start_utc": row["start_utc"], "market_key": market_key,
                                       "market": market["market_name"], "selection": selection["label"],
                                       "fair_prob": p, "fair_decimal": selection["fair_decimal"], "fair_american": a,
                                       "decision": "eligible-evidence-incomplete", "official_url": row["official_url"],
                                       "olbg_url": row["olbg"]["url"]})
    market_priority = {"match_winner": 0, "regulation_handicap": 1, "handicap": 2,
                       "total": 3, "regulation_3way": 9}
    candidates.sort(key=lambda c: (c["start_utc"], c["sport"], c["row_id"], -c["fair_prob"],
                                   market_priority.get(c["market_key"], 4), c["market_key"]))

    predictions = []
    chosen_rows = set()
    for candidate in candidates:
        if candidate["row_id"] in chosen_rows:
            candidate["decision"] = "eligible-alternate-not-selected"
            continue
        row = next(r for r in rows if r["id"] == candidate["row_id"])
        prefix = {"Ice Hockey": "IH", "Handball": "HB"}.get(row["sport"], "X")
        prediction = prose.make_prediction(row, candidate, ev, f"A172-{prefix}-{len(predictions)+1:03d}")
        if not prediction:
            continue
        candidate["decision"] = "published"
        prediction["candidate_probability"] = candidate["fair_prob"]
        predictions.append(prediction)
        chosen_rows.add(row["id"])
        row["analysis_status"] = "fully written prediction"
    predictions.sort(key=lambda p: (-p["prob"], p["start_utc"], p["prediction_id"]))

    # A numerical High label is never left without its own full analysis.
    for row in rows:
        pick = row.get("pick")
        if pick and pick["confidence"] == "High":
            if not any(p["row_id"] == row["id"] and p["selection"] == pick["selection"] for p in predictions):
                pick["confidence"] = "Medium"
                pick["rule"] = "numerical candidate, but this exact selection has no fully written analysis; capped Medium"

    by_sport = {}
    for sport in engine.SPORTS:
        sport_rows = [r for r in rows if r["sport"] == sport]
        count = sum(p["sport"] == sport for p in predictions)
        by_sport[sport] = {
            "slug": engine.SLUGS[sport], "rows": len(sport_rows),
            "official_sourced": sum(r["source_status"] == "official" for r in sport_rows),
            "priced": sum(bool(r.get("pick")) for r in sport_rows),
            "markets": sum(len(r.get("markets") or {}) for r in sport_rows),
            "written_high": count, "target": 5, "shortfall": max(0, 5 - count),
        }
    flags = flag_records(rows, predictions, candidates, ev)
    generated = os.environ.get("A172_GENERATED_UTC") or ev.manifest["finished_utc"]
    taxonomy = {}
    for event in events:
        for tip in event.get("tips") or []:
            if tip.get("market"):
                taxonomy.setdefault(event["sport"], {}).setdefault(tip["market"], 0)
                taxonomy[event["sport"]][tip["market"]] += 1

    desk = {
        "schema": "olbg4.a172.desk/1", "session": "arena/a172d5b9-olbg4",
        "capture_id": cap_dir.name, "captured_utc": ev.manifest["finished_utc"], "generated_utc": generated,
        "olbg_cutoff_utc": cutoff, "window_end_utc": end,
        "summary": {"rows_total": len(rows), "olbg_listed": len(rows),
                    "official_sourced": sum(r["source_status"] == "official" for r in rows),
                    "review_required": sum(r["source_status"] != "official" for r in rows),
                    "priced": sum(bool(r.get("pick")) for r in rows),
                    "predictions": len(predictions), "high_predictions": len(predictions),
                    "by_sport": by_sport},
        "confidence_rule": "Written High requires probability >70%, fair American -250…+10000, official fixture, captured OLBG event, adequate sample, recent-result evidence and a complete natural write-up. Other priced rows are Low/Medium.",
        "inventory_rule": "Every upcoming OLBG listing in the 15 requested sport hubs at the capture cutoff. Official schedules confirm or supplement evidence but are never used to invent an OLBG listing.",
        "price_rule": "Fair decimal is 1/probability; American is calculated directly from the unrounded displayed probability at four decimals. No OLBG or bookmaker price enters any calculation.",
        "olbg_market_taxonomy": taxonomy, "rows": rows,
    }
    engine.DATA.mkdir(parents=True, exist_ok=True)
    dump = lambda name, value: (engine.DATA / name).write_text(json.dumps(value, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    dump("desk.json", desk)
    dump("predictions.json", {"schema": "olbg4.a172.predictions/1", "predictions": predictions,
                              "summary": {"total": len(predictions), "min_words": min((p["word_count"] for p in predictions), default=0),
                                          "sports_covered": len({p["sport"] for p in predictions})}})
    dump("candidates.json", {"schema": "olbg4.a172.candidates/1", "rule": ">70% and fair American -250…+10000 before source/sample/prose gates", "candidates": candidates})
    dump("flags.json", {"schema": "olbg4.a172.flags/1", "count": len(flags), "flags": flags})
    dump("sources.json", {"schema": "olbg4.a172.sources/1", "capture_id": cap_dir.name,
                          "started_utc": ev.manifest["started_utc"], "finished_utc": ev.manifest["finished_utc"],
                          "sources": ev.manifest["records"], "failures": ev.manifest.get("failures", []),
                          "total": len(ev.manifest["records"]), "failure_count": len(ev.manifest.get("failures", []))})
    payload_audit = [{"id": r["id"], "url": r["url"], "manifest_sha256": r["sha256"],
                      "actual_sha256": ev.sha(r["id"]), "sha_match": ev.sha(r["id"]) == r["sha256"],
                      "bytes": r["bytes"], "status": r["status"]} for r in ev.manifest["records"]]
    audit = {"schema": "olbg4.a172.audit/1", "generated_utc": generated, "capture_id": cap_dir.name,
             "summary": {"payloads_ok": sum(x["sha_match"] for x in payload_audit), "payloads_total": len(payload_audit),
                         "capture_failures": len(ev.manifest.get("failures", [])), "rows": len(rows),
                         "official_rows": desk["summary"]["official_sourced"], "review_rows": desk["summary"]["review_required"],
                         "official_supplements_excluded": len(official) - len({r["id"] for r in rows if r["source_status"] == "official"})},
             "payloads": payload_audit,
             "rows": [{"row_id": r["id"], "sport": r["sport"], "source_status": r["source_status"],
                       "capture_id": r["capture_id"], "official_url": r["official_url"], "olbg_url": r["olbg"]["url"],
                       "official_sha256": r["official_sha256"], "unverified": r.get("unverified") or [],
                       "flags": r.get("flags") or []} for r in rows]}
    dump("audit.json", audit)
    dump("meta.json", {"schema": "olbg4.a172.meta/1", "release": "complete-olbg-inventory-1",
                       "generated_utc": generated, "capture_id": cap_dir.name, "counts": desk["summary"],
                       "prediction_ids": [p["prediction_id"] for p in predictions]})
    print(json.dumps(desk["summary"], indent=2))
    print(f"Built {len(rows)} OLBG rows; {len(candidates)} numerical candidates; {len(predictions)} written High picks; {len(flags)} flags")
    for p in predictions:
        print(p["prediction_id"], p["match"], "|", p["selection"], f"{p['prob']:.2%}", p["fair_american"], p["word_count"], "words")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

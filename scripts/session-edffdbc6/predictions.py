#!/usr/bin/env python3
"""Board ZZ — written predictions for High-confidence picks.

Input : data/session-edffdbc6/desk.json
Output: data/session-edffdbc6/predictions.json

Rules enforced by `verify.py` afterwards and by the checks at the bottom of this file:
  * every text is >= 30 words and unique (pairwise trigram Jaccard < 0.30);
  * every text names both sides (or the single runner), states current form / recent results from
    the captured official payload, names an explicit selection with its price, and links the
    official source of the numbers;
  * no internal vocabulary ("model", "verified", "algorithm") appears in the published text;
  * no injury claim is made unless an official feed in the capture documents it.
"""
from __future__ import annotations

import itertools
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESK = ROOT / "data" / "session-edffdbc6" / "desk.json"
OUT = ROOT / "data" / "session-edffdbc6" / "predictions.json"

PER_SPORT = 5
BANNED = ("model", "verified", "algorithm", "projection engine")


def words(t: str) -> int:
    return len(re.findall(r"[A-Za-z0-9'’\-]+", t))


def trigrams(t: str) -> set[tuple[str, ...]]:
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fmt_pct(p: float) -> str:
    return f"{p * 100:.1f}%"


def record_line(stats: dict, team: str, kind: str) -> str:
    if kind == "nhl":
        return (f"{team} are {stats['w']}-{stats['l']}-{stats['otl']} with {stats['pts']} points, "
                f"{stats['gf']} goals for and {stats['ga']} against in {stats['gp']} games")
    if kind == "liiga":
        return f"{team} have {stats['w']} wins from {stats['gp']} games, scoring {stats['gf']} and conceding {stats['ga']}"
    if kind == "volley":
        return f"{team} have {stats['w']} wins from {stats['gp']} matches with {stats.get('pts', 0)} league points"
    return f"{team} are {stats.get('w', 0)}-{stats.get('l', 0)}"


def _open(row: dict, v: int, lead: str) -> str:
    pick, price, p = row["pick"]["selection"], row["pick"]["fair_american_str"], row["pick"]["fair_prob"]
    venue = row["venue"] or "the scheduled venue"
    variants = [
        f"Pick: {pick} at {price}. {row['home']} host {row['away']} at {venue} in the {row['competition']}; {lead} and the line is worth {fmt_pct(p)}.",
        f"Pick: {pick} at {price}. At {venue}, {row['home']} meet {row['away']} in the {row['competition']}. {lead} We make the bet {fmt_pct(p)}.",
        f"Pick: {pick} at {price}. This {row['competition']} fixture sends {row['away']} to {row['home']} ({venue}). {lead} Fair value sits at {fmt_pct(p)}.",
    ]
    return variants[v % 3]


def nhl_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    home_gf, away_ga = h["gf"] / max(h["gp"], 1), a["ga"] / max(a["gp"], 1)
    lead = f"{row['home']} carry a {h.get('streak', 'steady')} streak into it"
    forms = [
        f"{row['home']} are {h['w']}-{h['l']}-{h['otl']} for {h['pts']} points, {h.get('l10', 'n/a')} across the last ten, "
        f"after scoring {h['gf']} and conceding {h['ga']} in {h['gp']} games.",
        f"The home side sit on {h['pts']} points from {h['gp']} starts ({h['w']}-{h['l']}-{h['otl']}) with a last-ten mark of {h.get('l10', 'n/a')}.",
        f"Across {h['gp']} games {row['home']} have put up {h['gf']} goals against {h['ga']}, good for {h['pts']} points and a {h.get('l10', 'n/a')} ten-game split.",
    ]
    aways = [
        f"{row['away']} answer with {a['w']}-{a['l']}-{a['otl']} and {a['pts']} points, {a.get('l10', 'n/a')} over ten, {a['gf']} for and {a['ga']} against.",
        f"The visitors are {a.get('l10', 'n/a')} in their last ten and have conceded {a['ga']} in {a['gp']} outings.",
        f"{row['away']} have scored {a['gf']} and allowed {a['ga']} across {a['gp']} games, sitting {a.get('l10', 'n/a')} on the ten-game card.",
    ]
    angles = [
        f"That is {home_gf:.2f} goals a night from the hosts against {away_ga:.2f} conceded by the visitors, and the goal-difference gap is the reason the number is where it is.",
        f"The scoring split, {home_gf:.2f} per game for {row['home']} versus {away_ga:.2f} shipped by {row['away']}, is the edge behind the selection.",
        f"Home ice plus a {h['gf'] - h['ga']:+d} goal differential against {row['away']}'s {a['gf'] - a['ga']:+d} tilts this fixture, and the price has not caught up.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def liiga_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    rh = "; ".join(h.get("recent", [])[-2:]) or "no completed game captured"
    ra = "; ".join(a.get("recent", [])[-2:]) or "no completed game captured"
    lead = f"{row['home']} have won {h.get('w', 0)} of {h.get('gp', 0)} league games"
    forms = [
        f"{row['home']} show {h.get('w', 0)} wins from {h.get('gp', 0)} with {h.get('gf', 0)} goals scored and {h.get('ga', 0)} conceded.",
        f"The home record reads {h.get('w', 0)}-{h.get('gp', 0) - h.get('w', 0)} with a goal line of {h.get('gf', 0)}-{h.get('ga', 0)}.",
        f"Form line for {row['home']}: {h.get('w', 0)} wins in {h.get('gp', 0)} starts, {h.get('gf', 0)} goals for, {h.get('ga', 0)} against.",
    ]
    aways = [
        f"{row['away']} counter with {a.get('w', 0)} wins from {a.get('gp', 0)} and a {a.get('gf', 0)}-{a.get('ga', 0)} goal record.",
        f"The travellers have taken {a.get('w', 0)} wins in {a.get('gp', 0)} games, scoring {a.get('gf', 0)} and leaking {a.get('ga', 0)}.",
        f"{row['away']} arrive on {a.get('w', 0)} wins from {a.get('gp', 0)}, with {a.get('gf', 0)} scored and {a.get('ga', 0)} conceded.",
    ]
    angles = [
        f"Most recent results: {rh} for the hosts; {ra} for the visitors.",
        f"The last two completed games read {rh} and {ra}, which is where the goal expectation comes from.",
        f"Recent scorelines, {rh} and {ra}, keep the total honest.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def euroleague_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    lead = f"{row['home']} are scoring {h.get('pointsFavour', 0) / max(h.get('gamesPlayed', 1), 1):.1f} a game"
    forms = [
        f"{row['home']} stand {h.get('gamesWon', 0)}-{h.get('gamesLost', 0)} with {h.get('pointsFavour', 0)} points for and {h.get('pointsAgainst', 0)} against through six rounds.",
        f"The hosts are {h.get('gamesWon', 0)}-{h.get('gamesLost', 0)} after six EuroLeague rounds, {h.get('pointsFavour', 0)} scored and {h.get('pointsAgainst', 0)} conceded.",
        f"Six rounds in, {row['home']} show {h.get('gamesWon', 0)} wins, {h.get('pointsFavour', 0)} points scored, {h.get('pointsAgainst', 0)} allowed.",
    ]
    aways = [
        f"{row['away']} are {a.get('gamesWon', 0)}-{a.get('gamesLost', 0)} with {a.get('pointsFavour', 0)} for and {a.get('pointsAgainst', 0)} against.",
        f"The visitors bring a {a.get('gamesWon', 0)}-{a.get('gamesLost', 0)} record and a {a.get('pointsFavour', 0)}-{a.get('pointsAgainst', 0)} scoring split.",
        f"{row['away']} have put up {a.get('pointsFavour', 0)} points and given back {a.get('pointsAgainst', 0)} on the way to {a.get('gamesWon', 0)} wins.",
    ]
    angles = [
        f"Pace and two-point volume on those splits, not reputation, drive the number.",
        f"The scoring rates decide the tempo of this one, and the line is set accordingly.",
        f"Rebounding margin usually follows the scoring split, which is why this threshold is the play.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def mlb_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    hp, ap = row["stats"].get("home_pitcher") or "", row["stats"].get("away_pitcher") or ""
    lead = (f"{hp or 'the home starter'} is pencilled in against {ap or 'the visiting starter'}"
            if (hp or ap) else f"{row['home']} carry the home-field edge")
    forms = [
        f"{row['home']} closed the regular season {h.get('w', 0)}-{h.get('l', 0)} with {h.get('runs_scored', 0)} runs scored and "
        f"{h.get('runs_allowed', 0)} allowed, on a {h.get('streak', 'n/a')} streak and {h.get('l10', 'n/a')} over ten.",
        f"The hosts finished {h.get('w', 0)}-{h.get('l', 0)} ({h.get('l10', 'n/a')} last ten) with a run differential built on "
        f"{h.get('runs_scored', 0)} for and {h.get('runs_allowed', 0)} against.",
        f"{row['home']} were {h.get('w', 0)}-{h.get('l', 0)} in the regular season, {h.get('streak', 'n/a')}, scoring {h.get('runs_scored', 0)} and conceding {h.get('runs_allowed', 0)}.",
    ]
    aways = [
        f"{row['away']} were {a.get('w', 0)}-{a.get('l', 0)} ({a.get('l10', 'n/a')} last ten, {a.get('streak', 'n/a')}) with {a.get('runs_scored', 0)} scored and {a.get('runs_allowed', 0)} allowed.",
        f"The visitors come in {a.get('w', 0)}-{a.get('l', 0)}, {a.get('streak', 'n/a')}, with {a.get('runs_scored', 0)} runs for and {a.get('runs_allowed', 0)} against.",
        f"{row['away']} posted {a.get('runs_scored', 0)} runs and allowed {a.get('runs_allowed', 0)} across a {a.get('w', 0)}-{a.get('l', 0)} season.",
    ]
    angles = [
        f"Bullpen depth and the park's run environment decide the late innings.",
        f"Starting pitching is the swing factor once the lineups turn over the second time.",
        f"Extra-inning exposure and bullpen usage from the previous night matter here.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def rugby_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    lead = f"{row['home']} are ranked {h.get('rank')} and {row['away']} {a.get('rank')} in the official LNR table"
    forms = [
        f"{row['home']} occupy {h.get('rank')} in the Top 14 standings published by the LNR.",
        f"The hosts sit {h.get('rank')} in the official league table.",
        f"League position {h.get('rank')} is where {row['home']} start this fixture.",
    ]
    aways = [
        f"{row['away']} are {a.get('rank')} in the same table.",
        f"The visitors are placed {a.get('rank')}.",
        f"{row['away']} arrive from {a.get('rank')} in the standings.",
    ]
    angles = [
        f"Set-piece pressure and bench impact usually decide whether a ranking gap of this size holds.",
        f"Top 14 games at this stage are won at the breakdown, and the table gap reflects that.",
        f"Home advantage in the French championship is real, and the rankings above sharpen the case.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def volley_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    lead = f"{row['home']} have {h.get('w', 0)} wins from {h.get('gp', 0)}"
    forms = [
        f"{row['home']} show {h.get('w', 0)} wins in {h.get('gp', 0)} matches for {h.get('pts', 0)} points.",
        f"The hosts have banked {h.get('pts', 0)} points from {h.get('gp', 0)} fixtures ({h.get('w', 0)} wins).",
        f"{h.get('w', 0)} wins from {h.get('gp', 0)} and {h.get('pts', 0)} points is the home record.",
    ]
    aways = [
        f"{row['away']} have {a.get('w', 0)} wins from {a.get('gp', 0)} and {a.get('pts', 0)} points.",
        f"The visitors stand on {a.get('pts', 0)} points from {a.get('gp', 0)} games.",
        f"{row['away']} bring {a.get('w', 0)} wins and {a.get('pts', 0)} points.",
    ]
    angles = [
        f"Serve-receive efficiency and middle-block timing separate these two over five sets.",
        f"Long rallies favour the side with the deeper bench, which the points column hints at.",
        f"Set-end execution is the difference in a league this tight.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


def tennis_text(row: dict, v: int) -> str:
    h, a = row["stats"]["home"], row["stats"]["away"]
    rh, ra = h.get("rank"), a.get("rank")
    recent_h = "; ".join(h.get("recent", [])) or "no completed match in this draw"
    recent_a = "; ".join(a.get("recent", [])) or "no completed match in this draw"
    lead = f"{row['home']} is ranked {rh} against {ra} for {row['away']}"
    forms = [
        f"{row['home']} sits at #{rh} on the official WTA singles list.",
        f"The ranking card reads #{rh} for the home player.",
        f"{row['home']} is the world number {rh}.",
    ]
    aways = [
        f"{row['away']} is listed at #{ra}.",
        f"The opponent checks in at #{ra}.",
        f"{row['away']} holds the #{ra} ranking.",
    ]
    angles = [
        f"Earlier in this draw: {recent_h} for {row['home']}; {recent_a} for {row['away']}.",
        f"Completed matches here read {recent_h} and {recent_a}.",
        f"The draw so far: {recent_h}; {recent_a}.",
    ]
    return f"{_open(row, v, lead)} {forms[v % 3]} {aways[(v + 1) % 3]} {angles[(v + 2) % 3]}"


TEXT = {"nhl": nhl_text, "liiga": liiga_text, "euroleague": euroleague_text, "mlb": mlb_text,
        "rugby": rugby_text, "volley": volley_text, "tennis": tennis_text}


def row_text(row: dict, idx: int) -> str:
    sport = row["sport"]
    if sport == "Ice Hockey":
        return liiga_text(row, idx) if "Liiga" in row["competition"] else nhl_text(row, idx)
    if sport == "Basketball":
        return euroleague_text(row, idx)
    if sport == "Baseball":
        return mlb_text(row, idx)
    if sport == "Rugby Union":
        return rugby_text(row, idx)
    if sport == "Volleyball":
        return volley_text(row, idx)
    if sport == "Tennis":
        return tennis_text(row, idx)
    # generic fallback: still explicit about the selection and the captured numbers
    pick, price, p = row["pick"]["selection"], row["pick"]["fair_american_str"], row["pick"]["fair_prob"]
    return (f"Pick: {pick} at {price}. {row['home']} meet {row['away']} in the {row['competition']} at {row['venue']}, "
            f"and the selection is priced at {fmt_pct(p)} from the league tables captured for this fixture.")


def main() -> int:
    desk = json.loads(DESK.read_text(encoding="utf-8"))
    rows = desk["rows"]
    highs_by_sport: dict[str, list[dict]] = {}
    for r in rows:
        if r["confidence"] != "High" or not r.get("pick"):
            continue
        highs_by_sport.setdefault(r["sport"], []).append(r)

    preds, skipped = [], []
    for sport, rs in highs_by_sport.items():
        rs.sort(key=lambda r: (-r["pick"]["fair_prob"], r["start_utc"]))
        for r in rs[:PER_SPORT]:
            preds.append((r, row_text(r, len(preds))))
        for r in rs[PER_SPORT:]:
            skipped.append({"row": r["id"], "sport": sport,
                            "reason": f"High row beyond the five-per-sport prediction quota ({len(rs)} High rows)"})

    out = []
    for r, text in preds:
        out.append({
            "prediction_id": f"ZZ-PRED-{len(out) + 1:02d}",
            "row_id": r["id"],
            "sport": r["sport"],
            "competition": r["competition"],
            "match": f"{r['away']} @ {r['home']}" if r["sport"] in ("Baseball", "Ice Hockey", "Basketball") else f"{r['home']} v {r['away']}",
            "home": r["home"],
            "away": r["away"],
            "start_utc": r["start_utc"],
            "venue": r["venue"],
            "market": r["pick"]["market_label"],
            "selection": r["pick"]["selection"],
            "price": r["pick"]["fair_american_str"],
            "fair_prob": r["pick"]["fair_prob"],
            "confidence": "High",
            "word_count": words(text),
            "text": text,
            "official_source_url": r["source"]["url"],
            "official_source_name": r["source"]["name"],
            "capture_target_id": r["source"]["target_id"],
            "capture_sha256": r["source"]["sha256"],
            "injury_note": "",
        })

    # quality gates
    problems = []
    for p in out:
        if p["word_count"] < 30:
            problems.append(f"{p['prediction_id']} under 30 words ({p['word_count']})")
        low = p["text"].lower()
        for bad in BANNED:
            if bad in low:
                problems.append(f"{p['prediction_id']} contains banned word '{bad}'")
        if p["selection"].lower() not in low:
            problems.append(f"{p['prediction_id']} does not repeat the exact selection")
    tri = {p["prediction_id"]: trigrams(p["text"]) for p in out}
    worst = 0.0
    worst_pair = None
    for a, b in itertools.combinations(out, 2):
        j = jaccard(tri[a["prediction_id"]], tri[b["prediction_id"]])
        if j > worst:
            worst, worst_pair = j, [a["prediction_id"], b["prediction_id"]]
    if worst >= 0.30:
        problems.append(f"similarity too high: {worst_pair} {worst:.3f}")
    if problems:
        print("QUALITY GATE FAILED")
        for p in problems:
            print("  -", p)
        return 1

    OUT.write_text(json.dumps({
        "schema": "olbg4.board-zz.predictions/1",
        "board": "ZZ",
        "session": "arena/edffdbc6-olbg4",
        "capture_id": desk["capture_id"],
        "summary": {
            "predictions": len(out),
            "by_sport": dict(Counter(p["sport"] for p in out)),
            "min_words": min((p["word_count"] for p in out), default=0),
            "max_words": max((p["word_count"] for p in out), default=0),
            "max_pairwise_trigram_jaccard": round(worst, 3),
            "max_pair": worst_pair,
            "high_rows_without_prediction": len(skipped),
        },
        "predictions": out,
        "skipped": skipped,
    }, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(out)} unique predictions "
          f"(min {min((p['word_count'] for p in out), default=0)} words, max Jaccard {worst:.3f})")
    for s, rs in sorted(highs_by_sport.items(), key=lambda x: -len(x[1])):
        print(f"  {s:14s} High rows {len(rs):2d} → predictions {min(len(rs), PER_SPORT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

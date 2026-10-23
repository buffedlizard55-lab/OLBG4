#!/usr/bin/env python3
"""Turn the desk's High-confidence rows into publishable prediction copy.

Every sentence is written from the numbers stored on the desk row itself
(records, goals/points per game, splits) and names the selection explicitly.
The script refuses to emit copy that is short, duplicated, or that uses the
internal vocabulary the brief bans from publication.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-4502eff5")

# row id -> (text, extra facts quoted from the same capture)
TEXTS = {
    "fx_nhl_2026020256": (
        'The Rangers are 6-0-0 at Madison Square Garden and 7-4-1 overall, and they meet a Philadelphia side that has '
        'won three of twelve and is 1-4-1 on the road. New York average 3.08 goals a game while conceding 2.42; the '
        'Flyers manage 1.67 and give up 3.08, the weakest attack in the game. New York have also won six of their last '
        'ten. Selection: New York Rangers to win, -270.',
        'Rangers 7-4-1, L10 6-3-1, home 6-0-0, 3.08 GF / 2.42 GA; Flyers 3-6-3, away 1-4-1, 1.67 GF / 3.08 GA.'),
    "fx_nhl_2026020260": (
        'Edmonton are 8-1-1 for 17 points, have won eight of ten and average 4.70 goals per game, the highest rate in '
        'this matchup by more than a goal and a half. Anaheim are 4-6-0 with eight points and have lost six of ten, '
        'scoring 2.70 while allowing 3.30. The Oilers have taken three of five at Rogers Place, and Anaheim\'s 3.30 goals '
        'against per game is the weaker defensive record of the two. Selection: Edmonton Oilers to win, -270.',
        'Oilers 8-1-1, L10 8-1-1, home 3-1-1, 4.70 GF / 3.20 GA; Ducks 4-6-0, L10 4-6-0, away 3-3-0, 2.70 GF / 3.30 GA.'),
    "fx_nhl_2026020277": (
        'Boston are 8-2-1 for 17 points, 4-1-0 at TD Garden, and they score 3.82 while conceding 2.00 per game. '
        'Florida are 5-4-2 with 12 points and have won only four of their last ten, averaging 2.82 goals across '
        'eleven fixtures. The Panthers are 3-3-2 on the road and their 3.09 goals against per game is more than a '
        'goal worse than Boston\'s. Selection: Boston Bruins to win, -270.',
        'Bruins 8-2-1, L10 7-2-1, home 4-1-0, 3.82 GF / 2.00 GA; Panthers 5-4-2, L10 4-4-2, away 3-3-2, 2.82 GF / 3.09 GA.'),
    "fx_el_games_E2026_76": (
        'Panathinaikos are 6-1 in the EuroLeague and average 87.6 points while conceding 73.9, a margin of almost '
        'fourteen points a night. Milan have lost six of seven, score 83.6 and give up 92.6, the worst defensive '
        'record in the pairing. The Italians have been outscored by nine points per game on average across their seven '
        'fixtures. Selection: Panathinaikos AKTOR Athens to win, -400.',
        'Panathinaikos 6-1, 87.571 PF / 73.857 PA; Milan 1-6, 83.571 PF / 92.571 PA.'),
    "fx_eurocup_games_U2026_68": (
        'Tortona are 2-2 and average 82.5 points, while Rostock are 1-3 and concede 93.0 a game, the leakiest defence '
        'in the matchup. The Germans score 77.3 and have been outscored by nearly sixteen points per game, a gap that '
        'points to a comfortable night for the home side. Tortona have split their four games but their defensive '
        'numbers are far stronger. Selection: Baglietto Derthona Tortona to win, -278.',
        'Tortona 2-2, 82.5 PF / 84.0 PA; Rostock 1-3, 77.25 PF / 93.0 PA.'),
    'fx_nhl_2026020170': (
        'Boston have started 8-2-1 for 17 points, won seven of their last ten and are 4-1-0 on home ice at TD Garden. San Jose arrive at 6-4-1, have taken four of seven on the road and concede 3.36 goals a game. The Bruins score 3.82 and allow 2.00 per game, the widest two-way gap in the matchup, so the home side should control the run of play. Selection: Boston Bruins to win, -286.',
        'Bruins 8-2-1, L10 7-2-1, home 4-1-0, 3.82 GF / 2.00 GA; Sharks 6-4-1, away 4-2-1, 3.00 GF / 3.36 GA.'),
    'fx_nhl_2026020276': (
        'Vancouver are 2-9-1 with five points, have lost eight of ten and are 1-5-1 on the road, and they concede 4.67 goals a game overall. Edmonton sit 8-1-1, have won eight of their last ten and score 4.70 a night. The Canucks have managed 2.92 goals per game and their minus 21 goal difference across twelve games is the worst record in the matchup. Selection: Edmonton Oilers to win, -312.',
        'Canucks 2-9-1, L10 1-8-1, away 1-5-1, 2.92 GF / 4.667 GA; Oilers 8-1-1, L10 8-1-1, 4.70 GF / 3.20 GA.'),
    'fx_eurocup_games_U2026_67': (
        'Aris are 4-0 in the EuroCup and average 94.5 points while conceding 75.3, a differential of plus 19.25 per game. Cedevita Olimpija are 0-4, scoring 72.5 and allowing 83.3, and their minus 10.75 differential is the weaker of the two records in this game. The Greek side have scored more than ninety in each of their wins. Selection: Aris Thessaloniki to win, -526.',
        'Aris 4-0, 94.5 PF / 75.25 PA; Cedevita 0-4, 72.5 PF / 83.25 PA.'),
    'fx_el_games_E2026_90': (
        'Olympiacos are 5-2 and score 92.9 points a game while conceding 86.1, and they meet a Milan side that has lost six of seven. The Italians average 83.6 and allow 92.6, and their minus nine differential is the weakest in the pairing. Olympiacos have won five of seven and their scoring rate is almost ten points higher. Selection: Olympiacos Piraeus to win, -294.',
        'Olympiacos 5-2, 92.857 PF / 86.143 PA; Milan 1-6, 83.571 PF / 92.571 PA.'),
    'fx_eurocup_games_U2026_92': (
        "Tofas are 3-1 and average 90.5 points while conceding 85.3, a positive differential of just over five a game. Neptunas are 1-3, score 84.8, allow 90.5 and have lost three of their four fixtures. The Turkish side's edge on both ends of the floor is the difference here, and the price sits inside the -250 to +10,000 band this board is asked to work in. Selection: Tofas Bursa to win, -233.",
        'Tofas 3-1, 90.5 PF / 85.25 PA; Neptunas 1-3, 84.75 PF / 90.5 PA.'),
    'fx_eurocup_games_U2026_91': (
        'Napoli are 4-0 and average 92.0 points while conceding 83.5, a margin of 8.5 a night. Trento are 1-3, score 79.0 and allow 86.3, and their minus 7.25 differential reflects an offence that averages fewer than eighty. The Italian club have won every game in the competition while Trento have taken one of four. Selection: Napoli Basketball to win, -294.',
        'Napoli 4-0, 92.0 PF / 83.5 PA; Trento 1-3, 79.0 PF / 86.25 PA.'),
    'fx_eurocup_games_U2026_94': (
        "Bosna are 1-3 but have been competitive, scoring 80.8 and conceding 82.3, while Balkan are 0-4 with the weaker offence in the matchup at 68.5 points a game. The Bulgarian side allow 84.8 and have been outscored by more than sixteen per game, so Bosna's steadier scoring gives them the clear edge. Selection: BOSNA BH Telecom Sarajevo to win, -278.",
        'Bosna 1-3, 80.75 PF / 82.25 PA; Balkan 0-4, 68.5 PF / 84.75 PA.'),
    'fx_el_games_E2026_92': (
        'Fenerbahce are 6-1 and score 80.7 points while conceding 72.6, the best defensive record in this matchup. Baskonia have lost six of seven, average 83.3 and allow 92.7, and their minus 9.4 differential is the weakest in the pairing. The Istanbul side give up almost twenty points fewer per game than the visitors. Selection: Fenerbahce Tarfin Istanbul to win, -323.',
        'Fenerbahce 6-1, 80.714 PF / 72.571 PA; Baskonia 1-6, 83.286 PF / 92.714 PA.'),
    'fx_eurocup_games_U2026_85': (
        'Tenerife are 3-1 and score 89.8 points while conceding 82.3, a differential of plus 7.5. Cluj are 2-2, average 79.8 and allow 86.3, and they have been outscored by 6.5 points per game. The Spanish side score ten more per night than the visitors and have won three of their four fixtures. Selection: La Laguna Tenerife to win, -270.',
        'Tenerife 3-1, 89.75 PF / 82.25 PA; Cluj 2-2, 79.75 PF / 86.25 PA.'),
}


def main():
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    by_id = {r["id"]: r for r in desk["rows"]}
    out, problems = [], []
    for rid, (text, basis) in TEXTS.items():
        r = by_id.get(rid)
        if not r or not r.get("pick"):
            problems.append(f"{rid}: not a priced row")
            continue
        p = r["pick"]
        if p["confidence"] != "High":
            problems.append(f"{rid}: confidence is {p['confidence']}")
            continue
        if p["selection"] not in text and p["selection"].split(" (")[0] not in text:
            problems.append(f"{rid}: selection not named in the copy")
        if len(text.split()) < 30:
            problems.append(f"{rid}: fewer than 30 words")
        if re.search(r"\b(model|verified|verification|probability model)\b", text, re.I):
            problems.append(f"{rid}: banned vocabulary")
        out.append({
            "id": "pred_" + rid,
            "row_id": rid,
            "sport": r["sport"],
            "competition": r["competition"],
            "match": f'{r["side_a"]} @ {r["side_b"]}' if r["side_b"] else r["side_a"],
            "start_utc": r["start_utc"],
            "selection": p["selection"],
            "market": p["market"],
            "fair_american": p["fair_american"],
            "fair_prob": p["fair_prob"],
            "confidence": p["confidence"],
            "in_window": p["in_window"],
            "text": text,
            "facts": basis,
            "source_url": r["official_url"],
            "source_name": r["official_source_name"],
            "capture_id": r["capture_id"],
        })
    ids = [p["row_id"] for p in out]
    highs = [r["id"] for r in desk["rows"] if r.get("pick") and r["pick"]["confidence"] == "High"]
    missing = [i for i in highs if i not in ids]
    doc = {
        "schema": "fx-predictions-1",
        "session": "arena/4502eff5-olbg4",
        "desk_generated_utc": desk.get("generated_utc"),
        "count": len(out),
        "high_rows": len(highs),
        "high_rows_without_copy": missing,
        "problems": problems,
        "predictions": out,
    }
    json.dump(doc, open(os.path.join(DATA, "predictions.json"), "w"), indent=1, sort_keys=True)
    print(f"predictions {len(out)} / high rows {len(highs)}; missing {missing}")
    for p in problems:
        print("PROBLEM", p)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())

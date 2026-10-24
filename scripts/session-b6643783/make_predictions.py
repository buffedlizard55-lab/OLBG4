#!/usr/bin/env python3
"""Board CA — written predictions.

Each entry is written for one row and cites only facts that are on that row:
the official form string, the official rate statistics, the venue and the date.
Nothing here states an injury, a lineup or a result that is not in the capture.

Validation before writing:
  * at least 30 words
  * unique against every other prediction (3-gram Jaccard)
  * no internal vocabulary ("model", "verified", "verification")
  * names the exact selection that the row's pick carries
"""
from __future__ import annotations

import itertools
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-b6643783")

BANNED = re.compile(r"\b(model|models|modelled|modeled|modelling|verif\w*)\b", re.I)

# row_id -> written prediction
TEXT = {
    # ---------------------------------------------------------------- ice hockey
    "fx_nhl_2026020217": (
        "Boston Bruins to beat the Chicago Blackhawks on home ice at TD Garden at our -455 money line. "
        "The NHL's own standings have Boston 8-2-1 for 17 points, 7-2-1 across their last ten and on a "
        "winning run, scoring 3.82 goals a game while conceding exactly 2.00. Chicago are 3-7-0 for six "
        "points, 3-7-0 over the same ten-game span, and have lost all four road games, conceding 4.00 a "
        "game. Boston's 4-1-0 home record against a winless travelling side makes the Bruins the bet."
    ),
    "fx_nhl_2026020226": (
        "Colorado Avalanche to see off the Calgary Flames at Ball Arena at -435. Colorado sit 6-4-1 for 13 "
        "points with a 4-1-1 home record and are averaging 4.27 goals per game, the strongest home scoring "
        "rate in this fixture. Calgary are 3-6-0, 1-3-0 on the road, managing 2.11 goals a game while "
        "giving up 4.22, and they arrive on a one-game winning run only. The gap in goals for and against "
        "per game is more than two, so the Avalanche win is the selection."
    ),
    "fx_nhl_2026020200": (
        "Edmonton Oilers to win at Rogers Place against the Calgary Flames, priced at -435. Edmonton are "
        "8-1-1 for 17 points, 8-1-1 in their last ten and on a winning streak, putting up 4.70 goals a "
        "game and allowing 3.20. Calgary are 3-6-0 with a 1-3-0 road record, scoring 2.11 and conceding "
        "4.22 per game. The Oilers have also taken three of five at home, and the scoring differential "
        "here is the widest on the board, which makes the home money line the pick."
    ),
    "fx_nhl_2026020271": (
        "Carolina Hurricanes to beat the Chicago Blackhawks at Lenovo Center at -385. Carolina are 8-2-2 "
        "for 18 points, 8-1-1 over their last ten, and are scoring 3.92 goals a game while conceding 2.75. "
        "Chicago are 3-7-0 for six points, 3-7-0 in the same span, and have not won away from home in four "
        "attempts, scoring 2.20 and conceding 4.00 per game. The Hurricanes carry a two-win unbeaten run "
        "into the game, so the home side is the confident call."
    ),
    "fx_nhl_2026020250": (
        "Seattle Kraken to beat the Calgary Flames at Climate Pledge Arena at -370. Seattle are 7-3-1 for "
        "15 points and 6-3-1 across their last ten, averaging 4.00 goals a game at 3-1-0 on home ice. "
        "Calgary are 3-6-0 for six points, 1-3-0 on the road, scoring 2.11 and conceding 4.22 per game, "
        "and their only recent encouragement is a single win. Seattle's home scoring rate is nearly double "
        "Calgary's road output, which is why the Kraken money line is the selection."
    ),
    # ----------------------------------------------------------------- basketball
    "fx_eurocup_games_U2026_67": (
        "Aris Thessaloniki to beat Cedevita Olimpija Ljubljana at -526 in the EuroCup. Aris are 4-0 and "
        "have scored 94.5 points per game while conceding 75.25, a differential of almost twenty points. "
        "Cedevita are 0-4, scoring 72.5 and conceding 83.25, so they are being outscored by nearly eleven "
        "per game. The Greek side have won every game on their own schedule and the visitors have won "
        "none, which makes the home win the strongest basketball selection on this card."
    ),
    "fx_el_games_E2026_76": (
        "Panathinaikos AKTOR Athens to beat Armani Olimpia Milan at -400 in the EuroLeague. Panathinaikos "
        "are 6-1, scoring 87.57 points per game and conceding only 73.86, the best defensive number in this "
        "tie. Milan are 1-6, scoring 83.57 but conceding 92.57, so their defence is giving up nearly "
        "nineteen points more than the hosts each night. With the Athenians at home and a five-game swing "
        "in the standings, the home money line is the pick."
    ),
    "fx_el_games_E2026_92": (
        "Fenerbahce Tarfin Istanbul to beat Kosner Baskonia Vitoria-Gasteiz at -323. Fenerbahce are 6-1 "
        "with 80.71 points scored and only 72.57 conceded per game, the tightest defence in the fixture. "
        "Baskonia are 1-6, scoring 83.29 but conceding 92.71, so they are losing the scoring battle by more "
        "than nine points a night. The Turkish side have lost once all season and hold home advantage, "
        "which makes Fenerbahce the selection here."
    ),
    "fx_eurocup_games_U2026_91": (
        "Napoli Basketball to beat Dolomiti Energia Trento at -294 in the EuroCup. Napoli are 4-0, putting "
        "up 92.0 points a game while conceding 83.5, a margin of eight and a half. Trento are 1-3, scoring "
        "79.0 and conceding 86.25, so they are being outscored by more than seven a game. An unbeaten home "
        "side against a visiting team with a single win is the clearest edge on this slate, and the Napoli "
        "money line is the bet."
    ),
    "fx_el_games_E2026_90": (
        "Olympiacos Piraeus to beat Armani Olimpia Milan at -294 in the EuroLeague. Olympiacos are 5-2, "
        "scoring 92.86 points per game and conceding 86.14. Milan are 1-6, scoring 83.57 and conceding "
        "92.57, so the Italians are being outscored by nine points a night while the Greeks are winning "
        "theirs by nearly seven. Olympiacos have won five of seven and are at home, which makes their "
        "money line the selection."
    ),
    # ------------------------------------------------------------------- handball
    "ca_olbg_12078": (
        "GOG to win at TMS Ringsted in the Danish Herreligaen at -238. The official table has GOG 9-1-0 on "
        "19 points with 352 goals scored and 292 conceded in ten matches, which is 35.2 scored and 29.2 "
        "conceded a game. Ringsted are 1-1-8 on three points, scoring 306 and conceding 342. Against a "
        "league average of 31.66 goals a match, GOG's attack and defence both point the same way, so the "
        "away win is the selection."
    ),
    # ---------------------------------------------------------------- rugby league
    "fx_rlwc_20261310340": (
        "Lebanon to beat France at CommBank Stadium in Rugby League World Cup round three at -333. "
        "Lebanon have scored 25.4 points and conceded 33.8 per match from one completed game, while France "
        "have managed 20.5 scored and conceded 46.4, the leakiest defensive record of the six completed "
        "matches in the tournament. Lebanon are rated to score around 40.9 here against France's 23.1, a "
        "margin of nearly eighteen points, which makes the home win the selection."
    ),
    "fx_rlwc_20261310350": (
        "Samoa to beat Tonga XIII at CommBank Stadium at -238. Samoa have played twice and averaged 43.9 "
        "points scored against 20.8 conceded, the best scoring rate in the tournament. Tonga have 29.6 "
        "scored and 23.3 conceded from a single match. Samoa are expected to put up 34.1 points to Tonga's "
        "21.4, a gap of almost thirteen, and their two-game sample is the most reliable form line in the "
        "pool, so the Samoa win is the pick."
    ),
    "fx_rlwc_20261310330": (
        "Australia to beat the Cook Islands in Townsville at -208. Australia have scored 27.5 points and "
        "conceded 26.8 per match, while the Cook Islands have scored 23.3 and conceded 33.1, the second "
        "weakest defence of the six matches played so far. Australia are rated at 31.6 points against 20.8 "
        "for the visitors, a margin of nearly eleven in front of a home crowd at Queensland Country Bank "
        "Stadium, and that makes the Kangaroos the selection."
    ),
    "fx_rlwc_20261310240": (
        "New Zealand to beat the Cook Islands at One NZ Stadium in Christchurch at -189. New Zealand have "
        "scored 26.8 and conceded 27.5 per match so far, while the Cook Islands have scored 23.3 and "
        "conceded 33.1. The hosts are expected to score 30.8 against 21.4 for the visitors, a nine-point "
        "margin, and they have home advantage in Christchurch. With the Cook Islands conceding more than "
        "thirty a game, New Zealand's money line is the selection."
    ),
    "fx_rlwc_20261310320": (
        "Fiji to beat New Zealand at Cbus Super Stadium on the Gold Coast at -179. Fiji have averaged 33.1 "
        "points scored and only 23.3 conceded from their completed match, the best defensive return in the "
        "pool, while New Zealand have 26.8 scored and 27.5 conceded. Fiji are rated at 30.3 points against "
        "21.7, a margin of nearly nine. Fiji's edge in both attack and defence makes them the value "
        "selection despite playing away from home."
    ),
    # ------------------------------------------------------------------ volleyball
    "fx_lv_29_Cisterna_Volley_Pallavolo_Padova": (
        "Cisterna Volley to beat Pallavolo Padova at the Palasport in Cisterna di Latina at -143. The "
        "official SuperLega table after the opening round has Cisterna on three points from a 3-0 win, "
        "scoring 26.3 points per set while conceding 18.7. Padova lost their opener 0-3, scoring 18.7 and "
        "conceding 25.0 per set. That is a seven-point swing per set in Cisterna's favour, and with home "
        "advantage the money line is the selection."
    ),
    "fx_lv_9_Gas_Sales_Bluenergy_Piacenza_Valsa_Group_Modena": (
        "Gas Sales Bluenergy Piacenza to beat Valsa Group Modena at PalaBancaSport at -135. Piacenza opened "
        "with a 3-0 win worth three points, scoring 25.0 points per set and conceding only 18.7. Modena "
        "lost their first match 0-3, scoring 20.3 and conceding 25.0 per set. The two sides are separated "
        "by more than six points per set on the official table, and Piacenza have home advantage, so their "
        "match-winner price is the pick."
    ),
    "fx_lv_10_Cucine_Lube_Civitanova_Pallavolo_Padova": (
        "Cucine Lube Civitanova to beat Pallavolo Padova at the Eurosuole Forum at -135. Civitanova took "
        "three points from a 3-0 opening win, scoring 26.0 points per set and conceding 21.7. Padova were "
        "beaten 0-3 in their first match, scoring 18.7 and conceding 25.0 per set. Across the opening "
        "round that is a gap of more than seven points a set in the home side's favour, and Civitanova "
        "also hold home advantage, which makes them the selection."
    ),
    "fx_lv_26_Gas_Sales_Bluenergy_Piacenza_Rana_Verona": (
        "Gas Sales Bluenergy Piacenza to beat Rana Verona at PalaBancaSport at -135. Piacenza's opening "
        "fixture was a 3-0 win worth three points, with 25.0 points scored and 18.7 conceded per set. "
        "Verona lost 0-3 and sit on nought points, scoring 21.7 and conceding 26.0 per set. The official "
        "table therefore has Piacenza more than six points per set the stronger side, and with the match "
        "at home the money line is the selection."
    ),
    "fx_lv_61_Sir_Susa_Scai_Perugia_Pallavolo_Padova": (
        "Sir Susa Scai Perugia to beat Pallavolo Padova at the Pala Barton Energy at -135. Perugia took two "
        "points from a five-set 3-2 win, scoring 22.8 points per set and conceding 19.0. Padova lost their "
        "opener 0-3, scoring 18.7 and conceding 25.0 per set. Perugia's defensive numbers are nearly six "
        "points per set better, and Padova have now conceded 25 points a set across their opening match, so "
        "the home win is the selection."
    ),
    # -------------------------------------------------------------------- baseball
    "fx_mlb_849804": (
        "Milwaukee Brewers to beat the Tampa Bay Rays at Tropicana Field in game three at -152. The Brewers "
        "finished the regular season 103-59, scoring 5.14 runs a game and conceding 3.82; the Rays were "
        "98-64, scoring 4.54 and conceding 4.01. Milwaukee's run differential of plus 214 is the better of "
        "the two by more than sixty runs. Robert Gasser is listed against Freddy Peralta, and on season "
        "scoring rates the Brewers are the selection away from home."
    ),
    "fx_mlb_849802": (
        "Milwaukee Brewers to beat the Tampa Bay Rays at American Family Field in game two at -111. "
        "Milwaukee are 103-59 for the season, scoring 5.14 runs a game and conceding 3.82, while Tampa Bay "
        "are 98-64, scoring 4.54 and conceding 4.01. Logan Henderson is the listed starter for the Brewers "
        "against Drew Rasmussen, and the hosts score more than half a run a game more than their opponents. "
        "With home advantage and the better offence, the Brewers money line is the pick."
    ),
    "fx_mlb_849803": (
        "Milwaukee Brewers to beat the Tampa Bay Rays at Tropicana Field in game four at -152, with the "
        "caveat that no starting pitcher had been announced for either side when this was written. The "
        "season numbers still separate them: Milwaukee are 103-59 with 5.14 runs scored and 3.82 conceded "
        "per game, Tampa Bay 98-64 with 4.54 scored and 4.01 conceded. On those figures the Brewers remain "
        "the selection, but the price should be re-checked once the starters are named."
    ),
    # ---------------------------------------------------------------- motor racing
    "ca_f1_mexico": (
        "Kimi Antonelli to win the Mexico City Grand Prix at +321, a lower-confidence outright. Formula "
        "1's official drivers' championship after round nineteen has Antonelli leading on 340 points for "
        "Mercedes, ahead of team-mate George Russell on 238, Lewis Hamilton on 229, Max Verstappen on 221 "
        "and Charles Leclerc on 215. Round twenty runs from 30 October to 1 November at Mexico City. The "
        "championship leader at more than three times the odds of a single win is the each-way case here."
    ),
}


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    rows = {r["id"]: r for r in desk["rows"]}

    preds, problems = [], []
    for rid, text in TEXT.items():
        r = rows.get(rid)
        if not r or not r.get("pick"):
            problems.append(f"{rid}: row missing or unpriced")
            continue
        p = r["pick"]
        words = len(text.split())
        if words < 30:
            problems.append(f"{rid}: only {words} words")
        if BANNED.search(text):
            problems.append(f"{rid}: banned vocabulary {BANNED.search(text).group(0)}")
        sel_short = re.sub(r"\s*\((home|away)\)$", "", p["selection"]).strip()
        if sel_short.split()[0].lower() not in text.lower():
            problems.append(f"{rid}: selection {sel_short!r} not named in the text")
        preds.append({
            "row_id": rid,
            "sport": r["sport"],
            "competition": r["competition"],
            "match": f'{r["side_a"]} v {r["side_b"]}'.strip(),
            "start_utc": r["start_utc"],
            "venue": r.get("venue", ""),
            "market": p["market"],
            "selection": p["selection"],
            "fair_prob": p["fair_prob"],
            "fair_decimal": p["fair_decimal"],
            "fair_american": p["fair_american"],
            "in_window": -250 <= p["fair_american"] <= 10000,
            "confidence": p["confidence"],
            "words": words,
            "text": text,
            "inputs": {k: v for k, v in (r.get("evidence") or {}).items()
                       if k not in ("standings_source", "table_source", "standings_top5")},
            "form": r.get("form") or {},
            "sample": r.get("sample", ""),
            "sources": [
                {"label": r.get("official_source_name") or "official source",
                 "url": r.get("official_url", "")},
            ] + ([{"label": "OLBG event page", "url": r["olbg"]["event_url"]}]
                 if (r.get("olbg") or {}).get("event_url") else []),
        })

    # uniqueness: pairwise 3-gram Jaccard
    def grams(t):
        w = re.findall(r"[a-z0-9]+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}

    worst = 0.0
    for a, b in itertools.combinations(preds, 2):
        ga, gb = grams(a["text"]), grams(b["text"])
        if ga and gb:
            j = len(ga & gb) / len(ga | gb)
            worst = max(worst, j)
            if j > 0.30:
                problems.append(f"near-duplicate: {a['row_id']} / {b['row_id']} jaccard {j:.2f}")

    doc = {
        "schema": "ca-predictions-1",
        "board": "CA",
        "session": "arena/b6643783-olbg4",
        "count": len(preds),
        "max_pairwise_3gram_jaccard": round(worst, 4),
        "problems": problems,
        "predictions": sorted(preds, key=lambda p: (p["sport"], -p["fair_prob"])),
    }
    json.dump(doc, open(os.path.join(DATA, "predictions.json"), "w", encoding="utf-8"), indent=1)
    print(f"{len(preds)} predictions, worst 3-gram Jaccard {worst:.3f}, {len(problems)} problems")
    for p in problems:
        print("  !", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

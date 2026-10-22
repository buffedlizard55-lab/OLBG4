#!/usr/bin/env python3
"""Board AF — hand-written predictions for the five strongest selections per sport.

Each entry is keyed by the desk row key (`sport|side_a|side_b|YYYY-MM-DD`) and
contains only facts that are printed on the official page recorded on that row:
records, points, goals/runs for and against, streaks, rankings, seeds or Elo.
The selection and the prices in the final sentence are the row's own originated
line. Nothing here is copied from OLBG, a bookmaker or another tipster.
"""

PREDICTIONS: dict[str, dict] = {
    # ------------------------------------------------------------------ Ice Hockey
    "ice-hockey|HPK|K-Espoo|2026-10-30": {
        "sport": "Ice Hockey",
        "text": (
            "K-Espoo travel to Hämeenlinna with the better goal record of the two clubs: 49 scored "
            "and 41 conceded across 16 Liiga games, against HPK's 35 for and 44 against. HPK have "
            "taken 21 points from 16 starts, K-Espoo 23 from the same number, so the gap is small "
            "enough that a 1.5-goal cushion matters. Selection: K-Espoo +1.5 at -218."
        ),
    },
    "ice-hockey|Pelicans|Tappara|2026-10-24": {
        "sport": "Ice Hockey",
        "text": (
            "Pelicans have scored 29 and conceded 29 in 13 Liiga outings, while Tappara arrive in "
            "Lahti with 40 goals for and 32 against from 15. Both clubs are mid-table (19 and 23 "
            "points), and our matchup total of 4.57 goals makes the low 3.5 line the standout. "
            "Selection: Over 3.5 goals at -218."
        ),
    },
    "ice-hockey|Tampa Bay Lightning|Colorado Avalanche|2026-10-24": {
        "sport": "Ice Hockey",
        "text": (
            "Tampa Bay are 7-2-0 with 31 goals for and 23 against, and they ride a three-game win "
            "streak into Ball Arena. Colorado are 5-4-1, have scored 41 and conceded 31 in ten, and "
            "have dropped their last two. Combined, the two goal records average 6.3 per game. "
            "Selection: Over 5.5 goals at -217."
        ),
    },
    "ice-hockey|New York Islanders|Minnesota Wild|2026-10-30": {
        "sport": "Ice Hockey",
        "text": (
            "The Islanders have conceded only 20 goals in nine games while scoring 27, and their "
            "last ten reads 5-3-1. Minnesota are 6-2-2 with 31 scored and 25 conceded in ten. "
            "Two defences allowing under three goals a game point to a total below our 5.6 model "
            "line. Selection: Under 6.5 goals at -216."
        ),
    },
    "ice-hockey|SaiPa|JYP|2026-10-30": {
        "sport": "Ice Hockey",
        "text": (
            "SaiPa sit fifth in Liiga on 28 points from 14 games, with 41 scored and 23 conceded. "
            "JYP are seventh on 27 points from 13, having scored 40 and conceded 34. One point "
            "separates them in the table, which is why a 1.5-goal start for the visitors is the "
            "line we want. Selection: JYP +1.5 at -216."
        ),
    },
    # ------------------------------------------------------------------ Basketball
    "basketball|Panathinaikos AKTOR Athens|Armani Olimpia Milan|2026-10-27": {
        "sport": "Basketball",
        "text": (
            "Panathinaikos are 6-1 and outscoring opponents by 13.7 points per game (613 for, 517 "
            "against). Armani Milan are 1-6 with a minus-9.0 differential (585 for, 648 against). "
            "The Athens spread is 9.5, and our model still gives Milan a 71.4% chance of keeping "
            "the margin inside it. Selection: Armani Olimpia Milan +9.5 at -219."
        ),
    },
    "basketball|Valencia Basket|Fenerbahce Tarfin Istanbul|2026-10-27": {
        "sport": "Basketball",
        "text": (
            "Valencia's six EuroLeague games have averaged 189.8 points (590 scored, 549 allowed), "
            "while Fenerbahce's six average 158.0 (501 scored, 447 allowed). Blend the two profiles "
            "and the expected total is 173.9, ten points under the posted 183.5. Selection: Under "
            "183.5 points at -218."
        ),
    },
    "basketball|LDLC ASVEL Villeurbanne|Kosner Baskonia Vitoria-Gasteiz|2026-10-30": {
        "sport": "Basketball",
        "text": (
            "ASVEL are 2-4 with a minus-7.5 average margin, and Baskonia are 1-6 at minus-9.4. "
            "Neither side has been able to pull clear of opponents this season, and at LDLC Arena "
            "our model gives Baskonia a 71.3% chance to stay within 7.5 points. Selection: Kosner "
            "Baskonia Vitoria-Gasteiz +7.5 at -218."
        ),
    },
    "basketball|Olympiacos Piraeus|Armani Olimpia Milan|2026-10-30": {
        "sport": "Basketball",
        "text": (
            "Olympiacos are 5-1 and their six games have produced 188.0 points on average (589 "
            "scored, 539 allowed). Milan's seven games average 176.1 (585 scored, 648 allowed), and "
            "the two profiles combine to 182.1. That sits almost ten points above the 172.5 line. "
            "Selection: Over 172.5 points at -218."
        ),
    },
    "basketball|FC Bayern Munich|FC Barcelona|2026-10-27": {
        "sport": "Basketball",
        "text": (
            "Bayern Munich's seven EuroLeague games have averaged 181.6 points (612 for, 659 "
            "against); Barcelona's seven average 178.6 (631 for, 619 against). SAP Garden has seen "
            "plenty of scoring, and our combined total of 180.1 clears the 170.5 line comfortably. "
            "Selection: Over 170.5 points at -218."
        ),
    },
    # ------------------------------------------------------------------ Baseball
    "baseball|Tampa Bay Rays|Milwaukee Brewers|2026-10-24": {
        "sport": "Baseball",
        "text": (
            "Milwaukee won 103 games and scored 832 runs while conceding 618; Tampa Bay went 98-64 "
            "with 736 scored and 650 conceded. Those season rates put the combined average at 8.75 "
            "runs, and the official Game 1 probables are Nick Martinez and Jacob Misiorowski. "
            "Selection: Over 6.5 runs at -215."
        ),
    },
    "baseball|Tampa Bay Rays|Milwaukee Brewers|2026-10-25": {
        "sport": "Baseball",
        "text": (
            "Game 2 stays at American Family Field, where Milwaukee's 103-59 record and five-game "
            "win streak frame the run environment. Tampa Bay have lost their most recent game but "
            "still scored 736 runs across the regular season. Drew Rasmussen is listed for the Rays. "
            "Selection: Over 6.5 runs at -215."
        ),
    },
    "baseball|Milwaukee Brewers|Tampa Bay Rays|2026-10-27": {
        "sport": "Baseball",
        "text": (
            "The series moves to Tropicana Field for Game 3. Milwaukee's 832 runs are the higher of "
            "the two season totals, and Tampa Bay's 736-650 split gives the matchup an 8.56-run "
            "baseline before any venue adjustment. Our line stays at 6.5, which the model clears "
            "70.8% of the time. Selection: Over 6.5 runs at -215."
        ),
    },
    "baseball|Milwaukee Brewers|Tampa Bay Rays|2026-10-28": {
        "sport": "Baseball",
        "text": (
            "Tampa Bay scored 736 and allowed 650 over 162 games; Milwaukee scored 832 and allowed "
            "618. Combining the two profiles produces 8.75 runs per game. Game 4 is a separate "
            "market, but the same season inputs keep our total at 6.5. Selection: Over 6.5 runs at "
            "-215."
        ),
    },
    "baseball|Milwaukee Brewers|Tampa Bay Rays|2026-10-29": {
        "sport": "Baseball",
        "text": (
            "By Game 5 the pitching plans are less certain, yet the season-long numbers still drive "
            "the line: 8.56 runs per Tampa Bay game and 8.95 per Milwaukee game. Milwaukee's run "
            "differential of plus-214 is the strongest in the series. Selection: Over 6.5 runs at "
            "-215."
        ),
    },
    # ------------------------------------------------------------------ Tennis
    "tennis|Tallon Griekspoor|Jiri Lehecka|2026-10-23": {
        "sport": "Tennis",
        "text": (
            "Jiri Lehecka is ranked 20th on 2,235 ranking points; Tallon Griekspoor is 60th on 885. "
            "The Czech has more than two and a half times the points of his opponent, and the "
            "Brussels quarter-final is priced as a straight win for him. Selection: Jiri Lehecka "
            "-0.5 games at -212."
        ),
    },
    "tennis|Corentin Moutet|Tommy Paul|2026-10-23": {
        "sport": "Tennis",
        "text": (
            "Tommy Paul is 15th on 2,575 points and Corentin Moutet is 94th on 640, so the match "
            "favourite is clear. The handicap is the interesting market: Moutet +6.5 games asks only "
            "that he stays within six games of the American. Our model gives that 70.7%. Selection: "
            "Corentin Moutet +6.5 games at -212."
        ),
    },
    "tennis|Arthur Fils|Alex Michelsen|2026-10-23": {
        "sport": "Tennis",
        "text": (
            "Arthur Fils is 10th on 3,325 points; Alex Michelsen is 37th on 1,370. Fils has more "
            "than double the ranking points, and our model makes him a 70.3% chance to win the "
            "Brussels quarter-final outright. Selection: Arthur Fils -0.5 games at -208."
        ),
    },
    "tennis|Mary Stoiana|Katerina Siniakova|2026-10-23": {
        "sport": "Tennis",
        "text": (
            "Katerina Siniakova is 86th on 865 points and Mary Stoiana is 114th on 666, a narrow gap "
            "in ranking terms. Siniakova +1.5 games protects against a tight three-set loss, and our "
            "model gives the Czech a 70.2% chance of covering it in Osaka. Selection: Katerina "
            "Siniakova +1.5 games at -207."
        ),
    },
    "tennis|Leylah Fernandez|Ekaterina Alexandrova|2026-10-23": {
        "sport": "Tennis",
        "text": (
            "Leylah Fernandez is 30th on 1,709 points, Ekaterina Alexandrova 33rd on 1,591 — barely "
            "a round apart in the WTA list. The 2.5-game cushion is therefore attractive, and our "
            "model prices it at 70.1% for the Ningbo quarter-final. Selection: Ekaterina "
            "Alexandrova +2.5 games at -207."
        ),
    },
    # ------------------------------------------------------------------ Rugby Union
    "rugby-union|RC Vannes|ASM Clermont|2026-10-24": {
        "sport": "Rugby Union",
        "text": (
            "RC Vannes have lost all six Top 14 matches and have one point, with 117 scored and 176 "
            "conceded. Clermont are 2-4 on 11 points (140 scored, 169 conceded). The model still "
            "rates Clermont the stronger side and gives them a 4.5-point start at Stade de la "
            "Rabiothèque. Selection: ASM Clermont +4.5 at -215."
        ),
    },
    "rugby-union|RC Toulon|Section Paloise|2026-10-24": {
        "sport": "Rugby Union",
        "text": (
            "Section Paloise are second on 22 points from six games, with 239 scored and 181 "
            "conceded, while Toulon are 2-4 on 12 points and level on points difference (130-130). "
            "Pau's form line reads V-D-V-V-V. The 4.5-point cushion for the visitors is the value "
            "line. Selection: Section Paloise +4.5 at -215."
        ),
    },
    "rugby-union|RC Narbonnais|CA Brive|2026-10-23": {
        "sport": "Rugby Union",
        "text": (
            "Narbonne have conceded 296 points in seven Pro D2 games while scoring 186; Brive have "
            "scored 206 and conceded 164. Their combined average is 60.7 points per game, well "
            "under the 68.5 line we have set for Friday night. Selection: Under 68.5 total points "
            "at -215."
        ),
    },
    "rugby-union|Racing 92|Montpellier Hérault Rugby|2026-10-24": {
        "sport": "Rugby Union",
        "text": (
            "Racing 92 are 2-4 with 143 scored and 196 conceded; Montpellier are 3-3 with 163 "
            "scored and 122 conceded. Montpellier's defence is 74 points better over the same six "
            "matches, and the model gives them a 6.5-point start in Paris. Selection: Montpellier "
            "Hérault Rugby +6.5 at -214."
        ),
    },
    "rugby-union|Castres Olympique|Stade Français Paris|2026-10-24": {
        "sport": "Rugby Union",
        "text": (
            "Castres have 9 points from six Top 14 games (126 scored, 153 conceded) and Stade "
            "Français have 14 (147 scored, 158 conceded). The table gap is five points, but the "
            "scoring difference is only 27, which makes an 8.5-point handicap for the home side "
            "generous. Selection: Castres Olympique +8.5 at -213."
        ),
    },
    # ------------------------------------------------------------------ Handball
    "handball|Skive fH|Aalborg Håndbold|2026-10-24": {
        "sport": "Handball",
        "text": (
            "Skive have one win in ten and sit 14th on two points with 328 goals for and 366 "
            "against. Aalborg are third on 15 points, 7-1-2, with 323 scored and 306 conceded. The "
            "model makes Aalborg a 71.4% winner in Saturday's Herreligaen fixture. Selection: "
            "Aalborg Håndbold at -214."
        ),
    },
    "handball|TTH Holstebro|TMS Ringsted Herrer|2026-11-01": {
        "sport": "Handball",
        "text": (
            "TTH Holstebro's ten games have averaged 62.6 goals (306 for, 320 against); TMS "
            "Ringsted's ten average 64.8 (306 for, 342 against). Blending the two gives 63.7, "
            "comfortably below the 68.5 line for this Herreligaen meeting. Selection: Under 68.5 "
            "goals at -214."
        ),
    },
    "handball|SAH|Sønderjyske Herrehåndbold|2026-11-01": {
        "sport": "Handball",
        "text": (
            "SAH are eighth on 12 points with 334 scored and 327 conceded; Sønderjyske are fourth "
            "on 14 points with 345 scored and 333 conceded. Both defences have kept totals in the "
            "sixties, and our model sets the game at 63.5 goals. Selection: Under 68.5 goals at "
            "-207."
        ),
    },
    "handball|Skjern Håndbold|Skive fH|2026-10-30": {
        "sport": "Handball",
        "text": (
            "Skjern are seventh on 12 points with 329 scored and 309 conceded, while Skive are "
            "bottom on two points and have conceded 366 in ten. Skjern's 6-4 record against Skive's "
            "1-9 record makes the home win the model's 70.6% play. Selection: Skjern Håndbold at "
            "-207."
        ),
    },
    "handball|TMS Ringsted Herrer|GOG|2026-10-25": {
        "sport": "Handball",
        "text": (
            "GOG are unbeaten in ten (9-0-1) with 352 scored and 292 conceded; TMS Ringsted have "
            "one win and a 306-342 goal record. The 8.5-goal cushion is large, and the model gives "
            "TMS a 70.6% chance of staying within it on Sunday. Selection: TMS Ringsted Herrer +8.5 "
            "at -207."
        ),
    },
    # ------------------------------------------------------------------ Darts
    "darts|Wessel Nijman|Martin Schindler|2026-10-23": {
        "sport": "Darts",
        "text": (
            "Wessel Nijman is seeded second for the Machineseeker European Championship; Martin "
            "Schindler is seeded 31st. The 29-place gap is the largest on Friday's first-round card "
            "in Dortmund, and our seed model gives Nijman an 81.0% chance. Selection: Wessel Nijman "
            "at -345."
        ),
    },
    "darts|Krzysztof Ratajski|Dave Chisnall|2026-10-23": {
        "sport": "Darts",
        "text": (
            "Krzysztof Ratajski carries the third seed into the Westfalenhalle; Dave Chisnall is "
            "30th. Ratajski's seeding reflects his European Tour order of merit, and the model "
            "makes him a 79.4% favourite over the best-of-11 first round. Selection: Krzysztof "
            "Ratajski at -317."
        ),
    },
    "darts|Nathan Aspinall|Cristo Reyes|2026-10-23": {
        "sport": "Darts",
        "text": (
            "Nathan Aspinall is seeded sixth; Cristo Reyes is 27th. The 21-place seeding gap and "
            "Aspinall's stronger European Tour position make him a 74.1% favourite in our model. "
            "Selection: Nathan Aspinall at -243."
        ),
    },
    "darts|Jonny Clayton|Niko Springer|2026-10-23": {
        "sport": "Darts",
        "text": (
            "Jonny Clayton is seeded seventh and Niko Springer 26th. Clayton's seeding is 19 places "
            "better, and our model gives him a 72.1% chance of advancing from the first round in "
            "Dortmund. Selection: Jonny Clayton at -223."
        ),
    },
    "darts|Ryan Joyce|Jermaine Wattimena|2026-10-23": {
        "sport": "Darts",
        "text": (
            "Ryan Joyce (15th seed) and Jermaine Wattimena (18th) are the closest pair on Friday's "
            "card. With only three seeding places between them, the model expects a long first-round "
            "match and makes Over 7.5 legs an 84.1% selection. Selection: Over 7.5 legs at -413."
        ),
    },
    # ------------------------------------------------------------------ Esports
    "esports|Gen.G Esports|Invictus Gaming|2026-10-23": {
        "sport": "eSports",
        "text": (
            "Gen.G Esports carry Riot's second-ranked team GPR, with an Elo of 1,552; Invictus "
            "Gaming are 15th on 1,344. The 208-point Elo gap makes Gen.G a 76.8% favourite in our "
            "model for the Worlds Swiss match. Selection: Gen.G Esports at -277."
        ),
    },
    "esports|Hanwha Life Esports|TOP ESPORTS|2026-10-23": {
        "sport": "eSports",
        "text": (
            "Hanwha Life Esports top Riot's global team GPR at 1,578 Elo; TOP Esports are 13th on "
            "1,364. The 214-point gap is the largest on the Swiss card, and our model gives HLE a "
            "77.4% chance of winning the best-of-one. Selection: Hanwha Life Esports at -286."
        ),
    },
    "esports|BILIBILI GAMING|Movistar KOI|2026-10-23": {
        "sport": "eSports",
        "text": (
            "BILIBILI GAMING are ranked third by Riot's team GPR (1,551 Elo), while Movistar KOI "
            "are 17th (1,330). The 221-point gap translates to a 78.1% win probability for BLG in "
            "our model. Selection: BILIBILI GAMING at -296."
        ),
    },
    "esports|LOS|T1|2026-10-23": {
        "sport": "eSports",
        "text": (
            "T1 sit fifth on Riot's GPR at 1,491 Elo; LOS are 39th at 1,263 despite a 2-0 Swiss "
            "record from their opening matches. The model weights the Elo gap more heavily and "
            "gives T1 a 78.8% chance. Selection: T1 at -307."
        ),
    },
    "esports|G2 Esports|Dplus KIA|2026-10-23": {
        "sport": "eSports",
        "text": (
            "G2 Esports are fourth on Riot's GPR (1,528 Elo) and Dplus KIA seventh (1,414). The "
            "gap is narrower than in the other Swiss ties, and the model makes G2 a 65.8% "
            "favourite — the one selection here that lands inside the −250 to +10,000 window. "
            "Selection: G2 Esports at -170."
        ),
    },

    # ------------------------------------------------------------------ Cricket
    "cricket|Afghanistan Men|Zimbabwe Men|2026-10-23": {
        "sport": "Cricket",
        "text": (
            "Afghanistan carry 93 ICC ODI rating points into the tri-series final in Sharjah; "
            "Zimbabwe have 53. Afghanistan are ranked seventh in the annual-update table and "
            "Zimbabwe 12th. Our total model sets the game at 268.5 runs, which puts the 243.5 line "
            "in play. Selection: Over 243.5 runs at -213."
        ),
    },
    "cricket|New Zealand Men|India Men|2026-10-24": {
        "sport": "Cricket",
        "text": (
            "India top the ICC Men's T20I rankings on 275 points, while New Zealand are fourth on "
            "247. The 28-point gap, plus India's top-ranked status, makes a 10.5-run handicap the "
            "play at Hagley Oval. Selection: India Men -10.5 runs at -215."
        ),
    },
    "cricket|Pakistan Men|England Men|2026-10-25": {
        "sport": "Cricket",
        "text": (
            "Pakistan are fifth on 98 ODI rating points and England eighth on 89, a nine-point gap "
            "in the ICC table. Gaddafi Stadium has a reputation for good batting conditions, and "
            "our total of 268.5 sits comfortably above the 243.5 line. Selection: Over 243.5 runs "
            "at -213."
        ),
    },
    "cricket|Pakistan Men|Sri Lanka Men|2026-10-27": {
        "sport": "Cricket",
        "text": (
            "Pakistan (98) and Sri Lanka (96) are separated by just two rating points in the ICC "
            "ODI table. With the match in Lahore, our model expects a total near 268.5 and makes "
            "Over 243.5 a 71.1% selection. Selection: Over 243.5 runs at -213."
        ),
    },
    "cricket|Afghanistan Men|Zimbabwe Men|2026-10-27": {
        "sport": "Cricket",
        "text": (
            "Afghanistan are 10th on 220 T20I rating points; Zimbabwe are 11th on 202. The 18-point "
            "gap is modest, but the model still gives Afghanistan a 1.5-run handicap at 71.3% for "
            "the 27 October T20I. Selection: Afghanistan Men -1.5 runs at -215."
        ),
    },
    # ------------------------------------------------------------------ Rugby League
    "rugby-league|Tonga XIII|Lebanon|2026-10-23": {
        "sport": "Rugby League",
        "text": (
            "Tonga are fifth in the IRL world rankings on 54 points; Lebanon are 23rd on seven. The "
            "47-point gap in ranking points points to a comfortable Tonga win, and our margin model "
            "makes a three-point winning margin 71.2%. Selection: Tonga XIII by 3+ at -213."
        ),
    },
    "rugby-league|Papua New Guinea|Samoa|2026-10-24": {
        "sport": "Rugby League",
        "text": (
            "Papua New Guinea are sixth on 47 IRL points and Samoa fourth on 56. Samoa are the "
            "higher-ranked side even though the match is in Port Moresby, and a 6.5-point start "
            "covers that ranking gap. Selection: Samoa +6.5 at -215."
        ),
    },
    "rugby-league|England|France|2026-10-24": {
        "sport": "Rugby League",
        "text": (
            "England are third on 70 IRL points; France are 11th on 21. The 49-point gap is one of "
            "the largest of Round 2, and our model gives England a 3.5-point handicap at 70.8%. "
            "Selection: England -3.5 at -210."
        ),
    },
    "rugby-league|New Zealand|Cook Islands|2026-10-25": {
        "sport": "Rugby League",
        "text": (
            "New Zealand are second on 82 IRL points and Cook Islands eighth on 24. The Kiwis are "
            "heavy favourites, so the value sits at the other end: Cook Islands +19.5 covers in "
            "71.0% of our simulations. Selection: Cook Islands +19.5 at -212."
        ),
    },
    "rugby-league|Australia|Fiji|2026-10-25": {
        "sport": "Rugby League",
        "text": (
            "Australia top the IRL rankings on 100 points; Fiji are seventh on 34. The Kangaroos' "
            "66-point edge is the widest in the round, and our model makes Australia -6.5 a 71.1% "
            "selection. Selection: Australia -6.5 at -212."
        ),
    },
}

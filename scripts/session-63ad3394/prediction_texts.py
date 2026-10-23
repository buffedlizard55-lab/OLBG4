"""Hand-written predictions for Board AK (session arena/63ad3394-olbg4).

One entry per published pick, keyed by desk row id. Every figure is copied from
the official payload recorded on that row (NHL schedule and standings API, MLB
Stats API, EuroLeague/EuroCup game feed, LNR TOP 14 page, PDC fixture service,
WST match service, PlusLiga match centre, RLWC 2026 fixture API, PGA TOUR
leaderboard, formula1.com). Nothing is inferred, and no injury is mentioned
anywhere because no injury feed was captured (see the Flagged for Review page).
"""

TEXTS: dict[str, str] = {
    # ------------------------------------------------ Ice Hockey (NHL)
    "nhl-2026020200": (
        "Edmonton are 8-1-1 in ten games for 17 points, with 47 goals for and 32 against, a "
        "plus 1.5 margin a night. Calgary are 3-6-0 in nine, six points, 19 goals for and 38 "
        "against, and they have conceded more than four a game. Rogers Place has been a hard "
        "trip and the Flames arrive on a six-loss run in nine: Edmonton Oilers at -272."
    ),
    "nhl-2026020217": (
        "Boston are 8-2-1 in eleven games with 42 goals for and only 22 against, the tightest "
        "defence in this slate at 2.0 a night. Chicago are 3-6-0 in nine on six points, 21 "
        "goals for and 36 against, and they come into TD Garden on a defeat. The Bruins have "
        "17 points to Chicago's six, so Boston Bruins at -249."
    ),
    "nhl-2026020206": (
        "Carolina are 8-2-2 in twelve games, 18 points, 47 goals for and 33 against, scoring "
        "3.9 a night. Columbus are 3-5-0 in eight on six points, 20 goals for and 29 against, "
        "and they lost their last outing. The home side has scored 27 more goals over the "
        "season and gives up fewer per game, so Carolina Hurricanes at -217."
    ),
    "nhl-2026020213": (
        "Vancouver are 2-9-1 in twelve games with five points, 35 goals for and 56 against, "
        "conceding 4.7 a night. San Jose are 6-4-1 in eleven on 13 points, 33 goals for and 37 "
        "against, and they won their most recent game. The Canucks have lost nine of twelve "
        "and leak almost five, so San Jose Sharks at -213 is the pick."
    ),
    "nhl-2026020187": (
        "Detroit are 4-3-3 in ten games on 11 points, 28 goals for and 30 against, and they "
        "have won their latest match. That is solid, but it is not an Edmonton team sitting on "
        "8-1-1, 17 points, 47 goals for and 32 against at 4.7 a night. Rogers Place has "
        "favoured the Oilers, so Edmonton Oilers at -190."
    ),
    # ------------------------------------------------ Basketball (EuroLeague / EuroCup)
    "ec_games-67": (
        "Aris Thessaloniki are 4-0 in the EuroCup, scoring 94.5 points a game and conceding "
        "75.25, a plus 19.25 margin over four games. Cedevita Olimpija are 0-4, scoring 72.5 "
        "and conceding 83.25, and every defeat came by at least four with two in double "
        "figures. The gap at both ends is 22 points a night, so Aris Thessaloniki at -587."
    ),
    "el_games-76": (
        "Panathinaikos are 6-1 in the EuroLeague, scoring 87.6 and conceding 73.9 for a plus "
        "13.7 margin, the best in this group. Armani Olimpia Milan are 1-6, scoring 83.6 and "
        "conceding 92.6, and their only win was a two-point game against Virtus Bologna. "
        "Athens has been a fortress, so Panathinaikos AKTOR Athens at -476."
    ),
    "el_games-90": (
        "Olympiacos are 5-1, scoring 98.2 points a game and conceding 89.8 across six "
        "EuroLeague games. Armani Olimpia Milan are 1-6, scoring 83.6 and conceding 92.6 in "
        "seven, and they have lost six of their last seven including a 21-point beating by "
        "Dubai. Milan now travel to Piraeus, so Olympiacos Piraeus at -414."
    ),
    "ec_games-91": (
        "Napoli Basketball are 4-0 in the EuroCup, scoring 92.0 and conceding 83.5 for a plus "
        "8.5 margin, and they have won every game by at least six. Dolomiti Energia Trento are "
        "1-3, scoring 79.0 and conceding 86.25, with a 25-point defeat already on the record. "
        "Napoli's home form and scoring depth make Napoli Basketball at -360 the call."
    ),
    "el_games-72": (
        "Dubai Basketball are 5-2 in the EuroLeague, scoring 85.3 and conceding 83.4 across "
        "seven games, and they have won three of their last four. Paris Basketball are 1-5, "
        "scoring 84.0 and conceding 90.8, with a 19-point loss to Panathinaikos among the "
        "defeats. Dubai's home record and the plus 1.9 margin are enough: Dubai Basketball at "
        "-297."
    ),
    # ------------------------------------------------ Rugby Union (TOP 14)
    "top14-11867": (
        "Stade Toulousain lead the TOP 14 on 24 points after six rounds, five wins and one "
        "defeat, with 197 points scored and 124 conceded, a plus 73 difference. USA Perpignan "
        "are 3-3 on 13 points, 166 scored and 199 conceded, 33 points in the red. Toulouse "
        "have won their last five and concede 20.7 a game: Stade Toulousain at -271."
    ),
    "top14-11866": (
        "Section Paloise are second on 22 points from five wins and one defeat, with 239 points "
        "scored and 181 conceded. RC Toulon are 2-4 on 12 points, 130 scored and 130 conceded, "
        "level on points difference while Pau sit plus 58. Pau have won five of six and travel "
        "with the better pack, so Section Paloise at -265."
    ),
    "top14-11862": (
        "RC Vannes are bottom of the TOP 14 with one point from six defeats, 117 points scored "
        "and 176 conceded, and they have not led at half-time in the run. ASM Clermont are 2-4 "
        "on 11 points with 140 scored and 169 conceded, and their wins came against sides above "
        "Vannes. A winless home side against that is the spot: ASM Clermont at -180."
    ),
    "top14-11861": (
        "Aviron Bayonnais are 4-2 on 17 points, with 190 points scored and 214 conceded, and "
        "they come home after a win. LOU Rugby are 3-3 on 14 points, 193 scored and 202 "
        "conceded, and they have alternated wins and defeats through six rounds. Bayonne have "
        "the extra league points and home advantage, so Aviron Bayonnais at -158."
    ),
    "top14-11865": (
        "Montpellier have scored 163 points and conceded 122 in six rounds for a plus 41 "
        "difference, 6.8 a game. Racing 92 are 2-4, with 143 scored and 196 conceded, and they "
        "have lost four of six. Racing's defence has been the weaker of the two all season, so "
        "Montpellier Herault Rugby at -143."
    ),
    # ------------------------------------------------ Baseball (World Series)
    "mlb-849805": (
        "Milwaukee won 103 games to Tampa Bay's 98 and out-scored them over the season, 5.14 "
        "runs a game to 4.54, while conceding 3.82 against 4.01. The Brewers finished the "
        "regular season winning five straight and the Rays lost their last game. American "
        "Family Field opens the series, so Brewers at -128."
    ),
    # ------------------------------------------------ Darts (PDC European Championship)
    "pdc-88052-SteKim": (
        "Stephen Bunting has won four of five completed matches in Dortmund, taking 28 legs to "
        "18, while Kim Huybrechts has won one of two with 11 legs to 7. Bunting has played "
        "twice as many matches and holds a plus 2.0 leg margin a game. Over a long format that "
        "matters, so Stephen Bunting at -151."
    ),
    "pdc-88052-RosDam": (
        "Damon Heta has won four of five at the European Championship, taking 27 legs to 20, a "
        "plus 1.4 margin a match. Ross Smith has won two of three, 16 legs to 12, but has "
        "played fewer completed matches. Heta's heavier scoring and longer route through the "
        "draw make him the call: Damon Heta at -128."
    ),
    "pdc-88053-WesMar": (
        "Wessel Nijman has won two of three completed matches in Dortmund, taking 17 legs to "
        "12 for a plus 1.67 margin. Martin Schindler has won one of two and is level on legs at "
        "10 apiece, so his scoring has not separated him from his opponents. Nijman has the "
        "better leg difference and the stronger record, so Wessel Nijman at -124."
    ),
    # ------------------------------------------------ Snooker (Northern Ireland Open)
    "wst-45bc77f9": (
        "Sam Craigie has won all three of his matches in Belfast for a 14-7 frame record, a "
        "plus 2.33 frame margin a match. Kyren Wilson has won two from two with 10 frames to "
        "4, but has played one fewer match. Craigie has taken the longer route through the "
        "draw with the sharper scoring across more frames: Sam Craigie at -109."
    ),
    # ------------------------------------------------ Golf (PGA TOUR)
    "golf-R2026528": (
        "Kensei Hirata is tied for the lead at 13 under through two rounds at Port Royal, "
        "having opened 65 and 64 for 129 strokes. The top-ten line sits at 11 under, so he is "
        "two strokes inside it with 36 holes to play, and only one player in the 120-man field "
        "has gone lower than his 64. Kensei Hirata for a top ten at -495."
    ),
    # ------------------------------------------------ Motor Racing (Formula 1)
    "f1-2026-united-states": (
        "Mercedes lead the 2026 constructors' championship on 578 points, with Ferrari on 444 "
        "and McLaren on 339 after seventeen rounds. Round 18 is the United States Grand Prix "
        "at the Circuit of the Americas over 56 laps on 25 October, and in first practice "
        "George Russell was fourth and Kimi Antonelli fifth behind Charles Leclerc's 1:36.052. "
        "Mercedes to supply the race winner at +234."
    ),
    # ------------------------------------------------ Volleyball (PlusLiga)
    "plusliga-energa-indykpol-azs-olsztyn-zaksa-k-dzie-2026-10-29": (
        "Energa Indykpol AZS Olsztyn have started the PlusLiga season with a 3-0 sets win and "
        "no sets dropped, while ZAKSA Kedzierzyn-Kozle have lost both matches 0-2 on sets, "
        "winning only one of seven sets played. That is a 6-1 set deficit against a side yet "
        "to concede. Olsztyn at home with that margin is the call at -655."
    ),
    "plusliga-energa-trefl-gda-sk-stilon-gorz-w-2026-11-03": (
        "Stilon Gorzow opened with a five-set win, taking three sets to two, while Energa Trefl "
        "Gdansk have lost both matches and have won only one set out of seven played. Gdansk "
        "concede three sets a match on average across the two defeats. With the set numbers "
        "this far apart, Stilon Gorzow at -426 is the pick."
    ),
    "plusliga-jastrz-bie-barkom-podziemia-kredowe-chks-2026-11-01": (
        "Jastrzebie Barkom won their opener 3-2 on sets, while Podziemia Kredowe ChKS Chelm "
        "lost theirs 2-3 and have played one match. The set margins are close, but Jastrzebie "
        "have the win on the board and home advantage in front of their own crowd. On the "
        "set records from that feed, Jastrzebie Barkom at -407."
    ),
    "plusliga--lepsk-malow-suwa-ki-neonet-norwid-cz-st-2026-10-30": (
        "NEONET Norwid Czestochowa have played two matches, winning one, but have taken three "
        "sets and lost five. Slepsk Malow Suwalki have lost both of theirs and have four sets "
        "to six. Neither side has settled, so the price sits closer to a coin flip, and the "
        "visitors' extra win makes NEONET Norwid Czestochowa at -199 the lean."
    ),
    "plusliga-bogdanka-luk-lublin-gks-katowice-2026-10-31": (
        "BOGDANKA LUK Lublin have won both matches without dropping a set, six sets to nil, "
        "while GKS Katowice have played once and taken it 3-2. Lublin's clean sheet across two "
        "matches is the strongest set record of the four sides in this round. At home, with "
        "that margin, BOGDANKA LUK Lublin at -174."
    ),
    # ------------------------------------------------ Rugby League (World Cup)
    "rlwc-20261310330": (
        "Australia opened their World Cup with a 24-22 win over New Zealand, 24 points scored "
        "and 22 conceded. Cook Islands lost their opener 12-40, conceding 40 points and "
        "scoring two tries' worth, a minus 28 margin. The gap in points difference is 30 "
        "across the two games, so Australia at -448 in Townsville."
    ),
    "rlwc-20261310310": (
        "Papua New Guinea opened with a 42-18 win, 42 points scored and 18 conceded, a plus 24 "
        "margin. England lost their opener 12-30, scoring 12 and conceding 30, a minus 18 "
        "margin. The two records sit 42 points apart on points difference, and the Kumuls' "
        "scoring rate is more than three times England's, so Papua New Guinea at -391."
    ),
    "rlwc-20261310320": (
        "Fiji opened their World Cup with a 40-12 win, a plus 28 margin, scoring 40 points. New "
        "Zealand lost their opener 22-24 to Australia, a minus 2 margin, and have conceded more "
        "than they have scored. Fiji's points difference is 30 better across the two games, so "
        "Fiji at -339 on the Gold Coast."
    ),
    "rlwc-20261310230": (
        "England lost their opener 12-30 but scored twice as many points as France did in "
        "theirs. France were beaten 4-78, conceding 78 points and scoring four, a minus 74 "
        "margin that is the worst in the pool. At HBF Park in Perth, with the ground rated good "
        "and the weather fine, England at -225."
    ),
    "rlwc-20261310340": (
        "Lebanon lost their opener 18-42, scoring 18 and conceding 42, a minus 24 margin. "
        "France were beaten 4-78 in theirs, scoring four points and conceding 78, a minus 74 "
        "margin. The 50-point gap in points difference across the two games is the widest of "
        "this round, so Lebanon at -210 in Sydney."
    ),
}

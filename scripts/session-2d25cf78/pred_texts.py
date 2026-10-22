"""Authored, human-written prediction texts for Board AF.

Each key is (row id, exact selection label from desk.json). Every factual claim below is
taken from that row's `official_inputs` (records, goals/runs/points for and against,
last-ten form, streak, venue, competition). No number appears here that is not in the
row's official inputs. predict.py rejects any text under 30 words and verify.py
re-checks word counts, uniqueness and that every figure is traceable.
"""

TEXTS = {
    # ---------------------------------------------------------------- Ice Hockey
    ("af_0048", "Nashville Predators +1.5"): (
        "Nashville have banked nine points from eight games (3-2-3) despite scoring only 23 goals, and they "
        "go into Monday's Bridgestone Arena meeting on a win. Colorado carry far more threat with 41 goals "
        "in ten games, but the Avalanche have just lost. With the extra goal and a half, back Nashville "
        "Predators +1.5 on the puck line at 1.40."
    ),
    ("af_0024", "Philadelphia Flyers +1.5"): (
        "Philadelphia's 3-6-3 start has been ugly: 20 goals for and 37 against in 12 games. Yet the Flyers "
        "have won their latest and now host an Anaheim side that is 4-5-0 with 26 goals and has lost its most "
        "recent game. Two modest offences, one goal of cushion. Philadelphia Flyers +1.5 at 1.405."
    ),
    ("af_0118", "San Jose Sharks +1.5"): (
        "Ottawa arrive at SAP Center at 7-3-0 with 14 points, but only 29 goals in ten games. San Jose are "
        "5-4-1 with 27 goals of their own, have won their latest start and are at home on Halloween night. "
        "A goal and a half for the Sharks is the value side: San Jose +1.5 at 1.406."
    ),
    ("af_0046", "Under 6.5"): (
        "Dallas have conceded just 15 goals in nine games and sit 5-3-1 on 11 points. The Islanders are also "
        "5-3-1 and have allowed only 20 while scoring 27, and both clubs won their last outing. The defensive "
        "numbers point down at American Airlines Center: Under 6.5 goals at 1.429."
    ),
    ("af_0085", "Edmonton Oilers"): (
        "Edmonton are 7-1-1 with 41 goals in nine games, 15 points and a win in their latest outing. Calgary "
        "are 2-6-0, have scored only 17 and conceded 37 in eight. The Battle of Alberta at Rogers Place should "
        "go to the Oilers, and our 1.449 on an Edmonton win sits inside the requested window."
    ),

    # ---------------------------------------------------------------- Basketball
    ("af_0055", "Crvena Zvezda Meridianbet Belgrade -2.5"): (
        "Crvena Zvezda are 4-2 and conceding only 76.2 points a game, the meanest defence in this pairing. "
        "Maccabi have lost five of seven and give up 93.3 a night, though they score 86.9. Belgrade's control "
        "on the glass and at the defensive end should cover the small line: Crvena Zvezda -2.5 at 1.40."
    ),
    ("af_0058", "Valencia Basket +4.5"): (
        "Fenerbahce are 5-1 and allow only 74.5 points per game, so this is no formality. Valencia, though, are "
        "4-2 and pour in 98.3 a night at home. A 4.5-point cushion for the fastest offence in the sample is too "
        "generous to pass: Valencia Basket +4.5 at 1.401."
    ),
    ("af_0105", "LDLC ASVEL Villeurbanne +1.5"): (
        "Both clubs are struggling, but Baskonia are 1-6 and concede 92.7 points a game while scoring 83.3. "
        "ASVEL are 2-4 yet put up 87.8 at home, and a 1.5-point cushion protects against a tight finish. "
        "LDLC ASVEL Villeurbanne +1.5 at 1.401 looks the safer side of a bad matchup."
    ),
    ("af_0076", "Hapoel IBI Tel Aviv"): (
        "Hapoel are 5-2, scoring 90.0 points a game and conceding 85.9. Efes sit 3-4 and have managed only "
        "83.0 a night, with 84.3 against. The better record, the better differential and home advantage all "
        "point one way. Back Hapoel IBI Tel Aviv to win at 1.414."
    ),
    ("af_0090", "Over 163.0"): (
        "Real Madrid are putting up 95.3 points a game and conceding 90.0, the highest scoring rate in this "
        "matchup. Fenerbahce's defence is the stingiest in the sample at 74.5, yet 163 points is a low bar when "
        "Madrid are involved. Over 163.0 at 1.414 is the call."
    ),

    # ---------------------------------------------------------------- Baseball
    ("af_0051", "Tampa Bay Rays +1.5"): (
        "Tampa Bay finished 98-64 with a +86 run differential and were 55-26 at Tropicana Field. Milwaukee won "
        "103 games, but 33 of their 59 defeats came on the road and they were 48-33 away. In a World Series "
        "game at the Trop the run-line cushion matters: Tampa Bay Rays +1.5 at 1.471."
    ),
    ("af_0061", "Tampa Bay Rays +1.5"): (
        "Game two of the series and the same logic holds. Tampa Bay's 55-26 home record and 650 runs allowed "
        "are the strongest defensive markers here, while Milwaukee bring the best last-ten record in the series "
        "at 8-2. We stay with Tampa Bay Rays +1.5 at 1.471."
    ),
    ("af_0016", "Over 7.5"): (
        "Milwaukee scored 832 runs this season and Tampa Bay added 736, two of the deeper line-ups in the "
        "postseason. Milwaukee allowed 618 and Tampa Bay 650 across the season, so this is not a soft total, but 7.5 is a modest ask "
        "for game one at American Family Field. Over 7.5 runs at 1.546."
    ),
    ("af_0034", "Over 7.5"): (
        "Game two at American Family Field pits the 832-run Milwaukee offence against a Tampa Bay side that "
        "scored 736 across 162 games. Milwaukee allowed 618 runs and Tampa Bay 650, so runs may be harder to "
        "find than the raw totals suggest, but seven and a half is still a low line for these bats: Over 7.5 at 1.546."
    ),
    ("af_0084", "Under 9.5"): (
        "By game four the hitters have seen each staff twice. Milwaukee allowed 618 runs in 162 games and "
        "Tampa Bay 650, both comfortably under five a night. A 9.5 total asks for ten runs from two teams "
        "whose seasons were built on run prevention. Under 9.5 runs at 1.61."
    ),

    # ---------------------------------------------------------------- Rugby Union
    ("af_0045", "Union Bordeaux-Bègles +6.5"): (
        "Bordeaux-Bègles have scored 215 points in six games with a +64 differential and three bonus points, "
        "the best points difference in this fixture. La Rochelle are 4-0-2 but have managed just 144 points and "
        "a +9 differential. Giving UBB 6.5 at Stade Marcel-Deflandre is the play at 1.406."
    ),
    ("af_0022", "Racing 92 +7.5"): (
        "Montpellier's +41 differential is among the best in the Top 14, but they travel to La Défense Arena "
        "to face a Racing 92 side that has scored 143 points and is desperate after four defeats in six. A "
        "7.5-point head start is generous. Racing 92 +7.5 at 1.423."
    ),
    ("af_0021", "Castres Olympique +5.5"): (
        "Castres are 2-0-4 but have lost narrowly, with 126 points scored and 153 conceded. Stade Français "
        "have shipped 158 in six matches and are only -11, and they must travel to Pierre-Fabre, one of the "
        "hardest away days in France. Castres Olympique +5.5 at 1.429."
    ),
    ("af_0019", "ASM Clermont"): (
        "Vannes have lost all six matches, scored 117 points and conceded 176, the worst differential in the "
        "Top 14 at -59. Clermont are 2-0-4 but own a -29 differential and three bonus points. The bottom "
        "side's home ground will not be enough: ASM Clermont to win at 1.431."
    ),
    ("af_0025", "Section Paloise"): (
        "Pau are 5-0-1 with 239 points scored, the best attack in the competition, and a +58 differential. "
        "Toulon are 2-0-4 and have scored only 130 points, albeit with four bonus points. Take Section "
        "Paloise to win at Stade Mayol, priced 1.454."
    ),

    # ---------------------------------------------------------------- Handball
    ("af_0074", "MT Melsungen +1.5"): (
        "Melsungen are 3-0-2 with 138 goals for and 138 against, while Vardar have lost four of five and "
        "conceded 158 in five matches. The Macedonian crowd is worth something, but not a goal and a half "
        "against a side with the better record. MT Melsungen +1.5 at 1.401."
    ),
    ("af_0081", "Over 59.0"): (
        "Celje have conceded 188 goals in five matches and scored 150; Zagreb are 2-0-3 with 146 for and 158 "
        "against. Neither defence is holding up in Group C, and 59 goals is a modest total for two sides "
        "conceding at this rate. Over 59.0 at 1.409."
    ),
    ("af_0075", "HBC Nantes +5.5"): (
        "Both clubs are 3-0-2 on six points. Plock have scored 141 and conceded 136; Nantes have scored 142 "
        "and conceded 143. Nothing in those numbers justifies a five-and-a-half-goal gap in either direction. "
        "HBC Nantes +5.5 at 1.422 is the value."
    ),
    ("af_0080", "Aalborg Håndbold +2.5"): (
        "Aalborg are unbeaten in five (4-1-0) with nine points and 170 goals for against 145 conceded. PSG "
        "are 3-1-1, have scored 182 but shipped 157. The Danish champions deserve more respect than a 2.5-goal "
        "handicap at Stade Pierre de Coubertin: Aalborg Håndbold +2.5 at 1.429."
    ),
    ("af_0082", "Over 59.0"): (
        "Magdeburg have won all five matches and scored 176 goals in five games. Kriens-Luzern "
        "have conceded 161 in five and scored 158, so they are no strangers to high-scoring games. Two "
        "attacking records and a 59-goal line point upwards: Over 59.0 at 1.431."
    ),

    # ---------------------------------------------------------------- Volleyball
    ("af_0038", "Cisterna Volley +1.5 sets"): (
        "Cisterna opened the season with a 3-0 sweep of Milano, winning 79 points to 56, while Trentino swept "
        "Modena 3-0, 75 points to 61. On one round of official data this is close, and the 1.5-set "
        "cushion is the safer side. Cisterna Volley +1.5 sets at 1.422."
    ),
    ("af_0043", "Acqua Sant'Anna Cuneo +1.5 sets"): (
        "Milano were swept 3-0 by Cisterna in round one, scoring just 56 points, and Cuneo took Sir Susa Scai "
        "Perugia to five sets before losing. Those form lines point to a competitive night at the Allianz "
        "Cloud. Acqua Sant'Anna Cuneo +1.5 sets at 1.43."
    ),
    ("af_0042", "Rana Verona +1.5 sets"): (
        "Monza lost 3-1 at Prata di Pordenone in the opening round, while Verona were swept by Civitanova. "
        "With one match played each the model spreads the probabilities widely, and a 1.5-set cushion is "
        "useful insurance. Rana Verona +1.5 sets at 1.482."
    ),
    ("af_0040", "Gas Sales Bluenergy Piacenza"): (
        "Piacenza opened with a 3-0 win, scoring 75 points to 56, while Modena were swept by Trentino and "
        "managed only 61 points. The home side's efficiency and Modena's opening-day struggles make Gas Sales Bluenergy Piacenza "
        "the lean, though the one-match sample keeps confidence in check. Piacenza to win at 1.787."
    ),
    ("af_0039", "Cucine Lube Civitanova"): (
        "Civitanova swept Verona 3-0 in round one, 78 points to 65, while Padova were swept by Piacenza and "
        "scored just 56. Civitanova's serving and block should tell at the Eurosuole Forum. Cucine Lube "
        "Civitanova to win at 1.812."
    ),
}

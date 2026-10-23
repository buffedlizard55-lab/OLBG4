"""Board BW (arena/343754f2-olbg4) — written predictions.

Each entry is (row_id, text). Every number quoted in a text is copied from that
row's `inputs_summary` in data/session-343754f2/desk.json, which itself is derived
from the captured official feed linked on the row. Wording rules enforced by
review.py and verify.py: no internal vocabulary ("model", "verified"), at least
30 words, an explicit "Selection:" line, and pairwise trigram Jaccard below 0.30
so no two texts read alike.

Coverage (33 texts): 5 Ice Hockey, 5 Basketball, 5 Baseball, 5 Tennis,
6 Rugby Union, 4 Volleyball, 2 Handball, 1 Snooker — every High-confidence row on
the desk is included. Injuries are deliberately not claimed: no official injury or
withdrawal report was captured for any of these fixtures, which is stated on the
Flagged page. Sports without a priced fixture on this capture (Cricket, Darts,
Golf, Gaelic Sports, Greyhounds, Motor Racing, Rugby League) carry no text and are
explained instead of padded.
"""

PREDICTIONS = [
    # ------------------------------------------------------------------ Ice Hockey
    ("bw_033",
     "Nashville have been generous hosts without being reckless: 23 goals for and 30 against in nine outings, "
     "a 3-3-3 record that has kept every game close. The Islanders arrive 5-3-2 having scored 29 and conceded 23 "
     "in ten, so two middling attacks meet at Bridgestone Arena. Set the two scoring rates side by side and the "
     "night projects to 5.85 goals, a shade under the posted six. Selection: Under 6.0 total goals at -245."),
    ("bw_040",
     "Washington's 5-4-0 start is built on fine margins: 30 goals scored, 29 conceded through nine games. "
     "Philadelphia have managed only 20 goals in twelve while shipping 37, the second-worst defensive record "
     "in this sample. Capital One Arena therefore gets a home side that does not blow teams away against a "
     "visitor that cannot buy a goal, and the combined expectation of 5.90 points to a low-scoring evening. "
     "Selection: Under 6.0 total goals at -235."),
    ("bw_058",
     "Boston are the form team here, 8-2-1 with 42 goals for and 22 against in eleven starts, so backing them "
     "outright costs more than this column is willing to pay. Chicago's 3-6-0 record with 21 scored and 36 "
     "conceded looks bleak, yet their expected output of 2.48 keeps a one-goal game within reach, and the puck "
     "line only needs that. Selection: Chicago Blackhawks +1.5 at -235."),
    ("bw_067",
     "Colorado return to Ball Arena at 5-4-1 with 41 goals scored and 31 conceded across ten matches, a good "
     "attack but not a suffocating one. Calgary's 3-6-0 with 19 goals for and 38 against explains the price on "
     "the visitors, and the projected 3.85-2.72 margin is exactly the sort that clears a one-and-a-half goal "
     "cushion. Selection: Calgary Flames +1.5 at -246."),
    ("bw_223",
     "KooKoo's Liiga campaign is 1-13 after fourteen rounds, with 31 goals scored and 60 conceded, and HIFK "
     "are not much better at 4-9 with 35 for and 45 against in thirteen. Neither dressing room brings a "
     "potent attack to this one, and the combined scoring rate settles at 5.88. Six goals is a line that "
     "needs an empty-netter or a power-play burst to beat. Selection: Under 6.0 total goals at -240."),

    # ------------------------------------------------------------------- Basketball
    ("bw_129",
     "Bayern's EuroLeague defence is conceding 94.1 points a night during a 2-5 start while scoring 87.4, the "
     "profile of a side that has to win shootouts. Barcelona are 4-3 with 90.1 scored and 88.4 allowed, and "
     "the projected 89.1-90.3 has the Catalans ahead in Munich. A four-and-a-half point cushion covers the "
     "awkward cases, including a one-possession finish. Selection: FC Barcelona +4.5 at -240."),
    ("bw_134",
     "Besiktas have leaked 92.0 points per game across a 3-4 opening while scoring 90.6, so they are rarely "
     "far from the scoreline. Olympiacos sit 5-2 with 92.9 scored and 86.1 allowed, the more complete profile "
     "of the two, and the projection lands 89.4-90.4 in favour of the Greeks. The handicap removes the need "
     "to call the exact margin. Selection: Olympiacos Piraeus +4.5 at -236."),
    ("bw_136",
     "ASVEL are 2-5 and giving up 96.7 points a game while scoring 87.4, the leakiest defence in this group of "
     "fixtures. Partizan are far stingier at 4-3 with 78.7 scored and 79.0 conceded, and the projection reads "
     "86.1-87.4 in a game few expect to be a shootout. A four-and-a-half point start is a generous cushion for "
     "the better defensive side. Selection: Partizan Mozzart Bet Belgrade +4.5 at -247."),
    ("bw_148",
     "Real Madrid average 95.3 points but concede 90.0, so their 4-3 record flatters the attack. Panathinaikos "
     "are 6-1 with 87.6 scored and only 73.9 allowed, the best defensive numbers in this set of games, and the "
     "projection of 86.9-88.1 hands them a narrow edge at the Palacio. Four and a half points is ample for a "
     "side that wins with defence. Selection: Panathinaikos AKTOR Athens +4.5 at -240."),
    ("bw_163",
     "Trento are 1-3 in the EuroCup, scoring 79.0 and conceding 86.2 per game, a combination that has left "
     "little margin in any of their outings. Buducnost are 2-2 with 90.8 for and 86.8 against, and the "
     "projected 84.8-86.1 points their way on the road. The visitors' scoring output makes a four-and-a-half "
     "point cushion comfortable rather than merely hopeful. Selection: Buducnost VOLI Podgorica +4.5 at -245."),

    # ---------------------------------------------------------------------- Baseball
    ("bw_121",
     "Milwaukee's 103-59 season included 832 runs scored, 618 allowed and a 55-26 home record, which is why "
     "they open the Series as favourites. Tampa Bay went 98-64 with 736 scored and 650 conceded, 43-38 on the "
     "road, and the run projection of 4.71-4.05 is closer than the records suggest. A run-and-a-half cushion "
     "on the visitors covers the one-run losses. Selection: Rays +1.5 at -160."),
    ("bw_122",
     "Game two brings the same two profiles back to American Family Field: Milwaukee at 832 runs for and 618 "
     "against with a 55-26 home mark, Tampa Bay at 736 and 650 with a 43-38 road mark. The scoring projection "
     "repeats at 4.71-4.05, a margin under a single run, so buying the cushion is preferable to taking a short "
     "price on the favourite. Selection: Rays +1.5 at -160."),
    ("bw_123",
     "The Series shifts to Tropicana Field, where Tampa Bay's 55-26 home record and 832-618 season run "
     "differential make them a narrow favourite at 4.44 to 4.30. Milwaukee scored 736 and allowed 650 with a "
     "48-33 road split, so they are not the sort of visitor that gets blown out, and a run-and-a-half start is "
     "the value side of a tight projection. Selection: Brewers +1.5 at -248."),
    ("bw_124",
     "Game four keeps the venue and the matchup but not the certainty: Tampa Bay's home 55-26 record sits "
     "alongside 832 runs scored and 618 conceded, while Milwaukee's road 48-33 mark came with 736 scored and "
     "650 allowed. The projected 4.44-4.30 margin is a single run either way, which is precisely when the "
     "underdog's cushion matters most. Selection: Brewers +1.5 at -248."),
    ("bw_125",
     "If a fifth game is needed it will be played under the same roof, and the numbers have not changed: "
     "Tampa Bay 103-59 overall, 832 runs for and 618 against, 55-26 at home; Milwaukee 98-64, 736 and 650, "
     "48-33 on the road. A 4.44-4.30 projection means the game is expected to be decided by a run, so the "
     "visitors' cushion is the safer side of the line. Selection: Brewers +1.5 at -248."),

    # ------------------------------------------------------------------------- Tennis
    ("bw_229",
     "Kudermetova is seeded second in Guangzhou and faces an unseeded opponent, a gap the draw makes explicit. "
     "Neither player has completed a main-draw match at the event yet, so the line rests on the seeding alone "
     "and the three-and-a-half game handicap is the honest way to express that edge without pretending to "
     "know her current form. Selection: Polina Kudermetova -3.5 games at -192."),
    ("bw_230",
     "Yastremska carries the top seed in Guangzhou and meets Xiaodi You, who is unseeded in this draw. With no "
     "completed main-draw sets for either woman, the seed positions are the only published strength signal, "
     "and a two-step gap in the draw is a substantial one at this level. The game handicap asks for a routine "
     "win rather than a specific score. Selection: Dayana Yastremska -3.5 games at -192."),
    ("bw_236",
     "Vandromme is seeded sixth in Guangzhou while Carol Young Suh Lee arrives unseeded, and the seeding gap "
     "is the only official strength marker available because neither has finished a main-draw match here. "
     "Taking the match outright avoids asking a young favourite to also cover a games line on a day when the "
     "draw gives no form to lean on. Selection: Jeline Vandromme at -246."),
    ("bw_240",
     "Samsonova is seeded third in Tokyo and faces Heather Watson, who is unseeded in the Pan Pacific draw. "
     "There is no completed main-draw form for either player in the captured feed, so the seed positions do "
     "all of the work and the three-and-a-half game handicap is the cleanest expression of a clear class gap. "
     "Selection: Liudmila Samsonova -3.5 games at -192."),
    ("bw_252",
     "Fernandez has played nine sets at Ningbo, winning nine and losing nine, with 57 games won and 31 lost. "
     "Bouzkova's tournament reads six sets won and six lost, 37 games to 22. Both figures describe long, "
     "attritional matches rather than quick ones, and the match itself projects close, which pushes the game "
     "count up. Selection: Over 21.5 total games at -139."),

    # -------------------------------------------------------------------- Rugby Union
    ("bw_317",
     "Montpellier are the stronger side on the LNR table, 3-0-3 on 14 points with 163 scored and 122 conceded, "
     "against a Racing team on 10 points whose 143 scored and 196 conceded is the leakiest defence in the round. "
     "The projection of 29.9-19.0 points is a two-score margin, but a two-touchdown cushion for the home side "
     "is more than the gap justifies. Selection: Racing 92 +14.5 at -235."),

    ("bw_313",
     "Vannes have lost all six Top 14 matches and sit on a single point, having scored 117 and conceded 176. "
     "Clermont are 2-0-4 on 11 points with 140 scored and 169 against, hardly a side that runs away with games "
     "on the road. The projection of 21.6-23.1 points keeps the margin inside a converted try, which the "
     "five-point start more than covers. Selection: RC Vannes +5 at -208."),
    ("bw_315",
     "Bayonne have 17 points from six matches (4-0-2) with 190 scored and 214 conceded, while LOU are on 14 "
     "points at 3-0-3 with 193 for and 202 against. Both defences have leaked, and the projection of 41.9-38.6 "
     "points makes this a high-scoring afternoon in which home advantage is worth roughly a score. Selection: "
     "Aviron Bayonnais +0.5 at -196."),
    ("bw_316",
     "Castres are 2-0-4 on nine points with 126 scored and 153 conceded, while Stade Français have 14 points "
     "from 3-0-3 with 147 for and 158 against. The projections are almost level at 21.7-21.0, so a three-point "
     "start for the home side sits on the right side of a game the table says is closer than the standings "
     "suggest. Selection: Castres Olympique +3 at -220."),
    ("bw_318",
     "Toulon's 2-0-4 record carries an even 130-130 points differential, the mark of a side that loses tight "
     "games. Pau are the form team of the round at 5-0-1 on 22 points with 239 scored and 181 conceded, and "
     "the projection of 25.7-29.1 puts them clear at Stade Mayol. The visitors' attack has been the best in "
     "the league so far. Selection: Section Paloise (away) at -218."),
    ("bw_319",
     "La Rochelle are 4-0-2 on 18 points with 144 scored and 135 conceded, a solid but unspectacular profile. "
     "Bordeaux-Bègles have the same record and 19 points, yet their 215 points scored against 151 conceded is "
     "a different level of output. The projection reads 23.7-27.2 in the visitors' favour, and the away win "
     "is the cleaner expression of that gap. Selection: Union Bordeaux-Bègles (away) at -227."),

    # --------------------------------------------------------------------- Volleyball
    ("bw_262",
     "Trentino sit third in the SuperLega classifica after one match, a 3-0 set win worth three points and a "
     "set quotient of 1.23. Cisterna are top on the same points with a 3-0 win and a quotient of 1.41, so the "
     "table separates them by set margin rather than results. With one match each, home advantage is the only "
     "tie-breaker and it makes this a genuine coin flip. Selection: Itas Trentino at -106."),
    ("bw_263",
     "Perugia are sixth after a 3-2 win that brought two points and a set quotient of 1.20, while Prata are "
     "fifth on three points from a 3-1 victory with a quotient of 1.03. The points-per-game measure therefore "
     "favours the visitors despite the home court, and the projection gives Prata the edge. One match each "
     "means the sample is thin, which is why this stays a measured pick. Selection: Tinet Prata di Pordenone "
     "at -196."),
    ("bw_264",
     "Civitanova opened with a 3-0 win, three points and a set quotient of 1.20, good for fourth. Padova lost "
     "their opener 0-3, took nothing from it and carry a quotient of 0.75, which is last in the early table. "
     "The gap in both points and set margin is wide enough that the home win is the obvious side even at a "
     "short price. Selection: Cucine Lube Civitanova at -568."),
    ("bw_265",
     "Monza lost their opening match 1-3 and hold a set quotient of 0.97, eighth in the classifica. Verona "
     "also lost, 0-3, with a quotient of 0.83 and ninth place. Two winless sides with one match apiece leaves "
     "home advantage as the deciding input, and it is worth only a small edge, so the price stays close to "
     "even money. Selection: Vero Volley Monza at -124."),

    # ------------------------------------------------------------------------ Handball
    ("bw_260",
     "Skive have one win in ten Herreligaen rounds, scoring 328 goals and conceding 366, a differential of "
     "minus 38 that explains their two points. Aalborg are 7-1-2 with 323 scored and 306 against, and the "
     "projection of 32.8-32.3 has the visitors narrowly ahead despite the away trip. A three-and-a-half goal "
     "start is a useful cushion in a league where one hot spell decides matches. Selection: Aalborg Handbold "
     "+3.5 at -259."),
    ("bw_261",
     "Skjern are 6-0-4 on 12 points with 329 goals scored and 309 conceded, a solid if unspectacular home "
     "profile. Ribe-Esbjerg are 7-1-2 on 15 points with 332 for and 311 against, marginally the better side on "
     "the table. The projection of 33.0-30.8 still hands the home team the edge, and the match outright is "
     "priced accordingly rather than with a handicap. Selection: Skjern Handbold at -203."),

    # ------------------------------------------------------------------------- Snooker
    ("bw_312",
     "Wilson is ranked ninth in the world and has won all four of his matches at the Northern Ireland Open, "
     "taking 18 frames and losing six. Craigie, ranked 70th, has won six matches and 26 frames while losing "
     "12, so he arrives with more table time but against a far stronger opponent. The rank gap is decisive "
     "over a long semi-final. Selection: Kyren Wilson at -568."),
]

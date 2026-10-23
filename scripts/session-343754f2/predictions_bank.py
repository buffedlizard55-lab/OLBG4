"""Board BW (arena/343754f2-olbg4) — written predictions.

Each entry is (row_id, text). Every number quoted in a text is copied from that
row's `inputs_summary` in data/session-343754f2/desk.json, which itself is
derived from the captured official feed linked on the row. Wording rules
enforced by review.py and verify.py: no internal vocabulary ("model",
"verified"), at least 30 words, an explicit "Selection:" line, and pairwise
trigram Jaccard below 0.30 so no two texts read alike.

Coverage: 5 Ice Hockey, 5 Basketball, 5 Baseball, 5 Tennis, 5 Rugby Union,
4 Volleyball, 2 Handball, 1 Snooker = 32 texts. All 13 High-confidence rows are
included. Sports without a priced fixture on this capture (Cricket, Darts, Golf,
Gaelic Sports, Greyhounds, Motor Racing, Rugby League) carry no text and are
explained on the Flagged page instead of being padded.
"""

PREDICTIONS = [
    # ---------------- Ice Hockey ----------------
    ("bw_033",
     "Nashville's Bridgestone Arena fixture against the Islanders shapes as a low-event night. The Predators "
     "are 3-3-3 through nine games with 23 goals scored and 30 conceded, while New York arrive 5-3-2 having "
     "scored 29 and allowed 23 in ten outings. Combining those two scoring rates gives an expected total of "
     "5.85 for the night. Selection: Under 6.0 total goals at -245."),
    ("bw_040",
     "Washington host Philadelphia with 30 goals scored and 29 conceded in nine games, a 5-4-0 start that has "
     "been built on narrow margins. The Flyers are 3-6-3 and have managed only 20 goals in twelve while "
     "conceding 37. Two cautious attacks meet at Capital One Arena and the projected total is 5.90. "
     "Selection: Under 6.0 total goals at -235."),
    ("bw_058",
     "Boston are flying at 8-2-1 through eleven games with 42 goals for and 22 against, so they deserve to be "
     "favoured at TD Garden. The puck line is where the value sits: Chicago have played nine games (3-6-0, 21 "
     "scored, 36 conceded) and their expected output of 2.48 still keeps a one-goal game live. "
     "Selection: Chicago Blackhawks +1.5 at -235."),
    ("bw_067",
     "Colorado return to Ball Arena at 5-4-1 with 41 goals scored and 31 conceded in ten matches. Calgary's "
     "record reads 3-6-0 with 19 scored and 38 allowed, which is exactly why the price on the visitors' "
     "cushion is attractive rather than the money line. The margin works out at 3.85-2.72. "
     "Selection: Calgary Flames +1.5 at -246."),
    ("bw_223",
     "KooKoo's Liiga season stands at 1-13 from fourteen rounds with only 31 goals scored against 60 conceded. "
     "HIFK are 4-9 with 35 for and 45 against in thirteen games, so neither side arrives with anything like a "
     "potent attack. The combined scoring rate works out at 5.88. "
     "Selection: Under 6.0 total goals at -240."),
    # ---------------- Basketball ----------------
    ("bw_129",
     "Bayern's defence has leaked 94.1 points a night during a 2-5 EuroLeague start, scoring 87.4 at the other "
     "end. Barcelona arrive 4-3 with 90.1 scored and 88.4 allowed, and the projected margin of 89.1-90.3 puts "
     "the Catalans ahead in Munich. Selection: FC Barcelona +4.5 at -240."),
    ("bw_134",
     "Besiktas have conceded 92.0 points per game while going 3-4, and their 90.6 scoring rate has not been "
     "enough to protect home court. Olympiacos are 5-2 with 92.9 scored and 86.1 allowed, and the projection "
     "reads 89.4-90.4 in their favour in Istanbul. Selection: Olympiacos Piraeus +4.5 at -236."),
    ("bw_136",
     "Villeurbanne's 2-5 start is built on 96.7 points allowed per night, a figure their 87.4 scoring rate has "
     "not been able to offset. Partizan counter with a 4-3 record and the tightest numbers in the pairing, "
     "78.7 scored and 79.0 allowed. The line settles at 86.1-87.4. "
     "Selection: Partizan Mozzart Bet Belgrade +4.5 at -247."),
    ("bw_148",
     "Real Madrid score 95.3 a night but give up 90.0, and their 4-3 record reflects that trade-off. "
     "Panathinaikos arrive at 6-1 having allowed only 73.9 points per game while scoring 87.6, so the Greek "
     "side's defence travels. The projection gives them an 86.9-88.1 edge at the Movistar Arena. "
     "Selection: Panathinaikos AKTOR Athens +4.5 at -240."),
    ("bw_163",
     "Trento's EuroCup campaign has produced a 1-3 record with 79.0 points scored and 86.2 conceded per game. "
     "Buducnost, at 2-2, average 90.8 at the offensive end and 86.8 at the other, which translates into an "
     "84.8-86.1 projection for the trip to the BTS Arena. "
     "Selection: Buducnost VOLI Podgorica +4.5 at -245."),
    # ---------------- Baseball (World Series) ----------------
    ("bw_121",
     "The World Series opens at American Family Field with Milwaukee's 103-59 season, 832 runs scored and 618 "
     "allowed, against Tampa Bay's 98-64 campaign and a 736-650 run ledger. The Brewers went 55-26 at home, yet "
     "the run projection of 4.71-4.05 is close enough for the visitors' cushion to matter. "
     "Selection: Tampa Bay Rays +1.5 at -160."),
    ("bw_122",
     "Sunday's second game keeps the same shape. Milwaukee's 832 runs are the best figure in the series, but "
     "Tampa Bay's 43-38 road record and 650 runs allowed describe a side that stays in games, and the Rays won "
     "55 of 81 at home themselves. A 4.71-4.05 projection leaves the one-run buffer doing real work. "
     "Selection: Tampa Bay Rays +1.5 at -160 for Game 2."),
    ("bw_123",
     "Game three moves to Tropicana Field, where Tampa Bay were 55-26 during the season. Milwaukee scored 5.14 "
     "runs a game across the campaign while Tampa Bay allowed 4.01, which produces a 4.44-4.30 projection for "
     "the visitors. At +1.5 the Brewers cover a one-run defeat. "
     "Selection: Milwaukee Brewers +1.5 at -248."),
    ("bw_124",
     "Game four repeats the matchup and the arithmetic. Milwaukee's 832 runs against 618 allowed dwarf Tampa "
     "Bay's 736 and 650, and a 48-33 road record supports the edge, even allowing for the Rays' home form. The "
     "projection sits at 4.44-4.30. Selection: Milwaukee Brewers +1.5 at -248 for Game 4."),
    ("bw_125",
     "If a fifth game is needed at Tropicana Field, the same 4.44-4.30 split applies, built from Milwaukee's "
     "5.14 runs per game and Tampa Bay's 4.01 allowed per game. The Rays' 55-26 home record is real, but the "
     "cushion covers the likely one-run margin. "
     "Selection: Milwaukee Brewers +1.5 at -248, scheduled only if required."),
    # ---------------- Tennis ----------------
    ("bw_253",
     "Ningbo's main draw puts top seed Elena Rybakina against sixth seed Diana Shnaider. The official "
     "tournament feed already shows Rybakina at 23 games won against five lost in this event, while Shnaider "
     "has needed 45 games to win 28. The seed gap and that scoring margin produce a 0.8205 match probability. "
     "Selection: Elena Rybakina -3.5 games at -181."),
    ("bw_254",
     "Top seed Ann Li meets Ashlyn Krueger in Osaka with 50 games won and 25 lost across her completed singles "
     "sets at the event, while Krueger stands at 36 won and 16 lost. An eight-place seed gap plus that game "
     "differential produces a 0.85 match probability. "
     "Selection: Ann Li -3.5 games at -192."),
    ("bw_252",
     "Leylah Fernandez and Marie Bouzkova are separated by little in Ningbo. Fernandez has won 57 games and "
     "lost 31 at the event, Bouzkova 37 and 22, and neither carries a seed in the draw. Two closely matched "
     "baseliners with 9-9 and 6-6 set records point to a long, attritional match. "
     "Selection: Over 21.5 total games at -139."),
    ("bw_255",
     "Katie Boulter is seeded eighth in Osaka and has split 14 sets at the tournament, winning 42 games and "
     "losing 16. Katerina Siniakova has also split 14 sets, with 40 games won and 12 lost. The pairing is close "
     "enough that a deciding set is the likeliest route. "
     "Selection: Over 21.5 total games at -136."),
    ("bw_230",
     "Dayana Yastremska carries the top qualifying seed in Guangzhou and faces Xiaodi You, an unseeded "
     "opponent with no completed singles match at the event. The eight-place gap in the official draw is the "
     "clearest hierarchy available before play begins, and it is wide. "
     "Selection: Dayana Yastremska -3.5 games at -192."),
    # ---------------- Rugby Union (TOP 14) ----------------
    ("bw_319",
     "Bordeaux-Begles have scored 215 points in six TOP 14 rounds and conceded 151, a return that outpaces La "
     "Rochelle's 144 and 135 even though both clubs sit on four wins. The projection reads 23.72-27.15 to the "
     "visitors at Stade Marcel-Deflandre. Selection: Union Bordeaux-Begles to win at -227."),
    ("bw_318",
     "Section Paloise are second with 22 points from six matches, having scored 239 and conceded 181. Toulon "
     "sit on 12 points with a 130-130 record after six rounds, two wins from six. The projection is "
     "25.67-29.06 in the visitors' favour at Stade Mayol. "
     "Selection: Section Paloise to win at -218."),
    ("bw_315",
     "Bayonne have won four of six despite a 190-214 points ledger, and home advantage at Jean-Dauger has been "
     "their anchor. Lyon arrive 3-3 with 193 scored and 202 conceded, and the projection lands 41.87-38.63, a "
     "high-scoring game that favours the hosts. Selection: Aviron Bayonnais to win at -183."),
    ("bw_313",
     "Vannes have lost all six matches, scoring 117 points and conceding 176, and sit bottom of the table on a "
     "single point. Clermont are 2-4 with 140 scored and 169 conceded, and the projection still favours them "
     "21.57-23.05 at Stade de la Rabine. Selection: ASM Clermont to win at -146."),
    ("bw_317",
     "Montpellier arrive at 14 points from six rounds with 163 points scored and 122 conceded, clearly the "
     "stronger side on the numbers, while Racing 92 have leaked 196 points in six matches. The projection reads "
     "19.03-29.88, a margin of roughly eleven points, which leaves the hosts' fourteen-and-a-half cushion with "
     "room to spare. Selection: Racing 92 +14.5 at -235."),
    ("bw_316",
     "Castres have scored 126 points and conceded 153 in six rounds, while Stade Francais sit on 147 scored and "
     "158 conceded. Neither side averages more than 26 points a game, and the combined expectation of 42.75 "
     "sits under the 43-point line at Pierre-Fabre. Selection: Under 43.0 total points at -125."),
    # ---------------- Volleyball (SuperLega) ----------------
    ("bw_264",
     "Cucine Lube Civitanova opened the SuperLega season with a 3-0 sweep and a 1.20 set quotient. Pallavolo "
     "Padova were beaten 0-3 in their opener and sit eleventh with a 0.75 quotient. The gap in the early table "
     "is the widest of the round. Selection: Cucine Lube Civitanova to win at -568."),
    ("bw_263",
     "Tinet Prata di Pordenone took three points from an opening 3-1 win and hold a 1.03 set quotient. Perugia "
     "needed five sets for a 3-2 victory, collecting two points, and their quotient of 1.20 came at a higher "
     "cost in games played. The visitors' early edge is narrow but real. "
     "Selection: Tinet Prata di Pordenone to win at -196."),
    ("bw_265",
     "Both clubs lost their opening fixture, but Monza took a set in a 1-3 defeat and hold a 0.97 set quotient. "
     "Verona were swept 0-3 and carry a 0.83 quotient into the match. Home court tips a close pairing toward "
     "Vero Volley. Selection: Vero Volley Monza to win at -124."),
    ("bw_262",
     "Itas Trentino and Cisterna Volley both opened with 3-0 wins, yet Cisterna's 1.41 set quotient is the "
     "stronger of the two against Trentino's 1.23. Home advantage at the ilT quotidiano Arena narrows that gap "
     "to a near coin flip in the projection. Selection: Itas Trentino to win at -106."),
    # ---------------- Handball (Herreligaen) ----------------
    ("bw_261",
     "Skjern have won six of ten Herreligaen rounds, scoring 329 goals and conceding 309. Ribe Esbjerg are "
     "7-1-2 with 332 scored and 311 conceded, so the two attacks are close. Home advantage in a tight Danish "
     "league tilts the 33.04-30.83 projection Skjern's way. "
     "Selection: Skjern Handbold to win at -203."),
    ("bw_260",
     "Skive's 1-0-9 record includes 328 goals scored and 366 conceded across ten rounds. Aalborg are 7-1-2 "
     "with 323 scored and 306 conceded, a far steadier defensive profile, and they arrive with 15 points "
     "against Skive's two. Selection: Aalborg Handbold +3.5 at -259."),
    # ---------------- Snooker ----------------
    ("bw_312",
     "Kyren Wilson, world number nine, has won all four of his matches at the Northern Ireland Open with an "
     "18-6 frame count. Sam Craigie is also unbeaten at six matches, but he is ranked 70th and has needed 38 "
     "frames to reach the semi-final. Selection: Kyren Wilson to win at -568."),
]

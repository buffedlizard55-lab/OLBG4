"""Board BW (arena/343754f2-olbg4) — prediction texts.

Each entry: (row_id, prediction_text). Every fact quoted is recorded in
data/session-343754f2/desk.json `inputs_summary` with its linked official
source; fair prices are the board's own originated lines. Wording rules: no
internal vocabulary (BANNED substrings), every text states an obvious
selection, every text is unique (pairwise trigram Jaccard < 0.30, enforced
by review.py).

Coverage: 5 Ice Hockey, 5 Basketball, 5 Baseball, 5 Tennis, 2 Handball
(only two Danish Herreligaen fixtures carry originated prices), 3 Volleyball
(four SuperLega ties priced; the fourth pick sits at 0.15 and is left out of
the bank — the shortfall is flagged). Snooker's single priced tie is likewise
left out: its only in-window selection is a 0.15 underdog, recorded on the
desk but not authored here. All twelve High-confidence rows are covered.
"""

PREDICTIONS = [
    # ---------------- Ice Hockey (all five High rows) ----------------
    ("ez_033",
     "Nashville's home date with the Islanders profiles as a low-event night: New York arrive 3-3-3 "
     "through nine games with 23 goals scored and 30 conceded, while the Predators sit 5-3-2 with "
     "29 for and 23 against in ten. The expected scoring lands at 2.87-2.98, comfortably short of "
     "the six-goal board number. Selection: Under 6.0 total goals, priced -245."),
    ("ez_040",
     "Washington host Philadelphia with two offences doing very little: the Capitals manage just 20 "
     "goals across twelve outings (3-6-3) while conceding 37, and the Flyers bring a 5-4-0 record "
     "with 30 scored and 29 against over nine. A 3.31-2.59 expected-goals split leaves the combined "
     "figure under six. The play is Under 6.0 goals at -235."),
    ("ez_058",
     "Chicago travel to Boston as the clearly stronger side on the early evidence: an 8-2-1 start "
     "worth 17 points and a 42-22 goal ledger, against a Bruins team 3-6-0 that has scored 21 and "
     "allowed 36. The visitors' rate works out to 3.72 expected goals against 2.48. "
     "Selection: Chicago Blackhawks +1.5, priced -235."),
    ("ez_067",
     "Calgary's trip to Denver lines the travelling side up against a slumping host. The Flames are "
     "5-4-1 with 41 goals scored and 31 allowed in ten, while Colorado limp along at 3-6-0 with only "
     "19 scored across nine. Our projection puts Calgary ahead 3.85-2.72. "
     "Take Calgary Flames +1.5 at -246."),
    ("ez_225",
     "KooKoo's season has collapsed to 1-13 from fourteen rounds with a 31-60 goal count, and HIFK "
     "offer little punch themselves at 4-9, having scored 35 and conceded 45 in thirteen. Neither "
     "attack pushes a combined total past six; the rate calculation lands at 5.88. "
     "Selection: Under 6.0 total goals, priced -240."),

    # ---------------- Baseball (World Series games 1-5) ----------------
    ("ez_121",
     "The World Series opens in Milwaukee with Tampa Bay owning the better regular-season ledger: "
     "103 wins, 832 runs scored and only 618 allowed, against a Brewers club at 98-64 with a "
     "736-650 differential. The run estimates lean 4.71-4.05 to the Rays, and the visitors still get "
     "the cushion. Selection: Rays +1.5, priced -160."),
    ("ez_122",
     "Sunday's second game finds the Brewers leaning on a 43-38 away mark that travels, yet Tampa "
     "Bay's full-season shape is sharper again — 103 wins versus 98 and a run differential 128 runs "
     "wider. Our line reads 4.71-4.05 in the Rays' favour, so the insurance run stays worth taking. "
     "Selection: Rays +1.5 at -160."),
    ("ez_123",
     "Game three shifts the series to Tampa Bay, where Milwaukee's 98-win summer (736 runs scored, 650 "
     "allowed) meets a hosts' side that went 103-59 behind an 832-618 ledger. Projected scoring of "
     "4.30-4.44 barely separates them, and at +1.5 the visitors cover a one-run defeat at a generous "
     "number. Selection: Brewers +1.5, priced -248."),
    ("ez_124",
     "The fourth game puts Tampa Bay's 48-33 away record under the microscope against a Brewers side "
     "that went 55-26 at home and scored 736 runs across the summer. Expectations of 4.30-4.44 are "
     "essentially a coin flip, which is exactly where underdog insurance earns its keep. "
     "Selection: Brewers +1.5, priced -248."),
    ("ez_125",
     "Should the schedule demand a fifth game on Thursday, the numbers behind it stay the same: "
     "Milwaukee's 736 runs scored and 650 allowed against Tampa Bay's 832 and 618, with only 0.14 "
     "runs between the two projections (4.30-4.44). The cushion is the play. "
     "Take Brewers +1.5 at -248, scheduled if necessary."),

    # ---------------- Basketball (EuroLeague / EuroCup) ----------------
    ("ez_131",
     "Barcelona's trip to Munich lines up against the softest defence on the sheet: Bayern have "
     "surrendered 94.1 points per game across a 2-5 start while scoring 87.4, and the visitors arrive "
     "4-3 at 90.1 and 88.4. The margin computes to 89.2-90.3 for the Catalans. "
     "Selection: FC Barcelona +4.5, priced -240."),
    ("ez_138",
     "Villeurbanne's home floor has not repaired their defence — 96.7 points allowed per night during "
     "a 2-5 start — and Partizan bring a 4-3 record built on restraint (78.7 scored, 79.0 allowed). "
     "The projection reads 86.2-87.5 to Belgrade, so the road underdog plus the points is comfortable. "
     "Selection: Partizan Mozzart Bet Belgrade +4.5 at -247."),
    ("ez_150",
     "Panathinaikos reach Madrid at 6-1 with the stingiest numbers in the comparison: 73.9 points "
     "allowed per night, against Real Madrid's 4-3 season logged at 95.3 for and 90.0 against. Our "
     "totals edge the Greeks 88.2-87.0 despite the venue, so 4.5 points look generous. "
     "Selection: Panathinaikos AKTOR Athens +4.5, priced -240."),
    ("ez_165",
     "The scoring mismatch decides Trento's Round Five tie: Buducnost average 90.8 a night even at "
     "2-2, while Dolomiti manage 79.0 and sit 1-3 after four. The expected margin, 84.8-86.1, hands "
     "Podgorica both the edge and the buffer. "
     "Selection: Buducnost VOLI Podgorica +4.5, priced -245."),
    ("ez_180",
     "Napoli are perfect at 4-0, outscoring opponents 92.0-83.5, and they host a Trento side with one "
     "win in four and 86.2 points conceded per game. The expected margin of 88.0-82.5 is one of the "
     "widest anywhere on our EuroCup card this round. "
     "Selection: Napoli Basketball to win outright, priced -231."),

    # ---------------- Tennis (ATP order-of-play sheets) ----------------
    ("ez_258",
     "Basel's Saturday order of play puts sixth seed Yannick Hanfmann against unseeded Marcos Giron "
     "in the Swiss Indoors, on a sheet released Friday at 19:35. The seeding split — six versus none "
     "— is the asymmetry the tournament itself publishes, and it sets the price. "
     "Selection: Yannick Hanfmann to win, priced -193."),
    ("ez_263",
     "Top seed Sebastian Baez draws the unseeded Giovanni Mpetshi Perricard in Saturday's Basel "
     "programme. First-ranked entry versus no entry in the seeding column usually shows up as broken "
     "serve over a full match, which is precisely what a 3.5-game line asks of the favourite. "
     "Selection: Sebastian Baez minus 3.5 games, priced -192."),
    ("ez_265",
     "Vienna lists Titouan Droguet fifth in Saturday's Erste Bank Open sheet, opposite the unseeded "
     "Joel Schwaerzler. When a seeded slot meets a player without one, the tournament's own hierarchy "
     "has already located the advantage before a ball is struck. "
     "Selection: Titouan Droguet to win, priced -241."),
    ("ez_267",
     "Thiago Tirante arrives as the top name in Vienna's Saturday draw and faces the unseeded Adrian "
     "Mannarino. The gap between a first seed and no seed tends to express itself across a games "
     "handicap rather than a single straight-sets result. "
     "Selection: Thiago Tirante minus 3.5 games at -192."),
    ("ez_271",
     "Corentin Moutet and sixth seed Tomas Machac share Saturday's Vienna card. The official sheet's "
     "seedings, six against none, carry our entire price here — Machac's place above Moutet in that "
     "hierarchy is the whole argument available on release night. "
     "Selection: Tomas Machac to win, priced -193."),

    # ---------------- Handball (the two priced Herreligaen ties) ----------------
    ("ez_281",
     "Skive host Aalborg on Saturday with the league table reading harshly on the home side: one win, "
     "no draws and nine defeats from ten rounds, 328 goals scored against 366. Aalborg's 7-1-2 and 15 "
     "points look far better, yet their scoring rate (323 in ten) barely exceeds Skive's, and home "
     "goals matter here. The expected-goals split of 32.84-32.28 makes Skive FH the play at -120."),
    ("ez_282",
     "Ribe Esbjerg travel to Skjern carrying more points (15 to 12) and a better record, but the "
     "scoring numbers tilt the other way: Skjern have 329 scored and 309 conceded across ten rounds "
     "against Ribe's 332-311, and home output decides it at 33.04-30.83 expected. "
     "Selection: Skjern Handbold, priced -203."),

    # ---------------- Volleyball (three of the four priced SuperLega ties) ----------------
    ("ez_283",
     "The SuperLega table updated on 18 October opens with both of these sides winning their first "
     "match 3-0 — Cisterna sitting first, Trentino third — and only the home court separates them "
     "now. Quotients of 1.23 against 1.41 leave the call almost even (51.5-48.5 percent). "
     "Selection: Itas Trentino to win, priced -106."),
    ("ez_284",
     "Perugia's opener needed five sets to win 3-2 (quotient 1.20), while Pordenone swept theirs 3-1 "
     "for three points, and Sunday's table places them one rank apart, sixth against fifth. The "
     "cleaner visiting start tips our line toward Prata di Pordenone despite the venue. "
     "Selection: Tinet Prata di Pordenone, priced -196."),
    ("ez_285",
     "Monza dropped their first fixture 1-3 and sit eighth; Verona were swept 0-3 and sit ninth. "
     "Both carry zero points, but Monza's quotient (0.97 against 0.83) and home advantage tilt a "
     "nearly even call their way. Selection: Vero Volley Monza to win, priced -124."),
]


def bank_by_row() -> dict:
    return dict(PREDICTIONS)


if __name__ == "__main__":
    for rid, text in PREDICTIONS:
        assert len(text.split()) >= 30, (rid, len(text.split()))
    print(f"prediction bank OK: {len(PREDICTIONS)} texts, all >= 30 words")

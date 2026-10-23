"""Board AH (arena/b2c7308d-olbg4) — prediction texts.

Each entry: (row_id, prediction_text). Facts quoted in every text are the ones
recorded in data/session-b2c7308d/desk.json `inputs_summary` and its linked
official source; the fair prices are the board's own originated lines. Wording
rules: no internal vocabulary, every text states an obvious selection, and every
text is unique (enforced pairwise by review.py). Selection counts: 5 Ice Hockey,
5 Basketball, 5 Baseball, 5 Tennis, 2 Handball (only two Danish Herreligaen
fixtures carry originated prices today; the shortfall is flagged).
"""

PREDICTIONS = [
    # ---------------- Ice Hockey (top five by confidence) ----------------
    ("ah_061",
     "Calgary's road date in Denver is the strangest matchup on Saturday's card: the Flames arrive 5-4-1 "
     "with a lively 41 goals for against 31 conceded in ten, while Colorado sit 3-6-0 on just 6 points, "
     "outscored 38-19 across nine. Even with the altitude in the hosts' favour, a 1.5-goal cushion for the "
     "better traveller is the position to take. Selection: Calgary Flames +1.5, priced -246."),
    ("ah_027",
     "Nashville host the Islanders on Tuesday and neither attack earns a big number right now. "
     "New York are 3-3-3 across nine games with 23 goals for and 30 against; the Predators sit 5-3-2 "
     "on 12 points with a modest 29 scored in ten. With combined expectation around six goals, "
     "the selection is Under 6.0 total goals, which we price at -245."),
    ("ah_146",
     "KooKoo are in free fall — 1-13 through fourteen Liiga rounds, outscored 60-31 — and HIFK arrive "
     "with form that is poor but far less alarming at 4-9 having scored 35 and conceded 45 in thirteen. "
     "Neither side finishes chances, and the season rates put the combined total below the line. "
     "Take Under 6.0 goals at -240 when these two meet on Saturday."),
    ("ah_034",
     "Washington's home date with Philadelphia is a struggle between a leaky defence and a stalled offence. "
     "The Capitals are 3-6-3 with 37 goals conceded in twelve games and just 20 scored; the Flyers counter "
     "at 5-4-0 having traded 30 for and 29 against in nine. Both rates point under — "
     "the play is Under 6.0 total goals, priced -235."),
    ("ah_052",
     "Chicago's revival is the story of the young season: 8-2-1 with 17 points and a 42-22 goal ledger in "
     "eleven games, arriving in Boston to face a Bruins side sitting 3-6-0 and conceding four a night. "
     "Even on the road, the visitors are clearly the stronger club, so the insurance goal is worth buying. "
     "Selection: Chicago Blackhawks +1.5, priced -235."),

    # ---------------- Basketball (EuroLeague / EuroCup) ----------------
    ("ah_102",
     "Trento have lost three of four in EuroCup play, scoring 79.0 a night while conceding 86.2, and now host "
     "a Buducnost side averaging 90.8 in its 2-2 start. The visitors' scoring rate travels, and the projection "
     "makes it 86.1-84.8 despite the home court. With Podgorica catching points, "
     "Buducnost VOLI Podgorica +4.5 is the selection at -245."),
    ("ah_078",
     "Bayern Munich's EuroLeague defence is the soft spot in this fixture: 94.1 points conceded per game "
     "during a 2-5 start, against a Barcelona team putting up 90.1 per night at 4-3. Munich give up nearly "
     "seven more than they score, and the projection has the Catalans ahead 90.3-89.1. "
     "Take FC Barcelona +4.5 at -240 in Munich on Tuesday."),
    ("ah_085",
     "ASVEL have dropped four of six while bleeding 95.3 points per game — the worst defensive rate in this "
     "pairing — while Partizan arrive 4-3 behind a disciplined 78.7 for and 79.0 against. Belgrade's efficiency "
     "edge survives the Villeurbanne road trip, and getting points makes it comfortable: "
     "Partizan Mozzart Bet Belgrade +4.5 is the play at -221."),
    ("ah_108",
     "Tortona host Rostock in EuroCup Round 5 with the visitors wobbling: 1-3, conceding 93.0 per game against "
     "77.2 scored. Derthona's 2-2 record sits on a steadier 82.5-84.0 profile, and home court tips a close "
     "projection (87.3-82.2) firmly their way. The selection is Baglietto Derthona Tortona to win "
     "the game outright, priced -217."),
    ("ah_087",
     "Crvena Zvezda are the quiet overachiever here: 4-3 with 81.0 scored and a stingy 77.4 conceded, "
     "while Bayern arrive 2-5 having allowed 94.1 a night. Belgrade's defence travels and the home crowd "
     "amplifies it; the projection reads 88.9-84.1. Take Crvena Zvezda Meridianbet Belgrade "
     "on the money line at -208 on Thursday."),

    # ---------------- Baseball (World Series) ----------------
    ("ah_069",
     "The scene shifts to Tampa for Game 3, and the Rays' 55-26 home record is the best in the sport — "
     "but Milwaukee's season was the more complete: 103-59 with 832 runs scored and a 48-33 road mark. "
     "A 1.5-run head start for the deeper lineup is the side we want at this price. "
     "Selection: Brewers +1.5, priced -248."),
    ("ah_070",
     "Game 4 in St. Petersburg is the same bet at the same number, and the case does not change: Milwaukee "
     "won 103 games with 832 runs scored and went 48-33 away, while Tampa Bay's 736-650 run profile leans on "
     "one-run margins that a 1.5-run cushion absorbs. Take Brewers +1.5 at -248."),
    ("ah_071",
     "If the series reaches Game 5 on Thursday, Milwaukee's balanced profile — 103-59, 832 scored, 650 allowed, "
     "48-33 on the road — still rates above a Tampa Bay team that scored 736 and defends at 55-26 at home. "
     "The visitor's 1.5-run start is the value. Selection: Brewers +1.5, priced -248."),
    ("ah_067",
     "Game 1 in Milwaukee pits the majors' best home team against a Rays club that won 98 with elite run "
     "prevention: Tampa Bay allowed 618 runs to Milwaukee's 650, and pitching-first openers stay tight. "
     "Tampa Bay went 43-38 on the road, so the 1.5-run start for the visitor is live. "
     "Selection: Rays +1.5, priced -160."),
    ("ah_068",
     "Game 2 stays in Milwaukee, where the 103-59 Brewers went 55-26, but the season math argues for the "
     "cushion: Tampa Bay scored 736 and allowed 618 — a +118 run differential built on pitching — while "
     "Milwaukee allowed 650. Close games dominate when both staffs are this good. "
     "The selection is Rays +1.5 at -160."),

    # ---------------- Tennis ----------------
    ("ah_155",
     "Cobolli against Nakashima is the Lyon quarter-final the top seed was drawn to survive, and the session "
     "sheet makes Flavio Cobolli the No. 1 seed against the American No. 5 seed, not before 19:00 local. "
     "The seed gap is the strongest hard form signal captured today, and it favours the Italian. "
     "Selection: Flavio Cobolli to win, priced -241."),
    ("ah_156",
     "Musetti follows the Cobolli match on the same Lyon court as the No. 6 seed against unseeded Luca Van Assche, "
     "and the seeding is the honest read of current form in this session's data — no completed-tour results feed "
     "was captured today, so confidence stays capped. The Italian's seeding edge still separates them. "
     "Selection: Lorenzo Musetti to win the match, priced -193."),
    ("ah_154",
     "Rybakina versus Shnaider is an all-Russian Ningbo semi-final with two long weeks behind both: the top seed "
     "beat Kudermetova 5-0 ret. and survived Kawa 6-1, 3-6, 6-1, while Shnaider ground past fourth-seeded Jovic "
     "6-3, 4-6, 6-1. Two fatigued baseliners who have both dropped sets this week push this past 21.5 games. "
     "Selection: Over 21.5 total games at -161."),
    ("ah_152",
     "Boulter meets Siniakova in the other Osaka semi-final, and the Briton's week has been anything but routine: "
     "wins over Sakatsume 6-3, 6-1 and Golubic 6-2, 6-1, then a 3-6, 6-3, 6-3 escape against Ruzic. Siniakova "
     "handled Stoiana 6-1, 6-2. Boulter's set-dropping pattern points to a longer afternoon. "
     "Selection: Over 21.5 total games, priced -158."),
    ("ah_157",
     "The Almaty semi-final sends qualifier Nikoloz Basilashvili against seventh-seeded Stefanos Tsitsipas, and "
     "the seeding ladder — a main-draw seed against a qualifier — is the strongest captured signal of whose level "
     "holds over three sets. The Greek's edge is real but not huge, which keeps the price honest. "
     "Selection: Stefanos Tsitsipas to win, priced -155."),

    # ---------------- Handball (Danish Herreligaen) ----------------
    ("ah_180",
     "Ribe-Esbjerg travel to Skjern second in the Betoro Herreligaen on 15 points from ten games (7-1-2) with 332 "
     "goals scored, against a Skjern side mid-table on 12 points after a 6-0-4 run that has produced 329 for and "
     "309 against. The visitors' steadier start travels. Selection: Ribe Esbjerg HH to win away, priced -203."),
    ("ah_179",
     "Aalborg visit bottom-of-the-table Skive, whose 1-0-9 record and 328-366 goal line make them the league's "
     "most porous defence; Aalborg sit third on 15 points with a 323-306 ledger across ten rounds. Form this "
     "one-sided usually holds even on the road. Selection: Aalborg Handbold to win, priced -120."),
]


def bank_by_row() -> dict:
    return dict(PREDICTIONS)


if __name__ == "__main__":
    for rid, text in PREDICTIONS:
        assert len(text.split()) >= 30, (rid, len(text.split()))
    print(f"prediction bank OK: {len(PREDICTIONS)} texts, all >= 30 words")

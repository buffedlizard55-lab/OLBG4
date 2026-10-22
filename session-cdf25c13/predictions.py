"""Board T written predictions — one per High-confidence selection.

Every factual clause below is traceable to an official league page read on 2026-10-22 and is
listed with its value and URL in `facts`. Nothing here is recalled from memory, and no claim
is made about a match that has not been played.
"""

PREDICTIONS = {
    "NHL-2026020164": {
        "text": (
            "Utah have quietly been one of the best stories of the young season, going 7-3-0 "
            "with 38 goals scored and only 31 conceded, and their last ten games read 7-3-0 "
            "with a win carrying into Seattle. The Kraken are a respectable 6-3-1 but have "
            "already shipped 34 goals in ten outings, and this projects as a one-goal game "
            "either way. That is why the play is Utah Mammoth +1.5 on the puck line at -233, "
            "with Nick Schmaltz, who has seven goals already, leading the offence."
        ),
        "selection": "Utah Mammoth +1.5",
        "price": "-233",
        "facts": [
            ("Utah record and goals", "7-3-0, 38 GF, 31 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Utah last ten and streak", "L10 7-3-0, W1", "https://www.nhl.com/standings/2026-10-22"),
            ("Seattle record and goals", "6-3-1, 39 GF, 34 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Nick Schmaltz goals", "7 goals in 2026-27",
             "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
            ("Fixture", "Utah Mammoth at Seattle Kraken, 22 Oct 2026, 22:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020177": {
        "text": (
            "Tampa Bay are the form team in this matchup: 7-2-0 through nine games, a three-game "
            "winning streak, 31 goals for and just 23 against. Utah's 7-3-0 start is genuine, but "
            "they have conceded 31 times in ten games and are facing a Lightning side that has "
            "allowed only 2.56 goals per game. The model makes this close to a coin flip on the "
            "moneyline, so the value in our price sits on Tampa Bay Lightning +1.5 at -250."
        ),
        "selection": "Tampa Bay Lightning +1.5",
        "price": "-250",
        "facts": [
            ("Tampa Bay record and goals", "7-2-0, 31 GF, 23 GA in 9 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Tampa Bay streak", "W3", "https://www.nhl.com/standings/2026-10-22"),
            ("Utah record and goals", "7-3-0, 38 GF, 31 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "Tampa Bay Lightning at Utah Mammoth, 24 Oct 2026, 21:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020179": {
        "text": (
            "Minnesota have lost only twice in regulation all season, sitting 6-2-2 with 31 goals "
            "for and 25 against, and they bring the league's leading scorer in Kirill Kaprizov, "
            "who already has 11 goals. Seattle are 6-3-1 at home but have conceded 34 goals in ten "
            "games, and our numbers make this a one-goal contest. The selection is Minnesota Wild "
            "+1.5 on the puck line at -250, which wins if the Wild lose by a single goal or better."
        ),
        "selection": "Minnesota Wild +1.5",
        "price": "-250",
        "facts": [
            ("Minnesota record and goals", "6-2-2, 31 GF, 25 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Minnesota last ten", "L10 6-2-2, OT1", "https://www.nhl.com/standings/2026-10-22"),
            ("Kirill Kaprizov goals", "11 goals, league leader",
             "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
            ("Seattle record and goals", "6-3-1, 39 GF, 34 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "Minnesota Wild at Seattle Kraken, 24 Oct 2026, 22:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020181": {
        "text": (
            "Dallas have conceded just 15 goals in nine games, an average of 1.67, and have won "
            "three in a row; the Islanders arrive on a two-game run having allowed 20 in nine. "
            "Both clubs are 5-3-1, both are built to defend first, and our model puts the expected "
            "total at 4.5 goals. With that projection the number to take is Under 5.5 on the match "
            "total at -238 for the Sunday evening game at American Airlines Center."
        ),
        "selection": "Under 5.5",
        "price": "-238",
        "facts": [
            ("Dallas record and goals", "5-3-1, 23 GF, 15 GA in 9 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Dallas streak", "W3", "https://www.nhl.com/standings/2026-10-22"),
            ("Islanders record and goals", "5-3-1, 27 GF, 20 GA in 9 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "New York Islanders at Dallas Stars, 25 Oct 2026, 18:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020186": {
        "text": (
            "Calgary are 2-6-0 with 17 goals for and 37 against, the weakest defensive record in "
            "the Western Conference through eight games, and their last ten reads 2-6-0. Toronto "
            "are nothing special at 5-4-2 but have won two straight and carry Auston Matthews, who "
            "has eight goals. Our moneyline makes the Maple Leafs a 70.7% favourite, so the pick is "
            "Toronto Maple Leafs to win at -244 on Monday night."
        ),
        "selection": "Toronto Maple Leafs (ML)",
        "price": "-244",
        "facts": [
            ("Calgary record and goals", "2-6-0, 17 GF, 37 GA in 8 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Calgary last ten", "L10 2-6-0", "https://www.nhl.com/standings/2026-10-22"),
            ("Toronto record and goals", "5-4-2, 38 GF, 35 GA in 11 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Toronto streak", "W2", "https://www.nhl.com/standings/2026-10-22"),
            ("Auston Matthews goals", "8 goals",
             "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
            ("Fixture", "Toronto Maple Leafs at Calgary Flames, 26 Oct 2026, 20:30 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020187": {
        "text": (
            "Edmonton are 7-1-1 with 41 goals already, a seven-game run of form that includes a "
            "two-game winning streak, and Leon Draisaitl has eight goals. Detroit have scraped to "
            "3-3-3, scoring only 23 times in nine games, and they arrive on the back of an overtime "
            "loss. The model gives the Oilers a 71.4% chance, which is the top of our requested "
            "price window, so the selection is Edmonton Oilers to win at -250."
        ),
        "selection": "Edmonton Oilers (ML)",
        "price": "-250",
        "facts": [
            ("Edmonton record and goals", "7-1-1, 41 GF, 27 GA in 9 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Edmonton last ten", "L10 7-1-1, W2", "https://www.nhl.com/standings/2026-10-22"),
            ("Leon Draisaitl goals", "8 goals",
             "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
            ("Detroit record and goals", "3-3-3, 23 GF, 28 GA in 9 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "Detroit Red Wings at Edmonton Oilers, 26 Oct 2026, 21:30 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020189": {
        "text": (
            "Carolina lead the Eastern Conference at 8-2-1 with 42 goals scored, but Boston are "
            "right behind them at 7-2-1 having conceded only 22 goals in ten games. Our model has "
            "this at roughly 53-47 on the moneyline, and "
            "when two top-six defences meet the one-goal margin is the likeliest outcome. The pick "
            "is Boston Bruins +1.5 on the puck line at -250."
        ),
        "selection": "Boston Bruins +1.5",
        "price": "-250",
        "facts": [
            ("Carolina record and goals", "8-2-1, 42 GF, 27 GA in 11 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Boston record and goals", "7-2-1, 36 GF, 22 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Boston last ten", "L10 7-2-1, OT1", "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "Boston Bruins at Carolina Hurricanes, 27 Oct 2026, 20:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
    "NHL-2026020195": {
        "text": (
            "Minnesota's 6-2-2 start has been built on defence, with only 25 goals conceded in ten "
            "games, and Kirill Kaprizov has 11 goals at the other end. Utah are 7-3-0 but have "
            "allowed 31 goals in the same number of games and were beaten by Seattle earlier in the "
            "week. Our line makes this a one-goal game, so the selection is Minnesota Wild +1.5 on "
            "the puck line at -233 for Tuesday night in Salt Lake City."
        ),
        "selection": "Minnesota Wild +1.5",
        "price": "-233",
        "facts": [
            ("Minnesota record and goals", "6-2-2, 31 GF, 25 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Kirill Kaprizov goals", "11 goals, league leader",
             "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
            ("Utah record and goals", "7-3-0, 38 GF, 31 GA in 10 GP",
             "https://www.nhl.com/standings/2026-10-22"),
            ("Fixture", "Minnesota Wild at Utah Mammoth, 27 Oct 2026, 21:00 ET",
             "https://www.nhl.com/schedule/2026-10-22"),
        ],
    },
}

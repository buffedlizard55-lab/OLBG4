"""Verified source data for the session-8070bc18 line desk.

Every value in this module was read in this session from the official page named
next to it. Nothing is copied from another board's data file, and no value is
estimated: if a field was not on the official page it is left as None / "" and
the build script flags it.

Retrieved: 2026-10-21, between 07:10Z and 07:45Z, with the agent web-fetch tool
(direct curl to these domains is blocked by the sandbox egress allowlist).
"""

CAPTURED_AT = "2026-10-21T07:45Z"

SOURCES = [
    dict(
        id="nhl_schedule",
        name="NHL.com — League schedule, 20–26 October 2026",
        url="https://www.nhl.com/schedule",
        domain="nhl.com",
        used_for="All NHL fixtures (date, start time, home/away, broadcast) and the "
                 "20 October final scores, winning goalies and game-winning goals.",
        captured="2026-10-21T07:20Z",
    ),
    dict(
        id="nhl_standings",
        name="NHL.com — 2026-27 standings (captured 21 Oct, 03:10 EDT)",
        url="https://www.nhl.com/standings/2026-10-20/wildcard",
        domain="nhl.com",
        used_for="Games played, points percentage, goals for/against and home/away "
                 "records for all 32 clubs — the model's strength and scoring inputs.",
        captured="2026-10-21T07:32Z",
    ),
    dict(
        id="nba_schedule",
        name="NBA.com — 2026-27 schedule, week 1 (20–25 October 2026)",
        url="https://www.nba.com/schedule?date=2026-10-21",
        domain="nba.com",
        used_for="All NBA fixtures: date, tip-off time (ET), arena, city, game id, "
                 "and the 20 October final scores.",
        captured="2026-10-21T07:12Z",
    ),
    dict(
        id="nba_standings",
        name="NBA.com — 2026-27 regular-season standings",
        url="https://www.nba.com/standings",
        domain="nba.com",
        used_for="Early-season win/loss records used (with shrinkage) as the NBA "
                 "strength input.",
        captured="2026-10-21T07:40Z",
    ),
    dict(
        id="mlb_postseason",
        name="MLB.com — 2026 Postseason bracket and World Series schedule",
        url="https://www.mlb.com/postseason",
        domain="mlb.com",
        used_for="World Series games 1–4 (dates, first-pitch times ET, home/away, "
                 "game ids).",
        captured="2026-10-21T07:22Z",
    ),
    dict(
        id="mlb_standings",
        name="MLB.com — 2026 regular-season final standings (through 27 September)",
        url="https://www.mlb.com/standings",
        domain="mlb.com",
        used_for="Final 2026 win/loss records and run totals for Tampa Bay and "
                 "Milwaukee, the two World Series clubs.",
        captured="2026-10-21T07:44Z",
    ),
    dict(
        id="pdc_schedule",
        name="PDC — 2026 Machineseeker European Championship schedule confirmed",
        url="https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/",
        domain="pdc.tv",
        used_for="All 16 round-one ties, session dates and session windows "
                 "(1900-2300 CEST / 1800-2200 BST), venue (Westfalenhalle, Dortmund).",
        captured="2026-10-21T07:36Z",
    ),
    dict(
        id="ehf_matches",
        name="EHF Champions League Men 2026-27 — matches, results and schedule",
        url="https://ehfcl.eurohandball.com/men/2026-27/matches/",
        domain="ehfcl.eurohandball.com",
        used_for="Five round fixtures on 22 October (pairings, published throw-off "
                 "times, per-match detail URLs).",
        captured="2026-10-21T07:38Z",
    ),
    dict(
        id="wst_matches",
        name="World Snooker Tour — BetVictor Northern Ireland Open 2026 matches",
        url="https://www.wst.tv/matches",
        domain="wst.tv",
        used_for="Round 1 results (frames) on 18–19 October and the ten Round 2 "
                 "pairings scheduled for 21 October, with match-centre URLs.",
        captured="2026-10-21T07:34Z",
    ),
    dict(
        id="bwf_calendar",
        name="BWF — tournament calendar (YONEX French Open 2026, 20–25 October)",
        url="https://bwfbadminton.com/calendar/",
        domain="bwfbadminton.com",
        used_for="Coverage check only: confirmed the dates, venue and match-centre id "
                 "for the French Open. No match-level draw was captured, so no "
                 "badminton rows are published.",
        captured="2026-10-21T07:39Z",
    ),
]

# ---------------------------------------------------------------------------
# Strength inputs
# ---------------------------------------------------------------------------

# NHL.com standings, 21 Oct 2026 03:10 EDT. (gp, points_pct, goals_for, goals_against)
NHL = {
    "BOS": dict(gp=10, pct=0.750, gf=36, ga=22),
    "TBL": dict(gp=9,  pct=0.778, gf=31, ga=23),
    "OTT": dict(gp=9,  pct=0.667, gf=24, ga=23),
    "CAR": dict(gp=11, pct=0.773, gf=42, ga=27),
    "NYR": dict(gp=11, pct=0.682, gf=33, ga=24),
    "NYI": dict(gp=9,  pct=0.611, gf=27, ga=20),
    "FLA": dict(gp=9,  pct=0.667, gf=30, ga=25),
    "TOR": dict(gp=11, pct=0.545, gf=38, ga=35),
    "WSH": dict(gp=9,  pct=0.556, gf=30, ga=29),
    "NJD": dict(gp=9,  pct=0.556, gf=29, ga=30),
    "BUF": dict(gp=9,  pct=0.556, gf=27, ga=34),
    "MTL": dict(gp=9,  pct=0.556, gf=30, ga=34),
    "DET": dict(gp=9,  pct=0.500, gf=23, ga=28),
    "PIT": dict(gp=10, pct=0.350, gf=33, ga=38),
    "PHI": dict(gp=11, pct=0.318, gf=17, ga=36),
    "CBJ": dict(gp=8,  pct=0.375, gf=20, ga=29),
    "UTA": dict(gp=10, pct=0.700, gf=38, ga=31),
    "MIN": dict(gp=10, pct=0.700, gf=31, ga=25),
    "DAL": dict(gp=9,  pct=0.611, gf=23, ga=15),
    "VGK": dict(gp=11, pct=0.727, gf=44, ga=30),
    "EDM": dict(gp=9,  pct=0.833, gf=41, ga=27),
    "SEA": dict(gp=10, pct=0.650, gf=39, ga=34),
    "COL": dict(gp=10, pct=0.550, gf=41, ga=31),
    "SJS": dict(gp=10, pct=0.550, gf=27, ga=35),
    "WPG": dict(gp=9,  pct=0.556, gf=24, ga=26),
    "NSH": dict(gp=8,  pct=0.563, gf=23, ga=24),
    "STL": dict(gp=9,  pct=0.500, gf=29, ga=29),
    "ANA": dict(gp=9,  pct=0.444, gf=26, ga=29),
    "CHI": dict(gp=9,  pct=0.333, gf=21, ga=36),
    "VAN": dict(gp=11, pct=0.227, gf=33, ga=51),
    "LAK": dict(gp=7,  pct=0.286, gf=17, ga=27),
    "CGY": dict(gp=8,  pct=0.250, gf=17, ga=37),
}

# NBA.com standings, 2026-27, captured 21 Oct (w, l). Teams absent from this map
# had played no game at capture time and are treated as 0-0 by the model.
NBA = {
    "Detroit Pistons": (1, 0),
    "Philadelphia 76ers": (1, 0),
    "Oklahoma City Thunder": (1, 0),
    "New York Knicks": (0, 1),
    "Boston Celtics": (0, 1),
    "San Antonio Spurs": (0, 1),
}

# MLB.com final 2026 regular-season records (w, l) — only the World Series clubs.
MLB = {
    "Milwaukee Brewers": (103, 59),
    "Tampa Bay Rays": (98, 64),
}

# WST Northern Ireland Open 2026, round-one frame results (frames for, against).
# Only players whose round-one score is visible on the WST matches page are listed.
SNOOKER_R1 = {
    "Pang Junxu": (4, 2),
    "Liam Davies": (4, 2),
    "Sam Craigie": (4, 3),
    "Xu Si": (4, 0),
    "Elliot Slessor": (4, 0),
    "Jamie Jones": (4, 1),
    "Luca Brecel": (4, 1),
    "David Gilbert": (4, 1),
    "Scott Donaldson": (4, 0),
    "Daniel Wells": (4, 2),
    "Joe O'Connor": (4, 1),
    "Matthew Selt": (4, 3),
    "Mateusz Baranowski": (4, 3),
    "Thepchaiya Un-Nooh": (4, 2),
    "Jack Lisowski": (4, 1),
    "Louis Heathcote": (4, 2),
    "Anthony McGill": (4, 1),
    "Ricky Walden": (4, 1),
    "Wang Xinbo": (4, 2),
}

# ---------------------------------------------------------------------------
# Fixtures
# Each tuple: (date, time_label, home, away, venue, extra)
# "time_label" is copied verbatim from the official page where one is published.
# ---------------------------------------------------------------------------

NHL_TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CAR": "Carolina Hurricanes", "CBJ": "Columbus Blue Jackets",
    "CGY": "Calgary Flames", "CHI": "Chicago Blackhawks",
    "COL": "Colorado Avalanche", "DAL": "Dallas Stars", "DET": "Detroit Red Wings",
    "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild",
    "MTL": "Montréal Canadiens", "NJD": "New Jersey Devils",
    "NSH": "Nashville Predators", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators",
    "PHI": "Philadelphia Flyers", "PIT": "Pittsburgh Penguins",
    "SEA": "Seattle Kraken", "SJS": "San Jose Sharks",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning",
    "TOR": "Toronto Maple Leafs", "UTA": "Utah Mammoth",
    "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WPG": "Winnipeg Jets", "WSH": "Washington Capitals",
}

# (date, time ET, away, home, venue_note)
NHL_FIXTURES = [
    ("2026-10-21", "7:30 PM EDT", "PHI", "BUF", ""),
    ("2026-10-21", "7:30 PM EDT", "FLA", "OTT", ""),
    ("2026-10-22", "7:00 PM EDT", "NSH", "BOS", ""),
    ("2026-10-22", "7:00 PM EDT", "NYR", "TOR", ""),
    ("2026-10-22", "7:00 PM EDT", "SJS", "OTT", ""),
    ("2026-10-22", "7:00 PM EDT", "ANA", "NJD", ""),
    ("2026-10-22", "7:00 PM EDT", "FLA", "PIT", ""),
    ("2026-10-22", "7:30 PM EDT", "LAK", "NYI", ""),
    ("2026-10-22", "8:00 PM EDT", "VGK", "STL", ""),
    ("2026-10-22", "8:00 PM EDT", "WPG", "DAL", ""),
    ("2026-10-22", "9:00 PM EDT", "MIN", "CGY", ""),
    ("2026-10-22", "9:00 PM EDT", "CAR", "EDM", ""),
    ("2026-10-22", "10:00 PM EDT", "UTA", "SEA", ""),
    ("2026-10-22", "10:00 PM EDT", "DET", "VAN", ""),
    ("2026-10-23", "8:00 PM EDT", "MTL", "CHI", ""),
    ("2026-10-23", "9:00 PM EDT", "TBL", "COL", ""),
    ("2026-10-24", "1:00 PM EDT", "ANA", "PHI", ""),
    ("2026-10-24", "3:30 PM EDT", "LAK", "NJD", ""),
    ("2026-10-24", "7:00 PM EDT", "SJS", "BOS", ""),
    ("2026-10-24", "7:00 PM EDT", "NYR", "OTT", ""),
    ("2026-10-24", "7:00 PM EDT", "NSH", "PIT", ""),
    ("2026-10-24", "7:00 PM EDT", "BUF", "WSH", ""),
    ("2026-10-24", "7:00 PM EDT", "VGK", "CBJ", ""),
    ("2026-10-24", "7:00 PM EDT", "CAR", "STL", ""),
    ("2026-10-24", "7:00 PM EDT", "TOR", "EDM", ""),
    ("2026-10-24", "9:00 PM EDT", "TBL", "UTA", ""),
    ("2026-10-24", "10:00 PM EDT", "DET", "CGY", ""),
    ("2026-10-24", "10:00 PM EDT", "MIN", "SEA", ""),
    ("2026-10-25", "3:00 PM EDT", "FLA", "CHI", ""),
    ("2026-10-25", "6:00 PM EDT", "NYI", "DAL", ""),
    ("2026-10-25", "7:00 PM EDT", "MTL", "WPG", "NHL.com schedule page does not list the arena; left blank rather than inferred (game page not captured)."),
    ("2026-10-25", "8:00 PM EDT", "COL", "NSH", ""),
    ("2026-10-25", "10:00 PM EDT", "MIN", "VAN", ""),
]

# (date, time ET, away, home, venue)
NBA_FIXTURES = [
    ("2026-10-21", "7:00 PM ET", "Atlanta Hawks", "Orlando Magic", "Kia Center, Orlando, FL"),
    ("2026-10-21", "7:00 PM ET", "Milwaukee Bucks", "Washington Wizards", "Capital One Arena, Washington, DC"),
    ("2026-10-21", "7:30 PM ET", "Minnesota Timberwolves", "Miami Heat", "Kaseya Center, Miami, FL"),
    ("2026-10-21", "7:30 PM ET", "Charlotte Hornets", "Brooklyn Nets", "Barclays Center, Brooklyn, NY"),
    ("2026-10-21", "7:30 PM ET", "Chicago Bulls", "Toronto Raptors", "Scotiabank Arena, Toronto, ON"),
    ("2026-10-21", "8:00 PM ET", "Utah Jazz", "Memphis Grizzlies", "FedExForum, Memphis, TN"),
    ("2026-10-21", "8:00 PM ET", "Indiana Pacers", "New Orleans Pelicans", "Smoothie King Center, New Orleans, LA"),
    ("2026-10-21", "8:30 PM ET", "Dallas Mavericks", "Houston Rockets", "Toyota Center, Houston, TX"),
    ("2026-10-21", "10:00 PM ET", "Golden State Warriors", "Los Angeles Lakers", "Crypto.com Arena, Los Angeles, CA"),
    ("2026-10-21", "10:00 PM ET", "Phoenix Suns", "Portland Trail Blazers", "Moda Center, Portland, OR"),
    ("2026-10-21", "10:30 PM ET", "Sacramento Kings", "LA Clippers", "Intuit Dome, Inglewood, CA"),
    ("2026-10-22", "7:00 PM ET", "Cleveland Cavaliers", "Philadelphia 76ers", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-22", "9:30 PM ET", "Denver Nuggets", "Oklahoma City Thunder", "Paycom Center, Oklahoma City, OK"),
    ("2026-10-23", "4:00 PM ET", "Chicago Bulls", "Milwaukee Bucks", "Fiserv Forum, Milwaukee, WI"),
    ("2026-10-23", "7:00 PM ET", "New York Knicks", "Boston Celtics", "TD Garden, Boston, MA"),
    ("2026-10-23", "7:00 PM ET", "Atlanta Hawks", "Charlotte Hornets", "Spectrum Center, Charlotte, NC"),
    ("2026-10-23", "7:00 PM ET", "Dallas Mavericks", "Indiana Pacers", "Gainbridge Fieldhouse, Indianapolis, IN"),
    ("2026-10-23", "7:00 PM ET", "Minnesota Timberwolves", "Orlando Magic", "Kia Center, Orlando, FL"),
    ("2026-10-23", "7:00 PM ET", "Toronto Raptors", "Washington Wizards", "Capital One Arena, Washington, DC"),
    ("2026-10-23", "8:00 PM ET", "Detroit Pistons", "Miami Heat", "Kaseya Center, Miami, FL"),
    ("2026-10-23", "9:30 PM ET", "Houston Rockets", "San Antonio Spurs", "Moody Center, Austin, TX"),
    ("2026-10-23", "9:30 PM ET", "New Orleans Pelicans", "Utah Jazz", "Delta Center, Salt Lake City, UT"),
    ("2026-10-23", "10:00 PM ET", "Memphis Grizzlies", "Golden State Warriors", "Chase Center, San Francisco, CA"),
    ("2026-10-23", "10:00 PM ET", "LA Clippers", "Los Angeles Lakers", "Crypto.com Arena, Los Angeles, CA"),
    ("2026-10-23", "10:00 PM ET", "Portland Trail Blazers", "Sacramento Kings", "Golden 1 Center, Sacramento, CA"),
    ("2026-10-24", "6:00 PM ET", "Miami Heat", "Charlotte Hornets", "Spectrum Center, Charlotte, NC"),
    ("2026-10-24", "7:30 PM ET", "Brooklyn Nets", "Cleveland Cavaliers", "Rocket Arena, Cleveland, OH"),
    ("2026-10-24", "7:30 PM ET", "Milwaukee Bucks", "Philadelphia 76ers", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-24", "8:00 PM ET", "Washington Wizards", "Chicago Bulls", "United Center, Chicago, IL"),
    ("2026-10-24", "8:00 PM ET", "San Antonio Spurs", "Dallas Mavericks", "American Airlines Center, Dallas, TX"),
    ("2026-10-24", "8:30 PM ET", "Houston Rockets", "Atlanta Hawks", "State Farm Arena, Atlanta, GA"),
    ("2026-10-24", "9:00 PM ET", "New Orleans Pelicans", "Denver Nuggets", "Ball Arena, Denver, CO"),
    ("2026-10-24", "10:00 PM ET", "Golden State Warriors", "Phoenix Suns", "Mortgage Matchup Center, Phoenix, AZ"),
    ("2026-10-25", "5:00 PM ET", "Los Angeles Lakers", "Utah Jazz", "Delta Center, Salt Lake City, UT"),
    ("2026-10-25", "6:00 PM ET", "Indiana Pacers", "Brooklyn Nets", "Barclays Center, Brooklyn, NY"),
    ("2026-10-25", "7:00 PM ET", "Orlando Magic", "New York Knicks", "Madison Square Garden, New York, NY"),
    ("2026-10-25", "7:00 PM ET", "Toronto Raptors", "Minnesota Timberwolves", "Target Center, Minneapolis, MN"),
    ("2026-10-25", "7:00 PM ET", "LA Clippers", "Oklahoma City Thunder", "Paycom Center, Oklahoma City, OK"),
    ("2026-10-25", "7:30 PM ET", "Detroit Pistons", "Philadelphia 76ers", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-25", "9:00 PM ET", "Memphis Grizzlies", "Sacramento Kings", "Golden 1 Center, Sacramento, CA"),
]

# MLB World Series: (date, time ET, away, home, game id, game number)
MLB_FIXTURES = [
    ("2026-10-23", "8:00 PM ET", "Tampa Bay Rays", "Milwaukee Brewers", "849805", "Game 1"),
    ("2026-10-24", "8:00 PM ET", "Tampa Bay Rays", "Milwaukee Brewers", "849802", "Game 2"),
    ("2026-10-26", "8:00 PM ET", "Milwaukee Brewers", "Tampa Bay Rays", "849804", "Game 3"),
    ("2026-10-27", "8:00 PM ET", "Milwaukee Brewers", "Tampa Bay Rays", "849803", "Game 4"),
]

PDC_FIXTURES = [
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Luke Woodhouse", "Dirk van Duijvenbode"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Danny Noppert", "Stephen Bunting"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Niels Zonneveld", "Cameron Menzies"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Gerwyn Price", "Rob Cross"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "James Wade", "Damon Heta"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Luke Humphries", "Ryan Searle"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Gian van Veen", "Andrew Gilding"),
    ("2026-10-22", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Ross Smith", "Karel Sedlacek"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Ryan Joyce", "Jermaine Wattimena"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Krzysztof Ratajski", "Dave Chisnall"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Nathan Aspinall", "Cristo Reyes"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Jonny Clayton", "Niko Springer"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Luke Littler", "William O'Connor"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Wessel Nijman", "Martin Schindler"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Kevin Doets", "Michael van Gerwen"),
    ("2026-10-23", "Session 19:00-23:00 CEST (18:00-22:00 BST)", "Josh Rock", "Chris Dobey"),
]

# EHF Champions League, 22 October 2026 (published throw-off times, timezone not
# stated on the page; kept verbatim).
EHF_FIXTURES = [
    ("2026-10-22", "18:45", "OTP Bank - PICK Szeged", "GOG", "202711020101043"),
    ("2026-10-22", "18:45", "MT Melsungen", "Orlen Wisla Plock", "202711020101019"),
    ("2026-10-22", "20:45", "Barça", "Montpellier Handball", "202711020101049"),
    ("2026-10-22", "20:45", "Sporting Clube de Portugal", "IFK Kristianstad", "202711020101041"),
    ("2026-10-22", "20:45", "Kolstad Håndball", "SC Magdeburg", "202711020101064"),
]

# WST Northern Ireland Open round 2, 21 October 2026. The WST list page renders
# clock times in the reader's locale, so no start time is published here.
WST_FIXTURES = [
    ("2026-10-21", "Pang Junxu", "Liam Davies", "round two", "72c7cfbc-8aa3-454f-94ac-7d89e2659728"),
    ("2026-10-21", "Cheung Ka Wai", "Stuart Bingham", "round two", "3d53c559-9bd7-4bc4-8e1d-a6c2b7459528"),
    ("2026-10-21", "John Higgins", "Jak Jones", "Match 45", "eba55492-fba6-4a53-90be-a04b3560ae65"),
    ("2026-10-21", "Daniel Wells", "Ryan Day", "round two", "e9c15ae6-b9b8-4cea-a83a-49c58eb14046"),
    ("2026-10-21", "Sam Craigie", "Xu Si", "Match 38", "afb42fc9-9654-479e-997e-d33d8a1a6888"),
    ("2026-10-21", "Zhang Anda", "Mark Williams", "Match 43", "480e5abf-5766-44ad-9918-f822ceefd4a5"),
    ("2026-10-21", "Michael Holt", "Jordan Brown", "Match 47", "e58a00e5-e6a7-479b-98d0-5c7867af28a8"),
    ("2026-10-21", "Gao Yang", "David Gilbert", "Match 41", "4fb27af0-7db4-4ec2-b93b-137de3f66135"),
    ("2026-10-21", "Noppon Saengkham", "Scott Donaldson", "Match 48", "3a24076e-455c-497b-abd5-976e194abc5e"),
    ("2026-10-21", "Elliot Slessor", "Jamie Jones", "Match 39", "f6536f1f-6c2d-47cd-b802-a81e6f04e4cc"),
]

# Verified player-level facts, all from the NHL.com schedule page for 20 October.
# Keys are the club the player belongs to.
NHL_PLAYER_FACTS = {
    "SJS": "San Jose beat Montréal 4-3 in overtime on 20 October; M. Celebrini scored the game-winning goal and A. Nedeljkovic was the winning goalie.",
    "NJD": "New Jersey beat Colorado 4-3 on 20 October; J. Boqvist scored the game-winning goal and J. Allen was the winning goalie.",
    "LAK": "Los Angeles won 5-2 at Washington on 20 October; E. Gustafsson scored the game-winning goal and D. Kuemper was the winning goalie.",
    "TOR": "Toronto won 6-2 at Columbus on 20 October; A. Matthews scored the game-winning goal and A. Stolarz was the winning goalie.",
    "STL": "St. Louis beat Winnipeg 2-1 on 20 October; P. Broberg scored the game-winning goal and J. Hofer was the winning goalie.",
    "DAL": "Dallas beat Boston 3-2 in overtime on 20 October; M. Rantanen scored the game-winning goal and J. Oettinger was the winning goalie.",
    "EDM": "Edmonton beat Minnesota 4-3 in overtime on 20 October; E. Bouchard scored the game-winning goal and D. Levi was the winning goalie.",
    "SEA": "Seattle beat Detroit 4-3 in a shootout on 20 October; P. Grubauer was the winning goalie.",
    "CAR": "Carolina won 6-3 at Vancouver on 20 October; N. Deslauriers scored the game-winning goal and P. Kochetkov was the winning goalie.",
    "TBL": "Tampa Bay won 6-2 at Vegas on 20 October; A. Cirelli scored the game-winning goal and A. Vasilevskiy was the winning goalie.",
    "NYI": "The Islanders beat Anaheim 3-2 on 20 October; S. Holmstrom scored the game-winning goal and I. Sorokin was the winning goalie.",
}

# Coverage decision per OLBG sport. "excluded" = the brief removes it.
# "not captured" = in scope, but no match-level official page was captured in this
# pass; these sports publish no rows rather than unverified rows.
COVERAGE = [
    dict(sport="Ice Hockey", status="covered", fixtures=33,
         source="NHL.com schedule + standings",
         note="All 33 NHL games from 21 to 25 October 2026, with model lines, picks and confidence."),
    dict(sport="Basketball", status="covered", fixtures=40,
         source="NBA.com schedule + standings",
         note="All 40 NBA games from 21 to 25 October 2026. Early-season records are thin, so confidence is capped."),
    dict(sport="Baseball", status="covered", fixtures=4,
         source="MLB.com postseason + final standings",
         note="World Series games 1-4 only; the rest of the postseason bracket is complete."),
    dict(sport="Darts", status="covered", fixtures=16,
         source="PDC European Championship schedule",
         note="All 16 round-one ties, 22-23 October. No verified ranking/form feed was captured, so lines are prior-only."),
    dict(sport="Handball", status="covered", fixtures=5,
         source="EHF Champions League schedule",
         note="Five EHF Champions League round fixtures on 22 October. No verified strength input captured; lines prior-only."),
    dict(sport="Snooker", status="covered", fixtures=10,
         source="World Snooker Tour match list",
         note="Ten Northern Ireland Open round-two ties dated 21 October. Only event frame scores were available as form."),
    dict(sport="Tennis", status="not captured", fixtures=0,
         source="ATP Tour scores page (live page read, no tournament-level draw captured)",
         note="The ATP scores page returned live match state without a citable tournament draw. No rows published rather than guess opponents or start times."),
    dict(sport="Cricket", status="not captured", fixtures=0,
         source="No official board page captured",
         note="Fixture lists seen were secondary aggregators. Publishing them would breach the official-source rule, so cricket is listed as a gap, not a row."),
    dict(sport="Rugby Union", status="not captured", fixtures=0,
         source="None captured",
         note="No governing-body fixture page was captured inside this session's tool window."),
    dict(sport="Rugby League", status="not captured", fixtures=0,
         source="None captured",
         note="Rugby League World Cup fixtures were visible only through secondary outlets that disagree on kick-off times; no official page captured, so no rows."),
    dict(sport="Volleyball", status="not captured", fixtures=0, source="None captured",
         note="No official competition schedule captured this pass."),
    dict(sport="Badminton", status="tournament only", fixtures=0,
         source="BWF calendar (French Open 2026, 20-25 October, Arena Grand Paris)",
         note="Tournament verified, but the match-level draw was not captured, so no match rows are published."),
    dict(sport="Table Tennis", status="not captured", fixtures=0, source="None captured",
         note="No official WTT event page captured this pass."),
    dict(sport="Golf", status="out of match scope", fixtures=0, source="—",
         note="Golf events are stroke-play tournaments, not two-sided matches, so no match-winner market is originated."),
    dict(sport="Greyhounds", status="out of match scope", fixtures=0, source="—",
         note="Racing product. Each race is a field event; no head-to-head match market is originated here."),
    dict(sport="Motor Racing", status="out of match scope", fixtures=0, source="—",
         note="Field event (grand prix), not a two-sided match. Not included in the match table."),
    dict(sport="Aussie Rules", status="off-season", fixtures=0,
         source="—",
         note="AFL club season is not running in the 21-27 October 2026 window; no official fixture was captured."),
    dict(sport="Esports", status="not captured", fixtures=0, source="None captured",
         note="No official publisher/tournament schedule captured this pass."),
    dict(sport="Soccer", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="Boxing", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="UFC / MMA", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="American Football", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="Hurling", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="Horse Racing", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="Cycling", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
    dict(sport="Specials", status="excluded", fixtures=0, source="—", note="Excluded by the brief."),
]

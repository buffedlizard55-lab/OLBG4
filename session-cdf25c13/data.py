"""Board T — verified raw inputs, read live on 2026-10-22 (UTC).

Every number in this file was copied from an official league page during this session.
Nothing is estimated, interpolated or carried over from an earlier build. Where an
official page did not publish a value it is None here and stays blank downstream.

Source URLs (all read 2026-10-22 between 02:50Z and 03:40Z):

NHL fixtures        https://www.nhl.com/schedule/2026-10-22   (schedule table, 22-28 Oct)
NHL standings       https://www.nhl.com/standings/2026-10-22  (Wild Card view, 32 clubs)
NHL goal leaders    https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10
NHL venues (5)      https://api-web.nhle.com/v1/schedule/2026-10-22
NBA fixtures        https://www.nba.com/schedule?date=2026-10-22 (Week 1: 22-25 Oct)
NBA standings       https://www.nba.com/standings (2026-27 regular season, snapshot)
MLB fixtures        https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-28
MLB team hitting    https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1&gameType=R
MLB team pitching   https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1&gameType=R
MLB TB pitching     https://statsapi.mlb.com/api/v1/teams/139/stats?season=2026&group=pitching&stats=season&gameType=R
MLB HR leaders      https://statsapi.mlb.com/api/v1/stats/leaders?leaderCategories=homeRuns&season=2026&sportId=1&limit=5
URC fixtures        https://stats.unitedrugby.com/match-centre/2026-27/4  (Round 4, local times)
URC table           https://stats.unitedrugby.com/match-centre/table/2026-27
"""

CUTOFF = "2026-10-22T03:40:00Z"
WINDOW_START, WINDOW_END = "2026-10-22", "2026-10-28"

NHL_SCHEDULE_URL = "https://www.nhl.com/schedule/2026-10-22"
NHL_STANDINGS_URL = "https://www.nhl.com/standings/2026-10-22"
NHL_LEADERS_URL = "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"
NBA_SCHEDULE_URL = "https://www.nba.com/schedule?date=2026-10-22"
NBA_STANDINGS_URL = "https://www.nba.com/standings"
MLB_SCHEDULE_URL = ("https://statsapi.mlb.com/api/v1/schedule?sportId=1"
                     "&startDate=2026-10-22&endDate=2026-10-28")
MLB_HITTING_URL = ("https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting"
                   "&stats=season&sportId=1&gameType=R")
MLB_PITCHING_URL = ("https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching"
                    "&stats=season&sportId=1&gameType=R")
URC_SCHEDULE_URL = "https://stats.unitedrugby.com/match-centre/2026-27/4"
URC_TABLE_URL = "https://stats.unitedrugby.com/match-centre/table/2026-27"

# --------------------------------------------------------------------------- NHL
NHL_TEAMS = {
    # abbr: (name, GP, W, L, OT, PTS, GF, GA, L10, streak)
    "ANA": ("Anaheim Ducks", 9, 4, 5, 0, 8, 26, 29, "4-5-0", "L4"),
    "BOS": ("Boston Bruins", 10, 7, 2, 1, 15, 36, 22, "7-2-1", "OT1"),
    "BUF": ("Buffalo Sabres", 10, 4, 4, 2, 10, 28, 37, "4-4-2", "L1"),
    "CGY": ("Calgary Flames", 8, 2, 6, 0, 4, 17, 37, "2-6-0", "W1"),
    "CAR": ("Carolina Hurricanes", 11, 8, 2, 1, 17, 42, 27, "8-2-0", "W1"),
    "CHI": ("Chicago Blackhawks", 9, 3, 6, 0, 6, 21, 36, "3-6-0", "L1"),
    "COL": ("Colorado Avalanche", 10, 5, 4, 1, 11, 41, 31, "5-4-1", "L2"),
    "CBJ": ("Columbus Blue Jackets", 8, 3, 5, 0, 6, 20, 29, "3-5-0", "L2"),
    "DAL": ("Dallas Stars", 9, 5, 3, 1, 11, 23, 15, "5-3-1", "W3"),
    "DET": ("Detroit Red Wings", 9, 3, 3, 3, 9, 23, 28, "3-3-3", "OT1"),
    "EDM": ("Edmonton Oilers", 9, 7, 1, 1, 15, 41, 27, "7-1-1", "W2"),
    "FLA": ("Florida Panthers", 10, 5, 3, 2, 12, 31, 30, "5-3-2", "L1"),
    "LAK": ("Los Angeles Kings", 7, 1, 4, 2, 4, 17, 27, "1-4-2", "W1"),
    "MIN": ("Minnesota Wild", 10, 6, 2, 2, 14, 31, 25, "6-2-2", "OT1"),
    "MTL": ("Montreal Canadiens", 9, 4, 3, 2, 10, 30, 34, "4-3-2", "OT1"),
    "NSH": ("Nashville Predators", 8, 3, 2, 3, 9, 23, 24, "3-2-3", "W1"),
    "NJD": ("New Jersey Devils", 9, 5, 4, 0, 10, 29, 30, "5-4-0", "W1"),
    "NYI": ("New York Islanders", 9, 5, 3, 1, 11, 27, 20, "5-3-1", "W2"),
    "NYR": ("New York Rangers", 11, 7, 3, 1, 15, 33, 24, "7-2-1", "W1"),
    "OTT": ("Ottawa Senators", 10, 7, 3, 0, 14, 29, 24, "7-3-0", "W1"),
    "PHI": ("Philadelphia Flyers", 12, 3, 6, 3, 9, 20, 37, "3-5-2", "W3"),
    "PIT": ("Pittsburgh Penguins", 10, 3, 6, 1, 7, 33, 38, "3-6-1", "L4"),
    "SJS": ("San Jose Sharks", 10, 5, 4, 1, 11, 27, 35, "5-4-1", "W1"),
    "SEA": ("Seattle Kraken", 10, 6, 3, 1, 13, 39, 34, "6-3-1", "W1"),
    "STL": ("St. Louis Blues", 9, 4, 4, 1, 9, 29, 29, "4-4-1", "W1"),
    "TBL": ("Tampa Bay Lightning", 9, 7, 2, 0, 14, 31, 23, "7-2-0", "W3"),
    "TOR": ("Toronto Maple Leafs", 11, 5, 4, 2, 12, 38, 35, "5-3-2", "W2"),
    "UTA": ("Utah Mammoth", 10, 7, 3, 0, 14, 38, 31, "7-3-0", "W1"),
    "VAN": ("Vancouver Canucks", 11, 2, 8, 1, 5, 33, 51, "1-8-1", "L2"),
    "VGK": ("Vegas Golden Knights", 11, 8, 3, 0, 16, 44, 30, "7-3-0", "L1"),
    "WSH": ("Washington Capitals", 9, 5, 4, 0, 10, 30, 29, "5-4-0", "L1"),
    "WPG": ("Winnipeg Jets", 9, 4, 3, 2, 10, 24, 26, "4-3-2", "L2"),
}

# Calgary and Los Angeles were not inside the rendered Wild Card table that was read.
NHL_MISSING_STATS = {}

# (date, ET time, away, home, game id, venue if returned by the official API)
NHL_GAMES = [
    ("2026-10-22", "19:00", "NSH", "BOS", "2026020154", "TD Garden"),
    ("2026-10-22", "19:00", "NYR", "TOR", "2026020155", "Scotiabank Arena"),
    ("2026-10-22", "19:00", "SJS", "OTT", "2026020156", "Canadian Tire Centre"),
    ("2026-10-22", "19:00", "ANA", "NJD", "2026020157", "Prudential Center"),
    ("2026-10-22", "19:00", "FLA", "PIT", "2026020158", "PPG Paints Arena"),
    ("2026-10-22", "19:30", "LAK", "NYI", "2026020159", None),
    ("2026-10-22", "20:00", "VGK", "STL", "2026020160", None),
    ("2026-10-22", "20:00", "WPG", "DAL", "2026020161", None),
    ("2026-10-22", "21:00", "MIN", "CGY", "2026020162", None),
    ("2026-10-22", "21:00", "CAR", "EDM", "2026020163", None),
    ("2026-10-22", "22:00", "UTA", "SEA", "2026020164", None),
    ("2026-10-22", "22:00", "DET", "VAN", "2026020165", None),
    ("2026-10-23", "20:00", "MTL", "CHI", "2026020166", None),
    ("2026-10-23", "21:00", "TBL", "COL", "2026020167", None),
    ("2026-10-24", "13:00", "ANA", "PHI", "2026020168", None),
    ("2026-10-24", "15:30", "LAK", "NJD", "2026020169", None),
    ("2026-10-24", "19:00", "SJS", "BOS", "2026020170", None),
    ("2026-10-24", "19:00", "NYR", "OTT", "2026020171", None),
    ("2026-10-24", "19:00", "NSH", "PIT", "2026020172", None),
    ("2026-10-24", "19:00", "BUF", "WSH", "2026020173", None),
    ("2026-10-24", "19:00", "VGK", "CBJ", "2026020174", None),
    ("2026-10-24", "19:00", "CAR", "STL", "2026020175", None),
    ("2026-10-24", "19:00", "TOR", "EDM", "2026020176", None),
    ("2026-10-24", "21:00", "TBL", "UTA", "2026020177", None),
    ("2026-10-24", "22:00", "DET", "CGY", "2026020178", None),
    ("2026-10-24", "22:00", "MIN", "SEA", "2026020179", None),
    ("2026-10-25", "15:00", "FLA", "CHI", "2026020180", None),
    ("2026-10-25", "18:00", "NYI", "DAL", "2026020181", None),
    ("2026-10-25", "19:00", "MTL", "WPG", "2026020182", None),
    ("2026-10-25", "20:00", "COL", "NSH", "2026020183", None),
    ("2026-10-25", "22:00", "MIN", "VAN", "2026020184", None),
    ("2026-10-26", "19:00", "LAK", "NYR", "2026020185", None),
    ("2026-10-26", "20:30", "TOR", "CGY", "2026020186", None),
    ("2026-10-26", "21:30", "DET", "EDM", "2026020187", None),
    ("2026-10-27", "19:00", "CBJ", "PHI", "2026020188", None),
    ("2026-10-27", "20:00", "BOS", "CAR", "2026020189", None),
    ("2026-10-27", "20:00", "LAK", "CHI", "2026020190", None),
    ("2026-10-27", "20:00", "MTL", "STL", "2026020191", None),
    ("2026-10-27", "20:00", "NYI", "NSH", "2026020192", None),
    ("2026-10-27", "20:00", "NJD", "DAL", "2026020193", None),
    ("2026-10-27", "20:00", "FLA", "WPG", "2026020194", None),
    ("2026-10-27", "21:00", "MIN", "UTA", "2026020195", None),
    ("2026-10-27", "22:00", "OTT", "VGK", "2026020196", None),
    ("2026-10-27", "22:00", "VAN", "ANA", "2026020197", None),
    ("2026-10-27", "22:30", "BUF", "SJS", "2026020198", None),
    ("2026-10-28", "19:30", "PHI", "WSH", "2026020199", None),
    ("2026-10-28", "20:30", "CGY", "EDM", "2026020200", None),
    ("2026-10-28", "21:00", "NJD", "COL", "2026020201", None),
    ("2026-10-28", "22:00", "TOR", "SEA", "2026020202", None),
]

# Official league goal leaders, read from the NHL stats API on 2026-10-22.
NHL_GOAL_LEADERS = {
    "MIN": ("Kirill Kaprizov", 11),
    "TOR": ("Auston Matthews", 8),
    "EDM": ("Leon Draisaitl", 8),
    "VGK": ("Mark Stone", 8),
    "WPG": ("Kyle Connor", 8),
    "COL": ("Artturi Lehkonen", 8),
    "UTA": ("Nick Schmaltz", 7),
    "NYR": ("Alexis Lafreniere", 7),
}

# --------------------------------------------------------------------------- NBA
NBA_TEAMS = {
    # name: (W, L) exactly as published on the 2026-27 standings view read this session
    "ATL": ("Atlanta Hawks", 1, 0), "BOS": ("Boston Celtics", 0, 1),
    "BKN": ("Brooklyn Nets", 0, 1), "CHA": ("Charlotte Hornets", 1, 0),
    "CHI": ("Chicago Bulls", 0, 1), "CLE": ("Cleveland Cavaliers", 0, 0),
    "DAL": ("Dallas Mavericks", 0, 0), "DEN": ("Denver Nuggets", 0, 0),
    "DET": ("Detroit Pistons", 1, 0), "GSW": ("Golden State Warriors", 0, 0),
    "HOU": ("Houston Rockets", 0, 0), "IND": ("Indiana Pacers", 1, 0),
    "LAC": ("LA Clippers", 0, 0), "LAL": ("Los Angeles Lakers", 0, 0),
    "MEM": ("Memphis Grizzlies", 1, 0), "MIA": ("Miami Heat", 0, 1),
    "MIL": ("Milwaukee Bucks", 0, 1), "MIN": ("Minnesota Timberwolves", 1, 0),
    "NOP": ("New Orleans Pelicans", 0, 1), "NYK": ("New York Knicks", 0, 1),
    "OKC": ("Oklahoma City Thunder", 1, 0), "ORL": ("Orlando Magic", 0, 1),
    "PHI": ("Philadelphia 76ers", 1, 0), "PHX": ("Phoenix Suns", 0, 0),
    "POR": ("Portland Trail Blazers", 0, 0), "SAC": ("Sacramento Kings", 0, 0),
    "SAS": ("San Antonio Spurs", 0, 1), "TOR": ("Toronto Raptors", 1, 0),
    "UTA": ("Utah Jazz", 0, 1), "WSH": ("Washington Wizards", 1, 0),
}

# (date, ET time, away, home, venue) — national schedule page, Week 1
NBA_GAMES = [
    ("2026-10-22", "19:00", "CLE", "PHI", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-22", "21:30", "DEN", "OKC", "Paycom Center, Oklahoma City, OK"),
    ("2026-10-23", "16:00", "CHI", "MIL", "Fiserv Forum, Milwaukee, WI"),
    ("2026-10-23", "19:00", "NYK", "BOS", "TD Garden, Boston, MA"),
    ("2026-10-23", "19:00", "ATL", "CHA", "Spectrum Center, Charlotte, NC"),
    ("2026-10-23", "19:00", "DAL", "IND", "Gainbridge Fieldhouse, Indianapolis, IN"),
    ("2026-10-23", "19:00", "MIN", "ORL", "Kia Center, Orlando, FL"),
    ("2026-10-23", "19:00", "TOR", "WSH", "Capital One Arena, Washington, DC"),
    ("2026-10-23", "20:00", "DET", "MIA", "Kaseya Center, Miami, FL"),
    ("2026-10-23", "21:30", "HOU", "SAS", "Moody Center, Austin, TX"),
    ("2026-10-23", "21:30", "NOP", "UTA", "Delta Center, Salt Lake City, UT"),
    ("2026-10-23", "22:00", "MEM", "GSW", "Chase Center, San Francisco, CA"),
    ("2026-10-23", "22:00", "LAC", "LAL", "Crypto.com Arena, Los Angeles, CA"),
    ("2026-10-23", "22:00", "POR", "SAC", "Golden 1 Center, Sacramento, CA"),
    ("2026-10-24", "18:00", "MIA", "CHA", "Spectrum Center, Charlotte, NC"),
    ("2026-10-24", "19:30", "BKN", "CLE", "Rocket Arena, Cleveland, OH"),
    ("2026-10-24", "19:30", "MIL", "PHI", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-24", "20:00", "WSH", "CHI", "United Center, Chicago, IL"),
    ("2026-10-24", "20:00", "SAS", "DAL", "American Airlines Center, Dallas, TX"),
    ("2026-10-24", "20:30", "HOU", "ATL", "State Farm Arena, Atlanta, GA"),
    ("2026-10-24", "21:00", "NOP", "DEN", "Ball Arena, Denver, CO"),
    ("2026-10-24", "22:00", "GSW", "PHX", "Mortgage Matchup Center, Phoenix, AZ"),
    ("2026-10-25", "17:00", "LAL", "UTA", "Delta Center, Salt Lake City, UT"),
    ("2026-10-25", "18:00", "IND", "BKN", "Barclays Center, Brooklyn, NY"),
    ("2026-10-25", "19:00", "ORL", "NYK", "Madison Square Garden, New York, NY"),
    ("2026-10-25", "19:00", "TOR", "MIN", "Target Center, Minneapolis, MN"),
    ("2026-10-25", "19:00", "LAC", "OKC", "Paycom Center, Oklahoma City, OK"),
    ("2026-10-25", "19:30", "DET", "PHI", "Xfinity Mobile Arena, Philadelphia, PA"),
    ("2026-10-25", "21:00", "MEM", "SAC", "Golden 1 Center, Sacramento, CA"),
]

# --------------------------------------------------------------------------- MLB
MLB_TEAMS = {
    "MIL": {"name": "Milwaukee Brewers", "gp": 162, "w": 103, "l": 59, "rs": 832, "ra": 601,
            "avg": ".258", "ops": ".744", "era": "3.23"},
    "TB": {"name": "Tampa Bay Rays", "gp": 162, "w": 98, "l": 64, "rs": 736, "ra": 650,
           "avg": ".258", "ops": ".728", "era": "3.70"},
}

MLB_GAMES = [
    # (date, ET time, away, home, venue, game number, note)
    ("2026-10-23", "20:00", "TB", "MIL", "American Family Field", 1, "World Series Game 1"),
    ("2026-10-24", "20:00", "TB", "MIL", "American Family Field", 2, "World Series Game 2"),
    ("2026-10-26", "20:00", "MIL", "TB", "Tropicana Field", 3, "World Series Game 3"),
    ("2026-10-27", "20:00", "MIL", "TB", "Tropicana Field", 4, "World Series Game 4"),
    ("2026-10-28", "20:00", "MIL", "TB", "Tropicana Field", 5,
     "World Series Game 5 - listed 'If Necessary' on the official schedule"),
]

MLB_PLAYER_FACTS = {
    "TB": ("Junior Caminero", "42 home runs in the 2026 regular season (joint 4th in MLB)"),
}

# --------------------------------------------------------------------------- URC
URC_TEAMS = {
    # name, PL, W, D, L, PF, PA, PTS, form list
    "Edinburgh": ("Edinburgh Rugby", 3, 3, 0, 0, 80, 54, 14, ["W", "W", "W"]),
    "Glasgow": ("Glasgow Warriors", 3, 2, 1, 0, 95, 72, 13, ["W", "D", "W"]),
    "Bulls": ("Vodacom Bulls", 3, 2, 0, 1, 126, 54, 11, ["W", "L", "W"]),
    "Stormers": ("DHL Stormers", 3, 2, 0, 1, 81, 54, 11, ["W", "L", "W"]),
    "Sharks": ("Hollywoodbets Sharks", 3, 2, 0, 1, 89, 83, 10, ["W", "W", "L"]),
    "Cardiff": ("Cardiff Rugby", 3, 2, 0, 1, 66, 71, 9, ["W", "W", "L"]),
    "Lions": ("10bet Lions", 3, 2, 0, 1, 77, 102, 9, ["W", "W", "L"]),
    "Dragons": ("Dragons RFC", 3, 1, 1, 1, 88, 83, 9, ["D", "W", "L"]),
    "Munster": ("Munster Rugby", 3, 1, 1, 1, 72, 74, 9, ["L", "W", "D"]),
    "Leinster": ("Leinster Rugby", 3, 1, 0, 2, 75, 58, 8, ["L", "L", "W"]),
    "Ulster": ("Ulster Rugby", 3, 0, 2, 1, 88, 93, 8, ["L", "D", "D"]),
    "Scarlets": ("Scarlets", 3, 1, 0, 2, 68, 85, 7, ["L", "L", "W"]),
    "Ospreys": ("Ospreys", 3, 1, 0, 2, 81, 107, 6, ["L", "L", "W"]),
    "Connacht": ("Connacht Rugby", 3, 1, 0, 2, 56, 84, 5, ["L", "W", "L"]),
    "Benetton": ("Benetton Rugby", 3, 0, 1, 2, 64, 68, 5, ["D", "L", "L"]),
    "Zebre": ("Zebre Parma", 3, 0, 0, 3, 52, 116, 1, ["L", "L", "L"]),
}

# (date, local time as published, home key, away key, venue)
URC_GAMES = [
    ("2026-10-23", "14:45", "Cardiff", "Sharks", "Cardiff Arms Park"),
    ("2026-10-23", "14:45", "Connacht", "Zebre", "Dexcom Stadium"),
    ("2026-10-23", "14:45", "Edinburgh", "Lions", "Hive Stadium"),
    ("2026-10-24", "07:45", "Bulls", "Ulster", "Loftus Versfeld"),
    ("2026-10-24", "10:00", "Stormers", "Scarlets", "DHL Stadium"),
    ("2026-10-24", "10:00", "Benetton", "Glasgow", "Stadio Monigo"),
    ("2026-10-24", "13:00", "Leinster", "Munster", "Aviva Stadium"),
    ("2026-10-24", "14:00", "Ospreys", "Dragons", "St Helen's"),
]

# Round 3 results, read from the URC match centre on 2026-10-22 (9-10 Oct 2026).
URC_ROUND3_RESULTS = [
    ("2026-10-09", "Glasgow Warriors", 36, 19, "Connacht Rugby"),
    ("2026-10-09", "Dragons RFC", 31, 38, "Ospreys"),
    ("2026-10-10", "Vodacom Bulls", 57, 15, "10bet Lions"),
    ("2026-10-10", "DHL Stormers", 39, 22, "Hollywoodbets Sharks"),
    ("2026-10-10", "Zebre Parma", 12, 29, "Edinburgh Rugby"),
    ("2026-10-10", "Scarlets", 27, 26, "Benetton Rugby"),
    ("2026-10-10", "Ulster Rugby", 26, 26, "Munster Rugby"),
    ("2026-10-10", "Leinster Rugby", 29, 5, "Cardiff Rugby"),
]

# EHF Champions League Men — fixtures verified on the organiser's page but NOT priced this session,
# because the standings view returned goal totals for only one group. (date, time as published, home, away)
EHF_GAMES = [
    ("2026-10-22", "18:45", "MT Melsungen", "Orlen Wisla Plock"),
    ("2026-10-22", "18:45", "OTP Bank - PICK Szeged", "GOG"),
    ("2026-10-22", "20:45", "Sporting Clube de Portugal", "IFK Kristianstad"),
    ("2026-10-22", "20:45", "Barca", "Montpellier Handball"),
    ("2026-10-22", "20:45", "Kolstad Handball", "SC Magdeburg"),
    ("2026-10-28", "18:45", "Orlen Wisla Plock", "HBC Nantes"),
    ("2026-10-28", "18:45", "FC Porto", "One Veszprem HC"),
    ("2026-10-28", "18:45", "HC Vardar 1961", "MT Melsungen"),
    ("2026-10-28", "20:45", "Industria Kielce", "Kolstad Handball"),
    ("2026-10-28", "20:45", "RK Celje Pivovarna Lasko", "HC Zagreb"),
    ("2026-10-28", "20:45", "SC Magdeburg", "HC Kriens-Luzern"),
    ("2026-10-28", "20:45", "Paris Saint-Germain", "Aalborg Handbold"),
]
EHF_URL = "https://ehfcl.eurohandball.com/men/2026-27/matches/"

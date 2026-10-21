#!/usr/bin/env python3
"""Transcribe the official-source tables captured in this session into data/session-74f9613e/inputs.json.

Every tuple below is copied from the official page named in its block comment.
Nothing is estimated: if a value was not on the official page it is left out.

Run: python3 scripts/prepare_inputs.py
"""
import json
import os
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "session-74f9613e", "inputs.json")

# ---------------------------------------------------------------------------
# NHL - source S10 (https://www.nhl.com/standings/2026-10-20/wildcard)
# Columns: code, GP, W, L, OT, PTS, GF, GA, home, away, L10, streak
# ---------------------------------------------------------------------------
NHL_TEAMS = [
    ("BOS", "Boston Bruins", 10, 7, 2, 1, 15, 36, 22, "3-1-0", "4-1-1", "7-2-1", "OT1"),
    ("TBL", "Tampa Bay Lightning", 8, 6, 2, 0, 12, 25, 21, "5-0-0", "1-2-0", "6-2-0", "W2"),
    ("OTT", "Ottawa Senators", 9, 6, 3, 0, 12, 24, 23, "3-1-0", "3-2-0", "6-3-0", "L1"),
    ("CAR", "Carolina Hurricanes", 11, 8, 2, 1, 17, 42, 27, "2-1-1", "6-1-0", "8-2-0", "W1"),
    ("NYR", "New York Rangers", 11, 7, 3, 1, 15, 33, 24, "6-0-0", "1-3-1", "7-2-1", "W1"),
    ("NYI", "New York Islanders", 9, 5, 3, 1, 11, 27, 20, "4-1-0", "1-2-1", "5-3-1", "W2"),
    ("FLA", "Florida Panthers", 9, 5, 2, 2, 12, 30, 25, "2-1-0", "3-1-2", "5-2-2", "W3"),
    ("TOR", "Toronto Maple Leafs", 11, 5, 4, 2, 12, 38, 35, "3-3-1", "2-1-1", "5-3-2", "W2"),
    ("WSH", "Washington Capitals", 9, 5, 4, 0, 10, 30, 29, "4-2-0", "1-2-0", "5-4-0", "L1"),
    ("NJD", "New Jersey Devils", 9, 5, 4, 0, 10, 29, 30, "4-2-0", "1-2-0", "5-4-0", "W1"),
    ("BUF", "Buffalo Sabres", 9, 4, 3, 2, 10, 27, 34, "3-2-0", "1-1-2", "4-3-2", "OT1"),
    ("MTL", "Montreal Canadiens", 9, 4, 3, 2, 10, 30, 34, "3-2-1", "1-1-1", "4-3-2", "OT1"),
    ("DET", "Detroit Red Wings", 9, 3, 3, 3, 9, 23, 28, "3-3-1", "0-0-2", "3-3-3", "OT1"),
    ("PIT", "Pittsburgh Penguins", 10, 3, 6, 1, 7, 33, 38, "2-1-0", "1-5-1", "3-6-1", "L4"),
    ("PHI", "Philadelphia Flyers", 11, 2, 6, 3, 7, 17, 36, "2-2-2", "0-4-1", "2-5-3", "W2"),
    ("CBJ", "Columbus Blue Jackets", 8, 3, 5, 0, 6, 20, 29, "3-3-0", "0-2-0", "3-5-0", "L2"),
    ("UTA", "Utah Mammoth", 10, 7, 3, 0, 14, 38, 31, "3-1-0", "4-2-0", "7-3-0", "W1"),
    ("MIN", "Minnesota Wild", 10, 6, 2, 2, 14, 31, 25, "4-0-0", "2-2-2", "6-2-2", "OT1"),
    ("DAL", "Dallas Stars", 9, 5, 3, 1, 11, 23, 15, "2-2-0", "3-1-1", "5-3-1", "W3"),
    ("VGK", "Vegas Golden Knights", 10, 8, 2, 0, 16, 42, 24, "5-1-0", "3-1-0", "8-2-0", "W3"),
    ("EDM", "Edmonton Oilers", 9, 7, 1, 1, 15, 41, 27, "2-1-1", "5-0-0", "7-1-1", "W2"),
    ("SEA", "Seattle Kraken", 10, 6, 3, 1, 13, 39, 34, "2-1-0", "4-2-1", "6-3-1", "W1"),
    ("COL", "Colorado Avalanche", 10, 5, 4, 1, 11, 41, 31, "3-1-1", "2-3-0", "5-4-1", "L2"),
    ("SJS", "San Jose Sharks", 10, 5, 4, 1, 11, 27, 35, "2-2-0", "3-2-1", "5-4-1", "W1"),
    ("WPG", "Winnipeg Jets", 9, 4, 3, 2, 10, 24, 26, "2-2-1", "2-1-1", "4-3-2", "L2"),
    ("NSH", "Nashville Predators", 8, 3, 2, 3, 9, 23, 24, "2-2-1", "1-0-2", "3-2-3", "W1"),
    ("STL", "St. Louis Blues", 9, 4, 4, 1, 9, 29, 29, "2-0-1", "2-4-0", "4-4-1", "W1"),
    ("ANA", "Anaheim Ducks", 9, 4, 5, 0, 8, 26, 29, "1-3-0", "3-2-0", "4-5-0", "L4"),
    ("CHI", "Chicago Blackhawks", 9, 3, 6, 0, 6, 21, 36, "3-2-0", "0-4-0", "3-6-0", "L1"),
    ("VAN", "Vancouver Canucks", 11, 2, 8, 1, 5, 33, 51, "1-3-0", "1-5-1", "1-8-1", "L2"),
    ("LAK", "Los Angeles Kings", 7, 1, 4, 2, 4, 17, 27, "0-3-0", "1-1-2", "1-4-2", "W1"),
    ("CGY", "Calgary Flames", 8, 2, 6, 0, 4, 17, 37, "1-3-0", "1-3-0", "2-6-0", "W1"),
]

# NHL schedule, 22 October 2026 - source S11.
# (away_code, home_code, "7:00 PM EDT")
NHL_FIXTURES = [
    ("NSH", "BOS", "19:00", "7:00 PM EDT"),
    ("NYR", "TOR", "19:00", "7:00 PM EDT"),
    ("SJS", "OTT", "19:00", "7:00 PM EDT"),
    ("ANA", "NJD", "19:00", "7:00 PM EDT"),
    ("FLA", "PIT", "19:00", "7:00 PM EDT"),
    ("LAK", "NYI", "19:30", "7:30 PM EDT"),
    ("VGK", "STL", "20:00", "8:00 PM EDT"),
    ("WPG", "DAL", "20:00", "8:00 PM EDT"),
    ("MIN", "CGY", "21:00", "9:00 PM EDT"),
    ("CAR", "EDM", "21:00", "9:00 PM EDT"),
    ("UTA", "SEA", "22:00", "10:00 PM EDT"),
    ("DET", "VAN", "22:00", "10:00 PM EDT"),
]

# ---------------------------------------------------------------------------
# NBA - 2025-26 final records, source S12. 2026-27 records, source S13.
# Fixtures 21 October 2026, source S14 (venue copied from the schedule).
# ---------------------------------------------------------------------------
NBA_PRIOR = {
    "DET": (60, 22), "BOS": (56, 26), "NYK": (53, 29), "CLE": (52, 30),
    "TOR": (46, 36), "ATL": (46, 36), "PHI": (45, 37), "ORL": (45, 37),
    "CHA": (44, 38), "MIA": (43, 39), "MIL": (32, 50), "CHI": (31, 51),
    "BKN": (20, 62), "IND": (19, 63), "WAS": (17, 65),
    "OKC": (64, 18), "SAS": (62, 20), "DEN": (54, 28), "LAL": (53, 29),
    "HOU": (52, 30), "MIN": (49, 33), "PHX": (45, 37), "POR": (42, 40),
    "LAC": (42, 40), "GSW": (37, 45), "NOP": (26, 56), "DAL": (26, 56),
}
NBA_NAMES = {
    "ATL": "Atlanta Hawks", "ORL": "Orlando Magic", "MIL": "Milwaukee Bucks",
    "WAS": "Washington Wizards", "MIN": "Minnesota Timberwolves", "MIA": "Miami Heat",
    "CHA": "Charlotte Hornets", "BKN": "Brooklyn Nets", "CHI": "Chicago Bulls",
    "TOR": "Toronto Raptors", "UTA": "Utah Jazz", "MEM": "Memphis Grizzlies",
    "IND": "Indiana Pacers", "NOP": "New Orleans Pelicans", "DAL": "Dallas Mavericks",
    "HOU": "Houston Rockets", "GSW": "Golden State Warriors", "LAL": "Los Angeles Lakers",
    "PHX": "Phoenix Suns", "POR": "Portland Trail Blazers",
    "SAC": "Sacramento Kings", "LAC": "LA Clippers",
}
# 2026-27 records actually present in S13 at capture time (all others 0-0).
NBA_CURRENT = {"DET": (1, 0), "PHI": (1, 0), "SAS": (0, 1), "NYK": (0, 1),
               "BOS": (0, 1), "OKC": (1, 0)}
NBA_FIXTURES = [
    ("ATL", "ORL", "19:00", "7:00 PM ET", "Kia Center, Orlando, FL"),
    ("MIL", "WAS", "19:00", "7:00 PM ET", "Capital One Arena, Washington, DC"),
    ("MIN", "MIA", "19:30", "7:30 PM ET", "Kaseya Center, Miami, FL"),
    ("CHA", "BKN", "19:30", "7:30 PM ET", "Barclays Center, Brooklyn, NY"),
    ("CHI", "TOR", "19:30", "7:30 PM ET", "Scotiabank Arena, Toronto, ON"),
    ("UTA", "MEM", "20:00", "8:00 PM ET", "FedExForum, Memphis, TN"),
    ("IND", "NOP", "20:00", "8:00 PM ET", "Smoothie King Center, New Orleans, LA"),
    ("DAL", "HOU", "20:30", "8:30 PM ET", "Toyota Center, Houston, TX"),
    ("GSW", "LAL", "22:00", "10:00 PM ET", "Crypto.com Arena, Los Angeles, CA"),
    ("PHX", "POR", "22:00", "10:00 PM ET", "Moda Center, Portland, OR"),
    ("SAC", "LAC", "22:30", "10:30 PM ET", "Intuit Dome, Inglewood, CA"),
]

# ---------------------------------------------------------------------------
# MLB - source S15 (final 2026 regular-season standings).
# Columns: code, name, W, L, RS, RA, home, away
# ---------------------------------------------------------------------------
MLB_TEAMS = {
    "TB": ("Tampa Bay Rays", 98, 64, 736, 650, "55-26", "43-38"),
    "MIL": ("Milwaukee Brewers", 103, 59, 832, 618, "55-26", "48-33"),
}

# ---------------------------------------------------------------------------
# Snooker - sources S17 (prize money) and S18 (Round 2 schedule, best of 7).
# ---------------------------------------------------------------------------
SNOOKER_PLAYERS = {
    "Zhao Xintong": (1, 1265550), "Wu Yize": (2, 1238900), "Judd Trump": (3, 1114050),
    "Neil Robertson": (4, 1100200), "Mark Selby": (5, 1070500), "John Higgins": (6, 905000),
    "Shaun Murphy": (7, 897350), "Mark Williams": (8, 747400), "Kyren Wilson": (9, 716800),
    "Barry Hawkins": (10, 670050), "Chris Wakelin": (11, 576550), "Mark Allen": (12, 536050),
    "Ronnie O'Sullivan": (13, 513750), "Xiao Guodong": (14, 503900), "Ding Junhui": (15, 479850),
    "Ali Carter": (16, 414400), "Zhou Yuelong": (17, 359100), "Jack Lisowski": (18, 358100),
    "Stuart Bingham": (19, 350550), "Chang Bingyu": (20, 350200), "Zhang Anda": (21, 332600),
    "Thepchaiya Un-Nooh": (22, 329850), "Elliot Slessor": (23, 329200), "Jak Jones": (24, 319300),
    "Si Jiahui": (25, 292500), "Yuan Sijun": (26, 288400), "Gary Wilson": (27, 286550),
    "Lei Peifan": (28, 279050), "Pang Junxu": (29, 272750), "Joe O'Connor": (30, 245450),
    "Noppon Saengkham": (31, 242500), "Hossein Vafaei": (32, 242450), "Stephen Maguire": (33, 235700),
    "David Gilbert": (34, 221200), "Tom Ford": (35, 199800), "Jackson Page": (36, 198500),
}
# Round 2, Wednesday 21 October 2026, source S18 (local UK times as published).
SNOOKER_FIXTURES = [
    ("Pang Junxu", "Liam Davies", "05:00"),
    ("Ka Wai Cheung", "Stuart Bingham", "05:00"),
    ("Daniel Wells", "Ryan Day", "08:00"),
    ("John Higgins", "Jak Jones", "08:00"),
    ("Sam Craigie", "Xu Si", "09:00"),
    ("Zhang Anda", "Mark Williams", "09:00"),
    ("Michael Holt", "Jordan Brown", "14:00"),
    ("Noppon Saengkham", "Scott Donaldson", "14:00"),
    ("Gao Yang", "David Gilbert", "14:00"),
    ("Elliot Slessor", "Jamie Jones", "15:00"),
    ("Luca Brecel", "Martin O'Donnell", "15:00"),
]

# ---------------------------------------------------------------------------
# URC - source S20 table (after Round 3): PTS, PL, W, D, L, BP, PF, PA
# ---------------------------------------------------------------------------
URC_TEAMS = {
    "Edinburgh": (14, 3, 3, 0, 0, 2, 80, 54),
    "Glasgow Warriors": (13, 3, 2, 1, 0, 3, 95, 72),
    "Vodacom Bulls": (11, 3, 2, 0, 1, 3, 126, 54),
    "DHL Stormers": (11, 3, 2, 0, 1, 3, 81, 54),
    "Hollywoodbets Sharks": (10, 3, 2, 0, 1, 2, 89, 83),
    "Cardiff Rugby": (9, 3, 2, 0, 1, 1, 66, 71),
    "10bet Lions": (9, 3, 2, 0, 1, 1, 77, 102),
    "Dragons RFC": (9, 3, 1, 1, 1, 3, 88, 83),
    "Munster": (9, 3, 1, 1, 1, 3, 72, 74),
    "Leinster": (8, 3, 1, 0, 2, 4, 75, 58),
    "Ulster": (8, 3, 0, 2, 1, 4, 88, 93),
    "Scarlets": (7, 3, 1, 0, 2, 3, 68, 85),
    "Ospreys": (6, 3, 1, 0, 2, 2, 81, 107),
    "Connacht": (5, 3, 1, 0, 2, 1, 56, 84),
    "Benetton": (5, 3, 0, 1, 2, 3, 64, 68),
    "Zebre Parma": (1, 3, 0, 0, 3, 1, 52, 116),
}
# Round 4 fixtures, source S19. Times are LOCAL as published by URC.
URC_FIXTURES = [
    ("Cardiff Rugby", "Hollywoodbets Sharks", "Fri 23 Oct 2026", "14:45 local", "Cardiff Arms Park"),
    ("Connacht", "Zebre Parma", "Fri 23 Oct 2026", "14:45 local", "Dexcom Stadium"),
    ("Edinburgh", "10bet Lions", "Fri 23 Oct 2026", "14:45 local", "Hive Stadium"),
    ("Vodacom Bulls", "Ulster", "Sat 24 Oct 2026", "07:45 local", "Loftus Versfeld"),
    ("DHL Stormers", "Scarlets", "Sat 24 Oct 2026", "10:00 local", "DHL Stadium"),
    ("Benetton", "Glasgow Warriors", "Sat 24 Oct 2026", "10:00 local", "Stadio Monigo"),
    ("Leinster", "Munster", "Sat 24 Oct 2026", "13:00 local", "Aviva Stadium"),
    ("Ospreys", "Dragons RFC", "Sat 24 Oct 2026", "14:00 local", "St Helen's"),
]


def utc_stamp(day, local_time, offset_hours):
    """Convert a published local clock time to a UTC ISO timestamp.

    `offset_hours` is the fixed offset of the published zone relative to UTC
    (EDT = -4, ET in the NBA table = -4 for the dates captured). No daylight
    assumption is made beyond that explicit offset.
    """
    naive = datetime.strptime(f"{day} {local_time}", "%Y-%m-%d %H:%M")
    return (naive - timedelta(hours=offset_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")


def slug(text):
    out = []
    for ch in text.lower():
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "-":
            out.append("-")
    return "".join(out).strip("-")


def nhl_inputs(code):
    row = next(r for r in NHL_TEAMS if r[0] == code)
    _, name, gp, w, l, ot, pts, gf, ga, home, away, l10, streak = row
    return {
        "name": name,
        "gp": gp, "w": w, "l": l, "ot": ot, "pts": pts,
        "gf": gf, "ga": ga, "home_record": home, "away_record": away,
        "l10": l10, "streak": streak,
    }


def build():
    matches = []

    for away, home, utc_time, display in NHL_FIXTURES:
        h, a = nhl_inputs(home), nhl_inputs(away)
        matches.append({
            "id": f"nhl-2026-10-22-{home.lower()}-{away.lower()}",
            "sport": "Ice Hockey",
            "sport_slug": "ice-hockey",
            "league": "NHL",
            "competition": "NHL regular season",
            "start_local": f"Thu 22 Oct 2026, {display}",
            "start_utc": utc_stamp("2026-10-22", utc_time, -4),
            "venue": "",
            "home": {"name": h["name"], "code": home},
            "away": {"name": a["name"], "code": away},
            "fixture_sources": ["S11"],
            "input_sources": ["S10"],
            "inputs_verified": True,
            "model": "nhl_amount",
            "inputs": {"home": h, "away": a},
            "notes": "",
        })

    for away, home, utc_time, display, venue in NBA_FIXTURES:
        if home not in NBA_PRIOR or away not in NBA_PRIOR:
            # Verified fixture, but one or both clubs' prior-season records were
            # truncated on the official table at capture time: do not originate.
            matches.append({
                "id": f"nba-2026-10-21-{home.lower()}-{away.lower()}",
                "sport": "Basketball",
                "sport_slug": "basketball",
                "league": "NBA",
                "competition": "NBA regular season",
                "start_local": f"Wed 21 Oct 2026, {display}",
                "start_utc": utc_stamp("2026-10-21", utc_time, -4),
                "venue": venue,
                "home": {"name": NBA_NAMES.get(home, home), "code": home},
                "away": {"name": NBA_NAMES.get(away, away), "code": away},
                "fixture_sources": ["S14"],
                "input_sources": ["S12", "S13"],
                "inputs_verified": False,
                "model": "nba",
                "inputs": {
                    "home": {"prior": NBA_PRIOR.get(home), "current": NBA_CURRENT.get(home, (0, 0))},
                    "away": {"prior": NBA_PRIOR.get(away), "current": NBA_CURRENT.get(away, (0, 0))},
                },
                "notes": "2025-26 record for one or both clubs was truncated in the official standings capture; no line originated.",
            })
            continue
        matches.append({
            "id": f"nba-2026-10-21-{home.lower()}-{away.lower()}",
            "sport": "Basketball",
            "sport_slug": "basketball",
            "league": "NBA",
            "competition": "NBA regular season",
            "start_local": f"Wed 21 Oct 2026, {display}",
            "start_utc": utc_stamp("2026-10-21", utc_time, -4),
            "venue": venue,
            "home": {"name": NBA_NAMES[home], "code": home},
            "away": {"name": NBA_NAMES[away], "code": away},
            "fixture_sources": ["S14"],
            "input_sources": ["S12", "S13"],
            "inputs_verified": True,
            "model": "nba",
            "inputs": {
                "home": {"prior": NBA_PRIOR[home], "current": NBA_CURRENT.get(home, (0, 0))},
                "away": {"prior": NBA_PRIOR[away], "current": NBA_CURRENT.get(away, (0, 0))},
            },
            "notes": "Totals not originated: no official team-level pace/efficiency table was captured.",
        })

    # MLB World Series Game 1 (fixture verified on S15 "next game" rows and S16).
    hname, hw, hl, hrs, hra, hhome, haway = MLB_TEAMS["MIL"]
    aname, aw, al, ars, ara, ahome, aaway = MLB_TEAMS["TB"]
    matches.append({
        "id": "mlb-2026-10-23-mil-tb",
        "sport": "Baseball",
        "sport_slug": "baseball",
        "league": "MLB",
        "competition": "World Series, Game 1",
        "start_local": "Fri 23 Oct 2026 (first-pitch time not confirmed from an official source)",
        "start_utc": "",
        "venue": "",
        "home": {"name": hname, "code": "MIL"},
        "away": {"name": aname, "code": "TB"},
        "fixture_sources": ["S15", "S16"],
        "input_sources": ["S15"],
        "inputs_verified": True,
        "model": "mlb",
        "inputs": {
            "home": {"w": hw, "l": hl, "rs": hrs, "ra": hra, "home_record": hhome, "away_record": haway},
            "away": {"w": aw, "l": al, "rs": ars, "ra": ara, "home_record": ahome, "away_record": aaway},
        },
        "notes": "Game 1 of the World Series at Milwaukee, per MLB standings 'next game' rows (Oct 23, TB at MIL).",
    })

    for home, away, date, time, venue in URC_FIXTURES:
        h, a = URC_TEAMS[home], URC_TEAMS[away]

        def pack(t):
            return {"pts": t[0], "pl": t[1], "w": t[2], "d": t[3], "l": t[4],
                    "bp": t[5], "pf": t[6], "pa": t[7]}
        matches.append({
            "id": f"urc-2026-{slug(home)}-{slug(away)}",
            "sport": "Rugby Union",
            "sport_slug": "rugby-union",
            "league": "United Rugby Championship",
            "competition": "URC Round 4",
            "start_local": f"{date}, {time}",
            "start_utc": "",
            "venue": venue,
            "home": {"name": home, "code": ""},
            "away": {"name": away, "code": ""},
            "fixture_sources": ["S19"],
            "input_sources": ["S20"],
            "inputs_verified": True,
            "model": "urc",
            "inputs": {"home": pack(h), "away": pack(a)},
            "notes": "Kick-off time is the local time published by URC; no UTC conversion applied.",
        })

    for home, away, time in SNOOKER_FIXTURES:
        have = home in SNOOKER_PLAYERS and away in SNOOKER_PLAYERS
        def srank(p):
            r = SNOOKER_PLAYERS.get(p)
            return {"rank": r[0], "money": r[1]} if r else {"rank": None, "money": None}
        matches.append({
            "id": f"snooker-2026-10-21-{slug(home)}-{slug(away)}",
            "sport": "Snooker",
            "sport_slug": "snooker",
            "league": "World Snooker Tour",
            "competition": "BetVictor Northern Ireland Open 2026, Round 2 (best of 7)",
            "start_local": f"Wed 21 Oct 2026, {time} UK time",
            "start_utc": "",
            "venue": "",
            "home": {"name": home, "code": ""},
            "away": {"name": away, "code": ""},
            "fixture_sources": ["S18"],
            "input_sources": ["S17"],
            "inputs_verified": have,
            "model": "snooker",
            "inputs": {"home": srank(home), "away": srank(away), "best_of": 7},
            "notes": "" if have else "One or both players fall outside the official top-36 prize-money extract captured; no line originated.",
        })

    data = {
        "meta": {
            "generated_by": "scripts/prepare_inputs.py",
            "captured_at_utc": "2026-10-21T09:00:00Z",
            "note": "Inputs transcribed from the official sources listed in data/session-74f9613e/sources.json. Missing inputs are omitted, never estimated.",
        },
        "matches": matches,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    print(f"wrote {OUT} with {len(matches)} matches")


if __name__ == "__main__":
    build()

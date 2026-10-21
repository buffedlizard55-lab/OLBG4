#!/usr/bin/env python3
"""Build the reverse-engineered OLBG inventory and the sport coverage register.

Two outputs:
  data/session-74f9613e/olbg_inventory.json - every fixture seen on the OLBG sport pages at capture
                             time, with the official source that confirms it (or a
                             NULL official source when none could be confirmed).
  data/session-74f9613e/coverage.json       - one row per OLBG sport, with the coverage decision and
                             the reason. This is the audit trail for the brief's
                             "every sport except ..." requirement.

Run: python3 scripts/prepare_inventory.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-74f9613e")

OLBG_BASE = "https://www.olbg.com"
HUB = f"{OLBG_BASE}/betting-tips"

# Sport taxonomy read from https://www.olbg.com/sitemap-betting-tips.xml (S09).
TAXONOMY = [
    ("Horse Racing", 2, "excluded"), ("Football", 1, "excluded"),
    ("Tennis", 3, "in scope"), ("Golf", 5, "in scope"),
    ("American Football", 11, "excluded"), ("Rugby League", 10, "in scope"),
    ("Rugby Union", 9, "in scope"), ("Cricket", 7, "in scope"),
    ("Basketball", 4, "in scope"), ("Baseball", 12, "in scope"),
    ("Darts", 15, "in scope"), ("Snooker", 8, "in scope"),
    ("Boxing", 16, "excluded"), ("Ice Hockey", 13, "in scope"),
    ("Motor Racing", 14, "in scope"), ("Handball", 20, "in scope"),
    ("Volleyball", 21, "in scope"), ("Greyhounds", 28, "in scope"),
    ("Cycling", 17, "excluded"), ("Gaelic Football", 25, "in scope"),
    ("Aussie Rules", 22, "in scope"), ("eSports", 23, "in scope"),
]

# ---------------------------------------------------------------------------
# Inventory rows.
# status meanings:
#   priced          - line originated from fully verified inputs (see matches.json)
#   fixture-only    - fixture confirmed by an official source; no line originated
#   unverified      - fixture seen on OLBG only; no official confirmation obtained
#   no-match-market - sport hub showed no head-to-head fixtures at capture time
# ---------------------------------------------------------------------------
ICC_BASE = "https://www.icc-cricket.com"

CRICKET = [
    ("ICC CWC Challenge League A, 2024-26", "21 Oct 2026, 02:45 (time as displayed by ICC)",
     "Kenya", "Denmark", f"{ICC_BASE}/tournaments/cwc-challenge-league/matches/275468/kenya-vs-denmark"),
    ("ICC Men's T20 World Cup Africa Sub Regional Qualifier C, 2026",
     "21 Oct 2026, 04:30 (time as displayed by ICC)", "Mozambique", "Gambia",
     f"{ICC_BASE}/matches/274932/mozambique-vs-gambia"),
    ("ICC Men's T20 World Cup Africa Sub Regional Qualifier C, 2026",
     "21 Oct 2026, 04:30 (time as displayed by ICC)", "Lesotho", "Uganda",
     f"{ICC_BASE}/matches/274933/lesotho-vs-uganda"),
    ("ODI (Afghanistan v Bangladesh)", "21 Oct 2026, 07:30 (time as displayed by ICC)",
     "Afghanistan", "Bangladesh", f"{ICC_BASE}/matches/274658/afghanistan-vs-bangladesh"),
    ("ICC Men's T20 World Cup Africa Sub Regional Qualifier C, 2026",
     "21 Oct 2026, 08:50 (time as displayed by ICC)", "Zambia", "Nigeria",
     f"{ICC_BASE}/matches/274934/zambia-vs-nigeria"),
    ("ICC CWC Challenge League A, 2024-26", "22 Oct 2026, 02:45 (time as displayed by ICC)",
     "Papua New Guinea", "Jersey",
     f"{ICC_BASE}/tournaments/cwc-challenge-league/matches/275470/papua-new-guinea-vs-jersey"),
    ("ICC CWC Challenge League A, 2024-26", "22 Oct 2026, 02:45 (time as displayed by ICC)",
     "Qatar", "Kuwait",
     f"{ICC_BASE}/tournaments/cwc-challenge-league/matches/275473/qatar-vs-kuwait"),
    ("T20 International (New Zealand v India)", "22 Oct 2026, 03:00 (time as displayed by ICC)",
     "New Zealand", "India", f"{ICC_BASE}/matches/271646/new-zealand-vs-india"),
    ("Ireland in Namibia, 5 ODI Series, 2026 - 1st ODI",
     "22 Oct 2026, 03:30 (time as displayed by ICC)", "Namibia", "Ireland", f"{ICC_BASE}/"),
    ("Ireland in Namibia, 5 ODI Series, 2026 - 2nd ODI",
     "24 Oct 2026, 03:30 (time as displayed by ICC)", "Namibia", "Ireland", f"{ICC_BASE}/"),
]

# Darts: PDC European Championship 2026, first round. Seen on OLBG (S02). The PDC
# tournament page (S23) confirms the event, venue, format and field size but the
# draw itself was not machine-readable, so these rows stay "unverified".
DARTS = [
    ("Luke Woodhouse", "Dirk van Duijvenbode", "22 Oct 2026, 13:15", "Win Match 2-way"),
    ("Niels Zonneveld", "Cameron Menzies", "22 Oct 2026, 14:15", "Win Match 2-way"),
    ("Gerwyn Price", "Rob Cross", "22 Oct 2026, 14:45", "Win Match 2-way"),
    ("James Wade", "Damon Heta", "22 Oct 2026, 15:15", "Win Match 2-way"),
    ("Luke Humphries", "Ryan Searle", "22 Oct 2026, 15:45", "Win Match 2-way"),
    ("Danny Noppert", "Stephen Bunting", "22 Oct 2026, 13:45", "Total Legs"),
    ("Gian van Veen", "Andrew Gilding", "22 Oct 2026, 16:15", "Win Match 2-way"),
    ("Ross Smith", "Karel Sedlacek", "22 Oct 2026, 16:45", "Win Match 2-way"),
    ("Jonny Clayton", "Niko Springer", "23 Oct 2026, 14:45", "Win Match 2-way"),
    ("Ryan Joyce", "Jermaine Wattimena", "23 Oct 2026, 13:15", "Win Match 2-way"),
    ("Krzysztof Ratajski", "Dave Chisnall", "23 Oct 2026, 13:45", "Win Match 2-way"),
    ("Nathan Aspinall", "Cristo Reyes", "23 Oct 2026, 14:15", "Win Match 2-way"),
    ("Luke Littler", "William O'Connor", "23 Oct 2026, 15:15", "Handicap 2-way"),
    ("Wessel Nijman", "Martin Schindler", "23 Oct 2026, 15:45", "Win Match 2-way"),
    ("Kevin Doets", "Michael van Gerwen", "23 Oct 2026, 16:15", "Total Legs"),
    ("Josh Rock", "Chris Dobey", "23 Oct 2026, 13:15", "Win Match 2-way"),
]

TENNIS = [
    ("Leylah Fernandez", "Aliaksandra Sasnovich", "21 Oct 2026, 02:30", "Win Match"),
    ("Katie Boulter", "Viktorija Golubic", "21 Oct 2026, 01:30", "Win Match"),
    ("James Duckworth", "Luciano Darderi", "21 Oct 2026, 02:30", "Win Match"),
    ("Adrian Mannarino", "Andrey Rublev", "21 Oct 2026, 05:30", "Win Match"),
    ("Sorana Cirstea", "Sara Bejlek", "21 Oct 2026, 04:00", "Win Match"),
    ("Zangar Nurlanuly", "Tomas Machac", "21 Oct 2026, 04:00", "1st Set Winner"),
    ("Mattia Bellucci", "Tomas Martin Etcheverry", "21 Oct 2026, 02:30", "Set Betting"),
    ("Dino Prizmic", "Damir Dzumhur", "21 Oct 2026, 05:30", "Win Match"),
    ("Stan Wawrinka", "Martin Landaluce", "21 Oct 2026, 08:00", "Win Match"),
    ("David Goffin", "Remy Bertola", "21 Oct 2026, 12:00", "Win Match"),
    ("Facundo Diaz Acosta", "Nikoloz Basilashvili", "21 Oct 2026, 04:00", "Set Betting"),
    ("Martin Damm", "Francisco Cerundolo", "21 Oct 2026, 05:30", "Set Betting"),
    ("Mariano Navone", "Tallon Griekspoor", "21 Oct 2026, 07:00", "Win Match"),
    ("Ekaterina Alexandrova", "Marta Kostyuk", "21 Oct 2026, 07:00", "Win Match"),
    ("Clement Chidekh", "Jacob Fearnley", "21 Oct 2026, 08:30", "Set Betting"),
]

# French professional rugby seen on OLBG's rugby-union page (S06). No official
# LNR source was captured this cycle, so these stay unverified.
RUGBY_FR = [
    ("Montauban", "Oyonnax", "22 Oct 2026, 15:00", "Pro D2"),
    ("Narbonne", "Brive", "23 Oct 2026, 13:00", "Pro D2"),
    ("Agen", "Nissa", "23 Oct 2026, 13:30", "Pro D2"),
    ("Soyaux Angouleme", "Dax", "23 Oct 2026, 13:30", "Pro D2"),
    ("Aurillac", "Nevers", "23 Oct 2026, 13:30", "Pro D2"),
    ("Valence Romans", "Colomiers", "23 Oct 2026, 13:30", "Pro D2"),
    ("Grenoble", "Biarritz", "23 Oct 2026, 15:00", "Pro D2"),
    ("Provence", "Beziers", "23 Oct 2026, 15:00", "Pro D2"),
    ("Bayonne", "Lyon", "24 Oct 2026, 10:35", "Top 14"),
    ("Toulouse", "Perpignan", "24 Oct 2026, 10:35", "Top 14"),
    ("La Rochelle", "Bordeaux", "25 Oct 2026, 16:05", "Top 14"),
]

GAELIC = [
    ("All-Ireland club championship", "25 Oct 2026, 12:00", "St Finbarrs", "Nemo Rangers", "Draw / +1.50 handicap"),
]


def build():
    rows = []

    for sport, slug, oid in (("Ice Hockey", "ice-hockey", 13), ("Basketball", "basketball", 4),
                             ("Baseball", "baseball", 12), ("Rugby Union", "rugby-union", 9),
                             ("Snooker", "snooker", 8)):
        pass  # fixture rows for priced sports come from matches.json, not duplicated here

    for comp, start, home, away, link in CRICKET:
        rows.append({
            "sport": "Cricket", "sport_slug": "cricket", "competition": comp,
            "start": start, "home": home, "away": away,
            "olbg_market_example": "Win Match",
            "olbg_url": f"{OLBG_BASE}/betting-tips/Cricket/All_Cricket/All_Events/7",
            "official_source": link, "official_source_id": "S21",
            "status": "fixture-only",
            "status_reason": "Fixture confirmed by the ICC. No line originated: the ICC ODI team-ranking table rendered empty in this environment, so no team-strength input could be verified.",
        })

    for home, away, start, market in DARTS:
        rows.append({
            "sport": "Darts", "sport_slug": "darts",
            "competition": "PDC Machineseeker European Championship 2026, first round",
            "start": start, "home": home, "away": away,
            "olbg_market_example": market,
            "olbg_url": f"{OLBG_BASE}/betting-tips/Darts/All_Darts/All_Events/15",
            "official_source": "", "official_source_id": "",
            "status": "unverified",
            "status_reason": "Pairing seen on OLBG only. The PDC tournament page confirms the event, venue and format, but its draw was not machine-readable, so the pairing and no player-level input could be verified.",
        })

    for home, away, start, market in TENNIS:
        rows.append({
            "sport": "Tennis", "sport_slug": "tennis", "competition": "ATP/WTA tour (as listed by OLBG)",
            "start": start, "home": home, "away": away,
            "olbg_market_example": market,
            "olbg_url": f"{OLBG_BASE}/betting-tips/Tennis/All_Tennis/3",
            "official_source": "", "official_source_id": "",
            "status": "unverified",
            "status_reason": "Pairing seen on OLBG only. ATP tournament draw and player pages did not render as machine-readable tables at capture time, so neither the pairing nor player-level inputs could be verified.",
        })

    for home, away, start, comp in RUGBY_FR:
        rows.append({
            "sport": "Rugby Union", "sport_slug": "rugby-union",
            "competition": f"French {comp} (as listed by OLBG)", "start": start,
            "home": home, "away": away, "olbg_market_example": "To Win",
            "olbg_url": f"{OLBG_BASE}/betting-tips/Rugby_Union/All_Rugby_Union/All_Events/9",
            "official_source": "", "official_source_id": "",
            "status": "unverified",
            "status_reason": "Fixture seen on OLBG only. No official LNR or Pro D2 source was captured this cycle, so it is listed but not priced.",
        })

    for comp, start, home, away, market in GAELIC:
        rows.append({
            "sport": "Gaelic Football", "sport_slug": "gaelic-football", "competition": comp,
            "start": start, "home": home, "away": away,
            "olbg_market_example": market,
            "olbg_url": f"{OLBG_BASE}/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/25",
            "official_source": "", "official_source_id": "",
            "status": "unverified",
            "status_reason": "Fixture seen on OLBG only; no GAA official source was captured in this cycle.",
        })

    inventory = {
        "meta": {
            "generated_by": "scripts/prepare_inventory.py",
            "captured_at_utc": "2026-10-21T09:00:00Z",
            "note": "Reverse-engineered OLBG listing surface. Priced sports take their fixture rows from data/session-74f9613e/matches.json to avoid duplication.",
        },
        "olbg_sport_taxonomy": [
            {"sport": s, "olbg_id": i, "hub_url": f"{HUB}/{s.replace(' ', '_')}/{i}",
             "scope": scope} for s, i, scope in TAXONOMY
        ],
        "rows": rows,
    }

    coverage = {
        "meta": {
            "generated_by": "scripts/prepare_inventory.py",
            "captured_at_utc": "2026-10-21T09:00:00Z",
            "decision_rule": "A sport is priced only when every model input for a match is verifiable from an official source. Otherwise the fixture is published with a blank line and a flag.",
        },
        "sports": [
            {"sport": "Ice Hockey", "olbg_id": 13, "status": "priced",
             "fixtures_listed": 12, "fixtures_priced": 12, "sources": ["S10", "S11"],
             "note": "All 12 NHL games scheduled for 22 Oct 2026 priced from official NHL standings and schedule."},
            {"sport": "Basketball", "olbg_id": 4, "status": "priced",
             "fixtures_listed": 11, "fixtures_priced": 9, "sources": ["S12", "S13", "S14"],
             "note": "All 11 NBA games on 21 Oct 2026 captured from the official schedule; two (Utah at Memphis, Sacramento at LA Clippers) left unpriced because those clubs' 2025-26 records were truncated in the official table. Totals are not originated for this sport: no official pace/efficiency table was captured."},
            {"sport": "Baseball", "olbg_id": 12, "status": "priced",
             "fixtures_listed": 1, "fixtures_priced": 1, "sources": ["S15", "S16"],
             "note": "World Series Game 1 (Tampa Bay at Milwaukee, 23 Oct 2026) is the only MLB fixture on the official calendar in the window."},
            {"sport": "Rugby Union", "olbg_id": 9, "status": "priced",
             "fixtures_listed": 19, "fixtures_priced": 8, "sources": ["S19", "S20", "S06"],
             "note": "All eight URC Round 4 matches priced from the official league table and match centre. Eleven French Top 14 / Pro D2 fixtures also appeared on OLBG; they are listed on the Flagged page but not priced because no official LNR source was captured."},
            {"sport": "Snooker", "olbg_id": 8, "status": "partially priced",
             "fixtures_listed": 11, "fixtures_priced": 2, "sources": ["S17", "S18"],
             "note": "All 11 Northern Ireland Open Round 2 matches confirmed on the official WST draw. Only two pairings have both players inside the official top-36 prize-money extract, so only those two are priced."},
            {"sport": "Cricket", "olbg_id": 7, "status": "fixture-only",
             "fixtures_listed": 10, "fixtures_priced": 0, "sources": ["S21", "S22"],
             "note": "Fixtures confirmed by the ICC. No lines: the ICC ODI team-ranking table rendered empty, so team strength could not be verified."},
            {"sport": "Darts", "olbg_id": 15, "status": "unverified inventory",
             "fixtures_listed": 16, "fixtures_priced": 0, "sources": ["S23", "S02"],
             "note": "European Championship fixtures seen on OLBG. PDC's tournament page confirms the event but not a machine-readable draw; pairings are therefore flagged, not published as priced rows."},
            {"sport": "Tennis", "olbg_id": 3, "status": "unverified inventory",
             "fixtures_listed": 15, "fixtures_priced": 0, "sources": ["S24", "S04"],
             "note": "Fixtures seen on OLBG. ATP pages did not render a usable draw or per-player form table in this environment, so nothing is priced."},
            {"sport": "Rugby League", "olbg_id": 10, "status": "no-match-market",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S07"],
             "note": "OLBG's rugby-league all-events page listed only outright markets at capture time (State of Origin 2027, Super League 2027 Grand Final, NRL 2027 Grand Final). No head-to-head fixture to price."},
            {"sport": "Gaelic Football", "olbg_id": 25, "status": "unverified inventory",
             "fixtures_listed": 1, "fixtures_priced": 0, "sources": ["S01"],
             "note": "Club fixture seen on OLBG; no GAA official confirmation captured."},
            {"sport": "Golf", "olbg_id": 5, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy; tournament/outright markets only. Not covered in this cycle."},
            {"sport": "Motor Racing", "olbg_id": 14, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy; race/outright markets only. Not covered in this cycle."},
            {"sport": "Greyhounds", "olbg_id": 28, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy; race-level markets. Not covered in this cycle."},
            {"sport": "Handball", "olbg_id": 20, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy. Not covered in this cycle."},
            {"sport": "Volleyball", "olbg_id": 21, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy. Not covered in this cycle."},
            {"sport": "eSports", "olbg_id": 23, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy (best-tipsters page only). Not covered in this cycle."},
            {"sport": "Aussie Rules", "olbg_id": 22, "status": "not covered",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"],
             "note": "Sport hub exists in the OLBG taxonomy (best-tipsters page only). Not covered in this cycle."},
            {"sport": "Horse Racing", "olbg_id": 2, "status": "excluded by brief",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"], "note": ""},
            {"sport": "Football", "olbg_id": 1, "status": "excluded by brief",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"], "note": ""},
            {"sport": "American Football", "olbg_id": 11, "status": "excluded by brief",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"], "note": ""},
            {"sport": "Boxing", "olbg_id": 16, "status": "excluded by brief",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"], "note": ""},
            {"sport": "Cycling", "olbg_id": 17, "status": "excluded by brief",
             "fixtures_listed": 0, "fixtures_priced": 0, "sources": ["S09"], "note": ""},
        ],
    }

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "olbg_inventory.json"), "w", encoding="utf-8") as fh:
        json.dump(inventory, fh, indent=2)
        fh.write("\n")
    with open(os.path.join(DATA, "coverage.json"), "w", encoding="utf-8") as fh:
        json.dump(coverage, fh, indent=2)
        fh.write("\n")
    print(f"wrote inventory ({len(rows)} rows) and coverage ({len(coverage['sports'])} sports)")


if __name__ == "__main__":
    build()

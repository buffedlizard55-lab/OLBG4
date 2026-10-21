#!/usr/bin/env python3
"""
Board K (session-ee9c2db4) — K1: Complete OLBG.com 28-Slot Sport Taxonomy & Sub-Feed Audit
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "session-ee9c2db4" / "data"


OLBG_SPORT_TAXONOMY = {
    "captured_date": "2026-10-21",
    "platform": "OLBG.com (Invendium Ltd / OLBG Betting Tips Platform)",
    "url_architecture": {
        "hub_url": "https://www.olbg.com/betting-tips",
        "sport_feed_pattern": "https://www.olbg.com/betting-tips/{Sport_Slug}/{sport_id}",
        "competition_subfeed_pattern": "https://www.olbg.com/betting-tips/{Sport_Slug}/{Category_Or_Competition}/{sport_id}",
        "nested_competition_pattern": "https://www.olbg.com/betting-tips/{Sport_Slug}/{Region}/{Competition}/{sport_id}",
        "match_market_pattern": "https://www.olbg.com/betting-tips/{Sport_Slug}/{Competition}/{Home_vs_Away}/{Market_Slug}/{event_id}",
        "tipster_leaderboard_url": "https://www.olbg.com/best-tipsters",
        "sitemap_index_url": "https://www.olbg.com/sitemap-betting-tips.xml",
    },
    "reverse_engineering_findings": [
        {
            "id": "RE-01",
            "title": "20-Card Top-Level Feed Truncation Hidden Behind Competition Sub-Feeds",
            "detail": (
                "OLBG's top-level sport pages (/betting-tips/{Sport}/{id}) cap initial server HTML rendering at ~20 event cards "
                "ordered by tipster volume. Probing competition sub-feeds (/Basketball/NBA/4, /Basketball/European/4, "
                "/Basketball/European/Euroleague/4, /Basketball/Other/4, /Ice_Hockey/NHL/13, /Ice_Hockey/Other/13) plus live intra-day "
                "additions across Tennis, Snooker, and Volleyball uncovered 30 additional live OLBG match fixtures (170 matches/races + "
                "24 outrights = 194 unique in-scope OLBG events vs 140 in earlier single-page captures)."
            ),
        },
        {
            "id": "RE-02",
            "title": "Complete 28-Slot Numeric Sport Router (IDs 1..28) & Correction of Prior Taxonomy Bug",
            "detail": (
                "Numeric sport IDs control OLBG's backend query while URL path text is cosmetic. Earlier repo artifact "
                "data/olbg-structure.json misidentified ID 17 as 'Aussie Rules' because /Aussie_Rules/17 returned Cycling's empty shell. "
                "Live probing of IDs 1..28 + /best-tipsters + /sitemap-betting-tips.xml proved: ID 6 = Specials (excluded), "
                "ID 17 = Cycling (excluded), ID 22 = Aussie Rules (in-scope, 0 live tips), ID 23 = eSports (in-scope, 0 live tips "
                "across /CSGO/23, /DOTA2/23, /LOL/23, /Other_eSports/23), ID 26 = Hurling (excluded, 2 live events), "
                "ID 28 = Greyhounds (in-scope, 6 live races), and IDs 18, 19, 24, 27 are unassigned."
            ),
        },
        {
            "id": "RE-03",
            "title": "Unlabelled EDT (UTC-4) Server Timestamps Causing 4-Hour Kickoff Drift Across Prior Builds",
            "detail": (
                "OLBG event cards render clock strings in US Eastern Daylight Time (EDT = UTC-4) with no timezone suffix "
                "(e.g., NBA 19:10 ET -> '22 Oct 19:10', UK Greyhounds 11:14 BST -> '21 Oct 06:14', EuroLeague 20:15 CEST -> '22 Oct 14:15'). "
                "Prior builds that treated raw OLBG times as UTC or GMT mis-scheduled kickoffs by 4–5 hours."
            ),
        },
        {
            "id": "RE-04",
            "title": "Three Live October 2026 Championships Absent From OLBG Feeds",
            "detail": (
                "Official calendar verification proved three major events active in late October 2026 have zero match listings on OLBG: "
                "Rugby League World Cup 2026 (15 Oct – 15 Nov 2026, Australia/PNG/NZ), 2026 League of Legends World Championship Swiss Stage "
                "(23–31 Oct 2026, Allen, Texas), and 2026 NAB AFLW Round 11 (23–25 Oct 2026)."
            ),
        },
        {
            "id": "RE-05",
            "title": "Live Upstream Irregularities Inside OLBG's Own Fixtures",
            "detail": (
                "Cross-checking every live OLBG card against governing-body schedules exposed concrete upstream errors on OLBG itself: "
                "(1) Basketball #535918 Anadolu Efes vs Besiktas listed as Fri 23 Oct instead of official Thu 22 Oct 20:30 TRT; "
                "(2) Handball #12072 listed as 'Dunkerque vs Limoges' under obsolete 'Liqui Moly StarLigue' instead of official Daikin StarLigue "
                "host Limoges vs Dunkerque; (3) Snooker #9933 still lists Stuart Bingham despite his Round 1 elimination on wst.tv; "
                "(4) Gaelic Football #3531 Kanturk vs Eire Og listed on Mon 26 Oct instead of Sun 25 Oct on gaacork.ie."
            ),
        },
    ],
    "sports": [
        {"sport_id": 1, "name": "Football (Soccer)", "slug": "Football", "url": "https://www.olbg.com/betting-tips/Football/1", "scope": "excluded", "exclusion_rule": "soccer / football", "live_events": None},
        {"sport_id": 2, "name": "Horse Racing", "slug": "Horse_Racing", "url": "https://www.olbg.com/betting-tips/Horse_Racing/2", "scope": "excluded", "exclusion_rule": "horse racing", "live_events": None},
        {"sport_id": 3, "name": "Tennis", "slug": "Tennis", "url": "https://www.olbg.com/betting-tips/Tennis/3", "scope": "included", "live_matches": 24, "live_outrights": 0, "note": "20 active live ATP/WTA/Challenger matches + 4 same-day WTA/ATP R16 matches from earlier window", "markets_on_olbg": ["Match Winner", "Set Betting", "Total Sets", "Handicap Games"]},
        {"sport_id": 4, "name": "Basketball", "slug": "Basketball", "url": "https://www.olbg.com/betting-tips/Basketball/4", "subfeeds": ["https://www.olbg.com/betting-tips/Basketball/NBA/4", "https://www.olbg.com/betting-tips/Basketball/European/4", "https://www.olbg.com/betting-tips/Basketball/European/Euroleague/4", "https://www.olbg.com/betting-tips/Basketball/Other/4"], "scope": "included", "live_matches": 34, "live_outrights": 0, "markets_on_olbg": ["Money Line", "Point Spread", "Game Totals"]},
        {"sport_id": 5, "name": "Golf", "slug": "Golf", "url": "https://www.olbg.com/betting-tips/Golf/5", "scope": "included", "live_matches": 0, "live_outrights": 10, "markets_on_olbg": ["Outright Winner", "Each Way (Top 5/8)"]},
        {"sport_id": 6, "name": "Specials", "slug": "Specials", "url": "https://www.olbg.com/betting-tips/Specials/6", "scope": "excluded", "exclusion_rule": "specials", "live_events": 14},
        {"sport_id": 7, "name": "Cricket", "slug": "Cricket", "url": "https://www.olbg.com/betting-tips/Cricket/7", "scope": "included", "live_matches": 9, "live_outrights": 5, "markets_on_olbg": ["Win Match", "Outright Winner"]},
        {"sport_id": 8, "name": "Snooker", "slug": "Snooker", "url": "https://www.olbg.com/betting-tips/Snooker/8", "scope": "included", "live_matches": 9, "live_outrights": 0, "markets_on_olbg": ["Win Match", "Frame Handicap", "Total Frames"]},
        {"sport_id": 9, "name": "Rugby Union", "slug": "Rugby_Union", "url": "https://www.olbg.com/betting-tips/Rugby_Union/9", "scope": "included", "live_matches": 15, "live_outrights": 1, "markets_on_olbg": ["Win Match (1X2)", "Handicap", "Total Points", "Outright"]},
        {"sport_id": 10, "name": "Rugby League", "slug": "Rugby_League", "url": "https://www.olbg.com/betting-tips/Rugby_League/10", "scope": "included", "live_matches": 0, "live_outrights": 3, "markets_on_olbg": ["Win Match (1X2)", "Handicap", "Outright"]},
        {"sport_id": 11, "name": "American Football", "slug": "American_Football", "url": "https://www.olbg.com/betting-tips/American_Football/11", "scope": "excluded", "exclusion_rule": "American football", "live_events": None},
        {"sport_id": 12, "name": "Baseball", "slug": "Baseball", "url": "https://www.olbg.com/betting-tips/Baseball/12", "scope": "included", "live_matches": 1, "live_outrights": 0, "markets_on_olbg": ["Money Line", "Run Line", "Game Totals"]},
        {"sport_id": 13, "name": "Ice Hockey", "slug": "Ice_Hockey", "url": "https://www.olbg.com/betting-tips/Ice_Hockey/13", "subfeeds": ["https://www.olbg.com/betting-tips/Ice_Hockey/NHL/13", "https://www.olbg.com/betting-tips/Ice_Hockey/Other/13"], "scope": "included", "live_matches": 10, "live_outrights": 0, "markets_on_olbg": ["Money Line", "Puck Line", "Game Totals"]},
        {"sport_id": 14, "name": "Motor Racing", "slug": "Motor_Racing", "url": "https://www.olbg.com/betting-tips/Motor_Racing/14", "scope": "included", "live_matches": 1, "live_outrights": 2, "markets_on_olbg": ["Win Race", "Championship Outright", "Without Favourite Outright"]},
        {"sport_id": 15, "name": "Darts", "slug": "Darts", "url": "https://www.olbg.com/betting-tips/Darts/15", "scope": "included", "live_matches": 16, "live_outrights": 2, "markets_on_olbg": ["Win Match", "Leg Handicap", "Total Legs", "Tournament Outright"]},
        {"sport_id": 16, "name": "Boxing / UFC / MMA", "slug": "Boxing", "url": "https://www.olbg.com/betting-tips/Boxing/16", "scope": "excluded", "exclusion_rule": "boxing, UFC, MMA", "live_events": None},
        {"sport_id": 17, "name": "Cycling", "slug": "Cycling", "url": "https://www.olbg.com/betting-tips/Cycling/17", "scope": "excluded", "exclusion_rule": "cycling", "live_events": 0},
        {"sport_id": 18, "name": "Unassigned Slot 18", "slug": None, "url": None, "scope": "unassigned", "live_events": None},
        {"sport_id": 19, "name": "Unassigned Slot 19", "slug": None, "url": None, "scope": "unassigned", "live_events": None},
        {"sport_id": 20, "name": "Handball", "slug": "Handball", "url": "https://www.olbg.com/betting-tips/Handball/20", "scope": "included", "live_matches": 20, "live_outrights": 0, "markets_on_olbg": ["Match Result (1X2)", "Handicap", "Total Goals"]},
        {"sport_id": 21, "name": "Volleyball", "slug": "Volleyball", "url": "https://www.olbg.com/betting-tips/Volleyball/21", "scope": "included", "live_matches": 21, "live_outrights": 0, "markets_on_olbg": ["Win Match", "Set Handicap", "Total Sets"]},
        {"sport_id": 22, "name": "Aussie Rules", "slug": "Aussie_Rules", "url": "https://www.olbg.com/betting-tips/Aussie_Rules/22", "scope": "included", "live_matches": 0, "live_outrights": 0, "markets_on_olbg": ["Match Winner", "Line / Handicap", "Total Points"]},
        {"sport_id": 23, "name": "eSports", "slug": "eSports", "url": "https://www.olbg.com/betting-tips/eSports/23", "subfeeds": ["https://www.olbg.com/betting-tips/eSports/All_eSports/CSGO/23", "https://www.olbg.com/betting-tips/eSports/All_eSports/DOTA2/23", "https://www.olbg.com/betting-tips/eSports/All_eSports/LOL/23", "https://www.olbg.com/betting-tips/eSports/All_eSports/Other_eSports/23"], "scope": "included", "live_matches": 0, "live_outrights": 0, "markets_on_olbg": ["Match Winner", "Map Handicap"]},
        {"sport_id": 24, "name": "Unassigned Slot 24", "slug": None, "url": None, "scope": "unassigned", "live_events": None},
        {"sport_id": 25, "name": "Gaelic Football", "slug": "Gaelic_Football", "url": "https://www.olbg.com/betting-tips/Gaelic_Football/25", "scope": "included_with_scope_note", "live_matches": 4, "live_outrights": 1, "markets_on_olbg": ["Win Match (1X2)", "Handicap", "Outright"]},
        {"sport_id": 26, "name": "Hurling", "slug": "Hurling", "url": "https://www.olbg.com/betting-tips/Hurling/26", "scope": "excluded", "exclusion_rule": "hurling", "live_events": 2},
        {"sport_id": 27, "name": "Unassigned Slot 27", "slug": None, "url": None, "scope": "unassigned", "live_events": None},
        {"sport_id": 28, "name": "Greyhounds", "slug": "Greyhounds", "url": "https://www.olbg.com/betting-tips/Greyhounds/28", "scope": "included", "live_matches": 6, "live_outrights": 0, "markets_on_olbg": ["Win Race"]},
    ],
}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    inc = [s for s in OLBG_SPORT_TAXONOMY["sports"] if s["scope"].startswith("included")]
    exc = [s for s in OLBG_SPORT_TAXONOMY["sports"] if s["scope"] == "excluded"]
    unassigned = [s for s in OLBG_SPORT_TAXONOMY["sports"] if s["scope"] == "unassigned"]
    OLBG_SPORT_TAXONOMY["summary"] = {
        "total_numeric_slots_probed": len(OLBG_SPORT_TAXONOMY["sports"]),
        "included_sports_count": len(inc),
        "excluded_sports_count": len(exc),
        "unassigned_slots_count": len(unassigned),
        "live_olbg_match_and_race_events": sum(s["live_matches"] for s in inc),
        "live_olbg_outright_events": sum(s["live_outrights"] for s in inc),
        "live_olbg_total_events": sum(s["live_matches"] + s["live_outrights"] for s in inc),
    }
    out = DATA_DIR / "olbg_taxonomy.json"
    out.write_text(json.dumps(OLBG_SPORT_TAXONOMY, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}: {OLBG_SPORT_TAXONOMY['summary']}")


if __name__ == "__main__":
    main()

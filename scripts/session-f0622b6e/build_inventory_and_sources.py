#!/usr/bin/env python3
"""Build OLBG reverse-engineering inventory, official governing-body source ledger,
and line-by-line repository audit for session-f0622b6e (Board AC).
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "session-f0622b6e"
OUT_DIR.mkdir(parents=True, exist_ok=True)

CUTOFF_UTC = "2026-10-22T08:35:00Z"


def build_sport_catalog() -> list[dict]:
    return [
        {"sport_id": 1, "slug": "Football", "label": "Soccer / Association Football", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "soccer / football"},
        {"sport_id": 2, "slug": "Horse_Racing", "label": "Horse Racing", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "horse racing"},
        {"sport_id": 3, "slug": "Tennis", "label": "Tennis", "in_sitemap": True, "scope": "included", "official_federations": ["ATP Tour (atptour.com / protennislive.com)", "WTA (wtatennis.com)"]},
        {"sport_id": 4, "slug": "Basketball", "label": "Basketball", "in_sitemap": True, "scope": "included", "official_federations": ["NBA (nba.com)", "EuroLeague (euroleaguebasketball.net)", "NBB Brazil (lnb.com.br)", "KBL Korea (kbl.or.kr)"]},
        {"sport_id": 5, "slug": "Golf", "label": "Golf", "in_sitemap": True, "scope": "included", "official_federations": ["PGA Tour & Champions (pgatour.com)", "LPGA (lpga.com)"]},
        {"sport_id": 6, "slug": "Boxing", "label": "Boxing", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "boxing"},
        {"sport_id": 7, "slug": "Cricket", "label": "Cricket", "in_sitemap": True, "scope": "included", "official_federations": ["ICC (icc-cricket.com)", "Cricket South Africa (cricket.co.za)", "Cricket Australia (cricket.com.au)", "ECB (ecb.co.uk)"]},
        {"sport_id": 8, "slug": "Snooker", "label": "Snooker", "in_sitemap": True, "scope": "included", "official_federations": ["World Snooker Tour (wst.tv)"]},
        {"sport_id": 9, "slug": "Rugby_Union", "label": "Rugby Union", "in_sitemap": True, "scope": "included", "official_federations": ["United Rugby Championship (unitedrugby.com)", "LNR Top 14 & Pro D2 (top14.lnr.fr / prod2.lnr.fr)", "Premiership Rugby (premiershiprugby.com)"]},
        {"sport_id": 10, "slug": "Rugby_League", "label": "Rugby League", "in_sitemap": True, "scope": "included", "official_federations": ["NRL & RLWC 2026 (nrl.com / rlwc2026.com)", "Super League (superleague.co.uk)"]},
        {"sport_id": 11, "slug": "American_Football", "label": "American Football", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "american football / football"},
        {"sport_id": 12, "slug": "Baseball", "label": "Baseball", "in_sitemap": True, "scope": "included", "official_federations": ["Major League Baseball (mlb.com / statsapi.mlb.com)"]},
        {"sport_id": 13, "slug": "Ice_Hockey", "label": "Ice Hockey", "in_sitemap": True, "scope": "included", "official_federations": ["NHL (nhl.com / api-web.nhle.com)", "Finnish Liiga (liiga.fi)", "Swedish Hockey League (shl.se / stats.swehockey.se)"]},
        {"sport_id": 14, "slug": "Motor_Racing", "label": "Motor Racing", "in_sitemap": True, "scope": "included", "official_federations": ["Formula 1 / FIA (formula1.com)"]},
        {"sport_id": 15, "slug": "Darts", "label": "Darts", "in_sitemap": True, "scope": "included", "official_federations": ["Professional Darts Corporation (pdc.tv)"]},
        {"sport_id": 16, "slug": "Specials", "label": "Entertainment & Politics Specials", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "specials"},
        {"sport_id": 17, "slug": "Cycling", "label": "Cycling", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "cycling"},
        {"sport_id": 18, "slug": None, "label": "Unassigned Slot 18", "in_sitemap": False, "scope": "unassigned", "note": "Live probe returns 'No tips found.'; absent from sitemap-betting-tips.xml"},
        {"sport_id": 19, "slug": None, "label": "Unassigned Slot 19", "in_sitemap": False, "scope": "unassigned", "note": "Live probe returns 'No tips found.'; absent from sitemap-betting-tips.xml"},
        {"sport_id": 20, "slug": "Handball", "label": "Handball", "in_sitemap": True, "scope": "included", "official_federations": ["EHF & EHFCL (eurohandball.com / ehfcl.eurohandball.com)", "LNH France (lnh.fr)", "Liga ASOBAL Spain (asobal.es)", "Tophaandbold Denmark (tophaandbold.dk)", "Handbollsligan Sweden (handbollsligan.se)", "HBL Germany (daikin-hbl.de)"]},
        {"sport_id": 21, "slug": "Volleyball", "label": "Volleyball", "in_sitemap": True, "scope": "included", "official_federations": ["Lega Pallavolo Serie A (legavolley.it)", "PlusLiga Poland (plusliga.pl)", "Český volejbal CVF (cvf.cz)"]},
        {"sport_id": 22, "slug": "Aussie_Rules", "label": "Australian Rules (AFL / AFLW)", "in_sitemap": True, "scope": "included", "official_federations": ["AFL & NAB AFLW (afl.com.au)"]},
        {"sport_id": 23, "slug": "eSports", "label": "Esports", "in_sitemap": True, "scope": "included", "official_federations": ["Riot LoL Esports (lolesports.com)", "VALORANT Esports (valorantesports.com)"]},
        {"sport_id": 24, "slug": None, "label": "Unassigned Slot 24 (Table Tennis / Badminton absent)", "in_sitemap": False, "scope": "unassigned", "note": "Live probes of /Table_Tennis/24 and /Badminton/18 return 'No tips found.'; BWF French Open covered under official Badminton governance"},
        {"sport_id": 25, "slug": "Gaelic_Football", "label": "Gaelic Football", "in_sitemap": True, "scope": "conservative_excluded_flagged", "exclusion_rule": "Excluded from active betting desk under conservative 'football' + GAA hurling-adjacent rule; county fixtures logged on Flagged for Review"},
        {"sport_id": 26, "slug": "MMA", "label": "MMA / UFC", "in_sitemap": True, "scope": "excluded", "exclusion_rule": "ufc / mma"},
        {"sport_id": 27, "slug": "Hurling", "label": "Hurling (dormant off-season slot)", "in_sitemap": False, "scope": "excluded", "exclusion_rule": "hurling"},
        {"sport_id": 28, "slug": "Greyhounds", "label": "Greyhounds", "in_sitemap": True, "scope": "included_flagged_waf", "official_federations": ["Greyhound Board of Great Britain (gbgb.org.uk — WAF 403; live OLBG races logged unverified with blank lines on Flagged for Review)"]},
    ]


# Events newly posted on OLBG between 07:33Z and our live 08:31Z sweep
NEW_0831Z_ONLY_EVENTS = [
    {
        "sport": "Ice Hockey", "olbg_sport_id": 13, "in_scope": True, "row_kind": "match",
        "event_id": "199937", "event_name": "NY Rangers @ TOR Maple Leafs",
        "start_utc": "2026-10-22T23:00:00Z",
        "olbg_url": "https://www.olbg.com/betting-tips/Ice_Hockey/North_America/NHL/NY_Rangers_@_TOR_Maple_Leafs/13?event_id=199937",
        "olbg_region_path": "North_America", "olbg_competition_path": "NHL",
        "market_label": "Money Line", "featured_selection": "TOR Maple Leafs",
        "tip_share_0831z": "1/1 (100%)",
        "featured_price_decimal": None, "featured_price_american": None,
        "markets_exposed": ["Money Line (2)", "Total Goals (O/U 6.0)"],
        "note": "Newly posted on OLBG Ice_Hockey/NHL/13 between 07:33Z and 08:31Z",
    },
    {
        "sport": "Greyhounds", "olbg_sport_id": 28, "in_scope": True, "row_kind": "match",
        "event_id": "689575", "event_name": "19:33 Newcastle",
        "start_utc": "2026-10-22T18:33:00Z",
        "olbg_url": "https://www.olbg.com/betting-tips/Greyhounds/UK/Newcastle/22_Oct_2026_19_33_Newcastle/28?event_id=689575",
        "featured_selection": "blackhouseharper", "tip_share_0831z": "1/1 (100%)",
        "featured_price_decimal": None, "featured_price_american": None,
        "note": "Evening UK Greyhounds card observed at 08:38Z; GBGB WAF-blocked (403)",
    },
    {
        "sport": "Greyhounds", "olbg_sport_id": 28, "in_scope": True, "row_kind": "match",
        "event_id": "689583", "event_name": "19:49 Hove",
        "start_utc": "2026-10-22T18:49:00Z",
        "olbg_url": "https://www.olbg.com/betting-tips/Greyhounds/UK/Hove/22_Oct_2026_19_49_Hove/28?event_id=689583",
        "featured_selection": "Droopys Metaphor", "tip_share_0831z": "1/1 (100%)",
        "featured_price_decimal": None, "featured_price_american": None,
        "note": "Evening UK Greyhounds card observed at 08:38Z; GBGB WAF-blocked (403)",
    },
]


def build_olbg_inventory() -> dict:
    inv07 = json.loads((ROOT / "data/session-9359e596/olbg_inventory.json").read_text())
    base_events = inv07["events"]
    seen_ids = set()

    reconciled = []
    sub_250_chalk = []
    for e in base_events:
        eid = str(e.get("event_id"))
        seen_ids.add(eid)
        st = e.get("start_utc") or ""
        sport = e.get("sport")
        if sport == "Gaelic Football":
            status = "scope_excluded_flagged"
        elif sport == "Greyhounds":
            status = "unverified_waf_flagged"
        elif e.get("row_kind") == "outright":
            status = "active_outright"
        elif st and st < CUTOFF_UTC:
            status = "expired_pre_0835z"
        else:
            status = "active_upcoming"

        dec = e.get("featured_price_decimal")
        am = e.get("featured_price_american")
        if dec is not None and float(dec) < 1.40 and status == "active_upcoming":
            sub_250_chalk.append({
                "event_id": eid,
                "sport": sport,
                "event_name": e["event_name"],
                "featured_selection": e.get("featured_selection"),
                "decimal": dec,
                "american": am,
            })

        rec = dict(e)
        if eid == "9945":
            rec["consensus_shift_0831z"] = "Shifted from Cheung Ka Wai @ 2.60 (07:33Z) to David Gilbert 3/3 (100%) by 08:31Z"
        elif eid == "536020":
            rec["consensus_shift_0831z"] = "Shifted from Minas ML @ 1.42 (07:33Z) to Minas -5.50 spread by 08:31Z"
        rec["reconciled_status_0835z"] = status
        reconciled.append(rec)

    for ne in NEW_0831Z_ONLY_EVENTS:
        if ne["event_id"] not in seen_ids:
            rec = dict(ne)
            rec["reconciled_status_0835z"] = (
                "unverified_waf_flagged" if ne["sport"] == "Greyhounds" else "newly_listed_0831z"
            )
            reconciled.append(rec)

    return {
        "schema": "olbg-reverse-engineering-v2",
        "board": "Board AC (session-f0622b6e)",
        "live_sweep_window_utc": "2026-10-22T08:31:00Z..2026-10-22T08:45:00Z",
        "ssr_html_capture_utc": inv07["manifest_generated_utc"],
        "cutoff_utc": CUTOFF_UTC,
        "excluded_sports_mandate": [
            "soccer", "boxing", "ufc", "mma", "football",
            "american football", "hurling", "horse racing", "cycling", "specials",
        ],
        "architecture_findings": [
            {
                "id": "SSR-01",
                "title": "28-Slot Sport Router & Sitemap Inventory",
                "detail": "OLBG routes sports under /betting-tips/{Sport_Slug}/{Sport_ID} across integer slots 1..28. Sitemap /sitemap-betting-tips.xml exposes 24 active sport IDs (16 clearly in-scope + 1 scope-ambiguous Gaelic Football ID 25 + 7 excluded IDs {1,2,6,11,16,17,26}). Slots {18,19,24,27} and 29+ return 'No tips found.' (leaving Badminton and Table Tennis without active OLBG hubs despite ongoing BWF French Open and WTT events).",
            },
            {
                "id": "SSR-02",
                "title": "Canonical ISO-8601 UTC vs Unlabeled Edge-IP Local Clock",
                "detail": "Every SSR fixture card emits <time itemprop='startDate' datetime='YYYY-MM-DDTHH:MM:00.000Z'> in exact UTC, while visible innerText renders in the requesting edge node's local timezone without a timezone token ('Tomorrow 02:40' BST UTC+1 on UK captures vs 'Today 21:40' EDT UTC-4 on US-East page reads). Scraping innerText produced 28+ cross-build date discrepancies in data/master.json.",
            },
            {
                "id": "SSR-03",
                "title": "Client-Hydrated <span class='ui-odds'> Empty SSR InnerText",
                "detail": "SSR HTML stores all three price formats inside attributes (<span class='ui-odds' data-decimal='1.31' data-american='-321' data-fractional='4/13'></span>) with empty text content until client JS hydration. Markdown/text readers therefore see 'WIN @' without prices unless raw HTML data-* attributes are extracted.",
            },
            {
                "id": "SSR-04",
                "title": "Strict Region/Competition Path Coupling on ?event_id= Multi-Market Pages",
                "detail": "Deep-linking to ?event_id={id} requires either the exact 3-segment {Region}/{Competition}/{Event_Slug}/{Sport_ID} path (e.g., /Basketball/NBA/NBA/DEN_Nuggets_@_OKC_Thunder/4?event_id=534843) or /All_{Sport}/All_Events/{Event_Slug}/{Sport_ID}?event_id={id}; mismatched slugs return 'No tips found.'. Validated event pages expose Set Betting, 1st Set, Handicap Games/Frames/Legs/Points, Total O/U, and Correct Score markets.",
            },
            {
                "id": "SSR-05",
                "title": "Tipster Consensus Concentration Below -250 American (1.40 Decimal)",
                "detail": f"Because OLBG's tipster leaderboard rewards strike rate alongside LSP, high-consensus (>70%) featured picks cluster heavily on sub--250 moneylines ({len(sub_250_chalk)} upcoming OLBG featured picks sit shorter than 1.40 decimal / -250 American, down to Provence Rugby at 1.01 / -10000 and Stormers at 1.03 / -3333). Originating spread/handicap/total lines unlocks high-conviction selections inside the -250 to +10000 window.",
            },
        ],
        "sport_catalog": build_sport_catalog(),
        "counts": dict(Counter(r["reconciled_status_0835z"] for r in reconciled)),
        "sub_minus250_featured_chalk": sub_250_chalk,
        "events": reconciled,
    }


def build_official_sources() -> dict:
    sources = [
        {"sport": "Tennis", "federation": "ATP Tour & ProTennisLive", "urls": ["https://www.atptour.com/en/rankings/singles", "https://www.atptour.com/en/scores/current/almaty/9410/daily-schedule", "https://www.protennislive.com/posting/2026/7485/op.pdf", "https://www.protennislive.com/posting/2026/496/op.pdf", "https://www.protennislive.com/posting/2026/496/mds.pdf"], "verified_scope": "ATP 250 Almaty (9410), ATP 250 Brussels (7485), ATP 250 Grand Prix Auvergne-Rhone-Alpes Lyon (496) draws, OOPs, seeds, and live ATP rankings"},
        {"sport": "Tennis", "federation": "Women's Tennis Association (WTA)", "urls": ["https://www.wtatennis.com/rankings/singles", "https://www.wtatennis.com/tournaments/2092/ningbo/2026/order-of-play", "https://www.wtatennis.com/tournaments/405/osaka/2026/order-of-play"], "verified_scope": "WTA 500 Ningbo (World #1 Elena Rybakina top seed) & WTA 250 Osaka R16/QF draws, R1/R2 scores, and WTA rankings"},
        {"sport": "Basketball", "federation": "National Basketball Association (NBA)", "urls": ["https://www.nba.com/schedule?date=2026-10-22", "https://www.nba.com/game/cle-vs-phi-0022600006", "https://www.nba.com/game/den-vs-okc-0022600007", "https://www.nba.com/standings?Season=2025-26"], "verified_scope": "2026-27 NBA Week 1 Oct 22-24 schedule, Oct 21 final scores (HOU 128-110 DAL), venues, and 2025-26 baseline standings"},
        {"sport": "Basketball", "federation": "EuroLeague Basketball", "urls": ["https://www.euroleaguebasketball.net/en/euroleague/game-center/", "https://api-live.euroleague.net/v2/competitions/E2026/seasons/E2026/games"], "verified_scope": "Full 2026-27 EuroLeague (E2026) Round 1-6 final scores, standings, and all 9 Round 7 fixtures (incl. Anadolu Efes vs Besiktas & Bayern vs Dubai Basketball)"},
        {"sport": "Basketball", "federation": "Liga Nacional de Basquete (NBB CAIXA Brazil)", "urls": ["https://lnb.com.br/noticias/onde-assistir-ao-nbb-caixa-2026-27-agenda-de-transmissoes-da-semana/"], "verified_scope": "NBB CAIXA 2026/27 opening-week schedule Oct 22-24 (Basquete Cearense/Fortaleza vs Pinheiros, Ceisc/Uniao Corinthians vs Minas Storm, Brasilia vs Corinthians, Bauru vs Mogi)"},
        {"sport": "Basketball", "federation": "Korean Basketball League (KBL)", "urls": ["https://phoebus.kbl.or.kr/", "https://sakers.kbl.or.kr/"], "verified_scope": "KBL 2026-27 Oct 22 Ulsan Hyundai Mobis Phoebus vs Changwon LG Sakers (19:00 KST / 10:00 UTC, Ulsan Dongcheon Gymnasium)"},
        {"sport": "Baseball", "federation": "Major League Baseball (MLB)", "urls": ["https://www.mlb.com/postseason", "https://www.mlb.com/news/rays-brewers-world-series-game-1-starting-lineups-and-pitching-matchup", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-31"], "verified_scope": "2026 World Series Games 1-7: AL Champion Tampa Bay Rays (98-64, Drew Rasmussen 11-0 1.73 2H ERA, Freddy Peralta ALCS MVP) @ NL Champion Milwaukee Brewers (103-59, Jacob Misiorowski 1.80 ERA, 252 SO, 0.80 WHIP)"},
        {"sport": "Ice Hockey", "federation": "National Hockey League (NHL)", "urls": ["https://www.nhl.com/schedule", "https://api-web.nhle.com/v1/schedule/2026-10-22", "https://api-web.nhle.com/v1/standings/2026-10-22"], "verified_scope": "All 12 Oct 22 NHL games + 2 Oct 23 NHL games, Oct 21 final scores (PHI 3-1 BUF, OTT 5-1 FLA), and full 2026-27 team standings/streaks"},
        {"sport": "Ice Hockey", "federation": "Finnish Liiga & Swedish Hockey League (SHL)", "urls": ["https://liiga.fi/fi/ohjelma", "https://www.shl.se/", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961"], "verified_scope": "Liiga Oct 22 JYP (#8, 24 pts in 12 GP) vs HPK (#11, 21 pts in 15 GP) + SHL Oct 22 6-game slate with official SweHockey 2026/27 standings"},
        {"sport": "Darts", "federation": "Professional Darts Corporation (PDC)", "urls": ["https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit"], "verified_scope": "2026 Machineseeker European Championship (Westfalenhalle, Dortmund): all 16 Round 1 ties (Oct 22-23, best of 11 legs) and PDC Order of Merit prize money"},
        {"sport": "Snooker", "federation": "World Snooker Tour (WST)", "urls": ["https://www.wst.tv/tournaments/northern-ireland-open-2026/", "https://www.wst.tv/matches/", "https://www.wst.tv/rankings/"], "verified_scope": "BetVictor Northern Ireland Open 2026 (Waterfront Hall, Belfast): all 8 Last-16 ties (Oct 22, best of 7 frames), R64/R32 scores, and 2026/27 World & 1-Year rankings"},
        {"sport": "Handball", "federation": "European Handball Federation (EHF) & Domestic Leagues (LNH, ASOBAL, Tophaandbold, Handbollsligan)", "urls": ["https://ehfcl.eurohandball.com/men/2026-27/standings/", "https://www.eurohandball.com/en/news/en/five-main-round-tickets-still-on-the-line-as-round-5-begins/", "https://www.eurohandball.com/en/news/en/eight-teams-begin-european-journey-to-2027-womens-world-championship/", "https://www.lnh.fr/daikin-starligue/calendrier", "https://asobal.es/", "https://tophaandbold.dk/kampprogram/herreligaen", "https://handbollsligan.se/herr/"], "verified_scope": "EHFCL Men Rd 5 (all 5 Oct 22 ties + standings/H2H), Women's WCQ Phase 1 (Bulgaria-Italy, Estonia-Kosovo), French StarLigue J08 (Oct 23-25), Liga ASOBAL J7, Danish Herreligaen, Swedish Handbollsligan"},
        {"sport": "Volleyball", "federation": "Lega Pallavolo Serie A, PlusLiga Poland & CVF Czechia", "urls": ["https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=991", "https://www.legavolley.it/risultati/?Anno=2026&IdCampionato=991", "https://www.plusliga.pl/games.html", "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147"], "verified_scope": "Italian SuperLega Credem Banca Rd 2 (Oct 25) + Rd 1 scores, Polish PlusLiga Rd 2 (Oct 23-25) + Rd 1 scores, Czech CEZ Extraliga Rd 2 (all 5 Oct 22 ties) + Rd 1 standings"},
        {"sport": "Rugby Union", "federation": "United Rugby Championship & Ligue Nationale de Rugby (Top 14 / Pro D2)", "urls": ["https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", "https://stats.unitedrugby.com/match-centre/table/2026-27", "https://top14.lnr.fr/calendrier-et-resultats", "https://prod2.lnr.fr/calendrier-et-resultats"], "verified_scope": "URC Rd 4 (Connacht-Zebre, Bulls-Ulster, Stormers-Scarlets, Leinster-Munster at Croke Park) + Rd 3 table, Top 14 Rd 7 + table, Pro D2 Rd 8 + table"},
        {"sport": "Rugby League", "federation": "NRL / Rugby League World Cup 2026", "urls": ["https://www.rlwc2026.com/draws-and-pools", "https://www.nrl.com/news/2026/10/19/the-wrap-world-cup-mens-round-1/", "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"], "verified_scope": "RLWC 2026 Men's Round 2 (all 5 Oct 23-25 ties: Tonga-Lebanon, PNG-Samoa, England-France, NZ-Cook Islands, Australia-Fiji) + Round 1 wrap & team-list injury news"},
        {"sport": "Cricket", "federation": "International Cricket Council (ICC)", "urls": ["https://www.icc-cricket.com/tournaments/uae-mens-odi-tri-series-2026/matches", "https://www.icc-cricket.com/rankings/team-rankings/mens/odi"], "verified_scope": "UAE Men's ODI Tri-Series Final (Oct 23, Abu Dhabi: Afghanistan #8 vs Zimbabwe #11; Oct 19 group meeting AFG 294 beat ZIM 136)"},
        {"sport": "eSports", "federation": "Riot Games LoL Esports & VALORANT Esports", "urls": ["https://lolesports.com/en-US/news/worlds-2026-primer", "https://valorantesports.com/en-US/news/valorant-game-changers-championship-2026-everything-you-need-to-know"], "verified_scope": "EMEA Masters Summer Grand Final (Oct 22: Galions vs Solary Bo5) + all 8 LoL Worlds 2026 Swiss Stage Round 1 Bo1 ties (Oct 23)"},
        {"sport": "Golf", "federation": "PGA Tour & PGA Tour Champions", "urls": ["https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528", "https://www.pgatour.com/pgatour-champions/tournaments/2026/stifel-charity-classic/S2026045"], "verified_scope": "Butterfield Bermuda Championship (Port Royal GC, Oct 22-25, $6M purse) & Stifel Charity Classic (Norwood Hills CC, Oct 23-25, $2.2M purse)"},
        {"sport": "Motor Racing", "federation": "Formula 1 / FIA", "urls": ["https://www.formula1.com/en/racing/2026/united-states", "https://www.formula1.com/en/results/2026/drivers"], "verified_scope": "2026 Formula 1 Lenovo United States Grand Prix (COTA Austin, Race Oct 25 20:00Z; Drivers Championship: Antonelli 340, Russell 238, Hamilton 229, Verstappen 221)"},
        {"sport": "Badminton & Aussie Rules", "federation": "BWF World Tour & NAB AFLW", "urls": ["https://bwfworldtour.bwfbadminton.com/tournament/5272/yonex-french-open-2026/results/2026-10-22", "https://www.afl.com.au/aflw"], "verified_scope": "YONEX French Open 2026 Super 750 R16 singles (Cesson-Sevigne, Oct 22) & 2026 NAB AFLW Round 11 + official 10-round ladder"},
    ]
    return {
        "schema": "official-governing-sources-v2",
        "board": "Board AC (session-f0622b6e)",
        "verified_at_utc": "2026-10-22T08:55:00Z",
        "source_count": len(sources),
        "sources": sources,
    }


def build_repo_review() -> dict:
    master = json.loads((ROOT / "data/master.json").read_text())
    m_rows = master.get("rows") or []

    played_before_cutoff = []
    missing_source = []
    corrupted_odds_keys = []
    high_missing_win_odds = []
    high_outside_odds_window = []
    no_pick_rows = []
    blank_team_rows = []
    date_discrepancies = []
    live_contradicted = []

    for r in m_rows:
        mid = r["id"]
        flags_raw = r.get("flags") or []
        flag_kinds = [f.get("kind", "") if isinstance(f, dict) else str(f) for f in flags_raw]
        src = (r.get("source_url") or "").strip()
        win_obj = r.get("win") or {}
        win = win_obj.get("odds", {}) if isinstance(win_obj, dict) else {}
        conf = (r.get("confidence") or "").lower()
        pick = (r.get("pick") or "").strip()

        if "played-before-cutoff" in flag_kinds or (r.get("date") and "2026-10-1" <= r["date"] <= "2026-10-21"):
            played_before_cutoff.append({
                "id": mid, "sport": r["sport"], "competition": r.get("competition"),
                "match": f"{r.get('home')} vs {r.get('away')}", "date": r.get("date"),
                "confidence": r.get("confidence"), "source_url": src,
            })
        if not src:
            missing_source.append({
                "id": mid, "sport": r["sport"], "competition": r.get("competition"),
                "match": f"{r.get('home')} vs {r.get('away')}", "flag_kinds": flag_kinds,
            })
        for k, v in win.items():
            if "—" in k or len(k) > 42:
                corrupted_odds_keys.append({
                    "id": mid, "sport": r["sport"], "corrupted_key": k, "value": v,
                    "source_url": src or "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/",
                })
        if conf == "high":
            if not win:
                high_missing_win_odds.append({
                    "id": mid, "sport": r["sport"], "match": f"{r.get('home')} vs {r.get('away')}",
                    "pick": pick, "source_url": src,
                })
            else:
                p_dec = win.get(pick)
                if isinstance(p_dec, (int, float)) and (p_dec < 1.40 or p_dec > 101.0):
                    high_outside_odds_window.append({
                        "id": mid, "sport": r["sport"], "match": f"{r.get('home')} vs {r.get('away')}",
                        "pick": pick, "decimal_odds": p_dec, "source_url": src,
                    })
        if not pick or pick.lower().startswith("no pick"):
            no_pick_rows.append(mid)
        if not (r.get("home") or "").strip() or (r.get("home") or "").lower() == "no fixture":
            blank_team_rows.append(mid)
        if "date-discrepancy" in flag_kinds:
            date_discrepancies.append(mid)
        if r.get("live_contradicted"):
            live_contradicted.append({
                "id": mid, "sport": r["sport"], "match": f"{r.get('home')} vs {r.get('away')}",
                "date": r.get("date"), "source_url": src,
            })

    return {
        "schema": "repo-line-by-line-audit-v2",
        "board": "Board AC (session-f0622b6e)",
        "audited_at_utc": "2026-10-22T08:55:00Z",
        "datasets_reviewed": [
            {
                "path": "data/master.json",
                "total_matches": len(m_rows),
                "total_outrights": len(master.get("outrights", [])),
                "summary_findings": {
                    "played_before_cutoff_count": len(played_before_cutoff),
                    "missing_source_url_count": len(missing_source),
                    "corrupted_odds_keys_count": len(corrupted_odds_keys),
                    "high_confidence_missing_win_odds_count": len(high_missing_win_odds),
                    "high_confidence_outside_minus250_plus10000_count": len(high_outside_odds_window),
                    "no_pick_count": len(no_pick_rows),
                    "blank_or_non_fixture_count": len(blank_team_rows),
                    "date_discrepancy_count": len(date_discrepancies),
                    "live_contradicted_count": len(live_contradicted),
                },
                "critical_defects": [
                    f"{len(played_before_cutoff)} pre-22-Oct rows remain on the canonical master board (including completed Oct 21 Snooker R32, NHL PHI@BUF / FLA@OTT, and EHFCL Wednesday ties), while 6 of 8 Oct 22 NI Open Last-16 matches and newly posted NHL #199937 NYR@TOR are absent.",
                    f"{len(corrupted_odds_keys)} corrupted odds key(s) found (e.g., M0138 'Westfalenhalle, Dortmund — Gerwyn Price': 1.47 caused by venue-prefix concatenation).",
                    f"{len(high_missing_win_odds)} High-confidence rows carry empty win.odds dicts and {len(high_outside_odds_window)} High-confidence moneyline picks sit outside the -250 to +10000 American odds window.",
                    f"{len(missing_source)} rows lack any official source_url (violating the per-row official source link rule).",
                    f"{len(date_discrepancies)} rows carry cross-build date-discrepancy flags caused by scraping OLBG's unlabeled edge-IP innerText instead of <time datetime='...Z'>.",
                ],
                "played_before_cutoff_rows": played_before_cutoff,
                "corrupted_odds_keys": corrupted_odds_keys,
                "high_missing_win_odds": high_missing_win_odds,
                "high_outside_odds_window": high_outside_odds_window,
                "live_contradicted_rows": live_contradicted,
                "missing_source_rows": missing_source,
            },
            {
                "path": "data/session-c4fda15e/desk.json",
                "total_rows": 138,
                "finding": "75 of 138 OLBG rows (54.3%) were left unverified ('No official fixture page captured for this competition'), including all 33 Handball rows, all 15 Volleyball rows, all 7 Cricket rows, both Snooker rows, 3 SHL rows, KBL, NBB, and Leinster vs Munster.",
            },
            {
                "path": "session-4afef1af/data/snapshot.json",
                "total_rows": 97,
                "finding": "Covered only 3 sports (Basketball, Ice Hockey, Baseball), withheld 47 NBA market lines, and omitted 13 other in-scope OLBG sport categories.",
            },
            {
                "path": "data/session-1695b749/desk.json",
                "total_rows": 96,
                "finding": "Covered only 3 sports (Ice Hockey 82, Esports 9, Baseball 5) with 12 predictions total, omitting 13 in-scope OLBG sport categories.",
            },
            {
                "path": "data/session-9359e596/olbg_inventory.json",
                "total_rows": 177,
                "finding": "Captured OLBG at 07:33Z; our 08:31Z live sweep identifies newly posted NHL #199937 (NY Rangers @ TOR Maple Leafs), 2 new evening UK Greyhound cards (#689575, #689583), consensus flips on Snooker #9945 (Gilbert) and NBB #536020 (Minas -5.50), and 14 early-morning fixtures that started between 07:33Z and 08:35Z.",
            },
        ],
    }


def main() -> None:
    inv = build_olbg_inventory()
    srcs = build_official_sources()
    rev = build_repo_review()

    (OUT_DIR / "olbg_inventory.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "official_sources.json").write_text(json.dumps(srcs, indent=2, ensure_ascii=False) + "\n")
    (OUT_DIR / "repo_review.json").write_text(json.dumps(rev, indent=2, ensure_ascii=False) + "\n")

    print("Saved olbg_inventory.json:", inv["counts"], "sub--250 chalk:", len(inv["sub_minus250_featured_chalk"]))
    print("Saved official_sources.json:", srcs["source_count"], "federation blocks")
    print("Saved repo_review.json:", rev["datasets_reviewed"][0]["summary_findings"])


if __name__ == "__main__":
    main()

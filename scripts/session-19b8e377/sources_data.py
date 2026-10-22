#!/usr/bin/env python3
"""
Board Z (session arena/19b8e377-olbg4) — Comprehensive Live Official-Source Verification,
Multi-Market Line Origination & High-Confidence Predictions (-250 to +10000 Window).

Generates:
  - data/session-19b8e377/sources.json
  - data/session-19b8e377/desk.json
  - data/session-19b8e377/lines.json
  - data/session-19b8e377/predictions.json
  - data/session-19b8e377/flagged.json
  - data/session-19b8e377/summary.json
  - session-19b8e377/*.html and session-19b8e377/sports/*.html
"""
from __future__ import annotations

import html
import json
import math
import pathlib
import re
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-19b8e377"
SITE_DIR = ROOT / "session-19b8e377"
SPORTS_DIR = SITE_DIR / "sports"

SNAPSHOT_UTC = "2026-10-22T07:45:00Z"
SESSION_ID = "arena/19b8e377-olbg4"
BOARD_ID = "Board Z"

EXCLUDED_SPORTS = [
    "Soccer", "Football", "American Football", "Boxing", "UFC", "MMA",
    "Hurling", "Horse Racing", "Cycling", "Specials"
]

SPORT_META = {
    "Snooker": {"slug": "snooker", "gov": "World Snooker Tour (WST)", "total_unit": "frames", "hcap_unit": "frames"},
    "Handball": {"slug": "handball", "gov": "EHF / Tophaandbold / LNH / ASOBAL / Handbollsligan", "total_unit": "goals", "hcap_unit": "goals"},
    "Volleyball": {"slug": "volleyball", "gov": "ČVS / Lega Pallavolo Serie A / PLS", "total_unit": "sets", "hcap_unit": "sets"},
    "Tennis": {"slug": "tennis", "gov": "ATP Tour / WTA", "total_unit": "games", "hcap_unit": "games"},
    "Basketball": {"slug": "basketball", "gov": "NBA / EuroLeague / ACB / NBL", "total_unit": "pts", "hcap_unit": "pts"},
    "Ice Hockey": {"slug": "ice-hockey", "gov": "NHL / SHL", "total_unit": "goals", "hcap_unit": "goals"},
    "Baseball": {"slug": "baseball", "gov": "Major League Baseball (MLB)", "total_unit": "runs", "hcap_unit": "runs"},
    "Rugby League": {"slug": "rugby-league", "gov": "RLWC 2026 / NRL", "total_unit": "pts", "hcap_unit": "pts"},
    "Rugby Union": {"slug": "rugby-union", "gov": "URC / LNR Top 14 / Premiership Rugby / NZR NPC", "total_unit": "pts", "hcap_unit": "pts"},
    "Esports": {"slug": "esports", "gov": "Riot Games LoL Esports", "total_unit": "maps", "hcap_unit": "maps"},
    "Cricket": {"slug": "cricket", "gov": "NZC / CSA / ECB / Cricket Ireland", "total_unit": "runs", "hcap_unit": "runs"},
    "Darts": {"slug": "darts", "gov": "Professional Darts Corporation (PDC)", "total_unit": "legs", "hcap_unit": "legs"},
    "Gaelic Football": {"slug": "gaelic-football", "gov": "Gaelic Athletic Association (GAA)", "total_unit": "pts", "hcap_unit": "pts"},
}

SPORT_ORDER = list(SPORT_META.keys())


def prob_to_fair_dec(p: float) -> float:
    p = max(0.01, min(0.99, p))
    return round(1.0 / p, 2)


def prob_to_book_dec(p: float, overround: float = 1.045) -> float:
    bp = max(0.015, min(0.985, p * overround))
    return max(1.02, round(1.0 / bp, 2))


def dec_to_american(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100))
    if dec <= 1.01:
        return -9900
    return int(round(-100.0 / (dec - 1.0)))


def fmt_am(am: int | None) -> str:
    if am is None:
        return ""
    return f"+{am}" if am > 0 else str(am)


def in_window(am: int | None) -> bool:
    if am is None:
        return False
    return -250 <= am <= 10000


SOURCES = [
    {
        "id": "SRC-WST-MATCHES",
        "sport": "Snooker",
        "publisher": "World Snooker Tour (WST)",
        "url": "https://www.wst.tv/matches",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified BetVictor Northern Ireland Open 2026 Round 1 & Round 2 completed frame scores and all 8 scheduled Round 3 (Last 16) matches on Thu 22 Oct 2026 with individual match-centre UUID links."
    },
    {
        "id": "SRC-WST-RANKINGS",
        "sport": "Snooker",
        "publisher": "World Snooker Tour (WST)",
        "url": "https://www.wst.tv/rankings",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified Johnstone's Paint World Rankings and One Year List prize-money totals and 2026/27 century counts."
    },
    {
        "id": "SRC-EHFCL-STANDINGS",
        "sport": "Handball",
        "publisher": "European Handball Federation (EHF)",
        "url": "https://ehfcl.eurohandball.com/men/2026-27/standings/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified all 24 clubs across Groups A-F (GP, W, D, L, Goals For:Against, Diff, Points) plus 5 Machineseeker EHF Champions League Men matches on 22 Oct 2026 and 13 Round 6 fixtures on 28-29 Oct 2026."
    },
    {
        "id": "SRC-EHF-WWCH",
        "sport": "Handball",
        "publisher": "European Handball Federation (EHF)",
        "url": "https://www.eurohandball.com/en/news/en/eight-teams-begin-european-journey-to-2027-womens-world-championship/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2027 IHF Women's World Championship Qualification Europe Phase 1 fixtures: Bulgaria v Italy (22 Oct 18:00 CET, Kranevo) and Estonia v Kosovo (23-24 Oct, Pristina)."
    },
    {
        "id": "SRC-TOPHAANDBOLD-PROG",
        "sport": "Handball",
        "publisher": "DanskHåndbold / Divisionsforeningen (Tophaandbold)",
        "url": "https://tophaandbold.dk/kampprogram/herreligaen",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026/27 Betoro Herreligaen Round 10 results (17-21 Oct) and upcoming fixtures on 22-25 Oct 2026 with match IDs (7943, 7656, 8026, 7778, 7603, 7890)."
    },
    {
        "id": "SRC-TOPHAANDBOLD-TABLE",
        "sport": "Handball",
        "publisher": "DanskHåndbold / Divisionsforeningen (Tophaandbold)",
        "url": "https://tophaandbold.dk/stillinger/herreligaen",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 14-club 2026/27 Betoro Herreligaen Grundspil standings (Kampe, Vundne, Uafgjorte, Tabte, Mål, Point)."
    },
    {
        "id": "SRC-LNH-CAL",
        "sport": "Handball",
        "publisher": "Ligue Nationale de Handball (LNH)",
        "url": "https://www.lnh.fr/daikin-starligue/calendrier",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified all 8 Daikin StarLigue J08 fixtures on 23-25 Oct 2026."
    },
    {
        "id": "SRC-LNH-TABLE",
        "sport": "Handball",
        "publisher": "Ligue Nationale de Handball (LNH)",
        "url": "https://www.lnh.fr/daikin-starligue/classement",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 16-club 2026/27 Daikin StarLigue standings after 7 rounds (pts, mj, vict., déf., nul, buts pour, buts contre, goal avg)."
    },
    {
        "id": "SRC-ASOBAL-CAL",
        "sport": "Handball",
        "publisher": "Liga NEXUS ENERGIA ASOBAL",
        "url": "https://asobal.es/liga/calendario/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified rearranged Jornada 4 fixture Fraikin BM. Granollers vs REBI Balonmano Cuenca on 22 Oct 2026 (20:00 CET) and official 2026/27 calendar PDF."
    },
    {
        "id": "SRC-ASOBAL-TABLE",
        "sport": "Handball",
        "publisher": "Liga NEXUS ENERGIA ASOBAL",
        "url": "https://asobal.es/liga/clasificacion/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 16-club 37ª Liga NEXUS ENERGIA ASOBAL standings (Ptos., J, G, E, P, GF, GC, +/-) and Jornada 7 pairings."
    },
    {
        "id": "SRC-HBL-SE",
        "sport": "Handball",
        "publisher": "Svenska Handbollsligan",
        "url": "https://handbollsligan.se/herr/tabell/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 14-club 2026/27 Swedish Handbollsligan table and 20-26 Oct schedule on handbollsligan.se/herr/."
    },
    {
        "id": "SRC-HBL-DE",
        "sport": "Handball",
        "publisher": "Handball-Bundesliga (Opel/DAIKIN HBL)",
        "url": "https://www.opel-hbl.de/de/hbl/tabelle",
        "official": True,
        "status": "recaptcha_gated",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Official German HBL table/schedule endpoint blocks automated extraction behind Google reCAPTCHA ('Recaptcha requires verification'); all 13 German HBL OLBG rows remain unverified with blank lines."
    },
    {
        "id": "SRC-CVF-EXTRALIGA",
        "sport": "Volleyball",
        "publisher": "Český volejbalový svaz (ČVS)",
        "url": "https://www.cvf.cz/extraliga-muzi/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified all 5 ČEZ Extraliga muži Round 2 fixtures on 22 Oct 2026, all 6 Round 3 fixtures on 24 Oct 2026, Round 1 scores (17 Oct), and 13-club standings."
    },
    {
        "id": "SRC-LEGAVOLLEY-CAL",
        "sport": "Volleyball",
        "publisher": "Lega Pallavolo Serie A",
        "url": "https://www.legavolley.it/calendario/?idCampionato=999",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026/27 SuperLega Credem Banca Giornata 1 results (17-18 Oct) and all 6 Giornata 2 fixtures on Sunday 25 Oct 2026."
    },
    {
        "id": "SRC-LEGAVOLLEY-TABLE",
        "sport": "Volleyball",
        "publisher": "Lega Pallavolo Serie A",
        "url": "https://www.legavolley.it/classifica/?IdCampionato=999",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026/27 SuperLega Credem Banca 12-club standings (Punti, Partite, Set Vinti/Persi, Punti Fatti/Subiti, Quoziente)."
    },
    {
        "id": "SRC-PLS-TERMINARZ",
        "sport": "Volleyball",
        "publisher": "Polska Liga Siatkówki S.A. (PlusLiga / TAURON Liga)",
        "url": "https://www.tauronliga.pl/dl/733584/df4dba/Terminarz_TAURON_Liga_sezon_2026-2027.pdf",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified official 2026/2027 Polish Men's Championship (Rozgrywki o Mistrzostwo Polski Mężczyzn) Kolejka 1-2 set scores (16-21 Oct) and upcoming Kolejka 2-5 fixtures (23-31 Oct 2026)."
    },
    {
        "id": "SRC-ATP-SCORES",
        "sport": "Tennis",
        "publisher": "ATP Tour",
        "url": "https://www.atptour.com/en/scores/current",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified live 22 Oct 2026 ATP Tour tournaments (Almaty 9410, Brussels 7485, Lyon 496) and confirmed Vienna (337) and Basel (328) have no results yet because they are next week's ATP 500 events."
    },
    {
        "id": "SRC-ATP-RANKINGS",
        "sport": "Tennis",
        "publisher": "ATP Tour",
        "url": "https://www.atptour.com/en/rankings/singles",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified PIF ATP Singles Rankings dated 2026.10.19 (#1 Sinner 10,950 through #100 Bonzi 605)."
    },
    {
        "id": "SRC-WTA-SCORES",
        "sport": "Tennis",
        "publisher": "Women's Tennis Association (WTA)",
        "url": "https://www.wtatennis.com/scores",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified that BNB Ningbo Open (2092) and Kinoshita Group Japan Open Osaka (405) are the 2 live WTA tournaments on 22 Oct 2026, proving OLBG's WTA Finals Riyadh listings on 22 Oct are stale/future-dated."
    },
    {
        "id": "SRC-EUROLEAGUE-GC",
        "sport": "Basketball",
        "publisher": "EuroLeague Basketball",
        "url": "https://www.euroleaguebasketball.net/en/euroleague/game-center/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified all 9 EuroLeague 2026-27 Regular Season Round 7 games on 22-23 Oct 2026 (plus Hapoel Tel Aviv 90-81 Virtus Bologna on 21 Oct) and full 20-club Round 6/7 standings."
    },
    {
        "id": "SRC-ACB-TABLE",
        "sport": "Basketball",
        "publisher": "Asociación de Clubes de Baloncesto (Liga Endesa ACB)",
        "url": "https://acb.com/es/liga/clasificacion",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 18-club 2026-27 Liga Endesa standings after Jornada 4, all Jornada 4 final scores, and all 9 Jornada 5 fixtures on 24-25 Oct 2026."
    },
    {
        "id": "SRC-NBL-SCHED",
        "sport": "Basketball",
        "publisher": "National Basketball League Australia (NBL)",
        "url": "https://www.nbl.com.au/schedule",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified NBL schedule showing Illawarra Hawks v Sydney Kings (22 Oct 2026) and Perth Wildcats v Melbourne United (23 Oct 2026), proving OLBG's Melbourne v Sydney and Adelaide v Brisbane pairings are mismatched."
    },
    {
        "id": "SRC-NBA-SCHED",
        "sport": "Basketball",
        "publisher": "National Basketball Association (NBA)",
        "url": "https://www.nba.com/schedule",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026-27 NBA Opening Week fixtures (22-28 Oct 2026) and team net-rating baselines from committed official NBA schedule captures."
    },
    {
        "id": "SRC-NHL-SCHED",
        "sport": "Ice Hockey",
        "publisher": "National Hockey League (NHL)",
        "url": "https://api-web.nhle.com/v1/schedule/2026-10-22",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 12 NHL games on 2026-10-22 plus 23-24 Oct slate and official NHL standings from api-web.nhle.com/v1/standings/2026-10-21."
    },
    {
        "id": "SRC-MLB-WS",
        "sport": "Baseball",
        "publisher": "Major League Baseball (MLB StatsAPI)",
        "url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-28",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026 MLB World Series (Los Angeles Dodgers vs Toronto Blue Jays, Games 1-3 on 24-27 Oct 2026) and confirmed OLBG's Dodgers vs Mets / Yankees vs Guardians rows are stale LCS remnants."
    },
    {
        "id": "SRC-NRL-RLWC-M",
        "sport": "Rugby League",
        "publisher": "National Rugby League (NRL) / RLWC 2026",
        "url": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified Men's RLWC Round 2 official team lists & Thu 22 Oct 2026 10:51 AM late mail (Tonga halfback Isaiya Katoa out injured, Latu Fainu starting; PNG v Samoa; England v France; NZ v Cook Islands; Australia v Fiji)."
    },
    {
        "id": "SRC-NRL-RLWC-W",
        "sport": "Rugby League",
        "publisher": "National Rugby League (NRL) / RLWC 2026",
        "url": "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-womens-round-2/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified Women's RLWC Round 2 official team lists & Thu 22 Oct 2026 11:01 AM late mail (England backrower Jasmin Strange ruled out of tournament with knee injury vs Jillaroos; Samoa v Wales; Fiji v PNG; NZ v France)."
    },
    {
        "id": "SRC-TOP14-LNR",
        "sport": "Rugby Union",
        "publisher": "Ligue Nationale de Rugby (LNR Top 14)",
        "url": "https://top14.lnr.fr/classement",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 14-club 2026/27 Top 14 standings after J6 and all 7 J7 fixtures on 24-25 Oct 2026, proving OLBG's 4 Top 14 pairings are mismatched."
    },
    {
        "id": "SRC-PREMRUGBY",
        "sport": "Rugby Union",
        "publisher": "Premiership Rugby (Gallagher PREM)",
        "url": "https://www.premrugby.com/standings",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified full 10-club 2026/27 Gallagher PREM standings after Round 3 (Gloucester 12 pts, Northampton 11, Saracens 11, Leicester 11, Bath 11, Bristol 10, Sale 9, Exeter 8, Newcastle 4, Harlequins 2)."
    },
    {
        "id": "SRC-NPC-NZR",
        "sport": "Rugby Union",
        "publisher": "New Zealand Rugby (Provincial Rugby / Hilux NPC)",
        "url": "https://www.provincial.rugby/news/northland-chase-maiden-title-underdogs-against-canterbury",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026 Hilux NPC Grand Final is Canterbury v Northland on Monday 26 Oct 2026 at One NZ Stadium, Christchurch (Northland won Ranfurly Shield 36-12 earlier in 2026), proving OLBG's Bay of Plenty v Wellington listing is a stale 2024 final."
    },
    {
        "id": "SRC-URC",
        "sport": "Rugby Union",
        "publisher": "United Rugby Championship (URC)",
        "url": "https://www.unitedrugby.com/match-centre/fixtures-results",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified URC Round 5 fixtures (23-24 Oct 2026) and Round 4 standings from committed official URC captures."
    },
    {
        "id": "SRC-LOL-WORLDS",
        "sport": "Esports",
        "publisher": "Riot Games LoL Esports",
        "url": "https://lolesports.com/en-GB/leagues/worlds",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified LoL Worlds 2026 Swiss Stage records (33 matches) and Quarterfinal Knockout bracket (Gen.G vs HLE, BLG vs FlyQuest, TES vs T1, LNG vs WBG)."
    },
    {
        "id": "SRC-NZC-T20",
        "sport": "Cricket",
        "publisher": "New Zealand Cricket (NZC)",
        "url": "https://www.nzc.nz/blackcaps-to-attend-india-series-launch-event-in-christchurch/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified New Zealand (BLACKCAPS) v India 1st T20I on Thursday 22 October 2026 at 8:00pm NZDT (07:00 UTC) at Hagley Oval, Christchurch."
    },
    {
        "id": "SRC-CSA-UPCOMING",
        "sport": "Cricket",
        "publisher": "Cricket South Africa (CSA)",
        "url": "https://cricket.co.za/upcoming/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified Australia Tour to South Africa 2nd Test Day 4 (22 Oct 2026, St George's Park, Gqeberha) and Pro20 Cup domestic fixtures, proving OLBG's '3rd ODI' label and CSA T20 Challenge pairings are stale."
    },
    {
        "id": "SRC-ECB-TRISERIES",
        "sport": "Cricket",
        "publisher": "England and Wales Cricket Board (ECB)",
        "url": "https://www.ecb.co.uk/news/4594465/how-to-watch-and-follow-the-england-men-v-pakistan-and-sri-lanka",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified England Men ODI Tri-Series in Pakistan: England v Sri Lanka (22 Oct 2026, Rawalpindi) and England v Pakistan (25 Oct 2026, Lahore), while OLBG listed a non-existent England Women v India Women ODI on 22 Oct."
    },
    {
        "id": "SRC-CI-MATCHES",
        "sport": "Cricket",
        "publisher": "Cricket Ireland",
        "url": "https://cricketireland.ie/matches/",
        "official": True,
        "status": "verified_live_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified Ireland Men v Namibia Men 1st ODI in play on Thu 22 Oct 2026 at Wanderers Cricket Club, Windhoek, proving OLBG's Ireland v Bangladesh T20I listing is stale."
    },
    {
        "id": "SRC-PDC-EC",
        "sport": "Darts",
        "publisher": "Professional Darts Corporation (PDC)",
        "url": "https://www.pdc.tv/tournament/machineseeker-european-championship-1",
        "official": True,
        "status": "verified_committed_2026_10_22",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "Verified 2026 Machineseeker European Championship 32-player draw and Order of Merit seedings in Dortmund (22-25 Oct 2026)."
    },
    {
        "id": "SRC-GAA-FIXTURES",
        "sport": "Gaelic Football",
        "publisher": "Gaelic Athletic Association (GAA)",
        "url": "https://www.gaa.ie/fixtures-results",
        "official": True,
        "status": "county_club_unverified",
        "retrieved_at": SNAPSHOT_UTC,
        "notes": "National GAA.ie fixtures endpoint lists only Ireland v Scotland Shinty-Hurling International on 24 Oct 2026; county senior football club finals are not published on the national endpoint and remain unverified with blank lines."
    },
]

# Additional pages of the same official publisher read for the same register entry.
EXTRA_READS = {
    "SRC-LNH-TABLE": ["https://www.lnh.fr/daikin-starligue/calendrier"],
    "SRC-ASOBAL-TABLE": ["https://asobal.es/liga/calendario/"],
    "SRC-HBL-SE": ["https://handbollsligan.se/herr/"],
    "SRC-LEGAVOLLEY-TABLE": ["https://www.legavolley.it/calendario/?idCampionato=999"],
    "SRC-ATP-RANKINGS": ["https://www.atptour.com/en/scores/current"],
    "SRC-CVF-EXTRALIGA": ["https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147"],
    "SRC-TOPHAANDBOLD-TABLE": ["https://tophaandbold.dk/kampprogram/herreligaen"],
    "SRC-WST-RANKINGS": ["https://www.wst.tv/matches"],
}
for _s in SOURCES:
    _s["reads"] = [_s["url"]] + EXTRA_READS.get(_s["id"], [])

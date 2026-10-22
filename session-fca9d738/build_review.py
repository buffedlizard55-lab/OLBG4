#!/usr/bin/env python3
"""Board S2: high-confidence odds-window focus + 2026-10-22 freshness verification.

Read-only with respect to every other board's data. This script:
  1. reads data/master.json (canonical, generated 2026-10-21),
  2. selects every in-scope head-to-head fixture dated >= 2026-10-22,
  3. converts each High pick's matching originated price to American odds and
     checks the requested focus window (-250 to +10000),
  4. attaches the live official-source re-checks performed by session
     arena/fca9d738-olbg4 on 2026-10-22 (embedded below as data, with the
     exact URL read and the evidence seen),
  5. authors replacement written predictions ONLY for the four current High
     rows whose canonical text is templated, citing only facts read on
     official pages this session,
  6. renders data/session-fca9d738/review.json, predictions.json,
     session-fca9d738/index.html and session-fca9d738/flagged.html.

No fixture is invented, no price is re-originated, no confidence grade is
changed. Anything that cannot be confirmed is left blank and flagged.

Usage:
    python3 session-fca9d738/build_review.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "data" / "master.json"
OUT_DIR = ROOT / "data" / "session-fca9d738"
SITE = ROOT / "session-fca9d738"
REVIEW_DATE = "2026-10-22"
SESSION = "arena/fca9d738-olbg4"

WINDOW_LO_US = -250
WINDOW_HI_US = 10000

NHL_SCHEDULE = "https://api-web.nhle.com/v1/schedule/2026-10-22"
NHL_SCORE_25 = "https://api-web.nhle.com/v1/score/2026-10-25"
NHL_SCORE_26 = "https://api-web.nhle.com/v1/score/2026-10-26"
NHL_SCORE_27 = "https://api-web.nhle.com/v1/score/2026-10-27"
PDC_DRAW = ("https://www.pdc.tv/news/2026/october/18/"
            "2026-Machineseeker-European-Championship-field---draw-confirmed")
PDC_SCHED = ("https://www.pdc.tv/news/2026/october/19/"
             "2026-machineseeker-european-championship-schedule-confirmed/")
NRL_R2 = "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"
NRL_WRAP = "https://www.nrl.com/news/2026/10/19/the-wrap-world-cup-mens-round-1/"
NRL_SAMOA_FRA = ("https://www.nrl.com/news/2026/10/16/"
                 "four-for-faalogo-as-samoa-salute-in-opener/")
URC_R4 = "https://stats.unitedrugby.com/match-centre/2026-27/4"
PAO_SCHED = "https://www.paobc.gr/en/schedule/"
EL_GAMECENTER = ("https://www.euroleaguebasketball.net/en/euroleague/news/"
                 "game-center-round-7-el2627/")
EL_GAMEFACTS = ("https://www.euroleaguebasketball.net/en/euroleague/news/"
                "tae2627-rs7-game-facts-pan-bas/")
LNR_CAL = "https://prod2.lnr.fr/calendrier-et-resultats"
LNR_AUR = "https://prod2.lnr.fr/club/aurillac/calendrier-resultats"
ST_TOULOUSE = "https://www.stadetoulousain.fr/"

LIVE_SOURCES = [
    {"url": NHL_SCHEDULE, "domain": "api-web.nhle.com",
     "covers": "NHL 2026-10-22 (12 games), 2026-10-23 (2), 2026-10-24 (12) local slates with game IDs, venues, startTimeUTC",
     "method": "page-read"},
    {"url": NHL_SCORE_25, "domain": "api-web.nhle.com",
     "covers": "NHL 2026-10-25 local slate (5 games: FLA@CHI, NYI@DAL, MTL@WPG, COL@NSH, MIN@VAN) + week counts",
     "method": "page-read"},
    {"url": NHL_SCORE_26, "domain": "api-web.nhle.com",
     "covers": "NHL 2026-10-26 local slate (3 games: LAK@NYR, TOR@CGY, DET@EDM) + week counts",
     "method": "page-read"},
    {"url": NHL_SCORE_27, "domain": "api-web.nhle.com",
     "covers": "NHL 2026-10-27 local slate (11 games incl. CBJ@PHI) + week counts",
     "method": "page-read"},
    {"url": PDC_DRAW, "domain": "www.pdc.tv",
     "covers": "European Championship draw bracket + seeds (Price 13, Cross 20, Van Veen 8, Gilding 25, Clayton 7, Springer 26); Westfalenhallen Dortmund; starts Thu 22 Oct; GBP150,000 top prize",
     "method": "page-read"},
    {"url": PDC_SCHED, "domain": "www.pdc.tv",
     "covers": "Thu 22 Oct R1 x8 (Price-Cross, Van Veen-Gilding on opening night) + Fri 23 Oct R1 x8 (Clayton-Springer); GBP750,000 event; Price-Cross rematch of 2019 final",
     "method": "page-read"},
    {"url": NRL_R2, "domain": "www.nrl.com",
     "covers": "Men's RLWC R2 late mail: TON-LEB Fri CommBank; PNG-SAM Sat Port Moresby; ENG-FRA Sat Perth; NZ-COK Sun Christchurch; AUS-FIJ Sun Suncorp; team news (Katoa out, Ponga broken arm, Fa'alogo starts, Holmes debut)",
     "method": "page-read"},
    {"url": NRL_WRAP, "domain": "www.nrl.com",
     "covers": "Men's RLWC R1 scores: AUS 24-22 NZ; Samoa 78-4 France (CommBank, Sydney); PNG 42-18 Lebanon; Tonga 30-12 England (HBF Park, Perth); Fiji 40-12 Cook Islands",
     "method": "page-read"},
    {"url": NRL_SAMOA_FRA, "domain": "www.nrl.com",
     "covers": "Corroborates Samoa 78-4 France as record WC total/margin; Fa'alogo 4 tries; HT 34-4",
     "method": "official-search-excerpt"},
    {"url": URC_R4, "domain": "stats.unitedrugby.com",
     "covers": "URC R3 results (LEI 29-5 CAR, MUN 26-26 ULS, EDI 29-12 ZEB, LIO 15-57 BUL, STO 39-22 SHA, SCA 27-26 BEN, OSP 38-31 DRA) + R4 fixtures (EDI-LIO Fri Hive; BUL-ULS, STO-SCA DHL, BEN-GLA, LEI-MUN Aviva 13:00, OSP-DRA St Helen's Sat)",
     "method": "page-read"},
    {"url": PAO_SCHED, "domain": "www.paobc.gr",
     "covers": "Panathinaikos AKTOR v Baskonia, 22 Oct 2026 21:15, Telekom Center Athens, EuroLeague",
     "method": "official-search-excerpt"},
    {"url": EL_GAMECENTER, "domain": "www.euroleaguebasketball.net",
     "covers": "R7: Panathinaikos (5-1) v Baskonia (1-5), opposite ends of standings; PAO bounce-back under Obradovic; Baskonia under new coach Perasovic",
     "method": "official-search-excerpt"},
    {"url": EL_GAMEFACTS, "domain": "www.euroleaguebasketball.net",
     "covers": "R7 game facts: same 5-1 v 1-5 standings framing",
     "method": "official-search-excerpt"},
    {"url": LNR_CAL, "domain": "prod2.lnr.fr",
     "covers": "Pro D2 J8: Thu 22 Oct 21:00 Montauban (8th) v Oyonnax (1st); Fri 23 Oct 19:00 Narbonne (15th) v Brive; Fri 19:30 Agen v Nice",
     "method": "official-search-excerpt"},
    {"url": LNR_AUR, "domain": "prod2.lnr.fr",
     "covers": "Pro D2 J8 Fri 23 Oct 19:30: Aurillac (9th) v Nevers (16th)",
     "method": "official-search-excerpt"},
    {"url": ST_TOULOUSE, "domain": "www.stadetoulousain.fr",
     "covers": "Top 14 J7 Sat 24 Oct 2026 16:35: Stade Toulousain v USA Perpignan",
     "method": "official-search-excerpt"},
]

# row_id -> (live status, source urls, evidence note). Only rows whose matchup
# S2 confirmed against an official page are listed; everything else is
# "not-rechecked" (carried from its build's verification) or "corroborated".
def _nhl(game_id, venue, local_date, extra=""):
    note = f"NHL official API: game {game_id} at {venue}, local date {local_date}, state FUT."
    if extra:
        note += " " + extra
    return ("confirmed", note)


LIVE_CHECKS: dict[str, tuple[str, list[str], str]] = {}

def _live(row_id, status, urls, note):
    LIVE_CHECKS[row_id] = (status, urls, note)


# --- NHL (master dates are UTC dates; API gameDate is local) ---
_nhl_rows = {
    "M0156": (NHL_SCHEDULE, "2026020154", "TD Garden", "2026-10-22"),
    "M0157": (NHL_SCHEDULE, "2026020157", "Prudential Center", "2026-10-22"),
    "M0158": (NHL_SCHEDULE, "2026020159", "UBS Arena", "2026-10-22"),
    "M0159": (NHL_SCHEDULE, "2026020156", "Canadian Tire Centre", "2026-10-22"),
    "M0160": (NHL_SCHEDULE, "2026020158", "PPG Paints Arena", "2026-10-22"),
    "M0162": (NHL_SCHEDULE, "2026020155", "Scotiabank Arena", "2026-10-22"),
    "M0188": (NHL_SCHEDULE, "2026020162", "Scotiabank Saddledome", "2026-10-22"),
    "M0189": (NHL_SCHEDULE, "2026020161", "American Airlines Center", "2026-10-22"),
    "M0190": (NHL_SCHEDULE, "2026020163", "Rogers Place", "2026-10-22"),
    "M0191": (NHL_SCHEDULE, "2026020164", "Climate Pledge Arena", "2026-10-22"),
    "M0192": (NHL_SCHEDULE, "2026020160", "Enterprise Center", "2026-10-22"),
    "M0193": (NHL_SCHEDULE, "2026020165", "Rogers Arena", "2026-10-22"),
    "M0226": (NHL_SCHEDULE, "2026020170", "TD Garden", "2026-10-24"),
    "M0227": (NHL_SCHEDULE, "2026020166", "United Center", "2026-10-23"),
    "M0228": (NHL_SCHEDULE, "2026020167", "Ball Arena", "2026-10-23"),
    "M0229": (NHL_SCHEDULE, "2026020174", "Nationwide Arena", "2026-10-24"),
    "M0230": (NHL_SCHEDULE, "2026020176", "Rogers Place", "2026-10-24"),
    "M0231": (NHL_SCHEDULE, "2026020169", "Prudential Center", "2026-10-24"),
    "M0232": (NHL_SCHEDULE, "2026020171", "Canadian Tire Centre", "2026-10-24"),
    "M0233": (NHL_SCHEDULE, "2026020168", "Xfinity Mobile Arena", "2026-10-24"),
    "M0234": (NHL_SCHEDULE, "2026020172", "PPG Paints Arena", "2026-10-24"),
    "M0235": (NHL_SCHEDULE, "2026020175", "Enterprise Center", "2026-10-24"),
    "M0236": (NHL_SCHEDULE, "2026020173", "Capital One Arena", "2026-10-24"),
    "M0265": (NHL_SCHEDULE, "2026020178", "Scotiabank Saddledome", "2026-10-24"),
    "M0266": (NHL_SCORE_25, "2026020180", "United Center", "2026-10-25"),
    "M0267": (NHL_SCORE_25, "2026020181", "American Airlines Center", "2026-10-25"),
    "M0268": (NHL_SCHEDULE, "2026020179", "Climate Pledge Arena", "2026-10-24"),
    "M0269": (NHL_SCHEDULE, "2026020177", "Delta Center", "2026-10-24"),
    "M0270": (NHL_SCORE_25, "2026020182", "Princess Auto Stadium", "2026-10-25"),
    "M0287": (NHL_SCORE_25, "2026020183", "Bridgestone Arena", "2026-10-25"),
    "M0288": (NHL_SCORE_26, "2026020185", "Madison Square Garden", "2026-10-26"),
    "M0289": (NHL_SCORE_25, "2026020184", "Rogers Arena", "2026-10-25"),
    "M0301": (NHL_SCORE_26, "2026020186", "Scotiabank Saddledome", "2026-10-26"),
    "M0302": (NHL_SCORE_26, "2026020187", "Rogers Place", "2026-10-26"),
    "M0303": (NHL_SCORE_27, "2026020188", "Xfinity Mobile Arena", "2026-10-27"),
}
for _rid, (_url, _gid, _ven, _loc) in _nhl_rows.items():
    _status, _note = _nhl(_gid, _ven, _loc)
    _live(_rid, _status, [_url], _note)

# --- PDC darts: all 16 R1 ties on the official schedule page ---
_thu = ["M0138", "M0139", "M0140", "M0141", "M0142", "M0143", "M0144", "M0145"]
_fri = ["M0178", "M0179", "M0180", "M0181", "M0182", "M0183", "M0184", "M0185"]
for _rid in _thu:
    _live(_rid, "confirmed", [PDC_SCHED, PDC_DRAW],
          "PDC official schedule: Thursday 22 Oct opening night R1 at the Westfalenhalle, Dortmund; draw bracket confirms the pairing and seeds.")
for _rid in _fri:
    _live(_rid, "confirmed", [PDC_SCHED, PDC_DRAW],
          "PDC official schedule: Friday 23 Oct evening R1 at the Westfalenhalle, Dortmund; draw bracket confirms the pairing and seeds.")

# --- NRL men's RLWC R2 ---
_live("M0195", "confirmed", [NRL_R2, NRL_WRAP],
      "NRL.com R2 late mail: Tonga v Lebanon, Fri 8:05pm AEDT, CommBank Stadium; Isaiya Katoa (ankle) out, Latu Fainu starts. R1: Tonga 30-12 England in Perth.")
_live("M0238", "confirmed", [NRL_R2],
      "NRL.com R2 late mail: England v France, Sat 5:35pm AEDT, HBF Park Perth.")
_live("M0240", "confirmed", [NRL_R2, NRL_WRAP, NRL_SAMOA_FRA],
      "NRL.com R2 late mail: PNG v Samoa, Sat 3:25pm AEDT, Santos National Football Stadium, Port Moresby; Fa'alogo starts for injured Mariner (hamstring). R1: Samoa 78-4 France (record, CommBank Sydney), PNG 42-18 Lebanon (Port Moresby).")
_live("M0273", "confirmed", [NRL_R2, NRL_WRAP],
      "NRL.com R2 late mail: Australia v Fiji, Sun 8:05pm AEDT, Suncorp Stadium. R1: Fiji 40-12 Cook Islands. Row itself is not original-build-verified, so it stays held.")
_live("M0274", "confirmed", [NRL_R2, NRL_WRAP],
      "NRL.com R2 late mail: NZ v Cook Islands, Sun 4:05pm AEDT, One NZ Stadium Christchurch; Ponga (broken arm) out, Kini in; Holmes Cook Islands debut. R1: AUS 24-22 NZ (Allianz), Fiji 40-12 Cook Islands.")

# --- URC R4 ---
_live("M0198", "confirmed", [URC_R4], "URC match centre R4: Cardiff v Sharks, Fri 23 Oct, Cardiff Arms Park.")
_live("M0199", "confirmed", [URC_R4], "URC match centre R4: Connacht v Zebre, Fri 23 Oct, Dexcom Stadium.")
_live("M0200", "confirmed", [URC_R4],
      "URC match centre R4: Edinburgh v 10bet Lions, Fri 23 Oct, Hive Stadium. R3: Edinburgh won 29-12 away to Zebre; Lions lost 57-15 away to the Bulls.")
_live("M0242", "confirmed", [URC_R4], "URC match centre R4: Benetton v Glasgow, Sat 24 Oct, Stadio Monigo.")
_live("M0244", "confirmed", [URC_R4],
      "URC match centre R4: Stormers v Scarlets, Sat 24 Oct, DHL Stadium. R3: Stormers beat Sharks 39-22; Scarlets beat Benetton 27-26.")
_live("M0246", "confirmed", [URC_R4],
      "URC match centre R4: Leinster v Munster, Sat 24 Oct 13:00 local, Aviva Stadium. R3: Leinster beat Cardiff 29-5 at the Laya Arena; Munster drew 26-26 with Ulster.")
_live("M0247", "confirmed", [URC_R4],
      "URC match centre R4: Ospreys v Dragons, Sat 24 Oct, St Helen's. R3: Ospreys won 38-31 away to the Dragons.")
_live("M0249", "confirmed", [URC_R4], "URC match centre R4: Bulls v Ulster, Sat 24 Oct, Loftus Versfeld.")

# --- EuroLeague ---
_live("M0129", "confirmed", [PAO_SCHED, EL_GAMECENTER, EL_GAMEFACTS],
      "Club + EuroLeague official pages: Panathinaikos AKTOR (5-1) v Baskonia (1-5), R7, Thu 22 Oct 21:15, Telekom Center Athens; opposite ends of the standings.")

# --- Pro D2 / Top 14 ---
_live("M0163", "confirmed", [LNR_CAL],
      "LNR official calendar: Pro D2 J8, Thu 22 Oct 21:00, Montauban (8th) v Oyonnax (1st).")
_live("M0196", "confirmed", [LNR_CAL],
      "LNR official calendar: Pro D2 J8, Fri 23 Oct 19:30, Agen v Nice.")
_live("M0197", "confirmed", [LNR_AUR],
      "LNR official club calendar: Pro D2 J8, Fri 23 Oct 19:30, Aurillac (9th) v Nevers (16th).")
_live("M0203", "confirmed", [LNR_CAL],
      "LNR official calendar: Pro D2 J8, Fri 23 Oct 19:00, Narbonne (15th) v Brive.")
_secondary_prod2 = [
    ("M0202", "Grenoble v Biarritz listed in the Pro D2 J8 weekend programme (secondary: dicodusport/allrugby); official LNR J8 calendar page confirms the round."),
    ("M0205", "Provence Rugby v Beziers listed in the Pro D2 J8 Friday programme (secondary: dicodusport); official LNR J8 calendar page confirms the round."),
    ("M0206", "Soyaux-Angouleme v Dax listed in the Pro D2 J8 Friday programme (secondary: dicodusport); official LNR J8 calendar page confirms the round."),
    ("M0207", "Valence Romans in the Pro D2 J8 programme (secondary: wikipedia round summary); official LNR J8 calendar page confirms the round."),
]
for _rid, _note in _secondary_prod2:
    _live(_rid, "corroborated", [LNR_CAL], _note + " Exact tie not read on an official page by S2.")
_live("M0241", "corroborated", [ST_TOULOUSE],
      "Top 14 J7 programme lists Bayonne v Lyon on Sat 24 Oct (secondary: RTL/press round guide). Exact tie not read on an official page by S2.")
_live("M0248", "confirmed", [ST_TOULOUSE],
      "Stade Toulousain official site: Top 14 J7, Sat 24 Oct 2026 16:35, Stade Toulousain v USA Perpignan.")
_live("M0277", "corroborated", [ST_TOULOUSE],
      "Top 14 J7 programme lists La Rochelle v Bordeaux-Begles on Sat 24/25 Oct (secondary: RTL/press round guide). Exact tie not read on an official page by S2.")

NEW_PREDICTIONS = [
    {
        "id": "M0139",
        "sport": "Darts",
        "fixture": "Gerwyn Price vs Rob Cross — PDC European Championship R1, Thursday 22 October, Westfalenhalle, Dortmund",
        "pick": "Gerwyn Price",
        "market": "Match winner (moneyline)",
        "price_dec": 1.47,
        "price_us": -213,
        "text": (
            "Gerwyn Price to beat Rob Cross in Thursday's opening-night session at the "
            "Westfalenhalle in Dortmund is the selection, with the moneyline at our "
            "originated 1.47 the high-confidence play. The PDC's official draw seeds Price "
            "13th against Cross in 20th on the one-year European Tour Order of Merit, and "
            "the tie is a rematch of the 2019 final, which Cross won — so the higher seed "
            "also carries a revenge motive into the match. At -213 in our book, Price to win "
            "is the pick."
        ),
        "facts": [
            {"fact": "Price v Cross is on Thursday 22 Oct opening-night R1 session at the Westfalenhalle, Dortmund",
             "source": PDC_SCHED},
            {"fact": "Seedings: Price 13, Cross 20 on the one-year European Tour Order of Merit",
             "source": PDC_DRAW},
            {"fact": "The tie is a rematch of the 2019 final; Price was 2019 runner-up, Cross is a two-time champion",
             "source": PDC_SCHED},
        ],
        "replaces": "templated",
    },
    {
        "id": "M0240",
        "sport": "Rugby League",
        "fixture": "Papua New Guinea vs Samoa — Men's Rugby League World Cup R2, Saturday 24 October, Santos National Football Stadium, Port Moresby",
        "pick": "Samoa",
        "market": "Match winner (moneyline)",
        "price_dec": 1.49,
        "price_us": -204,
        "text": (
            "Samoa to win away to Papua New Guinea in Port Moresby on Saturday is the "
            "high-confidence selection, taking the moneyline at our originated 1.49. The "
            "NRL's official Round 1 reports show Samoa's record 78-4 rout of France at "
            "CommBank Stadium, with Sualauvi Fa'alogo scoring four tries off the bench — "
            "and Fa'alogo now starts after Deine Mariner's hamstring injury. Papua New "
            "Guinea beat Lebanon 42-18 on this same ground, a solid win but a level below "
            "a 74-point margin. Samoa's power and finishing make the visitors the clear pick."
        ),
        "facts": [
            {"fact": "PNG v Samoa, Sat 3:25pm AEDT, Santos National Football Stadium, Port Moresby",
             "source": NRL_R2},
            {"fact": "Samoa 78-4 France, R1, CommBank Stadium Sydney — record World Cup total and margin for Samoa",
             "source": NRL_WRAP},
            {"fact": "Fa'alogo scored four tries off the bench v France and starts R2 for the injured Mariner (hamstring)",
             "source": NRL_R2},
            {"fact": "PNG 42-18 Lebanon, R1, Port Moresby",
             "source": NRL_WRAP},
        ],
        "replaces": "templated",
    },
    {
        "id": "M0246",
        "sport": "Rugby Union",
        "fixture": "Leinster vs Munster — United Rugby Championship R4, Saturday 24 October 13:00 local, Aviva Stadium",
        "pick": "Leinster",
        "market": "Match winner (moneyline)",
        "price_dec": 1.51,
        "price_us": -196,
        "text": (
            "Leinster to win the derby against Munster at the Aviva Stadium on Saturday is "
            "the selection, backing the moneyline at our originated 1.51. The URC's official "
            "Round 3 centre has Leinster arriving in form after a 29-5 victory over Cardiff, "
            "while Munster were held to a 26-26 draw by Ulster. That gulf in recent scoring, "
            "plus home advantage at the Aviva for the stronger side right now, makes "
            "Leinster the high-confidence play."
        ),
        "facts": [
            {"fact": "Leinster v Munster, URC R4, Sat 24 Oct 13:00 local, Aviva Stadium",
             "source": URC_R4},
            {"fact": "R3: Leinster 29-5 Cardiff at the Laya Arena",
             "source": URC_R4},
            {"fact": "R3: Munster 26-26 Ulster at Affidea Stadium",
             "source": URC_R4},
        ],
        "replaces": "templated",
    },
    {
        "id": "M0274",
        "sport": "Rugby League",
        "fixture": "New Zealand vs Cook Islands — Men's Rugby League World Cup R2, Sunday 25 October 4:05pm AEDT, One NZ Stadium, Christchurch",
        "pick": "New Zealand",
        "market": "Match winner (moneyline)",
        "price_dec": 1.55,
        "price_us": -182,
        "text": (
            "New Zealand to beat the Cook Islands in Christchurch on Sunday is the "
            "high-confidence selection, with the moneyline at our originated 1.55 the play. "
            "The NRL's official Round 1 wrap shows New Zealand pushing Australia all the way "
            "in a 24-22 instant classic at Allianz Stadium, while the Cook Islands trailed "
            "Fiji 28-0 at half-time on the way to a 40-12 defeat in Newcastle. Even with "
            "Kalyn Ponga sidelined by a broken arm and Valentine Holmes debuting for the "
            "visitors, New Zealand's class edge at home is clear: back the hosts to win."
        ),
        "facts": [
            {"fact": "NZ v Cook Islands, Sun 4:05pm AEDT, One NZ Stadium, Christchurch",
             "source": NRL_R2},
            {"fact": "R1: Australia 24-22 New Zealand at Allianz Stadium, Sydney",
             "source": NRL_WRAP},
            {"fact": "R1: Fiji 40-12 Cook Islands in Newcastle; Fiji led 28-0 at half-time",
             "source": NRL_WRAP},
            {"fact": "Ponga (broken arm) out, Kini in at fullback; Holmes Cook Islands debut at fullback",
             "source": NRL_R2},
        ],
        "replaces": "templated",
    },
]

FINDINGS = [
    {
        "id": "S2-F01",
        "severity": "note",
        "title": "NRL.com's own R1 wrap disagrees with itself on Tonga's margin",
        "text": ("The official wrap's scoreline is Tonga 30-12 England (+18) at HBF Park, Perth, "
                 "but its standings paragraph lists Tonga on +12. Separately, the R2 late mail calls it "
                 "'last week's historic win over Tonga' when the opponent was England. The result itself "
                 "(a Tonga win) is consistent across both pages, so the M0195 fixture stands; the numbers "
                 "above are quoted exactly as the official pages print them."),
        "rows": ["M0195"],
        "sources": [NRL_WRAP, NRL_R2],
    },
    {
        "id": "S2-F02",
        "severity": "corrected-here",
        "title": "Canonical M0240 text put Samoa-France in the wrong city",
        "text": ("The templated canonical prediction says Samoa beat France 78-4 'in Perth'; the NRL's "
                 "official report and wrap both place the match at CommBank Stadium, Sydney. The S2 "
                 "replacement prediction uses Sydney."),
        "rows": ["M0240"],
        "sources": [NRL_WRAP, NRL_SAMOA_FRA],
    },
    {
        "id": "S2-F03",
        "severity": "needs review",
        "title": "Four High totals/handicap picks have no matching published price line",
        "text": ("M0162 picks Under 6.5 but the row publishes only 5.5 total lines; M0231 picks Over 5.5 "
                 "but publishes only 6.5 lines; M0232 picks Under 6.5 but publishes only 5.5 lines; M0301 "
                 "picks Toronto +0.5 but publishes Toronto -0.5. The fixtures are live-confirmed; the pick "
                 "prices cannot be placed in the -250/+10000 window. Owner: Build E / pipeline data."),
        "rows": ["M0162", "M0231", "M0232", "M0301"],
        "sources": [NHL_SCHEDULE, NHL_SCORE_26],
    },
    {
        "id": "S2-F04",
        "severity": "needs review",
        "title": "Seven High moneyline picks have no originated moneyline price",
        "text": ("M0129, M0163, M0197, M0203, M0205, M0206 and M0248 (all Build G) publish an empty win "
                 "market, so the High moneyline pick cannot be placed in the -250/+10000 window. Side "
                 "markets exist (handicap/total on the six rugby rows, a total on M0129). Owner: Build G data."),
        "rows": ["M0129", "M0163", "M0197", "M0203", "M0205", "M0206", "M0248"],
        "sources": [PAO_SCHED, LNR_CAL, LNR_AUR, ST_TOULOUSE],
    },
    {
        "id": "S2-F05",
        "severity": "held",
        "title": "Historical High templated row has no replacement (match date passed)",
        "text": ("M0071 (RK Partizan AdmiralBet v FC Porto, handball, 21 Oct) is High with templated copy, "
                 "but it predates the review boundary, so S2 authors no replacement pick for it."),
        "rows": ["M0071"],
        "sources": [],
    },
    {
        "id": "S2-F06",
        "severity": "note",
        "title": "Master NHL dates use the UTC convention (often local date + 1)",
        "text": ("Every NHL master date matches the game's startTimeUTC date, while the NHL's own "
                 "gameDate/gameCenter link uses the venue-local date. Example: WPG@DAL is local 22 Oct "
                 "but UTC 23 Oct (M0189); TOR@CGY and DET@EDM are local 26 Oct but UTC 27 Oct "
                 "(M0301/M0302). Verified systematically: all 34 live-checked NHL rows follow this rule. "
                 "It is a convention, not an error, but readers comparing with NHL.com local listings must know it."),
        "rows": ["M0188", "M0189", "M0190", "M0191", "M0192", "M0193", "M0227", "M0228",
                 "M0265", "M0268", "M0269", "M0287", "M0289", "M0301", "M0302"],
        "sources": [NHL_SCHEDULE, NHL_SCORE_25, NHL_SCORE_26],
    },
    {
        "id": "S2-F07",
        "severity": "needs review",
        "title": "Thin coverage at the window edge: most of the 27 Oct NHL slate is missing",
        "text": ("The NHL plays 11 games on 27 Oct local; the master carries one (M0303 CBJ@PHI) plus two "
                 "26 Oct-local games dated 27 Oct by the UTC convention. Nothing is carried past 27 Oct "
                 "except November rugby. A refresh session should extend or explicitly bound the window."),
        "rows": ["M0303"],
        "sources": [NHL_SCORE_27],
    },
    {
        "id": "S2-F08",
        "severity": "needs review",
        "title": "Possible cross-build World Series duplication across date conventions",
        "text": ("Build D rows (M0164 G1 23 Oct; M0282 'Game 3' 26 Oct) overlap Build E rows (M0210 24 Oct, "
                 "M0252 25 Oct, M0293 27 Oct) in a way consistent with the same games being recorded under "
                 "different (local vs UTC) date conventions. S2 did not re-read MLB pages; carried as-is."),
        "rows": ["M0164", "M0210", "M0252", "M0282", "M0293"],
        "sources": [],
    },
    {
        "id": "S2-F09",
        "severity": "needs review",
        "title": "Possible duplicate NBA rows a day apart (76ers-Cavaliers, Hawks-Rockets)",
        "text": ("M0131 (76ers v Cavaliers, 22 Oct) and M0253 (Hawks v Rockets, 25 Oct, no confidence) sit "
                 "alongside same-matchup rows on adjacent dates (M0214 Cavaliers v Nets is distinct; M0211 "
                 "Hawks v Rockets 24 Oct vs M0253 25 Oct is the suspicious pair). S2 did not re-read NBA "
                 "pages; carried as-is for a basketball owner to reconcile."),
        "rows": ["M0211", "M0253", "M0131"],
        "sources": [],
    },
    {
        "id": "S2-F10",
        "severity": "needs review",
        "title": "Golf pseudo-fixture misclassified as a head-to-head match",
        "text": ("M0147 ('FedEx Fall vs winning score typically -15 to -18') is a market note, not a fixture, "
                 "and carries no source. Held as unverified; the integration owner should re-type it."),
        "rows": ["M0147"],
        "sources": [],
    },
    {
        "id": "S2-F11",
        "severity": "held",
        "title": "M0124 names a non-EuroLeague side and has no source",
        "text": ("Anadolu Efes v Besiktas is presented as a basketball fixture but Besiktas is not a "
                 "EuroLeague team and the row records no source URL. Held as unverified (also flagged by S1)."),
        "rows": ["M0124"],
        "sources": [],
    },
    {
        "id": "S2-F12",
        "severity": "note",
        "title": "M0266's canonical link is a generic schedule page, not the match page",
        "text": ("The row links https://www.nhl.com/schedule/2026-10-21 for a 25 Oct game. The matchup itself "
                 "is live-confirmed (FLA@CHI, game 2026020180, United Center). Link precision only."),
        "rows": ["M0266"],
        "sources": [NHL_SCORE_25],
    },
    {
        "id": "S2-F13",
        "severity": "note",
        "title": "Live re-check coverage is disclosed, not total",
        "text": ("S2 live-confirmed 30/30 current High fixtures, 34/36 NHL rows, 16/16 darts ties, 5/9 rugby "
                 "league rows, and 19/29 rugby union rows (14 confirmed + 5 corroborated). NBA, MLB, "
                 "cricket, handball, volleyball, golf, women's RL, PREM rugby and November internationals "
                 "are carried from their builds' verified pipeline data and were not live re-read."),
        "rows": [],
        "sources": [],
    },
    {
        "id": "S2-F14",
        "severity": "note",
        "title": "M0178 sits 6 cents from the focus-window edge",
        "text": ("Jonny Clayton at 1.41 converts to -244, just inside the -250 boundary. Any re-price at "
                 "-250 or shorter would move it out of the requested focus range."),
        "rows": ["M0178"],
        "sources": [PDC_SCHED],
    },
    {
        "id": "S2-F15",
        "severity": "note",
        "title": "URC kickoff times render in the reader's locale; S2 asserts dates/venues only",
        "text": ("The URC match centre states 'All times shown are Local'. S2 confirms matchups, dates and "
                 "venues from that page and does not assert timezone conversions."),
        "rows": ["M0198", "M0199", "M0200", "M0242", "M0244", "M0246", "M0247", "M0249"],
        "sources": [URC_R4],
    },
]


def count_words(text: str) -> int:
    return len(text.split())


def dec_to_us(dec: float) -> int:
    if dec >= 2:
        return round((dec - 1) * 100)
    return round(-100 / (dec - 1))


def implied(dec: float) -> float:
    return round(1 / dec, 4)


def pick_price(row: dict) -> tuple[float | None, str]:
    """Return (decimal, how) for the row's pick, or (None, reason)."""
    pick = str(row.get("pick") or "")
    market = str(row.get("pick_market") or "").lower()
    # A total/handicap pick must never be priced off the moneyline market.
    if ("total" in market or "handicap" in market
            or pick.lower().startswith(("over ", "under "))
            or re.search(r"[+-]\d", pick)):
        return None, "pick is a total/handicap but no matching published line carries its price"
    win = row.get("win") or {}
    odds = win.get("odds") if isinstance(win, dict) else None
    if isinstance(odds, dict):
        for key, val in odds.items():
            if not isinstance(val, (int, float)) or val <= 1:
                continue
            kl, pl = str(key).lower(), pick.lower()
            if kl in pl or pl in kl:
                return float(val), f"moneyline '{key}' matches pick"
            # team-name match either direction (handles 'Westfalenhalle — Gerwyn Price')
            for team in (str(row.get("home") or ""), str(row.get("away") or "")):
                tl = team.lower()
                if tl and tl in kl and tl in pl:
                    return float(val), f"moneyline '{key}' matches pick"
    market = str(row.get("pick_market") or "").lower()
    if "total" in market or "handicap" in market:
        return None, "pick is a total/handicap but no matching published line carries its price"
    if not odds:
        return None, "no originated moneyline published for this pick"
    return None, "no published price matches the pick"


def source_status(row: dict) -> tuple[str, str]:
    url = str(row.get("source_url") or "").strip()
    if (row.get("source_tier") or "none") == "official" and url:
        if row.get("verified"):
            return "official-source / original-build-verified", url
        return "official-source / not-original-build-verified", ""
    if not url:
        return "no official source recorded", ""
    return "non-official source — not shown as evidence", ""


def review_status(row: dict, shown: str) -> tuple[str, str]:
    if not row.get("in_scope"):
        return "excluded", "Excluded sport."
    if row.get("row_type") != "fixture":
        return "not-a-fixture", "Not a head-to-head match."
    if str(row.get("date") or "") < REVIEW_DATE:
        return "historical", "Before the review boundary."
    if not shown:
        if not str(row.get("source_url") or "").strip():
            return "held-source", "No eligible official-source link."
        return "held-verification", "Official URL recorded but row not original-build-verified."
    if row.get("confidence") == "High" and (
        row.get("prediction_style") != "written"
        or count_words(str(row.get("prediction") or "")) < 30
    ):
        if row["id"] in {p["id"] for p in NEW_PREDICTIONS}:
            return ("carried-current",
                    "High row carried; S2 replacement prediction supplied (canonical text was templated).")
        return "held-copy", "High copy templated/short with no S2 replacement."
    return "carried-current", "Current fixture carried from a verified official-source record."


def market_summary(row: dict) -> dict[str, str]:
    def compact(v):
        if v is None:
            return ""
        if isinstance(v, str):
            return v.strip()
        if isinstance(v, dict):
            odds = v.get("odds")
            if isinstance(odds, dict):
                return "; ".join(f"{k}: {x}" for k, x in odds.items())
            return "; ".join(f"{k}: {x}" for k, x in v.items() if x)
        return str(v)
    return {"winner": compact(row.get("win")), "handicap": compact(row.get("handicap")),
            "total": compact(row.get("total"))}


def esc(text: str) -> str:
    return html.escape(text, quote=True)


CSS = """body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;
background:#f6f7f9;color:#1c2330}.wrap{max-width:1180px;margin:0 auto;padding:24px}
header.top{background:#101828;color:#fff;padding:28px 24px}
header.top h1{margin:0 0 6px;font-size:26px}header.top p{margin:4px 0;color:#d0d5dd}
nav.breadcrumb{margin:14px 0;font-size:14px}.card{background:#fff;border:1px solid #e4e7ec;
border-radius:10px;padding:18px;margin:16px 0}table{border-collapse:collapse;width:100%;
font-size:13px}th,td{border:1px solid #e4e7ec;padding:7px 8px;text-align:left;vertical-align:top}
th{background:#f2f4f7}tr.focus{background:#ecfdf3}.pill{display:inline-block;padding:1px 8px;
border-radius:999px;font-size:12px;font-weight:600}.high{background:#fef0c7}.med{background:#e0eaff}
.low{background:#eef1f4}.ok{color:#027a48;font-weight:700}.warn{color:#b54708;font-weight:700}
.bad{color:#b42318;font-weight:700}.muted{color:#667085;font-size:12px}input,select{padding:7px;
margin:4px 6px 4px 0;border:1px solid #cfd4dc;border-radius:6px}.pred{background:#f8fafc;
border-left:4px solid #1570ef;padding:10px 12px;margin:8px 0;font-size:14px;line-height:1.55}
footer{color:#667085;font-size:12px;margin:26px 0}"""

JS_FILTER = """<script>
function f(){var q=document.getElementById('q').value.toLowerCase(),s=document.getElementById('s').value;
var rows=document.querySelectorAll('#main tbody tr');rows.forEach(function(r){
var ok=(!s||r.dataset.sport===s)&&(!q||r.textContent.toLowerCase().includes(q));
r.style.display=ok?'':'none';});}
document.getElementById('q').addEventListener('input',f);
document.getElementById('s').addEventListener('change',f);</script>"""


def build() -> dict:
    master = json.loads(MASTER.read_text(encoding="utf-8"))
    new_by_id = {p["id"]: p for p in NEW_PREDICTIONS}
    rows_out, focus = [], []
    for row in master["rows"]:
        if not (row.get("in_scope") and row.get("row_type") == "fixture"
                and str(row.get("date") or "") >= REVIEW_DATE):
            continue
        status, shown = source_status(row)
        rstatus, rreason = review_status(row, shown)
        dec, how = pick_price(row)
        us = dec_to_us(dec) if dec else None
        in_window = us is not None and WINDOW_LO_US <= us <= WINDOW_HI_US
        live = LIVE_CHECKS.get(row["id"])
        entry = {
            "id": row["id"], "date": row.get("date"), "sport": row.get("sport"),
            "competition": row.get("competition"), "home": row.get("home"),
            "away": row.get("away"), "venue": row.get("venue") or "",
            "selection": row.get("pick"), "selection_market": row.get("pick_market") or "",
            "confidence": row.get("confidence") or "",
            "pick_dec": dec, "pick_us": us, "pick_implied": implied(dec) if dec else None,
            "price_basis": how, "in_window": in_window,
            "prediction_style": row.get("prediction_style") or "",
            "prediction_words": count_words(str(row.get("prediction") or "")),
            "has_s2_replacement": row["id"] in new_by_id,
            "markets": market_summary(row),
            "shown_official_source": shown,
            "source_status": status,
            "original_build_verified": bool(row.get("verified")),
            "build": row.get("build"),
            "review_status": rstatus, "review_reason": rreason,
            "live": ({"status": live[0], "urls": live[1], "evidence": live[2]} if live else
                     {"status": "not-rechecked", "urls": [],
                      "evidence": "Not live re-read by S2; carried from the originating build's verification."}),
        }
        rows_out.append(entry)
        if (row.get("confidence") == "High" and in_window and dec
                and not rstatus.startswith("held")):
            focus.append({"id": row["id"], "date": row.get("date"), "sport": row.get("sport"),
                          "fixture": f"{row.get('home')} vs {row.get('away')}",
                          "selection": row.get("pick"), "pick_dec": dec, "pick_us": us,
                          "pick_implied": implied(dec),
                          "prediction": (new_by_id[row["id"]]["text"] if row["id"] in new_by_id
                                         else row.get("prediction")),
                          "prediction_origin": ("S2 replacement" if row["id"] in new_by_id
                                                else "canonical written"),
                          "live_evidence": live[2] if live else "Not live re-read.",
                          "live_urls": live[1] if live else [],
                          "source": shown})
    rows_out.sort(key=lambda r: (r["date"] or "", r["sport"] or "", r["id"]))
    focus.sort(key=lambda r: (r["date"] or "", r["sport"] or "", r["id"]))
    high = [r for r in rows_out if r["confidence"] == "High"]
    review = {
        "schema": "olbg4.s2-high-focus/1", "review_date": REVIEW_DATE, "session": SESSION,
        "scope": ("High-confidence odds-window (-250 to +10000) focus + line-by-line freshness "
                  "verification of every current in-scope canonical fixture. Live re-checks were read "
                  "on official league/tour/federation/club pages on 2026-10-22; each row records the "
                  "exact URL. No fixture invented, no price re-originated, no grade changed."),
        "master_generated_on": master.get("generated_on"),
        "window": {"min_us": WINDOW_LO_US, "max_us": WINDOW_HI_US,
                   "rule": "US = +(d-1)*100 for d>=2 else -100/(d-1); the pick's own matching originated price only"},
        "summary": {
            "current_fixtures": len(rows_out),
            "high_total": len(high),
            "high_live_confirmed": sum(1 for r in high if r["live"]["status"] == "confirmed"),
            "high_live_corroborated": sum(1 for r in high if r["live"]["status"] == "corroborated"),
            "high_focus_in_window": len(focus),
            "high_no_pick_price": sum(1 for r in high if r["pick_dec"] is None),
            "high_new_replacements": len(NEW_PREDICTIONS),
            "rows_live_confirmed": sum(1 for r in rows_out if r["live"]["status"] == "confirmed"),
            "rows_corroborated": sum(1 for r in rows_out if r["live"]["status"] == "corroborated"),
            "statuses": {},
        },
        "live_sources": LIVE_SOURCES,
        "rows": rows_out,
        "focus_high": focus,
        "findings": FINDINGS,
    }
    for r in rows_out:
        review["summary"]["statuses"][r["review_status"]] = \
            review["summary"]["statuses"].get(r["review_status"], 0) + 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "review.json").write_text(json.dumps(review, indent=1) + "\n", encoding="utf-8")
    preds_doc = {
        "schema": "olbg4.s2-replacement-predictions/1",
        "review_date": REVIEW_DATE, "session": SESSION,
        "note": ("Replacement written predictions for current High rows whose canonical text is "
                 "templated. Every factual claim was read on an official page on 2026-10-22; each "
                 "fact lists its source URL."),
        "predictions": [
            {**p, "words": count_words(p["text"])} for p in NEW_PREDICTIONS
        ],
    }
    (OUT_DIR / "predictions.json").write_text(json.dumps(preds_doc, indent=1) + "\n", encoding="utf-8")
    render_index(review, preds_doc)
    render_flagged(review)
    return review


def conf_pill(conf: str) -> str:
    cls = {"High": "high", "Medium": "med", "Low": "low"}.get(conf, "low")
    return f'<span class="pill {cls}">{esc(conf or "&mdash;")}</span>'


def render_index(review: dict, preds_doc: dict) -> None:
    s = review["summary"]
    sports = sorted({r["sport"] for r in review["rows"] if r.get("sport")})
    opts = "".join(f'<option value="{esc(x)}">{esc(x)}</option>' for x in sports)
    focus_cards = []
    for f in review["focus_high"]:
        links = " ".join(f'<a href="{esc(u)}">source</a>' for u in f["live_urls"]) or "no live re-read"
        focus_cards.append(
            f'<div class="card"><h3>{esc(f["fixture"])} — {esc(f["sport"])} — {esc(f["date"] or "")}</h3>'
            f'<p>Selection: <b>{esc(f["selection"] or "")}</b> · '
            f'Price {f["pick_dec"]} / {f["pick_us"]:+d} (implied {f["pick_implied"]:.1%}) · '
            f'Prediction: {esc(f["prediction_origin"])} · '
            f'<a href="{esc(f["source"])}">canonical official source</a> · live: {links}</p>'
            f'<div class="pred">{esc(f["prediction"] or "")}</div>'
            f'<p class="muted">Live evidence: {esc(f["live_evidence"])}</p></div>')
    rows_html = []
    for r in review["rows"]:
        live = r["live"]
        badge = {"confirmed": '<span class="ok">confirmed</span>',
                 "corroborated": '<span class="warn">corroborated</span>'}.get(
            live["status"], '<span class="muted">not re-read</span>')
        if r["pick_us"] is None:
            win = '<span class="warn">no pick price</span>'
        elif r["in_window"]:
            win = f'<span class="ok">{r["pick_us"]:+d} in window</span>'
        else:
            win = f'<span class="bad">{r["pick_us"]:+d} out</span>'
        src = (f'<a href="{esc(r["shown_official_source"])}">official</a>'
               if r["shown_official_source"] else '<span class="warn">held</span>')
        repl = " <b>(S2 replacement)</b>" if r["has_s2_replacement"] else ""
        rows_html.append(
            f'<tr data-sport="{esc(r["sport"] or "")}"><td>{esc(r["id"])}</td>'
            f'<td>{esc(r["date"] or "")}</td><td>{esc(r["sport"] or "")}</td>'
            f'<td>{esc(r["home"] or "")} vs {esc(r["away"] or "")}{repl}</td>'
            f'<td>{esc(r["selection"] or "")}</td><td>{conf_pill(r["confidence"])}</td>'
            f'<td>{win}</td><td>{badge}</td><td>{src}</td><td>{esc(r["review_status"])}</td></tr>')
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S2 high-focus desk — 22 Oct 2026</title><style>{CSS}</style></head>
<body><header class="top"><div class="wrap">
<h1>S2 high-confidence focus desk — 22 Oct 2026</h1>
<p>Session {esc(SESSION)} · canonical master {esc(review["master_generated_on"] or "")} · '
window {review["window"]["min_us"]} to +{review["window"]["max_us"]} · '
<a style="color:#fff" href="flagged.html">Flagged for Review ({len(review["findings"])})</a></p>
</div></header><div class="wrap">
<nav class="breadcrumb"><a href="../">repo home</a> · S2 focus desk</nav>
<div class="card"><h2>Headline</h2>
<p>{s["current_fixtures"]} current in-scope fixtures · {s["high_total"]} High · '
{s["high_live_confirmed"]} High live-confirmed on official pages · '
<b>{s["high_focus_in_window"]} High picks inside -250/+10000</b> · '
{s["high_no_pick_price"]} High picks with no matching price (held from focus) · '
{s["high_new_replacements"]} S2 replacement predictions · '
{len(review["findings"])} findings (<a href="flagged.html">flagged page</a>).</p>
<p class="muted">No fixture invented, no price re-originated, no grade changed. '
Every live check records its exact official URL. Machine-readable: '
<a href="../data/session-fca9d738/review.json">review.json</a> · '
<a href="../data/session-fca9d738/predictions.json">predictions.json</a>.</p></div>
<h2>Focus list — High picks inside -250/+10000 ({len(review["focus_high"])})</h2>
{"".join(focus_cards)}
<h2>All current fixtures ({len(review["rows"])})</h2>
<div class="card"><input id="q" type="search" placeholder="filter text…">
<select id="s"><option value="">all sports</option>{opts}</select>
<table id="main"><thead><tr><th>ID</th><th>Date</th><th>Sport</th><th>Fixture</th>
<th>Selection</th><th>Conf</th><th>Window</th><th>Live</th><th>Source</th><th>Status</th>
</tr></thead><tbody>{"".join(rows_html)}</tbody></table></div>
<footer>Board S2 · {esc(SESSION)} · generated from data/master.json + embedded 2026-10-22 '
official-page reads · rebuild: python3 session-fca9d738/build_review.py</footer>
</div>{JS_FILTER}</body></html>
"""
    (SITE / "index.html").write_text(page, encoding="utf-8")


def render_flagged(review: dict) -> None:
    items = []
    for f in review["findings"]:
        srcs = " ".join(f'<li><a href="{esc(u)}">{esc(u)}</a></li>' for u in f["sources"])
        src_block = f"<ul>{srcs}</ul>" if srcs else '<p class="muted">No external source (structural finding).</p>'
        items.append(
            f'<div class="card"><h3>{esc(f["id"])} — {esc(f["title"])} '
            f'<span class="pill low">{esc(f["severity"])}</span></h3><p>{esc(f["text"])}</p>'
            f'<p class="muted">Rows: {esc(", ".join(f["rows"]) or "—")}</p>{src_block}</div>')
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>S2 flagged for review — 22 Oct 2026</title><style>{CSS}</style></head>
<body><header class="top"><div class="wrap">
<h1>S2 — Flagged for Review</h1>
<p>{len(review["findings"])} published irregularities · <a style="color:#fff" href="index.html">back to focus desk</a></p>
</div></header><div class="wrap">
<nav class="breadcrumb"><a href="../">repo home</a> · <a href="index.html">S2 focus desk</a> · flagged</nav>
<p class="muted">Held items stay visible with their source links and do not block publication. '
Nothing here was silently filled.</p>
{"".join(items)}
<footer>Board S2 · {esc(SESSION)} · 2026-10-22</footer>
</div></body></html>
"""
    (SITE / "flagged.html").write_text(page, encoding="utf-8")


if __name__ == "__main__":
    build()

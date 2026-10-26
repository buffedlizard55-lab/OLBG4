#!/usr/bin/env python3
"""Build the capture target list for Board FB (session 53f83b8d).

Two families of target:

* ``olbg``     — OLBG's own 15-sport hubs, all-events category pages and (discovered
                 in a second pass inside ``fetch.py``) individual OLBG event pages.
                 These define the market universe: which matches OLBG is actually
                 listing, at which quoted price.
* ``official`` — the governing body / league / tour feed that carries the fixture,
                 the season record or the ranking used to originate our own price.

``proven`` targets are URLs a previous board recorded HTTP 200 for (manifests under
``data/session-*/capture/*/manifest.json``). ``probe`` targets are candidates; a
probe that fails is recorded in the manifest as a failure and never used.

Nothing here is data. It is only a list of where to look.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

# OLBG sport hub ids (read off the live hubs by Boards EC/A172).
OLBG_SPORTS = [
    ("Golf", 5),
    ("Volleyball", 21),
    ("Rugby_Union", 9),
    ("Cricket", 7),
    ("Snooker", 8),
    ("Darts", 15),
    ("Baseball", 12),
    ("Gaelic_Football", 25),
    ("Greyhounds", 28),
    ("Tennis", 3),
    ("Motor_Racing", 14),
    ("Handball", 20),
    ("Ice_Hockey", 13),
    ("Basketball", 4),
    ("Rugby_League", 10),
]

# Our canonical sport names, in the order the owner listed them.
SPORT_ORDER = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball",
    "Ice Hockey", "Basketball", "Rugby League",
]

OLBG_TO_SPORT = {
    "Golf": "Golf",
    "Volleyball": "Volleyball",
    "Rugby_Union": "Rugby Union",
    "Cricket": "Cricket",
    "Snooker": "Snooker",
    "Darts": "Darts",
    "Baseball": "Baseball",
    "Gaelic_Football": "Gaelic Sports",
    "Greyhounds": "Greyhounds",
    "Tennis": "Tennis",
    "Motor_Racing": "Motor Racing",
    "Handball": "Handball",
    "Ice_Hockey": "Ice Hockey",
    "Basketball": "Basketball",
    "Rugby_League": "Rugby League",
}


def olbg_targets() -> list[dict]:
    out = []
    for slug, sid in OLBG_SPORTS:
        sport = OLBG_TO_SPORT[slug]
        base = f"https://www.olbg.com/betting-tips/{slug}"
        out += [
            {"id": f"olbg_hub_{slug}", "sport": sport, "kind": "olbg",
             "tier": "proven", "url": f"{base}/{sid}"},
            {"id": f"olbg_hubdata_{slug}", "sport": sport, "kind": "olbg",
             "tier": "probe", "url": f"{base}/{sid}/__data.json"},
            {"id": f"olbg_allevents_{slug}", "sport": sport, "kind": "olbg",
             "tier": "probe",
             "url": f"{base}/All_{slug}/All_Events/{sid}"},
            {"id": f"olbg_alleventsdata_{slug}", "sport": sport, "kind": "olbg",
             "tier": "probe",
             "url": f"{base}/All_{slug}/All_Events/{sid}/__data.json"},
        ]
    out += [
        {"id": "olbg_hub_basketball_nba", "sport": "Basketball", "kind": "olbg",
         "tier": "proven", "url": "https://www.olbg.com/betting-tips/Basketball/NBA/4"},
        {"id": "olbg_hub_icehockey_nhl", "sport": "Ice Hockey", "kind": "olbg",
         "tier": "proven", "url": "https://www.olbg.com/betting-tips/Ice_Hockey/NHL/13"},
        {"id": "olbg_sitemap_tips", "sport": "all", "kind": "olbg",
         "tier": "proven", "url": "https://www.olbg.com/sitemap-betting-tips.xml"},
        {"id": "olbg_index", "sport": "all", "kind": "olbg", "tier": "proven",
         "url": "https://www.olbg.com/betting-tips"},
    ]
    return out


def official_targets(start: date, end: date) -> list[dict]:
    """Official feeds. ``nhl``, ``mlb``, ``wta`` and ``wst`` take a date window."""
    def t(id_, sport, url, tier):
        return {"id": id_, "sport": sport, "kind": "official", "tier": tier, "url": url}

    out: list[dict] = []

    # ---------------- Golf ----------------
    out += [
        t("owgr_ranking", "Golf", "https://www.owgr.com/current-world-ranking", "proven"),
        t("pgatour_schedule", "Golf", "https://www.pgatour.com/schedule", "proven"),
        t("pgatour_leaderboard", "Golf", "https://www.pgatour.com/leaderboard", "proven"),
        t("pgatour_fedex", "Golf", "https://www.pgatour.com/stats/stat.02671.html", "proven"),
        t("dpwt_schedule", "Golf", "https://www.europeantour.com/dpworld-tour/schedule", "proven"),
        t("lpga_schedule", "Golf", "https://www.lpga.com/tournaments", "proven"),
        t("lpga_leaderboard", "Golf", "https://www.lpga.com/leaderboard", "probe"),
        t("pgatour_bermuda", "Golf",
          "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528",
          "proven"),
        t("pgatour_api_lb", "Golf", "https://lbdata.pgatour.com/2026/r528/leaderboard.json", "probe"),
    ]

    # ---------------- Volleyball ----------------
    for cid in range(991, 1005):
        out.append(t(f"legavolley_cal_{cid}", "Volleyball",
                     f"https://www.legavolley.it/calendario/?Anno=2026&IdCampionato={cid}", "proven"))
    out += [
        t("legavolley_classifica", "Volleyball", "https://www.legavolley.it/classifica/", "proven"),
        t("plusliga_fixtures", "Volleyball", "https://www.plusliga.pl/mecze/tour/47.html", "proven"),
        t("plusliga_table", "Volleyball", "https://plusliga.pl/table/tour/47.html", "proven"),
        t("cvf_extraliga", "Volleyball",
          "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147", "proven"),
        t("vbl_home", "Volleyball", "https://www.volleyball-bundesliga.de/", "proven"),
        t("volleyballworld_vnl", "Volleyball",
          "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/", "proven"),
        t("cev_competitions", "Volleyball", "https://www.cev.eu/competitions/", "probe"),
    ]

    # ---------------- Rugby Union ----------------
    out += [
        t("world_rugby_rankings", "Rugby Union", "https://www.world.rugby/tournaments/rankings/mru", "proven"),
        t("prem_fixtures", "Rugby Union", "https://www.premiershiprugby.com/fixtures-results", "proven"),
        t("prem_standings", "Rugby Union", "https://www.premiershiprugby.com/standings", "proven"),
        t("top14_cal", "Rugby Union", "https://top14.lnr.fr/calendrier-et-resultats", "proven"),
        t("top14_classement", "Rugby Union", "https://top14.lnr.fr/classement", "proven"),
        t("urc_fixtures_in_full", "Rugby Union",
          "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", "proven"),
        t("urc_table", "Rugby Union", "https://stats.unitedrugby.com/match-centre/table/2026-27", "probe"),
        t("urc_fixtures_page", "Rugby Union", "https://www.unitedrugby.com/fixtures", "probe"),
        t("champions_cup", "Rugby Union",
          "https://www.epcrugby.com/champions-cup/fixtures", "probe"),
    ]

    # ---------------- Cricket ----------------
    out += [
        t("icc_t20i_rankings", "Cricket", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", "proven"),
        t("icc_odi_rankings", "Cricket", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", "proven"),
        t("icc_test_rankings", "Cricket", "https://www.icc-cricket.com/rankings/mens/team-rankings/test", "proven"),
        t("cricket_au_fixtures", "Cricket", "https://www.cricket.com.au/fixtures", "proven"),
        t("ecb_fixtures", "Cricket", "https://www.ecb.co.uk/england/men/fixtures", "proven"),
        t("nzc_matches", "Cricket", "https://www.nzc.nz/matches", "proven"),
        t("bcci_home", "Cricket", "https://www.bcci.tv/", "proven"),
        t("icc_fixtures", "Cricket", "https://www.icc-cricket.com/tournaments/fixtures", "probe"),
        t("bbl_fixtures", "Cricket", "https://www.bigbash.com.au/fixtures", "probe"),
    ]

    # ---------------- Snooker ----------------
    out += [
        t("wst_matches", "Snooker",
          "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=400"
          f"&filter[startDateTime][gte]={start.isoformat()}"
          f"&filter[startDateTime][lte]={end.isoformat()}", "proven"),
        t("wst_rankings", "Snooker", "https://www.wst.tv/rankings/", "proven"),
        t("wst_participants", "Snooker",
          "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=400", "proven"),
        t("wst_tournaments", "Snooker",
          "https://tournaments.snooker.web.gc.wstservices.co.uk/v2/?page.size=100", "probe"),
        t("snooker_org_cal", "Snooker", "https://www.snooker.org/res/index.asp?template=2", "proven"),
        t("wst_nio", "Snooker", "https://www.wst.tv/tournaments/northern-ireland-open-2026/", "proven"),
    ]

    # ---------------- Darts ----------------
    out += [
        t("pdc_participants", "Darts",
          "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=400", "proven"),
        t("pdc_matches", "Darts",
          "https://matches.darts.web.gc.pdcservices.co.uk/v2/?page.size=400"
          f"&filter[startDateTime][gte]={start.isoformat()}"
          f"&filter[startDateTime][lte]={end.isoformat()}", "probe"),
        t("pdc_tournaments_api", "Darts",
          "https://tournaments.darts.web.gc.pdcservices.co.uk/v2/?page.size=100", "probe"),
        t("pdc_oom", "Darts", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit", "proven"),
        t("pdc_calendar", "Darts", "https://www.pdc.tv/tournaments", "proven"),
    ]

    # ---------------- Baseball ----------------
    out += [
        t("mlb_schedule", "Baseball",
          "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
          f"&startDate={start.isoformat()}&endDate={end.isoformat()}"
          "&hydrate=probablePitcher,linescore,team,venue", "proven"),
        t("mlb_standings", "Baseball",
          "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"
          "&standingsTypes=regularSeason", "proven"),
        t("mlb_hitting", "Baseball",
          "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1",
          "proven"),
        t("mlb_pitching", "Baseball",
          "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1",
          "proven"),
        t("mlb_transactions", "Baseball",
          "https://statsapi.mlb.com/api/v1/transactions?sportId=1"
          f"&startDate={(start - timedelta(days=10)).isoformat()}&endDate={end.isoformat()}",
          "probe"),
        t("mlb_injuries", "Baseball",
          "https://statsapi.mlb.com/api/v1/sports/1/players?rosterType=fullRoster", "probe"),
    ]

    # ---------------- Gaelic ----------------
    out += [
        t("gaa_fixtures", "Gaelic Sports", "https://www.gaa.ie/fixtures", "proven"),
        t("gaa_results", "Gaelic Sports", "https://www.gaa.ie/fixtures-results", "proven"),
        t("gaacork_fixtures", "Gaelic Sports", "https://gaacork.ie/fixtures", "proven"),
        t("ladies_gaelic", "Gaelic Sports", "https://ladiesgaelic.ie/", "proven"),
        t("gaa_api", "Gaelic Sports", "https://www.gaa.ie/api/fixtures/", "probe"),
    ]

    # ---------------- Greyhounds ----------------
    out += [
        t("gbgb_results", "Greyhounds",
          "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100"
          f"&date={(start - timedelta(days=1)).isoformat()}&race_type=race", "proven"),
        t("gbgb_races_today", "Greyhounds",
          f"https://api.gbgb.org.uk/api/races?date={start.isoformat()}&page=1&itemsPerPage=200", "probe"),
        t("gbgb_meetings_today", "Greyhounds",
          f"https://api.gbgb.org.uk/api/meetings?date={start.isoformat()}", "probe"),
        t("gbgb_racecards", "Greyhounds", "https://www.gbgb.org.uk/racecards/", "probe"),
        t("gbgb_fixtures", "Greyhounds", "https://www.gbgb.org.uk/fixtures/", "probe"),
    ]

    # ---------------- Tennis ----------------
    out += [
        t("wta_tournaments", "Tennis",
          "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100", "proven"),
        t("wta_rankings", "Tennis",
          "https://api.wtatennis.com/tennis/players/rankings/singles?page=0&pageSize=200", "probe"),
        t("wta_1023", "Tennis", "https://api.wtatennis.com/tennis/tournaments/1023/2026/matches", "proven"),
        t("wta_1056", "Tennis", "https://api.wtatennis.com/tennis/tournaments/1056/2026/matches", "proven"),
        t("wta_2092", "Tennis", "https://api.wtatennis.com/tennis/tournaments/2092/2026/matches", "proven"),
        t("wta_405", "Tennis", "https://api.wtatennis.com/tennis/tournaments/405/2026/matches", "proven"),
        t("atp_rankings_api", "Tennis",
          "https://api.atptour.com/rankings/singles?rankRange=1-200&format=json", "probe"),
        t("atp_rankings_html", "Tennis",
          "https://www.atptour.com/en/rankings/singles", "probe"),
    ]

    # ---------------- Motor Racing ----------------
    out += [
        t("f1_season", "Motor Racing", "https://www.formula1.com/en/racing/2026.html", "proven"),
        t("f1_drivers", "Motor Racing", "https://www.formula1.com/en/results/2026/drivers", "proven"),
        t("f1_teams", "Motor Racing", "https://www.formula1.com/en/results/2026/team", "proven"),
        t("f1_mexico", "Motor Racing", "https://www.formula1.com/en/racing/2026/mexico", "proven"),
        t("f1_brazil", "Motor Racing", "https://www.formula1.com/en/racing/2026/brazil", "proven"),
        t("f1_races_results", "Motor Racing", "https://www.formula1.com/en/results/2026/races", "probe"),
        t("motogp_calendar", "Motor Racing", "https://www.motogp.com/en/calendar/2026", "proven"),
        t("indycar_schedule", "Motor Racing", "https://www.indycar.com/Schedule", "proven"),
        t("fia_f2", "Motor Racing", "https://www.fiaformula2.com/", "proven"),
    ]

    # ---------------- Handball ----------------
    out += [
        t("ehfcl_m_matches", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/matches/", "proven"),
        t("ehfcl_m_standings", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/standings/", "proven"),
        t("ehfcl_w_matches", "Handball", "https://ehfcl.eurohandball.com/women/2026-27/matches/", "proven"),
        t("ehfel_m_matches", "Handball", "https://ehfel.eurohandball.com/men/2026-27/matches/", "proven"),
        t("hbl_spielplan", "Handball", "https://www.dkb-handball-bundesliga.de/spielplan", "proven"),
        t("hbl_tabelle", "Handball", "https://www.dkb-handball-bundesliga.de/tabelle", "proven"),
        t("dk_herreligaen", "Handball", "https://tophaandbold.dk/stillinger/herreligaen", "proven"),
        t("dk_program", "Handball", "https://tophaandbold.dk/kampprogram/herreligaen", "proven"),
        t("handbollsligan", "Handball", "https://handbollsligan.se/", "proven"),
        t("ehf_matches_api", "Handball",
          "https://ehfcl.eurohandball.com/api/v1/matches?season=2026", "probe"),
        t("eurohandball_matches", "Handball", "https://www.eurohandball.com/en/matches/", "probe"),
    ]

    # ---------------- Ice Hockey ----------------
    out += [
        t("nhl_standings", "Ice Hockey", "https://api-web.nhle.com/v1/standings/now", "proven"),
        t("nhl_skaters", "Ice Hockey",
          "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals,points&limit=25",
          "proven"),
        t("nhl_goalies", "Ice Hockey",
          "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=savePctg,goalsAgainstAverage&limit=25",
          "proven"),
        t("shl_overview", "Ice Hockey", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961", "proven"),
        t("shl_standings", "Ice Hockey", "https://stats.swehockey.se/ScheduleAndResults/Standings/20961", "proven"),
        t("liiga_games", "Ice Hockey", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", "proven"),
        t("liiga_standings", "Ice Hockey", "https://liiga.fi/api/v2/standings/?season=2027", "proven"),
    ]
    # NHL schedule: one call per day across the window (proven endpoint shape).
    day = start
    while day <= end:
        out.append(t(f"nhl_sched_{day.isoformat()}", "Ice Hockey",
                     f"https://api-web.nhle.com/v1/schedule/{day.isoformat()}", "proven"))
        day += timedelta(days=1)
    # NHL injury/roster feed for the clubs that appear: probed generically, parsed later.
    for i, url in enumerate([
        "https://api-web.nhle.com/v1/roster/ANA/current",
        "https://api-web.nhle.com/v1/roster/BOS/current",
    ]):
        out.append(t(f"nhl_roster_{i}", "Ice Hockey", url, "probe"))

    # ---------------- Basketball ----------------
    out += [
        t("nba_schedule_full", "Basketball",
          "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", "proven"),
        t("nba_standings", "Basketball",
          "https://cdn.nba.com/static/json/liveData/standings/standings.json", "probe"),
        t("el_games", "Basketball",
          "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", "proven"),
        t("eurocup_games", "Basketball",
          "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games", "proven"),
        t("el_standings", "Basketball",
          "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings", "probe"),
        t("acb_calendario", "Basketball", "https://www.acb.com/calendario/", "proven"),
        t("acb_clasificacion", "Basketball", "https://www.acb.com/clasificacion/", "proven"),
        t("lega_basket", "Basketball", "https://www.legabasket.it/", "proven"),
    ]

    # ---------------- Rugby League ----------------
    out += [
        t("rlwc_api_fixtures", "Rugby League", "https://www.rlwc2026.com/api/fixtures", "proven"),
        t("rlwc_fixtures", "Rugby League", "https://www.rlwc2026.com/fixtures", "proven"),
        t("rlwc_results", "Rugby League", "https://www.rlwc2026.com/results", "proven"),
        t("rlwc_draws", "Rugby League", "https://www.rlwc2026.com/draws-and-pools", "proven"),
        t("superleague_fixtures", "Rugby League", "https://www.superleague.co.uk/fixtures", "probe"),
        t("nrl_draw", "Rugby League", "https://www.nrl.com/draw/", "probe"),
        t("nrl_ladder", "Rugby League", "https://www.nrl.com/ladder/", "probe"),
    ]
    return out


def build(start: date, end: date) -> dict:
    return {
        "session": "53f83b8d",
        "board": "FB",
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "sport_order": SPORT_ORDER,
        "targets": olbg_targets() + official_targets(start, end),
    }


if __name__ == "__main__":
    start = date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else date.today()
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 14
    doc = build(start, start + timedelta(days=days))
    out = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("scripts/session-53f83b8d/targets.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1))
    kinds = {}
    for x in doc["targets"]:
        kinds[x["kind"]] = kinds.get(x["kind"], 0) + 1
    print(f"wrote {out}: {len(doc['targets'])} targets {kinds} window {doc['window_start']}..{doc['window_end']}")

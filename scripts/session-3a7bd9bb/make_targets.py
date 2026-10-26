#!/usr/bin/env python3
"""Board CB (session arena/3a7bd9bb-olbg4) — build the capture target list.

    python3 scripts/session-3a7bd9bb/make_targets.py

Writes scripts/session-3a7bd9bb/targets.json deterministically. Two families of target:

  * olbg_*    — OLBG's own 15 in-scope sport boards (the market list the brief is about).
  * everything else — an official governing-body / league / tour / statutory page that can
    confirm or contradict what OLBG lists, for the 2026-10-26 .. 2026-11-08 window.

Nothing is fetched here; fetch.py does that on an egress-open Actions runner.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parent / "targets.json"

OLBG = "https://www.olbg.com"

# sport label -> OLBG sport id used in the site's own URLs
SPORTS = {
    "Golf": 5,
    "Volleyball": 21,
    "Rugby Union": 9,
    "Cricket": 7,
    "Snooker": 8,
    "Darts": 15,
    "Baseball": 12,
    "Gaelic Sports": 25,
    "Hurling": 26,
    "Greyhounds": 28,
    "Tennis": 3,
    "Motor Racing": 14,
    "Handball": 20,
    "Ice Hockey": 13,
    "Basketball": 4,
    "Rugby League": 10,
}

HUBS = [
    ("olbg_golf", "Golf", "/betting-tips/Golf/5"),
    ("olbg_volleyball", "Volleyball", "/betting-tips/Volleyball/21"),
    ("olbg_rugby_union", "Rugby Union", "/betting-tips/Rugby_Union/9"),
    ("olbg_cricket", "Cricket", "/betting-tips/Cricket/7"),
    ("olbg_snooker", "Snooker", "/betting-tips/Snooker/8"),
    ("olbg_darts", "Darts", "/betting-tips/Darts/15"),
    ("olbg_baseball", "Baseball", "/betting-tips/Baseball/12"),
    ("olbg_gaelic", "Gaelic Sports", "/betting-tips/Gaelic_Football/25"),
    ("olbg_hurling", "Gaelic Sports", "/betting-tips/Hurling/26"),
    ("olbg_greyhounds", "Greyhounds", "/betting-tips/Greyhounds/28"),
    ("olbg_tennis", "Tennis", "/betting-tips/Tennis/3"),
    ("olbg_motor_racing", "Motor Racing", "/betting-tips/Motor_Racing/14"),
    ("olbg_handball", "Handball", "/betting-tips/Handball/20"),
    ("olbg_ice_hockey", "Ice Hockey", "/betting-tips/Ice_Hockey/13"),
    ("olbg_basketball", "Basketball", "/betting-tips/Basketball/4"),
    ("olbg_rugby_league", "Rugby League", "/betting-tips/Rugby_League/10"),
    # competition-level boards OLBG exposes under the same sport id
    ("olbg_bb_nba", "Basketball", "/betting-tips/Basketball/NBA/USA/4"),
    ("olbg_bb_euroleague", "Basketball", "/betting-tips/Basketball/Euroleague/Europe/4"),
    ("olbg_bb_plk", "Basketball", "/betting-tips/Basketball/Poland/Poland/4"),
    ("olbg_ih_nhl", "Ice Hockey", "/betting-tips/Ice_Hockey/NHL/USA/13"),
    ("olbg_ih_shl", "Ice Hockey", "/betting-tips/Ice_Hockey/Sweden/Sweden/13"),
    ("olbg_mlb", "Baseball", "/betting-tips/Baseball/Major_League_Baseball/USA/12"),
    ("olbg_golf_pga", "Golf", "/betting-tips/Golf/USA/US_PGA_Tour/5"),
    ("olbg_golf_dpwt", "Golf", "/betting-tips/Golf/Europe/European_Tour/5"),
    # "all events" listings — checked to see whether OLBG exposes a multi-day list
    ("olbg_all_tennis", "Tennis", "/betting-tips/Tennis/All_Tennis/All_Events/3"),
    ("olbg_all_cricket", "Cricket", "/betting-tips/Cricket/All_Cricket/All_Events/7"),
    ("olbg_all_snooker", "Snooker", "/betting-tips/Snooker/All_Snooker/All_Events/8"),
    ("olbg_all_darts", "Darts", "/betting-tips/Darts/All_Darts/All_Events/15"),
    ("olbg_all_handball", "Handball", "/betting-tips/Handball/All_Handball/All_Events/20"),
    ("olbg_all_volleyball", "Volleyball", "/betting-tips/Volleyball/All_Volleyball/All_Events/21"),
    ("olbg_all_ice_hockey", "Ice Hockey", "/betting-tips/Ice_Hockey/All_Ice_Hockey/All_Events/13"),
    ("olbg_all_basketball", "Basketball", "/betting-tips/Basketball/All_Basketball/All_Events/4"),
    ("olbg_all_baseball", "Baseball", "/betting-tips/Baseball/All_Baseball/All_Events/12"),
    ("olbg_all_rugby_union", "Rugby Union", "/betting-tips/Rugby_Union/All_Rugby_Union/All_Events/9"),
    ("olbg_all_rugby_league", "Rugby League", "/betting-tips/Rugby_League/All_Rugby_League/All_Events/10"),
    ("olbg_all_golf", "Golf", "/betting-tips/Golf/All_Golf/All_Events/5"),
    ("olbg_all_motor", "Motor Racing", "/betting-tips/Motor_Racing/All_Motor_Racing/All_Events/14"),
    ("olbg_all_gaelic", "Gaelic Sports", "/betting-tips/Gaelic_Football/All_Gaelic_Football/All_Events/25"),
    ("olbg_all_greyhounds", "Greyhounds", "/betting-tips/Greyhounds/All_Greyhounds/All_Events/28"),
    # date/pagination probes on a high-volume sport
    ("olbg_probe_tennis_date", "Tennis", "/betting-tips/Tennis/3?date=2026-10-27"),
    ("olbg_probe_tennis_page2", "Tennis", "/betting-tips/Tennis/3?page=2"),
]

OFFICIAL = [
    # ---- Ice hockey -------------------------------------------------------
    ("nhl_standings", "Ice Hockey", "https://api-web.nhle.com/v1/standings/now"),
    ("nhl_roster_nyr", "Ice Hockey", "https://api-web.nhle.com/v1/roster/NYR/current"),
    ("nhl_roster_edm", "Ice Hockey", "https://api-web.nhle.com/v1/roster/EDM/current"),
    ("nhl_roster_tor", "Ice Hockey", "https://api-web.nhle.com/v1/roster/TOR/current"),
    ("nhl_roster_bos", "Ice Hockey", "https://api-web.nhle.com/v1/roster/BOS/current"),
    ("nhl_roster_col", "Ice Hockey", "https://api-web.nhle.com/v1/roster/COL/current"),
    ("nhl_roster_veg", "Ice Hockey", "https://api-web.nhle.com/v1/roster/VGK/current"),
    ("nhl_club_stats", "Ice Hockey", "https://api-web.nhle.com/v1/club-stats/EDM/now/season"),
    # ---- Baseball ---------------------------------------------------------
    ("mlb_postseason", "Baseball",
     "https://statsapi.mlb.com/api/v1/schedule/postseason?season=2026&hydrate=team,linescore,probablePitcher"),
    ("mlb_schedule_window", "Baseball",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-26&endDate=2026-11-08"
     "&hydrate=probablePitcher,team,linescore,venue"),
    ("mlb_standings", "Baseball",
     "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason"),
    ("mlb_team_hitting", "Baseball",
     "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&sportIds=1&group=hitting&stats=season"),
    ("mlb_team_pitching", "Baseball",
     "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&sportIds=1&group=pitching&stats=season"),
    # ---- Basketball -------------------------------------------------------
    ("el_games", "Basketball", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"),
    ("el_standings_r7", "Basketball",
     "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/rounds/7/standings"),
    ("el_standings_r8", "Basketball",
     "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/rounds/8/standings"),
    ("nba_injury_report", "Basketball", "https://official.nba.com/nba-injury-report-2026-27-season/"),
    ("nba_games_26", "Basketball", "https://www.nba.com/games?date=2026-10-26"),
    ("nba_games_27", "Basketball", "https://www.nba.com/games?date=2026-10-27"),
    ("nba_games_28", "Basketball", "https://www.nba.com/games?date=2026-10-28"),
    # ---- Tennis -----------------------------------------------------------
    ("wta_tournaments", "Tennis",
     "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=30&from=2026-10-26&to=2026-11-09"),
    ("wta_rankings", "Tennis",
     "https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankSingles&sort=asc"),
    ("wta_rankings_page", "Tennis", "https://www.wtatennis.com/rankings/singles"),
    ("atp_race_page", "Tennis", "https://www.atptour.com/en/rankings/singles"),
    ("atp_paris_mds", "Tennis", "https://www.protennislive.com/posting/2026/352/mds.pdf"),
    ("atp_paris_q", "Tennis", "https://www.protennislive.com/posting/2026/352/qs.pdf"),
    ("atp_rankings_pdf", "Tennis",
     "https://www.protennislive.com/posting/ramr/current_men_rankings.pdf"),
    # ---- Cricket ----------------------------------------------------------
    ("icc_schedule", "Cricket", "https://www.icc-cricket.com/tournaments/champions-trophy-2026/matches"),
    ("icc_mens_fixtures", "Cricket", "https://www.icc-cricket.com/fixtures-results/mens"),
    ("icc_t20_rankings", "Cricket", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i"),
    ("icc_odi_rankings", "Cricket", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi"),
    ("nzc_schedule", "Cricket", "https://www.nzc.nz/schedule"),
    ("ecb_men_fixtures", "Cricket", "https://www.ecb.co.uk/england/men/fixtures"),
    ("ca_fixtures", "Cricket", "https://www.cricket.com.au/matches"),
    ("bcci_home", "Cricket", "https://www.bcci.tv/"),
    # ---- Snooker ----------------------------------------------------------
    ("wst_rankings", "Snooker", "https://www.wst.tv/rankings/"),
    ("wst_matches", "Snooker", "https://www.wst.tv/matches/"),
    ("wst_ni_open_hub", "Snooker",
     "https://www.wst.tv/tournaments/betvictor-northern-ireland-open/"),
    ("wst_news_index", "Snooker", "https://www.wst.tv/news/"),
    # ---- Darts ------------------------------------------------------------
    ("pdc_oom", "Darts", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit"),
    ("pdc_calendar", "Darts", "https://www.pdc.tv/tournaments/calendar"),
    ("pdc_ec_hub", "Darts",
     "https://www.pdc.tv/tournaments/machineseeker-european-championship"),
    ("pdc_players_championship", "Darts",
     "https://www.pdc.tv/tournaments/players-championship-finals"),
    # ---- Golf -------------------------------------------------------------
    ("pga_schedule", "Golf", "https://www.pgatour.com/schedule"),
    ("pga_leaderboard", "Golf", "https://www.pgatour.com/leaderboard"),
    ("lpga_schedule", "Golf", "https://www.lpga.com/tournaments"),
    ("owgr_ranking", "Golf", "https://www.owgr.com/ranking"),
    # ---- Motor racing -----------------------------------------------------
    ("f1_schedule", "Motor Racing", "https://www.formula1.com/en/racing/2026"),
    ("f1_mexico", "Motor Racing", "https://www.formula1.com/en/racing/2026/mexico"),
    ("f1_brazil", "Motor Racing", "https://www.formula1.com/en/racing/2026/brazil"),
    ("f1_drivers", "Motor Racing", "https://www.formula1.com/en/results/2026/drivers"),
    ("f1_teams", "Motor Racing", "https://www.formula1.com/en/results/2026/team"),
    ("motogp_calendar", "Motor Racing", "https://www.motogp.com/en/calendar"),
    ("motogp_standings", "Motor Racing",
     "https://www.motogp.com/en/world-standing/2026/motogp/championship-standings"),
    # ---- Gaelic sports ----------------------------------------------------
    ("gaa_national_fixtures", "Gaelic Sports", "https://www.gaa.ie/fixtures-results"),
    ("gaa_munster_calendar", "Gaelic Sports", "https://munster.gaa.ie/fixtures/events-calendar/"),
    ("gaa_cork_fixtures", "Gaelic Sports", "https://gaacork.ie/fixtures/"),
    ("gaa_galway_fixtures", "Gaelic Sports", "https://galwaygaa.ie/fixtures/"),
    ("gaa_ulster_fixtures", "Gaelic Sports", "https://ulster.gaa.ie/fixtures/"),
    # ---- Greyhounds -------------------------------------------------------
    ("gri_upcoming_cards", "Greyhounds", "https://www.grireland.ie/racing/upcoming-race-cards/"),
    ("gri_results", "Greyhounds", "https://www.grireland.ie/racing/results/"),
    ("gbgb_open_races", "Greyhounds", "https://www.gbgb.org.uk/racing/open-races/"),
    ("gbgb_racecards", "Greyhounds", "https://www.gbgb.org.uk/racing/racecards/"),
    # ---- Handball ---------------------------------------------------------
    ("ehfcl_men_matches", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    ("ehfcl_men_standings", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/standings/"),
    ("ehfcl_women_matches", "Handball", "https://ehfcl.eurohandball.com/women/2026-27/matches/"),
    ("ehfel_women_matches", "Handball", "https://ehfel.eurohandball.com/women/2026-27/matches/"),
    ("handbollsligan_schema", "Handball", "https://handbollsligan.se/schema/"),
    ("asobal_home", "Handball", "https://www.asobal.es/"),
    ("dk_herreligaen_program", "Handball", "https://tophaandbold.dk/kampprogram/herreligaen"),
    # ---- Volleyball -------------------------------------------------------
    ("legavolley_cal", "Volleyball", "https://www.legavolley.it/calendario/?idCampionato=999"),
    ("legavolley_classifica", "Volleyball", "https://www.legavolley.it/classifica/"),
    ("plusliga_games", "Volleyball", "https://www.plusliga.pl/games.html"),
    ("plusliga_table", "Volleyball", "https://www.plusliga.pl/table.html"),
    ("cvf_extraliga", "Volleyball", "https://www.cvf.cz/extraliga-muzi/"),
    ("volley_nl", "Volleyball", "https://www.volleybal.nl/competitie/eredivisie-heren"),
    ("volley_fr", "Volleyball", "https://www.lnv.fr/calendrier"),
    # ---- Rugby union ------------------------------------------------------
    ("prem_fixtures", "Rugby Union", "https://www.premiershiprugby.com/fixtures-results/"),
    ("prem_standings", "Rugby Union", "https://www.premiershiprugby.com/standings/"),
    ("top14_calendrier", "Rugby Union", "https://top14.lnr.fr/calendrier-et-resultats"),
    ("top14_classement", "Rugby Union", "https://top14.lnr.fr/classement"),
    ("urc_home", "Rugby Union", "https://www.unitedrugby.com/"),
    ("urc_matchcentre", "Rugby Union", "https://www.unitedrugby.com/match-centre"),
    ("epcr_champions_cup", "Rugby Union", "https://www.epcrugby.com/champions-cup/fixtures"),
    # ---- Rugby league -----------------------------------------------------
    ("rlwc_draw", "Rugby League", "https://www.rlwc2026.com/draw"),
    ("rlwc_fixtures", "Rugby League", "https://www.rlwc2026.com/fixtures"),
    ("rfl_fixtures", "Rugby League", "https://www.rugby-league.com/fixtures-results"),
    ("superleague_fixtures", "Rugby League", "https://www.superleague.co.uk/fixtures"),
]


def main() -> int:
    targets: list[dict] = [
        {"id": "olbg_robots", "sport": "OLBG", "url": f"{OLBG}/robots.txt"},
        {"id": "olbg_sitemap", "sport": "OLBG", "url": f"{OLBG}/sitemap.xml"},
        {"id": "olbg_sitemap_tips", "sport": "OLBG", "url": f"{OLBG}/sitemap-betting-tips.xml"},
        {"id": "olbg_home", "sport": "OLBG", "url": f"{OLBG}/betting-tips"},
    ]
    for tid, sport, path in HUBS:
        targets.append({"id": tid, "sport": sport, "url": f"{OLBG}{path}"})

    # NHL schedule for every day of the window (the API is a plain GET, one call per date)
    day = date(2026, 10, 26)
    while day <= date(2026, 11, 8):
        targets.append({
            "id": f"nhl_sched_{day.isoformat()}",
            "sport": "Ice Hockey",
            "url": f"https://api-web.nhle.com/v1/schedule/{day.isoformat()}",
        })
        day += timedelta(days=1)

    for tid, sport, url in OFFICIAL:
        targets.append({"id": tid, "sport": sport, "url": url})

    OUT.write_text(json.dumps(targets, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {len(targets)} targets to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

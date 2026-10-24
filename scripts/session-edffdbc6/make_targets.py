#!/usr/bin/env python3
"""Board ZZ (session arena/edffdbc6-olbg4) — build the static capture target list.

Targets are official governing-body / league / tour / track endpoints (plus OLBG's own public
sport hubs for the 15 in-scope categories, used only to observe what OLBG lists).  Dates are
computed from the desk window so the file is reproducible for the 2026-10-24 → 2026-11-09 run.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent

WINDOW_START = date(2026, 10, 24)
WINDOW_END = date(2026, 11, 9)

OLBG_HUBS = [
    ("olbg_golf", "Golf", "https://www.olbg.com/betting-tips/Golf/5"),
    ("olbg_volleyball", "Volleyball", "https://www.olbg.com/betting-tips/Volleyball/21"),
    ("olbg_rugby_union", "Rugby Union", "https://www.olbg.com/betting-tips/Rugby_Union/9"),
    ("olbg_cricket", "Cricket", "https://www.olbg.com/betting-tips/Cricket/7"),
    ("olbg_snooker", "Snooker", "https://www.olbg.com/betting-tips/Snooker/8"),
    ("olbg_darts", "Darts", "https://www.olbg.com/betting-tips/Darts/15"),
    ("olbg_baseball", "Baseball", "https://www.olbg.com/betting-tips/Baseball/12"),
    ("olbg_gaelic_football", "Gaelic Sports", "https://www.olbg.com/betting-tips/Gaelic_Football/25"),
    ("olbg_hurling", "Gaelic Sports", "https://www.olbg.com/betting-tips/Hurling/26"),
    ("olbg_greyhounds", "Greyhounds", "https://www.olbg.com/betting-tips/Greyhounds/28"),
    ("olbg_tennis", "Tennis", "https://www.olbg.com/betting-tips/Tennis/3"),
    ("olbg_motor_racing", "Motor Racing", "https://www.olbg.com/betting-tips/Motor_Racing/14"),
    ("olbg_handball", "Handball", "https://www.olbg.com/betting-tips/Handball/20"),
    ("olbg_ice_hockey", "Ice Hockey", "https://www.olbg.com/betting-tips/Ice_Hockey/13"),
    ("olbg_basketball", "Basketball", "https://www.olbg.com/betting-tips/Basketball/4"),
    ("olbg_rugby_league", "Rugby League", "https://www.olbg.com/betting-tips/Rugby_League/10"),
    ("olbg_ice_hockey_nhl", "Ice Hockey", "https://www.olbg.com/betting-tips/Ice_Hockey/NHL/USA/13"),
    ("olbg_basketball_nba", "Basketball", "https://www.olbg.com/betting-tips/Basketball/NBA/USA/4"),
    ("olbg_basketball_el", "Basketball", "https://www.olbg.com/betting-tips/Basketball/Euroleague/Europe/4"),
    ("olbg_baseball_mlb", "Baseball", "https://www.olbg.com/betting-tips/Baseball/Major_League_Baseball/USA/12"),
]

STATIC = [
    # --- OLBG site itself (reverse-engineering: taxonomy, listing, robots) ---
    ("olbg_robots", "OLBG", "https://www.olbg.com/robots.txt"),
    ("olbg_sitemap", "OLBG", "https://www.olbg.com/sitemap.xml"),
    ("olbg_home", "OLBG", "https://www.olbg.com/betting-tips"),

    # --- Ice Hockey: NHL schedule/standings API, Liiga, SHL ---
    ("nhl_standings_now", "Ice Hockey", "https://api-web.nhle.com/v1/standings/now"),
    ("nhl_schedule_now", "Ice Hockey", "https://api-web.nhle.com/v1/schedule/now"),
    ("liiga_games_2027", "Ice Hockey", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027"),
    ("shl_games", "Ice Hockey",
     "https://www.shl.se/api/sports-v2/game-schedule?seasonUuid=s4y-994162547&seriesUuid=qQ9-af3704004p"
     "&gameTypeUuid=qQ9-af3704004p&gamePlace=all&played=all"),

    # --- Baseball: MLB Stats API ---
    ("mlb_schedule_window", "Baseball",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-24&endDate=2026-11-09"
     "&hydrate=probablePitcher,team,linescore"),
    ("mlb_postseason_2026", "Baseball",
     "https://statsapi.mlb.com/api/v1/schedule/postseason?season=2026&hydrate=team,linescore,decisions"),
    ("mlb_standings_2026", "Baseball",
     "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason"),
    ("mlb_teams_hitting_2026", "Baseball",
     "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&sportIds=1&group=hitting&stats=season"),
    ("mlb_teams_pitching_2026", "Baseball",
     "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&sportIds=1&group=pitching&stats=season"),

    # --- Basketball: NBA official CDN schedule + EuroLeague ---
    ("nba_schedule_league", "Basketball", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json"),
    ("nba_scoreboard_today", "Basketball", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json"),
    ("euroleague_games_e2026", "Basketball",
     "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"),
    ("euroleague_standings_e2026", "Basketball",
     "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/rounds/6/standings"),

    # --- Tennis: WTA official API (tournaments + rankings) ---
    ("wta_tournaments_window", "Tennis",
     "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=60&from=2026-10-20&to=2026-11-10"),
    ("wta_rankings_singles", "Tennis",
     "https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankSingles&sort=asc"),
    ("atp_rankings_home", "Tennis", "https://www.atptour.com/en/rankings/singles"),
    ("atp_vienna_home", "Tennis", "https://www.atptour.com/en/tournaments/vienna/336/overview"),
    ("atp_basel_home", "Tennis", "https://www.atptour.com/en/tournaments/basel/328/overview"),
    ("atp_paris_home", "Tennis", "https://www.atptour.com/en/tournaments/paris/352/overview"),

    # --- Snooker: snooker.org calendar (dynamic event pages) + WST ---
    ("snooker_calendar", "Snooker", "https://www.snooker.org/res/index.asp?template=4&season=2026"),
    ("snooker_org_2548", "Snooker", "https://www.snooker.org/res/index.asp?event=2548"),
    ("wst_matches", "Snooker", "https://www.wst.tv/matches/"),
    ("wst_rankings", "Snooker", "https://www.wst.tv/rankings/"),

    # --- Darts: PDC official ---
    ("pdc_participants_api", "Darts", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100"),
    ("pdc_tournament_hub_10870", "Darts", "https://www.pdc.tv/tournament-hub/10870"),
    ("pdc_calendar", "Darts", "https://www.pdc.tv/tournaments/calendar"),
    ("pdc_oom", "Darts", "https://www.pdc.tv/order-of-merit/pdc-order-merit"),
    ("pdc_matches", "Darts", "https://www.pdc.tv/matches"),
    ("pdc_ec_day2", "Darts",
     "https://www.pdc.tv/news/2026/october/23/2026-machineseeker-european-championship---day-two-latest"),
    ("pdc_ec_day3", "Darts",
     "https://www.pdc.tv/news/2026/october/24/2026-machineseeker-european-championship---day-three-latest"),
    ("pdc_ec_preview", "Darts",
     "https://www.pdc.tv/news/2026/10/22/2026-machineseeker-european-championship-preview"),

    # --- Volleyball ---
    ("legavolley_cal_999", "Volleyball", "https://www.legavolley.it/calendario/?idCampionato=999"),
    ("legavolley_classifica", "Volleyball", "https://www.legavolley.it/classifica/"),
    ("plusliga_games", "Volleyball", "https://www.plusliga.pl/games.html"),
    ("plusliga_table", "Volleyball", "https://www.plusliga.pl/table.html"),
    ("cvf_extraliga", "Volleyball", "https://www.cvf.cz/extraliga-muzi/"),

    # --- Handball ---
    ("ehfcl_men_matches", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    ("ehfcl_men_standings", "Handball", "https://ehfcl.eurohandball.com/men/2026-27/standings/"),
    ("ehfcl_women_matches", "Handball", "https://ehfcl.eurohandball.com/women/2026-27/matches/"),
    ("ehfcl_women_standings", "Handball", "https://ehfcl.eurohandball.com/women/2026-27/standings/"),
    ("dk_herreligaen_program", "Handball", "https://tophaandbold.dk/kampprogram/herreligaen"),
    ("dk_herreligaen_stilling", "Handball", "https://tophaandbold.dk/stilling/herreligaen"),
    ("de_hbl_spielplan", "Handball", "https://www.handball-bundesliga.de/spielplan"),
    ("fr_liquimoly_results", "Handball", "https://www.lnh.fr/liquimoly-starligue/calendrier-et-resultats"),

    # --- Rugby Union ---
    ("urc_fixtures", "Rugby Union", "https://www.unitedrugby.com/fixtures-and-results"),
    ("urc_standings", "Rugby Union", "https://www.unitedrugby.com/standings"),
    ("top14_calendrier", "Rugby Union", "https://top14.lnr.fr/calendrier-et-resultats"),
    ("top14_classement", "Rugby Union", "https://top14.lnr.fr/classement"),
    ("prem_fixtures", "Rugby Union", "https://www.premiershiprugby.com/fixtures-results/"),
    ("prem_standings", "Rugby Union", "https://www.premiershiprugby.com/standings/"),

    # --- Rugby League ---
    ("rlwc2026_draw", "Rugby League", "https://www.rlwc2026.com/draw"),
    ("nrl_rlwc_r3", "Rugby League", "https://www.nrl.com/draw/?competition=175&round=3&season=2026"),
    ("nrl_rlwc_r4", "Rugby League", "https://www.nrl.com/draw/?competition=175&round=4&season=2026"),
    ("nrl_rlwc_r3_data", "Rugby League",
     "https://www.nrl.com/draw/data?competition=175&round=3&season=2026"),
    ("nrl_ladder", "Rugby League", "https://www.nrl.com/ladder/?competition=175&season=2026"),

    # --- Cricket ---
    ("icc_fixtures", "Cricket", "https://www.icc-cricket.com/tournaments/womens-t20-world-cup-2026/matches"),
    ("ca_fixtures", "Cricket", "https://www.cricket.com.au/matches"),
    ("bcci_home", "Cricket", "https://www.bcci.tv/"),
    ("nzc_home", "Cricket", "https://www.nzc.nz/"),
    ("pcb_home", "Cricket", "https://www.pcb.com.pk/"),
    ("ecb_fixtures", "Cricket", "https://www.ecb.co.uk/matches"),

    # --- Golf ---
    ("pga_leaderboard", "Golf", "https://www.pgatour.com/leaderboard"),
    ("pga_schedule_2026", "Golf", "https://www.pgatour.com/schedule"),
    ("pga_bermuda", "Golf", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528"),
    ("dpwt_schedule_2026", "Golf", "https://www.europeantour.com/dpworld-tour/schedule/"),
    ("dpwt_leaderboard", "Golf", "https://www.europeantour.com/dpworld-tour/leaderboard"),
    ("lpga_leaderboard", "Golf", "https://www.lpga.com/tournaments/bmw-lpga-championship/leaderboard"),
    ("owgr_rankings", "Golf", "https://www.owgr.com/current-world-ranking"),

    # --- Motor Racing ---
    ("f1_schedule_2026", "Motor Racing", "https://www.formula1.com/en/racing/2026"),
    ("f1_us_gp_2026", "Motor Racing", "https://www.formula1.com/en/racing/2026/united-states"),
    ("f1_mexico_gp_2026", "Motor Racing", "https://www.formula1.com/en/racing/2026/mexico"),
    ("f1_brazil_gp_2026", "Motor Racing", "https://www.formula1.com/en/racing/2026/brazil"),
    ("f1_drivers_2026", "Motor Racing", "https://www.formula1.com/en/results/2026/drivers"),
    ("f1_teams_2026", "Motor Racing", "https://www.formula1.com/en/results/2026/team"),
    ("motogp_calendar_2026", "Motor Racing", "https://www.motogp.com/en/calendar"),
    ("motogp_standings_2026", "Motor Racing",
     "https://www.motogp.com/en/world-standing/2026/motogp/championship-standings"),
    ("motogp_australia_2026", "Motor Racing", "https://www.motogp.com/en/events/australia/2026"),

    # --- Gaelic Sports ---
    ("gaa_fixtures", "Gaelic Sports", "https://www.gaa.ie/fixtures-results"),
    ("gaa_munster_calendar", "Gaelic Sports", "https://munster.gaa.ie/fixtures/events-calendar/"),
    ("gaa_ulster_fixtures", "Gaelic Sports", "https://ulster.gaa.ie/fixtures-results/"),
    ("gaa_cork_fixtures", "Gaelic Sports", "https://gaacork.ie/fixtures/"),
    ("gaa_offaly_fixtures", "Gaelic Sports", "https://offaly.gaa.ie/fixtures-results/"),
    ("gaa_dublin_fixtures", "Gaelic Sports", "https://www.dublingaa.ie/fixtures"),

    # --- Greyhounds ---
    ("gri_upcoming_cards", "Greyhounds", "https://www.grireland.ie/racing/upcoming-race-cards/"),
    ("gbgb_open_races", "Greyhounds", "https://www.gbgb.org.uk/racing/open-races/"),
    ("gbgb_results", "Greyhounds", "https://www.gbgb.org.uk/racing/results/"),

    # --- second-pass alternates added after the first capture returned 403/404 on primary URLs ---
    ("nba_schedule_league_v2", "Basketball", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"),
    ("nba_data_season_schedule", "Basketball",
     "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2026/league/season_schedule.json"),
    ("nba_stats_team_dashboard", "Basketball",
     "https://stats.nba.com/stats/leaguedashteamstats?LeagueID=00&PerMode=PerGame&Season=2026-27"
     "&SeasonType=Regular+Season&MeasureType=Base"),
    ("urc_fixtures_alt1", "Rugby Union", "https://www.unitedrugby.com/fixtures"),
    ("urc_fixtures_alt2", "Rugby Union", "https://www.unitedrugby.com/match-centre"),
    ("icc_matches", "Cricket", "https://www.icc-cricket.com/matches"),
    ("icc_wt20_schedule", "Cricket",
     "https://www.icc-cricket.com/tournaments/womens-t20-world-cup-2026/schedule"),
    ("legavolley_risultati", "Volleyball", "https://www.legavolley.it/risultati/?idCampionato=999"),
    ("legavolley_agenda", "Volleyball", "https://www.legavolley.it/agenda/?idCampionato=999"),
    ("nrl_draw_data_full", "Rugby League", "https://www.nrl.com/draw/data?competition=175&season=2026"),
    ("snooker_api_events", "Snooker", "https://api.snooker.org/?t=5&s=2026"),
    ("snooker_api_matches_2548", "Snooker", "https://api.snooker.org/?t=6&e=2548"),
    ("pga_schedule_next", "Golf", "https://www.pgatour.com/schedule/2027"),
    ("motogp_calendar_alt", "Motor Racing", "https://www.motogp.com/en/calendar/2026"),
    ("ehf_el_matches", "Handball", "https://ehfel.eurohandball.com/men/2026-27/matches/"),
]



def main() -> int:
    targets: list[dict] = []
    for tid, sport, url in STATIC + OLBG_HUBS:
        targets.append({"id": tid, "sport": sport, "url": url})

    # NHL per-day schedule endpoints (the API only exposes one week per call).
    d = WINDOW_START
    while d <= WINDOW_END:
        targets.append({
            "id": f"nhl_sched_{d.isoformat()}",
            "sport": "Ice Hockey",
            "url": f"https://api-web.nhle.com/v1/schedule/{d.isoformat()}",
        })
        d += timedelta(days=1)

    out = HERE / "targets.json"
    out.write_text(json.dumps(targets, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(targets)} static targets to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

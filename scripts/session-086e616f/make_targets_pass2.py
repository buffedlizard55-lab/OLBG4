#!/usr/bin/env python3
"""Board AT — pass-2 target list.

Generated after inspecting pass-1 (`capture/20261023T213436Z/manifest.json`). Pass 1 proved
which official feeds are alive; pass 2 closes the specific gaps it exposed:

  * tennis   — need the current-week WTA/ATP tournament IDs (Ningbo, Osaka, Brussels, Almaty, Lyon)
  * cricket  — icc/nzc/cricket.com.au are JS shells; try the boards' own match pages and APIs
  * darts    — every pdc.tv URL returned an identical 1,241,860-byte client shell; try dated news articles
  * snooker  — wst.tv is a shell; snooker.org event 2548 IS the BetVictor Northern Ireland Open 2026,
               so walk neighbouring event IDs to find the International Championship and the NIO draw pages
  * greyhounds — only the GBGB results API answered; probe sibling API routes and the Cat-1 schedule page
  * gaelic   — gaa.ie/fixtures has no fixture rows; county-board fixture pages do
  * rugby league — nrl.com is a bot wall and rlwc2026.com/fixtures is a shell, but
               rlwc2026.com/draws-and-pools is server-rendered; add the NRL news articles (server-rendered)
  * basketball — cdn.nba.com is 403 from datacenter IPs; add stats.nba.com with a long timeout and
               probe the NBA's own stats blob container listing for the prior-season archive
  * rugby union / volleyball / handball / hockey — add the alternative routes for the shells found in pass 1
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("targets_pass2.json")
targets: list[dict] = []


def add(tid, url, sport, role="official", headers="bot", timeout=25, delay=None):
    t = {"id": tid, "url": url, "sport": sport, "role": role, "headers": headers, "timeout": timeout}
    if delay:
        t["delay"] = delay
    targets.append(t)


# ---------------------------------------------------------------- tennis
add("wta_tournaments_shell", "https://www.wtatennis.com/tournaments", "Tennis", headers="browser")
add("wta_api_calendar_p1", "https://api.wtatennis.com/tennis/tournaments?season=2026&page=1&pageSize=100", "Tennis")
add("wta_api_calendar_p2", "https://api.wtatennis.com/tennis/tournaments?season=2026&page=2&pageSize=100", "Tennis")
add("atp_tournaments_shell", "https://www.atptour.com/en/tournaments", "Tennis", headers="browser", timeout=45)
add("atp_content_api", "https://www.atptour.com/-/content/atp-media/contentapi/tournaments", "Tennis", headers="browser", timeout=45)
add("itf_calendar", "https://www.itftennis.com/en/itf-tours/calendar/", "Tennis", headers="browser")

# ---------------------------------------------------------------- cricket
add("icc_fixtures_results", "https://www.icc-cricket.com/fixtures-results", "Cricket", headers="browser")
add("icc_rankings_api", "https://www.icc-cricket.com/api/rankings?format=t20i&type=team", "Cricket")
add("nzc_fixtures", "https://www.nzc.nz/fixtures", "Cricket", headers="browser")
add("nzc_api_matches", "https://www.nzc.nz/api/matches", "Cricket")
add("ca_api_matches", "https://www.cricket.com.au/api/matches", "Cricket")
add("ca_series", "https://www.cricket.com.au/series", "Cricket", headers="browser")
add("eci_home", "https://www.cricketireland.ie/", "Cricket", headers="browser")
add("eci_fixtures", "https://www.cricketireland.ie/fixtures", "Cricket", headers="browser")
add("zimbabwe_cricket", "https://www.zimcricket.org/", "Cricket", headers="browser")
add("cwi_home", "https://www.windiescricket.com/", "Cricket", headers="browser")
add("cwi_fixtures", "https://www.windiescricket.com/fixtures/", "Cricket", headers="browser")
add("acb_home", "https://www.cricket.af/", "Cricket", headers="browser")
add("ecb_api_matches", "https://www.ecb.co.uk/api/matches", "Cricket")
add("ecb_england_fixtures", "https://www.ecb.co.uk/england/men/fixtures", "Cricket", headers="browser")
add("bcci_api_matches", "https://www.bcci.tv/api/matches", "Cricket")
add("slc_home", "https://srilankacricket.lk/", "Cricket", headers="browser")
add("pcb_home", "https://www.pcb.com.pk/", "Cricket", headers="browser")
add("pcb_fixtures", "https://www.pcb.com.pk/fixtures-results.html", "Cricket", headers="browser")
add("bangladesh_cricket", "https://www.tigercricket.com.bd/", "Cricket", headers="browser")
add("usa_cricket", "https://www.usacricket.org/", "Cricket", headers="browser")
add("namibia_cricket", "https://www.namibiacricket.org/", "Cricket", headers="browser")

# ---------------------------------------------------------------- darts
add("pdc_news_oct20", "https://www.pdc.tv/news/2026/october/20/", "Darts", headers="browser")
add("pdc_news_oct22", "https://www.pdc.tv/news/2026/october/22/", "Darts", headers="browser")
add("pdc_news_oct23", "https://www.pdc.tv/news/2026/october/23/", "Darts", headers="browser")
add("pdc_ec_results", "https://www.pdc.tv/news/2026/october/23/2026-machineseeker-european-championship-results/", "Darts", headers="browser")
add("pdc_ec_draw_alt", "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-draw/", "Darts", headers="browser")
add("pdc_ec_first_round", "https://www.pdc.tv/news/2026/october/22/2026-machineseeker-european-championship-first-round-results/", "Darts", headers="browser")
add("pdc_sitemap_news", "https://www.pdc.tv/sitemap.xml", "Darts")
add("pdc_robots", "https://www.pdc.tv/robots.txt", "Darts")

# ---------------------------------------------------------------- snooker
add("wst_nio_draw", "https://www.wst.tv/northern-ireland-open-2026-draw/", "Snooker", headers="browser")
add("wst_news", "https://www.wst.tv/news/", "Snooker", headers="browser")
add("wst_sitemap", "https://www.wst.tv/sitemap.xml", "Snooker")
add("snooker_org_upcoming", "https://www.snooker.org/trn/upcoming.asp", "Snooker")
add("snooker_org_calendar", "https://www.snooker.org/trn/", "Snooker")
add("snooker_org_live", "https://www.snooker.org/trn/live.asp", "Snooker")
for ev in (2536, 2537, 2538, 2539, 2540, 2541, 2542, 2543, 2544, 2554, 2555, 2556, 2557, 2558, 2559, 2560):
    add(f"snooker_org_{ev}", f"https://www.snooker.org/res/index.asp?event={ev}", "Snooker")

# ---------------------------------------------------------------- greyhounds
add("gbgb_cat1_schedule", "https://www.gbgb.org.uk/racing/open-races/2025-category-one-schedule/", "Greyhounds", headers="browser")
add("gbgb_open_races", "https://www.gbgb.org.uk/racing/open-races/", "Greyhounds", headers="browser")
for route in ("fixtures", "racecards", "cards", "meetings", "races", "events", "results"):
    add(f"gbgb_api2_{route}", f"https://api.gbgb.org.uk/api/{route}", "Greyhounds")
add("gbgb_api_results_24", "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100&date=2026-10-24&race_type=race", "Greyhounds")
add("gbgb_api_results_nodate", "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100", "Greyhounds")
add("gri_racing", "https://www.igb.ie/racing", "Greyhounds", headers="browser")
add("gri_results", "https://www.igb.ie/results", "Greyhounds", headers="browser")
add("gri_racecards", "https://www.igb.ie/racecards", "Greyhounds", headers="browser")

# ---------------------------------------------------------------- gaelic sports
add("mayogaa_fixtures", "https://mayogaa.com/fixtures/", "Gaelic Sports", headers="browser")
add("claregaa_fixtures", "https://clare.gaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("leitrimgaa_fixtures", "https://www.leitrimgaa.ie/fixtures-next-10-days/", "Gaelic Sports", headers="browser")
add("ulstergaa_fixtures", "https://ulster.gaa.ie/fixtures/", "Gaelic Sports", headers="browser")
add("dublingaa_fixtures", "https://www.dublingaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("kilkennygaa_fixtures", "https://kilkennygaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("gaa_sitemap", "https://www.gaa.ie/sitemap.xml", "Gaelic Sports")
add("gaa_fixtures_results", "https://www.gaa.ie/fixtures-results", "Gaelic Sports", headers="browser")
add("gaa_api_fixtures_v2", "https://www.gaa.ie/api/fixtures-results", "Gaelic Sports")

# ---------------------------------------------------------------- rugby league
add("nrl_wc_team_lists_r2", "https://www.nrl.com/news/2026-10-20/world-cup-team-lists-mens-round-2/", "Rugby League", headers="browser")
add("nrl_news_wc", "https://www.nrl.com/news/world-cup/", "Rugby League", headers="browser")
add("nrl_draw_rlwc", "https://www.nrl.com/draw/competition=rlwc&year=2026", "Rugby League", headers="browser")
add("rlwc_news", "https://www.rlwc2026.com/news", "Rugby League", headers="browser")
add("rlwc_matches", "https://www.rlwc2026.com/matches", "Rugby League", headers="browser")
add("rlwc_sitemap", "https://www.rlwc2026.com/sitemap.xml", "Rugby League")
add("rfl_fixtures", "https://www.rugby-league.com/fixtures", "Rugby League", headers="browser")
add("rfl_competitions", "https://www.rugby-league.com/competitions", "Rugby League", headers="browser")
add("superleague_results", "https://www.superleague.co.uk/results", "Rugby League", headers="browser")

# ---------------------------------------------------------------- basketball
add("nba_statsapi_gamelog", "https://stats.nba.com/stats/leaguegamelog?Season=2025-26&SeasonType=Regular%20Season&Sorter=DATE&Direction=DESC", "Basketball", headers="browser", timeout=120)
add("nba_statsapi_teamdashboard", "https://stats.nba.com/stats/leaguedashteamstats?Season=2025-26&SeasonType=Regular%20Season&PerMode=PerGame", "Basketball", headers="browser", timeout=120)
add("nba_blob_container", "https://nbastats.blob.core.windows.net/csv/", "Basketball", timeout=60)
add("nba_blob_season_index", "https://nbastats.blob.core.windows.net/csv/season_2025-26/index.html", "Basketball", timeout=60)
add("nba_cdn_schedule_v2_1", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", "Basketball", headers="browser")
add("nba_cdn_scoreboard_v2", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "Basketball", headers="browser")
add("euroleague_standings_a", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings", "Basketball")
add("euroleague_standings_b", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games/standings", "Basketball")
add("euroleague_results_a", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/results", "Basketball")
add("euroleague_teams_a", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/teams/", "Basketball")
add("euroleague_competitions", "https://api-live.euroleague.net/v2/competitions", "Basketball")
add("euroleague_seasons", "https://api-live.euroleague.net/v2/competitions/E/seasons", "Basketball")
add("euroleague_games_p1", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games?page=1&size=50", "Basketball")

# ---------------------------------------------------------------- rugby union
add("prem_api_fixtures", "https://www.premiershiprugby.com/api/fixtures", "Rugby Union")
add("prem_match_pages", "https://www.premiershiprugby.com/matches", "Rugby Union", headers="browser")
add("urc_matches", "https://www.unitedrugby.com/matches/", "Rugby Union", headers="browser")
add("urc_api_table", "https://stats.unitedrugby.com/api/table/2026-27", "Rugby Union")
add("urc_api_matchcentre", "https://stats.unitedrugby.com/api/match-centre/2026-27/6", "Rugby Union")
add("urc_standings", "https://www.unitedrugby.com/standings/", "Rugby Union", headers="browser")
add("lnr_top14_classement", "https://top14.lnr.fr/classement", "Rugby Union", headers="browser")
add("lnr_top14_calendrier", "https://top14.lnr.fr/calendrier", "Rugby Union", headers="browser")
add("rugby_ie_home", "https://www.rugby.ie/", "Rugby Union", headers="browser")
add("rugby_ie_fixtures", "https://www.rugby.ie/fixtures-results/", "Rugby Union", headers="browser")
add("worldrugby_rankings_api", "https://api.wr-rims-prod.pulselive.com/rugby/v3/ranking/mru", "Rugby Union")

# ---------------------------------------------------------------- volleyball
add("plusliga_terminarz_alt", "https://plusliga.pl/matches.html", "Volleyball", headers="browser")
add("plusliga_results", "https://plusliga.pl/results.html", "Volleyball", headers="browser")
add("vbl_spielplan", "https://www.volleyball-bundesliga.de/saison/spielplan", "Volleyball", headers="browser")
add("legavolley_risultati", "https://www.legavolley.it/risultati/", "Volleyball")
add("legavolley_seriea2", "https://www.legavolley.it/classifica/?IdCampionato=992", "Volleyball")
add("cev_competitions", "https://www.cev.eu/competitions/", "Volleyball", headers="browser")

# ---------------------------------------------------------------- handball
add("handbollsligan_program", "https://handbollsligan.se/spelschema/", "Handball", headers="browser")
add("handbollsligan_resultat", "https://handbollsligan.se/resultat/", "Handball", headers="browser")
add("tophaandbold_kampe", "https://tophaandbold.dk/kampe/herreligaen", "Handball", headers="browser")
add("tophaandbold_kampprogram", "https://tophaandbold.dk/kampprogram", "Handball", headers="browser")
add("hbl_ergebnisse", "https://www.dkb-handball-bundesliga.de/ergebnisse", "Handball", headers="browser")
add("asobal_partidos", "https://asobal.es/partidos/", "Handball", headers="browser")
add("asobal_clasificacion", "https://asobal.es/clasificacion/", "Handball", headers="browser")
add("lnh_division1", "https://www.lnh.fr/division-1", "Handball", headers="browser")
add("ehf_api_matches", "https://ehfcl.eurohandball.com/api/matches", "Handball")
add("ehf_home_matches", "https://www.eurohandball.com/en/matches/", "Handball", headers="browser")

# ---------------------------------------------------------------- ice hockey / baseball extras
add("nhl_club_sched_tor", "https://api-web.nhle.com/v1/club-schedule/TOR/week/now", "Ice Hockey")
add("nhl_team_landing", "https://api-web.nhle.com/v1/team-landing/20262027", "Ice Hockey")
add("mlb_news_schedule", "https://www.mlb.com/news/2026-mlb-playoff-and-world-series-schedule", "Baseball", headers="browser")
add("mlb_news_ws_faq", "https://www.mlb.com/news/2026-mlb-world-series-faq-schedule-times-teams-and-more", "Baseball", headers="browser")
add("mlb_brewers_news", "https://www.mlb.com/brewers/news", "Baseball", headers="browser")
add("mlb_rays_news", "https://www.mlb.com/rays/news", "Baseball", headers="browser")

# ---------------------------------------------------------------- motor racing
add("motogp_results_2026", "https://www.motogp.com/en/results/2026/moto-gp", "Motor Racing", headers="browser")
add("motogp_calendar_2026", "https://www.motogp.com/en/calendar/2026", "Motor Racing", headers="browser")
add("motogp_malaysia", "https://www.motogp.com/en/calendar/2026/malaysia", "Motor Racing", headers="browser")
add("indycar_results", "https://www.indycar.com/Results", "Motor Racing", headers="browser")

OUT.write_text(json.dumps(targets, indent=1) + "\n")
print(f"{len(targets)} pass-2 targets -> {OUT}")

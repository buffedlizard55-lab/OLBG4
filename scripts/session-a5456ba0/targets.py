#!/usr/bin/env python3
"""Generate the Board AN capture target list.

Every target is an official governing-body / league / tour / OLBG URL.  The list is
regenerated for the run date so the capture always covers *today* plus the next two
weeks, then committed as `targets.json` for the Actions capture runner.

    python3 scripts/session-a5456ba0/targets.py > scripts/session-a5456ba0/targets.json
"""
from __future__ import annotations

import json
from datetime import date, timedelta

TODAY = date.today()
DATES = [(TODAY + timedelta(days=i)).isoformat() for i in range(15)]  # today .. +14

T: list[dict] = []


def add(sport: str, tid: str, url: str, kind: str = "html", delay: float = 0.5) -> None:
    T.append({"sport": sport, "id": tid, "url": url, "kind": kind, "delay": delay})


# ---------------------------------------------------------------- OLBG listings
add("OLBG", "olbg_robots", "https://www.olbg.com/robots.txt", "text")
add("OLBG", "olbg_sitemap", "https://www.olbg.com/sitemap.xml", "xml")
add("OLBG", "olbg_all", "https://www.olbg.com/betting-tips")

HUB = {
    "Golf": ("Golf", 5, "golf"),
    "Volleyball": ("Volleyball", 21, "volleyball"),
    "Rugby Union": ("Rugby_Union", 9, "rugbyunion"),
    "Cricket": ("Cricket", 7, "cricket"),
    "Snooker": ("Snooker", 8, "snooker"),
    "Darts": ("Darts", 15, "darts"),
    "Baseball": ("Baseball", 12, "baseball"),
    "Gaelic Sports": ("Gaelic_Football", 25, "gaelicfootball"),
    "Gaelic Sports": ("Hurling", 26, "hurling"),
    "Greyhounds": ("Greyhounds", 28, "greyhounds"),
    "Tennis": ("Tennis", 3, "tennis"),
    "Motor Racing": ("Motor_Racing", 14, "motorracing"),
    "Handball": ("Handball", 20, "handball"),
    "Ice Hockey": ("Ice_Hockey", 13, "icehockey"),
    "Basketball": ("Basketball", 4, "basketball"),
    "Rugby League": ("Rugby_League", 10, "rugbyleague"),
}
for sport, (slug, sid, key) in HUB.items():
    add(sport, f"olbg_hub_{key}", f"https://www.olbg.com/betting-tips/{slug}/{sid}", delay=0.8)
    add(sport, f"olbg_hub_{key}_data", f"https://www.olbg.com/betting-tips/{slug}/{sid}/__data.json",
        "json", 0.6)

# ----------------------------------------------------------------------- Golf
add("Golf", "pgatour_schedule", "https://www.pgatour.com/schedule")
add("Golf", "pgatour_leaderboard", "https://www.pgatour.com/leaderboard")
add("Golf", "pgatour_bermuda", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528")
add("Golf", "pgatour_bermuda_field",
    "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528/field")
add("Golf", "owgr", "https://www.owgr.com/current-world-ranking")
add("Golf", "owgr_100", "https://www.owgr.com/current-world-ranking?page=1&pageSize=100")
add("Golf", "dpwt_schedule", "https://www.europeantour.com/dpworld-tour/schedule")
add("Golf", "dpwt_rankings", "https://www.europeantour.com/dpworld-tour/rankings")
add("Golf", "lpga_schedule", "https://www.lpga.com/tournaments")
add("Golf", "lpga_race", "https://www.lpga.com/statistics/race-to-the-cme-globe")

# ------------------------------------------------------------------ Volleyball
for cid in (991, 995, 997, 998, 999, 1000, 1001, 1002, 1003, 1004):
    add("Volleyball", f"legavolley_cal_{cid}",
        f"https://www.legavolley.it/calendario/?Anno=2026&IdCampionato={cid}", delay=0.6)
add("Volleyball", "legavolley_classifica", "https://www.legavolley.it/classifica/")
add("Volleyball", "plusliga_fixtures", "https://www.plusliga.pl/mecze/tour/47.html", delay=0.6)
add("Volleyball", "plusliga_table", "https://www.plusliga.pl/table/tour/47.html", delay=0.6)
add("Volleyball", "vbl_home", "https://www.volleyball-bundesliga.de/")
add("Volleyball", "cvf_extraliga",
    "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147")
add("Volleyball", "volleyballworld_vnl",
    "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/")
add("Volleyball", "cev_club", "https://www.cev.eu/club/competitions/")

# ------------------------------------------------------------------ Rugby Union
add("Rugby Union", "prem_api_fixtures", "https://www.premiershiprugby.com/api/fixtures", "json")
add("Rugby Union", "prem_fixtures", "https://www.premiershiprugby.com/fixtures-results")
add("Rugby Union", "prem_standings", "https://www.premiershiprugby.com/standings")
add("Rugby Union", "prem_standings_data", "https://www.premiershiprugby.com/standings/__data.json", "json")
add("Rugby Union", "top14_cal", "https://top14.lnr.fr/calendrier-et-resultats")
add("Rugby Union", "top14_classement", "https://top14.lnr.fr/classement")
add("Rugby Union", "urc_table", "https://stats.unitedrugby.com/match-centre/table/2026-27", "json")
for rnd in range(5, 12):
    add("Rugby Union", f"urc_r{rnd}", f"https://stats.unitedrugby.com/match-centre/2026-27/{rnd}", "json")
add("Rugby Union", "urc_fixtures_in_full",
    "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/")
add("Rugby Union", "world_rugby_rankings", "https://www.world.rugby/tournaments/rankings/mru")
add("Rugby Union", "world_rugby_matches", "https://www.world.rugby/match-centre")
add("Rugby Union", "epcr_fixtures", "https://www.epcrugby.com/fixtures")
add("Rugby Union", "super_rugby", "https://www.superrugby.co.nz/fixtures")

# ---------------------------------------------------------------------- Cricket
add("Cricket", "cricket_au_fixtures", "https://www.cricket.com.au/fixtures")
add("Cricket", "cricket_au_matches", "https://www.cricket.com.au/matches")
add("Cricket", "ecb_fixtures", "https://www.ecb.co.uk/england/men/fixtures")
add("Cricket", "nzc_matches", "https://www.nzc.nz/matches")
add("Cricket", "bcci_home", "https://www.bcci.tv/")
add("Cricket", "icc_test_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/test")
add("Cricket", "icc_odi_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi")
add("Cricket", "icc_t20i_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i")
add("Cricket", "icc_matches", "https://www.icc-cricket.com/matches")
add("Cricket", "cricket_ireland", "https://www.cricketireland.ie/fixtures")

# ---------------------------------------------------------------------- Snooker
add("Snooker", "wst_matches_api",
    "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=400"
    f"&filter[startDateTime][gte]={DATES[0]}&filter[startDateTime][lte]={DATES[-1]}", "json", 0.8)
add("Snooker", "wst_participants",
    "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=400", "json", 0.8)
add("Snooker", "wst_rankings_api",
    "https://rankings.snooker.web.gc.wstservices.co.uk/v2/?page.size=200", "json", 0.8)
add("Snooker", "wst_rankings", "https://www.wst.tv/rankings/")
add("Snooker", "wst_tournaments", "https://www.wst.tv/tournaments/")
add("Snooker", "wst_nio", "https://www.wst.tv/tournaments/northern-ireland-open-2026/")
add("Snooker", "snooker_org_cal", "https://www.snooker.org/res/index.asp?template=2")

# ------------------------------------------------------------------------ Darts
add("Darts", "pdc_home", "https://www.pdc.tv/")
add("Darts", "pdc_match_centre", "https://www.pdc.tv/match-centre")
add("Darts", "pdc_tournaments", "https://www.pdc.tv/tournaments")
add("Darts", "pdc_european_tour", "https://www.pdc.tv/european-tour")
add("Darts", "pdc_ec", "https://www.pdc.tv/tournaments/machineseeker-european-championship")
add("Darts", "pdc_grandslam", "https://www.pdc.tv/tournaments/boyle-sports-grand-slam-of-darts")
add("Darts", "pdc_pcf", "https://www.pdc.tv/tournaments/machineseeker-players-championship-finals")
add("Darts", "pdc_oom", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit")
add("Darts", "pdc_oom_data", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit/__data.json", "json")
add("Darts", "pdc_match_centre_data", "https://www.pdc.tv/match-centre/__data.json", "json")
add("Darts", "pdc_tournaments_data", "https://www.pdc.tv/tournaments/__data.json", "json")
add("Darts", "pdc_ec_data",
    "https://www.pdc.tv/tournaments/machineseeker-european-championship/__data.json", "json")
add("Darts", "pdc_gs_data",
    "https://www.pdc.tv/tournaments/boyle-sports-grand-slam-of-darts/__data.json", "json")
add("Darts", "darts_matches_api",
    "https://matches.darts.web.gc.wstservices.co.uk/v2/?page.size=400", "json")
add("Darts", "pdc_et_data", "https://www.pdc.tv/european-tour/__data.json", "json")

# --------------------------------------------------------------------- Baseball
add("Baseball", "mlb_schedule",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
    f"&startDate={DATES[0]}&endDate={DATES[-1]}"
    "&hydrate=probablePitcher,linescore,team,venue", "json", 0.8)
add("Baseball", "mlb_postseason",
    "https://statsapi.mlb.com/api/v1/schedule/postseason?sportId=1&season=2026"
    "&hydrate=probablePitcher,linescore,team,venue", "json", 0.8)
add("Baseball", "mlb_standings",
    "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"
    "&standingsTypes=regularSeason", "json", 0.8)
add("Baseball", "mlb_hitting",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1",
    "json", 0.8)
add("Baseball", "mlb_pitching",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1",
    "json", 0.8)
add("Baseball", "mlb_postseason_page", "https://www.mlb.com/postseason")

# --------------------------------------------------------------- Gaelic Sports
add("Gaelic Sports", "gaa_fixtures", "https://www.gaa.ie/fixtures")
add("Gaelic Sports", "gaa_results", "https://www.gaa.ie/fixtures-results")
add("Gaelic Sports", "gaa_club", "https://www.gaa.ie/club")
add("Gaelic Sports", "gaacork_fixtures", "https://gaacork.ie/fixtures")
add("Gaelic Sports", "ladies_gaelic", "https://ladiesgaelic.ie/")
add("Gaelic Sports", "gaa_county_fixtures", "https://www.gaa.ie/my-gaa/getting-involved/fixtures")

# ------------------------------------------------------------------- Greyhounds
add("Greyhounds", "gbgb_results_index", "https://www.gbgb.org.uk/results/")
add("Greyhounds", "gbgb_racecards", "https://www.gbgb.org.uk/racecards/")
add("Greyhounds", "gbgb_fixtures", "https://www.gbgb.org.uk/fixtures/")
for d in DATES[:4]:
    add("Greyhounds", f"gbgb_api_races_{d}", f"https://api.gbgb.org.uk/api/races?date={d}", "json")
    add("Greyhounds", f"gbgb_racecard_{d}", f"https://www.gbgb.org.uk/racecard/{d}")
add("Greyhounds", "igb_results", "https://www.igb.ie/results/")
add("Greyhounds", "igb_racecards", "https://www.igb.ie/racecards/")

# ----------------------------------------------------------------------- Tennis
add("Tennis", "wta_tournaments",
    "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100", "json", 0.8)
add("Tennis", "wta_matches",
    "https://api.wtatennis.com/tennis/matches/?page=0&pageSize=100", "json", 0.8)
add("Tennis", "wta_rankings",
    "https://api.wtatennis.com/tennis/players/rankings?page=0&pageSize=100", "json", 0.8)
add("Tennis", "atp_scores", "https://www.atptour.com/en/scores/current")
add("Tennis", "atp_rankings", "https://www.atptour.com/en/rankings/singles")
add("Tennis", "atp_calendar", "https://www.atptour.com/en/tournaments")
add("Tennis", "itf_calendar", "https://www.itftennis.com/en/tournament-calendar/")

# ---------------------------------------------------------------- Motor Racing
add("Motor Racing", "f1_racing_2026", "https://www.formula1.com/en/racing/2026.html")
add("Motor Racing", "f1_brazil", "https://www.formula1.com/en/racing/2026/brazil")
add("Motor Racing", "f1_mexico", "https://www.formula1.com/en/racing/2026/mexico")
add("Motor Racing", "f1_drivers", "https://www.formula1.com/en/results/2026/drivers")
add("Motor Racing", "f1_teams", "https://www.formula1.com/en/results/2026/team")
add("Motor Racing", "motogp_calendar", "https://www.motogp.com/en/calendar/2026")
add("Motor Racing", "motogp_standings", "https://www.motogp.com/en/standings/2026")
add("Motor Racing", "indycar_schedule", "https://www.indycar.com/Schedule")
add("Motor Racing", "nascar_schedule", "https://www.nascar.com/schedule/")
add("Motor Racing", "fia_f2", "https://www.fiaformula2.com/")
add("Motor Racing", "fia_f3", "https://www.fiaformula3.com/")

# --------------------------------------------------------------------- Handball
add("Handball", "ehfcl_m_matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/")
add("Handball", "ehfcl_m_standings", "https://ehfcl.eurohandball.com/men/2026-27/standings/")
add("Handball", "ehfcl_w_matches", "https://ehfcl.eurohandball.com/women/2026-27/matches/")
add("Handball", "ehfel_m_matches", "https://ehfel.eurohandball.com/men/2026-27/matches/")
add("Handball", "hbl_spielplan", "https://www.dkb-handball-bundesliga.de/spielplan")
add("Handball", "hbl_api_table", "https://www.dkb-handball-bundesliga.de/api/table", "json")
add("Handball", "dk_program", "https://tophaandbold.dk/kampprogram")
add("Handball", "dk_herreligaen", "https://tophaandbold.dk/stillinger/herreligaen")
add("Handball", "handbollsligan", "https://handbollsligan.se/")

# ------------------------------------------------------------------- Ice Hockey
add("Ice Hockey", "nhl_standings", "https://api-web.nhle.com/v1/standings/now", "json", 0.8)
for d in DATES:
    add("Ice Hockey", f"nhl_sched_{d}", f"https://api-web.nhle.com/v1/schedule/{d}", "json", 0.4)
add("Ice Hockey", "nhl_skaters",
    "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals,points&limit=25", "json")
add("Ice Hockey", "nhl_goalies",
    "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=savePctg,goalsAgainstAverage&limit=25",
    "json")
add("Ice Hockey", "liiga_games", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", "json")
add("Ice Hockey", "liiga_standings", "https://liiga.fi/api/v2/standings/?season=2027", "json")
add("Ice Hockey", "shl_overview", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961")
add("Ice Hockey", "shl_standings", "https://stats.swehockey.se/ScheduleAndResults/Standings/20961")

# ------------------------------------------------------------------- Basketball
add("Basketball", "el_games", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", "json")
add("Basketball", "el_standings", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings", "json")
add("Basketball", "eurocup_games", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games", "json")
add("Basketball", "acb_calendario", "https://www.acb.com/calendario/")
add("Basketball", "acb_clasificacion", "https://www.acb.com/clasificacion/")
add("Basketball", "lega_basket", "https://www.legabasket.it/")
add("Basketball", "nba_schedule_cdn", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", "json")
add("Basketball", "nba_games", "https://www.nba.com/games")
add("Basketball", "nba_standings",
    "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular%20Season",
    "json")

# ---------------------------------------------------------------- Rugby League
add("Rugby League", "rlwc_api_fixtures", "https://www.rlwc2026.com/api/fixtures", "json")
add("Rugby League", "rlwc_api_matches", "https://www.rlwc2026.com/api/matches", "json")
add("Rugby League", "rlwc_fixtures", "https://www.rlwc2026.com/fixtures")
add("Rugby League", "rlwc_results", "https://www.rlwc2026.com/results")
add("Rugby League", "rlwc_draws", "https://www.rlwc2026.com/draws-and-pools")
add("Rugby League", "nrl_draw", "https://www.nrl.com/draw/")
add("Rugby League", "superleague_fixtures", "https://www.superleague.co.uk/fixtures")
add("Rugby League", "superleague_table", "https://www.superleague.co.uk/table")
add("Rugby League", "rfl_fixtures", "https://www.rugby-league.com/fixtures")

# de-duplicate on id, keep first
seen, out = set(), []
for t in T:
    if t["id"] in seen:
        continue
    seen.add(t["id"])
    out.append(t)

print(json.dumps(out, indent=1))

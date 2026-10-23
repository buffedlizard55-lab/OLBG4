#!/usr/bin/env python3
"""Board AT — generate the capture target list.

Two roles, kept strictly separate in every downstream artefact:

  role="olbg"     OLBG.com public hub pages. Used only to reverse-engineer OLBG's sport and
                  market taxonomy and to enumerate the events OLBG lists. Never a source for a
                  published fixture time, team, price or statistic.
  role="official" League / tour / federation / governing-body feeds. The only sources a
                  published value may come from.

Endpoints that peer boards proved alive on 2026-10-23 are kept; endpoints they proved dead are
retried once with alternates (and the outcome is recorded as evidence either way).
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).with_name("targets.json")

SPORTS_OLBG = [
    ("Golf", "Golf/5"),
    ("Tennis", "Tennis/3"),
    ("Cricket", "Cricket/7"),
    ("Rugby Union", "Rugby_Union/9"),
    ("Rugby League", "Rugby_League/10"),
    ("Ice Hockey", "Ice_Hockey/13"),
    ("Basketball", "Basketball/4"),
    ("Darts", "Darts/15"),
    ("Handball", "Handball/20"),
    ("Volleyball", "Volleyball/21"),
    ("Gaelic Sports", "Gaelic_Football/25"),
    ("Greyhounds", "Greyhounds/28"),
    ("Baseball", "Baseball/12"),
    ("Motor Racing", "Motor_Racing/14"),
    ("Snooker", "Snooker/8"),
]

targets: list[dict] = []


def add(tid, url, sport, role="official", headers="bot", delay=None, timeout=25, note=None):
    t = {"id": tid, "url": url, "sport": sport, "role": role, "headers": headers, "timeout": timeout}
    if delay:
        t["delay"] = delay
    if note:
        t["note"] = note
    if t not in targets:
        targets.append(t)


# ---------------------------------------------------------------- OLBG taxonomy hubs
add("olbg_robots", "https://www.olbg.com/robots.txt", "-", role="olbg", delay=0.9)
add("olbg_sitemap_tips", "https://www.olbg.com/sitemap-betting-tips.xml", "-", role="olbg", delay=0.9)
add("olbg_all_tips", "https://www.olbg.com/betting-tips", "-", role="olbg", delay=0.9)
for sport, path in SPORTS_OLBG:
    slug = path.split("/")[0]
    add(f"olbg_{slug.lower()}", f"https://www.olbg.com/betting-tips/{path}", sport, role="olbg", delay=0.95)
# competition sub-hubs OLBG exposes for the in-scope sports
for sport, path in [
    ("Basketball", "Basketball/NBA/4"),
    ("Basketball", "Basketball/European/Euroleague/4"),
    ("Ice Hockey", "Ice_Hockey/NHL/13"),
    ("Ice Hockey", "Ice_Hockey/Other/13"),
    ("Basketball", "Basketball/Other/4"),
]:
    key = path.replace("/", "_").lower()
    add(f"olbg_sub_{key}", f"https://www.olbg.com/betting-tips/{path}", sport, role="olbg", delay=0.95)

# ---------------------------------------------------------------- ice hockey
d0 = date(2026, 10, 23)
for i in range(17):  # 23 Oct – 8 Nov 2026
    d = d0 + timedelta(days=i)
    add(f"nhl_sched_{d.isoformat()}", f"https://api-web.nhle.com/v1/schedule/{d.isoformat()}", "Ice Hockey")
for extra in ("now", "2026-10-23"):
    add(f"nhl_standings_{extra}", f"https://api-web.nhle.com/v1/standings/{extra}", "Ice Hockey")
add("nhl_skater_leaders", "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals,points&limit=20", "Ice Hockey")
add("nhl_goalie_leaders", "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=savePctg,goalsAgainstAverage&limit=20", "Ice Hockey")
add("liiga_games", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", "Ice Hockey")
add("liiga_standings", "https://liiga.fi/api/v2/standings/?season=2027", "Ice Hockey")
add("shl_overview", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961", "Ice Hockey")
add("ahl_schedule", "https://lscluster.hdmtech.net/view/calendars/daily_schedule?league_id=129&season_id=2026&date=2026-10-24", "Ice Hockey",
    note="AHL official calendar service (alternate host for the AHL schedule widget)")

# ---------------------------------------------------------------- basketball (NBA + Europe)
add("nba_cdn_schedule_v2", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", "Basketball", headers="browser")
add("nba_cdn_scoreboard_today", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "Basketball", headers="browser")
add("nba_cdn_standings", "https://cdn.nba.com/static/json/liveData/standings/standings_00.json", "Basketball", headers="browser")
for d in (date(2026, 10, 23), date(2026, 10, 24), date(2026, 10, 25)):
    add(f"nba_cdn_scoreboard_{d.isoformat()}",
        f"https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json?date={d.isoformat()}",
        "Basketball", headers="browser")
# Official NBA Stats season archives, published by the NBA on its own Azure blob host.
for season in ("2025-26", "2024-25"):
    for f in ("Miscellaneous_stats.csv", "Per_game.csv", "Advanced_stats.csv", "Opponent_per_game.csv"):
        add(f"nba_stats_{season}_{f[:-4].lower()}",
            f"https://nbastats.blob.core.windows.net/csv/season_{season}/{f}", "Basketball",
            timeout=90, note="official NBA Stats season archive (NBA-owned blob)")
add("euroleague_games_E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", "Basketball")
add("eurocup_games_U2026", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games", "Basketball")
add("euroleague_standings_E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings/", "Basketball")
add("euroleague_teams_E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/teams", "Basketball")
add("euroleague_home", "https://www.euroleaguebasketball.net/euroleague/", "Basketball", headers="browser")

# ---------------------------------------------------------------- baseball
add("mlb_ws_schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-11-08", "Baseball")
add("mlb_standings_2026", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason", "Baseball")
add("mlb_hitting_2026", "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1", "Baseball")
add("mlb_pitching_2026", "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1", "Baseball")
add("mlb_probable_pitchers", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-10-31&hydrate=probablePitcher,team,linescore,flags", "Baseball")
add("mlb_home", "https://www.mlb.com/postseason", "Baseball", headers="browser")

# ---------------------------------------------------------------- tennis
for tid in ("2092", "405", "1023", "1056", "328", "337", "496", "7485", "9410"):
    add(f"wta_{tid}_matches", f"https://api.wtatennis.com/tennis/tournaments/{tid}/2026/matches", "Tennis")
    add(f"wta_{tid}_tournament", f"https://api.wtatennis.com/tennis/tournaments/{tid}/2026", "Tennis")
add("wta_rankings_singles", "https://api.wtatennis.com/tennis/rankings/singles?rankDate=2026-10-20&page=0&pageSize=100", "Tennis")
add("wta_calendar", "https://api.wtatennis.com/tennis/tournaments?season=2026&page=0&pageSize=100", "Tennis")
add("atp_rankings_pdf", "https://www.protennislive.com/posting/2026/9410/rank.pdf", "Tennis", timeout=60)
for tid in ("328", "337", "496", "7485", "9410"):
    add(f"atp_{tid}_op", f"https://www.protennislive.com/posting/2026/{tid}/op.pdf", "Tennis", timeout=60)
    add(f"atp_{tid}_mds", f"https://www.protennislive.com/posting/2026/{tid}/mds.pdf", "Tennis", timeout=60)
add("atp_home", "https://www.atptour.com/en/", "Tennis", headers="browser")
add("wta_home", "https://www.wtatennis.com/", "Tennis", headers="browser")
add("itf_home", "https://www.itftennis.com/en/", "Tennis", headers="browser")

# ---------------------------------------------------------------- volleyball
add("legavolley_classifica", "https://www.legavolley.it/classifica/", "Volleyball")
add("legavolley_cal_991", "https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=991", "Volleyball")
add("legavolley_cal_2026", "https://www.legavolley.it/calendario/?Anno=2026", "Volleyball")
add("legavolley_home", "https://www.legavolley.it/", "Volleyball", headers="browser")
add("plusliga_home", "https://plusliga.pl/", "Volleyball", headers="browser")
add("plusliga_table_47", "https://plusliga.pl/table/tour/47.html", "Volleyball", headers="browser")
add("plusliga_table_48", "https://plusliga.pl/table/tour/48.html", "Volleyball", headers="browser")
add("plusliga_terminarz", "https://plusliga.pl/terminarz.html", "Volleyball", headers="browser")
add("vbl_home", "https://www.volleyball-bundesliga.de/", "Volleyball", headers="browser")
add("cvf_extraliga", "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147", "Volleyball", headers="browser")
add("cev_home", "https://www.cev.eu/", "Volleyball", headers="browser")
add("fivb_home", "https://www.fivb.com/", "Volleyball", headers="browser")

# ---------------------------------------------------------------- rugby union
add("urc_fixtures_in_full", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", "Rugby Union", headers="browser")
add("urc_match_centre_table", "https://stats.unitedrugby.com/match-centre/table/2026-27", "Rugby Union")
for rnd in (5, 6, 7):
    add(f"urc_round{rnd}", f"https://stats.unitedrugby.com/match-centre/2026-27/{rnd}", "Rugby Union")
add("urc_home", "https://www.unitedrugby.com/", "Rugby Union", headers="browser")
add("prem_fixtures", "https://www.premiershiprugby.com/fixtures-results", "Rugby Union", headers="browser")
add("prem_standings", "https://www.premiershiprugby.com/standings", "Rugby Union", headers="browser")
add("top14_cal", "https://top14.lnr.fr/calendrier-et-resultats", "Rugby Union", headers="browser")
add("prod2_cal", "https://prod2.lnr.fr/calendrier-et-resultats", "Rugby Union", headers="browser")
add("epcr_home", "https://www.epcrugby.com/", "Rugby Union", headers="browser")
add("worldrugby_home", "https://www.world.rugby/", "Rugby Union", headers="browser")
add("worldrugby_rankings", "https://www.world.rugby/en/rankings/mru", "Rugby Union", headers="browser")
add("rugby_com_au_wallabies", "https://www.rugby.com.au/competitions/wallabies", "Rugby Union", headers="browser")

# ---------------------------------------------------------------- rugby league
add("rlwc_draws", "https://www.rlwc2026.com/draws-and-pools", "Rugby League", headers="browser")
add("rlwc_fixtures", "https://www.rlwc2026.com/fixtures", "Rugby League", headers="browser")
add("rlwc_results", "https://www.rlwc2026.com/results", "Rugby League", headers="browser")
add("rlwc_home", "https://www.rlwc2026.com/", "Rugby League", headers="browser")
add("rlwc_ladder", "https://www.rlwc2026.com/ladders", "Rugby League", headers="browser")
add("nrl_draw", "https://www.nrl.com/draw/", "Rugby League", headers="browser")
add("nrl_home", "https://www.nrl.com/", "Rugby League", headers="browser")
add("intlrl_home", "https://www.internationalrugbyleague.com/", "Rugby League", headers="browser")
add("rfl_home", "https://www.rugby-league.com/", "Rugby League", headers="browser")
add("superleague_home", "https://www.superleague.co.uk/", "Rugby League", headers="browser")

# ---------------------------------------------------------------- cricket
add("icc_t20i_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", "Cricket", headers="browser")
add("icc_odi_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", "Cricket", headers="browser")
add("icc_wodi_rankings", "https://www.icc-cricket.com/rankings/womens/team-rankings/odi", "Cricket", headers="browser")
add("icc_home", "https://www.icc-cricket.com/", "Cricket", headers="browser")
add("icc_live_scores", "https://www.icc-cricket.com/live-cricket/live-scores", "Cricket", headers="browser")
add("cricket_au_fixtures", "https://www.cricket.com.au/fixtures", "Cricket", headers="browser")
add("cricket_au_home", "https://www.cricket.com.au/", "Cricket", headers="browser")
add("ecb_home", "https://www.ecb.co.uk/", "Cricket", headers="browser")
add("ecb_fixtures", "https://www.ecb.co.uk/fixtures", "Cricket", headers="browser")
add("ecb_england_m", "https://www.ecb.co.uk/england/men", "Cricket", headers="browser")
add("bcci_home", "https://www.bcci.tv/", "Cricket", headers="browser")
add("bcci_fixtures", "https://www.bcci.tv/international/fixtures", "Cricket", headers="browser")
add("nzc_matches", "https://www.nzc.nz/matches", "Cricket", headers="browser")
add("csa_home", "https://www.cricket.co.za/", "Cricket", headers="browser")
add("sl_home", "https://www.slcricket.com/", "Cricket", headers="browser")

# ---------------------------------------------------------------- darts
add("pdc_home", "https://www.pdc.tv/", "Darts", headers="browser")
add("pdc_ec_schedule", "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-", "Darts", headers="browser")
add("pdc_ec_preview", "https://www.pdc.tv/news/2026/october/21/2026-machineseeker-european-championship-preview/", "Darts", headers="browser")
add("pdc_ec_draw", "https://www.pdc.tv/news/2026/october/20/2026-machineseeker-european-championship-draw/", "Darts", headers="browser")
add("pdc_oom", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit", "Darts", headers="browser")
add("pdc_events", "https://www.pdc.tv/events", "Darts", headers="browser")
add("pdc_ec_draws", "https://www.pdc.tv/draws", "Darts", headers="browser")
add("wdf_home", "https://darts.wdf.org/", "Darts", headers="browser")

# ---------------------------------------------------------------- snooker
add("wst_home", "https://www.wst.tv/", "Snooker", headers="browser")
add("wst_nio_2026", "https://www.wst.tv/tournaments/northern-ireland-open-2026/", "Snooker", headers="browser")
add("wst_draws", "https://www.wst.tv/draws/", "Snooker", headers="browser")
add("wst_results", "https://www.wst.tv/results/", "Snooker", headers="browser")
add("wst_rankings", "https://www.wst.tv/rankings/", "Snooker", headers="browser")
add("wst_participants", "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=100", "Snooker")
add("wst_events_probe", "https://events.snooker.web.gc.wstservices.co.uk/v2/", "Snooker")
add("wst_comps_probe", "https://comps.snooker.web.gc.wstservices.co.uk/v2/", "Snooker")
add("snooker_org_home", "https://www.snooker.org/", "Snooker")
add("snooker_org_2548", "https://www.snooker.org/res/index.asp?event=2548", "Snooker")
for ev in (2545, 2546, 2547, 2549, 2550, 2551, 2552, 2553):
    add(f"snooker_org_{ev}", f"https://www.snooker.org/res/index.asp?event={ev}", "Snooker")
add("snooker_org_rankings", "https://www.snooker.org/rnk/", "Snooker")

# ---------------------------------------------------------------- golf
add("pgatour_leaderboard", "https://www.pgatour.com/leaderboard", "Golf", headers="browser")
add("pgatour_bermuda", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528", "Golf", headers="browser")
add("pgatour_schedule", "https://www.pgatour.com/schedule", "Golf", headers="browser")
add("pgatour_stifel_classic", "https://www.pgatour.com/pgatour-champions/tournaments/2026/stifel-charity-classic/S2026045", "Golf", headers="browser")
add("dpwt_genesis", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/tee-times", "Golf", headers="browser")
add("dpwt_schedule", "https://www.europeantour.com/dpworld-tour/schedule/", "Golf", headers="browser")
add("dpwt_leaderboard", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/leaderboard/", "Golf", headers="browser")
add("lpga_tournaments", "https://www.lpga.com/tournaments", "Golf", headers="browser")
add("lpga_leaderboard", "https://www.lpga.com/leaderboard", "Golf", headers="browser")
add("owgr_ranking", "https://www.owgr.com/current-world-ranking", "Golf", headers="browser")

# ---------------------------------------------------------------- motor racing
add("f1_racing_2026", "https://www.formula1.com/en/racing/2026.html", "Motor Racing", headers="browser")
add("f1_mexico_gp", "https://www.formula1.com/en/racing/2026/mexico", "Motor Racing", headers="browser")
add("f1_drivers_2026", "https://www.formula1.com/en/results/2026/drivers", "Motor Racing", headers="browser")
add("f1_constructors_2026", "https://www.formula1.com/en/results/2026/team", "Motor Racing", headers="browser")
add("f1_brazil_gp", "https://www.formula1.com/en/racing/2026/brazil", "Motor Racing", headers="browser")
add("motogp_calendar", "https://www.motogp.com/en/calendar", "Motor Racing", headers="browser")
add("motogp_results", "https://www.motogp.com/en/results/2026", "Motor Racing", headers="browser")
add("motogp_standings", "https://www.motogp.com/en/championship/standings", "Motor Racing", headers="browser")
add("indycar_schedule", "https://www.indycar.com/Schedule", "Motor Racing", headers="browser")
add("nascar_schedule", "https://www.nascar.com/cup-series/schedule/", "Motor Racing", headers="browser")

# ---------------------------------------------------------------- greyhounds
for endpoint in ("fixtures", "meetings", "racecards", "cards", "races", "events"):
    add(f"gbgb_api_{endpoint}", f"https://api.gbgb.org.uk/api/{endpoint}?date=2026-10-24", "Greyhounds")
add("gbgb_results_api", "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100&date=2026-10-23&race_type=race", "Greyhounds")
add("gbgb_results_home", "https://www.gbgb.org.uk/results/", "Greyhounds", headers="browser")
add("gbgb_home", "https://www.gbgb.org.uk/", "Greyhounds", headers="browser")
add("gbgb_racecards_page", "https://www.gbgb.org.uk/racecards/", "Greyhounds", headers="browser")
add("gbgb_calendar", "https://www.gbgb.org.uk/racing-calendar/", "Greyhounds", headers="browser")
add("igb_home", "https://www.igb.ie/", "Greyhounds", headers="browser")

# ---------------------------------------------------------------- gaelic sports
add("gaa_home", "https://www.gaa.ie/", "Gaelic Sports", headers="browser")
add("gaa_fixtures", "https://www.gaa.ie/fixtures", "Gaelic Sports", headers="browser")
add("gaa_fixtures_football", "https://www.gaa.ie/fixtures/gaelic-football", "Gaelic Sports", headers="browser")
add("gaa_api_fixtures", "https://www.gaa.ie/api/fixtures", "Gaelic Sports")
add("gaacork_home", "https://gaacork.ie/", "Gaelic Sports", headers="browser")
add("gaacork_fixtures", "https://gaacork.ie/fixtures", "Gaelic Sports", headers="browser")
add("gaadublin_fixtures", "https://gaadublin.ie/fixtures", "Gaelic Sports", headers="browser")
add("gaakerry_fixtures", "https://kerrygaa.ie/fixtures", "Gaelic Sports", headers="browser")
add("ladiesgaelic_home", "https://ladiesgaelic.ie/", "Gaelic Sports", headers="browser")

# ---------------------------------------------------------------- handball
add("ehfcl_matches_m", "https://ehfcl.eurohandball.com/men/2026-27/matches/", "Handball", headers="browser")
add("ehfcl_standings_m", "https://ehfcl.eurohandball.com/men/2026-27/standings/", "Handball", headers="browser")
add("ehfcl_matches_w", "https://ehfcl.eurohandball.com/women/2026-27/matches/", "Handball", headers="browser")
add("ehf_home", "https://www.eurohandball.com/", "Handball", headers="browser")
add("hbl_spielplan", "https://www.dkb-handball-bundesliga.de/spielplan", "Handball", headers="browser")
add("hbl_tabelle", "https://www.dkb-handball-bundesliga.de/tabelle", "Handball", headers="browser")
add("tophaandbold_herreligaen", "https://tophaandbold.dk/stillinger/herreligaen", "Handball", headers="browser")
add("handbollsligan_home", "https://handbollsligan.se/", "Handball", headers="browser")
add("handbollsligan_tabell", "https://handbollsligan.se/tabell/", "Handball", headers="browser")
add("handbollsligan_spelprogram", "https://handbollsligan.se/spelprogram/", "Handball", headers="browser")
add("asobal_home", "https://asobal.es/", "Handball", headers="browser")
add("asobal_calendario", "https://asobal.es/calendario/", "Handball", headers="browser")
add("lnh_home", "https://www.lnh.fr/", "Handball", headers="browser")
add("lnh_calendrier", "https://www.lnh.fr/division-1/calendrier-et-resultats", "Handball", headers="browser")

OUT.write_text(json.dumps(targets, indent=1) + "\n")
print(f"{len(targets)} targets -> {OUT}")

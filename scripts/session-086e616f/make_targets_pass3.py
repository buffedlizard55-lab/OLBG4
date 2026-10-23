#!/usr/bin/env python3
"""Board AT — pass-3 capture: the calibration and fixture pages that pass 1 and pass 2 exposed.

Pass 2 proved which pages are server-rendered and which are client-side shells. Pass 3 adds only
what is still needed to originate a line for a sport we can already list fixtures for:

  * prior-season feeds, so a rating has a real sample behind it instead of 1-6 games
    (Liiga 2026, Lega Volley 2025/26 grid, Danish handball results, F1 per-race results,
     the 2025 Butterfield Bermuda Championship leaderboard)
  * fixtures for competitions whose table we can read but whose calendar we cannot
    (Gallagher PREM, TOP 14 journee 7, Danish handball kampprogram, IRL rankings)
  * the last official sources for cricket, darts and the NRL, all of which are client-side
    apps on their own domains but may be server-rendered elsewhere
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("targets_pass3.json")
targets: list[dict] = []


SEEN: set[str] = set()


def add(tid, url, sport, role="official", headers="bot", timeout=30, delay=None):
    if tid in SEEN:
        return
    SEEN.add(tid)
    t = {"id": tid, "url": url, "sport": sport, "role": role, "headers": headers, "timeout": timeout}
    if delay:
        t["delay"] = delay
    targets.append(t)


# ------------------------------------------------- calibration: prior-season official results
add("liiga_games_2026", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2026", "Ice Hockey", timeout=90)
add("liiga_standings_2026", "https://liiga.fi/api/v2/standings/?season=2026", "Ice Hockey")
add("legavolley_risultati_2025", "https://www.legavolley.it/risultati/?Anno=2025&IdCampionato=923", "Volleyball")
add("legavolley_classifica_2025", "https://www.legavolley.it/classifica/?Anno=2025&IdCampionato=923", "Volleyball")
add("legavolley_risultati_991_2025", "https://www.legavolley.it/risultati/?Anno=2025&IdCampionato=991", "Volleyball")
add("tophaandbold_resultater", "https://tophaandbold.dk/resultater", "Handball", headers="browser")
add("tophaandbold_resultater_herre", "https://tophaandbold.dk/resultater/herreligaen", "Handball", headers="browser")
add("tophaandbold_stilling", "https://tophaandbold.dk/stillinger/herreligaen", "Handball", headers="browser")
add("hbl_spielplan_alt", "https://www.dkb-handball-bundesliga.de/spielplan/2026-27", "Handball", headers="browser")
add("f1_results_2026", "https://www.formula1.com/en/results/2026/races", "Motor Racing", headers="browser")
add("f1_results_index", "https://www.formula1.com/en/results/2026", "Motor Racing", headers="browser")
add("f1_results_usa", "https://www.formula1.com/en/results/2026/races/usa/result", "Motor Racing", headers="browser")
add("pga_bermuda_2025", "https://www.pgatour.com/tournaments/2025/butterfield-bermuda-championship/R2025528", "Golf",
    headers="browser", timeout=60)
add("pga_leaderboard_2025_alt", "https://www.pgatour.com/leaderboard/2025/butterfield-bermuda-championship", "Golf",
    headers="browser", timeout=60)
add("dpwt_genesis_leaderboard", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/leaderboard/", "Golf",
    headers="browser", timeout=60)
add("dpwt_schedule_alt", "https://www.europeantour.com/dpworld-tour/schedule/", "Golf", headers="browser")
add("lpga_leaderboard_alt", "https://www.lpga.com/tournaments/2026/maybank-championship/leaderboard", "Golf", headers="browser")
add("euroleague_games_all", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2025/games", "Basketball", timeout=90)
add("eurocup_games_all", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2025/games", "Basketball", timeout=90)
add("nhl_standings_prev", "https://api-web.nhle.com/v1/standings/2026-04-16", "Ice Hockey")
add("nhl_sched_prevseason_last", "https://api-web.nhle.com/v1/schedule/2026-04-16", "Ice Hockey")

# ------------------------------------------------- fixtures for competitions we can already table
add("prem_fixtures_results_page", "https://www.premrugby.com/fixtures-results", "Rugby Union", headers="browser")
add("prem_standings_page", "https://www.premrugby.com/standings?competition=gallagher-prem", "Rugby Union",
    headers="browser")
add("urc_matchcentre_r4", "https://stats.unitedrugby.com/match-centre/2026-27/4", "Rugby Union", headers="browser")
add("urc_matchcentre_r5", "https://stats.unitedrugby.com/match-centre/2026-27/5", "Rugby Union", headers="browser")
add("urc_table_page", "https://stats.unitedrugby.com/match-centre/table/2026-27", "Rugby Union", headers="browser")
add("lnr_top14_calendrier_resultats", "https://top14.lnr.fr/calendrier-et-resultats", "Rugby Union", headers="browser")
add("lnr_top14_classement_page", "https://top14.lnr.fr/classement", "Rugby Union", headers="browser")

# ------------------------------------------------- rugby league
add("irl_rankings", "https://www.internationalrugbyleague.com/rankings", "Rugby League", headers="browser")
add("irl_rankings_alt", "https://www.internationalrugbyleague.com/rankings/", "Rugby League", headers="browser")
add("irl_matches", "https://www.internationalrugbyleague.com/matches", "Rugby League", headers="browser")
add("rlwc_news_pools", "https://www.rlwc2026.com/news/pools-announced-for-rlwc26/", "Rugby League", headers="browser")
add("rlwc_draw_men", "https://www.rlwc2026.com/draw/men/2026", "Rugby League", headers="browser")
add("rlwc_draw_men_alt", "https://www.rlwc2026.com/draws-and-pools/men", "Rugby League", headers="browser")
add("rlwc_results_men", "https://www.rlwc2026.com/results/men", "Rugby League", headers="browser")
add("rfl_news_wc", "https://www.rugby-league.com/news", "Rugby League", headers="browser")
add("superleague_fixtures", "https://www.superleague.co.uk/fixtures", "Rugby League", headers="browser")

# ------------------------------------------------- cricket: the boards' own match pages
add("eci_matches_api", "https://www.cricketireland.ie/api/matches", "Cricket")
add("eci_fixtures_odi", "https://www.cricketireland.ie/fixtures?series=ireland-v-namibia-2026", "Cricket", headers="browser")
add("icc_rankings_mens_t20i", "https://www.icc-cricket.com/rankings/team-rankings/mens/t20i", "Cricket", headers="browser")
add("icc_rankings_mens_odi", "https://www.icc-cricket.com/rankings/team-rankings/mens/odi", "Cricket", headers="browser")
add("icc_rankings_womens_odi", "https://www.icc-cricket.com/rankings/team-rankings/womens/odi", "Cricket", headers="browser")
add("icc_api_rankings", "https://www.icc-cricket.com/api/rankings/team?format=t20i&gender=men", "Cricket")
add("nz_c_blackcaps", "https://www.nzc.nz/blackcaps", "Cricket", headers="browser")
add("nz_c_series_india", "https://www.nzc.nz/series/india-tour-of-new-zealand-2026", "Cricket", headers="browser")
add("bcci_international_fixtures", "https://www.bcci.tv/international/fixtures", "Cricket", headers="browser")
add("bcci_series_india_nz", "https://www.bcci.tv/series/india-tour-of-new-zealand-2026", "Cricket", headers="browser")
add("pcb_matches", "https://www.pcb.com.pk/matches.html", "Cricket", headers="browser")
add("espncricinfo_fixtures", "https://www.espncricinfo.com/cricket-fixtures", "Cricket", headers="browser")
add("cwi_matches", "https://www.windiescricket.com/matches/", "Cricket", headers="browser")

# ------------------------------------------------- darts: last official attempts
add("pdc_rankings_oom_page", "https://www.pdc.tv/rankings/pdc-order-of-merit", "Darts", headers="browser")
add("pdc_ec_2026_page", "https://www.pdc.tv/tournaments/european-championship", "Darts", headers="browser")
add("pdc_ec_2026_alt", "https://www.pdc.tv/tournaments/machineseeker-european-championship", "Darts", headers="browser")
add("pdc_ec_draw_page", "https://www.pdc.tv/draws", "Darts", headers="browser")
add("pdc_api_events", "https://www.pdc.tv/api/events", "Darts")

# ------------------------------------------------- tennis: the current week on the official tours
add("wta_rankings_page", "https://www.wtatennis.com/rankings/singles", "Tennis", headers="browser")
add("wta_api_rankings_v2", "https://api.wtatennis.com/tennis/rankings?type=singles&rankDate=2026-10-20", "Tennis")
add("wta_api_rankings_v3", "https://api.wtatennis.com/tennis/rankings/singles/rankDate/2026-10-20", "Tennis")
add("wta_ningbo_op", "https://www.protennislive.com/posting/2026/2092/op.pdf", "Tennis")
add("wta_osaka_op", "https://www.protennislive.com/posting/2026/405/op.pdf", "Tennis")
add("wta_ningbo_mds", "https://www.protennislive.com/posting/2026/2092/mds.pdf", "Tennis")
add("wta_osaka_mds", "https://www.protennislive.com/posting/2026/405/mds.pdf", "Tennis")
add("atp_brussels_op", "https://www.protennislive.com/posting/2026/7480/op.pdf", "Tennis")
add("atp_almaty_op", "https://www.protennislive.com/posting/2026/7481/op.pdf", "Tennis")
add("atp_lyon_op", "https://www.protennislive.com/posting/2026/7482/op.pdf", "Tennis")
for tid in ("7478", "7479", "7483", "7484", "7486", "7487", "7488", "7489", "7490"):
    add(f"atp_op_{tid}", f"https://www.protennislive.com/posting/2026/{tid}/op.pdf", "Tennis")

# ------------------------------------------------- basketball: last official NBA attempts
add("nba_statsapi_schedule", "https://stats.nba.com/stats/scheduleleaguev2?Season=2026-27&LeagueID=00", "Basketball",
    headers="browser", timeout=180)
add("nba_statsapi_scoreboard", "https://stats.nba.com/stats/scoreboardv3?DayOffset=0&LeagueID=00&GameDate=2026-10-24",
    "Basketball", headers="browser", timeout=180)
add("nba_cdn_scoreboard_alt", "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "Basketball", timeout=60)
add("nba_euroleague_standings_page", "https://www.euroleaguebasketball.net/euroleague/standings/", "Basketball",
    headers="browser")

# ------------------------------------------------- gaelic: provincial club championship pages
add("connachtgaa_fixtures", "https://connachtgaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("munstergaa_fixtures", "https://munster.gaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("leinstergaa_fixtures", "https://leinster.gaa.ie/fixtures-results/", "Gaelic Sports", headers="browser")
add("ulstergaa_results", "https://ulster.gaa.ie/results/", "Gaelic Sports", headers="browser")
add("ladiesgaelic_fixtures", "https://ladiesgaelic.ie/fixtures/", "Gaelic Sports", headers="browser")

# ------------------------------------------------- greyhounds: the last official racecard attempts
add("gbgb_results_25", "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100&date=2026-10-25&race_type=race",
    "Greyhounds")
add("gbgb_api_dogs", "https://api.gbgb.org.uk/api/dogs?page=1&itemsPerPage=20", "Greyhounds")
add("gbgb_api_tracks", "https://api.gbgb.org.uk/api/tracks", "Greyhounds")
add("gbgb_api_races_v2", "https://api.gbgb.org.uk/api/races?date=24/10/2026", "Greyhounds")
add("gbgb_open_races_oaks", "https://www.gbgb.org.uk/racing/open-races/premier-greyhound-racing-oaks/", "Greyhounds",
    headers="browser")
add("gbgb_scurry", "https://www.gbgb.org.uk/racing/open-races/arena-racing-company-scurry-gold-cup/", "Greyhounds",
    headers="browser")
add("gri_racing_today", "https://www.igb.ie/todays-racing", "Greyhounds", headers="browser")

# ------------------------------------------------- NHL: completed games, so the margin dispersion
# and each club's last five results come from official scores rather than from an assumption
NHL_DATES = [
    "2026-10-06", "2026-10-07", "2026-10-08", "2026-10-09", "2026-10-10", "2026-10-13",
    "2026-10-14", "2026-10-15", "2026-10-16", "2026-10-17", "2026-10-20", "2026-10-21", "2026-10-22",
]
for d in NHL_DATES:
    add(f"nhl_sched_prev_{d}", f"https://api-web.nhle.com/v1/schedule/{d}", "Ice Hockey", timeout=45)
for code in ("EDM", "CGY", "BOS", "CHI", "COL", "VAN", "TOR", "MTL", "TBL", "NYR"):
    add(f"nhl_club_prev_{code}", f"https://api-web.nhle.com/v1/club-schedule/{code}/week/2026-10-19", "Ice Hockey",
        timeout=45)

# ------------------------------------------------- volleyball: last season, for a real rating sample
add("legavolley_risultati_2025_923", "https://www.legavolley.it/risultati/?Anno=2025&IdCampionato=923", "Volleyball")

# ------------------------------------------------- handball: every remaining fixture route
add("ehfcl_m_2026_matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/", "Handball", headers="browser")
add("ehfcl_w_2026_matches", "https://ehfcl.eurohandball.com/women/2026-27/matches/", "Handball", headers="browser")
add("ehf_matches_api", "https://ehfcl.eurohandball.com/api/v1/matches", "Handball")
add("tophaandbold_kampprogram_alt", "https://tophaandbold.dk/kampprogram/herreligaen", "Handball", headers="browser")
add("dhf_home", "https://www.danskhaandbold.dk/", "Handball", headers="browser")

# ------------------------------------------------- rugby league: official ratings and results
add("irl_rankings_men", "https://www.internationalrugbyleague.com/rankings/men", "Rugby League", headers="browser")
add("irl_rankings_women", "https://www.internationalrugbyleague.com/rankings/women", "Rugby League", headers="browser")
add("irl_rankings_wheelchair", "https://www.internationalrugbyleague.com/rankings/wheelchair", "Rugby League",
    headers="browser")
add("rlwc_results_men_page", "https://www.rlwc2026.com/results/men", "Rugby League", headers="browser")
add("rlwc_ladder_men", "https://www.rlwc2026.com/ladder/men", "Rugby League", headers="browser")
add("rlwc_news_home", "https://www.rlwc2026.com/news/", "Rugby League", headers="browser")

# ------------------------------------------------- cricket: official fixtures and ratings
add("icc_rankings_api_v2", "https://www.icc-cricket.com/api/v1/rankings/team?format=t20i", "Cricket")
add("icc_api_fixtures", "https://www.icc-cricket.com/api/fixtures", "Cricket")
add("nz_c_fixtures_page", "https://www.nzc.nz/fixtures-results", "Cricket", headers="browser")
add("nz_c_blackcaps_india", "https://www.nzc.nz/news/blackcaps-v-india", "Cricket", headers="browser")
add("bcci_series_page", "https://www.bcci.tv/series", "Cricket", headers="browser")
add("eci_series_page", "https://www.cricketireland.ie/series", "Cricket", headers="browser")
add("pcb_news", "https://www.pcb.com.pk/press-release.html", "Cricket", headers="browser")
add("espncricinfo_calendar", "https://www.espncricinfo.com/ci/engine/match/index.html?view=calendar", "Cricket",
    headers="browser")

# ------------------------------------------------- gaelic: results, so a rating could exist
add("mayogaa_results", "https://mayogaa.com/results/", "Gaelic Sports", headers="browser")
add("leitrimgaa_results", "https://www.leitrimgaa.ie/results/", "Gaelic Sports", headers="browser")
add("claregaa_results", "https://clare.gaa.ie/results/", "Gaelic Sports", headers="browser")
add("ulstergaa_results", "https://ulster.gaa.ie/results/", "Gaelic Sports", headers="browser")
add("kilkennygaa_results", "https://kilkennygaa.ie/results/", "Gaelic Sports", headers="browser")

# ------------------------------------------------- darts: the WDF and the PDC event page variants
add("wdf_events", "https://darts.wdf.org/events", "Darts", headers="browser")
add("wdf_home_alt", "https://wdf.org/", "Darts", headers="browser")
add("pdc_ec_2026_event", "https://www.pdc.tv/tournaments/2026-european-championship", "Darts", headers="browser")
add("pdc_draws_page", "https://www.pdc.tv/draws-results", "Darts", headers="browser")
add("pdc_api_rankings", "https://www.pdc.tv/api/rankings", "Darts")

# ------------------------------------------------- greyhounds: the racecard that the Cat-1 page names
add("gbgb_dunstall", "https://www.gbgb.org.uk/racing/track/dunstall-park/", "Greyhounds", headers="browser")
add("gbgb_api_results_page2", "https://api.gbgb.org.uk/api/results?page=2&itemsPerPage=100", "Greyhounds")
add("gbgb_api_openraces", "https://api.gbgb.org.uk/api/open-races", "Greyhounds")
add("gri_today_racing", "https://www.igb.ie/todays-racing", "Greyhounds", headers="browser")

# ------------------------------------------------- tennis: ATP tour IDs via the official posting host
for tid in ("7475", "7476", "7477", "7491", "7492", "7493", "7494", "7495"):
    add(f"atp_op_b_{tid}", f"https://www.protennislive.com/posting/2026/{tid}/op.pdf", "Tennis")
add("wta_rankings_api_p0", "https://api.wtatennis.com/tennis/rankings/singles?page=0&pageSize=100", "Tennis")
add("wta_players_api", "https://api.wtatennis.com/tennis/players?page=0&pageSize=100", "Tennis")

OUT.write_text(json.dumps(targets, indent=1) + "\n")
print(f"{len(targets)} pass-3 targets -> {OUT}")

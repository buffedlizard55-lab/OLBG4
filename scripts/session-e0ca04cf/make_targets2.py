#!/usr/bin/env python3
"""Second-pass capture targets: machine-readable endpoints for the sports whose
first-pass HTML tables turned out to be JavaScript-rendered.

SvelteKit/Nuxt routes often expose a ``/__data.json`` twin; league sites often
expose a JSON feed.  Every candidate here is additive: a 404 or 403 just gets
logged in the manifest and the row stays unpriced rather than being guessed.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "targets2.json"
T: list[dict] = []


def add(sport: str, tid: str, url: str, delay: float = 0.5) -> None:
    T.append({"sport": sport, "id": tid, "url": url, "delay": delay})


# ------------------------------------------------------- Rugby Union tables
add("Rugby Union", "urc_table_data", "https://stats.unitedrugby.com/match-centre/table/2026-27/__data.json")
add("Rugby Union", "urc_root_data", "https://stats.unitedrugby.com/__data.json")
add("Rugby Union", "urc_round6_data", "https://stats.unitedrugby.com/match-centre/2026-27/6/__data.json")
add("Rugby Union", "urc_round7_data", "https://stats.unitedrugby.com/match-centre/2026-27/7/__data.json")
add("Rugby Union", "prem_api_fixtures", "https://www.premiershiprugby.com/api/fixtures")
add("Rugby Union", "prem_standings_data", "https://www.premiershiprugby.com/standings/__data.json")
add("Rugby Union", "top14_api_classement", "https://top14.lnr.fr/api/classement")
add("Rugby Union", "top14_api_calendrier", "https://top14.lnr.fr/api/calendrier")
add("Rugby Union", "world_rugby_rankings", "https://www.world.rugby/tournaments/rankings/mru")
add("Rugby Union", "world_rugby_fixtures", "https://www.world.rugby/tournaments/autumn-nations-series/fixtures")

# ---------------------------------------------------------------- Cricket
add("Cricket", "icc_t20i_api", "https://api.icc-cricket.com/rankings/mens/team/t20i")
add("Cricket", "icc_odi_api", "https://api.icc-cricket.com/rankings/mens/team/odi")
add("Cricket", "cricket_au_api_fixtures", "https://www.cricket.com.au/api/fixtures")
add("Cricket", "cricket_au_data", "https://www.cricket.com.au/__data.json")
add("Cricket", "ecb_api_fixtures", "https://www.ecb.co.uk/api/fixtures")
add("Cricket", "nzc_api_fixtures", "https://www.nzc.nz/api/fixtures")
add("Cricket", "icc_rankings_test", "https://www.icc-cricket.com/rankings/mens/team-rankings/test")
add("Cricket", "cricket_au_bbl", "https://www.cricket.com.au/fixtures/bbl")
add("Cricket", "bigbash_data", "https://www.bigbash.com.au/__data.json")

# ----------------------------------------------------------------- Tennis
add("Tennis", "wta_tournaments", "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100")
add("Tennis", "wta_tournaments_2026", "https://api.wtatennis.com/tennis/tournaments/2026?page=0&pageSize=100")
add("Tennis", "atp_scores_current", "https://api.atptour.com/scores/current")
add("Tennis", "atp_tournaments", "https://api.atptour.com/tournaments")
add("Tennis", "atp_rankings_race", "https://api.atptour.com/rankings/race-singles?rankRange=1-100&format=json")
add("Tennis", "ptl_7480_mds", "https://www.protennislive.com/posting/2026/7480/mds.pdf")
add("Tennis", "ptl_7480_op", "https://www.protennislive.com/posting/2026/7480/op.pdf")
add("Tennis", "ptl_2026_cal", "https://www.protennislive.com/posting/current/qs.pdf")

# ------------------------------------------------------------------ Darts
add("Darts", "pdc_match_centre", "https://www.pdc.tv/match-centre")
add("Darts", "pdc_api_matches", "https://api.pdc.tv/matches")
add("Darts", "pdc_pcf", "https://www.pdc.tv/tournaments/machineseeker-players-championship-finals")
add("Darts", "pdc_grandslam", "https://www.pdc.tv/tournaments/boyle-sports-grand-slam-of-darts")
add("Darts", "pdc_et", "https://www.pdc.tv/european-tour")
add("Darts", "pdc_oom_data", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit/__data.json")

# ------------------------------------------------------------------- Golf
add("Golf", "pgatour_field_bermuda", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528/field")
add("Golf", "pgatour_leaderboard_api", "https://www.pgatour.com/api/leaderboard")
add("Golf", "dpwt_leaderboard", "https://www.europeantour.com/dpworld-tour/leaderboard")
add("Golf", "owgr_top50", "https://www.owgr.com/current-world-ranking?page=1&pageSize=100")

# -------------------------------------------------------------- Greyhounds
add("Greyhounds", "gbgb_api_meetings_today", "https://api.gbgb.org.uk/api/meetings?date=2026-10-24")
add("Greyhounds", "gbgb_api_races_type", "https://api.gbgb.org.uk/api/races?date=2026-10-25&page=1&itemsPerPage=50&race_type=race")
add("Greyhounds", "gbgb_racecard_index", "https://www.gbgb.org.uk/racecard/")
add("Greyhounds", "gbgb_results_index", "https://www.gbgb.org.uk/results/")

# ------------------------------------------------------------------ Gaelic
add("Gaelic Sports", "gaa_api_fixtures", "https://www.gaa.ie/api/fixtures")
add("Gaelic Sports", "gaa_data_fixtures", "https://www.gaa.ie/fixtures/__data.json")
add("Gaelic Sports", "gaa_club_fixtures", "https://www.gaa.ie/club/fixtures")

# ----------------------------------------------------------------- Handball
add("Handball", "ehfcl_m_matches_static", "https://ehfcl.eurohandball.com/men/2026-27/matches/")
add("Handball", "ehfel_m_matches_static", "https://ehfel.eurohandball.com/men/2026-27/matches/")
add("Handball", "hbl_spielplan_static", "https://www.dkb-handball-bundesliga.de/spielplan")
add("Handball", "lnh_calendrier", "https://www.lnh.fr/calendrier")
add("Handball", "asobal_calendario", "https://asobal.es/calendario/")
add("Handball", "ehfcl_m_data", "https://ehfcl.eurohandball.com/men/2026-27/standings/__data.json")

# --------------------------------------------------------------- Basketball
add("Basketball", "nba_cdn_schedule_2", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_2.json")
add("Basketball", "nba_cdn_scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")
add("Basketball", "el_standings_rs", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings?phase=RS")
add("Basketball", "eurocup_standings_rs", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/standings?phase=RS")

# --------------------------------------------------------------- Ice hockey
add("Ice Hockey", "nhl_club_stats", "https://api-web.nhle.com/v1/club-stats/current")

# ------------------------------------------------------------ Rugby League
add("Rugby League", "rlwc_api_fixtures_alt", "https://www.rlwc2026.com/api/matches")

if __name__ == "__main__":
    OUT.write_text(json.dumps(T, indent=1) + "\n")
    print(f"{len(T)} pass-2 targets -> {OUT}")

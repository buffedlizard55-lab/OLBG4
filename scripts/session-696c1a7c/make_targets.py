#!/usr/bin/env python3
"""Build the Board SA capture target lists.

Round 1 (`targets1.json`) is a discovery pass: the 15 OLBG sport hubs we need, a
handful of OLBG listing-shape candidates, and candidate governing-body endpoints
for every sport. Anything that 404s or is refused is recorded in the capture
manifest and dropped from round 2, so no URL in this file is ever asserted to be
a source of fact.

Round 2 (`targets2.json`) is written by this script from the round-1 manifest
once the reachable endpoints are known.
"""
from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "targets1.json"

OLBG = "https://www.olbg.com/betting-tips"
SPORT_HUBS = {
    "Golf": (5, "Golf"),
    "Volleyball": (21, "Volleyball"),
    "Rugby Union": (9, "Rugby_Union"),
    "Cricket": (7, "Cricket"),
    "Snooker": (8, "Snooker"),
    "Darts": (15, "Darts"),
    "Baseball": (12, "Baseball"),
    "Gaelic Sports": (25, "Gaelic_Football"),
    "Greyhounds": (28, "Greyhounds"),
    "Tennis": (3, "Tennis"),
    "Motor Racing": (14, "Motor_Racing"),
    "Handball": (20, "Handball"),
    "Ice Hockey": (13, "Ice_Hockey"),
    "Basketball": (4, "Basketball"),
    "Rugby League": (10, "Rugby_League"),
}

T: list[dict] = []


def add(sport: str, tid: str, url: str, delay: float = 0.35, attempts: int = 1,
        accept: str | None = None) -> None:
    rec = {"sport": sport, "id": tid, "url": url, "delay": delay, "attempts": attempts}
    if accept:
        rec["accept"] = accept
    T.append(rec)


# --- OLBG: structure, then the 15 sport hubs (one fetch each, delayed) --------
add("OLBG", "olbg_robots", f"{OLBG}/../robots.txt", 0.5)
add("OLBG", "olbg_sitemap_tips", "https://www.olbg.com/sitemap-betting-tips.xml", 0.5)
for sport, (sid, slug) in SPORT_HUBS.items():
    add(sport, f"olbg_{slug.lower()}_hub", f"{OLBG}/{slug}/{sid}", 1.2)
# Listing-shape candidates: does OLBG expose a fuller all-events listing?
add("Basketball", "olbg_shape_all_events", f"{OLBG}/Basketball/All_Basketball/All_Events/4", 1.2)
add("Basketball", "olbg_shape_nba", f"{OLBG}/Basketball/NBA/4", 1.2)
add("Gaelic Sports", "olbg_gaelic_hurling", f"{OLBG}/Hurling/26", 1.2)

# --- Ice hockey -------------------------------------------------------------
start, end = date(2026, 10, 24), date(2026, 11, 8)
d = start
while d <= end:
    add("Ice Hockey", f"nhl_sched_{d.isoformat()}",
        f"https://api-web.nhle.com/v1/schedule/{d.isoformat()}", 0.2)
    d += timedelta(days=1)
add("Ice Hockey", "nhl_standings", "https://api-web.nhle.com/v1/standings/now", 0.2)
add("Ice Hockey", "nhl_skater_leaders",
    "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals,points&limit=25", 0.2)
add("Ice Hockey", "nhl_goalie_leaders",
    "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=savePctg,goalsAgainstAverage&limit=25", 0.2)
add("Ice Hockey", "shl_overview", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961", 0.4)
add("Ice Hockey", "shl_standings", "https://stats.swehockey.se/ScheduleAndResults/Standings/20961", 0.4)
add("Ice Hockey", "liiga_games", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", 0.4)
add("Ice Hockey", "liiga_standings", "https://liiga.fi/api/v2/standings/?season=2027", 0.4)
add("Ice Hockey", "nl_games", "https://www.nationalleague.ch/api/games?season=2026", 0.4)
add("Ice Hockey", "del_games", "https://www.penny-del.org/api/", 0.4)

# --- Baseball ---------------------------------------------------------------
add("Baseball", "mlb_schedule",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-24&endDate=2026-11-08"
    "&hydrate=probablePitcher,linescore,team", 0.3)
add("Baseball", "mlb_standings",
    "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason", 0.3)
add("Baseball", "mlb_hitting",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1", 0.3)
add("Baseball", "mlb_pitching",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1", 0.3)

# --- Basketball -------------------------------------------------------------
add("Basketball", "el_games", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", 0.3)
add("Basketball", "eurocup_games", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games", 0.3)
add("Basketball", "acb_calendario", "https://www.acb.com/calendario/", 0.4)
add("Basketball", "acb_clasificacion", "https://www.acb.com/clasificacion/", 0.4)
add("Basketball", "lega_basket", "https://www.legabasket.it/", 0.4)
add("Basketball", "nba_cdn_scoreboard",
    "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", 0.3)
add("Basketball", "nba_cdn_schedule",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", 0.3)
add("Basketball", "bsl_fixtures", "https://www.bsl.org.tr/", 0.4)
add("Basketball", "vtb_games", "https://vtb-league.com/en/games/", 0.4)

# --- Cricket ----------------------------------------------------------------
for t in ("t20i", "odi", "test"):
    add("Cricket", f"icc_{t}_rankings",
        f"https://www.icc-cricket.com/rankings/mens/team-rankings/{t}", 0.4)
add("Cricket", "cricket_au_fixtures", "https://www.cricket.com.au/fixtures", 0.4)
add("Cricket", "nzc_matches", "https://www.nzc.nz/matches", 0.4)
add("Cricket", "ecb_fixtures", "https://www.ecb.co.uk/england/men/fixtures", 0.4)
add("Cricket", "bcci_home", "https://www.bcci.tv/", 0.4)
add("Cricket", "pcb_home", "https://www.pcb.com.pk/", 0.4)
add("Cricket", "csa_home", "https://cricket.co.za/", 0.4)
add("Cricket", "windies_home", "https://www.windiescricket.com/", 0.4)
add("Cricket", "slc_home", "https://srilankacricket.lk/", 0.4)
add("Cricket", "cricket_ireland", "https://www.cricketireland.ie/", 0.4)

# --- Snooker ----------------------------------------------------------------
add("Snooker", "wst_matches_api",
    "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=250&sort=startDateTime"
    "&filter[startDateTime][gte]=2026-10-24&filter[startDateTime][lte]=2026-11-08", 0.3)
add("Snooker", "wst_participants",
    "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=300", 0.3)
add("Snooker", "wst_rankings", "https://www.wst.tv/rankings/", 0.3)
add("Snooker", "snooker_org_cal", "https://www.snooker.org/res/index.asp?template=2", 0.4)

# --- Darts ------------------------------------------------------------------
add("Darts", "pdc_oom", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit", 0.4)
add("Darts", "pdc_api_matches",
    "https://matches.pdc.web.gc.pdcservices.co.uk/v2/?page.size=250&sort=startDateTime"
    "&filter[startDateTime][gte]=2026-10-24&filter[startDateTime][lte]=2026-11-08", 0.3)
add("Darts", "pdc_api_participants",
    "https://participants.pdc.web.gc.pdcservices.co.uk/v2/?page.size=300", 0.3)
add("Darts", "pdc_api_tournaments",
    "https://tournaments.pdc.web.gc.pdcservices.co.uk/v2/?page.size=100", 0.3)
add("Darts", "wdf_home", "https://www.dartswdf.com/", 0.4)
add("Darts", "pdc_et_page", "https://www.pdc.tv/tournaments/machineseeker-european-championship", 0.4)

# --- Golf -------------------------------------------------------------------
add("Golf", "pgatour_leaderboard", "https://www.pgatour.com/leaderboard", 0.4)
add("Golf", "pgatour_schedule", "https://www.pgatour.com/schedule", 0.4)
add("Golf", "dpwt_tee_times",
    "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/tee-times", 0.4)
add("Golf", "dpwt_schedule", "https://www.europeantour.com/dpworld-tour/schedule", 0.4)
add("Golf", "owgr", "https://www.owgr.com/current-world-ranking", 0.4)
add("Golf", "lpga_tournaments", "https://www.lpga.com/tournaments", 0.4)

# --- Gaelic Sports ----------------------------------------------------------
add("Gaelic Sports", "gaa_fixtures", "https://www.gaa.ie/fixtures", 0.5)
add("Gaelic Sports", "gaa_results", "https://www.gaa.ie/fixtures-results", 0.5)
add("Gaelic Sports", "gaa_club", "https://www.gaa.ie/club-news", 0.5)
add("Gaelic Sports", "gaacork_fixtures", "https://gaacork.ie/fixtures", 0.5)
add("Gaelic Sports", "galwaygaa_fixtures", "https://galwaygaa.ie/fixtures/", 0.5)
add("Gaelic Sports", "dublingaa_fixtures", "https://www.dublingaa.ie/fixtures", 0.5)
add("Gaelic Sports", "gaa_api_guess", "https://www.gaa.ie/api/fixtures", 0.5)

# --- Greyhounds -------------------------------------------------------------
add("Greyhounds", "gbgb_results",
    "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100&date=2026-10-23&race_type=race", 0.4)
add("Greyhounds", "gbgb_racecards_api",
    "https://api.gbgb.org.uk/api/racecards?date=2026-10-25", 0.4)
add("Greyhounds", "gbgb_fixtures_api", "https://api.gbgb.org.uk/api/fixtures?date=2026-10-25", 0.4)
add("Greyhounds", "gbgb_home", "https://www.gbgb.org.uk/", 0.4)
add("Greyhounds", "gbgb_racing", "https://www.gbgb.org.uk/racing", 0.4)

# --- Tennis -----------------------------------------------------------------
add("Tennis", "wta_rankings", "https://api.wtatennis.com/tennis/players/rankings/singles?page=0&pageSize=200", 0.3)
add("Tennis", "wta_calendar", "https://api.wtatennis.com/tennis/tournaments?page=0&pageSize=80", 0.3)
add("Tennis", "wta_calendar_html", "https://www.wtatennis.com/tournaments", 0.4)
for tid in (1023, 1056, 2092, 405):
    add("Tennis", f"wta_t_{tid}", f"https://api.wtatennis.com/tennis/tournaments/{tid}/2026/matches", 0.3)
for pid in (328, 337, 496, 7485, 9410):
    add("Tennis", f"ptl_{pid}_mds", f"https://www.protennislive.com/posting/2026/{pid}/mds.pdf", 0.3)
    add("Tennis", f"ptl_{pid}_op", f"https://www.protennislive.com/posting/2026/{pid}/op.pdf", 0.3)
add("Tennis", "atp_rankings_html", "https://www.atptour.com/en/rankings/singles?rankRange=1-100", 0.4)
add("Tennis", "atp_calendar_html", "https://www.atptour.com/en/tournaments", 0.4)
add("Tennis", "ptl_live", "https://www.protennislive.com/lshs/default.asp", 0.3)

# --- Motor Racing -----------------------------------------------------------
add("Motor Racing", "f1_racing_2026", "https://www.formula1.com/en/racing/2026.html", 0.4)
add("Motor Racing", "f1_mexico", "https://www.formula1.com/en/racing/2026/mexico", 0.4)
add("Motor Racing", "f1_drivers", "https://www.formula1.com/en/results/2026/drivers", 0.4)
add("Motor Racing", "f1_teams", "https://www.formula1.com/en/results/2026/team", 0.4)
add("Motor Racing", "f1_race_results", "https://www.formula1.com/en/results/2026/races", 0.4)
add("Motor Racing", "motogp_calendar", "https://www.motogp.com/en/calendar/2026", 0.4)
add("Motor Racing", "motogp_results", "https://www.motogp.com/en/results/2026", 0.4)
add("Motor Racing", "f2_home", "https://www.fiaformula2.com/", 0.4)

# --- Handball ---------------------------------------------------------------
add("Handball", "ehfcl_m_matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/", 0.4)
add("Handball", "ehfcl_m_standings", "https://ehfcl.eurohandball.com/men/2026-27/standings/", 0.4)
add("Handball", "ehfcl_w_matches", "https://ehfcl.eurohandball.com/women/2026-27/matches/", 0.4)
add("Handball", "hbl_spielplan", "https://www.dkb-handball-bundesliga.de/spielplan", 0.4)
add("Handball", "hbl_tabelle", "https://www.dkb-handball-bundesliga.de/tabelle", 0.4)
add("Handball", "dk_herreligaen", "https://tophaandbold.dk/stillinger/herreligaen", 0.4)
add("Handball", "dk_program", "https://tophaandbold.dk/kampprogram", 0.4)
add("Handball", "handbollsligan", "https://handbollsligan.se/", 0.4)
add("Handball", "lnh_calendrier", "https://www.lnh.fr/calendrier-et-resultats", 0.4)
add("Handball", "lnh_classement", "https://www.lnh.fr/classement", 0.4)
add("Handball", "asobal_calendario", "https://asobal.es/calendario/", 0.4)
add("Handball", "asobal_clasificacion", "https://asobal.es/clasificacion/", 0.4)
add("Handball", "zprp_terminarz", "https://zprp.pl/terminarz/", 0.4)
add("Handball", "kezilabda_hu", "https://www.kezilabda.hu/", 0.4)
add("Handball", "handball_no", "https://www.handball.no/", 0.4)

# --- Rugby Union ------------------------------------------------------------
add("Rugby Union", "urc_fixtures_in_full",
    "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", 0.4)
add("Rugby Union", "urc_table", "https://stats.unitedrugby.com/match-centre/table/2026-27", 0.4)
add("Rugby Union", "urc_api_guess", "https://api.unitedrugby.com/v1/fixtures?season=2026-27", 0.4)
add("Rugby Union", "top14_cal", "https://top14.lnr.fr/calendrier-et-resultats", 0.4)
add("Rugby Union", "top14_classement", "https://top14.lnr.fr/classement", 0.4)
add("Rugby Union", "prem_fixtures", "https://www.premiershiprugby.com/fixtures-results", 0.4)
add("Rugby Union", "prem_standings", "https://www.premiershiprugby.com/standings", 0.4)
add("Rugby Union", "epcr_champions_cup", "https://www.epcrugby.com/champions-cup/fixtures", 0.4)
add("Rugby Union", "super_rugby_fixtures", "https://super.rugby/superrugby/fixtures/", 0.4)

# --- Rugby League -----------------------------------------------------------
add("Rugby League", "rlwc_fixtures", "https://www.rlwc2026.com/fixtures", 0.4)
add("Rugby League", "rlwc_api_fixtures", "https://www.rlwc2026.com/api/fixtures", 0.4)
add("Rugby League", "rlwc_draws", "https://www.rlwc2026.com/draws-and-pools", 0.4)
add("Rugby League", "nrl_draw", "https://www.nrl.com/draw/", 0.4)
add("Rugby League", "nrl_ladder", "https://www.nrl.com/ladder/", 0.4)
add("Rugby League", "superleague_fixtures", "https://www.superleague.co.uk/fixtures", 0.4)
add("Rugby League", "superleague_table", "https://www.superleague.co.uk/table", 0.4)

# --- Volleyball -------------------------------------------------------------
for cid in (991, 995, 997, 998, 999, 1000, 1001, 1002, 1003, 1004):
    add("Volleyball", f"legavolley_cal_{cid}",
        f"https://www.legavolley.it/calendario/?Anno=2026&IdCampionato={cid}", 0.3)
add("Volleyball", "legavolley_classifica", "https://www.legavolley.it/classifica/", 0.3)
add("Volleyball", "plusliga_table", "https://plusliga.pl/table/tour/47.html", 0.4)
add("Volleyball", "plusliga_fixtures", "https://www.plusliga.pl/mecze/tour/47.html", 0.4)
add("Volleyball", "cvf_extraliga",
    "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147", 0.4)
add("Volleyball", "cev_matches", "https://www.cev.eu/club/competitions/", 0.4)
add("Volleyball", "volleyballworld", "https://en.volleyballworld.com/volleyball/competitions/", 0.4)


if __name__ == "__main__":
    OUT.write_text(json.dumps(T, indent=1) + "\n")
    sports = sorted({t["sport"] for t in T})
    print(f"wrote {OUT} with {len(T)} targets across {len(sports)} labels")
    sys.exit(0)

#!/usr/bin/env python3
"""Build the Board EC capture target list (official sources + OLBG listings).

Window: 2026-10-25 .. 2026-11-08 UTC (the upcoming block after the 24 Oct cutoff).

Only governing-body / league / tour / track sources are used for fixtures and
form.  OLBG pages are captured separately and used only for two things: (a) to
confirm an event is actually listed on OLBG, and (b) to read the OLBG price that
is displayed on the listing.  OLBG is never treated as a source of fact about a
team, a player, a score or an injury.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "targets.json"

START = date(2026, 10, 25)
END = date(2026, 11, 8)


def days():
    d = START
    while d <= END:
        yield d
        d += timedelta(days=1)


T: list[dict] = []


def add(sport: str, tid: str, url: str, delay: float = 0.5) -> None:
    T.append({"sport": sport, "id": tid, "url": url, "delay": delay})


# ------------------------------------------------------------------ OLBG tax
add("OLBG", "olbg_robots", "https://www.olbg.com/robots.txt")
add("OLBG", "olbg_all", "https://www.olbg.com/betting-tips")
add("OLBG", "olbg_sports_nav", "https://www.olbg.com/betting-tips/all-sports")

# OLBG per-sport hubs (IDs 3..28 are the site's own sport ids)
OLBG_HUBS = {
    "Golf": ("olbg_golf", "Golf/5"),
    "Volleyball": ("olbg_volleyball", "Volleyball/21"),
    "Rugby Union": ("olbg_rugbyunion", "Rugby_Union/9"),
    "Cricket": ("olbg_cricket", "Cricket/7"),
    "Snooker": ("olbg_snooker", "Snooker/8"),
    "Darts": ("olbg_darts", "Darts/15"),
    "Baseball": ("olbg_baseball", "Baseball/12"),
    "Gaelic Sports": ("olbg_gaelic", "Gaelic_Football/25"),
    "Gaelic Sports": ("olbg_hurling", "Hurling/26"),
    "Greyhounds": ("olbg_greyhounds", "Greyhounds/28"),
    "Tennis": ("olbg_tennis", "Tennis/3"),
    "Motor Racing": ("olbg_motorracing", "Motor_Racing/14"),
    "Handball": ("olbg_handball", "Handball/20"),
    "Ice Hockey": ("olbg_icehockey", "Ice_Hockey/13"),
    "Basketball": ("olbg_basketball", "Basketball/4"),
    "Rugby League": ("olbg_rugbyleague", "Rugby_League/10"),
}
for _s, (tid, path) in OLBG_HUBS.items():
    add(_s, tid, f"https://www.olbg.com/betting-tips/{path}", delay=0.8)

# OLBG full event lists (the "All_<sport> / All_Events" views) so that every
# fixture we publish can be tied to a real OLBG event page.
OLBG_FULL = {
    "Golf": ("olbg_all_golf", "Golf"),
    "Volleyball": ("olbg_all_volleyball", "Volleyball"),
    "Rugby Union": ("olbg_all_rugbyunion", "Rugby_Union"),
    "Cricket": ("olbg_all_cricket", "Cricket"),
    "Snooker": ("olbg_all_snooker", "Snooker"),
    "Darts": ("olbg_all_darts", "Darts"),
    "Baseball": ("olbg_all_baseball", "Baseball"),
    "Gaelic Sports": ("olbg_all_gaelic", "Gaelic_Football"),
    "Greyhounds": ("olbg_all_greyhounds", "Greyhounds"),
    "Tennis": ("olbg_all_tennis", "Tennis"),
    "Motor Racing": ("olbg_all_motorracing", "Motor_Racing"),
    "Handball": ("olbg_all_handball", "Handball"),
    "Ice Hockey": ("olbg_all_icehockey", "Ice_Hockey"),
    "Basketball": ("olbg_all_basketball", "Basketball"),
    "Rugby League": ("olbg_all_rugbyleague", "Rugby_League"),
}
for _s, (tid, seg) in OLBG_FULL.items():
    add(_s, tid, f"https://www.olbg.com/betting-tips/{seg}/All_{seg}/All_Events", delay=0.8)

# ---------------------------------------------------------------- Golf
add("Golf", "pgatour_schedule", "https://www.pgatour.com/schedule")
add("Golf", "pgatour_leaderboard", "https://www.pgatour.com/leaderboard")
add("Golf", "pgatour_stats", "https://www.pgatour.com/stats")
add("Golf", "pgatour_cup", "https://www.pgatour.com/stats/stat.02671.html")
add("Golf", "dpwt_schedule", "https://www.europeantour.com/dpworld-tour/schedule")
add("Golf", "dpwt_rankings", "https://www.europeantour.com/dpworld-tour/rankings")
add("Golf", "lpga_schedule", "https://www.lpga.com/tournaments")
add("Golf", "owgr", "https://www.owgr.com/current-world-ranking")
add("Golf", "lets_rock_golf", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528")

# -------------------------------------------------------------- Volleyball
for _c in (991, 995, 997, 998, 999, 1000, 1001, 1002, 1003, 1004):
    add("Volleyball", f"legavolley_cal_{_c}", f"https://www.legavolley.it/calendario/?Anno=2026&IdCampionato={_c}")
add("Volleyball", "legavolley_classifica", "https://www.legavolley.it/classifica/")
add("Volleyball", "plusliga_table", "https://plusliga.pl/table/tour/47.html")
add("Volleyball", "plusliga_fixtures", "https://www.plusliga.pl/mecze/tour/47.html")
add("Volleyball", "cvf_extraliga", "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147")
add("Volleyball", "vbl_home", "https://www.volleyball-bundesliga.de/")
add("Volleyball", "cev_champions", "https://www.cev.eu/club/cev-champions-league/")
add("Volleyball", "volleyballworld_vnl", "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/")

# -------------------------------------------------------------- Rugby Union
add("Rugby Union", "urc_fixtures_in_full", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/")
add("Rugby Union", "urc_table", "https://stats.unitedrugby.com/match-centre/table/2026-27")
for _r in (5, 6, 7, 8, 9):
    add("Rugby Union", f"urc_r{_r}", f"https://stats.unitedrugby.com/match-centre/2026-27/{_r}")
add("Rugby Union", "top14_cal", "https://top14.lnr.fr/calendrier-et-resultats")
add("Rugby Union", "top14_classement", "https://top14.lnr.fr/classement")
add("Rugby Union", "prem_fixtures", "https://www.premiershiprugby.com/fixtures-results")
add("Rugby Union", "prem_standings", "https://www.premiershiprugby.com/standings")
add("Rugby Union", "epcr_champions", "https://www.epcrugby.com/champions-cup/fixtures")
add("Rugby Union", "world_rugby_rankings", "https://www.world.rugby/tournaments/rankings/mru")

# ------------------------------------------------------------------ Cricket
add("Cricket", "cricket_au_fixtures", "https://www.cricket.com.au/fixtures")
add("Cricket", "cricket_au_matches", "https://www.cricket.com.au/matches")
add("Cricket", "nzc_matches", "https://www.nzc.nz/matches")
add("Cricket", "ecb_fixtures", "https://www.ecb.co.uk/england/men/fixtures")
add("Cricket", "bcci_home", "https://www.bcci.tv/")
for _r in ("t20i", "odi", "test"):
    add("Cricket", f"icc_{_r}_rankings", f"https://www.icc-cricket.com/rankings/mens/team-rankings/{_r}")
add("Cricket", "icc_events", "https://www.icc-cricket.com/tournaments")
add("Cricket", "bigbash_fixtures", "https://www.bigbash.com.au/fixtures")
add("Cricket", "cricket_sa_fixtures", "https://cricket.co.za/fixtures")
add("Cricket", "pcb_schedule", "https://www.pcb.com.pk/fixtures")

# ------------------------------------------------------------------- Snooker
add("Snooker", "wst_nio", "https://www.wst.tv/tournaments/northern-ireland-open-2026/")
add("Snooker", "wst_rankings", "https://www.wst.tv/rankings/")
add(
    "Snooker",
    "wst_matches_api",
    "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=400"
    "&filter[startDateTime][gte]=2026-10-24&filter[startDateTime][lte]=2026-11-08",
)
add("Snooker", "wst_participants", "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=400")
add("Snooker", "snooker_org_cal", "https://www.snooker.org/res/index.asp?template=2")
add("Snooker", "snooker_org_2548", "https://www.snooker.org/res/index.asp?event=2548")

# --------------------------------------------------------------------- Darts
add("Darts", "pdc_oom", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit")
add("Darts", "pdc_ec", "https://www.pdc.tv/tournaments/machineseeker-european-championship")
add("Darts", "pdc_home", "https://www.pdc.tv/")
add("Darts", "pdc_calendar", "https://www.pdc.tv/tournaments")
add("Darts", "pdc_rankings", "https://www.pdc.tv/rankings")
add(
    "Darts",
    "pdc_matches_api",
    "https://matches.pdc.web.gc.wstservices.co.uk/v2/?page.size=400"
    "&filter[startDateTime][gte]=2026-10-24&filter[startDateTime][lte]=2026-11-08",
)
add("Darts", "pdc_participants", "https://participants.pdc.web.gc.wstservices.co.uk/v2/?page.size=400")

# ------------------------------------------------------------------ Baseball
add(
    "Baseball",
    "mlb_schedule",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-24&endDate=2026-11-08"
    "&hydrate=probablePitcher,linescore,team,venue",
)
add("Baseball", "mlb_standings", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason")
add("Baseball", "mlb_hitting", "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1")
add("Baseball", "mlb_pitching", "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1")
add("Baseball", "npb_schedule", "https://npb.jp/games/2026/schedule_10_detail.html")
add("Baseball", "npb_standings", "https://npb.jp/bis/2026/std_cs_pl.html")

# ------------------------------------------------------------- Gaelic Sports
add("Gaelic Sports", "gaa_fixtures", "https://www.gaa.ie/fixtures")
add("Gaelic Sports", "gaa_results", "https://www.gaa.ie/fixtures-results")
add("Gaelic Sports", "gaa_club", "https://www.gaa.ie/club/")
add("Gaelic Sports", "gaacork_fixtures", "https://gaacork.ie/fixtures")
add("Gaelic Sports", "ladies_gaelic", "https://ladiesgaelic.ie/")

# ---------------------------------------------------------------- Greyhounds
add("Greyhounds", "gbgb_racecards", "https://www.gbgb.org.uk/racecards/")
add("Greyhounds", "gbgb_fixtures", "https://www.gbgb.org.uk/fixtures/")
for _d in (date(2026, 10, 25), date(2026, 10, 26), date(2026, 10, 27)):
    for _form in (
        f"https://api.gbgb.org.uk/api/meetings?date={_d.isoformat()}",
        f"https://api.gbgb.org.uk/api/races?date={_d.isoformat()}&page=1&itemsPerPage=200",
        f"https://api.gbgb.org.uk/api/races?date={_d.isoformat()}",
    ):
        add("Greyhounds", "gbgb_" + _form.split("/api/")[1].replace("?", "_").replace("&", "_").replace("=", "-"), _form)

# ------------------------------------------------------------------- Tennis
add("Tennis", "atp_rankings", "https://www.atptour.com/en/rankings/singles?rankRange=1-100")
add("Tennis", "atp_rankings_api", "https://api.atptour.com/rankings/singles?rankRange=1-200&format=json")
add("Tennis", "atp_calendar", "https://www.atptour.com/en/tournaments")
add("Tennis", "atp_scores", "https://www.atptour.com/en/scores/current")
add("Tennis", "wta_rankings", "https://api.wtatennis.com/tennis/players/rankings/singles?page=0&pageSize=200")
add("Tennis", "wta_tournaments", "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=100")
add("Tennis", "ptl_current_op", "https://www.protennislive.com/posting/current/op.pdf")
add("Tennis", "ptl_current_mds", "https://www.protennislive.com/posting/current/mds.pdf")
add("Tennis", "ptl_current_qs", "https://www.protennislive.com/posting/current/qs.pdf")
add("Tennis", "itf_calendar", "https://www.itftennis.com/en/tournament-calendar/")

# -------------------------------------------------------------- Motor Racing
add("Motor Racing", "f1_mexico", "https://www.formula1.com/en/racing/2026/mexico")
add("Motor Racing", "f1_brazil", "https://www.formula1.com/en/racing/2026/brazil")
add("Motor Racing", "f1_racing_2026", "https://www.formula1.com/en/racing/2026.html")
add("Motor Racing", "f1_drivers", "https://www.formula1.com/en/results/2026/drivers")
add("Motor Racing", "f1_teams", "https://www.formula1.com/en/results/2026/team")
add("Motor Racing", "motogp_calendar", "https://www.motogp.com/en/calendar/2026")
add("Motor Racing", "motogp_standings", "https://www.motogp.com/en/standings/2026")
add("Motor Racing", "fia_f2", "https://www.fiaformula2.com/")
add("Motor Racing", "fia_f3", "https://www.fiaformula3.com/")
add("Motor Racing", "indycar_schedule", "https://www.indycar.com/Schedule")
add("Motor Racing", "nascar_schedule", "https://www.nascar.com/schedule/")

# ------------------------------------------------------------------ Handball
add("Handball", "ehfcl_m_matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/")
add("Handball", "ehfcl_m_standings", "https://ehfcl.eurohandball.com/men/2026-27/standings/")
add("Handball", "ehfcl_w_matches", "https://ehfcl.eurohandball.com/women/2026-27/matches/")
add("Handball", "ehfel_m_matches", "https://ehfel.eurohandball.com/men/2026-27/matches/")
add("Handball", "hbl_spielplan", "https://www.dkb-handball-bundesliga.de/spielplan")
add("Handball", "hbl_tabelle", "https://www.dkb-handball-bundesliga.de/tabelle")
add("Handball", "dk_herreligaen", "https://tophaandbold.dk/stillinger/herreligaen")
add("Handball", "dk_program", "https://tophaandbold.dk/kampprogram")
add("Handball", "asobal_calendario", "https://asobal.es/calendario/")
add("Handball", "asobal_clasificacion", "https://asobal.es/clasificacion/")
add("Handball", "handbollsligan", "https://handbollsligan.se/")
add("Handball", "lnh_calendrier", "https://www.lnh.fr/calendrier")

# ---------------------------------------------------------------- Ice Hockey
add("Ice Hockey", "nhl_standings", "https://api-web.nhle.com/v1/standings/now")
add("Ice Hockey", "nhl_skaters", "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals,points&limit=25")
add("Ice Hockey", "nhl_goalies", "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=savePctg,goalsAgainstAverage&limit=25")
for _d in days():
    if date(2026, 10, 24) <= _d <= date(2026, 11, 9):
        add("Ice Hockey", f"nhl_sched_{_d.isoformat()}", f"https://api-web.nhle.com/v1/schedule/{_d.isoformat()}")
add("Ice Hockey", "shl_overview", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961")
add("Ice Hockey", "shl_standings", "https://stats.swehockey.se/ScheduleAndResults/Standings/20961")
add("Ice Hockey", "liiga_games", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027")
add("Ice Hockey", "liiga_standings", "https://liiga.fi/api/v2/standings/?season=2027")
add("Ice Hockey", "khl_schedule", "https://www.khl.ru/calendar/")

# ---------------------------------------------------------------- Basketball
add("Basketball", "el_games", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games")
add("Basketball", "eurocup_games", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games")
add("Basketball", "el_standings", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings?phase=RS")
add("Basketball", "acb_calendario", "https://www.acb.com/calendario/")
add("Basketball", "acb_clasificacion", "https://www.acb.com/clasificacion/")
add("Basketball", "lega_basket", "https://www.legabasket.it/")
add("Basketball", "nba_cdn_schedule", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json")
add("Basketball", "nba_cdn_scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json")

# -------------------------------------------------------------- Rugby League
add("Rugby League", "rlwc_draws", "https://www.rlwc2026.com/draws-and-pools")
add("Rugby League", "rlwc_fixtures", "https://www.rlwc2026.com/fixtures")
add("Rugby League", "rlwc_results", "https://www.rlwc2026.com/results")
add("Rugby League", "rlwc_api_fixtures", "https://www.rlwc2026.com/api/fixtures")
add("Rugby League", "nrl_draw", "https://www.nrl.com/draw/")
add("Rugby League", "intrl_rankings", "https://www.intrl.sport/rankings")

if __name__ == "__main__":
    OUT.write_text(json.dumps(T, indent=1) + "\n")
    print(f"{len(T)} targets -> {OUT}")

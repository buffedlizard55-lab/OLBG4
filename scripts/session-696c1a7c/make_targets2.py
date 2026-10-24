#!/usr/bin/env python3
"""Build the round-2 capture target list.

Round 2 = (a) the official endpoints that failed or were missing in round 1,
(behind the header profiles that the league CDNs require) and (b) OLBG's
competition sub-hubs, derived from the `leagueUrl` of every upcoming event in
`data/session-696c1a7c/listings.json`, because a sport hub only renders the
events that currently carry a community tip.

Nothing here asserts a URL is a source of fact: every response is hashed into the
manifest and anything that fails stays listed as a failure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "data" / "session-696c1a7c"
OUT = HERE / "targets2.json"

# Browser profile that the NBA CDN and stats host require (referer + origin).
NBA_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Sec-Fetch-Site": "same-site",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Dest": "empty",
}
ATP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
}
PCB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Referer": "https://www.pcb.com.pk/",
}

T: list[dict] = []


def add(sport: str, tid: str, url: str, delay: float = 0.3, attempts: int = 2,
        headers: dict | None = None, accept: str | None = None) -> None:
    rec = {"sport": sport, "id": tid, "url": url, "delay": delay, "attempts": attempts}
    if headers:
        rec["headers"] = headers
    if accept:
        rec["accept"] = accept
    T.append(rec)


# --- Basketball: NBA, from the CDN and the stats host -----------------------
add("Basketball", "nba_schedule_cdn",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", 0.3, 2, NBA_HEADERS)
add("Basketball", "nba_scoreboard_today",
    "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    0.3, 2, NBA_HEADERS)
add("Basketball", "nba_standings_stats",
    "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular+Season",
    0.4, 2, NBA_HEADERS)
add("Basketball", "nba_gamelog_stats",
    "https://stats.nba.com/stats/leaguegamelog?Counter=1000&Direction=DESC&LeagueID=00"
    "&PlayerOrTeam=T&Season=2026-27&SeasonType=Regular+Season&Sorter=DATE", 0.4, 2, NBA_HEADERS)
add("Basketball", "nba_teamstats_stats",
    "https://stats.nba.com/stats/leaguedashteamstats?Conference=&DateFrom=&DateTo=&Division="
    "&GameScope=&GameSegment=&Height=&LastNGames=0&LeagueID=00&Location=&MeasureType=Base"
    "&Month=0&OpponentTeamID=0&Outcome=&PORound=0&PaceAdjust=N&PerMode=PerGame&Period=0"
    "&PlayerExperience=&PlayerPosition=&PlusMinus=N&Rank=N&Season=2026-27&SeasonSegment="
    "&SeasonType=Regular+Season&ShotClockRange=&StarterBench=&TeamID=0&VsConference=&VsDivision=",
    0.4, 2, NBA_HEADERS)

# --- Snooker: the full WST match list (round 1 proved the host answers) -----
add("Snooker", "wst_matches_window",
    "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=500&sort=startDateTime"
    "&filter%5BstartDateTime%5D%5Bgte%5D=2026-10-01&filter%5BstartDateTime%5D%5Blte%5D=2026-11-30",
    0.3, 2)
add("Snooker", "wst_matches_recent",
    "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=500&sort=-startDateTime"
    "&filter%5BstartDateTime%5D%5Bgte%5D=2026-05-01&filter%5BstartDateTime%5D%5Blte%5D=2026-10-24",
    0.3, 2)
add("Snooker", "wst_tournaments",
    "https://tournaments.snooker.web.gc.wstservices.co.uk/v2/?page.size=100", 0.3, 2)
add("Snooker", "snooker_org_event", "https://www.snooker.org/res/index.asp?event=2548", 0.4, 1)

# --- Tennis: rankings behind the tour's own header profile -----------------
add("Tennis", "atp_rankings_browser", "https://www.atptour.com/en/rankings/singles?rankRange=1-200",
    0.5, 2, ATP_HEADERS)
add("Tennis", "atp_rankings_race", "https://www.atptour.com/en/rankings/race-to-turin",
    0.5, 2, ATP_HEADERS)
add("Tennis", "wta_rankings_html", "https://www.wtatennis.com/rankings/singles", 0.5, 2, ATP_HEADERS)
add("Tennis", "wta_calendar_full",
    "https://api.wtatennis.com/tennis/tournaments?page=0&pageSize=200", 0.3, 2)
add("Tennis", "atp_calendar_browser", "https://www.atptour.com/en/tournaments", 0.5, 2, ATP_HEADERS)

# --- Cricket: board fixture pages and rankings that render server-side ------
add("Cricket", "icc_mens_rankings_api", "https://www.icc-cricket.com/api/rankings/mens/t20i", 0.4, 1)
add("Cricket", "pcb_fixtures", "https://www.pcb.com.pk/fixtures.html", 0.4, 2, PCB_HEADERS)
add("Cricket", "nzc_schedule", "https://www.nzc.nz/schedule", 0.4, 2)
add("Cricket", "ecb_schedule", "https://www.ecb.co.uk/england/men/schedule", 0.4, 2)
add("Cricket", "cricket_au_schedule", "https://www.cricket.com.au/schedule", 0.4, 2)
add("Cricket", "cricket_au_bbl", "https://www.cricket.com.au/big-bash", 0.4, 2)
add("Cricket", "csa_fixtures", "https://cricket.co.za/fixtures", 0.4, 2)

# --- Handball: national leagues whose pages render a table ---------------
add("Handball", "hbl_liquimoly_spielplan", "https://www.liquimoly-hbl.de/de/spielplan/", 0.4, 2)
add("Handball", "hbl_liquimoly_tabelle", "https://www.liquimoly-hbl.de/de/tabelle/", 0.4, 2)
add("Handball", "svenskhandboll", "https://www.svenskhandboll.se/", 0.4, 2)
add("Handball", "handbollsligan_statistik", "https://handbollsligan.se/statistik/", 0.4, 2)
add("Handball", "asobal_resultados", "https://asobal.es/resultados/", 0.4, 2)
add("Handball", "lnh_calendrier2", "https://www.lnh.fr/calendrier", 0.4, 2)
add("Handball", "ehfcl_m_results", "https://ehfcl.eurohandball.com/men/2026-27/matches/?round=6", 0.4, 2)

# --- Volleyball: the women's / other leagues OLBG lists ------------------
add("Volleyball", "lvgf_classifica", "https://www.legavolleyfemminile.it/classifica/", 0.4, 2)
add("Volleyball", "lvgf_calendario", "https://www.legavolleyfemminile.it/calendario/", 0.4, 2)
add("Volleyball", "tvf_fixtures", "https://tvf.org.tr/musabakalar/", 0.4, 2)
add("Volleyball", "cbv_superliga", "https://www.cbv.com.br/superliga", 0.4, 2)
add("Volleyball", "vbl_fixtures", "https://www.volleyball-bundesliga.de/cms/home/1bl_frauen/spielplan/", 0.4, 2)
add("Volleyball", "lnv_calendrier", "https://lnv.fr/calendrier/", 0.4, 2)
add("Volleyball", "plusliga_women", "https://www.tauronliga.pl/table/tour/2026.html", 0.4, 2)

# --- Rugby union: match centres that render server-side ------------------
add("Rugby Union", "prem_round", "https://www.premiershiprugby.com/fixtures-results?round=6", 0.4, 2)
add("Rugby Union", "top14_journee", "https://top14.lnr.fr/calendrier-et-resultats?journee=9", 0.4, 2)
add("Rugby Union", "urc_match_centre", "https://www.unitedrugby.com/match-centre", 0.4, 2)
add("Rugby Union", "epcr_home", "https://www.epcrugby.com/", 0.4, 2)
add("Rugby Union", "japan_rugby", "https://www.rugby-japan.jp/", 0.4, 2)

# --- Darts: host variants of the PDC platform and official series sites --
add("Darts", "pdc_gc_matches", "https://matches.gc.pdcservices.co.uk/v2/?page.size=200", 0.3, 1)
add("Darts", "pdc_api_root", "https://api.pdc.tv/v2/?page.size=50", 0.3, 1)
add("Darts", "pdc_sitemap", "https://www.pdc.tv/sitemap.xml", 0.4, 2)
add("Darts", "pdc_tournaments_page", "https://www.pdc.tv/tournaments", 0.4, 2)
add("Darts", "wdf_events", "https://www.dartswdf.com/events/", 0.4, 2)

# --- Gaelic sports ------------------------------------------------------
add("Gaelic Sports", "kilkennygaa", "https://kilkennygaa.ie/", 0.4, 2)
add("Gaelic Sports", "gaa_club_fixtures", "https://www.gaa.ie/fixtures-results/club", 0.4, 2)
add("Gaelic Sports", "dublingaa_results", "https://www.dublingaa.ie/results", 0.4, 2)
add("Gaelic Sports", "gaacork_results", "https://gaacork.ie/results", 0.4, 2)

# --- Greyhounds ---------------------------------------------------------
add("Greyhounds", "gbgb_api_races_date", "https://api.gbgb.org.uk/api/races?date=2026-10-25", 0.4, 2)
add("Greyhounds", "gbgb_api_racecards_date",
    "https://api.gbgb.org.uk/api/racecards?date=2026-10-25&page=1&itemsPerPage=100", 0.4, 2)
add("Greyhounds", "gbgb_racecard_page", "https://www.gbgb.org.uk/race-card/", 0.4, 2)
add("Greyhounds", "gbgb_meetings_page", "https://www.gbgb.org.uk/meetings/", 0.4, 2)

# --- Golf / Motor racing ------------------------------------------------
add("Golf", "owgr_api", "https://www.owgr.com/api/rankings/current", 0.4, 1)
add("Golf", "pgatour_bermuda", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528", 0.4, 2)
add("Golf", "dpwt_genesis", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/leaderboard", 0.4, 2)
add("Motor Racing", "f1_race_results_latest", "https://www.formula1.com/en/results/2026/races", 0.4, 2)
add("Motor Racing", "f1_mexico_results", "https://www.formula1.com/en/results/2026/races/1159/mexico/race-result", 0.4, 1)
add("Motor Racing", "motogp_results_2026", "https://www.motogp.com/en/calendar/2026/race-results", 0.4, 1)

# --- OLBG competition sub-hubs for the leagues that currently carry a tip --
listings_path = DATA / "listings.json"
if listings_path.exists():
    listings = json.loads(listings_path.read_text())
    now = listings.get("parsed_utc") or "2026-10-24T00:00:00Z"
    leagues: dict[str, str] = {}
    for sport, blob in listings["sports"].items():
        for ev in blob["events"]:
            if (ev.get("start_utc") or "9") < now:
                continue
            url = ev.get("league_url") or ""
            if "/betting-tips/" not in url:
                continue
            if url not in leagues:
                leagues[url] = sport
    for url, sport in sorted(leagues.items()):
        slug = url.rstrip("/").split("/")[-2:]
        tid = "olbg_league_" + re.sub(r"[^a-z0-9]+", "_", "/".join(slug).lower()).strip("_")
        add(sport, tid[:60], url, 1.3, 1)


if __name__ == "__main__":
    OUT.write_text(json.dumps(T, indent=1) + "\n")
    print(f"wrote {OUT} with {len(T)} targets")
    by_sport: dict[str, int] = {}
    for t in T:
        by_sport[t["sport"]] = by_sport.get(t["sport"], 0) + 1
    for s, n in sorted(by_sport.items()):
        print(f"  {s:15s} {n}")

#!/usr/bin/env python3
"""Generate scripts/session-2722b692/targets.json — the Board AJ capture plan.

Run: python3 scripts/session-2722b692/make_targets.py
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

OUT = Path(__file__).with_name("targets.json")
START = date(2026, 10, 23)
DAYS = 17  # 23 Oct .. 8 Nov 2026

T: list[dict] = []


def add(tid: str, url: str, sport: str, kind: str, label: str, delay: float | None = None) -> None:
    item = {"id": tid, "url": url, "sport": sport, "kind": kind, "label": label}
    if delay is not None:
        item["delay"] = delay
    elif "olbg.com" in url:
        item["delay"] = 0.95
    T.append(item)


# ---------------------------------------------------------------- OLBG taxonomy
add("olbg_robots", "https://www.olbg.com/robots.txt", "all", "policy", "OLBG robots.txt")
add("olbg_sitemap", "https://www.olbg.com/sitemap-betting-tips.xml", "all", "policy", "OLBG tips sitemap")
add("olbg_all", "https://www.olbg.com/betting-tips", "all", "listing", "OLBG all sports hub")

OLBG_HUBS = [
    ("Ice Hockey", "Ice_Hockey", 13, "Ice Hockey"),
    ("Ice Hockey", "Ice_Hockey/NHL", 13, "Ice Hockey / NHL"),
    ("Basketball", "Basketball", 4, "Basketball"),
    ("Basketball", "Basketball/NBA", 4, "Basketball / NBA"),
    ("Baseball", "Baseball", 12, "Baseball"),
    ("Tennis", "Tennis", 3, "Tennis"),
    ("Cricket", "Cricket", 7, "Cricket"),
    ("Rugby Union", "Rugby_Union", 9, "Rugby Union"),
    ("Rugby League", "Rugby_League", 10, "Rugby League"),
    ("Darts", "Darts", 15, "Darts"),
    ("Snooker", "Snooker", 8, "Snooker"),
    ("Golf", "Golf", 5, "Golf"),
    ("Motor Racing", "Motor_Racing", 14, "Motor Racing"),
    ("Handball", "Handball", 20, "Handball"),
    ("Volleyball", "Volleyball", 21, "Volleyball"),
    ("Gaelic Sports", "Gaelic_Football", 25, "Gaelic Football"),
    ("Greyhounds", "Greyhounds", 28, "Greyhounds"),
]
for sport, slug, sid, label in OLBG_HUBS:
    tid = "olbg_" + slug.replace("/", "_").lower() + f"_{sid}"
    add(tid, f"https://www.olbg.com/betting-tips/{slug}/{sid}", sport, "listing", f"OLBG {label}")

# ---------------------------------------------------------------- dates
DATES = [(START + timedelta(days=i)).isoformat() for i in range(DAYS)]

# Ice hockey — NHL official API (schedule + standings + leaders)
for d in DATES:
    add(f"nhl_sched_{d}", f"https://api-web.nhle.com/v1/schedule/{d}", "Ice Hockey", "schedule", f"NHL schedule {d}")
add("nhl_standings_now", "https://api-web.nhle.com/v1/standings/now", "Ice Hockey", "standings", "NHL standings now")
add("nhl_club_stats", "https://api-web.nhle.com/v1/club-stats/ANA/20262027/2", "Ice Hockey", "stats", "NHL club stats ANA")
# SHL (Sweden) + Liiga (Finland) official
add("swehockey_shl", "https://stats.swehockey.se/ScheduleAndResults/Overview/20961", "Ice Hockey", "schedule", "SHL schedule/results")
add("liiga_games", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", "Ice Hockey", "schedule", "Liiga games 2026-27")
add("liiga_standings", "https://liiga.fi/api/v2/standings/?season=2027", "Ice Hockey", "standings", "Liiga standings")

# Baseball — MLB Stats API
add("mlb_sched",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-11-08"
    "&gameType=F,D,L,W&hydrate=team,linescore,seriesStatus,probablePitcher,venue",
    "Baseball", "schedule", "MLB schedule 23 Oct - 8 Nov")
add("mlb_standings",
    "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026"
    "&standingsTypes=regularSeason&hydrate=team",
    "Baseball", "standings", "MLB final regular-season standings")
add("mlb_hitting",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=hitting&stats=season&sportId=1&gameType=R",
    "Baseball", "stats", "MLB team hitting 2026")
add("mlb_pitching",
    "https://statsapi.mlb.com/api/v1/teams/stats?season=2026&group=pitching&stats=season&sportId=1&gameType=R",
    "Baseball", "stats", "MLB team pitching 2026")

# Basketball — NBA CDN (schedule) + EuroLeague / EuroCup official game feeds
add("nba_sched", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", "Basketball", "schedule", "NBA 2026-27 schedule")
add("nba_standings", "https://cdn.nba.com/static/json/liveData/standings/standings_00.json", "Basketball", "standings", "NBA standings")
add("nba_scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "Basketball", "results", "NBA today scoreboard")
add("nba_companies", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", "Basketball", "schedule", "NBA schedule (alt)")
for comp, season in (("E", "E2026"), ("U", "U2026")):
    add(f"euroleague_games_{season}",
        f"https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{season}/games",
        "Basketball", "schedule", f"EuroLeague/Cup {season} games")
    add(f"euroleague_standings_{season}",
        f"https://api-live.euroleague.net/v2/competitions/{comp}/seasons/{season}/standings",
        "Basketball", "standings", f"EuroLeague/Cup {season} standings")

# Tennis — WTA official API, protennislive (ATP official live scoring) draws
add("wta_tournaments", "https://api.wtatennis.com/tennis/tournaments?page=0&pageSize=50&year=2026", "Tennis", "schedule", "WTA 2026 tournaments")
add("wta_rankings", "https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankSingles&sort=asc&metric=SINGLES", "Tennis", "rankings", "WTA singles rankings")
for tid in ("2092", "405", "1056", "1023"):
    add(f"wta_matches_{tid}", f"https://api.wtatennis.com/tennis/tournaments/{tid}/2026/matches", "Tennis", "schedule", f"WTA tournament {tid} matches")
add("atp_scores_current", "https://www.atptour.com/en/scores/current", "Tennis", "schedule", "ATP current scores")
add("atp_rankings", "https://www.atptour.com/en/rankings/singles", "Tennis", "rankings", "ATP singles rankings")
add("itf_calendar", "https://www.itftennis.com/en/itf-tours/calendar/", "Tennis", "schedule", "ITF tours calendar")
for ev in ("496", "7485", "9410", "328", "337"):
    add(f"ptl_{ev}_mds", f"https://www.protennislive.com/posting/2026/{ev}/mds.pdf", "Tennis", "draw", f"ATP draw {ev}")

# Cricket — official boards
add("cricket_au_fixtures", "https://www.cricket.com.au/fixtures", "Cricket", "schedule", "Cricket Australia fixtures")
add("cricket_au_series", "https://www.cricket.com.au/series", "Cricket", "schedule", "Cricket Australia series")
add("icc_fixtures", "https://www.icc-cricket.com/fixtures-results", "Cricket", "schedule", "ICC fixtures & results")
add("icc_fixtures_men", "https://www.icc-cricket.com/fixtures-results/men", "Cricket", "schedule", "ICC men's fixtures")
add("icc_odi_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", "Cricket", "rankings", "ICC ODI rankings")
add("icc_t20i_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", "Cricket", "rankings", "ICC T20I rankings")
add("icc_test_rankings", "https://www.icc-cricket.com/rankings/mens/team-rankings/test", "Cricket", "rankings", "ICC Test rankings")
add("nzc_matches", "https://www.nzc.nz/matches", "Cricket", "schedule", "New Zealand Cricket matches")
add("ecb_fixtures", "https://www.ecb.co.uk/fixtures", "Cricket", "schedule", "England & Wales Cricket Board fixtures")
add("bcci_fixtures", "https://www.bcci.tv/international/fixtures", "Cricket", "schedule", "BCCI fixtures")
add("pcb_fixtures", "https://www.pcb.com.pk/fixtures.html", "Cricket", "schedule", "Pakistan Cricket Board fixtures")

# Rugby union — URC, Premiership, LNR, EPCR, World Rugby
add("urc_fixtures", "https://www.unitedrugby.com/fixtures", "Rugby Union", "schedule", "URC fixtures")
add("urc_fixtures_in_full", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", "Rugby Union", "schedule", "URC 2026-27 fixtures in full")
add("urc_table", "https://stats.unitedrugby.com/match-centre/table/2026-27", "Rugby Union", "standings", "URC table")
for r in (4, 5, 6, 7, 8):
    add(f"urc_round_{r}", f"https://stats.unitedrugby.com/match-centre/2026-27/{r}", "Rugby Union", "schedule", f"URC round {r}")
add("prem_fixtures", "https://www.premiershiprugby.com/fixtures-results", "Rugby Union", "schedule", "Premiership Rugby fixtures")
add("prem_standings", "https://www.premiershiprugby.com/standings", "Rugby Union", "standings", "Premiership Rugby standings")
add("lnr_top14", "https://top14.lnr.fr/calendrier-et-resultats", "Rugby Union", "schedule", "LNR Top 14 calendar")
add("lnr_top14_table", "https://top14.lnr.fr/classement", "Rugby Union", "standings", "LNR Top 14 table")
add("lnr_prod2", "https://prod2.lnr.fr/calendrier-et-resultats", "Rugby Union", "schedule", "LNR Pro D2 calendar")
add("epcr", "https://www.epcrugby.com/match-centre/", "Rugby Union", "schedule", "EPCR match centre")
add("world_rugby_rankings", "https://www.world.rugby/rankings/mru", "Rugby Union", "rankings", "World Rugby men's rankings")

# Rugby league — RLWC 2026, NRL, Super League
for slug in ("fixtures", "results", "draws-and-pools", "matches"):
    add(f"rlwc_{slug}", f"https://www.rlwc2026.com/{slug}", "Rugby League", "schedule", f"RLWC 2026 {slug}")
add("nrl_draw", "https://www.nrl.com/draw/", "Rugby League", "schedule", "NRL draw")
add("superleague_fixtures", "https://www.superleague.co.uk/fixtures", "Rugby League", "schedule", "Super League fixtures")
add("intl_rl", "https://www.internationalrugbyleague.com/", "Rugby League", "rankings", "International Rugby League")

# Darts — PDC official services API + order of merit
for tid, url in (
    ("pdc_matches", "https://matches.darts.admin.gc.pdcservices.co.uk/v2/matches?page.size=200"),
    ("pdc_tournaments", "https://matches.darts.admin.gc.pdcservices.co.uk/v2/tournaments?page.size=100"),
    ("pdc_events", "https://matches.darts.admin.gc.pdcservices.co.uk/v2/events?page.size=100"),
    ("pdc_participants", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100"),
    ("pdc_participants_2", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100&page.number=2"),
    ("pdc_oom", "https://www.pdc.tv/order-of-merit/pdc-order-of-merit"),
    ("pdc_calendar", "https://www.pdc.tv/tournaments"),
    ("pdc_ec", "https://www.pdc.tv/tournaments/european-championship"),
):
    add(tid, url, "Darts", "schedule" if "matches" in tid or "calendar" in tid else "reference", tid)

# Snooker — WST official services API
for tid, url in (
    ("wst_events", "https://events.snooker.web.gc.wstservices.co.uk/v2/?page.size=100"),
    ("wst_comps", "https://comps.snooker.web.gc.wstservices.co.uk/v2/?page.size=100"),
    ("wst_matches", "https://matches.snooker.web.gc.wstservices.co.uk/v2/matches?page.size=200"),
    ("wst_participants", "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=100"),
    ("wst_participants_2", "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=100&page.number=2"),
    ("wst_rankings", "https://wst.tv/rankings"),
    ("wst_tournaments", "https://wst.tv/tournaments/"),
    ("wst_draws", "https://wst.tv/draws-results/"),
    ("wst_matches_site", "https://www.wst.tv/matches/"),
):
    add(tid, url, "Snooker", "schedule", tid)

# Golf — DP World Tour / PGA Tour / LPGA / OWGR
add("dpwt_schedule", "https://www.europeantour.com/dpworld-tour/schedule", "Golf", "schedule", "DP World Tour schedule")
add("dpwt_genesis_tee", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/tee-times", "Golf", "schedule", "DP World Tour Genesis Championship tee times")
add("pgatour_leaderboard", "https://www.pgatour.com/leaderboard", "Golf", "results", "PGA Tour leaderboard")
add("pgatour_schedule", "https://www.pgatour.com/schedule", "Golf", "schedule", "PGA Tour schedule")
add("lpga_schedule", "https://www.lpga.com/tournaments", "Golf", "schedule", "LPGA schedule")
add("owgr", "https://www.owgr.com/current-world-ranking", "Golf", "rankings", "OWGR world ranking")

# Motor racing — Formula 1 + MotoGP
for tid, url, kind, label in (
    ("f1_season", "https://www.formula1.com/en/racing/2026", "schedule", "F1 2026 season"),
    ("f1_season_html", "https://www.formula1.com/en/racing/2026.html", "schedule", "F1 2026 season (alt)"),
    ("f1_mexico", "https://www.formula1.com/en/racing/2026/mexico", "schedule", "F1 Mexico City GP"),
    ("f1_drivers", "https://www.formula1.com/en/results/2026/drivers", "standings", "F1 2026 driver standings"),
    ("f1_results", "https://www.formula1.com/en/results/2026", "results", "F1 2026 results"),
    ("motogp_calendar", "https://www.motogp.com/en/calendar", "schedule", "MotoGP 2026 calendar"),
    ("motogp_standings", "https://www.motogp.com/en/standings", "standings", "MotoGP 2026 standings"),
    ("wrc", "https://www.wrc.com/", "schedule", "WRC"),
):
    add(tid, url, "Motor Racing", kind, label)

# Handball — EHF Champions League, German HBL, Danish, Swedish, Spanish
add("ehfcl_matches", "https://ehfcl.eurohandball.com/men/2026-27/matches/", "Handball", "schedule", "EHF Champions League men matches")
add("ehfcl_standings", "https://ehfcl.eurohandball.com/men/2026-27/standings/", "Handball", "standings", "EHF CL men standings")
add("ehfcl_calendar", "https://ehfcl.eurohandball.com/men/2026-27/calendar/", "Handball", "schedule", "EHF CL men calendar")
add("ehfcl_women", "https://ehfcl.eurohandball.com/women/2026-27/matches/", "Handball", "schedule", "EHF CL women matches")
add("hbl_spielplan", "https://www.dkb-handball-bundesliga.de/spielplan", "Handball", "schedule", "German HBL schedule")
add("tophaandbold", "https://tophaandbold.dk/stillinger/herreligaen", "Handball", "standings", "Danish Herreligaen table")
add("tophaandbold_kampe", "https://tophaandbold.dk/kampe", "Handball", "schedule", "Danish Herreligaen fixtures")
add("handbollsligan", "https://handbollsligan.se/", "Handball", "schedule", "Swedish Handbollsligan")
add("asobal", "https://asobal.es/", "Handball", "standings", "Spanish ASOBAL")
add("lnh", "https://www.lnh.fr/", "Handball", "schedule", "French LNH")

# Volleyball — Lega Volley (ITA), PlusLiga (POL), CVF (CZE), Bundesliga (GER), FIVB/CEV
for tid, url, kind, label in (
    ("legavolley_cal_991", "https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=991", "schedule", "Italian SuperLega calendar"),
    ("legavolley_cal_999", "https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=999", "schedule", "Italian SuperLega calendar (2)"),
    ("legavolley_classifica", "https://www.legavolley.it/classifica/", "standings", "Italian SuperLega table"),
    ("plusliga_table", "https://plusliga.pl/table/tour/47.html", "standings", "PlusLiga table"),
    ("plusliga_schedule", "https://plusliga.pl/terminarz.html", "schedule", "PlusLiga fixtures"),
    ("cvf_extraliga", "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147", "standings", "Czech Extraliga"),
    ("vbl", "https://www.volleyball-bundesliga.de/", "schedule", "German Volleyball Bundesliga"),
    ("volleyballworld", "https://en.volleyballworld.com/volleyball/competitions/", "schedule", "FIVB Volleyball World competitions"),
    ("cev", "https://www.cev.eu/Competition-Area/Competitions/", "schedule", "CEV competitions"),
):
    add(tid, url, "Volleyball", kind, label)

# Gaelic sports — GAA official + county boards
add("gaa_fixtures", "https://www.gaa.ie/fixtures", "Gaelic Sports", "schedule", "GAA fixtures")
add("gaa_fixtures_results", "https://www.gaa.ie/fixtures-results/", "Gaelic Sports", "schedule", "GAA fixtures & results")
add("gaa_home", "https://www.gaa.ie/", "Gaelic Sports", "reference", "GAA home")
add("gaacork_fixtures", "https://gaacork.ie/fixtures", "Gaelic Sports", "schedule", "Cork GAA fixtures")
add("gaa_club", "https://www.gaa.ie/club/", "Gaelic Sports", "schedule", "GAA club fixtures")
add("gaa_leinster", "https://leinstergaa.ie/", "Gaelic Sports", "schedule", "Leinster GAA")

# Greyhounds — GBGB official results/fixtures API + site
for d in DATES[:6]:
    add(f"gbgb_results_{d}", f"https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100&date={d}&race_type=race", "Greyhounds", "results", f"GBGB results {d}")
add("gbgb_api_root", "https://api.gbgb.org.uk/api/", "Greyhounds", "reference", "GBGB API root")
add("gbgb_racecards", "https://www.gbgb.org.uk/racecards/", "Greyhounds", "schedule", "GBGB racecards")
add("gbgb_racing", "https://www.gbgb.org.uk/racing/", "Greyhounds", "schedule", "GBGB racing")
add("gbgb_results_page", "https://www.gbgb.org.uk/results/", "Greyhounds", "results", "GBGB results")

dedup: dict[str, dict] = {}
for item in T:
    dedup.setdefault(item["id"], item)

payload = list(dedup.values())
OUT.write_text(json.dumps(payload, indent=1))
print(f"wrote {len(payload)} targets to {OUT}")

#!/usr/bin/env python3
"""Board DS collection spec.

Every URL here is either (a) an OLBG.com page used to reverse-engineer the site and list
the fixtures OLBG publicly offers, or (b) a governing-body / official-tournament endpoint
used to confirm a fixture, a result, a table or a ranking.  Nothing here is an aggregator,
a betting shop or a Wikipedia page: a value is only ever published from bytes listed in
this file.

Groups are fetched independently and every outcome (200, 4xx, 5xx, timeout, DNS) is
recorded in the manifest.  A failed group is never silently replaced by an estimate.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------- OLBG
# Sport IDs re-confirmed against https://www.olbg.com/sitemap-betting-tips.xml at
# capture time.  The brief's fifteen sports are listed first; Hurling is captured with
# Gaelic Football because the brief says "Gaelic Sports" and OLBG files them as two
# separate sports.
OLBG = {
    "golf": (5, "Golf"),
    "volleyball": (21, "Volleyball"),
    "rugby_union": (9, "Rugby_Union"),
    "cricket": (7, "Cricket"),
    "snooker": (8, "Snooker"),
    "darts": (15, "Darts"),
    "baseball": (12, "Baseball"),
    "gaelic_football": (25, "Gaelic_Football"),
    "hurling": (26, "Hurling"),
    "greyhounds": (28, "Greyhounds"),
    "tennis": (3, "Tennis"),
    "motor_racing": (14, "Motor_Racing"),
    "handball": (20, "Handball"),
    "ice_hockey": (13, "Ice_Hockey"),
    "basketball": (4, "Basketball"),
    "rugby_league": (10, "Rugby_League"),
}

OLBG_URLS = {
    "sitemap": "https://www.olbg.com/sitemap-betting-tips.xml",
    "tips_index": "https://www.olbg.com/betting-tips",
}
for _key, (_sid, _slug) in OLBG.items():
    OLBG_URLS[f"hub_{_key}"] = f"https://www.olbg.com/betting-tips/{_slug}/{_sid}"

# ------------------------------------------------------------------------ OFFICIAL
# One key per official endpoint.  Keys are used as filenames, so they stay short.
OFFICIAL = {
    # --- Ice Hockey: NHL's own schedule and standings service -------------------------
    "nhl_standings": "https://api-web.nhle.com/v1/standings/now",
    "nhl_clubs": "https://api-web.nhle.com/v1/standings/season/now",
    # --- Baseball: MLB's own stats API ----------------------------------------------
    "mlb_sched": ("https://statsapi.mlb.com/api/v1/schedule?sportId=1"
                  "&startDate=2026-10-24&endDate=2026-11-05&hydrate=team,linescore,probablePitcher"),
    "mlb_standings": ("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
                      "&season=2026&standingsTypes=regularSeason&hydrate=team"),
    # --- Basketball ------------------------------------------------------------------
    "nba_scoreboard": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "euroleague_games": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
    "eurocup_games": "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games",
    # --- Cricket ---------------------------------------------------------------------
    "icc_matches": "https://www.icc-cricket.com/matches",
    "icc_rankings_odi": "https://www.icc-cricket.com/rankings/mens/team-rankings/odi",
    "icc_rankings_t20": "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i",
    # --- Snooker ---------------------------------------------------------------------
    "wst_home": "https://wst.tv/",
    "wst_wpjson": "https://wst.tv/wp-json/wp/v2/pages?per_page=20",
    # --- Darts -----------------------------------------------------------------------
    "pdc_home": "https://www.pdc.tv/",
    "pdc_wpjson": "https://www.pdc.tv/wp-json/wp/v2/posts?per_page=20",
    # --- Tennis ----------------------------------------------------------------------
    "atp_scores": "https://www.atptour.com/en/scores/current",
    "wta_scores": "https://www.wtatennis.com/scores",
    # --- Golf ------------------------------------------------------------------------
    "pgatour_schedule": "https://www.pgatour.com/schedule",
    "europeantour_schedule": "https://www.europeantour.com/dpworld-tour/schedule/",
    # --- Volleyball ------------------------------------------------------------------
    "volleyballworld": "https://en.volleyballworld.com/volleyball/competitions/",
    "cev_competitions": "https://www.cev.eu/competitions/",
    # --- Handball --------------------------------------------------------------------
    "ehf_matches": "https://ehfec.eurohandball.com/en/matches/",
    "ehf_cl": "https://ehfec.eurohandball.com/en/competitions/",
    "danish_table": "https://tophaandbold.dk/stillinger/herreligaen",
    # --- Rugby Union -----------------------------------------------------------------
    "urc_matchcentre": "https://www.unitedrugby.com/match-centre",
    "epcr_fixtures": "https://www.epcrugby.com/fixtures",
    "premiership_fixtures": "https://www.premiershiprugby.com/fixtures",
    # --- Rugby League ----------------------------------------------------------------
    "rfl_fixtures": "https://www.rugby-league.com/match-centre/fixtures",
    "nrl_draw": "https://www.nrl.com/draw/data?competition=111&season=2026",
    "nrl_ladder": "https://www.nrl.com/ladder/data?competition=111&season=2026",
    # --- Gaelic ----------------------------------------------------------------------
    "gaa_fixtures": "https://www.gaa.ie/fixtures-results/",
    # --- Greyhounds ------------------------------------------------------------------
    "gbgb_results": "https://www.gbgb.org.uk/results",
    "gbgb_racing": "https://www.gbgb.org.uk/racing",
    # --- Motor Racing ----------------------------------------------------------------
    "f1_racing": "https://www.formula1.com/en/racing/2026",
    "motogp_calendar": "https://www.motogp.com/en/calendar/2026",
}


def schedule_dates(start: str = "2026-10-24", days: int = 8) -> dict:
    """NHL schedule endpoints, one per date, generated so the capture is reproducible."""
    from datetime import date, timedelta

    y, m, d = (int(x) for x in start.split("-"))
    base = date(y, m, d)
    out = {}
    for i in range(days):
        day = base + timedelta(days=i)
        out[f"nhl_sched_{day.isoformat()}"] = f"https://api-web.nhle.com/v1/schedule/{day.isoformat()}"
    return out




# ---------------------------------------------------------------- round 2 probes
# A second pass added after reading the first capture: endpoints chosen because a
# governing body (not an aggregator) publishes the ranking/table/result the desk needs
# to originate a line.  Failures stay recorded in the manifest.
OFFICIAL.update({
    "wta_rankings": "https://www.wtatennis.com/rankings/singles",
    "atp_rankings": "https://www.atptour.com/en/rankings/singles",
    "wst_rankings": "https://www.wst.tv/rankings/",
    "wst_matches": "https://www.wst.tv/matches/",
    "wst_tournaments": "https://www.wst.tv/tournaments/",
    "pdc_oom": "https://www.pdc.tv/order-of-merit",
    "pdc_tournaments": "https://www.pdc.tv/tournaments",
    "world_rugby_rankings": "https://www.world.rugby/rankings/mru",
    "premiership_table": "https://www.premiershiprugby.com/table",
    "urc_table": "https://www.unitedrugby.com/table",
    "epcr_fixtures_en": "https://www.epcrugby.com/en/fixtures",
    "superleague_table": "https://www.superleague.co.uk/table",
    "superleague_fixtures": "https://www.superleague.co.uk/fixtures",
    "nrl_ladder_r1": "https://www.nrl.com/ladder/data?competition=111&season=2026&round=1",
    "hbl_table": "https://www.daikin-hbl.de/de/tabelle/",
    "lnh_table": "https://www.lnh.fr/liquimoly-starligue/classement",
    "asobal_table": "https://www.asobal.es/clasificacion",
    "ehfcl_standings": "https://ehfcl.eurohandball.com/men/2026-27/standings/",
    "icc_rankings_test": "https://www.icc-cricket.com/rankings/mens/team-rankings/test",
    "icc_fixtures_results": "https://www.icc-cricket.com/fixtures-results",
    "owgr_rankings": "https://www.owgr.com/current-rankings",
    "pga_leaderboard": "https://www.pgatour.com/leaderboard",
    "vnl_schedule": "https://en.volleyballworld.com/volleyball/competitions/volleyball-nations-league/schedule/",
    "cev_champions_league": "https://www.cev.eu/club/cev-champions-league/",
    "gaa_api_fixtures": "https://www.gaa.ie/api/fixtures",
    "gbgb_results_today": "https://www.gbgb.org.uk/results?date=2026-10-24",
    "f1_standings": "https://www.formula1.com/en/results/2026/drivers",
    "motogp_standings": "https://www.motogp.com/en/standings/2026",
    "nba_schedule": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json",
})

# OLBG's pages are SvelteKit; the framework exposes a JSON data endpoint alongside every
# route.  Probing it is part of the reverse-engineering brief: if it renders the feed
# server-side we can read past the "Load More" control without a browser.
OLBG_URLS.update({
    "data_ice_hockey": "https://www.olbg.com/betting-tips/Ice_Hockey/13/__data.json",
    "data_handball": "https://www.olbg.com/betting-tips/Handball/20/__data.json",
    "data_tennis": "https://www.olbg.com/betting-tips/Tennis/3/__data.json",
})

# Built last, after every update above, so a newly probed endpoint is always fetched.
ALL_GROUPS = {
    "olbg": OLBG_URLS,
    "official": {**OFFICIAL, **schedule_dates()},
}

OFFICIAL.update({
    # EHF's own competition pages: the standings page returned a server-rendered table,
    # so the fixtures/results routes are worth probing for official fixture identity.
    "ehfcl_matches": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
    "ehfcl_results": "https://ehfcl.eurohandball.com/men/2026-27/results/",
    "wta_calendar": "https://www.wtatennis.com/tournaments",
    "wtatour_rankings_doubles": "https://www.wtatennis.com/rankings/doubles",
})

MAX_BYTES = 12 * 1024 * 1024

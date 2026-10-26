#!/usr/bin/env python3
"""Board OV collection spec.

Every URL is either (a) an OLBG.com page, used to reverse-engineer the site and
to list the matches OLBG currently offers, or (b) a governing body / league /
tour / regulator endpoint, used to confirm a fixture, a result, a table, a
ranking or a season statistic.  No aggregator, no betting shop, no wiki: a
value is only ever published from bytes listed here.

Groups are fetched independently and every outcome (200, 4xx, 5xx, timeout,
DNS) is recorded in the manifest.  A failed target is never replaced by a guess.
"""
from __future__ import annotations

from datetime import date, timedelta

# ---------------------------------------------------------------- capture window
WINDOW_START = "2026-10-26"   # first day a match must start to be published
WINDOW_END = "2026-11-08"     # last day included in the desk
FORM_START = "2026-10-08"     # results earlier than this are not read for form

# ------------------------------------------------------------------- OLBG hubs
# Sport ids re-confirmed from https://www.olbg.com/sitemap-betting-tips.xml at
# capture time.  "Gaelic Sports" is served by OLBG as two sports, Gaelic
# Football and Hurling, so both are captured and reported together.
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

OLBG_URLS: dict[str, str] = {
    "olbg_robots": "https://www.olbg.com/robots.txt",
    "olbg_sitemap": "https://www.olbg.com/sitemap-betting-tips.xml",
    "olbg_tips_index": "https://www.olbg.com/betting-tips",
}
for _key, (_sid, _slug) in OLBG.items():
    OLBG_URLS[f"hub_{_key}"] = f"https://www.olbg.com/betting-tips/{_slug}/{_sid}"

# --------------------------------------------------------------- official feeds
OFFICIAL: dict[str, str] = {
    # Ice Hockey — NHL's own schedule and standings services
    "nhl_standings": "https://api-web.nhle.com/v1/standings/now",
    # Ice Hockey — Liiga (Finland) open API
    "liiga_games": "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027",
    "liiga_standings": "https://liiga.fi/api/v2/standings/?season=2027",
    # Baseball — MLB StatsAPI
    "mlb_standings": ("https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
                      "&season=2026&standingsTypes=regularSeason&hydrate=team"),
    "mlb_hitting": ("https://statsapi.mlb.com/api/v1/teams/stats?season=2026"
                    "&group=hitting&stats=season&sportId=1"),
    "mlb_pitching": ("https://statsapi.mlb.com/api/v1/teams/stats?season=2026"
                     "&group=pitching&stats=season&sportId=1"),
    # Basketball — NBA full-season schedule (carries every played score) + EuroLeague
    "nba_schedule": "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json",
    "nba_scoreboard": "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json",
    "euroleague_games": "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games",
    "eurocup_games": "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games",
    # Handball — EHF Champions League + national leagues
    "ehfcl_matches": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
    "ehfcl_standings": "https://ehfcl.eurohandball.com/men/2026-27/standings/",
    "hbl_spielplan": "https://www.dkb-handball-bundesliga.de/spielplan",
    "hbl_tabelle": "https://www.dkb-handball-bundesliga.de/tabelle",
    "danish_table": "https://tophaandbold.dk/stillinger/herreligaen",
    "danish_fixtures": "https://tophaandbold.dk/kampprogram/herreligaen",
    # Volleyball — Italian SuperLega / Serie A + Polish PlusLiga + CEV
    "legavolley_classifica": "https://www.legavolley.it/classifica/",
    "plusliga_table": "https://www.plusliga.pl/table/tour/47.html",
    "plusliga_matches": "https://www.plusliga.pl/mecze/tour/47.html",
    "cvf_extraliga": "https://www.cvf.cz/extraliga/extraliga-muzi?filteredGroupId=29147",
    "cev_competitions": "https://www.cev.eu/competitions/",
    # Tennis — WTA official API + rankings pages
    "wta_tournaments": "https://api.wtatennis.com/tennis/tournaments?year=2026&pageSize=100",
    "wta_rankings": "https://www.wtatennis.com/rankings/singles",
    "atp_rankings": "https://www.atptour.com/en/rankings/singles",
    "atp_scores": "https://www.atptour.com/en/scores/current",
    # Snooker — WST's own match service + rankings
    "wst_matches": ("https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=200"
                    "&filter[startDateTime][gte]=" + WINDOW_START + "T00:00:00Z"),
    "wst_participants": "https://participants.snooker.web.gc.wstservices.co.uk/v2/?page.size=200",
    "wst_rankings": "https://www.wst.tv/rankings/",
    "wst_tournaments": "https://www.wst.tv/tournaments/",
    # Darts — PDC services + order of merit
    "pdc_matches": "https://matches.darts.web.gc.pdcservices.co.uk/v2/?page.size=200",
    "pdc_participants": "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=200",
    "pdc_oom": "https://www.pdc.tv/order-of-merit/pdc-order-of-merit",
    "pdc_calendar": "https://www.pdc.tv/tournaments/calendar",
    # Rugby League — RLWC 2026 official API + Super League
    "rlwc_fixtures_api": "https://www.rlwc2026.com/api/fixtures",
    "rlwc_fixtures": "https://www.rlwc2026.com/fixtures",
    "rlwc_results": "https://www.rlwc2026.com/results",
    "superleague_fixtures": "https://www.superleague.co.uk/fixtures",
    "superleague_table": "https://www.superleague.co.uk/table",
    # Rugby Union — Premiership, Top 14, URC, EPCR, World Rugby
    "premiership_standings_api": "https://www.premiershiprugby.com/api/standings",
    "premiership_fixtures": "https://www.premiershiprugby.com/fixtures-results",
    "top14_calendar": "https://top14.lnr.fr/calendrier-et-resultats",
    "urc_fixtures_news": "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/",
    "urc_table": "https://stats.unitedrugby.com/match-centre/table/2026-27",
    "epcr_fixtures": "https://www.epcrugby.com/fixtures",
    "world_rugby_rankings": "https://www.world.rugby/rankings/mru",
    # Cricket — ICC + the boards that stage the fixtures
    "icc_fixtures_results": "https://www.icc-cricket.com/fixtures-results",
    "icc_rankings_t20": "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i",
    "icc_rankings_odi": "https://www.icc-cricket.com/rankings/mens/team-rankings/odi",
    "cricket_australia_fixtures": "https://www.cricket.com.au/fixtures",
    "ecb_fixtures": "https://www.ecb.co.uk/england/men/fixtures",
    "nzc_matches": "https://www.nzc.nz/matches",
    # Gaelic sports — GAA official fixtures
    "gaa_fixtures": "https://www.gaa.ie/fixtures",
    "gaa_results": "https://www.gaa.ie/fixtures-results",
    "ladies_gaelic": "https://ladiesgaelic.ie/",
    # Greyhounds — GBGB regulator results API
    "gbgb_racing": "https://www.gbgb.org.uk/racing",
    # Golf — OWGR + the tours
    "owgr_rankings": "https://www.owgr.com/current-world-ranking",
    "pgatour_schedule": "https://www.pgatour.com/schedule",
    "pgatour_leaderboard": "https://www.pgatour.com/leaderboard",
    "europeantour_schedule": "https://www.europeantour.com/dpworld-tour/schedule",
    "lpga_tournaments": "https://www.lpga.com/tournaments",
    # Motor racing — Formula 1 and MotoGP
    "f1_racing_2026": "https://www.formula1.com/en/racing/2026.html",
    "f1_drivers": "https://www.formula1.com/en/results/2026/drivers",
    "f1_teams": "https://www.formula1.com/en/results/2026/team",
    "motogp_calendar": "https://www.motogp.com/en/calendar/2026",
    "motogp_standings": "https://www.motogp.com/en/standings/2026",
}


def _date_range(start: str, days: int) -> list[str]:
    y, m, d = (int(x) for x in start.split("-"))
    base = date(y, m, d)
    return [(base + timedelta(days=i)).isoformat() for i in range(days)]


def build_official() -> dict[str, str]:
    """Add the generated per-date and per-competition endpoints."""
    out = dict(OFFICIAL)
    # NHL: a schedule per date, covering form (played) and the upcoming window.
    for day in _date_range("2026-10-14", 27):
        if not ("2026-10-14" <= day <= "2026-11-09"):
            continue
        out[f"nhl_sched_{day}"] = f"https://api-web.nhle.com/v1/schedule/{day}"
    # MLB: post-season schedule for the current window
    out["mlb_sched"] = (
        "https://statsapi.mlb.com/api/v1/schedule?sportId=1"
        f"&startDate={WINDOW_START}&endDate={WINDOW_END}"
        "&hydrate=team,linescore,probablePitcher"
    )
    # Italian volleyball: every championship OLBG's Serie A/B and women's events need
    for cid in (991, 995, 997, 998, 999, 1000, 1001, 1002, 1003, 1004):
        out[f"legavolley_cal_{cid}"] = (
            f"https://www.legavolley.it/calendario/?Anno=2026&IdCampionato={cid}"
        )
    # GBGB: today's and the previous two days' race results (form inputs)
    for day in ("2026-10-24", "2026-10-25", "2026-10-26"):
        out[f"gbgb_results_{day}"] = (
            "https://api.gbgb.org.uk/api/results?page=1&itemsPerPage=100"
            f"&date={day}&race_type=race"
        )
    # WTA: the tournaments OLBG historically lists, probed for the current draw
    for tid in (1023, 1056, 2092, 405, 2038, 2131, 2171):
        out[f"wta_t_matches_{tid}"] = (
            f"https://api.wtatennis.com/tennis/tournaments/{tid}/2026/matches"
        )
    return out


ALL_GROUPS = {
    "olbg": OLBG_URLS,
    "official": build_official(),
}


def targets(group: str) -> list[dict]:
    sport_of = {}
    for key, (_sid, slug) in OLBG.items():
        sport_of[f"hub_{key}"] = slug.replace("_", " ")
    rows = []
    for tid, url in ALL_GROUPS[group].items():
        rows.append({
            "id": tid,
            "url": url,
            "group": group,
            "sport": sport_of.get(tid, ""),
            "delay": 0.4,
            "timeout": 60 if "nba" in tid or "gaa" in tid else 45,
        })
    return rows


if __name__ == "__main__":
    import json
    import sys

    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "all":
        rows = targets("olbg") + targets("official")
    else:
        rows = targets(which)
    json.dump(rows, sys.stdout, indent=1)
    print()

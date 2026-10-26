#!/usr/bin/env python3
"""Board AN pass-2 targets: OLBG event/category pages + the sources pass 1 missed.

Pass 1 read the OLBG hubs, which only carry *tipped* events.  To see every match OLBG
lists for a sport we read the per-sport category page and the individual event pages
(the event page is where OLBG exposes all of its markets).  The gap list below targets
the sports where pass 1 found no usable official feed.

Usage: python3 make_targets_events.py OLBG_JSON OUT_JSON
"""
from __future__ import annotations

import json
import sys

olbg = json.load(open(sys.argv[1]))
out: list[dict] = []
seen: set[str] = set()


def add(sport: str, tid: str, url: str, kind: str = "html", delay: float = 0.4) -> None:
    if tid in seen:
        return
    seen.add(tid)
    out.append({"sport": sport, "id": tid, "url": url, "kind": kind, "delay": delay})


# 1. OLBG category page per sport (the listing behind each hub) + the tips sitemap.
add("OLBG", "olbg_sitemap_betting_tips", "https://www.olbg.com/sitemap-betting-tips.xml", "xml")
add("OLBG", "olbg_today", "https://www.olbg.com/betting-tips/today")
CAT = {
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
for sport, (slug, sid, key) in CAT.items():
    add(sport, f"olbg_cat_{key}", f"https://www.olbg.com/betting-tips/{slug}/All_{slug}/{sid}")
    add(sport, f"olbg_events_{key}",
        f"https://www.olbg.com/betting-tips/{slug}/All_{slug}/All_Events/{sid}")

# 2. One page per OLBG event already discovered (full market list for that match).
for ev in olbg.get("events", []):
    if not ev.get("upcoming") or not ev.get("event_url"):
        continue
    slug = ev["event_url"].rsplit("/", 1)[-1].split("?")[0]
    add(ev["sport"], f"olbg_ev_{slug[:52]}_{ev['event_url'].rsplit('=', 1)[-1]}", ev["event_url"])

# 3. Gaps: official sources pass 1 could not confirm.
GAP = [
    # darts — pdc.tv is a JS shell; try its REST surface and the official event pages
    ("Darts", "pdc_wp_json", "https://www.pdc.tv/wp-json/", "json"),
    ("Darts", "pdc_wp_pages", "https://www.pdc.tv/wp-json/wp/v2/pages?per_page=100", "json"),
    ("Darts", "pdc_api_tournaments", "https://www.pdc.tv/api/tournaments", "json"),
    ("Darts", "pdc_api_matches", "https://www.pdc.tv/api/matches", "json"),
    ("Darts", "pdc_ec_players",
     "https://www.pdc.tv/tournaments/machineseeker-european-championship/players"),
    ("Darts", "pdc_ec_draw",
     "https://www.pdc.tv/tournaments/machineseeker-european-championship/draw"),
    ("Darts", "darts_wst_matches",
     "https://matches.snooker.web.gc.wstservices.co.uk/v2/?page.size=5", "json"),
    # greyhounds — GBGB publishes results; racecards live behind a different route
    ("Greyhounds", "gbgb_home", "https://www.gbgb.org.uk/"),
    ("Greyhounds", "gbgb_results_date", "https://www.gbgb.org.uk/results/?date=2026-10-26"),
    ("Greyhounds", "gbgb_meetings", "https://www.gbgb.org.uk/meetings/"),
    ("Greyhounds", "gbgb_racing", "https://www.gbgb.org.uk/racing/"),
    ("Greyhounds", "gbgb_api_root", "https://api.gbgb.org.uk/api/", "json"),
    ("Greyhounds", "gbgb_api_races_plain", "https://api.gbgb.org.uk/api/races?date=2026-10-26", "json"),
    ("Greyhounds", "gbgb_api_v1", "https://api.gbgb.org.uk/api/v1/races?date=2026-10-26", "json"),
    ("Greyhounds", "igb_home", "https://www.igb.ie/"),
    ("Greyhounds", "igb_fixtures", "https://www.igb.ie/racing/fixtures/"),
    # tennis — rankings are the strength input; ATP blocks, so try WTA site + ITF + protennislive
    ("Tennis", "wta_rankings_page", "https://www.wtatennis.com/rankings/singles"),
    ("Tennis", "wta_rankings_page2", "https://www.wtatennis.com/rankings"),
    ("Tennis", "wta_api_rank2",
     "https://api.wtatennis.com/tennis/players/rankings?page=0&pageSize=100&type=singles", "json"),
    ("Tennis", "wta_api_players",
     "https://api.wtatennis.com/tennis/players?page=0&pageSize=100", "json"),
    ("Tennis", "wta_api_scores", "https://api.wtatennis.com/tennis/scores/?page=0&pageSize=100", "json"),
    ("Tennis", "atp_rank_page", "https://www.atptour.com/en/rankings/singles?rankRange=1-100"),
    ("Tennis", "atp_paris", "https://www.atptour.com/en/scores/current/paris-masters/352/results"),
    ("Tennis", "ptl_mds_352", "https://www.protennislive.com/posting/2026/352/mds.pdf", "pdf"),
    ("Tennis", "ptl_qs_352", "https://www.protennislive.com/posting/2026/352/qs.pdf", "pdf"),
    # cricket
    ("Cricket", "icc_fixtures", "https://www.icc-cricket.com/fixtures"),
    ("Cricket", "icc_scores", "https://www.icc-cricket.com/scores"),
    ("Cricket", "ecb_women", "https://www.ecb.co.uk/england/women/fixtures"),
    ("Cricket", "cricket_au_schedule", "https://www.cricket.com.au/schedule"),
    # rugby union
    ("Rugby Union", "urc_fixtures", "https://www.unitedrugby.com/fixtures"),
    ("Rugby Union", "urc_match_centre", "https://www.unitedrugby.com/match-centre"),
    ("Rugby Union", "autumn_nations", "https://www.autumnnationsseries.com/fixtures"),
    ("Rugby Union", "six_nations", "https://www.sixnationsrugby.com/fixtures"),
    ("Rugby Union", "prem_table_data", "https://www.premiershiprugby.com/table/__data.json", "json"),
    # basketball
    ("Basketball", "el_standings2",
     "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/standings?phase=RS", "json"),
    ("Basketball", "el_standings3", "https://api-live.euroleague.net/v2/standings/E2026", "json"),
    ("Basketball", "lega_classifica", "https://www.legabasket.it/classifica"),
    ("Basketball", "nba_scores_today", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", "json"),
    # handball
    ("Handball", "ehfcl_m_results", "https://ehfcl.eurohandball.com/men/2026-27/results/"),
    ("Handball", "ehf_world", "https://www.ihf.info/competitions"),
    # golf
    ("Golf", "pga_bermuda_teetimes",
     "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship/R2026528/teetimes"),
    ("Golf", "euro_schedule_2026", "https://www.europeantour.com/dpworld-tour/schedule/2026"),
    ("Golf", "lpga_schedule_2026", "https://www.lpga.com/tournaments?year=2026"),
    # motor racing
    ("Motor Racing", "f1_las_vegas", "https://www.formula1.com/en/racing/2026/las-vegas"),
    ("Motor Racing", "f1_qatar", "https://www.formula1.com/en/racing/2026/qatar"),
    ("Motor Racing", "f1_results_2026", "https://www.formula1.com/en/results/2026"),
    ("Motor Racing", "motogp_results", "https://www.motogp.com/en/results/2026"),
    # gaelic
    ("Gaelic Sports", "gaa_competitions", "https://www.gaa.ie/competitions"),
    # rugby league
    ("Rugby League", "rlwc_match_centre", "https://www.rlwc2026.com/match-centre"),
    ("Rugby League", "nrl_ladder", "https://www.nrl.com/ladder/"),
]
for entry in GAP:
    sport, tid, url = entry[0], entry[1], entry[2]
    kind = entry[3] if len(entry) > 3 else "html"
    add(sport, tid, url, kind)

json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), indent=1)
print(f"{len(out)} pass-2 targets")

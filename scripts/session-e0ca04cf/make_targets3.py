#!/usr/bin/env python3
"""Pass-3 targets: the ranking/table feeds that sit behind script-rendered pages."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "targets3.json"
T: list[dict] = []


def add(sport, tid, url, delay=0.6):
    T.append({"sport": sport, "id": tid, "url": url, "delay": delay})


# WST/Apollo-style feeds: matches. and participants. both answered, so try rankings.
add("Snooker", "wst_rankings_api", "https://rankings.snooker.web.gc.wstservices.co.uk/v2/?page.size=200")
add("Snooker", "wst_rankings_api2",
    "https://rankings.snooker.web.gc.wstservices.co.uk/v2/?page.size=200"
    "&filter[rankingType]=prizeMoney")
# Same provider for the PDC
add("Darts", "pdc_rankings_api", "https://rankings.pdc.web.gc.wstservices.co.uk/v2/?page.size=200")
add("Darts", "pdc_matches_api2",
    "https://matches.pdc.web.gc.wstservices.co.uk/v2/?page.size=400"
    "&filter[startDateTime][gte]=2026-10-24&filter[startDateTime][lte]=2026-11-08")
add("Darts", "pdc_participants2", "https://participants.pdc.web.gc.wstservices.co.uk/v2/?page.size=200")
# Rugby union: the Premiership feed the standings page advertises
add("Rugby Union", "rugby_feeds_matches", "https://rugby-union-feeds.incrowdsports.com/v1/matches?limit=200")
add("Rugby Union", "rugby_feeds_competitions", "https://rugby-union-feeds.incrowdsports.com/v1/competitions")
add("Rugby Union", "urc_standings_page", "https://www.unitedrugby.com/standings")
add("Rugby Union", "urc_standings_data", "https://stats.unitedrugby.com/standings/__data.json")
# Cricket: ICC ranking API attempts + a static fixture page
add("Cricket", "icc_api_rankings", "https://www.icc-cricket.com/api/rankings?gender=mens&type=team&discipline=t20i")
add("Cricket", "icc_api_root", "https://api.icc-cricket.com/rankings")
add("Cricket", "icc_t20i_json", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i.json")
# Handball: table endpoints for the leagues the OLBG card actually lists
add("Handball", "hbl_api_table", "https://www.dkb-handball-bundesliga.de/api/table")
add("Handball", "asobal_clasificacion", "https://asobal.es/clasificacion/")
add("Handball", "lnh_classement", "https://www.lnh.fr/classement")
# Volleyball: CEV / Bundesliga tables that would widen coverage beyond PlusLiga
add("Volleyball", "vbl_tabelle", "https://www.volleyball-bundesliga.de/tabelle")

if __name__ == "__main__":
    OUT.write_text(json.dumps(T, indent=1) + "\n")
    print(f"{len(T)} pass-3 targets -> {OUT}")

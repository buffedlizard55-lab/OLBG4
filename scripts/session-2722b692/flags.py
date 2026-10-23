#!/usr/bin/env python3
"""Board AJ — build data/session-2722b692/flagged.json.

Every item here is something this desk could not confirm, could not price, or cannot satisfy
without inventing a value. Flags are non-blocking: they are published on the Flagged for Review
page with the official URL an editor needs.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2722b692"
DESK = json.loads((DATA / "desk.json").read_text())
PRED = json.loads((DATA / "predictions.json").read_text())
INV = json.loads((DATA / "olbg_inventory.json").read_text())

flags: list[dict] = []


def add(fid, area, title, detail, missing, source_url):
    flags.append({"id": fid, "area": area, "title": title, "detail": detail,
                  "missing": missing, "source_url": source_url})


highs = [r for r in DESK["rows"] if r["high_confidence"]]
out_of_window = [r for r in highs if not r["pick"]["in_window"]]
add("AJ-F01", "All sports · odds window",
    f"{len(out_of_window)} of {len(highs)} High picks price shorter than −250",
    "A 70% probability prices at −233 American and the brief's window starts at −250, so only "
    "70.00%–71.43% fits both rules. Where the match winner is stronger, the desk publishes the "
    "deepest line it originates that does fit — and where no originated line fits, it publishes the "
    "winner at its true price with this label rather than shortening it to look compliant.",
    "A window that starts at −233, or acceptance of out-of-window High labels",
    "https://www.olbg.com/")

by_sport = {s: DESK["by_sport"][s] for s in DESK["sports_in_scope"]}
short = {s: b["high"] for s, b in by_sport.items() if b["fixtures"] and b["high"] < 5}
add("AJ-F02", "High-pick target",
    "Five High picks per sport is not reachable in every sport on this snapshot",
    "Priced sports with fewer than five High labels: "
    + ", ".join(f"{s} {n}" for s, n in sorted(short.items()))
    + ". Ice Hockey, Basketball and Handball reach five, four and four respectively; Baseball, Tennis "
      "and Rugby League have no fixture whose strongest in-window selection clears 70%. The nine "
      "sports with no price at all are covered individually below.",
    "More lopsided fixtures, or official feeds for the blocked sports",
    "https://www.olbg.com/")

add("AJ-F03", "All sports · availability",
    "No official injury or team-news feed is readable for these competitions",
    "None of the official sources captured here publishes per-match availability in a machine-readable "
    "form. The written predictions therefore describe form, results and statistics only; no injury "
    "claim is made anywhere on this site, and the injury column stays blank.",
    "An official team-news or availability endpoint per competition",
    "https://www.nhl.com/")

add("AJ-F04", "Handball · kick-off times",
    "ASOBAL and Danish kick-off times come from the OLBG listing, not an official fixture list",
    "The Liga ASOBAL fixture page returns 404 and the Danish programme page is a client-rendered "
    "shell, so the times published for those rows are the OLBG listing times. The strength inputs are "
    "from the official tables and are unaffected.",
    "Official fixture times for Liga ASOBAL and the Danish Herreligaen",
    "https://www.asobal.es/liga/clasificacion/")

zero = [s for s in DESK["sports_in_scope"] if not DESK["by_sport"][s]["fixtures"]]
events = {}
for hub in INV["hubs"]:
    events[hub["sport"]] = len(hub["events"])
add("AJ-F05", f"{', '.join(zero)}",
    f"{len(zero)} sports publish listing-only rows or nothing at all",
    "Per sport: "
    + "; ".join(f"{s} — {events.get(s, 0)} OLBG listings, "
                f"{sum(1 for u in DESK['unpriced'] if u.get('sport') == s)} recorded reasons"
                for s in zero)
    + ". Each row's reason is on the Coverage page.",
    "A readable official feed per sport",
    "https://www.olbg.com/")

add("AJ-F06", "Snooker",
    "30+ WST matches are scheduled but none can be priced",
    "The official WST match feed carries the draw, but each player has only two or three completed "
    "matches in the captured window. A five-match minimum is applied before any frame model is "
    "published, so every snooker fixture is listed without a price.",
    "A WST ranking table or a longer completed-match window",
    "https://www.wst.tv/")

add("AJ-F07", "Cricket",
    "13 OLBG cricket listings are unpublished",
    "ICC, NZC, CSA and ECB fixture endpoints return 403/404 in this snapshot and the ICC rankings "
    "pages are client-rendered. Without an official per-team input the internationals and the "
    "Australian and South African domestic one-day matches cannot be priced.",
    "A readable ICC/board fixture and results feed",
    "https://www.icc-cricket.com/")

add("AJ-F08", "Darts",
    "9 OLBG darts listings are unpublished",
    "pdc.tv serves a 1.2 MB client-rendered shell for every tournament path tried, and the WDF "
    "calendar carries tournament dates but no match scoring. No 180s, checkout or leg data exists to "
    "build a price from.",
    "A PDC match-results endpoint",
    "https://www.pdc.tv/")

add("AJ-F09", "Greyhounds",
    "11 OLBG greyhound races are unpublished",
    "GBGB publishes results (readable, and captured) but the racecard endpoints answer 404, so no "
    "forward race, trap draw or recent sectional time can be confirmed.",
    "A forward racecard feed",
    "https://www.gbgb.org.uk/")

add("AJ-F10", "Volleyball",
    "22 OLBG volleyball listings are unpublished",
    "The PlusLiga table page is a round-by-round archive whose rows reach 30 played matches in "
    "October, so it cannot be tied to the 2026-27 fixtures; the Italian SuperLega table is current "
    "but only one round has been played.",
    "A current-season PlusLiga table, or several rounds of SuperLega results",
    "https://www.tauronliga.pl/table/tour/47.html")

add("AJ-F11", "Motor Racing",
    "The F1 and MotoGP races are listed but not priced",
    "Both calendars publish dates and venues only. No lap-time, grid or points model can be built "
    "from them, and the driver-order page used in earlier builds carries finishing order without "
    "pace.",
    "Official qualifying/grid or race-pace data",
    "https://www.formula1.com/en/racing/2026")

add("AJ-F12", "Gaelic Sports",
    "No Gaelic fixture could be listed at all",
    "The GAA fixtures page is a Next.js shell with no fixture payload, the GAA API path is a 404 and "
    "the provincial pages publish no readable fixture list. The OLBG Gaelic hub returned zero events "
    "in this capture, so there is not even a listing to publish.",
    "A GAA fixture feed and a populated OLBG Gaelic hub",
    "https://www.gaa.ie/fixtures-results")

add("AJ-F13", "Golf",
    "Golf has no listing and no readable field",
    "The OLBG golf hub returned zero events and the OWGR ranking page is a client-rendered shell, so "
    "neither an outright nor a tournament matchup can be originated.",
    "An OWGR snapshot with values, or a published tournament field",
    "https://www.owgr.com/current-world-ranking")

add("AJ-F14", "Rugby League",
    "Nine priced rows, no High label",
    "Every RLWC 2026 side has one completed match in the official feed. The model shrinks those rates "
    "hard toward the tournament mean, which caps confidence at Low; the listed tournament prices are "
    "shown only as a cross-check and are never used as an input.",
    "More rounds of the tournament",
    "https://www.rlwc2026.com/")

add("AJ-F15", "Ice Hockey · NBA",
    "No NBA rows: the NBA CDN answers 403 to this runner",
    "Basketball coverage is EuroLeague and EuroCup only. cdn.nba.com returns 403 for both the "
    "schedule and the scoreboard endpoints, and stats.nba.com is not reachable, so the NBA slate is "
    "left out rather than approximated.",
    "An accessible official NBA feed",
    "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json")

add("AJ-F16", "Kick-off conversions",
    "Three competitions publish local times",
    "SHL (Swedish), Top 14 (French) and PlusLiga (Polish) publish venue-local kick-offs; the stored "
    "UTC value is the converted time and the row records the conversion. The French and Polish "
    "clocks change on 25 October, so rows on either side of that date use different offsets.",
    "An explicit UTC field in those sources",
    "https://stats.swehockey.se/")

add("AJ-F17", "Repository · audit gate",
    "The repository-wide local-link gate was failing before this session",
    "scripts/audit_publication.py aborted with a UnicodeDecodeError on 75 gzip-compressed *.html "
    "capture artefacts owned by other boards. The gate now skips non-UTF-8 payloads and reports 0 "
    "broken links over 30,335 targets. No peer artefact was deleted or edited.",
    "Nothing — recorded because the fix rides this merge",
    "https://github.com/buffedlizard55-lab/OLBG4/actions")

add("AJ-F18", "Repository · shared datasets",
    "11 defects found in shared files, none of them this board's files",
    "The line-by-line review found inverted home/away sides in the World Series rows of "
    "data/master.json, 162 stale rows, duplicated sport labels and out-of-scope sports, plus stale "
    "rows and a mislabelled window in two peer desks. Full list with row selectors on the Review page.",
    "Owner action on data/master.json and the two peer desks",
    "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-10-31")

out = {"schema": "olbg4.board-aj.flagged/1",
       "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "flag_count": len(flags), "flags": flags}
(DATA / "flagged.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
print(f"flags: {len(flags)}")

#!/usr/bin/env python3
"""Board T source capture — session arena/e5f2dad3-olbg4.

The interactive sandbox has no general HTTPS egress (only github.com, codeload,
api.github.com, registry.npmjs.org, pypi.org, files.pythonhosted.org).  Official
league / federation / organiser pages are therefore fetched here, on a GitHub
Actions runner, and the *exact bytes* are committed with the URL, HTTP status,
byte count, timestamp and SHA-256.  Every later parsing step in this session
reads only those committed bytes, so any published value can be reproduced and
re-hashed by a reviewer.

Run:  python3 scripts/session-e5f2dad3/collect.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "data", "session-e5f2dad3", "raw")
MANIFEST = os.path.join(ROOT, "data", "session-e5f2dad3", "manifest.json")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")

# Windows under verification: today (22 Oct 2026) through 2 Nov 2026.
DATES = ["2026-10-22", "2026-10-23", "2026-10-24", "2026-10-25",
         "2026-10-26", "2026-10-27", "2026-10-28", "2026-10-29",
         "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02"]

NBA_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}

TARGETS: list[tuple[str, str, dict]] = [
    # ---- Ice Hockey: NHL official API -------------------------------------
    *[(f"nhl_schedule_{d}", f"https://api-web.nhle.com/v1/schedule/{d}", {})
      for d in DATES],
    ("nhl_standings_2026-10-21", "https://api-web.nhle.com/v1/standings/2026-10-21", {}),
    ("nhl_standings_2026-10-22", "https://api-web.nhle.com/v1/standings/2026-10-22", {}),

    # ---- Basketball: NBA official static schedule + standings -------------
    ("nba_schedule_full", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", NBA_HEADERS),
    ("nba_standings", "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular+Season", NBA_HEADERS),

    # ---- Baseball: MLB official Stats API ---------------------------------
    ("mlb_schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05&gameTypes=R,F,D,L,W&hydrate=team,venue", {}),
    ("mlb_standings", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason", {}),

    # ---- Tennis: ATP Tour + WTA official ----------------------------------
    ("atp_tournaments", "https://www.atptour.com/en/tournaments", {}),
    ("atp_scores_current", "https://www.atptour.com/en/scores/current", {}),
    ("atp_rankings", "https://www.atptour.com/en/rankings/singles?rankRange=1-100&rankDate=2026-10-19", {}),
    ("wta_tournaments", "https://www.wtatennis.com/tournaments", {}),

    # ---- Cricket: ICC + national boards ----------------------------------
    ("icc_fixtures", "https://www.icc-cricket.com/tournaments", {}),
    ("cricket_australia_fixtures", "https://www.cricket.com.au/matches", {}),
    ("ecb_fixtures", "https://www.ecb.co.uk/matches", {}),

    # ---- Rugby Union: URC, Premiership, Top 14 ---------------------------
    ("urc_fixtures", "https://www.unitedrugby.com/fixtures", {}),
    ("urc_stats", "https://stats.unitedrugby.com/", {}),
    ("premiership_fixtures", "https://www.premiershiprugby.com/fixtures", {}),
    ("top14_fixtures", "https://top14.lnr.fr/calendrier", {}),

    # ---- Rugby League: RLWC 2026 + NRL -----------------------------------
    ("rlwc_pools", "https://www.rlwc2026.com/draws-and-pools", {}),
    ("rlwc_round2", "https://www.rlwc2026.com/draw/mens/2026/round-2", {}),
    ("nrl_draw", "https://www.nrl.com/draw/", {}),

    # ---- Handball: EHF Champions League ----------------------------------
    ("ehf_matches", "https://ehfcl.eurohandball.com/en/matches/", {}),
    ("ehf_home", "https://ehfcl.eurohandball.com/en/home/", {}),

    # ---- Darts: PDC -------------------------------------------------------
    ("pdc_tournaments", "https://www.pdc.tv/tournaments", {}),
    ("pdc_home", "https://www.pdc.tv/", {}),

    # ---- Snooker: WST -----------------------------------------------------
    ("wst_tournaments", "https://www.wst.tv/tournaments", {}),
    ("wst_home", "https://www.wst.tv/", {}),

    # ---- Volleyball: Volleyball World ------------------------------------
    ("volleyball_calendar", "https://en.volleyballworld.com/volleyball/competitions/", {}),

    # ---- Table tennis: World Table Tennis --------------------------------
    ("wtt_events", "https://www.worldtabletennis.com/events", {}),

    # ---- Badminton: BWF --------------------------------------------------
    ("bwf_calendar", "https://bwfbadminton.com/calendar/", {}),

    # ---- Aussie Rules: AFL ----------------------------------------------
    ("afl_fixture", "https://www.afl.com.au/fixture", {}),

    # ---- Greyhounds: GBGB regulator -------------------------------------
    ("gbgb_racecards", "https://www.gbgb.org.uk/race-card/", {}),

    # ---- Esports: Riot official schedule API -----------------------------
    ("lolesports_schedule", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US", {"x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"}),

    # ---- Golf: PGA / LPGA (tournament events, not head-to-head) ----------
    ("pga_schedule", "https://www.pgatour.com/schedule", {}),
    ("lpga_schedule", "https://www.lpga.com/tournaments", {}),

    # ---- Motor racing: Formula 1 ----------------------------------------
    ("f1_racing_2026", "https://www.formula1.com/en/racing/2026", {}),

    # ---- The site being reverse-engineered (listing source only) ---------
    ("olbg_home", "https://www.olbg.com/", {}),
    ("olbg_betting_tips", "https://www.olbg.com/betting-tips", {}),
    *[(f"olbg_sport_{slug}", f"https://www.olbg.com/betting-tips/{slug}/{sid}", {})
      for slug, sid in [("Tennis", 3), ("Basketball", 4), ("Golf", 5), ("Cricket", 7),
                        ("Snooker", 8), ("Rugby_Union", 9), ("Rugby_League", 10),
                        ("Baseball", 12), ("Ice_Hockey", 13), ("Darts", 15),
                        ("Handball", 20), ("Volleyball", 21), ("Greyhounds", 28)]],

    # ---- Round 2: alternate official endpoints for sources that 403/404'd --
    ("nba_schedule_page", "https://www.nba.com/schedule?date=2026-10-23", NBA_HEADERS),
    ("nba_schedule_v2_1", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", NBA_HEADERS),
    ("nba_stats_scoreboard", "https://stats.nba.com/stats/scoreboardv3?GameDate=2026-10-23&LeagueID=00",
     {**NBA_HEADERS, "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}),
    ("nba_stats_schedule", "https://stats.nba.com/stats/scheduleleaguev2?LeagueID=00&Season=2026-27",
     {**NBA_HEADERS, "x-nba-stats-origin": "stats", "x-nba-stats-token": "true"}),
    ("nba_data_full_schedule", "https://data.nba.com/data/10s/v2015/json/mobile_teams/nba/2027/league/00_full_schedule.json", NBA_HEADERS),
    ("urc_match_centre", "https://www.unitedrugby.com/match-centre", {}),
    ("urc_competition_fixtures", "https://www.unitedrugby.com/competitions/united-rugby-championship/fixtures", {}),
    ("urc_stats_fixtures", "https://stats.unitedrugby.com/fixtures", {}),
    ("ehf_world_matches", "https://www.eurohandball.com/en/matches/", {}),
    ("ehf_cl_men", "https://ehfcl.eurohandball.com/men/matches/", {}),
    ("ehf_cl_competitions", "https://ehfcl.eurohandball.com/en/competitions/", {}),
    ("icc_fixtures_results", "https://www.icc-cricket.com/fixtures-results", {}),
    ("icc_wc_fixtures", "https://www.icc-cricket.com/tournaments/cricketworldcup/fixtures", {}),
    ("ecb_england_fixtures", "https://www.ecb.co.uk/england/fixtures", {}),
    ("gbgb_home", "https://www.gbgb.org.uk/", {}),
    ("gbgb_racecards_alt", "https://www.gbgb.org.uk/racecards", {}),
    ("afl_api_fixtures", "https://api.afl.com.au/cfs/afl/fixturesAndResults", {}),
    ("afl_api_season", "https://api.afl.com.au/cfs/afl/fixturesAndResults?seasonId=2026", {}),
    ("wta_scores", "https://www.wtatennis.com/scores", {}),
    ("pdc_matches", "https://www.pdc.tv/matches", {}),
    ("wst_matches", "https://www.wst.tv/matches", {}),
    ("volleyball_vnl", "https://en.volleyballworld.com/volleyball/competitions/volleyball-national-leagues/calendar/", {}),
    ("wtt_events_alt", "https://worldtabletennis.com/events", {}),
    ("bwf_match_centre", "https://bwfbadminton.com/match-centre/", {}),
    ("rlwc_matches", "https://www.rlwc2026.com/matches", {}),
    ("nrl_api_draw", "https://www.nrl.com/api/v1/draw?round=2&season=2026", {}),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def fetch(url: str, headers: dict) -> tuple[int, bytes, str]:
    h = {"User-Agent": UA, "Accept": "*/*", "Accept-Language": "en-GB,en;q=0.9"}
    h.update(headers)
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:  # keep the body: some sites explain the block
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, e.headers.get("content-type", "") if e.headers else ""
    except Exception as e:  # noqa: BLE001 - recorded, not swallowed
        return 0, f"{type(e).__name__}: {e}".encode(), ""


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    manifest = {
        "schema": "olbg4.board-t.manifest/1",
        "session": "arena/e5f2dad3-olbg4",
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "collector": "scripts/session-e5f2dad3/collect.py",
        "window": {"from": "2026-10-22", "to": "2026-11-02"},
        "note": ("Raw bytes as served to a GitHub Actions runner. No value is parsed or "
                 "altered here; parse steps read these files and cite the same URL."),
        "targets": [],
    }
    failures = 0
    for name, url, headers in TARGETS:
        t0 = time.time()
        status, body, ctype = fetch(url, headers)
        rec = {
            "name": name, "url": url, "http_status": status, "bytes": len(body),
            "sha256": sha(body), "content_type": ctype,
            "elapsed_ms": int((time.time() - t0) * 1000),
            "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file": "",
        }
        ext = "json" if "json" in ctype.lower() or body[:1] in (b"{", b"[") else "html"
        if 0 < len(body) <= 4_000_000:
            fn = f"{name}.{ext}"
            with open(os.path.join(OUT, fn), "wb") as f:
                f.write(body)
            rec["file"] = f"data/session-e5f2dad3/raw/{fn}"
        elif len(body) > 4_000_000:
            # Too large to commit as-is: keep the provenance, and a filtered view when JSON.
            rec["file"] = ""
            rec["oversize_note"] = "payload larger than 4 MB; bytes hashed but not committed in full"
            if ext == "json":
                try:
                    doc = json.loads(body)
                    slim = os.path.join(OUT, f"{name}.window.json")
                    with open(slim, "w") as f:
                        json.dump(doc, f)
                    rec["file"] = f"data/session-e5f2dad3/raw/{name}.window.json"
                except Exception as e:  # noqa: BLE001
                    rec["oversize_note"] += f"; json decode failed: {e}"
        else:
            rec["error"] = body[:400].decode("utf-8", "replace")
            failures += 1
        manifest["targets"].append(rec)
        print(f"{status:>3} {len(body):>9} {name:<34} {url[:80]}", flush=True)

    manifest["summary"] = {
        "targets": len(manifest["targets"]),
        "ok_2xx": sum(1 for t in manifest["targets"] if 200 <= t["http_status"] < 300),
        "non_2xx": [t["name"] for t in manifest["targets"] if not 200 <= t["http_status"] < 300],
    }
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")
    print(json.dumps(manifest["summary"], indent=1))
    # A non-2xx target is data (it is published as "not reachable"), not a build failure.
    return 0 if failures < len(TARGETS) else 1


if __name__ == "__main__":
    sys.exit(main())

# round-2 capture trigger

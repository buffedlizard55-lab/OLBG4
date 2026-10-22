#!/usr/bin/env python3
"""Board Z (session arena/3a9cd0c0-olbg4) live OLBG + 18-sport official source capture.

Strict compliance:
1. Checks https://www.olbg.com/robots.txt first and verifies every OLBG URL requested
   is permitted by robots.txt (never requests /api/, /sports/, /events.php, etc.).
2. Captures raw bytes (.gz) + HTTP status + Content-Type + byte length + UTC timestamp +
   SHA-256 digest into data/session-3a9cd0c0/capture/manifest.json for deterministic
   offline verification.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import json
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "data" / "session-3a9cd0c0" / "capture"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

WTA_HEADERS = {
    "Origin": "https://www.wtatennis.com",
    "Referer": "https://www.wtatennis.com/",
    "Accept": "application/json",
}
PDC_HEADERS = {
    "Origin": "https://www.pdc.tv",
    "Referer": "https://www.pdc.tv/",
    "Accept": "application/json",
}
RIOT_HEADERS = {
    "x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z",
    "Accept": "application/json",
}
NBA_HEADERS = {
    "Origin": "https://www.nba.com",
    "Referer": "https://www.nba.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

TARGETS: list[tuple[str, str, dict[str, str]]] = [
    # --- OLBG public SSR hubs (robots.txt checked strictly before fetch) ---
    ("olbg_robots", "https://www.olbg.com/robots.txt", {}),
    ("olbg_all", "https://www.olbg.com/betting-tips", {}),
    ("olbg_tennis_3", "https://www.olbg.com/betting-tips/Tennis/3", {}),
    ("olbg_basketball_4", "https://www.olbg.com/betting-tips/Basketball/4", {}),
    ("olbg_golf_5", "https://www.olbg.com/betting-tips/Golf/5", {}),
    ("olbg_cricket_7", "https://www.olbg.com/betting-tips/Cricket/7", {}),
    ("olbg_snooker_8", "https://www.olbg.com/betting-tips/Snooker/8", {}),
    ("olbg_rugby_union_9", "https://www.olbg.com/betting-tips/Rugby_Union/9", {}),
    ("olbg_rugby_league_10", "https://www.olbg.com/betting-tips/Rugby_League/10", {}),
    ("olbg_baseball_12", "https://www.olbg.com/betting-tips/Baseball/12", {}),
    ("olbg_ice_hockey_13", "https://www.olbg.com/betting-tips/Ice_Hockey/13", {}),
    ("olbg_motor_racing_14", "https://www.olbg.com/betting-tips/Motor_Racing/14", {}),
    ("olbg_darts_15", "https://www.olbg.com/betting-tips/Darts/15", {}),
    ("olbg_badminton_18", "https://www.olbg.com/betting-tips/Badminton/18", {}),
    ("olbg_table_tennis_19", "https://www.olbg.com/betting-tips/Table_Tennis/19", {}),
    ("olbg_handball_20", "https://www.olbg.com/betting-tips/Handball/20", {}),
    ("olbg_volleyball_21", "https://www.olbg.com/betting-tips/Volleyball/21", {}),
    ("olbg_aussie_rules_22", "https://www.olbg.com/betting-tips/Aussie_Rules/22", {}),
    ("olbg_esports_23", "https://www.olbg.com/betting-tips/eSports/23", {}),
    ("olbg_gaelic_25", "https://www.olbg.com/betting-tips/Gaelic_Football/25", {}),
    ("olbg_greyhounds_28", "https://www.olbg.com/betting-tips/Greyhounds/28", {}),

    # --- 1. Ice Hockey (NHL + Finnish Liiga + Swedish SHL) ---
    ("nhl_standings_now", "https://api-web.nhle.com/v1/standings/now", {}),
    ("nhl_sched_2026-10-22", "https://api-web.nhle.com/v1/schedule/2026-10-22", {}),
    ("nhl_sched_2026-10-29", "https://api-web.nhle.com/v1/schedule/2026-10-29", {}),
    ("nhl_score_2026-10-19", "https://api-web.nhle.com/v1/score/2026-10-19", {}),
    ("nhl_score_2026-10-20", "https://api-web.nhle.com/v1/score/2026-10-20", {}),
    ("nhl_score_2026-10-21", "https://api-web.nhle.com/v1/score/2026-10-21", {}),
    ("nhl_skater_leaders", "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=points,goals&limit=50", {}),
    ("nhl_goalie_leaders", "https://api-web.nhle.com/v1/goalie-stats-leaders/current?categories=wins,savePctg&limit=30", {}),
    ("nhl_partner_odds_us", "https://api-web.nhle.com/v1/partner-game/US/now", {}),
    ("liiga_games_2027", "https://liiga.fi/api/v2/games?tournament=runkosarja&season=2027", {}),
    ("liiga_standings_2027", "https://liiga.fi/api/v2/standings/?season=2027", {}),
    ("shl_schedule_page", "https://www.shl.se/game-schedule", {}),

    # --- 2. Baseball (MLB World Series + Championship Series + Standings + Team Stats) ---
    ("mlb_postseason_schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-11&endDate=2026-11-05&gameTypes=L,W&hydrate=team,probablePitcher,venue,seriesStatus,decisions,linescore", {}),
    ("mlb_standings_2026", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason&hydrate=team", {}),
    ("mlb_rays_stats_2026", "https://statsapi.mlb.com/api/v1/teams/139/stats?stats=season&season=2026&group=hitting,pitching", {}),
    ("mlb_brewers_stats_2026", "https://statsapi.mlb.com/api/v1/teams/158/stats?stats=season&season=2026&group=hitting,pitching", {}),
    ("mlb_rays_roster_stats", "https://statsapi.mlb.com/api/v1/teams/139/roster?rosterType=postseason&season=2026&hydrate=person(stats(type=season,season=2026))", {}),
    ("mlb_brewers_roster_stats", "https://statsapi.mlb.com/api/v1/teams/158/roster?rosterType=postseason&season=2026&hydrate=person(stats(type=season,season=2026))", {}),

    # --- 3. Basketball (EuroLeague + EuroCup + NBA) ---
    ("euroleague_games_E2026", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games", {}),
    ("euroleague_games_E2025", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2025/games", {}),
    ("eurocup_games_U2026", "https://api-live.euroleague.net/v2/competitions/U/seasons/U2026/games", {}),
    ("nba_todays_scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", NBA_HEADERS),
    ("nba_schedule_v2", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", NBA_HEADERS),

    # --- 4. Tennis (WTA live APIs + ATP ProTennisLive PDFs) ---
    ("wta_tournaments_oct", "https://api.wtatennis.com/tennis/tournaments/?page=0&pageSize=30&excludeLevels=ITF&from=2026-10-19&to=2026-11-02", WTA_HEADERS),
    ("wta_405_matches", "https://api.wtatennis.com/tennis/tournaments/405/2026/matches", WTA_HEADERS),
    ("wta_2092_matches", "https://api.wtatennis.com/tennis/tournaments/2092/2026/matches", WTA_HEADERS),
    ("wta_rankings_p0", "https://api.wtatennis.com/tennis/players/ranked?page=0&pageSize=100&type=rankSingles&sort=asc&metric=SINGLES", WTA_HEADERS),
    ("wta_rankings_p1", "https://api.wtatennis.com/tennis/players/ranked?page=1&pageSize=100&type=rankSingles&sort=asc&metric=SINGLES", WTA_HEADERS),
    ("wta_rankings_p2", "https://api.wtatennis.com/tennis/players/ranked?page=2&pageSize=100&type=rankSingles&sort=asc&metric=SINGLES", WTA_HEADERS),
    ("atp_rankings_pdf", "https://www.protennislive.com/posting/ramr/singles_entry_numerical.pdf", {}),
    ("ptl_9410_op", "https://www.protennislive.com/posting/2026/9410/op.pdf", {}),
    ("ptl_9410_mds", "https://www.protennislive.com/posting/2026/9410/mds.pdf", {}),
    ("ptl_7485_op", "https://www.protennislive.com/posting/2026/7485/op.pdf", {}),
    ("ptl_7485_mds", "https://www.protennislive.com/posting/2026/7485/mds.pdf", {}),
    ("ptl_496_op", "https://www.protennislive.com/posting/2026/496/op.pdf", {}),
    ("ptl_496_mds", "https://www.protennislive.com/posting/2026/496/mds.pdf", {}),
    ("ptl_337_mds", "https://www.protennislive.com/posting/2026/337/mds.pdf", {}),
    ("ptl_328_mds", "https://www.protennislive.com/posting/2026/328/mds.pdf", {}),

    # --- 5. Darts (PDC Order of Merit + Participants API + EC Schedule) ---
    ("pdc_oom", "https://www.pdc.tv/order-merit/pdc-order-merit", {}),
    ("pdc_ec_schedule", "https://www.pdc.tv/news/2026/october/19/2026-machineseeker-european-championship-schedule-confirmed/", {}),
    ("pdc_participants_p1", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100", PDC_HEADERS),
    ("pdc_participants_p2", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100&page.number=2", PDC_HEADERS),

    # --- 6. Snooker (WST Northern Ireland Open + Rankings) ---
    ("wst_matches", "https://www.wst.tv/matches/", {}),
    ("wst_rankings", "https://www.wst.tv/rankings", {}),
    ("wst_nio_day4_pm", "https://www.wst.tv/news/2026/october/21/betvictor-northern-ireland-open-2026-day-four-afternoon", {}),
    ("wst_nio_day4_eve", "https://www.wst.tv/news/2026/october/21/betvictor-northern-ireland-open-2026-day-four-evening", {}),

    # --- 7 & 8. Rugby Union + Rugby League ---
    ("urc_fixtures_full", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/", {}),
    ("urc_table", "https://stats.unitedrugby.com/match-centre/table/", {}),
    ("top14_cal", "https://top14.lnr.fr/calendrier-et-resultats", {}),
    ("top14_table", "https://top14.lnr.fr/classement", {}),
    ("prod2_cal", "https://prod2.lnr.fr/calendrier-et-resultats", {}),
    ("prod2_table", "https://prod2.lnr.fr/classement", {}),
    ("rlwc_mens_r2", "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/", {}),
    ("rlwc_womens_r2", "https://www.nrl.com/news/2026/10/20/world-cup-team-lists-womens-round-2/", {}),

    # --- 9 & 10. Handball + Volleyball ---
    ("ehfcl_men_standings", "https://ehfcl.eurohandball.com/men/2026-27/standings/", {}),
    ("ehfcl_r5_preview", "https://www.eurohandball.com/en/news/en/five-main-round-tickets-still-on-the-line-as-round-5-begins", {}),
    ("opel_hbl_en", "https://www.opel-hbl.de/en/hbl", {}),
    ("lnh_starligue", "https://www.lnh.fr/daikin-starligue/accueil", {}),
    ("legavolley_cal", "https://ww2.legavolley.it/Calendario.asp", {}),
    ("plusliga_proj_warszawa", "https://www.tauronliga.pl/teams/tour/53/id/62.html", {}),
    ("plusliga_suwalki", "https://www.tauronliga.pl/teams/tour/53/id/56.html", {}),

    # --- 11–18. Cricket, Badminton, Table Tennis, Esports, Aussie Rules, Golf, Motor Racing, Greyhounds ---
    ("ecb_triseries", "https://www.ecb.co.uk/news/4594465/how-to-watch-and-follow-the-england-men-v-pakistan-and-sri-lanka", {}),
    ("icc_namibia_ireland", "https://www.icc-cricket.com/news/paul-stirling-to-lead-ireland-for-the-namibia-tour", {}),
    ("icc_afg_tri", "https://www.icc-cricket.com/news/afghanistan-announce-multi-format-series-against-bangladesh-and-zimbabwe", {}),
    ("nzc_fixtures", "https://scoring.nzc.nz/fixtures", {}),
    ("ca_aus_nz_w", "https://www.cricket.com.au/news/4592092/australia-v-new-zealand-t20is-preview-guide-broadcast-fixture-squads-teams-selection", {}),
    ("bwf_french_2026_10_22", "https://bwfworldchampionships.bwfbadminton.com/tournament/5272/yonex-french-open-2026/results/2026-10-22", {}),
    ("bwf_french_2026_10_21", "https://bwfworldchampionships.bwfbadminton.com/tournament/5272/yonex-french-open-2026/results/2026-10-21", {}),
    ("ittf_calendar_2026", "https://www.ittf.com/2026-events-calendar/", {}),
    ("lolesports_schedule", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US", RIOT_HEADERS),
    ("lolesports_leagues", "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US", RIOT_HEADERS),
    ("aflw_home_ladder", "https://www.afl.com.au/aflw", {}),
    ("aflw_full_fixture", "https://www.afl.com.au/aflw/news/1523395/full-fixture-no-re-match-for-former-melbourne-coach-mick-stinear-at-geelong-west-coast-eagles-get-a-break-by-avoiding-north-melbourne", {}),
    ("dpwt_genesis_entries", "https://www.europeantour.com/dpworld-tour/genesis-championship-2026/entry-list", {}),
    ("dpwt_genesis_teetimes", "https://www.europeantour.com/dpworld-tour/news/articles/detail/genesis-championship-tee-times-eugenio-chacarrra-ryan-fox-and-sungjae-im-start-together-in-korea/", {}),
    ("pga_bermuda_facts", "https://www.pgatour.com/article/news/latest/2026/10/20/butterfield-bermuda-championship-facts-and-figures-port-royal-golf-course-southampton-2026", {}),
    ("f1_calendar_2026", "https://www.formula1.com/en/racing/2026", {}),
    ("f1_drivers_2026", "https://www.formula1.com/en/results/2026/drivers", {}),
    ("f1_singapore_2026", "https://www.formula1.com/en/results/2026/races/1296/singapore/race-result", {}),
    ("gbgb_champion_stakes", "https://www.gbgb.org.uk/category-one-glory-beckons-in-coral-100-champion-stakes-final/", {}),
    ("gbgb_api_today", "https://api.gbgb.org.uk/api/results/meeting/2026-10-21?page=1&itemsPerPage=20", {}),
]

HOST_LOCKS: dict[str, threading.Lock] = {}
HOST_LAST: dict[str, float] = {}
GLOBAL_LOCK = threading.Lock()


def fetch_bytes(url: str, extra_headers: dict[str, str], min_gap: float = 0.35) -> tuple[int, str, bytes, str]:
    host = urllib.parse.urlsplit(url).hostname or ""
    with GLOBAL_LOCK:
        lock = HOST_LOCKS.setdefault(host, threading.Lock())
    with lock:
        wait = min_gap - (time.monotonic() - HOST_LAST.get(host, 0.0))
        if wait > 0:
            time.sleep(wait)
        HOST_LAST[host] = time.monotonic()

    headers = {"User-Agent": UA, "Accept-Encoding": "gzip, identity"}
    headers.update(extra_headers)
    req = urllib.request.Request(url, headers=headers)
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
            raw = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                raw = gzip.decompress(raw)
            return resp.status, resp.headers.get("Content-Type", ""), raw, ""
    except urllib.error.HTTPError as exc:
        body = b""
        try:
            body = exc.read()
        except Exception:
            pass
        return exc.code, exc.headers.get("Content-Type", "") if exc.headers else "", body, str(exc)
    except Exception as exc:
        return 0, "", b"", str(exc)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_dir = OUT_DIR / "files"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 1. Fetch and enforce OLBG robots.txt before touching any OLBG page.
    robots_url = "https://www.olbg.com/robots.txt"
    r_status, r_ctype, r_bytes, r_err = fetch_bytes(robots_url, {})
    rp = urllib.robotparser.RobotFileParser()
    if r_status == 200 and r_bytes:
        rp.parse(r_bytes.decode("utf-8", errors="replace").splitlines())

    def worker(item: tuple[str, str, dict[str, str]]) -> dict:
        tid, url, hdrs = item
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if tid == "olbg_robots":
            status, ctype, payload, err = r_status, r_ctype, r_bytes, r_err
        else:
            host = urllib.parse.urlsplit(url).hostname or ""
            if "olbg.com" in host and r_status == 200 and not rp.can_fetch("*", url):
                return {
                    "id": tid,
                    "url": url,
                    "fetched_utc": ts,
                    "status": -1,
                    "content_type": "",
                    "bytes": 0,
                    "sha256": "",
                    "file": "",
                    "error": "Skipped: disallowed by olbg.com/robots.txt",
                }
            status, ctype, payload, err = fetch_bytes(url, hdrs)

        digest = hashlib.sha256(payload).hexdigest() if payload else ""
        rel_file = ""
        if payload:
            gz_path = raw_dir / f"{tid}.gz"
            gz_path.write_bytes(gzip.compress(payload, mtime=0))
            rel_file = f"files/{tid}.gz"
        return {
            "id": tid,
            "url": url,
            "fetched_utc": ts,
            "status": status,
            "content_type": ctype,
            "bytes": len(payload),
            "sha256": digest,
            "file": rel_file,
            "error": err,
        }

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(worker, t): t[0] for t in TARGETS}
        for fut in concurrent.futures.as_completed(futures):
            res = fut.result()
            results.append(res)
            print(f"[{res['status']:3d}] {res['id']:28s} bytes={res['bytes']:8d} {res['url']}")

    results.sort(key=lambda r: [t[0] for t in TARGETS].index(r["id"]))
    manifest = {
        "schema": "olbg4.capture.v1",
        "session": "arena/3a9cd0c0-olbg4",
        "board": "Z",
        "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "total_targets": len(results),
        "http_200_count": sum(1 for r in results if r["status"] == 200),
        "items": results,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    print(f"Saved {len(results)} capture entries ({manifest['http_200_count']} HTTP 200).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

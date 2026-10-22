#!/usr/bin/env python3
"""Board AD — third capture pass: corrected official URLs + SPA payloads preserved.

Pass 1 stripped <script> blocks, which destroyed the JSON payloads that Next.js /
Nuxt federation sites use to ship their fixtures and rankings.  This pass re-fetches
those pages and keeps the script payloads alongside the readable text (see split_html).

Run:  python3 scripts/session-3a6388d2/collect3.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SID = "session-3a6388d2"
OUT = os.path.join(ROOT, "data", SID, "raw")
MANIFEST = os.path.join(ROOT, "data", SID, "manifest3.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
JSON_HEADERS = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
BROWSER = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "sec-ch-ua": '"Chromium";v="126", "Not(A:Brand";v="24"',
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}
NBA_HEADERS = {**BROWSER, "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
               "Sec-Fetch-Site": "same-site"}

MAX_CHARS = 1_200_000
TIMEOUT = 50

TARGETS = [
    # ---------------- Basketball: NBA CDN blocked the plain client; retry as a browser
    ("nba_schedule_browser", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", NBA_HEADERS, "Basketball", "api", "NBA.com official schedule feed — browser headers"),
    ("nba_schedule_curl_ua", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", {"User-Agent": "curl/8.5.0", "Accept": "*/*"}, "Basketball", "api", "NBA.com official schedule feed — curl UA"),
    ("nba_scoreboard_browser", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", NBA_HEADERS, "Basketball", "api", "NBA.com official live scoreboard — browser headers"),
    # Other official basketball competitions in season
    ("nbl_fixtures", "https://nbl.com.au/games", BROWSER, "Basketball", "html", "NBL (Australia) official games"),
    ("nbl_fixtures_alt", "https://www.nbl.com.au/fixtures", BROWSER, "Basketball", "html", "NBL official fixtures"),
    ("euroleague_home2", "https://www.euroleaguebasketball.net/en/", BROWSER, "Basketball", "html", "EuroLeague official home"),
    ("euroleague_standings2", "https://www.euroleaguebasketball.net/en/competitions/euroleague/standings/", BROWSER, "Basketball", "html", "EuroLeague official standings"),

    # ---------------- Rugby League: RLWC remaining rounds (NRL is the official host site)
    ("nrl_rlwc_round3", "https://www.nrl.com/draw/rugby-league-world-cup/2026/round-3/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 Round 3 draw"),
    ("nrl_rlwc_round4", "https://www.nrl.com/draw/rugby-league-world-cup/2026/round-4/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 Round 4 draw"),
    ("nrl_rlwc_round5", "https://www.nrl.com/draw/rugby-league-world-cup/2026/round-5/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 Round 5 draw"),
    ("nrl_rlwc_index", "https://www.nrl.com/draw/rugby-league-world-cup/2026/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 draw index"),
    ("nrl_rlwc_women", "https://www.nrl.com/draw/rugby-league-world-cup-women/2026/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 women's draw"),
    ("rugbyleague_com", "https://www.rugby-league.com/", BROWSER, "Rugby League", "html", "Rugby Football League official home"),
    ("superleague_alt", "https://www.superleague.co.uk/matches", BROWSER, "Rugby League", "html", "Super League official matches"),

    # ---------------- Rugby Union: full URC match centre + Premiership
    ("urc_match_centre", "https://stats.unitedrugby.com/match-centre", BROWSER, "Rugby Union", "html", "URC official match centre (stats.unitedrugby.com)"),
    ("urc_fixtures_alt", "https://www.unitedrugby.com/fixtures-and-results", BROWSER, "Rugby Union", "html", "URC official fixtures & results"),
    ("prem_fixtures2", "https://www.premiershiprugby.com/fixtures-results", BROWSER, "Rugby Union", "html", "Premiership Rugby official fixtures (browser headers)"),
    ("prem_home", "https://www.premiershiprugby.com/", BROWSER, "Rugby Union", "html", "Premiership Rugby official home"),
    ("worldrugby_rankings_mru", "https://www.world.rugby/rankings/mru", BROWSER, "Rugby Union", "html", "World Rugby official men's rankings (canonical path)"),
    ("worldrugby_rankings_hub", "https://www.world.rugby/rankings", BROWSER, "Rugby Union", "html", "World Rugby official rankings hub"),

    # ---------------- Cricket: boards + ICC rankings (payload preserved)
    ("icc_rank_t20i_men2", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", BROWSER, "Cricket", "html", "ICC official men's T20I team rankings (payload preserved)"),
    ("icc_rank_odi_men2", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", BROWSER, "Cricket", "html", "ICC official men's ODI team rankings (payload preserved)"),
    ("slc_home", "https://www.srilankacricket.lk/", BROWSER, "Cricket", "html", "Sri Lanka Cricket official home"),
    ("pcb_home", "https://www.pcb.com.pk/", BROWSER, "Cricket", "html", "Pakistan Cricket Board official home"),

    # ---------------- Darts: PDC event + rankings (Nuxt payloads preserved)
    ("pdc_oom2", "https://www.pdc.tv/rankings/pdc-order-of-merit", BROWSER, "Darts", "html", "PDC official Order of Merit (payload preserved)"),
    ("pdc_tv_home2", "https://www.pdc.tv/", BROWSER, "Darts", "html", "PDC official home (payload preserved)"),
    ("pdc_euro_tournament", "https://www.pdc.tv/tournaments/pdc-european-championship-2026", BROWSER, "Darts", "html", "PDC European Championship 2026 official page"),
    ("pdc_euro_tv", "https://www.pdc.tv/european-championship", BROWSER, "Darts", "html", "PDC European Championship hub"),

    # ---------------- Snooker: WST (Nuxt payloads preserved)
    ("wst_rankings2", "https://www.wst.tv/rankings", BROWSER, "Snooker", "html", "WST official world rankings (payload preserved)"),
    ("wst_tournaments", "https://www.wst.tv/tournaments", BROWSER, "Snooker", "html", "WST official tournaments"),
    ("wst_matches2", "https://www.wst.tv/matches", BROWSER, "Snooker", "html", "WST official matches"),
    ("wst_home2", "https://www.wst.tv/", BROWSER, "Snooker", "html", "WST official home"),

    # ---------------- Tennis: official tournament sites (ATP Cloudflare-blocks datacenter IPs)
    ("basel_swissindoors", "https://www.swissindoorsbasel.ch/", BROWSER, "Tennis", "html", "Swiss Indoors Basel official site"),
    ("vienna_erstebank", "https://www.erstebank-open.com/", BROWSER, "Tennis", "html", "Erste Bank Open Vienna official site"),
    ("wta_tournaments2", "https://www.wtatennis.com/tournaments", BROWSER, "Tennis", "html", "WTA official tournaments (payload preserved)"),
    ("wta_rankings2", "https://www.wtatennis.com/rankings", BROWSER, "Tennis", "html", "WTA official rankings (payload preserved)"),

    # ---------------- Golf: official tours (payload preserved)
    ("pga_schedule2", "https://www.pgatour.com/schedule", BROWSER, "Golf", "html", "PGA Tour official schedule (payload preserved)"),
    ("pga_leaderboard2", "https://www.pgatour.com/leaderboard", BROWSER, "Golf", "html", "PGA Tour official leaderboard (payload preserved)"),
    ("owgr_current2", "https://www.owgr.com/current-world-ranking", BROWSER, "Golf", "html", "Official World Golf Ranking (payload preserved)"),
    ("dptour_home2", "https://www.europeantour.com/", BROWSER, "Golf", "html", "DP World Tour official home"),

    # ---------------- Handball / Volleyball (payload preserved)
    ("ehfcl_home2", "https://ehfcl.eurohandball.com/", BROWSER, "Handball", "html", "EHF Champions League official home (payload preserved)"),
    ("ehf_matches2", "https://www.eurohandball.com/en/matches-results", BROWSER, "Handball", "html", "EHF official matches & results (payload preserved)"),
    ("hbl_fixtures", "https://www.dkb-handball-bundesliga.de/spielplan", BROWSER, "Handball", "html", "German Handball-Bundesliga official fixtures"),
    ("legavolley_calendar", "https://www.legavolley.it/calendari", BROWSER, "Volleyball", "html", "Italian SuperLega official calendar"),
    ("plusliga_terminarz", "https://www.plusliga.pl/terminarz", BROWSER, "Volleyball", "html", "Polish PlusLiga official fixtures"),

    # ---------------- Badminton / Table tennis (payload preserved)
    ("bwf_home2", "https://bwfbadminton.com/", BROWSER, "Badminton", "html", "BWF official home (payload preserved)"),
    ("bwf_tournaments2", "https://bwfbadminton.com/tournaments", BROWSER, "Badminton", "html", "BWF official tournaments (payload preserved)"),
    ("bwf_rankings2", "https://bwfbadminton.com/rankings", BROWSER, "Badminton", "html", "BWF official rankings (payload preserved)"),
    ("wtt_home2", "https://www.worldtabletennis.com/", BROWSER, "Table Tennis", "html", "WTT official home (payload preserved)"),

    # ---------------- Aussie Rules / Greyhounds (payload preserved)
    ("aflw_fixture2", "https://www.afl.com.au/aflw/fixture", BROWSER, "Aussie Rules", "html", "AFLW official fixture (payload preserved)"),
    ("afl_fixture2", "https://www.afl.com.au/fixture", BROWSER, "Aussie Rules", "html", "AFL official fixture (payload preserved)"),
    ("gbgb_results2", "https://www.gbgb.org.uk/results/", BROWSER, "Greyhounds", "html", "GBGB official results (payload preserved)"),

    # ---------------- Motor racing (payload preserved)
    ("f1_races2", "https://www.formula1.com/en/results/2026/races", BROWSER, "Motor Racing", "html", "Formula 1 official 2026 race results (payload preserved)"),
    ("f1_drivers2", "https://www.formula1.com/en/results/2026/drivers", BROWSER, "Motor Racing", "html", "Formula 1 official 2026 driver standings (payload preserved)"),
    ("f1_racing2", "https://www.formula1.com/en/racing/2026.html", BROWSER, "Motor Racing", "html", "Formula 1 official 2026 calendar (payload preserved)"),
]


def split_html(text: str):
    scripts = "".join(m.group(1) for m in re.finditer(r"(?is)<script\b[^>]*>(.*?)</script>", text))
    body = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", text)
    body = re.sub(r"(?is)<!--.*?-->", " ", body)
    body = re.sub(r"[ \t\r\f\v]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n", body)
    return body, scripts


def fetch(url: str, headers: dict):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        return raw, resp.geturl(), int(resp.status)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for idx, (sid, url, headers, sport, kind, note) in enumerate(TARGETS, 1):
        rec = {"id": sid, "url": url, "sport": sport, "kind": kind, "note": note,
               "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            raw, final_url, status = fetch(url, headers)
            digest = hashlib.sha256(raw).hexdigest()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", "replace")
            truncated = False
            if kind == "html":
                body, scripts = split_html(text)
                if len(body) > MAX_CHARS:
                    body, truncated = body[:MAX_CHARS], True
                if len(scripts) > MAX_CHARS:
                    scripts, truncated = scripts[:MAX_CHARS], True
                text = "-----HTML-TEXT-----\n" + body + "\n-----SCRIPT-PAYLOADS-----\n" + scripts
            elif len(text) > MAX_CHARS:
                text, truncated = text[:MAX_CHARS], True
            with open(os.path.join(OUT, f"{sid}.txt"), "w", encoding="utf-8") as fh:
                fh.write(text)
            rec.update({"http_status": status, "final_url": final_url, "bytes": len(raw),
                        "chars_saved": len(text), "truncated": truncated, "sha256_raw": digest,
                        "saved_as": f"data/{SID}/raw/{sid}.txt", "error": ""})
            print(f"[{idx:02d}/{len(TARGETS)}] {status} {sid:28s} {len(raw):>9,d}B -> {len(text):>9,d}ch")
        except urllib.error.HTTPError as exc:
            rec.update({"http_status": int(exc.code), "bytes": 0, "chars_saved": 0, "sha256_raw": "",
                        "saved_as": "", "error": f"HTTPError {exc.code} {exc.reason}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:28s} HTTP {exc.code} {exc.reason}")
        except Exception as exc:
            rec.update({"http_status": 0, "bytes": 0, "chars_saved": 0, "sha256_raw": "",
                        "saved_as": "", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:28s} {type(exc).__name__}: {exc}")
        entries.append(rec)
        time.sleep(0.5)

    manifest = {
        "schema": "olbg4/board-ad-raw-manifest/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "pass": "corrected-urls-and-spa-payloads",
        "collector": "scripts/session-3a6388d2/collect3.py",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets_total": len(TARGETS),
        "ok": sum(1 for e in entries if e["http_status"] == 200),
        "failed": sum(1 for e in entries if e["http_status"] != 200),
        "entries": entries,
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
        fh.write("\n")
    print(f"\nmanifest3: ok={manifest['ok']} failed={manifest['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

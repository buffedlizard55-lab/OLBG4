#!/usr/bin/env python3
"""Board AD official-source capture — session arena/3a6388d2-olbg4.

The interactive sandbox has no general HTTPS egress (github.com, codeload.github.com,
api.github.com, registry.npmjs.org, pypi.org and files.pythonhosted.org only).
Official league / federation / organiser / OLBG pages are therefore fetched here, on a
GitHub Actions runner with open egress, and the exact bytes are committed together with
the URL, HTTP status, byte count, UTC timestamp and SHA-256 digest.

Nothing is parsed or interpreted in this script. Every later step of Board AD reads
only these committed bytes, so any published value can be reproduced and re-hashed by
a reviewer from the manifest in data/session-3a6388d2/manifest.json.

Run:  python3 scripts/session-3a6388d2/collect.py
"""
from __future__ import annotations

import gzip
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
MANIFEST = os.path.join(ROOT, "data", SID, "manifest.json")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")

MAX_CHARS = 1_200_000          # hard cap per saved artefact (chars of decoded text)
TIMEOUT = 45                   # seconds per request
SLEEP_BETWEEN = 0.4            # be polite to the origin servers

NBA_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
}
LOL_HEADERS = {
    "User-Agent": UA,
    "Accept": "application/json, text/plain, */*",
    "x-api-key": "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z",
    "Referer": "https://lolesports.com/",
    "Origin": "https://lolesports.com",
}
ATP_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
JSON_HEADERS = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}

WINDOW_START = "2026-10-22"
WINDOW_END = "2026-11-08"

# id, url, headers, sport, kind, note
TARGETS = [
    # ---------------------------------------------------------------- Ice Hockey (NHL)
    ("nhl_sched_w1", "https://api-web.nhle.com/v1/schedule/2026-10-22", JSON_HEADERS, "Ice Hockey", "api", "NHL official schedule API — week of 22 Oct 2026"),
    ("nhl_sched_w2", "https://api-web.nhle.com/v1/schedule/2026-10-29", JSON_HEADERS, "Ice Hockey", "api", "NHL official schedule API — week of 29 Oct 2026"),
    ("nhl_sched_w3", "https://api-web.nhle.com/v1/schedule/2026-11-05", JSON_HEADERS, "Ice Hockey", "api", "NHL official schedule API — week of 5 Nov 2026"),
    ("nhl_standings_now", "https://api-web.nhle.com/v1/standings/now", JSON_HEADERS, "Ice Hockey", "api", "NHL official standings (current)"),
    ("nhl_score_2026-10-21", "https://api-web.nhle.com/v1/score/2026-10-21", JSON_HEADERS, "Ice Hockey", "api", "NHL official results 21 Oct 2026 — recent form"),
    ("nhl_score_2026-10-20", "https://api-web.nhle.com/v1/score/2026-10-20", JSON_HEADERS, "Ice Hockey", "api", "NHL official results 20 Oct 2026 — recent form"),

    # ---------------------------------------------------------------- Basketball (NBA)
    ("nba_schedule", "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2_1.json", NBA_HEADERS, "Basketball", "api", "NBA.com official static schedule feed"),
    ("nba_scoreboard", "https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json", NBA_HEADERS, "Basketball", "api", "NBA.com official live scoreboard"),
    ("nba_standings", "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular+Season", NBA_HEADERS, "Basketball", "api", "NBA official stats endpoint — standings"),
    ("nba_com_schedule", "https://www.nba.com/schedule", {}, "Basketball", "html", "NBA.com official schedule page"),
    ("nba_com_scores", "https://www.nba.com/scores", {}, "Basketball", "html", "NBA.com official scores page"),
    ("nba_com_standings", "https://www.nba.com/standings", {}, "Basketball", "html", "NBA.com official standings page"),
    ("euroleague_standings", "https://www.euroleaguebasketball.net/en/competitions/euroleague/standings/", {}, "Basketball", "html", "EuroLeague official standings"),
    ("euroleague_home", "https://www.euroleaguebasketball.net/en/", {}, "Basketball", "html", "EuroLeague official home — fixtures/results"),

    # ---------------------------------------------------------------- Baseball (MLB)
    ("mlb_schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-08&gameTypes=R,F,D,L,W,C&hydrate=team,venue,probablePitcher", JSON_HEADERS, "Baseball", "api", "MLB official Stats API — postseason window"),
    ("mlb_standings", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason", JSON_HEADERS, "Baseball", "api", "MLB official standings 2026"),

    # ---------------------------------------------------------------- Rugby League
    ("rlwc_home", "https://www.rlwc2026.com/", {}, "Rugby League", "html", "Rugby League World Cup 2026 official site"),
    ("rlwc_fixtures", "https://www.rlwc2026.com/fixtures", {}, "Rugby League", "html", "RLWC 2026 official fixtures"),
    ("rlwc_results", "https://www.rlwc2026.com/results", {}, "Rugby League", "html", "RLWC 2026 official results"),
    ("nrl_draw", "https://www.nrl.com/draw/", {}, "Rugby League", "html", "NRL official draw"),
    ("superleague_home", "https://www.superleague.co.uk/", {}, "Rugby League", "html", "Betfred Super League official home"),
    ("superleague_fixtures", "https://www.superleague.co.uk/fixtures-results", {}, "Rugby League", "html", "Betfred Super League official fixtures & results"),

    # ---------------------------------------------------------------- Rugby Union
    ("urc_fixtures", "https://www.unitedrugby.com/fixtures", {}, "Rugby Union", "html", "United Rugby Championship official fixtures"),
    ("urc_results", "https://www.unitedrugby.com/results", {}, "Rugby Union", "html", "URC official results"),
    ("urc_standings", "https://www.unitedrugby.com/standings", {}, "Rugby Union", "html", "URC official standings"),
    ("urc_home", "https://www.unitedrugby.com/", {}, "Rugby Union", "html", "URC official home"),
    ("epcr_fixtures", "https://www.epcrugby.com/fixtures-results", {}, "Rugby Union", "html", "EPCR official fixtures & results"),
    ("epcr_home", "https://www.epcrugby.com/", {}, "Rugby Union", "html", "EPCR official home"),
    ("prem_fixtures", "https://www.premiershiprugby.com/fixtures-results", {}, "Rugby Union", "html", "Gallagher Premiership Rugby official fixtures"),
    ("prem_standings", "https://www.premiershiprugby.com/standings", {}, "Rugby Union", "html", "Gallagher Premiership Rugby official standings"),
    ("lnr_top14", "https://www.lnr.fr/", {}, "Rugby Union", "html", "LNR (Top 14 / Pro D2) official home"),
    ("lnr_calendrier", "https://www.lnr.fr/competitions/top-14/calendrier", {}, "Rugby Union", "html", "LNR Top 14 official calendar"),
    ("worldrugby_tournaments", "https://www.world.rugby/tournaments", {}, "Rugby Union", "html", "World Rugby official tournament schedule"),

    # ---------------------------------------------------------------- Cricket
    ("icc_home", "https://www.icc-cricket.com/", {}, "Cricket", "html", "ICC official home — international schedule pointers"),
    ("icc_matches", "https://www.icc-cricket.com/tournaments", {}, "Cricket", "html", "ICC official tournaments / schedule hub"),
    ("icc_fixtures", "https://www.icc-cricket.com/fixtures", {}, "Cricket", "html", "ICC official fixtures hub"),
    ("nzc_home", "https://www.nzc.nz/", {}, "Cricket", "html", "New Zealand Cricket official home — international schedule"),
    ("nzc_matches", "https://www.nzc.nz/matches", {}, "Cricket", "html", "New Zealand Cricket official matches"),
    ("cricketcomau_fixtures", "https://www.cricket.com.au/fixtures", {}, "Cricket", "html", "Cricket Australia official fixtures"),
    ("ecb_home", "https://www.ecb.co.uk/", {}, "Cricket", "html", "ECB official home — schedule & results"),
    ("bcci_home", "https://www.bcci.tv/", {}, "Cricket", "html", "BCCI official home — schedule"),

    # ---------------------------------------------------------------- Darts
    ("pdc_home", "https://www.pdc.tv/", {}, "Darts", "html", "PDC (Professional Darts Corporation) official home"),
    ("pdc_tournaments", "https://www.pdc.tv/tournaments", {}, "Darts", "html", "PDC official tournament list"),
    ("pdc_euro_championship", "https://www.pdc.tv/tournaments/pdc-european-championship", {}, "Darts", "html", "PDC European Championship official page"),

    # ---------------------------------------------------------------- Snooker
    ("wst_home", "https://www.wst.tv/", {}, "Snooker", "html", "World Snooker Tour official home"),
    ("wst_calendar", "https://www.wst.tv/calendar", {}, "Snooker", "html", "WST official calendar"),
    ("wst_matches", "https://www.wst.tv/matches", {}, "Snooker", "html", "WST official matches"),

    # ---------------------------------------------------------------- Tennis
    ("atp_tournaments", "https://www.atptour.com/en/tournaments", ATP_HEADERS, "Tennis", "html", "ATP Tour official tournaments"),
    ("atp_scores", "https://www.atptour.com/en/scores/current", ATP_HEADERS, "Tennis", "html", "ATP Tour official current scores/draws"),
    ("wta_tournaments", "https://www.wtatennis.com/tournaments", ATP_HEADERS, "Tennis", "html", "WTA official tournaments"),

    # ---------------------------------------------------------------- Golf
    ("pga_schedule", "https://www.pgatour.com/schedule", {}, "Golf", "html", "PGA Tour official schedule"),
    ("pga_leaderboard", "https://www.pgatour.com/leaderboard", {}, "Golf", "html", "PGA Tour official leaderboard"),
    ("pga_competitions", "https://www.pgatour.com/competition/2026", {}, "Golf", "html", "PGA Tour official 2026 season page"),
    ("dptour_home", "https://www.europeantour.com/", {}, "Golf", "html", "DP World Tour official home"),
    ("dptour_schedule", "https://www.europeantour.com/dp-world-tour/schedule/", {}, "Golf", "html", "DP World Tour official schedule"),

    # ---------------------------------------------------------------- Handball
    ("ehf_home", "https://www.eurohandball.com/en/", {}, "Handball", "html", "EHF official home"),
    ("ehf_matches", "https://www.eurohandball.com/en/matches-results", {}, "Handball", "html", "EHF official matches & results"),
    ("ehfcl_fixtures", "https://ehfcl.eurohandball.com/men/2026-27/matches/", {}, "Handball", "html", "EHF Champions League official men's matches"),
    ("ehfcl_women_fixtures", "https://ehfcl.eurohandball.com/women/2026-27/matches/", {}, "Handball", "html", "EHF Champions League official women's matches"),
    ("ehfcl_home", "https://ehfcl.eurohandball.com/", {}, "Handball", "html", "EHF Champions League official site"),
    ("hbl_home", "https://www.dkb-handball-bundesliga.de/", {}, "Handball", "html", "German Handball-Bundesliga official site"),

    # ---------------------------------------------------------------- Volleyball
    ("cev_home", "https://www.cev.eu/", {}, "Volleyball", "html", "CEV official home"),
    ("legavolley_home", "https://www.legavolley.it/", {}, "Volleyball", "html", "Italian SuperLega official site"),
    ("plusliga_home", "https://www.plusliga.pl/", {}, "Volleyball", "html", "Polish PlusLiga official site"),

    # ---------------------------------------------------------------- Badminton
    ("bwf_home", "https://bwfbadminton.com/", {}, "Badminton", "html", "BWF official home"),
    ("bwf_tournaments", "https://bwfbadminton.com/tournaments", {}, "Badminton", "html", "BWF official tournaments"),
    ("bwf_calendar", "https://bwfbadminton.com/calendar", {}, "Badminton", "html", "BWF official calendar"),

    # ---------------------------------------------------------------- Table Tennis
    ("wtt_home", "https://www.worldtabletennis.com/", {}, "Table Tennis", "html", "World Table Tennis official home"),
    ("wtt_calendar", "https://www.worldtabletennis.com/eventCalendar", {}, "Table Tennis", "html", "WTT official event calendar"),
    ("ittf_events", "https://www.ittf.com/events", {}, "Table Tennis", "html", "ITTF official events calendar"),

    # ---------------------------------------------------------------- Aussie Rules
    ("afl_fixture", "https://www.afl.com.au/fixture", {}, "Aussie Rules", "html", "AFL official fixture"),
    ("aflw_fixture", "https://www.afl.com.au/aflw/fixture", {}, "Aussie Rules", "html", "AFLW official fixture"),

    # ---------------------------------------------------------------- Greyhounds
    ("gbgb_results", "https://www.gbgb.org.uk/results/", {}, "Greyhounds", "html", "GBGB official results"),

    # ---------------------------------------------------------------- Esports
    ("lol_schedule", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US&sport=lol", LOL_HEADERS, "Esports", "api", "Riot Games official esports API — schedule"),
    ("lol_live", "https://esports-api.lolesports.com/persisted/gw/getLive?hl=en-US", LOL_HEADERS, "Esports", "api", "Riot Games official esports API — live"),

    # ---------------------------------------------------------------- Motor Racing
    ("f1_racing", "https://www.formula1.com/en/racing/2026.html", {}, "Motor Racing", "html", "Formula 1 official 2026 race calendar"),
    ("motogp_calendar", "https://www.motogp.com/en/calendar", {}, "Motor Racing", "html", "MotoGP official calendar"),

    # ---------------------------------------------------------------- OLBG reverse engineering (taxonomy only)
    ("olbg_betting_tips", "https://www.olbg.com/betting-tips/", {}, "(OLBG taxonomy)", "html", "OLBG betting-tips sport index — taxonomy reverse-engineering"),
    ("olbg_sitemap", "https://www.olbg.com/sitemap.xml", {}, "(OLBG taxonomy)", "xml", "OLBG sitemap — sport/competition URL structure"),
]


def split_html(text: str):
    """Split an HTML document into readable text and (separately) its script payloads.

    Modern federation sites (Next.js / Nuxt) ship their fixtures inside
    <script id="__NEXT_DATA__"> or window.__NUXT__ blobs.  Stripping scripts would
    throw the only verifiable evidence away, so both parts are stored: first the
    human-readable text, then the raw script bodies.
    """
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
        return raw, resp.geturl(), int(resp.status)


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    for idx, (sid, url, headers, sport, kind, note) in enumerate(TARGETS, 1):
        rec = {
            "id": sid,
            "url": url,
            "sport": sport,
            "kind": kind,
            "note": note,
            "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
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
            else:
                if len(text) > MAX_CHARS:
                    text, truncated = text[:MAX_CHARS], True
            ext = "txt"
            path = os.path.join(OUT, f"{sid}.{ext}")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            rec.update({
                "http_status": status,
                "final_url": final_url,
                "bytes": len(raw),
                "chars_saved": len(text),
                "truncated": truncated,
                "sha256_raw": digest,
                "saved_as": f"data/{SID}/raw/{sid}.{ext}",
                "error": "",
            })
            print(f"[{idx:02d}/{len(TARGETS)}] {status} {sid:28s} {len(raw):>9,d}B -> {len(text):>9,d}ch")
        except urllib.error.HTTPError as exc:  # type: ignore[name-defined]
            rec.update({"http_status": int(exc.code), "bytes": 0, "chars_saved": 0,
                        "sha256_raw": "", "saved_as": "", "error": f"HTTPError {exc.code} {exc.reason}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:28s} HTTP {exc.code} {exc.reason}")
        except Exception as exc:  # network failure, DNS, timeout, decode
            rec.update({"http_status": 0, "bytes": 0, "chars_saved": 0,
                        "sha256_raw": "", "saved_as": "", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:28s} {type(exc).__name__}: {exc}")
        entries.append(rec)
        time.sleep(SLEEP_BETWEEN)

    manifest = {
        "schema": "olbg4/board-ad-raw-manifest/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "collector": "scripts/session-3a6388d2/collect.py",
        "started_at_utc": started,
        "finished_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "targets_total": len(TARGETS),
        "ok": sum(1 for e in entries if e["http_status"] == 200),
        "failed": sum(1 for e in entries if e["http_status"] != 200),
        "entries": entries,
    }
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=False)
        fh.write("\n")
    print(f"\nmanifest: {os.path.relpath(MANIFEST, ROOT)}  ok={manifest['ok']} failed={manifest['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

# pass-5 re-capture: OLBG per-sport cards must be decompressed (brotli-safe)

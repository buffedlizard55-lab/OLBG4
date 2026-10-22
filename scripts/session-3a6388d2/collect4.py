#!/usr/bin/env python3
"""Board AD — fourth capture pass: official standings / results needed as rating inputs.

Same architecture: the GitHub Actions runner fetches, we commit bytes + SHA-256 and
parse locally.  Targets here are the strength inputs for sports whose fixture list we
already captured (URC table, RLWC results, F1/MotoGP standings, NBA endpoints).

Run:  python3 scripts/session-3a6388d2/collect4.py
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
MANIFEST = os.path.join(ROOT, "data", SID, "manifest4.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
BROWSER = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "sec-ch-ua": '"Chromium";v="126", "Not(A:Brand";v="24"',
    "sec-ch-ua-platform": '"Windows"',
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none",
}
NBA_HEADERS = {**BROWSER, "Referer": "https://www.nba.com/", "Origin": "https://www.nba.com",
               "Sec-Fetch-Site": "same-site", "Accept": "application/json, text/plain, */*"}
MAX_CHARS = 1_200_000
TIMEOUT = 50

TARGETS = [
    ("urc_table_full", "https://stats.unitedrugby.com/match-centre/table/2026-27", BROWSER, "Rugby Union", "html", "URC official full league table 2026-27"),
    ("urc_results_full", "https://stats.unitedrugby.com/match-centre/results/2026-27", BROWSER, "Rugby Union", "html", "URC official results 2026-27"),
    ("nrl_rlwc_results_r1", "https://www.nrl.com/draw/rugby-league-world-cup/2026/round-1/", BROWSER, "Rugby League", "html", "NRL official RLWC 2026 Round 1 results"),
    ("nrl_results_page", "https://www.nrl.com/results/", BROWSER, "Rugby League", "html", "NRL official results"),
    ("nba_stats_standings", "https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27&SeasonType=Regular+Season", NBA_HEADERS, "Basketball", "api", "NBA official stats standings endpoint"),
    ("nba_scoreboardv3", "https://stats.nba.com/stats/scoreboardv3?GameDate=2026-10-23&LeagueID=00", NBA_HEADERS, "Basketball", "api", "NBA official stats scoreboard endpoint"),
    ("motogp_standings", "https://www.motogp.com/en/world-standing/2026", BROWSER, "Motor Racing", "html", "MotoGP official 2026 world standing"),
    ("motogp_riders", "https://www.motogp.com/en/riders/motogp", BROWSER, "Motor Racing", "html", "MotoGP official rider list"),
    ("f1_drivers_ssr", "https://www.formula1.com/en/results/2026/drivers", BROWSER, "Motor Racing", "html", "Formula 1 official 2026 driver standings"),
    ("wst_matches_alt", "https://www.wst.tv/matches-results", BROWSER, "Snooker", "html", "WST official matches & results"),
    ("legavolley_cal", "https://www.legavolley.it/calendario", BROWSER, "Volleyball", "html", "Italian SuperLega official calendar"),
    ("plusliga_calendar", "https://www.plusliga.pl/rozgrywki", BROWSER, "Volleyball", "html", "Polish PlusLiga official fixtures"),
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
            print(f"[{idx:02d}/{len(TARGETS)}] {status} {sid:26s} {len(raw):>9,d}B -> {len(text):>9,d}ch")
        except urllib.error.HTTPError as exc:
            rec.update({"http_status": int(exc.code), "bytes": 0, "chars_saved": 0, "sha256_raw": "",
                        "saved_as": "", "error": f"HTTPError {exc.code} {exc.reason}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:26s} HTTP {exc.code} {exc.reason}")
        except Exception as exc:
            rec.update({"http_status": 0, "bytes": 0, "chars_saved": 0, "sha256_raw": "",
                        "saved_as": "", "error": f"{type(exc).__name__}: {exc}"})
            print(f"[{idx:02d}/{len(TARGETS)}] ERR {sid:26s} {type(exc).__name__}: {exc}")
        entries.append(rec)
        time.sleep(0.6)

    manifest = {
        "schema": "olbg4/board-ad-raw-manifest/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "pass": "standings-and-results-inputs",
        "collector": "scripts/session-3a6388d2/collect4.py",
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
    print(f"\nmanifest4: ok={manifest['ok']} failed={manifest['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

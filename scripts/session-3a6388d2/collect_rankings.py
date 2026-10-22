#!/usr/bin/env python3
"""Board AD — second capture pass: official governing-body ranking / standings pages.

Same architecture as collect.py (GitHub Actions runner with open egress, exact bytes
committed with URL + HTTP status + SHA-256). These pages supply the *verified strength
inputs* used later to originate our own lines for sports that have no fixture API.

Run:  python3 scripts/session-3a6388d2/collect_rankings.py
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
MANIFEST = os.path.join(ROOT, "data", SID, "manifest_rankings.json")

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
JSON_HEADERS = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
ATP_HEADERS = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.9"}
MAX_CHARS = 900_000
TIMEOUT = 45

TARGETS = [
    # Rugby union — World Rugby (governing body) official men's rankings
    ("wr_rankings_men", "https://www.world.rugby/tournaments/rankings/mru", {}, "Rugby Union", "html", "World Rugby official men's international rankings"),
    # Rugby league — International Rugby League (governing body) official rankings
    ("irl_rankings_men", "https://www.intrl.co.uk/rankings/", {}, "Rugby League", "html", "IRL official men's world rankings"),
    ("irl_rankings_women", "https://www.intrl.co.uk/womens-rankings/", {}, "Rugby League", "html", "IRL official women's world rankings"),

    # Cricket — ICC (governing body) official team rankings
    ("icc_rank_t20i_men", "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i", {}, "Cricket", "html", "ICC official men's T20I team rankings"),
    ("icc_rank_odi_men", "https://www.icc-cricket.com/rankings/mens/team-rankings/odi", {}, "Cricket", "html", "ICC official men's ODI team rankings"),
    ("icc_rank_test_men", "https://www.icc-cricket.com/rankings/mens/team-rankings/test", {}, "Cricket", "html", "ICC official men's Test team rankings"),

    # Darts — PDC official Order of Merit
    ("pdc_order_of_merit", "https://www.pdc.tv/rankings/pdc-order-of-merit", {}, "Darts", "html", "PDC official Order of Merit"),
    ("pdc_euro_tour_oom", "https://www.pdc.tv/rankings/european-tour-order-of-merit", {}, "Darts", "html", "PDC official European Tour Order of Merit"),

    # Snooker — WST official world rankings
    ("wst_rankings", "https://www.wst.tv/rankings/", {}, "Snooker", "html", "World Snooker Tour official world rankings"),

    # Tennis — ATP / WTA official rankings
    ("atp_rankings_singles", "https://www.atptour.com/en/rankings/singles", ATP_HEADERS, "Tennis", "html", "ATP official singles rankings"),
    ("wta_rankings_singles", "https://www.wtatennis.com/rankings", ATP_HEADERS, "Tennis", "html", "WTA official singles rankings"),

    # Badminton — BWF official world rankings
    ("bwf_rankings", "https://bwfbadminton.com/rankings/", {}, "Badminton", "html", "BWF official world rankings"),
    ("bwf_rankings_ms", "https://bwfbadminton.com/rankings/?tab=MS", {}, "Badminton", "html", "BWF official men's singles rankings"),

    # Table tennis — ITTF / WTT official world ranking
    ("wtt_ranking", "https://www.worldtabletennis.com/ranking", {}, "Table Tennis", "html", "WTT official world ranking"),
    ("ittf_ranking", "https://www.ittf.com/rankings/", {}, "Table Tennis", "html", "ITTF official world ranking"),

    # Golf — OWGR (official world golf ranking)
    ("owgr_current", "https://www.owgr.com/current-world-ranking", {}, "Golf", "html", "Official World Golf Ranking — current ranking"),

    # Motor racing — official championships
    ("f1_drivers_2026", "https://www.formula1.com/en/results/2026/drivers", {}, "Motor Racing", "html", "Formula 1 official 2026 driver standings"),
    ("f1_races_2026", "https://www.formula1.com/en/results/2026/races", {}, "Motor Racing", "html", "Formula 1 official 2026 race results"),
    ("motogp_standings_2026", "https://www.motogp.com/en/standings/motogp/2026", {}, "Motor Racing", "html", "MotoGP official 2026 standings"),

    # Aussie Rules — AFL official ladders
    ("aflw_ladder", "https://www.afl.com.au/aflw/ladder", {}, "Aussie Rules", "html", "AFLW official ladder"),

    # Ice Hockey / Basketball / Baseball form feeds (official)
    ("nhl_team_stats_now", "https://api-web.nhle.com/v1/meta/stats/team/now?limit=-1", JSON_HEADERS, "Ice Hockey", "api", "NHL official team stats feed"),
    ("nhl_score_2026-10-19", "https://api-web.nhle.com/v1/score/2026-10-19", JSON_HEADERS, "Ice Hockey", "api", "NHL official results 19 Oct 2026"),
    ("nhl_score_2026-10-18", "https://api-web.nhle.com/v1/score/2026-10-18", JSON_HEADERS, "Ice Hockey", "api", "NHL official results 18 Oct 2026"),
]


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<(script|style|noscript|svg)\b.*?</\1>", " ", text)
    text = re.sub(r"(?is)<!--.*?-->", " ", text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text


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
        rec = {"id": sid, "url": url, "sport": sport, "kind": kind, "note": note,
               "fetched_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        try:
            raw, final_url, status = fetch(url, headers)
            digest = hashlib.sha256(raw).hexdigest()
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", "replace")
            if kind == "html":
                text = strip_html(text)
            truncated = len(text) > MAX_CHARS
            text = text[:MAX_CHARS]
            path = os.path.join(OUT, f"{sid}.txt")
            with open(path, "w", encoding="utf-8") as fh:
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
        time.sleep(0.4)

    manifest = {
        "schema": "olbg4/board-ad-raw-manifest/v1",
        "session": "arena/3a6388d2-olbg4",
        "board": "AD",
        "pass": "rankings-and-standings",
        "collector": "scripts/session-3a6388d2/collect_rankings.py",
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
    print(f"\nmanifest: {os.path.relpath(MANIFEST, ROOT)}  ok={manifest['ok']} failed={manifest['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

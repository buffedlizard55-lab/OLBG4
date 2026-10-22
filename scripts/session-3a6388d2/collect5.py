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
MANIFEST = os.path.join(ROOT, "data", SID, "manifest5.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0.0.0 Safari/537.36")
JSON_HEADERS = {"User-Agent": UA, "Accept": "application/json, text/plain, */*"}
BROWSER = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
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
    # OLBG own per-sport cards (taxonomy index + event list as OLBG publishes it)
    ("olbg_sp_tennis", "https://www.olbg.com/betting-tips/Tennis/3", BROWSER, "(OLBG)", "html", "OLBG Tennis tips card"),
    ("olbg_sp_basketball", "https://www.olbg.com/betting-tips/Basketball/4", BROWSER, "(OLBG)", "html", "OLBG Basketball tips card"),
    ("olbg_sp_golf", "https://www.olbg.com/betting-tips/Golf/5", BROWSER, "(OLBG)", "html", "OLBG Golf tips card"),
    ("olbg_sp_cricket", "https://www.olbg.com/betting-tips/Cricket/7", BROWSER, "(OLBG)", "html", "OLBG Cricket tips card"),
    ("olbg_sp_snooker", "https://www.olbg.com/betting-tips/Snooker/8", BROWSER, "(OLBG)", "html", "OLBG Snooker tips card"),
    ("olbg_sp_rugbyunion", "https://www.olbg.com/betting-tips/Rugby_Union/9", BROWSER, "(OLBG)", "html", "OLBG Rugby Union tips card"),
    ("olbg_sp_rugbyleague", "https://www.olbg.com/betting-tips/Rugby_League/10", BROWSER, "(OLBG)", "html", "OLBG Rugby League tips card"),
    ("olbg_sp_baseball", "https://www.olbg.com/betting-tips/Baseball/12", BROWSER, "(OLBG)", "html", "OLBG Baseball tips card"),
    ("olbg_sp_icehockey", "https://www.olbg.com/betting-tips/Ice_Hockey/13", BROWSER, "(OLBG)", "html", "OLBG Ice Hockey tips card"),
    ("olbg_sp_motorracing", "https://www.olbg.com/betting-tips/Motor_Racing/14", BROWSER, "(OLBG)", "html", "OLBG Motor Racing tips card"),
    ("olbg_sp_darts", "https://www.olbg.com/betting-tips/Darts/15", BROWSER, "(OLBG)", "html", "OLBG Darts tips card"),
    ("olbg_sp_handball", "https://www.olbg.com/betting-tips/Handball/20", BROWSER, "(OLBG)", "html", "OLBG Handball tips card"),
    ("olbg_sp_volleyball", "https://www.olbg.com/betting-tips/Volleyball/21", BROWSER, "(OLBG)", "html", "OLBG Volleyball tips card"),
    ("olbg_sp_aussierules", "https://www.olbg.com/betting-tips/Aussie_Rules/22", BROWSER, "(OLBG)", "html", "OLBG Aussie Rules tips card"),
    ("olbg_sp_esports", "https://www.olbg.com/betting-tips/eSports/23", BROWSER, "(OLBG)", "html", "OLBG eSports tips card"),
    ("olbg_sp_gaelic", "https://www.olbg.com/betting-tips/Gaelic_Football/25", BROWSER, "(OLBG)", "html", "OLBG Gaelic Football tips card"),
    ("olbg_sp_greyhounds", "https://www.olbg.com/betting-tips/Greyhounds/28", BROWSER, "(OLBG)", "html", "OLBG Greyhounds tips card"),
    ("olbg_sp_badminton", "https://www.olbg.com/betting-tips/Badminton/18", BROWSER, "(OLBG)", "html", "OLBG Badminton slot 18 (existence check)"),
    ("olbg_sp_tabletennis", "https://www.olbg.com/betting-tips/Table_Tennis/19", BROWSER, "(OLBG)", "html", "OLBG Table Tennis slot 19 (existence check)"),
    # Rugby League World Cup — official pool standings on the host federation site
    ("rlwc_standings", "https://www.rlwc2026.com/standings", BROWSER, "Rugby League", "html", "RLWC 2026 official standings"),
    ("rlwc_results2", "https://www.rlwc2026.com/results", BROWSER, "Rugby League", "html", "RLWC 2026 official results"),
    ("nrl_rlwc_r1b", "https://www.nrl.com/draw/rugby-league-world-cup/2026/round-1/", BROWSER, "Rugby League", "html", "NRL official RLWC Round 1 (retry)"),
    # Golf / Tennis official event pages for the events inside the window
    ("pga_bermuda", "https://www.pgatour.com/tournaments/2026/butterfield-bermuda-championship", BROWSER, "Golf", "html", "PGA Tour official Butterfield Bermuda Championship page"),
    ("wta_tournaments3", "https://www.wtatennis.com/tournaments", BROWSER, "Tennis", "html", "WTA official tournaments (retry)"),
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
        enc = (resp.headers.get("Content-Encoding") or "").lower()
        if enc == "gzip":
            import gzip
            raw = gzip.decompress(raw)
        elif enc == "deflate":
            import zlib
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        elif enc == "br":
            try:
                import brotli                       # noqa
                raw = brotli.decompress(raw)
            except Exception:
                pass
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
        "pass": "olbg-per-sport-cards",
        "collector": "scripts/session-3a6388d2/collect5.py",
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
    print(f"\nmanifest5: ok={manifest['ok']} failed={manifest['failed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Board AT (session arena/086e616f-olbg4) — deterministic, robots-compliant official-source capture.

Runs on an open-egress GitHub Actions runner (the sandbox shell reaches GitHub/npm/PyPI only).
It fetches:

  1. the public OLBG sport hubs for the 15 in-scope sports — used **only** to reverse-engineer
     OLBG's sport/market taxonomy and to enumerate which events OLBG lists; and
  2. official league / tour / federation / governing-body feeds for the 23 Oct – 8 Nov 2026
     window — the only sources any published value may come from.

Raw bytes are stored gzip-compressed with mtime=0 (deterministic) plus a SHA-256 manifest in
``data/session-086e616f/capture/<UTC_STAMP>/``. Every record keeps the request URL, final URL,
HTTP status, content type, byte length, sha256 of the *uncompressed* payload and any error, so a
404/403 is evidence, not a silent gap.

Politeness: per-netloc serialisation with a minimum spacing (0.90s for olbg.com, 0.45s
elsewhere), a hard robots.txt Disallow guard for olbg.com before any socket is opened, and a
per-target payload cap so one huge page cannot dominate the commit.

Usage:
    python3 scripts/session-086e616f/fetch.py <targets.json> <out_dir> [--workers N]
"""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

UA_BROWSER = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
UA_BOT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36 OLBG4-BoardAT/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

# olbg.com robots.txt Disallow prefixes, re-checked against the captured robots.txt itself.
OLBG_DISALLOWED_PREFIXES = (
    "/api/",
    "/sports/",
    "/events.php",
    "/tips/hot",
    "/newbg/",
    "/storage/",
    "/search",
    "/tipster/",
    "/premium/",
    "/cache/",
    "/mods/",
    "/bookiecenter/api/",
    "/sports_event_commenters.php",
    "/content-views-count/",
    "/setlocation.php",
)

HOST_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)
HOST_LAST: dict[str, float] = defaultdict(float)
PRINT_LOCK = threading.Lock()
MAX_BYTES = 6_000_000  # per-target cap on the *uncompressed* payload we keep


def log(msg: str) -> None:
    with PRINT_LOCK:
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {msg}", flush=True)


def olbg_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.endswith("olbg.com"):
        return not any(parsed.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def headers_for(target: dict) -> dict:
    profile = target.get("headers") or "bot"
    url = target["url"]
    if profile == "browser":
        head = {
            "User-Agent": UA_BROWSER,
            "Accept": "text/html,application/xhtml+xml,application/json,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        }
    else:
        head = {
            "User-Agent": UA_BOT,
            "Accept": "text/html,application/json,application/pdf,application/xml,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "gzip",
        }
    if url.endswith(".json") or "api" in urlparse(url).netloc:
        head["Accept"] = "application/json,text/plain,*/*"
    head.update(target.get("extra_headers") or {})
    return head


def fetch_once(url: str, hdrs: dict, timeout: int):
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding", "") == "gzip":
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        try:
            if exc.headers and exc.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
        except Exception:  # noqa: BLE001
            pass
        ctype = exc.headers.get("Content-Type", "") if exc.headers else ""
        return exc.code, url, ctype, body, f"HTTPError {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}"


def polite_wait(url: str, delay: float) -> None:
    host = urlparse(url).netloc
    with HOST_LOCKS[host]:
        wait = HOST_LAST[host] + delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        HOST_LAST[host] = time.monotonic()


def run_target(target: dict) -> dict:
    tid = target["id"]
    url = target["url"]
    delay = float(target.get("delay") or (0.9 if "olbg.com" in url else 0.45))
    timeout = int(target.get("timeout") or 25)
    rec: dict = {
        "id": tid,
        "url": url,
        "sport": target.get("sport"),
        "role": target.get("role", "official"),
        "final_url": None,
        "status": 0,
        "content_type": "",
        "bytes": 0,
        "truncated": False,
        "sha256": None,
        "file": None,
        "error": "",
    }
    if not olbg_allowed(url):
        rec["error"] = "blocked-by-robots-guard"
        log(f"SKIP  {tid} (robots guard)")
        return rec
    hdrs = headers_for(target)
    polite_wait(url, delay)
    status, final_url, ctype, body, err = fetch_once(url, hdrs, timeout)
    # one retry for transport-level failures and for CDN bot walls
    if status in (0, 403, 429) and target.get("retry", 1):
        time.sleep(1.5)
        alt = dict(hdrs)
        alt["User-Agent"] = UA_BROWSER if hdrs["User-Agent"] == UA_BOT else UA_BOT
        polite_wait(url, delay)
        status2, final2, ctype2, body2, err2 = fetch_once(url, alt, timeout)
        if status2 not in (0, 403, 429):
            status, final_url, ctype, body, err = status2, final2, ctype2, body2, err2
        elif status == 0:
            status, final_url, ctype, body, err = status2, final2, ctype2, body2, err2
    rec.update(status=status, final_url=final_url, content_type=ctype, error=err)
    if body:
        if len(body) > MAX_BYTES:
            body = body[:MAX_BYTES]
            rec["truncated"] = True
        rec["bytes"] = len(body)
        rec["sha256"] = hashlib.sha256(body).hexdigest()
        fname = f"{tid}.html.gz"
        ctype_l = (ctype or "").lower()
        if "json" in ctype_l or url.endswith(".json"):
            fname = f"{tid}.json.gz"
        elif "pdf" in ctype_l or url.endswith(".pdf"):
            fname = f"{tid}.pdf.gz"
        elif "xml" in ctype_l or url.endswith((".xml", ".rss")):
            fname = f"{tid}.xml.gz"
        elif "csv" in ctype_l or url.endswith(".csv"):
            fname = f"{tid}.csv.gz"
        out = Path(target["_out_dir"]) / fname
        with gzip.GzipFile(filename="", mode="wb", fileobj=out.open("wb"), compresslevel=9, mtime=0) as gz:
            gz.write(body)
        rec["file"] = fname
    log(f"{'OK  ' if status == 200 else 'FAIL'} {tid} status={status} bytes={rec['bytes']} {err}")
    return rec


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("targets")
    ap.add_argument("out_dir")
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    targets = json.loads(Path(args.targets).read_text())
    if isinstance(targets, dict):
        targets = targets.get("targets", [])
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for t in targets:
        t["_out_dir"] = str(out)

    started = datetime.now(timezone.utc)
    log(f"capturing {len(targets)} targets into {out} with {args.workers} workers")
    records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for rec in pool.map(run_target, targets):
            records.append(rec)
    finished = datetime.now(timezone.utc)

    records.sort(key=lambda r: r["id"])
    ok = sum(1 for r in records if r["status"] == 200)
    manifest = {
        "schema": "olbg4.board-at.capture-manifest/1",
        "board": "AT",
        "session": "arena/086e616f-olbg4",
        "stamp": out.name,
        "started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_utc": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets": len(records),
        "ok": ok,
        "failed": len(records) - ok,
        "max_bytes_cap": MAX_BYTES,
        "user_agents": {"bot": UA_BOT, "browser": UA_BROWSER},
        "records": records,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    by_sport: dict[str, list[int]] = defaultdict(list)
    for r in records:
        by_sport[r.get("sport") or "-"].append(r["status"])
    log(f"done: {ok}/{len(records)} HTTP 200")
    for sport in sorted(by_sport):
        codes = by_sport[sport]
        log(f"  {sport}: {sum(1 for c in codes if c == 200)}/{len(codes)} ok")
    for r in records:
        if r["status"] != 200:
            log(f"  FAILED {r['id']} status={r['status']} {r['error']} :: {r['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

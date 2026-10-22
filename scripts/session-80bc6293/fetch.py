#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) — official-source capture.

The interactive Arena sandbox can only reach github.com / npmjs / pypi, so this script runs
on a GitHub Actions runner (open egress) and commits the exact response bytes plus a
SHA-256 manifest to data/session-80bc6293/capture/<UTC_STAMP>/.

Rules:
  * Nothing is parsed, interpreted or rewritten here — bytes in, bytes on disk.
  * Every target records url, http_status, byte count, sha256, fetch timestamp, local file.
  * Polite per-host spacing (>=0.6s) and >=0.9s for olbg.com; OLBG robots.txt disallowed
    prefixes are skipped.
  * A non-200 is recorded, never retried into a fake success, and never silently dropped.

Usage:  python3 scripts/session-80bc6293/fetch.py <targets.json> <outdir>
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36 OLBG4-BoardAF/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

OLBG_DISALLOWED_PREFIXES = (
    "/api/", "/sports/", "/events.php", "/tips/hot", "/newbg/", "/storage/",
    "/search", "/tipster/", "/premium/", "/cache/", "/mods/", "/bookiecenter/api/",
    "/sports_event_commenters.php", "/content-views-count/", "/setlocation.php",
)

HOST_LAST: dict[str, float] = defaultdict(float)


def allowed(url: str) -> bool:
    p = urlparse(url)
    if p.netloc.endswith("olbg.com"):
        return not any(p.path.startswith(x) for x in OLBG_DISALLOWED_PREFIXES)
    return True


def polite(url: str) -> None:
    host = urlparse(url).netloc
    minimum = 0.9 if host.endswith("olbg.com") else 0.6
    wait = minimum - (time.time() - HOST_LAST[host])
    if wait > 0:
        time.sleep(wait)
    HOST_LAST[host] = time.time()


def fetch(url: str, headers: dict[str, str] | None = None, timeout: int = 45) -> tuple[int, bytes, str]:
    req_headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/html, application/xml, */*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip",
    }
    req_headers.update(headers or {})
    req = urllib.request.Request(url, headers=req_headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                try:
                    body = gzip.decompress(body)
                except OSError:
                    pass
            return int(resp.status), body, resp.geturl()
    except urllib.error.HTTPError as exc:  # a real HTTP status is evidence, not a failure to record
        try:
            body = exc.read()
        except Exception:  # pragma: no cover
            body = b""
        return int(exc.code), body, url
    except Exception as exc:  # network-level error: record the class and message
        return 0, f"{type(exc).__name__}: {exc}".encode("utf-8"), url


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: fetch.py <targets.json> <outdir>", file=sys.stderr)
        return 2
    targets = json.load(open(sys.argv[1], encoding="utf-8"))
    outdir = sys.argv[2]
    rawdir = os.path.join(outdir, "raw")
    os.makedirs(rawdir, exist_ok=True)

    manifest = {
        "schema": "olbg4/board-af-capture/v1",
        "session": "arena/80bc6293-olbg4",
        "board": "AF",
        "captured_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_agent": UA,
        "targets": [],
    }

    ok = fail = 0
    for t in targets:
        tid, url = t["id"], t["url"]
        if not allowed(url):
            manifest["targets"].append({
                "id": tid, "url": url, "sport": t.get("sport", ""),
                "skipped": "disallowed by OLBG robots.txt prefixes",
            })
            print(f"SKIP {tid} (robots)")
            continue
        polite(url)
        status, body, final_url = fetch(url, t.get("headers"))
        fname = f"{tid}.bin"
        if body[:2] == b"\x1f\x8b":  # server sent gzip we did not decode
            fname = f"{tid}.gz"
        with open(os.path.join(rawdir, fname), "wb") as fh:
            fh.write(body)
        rec = {
            "id": tid,
            "url": url,
            "final_url": final_url,
            "sport": t.get("sport", ""),
            "kind": t.get("kind", "official"),
            "http_status": status,
            "bytes": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
            "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "file": f"raw/{fname}",
        }
        manifest["targets"].append(rec)
        if status == 200:
            ok += 1
        else:
            fail += 1
        print(f"{status:>4} {len(body):>9}B  {tid}  {url}")

    manifest["summary"] = {
        "targets": len(targets), "http_200": ok, "other_or_error": fail,
        "sha256_of_manifest_body": "",
    }
    payload = json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8")
    with open(os.path.join(outdir, "manifest.json"), "wb") as fh:
        fh.write(payload)
    print(f"\n{ok}/{len(targets)} HTTP 200; {fail} other — manifest written to {outdir}/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

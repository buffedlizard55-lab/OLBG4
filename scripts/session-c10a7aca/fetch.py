#!/usr/bin/env python3
"""Board C10 (session arena/c10a7aca-olbg4) — deterministic, robots-compliant fresh capture.

Fetches public OLBG hubs/sub-hubs and official governing-body / league / tour feeds on an
open-egress GitHub Actions runner, storing deterministic gzip-compressed raw bytes alongside a
cryptographic SHA-256 manifest in data/session-c10a7aca/capture/<UTC_STAMP>/.

Design guarantees:
  - Strict per-host polite spacing enforced via per-netloc lock + monotonic timer
    (>=0.90s between requests to www.olbg.com; >=0.45s on every other host).
  - Hard guard against every OLBG robots.txt Disallow prefix prior to opening any socket.
  - Deterministic mtime=0 gzip compression and byte-exact SHA-256 digest over uncompressed payload.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36 OLBG4-BoardC10/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

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


def is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.endswith("olbg.com"):
        return not any(parsed.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def fetch_once(url: str, extra_headers: dict) -> tuple[int, str, str, bytes, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/json,application/pdf,application/xml,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip",
    }
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=22) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        try:
            if exc.headers and exc.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
        except Exception:
            pass
        ctype = exc.headers.get("Content-Type", "") if exc.headers else ""
        return exc.code, url, ctype, body, f"HTTPError {exc.code}"
    except Exception as exc:
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}"


def ext_for(content_type: str, url: str) -> str:
    ct = content_type.lower()
    if "json" in ct or url.lower().endswith(".json"):
        return "json"
    if "pdf" in ct or url.lower().endswith(".pdf"):
        return "pdf"
    if "xml" in ct or url.lower().endswith(".xml"):
        return "xml"
    if "text/plain" in ct or url.lower().endswith(".txt"):
        return "txt"
    return "html"


def process_target(idx: int, item: dict, out_dir: str) -> tuple[int, dict]:
    tid, url = item["id"], item["url"]
    rec = {"id": tid, "url": url}
    if not is_allowed(url):
        rec.update(status=None, error="refused: robots.txt disallowed path")
        return idx, rec

    host = urlparse(url).netloc.lower()
    min_gap = float(item.get("delay", 0.90 if host.endswith("olbg.com") else 0.45))

    status, final_url, ctype, body, err = 0, url, "", b"", ""
    for _ in range(2):
        with HOST_LOCKS[host]:
            elapsed = time.monotonic() - HOST_LAST[host]
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)
            status, final_url, ctype, body, err = fetch_once(url, item.get("headers", {}))
            HOST_LAST[host] = time.monotonic()
        if status == 200 and body:
            break
        if status in (403, 404):
            break
        time.sleep(1.2)

    fname = f"{tid}.{ext_for(ctype, url)}.gz"
    with open(os.path.join(out_dir, "raw", fname), "wb") as raw_fh:
        with gzip.GzipFile(fileobj=raw_fh, mode="wb", mtime=0) as gz:
            gz.write(body)

    rec.update(
        final_url=final_url,
        status=status,
        content_type=ctype,
        bytes=len(body),
        sha256=hashlib.sha256(body).hexdigest(),
        file=f"raw/{fname}",
        fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        error=err,
    )
    with PRINT_LOCK:
        print(f"{status:>3} {len(body):>9} {tid:<32} {url}", flush=True)
    return idx, rec


def main() -> int:
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.load(open(targets_path, encoding="utf-8"))
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results: list[tuple[int, dict]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(process_target, i, t, out_dir) for i, t in enumerate(targets)]
        for fut in concurrent.futures.as_completed(futs):
            results.append(fut.result())

    results.sort(key=lambda x: x[0])
    manifest_items = [r for _, r in results]
    ok_count = sum(1 for r in manifest_items if r.get("status") == 200 and r.get("bytes", 0) > 0)
    manifest = {
        "schema": "olbg4.board-c10.capture-manifest/1",
        "session": "arena/c10a7aca-olbg4",
        "board": "C10",
        "started_utc": started,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runner_run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "user_agent": UA,
        "target_count": len(manifest_items),
        "http_200_nonempty_count": ok_count,
        "items": manifest_items,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as mf:
        json.dump(manifest, mf, indent=2, ensure_ascii=False)
        mf.write("\n")
    print(f"Manifest written: {ok_count}/{len(manifest_items)} HTTP 200 non-empty targets.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

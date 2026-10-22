#!/usr/bin/env python3
"""Board AF (session arena/2d25cf78-olbg4) - polite, deterministic official-source capture.

Runs on a GitHub Actions runner (open egress) because the agent sandbox can only reach
GitHub / npm / PyPI. Every response is stored verbatim, gzip-compressed, next to a
SHA-256 manifest so a reviewer can reproduce and re-hash each published number.

Usage:
    python3 scripts/session-2d25cf78/fetch.py scripts/session-2d25cf78/targets.json OUT_DIR
"""
from __future__ import annotations

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

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36 OLBG4-BoardAF/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

# Prefixes OLBG's robots.txt disallows; never requested.
OLBG_DISALLOWED = (
    "/api/", "/sports/", "/events.php", "/tips/hot", "/newbg/", "/storage/", "/search",
    "/tipster/", "/premium/", "/cache/", "/mods/", "/bookiecenter/api/",
    "/sports_event_commenters.php", "/content-views-count/", "/setlocation.php",
)

HOST_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)
HOST_LAST: dict[str, float] = defaultdict(float)


def allowed(url: str) -> bool:
    p = urlparse(url)
    if p.netloc.endswith("olbg.com"):
        return not any(p.path.startswith(pre) for pre in OLBG_DISALLOWED)
    return True


def fetch(url: str, headers: dict | None = None):
    hdrs = {
        "User-Agent": UA,
        "Accept": "text/html,application/json,application/pdf,application/xml,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
        "Accept-Encoding": "gzip",
    }
    hdrs.update(headers or {})
    req = urllib.request.Request(url, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()
            if r.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
            return r.status, r.geturl(), r.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        try:
            if exc.headers and exc.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
        except Exception:
            pass
        return exc.code, url, (exc.headers.get("Content-Type", "") if exc.headers else ""), body, f"HTTPError {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}"


def ext_for(ctype: str, url: str) -> str:
    ct, low = ctype.lower(), url.lower()
    if "json" in ct or low.endswith(".json"):
        return "json"
    if "pdf" in ct or low.endswith(".pdf"):
        return "pdf"
    if "xml" in ct or low.endswith(".xml"):
        return "xml"
    if "text/plain" in ct or low.endswith(".txt"):
        return "txt"
    return "html"


def work(item: dict, out: Path) -> dict:
    tid, url = item["id"], item["url"]
    rec = {"id": tid, "url": url}
    if not allowed(url):
        rec.update(status=None, error="refused: robots.txt disallowed path")
        return rec
    host = urlparse(url).netloc.lower()
    gap = float(item.get("delay", 1.2 if host.endswith("olbg.com") else 0.35))
    status, final_url, ctype, body, err = 0, url, "", b"", ""
    for attempt in range(3):
        with HOST_LOCKS[host]:
            wait = gap - (time.monotonic() - HOST_LAST[host])
            if wait > 0:
                time.sleep(wait)
            status, final_url, ctype, body, err = fetch(url, item.get("headers"))
            HOST_LAST[host] = time.monotonic()
        if status == 200 and body:
            break
        if status in (401, 403, 404, 410):
            break
        time.sleep(1.2 * (attempt + 1))
    suffix = ext_for(ctype, url)
    fname = f"{tid}.{suffix}.gz"
    (out / "raw").mkdir(parents=True, exist_ok=True)
    if body:
        with gzip.open(out / "raw" / fname, "wb", compresslevel=9) as fh:
            fh.write(body)
    rec.update(
        final_url=final_url,
        status=status,
        content_type=ctype,
        bytes=len(body),
        sha256=hashlib.sha256(body).hexdigest() if body else "",
        file=f"raw/{fname}" if body else "",
        fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        error=err,
    )
    print(f"[{status:>3}] {len(body):>8} B  {tid}  {url}" + (f"  ({err})" if err else ""), flush=True)
    return rec


def main() -> int:
    targets_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    targets = json.loads(targets_path.read_text())
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(work, t, out_dir) for t in targets]
        for fut in concurrent.futures.as_completed(futures):
            results.append(fut.result())
    order = {t["id"]: i for i, t in enumerate(targets)}
    results.sort(key=lambda r: order.get(r["id"], 10**6))
    manifest = {
        "schema": "olbg4.board-af.capture-manifest/1",
        "session": "arena/2d25cf78-olbg4",
        "board": "AF",
        "started_utc": started,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runner_run_id": __import__("os").environ.get("GITHUB_RUN_ID", ""),
        "user_agent": UA,
        "target_count": len(targets),
        "http_200_nonempty_count": sum(1 for r in results if r.get("status") == 200 and r.get("bytes")),
        "files": results,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"\n{manifest['http_200_nonempty_count']}/{len(targets)} ok -> {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

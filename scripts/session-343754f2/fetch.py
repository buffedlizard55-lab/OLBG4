#!/usr/bin/env python3
"""Board BW (session arena/343754f2-olbg4) — deterministic, robots-compliant same-day capture.

Fetches public OLBG sport hubs (taxonomy + live listings for the 15-sport scope only) and
official governing-body / league / tour feeds for the 23 Oct – 2 Nov 2026 window on an
open-egress GitHub Actions runner, storing deterministic gzip-compressed raw bytes plus a
SHA-256 manifest in data/session-343754f2/capture/<UTC_STAMP>/.

Design guarantees (same discipline as the repo's earlier capture desks):
  - Per-host polite spacing via per-netloc lock + monotonic timer (>=0.90s between requests
    to www.olbg.com; >=0.45s on every other host).
  - Hard guard against every OLBG robots.txt Disallow prefix before any socket is opened.
  - Deterministic mtime=0 gzip compression; SHA-256 recorded over the uncompressed payload.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import io
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
    "Chrome/128.0 Safari/537.36 OLBG4-BoardEZ/1.0 "
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
        with urllib.request.urlopen(req, timeout=25) as resp:
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
            try:
                status, final_url, ctype, body, err = fetch_once(url, item.get("headers") or {})
            finally:
                HOST_LAST[host] = time.monotonic()
        if status == 200 and body:
            break
        if status in (301, 302, 303, 307, 308):
            time.sleep(0.4)
            continue
        break

    rec.update(status=status, final_url=final_url, content_type=ctype, error=err or None)
    if status == 200 and body:
        digest = hashlib.sha256(body).hexdigest()
        ext = ext_for(ctype, url)
        # gzip-compressed HTML must not carry a bare .html name: the repository-wide
        # publication audit reads every *.html as UTF-8 text (see PR #139 convention).
        fname = f"{tid}.{ext}" + (".gz" if ext == "html" else "")
        path = Path(out_dir) / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        gz = gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0)
        gz.write(body)
        gz.close()
        path.write_bytes(buf.getvalue())
        rec.update(file=fname, sha256=digest, bytes=len(body))
    with PRINT_LOCK:
        print(f"[{idx:03d}] {status or 'ERR':>3} {tid} ({len(body)}B) {url}", flush=True)
    return idx, rec


def main() -> int:
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.loads(Path(targets_path).read_text())
    started = datetime.now(timezone.utc)
    print(f"[board-bw] capture started {started.isoformat()} with {len(targets)} targets", flush=True)

    results: list[dict] = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(process_target, i, t, out_dir) for i, t in enumerate(targets, 1)]
            for fut in concurrent.futures.as_completed(futures):
                _, rec = fut.result()
                results.append(rec)
    except Exception:
        import traceback
        traceback.print_exc()

    results.sort(key=lambda r: r["id"])
    ok = sum(1 for r in results if r.get("status") == 200 and r.get("file"))
    manifest = {
        "board": "BW",
        "session": "arena/343754f2-olbg4",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "targets": len(targets),
        "ok": ok,
        "failed": len(targets) - ok,
        "records": results,
    }
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"[board-bw] finished: {ok}/{len(targets)} OK; manifest written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

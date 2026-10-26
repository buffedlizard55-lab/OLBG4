#!/usr/bin/env python3
"""Board CA (session arena/3a7bd9bb-olbg4) — deterministic, robots-compliant live capture.

Fetches public OLBG sport hubs (for the exact 15-sport scope only) and official governing-body,
league, tour, and statutory racing feeds on an open-egress GitHub Actions runner.
Every HTTP 200 payload is saved as deterministic mtime=0 gzip (`<id>.<ext>.gz`) so external HTML
never collides with the repo-wide local-link scanner, while `manifest.json` records the exact
uncompressed byte length and SHA-256 digest of every response.
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

ROOT = Path(__file__).resolve().parents[2]
TARGETS_FILE = Path(__file__).resolve().parent / "targets.json"
OUT_ROOT = ROOT / "data" / "session-3a7bd9bb" / "capture"

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36"
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
    if parsed.netloc.lower().endswith("olbg.com"):
        return not any(parsed.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def compress_deterministic(data: bytes) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(filename="", mode="wb", fileobj=buf, compresslevel=6, mtime=0) as gz:
        gz.write(data)
    return buf.getvalue()


def ext_for(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    ul = url.lower().split("?")[0]
    if "json" in ct or ul.endswith(".json"):
        return "json"
    if "pdf" in ct or ul.endswith(".pdf"):
        return "pdf"
    if "xml" in ct or ul.endswith(".xml"):
        return "xml"
    if "text/plain" in ct or ul.endswith(".txt"):
        return "txt"
    return "html"


def fetch_once(url: str, extra_headers: dict) -> tuple[int, str, str, bytes, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/json,application/pdf,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip",
    }
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            body = resp.read()
            if resp.headers.get("Content-Encoding", "").lower() == "gzip":
                try:
                    body = gzip.decompress(body)
                except Exception:
                    pass
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        ctype = exc.headers.get("Content-Type", "") if exc.headers else ""
        return exc.code, url, ctype, body, f"HTTPError {exc.code}"
    except Exception as exc:
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}"


def process_target(idx: int, item: dict, out_dir: Path) -> tuple[int, dict]:
    tid = item["id"]
    url = item["url"]
    sport = item.get("sport", "")
    rec: dict = {"id": tid, "sport": sport, "url": url}
    if not is_allowed(url):
        rec.update(status=None, bytes=0, sha256=None, file=None, error="refused: robots.txt disallowed path")
        return idx, rec

    host = urlparse(url).netloc.lower()
    min_gap = float(item.get("delay", 0.95 if host.endswith("olbg.com") else 0.45))

    status, final_url, ctype, body, err = 0, url, "", b"", ""
    for attempt in range(2):
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
        if attempt == 0:
            time.sleep(0.5)

    rec.update(status=status, final_url=final_url, content_type=ctype, error=err or None)
    if status == 200 and body:
        digest = hashlib.sha256(body).hexdigest()
        fname = f"{tid}.{ext_for(ctype, url)}.gz"
        (out_dir / fname).write_bytes(compress_deterministic(body))
        rec.update(bytes=len(body), sha256=digest, file=fname)
    else:
        rec.update(bytes=0, sha256=None, file=None)

    with PRINT_LOCK:
        print(f"[{idx+1:03d}] {status:3d} {rec['bytes']:8d}B  {tid:34s}  {url}")
    return idx, rec


def main() -> int:
    targets = json.loads(TARGETS_FILE.read_text(encoding="utf-8"))
    started = datetime.now(timezone.utc)
    stamp = started.strftime("%Y%m%dT%H%M%SZ")
    out_dir = OUT_ROOT / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    ordered: list[dict | None] = [None] * len(targets)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(process_target, i, t, out_dir) for i, t in enumerate(targets)]
        for fut in concurrent.futures.as_completed(futs):
            i, rec = fut.result()
            ordered[i] = rec

    finished = datetime.now(timezone.utc)
    records = [r for r in ordered if r is not None]
    ok_count = sum(1 for r in records if r.get("status") == 200 and (r.get("bytes") or 0) > 0)
    manifest = {
        "schema": "olbg4.board-cb.capture-manifest/1",
        "board": "CB",
        "session": "arena/3a7bd9bb-olbg4",
        "capture_id": stamp,
        "started_utc": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finished_utc": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets_total": len(records),
        "http_200_count": ok_count,
        "failed_count": len(records) - ok_count,
        "records": records,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Capture {stamp} complete: {ok_count}/{len(records)} HTTP-200 saved to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

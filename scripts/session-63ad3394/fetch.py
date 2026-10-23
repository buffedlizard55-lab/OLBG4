#!/usr/bin/env python3
"""Board AK (session arena/63ad3394-olbg4) — deterministic, robots-compliant capture.

Runs on a GitHub Actions runner (open egress) and writes the raw bytes of every
target to ``data/session-63ad3394/capture/<UTC_STAMP>/`` together with a SHA-256
manifest. Nothing is parsed here: parsing, line origination and verification all
happen locally against the committed bytes, so every published number can be
re-derived from a byte-identical payload.

Rules enforced before any socket is opened:
  * ``www.olbg.com`` robots.txt is fetched first and every OLBG path is checked
    against the Disallow prefixes parsed from that file (plus the static list
    this repository has used since 21 Oct so a robots.txt regression cannot
    silently widen the crawl).
  * No OLBG endpoint that requires a location cookie, an account or a search
    query is requested.
  * Per-host politeness: >=0.90 s between requests to olbg.com, >=0.45 s
    elsewhere, one lock per netloc.

Determinism: gzip payloads are written with mtime=0 and the manifest is sorted
by target id, so the same bytes produce the same tree.
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
    "Chrome/128.0 Safari/537.36 OLBG4-BoardAK/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

# Static baseline of OLBG robots.txt Disallow prefixes (read 2026-10-21..23).
OLBG_STATIC_DISALLOW = (
    "/api/", "/sports/", "/events.php", "/tips/hot", "/newbg/", "/storage/",
    "/search", "/tipster/", "/premium/", "/cache/", "/mods/",
    "/bookiecenter/api/", "/sports_event_commenters.php", "/content-views-count/",
    "/setlocation.php",
)

HOST_LOCKS: dict[str, threading.Lock] = defaultdict(threading.Lock)
HOST_LAST: dict[str, float] = defaultdict(float)
PRINT_LOCK = threading.Lock()
ROBOTS_DISALLOW: list[str] = list(OLBG_STATIC_DISALLOW)
ROBOTS_PREFIXES: list[str] = []


def parse_robots(text: str) -> tuple[list[str], list[str]]:
    """Return (disallow prefixes, allow prefixes) for the * wildcard agent."""
    disallow, allow, active = [], [], False
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key, value = key.strip().lower(), value.strip()
        if key == "user-agent":
            active = value in ("*", "OLBG4-BoardAK") or value.lower() == "olbg4"
        elif active and key == "disallow" and value:
            disallow.append(value)
        elif active and key == "allow" and value:
            allow.append(value)
    return disallow, allow


def is_allowed(url: str) -> tuple[bool, str]:
    parsed = urlparse(url)
    if not parsed.netloc.endswith("olbg.com"):
        return True, ""
    path = parsed.path or "/"
    if parsed.query:
        return False, "refused: query string on olbg.com (cookie/search style path)"
    for prefix in ROBOTS_PREFIXES + ROBOTS_DISALLOW:
        if prefix and path.startswith(prefix):
            return False, f"refused: robots.txt disallow {prefix}"
    return True, ""


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
        with urllib.request.urlopen(req, timeout=30) as resp:
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
    except Exception as exc:  # noqa: BLE001 - recorded in the manifest
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}"


def ext_for(content_type: str, url: str, body: bytes) -> str:
    ct = content_type.lower()
    if body[:4] == b"%PDF" or "pdf" in ct or url.lower().endswith(".pdf"):
        return "pdf"
    if "json" in ct or body[:1] in (b"{", b"["):
        return "json"
    if "xml" in ct or body[:5] == b"<?xml":
        return "xml"
    if "text/plain" in ct or url.lower().endswith(".txt") or url.endswith("robots.txt"):
        return "txt"
    return "html"


def process_target(idx: int, item: dict, out_dir: str) -> tuple[int, dict]:
    tid, url = item["id"], item["url"]
    rec = {"id": tid, "url": url, "sport": item.get("sport"), "kind": item.get("kind", "official")}
    allowed, reason = is_allowed(url)
    if not allowed:
        rec.update(status=None, error=reason)
        with PRINT_LOCK:
            print(f"[{idx:03d}] SKIP {tid} {reason}", flush=True)
        return idx, rec

    host = urlparse(url).netloc.lower()
    min_gap = float(item.get("delay", 0.90 if host.endswith("olbg.com") else 0.45))

    status, final_url, ctype, body, err = 0, url, "", b"", ""
    for attempt in range(3):
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
        if status in (429, 500, 502, 503, 504):
            time.sleep(1.5 * (attempt + 1))
            continue
        if status in (301, 302, 303, 307, 308):
            time.sleep(0.4)
            continue
        break

    rec.update(status=status, final_url=final_url, content_type=ctype,
               fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               error=err or None)
    if status == 200 and body:
        digest = hashlib.sha256(body).hexdigest()
        fname = f"{tid}.{ext_for(ctype, url, body)}.gz"
        path = Path(out_dir) / fname
        path.parent.mkdir(parents=True, exist_ok=True)
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as gz:
            gz.write(body)
        path.write_bytes(buf.getvalue())
        rec.update(file=fname, sha256=digest, bytes=len(body))
    with PRINT_LOCK:
        print(f"[{idx:03d}] {status or 'ERR':>3} {tid} ({len(body)}B) {url}", flush=True)
    return idx, rec


def main() -> int:
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.loads(Path(targets_path).read_text())
    started = datetime.now(timezone.utc)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    print(f"[board-ak] capture started {started.isoformat()} with {len(targets)} targets", flush=True)

    # robots.txt first, and honour it for every OLBG request in this run.
    robots = next((t for t in targets if t["id"] == "olbg_robots"), None)
    if robots:
        st, _, _, body, err = fetch_once(robots["url"], {})
        if st == 200 and body:
            disallow, allow = parse_robots(body.decode("utf-8", "replace"))
            global ROBOTS_PREFIXES
            ROBOTS_PREFIXES = [p for p in disallow if p not in (ROBOTS_DISALLOW)]
            digest = hashlib.sha256(body).hexdigest()
            fname = "olbg_robots.txt.gz"
            buf = io.BytesIO()
            with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as gz:
                gz.write(body)
            (Path(out_dir) / fname).write_bytes(buf.getvalue())
            robots_rec = {"id": robots["id"], "url": robots["url"], "sport": "_taxonomy",
                          "kind": "olbg", "status": 200, "final_url": robots["url"],
                          "content_type": "text/plain", "bytes": len(body), "file": fname,
                          "sha256": digest, "error": None,
                          "fetched_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            print(f"[board-ak] robots.txt: {len(disallow)} disallow, {len(allow)} allow prefixes", flush=True)
        else:
            robots_rec = {"id": robots["id"], "url": robots["url"], "status": st, "error": err or "robots fetch failed"}
            print(f"[board-ak] robots.txt fetch failed ({st} {err}); static baseline only", flush=True)
    else:
        robots_rec = None

    results: list[dict] = [robots_rec] if robots_rec else []
    pending = [t for t in targets if t["id"] != "olbg_robots"]
    # OLBG targets last so the rest of the capture never waits on the slow host.
    pending.sort(key=lambda t: (0 if not t["url"].startswith("https://www.olbg.com") else 1, t["id"]))
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(process_target, i, t, out_dir) for i, t in enumerate(pending, 1)]
            for fut in concurrent.futures.as_completed(futures):
                _, rec = fut.result()
                results.append(rec)
    except Exception:  # noqa: BLE001 - partial capture is still committed
        import traceback
        traceback.print_exc()

    results.sort(key=lambda r: r["id"])
    ok = sum(1 for r in results if r.get("status") == 200 and r.get("file"))
    manifest = {
        "schema": "olbg4.board-ak.capture/1",
        "board": "AK",
        "session": "arena/63ad3394-olbg4",
        "started_utc": started.isoformat(),
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "user_agent": UA,
        "robots_disallow_parsed": ROBOTS_PREFIXES,
        "targets": len(targets),
        "ok": ok,
        "failed": len(targets) - ok,
        "records": results,
    }
    (Path(out_dir) / "manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    print(f"[board-ak] finished: {ok}/{len(targets)} OK; manifest written", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

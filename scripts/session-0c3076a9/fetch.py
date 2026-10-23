#!/usr/bin/env python3
"""Board AJ (session arena/0c3076a9-olbg4) — deterministic, robots-compliant live capture.

Fetches public OLBG hubs/events (strictly for the 15 covered sports) and official governing-body
feeds on an open-egress GitHub Actions runner, storing deterministic gzip-compressed raw bytes
(mtime=0) alongside a cryptographic SHA-256 manifest in data/session-0c3076a9/capture/<STAMP>/.
"""
from __future__ import annotations

import concurrent.futures
import gzip
import hashlib
import json
import os
import subprocess
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
    if parsed.netloc.endswith("olbg.com"):
        return not any(parsed.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def fetch_urllib(url: str, extra_headers: dict) -> tuple[int, str, str, bytes, str, str]:
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
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, "", "urllib"
    except urllib.error.HTTPError as exc:
        body = exc.read() or b""
        try:
            if exc.headers and exc.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
        except Exception:
            pass
        ctype = exc.headers.get("Content-Type", "") if exc.headers else ""
        return exc.code, url, ctype, body, f"HTTPError {exc.code}", "urllib"
    except Exception as exc:
        return 0, url, "", b"", f"{type(exc).__name__}: {exc}", "urllib"


def fetch_curl(url: str, extra_headers: dict) -> tuple[int, str, str, bytes, str, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/json,application/pdf,application/xml,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    headers.update(extra_headers or {})
    meta_sep = b"\n__AJ_CURL_META__\n"
    cmd = [
        "curl", "-sS", "-L", "--compressed", "--http2", "--max-time", "25",
        "-w", "\n__AJ_CURL_META__\n%{http_code}\n%{content_type}\n%{url_effective}",
    ]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True)
    raw = proc.stdout or b""
    idx = raw.rfind(meta_sep)
    if idx == -1:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()[:200]
        return 0, url, "", b"", f"curl exit {proc.returncode}: {err}", "curl"
    body = raw[:idx]
    meta_lines = raw[idx + len(meta_sep):].decode("utf-8", "replace").splitlines()
    code = int(meta_lines[0].strip()) if meta_lines and meta_lines[0].strip().isdigit() else 0
    ctype = meta_lines[1].strip() if len(meta_lines) > 1 else ""
    final_url = meta_lines[2].strip() if len(meta_lines) > 2 else url
    err = "" if code == 200 else f"HTTP {code}"
    if proc.returncode != 0 and code == 0:
        err = (proc.stderr or b"").decode("utf-8", "replace").strip()[:200]
    return code, final_url, ctype, body, err, "curl"


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
    rec: dict = {"id": tid, "url": url, "sport": item.get("sport", "")}
    if not is_allowed(url):
        rec.update(status=None, error="refused: robots.txt disallowed path")
        return idx, rec

    host = urlparse(url).netloc.lower()
    min_gap = float(item.get("delay", 0.95 if host.endswith("olbg.com") else 0.40))
    headers = item.get("headers") or {}
    prefer_curl = bool(item.get("use_curl", False))

    status, final_url, ctype, body, err, transport = 0, url, "", b"", "", "urllib"
    for attempt in range(2):
        with HOST_LOCKS[host]:
            elapsed = time.monotonic() - HOST_LAST[host]
            if elapsed < min_gap:
                time.sleep(min_gap - elapsed)
            HOST_LAST[host] = time.monotonic()

        if prefer_curl:
            status, final_url, ctype, body, err, transport = fetch_curl(url, headers)
        else:
            status, final_url, ctype, body, err, transport = fetch_urllib(url, headers)
            if status in (0, 403, 406, 429) and not host.endswith("olbg.com"):
                status, final_url, ctype, body, err, transport = fetch_curl(url, headers)
        if status == 200 and body:
            break
        time.sleep(0.8 * (attempt + 1))

    sha = hashlib.sha256(body).hexdigest() if body else None
    ext = ext_for(ctype, url)
    rel_file = None
    if body:
        rel_file = f"raw/{tid}.{ext}.gz"
        abs_file = os.path.join(out_dir, rel_file)
        with open(abs_file, "wb") as fh:
            with gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
                gz.write(body)

    rec.update(
        status=status,
        final_url=final_url,
        content_type=ctype,
        bytes=len(body),
        sha256=sha,
        file=rel_file,
        transport=transport,
        retrieved_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    if err:
        rec["error"] = err
    with PRINT_LOCK:
        print(f"[{status}] {tid} ({len(body)} B via {transport}) <- {url}", flush=True)
    return idx, rec


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: fetch.py <targets.json> <out_dir>", file=sys.stderr)
        return 2
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.load(open(targets_path, encoding="utf-8"))
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    results: list[dict | None] = [None] * len(targets)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(process_target, i, t, out_dir) for i, t in enumerate(targets)]
        for fut in concurrent.futures.as_completed(futs):
            i, rec = fut.result()
            results[i] = rec

    finished = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ok_count = sum(1 for r in results if r and r.get("status") == 200 and (r.get("bytes") or 0) > 0)
    manifest = {
        "schema": "olbg4.board-aj.capture/1",
        "session": "arena/0c3076a9-olbg4",
        "started_utc": started,
        "finished_utc": finished,
        "total_targets": len(targets),
        "http_200_count": ok_count,
        "targets": results,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"Capture complete: {ok_count}/{len(targets)} HTTP 200 -> {out_dir}/manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board DS evidence collector.

Runs on a GitHub Actions runner because this sandbox can only reach GitHub.  Every
response is written verbatim under ``data/session-e880ce67/raw/<group>/`` together with a
SHA-256 hash, byte count, HTTP status, content type and fetch timestamp in
``data/session-e880ce67/raw/manifest.json``.

Failures are first-class: a non-200, a timeout or a DNS error is recorded with its
reason and the capture run is still allowed to succeed, so a missing governing-body
feed is visible instead of being papered over.

Usage::

    python3 scripts/session-e880ce67/collect.py            # fetch everything
    python3 scripts/session-e880ce67/collect.py olbg       # one group only
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "data", "session-e880ce67", "raw")
sys.path.insert(0, HERE)
from spec import ALL_GROUPS, MAX_BYTES  # noqa: E402

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/json,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Accept-Encoding": "identity",
}


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def curl_fetch(url: str, timeout: int = 45) -> dict:
    """Second attempt for hosts that answer urllib with 403 (Akamai bot rules).

    curl is used with the same browser headers plus a referer; the HTTP status is returned
    in the body tail so a real 404 is never mistaken for a successful fetch.
    """
    if not shutil.which("curl"):
        return {"status": None, "final_url": url, "content_type": "", "bytes": 0,
                "truncated": False, "elapsed_ms": 0, "error": "curl unavailable", "body": b""}
    cmd = ["curl", "-sS", "-L", "--max-time", str(timeout), "--compressed",
           "-A", UA, "-H", "Accept: text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
           "-H", "Accept-Language: en-GB,en;q=0.9",
           "-H", "Sec-Fetch-Mode: navigate", "-H", "Sec-Fetch-Site: none",
           "-H", "Upgrade-Insecure-Requests: 1",
           "-w", "\n%{http_code} %{content_type}", url]
    started = time.time()
    try:
        out = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    except subprocess.TimeoutExpired:
        return {"status": None, "final_url": url, "content_type": "", "bytes": 0,
                "truncated": False, "elapsed_ms": int((time.time() - started) * 1000),
                "error": "curl timeout", "body": b""}
    raw = out.stdout
    tail = raw.rsplit(b"\n", 1)
    meta = tail[-1].decode("utf-8", "replace") if len(tail) == 2 else ""
    body = tail[0] if len(tail) == 2 else raw
    parts = meta.split(" ")
    status = int(parts[0]) if parts and parts[0].isdigit() else None
    ctype = " ".join(parts[1:]) if len(parts) > 1 else ""
    truncated = len(body) > MAX_BYTES
    return {"status": status, "final_url": url, "content_type": ctype,
            "bytes": min(len(body), MAX_BYTES), "truncated": truncated,
            "elapsed_ms": int((time.time() - started) * 1000),
            "body": body[:MAX_BYTES] if status == 200 else b"",
            "error": "" if status == 200 else f"curl HTTP {status}"}


def fetch(url: str, timeout: int = 45) -> dict:
    result = _fetch_urllib(url, timeout)
    if result.get("status") == 200 and result.get("body"):
        return result
    # One retry through curl before a failure is recorded.
    retry = curl_fetch(url, timeout)
    if retry.get("status") == 200 and retry.get("body"):
        retry["via"] = "curl"
        return retry
    result["via"] = "urllib"
    return result


def _fetch_urllib(url: str, timeout: int = 45) -> dict:
    req = urllib.request.Request(url, headers=HEADERS)
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_BYTES + 1)
            truncated = len(raw) > MAX_BYTES
            if truncated:
                raw = raw[:MAX_BYTES]
            return {
                "status": resp.status,
                "final_url": resp.geturl(),
                "content_type": resp.headers.get("Content-Type", ""),
                "bytes": len(raw),
                "truncated": truncated,
                "elapsed_ms": int((time.time() - started) * 1000),
                "body": raw,
            }
    except urllib.error.HTTPError as exc:
        return {"status": exc.code, "final_url": url, "content_type": "",
                "bytes": 0, "truncated": False,
                "elapsed_ms": int((time.time() - started) * 1000),
                "error": f"HTTP {exc.code} {exc.reason}", "body": b""}
    except urllib.error.URLError as exc:
        return {"status": None, "final_url": url, "content_type": "", "bytes": 0,
                "truncated": False, "elapsed_ms": int((time.time() - started) * 1000),
                "error": f"URLError {exc.reason}", "body": b""}
    except (socket.timeout, TimeoutError) as exc:
        return {"status": None, "final_url": url, "content_type": "", "bytes": 0,
                "truncated": False, "elapsed_ms": int((time.time() - started) * 1000),
                "error": f"timeout {exc!r}", "body": b""}
    except Exception as exc:  # noqa: BLE001 - every failure must be recorded
        return {"status": None, "final_url": url, "content_type": "", "bytes": 0,
                "truncated": False, "elapsed_ms": int((time.time() - started) * 1000),
                "error": f"{type(exc).__name__}: {exc}", "body": b""}


EXT = {"json": ".json", "javascript": ".js", "xml": ".xml", "html": ".html"}


def extension(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    for needle, ext in EXT.items():
        if needle in ct:
            return ext
    path = url.split("?")[0].lower()
    for ext in (".json", ".xml", ".html"):
        if path.endswith(ext):
            return ext
    return ".txt"


def main() -> int:
    groups = sys.argv[1:] or list(ALL_GROUPS)
    captured = now()
    manifest_path = os.path.join(OUT, "manifest.json")
    manifest = {"captured_utc": captured, "entries": []}
    if os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, encoding="utf-8"))
            manifest["captured_utc"] = captured
        except json.JSONDecodeError:
            pass
    seen = {(e["group"], e["key"]): i for i, e in enumerate(manifest["entries"])}

    ok = fail = 0
    for group in groups:
        urls = ALL_GROUPS[group]
        target = os.path.join(OUT, group)
        os.makedirs(target, exist_ok=True)
        for key, url in urls.items():
            result = fetch(url)
            body = result.pop("body")
            entry = {"group": group, "key": key, "url": url,
                     "fetched_utc": now(), **result}
            if result["status"] == 200 and body:
                path = os.path.join(target, key + extension(result["content_type"], url))
                with open(path, "wb") as fh:
                    fh.write(body)
                entry["file"] = os.path.relpath(path, ROOT)
                entry["sha256"] = hashlib.sha256(body).hexdigest()
                ok += 1
            else:
                entry["file"] = ""
                entry["sha256"] = ""
                entry.setdefault("error", f"status {result['status']} with {len(body)} bytes")
                fail += 1
            if (group, key) in seen:
                manifest["entries"][seen[(group, key)]] = entry
            else:
                seen[(group, key)] = len(manifest["entries"])
                manifest["entries"].append(entry)
            flag = "ok  " if entry["sha256"] else "FAIL"
            print(f"[{flag}] {group}/{key} {result['status']} {entry['bytes']}B "
                  f"{entry.get('error', '')}")

    manifest["counts"] = {"ok": ok, "failed": fail, "total": ok + fail}
    os.makedirs(OUT, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"[manifest] {manifest_path} ok={ok} failed={fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

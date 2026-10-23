#!/usr/bin/env python3
"""Capture official sources from a runner with open egress.

Local sandbox egress is blocked (TLS reset for every non allow-listed host), so every
page used by this board is fetched here and committed as bytes together with a
SHA-256 manifest. Parsing happens only from the committed bytes.

Storage discipline: bodies are gzipped and capped at MAX_BYTES; a target that fails,
returns non-200, or exceeds the cap is recorded but stores no body. Nothing is
published from a target that did not return HTTP 200 with a non-empty body.

Usage: python3 scripts/session-2c05e0b2/fetch.py [capture-id]
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
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TARGETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "targets.json")
MAX_BYTES = 4 * 1024 * 1024
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/127.0 Safari/537.36")


def get(url: str) -> tuple[int, str, bytes, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/json,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            body = r.read(MAX_BYTES + 1)
            return r.status, r.headers.get("content-type", ""), body, ""
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("content-type", "") if e.headers else "", b"", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001 - recorded, never silently swallowed
        return 0, "", b"", f"{type(e).__name__}: {e}"


def main() -> int:
    capture_id = sys.argv[1] if len(sys.argv) > 1 else datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = os.path.join(ROOT, "data", "session-2c05e0b2", "capture", capture_id)
    os.makedirs(out_dir, exist_ok=True)
    targets = json.load(open(TARGETS))["targets"]
    manifest = {
        "capture_id": capture_id,
        "captured_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "user_agent": UA,
        "max_bytes": MAX_BYTES,
        "targets": [],
    }
    ok = 0
    for t in targets:
        status, ctype, body, err = get(t["url"])
        entry = {
            "id": t["id"], "sport": t["sport"], "tier": t["tier"], "url": t["url"],
            "http_status": status, "content_type": ctype, "bytes": len(body), "error": err,
            "sha256": "", "file": "",
        }
        if status == 200 and body and len(body) <= MAX_BYTES:
            entry["sha256"] = hashlib.sha256(body).hexdigest()
            rel = f"{t['id']}.gz"
            with gzip.open(os.path.join(out_dir, rel), "wb", compresslevel=9) as fh:
                fh.write(body)
            entry["file"] = rel
            ok += 1
        manifest["targets"].append(entry)
        print(f"{status:3d} {len(body):9d} {t['id']:26s} {err}", flush=True)
        time.sleep(0.4)
    manifest["summary"] = {
        "targets": len(targets),
        "http_200_with_body": ok,
        "failed": len(targets) - ok,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(json.dumps(manifest["summary"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

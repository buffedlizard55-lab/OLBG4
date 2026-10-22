#!/usr/bin/env python3
"""Board Z (session arena/9359e596-olbg4) - deterministic, robots-compliant page capture.

Captures public OLBG in-scope sport hub pages and official governing-body / league
pages on an open-egress runner, storing exact gzip-compressed bytes alongside a
SHA-256 manifest in data/session-9359e596/capture/<UTC_STAMP>/.

Compliance invariants:
  1. Honest User-Agent identifying the repository.
  2. Strict enforcement of OLBG robots.txt: every disallowed prefix (/api/, /sports/,
     /events.php, /tips/hot, /newbg/, /storage/, /search, /tipster/, /premium/,
     /cache/, /mods/, /bookiecenter/api/, /sports_event_commenters.php,
     /content-views-count/, /setlocation.php) is refused prior to any network call.
  3. Sequential polite spacing between requests (no parallel burst).
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
from urllib.parse import urlparse

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0 Safari/537.36 OLBG4-BoardZ/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)

OLBG_DISALLOWED_PREFIXES = (
    "/api/", "/sports/", "/events.php", "/tips/hot", "/newbg/", "/storage/",
    "/search", "/tipster/", "/premium/", "/cache/", "/mods/", "/bookiecenter/api/",
    "/sports_event_commenters.php", "/content-views-count/", "/setlocation.php",
)


def is_allowed(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.netloc.endswith("olbg.com"):
        return not any(parsed.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def fetch_once(url: str, extra_headers: dict) -> tuple[int, str, str, bytes, str]:
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/json,application/pdf,*/*;q=0.8",
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
    if "xml" in ct:
        return "xml"
    return "html"


def main() -> int:
    targets_path, out_dir = sys.argv[1], sys.argv[2]
    targets = json.load(open(targets_path, encoding="utf-8"))
    os.makedirs(os.path.join(out_dir, "raw"), exist_ok=True)
    manifest_items = []
    for item in targets:
        tid, url = item["id"], item["url"]
        rec = {"id": tid, "url": url}
        if not is_allowed(url):
            rec.update(status=None, error="refused: robots.txt disallowed path")
            manifest_items.append(rec)
            continue
        status, final_url, ctype, body, err = 0, url, "", b"", ""
        for attempt in range(2):
            status, final_url, ctype, body, err = fetch_once(url, item.get("headers", {}))
            if status == 200 and body:
                break
            time.sleep(2 + 2 * attempt)
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
        manifest_items.append(rec)
        print(f"{status} {len(body):>9} {tid} {url}", flush=True)
        time.sleep(float(item.get("delay", 0.8)))
    manifest = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "runner": os.environ.get("GITHUB_RUN_ID", "local"),
        "user_agent": UA,
        "items": manifest_items,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1)
    ok = sum(1 for m in manifest_items if m.get("status") == 200)
    print(f"captured {ok}/{len(manifest_items)} with HTTP 200")
    return 0


if __name__ == "__main__":
    sys.exit(main())

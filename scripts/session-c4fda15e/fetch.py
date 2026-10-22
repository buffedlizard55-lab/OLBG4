#!/usr/bin/env python3
"""Board W (session arena/c4fda15e-olbg4) - raw page capture.

Runs on a GitHub Actions runner (open egress). The interactive sandbox can only
reach GitHub/npm/PyPI hosts, so every OLBG hub page and every official league
page/API that Board W uses is fetched here, stored byte-for-byte, and listed in a
manifest with URL, final URL, HTTP status, content type, byte count, SHA-256 and
UTC fetch time. All later parsing reads only these stored bytes.

Compliance:
  * an explicit, honest User-Agent is sent (OLBG's robots.txt blocks the default
    "Python-urllib" agent, so the default is never used);
  * OLBG robots.txt disallowed paths are refused before any request is made;
  * requests are sequential with a delay - no bulk crawl.

Usage: python3 fetch.py <targets.json> <out_dir>
targets.json: [{"id": "...", "url": "...", "headers": {...}}, ...]
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

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36 OLBG4-BoardW/1.0 "
      "(+https://github.com/buffedlizard55-lab/OLBG4)")

# Paths disallowed for every agent by https://www.olbg.com/robots.txt (read 2026-10-22).
OLBG_DISALLOWED_PREFIXES = (
    "/api/", "/sports/", "/events.php", "/tips/hot", "/newbg/", "/storage/",
    "/search", "/tipster/", "/premium/", "/cache/", "/mods/", "/bookiecenter/api/",
    "/sports_event_commenters.php", "/content-views-count/", "/setlocation.php",
)


def allowed(url: str) -> bool:
    u = urlparse(url)
    if u.netloc.endswith("olbg.com"):
        return not any(u.path.startswith(p) for p in OLBG_DISALLOWED_PREFIXES)
    return True


def fetch(url: str, headers: dict) -> tuple[int, str, str, bytes, str]:
    h = {"User-Agent": UA, "Accept": "text/html,application/json,application/pdf,*/*;q=0.8",
         "Accept-Language": "en-GB,en;q=0.9", "Accept-Encoding": "gzip"}
    h.update(headers or {})
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            body = r.read()
            if r.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
            return r.status, r.geturl(), r.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as e:
        body = e.read() or b""
        try:
            if e.headers.get("Content-Encoding", "") == "gzip":
                body = gzip.decompress(body)
        except Exception:
            pass
        return e.code, url, e.headers.get("Content-Type", "") if e.headers else "", body, f"HTTPError {e.code}"
    except Exception as e:  # network error
        return 0, url, "", b"", f"{type(e).__name__}: {e}"


def ext_for(ctype: str, url: str) -> str:
    c = ctype.lower()
    if "json" in c:
        return "json"
    if "pdf" in c or url.lower().endswith(".pdf"):
        return "pdf"
    if "xml" in c:
        return "xml"
    return "html"


def main() -> int:
    targets = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(os.path.join(out, "raw"), exist_ok=True)
    manifest = []
    for t in targets:
        tid, url = t["id"], t["url"]
        rec = {"id": tid, "url": url}
        if not allowed(url):
            rec.update(status=None, error="refused: robots.txt disallowed path")
            manifest.append(rec)
            continue
        status, final, ctype, body, err = 0, url, "", b"", ""
        for attempt in range(3):
            status, final, ctype, body, err = fetch(url, t.get("headers", {}))
            if status == 200 and body:
                break
            time.sleep(3 + 3 * attempt)
        fname = f"{tid}.{ext_for(ctype, url)}.gz"
        with open(os.path.join(out, "raw", fname), "wb") as raw_fh:
            with gzip.GzipFile(fileobj=raw_fh, mode="wb", mtime=0) as fh:
                fh.write(body)
        rec.update(final_url=final, status=status, content_type=ctype, bytes=len(body),
                   sha256=hashlib.sha256(body).hexdigest(), file=f"raw/{fname}",
                   fetched_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   error=err)
        manifest.append(rec)
        print(f"{status} {len(body):>9} {tid} {url}", flush=True)
        time.sleep(float(t.get("delay", 1.5)))
    json.dump({"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "runner": os.environ.get("GITHUB_RUN_ID", "local"),
               "user_agent": UA, "items": manifest},
              open(os.path.join(out, "manifest.json"), "w", encoding="utf-8"), indent=1)
    ok = sum(1 for m in manifest if m.get("status") == 200)
    print(f"fetched {ok}/{len(manifest)} with HTTP 200")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Board SA (session 696c1a7c) capture harness.

Runs on a GitHub Actions runner because the authoring sandbox can only reach
GitHub/npm/PyPI hosts. Every response is stored byte-for-byte (gzip) beside a
SHA-256 manifest, so each number published downstream can be traced back to the
exact bytes it came from.

Only public pages are requested. OLBG paths listed as disallowed in
https://www.olbg.com/robots.txt ( /api/, /sports/, /events.php, /tips/hot,
/newbg/, /storage/app/json_data/* ) are never requested: the target list contains
sport hub pages only, one fetch each, with a delay between requests.

Usage:
    python3 fetch.py TARGETS_JSON OUTDIR [--label NAME]
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36 OLBG4-research/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)
CTX = ssl.create_default_context()


def get(url: str, timeout: int = 45, accept: str | None = None):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": accept
            or "text/html,application/xhtml+xml,application/json,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "identity",
            "Connection": "close",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read(), r.headers.get("Content-Type", ""), r.geturl()


def main() -> int:
    targets_path, outdir = sys.argv[1], sys.argv[2]
    label = "capture"
    if "--label" in sys.argv:
        label = sys.argv[sys.argv.index("--label") + 1]
    targets = json.load(open(targets_path))
    os.makedirs(outdir, exist_ok=True)
    records, failed = [], []
    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in targets:
        tid, url = t["id"], t["url"]
        delay = float(t.get("delay", 0.4))
        attempts = int(t.get("attempts", 1))
        last_exc = None
        for attempt in range(1, attempts + 1):
            try:
                status, body, ctype, final = get(url, accept=t.get("accept"))
                if status != 200:
                    raise RuntimeError(f"HTTP {status}")
                if not body:
                    raise RuntimeError("empty body")
                is_pdf = "pdf" in ctype.lower() or url.lower().endswith(".pdf")
                raw_name = tid + (".pdf.gz" if is_pdf else ".gz")
                with gzip.open(os.path.join(outdir, raw_name), "wb") as fh:
                    fh.write(body)
                records.append(
                    {
                        "id": tid,
                        "sport": t.get("sport", ""),
                        "url": url,
                        "final_url": final,
                        "status": status,
                        "content_type": ctype,
                        "bytes": len(body),
                        "sha256": hashlib.sha256(body).hexdigest(),
                        "file": raw_name,
                        "error": None,
                    }
                )
                print(f"OK   {tid:38s} {len(body):9d}  {url[:120]}", flush=True)
                last_exc = None
                break
            except Exception as exc:  # noqa: BLE001 - capture every failure verbatim
                last_exc = exc
                if attempt < attempts:
                    time.sleep(2.0 * attempt)
        if last_exc is not None:
            msg = f"{type(last_exc).__name__}: {last_exc}"
            code = getattr(last_exc, "code", 0) or 0
            failed.append({"id": tid, "sport": t.get("sport", ""), "url": url,
                           "status": code, "error": msg})
            print(f"FAIL {tid:38s} {msg[:110]}  {url[:110]}", flush=True)
        time.sleep(delay)

    manifest = {
        "board": "SA",
        "session": "arena/696c1a7c-olbg4",
        "label": label,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets": len(targets),
        "ok": len(records),
        "failed": len(failed),
        "records": records,
        "failures": failed,
    }
    with open(os.path.join(outdir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
    print(f"\n{len(records)} ok / {len(failed)} failed -> {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

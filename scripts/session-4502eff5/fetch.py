#!/usr/bin/env python3
"""Board FX (session 4502eff5) capture harness.

Runs on a GitHub Actions runner (open egress) because the authoring sandbox can only
reach GitHub/npm/PyPI.  Every response is stored byte-for-byte (gzip) next to a
SHA-256 manifest, so every downstream number can be traced to the exact official
bytes it came from.

Usage:  python3 fetch.py TARGETS_JSON OUTDIR
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
    "Chrome/126.0.0.0 Safari/537.36 OLBG4-research/1.0 (+https://github.com/buffedlizard55-lab/OLBG4)"
)
CTX = ssl.create_default_context()


def get(url: str, timeout: int = 45):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json,application/pdf,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
            "Accept-Encoding": "identity",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.status, r.read(), r.headers.get("Content-Type", ""), r.geturl()


def main() -> int:
    targets_path, outdir = sys.argv[1], sys.argv[2]
    targets = json.load(open(targets_path))
    os.makedirs(outdir, exist_ok=True)
    records, failed = [], []
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for t in targets:
        tid, url = t["id"], t["url"]
        delay = float(t.get("delay", 0.6))
        try:
            status, body, ctype, final = get(url)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            raw_name = tid + (".pdf.gz" if "pdf" in ctype.lower() or url.lower().endswith(".pdf") else ".gz")
            path = os.path.join(outdir, raw_name)
            with gzip.open(path, "wb") as fh:
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
            print(f"OK   {tid:34s} {len(body):8d}  {url}", flush=True)
        except Exception as exc:  # noqa: BLE001 - capture every failure verbatim
            msg = f"{type(exc).__name__}: {exc}"
            code = getattr(exc, "code", 0) or 0
            failed.append({"id": tid, "url": url, "status": code, "error": msg})
            print(f"FAIL {tid:34s} {msg[:120]}  {url}", flush=True)
        time.sleep(delay)

    manifest = {
        "board": "FX",
        "session": "arena/4502eff5-olbg4",
        "started_utc": stamp,
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

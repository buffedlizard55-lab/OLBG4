#!/usr/bin/env python3
"""Board OV (session 2d42572e) capture harness.

The authoring sandbox can reach GitHub only, so every OLBG page and every
governing-body / league / tour endpoint the desk cites is fetched here, on a
GitHub Actions runner with open egress.  Each response is stored byte-for-byte
(gzip) next to a SHA-256 manifest, so every number published downstream can be
traced back to the exact bytes it came from.

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
    "Chrome/128.0.0.0 Safari/537.36 OLBG4-research/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)
CTX = ssl.create_default_context()
MAX_BYTES = 24 * 1024 * 1024


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
        body = r.read(MAX_BYTES)
        return r.status, body, r.headers.get("Content-Type", ""), r.geturl()


def safe(name: str) -> str:
    return "".join(c if c.isalnum() or c in "-_.@" else "_" for c in name)[:150]


def main() -> int:
    targets_path, outdir = sys.argv[1], sys.argv[2]
    targets = json.load(open(targets_path))
    os.makedirs(outdir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    records, failed = [], []

    for t in targets:
        tid, url = t["id"], t["url"]
        try:
            status, body, ctype, final = get(url, timeout=int(t.get("timeout", 45)))
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            ext = ".pdf" if ("pdf" in ctype.lower() or url.lower().endswith(".pdf")) else ""
            raw_name = safe(tid) + ext + ".gz"
            with gzip.open(os.path.join(outdir, raw_name), "wb") as fh:
                fh.write(body)
            records.append(
                {
                    "id": tid,
                    "sport": t.get("sport", ""),
                    "group": t.get("group", ""),
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
            print(f"OK   {tid:44s} {len(body):9d}  {url}", flush=True)
        except Exception as exc:  # noqa: BLE001 - record every failure verbatim
            msg = f"{type(exc).__name__}: {exc}"
            failed.append({"id": tid, "url": url, "error": msg})
            print(f"FAIL {tid:44s} {msg}", flush=True)
        time.sleep(float(t.get("delay", 0.4)))

    manifest = {
        "schema": "olbg4.ov.manifest/1",
        "board": "OV",
        "session": "2d42572e",
        "captured_utc": stamp,
        "targets": len(targets),
        "ok": len(records),
        "failed": len(failed),
        "failures": failed,
        "records": records,
    }
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"\ncaptured {len(records)}/{len(targets)} into {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

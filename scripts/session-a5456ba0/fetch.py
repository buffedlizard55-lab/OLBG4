#!/usr/bin/env python3
"""Board AN (session a5456ba0) capture harness.

The authoring sandbox can only reach GitHub / npm / PyPI, so every official byte is
fetched by the Actions runner (`.github/workflows/an-a5456ba0-capture.yml`) and stored
byte-for-byte (gzip) next to a SHA-256 manifest.  Downstream code never reads the live
web: it reads these committed bytes, so each published number is traceable to the exact
response it came from.

Usage: python3 fetch.py TARGETS_JSON OUTDIR
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36 OLBG4-research/1.0 "
    "(+https://github.com/buffedlizard55-lab/OLBG4)"
)
CTX = ssl.create_default_context()
MAX_BYTES = 25 * 1024 * 1024  # protect the repository from a stray multi-hundred-MB payload


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
        delay = float(t.get("delay", 0.5))
        try:
            status, body, ctype, final = get(url)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            if len(body) > MAX_BYTES:
                raise RuntimeError(f"too large: {len(body)} bytes")
            is_pdf = "pdf" in ctype.lower() or url.lower().endswith(".pdf")
            raw_name = tid + (".pdf.gz" if is_pdf else ".gz")
            with gzip.open(os.path.join(outdir, raw_name), "wb") as fh:
                fh.write(body)
            records.append(
                {
                    "id": tid,
                    "sport": t.get("sport", ""),
                    "kind": t.get("kind", "html"),
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
            print(f"OK   {tid:42s} {len(body):9d}  {url}", flush=True)
        except Exception as exc:  # noqa: BLE001 - record every failure verbatim
            failed.append({"id": tid, "sport": t.get("sport", ""), "url": url,
                           "error": f"{type(exc).__name__}: {exc}"})
            print(f"FAIL {tid:42s} {type(exc).__name__}: {exc}  {url}", flush=True)

    manifest = {
        "schema": "olbg4.board-an.capture/1",
        "session": "arena/a5456ba0-olbg4",
        "started_utc": stamp,
        "targets": len(targets),
        "ok": len(records),
        "failed": len(failed),
        "records": sorted(records, key=lambda r: r["id"]),
        "failures": failed,
    }
    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"{len(records)} ok / {len(failed)} failed -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

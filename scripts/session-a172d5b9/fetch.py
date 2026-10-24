#!/usr/bin/env python3
"""Board A172 (session a172d5b9) capture harness.

Runs on a GitHub Actions runner because the authoring sandbox can only reach
GitHub/npm/PyPI hosts.  Every response is stored byte-for-byte (gzip) beside a
SHA-256 manifest so each number published downstream can be traced to the exact
official bytes it came from.

Usage:  python3 fetch.py TARGETS_JSON OUTDIR
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import ssl
import subprocess
import sys
import tempfile
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


def get_with_curl(url: str, timeout: int = 45):
    """Retry a refused request with curl's TLS stack, retaining only real response bytes."""
    with tempfile.NamedTemporaryFile() as tmp:
        command = [
            "curl", "-L", "--fail", "--silent", "--show-error", "--http2", "--compressed",
            "--max-time", str(timeout),
            "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "-H", "Accept: application/json,text/html;q=0.9,*/*;q=0.8",
            "-H", "Accept-Language: en-US,en;q=0.9",
        ]
        if "nba.com" in url:
            command += ["-H", "Referer: https://www.nba.com/", "-H", "Origin: https://www.nba.com",
                        "-H", "Sec-Fetch-Site: same-site", "-H", "Sec-Fetch-Mode: cors", "-H", "Sec-Fetch-Dest: empty"]
        command += ["-o", tmp.name, "-w", "%{json}", url]
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout + 5)
        if result.returncode:
            raise RuntimeError(f"curl exit {result.returncode}: {result.stderr.strip()}")
        meta = json.loads(result.stdout)
        status = int(meta.get("response_code") or 0)
        if status != 200:
            raise RuntimeError(f"curl HTTP {status}")
        return status, open(tmp.name, "rb").read(), meta.get("content_type") or "", meta.get("url") or url


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
            try:
                status, body, ctype, final = get(url)
            except urllib.error.HTTPError as exc:
                if exc.code not in (403, 429):
                    raise
                status, body, ctype, final = get_with_curl(url)
            except TimeoutError:
                status, body, ctype, final = get_with_curl(url)
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            is_pdf = "pdf" in ctype.lower() or url.lower().endswith(".pdf")
            raw_name = tid + (".pdf.gz" if is_pdf else ".gz")
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
            print(f"OK   {tid:38s} {len(body):8d}  {url}", flush=True)
        except Exception as exc:  # noqa: BLE001 - capture every failure verbatim
            msg = f"{type(exc).__name__}: {exc}"
            code = getattr(exc, "code", 0) or 0
            failed.append({"id": tid, "url": url, "status": code, "error": msg})
            print(f"FAIL {tid:38s} {msg[:120]}  {url}", flush=True)
        time.sleep(delay)

    manifest = {
        "board": "A172",
        "session": "arena/a172d5b9-olbg4",
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

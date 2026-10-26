#!/usr/bin/env python3
"""Fetch every Board FB capture target (runner-side; open egress).

Writes one gzip file per target into ``data/session-53f83b8d/capture/<STAMP>/`` plus a
``manifest.json`` recording, for every target, the URL, HTTP status, byte count,
SHA-256 of the *uncompressed* body and the sport it belongs to. Failures are recorded
verbatim; nothing is fabricated, retried silently or replaced with a placeholder.

Stage 2 ("discovery") reads the OLBG hubs/all-events pages already captured and fetches
the individual OLBG event pages they link to, which is where OLBG keeps the per-market
prices for a single match.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
HDRS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.9",
    "Cache-Control": "no-cache",
}
ROOT = Path(__file__).resolve().parents[2]


def fetch(url: str, timeout: int = 45) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers=HDRS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def safe_name(target_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", target_id)[:120]


def run_target(t: dict, outdir: Path, results: list, failures: list, attempts: int = 3) -> None:
    last = None
    for i in range(attempts):
        try:
            status, body = fetch(t["url"])
            sha = hashlib.sha256(body).hexdigest()
            path = outdir / (safe_name(t["id"]) + ".gz")
            with gzip.open(path, "wb", compresslevel=9) as f:
                f.write(body)
            results.append({
                "id": t["id"], "sport": t.get("sport", ""), "kind": t.get("kind", ""),
                "tier": t.get("tier", ""), "url": t["url"], "status": status,
                "bytes": len(body), "sha256": sha, "file": path.name,
                "retrieved_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
            print(f"OK   {status} {len(body):9d}  {t['id']}  {t['url']}", flush=True)
            return
        except urllib.error.HTTPError as e:
            last = f"HTTPError: {e}"
            status = e.code
            if status in (403, 404, 410):
                break
        except Exception as e:  # noqa: BLE001 - recorded verbatim
            last = f"{type(e).__name__}: {e}"
        time.sleep(1.5 * (i + 1))
    failures.append({"id": t["id"], "sport": t.get("sport", ""), "kind": t.get("kind", ""),
                     "tier": t.get("tier", ""), "url": t["url"], "error": last,
                     "status": 0})
    print(f"FAIL       {t['id']}  {last}", flush=True)


EVENT_RE = re.compile(
    r'(?:eventUrl:"|href=")(/betting-tips/[A-Za-z_]+/[^"\\]*?/All_Events/[^"\\?]*?/\d+)(?:\?event_id=(\d+))?')


def discover_events(outdir: Path, results: list, max_per_sport: int) -> list[dict]:
    """Read captured OLBG pages and list the event pages they link to."""
    found: dict[str, dict[str, str]] = {}
    for r in results:
        if r["kind"] != "olbg" or r["sport"] in ("", "all"):
            continue
        p = outdir / r["file"]
        try:
            body = gzip.open(p, "rb").read().decode("utf-8", "replace")
        except Exception:  # noqa: BLE001
            continue
        for m in EVENT_RE.finditer(body):
            path = m.group(1)
            if "/All_Events/" not in path or path.endswith("/All_Events"):
                continue
            q = f"?event_id={m.group(2)}" if m.group(2) else ""
            url = urljoin("https://www.olbg.com", path) + q
            found.setdefault(r["sport"], {}).setdefault(url, r["id"])
    targets = []
    for sport, urls in found.items():
        for i, url in enumerate(list(urls)[:max_per_sport]):
            targets.append({"id": f"olbg_event_{sport.replace(' ', '')}_{i}", "sport": sport,
                            "kind": "olbg_event", "tier": "discovered", "url": url})
    return targets


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default=str(ROOT / "scripts/session-53f83b8d/targets.json"))
    ap.add_argument("--out", default=str(ROOT / "data/session-53f83b8d/capture"))
    ap.add_argument("--stamp", default=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--events-per-sport", type=int, default=8)
    ap.add_argument("--no-discovery", action="store_true")
    args = ap.parse_args()

    doc = json.loads(Path(args.targets).read_text())
    stamp = args.stamp
    if not re.fullmatch(r"\d{8}T\d{6}Z", stamp):
        raise SystemExit(f"bad --stamp {stamp!r}: expected YYYYmmddTHHMMSSZ")
    outdir = Path(args.out) / stamp
    outdir.mkdir(parents=True, exist_ok=True)

    started = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    results: list[dict] = []
    failures: list[dict] = []
    targets = doc["targets"]

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        list(ex.map(lambda t: run_target(t, outdir, results, failures), targets))

    discovered: list[dict] = []
    if not args.no_discovery:
        discovered = discover_events(outdir, results, args.events_per_sport)
        print(f"discovery: {len(discovered)} OLBG event pages", flush=True)
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            list(ex.map(lambda t: run_target(t, outdir, results, failures), discovered))

    manifest = {
        "board": "FB",
        "session": "53f83b8d",
        "stamp": stamp,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start": doc.get("window_start"),
        "window_end": doc.get("window_end"),
        "tool": "scripts/session-53f83b8d/fetch.py",
        "targets": len(targets) + len(discovered),
        "ok": len(results),
        "failed": len(failures),
        "records": sorted(results, key=lambda r: r["id"]),
        "failures": sorted(failures, key=lambda r: r["id"]),
    }
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"\ncaptured {len(results)} ok / {len(failures)} failed -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

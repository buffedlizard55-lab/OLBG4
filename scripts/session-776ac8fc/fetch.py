#!/usr/bin/env python3
"""Capture official source bytes for Board AO (session 776ac8fc).

The sandbox this board is developed in has no egress to olbg.com or any
governing-body / league / tour host (every request fails before connect), so
this script runs on a GitHub Actions runner and writes the raw response bytes
straight into the repository.  Nothing is parsed here: later stages read the
committed bytes so that every published value can be traced to a byte-for-byte
payload with a SHA-256.

Usage:
    python3 scripts/session-776ac8fc/fetch.py <targets.json> <stage-dir>
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

EXT_BY_TYPE = (
    ("json", ".json"),
    ("html", ".html"),
    ("xml", ".xml"),
    ("csv", ".csv"),
    ("text/plain", ".txt"),
)


def ext_for(content_type: str) -> str:
    ctype = (content_type or "").lower()
    for needle, ext in EXT_BY_TYPE:
        if needle in ctype:
            return ext
    return ".bin"


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(target: dict, stage_dir: str) -> dict:
    key = target["key"]
    url = target["url"]
    record = {
        "key": key,
        "url": url,
        "sport": target.get("sport", ""),
        "kind": target.get("kind", ""),
        "note": target.get("note", ""),
        "ok": False,
        "status": 0,
        "content_type": "",
        "bytes": 0,
        "sha256": "",
        "path": "",
        "error": "",
    }
    tmp = os.path.join(stage_dir, "_tmp_body")
    cmd = [
        "curl", "-sS", "--compressed", "-L", "--max-time", str(target.get("timeout", 45)),
        "-A", UA,
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", "Accept: application/json, text/html, application/xhtml+xml, */*;q=0.8",
        "-H", "Sec-Fetch-Mode: navigate",
        "-w", "\n%{http_code}\t%{content_type}\t%{size_download}\t%{url_effective}",
        "-o", tmp, url,
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=target.get("timeout", 45) + 20)
    except subprocess.TimeoutExpired:
        record["error"] = "curl-timeout"
        return record
    tail = (proc.stdout or "").strip().splitlines()
    meta = tail[-1].split("\t") if tail else []
    if len(meta) >= 4:
        try:
            record["status"] = int(meta[0])
        except ValueError:
            record["status"] = 0
        record["content_type"] = meta[1]
        try:
            record["bytes"] = int(meta[2])
        except ValueError:
            record["bytes"] = 0
        record["effective_url"] = meta[3]
    if proc.stderr.strip():
        record["curl_stderr"] = proc.stderr.strip()[:400]

    if not os.path.exists(tmp):
        record["error"] = record.get("error") or "no-body"
        return record
    ext = ext_for(record["content_type"])
    out_path = os.path.join(stage_dir, key + ext)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    os.replace(tmp, out_path)
    record["path"] = os.path.relpath(out_path, os.path.dirname(stage_dir.rstrip("/")))
    record["bytes"] = os.path.getsize(out_path)
    record["sha256"] = sha256_of(out_path)
    record["ok"] = 200 <= record["status"] < 300 and record["bytes"] > 0
    if not record["ok"] and not record["error"]:
        record["error"] = "http-%s" % record["status"]
    return record


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    targets_path, stage_dir = sys.argv[1], sys.argv[2].rstrip("/")
    with open(targets_path, encoding="utf-8") as handle:
        spec = json.load(handle)
    targets = spec["targets"] if isinstance(spec, dict) else spec
    os.makedirs(stage_dir, exist_ok=True)

    records = []
    for target in targets:
        record = fetch(target, stage_dir)
        records.append(record)
        flag = "OK  " if record["ok"] else "FAIL"
        print(
            "[%s] %-42s %3s %8s %s"
            % (flag, record["key"], record["status"], record["bytes"], record["url"]),
            flush=True,
        )

    manifest = {
        "board": "AO / arena/776ac8fc-olbg4",
        "captured_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "targets_file": os.path.basename(targets_path),
        "label": spec.get("label", "") if isinstance(spec, dict) else "",
        "count": len(records),
        "ok_count": sum(1 for r in records if r["ok"]),
        "targets": records,
    }
    with open(os.path.join(stage_dir, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=1, sort_keys=True)
        handle.write("\n")

    print(
        "\ncapture %s: %d/%d ok"
        % (manifest["captured_utc"], manifest["ok_count"], manifest["count"])
    )
    for record in records:
        if not record["ok"]:
            print("  failed %-40s %s %s" % (record["key"], record["status"], record["error"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

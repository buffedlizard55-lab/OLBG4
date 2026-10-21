"""HTTP helper with retries, backoff and an on-disk cache.

Only official league endpoints are called by providers. Every response is recorded in
`FETCH_LOG` so data/snapshot.json can show exactly which URLs produced the snapshot,
their HTTP status, byte size and SHA-256 of the payload. That is the audit trail used
by the verification gate.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from . import config

FETCH_LOG: list[dict] = []


def _cache_path(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()[:24]
    return os.path.join(config.CACHE_DIR, h + ".bin")


def _read_cache(url: str, max_age_seconds: int) -> bytes | None:
    path = _cache_path(url)
    try:
        if time.time() - os.path.getmtime(path) > max_age_seconds:
            return None
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def _write_cache(url: str, payload: bytes) -> None:
    try:
        os.makedirs(config.CACHE_DIR, exist_ok=True)
        with open(_cache_path(url), "wb") as fh:
            fh.write(payload)
    except OSError:
        pass


def fetch_bytes(url: str, headers: dict | None = None, cache_seconds: int = 0) -> bytes:
    """GET a URL, with retries. Raises RuntimeError after the last failure."""
    if cache_seconds:
        cached = _read_cache(url, cache_seconds)
        if cached is not None:
            FETCH_LOG.append(
                {
                    "url": url,
                    "status": 200,
                    "bytes": len(cached),
                    "sha256": hashlib.sha256(cached).hexdigest(),
                    "cached": True,
                    "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
            return cached

    hdrs = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip",
    }
    if headers:
        hdrs.update(headers)

    last_err: Exception | None = None
    for attempt in range(1, config.HTTP_RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=hdrs)
            with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                    try:
                        raw = gzip.decompress(raw)
                    except OSError:
                        pass
                status = resp.status
            if status != 200:
                raise RuntimeError(f"HTTP {status}")
            _write_cache(url, raw) if cache_seconds else None
            FETCH_LOG.append(
                {
                    "url": url,
                    "status": status,
                    "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "cached": False,
                    "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                }
            )
            return raw
        except urllib.error.HTTPError as exc:
            last_err = exc
            if 400 <= exc.code < 500:  # client errors are deterministic; do not hammer
                break
            if attempt < config.HTTP_RETRIES:
                time.sleep(min(2 ** attempt, 8))
        except Exception as exc:  # noqa: BLE001 - network layer
            last_err = exc
            if attempt < config.HTTP_RETRIES:
                time.sleep(min(2 ** attempt, 8))
    FETCH_LOG.append(
        {
            "url": url,
            "status": None,
            "error": f"{type(last_err).__name__}: {last_err}",
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_json_curl(url: str, headers: dict | None = None, timeout: int = 45):
    """Fetch JSON with the system curl.

    Some league edges (notably cdn.nba.com) fingerprint the TLS client and reject Python's
    ssl stack with 403 no matter which headers are sent. curl negotiates HTTP/2 and a
    different TLS profile, so it is kept as an explicit fallback: the caller tries urllib
    first, and only falls back when the response was refused. Every attempt is logged.
    """
    import subprocess

    hdrs = {
        "User-Agent": config.USER_AGENT,
        "Accept": "application/json, text/plain, */*",
    }
    if headers:
        hdrs.update(headers)
    cmd = ["curl", "-sS", "-L", "--compressed", "--http2", "--max-time", str(timeout)]
    for key, value in hdrs.items():
        cmd += ["-H", f"{key}: {value}"]
    cmd.append(url)
    proc = subprocess.run(cmd, capture_output=True)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if proc.returncode != 0 or not proc.stdout:
        detail = (proc.stderr or b"").decode("utf-8", "replace").strip()[:200]
        FETCH_LOG.append(
            {"url": url, "status": None, "transport": "curl",
             "error": f"curl exit {proc.returncode}: {detail}", "retrieved_utc": now}
        )
        raise RuntimeError(f"curl failed for {url}: exit {proc.returncode} {detail}")
    payload = proc.stdout
    status = 200
    FETCH_LOG.append(
        {
            "url": url,
            "status": status,
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "cached": False,
            "transport": "curl",
            "retrieved_utc": now,
        }
    )
    return json.loads(payload.decode("utf-8", "replace"))


def fetch_json(url: str, headers: dict | None = None, cache_seconds: int = 0):
    payload = fetch_bytes(url, headers=headers, cache_seconds=cache_seconds)
    return json.loads(payload.decode("utf-8", "replace"))


def fetch_text(url: str, headers: dict | None = None, cache_seconds: int = 0) -> str:
    return fetch_bytes(url, headers=headers, cache_seconds=cache_seconds).decode(
        "utf-8", "replace"
    )


def with_query(base: str, **params) -> str:
    sep = "&" if "?" in base else "?"
    return base + sep + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})

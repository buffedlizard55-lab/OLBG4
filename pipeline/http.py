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

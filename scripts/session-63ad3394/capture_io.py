"""Shared capture reader for Board AK (session arena/63ad3394-olbg4).

The capture stores gzip payloads named ``<target-id>.<ext>.gz`` next to a
``manifest.json`` that records the SHA-256 of the *uncompressed* bytes. Every
parser in this session goes through :func:`read_capture` so a payload that no
longer matches its manifest hash is rejected rather than silently summarised.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path


def load_manifest(cap_dir: str | Path) -> dict:
    return json.loads((Path(cap_dir) / "manifest.json").read_text())


def read_capture(cap_dir: str | Path, rec: dict) -> bytes:
    path = Path(cap_dir) / rec["file"]
    raw = gzip.decompress(path.read_bytes())
    digest = hashlib.sha256(raw).hexdigest()
    if digest != rec["sha256"]:
        raise SystemExit(f"capture hash mismatch for {rec['id']}: {digest} != {rec['sha256']}")
    return raw


def text(cap_dir: str | Path, rec: dict) -> str:
    return read_capture(cap_dir, rec).decode("utf-8", "replace")


def by_id(manifest: dict) -> dict[str, dict]:
    return {r["id"]: r for r in manifest.get("records", [])}


def strip_html(html: str) -> str:
    import re
    s = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&nbsp;?", " ", s)
    s = re.sub(r"&amp;", "&", s)
    s = re.sub(r"&#0?39;|&apos;", "'", s)
    s = re.sub(r"&quot;", '"', s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def parse_iso(ts: str) -> str | None:
    """Return a canonical ``YYYY-MM-DDTHH:MM:SSZ`` from the shapes OLBG/feeds use."""
    from datetime import datetime, timezone
    if not ts:
        return None
    ts = ts.strip().replace("Z", "+00:00")
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return None

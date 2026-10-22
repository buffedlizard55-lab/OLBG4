#!/usr/bin/env python3
"""Shared evidence, time and JSON helpers for Board AF.

Every source value used by the desk is read from a byte-exact capture.  A manifest
entry is not treated as usable merely because it exists: HTTP status, non-empty
body, JSON parsing and SHA-256 are all checked before a provider sees it.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-0d3b826c"
SITE = ROOT / "session-0d3b826c"
WINDOW_END = "2026-11-08T23:59:59Z"


def iso_z(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        # Naive values are never silently interpreted as UTC by providers.
        raise ValueError(f"Timezone missing from source timestamp: {value}")
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def in_window(start: str, cutoff: str) -> bool:
    return bool(start) and cutoff < start <= WINDOW_END


def norm(value: str | None) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower().replace("&", " and ")
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def slug(value: str) -> str:
    return norm(value).replace(" ", "-")


def dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def american(decimal: float) -> int:
    if decimal <= 1.0:
        raise ValueError("Decimal price must exceed 1")
    if decimal >= 2.0:
        return int(round((decimal - 1.0) * 100))
    return -int(round(100 / (decimal - 1.0)))


def price(probability: float) -> dict[str, Any]:
    p = round(float(probability), 6)
    if not 0.0 < p < 1.0:
        raise ValueError(f"Invalid probability {p}")
    dec = round(1.0 / p, 3)
    return {"probability": p, "decimal": dec, "american": american(dec)}


def focus_price(pr: dict[str, Any]) -> bool:
    """The brief's American-odds window, evaluated on our fair price.

    Negative American prices run from -250 through -100; positive prices run
    from +100 through +10000.  Values between -100 and +100 are not valid
    American-price representations and are excluded explicitly.
    """
    am = pr["american"]
    return 1.4 <= pr["decimal"] <= 101.0 and (-250 <= am <= -100 or 100 <= am <= 10000)


def words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, flags=re.UNICODE))


class Capture:
    def __init__(self, path: str | os.PathLike[str] | None = None):
        if path:
            self.path = Path(path)
            if not self.path.is_absolute():
                self.path = ROOT / self.path
        elif os.environ.get("AF_CAPTURE"):
            self.path = Path(os.environ["AF_CAPTURE"])
            if not self.path.is_absolute():
                self.path = ROOT / self.path
        else:
            candidates = sorted((DATA / "capture").glob("*/manifest.json"))
            if not candidates:
                raise FileNotFoundError("No Board AF capture manifest found")
            self.path = candidates[-1].parent
        self.manifest = load(self.path / "manifest.json")
        self.items = {item["id"]: item for item in self.manifest["items"]}
        if len(self.items) != len(self.manifest["items"]):
            raise ValueError("Duplicate capture target IDs")
        self.cutoff = self.manifest["generated_utc"]
        self.capture_id = self.path.name
        self._verified: set[str] = set()

    def verify_hashes(self) -> int:
        for source_id, item in self.items.items():
            body = self.bytes(source_id)
            if len(body) != item["bytes"]:
                raise ValueError(f"Byte length mismatch: {source_id}")
            if hashlib.sha256(body).hexdigest() != item["sha256"]:
                raise ValueError(f"SHA-256 mismatch: {source_id}")
            self._verified.add(source_id)
        return len(self._verified)

    def bytes(self, source_id: str) -> bytes:
        item = self.items[source_id]
        with gzip.open(self.path / item["file"], "rb") as handle:
            return handle.read()

    def text(self, source_id: str) -> str:
        return self.bytes(source_id).decode("utf-8", "replace")

    def usable(self, source_id: str) -> bool:
        item = self.items.get(source_id)
        return bool(item and item.get("status") == 200 and item.get("bytes", 0) > 0)

    def json(self, source_id: str) -> Any:
        if not self.usable(source_id):
            raise ValueError(f"Source unavailable: {source_id} ({self.items.get(source_id)})")
        body = self.bytes(source_id)
        # Some CDN failures are HTTP 200 HTML error pages. Never parse them as data.
        if body.lstrip().startswith((b"<HTML", b"<html", b"<!DOCTYPE", b"<!doctype")):
            raise ValueError(f"HTML error page instead of JSON: {source_id}")
        return json.loads(body)

    def url(self, source_id: str) -> str:
        return self.items[source_id]["url"]

    def evidence(self, *source_ids: str) -> list[dict[str, Any]]:
        result = []
        for source_id in source_ids:
            item = self.items[source_id]
            result.append({
                "id": source_id,
                "url": item["url"],
                "http_status": item["status"],
                "sha256": item["sha256"],
                "bytes": item["bytes"],
                "fetched_utc": item["fetched_utc"],
                "file": f"data/session-0d3b826c/capture/{self.capture_id}/{item['file']}",
            })
        return result

    def source_rows(self) -> list[dict[str, Any]]:
        rows = []
        for item in self.manifest["items"]:
            host = urlparse(item["url"]).netloc
            kind = "OLBG structure only" if host.endswith("olbg.com") else "Official sports source"
            rows.append({**item, "kind": kind, "host": host})
        return rows

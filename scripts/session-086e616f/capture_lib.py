#!/usr/bin/env python3
"""Board AT — capture store reader.

Every published value on this desk must be traceable to bytes that an open-egress GitHub
Actions runner fetched from an official source and committed under
``data/session-086e616f/capture/<STAMP>/``. This module is the only way Board AT code reads
those bytes, and it:

  * re-hashes every payload against the committed SHA-256 manifest before returning it, so a
    corrupted or edited capture cannot silently feed the desk;
  * records the SHA-256, the capture stamp, the request URL and the final URL on every payload
    it hands out, so each desk row can carry its own provenance;
  * refuses to invent a payload for a target that was not captured or did not return HTTP 200.

Nothing here touches the network.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = ROOT / "data" / "session-086e616f" / "capture"
OUT_ROOT = ROOT / "data" / "session-086e616f"


def stamps() -> list[str]:
    return sorted(p.name for p in CAPTURE_ROOT.iterdir() if p.is_dir() and (p / "manifest.json").exists())


class Capture:
    """A read-only, hash-verified view over every committed capture stamp."""

    def __init__(self) -> None:
        self.stamps_list = stamps()
        self.manifests: dict[str, dict] = {}
        self.index: dict[str, dict] = {}
        for stamp in self.stamps_list:
            man = json.loads((CAPTURE_ROOT / stamp / "manifest.json").read_text())
            self.manifests[stamp] = man
            for rec in man["records"]:
                if rec.get("status") != 200 or not rec.get("file"):
                    continue
                prev = self.index.get(rec["id"])
                # newest stamp wins, so a refresh always supersedes the earlier capture
                if prev is None or prev["stamp"] < stamp:
                    self.index[rec["id"]] = dict(rec, stamp=stamp)
        self._cache: dict[str, bytes] = {}
        self.failures: list[dict] = []
        for stamp in self.stamps_list:
            for rec in self.manifests[stamp]["records"]:
                if rec.get("status") != 200:
                    self.failures.append(dict(rec, stamp=stamp))

    # ------------------------------------------------------------------ lookups
    def have(self, target_id: str) -> bool:
        return target_id in self.index

    def ids(self) -> list[str]:
        return sorted(self.index)

    def record(self, target_id: str) -> dict | None:
        return self.index.get(target_id)

    def url(self, target_id: str) -> str | None:
        rec = self.index.get(target_id)
        return rec["final_url"] or rec["url"] if rec else None

    def provenance(self, target_id: str) -> dict:
        rec = self.index.get(target_id)
        if not rec:
            raise KeyError(f"target {target_id!r} was not captured with HTTP 200")
        return {
            "capture_id": rec["stamp"],
            "capture_sha256": rec["sha256"],
            "capture_url": rec["url"],
            "source_url": rec["final_url"] or rec["url"],
            "captured_bytes": rec["bytes"],
            "captured_utc": self.manifests[rec["stamp"]]["started_utc"],
        }

    # ------------------------------------------------------------------ payloads
    def bytes(self, target_id: str) -> bytes:
        if target_id in self._cache:
            return self._cache[target_id]
        rec = self.index.get(target_id)
        if not rec:
            raise KeyError(f"target {target_id!r} was not captured with HTTP 200")
        path = CAPTURE_ROOT / rec["stamp"] / rec["file"]
        raw = path.read_bytes()
        payload = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        digest = hashlib.sha256(payload).hexdigest()
        if digest != rec["sha256"]:
            raise ValueError(
                f"capture integrity failure for {target_id}: manifest {rec['sha256']} != recomputed {digest}"
            )
        self._cache[target_id] = payload
        return payload

    def text(self, target_id: str) -> str:
        return self.bytes(target_id).decode("utf-8", "replace")

    def json(self, target_id: str) -> Any:
        return json.loads(self.bytes(target_id))

    def summary(self) -> dict:
        per_stamp = {
            s: {
                "targets": m["targets"],
                "ok": m["ok"],
                "failed": m["failed"],
                "started_utc": m["started_utc"],
                "finished_utc": m["finished_utc"],
            }
            for s, m in self.manifests.items()
        }
        return {
            "stamps": self.stamps_list,
            "per_stamp": per_stamp,
            "usable_targets": len(self.index),
            "failed_targets": len(self.failures),
        }


# ---------------------------------------------------------------------- html helpers
def strip_scripts(html_text: str) -> str:
    s = re.sub(r"<script\b.*?</script>", " ", html_text, flags=re.S | re.I)
    s = re.sub(r"<style\b.*?</style>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    return s


def to_text(html_text: str, keep_newlines: bool = False) -> str:
    s = strip_scripts(html_text)
    s = re.sub(r"<br\s*/?>", "\n" if keep_newlines else " ", s, flags=re.I)
    s = re.sub(r"</(p|div|li|tr|h[1-6]|td|th)>", "\n" if keep_newlines else " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = (s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
          .replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">")
          .replace("&#8209;", "-").replace("&#8217;", "'").replace("&#8211;", "-")
          .replace("&pound;", "£").replace("&#163;", "£").replace("&#8220;", '"')
          .replace("&#8221;", '"').replace("\xa0", " "))
    s = re.sub(r"[ \t\r\f\v]+", " ", s)
    s = re.sub(r"\n\s*\n+", "\n", s)
    return s.strip()


def html_tables(html_text: str) -> list[list[list[str]]]:
    """Return every <table> as a list of rows of cell texts."""
    out = []
    for tbl in re.findall(r"<table\b.*?</table>", strip_scripts(html_text), flags=re.S | re.I):
        rows = []
        for tr in re.findall(r"<tr\b.*?</tr>", tbl, flags=re.S | re.I):
            cells = []
            for c in re.findall(r"<t[dh]\b[^>]*>(.*?)</t[dh]>", tr, flags=re.S | re.I):
                c = re.sub(r"<br\s*/?>", "\n", c, flags=re.I)
                c = re.sub(r"<[^>]+>", " ", c)
                c = (c.replace("&nbsp;", " ").replace("&amp;", "&").replace("&#39;", "'")
                      .replace("&pound;", "£").replace("&#8209;", "-").replace("&#8217;", "'")
                      .replace("&quot;", '"').replace("\xa0", " "))
                cells.append(re.sub(r"[ \t\r\n]+", " ", c).strip())
            if cells:
                rows.append(cells)
        if rows:
            out.append(rows)
    return out


def sha256_file(path: str | os.PathLike) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n")

#!/usr/bin/env python3
"""Reverse-engineer the OLBG sport hubs from the committed capture bytes.

OLBG renders each ``/betting-tips/<Sport>/<id>`` hub server-side with a SvelteKit
hydration payload. That payload embeds two arrays we care about:

  ``tips:[{...}]``        every listed tip row: selection, market alias, decimal /
                          American / fractional price, event name, event start
                          (unix), event URL, league, expert and comment counts,
                          and an ``expired`` flag.
  ``tournaments:[{...}]`` outright/tournament markets (used on hubs whose
                          listings are outrights rather than fixtures).

Nothing on this page is treated as truth: the desk only uses OLBG for (a) the
sport/market taxonomy and (b) the list of events OLBG is currently listing. Each
event is then matched to an official fixture before any value is published.

Usage: python3 scripts/session-63ad3394/parse_olbg.py <capture_dir> <out.json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from capture_io import read_capture, load_manifest


def _objects(text: str, key: str) -> list[str]:
    """Return the raw source of every top-level object inside ``key:[ ... ]``.

    The payload is a JS object literal (unquoted keys, quoted strings), so the
    array is walked with a small brace/string-aware scanner rather than a regex.
    """
    out: list[str] = []
    for m in re.finditer(re.escape(f"{key}:[") , text):
        i = m.end() - 1  # at '['
        depth, in_str, esc = 0, False, False
        obj_start = None
        j = i
        while j < len(text):
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    break
            elif ch == "{" and depth == 1:
                obj_start = j
                obj_depth = 0
                k = j
                in_s, es = False, False
                while k < len(text):
                    c = text[k]
                    if in_s:
                        if es:
                            es = False
                        elif c == "\\":
                            es = True
                        elif c == '"':
                            in_s = False
                    elif c == '"':
                        in_s = True
                    elif c == "{":
                        obj_depth += 1
                    elif c == "}":
                        obj_depth -= 1
                        if obj_depth == 0:
                            out.append(text[obj_start:k + 1])
                            j = k
                            break
                    k += 1
            j += 1
        if out:
            break
    return out


FIELD = re.compile(r'([A-Za-z_][A-Za-z0-9_]*)\s*:\s*("(?:[^"\\]|\\.)*"|[^,}]+)')


def fields(obj: str) -> dict:
    rec = {}
    for k, v in FIELD.findall(obj):
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = v[1:-1].replace('\\"', '"').replace("\\/", "/")
        elif v in ("null", "true", "false"):
            v = {"null": None, "true": True, "false": False}[v]
        else:
            try:
                v = int(v) if re.fullmatch(r"-?\d+", v) else float(v)
            except ValueError:
                pass
        rec[k] = v
    return rec


HUB = re.compile(r"olbg_([a-z0-9_]+)_(\d+)$")


def main() -> int:
    cap_dir, out_path = sys.argv[1], sys.argv[2]
    manifest = load_manifest(cap_dir)
    rows, hubs = [], []
    for rec in manifest.get("records", []):
        tid = rec.get("id", "")
        m = HUB.match(tid)
        if not m or rec.get("status") != 200:
            continue
        sport_slug, sport_id = m.group(1), m.group(2)
        text = read_capture(cap_dir, rec).decode("utf-8", "replace")
        tips = [fields(o) for o in _objects(text, "tips")]
        tours = [fields(o) for o in _objects(text, "tournaments")]
        hubs.append({
            "target": tid, "sport_slug": sport_slug, "sport_id": sport_id,
            "url": rec["url"], "sha256": rec.get("sha256"), "bytes": rec.get("bytes"),
            "tip_rows": len(tips), "tournament_rows": len(tours),
            "market_aliases": sorted({t.get("market_alias") for t in tips if t.get("market_alias")}),
            "leagues": sorted({t.get("menu_league") for t in tips if t.get("menu_league")}),
        })
        for t in tips:
            rows.append({
                "hub": tid, "sport_id": sport_id,
                "event": t.get("event_name_alias"),
                "event_url": ("https://www.olbg.com" + t["eventUrl"]) if t.get("eventUrl") else None,
                "league": t.get("menu_league"),
                "selection": t.get("selection"),
                "market_alias": t.get("market_alias"),
                "decimal": t.get("odds"),
                "american": t.get("american_odds"),
                "start_unix": t.get("event_start_unix_timestamp"),
                "expired": t.get("expired"),
                "experts": t.get("experts_count"),
                "comments": t.get("comments_count"),
                "confidence": t.get("confidence"),
                "source_sha256": rec.get("sha256"),
            })
    payload = {"schema": "olbg4.board-ak.olbg-listing/1", "capture": Path(cap_dir).name,
               "hubs": hubs, "tips": rows}
    Path(out_path).write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"hubs={len(hubs)} tips={len(rows)} -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

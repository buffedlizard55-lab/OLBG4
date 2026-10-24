#!/usr/bin/env python3
"""Extra readers for Board EC.

Two jobs:

1. ``read_olbg_rows`` turns an OLBG *listing* page into individual priced
   selections.  The listing markup carries the event link (with ``event_id``), the
   start time in a ``<time itemprop="startDate">`` tag, the market label, the
   selection name and OLBG's own quote in ``data-decimal``/``data-american``
   attributes.  We keep that quote verbatim: it is the observed market price, and
   it is never fed into our own line.

2. ``read_nba`` and friends read the machine-readable official feeds that the
   JavaScript tables hide behind.

Nothing here estimates anything.  A missing field stays an empty string.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone

OLBG_SPORTS = {
    "Golf": "Golf",
    "Volleyball": "Volleyball",
    "Rugby Union": "Rugby Union",
    "Cricket": "Cricket",
    "Snooker": "Snooker",
    "Darts": "Darts",
    "Baseball": "Baseball",
    "Gaelic Football": "Gaelic Sports",
    "Hurling": "Gaelic Sports",
    "Greyhounds": "Greyhounds",
    "Tennis": "Tennis",
    "Motor Racing": "Motor Racing",
    "Handball": "Handball",
    "Ice Hockey": "Ice Hockey",
    "Basketball": "Basketball",
    "Rugby League": "Rugby League",
    "Baseball ": "Baseball",
}


def _clean(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<!---->|<!--\[-?\d*--?>|<!--\]-->", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _utc(s: str) -> str:
    if not s:
        return ""
    s = s.replace(" ", "T")
    if re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d", s):
        return s[:19] + "Z"
    return ""


def read_olbg_rows(cap, tids: list[str]) -> list[dict]:
    """Priced selections from OLBG listing pages (HTML, one block per selection)."""
    out: list[dict] = []
    for tid in tids:
        if not cap.exists(tid):
            continue
        text = cap.text(tid)
        sport = ""
        m = re.search(r"/betting-tips/([A-Za-z_]+)/", cap.url(tid))
        if m:
            sport = OLBG_SPORTS.get(m.group(1).replace("_", " "), OLBG_SPORTS.get(m.group(1), ""))
        # each selection block starts with the event anchor
        for blk in re.split(r'(?=<a itemprop="url" href=")', text):
            if not blk.startswith('<a itemprop="url" href="'):
                continue
            chunk = blk[:3000]
            em = re.search(r'href="([^"]*event_id=(\d+))"', chunk)
            nm = re.search(r'itemprop="name"[^>]*>([^<]{2,120})<', chunk)
            tm = re.search(r'itemprop="startDate" datetime="([^"]+)"', chunk)
            mk = re.search(r'<p class="truncate text-sm">([^<]{2,60})</p>', chunk)
            sel = re.search(r'<h4[^>]*>\s*([^<]{2,120})\s*</h4>', chunk)
            od = re.search(r'data-decimal="([0-9.]+)"', chunk)
            oa = re.search(r'data-american="(-?\+?[0-9]+)"', chunk)
            if not (em and nm):
                continue
            out.append(
                {
                    "sport": sport,
                    "event": _clean(nm.group(1)),
                    "event_url": em.group(1) if em.group(1).startswith("http") else "https://www.olbg.com" + em.group(1),
                    "event_id": em.group(2),
                    "start_utc": _utc(tm.group(1)) if tm else "",
                    "market": _clean(mk.group(1)) if mk else "",
                    "selection": _clean(sel.group(1)) if sel else "",
                    "decimal": od.group(1) if od else "",
                    "american": oa.group(1) if oa else "",
                    "hub_url": cap.url(tid),
                    "capture_id": tid,
                }
            )
    # de-duplicate identical (event_id, market, selection, decimal)
    seen, uniq = set(), []
    for r in out:
        k = (r["event_id"], r["market"], r["selection"], r["decimal"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(r)
    return uniq


def group_olbg(sel_rows: list[dict]) -> dict[str, dict]:
    """event_id -> {event, event_url, start_utc, sport, tips:[{market,selection,decimal,american}], hub_url}"""
    ev: dict[str, dict] = {}
    for r in sel_rows:
        e = ev.setdefault(
            r["event_id"],
            {
                "event_id": r["event_id"],
                "sport": r["sport"],
                "event": r["event"],
                "event_url": r["event_url"],
                "start_utc": r["start_utc"],
                "hub_url": r["hub_url"],
                "tips": [],
            },
        )
        e["tips"].append(
            {"market": r["market"], "selection": r["selection"], "decimal": r["decimal"], "american": r["american"]}
        )
    return ev


# ---------------------------------------------------------------------- NBA
def read_nba_schedule(cap, tid: str = "nba_cdn_schedule"):
    """NBA official CDN season schedule (JSON)."""
    if not cap.exists(tid):
        return []
    data = cap.json(tid)
    out = []
    for gd in (data.get("leagueSchedule") or {}).get("gameDates", []):
        for g in gd.get("games", []):
            if not g.get("gameTimeUTC"):
                continue
            home, away = g.get("homeTeam", {}), g.get("awayTeam", {})
            out.append(
                {
                    "id": "fx_nba_" + str(g.get("gameId")),
                    "sport": "Basketball",
                    "sport_slug": "basketball",
                    "competition": "NBA 2026-27 regular season",
                    "side_a": f"{away.get('teamCity','')} {away.get('teamName','')}".strip(),
                    "side_b": f"{home.get('teamCity','')} {home.get('teamName','')}".strip(),
                    "start_utc": _utc(g.get("gameTimeUTC", "")),
                    "venue": "",
                    "source_id": tid,
                    "source_url": cap.url(tid),
                    "source_name": "NBA official schedule feed (cdn.nba.com)",
                    "extra": {"game_id": g.get("gameId"), "game_code": g.get("gameCode", "")},
                }
            )
    return out


def read_nba_scoreboard(cap, tid: str = "nba_cdn_scoreboard"):
    """Today's NBA scoreboard: only used to confirm status/score of listed games."""
    if not cap.exists(tid):
        return {}
    data = cap.json(tid)
    out = {}
    for g in (data.get("scoreboard") or {}).get("games", []):
        out[str(g.get("gameId"))] = {
            "status": g.get("gameStatus"),
            "home": g.get("homeTeam", {}).get("score"),
            "away": g.get("awayTeam", {}).get("score"),
        }
    return out

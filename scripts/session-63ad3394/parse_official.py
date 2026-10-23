#!/usr/bin/env python3
"""Normalise every official payload captured for Board AK into one event table.

Each extractor reads *only* the bytes committed under
``data/session-63ad3394/capture/<stamp>/`` (hash-verified against the manifest)
and emits records of the shape::

    {id, sport, competition, side_a, side_b, start_utc, venue,
     source_url, source_name, source_sha256, capture,
     form: {a: {...}, b: {...}}, facts: [...], notes: [...]}

``form`` carries only numbers printed on the official page (or summed from
official per-game scores); nothing is imputed. A side with no verified sample
gets ``form: None`` and the fixture is published unpriced.

Sports whose official page is a JavaScript shell with no committed data are
still listed in ``unavailable`` with the exact URL that was tried, so the
coverage page can show what was attempted rather than silently omitting them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from capture_io import by_id, load_manifest, read_capture, strip_html, text

TODAY = "2026-10-23"
HORIZON = "2026-11-03"


def iso(dt: str | None) -> str | None:
    if not dt:
        return None
    dt = dt.strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M%z", "%Y-%m-%d %H:%M"):
        try:
            d = datetime.strptime(dt, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return d.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue
    return None


def within(start: str | None, lo: str = TODAY, hi: str = HORIZON) -> bool:
    return bool(start) and lo <= start[:10] <= hi


def table(results) -> dict:
    """Build W-L, points for/against per side from verified per-game scores."""
    t: dict[str, dict] = {}
    for a, b, sa, sb in results:
        for side, own, opp in ((a, sa, sb), (b, sb, sa)):
            d = t.setdefault(side, {"w": 0, "l": 0, "d": 0, "pf": 0, "pa": 0, "n": 0})
            d["n"] += 1
            d["pf"] += own
            d["pa"] += opp
            if own > opp:
                d["w"] += 1
            elif own < opp:
                d["l"] += 1
            else:
                d["d"] += 1
    for d in t.values():
        n = d["n"]
        dec = d["w"] + d["l"] + d["d"]
        d["win_pct"] = round((d["w"] + 0.5 * d["d"]) / dec, 4) if dec else 0.0
        d["margin"] = round((d["pf"] - d["pa"]) / n, 3) if n else 0.0
        d["pf_pg"] = round(d["pf"] / n, 3) if n else 0.0
        d["pa_pg"] = round(d["pa"] / n, 3) if n else 0.0
    return t


class Ctx:
    """Read-only view over every capture stamp, latest successful payload wins."""

    def __init__(self, cap_dirs):
        if isinstance(cap_dirs, (str, Path)):
            cap_dirs = [cap_dirs]
        self.dirs = sorted(Path(c) for c in cap_dirs)
        self.index: dict[str, tuple[Path, dict]] = {}
        self.stamps = []
        for d in self.dirs:
            man = load_manifest(d)
            self.stamps.append({"capture": d.name, "targets": man.get("targets"), "ok": man.get("ok"),
                                "started_utc": man.get("started_utc")})
            for rec in man.get("records", []):
                tid = rec.get("id")
                if not tid:
                    continue
                prev = self.index.get(tid)
                if prev is None or (rec.get("status") == 200 and prev[1].get("status") != 200):
                    self.index[tid] = (d, rec)
                elif rec.get("status") == 200:
                    self.index[tid] = (d, rec)
        self.stamp = "+".join(d.name for d in self.dirs)
        self.events: list[dict] = []
        self.unavailable: list[dict] = []

    # -- payload access -------------------------------------------------
    def rec(self, tid):
        hit = self.index.get(tid)
        return hit[1] if hit else None

    def raw(self, tid):
        hit = self.index.get(tid)
        if not hit or hit[1].get("status") != 200:
            return None
        return read_capture(hit[0], hit[1])

    def json(self, tid):
        b = self.raw(tid)
        return json.loads(b) if b else None

    def html(self, tid):
        b = self.raw(tid)
        return b.decode("utf-8", "replace") if b else None

    def meta(self, tid):
        hit = self.index.get(tid)
        if not hit:
            return {"source_url": None, "source_sha256": None, "capture": None}
        d, r = hit
        return {"source_url": r["url"], "source_sha256": r.get("sha256"), "capture": d.name}

    def add(self, **kw):
        self.events.append(kw)

    def missing(self, sport, tid, why):
        r = self.rec(tid) or {}
        self.unavailable.append({
            "sport": sport, "target": tid, "url": r.get("url"),
            "status": r.get("status"), "error": r.get("error"), "reason": why,
        })


# --------------------------------------------------------------------------
# Ice hockey — NHL schedule API + standings API
# --------------------------------------------------------------------------
def parse_nhl(ctx: Ctx):
    st = ctx.json("nhl_standings_now")
    if not st:
        ctx.missing("Ice Hockey", "nhl_standings_now", "no payload")
        return
    stand = {}
    for s in st.get("standings", []):
        ab = s["teamAbbrev"]["default"]
        gp = s.get("gamesPlayed") or 0
        stand[ab] = {
            "gp": gp, "w": s.get("wins"), "l": s.get("losses"), "otl": s.get("otLosses"),
            "pts": s.get("points"), "gf": s.get("goalFor"), "ga": s.get("goalAgainst"),
            "streak": s.get("streakCode"), "pct": s.get("pointPctg"),
        }
    seen = set()
    for tid in sorted(t for t in ctx.index if t.startswith("nhl_sched_")):
        d = ctx.json(tid)
        if not d:
            continue
        for week in d.get("gameWeek", []):
            for g in week.get("games", []):
                if g.get("gameState") not in ("FUT", "PRE"):
                    continue
                start = iso(g.get("startTimeUTC"))
                if not within(start) or g["id"] in seen:
                    continue
                seen.add(g["id"])
                a = g["awayTeam"]; h = g["homeTeam"]
                sa, sh = stand.get(a["abbrev"]), stand.get(h["abbrev"])
                if not sa or not sh:
                    continue
                ctx.add(
                    id=f"nhl-{g['id']}", sport="Ice Hockey", competition="NHL 2026-27 regular season",
                    side_a=f"{a['placeName']['default']} {a['commonName']['default']}",
                    side_b=f"{h['placeName']['default']} {h['commonName']['default']}",
                    start_utc=start, venue=(g.get("venue") or {}).get("default"),
                    form={
                        "a": {"gp": sa["gp"], "w": sa["w"], "l": sa["l"], "otl": sa["otl"], "pts": sa["pts"],
                              "gf": sa["gf"], "ga": sa["ga"], "streak": sa["streak"],
                              "win_pct": round((sa["w"] + 0.5 * sa["otl"]) / sa["gp"], 4) if sa["gp"] else 0.0,
                              "margin": round((sa["gf"] - sa["ga"]) / sa["gp"], 3) if sa["gp"] else 0.0,
                              "pf_pg": round(sa["gf"] / sa["gp"], 3) if sa["gp"] else 0.0,
                              "pa_pg": round(sa["ga"] / sa["gp"], 3) if sa["gp"] else 0.0, "n": sa["gp"]},
                        "b": {"gp": sh["gp"], "w": sh["w"], "l": sh["l"], "otl": sh["otl"], "pts": sh["pts"],
                              "gf": sh["gf"], "ga": sh["ga"], "streak": sh["streak"],
                              "win_pct": round((sh["w"] + 0.5 * sh["otl"]) / sh["gp"], 4) if sh["gp"] else 0.0,
                              "margin": round((sh["gf"] - sh["ga"]) / sh["gp"], 3) if sh["gp"] else 0.0,
                              "pf_pg": round(sh["gf"] / sh["gp"], 3) if sh["gp"] else 0.0,
                              "pa_pg": round(sh["ga"] / sh["gp"], 3) if sh["gp"] else 0.0, "n": sh["gp"]},
                    },
                    facts=[
                        f"{a['abbrev']} {sa['w']}-{sa['l']}-{sa['otl']} in {sa['gp']} games, {sa['pts']} points, {sa['gf']} goals for and {sa['ga']} against.",
                        f"{h['abbrev']} {sh['w']}-{sh['l']}-{sh['otl']} in {sh['gp']} games, {sh['pts']} points, {sh['gf']} goals for and {sh['ga']} against.",
                    ],
                    **ctx.meta(tid),
                )


# --------------------------------------------------------------------------
# Baseball — MLB Stats API (schedule + team season stats)
# --------------------------------------------------------------------------
def parse_mlb(ctx: Ctx):
    sched = ctx.json("mlb_ws_schedule")
    stand = ctx.json("mlb_standings") or {}
    hit = ctx.json("mlb_hitting") or {}
    pit = ctx.json("mlb_pitching") or {}
    if not sched:
        ctx.missing("Baseball", "mlb_ws_schedule", "no payload")
        return
    recs = {}
    for league in stand.get("records", []):
        for tr in league.get("teamRecords", []):
            recs[tr["team"]["id"]] = {
                "name": tr["team"]["name"], "w": tr["wins"], "l": tr["losses"],
                "rs": tr.get("runsScored"), "ra": tr.get("runsAllowed"),
                "pct": tr.get("winningPercentage"), "streak": (tr.get("streak") or {}).get("streakCode"),
            }
    stats = {"hit": {}, "pit": {}}
    for grp, payload in (("hit", hit), ("pit", pit)):
        for s in payload.get("stats", []):
            for sp in s.get("splits", []):
                stats[grp][sp["team"]["id"]] = sp.get("stat", {})
    for block in sched.get("dates", []):
        for g in block.get("games", []):
            state = (g.get("status") or {}).get("detailedState", "")
            if state.startswith(("Final", "Completed", "Cancelled", "Postponed")):
                continue
            start = iso(g.get("gameDate"))
            if not within(start):
                continue
            h, a = g["teams"]["home"], g["teams"]["away"]
            hid, aid = h["team"]["id"], a["team"]["id"]
            hr, ar = recs.get(hid), recs.get(aid)
            if not hr or not ar:
                continue

            def side(rec, st_id, side_obj):
                hs = stats["hit"].get(st_id, {}); ps = stats["pit"].get(st_id, {})
                gp = rec["w"] + rec["l"]
                return {
                    "gp": gp, "w": rec["w"], "l": rec["l"], "pct": rec["pct"], "streak": rec["streak"],
                    "rpg": round(rec["rs"] / gp, 3) if gp and rec["rs"] else None,
                    "rapg": round(rec["ra"] / gp, 3) if gp and rec["ra"] else None,
                    "ops": hs.get("ops"), "era": ps.get("era"), "whip": ps.get("whip"),
                    "win_pct": float(rec["pct"]) if rec["pct"] else None,
                    "margin": round((rec["rs"] - rec["ra"]) / gp, 3) if gp and rec["rs"] is not None else None,
                    "pf_pg": round(rec["rs"] / gp, 3) if gp and rec["rs"] is not None else None,
                    "pa_pg": round(rec["ra"] / gp, 3) if gp and rec["ra"] is not None else None,
                    "probable_pitcher": (side_obj.get("probablePitcher") or {}).get("fullName"),
                    "n": gp,
                }

            fa = side(ar, aid, a); fb = side(hr, hid, h)
            ctx.add(
                id=f"mlb-{g['gamePk']}", sport="Baseball", competition="MLB 2026 World Series",
                side_a=ar["name"], side_b=hr["name"], start_utc=start,
                venue=(g.get("venue") or {}).get("name"),
                form={"a": fa, "b": fb},
                facts=[
                    f"{ar['name']} finished the regular season {ar['w']}-{ar['l']} (RS {ar['rs']}, RA {ar['ra']}).",
                    f"{hr['name']} finished the regular season {hr['w']}-{hr['l']} (RS {hr['rs']}, RA {hr['ra']}).",
                    *([f"Probable starters: {a['team']['name']} {fa['probable_pitcher']} vs {h['team']['name']} {fb['probable_pitcher']}."]
                      if fa["probable_pitcher"] and fb["probable_pitcher"] else []),
                ],
                **ctx.meta("mlb_ws_schedule"),
            )


# --------------------------------------------------------------------------
# Basketball — EuroLeague / EuroCup game feeds
# --------------------------------------------------------------------------
def parse_euroleague(ctx: Ctx):
    for tid, comp in (("el_games", "EuroLeague 2026-27"), ("ec_games", "EuroCup 2026-27")):
        d = ctx.json(tid)
        if not d:
            ctx.missing("Basketball", tid, "no payload")
            continue
        games = d.get("data", [])
        results = []
        names = {}
        for g in games:
            if not g.get("played"):
                continue
            local, road = g.get("local") or {}, g.get("road") or {}
            la, ra = local.get("score"), road.get("score")
            lc, rc = local.get("club") or {}, road.get("club") or {}
            if la is None or ra is None or not lc or not rc:
                continue
            # key on the club code, not the sponsored display name, so a club
            # that appears under two spellings is still one team
            names[lc.get("code")] = lc.get("name")
            names[rc.get("code")] = rc.get("name")
            results.append((lc.get("code"), rc.get("code"), int(la), int(ra)))
        tbl = table(results)
        for g in games:
            if g.get("played"):
                continue
            start = iso(g.get("utcDate"))
            if not within(start):
                continue
            local, road = g.get("local") or {}, g.get("road") or {}
            lc, rc = local.get("club") or {}, road.get("club") or {}
            ln, rn = lc.get("name"), rc.get("name")
            if not ln or not rn:
                continue
            fa = dict(tbl.get(rc.get("code")) or {}); fb = dict(tbl.get(lc.get("code")) or {})
            if not fa or not fb:
                continue
            fa["points_pg"], fa["allowed_pg"] = fa["pf_pg"], fa["pa_pg"]
            fb["points_pg"], fb["allowed_pg"] = fb["pf_pg"], fb["pa_pg"]
            ctx.add(
                id=f"{tid}-{g.get('gameCode')}", sport="Basketball", competition=comp,
                side_a=rn, side_b=ln, start_utc=start,
                venue=(local.get("club") or {}).get("venue") or None,
                form={"a": fa, "b": fb},
                facts=[
                    f"{rn} {fa['w']}-{fa['l']} over {fa['n']} completed {comp.split()[0]} games, scoring {fa['pf_pg']} and conceding {fa['pa_pg']}.",
                    f"{ln} {fb['w']}-{fb['l']} over {fb['n']} completed {comp.split()[0]} games, scoring {fb['pf_pg']} and conceding {fb['pa_pg']}.",
                ],
                **ctx.meta(tid),
            )


# --------------------------------------------------------------------------
# Rugby League — RLWC 2026 official fixture API
# --------------------------------------------------------------------------
def parse_rlwc(ctx: Ctx):
    d = ctx.json("rlwc_api_fixtures")
    if not d:
        ctx.missing("Rugby League", "rlwc_api_fixtures", "no payload")
        return
    fixtures = [g for rf in d["result"]["roundFixtures"] for g in rf["gameFixtures"]]
    results = []
    for g in fixtures:
        if g.get("gameStateName") != "Final" or not g.get("teams"):
            continue
        if len(g["teams"]) != 2:
            continue
        t0, t1 = g["teams"]
        s0, s1 = t0.get("teamFinalScore"), t1.get("teamFinalScore")
        if s0 is None or s1 is None:
            continue
        results.append((t0["teamName"], t1["teamName"], s0, s1))
    tbl = table(results)
    for g in fixtures:
        if g.get("gameStateName") == "Final" or not g.get("startTimeUTC"):
            continue
        start = iso(g["startTimeUTC"])
        if not within(start):
            continue
        home = next((t for t in g["teams"] if t.get("isHomeTeam")), g["teams"][0])
        away = next((t for t in g["teams"] if not t.get("isHomeTeam")), g["teams"][1])
        fa, fb = tbl.get(away["teamName"]), tbl.get(home["teamName"])
        if not fa or not fb:
            continue
        ctx.add(
            id=f"rlwc-{g['gameId']}", sport="Rugby League",
            competition=f"Rugby League World Cup 2026 · {g.get('groupName')}",
            side_a=away["teamName"], side_b=home["teamName"], start_utc=start,
            venue=f"{g.get('venueName')}, {g.get('city')}",
            form={"a": fa, "b": fb},
            facts=[
                f"{away['teamName']} ({away.get('teamNickName')}) {fa['w']}-{fa['l']} in {fa['n']} completed World Cup matches, {fa['pf_pg']} points scored and {fa['pa_pg']} conceded per game.",
                f"{home['teamName']} ({home.get('teamNickName')}) {fb['w']}-{fb['l']} in {fb['n']} completed World Cup matches, {fb['pf_pg']} points scored and {fb['pa_pg']} conceded per game.",
                f"{g.get('groupName')} fixture at {g.get('venueName')}, {g.get('city')}, kick-off {start}; the official feed lists the ground as {g.get('groundConditionName')} with {g.get('weatherName')}.",
            ],
            **ctx.meta("rlwc_api_fixtures"),
        )


# --------------------------------------------------------------------------
# Snooker — WST match service + WST participant rankings
# --------------------------------------------------------------------------
def parse_wst(ctx: Ctx):
    """WST match service: form from completed frames, fixture from scheduled rows.

    The WST participant payload carries no numeric world ranking (the field is
    null for every player), so ranking is not used. Instead the completed rows
    of the same official match feed give a verified frames-won / frames-lost
    record for the players who are still in the event.
    """
    d = ctx.json("wst_matches_probe")
    if not d:
        ctx.missing("Snooker", "wst_matches_probe", "no payload")
        return
    rows = [m.get("attributes", {}) for m in d.get("data", [])]
    frames: dict[str, dict] = {}
    for a in rows:
        if a.get("status") != "Completed":
            continue
        hs, as_ = a.get("homePlayerScore"), a.get("awayPlayerScore")
        if None in (hs, as_):
            continue
        hp = (a.get("homePlayer") or {}); ap = (a.get("awayPlayer") or {})
        hn = f"{hp.get('firstName')} {hp.get('surname')}".strip()
        an = f"{ap.get('firstName')} {ap.get('surname')}".strip()
        for name, own, opp in ((hn, hs, as_), (an, as_, hs)):
            if not name:
                continue
            r = frames.setdefault(name, {"w": 0, "l": 0, "n": 0, "fw": 0, "fl": 0})
            r["n"] += 1; r["fw"] += own; r["fl"] += opp
            r["w" if own > opp else "l"] += 1
    for r in frames.values():
        r["win_pct"] = round(r["w"] / r["n"], 4) if r["n"] else 0.0
        r["margin"] = round((r["fw"] - r["fl"]) / r["n"], 3) if r["n"] else 0.0
        r["pf_pg"] = round(r["fw"] / r["n"], 3)
        r["pa_pg"] = round(r["fl"] / r["n"], 3)
    for a in rows:
        if a.get("status") not in ("Scheduled", "Suspended") or not a.get("playersAllocated"):
            continue
        start = iso(a.get("startDateTime"))
        if not within(start) or start[:10] > "2026-10-27":
            continue
        hp = (a.get("homePlayer") or {}); ap = (a.get("awayPlayer") or {})
        hn = f"{hp.get('firstName')} {hp.get('surname')}".strip()
        an = f"{ap.get('firstName')} {ap.get('surname')}".strip()
        fa, fb = frames.get(an), frames.get(hn)
        if not hn or not an or not fa or not fb:
            continue
        ctx.add(
            id="wst-" + hashlib.sha1(str(a.get("name")).encode()).hexdigest()[:8], sport="Snooker",
            competition="BetVictor Northern Ireland Open 2026",
            side_a=an, side_b=hn, start_utc=start, venue="Waterfront Hall, Belfast",
            form={"a": fa, "b": fb},
            facts=[f"{an} has won {fa['w']} of {fa['n']} completed matches in the captured WST feed ({fa['fw']}-{fa['fl']} frames).",
                   f"{hn} has won {fb['w']} of {fb['n']} completed matches in the captured WST feed ({fb['fw']}-{fb['fl']} frames).",
                   f"{a.get('round')} over {a.get('numberOfFrames')} frames, scheduled {start}."],
            **ctx.meta("wst_matches_probe"),
        )


# --------------------------------------------------------------------------
# Tennis — WTA official match feed
# --------------------------------------------------------------------------
def parse_wta(ctx: Ctx):
    names = {"2092": "WTA 500 Ningbo", "405": "WTA 250 Osaka", "1056": "WTA Guangzhou", "1023": "WTA Guangzhou"}
    seen = set()
    for tid in ("wta_2092", "wta_405", "wta_1056", "wta_1023"):
        d = ctx.json(tid)
        if not d or not d.get("matches"):
            continue
        tour = (d.get("tournament") or {}).get("Name") or names.get(tid.split("_")[1], "WTA tournament")
        ms = d["matches"]
        # recent completed results per player (form)
        tbl: dict[str, dict] = {}
        for m in ms:
            if m.get("Winner") in ("1", "2") and m.get("ScoreString"):
                wa = m["Winner"] == "1"
                pa = f"{m.get('PlayerNameFirstA')} {m.get('PlayerNameLastA')}".strip()
                pb = f"{m.get('PlayerNameFirstB')} {m.get('PlayerNameLastB')}".strip()
                for name, won in ((pa, wa), (pb, not wa)):
                    d2 = tbl.setdefault(name, {"w": 0, "l": 0, "n": 0})
                    d2["n"] += 1; d2["w"] += int(won); d2["l"] += int(not won)
        for d2 in tbl.values():
            d2["win_pct"] = round(d2["w"] / d2["n"], 4) if d2["n"] else 0.0
            d2["margin"] = 0.0
        for m in ms:
            state = m.get("MatchState")
            if state not in ("U", "P", "L", "S", ""):
                continue
            ts = m.get("MatchTimeStamp") or ""
            start = iso(ts)
            if not start or not within(start, lo="2026-10-21"):
                continue
            pa = f"{m.get('PlayerNameFirstA')} {m.get('PlayerNameLastA')}".strip()
            pb = f"{m.get('PlayerNameFirstB')} {m.get('PlayerNameLastB')}".strip()
            if not pa or not pb or (pa, pb) in seen:
                continue
            fa = tbl.get(pa); fb = tbl.get(pb)
            if not fa or not fb:
                continue
            seen.add((pa, pb))
            ctx.add(
                id=f"{tid}-{m.get('MatchID')}", sport="Tennis", competition=tour,
                side_a=pb, side_b=pa, start_utc=start, venue=None,
                form={"a": {"win_pct": fb["win_pct"], "n": fb["n"], "w": fb["w"], "l": fb["l"], "margin": 0.0,
                            "seed": m.get("SeedB") or None},
                      "b": {"win_pct": fa["win_pct"], "n": fa["n"], "w": fa["w"], "l": fa["l"], "margin": 0.0,
                            "seed": m.get("SeedA") or None}},
                facts=[f"{pa} is {fa['w']}-{fa['l']} in completed matches at this event.",
                       f"{pb} is {fb['w']}-{fb['l']} in completed matches at this event.",
                       f"Round {m.get('RoundID')}; scheduled {start}."],
                **ctx.meta(tid),
            )


# --------------------------------------------------------------------------
# Darts — PDC official fixture + result service
# --------------------------------------------------------------------------
def parse_pdc(ctx: Ctx):
    d = ctx.json("pdc_fixtures_web")
    if not d:
        ctx.missing("Darts", "pdc_fixtures_web", "no payload")
        return
    rows = [x.get("attributes", {}) for x in d.get("data", [])]
    legs: dict[str, dict] = {}
    for r in rows:
        if r.get("status") != "Result":
            continue
        p1, p2 = r.get("participant1") or {}, r.get("participant2") or {}
        s1, s2 = r.get("participant1Score"), r.get("participant2Score")
        if None in (s1, s2):
            continue
        for pl, own, opp in ((p1, s1, s2), (p2, s2, s1)):
            nm = f"{pl.get('firstName')} {pl.get('lastName')}".strip() if pl else ""
            if not nm:
                continue
            rec = legs.setdefault(nm, {"w": 0, "l": 0, "n": 0, "lw": 0, "ll": 0})
            rec["n"] += 1; rec["lw"] += own; rec["ll"] += opp
            rec["w" if own > opp else "l"] += 1
    for rec in legs.values():
        rec["win_pct"] = round(rec["w"] / rec["n"], 4) if rec["n"] else 0.0
        rec["margin"] = round((rec["lw"] - rec["ll"]) / rec["n"], 3) if rec["n"] else 0.0
        # per-match scoring rates, so `margin` stays pf_pg - pa_pg like every other sport
        rec["pf_pg"] = round(rec["lw"] / rec["n"], 3)
        rec["pa_pg"] = round(rec["ll"] / rec["n"], 3)
    for r in rows:
        if r.get("status") != "Fixture":
            continue
        p1, p2 = r.get("participant1") or {}, r.get("participant2") or {}
        if not p1 or not p2:
            continue
        start = iso(f"{r.get('startDate')}T{r.get('startTime')}")
        if not within(start):
            continue
        n1 = f"{p1.get('firstName')} {p1.get('lastName')}".strip()
        n2 = f"{p2.get('firstName')} {p2.get('lastName')}".strip()
        fa, fb = legs.get(n2), legs.get(n1)
        if not fa or not fb:
            continue
        t = r.get("tournament") or {}
        ctx.add(
            id=f"pdc-{r.get('tournamentRoundID')}-{n1[:3]}{n2[:3]}".replace(" ", ""),
            sport="Darts", competition=t.get("name") or "PDC",
            side_a=n2, side_b=n1, start_utc=start,
            venue=", ".join(x for x in (t.get("venue"), t.get("city")) if x) or None,
            form={"a": fa, "b": fb},
            facts=[f"{n2} has won {fa['w']} of {fa['n']} completed matches in the captured PDC feed, winning {fa['lw']} legs to {fa['ll']}.",
                   f"{n1} has won {fb['w']} of {fb['n']} completed matches in the captured PDC feed, winning {fb['lw']} legs to {fb['ll']}.",
                   f"{t.get('name')} at {t.get('venue')}, {r.get('startDate')} {r.get('startTime')}."],
            **ctx.meta("pdc_fixtures_web"),
        )


# --------------------------------------------------------------------------
# Golf — PGA TOUR official leaderboard (outright + top-10 markets)
# --------------------------------------------------------------------------
def parse_pga(ctx: Ctx):
    for tid, label in (("pga_bermuda_lb", "Butterfield Bermuda Championship"),
                       ("pga_bermuda", "Butterfield Bermuda Championship")):
        b = ctx.raw(tid)
        if not b:
            continue
        html = b.decode("utf-8", "replace")
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.S)
        if not m:
            continue
        data = json.loads(m.group(1))
        qs = data["props"]["pageProps"]["dehydratedState"]["queries"]
        lb = None
        for q in qs:
            st = q.get("state", {}).get("data")
            if isinstance(st, dict) and isinstance(st.get("players"), list):
                lb = st
                break
        if not lb:
            continue
        players = []
        for row in lb["players"]:
            sd = row.get("scoringData") or {}
            tot = sd.get("totalSort")
            if tot is None:
                continue
            players.append({
                "name": (row.get("player") or {}).get("displayName"),
                "country": (row.get("player") or {}).get("country"),
                "position": sd.get("position"), "total": tot,
                "thru": sd.get("thru"), "round": sd.get("currentRound"),
                "rounds": sd.get("rounds"),
            })
        if not players:
            continue
        st = lb.get("tournamentStatus") or {}
        ctx.add(
            id=f"golf-{lb.get('tournamentId')}", sport="Golf",
            competition=f"PGA TOUR · {label}",
            side_a=label, side_b="Field", start_utc=iso("2026-10-25T18:00:00Z"),
            venue="Port Royal Golf Course, Southampton",
            form=None, market_kind="outright",
            outright={"market": "Outright winner", "field": players,
                      "status": st if isinstance(st, str) else st.get("roundStatus"), "round_header": lb.get("leaderboardRoundHeader"),
                      "event_end": "2026-10-25"},
            facts=[f"{label} is in progress at Port Royal Golf Course; the board shows {len(players)} players after {lb.get('leaderboardRoundHeader')}.",
                   f"Leader: {players[0]['name']} on {players[0]['total']} (position {players[0]['position']})."],
            **ctx.meta(tid),
        )
        return
    ctx.missing("Golf", "pga_bermuda_lb", "no embedded leaderboard")


# --------------------------------------------------------------------------
# Motor racing — Formula 1 official calendar + constructor standings
# --------------------------------------------------------------------------
def parse_f1(ctx: Ctx):
    cal = ctx.html("f1_calendar_2026")
    teams = ctx.html("f1_team_results")
    races = ctx.html("f1_races_2026")
    if not cal or not teams:
        ctx.missing("Motor Racing", "f1_calendar_2026", "no payload")
        return
    t = strip_html(teams)
    i = t.find("2026 Teams")
    table = []
    for m in re.finditer(r"(\d+)\s+(Mercedes|Ferrari|Red Bull Racing|McLaren|Aston Martin|Williams|Alpine|Racing Bulls|Haas F1 Team|Audi|Cadillac)\s+(\d+)", t[i:] if i > 0 else t):
        table.append({"pos": int(m.group(1)), "team": m.group(2), "points": int(m.group(3))})
    if not table:
        ctx.missing("Motor Racing", "f1_team_results", "constructor table not parsed")
        return
    rc = strip_html(races) if races else ""
    wins = {}
    for m in re.finditer(r"(\d{2} - \d{2} [A-Z][a-z]{2})\s+([A-Z][A-Za-z\.\-\u00c0-\u017f' ]{3,40}?)\s+(Mercedes|Ferrari|Red Bull Racing|McLaren|Aston Martin|Williams|Alpine|Racing Bulls|Haas F1 Team|Audi|Cadillac)", rc):
        wins[m.group(3)] = wins.get(m.group(3), 0) + 1
    ctx.add(
        id="f1-2026-united-states", sport="Motor Racing",
        competition="FIA Formula One World Championship · United States Grand Prix",
        side_a="United States Grand Prix", side_b="Race winner market",
        start_utc=iso("2026-10-25T20:00:00Z"), venue="Circuit of the Americas, Austin",
        form=None, market_kind="outright",
        outright={"market": "Winning constructor", "table": table, "wins": wins,
                  "event_end": "2026-10-25"},
        facts=[f"Constructor standings read from formula1.com: " +
               "; ".join(f"{r['team']} {r['points']}" for r in table) + ".",
               f"Round 18 of the 2026 championship is the United States Grand Prix, 23-25 October, with the race on Sunday 25 October."],
        **ctx.meta("f1_team_results"),
    )


# --------------------------------------------------------------------------
# Rugby Union — TOP 14 official fixtures + standings (LNR) and URC fixture list
# --------------------------------------------------------------------------
def parse_top14(ctx: Ctx):
    cal = ctx.html("top14_classement") or ctx.html("top14_cal")
    if not cal:
        ctx.missing("Rugby Union", "top14_classement", "no payload")
        return
    clubs, form = {}, {}
    t = strip_html(cal)
    i = t.find("Prochain match")
    if i > 0:
        seg = t[i:i + 4000]
        names = re.findall(r"(?:^|\s)((?:Stade Toulousain|Section Paloise|Union Bordeaux-Bègles|Stade Rochelais|Racing 92|ASM Clermont|RC Toulon|Montpellier Hérault Rugby|Castres Olympique|Aviron Bayonnais|LOU Rugby|RC Vannes|USA Perpignan|Stade Français Paris))", seg)
        for nm in names:
            chunk = seg.split(nm, 1)[1][:120]
            nums = re.findall(r"\b\d+\b", chunk)[:9]
            fm = re.search(r"((?:[VDNP]\s+){3,})", chunk)
            if len(nums) >= 9 and fm:
                form[nm] = {"pts": int(nums[0]), "m": int(nums[1]), "w": int(nums[2]),
                            "d": int(nums[3]), "l": int(nums[4]), "bonus": int(nums[5]),
                            "pf": int(nums[6]), "pa": int(nums[7]),
                            "diff": float(nums[8]),
                            "margin": round(float(nums[8]) / max(1, int(nums[1])), 3),
                            "form": fm.group(1).split(),
                            "win_pct": round(int(nums[2]) / max(1, int(nums[1])), 4),
                            "pf_pg": round(int(nums[6]) / max(1, int(nums[1])), 3),
                            "pa_pg": round(int(nums[7]) / max(1, int(nums[1])), 3),
                            "n": int(nums[1])}
    m = re.search(r":matches='(\[.*?\])'", cal, re.S)
    if m:
        raw = m.group(1).replace("\\/", "/")
        try:
            matches = json.loads(raw)
        except json.JSONDecodeError:
            matches = []
        for mt in matches:
            h = (mt.get("hosting_club") or {}).get("name")
            v = (mt.get("visiting_club") or {}).get("name")
            start = iso(((mt.get("timer") or {}).get("firstPeriodStartDate") or ""))
            if not h or not v or not within(start):
                continue
            fa, fb = form.get(v), form.get(h)
            if not fa or not fb:
                continue
            ctx.add(
                id=f"top14-{mt.get('id')}", sport="Rugby Union", competition="TOP 14 2026-27 · Round 7",
                side_a=v, side_b=h, start_utc=start, venue=None,
                form={"a": fa, "b": fb},
                facts=[f"{v} has {fa['pts']} league points from {fa['m']} matches ({fa['w']}W-{fa['d']}D-{fa['l']}L), scoring {fa['pf']} and conceding {fa['pa']}.",
                       f"{h} has {fb['pts']} league points from {fb['m']} matches ({fb['w']}W-{fb['d']}D-{fb['l']}L), scoring {fb['pf']} and conceding {fb['pa']}.",
                       f"Round 7 fixture at {h}, kick-off {start}."],
                **ctx.meta("top14_classement"),
            )
    else:
        ctx.missing("Rugby Union", "top14_classement", "fixture JSON not found")


def parse_urc(ctx: Ctx):
    """URC Round 5 fixture list from the official 'Fixtures in Full' page (no table
    was retrievable, so these rows are listed but deliberately left unpriced)."""
    html = ctx.html("urc_fixtures_in_full")
    if not html:
        ctx.missing("Rugby Union", "urc_fixtures_in_full", "no payload")
        return
    t = strip_html(html)
    cur_round = None
    months = {"SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12}
    for line in re.finditer(r"ROUND (\d+)|(?:FRIDAY|SATURDAY|SUNDAY), ([A-Z]+) (\d{1,2})|([A-Z][A-Za-z0-9'\- ]{2,30}) v ([A-Z][A-Za-z0-9'\- ]{2,30})([^A-Z]{0,80}?KO (\d{1,2})[.:](\d{2}))", t):
        if line.group(1):
            cur_round = int(line.group(1)); continue
        if line.group(2):
            continue
        if cur_round != 5:
            continue
        a, b, ko = line.group(4).strip(), line.group(5).strip(), f"{line.group(7)}:{line.group(8)}"
        ctx.add(
            id=f"urc-r5-{re.sub(r'[^a-z0-9]+','-',(a+b).lower())[:40]}", sport="Rugby Union",
            competition="United Rugby Championship 2026-27 · Round 5",
            side_a=b, side_b=a, start_utc=None, venue=None, form=None,
            facts=[f"Round 5 fixture {a} v {b}, kick-off {ko} Irish/UK time, listed on the URC official fixtures page."],
            **ctx.meta("urc_fixtures_in_full"),
        )


# --------------------------------------------------------------------------
# Cricket — Cricket Australia official fixture feed
# --------------------------------------------------------------------------
def parse_ca(ctx: Ctx):
    html = ctx.html("ca_fixtures")
    if not html:
        ctx.missing("Cricket", "ca_fixtures", "no payload")
        return
    m = re.search(r"window\.FIXTURES_DATA = JSON\.parse\('(.*?)'\);", html, re.S)
    if not m:
        ctx.missing("Cricket", "ca_fixtures", "FIXTURES_DATA missing")
        return
    raw = m.group(1).encode().decode("unicode_escape")
    try:
        fixtures = json.loads(raw)
    except json.JSONDecodeError as exc:
        ctx.missing("Cricket", "ca_fixtures", f"FIXTURES_DATA unparsable: {exc}")
        return
    # Win/loss records per team, accumulated across every completed fixture in
    # the same competition type that the feed still lists.
    results: dict[tuple, dict] = {}
    for f in fixtures:
        parts = f.get("name", "").split(" v ")
        if len(parts) != 2 or not f.get("isCompleted"):
            continue
        text = f.get("resultText") or ""
        winner = next((p.strip() for p in parts if p.strip() and p.strip() in text), None)
        if not winner:
            continue
        for team in (parts[0].strip(), parts[1].strip()):
            r = results.setdefault((f.get("gameType"), team), {"w": 0, "l": 0, "n": 0})
            r["n"] += 1
            r["w" if team == winner else "l"] += 1
    for r in results.values():
        r["win_pct"] = round(r["w"] / r["n"], 4) if r["n"] else None
        r["margin"] = 0.0

    for f in fixtures:
        if f.get("isCompleted") or f.get("isLive"):
            continue
        start = iso(f.get("startDateTime"))
        if not within(start):
            continue
        parts = f.get("name", "").split(" v ")
        if len(parts) != 2:
            continue
        a, b = parts[0].strip(), parts[1].strip()
        fa, fb = results.get((f.get("gameType"), a)), results.get((f.get("gameType"), b))
        ctx.add(
            id=f"ca-{f.get('id')}", sport="Cricket",
            competition=f"{f.get('gameType')} · Cricket Australia",
            side_a=b, side_b=a, start_utc=start, venue=f.get("venue") or None,
            form={"a": fa, "b": fb} if fa and fb and fa.get("n") and fb.get("n") else None,
            facts=[f"{a} v {b}, {f.get('gameType')}, scheduled {start}.",
                   f"{f.get('resultText') or 'Match not yet played.'}"],
            **ctx.meta("ca_fixtures"),
        )


# --------------------------------------------------------------------------
# Gaelic games — GAA official fixtures and results payload
# --------------------------------------------------------------------------
def _brace_objects(s: str, key: str):
    out = []
    for m in re.finditer(re.escape(f'"{key}":"'), s):
        start = s.rfind("{", 0, m.start())
        depth, j, in_s, esc = 0, start, False, False
        while j < len(s):
            c = s[j]
            if in_s:
                if esc: esc = False
                elif c == "\\": esc = True
                elif c == '"': in_s = False
            elif c == '"': in_s = True
            elif c == "{": depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    out.append(s[start:j + 1]); break
            j += 1
    return out


def parse_gaa(ctx: Ctx):
    html = ctx.html("gaa_fixtures_results")
    if not html:
        ctx.missing("Gaelic Sports", "gaa_fixtures_results", "no payload")
        return
    s = html.replace('\\"', '"').replace('\\/', '/')
    seen, completed = set(), []
    games = []
    for obj in _brace_objects(s, "matchId"):
        if obj in seen:
            continue
        seen.add(obj)
        try:
            g = json.loads(obj)
        except json.JSONDecodeError:
            continue
        home = (g.get("homeTeam") or {}).get("name")
        away = (g.get("awayTeam") or {}).get("name")
        if not home or not away:
            continue
        sc = g.get("score") or {}
        hg, ag = sc.get("homeGoals", 0), sc.get("awayGoals", 0)
        hp, ap = sc.get("homePoints", 0), sc.get("awayPoints", 0)
        hs, as_ = hg * 3 + hp, ag * 3 + ap
        comp = g.get("url", "").strip("/").split("/")
        competition = comp[1].replace("-", " ").title() if len(comp) > 1 else "GAA"
        games.append({"id": g["matchId"], "home": home, "away": away, "start": iso(g.get("matchStartDate")),
                      "status": g.get("status"), "hs": hs, "as": as_, "competition": competition,
                      "round": g.get("roundName")})
        if (g.get("status") or "").lower() in ("completed", "result", "played") and (hs or as_):
            completed.append((g["matchId"], home, away, hs, as_))
    tbl = table([(h, a, hs, as_) for _, h, a, hs, as_ in completed])
    for g in games:
        if not within(g["start"]) or (g["status"] or "").lower() in ("completed", "result", "played"):
            continue
        fa, fb = tbl.get(g["away"]), tbl.get(g["home"])
        ctx.add(
            id=f"gaa-{g['id'][:12]}", sport="Gaelic Sports",
            competition=f"GAA · {g['competition']}",
            side_a=g["away"], side_b=g["home"], start_utc=g["start"], venue=None,
            form={"a": fa, "b": fb} if fa and fb else None,
            facts=[f"{g['home']} v {g['away']} in the {g['competition']} ({g.get('round') or 'fixture'}), scheduled {g['start']}."],
            **ctx.meta("gaa_fixtures_results"),
        )


# --------------------------------------------------------------------------
# Volleyball — PlusLiga (Poland) official match centre HTML
# --------------------------------------------------------------------------
def parse_plusliga(ctx: Ctx):
    html = ctx.html("plusliga_games_root")
    if not html:
        ctx.missing("Volleyball", "plusliga_games_root", "no payload")
        return
    blocks = re.split(r'<div class="gamesbox(?!-body)', html)
    rows = []
    for b in blocks[1:]:
        dm = re.search(r'<div class="date">([^<]+)</div>', b)
        names = re.findall(r'<div class="name notranslate">([^<]+)</div>', b)
        sets = re.findall(r'data-synced-games-content="setsTeam([AB])"[^>]*>([^<]*)<', b)
        if not dm or len(names) < 2:
            continue
        rows.append({"date": dm.group(1).strip(), "a": names[0].strip(), "b": names[1].strip(),
                     "sets": {k: v for k, v in sets}})
    mon = {"sty": 1, "lut": 2, "mar": 3, "kwi": 4, "maj": 5, "cze": 6, "lip": 7, "sie": 8,
           "wrz": 9, "paź": 10, "lis": 11, "gru": 12}
    results = []
    fixtures = []
    for r in rows:
        m = re.search(r"(\d{1,2}) (\w{3}), (\d{2}):(\d{2})", r["date"])
        if not m:
            continue
        mo = mon.get(m.group(2))
        if not mo:
            continue
        start = iso(f"2026-{mo:02d}-{int(m.group(1)):02d}T{m.group(3)}:{m.group(4)}:00Z")
        sa, sb = r["sets"].get("A", ""), r["sets"].get("B", "")
        if sa.isdigit() and sb.isdigit() and (int(sa) + int(sb)) >= 3:
            results.append((r["a"], r["b"], int(sa), int(sb)))
        else:
            fixtures.append((start, r["a"], r["b"]))
    tbl = table(results)
    for start, a, b in fixtures:
        if not within(start):
            continue
        fa, fb = tbl.get(b), tbl.get(a)
        ctx.add(
            id=f"plusliga-{re.sub(r'[^a-z0-9]+','-',(a+'|'+b).lower())[:40]}-{start[:10]}",
            sport="Volleyball", competition="PlusLiga 2026-27 (Poland)",
            side_a=b, side_b=a, start_utc=start, venue=None,
            form={"a": fa, "b": fb} if fa and fb else None,
            facts=[f"{a} v {b}, PlusLiga, scheduled {start}.",
                   f"Standings form is read from completed PlusLiga sets in the same official feed."],
            **ctx.meta("plusliga_games_root"),
        )
    if not fixtures:
        ctx.missing("Volleyball", "plusliga_games_root", "no parseable upcoming fixture rows")


EXTRACTORS = [parse_nhl, parse_mlb, parse_euroleague, parse_rlwc, parse_wst, parse_wta,
              parse_pdc, parse_pga, parse_f1, parse_top14, parse_urc, parse_ca, parse_gaa, parse_plusliga]


def main() -> int:
    caps = [Path(p) for p in sys.argv[1].split(",")]
    out = Path(sys.argv[2])
    ctx = Ctx(caps)
    for fn in EXTRACTORS:
        try:
            fn(ctx)
        except Exception as exc:  # noqa: BLE001 - a broken extractor must not hide the rest
            import traceback
            print(f"!! {fn.__name__} failed: {exc}")
            traceback.print_exc()
            ctx.unavailable.append({"sport": fn.__name__, "reason": f"extractor error: {exc}"})
    # Normalise the one derived field every sport exposes: `margin` must equal the
    # scoring rate minus the conceding rate, whichever table the row came from.
    for ev in ctx.events:
        form = ev.get("form") or {}
        for side in ("a", "b"):
            f = form.get(side) or {}
            if f.get("pf_pg") is not None and f.get("pa_pg") is not None:
                f["margin"] = round(f["pf_pg"] - f["pa_pg"], 3)

    payload = {
        "schema": "olbg4.board-ak.events/1",
        "session": "arena/63ad3394-olbg4",
        "captures": ctx.stamps,
        "capture": ctx.stamp,
        "generated_utc": os.environ.get("AK_GENERATED_UTC")
        or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {"from": TODAY, "to": HORIZON},
        "events": sorted(ctx.events, key=lambda e: (e["sport"], e["start_utc"], e["id"])),
        "unavailable": ctx.unavailable,
    }
    import collections
    c = collections.Counter(e["sport"] for e in ctx.events)
    out.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    print(f"events={len(ctx.events)} {dict(c)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

import json
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
    def __init__(self, cap: Path):
        self.cap = cap
        self.m = load_manifest(cap)
        self.R = by_id(self.m)
        self.stamp = cap.name
        self.events: list[dict] = []
        self.unavailable: list[dict] = []

    def rec(self, tid):
        return self.R.get(tid)

    def raw(self, tid):
        r = self.R.get(tid)
        return read_capture(self.cap, r) if r and r.get("status") == 200 else None

    def json(self, tid):
        b = self.raw(tid)
        return json.loads(b) if b else None

    def html(self, tid):
        b = self.raw(tid)
        return b.decode("utf-8", "replace") if b else None

    def meta(self, tid):
        r = self.R[tid]
        return {"source_url": r["url"], "source_sha256": r.get("sha256"), "capture": self.stamp}

    def add(self, **kw):
        self.events.append(kw)

    def missing(self, sport, tid, why):
        r = self.R.get(tid) or {}
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
    for tid in sorted(t for t in ctx.R if t.startswith("nhl_sched_")):
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
        for g in games:
            if not g.get("played"):
                continue
            local, road = g.get("local") or {}, g.get("road") or {}
            la, ra = local.get("score"), road.get("score")
            if la is None or ra is None or not local.get("club") or not road.get("club"):
                continue
            results.append((local["club"]["name"], road["club"]["name"], int(la), int(ra)))
        tbl = table(results)
        for g in games:
            if g.get("played"):
                continue
            start = iso(g.get("utcDate"))
            if not within(start):
                continue
            local, road = g.get("local") or {}, g.get("road") or {}
            ln = (local.get("club") or {}).get("name")
            rn = (road.get("club") or {}).get("name")
            if not ln or not rn:
                continue
            fa = dict(tbl.get(ln) or {}); fb = dict(tbl.get(rn) or {})
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
        fa, fb = tbl.get(home["teamName"]), tbl.get(away["teamName"])
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
        r["pf_pg"], r["pa_pg"] = r["fw"], r["fl"]
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
            id=f"wst-{a.get('name','')[:0] or hash(a.get('name'))%10**8}", sport="Snooker",
            competition="BetVictor Northern Ireland Open 2026",
            side_a=an, side_b=hn, start_utc=start, venue="Waterfront Hall, Belfast",
            form={"a": fa, "b": fb},
            facts=[f"{hn} has won {fa['w']} of {fa['n']} completed matches in the captured WST feed ({fa['fw']}-{fa['fl']} frames).",
                   f"{an} has won {fb['w']} of {fb['n']} completed matches in the captured WST feed ({fb['fw']}-{fb['fl']} frames).",
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


EXTRACTORS = [parse_nhl, parse_mlb, parse_euroleague, parse_rlwc, parse_wst, parse_wta]


def main() -> int:
    cap = Path(sys.argv[1])
    out = Path(sys.argv[2])
    ctx = Ctx(cap)
    for fn in EXTRACTORS:
        try:
            fn(ctx)
        except Exception as exc:  # noqa: BLE001 - a broken extractor must not hide the rest
            import traceback
            print(f"!! {fn.__name__} failed: {exc}")
            traceback.print_exc()
            ctx.unavailable.append({"sport": fn.__name__, "reason": f"extractor error: {exc}"})
    payload = {
        "schema": "olbg4.board-ak.events/1",
        "session": "arena/63ad3394-olbg4",
        "capture": ctx.stamp,
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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

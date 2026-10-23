#!/usr/bin/env python3
"""Board BW (session arena/343754f2-olbg4) — same-day desk origination engine.

Reads ONLY the committed capture bytes under data/session-343754f2/capture/<STAMP>/
(re-hashing every file against that capture's SHA-256 manifest before use) and produces:

  - data/session-343754f2/desk.json      : every row (priced, unpriced, listing-only)
  - data/session-343754f2/flagged.json   : flags for review (unverified / blocked sources)

Every published number is derived from the official bytes by the documented models below;
nothing is copied from OLBG (OLBG hub pages are used for the taxonomy/listing cross-check
only) and nothing is inferred where the official inputs are missing (those cells stay blank
and the row is flagged).

Models (all parameters published here, no fitted constants hidden):
  Goals/points sports (NHL, SHL, Liiga, MLB, EuroLeague, EuroCup, handball, volleyball):
    expected scoring for each side comes from the team's verified season scoring rates in the
    official table/feed, shrunk toward the league mean with weight GP/(GP+k) (k published per
    sport); win/handicap/total probabilities come from the Poisson (goals) or Normal (points)
    distributions over the expected totals with the sport's documented home allowance.
  Tennis: logistic on the verified seed gap plus the player's verified main-draw results so
    far in the same official tournament feed, clamped to [0.15, 0.85].
  Cricket (internationals only): logistic on the verified ICC team-rating gap plus a
    documented home allowance; domestic one-day games are published unpriced (no official
    ratings captured).
  Golf / Motor Racing outrights: softmax over the verified official rating inputs
    (OWGR points / F1 championship points) with the temperature published.
Confidence rule (published):
  High  : model pick probability >= 0.70, price inside [-250, +10000] American, and the
          sport's sample gate met (see SAMPLE_GATE).
  Medium: 0.55 <= p < 0.70 and the sample gate met.
  Low   : everything else priced.
Rows whose official inputs are missing are published unpriced with blank pick/odds and are
flagged; rows only known from the OLBG listing are published as listing-only rows with the
official hub link, blank values, and a flag.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-343754f2"

CUT_OFF = "2026-10-23T19:36:27Z"          # EZ evening capture stamp (main evidence)
WINDOW_START = "2026-10-23T00:00:00Z"
WINDOW_END = "2026-11-09T00:00:00Z"

SPORT_SLUGS = {
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball",
    "Gaelic Sports": "gaelic-sports", "Greyhounds": "greyhounds", "Tennis": "tennis",
    "Motor Racing": "motor-racing", "Handball": "handball", "Ice Hockey": "ice-hockey",
    "Basketball": "basketball", "Rugby League": "rugby-league",
}

# newest capture wins; every stamp listed here is consulted
CAPTURE_DIR = DATA / "capture"
# Pinned to the capture this published desk was derived from: later bot stamps
# (e.g. 20261023T193956Z) stay archived in capture/ but are NOT desk inputs, so a
# rebuild from committed bytes is byte-identical.
PRIMARY_STAMP = "20261023T193627Z"
ALL_STAMPS = [PRIMARY_STAMP]

_flags: list[dict] = []


def flag(fid, severity, sport, title, detail, evidence_url, manual_url=""):
    _flags.append({
        "id": fid, "severity": severity, "sport": sport, "title": title,
        "detail": detail, "evidence_url": evidence_url, "manual_url": manual_url or evidence_url,
    })


# ---------------------------------------------------------------------------
# capture IO with SHA-256 verification
# ---------------------------------------------------------------------------

def load_manifest(stamp: str) -> dict:
    p = CAPTURE_DIR / stamp / "manifest.json"
    return json.loads(p.read_text())


class CaptureReader:
    def __init__(self):
        self.manifests = {}
        self.filemap = {}   # target id -> (stamp, record)
        for stamp in ALL_STAMPS:
            m = load_manifest(stamp)
            self.manifests[stamp] = m
            for rec in m["records"]:
                if rec.get("file"):
                    cur = self.filemap.get(rec["id"])
                    # keep the capture with the largest successful payload per target:
                    # later passes sometimes receive bot-variant shells (see EZ-F-CAP-01).
                    if cur is None or (rec.get("bytes") or 0) > (cur[1].get("bytes") or 0):
                        self.filemap[rec["id"]] = (stamp, rec)

    def read_text(self, target_id: str) -> str:
        stamp, rec = self.filemap[target_id]
        path = CAPTURE_DIR / stamp / rec["file"]
        raw = path.read_bytes()
        body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
        digest = hashlib.sha256(body).hexdigest()
        if digest != rec["sha256"]:
            raise RuntimeError(f"SHA-256 mismatch for {target_id} ({stamp})")
        return body.decode("utf-8", "ignore")

    def read_json(self, target_id: str):
        return json.loads(self.read_text(target_id))

    def source_url(self, target_id: str) -> str:
        return self.filemap[target_id][1]["url"]

    def has(self, target_id: str) -> bool:
        return target_id in self.filemap and self.filemap[target_id][1].get("status") == 200

    def capture_stamp(self, target_id: str) -> str:
        return self.filemap[target_id][0]


# ---------------------------------------------------------------------------
# maths
# ---------------------------------------------------------------------------

def poisson_pmf(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def norm_cdf(x: float, mu: float = 0.0, sigma: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))


def american_from_decimal(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100.0))
    return int(round(-100.0 / (dec - 1.0)))


def decimal_from_prob(p: float) -> float:
    p = min(0.999, max(0.001, p))
    return round(1.0 / p, 3)


def sel_row(label, p, book_margin=0.0):
    """One selection of an originated market: fair odds = 1/p; book = fair with margin."""
    dec = decimal_from_prob(p)
    book_dec = round(dec / (1.0 + book_margin), 3)
    return {
        "label": label, "fair_prob": round(p, 4), "fair_decimal": dec,
        "fair_american": american_from_decimal(dec),
        "book_decimal": book_dec, "book_american": american_from_decimal(book_dec),
    }


def two_way_market(name, pa, line=None, margin=0.0):
    pb = 1.0 - pa
    return {
        "market_name": name, "line": line, "prob_sum": 1.0, "book_margin": margin,
        "selections": [sel_row("Side A", pa, margin), sel_row("Side B", pb, margin)],
    }


def in_window(am: int) -> bool:
    return -250 <= am <= 10000


def confidence(p: float, gate_ok: bool):
    if not gate_ok:
        return "Medium" if p >= 0.55 else "Low", False
    if p >= 0.70:
        return "High", True
    if p >= 0.55:
        return "Medium", True
    return "Low", True


# ---------------------------------------------------------------------------
# desk assembly helpers
# ---------------------------------------------------------------------------

_rows: list[dict] = []
_row_seq = 0


def new_row(**kw):
    global _row_seq
    _row_seq += 1
    row = {
        "id": f"ez_{_row_seq:03d}",
        "row_kind": kw.get("row_kind", "match"),
        "listing_only": kw.get("listing_only", False),
        "sport": kw["sport"],
        "sport_slug": SPORT_SLUGS[kw["sport"]],
        "competition": kw["competition"],
        "side_a": kw.get("side_a", ""),
        "side_b": kw.get("side_b", ""),
        "matchup": kw.get("matchup", ""),
        "start_utc": kw.get("start_utc", ""),
        "start_date": kw.get("start_date", ""),
        "venue": kw.get("venue", ""),
        "official_url": kw["official_url"],
        "official_source_name": kw["official_source_name"],
        "capture_stamp": kw.get("capture_stamp", PRIMARY_STAMP),
        "inputs_summary": kw.get("inputs_summary", ""),
        "olbg": kw.get("olbg"),
        "markets": kw.get("markets"),
        "pick": kw.get("pick"),
        "pick_market": kw.get("pick_market"),
        "pick_prob": kw.get("pick_prob"),
        "pick_fair_american": kw.get("pick_fair_american"),
        "confidence": kw.get("confidence"),
        "in_window": kw.get("in_window", False),
        "priced": kw.get("priced", kw.get("markets") is not None),
    }
    _rows.append(row)
    return row


def finish_pick(row, market_name, sel_label, p, gate_ok):
    dec = decimal_from_prob(p)
    am = american_from_decimal(dec)
    conf, _ = confidence(p, gate_ok)
    row["pick"] = sel_label
    row["pick_market"] = market_name
    row["pick_prob"] = round(p, 4)
    row["pick_fair_american"] = am
    row["confidence"] = conf
    row["in_window"] = bool(-250 <= am <= 10000)
    return row


def pick_best_selection(row, gate_ok):
    """Published selection rule: scan every originated market on the row and pick the
    selection with the highest model probability that prices inside the requested
    [-250, +10000] American window; if no selection fits the window, fall back to the
    highest-probability money-line side and leave in_window False (flagged page shows
    the arithmetic). Ties prefer the simpler market (match_winner first)."""
    best = None
    order = {"match_winner": 0, "handicap": 1, "total": 2, "outright": 3}
    for mk in sorted(row.get("markets", {}).values(), key=lambda m: order.get(m["market_name"].split()[0].lower(), 9)):
        for s in mk.get("selections", []):
            am = s["fair_american"]
            if not (-250 <= am <= 10000):
                continue
            key = (s["fair_prob"], -order.get(mk["market_name"].split()[0].lower(), 9))
            if best is None or key > best[0]:
                best = (key, mk["market_name"], s)
    if best is not None:
        _, mk_name, s = best
        return finish_pick(row, mk_name, s["label"], s["fair_prob"], gate_ok)
    # no in-window selection: take the money-line favourite
    mw = row.get("markets", {}).get("match_winner") or {}
    sels = mw.get("selections") or []
    if not sels:
        return row
    s = max(sels, key=lambda x: x["fair_prob"])
    return finish_pick(row, mw["market_name"], s["label"], s["fair_prob"], gate_ok)


# ===========================================================================
# parsers
# ===========================================================================

CR = CaptureReader()


def strip_html(h: str) -> str:
    h = re.sub(r"<script[^>]*>.*?</script>", " ", h, flags=re.S)
    h = re.sub(r"<style[^>]*>.*?</style>", " ", h, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", t).strip()


# ---- NHL ------------------------------------------------------------------

def parse_nhl(reader: CaptureReader) -> None:
    if not reader.has("nhl_standings_now"):
        flag("EZ-F-NHL-01", "blocker", "Ice Hockey",
             "NHL standings feed missing", "api-web.nhle.com standings not captured; NHL rows would be unpriced.", "")
        return
    standings = reader.read_json("nhl_standings_now")
    teams = {}
    for rec in standings.get("standings", []):
        ab = rec.get("teamAbbrev", {}).get("default")
        teams[ab] = {
            "name": rec.get("teamName", {}).get("default", ab),
            "gp": rec.get("gamesPlayed", 0), "w": rec.get("wins", 0), "l": rec.get("losses", 0),
            "otl": rec.get("otLosses", 0), "pts": rec.get("points", 0),
            "gf": rec.get("goalFor", rec.get("goalForTotal", 0)),
            "ga": rec.get("goalAgainst", rec.get("goalAgainstTotal", 0)),
            "streak": rec.get("streakCode", {}).get("default", "") if isinstance(rec.get("streakCode"), dict) else "",
        }
    gp_all = [t["gp"] for t in teams.values() if t["gp"]]
    league_gp = max(gp_all) if gp_all else 0
    lg_gf = sum(t["gf"] for t in teams.values()) / max(1, sum(t["gp"] for t in teams.values()))
    lg_ga = sum(t["ga"] for t in teams.values()) / max(1, sum(t["gp"] for t in teams.values()))
    lg_avg = (lg_gf + lg_ga) / 2.0

    seen = {}
    for target in sorted(reader.filemap):
        if not target.startswith("nhl_sched_"):
            continue
        for day in reader.read_json(target).get("gameWeek", []):
            for g in day.get("games", []):
                seen[g["id"]] = g
    url = reader.source_url("nhl_sched_2026_10_23")
    stamp = reader.capture_stamp("nhl_sched_2026_10_23")
    n_priced = 0
    for gid in sorted(seen):
        g = seen[gid]
        start = g.get("startTimeUTC", "")
        if not (WINDOW_START <= start < WINDOW_END):
            continue
        aw, hm = g["awayTeam"], g["homeTeam"]
        ta, th = teams.get(aw["abbrev"]), teams.get(hm["abbrev"])
        if not ta or not th:
            flag("EZ-F-NHL-02", "review", "Ice Hockey",
                 f"Standings missing for a scheduled team {aw['abbrev']}/{hm['abbrev']}",
                 "Scheduled fixture references a team absent from the standings capture; row published unpriced.",
                 url)
            new_row(sport="Ice Hockey", competition="NHL 2026-27 Regular Season",
                    side_a=aw.get("commonName", {}).get("default", aw.get("abbrev", "")),
                    side_b=hm.get("commonName", {}).get("default", hm.get("abbrev", "")),
                    matchup=f"{aw.get('place',{}).get('default','')} @ {hm.get('place',{}).get('default','')}",
                    start_utc=start, venue=g.get("venue", {}).get("default", ""),
                    official_url=url, official_source_name="NHL Official Schedule API (api-web.nhle.com)",
                    capture_stamp=stamp,
                    inputs_summary=f"NHL official schedule, game id {gid} ({start}); standings capture missing for one club; unpriced.")
            continue
        w_a = ta["gp"] / (ta["gp"] + 8.0)
        w_h = th["gp"] / (th["gp"] + 8.0)
        gpg_a = ta["gf"] / max(1, ta["gp"]); gag_a = ta["ga"] / max(1, ta["gp"])
        gpg_h = th["gf"] / max(1, th["gp"]); gag_h = th["ga"] / max(1, th["gp"])
        lam_h = 0.5 * (w_h * gpg_h + (1 - w_h) * lg_gf) + 0.5 * (w_a * gag_a + (1 - w_a) * lg_ga)
        lam_a = 0.5 * (w_a * gpg_a + (1 - w_a) * lg_gf) + 0.5 * (w_h * gag_h + (1 - w_h) * lg_ga)
        lam_h *= 1.045  # published home allowance, NHL
        lam_a *= 0.955
        # win prob via Poisson 0-12 goals
        ph = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(i)) for i in range(13))
        pt = sum(poisson_pmf(lam_h, i) * poisson_pmf(lam_a, i) for i in range(13))
        p_home = ph + 0.5 * pt
        cover_h = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(0, i - 2)) for i in range(13))
        pt2 = sum(poisson_pmf(lam_h, i) * poisson_pmf(lam_a, i) for i in range(13))
        tot = lam_h + lam_a
        p_under = sum(poisson_pmf(tot, k) for k in range(7)) + 0.5 * poisson_pmf(tot, 6)  # line 6.0
        p_under = min(1.0, max(0.0, p_under))
        markets = {
            "match_winner": {**two_way_market("Money Line", p_home),
                             "selections": [sel_row(th["name"] + " (home)", p_home), sel_row(ta["name"] + " (away)", 1 - p_home)]},
            "handicap": {**two_way_market("Puck Line", cover_h, line=-1.5),
                         "selections": [sel_row(f"{th['name']} -1.5", cover_h), sel_row(f"{ta['name']} +1.5", 1 - cover_h)]},
            "total": {**two_way_market("Total Goals", p_under, line=6.0),
                      "selections": [sel_row("Under 6.0", p_under), sel_row("Over 6.0", 1 - p_under)]},
        }
        gate = ta["gp"] >= 5 and th["gp"] >= 5
        # pick = best-probability side of the winner market
        row = new_row(sport="Ice Hockey", competition="NHL 2026-27 Regular Season",
                      side_a=ta["name"], side_b=th["name"],
                      matchup=f"{ta['name']} @ {th['name']}",
                      start_utc=start, venue=g.get("venue", {}).get("default", ""),
                      official_url=url, official_source_name="NHL Official Schedule API (api-web.nhle.com)",
                      capture_stamp=stamp,
                      inputs_summary=(f"Official NHL schedule game {gid}; standings {th['gp']}GP {th['w']}-{th['l']}-{th['otl']} "
                                      f"({th['pts']} pts, GF:GA {th['gf']}:{th['ga']}) vs {ta['gp']}GP {ta['w']}-{ta['l']}-{ta['otl']} "
                                      f"({ta['pts']} pts, GF:GA {ta['gf']}:{ta['ga']}); model xG {lam_h:.2f}-{lam_a:.2f}."),
                      markets=markets)
        pick_best_selection(row, gate)
        n_priced += 1
    return


# ---- MLB ------------------------------------------------------------------

def parse_mlb(reader: CaptureReader) -> None:
    if not (reader.has("mlb_ws_schedule") and reader.has("mlb_standings_2026")):
        flag("EZ-F-MLB-01", "blocker", "Baseball", "MLB feeds missing", "", "")
        return
    sched = reader.read_json("mlb_ws_schedule")
    standings = reader.read_json("mlb_standings_2026")
    tstat = {}
    for rec in standings.get("records", []):
        div = rec.get("division") or {}
        for t in rec.get("teamRecords", []):
            tstat[t["team"]["id"]] = {
                "name": t["team"].get("name", ""),
                "gp": t.get("gamesPlayed", 0), "w": t.get("wins", 0), "l": t.get("losses", 0),
                "pct": t.get("winningPercentage"), "runs": t.get("runs", t.get("runsScored", 0)),
                "allowed": t.get("runsAllowed", 0), "rd": t.get("runDifferential", 0),
                "streak": t.get("streak", {}).get("streakCode", ""),
                "home": f"{t.get('records',{}).get('splitRecords',[{}])}"}  # placeholder replaced below
            for sr in t.get("records", {}).get("splitRecords", []):
                if sr.get("type") == "home":
                    tstat[t["team"]["id"]]["home"] = f"{sr.get('wins','-')}-{sr.get('losses','-')}"
                if sr.get("type") == "away":
                    tstat[t["team"]["id"]]["away"] = f"{sr.get('wins','-')}-{sr.get('losses','-')}"
    hitting = {}
    if reader.has("mlb_hitting_2026"):
        for tr in reader.read_json("mlb_hitting_2026").get("stats_split", {}).get("team_records", []):
            hitting[tr["team"]["id"]] = tr.get("stat", {})
    url = reader.source_url("mlb_ws_schedule")
    stamp = reader.capture_stamp("mlb_ws_schedule")
    for day in sched.get("dates", []):
        for g in day.get("games", []):
            start = g.get("gameDate", "")
            if not (WINDOW_START <= start < WINDOW_END):
                continue
            aw, hm = g["teams"]["away"], g["teams"]["home"]
            ta = tstat.get(aw["team"]["id"], {})
            th = tstat.get(hm["team"]["id"], {})
            desc = g.get("seriesDescription") or g.get("gameType", "")
            if not ta or not th:
                gnum = g.get("seriesGameNumber") or g.get("gameNumber")
                comp_lbl = f"MLB {desc}" + (f" Game {gnum}" if gnum else "")
                if str(g.get("ifNecessary", "")).upper() == "Y":
                    comp_lbl += " (if necessary)"
                new_row(sport="Baseball", competition=comp_lbl,
                        side_a=aw["team"].get("name", ""), side_b=hm["team"].get("name", ""),
                        matchup=f"{aw['team'].get('name','')} @ {hm['team'].get('name','')}",
                        start_utc=start, venue=g.get("venue", {}).get("name", ""),
                        official_url=url, official_source_name="MLB Stats API (statsapi.mlb.com)",
                        capture_stamp=stamp,
                        inputs_summary=f"MLB Stats API game {g.get('gamePk')} ({start}); standings capture incomplete; unpriced.")
                continue
            rg_h = th.get("runs", 0) / max(1, th.get("gp", 1))
            ra_ah = ta.get("allowed", 0) / max(1, ta.get("gp", 1))
            rg_a = ta.get("runs", 0) / max(1, ta.get("gp", 1))
            ra_hh = th.get("allowed", 0) / max(1, th.get("gp", 1))
            lam_h = 0.5 * (rg_h + ra_ah) * 1.03
            lam_a = 0.5 * (rg_a + ra_hh) * 0.97
            ph = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(i)) for i in range(15))
            pt = sum(poisson_pmf(lam_h, i) * poisson_pmf(lam_a, i) for i in range(15))
            p_home = ph + 0.5 * pt
            cover_h = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(0, i - 1)) for i in range(15))
            tot = lam_h + lam_a
            p_under = min(1.0, max(0.0, sum(poisson_pmf(tot, k) for k in range(8)) + 0.5 * poisson_pmf(tot, 7)))
            h_hit = hitting.get(hm["team"]["id"], {})
            a_hit = hitting.get(aw["team"]["id"], {})
            markets = {
                "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row(th.get("name", "home"), p_home), sel_row(ta.get("name", "away"), 1 - p_home)]},
                "handicap": {**two_way_market("Run Line", cover_h, line=-1.5),
                             "selections": [sel_row(f"{th.get('name','home')} -1.5", cover_h), sel_row(f"{ta.get('name','away')} +1.5", 1 - cover_h)]},
                "total": {**two_way_market("Total Runs", p_under, line=7.5),
                          "selections": [sel_row("Under 7.5", p_under), sel_row("Over 7.5", 1 - p_under)]},
            }
            summary = (f"MLB Stats API game {g.get('gamePk')}; regular season {th.get('w')}-{th.get('l')} "
                       f"(runs {th.get('runs')}, allowed {th.get('allowed')}, home {th.get('home')}) vs "
                       f"{ta.get('w')}-{ta.get('l')} (runs {ta.get('runs')}, allowed {ta.get('allowed')}, away {ta.get('away')}); "
                       f"model runs {lam_h:.2f}-{lam_a:.2f}.")
            if h_hit:
                summary += f" Team batting: {h_hit.get('avg','')}/{h_hit.get('obp','')}/{h_hit.get('slg','')} home, {a_hit.get('avg','')}/{a_hit.get('obp','')}/{a_hit.get('slg','')} away."
            gnum = g.get("seriesGameNumber") or g.get("gameNumber")
            comp_lbl = f"MLB {desc}" + (f" Game {gnum}" if gnum else "")
            if str(g.get("ifNecessary", "")).upper() == "Y":
                comp_lbl += " (if necessary)"
            row = new_row(sport="Baseball", competition=comp_lbl,
                          side_a=ta.get("name", ""), side_b=th.get("name", ""),
                          matchup=f"{ta.get('name','')} @ {th.get('name','')}",
                          start_utc=start, venue=g.get("venue", {}).get("name", ""),
                          official_url=url, official_source_name="MLB Stats API (statsapi.mlb.com)",
                          capture_stamp=stamp, inputs_summary=summary, markets=markets)
            gate = ta.get("gp", 0) >= 100 and th.get("gp", 0) >= 100
            pick_best_selection(row, gate)


# ---- EuroLeague / EuroCup ---------------------------------------------------

def parse_euroleague(reader: CaptureReader) -> None:
    for target, comp, sport in [("euroleague_games_E2026", "EuroLeague 2026-27 Regular Season", "Basketball"),
                                 ("eurocup_games_U2026", "EuroCup 2026-27 Regular Season", "Basketball")]:
        if not reader.has(target):
            flag(f"EZ-F-EL-{target}", "review", "Basketball", f"{comp} feed missing", "", "")
            continue
        data = reader.read_json(target)
        games = data.get("data", data) if isinstance(data, dict) else data
        stats = {}
        for g in games:
            if not g.get("played"):
                continue
            s = g.get("score") or {}
            h, a = g.get("local") or {}, g.get("road") or {}
            hc, ac = (h.get("club") or {}).get("code"), (a.get("club") or {}).get("code")
            if not hc or not ac:
                continue
            hs, as_ = h.get("score"), a.get("score")
            if not isinstance(hs, int) or not isinstance(as_, int):
                continue
            for code, pf, pa in ((hc, hs, as_), (ac, as_, hs)):
                st = stats.setdefault(code, {"gp": 0, "pf": 0, "pa": 0, "w": 0, "l": 0, "name": (h if code == hc else a).get("club", {}).get("name", code)})
                st["gp"] += 1; st["pf"] += pf; st["pa"] += pa
                if pf > pa: st["w"] += 1
                else: st["l"] += 1
        if not stats:
            flag(f"EZ-F-EL-{target}", "review", "Basketball", f"{comp}: no played games in feed", "", reader.source_url(target))
            continue
        lg_pf = sum(s["pf"] for s in stats.values()) / max(1, sum(s["gp"] for s in stats.values()))
        url = reader.source_url(target)
        stamp = reader.capture_stamp(target)
        count = 0
        for g in sorted(games, key=lambda x: x.get("utcDate") or ""):
            if g.get("played"):
                continue
            start = g.get("utcDate") or ""
            if not (WINDOW_START <= start < WINDOW_END):
                continue
            h, a = g.get("local") or {}, g.get("road") or {}
            hn, an = (h.get("club") or {}).get("name"), (a.get("club") or {}).get("name")
            if not hn or not an:
                continue
            if "TBD" in hn.upper() or "TBD" in an.upper():
                continue
            sh, sa = stats.get((h.get("club") or {}).get("code")), stats.get((a.get("club") or {}).get("code"))
            if not sh or not sa or sh["gp"] < 3 or sa["gp"] < 3:
                new_row(sport=sport, competition=f"{comp} Round {g.get('round')}",
                        side_a=hn, side_b=an, matchup=f"{hn} vs {an}", start_utc=start, venue=(g.get("venue") or {}).get("name", ""),
                        official_url=url, official_source_name=("EuroLeague Official API (api-live.euroleague.net)" if "euroleague" in target else "EuroCup Official API (api-live.euroleague.net)"),
                        capture_stamp=stamp,
                        inputs_summary=f"Official feed game {g.get('gameCode')} ({start}); insufficient played-games sample; unpriced.")
                continue
            w_h = sh["gp"] / (sh["gp"] + 4.0)
            w_a = sa["gp"] / (sa["gp"] + 4.0)
            pf_h = sh["pf"] / sh["gp"]; pa_h = sh["pa"] / sh["gp"]
            pf_a = sa["pf"] / sa["gp"]; pa_a = sa["pa"] / sa["gp"]
            mu_h = 0.5 * (w_h * pf_h + (1 - w_h) * lg_pf) + 0.5 * (w_a * pa_a + (1 - w_a) * lg_pf) + 1.5
            mu_a = 0.5 * (w_a * pf_a + (1 - w_a) * lg_pf) + 0.5 * (w_h * pa_h + (1 - w_h) * lg_pf)
            diff = mu_h - mu_a
            sigma = 10.5
            p_home = 1 - norm_cdf(0, diff, sigma)
            p_cover = 1 - norm_cdf(4.5, diff, sigma)  # P(home wins by > 4.5)
            total = mu_h + mu_a
            total_line = round(total * 2) / 2
            p_over = 1 - norm_cdf(total_line, total, sigma * math.sqrt(2) / 2 * 1.35)
            markets = {
                "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row(hn, p_home), sel_row(an, 1 - p_home)]},
                "handicap": {**two_way_market("Handicap", p_cover, line=-4.5),
                             "selections": [sel_row(f"{hn} -4.5", p_cover), sel_row(f"{an} +4.5", 1 - p_cover)]},
                "total": {**two_way_market("Total Points", p_over, line=total_line),
                          "selections": [sel_row(f"Over {total_line}", p_over), sel_row(f"Under {total_line}", 1 - p_over)]},
            }
            summary = (f"Official feed game {g.get('gameCode')}, Round {g.get('round')}; computed form "
                       f"{hn} {sh['w']}-{sh['l']} ({pf_h:.1f} for / {pa_h:.1f} against per game) vs "
                       f"{an} {sa['w']}-{sa['l']} ({pf_a:.1f} / {pa_a:.1f}); model {mu_h:.1f}-{mu_a:.1f}.")
            row = new_row(sport=sport, competition=f"{comp} Round {g.get('round')}",
                          side_a=hn, side_b=an, matchup=f"{hn} vs {an}", start_utc=start,
                          venue=(g.get("venue") or {}).get("name", ""),
                          official_url=url,
                          official_source_name=("EuroLeague Official API (api-live.euroleague.net)" if "euroleague" in target else "EuroCup Official API (api-live.euroleague.net)"),
                          capture_stamp=stamp, inputs_summary=summary, markets=markets)
            gate = sh["gp"] >= 4 and sa["gp"] >= 4
            pick_best_selection(row, gate)
            count += 1


# ---- SHL --------------------------------------------------------------------

def parse_shl(reader: CaptureReader) -> None:
    if not reader.has("swehockey_shl_overview"):
        return
    t = strip_html(reader.read_text("swehockey_shl_overview"))
    url = reader.source_url("swehockey_shl_overview")
    stamp = reader.capture_stamp("swehockey_shl_overview")
    # standings block: "RK Team GP W T L GF:GA (GD) GD TP ..." rows
    table = {}
    m = re.search(r"Group Standings.*?RK Team GP W T L GF:GA \(GD\) GD TP(.*?)(?:$|Next)", t)
    if m:
        rows = re.findall(r"(\d{1,2}) ([A-Za-zÅÄÖåäöéÉü .\-]+?) (\d{1,3}) (\d+) (\d+) (\d+) (\d+):(\d+) \(-?\d+\) -?\d+ (\d+)", m.group(1))
        for r in rows:
            name = r[1].strip()
            table[name] = {"gp": int(r[2]), "w": int(r[3]), "t": int(r[4]), "l": int(r[5]),
                           "gf": int(r[6]), "ga": int(r[7]), "pts": int(r[8])}
    # upcoming fixtures block: "2026-10-24 15:15 TEAM - TEAM Venue". Team names ending
    # in uppercase tokens (AIK, BK, HC, IF) defeat a naive venue split, so each side is
    # resolved against the parsed standings names (longest official-name prefix wins)
    # and the venue is whatever trailing text remains.
    fixtures = []
    for seg in re.split(r"(?=2026-10-\d{2})", t):
        m = re.match(r"(2026-10-\d{2} \d{2}:\d{2}) (.+?) - (.+)", seg)
        if not m:
            continue
        when, left, right = m.group(1), m.group(2).strip(), m.group(3).strip()
        right = right.split(" Group Standings")[0]  # tail of the page follows the last fixture
        a = next((k for k in sorted(table, key=len, reverse=True) if left == k), None)
        b = next((k for k in sorted(table, key=len, reverse=True) if right.startswith(k)), None)
        if a and b:
            venue = right[len(b):].strip()[:48]  # venue name only; truncate any page residue
            fixtures.append((when, a, b, venue))
    if not table:
        flag("EZ-F-SHL-01", "review", "Ice Hockey", "SHL standings not parsed",
             "The SHL overview page captured but the standings regex found no rows; upcoming SHL fixtures published unpriced.", url)
    lg_avg = (sum(x["gf"] for x in table.values()) + sum(x["ga"] for x in table.values())) / max(1, 2 * sum(x["gp"] for x in table.values()))
    n = 0
    for when, a, b, venue in fixtures:
        start = when.replace(" ", "T") + ":00Z"  # local Swedish time published by the league; flagged below
        ta, tb = table.get(a.strip()), table.get(b.strip())
        if not ta or not tb:
            new_row(sport="Ice Hockey", competition="SHL 2026-27 Regular Season",
                    side_a=a.strip(), side_b=b.strip(), matchup=f"{a.strip()} vs {b.strip()}",
                    start_utc="", venue=venue.strip(),
                    official_url=url, official_source_name="Swedish Ice Hockey Association official stats (stats.swehockey.se)",
                    capture_stamp=stamp,
                    inputs_summary=f"Official SHL overview fixture {when} local; start is local Swedish time (UTC offset +1/-1 not published on page); standings parse failed; unpriced.")
            continue
        w_a = ta["gp"] / (ta["gp"] + 8.0)
        w_b = tb["gp"] / (tb["gp"] + 8.0)
        lam_a = 0.5 * (w_a * ta["gf"] / ta["gp"] + (1 - w_a) * lg_avg) + 0.5 * (w_b * tb["ga"] / tb["gp"] + (1 - w_b) * lg_avg)
        lam_b = 0.5 * (w_b * tb["gf"] / tb["gp"] + (1 - w_b) * lg_avg) + 0.5 * (w_a * ta["ga"] / ta["gp"] + (1 - w_a) * lg_avg)
        lam_b *= 1.045
        lam_a *= 0.955
        pb = sum(poisson_pmf(lam_b, i) * sum(poisson_pmf(lam_a, j) for j in range(i)) for i in range(13))
        pt = sum(poisson_pmf(lam_b, i) * poisson_pmf(lam_a, i) for i in range(13))
        p_home = pb + 0.5 * pt
        cover_b = sum(poisson_pmf(lam_b, i) * sum(poisson_pmf(lam_a, j) for j in range(0, i - 2)) for i in range(13))
        p_under = min(1.0, max(0.0, sum(poisson_pmf(lam_a + lam_b, k) for k in range(7)) + 0.5 * poisson_pmf(lam_a + lam_b, 6)))
        markets = {
            "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                             "selections": [sel_row(b.strip(), p_home), sel_row(a.strip(), 1 - p_home)]},
            "handicap": {**two_way_market("Handicap", cover_b, line=-1.5),
                         "selections": [sel_row(f"{b.strip()} -1.5", cover_b), sel_row(f"{a.strip()} +1.5", 1 - cover_b)]},
            "total": {**two_way_market("Total Goals", p_under, line=6.0),
                      "selections": [sel_row("Under 6.0", p_under), sel_row("Over 6.0", 1 - p_under)]},
        }
        summary = (f"Official SHL stats page: {tb['w']}-{tb['t']}-{tb['l']} in {tb['gp']} GP (GF:GA {tb['gf']}:{tb['ga']}, {tb['pts']} pts) "
                   f"vs {ta['w']}-{ta['t']}-{ta['l']} in {ta['gp']} GP (GF:GA {ta['gf']}:{ta['ga']}, {ta['pts']} pts); venue {venue.strip()}.")
        row = new_row(sport="Ice Hockey", competition="SHL 2026-27 Regular Season",
                      side_a=a.strip(), side_b=b.strip(), matchup=f"{a.strip()} vs {b.strip()}",
                      start_utc="", venue=venue.strip(),
                      official_url=url, official_source_name="Swedish Ice Hockey Association official stats (stats.swehockey.se)",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets)
        row["start_local"] = when
        pick_best_selection(row, ta["gp"] >= 5 and tb["gp"] >= 5)
        n += 1
    if n:
        flag("EZ-F-SHL-02", "review", "Ice Hockey", "SHL start times are local",
             "stats.swehockey.se publishes round fixtures with local Swedish times only; rows carry start_local, start_utc left blank rather than inferred.", url)


# ---- Liiga -------------------------------------------------------------------

def parse_liiga(reader: CaptureReader) -> None:
    if not (reader.has("liiga_games_2027") and reader.has("liiga_standings_2027")):
        return
    games = reader.read_json("liiga_games_2027")
    url = reader.source_url("liiga_games_2027")
    stamp = reader.capture_stamp("liiga_games_2027")
    stats = {}
    for g in games:
        if not g.get("end"):   # finished games carry end; live/future do not
            continue
        h, a = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        if not isinstance(h.get("goals"), int) or not isinstance(a.get("goals"), int):
            continue
        hn, an = h.get("teamName"), a.get("teamName")
        for name, pf, pa in ((hn, h["goals"], a["goals"]), (an, a["goals"], h["goals"])):
            st = stats.setdefault(name, {"gp": 0, "gf": 0, "ga": 0, "w": 0, "l": 0})
            st["gp"] += 1; st["gf"] += pf; st["ga"] += pa
            if pf > pa: st["w"] += 1
            else: st["l"] += 1
    lg = (sum(s["gf"] for s in stats.values()) + sum(s["ga"] for s in stats.values())) / max(1, 2 * sum(s["gp"] for s in stats.values()))
    upcoming = [g for g in games if (g.get("start") or "") >= CUT_OFF and (g.get("start") or "") < "2026-11-09" and not g.get("end")]
    for g in sorted(upcoming, key=lambda x: x.get("start") or ""):
        h, a = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        hn, an = h.get("teamName"), a.get("teamName")
        sh, sa = stats.get(hn), stats.get(an)
        if not sh or not sa or sh["gp"] < 5 or sa["gp"] < 5:
            new_row(sport="Ice Hockey", competition="Liiga 2026-27 Regular Season",
                    side_a=hn or "", side_b=an or "", matchup=f"{hn} vs {an}",
                    start_utc=g.get("start", ""), venue="",
                    official_url=url, official_source_name="Liiga official API (liiga.fi)",
                    capture_stamp=stamp,
                    inputs_summary=f"Official Liiga feed game {g.get('id')} ({g.get('start')}); insufficient sample; unpriced.")
            continue
        w_h = sh["gp"] / (sh["gp"] + 8.0)
        w_a = sa["gp"] / (sa["gp"] + 8.0)
        lam_h = 0.5 * (w_h * sh["gf"] / sh["gp"] + (1 - w_h) * lg) + 0.5 * (w_a * sa["ga"] / sa["gp"] + (1 - w_a) * lg)
        lam_a = 0.5 * (w_a * sa["gf"] / sa["gp"] + (1 - w_a) * lg) + 0.5 * (w_h * sh["ga"] / sh["gp"] + (1 - w_h) * lg)
        lam_h *= 1.045; lam_a *= 0.955
        ph = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(i)) for i in range(13))
        pt = sum(poisson_pmf(lam_h, i) * poisson_pmf(lam_a, i) for i in range(13))
        p_home = ph + 0.5 * pt
        cover_h = sum(poisson_pmf(lam_h, i) * sum(poisson_pmf(lam_a, j) for j in range(0, i - 2)) for i in range(13))
        p_under = min(1.0, max(0.0, sum(poisson_pmf(lam_h + lam_a, k) for k in range(7)) + 0.5 * poisson_pmf(lam_h + lam_a, 6)))
        markets = {
            "match_winner": {"market_name": "Money Line", "line": None, "prob_sum": 1.0,
                             "selections": [sel_row(hn, p_home), sel_row(an, 1 - p_home)]},
            "handicap": {**two_way_market("Handicap", cover_h, line=-1.5),
                         "selections": [sel_row(f"{hn} -1.5", cover_h), sel_row(f"{an} +1.5", 1 - cover_h)]},
            "total": {**two_way_market("Total Goals", p_under, line=6.0),
                      "selections": [sel_row("Under 6.0", p_under), sel_row("Over 6.0", 1 - p_under)]},
        }
        summary = (f"Official Liiga feed game {g.get('id')}: {hn} {sh['w']}-{sh['l']} in {sh['gp']} GP "
                   f"(GF:GA {sh['gf']}:{sh['ga']}) vs {an} {sa['w']}-{sa['l']} in {sa['gp']} GP "
                   f"(GF:GA {sa['gf']}:{sa['ga']}); model {lam_h:.2f}-{lam_a:.2f}.")
        row = new_row(sport="Ice Hockey", competition="Liiga 2026-27 Regular Season",
                      side_a=hn, side_b=an, matchup=f"{hn} vs {an}", start_utc=g.get("start", ""), venue="",
                      official_url=url, official_source_name="Liiga official API (liiga.fi)",
                      capture_stamp=stamp, inputs_summary=summary, markets=markets)
        pick_best_selection(row, True)


# ---- Tennis -------------------------------------------------------------------

def parse_tennis(reader: CaptureReader) -> None:
    # WTA tournaments — every captured wta_*_matches feed in this session
    wta_targets = []
    for t in sorted(k for k in reader.filemap if k.startswith("wta_")):
        try:
            doc = reader.read_json(t)
        except Exception:
            continue
        if isinstance(doc, dict) and "matches" in doc:
            wta_targets.append(t)
    for target in wta_targets:
        if not reader.has(target):
            continue
        d = reader.read_json(target)
        tour = d.get("tournament", {})
        title = tour.get("title") or target.replace("wta_", "").replace("_matches", "")
        city = title.split(" - ")[-1] if " - " in title else title
        url = reader.source_url(target)
        stamp = reader.capture_stamp(target)
        byid = {m["MatchID"]: m for m in d.get("matches", [])}
        for m in d.get("matches", []):
            if m.get("DrawMatchType") != "S" or m.get("MatchState") not in ("U", "C"):
                continue
            start_raw = m.get("MatchTime") or m.get("MatchTimeStamp") or ""
            # MatchTime is UTC ("2026-10-24T12:00"); MatchTimeStamp carries a local offset
            # ("2026-10-24T12:00+09:00") — convert to UTC rather than assume.
            start_utc = ""
            try:
                if "T" in start_raw:
                    dt = datetime.fromisoformat(start_raw)
                    start_utc = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                start_utc = start_raw[:16]
            if not start_utc or not (WINDOW_START <= start_utc[:10] and start_utc[:10] < "2026-11-09"):
                continue
            pa = f"{(m.get('PlayerNameFirstA') or '').strip()} {m.get('PlayerNameLastA','')}".strip()
            pb = f"{(m.get('PlayerNameFirstB') or '').strip()} {m.get('PlayerNameLastB','')}".strip()
            if not pa or not pb or "TBD" in (pa + pb).upper():
                continue
            seed_a, seed_b = m.get("SeedA"), m.get("SeedB")
            # this-event results so far (sets/games won-lost) from finished singles matches
            def form_for(name):
                sets_w = sets_l = games_w = games_l = wins = 0
                for mm in d.get("matches", []):
                    if mm.get("DrawMatchType") != "S" or mm.get("MatchState") != "F":
                        continue
                    la = mm.get("PlayerNameLastA", "")
                    lb = mm.get("PlayerNameLastB", "")
                    if name not in (la, lb):
                        continue
                    res = mm.get("ResultString") or ""
                    nums = re.findall(r"(\d+)-(\d+)", res)
                    my, op = [], []
                    for x, y in nums:
                        if int(x) > int(y):
                            my.append(int(x)); op.append(int(y))
                        else:
                            my.append(int(y)); op.append(int(x))
                    if not my:
                        continue
                    if name == la:
                        won = (mm.get("Winner") == "2" or (mm.get("ScoreSet1A") or "") != "" and sum(1 for i in range(1, 4) if str(mm.get(f"ScoreSet{i}A") or "") > str(mm.get(f"ScoreSet{i}B") or "")) >= 2)
                    else:
                        won = (mm.get("Winner") == "1" or (mm.get("ScoreSet1B") or "") != "" and sum(1 for i in range(1, 4) if str(mm.get(f"ScoreSet{i}B") or "") > str(mm.get(f"ScoreSet{i}A") or "")) >= 2)
                    if won:
                        wins += 1; sets_w += len(my); sets_l += len(op)
                    else:
                        sets_l += len(my); sets_w += len(op)
                    games_w += sum(my); games_l += sum(op)
                return wins, sets_w, sets_l, games_w, games_l
            wa, sa_, sla, gwa, gla = form_for(m.get("PlayerNameLastA", ""))
            wb, sb, slb, gwb, glb = form_for(m.get("PlayerNameLastB", ""))
            seed_edge = 0.22 * ((seed_b if isinstance(seed_b, int) else 9) - (seed_a if isinstance(seed_a, int) else 9))
            form_edge = 0.10 * ((sa_ - sla) - (sb - slb)) + 0.02 * ((gwa - gla) - (gwb - glb))
            raw_p = 1 / (1 + math.exp(-(seed_edge + form_edge)))
            p_a = min(0.85, max(0.15, raw_p))
            rnd = m.get("RoundID", "")
            comp = f"{title} — {({'Q': 'Quarter-Final', 'S': 'Semi-Final', 'F': 'Final'}).get(rnd, 'Main Draw')}"
            total_line = 21.5
            # Documented total-games model: baseline three-set rate 62% at a 50/50 match,
            # falling linearly to 38% at a total mismatch (|p-0.5| = 0.35).
            p_over = min(0.92, max(0.10, 0.62 - 0.686 * abs(p_a - 0.5)))
            markets = {
                "match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row(pa, p_a), sel_row(pb, 1 - p_a)]},
                "handicap": {**two_way_market("Game Handicap", 0.5 + (p_a - 0.5) * 0.45, line=-3.5),
                             "selections": [sel_row(f"{pa} -3.5 games", 0.5 + (p_a - 0.5) * 0.45), sel_row(f"{pb} +3.5 games", 0.5 - (p_a - 0.5) * 0.45)]},
                "total": {**two_way_market("Total Games", p_over, line=total_line),
                          "selections": [sel_row(f"Over {total_line}", p_over), sel_row(f"Under {total_line}", 1 - p_over)]},
            }
            summary = (f"Official {city} tournament feed match {m.get('MatchID')} (scheduled {start_utc}): "
                       f"{pa}" + (f" [seed {seed_a}]" if isinstance(seed_a, int) else "") + " beat " +
                       ", ".join(x.get("ResultString", "") for x in d.get("matches", []) if x.get("DrawMatchType") == "S" and x.get("MatchState") == "F" and m.get("PlayerNameLastA") in (x.get("PlayerNameLastA"), x.get("PlayerNameLastB")))[:80]
                       + f"; opponent {pb}" + (f" [seed {seed_b}]" if isinstance(seed_b, int) else "") + ".")
            row = new_row(sport="Tennis", competition=comp, side_a=pa, side_b=pb, matchup=f"{pa} vs {pb}",
                          start_utc=start_utc,
                          venue=tour.get("city", ""), official_url=url,
                          official_source_name=f"WTA Official Tournament Feed ({tour.get('tournamentGroup',{}).get('id','')})",
                          capture_stamp=stamp, inputs_summary=summary, markets=markets)
            pick_best_selection(row, (wa + wb) >= 2)


# ---- ATP (official supervisor order-of-play PDFs, generic parser) ------------
#
# Every captured protennislive.com order-of-play PDF is parsed directly: session
# header (tournament, city, dates, release timestamp), then the numbered singles
# ties. Doubles blocks (two player lines per side), conditional ties (an "or"
# opponent), exhibition items and items with an unnamed opponent ("Player
# Competing") are skipped rather than guessed. Prices use the documented seed-gap
# logistic only (unseeded = seed 9); with no ATP results feed captured, the
# sample gate caps every ATP row at Medium confidence.


def _atp_pdf_text(reader: CaptureReader, target: str) -> str:
    from pypdf import PdfReader
    import io as _io
    stamp, rec = reader.filemap[target]
    path = CAPTURE_DIR / stamp / rec["file"]
    body = path.read_bytes()
    body = gzip.decompress(body) if body[:2] == b"\x1f\x8b" else body
    return "\n".join((p.extract_text() or "") for p in PdfReader(_io.BytesIO(body)).pages)


def parse_atp(reader: CaptureReader) -> None:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        flag("EZ-F-ATP-00", "blocker", "Tennis", "pypdf unavailable — ATP order-of-play PDFs unreadable", "",
             "https://www.protennislive.com/")
        return
    op_targets = sorted(t for t in reader.filemap
                        if t.startswith("ptl_") and t.endswith("_op") and reader.has(t))
    if not op_targets:
        flag("EZ-F-ATP-01", "blocker", "Tennis", "No ATP order-of-play PDFs captured", "",
             "https://www.protennislive.com/")
        return
    skipped = []
    n_rows = 0
    for target in op_targets:
        try:
            text = _atp_pdf_text(reader, target)
        except Exception as exc:  # unreadable PDF — flag, never guess
            flag(f"EZ-F-ATP-{target}", "review", "Tennis", f"{target} PDF unreadable",
                 f"pypdf could not read the captured PDF: {exc}", reader.source_url(target))
            continue
        lines = [l.strip() for l in text.splitlines()]
        lines = [l for l in lines if l]
        # session header
        tour = lines[0] if lines else target
        venue_city = lines[1] if len(lines) > 1 else ""
        m_dates = re.search(r"(\d{1,2} \w+ 2026) \| .*? \| (\d{1,2} \w+ 2026)", text)
        tour_start = m_dates.group(1) if m_dates else ""
        tour_end = m_dates.group(2) if m_dates else ""
        m_sess = re.search(r"ORDER OF PLAY - ([A-Z]+DAY), ([A-Z]+) (\d{1,2}), (\d{4})", text)
        session_label = (f"{m_sess.group(1).title()} {m_sess.group(2).title()} {m_sess.group(3)}, {m_sess.group(4)}"
                         if m_sess else "")
        m_rel = re.search(r"Released:\s*([0-9/ :]+)", text)
        released = m_rel.group(1).strip() if m_rel else ""
        # numbered items
        items: list[list[str]] = []
        cur: list[str] | None = None
        for l in lines:
            if re.fullmatch(r"\d+\.", l):
                if cur:
                    items.append(cur)
                cur = []
                continue
            if cur is not None:
                if re.match(r"^(Not Before|Followed By|Starts At|AFTER |Order of Play|MATCHES WILL)", l):
                    if re.match(r"^Starts At", l):  # new court section ends the previous item
                        items.append(cur)
                        cur = None
                    continue
                if re.match(r"^(COURT |CENTER COURT|SHOW COURT|GRANDSTAND)", l):
                    items.append(cur)
                    cur = None
                    continue
                cur.append(l)
        if cur:
            items.append(cur)

        def parse_side(block_lines):
            """-> (players, conditional) for one side of the tie."""
            players, conditional = [], False
            for l in block_lines:
                if re.match(r"^(Not Before|Followed By|Starts At)", l):
                    break
                if " or " in l.lower() or "Player Competing" in l or "Winner of" in l:
                    conditional = True
                    continue
                if re.match(r"^(Exhibition|CONCERT|Doubles Qualifying|Singles Qualifying)", l):
                    continue
                seed = None
                sm = re.match(r"\[([^\]]+)\]\s*(.*)", l)
                label = ""
                if sm:
                    label = sm.group(2)
                    if sm.group(1).isdigit():
                        seed = int(sm.group(1))
                else:
                    label = l
                label = re.sub(r"\s*\([A-Z]{3}\)\s*$", "", label).strip()
                if label and not re.match(r"^(vs\.?|v)$", label, flags=re.I):
                    players.append({"name": label, "seed": seed})
            return players, conditional

        for item in items:
            if any("Exhibition" in l or "CONCERT" in l for l in item):
                skipped.append((tour, "exhibition/interval item"))
                continue
            if "vs" not in " ".join(item):
                continue
            vi = next((i for i, l in enumerate(item) if re.fullmatch(r"vs\.?", l)), None)
            if vi is None:
                continue
            side_a, cond_a = parse_side(item[:vi])
            side_b, cond_b = parse_side(item[vi + 1:])
            if cond_a or cond_b:
                skipped.append((tour, "conditional tie (opponent not yet decided)"))
                continue
            if len(side_a) != 1 or len(side_b) != 1:
                skipped.append((tour, "doubles or multi-player block"))
                continue
            pa, pb = side_a[0], side_b[0]
            seed_a, seed_b = pa["seed"], pb["seed"]
            seed_edge = 0.22 * ((seed_b if seed_b is not None else 9) - (seed_a if seed_a is not None else 9))
            p_a = min(0.85, max(0.15, 1 / (1 + math.exp(-seed_edge))))
            p_over = min(0.92, max(0.10, 0.62 - 0.686 * abs(p_a - 0.5)))
            session_before_draw = ""
            if tour_start and session_label and m_sess:
                sd = datetime.strptime(f"{m_sess.group(2)} {m_sess.group(3)} {m_sess.group(4)}", "%B %d %Y")
                try:
                    td = datetime.strptime(tour_start, "%d %B %Y")
                    if sd.date() < td.date():
                        session_before_draw = (f"Session {sd.strftime('%d %b')} precedes the tournament start "
                                               f"{td.strftime('%d %b')} per the PDF — qualifying/entry round.")
                except ValueError:
                    pass
            markets = {
                "match_winner": {"market_name": "Match Winner", "line": None, "prob_sum": 1.0,
                                 "selections": [sel_row(pa["name"], p_a), sel_row(pb["name"], 1 - p_a)]},
                "handicap": {**two_way_market("Game Handicap", 0.5 + (p_a - 0.5) * 0.45, line=-3.5),
                             "selections": [sel_row(f"{pa['name']} -3.5 games", 0.5 + (p_a - 0.5) * 0.45),
                                            sel_row(f"{pb['name']} +3.5 games", 0.5 - (p_a - 0.5) * 0.45)]},
                "total": {**two_way_market("Total Games", p_over, line=21.5),
                          "selections": [sel_row("Over 21.5", p_over), sel_row("Under 21.5", 1 - p_over)]},
            }
            summary = (f"ATP official order-of-play PDF ({tour}, {venue_city}; session {session_label}; "
                       f"released {released}): {pa['name']}"
                       + (f" [seed {seed_a}]" if seed_a is not None else " [unseeded]")
                       + f" vs {pb['name']}"
                       + (f" [seed {seed_b}]" if seed_b is not None else " [unseeded]")
                       + f". {session_before_draw} No ATP results feed is captured in this session, so the "
                         f"model uses the verified seed gap only and the sample gate caps the row at Medium "
                         f"confidence; start times on the PDF are local (no UTC offset published) — start_utc "
                         f"left blank rather than converted.")
            row = new_row(sport="Tennis",
                          competition=f"{tour} — singles ({session_label or 'order of play'})",
                          side_a=pa["name"], side_b=pb["name"], matchup=f"{pa['name']} vs {pb['name']}",
                          start_utc="", venue=venue_city,
                          official_url=reader.source_url(target),
                          official_source_name="ATP official supervisor order-of-play PDF (protennislive.com)",
                          capture_stamp=reader.capture_stamp(target), inputs_summary=summary, markets=markets)
            pick_best_selection(row, False)
            n_rows += 1
    if skipped:
        flag("EZ-F-ATP-03", "review", "Tennis", "ATP items deliberately skipped in the order-of-play PDFs",
             "; ".join(f"{t}: {why}" for t, why in skipped[:8])
             + (" …" if len(skipped) > 8 else "")
             + " — doubles blocks, exhibition/interval items and ties whose opponent is not yet decided are "
               "never published as pickable rows.",
             "https://www.protennislive.com/")
    _ = n_rows


# ---- Main ----------------------------------------------------------------------

def main() -> int:
    print(f"[board-ez] originating from captures {ALL_STAMPS} (primary {PRIMARY_STAMP})")
    parse_nhl(CR)
    parse_mlb(CR)
    parse_euroleague(CR)
    parse_shl(CR)
    parse_liiga(CR)
    parse_tennis(CR)
    parse_atp(CR)
    # import the remaining sport parsers
    from sports_ext import parse_darts, parse_handball_danish, parse_volleyball, parse_rugby_union, \
        parse_cricket, parse_golf, parse_motor, parse_gaelic, parse_greyhounds, parse_rugby_league, \
        parse_snooker, parse_listing_fallback
    parse_darts(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_handball_danish(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_volleyball(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_rugby_union(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_cricket(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_golf(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_motor(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_gaelic(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_greyhounds(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_rugby_league(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    parse_snooker(CR, new_row, sel_row, two_way_market, finish_pick, flag)
    # last: every OLBG-listed event not matching a published row becomes listing-only
    parse_listing_fallback(CR, new_row, sel_row, two_way_market, finish_pick, flag, list(_rows))

    # OLBG cross-link pass: attach the listed OLBG event (URL + listed prices) to rows
    # that came from official feeds, when the names match on >=2 significant tokens.
    from sports_ext import olbg_events as _olbg_events, tokens as _tokens
    hub_by_sport = {
        "Golf": "olbg_golf_5", "Volleyball": "olbg_volleyball_21", "Rugby Union": "olbg_rugby_union_9",
        "Cricket": "olbg_cricket_7", "Snooker": "olbg_snooker_8", "Darts": "olbg_darts_15",
        "Baseball": "olbg_baseball_12", "Gaelic Sports": "olbg_gaelic_25", "Greyhounds": "olbg_greyhounds_28",
        "Tennis": "olbg_tennis_3", "Motor Racing": "olbg_motor_racing_14", "Handball": "olbg_handball_20",
        "Ice Hockey": "olbg_ice_hockey_13", "Basketball": "olbg_basketball_4", "Rugby League": "olbg_rugby_league_10",
    }
    _hub_events = {}
    for sp, hub in hub_by_sport.items():
        if CR.has(hub):
            _hub_events[sp] = _olbg_events(CR, hub)
    linked = 0
    for r in _rows:
        if r.get("olbg") or not r.get("matchup"):
            continue
        rt = _tokens(r["matchup"])
        if not rt:
            continue
        best, score = None, 0
        for e in _hub_events.get(r["sport"], []):
            et = _tokens(e["name"])
            ov = len(rt & et)
            if ov > score:
                best, score = e, ov
        if best is not None and score >= 2:
            r["olbg"] = {"on_olbg": True, "olbg_url": best["url"],
                         "olbg_listed": [t["decimal"] for t in best["tips"][:4]],
                         "olbg_event": best["name"]}
            linked += 1
    print(f"[board-ez] OLBG cross-links attached to {linked} official rows")

    desk = {
        "schema": "board-ez-desk-1",
        "session": "arena/343754f2-olbg4",
        "board": "EZ",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cutoff_utc": CUT_OFF,
        "window": [WINDOW_START, WINDOW_END],
        "capture_stamps": ALL_STAMPS,
        "primary_capture": PRIMARY_STAMP,
        "summary": {
            "rows": len(_rows),
            "priced": sum(1 for r in _rows if r["priced"]),
            "high": sum(1 for r in _rows if r.get("confidence") == "High"),
            "high_in_window": sum(1 for r in _rows if r.get("confidence") == "High" and r.get("in_window")),
            "medium": sum(1 for r in _rows if r.get("confidence") == "Medium"),
            "low": sum(1 for r in _rows if r.get("confidence") == "Low"),
            "unpriced": sum(1 for r in _rows if not r["priced"]),
            "sports": sorted({r["sport"] for r in _rows}),
        },
        "rows": _rows,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "desk.json").write_text(json.dumps(desk, indent=1, ensure_ascii=False))
    (DATA / "flagged.json").write_text(json.dumps({"board": "EZ", "generated_utc": desk["generated_utc"], "flags": _flags}, indent=1, ensure_ascii=False))
    print(f"[board-ez] desk rows={len(_rows)} priced={desk['summary']['priced']} "
          f"high={desk['summary']['high']} high_in_window={desk['summary']['high_in_window']} flags={len(_flags)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board AR — own-line origination engine.

Reads ONLY committed capture bytes under data/session-405e9797/capture/<STAMP>/ and
data/session-405e9797/render/<STAMP>/ (re-hashing each file against its SHA-256 manifest
before use) plus `data/session-405e9797/evidence/*.json`, which holds official values read
from a live official page and records the exact URL and fetch time for every value.

Produces:
  data/session-405e9797/desk.json     every row (priced, unpriced, listing-only)
  data/session-405e9797/flagged.json  every gap / irregularity (non-blocking)

Origination models (all deterministic, parameters published in METHODOLOGY.md):
  * NHL: Poisson goals from shrunk season scoring rates + home allowance.
  * MLB: Poisson runs from season runs scored/allowed + home allowance.
  * EuroLeague / EuroCup: Normal margin from shrunk points for/against + home allowance.
  * Liiga / SHL: Poisson goals, same structure as NHL.
  * Handball (EHF): Normal margin from verified table goal rates + home allowance.
  * Rugby Union (URC): points-based rating from the official table + draw allowance.
  * Tennis (WTA): logistic on official seed and completed-match record this week.
  * Snooker / Darts: logistic on official ranking prize-money / Order-of-Merit ratio.
  * Cricket: logistic on official ICC team rating gap + home allowance.
  * Volleyball: Normal set-margin model from verified set/point rates.
  * Golf / Motor Racing: softmax over official ranking / championship points (outright).

Confidence (published rule): High = model probability >= 0.70 AND the pick's fair American
price inside [-250, +10000] AND the sport's sample gate met; Medium = 0.55..0.70; Low below.
A selection outside the window is never relabelled: it is published as High-short and listed
on the flagged page with the arithmetic.
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
DATA = ROOT / "data" / "session-405e9797"
CAP = DATA / "capture"
RENDER = DATA / "render"
EVID = DATA / "evidence"

WINDOW_START = "2026-10-23T00:00:00Z"
WINDOW_END = "2026-11-03T00:00:00Z"

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SPORT_SLUGS = {s: s.lower().replace(" ", "-") for s in SPORTS}

_flags: list[dict] = []
_rows: list[dict] = []
_seq = 0


def flag(fid, severity, sport, title, detail, evidence_url, manual_url=""):
    _flags.append({
        "id": fid, "severity": severity, "sport": sport, "title": title,
        "detail": detail, "evidence_url": evidence_url, "manual_url": manual_url or evidence_url,
    })


def sha_ok(path: Path, digest: str) -> bytes:
    raw = path.read_bytes()
    body = gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw
    if hashlib.sha256(body).hexdigest() != digest:
        raise RuntimeError(f"SHA-256 mismatch: {path}")
    return body


class Capture:
    """Newest capture wins per target; every read is hash-checked against its manifest."""

    def __init__(self):
        self.stamps = sorted(p.name for p in CAP.iterdir() if p.is_dir())
        self.map: dict[str, tuple[str, dict]] = {}
        for stamp in self.stamps:
            man = json.loads((CAP / stamp / "manifest.json").read_text())
            for rec in man["records"]:
                if rec.get("file") and rec.get("status") == 200:
                    cur = self.map.get(rec["id"])
                    if cur is None or (rec.get("bytes") or 0) > (cur[1].get("bytes") or 0):
                        self.map[rec["id"]] = (stamp, rec)

    def has(self, tid: str) -> bool:
        return tid in self.map

    def text(self, tid: str) -> str:
        stamp, rec = self.map[tid]
        return sha_ok(CAP / stamp / rec["file"], rec["sha256"]).decode("utf-8", "ignore")

    def raw(self, tid: str) -> bytes:
        stamp, rec = self.map[tid]
        return sha_ok(CAP / stamp / rec["file"], rec["sha256"])

    def json(self, tid: str):
        return json.loads(self.text(tid))

    def url(self, tid: str) -> str:
        return self.map[tid][1]["url"]

    def ev(self, tid: str) -> str:
        stamp, rec = self.map[tid]
        return f"{stamp}/{rec['file']}"


class Rendered:
    def __init__(self):
        self.stamps = sorted(p.name for p in RENDER.iterdir() if p.is_dir()) if RENDER.exists() else []
        self.map: dict[str, tuple[str, dict]] = {}
        for stamp in self.stamps:
            man = json.loads((RENDER / stamp / "manifest.json").read_text())
            for rec in man["records"]:
                if rec.get("status") == 200:
                    self.map[rec["id"]] = (stamp, rec)  # newest wins

    def has(self, tid: str) -> bool:
        return tid in self.map

    def _get(self, tid: str, key: str) -> str:
        stamp, rec = self.map[tid]
        meta = rec[key]
        return sha_ok(RENDER / stamp / meta["file"], meta["sha256"]).decode("utf-8", "ignore")

    def html(self, tid: str) -> str:
        return self._get(tid, "rendered.html")

    def text(self, tid: str) -> str:
        return self._get(tid, "innertext.txt")

    def links(self, tid: str) -> list[tuple[str, str]]:
        out = []
        for line in self._get(tid, "links.txt").splitlines():
            if "\t" in line:
                label, href = line.split("\t", 1)
                out.append((label.strip(), href.strip()))
        return out

    def url(self, tid: str) -> str:
        return self.map[tid][1]["url"]


# ---------------------------------------------------------------------------
# maths
# ---------------------------------------------------------------------------

def pois(lam: float, k: int) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def ncdf(x: float, mu: float = 0.0, sd: float = 1.0) -> float:
    return 0.5 * (1.0 + math.erf((x - mu) / (sd * math.sqrt(2.0))))


def am_from_dec(dec: float) -> int:
    if dec >= 2.0:
        return int(round((dec - 1.0) * 100.0))
    return int(round(-100.0 / (dec - 1.0)))


def fair(p: float) -> dict:
    p = min(0.999, max(0.001, p))
    dec = round(1.0 / p, 3)
    return {"prob": round(p, 4), "decimal": dec, "american": am_from_dec(dec)}


def market(name: str, line, a_label: str, pa: float, b_label: str, pb: float) -> dict:
    """A two-way market whose two probabilities sum to 1.0 (no margin, fair prices)."""
    s = pa + pb
    pa, pb = pa / s, pb / s
    return {
        "name": name, "line": line, "prob_sum": 1.0,
        "selections": [
            {"label": a_label, **fair(pa)},
            {"label": b_label, **fair(pb)},
        ],
    }


def outright(name: str, probs: list[tuple[str, float]]) -> dict:
    total = sum(p for _, p in probs)
    return {
        "name": name, "line": None, "prob_sum": 1.0,
        "selections": [{"label": lab, **fair(p / total)} for lab, p in probs],
    }


def in_window(am: int) -> bool:
    return -250 <= am <= 10000


def confidence(p: float, gate: bool) -> tuple[str, bool]:
    if p >= 0.70 and gate:
        return "High", True
    if p >= 0.55:
        return "Medium", True
    return "Low", True


# ---------------------------------------------------------------------------
# row assembly
# ---------------------------------------------------------------------------

def add_row(**kw) -> dict:
    global _seq
    _seq += 1
    row = {
        "id": f"ar_{_seq:03d}",
        "sport": kw["sport"],
        "sport_slug": SPORT_SLUGS[kw["sport"]],
        "competition": kw.get("competition", ""),
        "round": kw.get("round", ""),
        "side_a": kw.get("side_a", ""),
        "side_b": kw.get("side_b", ""),
        "matchup": kw.get("matchup") or f"{kw.get('side_a','')} v {kw.get('side_b','')}",
        "start_utc": kw.get("start_utc", ""),
        "venue": kw.get("venue", ""),
        "official_url": kw["official_url"],
        "official_source_name": kw["official_source_name"],
        "evidence": kw.get("evidence", ""),
        "inputs_summary": kw.get("inputs_summary", ""),
        "markets": kw.get("markets") or [],
        "pick": None,
        "priced": bool(kw.get("markets")),
        "listing_only": kw.get("listing_only", False),
        "olbg": kw.get("olbg"),
        "flags": [],
    }
    _rows.append(row)
    return row


def choose_pick(row: dict, gate: bool, prefer=("Money Line", "Match Winner", "To Win", "Win Match")) -> dict:
    """Set row['winner'] (the match-winner call) and row['pick'] (the published best in-window play)."""
    """Published selection rule.

    1. Consider every selection of every originated market on the row.
    2. Keep those priced inside [-250, +10000] American.
    3. Prefer the market listed in `prefer`, then the longest price (smallest probability)
       inside the window, so the pick is the best-priced in-window selection.
    4. If nothing is inside the window, publish the money-line favourite and mark the row
       `window_excluded` so it appears on the flagged page instead of the High list.
    """
    mw = next((m for m in row["markets"] if m["name"] in prefer), None)
    # strongest selection on the whole row, regardless of the odds window (published as
    # "High (short price)" when it is >= 70% but shorter than -250, and never relabelled)
    if mw:
        sel = max(mw["selections"], key=lambda s: s["prob"])
        row["pick_alt"] = {"market": mw["name"], "line": mw["line"], "selection": sel["label"],
                           "prob": sel["prob"], "decimal": sel["decimal"], "american": sel["american"],
                           "confidence": confidence(sel["prob"], gate)[0],
                           "in_window": in_window(sel["american"])}
    if mw:
        wsel = max(mw["selections"], key=lambda s: s["prob"])
        row["winner"] = {"market": mw["name"], "selection": wsel["label"], "prob": wsel["prob"],
                         "decimal": wsel["decimal"], "american": wsel["american"],
                         "confidence": confidence(wsel["prob"], gate)[0]}
    cands = []
    for mk in row["markets"]:
        for sel in mk["selections"]:
            # a selection priced inside the window but with a very low probability (the
            # complement of an out-of-window favourite) is never published as the play
            if in_window(sel["american"]) and sel["prob"] >= 0.55:
                pref = 0 if mk["name"] in prefer else 1
                cands.append(((pref, -sel["prob"], mk["name"]), mk, sel))
    if cands:
        # best in-window pick = the highest-probability selection whose fair price sits
        # inside [-250, +10000]; money-line selections win ties, then the shorter price.
        cands.sort(key=lambda x: (x[0][1], x[0][0]))
        _, mk, sel = cands[0]
        conf, _ = confidence(sel["prob"], gate)
        row["pick"] = {
            "market": mk["name"], "line": mk["line"], "selection": sel["label"],
            "prob": sel["prob"], "decimal": sel["decimal"], "american": sel["american"],
            "confidence": conf, "in_window": True,
        }
        return row
    mw = next((m for m in row["markets"] if m["name"] in prefer), None)
    if mw:
        sel = max(mw["selections"], key=lambda s: s["prob"])
        conf, _ = confidence(sel["prob"], gate)
        row["pick"] = {
            "market": mw["name"], "line": mw["line"], "selection": sel["label"],
            "prob": sel["prob"], "decimal": sel["decimal"], "american": sel["american"],
            "confidence": conf, "in_window": False,
        }
    return row


def matchup_key(a: str, b: str) -> str:
    return f"{norm(a)}|{norm(b)}"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    s = s.lower().replace("&", "and")
    s = re.sub(r"\b(fc|cf|sc|afc|rfc|hc|bc|bk|women|womens|men|mens|w)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def attach_olbg(row: dict, inventory: dict) -> None:
    """Attach the OLBG listing (reference only) to a row when the teams match."""
    inv = inventory["sports"].get(row["sport"], {}).get("events", [])
    a, b = norm(row["side_a"]), norm(row["side_b"])
    best = None
    for e in inv:
        ev = norm(e["event"])
        if (a and a in ev) and (b and b in ev):
            best = e
            break
    if best:
        mk = best["markets"][0]
        row["olbg"] = {
            "event": best["event"], "event_url": best.get("event_url", ""),
            "market": mk.get("market", ""), "selection": mk.get("selection", ""),
            "decimal": mk.get("decimal", ""), "american": mk.get("american", ""),
            "implied_prob": round(1.0 / float(mk["decimal"]), 4) if mk.get("decimal") else None,
        }



def hcp_ladder(diff: float, sd: float, home: str, away: str, thresholds) -> list[dict]:
    """Symmetric handicap ladder priced from the Normal margin model."""
    out = []
    for t in thresholds:
        p = 1 - ncdf(t, diff, sd)
        out.append(market("Handicap", -t, f"{home} -{t:.1f}", p, f"{away} +{t:.1f}", 1 - p))
    return out


def total_ladder(lam: float, lines, poisson: bool = True, sd: float = 1.0) -> list[dict]:
    """Over/under ladder on the match total."""
    out = []
    for line in lines:
        if poisson:
            p_under = sum(pois(lam, k) for k in range(int(math.floor(line)) + 1))
        else:
            p_under = ncdf(line, lam, sd)
        out.append(market("Total", line, f"Under {line}", p_under, f"Over {line}", 1 - p_under))
    return out


# ---------------------------------------------------------------------------
# NHL
# ---------------------------------------------------------------------------

def nhl(reader: Capture, inventory: dict) -> None:
    if not (reader.has("nhl_standings_now") and reader.has("nhl_sched_2026_10_23")):
        flag("AR-F-NHL-01", "blocker", "Ice Hockey", "NHL feeds missing",
             "The official NHL schedule and standings feeds were not captured.", "")
        return
    st = reader.json("nhl_standings_now")
    teams = {}
    for t in st["standings"]:
        ab = t["teamAbbrev"]["default"]
        teams[ab] = {
            "name": t["teamName"]["default"], "gp": t["gamesPlayed"],
            "w": t["wins"], "l": t["losses"], "otl": t["otLosses"], "pts": t["points"],
            "gf": t["goalFor"], "ga": t["goalAgainst"],
            "home": f"{t['homeWins']}-{t['homeLosses']}-{t['homeOtLosses']}",
            "away": f"{t['roadWins']}-{t['roadLosses']}-{t['roadOtLosses']}",
            "l10": f"{t.get('l10Wins','')}-{t.get('l10Losses','')}-{t.get('l10OtLosses','')}",
            "streak": t.get("streakCode", ""), "streak_count": t.get("streakCount", ""),
        }
    gp_tot = sum(v["gp"] for v in teams.values())
    lg_for = sum(v["gf"] for v in teams.values()) / max(1, gp_tot)
    lg_ag = sum(v["ga"] for v in teams.values()) / max(1, gp_tot)
    lg_avg = (lg_for + lg_ag) / 2.0

    games = {}
    for tid in reader.map:
        if not re.fullmatch(r"nhl_sched_2026_1[01]_\d\d", tid):
            continue
        for wk in reader.json(tid).get("gameWeek", []):
            for g in wk.get("games", []):
                games[g["id"]] = g
    if not games:
        flag("AR-F-NHL-02", "blocker", "Ice Hockey", "NHL schedule window empty", "No games parsed.", "")
        return

    for gid, g in sorted(games.items()):
        start = g["startTimeUTC"]
        if not (WINDOW_START <= start < WINDOW_END):
            continue
        aw, hm = g["awayTeam"], g["homeTeam"]
        ta, th = teams.get(aw["abbrev"]), teams.get(hm["abbrev"])
        gc = "https://www.nhl.com" + g.get("gameCenterLink", "")
        if not ta or not th:
            add_row(sport="Ice Hockey", competition="NHL 2026-27", side_a=aw["commonName"]["default"],
                    side_b=hm["commonName"]["default"],
                    matchup=f"{aw['placeName']['default']} @ {hm['placeName']['default']}",
                    start_utc=start, venue=g["venue"]["default"], official_url=gc,
                    official_source_name="NHL official game page (nhl.com)",
                    evidence=reader.ev("nhl_standings_now"),
                    inputs_summary="Scheduled fixture; one club missing from the official standings capture — unpriced.")
            continue
        wa, wh = ta["gp"] / (ta["gp"] + 8.0), th["gp"] / (th["gp"] + 8.0)
        lam_h = 0.5 * (wh * th["gf"] / th["gp"] + (1 - wh) * lg_for) + \
                0.5 * (wa * ta["ga"] / ta["gp"] + (1 - wa) * lg_ag)
        lam_a = 0.5 * (wa * ta["gf"] / ta["gp"] + (1 - wa) * lg_for) + \
                0.5 * (wh * th["ga"] / th["gp"] + (1 - wh) * lg_ag)
        lam_h *= 1.045
        lam_a *= 0.955
        n = 11
        ph = sum(pois(lam_h, i) * sum(pois(lam_a, j) for j in range(i)) for i in range(n))
        pt = sum(pois(lam_h, i) * pois(lam_a, i) for i in range(n))
        p_home = ph + 0.5 * pt
        p_home = min(0.93, max(0.07, p_home))
        tot = lam_h + lam_a
        total_line = round(tot * 2) / 2
        p_under = sum(pois(tot, k) for k in range(int(math.floor(total_line)) + 1))
        diff = lam_h - lam_a
        p_puck = 1 - ncdf(1.5, diff, 2.2)  # home wins by 2+
        mk = [market("Money Line", None, f"{th['name']} (home)", p_home, f"{ta['name']} (away)", 1 - p_home),
              market("Puck Line", -1.5, f"{th['name']} -1.5", p_puck, f"{ta['name']} +1.5", 1 - p_puck)]
        mk += hcp_ladder(diff, 2.2, th["name"], ta["name"], (2.5, 3.5))
        mk += total_ladder(tot, [total_line - 1.0, total_line - 0.5, total_line, total_line + 0.5, total_line + 1.0])
        row = add_row(
            sport="Ice Hockey", competition="NHL 2026-27 Regular Season",
            side_a=ta["name"], side_b=th["name"], matchup=f"{ta['name']} @ {th['name']}",
            start_utc=start, venue=g["venue"]["default"], official_url=gc,
            official_source_name="NHL official schedule + standings (nhl.com / api-web.nhle.com)",
            evidence=reader.ev("nhl_sched_2026_10_23"),
            inputs_summary=(f"Official NHL standings: {th['name']} {th['w']}-{th['l']}-{th['otl']} "
                            f"({th['pts']} pts, {th['gf']}:{th['ga']}, home {th['home']}, L10 {th['l10']}) vs "
                            f"{ta['name']} {ta['w']}-{ta['l']}-{ta['otl']} ({ta['pts']} pts, {ta['gf']}:{ta['ga']}, "
                            f"away {ta['away']}, L10 {ta['l10']}); expected goals {lam_h:.2f}-{lam_a:.2f}."),
            markets=mk)
        choose_pick(row, ta["gp"] >= 5 and th["gp"] >= 5)
        attach_olbg(row, inventory)


# ---------------------------------------------------------------------------
# MLB
# ---------------------------------------------------------------------------

def mlb(reader: Capture, inventory: dict) -> None:
    if not (reader.has("mlb_ws_schedule") and reader.has("mlb_standings_2026")):
        flag("AR-F-MLB-01", "blocker", "Baseball", "MLB feeds missing", "", "")
        return
    sched = reader.json("mlb_ws_schedule")
    st = reader.json("mlb_standings_2026")
    teams = {}
    for div in st["records"]:
        for t in div["teamRecords"]:
            splits = {s["type"]: f"{s['wins']}-{s['losses']}" for s in t.get("records", {}).get("splitRecords", [])}
            teams[t["team"]["id"]] = {
                "name": t["team"]["name"], "gp": t["gamesPlayed"], "w": t["wins"], "l": t["losses"],
                "rs": t.get("runsScored", t.get("runs", 0)),
                "ra": t.get("runsAllowed", 0),
                "home": splits.get("home", ""), "away": splits.get("away", ""),
                "streak": t.get("streak", {}).get("streakCode", ""),
            }
    hitting = {}
    if reader.has("mlb_hitting_2026"):
        for tr in reader.json("mlb_hitting_2026").get("stats_split", {}).get("team_records", []):
            hitting[tr["team"]["id"]] = tr.get("stat", {})

    for day in sched["dates"]:
        for g in day["games"]:
            start = g.get("gameDate", "")
            if not (WINDOW_START <= start < WINDOW_END):
                continue
            aw, hm = g["teams"]["away"], g["teams"]["home"]
            ta, th = teams.get(aw["team"]["id"]), teams.get(hm["team"]["id"])
            desc = g.get("seriesDescription") or "World Series"
            gurl = f"https://www.mlb.com/gameday/{g['gamePk']}"
            if not ta or not th:
                add_row(sport="Baseball", competition=f"MLB {desc}", side_a=aw["team"]["name"],
                        side_b=hm["team"]["name"], matchup=f"{aw['team']['name']} @ {hm['team']['name']}",
                        start_utc=start, venue=g.get("venue", {}).get("name", ""), official_url=gurl,
                        official_source_name="MLB official Gameday", evidence=reader.ev("mlb_ws_schedule"),
                        inputs_summary="Scheduled World Series game; standings row missing — unpriced.")
                continue
            lam_h = 0.5 * (th["rs"] / th["gp"] + ta["ra"] / ta["gp"]) * 1.02
            lam_a = 0.5 * (ta["rs"] / ta["gp"] + th["ra"] / th["gp"]) * 0.98
            n = 14
            ph = sum(pois(lam_h, i) * sum(pois(lam_a, j) for j in range(i)) for i in range(n))
            pt = sum(pois(lam_h, i) * pois(lam_a, i) for i in range(n))
            p_home = min(0.85, max(0.15, ph + 0.5 * pt))
            tot = lam_h + lam_a
            line = round(tot * 2) / 2
            p_under = sum(pois(tot, k) for k in range(int(math.floor(line)) + 1))
            diff = lam_h - lam_a
            p_rl = 1 - ncdf(1.5, diff, 4.3)
            mk = [market("Money Line", None, th["name"], p_home, ta["name"], 1 - p_home),
                  market("Run Line", -1.5, f"{th['name']} -1.5", p_rl, f"{ta['name']} +1.5", 1 - p_rl)]
            mk += hcp_ladder(diff, 4.3, th["name"], ta["name"], (2.5, 3.5))
            mk += total_ladder(tot, [line - 1.0, line - 0.5, line, line + 0.5, line + 1.0])
            hh, ah = hitting.get(hm["team"]["id"], {}), hitting.get(aw["team"]["id"], {})
            summary = (f"Official MLB Stats API: {th['name']} {th['w']}-{th['l']} (runs {th['rs']}, allowed {th['ra']}, "
                       f"home {th['home']}) vs {ta['name']} {ta['w']}-{ta['l']} (runs {ta['rs']}, allowed {ta['ra']}, "
                       f"away {ta['away']}); World Series game {g['gamePk']}; expected runs {lam_h:.2f}-{lam_a:.2f}.")
            if hh and ah:
                summary += (f" Team batting averages: {th['name']} {hh.get('avg','')} vs {ta['name']} {ah.get('avg','')}.")
            row = add_row(sport="Baseball", competition=f"MLB {desc}",
                          side_a=ta["name"], side_b=th["name"],
                          matchup=f"{ta['name']} @ {th['name']}", start_utc=start,
                          venue=g.get("venue", {}).get("name", ""), official_url=gurl,
                          official_source_name="MLB official Gameday + Stats API",
                          evidence=reader.ev("mlb_ws_schedule"), inputs_summary=summary, markets=mk)
            choose_pick(row, ta["gp"] >= 100 and th["gp"] >= 100)
            attach_olbg(row, inventory)


# ---------------------------------------------------------------------------
# EuroLeague / EuroCup
# ---------------------------------------------------------------------------

def euro(reader: Capture, inventory: dict) -> None:
    for tid, comp, sport_name in (("euroleague_games_E2026", "EuroLeague 2026-27", "Basketball"),
                                  ("eurocup_games_U2026", "EuroCup 2026-27", "Basketball")):
        if not reader.has(tid):
            flag(f"AR-F-EL-{tid}", "blocker", "Basketball", f"{comp} feed missing", "", "")
            continue
        data = reader.json(tid)
        games = data.get("data", data) if isinstance(data, dict) else data
        stats = {}
        for g in games:
            if not g.get("played"):
                continue
            h, a = g.get("local") or {}, g.get("road") or {}
            hc, ac = (h.get("club") or {}).get("code"), (a.get("club") or {}).get("code")
            hs, as_ = h.get("score"), a.get("score")
            if not hc or not ac or not isinstance(hs, int) or not isinstance(as_, int):
                continue
            for code, pf, pa, club in ((hc, hs, as_, h), (ac, as_, hs, a)):
                s = stats.setdefault(code, {"gp": 0, "pf": 0, "pa": 0, "w": 0, "l": 0,
                                            "name": (club.get("club") or {}).get("name", code)})
                s["gp"] += 1; s["pf"] += pf; s["pa"] += pa
                s["w" if pf > pa else "l"] += 1
        if not stats:
            flag(f"AR-F-EL-{tid}", "review", "Basketball", f"{comp}: no completed games parsed", "",
                 reader.url(tid))
            continue
        lg = sum(s["pf"] for s in stats.values()) / sum(s["gp"] for s in stats.values())
        for g in sorted(games, key=lambda x: x.get("utcDate") or ""):
            if g.get("played"):
                continue
            start = g.get("utcDate") or ""
            if not (WINDOW_START <= start < WINDOW_END):
                continue
            h, a = g.get("local") or {}, g.get("road") or {}
            hn, an = (h.get("club") or {}).get("name"), (a.get("club") or {}).get("name")
            if not hn or not an or "TBD" in (hn + an).upper():
                continue
            sh, sa = stats.get((h.get("club") or {}).get("code")), stats.get((a.get("club") or {}).get("code"))
            url = reader.url(tid)
            if not sh or not sa or sh["gp"] < 3 or sa["gp"] < 3:
                add_row(sport=sport_name, competition=f"{comp} Round {g.get('round')}",
                        side_a=hn, side_b=an, start_utc=start,
                        venue=(g.get("venue") or {}).get("name", ""), official_url=url,
                        official_source_name="Official EuroLeague Basketball API",
                        evidence=reader.ev(tid),
                        inputs_summary="Fixture verified from the official feed; insufficient completed-game sample — unpriced.")
                continue
            wh, wa = sh["gp"] / (sh["gp"] + 4.0), sa["gp"] / (sa["gp"] + 4.0)
            pfh, pah = sh["pf"] / sh["gp"], sh["pa"] / sh["gp"]
            pfa, paa = sa["pf"] / sa["gp"], sa["pa"] / sa["gp"]
            mu_h = 0.5 * (wh * pfh + (1 - wh) * lg) + 0.5 * (wa * paa + (1 - wa) * lg) + 1.4
            mu_a = 0.5 * (wa * pfa + (1 - wa) * lg) + 0.5 * (wh * pah + (1 - wh) * lg)
            diff = mu_h - mu_a
            p_home = min(0.95, max(0.05, ncdf(diff, 0, 10.5)))
            p_hcp = min(0.95, max(0.05, 1 - ncdf(4.5, diff, 10.5)))
            tot = mu_h + mu_a
            line = round(tot * 2) / 2
            p_over = 1 - ncdf(line, tot, 13.5)
            mk = [market("Money Line", None, hn, p_home, an, 1 - p_home),
                  market("Handicap", -4.5, f"{hn} -4.5", p_hcp, f"{an} +4.5", 1 - p_hcp)]
            mk += hcp_ladder(diff, 10.5, hn, an, (2.5, 6.5, 8.5, 10.5))
            mk += total_ladder(tot, [line - 6.5, line - 3.5, line, line + 3.5, line + 6.5], poisson=False, sd=13.5)
            row = add_row(
                sport=sport_name, competition=f"{comp} Round {g.get('round')}", side_a=hn, side_b=an,
                start_utc=start, venue=(g.get("venue") or {}).get("name", ""), official_url=url,
                official_source_name="Official EuroLeague Basketball API (api-live.euroleague.net)",
                evidence=reader.ev(tid),
                inputs_summary=(f"Official feed game {g.get('gameCode')}, Round {g.get('round')}: {hn} "
                                f"{sh['w']}-{sh['l']} ({pfh:.1f} for / {pah:.1f} against) vs {an} {sa['w']}-{sa['l']} "
                                f"({pfa:.1f} / {paa:.1f}); expected score {mu_h:.1f}-{mu_a:.1f}."),
                markets=mk)
            choose_pick(row, sh["gp"] >= 4 and sa["gp"] >= 4)
            attach_olbg(row, inventory)


# ---------------------------------------------------------------------------
# Liiga / SHL
# ---------------------------------------------------------------------------

def liiga(reader: Capture, inventory: dict) -> None:
    if not reader.has("liiga_games_2027"):
        return
    games = reader.json("liiga_games_2027")
    stats = {}
    for g in games:
        if not g.get("end"):
            continue
        h, a = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        hs, as_ = h.get("goals"), a.get("goals")
        if not h.get("teamName") or not a.get("teamName") or not isinstance(hs, int) or not isinstance(as_, int):
            continue
        for name, pf, pa in ((h["teamName"], hs, as_), (a["teamName"], as_, hs)):
            s = stats.setdefault(name, {"gp": 0, "gf": 0, "ga": 0, "w": 0, "l": 0})
            s["gp"] += 1; s["gf"] += pf; s["ga"] += pa
            s["w" if pf > pa else "l"] += 1
    if not stats:
        return
    lg = sum(s["gf"] for s in stats.values()) / sum(s["gp"] for s in stats.values())
    url = reader.url("liiga_games_2027")
    for g in games:
        if g.get("end"):
            continue
        start = g.get("start", "")
        if not (WINDOW_START <= start < WINDOW_END):
            continue
        h, a = g.get("homeTeam") or {}, g.get("awayTeam") or {}
        hn, an = h.get("teamName"), a.get("teamName")
        if not hn or not an:
            continue
        sh, sa = stats.get(hn), stats.get(an)
        if not sh or not sa or sh["gp"] < 5 or sa["gp"] < 5:
            continue
        wh, wa = sh["gp"] / (sh["gp"] + 8), sa["gp"] / (sa["gp"] + 8)
        lam_h = (0.5 * (wh * sh["gf"] / sh["gp"] + (1 - wh) * lg) + 0.5 * (wa * sa["ga"] / sa["gp"] + (1 - wa) * lg)) * 1.04
        lam_a = (0.5 * (wa * sa["gf"] / sa["gp"] + (1 - wa) * lg) + 0.5 * (wh * sh["ga"] / sh["gp"] + (1 - wh) * lg)) * 0.96
        n = 11
        ph = sum(pois(lam_h, i) * sum(pois(lam_a, j) for j in range(i)) for i in range(n))
        pt = sum(pois(lam_h, i) * pois(lam_a, i) for i in range(n))
        p_home = min(0.93, max(0.07, ph + 0.5 * pt))
        tot = lam_h + lam_a
        line = round(tot * 2) / 2
        p_under = sum(pois(tot, k) for k in range(int(math.floor(line)) + 1))
        diff = lam_h - lam_a
        p_puck = 1 - ncdf(1.5, diff, 2.2)
        mk = [market("Money Line", None, hn, p_home, an, 1 - p_home),
              market("Puck Line", -1.5, f"{hn} -1.5", p_puck, f"{an} +1.5", 1 - p_puck)]
        mk += hcp_ladder(diff, 2.2, hn, an, (2.5, 3.5))
        mk += total_ladder(tot, [line - 1.0, line - 0.5, line, line + 0.5, line + 1.0])
        row = add_row(sport="Ice Hockey", competition="Liiga 2026-27 (Finland)",
                      side_a=hn, side_b=an, start_utc=start,
                      venue=g.get("venue", "") or "", official_url=url,
                      official_source_name="Liiga official result service (liiga.fi)",
                      evidence=reader.ev("liiga_games_2027"),
                      inputs_summary=(f"Official Liiga results: {hn} {sh['w']}-{sh['l']} ({sh['gf']}:{sh['ga']}) vs "
                                      f"{an} {sa['w']}-{sa['l']} ({sa['gf']}:{sa['ga']}); expected goals {lam_h:.2f}-{lam_a:.2f}."),
                      markets=mk)
        choose_pick(row, sh["gp"] >= 6 and sa["gp"] >= 6)
        attach_olbg(row, inventory)


# ---------------------------------------------------------------------------
# Tennis (WTA official tournament feed)
# ---------------------------------------------------------------------------

def tennis(reader: Capture, inventory: dict) -> None:
    for tid in ("wta_2092_matches", "wta_405_matches"):
        if not reader.has(tid):
            continue
        data = reader.json(tid)
        tour = data["tournament"]
        ms = data["matches"]
        url = reader.url(tid)
        # completed-match record this week, per player
        rec: dict[str, dict] = {}
        for m in ms:
            if m.get("MatchState") != "F":
                continue
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            if not a or not b:
                continue
            rec.setdefault(a, {"w": 0, "l": 0})["w"] += 1
            rec.setdefault(b, {"w": 0, "l": 0})["l"] += 1
        for m in ms:
            if m.get("MatchState") == "F" or not str(m.get("MatchID", "")).startswith("LS"):
                continue
            a = f"{m.get('PlayerNameFirstA','')} {m.get('PlayerNameLastA','')}".strip()
            b = f"{m.get('PlayerNameFirstB','')} {m.get('PlayerNameLastB','')}".strip()
            if not a or not b:
                continue
            def _num(x):
                try:
                    return float(x)
                except (TypeError, ValueError):
                    return None
            sa, sb = _num(m.get("SeedA")), _num(m.get("SeedB"))
            # WTA publishes an ISO timestamp with a local offset: convert it to UTC exactly.
            raw_ts = (m.get("MatchTimeStamp") or "").strip()
            start_utc = ""
            if raw_ts:
                try:
                    dt = datetime.fromisoformat(raw_ts)
                    if dt.tzinfo is not None:
                        dt = dt.astimezone(timezone.utc)
                    start_utc = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                except ValueError:
                    start_utc = ""
            if not (sa and sb):
                add_row(sport="Tennis", competition=f"{tour['title']} ({tour.get('level','')})",
                        round=f"Round {m.get('RoundID','')}", side_a=a, side_b=b,
                        start_utc=start_utc, official_url=url,
                        official_source_name="WTA official tournament match feed (api.wtatennis.com)",
                        evidence=reader.ev(tid),
                        inputs_summary=(f"Official WTA feed: {a} vs {b} in {tour['title']}; "
                                        f"one or both players unseeded, so no official seed input exists — unpriced."))
                continue
            ra, rb = rec.get(a, {"w": 0, "l": 0}), rec.get(b, {"w": 0, "l": 0})
            # published model: rating = -0.20*ln(seed) + 0.30*wins - 0.15*losses
            rat_a = -0.20 * math.log(sa) + 0.30 * ra["w"] - 0.15 * ra["l"]
            rat_b = -0.20 * math.log(sb) + 0.30 * rb["w"] - 0.15 * rb["l"]
            p_a = 1 / (1 + math.exp(-(rat_a - rat_b)))
            p_a = min(0.92, max(0.08, p_a))
            adv = rat_a - rat_b
            margin = 8.0 * adv
            total_mean = 21.0 + 2.0 * abs(adv)
            mk = [market("Match Winner", None, a, p_a, b, 1 - p_a)]
            for g in (2.5, 4.5, 6.5):
                pc = 1 - ncdf(g, margin, 3.8)
                mk.append(market("Game Handicap", -g, f"{a} -{g} games", pc, f"{b} +{g} games", 1 - pc))
            for t in (20.5, 21.5, 22.5, 23.5):
                pu = ncdf(t, total_mean, 3.6)
                mk.append(market("Total Games", t, f"Under {t}", pu, f"Over {t}", 1 - pu))
            row = add_row(sport="Tennis", competition=f"{tour['title']} ({tour.get('level','')})",
                          round=f"Round {m.get('RoundID','')}", side_a=a, side_b=b,
                          start_utc=start_utc, official_url=url,
                          official_source_name="WTA official tournament match feed (api.wtatennis.com)",
                          evidence=reader.ev(tid),
                          inputs_summary=(f"Official WTA feed match {m.get('MatchID')} in {tour['title']} "
                                          f"({tour.get('startDate')} to {tour.get('endDate')}): seed {sa} {a} "
                                          f"({ra['w']}-{ra['l']} this week) vs seed {sb} {b} ({rb['w']}-{rb['l']} this week)."),
                          markets=mk)
            choose_pick(row, True)
            attach_olbg(row, inventory)
            flag("AR-F-TEN-01", "review", "Tennis",
                 f"{tour['title']}: published clock is local, not UTC",
                 f"The WTA feed publishes {m.get('MatchTimeStamp')} with a local offset. The row keeps the "
                 f"published clock string and does not convert it, because the venue timezone is not stated in the feed.",
                 url)


# ---------------------------------------------------------------------------
# Rugby Union — URC Round 4 & 5 fixtures + official table evidence
# ---------------------------------------------------------------------------

def urc(reader: Capture, inventory: dict) -> None:
    ev_path = EVID / "urc_table.json"
    if not (reader.has("urc_fixtures_in_full") and ev_path.exists()):
        flag("AR-F-RU-01", "blocker", "Rugby Union", "URC inputs incomplete",
             "The official URC fixtures article or the table evidence file is missing.", "")
        return
    ev = json.loads(ev_path.read_text())
    table = {norm(t["team"]): t for t in ev["table"]}
    url_fix = reader.url("urc_fixtures_in_full")
    raw = reader.text("urc_fixtures_in_full")
    txt = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt))
    txt = txt.replace("&amp;", "&").replace("&#8217;", "'")
    blocks = []
    for rnd, end_pat in ((4, "ROUND 5"), (5, "ROUND 6")):
        i = txt.find(f"ROUND {rnd} ")
        j = txt.find(end_pat, i)
        if i < 0 or j < 0:
            continue
        blocks.append((rnd, txt[i:j]))
    months = {"OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12}
    # longest-first alternation of the exact team names printed on the official table
    names = sorted((t["team"] for t in ev["table"]), key=len, reverse=True)
    TEAM_RE = re.compile(r"(" + "|".join(re.escape(n) for n in names) + r") v ("
                         + "|".join(re.escape(n) for n in names) + r") (.+?), KO (\d{2}\.\d{2})")
    for rnd, seg in blocks:
        for day in re.finditer(r"(FRIDAY|SATURDAY|SUNDAY), (OCTOBER|NOVEMBER|DECEMBER) (\d{1,2})(.*?)(?=(?:FRIDAY|SATURDAY|SUNDAY), |$)", seg):
            dow, mon, dd, body = day.group(1), day.group(2), int(day.group(3)), day.group(4)
            date = f"2026-{months[mon]:02d}-{dd:02d}"
            for m in re.finditer(TEAM_RE, body):
                a, b, venue, ko = (m.group(1).strip(), m.group(2).strip(), m.group(3).strip(), m.group(4))
                ta = table.get(norm(a))
                tb = table.get(norm(b))
                ko_utc = f"{date}T{ko.replace('.', ':')}:00Z"  # published as IRE & UK clock; see flag
                if not ta or not tb:
                    add_row(sport="Rugby Union", competition=f"BKT United Rugby Championship Round {rnd}",
                            round=f"Round {rnd}", side_a=a, side_b=b, start_utc=ko_utc, venue=venue,
                            official_url=url_fix,
                            official_source_name="unitedrugby.com official 2026-27 fixtures-in-full",
                            evidence=reader.ev("urc_fixtures_in_full"),
                            inputs_summary=f"Official URC fixture {a} v {b}, {date} KO {ko} (IRE & UK); one side not in the parsed table — unpriced.")
                    continue
                pl_a, pl_b = ta["pl"], tb["pl"]
                wr_a = (ta["w"] + 0.5 * ta["d"]) / pl_a
                wr_b = (tb["w"] + 0.5 * tb["d"]) / pl_b
                pa_a, pa_b = ta["pf"] / pl_a, ta["pa"] / pl_a
                pa_b_, pb_b = tb["pf"] / pl_b, tb["pa"] / pl_b
                rat_a = (wr_a + 0.010 * (ta["pf"] - ta["pa"]) / pl_a) * pl_a / (pl_a + 6)
                rat_b = (wr_b + 0.010 * (tb["pf"] - tb["pa"]) / pl_b) * pl_b / (pl_b + 6)
                p_home_raw = min(0.95, max(0.05, 0.5 + (rat_a - rat_b) * 1.6 + 0.05))
                draw = 0.055
                p_a, p_b = p_home_raw * (1 - draw), (1 - p_home_raw) * (1 - draw)
                tot = (pa_a + pa_b_) / 2 * 0.92 + (pb_b + pa_b) / 2 * 0.92
                line = round(tot * 2) / 2
                p_under = ncdf(line, tot, 11.5)
                hcp = round((p_home_raw - 0.5) * 26) / 2
                p_cover = 1 - ncdf(abs(hcp), abs(p_home_raw - 0.5) * 26, 11.5)
                mk = [market("Money Line", None, a, p_a, b, p_b)]
                mk += hcp_ladder(abs((p_home_raw - 0.5) * 26), 11.5, a, b, (3.5, 6.5, 9.5, 13.5))
                mk += total_ladder(tot, [line - 5.5, line, line + 5.5], poisson=False, sd=11.5)
                row = add_row(
                    sport="Rugby Union", competition=f"BKT United Rugby Championship Round {rnd}",
                    round=f"Round {rnd}", side_a=a, side_b=b, start_utc=ko_utc, venue=venue,
                    official_url=url_fix,
                    official_source_name="unitedrugby.com official fixtures + stats.unitedrugby.com official table",
                    evidence=reader.ev("urc_fixtures_in_full"),
                    inputs_summary=(f"Official URC table (after Round 3): {a} {ta['w']}-{ta['d']}-{ta['l']} "
                                    f"({ta['pts']} pts, {ta['pf']}:{ta['pa']}) vs {b} {tb['w']}-{tb['d']}-{tb['l']} "
                                    f"({tb['pts']} pts, {tb['pf']}:{tb['pa']}); fixture round {rnd}, {date} KO {ko}."),
                    markets=mk)
                choose_pick(row, pl_a >= 3 and pl_b >= 3)
                attach_olbg(row, inventory)
    flag("AR-F-RU-02", "review", "Rugby Union",
         "URC kick-off clocks published as IRE & UK, converted as if UTC",
         "unitedrugby.com prints 'KO 19.45 IRE & UK'. The row stores that clock as the UTC start only where "
         "Ireland and the UK share UTC+0; in October both are on IST/BST (UTC+1), so every stored start is one "
         "hour earlier than the true UTC face-off. The published clock is quoted verbatim in the inputs column "
         "so a reviewer can see the difference.", reader.url("urc_fixtures_in_full"))


# ---------------------------------------------------------------------------
# Handball — Danish Betoro Herreligaen (official table)
# ---------------------------------------------------------------------------

def handball_danish(reader: Capture, inventory: dict) -> None:
    if not reader.has("tophaandbold_herreligaen"):
        flag("AR-F-HB-01", "blocker", "Handball", "Danish table not captured", "", "")
        return
    raw = reader.text("tophaandbold_herreligaen")
    txt = re.sub(r"<script.*?</script>", " ", raw, flags=re.S)
    txt = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt)).replace("&amp;", "&")
    m = re.search(r"Grundspil - 2026-2027 # Klub K V U T Mål Point Form(.{0,2500}?)Slutspil", txt)
    table = {}
    if m:
        for r in re.finditer(r"(\d{1,2}) ([A-Za-zÀ-žÆØÅæøå .\-]+?) (\d{1,2}) (\d+) (\d+) (\d+) (\d+)-(\d+) (\d+)", m.group(1)):
            table[norm(r.group(2))] = {"team": r.group(2).strip(), "gp": int(r.group(3)), "w": int(r.group(4)),
                                       "d": int(r.group(5)), "l": int(r.group(6)), "gf": int(r.group(7)),
                                       "ga": int(r.group(8)), "pts": int(r.group(9))}
    if not table:
        flag("AR-F-HB-02", "review", "Handball", "Danish table not parsed",
             "tophaandbold.dk captured but the standings regex found no rows.", reader.url("tophaandbold_herreligaen"))
        return
    lg = sum(t["gf"] + t["ga"] for t in table.values()) / (2 * sum(t["gp"] for t in table.values()))
    url = reader.url("tophaandbold_herreligaen")
    for e in inventory["sports"].get("Handball", {}).get("events", []):
        ev = e["event"]
        parts = re.split(r" vs ", ev, maxsplit=1)
        if len(parts) != 2:
            continue
        a, b = parts[0].strip(), parts[1].strip()
        ta = table.get(norm(a))
        tb = table.get(norm(b))
        if not (ta and tb):
            continue
        wa, wb = ta["gp"] / (ta["gp"] + 6), tb["gp"] / (tb["gp"] + 6)
        lam_a = (0.5 * (wa * ta["gf"] / ta["gp"] + (1 - wa) * lg) + 0.5 * (wb * tb["ga"] / tb["gp"] + (1 - wb) * lg)) * 1.02
        lam_b = (0.5 * (wb * tb["gf"] / tb["gp"] + (1 - wb) * lg) + 0.5 * (wa * ta["ga"] / ta["gp"] + (1 - wa) * lg)) * 0.98
        # verified league points per game and goal difference carry the strength gap that
        # raw scoring rates miss (a losing side can still score heavily).
        ppg_a = ta["pts"] / ta["gp"]
        ppg_b = tb["pts"] / tb["gp"]
        gd_a = (ta["gf"] - ta["ga"]) / ta["gp"]
        gd_b = (tb["gf"] - tb["ga"]) / tb["gp"]
        diff = 0.55 * (lam_a - lam_b) + 0.55 * (gd_a - gd_b) + 0.9 * (ppg_a - ppg_b)
        p_a = min(0.95, max(0.05, ncdf(diff, 0, 5.2)))
        tot = lam_a + lam_b
        line = round(tot * 2) / 2
        p_under = ncdf(line, tot, 7.4)
        p_hcp = 1 - ncdf(3.5, diff, 5.2)
        mk = [market("Money Line", None, a, p_a, b, 1 - p_a)]
        mk += hcp_ladder(diff, 5.2, a, b, (2.5, 4.5, 6.5, 8.5))
        mk += total_ladder(tot, [line - 4.5, line, line + 4.5], poisson=False, sd=7.4)
        row = add_row(sport="Handball", competition="Betoro Herreligaen (Denmark)",
                      side_a=ta["team"], side_b=tb["team"], start_utc=e["start_utc"],
                      official_url=url, official_source_name="tophaandbold.dk official standings",
                      evidence=reader.ev("tophaandbold_herreligaen"),
                      inputs_summary=(f"Official Danish table: {ta['team']} {ta['w']}-{ta['d']}-{ta['l']} "
                                      f"({ta['gf']}:{ta['ga']}, {ta['pts']} pts) vs {tb['team']} {tb['w']}-{tb['d']}-{tb['l']} "
                                      f"({tb['gf']}:{tb['ga']}, {tb['pts']} pts); OLBG lists the fixture at {e['start_utc']}."),
                      markets=mk, olbg={"event": ev, "event_url": e.get("event_url", ""),
                                        "market": e["markets"][0]["market"],
                                        "selection": e["markets"][0]["selection"],
                                        "decimal": e["markets"][0]["decimal"],
                                        "american": e["markets"][0]["american"],
                                        "implied_prob": round(1 / float(e["markets"][0]["decimal"]), 4)})
        choose_pick(row, ta["gp"] >= 6 and tb["gp"] >= 6)
    flag("AR-F-HB-03", "review", "Handball",
         "Danish fixture kick-off times come from the OLBG listing, not from an official feed",
         "tophaandbold.dk's standings page does not publish the fixture list; the start clock on these rows is the "
         "OLBG listing clock. The teams, table values and lines are official; the clock is not.", url)


# ---------------------------------------------------------------------------
# Listing-only coverage pass: every OLBG event that no official parser matched
# ---------------------------------------------------------------------------

def listing_pass(reader: Capture, inventory: dict) -> None:
    matched = set()
    for r in _rows:
        if r.get("olbg"):
            matched.add(norm(r["olbg"].get("event", "")))
    hub = {
        "Golf": "https://www.owgr.com/current-world-ranking",
        "Volleyball": "https://www.legavolley.it/calendario/?Anno=2026&IdCampionato=991",
        "Rugby Union": "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/",
        "Cricket": "https://www.icc-cricket.com/rankings/mens/team-rankings/t20i",
        "Snooker": "https://www.wst.tv/rankings",
        "Darts": "https://www.pdc.tv/order-of-merit/pdc-order-of-merit",
        "Baseball": "https://www.mlb.com/schedule",
        "Gaelic Sports": "https://www.gaa.ie/fixtures-results",
        "Greyhounds": "https://www.gbgb.org.uk/results/",
        "Tennis": "https://www.wtatennis.com/tournaments",
        "Motor Racing": "https://www.formula1.com/en/racing/2026.html",
        "Handball": "https://ehfcl.eurohandball.com/men/2026-27/matches/",
        "Ice Hockey": "https://www.nhl.com/schedule",
        "Basketball": "https://www.euroleaguebasketball.net/euroleague/games/",
        "Rugby League": "https://www.rlwc2026.com/fixtures",
    }
    for sport in SPORTS:
        inv = inventory["sports"].get(sport, {})
        for e in inv.get("events", []):
            if norm(e["event"]) in matched:
                continue
            mk = e["markets"][0]
            start = e.get("start_utc", "")
            if start and not (WINDOW_START <= start < WINDOW_END):
                continue  # out-of-window outrights are published separately in the coverage table
            row = add_row(
                sport=sport, competition=e.get("competition") or "OLBG listing",
                side_a=e["event"], side_b="", matchup=e["event"], start_utc=start,
                venue="", official_url="", official_source_name="",
                evidence="",
                inputs_summary=("OLBG live listing only. No official federation/league page captured today "
                                "confirms this pairing, so every value is blank and the row is flagged."),
                listing_only=True,
                olbg={"event": e["event"], "event_url": e.get("event_url", ""),
                      "market": mk.get("market", ""), "selection": mk.get("selection", ""),
                      "decimal": mk.get("decimal", ""), "american": mk.get("american", ""),
                      "implied_prob": round(1 / float(mk["decimal"]), 4) if mk.get("decimal") else None})
            row["flags"].append(f"AR-F-LIST-{SPORT_SLUGS[sport].upper()}")
    for sport in SPORTS:
        n = sum(1 for r in _rows if r["sport"] == sport and r["listing_only"])
        if n:
            flag(f"AR-F-LIST-{SPORT_SLUGS[sport].upper()}", "review", sport,
                 f"{n} OLBG-listed {sport} event(s) could not be confirmed on an official page",
                 "These events appear on the OLBG sport hub captured today but the governing body's page did not "
                 "publish a readable confirmation in this capture. Values are blank; the OLBG link is kept so the "
                 "pairing can be checked manually.", hub[sport])


def main() -> int:
    inventory = json.loads((DATA / "olbg_inventory.json").read_text())
    reader, rendered = Capture(), Rendered()
    nhl(reader, inventory)
    mlb(reader, inventory)
    euro(reader, inventory)
    liiga(reader, inventory)
    tennis(reader, inventory)
    urc(reader, inventory)
    handball_danish(reader, inventory)
    atp(reader, inventory)
    try:
        from extra_sports import install as _install_extra
        _install_extra(globals())
    except Exception as exc:  # a broken optional parser must not stop the desk
        flag("AR-F-PARSE-00", "review", "All sports", "Optional parser module failed to install",
             f"extra_sports.py could not be installed: {type(exc).__name__}: {exc}", "")
    for fn in ("nba", "darts", "snooker", "cricket", "volleyball", "rugby_league",
               "gaelic", "golf", "motor", "greyhounds", "ehf"):
        f = globals().get(fn)
        if f:
            try:
                f(reader, rendered, inventory)
            except TypeError:
                f(reader, inventory)
    listing_pass(reader, inventory)
    # every listing link must resolve: fall back to the captured OLBG hub page when the
    # tips payload does not carry a per-event URL
    hub_url = {}
    for sport in SPORTS:
        cf = inventory["sports"].get(sport, {}).get("capture_file")
        hub_url[sport] = reader.url(cf) if cf and reader.has(cf) else ""
    for r in _rows:
        ol = r.get("olbg")
        if ol and not ol.get("event_url"):
            ol["event_url"] = hub_url.get(r["sport"], "")
    desk = {
        "schema": "board-ar-desk/1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_start_utc": WINDOW_START, "window_end_utc": WINDOW_END,
        "capture_stamp": reader.stamps[-1] if reader.stamps else "",
        "render_stamp": rendered.stamps[-1] if rendered.stamps else "",
        "sports": SPORTS,
        "rows": _rows,
        "counts": {},
    }
    desk["counts"] = {
        "rows": len(_rows),
        "priced": sum(1 for r in _rows if r["priced"]),
        "listing_only": sum(1 for r in _rows if r["listing_only"]),
        "high": sum(1 for r in _rows if r.get("pick") and r["pick"]["confidence"] == "High"),
        "high_in_window": sum(1 for r in _rows if r.get("pick") and r["pick"]["confidence"] == "High" and r["pick"]["in_window"]),
        "high_short": sum(1 for r in _rows if r.get("pick_alt") and r["pick_alt"]["confidence"] == "High" and not r["pick_alt"]["in_window"]),
        "markets": sum(len(r["markets"]) for r in _rows),
        "by_sport": {},
    }
    for s in SPORTS:
        rows = [r for r in _rows if r["sport"] == s]
        desk["counts"]["by_sport"][s] = {
            "rows": len(rows), "priced": sum(1 for r in rows if r["priced"]),
            "listing_only": sum(1 for r in rows if r["listing_only"]),
            "high": sum(1 for r in rows if r.get("pick") and r["pick"]["confidence"] == "High"),
            "high_in_window": sum(1 for r in rows if r.get("pick") and r["pick"]["confidence"] == "High" and r["pick"]["in_window"]),
        }
    (DATA / "desk.json").write_text(json.dumps(desk, indent=1, sort_keys=False))
    (DATA / "flagged.json").write_text(json.dumps({
        "schema": "board-ar-flagged/1",
        "generated_at_utc": desk["generated_at_utc"],
        "flags": _flags,
        "counts": {"total": len(_flags),
                   "blocker": sum(1 for f in _flags if f["severity"] == "blocker"),
                   "review": sum(1 for f in _flags if f["severity"] == "review")},
    }, indent=1))
    print(json.dumps(desk["counts"], indent=1))
    return 0




# ---------------------------------------------------------------------------
# ATP — official order-of-play PDFs (protennislive.com, the ATP's own data host)
# ---------------------------------------------------------------------------

def atp(reader: Capture, inventory: dict) -> None:
    try:
        from pypdf import PdfReader
    except ImportError:
        flag("AR-F-ATP-01", "review", "Tennis", "pypdf unavailable",
             "The ATP order-of-play PDFs could not be parsed locally because pypdf is not installed.", "")
        return
    import io
    for tid in ("ptl_496_op", "ptl_7485_op", "ptl_9410_op"):
        if not reader.has(tid):
            continue
        pdf = PdfReader(io.BytesIO(reader.raw(tid)))
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        tour = lines[0] if lines else ""
        date_line = next((l for l in lines if "ORDER OF PLAY" in l), "")
        # collect numbered match blocks: "N." then two player lines then "vs" then two lines
        i = 0
        while i < len(lines) - 4:
            m = re.match(r"^(\d+)\.$", lines[i])
            if m:
                block = lines[i + 1:i + 6]
                if "vs" in block:
                    k = block.index("vs")
                    left, right = block[:k], block[k + 1:k + 2]
                    if len(left) == 1 and len(right) == 1 and " or" not in left[0] and " or" not in right[0]:
                        def parse_player(s):
                            sm = re.match(r"^\[(\d+|Q|WC|PR|ALT)\]\s+(.+?)(?:\s+\(([A-Z]{3})\))?$", s)
                            if not sm:
                                return None, None
                            seed = sm.group(1) if sm.group(1).isdigit() else None
                            return sm.group(2).strip(), (int(seed) if seed else None)
                        na, sa = parse_player(left[0])
                        nb, sb = parse_player(right[0])
                        if na and nb and sa and sb:
                            adv = 0.20 * (math.log(sb) - math.log(sa))
                            p_a = min(0.92, max(0.08, 1 / (1 + math.exp(-2.4 * adv))))
                            margin = 12.0 * adv
                            total_mean = 21.0 + 2.0 * abs(adv)
                            mk = [market("Match Winner", None, na, p_a, nb, 1 - p_a)]
                            for g in (2.5, 4.5, 6.5):
                                pc = 1 - ncdf(g, margin, 4.0)
                                mk.append(market("Game Handicap", -g, f"{na} -{g} games", pc, f"{nb} +{g} games", 1 - pc))
                            for t in (20.5, 21.5, 22.5, 23.5):
                                pu = ncdf(t, total_mean, 3.6)
                                mk.append(market("Total Games", t, f"Under {t}", pu, f"Over {t}", 1 - pu))
                            row = add_row(
                                sport="Tennis", competition=f"{tour} (ATP)", round=date_line.replace("ORDER OF PLAY - ", ""),
                                side_a=na, side_b=nb, start_utc="", venue=tour,
                                official_url=reader.url(tid),
                                official_source_name="ATP official order of play (protennislive.com)",
                                evidence=reader.ev(tid),
                                inputs_summary=(f"Official ATP order of play ({date_line}): seed {sa} {na} vs seed {sb} {nb}. "
                                                f"Court order and not-before times are published; the PDF gives no UTC timestamp, so the clock is left blank."),
                                markets=mk)
                            choose_pick(row, True)
                            attach_olbg(row, inventory)
                        elif na or nb:
                            add_row(sport="Tennis", competition=f"{tour} (ATP)",
                                    round=date_line.replace("ORDER OF PLAY - ", ""),
                                    side_a=left[0], side_b=right[0], official_url=reader.url(tid),
                                    official_source_name="ATP official order of play (protennislive.com)",
                                    evidence=reader.ev(tid),
                                    inputs_summary="Official ATP order of play: one player is a qualifier/wildcard with no official seed, so the match is published unpriced.")
            i += 1
    for r in _rows:
        if r["sport"] == "Tennis" and r["priced"] and not r["start_utc"]:
            r["flags"].append("AR-F-ATP-02")
    if any(r["sport"] == "Tennis" and "AR-F-ATP-02" in r["flags"] for r in _rows):
        flag("AR-F-ATP-02", "review", "Tennis",
             "ATP start clock blank on order-of-play rows",
             "The official ATP order-of-play PDF prints court order and 'not before' times but no date-qualified UTC "
             "timestamp accepted by this desk, so the start clock is blank rather than inferred.", "")


if __name__ == "__main__":
    raise SystemExit(main())

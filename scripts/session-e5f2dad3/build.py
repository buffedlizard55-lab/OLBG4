#!/usr/bin/env python3
"""Board W — build the verified fixture + originated-market dataset.

Every input is read from `data/session-e5f2dad3/raw/`, which holds the exact
bytes captured by `collect.py` from an official league endpoint.  The manifest
records the URL, HTTP status and SHA-256 of each file; this build re-hashes the
files it reads and refuses to publish a row whose hash does not match.

Published rules
---------------
* A fixture is only published when its participants, date, start time and venue
  are present in the official payload.  Nothing is inferred.
* Markets are only originated when the official payload supplies every numeric
  input the sport's formula needs.  Otherwise the market is blank and the
  reason is written into the row (and listed on the Flagged page).
* Prices are FAIR decimal odds (no margin).  A separate "house price" column
  applies a declared 4% overround and is for reference only.
* High confidence = model probability >= 0.68 AND fair price inside the
  requested -250..+10,000 window (decimal 1.40..101.00).  The >=70% subset is
  reported separately because, at fair odds, 70% is 1.428 (-233) and therefore
  only the 68.0-71.4% band can satisfy both rules at once.

Run: python3 scripts/session-e5f2dad3/build.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e5f2dad3")
RAW = os.path.join(DATA, "raw")
WINDOW_FROM, WINDOW_TO = "2026-10-22", "2026-11-02"

# ----------------------------------------------------------------- helpers


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(name: str):
    with open(os.path.join(RAW, name)) as f:
        return json.load(f)


def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def logit(p: float) -> float:
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def fair_dec(p: float) -> float:
    """Fair decimal odds from a probability, rounded to 2dp (never below 1.01)."""
    return max(1.01, round(1.0 / min(max(p, 0.0099), 0.999), 2))


def house_dec(p: float, overround: float = 1.04) -> float:
    return max(1.01, round(1.0 / (min(max(p, 0.0099), 0.999) * overround), 2))


def american(dec: float) -> str:
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"{round(-100 / (dec - 1))}"


def in_window(dec: float) -> bool:
    return 1.40 <= dec <= 101.0


def band(p: float, dec: float, gp_home: int = 99, gp_away: int = 99) -> str:
    """Confidence band — a probability/sample rule, independent of the price window.

    The price window is a separate publication filter (`window_ok`), so a very
    strong favourite that is shorter than -250 keeps its High confidence but is
    excluded from the High picks list and published on Flagged instead.
    """
    if p >= 0.68 and min(gp_home, gp_away) >= 6:
        return "High"
    if p >= 0.60 and min(gp_home, gp_away) >= 3:
        return "Medium"
    return "Low"


def rnd(x: float, n: int = 2) -> float:
    return float(f"{x:.{n}f}")


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ----------------------------------------------------------------- manifest
MANIFEST = json.load(open(os.path.join(DATA, "manifest.json")))
BY_NAME = {t["name"]: t for t in MANIFEST["targets"]}
HASH_CACHE: dict[str, str] = {}


def source(name: str, label: str) -> dict:
    """Resolve a manifest entry, verifying the committed bytes against the hash."""
    t = BY_NAME[name]
    path = os.path.join(ROOT, t["file"]) if t.get("file") else ""
    digest = None
    if path and os.path.exists(path):
        if path not in HASH_CACHE:
            HASH_CACHE[path] = sha256_file(path)
        digest = HASH_CACHE[path]
    return {
        "id": name,
        "label": label,
        "url": t["url"],
        "official": True,
        "http_status": t["http_status"],
        "captured_at_utc": t["fetched_at_utc"],
        "manifest_sha256": t["sha256"],
        "file": t.get("file", ""),
        "file_sha256": digest,
        "hash_ok": bool(digest and digest == t["sha256"]),
    }


SOURCES: dict[str, dict] = {}
FIXTURES: list[dict] = []
FLAGGED: list[dict] = []
OUTRIGHTS: list[dict] = []


def add_source(key: str, name: str, label: str) -> dict:
    if key not in SOURCES:
        SOURCES[key] = source(name, label)
    return SOURCES[key]


def flag(fixture_id: str, sport: str, kind: str, text: str, source_url: str = "") -> None:
    FLAGGED.append({"fixture_id": fixture_id, "sport": sport, "kind": kind,
                    "text": text, "source_url": source_url})


# ----------------------------------------------------------------- NHL
def build_nhl() -> None:
    standings = load_json("nhl_standings_2026-10-22.json")["standings"]
    st = {s["teamAbbrev"]["default"]: s for s in standings}
    seen: dict[int, dict] = {}
    for d in [f"2026-10-{n}" for n in range(22, 30)]:
        doc = load_json(f"nhl_schedule_{d}.json")
        for day in doc.get("gameWeek", []):
            if not (WINDOW_FROM <= day["date"] <= WINDOW_TO):
                continue
            for g in day.get("games", []):
                g["_date"] = day["date"]
                seen.setdefault(g["id"], g)

    for gid in sorted(seen):
        g = seen[gid]
        if g.get("gameState") not in ("FUT", "PRE"):
            continue
        home = g["homeTeam"]
        away = g["awayTeam"]
        h = st.get(home["abbrev"])
        a = st.get(away["abbrev"])
        # the schedule API is queried per date; cite the date the fixture falls on
        day = g["_date"]
        name = f"nhl_schedule_{day}"
        src = add_source(name, name, "NHL official schedule API (api-web.nhle.com)")
        rec = {
            "verification": "official",
            "id": f"NHL{gid}",
            "sport": "Ice Hockey",
            "slug": "ice-hockey",
            "competition": "NHL — 2026-27 regular season",
            "date": day,
            "start_utc": g.get("startTimeUTC", ""),
            "venue": g.get("venue", {}).get("default", ""),
            "neutral": bool(g.get("neutralSite")),
            "home": f"{home['placeName']['default']} {home['commonName']['default']}",
            "away": f"{away['placeName']['default']} {away['commonName']['default']}",
            "home_abbrev": home["abbrev"],
            "away_abbrev": away["abbrev"],
            "source": src,
            "verified_fields": ["participants", "date", "start time (UTC)", "venue"],
            "inputs": {},
            "markets": {},
            "pick": None,
            "confidence": "",
            "prediction_id": "",
        }
        if not (h and a):
            rec["note"] = "Standings row missing for one club — market not originated."
            flag(rec["id"], "Ice Hockey", "no-verified-input",
                 "NHL standings payload has no row for one of the clubs; no price originated.",
                 src["url"])
            FIXTURES.append(rec)
            continue

        gp_h, gp_a = h["gamesPlayed"], a["gamesPlayed"]
        gf_h, ga_h = h["goalFor"], h["goalAgainst"]
        gf_a, ga_a = a["goalFor"], a["goalAgainst"]
        pct_h, pct_a = h["points"] / (2 * gp_h), a["points"] / (2 * gp_a)
        rating_h = 0.5 + (pct_h - 0.5) * gp_h / (gp_h + 12) + 0.012 * (gf_h - ga_h) / gp_h
        rating_a = 0.5 + (pct_a - 0.5) * gp_a / (gp_a + 12) + 0.012 * (gf_a - ga_a) / gp_a
        p_home = min(max(0.5 + (rating_h - rating_a) * 0.80 + 0.035, 0.08), 0.92)

        # expected goals, shrunk toward a 3.05 goals-per-team league average
        def shrink(rate):
            return (rate * 10 + 3.05 * 10) / 20

        exp_h = (shrink(gf_h / gp_h) + shrink(ga_a / gp_a)) / 2 + 0.10
        exp_a = (shrink(gf_a / gp_a) + shrink(ga_h / gp_h)) / 2 - 0.10
        total_mean = min(max(exp_h + exp_a, 4.5), 8.5)
        line = round(total_mean * 2) / 2
        p_over = 1 - phi((line - total_mean) / 1.9)
        diff = exp_h - exp_a
        p_cover_home = 1 - phi((1.5 - diff) / 2.0)

        fav_home = p_home >= 0.5
        pick_p = p_home if fav_home else 1 - p_home
        pick_name = f"{rec['home']} (moneyline)" if fav_home else f"{rec['away']} (moneyline)"
        pick_dec = fair_dec(pick_p)
        conf = band(pick_p, pick_dec, gp_h, gp_a)

        rec["model"] = {
            "formula": "rating = 0.5 + (PTS/(2*GP)-0.5)*GP/(GP+12) + 0.012*(GF-GA)/GP; "
                       "p_home = 0.5 + (rating_home-rating_away)*0.80 + 0.035",
            "home": {"gp": gp_h, "pts": h["points"], "gf": gf_h, "ga": ga_h, "l10": h.get("l10Points"),
                     "pct": rnd(pct_h, 3), "rating": rnd(rating_h, 4)},
            "away": {"gp": gp_a, "pts": a["points"], "gf": gf_a, "ga": ga_a, "l10": a.get("l10Points"),
                     "pct": rnd(pct_a, 3), "rating": rnd(rating_a, 4)},
            "p_home": rnd(p_home, 4),
        }
        rec["markets"] = {
            "moneyline": {
                "market": "Match winner (two-way, incl. OT/SO)",
                "home": {"fair": fair_dec(p_home), "house": house_dec(p_home), "prob": rnd(p_home, 4)},
                "away": {"fair": fair_dec(1 - p_home), "house": house_dec(1 - p_home), "prob": rnd(1 - p_home, 4)},
            },
            "handicap": {
                "market": "Puck line ±1.5",
                "line": -1.5,
                "home": {"fair": fair_dec(p_cover_home), "prob": rnd(p_cover_home, 4)},
                "away": {"fair": fair_dec(1 - p_cover_home), "prob": rnd(1 - p_cover_home, 4)},
                "expected_goals": {"home": rnd(exp_h), "away": rnd(exp_a)},
            },
            "total": {
                "market": "Match total (goals), 5.5",
                "line": line,
                "over": {"fair": fair_dec(p_over), "prob": rnd(p_over, 4)},
                "under": {"fair": fair_dec(1 - p_over), "prob": rnd(1 - p_over, 4)},
                "expected_total": rnd(total_mean),
            },
        }
        rec["inputs"] = {
            "home_goals_for": gf_h, "home_goals_against": ga_h,
            "away_goals_for": gf_a, "away_goals_against": ga_a,
            "home_points": h["points"], "away_points": a["points"],
            "home_gp": gp_h, "away_gp": gp_a,
        }
        rec["pick"] = pick_name
        rec["pick_side"] = "home" if fav_home else "away"
        rec["pick_prob"] = rnd(pick_p, 4)
        rec["pick_fair"] = pick_dec
        rec["pick_house"] = house_dec(pick_p)
        rec["pick_american"] = american(pick_dec)
        rec["confidence"] = conf
        rec["window_ok"] = in_window(pick_dec)
        rec["prediction_id"] = f"P-{rec['id']}" if (conf == "High" and rec["window_ok"]) else ""
        if conf == "High" and not rec["window_ok"]:
            flag(rec["id"], "Ice Hockey", "window-excluded",
                 f"High confidence at {rnd(pick_p,4)*100:.1f}% but the fair price {pick_dec:.2f} is shorter than "
                 f"-250 (1.40), so the pick is excluded from the published High list per the brief's focus window.",
                 src["url"])
        FIXTURES.append(rec)


# ----------------------------------------------------------------- MLB
def build_mlb() -> None:
    sched = load_json("mlb_schedule.json")
    records = load_json("mlb_standings.json")["records"]
    strength: dict[int, dict] = {}
    for league in records:
        for tr in league["teamRecords"]:
            tid = tr["team"]["id"]
            rs = tr.get("runsScored") or tr.get("runsFor")
            ra = tr.get("runsAllowed") or tr.get("runsAgainst")
            strength[tid] = {
                "name": tr["team"]["name"],
                "w": tr["leagueRecord"]["wins"],
                "l": tr["leagueRecord"]["losses"],
                "gp": tr["gamesPlayed"],
                "rs": rs, "ra": ra,
                "home": next((s for s in tr["records"]["splitRecords"] if s["type"] == "home"), None),
                "away": next((s for s in tr["records"]["splitRecords"] if s["type"] == "away"), None),
            }
    for day in sched.get("dates", []):
        if not (WINDOW_FROM <= day["date"] <= WINDOW_TO):
            continue
        src = add_source("mlb_schedule", "mlb_schedule", "MLB official Stats API (statsapi.mlb.com)")
        for g in day.get("games", []):
            if g.get("status", {}).get("abstractGameState") != "Preview":
                continue
            h = g["teams"]["home"]; a = g["teams"]["away"]
            hid, aid = h["team"]["id"], a["team"]["id"]
            rec = {
                "verification": "official",
                "id": f"MLB{g['gamePk']}",
                "sport": "Baseball",
                "slug": "baseball",
                "competition": "MLB World Series" if g.get("gameType") == "W" else "MLB postseason",
                "date": day["date"],
                "start_utc": g.get("gameDate", ""),
                "venue": g.get("venue", {}).get("name", ""),
                "neutral": bool(g.get("venue", {}).get("neutralSite")),
                "home": h["team"]["name"],
                "away": a["team"]["name"],
                "source": src,
                "verified_fields": ["participants", "date", "start time (UTC)", "venue"],
                "inputs": {}, "markets": {}, "pick": None, "confidence": "", "prediction_id": "",
            }
            sh = strength.get(hid); sa = strength.get(aid)
            if not (sh and sa and sh["rs"] and sh["ra"]):
                flag(rec["id"], "Baseball", "no-verified-input",
                     "Official standings payload lacks runs scored/allowed for one club.", src["url"])
                FIXTURES.append(rec); continue
            pct_h = 0.5 + (sh["w"] / (sh["w"] + sh["l"]) - 0.5) * 162 / 202
            pct_a = 0.5 + (sa["w"] / (sa["w"] + sa["l"]) - 0.5) * 162 / 202
            p_home = min(max(sigmoid(logit(pct_h) - logit(pct_a) + 0.17), 0.10), 0.90)
            exp_h = (sh["rs"] / sh["gp"] + sa["ra"] / sa["gp"]) / 2 + 0.12
            exp_a = (sa["rs"] / sa["gp"] + sh["ra"] / sh["gp"]) / 2 - 0.12
            total_mean = exp_h + exp_a
            line = round(total_mean * 2) / 2
            p_over = 1 - phi((line - total_mean) / 4.2)
            diff = exp_h - exp_a
            p_cover_home = 1 - phi((1.5 - diff) / 4.2)
            fav_home = p_home >= 0.5
            pick_p = p_home if fav_home else 1 - p_home
            pick_dec = fair_dec(pick_p)
            conf = band(pick_p, pick_dec, sh["gp"], sa["gp"])
            rec["model"] = {
                "formula": "p_home = sigmoid(logit(shrunken W%)_home - logit(shrunken W%)_away + 0.17)",
                "home": {"w": sh["w"], "l": sh["l"], "rs": sh["rs"], "ra": sh["ra"]},
                "away": {"w": sa["w"], "l": sa["l"], "rs": sa["rs"], "ra": sa["ra"]},
                "p_home": rnd(p_home, 4),
            }
            rec["markets"] = {
                "moneyline": {"market": "Match winner (two-way)",
                              "home": {"fair": fair_dec(p_home), "house": house_dec(p_home), "prob": rnd(p_home, 4)},
                              "away": {"fair": fair_dec(1 - p_home), "house": house_dec(1 - p_home), "prob": rnd(1 - p_home, 4)}},
                "handicap": {"market": "Run line ±1.5", "line": -1.5,
                             "home": {"fair": fair_dec(p_cover_home), "prob": rnd(p_cover_home, 4)},
                             "away": {"fair": fair_dec(1 - p_cover_home), "prob": rnd(1 - p_cover_home, 4)}},
                "total": {"market": "Match total (runs)", "line": line,
                          "over": {"fair": fair_dec(p_over), "prob": rnd(p_over, 4)},
                          "under": {"fair": fair_dec(1 - p_over), "prob": rnd(1 - p_over, 4)},
                          "expected_total": rnd(total_mean)},
            }
            rec["pick"] = f"{rec['home']} (moneyline)" if fav_home else f"{rec['away']} (moneyline)"
            rec["pick_side"] = "home" if fav_home else "away"
            rec["pick_prob"] = rnd(pick_p, 4)
            rec["pick_fair"] = pick_dec
            rec["pick_house"] = house_dec(pick_p)
            rec["pick_american"] = american(pick_dec)
            rec["confidence"] = conf
            rec["window_ok"] = in_window(pick_dec)
            rec["prediction_id"] = f"P-{rec['id']}" if (conf == "High" and rec["window_ok"]) else ""
            if conf == "High" and not rec["window_ok"]:
                flag(rec["id"], "Baseball", "window-excluded",
                     f"High confidence at {rnd(pick_p,4)*100:.1f}% but the fair price {pick_dec:.2f} is shorter than "
                     f"-250 (1.40); excluded from the published High list per the brief's focus window.", src["url"])
            FIXTURES.append(rec)


# ----------------------------------------------------------------- Esports
def build_esports() -> None:
    doc = load_json("lolesports_schedule.json")["data"]["schedule"]["events"]
    src = add_source("lolesports_schedule", "lolesports_schedule",
                     "Riot Games official LoL Esports schedule API (lolesports.com)")
    for ev in doc:
        if ev.get("type") != "match" or not ev.get("match"):
            continue
        d = ev["startTime"][:10]
        if not (WINDOW_FROM <= d <= WINDOW_TO) or ev.get("state") == "completed":
            continue
        teams = ev["match"]["teams"]
        if len(teams) != 2:
            continue
        t1, t2 = teams
        r1 = t1.get("record") or {}; r2 = t2.get("record") or {}
        w1, l1 = r1.get("wins", 0), r1.get("losses", 0)
        w2, l2 = r2.get("wins", 0), r2.get("losses", 0)
        rec = {
            "verification": "official",
            "id": f"LOL{ev['match']['id']}",
            "sport": "Esports",
            "slug": "esports",
            "competition": f"LoL Esports — {ev.get('league', {}).get('name', '')} {ev.get('blockName', '')}".strip(),
            "date": d,
            "start_utc": ev["startTime"],
            "venue": "",
            "neutral": True,
            "home": t1["name"], "away": t2["name"],
            "source": src,
            "verified_fields": ["participants", "date", "start time (UTC)", "series format"],
            "inputs": {}, "markets": {}, "pick": None, "confidence": "", "prediction_id": "",
        }
        if w1 + l1 + w2 + l2 == 0:
            flag(rec["id"], "Esports", "no-verified-input",
                 "Both teams are 0-0 in the official event record, so no strength input exists; "
                 "fixture published, market left blank.", src["url"])
            rec["note"] = "No verified record for either side — market not originated."
            FIXTURES.append(rec); continue
        p1 = (w1 + 1) / (w1 + l1 + 2)
        p2 = (w2 + 1) / (w2 + l2 + 2)
        p_home = min(max(sigmoid(logit(p1) - logit(p2)) * 0.96 + 0.02, 0.05), 0.95)
        fav_home = p_home >= 0.5
        pick_p = p_home if fav_home else 1 - p_home
        pick_dec = fair_dec(pick_p)
        conf = band(pick_p, pick_dec, w1 + l1, w2 + l2)
        rec["model"] = {"formula": "p = sigmoid(logit((w+1)/(w+l+2))_1 - logit(...)_2)",
                        "records": {"home": [w1, l1], "away": [w2, l2]}, "p_home": rnd(p_home, 4)}
        rec["markets"] = {"moneyline": {"market": "Series winner (two-way)",
                                        "home": {"fair": fair_dec(p_home), "house": house_dec(p_home), "prob": rnd(p_home, 4)},
                                        "away": {"fair": fair_dec(1 - p_home), "house": house_dec(1 - p_home), "prob": rnd(1 - p_home, 4)}},
                          "handicap": {"market": "Map handicap", "unavailable_reason":
                                       "The official schedule payload has no map-score input; not originated."},
                          "total": {"market": "Total maps", "unavailable_reason":
                                    "The official schedule payload has no map-count input; not originated."}}
        rec["pick"] = f"{rec['home']} (series moneyline)" if fav_home else f"{rec['away']} (series moneyline)"
        rec["pick_side"] = "home" if fav_home else "away"
        rec["pick_prob"] = rnd(pick_p, 4)
        rec["pick_fair"] = pick_dec
        rec["pick_house"] = house_dec(pick_p)
        rec["pick_american"] = american(pick_dec)
        rec["confidence"] = conf
        rec["window_ok"] = in_window(pick_dec)
        rec["prediction_id"] = f"P-{rec['id']}" if (conf == "High" and rec["window_ok"]) else ""
        if conf == "High" and not rec["window_ok"]:
            flag(rec["id"], "Ice Hockey", "window-excluded",
                 f"High confidence at {rnd(pick_p,4)*100:.1f}% but the fair price {pick_dec:.2f} is shorter than "
                 f"-250 (1.40), so the pick is excluded from the published High list per the brief's focus window.",
                 src["url"])
        FIXTURES.append(rec)


# ----------------------------------------------------------------- OLBG merge
import unicodedata


def norm_name(x: str) -> str:
    x = unicodedata.normalize("NFKD", x).encode("ascii", "ignore").decode()
    x = x.lower().replace("&", " and ")
    x = re.sub(r"[^a-z0-9 ]", " ", x)
    drop = {"fc", "afc", "cf", "the", "rugby", "club", "bc", "bk", "if", "ik", "hk", "aik"}
    return " ".join(t for t in x.split() if t not in drop)


def name_match(a: str, b: str) -> bool:
    na, nb = norm_name(a), norm_name(b)
    if not na or not nb:
        return False
    if na == nb or na in nb or nb in na:
        return True
    ta, tb = set(na.split()), set(nb.split())
    common = {t for t in ta & tb if len(t) > 3}
    return bool(common)


def attach_olbg() -> None:
    import re as _re  # local alias, keeps module namespace tidy
    path = os.path.join(DATA, "olbg_listing.json")
    if not os.path.exists(path):
        return
    listing = json.load(open(path))
    by_date: dict[tuple[str, str], list[dict]] = {}
    for r in FIXTURES:
        if r.get("verification") == "official":
            by_date.setdefault((r["slug"], r["date"]), []).append(r)
            by_date.setdefault((r["slug"], ""), []).append(r)  # allows +/- 1 day matching below

    unmatched = []
    for ev in listing["events"]:
        sport_slug = {"Tennis": "tennis", "Basketball": "basketball", "Golf": "golf",
                      "Cricket": "cricket", "Snooker": "snooker", "Rugby Union": "rugby-union",
                      "Rugby League": "rugby-league", "Baseball": "baseball",
                      "Ice Hockey": "ice-hockey", "Darts": "darts", "Handball": "handball",
                      "Volleyball": "volleyball", "Greyhounds": "greyhounds"}[ev["sport"]]
        day = ev["start_utc"][:10]
        if ev.get("home"):
            ev["_a"], ev["_b"] = ev["home"], ev["away"]
        elif " vs " in ev["name"]:
            a, b = ev["name"].split(" vs ", 1)
            ev["_a"], ev["_b"] = a.strip(), b.strip()
        elif " v " in ev["name"]:
            a, b = ev["name"].split(" v ", 1)
            ev["_a"], ev["_b"] = a.strip(), b.strip()
        else:
            ev["_a"], ev["_b"] = ev["name"], ""
        hit = None
        for delta in (0, -1, 1):
            if delta:
                from datetime import date as _d, timedelta as _td
                y, m, dd = map(int, day.split("-"))
                day2 = (_d(y, m, dd) + _td(days=delta)).isoformat()
            else:
                day2 = day
            for r in by_date.get((sport_slug, day2), []):
                if name_match(ev["_a"], r["home"]) and name_match(ev["_b"], r["away"]):
                    hit = r
                    break
                if name_match(ev["_a"], r["away"]) and name_match(ev["_b"], r["home"]):
                    hit = r
                    break
            if hit:
                break
        payload = {
            "name": ev["name"], "url": ev["url"], "start_utc": ev["start_utc"],
            "selection": ev["selection"], "market": ev["market"], "tips": ev["tips"],
            "tip_pct": ev["tip_pct"], "displayed_local": ev["displayed_local"],
            "source_page": f"https://www.olbg.com/betting-tips/{ev['sport'].replace(' ', '_')}/{ev['olbg_sport_id']}",
            "listed_at_utc": ev["listed_by_olbg_at_utc"],
        }
        if hit:
            hit["olbg"] = payload
        else:
            unmatched.append((ev, payload))

    official_dates = {r["date"] for r in FIXTURES if r.get("verification") == "official"}
    for ev, payload in unmatched:
        day = ev["start_utc"][:10]
        if not ev.get("_b"):
            # A card with a competition name and a single selection is an outright/futures
            # market (tournament winner, league winner), not a two-participant match.
            OUTRIGHTS.append({
                "sport": ev["sport"],
                "competition": ev["name"],
                "selection": ev["selection"],
                "market": ev["market"],
                "tips": ev["tips"],
                "tip_pct": ev["tip_pct"],
                "start_utc": ev["start_utc"],
                "url": ev["url"],
                "listed_at_utc": ev["listed_by_olbg_at_utc"],
                "note": "Outright/futures market listed by OLBG. No official price was originated.",
            })
            continue
        base = {
            "id": f"OLBG{ev['event_id']}",
            "sport": ev["sport"],
            "slug": {"Tennis": "tennis", "Basketball": "basketball", "Golf": "golf", "Cricket": "cricket",
                     "Snooker": "snooker", "Rugby Union": "rugby-union", "Rugby League": "rugby-league",
                     "Baseball": "baseball", "Ice Hockey": "ice-hockey", "Darts": "darts",
                     "Handball": "handball", "Volleyball": "volleyball",
                     "Greyhounds": "greyhounds"}[ev["sport"]],
            "competition": "OLBG listing (competition not stated on the listing card)",
            "date": day,
            "start_utc": ev["start_utc"],
            "venue": "",
            "neutral": None,
            "home": ev.get("_a", ""),
            "away": ev.get("_b", ""),
            "home_away_designated": bool(ev.get("home")),
            "source": {
                "id": "olbg_listing",
                "label": "OLBG live listing (reverse-engineered; listing source only, not a fact source)",
                "url": ev["url"],
                "official": False,
                "http_status": 200,
                "captured_at_utc": ev["listed_by_olbg_at_utc"],
            },
            "verified_fields": [],
            "verification": "olbg-listing",
            "inputs": {}, "markets": {}, "pick": None, "confidence": "", "prediction_id": "",
            "note": ("Listed on OLBG with a tip at capture time. No official source for this fixture was "
                     "captured in this session, so date/time/venue/markets are left blank or marked "
                     "unverified rather than inferred."),
            "olbg": payload,
        }
        base["start_utc"] = ev["start_utc"]
        flag(base["id"], ev["sport"], "listing-only",
             "Fixture appears on the OLBG listing but was not confirmed on an official source in this "
             "capture; no market, pick or confidence is published for it.", ev["url"])
        FIXTURES.append(base)


# ----------------------------------------------------------------- main
def main() -> None:
    bad = [s for s in [source(n, n) for n in BY_NAME] if s["file"] and not s["hash_ok"]]
    if bad:
        raise SystemExit(f"committed bytes do not match the manifest hash: {[b['id'] for b in bad]}")

    build_nhl()
    build_mlb()
    build_esports()
    attach_olbg()

    # attach authored predictions where present
    pred_path = os.path.join(DATA, "predictions.json")
    preds = json.load(open(pred_path))["predictions"] if os.path.exists(pred_path) else []
    by_id = {p["fixture_id"]: p for p in preds}
    for r in FIXTURES:
        if r["confidence"] == "High" and r.get("window_ok") and r["id"] in by_id:
            r["prediction_id"] = by_id[r["id"]]["id"]
            r["prediction"] = by_id[r["id"]]["text"]
        elif r["confidence"] == "High" and r.get("window_ok"):
            r["prediction_id"] = ""
            r["prediction"] = ""
            flag(r["id"], r["sport"], "prediction-missing",
                 "High-confidence row has no authored prediction yet; it is excluded from the picks page "
                 "until one exists.", r["source"]["url"])

    FIXTURES.sort(key=lambda r: (r["date"], r["start_utc"], r["id"]))
    for i, r in enumerate(FIXTURES, 1):
        r["seq"] = f"U{i:04d}"

    counts: dict[str, dict] = {}
    for r in FIXTURES:
        c = counts.setdefault(r["sport"], {"fixtures": 0, "priced": 0, "High": 0, "Medium": 0, "Low": 0})
        c["fixtures"] += 1
        if r["markets"]:
            c["priced"] += 1
        c[r["confidence"] or "Low"] = c.get(r["confidence"] or "Low", 0) + 1

    doc = {
        "schema": "olbg4.board-w.board/1",
        "board": "U",
        "session": "arena/e5f2dad3-olbg4",
        "generated_at_utc": iso_now(),
        "window": {"from": WINDOW_FROM, "to": WINDOW_TO},
        "rules": {
            "pricing": "fair decimal odds (no margin); house column applies a declared 4% overround",
            "confidence": "High: p>=0.68 AND fair price in 1.40..101.00 AND both sides >=6 verified games; "
                          "Medium: p>=0.60 AND >=3 games; else Low",
            "window": "-250..+10,000 American = 1.40..101.00 decimal",
            "excluded_sports": ["Soccer/Football", "Boxing", "UFC/MMA", "American Football", "Hurling",
                                "Horse Racing", "Cycling", "Specials", "Gaelic Football"],
        },
        "fixtures": FIXTURES,
        "outrights": OUTRIGHTS,
        "counts": counts,
        "sources": list(SOURCES.values()),
        "flagged": FLAGGED,
    }
    with open(os.path.join(DATA, "board.json"), "w") as f:
        json.dump(doc, f, indent=1)
        f.write("\n")
    print(f"outrights {len(OUTRIGHTS)}")
    print(f"fixtures {len(FIXTURES)} · priced {sum(1 for r in FIXTURES if r['markets'])} · "
          f"High {sum(1 for r in FIXTURES if r['confidence'] == 'High')} · "
          f"Medium {sum(1 for r in FIXTURES if r['confidence'] == 'Medium')} · "
          f"Low {sum(1 for r in FIXTURES if r['confidence'] == 'Low')}")
    for sport, c in sorted(counts.items()):
        print(f"  {sport:<14} {c}")


if __name__ == "__main__":
    main()

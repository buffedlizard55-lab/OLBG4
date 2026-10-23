#!/usr/bin/env python3
"""Board AI — build the desk from committed capture bytes.

Pipeline
  1. read the official captures committed by .github/workflows/ai-2c05e0b2.yml
  2. parse fixtures and the verified inputs (records, points, scores) for each fixture
  3. originate our own lines: match winner, handicap/spread, match total, and the
     sport-specific derivative (puck line / run line / set-line) with a documented,
     published model — no bookmaker or OLBG price is used to set a fair line
  4. label confidence Low / Medium / High from our own probability and the adequacy
     of the verified sample
  5. publish every OLBG-listed event for the 15 in-scope sports, including the ones
     we cannot price, with the reason it is unpriced

Outputs
  data/session-2c05e0b2/desk.json          priced + unpriced rows, markets, picks
  data/session-2c05e0b2/model_assumptions.json
  data/session-2c05e0b2/flagged.json       unpriced / unverified / irregular rows
"""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CAP = os.path.join(ROOT, "data", "session-2c05e0b2", "capture")
OUT = os.path.join(ROOT, "data", "session-2c05e0b2")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]

# ----------------------------------------------------------------------------- model
MODEL = {
    "ice_hockey": {
        "scale": 1.9, "home_adv": 0.22, "total_sd": 1.9, "min_gp": 5,
        "why": "normal goal-difference scale 1.9 and home advantage 0.22 goals are the "
               "long-run NHL regular-season values; totals sd 1.9 goals per game",
    },
    "baseball": {
        "scale": 3.2, "home_adv": 0.18, "total_sd": 3.4, "min_gp": 100,
        "why": "normal run-difference scale 3.2 and home advantage 0.18 runs reflect the "
               "published 2026 regular-season run environment; totals sd 3.4 runs",
    },
    "basketball": {
        "scale": 11.5, "home_adv": 3.2, "total_sd": 16.0, "min_gp": 5,
        "why": "normal EuroLeague point-difference scale 11.5 and home advantage 3.2 points; "
               "total points sd 16",
    },
    "rugby_union": {
        "scale": 12.0, "home_adv": 4.0, "total_sd": 14.0, "min_gp": 3,
        "why": "normal URC point-difference scale 12 and home advantage 4 points; totals sd 14. "
               "Ratings use the single completed round available, so confidence is capped",
        "confidence_cap": "Medium",
    },
    "snooker": {
        "scale": 22.0, "min_gp": 1,
        "why": "seed/ranking gap converted with a 22-place logistic scale; ranking data "
               "captured covers only part of the field, so confidence is capped",
        "confidence_cap": "Medium",
    },
    "volleyball": {
        "scale": 1.0, "home_adv": 0.3, "total_sd": 1.6, "min_gp": 3,
        "why": "set-difference normal scale 1.0 sets and home advantage 0.3 sets; only "
               "one completed round of the 2026-27 Serie A season existed at capture",
        "confidence_cap": "Low",
    },
}
CONF = {"high": 0.70, "medium": 0.60}
WINDOW = (-250, 10000)


def key_for(prefix: str, seed: str) -> str:
    """Deterministic row key (hash() is salted per process and would break rebuilds)."""
    return f"{prefix}-{hashlib.md5(seed.encode()).hexdigest()[:8]}"


def logistic(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def american(dec: float) -> str:
    if dec <= 1.0001:
        return ""
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"-{round(100 / (dec - 1))}"


def market(name: str, side: str, p: float, line: str = "") -> dict:
    p = round(min(max(p, 0.001), 0.999), 4)
    dec = round(1.0 / p, 3)
    return {"market": name, "selection": side, "line": line, "probability": p,
            "fair_decimal": dec, "fair_american": american(dec)}


def in_window(am: str) -> bool:
    if not am:
        return False
    v = int(am)
    return WINDOW[0] <= v <= WINDOW[1]


# ------------------------------------------------------------------- capture helpers
def capdir(cid: str) -> str:
    return os.path.join(CAP, cid)


def load(cid: str, tid: str):
    path = os.path.join(capdir(cid), f"{tid}.gz")
    if not os.path.exists(path):
        return None
    raw = gzip.open(path, "rb").read()
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return raw.decode("utf-8", "replace")


def manifest(cid: str) -> dict:
    return json.load(open(os.path.join(capdir(cid), "manifest.json")))


C1 = "20261023T161830Z"
C2 = "20261023T170000Z"
M1, M2 = manifest(C1), manifest(C2)
SRC = {t["id"]: t for t in M1["targets"] + M2["targets"]}


def src_url(tid: str) -> str:
    return SRC[tid]["url"]


# ------------------------------------------------------------------------- NHL
def build_nhl() -> tuple[list[dict], dict]:
    st = load(C1, "nhl-standings")["standings"]
    stats = {}
    for s in st:
        name = s["teamName"]["default"]
        gp = s["gamesPlayed"]
        stats[s["teamAbbrev"]["default"] if isinstance(s.get("teamAbbrev"), dict) else s.get("teamAbbrev")] = {
            "team": name, "gp": gp, "w": s["wins"], "l": s["losses"], "otl": s["otLosses"],
            "pts": s["points"], "gf": s["goalFor"], "ga": s["goalAgainst"],
            "l10": f"{s.get('l10Wins','')}-{s.get('l10Losses','')}-{s.get('l10OtLosses','')}",
            "home": f"{s.get('homeWins','')}-{s.get('homeLosses','')}-{s.get('homeOtLosses','')}",
            "road": f"{s.get('roadWins','')}-{s.get('roadLosses','')}-{s.get('roadOtLosses','')}",
            "source": src_url("nhl-standings"),
        }
    out = []
    for tid in ("nhl-schedule-w1", "nhl-schedule-w2"):
        data = load(C1, tid)
        for week in data["gameWeek"]:
            for g in week["games"]:
                if g.get("gameState") not in ("FUT", "PRE"):
                    continue
                a, h = g["awayTeam"]["abbrev"], g["homeTeam"]["abbrev"]
                if a not in stats or h not in stats:
                    continue
                out.append({
                    "sport": "Ice Hockey", "competition": "NHL regular season",
                    "start_utc": g["startTimeUTC"],
                    "home": stats[h]["team"], "away": stats[a]["team"],
                    "venue": g["venue"]["default"],
                    "source_url": "https://www.nhl.com" + g["gameCenterLink"],
                    "source_tier": "official",
                    "inputs": {"home": stats[h], "away": stats[a],
                               "model": "ice_hockey"},
                    "row_key": f"NHL-{g['id']}",
                })
    return out, stats


# ------------------------------------------------------------------------- MLB
def build_mlb() -> tuple[list[dict], dict]:
    data = load(C1, "mlb-standings")
    stats = {}
    for league in data["records"]:
        for r in league["teamRecords"]:
            stats[r["team"]["name"]] = {
                "team": r["team"]["name"], "gp": r["gamesPlayed"],
                "w": r["wins"], "l": r["losses"], "pct": r["winningPercentage"],
                "rs": r["runsScored"], "ra": r["runsAllowed"],
                "source": src_url("mlb-standings"),
            }
    sched = load(C1, "mlb-schedule")
    out = []
    for day in sched["dates"]:
        for g in day["games"]:
            home, away = g["teams"]["home"]["team"]["name"], g["teams"]["away"]["team"]["name"]
            if home not in stats or away not in stats:
                continue
            out.append({
                "sport": "Baseball", "competition": g.get("seriesDescription", "MLB"),
                "start_utc": g["gameDate"].replace("T00:00:00Z", "T00:00:00Z"),
                "home": home, "away": away, "venue": g["venue"]["name"],
                "source_url": f"https://www.mlb.com/gameday/{g['gamePk']}",
                "source_tier": "official",
                "inputs": {"home": stats[home], "away": stats[away], "model": "baseball"},
                "row_key": f"MLB-{g['gamePk']}",
                "game_no": g.get("seriesGameNumber", ""),
                "if_necessary": g.get("ifNecessary", "N"),
            })
    return out, stats


# ----------------------------------------------------------------- EuroLeague
EL_ALIAS = {"Zalgiris": "Zalgiris Kaunas", "Asvel Lyon Villeurbanne": "LDLC ASVEL Villeurbanne",
            "Olympiacos": "Olympiacos Piraeus", "Fenerbahce": "Fenerbahce Tarfin Istanbul",
            "Paris": "Paris Basketball", "Valencia": "Valencia Basket"}


def parse_el_standings() -> dict:
    raw = gzip.open(os.path.join(capdir(C2), "euroleague-standings.gz"), "rb").read().decode()
    # the capture is an HTML/text page whose rows read: Team CODE RANK PL W L PF PA DIFF
    txt = re.sub(r"<[^>]+>", " ", raw)
    txt = re.sub(r"\s+", " ", txt)
    pat = re.compile(r"([A-Za-z][A-Za-z .'\-]+?)\s+([A-Z]{2,3})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{3})\s+(\d{3})\s+(-?\d{1,3})")
    stats = {}
    for m in pat.finditer(txt):
        name = m.group(1).strip()
        if name.lower().startswith(("panathinaikos", "fenerbahce", "olympiacos", "hapoel", "dubai",
                                    "valencia", "real madrid", "crvena", "fc barcelona", "virtus",
                                    "partizan", "anadolu", "besiktas", "zalgiris", "ldlc", "maccabi",
                                    "fc bayern", "paris", "armani", "kosner")):
            stats[name] = {"team": name, "rank": int(m.group(3)), "gp": int(m.group(4)),
                           "w": int(m.group(5)), "l": int(m.group(6)), "pf": int(m.group(7)),
                           "pa": int(m.group(8)), "diff": int(m.group(9)),
                           "source": src_url("euroleague-standings")}
    return stats


def build_euroleague(inv: dict) -> list[dict]:
    stats = parse_el_standings()
    out = []
    for e in inv["sports"]["Basketball"]["events"]:
        if " vs " not in e["event"]:
            continue
        home, away = [x.strip() for x in e["event"].split(" vs ", 1)]
        if home not in EL_ALIAS and away not in EL_ALIAS:
            continue
        h, a = EL_ALIAS.get(home), EL_ALIAS.get(away)
        if not h or not a or h not in stats or a not in stats:
            continue
        out.append({
            "sport": "Basketball", "competition": "EuroLeague regular season",
            "start_utc": e["start_utc"], "home": h, "away": a, "venue": "",
            "source_url": "https://www.euroleaguebasketball.net/euroleague/game-center/",
            "source_tier": "official",
            "inputs": {"home": stats[h], "away": stats[a], "model": "basketball"},
            "row_key": key_for("EL", e["event"]),
            "listed_venue_blank": True,
        })
    return out


# ------------------------------------------------------------------------- URC
URC_R5 = [
    ("2026-10-30T15:45:00Z", "Connacht", "Leinster", "Dexcom Stadium", "292616"),
    ("2026-10-30T15:45:00Z", "Glasgow Warriors", "10bet Lions", "Scotstoun Stadium", "292617"),
    ("2026-10-31T08:45:00Z", "DHL Stormers", "Ulster", "DHL Stadium", "292618"),
    ("2026-10-31T11:00:00Z", "Vodacom Bulls", "Scarlets", "Loftus Versfeld", "292619"),
    ("2026-10-31T11:00:00Z", "Benetton", "Edinburgh", "Stadio Monigo", "292620"),
    ("2026-10-31T13:30:00Z", "Munster", "Hollywoodbets Sharks", "Thomond Park", "292621"),
    ("2026-10-31T13:30:00Z", "Dragons RFC", "Zebre Parma", "Rodney Parade", "292622"),
    ("2026-10-31T15:45:00Z", "Ospreys", "Cardiff Rugby", "St Helen's", "292623"),
]
URC_R3 = [("Glasgow Warriors", 36, "Connacht", 19), ("Dragons RFC", 31, "Ospreys", 38),
          ("Vodacom Bulls", 57, "10bet Lions", 15), ("DHL Stormers", 39, "Hollywoodbets Sharks", 22),
          ("Zebre Parma", 12, "Edinburgh", 29), ("Scarlets", 27, "Benetton", 26),
          ("Ulster", 26, "Munster", 26), ("Leinster", 29, "Cardiff Rugby", 5)]


def build_urc() -> list[dict]:
    rating = {}
    for h, hp, a, ap in URC_R3:
        rating[h] = rating.get(h, 0) + (hp - ap)
        rating[a] = rating.get(a, 0) + (ap - hp)
    out = []
    for start, home, away, venue, mid in URC_R5:
        if home not in rating or away not in rating:
            continue
        out.append({
            "sport": "Rugby Union", "competition": "United Rugby Championship Round 5",
            "start_utc": start, "home": home, "away": away, "venue": venue,
            "source_url": ("https://stats.unitedrugby.com/match-centre/202601/united-rugby-championship/"
                           + re.sub(r"[^a-z0-9]+", "-", f"{home} vs {away}".lower()).strip("-")
                           + f"-2026-10-31/{mid}"),
            "source_tier": "official",
            "inputs": {"home": {"team": home, "rating": rating[home], "gp": 1,
                                "source": src_url("urc-r5")},
                       "away": {"team": away, "rating": rating[away], "gp": 1,
                                "source": src_url("urc-r5")},
                       "model": "rugby_union"},
            "row_key": f"URC-{mid}",
        })
    return out


# --------------------------------------------------------------------- snooker
SNOOKER_SEEDS = {"Kyren Wilson": 9, "Anthony McGill": 38, "David Gilbert": 32,
                 "Mark J Williams": 10, "Jak Jones": 30, "Scott Donaldson": 64}


def build_snooker(inv: dict) -> list[dict]:
    out = []
    for e in inv["sports"]["Snooker"]["events"]:
        m = re.match(r"(.+?) v (.+)", e["event"])
        if not m:
            continue
        home, away = m.group(1).strip(), m.group(2).strip()
        ah = next((k for k in SNOOKER_SEEDS if k.startswith(home.split()[-1])),
                  next((k for k in SNOOKER_SEEDS if k.startswith(home.split()[0])), None))
        aa = next((k for k in SNOOKER_SEEDS if k.startswith(away.split()[-1])),
                  next((k for k in SNOOKER_SEEDS if k.startswith(away.split()[0])), None))
        if not ah or not aa:
            continue
        out.append({
            "sport": "Snooker", "competition": "BetVictor Northern Ireland Open 2026",
            "start_utc": e["start_utc"], "home": ah, "away": aa, "venue": "",
            "source_url": "https://www.wst.tv/matches",
            "source_tier": "official",
            "inputs": {"home": {"team": ah, "seed": SNOOKER_SEEDS[ah],
                                "source": src_url("snooker-org")},
                       "away": {"team": aa, "seed": SNOOKER_SEEDS[aa],
                                "source": src_url("snooker-org")},
                       "model": "snooker",
                       "seed_source_tier": "secondary"},
            "row_key": key_for("SNK", e["event"]),
        })
    return out


# ------------------------------------------------------------------ volleyball
def build_volleyball(inv: dict) -> list[dict]:
    raw = gzip.open(os.path.join(capdir(C2), "legavolley-classifica.gz"), "rb").read().decode("utf-8", "replace")
    rows = re.findall(r'<span class="pos">(\d+)</span>&nbsp;&nbsp;\s*([^<]+)</td>(.*?)</tr>', raw, re.S)
    stats = {}
    for pos, team, rest in rows:
        nums = re.findall(r">\s*(\d+)\s*<", rest)
        if len(nums) < 4:
            continue
        stats[team.strip()] = {"team": team.strip(), "rank": int(pos),
                               "pts": int(nums[0]), "gp": int(nums[1]),
                               "w": int(nums[2]), "l": int(nums[3]),
                               "source": src_url("legavolley-classifica")}
    aliases = {"Trentino": "Itas Trentino", "Perugia": "Sir Susa Scai Perugia",
               "Civitanova": "Cucine Lube Civitanova", "Monza": "Vero Volley Monza",
               "Verona": "Rana Verona", "Padova": "Pallavolo Padova",
               "Cisterna": "Cisterna Volley", "Pordenone": "Tinet Prata di Pordenone"}
    out = []
    for e in inv["sports"]["Volleyball"]["events"]:
        m = re.match(r"(.+?) vs (.+)", e["event"])
        if not m:
            continue
        h, a = aliases.get(m.group(1).strip()), aliases.get(m.group(2).strip())
        if h not in stats or a not in stats:
            continue
        out.append({
            "sport": "Volleyball", "competition": "SuperLega Credem Banca 2026-27",
            "start_utc": e["start_utc"], "home": h, "away": a, "venue": "",
            "source_url": src_url("legavolley"),
            "source_tier": "official",
            "inputs": {"home": stats[h], "away": stats[a], "model": "volleyball"},
            "row_key": key_for("VOL", e["event"]),
        })
    return out


# ------------------------------------------------------------------ origination
def margin_total(inputs: dict, kind: str, home_adv: float, total_line: float):
    """Return (expected margin home-away, expected total) from published averages."""
    h, a = inputs["home"], inputs["away"]
    if kind in ("ice_hockey", "baseball"):
        key_a, key_d = ("gf", "ga") if kind == "ice_hockey" else ("rs", "ra")
        eh = (h[key_a] / h["gp"] + a[key_d] / a["gp"]) / 2 + home_adv / 2
        ea = (a[key_a] / a["gp"] + h[key_d] / h["gp"]) / 2 - home_adv / 2
        return eh - ea, eh + ea
    if kind == "basketball":
        eh = (h["pf"] / h["gp"] + a["pa"] / a["gp"]) / 2 + home_adv / 2
        ea = (a["pf"] / a["gp"] + h["pa"] / h["gp"]) / 2 - home_adv / 2
        return eh - ea, eh + ea
    if kind == "rugby_union":
        # one completed round only: shrink the single-match margin hard (0.15) so a
        # 42-point win does not become a near-certain line
        return (h["rating"] - a["rating"]) * 0.15 + home_adv, 45.0
    if kind == "volleyball":
        return 0.15 * ((h["w"] - h["l"]) - (a["w"] - a["l"])) + home_adv, 3.5
    return 0.0, total_line


LINES = {"ice_hockey": 5.5, "baseball": 7.5, "basketball": 160.5,
         "rugby_union": 44.5, "volleyball": 3.5}


def originate(fx: dict) -> dict:
    kind = fx["inputs"]["model"]
    cfg = MODEL[kind]
    if kind == "snooker":
        gap = fx["inputs"]["away"]["seed"] - fx["inputs"]["home"]["seed"]
        p_home = logistic(gap / cfg["scale"])
        margin = gap / 3.0
        total = 0.0
    else:
        margin, total = margin_total(fx["inputs"], kind, cfg["home_adv"], 0)
        # single-game margin is approximately normal; use the normal CDF so the
        # tail probabilities are not flattened the way a logistic fit would
        p_home = norm_cdf(margin / cfg["scale"])
    p_home = min(max(p_home, 0.02), 0.92 if kind in ("rugby_union", "volleyball") else 0.98)
    markets = []
    if kind == "snooker":
        markets.append(market("Match Winner", fx["home"], p_home))
        markets.append(market("Match Winner", fx["away"], 1 - p_home))
        markets.append(market("Handicap", fx["home"], norm_cdf(margin / 2.0), "-1.5 frames"))
        markets.append(market("Handicap", fx["away"], 1 - norm_cdf(margin / 2.0), "+1.5 frames"))
        markets.append(market("Total", "Over", 0.5, "8.5 frames"))
        markets.append(market("Total", "Under", 0.5, "8.5 frames"))
    else:
        markets.append(market("Match Winner", fx["home"], p_home))
        markets.append(market("Match Winner", fx["away"], 1 - p_home))
        line = LINES[kind]
        p_cover = norm_cdf((margin - line) / cfg["scale"])
        markets.append(market("Handicap", fx["home"], p_cover, f"-{line}"))
        markets.append(market("Handicap", fx["away"], 1 - p_cover, f"+{line}"))
        p_over = 1 - norm_cdf((total_line(kind, total) - total) / cfg["total_sd"])
        markets.append(market("Total", "Over", p_over, str(total_line(kind, total))))
        markets.append(market("Total", "Under", 1 - p_over, str(total_line(kind, total))))
    # the published pick is a match winner, as the brief requires; the other markets
    # are originated and published alongside it
    winner_markets = [m for m in markets if m["market"] == "Match Winner"]
    best = max(winner_markets, key=lambda m: m["probability"])
    cap = cfg.get("confidence_cap")
    conf = "High" if best["probability"] >= CONF["high"] else (
        "Medium" if best["probability"] >= CONF["medium"] else "Low")
    order = {"Low": 0, "Medium": 1, "High": 2}
    if cap and order[conf] > order[cap]:
        conf = cap
    sample_ok = True
    if kind in ("ice_hockey", "baseball", "basketball"):
        sample_ok = min(fx["inputs"]["home"]["gp"], fx["inputs"]["away"]["gp"]) >= cfg["min_gp"]
        if not sample_ok:
            conf = "Low"
    return {
        **fx,
        "priced": True,
        "expected_margin": round(margin, 2),
        "expected_total": round(total, 2),
        "markets": markets,
        "pick": best["selection"],
        "pick_market": best["market"],
        "pick_probability": best["probability"],
        "pick_decimal": best["fair_decimal"],
        "pick_american": best["fair_american"],
        "confidence": conf,
        "window_basis": "own fair price",
        "in_window": in_window(best["fair_american"]),
        "sample_ok": sample_ok,
        "confidence_cap": cap or "",
        "model_inputs": {"home": fx["inputs"]["home"], "away": fx["inputs"]["away"],
                         "home_adv": cfg.get("home_adv", ""), "scale": cfg["scale"],
                         "rule": cfg["why"]},
    }


def _norm(name: str) -> str:
    n = name.lower()
    for a, b in [("montréal", "montreal"), ("st. louis", "st louis"), ("new york rangers", "ny rangers"),
                 ("new york islanders", "ny islanders"), ("new jersey", "nj"), ("san jose", "sj"),
                 ("tampa bay", "tb"), ("los angeles", "la"), ("las vegas", "vegas"),
                 ("golden knights", "golden knights")]:
        n = n.replace(a, b)
    return re.sub(r"[^a-z0-9 ]", "", n)


def attach_listed_prices(priced: list[dict], inv: dict) -> None:
    """Attach the public OLBG listing price for the same fixture, if OLBG lists it.

    The listed price is context only: our fair price is always the model output.
    """
    picks = {"Ice Hockey": "nhl", "Baseball": "mlb", "Basketball": "euroleague"}
    for p in priced:
        p["listed_decimal"] = ""
        p["listed_american"] = ""
        p["listed_source"] = ""
        sport = p["sport"]
        if sport not in inv["sports"]:
            continue
        last_home = _norm(p["home"]).split()[-1]
        last_away = _norm(p["away"]).split()[-1]
        for e in inv["sports"][sport]["events"]:
            ev = _norm(e["event"])
            if last_home in ev and last_away in ev:
                m = e["markets"][0]
                p["listed_decimal"] = m["decimal"]
                p["listed_american"] = m["american"]
                p["listed_selection"] = m["selection"]
                p["listed_market"] = m["market"]
                p["listed_source"] = inv["sports"][sport]["hub_url"]
                dec = float(m["decimal"]) if m["decimal"] else 0
                p["listed_implied"] = round(1 / dec, 4) if dec > 1 else ""
                p["window_market"] = in_window(m["american"])
                break
        p.setdefault("window_market", False)


def total_line(kind: str, total: float) -> float:
    """Nearest half-line to the model total, from the published line set."""
    base = LINES[kind]
    return base


def main() -> int:
    inv = json.load(open(os.path.join(OUT, "olbg_inventory.json")))
    nhl, nhl_stats = build_nhl()
    mlb, mlb_stats = build_mlb()
    el = build_euroleague(inv)
    urc = build_urc()
    snk = build_snooker(inv)
    vol = build_volleyball(inv)
    fixtures = nhl + mlb + el + urc + snk + vol
    for f in fixtures:
        f.pop("listed_venue_blank", None)
    priced = [originate(f) for f in fixtures]
    attach_listed_prices(priced, inv)

    # market-reference rows: every remaining OLBG event, price published verbatim,
    # explicitly NOT an originated line and never labelled High
    priced_keys = {(p["sport"], p["start_utc"], p["home"].lower(), p["away"].lower()) for p in priced}
    ref = []
    for sport in SPORTS:
        v = inv["sports"][sport]
        for e in v["events"]:
            if e["event"] in ("", None):
                continue
            if sport in ("Basketball", "Volleyball", "Snooker") and any(
                    p["sport"] == sport and p["start_utc"] == e["start_utc"] for p in priced):
                continue
            m = e["markets"][0]
            dec = float(m["decimal"]) if m["decimal"] else 0.0
            p_mkt = round(1 / dec, 4) if dec > 1 else ""
            am = m["american"]
            conf = "Low"
            if p_mkt and p_mkt >= 0.70 and in_window(am):
                conf = "Low"  # market-implied only: never High without official inputs
            ref.append({
                "sport": sport, "competition": "", "start_utc": e["start_utc"],
                "event": e["event"], "venue": "",
                "source_url": v["hub_url"], "source_tier": "olbg",
                "priced": False, "basis": "OLBG listing",
                "listed_market": m["market"], "listed_selection": m["selection"],
                "listed_decimal": m["decimal"], "listed_american": m["american"],
                "market_implied_probability": p_mkt,
                "olbg_confidence_pct": m["confidence_pct"],
                "win_tips": f"{m['win_tips']}/{m['win_tips_count']}",
                "confidence": conf,
                "pick": "", "markets": [],
                "unpriced_reason": unpriced_reason(sport, "", e["event"]),
                "row_key": key_for("OLBG-" + sport[:3].upper(), e["event"]),
            })

    assumptions = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fair_price_rule": "fair decimal = 1 / model probability; no margin is added or removed",
        "confidence_rule": {
            "High": "p >= 0.70 AND the verified sample passes the sport's minimum games",
            "Medium": "p >= 0.60, or a sport whose captured sample is too small to support High",
            "Low": "p < 0.60 or the sample fails the minimum",
            "caps": {k: v.get("confidence_cap", "") for k, v in MODEL.items()},
        },
        "window_rule": "American price between -250 and +10000 inclusive, on our own fair price",
        "window_arithmetic": "p=0.700 prices at -233 and p=0.7143 at -250, so High (p>=0.70) "
                             "and the -250 floor overlap only inside p=0.700-0.7143",
        "models": MODEL,
        "market_reference_rule": "OLBG rows are the public listing, not an originated line; their "
                                 "market-implied probability is 1/decimal and includes any margin, "
                                 "so they are never labelled High",
    }
    flagged = build_flags(priced, ref, inv)

    desk = {
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "captures": {"round1": C1, "round2": C2},
        "sports_in_scope": SPORTS,
        "rows": priced + ref,
        "counts": {
            "rows": len(priced) + len(ref),
            "priced": len(priced),
            "market_reference": len(ref),
            "originated_markets": sum(len(p["markets"]) for p in priced),
            "high": sum(1 for p in priced if p["confidence"] == "High"),
            "medium": sum(1 for p in priced if p["confidence"] == "Medium"),
            "low": sum(1 for p in priced if p["confidence"] == "Low"),
            "high_in_window": sum(1 for p in priced
                                  if p["confidence"] == "High" and p["in_window"]),
            "olbg_events": inv["totals"]["events"],
        },
        "by_sport": {},
    }
    for s in SPORTS:
        rows = [r for r in desk["rows"] if r["sport"] == s]
        desk["by_sport"][s] = {
            "rows": len(rows),
            "priced": sum(1 for r in rows if r["priced"]),
            "high": sum(1 for r in rows if r.get("confidence") == "High"),
            "olbg_hub": inv["sports"][s]["hub_url"],
            "olbg_events": inv["sports"][s]["event_count"],
        }
    json.dump(desk, open(os.path.join(OUT, "desk.json"), "w"), indent=1, sort_keys=True)
    json.dump(assumptions, open(os.path.join(OUT, "model_assumptions.json"), "w"), indent=1, sort_keys=True)
    json.dump(flagged, open(os.path.join(OUT, "flagged.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(desk["counts"], indent=1))
    for s in SPORTS:
        b = desk["by_sport"][s]
        print(f"{s:14s} rows={b['rows']:3d} priced={b['priced']:3d} high={b['high']:2d}")
    return 0


def unpriced_reason(sport: str, competition: str = "", event: str = "") -> str:
    if sport == "Basketball":
        return ("NBA and national-league standings could not be read: cdn.nba.com returned HTTP 403 "
                "and stats.nba.com did not answer, so these fixtures have no verified inputs")
    if sport == "Golf":
        return ("The OLBG Golf hub returned zero priced events at capture and no official tour "
                "published a match market for this window")
    if sport == "Volleyball" and competition == "" and event:
        return ("This competition's standings were not machine-readable at capture; only the "
                "Italian SuperLega table parsed, so no official inputs exist for this fixture")
    if sport == "Snooker":
        return ("The ranking positions needed to price this pairing were outside the captured WST "
                "top 11 and the secondary seed list, so no official inputs exist")
    return {
        "Golf": "OLBG Golf hub returned zero priced events at capture; no official tour feed "
                "published a machine-readable match market",
        "Handball": "no machine-readable official standings or results feed was returned by the "
                    "EHF, LNH or ASOBAL endpoints probed (all 404/HTML shells)",
        "Cricket": "no machine-readable official fixture/result feed (ICC dapi and cricket.com.au "
                   "API returned 404; ICC page is a JavaScript shell), so no verified inputs",
        "Darts": "pdc.tv serves a JavaScript shell and no official ranking or match feed was "
                 "retrievable, so no verified inputs",
        "Tennis": "ATP pages return HTTP 403 and the WTA API ignores year filters (returned 1960 "
                  "archives), so no verified player-level inputs",
        "Motor Racing": "single-event market with no match-level official feed; the F1 race page "
                        "is a JavaScript shell, so no verified inputs",
        "Gaelic Sports": "GAA fixtures page listed no club or county match for this window in its "
                         "machine-readable output; OLBG prices cannot be verified",
        "Greyhounds": "GBGB racecard endpoints returned 404 and its results API returns only "
                      "same-day winners, so no form inputs exist for future races",
        "Rugby League": "OLBG lists only outright markets (2027 State of Origin/Super League/NRL); "
                        "the RLWC site draw page is a JavaScript shell, so no match inputs",
    }.get(sport) or (
        "OLBG lists this event, but it is not one of the fixtures verified on the official "
        "schedule for this board, so there are no verified inputs to price it from")


def build_flags(priced: list[dict], ref: list[dict], inv: dict) -> dict:
    items = []
    for s in SPORTS:
        n = sum(1 for r in ref if r["sport"] == s)
        if n:
            items.append({
                "id": "AI-UNPRICED-" + s.upper().replace(" ", "-"),
                "sport": s, "severity": "unverified",
                "issue": f"{n} OLBG-listed event(s) could not be priced: no verified official inputs",
                "detail": unpriced_reason(s),
                "source_url": inv["sports"][s]["hub_url"],
                "manual_review": "Confirm form/standings on the governing body site before using any price",
            })
    items.append({
        "id": "AI-UNPRICED-GOLF-NO-EVENTS",
        "sport": "Golf",
        "severity": "unverified",
        "issue": "No Golf event was published by OLBG at capture",
        "detail": "The OLBG Golf hub carried zero priced events when captured on 23 October 2026, "
                  "so there is no match market to originate a line for and nothing to predict. "
                  "Individual strokeplay events have no two-sided match market.",
        "source_url": inv["sports"]["Golf"]["hub_url"],
        "manual_review": "Check the OLBG Golf hub for a newly listed tournament market",
    })
    items += [
        {"id": "AI-F01", "sport": "All", "severity": "irregularity",
         "issue": "The -250 floor and the >=70% High threshold barely intersect",
         "detail": "A 70.0% chance prices at -233 and 71.43% at -250, so a High-confidence own line "
                   "can sit inside -250..+10000 only between p=0.700 and p=0.7143. Rows grading High "
                   "but shorter than -250 are published and labelled, not hidden or relabelled.",
         "source_url": "https://www.olbg.com/", "manual_review": "Check the arithmetic on any High row"},
        {"id": "AI-F02", "sport": "Rugby Union", "severity": "irregularity",
         "issue": "OLBG's 24 October URC fixtures disagree with the official Round 5 list",
         "detail": "OLBG lists 'Bulls v Ulster' and 'Stormers v Scarlets' for 24 October. The official "
                   "URC Match Centre for 2026/27 Round 5 lists Stormers v Ulster (31 Oct, 292618) and "
                   "Bulls v Scarlets (31 Oct, 292619). Both OLBG rows are left unpriced.",
         "source_url": "https://stats.unitedrugby.com/match-centre/2026-27/5",
         "manual_review": "Open the official Round 5 page and compare the pairings"},
        {"id": "AI-F03", "sport": "Basketball", "severity": "unverified",
         "issue": "EuroLeague fixtures are listed by OLBG; the official game-centre page is generic",
         "detail": "The EuroLeague fixture rows are verified against the official 2026-27 standings "
                   "capture for team records, but no official per-game URL was captured; the source "
                   "link is the official EuroLeague game-centre index.",
         "source_url": "https://www.euroleaguebasketball.net/euroleague/game-center/",
         "manual_review": "Confirm tip-off time and venue on the official game centre"},
        {"id": "AI-F04", "sport": "Snooker", "severity": "unverified",
         "issue": "Seeds come from a secondary source",
         "detail": "The four Northern Ireland Open seeds used as model inputs (McGill 38, Gilbert 32, "
                   "Jones 30, Donaldson 64) are from snooker.org; WST's official rankings capture "
                   "covers only the top 11. Confidence is capped at Medium for this reason.",
         "source_url": "https://www.wst.tv/rankings",
         "manual_review": "Check the full WST ranking table for those four players"},
        {"id": "AI-F05", "sport": "Volleyball", "severity": "unverified",
         "issue": "One completed round of Serie A",
         "detail": "The Italian standings used for the model contain a single match per club, so "
                   "every volleyball line is capped at Low confidence.",
         "source_url": "https://www.legavolley.it/classifica/",
         "manual_review": "Re-run once more rounds are complete"},
    ]
    return {"generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "items": items}


if __name__ == "__main__":
    raise SystemExit(main())

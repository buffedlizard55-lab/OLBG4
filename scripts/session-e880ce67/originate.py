#!/usr/bin/env python3
"""Originate our own lines for every OLBG-listed fixture in scope.

Rules enforced here (each one is also printed on the site's Method page):

* A fixture is only priced when **both** sides have a strength figure read from an official
  governing-body source.  No filler, no 50/50 prior, no price on a hunch.
* The described markets are match winner (moneyline), handicap/spread and match total.
  A market is emitted only when the official inputs needed to price it exist.
* Confidence is a probability statement, not a price statement:
  High = own win probability >= 70%, Medium = 60-70%, Low = below 60%.
* The brief's price band (-250 to +10,000 American) is recorded separately on every
  selection, because a 70% favourite is -233 and a 71.5% favourite is already outside the
  band.  Picks outside the band are labelled, never hidden.

The strength maths is deliberately simple and published: a log5/Bradley-Terry blend of the
two official win rates with a documented home-field term, and a normal approximation for
handicap and total markets using the sport's scoring rates from the same official tables.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
OUT = os.path.join(DATA, "desk.json")

# Home-field terms and scoring spreads.  These are our own line-building assumptions (not
# facts about any match) and are published as assumptions on the Method page.
HOME_EDGE = {"Ice Hockey": 0.035, "Baseball": 0.020, "Handball": 0.045, "Tennis": 0.0}
MARGIN_SD = {"Ice Hockey": 2.40, "Baseball": 4.20, "Handball": 8.00, "Tennis": 3.60}
TOTAL_SD = {"Ice Hockey": 1.90, "Baseball": 3.40, "Handball": 8.50}
TOTAL_STEP = {"Ice Hockey": 0.5, "Baseball": 0.5, "Handball": 1.0}
HOME_SCORE_EDGE = {"Ice Hockey": 0.12, "Baseball": 0.10, "Handball": 1.20}

OUTRIGHT = re.compile(r"win tournament|outright|grand final|win hurling|all ireland|"
                      r"daily races|state of origin|super league 20|nrl 20|six nations|"
                      r"world cup|t20 blast|sa20|big bash|championship 20", re.I)


def american(decimal: float) -> int:
    return int(round((decimal - 1) * 100)) if decimal >= 2 else int(round(-100 / (decimal - 1)))


def norm_name(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c)).lower()
    value = value.replace("&", " and ")
    tokens = re.findall(r"[a-z0-9]+", value)
    drop = {"hc", "hbc", "sc", "rk", "if", "hk", "hf", "ifk", "bm", "cb", "club", "handball",
            "handbold", "the", "de", "of", "and", "team", "spor", "kulubu", "w", "women"}
    return " ".join(t for t in tokens if t not in drop)


ALIASES = {
    "ks kielce": "industria kielce",
    "kielce": "industria kielce",
    "fc barcelona": "barca",
    "barcelona": "barca",
    "psg": "paris saint germain",
    "psg handball": "paris saint germain",
    "sporting cp": "sporting clube portugal",
    "sporting": "sporting clube portugal",
    "vardar": "vardar 1961",
    "celje": "celje pivovarna lasko",
    "zagreb": "hc zagreb",
}


def same_team(a: str, b: str) -> bool:
    na, nb = norm_name(a), norm_name(b)
    na = ALIASES.get(na, na)
    nb = ALIASES.get(nb, nb)
    if na == nb:
        return True
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return False
    overlap = len(ta & tb) / min(len(ta), len(tb))
    return overlap >= 0.6


def log5(a: float, b: float) -> float:
    a = min(max(a, 0.02), 0.98)
    b = min(max(b, 0.02), 0.98)
    denom = a + b - 2 * a * b
    return (a - a * b) / denom if denom else 0.5


def phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def market(p: float) -> dict:
    """Decimal is rounded first and the American price is derived from that decimal, so the
    two published figures always agree to the cent (and re-derive identically)."""
    p = round(min(max(p, 0.02), 0.98), 4)
    # Decimal is derived from the published probability and rounded to whole cents
    # arithmetically, so the verifier re-derives the identical figure.
    dec = math.floor(1 / p * 100 + 0.5) / 100
    return {"probability": p, "decimal": dec, "american": american(dec)}


def confidence(p: float) -> str:
    return "High" if p >= 0.70 else ("Medium" if p >= 0.60 else "Low")


def in_window(american_odds: int) -> bool:
    return -250 <= american_odds <= 10000


# ------------------------------------------------------------------ sport adapters
# OLBG prints its own short codes for NHL clubs; the NHL API uses different ones.
NHL_ABBREV = {"SJ": "SJS", "VGS": "VGK", "CLB": "CBJ", "WAS": "WSH", "TB": "TBL",
              "LA": "LAK", "NJ": "NJD", "NY": "NYR", "UTA": "UTA", "MON": "MTL",
              "CAL": "CGY", "VAN": "VAN", "PHI": "PHI", "CHI": "CHI", "FLA": "FLA",
              "PIT": "PIT", "BOS": "BOS", "DAL": "DAL", "STL": "STL", "COL": "COL",
              "MIN": "MIN", "SEA": "SEA", "DET": "DET", "BUF": "BUF", "OTT": "OTT",
              "NSH": "NSH", "CAR": "CAR", "EDM": "EDM", "TOR": "TOR", "WPG": "WPG",
              "ANA": "ANA"}


def nhl_match(event: dict, ev: dict) -> dict | None:
    name = event["event_name"]
    m = re.search(r"^\s*([A-Z]{2,3})\b.*@\s*([A-Z]{2,3})\b", name)
    if not m:
        return None
    away = NHL_ABBREV.get(m.group(1), m.group(1))
    home = NHL_ABBREV.get(m.group(2), m.group(2))
    cands = [f for f in ev["ice_hockey"]["fixtures"]
             if f["home"] == home and f["away"] == away]
    if not cands:
        return None
    start = event["start_utc"]
    cands.sort(key=lambda f: abs(_dt(f["start_utc"]) - _dt(start)))
    fixture = cands[0]
    if abs(_dt(fixture["start_utc"]) - _dt(start)) > 6 * 3600:
        return None
    home_team = ev["ice_hockey"]["teams"].get(home)
    away_team = ev["ice_hockey"]["teams"].get(away)
    if not home_team or not away_team or not home_team.get("point_pct") or not away_team.get("point_pct"):
        return None
    return {"fixture": fixture, "home": home_team, "away": away_team,
            "source": ev["ice_hockey"]["sources"][0],
            "identity": True,
            "fixture_url": fixture["game_center"]}


def mlb_match(event: dict, ev: dict) -> dict | None:
    m = re.search(r"^\s*([A-Z]{2,3})\b.*@\s*([A-Z]{2,3})\b", event["event_name"])
    if not m:
        return None
    away, home = m.group(1), m.group(2)
    cands = [f for f in ev["baseball"]["fixtures"] if f["home"] == home and f["away"] == away]
    if not cands:
        return None
    cands.sort(key=lambda f: abs(_dt(f["start_utc"]) - _dt(event["start_utc"])))
    fixture = cands[0]
    if abs(_dt(fixture["start_utc"]) - _dt(event["start_utc"])) > 8 * 3600:
        return None
    home_team = ev["baseball"]["teams"].get(home)
    away_team = ev["baseball"]["teams"].get(away)
    if not home_team or not away_team:
        return None
    return {"fixture": fixture, "home": home_team, "away": away_team,
            "source": ev["baseball"]["sources"][0], "identity": True,
            "fixture_url": "https://www.mlb.com/gameday/" + str(fixture["id"])}


def ehf_lookup(name: str, ev: dict) -> dict | None:
    for group, rows in ev["handball_ehf"]["groups"].items():
        for row in rows:
            if same_team(name, row["team"]):
                return {**row, "name": row["team"], "group": group}
    return None


def danish_lookup(name: str, ev: dict) -> dict | None:
    for row in ev["handball_denmark"]["teams"]:
        if same_team(name, row["team"]):
            return {**row, "name": row["team"]}
    return None


def handball_match(event: dict, ev: dict) -> dict | None:
    parts = re.split(r"\s+vs\s+", event["event_name"], flags=re.I)
    if len(parts) != 2:
        return None
    left, right = (p.strip() for p in parts)
    a = ehf_lookup(left, ev) or danish_lookup(left, ev)
    b = ehf_lookup(right, ev) or danish_lookup(right, ev)
    if not a or not b:
        return None
    if "points" not in a or "points" not in b:
        return None
    try:
        pa, pb = float(a["points"]), float(b["points"])
    except (TypeError, ValueError):
        return None
    if float(a["gp"]) == 0 or float(b["gp"]) == 0:
        return None
    # OLBG is the only source that names this fixture; the EHF table supplies the strength.
    return {"fixture": None, "home": a, "away": b,
            "source": ev["handball_ehf"]["sources"][0] if "group" in a else ev["handball_denmark"]["sources"][0],
            "identity": False, "fixture_url": ""}


def wta_match(event: dict, ev: dict) -> dict | None:
    parts = re.split(r"\s+vs\s+", event["event_name"], flags=re.I)
    if len(parts) != 2:
        return None
    players = ev["tennis_wta"]["players"]
    found = []
    for part in parts:
        hit = players.get(part.strip())
        if not hit:
            # OLBG sometimes abbreviates a first name; match on the surname + initial.
            surname = part.strip().split()[-1].lower()
            hit = next((p for n, p in players.items() if n.split()[-1].lower() == surname), None)
        if not hit or not hit.get("rank"):
            return None
        found.append(hit)
    a, b = found
    return {"fixture": None, "home": a, "away": b, "source": ev["tennis_wta"]["sources"][0],
            "identity": False, "fixture_url": ""}


def _dt(value: str) -> float:
    if not value:
        return 0.0
    try:
        return datetime.strptime(value.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(
            tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0.0


# ----------------------------------------------------------------------- pricing
def price_pair(event: dict, match: dict, sport: str) -> dict:
    home, away = match["home"], match["away"]
    edge = HOME_EDGE.get(sport, 0.0)

    # Small samples are shrunk toward the competition mean: a club that is 5-0 after five
    # rounds is not a 98% favourite.  k is the number of "prior" games added at 0.5.
    SHRINK = {"Ice Hockey": 8.0, "Handball": 5.0, "Baseball": 0.0}

    if sport == "Ice Hockey":
        k = SHRINK[sport]
        sh = (float(home["point_pct"]) * float(home["gp"]) + 0.55 * k) / (float(home["gp"]) + k)
        sa = (float(away["point_pct"]) * float(away["gp"]) + 0.55 * k) / (float(away["gp"]) + k)
        # scoring rates per game
        h_gf, h_ga = home["gf"] / home["gp"], home["ga"] / home["gp"]
        a_gf, a_ga = away["gf"] / away["gp"], away["ga"] / away["gp"]
        form_h, form_a = home["l10"], away["l10"]
    elif sport == "Baseball":
        sh, sa = float(home["pct"]), float(away["pct"])
        h_gf, h_ga = home["runs_scored"] / home["gp"], home["runs_allowed"] / home["gp"]
        a_gf, a_ga = away["runs_scored"] / away["gp"], away["runs_allowed"] / away["gp"]
        form_h, form_a = home["l10"], away["l10"]
    elif sport == "Handball":
        k = SHRINK[sport]
        raw_h = (2 * float(home["wins"]) + float(home["draws"])) / (2 * float(home["gp"]))
        raw_a = (2 * float(away["wins"]) + float(away["draws"])) / (2 * float(away["gp"]))
        sh = (raw_h * float(home["gp"]) + 0.5 * k) / (float(home["gp"]) + k)
        sa = (raw_a * float(away["gp"]) + 0.5 * k) / (float(away["gp"]) + k)
        h_gf, h_ga = float(home["gf"]) / float(home["gp"]), float(home["ga"]) / float(home["gp"])
        a_gf, a_ga = float(away["gf"]) / float(away["gp"]), float(away["ga"]) / float(away["gp"])
        form_h = f"{home['wins']}-{home['draws']}-{home['losses']}"
        form_a = f"{away['wins']}-{away['draws']}-{away['losses']}"
    elif sport == "Tennis":
        # Ranking-points ratio, damped: (points_home ** 0.6) / sum.  A straight points ratio
        # overrates the top of the list (9,196 vs 1,709 would be 84%); the 0.6 exponent keeps
        # a genuine no.1 vs no.30 near 73%, which is where the tour actually prices it.
        ph = float(home.get("points") or 0)
        pa = float(away.get("points") or 0)
        if ph > 0 and pa > 0:
            p = (ph ** 0.6) / (ph ** 0.6 + pa ** 0.6)
        else:
            p = 0.5 + (float(away["rank"]) - float(home["rank"])) / 300.0
        sh = sa = None
        h_gf = h_ga = a_gf = a_ga = None
        form_h = f"world no. {home['rank']}"
        form_a = f"world no. {away['rank']}"
    else:
        return {}

    if sport != "Tennis":
        p_home = log5(sh + edge, sa - edge)
    else:
        p_home = p
    # No originated line claims better than a 90% chance: the inputs are a handful of games.
    p_home = min(max(p_home, 0.10), 0.90)

    markets = {"moneyline": {
        "label": "Match winner (moneyline)", "home": market(p_home),
        "away": market(1 - p_home)}}

    margin = None
    total = None
    if h_gf is not None:
        margin = (h_gf - h_ga) - (a_gf - a_ga) + HOME_SCORE_EDGE.get(sport, 0.0)
        total = ((h_gf + h_ga) + (a_gf + a_ga)) / 2.0
        total += HOME_SCORE_EDGE.get(sport, 0.0) * 0.5

    if margin is not None:
        # Handicap sits on the expected margin: 0.5 steps in hockey/baseball, 1.0 in handball.
        # The line is given to the side we make favourite, with the correct sign.
        step = 1.0 if sport == "Handball" else 0.5
        line = max(step, round(abs(margin) / step) * step)
        if margin >= 0:
            p_fav = phi((margin - line) / MARGIN_SD[sport])
            p_home_cover, p_away_cover = p_fav, 1 - p_fav
            home_selection, away_selection = (f"{home['name']} -{line:g}",
                                              f"{away['name']} +{line:g}")
        else:
            p_fav = phi((-margin - line) / MARGIN_SD[sport])
            p_home_cover, p_away_cover = 1 - p_fav, p_fav
            home_selection, away_selection = (f"{home['name']} +{line:g}",
                                              f"{away['name']} -{line:g}")
        markets["handicap"] = {
            "label": "Handicap / spread", "line": line,
            "home": market(p_home_cover), "away": market(p_away_cover),
            "home_selection": home_selection, "away_selection": away_selection,
        }

    if total is not None:
        step = TOTAL_STEP[sport]
        line = round(total / step) * step
        if abs(line - total) < 1e-9:      # never publish a line that can push
            line += step
        p_over = 1 - phi((line - total) / TOTAL_SD[sport])
        markets["total"] = {
            "label": "Match total", "line": line,
            "over": market(p_over), "under": market(1 - p_over),
            "over_selection": f"Over {line:g}", "under_selection": f"Under {line:g}",
        }

    # The match-winner pick is the side we make favourite.
    pick_side = "home" if p_home >= 0.5 else "away"
    pick = markets["moneyline"][pick_side]
    pick_name = home["name"] if pick_side == "home" else away["name"]
    return {"markets": markets,
            "pick": {"market": "moneyline", "side": pick_side, "selection": pick_name,
                     "probability": pick["probability"], "decimal": pick["decimal"],
                     "american": pick["american"], "confidence": confidence(pick["probability"]),
                     "in_price_window": in_window(pick["american"])},
            "form": {"home": form_h, "away": form_a},
            "scoring": {"home_for": round(h_gf, 2) if h_gf is not None else None,
                        "home_against": round(h_ga, 2) if h_ga is not None else None,
                        "away_for": round(a_gf, 2) if a_gf is not None else None,
                        "away_against": round(a_ga, 2) if a_ga is not None else None},
            "expected_margin": round(margin, 2) if margin is not None else None,
            "expected_total": round(total, 2) if total is not None else None}


ADAPTER = {"Ice Hockey": nhl_match, "Baseball": mlb_match, "Handball": handball_match,
           "Tennis": wta_match}

WHY_UNPRICED = {
    "Volleyball": "No official club-strength feed was reachable from the capture runner "
                  "(CEV and Volleyball World pages returned 404 or a script-only shell), so no "
                  "line can be originated without inventing one.",
    "Rugby Union": "Premiership, URC and EPCR pages captured are script-rendered or returned "
                   "404, and World Rugby's rankings route returned 404, so no official strength "
                   "figure was captured for either side.",
    "Cricket": "ICC team rankings and fixtures pages render client-side (skeleton rows only); "
               "the domestic South African T20 fixtures have no captured official standings.",
    "Snooker": "OLBG listed no upcoming snooker market at capture, and the WST rankings page is "
               "a script-only shell.",
    "Darts": "The PDC order-of-merit route returned the PDC home page (1,241,860 bytes, identical "
             "to the home capture), so no official ranking table was captured.",
    "Golf": "OLBG's golf hub returned 'No tips found' at capture, i.e. no OLBG market to price; "
            "the OWGR rankings route returned 404.",
    "Motor Racing": "OLBG listed no motor-racing market at capture. Formula 1's driver standings "
                    "page is script-rendered; MotoGP's standings route returned 404.",
    "Gaelic Football": "GAA's fixtures page returned a script-only shell and no club-strength "
                       "table was captured for either side.",
    "Hurling": "As Gaelic Football: no GAA fixture or club-strength data was readable.",
    "Greyhounds": "GBGB publishes results but no pre-race strength or trap-draw feed; one OLBG "
                  "race was listed and it is left unpriced rather than guessed.",
    "Rugby League": "OLBG listed only 2027 outright markets (no upcoming match), and the Super "
                    "League table routes returned HTTP 500.",
    "Basketball": "OLBG listed NBA/KBL matches. NBA's official endpoints returned HTTP 403 to the "
                  "runner and KBL has no captured table, so no line was originated. EuroLeague "
                  "and EuroCup results are captured but OLBG has not yet listed those fixtures.",
}


def specific_reason(event: dict, sport: str, ev: dict) -> str:
    """Name the exact missing input for an unpriced row, instead of a generic sentence."""
    name = event["event_name"]
    if sport == "Ice Hockey":
        if "@" in name:
            return ("Not matched to an NHL fixture in the captured schedule, or the club is "
                    "outside the NHL (European league); no official strength figure applies.")
        return ("European club fixture: no official league table for this competition was "
                "captured, so neither side has a strength figure.")
    if sport == "Handball":
        parts = re.split(r"\s+vs\s+", name, flags=re.I)
        if len(parts) == 2:
            left = ehf_lookup(parts[0].strip(), ev) or danish_lookup(parts[0].strip(), ev)
            right = ehf_lookup(parts[1].strip(), ev) or danish_lookup(parts[1].strip(), ev)
            missing = [p.strip() for p, hit in zip(parts, (left, right)) if not hit]
            if missing:
                return ("No captured official table contains " + ", ".join(missing) +
                        ", so this side has no strength figure and the match is not priced.")
        return ("Both sides are not in the same captured official table, so no comparable "
                "strength figure exists.")
    if sport == "Tennis":
        parts = re.split(r"\s+vs\s+", name, flags=re.I)
        if len(parts) == 2:
            players = ev["tennis_wta"]["players"]
            missing = [p.strip() for p in parts if p.strip() not in players]
            if missing:
                return ("ATP fixture: the official ATP rankings route returned HTTP 403 to the "
                        "capture runner and the WTA list does not contain " +
                        ", ".join(missing) + ", so no ranking input exists for this match.")
        return "No official ranking input captured for both players."
    if sport == "Baseball":
        return "No official MLB fixture matched this listing."
    return WHY_UNPRICED.get(sport, "No official strength input was captured.")


def olbg_quote(olbg: dict, event_id: str, selection: str) -> dict | None:
    """The price OLBG itself was showing for the selection we picked, when it listed one."""
    hit = None
    for row in olbg["rows"]:
        if row["event_id"] != event_id or row["olbg_decimal"] is None:
            continue
        if norm_name(row["selection"]) and (
                norm_name(row["selection"]) in norm_name(selection)
                or norm_name(selection) in norm_name(row["selection"])):
            hit = row
            break
    if not hit:
        return None
    return {"selection": hit["selection"], "decimal": hit["olbg_decimal"],
            "american": hit["olbg_american"], "market": hit["market"],
            "tips": f"{hit['tips_won']}/{hit['tips_total']}" if hit["tips_total"] else "",
            "tip_pct": hit["tip_pct"]}


def main() -> int:
    olbg = json.load(open(os.path.join(DATA, "olbg.json"), encoding="utf-8"))
    ev = json.load(open(os.path.join(DATA, "evidence.json"), encoding="utf-8"))
    capture = olbg["captured_utc"]
    rows, priced = [], 0
    for event in sorted(olbg["events"], key=lambda e: (e["sport"], e["start_utc"])):
        if not event["start_utc"] or event["start_utc"] <= capture:
            continue
        if OUTRIGHT.search(event["event_name"]) or not event["event_name"]:
            continue
        sport = event["sport"]
        row = {
            "id": f"{event['sport_key']}-{event['event_id']}",
            "sport": sport, "sport_key": event["sport_key"], "sport_id": event["sport_id"],
            "competition": event["competition"], "event_name": event["event_name"],
            "start_utc": event["start_utc"], "venue": "",
            "olbg_url": event["olbg_url"], "olbg_markets": event["markets"],
            "olbg_listed_selections": event["selections"],
            "status": "unpriced", "pick": None, "markets": {}, "flags": [],
            "official_url": "", "official_name": "", "official_sha256": "",
            "identity_confirmed": False, "form": {}, "scoring": {}, "olbg_quote": None,
            "expected_margin": None, "expected_total": None,
        }
        adapter = ADAPTER.get(sport)
        match = adapter(event, ev) if adapter else None
        detail = ""
        if adapter and not match:
            detail = specific_reason(event, sport, ev)
        if match:
            priced_result = price_pair(event, match, sport)
            if priced_result:
                row.update({
                    "status": "priced",
                    "home_name": match["home"]["name"], "away_name": match["away"]["name"],
                    "official_url": match["source"]["url"],
                    "official_name": match["source"]["label"],
                    "official_sha256": match["source"]["sha256"],
                    "identity_confirmed": match["identity"],
                    "fixture_url": match.get("fixture_url", ""),
                    "venue": (match["fixture"] or {}).get("venue", "") if match["fixture"] else "",
                    **priced_result,
                })
                row["olbg_quote"] = olbg_quote(olbg, event["event_id"], row["pick"]["selection"])
                if not match["identity"]:
                    row["flags"].append(
                        "OLBG is the only source naming this fixture; the governing body page "
                        "supplies the team records but not the fixture identity.")
                priced += 1
        if row["status"] == "unpriced":
            row["flags"].append(detail or WHY_UNPRICED.get(
                sport, "No official strength input was captured."))
        rows.append(row)

    summary = {}
    for sport in sorted({r["sport"] for r in rows}):
        subset = [r for r in rows if r["sport"] == sport]
        picks = [r for r in subset if r["status"] == "priced"]
        summary[sport] = {
            "fixtures": len(subset), "priced": len(picks),
            "high": sum(1 for r in picks if r["pick"]["confidence"] == "High"),
            "medium": sum(1 for r in picks if r["pick"]["confidence"] == "Medium"),
            "low": sum(1 for r in picks if r["pick"]["confidence"] == "Low"),
            "in_window": sum(1 for r in picks if r["pick"]["in_price_window"]),
        }
    desk = {"schema": "olbg4.ds.desk/1", "capture_utc": capture,
            "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "assumptions": {
                "home_edge": HOME_EDGE, "margin_sd": MARGIN_SD, "total_sd": TOTAL_SD,
                "total_step": TOTAL_STEP, "home_score_edge": HOME_SCORE_EDGE,
                "confidence": "High >= 70%, Medium 60-70%, Low < 60%",
                "price_window": "fair American price between -250 and +10,000",
                "prices": "fair (no bookmaker margin) prices derived from our own probability",
            },
            "summary": summary, "rows": rows}
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(desk, fh, indent=1, sort_keys=True)
        fh.write("\n")
    print(f"rows={len(rows)} priced={priced}")
    for sport, meta in summary.items():
        print(f"  {sport:16} fixtures={meta['fixtures']:3} priced={meta['priced']:3} "
              f"high={meta['high']:2} med={meta['medium']:2} low={meta['low']:2} "
              f"in-window={meta['in_window']:2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

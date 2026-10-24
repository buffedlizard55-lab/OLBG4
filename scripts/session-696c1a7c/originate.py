#!/usr/bin/env python3
"""Match OLBG-listed events to governing-body facts, originate our own lines and
grade every selection.

Board SA (session 696c1a7c). Inputs are both committed captures:

* `data/session-696c1a7c/listings.json` — what OLBG currently has open (fixture,
  start time, market labels, and the community's listed price, which is kept as a
  *reference quote only* and never used as a model input);
* `data/session-696c1a7c/facts.json` — governing-body fixtures, results, tables
  and rankings, each carrying the URL and SHA-256 it was read from.

The model is deliberately small and fully documented in METHODOLOGY.md:
per-team scoring rates from the official table (or from official results where a
league publishes no table), a league scoring mean, a measured or assumed home
advantage, and a Poisson (integer sports) or normal (high-scoring sports)
score distribution. Fair odds are 1/p with no margin. A selection is only
published for a fixture whose two sides can both be matched to the same
official competition.

Output: data/session-696c1a7c/desk.json
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"

# Evidence tiers
#   A — the fixture itself is on a governing-body feed (participants, date)
#   B — the fixture is OLBG-listed only, but both participants are confirmed in
#       the same official competition (table/ranking) captured at the same time
#   C — no official input at all: listed, never priced
TIER_CAP = {"A": "high", "B": "medium", "C": "low"}

# Score-difference standard deviations used when a competition has no history to
# measure one from. Values are the published convention for each sport and are
# stated in METHODOLOGY.md; a measured value always replaces them.
SIGMA_DEFAULT = {"Ice Hockey": 2.2, "Handball": 8.0, "Basketball": 11.5,
                 "Baseball": 3.2, "Rugby Union": 11.0, "Rugby League": 12.0,
                 "Volleyball": 12.0, "Snooker": 2.5, "Tennis": 3.0}
HOME_ADV_DEFAULT = {"Ice Hockey": 0.18, "Handball": 1.4, "Basketball": 2.2,
                    "Baseball": 0.10, "Rugby Union": 3.0, "Rugby League": 3.0,
                    "Volleyball": 0.6, "Snooker": 0.0, "Tennis": 0.0}
INTEGER_SPORTS = {"Ice Hockey", "Handball", "Baseball"}

SUFFIX = {"hc", "hk", "if", "bk", "fc", "bc", "cf", "sc", "ac", "as", "ss",
          "club", "team", "handball", "handbold", "håndbold", "w", "women"}
ALIAS = {
    "wolves": "wolverhampton", "spurs": "tottenham", "villa": "aston villa",
    "karp": "karpat", "tps": "tps", "psg": "paris saint germain",
    "vardar": "hc vardar", "vardar 1961": "hc vardar",
    "barca": "barcelona", "barca lassa": "barcelona",
}


def norm(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9 ]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def tokens(name: str) -> list[str]:
    out = []
    for t in norm(name).split():
        if t in SUFFIX or len(t) < 2:
            continue
        out.append(ALIAS.get(t, t))
    return out


def name_score(a: str, b: str) -> float:
    """How strongly two names refer to the same side (0…1)."""
    ta, tb = tokens(a), tokens(b)
    if not ta or not tb:
        return 0.0
    na, nb = norm(a), norm(b)
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.92
    shared = [t for t in ta if t in tb]
    if not shared:
        return 0.0
    longest = max(len(t) for t in shared)
    if longest < 4:
        return 0.0
    return min(0.9, 0.55 + 0.1 * len(shared))


# --------------------------------------------------------------------------- #
# Aim / pricing helpers
# --------------------------------------------------------------------------- #
def poisson_pmf(k: int, lam: float) -> float:
    return math.exp(-lam) * lam ** k / math.factorial(k)


def skellam_probs(lh: float, la: float, max_goals: int = 22) -> dict:
    ph = pd = 0.0
    for i in range(max_goals):
        pi = poisson_pmf(i, lh)
        for j in range(max_goals):
            p = pi * poisson_pmf(j, la)
            if i > j:
                ph += p
            elif i == j:
                pd += p
    return {"home": ph, "draw": pd, "away": max(0.0, 1 - ph - pd)}


def normal_cdf(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        return 1.0 if x > mu else 0.0
    return 0.5 * (1 + math.erf((x - mu) / (sigma * math.sqrt(2))))


def american(dec: float) -> int:
    if dec is None or dec <= 1:
        return 0
    return int(round((dec - 1) * 100)) if dec >= 2 else -int(round(100 / (dec - 1)))


def confidence(p: float, tier: str, min_sample: int | None) -> str:
    if p >= 0.70:
        label = "high"
    elif p >= 0.58:
        label = "medium"
    else:
        label = "low"
    order = {"low": 0, "medium": 1, "high": 2}
    cap = order[TIER_CAP[tier]]
    if min_sample is not None:
        if min_sample < 5:
            cap = min(cap, 0)
        elif min_sample < 10:
            cap = min(cap, 1)
    label = min(label, sorted(order, key=order.get)[cap]) if order[label] > cap else label
    return label


# --------------------------------------------------------------------------- #
def load(name: str) -> dict:
    path = DATA / name
    if not path.exists():
        raise SystemExit(f"missing {path}; run the capture + parse steps first")
    return json.loads(path.read_text())


def build_strength(facts: dict) -> dict:
    """Per-competition team strength from official tables, filled out from results."""
    strength: dict[str, dict] = defaultdict(lambda: {"teams": {}, "history": [],
                                                     "sigma": None, "home_adv": None,
                                                     "mean": None, "sport": None})
    for t in facts["teams"]:
        c = t["competition"]
        entry = strength[c]
        entry["sport"] = t["sport"]
        cur = entry["teams"].setdefault(t["team"], {})
        for k, v in t.items():
            if v is not None and k not in ("key", "sport", "competition", "team",
                                           "source_id", "source_url", "sha256",
                                           "bytes", "captured_utc"):
                cur[k] = v
    for h in facts["history"]:
        c = h["competition"]
        entry = strength[c]
        if entry["sport"] is None:
            entry["sport"] = h["sport"]
        entry["history"].append(h)
        for side, gf, ga in (("home", h["home_score"], h["away_score"]),
                             ("away", h["away_score"], h["home_score"])):
            key = h[side]
            team = entry["teams"].setdefault(key, {"team": key, "from_results": True})
            team["played"] = (team.get("played") or 0) + 1
            if gf is None or ga is None:
                continue
            team["goals_for"] = (team.get("goals_for") or 0) + gf
            team["goals_against"] = (team.get("goals_against") or 0) + ga
            if gf > ga:
                team["wins"] = (team.get("wins") or 0) + 1
            elif gf == ga:
                team["draws"] = (team.get("draws") or 0) + 1
            else:
                team["losses"] = (team.get("losses") or 0) + 1
    return strength


def rates(entry: dict) -> tuple[dict, dict]:
    """Per-team (for, against) per game, using the table totals the source prints."""
    table = {}
    for name, t in entry["teams"].items():
        played = t.get("played")
        gf = t.get("goals_for", t.get("points_for", t.get("runs_for", t.get("runs"))))
        ga = t.get("goals_against", t.get("points_against", t.get("runs_against")))
        if not played or gf is None or ga is None:
            continue
        table[name] = {"for": gf / played, "against": ga / played, "played": played,
                       "wins": t.get("wins"), "losses": t.get("losses"),
                       "draws": t.get("draws"), "points": t.get("points"),
                       "goals_for": gf, "goals_against": ga, "team": t.get("team", name)}
    return table, entry["teams"]


def fit(entry: dict) -> dict:
    table, raw = rates(entry)
    if not table:
        return {}
    mean_for = sum(v["for"] for v in table.values()) / len(table)
    mean_against = sum(v["against"] for v in table.values()) / len(table)
    hist = entry["history"]
    margins = []
    home_scores, away_scores = [], []
    for h in hist:
        if h["home_score"] is None or h["away_score"] is None:
            continue
        margins.append(h["home_score"] - h["away_score"])
        home_scores.append(h["home_score"])
        away_scores.append(h["away_score"])
    sigma = None
    if len(margins) >= 20:
        mu = sum(margins) / len(margins)
        sigma = math.sqrt(sum((m - mu) ** 2 for m in margins) / (len(margins) - 1))
    home_adv = None
    if len(home_scores) >= 20:
        home_adv = (sum(home_scores) / len(home_scores) - sum(away_scores) / len(away_scores)) / 2
    return {"table": table, "mean": (mean_for + mean_against) / 2, "sigma": sigma,
            "home_adv": home_adv, "mean_for": mean_for, "mean_against": mean_against}


def expected(fitinfo: dict, sport: str, home: str, away: str) -> dict | None:
    table = fitinfo["table"]
    h, a = table.get(home), table.get(away)
    if not h or not a:
        return None
    adv = fitinfo["home_adv"]
    if adv is None:
        adv = HOME_ADV_DEFAULT.get(sport, 0.0)
    mean = fitinfo["mean"] or 1.0
    lh = max(0.05, h["for"] * a["against"] / mean + adv / 2)
    la = max(0.05, a["for"] * h["against"] / mean - adv / 2)
    sigma = fitinfo["sigma"] or SIGMA_DEFAULT.get(sport, 3.0)
    return {"lambda_home": round(lh, 3), "lambda_away": round(la, 3),
            "sigma": round(sigma, 3), "home_adv": round(adv, 3),
            "sample": min(h["played"], a["played"]),
            "home_played": h["played"], "away_played": a["played"]}


def prices(sport: str, exp: dict) -> dict:
    lh, la, sigma = exp["lambda_home"], exp["lambda_away"], exp["sigma"]
    out = {"match_winner": {}, "handicap": {}, "total": {}}
    if sport in INTEGER_SPORTS:
        probs = skellam_probs(lh, la)
        if sport == "Handball":
            out["match_winner"] = {"home": probs["home"], "draw": probs["draw"], "away": probs["away"]}
        else:
            out["match_winner"] = {"home": probs["home"] + probs["draw"] / 2,
                                   "away": probs["away"] + probs["draw"] / 2}
    else:
        p_home = normal_cdf(0, -(lh - la), sigma)
        out["match_winner"] = {"home": p_home, "away": 1 - p_home}
    total_mean = lh + la
    total_sigma = math.sqrt(lh + la) if sport in INTEGER_SPORTS else sigma * 1.2
    line = round(total_mean * 2) / 2
    out["total"] = {"line": line,
                    "over": 1 - normal_cdf(line, total_mean, total_sigma),
                    "under": normal_cdf(line, total_mean, total_sigma)}
    spread_line = 1.5 if sport == "Ice Hockey" else (round((lh - la) * 2) / 2)
    out["handicap"] = {"line": spread_line,
                       "home": 1 - normal_cdf(-spread_line, lh - la, sigma),
                       "away": normal_cdf(-spread_line, lh - la, sigma)}
    return out


# --------------------------------------------------------------------------- #
def load_strength_for_sport(sport: str, strength: dict, competition_hint: str) -> list[str]:
    return [k for k, v in strength.items() if v["sport"] == sport]


def main() -> int:
    listings = load("listings.json")
    facts = load("facts.json")
    strength = build_strength(facts)
    fits = {k: fit(v) for k, v in strength.items()}
    now = listings["parsed_utc"]

    fixtures_by_comp = defaultdict(list)
    for f in facts["fixtures"]:
        fixtures_by_comp[f["competition"]].append(f)

    rows = []
    unmatched = []
    for sport, blob in listings["sports"].items():
        for ev in blob["events"]:
            if (ev.get("start_utc") or "9") < now:
                continue
            name = ev["event"]
            sides = re.split(r"\s+@\s+|\s+vs\.?\s+|\s+v\s+", name)
            row = {
                "sport": sport, "event": name, "olbg_url": ev["olbg_url"],
                "start_utc": ev["start_utc"], "event_id": ev["event_id"],
                "listed_markets": ev["listed_markets"], "competition": None,
                "home": sides[1] if "@" in name and len(sides) == 2 else (sides[0] if sides else None),
                "away": sides[0] if "@" in name and len(sides) == 2 else (sides[1] if len(sides) > 1 else None),
                "official": [], "markets": {}, "pick": None, "tier": "C", "flags": [],
            }
            if len(sides) != 2:
                row["flags"].append("event is a tournament/outright, not a two-sided match")
                rows.append(row)
                unmatched.append(row)
                continue
            best = None
            for comp in load_strength_for_sport(sport, strength, ""):
                table = fits.get(comp, {}).get("table") or {}
                if not table:
                    continue
                hbest = max(((name_score(row["home"], t), t) for t in table), default=(0, None))
                abest = max(((name_score(row["away"], t), t) for t in table), default=(0, None))
                if hbest[0] >= 0.55 and abest[0] >= 0.55 and hbest[1] != abest[1]:
                    score = min(hbest[0], abest[0])
                    if best is None or score > best[0]:
                        best = (score, comp, hbest[1], abest[1])
            if not best:
                row["flags"].append("no official fixture/table match for both participants")
                rows.append(row)
                unmatched.append(row)
                continue
            score, comp, home, away = best
            row["competition"] = comp
            row["official"] = [c for c in facts["competitions"] if c["key"] == comp]
            row["matched_home"] = home
            row["matched_away"] = away
            row["match_score"] = round(score, 2)
            # is the fixture itself printed by the governing body?
            for f in fixtures_by_comp.get(comp, []):
                if f["home"] == home and f["away"] == away and (f.get("start_utc") or "")[:10] == (row["start_utc"] or "")[:10]:
                    row["tier"] = "A"
                    row["fixture_source"] = {k: f[k] for k in ("source_url", "sha256", "source_id")}
                    row["venue"] = f.get("venue")
                    break
            if row["tier"] != "A":
                row["tier"] = "B"
                row["flags"].append("fixture date from the OLBG listing; participants confirmed in the official competition table")
            exp = expected(fits[comp], sport, home, away)
            if not exp:
                row["flags"].append("official rates unavailable for one side")
                rows.append(row)
                continue
            row["expected"] = exp
            row["markets"] = prices(sport, exp)
            rows.append(row)

    DATA.joinpath("desk_raw.json").write_text(json.dumps({"rows": rows,
                                                          "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                                          "unmatched": len(unmatched)}, indent=1) + "\n")
    print(f"events considered: {len(rows)}  matched: {sum(1 for r in rows if r['competition'])}  "
          f"unmatched: {len(unmatched)}")
    for r in rows:
        if r["competition"]:
            m = r["markets"]["match_winner"]
            print(f"  {r['tier']} {r['sport'][:12]:12s} {r['competition']:10s} "
                  f"{r['home'][:22]:22s} v {r['away'][:22]:22s} "
                  f"-> {r['matched_home'][:20]:20s} / {r['matched_away'][:20]:20s} "
                  f"p_home={m.get('home', 0):.3f} sample={r['expected']['sample']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

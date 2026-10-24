#!/usr/bin/env python3
"""Price the individual sports from the governing body's own match record.

Team sports are handled by originate.py with a scoring model. Sports where the
unit of competition is a player cannot use goals, so this module fits a
Bradley–Terry strength to the official match record instead: every completed
match in the captured feed is one comparison, the strengths are fitted by
maximum likelihood, and the win probability for a new pairing is
`sigmoid(r_a - r_b)`.

Inputs (all already captured):
    facts.json  tennis_matches  — WTA draw feeds: player names, state, winner,
                                  score, scheduled timestamp, source hash
    listings.json               — the OLBG event list to price against

Output: data/session-696c1a7c/desk_ind.json

Nothing is filled in. A player who does not appear in the official match record
gets no rating, and the event is returned as an unmatched row with that reason.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"

MIN_MATCHES = 3          # a player needs this many decided matches to be rated
SCALE = 0.8              # Bradley–Terry scale on the log-strength axis
RIDGE = 1.2              # L2 pull towards the field mean: keeps thin graphs off 99%
CONF_MEDIUM_MATCHES = 8  # both players with this many matches can reach Medium
P_CLAMP = (0.08, 0.92)   # no individual-sport line is published beyond this


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]+", " ", s.lower())
    return " ".join(s.split())


def last_first(name: str) -> tuple[str, str]:
    """"Katarzyna Kawa" -> ("kawa", "k"); "K. Kawa" -> ("kawa", "k")."""
    bits = norm(name).split()
    if not bits:
        return "", ""
    return bits[-1], bits[0][0]


def pct(p: float) -> float:
    return round(p, 4)


def american_from_prob(p: float) -> tuple[float, int]:
    p = min(max(p, 0.005), 0.995)
    dec = round(1 / p, 3)
    am = int(round((dec - 1) * 100)) if dec >= 2 else -int(round(100 / (dec - 1)))
    return dec, am


def bradley_terry(pairs: list[tuple[str, str]]) -> tuple[dict[str, float], dict[str, int]]:
    """Fit strengths by MLE on (winner, loser) pairs — no library, just the recursion."""
    players = sorted({p for pair in pairs for p in pair})
    if not players:
        return {}, {}
    r = {p: 0.0 for p in players}
    counts: dict[str, int] = {p: 0 for p in players}
    for w, l in pairs:
        counts[w] += 1
        counts[l] += 1
    for _ in range(600):                      # small graphs converge in a few dozen passes
        grad = {p: 0.0 for p in players}
        for w, l in pairs:
            p = 1 / (1 + math.exp(-(r[w] - r[l])))
            grad[w] += 1 - p
            grad[l] -= 1 - p
        total = sum(counts.values()) or 1
        for p in players:
            step = 0.35 * (len(players) / total)
            r[p] += step * (grad[p] - RIDGE * r[p])
        mean = sum(r.values()) / len(r)
        for p in players:
            r[p] -= mean
    return r, counts


def tennis_rows(facts: dict, listings: dict) -> dict:
    matches = facts.get("tennis_matches") or []
    pairs: list[tuple[str, str]] = []
    index: dict[tuple[str, str], dict] = {}
    upcoming: dict[frozenset[str], dict] = {}
    for m in matches:
        a = f"{m.get('player_first_a','')} {m.get('player_last_a','')}".strip()
        b = f"{m.get('player_first_b','')} {m.get('player_last_b','')}".strip()
        if not a or not b:
            continue
        for name in (a, b):
            index.setdefault(last_first(name), {"name": name, "id": m.get("player_id_a")})
        if m.get("winner") in ("1", "2") and m.get("state") == "F":
            win, lose = (a, b) if m["winner"] == "1" else (b, a)
            pairs.append((last_first(win), last_first(lose)))
        elif m.get("state") != "F" and m.get("start_utc"):
            upcoming[frozenset((last_first(a), last_first(b)))] = m
    strengths, counts = bradley_terry(pairs)

    recent: dict[tuple[str, str], list[dict]] = {}
    record: dict[tuple[str, str], dict] = {}
    for m in matches:
        if m.get("state") != "F" or m.get("winner") not in ("1", "2"):
            continue
        a = f"{m.get('player_first_a','')} {m.get('player_last_a','')}".strip()
        b = f"{m.get('player_first_b','')} {m.get('player_last_b','')}".strip()
        for name, other, won in ((a, b, m["winner"] == "1"), (b, a, m["winner"] == "2")):
            k = last_first(name)
            rec = record.setdefault(k, {"name": name, "wins": 0, "losses": 0})
            rec["wins" if won else "losses"] += 1
            recent.setdefault(k, []).append({
                "date": str(m.get("start_utc") or "")[:10], "opponent": other,
                "score": m.get("score") or "", "result": "W" if won else "L", "venue": "neutral"})

    rows, unmatched = [], []
    sport_events = listings["sports"].get("Tennis", {}).get("events", [])
    for ev in sport_events:
        sides = [s.strip() for s in re.split(r"\s+vs\.?\s+", ev["event"])]
        base = {"sport": "Tennis", "event": ev["event"], "olbg_url": ev["olbg_url"],
                "start_utc": ev.get("start_utc"), "listed_markets": ev.get("listed_markets", []),
                "competition": None, "official": [], "markets": {}, "pick": None,
                "tier": "C", "flags": []}
        if len(sides) != 2:
            base["flags"].append("event is a tournament/outright, not a two-sided match")
            unmatched.append(base)
            continue
        keys = []
        for side in sides:
            k = last_first(side)
            keys.append(k)
        missing = [s for s, k in zip(sides, keys) if k not in strengths]
        if missing:
            base["event_home"], base["event_away"] = sides
            base["flags"].append("player not present in the captured official match record: "
                                 + ", ".join(missing))
            unmatched.append(base)
            continue
        (ka, kb) = keys
        ra, rb = strengths[ka], strengths[kb]
        p_a = 1 / (1 + math.exp(-(ra - rb) * SCALE))
        p_a = min(max(p_a, P_CLAMP[0]), P_CLAMP[1])
        n = min(counts[ka], counts[kb])
        if n < MIN_MATCHES:
            base["event_home"], base["event_away"] = sides
            base["flags"].append(
                f"too few decided official matches behind the rating ({counts[ka]} and {counts[kb]}; "
                f"{MIN_MATCHES} needed each)")
            unmatched.append(base)
            continue
        fx = upcoming.get(frozenset((ka, kb)))
        tier = "B" if fx else "D"
        row = dict(base)
        row.update({
            "competition": "wta",
            "official": [{"key": "wta", "name": "WTA — official draw feeds", "kind": "tour",
                          "source_id": fx.get("source_id") if fx else (matches[0].get("source_id")
                                                                     if matches else None),
                          "source_url": (fx or matches[0]).get("source_url") if matches else "",
                          "sha256": (fx or matches[0]).get("sha256") if matches else ""}],
            "home": sides[0], "away": sides[1],
            "matched_home": index[ka]["name"], "matched_away": index[kb]["name"],
            "markets": {"match_winner": {"home": pct(p_a), "away": pct(1 - p_a)},
                        "ratings": {"home": round(ra, 3), "away": round(rb, 3),
                                    "matches_home": counts[ka], "matches_away": counts[kb]}},
            "expected": {"sample": n, "matches_home": counts[ka], "matches_away": counts[kb],
                         "rating_home": round(ra, 3), "rating_away": round(rb, 3)},
            "tier": tier,
            "stats": {ka[0]: {}, kb[0]: {}},
            "player_stats": {
                "home": {"played": counts[ka], "wins": record.get(ka, {}).get("wins"),
                         "losses": record.get(ka, {}).get("losses")},
                "away": {"played": counts[kb], "wins": record.get(kb, {}).get("wins"),
                         "losses": record.get(kb, {}).get("losses")},
            },
            "recent": {"home": sorted(recent.get(ka, []), key=lambda r: r["date"])[-5:][::-1],
                       "away": sorted(recent.get(kb, []), key=lambda r: r["date"])[-5:][::-1]},
        })
        if not fx:
            row["flags"].append("fixture time from the OLBG listing; both players are in the "
                                "official WTA match record but the pairing is not printed as a "
                                "scheduled match in the captured draws")
        else:
            row["fixture_source"] = {"source_id": fx.get("source_id"), "source_url": fx.get("source_url"),
                                     "sha256": fx.get("sha256")}
            row["venue"] = fx.get("tournament")
            row["start_utc"] = fx.get("start_utc") or row["start_utc"]
        rows.append(row)

    return {"sport": "Tennis", "rows": rows, "unmatched": len(unmatched),
            "ratings": {f"{k[0]}": v for k, v in list(strengths.items())[:40]},
            "players_rated": len(strengths), "decided_matches": len(pairs),
            "generated_utc": facts.get("generated_utc")}


def main() -> int:
    facts = json.loads((DATA / "facts.json").read_text())
    listings = json.loads((DATA / "listings.json").read_text())
    out = tennis_rows(facts, listings)
    (DATA / "desk_ind.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"tennis: {out['players_rated']} players rated from {out['decided_matches']} decided matches; "
          f"{len(out['rows'])} event(s) priced, {out['unmatched']} unmatched")
    for r in out["rows"]:
        mw = (r.get("markets") or {}).get("match_winner")
        print(f"  {r['tier']} {r['event'][:52]:52s} "
              f"{(mw or {}).get('home')} / {(mw or {}).get('away')} sample={r['expected']['sample'] if r.get('expected') else '-'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

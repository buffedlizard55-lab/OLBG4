#!/usr/bin/env python3
"""Board AD desk builder (session arena/8cbd0cb9-olbg4).

Reads the committed OLBG reverse-engineering snapshot (data/raw/*.json, collected 2026-10-21)
and originates disclosed neutral-prior lines for every in-scope event, then overlays the two
peer-session verified rows (session e1161e0e / Board X) that clear the high-confidence rule
(model probability >= 0.70 AND originated book American odds inside -250..+10000).

Nothing is inferred from unofficial sources. Rows with no governing-body source leave
pick/confidence/odds blank or neutral-prior and are flagged on the Flagged-for-Review page.

Writes:
  data/session-8cbd0cb9/desk.json
  data/session-8cbd0cb9/flagged.json (unverified rows, blank fields, review links)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "session-8cbd0cb9"
OUT.mkdir(parents=True, exist_ok=True)

EXCLUDED_SPORTS = {
    "soccer", "football", "boxing", "ufc", "mma", "american football",
    "hurling", "horse racing", "cycling", "specials",
}

SPORT_SLUG = {
    "Tennis": "tennis", "Basketball": "basketball", "Golf": "golf", "Cricket": "cricket",
    "Snooker": "snooker", "Rugby Union": "rugby-union", "Rugby League": "rugby-league",
    "Baseball": "baseball", "Ice Hockey": "ice-hockey", "Motor Racing": "motor-racing",
    "Darts": "darts", "Handball": "handball", "Volleyball": "volleyball",
    "Aussie Rules": "aussie-rules", "eSports": "esports", "Gaelic Football": "gaelic-football",
    "Greyhounds": "greyhounds",
}

# --- Disclosed model constants (neutral prior; no live strength feeds reachable from
# --- this sandbox — egress is limited to GitHub/package registries) -----------------
FAIR_2WAY = 2.00          # p = 0.50 each side, zero vig
VIG_2WAY = 0.042          # 4.2% vig, two-way (match winner / handicap)
VIG_3WAY = 0.052          # 5.2% vig, three-way (1X2)


def book_decimal_2way(fair: float) -> float:
    implied = (1.0 / fair) * (1.0 + VIG_2WAY)
    return round(1.0 / implied, 2)


def american_from_decimal(d: float) -> int:
    if d >= 2.0:
        return round((d - 1.0) * 100)
    return round(-100.0 / (d - 1.0))


BOOK_2WAY = book_decimal_2way(FAIR_2WAY)   # 1.92
BOOK_2WAY_AMER = american_from_decimal(BOOK_2WAY)  # -109

FEED_DATE = "2026-10-21"   # OLBG snapshot collection date (US Eastern labels)


def label_to_date(label: str) -> str:
    lab = label.strip().lower()
    if lab.startswith("today"):
        return FEED_DATE
    if lab.startswith("tomorrow"):
        return "2026-10-22"
    return ""


def side_block(side: str) -> dict:
    return {
        "side": side,
        "fair_decimal": FAIR_2WAY,
        "book_decimal": BOOK_2WAY,
        "book_american": BOOK_2WAY_AMER,
    }


def build_olbg_rows() -> list[dict]:
    rows: list[dict] = []
    for path in sorted(RAW.glob("*.json")):
        data = json.loads(path.read_text())
        sport = data["sport"]
        if sport.lower() in EXCLUDED_SPORTS:
            continue
        slug = SPORT_SLUG.get(sport)
        if slug is None:
            continue  # not an in-scope OLBG sport
        for e in data.get("events", []):
            eid = e["event_id"]
            start = label_to_date(e.get("olbg_date_label", ""))
            is_greyhound = sport == "Greyhounds"
            is_outright = sport in ("Golf", "Motor Racing")
            flags: list[str] = []

            if is_greyhound:
                flags.append("Greyhound Board of Great Britain feed WAF-blocked (HTTP 403) — no official inputs; pick, confidence and odds left blank")
                markets = {
                    "match_winner": None,
                    "handicap": None,
                    "total": None,
                }
                pick = ""
                pick_p = None
                pick_dec = None
                pick_amer = None
                confidence = ""
                verified = False
            elif is_outright:
                flags.append("Tournament/race winner event — no head-to-head match winner line originated; outright market not priced by this desk")
                markets = {
                    "match_winner": None,
                    "handicap": None,
                    "total": None,
                }
                pick = ""
                pick_p = None
                pick_dec = None
                pick_amer = None
                confidence = ""
                verified = False
            else:
                markets = {
                    "match_winner": {
                        e["p1"]: side_block(e["p1"]),
                        e["p2"]: side_block(e["p2"]),
                    },
                    "handicap": {
                        "line": 0.0,
                        "note": "Neutral pick'em — no verified handicap inputs; line is an opinion expression, not a verified price",
                        "sides": {
                            e["p1"]: side_block(e["p1"]),
                            e["p2"]: side_block(e["p2"]),
                        },
                    },
                    "total": None,
                }
                flags.append("Neutral-prior model (p = 0.50 each side) — no verified team-strength inputs; pick is first-listed side by convention")
                flags.append("Match total not originated — no verified scoring/pace inputs captured")
                pick = e["p1"]
                pick_p = 0.50
                pick_dec = FAIR_2WAY
                pick_amer = american_from_decimal(FAIR_2WAY)  # +100
                confidence = "Low"
                verified = False

            rows.append({
                "id": f"ad-olbg-{slug}-{eid}",
                "source_layer": "olbg-capture-2026-10-21",
                "sport": sport,
                "sport_slug": slug,
                "competition": e.get("competition_olbg") or "OLBG feed listing",
                "competition_olbg": e.get("competition_olbg"),
                "match": e["match"],
                "p1": e.get("p1"),
                "p2": e.get("p2"),
                "start_date_local": start,
                "olbg_date_label": e.get("olbg_date_label"),
                "status": ("upcoming-vs-feed" if start == "2026-10-22" else "feed-date-2026-10-21"),
                "feed_market": e.get("feed_market"),
                "olbg_event_id": eid,
                "olbg_url": e["olbg_url"],
                "olbg_source_page": data["source_page"],
                "markets": markets,
                "match_winner_pick": pick,
                "pick_market": "Match winner",
                "pick_p": pick_p,
                "pick_decimal": pick_dec,
                "pick_american": pick_amer,
                "confidence": confidence,
                "high_confidence": bool(confidence == "High" and pick_amer is not None and -250 <= pick_amer <= 10000),
                "prediction": "",
                "official_url": "",
                "official_source_name": "",
                "verified": verified,
                "flags": flags,
            })
    return rows


def overlay_peer_rows() -> list[dict]:
    """Verified peer-session rows (session e1161e0e, Board X) that clear the high window,
    copied verbatim from committed data and attributed."""
    src = json.loads((ROOT / "data" / "session-e1161e0e" / "board.json").read_text())
    rows: list[dict] = []
    for r in src["rows"]:
        p = r.get("pick_p")
        a = r.get("pick_amer")
        if p is None or a is None:
            continue
        if p < 0.70 or not (-250 <= a <= 10000):
            continue
        if r["sport"].lower() in EXCLUDED_SPORTS:
            continue
        flags = list(r.get("flags", [])) if isinstance(r.get("flags"), list) else []
        if r["sport"] == "Rugby League":
            flags.append("One Round-1 game per team at capture — small sample; selection stands per p >= 0.70 rule but treat as small-sample")
        rows.append({
            "id": f"ad-peer-{r['id']}",
            "source_layer": "peer-session-e1161e0e-attributed",
            "sport": r["sport"],
            "sport_slug": SPORT_SLUG[r["sport"]],
            "competition": r["competition"],
            "match": f"{r.get('home','')} vs {r.get('away','')}",
            "p1": r.get("home"),
            "p2": r.get("away"),
            "start_date_local": r.get("date", ""),
            "olbg_date_label": r.get("time_et", ""),
            "status": "upcoming-2026-10-23",
            "feed_market": r.get("pick_market"),
            "olbg_event_id": None,
            "olbg_url": "",
            "olbg_source_page": "peer session Board X fixture capture",
            "markets": {
                "match_winner": {
                    side: {"fair_decimal": None, "book_decimal": dec, "book_american": None}
                    for side, dec in r.get("markets", {}).get("Moneyline", r.get("markets", {}).get("Match winner", {})).items()
                } or None,
                "handicap": r.get("markets", {}).get("Spread Washington Wizards +6.5")
                            or r.get("markets", {}).get("Handicap Samoa -8.5"),
                "total": r.get("markets", {}).get("Total points"),
            },
            "match_winner_pick": r["pick"],
            "pick_market": r["pick_market"],
            "pick_p": p,
            "pick_decimal": r.get("pick_dec"),
            "pick_american": a,
            "confidence": "High",
            "high_confidence": True,
            "prediction": "",  # filled by predictions_bank.py
            "official_url": r.get("source_url") or r.get("fixture_url", ""),
            "official_source_name": r.get("source_name", ""),
            "verified": True,
            "flags": flags,
        })
    return rows


def build_flagged(rows: list[dict]) -> list[dict]:
    flagged: list[dict] = []
    for r in rows:
        if r["verified"]:
            continue
        reason = "; ".join(r["flags"]) if r["flags"] else "No governing-body source URL recorded for this fixture"
        review_url = r["olbg_url"] if r["olbg_url"] else ""
        flagged.append({
            "id": r["id"],
            "sport": r["sport"],
            "match": r["match"],
            "date": r["start_date_local"],
            "reason": reason,
            "review_url": review_url,
            "review_url_kind": "olbg.com listing (non-official, cross-check only)" if r["olbg_url"] else "none recorded",
            "blank_fields": [b for b in (["match_winner_pick"] if not r["match_winner_pick"] else [])
                                            + (["confidence"] if not r["confidence"] else [])
                                            + (["originated_odds"] if not r["pick_decimal"] else [])],
        })
    return flagged


def main() -> None:
    rows = build_olbg_rows()
    overlays = overlay_peer_rows()
    rows.extend(overlays)
    # stable ordering: sport, then date, then match
    rows.sort(key=lambda r: (r["sport"], r["start_date_local"], r["match"]))

    desk = {
        "schema": "olbg4.session-8cbd0cb9.desk.v1",
        "board": "AD",
        "session_id": "8cbd0cb9",
        "generated_at_utc": "2026-10-22T13:00:00Z",
        "cutoff_note": "OLBG snapshot collected 2026-10-21; peer-session overlay rows copied verbatim from data/session-e1161e0e/board.json and attributed",
        "excluded_sports": sorted(EXCLUDED_SPORTS),
        "model": {
            "name": "disclosed neutral prior",
            "fair_decimal_2way": FAIR_2WAY,
            "vig_2way_pct": VIG_2WAY * 100,
            "book_decimal_2way": BOOK_2WAY,
            "book_american_2way": BOOK_2WAY_AMER,
            "handicap_line": 0.0,
            "note": "No live market odds or strength feeds reachable from this sandbox; lines are our own disclosed opinion lines, not verified probabilities",
        },
        "high_confidence_rule": {
            "model_probability_pct": 70.0,
            "book_american_window": [-250, 10000],
            "count": sum(1 for r in rows if r["high_confidence"]),
        },
        "counts": {
            "rows_total": len(rows),
            "rows_from_olbg_capture": len(rows) - len(overlays),
            "rows_from_peer_overlay": len(overlays),
            "verified_rows": sum(1 for r in rows if r["verified"]),
            "high_confidence": sum(1 for r in rows if r["high_confidence"]),
            "medium_confidence": sum(1 for r in rows if r["confidence"] == "Medium"),
            "low_confidence": sum(1 for r in rows if r["confidence"] == "Low"),
        },
        "by_sport": {},
    }
    desk["rows"] = rows
    by_sport: dict[str, int] = {}
    for r in rows:
        by_sport[r["sport"]] = by_sport.get(r["sport"], 0) + 1
    desk["by_sport"] = dict(sorted(by_sport.items()))

    flagged = build_flagged(rows)

    (OUT / "desk.json").write_text(json.dumps(desk, indent=2, ensure_ascii=False))
    (OUT / "flagged.json").write_text(
        json.dumps({"schema": "olbg4.session-8cbd0cb9.flagged.v1",
                    "board": "AD", "session_id": "8cbd0cb9",
                    "count": len(flagged), "items": flagged}, indent=2, ensure_ascii=False))
    print(f"desk: {len(rows)} rows | overlays: {len(overlays)} | high: {desk['counts']['high_confidence']} | flagged: {len(flagged)}")


if __name__ == "__main__":
    main()

"""Build the Board S dataset: fixtures -> projections -> markets -> picks -> JSON.

    python3 -m deskbot.build            # write desk/data/board.json + report counts
    python3 -m deskbot.build --verbose  # also print every High candidate

Nothing is written to any other session's files. Outputs:

  desk/data/board.json      every fixture with projections, markets, picks and grades
  desk/data/board_summary.json  counts used by the site and the verification gate
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
from pathlib import Path

from . import model

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "desk" / "data"


def _load(name: str) -> dict:
    with open(DATA / name, encoding="utf-8") as fh:
        return json.load(fh)


def _agrees_home(proj: dict) -> bool:
    return (proj["p_home"] > 0.5) == (proj["p_home_winrate"] > 0.5)


def _agrees(pick: dict, proj: dict) -> bool:
    if pick["market"] in ("moneyline", "handicap"):
        side_home = pick["side"] == "home"
        model_side_home = proj["p_home_winrate"] > 0.5
        return side_home == model_side_home
    # totals: the second check is that the projection is clearly away from the line,
    # otherwise the pick is only riding the rounding of the line.
    edge = proj["expected_total"] - pick["line"]
    if pick["side"] == "under":
        edge = -edge
    return edge >= 0.25


def build() -> dict:
    nhl = _load("nhl_fixtures.json")
    nhl_st = _load("nhl_standings.json")
    mlb = _load("mlb_fixtures.json")
    mlb_st = _load("mlb_standings.json")

    states = {abbr: model.nhl_team_state(t) for abbr, t in nhl_st["teams"].items()}
    league_goals = round(
        sum(t["gf"] for t in nhl_st["teams"].values()) / sum(t["gp"] for t in nhl_st["teams"].values()), 4
    )
    model.CONSTANTS["league_goals_per_team"]["value"] = league_goals

    rows: list[dict] = []
    for fx in nhl["fixtures"]:
        hs, as_ = states[fx["home"]], states[fx["away"]]
        proj = model.nhl_projection(hs, as_)
        agree_home = _agrees_home(proj)
        markets = model.nhl_markets(fx, proj)
        sample_min = min(hs["gp"], as_["gp"])

        graded = []
        for sel in markets:
            agree = agree_home if sel["market"] in ("moneyline", "handicap") else _agrees(sel, proj)
            g = model.grade(sel, fx, proj, agree, sample_min)
            graded.append({**sel, **g})

        winner = max(
            [g for g in graded if g["market"] == "moneyline"], key=lambda g: g["prob"]
        )
        rows.append(
            {
                "id": fx["id"],
                "sport": "Ice Hockey",
                "sport_slug": "ice-hockey",
                "league": "NHL",
                "competition": fx["competition"],
                "date": fx["date_et"],
                "time": fx["time_et"],
                "time_label": "ET, as published",
                "home": fx["home_name"],
                "away": fx["away_name"],
                "home_abbr": fx["home"],
                "away_abbr": fx["away"],
                "neutral_site": fx["neutral_site"],
                "venue": fx["venue"],
                "source_url": fx["source_url"],
                "source_label": fx["source_label"],
                "extra_sources": [fx["schedule_source"]],
                "source_note": fx["source_note"],
                "inputs": {
                    "home": {
                        "record": hs["record"], "gp": hs["gp"], "gf": hs["gf"], "ga": hs["ga"],
                        "pts": hs["pts"], "l10": hs["l10"], "home": hs["home"], "away": hs["away"],
                        "streak": hs["streak"], "margin_per_game": round(hs["margin_per_game"], 3),
                    },
                    "away": {
                        "record": as_["record"], "gp": as_["gp"], "gf": as_["gf"], "ga": as_["ga"],
                        "pts": as_["pts"], "l10": as_["l10"], "home": as_["home"], "away": as_["away"],
                        "streak": as_["streak"], "margin_per_game": round(as_["margin_per_game"], 3),
                    },
                    "standings_source": nhl_st["source"],
                },
                "projection": {
                    "expected_margin": round(proj["margin"], 3),
                    "p_home_margin_model": round(proj["p_home"], 4),
                    "p_home_winrate_model": round(proj["p_home_winrate"], 4),
                    "expected_home_goals": round(proj["expected_home_goals"], 2),
                    "expected_away_goals": round(proj["expected_away_goals"], 2),
                    "expected_total": round(proj["expected_total"], 2),
                    "sigma_margin": proj["sigma_margin"],
                    "sigma_total": proj["sigma_total"],
                    "models_agree_home": agree_home,
                },
                "winner_pick": winner,
                "markets": graded,
                "high_picks": [g for g in graded if g["confidence"] == "High"],
                "sample_games_min": sample_min,
                "verification": {
                    "status": "official",
                    "checked_utc": "2026-10-22T01:45:00Z",
                    "fixture_source": "https://www.nhl.com/schedule",
                    "rating_source": nhl_st["source"],
                    "player_source": "https://api-web.nhle.com/v1/score/" + fx["date_et"],
                    "note": "Fixture, date and start time read on the NHL.com schedule; records, goals for/against and last-ten form read on the NHL.com standings page; club leaders read from the official NHL game feed. The per-row GameCenter page was not opened individually.",
                },
                "flags": [],
            }
        )

    for fx in mlb["fixtures"]:
        home, away = mlb_st["teams"][fx["home"]], mlb_st["teams"][fx["away"]]
        proj = model.mlb_projection(home, away, fx.get("probable_pitcher"))
        markets = model.mlb_markets(fx, proj)
        sample_min = min(home["gp"], away["gp"])
        graded = []
        for sel in markets:
            agree = _agrees_home(proj) if sel["market"] in ("moneyline", "handicap") else _agrees(sel, proj)
            g = model.grade(sel, fx, proj, agree, sample_min)
            graded.append({**sel, **g})
        winner = max([g for g in graded if g["market"] == "moneyline"], key=lambda g: g["prob"])
        rows.append(
            {
                "id": fx["id"], "sport": "Baseball", "sport_slug": "baseball", "league": "MLB",
                "competition": fx["competition"], "date": fx["date"], "time": "",
                "time_label": "UTC start from official API",
                "start_utc": fx["start_utc"],
                "home": fx["home_name"], "away": fx["away_name"],
                "home_abbr": fx["home"], "away_abbr": fx["away"],
                "neutral_site": False, "venue": fx["venue"],
                "source_url": fx["source_url"], "source_label": fx["source_label"],
                "extra_sources": [fx["api_source"]],
                "source_note": fx["source_note"],
                "description": fx["description"],
                "probable_pitcher": fx.get("probable_pitcher"),
                "inputs": {
                    "home": {"record": f"{home['w']}-{home['l']}", "rs": home["rs"], "ra": home["ra"],
                             "home": home["home"], "away": home["away"], "l10": home["l10"]},
                    "away": {"record": f"{away['w']}-{away['l']}", "rs": away["rs"], "ra": away["ra"],
                             "home": away["home"], "away": away["away"], "l10": away["l10"]},
                    "standings_source": mlb_st["source"],
                    "note": proj["starter_note"],
                },
                "projection": {
                    "expected_margin": round(proj["margin"], 3),
                    "p_home_margin_model": round(proj["p_home"], 4),
                    "expected_total": round(proj["expected_total"], 2),
                    "sigma_margin": proj["sigma_margin"], "sigma_total": proj["sigma_total"],
                },
                "winner_pick": winner,
                "markets": graded,
                "high_picks": [g for g in graded if g["confidence"] == "High"],
                "sample_games_min": sample_min,
                "verification": {
                    "status": "official",
                    "checked_utc": "2026-10-22T01:45:00Z",
                    "fixture_source": fx["api_source"],
                    "rating_source": mlb_st["source"],
                    "note": "Series game, venue, start time and probable pitcher read from the official MLB Stats API; final regular-season records and splits read from the same API's standings endpoint. Postseason results are not modelled.",
                },
                "flags": [],
            }
        )

    # ---- publication rule ------------------------------------------------
    # One headline high-confidence pick per fixture: the strongest in-band High
    # selection on a primary (non-alternate) market. Everything else that graded High
    # stays in the data as a market view but is not published as a pick.
    published: list[dict] = []
    for row in rows:
        # every in-band high-confidence selection we originated, at most one per
        # (fixture, market): the strongest probability of that market
        highs = [h for h in row["high_picks"] if h["in_band"]]
        if not highs:
            continue
        def prio(h):
            # prefer the plainest market first; a pick on the standard line is more
            # useful to a reader than one on an alternate, and the moneyline is the
            # match-winner market the brief asks for first.
            if h["market"] == "moneyline":
                return 0
            if h["market"] == "handicap" and not h["alternate_line"]:
                return 1
            if h["market"] == "total" and not h["alternate_line"]:
                return 2
            if h["market"] == "handicap":
                return 3
            return 4
        best = dict(min(highs, key=lambda h: (prio(h), -h["prob"])))
        best["pick_id"] = f"{row['id']}:{best['market']}:{best['selection']}"
        best["fixture_id"] = row["id"]
        best["match"] = f"{row['away']} at {row['home']}"
        best["sport"] = row["sport"]
        best["league"] = row["league"]
        best["date"] = row["date"]
        best["time"] = row["time"]
        best["source_url"] = row["source_url"]
        best["line_type"] = (
            "alternate" if best.get("alternate_line") else
            ("standard" if best["market"] in ("moneyline", "handicap", "total") else "standard")
        )
        best["market_context"] = {
            "moneyline": {
                "home": next(m for m in row["markets"] if m["market"] == "moneyline" and m["side"] == "home"),
                "away": next(m for m in row["markets"] if m["market"] == "moneyline" and m["side"] == "away"),
            },
            "total_line": next(
                (m["line"] for m in row["markets"] if m["market"] == "total" and not m["alternate_line"]),
                None,
            ),
            "handicap_line": next(
                (m["line"] for m in row["markets"] if m["market"] == "handicap" and not m["alternate_line"]),
                None,
            ),
        }
        published.append(best)
        row["published_pick_id"] = best["pick_id"]

    board = {
        "schema": "board-s/1",
        "generated_by": "deskbot.build",
        "generated_utc": "2026-10-22T02:05:00Z",
        "data_window": "2026-10-22 to 2026-10-28",
        "fixture_window_note": "NHL fixtures cover the four matchdays 22-25 October 2026 as published on NHL.com; "
                               "MLB covers World Series games 1-5, 23-28 October 2026.",
        "constants": model.CONSTANTS,
        "price_band": model.PRICE_BAND,
        "rows": rows,
        "published_high_picks": published,
        "counts": {
            "fixtures": len(rows),
            "by_sport": {
                s: sum(1 for r in rows if r["sport"] == s) for s in sorted({r["sport"] for r in rows})
            },
            "markets_originated": sum(len(r["markets"]) for r in rows),
            "winner_picks": sum(1 for r in rows if r.get("winner_pick")),
            "confidence": {
                level: sum(1 for r in rows if r["winner_pick"]["confidence"] == level)
                for level in ("High", "Medium", "Low")
            },
            "high_market_selections": sum(len(r["high_picks"]) for r in rows),
            "published_high_picks": len(published),
            "fixtures_with_a_published_high_pick": len(published),
            "in_band_high_selections": sum(
                1 for r in rows for m in r["markets"] if m["confidence"] == "High" and m["in_band"]
            ),
            "high_in_band_selections": sum(
                1 for r in rows for m in r["markets"] if m["confidence"] == "High" and m["in_band"]
            ),
            "high_out_of_band_selections": sum(
                1 for r in rows for m in r["markets"] if m["confidence"] == "High" and not m["in_band"]
            ),
            "fixtures_with_published_high_pick": len({p["fixture_id"] for p in published}),
            "medium_or_low_selections": sum(
                1 for r in rows for m in r["markets"] if m["confidence"] != "High"
            ),
        },
    }
    return board


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    board = build()
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / "board.json", "w", encoding="utf-8") as fh:
        json.dump(board, fh, indent=1, ensure_ascii=False)
    summary = {
        "counts": board["counts"],
        "published_high_picks": [
            {
                "pick_id": p["pick_id"], "match": p["match"], "date": p["date"], "market": p["market"],
                "selection": p["selection"], "prob_pct": p["prob_pct"], "american": p["american"],
                "price_decimal": p["price_decimal"], "confidence": p["confidence"],
                "band_status": p["band_status"], "reason": p["high_reason"],
            }
            for p in board["published_high_picks"]
        ],
    }
    with open(DATA / "board_summary.json", "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=1, ensure_ascii=False)
    print(json.dumps(board["counts"], indent=1))
    if args.verbose:
        for p in board["published_high_picks"]:
            print(f'{p["date"]}  {p["match"]:<46} {p["market"]:<9} {p["selection"]:<38} '
                  f'{p["prob_pct"]:>5}%  {p["american"]:>6}  {p["band_status"]}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Offline self-test.

Runs the whole stack against synthetic games with known strengths, so a CI run fails
before ingestion if the model, market builder, prediction writer, verification gate or
site builder is broken. No network access is required.

    python -m pipeline.selftest
"""
from __future__ import annotations

import random
import re
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from . import config, model, predictions, verify
from . import markets as markets_mod
from .build_site import build as build_site
from .records import make_game, make_result

FAILED: list[str] = []


def check(condition: bool, label: str) -> None:
    if condition:
        print(f"PASS  {label}")
    else:
        print(f"FAIL  {label}")
        FAILED.append(label)


def synth_results(sport: str, season: str, start_days_ago: int, n_days: int,
                  strengths: dict[str, float], home_adv: float, base: float,
                  rng: random.Random, now) -> list[dict]:
    out = []
    teams = list(strengths)
    game_id = 0
    for day in range(n_days):
        date = now - timedelta(days=start_days_ago - day)
        for _ in range(2):
            home, away = rng.sample(teams, 2)
            game_id += 1
            home_score = round(
                base + strengths[home] - strengths[away] / 2 + home_adv + rng.gauss(0, 9)
            )
            away_score = round(base + strengths[away] - strengths[home] / 2 + rng.gauss(0, 9))
            out.append(
                make_result(
                    sport=sport,
                    game_id=f"{season}-{game_id}",
                    date_utc=date.strftime("%Y-%m-%dT19:00:00Z"),
                    home_id=home,
                    away_id=away,
                    home_score=max(60, home_score),
                    away_score=max(60, away_score),
                    season=season,
                    source_url=f"https://www.nba.com/games?date={date:%Y-%m-%d}",
                    home_name=f"Home {home}",
                    away_name=f"Away {away}",
                )
            )
    return out


def main() -> int:
    now = config.utc_now()
    rng = random.Random(7)
    strengths = {f"t{i}": float(i * 2) for i in range(1, 11)}
    sport = "basketball"

    prior = synth_results(sport, "2025", 300, 60, strengths, 2.5, 108, rng, now)
    current = synth_results(sport, "2026", 30, 20, strengths, 2.5, 108, rng, now)
    results = prior + current

    fit = model.fit(results, sport, now, kind="current")
    check(fit.games > 150, "model fits the synthetic sample")
    check(fit.team_names.get("t10") is not None, "team names carried into the fit")
    edge = fit.expected("t10", "t1")["margin"] - fit.expected("t1", "t10")["margin"]
    check(edge > 10, "stronger team projects a materially larger margin")

    opening = model.opening_fit(results, sport, now, "2026")
    check(opening.kind == "opening" and opening.games > 50, "opening model uses the prior season")

    fixture = make_game(
        sport=sport,
        league="NBA",
        provider="nba",
        game_id="test-1",
        start_utc=(now + timedelta(days=1)).strftime("%Y-%m-%dT23:30:00Z"),
        home_id="t9",
        home_name="Home t9",
        home_abbr="H9",
        away_id="t2",
        away_name="Away t2",
        away_abbr="A2",
        venue="Test Arena",
        status="Scheduled",
        home_record="40-10",
        away_record="20-30",
        source_urls=["https://www.nba.com/games?date=2026-10-22", "https://cdn.nba.com/x.json"],
    )
    form = predictions.build_form(results, sport, now)
    built = markets_mod.build_markets(fixture, fit, opening, form)
    check(len(built["markets"]) == 3, "three markets built")
    for key, market in built["markets"].items():
        total = sum(s["prob"] for s in market["selections"])
        check(abs(total - 1.0) < 0.01, f"{key} probabilities sum to 1")
        check(all(s["price_decimal"] > 1.0 for s in market["selections"]), f"{key} prices > 1")
    check(built["winner_pick"]["selection"] == "Home t9", "match-winner pick follows the model")
    check(built["winner_pick"]["confidence"] in ("low", "medium", "high"), "confidence graded")

    h2h = predictions.head_to_head(results, "t9", "t2", now)
    pred = predictions.make_prediction(
        fixture, built, form, h2h, ["https://www.nba.com/games?date=2026-10-22"]
    )
    check(len(pred["text"].split()) >= 30, "prediction is at least 30 words")
    check("Selection:" in pred["text"] or "backing" in pred["text"], "prediction names the selection")
    check(len(pred["facts"]) >= 3, "prediction carries source-linked facts")

    # verification gate
    findings = verify.Findings()
    good = dict(fixture)
    bad = dict(fixture)
    bad["id"] = "nba-bad"
    bad["source_urls"] = ["https://example.com/not-official"]
    kept = verify.check_fixtures([good, bad], findings)
    check(len(kept) == 1 and kept[0]["id"] == fixture["id"], "unofficial source row is excluded")
    check(any(f["category"] == "unverified_source" for f in findings.items), "exclusion is flagged")

    rows = [{
        "fixture": kept[0],
        "form": {},
        "h2h": [],
        "analysis": built,
    }]
    rows = verify.check_analysis(rows, findings)
    check(len(rows) == 1, "well-formed analysis row passes")

    pred_rows = [{**pred, "fixture_id": fixture["id"], "selection": built["winner_pick"]["selection"],
                  "match": "Away t2 at Home t9", "sport": sport, "league": "NBA",
                  "confidence": built["winner_pick"]["confidence"],
                  "american": built["winner_pick"]["american"],
                  "prob_pct": built["winner_pick"]["prob_pct"],
                  "start_utc": fixture["start_utc"]}]
    problems = predictions.lint(pred_rows)
    check(not problems, f"prediction lint clean ({problems[:1]})")

    # site build
    with tempfile.TemporaryDirectory() as tmp:
        payload = {
            "fixtures": kept,
            "analysis": rows,
            "predictions": pred_rows,
            "models": {"basketball": {
                "league": "NBA", "current_season": "2026",
                "current": {"games": fit.games, "seasons": ["2026"], "home_advantage": 2.5,
                            "league_total": 216.0, "sigma_margin": 9.0, "sigma_total": 14.0,
                            "n_eff": 100.0, "notes": [], "ratings": model_rows(fit)},
                "opening": {"games": opening.games, "seasons": ["2025"], "kind": "opening",
                            "home_advantage": 2.5, "league_total": 216.0, "notes": ["prior season"]},
                "backtest": {"available": False, "reason": "synthetic"},
            }},
            "flagged": findings.items + [f for f in findings.items],
            "snapshot": {
                "generated_utc": now.isoformat(), "window": {
                    "start": now.strftime("%Y-%m-%dT00:00:00Z"),
                    "end": (now + timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z"),
                    "days": 7},
                "verification": verify.summary(findings, kept, rows, pred_rows),
                "counts": {"fixtures": 1}, "fetch_log": [], "pipeline_version": "selftest",
                "providers": {}, "sports": {}, "excluded_sports": [],
            },
            "taxonomy": None,
        }
        pages = build_site(payload, Path(tmp))
        check("index.html" in pages and "flagged.html" in pages, "site pages generated")
        check((Path(tmp) / "assets" / "site.css").exists(), "stylesheet copied")
        broken = broken_links(Path(tmp))
        check(not broken, f"internal links resolve ({broken[:2]})")
        html = (Path(tmp) / "index.html").read_text()
        check("Official-data line desk" in html, "landing page renders content")

    print()
    if FAILED:
        print(f"{len(FAILED)} check(s) failed")
        return 1
    print("all self-tests passed")
    return 0


def model_rows(fit: model.Fit) -> list[dict]:
    return [
        {"team_id": k, "team": fit.team_names.get(k, k), "rating": round(v, 2),
         "offence": 0.0, "defence": 0.0, "games": fit.games_per_team.get(k, 0)}
        for k, v in fit.ratings.items()
    ]


def broken_links(root: Path) -> list[str]:
    missing = []
    for html_file in root.glob("*.html"):
        text = html_file.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', text):
            if href.startswith(("http://", "https://", "#", "mailto:", "data:")):
                continue
            target = href.split("#")[0]
            if not target:
                continue
            path = root / target
            if not path.exists():
                missing.append(f"{html_file.name} -> {href}")
    return missing


if __name__ == "__main__":
    sys.exit(main())

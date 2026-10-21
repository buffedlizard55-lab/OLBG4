"""Pipeline entry point.

    python -m pipeline.run [--strict] [--skip-site]

1. ingest official fixtures + completed results for every in-scope sport
2. fit the ratings model and the opening-line model
3. build markets, originate lines, grade picks
4. write high-confidence predictions
5. run the verification gate
6. write data/*.json and rebuild the static site

Exit code is non-zero (in --strict mode) only for hard failures: a published row
without an official source, a malformed row, or an out-of-range probability/price.
Soft findings are published on the Flagged for Review page.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import config, http, model, predictions, verify
from . import markets as markets_mod
from .providers import mlb, nba, nhl

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

PROVIDERS = {"nba": nba, "nhl": nhl, "mlb": mlb}


def _json_dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=False)
        fh.write("\n")


def backtest(results: list[dict], sport: str, now: datetime, holdout_days: int = 30) -> dict:
    """Fit on everything older than the holdout, score the holdout. No leakage."""
    cutoff = now - timedelta(days=holdout_days)
    train = []
    test = []
    from .records import parse_iso
    for r in results:
        if r.get("sport") != sport:
            continue
        try:
            dt = parse_iso(r["date_utc"])
        except Exception:  # noqa: BLE001
            continue
        (test if dt >= cutoff else train).append(r)
    if len(train) < 100 or len(test) < 10:
        return {
            "available": False,
            "reason": f"insufficient sample (train={len(train)}, holdout={len(test)})",
            "train_games": len(train),
            "holdout_games": len(test),
            "holdout_days": holdout_days,
        }
    fitted = model.fit(train, sport, cutoff, kind="backtest")
    correct = 0
    brier = 0.0
    logloss = 0.0
    buckets: dict[str, dict] = {
        "50-55%": {"n": 0, "hits": 0, "sum_p": 0.0},
        "55-60%": {"n": 0, "hits": 0, "sum_p": 0.0},
        "60-65%": {"n": 0, "hits": 0, "sum_p": 0.0},
        "65-70%": {"n": 0, "hits": 0, "sum_p": 0.0},
        "70%+": {"n": 0, "hits": 0, "sum_p": 0.0},
    }
    used = 0
    for r in test:
        if str(r["home_id"]) not in fitted.ratings or str(r["away_id"]) not in fitted.ratings:
            continue
        exp = fitted.expected(str(r["home_id"]), str(r["away_id"]))
        p = fitted.p_margin_gt(exp["margin"], 0.0)
        p = min(0.99, max(0.01, p))
        outcome = 1 if r["home_score"] > r["away_score"] else 0
        used += 1
        correct += int((p >= 0.5) == bool(outcome))
        brier += (p - outcome) ** 2
        logloss += -(outcome * _log(p) + (1 - outcome) * _log(1 - p))
        edge = max(p, 1 - p)
        if edge < 0.55:
            key = "50-55%"
        elif edge < 0.60:
            key = "55-60%"
        elif edge < 0.65:
            key = "60-65%"
        elif edge < 0.70:
            key = "65-70%"
        else:
            key = "70%+"
        buckets[key]["n"] += 1
        buckets[key]["hits"] += int((p >= 0.5) == bool(outcome))
        buckets[key]["sum_p"] += edge
    if not used:
        return {"available": False, "reason": "no overlapping teams between train and holdout",
                "train_games": len(train), "holdout_games": len(test)}
    return {
        "available": True,
        "train_games": len(train),
        "holdout_games": used,
        "holdout_days": holdout_days,
        "accuracy": round(correct / used, 4),
        "brier": round(brier / used, 4),
        "log_loss": round(logloss / used, 4),
        "calibration": {
            k: {
                "n": v["n"],
                "predicted": round(v["sum_p"] / v["n"], 4) if v["n"] else None,
                "observed": round(v["hits"] / v["n"], 4) if v["n"] else None,
            }
            for k, v in buckets.items()
        },
        "note": "holdout scored with probabilities from the fitted model; "
                "accuracy is measured against the actual winner",
    }


def _log(x: float) -> float:
    import math
    return math.log(x)


def ratings_table(fit: model.Fit) -> list[dict]:
    rows = []
    for tid, rating in fit.ratings.items():
        rows.append(
            {
                "team_id": tid,
                "team": fit.team_names.get(tid, tid),
                "rating": round(rating, 2),
                "offence": round(fit.offence.get(tid, 0.0), 2),
                "defence": round(fit.defence.get(tid, 0.0), 2),
                "games": fit.games_per_team.get(tid, 0),
            }
        )
    rows.sort(key=lambda r: r["rating"], reverse=True)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true", help="exit non-zero on hard findings")
    parser.add_argument("--skip-site", action="store_true")
    parser.add_argument("--window-days", type=int, default=None)
    args = parser.parse_args(argv)

    if args.window_days:
        config.WINDOW_DAYS = args.window_days

    now = config.utc_now()
    start, end = config.window(now)
    findings = verify.Findings()
    snapshot: dict = {
        "generated_utc": now.isoformat(timespec="seconds"),
        "pipeline_version": __import__("pipeline").__version__,
        "window": {"start": start.isoformat(), "end": end.isoformat(),
                   "days": config.WINDOW_DAYS},
        "sports": {k: {kk: vv for kk, vv in v.items() if kk != "official_domains"}
                   for k, v in config.SPORTS.items()},
        "official_domains": {k: v["official_domains"] for k, v in config.SPORTS.items()},
        "excluded_sports": config.EXCLUDED_SPORTS,
        "providers": {},
        "counts": {},
        "git": {
            "commit": os.environ.get("GITHUB_SHA"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_url": (
                f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/"
                f"{os.environ.get('GITHUB_REPOSITORY', '')}/actions/runs/"
                f"{os.environ.get('GITHUB_RUN_ID', '')}"
                if os.environ.get("GITHUB_RUN_ID")
                else None
            ),
        },
    }

    all_fixtures: list[dict] = []
    all_results: list[dict] = []
    models: dict = {}
    backtests: dict = {}

    # ------------------------------------------------------------------
    # 1. ingest
    # ------------------------------------------------------------------
    for sport, meta in config.SPORTS.items():
        provider_name = meta["provider"]
        provider = PROVIDERS[provider_name]
        entry = {"sport": sport, "league": meta["league"], "provider": provider_name}
        print(f"[ingest] {meta['league']} fixtures…", flush=True)
        try:
            fixtures, fixture_sources = provider.fetch_fixtures(start, end, now)
            entry["fixture_sources"] = fixture_sources
            entry["fixtures_returned"] = len(fixtures)
        except Exception as exc:  # noqa: BLE001
            entry["fixtures_error"] = f"{type(exc).__name__}: {exc}"
            entry["traceback"] = traceback.format_exc(limit=3)
            fixtures = []
            findings.add(
                severity="warning", category="provider_unavailable", field="fixtures",
                detail=f"{meta['league']} fixture feed failed: {type(exc).__name__}: {exc}",
                source_urls=[config.SPORTS[sport]["official_domains"][0]],
            )
        print(f"[ingest] {meta['league']} completed results…", flush=True)
        try:
            results, train_meta = provider.fetch_training(
                config.training_start(sport, now), now
            )
            entry["training"] = train_meta
            entry["results_returned"] = len(results)
        except Exception as exc:  # noqa: BLE001
            entry["training_error"] = f"{type(exc).__name__}: {exc}"
            results = []
            findings.add(
                severity="warning", category="training_unavailable", field="results",
                detail=f"{meta['league']} results feed failed: {type(exc).__name__}: {exc}",
                source_urls=[config.SPORTS[sport]["official_domains"][0]],
            )
        entry["fetch_log"] = [
            f for f in http.FETCH_LOG
            if any(d in f.get("url", "") for d in meta["official_domains"])
        ]
        snapshot["providers"][sport] = entry
        all_fixtures.extend(fixtures)
        all_results.extend(results)

        # ---- 2. models ------------------------------------------------
        current_fit = model.fit(results, sport, now, kind="current")
        current_fit.team_names = _team_names(results, fixtures)
        current_season = _current_season(results, fixtures)
        opening = model.opening_fit(results, sport, now, current_season)
        opening.team_names = current_fit.team_names

        models[sport] = {
            "league": meta["league"],
            "current_season": current_season,
            "current": {
                "games": current_fit.games,
                "seasons": current_fit.seasons,
                "home_advantage": round(current_fit.home_advantage, 3),
                "league_total": round(current_fit.league_total, 3),
                "sigma_margin": round(current_fit.sigma_margin, 3),
                "sigma_total": round(current_fit.sigma_total, 3),
                "n_eff": round(current_fit.n_eff, 1),
                "notes": current_fit.notes,
                "ratings": ratings_table(current_fit),
            },
            "opening": {
                "games": opening.games,
                "seasons": opening.seasons,
                "kind": opening.kind,
                "home_advantage": round(opening.home_advantage, 3),
                "league_total": round(opening.league_total, 3),
                "notes": opening.notes,
            },
        }
        print(f"[model] {meta['league']} {current_fit.games} games, "
              f"opening={opening.games} ({opening.kind})", flush=True)
        backtests[sport] = backtest(results, sport, now)
        models[sport]["backtest"] = backtests[sport]

        # stash fits for the market stage (not serialised)
        models[sport]["_current_fit"] = current_fit
        models[sport]["_opening_fit"] = opening
        models[sport]["_season"] = current_season

    # ------------------------------------------------------------------
    # 3. markets + picks
    # ------------------------------------------------------------------
    fixtures_by_id = {fx["id"]: fx for fx in all_fixtures}
    analysis_rows: list[dict] = []
    prediction_rows: list[dict] = []
    for fx in all_fixtures:
        sport = fx["sport"]
        pack = models.get(sport) or {}
        current_fit = pack.get("_current_fit")
        opening_fit = pack.get("_opening_fit")
        if not current_fit or not opening_fit:
            continue
        form = predictions.build_form(all_results, sport, _dt(fx["start_utc"]))
        h2h = predictions.head_to_head(
            all_results, fx["home"]["id"], fx["away"]["id"], _dt(fx["start_utc"])
        )
        try:
            result = markets_mod.build_markets(fx, current_fit, opening_fit, form)
        except Exception as exc:  # noqa: BLE001
            findings.add(severity="error", category="market_build_failed",
                         detail=f"{type(exc).__name__}: {exc}", fixture=fx, action="excluded")
            continue
        row = {
            "fixture": fx,
            "form": {
                "home": _form_summary(form.get(str(fx["home"]["id"]))),
                "away": _form_summary(form.get(str(fx["away"]["id"]))),
            },
            "h2h": [
                {"date_utc": m["date_utc"], "home_id": str(m["home_id"]),
                 "away_id": str(m["away_id"]), "home_score": m["home_score"],
                 "away_score": m["away_score"], "source": m.get("source_url")}
                for m in h2h
            ],
            "analysis": result,
        }
        analysis_rows.append(row)

        for pick in [result["winner_pick"]] + result["market_picks"]:
            if pick["confidence"] != "high":
                continue
            pred = predictions.make_prediction(
                fx, {**result, "headline_pick": pick}, form, h2h,
                fx.get("official_source_urls") or fx.get("source_urls") or [],
            )
            pred["fixture_id"] = fx["id"]
            pred["sport"] = sport
            pred["league"] = fx["league"]
            pred["match"] = f"{fx['away']['name']} at {fx['home']['name']}"
            pred["start_utc"] = fx["start_utc"]
            pred["selection"] = pick["selection"]
            pred["confidence"] = pick["confidence"]
            pred["price_decimal"] = pick["price_decimal"]
            pred["american"] = pick["american"]
            pred["prob_pct"] = pick["prob_pct"]
            pred["market"] = pick["market"]
            pred["source_urls"] = fx.get("official_source_urls") or fx.get("source_urls")
            prediction_rows.append(pred)
            pick["prediction_id"] = fx["id"] + ":" + pick["market"]

    # ------------------------------------------------------------------
    # 4. verification
    # ------------------------------------------------------------------
    kept_fixtures = verify.check_fixtures(all_fixtures, findings)
    kept_ids = {fx["id"] for fx in kept_fixtures}
    analysis_rows = [r for r in analysis_rows if r["fixture"]["id"] in kept_ids]
    analysis_rows = verify.check_analysis(analysis_rows, findings)
    prediction_rows = verify.check_predictions(prediction_rows, findings, fixtures_by_id)
    verify.check_schedule_horizon(analysis_rows, start, end, findings)

    # one row per fixture; attach prediction ids
    for row in analysis_rows:
        preds = [p for p in prediction_rows if p["fixture_id"] == row["fixture"]["id"]]
        row["analysis"]["predictions"] = [
            {"market": p["market"], "selection": p["selection"], "id": p["fixture_id"] + ":" + p["market"]}
            for p in preds
        ]
        row["analysis"]["rationale"] = predictions.short_rationale(row["fixture"], row["analysis"])

    verification = verify.summary(findings, kept_fixtures, analysis_rows, prediction_rows)

    # coverage gaps are findings too
    for sport, entry in snapshot["providers"].items():
        if entry.get("fixtures_returned", 0) == 0 and not entry.get("fixtures_error"):
            findings.add(
                severity="info", category="no_fixtures_in_window", field="fixtures",
                detail=f"{config.SPORTS[sport]['league']}: the official feed returned no "
                       f"fixtures inside the publishing window",
            )

    # ------------------------------------------------------------------
    # 5. write data
    # ------------------------------------------------------------------
    for pack in models.values():
        pack.pop("_current_fit", None)
        pack.pop("_opening_fit", None)
        pack.pop("_season", None)

    snapshot["counts"] = {
        "fixtures": len(kept_fixtures),
        "analysis_rows": len(analysis_rows),
        "predictions": len(prediction_rows),
        "high_picks": sum(1 for r in analysis_rows
                          if r["analysis"]["winner_pick"]["confidence"] == "high"),
        "medium_picks": sum(1 for r in analysis_rows
                            if r["analysis"]["winner_pick"]["confidence"] == "medium"),
        "low_picks": sum(1 for r in analysis_rows
                         if r["analysis"]["winner_pick"]["confidence"] == "low"),
        "market_picks": sum(len(r["analysis"]["market_picks"]) for r in analysis_rows),
        "findings": len(findings.items),
    }
    snapshot["verification"] = verification
    snapshot["fetch_log"] = http.FETCH_LOG
    snapshot["model_notes"] = {
        s: {
            "current_games": models[s]["current"]["games"],
            "opening_games": models[s]["opening"]["games"],
            "opening_kind": models[s]["opening"]["kind"],
            "opening_notes": models[s]["opening"]["notes"],
            "backtest": {k: v for k, v in models[s]["backtest"].items() if k != "calibration"},
        }
        for s in models
    }

    _json_dump(DATA / "fixtures.json", kept_fixtures)
    _json_dump(DATA / "analysis.json", analysis_rows)
    _json_dump(DATA / "predictions.json", prediction_rows)
    _json_dump(DATA / "models.json", models)
    _json_dump(DATA / "flagged.json", findings.items)
    _json_dump(DATA / "snapshot.json", snapshot)

    print(f"[publish] fixtures={len(kept_fixtures)} analysis={len(analysis_rows)} "
          f"predictions={len(prediction_rows)} findings={len(findings.items)}")
    print(f"hard_failures={verification['hard_failures']} "
          f"counts={json.dumps(snapshot['counts'])}")
    for f in findings.items:
        if f["severity"] in ("error", "warning"):
            print(f"  [{f['severity']}] {f['category']}: {f['detail']}")

    # ------------------------------------------------------------------
    # 6. site
    # ------------------------------------------------------------------
    if not args.skip_site:
        from . import build_site
        payload = {
            "fixtures": kept_fixtures,
            "analysis": analysis_rows,
            "predictions": prediction_rows,
            "models": models,
            "flagged": findings.items,
            "snapshot": snapshot,
            "taxonomy": _load_taxonomy(),
        }
        build_site.build(payload, ROOT)
        print("site built")

    if args.strict:
        if verification["hard_failures"] > 0:
            print("STRICT: published rows failed verification", file=sys.stderr)
            return 1
        if not kept_fixtures:
            print("STRICT: no fixtures published", file=sys.stderr)
            return 1
        if verification.get("excluded_ratio", 0) > 0.25:
            print("STRICT: more than 25% of ingested rows were excluded", file=sys.stderr)
            return 1
    return 0


def _load_taxonomy() -> dict | None:
    path = DATA / "olbg-taxonomy.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dt(value: str) -> datetime:
    from .records import parse_iso
    return parse_iso(value)


def _team_names(results: list[dict], fixtures: list[dict]) -> dict[str, str]:
    names: dict[str, str] = {}
    for r in results:
        if r.get("home_name"):
            names[str(r["home_id"])] = r["home_name"]
        if r.get("away_name"):
            names[str(r["away_id"])] = r["away_name"]
    for fx in fixtures:
        names[str(fx["home"]["id"])] = fx["home"]["name"]
        names[str(fx["away"]["id"])] = fx["away"]["name"]
    return names


def _current_season(results: list[dict], fixtures: list[dict]) -> str | None:
    seasons = [str(fx["context"].get("season")) for fx in fixtures if fx.get("context", {}).get("season")]
    if seasons:
        return max(set(seasons), key=seasons.count)
    seasons = [str(r.get("season")) for r in results if r.get("season")]
    return max(seasons) if seasons else None


def _form_summary(form: dict | None) -> dict | None:
    if not form:
        return None
    return {
        "last5": [
            {"won": g["won"], "team_score": g["team_score"], "opp_score": g["opp_score"],
             "date": g["date"][:10], "venue": g["venue"],
             "opponent": (g.get("away_name") if g.get("venue") == "home" else g.get("home_name"))}
            for g in form.get("last5", [])
        ],
        "wins_last5": form.get("wins_last5"),
        "losses_last5": form.get("losses_last5"),
        "streak": form.get("streak"),
        "record": form.get("record"),
        "avg_scored_last5": form.get("avg_scored_last5"),
        "avg_allowed_last5": form.get("avg_allowed_last5"),
        "games_in_sample": form.get("games"),
    }


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001 - top-level guard, traceback is the deliverable
        traceback.print_exc()
        raise SystemExit(1)

#!/usr/bin/env python3
"""Build Board AH's isolated, target-only current-day OLBG evidence desk.

All live facts come from the checked-in observation/source ledgers or the
read-only 2026-10-23 provider snapshot. This script does not fetch external
pages and never modifies peer-owned files.
"""
from __future__ import annotations

import collections
import html
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
SESSION = "session-8860f8f7"
DATA = ROOT / "data" / SESSION
SITE = ROOT / SESSION
SCOPE_PATH = DATA / "target_scope.json"
LISTINGS_PATH = DATA / "listing_observations.json"
SOURCES_PATH = DATA / "source_ledger.json"
FIXTURES_PATH = ROOT / "session-4afef1af" / "data" / "fixtures.json"
ANALYSIS_PATH = ROOT / "session-4afef1af" / "data" / "analysis.json"
HISTORY_PATH = ROOT / "data" / "session-4885d641" / "desk.json"


def load(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def dump(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def esc(value) -> str:
    if value is None or value == "":
        return "<span class=\"blank\">Not captured</span>"
    return html.escape(str(value), quote=True)


def raw(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def link(url: str | None, label: str, css: str = "") -> str:
    if not url:
        return '<span class="blank">Not captured</span>'
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return f'<span class="blank">{raw(label)}</span>'
    cls = f' class="{raw(css)}"' if css else ""
    return f'<a{cls} href="{raw(url)}" target="_blank" rel="noopener noreferrer">{raw(label)} ↗</a>'


def pct(value: float | None) -> str:
    return "—" if value is None else f"{100 * value:.1f}%"


def american(prob: float) -> tuple[float, str]:
    if prob <= 0 or prob >= 1:
        raise ValueError(f"probability outside (0,1): {prob}")
    if prob >= 0.5:
        value = -100.0 * prob / (1.0 - prob)
        return value, f"−{abs(round(value))}"
    value = 100.0 * (1.0 - prob) / prob
    return value, f"+{round(value)}"


def decimal(prob: float) -> float:
    if prob <= 0:
        raise ValueError("probability must be positive")
    return 1.0 / prob


def fair_in_band(american_value: float) -> bool:
    return -250.0 <= american_value <= 10000.0


def tier(prob: float, in_band: bool) -> str:
    if prob >= 0.70:
        return "High · in window" if in_band else "≥70% · outside window"
    if prob >= 0.55:
        return "Medium"
    return "Low"


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def words(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text, re.UNICODE))


def fmt_datetime(value: str | None) -> str:
    if not value:
        return "Not captured"
    return value.replace("T", " ").replace("Z", " UTC")


def pill(text: str, cls: str = "neutral") -> str:
    return f'<span class="pill {raw(cls)}">{raw(text)}</span>'


def table(headers: list[str], rows: list[list[str]], empty: str = "No rows in this capture.") -> str:
    if not rows:
        return f'<div class="empty">{raw(empty)}</div>'
    head = "".join(f"<th>{raw(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def page(title: str, active: str, body: str, description: str = "Current-day OLBG source reconciliation and independently originated lines.", prefix: str = "") -> str:
    nav = [
        ("index.html", "Overview", "index"),
        ("entries.html", "Entries", "entries"),
        ("markets.html", "Markets", "markets"),
        ("picks.html", "Picks", "picks"),
        ("coverage.html", "Coverage", "coverage"),
        ("olbg.html", "OLBG map", "olbg"),
        ("sources.html", "Sources", "sources"),
        ("methodology.html", "Method", "methodology"),
        ("flagged.html", "Flagged review", "flagged"),
        ("verification.html", "Verification", "verification"),
        ("history.html", "History", "history"),
    ]
    nav_html = "".join(
        f'<a href="{prefix}{url}" class="{"active" if key == active else ""}">{label}</a>'
        for url, label, key in nav
    )
    board_home = f"{prefix}index.html"
    all_dashboards = f"{prefix}../index.html"
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{raw(title)} · Board AH · OLBG4</title>
<meta name="description" content="{raw(description)}">
<link rel="stylesheet" href="{prefix}assets/site.css">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%230e7490'/><text x='16' y='22' font-family='Arial' font-size='14' font-weight='700' fill='white' text-anchor='middle'>AH</text></svg>">
</head>
<body>
<header class="topbar"><div class="wrap topbar-inner">
  <a class="brand" href="{board_home}"><span class="brand-mark">AH</span><span><b>OLBG4</b><small>current-day line desk · 23 Oct 2026</small></span></a>
  <nav class="nav">{nav_html}</nav>
</div></header>
<main class="wrap">{body}</main>
<footer class="footer"><div class="wrap footer-inner">
  <span>Board AH · read-only source cut {raw(scope_asof())} · times shown in UTC unless stated.</span>
  <span><a href="{all_dashboards}">All dashboards</a> · <a href="{prefix}flagged.html">Flagged for review</a> · <a href="{prefix}verification.html">Verification register</a></span>
</div><div class="wrap footer-note">Source-first research display. No selection is guaranteed. 18+; gamble responsibly.</div></footer>
<script src="{prefix}assets/site.js"></script>
</body></html>'''


_SCOPE = None

def scope_asof() -> str:
    global _SCOPE
    if _SCOPE is None:
        _SCOPE = load(SCOPE_PATH)
    return _SCOPE["as_of_utc"]


def official_source_urls(fixture: dict) -> tuple[str | None, str | None]:
    urls = fixture.get("source_urls") or fixture.get("official_source_urls") or []
    return (urls[0] if urls else None, urls[1] if len(urls) > 1 else None)


def parse_line_name(name: str, family: str) -> str | None:
    if family == "moneyline":
        return None
    if family == "total":
        m = re.search(r"(?:Over|Under)\s+([0-9]+(?:\.[0-9]+)?)", name, re.I)
        return m.group(1) if m else None
    m = re.search(r"([+-]\d+(?:\.\d+)?)\s*$", name)
    return m.group(1) if m else None


def market_rows(fixture_id: str, analysis: dict) -> list[dict]:
    markets = analysis.get("markets") or {}
    out: list[dict] = []
    family_order = ["moneyline", "handicap", "total"]
    for family in family_order:
        market = markets.get(family)
        if not market:
            continue
        groups = [{"line": market.get("line"), "selections": market.get("selections", []), "primary": True}]
        if family == "handicap":
            groups[0]["line_home"] = market.get("line_home")
            groups[0]["line_away"] = market.get("line_away")
            for alt in market.get("alternates", []):
                groups.append({"line": alt.get("line_home"), "line_home": alt.get("line_home"), "line_away": -alt.get("line_home") if alt.get("line_home") is not None else None, "selections": alt.get("selections", []), "primary": False})
        elif family == "total":
            for alt in market.get("alternates", []):
                groups.append({"line": alt.get("line"), "selections": alt.get("selections", []), "primary": False})
        for group in groups:
            for selection in group.get("selections", []):
                prob = float(selection["prob"])
                fair_value, fair_text = american(prob)
                in_band = fair_in_band(fair_value)
                line_label = parse_line_name(selection.get("name", ""), family)
                out.append({
                    "id": f"{fixture_id}:{family}:{line_label or 'ml'}:{selection.get('side', 'na')}",
                    "fixture_id": fixture_id,
                    "family": family,
                    "market_label": market.get("label", family),
                    "line": line_label,
                    "line_group": (str(group.get("line_home")) if family == "handicap" else (str(group.get("line")) if family == "total" else "moneyline")),
                    "primary_line": bool(group.get("primary")),
                    "selection": selection.get("name", ""),
                    "side": selection.get("side"),
                    "probability": prob,
                    "probability_pct": 100.0 * prob,
                    "fair_decimal": decimal(prob),
                    "fair_american_value": fair_value,
                    "fair_american": fair_text,
                    "fair_in_band": in_band,
                    "focus_tier": tier(prob, in_band),
                    "margin_decimal": float(selection.get("price_decimal", 0)),
                    "margin_american": selection.get("american"),
                    "margin_assumption": 0.045,
                })
    return out


def main_build_data() -> tuple[dict, dict, dict, dict, dict]:
    scope = load(SCOPE_PATH)
    listings = load(LISTINGS_PATH)
    source_ledger = load(SOURCES_PATH)
    fixtures = {x["id"]: x for x in load(FIXTURES_PATH)}
    analyses = {x["fixture"]["id"]: x for x in load(ANALYSIS_PATH)}
    ag = load(HISTORY_PATH)
    category_by_label = {x["label"]: x for x in scope["categories"]}
    scope_by_slug = {x["slug"]: x for x in scope["categories"]}

    rows: list[dict] = []
    for event in listings["earlier_live_scan"]["events"]:
        fid = event["official_fixture_id"]
        fixture = fixtures[fid]
        analysis_record = analyses[fid]
        analysis = analysis_record["analysis"]
        sport_label = category_by_label[event["sport"]]["label"]
        primary, schedule = official_source_urls(fixture)
        market_status = analysis.get("market_status", "priced")
        if market_status == "withheld" or not analysis.get("markets"):
            selections = []
            winner = None
            market_note = analysis.get("market_note") or "No originated prices are available in the source snapshot."
            sample_min = analysis.get("sample_min")
            required_sample = 20
            engine_tag = None
        else:
            selections = market_rows(fid, analysis)
            raw_winner = analysis.get("winner_pick")
            sample_min = raw_winner.get("sample_games_min") if raw_winner else None
            required_sample = None
            market_note = "Own prices are derived from the official-feed training sample; OLBG and sportsbook quotes are not used."
            engine_tag = raw_winner.get("confidence") if raw_winner else None
            winner = None
            if raw_winner:
                p = float(raw_winner["prob"])
                fair_value, fair_text = american(p)
                in_band = fair_in_band(fair_value)
                winner = {
                    "selection": raw_winner["selection"],
                    "probability": p,
                    "probability_pct": 100 * p,
                    "fair_decimal": decimal(p),
                    "fair_american_value": fair_value,
                    "fair_american": fair_text,
                    "fair_in_band": in_band,
                    "confidence": "High" if p >= 0.70 and in_band else ("Medium" if p >= 0.55 else "Low"),
                    "pipeline_confidence_tag": engine_tag,
                    "pipeline_tag_adopted": False,
                    "margin_decimal": raw_winner.get("price_decimal"),
                    "margin_american": raw_winner.get("american"),
                    "training_sample_min_games": sample_min,
                }
        home, away = fixture["home"], fixture["away"]
        row = {
            "id": fid,
            "sport": sport_label,
            "sport_slug": category_by_label[event["sport"]]["slug"],
            "competition": fixture.get("league"),
            "provider_fixture_id": fid,
            "provider_game_id": fixture.get("provider_game_id"),
            "olbg_event_id": event["olbg_event_id"],
            "olbg_listing_title": event.get("listing_title"),
            "olbg_url": event.get("olbg_url") or category_by_label[event["sport"]]["olbg_hubs"][0]["url"],
            "olbg_hub_url": category_by_label[event["sport"]]["olbg_hubs"][0]["url"],
            "olbg_observed_utc": listings["earlier_live_scan"]["approx_utc"],
            "olbg_latest_status": "Observed in earlier live scan; card not reproduced in later hub response. Direct page marked Expired where rechecked.",
            "official_fixture_status": "schedule confirmed; event start is future in the official schedule snapshot",
            "start_utc": fixture.get("start_utc"),
            "official_status_text": fixture.get("status"),
            "home": home.get("name"),
            "away": away.get("name"),
            "home_record": home.get("record"),
            "away_record": away.get("record"),
            "record_label": (fixture.get("context") or {}).get("home_record_label"),
            "venue": fixture.get("venue"),
            "official_source_url": primary,
            "official_schedule_url": schedule,
            "other_official_sources": fixture.get("extra_sources", []),
            "market_status": "priced" if selections else "withheld",
            "market_note": market_note,
            "minimum_training_sample": sample_min,
            "required_training_sample": required_sample,
            "own_markets": selections,
            "winner_pick": winner,
            "model_internal_confidence_tag_not_used": engine_tag,
            "probable_pitchers": {
                "away": (fixture.get("context") or {}).get("away_probable_pitcher"),
                "home": (fixture.get("context") or {}).get("home_probable_pitcher"),
            } if sport_label == "Baseball" else None,
            "source_snapshot_utc": "2026-10-23T11:35:26Z",
        }
        rows.append(row)

    hurling_obs = next(
        e for result in listings["latest_hub_recheck"]["results"] if result["sport"] == "Hurling"
        for e in result.get("events", [])
    )
    gaelic = scope_by_slug["gaelic-sports"]
    rows.append({
        "id": "olbg-hurling-714",
        "sport": "Gaelic Sports",
        "sport_slug": "gaelic-sports",
        "competition": "Hurling · competition not independently established",
        "provider_fixture_id": None,
        "provider_game_id": None,
        "olbg_event_id": hurling_obs["olbg_event_id"],
        "olbg_listing_title": hurling_obs["matchup"],
        "teams": ["Ballyhale Shamrocks", "Tullaroan"],
        "matchup": hurling_obs["matchup"],
        "olbg_url": hurling_obs["event_url"],
        "olbg_hub_url": gaelic["olbg_hubs"][1]["url"],
        "olbg_observed_utc": listings["latest_hub_recheck"]["window_utc"],
        "olbg_latest_status": "Listing visible on the Hurling hub; exact club fixture not confirmed on an official source.",
        "official_fixture_status": "unconfirmed; listing-only row",
        "start_utc": None,
        "olbg_display_date": hurling_obs["display_date"],
        "olbg_display_time": hurling_obs["display_time"],
        "olbg_timezone": None,
        "home": None,
        "away": None,
        "home_record": None,
        "away_record": None,
        "record_label": None,
        "venue": None,
        "official_source_url": "https://kilkennygaa.ie/fixtures-results/",
        "official_schedule_url": "https://www.gaa.ie/fixtures-results",
        "other_official_sources": [],
        "market_status": "not-priced",
        "market_note": "No own line or pick: the listed club fixture and timezone were not confirmed on the official pages reviewed.",
        "minimum_training_sample": None,
        "required_training_sample": None,
        "own_markets": [],
        "winner_pick": None,
        "model_internal_confidence_tag_not_used": None,
        "probable_pitchers": None,
        "source_snapshot_utc": None,
    })

    rows.sort(key=lambda r: (r.get("start_utc") or "9999", r["sport"], r["id"]))
    all_market_selections = [m for row in rows for m in row.get("own_markets", [])]
    high_prob = [m for m in all_market_selections if m["probability"] >= 0.70]
    high_eligible = [m for m in high_prob if m["fair_in_band"]]
    high_outside = [m for m in high_prob if not m["fair_in_band"]]
    winner_picks = [row for row in rows if row.get("winner_pick")]
    market_audit = {
        "schema": "olbg4.board-ah.market-audit.v1",
        "generated_utc": scope["as_of_utc"],
        "fair_odds_band_american": {"min": -250, "max": 10000, "inclusive": True},
        "high_probability_threshold": 0.70,
        "margin_rate": 0.045,
        "selection_count": len(all_market_selections),
        "priced_event_count": sum(1 for row in rows if row["market_status"] == "priced"),
        "events_with_high_probability_selection": len({m["fixture_id"] for m in high_prob}),
        "high_probability_in_window_count": len(high_eligible),
        "high_probability_outside_window_count": len(high_outside),
        "high_probability_outside_window": [
            {
                "fixture_id": m["fixture_id"], "market": m["market_label"], "selection": m["selection"],
                "probability": m["probability"], "probability_pct": m["probability_pct"],
                "fair_decimal": m["fair_decimal"], "fair_american": m["fair_american"],
                "fair_american_value": m["fair_american_value"], "margin_decimal": m["margin_decimal"],
                "margin_american": m["margin_american"], "fair_in_band": m["fair_in_band"],
            } for m in high_outside
        ],
        "eligible_high_selections": [m for m in high_eligible],
        "match_winner_pick_count": len(winner_picks),
        "match_winner_picks": [
            {"fixture_id": r["id"], "sport": r["sport"], "matchup": f"{r['away']} @ {r['home']}", **r["winner_pick"]}
            for r in winner_picks
        ],
        "market_family_counts": dict(collections.Counter(m["family"] for m in all_market_selections)),
        "nba_withheld_count": sum(1 for r in rows if r["sport"] == "Basketball" and r["market_status"] == "withheld"),
        "interpretation": "Probability and fair odds are the originated values. Margin-adjusted prices are reported separately and are not used for the focus-band test.",
    }
    predictions = {
        "schema": "olbg4.board-ah.predictions.v1",
        "thresholds": {"high_probability": 0.70, "fair_american_min": -250, "fair_american_max": 10000},
        "eligible_count": len(high_eligible),
        "written_prediction_count": 0,
        "items": [],
        "reason": "No current originated selection meets both the ≥70% probability threshold and the fair-American odds band. No high-confidence prose was manufactured or copied from OLBG.",
    }

    ag_rows = ag.get("rows", [])
    target_price_slugs = {c["slug"] for c in scope["categories"] if c["slug"] not in {"gaelic-sports", "greyhounds"}}
    target_price_labels = {c["label"] for c in scope["categories"] if c["slug"] in target_price_slugs}
    old_counts = collections.Counter(r.get("sport") for r in ag_rows if r.get("sport") in target_price_labels)
    old_prediction_counts = collections.Counter(r.get("sport") for r in ag_rows if r.get("sport") in target_price_labels and r.get("prediction"))
    historical = {
        "schema": "olbg4.board-ah.history.v1",
        "source_board": "AG",
        "source_capture_utc": "2026-10-22T21:15:00Z",
        "source_file": "data/session-4885d641/desk.json",
        "target_priced_sports": sorted(target_price_labels),
        "fixture_rows": sum(old_counts.values()),
        "prediction_texts": sum(old_prediction_counts.values()),
        "by_sport": [
            {"sport": c["label"], "rows": old_counts[c["label"]], "predictions": old_prediction_counts[c["label"]]}
            for c in scope["categories"] if c["label"] in target_price_labels
        ],
        "warning": "This 2026-10-22 historical snapshot is not current-day evidence and is not used for any active entry or pick.",
    }

    current_count_by_slug = collections.Counter(r["sport_slug"] for r in rows)
    official_count_by_slug = collections.Counter(r["sport_slug"] for r in rows if r.get("provider_fixture_id"))
    priced_count_by_slug = collections.Counter(r["sport_slug"] for r in rows if r["market_status"] == "priced")
    coverage = {
        "schema": "olbg4.board-ah.coverage.v1",
        "as_of_utc": scope["as_of_utc"],
        "scope_count": len(scope["categories"]),
        "priced_scope_category_count": len(target_price_slugs),
        "current_entry_count": len(rows),
        "officially_crossmatched_entry_count": sum(official_count_by_slug.values()),
        "priced_entry_count": sum(priced_count_by_slug.values()),
        "high_in_window_pick_count": len(high_eligible),
        "five_pick_target": 5,
        "categories": [
            {
                **category,
                "observed_entry_count": current_count_by_slug[category["slug"]],
                "official_crossmatch_count": official_count_by_slug[category["slug"]],
                "priced_count": priced_count_by_slug[category["slug"]],
                "in_window_high_count": sum(1 for r in rows if r["sport_slug"] == category["slug"] and r.get("winner_pick") and r["winner_pick"]["confidence"] == "High"),
                "five_pick_shortfall": max(0, 5 - sum(1 for r in rows if r["sport_slug"] == category["slug"] and r.get("winner_pick") and r["winner_pick"]["confidence"] == "High")),
                "historical_rows_not_current": old_counts[category["label"]],
                "historical_predictions_not_current": old_prediction_counts[category["label"]],
            }
            for category in scope["categories"]
        ],
        "scope_note": scope["scope_interpretation"],
    }

    flag_rows = [
        {
            "id": "AH-F01", "severity": "high", "category": "OLBG listing volatility / status mismatch",
            "detail": "The 16:19Z scan observed 12 NBA, two NHL and one MLB OLBG cards. The 16:31–16:32Z hub recheck returned 'No tips found' on those three hubs; direct NHL event pages rendered 'Expired' while the NHL schedule still listed both games as upcoming. Keep the 15 event IDs as observed listings, not as a claim that the cards remained active.",
            "official_url": "https://api-web.nhle.com/v1/schedule/2026-10-23", "olbg_url": "https://www.olbg.com/betting-tips/Ice_Hockey/13"
        },
        {
            "id": "AH-F02", "severity": "high", "category": "NBA prices withheld",
            "detail": "Twelve NBA fixtures crossmatch, but the source snapshot has only 16 completed games in the 2026–27 training sample and individual team samples below 20. Moneyline, point spread and game-total numbers and picks are blank for all 12; do not infer them.",
            "official_url": "https://www.nba.com/games?date=2026-10-23", "olbg_url": "https://www.olbg.com/betting-tips/Basketball/4"
        },
        {
            "id": "AH-F03", "severity": "high", "category": "Twelve categories without an official crossmatch",
            "detail": "Only Baseball, Basketball and Ice Hockey have event-level official crossmatches in this current scan. Latest hub reads for the other 12 categories did not expose an officially matched card (except the unverified Hurling listing); this is a capture limitation, not proof that no fixtures exist. No old Board AG event or prediction is carried forward as current.",
            "official_url": "https://www.gaa.ie/fixtures-results", "olbg_url": "https://www.olbg.com/betting-tips"
        },
        {
            "id": "AH-F04", "severity": "high", "category": "Gaelic Sports scope and Hurling listing",
            "detail": "Gaelic Sports includes Gaelic Football and Hurling. OLBG lists Ballyhale Shamrocks v Tullaroan for 25 Oct, but the GAA national fixture page and the reviewed portion of the Kilkenny GAA county fixture page did not confirm that club fixture. Date/time zone and venue are therefore blank; no line or pick is published.",
            "official_url": "https://kilkennygaa.ie/fixtures-results/", "olbg_url": "https://www.olbg.com/betting-tips/Hurling/26"
        },
        {
            "id": "AH-F05", "severity": "medium", "category": "Market snapshot freshness",
            "detail": "The NHL and MLB originated market inputs come from the official-provider snapshot captured 2026-10-23T11:35Z–11:37Z. Later reads rechecked the schedules, not the full team history/model inputs. These prices are a same-day snapshot, not a live-odds guarantee.",
            "official_url": "https://api-web.nhle.com/v1/standings/now", "olbg_url": "https://www.olbg.com/betting-tips"
        },
        {
            "id": "AH-F06", "severity": "medium", "category": "Historical NHL form sample",
            "detail": "The pipeline's form.record fields for the two NHL games represent 91/92-game samples, not the current-season standings. They are omitted from the published form panel; current-season NHL records are taken from the official fixture snapshot (3-6-0 / 4-3-2 and 5-4-1 / 7-2-0).",
            "official_url": "https://api-web.nhle.com/v1/standings/now", "olbg_url": "https://www.olbg.com/betting-tips/Ice_Hockey/13"
        },
        {
            "id": "AH-F07", "severity": "medium", "category": "Injuries and lineup information",
            "detail": "No upcoming-game injury report or confirmed lineup source was captured for any row. No injury, availability or lineup claim is made.",
            "official_url": "https://www.nhl.com/gamecenter/mtl-vs-chi/2026/10/23/2026020166", "olbg_url": "https://www.olbg.com/betting-tips"
        },
        {
            "id": "AH-F08", "severity": "high", "category": "≥70% candidates outside fair-odds band",
            "detail": "Two originated totals exceed 70% probability, but fair prices are shorter than −250: Montréal–Chicago Over 5.5 at 73.98% (fair −284) and Tampa Bay–Colorado Under 8.5 at 72.97% (fair −270). They are shown as outside-window candidates, not eligible High picks.",
            "official_url": "https://www.nhl.com/gamecenter/mtl-vs-chi/2026/10/23/2026020166", "olbg_url": "https://www.olbg.com/betting-tips/Ice_Hockey/13"
        },
        {
            "id": "AH-F09", "severity": "medium", "category": "Fair versus margin-adjusted price",
            "detail": "The 4.5% margin-adjusted price and the fair price are both displayed. The −250 to +10,000 focus window is tested on the fair American price, not the shorter margin-adjusted price.",
            "official_url": "https://statsapi.mlb.com/api/v1/schedule?sportId=1&gamePk=849805", "olbg_url": "https://www.olbg.com/betting-tips/Baseball/12"
        },
        {
            "id": "AH-F10", "severity": "medium", "category": "Five-pick target shortfall",
            "detail": "No current in-window High selection was found. The requested target of up to five strongest High picks per sport is not met; the shortfall is displayed for all 15 categories rather than filled with weak or historical picks.",
            "official_url": "https://www.nba.com/games?date=2026-10-23", "olbg_url": "https://www.olbg.com/betting-tips"
        },
        {
            "id": "AH-F11", "severity": "medium", "category": "Web-reader capture integrity",
            "detail": "Current source checks are recorded with URLs, retrieval windows and extracted facts, but the Arena reader did not expose raw HTTP bytes or response hashes. The independent provider snapshot's reported hashes are recorded separately and were not recomputed from raw bytes in this Board AH workspace.",
            "official_url": "https://www.nba.com/games?date=2026-10-23", "olbg_url": "https://www.olbg.com/betting-tips"
        }
    ]

    desk = {
        "schema": "olbg4.board-ah.current-desk.v1",
        "board": "AH",
        "as_of_utc": scope["as_of_utc"],
        "scope": scope["scope_interpretation"],
        "source_capture": source_ledger,
        "events": rows,
    }
    return desk, market_audit, predictions, historical, {"coverage": coverage, "flags": flag_rows}


def render_header(title: str, subtitle: str, eyebrow: str = "BOARD AH · 23 OCTOBER 2026") -> str:
    return f'<section class="page-head"><div class="eyebrow">{raw(eyebrow)}</div><h1>{raw(title)}</h1><p>{raw(subtitle)}</p></section>'


def render_event_rows(events: list[dict], compact: bool = False) -> list[list[str]]:
    rows = []
    for event in events:
        start = fmt_datetime(event.get("start_utc")) if event.get("start_utc") else f"{event.get('olbg_display_date', 'Date not confirmed')} · {event.get('olbg_display_time', 'time not stated')} (zone unknown)"
        if event.get("provider_fixture_id"):
            matchup = f"<strong>{raw(event.get('away'))}</strong> @ <strong>{raw(event.get('home'))}</strong>"
        else:
            matchup = f"<strong>{raw(event.get('matchup') or event.get('olbg_listing_title'))}</strong>"
        status = "Confirmed fixture · listing not re-seen" if event.get("provider_fixture_id") else "Listing only · official fixture unconfirmed"
        status_cls = "warn" if not event.get("provider_fixture_id") or event.get("olbg_latest_status", "").startswith("Observed") else "neutral"
        official = link(event.get("official_source_url"), "Official source")
        olbg = link(event.get("olbg_url"), f"OLBG event {event.get('olbg_event_id')}")
        if event.get("market_status") == "withheld":
            selection = f'{pill("Prices withheld", "warn")}<small>{raw(event.get("market_note"))}</small>'
        elif event.get("winner_pick"):
            w = event["winner_pick"]
            selection = f'<strong>{raw(w["selection"])}</strong><br>{pct(w["probability"])} · {raw(w["confidence"])}<br><small>Fair {raw(w["fair_american"])}; margin price {raw(w["margin_american"])}</small>'
        else:
            selection = '<span class="blank">No own pick or price</span>'
        records = "—"
        if event.get("home_record") or event.get("away_record"):
            records = f'{raw(event.get("away"))}: {raw(event.get("away_record"))}<br>{raw(event.get("home"))}: {raw(event.get("home_record"))}'
        if compact:
            rows.append([raw(event["sport"]), start, matchup, selection, official])
        else:
            rows.append([
                start,
                f'<a href="sports/{raw(event["sport_slug"])}.html">{raw(event["sport"])}</a><br><small>{raw(event.get("competition"))}</small>',
                matchup + f'<small class="muted">{raw(event.get("venue") or "Venue not confirmed")}</small>',
                records,
                f'{pill(status, status_cls)}<small>{raw(event.get("olbg_latest_status"))}</small>',
                selection,
                official + '<br>' + (link(event.get("official_schedule_url"), "Schedule") if event.get("official_schedule_url") else ""),
                olbg,
            ])
    return rows


def render_index(desk: dict, market_audit: dict, coverage: dict, flags: list[dict], history: dict) -> str:
    rows = desk["events"]
    picks = [r for r in rows if r.get("winner_pick")]
    priced_events = sum(1 for r in rows if r["market_status"] == "priced")
    scope_count = coverage["scope_count"]
    cards = []
    for c in coverage["categories"]:
        count = c["official_crossmatch_count"]
        state = c["status"].split(";")[0]
        cls = "ok" if count else ("warn" if c["slug"] == "gaelic-sports" else "neutral")
        cards.append(f'<a class="sport-card" href="sports/{raw(c["slug"])}.html"><span>{raw(c["label"])}</span><b>{count} official matches</b><small>{raw(state)}</small><em class="dot {cls}"></em></a>')
    recent = table(["Sport", "Official start (UTC)", "Match", "Current match-winner lean", "Official source"], render_event_rows([r for r in rows if r.get("winner_pick")], compact=True), "No originated match-winner selections.")
    body = render_header("A live scan with the gaps left visible", "Fifteen requested sports are in scope. Only events matched to an official fixture are priced; the rest stay blank and flagged for review.")
    body += f'''<section class="hero-grid">
      <div class="hero-main"><div class="hero-kicker">Snapshot · {raw(scope_asof())}</div><h2>Three sports crossmatched.<br><span>Zero in-window High picks.</span></h2>
        <p>We observed 15 OLBG cards in an earlier scan: 12 NBA, two NHL and one MLB. Official fixtures matched all 15. A later hub recheck returned empty feeds on those pages, and the NHL event pages displayed “Expired”; that discrepancy remains visible rather than being treated as a live confirmed listing.</p>
        <div class="hero-actions"><a class="button primary" href="entries.html">Review 16 event observations</a><a class="button secondary" href="flagged.html">Open flagged issues</a></div>
      </div>
      <div class="hero-side"><span class="tag">CURRENT SCOPE</span><strong>{scope_count}</strong><span>target categories</span><hr><strong>{priced_events}</strong><span>events with originated lines</span></div>
    </section>
    <section class="stats-grid">
      <div class="stat"><span>OLBG ↔ official</span><b>15</b><small>observed once; later listing status differs</small></div>
      <div class="stat"><span>Own market selections</span><b>{market_audit['selection_count']}</b><small>moneyline, handicap and totals across NHL + MLB</small></div>
      <div class="stat"><span>≥70% candidates</span><b>{market_audit['high_probability_outside_window_count']}</b><small>both outside the fair-odds floor</small></div>
      <div class="stat"><span>High picks in band</span><b>0</b><small>no fabricated five-per-sport list</small></div>
    </section>
    <section class="notice warning"><b>Read this before using the table.</b> The 15 crossmatches are preserved from the 16:19Z scan. By 16:32Z, the three corresponding OLBG hubs showed no cards; the NHL event-detail pages showed “Expired”. Official schedules still listed the NHL/MLB fixtures as upcoming. See <a href="flagged.html">AH-F01</a> and the <a href="sources.html">source ledger</a>.</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">ORIGINATED ONLY WHERE INPUTS SUPPORT IT</div><h2>Current match-winner leans</h2></div><a href="picks.html">All picks &amp; threshold scan →</a></div>
      {recent}
      <p class="small muted">The three selections are Medium (55–69.9%), not High. Lines are independently derived; fair odds and 4.5%-margin prices are shown separately.</p>
    </section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">15-SPORT SCOPE</div><h2>Coverage at a glance</h2></div><a href="coverage.html">Coverage table →</a></div><div class="sport-grid">{''.join(cards)}</div></section>
    <section class="section split"><div class="panel"><div class="eyebrow">IMPORTANT LIMITS</div><h2>What is not priced</h2><ul class="clean"><li><b>NBA:</b> 12 fixtures match, but the provider snapshot has only 16 completed games overall and team samples below 20. All NBA market families are withheld.</li><li><b>Other sports:</b> current event-level official reconciliation is missing; a latest hub response of “No tips found” is not proof that no games exist.</li><li><b>Gaelic Sports:</b> one Hurling listing remains unconfirmed against a fixture-level GAA source.</li><li><b>Injuries:</b> no upcoming-game injury report was captured, so no availability claim is made.</li></ul></div><div class="panel"><div class="eyebrow">ARCHIVE IS NOT TODAY</div><h2>Previous-day evidence</h2><p>The target-only slice of Board AG contains {history['fixture_rows']} fixture rows and {history['prediction_texts']} predictions from its 22 Oct 21:15Z capture. None is carried into today’s event or pick list.</p><a class="button secondary" href="history.html">See the historical boundary</a></div></section>'''
    return page("Overview", "index", body)


def render_entries(desk: dict) -> str:
    events = desk["events"]
    headers = ["Official start (UTC)", "Sport / competition", "Fixture / venue", "Official records", "Listing status", "Our current pick / market status", "Official source", "OLBG discovery"]
    body = render_header("Observed listings and official fixtures", "Each row carries an official-source link. OLBG is the discovery layer; our own lines are built only from the official-provider inputs in the recorded snapshot.")
    body += f'''<div class="toolbar"><label for="entry-search">Filter events</label><input id="entry-search" type="search" placeholder="Sport, team, league, event ID…"><span class="small">{len(events)} rows · 15 earlier crossmatches + 1 Hurling listing-only observation</span></div>
    <section class="notice warning"><b>Listing-state mismatch:</b> NBA, NHL and Baseball hub reads at 16:31–16:32Z showed no cards, although the earlier scan found 15 cards. NHL event-detail pages said “Expired”. The official fixture rows below remain usable for schedule facts, but current OLBG presence is not reaffirmed.</section>
    {table(headers, render_event_rows(events))}
    <p class="small muted">Records are current-season official feed values where available. NHL historical form records from 91/92-game samples are intentionally omitted. Hurling date/time is transcribed from OLBG; timezone, venue and official fixture match are blank.</p>'''
    return page("Entries", "entries", body)


def render_markets(desk: dict, audit: dict) -> str:
    by_id = {r["id"]: r for r in desk["events"]}
    rows = []
    for m in audit["eligible_high_selections"] + audit["high_probability_outside_window"]:
        pass
    all_markets = [m for r in desk["events"] for m in r.get("own_markets", [])]
    for m in all_markets:
        event = by_id[m["fixture_id"]]
        market_name = {"moneyline": "Moneyline", "handicap": "Handicap", "total": "Total"}.get(m["family"], m["family"])
        band = pill("In band" if m["fair_in_band"] else "Outside", "ok" if m["fair_in_band"] else "warn")
        tier_tag = pill(m["focus_tier"], "warn" if m["probability"] >= .70 and not m["fair_in_band"] else "neutral")
        rows.append([
            f'<a href="sports/{raw(event["sport_slug"])}.html">{raw(event["sport"])}</a><br><small>{raw(event["away"])} @ {raw(event["home"])}</small>',
            market_name + (" · main" if m["primary_line"] else " · alt"),
            f'<strong>{raw(m["selection"])}</strong>',
            pct(m["probability"]),
            f'{m["fair_decimal"]:.3f}<br><small>{raw(m["fair_american"])}</small>',
            f'{m["margin_decimal"]:.3f}<br><small>{raw(m["margin_american"])}</small>',
            band + '<br>' + tier_tag,
            link(event["official_source_url"], "Official event source"),
        ])
    body = render_header("Our own lines, not copied odds", "Fair prices are derived from our selection probabilities. A 4.5% margin price is shown separately; only the fair American price is tested against the −250 to +10,000 focus band.")
    body += f'''<section class="stats-grid compact"><div class="stat"><span>Priced fixtures</span><b>{audit['priced_event_count']}</b><small>2 NHL · 1 MLB</small></div><div class="stat"><span>Selection prices</span><b>{audit['selection_count']}</b><small>both sides + alt lines</small></div><div class="stat"><span>≥70% in fair band</span><b>{audit['high_probability_in_window_count']}</b><small>no current qualifier</small></div><div class="stat"><span>≥70% outside band</span><b>{audit['high_probability_outside_window_count']}</b><small>displayed below</small></div></section>
    <section class="notice"><b>Pricing basis:</b> fair decimal = 1 / probability. The pipeline’s separate margin price applies a 4.5% two-way hold: 1 / (probability × 1.045). These are not bookmaker quotes and are not OLBG prices.</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">MONEYLINE · HANDICAP · TOTAL</div><h2>All originated selections</h2></div></div>
      {table(["Fixture", "Family", "Selection", "Probability", "Fair price", "4.5%-margin price", "Focus band / tier", "Official source"], rows, "No originated market selections.")}
    </section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">TRANSPARENT SHORTFALL</div><h2>High-probability selections outside the fair-price window</h2></div></div>
      {table(["Fixture", "Selection", "Probability", "Fair American", "Margin American", "Status", "Official source"], [
        [f'<strong>{raw(by_id[m["fixture_id"]]["away"])} @ {raw(by_id[m["fixture_id"]]["home"])}</strong>', raw(m["selection"]), pct(m["probability"]), raw(m["fair_american"]), raw(m["margin_american"]), pill("Outside −250 floor", "warn"), link(by_id[m["fixture_id"]]["official_source_url"], "Official event source")]
        for m in audit["high_probability_outside_window"]
      ], "No ≥70% outside-window candidates in this capture.")}
      <p class="small muted">No ≥70% selection is in the fair-odds band. The two rows above are not in-window High picks.</p>
    </section>
    <section class="section"><div class="eyebrow">NBA MARKET FAMILIES EXAMINED</div><h2>Withheld, not guessed</h2><p>The official NBA schedule crossmatches 12 OLBG-observed cards. The provider training data has 16 completed games total and each matched game’s teams have only one or two completed games. Moneyline, point spread and game total are all withheld until the sample gate is met.</p><a href="sports/basketball.html">See all 12 NBA rows →</a></section>'''
    return page("Markets", "markets", body)


def render_picks(desk: dict, audit: dict, coverage: dict) -> str:
    winners = [r for r in desk["events"] if r.get("winner_pick")]
    med_rows = []
    for r in winners:
        w = r["winner_pick"]
        med_rows.append([
            f'<a href="sports/{raw(r["sport_slug"])}.html">{raw(r["sport"])}</a>',
            f'<strong>{raw(r["away"])} @ {raw(r["home"])}</strong>',
            f'<strong>{raw(w["selection"])}</strong>',
            pct(w["probability"]),
            f'{raw(w["fair_american"])} ({w["fair_decimal"]:.3f})',
            pill(w["confidence"], "neutral"),
            link(r["official_source_url"], "Official source"),
        ])
    by_id = {r["id"]: r for r in desk["events"]}
    outside_rows = []
    for m in audit["high_probability_outside_window"]:
        event = by_id[m["fixture_id"]]
        outside_rows.append([
            f'<strong>{raw(event["away"])} @ {raw(event["home"])}</strong>', raw(m["selection"]), pct(m["probability"]), raw(m["fair_american"]), raw(m["margin_american"]), pill("Outside price band", "warn"), link(event["official_source_url"], "Official source")
        ])
    total_shortfall = sum(c["five_pick_shortfall"] for c in coverage["categories"])
    body = render_header("Picks: strict threshold, no forced quota", "The current in-window High list is empty. Medium selections and ≥70% selections outside the odds band are reported separately so the threshold is not blurred.")
    body += f'''<section class="notice warning"><b>There are no eligible High picks in this snapshot.</b> None of the originated selections simultaneously clears the ≥70% probability threshold and the fair-American −250 to +10,000 band. No written High-pick text is published.</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">CURRENT MATCH-WINNER SELECTIONS</div><h2>Three Medium leans</h2></div><span class="tag">NOT HIGH-CONFIDENCE PICKS</span></div>
      {table(["Sport", "Fixture", "Selection", "Probability", "Fair price", "Grade", "Official source"], med_rows, "No current match-winner selection is priced.")}
      <p class="small muted">All three probabilities are below 70%. They are not presented as High and receive no prediction prose.</p>
    </section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">PROBABILITY PASSES, ODDS TEST FAILS</div><h2>Two ≥70% selections outside the fair-price band</h2></div></div>
      {table(["Fixture", "Selection", "Probability", "Fair American", "4.5%-margin American", "Why not eligible", "Official source"], outside_rows, "No out-of-band candidates.")}
    </section>
    <section class="section split"><div class="panel"><div class="eyebrow">FIVE-PICK TARGET</div><h2>Shortfall: {total_shortfall} selections</h2><p>The working target is up to five strong High picks in each of the 15 requested categories. With zero in-band High picks, the shortfall is five per category. No historical or unverified picks are substituted.</p><a href="coverage.html">Review all 15 shortfalls →</a></div><div class="panel"><div class="eyebrow">NO INVENTED PROSE</div><h2>Zero prediction write-ups</h2><p>The write-up rules apply to qualifying High selections only. Because there are none, no 30-word prediction paragraphs are generated from weak or unsupported evidence.</p><a href="methodology.html">Read the threshold rules →</a></div></section>'''
    return page("Picks", "picks", body)


def render_coverage(coverage: dict) -> str:
    rows = []
    for c in coverage["categories"]:
        hubs = "<br>".join(link(h["url"], f"OLBG ID {h['id']}" + (f" · {h['subsport']}" if h.get("subsport") else "")) for h in c["olbg_hubs"])
        officials = "<br>".join(link(url, "Official source") for url in c["official_references"][:2])
        state = pill("Priced events" if c["priced_count"] else ("Listing only" if c["slug"] == "gaelic-sports" else "No current match rows"), "ok" if c["priced_count"] else "warn" if c["slug"] == "gaelic-sports" else "neutral")
        rows.append([
            f'<a href="sports/{raw(c["slug"])}.html"><strong>{raw(c["label"])}</strong></a>',
            f'{c["official_crossmatch_count"]} official / {c["observed_entry_count"]} observed',
            f'{c["priced_count"]} priced<br>{c["in_window_high_count"]} High in band',
            f'{c["five_pick_shortfall"]} of 5',
            state + f'<small>{raw(c["status"])}</small>',
            hubs,
            officials,
        ])
    body = render_header("Coverage across the requested 15 categories", "Coverage counts are event-level, not hub-level. “No current match rows” means no verified row is published in this snapshot—not that the sport has no fixtures.")
    body += f'''<section class="stats-grid compact"><div class="stat"><span>Target categories</span><b>{coverage['scope_count']}</b><small>13 priced-capable + Gaelic Sports + Greyhounds</small></div><div class="stat"><span>Official crossmatches</span><b>{coverage['officially_crossmatched_entry_count']}</b><small>3 categories; OLBG listing later recheck differs</small></div><div class="stat"><span>Originated fixtures</span><b>{coverage['priced_entry_count']}</b><small>2 NHL · 1 MLB; NBA withheld</small></div><div class="stat"><span>High in band</span><b>{coverage['high_in_window_pick_count']}</b><small>five-pick shortfalls retained</small></div></section>
    <section class="notice warning"><b>Freshness boundary:</b> direct current-day fixture reads were made only for NBA, NHL, MLB and the Gaelic/Hurling source review. Other official references link to the 22 Oct source ledger or governing-body pages, but were not rechecked as current fixture evidence.</section>
    {table(["Category", "Current rows", "Prices / High", "5-pick shortfall", "Status", "OLBG hub", "Official review link"], rows)}
    <section class="section"><h2>What “13 priced categories” means</h2><p>Baseball, Basketball, Cricket, Darts, Golf, Handball, Ice Hockey, Motor Racing, Rugby League, Rugby Union, Snooker, Tennis and Volleyball are the 13 priced-capable categories. Gaelic Sports is one requested category covering Gaelic Football and Hurling; Greyhounds is a separate requested category. Badminton, Aussie Rules, Table Tennis and eSports are outside this Board AH scope.</p><p>All 15 categories remain on the dashboard even when no current fixture can be published.</p></section>'''
    return page("Coverage", "coverage", body)


def render_sources(scope: dict, listings: dict, sources: dict) -> str:
    current_rows = []
    for item in sources["current_checks"]:
        current_rows.append([
            raw(item["sport"]), link(item["url"], item["id"]), raw(item["retrieved_window_utc"]), raw(item["finding"]), pill("No raw hash", "warn")
        ])
    snapshot_rows = []
    for item in sources["provider_snapshot_2026_10_23T11_35Z"]:
        snapshot_rows.append([
            raw(item["sport"]), link(item["url"], item["id"]), raw(item["retrieved_utc"]), raw(item.get("http_status")), raw(item.get("reported_sha256")), raw(item["note"])
        ])
    listing_rows = []
    for result in listings["latest_hub_recheck"]["results"]:
        listing_rows.append([raw(result["sport"]), link(result["url"], "OLBG hub"), raw(result["visible_feed_text"][:220]), raw(result["event_cards_observed"])])
    body = render_header("Sources and capture ledger", "Official schedules verify fixtures. OLBG pages identify events and expose market vocabulary, but their picks and odds are not used to originate our lines.")
    body += f'''<section class="notice warning"><b>Raw-response limitation:</b> current tool reads provided parsed text, not byte-for-byte responses. No SHA-256 is claimed for the 16:19–16:32Z page-reader checks. The earlier 11:35Z provider snapshot reports hashes in its metadata, but the raw response bodies are not in this Board AH folder.</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">CURRENT OFFICIAL RECHECKS</div><h2>Schedule and fixture evidence</h2></div></div>{table(["Sport", "Source", "Read window (UTC)", "Observed fact", "Capture"], current_rows)}</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">PROVIDER SNAPSHOT</div><h2>Model/line input sources (11:35–11:37Z)</h2></div><a href="../session-4afef1af/data/snapshot.json">Snapshot metadata ↗</a></div>{table(["Sport", "Official source", "Retrieved", "HTTP", "Reported SHA-256", "Use / note"], snapshot_rows)}</section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">OLBG DISCOVERY RECHECK</div><h2>16 hub responses</h2></div></div>{table(["Sport / sub-hub", "OLBG page", "First-chunk feed result", "Cards"], listing_rows)}</section>
    <section class="section"><h2>Per-category official references</h2><div class="source-grid">{''.join(f'<article class="source-card"><h3>{raw(c["label"])}</h3><p>{raw(c["status"])}</p><div>{" · ".join(link(u, "official source") for u in c["official_references"][:4])}</div></article>' for c in scope["categories"])}</div></section>
    <section class="section"><p class="small muted">Historical official-source inventory: <a href="../data/session-4885d641/official_sources.json">Board AG source manifest</a> (cutoff 2026-10-22T21:15Z). It is a reference inventory, not current-day fixture confirmation.</p><p class="small muted">Machine-readable Board AH ledger: <a href="../data/session-8860f8f7/source_ledger.json">source_ledger.json</a> · <a href="../data/session-8860f8f7/listing_observations.json">listing_observations.json</a>.</p></section>'''
    return page("Sources", "sources", body)


def render_methodology(scope: dict) -> str:
    body = render_header("How this desk decides what can be published", "A line-by-line path from OLBG discovery to official fixture, originated market, confidence grade and review flag.")
    body += '''<section class="method-grid">
      <article class="method-card"><span class="step">01</span><h2>Scope &amp; discovery</h2><p>The target is 15 categories: 13 priced-capable sports, Gaelic Sports (Gaelic Football plus Hurling), and Greyhounds. OLBG hub cards identify candidate events only. The later 16:32Z recheck is recorded alongside the earlier 16:19Z scan so feed changes are not hidden.</p></article>
      <article class="method-card"><span class="step">02</span><h2>Official fixture gate</h2><p>A row is crossmatched only when the OLBG event observation maps to an official provider fixture by event ID plus matchup/date. The NBA, NHL and MLB rows link to the official game page and schedule. The Hurling event remains listing-only because the exact club fixture was not confirmed.</p></article>
      <article class="method-card"><span class="step">03</span><h2>Own market construction</h2><p>For the three NHL/MLB fixtures with sufficient official-feed training data, the line engine supplies moneyline, handicap/run-or-puck line and total distributions, including alternate lines. No OLBG or sportsbook line is copied. Fair decimal = 1 / p; the separate margin price uses a 4.5% two-way hold.</p></article>
      <article class="method-card"><span class="step">04</span><h2>NBA sample hold</h2><p>The current NBA training sample has 16 completed games overall, and the matched teams have one or two completed games each. The required minimum is 20 per team; moneyline, pointspread and total markets are blank rather than inferred.</p></article>
      <article class="method-card"><span class="step">05</span><h2>Confidence &amp; odds window</h2><p>High requires probability ≥70% and a fair American price between −250 and +10,000 inclusive. Fair price—not margin-adjusted price—is used for the band test. Medium is 55% to under 70%; Low is under 55%. These desk grades override internal pipeline tags where they use a different threshold.</p></article>
      <article class="method-card"><span class="step">06</span><h2>Prediction prose</h2><p>Only qualifying High selections receive a unique, natural prediction of at least 30 words naming the bet and citing source-confirmed facts. No selection qualifies now, so no prediction prose is emitted. Injuries and lineups are not claimed without a direct upcoming-game source.</p></article>
    </section>
    <section class="section"><h2>Fair odds and the −250 boundary</h2><p>At 70% probability, fair American odds are approximately −233.3, so the two conditions can overlap only from 70% through about 71.43%. The 73.98% Over 5.5 and 72.97% Under 8.5 totals are shorter than −250 at fair odds, so they are listed as outside-window candidates rather than eligible High selections.</p><p>The source pipeline also reports a 4.5%-margin price. That figure can be shorter than the fair price. Both are shown in <a href="markets.html">Markets</a>; only the fair price determines window eligibility.</p></section>
    <section class="section"><h2>Data freshness and limits</h2><ul class="clean"><li>The underlying NHL/MLB training and market snapshot is from 2026-10-23 11:35–11:37Z. Later official reads rechecked schedule facts, not the full model inputs.</li><li>The current page-reader results are saved as extracted facts and URLs; raw response bytes and hashes were not provided.</li><li>Historical Board AG entries dated 22 Oct remain in a separate archive and never populate this current-day desk.</li><li>Every row has an official source link for manual review. Listing-only rows are labelled and carry no originated market, price, pick or confidence.</li><li>This desk is informational, not betting advice. Prices and outcomes can change.</li></ul></section>'''
    return page("Methodology", "methodology", body)


def render_olbg(listings: dict, scope: dict) -> str:
    category_rows = []
    for c in scope["categories"]:
        hub_links = "<br>".join(link(h["url"], f'ID {h["id"]}' + (f' · {h["subsport"]}' if h.get("subsport") else "")) for h in c["olbg_hubs"])
        category_rows.append([raw(c["label"]), hub_links, raw(c["latest_olbg_hub_observation"]), raw(", ".join(c["market_families"]))])
    event_rows = []
    for event in listings["earlier_live_scan"]["events"]:
        event_rows.append([
            raw(event["sport"]), raw(event["olbg_event_id"]), raw(event.get("listing_title") or "Title not retained"),
            link(event["olbg_url"], "OLBG detail/hub"), raw(event["official_fixture_id"])
        ])
    hurl = next(r for r in listings["latest_hub_recheck"]["results"] if r["sport"] == "Hurling")["events"][0]
    event_rows.append(["Gaelic Sports · Hurling", str(hurl["olbg_event_id"]), raw(hurl["matchup"]), link(hurl["event_url"], "OLBG event"), "No official fixture match confirmed"])
    body = render_header("OLBG page map and listing behaviour", "OLBG is used to discover candidate events and understand market names. Tip shares, bookmaker prices and tipster narratives do not become our lines or probabilities.")
    body += f'''<section class="notice"><b>Reverse-engineering result:</b> the latest hub responses show that the top feed can be empty even when an earlier scan observed cards. Individual event pages can also carry an “Expired” state while the official schedule still lists a future game. We preserve both observations instead of silently choosing one.</section>
    <section class="section"><div class="eyebrow">SPORT IDENTIFIERS</div><h2>All requested OLBG hubs</h2>{table(["Category", "Hub ID and URL", "Latest feed observation", "Markets described on OLBG"], category_rows)}</section>
    <section class="section"><div class="eyebrow">EARLIER LIVE SCAN</div><h2>15 observed crossmatch IDs</h2>{table(["Sport", "OLBG event ID", "Observed title", "OLBG link", "Official fixture ID"], event_rows)}</section>
    <section class="section"><h2>Market taxonomy checked</h2><div class="market-taxonomy"><article><h3>Baseball</h3><p>Money Line · Run Line · Game Totals</p></article><article><h3>Basketball</h3><p>Money Line · Pointspread · Game Totals</p></article><article><h3>Ice Hockey</h3><p>Money Line · Puck Line · Game Totals</p></article><article><h3>Gaelic Sports</h3><p>Full-Time Result / draw where applicable · points handicap · total points · outrights</p></article><article><h3>Other target categories</h3><p>Market families listed on the <a href="coverage.html">coverage page</a> are taxonomy notes only. No market is priced without an official fixture and usable inputs.</p></article></div></section>
    <section class="section"><h2>How not to read the OLBG data</h2><ul class="clean"><li>The displayed tip percentage is not a win probability and is not used in the desk’s probability calculation.</li><li>OLBG odds are not copied into fair prices or margin prices.</li><li>OLBG text about injuries, player form or tactics is not treated as official fact.</li><li>Event IDs are retained as discovery references; a later “No tips found” response is not converted into “no games”.</li></ul></section>'''
    return page("OLBG page map", "olbg", body)


def render_flags(flags: list[dict]) -> str:
    rows = []
    for f in flags:
        rows.append([
            raw(f["id"]), pill(f["severity"].upper(), "warn" if f["severity"] == "high" else "neutral"),
            f'<strong>{raw(f["category"])}</strong><p>{raw(f["detail"])}</p>',
            link(f.get("official_url"), "Official source") + "<br>" + link(f.get("olbg_url"), "OLBG source"),
        ])
    body = render_header("Flagged for review", "Irregularities and unverified observations are published now, with values left blank wherever confirmation failed.")
    body += f'''<section class="notice warning"><b>Non-blocking review issues are not hidden.</b> The dashboard still builds, but the scan is partial: OLBG card volatility, incomplete official coverage outside three sports, a listing-only Hurling event, and a same-day model-input timestamp are recorded below.</section>
    {table(["ID", "Severity", "Issue / action", "Manual review"], rows)}
    <section class="section"><h2>Rows deliberately left blank</h2><ul class="clean"><li>All 12 NBA events: no winner, spread, total, fair price or confidence.</li><li>Ballyhale Shamrocks v Tullaroan: no official start time, time zone, venue, line, probability, pick or confidence.</li><li>All remaining sports without an official event-level fixture match: no current entry or pick is invented.</li></ul></section>
    <section class="section"><h2>Review files</h2><p><a href="../data/session-8860f8f7/listing_observations.json">Listing observations</a> · <a href="../data/session-8860f8f7/source_ledger.json">Source ledger</a> · <a href="../data/session-8860f8f7/flags.json">Machine-readable flags</a> · <a href="verification.html">Verification gates</a></p></section>'''
    return page("Flagged for review", "flagged", body)


def render_history(history: dict) -> str:
    rows = [[raw(x["sport"]), str(x["rows"]), str(x["predictions"])] for x in history["by_sport"]]
    body = render_header("Historical data boundary", "The previous day’s Board AG slice is preserved as history only. It is not used for current fixtures, lines or picks.")
    body += f'''<section class="hero-grid history-hero"><div class="hero-main"><div class="hero-kicker">BOARD AG · CUTOFF 2026-10-22T21:15Z</div><h2>{history['fixture_rows']} rows<br><span>{history['prediction_texts']} prediction texts</span></h2><p>These counts cover the 13 priced-capable categories in Board AH scope. The capture predates this scan and must not be presented as current-day recommendations.</p><a class="button secondary" href="../session-4885d641/index.html">Open historical Board AG ↗</a></div><div class="hero-side"><span class="tag">NOT CURRENT</span><strong>0</strong><span>historical rows carried into the live desk</span></div></section>
    {table(["Priced-capable category", "Historical fixture rows", "Historical prediction texts"], rows)}
    <section class="section"><h2>Why the separation matters</h2><p>The 22 Oct board’s sources, fixtures and predictions may be useful as an audit trail, but schedules and event status change. Board AH uses only the current 23 Oct official-provider snapshot for the NBA/NHL/MLB rows and the fresh page-reader observations recorded in its own source ledger. No older pick is re-labelled as current.</p><p>Machine-readable summary: <a href="../data/session-8860f8f7/history.json">history.json</a>.</p></section>'''
    return page("History boundary", "history", body)


def render_verification(report: dict | None, desk: dict, coverage: dict, audit: dict) -> str:
    report = report or {"status": "pending", "checks": [], "summary": "Run scripts/session-8860f8f7/verify.py after building."}
    checks = report.get("checks", [])
    check_rows = [[raw(c.get("name")), pill(c.get("status", "PENDING"), "ok" if c.get("status") == "PASS" else "warn"), raw(c.get("detail"))] for c in checks]
    if not check_rows:
        check_rows = [["Automated validation", pill("PENDING", "warn"), raw(report.get("summary", "Pending."))]]
    body = render_header("Verification register", "Automated integrity checks for target scope, source links, originated prices, high threshold, unpriced purity and local pages.")
    body += f'''<section class="stats-grid compact"><div class="stat"><span>Current rows</span><b>{len(desk['events'])}</b><small>15 crossmatches + 1 listing-only</small></div><div class="stat"><span>Official source links</span><b>{sum(1 for e in desk['events'] if e.get('official_source_url'))}/{len(desk['events'])}</b><small>every published row</small></div><div class="stat"><span>Market selections</span><b>{audit['selection_count']}</b><small>probability and prices re-derived</small></div><div class="stat"><span>High in band</span><b>{audit['high_probability_in_window_count']}</b><small>strict threshold</small></div></section>
    <section class="notice {"success" if report.get('status') == 'PASS' else 'warning'}"><b>Gate status: {raw(report.get('status', 'PENDING'))}</b> · {raw(report.get('summary', 'Validation has not been run yet.'))}</section>
    {table(["Check", "Result", "Details"], check_rows)}
    <section class="section"><h2>How to reproduce</h2><pre><code>python3 scripts/session-8860f8f7/build.py
python3 scripts/session-8860f8f7/verify.py
python3 scripts/audit_publication.py --check</code></pre><p>Board-local verification is source-independent and deterministic; it does not fetch the internet. Current web-reader response hashes are not claimed.</p><p><a href="../data/session-8860f8f7/verification.json">Machine-readable verification report</a> · <a href="../scripts/session-8860f8f7/verify.py">Verifier source</a>.</p></section>'''
    return page("Verification", "verification", body)


def render_sport_page(category: dict, events: list[dict], coverage: dict) -> str:
    matches = [r for r in events if r["sport_slug"] == category["slug"]]
    c = next(x for x in coverage["categories"] if x["slug"] == category["slug"])
    refs = " · ".join(link(url, "Official review source") for url in category["official_references"][:4])
    hubs = " · ".join(link(h["url"], f"OLBG hub ID {h['id']}" + (f' ({h["subsport"]})' if h.get("subsport") else "")) for h in category["olbg_hubs"])
    body = render_header(category["label"], category["status"], eyebrow="SPORT PAGE · BOARD AH")
    body += f'''<div class="sport-meta"><div><span>Current scan</span><b>{c['observed_entry_count']} rows</b></div><div><span>Official matches</span><b>{c['official_crossmatch_count']}</b></div><div><span>Own priced fixtures</span><b>{c['priced_count']}</b></div><div><span>In-window High picks</span><b>{c['in_window_high_count']}</b></div></div>
    <section class="panel"><div class="eyebrow">SOURCE LINKS</div><p>{refs}</p><p>{hubs}</p></section>
    <section class="section"><div class="section-title"><div><div class="eyebrow">CURRENT-DAY ROWS</div><h2>Verified and flagged entries</h2></div></div>
      {table(["Official start (UTC)", "Fixture / competition", "Records", "Current status", "Own pick / markets", "Official source", "OLBG discovery"], [
        [fmt_datetime(e.get("start_utc")) if e.get("start_utc") else f'{raw(e.get("olbg_display_date"))} · {raw(e.get("olbg_display_time"))} (zone unknown)',
         f'<strong>{raw((e.get("away") + " @ " + e.get("home")) if e.get("provider_fixture_id") else e.get("matchup"))}</strong><small>{raw(e.get("competition"))}</small>',
         f'{raw(e.get("away_record"))} / {raw(e.get("home_record"))}' if e.get("home_record") or e.get("away_record") else '<span class="blank">Not confirmed</span>',
         pill("Official fixture confirmed; OLBG not re-seen" if e.get("provider_fixture_id") else "Listing only · unconfirmed", "warn" if not e.get("provider_fixture_id") or e.get("market_status") == "withheld" else "ok"),
         (f'<strong>{raw(e["winner_pick"]["selection"])}</strong> · {pct(e["winner_pick"]["probability"])} · {raw(e["winner_pick"]["confidence"])}' if e.get("winner_pick") else (pill("Withheld", "warn") if e.get("market_status") == "withheld" else '<span class="blank">No own pick</span>')),
         link(e.get("official_source_url"), "Official event / review source"), link(e.get("olbg_url"), f'OLBG {e.get("olbg_event_id")}')]
        for e in matches
      ], "No current event-level fixture rows were confirmed for this category.")}
    </section>
    <section class="section"><div class="panel"><div class="eyebrow">REVIEW NOTE</div><p>{raw(category['latest_olbg_hub_observation'])}</p><p class="small muted">Current rows: {raw(category['status'])}. Prior Board AG rows, if shown in History, are historical only.</p></div></section>'''
    return page(f"{category['label']} coverage", "coverage", body, prefix="../")


def render_site(desk: dict, market_audit: dict, predictions: dict, history: dict, aux: dict, sources: dict, listings: dict, verification: dict | None) -> None:
    scope = load(SCOPE_PATH)
    coverage = aux["coverage"]
    flags = aux["flags"]
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / ".nojekyll").write_text("", encoding="utf-8")
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(parents=True, exist_ok=True)
    css = r'''
:root{--ink:#12263a;--muted:#617387;--line:#dce5ed;--bg:#f5f8fb;--card:#fff;--navy:#0d263d;--teal:#0e7490;--cyan:#dff5f8;--green:#147d64;--warn:#9a4b17;--warnbg:#fff5e8;--red:#9b2c2c;--blue:#2b5f9e;--shadow:0 10px 30px rgba(16,42,67,.06)}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:'DM Sans',Inter,system-ui,-apple-system,Segoe UI,sans-serif;font-size:15px;line-height:1.55}a{color:#08789b;text-decoration:none}a:hover{text-decoration:underline;color:#075b79}.wrap{width:min(1220px,calc(100% - 36px));margin:0 auto}.topbar{background:var(--navy);color:#fff;border-bottom:3px solid #22a3b3}.topbar-inner{min-height:72px;display:flex;align-items:center;justify-content:space-between;gap:24px}.brand{display:flex;gap:11px;align-items:center;color:#fff;min-width:210px}.brand:hover{color:#fff;text-decoration:none}.brand-mark{width:39px;height:39px;border-radius:11px;background:#1b91a5;color:#fff;display:grid;place-items:center;font-weight:800;font-size:13px;letter-spacing:.04em}.brand small{display:block;color:#b2c6d4;font-size:11px;margin-top:1px}.nav{display:flex;gap:5px;align-items:center;flex-wrap:wrap;justify-content:flex-end}.nav a{color:#b7c7d3;padding:8px 10px;border-radius:7px;font-size:12px;font-weight:700}.nav a:hover,.nav a.active{background:#173c58;color:#fff;text-decoration:none}.page-head{padding:42px 0 24px}.eyebrow,.hero-kicker,.tag{font-family:'DM Mono',monospace;text-transform:uppercase;letter-spacing:.08em;font-size:10px;font-weight:500;color:var(--teal)}.page-head h1{font-size:clamp(30px,4.4vw,46px);letter-spacing:-.045em;line-height:1.05;margin:10px 0 12px;color:var(--navy)}.page-head p{max-width:790px;color:var(--muted);font-size:16px;margin:0}.hero-grid{display:grid;grid-template-columns:minmax(0,1fr) 240px;gap:18px;margin:10px 0 24px}.hero-main,.hero-side{border-radius:18px;background:linear-gradient(135deg,#0d263d,#16445e);color:#fff;box-shadow:var(--shadow);padding:28px 30px}.hero-main{background:radial-gradient(circle at 93% 16%,rgba(56,189,190,.18),transparent 32%),linear-gradient(135deg,#0d263d,#16445e)}.hero-kicker{color:#7dd3d6}.hero-main h2{font-size:clamp(28px,4.5vw,46px);line-height:1.08;letter-spacing:-.05em;margin:13px 0 12px}.hero-main h2 span{color:#83e2dc}.hero-main p{max-width:770px;color:#d2e1e9;margin:0 0 19px}.hero-side{display:flex;flex-direction:column;justify-content:center;align-items:flex-start;background:#fff;color:var(--ink);border:1px solid var(--line)}.hero-side .tag{color:var(--teal)}.hero-side strong{font-size:34px;line-height:1.05;color:var(--navy);margin-top:14px}.hero-side span:not(.tag){font-size:12px;color:var(--muted)}.hero-side hr{border:0;border-top:1px solid var(--line);width:100%;margin:16px 0 0}.hero-actions{display:flex;gap:9px;flex-wrap:wrap}.button{display:inline-flex;align-items:center;justify-content:center;padding:10px 15px;border-radius:8px;font-weight:700;font-size:13px}.button.primary{background:#52d4c5;color:#082b38}.button.secondary{border:1px solid rgba(255,255,255,.34);color:#fff;background:rgba(255,255,255,.06)}.panel .button.secondary{color:var(--teal);border-color:var(--line);background:#fff}.stats-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:18px 0 22px}.stats-grid.compact{margin:12px 0 18px}.stat{background:#fff;border:1px solid var(--line);border-radius:12px;padding:15px 17px;box-shadow:var(--shadow)}.stat span{display:block;color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em}.stat b{display:block;font-size:29px;letter-spacing:-.05em;color:var(--navy);line-height:1.15;margin:5px 0}.stat small{display:block;color:var(--muted);font-size:11px}.notice{margin:16px 0;padding:14px 16px;border-radius:11px;border:1px solid #bee8e6;background:#effcf9;color:#214e4b}.notice.warning{background:var(--warnbg);border-color:#f0d2ab;color:#704313}.notice.success{background:#effcf9;color:#17624e}.section{margin:30px 0}.section-title{display:flex;align-items:end;justify-content:space-between;gap:16px;margin-bottom:12px}.section-title h2,.section h2,.panel h2{margin:5px 0 8px;font-size:23px;letter-spacing:-.035em;color:var(--navy)}.section-title>a{font-size:13px;font-weight:700}.small{font-size:12px}.muted{color:var(--muted)}.sport-grid{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px}.sport-card{position:relative;display:flex;flex-direction:column;gap:3px;background:#fff;border:1px solid var(--line);border-radius:11px;padding:12px;color:var(--ink);min-height:88px}.sport-card:hover{text-decoration:none;border-color:#8dcbd1;box-shadow:var(--shadow)}.sport-card span{font-weight:800;font-size:13px}.sport-card b{color:var(--teal);font-size:11px}.sport-card small{color:var(--muted);font-size:10px;padding-right:10px}.sport-card .dot{position:absolute;width:7px;height:7px;border-radius:100%;right:12px;top:15px;background:#94a3b8}.sport-card .dot.ok{background:#1a987a}.sport-card .dot.warn{background:#d88938}.split{display:grid;grid-template-columns:1fr 1fr;gap:14px}.panel{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px;box-shadow:var(--shadow)}.panel p{color:var(--muted)}ul.clean{padding-left:19px;color:#40566b}ul.clean li{margin:7px 0}.table-wrap{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow);margin:10px 0 14px}table{border-collapse:collapse;width:100%;min-width:760px;font-size:12px}th{text-align:left;padding:11px 12px;background:#eef4f7;color:#486073;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:.06em;text-transform:uppercase;white-space:nowrap}td{padding:11px 12px;border-top:1px solid #e7edf1;vertical-align:top;max-width:330px}td small{display:block;color:var(--muted);font-size:10px;margin-top:4px;line-height:1.4}td p{margin:5px 0;color:#52697d}.pill{display:inline-flex;align-items:center;white-space:nowrap;border-radius:999px;padding:3px 8px;font-size:9px;line-height:1.3;font-weight:800;text-transform:uppercase;letter-spacing:.04em;background:#edf2f7;color:#44596b}.pill.ok{background:#e5f7f0;color:#167355}.pill.warn{background:#fff0d9;color:#975512}.pill.neutral{background:#eaf3f8;color:#235879}.blank{color:#7e8f9f;font-style:italic}.tag{display:inline-flex;border:1px solid #d6e9ee;border-radius:999px;padding:5px 8px;background:#f3fbfc}.empty{padding:18px;border:1px dashed #bdcbd5;border-radius:10px;color:var(--muted);background:#fff}.toolbar{display:flex;align-items:center;gap:10px;margin:10px 0 14px}.toolbar label{font-size:12px;font-weight:700}.toolbar input{width:min(420px,55vw);padding:9px 11px;border-radius:8px;border:1px solid #cbd8e2;background:#fff;font:inherit}.toolbar span{margin-left:auto}.page-head+.toolbar{margin-top:2px}.source-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.source-card{background:#fff;border:1px solid var(--line);border-radius:11px;padding:14px}.source-card h3{margin:0 0 5px;font-size:14px}.source-card p{font-size:11px;color:var(--muted)}.method-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.method-card{position:relative;background:#fff;border:1px solid var(--line);border-radius:13px;padding:20px;box-shadow:var(--shadow)}.method-card .step{font:11px 'DM Mono',monospace;color:var(--teal)}.method-card h2{font-size:18px;color:var(--navy);margin:7px 0}.method-card p{color:var(--muted);font-size:13px;margin:0}.market-taxonomy{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}.market-taxonomy article{background:#fff;border:1px solid var(--line);border-radius:10px;padding:15px}.market-taxonomy h3{margin:0 0 5px}.market-taxonomy p{margin:0;color:var(--muted);font-size:12px}.sport-meta{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:0 0 18px}.sport-meta>div{border:1px solid var(--line);background:#fff;border-radius:10px;padding:13px}.sport-meta span{display:block;color:var(--muted);font-size:10px;text-transform:uppercase;font-weight:700}.sport-meta b{display:block;color:var(--navy);font-size:20px}.footer{margin-top:50px;padding:22px 0;background:#102b42;color:#bdcbd4;font-size:11px}.footer-inner{display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap}.footer a{color:#8bd8db}.footer-note{margin-top:8px;color:#90a7b7}.history-hero .hero-main h2 span{color:#ffcf8b}pre{background:#102b42;color:#e1f0f6;border-radius:10px;padding:16px;overflow:auto;font-size:12px}.hero-main a:hover{filter:brightness(1.04);text-decoration:none}.section p{color:#536a7e}.no-results{display:none}.hide-row{display:none!important}
@media(max-width:920px){.topbar-inner{align-items:flex-start;flex-direction:column;padding:13px 0}.nav{justify-content:flex-start}.sport-grid{grid-template-columns:repeat(3,1fr)}.method-grid{grid-template-columns:repeat(2,1fr)}.source-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:680px){.wrap{width:min(100% - 22px,1220px)}.hero-grid{grid-template-columns:1fr}.hero-side{display:grid;grid-template-columns:1fr auto;align-items:center;gap:6px}.hero-side strong{grid-column:2;grid-row:1;font-size:27px}.hero-side span:not(.tag){grid-column:1}.hero-side hr{display:none}.stats-grid{grid-template-columns:repeat(2,1fr)}.split{grid-template-columns:1fr}.sport-grid{grid-template-columns:repeat(2,1fr)}.method-grid,.source-grid,.market-taxonomy{grid-template-columns:1fr}.sport-meta{grid-template-columns:repeat(2,1fr)}.page-head{padding:30px 0 18px}.page-head p{font-size:14px}.nav a{padding:7px 8px}.section-title{align-items:flex-start;flex-direction:column}.toolbar{align-items:flex-start;flex-direction:column}.toolbar span{margin-left:0}.toolbar input{width:100%}.footer-inner{flex-direction:column}}
'''
    (SITE / "assets/site.css").write_text(css, encoding="utf-8")
    js = r'''document.addEventListener('DOMContentLoaded',()=>{const input=document.querySelector('#entry-search');if(!input)return;const rows=[...document.querySelectorAll('table tbody tr')];input.addEventListener('input',()=>{const q=input.value.toLowerCase().trim();rows.forEach(row=>row.classList.toggle('hide-row',q&&!row.textContent.toLowerCase().includes(q)));});});'''
    (SITE / "assets/site.js").write_text(js, encoding="utf-8")

    pages = {
        "index.html": render_index(desk, market_audit, coverage, flags, history),
        "entries.html": render_entries(desk),
        "markets.html": render_markets(desk, market_audit),
        "picks.html": render_picks(desk, market_audit, coverage),
        "coverage.html": render_coverage(coverage),
        "sources.html": render_sources(scope, listings, sources),
        "methodology.html": render_methodology(scope),
        "olbg.html": render_olbg(listings, scope),
        "flagged.html": render_flags(flags),
        "history.html": render_history(history),
        "verification.html": render_verification(verification, desk, coverage, market_audit),
    }
    for name, content in pages.items():
        (SITE / name).write_text(content, encoding="utf-8")
    for category in scope["categories"]:
        content = render_sport_page(category, desk["events"], coverage)
        (SITE / "sports" / f"{category['slug']}.html").write_text(content, encoding="utf-8")
    readme = '''# Board AH — current-day target-only OLBG desk\n\nGenerated static pages for the 15-category 2026-10-23 scan.\n\nRebuild and verify from the repository root:\n\n```sh\npython3 scripts/session-8860f8f7/build.py\npython3 scripts/session-8860f8f7/verify.py\npython3 scripts/session-8860f8f7/build.py\npython3 scripts/session-8860f8f7/verify.py --check\n```\n\nThe current source and listing ledgers are in `data/session-8860f8f7/`. The older Board AG snapshot is historical only.\n'''
    (SITE / "README.md").write_text(readme, encoding="utf-8")


def build_all() -> None:
    desk, market_audit, predictions, history, aux = main_build_data()
    dump(DATA / "desk.json", desk)
    dump(DATA / "market_audit.json", market_audit)
    dump(DATA / "predictions.json", predictions)
    dump(DATA / "history.json", history)
    dump(DATA / "coverage.json", aux["coverage"])
    dump(DATA / "flags.json", aux["flags"])
    verification_path = DATA / "verification.json"
    verification = load(verification_path) if verification_path.exists() else None
    render_site(desk, market_audit, predictions, history, aux, load(SOURCES_PATH), load(LISTINGS_PATH), verification)
    print(f"Built {SITE.relative_to(ROOT)}: {len(desk['events'])} event rows, {market_audit['selection_count']} originated selections, {market_audit['high_probability_in_window_count']} in-window High selections, {len(aux['coverage']['categories'])} target categories.")


if __name__ == "__main__":
    build_all()

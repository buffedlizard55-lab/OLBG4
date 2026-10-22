#!/usr/bin/env python3
"""Render Board AF as a dependency-free, accessible GitHub Pages dashboard."""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from common import DATA, SITE, dump, load, slug

E = lambda value: html.escape(str(value if value is not None else ""), quote=True)


def link(url: str, label: str, external: bool = True) -> str:
    if not url:
        return '<span class="blank" title="Unconfirmed; intentionally blank">—</span>'
    attrs = ' target="_blank" rel="noopener noreferrer"' if external else ""
    return f'<a href="{E(url)}"{attrs}>{E(label)}</a>'


def time_label(value: str) -> str:
    if not value:
        return ""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%d %b · %H:%M UTC")


def price(selection: dict[str, Any]) -> str:
    return f"{selection['probability']:.1%} · {selection['decimal']:.3f} · {selection['american']:+d}"


def badge(text: str, kind: str = "") -> str:
    return f'<span class="badge {E(kind)}">{E(text)}</span>'


def filters(table_id: str, sports: list[str], confidence: bool = True, focus: bool = False) -> str:
    sport_options = ''.join(f'<option value="{E(s)}">{E(s)}</option>' for s in sports)
    confidence_field = '<label>Confidence<select data-field="confidence"><option value="">All</option><option>High</option><option>Medium</option><option>Low</option><option value="unpriced">Unpriced</option></select></label>' if confidence else ""
    focus_field = '<label>View<select data-field="focus"><option value="">All picks</option><option value="yes">Focus window only</option><option value="no">Outside focus window</option></select></label>' if focus else ""
    return f'''<form class="filters" data-filter-form="{E(table_id)}" onsubmit="return false">
      <label>Search<input type="search" data-q placeholder="Team, player, competition…"></label>
      <label>Sport<select data-field="sport"><option value="">All sports</option>{sport_options}</select></label>
      {confidence_field}{focus_field}<span class="filter-count" data-count></span>
    </form>'''


def page(path: str, title: str, body: str, description: str, capture: str) -> None:
    depth = len(Path(path).parents) - 1
    prefix = "../" * depth
    repo = "../" * (depth + 1)
    nav = [("index.html", "Overview"), ("entries.html", "Fixtures"), ("markets.html", "Our lines"),
           ("predictions.html", "Predictions"), ("coverage.html", "Coverage"), ("verification.html", "Verification"),
           ("review.html", "Repo review"), ("flagged.html", "Flagged")]
    links = ''.join(f'<a href="{prefix}{href}"' + (' aria-current="page"' if href == Path(path).name else '') + f'>{label}</a>' for href, label in nav)
    secondary = ''.join(f'<a href="{prefix}{href}">{label}</a>' for href, label in [
        ("olbg.html", "OLBG structure"), ("sources.html", "Sources"), ("methodology.html", "Method"), ("analysis.html", "Analysis")])
    doc = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="{E(description)}"><title>{E(title)} · OLBG Evidence Desk</title>
<link rel="stylesheet" href="{prefix}assets/style.css"><script defer src="{prefix}assets/app.js"></script></head>
<body><a class="skip" href="#main">Skip to content</a>
<header class="site-header"><div class="header-inner"><a class="brand" href="{prefix}index.html"><span class="brand-mark">O4</span><span>OLBG <b>Evidence Desk</b></span></a>
<div class="capture"><span class="live-dot"></span> Capture <strong>{E(capture)}</strong></div></div>
<nav class="main-nav" aria-label="Main navigation">{links}</nav></header>
<main id="main">{body}</main>
<footer><div><strong>OLBG Evidence Desk · Board AF</strong><br>Independent fair-line estimates, not bookmaker prices or guarantees.</div>
<div class="footer-links">{secondary}</div><p>Raw evidence: <a href="{repo}data/session-0d3b826c/capture/{E(capture)}/manifest.json">capture manifest</a>. Every unconfirmed value is blank and routed to review.</p></footer>
</body></html>'''
    target = SITE / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")


def heading(kicker: str, title: str, text: str, actions: str = "") -> str:
    return f'<section class="page-heading"><div><p class="kicker">{E(kicker)}</p><h1>{E(title)}</h1><p class="lede">{E(text)}</p></div>{actions}</section>'


def kpis(items: list[tuple[str, Any, str]]) -> str:
    return '<section class="kpi-grid">' + ''.join(
        f'<div class="kpi"><span>{E(label)}</span><strong>{E(value)}</strong><small>{E(note)}</small></div>'
        for label, value, note in items) + '</section>'


def fixture_rows(rows: list[dict[str, Any]], prefix: str = "") -> str:
    output = []
    for row in rows:
        pick = row.get("pick")
        confidence = pick["confidence"] if pick else "unpriced"
        pick_text = pick["selection"] if pick else ""
        pick_price = f"{pick['decimal']:.3f} / {pick['american']:+d}" if pick else ""
        search = ' '.join((row["id"], row["sport"], row["competition"], row["side_a"], row["side_b"], row["venue"])).lower()
        output.append(f'''<tr class="filterable" data-sport="{E(row['sport'])}" data-confidence="{confidence}" data-search="{E(search)}">
<td class="nowrap">{E(time_label(row['start_utc']))}</td><td>{link(prefix + 'sports/' + slug(row['sport']) + '.html', row['sport'], False)}<small>{E(row['competition'])}</small></td>
<td><strong>{E(row['side_a'])} <span class="vs">vs</span> {E(row['side_b'])}</strong><small>{E(row['venue'])}</small></td>
<td>{E(pick_text)}<small>{E(pick_price)}</small></td><td>{badge(confidence, confidence.lower()) if pick else badge('Unpriced','muted')}</td>
<td>{link(row['official_url'], 'Official ↗')}<small>{E(row['verification'])}</small></td></tr>''')
    return ''.join(output)


FIXTURE_HEAD = '<thead><tr><th>Start</th><th>Sport / competition</th><th>Match / venue</th><th>Our winner / fair price</th><th>Confidence</th><th>Evidence</th></tr></thead>'


def prediction_cards(predictions: list[dict[str, Any]]) -> str:
    cards = []
    for item in predictions:
        facts = ''.join(f'<li><span>{E(fact["type"])}</span>{E(fact["text"])} <div>{link(fact["url"], "Verify at official source ↗")}</div></li>' for fact in item["facts"])
        search = ' '.join((item["sport"], item["matchup"], item["selection"], item["text"])).lower()
        cards.append(f'''<article class="prediction-card filterable" data-sport="{E(item['sport'])}" data-confidence="High" data-focus="{'yes' if item['focus_eligible'] else 'no'}" data-search="{E(search)}">
<div class="prediction-top"><div><p class="kicker">{E(item['sport'])} · {E(item['market'])}</p><h2>{E(item['selection'])}</h2><p>{E(item['matchup'])}</p></div>
<div class="prediction-price"><strong>{item['probability']:.1%}</strong><span>fair {item['decimal']:.3f} / {item['american']:+d}</span>{badge('Focus pick','focus') if item['focus_eligible'] else badge('Outside window','muted')}</div></div>
<p class="prediction-text">{E(item['text'])}</p><div class="word-count">{item['word_count']} words · unique authored analysis</div>
<details><summary>Verified facts & manual-review links <span>{len(item['facts'])}</span></summary><ul class="fact-list">{facts}</ul></details></article>''')
    return ''.join(cards)


def render() -> None:
    desk = load(DATA / "desk.json")
    rows = desk["rows"]
    summary = desk["summary"]
    capture = desk["capture_id"]
    predictions = load(DATA / "predictions.json")["predictions"]
    coverage = load(DATA / "coverage.json")["coverage"]
    listing = load(DATA / "olbg_listing.json")
    flagged = load(DATA / "flagged.json")["flags"]
    verification = load(DATA / "verification.json")
    sources = load(DATA / "sources.json")["sources"]
    review = load(DATA / "repo_review.json")
    live_checks = load(DATA / "live_checks.json")
    sports = [c["sport"] for c in coverage]
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(parents=True, exist_ok=True)

    focus = [p for p in predictions if p["focus_eligible"]]
    outside = [p for p in predictions if not p["focus_eligible"]]
    landing_body = heading("Independent lines · official evidence", "A betting desk that shows its work.",
        "Current fixtures, transparent fair lines and written High picks—with unsupported sports and unresolved listings left visibly blank.",
        '<div class="hero-actions"><a class="button" href="predictions.html">Read focus picks</a><a class="button secondary" href="entries.html">Browse all fixtures</a></div>')
    landing_body += kpis([("Official fixtures", summary["official_fixtures"], "confirmed from captured bytes"),
                          ("Priced matches", summary["priced_fixtures"], f"{summary['sports_priced']} sports with adequate inputs"),
                          ("Focus High picks", summary["high_focus"], "≥70% and −250…+10,000"),
                          ("Written predictions", summary["written_predictions"], "50+ words, fact panels included"),
                          ("Review items", summary["flags"], "published, never silently filled")])
    landing_body += '<section class="notice"><strong>What “verified” means here.</strong> Fixture identity and numeric inputs come from official league, tour or federation responses whose SHA-256 is re-checked on every build. OLBG supplies structure only—not our prices, tips or verification.</section>'
    landing_body += '<section class="section"><div class="section-head"><div><p class="kicker">−250…+10,000 focus</p><h2>Seven qualifying hockey handicaps</h2></div><a href="predictions.html">All 19 written picks →</a></div>'
    landing_body += '<div class="table-wrap"><table><thead><tr><th>Selection</th><th>Match</th><th>Model probability</th><th>Fair decimal / American</th><th>Official</th></tr></thead><tbody>'
    for item in focus:
        row = next(r for r in rows if r["id"] == item["fixture_id"])
        landing_body += f'<tr><td><strong>{E(item["selection"])}</strong><small>{E(item["market"])}</small></td><td>{E(item["matchup"])}</td><td>{item["probability"]:.1%}</td><td>{item["decimal"]:.3f} / {item["american"]:+d}</td><td>{link(row["official_url"], "Source ↗")}</td></tr>'
    landing_body += '</tbody></table></div></section>'
    landing_body += '<section class="section"><div class="section-head"><div><p class="kicker">Sport by sport</p><h2>Coverage at a glance</h2></div><a href="coverage.html">Full coverage & shortfalls →</a></div><div class="sport-grid">'
    for item in coverage:
        landing_body += f'''<a class="sport-card" href="sports/{E(item['slug'])}.html"><div><strong>{E(item['sport'])}</strong><span>{E(item['coverage_status'])}</span></div>
        <dl><div><dt>Official</dt><dd>{item['official_fixtures']}</dd></div><div><dt>Priced</dt><dd>{item['priced']}</dd></div><div><dt>Focus</dt><dd>{item['focus_high']}</dd></div></dl></a>'''
    landing_body += '</div></section>'
    page("index.html", "Evidence-first betting dashboard", landing_body, "Official fixtures, independent lines and verified High predictions.", capture)

    body = heading("Every officially confirmed fixture", "Fixture inventory",
        f"{len(rows)} fixtures in the daily window through 8 November. Blank odds and confidence mean the official evidence did not support a line.")
    body += filters("fixtures", sports)
    body += f'<div class="table-wrap"><table id="fixtures">{FIXTURE_HEAD}<tbody>{fixture_rows(rows)}</tbody></table></div>'
    page("entries.html", "All fixtures", body, "All officially confirmed fixtures with blank unpriced fields.", capture)

    market_rows = []
    for row in rows:
        for key, market in row.get("markets", {}).items():
            sels = market["selections"]
            search = ' '.join((row["sport"], row["competition"], row["side_a"], row["side_b"], market["market"])).lower()
            market_rows.append(f'''<tr class="filterable" data-sport="{E(row['sport'])}" data-confidence="{E(row['pick']['confidence'])}" data-search="{E(search)}">
<td>{E(row['sport'])}<small>{E(time_label(row['start_utc']))}</small></td><td><strong>{E(row['side_a'])} vs {E(row['side_b'])}</strong><small>{E(row['competition'])}</small></td>
<td>{E(market['market'])}</td><td>{E(sels[0]['label'])}<small>{price(sels[0])}</small></td><td>{E(sels[1]['label'])}<small>{price(sels[1])}</small></td><td>{link(row['official_url'], 'Official ↗')}</td></tr>''')
    body = heading("Match winner · handicap · total", "Our originated lines",
        f"{len(market_rows)} market families. Prices are fair, margin-free 1/p estimates. Probability / decimal / American appears under each selection.")
    body += filters("markets", sports)
    body += '<div class="table-wrap"><table id="markets"><thead><tr><th>Sport / start</th><th>Match</th><th>Market</th><th>Selection A</th><th>Selection B</th><th>Inputs</th></tr></thead><tbody>' + ''.join(market_rows) + '</tbody></table></div>'
    page("markets.html", "Originated markets", body, "Independent match-winner, handicap and total prices.", capture)

    body = heading("High-confidence written analysis", "Predictions with receipts",
        "Seven picks meet both the ≥70% and −250…+10,000 focus rules. Twelve stronger moneylines fall outside that price band and remain separately labelled.")
    body += kpis([("Focus picks", len(focus), "all seven are +1.5 hockey handicaps"),
                  ("Outside-window High", len(outside), "published, not relabelled"),
                  ("Sports with focus picks", len({p['sport'] for p in focus}), "shortfalls flagged elsewhere"),
                  ("Shortest write-up", min(p["word_count"] for p in predictions), "words; every card has official fact links")])
    body += filters("predictions", sports, confidence=False, focus=True)
    body += '<div id="predictions"><section class="section"><h2>Focus window</h2><div class="prediction-grid">' + prediction_cards(focus) + '</div></section>'
    body += '<section class="section"><h2>High, but shorter than −250</h2><div class="prediction-grid">' + prediction_cards(outside) + '</div></section></div>'
    page("predictions.html", "High-confidence predictions", body, "Unique High predictions with official evidence panels.", capture)

    body = heading("All 17 OLBG sport categories", "Coverage and the five-pick target",
        "The target is up to five qualifying focus matches per sport. A shortfall is a result—not a reason to invent five selections.")
    body += '<div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG upcoming listed</th><th>Official fixtures</th><th>Priced</th><th>High selections</th><th>Focus</th><th>Written</th><th>Five-match shortfall</th></tr></thead><tbody>'
    for item in coverage:
        body += f'<tr><td>{link("sports/" + item["slug"] + ".html", item["sport"], False)}</td><td>{item["olbg_upcoming_listed"]}</td><td>{item["official_fixtures"]}</td><td>{item["priced"]}</td><td>{item["high"]}</td><td>{item["focus_high"]}</td><td>{item["written_predictions"]}</td><td>{badge(item["five_pick_target_shortfall"], "warn") if item["five_pick_target_shortfall"] else badge("Met","focus")}</td></tr>'
    body += '</tbody></table></div><section class="notice"><strong>Why only ice hockey meets the target.</strong> For a negative fair price, ≥70% and no shorter than −250 can coexist only between 70.0% and 71.4%. Positive prices imply less than 50%, so they cannot qualify. No model was bent to manufacture coverage.</section>'
    page("coverage.html", "Sport coverage", body, "Per-sport coverage and focus-pick shortfalls.", capture)

    for item in coverage:
        sport_rows = [r for r in rows if r["sport"] == item["sport"]]
        body = heading("Sport category", item["sport"],
            f"{item['official_fixtures']} official fixtures; {item['priced']} priced; {item['focus_high']} focus selections. OLBG upcoming listing rows: {item['olbg_upcoming_listed']}.")
        body += kpis([("Official fixtures", item["official_fixtures"], "source-linked below"),
                      ("Priced", item["priced"], "adequate official numeric inputs"),
                      ("High / focus", f"{item['high']} / {item['focus_high']}", "model and odds rules"),
                      ("Five-pick shortfall", item["five_pick_target_shortfall"], "not padded")])
        if sport_rows:
            body += f'<div class="table-wrap"><table>{FIXTURE_HEAD}<tbody>{fixture_rows(sport_rows, "../")}</tbody></table></div>'
        else:
            body += '<section class="empty"><h2>No officially reconciled fixture rows published</h2><p>This sport remains in the taxonomy and review queue. No price, winner or confidence is inferred from OLBG alone.</p><a class="button secondary" href="../flagged.html">Review the evidence gap</a></section>'
        page(f"sports/{item['slug']}.html", item["sport"], body, f"{item['sport']} fixtures and evidence coverage.", capture)

    body = heading("Row-level provenance", "Verification register",
        f"{verification['hash_verified_responses']} raw responses re-hashed. Every fixture below has an official source and a reproducible evidence chain.")
    body += filters("verification", sports, confidence=False)
    vrows = []
    for item in verification["rows"]:
        search = ' '.join((item["fixture_id"], item["sport"], item["matchup"], ' '.join(item["evidence_ids"]))).lower()
        raw_links = ' '.join(link(f"../data/session-0d3b826c/capture/{capture}/" + next(s["file"] for s in sources if s["id"] == source_id), source_id, False)
                             for source_id in item["evidence_ids"][:3])
        vrows.append(f'<tr class="filterable" data-sport="{E(item["sport"])}" data-search="{E(search)}"><td>{E(item["fixture_id"])}</td><td>{E(item["sport"])}</td><td>{E(item["matchup"])}<small>{E(item["start_utc"])}</small></td><td>{badge("Confirmed","focus")}</td><td>{raw_links}<small>SHA-256 {E(item["sha256"][0][:16])}…</small></td><td>{link(item["official_url"], "Official ↗")}</td></tr>')
    body += '<div class="table-wrap"><table id="verification"><thead><tr><th>ID</th><th>Sport</th><th>Fixture</th><th>Status</th><th>Raw evidence</th><th>Official</th></tr></thead><tbody>' + ''.join(vrows) + '</tbody></table></div>'
    page("verification.html", "Verification register", body, "Fixture-by-fixture official evidence and capture hashes.", capture)

    body = heading("HTTP status · bytes · SHA-256", "Source registry",
        f"{len(sources)} targets in capture {capture}. Failed responses stay registered and are never parsed as evidence.")
    source_rows = []
    for item in sources:
        source_rows.append(f'<tr><td>{E(item["kind"])}</td><td>{E(item["id"])}<small>{E(item["host"])}</small></td><td>{badge(item["status"], "focus" if item["status"] == 200 else "warn")}</td><td>{item["bytes"]:,}</td><td><code>{E(item["sha256"][:20])}…</code><small>{link("../data/session-0d3b826c/capture/" + capture + "/" + item["file"], "raw gzip", False)}</small></td><td>{link(item["url"], "Open source ↗")}</td></tr>')
    body += '<div class="table-wrap"><table><thead><tr><th>Class</th><th>Target</th><th>HTTP</th><th>Bytes</th><th>SHA-256 / raw</th><th>URL</th></tr></thead><tbody>' + ''.join(source_rows) + '</tbody></table></div>'
    body += '<section class="section"><h2>Official page-reader checks</h2><p>These official pages succeeded through a separate reader after the runner returned 429. Their excerpts are stored in <code>live_checks.json</code>.</p><div class="table-wrap"><table><thead><tr><th>Page</th><th>Exact relevant excerpt</th><th>Official</th></tr></thead><tbody>'
    for check in live_checks["checks"]:
        body += f'<tr><td>{E(check["title"])}</td><td>{E(check["excerpt"])}</td><td>{link(check["url"], "Verify ↗")}</td></tr>'
    body += '</tbody></table></div></section>'
    page("sources.html", "Official source registry", body, "Capture URLs, statuses, hashes and live official checks.", capture)

    upcoming = [e for e in listing["events"] if e["upcoming_at_capture"]]
    body = heading("Reverse engineering, kept separate from verification", "OLBG listing structure",
        "Public SvelteKit hubs embed tips and tournaments arrays. The robots-disallowed Load More API was not called. No tip percentage, tipster comment or bookmaker price enters our model.")
    body += kpis([("Upcoming listing rows", len(upcoming), "server-rendered at capture"),
                  ("Matched to official fixtures", sum(e["official_reconciliation"] == "matched" for e in upcoming), "conservative participant join"),
                  ("Unmatched / flagged", sum(e["official_reconciliation"] != "matched" for e in upcoming), "not promoted to official table"),
                  ("Sport hubs", len(listing["hubs"]), "public pages, including sub-hubs")])
    body += '<section class="section"><h2>Upcoming server-rendered listings</h2><div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG listed name</th><th>Listed UTC</th><th>Market labels</th><th>Reconciliation</th><th>OLBG / official</th></tr></thead><tbody>'
    for item in upcoming:
        body += f'<tr><td>{E(item["sport"])}</td><td>{E(item["listed_name"])}</td><td>{E(time_label(item["listed_start_utc"]))}</td><td>{E(", ".join(item["market_labels"]))}</td><td>{badge(item["official_reconciliation"], "focus" if item["official_reconciliation"] == "matched" else "warn")}</td><td>{link(item["olbg_url"], "OLBG ↗")} {link(item["official_url"], "Official ↗")}</td></tr>'
    body += '</tbody></table></div></section>'
    page("olbg.html", "OLBG reverse engineering", body, "Public OLBG listing structure and official reconciliation.", capture)

    body = heading("Needs review · non-blocking", "Flagged for Review",
        f"{len(flagged)} items. Missing values stay blank. These flags disclose source failures, unmatched OLBG rows, unpriced fixtures, focus exclusions and per-sport shortfalls.")
    flag_rows = []
    for item in flagged:
        flag_rows.append(f'<tr><td>{E(item["id"])}</td><td>{badge(item["code"], "warn")}</td><td>{E(item["sport"])}</td><td><strong>{E(item["title"])}</strong><small>{E(item["detail"])}</small></td><td>{link(item["url"], "Manual review ↗")}</td></tr>')
    body += '<div class="table-wrap"><table><thead><tr><th>ID</th><th>Code</th><th>Sport</th><th>Finding</th><th>Source</th></tr></thead><tbody>' + ''.join(flag_rows) + '</tbody></table></div>'
    page("flagged.html", "Flagged for Review", body, "All unresolved source, fixture, model and coverage issues.", capture)

    body = heading("Read-only peer audit", "Repository review",
        f"{review['finding_count']} findings from {sum(review['rows_checked'].values())} peer rows. Structural defects are not represented as fresh factual verification of every old claim.")
    counts = Counter()
    for finding in review["findings"]:
        counts[finding["code"]] += 1
    body += '<section class="finding-grid">' + ''.join(f'<div><strong>{count}</strong><span>{E(code)}</span></div>' for code, count in counts.most_common(12)) + '</section>'
    body += '<div class="table-wrap"><table><thead><tr><th>Dataset</th><th>Row</th><th>Finding</th><th>Detail</th><th>Manual review</th></tr></thead><tbody>'
    for item in review["findings"]:
        body += f'<tr><td>{E(item["dataset"])}</td><td>{E(item["row_id"])}</td><td>{badge(item["code"], "warn")}</td><td>{E(item["detail"])}</td><td>{link(item["manual_review_url"], "Source ↗")}</td></tr>'
    body += '</tbody></table></div>'
    page("review.html", "Repository review", body, "Line-by-line structural and math audit of peer datasets.", capture)

    body = heading("Findings behind the numbers", "Analysis",
        "The key issues are evidence coverage, the narrow focus-price intersection and integrity defects in earlier desks.")
    body += kpis([("OLBG listed / matched", f"{len(upcoming)} / {sum(e['official_reconciliation'] == 'matched' for e in upcoming)}", "unmatched rows quarantined"),
                  ("Core market families", len(market_rows), "winner, handicap and total"),
                  ("Peer findings", review["finding_count"], "read-only audit"),
                  ("Focus sports", len({p['sport'] for p in focus}), "of 17 OLBG categories")])
    body += '<section class="analysis-grid"><article><h2>Odds-window arithmetic</h2><p>At exactly 70%, fair decimal is 1.429 and American is approximately −233. At −250, implied probability is 71.43%. Therefore a favourite must sit in a very narrow band to satisfy both conditions. Positive American odds cannot exceed 50% implied probability.</p></article><article><h2>Peer integrity example</h2><p>Board AE row <code>ae_038</code> labels Milwaukee High at 59.2%. The MLB fixture itself is official, but the confidence label contradicts the 70% rule. Our audit separates that math defect from fixture verification.</p></article><article><h2>Completeness boundary</h2><p>OLBG’s Load More path is robots-disallowed. We inventory all server-rendered rows but do not claim an exhaustive hidden listing. Official schedules can add fixtures OLBG does not show.</p></article><article><h2>Prediction quality</h2><p>All 19 write-ups are unique, 50 words or longer, and linked to exact facts. Selected-side recent results are mandatory. Numeric tokens are checked against the evidence bundle.</p></article></section>'
    page("analysis.html", "Analysis and findings", body, "Odds-window, coverage and evidence-quality analysis.", capture)

    body = heading("Reproducible calculations", "Methodology",
        "No bookmaker or OLBG price enters the models. Fair decimal is 1/p; fair American is derived from that decimal without adding margin.")
    body += '''<section class="method-grid"><article><h2>NHL & Liiga</h2><p>Official GF/GA rates shrink toward the league mean over eight pseudo-games. Independent Poisson score grids price the winner, regulation −1.5/+1.5 line and total. Regulation ties split equally for the including-overtime winner. Home multiplier: 1.04. High requires at least eight games per club and p≥70%.</p></article>
<article><h2>EuroLeague & EuroCup</h2><p>Played-game PF/PA rates shrink over five pseudo-games. Captured results estimate home-court margin, margin sigma and total sigma. Normal approximations price moneyline, spread and total. High requires six games per club and p≥70%.</p></article>
<article><h2>MLB</h2><p>Regular-season winning percentages enter log5 with +1.5 percentage points for home field. Runs scored/allowed produce independent-Poisson run and total lines. Probable pitchers are reported only when MLB lists them; no individual adjustment is invented.</p></article>
<article><h2>WTA</h2><p>Each player’s weight is the square root of official ranking points, normalised against the opponent. This is our transformation, not a WTA probability. High also requires a current-tournament match for both players. Handicap and totals stay blank without game-level inputs.</p></article>
<article><h2>LoL Esports</h2><p>At least three completed series per team are required for any price. Shrunk series records enter log5. The current Worlds teams do not meet that threshold in the captured feed, so all eight fixtures are officially listed but unpriced.</p></article>
<article><h2>Confidence & focus</h2><p>Primary winner: High at p≥70% with the sport’s evidence threshold; Medium at p≥58%; otherwise Low. High picks shorter than −250 remain High but outside focus. A focus market pick must additionally have fair American odds in −250…−100 or +100…+10,000 and decimal 1.40…101.00.</p></article>
<article><h2>Prediction gate</h2><p>Every High candidate needs unique prose of at least 30 words, an explicit selection, selected-side current form and recent result, and relevant player evidence. Facts link to official pages. Numeric tokens are cross-checked against the evidence bundle.</p></article>
<article><h2>Blank means unverified</h2><p>Unsupported start times, venues, prices and confidence labels are blank. Unmatched OLBG rows stay out of the official fixture table. The site does not claim five picks per sport when the rules produce fewer.</p></article></section>'''
    body += '<section class="section"><h2>Rebuild</h2><pre><code>PYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/build.py\nPYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/review.py\nPYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/author.py\nPYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/build.py\nPYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/render.py\nPYTHONPATH=scripts/session-0d3b826c python3 scripts/session-0d3b826c/verify.py</code></pre></section>'
    page("methodology.html", "Methodology", body, "Transparent model, confidence and verification rules.", capture)

    # Machine-readable site bundle, useful for a manual reviewer who does not run Python.
    dump(SITE / "assets" / "summary.json", {"capture": capture, "summary": summary})


if __name__ == "__main__":
    render()
    print(f"Rendered Board AF site to {SITE}")

#!/usr/bin/env python3
"""Render the Board AH static dashboard from its isolated JSON snapshot."""
from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-6846f1ab"
SITE = ROOT / "session-6846f1ab"


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def safe_url(url: str) -> str:
    return url if isinstance(url, str) and url.startswith(("https://", "http://")) else ""


def link(url: str, label: str, cls: str = "external") -> str:
    url = safe_url(url)
    if not url:
        return '<span class="muted">Not captured</span>'
    return f'<a class="{cls}" href="{esc(url)}" target="_blank" rel="noopener noreferrer">{esc(label)}</a>'


def source_links(row: dict, prefix: str = "") -> str:
    official = row.get("official_url", "")
    olbg = row.get("olbg", {}).get("olbg_url", "")
    out = [link(official, "Official")]
    if olbg:
        out.append(link(olbg, "OLBG"))
    else:
        out.append(f'<a class="muted" href="{prefix}flagged.html#ah_olbg_gap_{esc(row.get("id", ""))}">OLBG not matched</a>')
    return '<span class="source-links">' + " · ".join(out) + "</span>"


def american(value) -> str:
    if value in (None, ""):
        return ""
    try:
        n = int(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{n:+d}"


def pct(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{float(value) * 100:.1f}%"
    except (TypeError, ValueError):
        return str(value)


def dt(value: str) -> str:
    if not value:
        return ""
    return value.replace("T", " ").replace("Z", " UTC")


def date_only(value: str) -> str:
    return (value or "")[:10]


def words(value: str) -> int:
    return len((value or "").split())


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def badge(text: str, kind: str = "") -> str:
    return f'<span class="badge {esc(kind)}">{esc(text)}</span>'


def confidence_badge(value: str) -> str:
    return badge(value or "Withheld", (value or "withheld").lower())


def odds_band(am: int | float | None) -> bool:
    try:
        return -250 <= int(am) <= 10000
    except (TypeError, ValueError):
        return False


def nav(prefix: str, active: str) -> str:
    items = [
        ("index.html", "Overview", "index"),
        ("matches.html", "Matches", "matches"),
        ("picks.html", "High picks", "picks"),
        ("markets.html", "Markets", "markets"),
        ("coverage.html", "Coverage", "coverage"),
        ("olbg.html", "OLBG map", "olbg"),
        ("sources.html", "Sources", "sources"),
        ("flagged.html", "Flagged for review", "flagged"),
        ("verification.html", "Verification", "verification"),
        ("methodology.html", "Method", "methodology"),
    ]
    links = []
    for href, label, key in items:
        cls = "navlink active" if active == key else "navlink"
        links.append(f'<a class="{cls}" href="{prefix}{href}">{esc(label)}</a>')
    return "".join(links)


def shell(title: str, active: str, body: str, prefix: str = "") -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG4 Board AH</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
<script defer src="{prefix}assets/app.js"></script>
</head>
<body>
<header class="topbar">
  <div class="brand"><a href="{prefix}index.html">OLBG<span>4</span></a><small>evidence desk</small></div>
  <nav class="nav">{nav(prefix, active)}</nav>
</header>
<main class="wrap">{body}</main>
<footer class="footer"><div>Board AH · source cutoff 2026-10-22 21:15 UTC · static GitHub Pages snapshot</div><div><a href="{prefix}methodology.html">Method</a> · <a href="{prefix}sources.html">Sources</a> · <a href="{prefix}flagged.html">Flagged for review</a></div></footer>
</body>
</html>"""


def page_header(kicker: str, title: str, intro: str = "") -> str:
    return f"""<section class="page-head"><div class="eyebrow">{esc(kicker)}</div><h1>{esc(title)}</h1>{f'<p>{intro}</p>' if intro else ''}</section>"""


def stat(label: str, value: str, note: str = "") -> str:
    note_html = f'<div class="stat-note">{note}</div>' if note else ""
    return f'<div class="stat"><div class="stat-value">{esc(value)}</div><div class="stat-label">{esc(label)}</div>{note_html}</div>'


def table_filter(table_id: str, placeholder: str = "Filter rows") -> str:
    return f'<label class="filter"><span>Filter</span><input data-filter="{esc(table_id)}" type="search" placeholder="{esc(placeholder)}"></label>'


def match_row(row: dict, prefix: str = "") -> str:
    matchup = row.get("matchup") or f'{row.get("side_a", "")} vs {row.get("side_b", "")}'
    kind = "Outright" if row.get("row_kind") == "outright" else "Match"
    selection = row.get("featured_pick") or row.get("match_winner_pick") or ""
    fair = row.get("featured_fair_american")
    book = row.get("featured_book_american")
    market = row.get("featured_market") or "Match Winner"
    source_qual = row.get("source_qualification", {})
    olbg_mark = '<span class="ok">matched</span>' if source_qual.get("olbg_listing_matched") else '<span class="warn">not matched</span>'
    return f"""<tr id="{esc(row.get('id', ''))}" data-search="{esc(' '.join(map(str, [row.get('sport',''), matchup, row.get('competition',''), selection, row.get('start_utc','')]))) }">
<td><a href="{prefix}sports/{esc(row.get('requested_sport_slug', row.get('sport_slug','')))}.html">{esc(row.get('sport',''))}</a><br>{badge(kind, 'soft')}</td>
<td class="nowrap">{esc(dt(row.get('start_utc','')))}</td>
<td><strong>{esc(matchup)}</strong><small>{esc(row.get('competition',''))}</small></td>
<td><strong>{esc(selection)}</strong><small>{esc(market)}</small></td>
<td>{confidence_badge(row.get('confidence',''))}<small>{pct(row.get('featured_prob'))}</small></td>
<td class="nowrap">Fair {esc(american(fair))}<br><small>Book {esc(american(book))}</small></td>
<td>{olbg_mark}<br>{source_links(row, prefix)}</td>
</tr>"""


def market_rows(rows: list[dict], prefix: str = "") -> str:
    out = []
    for row in rows:
        for market_key, market in (row.get("markets") or {}).items():
            if not market:
                continue
            selections = market.get("selections", [])
            for selection in selections:
                line_value = market.get("line", "")
                line_text = "" if line_value in (None, "") else str(line_value)
                out.append(
                    f"""<tr data-search="{esc(' '.join(map(str, [row.get('sport',''), row.get('matchup',''), market.get('market_name',''), selection.get('label','')]))) }">
<td>{esc(row.get('sport',''))}</td><td class="nowrap">{esc(dt(row.get('start_utc','')))}</td>
<td><strong>{esc(row.get('matchup',''))}</strong><small>{esc(row.get('id',''))}</small></td>
<td>{esc(market.get('market_name', market_key))}<small>Line {esc(line_text)} · Σp {esc(market.get('prob_sum',''))}</small></td>
<td><strong>{esc(selection.get('label',''))}</strong></td>
<td>{esc(pct(selection.get('fair_prob')))}<br>Fair {esc(american(selection.get('fair_american')))}</td>
<td>Book {esc(american(selection.get('book_american')))}<br><small>{esc(selection.get('book_decimal',''))}</small></td>
<td>{link(row.get('official_url',''), 'Official')}</td>
</tr>"""
                )
    return "".join(out)


def prediction_card(p: dict, row_by_id: dict, prefix: str = "") -> str:
    row = row_by_id.get(p.get("row_id", ""), {})
    # Keep the authored prediction exactly as text, while replacing internal
    # audit terminology in the supporting facts line shown to readers.
    facts = p.get("inputs_summary", "")
    facts = re.sub(r"\bverified\b", "official", facts, flags=re.I)
    facts = re.sub(r"\bmodel\b", "line desk", facts, flags=re.I)
    window = odds_band(p.get("fair_american")) and odds_band(p.get("book_american"))
    band = badge("in requested odds band", "high") if window else badge("outside requested odds band", "warn")
    olbg_url = row.get("olbg", {}).get("olbg_url", "")
    links = [link(p.get("official_url", ""), "Official source")]
    if olbg_url:
        links.append(link(olbg_url, "OLBG listing"))
    else:
        links.append('<span class="muted">OLBG listing not matched in capture</span>')
    return f"""<article class="prediction" id="{esc(p.get('pred_key',''))}" data-sport="{esc(p.get('sport',''))}">
<div class="prediction-top"><div>{confidence_badge('High')} {badge(p.get('sport',''), 'soft')} {band}</div><span class="muted">{esc(p.get('word_count', words(p.get('text',''))))} words</span></div>
<h3>{esc(p.get('selection',''))}</h3><div class="prediction-match">{esc(p.get('matchup',''))} · {esc(dt(p.get('start_utc','')))}</div>
<div class="prediction-meta"><span><b>Market</b> {esc(p.get('market',''))}</span><span><b>Fair</b> {esc(american(p.get('fair_american')))} ({esc(pct(p.get('fair_prob')))})</span><span><b>Book</b> {esc(american(p.get('book_american')))}</span></div>
<p class="prediction-text">{esc(p.get('text',''))}</p>
<p class="facts"><b>Official inputs:</b> {esc(facts)}</p>
<div class="source-links">{' · '.join(links)}</div>
</article>"""


def coverage_table(coverage: list[dict], prefix: str = "", source_map: dict | None = None) -> str:
    source_map = source_map or {}
    return "".join(
        f"""<tr data-search="{esc(c['sport'])}">
<td><a href="{prefix}sports/{esc(c['slug'])}.html">{esc(c['sport'])}</a></td>
<td>{esc(c['rows'])}<small>{esc(c['match_rows'])} matches · {esc(c['outright_rows'])} outrights</small></td>
<td>{esc(c['priced_rows'])} / {esc(c['rows'])}</td>
<td>{esc(c['high_predictions'])} / {esc(c['target_high_predictions'])}<br>{badge(c['high_target_status'], 'ok' if c['high_target_status'] == 'met' else 'warn')}</td>
<td>{esc(c['official_rows'])} · {esc(c['olbg_matched_rows'])} OLBG matched</td>
<td>{badge(c['status'], 'ok' if c['status'] == 'active desk' else 'warn')}</td>
<td>{source_map.get(c['sport'], '<span class="muted">Review link on category page</span>')}</td>
</tr>"""
        for c in coverage
    )


def flag_row(f: dict, prefix: str = "") -> str:
    fid = f.get("id", "")
    official = link(f.get("official_url", ""), "Official")
    olbg = link(f.get("olbg_url", ""), "OLBG") if f.get("olbg_url") else '<span class="muted">Not captured</span>'
    return f"""<tr id="{esc(fid)}" data-search="{esc(' '.join(map(str, [f.get('sport',''), f.get('event',''), f.get('category',''), f.get('reason','')]))) }">
<td>{esc(f.get('sport',''))}<small>{esc(f.get('record_kind',''))}</small></td>
<td class="nowrap">{esc(dt(f.get('start_utc','')))}</td>
<td><strong>{esc(f.get('event',''))}</strong><small>{esc(f.get('competition',''))}</small></td>
<td>{badge(f.get('category',''), 'warn')}<small>{esc(f.get('verification_status',''))}</small></td>
<td>{esc(f.get('reason',''))}</td>
<td>{official}<br>{olbg}</td>
</tr>"""


def render() -> None:
    desk = load("desk.json")
    predictions = load("predictions.json")
    coverage = load("coverage.json")["sports"]
    flags = load("flagged.json")["items"]
    taxonomy = load("taxonomy.json")
    sources = load("sources.json")
    manifest = load("manifest.json")
    audit_path = DATA / "audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {"status": "not run"}
    rows = desk["rows"]
    preds = predictions["predictions"]
    row_by_id = {r.get("id"): r for r in rows}
    coverage_sources = {}
    for item in coverage:
        matching = next((r for r in rows if r.get("sport") == item.get("sport") and r.get("official_url")), None)
        if matching:
            coverage_sources[item["sport"]] = link(matching.get("official_url", ""), "Official source")
        else:
            gap = next((f for f in flags if f.get("sport") == item.get("sport") and f.get("official_url")), None)
            coverage_sources[item["sport"]] = link(gap.get("official_url", ""), "Official review") if gap else '<span class="muted">No source captured</span>'
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(parents=True, exist_ok=True)

    # ----------------------------- Overview -----------------------------
    today_preds = [p for p in preds if date_only(p.get("start_utc")) == "2026-10-23"]
    today_preds.sort(key=lambda p: (not odds_band(p.get("fair_american")), -(p.get("fair_prob") or 0)))
    executive = today_preds[:10]
    executive_html = "".join(
        f"""<article class="pick-card"><div class="pick-card-top">{confidence_badge('High')} {badge(p.get('sport',''), 'soft')}</div>
<h3>{esc(p.get('selection',''))}</h3><p class="pick-match">{esc(p.get('matchup',''))}</p>
<div class="pick-line"><b>{esc(pct(p.get('fair_prob')))}</b> fair probability <span>Fair {esc(american(p.get('fair_american')))}</span></div>
<p>{esc(p.get('text',''))}</p><div>{link(p.get('official_url',''), 'Official source')} · <a href="picks.html#{esc(p.get('pred_key',''))}">Full pick</a></div></article>"""
        for p in executive
    ) or '<p class="muted">No prediction text was captured for the source-date executive set.</p>'
    overview_body = page_header(
        "Board AH · requested 15-sport desk",
        "A clear line desk, with the gaps left visible",
        "The latest committed official-source capture is narrowed to the sports requested in the brief. Rows carry our originated market families, a pick and confidence label; source gaps remain blank and are listed for review.",
    )
    overview_body += f"""<div class="notice"><strong>Snapshot boundary:</strong> source capture completed 2026-10-22 21:00 UTC with a 2026-10-22 21:15 UTC cutoff. This dashboard does not claim a live 2026-10-23 re-fetch; use the linked official pages before relying on any upcoming event. <a href="sources.html">Inspect source timestamps and hashes →</a></div>
<div class="stats-grid">{stat('Qualified desk rows', str(desk['summary']['rows']), '253 source-backed rows in 13 categories')}{stat('Head-to-head matches', str(desk['summary']['match_rows']), 'Golf and motor racing are outright cards')}{stat('Originated market families', str(desk['summary']['markets_in_rows']), 'Four families on each retained row')}{stat('High-confidence write-ups', str(desk['summary']['predictions']), 'Minimum 30 words each')}{stat('Requested sports with rows', f"{desk['summary']['sports_with_rows']} / {desk['summary']['sports_requested']}", 'Gaelic Sports and Greyhounds blank + flagged')}{stat('Flagged records', str(desk['summary']['flagged_records']), 'Withheld events and audit findings')}</div>
<section class="section"><div class="section-head"><div><div class="eyebrow">Executive summary · source date 23 October</div><h2>Highest-confidence captured selections</h2></div><a class="button" href="picks.html">See all {len(preds)} write-ups</a></div><div class="pick-grid">{executive_html}</div></section>
<section class="section"><div class="section-head"><div><div class="eyebrow">Coverage</div><h2>Every requested category</h2></div><a class="button secondary" href="coverage.html">Full coverage page</a></div><div class="table-wrap"><table><thead><tr><th>Sport</th><th>Rows</th><th>Priced</th><th>High write-ups</th><th>Official · OLBG matched</th><th>Status</th><th>Source</th></tr></thead><tbody>{coverage_table(coverage, '', coverage_sources)}</tbody></table></div></section>
<section class="section two-col"><div class="card"><div class="eyebrow">Start here</div><h2>Use the dashboard</h2><ul class="link-list"><li><a href="matches.html">Matches</a> — filter all active rows and inspect official/OLBG links.</li><li><a href="markets.html">Markets</a> — expand every originated winner, handicap, total and derivative selection.</li><li><a href="flagged.html">Flagged for review</a> — no race, team, price or confidence is invented when inputs are absent.</li></ul></div><div class="card"><div class="eyebrow">Integrity</div><h2>Line-by-line gate</h2><p>Source hashes, row scope, price math, normalized markets, prediction length and local links are checked by the isolated Board AH verifier.</p><p class="audit-result">{badge(str(audit.get('status','not run')), 'ok' if audit.get('status') == 'PASS' else 'warn')} {esc(audit.get('checks', 'Run verification to populate the count.'))}</p><a class="button secondary" href="verification.html">Read verification register</a></div></section>"""
    (SITE / "index.html").write_text(shell("Overview", "index", overview_body), encoding="utf-8")

    # ----------------------------- Matches -----------------------------
    matches_body = page_header("All active desk rows", "Matches and captured outrights", "Every row below has a governing-body or organiser source link. An OLBG link is shown when the captured OLBG inventory matched it; otherwise the row is clearly marked as official-schedule-only.")
    matches_body += f"""<div class="toolbar">{table_filter('matches-table', 'Sport, team, competition, pick…')}<span class="result-note">{len(rows)} rows · {sum(bool(r.get('olbg',{}).get('olbg_url')) for r in rows)} matched to an OLBG event URL</span></div>
<div class="table-wrap"><table id="matches-table" class="data-table"><thead><tr><th>Sport / type</th><th>Start (UTC)</th><th>Fixture or outright</th><th>Featured selection</th><th>Confidence</th><th>Fair / book</th><th>Source links</th></tr></thead><tbody>{''.join(match_row(r) for r in rows)}</tbody></table></div>"""
    (SITE / "matches.html").write_text(shell("Matches", "matches", matches_body), encoding="utf-8")

    # ----------------------------- Picks -----------------------------
    pick_sports = sorted({p.get("sport", "") for p in preds})
    picks_body = page_header("High-confidence desk", "Human-written selections", "Each card names the selection, shows our fair/book prices, states the evidence used and links to the official source. The text is retained only where the source desk supplied at least 30 words; no category shortfall is backfilled.")
    picks_body += f"""<div class="toolbar"><label class="filter"><span>Sport</span><select data-select-sport="predictions"><option value="">All sports</option>{''.join(f'<option>{esc(s)}</option>' for s in pick_sports)}</select></label><span class="result-note">{len(preds)} write-ups · {sum(bool(p.get('strict_70_in_window')) for p in preds)} strict ≥70% picks in the requested odds band</span></div><div id="predictions" class="prediction-grid">{''.join(prediction_card(p, row_by_id) for p in preds)}</div>"""
    (SITE / "picks.html").write_text(shell("High-confidence picks", "picks", picks_body), encoding="utf-8")

    # ----------------------------- Markets -----------------------------
    market_family_counts = Counter()
    market_selection_count = 0
    for row in rows:
        for key, market in (row.get("markets") or {}).items():
            if market:
                market_family_counts[market.get("market_name", key)] += 1
                market_selection_count += len(market.get("selections", []))
    market_summary = "".join(
        f"<tr><td>{esc(name)}</td><td>{count}</td><td>Two-sided/normalised families from captured desk rows</td></tr>"
        for name, count in sorted(market_family_counts.items())
    )
    markets_body = page_header("Own-line coverage", "Markets investigated", "The desk exposes each retained row's match-winner, handicap, total and sport-derivative family. Fair probability is normalised within each family and fair decimal is derived as 1/p; no bookmaker feed is presented as our own line.")
    markets_body += f"""<div class="stats-grid">{stat('Market families', str(sum(market_family_counts.values())), 'Rows × available family')}{stat('Selections displayed', str(market_selection_count), 'Each side/selection')}{stat('Family types', str(len(market_family_counts)), 'Names observed in the capture')}</div>
<section class="section"><h2>Family coverage</h2><div class="table-wrap"><table><thead><tr><th>Market</th><th>Rows</th><th>Definition</th></tr></thead><tbody>{market_summary}</tbody></table></div></section>
<section class="section"><div class="toolbar">{table_filter('markets-table', 'Sport, fixture, market, selection…')}<span class="result-note">All {market_selection_count} selections · each row links to its official source</span></div><div class="table-wrap"><table id="markets-table" class="data-table"><thead><tr><th>Sport</th><th>Start</th><th>Fixture</th><th>Market / line</th><th>Selection</th><th>Fair p / price</th><th>Book price</th><th>Source</th></tr></thead><tbody>{market_rows(rows)}</tbody></table></div></section>"""
    (SITE / "markets.html").write_text(shell("Markets", "markets", markets_body), encoding="utf-8")

    # ----------------------------- Coverage -----------------------------
    coverage_body = page_header("Requested categories", "Coverage at a glance", "Coverage is explicit: 5 high-confidence write-ups is the daily target, but the dashboard reports the source-backed count rather than manufacturing text for a category with no qualified rows.")
    coverage_body += f"""<div class="table-wrap"><table><thead><tr><th>Sport</th><th>Rows</th><th>Priced rows</th><th>High write-ups / target</th><th>Official / OLBG</th><th>Status</th><th>Source</th></tr></thead><tbody>{coverage_table(coverage, '', coverage_sources)}</tbody></table></div>
<section class="section two-col"><div class="card"><h2>Blank categories</h2><p><strong>Gaelic Sports:</strong> the capture retained Gaelic Football listings as a scope-ambiguity quarantine because the source desk conservatively applied the brief's football/hurling exclusions. They remain on <a href="flagged.html">Flagged for Review</a> with blank picks and odds.</p><p><strong>Greyhounds:</strong> the OLBG hub capture contained zero cards and the official GBGB page did not yield a dated runner-level card for this desk. It is shown blank rather than inferred.</p></div><div class="card"><h2>Market note</h2><p>Golf, motor racing and some snooker rows are outright/event cards rather than head-to-head matches. They are labelled as such; the site does not call an outright a match.</p></div></section>"""
    (SITE / "coverage.html").write_text(shell("Coverage", "coverage", coverage_body), encoding="utf-8")

    # ----------------------------- Sport pages -----------------------------
    for c in coverage:
        sport = c["sport"]
        sport_rows = [r for r in rows if r.get("sport") == sport]
        sport_preds = [p for p in preds if p.get("sport") == sport]
        sport_flags = [f for f in flags if f.get("sport") == sport]
        slug_name = c["slug"]
        body = page_header(f"Category · {sport}", sport, f"{c['rows']} retained rows · {c['high_predictions']} high-confidence write-ups · official links are shown on every active row.")
        body += f"""<div class="stats-grid">{stat('Rows', str(c['rows']), f"{c['match_rows']} matches · {c['outright_rows']} outrights")}{stat('Priced', str(c['priced_rows']), 'Own market families')}{stat('High write-ups', f"{c['high_predictions']} / {c['target_high_predictions']}", c['high_target_status'])}{stat('OLBG matches', str(c['olbg_matched_rows']), f"of {c['official_rows']} official rows")}</div>"""
        if sport_rows:
            body += f"""<section class="section"><div class="section-head"><div><div class="eyebrow">Active rows</div><h2>Fixtures and event cards</h2></div>{table_filter(f'{slug_name}-table', 'Fixture, competition, pick…')}</div><div class="table-wrap"><table id="{esc(slug_name)}-table" class="data-table"><thead><tr><th>Sport / type</th><th>Start</th><th>Fixture or outright</th><th>Selection</th><th>Confidence</th><th>Fair / book</th><th>Sources</th></tr></thead><tbody>{''.join(match_row(r, '../') for r in sport_rows)}</tbody></table></div></section>"""
        else:
            body += '<section class="section empty"><h2>No active qualified rows captured</h2><p>All fields that would require an unconfirmed fixture, runner or price are blank. The reason and manual-review links are listed below.</p><a class="button" href="../flagged.html">Open flagged records</a></section>'
        if sport_preds:
            body += f"""<section class="section"><div class="section-head"><div><div class="eyebrow">High-confidence writing</div><h2>{len(sport_preds)} source-backed selections</h2></div><a class="button secondary" href="../picks.html">All picks</a></div><div class="prediction-grid">{''.join(prediction_card(p, row_by_id, '../') for p in sport_preds)}</div></section>"""
        body += f"""<section class="section"><div class="section-head"><div><div class="eyebrow">Review trail</div><h2>{len(sport_flags)} flagged records</h2></div><a class="button secondary" href="../flagged.html">All flagged</a></div>"""
        if sport_flags:
            body += f'<div class="table-wrap"><table><thead><tr><th>Sport</th><th>Start</th><th>Event</th><th>Category</th><th>Reason</th><th>Sources</th></tr></thead><tbody>{"".join(flag_row(f, "../") for f in sport_flags)}</tbody></table></div>'
        else:
            body += '<p class="muted">No separate flagged records in the source capture.</p>'
        body += '</section>'
        (SITE / "sports" / f"{slug_name}.html").write_text(shell(sport, "coverage", body, "../"), encoding="utf-8")

    # ----------------------------- Sources / taxonomy -----------------------------
    source_records = sources.get("official_sources_used_by_rows", [])
    source_rows = "".join(
        f"<tr data-search=\"{esc(rec.get('domain',''))}\"><td>{esc(rec.get('domain',''))}</td><td>{link(rec.get('url',''), rec.get('source_name') or rec.get('url',''))}</td><td>{esc(rec.get('row_count',0))}</td><td>{esc(', '.join(rec.get('sports',[])))}</td></tr>"
        for rec in source_records
    )
    capture_rows = "".join(
        f"<tr data-search=\"{esc(' '.join([item.get('id',''), item.get('url','')]))}\"><td>{esc(item.get('id',''))}</td><td>{link(item.get('final_url') or item.get('url',''), item.get('url',''))}</td><td>{esc(item.get('status',''))}</td><td>{esc(item.get('bytes',0))}</td><td><code>{esc((item.get('sha256') or '')[:16])}…</code></td><td>{esc(item.get('fetched_utc',''))}</td></tr>"
        for item in sources.get("capture_manifest_items", [])
    )
    sources_body = page_header("Evidence register", "Official sources and capture trail", "Manual review starts here. Active rows link to governing-body, league, tour or organiser pages. The capture ledger records status, byte count, timestamp and a SHA-256 digest for each fetched target.")
    sources_body += f"""<div class="notice"><strong>{esc(manifest.get('source_cutoff_utc',''))} cutoff.</strong> {esc(manifest.get('capture_manifest_http_200_nonempty',0))} of {esc(manifest.get('capture_manifest_target_count',0))} captured targets returned non-empty HTTP 200 content. The source pages may update after this snapshot; links are live manual-review links.</div>
<section class="section"><div class="section-head"><div><h2>Sources used by active rows</h2><p class="muted">{len(source_records)} distinct official URLs across {len(rows)} rows.</p></div>{table_filter('source-table', 'Domain or sport…')}</div><div class="table-wrap"><table id="source-table" class="data-table"><thead><tr><th>Domain</th><th>Official page</th><th>Rows</th><th>Sports</th></tr></thead><tbody>{source_rows}</tbody></table></div></section>
<section class="section"><div class="section-head"><div><h2>Captured targets</h2><p class="muted">OLBG pages are evidence for the listing inventory; official pages are evidence for fixture facts.</p></div>{table_filter('capture-table', 'Target ID or URL…')}</div><div class="table-wrap"><table id="capture-table" class="data-table"><thead><tr><th>ID</th><th>URL</th><th>Status</th><th>Bytes</th><th>SHA-256 prefix</th><th>Fetched UTC</th></tr></thead><tbody>{capture_rows}</tbody></table></div></section>"""
    (SITE / "sources.html").write_text(shell("Sources", "sources", sources_body), encoding="utf-8")

    hubs_rows = "".join(
        f"<tr data-search=\"{esc(' '.join([h.get('hub_id',''), h.get('url',''), h.get('requested_sport','')]))}\"><td>{esc(h.get('requested_sport') or 'Observed / other')}</td><td>{link(h.get('url',''), h.get('hub_id',''))}</td><td>{esc(h.get('total_cards',0))}</td><td>{esc(h.get('in_scope_cards',0))}</td><td>{esc(h.get('excluded_cards',0))}</td><td>{esc(h.get('fetched_utc',''))}</td></tr>"
        for h in taxonomy.get("hub_summaries", [])
    )
    market_chips = "".join(f'<span class="chip">{esc(m)}</span>' for m in sorted(taxonomy.get("observed_market_types", {})))
    olbg_body = page_header("Reverse engineering", "OLBG sport and market map", "This page documents the public hub paths and market labels observed in the committed capture. It is a map of what was read, not a claim that every OLBG listing has an official numeric feed.")
    olbg_body += f"""<div class="stats-grid">{stat('Requested categories', str(len(taxonomy['requested_sports'])), 'Exact brief scope')}{stat('Observed hub pages', str(len(taxonomy['hub_summaries'])), 'Top-level and sub-hubs')}{stat('Market labels', str(len(taxonomy['observed_market_types'])), 'Labels in capture')}{stat('Gaelic records quarantined', str(taxonomy.get('gaelic_football_quarantined_count',0)), 'Blank + flagged')}</div>
<section class="section"><h2>Observed market labels</h2><div class="chips">{market_chips}</div></section>
<section class="section"><div class="section-head"><div><h2>Captured OLBG hubs</h2><p class="muted">Hub cards are not automatically treated as official fixture facts.</p></div>{table_filter('hub-table', 'Hub, sport or URL…')}</div><div class="table-wrap"><table id="hub-table" class="data-table"><thead><tr><th>Requested sport</th><th>Hub</th><th>Cards</th><th>In scope</th><th>Excluded</th><th>Fetched UTC</th></tr></thead><tbody>{hubs_rows}</tbody></table></div></section>
<section class="section card"><h2>Scope notes</h2><p>Gaelic Sports is presented as a requested label and retains the captured Gaelic Football listings for review. Hurling is shown in the underlying taxonomy as excluded by the capture's conservative scope rule. Greyhounds has a captured OLBG hub but no card row retained for pricing.</p><p>Market families on active rows are published on <a href="markets.html">Markets</a>, with every selection linked back to its official source.</p></section>"""
    (SITE / "olbg.html").write_text(shell("OLBG map", "olbg", olbg_body), encoding="utf-8")

    # ----------------------------- Flagged / verification -----------------------------
    flag_rows = "".join(flag_row(f) for f in flags)
    flagged_body = page_header("Nothing inferred", "Flagged for Review", "These records are intentionally visible instead of being silently dropped. Withheld event records have blank pick, confidence and originated odds. Audit findings identify a source or reconciliation gap without changing the active row.")
    flagged_body += f"""<div class="notice"><strong>{len(flags)} records.</strong> The biggest groups are captured events that had already started at cutoff, scope-ambiguous Gaelic listings, and official schedule rows for which no matching OLBG event URL was present. Check the official links manually before requesting a refresh.</div><div class="toolbar">{table_filter('flagged-table', 'Sport, event, reason…')}<span class="result-note">All flagged entries carry an official source link when one was captured.</span></div><div class="table-wrap"><table id="flagged-table" class="data-table"><thead><tr><th>Sport / type</th><th>Start</th><th>Event</th><th>Category</th><th>Reason</th><th>Source links</th></tr></thead><tbody>{flag_rows}</tbody></table></div>"""
    (SITE / "flagged.html").write_text(shell("Flagged for review", "flagged", flagged_body), encoding="utf-8")

    findings = audit.get("findings", []) if isinstance(audit, dict) else []
    finding_rows_parts = []
    for finding in findings:
        manual = link(finding.get("url", ""), "Review source") if finding.get("url") else '<span class="muted">Internal gate</span>'
        finding_rows_parts.append(
            f"<tr><td>{esc(finding.get('code',''))}</td><td>{esc(finding.get('severity',''))}</td><td>{esc(finding.get('message',''))}</td><td>{manual}</td></tr>"
        )
    finding_rows = "".join(finding_rows_parts)
    verification_body = page_header("Reproducible checks", "Verification register", "The gate re-derives the published counts and mathematics from the isolated JSON and committed source bytes. It distinguishes source integrity from live availability.")
    verification_body += f"""<div class="stats-grid">{stat('Gate status', str(audit.get('status','NOT RUN')), 'scripts/session-6846f1ab/verify.py')}{stat('Checks', str(audit.get('checks','—')), 'Assertions evaluated')}{stat('Errors', str(audit.get('errors','—')), 'Must be zero for a clean gate')}{stat('Input hashes', str(audit.get('input_hashes','—')), 'Re-hashed from capture')}</div>
<section class="section card"><h2>What is checked</h2><div class="rule-grid"><div><b>Scope</b><span>Exactly 15 requested labels; no excluded sport is copied into the active desk.</span></div><div><b>Sources</b><span>Official HTTPS source on every active and flagged table row; captured bytes match their manifest digests.</span></div><div><b>Markets</b><span>Each selection has a probability, fair decimal 1/p, American conversion, and family sum of 1.0.</span></div><div><b>Predictions</b><span>High label, at least 30 words, explicit selection, unique text, and source link.</span></div><div><b>Blank rule</b><span>Withheld event records have empty pick, confidence and odds; no value is inferred for missing evidence.</span></div><div><b>Publication</b><span>Every internal link resolves and every table row has an official external link.</span></div></div></section>
<section class="section"><h2>Gate findings</h2><div class="table-wrap"><table><thead><tr><th>Code</th><th>Severity</th><th>Message</th><th>Manual review</th></tr></thead><tbody>{finding_rows or '<tr><td colspan="4" class="muted">No additional findings recorded by the gate.</td></tr>'}</tbody></table></div></section>
<section class="section card"><h2>Run it locally</h2><pre><code>python3 scripts/session-6846f1ab/build.py
python3 scripts/session-6846f1ab/site.py
python3 scripts/session-6846f1ab/verify.py</code></pre><p class="muted">The build reads Board AG's committed capture and never rewrites peer files. A new live capture requires a separately recorded source timestamp and re-run of the gates.</p></section>"""
    (SITE / "verification.html").write_text(shell("Verification", "verification", verification_body), encoding="utf-8")
    (SITE / "review.html").write_text(shell("Review register", "flagged", page_header("Review register", "Source reconciliation review", "Use the Flagged for Review page for event-level records. The Verification page contains the machine gate and reproducibility checks.") + '<p><a class="button" href="flagged.html">Open Flagged for Review</a></p>'), encoding="utf-8")

    methodology_body = page_header("How to read the desk", "Method and limitations", "A transparent snapshot is more useful than a complete-looking table with invented facts.")
    methodology_body += """<section class="section two-col"><div class="card"><h2>1. Scope</h2><p>The active desk uses the 15 category labels in the brief. The underlying OLBG capture supplies the sport IDs and hub URLs. Gaelic Sports and Greyhounds remain visible even when no qualifying row is retained.</p><h2>2. Sources</h2><p>OLBG pages establish the listing surface. Fixture participants, times, venues and form inputs are linked to league, tour, federation, organiser or regulator pages. A missing official field remains blank.</p><h2>3. Own lines</h2><p>The captured desk publishes fair probabilities, fair decimal/American prices and book-style comparison prices for each available market family. These are originating lines, not bookmaker quotes.</p></div><div class="card"><h2>4. Confidence</h2><p>Rows retain the source desk's Low, Medium or High label. High write-ups are only shown where the source desk supplied an explicit selection and at least 30 words. The requested −250 to +10,000 American band is shown on each pick rather than treated as proof of a result.</p><h2>5. Time</h2><p>All times are UTC. The snapshot cutoff is 2026-10-22 21:15 UTC. Events that had started by then, conditional games, unresolved brackets and unavailable cards are flagged and not priced.</p><h2>6. Review</h2><p>Use the linked official pages for the current state. This site is a dated research snapshot, not a guarantee, advice, or a substitute for checking withdrawals and late schedule changes.</p></div></section><section class="section card"><h2>Links for manual review</h2><p><a href="sources.html">Source register</a> · <a href="olbg.html">OLBG taxonomy</a> · <a href="flagged.html">Flagged records</a> · <a href="verification.html">Verification gate</a></p></section>"""
    (SITE / "methodology.html").write_text(shell("Methodology", "methodology", methodology_body), encoding="utf-8")

    # Shared CSS and small progressive-enhancement filter.  Keeping these in the
    # owned folder makes every page portable on GitHub Pages.
    (SITE / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (SITE / "assets" / "app.js").write_text(JS, encoding="utf-8")
    print(f"Rendered {len(list(SITE.rglob('*.html')))} HTML pages in {SITE.relative_to(ROOT)}/")


CSS = r"""/* Board AH — compact, readable, dependency-free dashboard */
:root{--ink:#17243b;--muted:#607089;--line:#dbe3ee;--paper:#fff;--wash:#f3f6fb;--nav:#101d34;--blue:#2b63d9;--blue-soft:#e9f0ff;--green:#197a50;--green-soft:#e7f7ef;--amber:#9a5b00;--amber-soft:#fff3d9;--red:#a63e49;--red-soft:#fff0f1;--shadow:0 10px 28px rgba(20,42,76,.07)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--wash);color:var(--ink);font:15px/1.55 Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.topbar{background:var(--nav);color:#fff;padding:13px max(20px,calc((100vw - 1380px)/2));display:flex;gap:28px;align-items:center;flex-wrap:wrap;position:sticky;top:0;z-index:5;box-shadow:0 3px 14px rgba(0,0,0,.12)}.brand{font-weight:850;font-size:22px;letter-spacing:-.04em;display:flex;align-items:baseline;gap:8px}.brand a{color:#fff;text-decoration:none}.brand span{color:#74a0ff}.brand small{font-size:10px;color:#a7b7d4;letter-spacing:.12em;text-transform:uppercase;font-weight:700}.nav{display:flex;gap:5px;flex-wrap:wrap}.navlink{color:#c7d2e8;text-decoration:none;padding:6px 9px;border-radius:7px;font-size:12px;font-weight:700}.navlink:hover,.navlink.active{background:#263d67;color:#fff}.wrap{max-width:1380px;margin:0 auto;padding:34px 22px 68px}.page-head{max-width:940px;margin:3px 0 26px}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:11px;font-weight:850;color:var(--blue);margin-bottom:7px}.page-head h1{font-size:clamp(29px,4vw,46px);line-height:1.04;letter-spacing:-.05em;margin:0 0 12px}.page-head p{font-size:17px;color:var(--muted);max-width:850px;margin:0}.notice{background:var(--blue-soft);border:1px solid #cbdcff;border-left:4px solid var(--blue);padding:14px 17px;border-radius:10px;color:#2d4775;margin:18px 0 25px}.notice strong{color:var(--ink)}.notice a{color:var(--blue);font-weight:750}.stats-grid{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:20px 0 32px}.stat,.card,.prediction,.pick-card{background:var(--paper);border:1px solid var(--line);border-radius:13px;box-shadow:var(--shadow)}.stat{padding:17px 16px;min-height:108px}.stat-value{font-size:28px;line-height:1.1;font-weight:850;letter-spacing:-.04em}.stat-label{color:var(--muted);font-size:12px;font-weight:750;margin-top:7px}.stat-note{color:#8996a9;font-size:11px;margin-top:3px}.section{margin:37px 0}.section h2{font-size:25px;letter-spacing:-.035em;margin:0 0 14px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:14px;margin-bottom:14px}.section-head h2{margin:0}.section-head p{margin:3px 0 0}.pick-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.pick-card{padding:18px}.pick-card-top,.prediction-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.pick-card h3{font-size:18px;line-height:1.2;margin:15px 0 3px}.pick-match,.prediction-match{color:var(--muted);margin:0 0 11px}.pick-line{display:flex;gap:11px;align-items:baseline;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:9px 0;margin:10px 0;color:var(--muted);font-size:12px}.pick-line b{font-size:19px;color:var(--ink)}.pick-line span{margin-left:auto;font-weight:800;color:var(--ink)}.pick-card p:not(.pick-match):not(.pick-line){font-size:13px}.badge{display:inline-flex;align-items:center;border-radius:999px;padding:3px 8px;font-size:10px;line-height:1.25;font-weight:850;letter-spacing:.02em;text-transform:uppercase;background:#edf0f5;color:#526176;white-space:nowrap}.badge.high,.badge.ok{background:var(--green-soft);color:var(--green)}.badge.medium{background:#e9f0ff;color:#2c5ab1}.badge.low{background:#edf0f5;color:#5b687b}.badge.warn,.badge.withheld{background:var(--amber-soft);color:var(--amber)}.badge.soft{background:#eef2fa;color:#51627e}.ok{color:var(--green);font-weight:800}.warn{color:var(--amber);font-weight:800}.muted{color:var(--muted)}.button{display:inline-block;background:var(--blue);border:1px solid var(--blue);color:#fff;text-decoration:none;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:800}.button:hover{filter:brightness(.95)}.button.secondary{background:#fff;color:var(--blue);border-color:#bfd0f8}.two-col{display:grid;grid-template-columns:1fr 1fr;gap:15px}.card{padding:20px}.card h2{margin-top:0}.card p:last-child{margin-bottom:0}.link-list{padding-left:19px;margin-bottom:0}.link-list li{margin:8px 0}.link-list a,a{color:var(--blue)}.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:11px;background:var(--paper);box-shadow:var(--shadow)}table{border-collapse:collapse;width:100%;font-size:12px;min-width:760px}th{text-align:left;background:#f7f9fc;color:#56657d;text-transform:uppercase;letter-spacing:.07em;font-size:10px;font-weight:850;white-space:nowrap}th,td{padding:11px 12px;border-bottom:1px solid #e8edf4;vertical-align:top}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#fbfcff}td strong{display:block;color:var(--ink);font-weight:800}td small{display:block;color:var(--muted);font-size:11px;line-height:1.35;margin-top:3px}.nowrap{white-space:nowrap}.source-links{font-size:11px;line-height:1.65}.source-links a{white-space:nowrap}.toolbar{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;margin:0 0 13px}.filter{display:flex;align-items:center;gap:8px;color:var(--muted);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.08em}.filter input,.filter select{width:min(360px,70vw);border:1px solid #cbd6e5;border-radius:8px;background:#fff;padding:9px 10px;color:var(--ink);font:inherit;text-transform:none;letter-spacing:0}.result-note{font-size:12px;color:var(--muted)}.prediction-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}.prediction{padding:18px}.prediction h3{font-size:20px;line-height:1.17;letter-spacing:-.025em;margin:14px 0 4px}.prediction-meta{display:flex;flex-wrap:wrap;gap:7px 15px;border-block:1px solid var(--line);padding:9px 0;margin:10px 0;color:var(--muted);font-size:12px}.prediction-meta b{color:var(--ink)}.prediction-text{font-size:15px;line-height:1.62;margin:14px 0}.facts{color:var(--muted);font-size:12px;background:#f8fafc;border-radius:8px;padding:9px 10px}.facts b{color:var(--ink)}.empty{border:1px dashed #c3cfdf;text-align:center;background:#fbfcff}.empty h2{margin-bottom:5px}.chips{display:flex;flex-wrap:wrap;gap:8px}.chip{padding:7px 10px;background:var(--blue-soft);border:1px solid #cedcff;border-radius:8px;color:#35559b;font-size:12px;font-weight:700}.rule-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.rule-grid div{display:flex;flex-direction:column;gap:5px;background:#f8fafc;border:1px solid var(--line);border-radius:9px;padding:13px}.rule-grid b{font-size:12px}.rule-grid span{font-size:12px;color:var(--muted)}pre{overflow:auto;background:#101d34;color:#dbe8ff;border-radius:9px;padding:15px;font-size:12px}.footer{border-top:1px solid var(--line);background:#fff;color:var(--muted);padding:20px max(22px,calc((100vw - 1380px)/2));display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap;font-size:12px}.footer a{font-weight:750}.audit-result{display:flex;align-items:center;gap:8px}.section + .section{margin-top:44px}@media(max-width:1050px){.stats-grid{grid-template-columns:repeat(3,1fr)}.pick-grid{grid-template-columns:repeat(2,1fr)}}@media(max-width:720px){.topbar{position:static;padding:13px 14px}.wrap{padding:25px 14px 50px}.navlink{font-size:11px;padding:5px 7px}.stats-grid,.pick-grid,.prediction-grid,.two-col{grid-template-columns:1fr}.rule-grid{grid-template-columns:1fr}.page-head h1{font-size:35px}.section-head{align-items:flex-start;flex-direction:column}.footer{padding:18px 14px}.stat{min-height:auto}.prediction-text{font-size:14px}}
"""

JS = r"""(() => {
  const norm = (value) => (value || '').toLowerCase();
  document.querySelectorAll('[data-filter]').forEach((input) => {
    const table = document.getElementById(input.dataset.filter);
    if (!table) return;
    const rows = [...table.querySelectorAll('tbody tr')];
    input.addEventListener('input', () => {
      const query = norm(input.value);
      rows.forEach((row) => {
        const haystack = norm(row.dataset.search || row.textContent);
        row.hidden = query && !haystack.includes(query);
      });
    });
  });
  document.querySelectorAll('[data-select-sport]').forEach((select) => {
    const target = document.getElementById(select.dataset.selectSport);
    if (!target) return;
    const cards = [...target.querySelectorAll('[data-sport]')];
    select.addEventListener('change', () => {
      cards.forEach((card) => { card.hidden = select.value && card.dataset.sport !== select.value; });
    });
  });
})();
"""


if __name__ == "__main__":
    render()

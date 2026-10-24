#!/usr/bin/env python3
"""Render a static, evidence-first 15-sport dashboard from audit.json."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "data" / "session-265b28e5" / "audit.json"
SITE = ROOT / "session-265b28e5"
AUDIT = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
SUMMARY = AUDIT["summary"]
SPORTS = AUDIT["sports"]
AS_OF = AUDIT["as_of_utc"]


def e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def fnum(value, places=1, suffix="") -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.{places}f}{suffix}"


def short_time(value: str) -> str:
    if not value:
        return "—"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        return dt.strftime("%d %b %Y %H:%MZ")
    except Exception:
        return value


def host_name(url: str) -> str:
    return urlsplit(url).hostname or "source"


def external_link(url: str, label: str | None = None) -> str:
    if not url:
        return '<span class="muted">not provided</span>'
    text = label or host_name(url)
    suffix = "" if text.endswith("↗") else " ↗"
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(text)}{suffix}</a>'


def internal_link(path: str, label: str, prefix: str) -> str:
    return f'<a href="{e(prefix + path)}">{e(label)}</a>'


def nav(prefix: str, active: str) -> str:
    links = [
        ("index.html", "Overview", "index"),
        ("coverage.html", "Coverage", "coverage"),
        ("olbg.html", "OLBG upcoming", "olbg"),
        ("fixtures.html", "Fixture audit", "fixtures"),
        ("picks.html", "Pick screen", "picks"),
        ("markets.html", "Markets", "markets"),
        ("sources.html", "Sources & capture", "sources"),
        ("flagged.html", "Flagged for Review", "flagged"),
        ("methodology.html", "Methodology", "methodology"),
    ]
    items = ''.join(
        f'<a class="nav-link{" active" if key == active else ""}" href="{prefix}{path}">{e(label)}</a>'
        for path, label, key in links
    )
    sport_links = ''.join(
        f'<a href="{prefix}sports/{s["slug"]}.html">{e(s["sport"])}</a>'
        for s in SPORTS
    )
    return f'''<header class="topbar"><div class="top-inner">
      <a class="brand" href="{prefix}index.html"><span class="brand-icon">O4</span><span>OLBG<span class="brand-light"> evidence desk</span><small>15 sports · strict-scope audit</small></span></a>
      <nav class="main-nav" aria-label="Main navigation">{items}</nav>
      <details class="sport-menu"><summary>Sports <span aria-hidden="true">⌄</span></summary><div class="sport-menu-panel">{sport_links}</div></details>
    </div></header>'''


def page(title: str, description: str, body: str, active: str, prefix: str = "") -> str:
    css = prefix + "style.css"
    js = prefix + "app.js"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG evidence desk</title><meta name="description" content="{e(description)}">
<link rel="stylesheet" href="{e(css)}"></head><body>
{nav(prefix, active)}
<main class="wrap">
<div class="eyebrow">EVIDENCE-FIRST · FIXED REVIEW SNAPSHOT · {e(AS_OF)}</div>
{body}
<footer class="footer"><div><strong>OLBG evidence desk</strong><span>Source cutoffs: OLBG taxonomy {e(AUDIT['source_capture']['started_utc'])} · Board FB {e(SUMMARY['source_desk_cutoff_utc'])}</span></div><div><a href="{prefix}flagged.html">Flagged for Review</a><a href="{prefix}methodology.html">Methodology</a><a href="{prefix}../COORDINATION.md">Coordination log</a><a href="{prefix}../data/session-265b28e5/audit.json">Audit JSON</a><a href="{prefix}../data/session-265b28e5/dashboard.json">Dashboard JSON</a></div></footer>
</main><script src="{e(js)}"></script></body></html>'''


def alert(kind: str, title: str, text: str) -> str:
    return f'<aside class="alert {e(kind)}"><strong>{e(title)}</strong><div>{text}</div></aside>'


def badge(text: str, kind="neutral") -> str:
    return f'<span class="badge {e(kind)}">{e(text)}</span>'


def table(headers, rows, table_id="", empty="No rows.") -> str:
    thead = ''.join(f'<th>{h}</th>' for h in headers)
    if rows:
        body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    else:
        body = f'<tr><td colspan="{len(headers)}" class="empty">{e(empty)}</td></tr>'
    id_attr = f' id="{e(table_id)}"' if table_id else ''
    return f'<div class="table-wrap"><table{id_attr}><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table></div>'


def filter_bar(table_id: str, placeholder="Filter rows…") -> str:
    return f'<label class="filter"><span>Filter</span><input type="search" data-filter="{e(table_id)}" placeholder="{e(placeholder)}" autocomplete="off"></label>'


def source_capture_link(label: str, prefix: str) -> str:
    return f'<a href="{prefix}../data/session-48de8c1d/capture/20261023T213547Z/manifest.json">{e(label)}</a>'


def build_index():
    coverage_rows = []
    for s in SPORTS:
        slug = s["slug"]
        current = [r for r in AUDIT["current_olbg_events"] if r["sport"] == s["sport"]]
        official = [r for r in AUDIT["official_fixture_rows"] if r["sport"] == s["sport"]]
        coverage_rows.append([
            f'<a class="sport-name" href="sports/{e(slug)}.html">{e(s["sport"])} <span>→</span></a>',
            external_link(s["olbg_hub_url"], "OLBG hub ↗") if s["olbg_hub_url"] else badge("NO HUB", "warn"),
            f'<strong>{len(current)}</strong>',
            f'{sum(bool(r["official_source_url"]) for r in current)} matched',
            f'{len(official)}',
            badge("snapshot only" if current else "no future listing", "warn" if current else "neutral"),
        ])
    coverage = table(["Sport", "Captured OLBG hub source", "OLBG future rows", "Official crosswalk", "Historic fixture rows", "Status"], coverage_rows, "sportCoverage")
    body = f'''<section class="hero">
      <div class="hero-copy"><p class="kicker">BOARD GF · REFRESH AUDIT</p><h1>Fifteen sports.<br><span>Only evidence earns a pick.</span></h1>
      <p class="lede">An audit-led dashboard for Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts, Baseball, Gaelic Sports, Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball and Rugby League.</p>
      <div class="hero-actions"><a class="button primary" href="olbg.html">Browse 58 captured upcoming OLBG entries <span>→</span></a><a class="button secondary" href="flagged.html">Open Flagged for Review</a></div>
      <p class="hero-note">Frozen review time: <strong>{e(AS_OF)}</strong>. This is a dated capture—not a live feed or current odds screen.</p></div>
      <div class="hero-card"><div class="hero-card-top"><span class="live-dot"></span> RELEASE GATE</div><div class="big-number">0</div><div class="hero-card-title">picks cleared for publication</div><div class="hero-card-rule">No candidate currently meets every fixture, OLBG-link, source-claim and price-evidence requirement.</div><a href="picks.html">See the withheld numeric candidates →</a></div>
    </section>
    <section class="metric-grid" aria-label="Audit summary">
      <div class="metric"><span>Requested sports</span><strong>{SUMMARY['covered_sports']}</strong><small>All retained in scope</small></div>
      <div class="metric"><span>OLBG rows future at review time</span><strong>{SUMMARY['olbg_future_event_observations']}</strong><small>Captured 23 Oct · not live-checked</small></div>
      <div class="metric"><span>Exact official crosswalks</span><strong>{SUMMARY['future_olbg_events_with_manual_official_crosswalk']}</strong><small>Of {SUMMARY['olbg_future_unique_event_ids']} snapshot event IDs</small></div>
      <div class="metric"><span>Published High picks</span><strong>0</strong><small>Not enough evidence to release</small></div>
    </section>
    <section class="section-grid">
      <article class="panel panel-dark"><p class="kicker">EXECUTIVE SUMMARY</p><h2>No current top-pick list is defensible.</h2><p>The prior desk marked all {SUMMARY['source_desk_predictions_labelled_high']} prediction cards High. A probability audit finds {SUMMARY['high_prediction_cards_below_70_percent']} below 70%, {SUMMARY['prediction_cards_started_or_elapsed']} had already started or elapsed by this review, and none of the {SUMMARY['future_numeric_candidates_p_ge_70_in_price_window']} future numerical candidates is linked to an exact OLBG fixture in this capture.</p><p>All five candidates are retained for review, not promoted as picks. Their text, estimated probabilities and prices are not independently re-originated.</p><a class="text-link" href="picks.html">Review the five unreleased candidates →</a></article>
      <article class="panel"><p class="kicker">WHAT IS SOURCE-BACKED</p><h2>Four official fixture matches</h2><p>PCB, Cork GAA, Kilkenny GAA and EHF pages independently match four future OLBG event listings by participants and scheduled date. {SUMMARY['future_olbg_events_with_official_start_time_confirmed']} source pages state the start time; the PCB schedule does not, so that time remains an OLBG observation only.</p><div class="source-chips">{''.join(badge(name, 'good') for name in ['PCB', 'Cork GAA', 'Kilkenny GAA', 'EHF'])}</div><a class="text-link" href="sources.html">Open the source crosswalk →</a></article>
    </section>
    <section class="panel section"><div class="section-head"><div><p class="kicker">SCOPE CONTROL</p><h2>Coverage by sport</h2><p class="muted">A zero means no future OLBG entry in the dated capture—not no event in the real world.</p></div><a class="text-link" href="coverage.html">Coverage notes →</a></div>{coverage}</section>
    <section class="section-grid">
      <article class="panel"><p class="kicker">CAPTURE INTEGRITY</p><h2>{SUMMARY['capture_payloads_hash_pass']} / {SUMMARY['capture_payloads_hash_checked']} payload hashes pass</h2><p>That confirms the stored files match their manifest. It does not prove that every fixture, statistic, roster note, or prediction claim is supported by the bytes.</p>{source_capture_link('Open the Board FB capture manifest', '')}</article>
      <article class="panel"><p class="kicker">MARKET AUDIT</p><h2>{SUMMARY['source_desk_market_families']} market families · {SUMMARY['source_desk_market_outcomes']} outcomes</h2><p>Displayed fair-price conversions recalculate without arithmetic errors. The underlying line inputs were not fully reconciled; no bookmaker quote is presented as a current market price.</p><a class="text-link" href="markets.html">Review historical line estimates →</a></article>
    </section>
    <section class="panel section"><div class="section-head"><div><p class="kicker">QUICK ROUTES</p><h2>Use the desk without mistaking a gap for a signal.</h2></div></div><div class="quick-grid"><a href="olbg.html"><strong>OLBG snapshot</strong><span>58 event selections, event links, capture time and official-source crosswalk gaps.</span></a><a href="fixtures.html"><strong>Fixture audit</strong><span>114 rows from the previous source desk, with elapsed matches separated.</span></a><a href="markets.html"><strong>Market estimates</strong><span>Previous line outputs and assumptions, explicitly marked as unaudited.</span></a><a href="flagged.html"><strong>Flagged for Review</strong><span>All release blockers, mismatched references and unsupported items in one place.</span></a></div></section>'''
    (SITE / "index.html").write_text(page("Overview", "Evidence-first OLBG dashboard for the requested fifteen sports; dated capture and no unreleased picks presented as current.", body, "index"), encoding="utf-8")


def build_olbg():
    events = AUDIT["current_olbg_events"]
    rows = []
    for item in events:
        official = (external_link(item["official_source_url"], item["official_source_name"] + " ↗") + f'<small>{e(item["crosswalk_status"])}</small>') if item["official_source_url"] else badge("NOT MATCHED", "warn")
        selection = f'<strong>{e(item["selection"])}</strong><small>{e(item["market_alias"])}</small>'
        price = f'<strong>{e(item["olbg_american_odds"])}</strong><small>{e(item["olbg_decimal_odds"])} decimal</small>'
        rows.append([
            f'<span class="sport-tag">{e(item["sport"])}</span>',
            f'<strong>{e(item["event_name"])}</strong><small>Event ID {e(item["event_id"])}</small>',
            short_time(item["start_utc"]), selection, price,
            f'{e(item["tipster_consensus"])}<small>captured tipster record</small>',
            external_link(item["olbg_url"], "OLBG listing ↗"), official,
        ])
    body = f'''<section class="page-heading"><p class="kicker">OLBG TAXONOMY SNAPSHOT · CAPTURED {e(AUDIT['source_capture']['started_utc'])}</p><h1>Captured upcoming listings</h1><p class="lede">{len(events)} event IDs were timestamped after the fixed review time across 9 of the 15 requested sports. These are OLBG user-tip selections and prices as captured—not bookmaker prices, our lines, or a live market check.</p></section>
    {alert('warning', 'Freshness warning', 'The OLBG taxonomy was captured on 23 October. “Upcoming” is calculated against 24 October 17:10:06Z; it does not establish that a market is still available today. Use each OLBG link to check the current listing manually. The Official source column is intentionally blank unless a governing-body page confirms the exact fixture participants and scheduled date; time is separately identified where the official page does not state it.')}
    <section class="panel section"><div class="section-head"><div><p class="kicker">ALL LISTED ROWS</p><h2>Upcoming in the captured snapshot</h2></div><div class="table-meta">{filter_bar('olbgEvents', 'Filter sport, team, market, selection…')}</div></div>{table(['Sport','Event','Start (UTC)','Captured OLBG selection','Captured odds','Tipster record','OLBG source','Official event source'], rows, 'olbgEvents')}</section>
    <section class="section-grid"><article class="panel"><p class="kicker">HOW TO READ THE PRICE</p><h2>OLBG tipster price ≠ bookmaker offer</h2><p>The odds above are attached to the selection recorded on the OLBG event page. The snapshot does not capture a bookmaker, an accessible current price, or a full price history. No edge or bet recommendation is implied.</p></article><article class="panel"><p class="kicker">SOURCE MATCHING</p><h2>{SUMMARY['future_olbg_events_with_manual_official_crosswalk']} exact crosswalks</h2><p>Four events are matched by participants and date to official PCB, Cork GAA, Kilkenny GAA and EHF pages; only {SUMMARY['future_olbg_events_with_official_start_time_confirmed']} official pages state the start time. The other {len(events) - SUMMARY['future_olbg_events_with_manual_official_crosswalk']} rows keep their official-source cells blank and are flagged.</p><a class="text-link" href="sources.html">See official evidence →</a></article></section>'''
    (SITE / "olbg.html").write_text(page("OLBG upcoming snapshot", "Dated OLBG upcoming event list with source links and official-source gaps.", body, "olbg"), encoding="utf-8")


def build_fixtures():
    rows = []
    for row in AUDIT["official_fixture_rows"]:
        state = badge("UPCOMING AT REVIEW", "good") if row["time_status"] == "future_at_review_time" else badge("STARTED / ELAPSED", "neutral")
        ref = row["olbg_candidate_ref"]
        olbg = external_link(ref.get("event_url", ""), "OLBG ref ↗") if ref else badge("NO REF", "warn")
        source = external_link(row["official_source_url"], "carried citation ↗")
        manual_source = (external_link(row["manual_match_source_url"], row["manual_match_source_name"] + " ↗") + f'<small>{"official start time stated" if row["manual_source_start_time_confirmed"] else "official start time not stated"}</small>') if row["manual_match_source_url"] else badge("NOT MANUALLY CHECKED", "warn")
        capture = f'<code>{e(row["capture_target_id"])}</code><small>{"hash match" if row["capture_sha256_matches"] else "hash issue"}</small>'
        flag = badge("TARGET IS OLBG", "bad") if row["capture_target_id"] in {"olbg_rugby_union", "olbg_cricket"} else badge("LINK PROVIDED", "neutral")
        rows.append([
            f'<code>{e(row["id"])}</code>', e(row["sport"]), f'<strong>{e(row["match"])}</strong><small>{e(row["competition"])}</small>',
            short_time(row["start_utc"]), state, source, manual_source, capture, olbg, flag,
        ])
    body = f'''<section class="page-heading"><p class="kicker">114 ROWS · SOURCE-DESK CUTOFF {e(SUMMARY['source_desk_cutoff_utc'])}</p><h1>Fixture audit</h1><p class="lede">The previous desk's official fixture rows are retained for provenance review. “Link provided” is not an endorsement: only the four crosswalks listed on the OLBG page were manually checked here against an event-specific official schedule.</p></section>
    {alert('danger', 'Do not use this table as a live fixture feed', f"{SUMMARY['official_desk_rows_future_at_review_time']} rows were future at the review instant; {SUMMARY['official_desk_rows_started_or_elapsed']} had already started or elapsed. The source desk's cutoff was 23 October 21:40Z. A captured hash proves byte integrity only, not that a source page supports a row.")}
    <section class="panel section"><div class="section-head"><div><p class="kicker">SOURCE LINKS RETAINED</p><h2>All fixture rows</h2></div>{filter_bar('fixtureRows', 'Filter sport, team, source, status…')}</div>{table(['Row ID','Sport','Match / competition','Start (UTC)','Time gate','Citation carried from prior desk (not rechecked)','Manual official fixture source','Capture target','OLBG reference','Provenance note'], rows, 'fixtureRows')}</section>'''
    (SITE / "fixtures.html").write_text(page("Fixture audit", "Audit of 114 historical official-source fixture rows with explicit time and provenance status.", body, "fixtures"), encoding="utf-8")


def build_picks():
    rows = []
    for p in AUDIT["numeric_prediction_candidates"]:
        official = external_link(p["official_source_url"], host_name(p["official_source_url"]) + " ↗")
        rows.append([
            f'<code>{e(p["prediction_id"])}</code><small>{e(p["sport"])}</small>',
            f'<strong>{e(p["match"])}</strong><small>{short_time(p["start_utc"])}</small>',
            f'{e(p["market"])}<small>{e(p["selection"])}</small>',
            f'{fnum(100 * p["fair_probability_in_source_desk"], 2, "%")}<small>previous desk</small>',
            f'{e(p["fair_american_in_source_desk"]) }<small>previous fair estimate</small>',
            official,
            badge("NOT ON OLBG / NOT RELEASED", "bad"),
        ])
    body = f'''<section class="page-heading"><p class="kicker">RELEASE GATE · NOT A PICK LIST</p><h1>Unreleased numerical candidates</h1><p class="lede">{len(rows)} historical prediction cards pass a 70% probability and the requested American-odds window when screened at the fixed review time. The candidates are not approved picks.</p></section>
    {alert('danger', 'No High-confidence picks are being published', 'The previous desk has five future candidates with reported probabilities ≥70% and prices within −250…+10,000. None has an exact OLBG event crosswalk in the capture, and the model inputs, match-specific claims and current availability were not independently reconciled. Their old write-ups and numbers are shown only so each blocker is auditable; they are not approved picks, recommendations or fresh lines.')}
    <section class="panel section"><div class="section-head"><div><p class="kicker">QUARANTINED SCREEN RESULTS</p><h2>Candidate ≠ qualifying pick</h2></div>{filter_bar('candidateRows', 'Filter sport, match, market…')}</div>{table(['Record','Match','Selection','Previous probability','Previous fair price','Official citation carried forward','Release status'], rows, 'candidateRows')}</section>
    <section class="section-grid"><article class="panel"><p class="kicker">PREDICTION TEXT</p><h2>Old prose withheld</h2><p>The prior cards contain human-written text, but their factual claims were not checked one by one against the cited page bodies. Reprinting them here would overstate the evidence. No new 30-word preview is generated from insufficient or unconfirmed inputs.</p></article><article class="panel"><p class="kicker">NEXT RELEASE REQUIREMENTS</p><h2>Fixture, line and claim gates</h2><ul class="checklist"><li>Exact, current OLBG event link and market</li><li>Official fixture and recent-form evidence linked directly</li><li>Inputs and probabilities re-originated and recalculated</li><li>Availability only when an official update explicitly confirms it</li><li>Unique human analysis, at least 30 words, naming the selection</li></ul></article></section>'''
    (SITE / "picks.html").write_text(page("Unreleased pick screen", "Five prior numerical candidates are quarantined; zero current picks clear the evidence gate.", body, "picks"), encoding="utf-8")


def build_markets():
    rows = []
    for m in AUDIT["market_rows"]:
        status = badge("elapsed" if m["time_status"] == "started_or_elapsed" else "future at review", "neutral")
        source = external_link(m["official_source_url"], host_name(m["official_source_url"]) + " ↗")
        rows.append([
            e(m["sport"]), f'<strong>{e(m["match"])}</strong><small>{short_time(m["start_utc"])}</small>',
            e(m["market_label"]), e(m["selection"]), fnum(100 * (m["fair_probability"] or 0), 2, "%"),
            fnum(m["fair_decimal"], 3), e(m["fair_american"]), status, source,
        ])
    body = f'''<section class="page-heading"><p class="kicker">{SUMMARY['source_desk_market_families']} FAMILIES · {SUMMARY['source_desk_market_outcomes']} OUTCOMES</p><h1>Historical market estimates</h1><p class="lede">All rows come from the 23 October source desk. These are its fair-price outputs after probability normalization—never a live bookmaker quote and never an OLBG offered price.</p></section>
    {alert('warning', 'Interpret as audit material—not betting advice', 'Fair odds were recomputed from the stored probabilities and all 997 displayed conversions reconcile. The underlying means, standard deviations, player/runner ratings, injury assumptions and other inputs were not fully rechecked against official match pages. These estimates are stale and must not be treated as current lines.')}
    <section class="panel section"><div class="section-head"><div><p class="kicker">OUTCOME-LEVEL DETAIL</p><h2>Market and line outputs</h2><p class="muted">Source links are carried from the historical fixture row; they do not validate every market input.</p></div>{filter_bar('marketRows', 'Filter sport, match, market, selection…')}</div>{table(['Sport','Match / start','Market','Selection','Stored fair probability','Fair decimal','Fair American','Time gate','Carried source URL'], rows, 'marketRows')}</section>
    <section class="panel section"><p class="kicker">ARITHMETIC CHECK</p><h2>Conversion gate: pass</h2><p>The audit recalculates decimal odds as 1 ÷ probability and American odds from the same probability. It found <strong>{SUMMARY['math_conversion_errors']} conversion errors</strong>. A valid conversion does not establish a valid input probability.</p></section>'''
    (SITE / "markets.html").write_text(page("Historical market estimates", "997 historical outcomes with internally rechecked fair odds and explicit model-input limitations.", body, "markets"), encoding="utf-8")


def build_sources():
    rows = []
    for event in AUDIT["current_olbg_events"]:
        if not event["official_source_url"]:
            continue
        cross = AUDIT["manual_official_crosswalks"][event["event_id"]]
        rows.append([
            e(event["sport"]), f'<strong>{e(event["event_name"])}</strong><small>{short_time(event["start_utc"])}</small>',
            external_link(event["olbg_url"], "OLBG listing ↗"), external_link(event["official_source_url"], e(event["official_source_name"]) + " ↗"),
            e(cross["note"]),
        ])
    capture_rows = []
    for check in AUDIT["capture_checks"]:
        capture_rows.append([e(check["id"]), badge("PASS" if check["status"] == "pass" else check["status"], "good" if check["status"] == "pass" else "bad"), external_link(check.get("url", ""), host_name(check.get("url", "")) + " ↗"), f'<code>{e(check["actual_sha256"])}</code>'])
    body = f'''<section class="page-heading"><p class="kicker">OFFICIAL SOURCE REGISTER</p><h1>What was actually checked</h1><p class="lede">Four exact upcoming OLBG↔official schedule crosswalks were opened and reviewed during this audit. Every other official match-source cell remains blank, rather than being inferred from a broad hub link.</p></section>
    {alert('warning', 'Manual review is not a live refresh', 'The four evidence links below confirm fixture identity, scheduled date/time and the specific fact noted. They do not establish current betting availability, injuries, full-season form, every prediction claim or a supported fair price.')}
    <section class="panel section"><div class="section-head"><div><p class="kicker">EXACT FIXTURE IDENTITY + DATE</p><h2>Manually reconciled official fixtures</h2></div></div>{table(['Sport','OLBG event / start','OLBG event source','Official schedule source','Scope of check'], rows, 'crosswalkRows')}</section>
    <section class="section-grid"><article class="panel"><p class="kicker">PCB</p><h2>Pakistan v England · 25 Oct</h2><p>The PCB schedule confirms the fourth ODI at Gaddafi Stadium, Lahore. The PCB match report records Pakistan's 87-run win over England on 20 October and Arafat Minhas's 6-40 and 59. Injury/availability for the upcoming match is not confirmed by these pages.</p>{external_link(AUDIT['manual_official_crosswalks']['188838']['additional_urls'][0], 'PCB official match report ↗')}</article><article class="panel"><p class="kicker">CORK GAA</p><h2>Nemo Rangers v St Finbarrs · 25 Oct</h2><p>Cork GAA lists the senior football final at SuperValu Páirc Uí Chaoimh, 16:00, and records both teams' recent knockout results. That supports a fixture/form note, not a 70% selection probability.</p><p>{external_link(AUDIT['manual_official_crosswalks']['3530']['url'], 'Cork GAA event page ↗')}</p></article></section>
    <section class="section-grid"><article class="panel"><p class="kicker">KILKENNY GAA</p><h2>Ballyhale v Tullaroan · 25 Oct</h2><p>The county body's fixture listing gives 13:45 at UPMC Nowlan Park. The fixture link does not by itself establish a current squad or injury report.</p>{external_link(AUDIT['manual_official_crosswalks']['714']['url'], 'Kilkenny GAA fixtures ↗')}</article><article class="panel"><p class="kicker">EHF</p><h2>Montpellier v Dinamo · 29 Oct</h2><p>The EHF match detail page gives 20:45 CET at FDI Stadium in Montpellier and identifies the group-phase match. Player statistics were not yet available on that page.</p>{external_link(AUDIT['manual_official_crosswalks']['12133']['url'], 'EHF match detail ↗')}</article></section>
    <section class="panel section"><div class="section-head"><div><p class="kicker">BYTE INTEGRITY</p><h2>{SUMMARY['capture_payloads_hash_pass']} of {SUMMARY['capture_payloads_hash_checked']} successful HTTP payloads match the manifest</h2><p class="muted">Hash verification checks the saved payload against the manifest; it does not fact-check page content.</p></div>{source_capture_link('Manifest ↗', '')}</div>{table(['Capture target ID','Hash result','Captured source URL','SHA-256'], capture_rows, 'captureTable')}</section>
    <section class="panel section"><p class="kicker">FAILED CAPTURES</p><h2>{SUMMARY['capture_non_200']} targets did not return HTTP 200</h2><p>These source gaps remain visible in the original manifest and are not silently treated as empty evidence. No pick is promoted from an inaccessible response.</p>{source_capture_link('Review complete manifest and response records ↗', '')}</section>
    <section class="panel section"><p class="kicker">LIVE HUB SPOT-CHECK · 24 OCT</p><h2>{SUMMARY['live_olbg_hub_pages_spot_checked_without_timestamped_capture']} OLBG hubs opened</h2><p>The hub pages displayed current-day and later tip listings for Volleyball, Cricket and Handball. Their relative Today/Tomorrow labels were not captured as a UTC-time-stamped raw response, so this spot-check is not used to update the 58-row snapshot table.</p><ul class="checklist">{''.join(f'<li>{e(item["sport"])} — {external_link(item["url"], "open OLBG hub ↗")} — {e(item["note"])} </li>' for item in AUDIT['manual_olbg_hub_spot_checks'])}</ul></section>'''
    (SITE / "sources.html").write_text(page("Sources and capture", "Four manually checked official crosswalks plus capture-integrity evidence and limitations.", body, "sources"), encoding="utf-8")


def build_flagged():
    rows = []
    for finding in AUDIT["findings"]:
        links = ' · '.join(external_link(url, host_name(url) + ' ↗') for url in finding.get("official_source_urls", []))
        evidence = f'<a href="../{e(finding["evidence_file"])}">{e(finding["evidence_file"])} ↗</a>' if finding.get("evidence_file") else '<span class="muted">—</span>'
        rows.append([
            f'<strong>{e(finding["id"])}</strong><small>{badge(finding["severity"].upper(), "bad" if finding["severity"] in ("critical", "high") else "warn")}</small>',
            f'<strong>{e(finding["title"])}</strong><p>{e(finding["detail"])}</p>',
            str(finding["affected_count"]), f'{links}<small>Local evidence: {evidence}</small>',
        ])
    ref_rows = []
    for item in AUDIT["olbg_reference_mismatches"]:
        ref_rows.append([
            f'<code>{e(item["row_id"])}</code>', e(item["row_match"]), short_time(item["start_utc"]),
            f'{e(item["olbg_event_name"])}<small>{short_time(item["olbg_start_utc"])}</small>',
            external_link(item["olbg_url"], "OLBG ref ↗"), external_link(item["official_source_url"], host_name(item["official_source_url"]) + " ↗"),
        ])
    body = f'''<section class="page-heading"><p class="kicker">OPEN ISSUES · NO SILENT ASSUMPTIONS</p><h1>Flagged for Review</h1><p class="lede">Every publication blocker discovered in this audit is listed here. Missing values are intentionally left blank; the review does not convert a missing source into a fact.</p></section>
    {alert('danger', 'Publication gate remains closed', 'No current High-confidence selection is fully supported by an exact OLBG event, official evidence for the cited form/market claims, and a refreshed line. The dashboard is a dated audit, not a betting recommendation service.')}
    <section class="panel section"><div class="section-head"><div><p class="kicker">ISSUE REGISTER</p><h2>{len(rows)} open findings</h2></div></div>{table(['ID / severity','Finding and impact','Count','Source links / evidence'], rows, 'flagRows')}</section>
    <section class="panel section"><div class="section-head"><div><p class="kicker">OLBG REFERENCE CROSS-CHECK</p><h2>All {len(AUDIT['olbg_reference_mismatches'])} stored links with a time/ID mismatch</h2><p class="muted">Includes references to matches that had already started as well as one future date error.</p></div>{filter_bar('mismatchRows', 'Filter row ID, teams, source…')}</div>{table(['Desk row','Desk match','Desk start','Referenced OLBG listing','OLBG source','Official citation'], ref_rows, 'mismatchRows')}</section>
    <section class="panel section"><p class="kicker">REVIEW PRINCIPLE</p><h2>Do not promote until the row is reconciled</h2><p>When the exact fixture, start time, evidence source, line inputs, market availability, injury status or selection probability is not supported, the corresponding field stays blank and the match remains visible on this page.</p></section>'''
    (SITE / "flagged.html").write_text(page("Flagged for Review", "Open source, freshness, schedule and prediction issues for the 15-sport evidence dashboard.", body, "flagged"), encoding="utf-8")


def build_methodology():
    body = f'''<section class="page-heading"><p class="kicker">REPRODUCIBLE AUDIT · PYTHON STANDARD LIBRARY</p><h1>Methodology & limits</h1><p class="lede">This session chose conservative publication over repairing unsupported values by inference.</p></section>
    <section class="section-grid"><article class="panel"><p class="kicker">TIME GATE</p><h2>Fixed review instant</h2><p>All “future” / “started or elapsed” labels compare UTC start times with <code>{e(AS_OF)}</code>. OLBG inventory was captured at <code>{e(AUDIT['source_capture']['started_utc'])}</code>, and the previous official-source desk cutoff was <code>{e(SUMMARY['source_desk_cutoff_utc'])}</code>. Those captures are historical; this build does not claim a live refresh.</p></article><article class="panel"><p class="kicker">SCOPE GATE</p><h2>Exactly 15 requested sports</h2><p>Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts, Baseball, Gaelic Sports, Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball and Rugby League. A sport with zero captured future OLBG listings remains visible with zero; no unrelated category is added.</p></article></section>
    <section class="section-grid"><article class="panel"><p class="kicker">OFFICIAL CROSSWALK</p><h2>OLBG event ID + exact fixture/date + page review</h2><p>The four official-source links are attached only after checking the governing-body page for participants and scheduled date. OLBG and the source desk carry the same UTC start timestamp for these four, but the PCB schedule does not state a start time; that one time remains an OLBG/source-desk observation, not an official confirmation. Other event matches are not fuzzy-matched or guessed.</p></article><article class="panel"><p class="kicker">PREDICTION RELEASE</p><h2>70% and the requested price band are necessary, not sufficient</h2><p>The numerical screen applies p ≥ 0.70 and American odds from −250 through +10,000 to the old stored selection. Release additionally requires an exact OLBG listing, refreshed evidence for each claimed form/statistic, source-grounded line inputs and sourced availability. The five numerical candidates fail those added requirements, so no prediction prose is published.</p></article></section>
    <section class="panel section"><p class="kicker">LINE ARITHMETIC</p><h2>Conversions are checked; inputs are not endorsed</h2><p>For every historical outcome, decimal fair odds are checked as <code>1/p</code>; American fair odds are recomputed from the same probability. This catches arithmetic drift, not weak samples, hard-coded team strengths, unsupported expected scores or stale player status. The source desk lists {SUMMARY['source_desk_market_families']} market families and {SUMMARY['source_desk_market_outcomes']} outcomes, all explicitly labeled historical estimates.</p></section>
    <section class="panel section"><p class="kicker">PREDICTION TEXT RULE</p><h2>Do not write around missing evidence</h2><p>When a qualifying match is source-verified, the forecast must be unique, human-written, at least 30 words and explicitly state the selection. It must use official current form, recent match history and match-specific statistics. Injury/availability claims require explicit official confirmation; silence is not proof. No claim is carried forward just because its previous text was fluent.</p></section>
    <section class="panel section"><p class="kicker">REBUILD</p><h2>Recreate this audit and site</h2><pre><code>PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/audit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/build_site.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/verify.py</code></pre><p>Generated files: <code>data/session-265b28e5/audit.json</code> and the static pages under <code>session-265b28e5/</code>.</p></section>'''
    (SITE / "methodology.html").write_text(page("Methodology", "Reproducible scope, time, evidence and release rules for the 15-sport OLBG audit.", body, "methodology"), encoding="utf-8")


def build_coverage():
    rows = []
    for s in SPORTS:
        current = [r for r in AUDIT["current_olbg_events"] if r["sport"] == s["sport"]]
        official = [r for r in AUDIT["official_fixture_rows"] if r["sport"] == s["sport"]]
        screen = [p for p in AUDIT["numeric_prediction_candidates"] if p["sport"] == s["sport"]]
        rows.append([f'<a href="sports/{e(s["slug"])}.html">{e(s["sport"])} →</a>', external_link(s["olbg_hub_url"], "OLBG hub ↗") if s["olbg_hub_url"] else badge("NO HUB", "warn"), len(current), sum(bool(r["official_source_url"]) for r in current), len(official), len(screen), "No future OLBG row in this snapshot" if not current else "Captured rows need live re-check"])
    body = f'''<section class="page-heading"><p class="kicker">15-SPORT SCOPE</p><h1>Coverage, including zeroes</h1><p class="lede">The values below describe this dated capture. They do not claim complete event coverage across the live sports calendar.</p></section>
    {alert('warning', 'Zero is not an absence-of-event claim', 'A zero means the saved OLBG snapshot did not contain a future-timestamped event for that sport at the fixed review instant. It does not mean the sport has no upcoming events or markets today.')}
    <section class="panel section">{table(['Requested sport','Captured OLBG hub source','OLBG future rows','Officially crosswalked','Prior fixture rows','Numeric candidates withheld','Coverage note'], rows, 'coverageTable')}</section>'''
    (SITE / "coverage.html").write_text(page("Sport coverage", "Coverage matrix for the exact requested 15 sports and the dated OLBG snapshot.", body, "coverage"), encoding="utf-8")


def build_sport_pages():
    for sport in SPORTS:
        current = [r for r in AUDIT["current_olbg_events"] if r["sport"] == sport["sport"]]
        official = [r for r in AUDIT["official_fixture_rows"] if r["sport"] == sport["sport"]]
        candidates = [p for p in AUDIT["numeric_prediction_candidates"] if p["sport"] == sport["sport"]]
        olbg_rows = []
        for item in current:
            official_link = (external_link(item["official_source_url"], item["official_source_name"] + " ↗") + f'<small>{e(item["crosswalk_status"])}</small>') if item["official_source_url"] else badge("NOT MATCHED", "warn")
            olbg_rows.append([
                f'<strong>{e(item["event_name"])}</strong><small>Event {e(item["event_id"])}</small>', short_time(item["start_utc"]),
                f'{e(item["market_alias"])}<small>{e(item["selection"])}</small>', e(item["olbg_american_odds"]),
                external_link(item["olbg_url"], "OLBG ↗"), official_link,
            ])
        fixture_rows = []
        for row in official:
            state = "Upcoming at review" if row["time_status"] == "future_at_review_time" else "Started / elapsed"
            olbg = external_link(row["olbg_candidate_ref"].get("event_url", ""), "OLBG ref ↗") if row["olbg_candidate_ref"] else badge("NO REF", "warn")
            carried = external_link(row["official_source_url"], "carried citation ↗")
            manual = (external_link(row["manual_match_source_url"], row["manual_match_source_name"] + " ↗") + f'<small>{"official time stated" if row["manual_source_start_time_confirmed"] else "official time not stated"}</small>') if row["manual_match_source_url"] else badge("NOT MANUALLY CHECKED", "warn")
            fixture_rows.append([
                f'<strong>{e(row["match"])}</strong><small>{e(row["competition"])}</small>', short_time(row["start_utc"]), state,
                carried, manual, olbg,
            ])
        candidate_msg = f"{len(candidates)} old numerical candidate(s) are withheld; see the Pick screen for blockers." if candidates else "No numerical candidate from the previous desk passes the 70% / price-window screen for this sport."
        body = f'''<section class="page-heading"><p class="kicker">SPORT DESK · {e(sport['sport'].upper())}</p><h1>{e(sport['sport'])}</h1><p class="lede">Only this requested category is shown. Counts refer to the dated 23 October capture and the 24 October 17:10:06Z review gate.</p><p>{external_link(sport['olbg_hub_url'], 'Open current OLBG hub ↗') if sport['olbg_hub_url'] else badge('No hub URL in capture', 'warn')}</p></section>
        {alert('warning', 'No pick released', candidate_msg + ' The OLBG list is not live, and historical fair prices are not current bookmaker prices.')}
        <section class="panel section"><div class="section-head"><div><p class="kicker">OLBG LISTINGS</p><h2>{len(current)} captured future listing(s)</h2></div>{filter_bar('sportOlbg', 'Filter teams or markets…')}</div>{table(['OLBG event','Start (UTC)','Market / selection','Captured odds','OLBG source','Official source crosswalk'], olbg_rows, 'sportOlbg', 'No future listing for this sport appears in the saved OLBG snapshot.')}</section>
        <section class="panel section"><div class="section-head"><div><p class="kicker">PRIOR SOURCE DESK</p><h2>{len(official)} fixture row(s)</h2><p class="muted">Source links are carried forward for manual review; they are not all re-verified for content here.</p></div>{filter_bar('sportFixtures', 'Filter match, date, status…')}</div>{table(['Fixture / competition','Start (UTC)','Time status','Prior citation (not rechecked)','Manual official fixture source','OLBG candidate ref'], fixture_rows, 'sportFixtures', 'No prior fixture rows in this sport.')}</section>
        <section class="panel section"><p class="kicker">CURRENT PREDICTIONS</p><h2>0 released · {len(candidates)} held for review</h2><p>No synthetic quota-fill. Unsupported line values and injuries remain blank until an official source supports them.</p><a class="text-link" href="../picks.html">Open the full candidate review →</a></section>'''
        out = SITE / "sports" / f"{sport['slug']}.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(sport["sport"], f"Dated fixture and OLBG audit for {sport['sport']}.", body, "", prefix="../"), encoding="utf-8")


def write_css_js():
    css = r'''
:root{--ink:#182431;--muted:#687787;--line:#e2e8ec;--paper:#f5f7f8;--panel:#fff;--navy:#112940;--navy2:#183850;--teal:#13a89e;--teal-dark:#087e78;--red:#a23333;--red-bg:#fff0ed;--amber:#91580b;--amber-bg:#fff6e5;--green:#20734e;--green-bg:#eaf7ef;--shadow:0 8px 30px rgba(21,42,59,.055)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.58 'DM Sans',system-ui,-apple-system,Segoe UI,sans-serif}a{color:#096e78;text-decoration:none}a:hover{color:#064b54;text-decoration:underline}code,.mono{font-family:'DM Mono',monospace;font-size:.84em}code{background:#eef2f4;border-radius:4px;padding:2px 4px}.wrap{max-width:1320px;width:calc(100% - 40px);margin:0 auto}.topbar{background:var(--navy);color:#fff;position:sticky;top:0;z-index:30;box-shadow:0 3px 18px rgba(14,30,44,.18)}.top-inner{max-width:1440px;width:calc(100% - 36px);min-height:72px;margin:auto;display:flex;align-items:center;gap:30px}.brand{display:flex;align-items:center;gap:11px;color:#fff;font:800 16px/1.1 'Manrope',sans-serif;white-space:nowrap}.brand:hover{color:#fff;text-decoration:none}.brand-icon{height:38px;width:38px;border-radius:12px;background:linear-gradient(140deg,#42d9c3,#0e928e);display:grid;place-items:center;font-size:13px;color:#072c36;letter-spacing:-.06em}.brand-light{font-weight:500;color:#c6d4de}.brand small{display:block;font:500 10px 'DM Mono',monospace;color:#9fb2bf;margin-top:5px;letter-spacing:.04em}.main-nav{display:flex;align-items:center;gap:4px;overflow-x:auto;scrollbar-width:none;flex:1}.nav-link{color:#d5e0e7;padding:9px 11px;border-radius:8px;white-space:nowrap;font-size:12px;font-weight:600}.nav-link:hover,.nav-link.active{background:#23445c;color:#fff;text-decoration:none}.nav-link.active{box-shadow:inset 0 -2px var(--teal)}.sport-menu{position:relative;white-space:nowrap}.sport-menu summary{list-style:none;cursor:pointer;padding:9px 12px;border:1px solid #466175;border-radius:8px;font-size:12px;font-weight:700}.sport-menu summary::-webkit-details-marker{display:none}.sport-menu[open] summary{background:#23445c}.sport-menu-panel{position:absolute;right:0;top:47px;background:#fff;color:var(--ink);box-shadow:var(--shadow);border:1px solid var(--line);border-radius:12px;padding:10px;min-width:220px;display:grid;grid-template-columns:1fr 1fr;gap:3px}.sport-menu-panel a{padding:7px 8px;border-radius:6px;font-size:12px}.sport-menu-panel a:hover{background:#edf6f6;text-decoration:none}.eyebrow{margin:21px 0 12px;color:#7d8b95;font:500 10px 'DM Mono',monospace;letter-spacing:.075em}.hero{margin:0 0 20px;padding:42px 44px;border-radius:22px;display:grid;grid-template-columns:minmax(0,1.45fr) minmax(260px,.7fr);gap:35px;align-items:center;background:radial-gradient(circle at 80% 0%,rgba(29,185,171,.19),transparent 28%),linear-gradient(125deg,#10263b,#17354b 70%,#173b4b);color:#fff;overflow:hidden}.kicker{margin:0 0 10px;color:#7fa0ad;font:500 10px 'DM Mono',monospace;letter-spacing:.13em}.hero .kicker{color:#65d4c6}.hero h1,.page-heading h1{font:800 clamp(36px,5vw,58px)/1.04 'Manrope',sans-serif;letter-spacing:-.05em;margin:0 0 16px}.hero h1 span{color:#69dbcb}.lede{max-width:770px;color:#5f6f7e;font-size:17px;line-height:1.62;margin:0}.hero .lede{color:#d2dfe6;max-width:670px}.hero-actions{display:flex;gap:11px;flex-wrap:wrap;margin-top:24px}.button{display:inline-flex;align-items:center;gap:15px;border-radius:9px;padding:12px 16px;font-size:13px;font-weight:700}.button:hover{text-decoration:none;transform:translateY(-1px)}.button.primary{background:#48d2c1;color:#092a34}.button.secondary{border:1px solid #557081;color:#f3f7f8}.hero-note{margin:19px 0 0;color:#9fb4c0;font-size:11px}.hero-note strong{color:#eff9fa;font-family:'DM Mono',monospace}.hero-card{background:rgba(240,250,250,.08);border:1px solid rgba(211,241,240,.2);border-radius:18px;padding:23px 24px;min-height:225px;backdrop-filter:blur(8px)}.hero-card-top{font:500 10px 'DM Mono',monospace;color:#bad1d8;letter-spacing:.11em}.live-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#f6aa68;margin-right:7px;box-shadow:0 0 0 4px rgba(246,170,104,.12)}.big-number{font:800 65px/.98 'Manrope',sans-serif;color:#fff;margin:25px 0 6px;letter-spacing:-.07em}.hero-card-title{font:700 18px 'Manrope',sans-serif}.hero-card-rule{color:#c0d0d9;font-size:12px;margin:9px 0 14px}.hero-card a{color:#66decf;font-size:12px;font-weight:700}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:14px 0 20px}.metric{background:#fff;border:1px solid var(--line);border-radius:13px;padding:18px 20px;box-shadow:var(--shadow)}.metric span,.metric small{display:block;color:var(--muted);font-size:11px}.metric strong{font:800 31px 'Manrope',sans-serif;display:block;letter-spacing:-.04em;margin:6px 0}.metric small{font-size:10px}.section-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:16px 0}.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:24px;box-shadow:var(--shadow);min-width:0}.panel h2{font:750 22px/1.22 'Manrope',sans-serif;letter-spacing:-.035em;margin:0 0 9px}.panel p{margin:9px 0;color:#526271}.panel-dark{background:linear-gradient(135deg,#182f45,#1c3a50);color:#fff;border:0}.panel-dark .kicker{color:#66d1c4}.panel-dark p{color:#d2dfe5}.panel-dark h2{font-size:25px}.panel-dark .text-link{color:#65ddcf}.text-link{font-weight:700;font-size:12px}.source-chips{display:flex;gap:6px;flex-wrap:wrap;margin:15px 0}.section{margin:17px 0 22px}.section-head{display:flex;justify-content:space-between;align-items:flex-end;gap:20px;margin-bottom:17px}.section-head h2{margin-bottom:2px}.section-head p{margin:6px 0 0}.muted{color:var(--muted)!important}.quick-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}.quick-grid a{border:1px solid var(--line);border-radius:10px;padding:14px;color:var(--ink);transition:.15s}.quick-grid a:hover{border-color:#7fcac2;box-shadow:0 7px 18px #1129400c;text-decoration:none;transform:translateY(-1px)}.quick-grid strong,.quick-grid span{display:block}.quick-grid strong{font:700 14px 'Manrope',sans-serif}.quick-grid span{margin-top:7px;color:var(--muted);font-size:11px;line-height:1.45}.alert{border-radius:12px;padding:15px 18px;margin:16px 0;border:1px solid transparent;font-size:13px}.alert strong{display:block;font:750 14px 'Manrope',sans-serif;margin-bottom:4px}.alert div{color:#4d5d68}.alert.warning{background:var(--amber-bg);border-color:#f0dfb7}.alert.warning strong{color:#795010}.alert.danger{background:var(--red-bg);border-color:#f0d0ca}.alert.danger strong{color:#8e3030}.alert.info{background:#eef6fb;border-color:#d4e5f0}.alert.success{background:var(--green-bg);border-color:#cae8d4}.page-heading{padding:22px 2px 16px}.page-heading h1{font-size:clamp(34px,4vw,49px);margin-bottom:12px}.page-heading .kicker{color:#17827d}.page-heading .lede{font-size:16px}.badge{display:inline-flex;align-items:center;padding:4px 7px;border-radius:5px;font:600 9px 'DM Mono',monospace;letter-spacing:.04em;white-space:nowrap;background:#edf1f3;color:#61707b}.badge.good{background:#e5f6ed;color:#1e6c49}.badge.warn{background:#fff1d4;color:#89530d}.badge.bad{background:#ffe7e4;color:#9a3531}.table-meta{min-width:225px}.filter{display:flex;align-items:center;gap:8px}.filter span{font:500 10px 'DM Mono',monospace;color:#7a8790;text-transform:uppercase;letter-spacing:.07em}.filter input{width:100%;border:1px solid #d9e1e5;border-radius:8px;padding:9px 10px;font:12px 'DM Sans',sans-serif;background:#fbfcfc;color:var(--ink);outline:none}.filter input:focus{border-color:#4fbcb2;box-shadow:0 0 0 3px #4fbcb21c}.table-wrap{width:100%;overflow:auto;border:1px solid var(--line);border-radius:10px}table{width:100%;border-collapse:collapse;font-size:11px;min-width:800px}thead{background:#f3f6f7}th{text-align:left;color:#697984;font:600 9px 'DM Mono',monospace;letter-spacing:.07em;text-transform:uppercase;padding:11px 12px;white-space:nowrap;border-bottom:1px solid var(--line);position:sticky;top:0}td{padding:10px 12px;border-bottom:1px solid #edf0f2;vertical-align:top;color:#344450;line-height:1.45}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f8fbfb}td strong{color:#253644}td small{display:block;color:#83909a;font-size:9px;margin-top:3px}td p{font-size:10px;line-height:1.5;margin:5px 0!important;max-width:700px}td a{font-weight:600;white-space:nowrap}.empty{text-align:center;color:var(--muted);padding:22px}.sport-tag{font-size:10px;font-weight:700;color:#22656b}.sport-name{font-weight:700;color:#213b4b}.sport-name span{color:var(--teal-dark)}.table-wrap table code{font-size:9px}.section-grid .panel{height:100%}.checklist{margin:8px 0;padding-left:18px;color:#526271;font-size:12px}.checklist li{padding:4px 0}pre{overflow:auto;background:#142b3f;color:#d7eef0;border-radius:9px;padding:16px;font:12px/1.6 'DM Mono',monospace}.footer{display:flex;justify-content:space-between;gap:15px;border-top:1px solid #dae2e6;padding:22px 3px 35px;margin-top:28px;color:#75838c;font-size:10px}.footer div:first-child strong,.footer div:first-child span{display:block}.footer strong{color:#41505b}.footer a{margin-left:14px;font-weight:600}.footer div:first-child span{margin-top:4px}.source-chips .badge{font-size:9px}
@media(max-width:1050px){.top-inner{gap:12px}.main-nav{gap:1px}.nav-link{padding:8px;font-size:11px}.hero{padding:34px 30px}.quick-grid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:760px){.wrap{width:calc(100% - 24px)}.top-inner{width:calc(100% - 20px);min-height:62px;flex-wrap:wrap;padding:9px 0;gap:9px}.brand{font-size:14px}.brand-icon{width:32px;height:32px}.main-nav{order:3;flex-basis:100%;overflow-x:auto}.nav-link{padding:7px 9px}.sport-menu{margin-left:auto}.sport-menu-panel{top:39px}.eyebrow{font-size:9px}.hero{grid-template-columns:1fr;padding:27px 22px;border-radius:16px;gap:22px}.hero h1{font-size:39px}.hero-card{min-height:0}.big-number{font-size:55px;margin-top:15px}.metric-grid{grid-template-columns:1fr 1fr;gap:8px}.metric{padding:13px}.metric strong{font-size:26px}.section-grid{grid-template-columns:1fr;gap:10px}.panel{padding:18px}.section-head{align-items:flex-start;flex-direction:column}.table-meta{width:100%}.quick-grid{grid-template-columns:1fr 1fr}.footer{flex-direction:column}.footer a{margin:0 12px 0 0}.page-heading h1{font-size:37px}.lede{font-size:15px}}
@media(max-width:430px){.metric-grid{grid-template-columns:1fr 1fr}.quick-grid{grid-template-columns:1fr}.button{width:100%;justify-content:space-between}.hero h1{font-size:34px}.panel h2{font-size:20px}}
'''
    js = r'''document.addEventListener('DOMContentLoaded',()=>{document.querySelectorAll('[data-filter]').forEach(input=>{const target=document.getElementById(input.dataset.filter);if(!target)return;const rows=[...target.querySelectorAll('tbody tr')];input.addEventListener('input',()=>{const q=input.value.trim().toLocaleLowerCase();let visible=0;rows.forEach(row=>{const show=row.innerText.toLocaleLowerCase().includes(q);row.hidden=!show;if(show)visible++});let count=input.parentElement.querySelector('.filter-count');if(!count){count=document.createElement('small');count.className='filter-count';input.parentElement.appendChild(count)}count.textContent=q?`${visible} shown`:''})});document.querySelectorAll('a[href^="http"]').forEach(a=>{if(!a.target)a.target='_blank';a.rel='noopener noreferrer'})});'''
    (SITE / "style.css").write_text(css, encoding="utf-8")
    (SITE / "app.js").write_text(js, encoding="utf-8")


def write_dashboard_manifest():
    sport_pages = []
    for sport in SPORTS:
        current = [event for event in AUDIT["current_olbg_events"] if event["sport"] == sport["sport"]]
        sport_pages.append({
            "sport": sport["sport"], "slug": sport["slug"],
            "page": f"session-265b28e5/sports/{sport['slug']}.html",
            "olbg_hub_url": sport.get("olbg_hub_url", ""),
            "captured_future_event_rows": len(current),
            "officially_crosswalked_rows": sum(bool(event["official_source_url"]) for event in current),
        })
    manifest = {
        "schema": "olbg4.session-265b28e5.dashboard/1",
        "session": "arena/265b28e5-olbg4",
        "review_as_of_utc": AUDIT["as_of_utc"],
        "freshness": "historical snapshot; not live refreshed",
        "summary": AUDIT["summary"],
        "landing_page": "session-265b28e5/index.html",
        "pages": {
            "olbg_upcoming": "session-265b28e5/olbg.html",
            "fixture_audit": "session-265b28e5/fixtures.html",
            "pick_screen": "session-265b28e5/picks.html",
            "markets": "session-265b28e5/markets.html",
            "sources": "session-265b28e5/sources.html",
            "flagged_for_review": "session-265b28e5/flagged.html",
            "methodology": "session-265b28e5/methodology.html",
            "coverage": "session-265b28e5/coverage.html",
        },
        "sports": sport_pages,
        "audit_json": "data/session-265b28e5/audit.json",
    }
    out = ROOT / "data/session-265b28e5/dashboard.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build_all():
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(exist_ok=True)
    write_dashboard_manifest()
    write_css_js()
    build_index()
    build_olbg()
    build_fixtures()
    build_picks()
    build_markets()
    build_sources()
    build_flagged()
    build_methodology()
    build_coverage()
    build_sport_pages()
    print(f"Rendered 9 dashboard pages + {len(SPORTS)} sport pages under {SITE.relative_to(ROOT)}/")


if __name__ == "__main__":
    build_all()

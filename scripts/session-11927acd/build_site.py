#!/usr/bin/env python3
"""Render the static Board RI GitHub Pages dashboard."""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import ri

DESK = json.loads((ri.DATA / "desk.json").read_text())
PREDS = json.loads((ri.DATA / "predictions.json").read_text())
FLAGS = json.loads((ri.DATA / "flags.json").read_text())
SOURCES = json.loads((ri.DATA / "sources.json").read_text())
AUDIT = json.loads((ri.DATA / "audit.json").read_text())
CANDIDATES = json.loads((ri.DATA / "candidates.json").read_text())
ROWS = DESK["rows"]
PREDICTIONS = PREDS["predictions"]
BY_ID = {r["id"]: r for r in ROWS}
PRED_BY_ROW = {p["row_id"]: p for p in PREDICTIONS}

CSS = r"""
:root{--navy:#102a43;--navy2:#173f5f;--ink:#172b3a;--muted:#5d6b78;--bg:#f4f7fa;--card:#fff;--line:#dbe4eb;--green:#087f5b;--greenbg:#e8f7f1;--amber:#9a5b00;--amberbg:#fff5df;--red:#b42318;--redbg:#fff0ee;--blue:#1261a0;--bluebg:#eaf4fc}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--blue);text-decoration:none}a:hover{text-decoration:underline}a:focus-visible{outline:3px solid #78b7e5;outline-offset:2px}.wrap{width:min(1240px,calc(100% - 32px));margin:auto}.hero{background:linear-gradient(120deg,var(--navy),var(--navy2));color:#fff;padding:26px 0 22px;border-bottom:4px solid #35b98a}.hero h1{margin:0 0 5px;font-size:clamp(1.45rem,3vw,2.1rem);letter-spacing:-.02em}.hero p{margin:0;color:#d4e4ee}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:.73rem;font-weight:800;color:#83e1bd;margin-bottom:7px}.nav{display:flex;gap:7px;flex-wrap:wrap;margin-top:18px}.nav a{color:#eaf5fb;border:1px solid #49677d;border-radius:7px;padding:6px 10px;font-size:.84rem;background:#173b55}.nav a:hover{background:#23516f;text-decoration:none}.nav a.active{background:#fff;color:var(--navy);border-color:#fff;font-weight:750}.nav a .count{opacity:.72;font-variant-numeric:tabular-nums}main{padding:22px 0 40px}.exec{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--green);border-radius:12px;padding:18px 20px;box-shadow:0 3px 14px #16334a0a}.exec h2{margin:0 0 7px;font-size:1.28rem}.exec p{margin:7px 0}.actions{display:flex;gap:9px;flex-wrap:wrap;margin-top:13px}.button{display:inline-block;background:var(--navy);color:#fff;border-radius:7px;padding:8px 12px;font-weight:700}.button:hover{background:var(--navy2);text-decoration:none}.button.secondary{background:var(--bluebg);color:var(--blue);border:1px solid #bdd9ec}.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:11px;margin:15px 0}.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px}.kpi strong{display:block;font-size:1.65rem;line-height:1.1;color:var(--navy);font-variant-numeric:tabular-nums}.kpi span{display:block;color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.05em;margin-top:5px}h2.section{font-size:1.23rem;margin:29px 0 9px;color:var(--navy)}h3{color:var(--navy)}.sub{color:var(--muted);font-size:.88rem}.scroll{overflow:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;font-size:.85rem}th{text-align:left;background:#eaf0f5;color:#405466;text-transform:uppercase;letter-spacing:.045em;font-size:.69rem;padding:9px 10px;border-bottom:1px solid var(--line);white-space:nowrap}td{padding:10px;border-bottom:1px solid #e8eef2;vertical-align:top}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f7fafc}.num{font-variant-numeric:tabular-nums;white-space:nowrap}.pick{font-weight:800;color:var(--navy);font-size:.93rem}.badge{display:inline-block;border-radius:999px;padding:2px 8px;font-size:.72rem;font-weight:800;white-space:nowrap}.high{background:var(--greenbg);color:var(--green);border:1px solid #b6e4d3}.medium{background:var(--amberbg);color:var(--amber);border:1px solid #ecd6a7}.low,.review{background:var(--redbg);color:var(--red);border:1px solid #f0c5bf}.neutral{background:#edf1f4;color:#52616d;border:1px solid #d6dfe5}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:13px 0;box-shadow:0 3px 14px #16334a08}.card h3{margin:0 0 5px}.cardhead{display:flex;justify-content:space-between;gap:12px;align-items:start}.pickbanner{background:var(--greenbg);border:1px solid #bce4d5;border-radius:9px;padding:12px 14px;margin:12px 0}.prose{font-size:1rem;line-height:1.72;background:#f8fafb;border-left:3px solid var(--blue);padding:13px 15px;border-radius:0 8px 8px 0}.facts{padding-left:19px;font-size:.86rem}.facts li{margin:5px 0}.warn{background:var(--amberbg);border:1px solid #ead29e;border-radius:10px;padding:13px 15px}.danger{background:var(--redbg);border:1px solid #efc2bc;border-radius:10px;padding:13px 15px}.ok{background:var(--greenbg);border:1px solid #b6e4d3;border-radius:10px;padding:13px 15px}.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}.filters{display:flex;gap:10px;flex-wrap:wrap;margin:12px 0}.filters input,.filters select{font:inherit;color:var(--ink);background:#fff;border:1px solid #bfcdd7;border-radius:7px;padding:8px 10px}.filters input{min-width:min(360px,100%)}code{background:#eaf0f4;border-radius:4px;padding:1px 4px;font-size:.84em}details{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:10px 13px;margin:10px 0}summary{cursor:pointer;font-weight:750;color:var(--navy)}footer{border-top:1px solid var(--line);padding:20px 0 30px;color:var(--muted);font-size:.8rem}.footerlinks{display:flex;gap:12px;flex-wrap:wrap}.small{font-size:.79rem}.empty{padding:22px;color:var(--muted)}.marketgroup{margin:8px 0 14px}.target{font-weight:800}.right{text-align:right}@media(max-width:700px){.wrap{width:min(100% - 20px,1240px)}.hero{padding:20px 0}.card{padding:14px}.exec{padding:15px}.cardhead{display:block}th,td{padding:8px}.kpis{grid-template-columns:repeat(2,1fr)}}
"""

NAV = [
    ("index.html", "Dashboard", None), ("picks.html", "Written picks", len(PREDICTIONS)),
    ("fixtures.html", "All matches", len(ROWS)), ("sports.html", "Sports", 15),
    ("markets.html", "Markets", None), ("sources.html", "Sources", SOURCES["total"]),
    ("audit.html", "Audit", None), ("flagged.html", "Flagged", FLAGS["count"]),
    ("methodology.html", "Methodology", None),
]


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def link(url: str, label: str) -> str:
    return f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(label)}</a>' if url else "—"


def american(value: int) -> str:
    return f"+{value}" if value > 0 else str(value)


def badge(conf: str) -> str:
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(conf, "neutral")
    return f'<span class="badge {cls}">{esc(conf)}</span>'


def fmt_time(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime("%a %d %b · %H:%M UTC")
    except Exception:
        return value or "—"


def page(title: str, body: str, active: str, subtitle: str, prefix: str = "") -> str:
    nav = "".join(
        f'<a href="{prefix}{href}" class="{"active" if href == active else ""}">{esc(label)}{f" <span class=count>{count}</span>" if count is not None else ""}</a>'
        for href, label, count in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{esc(subtitle)}"><title>{esc(title)} · OLBG Release Integrity</title><style>{CSS}</style></head><body>
<header class="hero"><div class="wrap"><div class="eyebrow">OLBG · Release integrity desk</div><h1>{esc(title)}</h1><p>{esc(subtitle)}</p><nav class="nav" aria-label="Desk navigation">{nav}</nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap"><p>Official snapshot <strong>{esc(DESK['captured_utc'])}</strong> · page generated {esc(DESK['generated_utc'])} · fair lines are our calculations, not sportsbook offers. Nothing here guarantees a result.</p><div class="footerlinks"><a href="{prefix}methodology.html">Rules and limitations</a><a href="{prefix}flagged.html">Unverified items and shortfalls</a><a href="{prefix}../data/session-11927acd/desk.json">Desk JSON</a><a href="{prefix}../data/session-11927acd/predictions.json">Predictions JSON</a></div></div></footer></body></html>"""


def source_cell(row: dict, prefix: str = "") -> str:
    review = f'<br><a href="{prefix}flagged.html#row-{esc(row["id"])}">Review flags</a>'
    if row["source_status"] == "official":
        return link(row["official_url"], "Official fixture") + review
    stats = ""
    if row.get("official_stats_url"):
        stats = link(row["official_stats_url"], "Official stats") + "<br>"
    return f'{stats}<span class="badge review">Fixture unverified</span>{review}'


def olbg_cell(row: dict) -> str:
    if row.get("olbg"):
        url = row["olbg"].get("url") or row["olbg"].get("event_url") or row["olbg"].get("hub_url")
        return link(url, f"OLBG event {row['olbg'].get('event_id', '')}").replace("event  ", "event ")
    return '<span class="sub">Not crosswalked</span>'


def pick_cell(row: dict) -> str:
    pick = row.get("pick")
    if not pick:
        return '<span class="sub">—<br>No supported line</span>'
    return (f'<span class="pick">{esc(pick["selection"])}</span><br><span class="num">{pick["fair_prob"]*100:.2f}% · '
            f'{pick["fair_decimal"]:.2f} / {american(pick["fair_american"])}</span><br>'
            f'{badge(pick["confidence"])} <span class="sub">winner lean only</span>')


def written_cell(row: dict, prefix: str = "") -> str:
    pred = PRED_BY_ROW.get(row["id"])
    if not pred:
        return '<span class="sub">—</span>'
    return (f'<a class="pick" href="{prefix}picks.html#{esc(pred["prediction_id"])}">{esc(pred["selection"])}</a><br>'
            f'<span class="num">{pred["prob"]*100:.2f}% · {american(pred["fair_american"])}</span><br>{badge("High")}')


def fixture_table(rows: list[dict], prefix: str = "") -> str:
    if not rows:
        return '<div class="card empty">No upcoming match is present in this capture.</div>'
    body = []
    for row in rows:
        body.append(f"""<tr id="row-{esc(row['id'])}" data-sport="{esc(row['sport'])}"><td class="num">{esc(fmt_time(row['start_utc']))}</td><td><a href="{prefix}sports/{ri.SLUGS[row['sport']]}.html">{esc(row['sport'])}</a></td><td><strong>{esc(row['match'])}</strong><br><span class="sub">{esc(row.get('competition') or '')}{' · ' + esc(row['venue']) if row.get('venue') else ''}</span></td><td>{olbg_cell(row)}</td><td>{pick_cell(row)}</td><td>{written_cell(row,prefix)}</td><td>{source_cell(row,prefix)}</td></tr>""")
    return f"""<div class="scroll"><table class="match-table"><thead><tr><th>Start</th><th>Sport</th><th>Match</th><th>OLBG card</th><th>Match-winner lean · fair line</th><th>Fully written pick</th><th>Official source / review</th></tr></thead><tbody>{''.join(body)}</tbody></table></div>"""


def prediction_card(pred: dict, prefix: str = "") -> str:
    facts = "".join(f'<li><strong>{esc(f["label"])}:</strong> {esc(f["value"])} · {link(f["source_url"], "Official source")}</li>' for f in pred["facts"])
    return f"""<article class="card" id="{esc(pred['prediction_id'])}"><div class="cardhead"><div><h3>{esc(pred['match'])}</h3><p class="sub">{esc(pred['competition'])} · {esc(fmt_time(pred['start_utc']))} · {esc(pred['venue'])}</p></div>{badge('High')}</div>
<div class="pickbanner"><span class="sub">EXACT SELECTION</span><br><span class="pick">{esc(pred['selection'])}</span><br><strong>{pred['prob']*100:.2f}% estimated chance · fair {pred['fair_decimal']:.2f} / {american(pred['fair_american'])}</strong><br><span class="sub">{esc(pred['market'])}</span></div>
<div class="prose">{esc(pred['prediction_text'])}</div><p class="sub">{pred['word_count']} words · {pred['sample_games']} game minimum sample · <a href="{prefix}methodology.html#confidence">Why this is High</a></p>
<p>{link(pred['olbg_url'], 'Open the OLBG event')} · {link(pred['official_source_url'], 'Open the official fixture')} · <a href="{prefix}fixtures.html#row-{esc(pred['row_id'])}">Match-table location</a></p>
<details open><summary>Evidence behind this prediction</summary><ul class="facts">{facts}</ul><p class="warn small">{esc(pred['availability_note'])}</p></details></article>"""


def build_index() -> str:
    rows = []
    for i, pred in enumerate(PREDICTIONS, 1):
        rows.append(f"""<tr><td class="num"><strong>{i}</strong></td><td class="num">{esc(fmt_time(pred['start_utc']))}</td><td><strong>{esc(pred['match'])}</strong><br><span class="sub">{esc(pred['competition'])}</span></td><td><span class="pick">{esc(pred['selection'])}</span><br><span class="sub">{esc(pred['market'])}</span></td><td class="num"><strong>{pred['prob']*100:.2f}%</strong><br>{pred['fair_decimal']:.2f} / {american(pred['fair_american'])}</td><td>{badge('High')}</td><td><a href="picks.html#{esc(pred['prediction_id'])}">Read {pred['word_count']}-word analysis</a><br>{link(pred['official_source_url'],'Official fixture')} · {link(pred['olbg_url'],'OLBG')}</td></tr>""")
    sport_rows = []
    for sport in ri.SPORTS:
        s = DESK["summary"]["by_sport"][sport]
        sport_rows.append(f"""<tr><td><a href="sports/{ri.SLUGS[sport]}.html"><strong>{esc(sport)}</strong></a></td><td class="num">{s['rows']}</td><td class="num">{s['olbg_listed']}</td><td class="num">{s['priced']}</td><td class="num target">{s['written_high']} / 5</td><td>{esc(s['shortfall_reason']) if s['shortfall'] else '<span class="badge high">Target met</span>'}</td></tr>""")
    body = f"""
<section class="exec"><h2>Executive summary: four picks pass every strict gate</h2><p><strong>Start with the table below.</strong> It gives the match, exact betting selection, estimated chance, fair price and analysis location. Every pick is above 70%, inside -250…+10000, tied to a captured OLBG event and recomputed from official NHL payloads.</p><p>The five-per-sport daily target is not filled artificially. Ice Hockey has four; the other 14 sports have sourced shortfalls. {len(ROWS)} upcoming rows remain available in the full inventory, including official-schedule supplements that are not represented as OLBG listings.</p><div class="actions"><a class="button" href="picks.html">Read all four predictions</a><a class="button secondary" href="fixtures.html">Browse all {len(ROWS)} matches</a><a class="button secondary" href="flagged.html">Review {FLAGS['count']} flags</a></div></section>
<div class="kpis"><div class="kpi"><strong>4</strong><span>Written High picks</span></div><div class="kpi"><strong>71.31%</strong><span>Highest estimated chance</span></div><div class="kpi"><strong>{len(ROWS)}</strong><span>Upcoming match rows</span></div><div class="kpi"><strong>{DESK['summary']['olbg_listed']}</strong><span>Captured OLBG crosswalks</span></div><div class="kpi"><strong>{FLAGS['count']}</strong><span>Review flags</span></div></div>
<h2 class="section">Today's strict picks — strongest first</h2><div class="scroll"><table><thead><tr><th>#</th><th>Start</th><th>Match</th><th>Exact selection</th><th>Chance · fair price</th><th>Grade</th><th>Analysis and sources</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<p class="sub">Prices are fair lines with no bookmaker margin. OLBG links identify where the event is listed; they do not claim that OLBG offers our exact fair number.</p>
<h2 class="section">Five-per-sport coverage and honest shortfalls</h2><div class="scroll"><table><thead><tr><th>Sport</th><th>Matches</th><th>OLBG-linked</th><th>Priced</th><th>Written High / target</th><th>Status or reason</th></tr></thead><tbody>{''.join(sport_rows)}</tbody></table></div>
<h2 class="section">Release position</h2><div class="grid2"><div class="ok"><strong>Evidence checks passed.</strong><br>{AUDIT['summary']['payloads_ok']} stored payloads match their recorded SHA-256 values. The four published fixtures, player statistics and probabilities are reproducible from raw NHL responses.</div><div class="warn"><strong>Review remains visible.</strong><br>{DESK['summary']['review_required']} rows lack an official fixture programme, and {AUDIT['summary']['capture_failures']} source captures failed. These items do not enter the written High list.</div></div>
"""
    return page("Strict OLBG predictions", body, "index.html", "Four fully written picks above 70%, official evidence, exact selections and no invented fixtures.")


def build_picks() -> str:
    body = f"""<section class="exec"><h2>{len(PREDICTIONS)} fully written High predictions</h2><p>Each card states the exact selection, shows its fair price and chance, provides unique match analysis, and links the official fixture, OLBG event and every supporting statistic.</p><p class="warn"><strong>Team-news limitation:</strong> no official injury report is in this pinned capture, so these cards make no player-availability claim.</p></section>{''.join(prediction_card(p) for p in PREDICTIONS)}"""
    return page("Written picks", body, "picks.html", "Full analysis for the four selections that pass every release-integrity gate.")


def build_fixtures() -> str:
    options = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in ri.SPORTS)
    body = f"""<section class="exec"><h2>Complete upcoming inventory</h2><p>{len(ROWS)} rows from the pinned OLBG and official-schedule capture. “Match-winner lean” is only a selection and fair line; “Fully written pick” is reserved for complete analysis. A missing official programme leaves the official fixture field blank and creates a review flag.</p></section>
<div class="filters"><input id="q" type="search" placeholder="Filter by team, player or competition" aria-label="Filter matches"><select id="sport" aria-label="Filter by sport"><option value="">All 15 sports</option>{options}</select><span class="sub" id="visible">{len(ROWS)} rows shown</span></div>{fixture_table(ROWS)}
<script>const q=document.getElementById('q'),s=document.getElementById('sport'),rows=[...document.querySelectorAll('.match-table tbody tr')];function filter(){{let n=0;for(const r of rows){{const show=(!q.value||r.innerText.toLowerCase().includes(q.value.toLowerCase()))&&(!s.value||r.dataset.sport===s.value);r.style.display=show?'':'none';if(show)n++}}document.getElementById('visible').textContent=n+' rows shown'}}q.addEventListener('input',filter);s.addEventListener('change',filter);</script>"""
    return page("All matches", body, "fixtures.html", "Every upcoming row, with OLBG status, winner leans, written picks and official-source review links.")


def build_sports_index() -> str:
    cards = []
    for sport in ri.SPORTS:
        s = DESK["summary"]["by_sport"][sport]
        cards.append(f"""<div class="card"><h3><a href="sports/{ri.SLUGS[sport]}.html">{esc(sport)}</a></h3><p><strong>{s['written_high']} / 5</strong> written High · {s['rows']} matches · {s['olbg_listed']} OLBG-linked</p><p class="sub">{esc(s['shortfall_reason'])}</p><a href="sports/{ri.SLUGS[sport]}.html">Open sport page →</a></div>""")
    body = f'<section class="exec"><h2>All 15 covered sports</h2><p>Each category page keeps its matches, analysis and shortfall explanation together. No category is removed merely because it has no qualifying pick.</p></section><div class="grid2">{"".join(cards)}</div>'
    return page("Sports", body, "sports.html", "Fifteen category pages with match tables, analysis and explicit daily-target status.")


def build_sport(sport: str) -> str:
    rows = [r for r in ROWS if r["sport"] == sport]
    preds = [p for p in PREDICTIONS if p["sport"] == sport]
    s = DESK["summary"]["by_sport"][sport]
    body = f"""<section class="exec"><h2>{esc(sport)}: {s['written_high']} of five written High predictions</h2><p>{esc(s['shortfall_reason']) if s['shortfall'] else 'The daily target is met.'}</p><div class="actions"><a class="button secondary" href="../fixtures.html">All sports</a><a class="button secondary" href="../flagged.html">Flagged for Review</a></div></section>
<div class="kpis"><div class="kpi"><strong>{s['rows']}</strong><span>Match rows</span></div><div class="kpi"><strong>{s['olbg_listed']}</strong><span>OLBG-linked</span></div><div class="kpi"><strong>{s['official_sourced']}</strong><span>Official fixture sources</span></div><div class="kpi"><strong>{s['priced']}</strong><span>Winner leans</span></div><div class="kpi"><strong>{s['written_high']}</strong><span>Written High</span></div></div>
{('<h2 class="section">Written analysis</h2>' + ''.join(prediction_card(p,'../') for p in preds)) if preds else '<p class="warn">No prediction meets every strict gate in this sport. Empty analysis is preferable to unsupported prose.</p>'}
<h2 class="section">Upcoming {esc(sport)} matches</h2>{fixture_table(rows,'../')}"""
    return page(sport, body, "sports.html", f"{sport}: upcoming matches, official sources, exact picks and daily-target status.", "../")


def build_markets() -> str:
    taxonomy = {}
    for row in ROWS:
        names = {m["market_name"].split(" (")[0] for m in (row.get("markets") or {}).values()}
        taxonomy.setdefault(row["sport"], set()).update(names)
    tax_rows = "".join(f'<tr><td><a href="sports/{ri.SLUGS[s]}.html">{esc(s)}</a></td><td>{esc(", ".join(sorted(taxonomy.get(s, []))) or "No supported market")}</td></tr>' for s in ri.SPORTS)
    selected = "".join(prediction_card(p) for p in PREDICTIONS)
    no_market = [c for c in CANDIDATES["ri"] if c["decision"] == "no-qualifying-market"]
    gaps = "".join(f'<li><strong>{esc(c["match"])}</strong>: winner, regulation, puck-line, game-total and team-total lines were tested; none met both numerical tests. {link(c["official_url"],"Official fixture")} · {link(c["olbg_url"],"OLBG")}</li>' for c in no_market)
    body = f"""<section class="exec"><h2>Markets investigated</h2><p>Match-winner lines come first. Handicap/puck-line and totals are included wherever supported. The six adequately sampled OLBG-linked NHL games also received regulation, alternate puck-line, alternate game-total and team-total calculations.</p><p>Only one selection per event receives a full write-up. An eligible number alone is not enough: source, OLBG, sample and calculation checks must also pass.</p></section>
<h2 class="section">Market coverage by sport</h2><div class="scroll"><table><thead><tr><th>Sport</th><th>Published market families</th></tr></thead><tbody>{tax_rows}</tbody></table></div>
<h2 class="section">Two eligible games without a strict selection</h2><ul class="facts">{gaps}</ul>
<h2 class="section">Selected markets and full analysis</h2>{selected}"""
    return page("Markets and lines", body, "markets.html", "Winner, handicap, totals and additional NHL markets, with unsupported games left without a pick.")


def build_sources() -> str:
    rows = []
    for s in SOURCES["sources"]:
        rows.append(f'<tr><td><code>{esc(s["id"])}</code></td><td>{esc(s.get("sport") or "")}</td><td>{link(s["url"],s["url"])}</td><td class="num">{s["status"]}</td><td class="num">{s["bytes"]}</td><td><code>{esc(s["sha256"][:16])}…</code></td></tr>')
    failures = "".join(f'<tr><td><code>{esc(s.get("id"))}</code></td><td>{link(s.get("url") or "",s.get("url") or "")}</td><td class="num">{esc(s.get("status"))}</td><td>{esc(s.get("error") or "Capture failed")}</td></tr>' for s in SOURCES["failures"])
    body = f"""<section class="exec"><h2>Source register</h2><p>{SOURCES['total']} successful payloads are pinned in <code>data/session-b6643783/capture/{esc(ri.CAPTURE_ID)}/</code>. Every digest was independently recomputed. {SOURCES['failure_count']} failures remain visible below.</p></section>
<h2 class="section">Successful captures</h2><div class="scroll"><table><thead><tr><th>ID</th><th>Sport</th><th>Official or OLBG URL</th><th>HTTP</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2 class="section">Failed captures</h2><div class="scroll"><table><thead><tr><th>ID</th><th>URL</th><th>HTTP</th><th>Error</th></tr></thead><tbody>{failures}</tbody></table></div>"""
    return page("Sources", body, "sources.html", "Exact source URLs, response sizes and content digests, including failed captures.")


def candidate_table(items: list[dict]) -> str:
    rows = "".join(f"""<tr><td>{esc(c['match'])}</td><td>{esc(c['market'] or '—')}</td><td>{esc(c['selection'] or '—')}</td><td class="num">{f"{c['fair_prob']*100:.2f}%" if c['fair_prob'] is not None else '—'}<br>{american(c['fair_american']) if c['fair_american'] is not None else '—'}</td><td>{esc(c['decision'])}<br><span class="sub">{esc('; '.join(c['reasons']))}</span></td><td>{link(c['official_url'],'Official')} · {link(c['olbg_url'],'OLBG')}</td></tr>""" for c in items)
    return f'<div class="scroll"><table><thead><tr><th>Match</th><th>Market</th><th>Selection</th><th>Chance · fair</th><th>Decision and reason</th><th>Links</th></tr></thead><tbody>{rows}</tbody></table></div>'


def build_audit() -> str:
    defects = "".join(f'<div class="danger"><strong>{esc(d["id"])}</strong><br>{esc(d["detail"])}<br><code>{esc(d["where"])}</code></div>' for d in AUDIT["known_defects"])
    row_audit = "".join(f'<tr><td><code>{esc(r["row_id"])}</code></td><td>{esc(r["source_kind"])}</td><td><code>{esc(r["capture_id"])}</code></td><td>{"PASS" if r["payload_sha_match"] else "FAIL"}</td><td>{link(r["review_url"],"Review source")}</td></tr>' for r in AUDIT["rows"])
    body = f"""<section class="exec"><h2>Independent release audit</h2><p>{AUDIT['summary']['payloads_ok']} / {AUDIT['summary']['payloads_total']} successful payload digests match · {AUDIT['summary']['rows']} row provenance records · {AUDIT['summary']['row_hash_mismatches']} hash mismatches · {AUDIT['summary']['legacy_numeric_candidates']} legacy numerical candidates rejected.</p><p>{esc(AUDIT['scope_note'])}</p></section>
<h2 class="section">Defects prevented from reaching the pick list</h2><div class="grid2">{defects}</div>
<h2 class="section">New RI candidate ledger</h2>{candidate_table(CANDIDATES['ri'])}
<h2 class="section">Legacy numerical candidates — all rejected</h2><p class="sub">These rows passed only the displayed probability/price screen in the earlier desk. They fail source, OLBG, sample or confidence-cap checks.</p>{candidate_table(CANDIDATES['legacy'])}
<details><summary>Open all {len(AUDIT['rows'])} row provenance checks</summary><div class="scroll"><table><thead><tr><th>Row</th><th>Source type</th><th>Capture</th><th>Digest</th><th>Review</th></tr></thead><tbody>{row_audit}</tbody></table></div></details>"""
    return page("Release audit", body, "audit.html", "Payload checks, calculation defects and accept/reject reasons for every numerical candidate.")


def build_flagged() -> str:
    rows = []
    for i, flag in enumerate(FLAGS["flags"]):
        anchor = f' id="row-{esc(flag["row_id"])}"' if flag["row_id"] else ""
        sport_link = ""
        if flag["row_id"] and flag["row_id"] in BY_ID:
            sport = BY_ID[flag["row_id"]]["sport"]
            sport_link = f'<br><a href="sports/{ri.SLUGS[sport]}.html">Open {esc(sport)}</a>'
        rows.append(f'<tr{anchor}><td>{esc(flag["group"])}</td><td><strong>{esc(flag["title"])}</strong><br><span class="sub">{esc(flag["kind"])}</span></td><td>{esc(flag["detail"])}</td><td>{link(flag["source_url"],"Open review link")}{sport_link}</td></tr>')
    body = f"""<section class="exec"><h2>Flagged for Review: {FLAGS['count']} items</h2><p>Daily-target shortfalls, unverified fixture identity, capture failures, source defects and availability limitations are collected here. These flags do not hide failed requirements and do not block the four clean selections.</p></section><div class="scroll"><table><thead><tr><th>Group</th><th>Issue</th><th>What remains unsupported</th><th>Manual review</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>"""
    return page("Flagged for Review", body, "flagged.html", "Every unverified fixture, source failure, calculation defect and daily-target shortfall.")


def build_methodology() -> str:
    body = """<section class="exec"><h2>Strict rules, published before the picks</h2><p>This desk separates an upcoming-match inventory from a much smaller written-pick list. A fair number is not a sportsbook quote, an official fixture is not an OLBG listing, and a winner lean is not a written prediction.</p></section>
<h2 class="section" id="confidence">Written High confidence</h2><div class="card"><ul class="facts"><li>Estimated chance must be <strong>strictly greater than 70%</strong>, not rounded up from below.</li><li>Fair American price must be from <strong>-250 through +10000</strong>. Decimal is 1/p; for p ≥ .5, American is −100p/(1−p).</li><li>The fixture must appear in an official schedule payload and have a captured OLBG event card.</li><li>NHL selections require at least ten games played for each club. Other published caps are never overridden to fill a quota.</li><li>The selection must have unique, fully written analysis of at least 30 words with current form, recent history, match statistics and player context from official sources.</li></ul><p>The overlap is narrow: 70% is approximately -233.33 and -250 is approximately 71.43%. Selections above that ceiling are outside the requested price band.</p></div>
<h2 class="section">NHL scoring calculation</h2><div class="card"><p>Official goals-for and goals-against rates are partially pooled: 70% club rate and 30% league prior. Home expected goals combine home attack with away defence and a 1.06 home factor; away expected goals combine away attack with home defence and a 0.94 location factor. Expected goals are clamped to 0.8–5.2.</p><p>Independent Poisson score distributions produce regulation winner, puck-line, game-total and team-total chances. Moneyline including overtime/shootout uses regulation win plus half the draw chance, then shrinks 88% toward even odds and clamps to .18–.82. All probabilities are rounded to four decimals before fair prices are calculated.</p></div>
<h2 class="section">Prediction-writing rules</h2><div class="card"><ul class="facts"><li>Exact selection and market appear in the prose; overtime/team-total/handicap conditions are explicit.</li><li>Current records, last-ten form, home/away splits, season scoring rates and named official player statistics support each argument.</li><li>No availability claim is made without an official injury or team-news report. This capture has no such report, so the limitation is shown on every card.</li><li>Duplicate and boilerplate analysis is rejected by exact-text and pairwise-similarity gates.</li></ul></div>
<h2 class="section">What remains deliberately unsupported</h2><div class="warn">No injury report, no five-per-sport quota filling, no official-fixture claim from an OLBG URL, and no promotion of the earlier defective NHL calculations. The Flagged for Review page lists every known gap. Fair chances are estimates, not guarantees.</div>"""
    return page("Methodology", body, "methodology.html", "The exact probability, price, source, sample and writing rules behind the release.")


def main() -> int:
    ri.SITE.mkdir(parents=True, exist_ok=True)
    (ri.SITE / "sports").mkdir(exist_ok=True)
    (ri.SITE / "assets").mkdir(exist_ok=True)
    (ri.SITE / "assets" / "site.css").write_text(CSS, encoding="utf-8")
    pages = {
        "index.html": build_index(), "picks.html": build_picks(), "fixtures.html": build_fixtures(),
        "sports.html": build_sports_index(), "markets.html": build_markets(), "sources.html": build_sources(),
        "audit.html": build_audit(), "flagged.html": build_flagged(), "methodology.html": build_methodology(),
    }
    for name, content in pages.items():
        (ri.SITE / name).write_text(content, encoding="utf-8")
    for sport in ri.SPORTS:
        (ri.SITE / "sports" / f"{ri.SLUGS[sport]}.html").write_text(build_sport(sport), encoding="utf-8")
    print(f"Built {len(list(ri.SITE.rglob('*.html')))} HTML pages in {ri.SITE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

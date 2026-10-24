#!/usr/bin/env python3
"""Render the A172 clarity-first static dashboard; no external front-end dependencies."""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

import engine

E = html.escape
DESK = json.loads((engine.DATA / "desk.json").read_text(encoding="utf-8"))
PREDICTIONS = json.loads((engine.DATA / "predictions.json").read_text(encoding="utf-8"))["predictions"]
FLAGS = json.loads((engine.DATA / "flags.json").read_text(encoding="utf-8"))["flags"]
SOURCES = json.loads((engine.DATA / "sources.json").read_text(encoding="utf-8"))
CANDIDATES = json.loads((engine.DATA / "candidates.json").read_text(encoding="utf-8"))["candidates"]
AUDIT = json.loads((engine.DATA / "audit.json").read_text(encoding="utf-8"))
ROWS = DESK["rows"]
BY_ID = {r["id"]: r for r in ROWS}


def american(value) -> str:
    if value is None or value == "":
        return ""
    return f"+{value}" if value > 0 else str(value)


def stamp(value: str) -> str:
    if not value:
        return ""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%d %b %Y · %H:%M UTC")


def short_stamp(value: str) -> str:
    if not value:
        return ""
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.strftime("%d %b · %H:%M")


def url(value: str, label: str, cls: str = "") -> str:
    if not value:
        return ""
    return f'<a class="{E(cls)}" href="{E(value, quote=True)}" target="_blank" rel="noopener noreferrer">{E(label)}</a>'


def nav(prefix: str = "") -> str:
    links = [
        ("index.html", "Overview"), ("picks.html", "Written picks"), ("matches.html", "All OLBG matches"),
        ("sports.html", "Sports"), ("markets.html", "Markets"), ("coverage.html", "Coverage"),
        ("flagged.html", "Flagged for Review"), ("sources.html", "Sources"), ("methodology.html", "Method"),
    ]
    return "".join(f'<a href="{prefix}{href}">{label}</a>' for href, label in links)


def page(title: str, body: str, prefix: str = "", description: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · OLBG4 A172</title><meta name="description" content="{E(description or title, quote=True)}">
<link rel="stylesheet" href="{prefix}assets/site.css"></head>
<body><header class="topbar"><a class="brand" href="{prefix}index.html"><span>OLBG4</span><small>evidence desk</small></a>
<nav aria-label="Main navigation">{nav(prefix)}</nav></header>
<main>{body}</main><footer><strong>Snapshot:</strong> {E(stamp(DESK['captured_utc']))}. OLBG lists events; official bodies support facts. Fair lines are our own, not offers. No unsupported value is filled in.</footer>
</body></html>"""


def exec_intro(title: str, text: str) -> str:
    return f'<section class="exec"><p class="eyebrow">Executive summary</p><h1>{E(title)}</h1><p>{E(text)}</p></section>'


def kpis() -> str:
    s = DESK["summary"]
    values = [(s["rows_total"], "upcoming OLBG listings"), (s["official_sourced"], "official fixture crosswalks"),
              (s["priced"], "rows with an own winner line"), (len(PREDICTIONS), "fully written High picks")]
    return '<div class="kpis">' + "".join(f'<div class="kpi"><strong>{v}</strong><span>{E(label)}</span></div>' for v, label in values) + "</div>"


def source_cell(row: dict, prefix: str = "") -> str:
    if row["source_status"] == "official":
        return url(row["official_url"], "Official source") + f'<small>{E(row["capture_id"])}</small>'
    return f'<span class="blank">—</span> <a class="flag-link" href="{prefix}flagged.html">Unverified fixture</a>'


def pick_cell(row: dict) -> str:
    pick = row.get("pick")
    if not pick:
        return '<span class="blank">—</span><small>No originated line</small>'
    confidence = pick["confidence"].lower()
    return (f'<strong>{E(pick["selection"])}</strong><small>{pick["fair_prob"]:.1%} · {american(pick["fair_american"])} · '
            f'<span class="confidence {confidence}">{E(pick["confidence"])}</span></small>')


def row_table(rows: list[dict], prefix: str = "", limit: int | None = None) -> str:
    shown = rows[:limit] if limit else rows
    out = ['<div class="table-wrap"><table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>OLBG event / match</th><th>Own match-winner line</th><th>Official source</th><th>OLBG listing</th></tr></thead><tbody>']
    for row in shown:
        sport_href = f'{prefix}sports/{row["sport_slug"]}.html'
        match = E(row["match"])
        if row["source_status"] == "official" and row["match"] != row["olbg"]["event"]:
            match = f'{E(row["olbg"]["event"])}<small>Official: {E(row["match"])}</small>'
        out.append(f'<tr id="row-{E(row["id"], quote=True)}"><td>{E(short_stamp(row["start_utc"]))}</td>'
                   f'<td><a href="{sport_href}">{E(row["sport"])}</a></td><td>{match}</td>'
                   f'<td>{pick_cell(row)}</td><td>{source_cell(row, prefix)}</td>'
                   f'<td>{url(row["olbg"]["url"], "Open OLBG")}</td></tr>')
    out.append('</tbody></table></div>')
    if not shown:
        return '<p class="empty">No upcoming OLBG listing was captured for this sport in the snapshot window.</p>'
    return "".join(out)


def prediction_card(p: dict, prefix: str = "", full: bool = True) -> str:
    facts = "".join(f'<li><span>{E(f["label"])}</span><strong>{E(f["value"])}</strong>{url(f["source_url"], "Source")}</li>' for f in p["facts"])
    text = f'<p class="prediction-copy">{E(p["prediction_text"])}</p>' if full else ""
    details = f'<details><summary>Evidence links & availability note</summary><ul class="facts">{facts}</ul><p class="note">{E(p["availability_note"])}</p></details>' if full else ""
    return f'''<article class="pick-card" id="{E(p["prediction_id"], quote=True)}">
<div class="pick-top"><span class="sport-pill">{E(p["sport"])}</span><span>{E(stamp(p["start_utc"]))}</span><span class="confidence high">High</span></div>
<h2>{E(p["match"])}</h2><div class="selection"><span>Exact selection</span><strong>{E(p["selection"])}</strong>
<span>{p["prob"]:.1%} · fair American {american(p["fair_american"])} · {E(p["market"])}</span></div>
{text}<div class="pick-links"><a href="{prefix}sports/{engine.SLUGS[p['sport']]}.html">Sport page</a>{url(p["official_source_url"], "Official fixture")}{url(p["olbg_url"], "OLBG event")}</div>{details}</article>'''


def coverage_table(prefix: str = "") -> str:
    out = ['<div class="table-wrap"><table><thead><tr><th>Sport</th><th>OLBG rows</th><th>Official</th><th>Priced</th><th>Written High</th><th>Daily target</th><th>Page</th></tr></thead><tbody>']
    for sport in engine.SPORTS:
        s = DESK["summary"]["by_sport"][sport]
        out.append(f'<tr><td>{E(sport)}</td><td>{s["rows"]}</td><td>{s["official_sourced"]}</td><td>{s["priced"]}</td>'
                   f'<td>{s["written_high"]}</td><td>{"5/5" if s["shortfall"] == 0 else str(5-s["shortfall"])+"/5 · shortfall flagged"}</td>'
                   f'<td><a href="{prefix}sports/{s["slug"]}.html">Open {E(sport)}</a></td></tr>')
    out.append('</tbody></table></div>')
    return "".join(out)


def index() -> None:
    today = DESK["captured_utc"][:10]
    todays = [p for p in PREDICTIONS if p["start_utc"][:10] == today]
    upcoming = [p for p in PREDICTIONS if p["start_utc"][:10] != today]
    body = exec_intro("Upcoming OLBG matches, clear picks, official evidence",
                      f"{len(PREDICTIONS)} written High picks from {len(ROWS)} OLBG listings. Start here: the exact selection, fair price and analysis are below; every other match is one click away.")
    body += kpis()
    body += '''<section class="notice"><strong>Read the price rule before the picks.</strong> High requires a probability above 70% and a fair American price from −250 through +10000. A fair 70% price is about −233, so only the narrow ≥70% to −250 overlap qualifies. No pick is stretched to meet a quota.</section>'''
    body += '<section><div class="section-head"><div><p class="eyebrow">Today · UTC</p><h2>Highest-confidence written picks</h2></div><a href="picks.html">All written picks →</a></div>'
    body += "".join(prediction_card(p) for p in todays) if todays else '<p class="empty">No eligible written High selection starts on the capture date. See upcoming picks below; no substitute is invented.</p>'
    body += '</section>'
    if upcoming:
        body += '<section><div class="section-head"><div><p class="eyebrow">Upcoming</p><h2>Later fixtures</h2></div></div>' + "".join(prediction_card(p) for p in upcoming) + '</section>'
    body += '<section><div class="section-head"><div><p class="eyebrow">Where everything is</p><h2>15-sport coverage</h2></div><a href="matches.html">Full OLBG inventory →</a></div>' + coverage_table() + '</section>'
    body += '<section><div class="section-head"><div><p class="eyebrow">Next up</p><h2>Earliest captured listings</h2></div></div>' + row_table(ROWS, limit=12) + '</section>'
    (engine.SITE / "index.html").write_text(page("OLBG overview", body), encoding="utf-8")


def picks() -> None:
    lean_rows = [r for r in ROWS if r.get("pick")]
    body = exec_intro("Written High picks", f"{len(PREDICTIONS)} unique analyses. Each card names the bet before the reasoning and links every fact to an official source. Low/Medium winner leans are listed separately below.")
    body += '<section>' + ("".join(prediction_card(p) for p in PREDICTIONS) if PREDICTIONS else '<p class="empty">No selection passed every numerical, source, sample and evidence gate.</p>') + '</section>'
    body += '<section><div class="section-head"><div><p class="eyebrow">Not High</p><h2>Other originated winner leans</h2></div></div><p>These are transparent prices, not fully written High predictions. High labels are never assigned without the required analysis.</p>' + row_table(lean_rows) + '</section>'
    (engine.SITE / "picks.html").write_text(page("Written High picks", body), encoding="utf-8")


def matches() -> None:
    body = exec_intro("All upcoming OLBG listings", f"{len(ROWS)} captured rows in the exact 15-sport scope. Official source and OLBG listing are separate columns; blanks and review flags are intentional.")
    body += '<section><input class="search" type="search" placeholder="Filter rows by team, sport or selection…" aria-label="Filter match rows" data-filter="match-table">' + row_table(ROWS).replace('<table>', '<table id="match-table">', 1) + '</section>'
    body += '<script>document.querySelectorAll("[data-filter]").forEach(i=>i.addEventListener("input",()=>{const q=i.value.toLowerCase();document.querySelectorAll("#"+i.dataset.filter+" tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q))}));</script>'
    (engine.SITE / "matches.html").write_text(page("All OLBG matches", body), encoding="utf-8")


def sports() -> None:
    body = exec_intro("Sports coverage", "Every requested category has its own page, including categories with zero upcoming listings or zero qualifying written picks.")
    body += '<section>' + coverage_table() + '</section>'
    (engine.SITE / "sports.html").write_text(page("Sports", body), encoding="utf-8")


def sport_pages() -> None:
    for sport in engine.SPORTS:
        slug = engine.SLUGS[sport]
        rows = [r for r in ROWS if r["sport"] == sport]
        preds = [p for p in PREDICTIONS if p["sport"] == sport]
        summary = DESK["summary"]["by_sport"][sport]
        body = exec_intro(sport, f'{summary["rows"]} OLBG listings · {summary["official_sourced"]} official fixture crosswalks · {summary["priced"]} own winner lines · {summary["written_high"]}/5 written High picks.')
        body += '<section><div class="section-head"><h2>Written High picks</h2></div>' + ("".join(prediction_card(p, "../") for p in preds) if preds else '<p class="empty">No written High pick passed every gate. The shortfall is published on Flagged for Review.</p>') + '</section>'
        body += '<section><div class="section-head"><h2>All captured OLBG listings</h2></div>' + row_table(rows, "../") + '</section>'
        path = engine.SITE / "sports" / f"{slug}.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page(sport, body, "../"), encoding="utf-8")


def markets() -> None:
    body = exec_intro("Originated markets", "Winner, handicap and total markets are investigated wherever official inputs support them. Selection percentages and fair American prices are shown together; unsupported markets stay absent.")
    out = ['<section><div class="table-wrap"><table><thead><tr><th>Match</th><th>Market</th><th>Line</th><th>Selections · probability · fair American</th><th>Sources</th></tr></thead><tbody>']
    count = 0
    for row in ROWS:
        for key, market in (row.get("markets") or {}).items():
            count += 1
            legs = '<br>'.join(f'{E(s["label"])} — {s["fair_prob"]:.1%} · {american(s["fair_american"])}' for s in market["selections"])
            out.append(f'<tr><td>{E(row["match"])}<small>{E(row["sport"])} · {E(short_stamp(row["start_utc"]))} UTC</small></td>'
                       f'<td>{E(market["market_name"])}<small>{E(key)}</small></td><td>{E(str(market.get("line") if market.get("line") is not None else "—"))}</td>'
                       f'<td>{legs}<small>Probability sum: {market["probability_sum"]:.4f}</small></td>'
                       f'<td>{url(row["official_url"], "Official")}<br>{url(row["olbg"]["url"], "OLBG")}</td></tr>')
    out.append('</tbody></table></div></section>')
    body += f'<p class="note">{count} originated market families.</p>' + "".join(out)
    (engine.SITE / "markets.html").write_text(page("Originated markets", body), encoding="utf-8")


def coverage() -> None:
    body = exec_intro("Coverage and shortfalls", "The five-per-sport written-pick target is a goal, not permission to invent events, statistics or eligibility. Every gap remains visible.")
    body += '<section>' + coverage_table() + '</section><section><h2>What the counts mean</h2><ul><li><strong>OLBG rows:</strong> upcoming listings actually captured from the sport hubs.</li><li><strong>Official:</strong> listings crosswalked to an official league, tour, federation or event payload.</li><li><strong>Priced:</strong> rows with our own match-winner selection; handicap and totals appear on the Markets page.</li><li><strong>Written High:</strong> only selections passing probability, price, source, sample, recent-form and prose gates.</li></ul></section>'
    (engine.SITE / "coverage.html").write_text(page("Coverage", body), encoding="utf-8")


def flagged() -> None:
    body = exec_intro("Flagged for Review", f"{len(FLAGS)} non-blocking findings. These are not hidden and do not become facts by repetition. Follow the linked source to review each issue.")
    groups = {}
    for flag in FLAGS:
        groups.setdefault(flag["group"], []).append(flag)
    for group, items in groups.items():
        body += f'<section><h2>{E(group)} <span class="count">{len(items)}</span></h2><div class="table-wrap"><table><thead><tr><th>Item</th><th>Finding</th><th>Sport</th><th>Review link</th></tr></thead><tbody>'
        for i, flag in enumerate(items, 1):
            link = url(flag.get("source_url") or "", "Open source") if flag.get("source_url") else '<span class="blank">—</span>'
            row_link = f'<br><a href="matches.html#row-{E(flag["row_id"], quote=True)}">Locate row</a>' if flag.get("row_id") else ""
            body += f'<tr><td>{E(flag["title"])}</td><td>{E(flag["detail"])}</td><td>{E(flag.get("sport") or "")}</td><td>{link}{row_link}</td></tr>'
        body += '</tbody></table></div></section>'
    (engine.SITE / "flagged.html").write_text(page("Flagged for Review", body), encoding="utf-8")


def sources() -> None:
    body = exec_intro("Source register", f'Capture {DESK["capture_id"]}: {SOURCES["total"]} successful payloads and {SOURCES["failure_count"]} failures. SHA-256 values identify the exact bytes used by the build.')
    body += '<section><h2>Successful captures</h2><div class="table-wrap"><table><thead><tr><th>Capture ID</th><th>Role</th><th>URL</th><th>Bytes</th><th>SHA-256</th></tr></thead><tbody>'
    for record in SOURCES["sources"]:
        role = "OLBG listing only" if record["id"].startswith("olbg_") else "Captured evidence payload"
        body += f'<tr><td>{E(record["id"])}</td><td>{role}</td><td>{url(record["url"], "Open source")}</td><td>{record["bytes"]}</td><td><code>{E(record["sha256"])}</code></td></tr>'
    body += '</tbody></table></div></section><section><h2>Failed captures</h2><div class="table-wrap"><table><thead><tr><th>ID</th><th>Status</th><th>Error</th><th>URL</th></tr></thead><tbody>'
    for failure in SOURCES["failures"]:
        body += f'<tr><td>{E(failure.get("id") or "")}</td><td>{E(str(failure.get("status") or ""))}</td><td>{E(failure.get("error") or "")}</td><td>{url(failure.get("url") or "", "Open attempted source")}</td></tr>'
    body += '</tbody></table></div></section>'
    (engine.SITE / "sources.html").write_text(page("Sources", body), encoding="utf-8")


def methodology() -> None:
    body = exec_intro("Method and interpretation", "How OLBG listings, official evidence, fair lines and written High labels are kept distinct.")
    body += '''<section class="prose"><h2>1. Reverse-engineering the OLBG inventory</h2><p>The capture reads each requested OLBG sport hub and extracts the embedded event name, event URL, start timestamp and observed market labels. OLBG odds and tip percentages are not inputs to any price. The complete upcoming listing set is retained, even when no official match is found.</p>
<h2>2. Official-source crosswalks</h2><p>Official schedules and result payloads come from leagues, tours and federations. NHL abbreviations and team nicknames are checked together; NBA uses team codes and nicknames; the Danish handball row must agree with the official programme. A source table alone never confirms that a fixture exists.</p>
<h2>3. My fair lines</h2><p>Fair decimal odds are 1 ÷ probability, and fair American odds are calculated directly from probability. NHL scoring uses independently distributed goals with 70% club-rate weighting, 30% league pooling and published location adjustments. Handball uses the same family of scoring calculations with played/(played+8) pooling. Handicap and total probabilities are summed from the score distribution; every market must reconcile to 100% within rounding tolerance.</p>
<h2>4. Confidence and the price window</h2><p>Low is below 55%; Medium covers other playable leans and numerical candidates that miss a strict gate. Written High requires probability above 70%, fair American −250…+10000, an official fixture, an OLBG event, an adequate sample, recent results and full analysis. Since −233 corresponds roughly to 70%, the qualifying band is deliberately narrow. Higher-probability selections shorter than −250 are not mislabeled to fit the brief.</p>
<h2>5. Written analysis</h2><p>Each High card states its exact selection first, then uses only captured fixture, record, recent-result, scoring and player facts. Injury and lineup claims are omitted when no official report is present. Prediction prose never uses internal process vocabulary.</p>
<h2>6. Snapshot limits</h2><p>This is a timestamped research snapshot, not a promise that a market remains open. Recheck the OLBG event and official programme before acting. A blank cell means the value was not supported; a Flagged for Review link explains the gap.</p></section>'''
    (engine.SITE / "methodology.html").write_text(page("Method", body), encoding="utf-8")


def audit() -> None:
    body = exec_intro("Line-by-line evidence audit", f'{AUDIT["summary"]["payloads_ok"]}/{AUDIT["summary"]["payloads_total"]} payload hashes match. Each inventory row below exposes its source status, capture ID, unsupported fields and review links.')
    body += '<section><h2>Row provenance</h2><div class="table-wrap"><table><thead><tr><th>Row</th><th>Sport</th><th>Status</th><th>Capture</th><th>Unsupported fields / notes</th><th>Links</th></tr></thead><tbody>'
    for row in AUDIT["rows"]:
        notes = "; ".join((row.get("unverified") or []) + (row.get("flags") or []))
        body += f'<tr><td>{E(row["row_id"])}</td><td>{E(row["sport"])}</td><td>{E(row["source_status"])}</td><td>{E(row["capture_id"])}</td><td>{E(notes)}</td><td>{url(row["official_url"], "Official") if row["official_url"] else "—"}<br>{url(row["olbg_url"], "OLBG")}</td></tr>'
    body += '</tbody></table></div></section><section><h2>Candidate decisions</h2><div class="table-wrap"><table><thead><tr><th>Match</th><th>Selection</th><th>Probability</th><th>Fair American</th><th>Decision</th><th>Sources</th></tr></thead><tbody>'
    for c in CANDIDATES:
        body += f'<tr><td>{E(c["match"])}</td><td>{E(c["selection"])}</td><td>{c["fair_prob"]:.2%}</td><td>{american(c["fair_american"])}</td><td>{E(c["decision"])}</td><td>{url(c["official_url"], "Official")}<br>{url(c["olbg_url"], "OLBG")}</td></tr>'
    body += '</tbody></table></div></section>'
    (engine.SITE / "audit.html").write_text(page("Evidence audit", body), encoding="utf-8")


CSS = r'''
:root{--ink:#14213d;--muted:#61708a;--paper:#f5f7fb;--card:#fff;--line:#dfe5ef;--teal:#087f8c;--orange:#e56b2f;--green:#157347;--red:#ad3342}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.58 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.topbar{display:flex;align-items:center;gap:28px;padding:16px clamp(18px,4vw,58px);background:#101d35;color:#fff;position:sticky;top:0;z-index:5;box-shadow:0 3px 14px #0b152833}.brand{display:flex;align-items:baseline;gap:8px;color:#fff;text-decoration:none;white-space:nowrap}.brand span{font-size:23px;font-weight:850;letter-spacing:-.5px}.brand small{color:#9fc2cf}nav{display:flex;gap:4px;flex-wrap:wrap}nav a{color:#dbe7f1;text-decoration:none;padding:7px 9px;border-radius:7px;font-size:13px}nav a:hover{background:#ffffff17;color:#fff}main{max-width:1480px;margin:auto;padding:28px clamp(16px,3.5vw,48px) 60px}section{margin:24px 0}.exec{background:linear-gradient(125deg,#13294b,#135f6c);color:#fff;padding:clamp(24px,4vw,44px);border-radius:18px;margin-top:0;box-shadow:0 12px 30px #172b4718}.exec h1{font-size:clamp(28px,4vw,45px);line-height:1.12;letter-spacing:-1.2px;margin:4px 0 14px;max-width:1050px}.exec p:not(.eyebrow){max-width:1000px;color:#e2f0f2;font-size:17px}.eyebrow{text-transform:uppercase;letter-spacing:1.6px;font-size:11px;font-weight:800;margin:0;color:#66d4dc}.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.kpi{background:var(--card);padding:20px;border:1px solid var(--line);border-radius:13px}.kpi strong{display:block;font-size:32px;line-height:1.1}.kpi span{color:var(--muted);font-size:13px}.notice{border-left:5px solid var(--orange);background:#fff4e9;padding:16px 20px;border-radius:8px}.section-head{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:12px}.section-head h2,section>h2{margin:0;font-size:23px}.section-head a{color:var(--teal);font-weight:750}.pick-card{background:var(--card);border:1px solid var(--line);border-radius:15px;padding:22px;margin:15px 0;box-shadow:0 4px 16px #1b304a08}.pick-top{display:flex;gap:13px;align-items:center;flex-wrap:wrap;color:var(--muted);font-size:12px}.pick-card h2{font-size:20px;margin:10px 0}.sport-pill{background:#e5f4f4;color:#08636c;padding:4px 9px;border-radius:20px;font-weight:750}.selection{display:grid;grid-template-columns:140px 1fr;gap:2px 16px;background:#f0f7f7;border-left:4px solid var(--teal);padding:13px 16px;border-radius:8px}.selection span:first-child{grid-row:1/3;color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.8px}.selection strong{font-size:19px}.selection span:last-child{color:var(--muted)}.prediction-copy{font-size:16px;line-height:1.75;margin:18px 0}.pick-links{display:flex;gap:16px;flex-wrap:wrap;margin:12px 0}a{color:var(--teal)}details{border-top:1px solid var(--line);padding-top:10px}summary{cursor:pointer;font-weight:700}.facts{list-style:none;padding:0}.facts li{display:grid;grid-template-columns:minmax(170px,.7fr) 2fr 90px;gap:12px;border-bottom:1px solid #edf0f5;padding:9px 0}.facts li span{color:var(--muted)}.facts li strong{font-weight:550}.note{color:var(--muted);font-size:13px}.confidence{display:inline-block;padding:2px 7px;border-radius:12px;font-size:11px;font-weight:800}.confidence.high{background:#dff3e7;color:var(--green)}.confidence.medium{background:#fff0d5;color:#875d00}.confidence.low{background:#edf0f5;color:#5b6473}.table-wrap{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;background:#eaf0f6;color:#43516a;font-size:11px;text-transform:uppercase;letter-spacing:.45px}th,td{padding:11px 12px;border-bottom:1px solid #e8edf3;vertical-align:top}tbody tr:hover{background:#f7fafc}td small{display:block;color:var(--muted);margin-top:3px}td a{font-weight:650}.blank{color:#9aa4b2}.flag-link{color:var(--red);font-size:12px}.empty{padding:20px;background:#fff;border:1px dashed #b9c5d4;border-radius:10px;color:var(--muted)}.count{background:#e5ebf2;border-radius:15px;padding:3px 9px;font-size:12px}.search{width:100%;padding:13px 15px;border:1px solid #bdc9d7;border-radius:9px;margin-bottom:12px;font:inherit}code{font-size:10px;word-break:break-all}.prose{background:#fff;border:1px solid var(--line);border-radius:12px;padding:25px;max-width:1050px}.prose h2{font-size:19px;margin-top:24px}.prose h2:first-child{margin-top:0}footer{padding:24px clamp(18px,4vw,58px);background:#101d35;color:#b9c9d8;font-size:12px}@media(max-width:800px){.topbar{position:static;display:block}.brand{margin-bottom:12px}.kpis{grid-template-columns:repeat(2,1fr)}.selection{grid-template-columns:1fr}.selection span:first-child{grid-row:auto}.facts li{grid-template-columns:1fr}.facts li strong{font-size:13px}main{padding:16px 10px 40px}.exec{border-radius:12px}.table-wrap{border-radius:8px}th,td{padding:9px;min-width:90px}td:nth-child(3){min-width:210px}}
'''


def main() -> None:
    engine.SITE.mkdir(parents=True, exist_ok=True)
    (engine.SITE / "assets").mkdir(exist_ok=True)
    (engine.SITE / "assets" / "site.css").write_text(CSS.strip() + "\n", encoding="utf-8")
    index(); picks(); matches(); sports(); sport_pages(); markets(); coverage(); flagged(); sources(); methodology(); audit()
    (engine.SITE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Rendered {len(list(engine.SITE.rglob('*.html')))} HTML pages to {engine.SITE}")


if __name__ == "__main__":
    main()

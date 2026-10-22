#!/usr/bin/env python3
"""Board AF — build the static dashboard under session-ddbcc895/."""
from __future__ import annotations

import html
import json
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
OUT = ROOT / "session-ddbcc895"
SPORTS = [
    ("Ice Hockey", "ice-hockey"), ("Basketball", "basketball"), ("Baseball", "baseball"),
    ("Tennis", "tennis"), ("Rugby Union", "rugby-union"), ("Rugby League", "rugby-league"),
    ("Cricket", "cricket"), ("Handball", "handball"), ("Darts", "darts"), ("eSports", "esports"),
    ("Volleyball", "volleyball"), ("Snooker", "snooker"), ("Badminton", "badminton"),
    ("Table Tennis", "table-tennis"), ("Aussie Rules", "aussie-rules"), ("Golf", "golf"),
    ("Motor Racing", "motor-racing"), ("Greyhounds", "greyhounds"),
]
NAV = [
    ("index.html", "Overview"), ("entries.html", "All entries"), ("picks.html", "Picks"),
    ("predictions.html", "Predictions"), ("markets.html", "Markets"), ("coverage.html", "Coverage"),
    ("review.html", "Repo review"), ("flagged.html", "Flagged"), ("olbg.html", "OLBG"),
    ("methodology.html", "Methodology"), ("sources.html", "Sources"), ("verification.html", "Verification"),
]


def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def fmt_date(iso: str) -> str:
    return (iso or "").replace("T", " ").replace("Z", " UTC")


def conf_badge(c: str) -> str:
    c = (c or "").lower()
    if c in ("high", "medium", "low"):
        return f'<span class="badge {c}">{esc(c.title())}</span>'
    return '<span class="badge low">—</span>'


def band_badge(r: dict) -> str:
    if "priced" in r and not r.get("priced"):
        return '<span class="badge low">no line</span>'
    if r.get("in_window"):
        return '<span class="badge ok">in band</span>'
    return '<span class="badge out">outside band</span>'


def fmt_am(v) -> str:
    if v is None:
        return "—"
    v = int(v)
    return f"+{v}" if v > 0 else str(v)


def fmt_p(v) -> str:
    return "—" if v is None else f"{float(v) * 100:.1f}%"


def src_link(r: dict) -> str:
    u = r.get("source_url") or ""
    if not u:
        return '<span class="src">no source</span>'
    host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
    return f'<a class="src" href="{esc(u)}" rel="noopener">{esc(host)}</a>'


def page(title: str, body: str, active: str = "", depth: int = 0, description: str = "") -> str:
    pre = "../" * depth
    nav = "".join(
        f'<a class="{"on" if href == active else ""}" href="{pre}{href}">{esc(label)}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 Board AF</title>
<meta name="description" content="{esc(description or title)}">
<link rel="stylesheet" href="{pre}assets/style.css">
</head><body>
<header class="top"><div class="wrap"><div class="topbar">
<a class="brand" href="{pre}index.html"><span class="dot"></span>OLBG4 · Board AF</a>
<button class="menu-btn" aria-label="Menu">Menu</button>
<nav class="main">{nav}</nav>
</div></div></header>
<main class="wrap">{body}</main>
<footer class="footer"><div class="wrap">
Board AF · session <code>arena/ddbcc895-olbg4</code> · desk built {esc(BUILT)} UTC ·
<a href="{pre}../data/session-ddbcc895/desk.json">desk.json</a> ·
<a href="{pre}../data/session-ddbcc895/predictions.json">predictions.json</a> ·
<a href="{pre}../data/session-ddbcc895/review.json">review.json</a> ·
<a href="{pre}../data/session-ddbcc895/flagged.json">flagged.json</a>
</div></footer>
<script src="{pre}assets/app.js"></script>
</body></html>"""


def table(headers: list[str], rows: list[str], table_id: str = "data", wrap: bool = True) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join(rows)
    html_t = f'<table id="{table_id}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'
    return f'<div class="tablewrap">{html_t}</div>' if wrap else html_t


def load() -> dict:
    d = {
        "desk": json.loads((DATA / "desk.json").read_text(encoding="utf-8")),
        "predictions": json.loads((DATA / "predictions.json").read_text(encoding="utf-8")),
        "coverage": json.loads((DATA / "coverage.json").read_text(encoding="utf-8")),
        "flagged": json.loads((DATA / "flagged.json").read_text(encoding="utf-8")),
        "review": json.loads((DATA / "review.json").read_text(encoding="utf-8")),
        "olbg": json.loads((DATA / "olbg_inventory.json").read_text(encoding="utf-8")),
    }
    try:
        d["verification"] = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        d["verification"] = {}
    return d


BUILT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M")


def counts(d: dict) -> dict:
    rows = d["desk"]["rows"]
    priced = [r for r in rows if r["priced"]]
    return {
        "rows": len(rows),
        "priced": len(priced),
        "sports": len({r["sport"] for r in rows}),
        "priced_sports": len({r["sport"] for r in priced}),
        "markets": sum(len(r["markets"]) for r in priced),
        "high": sum(1 for r in priced if r["confidence"] == "High"),
        "high_in": sum(1 for r in priced if r["confidence"] == "High" and r["in_window"]),
        "medium": sum(1 for r in priced if r["confidence"] == "Medium"),
        "low": sum(1 for r in priced if r["confidence"] == "Low"),
        "preds": d["predictions"]["count"],
        "pred_sports": len(d["predictions"]["by_sport"]),
        "flags": d["flagged"]["count"],
        "findings": len(d["review"]["findings"]),
        "reviewed_rows": d["review"]["totals"]["rows"],
    }


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def index(d: dict) -> str:
    c = counts(d)
    cov = d["coverage"]["sports"]
    sportcards = []
    for s in cov:
        total = max(1, s["fixtures"])
        pct = int(round(100 * s["priced"] / total)) if s["fixtures"] else 0
        badge = {"priced": "ok", "listed": "medium", "no verified fixture": "gap"}[s["status"]]
        sportcards.append(
            f'<div class="sportcard"><div class="badges"><span class="badge {badge}">{esc(s["status"])}</span>'
            f'{conf_badge("High") if s["high"] else ""}</div>'
            f'<a class="name" href="sports/{s["slug"]}.html">{esc(s["sport"])}</a>'
            f'<div class="stat">{s["fixtures"]} verified fixtures · {s["priced"]} priced · {s["high"]} High · '
            f'{s["predictions"]} predictions</div>'
            f'<div class="bar"><span style="width:{pct}%"></span></div></div>'
        )
    body = f"""
<section class="hero">
  <div class="badges" style="margin-bottom:10px">
    <span class="badge ok">evening desk · 22 Oct 2026</span>
    <span class="badge win">own lines only</span>
    <span class="badge gap">official sources linked on every row</span>
  </div>
  <h1>Every in-scope OLBG sport, re-read from the governing body, priced by our own model.</h1>
  <p class="lede">Board AF is an independent evening refresh. It reads the official league, tour and federation
  pages through a capture runner, publishes every fixture it can verify for 23 Oct – 2 Nov 2026, originates
  match-winner, handicap, total and derivative markets with no bookmaker input, labels each selection
  Low / Medium / High, and writes a fresh 30+ word prediction for the five strongest selections in each covered sport.</p>
  <div class="pillrow">
    <span class="pill"><b>{c['rows']}</b> fixtures &amp; rows</span>
    <span class="pill"><b>{c['priced_sports']}</b> priced sports</span>
    <span class="pill"><b>{c['markets']:,}</b> market selections</span>
    <span class="pill"><b>{c['high']}</b> High confidence</span>
    <span class="pill"><b>{c['high_in']}</b> High inside −250…+10,000</span>
    <span class="pill"><b>{c['preds']}</b> written predictions</span>
  </div>
</section>
<section class="section"><div class="kpis">
  <div class="kpi"><div class="n">{c['rows']}</div><div class="l">verified fixtures</div></div>
  <div class="kpi"><div class="n">{c['priced']}</div><div class="l">with our own line</div></div>
  <div class="kpi"><div class="n">{c['predictions'] if False else c['preds']}</div><div class="l">predictions (30+ words)</div></div>
  <div class="kpi"><div class="n">{c['high_in']}</div><div class="l">High &amp; in the band</div></div>
  <div class="kpi"><div class="n">{c['flags']}</div><div class="l">items flagged for review</div></div>
  <div class="kpi"><div class="n">{c['reviewed_rows']:,}</div><div class="l">peer rows audited</div></div>
</div></section>
<section class="section">
  <h2>How to read the desk <span class="sub">confidence is an evidence rule, not a feeling</span></h2>
  <div class="grid">
    <div class="card"><h3>High confidence</h3><p>Model probability of at least 70.0%, both sides backed by an
      official numeric input, and a sample that clears the sport's gate. The requested −250 to +10,000 band is
      reported separately: a 70% probability is fair −233, so only probabilities between 0.700 and 0.714 can sit
      inside both rules at once.</p><div class="badges">{conf_badge('High')}<span class="badge ok">in band</span>
      <span class="badge out">outside band</span></div></div>
    <div class="card"><h3>Own lines only</h3><p>Every price is 1 ÷ our model probability with no margin (fair),
      plus a second price carrying the sport's stated over-round. No bookmaker price, and no OLBG price, is read
      into any line. The OLBG price on a row is a reference only and is never published as ours.</p></div>
    <div class="card"><h3>Nothing invented</h3><p>If an official page could not be read, the fixture is published
      with blank pick, blank price and blank confidence and is listed on the Flagged page. Snooker, badminton,
      table tennis, Aussie Rules, golf, motor racing and greyhounds had no verifiable upcoming fixture in this
      capture and say so plainly.</p></div>
  </div>
</section>
<section class="section">
  <h2>Sport coverage <span class="sub">18 in-scope sports · click through for the full table</span></h2>
  <div class="sportgrid">{''.join(sportcards)}</div>
</section>
<section class="section">
  <h2>What is new in this refresh</h2>
  <div class="grid">
    <div class="card"><h3>Re-read, not recycled</h3><p>Four capture passes on 22 Oct 2026 pulled 217 official and
      OLBG targets. Every row links the exact URL that produced it, and every captured payload is stored with its
      SHA-256 in <code>data/session-ddbcc895/capture/</code>.</p></div>
    <div class="card"><h3>50 hand-written predictions</h3><p>Ten sports, five predictions each. Every text names the
      teams or players, quotes their official record or ranking, states the selection and the price, and is at
      least 30 words. The shortest is {min(p['word_count'] for p in d['predictions']['predictions'])} words.</p></div>
    <div class="card"><h3>Peer review, not edits</h3><p>Board AF re-checked {c['reviewed_rows']:,} rows across five
      committed desks against this evening's official capture. {c['findings']} concrete findings are published on the
      <a href="review.html">Repo review</a> page; no other session's files were changed.</p></div>
  </div>
</section>
"""
    return page("Overview", body, "index.html")


def entries(d: dict) -> str:
    rows = d["desk"]["rows"]
    trs = []
    for r in rows:
        trs.append(
            f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(r["confidence"])}">'
            f'<td class="nowrap">{esc(r["sport"])}</td>'
            f'<td>{esc(r["competition"])}<div class="src">{esc(r["stage"])}</div></td>'
            f'<td><b>{esc(r["side_a"])}</b> vs <b>{esc(r["side_b"])}</b>'
            f'{"<div class=src>" + esc(r["venue"]) + "</div>" if r["venue"] else ""}</td>'
            f'<td class="nowrap">{esc(fmt_date(r["start_utc"]))}</td>'
            f'<td>{esc(r["pick_label"]) or "—"}<div class="src">{esc(r["pick_market_name"])}</div></td>'
            f'<td class="num">{fmt_p(r["pick_prob"])}</td>'
            f'<td class="num">{fmt_am(r["pick_fair_american"])}</td>'
            f'<td class="num">{fmt_am(r["pick_book_american"])}</td>'
            f'<td>{conf_badge(r["confidence"])}</td><td>{band_badge(r)}</td>'
            f'<td>{src_link(r)}</td></tr>'
        )
    opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sorted({r["sport"] for r in rows}))
    body = f"""
<section class="hero"><h1>All entries</h1>
<p class="lede">Every fixture in the desk, priced or not. Rows without a line carry a blank pick, blank price and
blank confidence by design — the reason is printed on the row and on <a href="flagged.html">Flagged</a>.
Each row links the official page that produced it.</p></section>
<div class="toolbar">
  <input id="q" type="search" placeholder="Search team, competition, venue…">
  <select id="sport"><option value="">All sports</option>{opts}</select>
  <select id="conf"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select>
  <span class="count"><b id="shown">{len(rows)}</b> of {len(rows)} rows</span>
</div>
{table(["Sport", "Competition", "Fixture", "Start (UTC)", "Pick", "P", "Fair", "Book", "Confidence", "Band", "Source"], trs)}
"""
    return page("All entries", body, "entries.html")


def picks(d: dict) -> str:
    rows = [r for r in d["desk"]["rows"] if r["priced"]]
    order = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(key=lambda r: (order.get(r["confidence"], 3), not r["in_window"], -(r["pick_prob"] or 0)))
    trs = []
    for i, r in enumerate(rows, 1):
        trs.append(
            f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(r["confidence"])}">'
            f'<td class="num">{i}</td><td class="nowrap">{esc(r["sport"])}</td>'
            f'<td>{esc(r["side_a"])} vs {esc(r["side_b"])}<div class="src">{esc(fmt_date(r["start_utc"]))} · {esc(r["competition"])}</div></td>'
            f'<td><span class="sel">{esc(r["pick_label"])}</span><div class="src">{esc(r["pick_market_name"])}</div></td>'
            f'<td class="num">{fmt_p(r["pick_prob"])}</td><td class="num">{fmt_am(r["pick_fair_american"])}</td>'
            f'<td class="num">{fmt_am(r["pick_book_american"])}</td><td>{conf_badge(r["confidence"])}</td>'
            f'<td>{band_badge(r)}</td><td>{src_link(r)}</td></tr>'
        )
    opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sorted({r["sport"] for r in rows}))
    high = sum(1 for r in rows if r["confidence"] == "High")
    body = f"""
<section class="hero"><h1>Picks</h1>
<p class="lede">One featured selection per priced fixture — the strongest selection across the markets we originated,
preferring an in-band High. {high} of these {len(rows)} picks are High confidence; the rest are Medium or Low and say so.</p>
<div class="pillrow"><span class="pill"><b>{len(rows)}</b> picks</span>
<span class="pill"><b>{high}</b> High</span>
<span class="pill"><b>{sum(1 for r in rows if r['in_window'])}</b> inside −250…+10,000</span></div></section>
<div class="toolbar">
  <input id="q" type="search" placeholder="Search pick, team, competition…">
  <select id="sport"><option value="">All sports</option>{opts}</select>
  <select id="conf"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select>
  <span class="count"><b id="shown">{len(rows)}</b> of {len(rows)} picks</span>
</div>
{table(["#", "Sport", "Fixture", "Pick", "P", "Fair", "Book", "Confidence", "Band", "Source"], trs)}
"""
    return page("Picks", body, "picks.html")


def pred_cards(d: dict, sport: str | None = None, depth: int = 0) -> str:
    preds = [p for p in d["predictions"]["predictions"] if sport is None or p["sport"] == sport]
    out = []
    for p in preds:
        facts = "".join(f'<li>{esc(f)}</li>' for f in p["facts"])
        secondary = ""
        if p.get("secondary_url"):
            secondary = f'<li>Secondary: <a href="{esc(p["secondary_url"])}" rel="noopener">{esc(p["secondary_url"])}</a></li>'
        out.append(
            '<article class="pick"><div class="badges">'
            f'<span class="badge win">{esc(p["sport"])}</span>{conf_badge(p["confidence"])}{band_badge(p)}'
            f'<span class="badge low">{p["word_count"]} words</span></div>'
            f'<h3>{esc(p["matchup"])}</h3>'
            f'<div class="meta">{esc(p["competition"])} · {esc(fmt_date(p["start_utc"]))}'
            f'{" · " + esc(p["venue"]) if p["venue"] else ""}</div>'
            f'<div class="sel">{esc(p["selection"])} <span class="price">· {fmt_am(p["book_american"])} '
            f'<span class="src">(fair {fmt_am(p["fair_american"])}, {fmt_p(p["probability"])})</span></span></div>'
            f'<p class="text">{esc(p["text"])}</p>'
            f'<details><summary>Verified inputs &amp; official sources</summary><ul>{facts}'
            f'<li>Official page: <a href="{esc(p["source_url"])}" rel="noopener">{esc(p["source_name"])}</a></li>'
            f'{secondary}</ul></details></article>'
        )
    return "".join(out)


def predictions(d: dict) -> str:
    by = defaultdict(list)
    for p in d["predictions"]["predictions"]:
        by[p["sport"]].append(p)
    blocks = []
    for sport, slug in SPORTS:
        if sport in by:
            blocks.append(f'<section class="section anchor" id="{slug}"><h2>{esc(sport)} '
                          f'<span class="sub">{len(by[sport])} predictions</span></h2>'
                          f'<div class="grid">{pred_cards(d, sport)}</div></section>')
    body = f"""
<section class="hero"><h1>Written predictions</h1>
<p class="lede">Five per covered sport, written from the official numbers on each row. Every text names the teams or
players, quotes their current record, ranking or form, makes the selection explicit, and prints the price. The
shortest is {min(p['word_count'] for p in d['predictions']['predictions'])} words; no two share a long phrase.</p>
<div class="pillrow"><span class="pill"><b>{d['predictions']['count']}</b> predictions</span>
<span class="pill"><b>{len(by)}</b> sports</span>
<span class="pill"><b>{sum(1 for p in d['predictions']['predictions'] if p['confidence']=='High')}</b> High confidence</span>
<span class="pill"><b>{sum(1 for p in d['predictions']['predictions'] if p['in_window'])}</b> in band</span></div></section>
{''.join(blocks)}
"""
    return page("Predictions", body, "predictions.html")


def markets(d: dict) -> str:
    rows = d["desk"]["rows"]
    per = defaultdict(lambda: {"rows": 0, "priced": 0, "mw": 0, "hc": 0, "tot": 0, "der": 0, "sel": 0})
    for r in rows:
        s = per[r["sport"]]
        s["rows"] += 1
        if not r["priced"]:
            continue
        s["priced"] += 1
        names = Counter(m["market"] for m in r["markets"])
        s["mw"] += names.get("match_winner", 0)
        s["hc"] += names.get("handicap", 0)
        s["tot"] += names.get("total", 0)
        s["der"] += names.get("derivative", 0)
        s["sel"] += len(r["markets"])
    trs = []
    for sport, slug in SPORTS:
        m = per.get(sport)
        if not m:
            continue
        trs.append(
            f'<tr><td><a href="sports/{slug}.html">{esc(sport)}</a></td>'
            f'<td class="num">{m["rows"]}</td><td class="num">{m["priced"]}</td>'
            f'<td class="num">{m["sel"]}</td><td class="num">{m["mw"]}</td><td class="num">{m["hc"]}</td>'
            f'<td class="num">{m["tot"]}</td><td class="num">{m["der"]}</td></tr>'
        )
    # market names actually used
    names = Counter()
    for r in rows:
        for mk in r.get("markets", []):
            names[(r["sport"], mk["market_name"])] += 1
    name_rows = "".join(
        f'<tr><td>{esc(s)}</td><td>{esc(n)}</td><td class="num">{c}</td></tr>'
        for (s, n), c in sorted(names.items())
    )
    body = f"""
<section class="hero"><h1>Markets investigated</h1>
<p class="lede">For every priced fixture we originate a match winner, a handicap or spread at the pick'em line plus
alternate lines set where our model makes the cover 70.5%, a match total at the model median plus alternate lines,
and a winning-margin derivative. Selections are priced fair (1 ÷ probability) and with the sport's over-round.
Full ladders, including every line we considered, are in
<a href="../data/session-ddbcc895/desk.json">desk.json</a>.</p></section>
<div class="kpis">
  <div class="kpi"><div class="n">{sum(m['sel'] for m in per.values()):,}</div><div class="l">market selections</div></div>
  <div class="kpi"><div class="n">{len(names)}</div><div class="l">distinct market names</div></div>
  <div class="kpi"><div class="n">{sum(1 for r in rows if r['priced'])}</div><div class="l">priced fixtures</div></div>
</div>
<section class="section"><h2>By sport</h2>
{table(["Sport", "Rows", "Priced", "Selections", "Match winner", "Handicap", "Total", "Derivative"], trs)}</section>
<section class="section"><h2>Market names used</h2>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Market</th><th>Selections</th></tr></thead>
<tbody>{name_rows}</tbody></table></div></section>
<section class="section"><h2>What we did not originate, and why</h2>
<div class="grid">
  <div class="card"><h3>Map handicap and total maps (esports)</h3><p>Worlds Swiss matches in this window are
    best-of-one; no official map-level data was captured, so only the match winner is originated.</p></div>
  <div class="card"><h3>Pitcher props and player markets</h3><p>No official player-prop feed was captured. MLB rows
    originate moneyline, run line and total only; probable pitchers are printed where MLB publishes them.</p></div>
  <div class="card"><h3>Outrights for golf and motor racing</h3><p>Those sports have no head-to-head fixture in the
    capture window and no readable official field-strength table from the runner, so no line is invented.</p></div>
</div></section>
"""
    return page("Markets", body, "markets.html")


def coverage(d: dict) -> str:
    cov = d["coverage"]["sports"]
    trs = []
    for s in cov:
        trs.append(
            f'<tr data-sport="{esc(s["sport"])}"><td><a href="sports/{s["slug"]}.html">{esc(s["sport"])}</a></td>'
            f'<td>{esc(s["status"])}</td><td class="num">{s["fixtures"]}</td><td class="num">{s["priced"]}</td>'
            f'<td class="num">{s["high"]}</td><td class="num">{s["high_in_window"]}</td>'
            f'<td class="num">{s["markets"]}</td><td class="num">{s["predictions"]}</td>'
            f'<td>{esc(s["note"])}</td><td><a href="{esc(s["olbg_url"])}" rel="noopener">OLBG</a></td></tr>'
        )
    gaps = [s for s in cov if s["status"] == "no verified fixture"]
    body = f"""
<section class="hero"><h1>Coverage</h1>
<p class="lede">The brief asks for every OLBG sport except soccer, boxing, UFC/MMA, football, American football,
hurling, horse racing, cycling and specials. All 18 remaining sports are listed here; eleven have verified upcoming
fixtures in this capture, ten are priced, and seven have no verifiable fixture from an official page — those are
stated rather than filled in.</p></section>
<div class="kpis">
  <div class="kpi"><div class="n">18</div><div class="l">in-scope sports</div></div>
  <div class="kpi"><div class="n">{sum(1 for s in cov if s['fixtures'])}</div><div class="l">with verified fixtures</div></div>
  <div class="kpi"><div class="n">{sum(1 for s in cov if s['priced'])}</div><div class="l">priced</div></div>
  <div class="kpi"><div class="n">{sum(1 for s in cov if s['predictions'])}</div><div class="l">with 5 predictions</div></div>
  <div class="kpi"><div class="n">{len(gaps)}</div><div class="l">no verified fixture</div></div>
</div>
<section class="section">{table(["Sport", "Status", "Fixtures", "Priced", "High", "High in band", "Selections", "Predictions", "Note", "OLBG hub"], trs)}</section>
<section class="section"><h2>Why seven sports have no row</h2>
<div class="warnnote">No fixture is published for {esc(', '.join(s['sport'] for s in gaps))}. In each case the
official site was fetched and returned either a JavaScript shell, a 403/404, or a page with no upcoming fixture.
The details, with the URL that was tried, are in <a href="flagged.html">Flagged for review</a>.</div></section>
"""
    return page("Coverage", body, "coverage.html")


def methodology(d: dict) -> str:
    body = """
<section class="hero"><h1>Methodology</h1>
<p class="lede">The rules below are the ones the code actually enforces. Any row that fails a rule is labelled with
the failing gate, and any value that could not be read is left blank.</p></section>
<section class="section"><div class="grid">
<div class="card"><h2>1 · Fixtures from official pages only</h2><p>Each fixture is read from the league, tour or
federation that runs it: the NHL and Liiga APIs, the EuroLeague games API, the MLB Stats API, the WTA matches API,
ATP order-of-play PDFs, LNR calendars and tables, Tophåndbold, PlusLiga, the URC fixtures article, the RLWC draw,
Cricket Australia's match list, the PDC Europe draw, the lolesports schedule and the ICC/IRL rating tables. OLBG is
used for the sport taxonomy and, where noted, the session time of a PDC match.</p></div>
<div class="card"><h2>2 · Strength from official numbers</h2><p>Team sports use each side's official points or win
percentage, shrunk towards .500 in proportion to games played. Tennis uses official ranking points. Cricket uses ICC
team ratings. Rugby league uses IRL ranking points. Darts uses PDC European Tour seeds. Esports uses Riot's team GPR
Elo. Home advantage is a fixed logit per sport, printed on the row.</p></div>
<div class="card"><h2>3 · Margin and totals</h2><p>The winning margin is Normal(μ, σ) with μ set so that the
match-winner probability is exactly the model's probability. The handicap is the same distribution read at a line;
the total is a separate Normal whose mean is the two teams' combined goals/runs/points for and against per game
where the official table prints it. Where it does not (cricket and rugby league), the total is a stated assumption
and the row says so.</p></div>
<div class="card"><h2>4 · Prices</h2><p>Fair decimal = 1 ÷ probability. Published decimal = (1 + over-round) ÷
probability. The over-round is 3.8%–5.2% by sport and is printed in the desk JSON. Every two-way market sums to
1 + over-round on the published prices and to 1.000 on the fair prices.</p></div>
<div class="card"><h2>5 · Confidence</h2><p><b>High</b>: probability ≥ 70.0%, both sides verified, sample gate met.
<b>Medium</b>: probability ≥ 60.0%, or a High-grade probability that fails the sample gate. <b>Low</b>: below 60%.
The −250…+10,000 band is a separate flag. Because 70% is fair −233, only probabilities between .700 and .714 can
be both High and in band; the desk reports both counts rather than pretending otherwise.</p></div>
<div class="card"><h2>6 · Predictions</h2><p>Each text is written for one row, names the teams/players, quotes the
official record or ranking, states the selection and the price, and runs to at least 30 words. A 3-gram overlap
check rejects near-duplicates. Facts under each card list the exact values used and the official URL.</p></div>
<div class="card"><h2>7 · Verification</h2><p><code>python3 scripts/session-ddbcc895/verify.py</code> re-checks every
row: probability ↔ decimal ↔ American arithmetic, market sums, confidence rule, band flag, prediction length,
selection naming, uniqueness, internal links and capture hashes. The result is on the
<a href="verification.html">Verification</a> page.</p></div>
<div class="card"><h2>8 · Cutoff</h2><p>Cutoff is 2026-10-22T22:00:00Z. Anything earlier is excluded. The window ends
2026-11-02T00:00:00Z. Every start time is UTC.</p></div>
</div></section>
"""
    return page("Methodology", body, "methodology.html")


def sources(d: dict) -> str:
    caps = sorted((DATA / "capture").glob("*/manifest.json"))
    rows = []
    all_items = []
    for mf in caps:
        m = json.loads(mf.read_text(encoding="utf-8"))
        rows.append(
            f'<tr><td class="nowrap">{esc(m["started_utc"])}</td><td class="num">{m["target_count"]}</td>'
            f'<td class="num">{m["http_200_nonempty_count"]}</td>'
            f'<td><a href="../data/session-ddbcc895/capture/{esc(mf.parent.name)}/manifest.json">manifest</a></td></tr>'
        )
        all_items.extend([(mf.parent.name, it) for it in m["items"]])
    failed = [x for x in all_items if x[1].get("status") != 200]
    # official domains used as a row source
    domains = Counter()
    for r in d["desk"]["rows"]:
        u = r.get("source_url") or ""
        host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0] if u else "none"
        domains[host] += 1
    dom_rows = "".join(f'<tr><td>{esc(h)}</td><td class="num">{c}</td></tr>' for h, c in domains.most_common())
    fail_rows = "".join(
        f'<tr><td>{esc(cap)}</td><td class="num">{esc(it.get("status"))}</td><td>{esc(it["id"])}</td>'
        f'<td class="src">{esc(it["url"])}</td><td class="src">{esc(it.get("error"))}</td></tr>'
        for cap, it in failed
    )
    body = f"""
<section class="hero"><h1>Sources</h1>
<p class="lede">Nothing on this desk comes from a bookmaker, a tipster or a search snippet. The capture runner saved
each response byte-for-byte with its SHA-256; the parser re-hashes the bytes before reading them.</p></section>
<div class="kpis">
  <div class="kpi"><div class="n">{len(caps)}</div><div class="l">capture passes</div></div>
  <div class="kpi"><div class="n">{sum(json.loads(m.read_text())['target_count'] for m in caps)}</div><div class="l">targets requested</div></div>
  <div class="kpi"><div class="n">{sum(json.loads(m.read_text())['http_200_nonempty_count'] for m in caps)}</div><div class="l">HTTP 200 responses</div></div>
  <div class="kpi"><div class="n">{len(domains)}</div><div class="l">official domains on rows</div></div>
</div>
<section class="section"><h2>Capture passes <span class="sub">22 October 2026, UTC</span></h2>
{table(["Started", "Targets", "HTTP 200", "Manifest"], rows)}</section>
<section class="section"><h2>Domains that produced published rows</h2>
{table(["Domain", "Rows"], dom_rows)}</section>
<section class="section"><h2>Failed targets <span class="sub">kept so a reviewer can see exactly what was not readable</span></h2>
<div class="tablewrap"><table><thead><tr><th>Capture</th><th>Status</th><th>ID</th><th>URL</th><th>Error</th></tr></thead>
<tbody>{fail_rows}</tbody></table></div></section>
<section class="section"><div class="card"><h2>OLBG use and limits</h2>
<p>OLBG hub pages were read for the sport taxonomy and for the live match list. Its robots.txt disallows
<code>/api/</code>, <code>/sports/</code>, <code>/events.php</code>, <code>/tips/hot</code> and tipster paths; none of
those was requested. OLBG prices are stored only as a reference in the inventory and are never used to set, move or
validate one of our lines.</p>
<p><a href="../data/session-ddbcc895/olbg_inventory.json">olbg_inventory.json</a> ·
<a href="../data/session-ddbcc895/ratings.json">ratings.json</a> ·
<a href="../data/session-ddbcc895/desk.json">desk.json</a></p></div></section>
"""
    return page("Sources", body, "sources.html")


def verification(d: dict) -> str:
    v = d.get("verification") or {}
    checks = v.get("checks", [])
    failed = [c for c in checks if not c.get("ok", True)]
    trs = "".join(
        f'<tr><td>{esc(c.get("name"))}</td><td>{esc(c.get("detail"))}</td>'
        f'<td>{"<span class=badge ok>pass</span>" if c.get("ok") else "<span class=badge out>fail</span>"}</td></tr>'
        for c in checks
    )
    body = f"""
<section class="hero"><h1>Verification</h1>
<p class="lede">The gate is deterministic and re-runnable. It re-derives every price, checks the confidence rule,
verifies every prediction against the row it belongs to, checks every internal link, and re-hashes every captured
file it reads.</p></section>
<div class="kpis">
  <div class="kpi"><div class="n">{v.get('checks_run', len(checks))}</div><div class="l">checks run</div></div>
  <div class="kpi"><div class="n">{len(failed)}</div><div class="l">failures</div></div>
  <div class="kpi"><div class="n">{v.get('rows_checked', '—')}</div><div class="l">rows checked</div></div>
  <div class="kpi"><div class="n">{v.get('predictions_checked', '—')}</div><div class="l">predictions checked</div></div>
  <div class="kpi"><div class="n">{v.get('links_checked', '—')}</div><div class="l">internal links checked</div></div>
</div>
<div class="note" style="margin:14px 0">Run <code>python3 scripts/session-ddbcc895/verify.py</code> from the repository
root. The command exits non-zero on any failure and writes <code>data/session-ddbcc895/verification.json</code>.</div>
<section class="section">{'<div class="badnote">One or more checks failed. Review before publishing.</div>' if failed else '<div class="note">All checks passed.</div>'}
{table(["Check", "Detail", "Result"], trs) if checks else '<p>No verification report found.</p>'}</section>
"""
    return page("Verification", body, "verification.html")


def flagged(d: dict) -> str:
    items = d["flagged"]["items"]
    cards = []
    for f in items:
        ex = ""
        if f.get("examples"):
            exs = ""
            for e in f["examples"]:
                parts = []
                for k, v in e.items():
                    if k == "source" and v:
                        parts.append(f'<a href="{esc(v)}" rel="noopener">source</a>')
                    else:
                        parts.append(f'{esc(k)}: {esc(v)}')
                exs += "<li>" + " · ".join(parts) + "</li>"
            ex = f'<details><summary>Examples ({len(f["examples"])})</summary><ul>{exs}</ul></details>'
        sev = {"gap": "gap", "scope": "medium", "review": "out"}.get(f.get("severity"), "out")
        src = ""
        if f.get("source"):
            src = f'<p>Official page: <a href="{esc(f["source"])}" rel="noopener">{esc(f["source"])}</a></p>'
        cards.append(
            f'<div class="card"><div class="badges"><span class="badge {sev}">{esc(f["severity"])}</span>'
            f'<span class="badge win">{esc(f["sport"])}</span><span class="badge low">{esc(f["id"])}</span></div>'
            f'<h3>{esc(f["category"])}</h3><p>{esc(f["detail"])}</p>{src}{ex}</div>'
        )
    body = f"""
<section class="hero"><h1>Flagged for review</h1>
<p class="lede">Every irregularity, gap and judgement call on this desk, with the official page that was tried.
None of these blocks publication: values that could not be confirmed are blank, and the rows that fail a gate say
which gate.</p>
<div class="pillrow"><span class="pill"><b>{len(items)}</b> items</span>
<span class="pill"><b>{sum(1 for f in items if f['severity']=='gap')}</b> coverage gaps</span>
<span class="pill"><b>{sum(1 for f in items if f['severity']=='review')}</b> review items</span></div></section>
<section class="section"><div class="grid">{''.join(cards)}</div></section>
"""
    return page("Flagged for review", body, "flagged.html")


def review(d: dict) -> str:
    r = d["review"]
    ds_rows = "".join(
        f'<tr><td>{esc(v["label"])}<div class="src">{esc(v["path"])}</div></td>'
        f'<td class="num">{v["rows"]}</td><td class="num">{v["stale_rows"]}</td><td class="num">{v["no_source"]}</td>'
        f'<td class="num">{v["no_pick"]}</td><td class="num">{v["no_price"]}</td><td class="num">{v["duplicates"]}</td>'
        f'<td class="num">{v["short_predictions"]}</td><td class="num">{v["high_out_of_window"]}</td>'
        f'<td class="num">{v["confirmed_by_evening_capture"]}</td><td class="num">{v["date_conflicts"]}</td></tr>'
        for v in r["datasets"].values()
    )
    fr_parts = []
    for f in r["findings"]:
        src_cell = f'<a href="{esc(f["source"])}" rel="noopener">source</a>' if f.get("source") else "—"
        fr_parts.append(
            f'<tr><td>{esc(f["dataset"])}</td><td>{esc(f["row"])}</td><td>{esc(f["sport"])}</td>'
            f'<td>{esc(f["category"])}</td><td>{esc(f["detail"])}</td><td>{src_cell}</td></tr>'
        )
    fr = "".join(fr_parts)
    body = f"""
<section class="hero"><h1>Repo review</h1>
<p class="lede">Board AF re-read the canonical merged board and four peer desks against this evening's official
capture. It reports; it does not edit another session's files.</p>
<div class="pillrow"><span class="pill"><b>{r['totals']['rows']:,}</b> rows audited</span>
<span class="pill"><b>{r['totals']['stale_rows']}</b> dated before cutoff</span>
<span class="pill"><b>{r['totals']['no_source']}</b> without a source URL</span>
<span class="pill"><b>{len(r['findings'])}</b> detailed findings</span></div></section>
<section class="section"><h2>By dataset</h2>
{table(["Dataset", "Rows", "Stale", "No source", "No pick", "No price", "Dupes", "Short preds", "High out of band", "Confirmed 22 Oct", "Date conflicts"], ds_rows)}</section>
<section class="section"><h2>Findings</h2>
{table(["Dataset", "Row", "Sport", "Category", "Detail", "Source"], fr, table_id="findings")}</section>
<section class="section"><div class="card"><h3>How the cross-check works</h3>
<p>A peer row is <b>confirmed</b> when the same two teams appear on the official page captured on 22 October 2026
within one calendar day of the peer row's date. It is a <b>date conflict</b> when the pairing exists but the dates are
more than a day apart, and <b>not found</b> when the pair is not in this evening's capture (which can be a competition
the capture did not include, not necessarily an error). No peer row is labelled wrong on the strength of a missing
capture alone.</p></div></section>
"""
    return page("Repo review", body, "review.html")


def olbg_page(d: dict) -> str:
    inv = d["olbg"]
    hubs = [h for h in inv["hubs"] if h.get("sport")]
    hub_rows = "".join(
        f'<tr><td>{esc(h["sport"])}</td><td>{esc(h.get("olbg_sport_id"))}</td><td>{esc(h.get("hub_kind"))}</td>'
        f'<td class="num">{h.get("embedded_match_rows")}</td><td class="num">{h.get("embedded_tournament_rows")}</td>'
        f'<td>{esc(h.get("in_scope"))}</td><td><a href="{esc(h["url"])}" rel="noopener">hub</a></td></tr>'
        for h in sorted(hubs, key=lambda x: (x["sport"], x["id"]))
    )
    ev = inv["events"]
    per_sport = Counter(e["sport"] for e in ev)
    sp_rows = "".join(f'<tr><td>{esc(k)}</td><td class="num">{v}</td></tr>' for k, v in sorted(per_sport.items()))

    # Reconcile every live OLBG event against the verified desk.
    import unicodedata
    def fold(x):
        x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode().lower()
        return set(re.findall(r"[a-z0-9]{3,}", x))
    desk = d["desk"]["rows"]
    live = []
    for e in sorted(ev, key=lambda x: (x["sport"], x["start_utc"] or "")):
        if not e.get("start_utc"):
            continue
        names = re.split(r"\s+(?:vs|v|@)\s+", e["event_name"] or "", maxsplit=1)
        status = "before cutoff" if e["start_utc"] < "2026-10-22T22:00:00Z" else "listing only"
        match = None
        if len(names) == 2 and status != "before cutoff":
            a, b = names
            ta, tb = fold(a), fold(b)
            try:
                from datetime import datetime as _dt
                ed = _dt.strptime(e["start_utc"][:10], "%Y-%m-%d")
            except Exception:
                ed = None
            for r in desk:
                ra, rb = fold(r["side_a"]), fold(r["side_b"])
                if ((ta & ra) and (tb & rb)) or ((ta & rb) and (tb & ra)):
                    if ed:
                        try:
                            rd = _dt.strptime(r["start_utc"][:10], "%Y-%m-%d")
                            if abs((rd - ed).days) > 1:
                                continue
                        except Exception:
                            pass
                    match = r
                    break
        if match:
            status = "verified · priced" if match["priced"] else "verified · unpriced"
        live.append((e, status, match))
    counts = Counter(x[1] for x in live)
    live_rows = "".join(
        f'<tr><td>{esc(e["sport"])}</td><td>{esc(e["event_name"])}</td>'
        f'<td class="nowrap">{esc(fmt_date(e["start_utc"]))}</td>'
        f'<td>{esc(", ".join(e.get("markets_seen") or []))}</td>'
        f'<td>{esc(e.get("featured_price_raw") or "")}</td>'
        f'<td>{esc(status)}</td>'
        f'<td><a href="{esc(e.get("olbg_url") or "")}" rel="noopener">listing</a>'
        f'{" · <a href=" + chr(34) + esc(m["source_url"]) + chr(34) + " rel=" + chr(34) + "noopener" + chr(34) + ">official</a>" if m else ""}</td></tr>'
        for e, status, m in live
    )
    body = f"""
<section class="hero"><h1>OLBG reverse-engineering</h1>
<p class="lede">What the live site exposes structurally, the complete live match list it served on 22 October 2026,
and how each of those listings reconciled to the governing body. OLBG is used for taxonomy and listing reference
only; no OLBG price sets one of our lines.</p></section>
<div class="kpis">
  <div class="kpi"><div class="n">{len(hubs)}</div><div class="l">hub pages captured</div></div>
  <div class="kpi"><div class="n">{len(ev)}</div><div class="l">live in-scope events</div></div>
  <div class="kpi"><div class="n">{counts.get('verified · priced',0) + counts.get('verified · unpriced',0)}</div><div class="l">reconciled to an official page</div></div>
  <div class="kpi"><div class="n">{counts.get('listing only',0)}</div><div class="l">listing only (not matched in this pass)</div></div>
  <div class="kpi"><div class="n">0</div><div class="l">OLBG prices used in a line</div></div>
</div>
<section class="section"><h2>Structure</h2><div class="grid">
<div class="card"><h3>Sport taxonomy</h3><p>OLBG's betting-tips hub exposes its sports as
<code>/betting-tips/&lt;Sport&gt;/&lt;id&gt;</code>. The ids observed in this capture are listed below.
The excluded sports are Football/Soccer (1), Horse Racing (2), American Football (11), Boxing/UFC/MMA (16),
Cycling (17) and Hurling (26); Specials has no stable id in the hub. Gaelic football (25) is published by OLBG
separately and is treated as out of scope on this desk, with the call flagged.</p></div>
<div class="card"><h3>Hydration arrays</h3><p>Each hub is a SvelteKit SSR page embedding <code>tips:[...]</code>
(fixtures) and <code>tournaments:[...]</code> (antepost and greyhound daily races). The machine-readable UTC start
is <code>event_start_unix_timestamp</code>; the visible clock is rendered in the client timezone. Greyhound daily
races sit inside <code>tournaments</code> with <code>market_alias:"Daily Races"</code> and <code>odds:"SP"</code>.</p></div>
<div class="card"><h3>Robots and politeness</h3><p>The capture honours OLBG's robots.txt: <code>/api/</code>,
<code>/sports/</code>, <code>/events.php</code>, <code>/tips/hot</code>, <code>/tipster/</code> and similar paths were
never requested. Requests to OLBG are spaced at least 0.85 s apart; the runner fetches public hub pages only.</p></div>
<div class="card"><h3>What the listing lacks</h3><p>On 22 October the Badminton, Table Tennis, Aussie Rules,
eSports and Greyhounds hubs served no embedded fixture rows; Snooker carried eight ties from the afternoon session
and Darts eight Friday first-round ties. That is why the official BWF, WTT, AFL, Riot and WST pages were tried
directly — and why seven sports end up with no verified fixture when those pages are shells or refuse the runner.</p></div>
</div></section>
<section class="section"><h2>Hubs captured</h2>
{table(["Sport", "OLBG id", "Hub", "Match rows", "Tournament rows", "Scope", "Link"], hub_rows)}</section>
<section class="section"><h2>The full live list, and what happened to it</h2>
<p class="lede" style="margin-bottom:10px">All {len(live)} dated in-scope events in the 20:58Z OLBG capture. A listing is
published as a desk row only when the same fixture was found on an official page; otherwise it stays here as
listing-only and is not priced. Matching is by team name and date, so an abbreviation-only OLBG name can appear as
“listing only” even where the official fixture was captured — those are not counted as errors.</p>
{table(["Sport", "OLBG event", "Start (UTC)", "Markets seen", "OLBG ref price", "Reconciliation", "Links"], live_rows, table_id="live")}</section>
<section class="section"><h2>In-scope events by sport</h2>
{table(["Sport", "Events"], sp_rows, table_id="events")}</section>
<section class="section"><h2>Discrepancies found</h2><div class="grid">
<div class="card"><h3>Darts spelling</h3><p>OLBG lists “Nathan Aspinall vs Cristo Reyes”; the official PDC Europe
draw prints “Christo Reyes”. The fixture is the same; the spelling differs.
<a href="https://www.olbg.com/betting-tips/Darts/15" rel="noopener">OLBG</a> ·
<a href="https://www.pdc-europe.tv/turniere/european-championship-2026" rel="noopener">PDC Europe</a></p></div>
<div class="card"><h3>Empty hubs</h3><p>Badminton, Table Tennis, Aussie Rules and eSports show zero embedded events on
22 October even though each has an official event in the window (BWF French Open, WTT Montpellier, AFLW, Worlds).
The official pages are the only verifiable route, and only lolesports exposed its data to the runner.</p></div>
<div class="card"><h3>Greyhounds “Daily Races”</h3><p>Greyhound rows are serialised as tournaments with an SP price.
They are not fixtures in the usual sense and GBGB publishes no machine-readable upcoming race list, so they are not
published here.</p></div>
<div class="card"><h3>Session times</h3><p>OLBG's visible clock strings are client-timezone; its epoch field is UTC.
The desk uses the epoch field for darts, then cross-checks the PDC session (Friday, 19:00 local / 17:00Z).</p></div>
</div></section>
"""
    return page("OLBG reverse-engineering", body, "olbg.html")


def sport_page(d: dict, sport: str, slug: str) -> str:
    rows = [r for r in d["desk"]["rows"] if r["sport"] == sport]
    cov = next((s for s in d["coverage"]["sports"] if s["sport"] == sport), {})
    preds = [p for p in d["predictions"]["predictions"] if p["sport"] == sport]
    trs = []
    for r in rows:
        trs.append(
            f'<tr data-conf="{esc(r["confidence"])}"><td>{esc(r["competition"])}<div class="src">{esc(r["stage"])}</div></td>'
            f'<td><b>{esc(r["side_a"])}</b> vs <b>{esc(r["side_b"])}</b>'
            f'{"<div class=src>" + esc(r["venue"]) + "</div>" if r["venue"] else ""}</td>'
            f'<td class="nowrap">{esc(fmt_date(r["start_utc"]))}</td>'
            f'<td>{esc(r["pick_label"]) or "—"}<div class="src">{esc(r["pick_market_name"])}</div></td>'
            f'<td class="num">{fmt_p(r["pick_prob"])}</td><td class="num">{fmt_am(r["pick_fair_american"])}</td>'
            f'<td class="num">{fmt_am(r["pick_book_american"])}</td><td>{conf_badge(r["confidence"])}</td>'
            f'<td>{band_badge(r)}</td><td>{src_link(r)}</td></tr>'
        )
    flags = [f for f in d["flagged"]["items"] if f["sport"] == sport or sport in f["sport"]]
    flag_parts = []
    for f in flags:
        src = f'<p><a href="{esc(f["source"])}" rel="noopener">Official page</a></p>' if f.get("source") else ""
        flag_parts.append(f'<div class="card"><h3>{esc(f["category"])}</h3><p>{esc(f["detail"])}</p>{src}</div>')
    flag_html = "".join(flag_parts)
    srcs = {}
    for r in rows:
        if r.get("source_url"):
            srcs[r["source_url"]] = r.get("source_name", "")
    src_html = "".join(f'<li><a href="{esc(u)}" rel="noopener">{esc(n or u)}</a></li>' for u, n in srcs.items())
    pred_html = f'<div class="grid">{pred_cards(d, sport, depth=1)}</div>' if preds else \
        '<div class="warnnote">No prediction is published for this sport. A prediction is only written when a row has a verified fixture, a verified line and a named selection; writing one without those would be invention.</div>'
    body = f"""
<section class="hero">
  <div class="badges"><a href="../coverage.html" class="badge win">← all sports</a>
  <span class="badge {'ok' if cov.get('priced') else ('medium' if cov.get('fixtures') else 'gap')}">{esc(cov.get('status',''))}</span></div>
  <h1>{esc(sport)}</h1>
  <p class="lede">{esc(cov.get('note',''))}</p>
  <div class="pillrow">
    <span class="pill"><b>{cov.get('fixtures',0)}</b> verified fixtures</span>
    <span class="pill"><b>{cov.get('priced',0)}</b> priced</span>
    <span class="pill"><b>{cov.get('high',0)}</b> High</span>
    <span class="pill"><b>{cov.get('high_in_window',0)}</b> High in band</span>
    <span class="pill"><b>{cov.get('markets',0)}</b> selections</span>
    <span class="pill"><b>{cov.get('predictions',0)}</b> predictions</span>
  </div>
</section>
<section class="section"><h2>Fixtures and picks</h2>
{('<div class="toolbar"><input id="q" type="search" placeholder="Search fixture or pick…"><select id="conf"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select><span class="count"><b id="shown">' + str(len(rows)) + '</b> of ' + str(len(rows)) + ' rows</span></div>' + table(["Competition", "Fixture", "Start (UTC)", "Pick", "P", "Fair", "Book", "Confidence", "Band", "Source"], trs)) if rows else '<div class="warnnote">No verified upcoming fixture for this sport in the 22 October 2026 capture. See <a href="../flagged.html">Flagged for review</a> for the URLs that were tried.</div>'}
</section>
<section class="section"><h2>Predictions</h2>{pred_html}</section>
<section class="section"><h2>Official sources used</h2><div class="card"><ul>{src_html or '<li>None — no fixture was verified.</li>'}</ul>
<p><a href="{esc(cov.get('olbg_url','https://www.olbg.com/betting-tips'))}" rel="noopener">OLBG hub for {esc(sport)}</a></p></div></section>
<section class="section"><h2>Flags for this sport</h2><div class="grid">{flag_html or '<div class="card"><p>No sport-specific flag.</p></div>'}</div></section>
"""
    return page(sport, body, "", depth=1, description=f"{sport} fixtures, own lines and predictions")


def main() -> int:
    d = load()
    OUT.mkdir(exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    pages = {
        "index.html": (index(d), "Overview"),
        "entries.html": (entries(d), "All entries"),
        "picks.html": (picks(d), "Picks"),
        "predictions.html": (predictions(d), "Predictions"),
        "markets.html": (markets(d), "Markets"),
        "coverage.html": (coverage(d), "Coverage"),
        "methodology.html": (methodology(d), "Methodology"),
        "sources.html": (sources(d), "Sources"),
        "verification.html": (verification(d), "Verification"),
        "flagged.html": (flagged(d), "Flagged for review"),
        "review.html": (review(d), "Repo review"),
        "olbg.html": (olbg_page(d), "OLBG reverse-engineering"),
    }
    for name, (html_text, _) in pages.items():
        (OUT / name).write_text(html_text, encoding="utf-8")
    for sport, slug in SPORTS:
        (OUT / "sports" / f"{slug}.html").write_text(sport_page(d, sport, slug), encoding="utf-8")
    print("pages", len(pages) + len(SPORTS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

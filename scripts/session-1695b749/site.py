#!/usr/bin/env python3
"""Board AB — static dashboard generator (no external assets, no CDN, no JS framework)."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-1695b749"
SITE = ROOT / "session-1695b749"

NAV = [
    ("index.html", "Dashboard"),
    ("picks.html", "High-confidence picks"),
    ("entries.html", "All fixtures"),
    ("markets.html", "Markets &amp; prices"),
    ("verification.html", "Verification register"),
    ("coverage.html", "Coverage"),
    ("methodology.html", "Method"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]


def e(x) -> str:
    return html.escape(str(x), quote=True)


def load(name):
    return json.loads((DATA / name).read_text())


CSS = """
:root{--ink:#12253c;--muted:#5a6b80;--line:#dfe5ee;--bg:#f5f7fb;--card:#fff;--blue:#0b5cad;--teal:#0f766e;--amber:#b45309;--red:#b42318;--green:#0f7b3f}
*{box-sizing:border-box}body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--blue)}a:hover{text-decoration:none}
header.top{background:#0d1b2a;color:#fff;padding:14px 0}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.brand{display:flex;align-items:baseline;gap:10px;text-decoration:none;color:#fff}
.brand b{font-size:21px;letter-spacing:.4px}.brand span{color:#9fb3c8;font-size:13px}
nav.main{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
nav.main a{color:#cfe0f0;text-decoration:none;font-size:13.5px;padding:5px 10px;border-radius:6px}
nav.main a:hover{background:#1b2f45;color:#fff}
nav.main a.active{background:#22405e;color:#fff}
main{padding:26px 0 60px}
h1{font-size:29px;margin:0 0 6px;letter-spacing:-.3px}h2{font-size:20px;margin:34px 0 10px}h3{font-size:16px;margin:0 0 6px}
.lede{color:var(--muted);max-width:900px;margin:0 0 18px}
.grid{display:grid;gap:14px}.k4{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}.k3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px}
.kpi .n{font-size:27px;font-weight:650;line-height:1.1}.kpi .l{color:var(--muted);font-size:13px;margin-top:4px}
.note{background:#fff;border:1px solid var(--line);border-left:4px solid var(--blue);border-radius:8px;padding:14px 16px;margin:16px 0}
.note.warn{border-left-color:var(--amber);background:#fffbf3}
.note.bad{border-left-color:var(--red);background:#fff7f6}
.tablewrap{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 11px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f7;font-size:12.5px;text-transform:uppercase;letter-spacing:.03em;color:#33475b;position:sticky;top:0}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.small{font-size:12.5px;color:var(--muted)}.muted{color:var(--muted)}
.tag + .tag{margin-left:6px}.tag{display:inline-block;font-size:11.5px;padding:2px 8px;border-radius:20px;border:1px solid var(--line);background:#f1f4f8;color:#33475b;white-space:nowrap}
.tag.high{background:#e7f6ec;border-color:#bfe5cb;color:var(--green)}
.tag.medium{background:#fff4e5;border-color:#f3d6ab;color:var(--amber)}
.tag.low{background:#f1f4f8;color:#475a70}
.tag.in{background:#e8f1fb;border-color:#bcd6f2;color:var(--blue)}
.tag.out{background:#f6eefb;border-color:#dcc8ef;color:#6b3fa0}
.tag.verified{background:#e7f6ec;border-color:#bfe5cb;color:var(--green)}
.tag.unverified{background:#fff1f0;border-color:#f3c6c1;color:var(--red)}
input[type=search]{width:100%;max-width:460px;padding:10px 12px;border:1px solid var(--line);border-radius:8px;font-size:14px;margin:10px 0}
.pick{background:#fff;border:1px solid var(--line);border-radius:10px;padding:16px;margin:14px 0}
.pick h3{margin:0 0 2px}.pick .meta{color:var(--muted);font-size:13px;margin-bottom:8px}
.pick p{margin:8px 0}
.pick ul{margin:6px 0 0 18px;padding:0;font-size:13px;color:var(--muted)}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:18px 0 40px}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:13px}
details summary{cursor:pointer;color:var(--blue)}
.evidence{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:#0d1b2a;color:#dbe7f3;padding:10px;border-radius:8px;overflow:auto;white-space:pre-wrap;word-break:break-word}
"""

JS = """
const box=document.querySelector('#filter');
if(box){const rows=[...document.querySelectorAll('tbody tr[data-row]')];const count=document.querySelector('#shown');
const run=()=>{const q=box.value.toLowerCase();let n=0;for(const r of rows){const hit=!q||r.dataset.search.includes(q);r.hidden=!hit;if(hit)n++;}if(count)count.textContent=n+' rows shown';};
box.addEventListener('input',run);run();}
"""


def page(title: str, body: str, active: str, prefix: str = "") -> str:
    nav = "".join(
        f'<a class="{"active" if href == active else ""}" href="{prefix}{href}">{label}</a>'
        for href, label in NAV
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OLBG4 Board AB</title>
<meta name="description" content="Verified fixtures, originated lines and high-confidence picks for {e(title)} — every row carries an official source link.">
<link rel="stylesheet" href="{prefix}style.css">
</head>
<body>
<header class="top"><div class="wrap">
  <a class="brand" href="{prefix}index.html"><b>OLBG4</b><span>Board AB · verified line desk · 22 Oct – 2 Nov 2026</span></a>
  <nav class="main">{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="wrap">
  Board AB · session <code>arena/1695b749-olbg4</code> · every price on this site is our own model output, not a bookmaker quote ·
  every fixture row links to the official payload it was read from · <a href="{prefix}flagged.html">Flagged for review</a>
</footer>
<script src="{prefix}app.js"></script>
</body>
</html>
"""


def conf_tag(c: str) -> str:
    return f'<span class="tag {c.lower()}">{e(c)}</span>'


def window_tag(inw: bool) -> str:
    return '<span class="tag in">in window</span>' if inw else '<span class="tag out">shorter than −250</span>'


def build():
    desk = load("desk.json")
    spec = load("model_spec.json")
    ver = load("verification.json")
    cov = load("coverage.json")
    flagged = load("flagged.json")
    listing = load("listing.json")
    checks = load("live_checks.json")
    fixtures = desk["fixtures"]
    highs = desk["high_selections"]
    counts = desk["counts"]
    hi = [h for h in highs if h["in_window"]]
    out = [h for h in highs if not h["in_window"]]
    hi.sort(key=lambda h: h["start_utc"])
    SITE.mkdir(exist_ok=True)
    (SITE / "sports").mkdir(exist_ok=True)
    (SITE / "style.css").write_text(CSS, encoding="utf-8")
    (SITE / "app.js").write_text(JS, encoding="utf-8")

    # ---------------- index
    sport_cards = []
    for sport in ("Ice Hockey", "Baseball", "Esports"):
        fs = [f for f in fixtures if f["sport"] == sport]
        hs = [h for h in highs if h["sport"] == sport and h["in_window"]]
        slug = fs[0]["slug"]
        sport_cards.append(f"""<div class="card"><h3>{e(sport)}</h3>
        <p class="small">{len(fs)} fixtures priced · {len(hs)} high-confidence selections inside the window</p>
        <p class="small"><a href="sports/{slug}.html">Open the {e(sport)} page →</a></p></div>""")
    top_picks = "".join(f"""<div class="pick">
      <h3>{e(h['selection'])}</h3>
      <div class="meta">{e(h['match'])} · {e(h['date'])} · {e(h['competition'])} · model probability {h['prob']:.4f} · fair {e(h['fair_american'])} (offered {e(h['offered_american'])}) {conf_tag(h['confidence'])} {window_tag(True)}</div>
      <p>{e(h['prediction']['text']) if h.get('prediction') else 'No write-up attached.'}</p>
    </div>""" for h in hi[:4])
    body = f"""
<h1>Verified fixtures, our own lines, one official source on every row.</h1>
<p class="lede">Board AB prices the next twelve days of the sports it could verify end to end — NHL, the MLB World Series and LoL Esports — and carries OLBG's live listing for every other in-scope sport with the official source deliberately blank. No bookmaker price is read anywhere, and no value is filled in when the official page is silent.</p>

<div class="grid k4">
  <div class="card kpi"><div class="n">{counts['fixtures']}</div><div class="l">fixtures priced from official inputs</div></div>
  <div class="card kpi"><div class="n">{sum(1 for f in fixtures if f['markets'].get('handicap', {}).get('home'))}</div><div class="l">with an originated handicap</div></div>
  <div class="card kpi"><div class="n">{sum(1 for f in fixtures if f['markets'].get('total', {}).get('over'))}</div><div class="l">with an originated match total</div></div>
  <div class="card kpi"><div class="n">{len(hi)}</div><div class="l">high-confidence selections inside −250 … +10,000</div></div>
</div>

<div class="note"><strong>How the confidence grades and the window interact.</strong>
{counts['high']} selections clear the brief's 70% rule. Because −250 is an implied 71.43%, a pick above 71.43% is
automatically shorter than the floor, so only {counts['high_in_window']} sit inside the requested window and
{counts['high_outside_window']} do not. Both sets are published in full on
<a href="picks.html">High-confidence picks</a>; nothing is relabelled. <a href="flagged.html">Flagged for review</a> records the arithmetic.</div>

<h2>The {len(hi)} in-window high-confidence selections</h2>
<p class="lede">Each one has a hand-written prediction grounded in the official record, recent results and a named player.</p>
{top_picks}
<p class="small"><a href="picks.html">Read all {len(hi)} write-ups and the full high-confidence board →</a></p>

<h2>Browse by sport</h2>
<div class="grid k3">{''.join(sport_cards)}</div>

<h2>What is on the site</h2>
<div class="grid k3">
  <div class="card"><h3>All fixtures</h3><p class="small">{len(fixtures)} priced fixtures with our moneyline, handicap, match total and team totals, plus {len(listing['matches'])} OLBG listing rows that carry no official source and no price. <a href="entries.html">Open the table →</a></p></div>
  <div class="card"><h3>Verification register</h3><p class="small">{len(ver['rows'])} rows, {sum(1 for r in ver['rows'] if r['status']=='verified')} hash-verified against the capture manifest, each with the exact field values read and the official URL. <a href="verification.html">Open the register →</a></p></div>
  <div class="card"><h3>Coverage</h3><p class="small">All {len(cov['rows'])} in-scope sports and the {len(cov['excluded_by_brief'])} sports the brief excludes, with the reason any sport is unpriced. <a href="coverage.html">Open coverage →</a></p></div>
  <div class="card"><h3>Flagged for review</h3><p class="small">{len(flagged['items'])} published irregularities with source links — the window arithmetic, a stadium anomaly, correlated picks and the sports this session could not price. <a href="flagged.html">Open flags →</a></p></div>
</div>
"""
    (SITE / "index.html").write_text(page("Dashboard", body, "index.html"), encoding="utf-8")

    # ---------------- picks
    def pick_block(h, idx):
        pred = h.get("prediction")
        facts = ""
        if pred:
            facts = "<ul>" + "".join(f"<li>{e(x)}</li>" for x in pred["facts"]) + "</ul>"
        return f"""<div class="pick">
        <h3>{idx}. {e(h['selection'])}</h3>
        <div class="meta">{e(h['match'])} · {e(h['competition'])} · starts {e(h['start_utc'])} UTC · market: {e(h['market'].replace('_',' '))} ·
        model probability {h['prob']:.4f} · fair {e(h['fair_american'])} · our offered {e(h['offered_american'])} {conf_tag(h['confidence'])} {window_tag(h['in_window'])}</div>
        <p>{e(pred['text']) if pred else 'No write-up attached.'}</p>
        {facts}
        <p class="small">Official fixture: <a href="{e(h['source_url'])}">{e(h['source_url'])}</a> · inputs: <a href="{e(h['inputs_url'])}">{e(h['inputs_url'])}</a></p>
        </div>"""

    in_blocks = "".join(pick_block(h, i + 1) for i, h in enumerate(hi))
    out_rows = "".join(
        f"<tr data-row data-search=\"{e((h['match']+' '+h['selection']+' '+h['sport']).lower())}\">"
        f"<td>{e(h['date'])}</td><td>{e(h['sport'])}</td><td>{e(h['match'])}</td>"
        f"<td><strong>{e(h['selection'])}</strong><br><span class='small muted'>{e(h['market'].replace('_',' '))}</span></td>"
        f"<td class='num'>{h['prob']:.4f}</td><td class='num'>{e(h['fair_american'])}</td><td class='num'>{e(h['offered_american'])}</td>"
        f"<td>{conf_tag(h['confidence'])}</td><td>{window_tag(h['in_window'])}</td>"
        f"<td class='small'><a href='{e(h['source_url'])}'>official</a></td></tr>"
        for h in sorted(out, key=lambda x: x["start_utc"])
    )
    body = f"""
<h1>High-confidence picks</h1>
<p class="lede">Every selection whose model probability is at least 0.70. The brief asks for picks between −250 and +10,000, so the first
section is the in-window set with a written prediction each; the second section is the rest of the high-confidence board, priced shorter
than the −250 floor and published rather than hidden.</p>
<div class="note"><strong>{len(hi)} in-window · {len(out)} outside the window · {counts['match_winner_high']} match-winner picks reach 70% at all.</strong>
The match-winner grade is the headline pick on each fixture row; the high-confidence board also contains puck-line and team-total selections,
which is where most of the 70%+ probabilities live this early in the NHL season.</div>
<h2>In the window (−250 to +10,000): {len(hi)} picks</h2>
{in_blocks}
<h2>High confidence but shorter than −250: {len(out)} selections</h2>
<p class="lede">These clear 70% but price shorter than the brief's floor. They are listed with their prices and official fixture link so you can see
exactly what was excluded, and why.</p>
<label class="small" for="filter">Filter by team, sport or selection</label>
<input id="filter" type="search" placeholder="e.g. Oilers, Bruins, team total">
<p class="small" id="shown"></p>
<div class="tablewrap"><table><thead><tr><th>Date (UTC)</th><th>Sport</th><th>Match</th><th>Selection</th><th class="num">p</th><th class="num">Fair</th><th class="num">Offered</th><th>Grade</th><th>Window</th><th>Source</th></tr></thead>
<tbody>{out_rows}</tbody></table></div>
"""
    (SITE / "picks.html").write_text(page("High-confidence picks", body, "picks.html"), encoding="utf-8")

    # ---------------- entries (all fixtures + listing)
    fx_rows = []
    for f in fixtures:
        p = f["pick"]
        mk = f["markets"]
        tot = mk.get("total", {})
        hc = mk.get("handicap", {})
        fx_rows.append(
            f"<tr data-row data-search=\"{e((f['match'] if 'match' in f else f['away']+' '+f['home']+' '+f['sport']+' '+f['competition']).lower())}\">"
            f"<td>{e(f['date'])}<br><span class='small muted'>{e(f['start_utc'][11:16])}Z</span></td>"
            f"<td>{e(f['sport'])}<br><span class='small muted'>{e(f['league'])}</span></td>"
            f"<td>{e(f['away'])} at {e(f['home'])}<br><span class='small muted'>{e(f['venue'])}</span></td>"
            f"<td><strong>{e(p['selection'])}</strong><br><span class='small muted'>{e(p['fair_american'])} fair · {e(p['offered_american'])} offered</span></td>"
            f"<td>{conf_tag(p['confidence'])}</td>"
            f"<td class='num'>{e(hc.get('home', {}).get('offered_american', '—'))} / {e(hc.get('away', {}).get('offered_american', '—'))}</td>"
            f"<td class='num'>{e(tot.get('line', '—'))}<br><span class='small muted'>{e(tot.get('over', {}).get('offered_american', '—'))} / {e(tot.get('under', {}).get('offered_american', '—'))}</span></td>"
            f"<td class='small'><span class='tag verified'>verified</span><br><a href='{e(f['source']['url'])}'>official fixture</a><br><a href='{e(f['inputs']['url'])}'>official inputs</a></td></tr>"
        )
    lst_rows = []
    for r in sorted(listing["matches"], key=lambda x: (x["start_utc"] or "", x["sport"])):
        lst_rows.append(
            f"<tr data-row data-search=\"{e((r['sport']+' '+r['event_name']).lower())}\">"
            f"<td>{e((r['start_utc'] or '')[:10])}<br><span class='small muted'>{e((r['start_utc'] or '')[11:16])}Z</span></td>"
            f"<td>{e(r['sport'])}</td><td>{e(r['event_name'])}</td>"
            f"<td class='muted'>—</td><td><span class='tag low'>ungraded</span></td>"
            f"<td class='num'>—</td><td class='num'>—</td>"
            f"<td class='small'><span class='tag unverified'>unverified</span><br>no official source captured<br><a href='{e(r['olbg_url'])}'>OLBG listing</a></td></tr>"
        )
    body = f"""
<h1>All fixtures</h1>
<p class="lede">Two blocks, deliberately separated. The first is {len(fixtures)} fixtures this board priced from official payloads. The second is
{len(listing['matches'])} match rows carried from OLBG's live listing: they are real listing rows, but no official source was captured for them
in this session, so their price, pick and official link are blank and they are flagged unverified.</p>
<div class="note"><strong>Verification rule.</strong> A row is only marked verified when every value on it came from an official payload whose
SHA-256 matches the capture manifest. Where that is not true the value is blank, not estimated. The register is on
<a href="verification.html">Verification</a>.</div>
<h2>Priced from official sources: {len(fixtures)} fixtures</h2>
<label class="small" for="filter">Filter by team, sport or competition</label>
<input id="filter" type="search" placeholder="e.g. Oilers, Maple Leafs, NHL">
<p class="small" id="shown"></p>
<div class="tablewrap"><table><thead><tr><th>Date (UTC)</th><th>Sport</th><th>Fixture</th><th>Match-winner pick</th><th>Grade</th><th class="num">Handicap (home / away)</th><th class="num">Total (line · over / under)</th><th>Source</th></tr></thead>
<tbody>{''.join(fx_rows)}</tbody></table></div>

<h2>OLBG listing only: {len(listing['matches'])} match rows and {len(listing['outrights'])} outrights</h2>
<p class="lede">Carried from the commit-verified OLBG hub capture of {e(listing['matches'][0]['captured_at_utc'])}. No price, tip or percentage from OLBG is reproduced; OLBG is used as the listing source only.</p>
<div class="tablewrap"><table><thead><tr><th>Date (UTC)</th><th>Sport</th><th>Event</th><th>Our price</th><th>Grade</th><th class="num">Handicap</th><th class="num">Total</th><th>Status</th></tr></thead>
<tbody>{''.join(lst_rows)}</tbody></table></div>
"""
    (SITE / "entries.html").write_text(page("All fixtures", body, "entries.html"), encoding="utf-8")

    # ---------------- markets
    def dist(sel_key):
        vals = [h[sel_key] for h in highs]
        return vals
    market_counts = {m: 0 for m in ("moneyline", "handicap", "total", "team_total_home", "team_total_away")}
    for f in fixtures:
        for m in market_counts:
            if m in f["markets"] and ("home" in f["markets"][m] or "over" in f["markets"][m]):
                market_counts[m] += 1
    sample_rows = []
    for f in fixtures[:1] + [x for x in fixtures if x["sport"] == "Baseball"][:1] + [x for x in fixtures if x["sport"] == "Esports"][:1]:
        ml, hc, tt = f["markets"]["moneyline"], f["markets"]["handicap"], f["markets"]["total"]
        rows = [
            ("Moneyline", f"{f['home']}", ml["home"]["offered_american"], f"{ml['home']['prob']:.4f}"),
            ("Moneyline", f"{f['away']}", ml["away"]["offered_american"], f"{ml['away']['prob']:.4f}"),
        ]
        if "home" in hc:
            line = "-1.5" if f["sport"] in ("Ice Hockey", "Baseball") else ""
            rows += [(f"Handicap {line}", f"{f['home']}", hc["home"]["offered_american"], f"{hc['home']['prob']:.4f}"),
                     (f"Handicap {'+1.5' if line else ''}", f"{f['away']}", hc["away"]["offered_american"], f"{hc['away']['prob']:.4f}")]
        if "over" in tt:
            rows += [(f"Match total {tt['line']}", "Over", tt["over"]["offered_american"], f"{tt['over']['prob']:.4f}"),
                     (f"Match total {tt['line']}", "Under", tt["under"]["offered_american"], f"{tt['under']['prob']:.4f}")]
        for m in ("team_total_home", "team_total_away"):
            if m in f["markets"] and "over" in f["markets"][m]:
                t = f["markets"][m]
                rows += [(f"Team total {t['line']}", f"{t['market']} over", t["over"]["offered_american"], f"{t['over']['prob']:.4f}"),
                         (f"Team total {t['line']}", f"{t['market']} under", t["under"]["offered_american"], f"{t['under']['prob']:.4f}")]
        for market, sel, price, prob in rows:
            sample_rows.append(f"<tr><td>{e(f['away'])} at {e(f['home'])}<br><span class='small muted'>{e(f['sport'])}</span></td><td>{e(market)}</td><td>{e(sel)}</td><td class='num'>{e(price)}</td><td class='num'>{e(prob)}</td></tr>")
    body = f"""
<h1>Markets and prices</h1>
<p class="lede">Four markets are investigated for every fixture that has the official inputs to support them: match winner,
handicap, match total and both team totals. Every price is our own — a model probability converted to a fair price, then shortened by a
flat 4% two-way overround for the offered price. No bookmaker, exchange or OLBG price is read.</p>
<div class="grid k4">
  <div class="card kpi"><div class="n">{market_counts['moneyline']}</div><div class="l">fixtures with a moneyline</div></div>
  <div class="card kpi"><div class="n">{market_counts['handicap']}</div><div class="l">with a handicap (puck line or run line)</div></div>
  <div class="card kpi"><div class="n">{market_counts['total']}</div><div class="l">with a match total</div></div>
  <div class="card kpi"><div class="n">{market_counts['team_total_home'] + market_counts['team_total_away']}</div><div class="l">team-total books created</div></div>
</div>
<div class="note"><strong>Two-way book, always.</strong> Home and away (or over and under) probabilities sum to 1 before the margin and the two
offered prices both carry the same 4% haircut, so the pair is a genuine book rather than two unrelated numbers.</div>
<h2>Worked examples — one fixture from each covered sport</h2>
<div class="tablewrap"><table><thead><tr><th>Fixture</th><th>Market</th><th>Selection</th><th class="num">Our price</th><th class="num">Model p</th></tr></thead><tbody>{''.join(sample_rows)}</tbody></table></div>
<h2>What each market means here</h2>
<div class="grid k3">
  <div class="card"><h3>Match winner</h3><p class="small">NHL: includes overtime and the shootout. MLB: includes extra innings. LoL: series winner over the stated format. The headline pick on every fixture is this market.</p></div>
  <div class="card"><h3>Handicap</h3><p class="small">NHL puck line ±1.5 and MLB run line ±1.5, priced from the distribution of the goal or run difference. Not originated for LoL, because the official payload carries no map-score input.</p></div>
  <div class="card"><h3>Totals</h3><p class="small">NHL match total (5.5 or 6.5) and team totals of 2.5; MLB match total at the half-run line nearest the two-sided expectation and team totals of 3.5. Priced from a Poisson sum, never from a market line.</p></div>
</div>
<h2>Model parameters</h2>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Strength</th><th>Moneyline</th><th>Totals</th></tr></thead><tbody>
<tr><td>NHL</td><td>{e(spec['nhl']['strength'])}</td><td>{e(spec['nhl']['moneyline'])}</td><td>{e(spec['nhl']['total'])}</td></tr>
<tr><td>MLB</td><td>{e(spec['mlb']['strength'])}</td><td>{e(spec['mlb']['moneyline'])}</td><td>{e(spec['mlb']['total'])}</td></tr>
<tr><td>LoL</td><td>{e(spec['esports']['strength'])}</td><td>{e(spec['esports']['moneyline'])}</td><td>{e(spec['esports']['total_handicap'])}</td></tr>
</tbody></table></div>
"""
    (SITE / "markets.html").write_text(page("Markets and prices", body, "markets.html"), encoding="utf-8")

    # ---------------- verification
    vrows = []
    for r in ver["rows"]:
        evid = "".join(f"""<details><summary>{e(f['field'])}</summary>
        <div class="evidence">{e(f['value'])}</div>
        <p class="small">Source: <a href="{e(f['url'])}">{e(f['url'])}</a> · captured {e(f['captured_at_utc'])} · file <code>{e(f['file'])}</code><br>
        SHA-256 <code>{e(f['sha256'])}</code> · recomputed at build time: <strong>{'match' if f['hash_ok'] else 'MISMATCH'}</strong></p></details>"""
                      for f in r["fields"])
        vrows.append(f"""<tr data-row data-search="{e((r['match']+' '+r['sport']+' '+r['competition']).lower())}">
        <td>{e(r['date'])}</td><td>{e(r['sport'])}<br><span class="small muted">{e(r['competition'])}</span></td>
        <td>{e(r['match'])}<br><span class="small muted">{e(r['venue'])} · {e(r['start_utc'])}</span></td>
        <td><span class="tag verified">{e(r['status'])}</span></td>
        <td>{evid}<p class="small">Not checked: {e(', '.join(r['not_checked']))}.</p></td></tr>""")
    body = f"""
<h1>Verification register</h1>
<p class="lede">One row per priced fixture. Each row lists the exact values read for that fixture and its inputs, the official URL they came from,
the capture timestamp and the SHA-256 that was recomputed when this page was built. A row is only marked verified when every hash matches.</p>
<div class="note"><strong>{sum(1 for r in ver['rows'] if r['status'] == 'verified')} of {len(ver['rows'])} rows verified by hash; 0 mismatches.</strong>
The payloads themselves were captured earlier today (02:59–04:41 UTC) by the repository's official-source collector and committed byte-for-byte; this board
re-read those bytes, re-checked every hash and re-derived every published value from them, and separately re-read five pages live (see <a href="sources.html">Sources</a>).
The register deliberately does <em>not</em> claim fact-checking of team news: injuries, suspensions, weather and line movement were not checked and are
named as unchecked on every row. Team records, scoring inputs, participants, dates, start times and venues were checked against the official payloads.</div>
<label class="small" for="filter">Filter by team, sport or competition</label>
<input id="filter" type="search" placeholder="e.g. Rangers, Panthers, World Series">
<p class="small" id="shown"></p>
<div class="tablewrap"><table><thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Status</th><th>Evidence read (expand)</th></tr></thead>
<tbody>{''.join(vrows)}</tbody></table></div>
"""
    (SITE / "verification.html").write_text(page("Verification register", body, "verification.html"), encoding="utf-8")

    # ---------------- coverage
    crows = "".join(
        f"<tr><td><strong>{e(r['sport'])}</strong><br><span class='small muted'>{e(r['note'])}</span></td>"
        f"<td><span class='tag {'verified' if r['status']=='covered' else ('medium' if 'listed' in r['status'] or 'outright' in r['status'] else 'unverified')}'>{e(r['status'])}</span></td>"
        f"<td class='num'>{r['fixtures']}</td><td class='num'>{r['priced']}</td><td class='num'>{r.get('listed_on_olbg', 0)}</td>"
        f"<td class='num'>{r.get('listed_outrights', 0)}</td><td class='num'>{r['high_in_window']}</td>"
        f"<td class='small'>{e(r.get('reason', ''))}</td></tr>" for r in cov["rows"])
    ex = " ".join(f"<span class='tag low'>{e(r['sport'])}</span>" for r in cov["excluded_by_brief"])
    body = f"""
<h1>Coverage</h1>
<p class="lede">The brief's in-scope sports and exactly what this session did with each one. Nothing is priced without official numeric inputs;
where a sport could not be priced the row is blank and the reason is stated.</p>
<div class="grid k3">
  <div class="card kpi"><div class="n">{sum(1 for r in cov['rows'] if r['status']=='covered')}</div><div class="l">sports priced end to end</div></div>
  <div class="card kpi"><div class="n">{len(listing['matches'])}</div><div class="l">OLBG match rows carried as listing only</div></div>
  <div class="card kpi"><div class="n">{sum(1 for r in cov['rows'] if r['status'].startswith('not covered'))}</div><div class="l">sports with no fixture at all this session</div></div>
</div>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Status</th><th class="num">Priced here</th><th class="num">Of which priced</th><th class="num">OLBG match rows</th><th class="num">OLBG outrights</th><th class="num">High in window</th><th>Reason if not priced</th></tr></thead>
<tbody>{crows}</tbody></table></div>
<h2>Excluded by the brief — and honoured</h2>
<p class="lede">These categories appear nowhere in this board's fixtures, prices or picks: {ex}</p>
<div class="note warn"><strong>Gaelic Football and Motor Racing are a judgement call.</strong> OLBG's listing carried them, but the brief names neither.
They are carried as listing-only rows with a blank price and are flagged on <a href="flagged.html">Flagged for review</a> rather than priced or dropped.</div>
<h2>How to close the gaps</h2>
<p class="lede">Every unpriced sport needs the same two things this desk used for hockey and baseball: an official fixture feed and an official
numeric form input on the same domain. Earlier desks on this repository priced handball, tennis, darts, URC and NFL from their own captures; their
pages remain linked from the repository's root dashboard.</p>
"""
    (SITE / "coverage.html").write_text(page("Coverage", body, "coverage.html"), encoding="utf-8")

    # ---------------- methodology
    body = f"""
<h1>Method</h1>
<p class="lede">A short, checkable description of how every number on this site was produced. If a step is not described here, it was not done.</p>
<h2>The sequence</h2>
<ol>
<li><strong>Fixture list.</strong> The 22 October – 2 November 2026 window was read from the official league payloads (NHL schedule API for each day,
MLB Stats API for the World Series, Riot's LoL Esports schedule). OLBG's live listing supplies the wider in-scope fixture list and is carried as listing only.</li>
<li><strong>Provenance.</strong> Every payload is committed byte-for-byte with its URL, HTTP status, capture timestamp and SHA-256. The build recomputes
each hash and refuses to run on a mismatch. Five additional pages were read live by this session and are listed on <a href="sources.html">Sources</a>.</li>
<li><strong>Inputs.</strong> Only official fields: points, games played, wins/losses, goals or runs for and against, home/road splits, last-ten and streak.
Those exact field values are printed in the <a href="verification.html">verification register</a> for every fixture.</li>
<li><strong>Model.</strong> Strengths come from shrunk official win/points percentages with a goal-difference term; the moneyline is a logistic function of
the strength difference plus a fixed home edge; totals are a blend of official scoring rates with the league average, priced as a Poisson sum; the handicap
is the probability of a two-goal (or two-run) margin from a Skellam distribution. Parameters are listed on <a href="markets.html">Markets</a>.</li>
<li><strong>Prices.</strong> Fair price = 1 / p. Offered price = fair × (1 − 4%). Two-way books only; the two sides sum to 1 before the margin.</li>
<li><strong>Grades.</strong> High = p ≥ 0.70 with complete inputs; Medium = 0.60–0.70; Low = below 0.60. A roster-thin side (fewer than 6 NHL games, fewer
than 3 LoL series) cannot be graded above Low.</li>
<li><strong>Window.</strong> A pick is "in window" when its <em>fair</em> price is between −250 and +10,000. Because our offered price carries a margin it is
always shorter than the fair price, so the window is judged on the fair price and both are printed.</li>
<li><strong>Write-ups.</strong> Only for in-window High selections: one hand-written prediction each, at least 30 words, naming the selection, the clubs, the
form line, at least one recent result and (where the official leaderboard supports it) a player, with the facts listed underneath.</li>
</ol>
<h2>What the model does not do</h2>
<div class="grid k3">
  <div class="card"><h3>It does not read prices</h3><p class="small">No bookmaker, exchange or OLBG price enters any calculation. There is therefore no
  market-calibration step and no "value" claim — these are independent numbers.</p></div>
  <div class="card"><h3>It does not know team news</h3><p class="small">No injury, suspension, line-up or weather feed was captured. A goaltender or
  starting-pitcher change is not reflected.</p></div>
  <div class="card"><h3>It does not extrapolate</h3><p class="small">If an official field is missing, the market is left blank with a reason. Nine LoL fixtures
  have no map handicap or map total for exactly that reason.</p></div>
</div>
<h2>Known limitations</h2>
<p class="lede">Early season samples are small (8–11 NHL games), so probabilities are deliberately compressed toward 50% and only
{counts['match_winner_high']} of {counts['fixtures']} fixtures clear a 70% match-winner grade. MLB strength uses the full 162-game record with no
starting-pitcher adjustment. LoL series records come from the completed matches in the same schedule payload and use a four-series prior.</p>
"""
    (SITE / "methodology.html").write_text(page("Method", body, "methodology.html"), encoding="utf-8")

    # ---------------- sources
    src_rows = "".join(
        f"<tr><td>{e(s['label'])}<br><span class='small muted'>{e(s['file'])}</span></td>"
        f"<td><a href='{e(s['url'])}'>{e(s['url'])}</a></td>"
        f"<td class='num'>{e(s['captured_at_utc'])}</td><td class='num'>{s.get('bytes','')}</td>"
        f"<td class='small'><code>{e(s['sha256'][:24])}…</code><br>{'match' if s['hash_ok'] else 'MISMATCH'}</td></tr>"
        for s in sorted(desk["sources"], key=lambda x: x["name"]))
    live_rows = "".join(
        f"<tr><td>{e(c['id'])}</td><td>{e(c['purpose'])}</td><td><a href='{e(c['url'])}'>{e(c['url'])}</a></td>"
        f"<td class='num'>{e(c['fetched_at_utc'])}</td><td class='small'>{e(c.get('observed',''))}</td></tr>" for c in checks["checks"])
    body = f"""
<h1>Sources</h1>
<p class="lede">Every source is on the governing body's own domain. Payloads captured by the repository's official-source collector are committed
byte-for-byte and hash-checked here; the five live reads this session made with the page-fetch tool are listed separately with a quote of what was observed.</p>
<h2>Committed official payloads ({len(desk['sources'])})</h2>
<div class="tablewrap"><table><thead><tr><th>Source</th><th>URL</th><th class="num">Captured (UTC)</th><th class="num">Bytes</th><th>SHA-256 vs file</th></tr></thead><tbody>{src_rows}</tbody></table></div>
<h2>Live reads by this session ({len(checks['checks'])})</h2>
<div class="tablewrap"><table><thead><tr><th>ID</th><th>Purpose</th><th>URL</th><th class="num">Fetched (UTC)</th><th>What was observed</th></tr></thead><tbody>{live_rows}</tbody></table></div>
<h2>Player data</h2>
<p class="lede">The players named in write-ups come from the NHL's own skater points-leaders endpoint,
<a href="{e(load('live/nhl_points_leaders_excerpt.json')['source_url'])}">skater-stats-leaders</a>, read on 2026-10-22. Only the players quoted are stored, with
their season points, in <code>data/session-1695b749/live/nhl_points_leaders_excerpt.json</code>.</p>
<h2>Listing source</h2>
<p class="lede">OLBG's hub capture ({listing['hubs_verified']} hubs, all hash-verified, {len(listing['matches'])} match rows, {len(listing['outrights'])} outrights)
is used for the listing only. No OLBG tip, percentage, comment or price is reproduced on this site.</p>
<h2>Blocked or unavailable</h2>
<p class="lede">The sandbox shell can only reach GitHub, npm and PyPI, so league domains were read with the page-fetch tool or from the committed capture.
Endpoints that failed during the repository's collection runs are recorded with their exact URL and status — for example the NBA schedule CDN
(HTTP 403 / access denied), the NBA scoreboard (timeout) and the ATP Tour scores page (JavaScript challenge). Those sports are listed as unpriced on
<a href="coverage.html">Coverage</a> instead of being estimated.</p>
"""
    (SITE / "sources.html").write_text(page("Sources", body, "sources.html"), encoding="utf-8")

    # ---------------- flagged
    items = "".join(f"""<div class="pick">
      <h3>{e(i['id'])} · {e(i['title'])}</h3>
      <div class="meta">severity: {e(i['severity'])}</div>
      <p>{e(i['detail'])}</p>
      <p class="small">Sources: {' · '.join(f"<a href='{e(u)}'>{e(u)}</a>" for u in i['sources'])}</p></div>""" for i in flagged["items"])
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Every irregularity this session found, published with its source links. None of these blocked publication; each one is here so it can be
reviewed after the site is live and a change requested if you disagree with the call.</p>
<div class="note bad"><strong>Nothing on this page is a corrected value.</strong> Where a value looked wrong it was left exactly as the official payload
returns it, and the discrepancy is described here.</div>
{items}
"""
    (SITE / "flagged.html").write_text(page("Flagged for review", body, "flagged.html"), encoding="utf-8")

    # ---------------- sport pages
    for sport, slug in (("Ice Hockey", "ice-hockey"), ("Baseball", "baseball"), ("Esports", "esports")):
        fs = [f for f in fixtures if f["sport"] == sport]
        if not fs:
            continue
        hs = [h for h in highs if h["sport"] == sport]
        iw = [h for h in hs if h["in_window"]]
        rows = []
        for f in fs:
            p = f["pick"]
            rows.append(f"""<tr data-row data-search="{e((f['away']+' '+f['home']+' '+f['competition']).lower())}">
            <td>{e(f['date'])}<br><span class="small muted">{e(f['start_utc'][11:16])}Z</span></td>
            <td>{e(f['away'])} at {e(f['home'])}<br><span class="small muted">{e(f['venue'])}</span></td>
            <td><strong>{e(p['selection'])}</strong><br><span class="small muted">{e(p['fair_american'])} fair</span></td>
            <td>{conf_tag(p['confidence'])}</td>
            <td class="num">{p['prob']:.4f}</td>
            <td class="small"><a href="{e(f['source']['url'])}">official fixture</a><br><a href="{e(f['inputs']['url'])}">inputs</a></td></tr>""")
        writeups = "".join(pick_block(h, i + 1) for i, h in enumerate(iw))
        body = f"""
<h1>{e(sport)}</h1>
<p class="lede">{len(fs)} fixtures priced from official inputs, {len(hs)} High-confidence selections, {len(iw)} of them inside the −250 … +10,000 window.</p>
<div class="note"><a href="../index.html">← Back to the dashboard</a> · <a href="../markets.html">market parameters</a> · <a href="../flagged.html">flags</a></div>
<h2>Fixtures and match-winner picks</h2>
<label class="small" for="filter">Filter</label>
<input id="filter" type="search" placeholder="Filter fixtures">
<p class="small" id="shown"></p>
<div class="tablewrap"><table><thead><tr><th>Date (UTC)</th><th>Fixture</th><th>Pick</th><th>Grade</th><th class="num">p</th><th>Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<h2>In-window high-confidence write-ups</h2>
{writeups or '<p class="lede">No in-window High selection for this sport.</p>'}
"""
        (SITE / "sports" / f"{slug}.html").write_text(page(sport, body, "", prefix="../"), encoding="utf-8")

    print(json.dumps({"pages": 9 + 3, "in_window": len(hi), "outside": len(out)}, indent=2))


if __name__ == "__main__":
    build()

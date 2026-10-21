#!/usr/bin/env python3
"""
tools/build_site.py — Generate this session's static GitHub Pages dashboard in session-6e0f382d/
from data/matches/*.json (originated by tools/model.py).

Every table row carries a link to its official source. The builder fails
loudly if a high-confidence pick lacks a written prediction, if a row lacks
a source, or if an internal link would be broken.
"""
import json, os, re, sys
from html import escape as E

ROOT = os.path.join(os.path.dirname(__file__), '..')
MD = os.path.join(ROOT, 'data', 'matches')
VD = os.path.join(ROOT, 'data', 'verified')
DOCS = os.path.join(ROOT, 'session-6e0f382d')  # this build's folder (multi-build portal on main; docs/ is Build A)
SPORTS_DIR = os.path.join(DOCS, 'sports')
ASSETS = os.path.join(DOCS, 'assets')
for p in (SPORTS_DIR, ASSETS):
    os.makedirs(p, exist_ok=True)

def load_matches():
    sports = []
    for f in sorted(os.listdir(MD)):
        if not f.endswith('.json'):
            continue
        slug = f[:-5]
        payload = json.load(open(os.path.join(MD, f)))
        sports.append({'slug': slug, **payload})
    sports.sort(key=lambda s: s['sport'])
    return sports

def zero_check(sport):
    z = sport.get('zero_event_check')
    if z:
        return z
    vf = os.path.join(VD, sport['slug'] + '.json')
    if os.path.exists(vf):
        v = json.load(open(vf))
        for k in ('zero_event_cross_check', 'zero_match_cross_check', 'coverage_finding'):
            if v.get(k):
                return v[k]
    return None

def pct(p, digits=0):
    if p is None:
        return '—'
    return f"{p*100:.{digits}f}%"

def conf_chip(c):
    return f'<span class="chip chip-{c}">{c}</span>'

def src_link(m, label='Official source'):
    url = m.get('source_url')
    if not url:
        return '<span class="missing">MISSING</span>'
    name = m.get('source_name') or label
    return f'<a href="{E(url)}" target="_blank" rel="noopener">{E(name)}</a>'

def probs_cell(m):
    if m.get('prob_home') is None:
        return '—'
    bits = [f"H {pct(m['prob_home'])}"]
    if m.get('prob_draw') is not None:
        bits.append(f"D {pct(m['prob_draw'])}")
    bits.append(f"A {pct(m['prob_away'])}")
    return ' · '.join(bits)

def lines_cell(m):
    if not m.get('lines'):
        return '<span class="muted">Not originated (see detail)</span>'
    items = []
    for l in m['lines']:
        seg = f"<b>{E(l['market'])}:</b> {E(l['selection'])}"
        if l.get('probability') is not None:
            seg += f" — {pct(l['probability'])} (fair {l['fair_odds']})"
        items.append(seg)
    return '<br>'.join(items)

NAV_PAGES = [('index.html', 'Home'), ('methodology.html', 'Methodology'),
             ('findings.html', 'Findings'), ('flagged.html', 'Flagged for Review')]

def page(title, body, sports, depth=0, active=''):
    prefix = '../' * depth
    nav = ['<nav class="topnav">']
    nav.append(f'<a class="brand" href="{prefix}index.html">OLBG Reverse-Engineered — Modelled Lines Dashboard</a>')
    nav.append('<span class="navlinks">')
    for href, label in NAV_PAGES:
        cls = ' class="active"' if active == href else ''
        nav.append(f'<a{cls} href="{prefix}{href}">{label}</a>')
    nav.append('</span></nav>')
    sport_nav = ' · '.join(
        f'<a href="{prefix}sports/{s["slug"]}.html">{E(s["sport"])}</a>' for s in sports)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
{''.join(nav)}
<div class="sportnav">{sport_nav}</div>
<main>
{body}
</main>
<footer>
<p>All lines on this site are <strong>original lines originated by this project</strong> from official,
publicly available data (see <a href="{prefix}methodology.html">Methodology</a>). They are modelled
probabilities, <strong>not</strong> bookmaker prices and <strong>not</strong> betting advice. Fixtures and inputs verified 21 October 2026.
Event coverage reflects the OLBG.com tipster feed as server-rendered on that date.</p>
</footer>
</body>
</html>"""

CSS = """
:root { --ink:#1a2332; --mut:#5b6b80; --line:#d8dee7; --bg:#f6f8fb; --card:#fff;
        --high:#146c2e; --med:#9a6200; --low:#5b6b80; --accent:#0b5cad; }
* { box-sizing: border-box; }
body { margin:0; font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
       color:var(--ink); background:var(--bg); line-height:1.45; }
a { color:var(--accent); }
.topnav { background:#0e2233; color:#fff; padding:10px 18px; display:flex; flex-wrap:wrap;
          gap:10px; align-items:center; justify-content:space-between; }
.topnav a { color:#cfe3f5; text-decoration:none; margin-right:14px; }
.topnav a.brand { color:#fff; font-weight:700; font-size:17px; }
.topnav a.active { color:#fff; text-decoration:underline; }
.sportnav { background:#e8eef5; padding:8px 18px; font-size:13.5px; border-bottom:1px solid var(--line); }
.sportnav a { white-space:nowrap; }
main { max-width:1180px; margin:0 auto; padding:22px 16px 30px; }
h1 { font-size:26px; margin:6px 0 10px; } h2 { font-size:20px; margin:28px 0 8px; }
h3 { font-size:16px; margin:20px 0 6px; }
.cards { display:grid; grid-template-columns:repeat(auto-fill,minmax(215px,1fr)); gap:12px; margin:16px 0; }
.card2 { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
.card2 h3 { margin:0 0 6px; font-size:17px; } .card2 p { margin:2px 0; font-size:13.5px; color:var(--mut); }
.statline { display:flex; flex-wrap:wrap; gap:10px; margin:14px 0; }
.stat { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 16px; }
.stat b { font-size:22px; display:block; } .stat span { font-size:12.5px; color:var(--mut); }
table { width:100%; border-collapse:collapse; background:var(--card); font-size:13.5px; margin:10px 0 18px; }
th, td { border:1px solid var(--line); padding:7px 8px; vertical-align:top; text-align:left; }
th { background:#eef3f9; font-size:12.5px; text-transform:uppercase; letter-spacing:.03em; }
tr.detail td { background:#fbfcfe; font-size:13px; }
tr.detail p { margin:3px 0; }
.chip { display:inline-block; padding:1px 8px; border-radius:20px; font-size:11.5px; font-weight:700;
        text-transform:capitalize; color:#fff; }
.chip-high { background:var(--high); } .chip-medium { background:var(--med); } .chip-low { background:var(--low); }
.muted { color:var(--mut); } .missing { color:#b00020; font-weight:700; }
.prediction { background:#eef7ee; border-left:4px solid var(--high); padding:8px 10px; border-radius:4px; }
.flags { background:#fdf3e3; border-left:4px solid #d9930d; padding:6px 10px; border-radius:4px; }
.note { background:#eef3f9; border-left:4px solid var(--accent); padding:8px 12px; border-radius:4px; }
code { background:#eef3f9; padding:0 4px; border-radius:3px; font-size:12.5px; }
footer { max-width:1180px; margin:0 auto; padding:0 16px 34px; color:var(--mut); font-size:13px; }
.wrap { overflow-x:auto; }
"""

def match_rows(m):
    pick = E(m['pick']) if m.get('pick') else '<span class="muted">No pick — flagged</span>'
    if m.get('pick_probability') is not None:
        pick += f"<br><span class='muted'>{pct(m['pick_probability'],1)} model probability</span>"
    main = f"""<tr id="ev-{m['event_id']}">
<td>{E(str(m.get('date') or '—'))}</td>
<td>{E(m.get('competition') or '')}</td>
<td><b>{E(m['home'])}</b>{' vs <b>' + E(m['away']) + '</b>' if m.get('away') else ''}{'<br><span class=muted>' + E(m['venue']) + '</span>' if m.get('venue') else ''}</td>
<td>{pick}</td>
<td>{conf_chip(m['confidence'])}</td>
<td>{probs_cell(m)}</td>
<td>{lines_cell(m)}</td>
<td>{src_link(m)}</td>
</tr>"""
    detail_bits = []
    if m.get('expected_score'):
        detail_bits.append(f"<p><b>Model view:</b> {E(m['expected_score'])}</p>")
    if m.get('inputs_summary'):
        detail_bits.append(f"<p><b>Verified inputs:</b> {E(m['inputs_summary'])}</p>")
    if m.get('form_context'):
        detail_bits.append(f"<p><b>Form/context (verified):</b> {E(m['form_context'])}</p>")
    if m.get('prediction'):
        detail_bits.append(f"<p class='prediction'><b>Written prediction (high confidence):</b> {E(m['prediction'])}</p>")
    if m.get('flags'):
        fl = '<br>'.join('⚠ ' + E(f) for f in m['flags'] if f)
        if fl:
            detail_bits.append(f"<p class='flags'>{fl}</p>")
    status_line = {'modelled': 'Fully modelled from verified inputs.',
                   'qualitative': 'Qualitative pick only — numeric lines not originated (see inputs).',
                   'flagged': 'Flagged for review — no pick or lines originated.'}.get(m.get('status'), '')
    detail_bits.append(f"<p class='muted'>Status: {E(m.get('status',''))}. {status_line} OLBG event ID {m['event_id']}.</p>")
    detail = f"<tr class='detail'><td colspan='8'>{''.join(detail_bits)}</td></tr>"
    return main + '\n' + detail

def outrights_table(outrights):
    if not outrights:
        return ''
    rows = []
    for o in outrights:
        prob = pct(o['pick_probability'], 1) if o.get('pick_probability') is not None else '—'
        rows.append(f"""<tr id="ev-{o['event_id']}">
<td>{E(str(o.get('date') or '—'))}</td><td>{E(o.get('competition') or '')}</td>
<td><b>{E(o.get('pick') or '')}</b></td><td>{prob}</td><td>{conf_chip(o['confidence'])}</td>
<td>{E(o.get('basis') or '')}</td><td>{src_link(o)}</td></tr>""")
    return f"""<h2>Tournament outrights (ante-post)</h2>
<p class="muted">Outright picks are always labelled <b>low</b> confidence: fields are large and, except where a
documented ratings model exists (golf), no precise probability is originated.</p>
<div class="wrap"><table><thead><tr><th>Date</th><th>Competition</th><th>Model pick</th><th>Model prob.</th>
<th>Confidence</th><th>Basis (verified)</th><th>Source</th></tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table></div>"""

def sport_page(sport, sports):
    ms = sport['matches']
    body = [f"<h1>{E(sport['sport'])}</h1>"]
    nhigh = sum(1 for m in ms if m['confidence'] == 'high')
    body.append(f"<p>{len(ms)} upcoming matches · {len(sport.get('outrights', []))} outrights · "
                f"{nhigh} high-confidence picks. All lines below are <b>originated by our model</b> from the "
                f"verified inputs shown under each match — they are not bookmaker prices. "
                f"See <a href='../methodology.html'>Methodology</a> for the formulas.</p>")
    z = zero_check(sport)
    if z and not ms:
        if isinstance(z, dict):
            body.append(f"<div class='note'><b>No OLBG-listed matches.</b> {E(z.get('finding',''))} "
                        f"<br>Source: <a href='{E(z.get('source_url',''))}' target='_blank' rel='noopener'>official calendar</a></div>")
        else:
            body.append(f"<div class='note'><b>No OLBG-listed matches.</b> {E(str(z))}</div>")
    if z and ms and sport['slug'] == 'rugby-league':
        finding = z.get('finding', '') if isinstance(z, dict) else str(z)
        body.append(f"<div class='note'>{E(finding)}</div>")
    if ms:
        rows = '\n'.join(match_rows(m) for m in ms)
        body.append(f"""<h2>Upcoming matches &amp; originated lines</h2>
<div class="wrap"><table><thead><tr><th>Date</th><th>Competition</th><th>Match</th><th>Model pick</th>
<th>Confidence</th><th>Win probs (H/D/A)</th><th>Originated lines (modelled)</th><th>Official source</th></tr></thead>
<tbody>{rows}</tbody></table></div>""")
    body.append(outrights_table(sport.get('outrights', [])))
    return page(f"{sport['sport']} — Modelled Lines", '\n'.join(body), sports, depth=1)

def index_page(sports):
    total_m = sum(len(s['matches']) for s in sports)
    total_o = sum(len(s.get('outrights', [])) for s in sports)
    highs = [(s, m) for s in sports for m in s['matches'] if m['confidence'] == 'high']
    flagged_n = sum(1 for s in sports for m in s['matches'] if m['status'] != 'modelled' or m.get('flags'))
    cards = []
    for s in sports:
        h = sum(1 for m in s['matches'] if m['confidence'] == 'high')
        md = sum(1 for m in s['matches'] if m['confidence'] == 'medium')
        lo = sum(1 for m in s['matches'] if m['confidence'] == 'low')
        cards.append(f"""<div class="card2"><h3><a href="sports/{s['slug']}.html">{E(s['sport'])}</a></h3>
<p>{len(s['matches'])} matches · {len(s.get('outrights', []))} outrights</p>
<p>{conf_chip('high')} {h} &nbsp; {conf_chip('medium')} {md} &nbsp; {conf_chip('low')} {lo}</p></div>""")
    rows = []
    for s, m in sorted(highs, key=lambda x: -(x[1]['pick_probability'] or 0)):
        rows.append(f"""<tr><td><a href="sports/{s['slug']}.html">{E(s['sport'])}</a></td>
<td>{E(str(m.get('date') or ''))}</td>
<td><a href="sports/{s['slug']}.html#ev-{m['event_id']}">{E(m['home'])} vs {E(m['away'] or '')}</a></td>
<td><b>{E(m['pick'])}</b></td><td>{pct(m['pick_probability'],1)}</td><td>{conf_chip('high')}</td></tr>""")
    body = f"""<h1>Upcoming matches &amp; modelled lines — every OLBG sport in scope</h1>
<p>This dashboard reverse-engineers <b>OLBG.com</b>'s sports coverage and rebuilds it from scratch: every upcoming
match OLBG lists across the 17 in-scope sports, each fixture <b>verified line-by-line against official sources</b>,
with <b>original betting lines originated by our own statistical models</b> (never copied from bookmakers or tipsters)
and a picked winner labelled <b>low / medium / high</b> confidence. High-confidence picks carry a unique written
prediction built only from verified information. Anything that could not be verified is left blank and published on the
<a href="flagged.html">Flagged for Review</a> page — nothing is inferred or filled in.</p>
<p class="note"><b>Scope:</b> all OLBG sports <i>excluding</i> football/soccer, horse racing, specials, American football,
boxing (incl. UFC/MMA), cycling and hurling, as briefed. Coverage = events present in OLBG's server-rendered tipster
feed on 21 October 2026 (see <a href="methodology.html">Methodology</a> and <a href="findings.html">Findings</a>).</p>
<div class="statline">
<div class="stat"><b>17</b><span>sports covered</span></div>
<div class="stat"><b>{total_m}</b><span>upcoming matches verified</span></div>
<div class="stat"><b>{total_o}</b><span>tournament outrights</span></div>
<div class="stat"><b>{len(highs)}</b><span>high-confidence picks</span></div>
<div class="stat"><b>{flagged_n}</b><span>rows with flags / partial data</span></div>
</div>
<h2>Sports</h2>
<div class="cards">{''.join(cards)}</div>
<h2>High-confidence picks (with written predictions)</h2>
<p>High confidence = model probability ≥ 70% from current, official inputs with adequate sample size.
Click a match for full lines, verified inputs and the written prediction.</p>
<div class="wrap"><table><thead><tr><th>Sport</th><th>Date</th><th>Match</th><th>Pick</th><th>Model prob.</th><th>Confidence</th></tr></thead>
<tbody>{chr(10).join(rows)}</tbody></table></div>
<h2>How to read the sport pages</h2>
<ul>
<li><b>Model pick / Confidence</b> — the selection our formula favours, and its tier (rules on the Methodology page).</li>
<li><b>Win probs (H/D/A)</b> — modelled home/draw/away probabilities (draw shown only where the sport allows one).</li>
<li><b>Originated lines</b> — our fair handicap and totals lines (the line at which both sides are ~50/50 in the model),
market win probabilities and fair decimal equivalents (1 ÷ probability, no bookmaker margin).</li>
<li><b>Verified inputs</b> under each match list exactly what the number was computed from, with an official source link on every row.</li>
<li>Blank lines mean the verified data did not support a number — see <a href="flagged.html">Flagged for Review</a>.</li>
</ul>"""
    return page('OLBG Modelled Lines Dashboard', body, sports, active='index.html')

METHODOLOGY = """<h1>Methodology</h1>
<h2>1. Reverse-engineering OLBG</h2>
<p>OLBG.com organises tips by sport under <code>/betting-tips/{Sport}/{id}</code> (24 sport sections). We mapped the full
structure (sport IDs, event pages, market labels, "most tipped" summaries) into <code>data/olbg-structure.json</code>.
The public event lists are server-rendered tipster feeds: OLBG only surfaces events its tipsters have tipped, and deeper
events hide behind a JavaScript "Load More Tips" control. <b>Coverage therefore equals the server-rendered feed visible on
21 October 2026</b>; the gap this creates is analysed in <a href="findings.html">Findings</a>. Seven sections were excluded
by the brief: Football (1), Horse Racing (2), Specials (6), American Football (11), Boxing incl. UFC/MMA (16),
Cycling (17) and Hurling (26), leaving <b>17 in-scope sports</b>.</p>
<h2>2. Verification (line-by-line, official sources only)</h2>
<p>Every fixture, date, venue, participant and rating input was checked against the sport's official source — e.g. ATP/WTA
official draws and the 19 Oct 2026 rankings; EuroLeague/EuroCup/NBA official standings; EHF and national handball tables;
LNR and United Rugby Championship tables; PDC Order of Merit; ICC team ratings; NHL official API; MLB Stats API;
Formula1.com results; OWGR event fields; county-board GAA fixtures. Each row on this site links to its official source.
Anything that could not be confirmed was left blank and flagged (see <a href="flagged.html">Flagged for Review</a>).
OLBG's own kick-off times were repeatedly found to be timezone-shifted, so official dates/venues are published instead.</p>
<h2>3. Originated lines — the models</h2>
<p>No bookmaker or tipster price was copied. Each sport uses a documented mechanical model
(<code>tools/model.py</code>) applied only to verified inputs:</p>
<table><thead><tr><th>Sport</th><th>Verified inputs</th><th>Model</th><th>Markets originated</th></tr></thead><tbody>
<tr><td>Tennis</td><td>Official ATP/WTA ranking points (19 Oct 2026)</td><td>Match prob = logistic on log points ratio (k=1.15); inverted to set prob, then game prob (tiebreak modelled), giving games distribution</td><td>Win Match, Set Betting, 1st Set Winner, Total Games</td></tr>
<tr><td>Basketball</td><td>Official PF/PA (EuroLeague/EuroCup); NBA 2025-26 W-L; KBL W-L</td><td>Shrunk attack/defence Poisson (k=3/2), home ×1.04, OT split; NBA/KBL: shrunk win% → Normal margin</td><td>Money Line, Point Spread, Game Totals (NBA/KBL totals blank — no verified scoring inputs)</td></tr>
<tr><td>Handball</td><td>Official GF/GA tables (EHF CL, Danish; Swedish/Norwegian partial)</td><td>Shrunk Poisson, home ×1.05, draw from Skellam P(0)</td><td>Money Line (3-way), Handicap, Totals</td></tr>
<tr><td>Rugby Union</td><td>Official PF/PA (Top 14, Pro D2, URC)</td><td>Shrunk attack/defence expected scores (k=2, home ×1.10); probabilities from Normal margin (SD 15) / total (SD 13) because 3/5/7-point scoring makes Poisson under-dispersed</td><td>To Win (3-way), Handicap, Totals</td></tr>
<tr><td>Volleyball</td><td>Official set records; Italy rally points</td><td>Shrunk set-win rates → log5 set prob (home logit +0.12) → race-to-3 distribution</td><td>Win Match, Set Handicap, Total Sets, Total Points (Italy)</td></tr>
<tr><td>Darts</td><td>Official PDC Order of Merit (2-yr money)</td><td>Leg prob = logistic on log-money gap (k=0.30); best of 11 legs</td><td>Win Match, Leg Handicap, Total Legs</td></tr>
<tr><td>Snooker</td><td>Official tournament seedings (= world rankings)</td><td>Frame prob = logistic on log-rank gap (k=0.40); first to 4</td><td>Win Match, Frame Handicap, Total Frames, correct-score probabilities</td></tr>
<tr><td>Cricket</td><td>ICC team ratings (Oct 2026)</td><td>Logistic on rating diff (+6 ODI / +8 T20I home adj., none at neutral venues)</td><td>Win Match only (no verified basis for runs totals)</td></tr>
<tr><td>Ice Hockey</td><td>Official GF/GA (NHL, ICEHL; SHL cross-checked secondary)</td><td>Shrunk Poisson (k=5), home ×1.045, OT by λ-share; totals include OT decider</td><td>Money Line (incl. OT), Puck Line −1.5, Game Totals</td></tr>
<tr><td>Baseball</td><td>MLB Stats API: W-L, RS/RA (all 30 teams)</td><td>Money Line: log5 on blended actual/Pythagorean win% + home shift; Run Line/Totals: Poisson run model vs league avg 4.481</td><td>Money Line, Run Line −1.5, Game Totals</td></tr>
<tr><td>Gaelic Football</td><td>Verified knockout margins from official county boards</td><td>Expected margin (halved, capped; +1 reigning champion) → Normal(m, SD 8); draw = mass on 0</td><td>Match Winner (3-way), Handicap (no totals)</td></tr>
<tr><td>Golf (outrights)</td><td>OWGR SG World Rating + Performance Points</td><td>SGWR shrunk by PP sample → softmax (σ=0.6) over extracted contenders (3 events); other events: verified merit-order/OWGR-leading pick, no probability</td><td>Win Tournament</td></tr>
<tr><td>Motor Racing / Rugby League outrights</td><td>Official standings / 2026 champions</td><td>Leader / reigning-champion basis, no precise probability (large fields)</td><td>Win Race / Win Tournament</td></tr>
<tr><td>Greyhounds</td><td>GBGB tracks confirmed; no official form lines extractable</td><td>None — no picks or lines originated; copying tipster verdicts rejected</td><td>— (Flagged for Review)</td></tr>
</tbody></table>
<p>Handicap and totals lines shown are <b>fair (50/50) half-point lines</b> computed from each model's score distribution;
"fair odds" are 1 ÷ probability with no overround. Expected scores are model means, not predictions of exact results.</p>
<h2>4. Confidence tiers</h2>
<ul>
<li><b>High</b>: model probability ≥ 70% <i>and</i> inputs are current-season official data with an adequate sample
(≥5 team games, or complete official ranking lists).</li>
<li><b>Medium</b>: probability 57–69.9%, or capped for prior-season (NBA), secondary-source (SHL, Swedish/Norwegian handball)
or small-sample inputs (EuroCup, URC, early-season volleyball, EHF group stage, Gaelic finals).</li>
<li><b>Low</b>: probability &lt; 57%, qualitative picks without numeric inputs, and all tournament outrights.</li>
</ul>
<h2>5. Known limitations</h2>
<ul>
<li>Models use standings-level inputs only — no injuries, line-ups, weather or scheduling fatigue (noted where material, e.g. MLB probables unannounced).</li>
<li>Poisson/independence assumptions understate tail risk; ranking-points models lag abrupt form changes (flagged per match where verified evidence shows this, e.g. darts' Zonneveld, snooker's round-1 upset wave).</li>
<li>Early-season samples are shrunk toward league averages but remain noisy — hence the confidence caps.</li>
</ul>"""

FINDINGS = """<h1>Analysis &amp; Findings</h1>
<h2>How OLBG coverage actually works</h2>
<ul>
<li><b>Tipster-driven, not fixture-driven.</b> OLBG lists events its tipsters have tipped. Sports with thin tipster
communities show "No tips found" even mid-season, so the public feed materially under-covers the real sporting calendar.</li>
<li><b>Server-rendered window.</b> Only the first page of events is server-rendered; more sit behind a JavaScript
"Load More Tips" button. Any third-party scrape of OLBG inherits this truncation.</li>
<li><b>Timezone-shifted start times.</b> Across several sports, OLBG's displayed times did not match official schedules
(consistently shifted), and at least one fixture date was flatly wrong (Waterford SFC final: OLBG 1 Nov, official 25 Oct).
We publish official dates/venues everywhere.</li>
<li><b>Stale labels.</b> OLBG uses outdated or loose competition names (e.g. "Austria EHL" for the ICE Hockey League;
"KCC Egis" for Busan KCC). Official names are used on this site with the OLBG label noted.</li>
</ul>
<h2>Coverage gaps found by cross-checking official calendars</h2>
<ul>
<li><b>Rugby league:</b> OLBG lists zero matches while the 2026 Rugby League World Cup is actively running
(15 Oct – 15 Nov 2026; Australia beat New Zealand 24–22 in the opener). Only 2027 outrights are offered. This is the
single largest gap found. Per scope we originate no non-OLBG matches; the outrights are covered on the
<a href="sports/rugby-league.html">Rugby League page</a>.</li>
<li><b>Aussie rules:</b> the men's AFL season genuinely ended 10 Oct, but AFLW 2026 is mid-season (Round 11 on
23–25 Oct) and entirely absent from OLBG.</li>
<li><b>eSports:</b> League of Legends Worlds 2026 is running in the US (Swiss Stage from 23 Oct) with no OLBG coverage at all.</li>
</ul>
<h2>Sport-specific findings</h2>
<ul>
<li><b>Snooker (Northern Ireland Open):</b> round 1 produced an exceptional upset wave — Trump, O'Sullivan, Murphy,
Selby, Robertson, Zhao and others all lost in best-of-7 matches. Our seeding-based model still produces high-confidence
favourites in round 2; the variance warning is flagged on every tie.</li>
<li><b>Darts:</b> European Championship seedings (Euro Tour order) diverge sharply from world rankings — world No.1
Luke Littler is only the 11th seed, and Niels Zonneveld (world 29) is seeded 4th after winning the Dutch Darts
Championship on 18 Oct. Our model deliberately uses 2-year world-ranking money; the form-lag is flagged.</li>
<li><b>Tennis:</b> ranking-points models produce eye-catching prices where reputation and points diverge — e.g. former
world No.7 David Goffin (now #657, retiring season) is modelled as a heavy underdog against lucky loser Rémy Bertola.
The caveat is written into that prediction rather than the number being quietly adjusted.</li>
<li><b>Greyhound racing:</b> no official racecard with form lines/calculated times could be extracted from the GBGB
(the official card routes returned 404s), and the only available "verdicts" were tipster opinions we refuse to copy.
All six races are therefore published with no pick, with a documented model ready (softmax over best recent calculated
time, τ=0.12s) should official racecard PDFs be supplied.</li>
<li><b>Basketball:</b> official sources vary in completeness — EuroLeague/EuroCup publish full PF/PA, while the BCL and
KBL public standings expose W-L only, so totals there are blank rather than estimated. Two "home" teams (Hapoel Tel
Aviv in Sofia, one EuroCup side in Belgrade) are not actually playing at home; home advantage was reduced/removed accordingly.</li>
<li><b>Baseball:</b> OLBG's single listed game is World Series Game 1 (Tampa Bay @ Milwaukee). Probable pitchers were
not announced at verification time, so the line is team-strength only and flagged as such.</li>
<li><b>Golf:</b> three of ten OLBG-listed tournaments returned "NO TOURNAMENT DATA" from the OWGR system; picks there
rest on verified merit-order information and are flagged accordingly.</li>
<li><b>Motor racing:</b> OLBG's "Without Antonelli" market only makes sense against the official table: Kimi Antonelli
leads the Drivers' Championship by 102 points with seven wins — yet OLBG's most-tipped USA GP winner was Verstappen,
the in-form driver (wins in Bahrain and Singapore). Our pick follows the season-long data with the form caveat stated.</li>
</ul>
<h2>Where the model and the crowd disagree (illustrative)</h2>
<p>Because our lines are originated independently, divergences from tipster sentiment are expected — e.g. the model
makes Panathinaikos a 23.5-point favourite over Baskonia (96%) purely from six rounds of official PF/PA, and rates
Provence Rugby 92% at home to Béziers. These are statements about the verified inputs, not about market prices.</p>"""

def flagged_page(sports):
    rows = []
    for s in sports:
        for m in s['matches']:
            issues = [f for f in (m.get('flags') or []) if f]
            if m['status'] == 'qualitative':
                issues.append('Qualitative pick only — numeric lines not originated.')
            if m['status'] == 'flagged':
                issues.append('No pick or lines originated.')
            if not issues:
                continue
            match_txt = f"{m['home']} vs {m['away']}" if m.get('away') else m['home']
            rows.append(f"""<tr><td><a href="sports/{s['slug']}.html#ev-{m['event_id']}">{E(s['sport'])}</a></td>
<td>{E(match_txt)}<br><span class="muted">{E(m.get('competition') or '')} · {E(str(m.get('date') or ''))}</span></td>
<td>{E(m['status'])}</td><td>{'<br>'.join('⚠ ' + E(i) for i in issues)}</td><td>{src_link(m)}</td></tr>""")
        for o in s.get('outrights', []):
            issues = [f for f in (o.get('flags') or []) if f]
            if not issues:
                continue
            rows.append(f"""<tr><td><a href="sports/{s['slug']}.html#ev-{o['event_id']}">{E(s['sport'])}</a></td>
<td>{E(o.get('competition') or '')} (outright)</td><td>outright</td>
<td>{'<br>'.join('⚠ ' + E(i) for i in issues)}</td><td>{src_link(o)}</td></tr>""")
    body = f"""<h1>Flagged for Review</h1>
<p>Every row below has an irregularity, a data gap, or only partially verified inputs. Per project policy, unverified
values were <b>left blank rather than inferred</b>, confidence was capped, and the item published here for human review.
Flagged items do not block publication of the rest of the dashboard.</p>
<div class="wrap"><table><thead><tr><th>Sport</th><th>Event</th><th>Status</th><th>Issue(s)</th><th>Official source</th></tr></thead>
<tbody>{chr(10).join(rows)}</tbody></table></div>
<p class="muted">{len(rows)} flagged rows. Sport-level coverage gaps (Rugby League World Cup, AFLW, LoL Worlds) are
documented in <a href="findings.html">Findings</a> and on the relevant sport pages.</p>"""
    return page('Flagged for Review', body, sports, active='flagged.html')

def validate(sports):
    problems = []
    for s in sports:
        for m in s['matches']:
            if not m.get('source_url'):
                problems.append(f"{s['sport']} ev {m['event_id']}: missing source_url")
            if m['confidence'] == 'high' and not m.get('prediction'):
                problems.append(f"{s['sport']} ev {m['event_id']}: high confidence without prediction")
            if m.get('prediction') and len(m['prediction'].split()) < 30:
                problems.append(f"{s['sport']} ev {m['event_id']}: prediction under 30 words")
        for o in s.get('outrights', []):
            if not o.get('source_url'):
                problems.append(f"{s['sport']} outright {o.get('event_id')}: missing source_url")
    return problems

def linkcheck():
    broken = []
    for root, _, files in os.walk(DOCS):
        for fn in files:
            if not fn.endswith('.html'):
                continue
            path = os.path.join(root, fn)
            html = open(path).read()
            for href in re.findall(r'(?:href|src)="([^"]+)"', html):
                if href.startswith(('http://', 'https://', 'mailto:', '#')):
                    continue
                target = href.split('#')[0]
                if not target:
                    continue
                full = os.path.normpath(os.path.join(root, target))
                if not os.path.exists(full):
                    broken.append(f"{os.path.relpath(path, DOCS)} -> {href}")
                elif '#' in href:
                    anchor = href.split('#')[1]
                    if f'id="{anchor}"' not in open(full).read():
                        broken.append(f"{os.path.relpath(path, DOCS)} -> {href} (missing anchor)")
    return broken

if __name__ == '__main__':
    sports = load_matches()
    problems = validate(sports)
    if problems:
        print('VALIDATION PROBLEMS:')
        [print(' -', p) for p in problems]
        sys.exit(1)
    open(os.path.join(ASSETS, 'style.css'), 'w').write(CSS)
    open(os.path.join(DOCS, '.nojekyll'), 'w').write('')
    open(os.path.join(DOCS, 'index.html'), 'w').write(index_page(sports))
    for s in sports:
        open(os.path.join(SPORTS_DIR, s['slug'] + '.html'), 'w').write(sport_page(s, sports))
    open(os.path.join(DOCS, 'methodology.html'), 'w').write(
        page('Methodology', METHODOLOGY, sports, active='methodology.html'))
    open(os.path.join(DOCS, 'findings.html'), 'w').write(
        page('Findings', FINDINGS, sports, active='findings.html'))
    open(os.path.join(DOCS, 'flagged.html'), 'w').write(flagged_page(sports))
    broken = linkcheck()
    total_m = sum(len(s['matches']) for s in sports)
    total_o = sum(len(s.get('outrights', [])) for s in sports)
    print(f"built: index + {len(sports)} sport pages + methodology/findings/flagged")
    print(f"matches={total_m} outrights={total_o}")
    if broken:
        print('BROKEN LINKS:')
        [print(' -', b) for b in broken]
        sys.exit(1)
    print('link check: OK (no broken internal links or anchors)')

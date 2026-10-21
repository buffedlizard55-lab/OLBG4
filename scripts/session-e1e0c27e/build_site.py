#!/usr/bin/env python3
"""Render session-e1e0c27e/ audit pages from the JSON produced by audit.py."""
import json, os, html
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
D = os.path.join(ROOT, 'session-e1e0c27e', 'data')
OUT = os.path.join(ROOT, 'session-e1e0c27e')
rows = json.load(open(os.path.join(D, 'audit_rows.json')))
summary = json.load(open(os.path.join(D, 'summary.json')))
cross = json.load(open(os.path.join(D, 'crossbuild.json')))
checks = json.load(open(os.path.join(D, 'spot_checks.json')))
findings = json.load(open(os.path.join(D, 'findings.json')))

BUILDS = {
    'A': ('Build A', 'docs/', '../docs/'),
    'B': ('Build B', 'session-7114b6a1/', '../session-7114b6a1/'),
    'C': ('Build C', 'session-74f9613e/', '../session-74f9613e/'),
    'D': ('Build D (root hub)', '/', '../'),
    'E': ('Build E', 'session-4afef1af/', '../session-4afef1af/'),
    'G': ('Build G', 'session-6e0f382d/', '../session-6e0f382d/'),
}
e = lambda s: html.escape(str(s if s is not None else ''))

CSS = """
:root{--bg:#f6f8fa;--card:#fff;--ink:#1f2937;--mut:#6b7280;--line:#e5e7eb;--ok:#047857;--okbg:#ecfdf5;--warn:#b45309;--warnbg:#fffbeb;--bad:#b91c1c;--badbg:#fef2f2;--info:#1d4ed8;--infobg:#eff6ff;--brand:#7c2d12}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
a{color:#1d4ed8}header{background:#fff;border-bottom:1px solid var(--line)}.wrap{max-width:1280px;margin:0 auto;padding:0 18px}
.head{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;padding:12px 0}.brand{font-weight:700;color:var(--brand);text-decoration:none;font-size:1.05rem}
nav a{display:inline-block;padding:6px 10px;margin:2px;border-radius:8px;text-decoration:none;color:var(--ink);border:1px solid transparent}nav a.active,nav a:hover{background:var(--bg);border-color:var(--line)}
nav a.flag{color:var(--bad);font-weight:600}main{padding:18px 0 40px}h1{margin:.2em 0 .3em;font-size:1.6rem}h2{margin:1.4em 0 .4em;font-size:1.2rem}.lead{color:var(--mut);margin:0 0 14px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .big{font-size:1.9rem;font-weight:700;line-height:1.1}.kpi small{color:var(--mut)}
.notice{border-radius:10px;padding:12px 14px;margin:12px 0;border:1px solid}.notice.bad{background:var(--badbg);border-color:#fecaca}.notice.warn{background:var(--warnbg);border-color:#fde68a}.notice.info{background:var(--infobg);border-color:#bfdbfe}
.table-wrap{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:12px}table{border-collapse:collapse;width:100%;font-size:.9rem}th,td{padding:8px 10px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}th{background:#f9fafb;position:sticky;top:0;cursor:pointer;white-space:nowrap}
tr:hover td{background:#fafafa}.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:.78rem;font-weight:600;white-space:nowrap}
.b-ok{background:var(--okbg);color:var(--ok)}.b-warn{background:var(--warnbg);color:var(--warn)}.b-bad{background:var(--badbg);color:var(--bad)}.b-info{background:var(--infobg);color:var(--info)}.b-mut{background:#f3f4f6;color:var(--mut)}
.mono{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:.85em}.muted{color:var(--mut)}.small{font-size:.85rem}
.controls{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}.controls input,.controls select{padding:7px 10px;border:1px solid var(--line);border-radius:8px;font:inherit}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:.85rem;padding:14px 0}
details summary{cursor:pointer;color:#1d4ed8}ul.src{margin:4px 0 0 16px;padding:0}ul.src li{word-break:break-all}
"""
JS = """
document.querySelectorAll('table[data-filterable]').forEach(function(t){
 var box=t.closest('.table-wrap');var ctl=document.createElement('div');ctl.className='controls';
 var inp=document.createElement('input');inp.placeholder='Filter rows…';ctl.appendChild(inp);
 var cnt=document.createElement('span');cnt.className='muted small';ctl.appendChild(cnt);box.parentNode.insertBefore(ctl,box);
 var rows=[].slice.call(t.tBodies[0].rows);function upd(){var q=inp.value.toLowerCase();var n=0;rows.forEach(function(r){var s=r.textContent.toLowerCase().indexOf(q)>-1;r.style.display=s?'':'none';if(s)n++;});cnt.textContent=n+' of '+rows.length+' rows';}
 inp.addEventListener('input',upd);upd();
 [].forEach.call(t.tHead.rows[0].cells,function(th,i){th.addEventListener('click',function(){var dir=th.dataset.dir==='asc'?'desc':'asc';th.dataset.dir=dir;
  rows.sort(function(a,b){var x=a.cells[i].textContent.trim(),y=b.cells[i].textContent.trim();var nx=parseFloat(x),ny=parseFloat(y);if(!isNaN(nx)&&!isNaN(ny)){x=nx;y=ny}return (x>y?1:x<y?-1:0)*(dir==='asc'?1:-1)});
  rows.forEach(function(r){t.tBodies[0].appendChild(r)});});});
});
"""

NAV = [('index.html', 'Overview'), ('rows.html', 'All rows'), ('builds.html', 'By build'), ('spot-checks.html', 'Spot checks'),
       ('crossbuild.html', 'Cross-build'), ('method.html', 'Method'), ('flagged.html', 'Flagged for Review')]

def page(title, active, body, desc=''):
    nav = ''.join(f'<a href="{h}" class="{"active" if h == active else ""}{" flag" if h == "flagged.html" else ""}">{t}</a>' for h, t in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG4 audit</title><meta name="description" content="{e(desc or title)}"><style>{CSS}</style></head><body>
<header><div class="wrap head"><a class="brand" href="index.html">OLBG4 · Board I audit</a><nav>{nav}<a href="../">← Portal</a></nav></div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">Independent cross-build audit (Board I) by session <span class="mono">arena/e1e0c27e-olbg4</span> · generated {e(summary['generated_utc'])} · data in <a href="data/audit_rows.json">audit_rows.json</a>, <a href="data/summary.json">summary.json</a>, <a href="data/crossbuild.json">crossbuild.json</a>, <a href="data/spot_checks.json">spot_checks.json</a>, <a href="data/findings.json">findings.json</a> · script <span class="mono">scripts/session-e1e0c27e/</span>. This page audits the other builds; it originates no lines of its own.</div></footer>
<script>{JS}</script></body></html>"""

def verdict_badge(v):
    if v.startswith('official'):
        return f'<span class="badge b-ok">{e(v)}</span>'
    if v.startswith('OLBG'):
        return f'<span class="badge b-warn">{e(v)}</span>'
    return f'<span class="badge b-bad">{e(v)}</span>'

def src_cell(r):
    items = []
    for s in r['source_classes']:
        cls = {'official': 'b-ok', 'olbg': 'b-warn', 'secondary': 'b-bad', 'none': 'b-mut'}[s['class']]
        dom = s['url'].split('/')[2].removeprefix('www.') if '://' in s['url'] else s['url']
        items.append(f'<a href="{e(s["url"])}" target="_blank" rel="noopener">{e(dom)}</a> <span class="badge {cls}">{s["class"]}</span>' + (f' <span class="muted small">{e(s["note"])}</span>' if s['note'] else ''))
    return '<br>'.join(items) or '<span class="badge b-mut">none</span>'

def rows_table(rs, show_build=True):
    h = ['<div class="table-wrap"><table data-filterable="1"><thead><tr>' + ('<th>Build</th>' if show_build else '') +
         '<th>Row id</th><th>Sport</th><th>Event</th><th>Date</th><th>Build\'s own status</th><th>Pick</th><th>Conf.</th><th>Pred. words</th><th>Source link(s) &amp; class</th><th>Audit verdict</th></tr></thead><tbody>']
    for r in rs:
        own = e(r['own_status']) + (' <span class="badge b-warn">flagged</span>' if r['own_flag'] else '')
        bl = BUILDS[r['build']]
        h.append('<tr>' + (f'<td><a href="{bl[2]}">{bl[0]}</a></td>' if show_build else '') +
                 f'<td class="mono">{e(r["id"])}</td><td>{e(r["sport"])}</td><td>{e(r["event"])}<div class="muted small">{e(r["competition"])}</div></td><td class="mono">{e(r["date"])}</td>'
                 f'<td>{own}</td><td>{e(r["pick"])}</td><td>{e(r["confidence"])}</td><td>{r["prediction_words"] or ""}</td><td>{src_cell(r)}</td><td>{verdict_badge(r["verdict"])}</td></tr>')
    h.append('</tbody></table></div>')
    return ''.join(h)

# ---------- Overview ----------
tv = summary['total_verdicts']
n_off = tv.get('official source present', 0); n_olbg = tv.get('OLBG only — no official fixture source', 0); n_sec = tv.get('secondary source only — no official source', 0)
n_checks = len(checks['checks']); res = Counter(c['result'] for c in checks['checks'])
sev = Counter(f['severity'] for f in findings['findings'])
body = f"""
<h1>Independent audit of the published builds (A–E and G)</h1>
<p class="lead">Every table row published by builds A, B, C, D, E and G was read from its data file, its source link classified (official governing body / league feed, OLBG aggregator, or secondary media), and a sample of rows re-checked against official pages with links for manual review. Nothing was inferred: where a build's value could not be confirmed it is listed here as <em>unverified</em>, not corrected.</p>
<div class="grid">
<div class="card kpi"><div class="big">{summary['total_rows']}</div><small>rows audited across 6 builds</small></div>
<div class="card kpi"><div class="big" style="color:var(--ok)">{n_off}</div><small>rows with an official source link</small></div>
<div class="card kpi"><div class="big" style="color:var(--warn)">{n_olbg}</div><small>rows sourced to OLBG only</small></div>
<div class="card kpi"><div class="big" style="color:var(--bad)">{n_sec}</div><small>rows with secondary source only</small></div>
<div class="card kpi"><div class="big">{n_checks}</div><small>row-level spot checks ({res.get('confirmed',0)} confirmed · {res.get('partial',0)} partial · {res.get('contradicted',0)} contradicted)</small></div>
<div class="card kpi"><div class="big">{summary['cross_build']['fixtures_in_2_or_more_builds']}</div><small>fixtures in 2+ builds ({summary['cross_build']['pick_conflicts']} with opposite picks)</small></div>
<div class="card kpi"><div class="big" style="color:var(--bad)">{len(findings['findings'])}</div><small>findings ({sev.get('high',0)} high · {sev.get('medium',0)} medium · {sev.get('low',0)} low)</small></div>
</div>
<div class="notice bad"><b>Headline finding.</b> The root hub (Build D) — the first thing a visitor sees — marks 34 of its 66 rows <em>verified</em> although their only source is ESPN, Wikipedia, BBC, Sky, a betting blog or OLBG, and five of its fifteen high-confidence predictions contain form or fixture claims that the league's own pages contradict (Sharks "0-4" v NHL 4-4-1; Bruins "1-3" v NHL 7-2-0; "seven-game ALCS" v six; Efes/Beşiktaş records inverted; a "Pacific Championships" fixture in a World Cup year). Details with links: <a href="flagged.html">Flagged for Review</a> and <a href="spot-checks.html">Spot checks</a>. Builds A, C, E and G link an official page on every row; Build B links OLBG on every row and official pages only inside its nine written predictions. <b>Second finding (post-rebase):</b> a later session overwrote Build A's data (144 → 137 rows, Gaelic/golf/greyhound/motor-racing pages deleted) and Build B's predictions file with templated texts — one of which compares Boston with the wrong opponent — see <a href="flagged.html#F-11">F-11</a> and <a href="flagged.html#F-12">F-12</a>.</div>
{''.join(f'<div class="notice info small">{e(n)}</div>' for n in summary.get('notes', []))}
<h2>Per-build summary</h2>
<div class="table-wrap"><table><thead><tr><th>Build</th><th>Rows</th><th>Official source on row</th><th>OLBG only</th><th>Secondary only</th><th>High-conf. rows</th><th>High predictions &lt;30 words</th><th>Self-marked verified without official source</th><th>Confidence mix</th></tr></thead><tbody>"""
for b, (name, path, rel) in BUILDS.items():
    s = summary['builds'][b]; v = s['verdicts']
    body += f"""<tr><td><a href="{rel}">{name}</a><div class="muted small mono">{path}</div></td><td>{s['rows']}</td><td>{v.get('official source present',0)}</td><td>{v.get('OLBG only — no official fixture source',0)}</td><td>{v.get('secondary source only — no official source',0)}</td><td>{s['high_confidence_rows']}</td><td>{len(s['high_predictions_under_30_words'])}</td><td>{len(s['rows_self_marked_verified_without_official_source'])}</td><td class="small">{e(', '.join(f'{k} {v}' for k,v in s['confidence_mix'].items()))}</td></tr>"""
body += """</tbody></table></div>
<h2>How to read this site</h2>
<ul>
<li><a href="rows.html">All rows</a> — one line per published row across all builds, with its source link, the link's classification and the audit verdict. Filter by build id, sport or domain.</li>
<li><a href="builds.html">By build</a> — the same rows grouped per build with the domain breakdown.</li>
<li><a href="spot-checks.html">Spot checks</a> — rows re-read against the official page, with what the build says, what the source says, and the link.</li>
<li><a href="crossbuild.html">Cross-build</a> — fixtures that appear in more than one build, and where the builds' picks disagree.</li>
<li><a href="flagged.html">Flagged for Review</a> — the irregularity register for the user, with the links needed to confirm each item.</li>
</ul>"""
open(os.path.join(OUT, 'index.html'), 'w').write(page('Overview', 'index.html', body, 'Independent audit of all OLBG4 builds'))

# ---------- All rows ----------
body = f"<h1>All {len(rows)} published rows</h1><p class=\"lead\">Source classes: <span class=\"badge b-ok\">official</span> governing body / league / official data feed · <span class=\"badge b-warn\">olbg</span> OLBG event page (aggregator) · <span class=\"badge b-bad\">secondary</span> media, Wikipedia, stats or ticket sites. The verdict is mechanical: a row passes if at least one of its links is official. \"Build's own status\" is what the build itself published for the row.</p>" + rows_table(rows)
open(os.path.join(OUT, 'rows.html'), 'w').write(page('All rows', 'rows.html', body))

# ---------- By build ----------
body = '<h1>Rows by build</h1>'
for b, (name, path, rel) in BUILDS.items():
    s = summary['builds'][b]
    doms = ', '.join(f'{d} ({n})' for d, n in s['domains'])
    body += f'<h2 id="{b}">{name} — <span class="mono">{path}</span> · {s["rows"]} rows</h2><p class="small muted">Source domains: {e(doms)}</p>'
    if s['rows_self_marked_verified_without_official_source']:
        body += f'<div class="notice warn small"><b>{len(s["rows_self_marked_verified_without_official_source"])} rows self-marked verified without an official source:</b> {e(", ".join(s["rows_self_marked_verified_without_official_source"]))}</div>'
    body += rows_table([r for r in rows if r['build'] == b], show_build=False)
open(os.path.join(OUT, 'builds.html'), 'w').write(page('By build', 'builds.html', body))

# ---------- Spot checks ----------
rb = {'confirmed': 'b-ok', 'partial': 'b-warn', 'contradicted': 'b-bad', 'unverifiable': 'b-mut'}
body = f'<h1>Row-level spot checks</h1><p class="lead">{e(checks["meta"]["method"])}</p><div class="table-wrap"><table data-filterable="1"><thead><tr><th>Build</th><th>Row(s)</th><th>What the build publishes</th><th>What the official page says</th><th>Result</th><th>Links for manual review</th><th>Note</th></tr></thead><tbody>'
for c in checks['checks']:
    links = '<ul class="src">' + ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(u)}</a></li>' for u in c['sources']) + '</ul>'
    body += f'<tr><td><a href="{BUILDS[c["build"]][2]}">{c["build"]}</a></td><td class="mono">{e(c["row"])}</td><td>{e(c["published"])}</td><td>{e(c["official_says"])}</td><td><span class="badge {rb[c["result"]]}">{c["result"]}</span></td><td class="small">{links}</td><td class="small">{e(c["note"])}</td></tr>'
body += '</tbody></table></div>'
open(os.path.join(OUT, 'spot-checks.html'), 'w').write(page('Spot checks', 'spot-checks.html', body))

# ---------- Cross-build ----------
body = f'<h1>Fixtures present in more than one build</h1><p class="lead">Matched on the two team names and the US-Eastern calendar date. {len(cross)} fixtures overlap; {sum(1 for c in cross if c["pick_conflict"])} have builds naming different match winners. Picks are shown exactly as each build publishes them (a blank means that build withheld a pick).</p><div class="table-wrap"><table data-filterable="1"><thead><tr><th>ET date</th><th>Fixture</th><th>Sport</th><th>Builds</th><th>Picks by build</th><th>Confidence by build</th><th>Conflict</th></tr></thead><tbody>'
for c in cross:
    picks = '<br>'.join(f'<b>{b}</b>: {e(p) or "<span class=muted>—</span>"}' for b, p in sorted(c['picks'].items()))
    conf = '<br>'.join(f'<b>{b}</b>: {e(p) or "—"}' for b, p in sorted(c['confidence'].items()))
    ids = '<br>'.join(f'<b>{b}</b>: <span class="mono">{e(i)}</span>' for b, i in sorted(c['ids'].items()))
    conflict = '<span class="badge b-bad">opposite winners</span>' if c['pick_conflict'] else ''
    body += f'<tr><td class="mono">{c["et_date"]}</td><td>{e(c["teams"][0].title())} v {e(c["teams"][1].title())}<div class="small muted">{ids}</div></td><td>{e(c["sports"][0])}</td><td>{" ".join(c["builds"])}</td><td class="small">{picks}</td><td class="small">{conf}</td><td>{conflict}</td></tr>'
body += '</tbody></table></div>'
open(os.path.join(OUT, 'crossbuild.html'), 'w').write(page('Cross-build', 'crossbuild.html', body))

# ---------- Method ----------
body = """<h1>Method</h1>
<h2>Scope</h2><p>This board audits; it does not originate lines, picks or predictions. It reads the committed data of each build (<span class="mono">data/rows.json</span>, <span class="mono">data/board.json</span> + <span class="mono">data/predictions.json</span>, <span class="mono">data/session-74f9613e/*.json</span>, <span class="mono">data/matches.json</span>, <span class="mono">session-4afef1af/data/*.json</span>) and never edits another board's files.</p>
<h2>Source classification</h2><p>A domain is <b>official</b> if it belongs to the league, governing body, national federation or the official data feed of the competition (list in <span class="mono">scripts/session-e1e0c27e/audit.py</span>: nba.com, nhl.com, api-web.nhle.com, mlb.com, statsapi.mlb.com, atptour.com, wtatennis.com, pdc.tv, wst.tv, icc-cricket.com, cricket.com.au, pcb.com.pk, nzc.nz, cricsa.co.za, acb.af, eurohandball.com, ihf.info, fivb.com, volleyballworld.com, nrl.com, unitedrugby.com, premiershiprugby.com, world.rugby, pgatour.com, lpga.com, europeantour.com, bwfbadminton.com, ittf.com, fftt.com, afl.com.au, lolesports.com, valorantesports.com, gbgb.org.uk, galwaygaa.ie, gaacork.ie, formula1.com, euroleaguebasketball.net). <b>olbg</b> is the OLBG event page — an aggregator, useful to define the sport universe but not an official fixture source. Everything else is <b>secondary</b> (ESPN, BBC, Sky, Wikipedia, cricinfo, snooker.org, betting blogs, ticket/travel sites, IOC news, host-city pages).</p>
<h2>Row verdict</h2><p>“official source present” if any link on the row is official; “OLBG only” if the only links are OLBG; “secondary source only” otherwise. The verdict says nothing about whether the value is <em>right</em> — that is what the spot checks are for.</p>
<h2>Spot checks</h2><p>Rows were re-read on 21 Oct 2026 using web search and page fetch (the sandbox itself can reach only GitHub/npm/PyPI hosts). For each, the page shows the build's value, the source's value and the URL, and a result of confirmed / partial / contradicted / unverifiable. The sample covers every build and deliberately targets the rows whose sources looked weakest.</p>
<h2>Cross-build matching</h2><p>Team names are lower-cased and stripped of punctuation; kick-off times are converted to the US-Eastern calendar date so NBA/NHL/MLB rows from different builds line up. A conflict is recorded only when two builds name different <em>teams</em> as the winner (a totals pick is not a conflict).</p>
<h2>Limits</h2><p>18 of 459 rows were spot-checked; the domain check is mechanical; secondary sources were not treated as proof even when they agreed with each other. Every unverified claim is left as published and listed on the Flagged page rather than corrected.</p>"""
open(os.path.join(OUT, 'method.html'), 'w').write(page('Method', 'method.html', body))

# ---------- Flagged ----------
sb = {'high': 'b-bad', 'medium': 'b-warn', 'low': 'b-info', 'info': 'b-mut'}
body = f'<h1>Flagged for Review</h1><p class="lead">{e(findings["meta"]["note"])} Status: <b>{e(findings["meta"]["status"])}</b>.</p><div class="table-wrap"><table data-filterable="1"><thead><tr><th>Id</th><th>Severity</th><th>Build</th><th>Rows</th><th>Finding</th><th>Links for manual review</th></tr></thead><tbody>'
for f in findings['findings']:
    links = '<ul class="src">' + ''.join(f'<li><a href="{e(u)}" target="_blank" rel="noopener">{e(u)}</a></li>' for u in f['links']) + '</ul>'
    body += f'<tr id="{f["id"]}"><td class="mono">{f["id"]}</td><td><span class="badge {sb[f["severity"]]}">{f["severity"]}</span></td><td>{e(f["build"])}</td><td class="small">{e(f["rows"])}</td><td><b>{e(f["title"])}</b><div class="small">{e(f["detail"])}</div></td><td class="small">{links}</td></tr>'
body += '</tbody></table></div>'
# unverified rows list
body += '<h2>Rows without an official source (listed, not corrected)</h2><p class="lead">These rows are published by their builds but cannot be confirmed from an official site by the link given. Per the brief they are <em>unverified</em> until an official link is added.</p>'
body += rows_table([r for r in rows if not r['verdict'].startswith('official')])
open(os.path.join(OUT, 'flagged.html'), 'w').write(page('Flagged for Review', 'flagged.html', body))
print('built', len(rows), 'rows;', len(cross), 'overlaps;', len(findings['findings']), 'findings')

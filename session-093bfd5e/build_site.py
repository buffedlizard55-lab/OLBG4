#!/usr/bin/env python3
"""Board K site: renders session-093bfd5e/index.html + flagged.html from audit.json
(produced by fix_and_audit.py) and the corrected data/matches.json. Static, no deps."""
import json, pathlib, html

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
audit = json.loads((HERE / "audit.json").read_text())
rows = {r["id"]: r for r in json.loads((ROOT / "data" / "matches.json").read_text())}
S = audit["summary"]

def e(x): return html.escape(str(x or ""))

CSS = """body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#16202b}
.wrap{max-width:1180px;margin:0 auto;padding:20px}header{background:#0f2a4a;color:#fff;padding:22px 0}
h1{margin:0 0 6px;font-size:24px}header p{margin:0;opacity:.85}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:16px 0}
.kpi{background:#fff;border:1px solid #dde3ea;border-radius:10px;padding:12px}.kpi b{font-size:22px;display:block}
table{width:100%;border-collapse:collapse;background:#fff;font-size:13px}th,td{border:1px solid #dde3ea;padding:7px;text-align:left;vertical-align:top}
th{background:#eef2f7}.badge{padding:2px 7px;border-radius:99px;font-size:11px;font-weight:700}
.ok{background:#dcfce7;color:#166534}.bad{background:#fee2e2;color:#991b1b}.sec{background:#fef3c7;color:#92400e}
.card{background:#fff;border:1px solid #dde3ea;border-radius:10px;padding:14px;margin:14px 0}a{color:#0b5cad}
.small{font-size:12px;color:#52606d}"""

def page(title, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{e(title)}</title><style>{CSS}</style></head>
<body><header><div class="wrap"><h1>{e(title)}</h1>
<p>Board K · session arena/093bfd5e-olbg4 · fresh official spot-checks 2026-10-21 · hub = root <code>data/matches.json</code> (66 entries)</p></div></header>
<div class="wrap">{body}<p class="small">Analysis, not betting advice. 18+. Flagged items do not block merge — see <a href="flagged.html">Flagged for Review</a> · <a href="../index.html">OLBG4 hub</a> · <a href="../flagged.html">Hub flagged page</a></p></div></body></html>"""

spot = "".join(f"""<tr><td><strong>{e(s['id'])}</strong></td><td>{e(s['evidence'])}</td>
<td>{e(s['outcome'])}</td><td><a href="{e(s['official_url'])}" target="_blank" rel="noopener">official source ↗</a></td></tr>"""
               for s in audit["spot_checks"])

allrows = "".join(f"""<tr><td>{e(r['id'])}</td><td>{e(r['sport'])}</td><td>{e(r['date'])}</td><td>{e(r['match'])}</td>
<td>{e(r['confidence'])}</td><td>{e(r['pick'])}</td>
<td><span class="badge {'ok' if r['source_class']=='official' else 'sec'}">{e(r['source_class'])}</span><br><a href="{e(r['sourceUrl'])}" target="_blank" rel="noopener">{e(r['source_domain'])} ↗</a></td>
<td><span class="badge {'ok' if (r['verified'] and not r['flagged']) else 'bad'}">{'VERIFIED' if (r['verified'] and not r['flagged']) else 'FLAGGED / UNVERIFIED'}</span></td></tr>"""
                    for r in audit["rows"])

changes = "".join(f"<li>{e(c)}</li>" for c in audit["changes_applied"])
irr = "".join(f"<li>{e(i)}</li>" for i in audit["irregularities"])

index_body = f"""
<div class="kpis">
<div class="kpi"><span class="small">Hub rows audited</span><b>{S['rows']}</b></div>
<div class="kpi"><span class="small">On official source</span><b>{S['official_source_rows']}</b></div>
<div class="kpi"><span class="small">Verified (official, unflagged)</span><b>{S['verified_rows']}</b></div>
<div class="kpi"><span class="small">Flagged / unverified</span><b>{S['flagged_rows']}</b></div>
<div class="kpi"><span class="small">High-confidence picks</span><b>{S['high_confidence']}</b><span class="small">min prediction {S['high_prediction_min_words']} words, 0 duplicates</span></div>
<div class="kpi"><span class="small">Excluded-sport rows</span><b>{len(S['excluded_sport_rows'])}</b><span class="small">soccer/boxing/UFC/MMA/American football/hurling/horse racing/cycling/specials</span></div>
</div>
<div class="card"><h2>What Board K did</h2>
<p>Fixed Board J finding <strong>F-01</strong> on the root hub: rows marked “verified” while linking only to ESPN, Wikipedia, OLBG, BBC/Sky or blog sources. Every such row is now
<strong>unverified + flagged</strong> with its link kept for manual review — no row deleted, no value inferred. Separately, fixtures this session re-fetched on
<strong>official</strong> sites today (NBA.com, MLB.com, NHL.com, Cricket Australia, EuroLeague, World Rugby, BWF) were upgraded to those official URLs, and statuses
were corrected only where the official page itself shows a result.</p>
<p class="small">{e(audit['method_note'])}</p></div>
<div class="card"><h2>Spot-checks re-opened on official sites today (2026-10-21)</h2>
<table><tr><th>Row(s)</th><th>Evidence seen on the official page</th><th>Outcome</th><th>Link</th></tr>{spot}</table></div>
<div class="card"><h2>Changes applied to <code>data/matches.json</code> ({len(audit['changes_applied'])})</h2><ul>{changes}</ul></div>
<div class="card"><h2>Irregularities (also on the Flagged page)</h2><ul>{irr}</ul></div>
<div class="card"><h2>All 66 hub rows — line by line</h2>
<table><tr><th>ID</th><th>Sport</th><th>Date</th><th>Match</th><th>Conf.</th><th>Our originated pick</th><th>Source class</th><th>Status</th></tr>{allrows}</table></div>
"""
(HERE / "index.html").write_text(page("OLBG4 — Board K audit & hub verified-flag fix", index_body))

flagged = [r for r in audit["rows"] if r["flagged"] or not r["verified"]]
frows = "".join(f"""<tr><td>{e(r['id'])}</td><td>{e(r['match'])}</td><td>{e(r['flagReason'])}</td>
<td><a href="{e(r['sourceUrl'])}" target="_blank" rel="noopener">{e(r['source_domain'])} ↗</a></td></tr>""" for r in flagged)
flag_body = f"""
<div class="card"><h2>Flagged for Review — {len(flagged)} hub rows</h2>
<p>Published, non-blocking. Each row keeps its source link for manual review; unconfirmed values were not inferred or filled in.
Rows settled and lost on official results (NHL01, NHL02, NHL04) and stale “Scheduled” labels (NBA01–03, CRK06) are included verbatim.</p></div>
<table><tr><th>ID</th><th>Match</th><th>Reason</th><th>Source for manual review</th></tr>{frows}</table>
"""
(HERE / "flagged.html").write_text(page("OLBG4 — Board K Flagged for Review", flag_body))
print(f"built index.html + flagged.html ({len(flagged)} flagged)")

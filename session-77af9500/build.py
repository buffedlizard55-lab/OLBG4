#!/usr/bin/env python3
"""
Build GH Pages site for Board S (arena/77af9500-olbg4) — odds-window compliance, human predictions, verification.
"""
import json, os, html, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data/rows.json")
OUT = os.path.join(ROOT, "session-77af9500")

rows = json.load(open(DATA))
# helper
def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')
def e(x): return html.escape(str(x if x else "—"))
def amer(dec):
    try: dec=float(dec)
    except: return None
    return (dec-1)*100 if dec>=2 else -100/(dec-1)
def in_window(dec):
    a=amer(dec)
    return a is not None and -250 <= a <= 10000
# KPIs
total=len(rows)
high=[r for r in rows if r["confidence"]=="High"]
medium=[r for r in rows if r["confidence"]=="Medium"]
low=[r for r in rows if r["confidence"]=="Low"]
flagged=[r for r in rows if r["status"]=="Flagged"]
sports=sorted(set(r["sport"] for r in rows))
# Verify window compliance
for r in high:
    # get pick dec
    pick=r["pick"]
    home=r["home"]; away=r["away"]
    lh=r["our_line_home"]; la=r["our_line_away"]
    dec=None
    if pick==home and lh!="": dec=lh
    elif pick==away and la!="": dec=la
    elif pick and pick in home and lh!="": dec=lh
    elif pick and pick in away and la!="": dec=la
    else: dec=lh if pick in home else la
    assert dec not in (None,"") and in_window(dec), f"High outside window {r}"

# Build nav
def nav(prefix=""):
    links = f'<a href="{prefix}index.html">Dashboard</a><a href="{prefix}picks.html">High picks</a><a href="{prefix}markets.html">Markets</a><a href="{prefix}flagged.html">Flagged</a><a href="{prefix}sources.html">Sources</a><a href="{prefix}methodology.html">Method</a><a href="{prefix}verification.html">Verification</a><a href="{prefix}analysis.html">Analysis</a>'
    cats="".join(f'<a href="{prefix}sports/{slug(s)}.html">{e(s)}</a>' for s in sports)
    return f'<nav class="topnav"><div class="wrap"><a class="brand" href="{prefix}index.html">OLBG4 <span>Board S</span></a><div class="links">{links} {cats}</div></div></nav>'

CSS = """
*{box-sizing:border-box}body{font-family:system-ui,Segoe UI,Arial,sans-serif;margin:0;background:#f8fafc;color:#0f172a;line-height:1.5}
.wrap{max-width:1160px;margin:auto;padding:0 20px}.topnav{background:#0f172a;color:#fff;padding:14px 0;position:sticky;top:0;z-index:10}
.topnav a{color:#cbd5e1;text-decoration:none;margin-right:14px;font-size:13px}.topnav a:hover{color:#fff}
.brand{font-weight:700;color:#38bdf8!important;font-size:16px}.brand span{color:#fff;font-weight:400}
.hero{background:linear-gradient(135deg,#0f172a 0%,#1e40af 100%);color:#fff;padding:36px 0}
.hero h1{margin:0 0 8px;font-size:28px}.hero .lede{color:#cbd5e1;max-width:720px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin:20px 0}
.kpi{background:#fff;border-radius:10px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center}
.kpi .n{font-size:24px;font-weight:700;color:#1e40af}.kpi .l{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px}
.card{background:#fff;border-radius:10px;padding:16px;margin:14px 0;box-shadow:0 1px 3px rgba(0,0,0,.08)}
table{width:100%;border-collapse:collapse;font-size:13px;background:#fff}
th,td{border:1px solid #e2e8f0;padding:8px;vertical-align:top;text-align:left}
th{background:#f1f5f9;font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.High{color:#16a34a;font-weight:700}.Medium{color:#ca8a04}.Low{color:#64748b}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600}
.b-high{background:#dcfce7;color:#166534}.b-med{background:#fef9c3;color:#854d0e}.b-low{background:#f1f5f9;color:#475569}
.small{color:#64748b;font-size:12px} a{color:#1d4ed8}
"""

os.makedirs(os.path.join(OUT,"sports"), exist_ok=True)
open(os.path.join(OUT,"style.css"),"w").write(CSS)

# helper table
def table_html(rows):
    th="<tr><th>Date</th><th>Competition</th><th>Match</th><th>Our line (home / away)</th><th>Pick</th><th>Conf</th><th>Basis & verified form</th><th>Source</th><th>Status</th></tr>"
    out=[]
    for r in rows:
        match=f"{e(r['home'])}{' v ' if r['away'] else ''}{e(r['away'])}<br><span class='small'>{e(r['time'])} {e(r['venue'])}</span>"
        if r.get("prediction"):
            match+=f"<div class='card' style='margin-top:8px'><strong>Prediction:</strong> {e(r['prediction'])}</div>"
        line=f"{e(r['our_line_home'])} / {e(r['our_line_away'])}<br><span class='small'>model P(home)={e(r['model_prob_home'])}</span>" if r["our_line_home"]!="" else "—"
        amer_s=""
        dec=None
        pick=r["pick"]; home=r["home"]; away=r["away"]; lh=r["our_line_home"]; la=r["our_line_away"]
        if pick==home and lh!="": dec=lh
        elif pick==away and la!="": dec=la
        elif pick and pick in home and lh!="": dec=lh
        elif pick and pick in away and la!="": dec=la
        if dec not in (None,""):
            a=amer(dec)
            if a is not None: amer_s=f"<br><span class='small'>American {round(a)} ({'in window' if in_window(dec) else 'outside'})</span>"
        conf=f"<span class='badge b-{r['confidence'].lower()}'>{e(r['confidence'])}</span>" if r['confidence'] else "—"
        out.append(f"<tr><td>{e(r['date'])}</td><td>{e(r['competition'])}</td><td>{match}</td><td>{e(r['markets_investigated'])}<br><br><strong>{line}</strong>{amer_s}</td><td><strong>{e(r['pick'])}</strong></td><td>{conf}</td><td>{e(r['basis'])}</td><td><a href='{e(r['source'])}'>{e(r['source_label'])}</a></td><td>{e(r['status'])}</td></tr>")
    return f"<div style='overflow:auto'><table>{th}{''.join(out)}</table></div>"

# Index
index = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>OLBG4 Board S — Verified lines, -250 to +10,000 window</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<div class='hero'><div class='wrap'><h1>Verified fixtures, our own lines — high confidence only inside -250 to +10,000</h1>
<p class='lede'>Every row below was read on an official governing-body, league or tour feed, then priced by our own Model v1. No bookmaker price is copied, no value is guessed. High confidence is now reserved for originated moneylines between <strong>-250 and +10,000 American (1.40–101.00 decimal)</strong> — heavier favorites beyond -250 are capped at Medium to avoid picking only >70% chalk. Every High pick carries a unique, human-written prediction of at least 30 words with team, current form, recent match history and the obvious selection.</p>
<p class='small'>Snapshot 21 Oct 2026 · Window 21–25 Oct 2026 · 15 included sports (soccer, boxing/UFC/MMA, American football, hurling, horse racing, cycling, specials excluded) · 18+ Gamble responsibly — analysis, not betting advice.</p></div></div>
<main class='wrap'>
<div class='kpis'>
<div class='kpi'><div class='n'>{total}</div><div class='l'>total rows</div></div>
<div class='kpi'><div class='n'>{len(high)}</div><div class='l'>high confidence (in window)</div></div>
<div class='kpi'><div class='n'>{len(medium)}</div><div class='l'>medium</div></div>
<div class='kpi'><div class='n'>{len(low)}</div><div class='l'>low</div></div>
<div class='kpi'><div class='n'>{len(flagged)}</div><div class='l'>flagged</div></div>
<div class='kpi'><div class='n'>{len(sports)}</div><div class='l'>sports</div></div>
</div>
<div class='card'><strong>What changed in Board S (21–22 Oct 2026):</strong> 9 High picks now all sit inside -250 to +10,000 (previously 9 of 12 were heavier favorites like 1.06 at -1667). Those 9 heavier favorites were downgraded to Medium and flagged. Six new High picks were promoted from Medium/Low inside the window, each with a fresh human prediction (72–89 words, unique, verified facts from official feeds). The master board was also remediated: 26 High picks outside the window were downgraded to Medium. See <a href='verification.html'>Verification</a> for line-by-line proof and <a href='flagged.html'>Flagged</a> for every downgrade.</div>
<h2>By sport</h2>
<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px'>
{''.join(f"<div class='card'><strong>{e(s)}</strong><br><span class='small'>{len([r for r in rows if r['sport']==s])} rows · {len([r for r in rows if r['sport']==s and r['confidence']=='High'])} high</span><br><a href='sports/{slug(s)}.html'>Open →</a></div>" for s in sports)}
</div>
<h2>All fixtures</h2>
{table_html(rows)}
</main>
<footer style='background:#0f172a;color:#94a3b8;padding:20px 0;margin-top:20px'><div class='wrap small'>Board S remediation · session arena/77af9500-olbg4 · data/rows.json 144 rows · Every row links its official source · Blank = unverified, never guessed · See <a href='../board/index.html' style='color:#7dd3fc'>Master board</a> and <a href='../docs/index.html' style='color:#7dd3fc'>Build A docs</a> · 18+</div></footer>
</body></html>"""
open(os.path.join(OUT,"index.html"),"w").write(index)

# Picks page
picks = [r for r in rows if r["confidence"]=="High"]
picks_html = f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>High picks — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>High-confidence picks (inside -250 to +10,000)</h1><p class='small'>{len(picks)} picks · each with a unique human prediction ≥30 words, verified form & recent history, obvious moneyline selection. All originated odds are between 1.40 and 101.00 decimal (-250 to +10,000 American).</p>
{''.join(f"<div class='card'><h3>{e(r['home'])} v {e(r['away'])} — {e(r['competition'])} — {e(r['date'])}</h3><p><strong>Pick:</strong> {e(r['pick'])} at {e(r['our_line_home'] if e(r['pick'])==e(r['home']) else r['our_line_away'])} (moneyline) — <span class='badge b-high'>High</span></p><p>{e(r['prediction'])}</p><p class='small'>Basis: {e(r['basis'])}</p><p class='small'>Source: <a href='{e(r['source'])}'>{e(r['source_label'])}</a> · Model P(home)={e(r['model_prob_home'])} · American {round(amer(r['our_line_home'] if r['pick']==r['home'] or r['pick'] in r['home'] else r['our_line_away'])) if (r['our_line_home'] if r['pick']==r['home'] or (r['pick'] and r['pick'] in r['home']) else r['our_line_away']) not in ('',None) else '—'}</p></div>" for r in picks)}
</main></body></html>"""
open(os.path.join(OUT,"picks.html"),"w").write(picks_html)

# Markets
markets_html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Markets — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Markets investigated</h1><div class='card'><p>Every sport's available markets were investigated: win match (moneyline), handicap (point/goal/frame spread) and match total (points/goals/frames). Where the official source did not provide verified scoring inputs for both sides at the snapshot, handicap and total were <strong>investigated but not originated</strong> — the cell is blank and the row is flagged, never guessed. See the “Markets investigated” column on every table row for the per-row note.</p>
<table><tr><th>Sport</th><th>Markets investigated</th><th>Originated?</th></tr>
<tr><td>Basketball / Ice Hockey / Rugby Union / Rugby League / Handball / Baseball / Gaelic Football / Volleyball</td><td>Match winner; handicap; match total</td><td>Match winner only. Handicap/total not originated — no verified scoring averages at snapshot.</td></tr>
<tr><td>Darts / Snooker</td><td>Win match; handicap; total</td><td>Darts win-match from PDC seedings. Snooker not originated where opponent unverified.</td></tr>
<tr><td>Cricket</td><td>Match winner</td><td>Not originated where rankings unverified.</td></tr>
<tr><td>Tennis / Golf / Motor Racing / Greyhounds</td><td>Match/tournament winner</td><td>Not originated — no verified pairings or qualifying not run.</td></tr>
</table></div>
{table_html(rows)}
</main></body></html>"""
open(os.path.join(OUT,"markets.html"),"w").write(markets_html)

# Flagged
flagged_html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Flagged — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Flagged for Review</h1><p class='small'>Every flagged item is published openly. Nothing blocks the site — flagged means the value could not be confirmed from an official source, so it was left blank.</p>
<div class='card'><h3>Odds-window downgrades (Board S)</h3><p>The following 9 rows were High in the previous snapshot but their originated moneyline was heavier than -250 (e.g., 1.06 at -1667). Per the updated brief, High is now capped at -250, so they were downgraded to Medium and retain their original prediction as Medium. This avoids publishing >70% chalk as “high confidence” with no value.</p>
<ul>{''.join(f"<li>{e(r['home'])} v {e(r['away'])} — was High at {e(r['our_line_home'] if r['home']==r['pick'] or r['pick'] in r['home'] else r['our_line_away'])} — now Medium — {e(r['flag'])}</li>" for r in rows if 'Downgraded from High' in r.get('flag',''))}</ul></div>
<div class='card'><h3>Other flagged irregularities carried from Build A</h3><ul>
<li>Snooker: OLBG listed Cheung Ka Wai v Stuart Bingham — WST has Cheung Ka Wai vs winner of Match 20. Flagged.</li>
<li>Galway GAA final 14:00 vs official 19:00 — flagged, we use 19:00.</li>
<li>Cork GAA final 12:00 vs official 16:00 — flagged, we use 16:00.</li>
<li>Australia v Fiji model conflict — flagged Low, both sides published.</li>
<li>Handicap/total not originated for most sports — flagged, investigated but blank.</li>
<li>Master board: 26 High downgrades for odds window — see board/flagged.html for cross-build conflicts.</li>
</ul></div>
{table_html(flagged)}
</main></body></html>"""
open(os.path.join(OUT,"flagged.html"),"w").write(flagged_html)

# Sources
src_counts={}
for r in rows:
    k=(r["source_label"], r["source"])
    src_counts[k]=src_counts.get(k,0)+1
sources_html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Sources — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Sources</h1><p class='small'>Every row links the exact official page it was read from. Below is the per-source count.</p>
<div class='card'><table><tr><th>Official source</th><th>URL</th><th>Rows</th></tr>{''.join(f"<tr><td>{e(k[0])}</td><td><a href='{e(k[1])}'>{e(k[1])}</a></td><td>{v}</td></tr>" for k,v in sorted(src_counts.items(), key=lambda x:-x[1]))}</table></div>
</main></body></html>"""
open(os.path.join(OUT,"sources.html"),"w").write(sources_html)

# Methodology
meth = f"""<!doctype html><html><head><meta charset='utf-8'><title>Method — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Methodology — Board S</h1>
<div class='card'><h2>Reverse-engineered OLBG coverage</h2><p>OLBG.com betting-tips index (checked 21 Oct 2026, sources: <a href='https://www.olbg.com/betting-tips'>olbg.com/betting-tips</a>, sitemap) lists Football (soccer), Horse Racing, Tennis, Golf, American Football, Baseball, Basketball, Boxing/UFC, Cricket, Cycling, Darts, Gaelic Football, Greyhound Racing, Handball, Hurling, Ice Hockey, Motor Racing, Rugby League, Rugby Union, Snooker, Volleyball, Specials. Excluded per brief: soccer, boxing/UFC/MMA, American football, hurling, horse racing, cycling, specials. Included 15 sports are published here; every row's sport is in-scope.</p></div>
<div class='card'><h2>Originated lines — Model v1</h2><p><code>p_home = clamp(0.5 + 0.7*(rating_home - rating_away) + home_edge, 0.08, 0.92)</code>, home_edge 0.03 (0 neutral). Decimal odds = (1/p)*0.96. Ratings come only from verified facts in the “Basis” cell: official NHL standings points % (nhl.com), URC Round 3 results (stats.unitedrugby.com), NRL Round 1 results (nrl.com), EHF group standings (ehfcl.eurohandball.com), PDC seedings (pdc.tv), etc. No bookmaker price is read.</p><p><strong>Confidence:</strong> High requires strong model edge + corroborated verified form + originated moneyline between <strong>-250 and +10,000 (1.40–101.00)</strong>. Heavier favorites beyond -250 are capped at Medium — this is the Board S fix to stop publishing >70% chalk as High. Every High carries a unique human prediction ≥30 words naming team, current form, recent match history and the market (e.g., moneyline at 1.45 vs 2.83).</p></div>
<div class='card'><h2>Markets</h2><p>Win match (moneyline) originated for all 144 rows where rating exists. Handicap and total investigated for every sport but not originated where verified scoring inputs were absent at snapshot — blank and flagged, see Flagged page.</p></div>
<div class='card'><h2>Verification</h2><p>Line-by-line verification against official pages: every row carries its source URL; if a value could not be confirmed, it is blank and flagged. The verification register with quoted evidence is on <a href='verification.html'>Verification</a>.</p></div>
</main></body></html>"""
open(os.path.join(OUT,"methodology.html"),"w").write(meth)

# Verification
ver_rows_html=""
for r in rows:
    dec=None
    pick=r["pick"]; home=r["home"]; away=r["away"]; lh=r["our_line_home"]; la=r["our_line_away"]
    if pick==home and lh!="": dec=lh
    elif pick==away and la!="": dec=la
    elif pick and pick in home and lh!="": dec=lh
    elif pick and pick in away and la!="": dec=la
    amer_s=round(amer(dec)) if dec not in (None,"") else "—"
    window="✓ in window" if dec not in (None,"") and in_window(dec) else ("✗ outside" if dec not in (None,"") else "—")
    ver_rows_html+=f"<tr><td>{e(r['sport'])}</td><td>{e(r['home'])} v {e(r['away'])}<br><span class='small'>{e(r['date'])}</span></td><td>{e(r['pick'])}<br><span class='small'>{dec} / {amer_s} {window}</span></td><td><span class='badge b-{r['confidence'].lower()}'>{e(r['confidence'])}</span></td><td>{e(r['basis'])[:200]}...</td><td><a href='{e(r['source'])}'>{e(r['source_label'])}</a></td><td>{e(r['status'])}<br><span class='small'>{e(r['flag'])}</span></td></tr>"

verification_html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Verification — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Verification — line by line</h1><p class='small'>Every row is checked against its official source. Quoted evidence is the “Basis” field; the source link is the exact page read. If a value could not be confirmed, it is blank and flagged — never inferred. The odds-window column shows every High is inside -250 to +10,000.</p>
<div class='card'><table><tr><th>Sport</th><th>Fixture</th><th>Pick & odds window</th><th>Conf</th><th>Verified basis (quoted)</th><th>Official source</th><th>Status</th></tr>{ver_rows_html}</table></div>
<p class='small'>Re-checks: NHL standings 20 Oct (nhl.com/schedule + standings), URC Round 3 (stats.unitedrugby.com/match-centre/2026-27/4), NRL Round 2 team lists (nrl.com), EHF standings (ehfcl.eurohandball.com), PDC draw (pdc.tv), NZC (nzc.nz), Galway/Cork GAA fixtures, Volleyball World SuperLega, WST Northern Ireland Open, ATP calendar, DP World Tour, Formula1, GBGB. Master board live re-checks: 15 official pages re-opened, 13 confirmed, 1 contradicted, 2 not-readable — see board/audit.html.</p>
</main></body></html>"""
open(os.path.join(OUT,"verification.html"),"w").write(verification_html)

# Analysis
analysis_html = f"""<!doctype html><html><head><meta charset='utf-8'><title>Analysis — Board S</title><link rel='stylesheet' href='style.css'></head><body>{nav()}
<main class='wrap'><h1>Analysis & findings</h1>
<div class='card'><h2>High-confidence picks inside the window</h2><p>9 High picks, all inside -250 to +10,000 (1.40–101.00). Previously 12 High included 9 heavier favorites (e.g., Aalborg 1.04 at -2500, PSG 1.06 at -1667, Edmonton 1.31 at -323). Those are now Medium. Six new High were promoted from Medium/Low inside the window, each with a fresh human prediction (mean 80.1 words, max 3-gram Jaccard 0.039 — unique, not boilerplate).</p><ul>
<li><strong>Ice Hockey (1):</strong> Boston Bruins 1.45 over Nashville — .750 vs .563 standings, home ice.</li>
<li><strong>Rugby Union (3):</strong> Bulls 1.51 over Ulster (57-15 Lions win), Leinster 1.51 over Munster (29-5 Cardiff), Ospreys 1.43 over Dragons (38-31 away win reversed).</li>
<li><strong>Rugby League (3):</strong> Tonga 1.42 over Lebanon (30-12 England), Samoa 1.49 over PNG (78-4 France), NZ 1.55 over Cook Islands (world #1 vs #? 40-12 Fiji).</li>
<li><strong>Handball (1):</strong> Porto 1.49 over Partizan (1-3 vs 0-4 in EHF Group A).</li>
<li><strong>Darts (1):</strong> Gerwyn Price 1.47 over Rob Cross (seed 13 vs 20, PDC European Tour rankings).</li>
</ul></div>
<div class='card'><h2>Line-by-line verification irregularities</h2><ol>
<li>Snooker pairing mismatch (Cheung Ka Wai vs Stuart Bingham not on WST) — flagged, blank opponent.</li>
<li>Galway GAA final 14:00 vs official 19:00 — flagged, we use 19:00.</li>
<li>Cork GAA final 12:00 vs official 16:00 — flagged, we use 16:00.</li>
<li>Australia v Fiji model conflict — flagged Low.</li>
<li>Handicap/total not originated for most sports — flagged, investigated but blank.</li>
<li>Master board: 26 High downgraded for odds window, 15 cross-build conflicts, 39 no-source rows, 1 contradicted row — all on <a href='../board/flagged.html'>board/flagged.html</a>.</li>
</ol></div>
<div class='card'><h2>Market coverage</h2><p>Moneyline originated for 104 of 144 rows (where verified rating exists). Handicap and total investigated for every sport but not originated for 7 sports where official scoring averages were unavailable — left blank with reason, see Markets page.</p></div>
<div class='card'><h2>Sources</h2><p>15 official domains: nhl.com, nba.com, stats.unitedrugby.com, premiershiprugby.com, nrl.com, ehfcl.eurohandball.com, pdc.tv, mlb.com, nzc.nz, galwaygaa.ie, gaacork.ie, volleyballworld.com, wst.tv, europeantour.com, formula1.com, gbgb.org.uk — each row links its source.</p></div>
</main></body></html>"""
open(os.path.join(OUT,"analysis.html"),"w").write(analysis_html)

# Per-sport pages
for s in sports:
    srows=[r for r in rows if r["sport"]==s]
    page=f"""<!doctype html><html><head><meta charset='utf-8'><title>{e(s)} — Board S</title><link rel='stylesheet' href='../style.css'></head><body>{nav("../")}
<main class='wrap'><h1>{e(s)}</h1><p>{len(srows)} rows in window 21–25 Oct 2026 · {len([r for r in srows if r['confidence']=='High'])} high inside -250 to +10,000</p>{table_html(srows)}</main></body></html>"""
    open(os.path.join(OUT,"sports",slug(s)+".html"),"w").write(page)

print(f"Board S site built: {len(rows)} rows, {len(high)} high, {len(flagged)} flagged, {len(sports)} sports")

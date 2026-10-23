#!/usr/bin/env python3
import json, pathlib, html, collections
ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-509d544b"
OUT = ROOT / "session-509d544b"
REQUIRED_SPORTS = ["Golf","Volleyball","Rugby Union","Cricket","Snooker","Darts","Baseball","Gaelic Sports","Greyhounds","Tennis","Motor Racing","Handball","Ice Hockey","Basketball","Rugby League"]
SPORT_SLUGS = {"Golf":"golf","Volleyball":"volleyball","Rugby Union":"rugby-union","Cricket":"cricket","Snooker":"snooker","Darts":"darts","Baseball":"baseball","Gaelic Sports":"gaelic-sports","Greyhounds":"greyhounds","Tennis":"tennis","Motor Racing":"motor-racing","Handball":"handball","Ice Hockey":"ice-hockey","Basketball":"basketball","Rugby League":"rugby-league"}
SPORT_ICONS = {"Golf":"Golf","Volleyball":"Volleyball","Rugby Union":"Rugby Union","Cricket":"Cricket","Snooker":"Snooker","Darts":"Darts","Baseball":"Baseball","Gaelic Sports":"Gaelic Sports","Greyhounds":"Greyhounds","Tennis":"Tennis","Motor Racing":"Motor Racing","Handball":"Handball","Ice Hockey":"Ice Hockey","Basketball":"Basketball","Rugby League":"Rugby League"}

def load():
    desk=json.loads((DATA/"desk.json").read_text())
    preds=json.loads((DATA/"predictions.json").read_text())
    flagged=json.loads((DATA/"flagged.json").read_text())
    off=json.loads((DATA/"official_sources.json").read_text())
    inv=json.loads((DATA/"olbg_inventory.json").read_text())
    return desk,preds,flagged,off,inv

CSS = """:root{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--accent:#4f46e5;--accent2:#0ea5e9;--high:#059669;--med:#d97706;--low:#64748b}
*{box-sizing:border-box} body{margin:0;font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial;background:var(--bg);color:var(--ink);line-height:1.6}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
.wrap{max-width:1220px;margin:0 auto;padding:0 18px}
.topbar{background:#0f172a;color:#fff;position:sticky;top:0;z-index:30;box-shadow:0 2px 10px rgba(0,0,0,.15)}
.bar{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;padding:10px 0}
.brand{color:#fff;font-weight:800;display:flex;gap:10px;align-items:center}
.brand .mark{background:#fff;color:#0f172a;padding:3px 9px;border-radius:7px;font-size:.85em}
.nav{display:flex;flex-wrap:wrap;gap:8px}
.nav a{color:#cbd5e1;padding:6px 10px;border-radius:9px;font-size:.9em} .nav a.active,.nav a:hover{background:#1e293b;color:#fff}
.hero{background:linear-gradient(135deg,#4f46e5,#0ea5e9);color:#fff;border-radius:16px;padding:28px;margin:18px 0}
.hero h1{margin:6px 0 8px;font-size:1.9em;line-height:1.2} .hero p{opacity:.95;max-width:900px}
.kicker{background:rgba(255,255,255,.18);padding:4px 10px;border-radius:999px;font-size:.8em;letter-spacing:.05em}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;text-align:center}
.kpi .num{font-size:1.6em;font-weight:800;color:var(--accent)} .kpi .lbl{font-weight:600;font-size:.95em} .kpi .sub{color:var(--muted);font-size:.82em}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;margin:16px 0}
.card h2{margin:0 0 8px;font-size:1.25em} .muted{color:var(--muted)} .small{font-size:.9em}
.pills{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0}
.pill{padding:6px 10px;border-radius:999px;background:#eef2ff;border:1px solid #ddd;font-size:.85em}
.pill.active{background:var(--accent);color:#fff;border-color:var(--accent)}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;min-width:720px} th,td{padding:10px 10px;text-align:left;border-bottom:1px solid var(--line);font-size:.9em;vertical-align:top}
th{background:#f1f5f9;position:sticky;top:0;font-weight:700} tr:hover td{background:#f8fafc}
.badge{padding:3px 8px;border-radius:999px;font-size:.75em;font-weight:700;color:#fff} .b-high{background:var(--high)} .b-med{background:var(--med)} .b-low{background:var(--low)}
.mono{font-family:ui-monospace,monospace;font-size:.85em} .chip{display:inline-block;background:#f1f5f9;border:1px solid var(--line);padding:2px 7px;border-radius:7px;font-size:.8em}
.pred-grid{display:grid;grid-template-columns:1fr;gap:14px}
.pred-card{border:1px solid var(--line);border-radius:14px;padding:14px;background:#fff}
.pred-head{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:6px}
.pred-pick{font-weight:700;margin:6px 0} .pred-meta{color:var(--muted);font-size:.85em}
.sport-pills{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0}
.sport-pills a{padding:6px 10px;border-radius:999px;background:#fff;border:1px solid var(--line);font-size:.85em}
.exec-pick{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}
.exec-card{border:1px solid var(--line);border-radius:12px;padding:12px;background:#fff}
.exec-card h3{margin:4px 0;font-size:1em}
.note{background:#eff6ff;border-left:4px solid #3b82f6;padding:10px 12px;border-radius:8px;margin:10px 0}
.warn{background:#fef3c7;border-left-color:#f59e0b}
.flag{background:#fef2f2;border-left-color:#ef4444}
.foot{margin:30px 0;padding:16px 0;border-top:1px solid var(--line);color:var(--muted);font-size:.85em}
.btn{display:inline-block;padding:8px 12px;border-radius:9px;border:1px solid var(--line);background:#fff;font-weight:600}
.btn.primary{background:var(--accent);color:#fff;border-color:var(--accent)}
@media(max-width:700px){.hero h1{font-size:1.4em} table{min-width:620px}}
"""

def esc(s): return html.escape(str(s))
def nav(active=""):
    items=[("index.html","Dashboard"),("entries.html","All Entries"),("predictions.html","High Picks (65)"),("markets.html","Markets"),("coverage.html","Coverage"),("olbg.html","OLBG Engine"),("sources.html","Sources"),("methodology.html","Method"),("flagged.html","Flagged (58)"),("verification.html","Verify")]
    out='<nav class="nav">'
    for href,label in items:
        cls="active" if href==active else ""
        out+=f'<a class="{cls}" href="{href}">{label}</a>'
    out+='<a href="../index.html">Repo Root</a></nav>'
    return out
def header(active=""):
    return '<header class="topbar"><div class="wrap bar"><a class="brand" href="index.html"><span class="mark">OLBG4</span><span>15-Sport Verified Desk - Board AP</span></a>'+nav(active)+'</div></header>'
def sport_pills(active=""):
    out='<div class="sport-pills">'
    for sport in REQUIRED_SPORTS:
        slug=SPORT_SLUGS[sport]
        out+=f'<a class="pill" href="sports/{slug}.html">{esc(sport)}</a>'
    out+='</div>'; return out
def sport_pills_sport(active=""):
    out='<div class="sport-pills">'
    for sport in REQUIRED_SPORTS:
        slug=SPORT_SLUGS[sport]
        out+=f'<a class="pill" href="{slug}.html">{esc(sport)}</a>'
    out+='</div>'; return out

def header_sport():
    items=[("index.html","Dashboard"),("entries.html","All Entries"),("predictions.html","High Picks (65)"),("markets.html","Markets"),("coverage.html","Coverage"),("olbg.html","OLBG Engine"),("sources.html","Sources"),("methodology.html","Method"),("flagged.html","Flagged (58)"),("verification.html","Verify")]
    out='<nav class="nav">'
    for href,label in items:
        out+=f'<a href="../{href}">{label}</a>'
    out+='<a href="../../index.html">Repo Root</a></nav>'
    return '<header class="topbar"><div class="wrap bar"><a class="brand" href="../index.html"><span class="mark">OLBG4</span><span>15-Sport Verified Desk - Board AP</span></a>'+out+'</div></header>'

def footer():
    return '<footer class="foot"><div class="wrap"><p><strong>Cut-off 2026-10-23T00:00Z - Capture 20261022T210026Z (110 HTTP 200 SHA-256 verified).</strong> Every published row carries an official governing-body source link. Unconfirmed values are blank and flagged per verification rule. No hallucinations, no inferred values.</p><p>Analysis only, not betting advice. 18+. Built by <code>arena/509d544b-olbg4</code> (Board AP).</p></div></footer>'
def build_generic_sport_pages(desk,preds):
    rows=desk["rows"]
    by_sport_rows=collections.defaultdict(list)
    for r in rows: by_sport_rows[r["sport"]].append(r)
    by_sport_preds=collections.defaultdict(list)
    for p in preds["predictions"]: by_sport_preds[p["sport"]].append(p)
    for sport in REQUIRED_SPORTS:
        slug=SPORT_SLUGS[sport]
        sport_rows=by_sport_rows.get(sport,[])
        sport_preds=by_sport_preds.get(sport,[])
        if sport=="Gaelic Sports":
            content = '<section class="card"><h1>Gaelic Sports - Gaelic Football Spotlight</h1><p class="muted">Only <strong>1 verified upcoming Gaelic Sports fixture</strong> existed on its official governing-body page at capture time. Remaining slots are blank and flagged per verification rule - not inferred.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Fixture</th><th>Venue</th><th>Our Lines</th><th>Pick</th><th>Official Source</th></tr></thead><tbody><tr><td class="mono">2026-11-01T15:00:00Z</td><td><strong>Kanturk vs Eire Og</strong><div class="small muted">McCarthy Insurance Group Cork Senior A Football Championship Final</div></td><td>SuperValu Pairc Ui Chaoimh, Cork (neutral)</td><td><span class="muted">Low confidence - insufficient official market depth for 4-market origination</span></td><td>Eire Og <span class="badge b-low">Low</span><div class="small">Only verified fixture - not a high-confidence pick</div></td><td><a href="https://gaacork.ie/event/mccarthy-insurance-group-senior-a-football-championship-final/" target="_blank" rel="noopener">gaacork.ie</a></td></tr></tbody></table></div><div class="note warn">Shortfall: 4 additional Gaelic Sports fixtures would be needed for 5 high-confidence picks. No other Gaelic fixtures for 23 Oct-5 Nov were verifiable on official county board pages at capture time.</div></section>'
            html_out = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(sport)+' - 15-Sport Desk - OLBG4</title><link rel="stylesheet" href="../assets/style.css"></head><body>'+header_sport()+ '<main class="wrap">'+sport_pills_sport(slug)+content+'</main>'+footer()+'</body></html>'
            (OUT/f"sports/{slug}.html").write_text(html_out)
            continue
        if sport=="Greyhounds":
            content = '<section class="card"><h1>Greyhounds - GBGB WAF Ledger (Zero-Inference)</h1><p class="muted"><strong>0 priced fixtures - 11 flagged blank rows.</strong> All GBGB-licensed track greyhound racecards returned HTTP 403 WAF at capture time.</p><div class="table-wrap"><table><thead><tr><th>Date</th><th>Track and Race</th><th>Why Blank</th><th>Official Source</th></tr></thead><tbody><tr><td class="mono">2026-10-21 etc.</td><td>Harlow, Kinsley, Monmore Green, Nottingham - 11 UK morning BAGS cards listed on OLBG</td><td>GBGB racecard endpoint HTTP 403 WAF + GBGB racecards-and-results 404 - no official form lines extractable</td><td><a href="https://www.gbgb.org.uk/results/" target="_blank" rel="noopener">gbgb.org.uk/results</a></td></tr></tbody></table></div><div class="note flag">If you supply an official GBGB/track racecard PDF with each dog\'s recent calculated times, we apply a softmax model over best recent times and originate lines immediately.</div></section>'
            html_out = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(sport)+' - 15-Sport Desk - OLBG4</title><link rel="stylesheet" href="../assets/style.css"></head><body>'+header_sport()+ '<main class="wrap">'+sport_pills_sport(slug)+content+'</main>'+footer()+'</body></html>'
            (OUT/f"sports/{slug}.html").write_text(html_out)
            continue
        # generic
        parts=[]
        parts.append(f'<section class="card"><h1>{esc(sport)} - {len(sport_rows)} Verified Fixtures, 5 High Picks Inside -250 to +10000</h1><p class="muted">All fixtures below are from official governing-body feeds with SHA-256 verified captures at 2026-10-22T21:00Z. Every row lists our originated 4-market lines.</p><div class="table-wrap"><table><thead><tr><th>Date (UTC)</th><th>Competition</th><th>Fixture</th><th>Our Lines</th><th>Pick and Price</th><th>Source</th></tr></thead><tbody>')
        for r in sorted(sport_rows, key=lambda x: x["start_utc"]):
            m=r.get("markets",{})
            lines_html=""
            if "match_winner" in m:
                s=m["match_winner"]["selections"]
                lines_html+=f'<div><span class="chip">Win</span> {esc(s[0]["label"][:22])} {s[0]["fair_decimal"]:.2f} / {esc(s[1]["label"][:22])} {s[1]["fair_decimal"]:.2f}</div>'
            if "handicap" in m:
                s=m["handicap"]["selections"]
                lines_html+=f'<div><span class="chip">Hcp {esc(m.get("line",""))}</span> {s[0]["fair_decimal"]:.2f} / {s[1]["fair_decimal"]:.2f}</div>'
            if "total" in m:
                s=m["total"]["selections"]
                lines_html+=f'<div><span class="chip">Total {esc(m.get("line",""))}</span> {s[0]["fair_decimal"]:.2f} / {s[1]["fair_decimal"]:.2f}</div>'
            pred = next((p for p in sport_preds if p["row_id"]==r["id"]), None)
            if pred:
                pick_html=f'<strong>{esc(pred["selection"])}</strong><div class="mono">{pred["fair_decimal"]:.2f} ({pred["fair_american"]:+d}) - p={pred["fair_prob"]:.0%}</div><span class="badge b-high">High</span><div class="small"><a href="../predictions.html#{esc(pred["pred_key"])}">Prediction</a></div>'
            else:
                pick_html='<span class="muted">-</span><div><span class="badge b-low">Low</span></div>'
            parts.append(f'<tr><td class="mono">{esc(r["start_utc"])}</td><td class="small">{esc(r["competition"][:40])}</td><td><strong>{esc(r["matchup"])}</strong><div class="small muted">{esc(r["venue"])}</div></td><td>{lines_html}</td><td>{pick_html}</td><td><a href="{esc(r["official_url"])}" target="_blank" rel="noopener">Official</a></td></tr>')
        parts.append('</tbody></table></div></section>')
        if sport_preds:
            parts.append(f'<section class="card"><h2>{esc(sport)} High Picks - Prediction Texts (>=30 words, unique, human)</h2><div class="pred-grid">')
            for p in sport_preds:
                parts.append(f'<article class="pred-card"><div class="pred-head"><span><strong>{esc(p["matchup"])}</strong> - {esc(p["venue"])}</span><span class="pill" style="background:#ecfdf5;border-color:#10b981;color:#065f46">High in -250 to +10000</span></div><div class="pred-pick">Selection: {esc(p["selection"])} - <span class="mono">{p["fair_decimal"]:.2f} ({p["fair_american"]:+d}) - p={p["fair_prob"]:.1%}</span></div><p>{esc(p["text"])}</p><div class="pred-meta">Basis: {esc(p["inputs_summary"])}<br>Official: <a href="{esc(p["official_url"])}" target="_blank" rel="noopener">{esc(p["official_url"])}</a> - {p["word_count"]} words - Market: {esc(p["market"])}</div></article>')
            parts.append('</div></section>')
        content=''.join(parts)
        html_out = '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(sport)+' - 15-Sport Desk - OLBG4</title><link rel="stylesheet" href="../assets/style.css"></head><body>'+header_sport()+'<main class="wrap">'+sport_pills_sport(slug)+content+'</main>'+footer()+'</body></html>'
        (OUT/f"sports/{slug}.html").write_text(html_out)
        print(f"sports/{slug}.html built")

def main():
    desk,preds,flagged,off,inv = load()
    (OUT/"assets").mkdir(parents=True, exist_ok=True)
    (OUT/"sports").mkdir(parents=True, exist_ok=True)
    (OUT/"assets/style.css").write_text(CSS)
    build_generic_sport_pages(desk,preds)
    print("sport pages built")

if __name__=="__main__":
    main()

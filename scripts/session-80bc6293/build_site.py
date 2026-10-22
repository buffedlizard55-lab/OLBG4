#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) - build the GitHub Pages dashboard.

Reads only Board AF data files and writes only inside session-80bc6293/.
Every table row carries its official source link; a value that no official source printed is
left blank and the row is flagged, never inferred.
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")
OUT = os.path.join(ROOT, "session-80bc6293")

SLUG = {
    "Ice Hockey": "ice-hockey", "Baseball": "baseball", "Rugby Union": "rugby-union",
    "Tennis": "tennis", "Motor Racing": "motor-racing", "Basketball": "basketball",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Handball": "handball",
    "Volleyball": "volleyball", "Aussie Rules": "aussie-rules", "Esports": "esports",
    "Table Tennis": "table-tennis", "Badminton": "badminton", "Gaelic Football": "gaelic-football",
    "Greyhounds": "greyhounds", "Rugby League": "rugby-league", "Golf": "golf",
    "Football": "excluded-football", "Horse Racing": "excluded-horse-racing",
    "Specials": "excluded-specials", "American Football": "excluded-american-football",
    "Boxing": "excluded-boxing", "Cycling": "excluded-cycling", "Hurling": "excluded-hurling",
}

CSS = """
:root{--bg:#0f1115;--card:#171a21;--line:#252a34;--fg:#e8ebf0;--mut:#9aa4b2;--acc:#4ea1ff;
--ok:#3ddc97;--warn:#ffb454;--bad:#ff6b6b;--chip:#20262f}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
header{padding:26px 28px 18px;border-bottom:1px solid var(--line);background:linear-gradient(180deg,#141821,#0f1115)}
header h1{margin:0 0 6px;font-size:23px;letter-spacing:.2px}
header p{margin:0;color:var(--mut);max-width:1050px}
nav{display:flex;flex-wrap:wrap;gap:8px;padding:14px 28px;border-bottom:1px solid var(--line);background:#12151c;position:sticky;top:0;z-index:5}
nav a{color:var(--fg);text-decoration:none;background:var(--chip);border:1px solid var(--line);padding:6px 11px;border-radius:999px;font-size:13px}
nav a:hover{border-color:var(--acc);color:var(--acc)}
nav a.here{background:var(--acc);color:#08111f;border-color:var(--acc);font-weight:600}
main{padding:22px 28px 60px;max-width:1500px}
h2{font-size:19px;margin:30px 0 10px}
h3{font-size:16px;margin:22px 0 8px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:16px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card b{display:block;font-size:26px;line-height:1.1}
.card span{color:var(--mut);font-size:12.5px;text-transform:uppercase;letter-spacing:.6px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13.5px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#1b2029;color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:52px}
tr:last-child td{border-bottom:none}
tr:hover td{background:#1b212b}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
a{color:var(--acc)}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;border:1px solid var(--line);background:var(--chip)}
.hi{color:var(--ok);border-color:#1d5c46}.med{color:var(--warn);border-color:#5c4520}.lo{color:var(--mut)}
.blank{color:#5d6773;font-style:italic}
.note{background:#141a24;border-left:3px solid var(--acc);padding:12px 14px;border-radius:8px;color:#cfd8e3;margin:12px 0}
.warn{background:#1e1a12;border-left:3px solid var(--warn)}
.pred{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.pred h4{margin:0 0 6px;font-size:16px}
.pred .meta{color:var(--mut);font-size:12.5px;margin-bottom:10px}
.pred p{text-align:left}
.pred ul{margin:10px 0 0;padding-left:18px;color:#c9d3de;font-size:12.8px}
.pred li{margin:3px 0}
.filters{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px}
.filters select,.filters input{background:#12161d;color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:7px 10px;font-size:13px}
footer{padding:20px 28px 40px;color:var(--mut);font-size:12.5px;border-top:1px solid var(--line)}
.small{color:var(--mut);font-size:12.5px}
code{background:#12161d;border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:12.5px}
"""

JS = """
function filterTable(tid){
  var t=document.getElementById(tid); if(!t) return;
  var inputs=t.querySelectorAll('thead select, thead input');
  var rows=t.querySelectorAll('tbody tr');
  rows.forEach(function(r){
    var show=true;
    inputs.forEach(function(inp){
      var idx=parseInt(inp.getAttribute('data-col'),10);
      var cell=r.cells[idx]; if(!cell) return;
      var v=(cell.getAttribute('data-v')||cell.textContent||'').toLowerCase();
      var want=(inp.value||'').toLowerCase();
      if(want && v.indexOf(want)===-1) show=false;
    });
    r.style.display=show?'':'none';
  });
}
"""

PAGES = ["index.html", "entries.html", "picks.html", "markets.html", "coverage.html", "olbg.html",
         "methodology.html", "sources.html", "flagged.html", "review.html", "verification.html"]


BLANK = '<span class="blank">blank</span>'
NO_MARKET = '<span class="blank">no market originated</span>'
CHIP_OPEN = '<span class="'
CHIP_MID = '">'
CHIP_CLOSE = "</span>"
STATUS_MET = '<span class="chip hi">target met</span>'
STATUS_SHORT = '<span class="chip med">shortfall - see coverage</span>'
NONE_ORIGINATED = '<span class="blank">none originated</span>'


def review_link(url):
    if not url:
        return '<span class="blank">no URL</span>'
    return '<a href="' + e(url) + '" rel="nofollow noopener" target="_blank">check &#8599;</a>'


def conf_chip(conf: str) -> str:
    if conf == "High":
        return CHIP_OPEN + "chip hi" + CHIP_MID + e(conf) + CHIP_CLOSE
    if conf == "Medium":
        return CHIP_OPEN + "chip med" + CHIP_MID + e(conf) + CHIP_CLOSE
    if conf == "Low":
        return CHIP_OPEN + "chip lo" + CHIP_MID + e(conf) + CHIP_CLOSE
    return BLANK


def e(x) -> str:
    return html.escape("" if x is None else str(x))


def cell(v, cls=""):
    if v in (None, "", []):
        return f'<td class="{cls}"><span class="blank">blank — unverified</span></td>'
    return f'<td class="{cls}">{e(v)}</td>'


def num(v, suffix=""):
    if v in (None, ""):
        return '<td class="num"><span class="blank">blank</span></td>'
    return f'<td class="num">{e(v)}{suffix}</td>'


def src_link(row) -> str:
    u = row.get("source_url")
    if not u:
        return '<span class="blank">no source</span>'
    return f'<a href="{e(u)}" rel="nofollow noopener" target="_blank">{e(row.get("source_name") or u)[:64]} ↗</a>'


def page(title, active, body, sub="") -> str:
    nav = "".join(
        f'<a class="{"here" if p == active else ""}" href="{("./" + p) if not p.startswith("sports/") else p}">{e(n)}</a>'
        for p, n in [("index.html", "Dashboard"), ("entries.html", "All entries"), ("picks.html", "High-confidence picks"),
                     ("markets.html", "Markets"), ("coverage.html", "Sport coverage"), ("olbg.html", "OLBG reverse-engineering"),
                     ("methodology.html", "Methodology"), ("sources.html", "Sources"), ("verification.html", "Verification"),
                     ("flagged.html", "Flagged for review"), ("review.html", "Repo review")]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — Board AF · OLBG4</title>
<link rel="stylesheet" href="./assets/site.css"><script src="./assets/site.js" defer></script>
</head><body>
<header><h1>{e(title)}</h1><p>{sub}</p></header>
<nav>{nav}</nav>
<main>{body}</main>
<footer>Board AF · session <code>arena/80bc6293-olbg4</code> · generated {NOW} UTC from committed official bytes in
<code>data/session-80bc6293/capture/</code>. Every row links to the source that produced it; any value no official source
printed is left blank and flagged.</footer>
</body></html>"""


NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "authored_predictions.json"), encoding="utf-8"))
    cands = json.load(open(os.path.join(DATA, "high_candidates.json"), encoding="utf-8"))
    review = json.load(open(os.path.join(DATA, "review.json"), encoding="utf-8")) if os.path.exists(os.path.join(DATA, "review.json")) else {"findings": [], "datasets": []}
    gaps = json.load(open(os.path.join(DATA, "flagged_source_gaps.json"), encoding="utf-8"))
    olbg = json.load(open(os.path.join(DATA, "parsed", "olbg.json"), encoding="utf-8"))
    assumptions = desk["model_assumptions"]
    rows = desk["rows"]
    priced = [r for r in rows if not r.get("listing_only")]
    listing = [r for r in rows if r.get("listing_only")]
    high_rows = [r for r in priced if r["confidence"] == "High"]
    sports_in = sorted(({r["sport"] for r in rows} |
                        {s for s, v in desk["coverage"].items() if v.get("in_scope")}) -
                       {"Football", "Horse Racing", "Specials", "American Football", "Boxing", "Cycling", "Hurling"})
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    open(os.path.join(OUT, "assets", "site.css"), "w").write(CSS)
    open(os.path.join(OUT, "assets", "site.js"), "w").write(JS)

    n_markets = sum(len(r["markets"]) for r in priced)
    # ---------------------------------------------------------- index
    cov_rows = ""
    for s in sports_in:
        sr = [r for r in rows if r["sport"] == s]
        sp = [r for r in sr if not r.get("listing_only")]
        sh = [r for r in sp if r["confidence"] == "High"]
        spreds = [p for p in preds["predictions"] if p["sport"] == s]
        status = STATUS_MET if len(spreds) >= 5 else STATUS_SHORT
        cov_rows += (f'<tr><td><a href="./sports/{SLUG[s]}.html">{e(s)}</a></td><td class="num">{len(sr)}</td>'
                     f'<td class="num">{len(sp)}</td><td class="num">{sum(len(r["markets"]) for r in sp)}</td>'
                     f'<td class="num">{len(sh)}</td><td class="num">{len(spreds)}</td>'
                     f'<td class="num">5</td><td>{status}</td></tr>')
    body = f"""
<div class="cards">
 <div class="card"><b>{len(rows)}</b><span>Rows published</span></div>
 <div class="card"><b>{len(priced)}</b><span>Rows with our own line</span></div>
 <div class="card"><b>{n_markets}</b><span>Markets originated</span></div>
 <div class="card"><b>{len(high_rows)}</b><span>High-confidence picks</span></div>
 <div class="card"><b>{len(cands['candidates'])}</b><span>In-window High candidates</span></div>
 <div class="card"><b>{len(preds['predictions'])}</b><span>Written predictions</span></div>
 <div class="card"><b>{len(listing)}</b><span>Listed, deliberately unpriced</span></div>
 <div class="card"><b>{len(gaps)+len([r for r in listing if r.get('listing_reason')])}</b><span>Flagged items</span></div>
</div>
<div class="note"><b>What this desk is.</b> Board AF re-read OLBG.com's sport and market taxonomy live on
{e(desk['generated_at_utc'][:10])}, then read fixtures and form <i>only</i> from official league, tour, federation and
regulator endpoints, captured as committed bytes with SHA-256 in <code>data/session-80bc6293/capture/</code>. Every price
below is our own: fair decimal = 1 ÷ model probability, with no bookmaker margin added. Where a league publishes market
prices on its own feed (NHL.com does) that price is recorded separately and used only for the −250…+10,000 window test.</div>
<h2>In-scope sport coverage</h2>
<p class="small">Every OLBG sport except soccer, boxing, UFC/MMA, football (association), American football, hurling,
horse racing, cycling and specials. The brief's target is five written high-confidence predictions per sport per day.</p>
<table><thead><tr><th>Sport</th><th class="num">Rows</th><th class="num">Priced</th><th class="num">Markets</th>
<th class="num">High rows</th><th class="num">Predictions</th><th class="num">Target</th><th>Status</th></tr></thead>
<tbody>{cov_rows}</tbody></table>
<h2>Where to look</h2>
<table><thead><tr><th>Page</th><th>What it shows</th></tr></thead><tbody>
<tr><td><a href="./entries.html">All entries</a></td><td>Every published row with its fixture, our line, pick, confidence and official source link, filterable by sport / confidence / market.</td></tr>
<tr><td><a href="./picks.html">High-confidence picks</a></td><td>The written predictions, the in-window High candidate scan across every market, and the Medium rows that came closest.</td></tr>
<tr><td><a href="./markets.html">Markets</a></td><td>Which markets were investigated per sport and which could be originated from verified inputs.</td></tr>
<tr><td><a href="./coverage.html">Sport coverage</a></td><td>The five-per-sport target, what was delivered and the exact official endpoint that blocked each gap.</td></tr>
<tr><td><a href="./olbg.html">OLBG reverse-engineering</a></td><td>The 24-sport taxonomy with IDs and scope decisions, the URL patterns and the market names OLBG itself prints.</td></tr>
<tr><td><a href="./flagged.html">Flagged for review</a></td><td>Every unconfirmed value, declared modelling constant, source failure and prediction shortfall, with links.</td></tr>
<tr><td><a href="./review.html">Repo review</a></td><td>The line-by-line audit of the shared canonical board and peer desks: {review.get('findings_total', 0)} findings across {review.get('rows_reviewed', 0)} rows.</td></tr>
</tbody></table>"""
    open(os.path.join(OUT, "index.html"), "w").write(
        page("OLBG4 · Board AF desk", "index.html", body,
             f"Reverse-engineered OLBG.com coverage, our own originated lines and verified high-confidence predictions · cut-off {e(desk['cutoff_utc'])}"))

    # ---------------------------------------------------------- entries
    trs = ""
    for r in rows:
        mk = r.get("markets") or []
        conf = r.get("confidence") or ""
        chip = {"High": "chip hi", "Medium": "chip med", "Low": "chip lo"}.get(conf, "chip lo")
        fixture = f'{e(r.get("away"))} @ {e(r.get("home"))}' if r.get("away") else e(r.get("home") or r.get("venue") or "")
        markets_txt = "; ".join(f'{m["market"]}: {m["selection"]} p={m["p"]} ({m["fair_american"]:+d})' for m in mk[:4])
        trs += (f'<tr><td>{e(r["id"])}</td><td data-v="{e(r["sport"])}">{e(r["sport"])}</td>'
                f'<td>{e(r.get("competition",""))}</td><td>{e(r.get("date",""))}</td><td>{fixture}</td>'
                f'<td>{e(r.get("venue",""))}</td>'
                f'<td data-v="{e(r.get("pick",""))}">{e(r.get("pick","")) or BLANK}</td>'
                f'{num(r.get("pick_probability"))}{num(r.get("pick_fair_american"))}'
                f'{num(r.get("official_market_american_for_pick"))}'
                f'<td data-v="{e(conf)}">{conf_chip(conf)}</td>'
                f'<td class="small">{e(markets_txt) or NO_MARKET}</td>'
                f'<td>{src_link(r)}</td></tr>')
    body = f"""<h2>All entries ({len(rows)} rows)</h2>
<div class="note">Rows with a blank pick, blank price and blank confidence are fixtures we could verify on OLBG's own
listing but could not price, because the official governing-body endpoint did not publish the numbers a line needs.
The reason is on each sport page and on <a href="./flagged.html">Flagged for review</a>.</div>
<div class="filters">
<select onchange="filterTable('entries')" data-for="entries"><option value="">all sports</option>{''.join(f'<option>{e(s)}</option>' for s in sorted({r['sport'] for r in rows}))}</select>
</div>
<table id="entries"><thead><tr>
<th>ID</th><th><select data-col="1" onchange="filterTable('entries')"><option value="">Sport</option>{''.join(f'<option>{e(s)}</option>' for s in sorted({r['sport'] for r in rows}))}</select></th>
<th>Competition</th><th>Date</th><th>Fixture</th><th>Venue</th>
<th><input data-col="6" onkeyup="filterTable('entries')" placeholder="Pick…"></th>
<th class="num">p</th><th class="num">Fair (US)</th><th class="num">Official mkt (US)</th>
<th><select data-col="10" onchange="filterTable('entries')"><option value="">Confidence</option><option>High</option><option>Medium</option><option>Low</option></select></th>
<th>Markets originated (first four)</th><th>Official source</th></tr></thead><tbody>{trs}</tbody></table>"""
    open(os.path.join(OUT, "entries.html"), "w").write(page("All entries", "entries.html", body, "Every row we publish, with our own line and the official source that produced the fixture."))

    # ---------------------------------------------------------- picks
    cards = ""
    for p in preds["predictions"]:
        cards += f"""<div class="pred"><h4>{e(p['selection'])} — {e(p['market'])}</h4>
<div class="meta">{e(p['fixture'])} · {e(p['date'])} · {e(p['venue'])}<br>
Model probability <b>{p['probability']:.3f}</b> · our fair price <b>{p['fair_american']:+d}</b> ({p['fair_decimal']:.4f}) ·
inside −250…+10,000: <b>{'yes' if p['in_window'] else 'no'}</b> ({e(p['window_basis'])})</div>
<p>{e(p['text'])}</p>
<ul>{''.join('<li>'+e(f)+'</li>' for f in p['facts'])}
<li>Source: <a href="{e(p['source_url'])}" rel="nofollow noopener" target="_blank">{e(p['source_url'])} ↗</a></li></ul></div>"""
    cand = ""
    for c in cands["candidates"]:
        cand += (f'<tr><td>{e(c["row_id"])}</td><td>{e(c["sport"])}</td><td>{e(c["date"])}</td><td>{e(c["fixture"])}</td>'
                 f'<td>{e(c["market"])}</td><td><b>{e(c["selection"])}</b></td>{num(c["p"])}{num(c["fair_american"])}'
                 f'<td><a href="{e(c["source_url"])}" rel="nofollow noopener" target="_blank">official source ↗</a></td></tr>')
    near = [r for r in priced if r["confidence"] == "Medium" and (r.get("pick_probability") or 0) >= 0.60]
    near.sort(key=lambda r: -(r.get("pick_probability") or 0))
    near_rows = "".join(
        f'<tr><td>{e(r["id"])}</td><td>{e(r["sport"])}</td><td>{e(r["date"])}</td>'
        f'<td>{e(r.get("away"))} @ {e(r.get("home"))}</td><td>{e(r["pick"])}</td>{num(r["pick_probability"])}'
        f'{num(r["pick_fair_american"])}<td class="small">{e(r.get("evidence_cap") or ("price outside −250…+10,000" if not r.get("pick_in_window") else "sample below 8 official matches"))}</td>'
        f'<td><a href="{e(r["source_url"])}" rel="nofollow noopener" target="_blank">official source ↗</a></td></tr>'
        for r in near[:40])
    body = f"""<h2>Written high-confidence predictions ({len(preds['predictions'])})</h2>
<div class="note">Hand-written, one per selection, {min(len(p['text'].split()) for p in preds['predictions'])}–{max(len(p['text'].split()) for p in preds['predictions'])} words each.
Every number in every card is re-checked by <code>scripts/session-80bc6293/verify.py</code> against that row's official
model inputs, and no sentence frame is repeated. Player names are deliberately not used: the official bytes captured
publish team-level form (and ATP seeds) but not player form — that gap is flagged rather than filled in.</div>
{cards}
<h2>In-window High candidate scan across every market ({cands['total']})</h2>
<p class="small">Rule: {e(cands['rule'])}</p>
<table><thead><tr><th>Row</th><th>Sport</th><th>Date</th><th>Fixture</th><th>Market</th><th>Selection</th>
<th class="num">p</th><th class="num">Fair (US)</th><th>Source</th></tr></thead><tbody>{cand}</tbody></table>
<h2>Closest Medium rows (probability ≥ 0.60) — not sold as High</h2>
<table><thead><tr><th>Row</th><th>Sport</th><th>Date</th><th>Fixture</th><th>Pick</th><th class="num">p</th>
<th class="num">Fair (US)</th><th>Why it is not High</th><th>Source</th></tr></thead><tbody>{near_rows}</tbody></table>"""
    open(os.path.join(OUT, "picks.html"), "w").write(page("High-confidence picks", "picks.html", body, "Written predictions for picks at ≥70% model probability whose price sits inside −250…+10,000 American odds."))

    # ---------------------------------------------------------- markets
    mrows = ""
    for s in sports_in:
        sr = [r for r in priced if r["sport"] == s]
        names = sorted({m["market"].split(" Over ")[0].split(" Under ")[0]
                        for r in sr for m in r["markets"]})
        mrows += (f'<tr><td><a href="./sports/{SLUG[s]}.html">{e(s)}</a></td><td class="num">{len(sr)}</td>'
                  f'<td class="num">{sum(len(r["markets"]) for r in sr)}</td><td class="small">{e(", ".join(names)) or NONE_ORIGINATED}</td>'
                  f'<td class="small">{e(assumptions["listing_reasons"].get(s, ""))[:300]}</td></tr>')
    body = f"""<h2>Markets investigated and originated</h2>
<div class="note">The brief asks us to investigate every available market. OLBG's own pages print these market names —
{e(', '.join(sorted({m for v in olbg['sports'].values() for m in v.get('markets_seen', [])})[:26]))} — so the full list is
published on the <a href="./olbg.html">OLBG reverse-engineering</a> page. A market is only originated here when an official
endpoint published the inputs it needs; otherwise the cell stays blank and the reason is recorded.</div>
<table><thead><tr><th>Sport</th><th class="num">Priced fixtures</th><th class="num">Markets originated</th>
<th>Markets we could originate</th><th>Why the rest stay blank</th></tr></thead><tbody>{mrows}</tbody></table>"""
    open(os.path.join(OUT, "markets.html"), "w").write(page("Markets", "markets.html", body, "Match winner, handicap and total coverage per sport, plus the markets OLBG itself lists."))

    # ---------------------------------------------------------- coverage
    cov = desk["coverage"]
    crows = ""
    for s, info in sorted(cov.items()):
        sr = [r for r in rows if r["sport"] == s]
        sp = [r for r in sr if not r.get("listing_only")]
        spred = len([p for p in preds["predictions"] if p["sport"] == s])
        scope = "in scope" if info.get("in_scope") else "<b>excluded by the brief</b>"
        crows += (f'<tr><td>{e(s)}</td><td class="num">{e(info.get("olbg_sport_id"))}</td><td>{scope}</td>'
                  f'<td class="num">{info.get("events_listed", 0)}</td><td class="num">{len(sr)}</td><td class="num">{len(sp)}</td>'
                  f'<td class="num">{spred} / 5</td><td class="small">{e(assumptions["listing_reasons"].get(s, info.get("reason", "")))[:420]}</td>'
                  f'<td><a href="{e(info.get("hub_url",""))}" rel="nofollow noopener" target="_blank">OLBG hub ↗</a></td></tr>')
    body = f"""<h2>Sport coverage against the five-per-sport target</h2>
<div class="note warn"><b>Honest result.</b> The target is five written high-confidence predictions per sport per day.
That was met for Ice Hockey, where 145 fixtures across three official NHL schedule weeks produced {cands['total']} market
selections at ≥70% model probability with our fair price inside −250…+10,000. For every other sport the honest answer is
below: either the governing body did not publish readable fixture/form data to our capture, or the sport's own calendar
this week has no match market to originate (single-field events in golf and motor racing, multi-runner races in
greyhounds). Each gap names the endpoint that failed and the HTTP status it returned, so a reviewer can re-try it.</div>
<table><thead><tr><th>Sport</th><th class="num">OLBG ID</th><th>Scope</th><th class="num">OLBG events listed</th>
<th class="num">Rows published</th><th class="num">Priced</th><th class="num">Predictions / target</th>
<th>Why (official endpoint + status)</th><th>OLBG hub</th></tr></thead><tbody>{crows}</tbody></table>"""
    open(os.path.join(OUT, "coverage.html"), "w").write(page("Sport coverage", "coverage.html", body, "What OLBG lists, what we could verify officially, what we priced, and the exact reason for every gap."))

    # ---------------------------------------------------------- olbg reverse-engineering
    srows = ""
    for s, info in sorted(olbg["sports"].items(), key=lambda kv: kv[1]["sport_id"]):
        srows += (f'<tr><td class="num">{info["sport_id"]}</td><td>{e(s)}</td>'
                  f'<td>{"<span class=chip>in scope</span>" if s not in ("Football","Horse Racing","Specials","American Football","Boxing","Cycling","Hurling") else "<span class=chip lo>excluded</span>"}</td>'
                  f'<td class="num">{info["events_listed"]}</td><td class="small">{e(", ".join(info.get("markets_seen", []))[:180])}</td>'
                  f'<td><a href="{e(info["hub_url"])}" rel="nofollow noopener" target="_blank">{e(info["hub_url"])} ↗</a></td></tr>')
    body = f"""<h2>How OLBG.com is put together</h2>
<div class="note">Read live from OLBG's own sitemap and sport hubs on {e(NOW[:10])}. The trailing number on every
OLBG betting-tips URL is the <b>sport ID</b>, not a market ID. URL patterns:</div>
<table><thead><tr><th>Object</th><th>Pattern</th><th>Example read in this capture</th></tr></thead><tbody>
<tr><td>Sport hub</td><td><code>/betting-tips/&lt;Sport&gt;/&lt;sport_id&gt;</code></td><td><a href="https://www.olbg.com/betting-tips/Darts/15" rel="nofollow noopener" target="_blank">olbg.com/betting-tips/Darts/15 ↗</a></td></tr>
<tr><td>Competition</td><td><code>/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;sport_id&gt;</code></td><td><a href="https://www.olbg.com/betting-tips/Baseball/MLB/MLB/12" rel="nofollow noopener" target="_blank">olbg.com/betting-tips/Baseball/MLB/MLB/12 ↗</a></td></tr>
<tr><td>Event</td><td><code>/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;Event&gt;/&lt;sport_id&gt;?event_id=&lt;id&gt;</code></td><td><a href="https://www.olbg.com/betting-tips/Baseball/MLB/MLB/TB_Rays_@_MIL_Brewers/12?event_id=160789" rel="nofollow noopener" target="_blank">TB Rays @ MIL Brewers, event_id 160789 ↗</a></td></tr>
<tr><td>Sport sitemap</td><td><code>/sitemap-betting-tips.xml</code></td><td><a href="https://www.olbg.com/sitemap-betting-tips.xml" rel="nofollow noopener" target="_blank">olbg.com/sitemap-betting-tips.xml ↗</a></td></tr>
</tbody></table>
<h2>The 24 sports OLBG lists, with IDs and scope</h2>
<table><thead><tr><th class="num">ID</th><th>Sport</th><th>Scope</th><th class="num">Events on the hub in this capture</th>
<th>Market names OLBG prints</th><th>Hub (source)</th></tr></thead><tbody>{srows}</tbody></table>
<h2>What the reverse-engineering found</h2>
<ul class="small">
<li>OLBG only surfaces events that already have at least one tip, so its hubs are <b>not</b> a complete fixture list.
That is why every fixture we price comes from the governing body and OLBG is used only for taxonomy and market names.</li>
<li>Hurling (ID 26) and Gaelic football (ID 25) are separate OLBG sports. The brief excludes hurling but never names
Gaelic football, so Gaelic football is treated as in scope and the ambiguity is flagged for review.</li>
<li>Boxing is one OLBG sport (ID 16) that carries UFC/MMA inside it; the brief excludes all three, so nothing under ID 16
is published here.</li>
<li>OLBG times render in the visitor's local timezone, which is why every row on this site carries a UTC start time read
from the official feed, and leaves the field blank when the official feed only prints a local time (URC fixture cards).</li>
</ul>"""
    open(os.path.join(OUT, "olbg.html"), "w").write(page("OLBG reverse-engineering", "olbg.html", body, "Sport taxonomy, URL patterns and the market names OLBG itself prints, all read live from olbg.com."))

    # ---------------------------------------------------------- methodology
    body = f"""<h2>How a line is originated here</h2>
<ol class="small">
<li><b>Fixtures</b> come only from a governing body: the NHL official API, the MLB Stats API, the URC Match Centre,
the ATP Tour daily schedule. OLBG is used for taxonomy and coverage only, never as the source of a fixture we price.</li>
<li><b>Inputs</b> are the numbers those sources print — goals for/against, points, home and road splits, last ten,
streaks, season runs scored and allowed, published seeds.</li>
<li><b>Model</b> per sport: a Poisson goal model for ice hockey; a run-differential normal-margin model for baseball; an
expected-points model with an explicit draw band for rugby union; a published-seed logistic for tennis. Every constant is
either derived from official numbers or declared below.</li>
<li><b>Price</b>: fair decimal = 1 ÷ probability, converted to American. No margin is added, so our prices are
margin-free fair prices, not bookmaker prices.</li>
<li><b>Window test</b>: the brief's −250…+10,000 band. At fair odds 70% prices at −233 and 71.4% at −250, so
"probability ≥ 70%" and "our own fair price ≥ −250" can only both hold inside a 1.4-point probability band. We therefore
report both bases on every row — our fair price and, where the league publishes one, the official market price on the
league's own feed — and label which one put the row inside the band.</li>
<li><b>Confidence</b>: High needs probability ≥ 0.70, at least {assumptions['min_games_for_high']} completed official
matches per side, and a price inside the band. Probability ≥ 0.70 with a failed sample or window test is published as
Medium and the reason is printed on the row. Never as High.</li>
</ol>
<h2>Declared modelling constants</h2>
<p class="small">These are ours, not the governing bodies'. Each is also published on the Flagged page.</p>
<table><thead><tr><th>Sport</th><th>Constant</th><th>Value</th><th>Why</th></tr></thead><tbody>
{''.join(f'<tr><td>{e(sport)}</td><td>{e(c.get("name"))}</td><td class="num">{e(c.get("value"))}</td><td class="small">{e(c.get("why"))}</td></tr>'
         for sport, blk in assumptions.items() if isinstance(blk, dict) for c in blk.get("declared_modelling_choices", []))}
</tbody></table>
<h2>What "verified" means on this site</h2>
<p class="small">A value is verified when the official page or API that produced it is linked on the same row and the raw
response is committed in <code>data/session-80bc6293/capture/</code> with its SHA-256 in the manifest. Anything else is
left blank. The URC table and Round-4 fixtures are the one hand transcription, because stats.unitedrugby.com renders
client-side: the transcription records the URL, the read time and the method, and the unrendered shell bytes are
committed alongside it so a reviewer can see exactly what the runner received.</p>"""
    open(os.path.join(OUT, "methodology.html"), "w").write(page("Methodology", "methodology.html", body, "How fixtures were verified, how each line was originated, how confidence was graded."))

    # ---------------------------------------------------------- sources
    man = []
    for cap in sorted(os.listdir(os.path.join(DATA, "capture"))):
        for sub in ("", "pass2", "pass3"):
            mp = os.path.join(DATA, "capture", cap, sub, "manifest.json")
            if os.path.exists(mp):
                m = json.load(open(mp, encoding="utf-8"))
                for t in m["targets"]:
                    t["capture"] = cap + ("/" + sub if sub else "")
                    man.append(t)
    srows = "".join(
        f'<tr><td>{e(t.get("sport") or "—")}</td><td>{e(t["id"])}</td>'
        f'<td class="num">{e(t.get("http_status"))}</td><td class="num">{e(t.get("bytes"))}</td>'
        f'<td class="small"><code>{e((t.get("sha256") or "")[:16])}…</code></td>'
        f'<td><a href="{e(t["url"])}" rel="nofollow noopener" target="_blank">{e(t["url"])[:88]} ↗</a></td>'
        f'<td class="small">{e(t.get("capture"))}</td></tr>'
        for t in sorted(man, key=lambda x: (-(x.get("http_status") == 200), x.get("sport", ""), x["id"])))
    ok = len([t for t in man if t.get("http_status") == 200])
    body = f"""<h2>Every source fetched, with its HTTP status and SHA-256</h2>
<div class="note">{len(man)} requests to official governing bodies and to OLBG; <b>{ok}</b> returned HTTP 200.
A non-200 is recorded, never retried into a fake success, and never used as the source of a published number.</div>
<table><thead><tr><th>Sport</th><th>Target</th><th class="num">HTTP</th><th class="num">Bytes</th>
<th>SHA-256 (first 16)</th><th>URL (source)</th><th>Capture</th></tr></thead><tbody>{srows}</tbody></table>"""
    open(os.path.join(OUT, "sources.html"), "w").write(page("Sources", "sources.html", body, "Every official endpoint and OLBG page in the capture, with status, size and hash."))

    # ---------------------------------------------------------- flagged
    frows = ""
    for g in gaps:
        frows += (f'<tr><td>{e(g.get("id"))}</td><td>{e(g.get("sport"))}</td><td>{e(g.get("fixture"))}</td>'
                  f'<td>{e(g.get("issue"))}</td><td>{e(g.get("action"))}</td>'
                  f'<td><a href="{e(g.get("source_url"))}" rel="nofollow noopener" target="_blank">official page ↗</a></td></tr>')
    lrows = ""
    seen_reasons = {}
    for r in listing:
        key = (r["sport"], r.get("listing_reason", "")[:60])
        seen_reasons.setdefault(key, []).append(r)
    for (sport, reason), rr in sorted(seen_reasons.items()):
        lrows += (f'<tr><td>{e(sport)}</td><td class="num">{len(rr)}</td><td class="small">{e(reason or rr[0].get("listing_reason",""))}</td>'
                  f'<td class="small">{e(", ".join(x.get("home") or x.get("venue") or "" for x in rr[:4]))}{"…" if len(rr) > 4 else ""}</td>'
                  f'<td><a href="{e(rr[0]["source_url"])}" rel="nofollow noopener" target="_blank">example source &#8599;</a></td></tr>')
    arows = "".join(
        f'<tr><td>{e(sport)}</td><td>{e(c.get("name"))}</td><td class="num">{e(c.get("value"))}</td><td class="small">{e(c.get("why"))}</td></tr>'
        for sport, blk in assumptions.items() if isinstance(blk, dict) for c in blk.get("declared_modelling_choices", []))
    shortfall = ""
    for s in sports_in:
        n = len([p for p in preds["predictions"] if p["sport"] == s])
        if n >= 5:
            continue
        reason = assumptions["listing_reasons"].get(s, "")
        shortfall += (f'<tr><td><a href="./sports/{SLUG[s]}.html">{e(s)}</a></td><td class="num">{n}</td><td class="num">5</td>'
                      f'<td class="num">{5-n}</td><td class="small">{e(reason or "no High-confidence row satisfied the ≥70% probability and −250…+10,000 window tests on verified official inputs this week")}</td></tr>')
    body = f"""<h2>Flagged for review</h2>
<div class="note warn">Nothing on this page blocks publication. It exists so a reviewer can see exactly what we could not
confirm, what we declared rather than read, and where the five-per-sport target was not met — each with the link to check.</div>
<h3>1. Prediction shortfall against the five-per-sport target</h3>
<table><thead><tr><th>Sport</th><th class="num">Delivered</th><th class="num">Target</th><th class="num">Short</th>
<th>Reason, with the official endpoint that was tried</th></tr></thead><tbody>{shortfall}</tbody></table>
<h3>2. Rows published with fixture detail but no line ({len(listing)})</h3>
<table><thead><tr><th>Sport</th><th class="num">Rows</th><th>Why no line could be originated</th>
<th>Examples</th><th>Source used for the listing</th></tr></thead><tbody>{lrows}</tbody></table>
<h3>3. Source-level gaps found while auditing the desk</h3>
<table><thead><tr><th>ID</th><th>Sport</th><th>Fixture</th><th>Issue</th><th>Action taken</th><th>Source</th></tr></thead>
<tbody>{frows or '<tr><td colspan="6">none</td></tr>'}</tbody></table>
<h3>4. Declared modelling constants (ours, not the governing bodies')</h3>
<table><thead><tr><th>Sport</th><th>Constant</th><th class="num">Value</th><th>Why</th></tr></thead><tbody>{arows}</tbody></table>
<h3>5. Known limitations of this desk</h3>
<ul class="small">
<li><b>No player-level facts.</b> The official bytes captured publish team form and ATP seeds, not player form, so the
written predictions quote teams, records, venues and selections only. Adding a player claim would mean inventing it.</li>
<li><b>URC local times.</b> The URC fixture cards print local kick-off times and state "All times shown are Local"; UTC
is left blank on those rows rather than derived from an assumed venue timezone.</li>
<li><b>MLB World Series games 5–7 are 'if necessary'.</b> The official schedule carries the flag and it is printed on
each row; those games may never be played.</li>
<li><b>Gaelic football scope.</b> The brief excludes hurling but never names Gaelic football; treated as in scope and flagged.</li>
<li><b>Early-season samples.</b> NHL clubs have played 8–12 games and the URC has completed three rounds, so shrinkage to
the league mean does most of the work; the {assumptions['min_games_for_high']}-game rule keeps that from becoming false confidence.</li>
<li><b>The −250 boundary.</b> At fair odds the ≥70% probability floor and the −250 price floor overlap only between
p = 0.700 and p = 0.714. This is arithmetic, not a bug, and it is the single biggest reason the five-per-sport target is
not met everywhere. Rows above the band are published as High-by-probability-but-outside-window on the picks page rather
than being quietly relabelled.</li>
</ul>"""
    open(os.path.join(OUT, "flagged.html"), "w").write(page("Flagged for review", "flagged.html", body, "Unconfirmed values, declared constants, source failures and prediction shortfalls, each with a link to check."))

    # ---------------------------------------------------------- review
    rrows = "".join(
        f'<tr><td><span class="chip">{e(f["severity"])}</span></td><td>{e(f["where"])}</td><td>{e(f["sport"])}</td>'
        f'<td class="small">{e(f["finding"])}</td><td class="small">{e(f["rule"])}</td>'
        f'<td>{review_link(f.get("review_url"))}</td></tr>'
        for f in review.get("findings", [])[:600])
    body = f"""<h2>Line-by-line review of the shared repo datasets</h2>
<div class="note">{review.get('rows_reviewed', 0)} rows across {len(review.get('datasets', []))} datasets, re-checked against the
brief's own rules. Findings: <b>{review.get('findings_total', 0)}</b> —
{e(json.dumps(review.get('by_severity', {})))}. Board AF edits none of these files; every finding is advisory and each
carries the link a reviewer should open.</div>
<h3>Datasets reviewed</h3>
<table><thead><tr><th>File</th><th>Key</th><th class="num">Rows</th></tr></thead><tbody>
{''.join(f'<tr><td><code>{e(d["path"])}</code></td><td>{e(d["key"])}</td><td class="num">{d["rows"]}</td></tr>' for d in review.get('datasets', []))}
</tbody></table>
<h3>Findings</h3>
<table><thead><tr><th>Severity</th><th>Where</th><th>Sport</th><th>Finding</th><th>Rule</th><th>Manual review link</th></tr></thead>
<tbody>{rrows}</tbody></table>
<h3>Integration requests (Board AF will not edit another owner's files)</h3>
<ul class="small">{''.join('<li>'+e(r['request'])+' <span class="small">('+e(r['why'])+')</span></li>' for r in review.get('integration_requests', []))}</ul>"""
    open(os.path.join(OUT, "review.html"), "w").write(page("Repository review", "review.html", body, "Advisory findings on the shared canonical board and every peer desk."))

    # ---------------------------------------------------------- verification
    body = f"""<h2>Verification register</h2>
<div class="note">Run <code>python3 scripts/session-80bc6293/verify.py</code> to reproduce every check below. The gate
re-derives each published price from its own probability, re-checks the confidence rule, the window flag, the prediction
word counts and uniqueness, that unpriced rows publish nothing, that every row carries a source URL, and that every
internal link on this site resolves.</div>
<table><thead><tr><th>Check</th><th>Rule</th><th>How it is enforced</th></tr></thead><tbody>
<tr><td>Fixture provenance</td><td>fixtures only from a governing body</td><td>each priced row's <code>source_url</code> must be nhl.com / statsapi.mlb.com / stats.unitedrugby.com / atptour.com</td></tr>
<tr><td>Evidence integrity</td><td>raw bytes committed</td><td>every manifest entry must name a file that exists, and its SHA-256 is recomputed at build time</td></tr>
<tr><td>Price maths</td><td>fair decimal = 1 ÷ p</td><td>re-derived for all {n_markets} originated markets; tolerance 0.001</td></tr>
<tr><td>American conversion</td><td>standard decimal↔American</td><td>re-derived for every market; tolerance 2 units for rounding</td></tr>
<tr><td>Two-way markets</td><td>probabilities sum to 1</td><td>checked per market group; tolerance 0.002</td></tr>
<tr><td>Confidence rule</td><td>High = p ≥ 0.70 + sample ≥ {assumptions['min_games_for_high']} + price in band</td><td>recomputed for every row; any mismatch fails the gate</td></tr>
<tr><td>Window flag</td><td>−250 ≤ American ≤ +10,000</td><td>recomputed from the published price and the basis recorded</td></tr>
<tr><td>Unpriced purity</td><td>a row with no line publishes no pick, no price, no confidence</td><td>checked for all {len(listing)} listing-only rows</td></tr>
<tr><td>Predictions</td><td>≥30 words, unique, names a side, states the selection, every quoted number traceable</td><td>word count, pairwise 3-gram overlap and number-traceability all checked</td></tr>
<tr><td>Links</td><td>no broken internal links, every external row link present</td><td>all <code>href</code> targets on this site are resolved against the file tree</td></tr>
</tbody></table>"""
    open(os.path.join(OUT, "verification.html"), "w").write(page("Verification", "verification.html", body, "What the verification gate checks and how to reproduce it."))

    # ---------------------------------------------------------- per-sport pages
    for s in sports_in:
        sr = [r for r in rows if r["sport"] == s]
        sp = [r for r in sr if not r.get("listing_only")]
        spred = [p for p in preds["predictions"] if p["sport"] == s]
        trs = ""
        for r in sr:
            fixture = f'{e(r.get("away"))} @ {e(r.get("home"))}' if r.get("away") else e(r.get("home") or r.get("venue") or "")
            mk = "; ".join(f'{m["market"]}: {m["selection"]} p={m["p"]} ({m["fair_american"]:+d})' for m in (r.get("markets") or [])[:6])
            conf = r.get("confidence") or ""
            trs += (f'<tr><td>{e(r["id"])}</td><td>{e(r.get("competition",""))}</td><td>{e(r.get("date",""))}</td>'
                    f'<td>{e(r.get("local_time") or r.get("time_utc") or "")}</td><td>{fixture}</td><td>{e(r.get("venue",""))}</td>'
                    f'<td>{e(r.get("pick","")) or BLANK}</td>{num(r.get("pick_probability"))}'
                    f'{num(r.get("pick_fair_american"))}<td>{conf_chip(conf)}</td>'
                    f'<td class="small">{e(mk) or NO_MARKET}</td>'
                    f'<td class="small">{e(r.get("listing_reason",""))[:220]}</td><td>{src_link(r)}</td></tr>')
        cards = "".join(f"""<div class="pred"><h4>{e(p['selection'])} — {e(p['market'])}</h4>
<div class="meta">{e(p['fixture'])} · {e(p['date'])} · p={p['probability']:.3f} · fair {p['fair_american']:+d}</div>
<p>{e(p['text'])}</p><ul>{''.join('<li>'+e(f)+'</li>' for f in p['facts'])}
<li>Source: <a href="{e(p['source_url'])}" rel="nofollow noopener" target="_blank">{e(p['source_url'])} ↗</a></li></ul></div>"""
                        for p in spred)
        olbg_info = desk["coverage"].get(s, {})
        body = f"""<div class="cards">
<div class="card"><b>{len(sr)}</b><span>Rows</span></div>
<div class="card"><b>{len(sp)}</b><span>Priced with our own line</span></div>
<div class="card"><b>{sum(len(r['markets']) for r in sp)}</b><span>Markets originated</span></div>
<div class="card"><b>{len([r for r in sp if r['confidence']=='High'])}</b><span>High rows</span></div>
<div class="card"><b>{len(spred)} / 5</b><span>Predictions vs target</span></div>
<div class="card"><b>{olbg_info.get('events_listed', 0)}</b><span>Events on the OLBG hub</span></div></div>
{('<h2>Written high-confidence predictions</h2>'+cards) if cards else '<div class="note warn">No written prediction for this sport this week: no row met the High rule (probability ≥ 0.70, sample ≥ '+str(assumptions['min_games_for_high'])+' official matches, price inside −250…+10,000) on verified official inputs. The reason is on <a href="../flagged.html">Flagged for review</a>.</div>'}
<h2>Every {e(s)} row</h2>
<table><thead><tr><th>ID</th><th>Competition</th><th>Date</th><th>Time</th><th>Fixture</th><th>Venue</th>
<th>Pick</th><th class="num">p</th><th class="num">Fair (US)</th><th>Confidence</th>
<th>Markets originated</th><th>Why unpriced</th><th>Official source</th></tr></thead><tbody>{trs}</tbody></table>"""
        os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
        f_out = os.path.join(OUT, "sports", SLUG[s] + ".html")
        html_txt = page(f"{s} — Board AF", "sports/" + SLUG[s] + ".html", body,
                        f"Official fixtures, our own originated lines and confidence grades for {s}.")
        html_txt = (html_txt.replace('href="./', 'href="../')
                            .replace('src="./', 'src="../')
                            .replace('href="../sports/', 'href="./'))
        open(f_out, "w").write(html_txt)

    print(f"site written: {len(PAGES)} top-level pages + {len(sports_in)} sport pages -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

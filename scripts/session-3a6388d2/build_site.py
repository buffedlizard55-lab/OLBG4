#!/usr/bin/env python3
"""Board AD — build the GitHub Pages dashboard under session-3a6388d2/.

Reads only the files produced by this board (desk.json, review.json, flagged.json,
predictions.json and the capture manifests) and writes static HTML.  Every data row
carries the official source it was verified from; every unpriced row says why.

Run:  python3 scripts/session-3a6388d2/build_site.py
"""
from __future__ import annotations

import html
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-3a6388d2")
SITE = os.path.join(ROOT, "session-3a6388d2")
SPORTS = os.path.join(SITE, "sports")
ASSETS = os.path.join(SITE, "assets")

BOARD = "Board AD"
SESSION = "arena/3a6388d2-olbg4"
GENERATED = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

EXCLUDED_SPORTS = ["Soccer / Football (association)", "American Football", "Boxing",
                   "UFC / MMA", "Hurling", "Horse Racing", "Cycling", "Specials"]

# OLBG sport-id taxonomy observed live on 2026-10-22 from sitemap-betting-tips.xml
OLBG_SPORTS = [
    (1, "Football", "excluded"), (2, "Horse Racing", "excluded"), (3, "Tennis", "in-scope"),
    (4, "Basketball", "in-scope"), (5, "Golf", "in-scope"), (6, "Specials", "excluded"),
    (7, "Cricket", "in-scope"), (8, "Snooker", "in-scope"), (9, "Rugby Union", "in-scope"),
    (10, "Rugby League", "in-scope"), (11, "American Football", "excluded"),
    (12, "Baseball", "in-scope"), (13, "Ice Hockey", "in-scope"), (14, "Motor Racing", "in-scope"),
    (15, "Darts", "in-scope"), (16, "Boxing", "excluded"), (17, "Cycling", "excluded"),
    (20, "Handball", "in-scope"), (21, "Volleyball", "in-scope"), (22, "Aussie Rules", "in-scope"),
    (23, "eSports", "in-scope"), (25, "Gaelic Football", "scope-call"), (28, "Greyhounds", "in-scope"),
]

MARKET_TAXONOMY = [
    ("Ice Hockey", "Match Winner (incl. OT/SO), Puck Line ±1.5, Total Goals O/U, Regulation 3-way",
     "https://www.olbg.com/betting-tips/Ice_Hockey/13", "https://api-web.nhle.com/v1/schedule/2026-10-22"),
    ("Baseball", "Match Winner, Run Line ±1.5, Total Runs O/U, World Series outright",
     "https://www.olbg.com/betting-tips/Baseball/12",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-08"),
    ("Rugby Union", "Match Winner, Draw, Handicap, Total Points O/U",
     "https://www.olbg.com/betting-tips/Rugby_Union/9", "https://stats.unitedrugby.com/match-centre/table/2026-27"),
    ("Rugby League", "Match Winner, Handicap, Total Points O/U (markets investigated; no line originated)",
     "https://www.olbg.com/betting-tips/Rugby_League/10", "https://www.nrl.com/draw/"),
    ("Esports", "Map Winner, Map Handicap, Total Maps O/U (markets investigated; no line originated)",
     "https://www.olbg.com/betting-tips/eSports/23", "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US&sport=lol"),
    ("Motor Racing", "Race Winner, Podium, Head-to-head (markets investigated; no line originated)",
     "https://www.olbg.com/betting-tips/Motor_Racing/14", "https://www.formula1.com/en/racing/2026.html"),
    ("Cricket", "Match Winner, Top Run-scorer, Total Runs O/U (markets investigated; no line originated)",
     "https://www.olbg.com/betting-tips/Cricket/7", "https://www.cricket.com.au/fixtures"),
]


# ----------------------------------------------------------------------------- helpers
def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", str(s)).strip("-").lower()
    return s or "x"


def load(name, default=None):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def ams(p) -> str:
    return "" if p in (None, "") else f"{p:+d}" if p > 0 else str(p)


CSS = """
:root{--bg:#f6f7f9;--card:#fff;--ink:#111827;--muted:#5b6472;--line:#e3e7ee;--accent:#0b5fff;
--hi:#0f7b3f;--med:#a06a00;--low:#7a7f8a;--flag:#b3261e;--chip:#eef2ff}
*{box-sizing:border-box}
body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.top{background:#0f172a;color:#fff;padding:14px 20px;position:sticky;top:0;z-index:20}
header.top h1{font-size:16px;margin:0;display:inline-block}
header.top nav{display:inline-block;margin-left:16px;flex-wrap:wrap}
header.top nav a{color:#c7d2fe;margin-right:12px;font-size:13px}
header.top nav a:hover{color:#fff}
.wrap{max-width:1280px;margin:0 auto;padding:20px}
h2{font-size:20px;margin:24px 0 8px}
h3{font-size:16px;margin:18px 0 6px}
p.lede{color:var(--muted);margin:0 0 16px;max-width:900px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.card .k{font-size:26px;font-weight:600}
.card .l{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.panel h3{margin-top:0}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:13.5px}
th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:#eef1f6;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:#3a4354;position:sticky;top:46px}
tbody tr:hover{background:#f9fbff}
.badge{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:600;border:1px solid transparent}
.b-High{background:#e6f6ec;color:var(--hi);border-color:#b7e2c6}
.b-Medium{background:#fdf3e0;color:var(--med);border-color:#f0dcae}
.b-Low{background:#f1f3f6;color:var(--low);border-color:#dfe3ea}
.b-none{background:#fdeceb;color:var(--flag);border-color:#f4c7c3}
.chip{display:inline-block;background:var(--chip);color:#1e3a8a;border-radius:6px;padding:1px 6px;font-size:11.5px;margin-right:4px}
.controls{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.controls input,.controls select{padding:7px 9px;border:1px solid var(--line);border-radius:8px;font-size:13px;background:#fff}
.small{font-size:12px;color:var(--muted)}
.note{background:#fff8e6;border:1px solid #f2dfae;border-radius:8px;padding:10px 12px;font-size:13px}
.ok{background:#e6f6ec;border:1px solid #b7e2c6;border-radius:8px;padding:10px 12px;font-size:13px}
pre{background:#0f172a;color:#e6edf3;padding:10px;border-radius:8px;overflow-x:auto;font-size:12px}
footer{color:var(--muted);font-size:12px;padding:24px 20px;max-width:1280px;margin:0 auto}
.scroll{max-height:none}
@media(max-width:820px){th{position:static}table{font-size:12.5px}}
"""

JS = """
document.addEventListener('DOMContentLoaded',function(){
  function wire(){
    document.querySelectorAll('[data-filter-for]').forEach(function(inp){
      var target=inp.getAttribute('data-filter-for');
      var col=inp.getAttribute('data-filter-col');
      inp.addEventListener('input',function(){
        var q=inp.value.toLowerCase().trim();
        var table=document.getElementById(target);
        if(!table) return;
        var idx=col?parseInt(col,10):null;
        table.querySelectorAll('tbody tr').forEach(function(tr){
          var hay=(idx!==null&&!isNaN(idx))?(tr.cells[idx]?tr.cells[idx].textContent:tr.textContent):tr.textContent;
          tr.style.display=hay.toLowerCase().indexOf(q)>=0?'':'none';
        });
      });
    });
    document.querySelectorAll('[data-select-for]').forEach(function(sel){
      var target=sel.getAttribute('data-select-for');
      var col=parseInt(sel.getAttribute('data-select-col'),10);
      sel.addEventListener('change',function(){
        var v=sel.value.toLowerCase();
        var table=document.getElementById(target);
        if(!table) return;
        table.querySelectorAll('tbody tr').forEach(function(tr){
          var cell=tr.cells[col]?tr.cells[col].textContent.trim().toLowerCase():'';
          tr.style.display=(!v||cell===v)?'':'none';
        });
      });
    });
  }
  wire();
});
"""


def nav(active: str) -> str:
    items = [("index.html", "Dashboard"), ("matches.html", "All entries"),
             ("picks.html", "High-confidence picks"), ("markets.html", "Markets"),
             ("coverage.html", "Coverage"), ("olbg.html", "OLBG reverse engineering"),
             ("review.html", "Repo review"), ("flagged.html", "Flagged for review"),
             ("methodology.html", "Methodology"), ("sources.html", "Sources")]
    links = "".join(
        f'<a href="{href}" class="{"active" if href == active else ""}">{esc(label)}</a>'
        for href, label in items)
    return links


def page(title: str, active: str, body: str, subtitle: str = "", base: str = "") -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 {BOARD}</title>
<link rel="stylesheet" href="{base}assets/style.css">
</head><body>
<header class="top"><h1>OLBG4 · {BOARD} <span class="small" style="color:#94a3b8">({SESSION})</span></h1>
<nav>{nav_links(active, base)}</nav></header>
<div class="wrap">
<h2>{esc(title)}</h2>
{('<p class="lede">' + esc(subtitle) + '</p>') if subtitle else ''}
{body}
</div>
<footer>{BOARD} · session {SESSION} · generated {GENERATED} · every row links to the official source it was verified from.</footer>
<script src="{base}assets/app.js"></script>
</body></html>
"""


def nav_links(active: str, base: str = "") -> str:
    items = [("index.html", "Dashboard"), ("matches.html", "All entries"),
             ("picks.html", "High-confidence picks"), ("markets.html", "Markets"),
             ("coverage.html", "Coverage"), ("olbg.html", "OLBG reverse engineering"),
             ("review.html", "Repo review"), ("flagged.html", "Flagged for review"),
             ("methodology.html", "Methodology"), ("sources.html", "Sources")]
    return "".join(f'<a href="{base}{href}">{esc(label)}</a>' for href, label in items)


# ----------------------------------------------------------------------------- load data
def main() -> int:
    desk = load("desk.json", {"rows": []})
    rows = desk.get("rows", [])
    review = load("review.json", {"summary": {}, "findings": [], "cross_check": []})
    flags = load("flagged.json", {"items": []})
    olbg_board = load("olbg_board.json", {})
    vrep = load("verify_report.json", {})
    preds = load("predictions.json", {"predictions": []})
    manifests = []
    for name in ("manifest.json", "manifest3.json", "manifest4.json", "manifest5.json",
                 "manifest_rankings.json"):
        m = load(name)
        if m:
            manifests.append((name, m))

    os.makedirs(SPORTS, exist_ok=True)
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    with open(os.path.join(ASSETS, "app.js"), "w", encoding="utf-8") as fh:
        fh.write(JS)

    priced = [r for r in rows if r.get("markets")]
    unpriced = [r for r in rows if not r.get("markets")]
    high = [r for r in rows if r.get("confidence") == "High"]
    high_in_window = [r for r in high if r.get("in_odds_window")]
    by_sport = Counter(r["sport"] for r in rows)
    sports = sorted(by_sport)
    captures = sum(m["targets_total"] for _, m in manifests)
    captures_ok = sum(m["ok"] for _, m in manifests)

    # ------------------------------------------------------------------ row rendering
    def row_tr(r: dict, with_pred: bool = False) -> str:
        conf = r.get("confidence") or ""
        cls = f"b-{conf}" if conf else "b-none"
        pick = r.get("pick") or {}
        src = r.get("source_url") or ""
        venue = r.get("venue") or ""
        link = (f'<a href="{esc(src)}" target="_blank" rel="noopener">source</a>'
                if src else '<span class="badge b-none">no source</span>')
        if r.get("markets"):
            price = f'{pick.get("fair_american","")}'
            bookp = f'{pick.get("book_american","")}'
            sel = esc(pick.get("selection", ""))
            p = pick.get("p", "")
            window = ('<span class="chip">in −250…+10000</span>' if r.get("in_odds_window")
                      else '<span class="chip" style="background:#fdeceb;color:#b3261e">outside window</span>')
        else:
            price = bookp = sel = p = ""
            window = '<span class="chip" style="background:#fdeceb;color:#b3261e">no line</span>'
        pred_cell = ""
        if with_pred and r.get("prediction"):
            pred_cell = (f'<details><summary>read ({r.get("prediction_words",0)} words)</summary>'
                         f'<p class="small">{esc(r["prediction"])}</p></details>')
        return (f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(conf)}">'
                f'<td>{esc(r["date"])}<br><span class="small">{esc((r.get("time_utc") or "")[11:16])} UTC</span></td>'
                f'<td>{esc(r["sport"])}</td>'
                f'<td>{esc(r["competition"])}</td>'
                f'<td>{esc(r["away"])}<br><span class="small">@</span> {esc(r["home"])}'
                f'{("<br><span class=small>" + esc(venue) + "</span>") if venue else ""}</td>'
                f'<td>{sel}</td>'
                f'<td>{esc(p)}</td><td>{esc(price)}</td><td>{esc(bookp)}</td>'
                f'<td><span class="badge {cls}">{esc(conf or "no line")}</span> {window}</td>'
                f'<td>{link}</td><td>{pred_cell}</td></tr>')

    table_cols = ('<thead><tr><th>Date (UTC)</th><th>Sport</th><th>Competition</th>'
                  '<th>Fixture</th><th>Our pick</th><th>p</th><th>Fair</th><th>Book</th>'
                  '<th>Confidence</th><th>Source</th><th>Prediction</th></tr></thead>')

    # ------------------------------------------------------------------ index
    kpis = [
        ("Fixtures in window", len(rows)),
        ("Own lines originated", len(priced)),
        ("Markets priced", sum(len(r["markets"]) for r in priced)),
        ("High confidence", len(high)),
        ("High inside −250…+10000", len(high_in_window)),
        ("Sports covered", len(sports)),
        ("Official captures", f"{captures_ok}/{captures}"),
        ("Repo-review findings", len(review.get("findings", []))),
    ]
    kpi_html = "".join(f'<div class="card"><div class="k">{esc(v)}</div><div class="l">{esc(k)}</div></div>'
                       for k, v in kpis)

    sport_cards = "".join(
        f'<a class="panel" href="sports/{slug(s)}.html"><h3>{esc(s)}</h3>'
        f'<div class="small">{by_sport[s]} rows · '
        f'{sum(1 for r in priced if r["sport"] == s)} priced · '
        f'{sum(1 for r in high if r["sport"] == s)} High</div></a>' for s in sports)

    pick_cards = []
    for r in sorted(high, key=lambda x: -x["pick"]["p"]):
        mi = r.get("model_inputs", {})
        facts = " · ".join(f"{k}: {v}" for k, v in list(mi.items())[:6])
        if r.get("in_odds_window"):
            window_chip = '<span class="chip">inside −250…+10000</span>'
        else:
            window_chip = '<span class="chip" style="background:#fdeceb;color:#b3261e">shorter than −250</span>'
        pick_cards.append(
            '<div class="panel"><h3>' + esc(r["pick"]["selection"]) + ' '
            + '<span class="badge b-High">High</span></h3>'
            + '<div class="small">' + esc(r["sport"]) + ' · ' + esc(r["date"]) + ' · '
            + esc(r["away"]) + ' @ ' + esc(r["home"]) + ' · ' + esc(r["venue"]) + '</div>'
            + '<p class="small">' + esc(r["prediction"]) + '</p>'
            + '<div class="small">Our fair line <strong>' + ams(r["pick"]["fair_american"]) + '</strong> '
            + '· book ' + ams(r["pick"]["book_american"]) + ' · model p ' + str(r["pick"]["p"])
            + ' · ' + window_chip + '</div>'
            + '<div class="small">Official inputs — ' + esc(facts) + '</div>'
            + '<div class="small"><a href="' + esc(r["source_url"])
            + '" target="_blank" rel="noopener">official source</a></div></div>')

    kpi_verify = (
        '<div class="card"><div class="k">' + str(vrep.get("checks_run", 0)) + '</div>'
        '<div class="l">Verification checks</div></div>'
        '<div class="card"><div class="k">' + str(vrep.get("captures_ok", 0)) + '/' + str(vrep.get("captures_total", 0)) + '</div>'
        '<div class="l">Official captures 200</div></div>')
    comp_note = ""
    for sport, c in sorted((vrep.get("completeness") or {}).items()):
        comp_note += (f"Completeness, {sport}: {c['desk_rows']} desk rows against "
                      f"{c['official_fixtures_in_window']} official in-window fixtures "
                      f"({c['missing_from_desk']} missing) read from {c['official_source']}. ")

    body = f"""
<div class="cards">{kpi_html}{kpi_verify}</div>
<p class="lede">Fresh desk for 22 Oct – 8 Nov 2026 for every OLBG sport except soccer/football, American
football, boxing, UFC/MMA, hurling, horse racing, cycling and specials. Fixtures, times, venues and every
rating input were read from official league, federation or organiser endpoints; the raw bytes of every
request are committed with a SHA-256 digest (see <a href="sources.html">Sources</a>). We originate our own
lines — no bookmaker price, tipster percentage or third-party rating is used anywhere on this site.
Where an official input could not be read, the row is published with the fixture detail,
<strong>no price and no pick</strong>, and is listed on
<a href="flagged.html">Flagged for review</a>.</p>
<div class="note"><strong>Scope exclusions applied:</strong> {esc(', '.join(EXCLUDED_SPORTS))}.</div>
<h3>High-confidence picks with written predictions</h3>
<div class="grid">{''.join(pick_cards) or '<p class="small">none</p>'}</div>
<h3>Browse by sport</h3>
<div class="grid">{sport_cards}</div>
<h3>What is on this site</h3>
<div class="grid">
<a class="panel" href="matches.html"><h3>All entries</h3><div class="small">{len(rows)} rows, filterable, one official source link per row.</div></a>
<a class="panel" href="picks.html"><h3>High-confidence picks</h3><div class="small">{len(high)} picks at ≥70% with hand-written predictions.</div></a>
<a class="panel" href="markets.html"><h3>Markets</h3><div class="small">every market investigated per sport, with our own lines.</div></a>
<a class="panel" href="coverage.html"><h3>Coverage</h3><div class="small">sport-by-sport status: verified, priced or flagged, with the official check made.</div></a>
<a class="panel" href="olbg.html"><h3>OLBG reverse engineering</h3><div class="small">URL taxonomy, sport IDs, market types, SSR behaviour.</div></a>
<a class="panel" href="review.html"><h3>Repo review</h3><div class="small">line-by-line review of data/master.json — {len(review.get('findings', []))} findings.</div></a>
<a class="panel" href="flagged.html"><h3>Flagged for review</h3><div class="small">{sum(1 for r in rows if not r['markets'])} rows with no line, each with the reason and the official source checked.</div></a>
</div>
<h3>Verification</h3>
<div class="note">
<strong>{esc(vrep.get('checks_run', 0))} automated checks, {esc('all passing' if vrep.get('passed') else 'FAILURES PRESENT')}</strong>
(re-run with <code>python3 scripts/session-3a6388d2/verify.py</code>; the report is committed as
<code>data/session-3a6388d2/verify_report.json</code>). Every row carries an official source URL; every fair
price equals 1/p; every published price equals p with the stated 4.2&nbsp;% / 5.2&nbsp;% over-round; two-way
and three-way markets sum to 1; the confidence label follows the published rule; the −250…+10000 flag matches
the price; unpriced rows publish no pick, no price and no confidence; every high-confidence prediction is
≥30&nbsp;words, unique, names a side, states the selection, and quotes no statistic that is not in that row's
committed official inputs; every internal link resolves; every raw file named by a manifest exists.
{esc(comp_note)}
</div>
"""
    write("index.html", page("Dashboard", "index.html", body,
                             "Verified fixtures, our own originated lines, and high-confidence human predictions."))

    # ------------------------------------------------------------------ matches
    body = f"""
<div class="controls">
<input placeholder="Filter rows (team, competition, venue…)" data-filter-for="tbl-all" data-filter-col="3">
<select data-select-for="tbl-all" data-select-col="1"><option value="">all sports</option>
{''.join(f'<option value="{esc(s.lower())}">{esc(s)}</option>' for s in sports)}</select>
<select data-select-for="tbl-all" data-select-col="8"><option value="">any confidence</option>
<option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
<option value="no line">no line</option></select>
</div>
<p class="small">{len(rows)} rows · {len(priced)} with originated lines · {len(unpriced)} published without a line
(see <a href="flagged.html">Flagged for review</a>). Times are UTC.</p>
<table id="tbl-all">{table_cols}<tbody>
{''.join(row_tr(r, True) for r in sorted(rows, key=lambda x: (x['date'], x['sport'])))}
</tbody></table>
"""
    write("matches.html", page("All entries", "matches.html", body,
                               "Every fixture captured for the window, with our line, pick and confidence."))

    # ------------------------------------------------------------------ picks
    pred_panels = []
    for r in sorted(high, key=lambda x: -x["pick"]["p"]):
        inputs = "; ".join(f"{k}={v}" for k, v in r.get("model_inputs", {}).items())
        pred_panels.append(
            '<div class="panel"><h3>' + esc(r["pick"]["selection"]) + ' — ' + esc(r["away"]) + ' @ '
            + esc(r["home"]) + ' <span class="small">' + esc(r["date"]) + '</span></h3>'
            + '<p>' + esc(r["prediction"]) + '</p>'
            + '<div class="small">' + str(r.get("prediction_words", 0)) + ' words · selection: '
            + esc(r["pick"]["selection"]) + ' (' + esc(r["pick"]["market"]) + ') · our fair line '
            + ams(r["pick"]["fair_american"]) + ' · book ' + ams(r["pick"]["book_american"]) + ' · '
            + '<a href="' + esc(r["source_url"]) + '" target="_blank" rel="noopener">official source</a></div>'
            + '<div class="small">Verified inputs: ' + esc(inputs) + '</div></div>')
    pred_panels = "".join(pred_panels)

    body_picks = f"""
<p class="lede">High confidence = model probability ≥ 0.700. The brief asks for the focus to sit between
−250 and +10000 American; {len(high_in_window)} of the {len(high)} High picks fall inside that window,
the rest are shorter than −250 and are labelled as such (see
<a href="methodology.html">methodology</a> for the arithmetic).</p>
<table id="tbl-picks">{table_cols}<tbody>
{''.join(row_tr(r, True) for r in sorted(high, key=lambda x: -x['pick']['p']))}
</tbody></table>
<h3>Written predictions</h3>
{pred_panels}
"""
    write("picks.html", page("High-confidence picks", "picks.html", body_picks,
                             "Selections at ≥70% model probability, each with a hand-written prediction."))

    # ------------------------------------------------------------------ markets
    mcount = Counter()
    for r in priced:
        for m in r["markets"]:
            mcount[(r["sport"], m["market"])] += 1
    mrows = "".join(
        f'<tr><td>{esc(s)}</td><td>{esc(m)}</td><td>{n}</td></tr>'
        for (s, m), n in sorted(mcount.items()))
    sport_market = defaultdict(set)
    for (s, m) in mcount:
        sport_market[s].add(m)
    sample = []
    for s in sorted(sport_market):
        rs = [r for r in priced if r["sport"] == s]
        if not rs:
            continue
        r = sorted(rs, key=lambda x: -x["markets"][0]["p"])[0]
        lines = "".join(
            f'<li>{esc(m["market"])} — <strong>{esc(m["selection"])}</strong> '
            f'p={m["p"]} fair {ams(m["fair_american"])} book {ams(m["book_american"])}</li>'
            for m in r["markets"])
        sample.append(f'<div class="panel"><h3>{esc(s)} — worked example</h3>'
                      f'<div class="small">{esc(r["away"])} @ {esc(r["home"])} · {esc(r["date"])}</div>'
                      f'<ul class="small">{lines}</ul>'
                      f'<div class="small"><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">official source</a></div></div>')
    tax_rows = "".join(
        f'<tr><td>{esc(s)}</td><td>{esc(mk)}</td>'
        f'<td><a href="{esc(olbg)}" target="_blank" rel="noopener">OLBG card</a></td>'
        f'<td><a href="{esc(off)}" target="_blank" rel="noopener">official feed</a></td></tr>'
        for s, mk, olbg, off in MARKET_TAXONOMY)
    body = f"""
<h3>Markets originated by sport</h3>
<p class="small">Counts are the number of individual selections priced, not the number of fixtures.</p>
<table><thead><tr><th>Sport</th><th>Market</th><th>Selections priced</th></tr></thead><tbody>{mrows}</tbody></table>
<h3>Markets investigated, and where the input comes from</h3>
<table><thead><tr><th>Sport</th><th>Markets investigated</th><th>OLBG</th><th>Official source used</th></tr></thead>
<tbody>{tax_rows}</tbody></table>
<h3>Worked examples</h3>
<div class="grid">{''.join(sample)}</div>
"""
    write("markets.html", page("Markets", "markets.html", body,
                               "Every market we looked at, what we priced, and the official input behind it."))

    # ------------------------------------------------------------------ coverage
    cov = []
    for s in sports:
        sr = [r for r in rows if r["sport"] == s]
        sp = [r for r in sr if r.get("markets")]
        srcs = sorted({r["source_url"] for r in sr if r.get("source_url")})
        names = sorted({r["source_name"] for r in sr if r.get("source_name")})
        cov.append(f"""<tr><td><strong>{esc(s)}</strong></td><td>{len(sr)}</td><td>{len(sp)}</td>
<td>{len(sr) - len(sp)}</td>
<td>{'yes' if sp else 'no — flagged'}</td>
<td>{''.join(f'<div class="small"><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></div>' for u in srcs[:4])}</td>
<td class="small">{esc('; '.join(names)[:180])}</td></tr>""")
    body = f"""
<table><thead><tr><th>Sport</th><th>Rows</th><th>Priced</th><th>No line</th><th>Own lines?</th>
<th>Official source(s)</th><th>Source name</th></tr></thead><tbody>{''.join(cov)}</tbody></table>
<h3>Sports with no row in this window</h3>
<p class="small">These in-scope OLBG sports produced no verifiable fixture in the window from an official
source; each is listed with the official site checked so the owner can review it.</p>
<table><thead><tr><th>Sport</th><th>Official site checked</th><th>Result</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(s)}</td><td><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)}</a></td><td class="small">{esc(note)}</td></tr>' for s, u, note in NO_ROW_SPORTS)}
</tbody></table>
"""
    write("coverage.html", page("Coverage", "coverage.html", body,
                                "Which sports we covered, what we priced, and the official source behind each row."))

    # ---- OLBG live board vs our own desk -------------------------------------------
    def norm(x: str) -> set:
        return {w for w in re.findall(r"[a-z0-9]{3,}", (x or "").lower())}

    desk_by_sport = defaultdict(list)
    for r in rows:
        desk_by_sport[r["sport"]].append(r)
    olbg_rows, matched_events = [], 0
    for key, blk in sorted((olbg_board.get("sports") or {}).items()):
        for e in blk["events"]:
            sport = e["sport"]
            ours = ""
            if sport in desk_by_sport:
                want = norm(e["home"]) | norm(e["away"])
                for r in desk_by_sport[sport]:
                    have = norm(r["home"]) | norm(r["away"])
                    pick = r.get("pick") or {}
                    if want and len(want & have) >= max(2, len(want) - 1) and pick.get("selection"):
                        ours = (r["id"] + " · " + esc(pick["selection"]) + " "
                                + ams(pick["fair_american"]) + " (" + r["confidence"] + ")")
                        matched_events += 1
                        break
            olbg_rows.append(
                '<tr><td>' + esc(sport) + '</td><td>' + esc(e["home"])
                + (' vs ' + esc(e["away"]) if e["away"] else '') + '</td>'
                + '<td>' + (esc(str(e["tips_on_olbg"])) if e["tips_on_olbg"] is not None else '—') + '</td>'
                + '<td>' + (esc(ours) if ours else '<span class="chip">no verified row</span>') + '</td>'
                + '<td><a href="' + esc(e["url"]) + '" target="_blank" rel="noopener">'
                + str(e["event_id"]) + '</a></td></tr>')
    olbg_rows = "".join(olbg_rows)
    olbg_events = olbg_board.get("events_total", 0)

    # ------------------------------------------------------------------ olbg
    sport_rows = "".join(
        f'<tr><td>{i}</td><td>{esc(n)}</td><td>{esc(k)}</td>'
        f'<td><a href="https://www.olbg.com/betting-tips/{esc(n.replace(" ", "_"))}/{i}" target="_blank" rel="noopener">/betting-tips/{esc(n.replace(" ", "_"))}/{i}</a></td></tr>'
        for i, n, k in OLBG_SPORTS)
    body = f"""
<p class="lede">OLBG.com is used here only as the taxonomy index — the list of sports and markets the site
offers. Every fixture on this desk is verified against the sport's own governing body, not against OLBG.</p>
<h3>URL structure (observed live 2026-10-22)</h3>
<pre>https://www.olbg.com/betting-tips/&lt;Sport&gt;/&lt;Sport_ID&gt;
https://www.olbg.com/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;Sport_ID&gt;
https://www.olbg.com/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;Event&gt;/&lt;Sport_ID&gt;?event_id=&lt;event_id&gt;
https://www.olbg.com/best-tipsters/&lt;Sport&gt;/&lt;Sport_ID&gt;</pre>
<p class="small">The trailing integer on every betting-tips URL is the <strong>sport id</strong>, not a
market id. Sitemap: <a href="https://www.olbg.com/sitemap-betting-tips.xml" target="_blank" rel="noopener">/sitemap-betting-tips.xml</a>
(committed raw copy: <a href="../data/session-3a6388d2/raw/olbg_sitemap.txt">olbg_sitemap.txt</a>).</p>
<h3>Sport ids enumerated from the live sitemap (2026-10-22)</h3>
<table><thead><tr><th>ID</th><th>Sport</th><th>Our classification</th><th>Landing page</th></tr></thead>
<tbody>{sport_rows}</tbody></table>
<h3>Market taxonomy observed on an event page</h3>
<p class="small">Read live on
<a href="https://www.olbg.com/betting-tips/Darts/All_Darts/All_Events/Gerwyn_Price_vs_Rob_Cross/15?event_id=32325" target="_blank" rel="noopener">a darts event page</a>:
<strong>Win Match 2-way</strong>, <strong>Handicap 2-way</strong> (±1.50 legs) and <strong>Total Legs</strong>
(Over/Under 9.50) — the same three families (winner, handicap, total) that this desk originates for every
priced sport. Football events show Full Time Result, horse racing shows a Daily Racing win market, rugby
union shows To Win.</p>
<h3>Behaviour that matters for anyone re-scraping</h3>
<ul class="small">
<li>Event start times render in the requesting edge node's local timezone; the SSR markup carries the
UTC value in <code>&lt;time itemprop="startDate" datetime="…Z"&gt;</code>.</li>
<li>Prices are shipped in data attributes (<code>data-decimal</code>, <code>data-american</code>,
<code>data-fractional</code>) and only filled in after client-side hydration, so a text reader sees an
empty price.</li>
<li>OLBG only lists events that already have at least one tip, so an untipped fixture is not enumerable
from the site — which is why this desk builds its fixture list from official league feeds instead.</li>
<li>Tipster consensus is shown as "n/m Win Tips" plus a percentage; it is a community sentiment figure,
not a probability, and is not used anywhere in our numbers.</li>
</ul>
<h3>OLBG's own live board at capture time vs this desk</h3>
<p class="small">{esc(olbg_events)} events were read out of the committed bytes of OLBG's {esc(olbg_board.get("sports_captured", 0))}
per-sport pages on 22 Oct 2026. {esc(matched_events)} of them match a row on our own desk (named below and
linked to the official source); the rest are either outright markets OLBG carries for 2027 competitions, or
events in a sport where no official pairing could be verified in the window — for those we publish no line
rather than guess one. This is a completeness cross-check only: <strong>no OLBG price, percentage or tipster
figure is used anywhere in our numbers</strong>.</p>
<table id="tbl-olbg"><thead><tr><th data-sort="0">Sport</th><th data-sort="1">OLBG event</th>
<th data-sort="2">Tips on OLBG</th><th data-sort="3">Our desk</th><th>OLBG event id</th></tr></thead>
<tbody>
{olbg_rows}
</tbody></table>
"""
    write("olbg.html", page("OLBG reverse engineering", "olbg.html", body,
                            "How OLBG.com is put together — sport ids, URL patterns, market taxonomy, SSR behaviour."))

    # ------------------------------------------------------------------ review
    s = review.get("summary", {})
    findings = review.get("findings", [])
    by_kind = Counter(f["kind"] for f in findings)
    kinds = "".join(f'<tr><td>{esc(k)}</td><td>{n}</td></tr>' for k, n in by_kind.most_common())
    def finding_row(f, extra_attr=""):
        link = ('<a href="' + esc(f["link"]) + '" target="_blank" rel="noopener">open</a>'
                if f.get("link") else "")
        return ('<tr' + extra_attr + '><td>' + esc(f["id"]) + '</td><td>' + esc(f["kind"])
                + '</td><td>' + esc(f["severity"]) + '</td><td>' + esc(f["sport"]) + '</td><td>'
                + esc(f["date"]) + '</td><td>' + esc(f["match"]) + '</td><td class="small">'
                + esc(f["detail"]) + '</td><td>' + link + '</td></tr>')

    frows = "".join(finding_row(f, ' data-kind="' + esc(f["kind"]) + '"') for f in findings)
    cross = "".join(
        f'<tr><td>{esc(c["sport"])}</td><td>{c["board_ad_rows"]}</td><td>{c["board_ad_priced"]}</td>'
        f'<td>{c["master_rows_from_today"]}</td><td>{c["master_verified"]}</td></tr>'
        for c in review.get("cross_check", []))
    body = f"""
<div class="cards">
<div class="card"><div class="k">{esc(s.get('master_rows', 0))}</div><div class="l">canonical rows reviewed</div></div>
<div class="card"><div class="k">{esc(len(findings))}</div><div class="l">findings</div></div>
<div class="card"><div class="k">{esc(s.get('rows_before_cutoff', 0))}</div><div class="l">dated before 22 Oct</div></div>
<div class="card"><div class="k">{esc(s.get('rows_without_source', 0))}</div><div class="l">no source URL</div></div>
<div class="card"><div class="k">{esc(s.get('rows_unverified', 0))}</div><div class="l">unverified</div></div>
<div class="card"><div class="k">{esc(s.get('rows_high_confidence', 0))}</div><div class="l">High confidence</div></div>
</div>
<p class="lede">Every row of <code>data/master.json</code> (canonical board, generated
{esc(s.get('master_generated_on',''))}) was walked and checked. Findings are evidence only — nothing in
another board's files was edited by this session.</p>
<div class="controls"><input placeholder="Filter findings" data-filter-for="tbl-f" data-filter-col="6"></div>
<table id="tbl-f"><thead><tr><th>ID</th><th>Kind</th><th>Severity</th><th>Sport</th><th>Date</th>
<th>Match</th><th>Detail</th><th>Link</th></tr></thead><tbody>{frows}</tbody></table>
<h3>Findings by kind</h3>
<table><thead><tr><th>Kind</th><th>Rows</th></tr></thead><tbody>{kinds}</tbody></table>
<h3>Our desk versus the canonical board (rows dated 22 Oct or later)</h3>
<table><thead><tr><th>Sport</th><th>Board AD rows</th><th>Board AD priced</th>
<th>Canonical rows</th><th>Canonical verified</th></tr></thead><tbody>{cross}</tbody></table>
"""
    write("review.html", page("Repo review", "review.html", body,
                              "Line-by-line review of the canonical board, with a link for every finding."))

    # ------------------------------------------------------------------ flagged
    unpriced_rows = "".join(
        f'<tr><td>{esc(r["id"])}</td><td>{esc(r["sport"])}</td><td>{esc(r["date"])}</td>'
        f'<td>{esc(r["away"])} @ {esc(r["home"])}</td>'
        f'<td class="small">{esc((r.get("flags") or [{}])[0].get("text", ""))}</td>'
        f'<td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">official source</a></td></tr>'
        for r in sorted(unpriced, key=lambda x: (x["sport"], x["date"])))
    capfails = []
    for name, m in manifests:
        for e in m["entries"]:
            if e["http_status"] != 200:
                capfails.append((name, e))
    cf = "".join(
        f'<tr><td>{esc(nm)}</td><td>{esc(e["id"])}</td><td>{esc(e["sport"])}</td>'
        f'<td><a href="{esc(e["url"])}" target="_blank" rel="noopener">{esc(e["url"])}</a></td>'
        f'<td class="small">{esc(e["error"])}</td></tr>' for nm, e in capfails)
    rf = "".join(finding_row(f) for f in findings
                 if f["severity"] in ("blocking", "needs-review"))
    body = f"""
<div class="note"><strong>What this page is.</strong> Everything the owner should eyeball. None of it
blocks the site: values that could not be confirmed are left blank rather than filled in.</div>
<h3>Rows published without a line ({len(unpriced)})</h3>
<p class="small">The fixture detail is verified from the official source; the price and pick are deliberately
blank because an official strength input could not be read at capture time.</p>
<table><thead><tr><th>ID</th><th>Sport</th><th>Date</th><th>Fixture</th><th>Why no line</th><th>Source</th></tr></thead>
<tbody>{unpriced_rows}</tbody></table>
<h3>Official captures that failed ({len(capfails)})</h3>
<p class="small">Every failure is recorded with the URL and the HTTP/transport error so it can be retried or
reviewed by hand. Nothing was substituted from a non-official source.</p>
<table><thead><tr><th>Pass</th><th>Id</th><th>Sport</th><th>URL</th><th>Error</th></tr></thead><tbody>{cf}</tbody></table>
<h3>Repository-review findings needing a decision ({len(rf)})</h3>
<table><thead><tr><th>ID</th><th>Kind</th><th>Severity</th><th>Detail</th><th>Link</th></tr></thead><tbody>{rf}</tbody></table>
"""
    write("flagged.html", page("Flagged for review", "flagged.html", body,
                               "Unpriced rows, failed official captures and repository findings — with a link for each."))

    # ------------------------------------------------------------------ methodology
    body = f"""
<h3>How the data was captured</h3>
<p>The interactive sandbox has no general HTTPS egress, so the raw bytes of every official request are
fetched by a GitHub Actions runner (<code>.github/workflows/ad-3a6388d2.yml</code>) and committed with the
URL, HTTP status, byte count, UTC timestamp and SHA-256 of the response. Parsing, line origination,
verification and site building then happen locally against those committed bytes, so any published value can
be re-derived by a reviewer. Capture manifests:
<a href="../data/session-3a6388d2/manifest.json">pass 1</a>,
<a href="../data/session-3a6388d2/manifest_rankings.json">rankings</a>,
<a href="../data/session-3a6388d2/manifest3.json">pass 3</a>,
<a href="../data/session-3a6388d2/manifest4.json">pass 4</a>,
<a href="../data/session-3a6388d2/manifest5.json">pass 5</a>.</p>
<h3>Models</h3>
<ul>
<li><strong>Ice hockey (NHL)</strong> — independent Poisson goal model. Each team's goals-for and
goals-against per game are read from the official NHL standings and shrunk towards the league mean
(weight = GP/(GP+14)); the home-ice advantage is measured from the official home/road splits rather than
assumed. Ties after 60 minutes are split 52/48 to the home side for the moneyline, which is how overtime
and shootouts actually behave. Puck-line prices use the regulation margin (an OT win is still a one-goal
game).</li>
<li><strong>Baseball (MLB)</strong> — Pythagorean win expectancy (exponent 1.83) from official runs
scored/allowed, combined with a Poisson runs model for totals and a normal margin model (sd 4.35) for the
run line; a 1.08 home-field multiplier is applied. The World Series outright is a binomial first-to-four
simulation built from those same per-game probabilities.</li>
<li><strong>Rugby union (URC)</strong> — attack/defence points model fitted to the official URC table
(points for/against per game, shrunk towards the league mean), a normal margin model (sd 15.5) for the
handicap, and a normal total model (sd 15.0). Home advantage and the 2% draw rate are stated assumptions,
not verified figures.</li>
</ul>
<h3>Confidence and the odds window</h3>
<p><strong>High</strong> = model probability ≥ 0.700 · <strong>Medium</strong> = 0.600–0.700 ·
<strong>Low</strong> = below 0.600. A row is capped at Medium when the official sample is thin (fewer than
five team-games at capture time), which is why the URC — three rounds played — cannot grade High.</p>
<p>The −250 … +10000 window is applied to our own fair American price for the selection. −250 is a 71.43%
chance, so the overlap between "≥70%" and "no shorter than −250" is narrow: it only exists between 70.0%
and 71.4%. Picks above that band are published and explicitly labelled
<em>shorter than −250</em> rather than dropped.</p>
<h3>Publishing our own lines</h3>
<p>Fair price = 1 / model probability. Our book price applies a 4.2% over-round on two-way markets and
5.2% on three-way markets, distributed in proportion to the fair probability.</p>
<h3>Predictions</h3>
<p>One hand-written prediction per High-confidence selection, each naming the teams, their current form and
recent record, and the selection itself. Every statistic quoted is taken from that row's verified official
inputs and is re-checked by <code>scripts/session-3a6388d2/verify.py</code>.</p>
<h3>Rules we never break</h3>
<ul>
<li>No bookmaker price, tipster percentage or third-party rating is used as an input.</li>
<li>If a value cannot be read from an official source, it is left blank and the row is flagged.</li>
<li>Every row links to the official page it came from; captures are hashed so a reviewer can re-check them.</li>
</ul>
"""
    write("methodology.html", page("Methodology", "methodology.html", body,
                                   "Where the data comes from, how the lines are built, and what we refuse to guess."))

    # ------------------------------------------------------------------ sources
    srows = []
    for name, m in manifests:
        for e in m["entries"]:
            rawlink = f"../data/session-3a6388d2/raw/{e['id']}.txt" if e.get("saved_as") else ""
            raw_cell = ('<a href="' + esc(rawlink) + '">raw</a>') if rawlink else "—"
            srows.append(
                '<tr data-status="' + esc(e["http_status"]) + '"><td>'
                + esc(name.replace("manifest", "").replace(".json", "") or "1") + '</td>'
                + '<td>' + esc(e["sport"]) + '</td><td>' + esc(e["id"]) + '</td>'
                + '<td><a href="' + esc(e["url"]) + '" target="_blank" rel="noopener">'
                + esc(e["url"]) + '</a></td>'
                + '<td>' + esc(e["http_status"]) + '</td><td>' + esc(e.get("fetched_at_utc", ""))[:19] + '</td>'
                + '<td class="small">' + esc((e.get("sha256_raw") or "")[:16]) + '</td>'
                + '<td>' + raw_cell + '</td></tr>')
    body = f"""
<p class="lede">Every official source this board touched, with the HTTP status, capture time and the SHA-256
of the exact bytes we parsed. Raw files are committed in
<code>data/session-3a6388d2/raw/</code>.</p>
<div class="controls"><input placeholder="Filter sources" data-filter-for="tbl-s" data-filter-col="3"></div>
<table id="tbl-s"><thead><tr><th>Pass</th><th>Sport</th><th>Id</th><th>URL</th><th>HTTP</th>
<th>Captured (UTC)</th><th>SHA-256</th><th>Raw</th></tr></thead><tbody>{''.join(srows)}</tbody></table>
"""
    write("sources.html", page("Sources", "sources.html", body,
                               "Every official source touched, with status, timestamp and hash."))

    # ------------------------------------------------------------------ sport pages
    for s in sports:
        sr = [r for r in rows if r["sport"] == s]
        sp = [r for r in sr if r.get("markets")]
        body = f"""
<div class="cards">
<div class="card"><div class="k">{len(sr)}</div><div class="l">rows</div></div>
<div class="card"><div class="k">{len(sp)}</div><div class="l">priced</div></div>
<div class="card"><div class="k">{sum(1 for r in sr if r.get('confidence')=='High')}</div><div class="l">High</div></div>
<div class="card"><div class="k">{len({r['source_url'] for r in sr if r.get('source_url')})}</div><div class="l">official sources</div></div>
</div>
<table id="tbl-sport">{table_cols}<tbody>
{''.join(row_tr(r, True) for r in sorted(sr, key=lambda x: (x['date'], x.get('time_utc') or '')))}
</tbody></table>
<p class="small"><a href="../index.html">← back to dashboard</a></p>
"""
        write(os.path.join("sports", f"{slug(s)}.html"),
              page(f"{s}", "matches.html", body,
                   f"{s} — every row, with the official source it was verified from.", base="../"))

    print(f"site written: {SITE} ({len(rows)} rows, {len(sports)} sport pages)")
    return 0


NO_ROW_SPORTS = [
    ("Tennis", "https://www.atptour.com/en/tournaments",
     "ATP returns HTTP 403 to automated readers; the two official event sites captured (Vienna, Basel) publish the event dates but not a machine-readable draw, so no pairing could be verified — no row published."),
    ("Darts", "https://www.pdc.tv/tournaments",
     "pdc.tv is a Nuxt SPA whose tournament and ranking data is fetched client-side; the captured pages carried no fixture payload, so no pairing was verified against the PDC — no row published."),
    ("Snooker", "https://www.wst.tv/",
     "WST home, calendar, matches and rankings all captured but carry no machine-readable fixture payload — no row published."),
    ("Golf", "https://www.pgatour.com/schedule",
     "PGA Tour schedule captured (Butterfield Bermuda Championship, 22–25 Oct 2026) but the leaderboard/field is client-rendered, so no line could be originated — covered on the coverage page instead of as a priced row."),
    ("Handball", "https://www.eurohandball.com/en/",
     "EHF and EHF Champions League pages captured with no fixture payload in the response bytes — no row published."),
    ("Volleyball", "https://www.legavolley.it/calendari",
     "SuperLega calendar captured but the fixture list renders client-side — no row published."),
    ("Aussie Rules", "https://www.afl.com.au/aflw/fixture",
     "AFL/AFLW fixture pages captured; the fixture list is client-rendered and no round was readable from the committed bytes — no row published."),
    ("Table Tennis", "https://www.worldtabletennis.com/",
     "WTT blocks automated readers (HTTP 403) and the ITTF events path returned 404 — no row published."),
    ("Badminton", "https://bwfbadminton.com/",
     "BWF home and rankings captured without a readable fixture payload (tournaments path 404) — no row published."),
    ("Greyhounds", "https://www.gbgb.org.uk/results/",
     "GBGB results page captured but the meeting list renders client-side — no row published."),
]


def write(path: str, content: str) -> None:
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as fh:
        fh.write(content)


if __name__ == "__main__":
    raise SystemExit(main())

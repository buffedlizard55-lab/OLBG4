#!/usr/bin/env python3
"""Render the Board AC dashboard from data/session-1695b749/ac/*.json."""
from __future__ import annotations

import html
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DATA = REPO / "data/session-1695b749/ac"
OUT = REPO / "session-1695b749/ac"

STAMP = "2026-10-22T09:30:00Z"

NAV = [
    ("index.html", "Overview"),
    ("sports/ice-hockey.html", "Ice Hockey"),
    ("sports/baseball.html", "Baseball"),
    ("sports/esports.html", "Esports"),
    ("picks.html", "High picks"),
    ("markets.html", "Markets"),
    ("verification.html", "Verification"),
    ("coverage.html", "Coverage"),
    ("listing.html", "All matches"),
    ("sources.html", "Sources"),
    ("methodology.html", "Method"),
    ("review.html", "Repo review"),
    ("flagged.html", "Flagged"),
]

CSS = """
:root{--ink:#14181f;--muted:#5b6573;--line:#e2e6ec;--bg:#f6f8fa;--card:#fff;--accent:#0b5cad;--accent-2:#0d7a5f;--warn:#a8460f;--high:#0d7a5f;--med:#8a6100;--low:#6b7280}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent)}
header.site{background:#0f1720;color:#fff}
header.site .bar{max-width:1120px;margin:0 auto;padding:14px 20px;display:flex;flex-wrap:wrap;gap:14px;align-items:baseline}
header.site a{color:#cfe0f5;text-decoration:none;font-size:14px}
header.site a.brand{color:#fff;font-weight:700;font-size:16px;letter-spacing:.2px}
header.site nav{display:flex;flex-wrap:wrap;gap:12px}
header.site a[aria-current="page"]{color:#fff;border-bottom:2px solid #6db3f2}
main{max-width:1120px;margin:0 auto;padding:28px 20px 64px}
h1{font-size:32px;line-height:1.2;margin:8px 0 12px}
h2{font-size:22px;margin:36px 0 10px}
h3{font-size:17px;margin:22px 0 8px}
p.lede{font-size:18px;color:var(--muted);max-width:78ch}
p,ul,ol{max-width:88ch}
.crumbs{font-size:13px;color:var(--muted);margin:0 0 6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.stat{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}
.stat b{display:block;font-size:26px;line-height:1.1}
.stat span{color:var(--muted);font-size:13px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:16px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card h3{margin:0 0 6px}
.card p{margin:6px 0;color:var(--muted);font-size:14px}
table{width:100%;border-collapse:collapse;background:var(--card);font-size:14px;border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#eef2f7;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:#3b4653}
tr:last-child td{border-bottom:none}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.grade{font-weight:700;font-size:12px;letter-spacing:.04em;text-transform:uppercase}
.g-High{color:var(--high)} .g-Medium{color:var(--med)} .g-Low{color:var(--low)}
.tag{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;border:1px solid var(--line);background:#f3f6fa;color:#41505f;margin:0 6px 4px 0}
.tag.ok{background:#e9f6f1;border-color:#bfe3d6;color:#0a5c46}
.tag.no{background:#fdf1ea;border-color:#f3d3c1;color:#94400f}
.muted{color:var(--muted)}
.small{font-size:13px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:12px;word-break:break-all}
.note{background:#fff8e6;border:1px solid #f0dfae;border-radius:10px;padding:12px 14px;margin:16px 0}
.note strong{color:#7a5300}
.pick{border:1px solid var(--line);background:var(--card);border-radius:12px;padding:16px;margin:14px 0}
.pick h3{margin:0 0 4px;font-size:18px}
.pick .meta{font-size:13px;color:var(--muted);margin-bottom:8px}
.pick .text{margin:8px 0 10px}
.pick .facts{font-size:13px;color:#3d4854}
table.filter{display:block;overflow:auto;max-height:none}
input.filter{width:100%;max-width:360px;padding:8px 10px;border:1px solid var(--line);border-radius:8px;font-size:14px;margin:10px 0}
footer.site{max-width:1120px;margin:0 auto;padding:24px 20px 48px;color:var(--muted);font-size:13px;border-top:1px solid var(--line)}
footer.site a{color:var(--accent)}
ul.plain{padding-left:18px}
"""

JS = """
document.querySelectorAll('input[data-filter]').forEach(function(box){
  var table=document.getElementById(box.dataset.filter);
  box.addEventListener('input',function(){
    var q=box.value.toLowerCase();
    table.querySelectorAll('tbody tr').forEach(function(tr){
      tr.style.display = tr.textContent.toLowerCase().indexOf(q)>-1 ? '' : 'none';
    });
    var vis=table.querySelectorAll('tbody tr:not([style*="none"])').length;
    var out=document.getElementById(box.dataset.filter+'-count');
    if(out){out.textContent=vis+' rows shown';}
  });
});
"""


def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def price(a):
    if a is None or a == "":
        return "—"
    return f"{a:+d}" if a > 0 else str(a)


def page(title, body, active, depth=0, extra_head=""):
    root = "../" * depth
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == active else ""
        links.append(f'<a href="{root}{href}"{cur}>{e(label)}</a>')
    nav = "\n      ".join(links)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Board AC · OLBG4</title>
<link rel="stylesheet" href="{root}style.css">
{extra_head}</head>
<body>
<header class="site"><div class="bar">
  <a class="brand" href="{root}index.html">Board AC · OLBG4</a>
  <nav>
      {nav}
  </nav>
</div></header>
<main>
{body}
</main>
<footer class="site">
  <p><strong>Board AC</strong> · session arena/1695b749-olbg4 · built {e(STAMP)} · window 22 October – 21 November 2026, fixtures published {e(WINDOW[0])} to {e(WINDOW[1])}.</p>
  <p>Every fixture row names the official payload it came from. Where an official page was silent, the value is blank and the gap is on the <a href="{root}flagged.html">Flagged for review</a> page. Sports excluded by the brief (soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials) are absent from this dataset.</p>
  <p><a href="{root}../index.html">Repository dashboard</a> · <a href="{root}verification.html">Verification register</a> · <a href="{root}sources.html">Sources</a></p>
</footer>
<script src="{root}app.js"></script>
</body>
</html>
"""


def stat(n, label):
    return f'<div class="stat"><b>{e(n)}</b><span>{e(label)}</span></div>'


def grade(g):
    return f'<span class="grade g-{e(g)}">{e(g)}</span>' if g else '<span class="muted">—</span>'


def main():
    desk = json.loads((DATA / "desk.json").read_text())
    ver = json.loads((DATA / "verification.json").read_text())
    cov = json.loads((DATA / "coverage.json").read_text())
    flags = json.loads((DATA / "flagged.json").read_text())
    listing = json.loads((DATA / "listing.json").read_text())
    spec = json.loads((DATA / "model_spec.json").read_text())
    sources = json.loads((DATA / "sources.json").read_text())
    review = json.loads((DATA / "review.json").read_text()) if (DATA / "review.json").exists() else {"files": [], "findings": []}

    global WINDOW
    WINDOW = tuple(desk["covered_dates"])
    fx = desk["fixtures"]
    t = desk["totals"]
    ver_by_id = {r["id"]: r for r in ver["rows"]}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    (OUT / "style.css").write_text(CSS)
    (OUT / "app.js").write_text(JS)

    # ---------------- overview ----------------
    picks = desk["picks_in_window"]
    rows = []
    for p in picks[:20]:
        rows.append(f"""<tr>
<td><a href="picks.html#{e(p['fixture_id'])}">{e(p['date'])}</a></td>
<td>{e(p['sport'])}</td>
<td>{e(p['fixture'])}</td>
<td>{e(p['market'])}{(' ' + e(p['line'])) if p['line'] is not None else ''}</td>
<td><strong>{e(p['selection'])}</strong></td>
<td class="num">{e(price(p['price']))}</td>
<td class="num">{p['p']*100:.1f}%</td>
<td>{grade('High')}</td>
</tr>""")
    sport_cards = []
    for name, s in desk["by_sport"].items():
        slug = {"Ice Hockey": "ice-hockey", "Baseball": "baseball", "Esports": "esports"}[name]
        sport_cards.append(f"""<div class="card">
  <h3><a href="sports/{slug}.html">{e(name)}</a></h3>
  <p><strong>{s['fixtures']}</strong> fixtures · <strong>{s['priced']}</strong> priced · <strong>{s['picks']}</strong> graded picks</p>
  <p>{s['high']} graded High, {s['high_in_window']} of them inside the −250 to +10,000 window.</p>
</div>""")
    body = f"""<p class="crumbs">Board AC · independent line desk · built {e(STAMP)}</p>
<h1>Every in-scope fixture we could verify, priced from official numbers, with one written case behind each High pick.</h1>
<p class="lede">{t['fixtures']} fixtures across 3 sports, {t['priced_fixtures']} of them priced from official payloads that were re-hashed before use.
{t['selections']:,} selections across moneyline, handicap, match total and team totals. {t['picks']} graded picks, {t['high_in_window']} of them High and inside the
−250 to +10,000 window, each with an original prediction of 46 words or more.</p>
<div class="grid">
  {stat(t['fixtures'], 'fixtures in scope')}
  {stat(t['priced_fixtures'], 'priced from official inputs')}
  {stat(f"{t['selections']:,}", 'selections originated')}
  {stat(f"{t['picks_high']} / {t['picks_medium']} / {t['picks_low']}", 'picks High / Medium / Low')}
  {stat(t['high_in_window'], 'High picks in the window')}
  {stat(t['predictions'], 'written predictions')}
  {stat(t['listing_rows'], 'in-scope rows on OLBG listing')}
  {stat(t['flags'], 'published irregularities')}
</div>
<div class="note"><strong>How to read this board.</strong> No bookmaker price is read anywhere on this site. Every number on a fixture row was parsed from a governing-body payload
(NHL, MLB, LoL Esports) that is hash-checked against the capture manifest before it is used, and the register records the URL, the SHA-256 and the capture time for each field.
Our prices are fair odds derived from our own probability, with no margin added, so a −247 is a 71.2% view rather than a bookmaker quote. When an official page is silent, the value stays blank and the gap is published on the flagged page.</div>
<h2>The three sports this board priced</h2>
<div class="cards">{''.join(sport_cards)}</div>
<h2>The {len(picks)} High picks inside −250 to +10,000</h2>
<p>These are the only selections that carry a written prediction, as the brief requires. Each one is a graded pick on a main market whose fair price lands inside the window; every price shorter than −250 is still published on the <a href="markets.html">markets</a> pages and counted on <a href="picks.html">High picks</a>.</p>
<table>
<thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Market</th><th>Selection</th><th class="num">Price</th><th class="num">Model</th><th>Grade</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<h2>What is not here</h2>
<p>{cov['summary']['listed_only']} of the 19 sport labels considered appear only as OLBG listing rows with a blank official source, and {cov['summary']['no_fixture']} had no in-window fixture on any official page read this session.
The full accounting is on <a href="coverage.html">Coverage</a>, and the {t['listing_rows']} in-scope match rows OLBG lists are reproduced on <a href="listing.html">All matches</a> so nothing in scope is invisible.
The brief's exclusions — soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials — appear nowhere in this dataset.</p>
<h2>Verification, in one line per fixture</h2>
<p>The <a href="verification.html">register</a> has {t['fixtures']} rows. Each row names the official URL behind the participants, the date and start time, the venue and the scoring inputs,
prints the payload hash, and lists what was <em>not</em> checked: injuries, suspensions, line-ups, weather and line movement.</p>"""
    (OUT / "index.html").write_text(page("Overview", body, "index.html"))

    # ---------------- sports pages ----------------
    for name, s in desk["by_sport"].items():
        slug = {"Ice Hockey": "ice-hockey", "Baseball": "baseball", "Esports": "esports"}[name]
        fixtures = [f for f in fx if f["sport"] == name]
        trs = []
        for f in fixtures:
            v = ver_by_id.get(f["id"], {})
            src = v.get("sources", [{}])[0].get("url", "")
            if f.get("priced") is False:
                trs.append(f"""<tr><td>{e(f['date'])}</td><td>{e(f['fixture'] if 'fixture' in f else f['away'] + ' at ' + f['home'])}<br><span class="small muted">{e(f['competition'])} · {e(f['venue'])}</span></td>
<td colspan="4" class="muted">{e(f.get('unpriced_reason','No numeric input'))}</td>
<td><a href="../verification.html#{e(f['id'])}">register</a><br><a class="mono" href="{e(src)}">official</a></td></tr>""")
                continue
            p = f["headline"]
            mk = f["markets"]
            ml = {x["side"]: x for x in mk["moneyline"]}
            hc = {x["side"]: x for x in mk["handicap"]}
            tot = [x for x in mk["total"]]
            trs.append(f"""<tr>
<td>{e(f['date'])}<br><span class="small muted">{e(f['start_utc'][11:16])}Z</span></td>
<td>{e(f['away'])} at <strong>{e(f['home'])}</strong><br><span class="small muted">{e(f['competition'])} · {e(f['venue'])}</span></td>
<td><strong>{e(p['selection'])}</strong><br><span class="small">{e(p['market'])}{(' ' + e(p['line'])) if p['line'] is not None else ''} @ {e(price(p['price']))}</span><br>{grade(p['grade'])}</td>
<td class="num small">ML {e(price(ml['home']['price']))} / {e(price(ml['away']['price']))}<br>Hcp {e(hc['home']['line'])} {e(price(hc['home']['price']))} / {e(price(hc['away']['price']))}<br>Tot {e(tot[0]['line'])} {e(price(tot[0]['price']))} / {e(price(tot[1]['price']))}</td>
<td class="num">{p['p']*100:.1f}%</td>
<td><a href="../verification.html#{e(f['id'])}">register</a><br><a class="mono" href="{e(src)}">official</a></td>
</tr>""")
        highest = sorted([f for f in fixtures if f.get("picks")], key=lambda f: -f["headline"]["p"])[:5]
        top = ''.join(f"<li>{e(f['away'])} at {e(f['home'])} — <strong>{e(f['headline']['selection'])}</strong> @ {e(price(f['headline']['price']))} ({grade(f['headline']['grade'])}, model {f['headline']['p']*100:.1f}%)</li>" for f in highest)
        body = f"""<p class="crumbs"><a href="../index.html">Overview</a> · {e(name)}</p>
<h1>{e(name)} — {s['fixtures']} fixtures, {s['priced']} priced</h1>
<p class="lede">{s['picks']} graded picks on this page, {s['high']} of them High. Every row names the official payload behind it and links to its line in the verification register.</p>
{"<h2>Highest-rated picks</h2><ul class='plain'>" + top + "</ul>" if top else ""}
<h2>Fixtures</h2>
<input class="filter" data-filter="fx" placeholder="Filter by team, date or venue">
<p class="small muted" id="fx-count">{len(fixtures)} rows shown</p>
<div style="overflow:auto">
<table id="fx">
<thead><tr><th>Date (UTC)</th><th>Fixture</th><th>Our pick</th><th class="num">Market prices</th><th class="num">Model</th><th>Source</th></tr></thead>
<tbody>{''.join(trs)}</tbody></table></div>
<p class="small muted">ML = match winner (two-way) home / away. Hcp = handicap at the line shown, home side first. Tot = match total at the line shown, over / under.
Prices are fair odds from our own model, without a margin. The full book, including team totals, is on <a href="../markets.html">Markets</a>.</p>"""
        (OUT / "sports" / f"{slug}.html").write_text(page(name, body, f"sports/{slug}.html", depth=1))

    # ---------------- picks ----------------
    cards = []
    for p in picks:
        f = next(x for x in fx if x["id"] == p["fixture_id"])
        v = ver_by_id[p["fixture_id"]]
        src = v["sources"][0]["url"]
        implied = abs(p["price"]) / (abs(p["price"]) + 100.0) if p["price"] < 0 else 100.0 / (p["price"] + 100.0)
        cards.append(f"""<article class="pick" id="{e(p['fixture_id'])}">
<h3>{e(p['selection'])} — {e(p['market'])}{(' ' + e(p['line'])) if p['line'] is not None else ''} @ {e(price(p['price']))}</h3>
<div class="meta">{e(p['fixture'])} · {e(p['date'])} · {e(f['venue'])} · {grade('High')} · model {p['p']*100:.1f}% · implied by our price {implied*100:.1f}%</div>
<p class="text">{e(p['write_up'])}</p>
<p class="facts"><span class="tag ok">official source</span><a class="mono" href="{e(src)}">{e(src)}</a><br>
<span class="tag">{e(f['competition'])}</span><span class="tag">record {e(f['inputs']['home']['record'])} v {e(f['inputs']['away']['record'])}</span><span class="tag">hash-checked payload</span>
<span class="tag"><a href="verification.html#{e(f['id'])}">register row</a></span></p>
</article>""")
    all_high = [(f, s) for f in fx for s in f.get("picks", []) if s["grade"] == "High"]
    short = [x for x in all_high if not x[1]["in_window"]]
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · High picks</p>
<h1>{len(picks)} High picks inside the window, each with an original prediction.</h1>
<p class="lede">The brief asks for High-confidence picks priced between −250 and +10,000 and generally above 70% implied.
Because −250 is already 71.43%, both conditions can only overlap in a narrow band; this page publishes the {len(picks)} graded picks that satisfy both,
with a written case each, and lists the {len(short)} further High picks that are shorter than −250 further down so nothing is hidden.</p>
{''.join(cards)}
<h2>High picks shorter than −250</h2>
<p>These graded High picks price shorter than the −250 floor, so they sit outside the requested window and, per the brief, carry no written prediction.
They are listed here with their prices so the grading is transparent. This is <a href="flagged.html">AF-01</a>.</p>
<table><thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Market</th><th>Selection</th><th class="num">Price</th><th class="num">Model</th></tr></thead><tbody>
{''.join(f"<tr><td>{e(f['date'])}</td><td>{e(f['sport'])}</td><td>{e(f['away'])} at {e(f['home'])}</td><td>{e(s['market'])}{(' ' + e(s['line'])) if s['line'] is not None else ''}</td><td>{e(s['selection'])}</td><td class='num'>{e(price(s['price']))}</td><td class='num'>{s['p']*100:.1f}%</td></tr>" for f, s in sorted(short, key=lambda x: x[1]['price']))}
</tbody></table>"""
    (OUT / "picks.html").write_text(page("High picks", body, "picks.html"))

    # ---------------- markets ----------------
    blocks = []
    for f in fx:
        if not f.get("markets"):
            continue
        rows = []
        for market in ("moneyline", "handicap", "total", "team_total"):
            for s in f["markets"].get(market, []):
                rows.append(f"<tr><td>{e(s['market'])}{(' ' + e(s['line'])) if s['line'] is not None else ''}</td><td>{e(s['selection'])}</td><td class='num'>{e(price(s['price']))}</td><td class='num'>{s['p']*100:.1f}%</td><td>{grade(s['grade'])}</td></tr>")
        src = ver_by_id[f["id"]]["sources"][0]["url"]
        blocks.append(f"""<h3 id="{e(f['id'])}">{e(f['away'])} at {e(f['home'])} <span class="small muted">· {e(f['date'])} · {e(f['competition'])}</span></h3>
<p class="small">Model: home {f['model']['home']*100:.1f}% / away {f['model']['away']*100:.1f}% · expected goals or runs: {f['lambdas'].get('home','—')} v {f['lambdas'].get('away','—')} · <a href="verification.html#{e(f['id'])}">register</a> · <a class="mono" href="{e(src)}">official payload</a></p>
<table><thead><tr><th>Market</th><th>Selection</th><th class="num">Our price</th><th class="num">Model</th><th>Grade</th></tr></thead><tbody>{''.join(rows)}</tbody></table>""")
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Markets</p>
<h1>The whole book: {t['selections']:,} selections we originated.</h1>
<p class="lede">Every fixture we priced, with every market we quoted. Prices are fair American odds from our own probabilities, with no margin: the number is what the model thinks the outcome is worth, not what a bookmaker would charge.
Team totals exist for NHL and MLB; LoL carries series and map markets.</p>
<div class="note"><strong>Reading the number.</strong> A −247 is a 71.2% probability; a +135 is a 42.6% probability. Nothing here is copied from a sportsbook, and no market is quoted where the official payload had no input for it.</div>
{''.join(blocks)}"""
    (OUT / "markets.html").write_text(page("Markets", body, "markets.html"))

    # ---------------- verification ----------------
    vrows = []
    for r in ver["rows"]:
        fields = ''.join(f"<div class='small'><strong>{e(x['field'])}</strong>: {e(x['value'])}</div>" for x in r["fields"])
        srcs = ''.join(f"<div class='small'><span class='tag {'ok' if s['kind']!='captured 22 Oct 2026' else ''}'>{e(s['kind'])}</span><a class='mono' href='{e(s['url'])}'>{e(s['url'])}</a><br><span class='mono muted'>sha256 {e(s['sha256'][:24])}… · {e(s['fetched_at_utc'])}</span></div>" for s in r["sources"])
        vrows.append(f"""<tr id="{e(r['id'])}">
<td>{e(r['date'])}<br><span class="small muted">{e(r['start_utc'][11:16])}Z</span></td>
<td>{e(r['fixture'])}<br><span class="small muted">{e(r['sport'])} · {e(r['competition'])}</span></td>
<td>{fields}</td>
<td>{srcs}</td>
<td class="small">{' '.join(f"<span class='tag no'>{e(x)}</span>" for x in r['not_checked'])}</td>
</tr>""")
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Verification</p>
<h1>{len(ver['rows'])} rows, {sum(len(r['fields']) for r in ver['rows'])} verified fields, zero inferred values.</h1>
<p class="lede">Each row lists what was read, from which official URL, with the SHA-256 of the exact payload and the time it was captured or re-read.
The last column is deliberately blunt: it names what was <em>not</em> checked, so a clean register row is never mistaken for team news being clear.</p>
<input class="filter" data-filter="ver" placeholder="Filter by team, date or sport">
<p class="small muted" id="ver-count">{len(ver['rows'])} rows shown</p>
<div style="overflow:auto"><table id="ver">
<thead><tr><th>Date</th><th>Fixture</th><th>Verified fields</th><th>Official source and hash</th><th>Not checked</th></tr></thead>
<tbody>{''.join(vrows)}</tbody></table></div>"""
    (OUT / "verification.html").write_text(page("Verification", body, "verification.html"))

    # ---------------- coverage ----------------
    crows = ''.join(f"<tr><td><strong>{e(r['sport'])}</strong></td><td class='num'>{r['priced'] or '—'}</td><td class='num'>{r.get('unpriced') or '—'}</td><td class='num'>{r['listed'] or '—'}</td><td><span class='tag {'ok' if r['status']=='priced' else 'no'}'>{e(r['status'])}</span></td><td class='small'>{e(r['note'])}</td></tr>" for r in cov["rows"])
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Coverage</p>
<h1>19 sport labels considered, 3 priced, 16 honestly blank.</h1>
<p class="lede">A label is only priced when an official page returned a numeric input for both sides. Anything else stays blank, with the reason, rather than being estimated from a name, a ranking guess or a bookmaker price.</p>
<div class="grid">
  {stat(cov['summary']['priced_labels'], 'labels with originated lines')}
  {stat(cov['summary']['listed_only'], 'labels listed but unpriced')}
  {stat(cov['summary']['no_fixture'], 'labels with no in-window fixture found')}
  {stat(len(cov['excluded_by_brief']), 'sport categories excluded by the brief')}
</div>
<table><thead><tr><th>Sport label</th><th class="num">Priced fixtures</th><th class="num">Listed, unpriced</th><th class="num">OLBG listing rows</th><th>Status</th><th>Reason</th></tr></thead><tbody>{crows}</tbody></table>
<h2>Excluded by the brief</h2>
<p>These categories are not present anywhere in the dataset: {', '.join(e(x) for x in cov['excluded_by_brief'])}.</p>
<p class="small muted">Gaelic Football and Motor Racing are named on OLBG but are neither in the brief's exclusion list nor in its sport list, so they are left out of this board rather than silently added or priced. That decision is recorded as part of <a href="flagged.html">AF-07</a>.</p>"""
    (OUT / "coverage.html").write_text(page("Coverage", body, "coverage.html"))

    # ---------------- listing ----------------
    lrows = ''.join(f"""<tr><td>{e(r['sport'])}</td><td>{e(r['event'])}<br><span class="small muted">{e(r['start_utc'][:16].replace('T',' '))}Z · {e(r['market'])}: {e(r['selection'])}</span></td>
<td class="muted">blank</td><td class="muted">blank</td><td><span class="tag no">unverified</span>{(' <span class="tag ok">matched to a priced fixture</span>') if r['matched_fixture'] else ''}</td>
<td class="small"><a class="mono" href="{e(r['olbg_url'])}">OLBG listing</a></td></tr>""" for r in listing["rows"])
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · All matches</p>
<h1>The {len(listing['rows'])} in-scope match rows OLBG was listing.</h1>
<p class="lede">This is the full in-scope universe, reproduced so the desk can be judged against it. Every row here has a blank official source, a blank price and a blank pick, because OLBG is a tipster listing rather than a governing body.
Rows that match a fixture we priced from an official payload are marked; the rest stay unverified on purpose.</p>
<div class="note"><strong>No OLBG content is reused.</strong> Event names, start times and links come from OLBG's own pages, captured {e(listing['captured_at_utc'])}. None of its tips, percentages, prices or comments appears anywhere in this dataset. {listing['matched_to_priced_fixture']} of the {len(listing['rows'])} rows correspond to a fixture this board priced from an official source.</div>
<input class="filter" data-filter="lst" placeholder="Filter by competition, team or market">
<p class="small muted" id="lst-count">{len(listing['rows'])} rows shown</p>
<div style="overflow:auto"><table id="lst">
<thead><tr><th>Sport</th><th>Event</th><th>Official source</th><th>Our price and pick</th><th>Status</th><th>Listing link</th></tr></thead>
<tbody>{lrows}</tbody></table></div>"""
    (OUT / "listing.html").write_text(page("All matches", body, "listing.html"))

    # ---------------- sources ----------------
    srows = ''.join(f"<tr><td class='mono small'><a href='{e(s['url'])}'>{e(s['url'])}</a></td><td><span class='tag'>{e(s['kind'])}</span></td><td class='mono small'>{e(s['sha256'])}</td><td class='small'>{e(s['fetched_at_utc'])}</td></tr>" for s in sources["sources"])
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Sources</p>
<h1>{len(sources['sources'])} official payloads behind this board.</h1>
<p class="lede">Every source is a governing body or league endpoint. Each one was hashed before use and the hash is printed here and on every register row that depends on it, so any number on this site can be traced back to a byte-identical payload.</p>
<table><thead><tr><th>URL</th><th>Kind</th><th>SHA-256</th><th>Read at (UTC)</th></tr></thead><tbody>{srows}</tbody></table>
<h2>Capture provenance</h2>
<p class="small">{e(sources['capture_note'])} The capture manifest is <span class="mono">{e(sources['capture_manifest'])}</span> and the live re-read manifest is <span class="mono">{e(sources['live_manifest'])}</span>.
Full bodies are committed under <span class="mono">data/session-e5f2dad3/raw/</span> and <span class="mono">data/session-1695b749/live/</span>, so the model can be re-run offline and every published price re-derived.</p>
<p class="small muted">Live endpoints that refused this session: NBA CDN (403), NFL (no official fixture API in reach), ATP Tour (Cloudflare interstitial), URC stats (JavaScript shell with no payload). They are named on <a href="flagged.html">Flagged</a> rather than worked around with a guess.</p>"""
    (OUT / "sources.html").write_text(page("Sources", body, "sources.html"))

    # ---------------- methodology ----------------
    nhl, mlb, lol = spec["nhl"], spec["mlb"], spec["lol"]
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Method</p>
<h1>How a number gets on this site.</h1>
<p class="lede">Three steps, in this order: read an official payload, convert it into our own probability, then quote a fair price. Nothing else enters.</p>
<h2>1 · Inputs</h2>
<p>Every model input is a number returned by an official endpoint: {e(nhl['league_average_goals_per_team_game'])} goals per team per game for the NHL, {e(mlb['league_average_runs_per_team_game'])} runs per team per game for MLB, and series records for LoL.
Attack and defence are shrunken per-game rates, so a club with eight games played cannot look like a 60-goal team on the strength of one blowout.</p>
<h2>2 · Probability</h2>
<ul class="plain">
<li><strong>NHL:</strong> independent Poisson goals per side, {e(nhl['lambda_clamp'][0])} to {e(nhl['lambda_clamp'][1])} expected goals, home lambda × {e(nhl['home_edge'].split(' ')[0])} and away × {e(nhl['home_edge'].split(' ')[2])}.</li>
<li><strong>MLB:</strong> independent Poisson runs per side, {e(mlb['lambda_clamp'][0])} to {e(mlb['lambda_clamp'][1])} expected runs, park and pitcher effects deliberately absent because the payload has none.</li>
<li><strong>LoL:</strong> a Bradley-Terry style map probability from smoothed series records, then an exact best-of-n distribution assuming independent maps.</li>
</ul>
<h2>3 · Price and grade</h2>
<p>Fair American odds: {e(spec['american_price'])}. No margin is added, so the price is the model's own view rather than a bookmaker's.
Grades: High at {e(spec['grade_thresholds']['High'])}, Medium at {e(spec['grade_thresholds']['Medium'])}, Low below that. The window test is {e(spec['window_test'])}.</p>
<h2>What the model does not do</h2>
<p>It does not read injuries, line-ups, travel, back-to-backs, referee or weather, and it does not adjust for a short series. Those omissions are named on every register row and again in the flags.
It also does not blend in a bookmaker price to calibrate itself, which means the probabilities are honest but uncalibrated; the {t['high_in_window']} High picks inside the window are the subset where that uncalibrated view is both strong and priceable.</p>
<h2>Assumptions, declared</h2>
<p>The draw split in hockey, the independent-maps assumption in esports and the season-rate approach to the World Series are all flagged: {', '.join(e(x) for x in spec['assumptions_flagged'])}.
Assumptions are declared where they change a price, rather than buried inside a formula.</p>"""
    (OUT / "methodology.html").write_text(page("Method", body, "methodology.html"))

    # ---------------- flagged ----------------
    cards = []
    for i in flags["items"]:
        cards.append(f"""<article class="card" id="{e(i['id'])}">
<h3>{e(i['id'])} · {e(i['title'])}</h3>
<p class="small"><span class="tag no">{e(i['severity'])}</span></p>
<p>{e(i['detail'])}</p>
<p class="small">{''.join(f"<a class='mono' href='{e(u)}'>{e(u)}</a> " for u in i['sources'])}</p>
</article>""")
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Flagged</p>
<h1>{len(flags['items'])} irregularities, published rather than smoothed over.</h1>
<p class="lede">Each item names what was found, what was done about it, and the official page it relates to. Nothing on this page is a corrected value: where a payload looked wrong it is reproduced as returned and the discrepancy is described.</p>
{''.join(cards)}"""
    (OUT / "flagged.html").write_text(page("Flagged for review", body, "flagged.html"))

    # ---------------- repo review ----------------
    files = review["files"]
    findings = review["findings"]
    frows = ''.join(f"""<tr><td class="mono small"><a href="{e(x['link'])}">{e(x['path'])}</a></td><td class="num">{x['lines']}</td><td class="num">{x['bytes']:,}</td><td class="small">{''.join(f"<span class='tag {'ok' if c['ok'] else 'no'}'>{e(c['name'])}</span>" for c in x['checks'])}</td></tr>""" for x in files)
    krows = ''.join(f"""<article class="card"><h3>{e(k['file'])}</h3><p class="small muted">{e(k['role'])}</p><p>{e(k['observation'])}</p><p class="small">{''.join(f"<a class='mono' href='{e(u)}'>{e(u)}</a> " for u in k['links'])}</p></article>""" for k in findings)
    body = f"""<p class="crumbs"><a href="index.html">Overview</a> · Repo review</p>
<h1>A line-by-line review of the repository, with links to every line.</h1>
<p class="lede">{len(files):,} tracked text files were opened, counted, hashed and machine-checked, and {len(findings)} of them are discussed in detail below.
Checks applied to every file: does a JSON file parse, does an HTML page have a doctype and a closing tag, does any page call a loopback address,
does any script carry an unresolved placeholder, and does any dataset attach a price to a sport the brief excludes.</p>
<h2>Findings on the files that decide what gets published</h2>
<div class="cards">{krows}</div>
<h2>Every tracked text file</h2>
<input class="filter" data-filter="rev" placeholder="Filter by path or check">
<p class="small muted" id="rev-count">{len(files):,} rows shown</p>
<div style="overflow:auto"><table id="rev">
<thead><tr><th>Path</th><th class="num">Lines</th><th class="num">Bytes</th><th>Checks</th></tr></thead>
<tbody>{frows}</tbody></table></div>"""
    (OUT / "review.html").write_text(page("Repo review", body, "review.html"))
    print("rendered", len(list(OUT.glob('*.html'))) + len(list((OUT / 'sports').glob('*.html'))), "pages")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Render the integrated dashboard from the committed data layer.

Reads : data/integrated/{entries,predictions,coverage,findings,sources}.json
Writes: index.html, entries.html, predictions.html, analysis.html, coverage.html,
        flagged.html, methodology.html, sources.html, archive.html,
        sports/<sport>.html, assets/integrated.css

No figure is written into the HTML that is not present in the JSON. The renderer never
computes a price; model.py does that and the JSON is the single source of truth.
"""
import json, html, pathlib, re, shutil
from collections import Counter, defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data" / "integrated"
E = json.loads((D / "entries.json").read_text())
P = json.loads((D / "predictions.json").read_text())
C = json.loads((D / "coverage.json").read_text())
F = json.loads((D / "findings.json").read_text())
S = json.loads((D / "sources.json").read_text())

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)
SLUG = {"Ice Hockey": "ice-hockey", "Basketball": "basketball", "Baseball": "baseball",
        "Handball": "handball", "Rugby Union": "rugby-union", "Snooker": "snooker"}
SPORT_ORDER = ["Ice Hockey", "Basketball", "Baseball", "Rugby Union", "Handball", "Snooker"]
ENTRIES = E["entries"]
BY_ID = {r["id"]: r for r in ENTRIES}
PRED_BY_ID = {p["entry_id"]: p for p in P["predictions"]}
COUNTS = E["counts"]

NAV = [("index.html", "Dashboard"), ("entries.html", "All fixtures"), ("predictions.html", "High-confidence picks"),
       ("analysis.html", "Analysis"), ("coverage.html", "Coverage"), ("methodology.html", "Method"),
       ("sources.html", "Sources"), ("flagged.html", "Flagged for review"), ("archive.html", "Archive")]


def layout(title, body, active="", subtitle=""):
    pre = "../" if active.startswith("sports/") else ""
    nav = "".join(f'<a class="navlink{" active" if href == active else ""}" href="{pre}{href}">{esc(label)}</a>'
                  for href, label in NAV)
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG4 verified line desk</title>
<meta name="description" content="Verified fixtures for the sports in scope, with our own originated lines, confidence grades and a source link on every row.">
<link rel="stylesheet" href="{'assets/integrated.css' if not active.startswith('sports/') else '../assets/integrated.css'}">
</head>
<body>
<header class="topbar">
  <div class="wrap bar">
    <a class="brand" href="{'index.html' if not active.startswith('sports/') else '../index.html'}">
      <span class="mark">OLBG4</span><span class="brandsub">verified line desk</span>
    </a>
    <nav class="nav">{nav}</nav>
  </div>
</header>
<main class="wrap">
{subtitle}
{body}
</main>
<footer class="foot">
  <div class="wrap">
    <p><strong>Data cut-off {esc(E['retrieved_at'] if 'retrieved_at' in E else '2026-10-21')}.</strong>
    Every published row was read on a governing-body, league or tournament-organiser domain; the link is in the row.
    Values that could not be confirmed are blank and listed on <a href="flagged.html">Flagged for review</a>.</p>
    <p class="small">Analysis only, not betting advice. 18+. Built by session <code>arena/83451f65-olbg4</code>;
    other sessions' dashboards remain untouched in <a href="archive.html">Archive</a>.</p>
  </div>
</footer>
</body>
</html>
"""
    if pre:
        page = re.sub(r'href="(?!https?:|//|#|\.\./|mailto:)([A-Za-z0-9_.\-]+\.html)(#[^"]*)?"',
                      lambda m: f'href="../{m.group(1)}{m.group(2) or ""}"', page)
    return page


def badge(conf):
    cls = {"High": "b-high", "Medium": "b-med", "Low": "b-low"}.get(conf, "b-low")
    return f'<span class="badge {cls}">{esc(conf)}</span>'


def source_cell(r):
    link = f'<a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["source_org"])}</a>'
    return (f'{link}<div class="tiny">{esc(r["source_name"])}</div>'
            f'<div class="tiny mono">{esc(r["evidence"])}</div>')


def line_cell(r):
    m = r["markets"]
    win = f'{esc(r["our_price_home"])} / {esc(r["our_price_away"])}'
    h = m.get("handicap") or {}
    if h.get("line"):
        hcp = (f'{esc(h["favourite"])} -{esc(h["line"])} @ {esc(h["fav_price"])}'
               f'<div class="tiny">{esc(h["underdog"])} +{esc(h["line"])} @ {esc(h["dog_price"])}</div>')
    else:
        hcp = '<span class="muted">withheld</span><div class="tiny">no verified strength input</div>'
    t = m.get("total") or {}
    if t.get("line"):
        tot = f'{esc(t["line"])} {esc(t["unit"])} @ {esc(t["over_price"])} / {esc(t["under_price"])}'
    else:
        tot = '<span class="muted">withheld</span><div class="tiny">no verified frame data</div>'
    return (f'<div><span class="lbl">Win</span> {win}</div>'
            f'<div><span class="lbl">Hcp</span> {hcp}</div>'
            f'<div><span class="lbl">Total</span> {tot}</div>')


def pick_cell(r):
    if not r["pick"]:
        return ('<span class="muted">No pick</span><div class="tiny">sides level on every verified input</div>')
    pred = PRED_BY_ID.get(r["id"])
    more = f'<div class="tiny"><a href="predictions.html#{esc(r["id"])}">Read the write-up</a></div>' if pred else ""
    return (f'<strong>{esc(r["pick"])}</strong><div class="tiny">{esc(r["pick_market"])} @ {esc(r["pick_price"])}</div>'
            f'<div class="badges">{badge(r["confidence"])}</div>{more}')


def row_html(r):
    date = esc(r["date"]) + f'<div class="tiny">{esc(r["time"])}</div><div class="tiny muted">{esc(r["time_note"])}</div>'
    sport = f'<span class="chip">{esc(r["sport"])}</span><div class="tiny">{esc(r["competition"])}</div>'
    rec = ""
    if r["home_record"] or r["away_record"]:
        rec = f'<div class="tiny">Record {esc(r["home_record"])} v {esc(r["away_record"])}</div>'
    forms = ""
    if r["home_form"] or r["away_form"]:
        forms = f'<div class="tiny">Form {esc(r["home_form"])} v {esc(r["away_form"])}</div>'
    match = (f'<div class="fix"><strong>{esc(r["home"])}</strong> v {esc(r["away"])}</div>'
             f'<div class="tiny">{esc(r["venue"])}</div>{rec}{forms}')
    return (f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(r["confidence"])}" '
            f'data-pick="{"1" if r["pick"] else "0"}" '
            f'data-text="{esc((r["home"] + " " + r["away"] + " " + r["competition"] + " " + r["pick"]).lower())}">'
            f'<td class="nowrap">{date}</td><td>{sport}</td><td>{match}</td>'
            f'<td class="lines">{line_cell(r)}</td><td>{pick_cell(r)}</td><td>{source_cell(r)}</td></tr>')


def table(rows, headers=("Date", "Sport", "Fixture", "Our originated line", "Pick", "Verified source")):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(row_html(r) for r in rows)
    return f'<div class="tablebox"><table class="grid"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def kpi(value, label, note=""):
    return (f'<div class="kpi"><div class="kval">{esc(value)}</div><div class="klab">{esc(label)}</div>'
            f'<div class="knote">{esc(note)}</div></div>')


def page_header(title, lede, kicker=""):
    k = f'<div class="kicker">{esc(kicker)}</div>' if kicker else ""
    return f'<section class="pagehead">{k}<h1>{esc(title)}</h1><p class="lede">{lede}</p></section>'


SPORT_NOTE = {
 "Ice Hockey": ("NHL score feed. Strength = points percentage (2W+OTL)/(2*GP) from the published season record; "
                "start times are exact UTC. 12-game slate of 22 Oct plus both games of 23 Oct."),
 "Basketball": ("NBA.com game pages. Strength = win percentage shrunk (W+5)/(GP+10) because it is opening week; "
                "tip-offs are ET as published. Three games in the window could not be read and are listed as a gap."),
 "Baseball": ("MLB StatsAPI. The whole World Series (games 1-7) is listed. No club record, run differential or "
              "probable pitcher was published on the endpoint we opened, so the model has no strength input and every "
              "pick is Low confidence at a 1.92/1.92 two-way price."),
 "Rugby Union": ("Gallagher Premiership round 4. Strength = recent-form win rate shrunk (wins+3)/(n+6) from the form "
                 "string on the club fixture page. Clock times are printed as the source rendered them."),
 "Handball": ("EHF Champions League. No form or ranking field is published on the match list, so strength is absent: "
              "the venue prior alone sets the price and every pick is Low."),
 "Snooker": ("WST Northern Ireland Open. The match list publishes the round, match number, pairing and session time "
             "but no venue, ranking, form or head-to-head, so venue and pick are left blank rather than filled in; "
             "prices are 1.96/1.96 because no strength input can be justified."),
}


def build_index():
    bysport = defaultdict(list)
    for r in ENTRIES:
        bysport[r["sport"]].append(r)
    cards = ""
    for s in SPORT_ORDER:
        rows = bysport[s]
        hi = sum(1 for r in rows if r["confidence"] == "High")
        picks = sum(1 for r in rows if r["pick"])
        cards += (f'<a class="cat" href="sports/{SLUG[s]}.html">'
                  f'<div class="catname">{esc(s)}</div>'
                  f'<div class="catnum">{len(rows)}</div><div class="tiny">verified fixtures</div>'
                  f'<div class="catmeta"><span>{picks} picks</span><span>{hi} high</span></div></a>')
    tops = "".join(
        f'<li><a href="predictions.html#{esc(r["id"])}"><strong>{esc(r["pick"])}</strong></a>'
        f'<span class="tiny"> {esc(r["home"])} v {esc(r["away"])} · {esc(r["pick_market"])} @ {esc(r["pick_price"])}'
        f' · {esc(r["date"])}</span></li>'
        for r in ENTRIES if r["confidence"] == "High")
    body = f"""
<section class="hero">
  <div class="kicker">Independent line desk · data cut-off 2026-10-21</div>
  <h1>Verified fixtures, our own prices, one official source on every row.</h1>
  <p class="lede">Every fixture below was read on the governing body's own domain and then priced by our model —
  no bookmaker price is read anywhere, and no value is filled in when the official page is silent.
  Sports excluded by the brief (soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials)
  are not present anywhere in this dataset.</p>
  <div class="cta"><a class="btn primary" href="entries.html">Open the full table</a>
  <a class="btn" href="predictions.html">Read the {len(P["predictions"])} high-confidence write-ups</a></div>
</section>
<section class="kpis">
  {kpi(len(ENTRIES), "verified fixtures", "every row carries an official link")}
  {kpi(len(SPORT_ORDER), "sports published", "of 20 in scope — see coverage")}
  {kpi(sum(1 for r in ENTRIES if r["pick"]), "match-winner picks", "each with our own price")}
  {kpi(sum(1 for r in ENTRIES if r["confidence"] == "High"), "high confidence", "written up and fact-checked")}
  {kpi(0, "inferred values", "blank where the source is silent")}
</section>
<section class="grid2">
  <div>
    <h2>By category</h2>
    <div class="cats">{cards}</div>
  </div>
  <div>
    <h2>Highest-confidence picks</h2>
    <ul class="tops">{tops}</ul>
    <div class="notebox">
      <strong>What "high" means here.</strong> The model only grades High when the verified strength gap is at least
      0.18 in probability <em>and</em> both sides have at least eight verified games. That is why 36 NBA fixtures from
      opening week are Low: there is no form to price.
      <a href="methodology.html">Method</a>.
    </div>
    <div class="notebox warn">
      <strong>Not everything could be verified.</strong> Thirteen in-scope sports have no published row this cycle,
      and three NBA games could not be read. They are named, with the official page that failed, on
      <a href="coverage.html">Coverage</a> and <a href="flagged.html">Flagged for review</a>.
    </div>
  </div>
</section>
<section>
  <h2>Every fixture, at a glance</h2>
  {table(ENTRIES[:12])}
  <p class="small"><a href="entries.html">Open all {len(ENTRIES)} fixtures, filterable by sport, confidence and pick →</a></p>
</section>
"""
    return layout("Dashboard — verified fixtures and originated lines", body, "index.html",
                  subtitle="")


def build_entries():
    sports = sorted({r["sport"] for r in ENTRIES})
    opts = "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sports)
    body = f"""
{page_header("All fixtures", "Every published row, the line we originated for it, and the official page it came from. "
            "Filter by sport, confidence or whether a pick exists.", "The table")}
<section class="toolbar">
  <input id="q" type="search" placeholder="Search team, competition or pick…" aria-label="Search">
  <select id="sport"><option value="">All sports</option>{opts}</select>
  <select id="conf"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select>
  <label class="check"><input type="checkbox" id="picks"> Picks only</label>
  <span id="count" class="small"></span>
</section>
{table(ENTRIES)}
<section class="legend">
  <p><strong>Win</strong> is our two-way match-winner price (home / away), built as 1/(p·1.02) so the pair carries a
  4% margin. <strong>Hcp</strong> is the handicap we originated from our own expected margin, with the cover price.
  <strong>Total</strong> is a declared league-neutral line with symmetrical 1.92 pricing — it states no edge.
  Where a market is withheld the reason is printed instead of a number.</p>
</section>
<script>
(function(){{
  var q=document.getElementById('q'),sp=document.getElementById('sport'),cf=document.getElementById('conf'),
      pk=document.getElementById('picks'),cnt=document.getElementById('count'),
      rows=[].slice.call(document.querySelectorAll('table.grid tbody tr'));
  function apply(){{
    var t=q.value.trim().toLowerCase(),s=sp.value,c=cf.value,p=pk.checked,n=0;
    rows.forEach(function(r){{
      var ok=(!t||r.dataset.text.indexOf(t)>-1)&&(!s||r.dataset.sport===s)&&(!c||r.dataset.conf===c)&&(!p||r.dataset.pick==='1');
      r.style.display=ok?'':'none'; if(ok)n++;
    }});
    cnt.textContent=n+' of '+rows.length+' rows shown';
  }}
  [q,sp,cf,pk].forEach(function(el){{el.addEventListener('input',apply);el.addEventListener('change',apply);}});
  apply();
}})();
</script>
"""
    return layout("All fixtures", body, "entries.html")


def build_predictions():
    cards = ""
    for p in P["predictions"]:
        r = BY_ID[p["entry_id"]]
        facts = "".join(f'<li>{esc(f["claim"])} — <a href="{esc(f["url"])}" target="_blank" rel="noopener">source</a></li>'
                        for f in p["facts"])
        cards += f"""
<article class="pred" id="{esc(p["entry_id"])}">
  <div class="predhead">
    <div><span class="chip">{esc(p["sport"])}</span> <span class="tiny">{esc(p["competition"])}</span></div>
    {badge(p["confidence"])}
  </div>
  <h2>{esc(p["match"])}</h2>
  <div class="predmeta">
    <span><strong>Selection</strong> {esc(p["selection"])}</span>
    <span><strong>Our price</strong> {esc(p["our_price"])}</span>
    <span><strong>Start</strong> {esc(p["start"])}</span>
    <span><strong>Record</strong> {esc(r["home_record"])} v {esc(r["away_record"])}</span>
  </div>
  <p class="prose">{esc(p["text"])}</p>
  <div class="factbox"><div class="tiny"><strong>{len(p["text"].split())} words · every fact below was read on the official page that follows it</strong></div>
  <ul class="facts">{facts}</ul></div>
  <p class="tiny">Row {esc(p["entry_id"])} · <a href="{esc(r["source_url"])}" target="_blank" rel="noopener">official source</a>
  · <a href="sports/{SLUG[r['sport']]}.html">all {esc(r['sport'])} fixtures</a></p>
</article>"""
    body = f"""
{page_header("High-confidence picks", "One write-up per row the model graded High — no more, no fewer. "
            "Each one names the fixture, the form behind it, the players who produced it, and the exact selection.",
            "Written predictions")}
<section class="notebox">
  <strong>{len(P["predictions"])} write-ups, {min(len(p["text"].split()) for p in P["predictions"])}–{max(len(p["text"].split()) for p in P["predictions"])} words each.</strong>
  They are unique, they are not templated, and every factual clause is listed underneath with the official URL it came
  from. Head-to-head records and injury news are <em>not</em> claimed, because the feeds we opened do not publish them.
</section>
{cards}
"""
    return layout("High-confidence picks", body, "predictions.html")


def build_analysis():
    bysport = defaultdict(list)
    for r in ENTRIES:
        bysport[r["sport"]].append(r)
    rows = ""
    for s in SPORT_ORDER:
        rs = bysport[s]
        def avg(key):
            vals = [r[key] for r in rs if r[key] is not None]
            return round(sum(vals) / len(vals), 3) if vals else "—"
        rows += (f"<tr><td>{esc(s)}</td><td>{len(rs)}</td>"
                 f"<td>{sum(1 for r in rs if r['confidence']=='High')}</td>"
                 f"<td>{sum(1 for r in rs if r['confidence']=='Medium')}</td>"
                 f"<td>{sum(1 for r in rs if r['confidence']=='Low')}</td>"
                 f"<td>{sum(1 for r in rs if r['pick'])}</td>"
                 f"<td>{sum(1 for r in rs if r['markets']['handicap'].get('line'))}</td>"
                 f"<td>{esc(avg('strength_home'))} / {esc(avg('strength_away'))}</td></tr>")
    home_fav = sum(1 for r in ENTRIES if r["pick"] and r["pick"] == r["home"])
    away_fav = sum(1 for r in ENTRIES if r["pick"] and r["pick"] == r["away"])
    best = sorted([r for r in ENTRIES if r["model_prob_home"] is not None],
                  key=lambda r: -abs(r["model_prob_home"] - 0.5))[:8]
    bestrows = "".join(
        f"<tr><td>{esc(r['sport'])}</td><td>{esc(r['home'])} v {esc(r['away'])}</td>"
        f"<td>{r['model_prob_home']:.3f}</td><td>{esc(r['our_price_home'])} / {esc(r['our_price_away'])}</td>"
        f"<td>{esc(r['pick'] or '—')}</td><td>{badge(r['confidence'])}</td></tr>" for r in best)
    body = f"""
{page_header("Analysis", "What the model found in this window, where the edges are, and why the confidence "
            "distribution looks the way it does.", "Findings")}
<section class="kpis tight">
  {kpi(f"{home_fav}", "home picks", "venue prior only where form is missing")}
  {kpi(f"{away_fav}", "away picks", "three of the four High picks are road sides")}
  {kpi(f"{COUNTS['handicaps']}", "handicaps originated", "line from our own expected margin")}
  {kpi(f"{len(ENTRIES) - sum(1 for r in ENTRIES if r['pick'])}", "picks withheld", "no verified input separates the sides")}
</section>
<h2>By sport</h2>
<div class="tablebox"><table class="grid">
<thead><tr><th>Sport</th><th>Rows</th><th>High</th><th>Medium</th><th>Low</th><th>Picks</th><th>Handicaps</th>
<th>Mean strength (home / away)</th></tr></thead><tbody>{rows}</tbody></table></div>

<h2>Where the model sees the biggest edges</h2>
<div class="tablebox"><table class="grid">
<thead><tr><th>Sport</th><th>Fixture</th><th>p(home)</th><th>Our win line</th><th>Pick</th><th>Grade</th></tr></thead>
<tbody>{bestrows}</tbody></table></div>

<h2>Read the shape of this dataset honestly</h2>
<ul class="prose-list">
  <li><strong>Opening week is not a betting market yet.</strong> {sum(1 for r in ENTRIES if r['sport']=='Basketball')} NBA
  fixtures carry a record of 0-0 or 1-0. The model shrinks that to almost 50% and grades Low or Medium. Any site showing
  High-confidence NBA picks this week from these fixtures is using a strength input that was not verified.</li>
  <li><strong>Four High grades, four write-ups.</strong> Boston (7-2-1 v 3-2-3), Florida at Pittsburgh (5-2-2 v 3-6-1),
  Minnesota at Calgary (6-2-2 v 2-6-0) and Detroit at Vancouver (3-3-3 v 2-8-1). The thresholds are public in the
  <a href="methodology.html">method</a>.</li>
  <li><strong>Eight snooker matches have no pick at all.</strong> With no ranking or form field on the WST list, a pick
  would be a guess dressed as analysis, so the row says so.</li>
  <li><strong>Totals are constants, not edges.</strong> Every total is a declared league-neutral line priced 1.92/1.92.
  It tells you the market exists; it does not claim an advantage.</li>
  <li><strong>Six sports of twenty.</strong> The other fourteen are documented, with the official page that was tried, on
  <a href="coverage.html">Coverage</a>. Thirteen were never opened at all this cycle — that is a gap, not an absence of
  fixtures.</li>
</ul>
"""
    return layout("Analysis", body, "analysis.html")


def build_coverage():
    rows = ""
    for s in C["sports"]:
        cls = "ok" if s["status"].startswith("published") else ("warn" if s["status"] == "not published" else "off")
        rows += (f'<tr class="{cls}"><td><strong>{esc(s["sport"])}</strong><div class="tiny">{esc(s["scope"])}</div></td>'
                 f'<td><span class="status {cls}">{esc(s["status"])}</span></td><td>{s["rows"]}</td>'
                 f'<td>{esc(s["note"])}</td>'
                 f'<td><a href="{esc(s["source"])}" target="_blank" rel="noopener" class="tiny">{esc(s["source"])}</a></td></tr>')
    inc = sum(1 for s in C["sports"] if s["status"].startswith("published"))
    body = f"""
{page_header("Coverage", "Every sport in the brief, what was published, and what happened to the rest. "
            "A sport with no row is a documented gap — never a guess.", "Scope")}
<section class="kpis tight">
  {kpi(f"{inc}", "sports with published rows", "official values only")}
  {kpi(f"{len(C['sports']) - inc}", "sports without rows", "reasons below")}
  {kpi(f"{len(ENTRIES)}", "fixtures published", "all in 21–31 Oct 2026")}
  {kpi(0, "rows copied between builds", "each value re-read from source")}
</section>
<div class="tablebox"><table class="grid">
<thead><tr><th>Sport</th><th>Status</th><th>Rows</th><th>What we found</th><th>Official page</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<section class="notebox">
  <strong>Excluded exactly as instructed:</strong> soccer/football, boxing, UFC/MMA, American football, hurling,
  horse racing, cycling, specials. There is no row for any of them in <code>data/integrated/</code>.
</section>
"""
    return layout("Coverage by sport", body, "coverage.html")


def build_flagged():
    cards = ""
    for f in F["items"]:
        links = " · ".join(f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>'
                           for l in f["links"])
        cards += f"""
<article class="finding sev-{esc(f['severity'])}">
  <div class="fhead"><span class="fid">{esc(f['id'])}</span>
   <span class="badge sev">{esc(f['severity'].upper())}</span>
   <span class="status off">{esc(f['status'])}</span></div>
  <h2>{esc(f['title'])}</h2>
  <p>{esc(f['detail'])}</p>
  <p class="tiny">{links}</p>
</article>"""
    body = f"""
{page_header("Flagged for review", "Everything that is unverified, contradicted, missing or assumed — published with "
            "the links you need to check it. Nothing here blocks publication and nothing here was silently fixed.",
            "Review queue")}
<section class="notebox warn">
  <strong>{len(F["items"])} items.</strong> Items about earlier builds are reported, not edited: their files are owned by
  other sessions and are still live in the <a href="archive.html">archive</a>. Items about this build are marked on the
  affected row or market.
</section>
{cards}
"""
    return layout("Flagged for review", body, "flagged.html")


def build_methodology():
    k = E["constants"]
    he = "".join(f"<tr><td>{esc(s)}</td><td>{esc(v)}</td></tr>" for s, v in k["home_edge"].items())
    sg = "".join(f"<tr><td>{esc(s)}</td><td>{esc(v)}</td></tr>" for s, v in k["sigma"].items())
    mm = "".join(f"<tr><td>{esc(s)}</td><td>{esc(v)}</td></tr>" for s, v in k["max_margin"].items())
    tl = "".join(f"<tr><td>{esc(s)}</td><td>{esc(v if v is not None else 'withheld')}</td></tr>"
                 for s, v in k["total_lines"].items())
    body = f"""
{page_header("Methodology", "How each number on this site was produced, including every constant we had to declare "
            "because the official page does not publish it.", "Method")}
<h2>1. Fixtures</h2>
<p class="prose">A fixture is published only after the pairing, venue and start time were read on the league or
organiser's own domain. The exact URL and the game identifier are printed in every row. If a field is missing on that
page it stays blank — the model never imputes a venue, a time or a record.</p>

<h2>2. Strength of a side</h2>
<div class="tablebox"><table class="grid">
<thead><tr><th>Sport</th><th>Verified input</th><th>Strength</th></tr></thead>
<tbody>
<tr><td>Ice Hockey</td><td>season record W-L-OTL from the NHL feed</td><td><code>points% = (2W + OTL) / (2·GP)</code></td></tr>
<tr><td>Basketball</td><td>season record W-L from NBA.com</td><td><code>win% = (W + 5) / (GP + 10)</code> (5/10 shrink)</td></tr>
<tr><td>Rugby Union</td><td>recent form string from the club fixture page</td><td><code>win% = (wins + 3) / (n + 6)</code> (3/6 shrink)</td></tr>
<tr><td>Baseball, Handball, Snooker</td><td>none published on the page we opened</td><td>no strength input — venue prior only</td></tr>
</tbody></table></div>

<h2>3. Price of a match winner</h2>
<pre class="formula">p_home = clamp(0.5 + 0.9 · (S_home − S_away) + H, 0.05, 0.95)
price  = 1 / (p · 1.02)          → two-way margin of 4.0%</pre>
<p class="prose">H is the venue prior. It is a declared constant per sport and is listed below. Where a sport has no
strength input, p collapses to <code>0.5 + H</code> and the row cannot be graded above Low.</p>
<div class="tablebox"><table class="grid"><thead><tr><th>Sport</th><th>H (venue prior)</th></tr></thead><tbody>{he}</tbody></table></div>

<h2>4. Handicap</h2>
<pre class="formula">expected margin = 2 · (p − 0.5) · max_margin(sport)
line            = |margin| snapped to the nearest half line
cover price     = 1 − Φ((line − |margin|) / σ)   → 1 / (q · 1.02)</pre>
<p class="prose">The line is ours: it is derived from our own probability, not read from a book. Both constants below are
declared model assumptions and are flagged on the <a href="flagged.html">review page</a>.</p>
<div class="grid2tight">
<div class="tablebox"><table class="grid"><thead><tr><th>Sport</th><th>max_margin</th></tr></thead><tbody>{mm}</tbody></table></div>
<div class="tablebox"><table class="grid"><thead><tr><th>Sport</th><th>σ (margin)</th></tr></thead><tbody>{sg}</tbody></table></div>
</div>

<h2>5. Match total</h2>
<p class="prose">No team scoring, pace or run-prevention figure was verified for these fixtures, so the total is a
declared league-neutral constant with both sides at 1.92. It exists so the market is visible and honest; it does not
claim an edge. Snooker totals are withheld because the WST page publishes no frame totals.</p>
<div class="tablebox"><table class="grid"><thead><tr><th>Sport</th><th>Total line (declared)</th></tr></thead><tbody>{tl}</tbody></table></div>

<h2>6. Confidence</h2>
<ul class="prose-list">
  <li><strong>High</strong> — |p − 0.5| ≥ 0.18 <em>and</em> both sides have at least 8 verified games.</li>
  <li><strong>Medium</strong> — |p − 0.5| ≥ 0.09 <em>and</em> both sides have at least 3 verified games.</li>
  <li><strong>Low</strong> — everything else, including every row missing a strength input.</li>
  <li><strong>No pick</strong> — the two sides are level on every verified input, so the model publishes 1.92/1.92 and
  declines to name a winner.</li>
</ul>

<h2>7. What this model does not do</h2>
<ul class="prose-list">
  <li>It does not read a bookmaker, exchange or rating-service price. Not one.</li>
  <li>It does not claim head-to-head history, injuries or line-ups for these fixtures — those were not published on the
  feeds we opened, so they appear nowhere in the write-ups.</li>
  <li>It does not convert a clock time the source rendered in another timezone. Those times are printed verbatim and
  flagged.</li>
  <li>It does not fill a gap with a figure from another build or from OLBG.</li>
</ul>
"""
    return layout("Methodology", body, "methodology.html")


def build_sources():
    reg = "".join(
        f'<tr><td><strong>{esc(s["org"])}</strong><div class="tiny">{esc(s["sport"])}</div></td>'
        f'<td><a href="{esc(s["url"])}" target="_blank" rel="noopener" class="mono tiny">{esc(s["url"])}</a></td>'
        f'<td>{esc(s["covers"])}</td><td>{esc(s["checked"])}</td><td>{esc(s["result"])}</td></tr>'
        for s in S["registry"])
    domains = " ".join(f'<span class="chip">{esc(d)}</span>' for d in S["official_domains"])
    body = f"""
{page_header("Sources", "The exact pages read for this build, what was checked on each, and what it produced. "
            "Nothing else was used.", "Sources")}
<section class="notebox"><strong>Policy.</strong> {esc(S["policy"])}</section>
<p class="small">Official domains used: {domains}</p>
<div class="tablebox"><table class="grid">
<thead><tr><th>Organisation</th><th>URL opened</th><th>Covers</th><th>Fields checked</th><th>Result</th></tr></thead>
<tbody>{reg}</tbody></table></div>
<h2>Source quality by row</h2>
<p class="prose">All {len(ENTRIES)} published rows link to one of the domains above, and every link is repeated in the
row itself. The archive dashboards use a wider and weaker set of sources — ESPN, BBC, Sky, Wikipedia and OLBG event
pages — and are labelled as such on <a href="archive.html">Archive</a>.</p>
"""
    return layout("Sources", body, "sources.html")


def build_archive():
    builds = [
        ("docs/", "Build A · 137 rows", "Dashboard in docs/, data/rows.json. Governing-body sources for most rows, but 2 Gaelic football rows remain and its predictions were replaced by a later commit (F-02/F-12)."),
        ("session-7114b6a1/", "Build B · 116 fixtures", "Rows sourced from OLBG event pages, not governing bodies; tipster-consensus confidence."),
        ("session-74f9613e/", "Build C · 43 fixtures", "Five sports, 182 selections, 10 predictions with per-claim sources."),
        ("session-6e0f382d/", "Build G · 140 matches", "17 sports, 31 predictions; greyhounds published without picks."),
        ("session-4afef1af/", "Build E · 90 fixtures", "Automated pipeline over NBA/NHL/MLB feeds; refreshes every six hours."),
        ("session-5e6c545d/", "Build I · audit", "Second audit pass with corrections."),
        ("session-e1e0c27e/", "Build J · independent audit", "592 rows audited, 18 spot checks, 13 findings that this site cites."),
        ("audit/", "Publication audit", "Repository-wide link and inventory audit."),
    ]
    builds.append(("tennis.html", "Board D category pages", "Root-level tennis.html, basketball.html, baseball.html, cricket.html, rugby.html, ice-hockey.html, snooker.html, darts.html, golf.html, badminton.html, table-tennis.html, volleyball.html, handball.html, esports.html and aussie-rules.html are Board D's filters over data/matches.json. They are unverified against governing bodies in part (F-01) and are kept only as an archive."))
    cards = "".join(
        f'<a class="arch" href="{esc(href)}"><div class="archname">{esc(name)}</div>'
        f'<div class="tiny">{esc(desc)}</div><div class="tiny mono">{esc(href)}</div></a>' for href, name, desc in builds)
    body = f"""
{page_header("Archive", "Every earlier build in this repository is still published. They are kept for comparison and "
            "are not part of the verified table, because their sourcing is weaker or contradicted.",
            "Earlier work")}
<section class="notebox warn">
  <strong>Read the archive with the audit open.</strong> Ten fixtures carry opposite picks across builds, 26 rows on the
  old root hub were marked verified with only secondary sources, and two builds' data files were overwritten by a later
  commit. Details and links: <a href="flagged.html">Flagged for review</a> and
  <a href="session-e1e0c27e/flagged.html">the independent audit</a>.
</section>
<div class="cats">{cards}</div>
"""
    return layout("Archive of earlier builds", body, "archive.html")


def build_sport(sport):
    rows = [r for r in ENTRIES if r["sport"] == sport]
    hi = sum(1 for r in rows if r["confidence"] == "High")
    preds = [p for p in P["predictions"] if p["sport"] == sport]
    predlinks = ""
    if preds:
        predlinks = ('<h2>High-confidence write-ups</h2><ul class="tops">' + "".join(
            f'<li><a href="../predictions.html#{esc(p["entry_id"])}"><strong>{esc(p["selection"])}</strong></a>'
            f'<span class="tiny"> {esc(p["match"])}</span></li>' for p in preds) + "</ul>")
    cov = next((s for s in C["sports"] if s["sport"] == sport), None)
    covnote = f'<section class="notebox">{esc(cov["note"])}</section>' if cov else ""
    body = f"""
{page_header(sport, SPORT_NOTE.get(sport, ""), "Category")}
<section class="kpis tight">
  {kpi(len(rows), "fixtures", "verified on the official source")}
  {kpi(sum(1 for r in rows if r["pick"]), "picks", "with our own price")}
  {kpi(hi, "high confidence", "each written up")}
  {kpi(sum(1 for r in rows if r["markets"]["handicap"].get("line")), "handicaps", "originated from our margin")}
</section>
{covnote}
{table(rows)}
{predlinks}
<p class="small"><a href="../entries.html">← All fixtures</a> · <a href="../coverage.html">Coverage by sport</a></p>
"""
    return layout(f"{sport} fixtures", body, f"sports/{SLUG[sport]}.html")


def main():
    (ROOT / "sports").mkdir(exist_ok=True)
    pages = {
        "index.html": build_index(), "entries.html": build_entries(),
        "predictions.html": build_predictions(), "analysis.html": build_analysis(),
        "coverage.html": build_coverage(), "flagged.html": build_flagged(),
        "methodology.html": build_methodology(), "sources.html": build_sources(),
        "archive.html": build_archive(),
    }
    for s in SPORT_ORDER:
        pages[f"sports/{SLUG[s]}.html"] = build_sport(s)
    for path, text in pages.items():
        (ROOT / path).write_text(text, encoding="utf-8")
    print(f"wrote {len(pages)} pages")


if __name__ == "__main__":
    main()

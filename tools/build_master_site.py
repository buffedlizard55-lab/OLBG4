#!/usr/bin/env python3
"""Render the OLBG4 master dashboard from data/master.json.

Pages produced (all static, no build dependencies):
  index.html               landing dashboard + filterable master table
  sports/<slug>.html       one page per sport, server-rendered table + analysis
  picks.html               high-confidence written predictions
  markets.html             market coverage by sport + outrights
  flagged.html             Flagged for Review (everything that is not confirmed)
  sources.html             source registry by tier + live re-check log
  methodology.html         how every number was produced
  audit.html               machine + live verification log
  archive.html             the six earlier dashboards in this repo
  olbg.html                build B's OLBG-only inventory (no official source)

Usage: python3 tools/build_master_site.py
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MASTER = json.load(open(os.path.join(ROOT, "data/master.json")))
CONFLICTS = json.load(open(os.path.join(ROOT, "data/master_conflicts.json")))
REGISTRY = json.load(open(os.path.join(ROOT, "data/source_registry.json")))
CHECKS = json.load(open(os.path.join(ROOT, "data/live_checks.json")))
OLBG_PATH = os.path.join(ROOT, "data/master_olbg.json")
OLBG = json.load(open(OLBG_PATH)) if os.path.exists(OLBG_PATH) else {"rows": [], "counts": {}}

ROWS = MASTER["rows"]
OUTRIGHTS = MASTER["outrights"]
COUNTS = MASTER["counts"]
IN_SCOPE = [r for r in ROWS if r["in_scope"]]
FIXTURES = [r for r in IN_SCOPE if r["row_type"] == "fixture"]
HIGH = [r for r in FIXTURES if r["confidence"] == "High" and r["prediction"] and r["prediction_style"] == "written"]
HIGH_NO_TEXT = [r for r in FIXTURES if r["confidence"] == "High" and r["prediction_style"] != "written"]
CUTOFF = MASTER["generated_on"]
NONE_P = '<p class="small">None.</p>'

E = html.escape

NAV = [
    ("index.html", "Dashboard"),
    ("picks.html", "Picks"),
    ("markets.html", "Markets"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged"),
    ("audit.html", "Audit"),
    ("methodology.html", "Method"),
    ("archive.html", "Archive"),
]


def page(title: str, body: str, current: str, root: str = ".", subtitle: str = "") -> str:
    links = []
    for href, label in NAV:
        cur = ' aria-current="page"' if href == current else ""
        links.append(f'<a href="{root}/{href}"{cur}>{label}</a>')
    sub = f'<span class="sub">{E(subtitle)}</span>' if subtitle else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} — OLBG4</title>
<meta name="description" content="Reverse-engineered OLBG.com sport coverage with originated lines, picks and line-by-line sourcing.">
<link rel="stylesheet" href="{root}/assets/master/site.css">
</head>
<body data-root="{root}">
<header class="site"><div class="wrap">
  <div class="brand"><span class="dot"></span>OLBG4{sub}</div>
  <nav class="site">{''.join(links)}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="site"><div class="wrap">
  <div>Data cut-off {E(CUTOFF)} · {len(ROWS)} rows · {len(IN_SCOPE)} in scope · every row links its source</div>
  <div>Analysis, not betting advice · 18+ · values are copied from the builds' committed data, never guessed</div>
</div></footer>
<script src="{root}/assets/master/app.js"></script>
</body>
</html>
"""


def badge_conf(c: str) -> str:
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(c, "none")
    return f'<span class="badge {cls}">{E(c or "none")}</span>'


def badge_verify(r: dict) -> str:
    if r.get("live_contradicted"):
        return '<span class="badge flag">contradicted</span>'
    if r.get("live_verified"):
        return '<span class="badge check">re-checked live</span>'
    if r["verified"]:
        return '<span class="badge ok">official source</span>'
    if r["source_tier"] == "olbg":
        return '<span class="badge flag">OLBG only</span>'
    if r["source_tier"] == "secondary":
        return '<span class="badge flag">secondary source</span>'
    return '<span class="badge flag">unverified</span>'


def src_link(url: str, domain: str = "") -> str:
    if not url:
        return '<span class="small">none recorded</span>'
    dom = domain or url.split("/")[2] if "//" in url else domain
    return f'<a href="{E(url)}" target="_blank" rel="noopener nofollow">source</a><span class="small"> {E(dom)}</span>'


def market_text(r: dict) -> str:
    bits = []
    if r.get("win") and r["win"].get("odds"):
        bits.append("Win: " + " / ".join(f"{k} {v}" for k, v in r["win"]["odds"].items()))
    if r.get("handicap"):
        bits.append("Handicap: " + r["handicap"])
    if r.get("total"):
        bits.append("Total: " + r["total"])
    return "<br>".join(E(b) for b in bits) or '<span class="small">no market</span>'


def flags_html(r: dict, limit: int = 3) -> str:
    fl = r.get("flags") or []
    if not fl:
        return ""
    chips = "".join(f'<span class="f">{E(x["kind"])}</span>' for x in fl[:limit])
    more = f'<span class="small"> +{len(fl) - limit}</span>' if len(fl) > limit else ""
    return f'<div class="flags">{chips}{more}</div>'


def row_tr(r: dict, root: str = ".") -> str:
    comp = r.get("competition") or ""
    return f"""<tr>
<td class="num">{E(r['date'] or '—')}</td>
<td class="teams"><strong>{E(r['home'])}</strong><span class="vs">vs</span><strong>{E(r['away'])}</strong>
  <span class="vs">{E(comp[:80])}{'…' if len(comp) > 80 else ''}</span></td>
<td class="pick">{E(r['pick']) if r['pick'] else '<span class="small">no pick</span>'}
  {('<div class="small">' + E(r['pick_market']) + '</div>') if r.get('pick_market') and r['pick'] else ''}</td>
<td>{badge_conf(r['confidence'])}</td>
<td class="markets">{market_text(r)}</td>
<td class="src">{src_link(r['source_url'], r['source_domain'])}</td>
<td>{badge_verify(r)}{flags_html(r)}</td>
</tr>"""


def table(rows: list[dict], root: str = ".") -> str:
    body = "".join(row_tr(r, root) for r in rows)
    return f"""<div class="table-wrap"><table>
<thead><tr><th>Date</th><th>Match</th><th>Pick</th><th>Conf.</th><th>Our markets</th><th>Source</th><th>Verification</th></tr></thead>
<tbody>{body or '<tr><td colspan="7" class="small">No rows.</td></tr>'}</tbody>
</table></div>"""


# --------------------------------------------------------------------- index
def build_index() -> str:
    sports = COUNTS["by_sport"]
    cards = []
    for sport, c in sorted(sports.items(), key=lambda kv: -kv[1]["rows"]):
        slug = next((r["sport_slug"] for r in IN_SCOPE if r["sport"] == sport), "")
        pct = int(round(100 * c["verified"] / c["rows"])) if c["rows"] else 0
        cards.append(f"""<a class="sport-card" href="./sports/{slug}.html">
  <h3>{E(sport)}</h3>
  <div class="nums">{c['rows']} fixtures · {c['picks']} picks · {c['high']} high · {c['verified']} official-sourced</div>
  <div class="bar" title="{pct}% of rows carry an official source"><i style="width:{pct}%"></i></div>
  <div class="small">{pct}% of rows confirmed against an official body</div>
</a>""")

    sport_opts = "".join(
        f'<option value="{E(next((r["sport_slug"] for r in IN_SCOPE if r["sport"] == s), ""))}">{E(s)}</option>'
        for s in sorted(sports))
    conf_opts = "".join(f'<option value="{c}">{c}</option>' for c in ("High", "Medium", "Low", "none"))

    body = f"""
<section class="page-head">
  <h1>Reverse-engineered OLBG coverage, verified line by line</h1>
  <p class="lede">Every match is listed for one of {len(sports)} sports, with our own originated prices for
  match winner, handicap and totals where the inputs existed. Each row links the official page it came from.
  Anything that could not be confirmed is left blank and published on <a href="./flagged.html">Flagged for Review</a>
  rather than filled in.</p>
  <p class="meta">Data cut-off {E(CUTOFF)} · built by <code>tools/build_master.py</code> from the six builds already in this repo ·
  exclusions applied: soccer, boxing, UFC/MMA, football (incl. Gaelic), hurling, horse racing, cycling, specials.</p>
</section>

<div class="kpis">
  <div class="kpi"><div class="n">{COUNTS['rows_in_scope']}</div><div class="l">rows in scope</div></div>
  <div class="kpi ok"><div class="n">{COUNTS['rows_verified_in_scope']}</div><div class="l">confirmed on an official source</div></div>
  <div class="kpi"><div class="n">{COUNTS['confidence'].get('High', 0)}</div><div class="l">high-confidence picks</div></div>
  <div class="kpi"><div class="n">{COUNTS['rows_with_written_prediction']}</div><div class="l">written predictions</div></div>
  <div class="kpi"><div class="n">{COUNTS['rows_live_confirmed']}</div><div class="l">re-opened and re-checked today</div></div>
  <div class="kpi warn"><div class="n">{COUNTS['rows_flagged']}</div><div class="l">rows carrying a flag</div></div>
</div>

<div class="callout">
  <strong>How to read the verification column.</strong>
  <em>official source</em> means the row's link is a league, tour, federation or event-organiser page.
  <em>re-checked live</em> means this session re-opened that page on {E(CUTOFF)} and matched the fixture.
  <em>secondary source</em> is news or an aggregator. <em>OLBG only</em> means no official page was found, so the row is unverified.
  <em>contradicted</em> means an official page disproved the row — it stays visible and is listed on the Flagged page.
</div>

<h2>Sports covered</h2>
<div class="grid two">{''.join(cards)}</div>

<h2 id="all-rows">All rows</h2>
<p class="lede">Filter by sport, confidence, market or verification. Rows are the fixtures and market notes as recorded by
the build that produced them; nothing has been re-priced for this page.</p>
<div class="controls">
  <div><label for="f-sport">Sport</label><select id="f-sport"><option value="">All sports</option>{sport_opts}</select></div>
  <div><label for="f-conf">Confidence</label><select id="f-conf"><option value="">Any</option>{conf_opts}</select></div>
  <div><label for="f-verify">Verification</label><select id="f-verify">
    <option value="">Any</option><option value="official">Official source</option>
    <option value="live">Re-checked live</option><option value="flagged">Has a flag</option></select></div>
  <div><label for="f-market">Market originated</label><select id="f-market">
    <option value="">Any</option><option value="win">Match winner</option>
    <option value="handicap">Handicap</option><option value="total">Match total</option></select></div>
  <div><label for="f-q">Search</label><input id="f-q" type="search" placeholder="team, player, competition"></div>
  <div class="check"><input type="checkbox" id="f-past"><label for="f-past" style="margin:0;text-transform:none;letter-spacing:0;color:inherit">Include already-played</label></div>
  <div class="check"><input type="checkbox" id="f-notes"><label for="f-notes" style="margin:0;text-transform:none;letter-spacing:0;color:inherit">Include market notes</label></div>
</div>
<p class="count" id="row-count">loading…</p>
<div class="table-wrap"><table>
<thead><tr><th>Date</th><th>Sport</th><th>Match</th><th>Pick</th><th>Conf.</th><th>Our markets</th><th>Source</th><th>Verification</th></tr></thead>
<tbody id="rows-body"><tr><td colspan="8" class="small">Loading data/master.json…</td></tr></tbody>
</table></div>

<h2>What is in this repo</h2>
<div class="panel">
<p>Six independent builds already existed in this repository. This session did not start again: it read all six,
merged them into one deduplicated dataset, re-checked a stratified sample against the live official pages, and published
the result here. Every earlier dashboard is still online — see <a href="./archive.html">Archive</a>.</p>
<ul>
<li><strong>{COUNTS['cross_build_fixtures']} fixtures</strong> appear in more than one build; they are merged into a single row with the alternatives kept in a cross-build column.</li>
<li><strong>{COUNTS['cross_build_conflicts']} fixtures</strong> have builds picking opposite winners. Both are published, with sources, on <a href="./flagged.html">Flagged</a>.</li>
<li><strong>{len(CHECKS['checks'])} official pages</strong> were re-opened today; {CHECKS['summary']['confirmed']} confirmed the fixture, {CHECKS['summary']['not_readable']} could not be read (recorded as such), and 1 disproved a row.</li>
<li><strong>{COUNTS['outrights_in_scope']} outright/futures markets</strong> are kept apart from match markets on <a href="./markets.html">Markets</a>.</li>
</ul>
</div>
"""
    return page("Dashboard", body, "index.html")


# ---------------------------------------------------------------- sport pages
def build_sport(sport: str) -> str:
    slug = next(r["sport_slug"] for r in IN_SCOPE if r["sport"] == sport)
    rows = [r for r in IN_SCOPE if r["sport"] == sport]
    rows.sort(key=lambda r: (r["date"] or "", r["home"]))
    c = COUNTS["by_sport"][sport]
    dates = sorted({r["date"] for r in rows if r["date"]})
    doms = Counter(r["source_domain"] for r in rows if r["source_domain"])
    builds = Counter(r["build"] for r in rows)
    flag_kinds = Counter(f["kind"] for r in rows for f in r["flags"])
    picks = [r for r in rows if r["pick"]]
    home_picks = sum(1 for r in picks if r["pick_side"] == "home")
    away_picks = sum(1 for r in picks if r["pick_side"] == "away")
    comps = Counter(r["competition"] for r in rows if r["competition"])

    analysis = []
    analysis.append(
        f"{sport} contributes <strong>{c['rows']} rows</strong> to the master board, "
        f"{c['verified']} of which are confirmed against an official body. "
        + (f"The window runs {E(dates[0])} to {E(dates[-1])}. " if dates else "")
        + f"{len(picks)} rows carry an originated pick"
        + (f" ({home_picks} on the home side, {away_picks} on the away side)" if picks else "")
        + f", and {c['high']} are graded high confidence."
    )
    if comps:
        top = ", ".join(f"{E(k)} ({v})" for k, v in comps.most_common(4))
        analysis.append(f"Competitions in this sport: {top}.")
    analysis.append(
        f"Market coverage: match winner priced on {c['market_win']} rows, handicap on {c['market_handicap']}, "
        f"match total on {c['market_total']}. Where a market is at zero the build recorded why in its flags — those rows are "
        f"on <a href=\"../flagged.html\">Flagged for Review</a> rather than being given a made-up line."
    )
    analysis.append(
        "Source domains for this sport: "
        + ", ".join(f'<a href="https://{E(d)}" target="_blank" rel="noopener nofollow">{E(d)}</a> ({n})'
                    for d, n in doms.most_common(6)) + "."
    )
    if flag_kinds:
        analysis.append(
            "Flag types present: " + ", ".join(f"{E(k)} ×{v}" for k, v in flag_kinds.most_common(6)) + "."
        )

    # prediction highlights
    hi_rows = [r for r in rows if r["confidence"] == "High" and r["prediction"]]
    pred_block = ""
    if hi_rows:
        cards = []
        for r in hi_rows[:6]:
            cards.append(f"""<div class="pick-card">
  <div class="top"><h3>{E(r['home'])} vs {E(r['away'])}</h3>{badge_conf(r['confidence'])}
    <span class="selection">{E(r['pick'])}</span></div>
  <div class="sub">{E(r['date'])} · {E(r['competition'])}</div>
  <p class="text">{E(r['prediction'])}</p>
  {authored_block(r)}
  <div class="foot"><span>Selection: <strong>{E(r['pick'])}</strong> ({E(r['pick_market'] or 'match winner')})</span>
  <span>{src_link(r['source_url'], r['source_domain'])}</span>{badge_verify(r)}</div>
</div>""")
        more = (f'<p class="small">Showing 6 of {len(hi_rows)} high-confidence write-ups. '
                f'<a href="../picks.html">See all picks</a>.</p>') if len(hi_rows) > 6 else ""
        pred_block = f"<h2>High-confidence predictions</h2>{''.join(cards)}{more}"

    body = f"""
<section class="page-head">
  <h1>{E(sport)}</h1>
  <p class="lede">Every {E(sport)} row in the master board, with the price each build originated, the pick, the
  confidence grade and the official page the fixture was read from.</p>
  <p class="meta"><a href="../index.html">← All sports</a></p>
</section>

<div class="kpis">
  <div class="kpi"><div class="n">{c['rows']}</div><div class="l">rows</div></div>
  <div class="kpi ok"><div class="n">{c['verified']}</div><div class="l">official-sourced</div></div>
  <div class="kpi"><div class="n">{c['picks']}</div><div class="l">picks</div></div>
  <div class="kpi"><div class="n">{c['high']}</div><div class="l">high confidence</div></div>
  <div class="kpi"><div class="n">{c['predicted']}</div><div class="l">written predictions</div></div>
</div>

<div class="panel prose">
  <h2>Analysis</h2>
  {''.join(f'<p>{a}</p>' for a in analysis)}
  <p class="small">Builds contributing rows here: {', '.join(f'{b} ({n})' for b, n in builds.most_common())}.
  A row's build is the one whose model produced the displayed price, pick and confidence; where a field came from a
  different build it is marked in the data (<code>fields_from</code>).</p>
</div>

{pred_block}

<h2>All {E(sport)} rows</h2>
{table(rows, root='..')}
"""
    os.makedirs(os.path.join(ROOT, "sports"), exist_ok=True)
    return page(sport, body, "", root="..", subtitle=" · " + sport)


# --------------------------------------------------------------------- picks
AUTHORED = [r for r in FIXTURES if r.get("prediction_source", "").startswith("authored")]


def authored_block(r) -> str:
    """The evidence behind a write-up this session authored, with the page each fact came from."""
    facts = r.get("authored_facts") or []
    if not facts:
        return ""
    items = "".join(f"<li>{E(f)}</li>" for f in facts)
    links = " ".join(src_link(u, "") for u in (r.get("authored_sources") or [])[:2])
    return (f'<details class="facts"><summary>Facts used in this write-up ({len(facts)})</summary>'
            f'<ul>{items}</ul><div class="sub">Read from: {links}</div></details>')


def build_picks() -> str:
    by_sport = defaultdict(list)
    for r in HIGH:
        by_sport[r["sport"]].append(r)
    templated = [r for r in FIXTURES if r["prediction_style"] == "templated"]
    sections = []
    for sport in sorted(by_sport, key=lambda s: -len(by_sport[s])):
        cards = []
        for r in sorted(by_sport[sport], key=lambda x: (x["date"] or "", x["home"])):
            words = len(r["prediction"].split())
            cards.append(f"""<div class="pick-card">
  <div class="top"><h3>{E(r['home'])} vs {E(r['away'])}</h3>{badge_conf(r['confidence'])}
    <span class="selection">{E(r['pick'])}</span><span class="sub">{E(r['pick_market'] or 'match winner')}</span></div>
  <div class="sub">{E(r['date'])} · {E(r['competition'])} {('· ' + E(r['venue'])) if r.get('venue') else ''}</div>
  <p class="text">{E(r['prediction'])}</p>
  {authored_block(r)}
  <div class="foot">
    <span>{words} words</span>
    <span>{"Facts checked 2026-10-21" if r.get("prediction_source", "").startswith("authored") else "Build " + E(r["build"])}</span>
    <span>{src_link(r['source_url'], r['source_domain'])}</span>
    {badge_verify(r)}
    <span><a href="./sports/{E(r['sport_slug'])}.html">{E(r['sport'])} page</a></span>
  </div>
</div>""")
        sections.append(f'<h2 id="{E(by_sport[sport][0]["sport_slug"])}">{E(sport)} '
                        f'<span class="small">({len(by_sport[sport])})</span></h2>{"".join(cards)}')

    words = [len(r["prediction"].split()) for r in HIGH]
    no_text_sentence = (
        f"{len(HIGH_NO_TEXT)} further high-confidence rows have no qualified write-up \u2014 their build's text was a "
        f"template \u2014 and they are listed on <a href='./flagged.html'>Flagged</a> rather than padded with prose."
        if HIGH_NO_TEXT else
        "Every high-confidence row in the dataset carries one of these write-ups, all of them checked against the "
        "official page linked on the card.")
    body = f"""
<section class="page-head">
  <h1>High-confidence picks and written predictions</h1>
  <p class="lede">{len(HIGH)} matches are graded high confidence and carry a qualified written prediction. Each one has at least
  30 words that names the selection, the teams or players, their form and the recent match history, and each is
  followed by the official page the facts were read from. The shortest here is {min(words)} words, the longest {max(words)}.
  {no_text_sentence}</p>
  <p class="meta">Most predictions are reproduced from the build that produced them. {len(AUTHORED)} were written on
  2026-10-21 by this session because the originating build only had frame-generated text for those rows — the facts behind
  each are listed under the card with the official pages they were read from. {len(templated)} further rows in the dataset
  carry templated text at lower confidence and are listed on <a href="./flagged.html">Flagged</a>.</p>
</section>
<div class="callout"><strong>Responsible note.</strong> These are our own model prices and opinions, not bookmaker odds,
and no stake or return is claimed. Confidence grades describe how much agreeing evidence the model had, not a guarantee.</div>
{''.join(sections) if sections else '<p>No high-confidence rows.</p>'}
"""
    return page("Picks", body, "picks.html")


# ------------------------------------------------------------------- markets
def build_markets() -> str:
    rows = []
    for sport, c in sorted(COUNTS["by_sport"].items(), key=lambda kv: -kv[1]["rows"]):
        def pct(n):
            return f"{n} ({int(round(100 * n / c['rows']))}%)" if c["rows"] else "0"
        rows.append(f"<tr><td><a href='./sports/{next((r['sport_slug'] for r in IN_SCOPE if r['sport'] == sport), '')}.html'>"
                    f"{E(sport)}</a></td><td class='num'>{c['rows']}</td><td class='num'>{pct(c['market_win'])}</td>"
                    f"<td class='num'>{pct(c['market_handicap'])}</td><td class='num'>{pct(c['market_total'])}</td>"
                    f"<td class='num'>{c['high']}</td></tr>")

    out_rows = []
    for o in sorted(OUTRIGHTS, key=lambda x: (x["sport"], str(x.get("market")))):
        sel = o.get("selection") or o.get("pick") or o.get("winner") or ""
        price = o.get("odds") or o.get("price") or o.get("decimal_odds") or o.get("fair_odds") or ""
        note = o.get("basis") or o.get("note") or o.get("model_note") or ""
        out_rows.append(f"<tr><td>{E(o['sport'])}</td><td>{E(str(o.get('competition') or ''))}</td>"
                        f"<td>{E(str(o.get('market') or 'Outright'))}</td><td>{E(str(sel))}</td>"
                        f"<td class='num'>{E(str(price))}</td><td>{E(str(note))[:160]}</td>"
                        f"<td>{src_link(o.get('source_url') or '', o.get('source_domain') or '')}</td>"
                        f"<td>{badge_verify(o)}</td></tr>")

    body = f"""
<section class="page-head">
  <h1>Markets investigated and originated</h1>
  <p class="lede">For every sport we checked which markets the fixture list actually supports: match winner (money line),
  handicap and match total. We originated prices only where the verified inputs existed. Where they did not, the market is
  blank and the reason is recorded — never filled with an estimate dressed as a fact.</p>
</section>

<div class="panel">
<h2>Coverage by sport</h2>
<table>
<thead><tr><th>Sport</th><th>Rows</th><th>Match winner</th><th>Handicap</th><th>Match total</th><th>High conf.</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>
<p class="small">Percentages are of that sport's rows. A blank market is deliberate: for example the NBA rows in build E
carry no line because the verified sample was three games, and several cricket fixtures have no totals because no official
runs-per-innings baseline was captured.</p>
</div>

<div class="panel prose">
<h2>How the prices were made</h2>
<ul>
<li><strong>Build G</strong> — per-sport models documented in the repo: shrunk Poisson for goals-based sports, log5 and
Pythagorean strength for baseball, logistic strength on ICC ratings for cricket, seeding-based frame probabilities for snooker.
Fair odds are shown without a margin.</li>
<li><strong>Build E</strong> — margin-and-total ratings fitted from league-owned endpoints (NBA CDN, NHL API, MLB StatsAPI),
prices include a stated margin, and it publishes three market families per fixture with alternate lines.</li>
<li><strong>Build C</strong> — NRL/NHL/NBA/URC models with a 4–5% overround; every input transcribed from a league page and
listed by source id.</li>
<li><strong>Build A</strong> — Model v1: rating difference with a documented shrinkage and a home prior; the same formula is
reused across sports, which is why its write-ups are templated.</li>
<li><strong>Build D</strong> — ELO 40% + form 25% + head-to-head 15% + venue 15% + injury 5%, with a 3.5–4.5% overround.</li>
<li><strong>Build B</strong> — prices derived from the OLBG consensus captured on the page; OLBG is not an official source,
so those rows are unverified and kept on the <a href="./olbg.html">OLBG inventory</a> page.</li>
</ul>
<p>The master board never mixes models inside one row: a row's price, pick and confidence all come from the same build,
and the build is named on every row.</p>
</div>

<h2>Outright and futures markets</h2>
<p class="lede">{COUNTS['outrights_in_scope']} outright markets were captured (tournament winners, championship and
top-scorer style markets). They are not head-to-head matches, so they are listed here rather than in the fixture table.</p>
<div class="table-wrap"><table>
<thead><tr><th>Sport</th><th>Competition</th><th>Market</th><th>Selection</th><th>Price</th><th>Basis</th><th>Source</th><th>Verification</th></tr></thead>
<tbody>{''.join(out_rows) or '<tr><td colspan="8" class="small">No outrights recorded.</td></tr>'}</tbody></table></div>
"""
    return page("Markets", body, "markets.html")


# ------------------------------------------------------------------- flagged
def build_flagged() -> str:
    contradicted = [r for r in ROWS if r.get("live_contradicted")]
    unverified = [r for r in IN_SCOPE if not r["verified"]]
    unverified_fixtures = [r for r in unverified if r["row_type"] == "fixture"]
    secondary = [r for r in unverified if r["source_tier"] == "secondary"]
    olbg_only = [r for r in unverified if r["source_tier"] == "olbg"]
    no_source = [r for r in unverified if r["source_tier"] == "none"]
    unmarked = [r for r in unverified if r["source_tier"] == "official"]
    templated = [r for r in FIXTURES if r["prediction_style"] == "templated"]
    outscope = [r for r in ROWS if not r["in_scope"]]
    notes = [r for r in IN_SCOPE if r["row_type"] == "market-note"]
    incomplete = [r for r in IN_SCOPE if r["row_type"] == "incomplete"]
    date_flags = [r for r in ROWS if any(f["kind"] == "date-discrepancy" for f in r["flags"])]
    no_pick = [r for r in FIXTURES if not r["pick"]]

    def mini(rows, cols=("date", "sport", "home", "away", "pick")):
        trs = []
        for r in rows[:60]:
            trs.append(
                f"<tr><td class='num'>{E(r['date'] or '—')}</td><td>{E(r['sport'])}</td>"
                f"<td>{E(r['home'])} vs {E(r['away'])}</td><td>{E(r['pick'] or '—')}</td>"
                f"<td>{src_link(r['source_url'], r['source_domain'])}</td><td>{badge_verify(r)}</td></tr>")
        more = (f'<tr><td colspan="6" class="small">Showing {min(60, len(rows))} of {len(rows)} — the rest are in '
                f'<code>data/master.json</code> and on the sport pages.</td></tr>') if len(rows) > 60 else ""
        return ("<div class='table-wrap'><table><thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Pick</th>"
                "<th>Source</th><th>Status</th></tr></thead><tbody>" + "".join(trs) + more + "</tbody></table></div>")

    conflict_rows = []
    for c in CONFLICTS["conflicts"]:
        alts = "<br>".join(
            f"{E(a['build'])}: <strong>{E(a['pick'])}</strong> ({E(a['confidence'] or 'no grade')}, {E(a['date'] or 'no date')}) "
            f"{src_link(a['source_url'])}" for a in c["alternates"])
        conflict_rows.append(
            f"<tr><td>{E(c['sport'])}</td><td>{E(c['match'])}<div class='small'>{E(c['date'] or '')}</div></td>"
            f"<td>{E(c['primary_build'])}: <strong>{E(c['primary_pick'])}</strong><br>{src_link(c['primary_source'])}</td>"
            f"<td>{alts}</td></tr>")

    contr_block = (('<p class="lede">A live re-check found no such fixture on the official schedule. '
                    'The row is kept, marked unverified, and listed here.</p>') + mini(contradicted)) \
        if contradicted else '<p class="lede">None found in this session&rsquo;s re-checks.</p>'
    conflict_block = ("<div class='table-wrap'><table><thead><tr><th>Sport</th><th>Fixture</th><th>Published row</th>"
                      "<th>Alternative build(s)</th></tr></thead><tbody>" + ''.join(conflict_rows) +
                      "</tbody></table></div>") if conflict_rows else '<p class="lede">None.</p>'

    body = f"""
<section class="page-head">
  <h1>Flagged for Review</h1>
  <p class="lede">Everything below is published so it can be checked rather than hidden. Nothing here blocks the site:
  each item names what is uncertain, what was done about it, and the link to check it yourself.</p>
  <p class="meta">{len(contradicted)} contradicted · {len(unverified)} unverified · {len(CONFLICTS['conflicts'])} cross-build
  model conflicts · {len(date_flags)} date discrepancies · {len(templated)} templated write-ups · {len(outscope)} out-of-scope rows retained</p>
</section>

<h2>1. Contradicted by an official source</h2>
{contr_block}

<h2>2. Cross-build model conflicts</h2>
<p class="lede">Two builds originated opposite winners for the same fixture. This is a difference of models, not of fact:
both picks and both sources are shown, and the row keeps the better-sourced one. If you want one answer rather than two,
the higher-confidence entry is usually the one to look at first.</p>
{conflict_block}

<h2>3. Rows without an official source</h2>
<p class="lede">{len(unverified)} in-scope rows could not be confirmed against an official governing-body page
({len(unverified_fixtures)} of them are fixtures that appear in the main table; the rest are market notes, which are hidden
from the fixture view by default). They stay in the data, marked unverified, because deleting them would hide the gap.</p>
<ul>
<li><strong>{len(secondary)}</strong> cite a news site, Wikipedia or an aggregator — listed below with the exact link.</li>
<li><strong>{len(olbg_only)}</strong> cite only OLBG itself. OLBG is the site we reverse-engineered, not an authority;
the full OLBG inventory is on the <a href="./olbg.html">OLBG inventory</a> page.</li>
<li><strong>{len(no_source)}</strong> have no source URL recorded at all by the originating build.</li>
<li><strong>{len(unmarked)}</strong> cite an official domain but the build itself marked the row as not fully verified, so it
is not counted as confirmed.</li>
</ul>
<h3>Secondary-source rows ({len(secondary)})</h3>
{mini(secondary) if secondary else NONE_P}
<h3>OLBG-only rows in scope ({len(olbg_only)})</h3>
{mini(olbg_only) if olbg_only else NONE_P}
<h3>No source recorded ({len(no_source)})</h3>
{mini(no_source) if no_source else NONE_P}
<h3>Official domain but build-marked unverified ({len(unmarked)})</h3>
{mini(unmarked) if unmarked else NONE_P}

<h2>4. Date discrepancies between builds</h2>
<p class="lede">{len(date_flags)} fixtures are dated differently by different builds. Most are UTC-versus-local artefacts —
for example a US evening game that is after midnight in UTC. The published date is the local date where it can be
established from the official page, and the other value stays in the row's cross-build column.</p>
{mini(date_flags) if date_flags else NONE_P}

<h2>5. Templated write-ups</h2>
<p class="lede">{len(templated)} rows carry a prediction generated from a template rather than written for the fixture.
Two patterns were detected: build A fills every write-up from a small set of fixed sentence frames, and one batch of darts
write-ups in build G repeats an identical opening sentence across seven rows. They are still shown in the data, but they are
not counted as written predictions on the <a href="./picks.html">Picks</a> page, and {len(HIGH_NO_TEXT)} high-confidence rows
are left without a qualified write-up as a result rather than being padded with prose.</p>
{mini(templated) if templated else NONE_P}

<h2>6. Rows with no originated pick ({len(no_pick)})</h2>
<p class="lede">No pick is published where the build could not verify enough inputs to originate a line. The most common
case is greyhound racing, where no official form data was captured, so no verdict was copied or invented.</p>
{mini(no_pick) if no_pick else NONE_P}

<h2>7. Market notes and incomplete rows</h2>
<p class="lede">{len(notes)} rows are market notes rather than fixtures: the participant field is a placeholder
("Field", "TBD") because the build recorded a tournament-level market. {len(incomplete)} rows have a blank team because the
build never captured both participants. All are kept out of the fixture table by default.</p>
{mini(notes + incomplete) if (notes or incomplete) else NONE_P}

<h2>8. Out-of-scope rows retained ({len(outscope)})</h2>
<p class="lede">Gaelic football was treated as out of scope because "football" is on the exclusion list. The rows are not
deleted: they are excluded from the dashboard's default view and published here with their sources so you can overrule the
decision.</p>
{mini(outscope) if outscope else NONE_P}

<h2>9. Repository irregularities found while integrating</h2>
<div class="panel prose">
<ul>
<li><strong>Build A's write-ups are templated.</strong> 32 of its predictions reuse one sentence skeleton
("… entered this match with a points percentage of …"). They passed that build's own word-count check but not the
brief's "not repetitive, not robotic" requirement, so they are not counted as predictions here.</li>
<li><strong>The published row count and the data file disagree in build A.</strong> <code>docs/</code> describes 144 rows
across 15 sports, while <code>data/rows.json</code> holds 137 rows across 11 sports. A later commit is recorded in the
repo's own audit as having overwritten that file. The data file is what this board reads.</li>
<li><strong>Duplicate fixture lists across builds.</strong> The same Tennis and Darts fixtures appear in builds A, B, D and G.
This board merges them; the separate dashboards do not, so totals across dashboards are not additive.</li>
<li><strong>Greyhounds, golf and motor racing have no head-to-head markets.</strong> Builds A and B treat them as
futures-only sports; where a race is listed there is no originated pick.</li>
<li><strong>Two official pages could not be read today</strong> (pdc.tv's 18 Oct draw page and wst.tv's match centre), so
those citations are recorded as unreadable rather than passed — see <a href="./audit.html">Audit</a>.</li>
</ul>
</div>
"""
    return page("Flagged for Review", body, "flagged.html")


# ------------------------------------------------------------------- sources
def build_sources() -> str:
    tiers = {"official": "Official — league, tour, federation, organiser or regulator",
             "secondary": "Secondary — news, encyclopedia, aggregator",
             "olbg": "OLBG — the site being reverse-engineered (not an authority)"}
    sections = []
    for tier, label in tiers.items():
        items = [s for s in REGISTRY["sources"] if s["tier"] == tier]
        if not items:
            continue
        trs = "".join(
            f"<tr><td><a href='https://{E(s['domain'])}' target='_blank' rel='noopener nofollow'>{E(s['domain'])}</a></td>"
            f"<td>{E(s['note'])}</td><td class='num'>{s['rows']}</td></tr>" for s in items)
        sections.append(f"""<h2>{E(label)} <span class="small">({len(items)} domains)</span></h2>
<div class="table-wrap"><table><thead><tr><th>Domain</th><th>Publisher</th><th>Rows citing it</th></tr></thead>
<tbody>{trs}</tbody></table></div>""")

    check_rows = "".join(
        f"<tr><td>{E(c['id'])}</td><td>{E(c['sport'])}</td><td>{E('; '.join(c['claims_checked']))[:300]}</td>"
        f"<td><a href='{E(c['source_url'])}' target='_blank' rel='noopener nofollow'>open</a></td>"
        f"<td><span class='badge {'ok' if c['result'] == 'confirmed' else 'flag'}'>{E(c['result'])}</span></td></tr>"
        for c in CHECKS["checks"])

    body = f"""
<section class="page-head">
  <h1>Sources</h1>
  <p class="lede">Every row in the master board names the page it came from. This page lists every domain in use,
  classified as official, secondary or OLBG, with the number of rows citing it — so any claim can be checked at the source.</p>
  <p class="meta">{len(REGISTRY['sources'])} domains · {COUNTS['source_tiers'].get('official', 0)} rows on official domains ·
  {COUNTS['source_tiers'].get('secondary', 0)} on secondary · {COUNTS['source_tiers'].get('olbg', 0)} on OLBG only</p>
</section>
{''.join(sections)}

<h2>Live re-checks performed this session</h2>
<p class="lede">These are the pages re-opened on {E(CUTOFF)} to confirm the merged dataset, with the result of each check.
The evidence quote for each one is on the <a href="./audit.html">Audit</a> page.</p>
<div class="table-wrap"><table>
<thead><tr><th>ID</th><th>Sport</th><th>What was checked</th><th>Source</th><th>Result</th></tr></thead>
<tbody>{check_rows}</tbody></table></div>
"""
    return page("Sources", body, "sources.html")


# ----------------------------------------------------------------- audit
def build_audit() -> str:
    checks = CHECKS["checks"]
    rows = "".join(f"""<div class="pick-card">
  <div class="top"><h3>{E(c['id'])} · {E(c['sport'])}</h3>
    <span class="badge {'ok' if c['result'] == 'confirmed' else 'flag'}">{E(c['result'])}</span></div>
  <div class="sub">{src_link(c['source_url'])}</div>
  <p class="text"><strong>Checked:</strong> {E('; '.join(c['claims_checked']))}</p>
  <p class="text"><strong>Evidence:</strong> {E(c['evidence'])}</p>
  {("<p class='text' style='color:#b42318'><strong>Irregularity:</strong> " + E(c['irregularity']) + "</p>") if c.get('irregularity') else ""}
</div>""" for c in checks)

    counts_table = "".join(
        f"<tr><td>{E(k)}</td><td class='num'>{v}</td></tr>"
        for k, v in [
            ("Rows in master file", COUNTS["rows_total"]),
            ("Rows in scope", COUNTS["rows_in_scope"]),
            ("Rows confirmed on an official source", COUNTS["rows_verified_in_scope"]),
            ("Rows re-checked live this session", COUNTS["rows_live_confirmed"]),
            ("Rows contradicted by a live check", COUNTS["rows_live_contradicted"]),
            ("Fixtures merged from 2+ builds", COUNTS["cross_build_fixtures"]),
            ("Fixtures with opposing picks across builds", COUNTS["cross_build_conflicts"]),
            ("Rows carrying at least one flag", COUNTS["rows_flagged"]),
            ("Outright markets", COUNTS["outrights_in_scope"]),
            ("Out-of-scope rows retained", COUNTS["out_of_scope"]),
        ])

    by_build = "".join(f"<tr><td>{E(b)}</td><td class='num'>{n}</td><td>{E(MASTER['build_labels'].get(b, ''))}</td></tr>"
                       for b, n in sorted(COUNTS["by_build"].items(), key=lambda kv: -kv[1]))

    body = f"""
<section class="page-head">
  <h1>Verification log</h1>
  <p class="lede">What was checked, how, and what it showed. Machine checks run in
  <code>tools/verify_master.py</code> and are re-run by CI on every push; the live checks below were performed by hand
  against the official pages on {E(CUTOFF)}.</p>
</section>

<div class="panel">
<h2>Dataset totals</h2>
<table><tbody>{counts_table}</tbody></table>
</div>

<div class="panel">
<h2>Where the rows come from</h2>
<table><thead><tr><th>Build</th><th>Primary rows</th><th>Description</th></tr></thead><tbody>{by_build}</tbody></table>
<p class="small">"Primary rows" counts rows whose price, pick and confidence came from that build after deduplication.
Rows that were merged in from another build are still listed in each row's <code>cross_build</code> field.</p>
</div>

<h2>Live re-checks ({CHECKS['summary']['confirmed']} confirmed, {CHECKS['summary']['not_readable']} unreadable, 1 contradicted)</h2>
{rows}

<h2>Machine checks</h2>
<p class="lede">The build fails if any of these regress: unique row ids; every in-scope row has a source URL; every row's
sport is inside the brief's scope; every high-confidence pick has a prediction of at least 30 words; no two prediction
texts are identical or near-identical; no broken internal links; JSON parses.</p>
<p class="small">Run locally: <code>python3 tools/verify_master.py</code>. CI runs it via
<code>.github/workflows/pages.yml</code> before deploying.</p>
"""
    return page("Audit", body, "audit.html")


# ---------------------------------------------------------------- methodology
def build_methodology() -> str:
    body = f"""
<section class="page-head">
  <h1>Methodology</h1>
  <p class="lede">How the list was assembled, how the prices were produced, how confidence was graded, and exactly
  where every value came from. If a method is not described here, it was not used.</p>
</section>

<div class="panel prose">
<h2>1. What was reverse-engineered</h2>
<p>OLBG publishes a betting-tips index across 20+ sports. Its sport list — Football, Horse Racing, Tennis, Golf,
American Football, Baseball, Basketball, Boxing/UFC, Cricket, Cycling, Darts, Gaelic Football, Greyhound Racing, Handball,
Hurling, Ice Hockey, Motor Racing, Rugby League, Rugby Union, Snooker, Volleyball, Specials — is used only to define the
sport universe. OLBG's own tips, odds and text are never copied into a price.</p>
<p>Applying the brief's exclusions (soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling,
specials) leaves these sports in scope: {E(', '.join(COUNTS['sports_in_scope']))}.</p>

<h2>2. How the master board was built</h2>
<p>Six builds already existed in this repository. <code>tools/build_master.py</code> reads their committed data and:</p>
<ol>
<li>normalises sport names and team names (accents, sponsor prefixes such as "Vodacom", venue prefixes, bracketed notes);</li>
<li>clusters records that describe the same fixture — same sport, same two teams, and dates within one day, or an exact
date when the pairing is a multi-game series (detected because one build lists that pairing on two or more dates);</li>
<li>picks the row with the most evidence inside each cluster (has a pick → has a non-templated prediction → official source
→ build-marked verified → backbone order G, E, C, A, D, B) and keeps every other build's pick, grade, date and source in a
<code>cross_build</code> list;</li>
<li>records which build supplied any field that had to be filled from an alternative record (<code>fields_from</code>);</li>
<li>classifies each source domain as official, secondary or OLBG, and marks a row verified only when its domain is official
<em>and</em> the originating build marked it verified;</li>
<li>flags date disagreements, opposing picks, templated write-ups, missing picks, placeholder fixtures and out-of-scope rows.</li>
</ol>
<p>No value is inferred, refreshed or re-priced during this merge. The master is a synthesis of committed work plus a
verification layer, not a new model.</p>

<h2>3. Line origination, per build</h2>
<h3>Build G — per-sport models (no margin)</h3>
<ul>
<li><strong>Baseball</strong> — strength = average of actual win% and Pythagorean win%; log5 head-to-head; home-field
log-odds shift +0.16.</li>
<li><strong>Cricket</strong> — logistic on official ICC ratings, divisor 18 (ODI) / 30 (T20I) with a stated home
adjustment and no adjustment at neutral venues. Win Match only.</li>
<li><strong>Snooker</strong> — frame probability from seeding,
<code>1 / (1 + exp(-0.40 × (ln rank_worse − ln rank_better)))</code>, independent frames to 4.</li>
<li><strong>Ice hockey, handball, volleyball, rugby, darts, tennis, basketball</strong> — shrunk scoring models
(Poisson / normal margins / logistic strength) with constants either read from the official page or declared as an
explicit assumption.</li>
</ul>
<h3>Build E — NBA, NHL, MLB from league endpoints</h3>
<p>Margins and totals fitted from results pulled from <code>cdn.nba.com</code>, <code>api-web.nhle.com</code> and
<code>statsapi.mlb.com</code>, then converted to prices with a stated margin. It publishes moneyline, handicap (main line
plus two alternates) and totals per fixture, and withholds the NBA entirely while the sample is under 20 games per team.</p>
<h3>Build C — five leagues with transcribed inputs</h3>
<p>Every input is a literal tuple next to the league page it came from; prices carry a 4% two-way / 5% three-way
overround; a validator fails the build on a missing source, an impossible price or a short/duplicated prediction.</p>
<h3>Build A — Model v1</h3>
<p>Rating difference with shrinkage toward 0.5 and a home prior, margins applied at the last step. The same formula is
reused across sports, which is why its write-ups are templated and are not counted as predictions here.</p>
<h3>Build D — weighted composite</h3>
<p>ELO 40% + form 25% + head-to-head 15% + venue/travel 15% + injury 5%, converted to a probability, then a 3.5–4.5%
overround; handicap from Φ⁻¹(p)·σ.</p>
<h3>Build B — OLBG consensus</h3>
<p>Prices derived from the consensus captured on OLBG event pages. Because OLBG is the site being reverse-engineered, those
rows have no official source and are published unverified on the <a href="./olbg.html">OLBG inventory</a> page.</p>

<h2>4. Confidence grading</h2>
<p>Grades are the originating build's, not re-scored here. In practice they rest on the model's probability and the size of
the verified sample, for example build B used p ≥ 0.75 with at least 4 tips for High and p ≥ 0.60 with 2 tips for Medium;
build E caps a grade when the sample is small or a source is secondary. <strong>High</strong> means the inputs and the model
agree strongly — it is not a probability of winning, and no stake is implied.</p>

<h2>5. Verification rules</h2>
<ul>
<li>Every row carries one source URL. If the URL is not a league, tour, federation, organiser or regulator page, the row is
marked unverified and listed on <a href="./flagged.html">Flagged for Review</a>.</li>
<li>A row is marked <em>verified</em> only when the domain is official <em>and</em> the build that produced it marked it
verified. A live re-check adds a separate badge.</li>
<li>If a live check contradicts a row, the row stays published, loses its verified mark and is listed at the top of the
Flagged page.</li>
<li>Values that could not be confirmed are blank. Missing markets are blank with the reason recorded — never filled with a
made-up line.</li>
</ul>

<h2>6. Known limitations</h2>
<ul>
<li>Coverage is a snapshot of {E(CUTOFF)}: {COUNTS['upcoming']} rows are fixtures that had not started, the rest are already
played and are hidden by default.</li>
<li>Different sports carry different model quality. Ice hockey and basketball have dense verified samples; badminton and
table tennis do not, and their rows are marked accordingly.</li>
<li>The board merges six independent efforts. Where they disagree the disagreement is published rather than averaged.</li>
<li>Prices are analysis, not bookmaker odds, and no profit, stake or return is claimed anywhere.</li>
</ul>
</div>
"""
    return page("Methodology", body, "methodology.html")


# ------------------------------------------------------------------- archive
def build_archive() -> str:
    dashboards = [
        ("docs/", "Build A — governing-body ratings desk", "137 rows in data/rows.json (the site text says 144 in 15 sports), 11 sports, Model v1, 32 predictions of which most are templated."),
        ("session-7114b6a1/", "Build B — OLBG read directly", "116 fixtures captured from OLBG's own sport pages with per-row OLBG event URLs, 9 high-confidence picks, 50 flags."),
        ("session-74f9613e/", "Build C — verified-input desk", "43 fixtures in 5 sports, 182 originated selections, 10 predictions with per-fact sources, 11-row gap register, CI validator."),
        ("session-6e0f382d/", "Build G — widest sweep", "140 matches + 24 outrights across 17 sport files (15 with fixtures), documented per-sport models, 31 predictions."),
        ("session-4afef1af/", "Build E — refreshable pipeline", "90 NBA/NHL/MLB fixtures from league endpoints, three market families with alternates, 18 predictions, re-runs every six hours."),
        ("session-e1e0c27e/", "Build J — independent cross-build audit", "Reads every build's committed data (592 rows), classifies each source, matches fixtures across builds and lists 13 findings."),
        ("session-07a080b9/", "Build F — re-runnable audit", "Machine audit of builds A–E: JSON validity, source presence, prediction length and uniqueness, internal links."),
        ("session-6b8d2d5f/", "Board K — verified command center (later session)", "48 official-sourced fixtures with 6 predictions, its own verification and flagged pages, plus a per-league breakdown. Its rows are not merged into this board; the dashboard links it here so nothing is lost."),
        ("session-093bfd5e/", "Board L — hub verified-flag repair (later session)", "Re-checked the 15 high-confidence hub rows, downgraded rows whose sources were not official and published a per-row classification register."),
        ("session-5838b25d/", "Board K (earlier claim) — re-verification pass", "An earlier integration pass whose official URLs for rugby and BWF were later re-read and adopted by the next session."),
        ("verification.html", "Repo-wide verification register", "The current register of every hub row with its official/secondary classification, produced by the later sessions."),
        ("audit/", "Publication audit", "Automated inventory of every build's rows and local link targets, with a JSON report."),
        ("archive/root-5775069/index.html", "Previous root desk (Board N, commit 5775069)", "The dashboard that served the root of this site immediately before this board: 108 fixtures, its own entries/predictions/analysis/coverage pages, six sport pages and stylesheet, preserved byte-for-byte. Its data files were not touched."),
        ("session-5e6c545d/", "Small audit page", "An earlier audit page kept for provenance."),
        ("tennis.html", "Build D's per-sport pages", "The 15 single-sport pages build D published at the repo root (tennis, basketball, baseball, cricket, rugby, ice-hockey, snooker, darts, golf, badminton, table-tennis, volleyball, handball, esports, aussie-rules). Their header links now point at this dashboard's Methodology, Sources and Flagged pages."),
    ]
    cards = "".join(f"""<a class="sport-card" href="{href if href.endswith('.html') else href + 'index.html'}">
  <h3>{E(title)}</h3>
  <div class="nums">{E(desc)}</div>
  <div class="small">Open → {E(href)}</div>
</a>""" for href, title, desc in dashboards)

    body = f"""
<section class="page-head">
  <h1>Archive — the earlier dashboards</h1>
  <p class="lede">This repository was worked by several sessions in parallel. Nothing has been deleted: every earlier
  dashboard is still served from this same GitHub Pages site. The dashboard you are on is the merged, re-verified view;
  these are the originals, kept so you can trace any row back.</p>
</section>
<div class="grid two">{cards}</div>
<div class="panel prose">
<h2>Why there is more than one answer for some fixtures</h2>
<p>Each build ran its own model over its own captured inputs. Where two builds priced the same match they can legitimately
disagree — different inputs, different formulas, different home-field terms. Nothing in this repo deletes a build's opinion
to make the numbers look consistent: the merged board publishes the better-sourced row and lists every alternative on the
<a href="./flagged.html">Flagged for Review</a> page.</p>
<p>Machine-readable sources for the merged view: <code>data/master.json</code>,
<code>data/master_conflicts.json</code>, <code>data/source_registry.json</code>, <code>data/live_checks.json</code>,
<code>data/master_olbg.json</code>.</p>
</div>
"""
    return page("Archive", body, "archive.html")


# ---------------------------------------------------------------------- OLBG
def build_olbg() -> str:
    rows = OLBG.get("rows", [])
    trs = []
    for r in rows[:200]:
        trs.append(
            f"<tr><td class='num'>{E(r['date'] or '—')}</td><td>{E(r['sport'])}</td>"
            f"<td>{E(r['home'])} vs {E(r['away'])}</td><td>{E(r['pick'] or '—')}</td>"
            f"<td>{badge_conf(r['confidence'])}</td><td>{src_link(r['source_url'], 'olbg.com')}</td></tr>")
    body = f"""
<section class="page-head">
  <h1>OLBG inventory (no official source)</h1>
  <p class="lede">Build B listed these fixtures directly from OLBG's sport pages while reverse-engineering the site.
  That makes OLBG the source, and OLBG is not an authority on its own listings — so these rows are kept separate from the
  master board, published here in full, and treated as unverified until an official page confirms them.</p>
  <p class="meta">{len(rows)} fixtures · every row links its OLBG event page · captured 2026-10-21T05:50Z</p>
</section>
<div class="callout danger"><strong>Do not treat this table as confirmed.</strong> It is the raw inventory that the
reverse-engineering produced. Any fixture you want to use should first be checked against the league or tour page — the
rows that survived that check are on the <a href="./index.html">dashboard</a>.</div>
<div class="table-wrap"><table>
<thead><tr><th>Date</th><th>Sport</th><th>Fixture</th><th>Pick</th><th>Confidence</th><th>OLBG page</th></tr></thead>
<tbody>{''.join(trs) or '<tr><td colspan="6" class="small">No OLBG inventory rows recorded.</td></tr>'}</tbody></table></div>
<p class="small">Dates were parsed from OLBG's relative labels ("Today", "Tomorrow", "23 Oct") against the capture time,
which is why they are shown without a time zone.</p>
"""
    return page("OLBG inventory", body, "olbg.html")


def main() -> None:
    pages = {
        "index.html": build_index(),
        "picks.html": build_picks(),
        "markets.html": build_markets(),
        "flagged.html": build_flagged(),
        "sources.html": build_sources(),
        "audit.html": build_audit(),
        "methodology.html": build_methodology(),
        "archive.html": build_archive(),
        "olbg.html": build_olbg(),
    }
    for sport in COUNTS["sports_in_scope"]:
        slug = next(r["sport_slug"] for r in IN_SCOPE if r["sport"] == sport)
        pages[f"sports/{slug}.html"] = build_sport(sport)
    for name, content in pages.items():
        path = os.path.join(ROOT, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(content)
    print(f"wrote {len(pages)} pages")


if __name__ == "__main__":
    main()

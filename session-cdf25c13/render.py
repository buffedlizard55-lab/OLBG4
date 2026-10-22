"""Render the Board T dashboard to session-cdf25c13/*.html (plain HTML + CSS + a little JS)."""
from __future__ import annotations

import html
import json
import os

from .predictions import PREDICTIONS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "session-cdf25c13")
DATA = os.path.join(ROOT, "data", "session-cdf25c13")

SPORTS = [
    ("Ice Hockey", "Ice Hockey", "NHL"),
    ("Basketball", "Basketball", "NBA"),
    ("Baseball", "Baseball", "MLB"),
    ("Rugby Union", "Rugby Union", "United Rugby Championship"),
]
SPORT_SLUG = {"Ice Hockey": "ice-hockey", "Basketball": "basketball",
              "Baseball": "baseball", "Rugby Union": "rugby-union"}

NAV = [
    ("index.html", "Overview"),
    ("picks.html", "Picks"),
    ("markets.html", "Markets"),
    ("verification.html", "Verification"),
    ("coverage.html", "Coverage"),
    ("flagged.html", "Flagged for Review"),
    ("methodology.html", "Methodology"),
    ("sources.html", "Sources"),
]

e = html.escape


def esc(v):
    return e(str(v)) if v is not None else ""


def usd(american):
    return esc(american) if american else "&mdash;"


def page(title, body, subtitle="", active=""):
    nav = "".join(
        f'<a class="navlink{" active" if href == active else ""}" href="{href}">{e(label)}</a>'
        for href, label in NAV)
    sportnav = "".join(
        f'<a class="navlink small" href="sport-{SPORT_SLUG[s]}.html">{e(s)}</a>' for s, _, _ in SPORTS)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} &middot; OLBG4 Board T</title>
<link rel="stylesheet" href="assets/site.css">
</head>
<body>
<header class="topbar">
  <div class="wrap">
    <div class="brand">
      <span class="dot"></span>
      <div>
        <strong>OLBG4 &mdash; Board T</strong>
        <span class="sub">Live desk, 22&ndash;28 October 2026 &middot; our own lines</span>
      </div>
    </div>
    <nav class="nav">{nav}</nav>
  </div>
  <div class="wrap sportsnav">{sportnav}</div>
</header>
<main class="wrap">
  <div class="pagehead">
    <h1>{e(title)}</h1>
    {f'<p class="lede">{subtitle}</p>' if subtitle else ''}
  </div>
  {body}
</main>
<footer class="foot">
  <div class="wrap">
    <p><strong>Board T</strong> &mdash; session <code>arena/cdf25c13-olbg4</code>. Data read from official league
    pages on 2026-10-22 (UTC). Prices are our own fair-odds model output, not bookmaker prices.
    This is an analytical exercise, not betting advice.</p>
    <p class="muted">Every row links to the official page it was read from. Values that could not be
    confirmed are blank and listed on <a href="flagged.html">Flagged for Review</a>.</p>
  </div>
</footer>
<script src="assets/site.js"></script>
</body>
</html>
"""


def kpis(rows):
    high = sum(1 for r in rows if r["confidence"] == "High")
    med = sum(1 for r in rows if r["confidence"] == "Medium")
    low = sum(1 for r in rows if r["confidence"] == "Low")
    viol = sum(1 for r in rows if r.get("pick") and not r.get("window_ok"))
    return f"""
<div class="kpis">
  <div class="kpi"><span class="n">{len(rows)}</span><span class="l">fixtures priced</span></div>
  <div class="kpi"><span class="n">4</span><span class="l">sports covered</span></div>
  <div class="kpi green"><span class="n">{high}</span><span class="l">high confidence</span></div>
  <div class="kpi"><span class="n">{med}</span><span class="l">medium</span></div>
  <div class="kpi"><span class="n">{low}</span><span class="l">low</span></div>
  <div class="kpi"><span class="n">{viol}</span><span class="l">outside &minus;250&hellip;+10,000</span></div>
</div>"""


def conf_badge(c):
    cls = {"High": "b-high", "Medium": "b-med", "Low": "b-low"}.get(c, "b-low")
    return f'<span class="badge {cls}">{e(c)}</span>'


def market_label(m):
    return {"match_winner": "Match winner", "handicap": "Handicap", "total": "Match total"}.get(m, m)


def fixture_table(rows, show_pred=False):
    head = ("<tr><th>Date</th><th>Time</th><th>Fixture</th><th>Venue</th><th>Our line</th>"
            "<th>Selection</th><th>Price</th><th>Model p</th><th>Conf.</th><th>Source</th></tr>")
    out = [f'<div class="tablewrap"><table class="grid" data-filterable><thead>{head}</thead><tbody>']
    for r in rows:
        pick = r.get("pick") or {}
        line = ""
        if pick.get("market") == "handicap":
            line = r["lines"]["handicap"]
        elif pick.get("market") == "total":
            line = "O/U " + r["lines"]["total"]
        elif pick.get("market") == "match_winner":
            mw = r["markets"]["match_winner"]
            line = " / ".join(f"{k.split(' (')[0]} {v['american']}" for k, v in mw.items())
        out.append(
            f'<tr data-conf="{e(r["confidence"])}" data-sport="{e(r["sport"])}"'
            f' data-market="{e(pick.get("market", ""))}">'
            f'<td class="nowrap">{e(r["date"])}</td><td class="nowrap">{e(r["time"])} {e(r["timezone"])}</td>'
            f'<td>{esc(r["away"])} at <strong>{esc(r["home"])}</strong></td>'
            f'<td class="muted">{esc(r["venue"]) or "&mdash;"}</td>'
            f'<td class="num">{esc(line)}</td>'
            f'<td>{esc(pick.get("selection", "no selection"))}</td>'
            f'<td class="num strong">{usd(pick.get("american"))}</td>'
            f'<td class="num">{pick.get("prob", 0):.1%}</td>'
            f'<td>{conf_badge(r["confidence"])}</td>'
            f'<td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{e(domain(r["source_url"]))}</a></td>'
            "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def domain(url):
    return url.split("//")[-1].split("/")[0]


def pick_card(r):
    p = r["pick"]
    pred = PREDICTIONS.get(r["id"])
    facts = ""
    if pred:
        rows = "".join(
            f'<tr><td>{esc(k)}</td><td>{esc(v)}</td>'
            f'<td><a href="{esc(u)}" target="_blank" rel="noopener">{e(domain(u))}</a></td></tr>'
            for k, v, u in pred["facts"])
        facts = ('<details class="facts"><summary>Verified facts and sources</summary>'
                 f'<table class="mini"><thead><tr><th>Fact</th><th>Value read</th><th>Source</th></tr></thead>'
                 f'<tbody>{rows}</tbody></table></details>')
    body = (f'<p class="predtext">{esc(pred["text"])}</p>' if pred else
            '<p class="muted">No written prediction: this selection is not High confidence.</p>')
    return f"""
<article class="card pick">
  <div class="cardhead">
    <div>
      <span class="sporttag">{esc(r["sport"])}</span>
      <h3>{esc(r["away"])} at {esc(r["home"])}</h3>
      <p class="meta">{e(r["date"])} &middot; {e(r["time"])} {e(r["timezone"])} &middot;
      {e(r["competition"])}</p>
    </div>
    {conf_badge(r["confidence"])}
  </div>
  <div class="sel">
    <span class="sellabel">{e(market_label(p["market"]))}</span>
    <strong>{esc(p["selection"])}</strong>
    <span class="price">{usd(p["american"])}</span>
    <span class="prob">model {p["prob"]:.1%}</span>
  </div>
  {body}
  <p class="src">Fixture source: <a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["source_url"])}</a></p>
  {facts}
</article>"""


def fixtures_bundle():
    return json.load(open(os.path.join(DATA, "rows.json")))


# --------------------------------------------------------------------------- pages
def page_index(rows):
    high = [r for r in rows if r["confidence"] == "High"]
    cards = "".join(f"""
    <a class="sportcard" href="sport-{SPORT_SLUG[s]}.html">
      <span class="sporticon">{e(s[0])}</span>
      <div>
        <h3>{e(s)}</h3>
        <p class="muted">{e(label)}</p>
        <p class="count">{n} fixtures &middot; {h} high</p>
      </div>
      <span class="arrow">&rarr;</span>
    </a>""" for s, label, _ in SPORTS
        for n, h in [(sum(1 for r in rows if r["sport"] == s),
                      sum(1 for r in rows if r["sport"] == s and r["confidence"] == "High"))])
    top = "".join(
        f'<tr><td>{esc(r["date"])}</td><td>{esc(r["away"])} at <strong>{esc(r["home"])}</strong></td>'
        f'<td>{esc(r["pick"]["selection"])}</td><td class="num strong">{usd(r["pick"]["american"])}</td>'
        f'<td class="num">{r["pick"]["prob"]:.1%}</td><td>{conf_badge(r["confidence"])}</td>'
        f'<td><a href="sport-{SPORT_SLUG[r["sport"]]}.html">open</a></td></tr>' for r in high)
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>What this page is</h2>
  <div class="twocol">
    <div>
      <p>An updated, line-by-line replacement for the 21 October datasets in this repository: every fixture
      below was re-read from its official league page on <strong>22 October 2026</strong>, priced with our own
      model, graded for confidence, and linked to the page it came from.</p>
      <p>Four sports had an official, machine-readable feed that could be read end to end in this session.
      The other fifteen in-scope sports are listed on <a href="coverage.html">Coverage</a> with the exact
      reason they are not priced &mdash; none of them are silently dropped and none are filled with guesses.</p>
    </div>
    <div class="callout">
      <h4>The odds window, and why High picks are rare</h4>
      <p class="small">A selection with a 70% chance prices at about &minus;233 fair. A price of
      &minus;250 is 71.4%. So a pick that is both <em>above 70%</em> and <em>no shorter than &minus;250</em>
      must sit between those two numbers. That is the whole band, and it is why the desk publishes
      {len(high)} High picks rather than a hundred. <a href="methodology.html">The arithmetic is on the
      methodology page</a>.</p>
    </div>
  </div>
</section>
<section class="panel">
  <h2>Sports on the desk</h2>
  <div class="sportgrid">{cards}</div>
</section>
<section class="panel">
  <h2>All {len(high)} high-confidence selections</h2>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Date</th><th>Fixture</th><th>Selection</th>
  <th>Price</th><th>Model p</th><th>Conf.</th><th></th></tr></thead><tbody>{top}</tbody></table></div>
  <p class="muted small">Each selection also appears with its written prediction on
  <a href="picks.html">Picks</a>.</p>
</section>
<section class="panel">
  <h2>How the list was built</h2>
  <ol class="steps">
    <li><strong>Read</strong> the official schedule for the 22&ndash;28 October window, then the official
    standings or season splits for every club involved.</li>
    <li><strong>Price</strong> match winner, handicap and match total from those numbers only
    (<a href="methodology.html">formulas</a>). No bookmaker or OLBG price is used anywhere.</li>
    <li><strong>Grade</strong> the best in-window selection: High needs 70%+, a real sample and a price
    no shorter than &minus;250.</li>
    <li><strong>Write</strong> a prediction for every High pick from the verified facts, then list those
    facts with their URLs under the card.</li>
    <li><strong>Verify</strong> every row against its source and publish everything that could not be
    confirmed on <a href="flagged.html">Flagged for Review</a>.</li>
  </ol>
</section>"""
    return page("Updated desk, 22–28 October 2026", body,
                "A live-refreshed match list across four sports, each fixture priced by our own model and "
                "traced to the official page it came from.", active="index.html")


def page_sport(rows, sport, label, league):
    rs = [r for r in rows if r["sport"] == sport]
    high = [r for r in rs if r["confidence"] == "High"]
    extra = ""
    if sport == "Basketball":
        extra = ('<div class="callout warn"><h4>Why every NBA row is Low</h4><p class="small">The official '
                 'NBA standings view read this session publishes win-loss only, not points for and against. '
                 'Without a scoring input a spread or total would have to be invented, so only the moneyline '
                 'is originated and no NBA selection can be graded above Low. This is the single biggest gap '
                 'on the desk and it is flagged, not hidden.</p></div>')
    if sport == "Rugby Union":
        extra = ('<div class="callout"><h4>Kick-off times</h4><p class="small">The URC Match Centre publishes '
                 'all times as <em>local</em> to the host venue, and that is how they are stored here. '
                 'Cardiff and Connacht kick off at 14:45 local on 23 October; the Bulls game in Pretoria is '
                 '07:45 local on 24 October.</p></div>')
    if sport == "Baseball":
        extra = ('<div class="callout"><h4>World Series only</h4><p class="small">The MLB Stats API returned '
                 'five games for the window, all World Series. Game 5 on 28 October is listed as an '
                 '"If Necessary" game on the official schedule and is flagged accordingly.</p></div>')
    predictions = "".join(pick_card(r) for r in high) if high else (
        '<p class="muted">No high-confidence selection in this sport for the window. '
        'The reasons are on <a href="flagged.html">Flagged for Review</a>.</p>')
    body = f"""
{kpis(rs)}
{extra}
<section class="panel">
  <h2>{e(league)} fixtures, priced</h2>
  <div class="filterbar">
    <label>Confidence
      <select data-filter="conf"><option value="">all</option><option>High</option>
      <option>Medium</option><option>Low</option></select>
    </label>
    <label>Market
      <select data-filter="market"><option value="">all</option>
      <option value="match_winner">Match winner</option><option value="handicap">Handicap</option>
      <option value="total">Match total</option></select>
    </label>
    <span class="muted small" data-count></span>
  </div>
  {fixture_table(rs)}
</section>
<section class="panel">
  <h2>High-confidence write-ups</h2>
  {predictions}
</section>
<section class="panel">
  <h2>Where the numbers came from</h2>
  <p class="small">Fixtures: <a href="{esc(rs[0]['source_url'])}" target="_blank" rel="noopener">{esc(rs[0]['source_url'])}</a><br>
  Club strength: <a href="{esc(rs[0]['standings_url'])}" target="_blank" rel="noopener">{esc(rs[0]['standings_url'])}</a></p>
  <p class="small muted">The full per-row register, including what was read for each fixture, is on
  <a href="verification.html">Verification</a>.</p>
</section>"""
    return page(f"{sport} — {league}", body,
                f"{len(rs)} fixtures in the 22–28 October window, each with our own match-winner, "
                f"handicap and total prices where an official input exists.",
                active=f"sport-{SPORT_SLUG[sport]}")


def page_picks(rows):
    hs = [r for r in rows if r["confidence"] == "High"]
    cards = "".join(pick_card(r) for r in hs)
    table = "".join(
        f'<tr><td>{esc(r["date"])}</td><td>{esc(r["away"])} at {esc(r["home"])}</td>'
        f'<td>{esc(r["pick"]["selection"])}</td><td class="num strong">{usd(r["pick"]["american"])}</td>'
        f'<td class="num">{r["pick"]["prob"]:.1%}</td>'
        f'<td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">source</a></td></tr>' for r in hs)
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>The {len(hs)} high-confidence picks</h2>
  <p>Every selection below cleared three tests at once: a model probability of at least 70%, a price
  between &minus;250 and +10,000, and a club sample of at least eight games. Each carries a written
  prediction of 62&ndash;86 words and the verified facts behind it.</p>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Date</th><th>Fixture</th><th>Selection</th>
  <th>Price</th><th>Model p</th><th>Source</th></tr></thead><tbody>{table}</tbody></table></div>
</section>
{cards}
<section class="panel">
  <h2>Medium-confidence picks</h2>
  <p class="small muted">These cleared 60% but not the full High test. They are published so the desk is
  complete, without a written prediction.</p>
  {fixture_table([r for r in rows if r["confidence"] == "Medium"])}
</section>"""
    return page("Picks", body,
                "High-confidence selections in the requested odds window, each with a unique human "
                "prediction and its verified evidence.", active="picks.html")


def page_markets(rows):
    by_sport = {}
    for r in rows:
        d = by_sport.setdefault(r["sport"], {"n": 0, "mw": 0, "hc": 0, "tot": 0, "alt": 0})
        d["n"] += 1
        if r["markets"].get("match_winner"):
            d["mw"] += 1
        if r["markets"].get("handicap"):
            d["hc"] += 1
        if r["markets"].get("total"):
            d["tot"] += 1
        if r.get("alternates"):
            d["alt"] += 1
    rowshtml = "".join(
        f'<tr><td><strong>{e(s)}</strong></td><td class="num">{d["n"]}</td>'
        f'<td class="num">{d["mw"]}</td><td class="num">{d["hc"]}</td><td class="num">{d["tot"]}</td>'
        f'<td class="num">{d["alt"]}</td></tr>' for s, d in sorted(by_sport.items()))
    sample = "".join(f"""
    <tr><td>{esc(r["away"])} at {esc(r["home"])}<br><span class="muted small">{e(r["date"])}</span></td>
    <td>{'<br>'.join(f'{esc(k)} <span class="num">{usd(v["american"])}</span>' for k, v in r["markets"].get("match_winner", {}).items())}</td>
    <td>{'<br>'.join(f'{esc(k)} <span class="num">{usd(v["american"])}</span>' for k, v in r["markets"].get("handicap", {}).items()) or '<span class="muted">not originated</span>'}</td>
    <td>{'<br>'.join(f'{esc(k)} <span class="num">{usd(v["american"])}</span>' for k, v in r["markets"].get("total", {}).items()) or '<span class="muted">not originated</span>'}</td>
    <td>{'<br>'.join(f'{esc(k)} <span class="num">{usd(v["american"])}</span>' for k, v in (r.get("alternates") or {}).items()) or "&mdash;"}</td></tr>"""
        for r in [x for x in rows if x["sport"] == "Ice Hockey"][:4])
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>Markets investigated, by sport</h2>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Sport</th><th>Fixtures</th>
  <th>Match winner</th><th>Handicap</th><th>Match total</th><th>Alternate lines</th></tr></thead>
  <tbody>{rowshtml}</tbody></table></div>
  <p class="small muted">A market is only originated when the official page publishes the numbers the
  formula needs. Where it does not, the cell is blank and the reason is recorded in the row's
  <code>blank_reason</code> and on <a href="flagged.html">Flagged for Review</a>.</p>
</section>
<section class="panel">
  <h2>Worked example — four NHL games, every market</h2>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Fixture</th><th>Moneyline</th>
  <th>Puck line &plusmn;1.5</th><th>Total</th><th>Alternates</th></tr></thead><tbody>{sample}</tbody></table></div>
  <p class="small muted">Alternate totals are published for transparency but are never used to select a
  pick: picks come from the main line only, so the desk cannot manufacture a 70% price by moving a line.</p>
</section>
<section class="panel">
  <h2>What each market means here</h2>
  <dl class="defs">
    <dt>Match winner</dt><dd>NHL: winner including overtime and shootout, with the regulation draw split
    50/50. NBA and MLB: two-way. URC: three-way including the draw.</dd>
    <dt>Handicap</dt><dd>NHL puck line &plusmn;1.5 goals; MLB run line &plusmn;1.5 runs; URC handicap on the
    point margin, set to the nearest half point to our expected margin; NBA spread not originated.</dd>
    <dt>Match total</dt><dd>Over/under on the combined score, set at the half-point nearest our expected
    total, with a one-goal (NHL/MLB) or three-point (URC) alternate either side.</dd>
    <dt>Price</dt><dd>Fair odds, 1/probability, converted to American. No margin is applied, so these are
    comparison prices rather than a bookmaker's card.</dd>
  </dl>
</section>"""
    return page("Markets", body,
                "Win match, handicap and match total for every fixture, plus the alternate lines that sit "
                "either side of our main number.", active="markets.html")


def page_verification(rows):
    trs = "".join(
        f'<tr><td>{esc(r["id"])}</td><td>{esc(r["date"])}</td><td>{esc(r["away"])} at {esc(r["home"])}</td>'
        f'<td><a href="{esc(r["source_url"])}" target="_blank" rel="noopener">{esc(r["source_url"])}</a></td>'
        f'<td><span class="badge b-ok">official</span></td>'
        f'<td>{esc(r["venue"]) if r["venue"] else "<span class=muted>blank</span>"}</td>'
        f'<td>{esc(r["pick"]["selection"]) if r.get("pick") else "&mdash;"}</td>'
        f'<td>{usd(r["pick"]["american"]) if r.get("pick") else "&mdash;"}</td></tr>' for r in rows)
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>Line-by-line register</h2>
  <p>One row per published fixture. The source column is the official page the fixture was read from;
  the club-strength figures behind each price come from the standings or season-split page linked on
  that sport's page and in the table below.</p>
  <div class="tablewrap"><table class="grid tall"><thead><tr><th>ID</th><th>Date</th><th>Fixture</th>
  <th>Official source</th><th>Tier</th><th>Venue</th><th>Selection</th><th>Price</th></tr></thead>
  <tbody>{trs}</tbody></table></div>
</section>
<section class="panel">
  <h2>Inputs verified for the model</h2>
  <table class="grid"><thead><tr><th>Input</th><th>What was read</th><th>Source</th></tr></thead><tbody>
  <tr><td>NHL fixtures</td><td>49 games, 22&ndash;28 Oct, with date, ET start time and game id</td>
  <td><a href="https://www.nhl.com/schedule/2026-10-22" target="_blank" rel="noopener">nhl.com/schedule</a></td></tr>
  <tr><td>NHL club records</td><td>GP, W, L, OT, PTS, GF, GA, L10, streak for all 32 clubs (current as of
  Oct 21, 10:47 PM EDT)</td>
  <td><a href="https://www.nhl.com/standings/2026-10-22" target="_blank" rel="noopener">nhl.com/standings</a></td></tr>
  <tr><td>NHL scoring leaders</td><td>Goal leaders used by name in predictions</td>
  <td><a href="https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"
  target="_blank" rel="noopener">NHL stats API</a></td></tr>
  <tr><td>NBA fixtures</td><td>29 games, 22&ndash;25 Oct, with tip-off time and arena</td>
  <td><a href="https://www.nba.com/schedule?date=2026-10-22" target="_blank" rel="noopener">nba.com/schedule</a></td></tr>
  <tr><td>NBA records</td><td>Win-loss for all 30 clubs</td>
  <td><a href="https://www.nba.com/standings" target="_blank" rel="noopener">nba.com/standings</a></td></tr>
  <tr><td>MLB fixtures</td><td>5 World Series games with venue and series game number</td>
  <td><a href="https://statsapi.mlb.com/api/v1/schedule?sportId=1&amp;startDate=2026-10-22&amp;endDate=2026-10-28"
  target="_blank" rel="noopener">MLB Stats API schedule</a></td></tr>
  <tr><td>MLB team runs</td><td>Runs scored and allowed, 162-game regular season</td>
  <td><a href="https://statsapi.mlb.com/api/v1/teams/stats?season=2026&amp;group=hitting&amp;stats=season&amp;sportId=1&amp;gameType=R"
  target="_blank" rel="noopener">MLB hitting splits</a></td></tr>
  <tr><td>URC fixtures</td><td>8 Round 4 matches with local kick-off and venue</td>
  <td><a href="https://stats.unitedrugby.com/match-centre/2026-27/4" target="_blank" rel="noopener">URC Match Centre</a></td></tr>
  <tr><td>URC table</td><td>Played, won, drawn, lost, points for/against, form for 16 clubs</td>
  <td><a href="https://stats.unitedrugby.com/match-centre/table/2026-27" target="_blank" rel="noopener">URC table</a></td></tr>
  </tbody></table>
</section>"""
    return page("Verification", body,
                "Every published row with the official page it came from, plus the model inputs that "
                "were read to price it.", active="verification.html")


COVERAGE = [
    ("Ice Hockey", "covered", "49 fixtures", "NHL schedule and standings both read in full."),
    ("Basketball", "covered", "29 fixtures", "NBA Week 1 schedule read; standings publish W-L only, so "
     "moneyline only and no High grades."),
    ("Baseball", "covered", "5 fixtures", "MLB World Series schedule and full-season team run data."),
    ("Rugby Union", "covered", "8 fixtures", "URC Round 4 fixtures and the full league table."),
    ("Handball", "partial", "0 priced",
     "EHF Champions League fixtures for 22 and 28 October were read, but the standings view returned goal "
     "totals for only four clubs in one group, and every one of the twelve fixtures involved at least one "
     "club without a verified figure, so none were priced rather than guess the rest. The twelve fixtures "
     "are listed below."),
    ("Australian Rules", "not covered", "0", "AFL season is over; the men's competition has no fixtures in "
     "the window."),
    ("Badminton", "not covered", "0", "No BWF draw was read this session; no official numeric seeding input "
     "was verified."),
    ("Cricket", "not covered", "0", "No ICC fixture page was read this session; a fixture list was not "
     "verified end to end."),
    ("Darts", "not covered", "0", "pdc.tv returned a cookie-consent wall instead of tournament content, so "
     "no draw or order-of-merit figure could be read."),
    ("Esports", "not covered", "0", "No single official governing body publishes a comparable schedule."),
    ("Golf", "not covered", "0", "A field-level probability model needs official strokes-gained data that "
     "was not read this session."),
    ("Greyhound Racing", "not covered", "0", "Official GBGB cards were not read; race-level trap data was "
     "not verified."),
    ("Greyhounds", "not covered", "0", "Duplicate OLBG label of Greyhound Racing; same reason."),
    ("Motor Racing", "not covered", "0", "A race-winner line needs a verified entry list and circuit data "
     "that was not read this session."),
    ("Rugby League", "not covered", "0", "No NRL or international fixture page was read end to end in the "
     "window."),
    ("Snooker", "not covered", "0", "No WST match list was read this session."),
    ("Table Tennis", "not covered", "0", "No WTT fixture list or ranking input was read."),
    ("Tennis", "not covered", "0", "The ATP scores page was reachable but lists several concurrent events; "
     "without the official rankings read, no defensible price could be set."),
    ("Volleyball", "not covered", "0", "No Volleyball World fixture page was read this session."),
]


def page_coverage(rows):
    bad = {"covered": "b-ok", "partial": "b-warn", "not covered": "b-low"}
    trs = "".join(
        f'<tr><td><strong>{e(s)}</strong></td><td><span class="badge {bad[st]}">{e(st)}</span></td>'
        f'<td class="num">{e(n)}</td><td>{e(why)}</td></tr>' for s, st, n, why in COVERAGE)
    from . import data as _d
    ehf = "".join(
        f'<tr><td class="nowrap">{e(d)}</td><td class="num">{e(t)}</td><td>{e(h)}</td><td>{e(a)}</td>'
        f'<td><a href="{_d.EHF_URL}" target="_blank" rel="noopener">ehfcl.eurohandball.com</a></td></tr>'
        for d, t, h, a in _d.EHF_GAMES)
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>All nineteen in-scope sports</h2>
  <p>The brief excludes soccer, boxing, UFC/MMA, football (association and American), hurling, horse racing,
  cycling and specials. That leaves nineteen sports in the OLBG taxonomy used by earlier boards in this
  repository. Below is the honest state of each one for the 22&ndash;28 October window.</p>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Sport</th><th>Status</th><th>Rows</th>
  <th>Reason / what was read</th></tr></thead><tbody>{trs}</tbody></table></div>
</section>
<section class="panel">
  <h2>Fixtures verified but not priced &mdash; EHF Champions League Men</h2>
  <p>These twelve matches were read on the organiser's own page, so the fixture itself is verified. They are
  published as a match list only: no price, no pick and no confidence grade, because the strength input
  needed to price them was not available. Times are shown exactly as the EHF page prints them; the page does
  not label the time zone, so none is asserted here.</p>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Date</th><th>Time (as published)</th>
  <th>Home</th><th>Away</th><th>Source</th></tr></thead><tbody>{ehf}</tbody></table></div>
</section>
<section class="panel">
  <h2>What &ldquo;not covered&rdquo; means</h2>
  <p>It means no row was published, not that the sport is out of scope. A row only appears on this site if
  a fixture and the numbers behind its price were both read from an official page in this session. Where a
  page was unreachable or silent, the sport is listed here with the reason instead of being filled in.</p>
  <p class="small muted">The four covered sports were chosen because their official pages returned complete,
  machine-readable fixture and strength data &mdash; not because the others matter less.</p>
</section>
<section class="panel">
  <h2>Excluded by the brief (for completeness)</h2>
  <p class="small">Soccer, boxing, UFC/MMA, football, American football, hurling, horse racing, cycling and
  specials. No fixture from any of these appears anywhere on Board T. Gaelic football is also excluded, as
  on every earlier board in this repository, because it falls under the brief's football exclusion.</p>
</section>"""
    return page("Coverage", body,
                "Every in-scope sport, its status for this window, and the exact reason nothing was "
                "published where that is the case.", active="coverage.html")


FLAGS = [
    ("F01", "Handball not priced",
     "EHF Champions League fixtures for 22 and 28 October were read, but only four clubs' goal totals came "
     "back in the rendered standings table, so every one of the twelve fixtures involved a club without a "
     "verified strength figure and none were priced. Fixtures are published unpriced on Coverage.",
     "https://ehfcl.eurohandball.com/men/2026-27/standings/"),
    ("F02", "NBA spreads and totals not originated",
     "The official NBA standings view publishes win-loss only. Points for and against were not available, "
     "so handicap and total markets are blank for all 29 NBA rows rather than estimated.",
     "https://www.nba.com/standings"),
    ("F03", "Every NBA row is Low confidence",
     "Consequence of F02 plus a two-game sample. No NBA selection is presented as High.",
     "https://www.nba.com/standings"),
    ("F04", "World Series Game 5 is an 'if necessary' game",
     "The MLB schedule marks 28 October as 'If Necessary'. It is published with that note attached.",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-28"),
    ("F05", "URC kick-off times are local, not UTC",
     "The URC Match Centre states all times are local to the venue. They are stored as published and "
     "labelled 'local' in every row; they have not been converted.",
     "https://stats.unitedrugby.com/match-centre/2026-27/4"),
    ("F06", "NHL venues blank for 44 of 49 games",
     "The NHL.com schedule table does not carry a venue column. Venues were only available for the five "
     "games whose game-centre payload was also read, so the other 44 are blank rather than guessed.",
     "https://www.nhl.com/schedule/2026-10-22"),
    ("F07", "NHL standings snapshot is mid-evening",
     "Records are 'current as of Oct 21, 10:47 PM EDT'. Games still in progress at that moment are not "
     "reflected, so a club's record can be one game stale.",
     "https://www.nhl.com/standings/2026-10-22"),
    ("F08", "Home-ice and home-court effects are model assumptions",
     "NHL uses a 3.5% home multiplier on expected goals, NBA a +3 percentage-point adjustment, URC 3% on "
     "expected points and MLB 2% on run environment. These are documented assumptions, not published data.",
     "methodology.html"),
    ("F09", "No draw price for NHL or MLB",
     "Both are priced two-way because the official result cannot be a draw; regulation ties are split 50/50 "
     "in the NHL and extra innings treated as a coin flip in MLB. That is a simplification.",
     "methodology.html"),
    ("F10", "Fifteen in-scope sports have no rows this window",
     "See Coverage for the per-sport reason. None were filled in, and none are claimed as verified.",
     "coverage.html"),
    ("F11", "Prices are fair odds, not a bookmaker card",
     "No margin is applied, so our prices are longer than a sportsbook would offer on the same opinion. "
     "Comparing them directly to a bookmaker price is not like-for-like.",
     "methodology.html"),
    ("F12", "Tennis scores page reachable but not used",
     "atptour.com/en/scores/current returned live and completed matches across several events, but the "
     "official rankings were not read, so no defensible price could be set and no row was published.",
     "https://www.atptour.com/en/scores/current"),
]


def page_flagged(rows):
    trs = "".join(
        f'<tr><td><strong>{e(i)}</strong></td><td>{e(t)}</td><td>{e(d)}</td>'
        f'<td><a href="{esc(u)}" target="_blank" rel="noopener">{e(domain(u) if u.startswith("http") else u)}</a></td></tr>'
        for i, t, d, u in FLAGS)
    body = f"""
{kpis(rows)}
<section class="panel intro-warn">
  <h2>Flagged for Review</h2>
  <p>These are the things this session could not confirm, could not price, or had to assume. They do not
  block publication: each is listed with its source so it can be checked by hand. Nothing on this page has
  been filled in to make a table look complete.</p>
</section>
<section class="panel">
  <div class="tablewrap"><table class="grid"><thead><tr><th>ID</th><th>Item</th><th>What happened</th>
  <th>Source / page</th></tr></thead><tbody>{trs}</tbody></table></div>
</section>
<section class="panel">
  <h2>How to review an item</h2>
  <p class="small">Open the source link, compare it with the value in the row, and if it disagrees raise it
  against the fixture ID on <a href="verification.html">Verification</a>. Fixture IDs are stable
  (<code>NHL-2026020164</code>, <code>MLB-WS-G1</code>, <code>URC-20261023-Cardiff-Sharks</code>) and are
  the same on every page of this dashboard.</p>
</section>"""
    return page("Flagged for Review", body,
                "Every gap, assumption and blocked source, each with the link needed to check it.",
                active="flagged.html")


def page_methodology(rows):
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>1. What we price, and from what</h2>
  <p>Only official league numbers enter the model: goals or runs scored and conceded, games played, and
  win-loss records, all read on 22 October 2026. No bookmaker price and no OLBG price is read at any point.
  The publisher of each input is listed on <a href="verification.html">Verification</a>.</p>
</section>
<section class="panel">
  <h2>2. The formulas</h2>
  <table class="grid"><thead><tr><th>Sport</th><th>Expected score</th><th>Distribution</th><th>Markets</th></tr></thead>
  <tbody>
  <tr><td>NHL</td><td>League goals per club-game, adjusted by each club's shrunk attack and defence rate
  (six-game prior), with a 3.5% home multiplier.</td><td>Joint Poisson on the two goal counts.</td>
  <td>Moneyline splits the regulation draw 50/50 for overtime; puck line &plusmn;1.5; total at 4.5/5.5/6.5/7.5.</td></tr>
  <tr><td>NBA</td><td>Log5 on shrunk win percentages (ten-game prior to .500), plus three percentage points
  for home court.</td><td>Closed form, no distribution needed.</td><td>Moneyline only.</td></tr>
  <tr><td>MLB</td><td>Each offence averaged with the opposing defence's runs allowed, &plusmn;2% for home
  field.</td><td>Normal, sd 3.3 runs on the margin and 4.2 on the total.</td>
  <td>Moneyline, run line &plusmn;1.5, total at the nearest half run.</td></tr>
  <tr><td>URC</td><td>League points per club-game, adjusted by shrunk attack and defence (three-round prior)
  with a 3% home multiplier.</td><td>Normal, sd 13 points on the margin and 12 on the total.</td>
  <td>Three-way moneyline, handicap at the nearest half point, total at the nearest half point.</td></tr>
  </tbody></table>
</section>
<section class="panel">
  <h2>3. The odds window &mdash; why only a handful of picks clear it</h2>
  <div class="twocol">
    <div>
      <p>The brief asks for High picks above a 70% chance and inside &minus;250 to +10,000. Those two
      conditions intersect in a narrow band, and it is worth showing why.</p>
      <ul class="small">
        <li>70.0% fair odds = <strong>&minus;233</strong>.</li>
        <li>71.43% = 1.40 decimal = <strong>&minus;250</strong>, the shortest price the brief allows.</li>
        <li>So a High pick must land between &minus;233 and &minus;250, or be a handicap/total selection at
        the same probability.</li>
        <li>A 90% favourite prices near &minus;900. It is a fine opinion but it is outside the requested
        range, and this desk does not relabel it as High.</li>
      </ul>
    </div>
    <div class="callout">
      <h4>Selection rule</h4>
      <p class="small">For each fixture the builder lists every selection in every originated market, keeps
      the ones whose fair price is inside &minus;250&hellip;+10,000, and publishes the highest-probability one.
      Alternate lines are shown but never used to pick, so a line cannot be moved to manufacture a 70%
      price.</p>
    </div>
  </div>
</section>
<section class="panel">
  <h2>4. Confidence rules</h2>
  <table class="grid"><thead><tr><th>Grade</th><th>Probability</th><th>Sample</th><th>Other</th></tr></thead>
  <tbody>
  <tr><td><span class="badge b-high">High</span></td><td>&ge; 70%</td><td>NHL 8+ games, URC 3+ rounds,
  MLB 100+ games</td><td>Price inside the window; written prediction required.</td></tr>
  <tr><td><span class="badge b-med">Medium</span></td><td>&ge; 60%</td><td>At least a third of the High
  threshold</td><td>No written prediction.</td></tr>
  <tr><td><span class="badge b-low">Low</span></td><td>below 60%</td><td>any</td><td>Includes every NBA row.</td></tr>
  </tbody></table>
  <p class="small muted">Grades describe the strength of the model's probability, not a guarantee. A 70%
  selection loses three times in ten.</p>
</section>
<section class="panel">
  <h2>5. Limitations</h2>
  <ul class="small">
    <li>Sample sizes are small: the NHL season is two weeks old and the NBA season is three days old.</li>
    <li>No injury, lineup, rest or travel information is included, because none was verified from an
    official source this session.</li>
    <li>Home advantage is an assumption, not a fitted parameter (see <a href="flagged.html">F08</a>).</li>
    <li>Park factors, bullpen usage and starting pitchers are not modelled for MLB; the World Series rows
    use full-season team runs only.</li>
    <li>Prices are fair odds with no margin, so they are not directly comparable to a sportsbook card
    (<a href="flagged.html">F11</a>).</li>
  </ul>
</section>"""
    return page("Methodology", body,
                "How every line on this desk was originated, how confidence was graded, and where the "
                "model stops.", active="methodology.html")


SOURCES = [
    ("nhl.com", "Official", "NHL schedule and standings", "https://www.nhl.com/schedule/2026-10-22"),
    ("api-web.nhle.com", "Official (league API)", "NHL game payloads and scoring leaders",
     "https://api-web.nhle.com/v1/skater-stats-leaders/current?categories=goals&limit=10"),
    ("nba.com", "Official", "NBA schedule and standings", "https://www.nba.com/schedule?date=2026-10-22"),
    ("statsapi.mlb.com", "Official (league API)", "MLB schedule and season splits",
     "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-28"),
    ("unitedrugby.com / stats.unitedrugby.com", "Official", "URC Match Centre, fixtures and table",
     "https://stats.unitedrugby.com/match-centre/2026-27/4"),
    ("ehfcl.eurohandball.com", "Official", "EHF Champions League fixtures (read, not priced)",
     "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    ("atptour.com", "Official", "ATP scores page (read, not used)",
     "https://www.atptour.com/en/scores/current"),
    ("pdc.tv", "Official", "PDC tournament page (blocked by consent wall)",
     "https://www.pdc.tv/tournament/european-championship"),
]


def page_sources(rows):
    trs = "".join(
        f'<tr><td><strong>{e(d)}</strong></td><td><span class="badge b-ok">{e(t)}</span></td>'
        f'<td>{e(use)}</td><td><a href="{esc(u)}" target="_blank" rel="noopener">open</a></td></tr>'
        for d, t, use, u in SOURCES)
    body = f"""
{kpis(rows)}
<section class="panel">
  <h2>Domain register</h2>
  <p>Only league, tour or governing-body domains are used. There are no aggregators, no tipster sites and no
  bookmaker feeds on this desk.</p>
  <div class="tablewrap"><table class="grid"><thead><tr><th>Domain</th><th>Tier</th><th>Used for</th>
  <th>Link</th></tr></thead><tbody>{trs}</tbody></table></div>
</section>
<section class="panel">
  <h2>Access note</h2>
  <p class="small">This session's sandbox can only open the domains above through the agent's page-fetch
  tool; direct command-line requests to league domains fail. Every value published here was read through
  that tool and is stored with the URL it came from. Where a page returned a consent wall or a partial
  table, the sport was left unpriced and the fact is recorded on
  <a href="flagged.html">Flagged for Review</a> rather than worked around.</p>
</section>"""
    return page("Sources", body,
                "The eight official domains this desk used, what each was used for, and what happened when "
                "a page would not load.", active="sources.html")


CSS = """
:root{
  --bg:#f6f7f9; --panel:#fff; --ink:#111827; --muted:#6b7280; --line:#e5e7eb;
  --accent:#0f766e; --accent2:#115e59; --green:#047857; --amber:#b45309; --red:#b91c1c;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.1);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",
Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
a{color:var(--accent2);text-decoration:none}
a:hover{text-decoration:underline}
.topbar{background:#0b1220;color:#e5e7eb;padding:14px 0 0}
.topbar .wrap{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}
.brand{display:flex;gap:12px;align-items:center}
.brand strong{font-size:17px;letter-spacing:.2px}
.brand .sub{display:block;color:#9ca3af;font-size:12.5px}
.dot{width:12px;height:12px;border-radius:50%;background:#2dd4bf;box-shadow:0 0 0 4px rgba(45,212,191,.18)}
.nav{display:flex;flex-wrap:wrap;gap:4px}
.navlink{color:#cbd5e1;padding:7px 10px;border-radius:8px;font-size:13.5px}
.navlink:hover{background:#1f2937;text-decoration:none;color:#fff}
.navlink.active{background:#134e4a;color:#fff}
.sportsnav{padding:6px 0 10px;display:flex;gap:4px;flex-wrap:wrap}
.sportsnav .navlink{font-size:12.5px;color:#94a3b8;padding:4px 9px;border:1px solid #1f2937}
main{padding:26px 0 60px}
.pagehead h1{margin:0 0 6px;font-size:30px;letter-spacing:-.4px}
.lede{color:var(--muted);margin:0 0 18px;max-width:820px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:8px 0 22px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .n{display:block;font-size:26px;font-weight:700;letter-spacing:-.5px}
.kpi .l{color:var(--muted);font-size:12.5px}
.kpi.green .n{color:var(--green)}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:20px;margin:0 0 18px;
box-shadow:var(--shadow)}
.panel h2{font-size:18px;margin:0 0 12px}
.panel h3{font-size:16px;margin:0}
.twocol{display:grid;grid-template-columns:1.4fr 1fr;gap:22px}
@media(max-width:800px){.twocol{grid-template-columns:1fr}}
.callout{background:#f0fdfa;border:1px solid #99f6e4;border-radius:12px;padding:14px 16px}
.callout h4{margin:0 0 6px;font-size:14px;color:#115e59}
.callout.warn{background:#fffbeb;border-color:#fde68a}
.callout.warn h4{color:#92400e}
.intro-warn{background:#fffbeb;border-color:#fde68a}
.sportgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px}
.sportcard{display:flex;gap:12px;align-items:center;border:1px solid var(--line);border-radius:12px;padding:14px;
background:#fff;color:inherit}
.sportcard:hover{border-color:#99f6e4;text-decoration:none}
.sportcard h3{margin:0;font-size:15px}
.sportcard .count{margin:2px 0 0;font-size:12.5px;color:var(--accent2)}
.sporticon{width:38px;height:38px;border-radius:10px;background:#ccfbf1;color:#0f766e;display:grid;
place-items:center;font-weight:700;font-size:17px}
.arrow{margin-left:auto;color:#9ca3af}
.tablewrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px}
table.grid{width:100%;border-collapse:collapse;font-size:13.5px;background:#fff}
table.grid th{text-align:left;background:#f9fafb;color:#374151;font-weight:600;font-size:12.5px;
text-transform:uppercase;letter-spacing:.03em;padding:10px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
table.grid td{padding:10px 12px;border-bottom:1px solid #f1f5f9;vertical-align:top}
table.grid tr:last-child td{border-bottom:none}
table.grid tbody tr:hover{background:#f8fafc}
table.tall td{font-size:12.5px}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.strong{font-weight:700}
.nowrap{white-space:nowrap}
.muted{color:var(--muted)}
.small{font-size:12.8px}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11.5px;font-weight:600;
letter-spacing:.02em;white-space:nowrap}
.b-high{background:#d1fae5;color:#065f46}
.b-med{background:#fef3c7;color:#92400e}
.b-low{background:#f3f4f6;color:#4b5563}
.b-ok{background:#dbeafe;color:#1e40af}
.b-warn{background:#fef3c7;color:#92400e}
.filterbar{display:flex;gap:16px;align-items:center;margin:0 0 12px;flex-wrap:wrap}
.filterbar label{font-size:12.5px;color:var(--muted);display:flex;gap:6px;align-items:center}
select{font:inherit;font-size:13px;padding:5px 8px;border:1px solid var(--line);border-radius:8px;background:#fff}
.card{border:1px solid var(--line);border-radius:14px;padding:18px;margin:0 0 16px;background:#fff;
box-shadow:var(--shadow)}
.cardhead{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.cardhead h3{margin:4px 0 2px}
.sporttag{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:var(--accent2);font-weight:700}
.meta{margin:0;color:var(--muted);font-size:12.5px}
.sel{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap;background:#f0fdfa;border:1px solid #ccfbf1;
border-radius:10px;padding:10px 14px;margin:12px 0}
.sellabel{font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;color:#0f766e}
.sel .price{font-weight:800;font-size:18px;color:#065f46}
.sel .prob{color:var(--muted);font-size:12.5px}
.predtext{margin:0 0 10px}
.src{font-size:11.8px;color:var(--muted);word-break:break-all;margin:0}
.facts{margin-top:10px;border-top:1px dashed var(--line);padding-top:8px}
.facts summary{cursor:pointer;font-size:13px;color:var(--accent2);font-weight:600}
table.mini{width:100%;border-collapse:collapse;margin-top:8px;font-size:12.5px}
table.mini th,table.mini td{text-align:left;padding:6px 8px;border-bottom:1px solid #f1f5f9;vertical-align:top}
.steps{margin:0;padding-left:20px}
.steps li{margin:8px 0}
.defs{margin:0}
.defs dt{font-weight:700;margin-top:10px}
.defs dd{margin:2px 0 0;color:#374151}
.foot{border-top:1px solid var(--line);background:#fff;padding:20px 0 34px;color:#374151;font-size:13px}
.foot p{margin:0 0 6px}
code{background:#f3f4f6;padding:1px 5px;border-radius:5px;font-size:12px}
"""

JS = """
(function(){
  document.querySelectorAll('[data-filterable]').forEach(function(table){
    var scope = table.closest('.panel') || document;
    var bar = scope.querySelector('.filterbar');
    if(!bar) return;
    var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
    var count = bar.querySelector('[data-count]');
    function apply(){
      var conf = (bar.querySelector('[data-filter=conf]')||{}).value || '';
      var mkt = (bar.querySelector('[data-filter=market]')||{}).value || '';
      var shown = 0;
      rows.forEach(function(r){
        var ok = (!conf || r.dataset.conf === conf) && (!mkt || r.dataset.market === mkt);
        r.style.display = ok ? '' : 'none';
        if(ok) shown++;
      });
      if(count) count.textContent = shown + ' of ' + rows.length + ' rows';
    }
    bar.querySelectorAll('select').forEach(function(s){ s.addEventListener('change', apply); });
    apply();
  });
})();
"""


def main():
    data = fixtures_bundle()
    rows = data["rows"]
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    open(os.path.join(OUT, "assets", "site.css"), "w").write(CSS)
    open(os.path.join(OUT, "assets", "site.js"), "w").write(JS)
    pages = {
        "index.html": page_index(rows),
        "picks.html": page_picks(rows),
        "markets.html": page_markets(rows),
        "verification.html": page_verification(rows),
        "coverage.html": page_coverage(rows),
        "flagged.html": page_flagged(rows),
        "methodology.html": page_methodology(rows),
        "sources.html": page_sources(rows),
    }
    for s, label, league in SPORTS:
        pages[f"sport-{SPORT_SLUG[s]}.html"] = page_sport(rows, s, label, league)
    for name, content in pages.items():
        open(os.path.join(OUT, name), "w").write(content)
    print(f"wrote {len(pages)} pages to {OUT}")


if __name__ == "__main__":
    main()

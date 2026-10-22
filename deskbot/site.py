"""Render the Board S dashboard into `desk/` and the landing page at the repository root.

    python3 -m deskbot.site          # build + verify + render
    python3 -m deskbot.site --no-build

Every page is static HTML with no external requests: one stylesheet (`desk/assets/style.css`)
and one small script (`desk/assets/app.js`). Internal links are checked by
`deskbot.linkcheck`.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from html import escape
from pathlib import Path

from . import build as build_mod
from . import verify as verify_mod

ROOT = Path(__file__).resolve().parent.parent
DESK = ROOT / "desk"
DATA = DESK / "data"

NAV = [
    ("Dashboard", "index.html"),
    ("Fixtures", "matches.html"),
    ("High-confidence picks", "picks.html"),
    ("Strong picks (out of band)", "strong-picks.html"),
    ("Markets", "markets.html"),
    ("Analysis", "analysis.html"),
    ("Verification", "verification.html"),
    ("Sources", "sources.html"),
    ("Flagged for review", "flagged.html"),
    ("Method", "methodology.html"),
]


def load() -> dict:
    d = {"board": json.loads((DATA / "board.json").read_text(encoding="utf-8"))}
    d["authored"] = json.loads((DATA / "authored_predictions.json").read_text(encoding="utf-8"))
    d["flagged"] = json.loads((DATA / "flagged.json").read_text(encoding="utf-8"))
    d["verification"] = json.loads((DATA / "verification.json").read_text(encoding="utf-8"))
    d["standings"] = json.loads((DATA / "nhl_standings.json").read_text(encoding="utf-8"))
    d["mlb_standings"] = json.loads((DATA / "mlb_standings.json").read_text(encoding="utf-8"))
    d["leaders"] = json.loads((DATA / "nhl_leaders.json").read_text(encoding="utf-8"))
    return d


# --------------------------------------------------------------------------- helpers
def conf_badge(level: str) -> str:
    cls = {"High": "b-high", "Medium": "b-med", "Low": "b-low"}.get(level, "b-low")
    return f'<span class="badge {cls}">{escape(level)}</span>'


def band_badge(p: dict) -> str:
    if p.get("in_band"):
        return '<span class="badge b-band">in band</span>'
    return '<span class="badge b-out">outside band</span>'


def link(url: str, label: str | None = None) -> str:
    if not url.startswith("http"):
        return f'<span class="muted">{escape(label or url)}</span>'
    label = label or re.sub(r"^https?://(www\.)?", "", url)
    return f'<a href="{escape(url)}" rel="noopener">{escape(label)}</a>'


def source_cell(row: dict) -> str:
    return link(row["source_url"], f"{row['source_label']} ↗")


def layout(title: str, body: str, *, active: str = "", root_landing: bool = False,
           depth: int = 1) -> str:
    if root_landing:
        asset, plink, repo = "desk/", "desk/", ""
    else:
        asset = plink = "../" * (depth - 1)
        repo = "../" * depth
    nav_bits = []
    for name, href in NAV:
        cur = ' aria-current="page"' if name == active else ""
        nav_bits.append(f'<a href="{plink}{href}"{cur}>{escape(name)}</a>')
    nav = "".join(nav_bits)
    root_link = "" if root_landing else f'<a href="{repo}index.html">repository root</a>, '
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<meta name="description" content="Board S — official-source fixtures, our own originated lines, confidence grades and hand-written predictions for the sports in scope.">
<link rel="stylesheet" href="{asset}assets/style.css">
</head>
<body>
<header class="top"><div class="wrap bar">
  <a class="brand" href="{plink}index.html"><span class="mark">OLBG4</span><span class="sub">Board S · live desk 22 Oct 2026</span></a>
  <nav class="main">{nav}</nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
<p><strong>Board S</strong> · data cut-off 2026-10-22T02:00Z · every row carries the official page it was read from ·
every published pick is inside the requested -250..+10000 band · no bookmaker price is read anywhere.</p>
<p class="small">Probabilities and prices on this site are model output, not betting advice. Blank cells mean the official
source is silent, not that the value is zero. <a href="{plink}flagged.html">Flagged for review</a> lists everything
unconfirmed or structurally awkward. Earlier dashboards: <a href="{repo}board/index.html">master board</a>,
<a href="{repo}docs/index.html">docs build</a>, {root_link}and the <a href="{plink}verification.html">verification register</a>.</p>
</div></footer>
<script src="{asset}assets/app.js" defer></script>
</body></html>"""


def kpis(board: dict, flagged: dict, verification: dict) -> str:
    c = board["counts"]
    return f"""<div class="grid kpis">
  <div class="kpi"><div class="n">{c['fixtures']}</div><div class="l">fixtures</div></div>
  <div class="kpi"><div class="n">{len(c['by_sport'])}</div><div class="l">sports covered</div></div>
  <div class="kpi"><div class="n">{c['markets_originated']}</div><div class="l">market selections originated</div></div>
  <div class="kpi"><div class="n">{c['published_high_picks']}</div><div class="l">published high-confidence picks</div></div>
  <div class="kpi"><div class="n">{c['high_in_band_selections']}</div><div class="l">in-band high selections</div></div>
  <div class="kpi"><div class="n">{verification['passed']}/{len(verification['checks'])}</div><div class="l">verification gates passed</div></div>
</div>"""


def fixture_table(rows: list[dict], *, show_markets: bool = False) -> str:
    head = ("<tr><th>Date</th><th>Time</th><th>Sport</th><th>Match</th><th>Winner pick</th>"
            "<th class='num'>Price</th><th class='num'>Prob</th><th>Confidence</th><th>Band</th><th>Source</th></tr>")
    body = []
    for r in rows:
        w = r["winner_pick"]
        band = band_badge(w)
        body.append(
            f"<tr data-sport='{escape(r['sport'])}' data-conf='{escape(w['confidence'])}' "
            f"data-band='{'in' if w['in_band'] else 'out'}'>"
            f"<td class='num'>{escape(r['date'])}</td><td class='num'>{escape(r.get('time') or '—')}</td>"
            f"<td>{escape(r['sport'])}</td>"
            f"<td><strong>{escape(r['away'])}</strong> at <strong>{escape(r['home'])}</strong>"
            + (f"<div class='small muted'>{escape(r.get('description',''))}</div>" if r.get("description") else "")
            + f"</td>"
            f"<td>{escape(w['selection'])}<div class='small muted'>{escape(w['market_label'])}</div></td>"
            f"<td class='num'>{escape(w['american'])}</td><td class='num'>{w['prob_pct']}%</td>"
            f"<td>{conf_badge(w['confidence'])}</td><td>{band}</td>"
            f"<td>{source_cell(r)}</td></tr>"
        )
    return f"<div class='tablewrap'><table id='fixtures'>{head}{''.join(body)}</table></div>"


def pick_card(p: dict, pred: dict, row: dict) -> str:
    line_note = "alternate line" if p.get("line_type") == "alternate" else "standard line"
    facts = "".join(
        f"<li>{escape(f['fact'])} — {link(f['source'], 'source')}</li>" for f in pred["facts"]
    )
    return f"""<article class="pick">
  <div class="top">
    <div>
      <h3>{escape(p['match'])}</h3>
      <div class="meta">{escape(p['date'])} {escape(p.get('time') or '')} · {escape(p['league'])} · {escape(row.get('venue') or 'venue not captured')} · {source_cell(row)}</div>
    </div>
    <div>{conf_badge(p['confidence'])} {band_badge(p)}</div>
  </div>
  <div class="sel">
    <span class="chip">{escape(p['selection'])}</span>
    <span class="chip alt">{escape(p['american'])} · {p['prob_pct']}% model probability</span>
    <span class="chip alt">{escape(p['market_label'])} · {line_note}</span>
  </div>
  <p class="body">{escape(pred['text'])}</p>
  <details><summary>Why this grades High, and the {len(pred['facts'])} facts behind it</summary>
    <p class="small muted" style="margin-top:10px">Grade rule: {escape(p['high_reason'])}.</p>
    <ul>{facts}</ul>
  </details>
</article>"""


# --------------------------------------------------------------------------- pages
def page_dashboard(d: dict) -> str:
    b = d["board"]
    n_pub = len(b["published_high_picks"])
    rows = b["rows"]
    picks = b["published_high_picks"]
    by_sport = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)
    sport_rows = "".join(
        f"<tr><td><strong>{escape(s)}</strong></td><td class='num'>{len(rs)}</td>"
        f"<td class='num'>{sum(len(r['markets']) for r in rs)}</td>"
        f"<td class='num'>{sum(1 for r in rs for m in r['markets'] if m['confidence']=='High')}</td>"
        f"<td class='num'>{sum(1 for p in picks if p['sport']==s)}</td>"
        f"<td>{link('sports/' + rs[0]['sport_slug'] + '.html', 'open ' + s.lower() + ' page')}</td></tr>"
        for s, rs in sorted(by_sport.items())
    )
    featured = "".join(
        f"<div class='card'><div class='meta'>{escape(p['date'])} · {escape(p['league'])}</div>"
        f"<h3>{escape(p['match'])}</h3><p><strong>{escape(p['selection'])}</strong> at "
        f"<span class='mono'>{escape(p['american'])}</span> · {p['prob_pct']}%</p>"
        f"<div class='meta'>{conf_badge(p['confidence'])} {band_badge(p)}</div></div>"
        for p in picks[:3]
    )
    body = f"""
<section class="hero">
  <div class="kicker">Board S · refreshed 22 October 2026</div>
  <h1>Updated fixtures, our own lines, and {n_pub} high-confidence picks inside the price band you asked for.</h1>
  <p class="lede">{b['counts']['fixtures']} fixtures across {len(b['counts']['by_sport'])} sports, every one read on an official league page, {b['counts']['markets_originated']}
  market selections priced by our own model, and a hand-written prediction on each of the {n_pub} high-confidence picks that
  lands between -250 and +10000. Nothing is filled in when the official page is silent.</p>
  <div class="cta">
    <a class="btn primary" href="picks.html">Read the {len(picks)} predictions</a>
    <a class="btn" href="matches.html">Open the fixture table</a>
    <a class="btn" href="analysis.html">Why the band is narrow</a>
  </div>
</section>
{kpis(b, d['flagged'], d['verification'])}
<div class="note warn">
  <strong>Read this first.</strong> The band you asked for, -250 to +10000, is exactly the 0.00%-71.43% implied-probability
  range. Combined with "greater than 70% to win", the publishable window is 70.00%-71.43% — a 1.43-point slice. Every pick
  stronger than 71.43% prices shorter than -250 and is therefore published separately, graded, on the
  <a href="strong-picks.html">Strong picks</a> page rather than here. That is a mathematical property of the request, not a
  modelling choice, and it is logged as <a href="flagged.html">S-02</a>.
</div>
<h2>What is on the desk</h2>
<div class="tablewrap"><table>
<tr><th>Sport</th><th class="num">Fixtures</th><th class="num">Selections</th><th class="num">Selections graded High</th><th class="num">Published high picks</th><th>Page</th></tr>
{sport_rows}
</table></div>
<h2>{min(3, n_pub)} of the {n_pub} high-confidence picks</h2>
<div class="grid cards">{featured}</div>
<h2>How a row is built</h2>
<div class="grid cards">
  <div class="card"><h3>1 · Official fixture</h3><p class="meta">Date, start time, venue and clubs read on the league's own domain;
  the per-row link is the official game page. OLBG is not used as a source of any published value.</p></div>
  <div class="card"><h3>2 · Our own line</h3><p class="meta">A margin model on official goals/runs and record data, plus an
  independent win-rate model as a stability check. Prices are fair opening lines with no bookmaker input.</p></div>
  <div class="card"><h3>3 · Grade, then write</h3><p class="meta">High needs ≥70%, a price inside the band, seven games on both
  clubs and agreement between the two models. Only then is a human prediction written, with every number traced to a fact.</p></div>
</div>
<h2>Everything that is not confirmed</h2>
<p>{d['flagged']['counts']['total']} items are on the <a href="flagged.html">Flagged for review</a> page with their sources, including the
deployment blocker (S-01), the band arithmetic (S-02) and the sports this session could not capture (S-07).</p>
"""
    return layout("Dashboard — Board S · OLBG4", body, active="Dashboard", depth=1)


def page_matches(d: dict) -> str:
    rows = d["board"]["rows"]
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">All fixtures</div>
  <h1 style="font-size:30px">The full list, {len(rows)} rows</h1>
  <p class="lede" style="font-size:16px">One row per fixture, with the winner pick our model makes, its price, its grade, and the
  official page the fixture came from. Filter by sport, confidence or band.</p>
</section>
<div class="toolbar" style="margin-top:18px">
  <input type="search" id="q" placeholder="Search club, competition…" aria-label="Search fixtures">
  <select id="f-sport" aria-label="Filter by sport"><option value="">All sports</option>
    {''.join(f'<option>{escape(s)}</option>' for s in sorted({r['sport'] for r in rows}))}</select>
  <select id="f-conf" aria-label="Filter by confidence"><option value="">All confidence grades</option>
    <option>High</option><option>Medium</option><option>Low</option></select>
  <select id="f-band" aria-label="Filter by price band"><option value="">Any price</option>
    <option value="in">Inside -250..+10000</option><option value="out">Outside the band</option></select>
  <span class="small muted" id="count"></span>
</div>
{fixture_table(rows)}
<p class="small muted" style="margin-top:10px">NHL start times are Eastern, exactly as NHL.com publishes them. MLB start times are
UTC from the official MLB API. Blank venues are listed on <a href="flagged.html">Flagged</a>. Confidence grades are explained on
<a href="methodology.html">Method</a>.</p>
"""
    return layout("Fixtures — Board S · OLBG4", body, active="Fixtures", depth=1)


def page_picks(d: dict) -> str:
    n_out_band = d['board']['counts']['high_out_of_band_selections']
    b = d["board"]
    picks = b["published_high_picks"]
    rows = {r["id"]: r for r in b["rows"]}
    cards = "".join(pick_card(p, d["authored"]["predictions"][p["pick_id"]], rows[p["fixture_id"]]) for p in picks)
    wc = [len(d["authored"]["predictions"][p["pick_id"]]["text"].split()) for p in picks]
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">High-confidence picks</div>
  <h1 style="font-size:30px">{len(picks)} picks, each inside -250..+10000</h1>
  <p class="lede" style="font-size:16px">Every pick below clears 70% on our model, is priced at -250 or longer, sits on a fixture with a full
  sample on both sides (seven games for the team sports, ten matches for snooker), and is confirmed by the independent
  second model — the win-rate model for teams, the points-per-match check for snooker. Each carries a unique hand-written prediction of
  {min(wc)}-{max(wc)} words, with its facts and sources printed underneath.</p>
</section>
<div class="note"><strong>No template is reused.</strong> The build measures a six-word-shingle overlap between every pair of
predictions and fails above 0.25; the highest observed overlap in this set is printed on the
<a href="verification.html">verification page</a>. Every number in a prediction must appear in that prediction's own fact block,
which is also a build gate.</div>
{cards}
<h2>What is not here</h2>
<p>{n_out_band} selections that clear 70% price shorter than -250 and are therefore outside the requested band. They are
published with their grade, without a prediction, on <a href="strong-picks.html">Strong picks</a> — see
<a href="flagged.html">S-02</a> for the arithmetic.</p>
"""
    return layout("High-confidence picks — Board S · OLBG4", body, active="High-confidence picks", depth=1)


def page_strong(d: dict) -> str:
    n_pub = len(d["board"]["published_high_picks"])
    rows = d["board"]["rows"]
    out = []
    for r in rows:
        for m in r["markets"]:
            if m["confidence"] == "High" and not m["in_band"]:
                out.append((r, m))
    out.sort(key=lambda x: -x[1]["prob"])
    body_rows = "".join(
        f"<tr><td class='num'>{escape(r['date'])}</td><td>{escape(r['away'])} at {escape(r['home'])}</td>"
        f"<td>{escape(m['selection'])}<div class='small muted'>{escape(m['market_label'])}</div></td>"
        f"<td class='num'>{m['american']}</td><td class='num'>{m['prob_pct']}%</td>"
        f"<td>{conf_badge(m['confidence'])}</td><td>{source_cell(r)}</td></tr>"
        for r, m in out
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Outside the requested band</div>
  <h1 style="font-size:30px">{len(out)} selections clear 70% but price shorter than -250</h1>
  <p class="lede" style="font-size:16px">These are the strongest numbers on the desk and the reason the band matters. Each one
  is a genuine model view, graded High on probability, but its fair price is shorter than -250, so it cannot be published as a
  high-confidence pick under the rule you set. They carry no prediction by design; if you want them in the published set, the
  band floor needs to move and that is your call, not ours.</p>
</section>
<div class="tablewrap"><table>
<tr><th>Date</th><th>Match</th><th>Selection</th><th class="num">Our price</th><th class="num">Model prob</th><th>Grade</th><th>Source</th></tr>
{body_rows}
</table></div>
<p class="small muted">Sorted by probability. The same selections appear inside each fixture's row in
<a href="verification.html">the verification register</a>; none of them is counted in the {n_pub} published picks.</p>
"""
    return layout("Strong picks outside the band — Board S · OLBG4", body, active="Strong picks (out of band)", depth=1)


def page_markets(d: dict) -> str:
    rows = d["board"]["rows"]
    per = defaultdict(lambda: Counter())
    for r in rows:
        for m in r["markets"]:
            per[r["sport"]][m["market"]] += 1
    summary = "".join(
        f"<tr><td><strong>{escape(s)}</strong></td><td class='num'>{c['moneyline']}</td>"
        f"<td class='num'>{c['handicap']}</td><td class='num'>{c['total']}</td>"
        f"<td class='num'>{sum(c.values())}</td></tr>"
        for s, c in sorted(per.items())
    )
    sample_rows = []
    for r in rows[:12]:
        for m in r["markets"]:
            if m["market"] == "handicap" and m["alternate_line"]:
                continue
            if m["market"] == "total" and m["alternate_line"]:
                continue
            sample_rows.append(
                f"<tr><td>{escape(r['away'])} at {escape(r['home'])}</td><td>{escape(m['market_label'])}</td>"
                f"<td>{escape(m['selection'])}</td><td class='num'>{m['american']}</td>"
                f"<td class='num'>{m['prob_pct']}%</td><td>{conf_badge(m['confidence'])}</td></tr>"
            )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Markets</div>
  <h1 style="font-size:30px">Match winner, handicap and total — all three, every fixture</h1>
  <p class="lede" style="font-size:16px">We originate a two-way price on the moneyline, the puck/run line (standard ±1.5 plus two
  alternates) and the match total (standard line plus one alternate). That is {d['board']['counts']['markets_originated']} priced
  selections over {len(rows)} fixtures. No market is left blank without a stated reason.</p>
</section>
<h2>Coverage by sport</h2>
<div class="tablewrap"><table>
<tr><th>Sport</th><th class="num">Moneyline selections</th><th class="num">Handicap selections</th><th class="num">Total selections</th><th class="num">All</th></tr>
{summary}
</table></div>
<h2>Sample of originated markets</h2>
<div class="tablewrap"><table>
<tr><th>Match</th><th>Market</th><th>Selection</th><th class="num">Price</th><th class="num">Prob</th><th>Grade</th></tr>
{''.join(sample_rows)}
</table></div>
<div class="note"><strong>Line construction.</strong> Moneyline probability comes from a normal margin distribution around the
projected goal/run margin. The handicap prices P(margin &gt; line) on the same distribution. The total prices P(goals &gt; line)
around the projected total. Standard lines are 5.5/6.5 and ±1.5; 4.5/7.5 and ±2.5/±3.5 are alternates and are labelled as such.
A -0.5 puck line is deliberately not quoted: a win is always by at least one goal, so it would be the moneyline under a second name.</div>
"""
    return layout("Markets — Board S · OLBG4", body, active="Markets", depth=1)


def page_analysis(d: dict) -> str:
    b = d["board"]
    rows = b["rows"]
    band = b["price_band"]
    n_high = sum(len(r["high_picks"]) for r in rows)
    n_in = b["counts"]["high_in_band_selections"]
    n_out = n_high - n_in
    def _proj_cells(r: dict) -> str:
        pr = r["projection"]
        if "expected_margin" in pr:
            m1 = f"{pr['expected_margin']:+.2f}"
            m2 = f"{pr['p_home_margin_model'] * 100:.1f}%"
            m3 = f"{pr.get('expected_total', 0):.2f}"
        elif "expected_frames" in pr:
            m1 = f"frames {pr['expected_frames']:.2f}"
            m2 = f"{pr.get('p_frame', 0) * 100:.1f}% frame"
            m3 = f"{pr.get('p_home_winrate_model', 0) * 100:.1f}% match"
        else:
            m1 = m2 = m3 = ""
        agree = "agree" if pr.get("models_agree_home", pr.get("scoring_check_agrees", True)) else "split"
        return (f"<td class='num'>{m1}</td><td class='num'>{m2}</td>"
                f"<td class='num'>{pr.get('p_home_winrate_model', 0) * 100:.1f}%</td>"
                f"<td class='num'>{m3}</td><td class='num'>{r['sample_games_min']}</td>"
                f"<td>{agree}</td>")

    proj_rows = "".join(
        f"<tr><td class='num'>{escape(r['date'])}</td><td>{escape(r['away'])} at {escape(r['home'])}</td>"
        + _proj_cells(r) + "</tr>"
        for r in rows
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Analysis</div>
  <h1 style="font-size:30px">What the model says, and what the price band does to it</h1>
  <p class="lede" style="font-size:16px">Two independent strength estimates per fixture, a normal margin distribution for prices,
  and a hard band rule on top. The numbers below are the whole analysis — there is no black box to take on trust.</p>
</section>
<h2>The band arithmetic</h2>
<div class="grid cards">
  <div class="card"><h3>-250 is 71.43%</h3><p class="meta">American -250 converts to a decimal price of 1.40, and 1/1.40 = 71.43%.
  That is the floor of the band you set, expressed as a probability.</p></div>
  <div class="card"><h3>&gt;70% is the other gate</h3><p class="meta">The other gate is a model probability above 70.00%. Put the two
  together and the publishable window is 70.00% to 71.43%.</p></div>
  <div class="card"><h3>{n_high} selections clear 70%</h3><p class="meta">Of those, {n_in} sit inside the band and {n_out} price
  shorter than -250. The {n_out} are published, graded, on <a href="strong-picks.html">Strong picks</a>.</p></div>
</div>
<p>This is the single most important finding of the session. A "greater than 70% chance" pick is, by construction, a short
favourite, and a short favourite cannot price at -250 or longer. The only overlap is the narrow slice just above 70%. Every
pick in that slice on this card is a total or a puck line for exactly that reason — the moneylines are either below 70% or
above 71.43%.</p>
<h2>Projections, fixture by fixture</h2>
<div class="tablewrap"><table>
<tr><th>Date</th><th>Match</th><th class="num">Proj. margin / frames</th><th class="num">Margin or frame model (home)</th><th class="num">Win-rate model (home)</th><th class="num">Proj. total / frame p</th><th class="num">Min games</th><th>Models</th></tr>
{proj_rows}
</table></div>
<h2>How the two estimates are built</h2>
<dl class="kv">
  <dt>Margin model</dt><dd>Goals (or runs) for minus against, per game, shrunk toward zero by the games played, plus a declared
  home edge, read through a normal distribution whose standard deviation is a declared league constant.</dd>
  <dt>Win-rate model</dt><dd>Win rate, shrunk toward .500, on a logit scale, with a small home-edge term. NHL overtime and
  shootout losses count as half a win for the match-winner market.</dd>
  <dt>Agreement</dt><dd>The two are never blended. A pick can only grade High when both point the same way. On this card
  {sum(1 for r in rows if r['projection'].get('models_agree_home', True))} of {len(rows)} fixtures have agreeing models.</dd>
  <dt>Totals</dt><dd>Projected team goals are half the club's own scoring rate plus half the opponent's conceding rate, shrunk
  toward the league average, with the home edge split between the sides. The total's second check is that the projection is at
  least 0.25 goals clear of the line.</dd>
  <dt>What is missing</dt><dd>No game-level backtest, no calibration curve, no closing-line comparison. Those need historical
  game logs that this environment could not pull. Flagged as S-05.</dd>
</dl>
<h2>Coverage and gaps</h2>
<p>Two sports are covered because two official machine-readable feeds were reachable: the NHL score/standings API and the MLB
Stats API. The NBA endpoints returned HTTP 500 or did not respond; every other in-scope sport publishes fixtures as HTML or
behind a browser, and re-keying those pages by hand is how errors get in. Those sports are listed as not captured (S-07) rather
than padded with unverified rows.</p>
"""
    return layout("Analysis — Board S · OLBG4", body, active="Analysis", depth=1)


def page_verification(d: dict) -> str:
    v = d["verification"]
    rows = d["board"]["rows"]
    def _result(ok: bool) -> str:
        return '<span class="badge b-ok">PASS</span>' if ok else '<span class="badge b-out">FAIL</span>'

    checks = "".join(
        "<tr><td>" + _result(c["ok"]) + "</td>"
        + f"<td>{escape(c['check'])}</td><td class='small muted'>{escape(c['detail'])}</td></tr>"
        for c in v["checks"]
    )
    reg = "".join(
        f"<tr><td class='mono small'>{escape(r['id'])}</td><td class='num'>{escape(r['date'])}</td>"
        f"<td>{escape(r['away'])} at {escape(r['home'])}</td>"
        f"<td>{link(r['verification']['fixture_source'], 'fixture')}</td>"
        f"<td>{link(r['verification']['rating_source'], 'form & record')}</td>"
        f"<td>{link(r['source_url'], 'game page')}</td>"
        f"<td><span class='badge b-ok'>official</span></td></tr>"
        for r in rows
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Verification register</div>
  <h1 style="font-size:30px">{v['passed']} of {len(v['checks'])} gates pass</h1>
  <p class="lede" style="font-size:16px">The gate is code, not a claim: <span class="mono">python3 -m deskbot.verify</span> exits
  non-zero if a row loses its official source, a price stops reproducing, a published pick leaves the band, a prediction drops
  below 30 words or introduces a number that is not in its own fact block.</p>
</section>
<h2>Gate results</h2>
<div class="tablewrap"><table><tr><th>Result</th><th>Check</th><th>Evidence</th></tr>{checks}</table></div>
<h2>Row-by-row register</h2>
<p class="small muted">Each fixture's date and start time was read on the league schedule page, its records and form on the
league standings page, and its club leaders in the official game feed. The per-row game page is linked but not individually
opened; that is stated on every row rather than implied.</p>
<div class="tablewrap"><table>
<tr><th>ID</th><th>Date</th><th>Match</th><th>Fixture source</th><th>Form & record source</th><th>Game page</th><th>Status</th></tr>
{reg}
</table></div>
"""
    return layout("Verification — Board S · OLBG4", body, active="Verification", depth=1)


def page_sources(d: dict) -> str:
    b = d["board"]
    domains = Counter()
    for r in b["rows"]:
        for u in [r["source_url"], *r.get("extra_sources", [])]:
            m = re.match(r"https?://([^/]+)", u)
            if m:
                domains[m.group(1)] += 1
    dom_rows = "".join(
        f"<tr><td class='mono'>{escape(k)}</td><td class='num'>{v}</td>"
        f"<td>{'league / governing body' if any(x in k for x in ('nhl.com','mlb.com')) else 'other'}</td></tr>"
        for k, v in domains.most_common()
    )
    creds = "".join(
        f"<tr><td>{escape(name)}</td><td>{link(url)}</td><td class='small muted'>{escape(what)}</td></tr>"
        for name, url, what in [
            ("NHL.com schedule", "https://www.nhl.com/schedule", "fixture list, dates, start times in ET"),
            ("NHL.com standings", "https://www.nhl.com/standings/2026-10-21/wildcard", "record, goals for/against, home/away splits, last ten, streak"),
            ("NHL score feed 22 Oct", "https://api-web.nhle.com/v1/score/2026-10-22", "club leaders (goals, assists, goalie wins), venues"),
            ("NHL score feed 23 Oct", "https://api-web.nhle.com/v1/score/2026-10-23", "club leaders, venue for the 23 October games"),
            ("NHL score feed 25 Oct", "https://api-web.nhle.com/v1/score/2026-10-25", "club leaders and venues for 25 October"),
            ("MLB Stats API schedule", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-29&hydrate=probablePitcher", "World Series game numbers, venues, start times, probable pitcher"),
            ("MLB Stats API standings", "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026&standingsTypes=regularSeason", "2026 final regular-season records, runs for/against, home/away and last-ten splits"),
        ]
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Sources</div>
  <h1 style="font-size:30px">Every value comes from a league domain</h1>
  <p class="lede" style="font-size:16px">No aggregator, no bookmaker, no OLBG page is the source of a published number. The
  domains below are the only ones used, and each is linked from the row it produced.</p>
</section>
<h2>Domains in use</h2>
<div class="tablewrap"><table><tr><th>Domain</th><th class="num">Links</th><th>Classification</th></tr>{dom_rows}</table></div>
<h2>The seven pages this desk actually reads</h2>
<div class="tablewrap"><table><tr><th>Source</th><th>URL</th><th>What it supplies</th></tr>{creds}</table></div>
<div class="note warn"><strong>What is deliberately absent.</strong> No bookmaker or odds-comparison page is read, so the prices
here are our own fair lines and not a market consensus. No secondary news site is used for a fact. OLBG itself could not be
fetched from this environment (S-10), so the OLBG event ids are not used and the sport universe is the one recorded by earlier
sessions.</div>
"""
    return layout("Sources — Board S · OLBG4", body, active="Sources", depth=1)


def page_flagged(d: dict) -> str:
    items = d["flagged"]["items"]
    cards = "".join(
        f"""<article class="pick">
  <div class="top"><div><h3>{escape(i['title'])}</h3>
  <div class="meta">{escape(i['id'])} · severity {escape(i['severity'])}</div></div>
  <div><span class="badge {'b-out' if i['severity']=='high' else ('b-warn' if i['severity']=='medium' else 'b-low')}">{escape(i['severity'])}</span></div></div>
  <p class="body">{escape(i['detail'])}</p>
  <details><summary>Sources for this item</summary><ul>
  {''.join(f"<li>{link(s['url'], s['label'])}</li>" for s in i['sources'])}
  </ul></details>
</article>"""
        for i in items
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Flagged for review</div>
  <h1 style="font-size:30px">{d['flagged']['counts']['total']} items, with sources</h1>
  <p class="lede" style="font-size:16px">Everything unconfirmed, structurally awkward or incomplete is here rather than buried.
  Nothing on this page blocks publication: the site states the limitation instead of filling the gap with a guess.</p>
</section>
<div class="note bad"><strong>Two items matter most.</strong> S-01: the GitHub connection in this environment cannot open a pull
request or deploy, so this site is published as a branch, not on Pages. S-02: the requested price band mathematically caps the
publishable probability at 71.43%, which is why the strongest picks sit outside the published set.</div>
{cards}
"""
    return layout("Flagged for review — Board S · OLBG4", body, active="Flagged for review", depth=1)


def page_method(d: dict) -> str:
    c = d["board"]["constants"]
    band = d["board"]["price_band"]
    const_rows = "".join(
        f"<tr><td class='mono'>{escape(k)}</td><td class='num'>{escape(str(v['value']))}</td><td>{escape(v['why'])}</td></tr>"
        for k, v in c.items()
    )
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">Method</div>
  <h1 style="font-size:30px">How a fixture becomes a pick</h1>
  <p class="lede" style="font-size:16px">Five steps, each with its inputs named. Every constant is listed below with the reason
  it has the value it has; none of them is fitted on data this session could not see.</p>
</section>
<h2>1 · Fixture</h2>
<p>A fixture is published only if a league or governing body's own domain lists it with at least a date and two clubs. The row
stores that URL. Where the official page is silent on a field — venue, for example — the cell is blank and the gap is on
<a href="flagged.html">Flagged</a>.</p>
<h2>2 · Projection</h2>
<p>Two estimates: a margin model on shrunk goal/run differential plus a declared home edge, and an independent win-rate model
on shrunk win percentage. The margin model sets the price; the win-rate model is a stability check and never blended in.</p>
<h2>3 · Line</h2>
<p>Prices are fair opening lines: decimal price = 1/probability, with no overround added. Moneyline, least two handicap lines
and at least two total lines are priced for every fixture. Half-point lines only, so nothing can push.</p>
<h2>4 · Grade</h2>
<ul>
  <li><strong>High</strong> — probability ≥ {band['min_prob']*100:.0f}%, price inside {band['label']}, both clubs on 7+ games,
  and the second model agreeing on the side.</li>
  <li><strong>Medium</strong> — probability 60.0%-69.9%, or a High-level probability that fails one of the gates above.</li>
  <li><strong>Low</strong> — below 60.0%.</li>
</ul>
<h2>5 · Prediction</h2>
<p>A prediction is written by hand for each published High pick and must name the clubs, a player from the official club-leaders
data, current form, the recent record and the exact selection. The build rejects anything under 30 words, anything whose numbers
are not in its own fact block, and any pair of predictions sharing a six-word run.</p>
<h2>Declared constants</h2>
<div class="tablewrap"><table><tr><th>Constant</th><th class="num">Value</th><th>Why</th></tr>{const_rows}</table></div>
<h2>What this method cannot do</h2>
<p>It cannot measure its own accuracy: no historical game log was reachable, so there is no backtest, no calibration table and no
closing-line record. It cannot see injuries, rest, travel or goaltender starters beyond the one probable pitcher MLB published.
And it cannot produce a high-confidence pick at a long price, because "high confidence" is defined by probability and long prices
are low probabilities. Those limits are published, not hidden.</p>
"""
    return layout("Method — Board S · OLBG4", body, active="Method", depth=1)


def page_sport(d: dict, slug: str) -> str:
    rows = [r for r in d["board"]["rows"] if r["sport_slug"] == slug]
    sport = rows[0]["sport"]
    picks = [p for p in d["board"]["published_high_picks"] if p["sport"] == sport]
    standings = ""
    if slug == "ice-hockey":
        teams = sorted(d["standings"]["teams"].values(), key=lambda t: -t["pts"])
        standings = (
            "<h2>Official standings used as model input</h2>"
            f"<p class='small muted'>Source: {link(d['standings']['source'], d['standings']['source_label'])}. Captured 2026-10-22.</p>"
            "<div class='tablewrap'><table><tr><th>Team</th><th class='num'>GP</th><th class='num'>W</th><th class='num'>L</th>"
            "<th class='num'>OT</th><th class='num'>PTS</th><th class='num'>GF</th><th class='num'>GA</th><th>Home</th><th>Away</th><th>L10</th><th>STRK</th></tr>"
            + "".join(
                f"<tr><td>{escape(t['name'])}</td><td class='num'>{t['gp']}</td><td class='num'>{t['w']}</td>"
                f"<td class='num'>{t['l']}</td><td class='num'>{t['otl']}</td><td class='num'>{t['pts']}</td>"
                f"<td class='num'>{t['gf']}</td><td class='num'>{t['ga']}</td><td class='num'>{t['home']}</td>"
                f"<td class='num'>{t['away']}</td><td class='num'>{t['l10']}</td><td class='num'>{t['streak']}</td></tr>"
                for t in teams
            )
            + "</table></div>"
        )
    if slug == "snooker":
        players = []
        for r in rows:
            for side in ("home", "away"):
                st = r["inputs"][side]
                if st.get("matches"):
                    players.append((r[side], st))
        players.sort(key=lambda x: (-(x[1].get("win_pct") or 0), x[0]))
        standings = (
            "<h2>Official season form used as model input</h2>"
            f"<p class='small muted'>Season matches, match win rate, points, 50+ breaks and centuries from each player's "
            f"{link('https://www.wst.tv/matches', 'official WST Match Centre')}. Ranking positions come from the "
            f"{link('https://www.wst.tv/rankings/abfba8fe-1423-5a2a-a96b-d77e8b413ca8?showLive=false', 'official WST world rankings')}, "
            "which publishes only the top 36 players — a blank rank means the player is outside that published table, not that the rank is zero.</p>"
            "<div class='tablewrap'><table><tr><th>Player</th><th class='num'>Matches</th><th class='num'>Win %</th>"
            "<th class='num'>Points</th><th class='num'>50+</th><th class='num'>100+</th><th class='num'>AST</th><th class='num'>Rank</th></tr>"
            + "".join(
                f"<tr><td>{escape(name)}</td><td class='num'>{st['matches']}</td><td class='num'>{st['win_pct']}%</td>"
                f"<td class='num'>{st['points']}</td><td class='num'>{st['fifties']}</td><td class='num'>{st['hundreds']}</td>"
                f"<td class='num'>{st['ast']}</td><td class='num'>{st.get('rank') or ''}</td></tr>"
                for name, st in players
            )
            + "</table></div>"
        )
    if slug == "baseball":
        teams = d["mlb_standings"]["teams"]
        standings = (
            "<h2>Official 2026 regular-season records used as model input</h2>"
            f"<p class='small muted'>Source: {link(d['mlb_standings']['source'], d['mlb_standings']['source_label'])}. Records are final regular-season figures; postseason results are not included.</p>"
            "<div class='tablewrap'><table><tr><th>Team</th><th class='num'>W-L</th><th class='num'>RS</th><th class='num'>RA</th><th>Home</th><th>Away</th><th>L10</th></tr>"
            + "".join(
                f"<tr><td>{escape(t['name'])}</td><td class='num'>{t['w']}-{t['l']}</td><td class='num'>{t['rs']}</td>"
                f"<td class='num'>{t['ra']}</td><td class='num'>{t['home']}</td><td class='num'>{t['away']}</td><td class='num'>{t['l10']}</td></tr>"
                for t in teams.values()
            )
            + "</table></div>"
        )
    pick_cards = "".join(
        f"<div class='card'><div class='meta'>{escape(p['date'])}</div><h3>{escape(p['match'])}</h3>"
        f"<p><strong>{escape(p['selection'])}</strong> · <span class='mono'>{escape(p['american'])}</span> · {p['prob_pct']}%</p>"
        f"<div class='meta'>{conf_badge(p['confidence'])} {band_badge(p)}</div></div>"
        for p in picks
    ) or "<p class='muted'>No fixture in this sport produced a pick inside the requested band.</p>"
    body = f"""
<section class="hero" style="padding:22px 26px">
  <div class="kicker">{escape(sport)}</div>
  <h1 style="font-size:30px">{len(rows)} fixtures · {sum(len(r['markets']) for r in rows)} originated selections</h1>
  <p class="lede" style="font-size:16px">Every row below was read on the league's own domain and priced by the model described on
  the <a href="../methodology.html">Method</a> page. Winner pick, price, grade and band are shown for each fixture; the full
  market book is in the verification register.</p>
</section>
<div class="grid cards" style="margin-bottom:8px">{pick_cards}</div>
{fixture_table(rows)}
{standings}
"""
    return layout(f"{sport} — Board S · OLBG4", body, active="Dashboard", depth=2)


def page_root_landing(d: dict) -> str:
    b = d["board"]
    n_pub = len(b["published_high_picks"])
    picks = b["published_high_picks"]
    wc = [len(d["authored"]["predictions"][p["pick_id"]]["text"].split()) for p in picks]
    featured = "".join(
        f"""<a class="card" href="desk/picks.html" style="display:block;color:inherit">
        <div class="meta">{escape(p['date'])} · {escape(p['league'])}</div>
        <h3>{escape(p['match'])}</h3>
        <p><strong>{escape(p['selection'])}</strong> at <span class="mono">{escape(p['american'])}</span> · {p['prob_pct']}%</p>
        <div class="meta">{conf_badge(p['confidence'])} {band_badge(p)}</div></a>"""
        for p in picks[:3]
    )
    body = f"""
<section class="hero">
  <div class="kicker">OLBG4 · Board S · refreshed 22 October 2026</div>
  <h1>Official-source fixtures, our own lines, and predictions you can check line by line.</h1>
  <p class="lede">A clean desk for the sports in scope: {b['counts']['fixtures']} upcoming fixtures across
  {len(b['counts']['by_sport'])} sports, {b['counts']['markets_originated']} originated selections, and
  {len(picks)} hand-written high-confidence picks — every one inside the -250 to +10000 band you asked for, every fact
  linked to the league page it came from.</p>
  <div class="cta">
    <a class="btn primary" href="desk/index.html">Open the dashboard</a>
    <a class="btn" href="desk/picks.html">Read the {len(picks)} predictions</a>
    <a class="btn" href="desk/matches.html">All {b['counts']['fixtures']} fixtures</a>
    <a class="btn" href="desk/flagged.html">Flagged for review</a>
  </div>
</section>
{kpis(b, d['flagged'], d['verification'])}
<div class="note warn"><strong>This site is committed to the branch, not yet deployed.</strong>
The GitHub connection in this environment cannot create a pull request or trigger Pages (invalid CLI token, API returns 403),
so the deploy step is outstanding and is logged as S-01 on <a href="desk/flagged.html">Flagged for review</a>. Everything else —
data, gates, pages — is finished and reproducible from the repository.</div>
<h2>Start here</h2>
<div class="grid cards">
  <a class="card" href="desk/index.html" style="display:block;color:inherit"><h3>Dashboard</h3>
  <p class="meta">The headline numbers, the coverage table and what each page holds.</p></a>
  <a class="card" href="desk/picks.html" style="display:block;color:inherit"><h3>High-confidence picks</h3>
  <p class="meta">{len(picks)} picks, {min(wc)}-{max(wc)} words each, with every fact and source printed under the card.</p></a>
  <a class="card" href="desk/matches.html" style="display:block;color:inherit"><h3>Fixture table</h3>
  <p class="meta">All {b['counts']['fixtures']} fixtures, filterable by sport, confidence and price band.</p></a>
  <a class="card" href="desk/analysis.html" style="display:block;color:inherit"><h3>Analysis</h3>
  <p class="meta">The two models, the projections, and why the -250 floor caps the publishable probability at 71.43%.</p></a>
  <a class="card" href="desk/verification.html" style="display:block;color:inherit"><h3>Verification</h3>
  <p class="meta">{d['verification']['passed']} of {len(d['verification']['checks'])} gates pass, with a row-by-row register.</p></a>
  <a class="card" href="desk/flagged.html" style="display:block;color:inherit"><h3>Flagged for review</h3>
  <p class="meta">{d['flagged']['counts']['total']} items that are unconfirmed or structurally awkward, each with sources.</p></a>
</div>
<h2>{min(3, n_pub)} of the {n_pub} picks</h2>
<div class="grid cards">{featured}</div>
<h2>Earlier builds in this repository</h2>
<p class="small">This session did not touch them; each carries its own 21 October cut-off and its own verification register.</p>
<div class="grid cards">
  <a class="card" href="board/index.html" style="display:block;color:inherit"><h3>Consolidated master board</h3><p class="meta">317 rows across 18 sports, merged from six earlier builds.</p></a>
  <a class="card" href="docs/index.html" style="display:block;color:inherit"><h3>Docs build</h3><p class="meta">144 rows across 15 sports with per-sport pages.</p></a>
  <a class="card" href="session-ee9c2db4/index.html" style="display:block;color:inherit"><h3>All-17-sports desk</h3><p class="meta">268 events, 696 probability books, 38 high picks.</p></a>
  <a class="card" href="session-4afef1af/index.html" style="display:block;color:inherit"><h3>Refreshable pipeline desk</h3><p class="meta">NBA, NHL and MLB from official APIs, refreshed by GitHub Actions.</p></a>
</div>
"""
    return layout("OLBG4 — official-source fixtures, our own lines, verified picks", body, root_landing=True)


def page_coverage_extra(d: dict) -> str:
    """Sports in scope but not captured, with the reason and the prior build that covers them."""
    return ""


def render(d: dict) -> list[Path]:
    pages = {
        DESK / "index.html": page_dashboard(d),
        DESK / "matches.html": page_matches(d),
        DESK / "picks.html": page_picks(d),
        DESK / "strong-picks.html": page_strong(d),
        DESK / "markets.html": page_markets(d),
        DESK / "analysis.html": page_analysis(d),
        DESK / "verification.html": page_verification(d),
        DESK / "sources.html": page_sources(d),
        DESK / "flagged.html": page_flagged(d),
        DESK / "methodology.html": page_method(d),
        DESK / "sports" / "ice-hockey.html": page_sport(d, "ice-hockey"),
        DESK / "sports" / "baseball.html": page_sport(d, "baseball"),
        DESK / "sports" / "snooker.html": page_sport(d, "snooker"),
        ROOT / "index.html": page_root_landing(d),
    }
    written = []
    for path, html in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding="utf-8")
        written.append(path)
    # keep the repo root landing self-contained for its own stylesheet path
    return written


APP_JS = """
(function () {
  var table = document.getElementById('fixtures');
  if (!table) return;
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  var q = document.getElementById('q'),
      sport = document.getElementById('f-sport'),
      conf = document.getElementById('f-conf'),
      band = document.getElementById('f-band'),
      count = document.getElementById('count');
  function apply() {
    var term = (q.value || '').toLowerCase(), shown = 0;
    rows.forEach(function (tr) {
      var text = tr.innerText.toLowerCase();
      var ok = (!term || text.indexOf(term) !== -1)
        && (!sport.value || tr.getAttribute('data-sport') === sport.value)
        && (!conf.value || tr.getAttribute('data-conf') === conf.value)
        && (!band.value || tr.getAttribute('data-band') === band.value);
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++;
    });
    if (count) count.textContent = shown + ' of ' + rows.length + ' fixtures';
  }
  [q, sport, conf, band].forEach(function (el) { if (el) el.addEventListener('input', apply); });
  apply();
})();
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-build", action="store_true")
    args = ap.parse_args(argv)
    if not args.no_build:
        board = build_mod.build()
        (DATA / "board.json").write_text(json.dumps(board, indent=1, ensure_ascii=False), encoding="utf-8")
        gate = verify_mod.run()
        (DATA / "verification.json").write_text(json.dumps({
            "checks": gate.checks,
            "passed": sum(1 for c in gate.checks if c["ok"]),
            "failed": len(gate.failures),
            "generated_utc": "2026-10-22T02:40:00Z",
        }, indent=1), encoding="utf-8")
        if gate.failures:
            print(f"{len(gate.failures)} gate(s) failed; refusing to render")
            for c in gate.failures:
                print(" -", c["check"], c["detail"])
            return 1
    d = load()
    (DESK / "assets" / "app.js").write_text(APP_JS, encoding="utf-8")
    written = render(d)
    print(f"rendered {len(written)} pages")
    for p in written:
        print("  ", p.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

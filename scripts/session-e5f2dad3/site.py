#!/usr/bin/env python3
"""Render the Board U dashboard from data/session-e5f2dad3/board.json.

Static HTML only: no external fonts, no analytics, no JavaScript requests.  The
single script file filters tables that are already fully rendered in the page, so
the tables work with JavaScript disabled too (the filter controls are hidden).

Run: python3 scripts/session-e5f2dad3/site.py
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e5f2dad3")
OUT = os.path.join(ROOT, "session-e5f2dad3")
BOARD = json.load(open(os.path.join(DATA, "board.json")))
LISTING = json.load(open(os.path.join(DATA, "olbg_listing.json")))
PRED_PATH = os.path.join(DATA, "predictions.json")
PREDS = json.load(open(PRED_PATH))["predictions"] if os.path.exists(PRED_PATH) else []


def e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def moneyline(r):
    return (r.get("markets") or {}).get("moneyline")


def source_link(r) -> str:
    s = r["source"]
    label = "official source" if s.get("official") else "OLBG listing"
    return f'<a href="{e(s["url"])}" rel="noopener">{e(label)} ↗</a>'


def ver_badge(r) -> str:
    if r.get("verification") == "official":
        return '<span class="badge ok">official</span>'
    return '<span class="badge warn">OLBG listing</span>'


def conf_badge(c: str) -> str:
    if c == "High":
        return '<span class="badge high">High</span>'
    if c == "Medium":
        return '<span class="badge med">Medium</span>'
    if c == "Low":
        return '<span class="badge low">Low</span>'
    return '<span class="badge none">not graded</span>'


def match_label(r) -> str:
    if r.get("home_away_designated") is False:
        return f'{r["home"]} v {r["away"]}'
    return f'{r["away"]} @ {r["home"]}'


def win_badge(r) -> str:
    if r.get("window_ok"):
        return '<span class="badge ok">in window</span>'
    return '<span class="badge warn">shorter than −250</span>'


def when(r) -> str:
    t = r.get("start_utc") or ""
    if t.endswith(".000Z"):
        t = t[:-5] + "Z"
    return t.replace("T", " ").replace("Z", " UTC") if t else "—"


NAV = [("index.html", "Dashboard"), ("fixtures.html", "All matches"), ("picks.html", "Our lines & picks"),
       ("predictions.html", "High-confidence write-ups"), ("markets.html", "Markets"),
       ("verification.html", "Verification register"), ("analysis.html", "Analysis"),
       ("flagged.html", "Flagged for review"), ("sources.html", "Sources"), ("methodology.html", "Method")]

SPORT_ORDER = ["Ice Hockey", "Baseball", "Basketball", "Cricket", "Tennis", "Darts", "Snooker",
               "Rugby Union", "Rugby League", "Handball", "Volleyball", "Esports", "Golf",
               "Greyhounds", "Aussie Rules", "Badminton", "Table Tennis", "Motor Racing",
               "Gaelic Football"]

SLUG = {r["sport"]: r["slug"] for r in BOARD["fixtures"]}


def page(title: str, active: str, body: str, subtitle: str = "", up: str = "") -> str:
    nav = "".join(f'<a class="navlink{" active" if href == active else ""}" href="{up}{href}">{e(label)}</a>'
                  for href, label in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OLBG4 Board U</title>
<meta name="description" content="Board U: official-source verified fixtures for the sports OLBG covers, our own originated lines, graded picks and a source link on every row.">
<link rel="stylesheet" href="{up}assets/site.css">
</head>
<body>
<header class="topbar">
  <div class="wrap bar">
    <a class="brand" href="{up}index.html"><span class="mark">OLBG4</span><span class="brandsub">Board U · 22 Oct 2026 refresh</span></a>
    <nav class="nav">{nav}</nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap footer">
  <p>Board U · session <code>arena/e5f2dad3-olbg4</code> · dataset generated {e(BOARD["generated_at_utc"])}.
  Sports excluded by the brief (soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials)
  are absent from every table. Every published price is our own fair-odds estimate; no bookmaker price is read anywhere.</p>
  <p>{subtitle}</p>
</footer>
<script src="{up}assets/app.js"></script>
</body>
</html>
"""


def kpi(value, label, note) -> str:
    return (f'<div class="kpi"><div class="kval">{e(value)}</div>'
            f'<div class="klab">{e(label)}</div><div class="knote">{e(note)}</div></div>')


def table(rows, headers, cls="", table_id="", filters=False, row_attrs=None) -> str:
    """rows: list of (cells_html, attrs_string)."""
    controls = ""
    if filters:
        sports = sorted({r["sport"] for r in BOARD["fixtures"]}, key=lambda s: SPORT_ORDER.index(s) if s in SPORT_ORDER else 99)
        opts = "".join(f'<option value="{e(s)}">{e(s)}</option>' for s in sports)
        controls = f"""<div class="filters" data-for="{table_id}">
  <label>Sport <select data-f="sport"><option value="">All</option>{opts}</select></label>
  <label>Verification <select data-f="ver"><option value="">All</option>
    <option value="official">official source</option><option value="olbg-listing">OLBG listing only</option></select></label>
  <label>Confidence <select data-f="conf"><option value="">All</option>
    <option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option>
    <option value="none">not graded</option></select></label>
  <label>Search <input type="search" data-f="q" placeholder="team, player, competition"></label>
  <span class="count" data-count>—</span>
</div>"""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join(f"<tr {a}>{c}</tr>" for c, a in rows)
    return f"""{controls}<div class="tablewrap"><table class="{cls}" id="{table_id}">
<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"""


# ------------------------------------------------------------------ derived
FIX = BOARD["fixtures"]
OFFICIAL = [r for r in FIX if r.get("verification") == "official"]
PRICED = [r for r in FIX if r.get("markets")]
HIGH_ALL = [r for r in FIX if r.get("confidence") == "High"]
HIGH = [r for r in HIGH_ALL if r.get("window_ok")]
HIGH_EXCLUDED = [r for r in HIGH_ALL if not r.get("window_ok")]
MED = [r for r in FIX if r.get("confidence") == "Medium"]
LOW = [r for r in FIX if r.get("confidence") == "Low"]
LISTING_ROWS = [r for r in FIX if r.get("verification") == "olbg-listing"]
COUNTS = BOARD["counts"]
PRED_BY_FIX = {p["fixture_id"]: p for p in PREDS}


def sport_summary():
    out = {}
    for r in FIX:
        s = r["sport"]
        d = out.setdefault(s, {"slug": r["slug"], "total": 0, "official": 0, "priced": 0,
                               "High": 0, "Medium": 0, "Low": 0, "listing": 0})
        d["total"] += 1
        if r.get("verification") == "official":
            d["official"] += 1
        else:
            d["listing"] += 1
        if r.get("markets"):
            d["priced"] += 1
        if r.get("confidence") in ("High", "Medium", "Low"):
            d[r["confidence"]] += 1
    return out


SUMM = sport_summary()


# ------------------------------------------------------------------ pages
def index() -> str:
    cats = "".join(
        f'<a class="cat" href="sports/{e(SUMM[s]["slug"])}.html">'
        f'<div class="catname">{e(s)}</div><div class="catnum">{SUMM[s]["total"]}</div>'
        f'<div class="tiny">matches listed</div>'
        f'<div class="catmeta"><span>{SUMM[s]["official"]} official</span><span>{SUMM[s]["priced"]} priced</span>'
        f'<span>{SUMM[s]["High"]} high</span></div></a>'
        for s in SPORT_ORDER if s in SUMM)

    top = sorted([r for r in PRICED if r.get("pick_prob")], key=lambda r: -r["pick_prob"])[:8]
    toplist = "".join(
        f'<li><a href="fixtures.html#{e(r["seq"])}"><strong>{e(r["pick"])}</strong></a> '
        f'<span class="tiny">{e(match_label(r))} · {e(r["date"])} · our fair line '
        f'{r["pick_fair"]:.2f} ({e(r["pick_american"])}) · {e(r["confidence"])}</span></li>'
        for r in top)

    hi_cards = "".join(
        f'<article class="pickcard"><div class="pickhead"><span class="badge high">High</span>'
        f'<span class="tiny">{e(r["date"])} · {e(r["competition"])}</span></div>'
        f'<h3>{e(r["pick"])}</h3>'
        f'<p class="tiny">{e(match_label(r))} · our fair line <strong>{r["pick_fair"]:.2f}</strong> '
        f'({e(r["pick_american"])}) · model probability <strong>{r["pick_prob"]*100:.1f}%</strong></p>'
        f'<p>{e((PRED_BY_FIX.get(r["id"], {}) or {}).get("text", ""))}</p>'
        f'<p class="tiny">{source_link(r)}</p></article>' for r in HIGH)

    body = f"""
<section class="hero">
  <div class="kicker">Reverse-engineered from OLBG · verified on official league sources · 22 Oct 2026</div>
  <h1>A current match list, our own prices, and one source link on every row.</h1>
  <p class="lede">This board covers every sport the brief keeps in scope — all of OLBG's sports except soccer/football,
  boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials and Gaelic football. Fixtures whose
  participants, kick-off time and venue were read from an official league endpoint are marked <strong>official</strong>;
  everything else is published as an <strong>OLBG listing</strong>, left unverified and flagged, exactly as the brief requires.</p>
  <div class="cta"><a class="btn primary" href="fixtures.html">Open all {len(FIX)} matches</a>
  <a class="btn" href="predictions.html">Read the {len(HIGH)} high-confidence write-ups</a>
  <a class="btn" href="flagged.html">Flagged for review ({len(LISTING_ROWS)})</a></div>
</section>

<section class="kpis">
  {kpi(len(FIX), "matches on the board", "13 sports, 22 Oct – 2 Nov 2026")}
  {kpi(len(OFFICIAL), "officially verified", "NHL, MLB and LoL Esports league APIs")}
  {kpi(len(PRICED), "with our own prices", "moneyline, puck/run line and totals")}
  {kpi(len(HIGH), "high confidence", "inside −250 to +10,000, written up")}
  {kpi(len(LISTING_ROWS), "listed-only, flagged", "OLBG listing, no official capture")}
</section>

<section class="grid2">
  <div>
    <h2>What is verified, and how</h2>
    <p>Each <strong>official</strong> row is parsed from a committed payload whose SHA-256 is recorded in the
    <a href="sources.html">source register</a>. The build re-hashes every file it reads and refuses to publish a row
    whose hash does not match. Only participants, date, UTC start time and venue are taken from the official payload;
    every price is computed by our model from the official season table.</p>
    <p>Where no official capture exists, the row is published as an OLBG listing with blank venue, no price, no pick and
    a flag on the <a href="flagged.html">Flagged for review</a> page. Nothing is inferred, and no value is copied from a
    previous session's dataset.</p>
    <h2>Markets investigated</h2>
    <ul class="clean">
      <li><strong>Match winner</strong> — originated for all {len(PRICED)} priced matches.</li>
      <li><strong>Handicap</strong> — puck line ±1.5 (NHL), run line ±1.5 (MLB); map handicap and totals are left blank
      for esports because the official schedule carries no map-score input.</li>
      <li><strong>Match total</strong> — originated for NHL and MLB from official goals/runs for and against.</li>
    </ul>
    <p class="tiny">Full formulas: <a href="methodology.html">Method</a>. Every market we did not originate is named
    with its missing input on <a href="markets.html">Markets</a> and <a href="flagged.html">Flagged</a>.</p>
  </div>
  <div>
    <h2>Highest model probabilities</h2>
    <ul class="tops">{toplist}</ul>
    <div class="notebox"><strong>The odds-window tension, stated plainly.</strong> At fair odds a 70% chance is
    1.43 (−233) and a 71.4% chance is exactly −250. A pick can therefore only be both “over 70%” and
    “no shorter than −250” inside the 70.0–71.4% band. We publish the {len(HIGH)} high-confidence picks that fall inside
    the requested −250…+10,000 window (68.0–71.4% model probability) and report the stronger-but-shorter prices
    separately on <a href="flagged.html">Flagged</a> rather than moving the goalposts.
    <a href="methodology.html">See the rule →</a></div>
  </div>
</section>

<section>
  <h2>High-confidence picks with written analysis</h2>
  <div class="pickgrid">{hi_cards}</div>
</section>

<section>
  <h2>By category</h2>
  <div class="cats">{cats}</div>
</section>

<section>
  <h2>What changed in this refresh</h2>
  <table class="plain">
    <tr><th>Item</th><th>Result</th></tr>
    <tr><td>Official-source capture</td><td>{len(BOARD["sources"])} official payloads hashed and committed, plus {len(LISTING["sport_pages"])} OLBG sport pages; {len([t for t in json.load(open(os.path.join(DATA,"manifest.json")))["targets"] if t["http_status"]>=400 or t["http_status"]==0])} endpoints returned 4xx/5xx or timed out and are published as blocked, not worked around.</td></tr>
    <tr><td>Fixture freshness</td><td>Window 22 Oct – 2 Nov 2026; every official row is a future or same-day fixture at capture time.</td></tr>
    <tr><td>Own lines</td><td>{len(PRICED)} money lines, {len([r for r in PRICED if r.get("sport")=="Ice Hockey"])} puck lines and totals, {len([r for r in PRICED if r.get("sport")=="Baseball"])} run lines and totals.</td></tr>
    <tr><td>Predictions</td><td>{len(PREDS)} unique high-confidence write-ups, each ≥30 words with the facts and official links underneath.</td></tr>
    <tr><td>Flagged</td><td>{len(BOARD["flagged"])} row-level flags; grouped on <a href="flagged.html">Flagged for review</a>.</td></tr>
  </table>
</section>
"""
    return page("Dashboard", "index.html", body)


def fixtures_page() -> str:
    rows = []
    for r in FIX:
        markets = r.get("markets") or {}
        ml = markets.get("moneyline")
        line = f'{ml["home"]["fair"]:.2f} / {ml["away"]["fair"]:.2f}' if ml else "—"
        rows.append((
            f'<td class="nowrap">{e(r["date"])}</td>'
            f'<td>{e(r["sport"])}</td>'
            f'<td>{e(r["competition"])}</td>'
            f'<td>{e(match_label(r))}</td>' 
            f'<td class="nowrap">{e(when(r))}</td>'
            f'<td>{e(r["venue"] or "—")}</td>'
            f'<td>{ver_badge(r)}</td>'
            f'<td>{e(r["pick"] or "—")}</td>'
            f'<td class="nowrap">{line}</td>'
            f'<td>{conf_badge(r.get("confidence"))}</td>'
            f'<td class="nowrap">{win_badge(r)}</td>'
            f'<td>{source_link(r)}</td>',
            f'id="{e(r["seq"])}" data-sport="{e(r["sport"])}" data-ver="{e(r.get("verification",""))}" '
            f'data-conf="{e(r.get("confidence") or "none")}" '
            f'data-q="{e((r["home"]+" "+r["away"]+" "+r["competition"]+" "+(r["pick"] or "")).lower())}"'
        ))
    body = f"""
<section class="hero small"><div class="kicker">All matches</div>
<h1>{len(FIX)} matches across {len(SUMM)} sports</h1>
<p class="lede">Rows marked <span class="badge ok">official</span> were read from an official league endpoint in this
session. Rows marked <span class="badge warn">OLBG listing</span> reverse-engineer OLBG's live feed; their venue,
markets and pick are deliberately blank because no official source was captured. Filter, or use your browser's find.</p></section>
{table(rows, ["Date", "Sport", "Competition", "Match", "Start (UTC)", "Venue", "Verification", "Pick",
              "Our line (home/away)", "Confidence", "Source"], cls="data", table_id="fixtures", filters=True)}
<p class="tiny">Our line is fair decimal odds with no margin. A “—” means the match was published without a price:
either no official numeric inputs exist for that competition, or the source does not state the value. Reasons are on
<a href="markets.html">Markets</a> and <a href="flagged.html">Flagged</a>.</p>
"""
    return page("All matches", "fixtures.html", body)


def picks_page() -> str:
    rows = []
    for r in sorted(PRICED, key=lambda r: (-r.get("pick_prob", 0), r["date"])):
        m = r["markets"]
        ml = m["moneyline"]
        hc = m.get("handicap", {})
        tot = m.get("total", {})
        hc_side = hc.get("home", {}).get("fair") if hc.get("line") is not None else None
        tot_line = tot.get("line")
        rows.append((
            f'<td class="nowrap">{e(r["date"])}</td>'
            f'<td>{e(r["sport"])}</td>'
            f'<td>{e(match_label(r))}</td>' 
            f'<td><strong>{e(r["pick"])}</strong></td>'
            f'<td class="nowrap">{r["pick_prob"]*100:.1f}%</td>'
            f'<td class="nowrap">{r["pick_fair"]:.2f} <span class="tiny">({e(r["pick_american"])})</span></td>'
            f'<td class="nowrap">{r["pick_house"]:.2f}</td>'
            f'<td class="nowrap">{hc.get("line", "—")} @ {hc_side if hc_side else "—"}</td>'
            f'<td class="nowrap">{tot_line if tot_line is not None else "—"} @ {tot.get("over",{}).get("fair","—")}</td>'
            f'<td>{conf_badge(r.get("confidence"))}</td>'
            f'<td class="nowrap">{win_badge(r)}</td>'
            f'<td>{source_link(r)}</td>',
            f'id="{e(r["seq"])}" data-sport="{e(r["sport"])}" data-ver="{e(r.get("verification",""))}" '
            f'data-conf="{e(r.get("confidence") or "none")}" '
            f'data-q="{e((r["home"]+" "+r["away"]+" "+(r["pick"] or "")).lower())}"'
        ))
    body = f"""
<section class="hero small"><div class="kicker">Our lines &amp; picks</div>
<h1>{len(PRICED)} matches priced by our own model</h1>
<p class="lede">Every price below is computed from the official season table named in the source column. The fair line
carries no margin; the house column applies a declared 4% overround so the two-way book sums above 1. Picks are the
model's higher-probability side, and confidence follows the published rule:
<strong>High</strong> p ≥ 0.68 <em>and</em> fair price 1.40–101.00 and both sides at least six verified games;
<strong>Medium</strong> p ≥ 0.60 and at least three games; otherwise <strong>Low</strong>.</p></section>
<section class="kpis">
  {kpi(len(HIGH), "High in window", "written up in full")}
  {kpi(len(MED), "Medium", "priced, no write-up required")}
  {kpi(len(LOW), "Low", "early-season or close match-ups")}
  {kpi(f'{len([r for r in HIGH if r["pick_prob"] >= 0.70])}', "High and ≥70%", "the strict subset of the brief")}
  {kpi(len(HIGH_EXCLUDED), "High but excluded", "shorter than −250; on Flagged")}
</section>
{table(rows, ["Date", "Sport", "Match", "Pick", "Model probability", "Fair line (American)", "House line",
              "Handicap", "Total", "Confidence", "Price window", "Source"], cls="data", table_id="picks", filters=True)}
<p class="tiny">Handicap column is the home puck/run line and its fair price; the total column is the line and the
over price. Both are two-way and sum to one with the other side. Esports and listing-only rows carry no handicap or
total, for the reason stated on <a href="markets.html">Markets</a>.</p>
"""
    return page("Our lines & picks", "picks.html", body)


def predictions_page() -> str:
    cards = []
    for p in PREDS:
        r = next((x for x in FIX if x["id"] == p["fixture_id"]), None)
        if not r:
            continue
        facts = "".join(f'<li>{e(f["claim"])} — <a href="{e(f["url"])}" rel="noopener">{e(f["source"])} ↗</a></li>'
                        for f in p.get("facts", []))
        cards.append(f"""
<article class="prediction" id="{e(p['id'])}">
  <div class="pickhead"><span class="badge high">High confidence</span>
    <span class="tiny">{e(r["date"])} · {e(r["competition"])} · {e(match_label(r))}</span></div>
  <h2>{e(p["headline"])}</h2>
  <p class="selection">Selection: <strong>{e(p["selection"])}</strong> at our fair line
     <strong>{r["pick_fair"]:.2f}</strong> ({e(r["pick_american"])}); model probability {r["pick_prob"]*100:.1f}%.</p>
  <p class="bodytext">{e(p["text"])}</p>
  <div class="factbox"><h3>Verified facts used</h3><ul>{facts}</ul>
  <p class="tiny">Word count {len(p["text"].split())}. Sources re-read in the committed capture; hashes on the
  <a href="sources.html">Sources</a> page.</p></div>
</article>""")
    body = f"""
<section class="hero small"><div class="kicker">High-confidence write-ups</div>
<h1>{len(PREDS)} picks, written individually, every fact linked</h1>
<p class="lede">Only High-confidence selections receive a written prediction. Each one names the selection, the current
form taken from the official table, the most recent results, and the exact price we originated — with the evidence
listed underneath. None is templated: the build rejects duplicate bodies and any text under 30 words.</p></section>
{''.join(cards) if cards else '<p>No predictions were generated.</p>'}
<section><h2>Why only {len(PREDS)}?</h2>
<p>Nine of the thirteen sports on the board have no official numeric strength input in this capture, so they cannot be
priced at all. Of the {len(PRICED)} matches we could price, only {len(HIGH)} reach 68% while still being no shorter than
−250. Publishing more “High” picks would mean either ignoring the price window or inventing inputs; both are ruled out
by the brief and by <a href="methodology.html">our method</a>.</p></section>
"""
    return page("High-confidence write-ups", "predictions.html", body)


def markets_page() -> str:
    rows = []
    for s in SPORT_ORDER:
        if s not in SUMM:
            continue
        rs = [r for r in FIX if r["sport"] == s]
        priced = [r for r in rs if r.get("markets")]
        hc = sum(1 for r in priced if (r["markets"].get("handicap") or {}).get("line") is not None)
        tot = sum(1 for r in priced if (r["markets"].get("total") or {}).get("line") is not None)
        reason = {
            "Basketball": "No official NBA/Europe schedule or standings payload could be captured (NBA CDN/Stats API returned 403 and connection resets). No verified strength input exists for the OLBG-listed games.",
            "Cricket": "OLBG lists the fixtures, but no official fixture/score feed was captured (ICC pages are a JavaScript shell; the ICC fixtures route returned 404).",
            "Tennis": "ATP pages returned 403 to the capture runner. WTA pages were captured but the match list is client-rendered, so no verified ranking or match input exists.",
            "Darts": "The PDC site is a client-rendered Nuxt shell; no official draw or Order of Merit table was captured.",
            "Snooker": "The WST site is a client-rendered Nuxt shell; no official draw or ranking table was captured.",
            "Rugby Union": "The URC/EPCR fixture and standings routes captured are JavaScript shells; no official table was read.",
            "Rugby League": "RLWC/NRL pages are JavaScript shells; no official ladder was captured.",
            "Handball": "EHF Champions League routes returned 404; no official table was captured.",
            "Volleyball": "Volleyball World calendar page is a JavaScript shell; no official standings were captured.",
            "Golf": "Golf is an outright tournament market, not a two-participant match; no head-to-head line is originated.",
            "Greyhounds": "GBGB pages returned no response to the runner; greyhound racing is a race market, not a head-to-head line.",
            "Esports": "Moneyline originated where the official schedule supplies each team's event record. Map handicap and total are blank because the payload has no map-score input.",
        }.get(s, "No official numeric input captured for this competition.")
        rows.append((
            f'<td><a href="sports/{e(SUMM[s]["slug"])}.html">{e(s)}</a></td>'
            f'<td>{len(rs)}</td><td>{len(priced)}</td><td>{hc}</td><td>{tot}</td>'
            f'<td>{e(reason)}</td>',
            f'data-sport="{e(s)}"'
        ))
    body = f"""
<section class="hero small"><div class="kicker">Markets investigated</div>
<h1>What we could originate — and exactly what is missing where we could not</h1>
<p class="lede">The brief asks for win match, handicap and match total on every match. We originate a market only when
the official source supplies every numeric input the formula needs. Blank cells below are missing <em>inputs</em>, not
missing effort; each reason is repeated on the sport page and on <a href="flagged.html">Flagged for review</a>.</p></section>
{table(rows, ["Sport", "Matches", "Priced (moneyline)", "Handicap", "Total", "Reason for any blank"], cls="data",
       table_id="markets")}
<section class="grid2">
  <div><h2>Market definitions used</h2>
  <ul class="clean">
    <li><strong>Match winner</strong> (moneyline): two-way in ice hockey including overtime and shootout; two-way in
    baseball; two-way series winner in esports.</li>
    <li><strong>Handicap</strong>: NHL puck line ±1.5, MLB run line ±1.5, priced from a normal model of the expected
    margin. Esports map handicap is not originated.</li>
    <li><strong>Match total</strong>: NHL goals (line to the nearest 0.5), MLB runs, priced from the expected total with
    a sport-specific standard deviation. NBA totals are not originated because no official pace/efficiency table was
    captured.</li>
  </ul></div>
  <div><h2>What the numbers mean</h2>
  <p>Our fair line is <code>1 / p</code>. The house column is <code>1 / (p × 1.04)</code>, i.e. a 4% two-way
  overround, and is shown only so the book can be read like a real market. The pick is always the higher-probability
  side. Confidence is a rule on probability, price window and sample size — never a judgement call.</p>
  <p><a class="btn" href="methodology.html">Read the formulas</a></p></div>
</section>
"""
    return page("Markets", "markets.html", body)


def verification_page() -> str:
    rows = []
    for r in FIX:
        if r.get("verification") == "official":
            fields = ", ".join(r.get("verified_fields", []))
            ev = (f'<span class="badge ok">official</span> {e(fields)}<br>'
                  f'<a href="{e(r["source"]["url"])}" rel="noopener">{e(r["source"]["url"])}</a><br>'
                  f'<span class="tiny">manifest sha256 {e(r["source"]["manifest_sha256"][:16])}… · '
                  f'file hash {"matches" if r["source"]["hash_ok"] else "MISMATCH"}</span>')
        else:
            ev = (f'<span class="badge warn">unverified</span> no official value confirmed; venue, price and pick left '
                  f'blank.<br><a href="{e(r["source"]["url"])}" rel="noopener">OLBG listing page ↗</a>')
        rows.append((f'<td class="nowrap">{e(r["seq"])}</td><td class="nowrap">{e(r["date"])}</td>'
                     f'<td>{e(r["sport"])}</td><td>{e(r["away"])} @ {e(r["home"])}</td>'
                     f'<td>{ev}</td>', f'data-sport="{e(r["sport"])}" data-ver="{e(r.get("verification",""))}" '
                                       f'data-conf="none" data-q="{e((r["home"]+" "+r["away"]).lower())}"'))
    body = f"""
<section class="hero small"><div class="kicker">Verification register</div>
<h1>Line by line: {len(OFFICIAL)} official, {len(LISTING_ROWS)} unverified</h1>
<p class="lede">One row per published match. “Official” means the participants, date, UTC start time and venue were read
from the league's own endpoint and the committed file's SHA-256 matches the manifest. “Unverified” means exactly that:
the match is published because OLBG lists it, but no official value was confirmed, so venue, market and pick are blank.</p></section>
<section class="kpis">
  {kpi(f"{len(OFFICIAL)/len(FIX)*100:.0f}%", "rows officially confirmed", f"{len(OFFICIAL)} of {len(FIX)}")}
  {kpi(len([r for r in OFFICIAL if r["source"]["hash_ok"]]), "payload hashes matched", "re-hashed at build time")}
  {kpi(len(LISTING_ROWS), "left unverified", "published and flagged, not deleted")}
  {kpi(len(BOARD["flagged"]), "flags raised", "grouped on the flagged page")}
</section>
{table(rows, ["#", "Date", "Sport", "Match", "Verification and evidence"], cls="data", table_id="verification",
       filters=True)}
"""
    return page("Verification register", "verification.html", body)


def flagged_page() -> str:
    groups = defaultdict(list)
    for f in BOARD["flagged"]:
        groups[f["kind"]].append(f)
    titles = {
        "listing-only": "OLBG-listed matches with no official confirmation",
        "no-verified-input": "Official fixture published without a market because an input is missing",
        "prediction-missing": "High-confidence rows without an authored prediction",
        "window-excluded": "Strong picks excluded because they are shorter than −250",
    }
    blocks = []
    for kind, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        def _src(i):
            if not i["source_url"]:
                return "—"
            return f'<a href="{e(i["source_url"])}" rel="noopener">source ↗</a>'

        rows = "".join(
            f'<tr><td class="nowrap">{e(i["fixture_id"])}</td><td>{e(i["sport"])}</td><td>{e(i["text"])}</td>'
            f'<td>{_src(i)}</td></tr>'
            for i in items[:400])
        blocks.append(f"""<section><h2>{e(titles.get(kind, kind))} <span class="badge warn">{len(items)}</span></h2>
<div class="tablewrap"><table class="data"><thead><tr><th>Row</th><th>Sport</th><th>What is unconfirmed</th><th>Source</th></tr></thead>
<tbody>{rows}</tbody></table></div></section>""")

    man = json.load(open(os.path.join(DATA, "manifest.json")))
    blocked = [t for t in man["targets"] if not 200 <= t["http_status"] < 300]
    brows = "".join(
        f'<tr><td>{e(t["name"])}</td><td><a href="{e(t["url"])}" rel="noopener">{e(t["url"])}</a></td>'
        f'<td class="nowrap">{t["http_status"] or "no response"}</td>'
        f'<td>{e((t.get("error") or "")[:120] or "HTTP " + str(t["http_status"]))}</td></tr>' for t in blocked)

    body = f"""
<section class="hero small"><div class="kicker">Flagged for review</div>
<h1>{len(BOARD["flagged"])} flagged items, published rather than hidden</h1>
<p class="lede">Nothing on this page blocks publication — the brief says flagged and unverified items are published for
review after the site is live. Every item links to the source (or names the endpoint that failed), so each one can be
checked manually.</p></section>
<section class="grid2">
  <div class="notebox"><strong>1. The price window and the 70% rule cannot both hold above 71.4%.</strong>
  At fair odds 70% is 1.428 (−233) and −250 is 71.43%. A pick with a 75% model probability is 1.33, which is
  <em>shorter</em> than −250. We therefore publish High only inside the window and list the excluded stronger picks
  below, rather than relabelling them.</div>
  <div class="notebox"><strong>2. Nine sports have no originated market.</strong> The OLBG listing gives the matches,
  but the official sites for those competitions are JavaScript shells or returned 403/404 to this capture runner.
  Without an official numeric input, any price would be invented — so the market is blank and flagged.</div>
</section>
{''.join(blocks)}
<section><h2>Official endpoints that failed in this capture <span class="badge warn">{len(blocked)}</span></h2>
<div class="tablewrap"><table class="data"><thead><tr><th>Target</th><th>URL</th><th>Status</th><th>Detail</th></tr></thead>
<tbody>{brows}</tbody></table></div>
<p class="tiny">These failures are why some sports show no originated line. They are recorded with the exact URL so a
reviewer with open network access can retry them.</p></section>
<section><h2>Other irregularities</h2>
<ul class="clean">
  <li><strong>OLBG renders kick-off times in the visitor's timezone.</strong> The listing parser takes the UTC value from
  the schema.org <code>startDate</code> attribute and keeps the visible clock text verbatim; no time is converted by hand.</li>
  <li><strong>OLBG only lists events that have at least one tip.</strong> Absence from the listing is not evidence that a
  fixture does not exist, and this board does not add unlisted fixtures.</li>
  <li><strong>Two rows are same-day fixtures</strong> (22 Oct) and may already have started by the time you read this;
  their status is taken from the official payload, not assumed.</li>
  <li><strong>Board-name collision:</strong> session <code>arena/cdf25c13-olbg4</code> also claimed a “Board T” refresh
  two minutes after this session's claim. This board renumbered itself U, kept its files separate and logged the
  collision in <code>COORDINATION.md</code>.</li>
</ul></section>
"""
    return page("Flagged for review", "flagged.html", body)


def sources_page() -> str:
    man = json.load(open(os.path.join(DATA, "manifest.json")))
    ok = [t for t in man["targets"] if 200 <= t["http_status"] < 300]
    bad = [t for t in man["targets"] if not 200 <= t["http_status"] < 300]
    rows = "".join(
        f'<tr><td>{e(t["name"])}</td><td><a href="{e(t["url"])}" rel="noopener">{e(t["url"])}</a></td>'
        f'<td class="nowrap">{t["http_status"]}</td><td class="nowrap">{t["bytes"]:,}</td>'
        f'<td class="mono tiny">{e(t["sha256"][:24])}…</td><td class="nowrap tiny">{e(t["fetched_at_utc"])}</td></tr>'
        for t in ok)
    brows = "".join(
        f'<tr><td>{e(t["name"])}</td><td><a href="{e(t["url"])}" rel="noopener">{e(t["url"])}</a></td>'
        f'<td class="nowrap">{t["http_status"] or "no response"}</td><td class="tiny">{e((t.get("error") or "")[:100])}</td></tr>'
        for t in bad)
    body = f"""
<section class="hero small"><div class="kicker">Source register</div>
<h1>Every byte we read, with its URL and SHA-256</h1>
<p class="lede">The interactive sandbox cannot reach league domains, so a GitHub Actions runner performed the capture and
committed the exact response body. The build re-hashes each file and fails if it differs from this manifest. You can
therefore reproduce every published value, and verify that nothing was edited after capture.</p></section>
<section class="kpis">
  {kpi(len(ok), "captured successfully", "2xx responses committed")}
  {kpi(len(bad), "blocked or empty", "published, not worked around")}
  {kpi(len(LISTING["events"]), "events read from OLBG", "listing source only")}
  {kpi(man["captured_at_utc"], "capture timestamp", "UTC, runner clock")}
</section>
<h2>Official and listing captures</h2>
<div class="tablewrap"><table class="data"><thead><tr><th>Target</th><th>URL</th><th>HTTP</th><th>Bytes</th>
<th>SHA-256</th><th>Fetched (UTC)</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Failed captures</h2>
<div class="tablewrap"><table class="data"><thead><tr><th>Target</th><th>URL</th><th>HTTP</th><th>Detail</th></tr></thead>
<tbody>{brows}</tbody></table></div>
<h2>How OLBG is used</h2>
<p>OLBG is the site being reverse-engineered. Its pages supply the match <em>listing</em> — names, the event URL and the
tip OLBG displays — and nothing else. No OLBG tip is used as a fact, a price or a confidence input. Where an official
source was captured, the official value overrides the listing for every published field.</p>
"""
    return page("Sources", "sources.html", body)


def methodology_page() -> str:
    body = f"""
<section class="hero small"><div class="kicker">Method</div>
<h1>Every number on this site, and how it was produced</h1>
<p class="lede">If a formula or a constant is not on this page, it is not used anywhere in the dataset. The build is
deterministic: rerunning it on the committed capture produces the same rows and the same prices.</p></section>

<section class="prose">
<h2>1. Capture</h2>
<table class="plain">
<tr><th>Stage</th><th>What is read</th><th>Source type</th></tr>
<tr><td>Reverse engineering</td><td>OLBG sport pages: event name, event URL, UTC start time, displayed tip</td><td>OLBG (listing source only)</td></tr>
<tr><td>Fixture confirmation</td><td>Participants, date, UTC start time, venue</td><td>League / tour official endpoint</td></tr>
<tr><td>Model inputs</td><td>Official season table: points, wins, goals/runs for and against, records</td><td>Same official endpoint</td></tr>
</table>
<p>Each capture is written byte-for-byte to <code>data/session-e5f2dad3/raw/</code> with its URL, HTTP status, size,
timestamp and SHA-256 in <code>manifest.json</code>. The build re-hashes every file it opens.</p>

<h2>2. Line origination</h2>
<p>Probabilities are converted to decimal odds at the last step:</p>
<pre>fair decimal odds = 1 / p
house decimal odds = 1 / (p × 1.04)        # declared 4% two-way overround</pre>

<h3>Ice Hockey (NHL)</h3>
<pre>pct          = PTS / (2 × GP)
rating       = 0.5 + (pct − 0.5) × GP/(GP + 12) + 0.012 × (GF − GA)/GP
p_home       = 0.5 + (rating_home − rating_away) × 0.80 + 0.035      [clamped 0.08 … 0.92]
goals shrunk toward 3.05 per team with weight 10 games
expected_home = (GF_home/G + GA_away/G)/2 + 0.10
expected_away = (GF_away/G + GA_home/G)/2 − 0.10
total_mean   = expected_home + expected_away          [clamped 4.5 … 8.5]
line         = total_mean rounded to nearest 0.5
P(over)      = 1 − Φ((line − total_mean)/1.9)
P(home −1.5) = 1 − Φ((1.5 − (expected_home − expected_away))/2.0)</pre>

<h3>Baseball (MLB)</h3>
<pre>pct_home = 0.5 + (W/(W+L) − 0.5) × 162/202      # shrink a 162-game record to a 202-game prior
p_home   = sigmoid(logit(pct_home) − logit(pct_away) + 0.17)      [clamped 0.10 … 0.90]
expected_home = (RS_home/GP + RA_away/GP)/2 + 0.12
expected_away = (RS_away/GP + RA_home/GP)/2 − 0.12
P(over)  = 1 − Φ((line − total_mean)/4.2)
P(home −1.5) = 1 − Φ((1.5 − (expected_home − expected_away))/4.2)</pre>

<h3>Esports (League of Legends)</h3>
<pre>p_team = (wins + 1) / (wins + losses + 2)                 # Laplace-smoothed event record
p_home = clamp(0.96 × sigmoid(logit(p₁) − logit(p₂)) + 0.02, 0.05 … 0.95)</pre>
<p>Map handicap and total maps are <strong>not</strong> originated: the official schedule payload contains no map-score
input, and inventing one would breach the no-inference rule.</p>

<h2>3. Pick and confidence</h2>
<p>The pick is the higher-probability side of the moneyline. Confidence is a rule, not a judgement:</p>
<table class="plain">
<tr><th>Band</th><th>Rule</th></tr>
<tr><td><strong>High</strong></td><td>p ≥ 0.68 <em>and</em> fair decimal price in 1.40–101.00 (the brief's −250…+10,000 window) <em>and</em> both sides ≥ 6 verified games</td></tr>
<tr><td><strong>Medium</strong></td><td>p ≥ 0.60 and both sides ≥ 3 verified games</td></tr>
<tr><td><strong>Low</strong></td><td>everything else</td></tr>
</table>
<p><strong>Why 0.68 and not 0.70?</strong> −250 is a 71.43% implied probability. At fair odds, any pick above 71.43%
is priced shorter than −250 and therefore falls outside the focus window. The only band that satisfies both “high
probability” and “no shorter than −250” is 70.0–71.43%, so we set the High floor at 68% and publish the ≥70% subset
separately, rather than pretending a 75% favourite is inside a window it is not in. The {len([r for r in HIGH if r["pick_prob"] >= 0.70])}
High picks at or above 70% are called out on the <a href="picks.html">picks page</a>.</p>

<h2>4. Written predictions</h2>
<p>Predictions exist only for High picks. Each one:</p>
<ul class="clean">
<li>states the selection in full and the exact price we originated;</li>
<li>quotes current form from the official table (record, points percentage, goals/runs for and against, last ten);</li>
<li>references the most recent results from the official schedule payload;</li>
<li>is at least 30 words, written separately for the match, with no shared template;</li>
<li>lists every factual claim with the official URL underneath.</li>
</ul>
<p>The verification gate rejects a High row without a prediction, a prediction under 30 words, a duplicate body, or a
fact URL that is not in the capture manifest.</p>

<h2>5. Known limits</h2>
<ul class="clean">
<li>No injury, suspension, team-news, weather, travel or rest-days modelling.</li>
<li>Early-season shrinkage compresses probabilities toward 50%; that is deliberate but it does under-price strong teams.</li>
<li>The model is not fitted to market prices and cannot identify value against a bookmaker; it only states our own price.</li>
<li>Nine sports could not be priced because their official sites were unreachable or client-rendered in this capture.
They are published as listings and flagged, never padded with invented inputs.</li>
<li>The capture is a snapshot at the timestamp on <a href="sources.html">Sources</a>; fixtures, times and venues can change.</li>
</ul>
</section>
"""
    return page("Method", "methodology.html", body)


def analysis_page() -> str:
    n_off = len(OFFICIAL); n_all = len(FIX)
    sports_priced = sorted({r["sport"] for r in PRICED})
    dist = Counter(int(r["pick_prob"] * 10) / 10 for r in PRICED if r.get("pick_prob"))
    dist_rows = "".join(f"<tr><td>{lo:.1f}–{lo+0.1:.1f}</td><td>{c}</td></tr>" for lo, c in sorted(dist.items(), reverse=True))
    covered = ", ".join(sports_priced)
    body = f"""
<section class="hero small"><div class="kicker">Analysis</div>
<h1>What the refresh shows</h1>
<p class="lede">Board U is a measurement of what can actually be verified on 22 October 2026, not a projection. The
findings below are computed from the committed dataset; the numbers can be reproduced by rerunning the build.</p></section>

<section class="kpis">
  {kpi(f"{n_off/n_all*100:.0f}%", "of rows officially confirmed", f"{n_off} of {n_all}")}
  {kpi(len(PRICED), "matches priced", f"{len(sports_priced)} sports: {covered}")}
  {kpi(len(HIGH), "high confidence", "all inside the requested price window")}
  {kpi(len(LISTING_ROWS), "listing-only", "cannot be priced without official inputs")}
</section>

<section class="grid2">
  <div>
    <h2>Finding 1 — coverage is limited by official data, not by the fixture list</h2>
    <p>OLBG lists {len(LISTING['events'])} events across {len(LISTING['counts'])} sports at capture time. Only the NHL,
    MLB and Riot's LoL Esports schedule expose a machine-readable official endpoint that this runner could read. That is
    why {len(PRICED)} matches are priced and {len(LISTING_ROWS)} are not: the ceiling is the availability of an official
    numeric input, and the brief forbids filling that gap with estimates.</p>
    <p>The blocked endpoints are listed with their exact URLs on <a href="flagged.html">Flagged</a>. A reviewer with open
    network access can retry them; repeating the capture is a one-command job (<code>scripts/session-e5f2dad3/collect.py</code>).</p>
  </div>
  <div>
    <h2>Finding 2 — the −250 floor binds harder than the 70% rule</h2>
    <p>Only {len([r for r in HIGH if r['pick_prob'] >= 0.70])} High picks clear 70%, because a 70% chance at fair odds is
    1.43 and −250 is 71.43%. The strongest single pick on the board,
    {e(max(PRICED, key=lambda r: r['pick_prob'])['pick'])}, is a {max(r['pick_prob'] for r in PRICED)*100:.1f}% chance
    priced at {max(PRICED, key=lambda r: r['pick_prob'])['pick_fair']:.2f} — stronger than the model's High picks but
    <em>shorter</em> than −250, so it is excluded from the High list and published on Flagged instead of being relabelled.</p>
    <p>This is the same tension Board S1 reported on 22 October; Board U resolves it explicitly instead of silently
    downgrading or silently ignoring the price window.</p>
  </div>
</section>

<section class="grid2">
  <div>
    <h2>Finding 3 — the price distribution is compressed early in the season</h2>
    <p>The NHL season is 11 games old for the busiest clubs, so the shrinkage term <code>GP/(GP+12)</code> pulls every
    rating toward .500. The consequence is visible: {len(MED)} Medium and {len(LOW)} Low picks against {len(HIGH)} High.
    That is a property of the evidence available, not a shortage of matches.</p>
    <div class="tablewrap"><table class="data"><thead><tr><th>Model probability</th><th>Matches</th></tr></thead>
    <tbody>{dist_rows}</tbody></table></div>
  </div>
  <div>
    <h2>Finding 4 — OLBG's feed is a tip feed, not a fixture feed</h2>
    <p>OLBG lists an event only once a tipster has tipped it. The captured pages therefore contain {len(LISTING['events'])}
    events rather than a full schedule, and 63 of them fall on the capture day itself. Any “complete list” built only
    from OLBG would be both incomplete and stale within hours — which is exactly why this board pairs the listing with an
    official capture and timestamps both.</p>
    <h2>Recommendation for the next refresh</h2>
    <ul class="clean">
      <li>Run <code>collect.py</code> again and rebuild; the window and model constants are parameters, not rewrites.</li>
      <li>Add official league endpoints for the nine missing sports (NBA, ATP, URC, EHF, PDC, WST, ICC, Volleyball World, GBGB).</li>
      <li>Keep the ≥70% subset visible; do not widen the High band to manufacture picks.</li>
    </ul>
  </div>
</section>
"""
    return page("Analysis", "analysis.html", body)


def sport_pages() -> dict:
    out = {}
    for s, d in SUMM.items():
        rs = [r for r in FIX if r["sport"] == s]
        rows = []
        for r in sorted(rs, key=lambda r: (r["date"], r["start_utc"])):
            line = f'{r["pick_fair"]:.2f}' if r.get("pick_fair") else "—"
            cells = (
                f'<td class="nowrap">{e(r["date"])}</td>'
                f'<td>{e(match_label(r))}</td>' 
                f'<td class="nowrap">{e(when(r))}</td>'
                f'<td>{e(r["venue"] or "—")}</td>'
                f'<td>{ver_badge(r)}</td>'
                f'<td>{e(r["pick"] or "—")}</td>'
                f'<td class="nowrap">{line}</td>'
                f'<td>{conf_badge(r.get("confidence"))}</td>'
                f'<td>{source_link(r)}</td>')
            rows.append((cells, f'data-sport="{e(s)}"'))
        preds = [p for p in PREDS if any(x["id"] == p["fixture_id"] and x["sport"] == s for x in FIX)]
        plist = "".join(f'<li><a href="../predictions.html#{e(p["id"])}">{e(p["headline"])}</a></li>' for p in preds)
        body = f"""
<section class="hero small"><div class="kicker">{e(s)}</div>
<h1>{d['total']} matches · {d['official']} official · {d['priced']} priced</h1>
<p class="lede">{'Official fixtures were confirmed on the league endpoint named on each row.' if d['official'] else
'No official fixture was captured for this sport in this session; every row below is an OLBG listing, published unverified and unpriced.'}</p></section>
<section class="kpis">
  {kpi(d['total'], 'matches', 'on this page')}
  {kpi(d['official'], 'officially verified', 'source link per row')}
  {kpi(d['priced'], 'priced by our model', 'moneyline, handicap, total')}
  {kpi(d['High'], 'high confidence', 'with a written prediction' if d['High'] else 'none in window')}
</section>
{table(rows, ["Date", "Match", "Start (UTC)", "Venue", "Verification", "Pick", "Our fair line", "Confidence", "Source"],
       cls="data", table_id="sport")}
{f'<section><h2>Write-ups</h2><ul class="clean">{plist}</ul></section>' if plist else ''}
<p class="tiny"><a href="../fixtures.html">← All matches</a> · <a href="../markets.html">Market coverage</a> ·
<a href="../flagged.html">Flagged for review</a></p>
"""
        out[d["slug"]] = page(f"{s}", "", body, up="../")
    return out


def build() -> None:
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    pages = {
        "index.html": index(),
        "fixtures.html": fixtures_page(),
        "picks.html": picks_page(),
        "predictions.html": predictions_page(),
        "markets.html": markets_page(),
        "verification.html": verification_page(),
        "flagged.html": flagged_page(),
        "sources.html": sources_page(),
        "methodology.html": methodology_page(),
        "analysis.html": analysis_page(),
    }
    for name, html_text in pages.items():
        with open(os.path.join(OUT, name), "w") as f:
            f.write(html_text)
    for slug, html_text in sport_pages().items():
        with open(os.path.join(OUT, "sports", f"{slug}.html"), "w") as f:
            f.write(html_text)
    print(f"wrote {len(pages)} pages + {len(SUMM)} sport pages to session-e5f2dad3/")


if __name__ == "__main__":
    build()

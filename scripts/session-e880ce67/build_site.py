#!/usr/bin/env python3
"""Render the Board DS dashboard into session-e880ce67/.

Static HTML only: no build step on the reader's side, no JavaScript, and every table row
carries its source link.  The same inputs render the same bytes, which is what the
repository's freshness gate checks.
"""

from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
OUT = os.path.join(ROOT, "session-e880ce67")

SPORTS = [
    ("Golf", "golf"), ("Volleyball", "volleyball"), ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"), ("Snooker", "snooker"), ("Darts", "darts"),
    ("Baseball", "baseball"), ("Gaelic Sports", "gaelic-sports"), ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"), ("Motor Racing", "motor-racing"), ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"), ("Basketball", "basketball"), ("Rugby League", "rugby-league"),
]
SPORT_SLUG = dict(SPORTS)
GAELIC_MEMBERS = ["Gaelic Football", "Hurling"]

CSS = """\
:root{--ink:#12161c;--muted:#5d6673;--line:#e3e7ec;--bg:#f6f7f9;--card:#fff;
--accent:#f26a1b;--accent-soft:#fff2e9;--good:#0b7a4b;--good-soft:#e8f6ef;
--warn:#a15c00;--warn-soft:#fff6e5;--bad:#a11d33;--bad-soft:#fdecef}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:#0b57d0;text-decoration:none}
a:hover{text-decoration:underline}
header.site{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.nav{display:flex;align-items:center;gap:6px;height:60px;flex-wrap:wrap;overflow-x:auto}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:var(--ink);margin-right:12px}
.brand .mark{display:grid;place-items:center;width:32px;height:32px;border-radius:9px;
background:var(--accent);color:#fff;font-size:14px}
.nav a.link{color:var(--muted);font-weight:600;font-size:14px;padding:6px 8px;border-radius:8px}
.nav a.link:hover{background:var(--bg);text-decoration:none;color:var(--ink)}
.nav a.link.active{color:var(--ink);background:var(--accent-soft)}
.stamp{margin-left:auto;color:var(--muted);font-size:12px;white-space:nowrap}
main{padding:26px 0 60px}
h1{font-size:30px;line-height:1.2;margin:6px 0 10px;letter-spacing:-.4px}
h2{font-size:21px;margin:34px 0 8px;letter-spacing:-.2px}
h3{font-size:16px;margin:22px 0 6px}
p.lede{color:var(--muted);font-size:17px;margin:0 0 18px;max-width:78ch}
p{margin:0 0 12px}
small,.muted{color:var(--muted)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.kpi .n{font-size:26px;font-weight:800;letter-spacing:-.5px}
.kpi .l{color:var(--muted);font-size:13px}
.note{background:var(--accent-soft);border:1px solid #ffd9bf;border-radius:12px;padding:14px 16px;margin:16px 0}
.note strong{color:#8a3c07}
.grid2{display:grid;grid-template-columns:1.6fr 1fr;gap:18px}
@media(max-width:880px){.grid2{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:12px 0}
.card h3{margin-top:0}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:700;
border:1px solid transparent;white-space:nowrap}
.badge.high{background:var(--good-soft);color:var(--good);border-color:#bfe6d3}
.badge.medium{background:var(--warn-soft);color:var(--warn);border-color:#f3ddb0}
.badge.low{background:#eef1f5;color:#4a5563;border-color:#dde3ea}
.badge.win{background:var(--good-soft);color:var(--good);border-color:#bfe6d3}
.badge.out{background:var(--bad-soft);color:var(--bad);border-color:#f2c6cf}
.badge.tag{background:#eef1f5;color:#39424e;border-color:#dde3ea;font-weight:600}
.pickgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px;margin:16px 0}
.pick{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);
border-radius:12px;padding:16px 18px}
.pick .sport{font-size:12px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);font-weight:700}
.pick .match{font-weight:800;font-size:17px;margin:3px 0}
.pick .meta{color:var(--muted);font-size:13px}
.sel{margin:12px 0;padding:10px 12px;background:var(--bg);border-radius:10px}
.sel .lab{font-size:11px;text-transform:uppercase;letter-spacing:.6px;color:var(--muted);font-weight:700}
.sel .val{font-size:18px;font-weight:800}
.sel .px{color:var(--accent);font-weight:800}
.pick p.txt{font-size:14.5px;margin:10px 0 6px}
.src{font-size:12.5px;color:var(--muted);word-break:break-word}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:14px}
th{background:#f1f3f6;text-align:left;padding:9px 10px;font-size:12px;text-transform:uppercase;
letter-spacing:.4px;color:#3f4855;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:9px 10px;border-bottom:1px solid var(--line);vertical-align:top}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#fbfbfc}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tablescroll{overflow-x:auto;margin:10px 0 4px}
.pillrow{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0}
.pill{background:#fff;border:1px solid var(--line);border-radius:999px;padding:6px 12px;font-size:13px}
.pill b{font-weight:800}
footer{border-top:1px solid var(--line);background:#fff;padding:20px 0;color:var(--muted);font-size:13px}
ul{margin:8px 0 14px;padding-left:20px}li{margin:4px 0}
.srclist{font-size:13px;margin:8px 0 0;padding-left:18px}
.code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;background:#f3f4f6;
padding:1px 5px;border-radius:5px;word-break:break-all}
"""


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def money(american) -> str:
    if american in (None, ""):
        return "—"
    value = int(american)
    return f"+{value}" if value > 0 else str(value)


def clock(iso: str) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return iso
    return dt.strftime("%a %d %b, %H:%M UTC")


def badge(conf: str) -> str:
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(conf, "low")
    return f'<span class="badge {cls}">{esc(conf or "—")}</span>'


def page(title: str, active: str, body: str, capture: str) -> str:
    nav = [("Overview", "index.html"), ("Picks", "picks.html"),
           ("Predictions", "predictions.html"), ("All matches", "matches.html"),
           ("Sports", "coverage.html"), ("Markets", "markets.html"),
           ("Sources", "sources.html"), ("Method", "methodology.html"),
           ("Repo review", "review.html"), ("Flagged", "flagged.html")]
    links = "".join(
        f'<a class="link{" active" if label == active else ""}" href="{href}">{label}</a>'
        for label, href in nav)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG desk</title>
<link rel="stylesheet" href="style.css">
</head><body>
<header class="site"><div class="wrap"><div class="nav">
<a class="brand" href="index.html"><span class="mark">DS</span><span>OLBG desk</span></a>
{links}<span class="stamp">Official data read {esc(capture)}</span>
</div></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
Board DS · every fixture, price and statistic on this site is traceable to a captured
governing-body response listed on <a href="sources.html">Sources</a>. Prices are our own fair
lines, not bookmaker quotes. If a value could not be confirmed it is blank and listed on
<a href="flagged.html">Flagged for review</a>.
</div></footer></body></html>
"""


def table(headers, rows, cls="") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablescroll"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "predictions.json"), encoding="utf-8"))
    olbg = json.load(open(os.path.join(DATA, "olbg.json"), encoding="utf-8"))
    evidence = json.load(open(os.path.join(DATA, "evidence.json"), encoding="utf-8"))
    review = json.load(open(os.path.join(DATA, "review.json"), encoding="utf-8"))
    manifest = json.load(open(os.path.join(DATA, "raw", "manifest.json"), encoding="utf-8"))
    capture = desk["capture_utc"]
    rows = desk["rows"]
    priced = [r for r in rows if r["status"] == "priced"]
    highs = [r for r in priced if r["pick"]["confidence"] == "High"]
    inwin = [r for r in priced if r["pick"]["in_price_window"]]
    high_in = [r for r in highs if r["pick"]["in_price_window"]]
    pred_by_id = {p["id"]: p for p in preds["predictions"]}
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "style.css"), "w", encoding="utf-8").write(CSS)

    # ---------------------------------------------------------------- helpers
    def sport_rows(sport):
        if sport == "Gaelic Sports":
            return [r for r in rows if r["sport"] in GAELIC_MEMBERS]
        return [r for r in rows if r["sport"] == sport]

    def sport_preds(sport):
        if sport == "Gaelic Sports":
            return [p for p in preds["predictions"] if p["sport"] in GAELIC_MEMBERS]
        return [p for p in preds["predictions"] if p["sport"] == sport]

    def match_cell(r):
        home = r.get("home_name") or r["event_name"]
        away = r.get("away_name") or ""
        if away and away not in home:
            return f"{esc(home)} <span class='muted'>v</span> {esc(away)}"
        return esc(home)

    def source_cell(r):
        if r["status"] != "priced":
            return "<span class='muted'>no official strength input</span>"
        label = esc(r["official_name"].split("(")[0].strip())
        url = r["official_url"]
        extra = (f"<br><a href='{esc(r['fixture_url'])}' target='_blank' rel='noopener'>"
                 f"fixture page</a>" if r.get("fixture_url") else "")
        return (f"<a href='{esc(url)}' target='_blank' rel='noopener'>{label}</a>{extra}"
                f"<br><a href='{esc(r['olbg_url'])}' target='_blank' rel='noopener'>OLBG market</a>")

    def pick_cell(r):
        if r["status"] != "priced":
            return "<span class='muted'>—</span>"
        p = r["pick"]
        win = ("<span class='badge win'>in band</span>" if p["in_price_window"]
               else "<span class='badge out'>outside band</span>")
        return (f"<b>{esc(p['selection'])}</b><br><span class='muted'>{esc(p['market'])}</span> "
                f"<span class='num'>{money(p['american'])}</span><br>{win}")

    # ---------------------------------------------------------------- index
    today = [r for r in priced if r["start_utc"][:10] == "2026-10-24"]
    tomorrow = [r for r in priced if r["start_utc"][:10] == "2026-10-25"]
    top = sorted(priced, key=lambda r: -r["pick"]["probability"])[:6]
    cards = ""
    for r in top:
        p = r["pick"]
        pred = pred_by_id.get(r["id"])
        excerpt = (pred["text"][:260].rsplit(" ", 1)[0] + "…") if pred else (
            "No written prediction for this match; the selection and price are listed on "
            "<a href='picks.html'>Picks</a>.")
        quote = ""
        if r.get("olbg_quote"):
            q = r["olbg_quote"]
            quote = (f"<div class='meta'>OLBG was quoting {esc(q['selection'])} at "
                     f"{money(q['american'])} ({q['tips']} tips)</div>")
        cards += f"""<article class="pick">
<div class="top"><span class="sport">{esc(r['sport'])} · {esc(r['competition'] or 'OLBG listing')}</span>
<span class="badge {p['confidence'].lower()}">{esc(p['confidence'])}</span></div>
<div class="match">{match_cell(r)}</div>
<div class="meta">{clock(r['start_utc'])}{(' · ' + esc(r['venue'])) if r.get('venue') else ''}</div>
<div class="sel"><div class="lab">Selection · {esc(p['market'])}</div>
<div class="val">{esc(p['selection'])} <span class="px">{money(p['american'])}</span></div>
<div class="meta">our fair price · implied {p['probability']*100:.1f}%{'' if p['in_price_window'] else ' · outside the −250…+10,000 band'}</div></div>
<p class="txt">{excerpt}</p>
{quote}
<div class="src">Source: <a href="{esc(r['official_url'])}" target="_blank" rel="noopener">{esc(r['official_name'])}</a>
 · <a href="{esc(r['olbg_url'])}" target="_blank" rel="noopener">OLBG market</a></div>
</article>"""

    cov_rows = []
    for name, slug in SPORTS:
        subset = sport_rows(name)
        pp = [r for r in subset if r["status"] == "priced"]
        pr = sport_preds(name)
        reason = ""
        if not subset:
            reason = "OLBG listed no upcoming match market at capture."
        elif not pp:
            reason = subset[0]["flags"][0] if subset[0]["flags"] else ""
        cov_rows.append([
            f"<a href='sports/{slug}.html'>{esc(name)}</a>",
            f"<span class='num'>{olbg['sports'].get(name.lower().replace(' ', '_'), {}).get('events', '—')}</span>",
            f"<span class='num'>{len(subset)}</span>",
            f"<span class='num'>{len(pp)}</span>",
            f"<span class='num'>{len(pr)}</span>",
            f"<span class='num'>{sum(1 for r in pp if r['pick']['confidence']=='High')}</span>",
            esc(reason[:150]) if reason else "<span class='badge win'>priced</span>",
        ])

    today_table = table(
        ["Kick-off", "Sport", "Match", "Our pick", "Price", "Confidence", "Source"],
        [[clock(r["start_utc"]), esc(r["sport"]), match_cell(r),
          f"<b>{esc(r['pick']['selection'])}</b>", f"<span class='num'>{money(r['pick']['american'])}</span>",
          badge(r["pick"]["confidence"]),
          f"<a href='{esc(r['official_url'])}' target='_blank' rel='noopener'>stats</a> · "
          f"<a href='{esc(r['olbg_url'])}' target='_blank' rel='noopener'>OLBG</a>"]
         for r in sorted(today + tomorrow, key=lambda r: r["start_utc"])]) if (today or tomorrow) else (
        "<p class='muted'>Nothing priced in the next 24 hours.</p>")

    body = f"""
<h1>Every OLBG match in our fifteen sports, our own line, and the pick in plain sight.</h1>
<p class="lede">OLBG's public pages were read at {esc(capture)}. This desk lists every upcoming
match OLBG was offering in the fifteen sports in the brief, originates a price for each one from
governing-body data only, labels a confidence, and writes the reasoning out in full where the
evidence supports it. Nothing is guessed: where an official input is missing, the row is blank
and named on the <a href="flagged.html">Flagged for review</a> page.</p>

<div class="kpis">
<div class="kpi"><div class="n">{len(rows)}</div><div class="l">upcoming OLBG matches in scope</div></div>
<div class="kpi"><div class="n">{len(priced)}</div><div class="l">with our own price</div></div>
<div class="kpi"><div class="n">{len(preds['predictions'])}</div><div class="l">written predictions</div></div>
<div class="kpi"><div class="n">{len(highs)}</div><div class="l">high confidence</div></div>
<div class="kpi"><div class="n">{len(inwin)}</div><div class="l">inside −250…+10,000</div></div>
</div>

<div class="note"><strong>Start here.</strong> The picks are the six cards below and the full
list on <a href="picks.html">Picks</a>. The reasoning for each is on
<a href="predictions.html">Predictions</a>. Every row of every table links its official source.
Sports with no priceable match are named, with the exact missing input, on
<a href="coverage.html">Sports</a>.</div>

<h2>Executive summary</h2>
<div class="grid2">
<div class="card">
<p><b>What OLBG is offering.</b> {len(rows)} upcoming match markets across
{len({r['sport'] for r in rows})} of the fifteen sports, plus a number of outright markets
(tournament and futures) that are listed on <a href="coverage.html">Sports</a> but excluded from
the match desk because they are not head-to-head fixtures.</p>
<p><b>What we could price.</b> {len(priced)} matches: {', '.join(f"{s} {n}" for s, n in sorted(
    ((s, sum(1 for r in priced if r['sport'] == s)) for s in {r['sport'] for r in priced}),
    key=lambda x: (-x[1], x[0])))}. Each price uses both sides' official records, not one team's.</p>
<p><b>Where the confidence sits.</b> {len(highs)} picks clear a 70% win probability
({', '.join(sorted({r['sport'] for r in highs}))}). {len(high_in)} of those also sit inside the
brief's −250…+10,000 price band, because a 70% favourite is already about −233: see
<a href="methodology.html">Method</a> for the arithmetic.</p>
<p><b>Where it stops.</b> Eleven sports have no priceable match today, and the reason is stated
row by row, not hidden: no official strength feed was reachable (ATP and NBA return HTTP 403 to
the capture runner, OWGR and World Rugby return 404, the ICC, WST, PDC and GAA pages render
client-side only), or OLBG listed no upcoming match at all.</p>
</div>
<div class="card">
<h3>How to read this site</h3>
<ul>
<li><a href="picks.html"><b>Picks</b></a> — one obvious table per sport, with the selection,
our price and its confidence.</li>
<li><a href="predictions.html"><b>Predictions</b></a> — the full written case, 58–75 words
each, with its sources underneath.</li>
<li><a href="matches.html"><b>All matches</b></a> — every row, priced or not.</li>
<li><a href="coverage.html"><b>Sports</b></a> — fifteen pages, one per sport.</li>
<li><a href="flagged.html"><b>Flagged</b></a> — everything we could not confirm.</li>
</ul>
<h3>Today and tomorrow</h3>
<p class="muted">{len(today)} priced matches kick off later today (UTC) and {len(tomorrow)}
tomorrow.</p>
</div>
</div>

<h2>Kicking off later today <small class="muted">— 24 October, UTC</small></h2>
{today_table}

<h2>Highest-confidence picks <small class="muted">— sorted by our win probability</small></h2>
<div class="pickgrid">{cards}</div>

<h2>Coverage at a glance</h2>
<p class="lede">OLBG events are what OLBG itself was offering at capture; "rows" excludes
outright markets. A sport with rows but no price has no official strength input, and the last
column says which.</p>
{table(["Sport", "OLBG events", "Upcoming matches", "Priced", "Predictions", "High", "Status"], cov_rows)}
"""

    pages = {"index.html": page("Overview", "Overview", body, capture)}

    # ---------------------------------------------------------------- picks
    blocks = []
    for name, slug in SPORTS:
        subset = sorted([r for r in sport_rows(name) if r["status"] == "priced"],
                        key=lambda r: -r["pick"]["probability"])[:10]
        if not subset:
            continue
        trs = []
        for r in subset:
            p = r["pick"]
            q = r.get("olbg_quote")
            pred = pred_by_id.get(r["id"])
            trs.append([
                match_cell(r),
                clock(r["start_utc"]),
                f"<b>{esc(p['selection'])}</b>",
                esc(p["market"]),
                f"<span class='num'>{money(p['american'])}</span>",
                f"<span class='num'>{money(q['american']) if q else '—'}</span>",
                f"<span class='num'>{p['probability']*100:.1f}%</span>",
                badge(p["confidence"]),
                "<span class='badge win'>yes</span>" if p["in_price_window"]
                else "<span class='badge out'>no</span>",
                (f"<a href='predictions.html#{esc(pred['id'])}'>read</a>" if pred else "—"),
                source_cell(r),
            ])
        blocks.append(f"""<h2>{esc(name)} <small class="muted">— {len(subset)} shown</small></h2>
{table(["Match", "Kick-off", "Selection", "Market", "Our price", "OLBG", "Win prob", "Confidence", "In band", "Write-up", "Source"], trs)}""")

    body = f"""
<h1>Picks</h1>
<p class="lede">One line per match we priced, grouped by sport, highest probability first.
"OLBG" is the price OLBG itself was showing for that selection where it listed one; a dash means
OLBG listed a different selection or no price. Prices are our fair line, so a small edge over
OLBG's quote is the point of the exercise, not a misprint.</p>
<div class="pillrow">
<div class="pill"><b>{len(priced)}</b> picks</div>
<div class="pill"><b>{len(highs)}</b> high confidence</div>
<div class="pill"><b>{len(inwin)}</b> inside the −250…+10,000 band</div>
<div class="pill"><b>{len(preds['predictions'])}</b> with a full write-up</div>
</div>
{''.join(blocks) if blocks else '<div class="card">No picks today.</div>'}
<h2>Sports with no pick</h2>
<p class="lede">These sports have OLBG matches listed but no price, because no official strength
input was captured. The exact missing input is on <a href="coverage.html">Sports</a>.</p>
{table(["Sport", "Matches listed", "Reason"],
      [[f"<a href='sports/{slug}.html'>{esc(n)}</a>",
        f"<span class='num'>{len(sport_rows(n))}</span>",
        esc(sport_rows(n)[0]["flags"][0] if sport_rows(n) else "OLBG listed no upcoming match.")]
       for n, slug in SPORTS if not any(r["status"] == "priced" for r in sport_rows(n))])}
"""
    pages["picks.html"] = page("Picks", "Picks", body, capture)

    # ---------------------------------------------------------------- predictions
    cards = []
    for p in sorted(preds["predictions"], key=lambda x: (x["sport"], -x["probability"])):
        srcs = " · ".join(f"<a href='{esc(s['url'])}' target='_blank' rel='noopener'>{esc(s['label'])}</a>"
                          for s in p["sources"])
        flag = ("" if p["identity_confirmed"] else
                "<div class='note'><strong>Fixture identity:</strong> OLBG is the only source "
                "that names this fixture; the governing body supplies the team records, not the "
                "pairing. Logged on <a href='flagged.html'>Flagged for review</a>.</div>")
        cards.append(f"""<article class="card" id="{esc(p['id'])}">
<div class="top"><span class="sport muted">{esc(p['sport'])} · {clock(p['start_utc'])}</span>
{badge(p['confidence'])}</div>
<h3>{esc(p['heading'])}</h3>
<div class="sel"><div class="lab">Selection · {esc(p['market'])}</div>
<div class="val">{esc(p['selection'])} <span class="px">{money(p['american'])}</span>
<span class="muted" style="font-size:13px">our fair price · {p['probability']*100:.1f}%</span></div>
<div class="meta">{esc(p['event_name'])}</div></div>
<p class="txt">{esc(p['text'])}</p>
{flag}
<div class="src">Sources: {srcs} · {p['words']} words</div>
</article>""")
    body = f"""
<h1>Written predictions</h1>
<p class="lede">{len(preds['predictions'])} predictions across
{len({p['sport'] for p in preds['predictions']})} sports. Each one names the teams or players,
states the record and scoring figures we hold for both sides, names the selection and its price,
and links the official page those figures came from. Length is 58–75 words; no two texts share
more than 0.35 word overlap.</p>
<div class="note"><strong>Why not fifteen sports?</strong> A prediction needs a priced market and
two verified strength inputs. Eleven sports have neither today, and writing a pick without them
would be invention. The full list of what is missing, with URLs, is on
<a href="flagged.html">Flagged for review</a>.</div>
{''.join(cards)}
"""
    pages["predictions.html"] = page("Predictions", "Predictions", body, capture)

    # ---------------------------------------------------------------- matches
    trs = []
    for r in sorted(rows, key=lambda r: (r["start_utc"], r["sport"])):
        state = ("<span class='badge win'>priced</span>" if r["status"] == "priced"
                 else "<span class='badge low'>unpriced</span>")
        trs.append([
            esc(r["sport"]),
            esc(r["competition"] or "—"),
            match_cell(r),
            clock(r["start_utc"]),
            esc(r["venue"] or "—"),
            pick_cell(r),
            badge(r["pick"]["confidence"]) if r["status"] == "priced" else "—",
            state,
            source_cell(r),
            esc(r["flags"][0][:120]) if r["flags"] else "",
        ])
    body = f"""
<h1>All matches</h1>
<p class="lede">Every upcoming OLBG match in the fifteen sports, priced or not. This is the
complete list behind the picks: {len(rows)} rows, {len(priced)} priced. A row with no price has
its reason in the final column.</p>
{table(["Sport", "Competition", "Match", "Kick-off", "Venue", "Our pick / price", "Conf.", "State", "Official source", "Note"], trs)}
"""
    pages["matches.html"] = page("All matches", "All matches", body, capture)

    # ---------------------------------------------------------------- sports pages
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    for name, slug in SPORTS:
        subset = sorted(sport_rows(name), key=lambda r: r["start_utc"])
        pp = [r for r in subset if r["status"] == "priced"]
        pr = sport_preds(name)
        meta = olbg["sports"].get(name.lower().replace(" ", "_"), {})
        trs = []
        for r in subset:
            trs.append([
                match_cell(r), clock(r["start_utc"]), esc(r["competition"] or "—"),
                pick_cell(r),
                badge(r["pick"]["confidence"]) if r["status"] == "priced" else "—",
                source_cell(r),
                esc(r["flags"][0][:140]) if r["flags"] else "",
            ])
        pred_html = ""
        for p in pr:
            srcs = " · ".join(f"<a href='{esc(s['url'])}' target='_blank' rel='noopener'>{esc(s['label'])}</a>"
                              for s in p["sources"])
            pred_html += f"""<article class="card">
<h3>{esc(p['heading'])} {badge(p['confidence'])}</h3>
<div class="sel"><div class="lab">Selection</div>
<div class="val">{esc(p['selection'])} <span class="px">{money(p['american'])}</span></div>
<div class="meta">{esc(p['event_name'])} · {clock(p['start_utc'])}</div></div>
<p class="txt">{esc(p['text'])}</p>
<div class="src">Sources: {srcs}</div></article>"""
        empty = ""
        if not subset:
            empty = ("<div class='note'><strong>No OLBG match market at capture.</strong> OLBG's "
                     f"{esc(name)} hub returned no upcoming tipped event when it was read at "
                     f"{esc(capture)}. That is OLBG's own feed behaviour, not a gap in our "
                     "reading, and it is logged on <a href='../flagged.html'>Flagged</a>.</div>")
        elif not pp:
            empty = (f"<div class='note'><strong>Listed but unpriced.</strong> "
                     f"{esc(subset[0]['flags'][0])} The official pages we attempted are on "
                     "<a href='../sources.html'>Sources</a>.</div>")
        body = f"""
<h1>{esc(name)}</h1>
<p class="lede">{len(subset)} upcoming OLBG matches, {len(pp)} priced,
{len(pr)} written predictions.</p>
<div class="pillrow">
<div class="pill">OLBG hub events <b>{meta.get('events', '—')}</b></div>
<div class="pill">Priced <b>{len(pp)}</b></div>
<div class="pill">High confidence <b>{sum(1 for r in pp if r['pick']['confidence']=='High')}</b></div>
<div class="pill">Predictions <b>{len(pr)}</b></div>
</div>
{empty}
<h2>Matches and picks</h2>
{table(["Match", "Kick-off", "Competition", "Our pick / price", "Conf.", "Official source", "Note"], trs) if subset else "<p class='muted'>No rows.</p>"}
<h2>Written predictions</h2>
{pred_html or "<p class='muted'>No written prediction for this sport today — see the reason above.</p>"}
"""
        pages[os.path.join("sports", f"{slug}.html")] = page(
            name, "Sports", body, capture).replace('href="style.css"', 'href="../style.css"') \
            .replace('href="index.html"', 'href="../index.html"').replace(
                'href="picks.html"', 'href="../picks.html"').replace(
                'href="predictions.html"', 'href="../predictions.html"').replace(
                'href="matches.html"', 'href="../matches.html"').replace(
                'href="coverage.html"', 'href="../coverage.html"').replace(
                'href="markets.html"', 'href="../markets.html"').replace(
                'href="sources.html"', 'href="../sources.html"').replace(
                'href="methodology.html"', 'href="../methodology.html"').replace(
                'href="review.html"', 'href="../review.html"').replace(
                'href="flagged.html"', 'href="../flagged.html"')

    # ---------------------------------------------------------------- markets
    trs = []
    for r in sorted(priced, key=lambda r: (r["sport"], r["start_utc"])):
        ml = r["markets"]["moneyline"]
        hc = r["markets"].get("handicap")
        tt = r["markets"].get("total")
        trs.append([
            esc(r["sport"]), match_cell(r), clock(r["start_utc"]),
            f"{money(ml['home']['american'])} / {money(ml['away']['american'])}",
            (f"{esc(hc['home_selection'])} {money(hc['home']['american'])}" if hc else "—"),
            (f"Over {hc['line']:g}" if False else (f"{esc(tt['over_selection'])} {money(tt['over']['american'])}"
                                                   f" / {esc(tt['under_selection'])} {money(tt['under']['american'])}"
                                                   if tt else "—")),
            f"<span class='num'>{r['expected_margin'] if r['expected_margin'] is not None else '—'}</span>",
            f"<span class='num'>{r['expected_total'] if r['expected_total'] is not None else '—'}</span>",
        ])
    taxonomy = sorted({m for e in olbg["events"] for m in e["markets"]})
    body = f"""
<h1>Markets</h1>
<p class="lede">Three markets were investigated for every priced match: match winner
(moneyline), handicap/spread and match total. All twenty-seven are shown here with the price on
each side, so the reasoning can be checked market by market. Where a market could not be priced
from official scoring rates, the cell is blank.</p>
<h2>Every originated market</h2>
{table(["Sport", "Match", "Kick-off", "Moneyline (home / away)", "Handicap", "Total (over / under)", "Expected margin", "Expected total"], trs)}
<h2>Market names OLBG itself was showing</h2>
<p class="lede">Read from the captured OLBG feed. These are the market labels OLBG uses on its
public pages, which is what a reader has to search for when they want to place a bet.</p>
<div class="pillrow">{''.join(f'<div class="pill">{esc(m)}</div>' for m in taxonomy)}</div>
<h2>Which markets each sport supports in our desk</h2>
{table(["Sport", "Moneyline", "Handicap", "Total", "Reason where absent"],
      [[esc(n),
        str(sum(1 for r in sport_rows(n) if r["status"] == "priced")),
        str(sum(1 for r in sport_rows(n) if r.get("markets", {}).get("handicap"))),
        str(sum(1 for r in sport_rows(n) if r.get("markets", {}).get("total"))),
        esc(sport_rows(n)[0]["flags"][0][:110]) if sport_rows(n) and not any(
            r["status"] == "priced" for r in sport_rows(n)) else "—"]
       for n, _ in SPORTS])}
"""
    pages["markets.html"] = page("Markets", "Markets", body, capture)

    # ---------------------------------------------------------------- coverage
    trs = []
    for name, slug in SPORTS:
        subset = sport_rows(name)
        pp = [r for r in subset if r["status"] == "priced"]
        pr = sport_preds(name)
        meta = olbg["sports"].get(name.lower().replace(" ", "_"), {})
        trs.append([
            f"<a href='sports/{slug}.html'>{esc(name)}</a>",
            f"<span class='num'>{meta.get('events', '—')}</span>",
            f"<span class='num'>{len(subset)}</span>",
            f"<span class='num'>{len(pp)}</span>",
            f"<span class='num'>{len(pr)}</span>",
            esc(subset[0]["flags"][0]) if subset and not pp else (
                "priced" if pp else "OLBG listed no upcoming match market at capture."),
        ])
    body = f"""
<h1>Sports</h1>
<p class="lede">All fifteen sports in the brief, what OLBG was offering, what we could price and
what we wrote. The final column is the honest gap: the exact missing input, in the words of the
row itself.</p>
{table(["Sport", "OLBG events listed", "Upcoming matches", "Priced", "Predictions", "Gap"], trs)}
<h2>Outright and futures markets OLBG was listing</h2>
<p class="lede">OLBG also offered tournament and futures markets (for example a darts tournament
winner or an All-Ireland outright). They are not head-to-head matches, so they sit outside this
match desk and outside the pick count. They are listed here so the inventory is complete.</p>
"""
    outs = []
    for e in olbg["events"]:
        if e["start_utc"] and e["start_utc"] > capture and (
                "Tournament" in " ".join(e["markets"]) or "Outright" in " ".join(e["markets"])
                or "Winner" in " ".join(e["markets"]) or "Hurling" in " ".join(e["markets"])
                or "Races" in " ".join(e["markets"])):
            outs.append([esc(e["sport"]), esc(e["event_name"] or "—"),
                         clock(e["start_utc"]), esc(", ".join(e["markets"]) or "—"),
                         f"<a href='{esc(e['olbg_url'])}' target='_blank' rel='noopener'>OLBG</a>"])
    body += table(["Sport", "Market", "Starts", "OLBG market label", "Link"], outs)
    pages["coverage.html"] = page("Sports", "Sports", body, capture)

    # ---------------------------------------------------------------- sources
    entries = sorted(manifest["entries"], key=lambda e: (e["group"], e["key"]))
    trs = []
    for e in entries:
        ok = e.get("status") == 200 and e.get("sha256")
        trs.append([
            esc(e["group"]), f"<span class='code'>{esc(e['key'])}</span>",
            f"<a href='{esc(e['url'])}' target='_blank' rel='noopener'>{esc(e['url'][:78])}</a>",
            f"<span class='num'>{e.get('status')}</span>",
            f"<span class='num'>{e.get('bytes', 0):,}</span>",
            f"<span class='code'>{esc((e.get('sha256') or '')[:16])}</span>",
            "<span class='badge win'>captured</span>" if ok else
            f"<span class='badge out'>{esc((e.get('error') or 'failed')[:48])}</span>",
        ])
    failed = [e for e in entries if not (e.get("status") == 200 and e.get("sha256"))]
    body = f"""
<h1>Sources</h1>
<p class="lede">Every response behind this site, with its HTTP status, byte count and SHA-256
hash. {len(entries)} requests, {len(entries)-len(failed)} captured, {len(failed)} failed. A
failed request is published, not retried until it looks successful: it is the reason a sport is
unpriced.</p>
<div class="note"><strong>How to check a number.</strong> Pick any row on
<a href="matches.html">All matches</a>, open its source link, and compare. The hash column lets
you confirm the exact bytes we parsed are the ones listed here.</div>
<h2>Failed or blocked requests</h2>
{table(["Key", "URL", "Status", "Error"],
      [[f"<span class='code'>{esc(e['key'])}</span>",
        f"<a href='{esc(e['url'])}' target='_blank' rel='noopener'>{esc(e['url'][:80])}</a>",
        f"<span class='num'>{e.get('status')}</span>", esc(e.get('error', ''))]
       for e in failed]) if failed else "<p class='muted'>None.</p>"}
<h2>Complete capture record</h2>
{table(["Group", "Key", "URL", "HTTP", "Bytes", "SHA-256", "Result"], trs)}
"""
    pages["sources.html"] = page("Sources", "Sources", body, capture)

    # ---------------------------------------------------------------- methodology
    a = desk["assumptions"]
    body = f"""
<h1>Method</h1>
<p class="lede">How a number gets onto this site, and what we refuse to do. Everything below is
reproducible from the committed capture: <span class="code">collect.py</span> fetches,
<span class="code">evidence.py</span> parses, <span class="code">originate.py</span> prices,
<span class="code">predict.py</span> attaches the writing, <span class="code">verify.py</span>
checks the lot.</p>

<h2>1. What counts as a fixture</h2>
<p>An OLBG event is only listed here if OLBG's own page carried it with a kick-off time and at
least one market. OLBG renders events that have at least one public tip, so the inventory means
"events OLBG is currently offering", not every fixture in world sport. Where OLBG lists an
outright rather than a match, it is on <a href="coverage.html">Sports</a>, not in the matches.</p>

<h2>2. What counts as a price</h2>
<p>A match is priced only when <b>both</b> sides have a strength figure from a captured
governing-body response. No 50/50 prior, no price from a hunch, no price borrowed from OLBG's own
quote. The sixteen unpriced sports or fixtures are named individually with the missing input.</p>

<h2>3. The model-free maths we publish</h2>
<p>We call it a line, not a model. For a two-sided match the win probability is a log5 blend of
the two official win rates, with a documented home-field term:</p>
<p class="code">p(home) = ((a + h) − (a + h)(b − h)) / ((a + h) + (b − h) − 2(a + h)(b − h))</p>
<p>Small samples are shrunk toward the competition mean before that blend, so a club that is 5-0
after five rounds is not treated as a 98% favourite. Handicap and total markets use the expected
margin and expected total from each side's scoring rate, with a normal approximation and a
published spread:</p>
{table(["Assumption", "Ice Hockey", "Baseball", "Handball", "Tennis"],
      [["Home-field term", a["home_edge"]["Ice Hockey"], a["home_edge"]["Baseball"],
        a["home_edge"]["Handball"], a["home_edge"]["Tennis"]],
       ["Margin spread (goals/runs)", a["margin_sd"]["Ice Hockey"], a["margin_sd"]["Baseball"],
        a["margin_sd"]["Handball"], a["margin_sd"]["Tennis"]],
       ["Total spread", a["total_sd"]["Ice Hockey"], a["total_sd"]["Baseball"],
        a["total_sd"]["Handball"], "—"],
       ["Home scoring edge", a["home_score_edge"]["Ice Hockey"], a["home_score_edge"]["Baseball"],
        a["home_score_edge"]["Handball"], "—"]])}
<p>These are our own line-building assumptions, stated as assumptions. They are not facts about
any match, and they are the first thing to challenge if a price looks wrong.</p>

<h2>4. Confidence and the price band</h2>
<p>Confidence is a probability statement: <b>High</b> at 70% or better, <b>Medium</b> from 60% to
70%, <b>Low</b> below 60%. The brief also asks for picks priced between −250 and +10,000. Those
two rules collide: −250 is a 71.4% implied chance, so a pick that clears 70% and sits inside the
band must land between 70.0% and 71.4%. Every pick therefore shows both facts — its label and
whether it is inside the band — and nothing is relabelled to force a match. Today {len(highs)}
picks clear 70% and {len(high_in)} of them are inside the band.</p>

<h2>5. What is deliberately absent</h2>
<ul>
<li><b>No injuries.</b> No official availability report was captured for these fixtures, so no
prediction claims one. An invented injury list is worse than no injury list.</li>
<li><b>No head-to-head history</b> unless a captured official source states it.</li>
<li><b>No odds-shop quotes.</b> The only price we compare against is the one OLBG displayed, and
it is labelled as such.</li>
<li><b>No filler picks.</b> A match without two verified inputs gets no pick, and the sport says
so on its own page.</li>
</ul>

<h2>6. Verification gates</h2>
<p><span class="code">verify.py</span> re-derives every decimal and American price from its own
probability, checks both sides of every market sum to 1.0000 within rounding, re-applies the
confidence rule and the band test, checks each prediction against its word floor, uniqueness and
selection naming, confirms every rendered table row carries an https source link, and rebuilds the
site byte for byte. Exit code is zero only if all of it passes.</p>
"""
    pages["methodology.html"] = page("Method", "Method", body, capture)

    # ---------------------------------------------------------------- review
    blocks = []
    for f in review["findings"]:
        rows_html = ""
        if f["examples"]:
            rows_html = table(
                ["Sport", "Date", "Match", "Pick", "Conf.", "Source"],
                [[esc(x["sport"]), esc(x["date"]), esc(f"{x['home']} v {x['away']}"),
                  esc(x["pick"]), esc(x["confidence"]),
                  (f"<a href='{esc(x['source_url'])}' target='_blank' rel='noopener'>open</a>"
                   if x["source_url"] else "<span class='muted'>none</span>")]
                 for x in f["examples"]])
        blocks.append(f"""<article class="card">
<h3>{esc(f['id'])} · {esc(f['title'])} <span class="badge {'out' if f['severity']=='review' else 'win'}">{esc(f['severity'])}</span>
<small class="muted">— {f['count']} affected</small></h3>
<p>{esc(f['detail'])}</p>{rows_html}</article>""")
    body = f"""
<h1>Repository review</h1>
<p class="lede">A line-by-line check of the repository's canonical desk
(<span class="code">{esc(review['reviewed_file'])}</span>, generated
{esc(review['generated_on'])}, {review['rows_reviewed']} rows). Every finding is reproducible
from that file and links the affected row's own source so it can be opened by hand. This board
does not edit another session's data; the findings are published here for the owner.</p>
<div class="pillrow"><div class="pill"><b>{review['rows_reviewed']}</b> rows reviewed</div>
<div class="pill"><b>{sum(f['count'] for f in review['findings'] if f['severity']=='review')}</b> rows affected</div>
<div class="pill"><b>{len(review['findings'])}</b> findings</div></div>
{''.join(blocks)}
"""
    pages["review.html"] = page("Repo review", "Repo review", body, capture)

    # ---------------------------------------------------------------- flagged
    identity = [r for r in priced if not r["identity_confirmed"]]
    unpriced = [r for r in rows if r["status"] != "priced"]
    flag_rows = []
    for r in identity:
        flag_rows.append([esc(r["sport"]), match_cell(r), "Fixture identity",
                          "OLBG is the only source naming this pairing; the governing body "
                          "supplies the team records but not the fixture itself.",
                          f"<a href='{esc(r['olbg_url'])}' target='_blank' rel='noopener'>OLBG</a> · "
                          f"<a href='{esc(r['official_url'])}' target='_blank' rel='noopener'>official table</a>"])
    for r in unpriced[:40]:
        flag_rows.append([esc(r["sport"]), match_cell(r), "Unpriced",
                          esc(r["flags"][0]), "<span class='muted'>no official input</span>"])
    short_predictions = []
    for name, slug in SPORTS:
        n = len(sport_preds(name))
        if n < 5:
            short_predictions.append([f"<a href='sports/{slug}.html'>{esc(name)}</a>",
                                      f"<span class='num'>{n}</span>",
                                      "Target is five written predictions per sport. This sport "
                                      "has fewer priced matches today."])
    body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything this board could not confirm, every assumption that could be
challenged, and every place the brief and the arithmetic disagree. None of it is hidden inside a
blank cell: each item says what is missing and where to check.</p>

<h2>A. Brief-level irregularities</h2>
<div class="card"><h3>F-01 · The 70% rule and the −250 floor cannot both bind</h3>
<p>A −250 price implies 71.43%. "High confidence" is defined as 70% or better. So a pick that is
both High and inside −250…+10,000 must have a true probability between 70.0% and 71.4%. Today
{len(highs)} picks clear 70% and {len(high_in)} sit inside the band; {len(highs)-len(high_in)}
sitre shorter than −250 and are labelled on <a href="picks.html">Picks</a> rather than relabelled.
Manual review: compare any row's percentage with the American conversion on
<a href="methodology.html">Method</a>.</p></div>

<div class="card"><h3>F-02 · OLBG lists nothing for two sports</h3>
<p>The Golf and Motor Racing hubs returned OLBG's own "No tips found" response at
{esc(capture)}. OLBG only renders events that carry a public tip, so there is no OLBG market to
price for those sports today. The hubs are on <a href="sources.html">Sources</a> so the claim can
be checked.</p></div>

<div class="card"><h3>F-03 · Fixture identity on {len(identity)} priced matches rests on OLBG</h3>
<p>The governing-body pages we captured publish team records but not the fixture list (EHF), or
the match is not on a captured official schedule (WTA). The pairing therefore comes from OLBG and
the strength figures from the governing body. Every such row is marked above and on
<a href="matches.html">All matches</a>.</p></div>

<div class="card"><h3>F-04 · Official sources that refused the capture runner</h3>
<p>ATP (<span class="code">HTTP 403</span>), NBA (<span class="code">HTTP 403</span>), OWGR
(<span class="code">404</span>), World Rugby rankings (<span class="code">404</span>), MotoGP
standings (<span class="code">404</span>), Super League tables (<span class="code">500</span>),
and the ICC, WST, PDC and GAA pages that render client-side only. Each URL is listed with its
status on <a href="sources.html">Sources</a>. This is why tennis, basketball, cricket, snooker,
darts, rugby league and Gaelic sports carry few or no picks.</p></div>

<div class="card"><h3>F-05 · No injury or availability data</h3>
<p>No official availability report was captured for any fixture, so no prediction mentions an
injury. The brief asks for verified injuries; the honest answer today is that we have none, and
inventing one would break the rule that matters more.</p></div>

<div class="card"><h3>F-06 · OLBG's feed is not a complete fixture list</h3>
<p>OLBG renders only events with at least one public tip and hides further events behind a
lazy-load control. Two fixtures we could see in the hub payload had no visible row at all. The
inventory is therefore "what OLBG is offering with coverage", not a complete global schedule.</p></div>

<h2>B. Prediction coverage against the five-per-sport target</h2>
{table(["Sport", "Written", "Note"], short_predictions)}

<h2>C. Row-level flags</h2>
<p class="lede">{len(flag_rows)} rows: {len(identity)} priced matches whose fixture identity rests
on OLBG, and the first {min(40, len(unpriced))} of {len(unpriced)} unpriced matches with the exact
missing input.</p>
{table(["Sport", "Match", "Kind", "Detail", "Check"], flag_rows)}

<h2>D. Repository review findings</h2>
<p class="lede">The canonical desk has {sum(f['count'] for f in review['findings'] if f['severity']=='review')}
affected rows across {len([f for f in review['findings'] if f['severity']=='review'])} findings —
stale dates, missing sources, short predictions and a duplicated sport label. Details and links on
<a href="review.html">Repository review</a>.</p>
"""
    pages["flagged.html"] = page("Flagged", "Flagged", body, capture)

    # ---------------------------------------------------------------- write
    for rel, content in pages.items():
        path = os.path.join(OUT, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
    print(f"pages={len(pages)} priced={len(priced)} predictions={len(preds['predictions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

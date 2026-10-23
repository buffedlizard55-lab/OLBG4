#!/usr/bin/env python3
"""Board FX static dashboard generator (GitHub Pages).

Inputs (all committed):  data/session-4502eff5/desk.json, predictions.json,
review.json, flagged.json, verify.json
Output: session-4502eff5/*.html
"""
from __future__ import annotations

import html
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-4502eff5")
OUT = os.path.join(ROOT, "session-4502eff5")

NAV = [
    ("index.html", "Overview"), ("entries.html", "All matches"), ("picks.html", "Picks"),
    ("predictions.html", "Predictions"), ("markets.html", "Markets"), ("coverage.html", "Coverage"),
    ("review.html", "Repo review"), ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"), ("methodology.html", "Method"), ("verification.html", "Verification"),
]


def esc(x):
    return html.escape(str(x if x is not None else ""))


def load(name, default):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        return json.load(open(p))
    return default


def page(title, body, active="", subtitle=""):
    nav = "".join(
        f'<a class="{"on" if href == active else ""}" href="{href}">{esc(label)}</a>' for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} - OLBG4 Board FX</title>
<link rel="stylesheet" href="assets.css">
</head><body>
<header class="top"><div class="wrap">
  <div class="brand"><span class="dot"></span> OLBG4 <span class="muted">/ Board FX desk</span></div>
  <nav>{nav}</nav>
</div></header>
<main class="wrap">
  <div class="crumb"><a href="../index.html">Repository index</a> / <a href="index.html">Board FX</a></div>
  <h1>{esc(title)}</h1>
  {f'<p class="sub">{subtitle}</p>' if subtitle else ''}
  {body}
</main>
<footer class="wrap foot">
  <p>Board FX - session <code>arena/4502eff5-olbg4</code> - every value traced to an official source captured in
  <code>data/session-4502eff5/capture/</code>. Own lines only: no bookmaker or OLBG price is used to originate a number.
  OLBG is used for sport/market taxonomy and listing cross-reference. Unconfirmed values are blank, never inferred.</p>
</footer>
</body></html>"""


CSS = """
:root{--bg:#0f1216;--panel:#171c22;--line:#26303a;--txt:#e8eef4;--mut:#93a3b1;--acc:#39d0a3;--warn:#ffb454;--bad:#ff6b6b;--blue:#5aa9ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:0 18px}
header.top{background:#0b0e12;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
header .wrap{display:flex;flex-wrap:wrap;gap:10px;align-items:center;justify-content:space-between;padding-top:10px;padding-bottom:10px}
.brand{font-weight:700;letter-spacing:.3px}.brand .dot{display:inline-block;width:9px;height:9px;border-radius:50%;background:var(--acc);margin-right:6px}
.muted{color:var(--mut);font-weight:400}
nav a{color:var(--mut);text-decoration:none;margin:0 7px;font-size:13.5px;padding:4px 6px;border-radius:6px}
nav a:hover{color:var(--txt);background:#1d242c}nav a.on{color:#08120f;background:var(--acc);font-weight:700}
.crumb{margin:14px 0 2px;color:var(--mut);font-size:12.5px}.crumb a{color:var(--mut)}
h1{font-size:27px;margin:6px 0 4px;letter-spacing:.2px}h2{font-size:19px;margin:26px 0 8px}h3{font-size:15.5px;margin:18px 0 6px}
.sub{color:var(--mut);margin:0 0 14px;max-width:940px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:14px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card .k{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.08em}
.card .v{font-size:26px;font-weight:750;margin-top:2px}
.card .n{color:var(--mut);font-size:12.5px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13.5px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#131920;color:#b9c7d4;font-size:12px;text-transform:uppercase;letter-spacing:.05em;position:sticky;top:0}
tr:hover td{background:#1a212a}
td.num{text-align:right;font-variant-numeric:tabular-nums}
.tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:700;border:1px solid var(--line)}
.high{background:rgba(57,208,163,.16);color:#7bf0c9;border-color:rgba(57,208,163,.45)}
.medium{background:rgba(90,169,255,.14);color:#9ccdff;border-color:rgba(90,169,255,.4)}
.low{background:rgba(255,180,84,.12);color:#ffcf8f;border-color:rgba(255,180,84,.35)}
.ok{color:#7bf0c9}.no{color:#ff9b9b}.win{color:#7bf0c9}.out{color:var(--mut)}
a{color:var(--blue)}.src{font-size:12px;color:var(--mut);word-break:break-all}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;background:#1d242c;color:var(--mut);font-size:12px;margin:2px 4px 2px 0}
.hero{background:linear-gradient(135deg,#14211d,#111820 60%);border:1px solid #2a4038;border-radius:14px;padding:18px}
.hero h2{margin:0 0 6px;font-size:18px}
.two{display:grid;grid-template-columns:1.35fr .65fr;gap:16px}@media(max-width:900px){.two{grid-template-columns:1fr}}
.note{border-left:3px solid var(--warn);background:#1c1a14;padding:10px 12px;border-radius:8px;color:#f0dcc0;font-size:13.5px;margin:12px 0}
.badnote{border-left-color:var(--bad);background:#1e1416;color:#ffd3d3}
.pred{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin:12px 0}
.pred .head{display:flex;gap:8px;flex-wrap:wrap;align-items:center;justify-content:space-between}
.pred .txt{margin:10px 0 6px}
.pred .facts{color:var(--mut);font-size:12.5px}
footer.foot{border-top:1px solid var(--line);margin-top:34px;padding:18px;color:var(--mut);font-size:12.5px}
code{background:#1b232b;padding:1px 5px;border-radius:5px;font-size:12.5px}
.bar{height:7px;background:#202a34;border-radius:6px;overflow:hidden;min-width:70px}.bar span{display:block;height:100%;background:var(--acc)}
"""


def conf_tag(c):
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(c, "low")
    return f'<span class="tag {cls}">{esc(c)}</span>'


def money(v):
    return f"{v:+d}" if isinstance(v, int) else esc(v)


def row_pick(r):
    p = r.get("pick")
    if not p:
        return '<span class="muted">no line originated</span>'
    win = '<span class="ok">in window</span>' if p["in_window"] else '<span class="out">outside -250/+10000</span>'
    return (f'<b>{esc(p["selection"])}</b><br><span class="muted">{esc(p["market"])} &middot; '
            f'{money(p["fair_american"])} &middot; p={p["fair_prob"]:.3f}</span><br>'
            f'{conf_tag(p["confidence"])} {win}')


def odds_cell(m):
    if not m:
        return '<span class="muted">-</span>'
    return "<br>".join(
        f'{esc(s["label"])} <span class="muted">{money(s["fair_american"])}</span>' for s in m["selections"]
    )


def table(headers, rows, cls=""):
    h = "".join(f"<th>{esc(x)}</th>" for x in headers)
    b = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def build():
    desk = load("desk.json", {"rows": [], "summary": {}, "capture": "", "generated_utc": ""})
    preds = load("predictions.json", {"predictions": []})
    review = load("review.json", {"findings": [], "summary": {}})
    flagged = load("flagged.json", {"flags": []})
    verify = load("verify.json", {"checks": [], "ok": False})
    rows = desk["rows"]
    summary = desk["summary"]
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    open(os.path.join(OUT, "assets.css"), "w").write(CSS)

    priced = [r for r in rows if r.get("pick")]
    highs = sorted([r for r in priced if r["pick"]["confidence"] == "High"],
                   key=lambda r: -r["pick"]["fair_prob"])
    highs_win = [r for r in highs if r["pick"]["in_window"]]
    top = sorted(priced, key=lambda r: -r["pick"]["fair_prob"])[:12]
    total_markets = sum(len(r["markets"]) for r in rows)
    sports_with_picks = sum(1 for s in summary.values() if s["priced"])

    # ---------------------------------------------------------------- overview
    cards = "".join([
        f'<div class="card"><div class="k">Fixtures listed</div><div class="v">{len(rows)}</div><div class="n">official-source rows in the 23 Oct - 8 Nov window</div></div>',
        f'<div class="card"><div class="k">Priced by us</div><div class="v">{len(priced)}</div><div class="n">{sports_with_picks} of 15 sports carry own lines</div></div>',
        f'<div class="card"><div class="k">High confidence</div><div class="v">{len(highs)}</div><div class="n">{len(highs_win)} inside -250 to +10,000</div></div>',
        f'<div class="card"><div class="k">Markets originated</div><div class="v">{total_markets}</div><div class="n">winner, handicap, total (+ sport derivatives)</div></div>',
    ])
    top_rows = []
    for r in top:
        p = r["pick"]
        top_rows.append([
            esc(r["sport"]), f'{esc(r["side_a"])} @ {esc(r["side_b"])}', esc(r["start_utc"][:16].replace("T", " ")),
            f'{esc(p["selection"])}<br><span class="muted">{esc(p["market"])}</span>',
            f'<span class="num">{money(p["fair_american"])}</span>', f'{p["fair_prob"]:.3f}',
            conf_tag(p["confidence"]), esc(r["official_source_name"]),
            f'<a href="{esc(r["official_url"])}">source</a>',
        ])
    cover_rows = []
    for sport, s in summary.items():
        cover_rows.append([
            f'<a href="sports/{esc(s["slug"])}.html">{esc(sport)}</a>',
            f'<span class="num">{s["rows"]}</span>', f'<span class="num">{s["priced"]}</span>',
            f'<span class="num">{s["high"]}</span>', f'<span class="num">{s["high_in_window"]}</span>',
            f'<span class="num">{s["markets"]}</span>',
        ])
    overview = f"""
<div class="hero">
  <h2>Executive summary - upcoming matches, own lines, explicit picks</h2>
  <p class="sub" style="margin:0">Capture <code>{esc(desk["capture"])}</code> of the official governing-body pages, read at
  {esc(desk["generated_utc"])}. Each fixture below is a real scheduled event on the league or tour's own site; the line beside it is
  ours (1 / probability, no margin), and the pick is the selection we would back with its confidence label.</p>
</div>
<div class="grid">{cards}</div>
<h2>Highest-confidence picks available now</h2>
<p class="sub">Sorted by our own probability. Confidence labels: High &ge; 70%, Medium 55-70%, Low &lt; 55%.
The brief's -250 to +10,000 window is shown separately for every pick: at 70% the fair price is about -233, so only a thin band
of probabilities (roughly 70.0-71.4%) can satisfy both rules at once. We publish every High pick, and say plainly which ones sit
outside the price window.</p>
{table(["Sport", "Match", "Start (UTC)", "Selection", "Fair price", "Prob.", "Confidence", "Official source", "Link"], top_rows)}
<h2>Coverage by sport</h2>
{table(["Sport", "Listed", "Priced", "High", "High in window", "Markets"], cover_rows)}
<div class="note">Sports where no official fixture/strength feed could be captured are still listed with their OLBG events and
official pages where they exist; those rows are deliberately unpriced and carry the exact reason on the
<a href="flagged.html">Flagged for review</a> page. Nothing is guessed to fill a gap.</div>
"""
    open(os.path.join(OUT, "index.html"), "w").write(
        page("Overview", overview, "index.html",
             "A 15-sport desk: official match list, our own multi-market lines, a labelled pick for every match, and the high-confidence write-ups."))

    # ---------------------------------------------------------------- entries
    all_rows = []
    for r in sorted(rows, key=lambda x: (x["sport"], x["start_utc"] or "9999", x["side_a"])):
        p = r.get("pick") or {}
        all_rows.append([
            esc(r["sport"]), f'{esc(r["side_a"])}<br><span class="muted">vs</span> {esc(r["side_b"])}',
            esc(r["competition"]), esc((r["start_utc"] or "")[:16].replace("T", " ")), esc(r["venue"]),
            esc(p.get("selection", "")), money(p.get("fair_american")) if p else "",
            conf_tag(p["confidence"]) if p else '<span class="muted">-</span>',
            f'<a href="{esc(r["official_url"])}">official</a>' +
            (f'<br><a href="{esc(r["olbg"]["event_url"])}">OLBG</a>' if r.get("olbg") else ""),
            esc("; ".join(r["flags"])),
        ])
    open(os.path.join(OUT, "entries.html"), "w").write(page(
        "All matches", f'<p class="sub">{len(rows)} rows. Every row links the official page it was read from; blanks mean the value was not published or not captured, never zero.</p>' +
        table(["Sport", "Match", "Competition", "Start (UTC)", "Venue", "Our pick", "Price", "Conf.", "Sources", "Flags"], all_rows),
        "entries.html"))

    # ---------------------------------------------------------------- picks
    pick_rows = []
    for r in sorted(priced, key=lambda x: (-{"High": 2, "Medium": 1, "Low": 0}[x["pick"]["confidence"]], -x["pick"]["fair_prob"])):
        p = r["pick"]
        pick_rows.append([
            esc(r["sport"]), f'{esc(r["side_a"])} @ {esc(r["side_b"])}', esc((r["start_utc"] or "")[:16].replace("T", " ")),
            f'{esc(p["selection"])}<br><span class="muted">{esc(p["market"])}</span>',
            f'{p["fair_prob"]:.3f}', f'{p["fair_decimal"]:.2f}', money(p["fair_american"]),
            conf_tag(p["confidence"]), '<span class="ok">yes</span>' if p["in_window"] else '<span class="out">no</span>',
            f'<a href="{esc(r["official_url"])}">source</a>',
        ])
    open(os.path.join(OUT, "picks.html"), "w").write(page(
        "Picks",
        f'<p class="sub">{len(priced)} labelled picks. "In window" means the fair American price is between -250 and +10,000, '
        f'the range the brief asks us to focus on. {len(highs)} are High confidence, {len(highs_win)} of those inside the window.</p>' +
        table(["Sport", "Match", "Start (UTC)", "Selection", "Prob.", "Dec.", "American", "Conf.", "In window", "Source"], pick_rows),
        "picks.html"))

    # ---------------------------------------------------------------- predictions
    pred_cards = []
    for p in preds["predictions"]:
        pred_cards.append(f'''<div class="pred">
  <div class="head"><div><b>{esc(p["match"])}</b><br><span class="muted">{esc(p["competition"])} &middot; {esc(p["start_utc"][:16].replace("T"," "))} UTC</span></div>
  <div>{conf_tag("High")} <span class="pill">{esc(p["selection"])}</span> <span class="pill">{money(p["fair_american"])}</span></div></div>
  <p class="txt">{esc(p["text"])}</p>
  <div class="facts"><b>Inputs:</b> {esc(p["inputs"])}<br><b>Source:</b> <a href="{esc(p["source_url"])}">{esc(p["source_url"])}</a>
  &nbsp;·&nbsp; <b>OLBG event:</b> {f'<a href="{esc(p["olbg_url"])}">listing</a>' if p.get("olbg_url") else "not listed"}</div>
</div>''')
    open(os.path.join(OUT, "predictions.html"), "w").write(page(
        "High-confidence predictions",
        f'<p class="sub">{len(preds["predictions"])} hand-written predictions, one per High pick, each at least 30 words, naming a real selection and '
        'quoting only numbers printed on the linked official page.</p>' + "".join(pred_cards),
        "predictions.html"))

    # ---------------------------------------------------------------- markets
    mrows = []
    for sport, s in summary.items():
        sr = [r for r in rows if r["sport"] == sport]
        mk = {}
        for r in sr:
            for k, m in r["markets"].items():
                mk.setdefault(k, []).append(m["market_name"])
        for k in ("match_winner", "handicap", "total", "outright"):
            if k in mk:
                mrows.append([esc(sport), esc(k), esc(sorted(set(mk[k]))[0]), f'<span class="num">{len(mk[k])}</span>'])
    open(os.path.join(OUT, "markets.html"), "w").write(page(
        "Markets investigated",
        '<p class="sub">Every market we originated, and for which sport. Markets we could not model from a verified input are listed on the '
        '<a href="flagged.html">flagged page</a> rather than filled with a placeholder.</p>' +
        table(["Sport", "Market key", "Market name", "Rows"], mrows), "markets.html"))

    # ---------------------------------------------------------------- coverage
    cov = []
    for sport, s in summary.items():
        srcs = sorted({r["official_source_name"] for r in rows if r["sport"] == sport and r["official_source_name"]})
        cov.append([f'<a href="sports/{esc(s["slug"])}.html">{esc(sport)}</a>', f'<span class="num">{s["rows"]}</span>',
                    f'<span class="num">{s["priced"]}</span>', f'<span class="num">{s["high"]}</span>',
                    f'<span class="num">{s["high_in_window"]}</span>', esc("; ".join(srcs[:2]))])
    open(os.path.join(OUT, "coverage.html"), "w").write(page(
        "Coverage", '<p class="sub">What each sport has: official fixtures, our own lines, and the source family behind it.</p>' +
        table(["Sport", "Listed", "Priced", "High", "High in window", "Official source family"], cov), "coverage.html"))

    # ---------------------------------------------------------------- sports
    for sport, s in summary.items():
        sr = [r for r in rows if r["sport"] == sport]
        trows = []
        for r in sorted(sr, key=lambda x: (x["start_utc"] or "9999", x["side_a"])):
            trows.append([
                f'{esc(r["side_a"])}<br><span class="muted">vs</span> {esc(r["side_b"])}',
                esc(r["competition"]), esc((r["start_utc"] or "")[:16].replace("T", " ")), esc(r["venue"]),
                odds_cell(r["markets"].get("match_winner")),
                odds_cell(r["markets"].get("handicap")),
                odds_cell(r["markets"].get("total")),
                row_pick(r),
                f'<a href="{esc(r["official_url"])}">official</a>' +
                (f'<br><a href="{esc(r["olbg"]["event_url"])}">OLBG</a>' if r.get("olbg") else ""),
                esc("; ".join(r["flags"])),
            ])
        body = (f'<div class="grid">'
                f'<div class="card"><div class="k">Rows</div><div class="v">{s["rows"]}</div><div class="n">fixtures and listings</div></div>'
                f'<div class="card"><div class="k">Priced</div><div class="v">{s["priced"]}</div><div class="n">own lines originated</div></div>'
                f'<div class="card"><div class="k">High</div><div class="v">{s["high"]}</div><div class="n">{s["high_in_window"]} in the price window</div></div>'
                f'<div class="card"><div class="k">Markets</div><div class="v">{s["markets"]}</div><div class="n">winner/handicap/total</div></div></div>'
                + table(["Match", "Competition", "Start (UTC)", "Venue", "Winner", "Handicap", "Total", "Our pick", "Sources", "Flags"], trows))
        open(os.path.join(OUT, "sports", f'{s["slug"]}.html'), "w").write(
            page(sport, body, "", f'{sport}: official fixtures, our own lines and the pick we would take.'))

    # ---------------------------------------------------------------- review
    fr = []
    for f in review.get("findings", []):
        fr.append([esc(f.get("id", "")), esc(f.get("severity", "")), esc(f.get("dataset", "")),
                   esc(f.get("row", "")), esc(f.get("finding", "")), esc(f.get("verification", "")),
                   f'<a href="{esc(f.get("manual_url", ""))}">manual review</a>' if f.get("manual_url") else ""])
    open(os.path.join(OUT, "review.html"), "w").write(page(
        "Repository review",
        f'<p class="sub">Line-by-line check of the shared datasets against official pages. {len(fr)} findings; '
        'shared files are read-only for this session, so every defect is logged here for the owning session to fix.</p>' +
        table(["ID", "Severity", "Dataset", "Row", "Finding", "How it was checked", "Link"], fr), "review.html"))

    # ---------------------------------------------------------------- flagged
    fl = []
    for f in flagged.get("flags", []):
        fl.append([esc(f.get("id", "")), esc(f.get("sport", "")), esc(f.get("row", "")), esc(f.get("issue", "")),
                   esc(f.get("impact", "")), f'<a href="{esc(f.get("source_url", ""))}">source</a>' if f.get("source_url") else ""])
    open(os.path.join(OUT, "flagged.html"), "w").write(page(
        "Flagged for review",
        f'<p class="sub">{len(fl)} items we could not confirm from an official source, or where sources disagree. '
        'These do not block publication; they are the manual-review queue. Values stay blank rather than inferred.</p>' +
        table(["ID", "Sport", "Row", "Issue", "Impact", "Source"], fl), "flagged.html"))

    # ---------------------------------------------------------------- sources
    srows = {}
    for r in rows:
        if r["official_url"]:
            srows[(r["official_source_name"], r["official_url"])] = srows.get((r["official_source_name"], r["official_url"]), 0) + 1
    srows = [[esc(n), f'<a href="{esc(u)}">{esc(u)}</a>', f'<span class="num">{c}</span>']
             for (n, u), c in sorted(srows.items())]
    open(os.path.join(OUT, "sources.html"), "w").write(page(
        "Sources", '<p class="sub">Every official page this desk read, with the number of rows that cite it. Raw bytes and their SHA-256 hashes are in the capture folder.</p>' +
        table(["Source", "URL", "Rows"], srows), "sources.html"))

    # ---------------------------------------------------------------- methodology
    meth = f"""
<h2>What this desk does</h2>
<p>It rebuilds the OLBG sport list (15 sports in scope) from OLBG's own sport hubs, then goes to the governing body for every
fixture, result and table it needs. OLBG supplies taxonomy and the listing link; it never supplies a number that goes into a line.</p>
<h2>Line origination</h2>
<ul>
<li><b>Ice hockey</b> (NHL, Liiga): independent-Poisson goals from the official standings' goals-for and goals-against per game,
with a 1.06 home factor, then exact win/draw/tie split, puck line and total.</li>
<li><b>Basketball</b> (EuroLeague, EuroCup): normal point-margin model from points for/against per game in the official game feed,
with a 1.5-point home court and a 12.5-point standard deviation.</li>
<li><b>Baseball</b> (MLB): independent-Poisson runs from the official season team rates, with the listed probable pitchers
recorded as an input where the official schedule publishes them.</li>
<li><b>Volleyball</b> (SuperLega): point-ratio to set probability, then an exact best-of-five set distribution.</li>
<li><b>Tennis / snooker</b>: logistic on the official ranking/seeding gap, then the exact best-of-n distribution.</li>
<li><b>Golf / motor racing</b>: remaining-hole Monte Carlo on the official leaderboard, and a Plackett-Luce on official championship
points. Both are capped at Medium confidence because a 100-player field or a 20-driver grid cannot be a 70% proposition.</li>
</ul>
<p>Every price is 1 / probability with no bookmaker margin, so the two sides of a market sum to 1.000.</p>
<h2>Calibration and caps</h2>
<p>Model probabilities are shrunk toward 50% by a documented constant (0.88-0.90 for hockey, 0.80-0.85 for basketball/baseball)
and clamped to a sport-specific band. Samples below the sport's minimum (10 games for hockey, 4 for basketball, 5 matches for
volleyball) cap the row at Medium. A pick is <b>High</b> only at p &ge; 0.70.</p>
<h2>The -250 to +10,000 window</h2>
<p>At p = 0.70 the fair American price is -233; at -250 it is 0.714. So the brief's two rules overlap only in p &isin; [0.700, 0.714].
We therefore report, for every pick, whether it is inside the window, and we do not relabel an out-of-window favourite as something
it is not.</p>
<h2>Verification</h2>
<p>Each row keeps the capture id and exact URL it came from. <code>verify.py</code> re-derives every price from its probability,
re-checks the window, the confidence rule, the prediction length and uniqueness, and that every row's source URL exists in the
committed manifest. See <a href="verification.html">Verification</a>.</p>
"""
    open(os.path.join(OUT, "methodology.html"), "w").write(page("Method", meth, "methodology.html"))

    # ---------------------------------------------------------------- verification
    vrows = [[esc(c.get("name", "")), '<span class="ok">PASS</span>' if c.get("ok") else '<span class="no">FAIL</span>', esc(c.get("detail", ""))]
             for c in verify.get("checks", [])]
    open(os.path.join(OUT, "verification.html"), "w").write(page(
        "Verification",
        f'<p class="sub">Gate result: <b class="{"ok" if verify.get("ok") else "no"}">{"PASS" if verify.get("ok") else "FAIL"}</b> at {esc(verify.get("generated_utc", ""))}.</p>' +
        table(["Check", "Result", "Detail"], vrows), "verification.html"))

    print("built", len([f for f in os.listdir(OUT) if f.endswith('.html')]), "pages")


if __name__ == "__main__":
    build()

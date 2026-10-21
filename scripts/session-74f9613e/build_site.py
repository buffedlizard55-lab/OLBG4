#!/usr/bin/env python3
"""Render the static dashboard into site/ from the JSON data files.

Run: python3 scripts/build_site.py
"""
import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-74f9613e")
SITE = os.environ.get("SITE_DIR", os.path.join(ROOT, "session-74f9613e"))

BUILD_TIME = "2026-10-21T09:00:00Z"

SPORTS = [
    ("ice-hockey", "Ice Hockey", "NHL"),
    ("basketball", "Basketball", "NBA"),
    ("baseball", "Baseball", "MLB"),
    ("rugby-union", "Rugby Union", "URC"),
    ("snooker", "Snooker", "WST"),
    ("cricket", "Cricket", "ICC"),
    ("darts", "Darts", "PDC"),
    ("tennis", "Tennis", "ATP / WTA"),
    ("gaelic-football", "Gaelic Football", "GAA"),
]


def esc(value):
    return html.escape(str(value), quote=True)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def badge(conf):
    label = {"high": "High", "medium": "Medium", "low": "Low", "unrated": "Unrated"}.get(conf, conf)
    return f'<span class="badge badge--{esc(conf)}">{esc(label)}</span>'


def src_links(ids, sources):
    out = []
    for sid in ids:
        s = sources.get(sid)
        if not s:
            continue
        cls = "src src--official" if s["official"] else "src"
        out.append(f'<a class="{cls}" href="{esc(s["url"])}" rel="noopener">{esc(sid)} · {esc(s["publisher"])}</a>')
    return " ".join(out) or '<span class="muted">none</span>'


CSS = """
:root{
  --bg:#f5f7fb; --card:#ffffff; --ink:#101828; --muted:#5b6478; --line:#e4e8f0;
  --accent:#1f5eff; --accent-soft:#eaf0ff; --high:#0f7b4f; --high-bg:#e6f5ee;
  --med:#8a5b00; --med-bg:#fdf3df; --low:#475467; --low-bg:#eef1f6;
  --unrated:#9b1c1c; --unrated-bg:#fdeaea;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header.top{background:#0b1220;color:#fff;padding:14px 24px;position:sticky;top:0;z-index:20}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.brand{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}
.brand strong{font-size:17px;letter-spacing:.2px}
.brand span{color:#94a3b8;font-size:13px}
nav.main{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
nav.main a{color:#cbd5e1;font-size:13.5px;padding:6px 10px;border-radius:8px}
nav.main a:hover{background:#1e293b;text-decoration:none;color:#fff}
nav.main a.active{background:#1d4ed8;color:#fff}
main{padding:26px 0 60px}
h1{font-size:27px;margin:14px 0 6px;letter-spacing:-.3px}
h2{font-size:19px;margin:32px 0 10px}
h3{font-size:15.5px;margin:20px 0 8px}
p.lede{color:var(--muted);max-width:80ch;margin:0 0 18px}
.grid{display:grid;gap:14px}
.grid--kpi{grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.grid--two{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px}
.kpi .n{font-size:30px;font-weight:700;letter-spacing:-1px}
.kpi .l{color:var(--muted);font-size:13px;margin-top:2px}
.kpi .s{color:var(--muted);font-size:12px;margin-top:6px}
.tablewrap{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:auto}
table{border-collapse:collapse;width:100%;font-size:13.6px}
th,td{padding:9px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f8fafc;color:var(--muted);font-weight:600;font-size:12.4px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#fbfcfe}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.badge--high{color:var(--high);background:var(--high-bg)}
.badge--medium{color:var(--med);background:var(--med-bg)}
.badge--low{color:var(--low);background:var(--low-bg)}
.badge--unrated{color:var(--unrated);background:var(--unrated-bg)}
.pill{display:inline-block;padding:2px 8px;border-radius:6px;background:var(--accent-soft);color:#1e40af;font-size:12px;font-weight:600}
.src{display:inline-block;margin:1px 4px 1px 0;padding:1px 7px;border:1px solid var(--line);border-radius:6px;
  background:#fff;font-size:11.6px;color:#334155;white-space:nowrap}
.src--official{border-color:#bfe3d0;background:#f2fbf6;color:#0f7b4f}
.muted{color:var(--muted)}
.small{font-size:12.4px}
.foot{border-top:1px solid var(--line);margin-top:40px;padding:20px 0 40px;color:var(--muted);font-size:12.6px}
.note{background:#fffbea;border:1px solid #f4e3a8;border-radius:10px;padding:12px 14px;font-size:13.4px;color:#5b4700}
.warn{background:var(--unrated-bg);border:1px solid #f3c7c7;border-radius:10px;padding:12px 14px;font-size:13.4px;color:#7a1414}
.pred{border-left:3px solid var(--accent);padding:10px 14px;background:#fbfcff;border-radius:0 8px 8px 0;margin:10px 0}
.pred .who{font-weight:700}
.pred p{margin:6px 0}
.tagrow{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0 2px}
.tag{background:#eef2f9;color:#334155;border-radius:6px;padding:2px 8px;font-size:12px}
.odds{font-variant-numeric:tabular-nums;font-weight:600}
h2 .count{font-weight:400;color:var(--muted);font-size:14px}
"""


def page(title, body, active="", depth=0):
    prefix = "" if depth == 0 else ""
    nav_items = [
        ("index.html", "Overview"),
        ("picks.html", "Picks"),
        ("markets.html", "All markets"),
        ("predictions.html", "Predictions"),
        ("coverage.html", "Sport coverage"),
        ("findings.html", "Findings"),
        ("flagged.html", "Flagged for review"),
        ("methodology.html", "Method"),
        ("sources.html", "Sources"),
    ]
    nav = "".join(
        f'<a class="{"active" if href == active else ""}" href="{href}">{label}</a>'
        for href, label in nav_items
    )
    links = "".join(f'<li><a href="{href}">{label}</a></li>' for href, label in nav_items)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG Reverse-Engineering Dashboard</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <div class="brand">
      <strong>OLBG Reverse-Engineering Dashboard</strong>
      <span>Independent lines · verified inputs only · snapshot {esc(BUILD_TIME[:10])}</span>
    </div>
    <nav class="main">{nav}</nav>
  </div>
</header>
<main><div class="wrap">
{body}
<div class="foot">
  <p><strong>Method:</strong> every line is generated by a documented deterministic model from official-source inputs. No bookmaker prices were read or copied.
  <strong>Status:</strong> research output, not betting advice. 18+. Betting involves risk.</p>
  <p>Snapshot captured {esc(BUILD_TIME)}. Build artefacts generated by <code>scripts/build_site.py</code>.
  Source links open the publisher's page; some publishers render tables with JavaScript and may look different in a browser than in the capture used here.</p>
  <p>Unverified or incomplete items are never hidden — see <a href="flagged.html">Flagged for review</a>.</p>
</div>
</div></main>
</body>
</html>
"""


def market_cells(m):
    """Return (moneyline, handicap, total) cell markup for a priced match."""
    if not m.get("priced"):
        return ("", "", "")
    ml = [s for s in m["selections"] if s["market"] == "moneyline"]
    hc = [s for s in m["selections"] if s["market"] == "handicap"]
    tt = [s for s in m["selections"] if s["market"] == "total"]
    ml_html = "<br>".join(
        f'<span class="small">{esc(s["selection"])}</span> <span class="odds">{s["odds"]:.2f}</span>'
        for s in ml)
    hc_html = "<br>".join(
        f'<span class="small">{esc(s["selection"])}</span> <span class="odds">{s["odds"]:.2f}</span>'
        for s in hc) or '<span class="muted">—</span>'
    tt_html = "<br>".join(
        f'<span class="small">{esc(s["selection"])}</span> <span class="odds">{s["odds"]:.2f}</span>'
        for s in tt) or '<span class="muted">not originated</span>'
    return (ml_html, hc_html, tt_html)


def match_table(matches, sources, include_sport=False):
    head = "<tr><th>Date / time (as published)</th>"
    if include_sport:
        head += "<th>Sport</th>"
    head += ("<th>Match</th><th>Venue</th><th>Money line (our price)</th>"
             "<th>Handicap</th><th>Total</th><th>Pick</th><th>Confidence</th><th>Sources</th></tr>")
    rows = []
    for m in matches:
        ml, hc, tt = market_cells(m)
        venue_html = esc(m["venue"]) if m["venue"] else '<span class="muted">not confirmed</span>'
        empty = '<span class="muted">—</span>'
        ml_html = ml or empty
        sport_cell = f'<td><a href="{esc(m["sport_slug"])}.html">{esc(m["sport"])}</a></td>' if include_sport else ""
        if m.get("priced"):
            pick = (f'{esc(m["pick"]["selection"])}<br><span class="small muted">'
                    f'{esc(m["pick"]["market"])} @ {m["pick"]["odds"]:.2f} · model p={m["pick"]["prob"]:.3f}</span>')
            conf = badge(m["confidence"])
        else:
            pick = '<span class="muted">not originated</span>'
            conf = badge("unrated")
        rows.append(
            f'<tr><td>{esc(m["start_local"])}</td>{sport_cell}'
            f'<td><strong>{esc(m["away"]["name"])}</strong> at <strong>{esc(m["home"]["name"])}</strong><br>'
            f'<span class="small muted">{esc(m["competition"])}</span></td>'
            f'<td class="small">{venue_html}</td>'
            f'<td>{ml_html}</td><td>{hc}</td><td>{tt}</td>'
            f'<td>{pick}</td><td>{conf}</td>'
            f'<td class="small">{src_links(m["fixture_sources"] + m["input_sources"], sources)}</td></tr>'
        )
    return f'<div class="tablewrap"><table>{head}{"".join(rows)}</table></div>'


def build():
    matches_doc = load("matches.json")
    sources_doc = load("sources.json")
    coverage_doc = load("coverage.json")
    inventory_doc = load("olbg_inventory.json")
    preds_doc = load("predictions.json")
    findings_doc = load("findings.json")

    matches = matches_doc["matches"]
    sources = {s["id"]: s for s in sources_doc["sources"]}
    preds = {p["match_id"]: p for p in preds_doc["predictions"]}
    by_sport = {}
    for m in matches:
        by_sport.setdefault(m["sport_slug"], []).append(m)

    priced = [m for m in matches if m.get("priced")]
    unpriced = [m for m in matches if not m.get("priced")]
    counts = {"high": 0, "medium": 0, "low": 0}
    for m in priced:
        counts[m["confidence"]] = counts.get(m["confidence"], 0) + 1
    markets_total = sum(len(m["selections"]) for m in priced)

    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)

    # ---------------- Overview ----------------
    kpis = f"""
<div class="grid grid--kpi">
  <div class="card kpi"><div class="n">{len(matches)}</div><div class="l">matches in the verified fixture set</div>
    <div class="s">across {len(by_sport)} sports with verified fixtures</div></div>
  <div class="card kpi"><div class="n">{len(priced)}</div><div class="l">matches with our own lines</div>
    <div class="s">{markets_total} priced selections</div></div>
  <div class="card kpi"><div class="n">{counts['high']}</div><div class="l">high-confidence picks</div>
    <div class="s">each with a written prediction</div></div>
  <div class="card kpi"><div class="n">{counts['medium']} / {counts['low']}</div><div class="l">medium / low picks</div>
    <div class="s">confidence bands from the model</div></div>
  <div class="card kpi"><div class="n">{len(inventory_doc['rows']) + len(unpriced)}</div><div class="l">flagged items</div>
    <div class="s">published, unpriced, linked</div></div>
</div>"""

    top_picks = sorted([m for m in priced if m["confidence"] == "high"],
                       key=lambda m: -m["pick"]["prob"])
    rows = []
    for m in top_picks:
        rows.append(
            f'<tr><td><a href="{esc(m["sport_slug"])}.html">{esc(m["sport"])}</a></td>'
            f'<td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}<br>'
            f'<span class="small muted">{esc(m["start_local"])}</span></td>'
            f'<td><strong>{esc(m["pick"]["selection"])}</strong></td>'
            f'<td class="num">{m["pick"]["prob"]:.3f}</td>'
            f'<td class="num">{m["pick"]["odds"]:.2f}</td>'
            f'<td>{badge(m["confidence"])}</td>'
            f'<td class="small"><a href="predictions.html#{esc(m["id"])}">read prediction</a></td></tr>')
    picks_table = ("<div class=\"tablewrap\"><table><tr><th>Sport</th><th>Match</th><th>Pick</th>"
                   "<th class=\"num\">Model probability</th><th class=\"num\">Our price</th>"
                   "<th>Confidence</th><th></th></tr>" + "".join(rows) + "</table></div>")

    sport_cards = ""
    for slug, sport_name, short in SPORTS:
        ms = by_sport.get(slug, [])
        pr = [m for m in ms if m.get("priced")]
        hi = sum(1 for m in pr if m["confidence"] == "high")
        if pr:
            stat = f"{len(pr)} priced · {hi} high confidence"
        elif ms:
            stat = f"{len(ms)} listed · not priced"
        else:
            inv_n = sum(1 for r in inventory_doc["rows"] if r["sport"] == sport_name)
            stat = f"{inv_n} listed · not priced" if inv_n else "not covered this cycle"
        sport_cards += (f'<a class="card" href="{slug}.html" style="text-decoration:none;color:inherit">'
                        f'<h3 style="margin-top:0">{esc(sport_name)}</h3>'
                        f'<div class="small muted">{esc(short)}</div>'
                        f'<div class="small" style="margin-top:6px">{esc(stat)}</div></a>')

    cov_rows = []
    for c in coverage_doc["sports"]:
        status_map = {
            "priced": "pill", "partially priced": "pill", "fixture-only": "tag",
            "unverified inventory": "tag", "no-match-market": "tag",
            "not covered": "tag", "excluded by brief": "tag",
        }
        cls = status_map.get(c["status"], "tag")
        cov_rows.append(
            f'<tr><td><strong>{esc(c["sport"])}</strong></td><td><span class="{cls}">{esc(c["status"])}</span></td>'
            f'<td class="num">{c["fixtures_listed"]}</td><td class="num">{c["fixtures_priced"]}</td>'
            f'<td class="small">{esc(c["note"])}</td></tr>')
    cov_table = ("<div class=\"tablewrap\"><table><tr><th>Sport</th><th>Status</th><th class=\"num\">Fixtures listed</th>"
                 "<th class=\"num\">Priced</th><th>Note</th></tr>" + "".join(cov_rows) + "</table></div>")

    body = f"""
<h1>Overview</h1>
<p class="lede">A reverse-engineered view of OLBG's in-scope fixture list, rebuilt from official primary sources, with our own
money-line, handicap and total prices for every match where every input could be verified. Anything that could not be verified is
left blank and published on the Flagged for Review page.</p>
{kpis}

<h2>High-confidence picks <span class="count">({len(top_picks)} of {len(priced)} priced matches)</span></h2>
{picks_table}

<h2>Browse by sport</h2>
<div class="grid grid--kpi">
{sport_cards}
</div>

<h2>Market coverage by sport</h2>
{cov_table}

<h2>How to read this site</h2>
<div class="grid grid--two">
  <div class="card"><h3>Our own lines</h3>
    <p class="small">Each match page shows a money line, a handicap and (where the official table supports it) a total, all priced
    from the model with a 4% two-way / 5% three-way overround. The model never reads a bookmaker price, so the numbers are genuinely
    independent.</p></div>
  <div class="card"><h3>Confidence</h3>
    <p class="small">High = model probability of 0.65 or better, medium = 0.57 to 0.65, low = below 0.57. Confidence describes the
    model's own probability, not a guarantee, and every high pick is checked to have complete official inputs.</p></div>
  <div class="card"><h3>Verification rule</h3>
    <p class="small">Every table row links to the official page that confirms its fixture and to the official table that supplies its
    inputs. If a value could not be confirmed it is blank and flagged; it is never inferred.</p></div>
  <div class="card"><h3>What is excluded</h3>
    <p class="small">Horse racing, football (soccer), American football, boxing, cycling, and the brief's specials category are out of
    scope. The reason each in-scope sport is priced, unpriced or uncovered is on the Sport coverage page.</p></div>
</div>
"""
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Overview", body, active="index.html"))

    # ---------------- Picks ----------------
    order = {"high": 0, "medium": 1, "low": 2}
    all_picks = sorted(priced, key=lambda m: (order.get(m["confidence"], 3), -m["pick"]["prob"]))
    rows = []
    for m in all_picks:
        rows.append(
            f'<tr><td><a href="{esc(m["sport_slug"])}.html">{esc(m["sport"])}</a></td>'
            f'<td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}<br>'
            f'<span class="small muted">{esc(m["competition"])} · {esc(m["start_local"])}</span></td>'
            f'<td><strong>{esc(m["pick"]["selection"])}</strong><br><span class="small muted">{esc(m["pick"]["market"])}</span></td>'
            f'<td class="num">{m["pick"]["prob"]:.3f}</td><td class="num">{m["pick"]["odds"]:.2f}</td>'
            f'<td>{badge(m["confidence"])}</td>'
            f'<td class="small">{src_links(m["input_sources"], sources)}</td></tr>')
    body = f"""
<h1>Picks</h1>
<p class="lede">One pick per priced match — the model's match winner, with the price the model itself would offer and the confidence
band that probability falls into. Handicap and total prices for the same matches are on each sport page and on the All markets page.</p>
<div class="note"><strong>{counts['high']} high</strong> · {counts['medium']} medium · {counts['low']} low.
High-confidence picks each have a written prediction on the <a href="predictions.html">Predictions</a> page.</div>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Match</th><th>Pick</th><th class="num">Model probability</th><th class="num">Our price</th><th>Confidence</th><th>Input sources</th></tr>
{"".join(rows)}
</table></div>
"""
    with open(os.path.join(SITE, "picks.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Picks", body, active="picks.html"))

    # ---------------- Sport pages ----------------
    for slug, sport_name, short in SPORTS:
        ms = by_sport.get(slug, [])
        p = [m for m in ms if m.get("priced")]
        hc = sum(1 for m in p if m["confidence"] == "high")
        md = sum(1 for m in p if m["confidence"] == "medium")
        lo = sum(1 for m in p if m["confidence"] == "low")

        if ms:
            head = f"""
<h1>{esc(sport_name)}</h1>
<p class="lede">Sport hub {esc(short)}. {len(ms)} fixtures confirmed and listed, {len(p)} priced from verified inputs
({hc} high, {md} medium, {lo} low confidence).</p>
{match_table(ms, sources)}
"""
        else:
            cov = next((c for c in coverage_doc["sports"] if c["sport"] == sport_name), None)
            inv = [r for r in inventory_doc["rows"] if r["sport"] == sport_name]
            inv_rows = ""
            if inv:
                body_rows = []
                for r in inv:
                    official = (f'<a href="{esc(r["official_source"])}" rel="noopener">official fixture page</a>'
                                if r["official_source"] else '<span class="unrated">none found</span>')
                    body_rows.append(
                        f'<tr><td>{esc(r["competition"])}<br><span class="small muted">{esc(r["start"])}</span></td>'
                        f'<td>{esc(r["home"])} v {esc(r["away"])}</td>'
                        f'<td class="small">{esc(r["olbg_market_example"])}</td><td class="small">{official}</td>'
                        f'<td><span class="badge badge--unrated">{esc(r["status"])}</span></td>'
                        f'<td class="small">{esc(r["status_reason"])}</td></tr>')
                inv_rows = f"""
<h2>Fixtures captured <span class="count">({len(inv)})</span></h2>
<div class="tablewrap"><table>
<tr><th>Competition / time</th><th>Match</th><th>OLBG market seen</th><th>Official source</th><th>Status</th><th>Why it is not priced</th></tr>
{"".join(body_rows)}
</table></div>"""
            head = f"""
<h1>{esc(sport_name)}</h1>
<p class="lede">{esc(cov["note"]) if cov else "Not covered in this cycle."}</p>
<div class="warn">No line was originated for {esc(sport_name)} in this snapshot. Everything captured for the sport is listed below and
mirrored on the <a href="flagged.html">Flagged for review</a> page, with the exact reason each item was not priced.</div>
{inv_rows}
"""

        # selections table
        sel_rows = []
        for m in p:
            for s in m["selections"]:
                sel_rows.append(
                    f'<tr><td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}</td>'
                    f'<td>{esc(s["market"])}</td><td>{esc(s["selection"])}</td>'
                    f'<td class="num">{s["prob"]:.3f}</td><td class="num">{s["odds"]:.2f}</td>'
                    f'<td class="small">{esc(m["model_view"].get("note", ""))}</td></tr>')
        if sel_rows:
            analysis = f"""
<h2>All originated markets</h2>
<div class="tablewrap"><table>
<tr><th>Match</th><th>Market</th><th>Selection</th><th class="num">Model probability</th><th class="num">Our price</th><th>Model note</th></tr>
{"".join(sel_rows)}
</table></div>
"""
        else:
            analysis = ""

        # model view per match
        mv_rows = []
        for m in p:
            mv = m["model_view"]
            detail = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in mv.items() if k != "note")
            mv_rows.append(
                f'<tr><td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}</td>'
                f'<td class="small">{esc(detail)}</td>'
                f'<td class="small">{src_links(m["input_sources"], sources)}</td></tr>')
        mv_html = ""
        if mv_rows:
            mv_html = f"""
<h2>Model inputs and outputs</h2>
<div class="tablewrap"><table><tr><th>Match</th><th>Model view</th><th>Official input source</th></tr>
{"".join(mv_rows)}</table></div>
"""

        body = head + analysis + mv_html
        with open(os.path.join(SITE, f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(sport_name, body, active=f"{slug}.html"))

    # ---------------- All markets ----------------
    rows = []
    for m in sorted(priced, key=lambda x: (x["sport"], x["start_local"])):
        ml = {s["selection"]: s for s in m["selections"] if s["market"] == "moneyline"}
        hc = [s for s in m["selections"] if s["market"] == "handicap"]
        tt = [s for s in m["selections"] if s["market"] == "total"]
        ml_txt = " / ".join(f'{esc(k)} {v["odds"]:.2f}' for k, v in ml.items())
        hc_txt = "<br>".join(f'{esc(s["selection"])} {s["odds"]:.2f} ({s["prob"]:.3f})' for s in hc)
        tt_txt = "<br>".join(f'{esc(s["selection"])} {s["odds"]:.2f} ({s["prob"]:.3f})' for s in tt) or '<span class="muted">not originated</span>'
        rows.append(
            f'<tr><td><a href="{esc(m["sport_slug"])}.html">{esc(m["sport"])}</a></td>'
            f'<td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}</td>'
            f'<td class="small">{ml_txt}</td><td class="small">{hc_txt}</td><td class="small">{tt_txt}</td>'
            f'<td class="small">{src_links(m["input_sources"], sources)}</td></tr>')
    body = f"""
<h1>All markets</h1>
<p class="lede">Every originated price in the snapshot: money line, handicap and total for each of the {len(priced)} priced matches
({markets_total} selections). Probabilities in brackets are the model's own, before the overround is applied.</p>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Match</th><th>Money line</th><th>Handicap</th><th>Total</th><th>Input sources</th></tr>
{"".join(rows)}
</table></div>
"""
    with open(os.path.join(SITE, "markets.html"), "w", encoding="utf-8") as fh:
        fh.write(page("All markets", body, active="markets.html"))

    # ---------------- Predictions ----------------
    blocks = []
    for p in preds_doc["predictions"]:
        m = next((x for x in matches if x["id"] == p["match_id"]), None)
        if not m:
            continue
        facts = "".join(
            f'<li>{esc(f["claim"])} — <a href="{esc(sources[f["source"]]["url"])}" rel="noopener">'
            f'{esc(f["source"])} · {esc(sources[f["source"]]["publisher"])}</a></li>' for f in p["facts"])
        blocks.append(f"""
<div class="card" id="{esc(m['id'])}">
  <div class="tagrow"><span class="tag">{esc(m['sport'])}</span><span class="tag">{esc(m['competition'])}</span>
    <span class="tag">{esc(m['start_local'])}</span>{badge(m['confidence'])}</div>
  <h3>{esc(m['away']['name'])} at {esc(m['home']['name'])}</h3>
  <div class="pred"><div class="who">{esc(p['selection'])} — {esc(p['market'])} @ {m['pick']['odds']:.2f}
    (model p={m['pick']['prob']:.3f})</div>
    <p>{esc(p['text'])}</p></div>
  <details><summary class="small muted">Verified facts used in this prediction ({len(p['facts'])})</summary>
    <ul class="small">{facts}</ul></details>
</div>""")
    body = f"""
<h1>High-confidence predictions</h1>
<p class="lede">Written only for high-confidence picks. Each prediction names the selection, the verified form lines and the recent
match history behind it, and every factual claim is listed underneath with the official page it came from.</p>
<div class="grid grid--two">{"".join(blocks)}</div>
"""
    with open(os.path.join(SITE, "predictions.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Predictions", body, active="predictions.html"))

    # ---------------- Coverage ----------------
    rows = []
    for c in coverage_doc["sports"]:
        rows.append(
            f'<tr><td><strong>{esc(c["sport"])}</strong><br><span class="small muted">OLBG id {c["olbg_id"]}</span></td>'
            f'<td>{esc(c["status"])}</td><td class="num">{c["fixtures_listed"]}</td><td class="num">{c["fixtures_priced"]}</td>'
            f'<td class="small">{esc(c["note"])}</td><td class="small">{src_links(c["sources"], sources)}</td></tr>')
    taxonomy = "".join(
        f'<tr><td>{esc(t["sport"])}</td><td class="num">{t["olbg_id"]}</td><td>{esc(t["scope"])}</td>'
        f'<td class="small"><a href="{esc(t["hub_url"])}" rel="noopener">{esc(t["hub_url"].replace("https://www.", ""))}</a></td></tr>'
        for t in inventory_doc["olbg_sport_taxonomy"])
    body = f"""
<h1>Sport coverage</h1>
<p class="lede">The brief asks for every sport except soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling and
specials. This page records, sport by sport, what was captured, what was priced, and — where nothing was priced — exactly why.</p>
<h2>Coverage decision per sport</h2>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Status</th><th class="num">Fixtures listed</th><th class="num">Priced</th><th>Reason / note</th><th>Sources</th></tr>
{"".join(rows)}
</table></div>
<h2>Reverse-engineered OLBG sport taxonomy</h2>
<div class="tablewrap"><table><tr><th>Sport</th><th class="num">OLBG id</th><th>Brief scope</th><th>OLBG hub URL</th></tr>{taxonomy}</table></div>
"""
    with open(os.path.join(SITE, "coverage.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Sport coverage", body, active="coverage.html"))

    # ---------------- Findings ----------------
    cards = "".join(
        f'<div class="card"><h3>{esc(f["title"])}</h3><p class="small">{esc(f["text"])}</p>'
        f'<p class="small">{src_links(f["sources"], sources)}</p></div>'
        for f in findings_doc["findings"])
    body = f"""
<h1>Findings</h1>
<p class="lede">What the reverse-engineering pass actually found, including the parts that did not work. Each finding links to the
source that supports it.</p>
<div class="grid grid--two">{cards}</div>
"""
    with open(os.path.join(SITE, "findings.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Findings", body, active="findings.html"))

    # ---------------- Flagged ----------------
    inv_rows = []
    for r in inventory_doc["rows"]:
        official = (f'<a href="{esc(r["official_source"])}" rel="noopener">official fixture page</a>'
                    if r["official_source"] else '<span class="unrated">none found</span>')
        inv_rows.append(
            f'<tr><td>{esc(r["sport"])}</td><td>{esc(r["competition"])}<br><span class="small muted">{esc(r["start"])}</span></td>'
            f'<td>{esc(r["home"])} v {esc(r["away"])}</td>'
            f'<td class="small">{esc(r["olbg_market_example"])}<br>'
            f'<a href="{esc(r["olbg_url"])}" rel="noopener">OLBG listing</a></td>'
            f'<td class="small">{official}</td><td><span class="badge badge--unrated">{esc(r["status"])}</span></td>'
            f'<td class="small">{esc(r["status_reason"])}</td></tr>')

    un_rows = []
    for m in unpriced:
        un_rows.append(
            f'<tr><td>{esc(m["sport"])}</td><td>{esc(m["competition"])}<br><span class="small muted">{esc(m["start_local"])}</span></td>'
            f'<td>{esc(m["away"]["name"])} at {esc(m["home"]["name"])}</td>'
            f'<td class="small">{src_links(m["fixture_sources"], sources)}</td>'
            f'<td><span class="badge badge--unrated">unpriced</span></td>'
            f'<td class="small">{esc(m["market_status"])}. {esc(m["notes"])}</td></tr>')

    body = f"""
<h1>Flagged for review</h1>
<div class="warn"><strong>These items are published deliberately incomplete.</strong> They are not hidden and they are not priced.
Where a fixture could not be confirmed from an official source, the official-source column says "none found" rather than showing a
link that would lend false confidence. Nothing on this page blocks the rest of the site.</div>

<h2>1. Fixtures listed but not priced <span class="count">({len(unpriced)})</span></h2>
<p class="small muted">Matches whose fixture is officially confirmed but where at least one model input was missing from the captured
official table. The missing input is named in the last column.</p>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Competition / time</th><th>Match</th><th>Official fixture source</th><th>Status</th><th>Reason</th></tr>
{"".join(un_rows)}
</table></div>

<h2>2. Inventory captured, no official confirmation <span class="count">({len(inventory_doc['rows'])})</span></h2>
<p class="small muted">Pairings or races seen on OLBG but not confirmed on an official organiser page through this environment, or
confirmed as fixtures without the inputs needed to originate a price.</p>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Competition / time</th><th>Match</th><th>OLBG listing</th><th>Official source</th><th>Status</th><th>Reason</th></tr>
{"".join(inv_rows)}
</table></div>

<h2>3. Sports with nothing to price</h2>
<div class="tablewrap"><table><tr><th>Sport</th><th>Status</th><th>Reason</th></tr>
<tr><td>Rugby League</td><td><span class="badge badge--low">no match market</span></td>
<td>OLBG's rugby-league hub listed only outright markets at capture time. <a href="https://www.olbg.com/betting-tips/Rugby_League/All_Rugby_League/All_Events/10" rel="noopener">OLBG listing</a></td></tr>
<tr><td>Golf · Motor Racing · Greyhounds · Handball · Volleyball · eSports · Aussie Rules</td>
<td><span class="badge badge--low">not covered</span></td>
<td>Present in the OLBG taxonomy (see <a href="coverage.html">Sport coverage</a>) but not captured in this cycle; no official fixtures or inputs were verified, so nothing is published as a price.</td></tr>
</table></div>
"""
    with open(os.path.join(SITE, "flagged.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Flagged for review", body, active="flagged.html"))

    # ---------------- Methodology ----------------
    body = """
<h1>Method</h1>
<p class="lede">The whole point of this build is that the numbers can be audited. This page states every formula, every constant and
every place where a judgement was made.</p>

<h2>1. Capture</h2>
<div class="tablewrap"><table>
<tr><th>Step</th><th>What was captured</th><th>How</th></tr>
<tr><td>Inventory</td><td>OLBG's sport taxonomy and its in-scope fixture lists</td><td>Read the OLBG betting-tips sitemap and each sport's
"all events" page. Only day/time, participants and the market OLBG displayed were read — no OLBG prices were used as inputs.</td></tr>
<tr><td>Verification</td><td>Official fixture confirmation and model inputs</td><td>Official league, tour and federation pages: nhl.com,
nba.com, mlb.com, wst.tv, stats.unitedrugby.com, icc-cricket.com.</td></tr>
<tr><td>Transcription</td><td>Numeric inputs</td><td><code>scripts/prepare_inputs.py</code> — every table is copied field by field from the
official page. Values that were not on the page are omitted.</td></tr>
</table></div>

<h2>2. The model</h2>
<p class="small">Every match is priced by a deterministic function. No bookmaker price is an input, so there is no copying. Margins are
applied only at the last step: 4% overround on two-way markets, 5% on three-way markets. Decimal odds = 1 / (probability × overround).</p>
<div class="tablewrap"><table>
<tr><th>Sport</th><th>Strength input</th><th>Win probability</th><th>Totals</th><th>Handicap</th></tr>
<tr><td>NHL</td><td>Points percentage shrunk toward .500 by GP/(GP+12), plus goal difference per game × 0.012</td>
<td>0.5 + (rating diff) × 0.80 + 0.035 home term, clamped 0.08–0.92</td>
<td>Goals rates shrunk to 3.05 per team per game with weight 10; normal(σ=1.9) around the expected total, line rounded to the nearest 0.5</td>
<td>Puck line ±1.5 from normal(σ=2.0) on the expected goal difference</td></tr>
<tr><td>NBA</td><td>2025-26 win% shrunk by 0.75 toward .500, blended with 2026-27 record weighted GP/(GP+20)</td>
<td>Log-odds difference plus a 0.24 home term (≈57.5% base home win rate), clamped 0.05–0.95</td>
<td>Not originated — no official pace/efficiency table captured</td>
<td>Spread = inverse-normal(p) × 11.5, rounded to the nearest 0.5</td></tr>
<tr><td>MLB</td><td>Win% shrunk by 162/202 toward .500</td>
<td>Log-odds difference plus a 0.17 home term (≈54%), clamped 0.10–0.90</td>
<td>Runs per game from RS/RA with a 0.12 run home adjustment; normal(σ=4.2)</td>
<td>Run line ±1.5 from normal(σ=4.2)</td></tr>
<tr><td>URC</td><td>Win rate + points difference per game × 0.010, shrunk toward .500 by PL/(PL+6)</td>
<td>0.5 + (rating diff) × 0.90 + 0.05 home term; 5.5% draw, remaining probability split</td>
<td>Match points shrunk toward 47.5 with weight 6; normal(σ=12)</td>
<td>Spread = inverse-normal(p) × 13, rounded to the nearest 0.5</td></tr>
<tr><td>Snooker</td><td>Log of official ranking prize money, scaled by 0.45 into a per-frame win probability (clamped 0.15–0.85)</td>
<td>Exact best-of-seven binomial series probability</td>
<td>Exact distribution over 4–7 frames; expected frames rounded to the nearest 0.5</td>
<td>Frame handicap −1.5 = series won by two frames or more</td></tr>
</table></div>

<h2>3. Pick and confidence</h2>
<p class="small">The pick is the model's match winner (home or away on the money line). Confidence uses the model probability of that
pick: <strong>high ≥ 0.65</strong>, <strong>medium 0.57–0.649</strong>, <strong>low &lt; 0.57</strong>. A pick is only eligible for
"high" when every input for that match is verified; a match with any missing input is not priced at all.</p>

<h2>4. Predictions</h2>
<p class="small">Written predictions exist only for high-confidence picks. Each is at least 30 words, names the selection explicitly,
uses the verified form line and the most recent confirmed result, and lists every factual claim with its official source underneath.</p>

<h2>5. What this model is not</h2>
<ul class="small">
<li>It is not fitted to market prices, so it cannot tell you whether a bookmaker price is value. It only tells you what our own price is.</li>
<li>It does not know about injuries, team news, suspensions, weather or schedule spots. Those are real reasons a human might disagree.</li>
<li>Early-season samples are small. Shrinkage reduces the damage but does not remove it.</li>
<li>Confidence is a probability band, not a guarantee. Short prices lose too.</li>
</ul>
"""
    with open(os.path.join(SITE, "methodology.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Method", body, active="methodology.html"))

    # ---------------- Sources ----------------
    rows = []
    for s in sorted(sources_doc["sources"], key=lambda x: (not x["official"], x["id"])):
        used = sum(1 for m in matches if s["id"] in m.get("fixture_sources", []) + m.get("input_sources", []))
        kind = "Official" if s["official"] else "Listing source (not used as a fact source)"
        rows.append(
            f'<tr><td><strong>{esc(s["id"])}</strong></td><td>{esc(s["publisher"])}</td>'
            f'<td><a href="{esc(s["url"])}" rel="noopener">{esc(s["title"])}</a></td>'
            f'<td class="small">{esc(kind)}</td><td class="num">{used}</td></tr>')
    body = f"""
<h1>Sources</h1>
<p class="lede">Every source used in this build, with the number of match rows it supports. Official sources are what the model reads;
OLBG is used only to reconstruct the listing surface and is never treated as a fact source.</p>
<div class="tablewrap"><table>
<tr><th>ID</th><th>Publisher</th><th>Page</th><th>Type</th><th class="num">Match rows using it</th></tr>
{"".join(rows)}
</table></div>
<p class="small muted">Capture window: {esc(BUILD_TIME)}. Pages change; a link may show a later edition of the same table.</p>
"""
    with open(os.path.join(SITE, "sources.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Sources", body, active="sources.html"))

    print(f"built site: {len([f for f in os.listdir(SITE) if f.endswith(chr(46)+chr(104)+chr(116)+chr(109)+chr(108))])} html pages + assets -> {SITE}")


if __name__ == "__main__":
    build()

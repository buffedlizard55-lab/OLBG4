#!/usr/bin/env python3
"""Board EC static site renderer.

Reads data/session-e0ca04cf/desk.json + predictions.json and writes
session-e0ca04cf/*.html.  Every table cell that carries a fact is either a value
copied from the desk or a link to the official URL recorded on that row; nothing
is filled in here.
"""
from __future__ import annotations

import html
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data" / "session-e0ca04cf"
OUT = ROOT / "session-e0ca04cf"

SPORTS = [
    ("Golf", "golf"),
    ("Volleyball", "volleyball"),
    ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"),
    ("Snooker", "snooker"),
    ("Darts", "darts"),
    ("Baseball", "baseball"),
    ("Gaelic Sports", "gaelic-sports"),
    ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"),
    ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"),
    ("Rugby League", "rugby-league"),
]
SLUG = dict(SPORTS)

CSS = """
:root{
  --bg:#0b1220; --panel:#111a2b; --panel2:#162134; --line:#22304a;
  --ink:#e8eefb; --mute:#9fb0cc; --accent:#3ba3ff; --accent2:#21d4a4;
  --high:#21d4a4; --med:#ffc857; --low:#9fb0cc; --flag:#ff7a7a;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
 font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 18px}
header.top{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.94);
 border-bottom:1px solid var(--line);backdrop-filter:blur(8px)}
header.top .bar{display:flex;gap:14px;align-items:center;justify-content:space-between;
 padding:10px 0;flex-wrap:wrap}
.brand{font-weight:700;letter-spacing:.2px}
.brand span{color:var(--accent)}
nav.main{display:flex;gap:4px;flex-wrap:wrap}
nav.main a{padding:6px 10px;border-radius:8px;color:var(--mute);font-size:14px}
nav.main a:hover{background:var(--panel2);text-decoration:none;color:var(--ink)}
nav.main a.on{background:var(--panel2);color:var(--ink);box-shadow:inset 0 -2px 0 var(--accent)}
main{padding:26px 0 60px}
h1{font-size:28px;line-height:1.25;margin:0 0 6px}
h2{font-size:20px;margin:34px 0 10px}
h3{font-size:16px;margin:22px 0 8px}
p.lede{color:var(--mute);margin:0 0 18px;max-width:70ch}
.sub{color:var(--mute);font-size:14px}
.grid{display:grid;gap:14px}
.cards{grid-template-columns:repeat(auto-fill,minmax(240px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h3{margin:0 0 6px;font-size:15px}
.card .big{font-size:24px;font-weight:700}
.kpi{display:flex;gap:22px;flex-wrap:wrap;margin:16px 0 6px}
.kpi div{background:var(--panel);border:1px solid var(--line);border-radius:12px;
 padding:12px 16px;min-width:132px}
.kpi .n{font-size:22px;font-weight:700}
.kpi .l{font-size:12px;color:var(--mute);text-transform:uppercase;letter-spacing:.06em}
table{width:100%;border-collapse:collapse;background:var(--panel);
 border:1px solid var(--line);border-radius:12px;overflow:hidden;font-size:13.5px}
th,td{padding:9px 10px;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
th{background:var(--panel2);font-size:11.5px;text-transform:uppercase;letter-spacing:.06em;
 color:var(--mute);position:relative;white-space:nowrap}
tr:last-child td{border-bottom:none}
tbody tr:hover{background:#16223a}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;
 font-weight:700;letter-spacing:.04em;text-transform:uppercase}
.pill.High{background:rgba(33,212,164,.16);color:var(--high)}
.pill.Medium{background:rgba(255,200,87,.16);color:var(--med)}
.pill.Low{background:rgba(159,176,204,.16);color:var(--low)}
.pill.none{background:rgba(255,122,122,.14);color:var(--flag)}
.tag{display:inline-block;background:var(--panel2);border:1px solid var(--line);
 border-radius:999px;padding:1px 8px;font-size:11.5px;color:var(--mute)}
.pick{font-weight:700}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.note{border-left:3px solid var(--accent);background:var(--panel);padding:10px 14px;
 border-radius:0 10px 10px 0;margin:14px 0;color:var(--mute)}
.note.warn{border-left-color:var(--flag)}
.note.ok{border-left-color:var(--high)}
.pred{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px;margin:14px 0}
.pred .head{display:flex;gap:10px;align-items:baseline;justify-content:space-between;flex-wrap:wrap}
.pred .match{font-weight:700}
.pred .sel{color:var(--accent2);font-weight:700}
.pred p{margin:8px 0 0}
.pred .meta{color:var(--mute);font-size:12.5px;margin-top:10px}
.pred .meta a{color:var(--accent)}
.scroll{overflow-x:auto;border-radius:12px}
footer{border-top:1px solid var(--line);color:var(--mute);font-size:13px;padding:18px 0 40px}
ul.tight{margin:8px 0 0 18px;padding:0}
ul.tight li{margin:3px 0}
code{background:var(--panel2);padding:1px 5px;border-radius:5px;font-size:12.5px}
@media (max-width:640px){h1{font-size:22px}td,th{padding:7px 8px}}
"""

NAV = [
    ("index.html", "Overview"),
    ("picks.html", "Picks"),
    ("entries.html", "All matches"),
    ("markets.html", "Markets"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
    ("methodology.html", "Methodology"),
    ("olbg.html", "OLBG"),
    ("review.html", "Repo review"),
]


def e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def money(p: float | None) -> str:
    return "—" if p is None else f"{p*100:.1f}%"


def am(v) -> str:
    if v in (None, "", 0):
        return "—"
    return f"+{v}" if v > 0 else f"{v}"


def dec(v) -> str:
    return "—" if v in (None, "", 0) else f"{v:.2f}"


def pill(conf: str) -> str:
    if not conf:
        return '<span class="pill none">no line</span>'
    return f'<span class="pill {e(conf)}">{e(conf)}</span>'


def when(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return e(iso)
    return dt.strftime("%a %d %b %H:%M UTC")


def src(url: str, name: str = "", text: str = "") -> str:
    if not url:
        return '<span class="tag">unverified — no source</span>'
    label = text or name or "official"
    return f'<a href="{e(url)}" rel="noopener" target="_blank">{e(label)}</a>'


def page(title: str, body: str, active: str = "", root: str = "") -> str:
    nav = "".join(
        f'<a class="{"on" if href == active else ""}" href="{root}{href}">{e(label)}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG 15-sport desk</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap bar">
  <div class="brand">OLBG <span>15-sport desk</span></div>
  <nav class="main">{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
  <p>Board EC · session <code>arena/e0ca04cf-olbg4</code> · prices are our own fair lines
  derived from captured official inputs; the OLBG quote shown next to them is what the
  listing displayed when the page was captured. Nothing here is a tip to stake money.</p>
</div></footer>
</body></html>
"""


def load():
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text()) if (DATA / "predictions.json").exists() else {}
    review = json.loads((DATA / "review.json").read_text()) if (DATA / "review.json").exists() else {}
    return desk, preds, review


# --------------------------------------------------------------------- tables
def picks_table(rows, root="", show_sport=True, limit=None) -> str:
    head = ['<div class="scroll"><table><thead><tr>']
    cols = ["When (UTC)", "Sport", "Match", "Pick", "Our price", "OLBG price", "Conf.", "Official source"]
    if not show_sport:
        cols.remove("Sport")
    head.append("".join(f"<th>{e(c)}</th>" for c in cols))
    head.append("</tr></thead><tbody>")
    body = []
    for r in (rows if limit is None else rows[:limit]):
        p = r.get("pick") or {}
        mk = (r.get("markets") or {}).get(p.get("market", ""), {})
        row = []
        row.append(f'<td class="num">{e(when(r.get("start_utc", "")))}</td>')
        if show_sport:
            row.append(f'<td><a href="{root}{e(r.get("sport_slug",""))}.html">{e(r.get("sport"))}</a></td>')
        row.append(f'<td>{e(r.get("side_a"))} <span class="sub">v</span> {e(r.get("side_b") or "")}'
                   f'<div class="sub">{e(r.get("competition",""))}</div></td>')
        row.append(f'<td><span class="pick">{e(p.get("selection",""))}</span>'
                   f'<div class="sub">{e(mk.get("note") or p.get("market","").replace("_"," "))}</div></td>')
        row.append(f'<td class="num">{e(dec(p.get("decimal")))}<div class="sub">{e(am(p.get("american")))} · {e(money(p.get("p")))}</div></td>')
        if p.get("market_decimal"):
            row.append(f'<td class="num">{e(dec(p.get("market_decimal")))}'
                       f'<div class="sub">{e(am(p.get("market_american")))}</div></td>')
        else:
            row.append('<td class="num"><span class="tag">not captured</span></td>')
        row.append(f'<td>{pill(p.get("confidence"))}</td>')
        row.append(f'<td>{src(r.get("source_url"), r.get("source_name"), r.get("source_name") or "source")}'
                   f'<div class="sub">{e(r.get("source_id",""))}</div></td>')
        body.append("<tr>" + "".join(row) + "</tr>")
    if not body:
        body.append(f'<tr><td colspan="{len(cols)}">No priced row in this view — see the flags on '
                    f'<a href="{root}flagged.html">Flagged for review</a>.</td></tr>')
    return "".join(head) + "".join(body) + "</tbody></table></div>"


def markets_table(rows, root="") -> str:
    out = ['<div class="scroll"><table><thead><tr><th>When</th><th>Match</th><th>Market</th>'
           '<th>Line</th><th>Selection</th><th class="num">Our dec</th><th class="num">Our Am.</th>'
           '<th class="num">OLBG dec</th><th>Source</th></tr></thead><tbody>']
    n = 0
    for r in rows:
        o = r.get("olbg") or {}
        quotes = {}
        for q in o.get("listed", []) or []:
            quotes[(q.get("market", "").lower(), q.get("selection", ""))] = q.get("decimal")
        first = True
        for mname, mk in (r.get("markets") or {}).items():
            for s in mk.get("selections", []):
                n += 1
                q = quotes.get((mname.replace("_", " ").lower(), s.get("name", "")))
                out.append(
                    "<tr>"
                    + (f'<td class="num">{e(when(r.get("start_utc","")))}</td>' if first else "<td></td>")
                    + (f'<td>{e(r.get("side_a"))} v {e(r.get("side_b"))}</td>' if first else "<td></td>")
                    + f'<td>{e(mname.replace("_"," "))}</td><td class="num">{e(mk.get("line") if mk.get("line") is not None else "—")}</td>'
                    + f'<td>{e(s.get("name",""))}</td>'
                    + f'<td class="num">{e(dec(s.get("decimal")))}</td>'
                    + f'<td class="num">{e(am(s.get("american")))}</td>'
                    + f'<td class="num">{e(dec(q)) if q else "—"}</td>'
                    + (f'<td>{src(r.get("source_url"), r.get("source_name"), "source")}</td>' if first else "<td></td>")
                    + "</tr>"
                )
                first = False
    if n == 0:
        out.append('<tr><td colspan="9">No originated market in this view.</td></tr>')
    return "".join(out) + "</tbody></table></div>"


def pred_card(r, p, root="") -> str:
    p = p or {}
    sel = p.get("selection") or (r.get("pick") or {}).get("selection", "")
    conf = (r.get("pick") or {}).get("confidence", "")
    price = (r.get("pick") or {}).get("decimal")
    inputs = "".join(f"<li>{e(k)}: {e(v)}</li>" for k, v in (p.get("inputs") or {}).items())
    return f"""<div class="pred">
  <div class="head">
    <div class="match">{e(r.get('side_a'))} v {e(r.get('side_b') or '—')}
      <div class="sub">{e(r.get('competition',''))} · {e(when(r.get('start_utc','')))}</div></div>
    <div>{pill(conf)} <span class="tag">pick at {e(dec(price))}</span></div>
  </div>
  <p><span class="sel">Selection: {e(sel)}</span></p>
  <p>{e(p.get('text',''))}</p>
  <div class="meta">Words: {e(p.get('words',''))} · Official source: {src(r.get('source_url'), r.get('source_name'), r.get('source_name') or 'source')}
  {('<br>OLBG event: <a href="' + e((r.get('olbg') or {}).get('event_url','')) + '" rel="noopener" target="_blank">listed market</a>') if (r.get('olbg') or {}).get('event_url') else ''}
  {('<details><summary>Inputs used</summary><ul class="tight">' + inputs + '</ul></details>') if inputs else ''}
  </div>
</div>"""


# ----------------------------------------------------------------------- pages
def build():
    desk, preds, review = load()
    rows = desk["rows"]
    OUT.mkdir(parents=True, exist_ok=True)
    cap = desk.get("capture", "")
    cutoff = desk.get("cutoff_utc", "")
    window = desk.get("window", {})

    def preds_for(sport=None):
        out = []
        for r in rows:
            p = preds.get(r["id"])
            if not p:
                continue
            if sport and r["sport"] != sport:
                continue
            out.append((r, p))
        return out

    priced = [r for r in rows if r.get("pick")]
    highs = [r for r in priced if r["pick"].get("confidence") == "High"]
    inband = [r for r in priced if r["pick"].get("in_band")]

    def rank(r):
        o = {"High": 0, "Medium": 1, "Low": 2}.get(r["pick"].get("confidence"), 3)
        return (o, -r["pick"].get("p", 0), r.get("start_utc", ""))

    highs.sort(key=rank)
    inband.sort(key=rank)

    # ---------------------------------------------------------------- overview
    per_sport_cards = []
    for sport, slug in SPORTS:
        srows = [r for r in rows if r["sport"] == sport]
        sp = [r for r in srows if r.get("pick")]
        sh = [r for r in sp if r["pick"].get("confidence") == "High"]
        sband = [r for r in sp if r["pick"].get("in_band")]
        npred = len(preds_for(sport))
        status = "priced" if sp else ("listed, no line" if srows else "not captured")
        per_sport_cards.append(f"""<a class="card" href="{slug}.html" style="display:block;color:inherit">
  <h3>{e(sport)}</h3>
  <div class="big">{len(sp)}<span class="sub"> / {len(srows)} priced</span></div>
  <div class="sub">High {len(sh)} · in band {len(sband)} · write-ups {npred}</div>
  <div class="sub" style="margin-top:6px">{e(status)}</div>
</a>""")

    top = "\n".join(pred_card(r, preds.get(r["id"])) for r, _ in preds_for()[:3])
    body = f"""
<h1>Fifteen sports, our own lines, and the reasoning behind each pick</h1>
<p class="lede">A single desk for Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts, Baseball,
Gaelic Sports, Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball and Rugby League.
Every fixture below is tied to the official page it was read from, every price is our own fair line
derived from those official numbers, and the OLBG quote is shown beside it where the listing exposed one.</p>

<div class="kpi">
  <div><div class="n">{len(rows)}</div><div class="l">fixtures captured</div></div>
  <div><div class="n">{len(priced)}</div><div class="l">with our own line</div></div>
  <div><div class="n">{len(highs)}</div><div class="l">High confidence</div></div>
  <div><div class="n">{len(inband)}</div><div class="l">High inside −250…+10,000</div></div>
  <div><div class="n">{len(preds_for())}</div><div class="l">written predictions</div></div>
  <div><div class="n">{len(SPORTS)}</div><div class="l">sports covered</div></div>
</div>
<p class="sub">Snapshot {e(cap)} · desk cutoff {e(cutoff)} · fixture window
{e(window.get('start',''))} → {e(window.get('end',''))}</p>

<h2>Executive summary — highest-confidence picks</h2>
<p class="lede">Ranked by our own probability, then by start time. “In band” means the selection's
price sits inside the −250 to +10,000 window asked for; where the OLBG listing quoted a price for
that exact selection it is shown next to ours, otherwise the band test uses our fair price and the
row says so.</p>
{picks_table(highs[:15], root="")}
<p class="sub"><a href="picks.html">See all {len(priced)} picks →</a></p>

<h2>Written predictions</h2>
<p class="lede">Each one names the fixture, states the selection in plain words, and uses only
numbers captured from the official source linked under it.</p>
{top if top else '<div class="note warn">No written prediction reached publication in this snapshot — see <a href="flagged.html">Flagged for review</a>.</div>'}
<p class="sub"><a href="picks.html">All written predictions →</a></p>

<h2>Sports</h2>
<div class="grid cards">
{''.join(per_sport_cards)}
</div>
"""
    (OUT / "index.html").write_text(page("Overview", body, "index.html"))

    # ------------------------------------------------------------------- picks
    by_conf = {c: [r for r in priced if r["pick"].get("confidence") == c] for c in ("High", "Medium", "Low")}
    pbody = ["<h1>Picks</h1>",
             f'<p class="lede">Every row carries our own price, the OLBG quote where one was captured, '
             f'the confidence label and the official source. {len(priced)} priced rows, '
             f'{len(preds_for())} with a full written prediction.</p>']
    cur = None
    for r, p in sorted(preds_for(), key=lambda t: rank(t[0])):
        if r["sport"] != cur:
            cur = r["sport"]
    pbody.append("<h2>Written predictions</h2>")
    got = False
    for r, p in sorted(preds_for(), key=lambda t: rank(t[0])):
        got = True
        pbody.append(pred_card(r, p))
    if not got:
        pbody.append('<div class="note warn">No written predictions in this snapshot.</div>')
    for c in ("High", "Medium", "Low"):
        pbody.append(f"<h2>{c} confidence — {len(by_conf[c])} picks</h2>")
        pbody.append(picks_table(by_conf[c]))
    (OUT / "picks.html").write_text(page("Picks", "".join(pbody), "picks.html"))

    # ----------------------------------------------------------------- entries
    ebody = ["<h1>All matches</h1>",
             '<p class="lede">One line per selection, for every market we originated. '
             'Rows are grouped by sport; each group links to that sport’s page with the write-ups.</p>']
    for sport, slug in SPORTS:
        srows = [r for r in rows if r["sport"] == sport]
        if not srows:
            continue
        ebody.append(f'<h2 id="{slug}">{e(sport)} — {len(srows)} fixtures</h2>')
        ebody.append(markets_table(srows))
    (OUT / "entries.html").write_text(page("All matches", "".join(ebody), "entries.html"))

    # ----------------------------------------------------------------- markets
    tax = desk.get("olbg_market_taxonomy", {})
    mbody = ["<h1>Markets</h1>",
             '<p class="lede">Two different lists: the markets we originate ourselves for each sport, '
             'and the market names OLBG’s own listings used when the pages were captured.</p>']
    mbody.append("<h2>What we originate</h2><div class=\"scroll\"><table><thead><tr>"
                 "<th>Sport</th><th>Markets we price</th><th class=\"num\">Rows priced</th>"
                 "<th class=\"num\">Selections</th><th>Method</th></tr></thead><tbody>")
    for sport, slug in SPORTS:
        srows = [r for r in rows if r["sport"] == sport and r.get("pick")]
        mset = sorted({m for r in srows for m in (r.get("markets") or {})})
        nsel = sum(len(mk.get("selections", [])) for r in srows for mk in (r.get("markets") or {}).values())
        method = next((r.get("pick", {}).get("basis", "") for r in srows), "")
        mbody.append(f'<tr><td><a href="{slug}.html">{e(sport)}</a></td>'
                     f'<td>{", ".join(e(m.replace("_"," ")) for m in mset) or "<span class=tag>none</span>"}</td>'
                     f'<td class="num">{len(srows)}</td><td class="num">{nsel}</td>'
                     f'<td class="sub">{e(method)}</td></tr>')
    mbody.append("</tbody></table></div>")
    mbody.append("<h2>Market names seen on OLBG</h2><div class=\"scroll\"><table><thead><tr>"
                 "<th>Sport</th><th>Market alias captured verbatim</th><th class=\"num\">Tips</th>"
                 "</tr></thead><tbody>")
    for sport, mks in sorted(tax.items()):
        for m, n in sorted(mks.items(), key=lambda kv: -kv[1]):
            mbody.append(f"<tr><td>{e(sport)}</td><td>{e(m)}</td><td class=\"num\">{n}</td></tr>")
    if not tax:
        mbody.append('<tr><td colspan="3">No OLBG listing parsed in this snapshot.</td></tr>')
    mbody.append("</tbody></table></div>")
    (OUT / "markets.html").write_text(page("Markets", "".join(mbody), "markets.html"))

    # ----------------------------------------------------------------- sources
    man = desk.get("manifest", {})
    sbody = ["<h1>Sources</h1>",
             f'<p class="lede">Capture <code>{e(cap)}</code>. Each response is stored byte-for-byte '
             f'with its SHA-256, so any published number can be traced to the exact bytes it came from.</p>']
    sbody.append(f"""<div class="kpi">
      <div><div class="n">{e(man.get('targets',''))}</div><div class="l">targets</div></div>
      <div><div class="n">{e(man.get('ok',''))}</div><div class="l">responses stored</div></div>
      <div><div class="n">{e(man.get('failed',''))}</div><div class="l">failed (logged)</div></div>
      <div><div class="n">{e(man.get('started_utc',''))}</div><div class="l">capture start (UTC)</div></div>
    </div>""")
    sbody.append("<h2>Every successful response</h2><div class=\"scroll\"><table><thead><tr>"
                 "<th>ID</th><th>Sport</th><th>URL</th><th class=\"num\">Bytes</th><th>SHA-256</th>"
                 "</tr></thead><tbody>")
    for rec in man.get("records", []):
        sbody.append(f"<tr><td class=\"mono\">{e(rec.get('id'))}</td><td>{e(rec.get('sport'))}</td>"
                     f"<td><a href=\"{e(rec.get('url'))}\" rel=\"noopener\" target=\"_blank\">{e(rec.get('url'))}</a></td>"
                     f"<td class=\"num\">{e(rec.get('bytes'))}</td>"
                     f"<td class=\"mono\">{e((rec.get('sha256') or '')[:16])}…</td></tr>")
    sbody.append("</tbody></table></div>")
    fails = man.get("failures", [])
    sbody.append(f"<h2>Failed targets ({len(fails)})</h2>")
    if fails:
        sbody.append("<div class=\"scroll\"><table><thead><tr><th>ID</th><th>URL</th><th>Error</th>"
                     "</tr></thead><tbody>")
        for f in fails:
            sbody.append(f"<tr><td class=\"mono\">{e(f.get('id'))}</td>"
                         f"<td>{e(f.get('url'))}</td><td class=\"sub\">{e(f.get('error'))}</td></tr>")
        sbody.append("</tbody></table></div>")
    else:
        sbody.append('<p class="sub">None.</p>')
    (OUT / "sources.html").write_text(page("Sources", "".join(sbody), "sources.html"))

    # ----------------------------------------------------------------- flagged
    fbody = ["<h1>Flagged for review</h1>",
             '<p class="lede">Everything we could not confirm from an official source, every value we '
             'left blank rather than infer, and every structural irregularity we found while checking '
             'the repository. Nothing on this page blocks publication; it is the list to review.</p>']
    fbody.append("<h2>Rows with a flag</h2>")
    flagged = [r for r in rows if r.get("flags")]
    fbody.append(f'<p class="sub">{len(flagged)} of {len(rows)} rows carry at least one flag.</p>')
    fbody.append("<div class=\"scroll\"><table><thead><tr><th>Sport</th><th>Fixture</th>"
                 "<th>Flag</th><th>Official source</th></tr></thead><tbody>")
    for r in flagged[:400]:
        fbody.append(f"<tr><td>{e(r['sport'])}</td>"
                     f"<td>{e(r.get('side_a'))} {('v ' + e(r.get('side_b'))) if r.get('side_b') else ''}"
                     f"<div class=\"sub\">{e(when(r.get('start_utc','')))}</div></td>"
                     f"<td>{'<br>'.join(e(f) for f in r['flags'])}</td>"
                     f"<td>{src(r.get('source_url'), r.get('source_name'), 'source')}</td></tr>")
    fbody.append("</tbody></table></div>")
    if review:
        fbody.append("<h2>Repository review</h2>")
        fbody.append(f'<p class="lede">{e(review.get("summary",""))}</p>')
        fbody.append("<div class=\"scroll\"><table><thead><tr><th>ID</th><th>Where</th><th>Finding</th>"
                     "<th>Impact</th><th>Status</th></tr></thead><tbody>")
        for f in review.get("findings", []):
            fbody.append(f"<tr><td class=\"mono\">{e(f.get('id'))}</td><td>{e(f.get('where'))}</td>"
                         f"<td>{e(f.get('finding'))}"
                         + (f'<div class="sub"><a href="{e(f.get("source"))}" rel="noopener" target="_blank">{e(f.get("source"))}</a></div>' if f.get("source") else "")
                         + f"</td><td>{e(f.get('impact'))}</td><td>{e(f.get('status'))}</td></tr>")
        fbody.append("</tbody></table></div>")
    (OUT / "flagged.html").write_text(page("Flagged for review", "".join(fbody), "flagged.html"))

    # ------------------------------------------------------------- methodology
    meth = desk.get("methodology", {})
    mbody2 = ["<h1>Methodology</h1>",
              '<p class="lede">How a fixture becomes a price, and where the method stops.</p>']
    mbody2.append(f"<div class=\"note\"><b>Read this first.</b> {e(meth.get('headline',''))}</div>")
    for k, v in (meth.get("sections") or {}).items():
        mbody2.append(f"<h2>{e(k)}</h2><p>{e(v)}</p>")
    mbody2.append("<h2>Constants used</h2><div class=\"scroll\"><table><thead><tr><th>Key</th>"
                  "<th>Value</th><th>Why</th></tr></thead><tbody>")
    for k, (val, why) in (meth.get("constants") or {}).items():
        mbody2.append(f"<tr><td class=\"mono\">{e(k)}</td><td class=\"mono\">{e(val)}</td>"
                      f"<td class=\"sub\">{e(why)}</td></tr>")
    mbody2.append("</tbody></table></div>")
    (OUT / "methodology.html").write_text(page("Methodology", "".join(mbody2), "methodology.html"))

    # -------------------------------------------------------------------- OLBG
    ol = desk.get("olbg_notes", {})
    obody = ["<h1>OLBG</h1>",
             '<p class="lede">What the site actually exposes, and what we used from it.</p>']
    obody.append(f"<div class=\"note\">{e(ol.get('summary',''))}</div>")
    obody.append("<h2>URL and markup patterns observed</h2><div class=\"scroll\"><table><thead><tr>"
                 "<th>Pattern</th><th>What it gives us</th></tr></thead><tbody>")
    for k, v in (ol.get("patterns") or {}).items():
        obody.append(f"<tr><td class=\"mono\">{e(k)}</td><td>{e(v)}</td></tr>")
    obody.append("</tbody></table></div>")
    ev = ol.get("events") or []
    obody.append(f"<h2>Events listed on OLBG in this capture ({len(ev)})</h2>")
    obody.append("<div class=\"scroll\"><table><thead><tr><th>Sport</th><th>Event as listed</th>"
                 "<th>Start (UTC)</th><th class=\"num\">Tips</th><th>Event page</th></tr></thead><tbody>")
    for x in ev[:300]:
        obody.append(f"<tr><td>{e(x.get('sport'))}</td><td>{e(x.get('event'))}</td>"
                     f"<td class=\"num\">{e(when(x.get('start_utc','')))}</td>"
                     f"<td class=\"num\">{e(x.get('tips'))}</td>"
                     f"<td><a href=\"{e(x.get('url'))}\" rel=\"noopener\" target=\"_blank\">event</a></td></tr>")
    obody.append("</tbody></table></div>")
    (OUT / "olbg.html").write_text(page("OLBG", "".join(obody), "olbg.html"))

    # ------------------------------------------------------------------- review
    rbody = ["<h1>Repository review</h1>",
             f'<p class="lede">{e(review.get("summary",""))}</p>']
    for section, items in (review.get("sections") or {}).items():
        rbody.append(f"<h2>{e(section)}</h2>")
        rbody.append("<div class=\"scroll\"><table><thead><tr><th>Item</th><th>What we found</th>"
                     "<th>Source</th><th>Status</th></tr></thead><tbody>")
        for it in items:
            rbody.append(f"<tr><td>{e(it.get('item'))}</td><td>{e(it.get('finding'))}</td>"
                         f"<td>{src(it.get('source'), '', 'source') if it.get('source') else '<span class=tag>none</span>'}</td>"
                         f"<td>{e(it.get('status'))}</td></tr>")
        rbody.append("</tbody></table></div>")
    (OUT / "review.html").write_text(page("Repository review", "".join(rbody), "review.html"))

    # ------------------------------------------------------------------- sports
    for sport, slug in SPORTS:
        srows = sorted([r for r in rows if r["sport"] == sport],
                       key=lambda r: (r.get("start_utc", ""), r.get("side_a", "")))
        sp = [r for r in srows if r.get("pick")]
        sh = [r for r in sp if r["pick"].get("confidence") == "High"]
        sb = [r for r in sp if r["pick"].get("in_band")]
        npred = preds_for(sport)
        sbody = [f"<h1>{e(sport)}</h1>"]
        note = (desk.get("sport_notes") or {}).get(sport, "")
        sbody.append(f'<p class="lede">{e(note)}</p>')
        sbody.append(f"""<div class="kpi">
          <div><div class="n">{len(srows)}</div><div class="l">fixtures</div></div>
          <div><div class="n">{len(sp)}</div><div class="l">priced</div></div>
          <div><div class="n">{len(sh)}</div><div class="l">High</div></div>
          <div><div class="n">{len(sb)}</div><div class="l">in −250…+10,000</div></div>
          <div><div class="n">{len(npred)}</div><div class="l">written predictions</div></div>
        </div>""")
        sbody.append("<h2>Picks for this sport</h2>")
        sbody.append(picks_table(sp, root="", show_sport=False))
        sbody.append("<h2>Written predictions</h2>")
        if npred:
            sbody.extend(pred_card(r, p) for r, p in npred)
        else:
            sbody.append('<div class="note warn">No written prediction for this sport in this snapshot. '
                         'The reason is recorded on <a href="flagged.html">Flagged for review</a>.</div>')
        sbody.append("<h2>Every market we originated</h2>")
        sbody.append(markets_table(srows))
        zero = [r for r in srows if not r.get("pick")]
        if zero:
            sbody.append(f"<h2>Fixtures without a line ({len(zero)})</h2>")
            sbody.append("<div class=\"scroll\"><table><thead><tr><th>When</th><th>Fixture</th>"
                         "<th>Competition</th><th>Why no line</th><th>Official source</th></tr></thead><tbody>")
            for r in zero:
                sbody.append(f'<tr><td class="num">{e(when(r.get("start_utc","")))}</td>'
                             f'<td>{e(r.get("side_a"))} {("v " + e(r.get("side_b"))) if r.get("side_b") else ""}</td>'
                             f'<td class="sub">{e(r.get("competition",""))}</td>'
                             f'<td class="sub">{e("; ".join(r.get("flags") or ["no verified inputs"]))}</td>'
                             f'<td>{src(r.get("source_url"), r.get("source_name"), "source")}</td></tr>')
            sbody.append("</tbody></table></div>")
        (OUT / f"{slug}.html").write_text(page(sport, "".join(sbody)))

    print(f"site rebuilt: {len(list(OUT.glob('*.html')))} pages")


if __name__ == "__main__":
    build()

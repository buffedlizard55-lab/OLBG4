#!/usr/bin/env python3
"""Board Y (session c4fda15e) - static sub-site generator -> session-c4fda15e/*.html

Reads data/session-c4fda15e/{desk.json, writeups.json, official.json, official_manual.json,
olbg_inventory.json} and the capture manifests. Deterministic: same inputs -> same bytes.
"""
from __future__ import annotations

import html
import json
import os
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-c4fda15e")
OUT = os.path.join(ROOT, "session-c4fda15e")
os.makedirs(OUT, exist_ok=True)

desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
WR = json.load(open(os.path.join(DATA, "writeups.json"), encoding="utf-8"))["writeups"]
OFF = json.load(open(os.path.join(DATA, "official.json"), encoding="utf-8"))
MAN = json.load(open(os.path.join(DATA, "official_manual.json"), encoding="utf-8"))["blocks"]
ROWS = desk["rows"]
EXTRA = desk["official_only"]
E = lambda s: html.escape("" if s is None else str(s))  # noqa: E731

SPORT_PAGES = [("Tennis", "tennis"), ("Darts", "darts"), ("Basketball", "basketball"), ("Rugby Union", "rugby-union"),
               ("Baseball", "baseball"), ("Ice Hockey", "ice-hockey"), ("Cricket", "cricket"), ("Snooker", "snooker"),
               ("Handball", "handball"), ("Volleyball", "volleyball"), ("Gaelic Football", "gaelic-football")]
NAV = [("index.html", "Dashboard"), ("high.html", "High picks"), ("picks.html", "All lines & markets"), ("olbg.html", "OLBG reconciliation"),
       ("flagged.html", "Flagged for Review"), ("sources.html", "Sources"), ("methodology.html", "Methodology")]

CSS = """
:root{--ink:#17202a;--mut:#5d6d7e;--line:#d5dbe1;--bg:#f7f9fb;--card:#fff;--acc:#1f5f8b;--hi:#0b7a3b;--med:#9a6b00;--lo:#7b8a97;--bad:#b03a2e}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#13324a;color:#fff;padding:14px 20px}header a{color:#fff}header .t{font-weight:700;font-size:18px}
nav{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:6px;font-size:14px}nav a{color:#cfe3f3;text-decoration:none}nav a:hover{text-decoration:underline}
main{max-width:1240px;margin:0 auto;padding:18px 20px 40px}h1{font-size:24px;margin:6px 0 4px}h2{font-size:19px;margin:26px 0 8px}
.sub{color:var(--mut);margin:0 0 14px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}.card .n{font-size:26px;font-weight:700}.card .l{color:var(--mut);font-size:13px}
table{border-collapse:collapse;width:100%;background:var(--card);border:1px solid var(--line);font-size:13.5px}
th,td{border-bottom:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:#eef2f6;position:sticky;top:0}
tr:hover td{background:#fbfcfd}.tag{display:inline-block;padding:1px 7px;border-radius:10px;font-size:12px;font-weight:600;color:#fff}
.High{background:var(--hi)}.Medium{background:var(--med)}.Low{background:var(--lo)}.unv{background:var(--bad)}.ok{background:#2e7d4f}.part{background:#8e6c00}
.flag{color:var(--bad);font-size:12.5px}.mut{color:var(--mut);font-size:12.5px}.wu{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--hi);border-radius:6px;padding:12px 14px;margin:12px 0}
.wu h3{margin:0 0 4px;font-size:16px}.wu p{margin:6px 0}.wu ul{margin:6px 0 0 18px;padding:0;font-size:13px}input[type=search]{padding:6px 9px;width:min(420px,100%);border:1px solid var(--line);border-radius:6px;margin:6px 0 10px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:12px}code{background:#eef2f6;padding:0 4px;border-radius:3px}
footer{color:var(--mut);font-size:12.5px;max-width:1240px;margin:0 auto;padding:0 20px 30px}
"""
JS = """document.querySelectorAll('input[data-filter]').forEach(function(inp){var t=document.getElementById(inp.dataset.filter);
inp.addEventListener('input',function(){var q=inp.value.toLowerCase();t.querySelectorAll('tbody tr').forEach(function(r){r.style.display=r.textContent.toLowerCase().indexOf(q)>-1?'':'none';});});});"""


def am(x):
    if x is None:
        return ""
    return f"{x:+d}" if isinstance(x, int) else str(x)


def pct(p):
    return "" if p is None else f"{100 * p:.1f}%"


def page(fn, title, body, sub=""):
    nav = " ".join(f'<a href="{h}">{E(t)}</a>' for h, t in NAV)
    sp = " ".join(f'<a href="{s}.html">{E(n)}</a>' for n, s in SPORT_PAGES)
    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · OLBG4 Board Y</title><link rel="stylesheet" href="style.css"></head><body>
<header><div class="t"><a href="index.html" style="text-decoration:none">OLBG4 · Board Y — OLBG live listing, reconciled</a></div>
<nav>{nav}</nav><nav style="margin-top:2px">{sp}</nav></header>
<main><p class="mut"><a href="../index.html">← OLBG4 home</a></p><h1>{E(title)}</h1>{f'<p class="sub">{sub}</p>' if sub else ''}
{body}</main>
<footer>OLBG listing captured {E(desk['olbg_capture_utc'])} UTC (runner capture, SHA-256 in manifest) · lines frozen {E(desk['built_utc'])} ·
Session <code>arena/c4fda15e-olbg4</code>. OLBG tip counts, percentages and comments are not reproduced; prices are this board's fair lines unless labelled
“market (OLBG)”. Unconfirmed values are left blank and flagged.</footer><script src="app.js"></script></body></html>
"""
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write(doc)


def vtag(v):
    cls = {"verified": "ok", "partially verified": "part", "verified (official only)": "ok"}.get(v, "unv")
    return f'<span class="tag {cls}">{E(v)}</span>'


def ctag(c):
    return f'<span class="tag {E(c)}">{E(c)}</span>' if c else '<span class="mut">no line</span>'


def off_link(r):
    o = r.get("official")
    if not o:
        return '<span class="flag">blank — unverified</span>'
    return f'<a href="{E(o["url"])}">{E(o["source_name"])}</a>'


def olbg_link(r):
    return f'<a href="{E(r["olbg_url"])}">OLBG #{E(r["event_id"])}</a>' if r.get("olbg_url") else '<span class="mut">not on OLBG</span>'


def when(r):
    o = r.get("official") or {}
    if o.get("utc"):
        return E(o["utc"].replace("T", " ").replace(":00Z", "Z"))
    if o:
        return f'<span class="mut">{E(o.get("date") or "")} {E(o.get("utc_basis") or "")}</span>'
    return ""


def markets_cell(r):
    L = r.get("line")
    if not L:
        return ""
    mk = L.get("markets", {})
    bits = []
    if "spread_home" in mk:
        bits.append(f'{E(L.get("home"))} {mk["spread_home"]:+} ({pct(mk.get("p_home_cover"))} to cover)')
    if mk.get("total_line") is not None:
        bits.append(f'Total {mk["total_line"]}: over {pct(mk.get("p_over"))}')
    if "run_line_home_-1.5" in mk:
        bits.append(f'{E(L.get("home"))} -1.5 runs: {pct(mk["run_line_home_-1.5"])}')
    if "puck_line" in mk:
        k = list(mk["puck_line"].items())[0]
        bits.append(f'{E(L.get("home"))} {k[0].split()[-1]}: {pct(k[1])}')
    if "totals" in mk:
        bits.append("Goals " + ", ".join(f'{k}: {pct(v)}' for k, v in mk["totals"].items() if "5.5" in k))
    if "first_set_a" in mk:
        bits.append(f'1st set {E((r.get("official") or {}).get("a"))}: {pct(mk["first_set_a"])}')
        cs = list(mk["set_betting"].items())[:2]
        bits.append("Sets " + ", ".join(f"{k} {pct(v)}" for k, v in cs))
    if "leg_handicap" in mk:
        h = mk["leg_handicap"]
        bits.append(f'A -1.5 legs: {pct(h.get("A -1.5"))}')
        bits.append("Legs " + ", ".join(f"{k}: {pct(v)}" for k, v in mk["total_legs"].items()))
    if "reg_3way" in mk:
        a, d, b = mk["reg_3way"]
        bits.append(f"Regulation 1X2 {pct(a)}/{pct(d)}/{pct(b)}")
    if L.get("p_draw"):
        bits.append(f'Draw {pct(L["p_draw"])}')
    return "<br>".join(bits)


def row_table(rows, tid, sport_col=True):
    head = ("<th>Sport</th>" if sport_col else "") + "<th>Event</th><th>Competition (official)</th><th>Start (official, UTC)</th><th>Verification</th><th>Our pick</th><th>Fair price</th><th>Confidence</th><th>Market (OLBG)</th><th>Other markets (fair %)</th><th>Sources</th><th>Flags</th>"
    out = [f'<input type="search" placeholder="Filter rows…" data-filter="{tid}"><table id="{tid}"><thead><tr>{head}</tr></thead><tbody>']
    for r in rows:
        pk = r.get("pick") or {}
        o = r.get("official") or {}
        mk = "" if pk.get("market_reference") is None else am(pk["market_reference"])
        mnote = E(pk.get("market_note") or "")
        flags = "<br>".join(f'<span class="flag">{E(x)}</span>' for x in r.get("flags", []))
        started = '<span class="mut">started before lines were frozen</span>' if r.get("started_before_desk") else ""
        out.append("<tr>" + (f"<td>{E(r['sport'])}</td>" if sport_col else "") +
                   f"<td>{E(r['event_name'])}</td><td>{E(o.get('competition'))}</td><td>{when(r)}</td><td>{vtag(r['verification'])}</td>"
                   f"<td>{E(pk.get('selection'))}{started}</td><td>{am(pk.get('fair_american'))}<br><span class='mut'>{pct(pk.get('p'))}</span></td>"
                   f"<td>{ctag(pk.get('confidence'))}<br><span class='mut'>{E(pk.get('confidence_reason'))}</span></td>"
                   f"<td>{mk}<br><span class='mut'>{mnote}</span></td><td>{markets_cell(r)}</td><td>{olbg_link(r)}<br>{off_link(r)}</td><td>{flags}</td></tr>")
    out.append("</tbody></table>")
    return "".join(out)


# ------------------------------------------------------------------ assets
open(os.path.join(OUT, "style.css"), "w").write(CSS.strip() + "\n")
open(os.path.join(OUT, "app.js"), "w").write(JS.strip() + "\n")

# ------------------------------------------------------------------ dashboard
ver = Counter(r["verification"] for r in ROWS)
conf = Counter((r.get("pick") or {}).get("confidence") for r in ROWS if r.get("pick"))
highs = [r for r in ROWS if (r.get("pick") or {}).get("confidence") == "High"]
by_sport = defaultdict(list)
for r in ROWS:
    by_sport[r["sport"]].append(r)
cards = [("OLBG rows captured", len(ROWS) + len(desk["outrights"])), ("Match rows", len(ROWS)), ("Outright rows", len(desk["outrights"])),
         ("Verified vs official", ver.get("verified", 0)), ("Partially verified", ver.get("partially verified", 0)), ("Unverified (flagged)", ver.get("unverified", 0)),
         ("Lines originated", sum(1 for r in ROWS if r.get("pick")) + sum(1 for r in EXTRA if r.get("pick"))), ("High picks (−250…+10000)", len(highs))]
cards_html = '<div class="cards">' + "".join(f'<div class="card"><div class="n">{n}</div><div class="l">{E(l)}</div></div>' for l, n in cards) + "</div>"
sport_rows = []
for name, slug in SPORT_PAGES:
    rs = by_sport.get(name, [])
    if not rs:
        continue
    c = Counter(r["verification"] for r in rs)
    sport_rows.append(f'<tr><td><a href="{slug}.html">{E(name)}</a></td><td>{len(rs)}</td><td>{c.get("verified", 0)}</td><td>{c.get("partially verified", 0)}</td>'
                      f'<td>{c.get("unverified", 0)}</td><td>{sum(1 for r in rs if r.get("pick"))}</td><td>{sum(1 for r in rs if (r.get("pick") or {}).get("confidence") == "High")}</td></tr>')
hub_rows = "".join(f'<tr><td>{E(h["sport"])}</td><td><a href="{E(h["hub_url"])}">{E(h["hub_url"].replace("https://www.olbg.com", ""))}</a></td><td>{h["embedded_match_rows"]}</td><td>{h["embedded_outright_rows"]}</td>'
                   f'<td class="mut">{E(h["sha256"][:16])}…</td><td class="mut">{E(h.get("scope_note"))}</td></tr>' for h in desk["hubs"])
hi_rows = "".join(f'<tr><td>{E(r["sport"])}</td><td><a href="high.html#e{E(r["event_id"])}">{E(r["event_name"])}</a></td><td>{E(r["pick"]["selection"])}</td><td>{am(r["pick"]["fair_american"])}</td>'
                  f'<td>{am(r["pick"]["market_reference"])}</td><td>{when(r)}</td></tr>' for r in highs)
body = f"""{cards_html}
<div class="grid2"><div><h2>High-confidence picks</h2><table><thead><tr><th>Sport</th><th>Event</th><th>Pick</th><th>Fair</th><th>Market (OLBG)</th><th>Start (UTC)</th></tr></thead><tbody>{hi_rows}</tbody></table>
<p class="mut">High = model probability ≥ 60%, fair price inside −250…+10000, the market price OLBG showed for the same selection also inside the window, a fully verified fixture,
no model–market or recent-form contradiction. Write-ups: <a href="high.html">High picks</a>.</p></div>
<div><h2>Coverage by sport</h2><table><thead><tr><th>Sport</th><th>OLBG rows</th><th>Verified</th><th>Partial</th><th>Unverified</th><th>Lines</th><th>High</th></tr></thead><tbody>{''.join(sport_rows)}</tbody></table>
<p class="mut">Excluded per brief and not captured: soccer/football, American football, boxing/UFC/MMA, hurling, horse racing, cycling, specials. Aussie Rules, eSports and Greyhounds hubs listed no events at capture.</p></div></div>
<h2>What this board did</h2>
<ol><li><b>Reverse-engineered OLBG’s listing.</b> Each OLBG sport hub is a SvelteKit page that embeds its listing (<code>tips:[…]</code>, <code>tournaments:[…]</code>) with a machine timestamp per event; the server builds it from <code>/sports/&lt;Sport&gt;/top_tips?paginate=1-100&amp;include_expired=1</code>. That API and OLBG’s <code>/api/svelte</code> “Load More” endpoint sit under robots-disallowed paths, so they were <b>not</b> called — the inventory uses only the 18 public hub pages. Every hub returned fewer than 100 rows, so the embedded arrays hold the full listing the hubs render. OLBG lists only events that already carry tips. <a href="methodology.html">Details</a>.</li>
<li><b>Reconciled every OLBG match row</b> against an official page or feed (ATP/ProTennisLive, WTA, PDC, NBA.com, EuroLeague, LNR, URC, MLB, Liiga). <a href="olbg.html">Row-by-row table</a>.</li>
<li><b>Originated our own lines</b> from official numeric inputs only (rankings, Order of Merit, standings, points/runs/goals for and against), with handicap/total markets where the inputs support them. <a href="picks.html">All lines</a>.</li>
<li><b>Flagged</b> everything unconfirmed, mismatched or irregular. <a href="flagged.html">Flagged for Review</a>.</li></ol>
<h2>OLBG hubs captured</h2><table><thead><tr><th>Sport</th><th>Hub</th><th>Match rows</th><th>Outright rows</th><th>SHA-256</th><th>Scope note</th></tr></thead><tbody>{hub_rows}</tbody></table>
"""
page("index.html", "Dashboard", body, "OLBG’s live listing for every in-scope sport, checked against official sources, with our own lines and confidence labels.")

# ------------------------------------------------------------------ high picks
parts = []
for r in highs:
    w = WR.get(str(r["event_id"]))
    pk = r["pick"]
    facts = "".join(f'<li>{E(t)} — <a href="{E(u)}">{E(u.split("/")[2])}</a></li>' for t, u in (w or {}).get("facts", []))
    parts.append(f"""<div class="wu" id="e{E(r['event_id'])}"><h3>{E(r['event_name'])} — <span class="tag High">High</span> {E(pk['selection'])}</h3>
<p class="mut">{E((r.get('official') or {}).get('competition'))} · {when(r)} · fair {am(pk['fair_american'])} ({pct(pk['p'])}) · market shown on OLBG {am(pk['market_reference'])} · window check: fair {'inside' if pk['in_window_fair'] else 'outside'}, market {'inside' if pk['in_window_market'] else ('n/a' if pk['in_window_market'] is None else 'outside')}</p>
<p>{E((w or {}).get('text') or 'Write-up missing')}</p><ul>{facts}</ul><p class="mut">{olbg_link(r)} · {off_link(r)}</p></div>""")
near = [r for r in ROWS + EXTRA if (r.get("pick") or {}).get("confidence") == "Medium" and "capped" in (r["pick"].get("confidence_reason") or "")]
near_rows = "".join(f'<tr><td>{E(r["event_name"])}</td><td>{E(r["pick"]["selection"])}</td><td>{am(r["pick"]["fair_american"])}</td><td>{E(r["pick"]["confidence_reason"])}</td></tr>' for r in near)
outw = [r for r in ROWS if (r.get("pick") or {}).get("confidence") == "Medium" and "outside window" in (r["pick"].get("confidence_reason") or "")]
outw_rows = "".join(f'<tr><td>{E(r["event_name"])}</td><td>{E(r["pick"]["selection"])}</td><td>{am(r["pick"]["fair_american"])}</td><td>{am(r["pick"]["market_reference"])}</td><td>{E(r["pick"]["confidence_reason"])}</td></tr>' for r in outw)
body = "".join(parts) + f"""<h2>Strong models kept out of High (capped)</h2><p class="mut">These passed the 60% model bar but failed a market, form or verification check.</p>
<table><thead><tr><th>Event</th><th>Model pick</th><th>Fair</th><th>Why not High</th></tr></thead><tbody>{near_rows}</tbody></table>
<h2>Favourites outside the −250 window</h2><p class="mut">The brief says High picks must not just be heavy favourites, so selections priced shorter than −250 (fair or market) are capped at Medium.</p>
<table><thead><tr><th>Event</th><th>Pick</th><th>Fair</th><th>Market (OLBG)</th><th>Reason</th></tr></thead><tbody>{outw_rows}</tbody></table>"""
page("high.html", "High-confidence picks", body, f"{len(highs)} selections inside −250…+10000, each written by hand from facts read on official pages (linked under each write-up).")

# ------------------------------------------------------------------ all picks
lined = [r for r in ROWS if r.get("pick")]
body = f"""<p>Every line below is a <b>fair</b> price (no bookmaker margin) originated from official inputs; the model per sport is on the <a href="methodology.html">methodology</a> page.
“Other markets” lists our derived handicap, total, set or leg probabilities.</p>{row_table(lined, 't_all')}
<h2>Official fixtures in the same rounds that OLBG did not list</h2><p class="mut">OLBG lists only events that already carry tips; these come from the same official feeds and get lines too (capped at Medium: no market reference).</p>
{row_table(EXTRA, 't_extra')}
<h2>Markets OLBG shows, by sport</h2><table><thead><tr><th>Sport</th><th>Market labels seen on OLBG listing rows</th><th>Markets this board originated</th></tr></thead><tbody>"""
lab = defaultdict(Counter)
for r in ROWS:
    lab[r["sport"]][r["market_label"] or "(unlabelled handicap)"] += 1
ours = {"Tennis": "match winner, 1st-set winner, set betting (2-0/2-1), set handicap, total sets", "Darts": "match winner, leg handicap ±1.5/2.5/3.5, total legs 8.5/9.5 (best-of-11 assumed)",
        "Basketball": "moneyline, spread; total (EuroLeague only)", "Rugby Union": "three-way result, handicap, match total (Pro D2/Top 14)",
        "Baseball": "moneyline, run line −1.5, total runs", "Ice Hockey": "two-way moneyline, regulation 1X2, puck line, goal totals (Liiga)"}
for sp, c in sorted(lab.items()):
    body += f"<tr><td>{E(sp)}</td><td>{E(', '.join(f'{k} ({v})' for k, v in c.most_common()))}</td><td>{E(ours.get(sp, 'none — official numeric inputs not captured'))}</td></tr>"
body += "</tbody></table>"
page("picks.html", "All lines & markets", body, f"{len(lined)} OLBG rows with an originated line plus {len(EXTRA)} official-only fixtures.")

# ------------------------------------------------------------------ OLBG reconciliation
def olbg_row(r):
    o = r.get("official") or {}
    return (f"<tr><td>{E(r['sport'])}</td><td>{olbg_link(r)}</td><td>{E(r['event_name'])}</td><td>{E(r.get('olbg_competition_path') or r.get('olbg_menu_league') or '')}</td>"
            f"<td>{E((r.get('start_utc') or '').replace('T', ' ').replace(':00Z', 'Z'))}</td><td>{E(r.get('market_label'))}</td><td>{vtag(r['verification'])}</td>"
            f"<td>{E(o.get('competition'))}</td><td>{when(r)}</td><td>{off_link(r)}</td><td>{'<br>'.join('<span class=flag>' + E(x) + '</span>' for x in r.get('flags', []))}</td></tr>")
outr = "".join(f"<tr><td>{E(x['sport'])}</td><td><a href='{E(x['olbg_url'])}'>OLBG #{E(x['event_id'])}</a></td><td>{E(x['event_name'])}</td><td>{E(x['market_label'])}</td>"
               f"<td>{E((x['start_utc'] or '')[:10])}</td><td class='mut'>outright — no match line originated</td></tr>" for x in desk["outrights"])
body = f"""<p>One row per OLBG listing row (structure only). “Start (OLBG)” is OLBG’s own machine timestamp; the official columns come from the linked official page or feed.
Status <b>verified</b> = participants and date match an official schedule (times compared to the minute where the official schedule prints one).</p>
<input type="search" placeholder="Filter rows…" data-filter="t_olbg"><table id="t_olbg"><thead><tr><th>Sport</th><th>OLBG</th><th>Event (OLBG label)</th><th>OLBG competition path</th><th>Start (OLBG, UTC)</th><th>OLBG market</th><th>Status</th><th>Official competition</th><th>Official start (UTC)</th><th>Official source</th><th>Flags</th></tr></thead><tbody>
{''.join(olbg_row(r) for r in ROWS)}</tbody></table>
<h2>Outright rows on OLBG ({len(desk['outrights'])})</h2><table><thead><tr><th>Sport</th><th>OLBG</th><th>Event</th><th>Market</th><th>Settles</th><th>Note</th></tr></thead><tbody>{outr}</tbody></table>"""
page("olbg.html", "OLBG reconciliation", body, f"{len(ROWS)} match rows and {len(desk['outrights'])} outright rows captured from 18 public OLBG hub pages at {desk['olbg_capture_utc']} UTC.")

# ------------------------------------------------------------------ sport pages
for name, slug in SPORT_PAGES:
    rs = by_sport.get(name, [])
    ex = [r for r in EXTRA if r["sport"] == name]
    c = Counter(r["verification"] for r in rs)
    body = f"""<div class="cards"><div class="card"><div class="n">{len(rs)}</div><div class="l">OLBG match rows</div></div><div class="card"><div class="n">{c.get('verified', 0)}</div><div class="l">verified</div></div>
<div class="card"><div class="n">{c.get('unverified', 0)}</div><div class="l">unverified (flagged)</div></div><div class="card"><div class="n">{sum(1 for r in rs if r.get('pick'))}</div><div class="l">lines</div></div></div>
{row_table(rs, 't_s', sport_col=False) if rs else '<p>No OLBG rows at capture.</p>'}
{('<h2>Official-only fixtures</h2>' + row_table(ex, 't_x', sport_col=False)) if ex else ''}"""
    page(f"{slug}.html", name, body, "OLBG rows for this sport with official verification, our line and confidence.")

# ------------------------------------------------------------------ flagged
fl = [r for r in ROWS if r.get("flags")]
irreg = [
    ("OLBG time convention", "NBA rows on OLBG are timestamped 10 minutes after the official NBA.com tip-off (e.g. Cavaliers–76ers 23:10Z vs 7:00 PM ET = 23:00Z).", "https://www.nba.com/schedule?date=2026-10-22"),
    ("Venue", "Rockets at Spurs (23 Oct) is staged at the Moody Center, Austin TX according to NBA.com, not at the Spurs' usual arena.", "https://www.nba.com/game/hou-vs-sas-0022600009"),
    ("Venue", "Maccabi Rapyd Tel Aviv v Real Madrid (EuroLeague R7) is played at Aleksandar Nikolic Hall per the official EuroLeague API.", "https://api-live.euroleague.net/v2/competitions/E/seasons/E2026/games"),
    ("Schedule", "Leinster v Munster (24 Oct) is listed by OLBG but is not in the official URC 'Fixtures in Full' excerpt for that date; left unverified.", "https://www.unitedrugby.com/latest/news/2026-27-fixtures-in-full/"),
    ("Data definition", "The PDC participants feed carries a 'prizeMoney' field that is not the two-year Order of Merit (James Wade £5.51m > Luke Littler £4.87m while ranked 6th v 1st); this board uses only the official ranking field.", "https://participants.darts.web.gc.pdcservices.co.uk/v2/?page.size=100"),
    ("Scope", "Gaelic Football is listed by OLBG separately from Football; the brief excludes 'football'. Rows are included and flagged for the owner's decision.", "https://www.olbg.com/betting-tips/Gaelic_Football/25"),
    ("DST", "France leaves CEST on 25 Oct 2026: La Rochelle v Bordeaux-Bègles (21h05 local) is 20:05Z, which OLBG has right.", "https://top14.lnr.fr/calendrier-et-resultats"),
    ("OLBG access", "OLBG’s 'Load More Tips' endpoint (/api/svelte) and listing API (/sports/…/top_tips) are robots-disallowed; not used. Hub arrays never reached the API page size of 100.", "https://www.olbg.com/robots.txt"),
    ("Coordination", "Board letters U, V and W were each claimed by two sessions on 22 Oct; this session renamed V→W→Y (see COORDINATION.md).", "https://github.com/buffedlizard55-lab/OLBG4/blob/main/COORDINATION.md"),
]
irr_rows = "".join(f'<tr><td>{E(a)}</td><td>{E(b)}</td><td><a href="{E(c)}">{E(c.split("/")[2])}</a></td></tr>' for a, b, c in irreg)
body = f"""<p>Nothing here blocked publication. Each item links to the official page (or the OLBG page) needed for a manual check.</p>
<h2>Irregularities</h2><table><thead><tr><th>Type</th><th>Finding</th><th>Check</th></tr></thead><tbody>{irr_rows}</tbody></table>
<h2>Flagged rows ({len(fl)})</h2>{row_table(fl, 't_fl')}"""
page("flagged.html", "Flagged for Review", body, "Unverified, partially verified or mismatched rows, and irregularities found while reconciling OLBG with official sources.")

# ------------------------------------------------------------------ sources
caps = []
for stamp in sorted(os.listdir(os.path.join(DATA, "capture"))):
    mp = os.path.join(DATA, "capture", stamp, "manifest.json")
    if os.path.exists(mp):
        for it in json.load(open(mp, encoding="utf-8"))["items"]:
            caps.append((stamp, it))
cap_rows = "".join(f'<tr><td class="mut">{E(s)}</td><td>{E(it["id"])}</td><td><a href="{E(it["url"])}">{E(it["url"][:90])}</a></td><td>{E(it.get("status"))}</td>'
                   f'<td class="mut">{E((it.get("sha256") or "")[:16])}</td><td class="mut">{E(it.get("error") or "")}</td></tr>' for s, it in caps)
man_rows = "".join(f'<tr><td>{E(b["source_name"])}</td><td><a href="{E(b["url"])}">{E(b["url"][:95])}</a></td><td class="mut">{E(b.get("read_utc") or b.get("capture") or "")}</td></tr>' for b in MAN)
body = f"""<h2>Official pages read with the page reader</h2><p class="mut">Transcriptions are stored in <code>data/session-c4fda15e/official_manual.json</code>.</p>
<table><thead><tr><th>Source</th><th>URL</th><th>Read / capture</th></tr></thead><tbody>{man_rows}</tbody></table>
<h2>Runner captures (exact bytes in git, SHA-256)</h2><p class="mut">Fetched by <code>.github/workflows/w-c4fda15e.yml</code> and stored gzip-compressed under <code>data/session-c4fda15e/capture/&lt;stamp&gt;/</code>. Non-200 rows show what could not be fetched.</p>
<input type="search" placeholder="Filter…" data-filter="t_cap"><table id="t_cap"><thead><tr><th>Capture</th><th>ID</th><th>URL</th><th>HTTP</th><th>SHA-256 (16)</th><th>Error</th></tr></thead><tbody>{cap_rows}</tbody></table>"""
page("sources.html", "Sources", body, "Every official source behind the tables, with capture hashes.")

# ------------------------------------------------------------------ methodology
body = """<h2>1 · OLBG reverse engineering</h2><ul>
<li>Hub URLs: <code>https://www.olbg.com/betting-tips/&lt;Sport&gt;/&lt;sport_id&gt;</code>; event URLs: <code>/betting-tips/&lt;Sport&gt;/&lt;Region&gt;/&lt;Competition&gt;/&lt;Event_Slug&gt;/&lt;sport_id&gt;?event_id=N</code>. A hub URL without the numeric id returns 404.</li>
<li>Each hub is a SvelteKit page. The hydration script holds <code>tips:[…]</code> (match rows) and <code>tournaments:[…]</code> (outrights) with <code>event_start_unix_timestamp</code>, <code>eventUrl</code>, <code>event_name_alias</code>, <code>market_alias</code>, the featured selection and its price (<code>odds</code>, <code>american_odds</code>), and <code>expired</code>. This board keeps those fields and drops tip counts, percentages, star ratings and comments.</li>
<li>The data source is <code>tipsApiUrl: /sports/&lt;Sport&gt;/top_tips?paginate=1-100&amp;include_recommendations=1&amp;include_expired=1</code>; “Load More Tips” uses <code>PUBLIC_API_URL=https://www.olbg.com/api/svelte</code>. Both are under paths OLBG’s robots.txt disallows for all agents (<code>/sports/</code>, <code>/api/</code>), so neither was called.</li>
<li>Displayed times depend on the reader’s timezone (the page reader saw US Eastern); the embedded Unix timestamp removes that ambiguity, and every time on this site is UTC.</li>
<li>OLBG lists only events that already have tips; <code>include_expired=1</code> means in-play/finished events stay listed (marked <i>started</i> here, no line).</li></ul>
<h2>2 · Verification</h2><ul><li>Each OLBG row is matched to an official schedule by participant names (surnames for tennis/darts, canonical club names for team sports) and compared on date and time.</li>
<li><b>verified</b>: an official page or feed prints the same participants on the same date (and the same minute where a fixed time is printed); <b>partially verified</b>: participants confirmed by an official draw/feed, but the official schedule for that match was not yet published; <b>unverified</b>: no official schedule was captured for that competition in this run — official columns left blank.</li>
<li>Times OLBG shows for “followed by” or session-based schedules (tennis order of play, PDC sessions) are flagged as estimates rather than errors.</li></ul>
<h2>3 · Lines (fair prices, no margin)</h2><ul>
<li><b>Tennis</b>: P(A) = ptsA^0.9 / (ptsA^0.9 + ptsB^0.9) on official ATP (ProTennisLive PDF) and WTA (api.wtatennis.com) rankings of 19 Oct 2026. Set markets come from an i.i.d. best-of-three set model solved to the match probability. Players ranked outside the top 200 cap the row at Low.</li>
<li><b>Darts</b>: P(A) = rB^0.5 / (rA^0.5 + rB^0.5) on the official PDC Order of Merit position; leg markets from a race-to-6 model (best-of-11 assumed — format not printed on the captured PDC page).</li>
<li><b>NBA</b>: 2025-26 official win%, regressed 35% toward .500, log5 plus a home edge of 0.28 log-odds (halved for the Austin game); spread from a normal margin model (sd 12).</li>
<li><b>EuroLeague</b>: per-game net points, 2026-27 blended with the 2025-26 regular season (current weight = gp/(gp+8)), home +3.0, margin sd 11.5, total sd 15.</li>
<li><b>Pro D2 / Top 14</b>: points difference per game from the official LNR tables, home +7, margin sd 13, total sd 14, draw = margin within half a point.</li>
<li><b>MLB</b>: Pythagorean win% (exponent 1.83) from official runs scored/allowed, log5 plus 54% home field; run line and total from normal models.</li>
<li><b>Liiga</b>: independent Poisson on official goals for/against per game (home ×1.07, away ×0.95).</li>
<li>No line where official numeric inputs were not captured (cricket, snooker, handball, volleyball, Gaelic football, SHL, URC, KBL, NBB): blank and flagged, never estimated.</li></ul>
<h2>4 · Confidence</h2><ul><li><b>High</b>: model ≥ 60%; fair price inside −250…+10000 (no shorter than −250 = 71.4%); fully verified fixture; complete official inputs; if OLBG shows a moneyline for our selection, it must be inside the window; if OLBG shows only the opponent, it must not favour the opponent (model–market disagreement) and must not be +250 or longer; with no moneyline shown at all, the fair price must be no shorter than −200; where official recent results exist, the opponent must not have the better recent form. Each High pick gets a hand-written write-up of at least 30 words citing official facts.</li>
<li><b>Medium</b>: model ≥ 56% with complete inputs but not High — including favourites outside the window (the brief’s “just >70% favourites” case).</li><li><b>Low</b>: close contests or partial/unreliable inputs.</li></ul>
<h2>5 · Reproduce</h2><p><code>python3 scripts/session-c4fda15e/parse_olbg.py data/session-c4fda15e/capture/20261022T030401Z data/session-c4fda15e/olbg_inventory.json</code> → <code>official.py</code> → <code>build.py</code> → <code>site.py</code> → <code>verify.py</code>.</p>"""
page("methodology.html", "Methodology", body, "How the listing was captured, verified, priced and graded.")
print("pages:", len([f for f in os.listdir(OUT) if f.endswith(".html")]))

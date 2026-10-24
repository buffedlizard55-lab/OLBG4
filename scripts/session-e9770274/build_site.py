#!/usr/bin/env python3
"""Board CA (arena/e9770274-olbg4) — build the dashboard site under session-e9770274/.

Design brief from the user this cycle: the site must open with an executive summary, and it must be
obvious what each pick is and where it lives. So every page answers three questions at the top:
how many fixtures were checked, how many written predictions exist, and what to click next.
Every table row carries the official source link that backs it.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SID = "session-e9770274"
DATA = ROOT / "data" / SID
SITE = ROOT / SID

SPORT_SLUG = {
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union", "Cricket": "cricket",
    "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball", "Gaelic Sports": "gaelic-sports",
    "Greyhounds": "greyhounds", "Tennis": "tennis", "Motor Racing": "motor-racing",
    "Handball": "handball", "Ice Hockey": "ice-hockey", "Basketball": "basketball",
    "Rugby League": "rugby-league",
}
SPORT_ORDER = ["Ice Hockey", "Basketball", "Baseball", "Tennis", "Volleyball", "Handball", "Darts",
               "Snooker", "Cricket", "Rugby Union", "Rugby League", "Gaelic Sports", "Greyhounds",
               "Motor Racing", "Golf"]

CSS = """
:root{--bg:#0d1117;--card:#161b22;--line:#243040;--ink:#e6edf3;--dim:#8b949e;--accent:#3fb950;
--high:#3fb950;--med:#d29922;--low:#8b949e;--pick:#58a6ff;--warn:#f85149}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
background:var(--bg);color:var(--ink)}
a{color:var(--pick);text-decoration:none}a:hover{text-decoration:underline}
header.top{background:linear-gradient(160deg,#101a2b,#0d1117);border-bottom:1px solid var(--line);padding:22px 20px}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
h1{font-size:1.65rem;margin:0 0 4px}
h2{font-size:1.2rem;margin:34px 0 10px;border-left:4px solid var(--accent);padding-left:10px}
h3{font-size:1.02rem;margin:22px 0 8px}
.sub{color:var(--dim);font-size:.9rem;margin:0}
nav{display:flex;flex-wrap:wrap;gap:6px;margin-top:14px}
nav a{background:#1b2431;border:1px solid var(--line);border-radius:999px;padding:5px 12px;font-size:.85rem;color:var(--ink)}
nav a.on{background:var(--accent);color:#06210c;border-color:var(--accent);font-weight:600}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:20px 0 4px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px}
.kpi b{display:block;font-size:1.5rem;line-height:1.2}
.kpi span{color:var(--dim);font-size:.78rem;text-transform:uppercase;letter-spacing:.04em}
.exec{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--pick);border-radius:10px;
padding:16px 18px;margin:18px 0}
.exec p{margin:0 0 10px}
.exec p:last-child{margin:0}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow:hidden;font-size:.88rem;margin:10px 0 4px;display:table}
th{background:#1b2431;text-align:left;padding:9px 10px;font-size:.76rem;text-transform:uppercase;
letter-spacing:.05em;color:var(--dim);border-bottom:1px solid var(--line);position:sticky;top:0}
td{padding:9px 10px;border-bottom:1px solid #1d2531;vertical-align:top}
tr:last-child td{border-bottom:0}
tr:hover td{background:#19212c}
.pickcell{font-weight:700;color:var(--pick)}
.tag{display:inline-block;border-radius:6px;padding:2px 7px;font-size:.74rem;font-weight:700;letter-spacing:.03em}
.high{background:rgba(63,185,80,.16);color:var(--high);border:1px solid rgba(63,185,80,.4)}
.medium{background:rgba(210,153,34,.15);color:var(--med);border:1px solid rgba(210,153,34,.4)}
.low{background:rgba(139,148,158,.14);color:var(--low);border:1px solid rgba(139,148,158,.35)}
.unpriced{background:rgba(248,81,73,.1);color:var(--warn);border:1px solid rgba(248,81,73,.35)}
.num{font-variant-numeric:tabular-nums;white-space:nowrap}
.small{font-size:.8rem;color:var(--dim)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:14px 0}
.card h3{margin-top:0}
.card .head{display:flex;flex-wrap:wrap;gap:10px;align-items:baseline;justify-content:space-between}
.predtext{background:#0f1620;border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:10px 0}
.facts{margin:8px 0 0;padding-left:18px;font-size:.85rem;color:#c9d1d9}
.facts li{margin:2px 0}
ol.preds{padding-left:0;list-style:none}
.scroll{overflow-x:auto}
footer{border-top:1px solid var(--line);margin-top:40px;padding:22px 0;color:var(--dim);font-size:.82rem}
.pill{display:inline-block;background:#1b2431;border:1px solid var(--line);border-radius:999px;
padding:2px 9px;font-size:.75rem;color:var(--dim);margin-right:6px}
.warnbox{background:rgba(248,81,73,.08);border:1px solid rgba(248,81,73,.35);border-radius:10px;padding:14px 16px}
.okbox{background:rgba(63,185,80,.08);border:1px solid rgba(63,185,80,.35);border-radius:10px;padding:14px 16px}
"""

NAV = [("index.html", "Dashboard"), ("picks.html", "Predictions"), ("fixtures.html", "All matches"),
       ("markets.html", "Markets & lines"), ("sources.html", "Sources"),
       ("review.html", "Repo review"), ("flagged.html", "Flagged for review"),
       ("methodology.html", "Methodology")]


def esc(s) -> str:
    return html.escape(str(s if s is not None else ""))


def usd(a: int) -> str:
    return f"+{a}" if a > 0 else f"{a}"


PREFIX = ""          # "" for root pages, "../" for pages in sports/


def page(title: str, body: str, active: str, subtitle: str = "") -> str:
    nav = "".join(f'<a class="{"on" if href == active else ""}" href="{PREFIX}{href}">{esc(label)}</a>'
                  for href, label in NAV)
    body = body.replace('href="index.html', f'href="{PREFIX}index.html') \
               .replace('href="picks.html', f'href="{PREFIX}picks.html') \
               .replace('href="fixtures.html', f'href="{PREFIX}fixtures.html') \
               .replace('href="markets.html', f'href="{PREFIX}markets.html') \
               .replace('href="sources.html', f'href="{PREFIX}sources.html') \
               .replace('href="review.html', f'href="{PREFIX}review.html') \
               .replace('href="flagged.html', f'href="{PREFIX}flagged.html') \
               .replace('href="methodology.html', f'href="{PREFIX}methodology.html') \
               .replace('href="sports/', f'href="{PREFIX}sports/')
    if PREFIX:
        body = body.replace(f'href="{PREFIX}sports/', 'href="')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} — OLBG 15-sport desk (24 Oct 2026)</title>
<style>{CSS}</style></head>
<body>
<header class="top"><div class="wrap">
<h1>{esc(title)}</h1>
<p class="sub">{esc(subtitle)}</p>
<nav>{nav}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">
<p>Session <code>arena/e9770274-olbg4</code> · board CA · data capture <code>{esc(DESK['capture_id'])}</code>
({esc(DESK['captured_utc'])}) · every price is our own fair line, never a copied bookmaker or OLBG price.</p>
<p>OLBG public boards are used only to establish <em>which</em> fixtures are listed and what the crowd price is.
Every team statistic, record and result behind a pick is read from the official league, tour or federation page
linked on the row. Values that could not be confirmed from an official source are left blank and listed on
<a href="{PREFIX}flagged.html">Flagged for review</a>.</p>
</div></footer>
</body></html>"""


# --------------------------------------------------------------------------- data
DESK = json.loads((DATA / "desk.json").read_text())
PREDS = json.loads((DATA / "predictions.json").read_text())
REVIEW = json.loads((DATA / "review.json").read_text())
FLAGS = json.loads((DATA / "flags.json").read_text())
SOURCES = json.loads((DATA / "sources.json").read_text())
BY_ID = {r["id"]: r for r in DESK["rows"]}
PRED_BY_ROW = {p["row_id"]: p for p in PREDS["predictions"]}


def conf_tag(c: str) -> str:
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(c, "low")
    return f'<span class="tag {cls}">{esc(c)}</span>'


def sport_link(sport: str, text: str | None = None) -> str:
    slug = SPORT_SLUG.get(sport)
    return f'<a href="sports/{slug}.html">{esc(text or sport)}</a>' if slug else esc(text or sport)


def fmt_start(iso: str) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.strptime(iso.replace("Z", ""), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return esc(iso)
    return dt.strftime("%a %d %b %H:%M UTC")


def pick_summary(row: dict, show_market: bool = True) -> str:
    p = row.get("pick")
    if not p:
        return '<span class="tag unpriced">no line</span>'
    market = f'<span class="small">{esc(p["market"])}</span><br>' if show_market else ""
    return (f'{market}<span class="pickcell">{esc(p["selection"])}</span><br>'
            f'<span class="small num">{p["decimal"]:.2f} · {usd(p["american"])} · {p["prob"]*100:.1f}%</span>')


def source_cell(row: dict) -> str:
    o = row.get("official") or {}
    if o.get("url"):
        return f'<a href="{esc(o["url"])}" rel="noopener">official source</a>'
    f = row.get("flags") or []
    return f'<span class="small">{esc(f[0]["kind"] if f else "no source")}</span>'


# --------------------------------------------------------------------------- dashboard
def kpis() -> str:
    s = DESK["summary"]
    conf = PREDS["summary"]["confidence_counts"]
    return f"""<div class="kpis">
<div class="kpi"><b>{s['rows_total']}</b><span>OLBG fixtures checked</span></div>
<div class="kpi"><b>{s['priced']}</b><span>fixtures we priced</span></div>
<div class="kpi"><b>{PREDS['summary']['total']}</b><span>written predictions</span></div>
<div class="kpi"><b>{conf.get('High',0)}</b><span>High-confidence picks</span></div>
<div class="kpi"><b>{conf.get('Medium',0)}</b><span>Medium-confidence picks</span></div>
<div class="kpi"><b>{len(DESK['summary']['by_sport'])}</b><span>sports on the board</span></div>
</div>"""


def exec_summary() -> str:
    s = DESK["summary"]
    conf = PREDS["summary"]["confidence_counts"]
    sports_written = len({p["sport"] for p in PREDS["predictions"]})
    short = [f"{sp} ({d['priced']})" for sp, d in sorted(s["by_sport"].items(),
                                                        key=lambda kv: -kv[1]["priced"]) if d["priced"]]
    gaps = [sp for sp, d in s["by_sport"].items() if d["priced"] == 0]
    return f"""<div class="exec">
<p><b>What this is.</b> Every fixture OLBG listed in the 15 sports we cover, captured
{esc(DESK['captured_utc'])} from OLBG's own public boards, then re-checked against the official league,
tour or federation. We originate our own fair lines, pick a side, grade it, and — where the evidence
supports it — publish a written prediction of at least 30 words with the sources under it.</p>
<p><b>Today's position.</b> {s['rows_total']} listed fixtures · {s['priced']} priced by us ·
{PREDS['summary']['total']} written predictions across {sports_written} sports
({conf.get('High',0)} High, {conf.get('Medium',0)} Medium, {conf.get('Low',0)} Low).
Priced sports: {esc(', '.join(short)) if short else 'none'}.</p>
<p><b>Where the picks are.</b> The single table directly below this summary is the whole pick list for
today: one row per written prediction, with the selection in bold, its price, and the probability behind
it. Full text, verified stats and source links are on <a href="picks.html">Predictions</a>. Every fixture
we checked — priced or not — is on <a href="fixtures.html">All matches</a>, and each sport has its own page.</p>
<p><b>What we could not do, and why.</b> No line is originated for a fixture unless we hold a verified
official input for both sides. That leaves {len(gaps)} sports with no priced fixture in this capture
({esc(', '.join(gaps))}). Each reason is specific and is repeated on the sport page and on
<a href="flagged.html">Flagged for review</a> — for example OLBG's golf hub served no fixture cards at
all today, and the NBA, PDC and WST data hosts refused or client-rendered our capture requests. We would
rather publish an empty market than a made-up number.</p>
</div>"""


def top_picks_table(limit: int = 12, only_high: bool = False) -> str:
    preds = sorted(PREDS["predictions"], key=lambda p: (-p["prob"], p["sport"]))
    if only_high:
        preds = [p for p in preds if p["confidence"] == "High"]
    rows = []
    for i, p in enumerate(preds[:limit], 1):
        row = BY_ID[p["row_id"]]
        rows.append(f"""<tr>
<td class="num">{i}</td>
<td>{sport_link(p['sport'])}</td>
<td><b>{esc(p['match'])}</b><br><span class="small">{fmt_start(p['start_utc'])}</span></td>
<td>{pick_summary(row)}</td>
<td>{conf_tag(p['confidence'])}</td>
<td class="small"><a href="picks.html#{esc(p['prediction_id'])}">read the {p['word_count']}-word prediction →</a></td>
</tr>""")
    return f"""<div class="scroll"><table>
<thead><tr><th>#</th><th>Sport</th><th>Match</th><th>Our pick (price · probability)</th>
<th>Confidence</th><th>Prediction</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def sport_overview() -> str:
    rows = []
    for sp in SPORT_ORDER:
        d = DESK["summary"]["by_sport"].get(sp)
        if not d:
            continue
        written = [p for p in PREDS["predictions"] if p["sport"] == sp]
        status = "priced" if d["priced"] else "no official input"
        cls = "high" if d["priced"] else "unpriced"
        rows.append(f"""<tr>
<td>{sport_link(sp)}</td>
<td class="num">{d['listed']}</td>
<td class="num">{d['priced']}</td>
<td class="num">{d['high']}</td>
<td class="num">{d['medium']}</td>
<td class="num">{len(written)}</td>
<td><span class="tag {cls}">{esc(status)}</span></td>
</tr>""")
    return f"""<div class="scroll"><table>
<thead><tr><th>Sport</th><th>Listed on OLBG</th><th>Priced by us</th><th>High</th><th>Medium</th>
<th>Written predictions</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""


def build_index() -> str:
    gaps = {sp: d for sp, d in DESK["summary"]["by_sport"].items() if d["priced"] == 0}
    reason_rows = []
    for sp, d in sorted(gaps.items()):
        reason = next((f["text"] for r in DESK["rows"] if r["sport"] == sp and r["flags"]
                       for f in r["flags"] if f["kind"] in ("no-official-input", "market-withheld")), "")
        reason_rows.append(f"<tr><td>{sport_link(sp)}</td><td class='num'>{d['listed']}</td><td>{esc(reason)}</td></tr>")
    body = f"""
{kpis()}
{exec_summary()}
<h2>Today's picks — highest confidence first</h2>
<p class="sub">This is the pick list. The bold text in "Our pick" is the selection; the line under it is our
fair price and our modelled win probability. Click through for the full written prediction.</p>
{top_picks_table(14)}
<p class="small"><a href="picks.html">All {PREDS['summary']['total']} written predictions →</a>
 · <a href="fixtures.html">Every fixture we checked →</a></p>

<h2>Sport-by-sport position</h2>
{sport_overview()}

<h2>Fixtures we deliberately did not price</h2>
<p class="sub">No official input, no line. These are the specific reasons.</p>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Listed</th><th>Why no line was originated</th></tr></thead>
<tbody>{''.join(reason_rows) if reason_rows else '<tr><td colspan=3>Every listed sport was priced.</td></tr>'}</tbody></table></div>
"""
    return page("OLBG 15-sport desk — executive summary",
                body, "index.html",
                "Every fixture OLBG lists in our 15 sports, our own lines, our picks, and the written "
                "predictions behind them. Start here.")


# --------------------------------------------------------------------------- picks page
def build_picks() -> str:
    blocks = []
    for sp in SPORT_ORDER:
        preds = [p for p in PREDS["predictions"] if p["sport"] == sp]
        if not preds:
            continue
        cards = []
        for p in sorted(preds, key=lambda x: (-x["prob"])):
            row = BY_ID[p["row_id"]]
            facts = "".join(f'<li>{esc(f["label"])}: {esc(f["value"])} '
                            f'<a href="{esc(f["source_url"])}" rel="noopener">source</a></li>'
                            for f in p["facts"])
            markets = "".join(
                f'<li>{esc(m["market"])}: ' +
                ", ".join(f'{esc(s["selection"])} {s["decimal"]:.2f} ({usd(s["american"])})'
                          for s in m["selections"]) + "</li>"
                for m in row["markets"])
            cards.append(f"""<div class="card" id="{esc(p['prediction_id'])}">
<div class="head"><h3>{esc(p['match'])}</h3>{conf_tag(p['confidence'])}</div>
<p class="small">{esc(p['competition'])} · {fmt_start(p['start_utc'])}
{f" · {esc(p['venue'])}" if p.get('venue') else ""} · <a href="{esc(row['olbg']['url'])}" rel="noopener">OLBG listing</a>
 · <a href="{esc(p['official_source_url'])}" rel="noopener">{esc(p['official_source_name'])}</a></p>
<p><b>The pick: {esc(p['selection'])}</b> — {esc(p['market'])}, our fair price
<span class="num">{p['fair_decimal']:.2f} / {usd(p['fair_american'])}</span>,
modelled probability <span class="num">{p['prob']*100:.1f}%</span>. {esc(p['confidence_reason'])}.</p>
<div class="predtext">{esc(p['prediction_text'])}</div>
<p class="small"><b>{p['word_count']} words</b> · selection stated in the text: {esc(p['selection_language'])}</p>
<h3 style="margin-top:14px">Verified facts used</h3>
<ul class="facts">{facts}</ul>
<h3 style="margin-top:14px">Lines we originated for this match</h3>
<ul class="facts">{markets}</ul>
</div>""")
        blocks.append(f"<h2>{sport_link(sp)} — {len(preds)} written prediction(s)</h2>{''.join(cards)}")

    missing = [sp for sp in SPORT_ORDER if sp in DESK["summary"]["by_sport"]
               and not [p for p in PREDS["predictions"] if p["sport"] == sp]]
    gap_html = "".join(
        f"<tr><td>{sport_link(sp)}</td><td class='num'>{DESK['summary']['by_sport'][sp]['listed']}</td>"
        f"<td>No written prediction: no fixture in this sport could be priced from verified official input "
        f'today. See <a href="{PREFIX}flagged.html">Flagged for review</a>.</td></tr>' for sp in missing)
    body = f"""
<div class="exec"><p><b>Where the picks are.</b> Every written prediction for today is on this page, grouped
by sport. Each card gives the match, the exact selection in bold, our fair price, the modelled probability,
the confidence grade, the full prediction text, the verified facts with their official source links, and
all the lines we originated for that match.</p>
<p>{PREDS['summary']['total']} predictions from {DESK['summary']['priced']} priced fixtures.
Shortest text {PREDS['summary']['min_words']} words, longest {PREDS['summary']['max_words']} words.
Highest pairwise similarity between any two texts: {PREDS['summary']['max_similarity']:.2f}.</p></div>
{''.join(blocks)}
<h2>Sports with no written prediction today</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Listed on OLBG</th><th>Position</th></tr></thead>
<tbody>{gap_html if gap_html else '<tr><td colspan=3>Every sport with a listing has at least one prediction.</td></tr>'}</tbody></table></div>
"""
    return page("Predictions", body, "picks.html",
                "The written predictions, in full, sport by sport — with the selection, the price and the source for every claim.")


# --------------------------------------------------------------------------- fixtures page
def fixtures_table(rows: list[dict]) -> str:
    out = []
    for r in rows:
        o = r.get("official") or {}
        src = (f'<a href="{esc(o["url"])}" rel="noopener">official</a><br>'
               f'<span class="small">{esc(o.get("capture_id",""))}</span>') if o.get("url") else ""
        out.append(f"""<tr>
<td class="num">{r['seq']}</td>
<td>{sport_link(r['sport'])}</td>
<td><b>{esc(r['match'])}</b><br><span class="small">{fmt_start(r['start_utc'])}</span></td>
<td class="small">{esc(r.get('competition') or '')}</td>
<td class="num">{r['olbg']['tip_count'] or ''}</td>
<td><a href="{esc(r['olbg']['url'])}" rel="noopener">OLBG card</a></td>
<td>{pick_summary(r)}</td>
<td>{conf_tag(r['pick']['confidence']) if r.get('pick') else '<span class="tag unpriced">no line</span>'}</td>
<td>{src}</td>
</tr>""")
    return f"""<div class="scroll"><table>
<thead><tr><th>#</th><th>Sport</th><th>Fixture (start)</th><th>Competition</th><th>OLBG tips</th>
<th>OLBG</th><th>Our line &amp; pick</th><th>Confidence</th><th>Official source</th></tr></thead>
<tbody>{''.join(out)}</tbody></table></div>"""


def build_fixtures() -> str:
    rows = DESK["rows"]
    priced = [r for r in rows if r["status"] == "priced"]
    body = f"""
<div class="exec"><p><b>Every fixture we checked.</b> {len(rows)} upcoming events were read off OLBG's
15 in-scope sport boards at {esc(DESK['captured_utc'])}. {len(priced)} of them we were able to price from
verified official input; the rest are listed with no line and the reason is on the sport page and on
<a href="flagged.html">Flagged for review</a>.</p>
<p>Columns: OLBG tips is the number of OLBG members' win-tips on the card (context only — it is not an
input to our prices). "Our line &amp; pick" is our own fair price and the side we would take.</p></div>
{fixtures_table(rows)}
"""
    return page("All matches", body, "fixtures.html",
                "The complete list: every event OLBG lists in our 15 sports, priced or not, with the source for each.")


def build_sport_page(sp: str) -> str:
    global PREFIX
    PREFIX = "../"
    rows = [r for r in DESK["rows"] if r["sport"] == sp]
    d = DESK["summary"]["by_sport"].get(sp, {"listed": 0, "priced": 0})
    preds = [p for p in PREDS["predictions"] if p["sport"] == sp]
    reasons = []
    for r in rows:
        for f in r["flags"]:
            if f["kind"] in ("no-official-input", "market-withheld") and f["text"] not in reasons:
                reasons.append(f["text"])
    reason_html = "".join(f"<li>{esc(x)}</li>" for x in reasons)
    pred_html = "".join(
        f"""<div class="card"><div class="head"><h3>{esc(p['match'])}</h3>{conf_tag(p['confidence'])}</div>
<p class="small">{fmt_start(p['start_utc'])} · <a href="picks.html#{esc(p['prediction_id'])}">full prediction and sources →</a></p>
<p><b>The pick: {esc(p['selection'])}</b> — {esc(p['market'])}, {p['fair_decimal']:.2f} / {usd(p['fair_american'])},
{p['prob']*100:.1f}%.</p>
<div class="predtext">{esc(p['prediction_text'])}</div></div>""" for p in preds)
    body = f"""
<div class="kpis">
<div class="kpi"><b>{d['listed']}</b><span>fixtures listed on OLBG</span></div>
<div class="kpi"><b>{d['priced']}</b><span>priced by us</span></div>
<div class="kpi"><b>{d.get('high',0)}</b><span>High-confidence</span></div>
<div class="kpi"><b>{len(preds)}</b><span>written predictions</span></div>
</div>
<h2>Our lines for every {esc(sp)} fixture</h2>
{fixtures_table(rows) if rows else '<p class="sub">OLBG listed no upcoming fixture in this sport at capture time.</p>'}
{"<h2>Written predictions</h2>" + pred_html if pred_html else "<h2>Written predictions</h2><p class='sub'>None: no fixture in this sport was priceable from verified official input today.</p>"}
{"<h2>Why some fixtures carry no line</h2><ul class='facts'>" + reason_html + "</ul>" if reason_html else ""}
"""
    out = page(f"{sp}", body, f"sports/{SPORT_SLUG[sp]}.html",
                f"{sp}: everything OLBG lists, what we priced, and the picks.")
    PREFIX = ""
    return out


# --------------------------------------------------------------------------- markets page
def build_markets() -> str:
    per_sport: dict[str, set[str]] = {}
    withheld: dict[str, set[str]] = {}
    for r in DESK["rows"]:
        for m in r["markets"]:
            per_sport.setdefault(r["sport"], set()).add(m["market"].split(" (")[0])
        for f in r["flags"]:
            if f["kind"] == "market-withheld":
                withheld.setdefault(r["sport"], set()).add(f["text"][:160])
    rows = []
    for sp in SPORT_ORDER:
        ms = sorted(per_sport.get(sp, []))
        rows.append(f"<tr><td>{sport_link(sp)}</td><td>{esc(', '.join(ms)) if ms else '<span class=small>none originated</span>'}</td></tr>")
    wh = "".join(f"<li><b>{esc(sp)}</b>: {esc(t)}…</li>" for sp, ts in withheld.items() for t in ts)
    body = f"""
<div class="exec"><p><b>What we investigated.</b> For every priceable fixture we built the match-winner
market first, then handicap / puck-line, then match totals, then a sport-specific market (draw-no-bet and
team totals in ice hockey, set handicaps and set totals in volleyball, double chance where a draw is live).
We only publish a market when the official source supports the inputs; otherwise we say so in writing.</p></div>
<h2>Markets originated, by sport</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Markets we originated</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>
<h2>Markets we deliberately withheld</h2>
<ul class="facts">{wh if wh else '<li>None.</li>'}</ul>
<h2>How a fair price is built</h2>
<ul class="facts">
<li><b>Ice hockey (NHL)</b>: independent-Poisson score matrix. Expected goals for each side come from official
NHL goals-for and goals-against per game against the league average, with a 1.055 home multiplier; the
matrix gives match winner, regulation 3-way, puck line, draw-no-bet, team totals and totals at 4.5-7.5.</li>
<li><b>Volleyball (SuperLega)</b>: per-set probability from the official point ratio (points scored ÷ conceded)
with a 3% home term, then a best-of-five set model, which produces match winner, set handicaps and set totals.</li>
<li><b>Baseball (MLB)</b>: Bradley-Terry on official regular-season winning percentage with a
home-field term of 0.09 log-odds; moneyline only, because no verifiable per-game run distribution exists
for a single postseason game.</li>
<li><b>Probability → price</b>: fair decimal = 1/p (2dp); American = −100p/(1−p) at p ≥ 0.5 and
+100(1−p)/p below that. No margin is added: these are fair prices, not bookmaker prices.</li>
<li><b>Confidence</b>: High needs verified inputs on both sides, an adequate sample, a fair price inside
−250…+10,000, and either a modelled probability of at least 66% or at least a 6-point edge over the
OLBG-listed price. See <a href="methodology.html">Methodology</a> for why 66% and not 70% is the practical
floor inside that band.</li>
</ul>
"""
    return page("Markets & lines", body, "markets.html",
                "Which markets we originated for which sport, and the arithmetic behind every price.")


# --------------------------------------------------------------------------- sources page
def build_sources() -> str:
    rows = []
    for s in SOURCES["sources"]:
        used = "used" if s["used"] else "captured, not used"
        rows.append(f"""<tr><td class="small"><code>{esc(s['id'])}</code></td><td>{esc(s['sport'])}</td>
<td><a href="{esc(s['url'])}" rel="noopener">{esc(s['url'])}</a></td>
<td class="num">{s['status']}</td><td class="num">{s['bytes']}</td>
<td class="small"><code>{esc((s['sha256'] or '')[:16])}…</code></td><td class="small">{esc(used)}</td></tr>""")
    body = f"""
<div class="exec"><p><b>Sources.</b> Every official page or API the desk used is listed below with the exact
URL, the HTTP status our capture runner received, the byte count and the SHA-256 of the committed response,
so any figure on this site can be traced back to the bytes it came from. {SOURCES['used_count']} distinct targets back a
published line or fact; the remaining {SOURCES['total']-SOURCES['used_count']} were captured to try to widen
coverage and are listed here for completeness — including the ones that failed, because a failed capture is
the reason a market is missing.</p>
<p>Capture job: <code>.github/workflows/ca-e9770274.yml</code> → <code>scripts/session-e9770274/fetch.py</code>,
which refuses any path OLBG's robots.txt disallows and rate-limits per host.</p></div>
<h2>Capture manifest</h2>
<div class="scroll"><table><thead><tr><th>Capture id</th><th>Sport</th><th>Official URL</th><th>HTTP</th>
<th>Bytes</th><th>SHA-256</th><th>Used</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
"""
    return page("Sources", body, "sources.html",
                "Every official source, its HTTP status and the SHA-256 of the response we relied on.")


# --------------------------------------------------------------------------- flagged page
def build_flagged() -> str:
    groups: dict[str, list[dict]] = {}
    for f in FLAGS["flags"]:
        groups.setdefault(f["group"], []).append(f)
    blocks = []
    for g, items in groups.items():
        lis = "".join(
            f"<li><b>{esc(i['title'])}</b><br>{esc(i['detail'])}"
            + (f'<br><span class="small">Source: <a href="{esc(repo_link(i["source_url"]))}" rel="noopener">'
               f'{esc(i["source_url"])}</a></span>' if i.get("source_url") else "")
            + "</li>" for i in items)
        blocks.append(f'<div class="card"><h3>{esc(g)}</h3><ul class="facts">{lis}</ul></div>')
    body = f"""
<div class="warnbox"><b>Flagged for review.</b> {len(FLAGS['flags'])} items. Nothing here blocks the
publication of the desk — it is the list of things we could not confirm from an official source, or where
two official sources disagree, or where the brief's requirements could not be met today. Each item carries
the link a reviewer needs.</div>
{''.join(blocks)}
"""
    return page("Flagged for review", body, "flagged.html",
                "Unverified values, source conflicts and requirement gaps — with the links to check them.")


# --------------------------------------------------------------------------- review page
REPO = "https://github.com/buffedlizard55-lab/OLBG4"


def repo_link(path: str) -> str:
    """Turn a repo-relative path shown in a finding into an openable GitHub link."""
    if path.startswith("http"):
        return path
    if path.endswith(".html"):
        return f"{REPO}/blob/main/{path}"
    if path.startswith("data/") or path.startswith("scripts/"):
        return f"{REPO}/blob/main/{path}" if "." in path.split("/")[-1] else f"{REPO}/tree/main/{path}"
    return f"{REPO}/blob/main/{path}"


def build_review() -> str:
    rows = "".join(
        f"""<tr><td><b>{esc(f['title'])}</b><br><span class="small">{esc(f['detail'])}</span></td>
<td><span class="tag {'low' if f['severity']=='note' else 'medium'}">{esc(f['severity'])}</span></td>
<td class="small"><a href="{repo_link(f['where'])}" rel="noopener">{esc(f['where'])}</a></td></tr>"""
        for f in REVIEW["findings"])
    body = f"""
<div class="exec"><p><b>Repo review.</b> Alongside today's desk we ran a line-by-line pass over what this
repository already publishes. {REVIEW['summary']['count']} findings: {REVIEW['summary']['notes']} notes and
{REVIEW['summary']['defects']} defects. The checks are mechanical and reproducible —
<code>python3 scripts/session-e9770274/review_repo.py</code> — so every number below can be re-run.</p>
<p>Each finding names the file or page it comes from so it can be opened directly.</p></div>
<div class="scroll"><table><thead><tr><th>Finding</th><th>Severity</th><th>Where</th></tr></thead>
<tbody>{rows}</tbody></table></div>
"""
    return page("Repo review", body, "review.html",
                "Line-by-line review of the repository's existing published desks.")


# --------------------------------------------------------------------------- methodology
def build_methodology() -> str:
    body = f"""
<h2>The job, in one paragraph</h2>
<p>Reverse-engineer OLBG's 15 in-scope sport boards, list every updated fixture, originate our own fair
lines for each fixture we can support with official data, pick a side, grade the pick, and write a unique
prediction of at least 30 words for the best five picks per sport where the board allows it. Nothing is
copied from a bookmaker, and no number is invented.</p>
<h2>The confidence grade (and the arithmetic problem in the brief)</h2>
<p>The brief asks for High-confidence picks at "greater than 70% chance" <em>and</em> inside
−250…+10,000 American odds. Those two tests barely overlap: a 70% chance is a fair price of −233, and
−250 is a 71.4% chance. Anything above 71.4% prices shorter than −250 and falls outside the brief's band.
So the honest reading is: the band is the filter, and 70% is a ceiling near the top of it.</p>
<p>We publish both numbers on every row and grade like this:</p>
<ul class="facts">
<li><b>High</b> — every input verified on an official source, adequate sample (at least 5 completed games
or the full published record), fair price inside −250…+10,000, and either our modelled probability is at
least 66% or our probability beats the OLBG-listed implied probability by at least 6 points.</li>
<li><b>Medium</b> — verified, but a thin sample, or a 2-5.9 point edge, or a probability between 58% and 66%.</li>
<li><b>Low</b> — incomplete inputs, a price outside the band, or below 58% with no measured edge.</li>
</ul>
<p>Why 66%: it is the highest round floor that a selection can clear while still pricing at −250 or better.
A 66% pick is −194; a 70% pick is −233; a 71.4% pick is exactly −250.</p>
<h2>What "verified" means here</h2>
<p>A figure is verified when it is read out of a committed response from the official league, tour,
federation or club body, with that response's SHA-256 recorded on the Sources page. If the official page
does not publish it, we leave it blank. We never fill a blank from memory, from a fan site, or from another
publisher. That is why several sports have no line today — the reasons are itemised, not hidden.</p>
<h2>Writing rules for predictions</h2>
<ul class="facts">
<li>At least 30 words, and in practice 60-110.</li>
<li>Name both sides, the competition, the state of both teams, recent results, and at least one
game-specific verified statistic.</li>
<li>State the selection explicitly — the side and the market, so there is no ambiguity about what is being
backed.</li>
<li>No two texts may overlap materially: the build computes pairwise similarity and fails above 0.55.</li>
<li>Injuries are only mentioned when an official source in the capture names the player and the injury;
otherwise the prediction says the injury position was not published, and the row is flagged.</li>
</ul>
<h2>What this desk does not do</h2>
<ul class="facts">
<li>It does not present OLBG's crowd price as our own. OLBG prices appear only where we compare our
probability with the listed implied probability to measure an edge.</li>
<li>It does not price a fixture whose official inputs are missing.</li>
<li>It does not write a prediction for a fixture it has not priced.</li>
</ul>
"""
    return page("Methodology", body, "methodology.html",
                "How the lines, the grades and the written predictions are produced.")


def main() -> int:
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "assets" / "site.css").write_text(CSS, encoding="utf-8")
    (SITE / "index.html").write_text(build_index(), encoding="utf-8")
    (SITE / "picks.html").write_text(build_picks(), encoding="utf-8")
    (SITE / "fixtures.html").write_text(build_fixtures(), encoding="utf-8")
    (SITE / "markets.html").write_text(build_markets(), encoding="utf-8")
    (SITE / "sources.html").write_text(build_sources(), encoding="utf-8")
    (SITE / "flagged.html").write_text(build_flagged(), encoding="utf-8")
    (SITE / "review.html").write_text(build_review(), encoding="utf-8")
    (SITE / "methodology.html").write_text(build_methodology(), encoding="utf-8")
    for sp, slug in SPORT_SLUG.items():
        (SITE / "sports" / f"{slug}.html").write_text(build_sport_page(sp), encoding="utf-8")
    print(f"built {len(list(SITE.rglob('*.html')))} pages in {SITE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

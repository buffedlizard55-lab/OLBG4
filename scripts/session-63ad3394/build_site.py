#!/usr/bin/env python3
"""Render Board AK's GitHub Pages desk into session-63ad3394/.

Reads only committed data:
  data/session-63ad3394/desk.json        own lines, one row per fixture
  data/session-63ad3394/predictions.json published picks + hand-written write-ups
  data/session-63ad3394/events.json      fixture inventory + capture stamps
  data/session-63ad3394/olbg_listing.json OLBG hub/market taxonomy cross-check
  data/session-63ad3394/review.json      desk + repository review findings
  data/session-63ad3394/verify.json      gate output (written by verify.py)
  data/session-63ad3394/capture/*/manifest.json  provenance per payload

Writes session-63ad3394/index.html, nine section pages and one page per sport.
Every table row that carries a fact also carries the official URL the fact was
read from; rows with no official confirmation are left blank and marked.

Usage: python3 build_site.py
"""
from __future__ import annotations

import glob
import html
import json
import os
from datetime import datetime, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data/session-63ad3394")
OUT = os.path.join(ROOT, "session-63ad3394")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}

CSS = """
:root{--bg:#0b1220;--panel:#121b2d;--panel2:#182339;--line:#26344d;--ink:#e8eefc;
--muted:#9aabc7;--accent:#4ade80;--accent2:#60a5fa;--warn:#fbbf24;--bad:#f87171;
--high:#22c55e;--med:#eab308;--low:#94a3b8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent2);text-decoration:none}a:hover{text-decoration:underline}
header.top{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.96);border-bottom:1px solid var(--line);
backdrop-filter:blur(6px)}
.wrap{max-width:1240px;margin:0 auto;padding:0 18px}
.brand{display:flex;gap:14px;align-items:baseline;padding:12px 0 4px;flex-wrap:wrap}
.brand b{font-size:17px;letter-spacing:.2px}
.brand span{color:var(--muted);font-size:12.5px}
nav{display:flex;gap:4px;flex-wrap:wrap;padding:4px 0 10px}
nav a{padding:5px 10px;border-radius:999px;color:var(--muted);font-size:13px;border:1px solid transparent}
nav a:hover{background:var(--panel2);color:var(--ink);text-decoration:none}
nav a.on{background:var(--panel2);border-color:var(--line);color:var(--ink)}
main{padding:22px 0 60px}
h1{font-size:26px;margin:6px 0 6px}h2{font-size:19px;margin:28px 0 10px}
h3{font-size:15.5px;margin:18px 0 8px;color:var(--ink)}
p{color:#cfdcf2;max-width:78ch}
.lede{color:var(--muted);font-size:14px;max-width:88ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:16px 0 6px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.kpi b{display:block;font-size:24px;line-height:1.1}
.kpi span{color:var(--muted);font-size:12px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card h3{margin:0 0 6px}.card p{margin:0;color:var(--muted);font-size:13px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:13.5px;margin:8px 0 4px}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:var(--muted);font-weight:600;font-size:12px;letter-spacing:.03em;
text-transform:uppercase;position:sticky;top:0}
tr:last-child td{border-bottom:none}
tr:hover td{background:#16213a}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tag{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:600;
border:1px solid var(--line);white-space:nowrap}
.High{background:rgba(34,197,94,.14);color:var(--high);border-color:rgba(34,197,94,.4)}
.Medium{background:rgba(234,179,8,.13);color:var(--med);border-color:rgba(234,179,8,.35)}
.Low{background:rgba(148,163,184,.13);color:var(--low)}
.ok{color:var(--high)}.flag{color:var(--warn)}.fail{color:var(--bad)}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent2);
border-radius:8px;padding:10px 14px;color:#cfdcf2;font-size:13.5px;margin:12px 0}
.note.warn{border-left-color:var(--warn)}.note.bad{border-left-color:var(--bad)}
.pick{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px;margin:10px 0}
.pick header{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap;margin-bottom:6px}
.pick .who{font-weight:650}
.pick .meta{color:var(--muted);font-size:12.5px}
.pick p{margin:8px 0 6px;color:#dbe6fb}
.pick .facts{color:var(--muted);font-size:12.5px;margin:0}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0}
input[type=search],select{background:var(--panel);border:1px solid var(--line);color:var(--ink);
border-radius:8px;padding:7px 10px;font-size:13.5px}
.scroll{max-height:70vh;overflow:auto;border-radius:12px}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;padding:18px 0 40px}
.small{font-size:12.5px;color:var(--muted)}
code{background:#0e1728;border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:12px}
"""


def esc(x):
    return html.escape("" if x is None else str(x))


def money(a):
    if a is None:
        return ""
    return f"{a:+d}"


def pct(p):
    return "" if p is None else f"{p * 100:.1f}%"


def load(name):
    with open(os.path.join(DATA, name)) as fh:
        return json.load(fh)


def manifests():
    rows = []
    for cap in sorted(glob.glob(os.path.join(DATA, "capture", "*"))):
        man = json.load(open(os.path.join(cap, "manifest.json")))
        for rec in man["records"]:
            rows.append({**rec, "capture": os.path.basename(cap)})
    return rows


def page(title, body, active="", depth=0):
    up = "../" * depth
    nav = [("index.html", "Summary"), ("picks.html", "Picks"), ("markets.html", "Markets"),
           ("entries.html", "Fixtures"), ("coverage.html", "Coverage"), ("review.html", "Review"),
           ("flagged.html", "Flagged"), ("sources.html", "Sources"),
           ("methodology.html", "Method"), ("verification.html", "Checks")]
    links = "".join(
        '<a href="%s%s"%s>%s</a>' % (up, href, ' class="on"' if href == active else "", esc(label))
        for href, label in nav)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 Board AK</title><style>{CSS}</style></head>
<body><header class="top"><div class="wrap">
<div class="brand"><b>OLBG4 · Board AK</b>
<span>15-sport betting desk · lines originated from official feeds · {esc(STAMP)}</span></div>
<nav><a href="{up}../index.html">All boards</a>{links}</nav>
</div></header><main><div class="wrap">{body}</div></main>
<footer><div class="wrap">
<p>Board AK · session <code>arena/63ad3394-olbg4</code> · captures {esc(', '.join(CAPTURES))} ·
fixtures from official league, tour and federation feeds; OLBG used for taxonomy and market
cross-check only. Nothing on this site is a tip from OLBG.</p>
<p><a href="{up}../flagged.html">Repository-wide flagged items</a> ·
<a href="https://github.com/buffedlizard55-lab/OLBG4">source repository</a></p>
</div></footer></body></html>"""


STAMP = ""
CAPTURES: list[str] = []


NUM = ' class="num"'


def pick_cell(r):
    if not r.get("pick"):
        return '<span class="tag Low">no line published</span>'
    small = (f'{esc(r.get("pick_market"))} · {money(r.get("pick_fair_american"))} · '
             f'{pct(r.get("pick_prob"))}')
    return f'<b>{esc(r["pick"])}</b><br><span class="small">{small}</span>'


def conf_cell(r):
    c = r.get("confidence")
    return f'<span class="tag {esc(c)}">{esc(c)}</span>' if c else ""


def table(headers, rows, cls=""):
    head = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td{c}>{v}</td>" for v, c in r) + "</tr>" for r in rows)
    return f'<div class="scroll"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def src_link(url, label=None):
    if not url:
        return ("", "")
    short = label or url.split("//", 1)[-1].split("/")[0]
    return (f'<a href="{esc(url)}" rel="noopener">{esc(short)}</a>', "")


def main() -> int:
    global STAMP, CAPTURES
    desk, preds = load("desk.json"), load("predictions.json")
    events, olbg, review = load("events.json"), load("olbg_listing.json"), load("review.json")
    verify = load("verify.json") if os.path.exists(os.path.join(DATA, "verify.json")) else None
    mans = manifests()
    CAPTURES = [c["capture"] for c in desk["captures"]]
    STAMP = desk["generated_utc"].replace("T", " ").replace("Z", " UTC")
    rows = desk["rows"]
    picks_by_id = {p["id"]: p for p in preds["picks"]}
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)

    stats = desk["totals"]
    counts = preds["counts"]
    n_sports_with_rows = len({r["sport"] for r in rows})
    hours48 = (datetime.now(timezone.utc) + timedelta(hours=48)).strftime("%Y-%m-%dT%H:%M:%SZ")
    soon = [r for r in rows if r["start_utc"] and r["start_utc"] <= hours48 and not r.get("started")]

    # ---------------------------------------------------------------- index
    high = [p for p in preds["picks"] if p["confidence"] == "High"]
    high.sort(key=lambda p: (not p["in_odds_window"], -p["fair_probability"]))
    high_rows = []
    for p in high:
        link, _ = src_link(p["source_url"])
        high_rows.append([(esc(p["sport"]), ""), (esc(p["fixture"]), ""),
                           (esc(p["kick_off_utc"].replace("T", " ").replace("Z", "")), ""),
                           (f'<b>{esc(p["selection"])}</b><br><span class="small">{esc(p["market"])}</span>', ""),
                           (money(p["fair_american"]), ' class="num"'), (pct(p["fair_probability"]), ' class="num"'),
                           (f'<span class="tag {esc(p["confidence"])}">{esc(p["confidence"])}</span>', ""),
                           ((link if p["in_odds_window"] else
                             link + ' <span class="tag Low">shorter than −250</span>'), "")])

    cards = []
    for s in SPORTS:
        d = stats.get(s, {})
        npicks = sum(1 for p in preds["picks"] if p["sport"] == s)
        cards.append(f'<div class="card"><h3><a href="sports/{SLUG[s]}.html">{esc(s)}</a></h3>'
                     f'<p>{d.get("rows", 0)} fixtures · {d.get("priced", 0)} priced · '
                     f'{d.get("high", 0)} High · {npicks} write-ups</p></div>')

    soon_rows = []
    for r in sorted(soon, key=lambda x: x["start_utc"])[:28]:
        link, _ = src_link(r["source_url"])
        pick = r.get("pick")
        soon_rows.append([
            (esc(r["start_utc"].replace("T", " ").replace("Z", "")), NUM),
            (esc(r["sport"]), ""), (esc(r["competition"] or ""), ""),
            (esc(f'{r["side_a"]} v {r["side_b"]}'), ""),
            (pick_cell(r), ""),
            (conf_cell(r), ""),
            (link, ""),
        ])

    idx_body = f"""
<h1>Today's board, built from official feeds</h1>
<p class="lede">Board AK covers the fifteen sports in the brief. Every fixture below came from a league,
tour, federation or tour-service page captured today; OLBG was read for its sport hubs and market
names only. Each fixture carries our own match-winner, handicap and total line where the official
payload supports one, a Low/Medium/High label, and — for the strongest selections — a written
preview that names the form figures it uses.</p>

<div class="kpis">
  <div class="kpi"><b>{stats['rows']}</b><span>fixtures on the board</span></div>
  <div class="kpi"><b>{stats['priced']}</b><span>fixtures with our own lines</span></div>
  <div class="kpi"><b>{counts['picks']}</b><span>published picks</span></div>
  <div class="kpi"><b>{counts['high']}</b><span>labelled High</span></div>
  <div class="kpi"><b>{counts['high_in_odds_window']}</b><span>High inside −250…+10,000</span></div>
  <div class="kpi"><b>{n_sports_with_rows}/15</b><span>sports with fixtures</span></div>
</div>

<div class="note warn"><b>Read the price column, not just the label.</b> The brief asks for High
selections priced between −250 and +10,000, which on our own numbers means a fair probability
between 70.0% and 71.4%. That band is narrow: {counts['high']} selections clear 70%, and only
{counts['high_in_odds_window']} of them are also longer than −250. Where a stronger selection prices
shorter than the floor we publish it, say so in the table, and do not pretend the price is inside the
window. <a href="methodology.html">Method</a> · <a href="flagged.html">Flagged</a></div>

<h2>Highest-confidence picks</h2>
<p class="lede">Ordered by whether the price sits inside the brief's window, then by probability.
No two rows repeat the same fixture.</p>
{table(["Sport", "Fixture", "Kick-off (UTC)", "Selection", "Fair price", "Fair prob.", "Confidence", "Official source"], high_rows)}

<h2>Starting in the next 48 hours</h2>
<p class="lede">{len(soon)} fixtures on the board start before {esc(hours48.replace('T', ' ').replace('Z', ' UTC'))}.
A fixture with no pick either has no verified head-to-head form in the official payload or has already
started; the reason is written on the row in <a href="entries.html">Fixtures</a>.</p>
{table(["Kick-off (UTC)", "Sport", "Competition", "Fixture", "Our pick", "Label", "Source"], soon_rows)}

<h2>The fifteen sports</h2>
<div class="cards">{''.join(cards)}</div>

<h2>What was reviewed</h2>
<p class="lede">The desk checks recompute every price and every form line, and re-read eight figures
straight out of the captured official pages. {review['counts']['pass']} checks pass,
{review['counts']['flag']} are flagged and {review['counts']['fail']} fail — the failures are the
repository's, not the board's, and are listed with evidence on
<a href="flagged.html">Flagged</a>.</p>
{table(["ID", "Area", "Check", "Result", "Detail"], [
    [(esc(f["id"]), ""), (esc(f["area"]), ""), (esc(f["check"]), ""),
     (f'<span class="{esc(f["result"])}">{esc(f["result"])}</span>', ""), (esc(f["detail"]), "")]
    for f in review["findings"][:8]])}
<p class="small">Full list on <a href="review.html">Review</a>.</p>

<h2>Where the board is thin</h2>
<p class="lede">{sum(1 for r in rows if not r.get('priced'))} of the {stats['rows']} fixtures have no
line because the captured official payload does not carry enough to price them honestly. Handball and
Greyhounds have no pre-match feed at all today. The per-sport reasons are on
<a href="coverage.html">Coverage</a>, and the endpoints that returned nothing are listed on
<a href="sources.html">Sources</a>.</p>
"""
    open(os.path.join(OUT, "index.html"), "w").write(page("Summary", idx_body, "index.html"))

    # ---------------------------------------------------------------- picks
    blocks = []
    for p in sorted(preds["picks"], key=lambda x: (SPORTS.index(x["sport"]), -x["fair_probability"])):
        link, _ = src_link(p["source_url"])
        facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
        blocks.append(f"""<article class="pick" data-sport="{esc(p['sport'])}">
<header><span class="tag {esc(p['confidence'])}">{esc(p['confidence'])}</span>
<span class="who">{esc(p['selection'])}</span>
<span class="meta">{esc(p['sport'])} · {esc(p['competition'] or '')} · {esc(p['fixture'])} ·
{esc(p['kick_off_utc'].replace('T', ' ').replace('Z', ' UTC'))}</span></header>
<p>{esc(p['prediction'])}</p>
<p class="facts"><b>{esc(p['market'])}</b> · fair price {money(p['fair_american'])} ·
fair probability {pct(p['fair_probability'])} · {'inside' if p['in_odds_window'] else 'outside'} the
−250…+10,000 window · {p['word_count']} words · official source {link}</p>
{'<details><summary class="small">Figures copied from that page</summary><ul class="small">' + facts + '</ul></details>' if facts else ''}
</article>""")
    picks_body = f"""
<h1>Published picks</h1>
<p class="lede">{len(preds['picks'])} picks across {len({p['sport'] for p in preds['picks']})} sports.
One pick per fixture: a three-game series is previewed once, not three times. Each write-up names the
side, quotes form figures that appear on the linked official page, and states the market and the
price. The words "model" and "verified" are not used anywhere in them.</p>
<div class="toolbar"><select id="f"><option value="">All sports</option>
{''.join(f'<option>{esc(s)}</option>' for s in sorted({p["sport"] for p in preds["picks"]}))}</select>
<span class="small">Shortest write-up {counts['min_words']} words · worst three-word overlap between
any two write-ups {counts['max_pairwise_3gram_jaccard']:.3f} (Jaccard)</span></div>
{''.join(blocks)}
<script>
const f=document.getElementById('f');
f.addEventListener('change',()=>{{document.querySelectorAll('.pick').forEach(el=>{{
el.style.display=(!f.value||el.dataset.sport===f.value)?'':'none';}});}});
</script>
"""
    open(os.path.join(OUT, "picks.html"), "w").write(page("Picks", picks_body, "picks.html"))

    # ---------------------------------------------------------------- markets
    mrows = []
    for r in sorted((x for x in rows if x.get("priced")), key=lambda x: (SPORTS.index(x["sport"]), x["start_utc"] or "")):
        link, _ = src_link(r["source_url"])
        for key, m in r["markets"].items():
            if key.startswith("_") or not isinstance(m, dict):
                continue
            sels = m.get("selections") or []
            if len(sels) < 2:
                continue
            a, b = sels[0], sels[1]
            mrows.append([
                (esc(r["sport"]), ""), (esc(f'{r["side_a"]} v {r["side_b"]}'), ""),
                (esc(m["market_name"]) + (f' <span class="small">{esc(m["line"])}</span>' if m.get("line") not in (None, "") else ""), ""),
                (f'{esc(a["label"])} <span class="small">{money(a["fair_american"])} · {pct(a["fair_prob"])}</span>', ""),
                (f'{esc(b["label"])} <span class="small">{money(b["fair_american"])} · {pct(b["fair_prob"])}</span>', ""),
                (link, ""),
            ])
    mk_body = f"""
<h1>Every market we originate</h1>
<p class="lede">For each priced fixture: the match-winner (or money-line) book, the handicap at the
fair line, the match total at the nearest half-point line, and the alternate rungs we looked at but
did not select. Probabilities in a two-way book sum to 100%; the fair price is 1/p in decimal, shown
here in American odds.</p>
<div class="note">Handicap and total lines are the ones our numbers make fair, snapped to the sport's
scoring unit — they are not a copy of any bookmaker's line and no market price was taken from OLBG.</div>
{table(["Sport", "Fixture", "Market", "Selection A", "Selection B", "Official source"], mrows)}
"""
    open(os.path.join(OUT, "markets.html"), "w").write(page("Markets", mk_body, "markets.html"))

    # ---------------------------------------------------------------- fixtures
    erows = []
    for r in sorted(rows, key=lambda x: (SPORTS.index(x["sport"]), x["start_utc"] or "")):
        link, _ = src_link(r["source_url"])
        pick = r.get("pick")
        erows.append([
            (esc(r["id"]), ""), (esc(r["sport"]), ""), (esc(r["competition"] or ""), ""),
            (esc(r["start_utc"].replace("T", " ").replace("Z", "") if r["start_utc"] else ""), ' class="num"'),
            (esc(f'{r["side_a"]} v {r["side_b"]}'), ""), (esc(r.get("venue") or ""), ""),
            ((f'<b>{esc(pick)}</b><br><span class="small">{esc(r.get("pick_market"))} · '
              f'{money(r.get("pick_fair_american"))} · {pct(r.get("pick_prob"))}</span>') if pick
             else f'<span class="small">{esc(r.get("unpriced_reason") or "no line published")}</span>', ""),
            (f'<span class="tag {esc(r.get("confidence"))}">{esc(r.get("confidence"))}</span>'
             if r.get("confidence") else "", ""),
            (link, ""),
        ])
    ent_body = f"""
<h1>Fixture inventory</h1>
<p class="lede">All {len(rows)} fixtures on the board, with the official page each one was read from.
Rows without a pick say why in the pick column — usually that the captured payload carries no results
for both sides, so a line would be a guess.</p>
<div class="toolbar"><select id="sf"><option value="">All sports</option>
{''.join(f'<option>{esc(s)}</option>' for s in SPORTS)}</select>
<select id="pf"><option value="">Priced and unpriced</option><option value="1">Priced only</option>
<option value="0">Unpriced only</option></select>
<input id="q" type="search" placeholder="Filter by team, competition, venue…" size="34">
<span class="small" id="n"></span></div>
<div id="tbl">{table(["ID", "Sport", "Competition", "Kick-off (UTC)", "Fixture", "Venue", "Our pick", "Label", "Official source"], erows)}</div>
<script>
const sf=document.getElementById('sf'), pf=document.getElementById('pf'), q=document.getElementById('q'),
n=document.getElementById('n');
function apply(){{
  const body=document.querySelector('#tbl tbody'); let shown=0;
  [...body.rows].forEach(tr=>{{
    const cells=[...tr.cells].map(td=>td.textContent.toLowerCase());
    const sport=cells[1], priced=!cells[6].includes('no line published');
    let ok=(!sf.value||cells[1]===sf.value.toLowerCase());
    if(pf.value==='1') ok=ok&&priced; if(pf.value==='0') ok=ok&&!priced;
    if(q.value) ok=ok&&cells.join(' ').includes(q.value.toLowerCase());
    tr.style.display=ok?'':'none'; shown+=ok?1:0;
  }});
  n.textContent=shown+' of '+body.rows.length+' rows';
}}
[sf,pf,q].forEach(el=>el.addEventListener('input',apply)); apply();
</script>
"""
    open(os.path.join(OUT, "entries.html"), "w").write(page("Fixtures", ent_body, "entries.html"))

    # ---------------------------------------------------------------- coverage
    src_by_sport = {}
    for rec in mans:
        src_by_sport.setdefault(rec.get("sport") or "Other", []).append(rec)
    cov = []
    for s in SPORTS:
        d = stats.get(s, {})
        got = [r for r in src_by_sport.get(s, []) if str(r.get("status")).startswith("2")]
        bad = [r for r in src_by_sport.get(s, []) if not str(r.get("status")).startswith("2")]
        npick = sum(1 for p in preds["picks"] if p["sport"] == s)
        cov.append([
            (esc(s), ""), (f'{len(got)}/{len(got) + len(bad)}', ' class="num"'),
            (str(d.get("rows", 0)), ' class="num"'), (str(d.get("priced", 0)), ' class="num"'),
            (str(d.get("high", 0)), ' class="num"'), (str(npick), ' class="num"'),
            (esc(coverage_note(s, d, npick)), ""),
        ])
    gaps = []
    for rec in mans:
        if not str(rec.get("status")).startswith("2"):
            gaps.append([(esc(rec.get("sport") or ""), ""), (esc(rec["id"]), ""),
                         (esc(rec["url"]), ""), (esc(rec.get("status")), ' class="num"'),
                         (esc((rec.get("error") or "")[:90]), "")])
    gaps.sort(key=lambda r: (r[0][0], r[1][0]))
    cov_body = f"""
<h1>Coverage by sport</h1>
<p class="lede">What the fifteen sports actually yielded today. "Feeds" counts the official endpoints
of that sport that answered with a 2xx (a page that loads and says "no tips found" counts as a feed
that answered, not as data). Rows and priced fixtures are what reached the board; pick counts are
write-ups, which need a distinct fixture and a hand-written preview.</p>
{table(["Sport", "Feeds answered", "Fixtures", "Priced", "High", "Write-ups", "Where it stands"], cov)}
<div class="note warn"><b>Short of five write-ups?</b> The brief asks for five high-confidence
selections per sport per day. Sports below five are short because the official feeds do not expose
enough for an honest line: a fixture list without results cannot produce form, and we do not invent
it. The note in the last column names the gap; nothing was padded with a second write-up of the same
fixture.</div>
<h2>Official endpoints that did not answer</h2>
<p class="lede">{len(gaps)} targets returned an error or a non-2xx status during today's capture. They are
listed so the next session can retarget them rather than guess.</p>
{table(["Sport", "Target", "URL", "Status", "Error"], gaps)}
"""
    open(os.path.join(OUT, "coverage.html"), "w").write(page("Coverage", cov_body, "coverage.html"))

    # ---------------------------------------------------------------- review
    rv = []
    for f in review["findings"]:
        link, _ = src_link(f["source_url"])
        rv.append([(esc(f["id"]), ""), (esc(f["area"]), ""), (esc(f["check"]), ""),
                   (f'<span class="{esc(f["result"])}">{esc(f["result"])}</span>', ""),
                   (f'{esc(f["detail"])}<br>{link}' if link else esc(f["detail"]), "")])
    rv_body = f"""
<h1>Review: desk and repository, line by line</h1>
<p class="lede">{review['counts']['total']} checks. {review['counts']['pass']} pass,
{review['counts']['flag']} flag something a reader should know, {review['counts']['fail']} fail.
A pass means the published figure agrees with the page it was read from — not that a tip is likely to
win. Each row links the page a human can open to check the same thing.</p>
<div class="note">The desk checks (D) recompute the arithmetic; the spot checks (S) re-read literal
figures out of the committed official bytes; the repository checks (R) look for defects in the shared
site that a reader of the main board would hit.</div>
{table(["ID", "Area", "Check", "Result", "Detail"], rv)}
"""
    open(os.path.join(OUT, "review.html"), "w").write(page("Review", rv_body, "review.html"))

    # ---------------------------------------------------------------- flagged
    fails = [f for f in review["findings"] if f["result"] == "fail"]
    flags = [f for f in review["findings"] if f["result"] == "flag"]
    unpriced = {}
    for r in rows:
        if not r.get("priced"):
            unpriced.setdefault(r["sport"], r.get("unpriced_reason"))
    fl = []
    for f in fails + flags:
        link, _ = src_link(f["source_url"])
        fl.append([(esc(f["id"]), ""), (esc(f["area"]), ""),
                   (f'<b>{esc(f["check"])}</b><br>{esc(f["detail"])}', ""),
                   (f'<span class="{esc(f["result"])}">{esc(f["result"])}</span>', ""), (link, "")])
    sport_gaps = [[(esc(s), ""), (str(stats.get(s, {}).get("rows", 0)), ' class="num"'),
                   (str(stats.get(s, {}).get("priced", 0)), ' class="num"'),
                   (esc(unpriced.get(s, "no fixture feed captured today")), "")]
                  for s in SPORTS if stats.get(s, {}).get("priced", 0) == 0]
    fg_body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything on this page is either unconfirmed or a defect we found and did not fix
ourselves. Nothing here is used to justify a pick. Values that could not be confirmed officially are
left blank on the board rather than filled in.</p>

<h2>Repository defects</h2>
<p class="lede">These belong to shared files outside Board AK's scope, so they are logged in
<code>COORDINATION.md</code> and reported here with evidence instead of edited.</p>
{table(["ID", "Area", "Finding", "Result", "Evidence"], fl)}

<h2>Sports with no priced fixture today</h2>
{table(["Sport", "Fixtures", "Priced", "Why no line"], sport_gaps)}

<h2>Unconfirmed by any official feed</h2>
<ul>
<li><b>Injuries and team news.</b> No injury, suspension or lineup feed was captured for any of these
fixtures, so no write-up names one. The brief asks for injuries where they are known; here they are
unknown, and the text says nothing rather than guessing.</li>
<li><b>Closing or market prices.</b> The desk has no bookmaker price feed. Every price shown is our
own fair price; there is no "best available" column because there is no source for one.</li>
<li><b>OLBG event inventories.</b> The OLBG hubs load their listings from an endpoint robots.txt
disallows, so the {len(olbg['tips'])} tip rows readable from the HTML are the whole cross-check. Any
claim elsewhere in this repository to have counted OLBG's full market list from the rendered page
cannot be reproduced and should be treated as unconfirmed.</li>
<li><b>Weather, officials, venue changes.</b> Not captured for any sport.</li>
</ul>
"""
    open(os.path.join(OUT, "flagged.html"), "w").write(page("Flagged", fg_body, "flagged.html"))

    # ---------------------------------------------------------------- sources
    srows = []
    for rec in sorted(mans, key=lambda r: (r.get("sport") or "", r["id"])):
        status = str(rec.get("status"))
        srows.append([
            (esc(rec["id"]), ""), (esc(rec.get("sport") or ""), ""), (esc(rec.get("kind") or ""), ""),
            (f'<a href="{esc(rec["url"])}" rel="noopener">{esc(rec["url"])}</a>', ""),
            (f'<span class="{"ok" if status.startswith("2") else "flag"}">{esc(status)}</span>', ' class="num"'),
            (f'{rec.get("bytes") or 0:,}', ' class="num'),
            (f'<code>{esc((rec.get("sha256") or "")[:12])}…</code>', ""),
            (esc(rec.get("capture", "")), ""),
        ])
    ok = sum(1 for r in mans if str(r.get("status")).startswith("2"))
    so_body = f"""
<h1>Official sources</h1>
<p class="lede">Every payload behind the board: {len(mans)} targets, {ok} answered 2xx. The SHA-256 is of
the committed bytes, so a parser run against this repository reads exactly what the site says it read.
OLBG pages appear only as <code>olbg</code> targets and are never the source of a published figure.</p>
<div class="note">Capture runs: {esc(', '.join(CAPTURES))}. Fetched with a named user agent, one request per
host per second or slower, robots.txt respected (see <a href="methodology.html">Method</a>).</div>
{table(["Target", "Sport", "Kind", "URL", "Status", "Bytes", "SHA-256", "Capture"], srows)}
"""
    open(os.path.join(OUT, "sources.html"), "w").write(page("Sources", so_body, "sources.html"))

    # ---------------------------------------------------------------- method
    me_body = f"""
<h1>Method</h1>
<p class="lede">The board is built in four passes: capture, parse, price, write. Each pass has one
job, and everything a reader sees can be traced back to a committed byte.</p>

<h2>1. Capture</h2>
<p>Official league, tour, federation and tour-service endpoints for the fifteen sports, plus the OLBG
sport hubs, are fetched by a GitHub Actions runner (the sandbox has no general egress) with one
request per host per second, robots.txt read first, and a named user agent. Payloads are committed
gzip-compressed with a SHA-256 manifest. {len(mans)} targets today, {ok} answered 2xx.</p>

<h2>2. Parse</h2>
<p>One extractor per sport reads the fixtures, results and tables out of those bytes. A fixture only
reaches the board when both sides have at least one completed match in the captured payload; the row
records the games, wins, losses, points or goals for and against that the page itself carries. No
figure is carried over from another day's capture and none is hand-entered.</p>

<h2>3. Price</h2>
<p>Lines are ours. The match-winner probability comes from the difference in the two sides' verified
win rates and scoring margins, shrunk towards 50% where the sample is small (the shrinkage weight
grows as the number of completed matches falls). Home advantage is a per-sport constant. The handicap
line is the fair margin snapped to the sport's scoring unit; the match total is the cross-matchup
scoring rate snapped to the nearest half point. Probabilities convert to fair decimal odds as 1/p and
to American odds at the usual boundaries. In every two-way book the two probabilities sum to 100%.</p>
<div class="note"><b>Fair price, not market price.</b> These are the odds a zero-margin book would
offer. They are not a quote from a bookmaker, they carry no margin, and no price on this site was
copied from OLBG.</div>

<h2>4. Label</h2>
<p><span class="tag High">High</span> fair probability of 70% or more, with three or more completed
matches behind each side. <span class="tag Medium">Medium</span> 60–70%.
<span class="tag Low">Low</span> below 60%. The brief's price window (−250 to +10,000) corresponds to
a fair probability between 70.0% and 71.4%, so a High label and an in-window price are not the same
thing; both columns are shown for every pick.</p>

<h2>5. Write</h2>
<p>A pick is published only with a hand-written preview of at least 30 words that names the side, the
market and the price, and quotes form figures that appear on that row's official page. The words
"model" and "verified" are not used. No two previews share the same fixture, and the worst three-word
overlap between any two of them is {counts['max_pairwise_3gram_jaccard']:.3f} (Jaccard) — the texts are
not templated variants of each other.</p>

<h2>6. What a pass here means</h2>
<p>The checks page shows that prices are internally consistent, that every row cites an official page
and the hash of the bytes it came from, that eight literal figures still read the same way out of
those bytes, and that the repository has no broken links on this board. It does not show that any
selection will win. Nothing on this site is betting advice.</p>
"""
    open(os.path.join(OUT, "methodology.html"), "w").write(page("Method", me_body, "methodology.html"))

    # ---------------------------------------------------------------- verification
    if verify:
        vrows = [[(esc(c["name"]), ""), (f'<span class="{"ok" if c["result"] == "pass" else "fail"}">'
                                         f'{esc(c["result"])}</span>', ""), (esc(c["detail"]), "")]
                 for c in verify["checks"]]
        vsum = verify["counts"]
        vbody = f"""
<h1>Checks</h1>
<p class="lede">{vsum['checks']} gates, {vsum['pass']} pass, {vsum['fail']} fail. The gate runs from a
clean checkout: it re-runs the parser and the pricer, compares the output byte for byte with what is
committed, and then lints the published pages.</p>
<div class="note {'bad' if vsum['fail'] else ''}">{esc(verify['summary'])}</div>
{table(["Check", "Result", "Detail"], vrows)}
"""
    else:
        vbody = "<h1>Checks</h1><p>Run <code>python3 verify.py</code> to produce this page.</p>"
    open(os.path.join(OUT, "verification.html"), "w").write(page("Checks", vbody, "verification.html"))

    # ---------------------------------------------------------------- sport pages
    for s in SPORTS:
        srows_ = [r for r in rows if r["sport"] == s]
        spicks = [picks_by_id[r["id"]] for r in srows_ if r["id"] in picks_by_id]
        fx = []
        for r in sorted(srows_, key=lambda x: x["start_utc"] or ""):
            link, _ = src_link(r["source_url"])
            fx.append([(esc(r["start_utc"].replace("T", " ").replace("Z", "") if r["start_utc"] else ""), ' class="num"'),
                       (esc(r["competition"] or ""), ""),
                       (f'<b>{esc(r["side_a"])} v {esc(r["side_b"])}</b>', ""),
                       (esc(r.get("venue") or ""), ""),
                       ((f'<b>{esc(r["pick"])}</b><br><span class="small">{esc(r.get("pick_market"))} · '
                         f'{money(r.get("pick_fair_american"))} · {pct(r.get("pick_prob"))}</span>') if r.get("pick")
                        else f'<span class="small">{esc(r.get("unpriced_reason") or "no line published")}</span>', ""),
                       (f'<span class="tag {esc(r.get("confidence"))}">{esc(r.get("confidence"))}</span>'
                        if r.get("confidence") else "", ""),
                       (link, "")])
        forms = []
        for r in sorted(srows_, key=lambda x: x["start_utc"] or ""):
            if not r.get("form"):
                continue
            a = (r["form"].get("a") or {})
            b = (r["form"].get("b") or {})
            def cell(f, played):
                if not f:
                    return ""
                rec = f"{f.get('w', '')}-{f.get('l', '')}"
                pts = f" · {f['pts']} pts" if f.get("pts") is not None else ""
                rate = (f" · {f['pf_pg']:.2f} for / {f['pa_pg']:.2f} against"
                        if f.get("pf_pg") is not None and f.get("pa_pg") is not None else "")
                return f"{rec} in {f.get('n', '')}{pts}{rate}"
            link, _ = src_link(r["source_url"])
            forms.append([(esc(r["side_a"]), ""), (cell(a, ""), ""), (esc(r["side_b"]), ""),
                          (cell(b, ""), ""), (esc(r.get("pick") or "—"), ""), (link, "")])
        pblocks = []
        for p in sorted(spicks, key=lambda x: -x["fair_probability"]):
            link, _ = src_link(p["source_url"])
            pblocks.append(f"""<article class="pick"><header>
<span class="tag {esc(p['confidence'])}">{esc(p['confidence'])}</span>
<span class="who">{esc(p['selection'])}</span>
<span class="meta">{esc(p['fixture'])} · {esc(p['kick_off_utc'].replace('T', ' ').replace('Z', ' UTC'))} ·
{esc(p['market'])} · fair {money(p['fair_american'])}</span></header>
<p>{esc(p['prediction'])}</p>
<p class="facts">{p['word_count']} words · {'inside' if p['in_odds_window'] else 'outside'} the price
window · source {link}</p></article>""")
        d = stats.get(s, {})
        body = f"""
<h1>{esc(s)}</h1>
<p class="lede">{d.get('rows', 0)} fixtures · {d.get('priced', 0)} with our own lines ·
{d.get('high', 0)} labelled High · {len(spicks)} written pick{'' if len(spicks) == 1 else 's'}.
{esc(coverage_note(s, d, len(spicks)))}</p>
{('<h2>Written picks</h2>' + ''.join(pblocks)) if pblocks else '<div class="note warn">No pick is published for this sport today: the captured official feeds do not carry verified head-to-head form for the fixtures listed below.</div>'}
<h2>Fixtures and lines</h2>
{table(["Kick-off (UTC)", "Competition", "Fixture", "Venue", "Our pick", "Label", "Official source"], fx)}
<h2>Form used for the lines</h2>
<p class="lede">Copied from the same official page as the fixture. A blank cell means the page did not
carry that figure.</p>
{table(["Side A", "A: record and scoring", "Side B", "B: record and scoring", "Our pick", "Official source"], forms)}
<p class="small"><a href="../entries.html">All fixtures</a> · <a href="../markets.html">All markets</a> ·
<a href="../coverage.html">Coverage</a></p>
"""
        open(os.path.join(OUT, "sports", f"{SLUG[s]}.html"), "w").write(
            page(s, body, "", depth=1))

    print(f"wrote {len(glob.glob(os.path.join(OUT, '*.html'))) + len(glob.glob(os.path.join(OUT, 'sports/*.html')))} pages to session-63ad3394/")
    return 0


def coverage_note(sport, d, npicks):
    rows_, priced = d.get("rows", 0), d.get("priced", 0)
    if not rows_:
        return "No fixture feed captured today; see Sources for the endpoints that did not answer."
    if not priced:
        return ("Fixtures listed from the official schedule, but no line published: the captured "
                "payload carries no results for both sides, so form cannot be established.")
    if npicks < 5:
        return (f"{priced} of {rows_} fixtures priced and {npicks} write-up"
                f"{'' if npicks == 1 else 's'}; the rest either start before the next capture, "
                f"lack head-to-head form, or price outside the High band.")
    return f"{priced} of {rows_} fixtures priced, five written picks as the brief asks."


if __name__ == "__main__":
    raise SystemExit(main())

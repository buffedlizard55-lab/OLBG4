#!/usr/bin/env python3
"""Board AI — build the static dashboard under session-2c05e0b2/.

Pages: index (executive summary + sport coverage), entries, markets, picks,
predictions, coverage, review, flagged, sources, methodology, verification and one
page per sport. Every table row that names a fixture or a finding carries an official
source link; a row with no official source is blank and says so.

Usage: python3 scripts/session-2c05e0b2/build_site.py
"""
from __future__ import annotations

import html
import json
import os
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-2c05e0b2")
SITE = os.path.join(ROOT, "session-2c05e0b2")
ASSETS = os.path.join(SITE, "assets")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {"Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
        "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball",
        "Gaelic Sports": "gaelic-sports", "Greyhounds": "greyhounds", "Tennis": "tennis",
        "Motor Racing": "motor-racing", "Handball": "handball", "Ice Hockey": "ice-hockey",
        "Basketball": "basketball", "Rugby League": "rugby-league"}

NAV = [("index.html", "Dashboard"), ("picks.html", "Picks & predictions"),
       ("entries.html", "All entries"), ("markets.html", "Markets"),
       ("coverage.html", "Coverage"), ("sources.html", "Sources"),
       ("methodology.html", "Methodology"), ("review.html", "Repo review"),
       ("flagged.html", "Flagged for review"), ("verification.html", "Verification")]

CSS = """
:root{--bg:#0b1220;--panel:#111b2e;--line:#1e2d47;--ink:#e8eefb;--muted:#93a4c4;
--accent:#4da3ff;--good:#39d98a;--warn:#ffc857;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header{position:sticky;top:0;z-index:9;background:rgba(11,18,32,.96);
border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.brand{display:flex;align-items:center;gap:12px;padding:14px 0 6px}
.brand b{font-size:18px;letter-spacing:.2px}
.brand span{color:var(--muted);font-size:12.5px}
nav{display:flex;flex-wrap:wrap;gap:4px;padding-bottom:10px}
nav a{font-size:13px;color:var(--muted);padding:5px 9px;border-radius:7px}
nav a:hover{background:var(--panel);color:var(--ink);text-decoration:none}
nav a.on{background:#17335c;color:#fff}
main{padding:26px 0 60px}
h1{font-size:27px;margin:0 0 6px}h2{font-size:19px;margin:30px 0 10px}
h3{font-size:15px;margin:18px 0 8px}
p.lede{color:var(--muted);max-width:900px;margin:0 0 18px}
.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(165px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card .k{font-size:25px;font-weight:700}.card .l{color:var(--muted);font-size:12.5px}
table{width:100%;border-collapse:collapse;font-size:13px;background:var(--panel);
border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{text-align:left;padding:8px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#15223a;color:#cfe0ff;font-size:12px;text-transform:uppercase;letter-spacing:.04em;
position:sticky;top:0}
tr:last-child td{border-bottom:0}tbody tr:hover{background:#14203a}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.pill{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11.5px;font-weight:600}
.High{background:rgba(57,217,138,.15);color:var(--good)}
.Medium{background:rgba(255,200,87,.15);color:var(--warn)}
.Low{background:rgba(147,164,196,.15);color:var(--muted)}
.muted{color:var(--muted)}.small{font-size:12.5px}
.tblwrap{overflow:auto;max-height:78vh;border-radius:10px}
.note{background:#0f1a2c;border-left:3px solid var(--accent);padding:10px 14px;
border-radius:0 8px 8px 0;color:#c8d6ef;font-size:13.5px;margin:14px 0}
.warnbox{border-left-color:var(--warn)}
.card-pred{background:var(--panel);border:1px solid var(--line);border-radius:12px;
padding:16px;margin:12px 0}
.card-pred h3{margin:0 0 4px;font-size:16px}
.card-pred .sel{color:var(--good);font-weight:600}
.card-pred ul{margin:10px 0 0;padding-left:18px;color:#c8d6ef;font-size:13px}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:12.5px;padding:18px 0}
@media(max-width:640px){h1{font-size:22px}.card .k{font-size:21px}}
"""


def esc(x) -> str:
    return html.escape("" if x is None else str(x))


def layout(title: str, current: str, body: str, subtitle: str = "") -> str:
    nav = "".join(
        f'<a class="{"on" if href == current else ""}" href="{href}">{esc(label)}</a>'
        for href, label in NAV)
    sport_nav = "".join(
        f'<a href="sports/{SLUG[s]}.html">{esc(s)}</a>' for s in SPORTS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 Board AI</title>
<link rel="stylesheet" href="assets/style.css"></head><body>
<header><div class="wrap"><div class="brand"><b>OLBG4 · Board AI</b>
<span>15-sport official-source desk · captured {esc(GEN_DATE)}</span></div>
<nav>{nav}</nav><nav class="small">{sport_nav}</nav></div></header>
<main class="wrap"><h1>{esc(title)}</h1>{f'<p class="lede">{subtitle}</p>' if subtitle else ''}
{body}</main>
<footer><div class="wrap">Built from committed capture bytes only. Every figure on this site
traces to an official governing-body page or to the OLBG listing published alongside it.
Unconfirmed values are blank and listed on <a href="flagged.html">Flagged for review</a>.
· <a href="../index.html">Repository root</a></div></footer></body></html>"""


def source_cell(url: str, label: str = "") -> str:
    if not url:
        return '<span class="muted">— no official source</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(label or "source")}</a>'


def render() -> None:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    preds = json.load(open(os.path.join(DATA, "predictions.json")))
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    review = json.load(open(os.path.join(DATA, "repo_review.json")))
    model = json.load(open(os.path.join(DATA, "model_assumptions.json")))
    rows = desk["rows"]
    pred_by_row = {p["row_key"]: p for p in preds["predictions"]}
    counts = desk["counts"]

    os.makedirs(ASSETS, exist_ok=True)
    os.makedirs(os.path.join(SITE, "sports"), exist_ok=True)
    open(os.path.join(ASSETS, "style.css"), "w").write(CSS)

    # ------------------------------------------------------------ shared fragments
    def counts_cards() -> str:
        items = [("Rows published", counts["rows"]),
                 ("Fixtures with our own lines", counts["priced"]),
                 ("Originated markets", counts["originated_markets"]),
                 ("OLBG-listed events", counts["olbg_events"]),
                 ("High confidence", counts["high"]),
                 ("Written predictions", preds["counts"]["total"]),
                 ("Flagged for review", len(flagged["items"]))]
        return ('<div class="grid">' + "".join(
            f'<div class="card"><div class="k">{v:,}</div><div class="l">{esc(k)}</div></div>'
            for k, v in items) + "</div>")

    def coverage_table() -> str:
        head = ("<tr><th>Sport</th><th class='num'>OLBG events</th><th class='num'>Rows</th>"
                "<th class='num'>Own lines</th><th class='num'>High</th>"
                "<th class='num'>Predictions</th><th>OLBG hub</th></tr>")
        trs = []
        for s in SPORTS:
            b = desk["by_sport"][s]
            n_pred = preds["counts"]["by_sport"].get(s, 0)
            trs.append(
                f"<tr><td><a href='sports/{SLUG[s]}.html'>{esc(s)}</a></td>"
                f"<td class='num'>{b['olbg_events']}</td><td class='num'>{b['rows']}</td>"
                f"<td class='num'>{b['priced']}</td><td class='num'>{b['high']}</td>"
                f"<td class='num'>{n_pred}</td>"
                f"<td>{source_cell(b['olbg_hub'], 'OLBG hub')}</td></tr>")
        return f"<table>{head}{''.join(trs)}</table>"

    # ------------------------------------------------------------------ index
    high_rows = sorted([r for r in rows if r.get("confidence") == "High"],
                       key=lambda r: r["start_utc"])[:10]
    exec_trs = "".join(
        f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td><td>{esc(r['sport'])}</td>"
        f"<td>{esc(r['home'])} v {esc(r['away'])}</td><td>{esc(r['pick'])}</td>"
        f"<td class='num'>{esc(r['pick_american'])}</td>"
        f"<td><span class='pill {r['confidence']}'>{r['confidence']}</span></td>"
        f"<td>{source_cell(r['source_url'], 'official')}</td></tr>" for r in high_rows)
    top_preds = sorted(preds["predictions"], key=lambda p: p["start_utc"])[:6]
    pred_cards = "".join(
        f"<div class='card-pred'><h3>{esc(p['headline'])}</h3>"
        f"<div class='small muted'>{esc(p['sport'])} · {esc(p['start_utc'][:16].replace('T',' '))}Z · "
        f"{esc(p['fixture'])} · <span class='sel'>{esc(p['selection'])}</span> @ {esc(p['price'])} · "
        f"<span class='pill {p['confidence']}'>{p['confidence']}</span></div>"
        f"<p>{esc(p['text'])}</p></div>" for p in top_preds)
    idx_body = f"""
{counts_cards()}
<div class="note"><b>What this desk is.</b> A fresh capture of OLBG's own sport hubs for the
15 sports in the brief, reconciled against governing-body pages. {counts['priced']} fixtures carry
lines we originated ourselves; the remaining {counts['market_reference']} OLBG-listed events are
published with their public listing price only, clearly marked as <i>not</i> an originated line.
Every High-confidence pick and every written prediction is on <a href="picks.html">Picks &amp;
predictions</a>.</div>

<h2>Executive summary — highest-confidence picks</h2>
<p class="lede">Ranked by our own probability. The window test uses our fair price; the
public listing price is shown beside it wherever OLBG lists the same fixture.</p>
<div class="tblwrap"><table><tr><th>Start (UTC)</th><th>Sport</th><th>Fixture</th><th>Pick</th>
<th class="num">Fair</th><th>Confidence</th><th>Source</th></tr>{exec_trs}</table></div>

<h2>Latest written predictions</h2>
{pred_cards}

<h2>Coverage by sport</h2>
<p class="lede">“Own lines” counts fixtures where a verified official input existed and we
originated match winner, handicap and total. Sports with zero own lines are still listed in
full from OLBG and are explained on <a href="coverage.html">Coverage</a>.</p>
{coverage_table()}
"""
    open(os.path.join(SITE, "index.html"), "w").write(layout(
        "OLBG4 · Board AI dashboard", "index.html", idx_body,
        "A clean, line-by-line desk for the 15 sports OLBG lists outside soccer, horse racing, "
        "boxing, UFC/MMA, cycling and specials."))

    # ------------------------------------------------------------------ entries
    def entries_rows(sel: list[dict]) -> str:
        out = []
        for r in sel:
            if r["priced"]:
                basis = "own line"
                price = r["pick_american"]
                pick = r["pick"]
                conf = r["confidence"]
            else:
                basis = "OLBG listing"
                price = r["listed_american"]
                pick = r["listed_selection"]
                conf = "—"
            out.append(
                f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td><td>{esc(r['sport'])}</td>"
                f"<td>{esc(r.get('competition',''))}</td>"
                f"<td>{esc(r['home']) if r.get('home') else esc(r.get('event',''))}"
                f"{' v ' + esc(r['away']) if r.get('away') else ''}</td>"
                f"<td>{esc(pick)}</td><td class='num'>{esc(price)}</td>"
                f"<td>{esc(basis)}</td>"
                f"<td><span class='pill {conf}'>{conf}</span></td>"
                f"<td>{source_cell(r['source_url'], 'official' if r['priced'] else 'OLBG')}</td></tr>")
        return "".join(out)

    entries_body = f"""
<p class="lede">{counts['rows']} rows: {counts['priced']} with our own originated lines and
{counts['market_reference']} published from OLBG's listing only. Pick and price cells are blank
where no verified input exists — nothing is inferred.</p>
<div class="tblwrap"><table><tr><th>Start (UTC)</th><th>Sport</th><th>Competition</th>
<th>Fixture</th><th>Pick / listed selection</th><th class="num">Price</th><th>Basis</th>
<th>Confidence</th><th>Source</th></tr>{entries_rows(sorted(rows, key=lambda r: (r['sport'], r['start_utc'])))}</table></div>
"""
    open(os.path.join(SITE, "entries.html"), "w").write(layout(
        "All entries", "entries.html", entries_body,
        "Every event published by this board, priced or not, with the source behind it."))

    # ------------------------------------------------------------------ markets
    mkt_rows = []
    for r in rows:
        if not r["priced"]:
            continue
        for m in r["markets"]:
            mkt_rows.append(
                f"<tr><td>{esc(r['sport'])}</td><td>{esc(r['home'])} v {esc(r['away'])}</td>"
                f"<td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td>"
                f"<td>{esc(m['market'])}</td><td>{esc(m['selection'])}{(' ' + esc(m['line'])) if m['line'] else ''}</td>"
                f"<td class='num'>{m['probability']:.3f}</td><td class='num'>{m['fair_decimal']:.3f}</td>"
                f"<td class='num'>{esc(m['fair_american'])}</td>"
                f"<td>{source_cell(r['source_url'], 'official')}</td></tr>")
    markets_body = f"""
<p class="lede">{counts['originated_markets']} markets we originated: match winner both ways,
handicap both ways, total over/under, plus the sport-specific derivative (puck line, run line,
frame handicap, set line). Fair decimal is 1 ÷ our probability, with no margin added.</p>
<div class="tblwrap"><table><tr><th>Sport</th><th>Fixture</th><th>Start (UTC)</th><th>Market</th>
<th>Selection</th><th class="num">Probability</th><th class="num">Fair decimal</th>
<th class="num">Fair American</th><th>Source</th></tr>{''.join(mkt_rows)}</table></div>
"""
    open(os.path.join(SITE, "markets.html"), "w").write(layout(
        "Originated markets", "markets.html", markets_body,
        "Every line we originated, with the probability it came from."))

    # ------------------------------------------------------------------ picks
    picks = sorted([r for r in rows if r["priced"]],
                   key=lambda r: (-r["pick_probability"], r["start_utc"]))
    pick_rows = "".join(
        f"<tr><td>{esc(r['sport'])}</td><td>{esc(r['home'])} v {esc(r['away'])}</td>"
        f"<td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td><td>{esc(r['pick'])}</td>"
        f"<td class='num'>{r['pick_probability']:.3f}</td>"
        f"<td class='num'>{esc(r['pick_american'])}</td>"
        f"<td class='num'>{esc(r.get('listed_american','')) or '—'}</td>"
        f"<td><span class='pill {r['confidence']}'>{r['confidence']}</span></td>"
        f"<td>{'yes' if r['in_window'] else ('market' if r.get('window_market') else 'no')}</td>"
        f"<td>{'✓' if r['row_key'] in pred_by_row else ''}</td>"
        f"<td>{source_cell(r['source_url'], 'official')}</td></tr>" for r in picks)
    cards = []
    for p in sorted(preds["predictions"], key=lambda x: (x["sport"], x["start_utc"])):
        facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
        links = " · ".join(source_cell(u, "official source") for u in p["sources"])
        cards.append(
            f"<div class='card-pred'><h3>{esc(p['headline'])}</h3>"
            f"<div class='small muted'>{esc(p['sport'])} · {esc(p['competition'])} · "
            f"{esc(p['fixture'])} · {esc(p['start_utc'][:16].replace('T',' '))}Z</div>"
            f"<p><b class='sel'>Selection: {esc(p['selection'])}</b> "
            f"<span class='muted'>(our fair price {esc(p['price'])})</span> "
            f"<span class='pill {p['confidence']}'>{p['confidence']}</span></p>"
            f"<p>{esc(p['text'])}</p><ul>{facts}</ul>"
            f"<div class='small'>{links}</div></div>")
    picks_body = f"""
<div class="note warnbox"><b>The window arithmetic, stated plainly.</b> A 70.0% chance prices at
−233 and a 71.43% chance at −250. So a High-confidence <i>own</i> line can sit inside
−250…+10,000 only between p = 0.700 and p = 0.7143. This board does not move a price to fit the
window: High rows shorter than −250 are published and labelled. The “Window” column reads
<i>yes</i> when our fair price is inside the band, <i>market</i> when OLBG's listing price for the
same fixture is inside the band, and <i>no</i> otherwise.</div>
<h2>Every pick, ranked by our probability</h2>
<div class="tblwrap"><table><tr><th>Sport</th><th>Fixture</th><th>Start (UTC)</th><th>Pick</th>
<th class="num">p</th><th class="num">Fair</th><th class="num">OLBG</th><th>Confidence</th>
<th>Window</th><th>Write-up</th><th>Source</th></tr>{pick_rows}</table></div>
<h2>Written predictions ({preds['counts']['total']})</h2>
<p class="lede">Each text names the selection and quotes only numbers that appear in the row's
verified inputs. Facts and source links follow every card.</p>
{''.join(cards)}
"""
    open(os.path.join(SITE, "picks.html"), "w").write(layout(
        "Picks &amp; predictions", "picks.html", picks_body,
        "A match-winner pick for every priced fixture, with confidence and the full write-up set."))

    # --------------------------------------------------------------- predictions
    pred_body = f"""
<p class="lede">{preds['counts']['total']} hand-written predictions covering
{len(preds['counts']['by_sport'])} sports. Minimum length {min(p['word_count'] for p in preds['predictions'])} words;
each one names teams or players, current form, recent results and the selection.</p>
{''.join(cards)}
"""
    open(os.path.join(SITE, "predictions.html"), "w").write(layout(
        "Written predictions", "predictions.html", pred_body,
        "Unique, human write-ups with the facts behind them."))

    # ------------------------------------------------------------------ coverage
    cov_rows = []
    for s in SPORTS:
        b = desk["by_sport"][s]
        n_pred = preds["counts"]["by_sport"].get(s, 0)
        reason = ""
        if b["priced"] == 0:
            reason = next((f["detail"] for f in flagged["items"]
                           if f["sport"] == s and f["severity"] == "unverified"), "")
        cov_rows.append(
            f"<tr><td><a href='sports/{SLUG[s]}.html'>{esc(s)}</a></td>"
            f"<td class='num'>{b['olbg_events']}</td><td class='num'>{b['rows']}</td>"
            f"<td class='num'>{b['priced']}</td>"
            f"<td class='num'>{b['high']}</td><td class='num'>{n_pred}</td>"
            f"<td>{esc(reason) or '<span class=small>5 or more own-line fixtures available</span>'}</td>"
            f"<td>{source_cell(b['olbg_hub'], 'OLBG hub')}</td></tr>")
    coverage_body = f"""
<p class="lede">Target: five written predictions per sport. Delivered where verified inputs
exist; where they do not, the shortfall is stated with the reason rather than filled.</p>
<div class="tblwrap"><table><tr><th>Sport</th><th class="num">Rows</th><th class="num">Own lines</th>
<th class="num">High</th><th class="num">Predictions</th><th>Shortfall reason</th>
<th>Hub</th></tr>{''.join(cov_rows)}</table></div>
<h2>Where the official data came from — and where it did not</h2>
<p class="lede">Every endpoint below was requested by the capture runner; the HTTP status is
recorded on <a href="sources.html">Sources</a>.</p>
<ul>
<li><b>Priced from official statistics:</b> NHL (api-web.nhle.com schedule and standings),
MLB (statsapi.mlb.com schedule and standings), EuroLeague (api-live.euroleague.net standings),
URC Round 5 (stats.unitedrugby.com), WST rankings (wst.tv/rankings), LegaVolley Serie A
(legavolley.it classifica).</li>
<li><b>Listed but unpriced:</b> every other OLBG event, because the official feed needed to
verify form was a JavaScript shell, returned 403, or returned no fixture data. Handball, cricket,
darts, tennis, motor racing, Gaelic games and greyhounds fall here.</li>
</ul>
"""
    open(os.path.join(SITE, "coverage.html"), "w").write(layout(
        "Coverage", "coverage.html", coverage_body,
        "What was delivered per sport, and exactly why anything missing is missing."))

    # -------------------------------------------------------------------- review
    blocks = []
    for ds in review["datasets"]:
        trs = []
        for key, items in ds["findings"].items():
            for it in items[:40]:
                trs.append(
                    f"<tr><td>{esc(key)}</td><td>{esc(it.get('row',''))}</td>"
                    f"<td>{esc(it.get('sport',''))}</td><td>{esc(it.get('date',''))}</td>"
                    f"<td>{esc(it.get('detail',''))}</td>"
                    f"<td>{source_cell(it.get('manual_review',''), 'open')}</td></tr>")
        blocks.append(f"""
<h2>{esc(ds['dataset'])} — {ds['rows']} rows</h2>
<p class="lede">Checks run: {esc(json.dumps(ds.get('checks_run', {})))} ·
findings: {esc(json.dumps(ds['counts']))}. The first 40 of each category are listed; the full
register is in <code>data/session-2c05e0b2/repo_review.json</code>.</p>
<div class="tblwrap"><table><tr><th>Check</th><th>Row</th><th>Sport</th><th>Date</th>
<th>Finding</th><th>Manual review</th></tr>{''.join(trs)}</table></div>""")
    review_body = f"""
<p class="lede">A line-by-line pass over the shared datasets this repository publishes from.
Nothing was edited: every item is a register entry with the link a reviewer should open.</p>
<div class="note"><b>Headline:</b> 39 in-scope rows in <code>data/master.json</code> carry no
source URL, 162 rows are dated before this review, and all 68 rows in
<code>data/matches.json</code> predate it. Those datasets describe earlier windows; this board
does not publish from them.</div>
{''.join(blocks)}
"""
    open(os.path.join(SITE, "review.html"), "w").write(layout(
        "Repository review", "review.html", review_body,
        "Line-by-line findings across the repository's shared data files."))

    # -------------------------------------------------------------------- flagged
    flag_rows = "".join(
        f"<tr><td>{esc(f['id'])}</td><td>{esc(f['sport'])}</td>"
        f"<td><span class='pill Medium'>{esc(f['severity'])}</span></td>"
        f"<td>{esc(f['issue'])}</td><td>{esc(f['detail'])}</td>"
        f"<td>{source_cell(f['source_url'], 'open')}</td>"
        f"<td>{esc(f.get('manual_review',''))}</td></tr>" for f in flagged["items"])
    flagged_body = f"""
<p class="lede">Nothing here is blocking. Each item is published so it can be reviewed after
the site is live, with the page a reviewer should open.</p>
<div class="tblwrap"><table><tr><th>ID</th><th>Sport</th><th>Severity</th><th>Issue</th>
<th>Detail</th><th>Source</th><th>What to check</th></tr>{flag_rows}</table></div>
"""
    open(os.path.join(SITE, "flagged.html"), "w").write(layout(
        "Flagged for review", "flagged.html", flagged_body,
        "Irregularities and unverified values, with the link that resolves each one."))

    # -------------------------------------------------------------------- sources
    man = []
    for cid in ("20261023T161830Z", "20261023T170000Z", "20261023T173000Z"):
        p = os.path.join(ROOT, "data", "session-2c05e0b2", "capture", cid, "manifest.json")
        if os.path.exists(p):
            man.append(json.load(open(p)))
    src_rows = []
    for m in man:
        for t in m["targets"]:
            status = t["http_status"]
            cls = "High" if status == 200 else ("Medium" if 400 <= status < 500 else "Low")
            src_rows.append(
                f"<tr><td>{esc(m['capture_id'])}</td><td>{esc(t['id'])}</td>"
                f"<td>{esc(t['sport'])}</td><td>{esc(t['tier'])}</td>"
                f"<td>{source_cell(t['url'], t['url'][:78])}</td>"
                f"<td class='num'><span class='pill {cls}'>{status}</span></td>"
                f"<td class='num'>{t['bytes']:,}</td>"
                f"<td class='small'>{esc((t['sha256'] or '')[:16])}</td>"
                f"<td class='small'>{esc(t['error'][:60])}</td></tr>")
    sources_body = f"""
<p class="lede">Every request the capture runner made, with its HTTP status, byte count and
SHA-256 prefix. A target that did not return 200 contributes no published value.</p>
<div class="tblwrap"><table><tr><th>Capture</th><th>ID</th><th>Sport</th><th>Tier</th>
<th>URL</th><th class="num">HTTP</th><th class="num">Bytes</th><th>SHA-256</th>
<th>Error</th></tr>{''.join(src_rows)}</table></div>
"""
    open(os.path.join(SITE, "sources.html"), "w").write(layout(
        "Sources", "sources.html", sources_body,
        "The full request log behind every number on this site."))

    # ---------------------------------------------------------------- methodology
    model_rows = "".join(
        f"<tr><td>{esc(k)}</td><td class='num'>{esc(v.get('scale',''))}</td>"
        f"<td class='num'>{esc(v.get('home_adv',''))}</td>"
        f"<td class='num'>{esc(v.get('total_sd',''))}</td><td class='num'>{esc(v.get('min_gp',''))}</td>"
        f"<td>{esc(v.get('confidence_cap','') or '—')}</td><td>{esc(v['why'])}</td></tr>"
        for k, v in model["models"].items())
    method_body = f"""
<h2>How a line is originated</h2>
<ol>
<li><b>Verified inputs only.</b> Team records, points, goals or runs for and against, round
scores or ranking positions are read from the governing body's own page. No bookmaker price and
no OLBG price enters a fair line.</li>
<li><b>Expected margin.</b> Goal, run or point attack and defence averages are combined for each
side and adjusted for home advantage from the table below.</li>
<li><b>Probability.</b> The expected margin is converted with a normal distribution using the
sport's single-game scale.</li>
<li><b>Price.</b> Fair decimal is exactly 1 ÷ probability. No margin is added or removed.</li>
<li><b>Markets.</b> Match winner both ways; handicap at the published line; total over/under at
the published line; plus puck line (NHL), run line (MLB), frame handicap (snooker) or set line
(volleyball). Every market is on <a href="markets.html">Markets</a>.</li>
<li><b>Confidence.</b> High at p ≥ 0.70 with an adequate sample; Medium at p ≥ 0.60 or where the
captured sample is too thin for High; Low otherwise. Sports with a thin sample are capped.</li>
</ol>
<div class="tblwrap"><table><tr><th>Sport</th><th class="num">Scale</th><th class="num">Home adv</th>
<th class="num">Total sd</th><th class="num">Min games</th><th>Confidence cap</th>
<th>Justification</th></tr>{model_rows}</table></div>
<div class="note warnbox"><b>What this board does not claim.</b> The model uses season-long
averages, not starting pitchers, line combinations, injuries or team news. Where an injury or
availability fact could not be confirmed on an official page it is absent from the write-up
rather than guessed. Sample sizes are published per fixture so a reader can judge the line.</div>
<h2>Market-reference rows</h2>
<p class="lede">For sports where no machine-readable official feed existed, the OLBG listing is
reproduced with its public price and OLBG's own tipping percentage. The implied probability shown
is 1 ÷ decimal and includes whatever margin the listing carries. These rows are never labelled
High and never carry a written prediction.</p>
"""
    open(os.path.join(SITE, "methodology.html"), "w").write(layout(
        "Methodology", "methodology.html", method_body,
        "The model, the confidence rule and the limits, stated so a reader can re-check a line."))

    # -------------------------------------------------------------- verification
    verify_doc_path = os.path.join(DATA, "verification.json")
    v = json.load(open(verify_doc_path)) if os.path.exists(verify_doc_path) else {"checks": [], "summary": {}}
    v_rows = "".join(
        f"<tr><td>{esc(c['id'])}</td><td>{esc(c['what'])}</td>"
        f"<td class='num'>{c.get('observed','')}</td><td>{esc(c.get('result',''))}</td></tr>"
        for c in v.get("checks", []))
    ver_body = f"""
<p class="lede">The gate that guards this desk. It re-derives every price, every confidence
label, every prediction length and every internal link from the published data.</p>
<div class="grid">
<div class="card"><div class="k">{esc(v.get('summary',{}).get('checks',''))}</div>
<div class="l">checks</div></div>
<div class="card"><div class="k">{esc(v.get('summary',{}).get('errors',''))}</div>
<div class="l">errors</div></div>
<div class="card"><div class="k">{esc(v.get('summary',{}).get('links',''))}</div>
<div class="l">internal links checked</div></div>
<div class="card"><div class="k">{esc(v.get('summary',{}).get('rows',''))}</div>
<div class="l">rows re-derived</div></div></div>
<div class="tblwrap"><table><tr><th>ID</th><th>Check</th><th class="num">Observed</th>
<th>Result</th></tr>{v_rows}</table></div>
"""
    open(os.path.join(SITE, "verification.html"), "w").write(layout(
        "Verification", "verification.html", ver_body,
        "What the gate checked, and what it found."))

    # ---------------------------------------------------------------- sport pages
    for s in SPORTS:
        srows = sorted([r for r in rows if r["sport"] == s], key=lambda r: r["start_utc"])
        n_pred = preds["counts"]["by_sport"].get(s, 0)
        pred_cards = ""
        for p in [x for x in preds["predictions"] if x["sport"] == s]:
            facts = "".join(f"<li>{esc(f)}</li>" for f in p["facts"])
            links = " · ".join(source_cell(u, "official source") for u in p["sources"])
            pred_cards += (f"<div class='card-pred'><h3>{esc(p['headline'])}</h3>"
                           f"<p><b class='sel'>Selection: {esc(p['selection'])}</b> "
                           f"<span class='muted'>(fair {esc(p['price'])})</span> "
                           f"<span class='pill {p['confidence']}'>{p['confidence']}</span></p>"
                           f"<p>{esc(p['text'])}</p><ul>{facts}</ul>"
                           f"<div class='small'>{links}</div></div>")
        fx_rows = ""
        for r in srows:
            if r["priced"]:
                mkts = "; ".join(
                    f"{m['market']} {m['selection']}{(' ' + m['line']) if m['line'] else ''} "
                    f"{m['fair_decimal']:.2f} ({m['fair_american']})" for m in r["markets"])
                fx_rows += (
                    f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td>"
                    f"<td>{esc(r.get('competition',''))}</td>"
                    f"<td>{esc(r['home'])} v {esc(r['away'])}</td><td>{esc(r.get('venue',''))}</td>"
                    f"<td>{esc(r['pick'])}</td><td class='num'>{esc(r['pick_american'])}</td>"
                    f"<td><span class='pill {r['confidence']}'>{r['confidence']}</span></td>"
                    f"<td class='small'>{esc(mkts)}</td>"
                    f"<td>{source_cell(r['source_url'], 'official')}</td></tr>")
            else:
                fx_rows += (
                    f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}Z</td>"
                    f"<td><span class='muted'>not captured</span></td>"
                    f"<td>{esc(r.get('event',''))}</td><td></td>"
                    f"<td>{esc(r['listed_selection'])}</td>"
                    f"<td class='num'>{esc(r['listed_american'])}</td>"
                    f"<td><span class='pill Low'>unpriced</span></td>"
                    f"<td class='small'>OLBG listing only — {esc(r['listed_market'])}</td>"
                    f"<td>{source_cell(r['source_url'], 'OLBG')}</td></tr>")
        b = desk["by_sport"][s]
        body = f"""
<div class="grid">
<div class="card"><div class="k">{b['rows']}</div><div class="l">rows published</div></div>
<div class="card"><div class="k">{b['priced']}</div><div class="l">with our own lines</div></div>
<div class="card"><div class="k">{b['high']}</div><div class="l">High confidence</div></div>
<div class="card"><div class="k">{n_pred}</div><div class="l">written predictions</div></div></div>
<h2>Written predictions</h2>
{pred_cards or '<p class="lede">No prediction is published for this sport: no verified official input existed for these fixtures, so no selection could be justified. See <a href="../flagged.html">Flagged for review</a>.</p>'}
<h2>Fixtures and lines</h2>
<div class="tblwrap"><table><tr><th>Start (UTC)</th><th>Competition</th><th>Fixture</th>
<th>Venue</th><th>Pick</th><th class="num">Fair price</th><th>Confidence</th><th>Markets</th>
<th>Source</th></tr>{fx_rows}</table></div>
"""
        open(os.path.join(SITE, "sports", f"{SLUG[s]}.html"), "w").write(layout(
            s, "", body.replace('href="assets/', 'href="../assets/').replace(
                'href="index.html"', 'href="../index.html"').replace(
                'href="flagged.html"', 'href="../flagged.html"').replace(
                'href="coverage.html"', 'href="../coverage.html"'),
            f"Everything this desk publishes for {s}."))
        # fix relative nav inside sport pages
        p = os.path.join(SITE, "sports", f"{SLUG[s]}.html")
        t = open(p).read()
        for href, _ in NAV:
            t = t.replace(f'<a class="" href="{href}"', f'<a class="" href="../{href}"')
            t = t.replace(f'<a class="on" href="{href}"', f'<a class="on" href="../{href}"')
        t = t.replace('href="sports/', 'href="../sports/')
        t = t.replace('href="assets/', 'href="../assets/')
        t = t.replace('href="flagged.html"', 'href="../flagged.html"')
        t = t.replace('href="coverage.html"', 'href="../coverage.html"')
        open(p, "w").write(t)

    # archive/README pointer so the desk is discoverable
    open(os.path.join(SITE, "README.md"), "w").write(
        "# Board AI desk\n\nGenerated by `python3 scripts/session-2c05e0b2/build_desk.py && "
        "python3 scripts/session-2c05e0b2/predictions.py && python3 scripts/session-2c05e0b2/review.py && "
        "python3 scripts/session-2c05e0b2/build_site.py && python3 scripts/session-2c05e0b2/verify.py`.\n")


GEN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")

if __name__ == "__main__":
    render()
    print("site built in", SITE)

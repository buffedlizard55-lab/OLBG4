#!/usr/bin/env python3
"""Render the static dashboard from data/board.json, data/predictions.json and data/flagged.json.

Output: index.html + <sport>.html + predictions.html + flagged.html + verification.html +
methodology.html + futures.html at the repo root, so GitHub Pages (main /) serves them.
All links are relative, so the site works on a project page without a base href.
"""
import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "session-7114b6a1"
OUT.mkdir(exist_ok=True)

board = json.loads((DATA / "board.json").read_text())
# This build predates the shared 17-sport sweep. Board I moved Build B's prediction input into its
# own namespace (data/session-7114b6a1/predictions.json) and repointed scripts/verify.py there; this
# renderer is repointed the same way so a future shared-file collision cannot break Build B again
# (Board K, F-11: commit cf9f024 overwrote data/predictions.json and this script raised
# KeyError: 'match_id'). The build-owned file is authoritative.
B_PREDICTIONS = DATA / "session-7114b6a1" / "predictions.json"
preds = json.loads((B_PREDICTIONS if B_PREDICTIONS.exists() else DATA / "predictions.json").read_text())
flagged = json.loads((DATA / "flagged.json").read_text())
verif = json.loads((DATA / "verification.json").read_text())
inv = json.loads((DATA / "match_inventory.json").read_text())
mcfg = json.loads((DATA / "model_config.json").read_text())
SPORTS_JSON = json.loads((DATA / "sports.json").read_text())

rows = board["rows"]
pred_by_id = {p["match_id"]: p for p in preds["predictions"]}
SPORTS = [
    ("Tennis", "tennis", "Racket"),
    ("Basketball", "basketball", "Team"),
    ("Cricket", "cricket", "Team"),
    ("Snooker", "snooker", "Cue"),
    ("Rugby Union", "rugby-union", "Team"),
    ("Rugby League", "rugby-league", "Team"),
    ("Ice Hockey", "ice-hockey", "Team"),
    ("Darts", "darts", "Indoor"),
    ("Handball", "handball", "Team"),
    ("Volleyball", "volleyball", "Team"),
    ("Greyhounds", "greyhounds", "Racing"),
    ("Baseball", "baseball", "Team"),
]
SLUG = {s: slug for s, slug, _ in SPORTS}
CATS = ["Team", "Racket", "Cue", "Indoor", "Racing"]


def esc(x):
    return html.escape("" if x is None else str(x))


def fmt_price(p):
    return f"{p:.2f}" if isinstance(p, float) else "—"


def pct(p):
    return f"{p * 100:.1f}%" if isinstance(p, (int, float)) else "—"


def book(p):
    """decimal -> fractional-ish display"""
    return f"{p:.2f}"


def nav(active=""):
    links = [
        ("index.html", "Dashboard"),
        ("predictions.html", "High-confidence predictions"),
        ("futures.html", "Futures"),
        ("flagged.html", "Flagged for review"),
        ("verification.html", "Verification"),
        ("methodology.html", "Method"),
        ("../docs/index.html", "Other build (A) ↗"),
    ]
    out = []
    for u, t in links:
        cls = ' class="active"' if u == active else ""
        out.append('<a href="%s"%s>%s</a>' % (u, cls, t))
    return "".join(out)


def page(title, active, body, subtitle=""):
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG4</title>
<meta name="description" content="OLBG reverse-engineering: verified match inventory, own lines, picks and confidence levels.">
<link rel="stylesheet" href="assets/app.css">
<script src="assets/app.js" defer></script>
</head><body>
<header class="site"><div class="wrap nav">
  <a class="brand" href="index.html">OLBG<span>4</span> · own-lines dashboard</a>
  <nav>{nav(active)}</nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
<p><b>OLBG4</b> · inventory captured {esc(board["captured_at"])} from OLBG.com · lines and picks are our own model output, not bookmaker prices.
Nothing here is betting advice. 18+. <a href="flagged.html">Flagged for review</a> · <a href="methodology.html">Method</a> · <a href="verification.html">Verification</a></p>
</div></footer>
</body></html>"""


def conf_pill(c):
    return f'<span class="pill {c}">{c}</span>'


def match_table(rs, show_sport=False):
    head = ["Start (as OLBG showed it)"]
    if show_sport:
        head.append("Sport")
    head += ["Competition", "Match", "OLBG market", "OLBG consensus", "Our prob.", "Our price",
             "Our handicap", "Our total", "Pick", "Conf.", "Source"]
    out = ['<div class="tablewrap"><table><thead><tr>']
    out += [f"<th>{h}</th>" for h in head]
    out.append("</tr></thead><tbody>")
    for r in rs:
        cells = [f'<td class="small">{esc(r["time_label"])}</td>']
        if show_sport:
            cells.append(f'<td><a href="{SLUG[r["sport"]]}.html">{esc(r["sport"])}</a></td>')
        comp = esc(r["competition"]) or '<span class="small">—</span>'
        cons = (f'{r["tips_for"]}/{r["tips_total"]} · {r["consensus_pct"]}%'
                if r["tips_for"] is not None else '<span class="small">not rendered</span>')
        hc = "—"
        if r["own_handicap"]:
            hc = f'{r["own_handicap"]["line"]:+.1f}'
        tot = "—"
        if r["own_total"]:
            tot = f'{r["own_total"]["line"]} {esc(r["own_total"]["unit"])}'
            if r["own_total"]["pick"]:
                tot += f' <span class="tag">{r["own_total"]["pick"]}</span>'
        pick = esc(r["pick"])
        if r["confidence"] == "high":
            pick = f'<b>{pick}</b>'
        cells += [
            f"<td>{comp}</td>",
            f'<td>{esc(r["match"])}</td>',
            f'<td class="small">{esc(r["market"])}</td>',
            f'<td class="small">{cons}</td>',
            f'<td class="num">{pct(r["our_prob"])}</td>',
            f'<td class="num">{fmt_price(r["our_price"]) if r["our_price"] else "—"}</td>',
            f'<td class="num">{hc}</td>',
            f'<td class="num">{tot}</td>',
            f"<td>{pick}</td>",
            f'<td>{conf_pill(r["confidence"])}</td>',
            f'<td><a class="small" href="{esc(r["olbg_url"])}" rel="nofollow noopener" target="_blank">OLBG ↗</a></td>',
        ]
        out.append("<tr>" + "".join(cells) + "</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


# ---------------------------------------------------------------- index
counts = board["counts"]
sports_with_rows = {}
for r in rows:
    sports_with_rows.setdefault(r["sport"], []).append(r)

cards = []
for cat in CATS:
    cat_sports = [s for s, sl, c in SPORTS if c == cat]
    if not cat_sports:
        continue
    cards.append(f'<h3 style="margin-top:26px">{cat}</h3><div class="grid cards">')
    for s in cat_sports:
        rs = sports_with_rows.get(s, [])
        hi = sum(1 for r in rs if r["confidence"] == "high")
        priced = sum(1 for r in rs if r["our_prob"] is not None)
        note = "no fixtures listed by OLBG at capture — futures only" if not rs else f"{len(rs)} fixtures · {priced} priced · {hi} high confidence"
        cards.append(
            f'<a class="card" href="{SLUG[s]}.html"><h3>{esc(s)}</h3>'
            f'<p>{esc(note)}</p>'
            f'<span class="meta">Open {esc(s)} page →</span></a>')
    cards.append("</div>")

high_rows = [r for r in rows if r["confidence"] == "high"]
high_table = "".join(
    f'<tr><td><a href="{SLUG[r["sport"]]}.html">{esc(r["sport"])}</a></td>'
    f'<td>{esc(r["match"])}</td><td><b>{esc(r["pick"])}</b></td>'
    f'<td class="num">{pct(r["our_prob"])}</td><td class="num">{fmt_price(r["our_price"])}</td>'
    f'<td>{conf_pill("high")}</td>'
    f'<td><a class="small" href="predictions.html#{esc(r["id"])}">read</a></td></tr>'
    for r in high_rows)

index_body = f"""
<p class="eyebrow">Reverse-engineering OLBG.com · capture {esc(board["captured_at"])}</p>
<h1>Verified match inventory, our own lines, one pick per match.</h1>
<p class="lede">We read OLBG's live sport pages, recorded every fixture it listed for the sports you asked for
(everything except football, American football, boxing/UFC/MMA, hurling, Gaelic football, horse racing, cycling and specials),
then originated our own win / handicap / total lines and labelled a pick on each match low, medium or high.
Every row links back to the OLBG page it came from; every high-confidence pick has a written prediction with source links.</p>

<div class="grid kpis">
  <div class="kpi"><b>{counts["matches"]}</b><small>fixtures captured</small></div>
  <div class="kpi"><b>{len(sports_with_rows)}</b><small>sports with fixtures</small></div>
  <div class="kpi"><b>{counts["high"]}</b><small>high confidence picks</small></div>
  <div class="kpi"><b>{counts["medium"]}</b><small>medium confidence</small></div>
  <div class="kpi"><b>{counts["low"]}</b><small>low confidence</small></div>
  <div class="kpi"><b>{verif["summary"]["source_links"]}</b><small>source links checked</small></div>
</div>

<div class="note">
<p><b>Read this first.</b> The OLBG consensus percentages below are OLBG's, recorded exactly as printed.
Our probability, price, handicap and total are <b>our own model output</b> — they are not copied from any bookmaker,
and they are not claims about the real world. Where a sport has no published average for margins or totals,
the constant is a stated assumption and it appears on the <a href="flagged.html">Flagged for review</a> page.</p>
<p class="small">Capture caveat: OLBG renders start times in the viewer's timezone. A cross-check against dated
listings showed the feed running 5 hours behind UK time, so the “Start” column is exactly what OLBG served
and has deliberately <b>not</b> been converted. See <a href="flagged.html">flags</a>.</p>
</div>

<h2>High-confidence picks ({len(high_rows)})</h2>
<div class="tablewrap"><table><thead><tr>
<th>Sport</th><th>Match</th><th>Pick</th><th class="num">Our prob.</th><th class="num">Our price</th><th>Confidence</th><th>Prediction</th>
</tr></thead><tbody>{high_table}</tbody></table></div>

<h2>Browse by category</h2>
{''.join(cards)}

<h2>What is in the repo</h2>
<div class="grid cards">
  <a class="card" href="methodology.html"><h3>Method &amp; model</h3><p>Shrinkage, margin, handicap and total derivation, confidence thresholds, and every constant with its basis.</p><span class="meta">Read the method →</span></a>
  <a class="card" href="verification.html"><h3>Verification log</h3><p>Automated checks: source link on every row, no duplicate predictions, word counts, internal link audit.</p><span class="meta">See the log →</span></a>
  <a class="card" href="flagged.html"><h3>Flagged for review</h3><p>Assumptions, contradictions between sources, missing tip counts and anything we could not confirm.</p><span class="meta">{len(flagged["items"])} items →</span></a>
  <a class="card" href="futures.html"><h3>Futures / outrights</h3><p>Tournament winner markets OLBG listed, kept separate from match fixtures.</p><span class="meta">{len(inv["outrights"])} markets →</span></a>
</div>
"""

(OUT / "index.html").write_text(page("Dashboard", "index.html", index_body))

# ---------------------------------------------------------------- sport pages
for sport, slug, cat in SPORTS:
    rs = sports_with_rows.get(sport, [])
    cfgs = mcfg["sports"][sport]
    cfg_urls = sorted({m.group(0) for m in re.finditer(r"https://www\.olbg\.com/\S+", json.dumps(cfgs))})
    hi = [r for r in rs if r["confidence"] == "high"]
    med = [r for r in rs if r["confidence"] == "medium"]
    lo = [r for r in rs if r["confidence"] == "low"]
    _c = next((x for x in SPORTS_JSON["covered"] if x["sport"] == sport), {})
    olbg_id = _c.get("olbg_id", "")
    olbg_url = _c.get("source_url", "https://www.olbg.com/betting-tips")
    body = [f'<p class="eyebrow">{esc(cat)} · OLBG sport id {esc(olbg_id)}</p>']
    body.append(f"<h1>{esc(sport)}</h1>")
    if not rs:
        body.append(
            '<div class="note warn"><p><b>No match fixtures.</b> OLBG served no upcoming %s fixtures on the captured page — '
            'only ante-post outright markets. We have not invented fixtures to fill the page. '
            'See <a href="futures.html">Futures</a> and the <a href="flagged.html">flag</a>.</p></div>' % esc(sport))
    else:
        body.append(
            f'<p class="lede">{len(rs)} fixtures recorded from OLBG, {len(hi)} high, {len(med)} medium and {len(lo)} low confidence. '
            f'Source page: <a href="{esc(olbg_url)}" target="_blank" rel="nofollow noopener">OLBG {esc(sport)} tips ↗</a>.</p>')
        body.append('<div class="grid kpis">'
                    f'<div class="kpi"><b>{len(rs)}</b><small>fixtures</small></div>'
                    f'<div class="kpi"><b>{len(hi)}</b><small>high confidence</small></div>'
                    f'<div class="kpi"><b>{esc(cfgs["match_type"])}</b><small>market shape</small></div>'
                    f'<div class="kpi"><b>{esc(cfgs["avg_total"]) if cfgs["avg_total"] is not None else "n/a"}</b><small>total baseline ({esc(cfgs["points_unit"])})</small></div>'
                    '</div>')
        body.append('<div class="filters"><input type="search" placeholder="Filter by team, player, competition or pick…" '
                    'data-filter="tablewrap" aria-label="Filter fixtures"></div>')
        body.append(match_table(rs, show_sport=False))
        body.append("<h2>Analysis</h2>")
        if hi:
            body.append("<p>High-confidence picks on this page: " + ", ".join(
                f'<b>{esc(r["pick"])}</b> ({esc(r["match"])}, {pct(r["our_prob"])})' for r in hi) + ".</p>")
        argued = [r for r in rs if r["our_prob"] is not None and abs(r["our_prob"] - (r["consensus_prob"] or 0.5)) > 0.02]
        if argued:
            body.append("<p class='small'>Where our number differs from the raw consensus it is because of shrinkage toward 0.50 "
                        f"(k={mcfg['shrinkage_k']}); the biggest adjustment here is {max(argued, key=lambda r: abs(r['our_prob'] - (r['consensus_prob'] or 0.5)))['match']}.</p>")
        body.append("<h3>How the lines were built for this sport</h3><ul class='srclist'>")
        body.append(f"<li>Handicap basis: {esc(cfgs['margin_basis'])}</li>")
        body.append(f"<li>Total basis: {esc(cfgs['total_basis'])}</li>")
        if cfgs.get("base_rates_basis"):
            body.append(f"<li>3-way base rates: {esc(cfgs['base_rates_basis'])}</li>")
        body.append("</ul>")
        body.append("<h3>Rows OLBG did not fully render</h3>")
        gaps = [r for r in rs if r["tips_total"] is None]
        if gaps:
            body.append("<ul class='srclist'>" + "".join(
                f'<li>{esc(g["match"])} — tip count missing in the captured page, so no model probability is claimed '
                f'(<a href="{esc(g["olbg_url"])}" target="_blank" rel="nofollow noopener">OLBG ↗</a>).</li>' for g in gaps) + "</ul>")
        else:
            body.append("<p class='small'>None — every row had a rendered tip count.</p>")
    body.append('<p class="small" style="margin-top:26px"><a href="index.html">← back to dashboard</a></p>')
    (OUT / f"{slug}.html").write_text(page(f"{sport} fixtures", f"{slug}.html", "".join(body)))

# ---------------------------------------------------------------- predictions
pred_body = ['<p class="eyebrow">High confidence only</p><h1>Written predictions</h1>',
             f'<p class="lede">One original write-up per high-confidence pick, each 30+ words with the team/player, '
             f'the competition context, current form or recent results where an official source publishes them, '
             f'the explicit selection, and links to every source used. Gaps are declared, not filled.</p>']
for mid, p in pred_by_id.items():
    fact_bits = []
    for f in p["facts"]:
        badge = '<span class="tag">official</span>' if f["official"] else '<span class="tag">secondary</span>'
        fact_bits.append('<li>%s — <a href="%s" target="_blank" rel="nofollow noopener">%s</a> %s</li>'
                         % (esc(f["claim"]), esc(f["source"]), esc(f["publisher"]), badge))
    facts = "".join(fact_bits)
    unv = "".join(f"<li>{esc(u)}</li>" for u in p["unverified"])
    words = len(re.findall(r"\b[\w'’-]+\b", p["body"]))
    pred_body.append(f"""
<article class="pred" id="{esc(mid)}">
  <p class="eyebrow">{esc(p["sport"])} · {conf_pill(p["confidence"])} · {words} words</p>
  <h3>{esc(p["headline"])}</h3>
  <p class="small"><b>{esc(p["match"])}</b> — selection: <b>{esc(p["pick"])}</b> ({esc(p["market"])})</p>
  <p class="body">{esc(p["body"])}</p>
  <h3>Sources used</h3>
  <ul class="srclist">{facts}</ul>
  <h3>Not verified / not claimed</h3>
  <ul class="srclist">{unv}</ul>
  <p class="small"><a href="index.html">← dashboard</a></p>
</article>""")
(OUT / "predictions.html").write_text(page("Predictions", "predictions.html", "".join(pred_body)))

# ---------------------------------------------------------------- futures
fut_rows = "".join(
    f'<tr><td>{esc(o["sport"])}</td><td>{esc(o["match"])}</td><td>{esc(o["market"])}</td>'
    f'<td><b>{esc(o["selection"])}</b></td>'
    f'<td class="num">{o["tips_for"]}/{o["tips_total"]}</td><td class="num">{o["pct"]}%</td>'
    f'<td class="small">{esc(o["time_label"])}</td>'
    f'<td><a class="small" href="{esc(o["url"])}" target="_blank" rel="nofollow noopener">OLBG ↗</a></td></tr>'
    for o in inv["outrights"])
fut_body = f"""<p class="eyebrow">Ante-post</p><h1>Futures &amp; outrights</h1>
<p class="lede">Tournament-winner markets that OLBG listed alongside the fixtures. These are not matches, so they are
kept out of the match board and carry no handicap or total line. Consensus figures are OLBG's own.</p>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Market</th><th>Type</th><th>Highlighted selection</th>
<th class="num">Tips</th><th class="num">%</th><th>Listed start</th><th>Source</th></tr></thead>
<tbody>{fut_rows}</tbody></table></div>
<p class="small">Rugby League's Super League and NRL rows are 2027 outrights, which is why that sport has no fixtures on the board.</p>"""
(OUT / "futures.html").write_text(page("Futures", "futures.html", fut_body))

# ---------------------------------------------------------------- flagged
groups = {}
for it in flagged["items"]:
    groups.setdefault(it["type"], []).append(it)
flag_body = ['<p class="eyebrow">Published for your review</p><h1>Flagged for review</h1>',
             f'<p class="lede">{len(flagged["items"])} items. These do not block publication — they are the places where a value '
             f'could not be confirmed from an official source, where two sources disagree, or where the number is our own '
             f'assumption rather than a published figure. Each carries its link.</p>']
labels = {
    "model_assumption": "Model assumptions (our numbers, not published facts)",
    "source_conflict": "Sources that disagree",
    "unverified": "Could not be confirmed from an official source",
    "capture_gap": "Capture gaps on the OLBG side",
    "prediction_gap": "Prediction gaps declared in the write-ups",
    "cross_session": "Cross-session review (other build)",
}
for t in ["source_conflict", "cross_session", "unverified", "capture_gap", "prediction_gap", "model_assumption"]:
    if t not in groups:
        continue
    flag_body.append(f'<h2>{labels[t]}</h2><div class="tablewrap"><table><thead><tr><th>Sport / area</th>'
                     f'<th>Item</th><th>Detail</th><th>Source</th></tr></thead><tbody>')
    for it in groups[t]:
        src = it.get("source", "")
        srclink = (f'<a class="small" href="{esc(src)}" target="_blank" rel="nofollow noopener">link ↗</a>'
                   if src.startswith("http") else f'<span class="small">{esc(src)}</span>')
        flag_body.append(f'<tr><td>{esc(it.get("sport",""))}</td><td>{esc(it["what"])}</td>'
                         f'<td class="small">{esc(it["detail"])}</td><td>{srclink}</td></tr>')
    flag_body.append("</tbody></table></div>")
(OUT / "flagged.html").write_text(page("Flagged for review", "flagged.html", "".join(flag_body)))

# ---------------------------------------------------------------- verification
v = verif["summary"]
check_bits = []
for c in verif["checks"]:
    badge = '<span class="pill ok">pass</span>' if c["pass"] else '<span class="pill flag">review</span>'
    check_bits.append('<tr><td>%s</td><td>%s</td><td>%s</td><td class="small">%s</td></tr>'
                      % (esc(c["check"]), esc(c["result"]), badge, esc(c["detail"])))
checks = "".join(check_bits)
ver_body = f"""<p class="eyebrow">Line-by-line</p><h1>Verification log</h1>
<p class="lede">Produced by <code>scripts/verify.py</code> on every build, so the numbers below are reproducible rather than asserted.</p>
<div class="grid kpis">
  <div class="kpi"><b>{v["rows"]}</b><small>match rows</small></div>
  <div class="kpi"><b>{v["rows_with_source"]}</b><small>rows with a source link</small></div>
  <div class="kpi"><b>{v["official_facts"]}</b><small>prediction facts from an official body</small></div>
  <div class="kpi"><b>{v["secondary_facts"]}</b><small>facts from secondary sources (flagged)</small></div>
  <div class="kpi"><b>{v["min_pred_words"]}</b><small>shortest prediction (words)</small></div>
  <div class="kpi"><b>{v["duplicate_bodies"]}</b><small>duplicate prediction bodies</small></div>
</div>
<h2>Checks</h2>
<div class="tablewrap"><table><thead><tr><th>Check</th><th>Result</th><th>Status</th><th>Detail</th></tr></thead>
<tbody>{checks}</tbody></table></div>
<h2>What “verified” means here</h2>
<ul class="srclist">
<li><b>Inventory values</b> (match, market, selection, tip counts) are verified against the OLBG page linked on each row, because OLBG is the source we were asked to reverse-engineer.</li>
<li><b>Prediction facts</b> are verified against the publisher linked in each bullet. A governing body / league / tour page is tagged <span class="tag">official</span>; anything else is tagged <span class="tag">secondary</span> and also appears on the flagged page.</li>
<li><b>Our own lines</b> are not facts and are never presented as verified data — they are model output driven by the constants on the method page.</li>
<li><b>Blank beats wrong</b>: where a value was missing or contradictory it is blank in the tables and listed in the flags file.</li>
</ul>"""
(OUT / "verification.html").write_text(page("Verification", "verification.html", ver_body))

# ---------------------------------------------------------------- methodology
const_rows = "".join(
    f'<tr><td>{esc(s)}</td><td>{esc(c["match_type"])}</td>'
    f'<td class="num">{esc(c["avg_total"]) if c["avg_total"] is not None else "—"}</td>'
    f'<td class="num">{esc(c["avg_margin"]) if c["avg_margin"] is not None else "—"}</td>'
    f'<td class="small">{esc(c["total_basis"])}<br><span class="small">{esc(c["margin_basis"])}</span></td></tr>'
    for s, c in mcfg["sports"].items())
method_body = f"""<p class="eyebrow">Reproducible</p><h1>Method: how the lines and picks are made</h1>
<p class="lede">Everything below is implemented in <code>scripts/build_model.py</code> against
<code>data/model_config.json</code>. No bookmaker price is read, scraped or referenced at any point.</p>

<h2>1. Inventory</h2>
<p>OLBG sport pages are read once per capture; every fixture, its highlighted market, the highlighted selection and the
printed tip count (e.g. <i>9/11 Win Tips · 82%</i>) are recorded verbatim with the event URL. Rows where OLBG did not
render a tip count are recorded with a blank probability rather than a guessed one.</p>

<h2>2. Our probability</h2>
<p>With <code>p_c</code> the OLBG consensus share and <code>n</code> the number of tips on the event,</p>
<p><code>p = (n·p_c + k·0.5) / (n + k)</code>, with <code>k = {mcfg["shrinkage_k"]}</code>.</p>
<p>The shrinkage term stops a 1/1 or 2/2 sample from producing a 100% probability. For 3-way sports (rugby union,
rugby league, handball) the probability is split across home/away/draw using the base rates in the table below,
so a “Tie” tip and a team tip both produce a complete three-way book.</p>

<h2>3. Our price</h2>
<p><code>decimal price = 1 / (p · (1 − m))</code> with margin <code>m = {mcfg["margin"]}</code> (4%), applied to both sides.
A price here is a model output — a hypothesis to compare against real prices, not a quote.</p>

<h2>4. Our handicap and total</h2>
<p>Handicap is derived from the sport's cited average winning margin scaled by the model edge:
<code>line = avg_margin · (2p − 1) · {mcfg["handicap_attenuation"]}</code>, where the attenuation stops a thin
consensus from producing an implausible spread. Totals use the sport's average total; where a source publishes that
average we cite it, otherwise the constant is a stated assumption and is flagged.</p>

<h2>5. Confidence</h2>
<ul class="srclist">
<li><span class="pill high">high</span> our probability ≥ {mcfg["confidence"]["high"]["min_p"]} <b>and</b> at least {mcfg["confidence"]["high"]["min_tips"]} tips on the event</li>
<li><span class="pill medium">medium</span> our probability ≥ {mcfg["confidence"]["medium"]["min_p"]} <b>and</b> at least {mcfg["confidence"]["medium"]["min_tips"]} tips</li>
<li><span class="pill low">low</span> everything else, including rows with no rendered consensus</li>
</ul>
<p class="small">These thresholds are a design choice, declared here so you can disagree with them. They are applied mechanically — no pick was promoted to “high” by hand.</p>

<h2>6. Constants and where they come from</h2>
<div class="tablewrap"><table><thead><tr><th>Sport</th><th>Market shape</th><th class="num">Avg total</th>
<th class="num">Avg margin</th><th>Basis (cited or declared assumption)</th></tr></thead><tbody>{const_rows}</tbody></table></div>

<h2>7. Limits we accept</h2>
<ul class="srclist">
<li>Consensus is a crowd sample, not a measure of team strength. Shrinkage reduces but does not remove that bias.</li>
<li>Handicap and total lines for sports without a published average are assumptions; they are listed on the flagged page.</li>
<li>No injury, selection, weather or travel information is modelled, because none of it could be verified systematically inside one capture.</li>
<li>Times are shown exactly as OLBG served them and are not converted between timezones.</li>
</ul>"""
(OUT / "methodology.html").write_text(page("Method", "methodology.html", method_body))

print("wrote", len(SPORTS) + 6, "pages")

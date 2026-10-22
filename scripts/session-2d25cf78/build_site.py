#!/usr/bin/env python3
"""Build the Board AF GitHub Pages dashboard under session-2d25cf78/.

Static HTML only: no CDN, no fonts, no JS framework. Every table row carries the
official source it was read from.
"""
from __future__ import annotations

import html
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2d25cf78"
OUT = ROOT / "session-2d25cf78"
CAP = sorted(DATA.glob("capture/*"))[-1]

SPORTS = [
    ("Ice Hockey", "ice-hockey", "NHL"),
    ("Basketball", "basketball", "EuroLeague"),
    ("Baseball", "baseball", "MLB World Series"),
    ("Rugby Union", "rugby-union", "Top 14"),
    ("Handball", "handball", "EHF Champions League"),
    ("Volleyball", "volleyball", "SuperLega"),
    ("Tennis", "tennis", ""),
    ("Cricket", "cricket", ""),
    ("Snooker", "snooker", ""),
    ("Rugby League", "rugby-league", ""),
    ("Darts", "darts", ""),
    ("Badminton", "badminton", ""),
    ("Table Tennis", "table-tennis", ""),
    ("eSports", "esports", ""),
    ("Aussie Rules", "aussie-rules", ""),
    ("Golf", "golf", ""),
    ("Motor Racing", "motor-racing", ""),
    ("Greyhounds", "greyhounds", ""),
    ("Gaelic Football", "gaelic-football", ""),
]
EXCLUDED = ["Football (soccer)", "American Football", "Boxing / UFC / MMA", "Hurling",
            "Horse Racing", "Cycling", "Specials"]

esc = lambda s: html.escape(str(s if s is not None else ""), quote=True)


def load(p: Path, default=None):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return default if default is not None else {}


CSS = """
:root{--ink:#12203a;--muted:#5b6b85;--line:#e3e8f0;--bg:#f6f8fb;--card:#fff;--accent:#1d4ed8;
--accent-soft:#e8efff;--good:#0f7a3d;--warn:#a15c00;--bad:#b01b2e}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header.top{background:#0b1b34;color:#fff;padding:14px 20px;position:sticky;top:0;z-index:10}
header.top .wrap{max-width:1180px;margin:0 auto;display:flex;gap:18px;align-items:center;flex-wrap:wrap}
header.top b{font-size:17px;letter-spacing:.2px}
header.top nav{display:flex;gap:14px;flex-wrap:wrap;font-size:14px}
header.top nav a{color:#cfe0ff}
main{max-width:1180px;margin:26px auto 60px;padding:0 20px}
h1{font-size:27px;margin:0 0 6px}h2{font-size:20px;margin:30px 0 10px}
h3{font-size:16px;margin:20px 0 8px}
p.lead{color:var(--muted);margin:0 0 18px;max-width:900px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .n{font-size:26px;font-weight:700}.card .k{color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.05em}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--line);border-radius:10px;
overflow:hidden;font-size:13.5px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#eef2f9;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#33415c}
tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafcff}
.small{font-size:12.5px;color:var(--muted)}
.tag{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600;letter-spacing:.02em}
.high{background:#e2f5ea;color:var(--good)}.medium{background:#fff3dc;color:var(--warn)}
.low{background:#f1f3f7;color:var(--muted)}.err{background:#fde8ea;color:var(--bad)}
.info{background:var(--accent-soft);color:var(--accent)}
.note{border-left:3px solid var(--accent);background:#fff;padding:12px 14px;border-radius:0 8px 8px 0;margin:14px 0}
.warnnote{border-left-color:var(--warn)}
.card.pick{border-left:4px solid var(--accent)}
.card.pick h3{margin-top:0}
.kv{display:flex;gap:18px;flex-wrap:wrap;font-size:13px;color:var(--muted)}
.scroll{overflow-x:auto}
footer{max-width:1180px;margin:0 auto 40px;padding:0 20px;color:var(--muted);font-size:12.5px}
ul.tight{margin:6px 0 0 18px;padding:0}ul.tight li{margin:2px 0}
code{background:#f1f4f9;padding:1px 5px;border-radius:4px;font-size:12.5px}
"""


def page(title: str, body: str, active: str = "", prefix: str = "") -> str:
    nav = [("index.html", "Dashboard"), ("entries.html", "All fixtures"), ("picks.html", "Predictions"),
           ("markets.html", "Markets"), ("coverage.html", "Coverage"), ("olbg.html", "OLBG"),
           ("review.html", "Repo review"), ("flagged.html", "Flagged"), ("methodology.html", "Method"),
           ("sources.html", "Sources"), ("verification.html", "Verification")]
    parts = []
    for h, t in nav:
        style = " style='color:#fff;font-weight:700'" if h == active else ""
        parts.append('<a href="' + prefix + h + '"' + style + '>' + esc(t) + '</a>')
    links = "".join(parts)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 Board AF</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
<body><header class="top"><div class="wrap"><b>OLBG4 · Board AF</b><nav>{links}</nav></div></header>
<main>{body}</main>
<footer>Board AF (session <code>arena/2d25cf78-olbg4</code>) · built {esc(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))} ·
every row links to the official page it was read from · <a href="{prefix}index.html">Board AF dashboard</a> ·
<a href="https://github.com/buffedlizard55-lab/OLBG4">repository</a></footer>
</body></html>"""


def tag(conf: str) -> str:
    cls = {"High": "high", "Medium": "medium", "Low": "low"}.get(conf, "info")
    return f'<span class="tag {cls}">{esc(conf)}</span>'


def main() -> int:
    desk = load(DATA / "desk.json")
    preds = load(DATA / "predictions.json")
    flags = load(DATA / "flagged.json")
    review = load(DATA / "review.json")
    olbgd = load(DATA / "olbg.json")
    verification = load(DATA / "verification.json", {})
    man = load(CAP / "manifest.json")
    rows = desk["rows"]
    by_sport = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)
    pred_by_sport = defaultdict(list)
    for p in preds.get("predictions", []):
        pred_by_sport[p["sport"]].append(p)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    (OUT / "assets/style.css").write_text(CSS)

    markets_total = sum(len(r["markets"]) for r in rows)
    selections_total = sum(len(m["selections"]) for r in rows for m in r["markets"])
    high_picks = sum(1 for r in rows if r["pick"]["confidence"] == "High")
    high_window = sum(1 for r in rows if r["pick"]["confidence"] == "High" and r["pick"]["in_window_fair"])
    pred_high = sum(1 for p in preds.get("predictions", []) if p["confidence"] == "High")
    pred_med = sum(1 for p in preds.get("predictions", []) if p["confidence"] == "Medium")
    pred_low = sum(1 for p in preds.get("predictions", []) if p["confidence"] == "Low")

    # ---------------------------------------------------------------- index
    sport_rows = ""
    for sport, slug, comp in SPORTS:
        n = len(by_sport.get(sport, []))
        pn = len(pred_by_sport.get(sport, []))
        band = sum(len(r["high_candidates"]) for r in by_sport.get(sport, []))
        status = ("covered" if n and pn else ("fixtures only" if n else "not covered today"))
        sport_rows += (f"<tr><td><a href='sports/{slug}.html'>{esc(sport)}</a></td><td>{esc(comp)}</td>"
                       f"<td>{n}</td><td>{band}</td><td>{pn}</td><td>{esc(status)}</td></tr>")
    top = sorted(preds.get("predictions", []), key=lambda p: -p["prob"])[:8]
    top_cards = "".join(
        f"""<div class="card pick"><div class="kv"><span>{esc(p['sport'])}</span>
        <span>{esc(p['start_utc'][:16].replace('T', ' '))} UTC</span>{tag(p['confidence'])}</div>
        <h3>{esc(p['selection'])}</h3><div class="small">{esc(p['matchup'])} · {esc(p['competition'])}</div>
        <p>{esc(p['text'])}</p><div class="kv"><span>Model probability {p['prob']*100:.1f}%</span>
        <span>Our price {p['fair_decimal']} ({p['fair_american']:+d})</span>
        <a href="{esc(p['official_url'])}" rel="noopener">official source ↗</a></div></div>"""
        for p in top)
    index_body = f"""
<h1>Verified fixtures, our own lines, and human predictions</h1>
<p class="lead">Board AF re-read the official league and governing-body feeds on 22 October 2026 and built a desk for
the 23–31 October window across the sports in scope on OLBG. No bookmaker or OLBG price is an input: every number
below is originated from official season data, and every row links to the page it came from.</p>
<div class="grid">
<div class="card"><div class="n">{len(rows)}</div><div class="k">verified fixtures</div></div>
<div class="card"><div class="n">{markets_total:,}</div><div class="k">originated markets</div></div>
<div class="card"><div class="n">{selections_total:,}</div><div class="k">priced selections</div></div>
<div class="card"><div class="n">{len(preds.get('predictions', []))}</div><div class="k">written predictions</div></div>
<div class="card"><div class="n">{high_picks}</div><div class="k">High-confidence match picks</div></div>
<div class="card"><div class="n">{len(flags.get('items', []))}</div><div class="k">items flagged for review</div></div>
</div>
<div class="note"><b>The odds arithmetic, stated up front.</b> −250 is a decimal 1.400, i.e. a 71.43% implied chance.
A pick that is both “&gt;70% to win” and “no shorter than −250” therefore has to sit in a very narrow band
(70.00%–71.43%, fair 1.4000–1.4286). Board AF publishes the 70%+ picks it finds even when they are shorter than
−250, and builds the five-per-sport prediction set from the highest-probability selections that do land inside
−250 … +10,000. Today that is <b>{pred_high} High</b>, {pred_med} Medium and {pred_low} Low among the
{len(preds.get('predictions', []))} written predictions. <a href="methodology.html">Full method →</a></div>
<h2>Coverage by sport</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Competition priced</th><th>Fixtures verified</th>
<th>In-window High candidates</th><th>Predictions</th><th>Status</th></tr></thead><tbody>{sport_rows}</tbody></table></div>
<p class="small">“In-window High candidates” counts selections at 70.00–71.43% model probability — the only overlap of
the two requested rules. Sports marked <i>not covered today</i> have no verified official fixture/ranking feed in this
capture; they are listed on the <a href="flagged.html">Flagged for Review</a> page with the reason, and nothing is guessed.</p>
<h2>Highest-probability written predictions</h2>
<div class="grid">{top_cards}</div>
<p><a href="picks.html">All {len(preds.get('predictions', []))} predictions →</a></p>
<h2>What was checked</h2>
<ul class="tight">
<li>{man.get('http_200_nonempty_count')} of {man.get('target_count')} official requests returned content; the rest are
listed with their HTTP status on the <a href="sources.html">Sources</a> page and none of them is the source of a published number.</li>
<li>{review.get('rows_reviewed', 0)} rows of the shared <code>data/master.json</code> were reviewed line by line;
{review.get('cross_check', [{}])[0].get('fixtures_compared', 0)} in-window NHL/MLB/EuroLeague fixtures were compared with the
official capture and <b>{review.get('cross_check', [{}])[0].get('mismatches', 0)} mismatches</b> were found.
<a href="review.html">Review register →</a></li>
<li>Every prediction is at least 30 words, written for one selection, and quotes only figures that exist in the official
inputs printed under it. <a href="verification.html">Verification report →</a></li>
</ul>
"""
    (OUT / "index.html").write_text(page("Dashboard", index_body, "index.html"))

    # ---------------------------------------------------------------- entries
    trs = ""
    for r in rows:
        p = r["pick"]
        trs += (f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}</td><td>{esc(r['sport'])}</td>"
                f"<td>{esc(r['competition'])}</td><td>{esc(r['side_a'])} vs {esc(r['side_b'])}</td>"
                f"<td>{esc(p['selection'])}</td><td>{tag(p['confidence'])}</td>"
                f"<td>{p['prob']*100:.1f}%</td><td>{p['fair_decimal']} ({p['fair_american']:+d})</td>"
                f"<td>{len(r['markets'])}</td>"
                f"<td><a href='{esc(r['official_url'])}' rel='noopener'>official</a></td></tr>")
    entries_body = f"""
<h1>All verified fixtures</h1>
<p class="lead">{len(rows)} fixtures dated {esc(desk['cutoff_utc'])} to {esc(desk['horizon_utc'])}, every one read from an
official league or governing-body feed in the committed capture. The pick column is the match-winner selection our model
makes favourite; the price is our own fair line (0% margin).</p>
<div class="scroll"><table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Competition</th><th>Fixture</th>
<th>Match-winner pick</th><th>Confidence</th><th>Model probability</th><th>Our fair price</th><th>Markets</th>
<th>Source</th></tr></thead><tbody>{trs}</tbody></table></div>
<p class="small">Confidence rule: High at ≥70.0%, Medium 55.0–69.9%, Low below 55.0%, with a sample cap (a side with fewer
than 5 official games cannot be High). Full market ladders — match winner, handicap/spread/puck/run line, match total and
team totals — are in <a href="../data/session-2d25cf78/desk.json">desk.json</a>.</p>
"""
    (OUT / "entries.html").write_text(page("All fixtures", entries_body, "entries.html"))

    # ---------------------------------------------------------------- picks
    cards = ""
    for sport, _, _ in SPORTS:
        ps = pred_by_sport.get(sport)
        if not ps:
            continue
        cards += f"<h2>{esc(sport)}</h2>"
        for p in ps:
            inputs = "".join(f"<li>{esc(i)}</li>" for i in p["official_inputs"][:3])
            cards += f"""<div class="card pick"><div class="kv"><span>{esc(p['competition'])}</span>
            <span>{esc(p['start_utc'][:16].replace('T',' '))} UTC</span><span>{esc(p['venue']) or 'venue not published'}</span>
            {tag(p['confidence'])}</div>
            <h3>{esc(p['selection'])} <span class="small">— {esc(p['matchup'])}</span></h3>
            <p>{esc(p['text'])}</p>
            <div class="kv"><span>Market: {esc(p['market'])}</span><span>Model probability {p['prob']*100:.1f}%</span>
            <span>Our price {p['fair_decimal']} ({p['fair_american']:+d})</span><span>{p['word_count']} words</span>
            <a href="{esc(p['official_url'])}" rel="noopener">{esc(p['official_source_name'])} ↗</a></div>
            <ul class="tight small">{inputs}</ul></div>"""
    picks_body = f"""
<h1>Written predictions</h1>
<p class="lead">Five per covered sport, each tied to one selection inside the requested −250 … +10,000 window. Every
figure quoted in the text appears in the official inputs printed under the card, and each card links to the page the
inputs came from. The confidence badge is the model’s own label — {pred_high} High, {pred_med} Medium, {pred_low} Low —
not a claim that every pick clears 70%.</p>
{cards}
"""
    (OUT / "picks.html").write_text(page("Predictions", picks_body, "picks.html"))

    # ---------------------------------------------------------------- sports pages
    for sport, slug, comp in SPORTS:
        rs = by_sport.get(sport, [])
        ps = pred_by_sport.get(sport, [])
        head = f"<h1>{esc(sport)}</h1><p class='lead'>{len(rs)} verified fixtures, {len(ps)} written predictions."
        if comp:
            head += f" Competition priced: {esc(comp)}."
        head += "</p>"
        if not rs:
            body = head + (
                "<div class='note warnnote'><b>No verified fixture feed for this sport in the Board AF capture.</b> "
                "The official page was either client-rendered without a readable payload, blocked (HTTP 403/404), or did "
                "not publish a head-to-head line-up before the cut-off. Nothing has been guessed or filled in. See the "
                "<a href='../flagged.html'>Flagged for Review</a> page and the <a href='../sources.html'>Sources</a> page "
                "for the exact URLs and HTTP statuses.</div>")
            (OUT / f"sports/{slug}.html").write_text(page(sport, body, "", prefix="../"))
            continue
        trs = ""
        for r in rs:
            p = r["pick"]
            trs += (f"<tr><td>{esc(r['start_utc'][:16].replace('T',' '))}</td><td>{esc(r['competition'])}</td>"
                    f"<td>{esc(r['side_a'])} vs {esc(r['side_b'])}</td><td>{esc(p['selection'])}</td>"
                    f"<td>{tag(p['confidence'])}</td><td>{p['prob']*100:.1f}%</td>"
                    f"<td>{p['fair_decimal']} ({p['fair_american']:+d})</td>"
                    f"<td><a href='{esc(r['official_url'])}' rel='noopener'>official</a></td></tr>")
        pcards = ""
        for p in ps:
            pcards += f"""<div class="card pick"><div class="kv">{tag(p['confidence'])}
            <span>{esc(p['matchup'])}</span><span>{p['prob']*100:.1f}% at {p['fair_decimal']}</span></div>
            <h3>{esc(p['selection'])}</h3><p>{esc(p['text'])}</p>
            <div class="kv"><a href="{esc(p['official_url'])}" rel="noopener">official source ↗</a></div></div>"""
        body = head + f"""
<div class="scroll"><table><thead><tr><th>Start (UTC)</th><th>Competition</th><th>Fixture</th><th>Pick</th>
<th>Confidence</th><th>Model probability</th><th>Our fair price</th><th>Source</th></tr></thead><tbody>{trs}</tbody></table></div>
<h2>Predictions</h2>{pcards or '<p class="small">No written prediction for this sport today.</p>'}
<p><a href="../picks.html">All predictions</a> · <a href="../entries.html">All fixtures</a></p>
"""
        (OUT / f"sports/{slug}.html").write_text(page(sport, body, "", prefix="../"))

    # ---------------------------------------------------------------- markets
    mk = Counter()
    per = defaultdict(Counter)
    for r in rows:
        for m in r["markets"]:
            mk[m["market"].split(" ")[0] + (" " + m["market"].split(" ")[1] if len(m["market"].split(" ")) > 1 else "")] += 1
            per[r["sport"]][m["market"].split(" ")[0]] += 1
    market_rows = "".join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k, v in mk.most_common(20))
    per_rows = ""
    for sport, _, _ in SPORTS:
        if not by_sport.get(sport):
            continue
        c = per[sport]
        per_rows += (f"<tr><td>{esc(sport)}</td><td>{len(by_sport[sport])}</td>"
                     f"<td>{sum(len(r['markets']) for r in by_sport[sport])}</td>"
                     f"<td>{c.get('Match', 0)}</td><td>{c.get('Handicap', 0) + c.get('Puck', 0) + c.get('Run', 0) + c.get('Set', 0)}</td>"
                     f"<td>{c.get('Total', 0)}</td><td>{c.get('Team', 0)}</td></tr>")
    markets_body = f"""
<h1>Markets investigated</h1>
<p class="lead">Every fixture carries the markets the official inputs actually support: match winner, a handicap or
spread ladder, a match-total ladder, and team totals. No market is priced without an official input behind it, and no
bookmaker price is used anywhere.</p>
<div class="grid">
<div class="card"><div class="n">{markets_total:,}</div><div class="k">markets originated</div></div>
<div class="card"><div class="n">{selections_total:,}</div><div class="k">priced selections</div></div>
<div class="card"><div class="n">{len(mk)}</div><div class="k">distinct market families</div></div>
</div>
<h2>By market family</h2>
<div class="scroll"><table><thead><tr><th>Market family</th><th>Markets originated</th></tr></thead>
<tbody>{market_rows}</tbody></table></div>
<h2>By sport</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Fixtures</th><th>Markets</th><th>Match winner</th>
<th>Handicap / spread</th><th>Match total</th><th>Team totals</th></tr></thead><tbody>{per_rows}</tbody></table></div>
<div class="note"><b>How a price is made.</b> Team sport probabilities come from official season scoring rates shrunk
toward the league average (empirical Bayes), blended with the official win-percentage record where the sport’s points
model alone would overrate a small sample. Hockey, baseball and handball use a Poisson goal/run model; basketball and
rugby use a normal margin model. The published line is the fair price (1 ÷ probability); our book line adds a stated
overround carried on the opposing selection. <a href="methodology.html">Method and parameters →</a></div>
"""
    (OUT / "markets.html").write_text(page("Markets", markets_body, "markets.html"))

    # ---------------------------------------------------------------- coverage
    cov_rows = ""
    olbg_by_sport = {s["sport"]: s for s in olbgd.get("per_sport", [])}
    for sport, slug, comp in SPORTS:
        n = len(by_sport.get(sport, []))
        pn = len(pred_by_sport.get(sport, []))
        o = olbg_by_sport.get(sport, {})
        listed = o.get("olbg_events_listed", "")
        status = ("Covered" if n and pn else ("Fixtures verified, no prediction" if n else "Not covered today"))
        cov_rows += (f"<tr><td><a href='sports/{slug}.html'>{esc(sport)}</a></td><td>{esc(comp) or '—'}</td>"
                     f"<td>{n}</td><td>{pn}</td><td>{listed}</td><td>{esc(status)}</td>"
                     f"<td>{esc(o.get('page_url', 'https://www.olbg.com/betting-tips'))}</td></tr>")
    excluded_rows = "".join(f"<tr><td>{esc(x)}</td><td>Excluded by the brief — not collected.</td></tr>" for x in EXCLUDED)
    coverage_body = f"""
<h1>Coverage</h1>
<p class="lead">OLBG’s live taxonomy was re-read from its sitemap and sport landing pages on 22 October 2026. Nineteen
sports are in scope; six have verified official fixtures and written predictions today, and the rest are published as
gaps rather than guesses.</p>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Competition priced</th><th>Verified fixtures</th>
<th>Predictions</th><th>Events listed on OLBG</th><th>Status</th><th>OLBG page</th></tr></thead>
<tbody>{cov_rows}</tbody></table></div>
<h2>Excluded by the brief</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>Status</th></tr></thead><tbody>{excluded_rows}</tbody></table></div>
<p class="small">Scope note: Gaelic Football is <b>in</b> scope — the brief excludes football (soccer) and American
football, not Gaelic football. Board AF did not capture a GAA fixture feed in this run, so it is listed as a gap.</p>
"""
    (OUT / "coverage.html").write_text(page("Coverage", coverage_body, "coverage.html"))

    # ---------------------------------------------------------------- OLBG page
    olbg_rows = ""
    for s in olbgd.get("per_sport", []):
        olbg_rows += (f"<tr><td>{esc(s['sport'])}</td><td>{s.get('olbg_events_listed','—')}</td>"
                      f"<td>{s.get('desk_fixtures','—')}</td><td>{s.get('desk_fixtures_also_on_olbg','—')}</td>"
                      f"<td>{s.get('on_olbg_not_in_desk','—')}</td>"
                      f"<td>{esc('; '.join(s.get('olbg_competitions', [])) or '—')}</td></tr>")
    tax_rows = "".join(
        f"<tr><td>{esc(t['sport'])}</td><td>{t['olbg_id']}</td>"
        f"<td>{'excluded' if t['excluded'] else 'in scope'}</td>"
        f"<td><a href='{esc(t['url'])}' rel='noopener'>landing page</a></td></tr>"
        for t in olbgd.get("sports_taxonomy", []))
    olbg_body = f"""
<h1>OLBG reverse-engineering</h1>
<p class="lead">How OLBG is structured, read from its own sitemap and server-rendered sport pages on 22 October 2026
(capture {esc(olbgd.get('capture_started_utc',''))}, SHA-256 manifest committed), and how that inventory compares with
the fixtures we verified on the governing bodies’ pages.</p>
<h2>Structure</h2>
<ul class="tight">
<li><b>Sport landing page:</b> <code>/betting-tips/&lt;Sport&gt;/&lt;sport_id&gt;</code></li>
<li><b>Competition hub:</b> <code>/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;sport_id&gt;</code></li>
<li><b>Event page:</b> <code>/betting-tips/&lt;Sport&gt;/&lt;Category&gt;/&lt;Competition&gt;/&lt;Event&gt;/&lt;sport_id&gt;?event_id=&lt;id&gt;</code></li>
</ul>
<h2>Sport taxonomy</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>OLBG id</th><th>Scope</th><th>Page</th></tr></thead>
<tbody>{tax_rows}</tbody></table></div>
<h2>Inventory comparison</h2>
<div class="scroll"><table><thead><tr><th>Sport</th><th>OLBG events listed</th><th>Our verified fixtures</th>
<th>Both</th><th>OLBG-only</th><th>Competitions OLBG lists</th></tr></thead><tbody>{olbg_rows}</tbody></table></div>
<div class="note warnnote"><b>What the comparison shows.</b> The two inventories are not the same thing. OLBG’s landing
pages lean on domestic competitions (Pro D2 rugby, French handball, domestic volleyball) while our desk prices the
elite competitions with a machine-readable official feed (NHL, EuroLeague, Top 14, EHF Champions League). Where OLBG lists
an event we could not verify, we publish the gap instead of copying their row — the whole point is that our line is ours.</div>
<p class="small">OLBG pages were requested politely (≥1.2 s between requests, robots.txt disallow-prefixes never
requested). The capture manifest on the <a href="sources.html">Sources</a> page carries the SHA-256 of every response.</p>
"""
    (OUT / "olbg.html").write_text(page("OLBG", olbg_body, "olbg.html"))

    # ---------------------------------------------------------------- review
    cats = review.get("category_counts", {})
    cat_rows = "".join(f"<tr><td>{esc(k)}</td><td>{v}</td></tr>" for k, v in sorted(cats.items(), key=lambda kv: -kv[1]))
    find_rows = ""
    for f in review.get("findings", [])[:400]:
        r = f.get("row") or {}
        sev = {"error": "err", "warning": "medium", "info": "info"}.get(f.get("severity"), "info")
        src = f.get("source_url")
        src_cell = ('<a href="' + esc(src) + '" rel="noopener">source</a>') if src else "—"
        find_rows += ("<tr><td><span class='tag " + sev + "'>" + esc(f.get("severity")) + "</span></td>"
                      "<td>" + esc(f.get("category")) + "</td><td>" + esc(r.get("sport", "")) + "</td>"
                      "<td>" + esc(r.get("date", "")) + "</td><td>" + esc(r.get("home", "")) + " vs " +
                      esc(r.get("away", "")) + "</td><td>" + esc(f.get("detail")) + "</td>"
                      "<td>" + src_cell + "</td></tr>")
    peer_rows = "".join(f"<tr><td>{esc(p['file'])}</td><td>{p['rows']}</td><td>{p['rows_without_source']}</td></tr>"
                        for p in review.get("peer_desks", [])[:20])
    xc = (review.get("cross_check") or [{}])[0]
    review_body = f"""
<h1>Line-by-line review of the shared data</h1>
<p class="lead">{review.get('rows_reviewed', 0)} rows of <code>data/master.json</code> were checked row by row on
{esc(review.get('generated_utc',''))}. Nothing in that file is edited by this session; the findings below are advisory
and each one points at the row and, where available, the official page.</p>
<div class="grid">
<div class="card"><div class="n">{review.get('rows_reviewed', 0)}</div><div class="k">rows reviewed</div></div>
<div class="card"><div class="n">{len(review.get('findings', []))}</div><div class="k">findings</div></div>
<div class="card"><div class="n">{xc.get('fixtures_compared', 0)}</div><div class="k">fixtures re-checked against official capture</div></div>
<div class="card"><div class="n">{xc.get('mismatches', 0)}</div><div class="k">official mismatches found</div></div>
<div class="card"><div class="n">{xc.get('skipped_outside_capture_window', 0)}</div><div class="k">rows outside the capture window</div></div>
</div>
<div class="note"><b>Result of the official cross-check.</b> Every in-window NHL, MLB and EuroLeague row in
<code>master.json</code> ({xc.get('fixtures_compared', 0)} fixtures) matches a fixture in the committed official capture
— <b>{xc.get('mismatches', 0)} mismatches</b>. The remaining findings are about record quality, not wrong fixtures:
stale dates, missing sources, placeholder rows and prices published while unverified.</div>
<h2>Findings by category</h2>
<div class="scroll"><table><thead><tr><th>Category</th><th>Count</th></tr></thead><tbody>{cat_rows}</tbody></table></div>
<h2>Findings</h2>
<div class="scroll"><table><thead><tr><th>Severity</th><th>Category</th><th>Sport</th><th>Date</th><th>Row</th>
<th>Detail</th><th>Source</th></tr></thead><tbody>{find_rows}</tbody></table></div>
<h2>Peer desks inventoried</h2>
<div class="scroll"><table><thead><tr><th>File</th><th>Rows</th><th>Rows without a source URL</th></tr></thead>
<tbody>{peer_rows}</tbody></table></div>
"""
    (OUT / "review.html").write_text(page("Repo review", review_body, "review.html"))

    # ---------------------------------------------------------------- flagged
    flag_cards = ""
    for f in flags.get("items", []):
        sev = "err" if f["severity"] == "needs review" else ("medium" if f["severity"] == "warning" else "info")
        flag_cards += f"""<div class="card"><div class="kv"><span class="tag {sev}">{esc(f['severity'])}</span>
        <span>{esc(f['id'])}</span><span>{esc(f['area'])}</span></div><h3>{esc(f['title'])}</h3>
        <p>{esc(f['detail'])}</p>
        <div class="kv"><a href="{esc(f['source_url'])}" rel="noopener">source ↗</a></div></div>"""
    flagged_body = f"""
<h1>Flagged for Review</h1>
<p class="lead">Everything Board AF could not fully verify, plus the disclosures a reader needs to judge the desk. None
of these items blocks publication; each has the source link a reviewer needs to check it.</p>
{flag_cards}
"""
    (OUT / "flagged.html").write_text(page("Flagged for review", flagged_body, "flagged.html"))

    # ---------------------------------------------------------------- methodology
    method_body = f"""
<h1>Method</h1>
<p class="lead">The desk is reproducible end to end from committed bytes: capture → model → lines → picks → predictions →
verification. No price from OLBG or any bookmaker is an input.</p>
<h2>1 · Capture</h2>
<p>Official pages are fetched by an open-egress GitHub Actions runner (<code>.github/workflows/capture-2d25cf78.yml</code>)
and committed gzip-compressed with a SHA-256 manifest. <code>scripts/session-2d25cf78/fetch.py</code> enforces polite
spacing per host and never requests a robots.txt-disallowed OLBG path. {man.get('http_200_nonempty_count')} of
{man.get('target_count')} requests returned content.</p>
<h2>2 · Model</h2>
<ul class="tight">
<li><b>Team sports:</b> attack and defence rates from the official season scoring columns, shrunk toward the league
average with an empirical-Bayes weight k (8 for NHL, 30 for MLB, 6 for EuroLeague, 4 for Top 14 and the EHF).</li>
<li><b>Blend:</b> Top 14 and EHF also use the official win-percentage record (log5, home odds edge 1.10), averaged 50/50
with the scoring model, so a 0-6 team cannot be made favourite by heavy shrinkage alone.</li>
<li><b>Distributions:</b> Poisson for goals/runs (NHL, MLB, EHF totals); normal margin for basketball and rugby; a
set-based model for volleyball.</li>
<li><b>Home advantage:</b> a disclosed model parameter (+3% goals NHL, +2% runs MLB, +2% points EuroLeague, +3 points
margin Top 14, +2% EHF), not a data value.</li>
<li><b>Rankings-based sports</b> (none published today) would use official ranking points; no ranking feed verified in
this run, so no such lines are published.</li>
</ul>
<h2>3 · Lines and confidence</h2>
<p>Our published line is the fair price, 1 ÷ model probability. Our book line adds a 2% overround carried on the opposing
selection, so the side we put up keeps its fair price. Confidence: <b>High</b> at ≥70.0%, <b>Medium</b> at 55.0–69.9%,
<b>Low</b> below 55.0%; a side with fewer than the sport’s required official games cannot be labelled High.</p>
<h2>4 · The −250 … +10,000 window</h2>
<p>−250 is decimal 1.400 (71.43%). +10,000 is decimal 101.0 (0.99%). A selection that is both “&gt;70% to win” and “no
shorter than −250” must therefore have a model probability of 0.7000–0.7143. Board AF does not hide the arithmetic: it
publishes every 70%+ match-winner pick (including those shorter than −250, labelled as such) and builds the five
predictions per sport from the highest-probability selections that do sit inside the window.</p>
<h2>5 · Predictions</h2>
<p>Each prediction is written for one selection, is ≥30 words, names the teams/players, quotes only figures printed in the
row’s official inputs, states the selection plainly, and carries the official source link. Word counts, uniqueness and
figure traceability are re-checked by <code>verify.py</code>.</p>
<h2>6 · What is deliberately blank</h2>
<p>No value is inferred. Where an official input does not exist — a probable pitcher not yet published, a start time not
confirmed, a fixture only available on a client-rendered page — the row is either unpriced or published with a flag on the
<a href="flagged.html">Flagged for Review</a> page.</p>
"""
    (OUT / "methodology.html").write_text(page("Method", method_body, "methodology.html"))

    # ---------------------------------------------------------------- sources
    src_rows = ""
    for f in man.get("files", []):
        src_rows += (f"<tr><td>{esc(f['id'])}</td><td><a href='{esc(f['url'])}' rel='noopener'>{esc(f['url'])}</a></td>"
                     f"<td>{esc(f.get('status'))}</td><td>{f.get('bytes', 0):,}</td>"
                     f"<td><code>{esc((f.get('sha256') or '')[:16])}…</code></td><td>{esc(f.get('fetched_utc',''))}</td>"
                     f"<td class='small'>{esc(f.get('error',''))}</td></tr>")
    sources_body = f"""
<h1>Sources</h1>
<p class="lead">Every response used by this desk, with HTTP status, byte count, SHA-256 and the committed raw file. Capture
started {esc(man.get('started_utc',''))}; {man.get('http_200_nonempty_count')} of {man.get('target_count')} returned
content. The manifest itself is <a href="../data/session-2d25cf78/capture/{esc(CAP.name)}/manifest.json">here</a>.</p>
<div class="scroll"><table><thead><tr><th>Id</th><th>URL</th><th>HTTP</th><th>Bytes</th><th>SHA-256</th>
<th>Fetched (UTC)</th><th>Error</th></tr></thead><tbody>{src_rows}</tbody></table></div>
"""
    (OUT / "sources.html").write_text(page("Sources", sources_body, "sources.html"))

    # ---------------------------------------------------------------- verification
    checks = verification.get("checks", [])
    ok = sum(1 for c in checks if c.get("ok"))
    vrows = "".join(f"<tr><td>{esc(c['name'])}</td><td>{'PASS' if c.get('ok') else 'FAIL'}</td>"
                    f"<td>{esc(c.get('detail',''))}</td></tr>" for c in checks[:400])
    verif_body = f"""
<h1>Verification</h1>
<p class="lead">{len(checks)} deterministic checks over the desk, the predictions, the site links and the capture manifest.
Result: <b>{ok}/{len(checks)} pass</b>, {len(checks)-ok} failures. Reproduce with
<code>python3 scripts/session-2d25cf78/verify.py</code>.</p>
<div class="scroll"><table><thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead><tbody>{vrows}</tbody></table></div>
<p class="small">The gate covers: every row has an official URL; fair price = 1 ÷ probability; American odds re-derived;
confidence follows the published rule and the sample cap; in-window flags match the arithmetic; high-candidate band
membership; prediction length ≥30 words, uniqueness, explicit selection and figure traceability to the row’s official
inputs; every internal link resolves; every raw file named in the manifest exists and re-hashes.</p>
"""
    (OUT / "verification.html").write_text(page("Verification", verif_body, "verification.html"))

    # copy machine-readable data next to the site for reviewers
    for name in ("desk.json", "predictions.json", "flagged.json", "review.json", "olbg.json"):
        shutil.copyfile(DATA / name, OUT / name)
    print("built", len(list(OUT.glob('*.html'))) + len(list((OUT / 'sports').glob('*.html'))), "pages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

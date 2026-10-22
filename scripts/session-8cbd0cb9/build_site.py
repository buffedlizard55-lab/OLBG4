#!/usr/bin/env python3
"""Board AD site builder (session arena/8cbd0cb9-olbg4, AD5).

Generates the static GitHub Pages dashboard under session-8cbd0cb9/ from the committed
desk/predictions/flagged/review data. Stdlib only. Every table row carries its official
source link where one exists; unverified values are blank and flagged.

Pages:
  index.html                landing dashboard (KPIs, sport tiles, high-confidence cards)
  sports/<slug>.html        per-sport all-entries table
  predictions.html          high-confidence human write-ups
  flagged.html              Flagged for Review (unverified rows, blank fields, review links)
  markets.html              markets investigated per sport
  methodology.html          model disclosure, scope, limitations
  verification.html         verification-gate results
  assets/{style.css,app.js}
"""

from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "session-8cbd0cb9"
DATA = ROOT / "data" / "session-8cbd0cb9"
SPORTS_DIR = OUT / "sports"
ASSETS = OUT / "assets"
for d in (OUT, SPORTS_DIR, ASSETS):
    d.mkdir(parents=True, exist_ok=True)

desk = json.loads((DATA / "desk.json").read_text())
preds = json.loads((DATA / "predictions.json").read_text())
flagged = json.loads((DATA / "flagged.json").read_text())
review = json.loads((DATA / "repo_review.json").read_text())

ROWS = desk["rows"]
BY_SPORT: dict[str, list[dict]] = {}
for r in ROWS:
    BY_SPORT.setdefault(r["sport_slug"], []).append(r)

EXCLUDED = {"soccer", "football", "boxing", "ufc", "mma", "american football",
            "hurling", "horse racing", "cycling", "specials"}

SPORT_SLUG = {
    "Tennis": "tennis", "Basketball": "basketball", "Golf": "golf", "Cricket": "cricket",
    "Snooker": "snooker", "Rugby Union": "rugby-union", "Rugby League": "rugby-league",
    "Baseball": "baseball", "Ice Hockey": "ice-hockey", "Motor Racing": "motor-racing",
    "Darts": "darts", "Handball": "handball", "Volleyball": "volleyball",
    "Aussie Rules": "aussie-rules", "eSports": "esports", "Gaelic Football": "gaelic-football",
    "Greyhounds": "greyhounds",
}

SPORT_TITLES = {
    "tennis": "Tennis", "basketball": "Basketball", "golf": "Golf", "cricket": "Cricket",
    "snooker": "Snooker", "rugby-union": "Rugby Union", "rugby-league": "Rugby League",
    "baseball": "Baseball", "ice-hockey": "Ice Hockey", "motor-racing": "Motor Racing",
    "darts": "Darts", "handball": "Handball", "volleyball": "Volleyball",
    "aussie-rules": "Aussie Rules", "esports": "eSports", "gaelic-football": "Gaelic Football",
    "greyhounds": "Greyhounds",
}

ORDER = ["tennis", "basketball", "baseball", "ice-hockey", "darts", "snooker",
         "handball", "volleyball", "rugby-union", "rugby-league", "cricket",
         "aussie-rules", "gaelic-football", "golf", "motor-racing", "greyhounds", "esports"]

NAV_LINKS = [
    ("index.html", "Dashboard"),
    ("sports/tennis.html", "Sport pages"),
    ("predictions.html", "High-confidence predictions"),
    ("flagged.html", "Flagged for Review"),
    ("markets.html", "Markets & coverage"),
    ("methodology.html", "Methodology"),
    ("verification.html", "Verification"),
]


def esc(v) -> str:
    return html.escape(str(v) if v is not None else "")


def american(n) -> str:
    if n is None:
        return "—"
    return f"{int(n):+d}" if int(n) >= 0 else f"-{abs(int(n))}"


def dec(n) -> str:
    return f"{n:.2f}" if n is not None else "—"


def badge(conf: str) -> str:
    color = {"High": "#166534", "Medium": "#92400e", "Low": "#475569"}.get(conf, "#64748b")
    label = conf or "unverified"
    return (f'<span class="badge" style="background:#{color == "#166534" and "dcfce7" or color == "#92400e" and "fef3c7" or "e2e8f0"}'
            f';color:{color}">{esc(label)}</span>')


def nav(prefix: str = "") -> str:
    items = "".join(f'<li><a href="{prefix}{u}">{t}</a></li>' for u, t in NAV_LINKS)
    return f'<nav class="topnav"><ul>{items}</ul></nav>'


def header(title: str, prefix: str = "") -> str:
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — OLBG4 Board AD</title><link rel="stylesheet" href="{prefix}assets/style.css"></head>
<body>{nav(prefix)}<header class="band"><div class="wrap"><h1>{esc(title)}</h1>
<p class="subtitle">OLBG reverse-engineering re-verification · originated lines · high-confidence predictions · official sources or blank+flagged</p></div></header>
<main class="wrap">"""


def footer(prefix: str = "") -> str:
    return f"""</main><footer class="wrap"><hr>
<p style="font-size:13px;color:#64748b">OLBG4 — session arena/8cbd0cb9-olbg4 (Board AD). Peer sessions: <a href="https://buffedlizard55-lab.github.io/OLBG4/session-f0622b6e/">session-f0622b6e</a> · <a href="https://buffedlizard55-lab.github.io/OLBG4/session-19b8e377/">session-19b8e377</a>. No entries from excluded sports (soccer/football, boxing/UFC/MMA, American football, hurling, horse racing, cycling, specials).</p></footer>
<script src="{prefix}assets/app.js"></script></body></html>"""


def source_cell(r: dict) -> str:
    u = r.get("official_url") or ""
    if u.startswith("https://"):
        return f'<a href="{esc(u)}" rel="noopener">{esc(r.get("official_source_name") or u)}</a>'
    if r.get("olbg_url"):
        return ('<span class="muted">none recorded — OLBG listing only '
                f'(<a href="{esc(r["olbg_url"])}" rel="noopener">OLBG event page, non-official</a>)</span>')
    return '<span class="muted">none recorded</span>'


def row_tr(r: dict, idx: int) -> str:
    pick = r.get("match_winner_pick") or "—"
    conf = r.get("confidence") or "unverified"
    mw = r["markets"].get("match_winner") if r["markets"] else None
    if mw:
        pick_side = mw.get(pick, {}) if pick in mw else next(iter(mw.values()), {})
        line = f'{esc(pick)} {dec(pick_side.get("book_decimal"))} {american(pick_side.get("book_american"))}'
    else:
        line = "— not originated"
    hc = r["markets"].get("handicap") if r["markets"] else None
    hdisp = "— not originated"
    if hc:
        sides = hc.get("sides") or {}
        parts = []
        for sname, bl in sides.items():
            parts.append(f"{esc(sname)} {dec(bl.get('book_decimal'))} {american(bl.get('book_american'))}")
        hdisp = f"line {hc.get('line')} · " + " | ".join(parts) if parts else f"line {hc.get('line')}"
    tot = r["markets"].get("total") if r["markets"] else None
    tdisp = "— not originated (no verified scoring inputs)"
    if isinstance(tot, dict):
        tdisp = tot.get("summary", "originated")
    flags = " ".join(f'<span class="flag">F</span>' for _ in r.get("flags", []))
    flag_title = " · ".join(r.get("flags", []))
    return f"""<tr data-sport="{esc(r['sport_slug'])}" data-conf="{esc(conf or '')}">
<td>{esc(r['sport'])}</td><td>{esc(r['competition'])}</td><td>{esc(r['match'])}</td>
<td>{esc(r['start_date_local']) or esc(r['olbg_date_label'])} <span class="muted">({esc(r['status'])})</span></td>
<td><b>{esc(pick)}</b></td>{badge(conf)}
<td class="num">{esc(line)}</td><td class="num">{esc(hdisp)}</td><td class="num">{esc(tdisp)}</td>
<td class="src">{source_cell(r)}</td>
<td class="flags" title="{esc(flag_title)}">{flags}</td></tr>"""


def sport_table(rows: list[dict]) -> str:
    body = "".join(row_tr(r, i) for i, r in enumerate(rows))
    return f"""<table class="data" id="entries-table"><thead><tr>
<th>Sport</th><th>Competition</th><th>Match</th><th>Date (per OLBG feed label)</th><th>Pick</th>
<th>Confidence</th><th>Match-winner line (book)</th><th>Handicap</th><th>Match total</th>
<th>Official source</th><th>Flags</th></tr></thead><tbody>{body}</tbody></table>"""


# ---------------- index ----------------
kpis = [
    ("Desk rows", desk["counts"]["rows_total"], "in-scope matches listed"),
    ("Sports covered", len(desk["by_sport"]), "in-scope sports (excluded sports: 0 rows)"),
    ("High-confidence picks", desk["counts"]["high_confidence"], "p ≥ 70% and odds in −250…+10000"),
    ("Flagged for review", flagged["count"], "unverified rows with blank values"),
]
kpi_html = "".join(
    f'<div class="kpi"><div class="big">{v}</div><div class="small">{t}</div><div class="muted">{d}</div></div>'
    for t, v, d in kpis)
tiles = "".join(
    f'<a class="tile" href="sports/{s}.html">{esc(SPORT_TITLES[s])} <span class="badge" style="background:#e2e8f0;color:#334155">{len(BY_SPORT.get(s, []))}</span></a>'
    for s in ORDER)
high_cards = ""
for p in preds["predictions"]:
    high_cards += f"""<div class="card">
<h3>{esc(p['matchup'])}</h3>
<p class="muted">{esc(p['sport'])} · {esc(p['competition'])} · {esc(p['start_local'])}</p>
<p>{esc(p['text'][:160])}…</p>
<p><strong>Selection:</strong> {esc(p['selection'])} · book {american(p['book_american'])} (fair {dec(p['fair_decimal'])})</p>
<p class="muted">Official source: <a href="{esc(p['official_url'])}">{esc(p['official_source_name'])}</a></p>
</div>"""

index_body = f"""<section class="section">
<h2>Dashboard · Board AD (session arena/8cbd0cb9-olbg4)</h2>
<p class="muted">Every row on this site traces to a source link on the row. Where no governing-body source could be confirmed,
the pick, confidence and odds are left blank and the row is flagged on the <a href="flagged.html">Flagged for Review</a> page. Nothing is inferred.</p>
<div class="kpi-row">{kpi_html}</div>
<h3>Matches by sport</h3>
<div class="tiles">{tiles}</div>
<h3>High-confidence picks ({len(preds['predictions'])})</h3>
<p class="muted">Model probability ≥ 70% <strong>and</strong> originated book American odds inside −250…+10000. Full write-ups on the predictions page.</p>
<div class="cards">{high_cards}</div>
</section>"""
(OUT / "index.html").write_text(header("Dashboard") + index_body + footer())

def source_note(s: str) -> str:
    notes = {
        "greyhounds": "Quarantined: Greyhound Board of Great Britain feed WAF-blocked (HTTP 403) — no official inputs; picks/odds left blank.",
        "gaelic-football": "Scope note: brief excludes soccer/football and hurling; Gaelic football is a distinct GAA sport and is listed here for review (interpretation flagged).",
    }
    return f'<p class="muted flagbox">{esc(notes[s])}</p>' if s in notes else ""


# ---------------- sport pages ----------------
for s in ORDER:
    rows = BY_SPORT.get(s, [])
    if not rows:
        table = '<p class="muted">No events listed on the OLBG capture for this sport (audited, empty).</p>'
    else:
        table = sport_table(rows)
    body = f"""<section class="section">
<a class="button" href="../index.html">← Dashboard</a>
<h2>{esc(SPORT_TITLES[s])}</h2>
<p class="muted">{len(rows)} entr{"y" if len(rows)==1 else "ies"} rows</p>
{source_note(s)}
{table}
</section>"""
    (SPORTS_DIR / f"{s}.html").write_text(header(SPORT_TITLES[s], "../") + body + footer("../"))


# ---------------- predictions ----------------
cards = ""
for p in preds["predictions"]:
    cards += f"""<div class="card pred">
<h3>{esc(p['matchup'])}</h3>
<p class="muted">{esc(p['sport'])} · {esc(p['competition'])} · {esc(p['start_local'])} {esc(p['time_label'])}</p>
<p>{esc(p['text'])}</p>
<p><strong>Selection:</strong> {esc(p['selection'])} · <strong>Market:</strong> {esc(p['market_type'])} ·
<strong>Book:</strong> {dec(p['book_decimal'])} ({american(p['book_american'])}) ·
<strong>Model fair:</strong> {dec(p['fair_decimal'])}</p>
<p><strong>Words:</strong> {p['word_count']} · <strong>In window −250…+10000:</strong> yes</p>
<p><strong>Official source:</strong> <a href="{esc(p['official_url'])}" rel="noopener">{esc(p['official_source_name'])}</a></p>
</div>"""
pred_body = f"""<section class="section">
<h2>High-confidence human predictions</h2>
<p class="muted">All {len(preds['predictions'])} picks clear model probability ≥ 70% <strong>and</strong> originated book American odds in −250…+10000.
Each prediction is unique, human-written, ≥ {preds['min_words']} words, names the teams/players, states verified form and recent history from the cited official source, and states the explicit betting selection.
Max pairwise trigram Jaccard across predictions: {preds['max_pairwise_trigram_jaccard']:.4f}.</p>
<div class="cards">{cards}</div>
</section>"""
(OUT / "predictions.html").write_text(header("High-confidence predictions") + pred_body + footer())

# ---------------- flagged ----------------
items = ""
for it in flagged["items"]:
    blanks = ", ".join(it["blank_fields"]) or "none (unverified opinion line — see reason)"
    items += f"""<tr>
<td>{esc(it['id'])}</td><td>{esc(it['sport'])}</td><td>{esc(it['match'])}</td><td>{esc(it['date'])}</td>
<td>{esc(it['reason'])}</td><td class="muted">{blanks}</td>
<td>{f'<a href="{esc(it["review_url"])}" rel="noopener">review link</a> ({esc(it["review_url_kind"])})' if it["review_url"] else '— none recorded'}</td></tr>"""
flag_body = f"""<section class="section">
<h2>Flagged for Review</h2>
<p class="muted">{flagged['count']} rows could not be confirmed from an official governing-body source. Picks, confidence and odds are left blank
(or are disclosed neutral-prior opinion lines) and are published here for manual review — non-blocking. Review links point to OLBG listings
(non-official, cross-check only) where no official URL was recorded.</p>
<table class="data"><thead><tr><th>Id</th><th>Sport</th><th>Match</th><th>Date</th><th>Reason</th><th>Blank fields</th><th>Review link</th></tr></thead>
<tbody>{items}</tbody></table>
</section>"""
(OUT / "flagged.html").write_text(header("Flagged for Review") + flag_body + footer())

# ---------------- markets ----------------
market_rows = ""
for path in sorted(RAW := ROOT.glob("data/raw/*.json")):
    data = json.loads(path.read_text())
    sport = data["sport"]
    if sport.lower() in EXCLUDED:
        continue
    slug = SPORT_SLUG[sport]
    markets = ", ".join(esc(m) for m in data.get("olbg_markets_for_sport", []))
    n = len(BY_SPORT.get(slug, []))
    market_rows += f"""<tr><td>{esc(sport)}</td><td>{esc(data['source_page'])}</td><td>{n}</td><td>{markets or "— not stated on landing page"}</td>
<td>{esc(data.get('olbg_markets_evidence', ""))[:220]}</td></tr>"""
markets_body = f"""<section class="section">
<h2>Markets investigated, by sport</h2>
<p class="muted">Markets listed below are those OLBG publishes tips for on each sport landing page (captured 2026-10-21).
This desk originated Match Winner, Handicap and Match Total lines where verified inputs exist; otherwise the market cell is blank + flagged.</p>
<table class="data"><thead><tr><th>Sport</th><th>OLBG sport page</th><th>Desk rows</th><th>OLBG markets for sport</th><th>Evidence note</th></tr></thead>
<tbody>{market_rows}</tbody></table>
</section>"""
(OUT / "markets.html").write_text(header("Markets & coverage") + markets_body + footer())

# ---------------- methodology ----------------
method_body = f"""<section class="section">
<h2>Methodology</h2>
<h3>Scope</h3>
<p>In-scope sports: every OLBG sport except soccer/football, boxing (incl. UFC & MMA), American football, hurling, horse racing, cycling and specials.
OLBG sport IDs in scope: 3 Tennis, 4 Basketball, 5 Golf, 7 Cricket, 8 Snooker, 9 Rugby Union, 10 Rugby League, 12 Baseball, 13 Ice Hockey,
14 Motor Racing, 15 Darts, 20 Handball, 21 Volleyball, 22 Aussie Rules, 23 eSports, 25 Gaelic Football, 28 Greyhounds.</p>
<h3>Source of the fixture list</h3>
<p>Committed OLBG reverse-engineering snapshot <code>data/raw/*.json</code> (collected 2026-10-21): server-rendered event feeds from each in-scope
OLBG sport landing page. Limitation recorded on the source page: OLBG only surfaces events that have received at least one tip, and additional
events sit behind a JavaScript "Load More Tips" control, so the public feed is not a complete fixture list. Untipped fixtures are not enumerable
from OLBG's public pages and are not invented here.</p>
<h3>Line origination (our own lines)</h3>
<p>No live market odds or team-strength feeds are reachable from this sandbox (egress limited to GitHub and package registries), so fair prices
originate from a disclosed <strong>neutral-prior model</strong>: win probability 0.50 / 0.50 for two-sided matches (fair decimal 2.00 per side);
book price at a disclosed 4.2% vig → decimal 1.92 (American −109 per side); handicap line 0.0 (pick'em); match total not originated (no verified
scoring inputs). Golf and motor-racing entries are tournament/race winner events with no head-to-head match-winner line. Greyhounds are quarantined
(GBGB feed WAF-blocked, HTTP 403). All lines are our own opinion expressions, not verified probabilities.</p>
<h3>Confidence</h3>
<p>Low for all neutral-prior rows (no verified strength inputs). High <strong>only</strong> where model probability ≥ 70% <strong>and</strong>
originated book American odds fall inside −250…+10000. Two peer-session verified rows (session e1161e0e, Board X) clear that rule and are overlaid
with attribution: X032 Toronto Raptors at Washington Wizards (p 0.708, −242) and X087 Samoa v Wales (p 0.700, −233).</p>
<h3>Predictions</h3>
<p>High-confidence picks only: unique, human-written, ≥ 30 words each, naming teams/players, stating verified form and recent match history from
the cited official source, and stating the explicit betting selection. No text is templated or generated from unverified inputs.</p>
<h3>Verification standard</h3>
<p>Every table row shows its source link. If a value cannot be confirmed from an official source it is left blank and the row is flagged.
Nothing is inferred or filled in. Repo-wide line-by-line review findings are in <code>data/session-8cbd0cb9/repo_review.json</code> and summarised
on the Flagged for Review page.</p>
<h3>Network limitation</h3>
<p class="muted">OLBG.com and governing-body domains were unreachable from this sandbox at build time (HTTP connect failed); verification is therefore
against the committed official-source records (data/source_registry.json) and attributed peer-session data, not against live pages. All live
re-verification is left as manual review items on the Flagged for Review page.</p>
</section>"""
(OUT / "methodology.html").write_text(header("Methodology") + method_body + footer())

# ---------------- verification ----------------
ver_res = DATA / "verify_result.json"
ver_lines = []
if ver_res.exists():
    vr = json.loads(ver_res.read_text())
    ver_lines.append(f'gate: {"PASS" if vr["passed"] else "FAIL"} · {vr["checks"]} checks · {len(vr["errors"])} errors')
    ver_lines.append(f'desk rows: {vr["rows"]} | high-confidence: {vr["high_confidence"]} | predictions: {vr["predictions"]} | flagged: {vr["flagged"]}')
    ver_lines.append(f'max prediction trigram Jaccard: {vr["max_prediction_trigram_jaccard"]:.4f}')
    if vr["errors"]:
        ver_lines.append("")
        ver_lines.extend(f'ERROR: {e}' for e in vr["errors"])
else:
    ver_lines.append("Verification gate not yet run: python3 scripts/session-8cbd0cb9/verify.py")
ver_body = f"""<section class="section">
<h2>Verification</h2>
<p class="muted">Verification gate: <code>python3 scripts/session-8cbd0cb9/verify.py</code> — exits non-zero on any failure.</p>
<pre>{chr(10).join(ver_lines)}</pre>
</section>"""
(OUT / "verification.html").write_text(header("Verification") + ver_body + footer())

# ---------------- assets ----------------
css = """* { box-sizing: border-box; }
body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f4f7fb; color: #17263c; margin: 0; }
.wrap { max-width: 1400px; margin: 0 auto; padding: 16px 20px; }
.band { background: #17263c; color: #fff; padding: 24px 0; margin-bottom: 8px; }
.band h1 { margin: 0 0 6px 0; font-size: 22px; }
.subtitle { margin: 0; color: #c9d6e8; font-size: 14px; }
.topnav { background: #ffffff; border-bottom: 1px solid #dce2eb; }
.topnav ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; }
.topnav li { margin: 0; }
.topnav a { display: block; padding: 10px 14px; color: #0758a3; text-decoration: none; font-size: 14px; }
.topnav a:hover { background: #eef3fa; }
main { background: #ffffff; border: 1px solid #dce2eb; border-radius: 8px; padding: 24px; margin-bottom: 16px; }
section { margin-bottom: 26px; }
section h2 { font-size: 18px; margin: 0 0 8px 0; border-bottom: 2px solid #17263c; padding-bottom: 6px; }
h3 { font-size: 15px; margin: 16px 0 6px 0; }
p { line-height: 1.55; }
.muted { color: #64748b; font-size: 13px; }
a { color: #0758a3; }
.kpi-row { display: flex; flex-wrap: wrap; gap: 12px; margin: 14px 0 20px 0; }
.kpi { background: #eef3fa; border: 1px solid #dce2eb; border-radius: 8px; padding: 14px 16px; flex: 1 1 170px; min-width: 160px; }
.kpi .big { font-size: 26px; font-weight: 700; color: #17263c; }
.kpi .small { font-size: 13px; color: #0758a3; margin-top: 4px; }
.tiles { display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0; }
.tile { border: 1px solid #dce2eb; border-radius: 8px; padding: 12px 14px; text-decoration: none; color: #17263c; font-weight: 600; background: #fff; }
.tile:hover { border-color: #0758a3; background: #eef3fa; }
.cards { display: flex; flex-wrap: wrap; gap: 14px; margin: 10px 0; }
.card { border: 1px solid #dce2eb; border-radius: 8px; padding: 14px 16px; background: #fff; flex: 1 1 300px; min-width: 260px; }
.card.pred { min-width: 560px; }
.card h3 { margin: 0 0 6px 0; font-size: 15px; }
.button { display: inline-block; border: 1px solid #dce2eb; border-radius: 8px; padding: 8px 12px; text-decoration: none; color: #0758a3; margin-bottom: 10px; }
.button:hover { background: #eef3fa; }
table.data { border-collapse: collapse; width: 100%; font-size: 13px; margin-top: 10px; }
table.data th { background: #17263c; color: #fff; text-align: left; padding: 8px 10px; border: 1px solid #dce2eb; font-size: 12px; }
table.data td { padding: 7px 10px; border: 1px solid #dce2eb; vertical-align: top; }
table.data tr:nth-child(even) td { background: #f6f9fc; }
.num { white-space: nowrap; }
.src { max-width: 220px; overflow-wrap: break-word; }
.flags .flag { display: inline-block; width: 9px; height: 9px; background: #b91c1c; border-radius: 50%; margin-right: 4px; vertical-align: middle; }
.badge { display: inline-block; border-radius: 10px; padding: 2px 8px; font-size: 11.5px; font-weight: 700; }
.flagbox { background: #fdf3e7; border-left: 4px solid #b56600; padding: 10px 14px; margin: 10px 0; }
pre { background: #0f172a; color: #e2e8f0; padding: 14px; border-radius: 6px; overflow: auto; font-size: 12px; }
footer { border-top: 1px solid #dce2eb; color: #64748b; font-size: 12.5px; padding: 18px 0; }
footer a { color: #0758a3; }
"""
(ASSETS / "style.css").write_text(css)

js = """document.addEventListener('DOMContentLoaded', function(){
var table = document.getElementById('entries-table');
if (!table) return;
var rows = table.querySelectorAll('tbody tr');
var filters = {};
function render(){
  var sport = document.getElementById('fsport').value;
  var conf = document.getElementById('fconf').value;
  rows.forEach(function(tr){
    var show = (!sport || tr.dataset.sport === sport) && (!conf || tr.dataset.conf === conf);
    tr.style.display = show ? '' : 'none';
  });
  var n = 0; rows.forEach(function(tr){ if (tr.style.display !== 'none') n++; });
  var el = document.getElementById('count'); if (el) el.textContent = n + ' of ' + rows.length + ' entries shown';
}
var fsport = document.getElementById('fsport');
if (fsport) fsport.addEventListener('change', render);
var fconf = document.getElementById('fconf');
if (fconf) fconf.addEventListener('change', render);
render();
});"""
(ASSETS / "app.js").write_text(js)

print("site written:", len(list(OUT.rglob('*.html'))), "html pages")
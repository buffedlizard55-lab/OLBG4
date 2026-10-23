#!/usr/bin/env python3
"""Board ED — build the dashboard site under session-ed4c358c/.

Landing page (executive summary) + one page per sport + entries / markets / picks /
predictions / coverage / sources / methodology / review / flagged pages. Every table row
that has an official source links to it; rows without one say so explicitly.
"""
from __future__ import annotations

import html
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from edlib import DATA, ROOT, SLUG, SPORTS, iso_now

OUT = ROOT / "session-ed4c358c"
SPORT_DIR = OUT / "sports"
STAMP = json.loads((DATA / "desk.json").read_text())["capture_stamp"]

CSS = """
:root{--bg:#0b1220;--panel:#121b2e;--panel2:#18233a;--ink:#e8eefb;--muted:#93a3c0;--line:#24314d;
--accent:#4da3ff;--good:#35d07f;--warn:#ffc857;--bad:#ff6b6b;--chip:#1d2b45}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
header.top{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.95);border-bottom:1px solid var(--line);backdrop-filter:blur(6px)}
.wrap{max-width:1240px;margin:0 auto;padding:0 20px}
.bar{display:flex;align-items:center;gap:18px;height:60px;flex-wrap:wrap}
.brand{font-weight:700;letter-spacing:.4px;font-size:16px}
.brand span{color:var(--accent)}
nav{display:flex;gap:14px;flex-wrap:wrap;font-size:13.5px}
nav a{color:var(--muted)}nav a.active,nav a:hover{color:var(--ink)}
main{padding:26px 0 60px}
h1{font-size:28px;margin:6px 0 6px}h2{font-size:19px;margin:30px 0 10px}h3{font-size:15.5px;margin:20px 0 8px}
p.lead{color:var(--muted);margin:0 0 18px;max-width:900px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0 6px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .k{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.6px}
.card .v{font-size:26px;font-weight:700;margin-top:4px}
.card .s{color:var(--muted);font-size:12.5px;margin-top:2px}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:4px 0;overflow:auto;margin-top:8px}
table{border-collapse:collapse;width:100%;font-size:13.2px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--panel2);color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.5px;position:sticky;top:60px}
tr:hover td{background:#16203566}
.chip{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11.5px;font-weight:600;background:var(--chip);border:1px solid var(--line);white-space:nowrap}
.high{color:var(--good);border-color:#2b6b4b;background:#12351f}
.medium{color:var(--warn);border-color:#7a6021;background:#31260c}
.low{color:var(--muted)}
.off{color:var(--accent)}.olbgc{color:var(--warn)}
.muted{color:var(--muted)}.small{font-size:12px}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.flag{color:var(--warn)}
input[type=search],select{background:var(--panel2);border:1px solid var(--line);color:var(--ink);padding:8px 10px;border-radius:8px;font-size:13px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0}
.pred{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin:12px 0}
.pred h3{margin:0 0 4px;font-size:16px}
.pred .meta{color:var(--muted);font-size:12.5px;margin-bottom:8px}
.pred .txt{max-width:940px}
.pred .src{margin-top:10px;font-size:12.5px;color:var(--muted)}
.sel{display:inline-block;background:#12351f;border:1px solid #2b6b4b;color:var(--good);border-radius:8px;padding:2px 9px;font-weight:600;font-size:12.5px}
.footer{color:var(--muted);font-size:12.5px;border-top:1px solid var(--line);margin-top:40px;padding-top:16px}
.note{border-left:3px solid var(--accent);background:#101a2c;padding:10px 14px;border-radius:6px;margin:12px 0;color:var(--muted)}
.warnbox{border-left:3px solid var(--warn);background:#241d0c;padding:10px 14px;border-radius:6px;margin:12px 0}
"""

NAV = [
    ("index.html", "Overview"), ("picks.html", "Picks"), ("predictions.html", "Predictions"),
    ("entries.html", "All entries"), ("markets.html", "Markets"), ("coverage.html", "Coverage"),
    ("sources.html", "Sources"), ("methodology.html", "Methodology"), ("review.html", "Repo review"),
    ("flagged.html", "Flagged for review"), ("verification.html", "Verification"),
]


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def page(title: str, body: str, active: str = "", prefix: str = "") -> str:
    if prefix:
        body = re.sub(r'href="(?!https?:|#|\.\./)', 'href="' + prefix, body)
    nav = "".join(
        f'<a href="{prefix}{href}"'
        f'{" class=active" if href == active else ""}>{label}</a>'
        for href, label in NAV
    )
    sport_nav = "".join(
        f'<a href="{prefix}sports/{SLUG[s]}.html">{esc(s)}</a>' for s in SPORTS
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · OLBG4 Board ED</title><style>{CSS}</style></head><body>
<header class="top"><div class="wrap">
<div class="bar"><div class="brand">OLBG4 <span>· Board ED</span></div>
<nav>{nav}</nav></div>
<div class="bar" style="height:auto;padding-bottom:8px"><nav>{sport_nav}</nav></div>
</div></header><main><div class="wrap">{body}
<div class="footer">Desk built {esc(iso_now())} from official capture <span class="mono">{esc(STAMP)}</span>.
Every row links its source. Values that could not be confirmed from an official page are blank and listed on
<a href="{prefix}flagged.html">Flagged for review</a>. Session <span class="mono">arena/ed4c358c-olbg4</span>.</div>
</div></main></body></html>"""


def conf_chip(c: str) -> str:
    if not c:
        return '<span class="chip low">—</span>'
    return f'<span class="chip {c.lower()}">{esc(c)}</span>'


def price(x) -> str:
    return f"{x:+.0f}" if isinstance(x, (int, float)) else ""


def source_cell(row: dict) -> str:
    if row.get("official_url") and row.get("source_tier") != "olbg-listing":
        return f'<a href="{esc(row["official_url"])}" target="_blank" rel="noopener">official ↗</a>'
    ol = row.get("olbg") or {}
    if ol.get("hub_url"):
        return f'<a class="olbgc" href="{esc(ol["hub_url"])}" target="_blank" rel="noopener">OLBG listing ↗</a>'
    return '<span class="flag">no source</span>'


def pick_cell(row: dict) -> str:
    b = row.get("best")
    if not b:
        return '<span class="muted">— no own line —</span>'
    return (f'{esc(b["market_name"])}: <b>{esc(b["selection"])}</b><br>'
            f'<span class="mono">{b["fair_prob"]*100:.1f}% · {b["fair_american"]:+d}</span> '
            f'{conf_chip(b.get("confidence",""))}')
    return ""


def row_tr(r: dict) -> str:
    t = r["start_utc"][:16].replace("T", " ") if r["start_utc"] else "TBC"
    flags = " ".join(f'<span class="flag">⚑ {esc(f)}</span>' for f in r.get("flags", []))
    return (f'<tr><td class="mono">{esc(t)}</td><td>{esc(r["competition"])}</td>'
            f'<td>{esc(r["matchup"])}</td><td>{esc(r.get("venue",""))}</td>'
            f'<td>{source_cell(r)}</td><td>{pick_cell(r)}</td>'
            f'<td>{conf_chip(r.get("confidence",""))}</td><td class="small">{flags}</td></tr>')


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    review = json.loads((DATA / "repo_review.json").read_text())
    inv = json.loads((DATA / "olbg_inventory.json").read_text())
    rows = desk["rows"]
    priced = [r for r in rows if r["markets"]]
    by_sport = defaultdict(list)
    for r in rows:
        by_sport[r["sport"]].append(r)

    OUT.mkdir(exist_ok=True)
    SPORT_DIR.mkdir(exist_ok=True)

    # ---------------------------------------------------------------- overview
    high = [r for r in rows if r.get("best") and r["best"].get("confidence") == "High"]
    inwin = [r for r in high if r["best"].get("in_window")]
    exec_rows = sorted(high, key=lambda r: -r["best"]["fair_prob"])[:20]
    cards = [
        ("Verified rows", len(rows), f"{len(priced)} with our own lines"),
        ("Own-line markets", desk["summary"]["markets"], "winner · handicap · total"),
        ("OLBG events mirrored", inv["totals"]["events"], f"{inv['totals']['markets']} listed prices"),
        ("High-confidence picks", len(high), f"{len(inwin)} inside −250…+10,000"),
        ("Written predictions", preds["count"], ", ".join(f"{k} {v}" for k, v in preds["by_sport"].items())),
        ("Repo defects logged", review["summary"]["findings"], f"{review['summary']['rows_inspected']} rows inspected"),
    ]
    card_html = "".join(
        f'<div class="card"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div><div class="s">{esc(s)}</div></div>'
        for k, v, s in cards)
    body = f"""<h1>Executive summary</h1>
<p class="lead">A self-contained betting desk for the fifteen OLBG sports in scope. Fixtures and form come from
official league, tour and federation feeds captured on {esc(desk['capture_stamp'])}; OLBG.com is used for its
sport and market taxonomy and for a listing cross-check. We originate our own margin-free lines, grade every pick,
and publish only what an official source supports.</p>
<div class="grid">{card_html}</div>
<div class="note"><b>Reading the window.</b> A 70.0% chance prices at −233 and 71.43% at −250, so a pick that is
both above 70% and inside −250…+10,000 can only sit in the narrow band p = 0.700–0.7143. We do not move prices to
fit that band: picks above 70% but shorter than −250 are labelled as such, and {len(inwin)} of {len(high)} High
picks land inside it. Full arithmetic on <a href="picks.html">Picks</a>.</div>
<h2>Highest-confidence picks</h2>
<div class="panel"><table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Match</th><th>Selection</th>
<th>Fair price</th><th>Grade</th><th>Source</th></tr></thead><tbody>
{''.join(f'<tr><td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{esc(r["sport"])}</td>'
         f'<td>{esc(r["matchup"])}</td><td>{esc(r["best"]["market_name"])}: <b>{esc(r["best"]["selection"])}</b></td>'
         f'<td class="mono">{r["best"]["fair_american"]:+d} ({r["best"]["fair_prob"]*100:.1f}%)</td>'
         f'<td>{conf_chip(r["best"]["confidence"])}</td><td>{source_cell(r)}</td></tr>' for r in exec_rows)}
</tbody></table></div>
<h2>Coverage at a glance</h2>
<div class="panel"><table><thead><tr><th>Sport</th><th>Rows</th><th>With own lines</th><th>High</th>
<th>Predictions</th><th>Official form source used</th></tr></thead><tbody>
{''.join(f'<tr><td><a href="sports/{SLUG[s]}.html">{esc(s)}</a></td>'
         f'<td>{len(by_sport[s])}</td><td>{sum(1 for r in by_sport[s] if r["markets"])}</td>'
         f'<td>{sum(1 for r in by_sport[s] if r.get("best") and r["best"].get("confidence")=="High")}</td>'
         f'<td>{preds["by_sport"].get(s, 0)}</td>'
         f'<td class="small">{esc(next((r["official_source_name"] for r in by_sport[s] if r["markets"]), "— no official form feed captured —"))}</td></tr>'
         for s in SPORTS)}
</tbody></table></div>
<h2>What the desk does not claim</h2>
<div class="warnbox">Seven of the fifteen sports carry no originated line in this capture because no official
machine-readable form or standings feed was reachable for them (Golf listed no event at all; Darts, Gaelic Sports,
Greyhounds, Rugby League, Snooker and Rugby Union returned JavaScript shells or login walls). Those fixtures are
published from the OLBG listing with blank prices and an explicit flag rather than with invented numbers. Details
on <a href="coverage.html">Coverage</a> and <a href="flagged.html">Flagged for review</a>.</div>
"""
    (OUT / "index.html").write_text(page("Executive summary", body, "index.html"))

    # ---------------------------------------------------------------- sport pages
    for s in SPORTS:
        rs = sorted(by_sport[s], key=lambda r: (r["start_utc"], r["matchup"]))
        priced_s = [r for r in rs if r["markets"]]
        top = sorted([r for r in rs if r.get("best")],
                     key=lambda r: (-(r["best"].get("confidence") == "High"), -r["best"]["fair_prob"]))[:5]
        preds_s = [p for p in preds["predictions"] if p["sport"] == s]
        src = next((r["official_source_name"] for r in priced_s), "")
        body = f"""<h1>{esc(s)}</h1>
<p class="lead">{len(rs)} fixtures in the {esc(desk['cutoff_utc'][:10])} – {esc(desk['window_end_utc'][:10])} window,
{len(priced_s)} with our own lines. {esc(src) if src else 'No official form feed was captured for this sport, so no line is originated.'}</p>
<h2>Top five selections</h2>
<div class="panel"><table><thead><tr><th>Start</th><th>Match</th><th>Selection</th><th>Fair price</th><th>Grade</th><th>Source</th></tr></thead><tbody>
{''.join(f'<tr><td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{esc(r["matchup"])}</td>'
         f'<td>{esc(r["best"]["market_name"])}: <b>{esc(r["best"]["selection"])}</b></td>'
         f'<td class="mono">{r["best"]["fair_american"]:+d} ({r["best"]["fair_prob"]*100:.1f}%)</td>'
         f'<td>{conf_chip(r["best"].get("confidence",""))}</td><td>{source_cell(r)}</td></tr>' for r in top)
 or '<tr><td colspan="6" class="muted">No selection could be originated for this sport in this capture.</td></tr>'}
</tbody></table></div>
<h2>All fixtures</h2>
<div class="panel"><table><thead><tr><th>Start (UTC)</th><th>Competition</th><th>Match</th><th>Venue</th>
<th>Source</th><th>Our line / pick</th><th>Grade</th><th>Notes</th></tr></thead><tbody>
{''.join(row_tr(r) for r in rs) or '<tr><td colspan="8" class="muted">No fixture published for this sport.</td></tr>'}
</tbody></table></div>
{('<h2>Predictions</h2>' + ''.join(render_pred(p) for p in preds_s)) if preds_s else ''}
"""
        body = body  # relative links are prefixed inside page()
        (SPORT_DIR / f"{SLUG[s]}.html").write_text(page(s, body, f"sports/{SLUG[s]}.html", prefix="../"))

    # ---------------------------------------------------------------- picks
    picks_by_sport = []
    for s in SPORTS:
        rs = sorted([r for r in by_sport[s] if r.get("best")],
                    key=lambda r: (-(r["best"].get("confidence") == "High"), -r["best"]["fair_prob"]))[:5]
        picks_by_sport.append((s, rs))
    body = f"""<h1>Picks and the −250…+10,000 window</h1>
<p class="lead">The five strongest selections for each sport we could originate. Confidence is graded on our own
fair probability: High ≥ 70%, Medium 58–70%, Low below 58%. Sample caps (few rounds played, seed-only inputs)
force Medium at best.</p>
<div class="note"><b>Why the window is narrow.</b> American −250 is a 71.43% implied chance and +10,000 is 0.99%.
Anything above 70% therefore sits between −233 and −250 at the top of the range. Of {len(high)} High picks,
{len(inwin)} fall inside −250…+10,000; the rest are shorter than −250 and are shown with their true price rather
than trimmed to fit.</div>
{''.join(f'''<h2>{esc(s)}</h2><div class="panel"><table><thead><tr><th>#</th><th>Start</th><th>Match</th>
<th>Selection</th><th>Fair price</th><th>Probability</th><th>Grade</th><th>Window</th><th>Source</th></tr></thead><tbody>
{''.join(f'<tr><td>{i}</td><td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{esc(r["matchup"])}</td>'
         f'<td>{esc(r["best"]["market_name"])}: <b>{esc(r["best"]["selection"])}</b></td>'
         f'<td class="mono">{r["best"]["fair_american"]:+d}</td><td class="mono">{r["best"]["fair_prob"]*100:.1f}%</td>'
         f'<td>{conf_chip(r["best"].get("confidence",""))}</td>'
         f'<td>{"inside" if r["best"].get("in_window") else "outside (−250..+10,000)"}</td>'
         f'<td>{source_cell(r)}</td></tr>' for i, r in enumerate(rs, 1)) or
'<tr><td colspan="9" class="muted">No priced selection for this sport.</td></tr>'}
</tbody></table></div>''' for s, rs in picks_by_sport)}
"""
    (OUT / "picks.html").write_text(page("Picks", body, "picks.html"))

    # ---------------------------------------------------------------- predictions
    body = f"""<h1>Written predictions</h1>
<p class="lead">{preds['count']} hand-written previews across {len(preds['by_sport'])} sports, each naming the
teams or players, the official form inputs for that specific fixture, and a stated betting selection. Every card
links the official page the facts came from.</p>
<div class="note">Sports are only included where an official feed gave us enough to support a specific, checkable
statement. We do not write around gaps: sports without a captured form feed carry no prediction and are listed on
<a href="coverage.html">Coverage</a>.</div>
{''.join(render_pred(p) for p in preds['predictions'])}
"""
    (OUT / "predictions.html").write_text(page("Predictions", body, "predictions.html"))

    # ---------------------------------------------------------------- entries
    body = f"""<h1>All entries</h1>
<p class="lead">{len(rows)} rows across {len([s for s in SPORTS if by_sport[s]])} sports, {desk['window_end_utc'][:10]}
cut-off. Filter by sport, grade or source type.</p>
<div class="toolbar">
<input type="search" id="q" placeholder="Search team, competition, venue…" style="min-width:280px">
<select id="sport"><option value="">All sports</option>{''.join(f'<option>{esc(s)}</option>' for s in SPORTS if by_sport[s])}</select>
<select id="conf"><option value="">All grades</option><option>High</option><option>Medium</option><option>Low</option><option>unpriced</option></select>
<span class="muted small" id="count"></span></div>
<div class="panel"><table id="tbl"><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Competition</th><th>Match</th>
<th>Venue</th><th>Source</th><th>Our line / pick</th><th>Grade</th><th>Notes</th></tr></thead><tbody>
{''.join(f'<tr data-sport="{esc(r["sport"])}" data-conf="{esc(r.get("confidence") or "unpriced")}">'
         f'<td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{esc(r["sport"])}</td>'
         f'<td>{esc(r["competition"])}</td><td>{esc(r["matchup"])}</td><td>{esc(r.get("venue",""))}</td>'
         f'<td>{source_cell(r)}</td><td>{pick_cell(r)}</td><td>{conf_chip(r.get("confidence",""))}</td>'
         f'<td class="small">{" ".join("⚑ "+esc(f) for f in r.get("flags", []))}</td></tr>' for r in rows)}
</tbody></table></div>
<script>
const q=document.getElementById('q'),sp=document.getElementById('sport'),cf=document.getElementById('conf'),
 rows=[...document.querySelectorAll('#tbl tbody tr')],cnt=document.getElementById('count');
function f(){{const t=q.value.toLowerCase(),s=sp.value,c=cf.value;let n=0;
 rows.forEach(r=>{{const ok=(!t||r.textContent.toLowerCase().includes(t))&&(!s||r.dataset.sport===s)&&
 (!c||r.dataset.conf===c);r.style.display=ok?'':'none';if(ok)n++;}});cnt.textContent=n+' rows';}}
[q,sp,cf].forEach(e=>e.addEventListener('input',f));f();
</script>
"""
    (OUT / "entries.html").write_text(page("All entries", body, "entries.html"))

    # ---------------------------------------------------------------- markets
    markets_html = []
    for r in priced:
        sel = ""
        for mkey, m in r["markets"].items():
            rows_html = "".join(
                f'<tr><td>{esc(m.get("market_name", mkey))}{" " + str(m.get("line")) if m.get("line") not in (None, "") else ""}</td>'
                f'<td>{esc(s["label"])}</td><td class="mono">{s["fair_prob"]*100:.1f}%</td>'
                f'<td class="mono">{s["fair_decimal"]:.3f}</td><td class="mono">{s["fair_american"]:+d}</td></tr>'
                for s in m["selections"])
            sel += rows_html
        markets_html.append(f'<tr><td>{esc(r["sport"])}</td><td>{esc(r["matchup"])}</td>'
                            f'<td>{source_cell(r)}</td><td class="small">{sel}</td></tr>')
    body = f"""<h1>Markets originated</h1>
<p class="lead">{desk['summary']['markets']} fair (margin-free) selections across {len(priced)} fixtures:
match winner both ways, a handicap or spread, and a match total. Prices are 1 / probability with no bookmaker
margin applied.</p>
<div class="panel"><table><thead><tr><th>Sport</th><th>Match</th><th>Source</th><th>Markets (probability · decimal · American)</th></tr></thead><tbody>
{''.join(markets_html)}
</tbody></table></div>
"""
    (OUT / "markets.html").write_text(page("Markets", body, "markets.html"))

    # ---------------------------------------------------------------- coverage
    cov_rows = []
    for s in SPORTS:
        rs = by_sport[s]
        priced_s = [r for r in rs if r["markets"]]
        reasons = sorted({f for r in rs for f in r.get("flags", [])})
        cov_rows.append(
            f'<tr><td><a href="sports/{SLUG[s]}.html">{esc(s)}</a></td><td>{len(rs)}</td>'
            f'<td>{len(priced_s)}</td><td>{sum(1 for r in rs if r.get("best") and r["best"].get("confidence")=="High")}</td>'
            f'<td>{preds["by_sport"].get(s,0)}</td>'
            f'<td class="small">{esc("; ".join(reasons)[:260])}</td></tr>')
    body = f"""<h1>Coverage and honest gaps</h1>
<p class="lead">What each sport actually carries in this build, and why anything is missing.</p>
<div class="panel"><table><thead><tr><th>Sport</th><th>Rows</th><th>With own lines</th><th>High picks</th>
<th>Predictions</th><th>Notes and flags</th></tr></thead><tbody>{''.join(cov_rows)}</tbody></table></div>
<h2>Sources that worked and sources that did not</h2>
<p class="lead">Every URL below was requested by the capture job; the table on <a href="sources.html">Sources</a>
shows the exact HTTP status for each. The pattern is consistent with previous boards: JSON APIs from the
NHL, MLB, EuroLeague, WTA and Liiga work, while several league sites return JavaScript shells (URC, WST, PDC,
NBA, NRL) and were not used as evidence.</p>
<div class="warnbox"><b>No line without a feed.</b> Golf listed no event on the OLBG hub at capture and no
official field feed was reachable, so Golf carries zero rows rather than an invented outright market.
Greyhounds returned only completed-race results (the pre-race endpoints 404), so no upcoming race is priced.
The same applies to Darts, Gaelic Sports, Rugby League, Snooker and Rugby Union.</div>
"""
    (OUT / "coverage.html").write_text(page("Coverage", body, "coverage.html"))

    # ---------------------------------------------------------------- sources
    manifest = json.loads((DATA / "capture" / STAMP / "manifest.json").read_text())
    src_rows = "".join(
        f'<tr><td class="mono">{esc(r.get("status"))}</td><td>{esc(r["id"])}</td>'
        f'<td class="small"><a href="{esc(r["url"])}" target="_blank" rel="noopener">{esc(r["url"][:110])}</a></td>'
        f'<td class="mono small">{esc((r.get("sha256") or "")[:16])}</td>'
        f'<td class="mono">{esc(r.get("bytes") or "")}</td></tr>'
        for r in sorted(manifest["records"], key=lambda r: (r.get("status") != 200, r["id"])))
    body = f"""<h1>Sources — capture manifest</h1>
<p class="lead">Capture <span class="mono">{esc(STAMP)}</span>: {manifest['ok']} of {manifest['targets']} URLs
returned 200. Raw bytes are committed under <span class="mono">data/session-ed4c358c/capture/{esc(STAMP)}/</span>
with a SHA-256 per file, and every published value is re-hashed against this manifest before use.</p>
<div class="panel"><table><thead><tr><th>HTTP</th><th>Target</th><th>URL</th><th>SHA-256 (head)</th><th>Bytes</th></tr></thead>
<tbody>{src_rows}</tbody></table></div>
"""
    (OUT / "sources.html").write_text(page("Sources", body, "sources.html"))

    # ---------------------------------------------------------------- methodology
    body = f"""<h1>Methodology</h1>
<p class="lead">Everything below is deterministic: the same captured bytes rebuild the same desk.</p>
<h2>1. What is captured</h2>
<p>A GitHub Actions runner with open egress requests each official URL once, politely, and commits the exact
bytes plus a SHA-256 manifest. Local parsing re-hashes every file before use, so a published number can always be
traced to bytes that are in the repository.</p>
<h2>2. How lines are originated</h2>
<ul>
<li><b>Ice Hockey.</b> Team attack and defence ratings are goals for/against per game against the league average,
shrunk toward 1.0 with a 12–14 game prior, then multiplied with a 6% home edge. A Poisson score matrix gives the
money line, puck line and total.</li>
<li><b>Baseball.</b> The same Poisson construction on team runs scored and allowed per game from the MLB Stats API
season splits, with a 2% park/home adjustment.</li>
<li><b>Basketball.</b> Expected points from season-to-date points for/against per game, margin as a Normal with
sigma 10.5 and totals with sigma 12.</li>
<li><b>Handball and Volleyball.</b> Attack/defence from the official league table; Poisson for handball,
set-ratio and point-ratio logistic for volleyball, converted to a per-set probability to price the set handicap
and total sets.</li>
<li><b>Tennis.</b> Seeding implies a ranking slot (seed n ≈ rank 2n−1, unseeded ≈ 45–55), mapped to an Elo via
2200 − 100·ln(rank). Seed-only inputs are capped at Medium.</li>
<li><b>Motor Racing.</b> Race-winner probabilities are a softmax over official championship points with a
55-point temperature.</li>
</ul>
<h2>3. Grading</h2>
<p>High ≥ 70%, Medium 58–70%, Low below 58%, with sample caps. The pick column on each row is the match winner;
the pick table also shows the strongest selection across every market we originated.</p>
<h2>4. What is deliberately blank</h2>
<p>No value is inferred. A row with no official form feed keeps an empty price and an explicit flag. Injury
information is only ever stated when an official page carries it, which is why no prediction claims an injury in
this build.</p>
"""
    (OUT / "methodology.html").write_text(page("Methodology", body, "methodology.html"))

    # ---------------------------------------------------------------- review
    ds_rows = "".join(
        f'<tr><td class="mono">{esc(p)}</td><td>{d.get("rows","—")}</td><td>{d.get("missing_source","—")}</td>'
        f'<td>{d.get("past_dated","—")}</td><td>{d.get("predictions_under_30_words","—")}</td>'
        f'<td>{d.get("predictions_with_internal_vocabulary","—")}</td><td>{d.get("duplicate_matchups","—")}</td></tr>'
        for p, d in review["datasets"].items())
    def _sev(f):
        return "high" if f["severity"] == "high" else ("medium" if f["severity"] == "medium" else "low")

    def _link(f):
        if not f.get("review_url"):
            return "—"
        return '<a href="%s" target="_blank" rel="noopener">open ↗</a>' % esc(f["review_url"])

    find_rows = "".join(
        '<tr><td>%s</td><td><span class="chip %s">%s</span></td><td class="mono small">%s</td>'
        '<td>%s</td><td class="mono">%s</td><td class="small">%s</td></tr>' % (
            esc(f["id"]), _sev(f), esc(f["severity"]), esc(f["dataset"]), esc(f["issue"]),
            f["count"], _link(f))
        for f in review["findings"])
    ex = []
    for f in review["findings"]:
        for e in f.get("examples", [])[:4]:
            link = f'<a href="{esc(e["review_url"])}" target="_blank" rel="noopener">source ↗</a>' if e.get("review_url") else '<span class="muted">no source on row</span>'
            ex.append(f'<li><b>{esc(f["id"])}</b> — {esc(e["label"])} · {link}</li>')
    body = f"""<h1>Repository review</h1>
<p class="lead">Line-by-line check of the datasets owned by other boards: {review['summary']['rows_inspected']}
rows inspected across {review['summary']['datasets_reviewed']} files, {review['summary']['findings']} findings
({review['summary']['high']} high, {review['summary']['medium']} medium, {review['summary']['low']} low). Nothing
in those files was edited; the defects are published for review.</p>
<div class="panel"><table><thead><tr><th>Dataset</th><th>Rows</th><th>No source</th><th>Past-dated</th>
<th>Predictions &lt; 30 words</th><th>Internal vocabulary</th><th>Duplicate matchups</th></tr></thead>
<tbody>{ds_rows}</tbody></table></div>
<h2>Findings</h2>
<div class="panel"><table><thead><tr><th>ID</th><th>Severity</th><th>Dataset</th><th>Issue</th><th>Rows</th><th>Link</th></tr></thead>
<tbody>{find_rows}</tbody></table></div>
<h2>Examples to open manually</h2>
<ul class="small">{''.join(ex)}</ul>
"""
    (OUT / "review.html").write_text(page("Repository review", body, "review.html"))

    # ---------------------------------------------------------------- flagged
    flags = defaultdict(list)
    for r in rows:
        for f in r.get("flags", []):
            flags[f].append(r)
    flag_rows = []
    for f, rs in sorted(flags.items(), key=lambda kv: -len(kv[1])):
        sports = sorted({r["sport"] for r in rs})
        example = rs[0]
        flag_rows.append(
            f'<tr><td>{esc(f)}</td><td>{len(rs)}</td><td class="small">{esc(", ".join(sports))}</td>'
            f'<td class="small">{source_cell(example)}</td></tr>')
    body = f"""<h1>Flagged for review</h1>
<p class="lead">Everything the desk could not confirm, published rather than hidden. These do not block
publication; they tell you exactly which cells are blank and why.</p>
<h2>Row-level flags</h2>
<div class="panel"><table><thead><tr><th>Flag</th><th>Rows</th><th>Sports</th><th>Example source</th></tr></thead>
<tbody>{''.join(flag_rows)}</tbody></table></div>
<h2>Rows with no originated line</h2>
<div class="panel"><table><thead><tr><th>Sport</th><th>Match</th><th>Start</th><th>Listing source</th><th>Why</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(r["sport"])}</td><td>{esc(r["matchup"])}</td>'
         f'<td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{source_cell(r)}</td>'
         f'<td class="small">{esc("; ".join(r.get("flags", [])))}</td></tr>'
         for r in rows if not r["markets"])}
</tbody></table></div>
<h2>Repository defects</h2>
<p class="lead">The full list, with severities and manual-review links, is on <a href="review.html">Repo review</a>.
The most urgent one: a peer board committed gzip payloads with a <span class="mono">.html</span> extension on
23 October, which makes <span class="mono">scripts/audit_publication.py</span> fail on main. It is logged here for
the repository owner to fix; this board has not edited another session's data.</p>
"""
    (OUT / "flagged.html").write_text(page("Flagged for review", body, "flagged.html"))

    # verification page placeholder (verify.py rewrites it with the real result)
    body = """<h1>Verification</h1><p class="lead">Run <span class="mono">scripts/session-ed4c358c/verify.py</span>
to regenerate this page with the current check results.</p>"""
    (OUT / "verification.html").write_text(page("Verification", body, "verification.html"))

    print(f"built {len(list(OUT.rglob('*.html')))} pages in {OUT}")
    return 0


def render_pred(p: dict) -> str:
    srcs = " · ".join(f'<a href="{esc(s["url"])}" target="_blank" rel="noopener">{esc(s["name"])}</a>'
                      for s in p["sources"])
    am = p.get("fair_american")
    price = f'{am:+d}' if isinstance(am, int) else "n/a"
    prob = f'{p["fair_prob"]*100:.1f}%' if isinstance(p.get("fair_prob"), (int, float)) else "n/a"
    return f"""<div class="pred" id="{esc(p['row_id'])}">
<h3>{esc(p['matchup'])}</h3>
<div class="meta">{esc(p['sport'])} · {esc(p['competition'])} · {esc(p['start_utc'][:16].replace('T',' '))} UTC ·
{conf_chip(p['confidence'])} · {p['words']} words</div>
<div class="txt">{esc(p['text'])}</div>
<div class="src"><span class="sel">{esc(p['market'])}: {esc(p['selection'])}</span>
&nbsp;our fair price {esc(price)} ({esc(prob)})
<br>Facts from: {srcs}</div></div>"""


if __name__ == "__main__":
    raise SystemExit(main())

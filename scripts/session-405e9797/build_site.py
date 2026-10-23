#!/usr/bin/env python3
"""Board AR — static dashboard build.

Reads the desk, the prediction bank, the flag register and the repository review, then
writes a self-contained site under session-405e9797/:

    index.html              executive summary + coverage dashboard
    sports/<slug>.html      one page per covered sport
    flagged.html            every flag + every short-priced High play
    review.html             repository review findings
    methodology.html        pricing rules, parameters, sources
    data.json               everything the pages are built from
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-405e9797"
OUT = ROOT / "session-405e9797"

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}

STATUS_NOTE = {
    "Golf": "No Golf event was present on the OLBG hub in this capture, so there is nothing to price.",
    "Volleyball": "Italian SuperLega fixtures priced from the official league table; other leagues are listing-only.",
    "Rugby Union": "United Rugby Championship, priced from the official URC table.",
    "Cricket": "Listed fixtures could not be tied to a numeric official feed; every row is blank and flagged.",
    "Snooker": "Northern Ireland Open ties priced from the WST match feed and world ranking.",
    "Darts": "European Championship ties listed; the PDC match host did not resolve, so no price is published.",
    "Baseball": "World Series games priced from the MLB Stats API records.",
    "Gaelic Sports": "Cork final is confirmed on the official Cork GAA fixture page but no official form table exists.",
    "Greyhounds": "Race fields are not published by the GBGB results service, so no price is published.",
    "Tennis": "WTA and ATP matches priced from the official tour feeds and order-of-play sheets.",
    "Motor Racing": "United States Grand Prix priced from the official F1 drivers' standings.",
    "Handball": "Danish Betoro Herreligaen priced from the official league table.",
    "Ice Hockey": "NHL and Liiga priced from official schedules and standings.",
    "Basketball": "EuroLeague and EuroCup priced from the official competition feed.",
    "Rugby League": "Only 2027 futures were listed, so no in-window match exists to price.",
}

CSS = """
:root{--bg:#0b1220;--panel:#121a2b;--panel2:#16223a;--ink:#e8eefc;--mut:#93a3c4;--line:#24314b;
--acc:#5eead4;--hi:#34d399;--md:#fbbf24;--lo:#f87171;--link:#7dd3fc}
*{box-sizing:border-box}
body{margin:0;background:linear-gradient(180deg,#0b1220,#0d1626 40%,#0b1220);color:var(--ink);
font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial}
a{color:var(--link);text-decoration:none}a:hover{text-decoration:underline}
header{padding:28px 22px 10px;max-width:1180px;margin:0 auto}
h1{margin:0 0 6px;font-size:26px;letter-spacing:.2px}
h2{margin:30px 0 10px;font-size:19px}
h3{margin:18px 0 8px;font-size:16px;color:#cfe0ff}
.sub{color:var(--mut);font-size:13.5px}
nav{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0 0;font-size:14px}
main{max-width:1180px;margin:0 auto;padding:0 22px 60px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.card .k{font-size:26px;font-weight:700;color:var(--acc)}
.card .l{color:var(--mut);font-size:12.5px;text-transform:uppercase;letter-spacing:.6px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
border-radius:12px;overflow:hidden;font-size:13.6px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--panel2);color:#cfe0ff;font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.4px}
tr:last-child td{border-bottom:none}
tr:hover td{background:#16223a55}
.pill{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:700;letter-spacing:.3px}
.hi{background:#0d3b2e;color:var(--hi);border:1px solid #1d6b52}
.md{background:#3a2c0b;color:var(--md);border:1px solid #6b5312}
.lo{background:#3b1212;color:var(--lo);border:1px solid #6b2020}
.none{background:#1b2436;color:var(--mut);border:1px solid var(--line)}
.mut{color:var(--mut)}
.mono{font-variant-numeric:tabular-nums}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--acc);
border-radius:10px;padding:12px 14px;margin:12px 0}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
footer{max-width:1180px;margin:0 auto;padding:0 22px 40px;color:var(--mut);font-size:12.5px}
.tag{font-size:11.5px;color:var(--mut);border:1px solid var(--line);border-radius:8px;padding:1px 6px}
"""


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def money(am):
    if am is None:
        return ""
    return f"+{am}" if am > 0 else str(am)


def conf_pill(c):
    cls = {"High": "hi", "Medium": "md", "Low": "lo"}.get(c or "", "none")
    return f'<span class="pill {cls}">{esc(c or "—")}</span>'


def page(title: str, body: str, rel: str = "") -> str:
    nav = (f'<nav><a href="{rel}index.html">Dashboard</a>'
           f'<a href="{rel}coverage.html">Coverage</a>'
           f'<a href="{rel}picks.html">All picks</a>'
           f'<a href="{rel}flagged.html">Flagged for review</a>'
           f'<a href="{rel}review.html">Repository review</a>'
           f'<a href="{rel}methodology.html">Method</a></nav>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · Board AR</title><link rel="stylesheet" href="{rel}assets/site.css"></head>
<body><header><h1>{esc(title)}</h1>
<div class="sub">Board AR · session 405e9797 · 23 October 2026 · 15-sport scope</div>{nav}</header>
<main>{body}</main>
<footer>Every price on this site is originated by this desk from the official figures quoted on the row.
Nothing is copied from a bookmaker. Rows without an official numeric input stay blank and are listed on the
flagged page.</footer></body></html>"""


def pick_table(rows, preds, limit=None, show_note=False):
    out = ['<table><thead><tr><th>Start (UTC)</th><th>Match</th><th>Selection</th>'
           '<th>Our price</th><th>Chance</th><th>Confidence</th><th>Source</th></tr></thead><tbody>']
    for r in rows[:limit] if limit else rows:
        p = r.get("pick") or {}
        pred = preds.get("notes", {}).get(r["id"])
        src = (f'<a href="{esc(r["official_url"])}" rel="noopener">official</a>'
               if r.get("official_url") else '<span class="mut">—</span>')
        note = ""
        if show_note and pred:
            note = f'<div class="sub" style="margin-top:6px">{esc(pred["text"])}</div>'
        out.append(
            f'<tr><td class="mono">{esc(r["start_utc"][:16].replace("T", " ") or "—")}</td>'
            f'<td><strong>{esc(r["matchup"])}</strong>{note}'
            f'<div class="sub">{esc(r.get("competition",""))}{(" · " + esc(r["round"])) if r.get("round") else ""}</div></td>'
            f'<td><strong>{esc(p.get("selection",""))}</strong><div class="sub">{esc(p.get("market",""))}'
            f'{(" · " + esc(p.get("line"))) if p.get("line") is not None else ""}</div></td>'
            f'<td class="mono">{esc(money(p.get("american")))}</td>'
            f'<td class="mono">{p.get("prob",0)*100:.1f}%</td>'
            f'<td>{conf_pill(p.get("confidence"))}</td><td>{src}</td></tr>')
    out.append("</tbody></table>")
    return "".join(out)


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    flg = json.loads((DATA / "flagged.json").read_text())
    review = json.loads((DATA / "review.json").read_text()) if (DATA / "review.json").exists() else {"findings": []}
    rows = desk["rows"]
    c = desk["counts"]

    OUT.mkdir(exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets" / "site.css").write_text(CSS)

    high = [r for r in rows if (r.get("pick") or {}).get("confidence") == "High" and r["pick"].get("in_window")]
    high.sort(key=lambda r: (-(r["pick"]["prob"]), r["start_utc"]))
    short_high = [r for r in rows if (r.get("pick_alt") or {}).get("confidence") == "High"
                  and not r["pick_alt"].get("in_window")]
    top = high[:12]

    cards = f"""<div class="cards">
<div class="card"><div class="k">{c['rows']}</div><div class="l">matches listed</div></div>
<div class="card"><div class="k">{c['priced']}</div><div class="l">priced by this desk</div></div>
<div class="card"><div class="k">{c['high']}</div><div class="l">high-confidence</div></div>
<div class="card"><div class="k">{len(short_high)}</div><div class="l">high but shorter than -250</div></div>
<div class="card"><div class="k">{len(flg['flags'])}</div><div class="l">flagged items</div></div>
<div class="card"><div class="k">{c['markets']}</div><div class="l">markets originated</div></div>
</div>"""

    cover_rows = []
    for s in SPORTS:
        b = c["by_sport"][s]
        link = f'<a href="sports/{SLUG[s]}.html">{esc(s)}</a>' if b["rows"] else esc(s)
        cover_rows.append(
            f'<tr><td>{link}</td><td class="mono">{b["rows"]}</td><td class="mono">{b["priced"]}</td>'
            f'<td class="mono">{b["high"]}</td><td>{conf_pill("High" if b["high"] else ("Medium" if b["priced"] else ""))}</td>'
            f'<td class="mut">{esc(STATUS_NOTE[s])}</td></tr>')
    coverage = ("<table><thead><tr><th>Sport</th><th>Rows</th><th>Priced</th><th>High</th>"
                "<th>Best level</th><th>Status</th></tr></thead><tbody>" + "".join(cover_rows) + "</tbody></table>")

    exec_body = f"""
<div class="note"><strong>Today's headline plays.</strong> The desk originated {c['markets']:,} markets across
{c['rows']} listed matches. {c['priced']} matches carry a price built from an official table, schedule or feed;
{c['high']} of those reach the top confidence band and {len(high)} sit inside the −250 to +10,000 window the
brief asks us to work in. Every row below links to the official page the numbers came from.</div>
{cards}
<h2>Highest-confidence picks</h2>
{pick_table(top, preds, show_note=True)}
<p class="sub">Full list on the <a href="picks.html">all picks</a> page. Short-priced High calls are on the
<a href="flagged.html">flagged page</a> with the arithmetic that excludes them from the window.</p>
<h2>Coverage by sport</h2>
{coverage}
<h2>How the board is organised</h2>
<div class="grid2">
<div class="note"><strong>Data only from official pages.</strong> Each priced row names the governing body,
league or tour page it was built from, and the captured file is hash-checked against the run manifest before
use. Bookmaker listings are used only to see which matches exist.</div>
<div class="note"><strong>Gaps are published, not filled.</strong> Where an official page did not publish a
readable number, the row stays blank and appears on the <a href="flagged.html">flagged page</a>. Nothing is
inferred to make a table look complete.</div>
</div>
"""

    (OUT / "index.html").write_text(page("Board AR — today's originated book", exec_body))

    # ---- picks page
    all_priced = [r for r in rows if r.get("priced") and r.get("pick")]
    all_priced.sort(key=lambda r: (SPORTS.index(r["sport"]), -r["pick"]["prob"]))
    picks_body = f"""<div class="note">Every priced match, grouped by sport. Prices are this desk's fair lines
derived from the official numbers quoted in each row's evidence; they are not bookmaker prices.</div>
{pick_table(all_priced, preds, show_note=False)}"""
    (OUT / "picks.html").write_text(page("All originated picks", picks_body))

    # ---- coverage page (same table plus per-sport notes)
    cov_body = f"""<div class="note">All fifteen sports in scope, whether or not OLBG listed a match today.
The desk never pads a sport: if nothing could be priced, the reason is written out here and the items are
flagged.</div>{coverage}
<h2>What each sport is missing</h2>
<ul>{''.join(f'<li><strong>{esc(s)}</strong> — {esc(STATUS_NOTE[s])}</li>' for s in SPORTS)}</ul>"""
    (OUT / "coverage.html").write_text(page("Coverage", cov_body))

    # ---- flagged page
    flag_rows = []
    for f in flg["flags"]:
        flag_rows.append(
            f'<tr><td class="mono">{esc(f["id"])}</td><td>{esc(f["sport"])}</td><td>{esc(f["title"])}</td>'
            f'<td class="mut">{esc(f["detail"])}</td><td>{esc(f["severity"])}</td>'
            f'<td><a href="{esc(f["manual_url"])}" rel="noopener">check</a></td></tr>')
    short_rows = []
    for r in short_high:
        alt = r["pick_alt"]
        short_rows.append(
            f'<tr><td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td><td>{esc(r["matchup"])}</td>'
            f'<td>{esc(alt["selection"])}</td><td class="mono">{esc(money(alt["american"]))}</td>'
            f'<td class="mono">{alt["prob"]*100:.1f}%</td>'
            f'<td class="mut">Chance above 70% but the fair price is shorter than −250, outside the brief\'s window.</td>'
            f'<td><a href="{esc(r["official_url"])}" rel="noopener">official</a></td></tr>')
    listing_rows = []
    for r in rows:
        if r.get("listing_only"):
            ol = r.get("olbg") or {}
            listing_rows.append(
                f'<tr><td>{esc(r["sport"])}</td><td>{esc(r["matchup"])}</td>'
                f'<td class="mono">{esc(r["start_utc"][:16].replace("T"," "))}</td>'
                f'<td><a href="{esc(ol.get("event_url",""))}" rel="noopener">listing</a></td>'
                f'<td class="mut">{esc(r["inputs_summary"])}</td></tr>')
    flagged_body = f"""<div class="note"><strong>This page is deliberately incomplete.</strong> It carries the
items this desk could not confirm against an official page, plus the High-confidence calls whose fair price is
shorter than −250. Nothing here is hidden from the main tables; it is listed again with the reason.</div>
<h2>High confidence, price outside the window ({len(short_high)})</h2>
<table><thead><tr><th>Start (UTC)</th><th>Match</th><th>Selection</th><th>Price</th><th>Chance</th>
<th>Why it is here</th><th>Source</th></tr></thead><tbody>{''.join(short_rows)}</tbody></table>
<h2>Register of flags ({len(flg['flags'])})</h2>
<table><thead><tr><th>ID</th><th>Sport</th><th>Issue</th><th>Detail</th><th>Severity</th><th>Manual check</th>
</tr></thead><tbody>{''.join(flag_rows)}</tbody></table>
<h2>Listing-only rows ({sum(1 for r in rows if r.get("listing_only"))})</h2>
<table><thead><tr><th>Sport</th><th>Event</th><th>Start (UTC)</th><th>OLBG</th><th>Why no price</th></tr></thead>
<tbody>{''.join(listing_rows)}</tbody></table>"""
    (OUT / "flagged.html").write_text(page("Flagged for review", flagged_body))

    # ---- review page
    frows = []
    for f in review.get("findings", []):
        frows.append(
            f'<tr><td class="mono">{esc(f.get("id",""))}</td><td>{esc(f.get("area",""))}</td>'
            f'<td>{esc(f.get("finding",""))}</td><td class="mut">{esc(f.get("impact",""))}</td>'
            f'<td>{esc(f.get("status",""))}</td>'
            f'<td><a href="{esc(f.get("source_url",""))}" rel="noopener">official</a></td></tr>')
    review_body = f"""<div class="note">{esc(review.get("summary",""))}</div>
<h2>Findings</h2>
<table><thead><tr><th>ID</th><th>Area</th><th>Finding</th><th>Impact on this desk</th><th>Status</th>
<th>Source</th></tr></thead><tbody>{''.join(frows)}</tbody></table>
<h2>What was checked</h2>
<ul>{''.join(f"<li>{esc(x)}</li>" for x in review.get("checks", []))}</ul>"""
    (OUT / "review.html").write_text(page("Repository review", review_body))

    # ---- methodology
    meth_body = f"""<div class="note">All lines are this desk's own fair prices: no margin, no bookmaker copy.
The parameters below are the ones actually used in the run that produced these pages.</div>
<h2>Confidence rule</h2>
<p>A pick is <span class="pill hi">High</span> when its chance is at least 70% and its fair American price sits
inside −250 to +10,000. <span class="pill md">Medium</span> is 55–70%. Below that the row is
<span class="pill lo">Low</span>. A selection above 70% whose fair price is shorter than −250 is never relabelled:
it is published as High on the flagged page, with the arithmetic.</p>
<h2>Pricing blocks</h2>
<table><thead><tr><th>Sport</th><th>Model</th><th>Markets</th></tr></thead><tbody>
<tr><td>Ice Hockey</td><td>Poisson goals from shrunk season scoring rates, home allowance 1.045/0.955; Liiga shares the structure.</td>
<td>Money line, puck line ±1.5, handicap 2.5/3.5, totals ±1.0/±0.5</td></tr>
<tr><td>Baseball</td><td>Poisson runs from season runs scored/allowed, home allowance 1.02/0.98.</td>
<td>Money line, run line ±1.5, handicap 2.5/3.5, totals ±1.0/±0.5</td></tr>
<tr><td>Basketball</td><td>Normal margin from shrunk points for/against, home allowance +1.4 (EuroLeague/EuroCup).</td>
<td>Money line, handicap ladder 2.5–10.5, totals ±3.5/±6.5</td></tr>
<tr><td>Rugby Union</td><td>Points-based rating from the official URC table plus a 5.5% draw allowance.</td>
<td>Money line, handicap 3.5/6.5/9.5/13.5, totals ±5.5</td></tr>
<tr><td>Handball</td><td>Normal margin blending shrunk goal rates, league points per game and goal difference.</td>
<td>Money line, handicap 2.5–8.5, totals ±4.5</td></tr>
<tr><td>Tennis</td><td>Logistic on seed gap and the week's completed results (WTA feed), plus game handicaps and totals;
ATP ties from the official order-of-play sheets.</td><td>Match winner, game handicap 2.5–6.5, total games</td></tr>
<tr><td>Snooker</td><td>Frame probability from the log prize-money gap on the official world ranking, expanded to a
best-of-n match.</td><td>Match winner, frame handicap, total frames</td></tr>
<tr><td>Motor Racing</td><td>Softmax over official championship points.</td><td>Race winner outright</td></tr>
<tr><td>Volleyball</td><td>Set-margin read from the official SuperLega table, capped at Medium because the sample is one round.</td>
<td>Match winner, set handicap</td></tr>
</tbody></table>
<h2>Sources used</h2>
<ul>
<li>NHL schedule and standings (api-web.nhle.com, nhl.com), Liiga result service.</li>
<li>MLB Stats API schedule and standings.</li>
<li>EuroLeague / EuroCup official game feeds.</li>
<li>United Rugby Championship official table.</li>
<li>tophaandbold.dk official Danish standings.</li>
<li>WTA official tournament feed; ATP order-of-play PDFs on protennislive.com.</li>
<li>WST match and ranking services (wstservices.co.uk); PDC ranking service.</li>
<li>Formula 1 official drivers' standings.</li>
<li>Lega Pallavolo Serie A official standings.</li>
<li>OLBG sport hubs for the listing of which matches exist (never for prices).</li>
</ul>
<h2>Reproducing the run</h2>
<p class="mut mono">python3 scripts/session-405e9797/re_olbg.py<br>
python3 scripts/session-405e9797/originate.py<br>
python3 scripts/session-405e9797/predictions.py<br>
python3 scripts/session-405e9797/build_site.py<br>
python3 scripts/session-405e9797/verify.py</p>"""
    (OUT / "methodology.html").write_text(page("Method and parameters", meth_body))

    # ---- per-sport pages
    for s in SPORTS:
        sr = [r for r in rows if r["sport"] == s]
        priced = [r for r in sr if r.get("priced") and r.get("pick")]
        priced.sort(key=lambda r: -r["pick"]["prob"])
        unpriced = [r for r in sr if not r.get("priced")]
        sflags = [f for f in flg["flags"] if f["sport"] == s]
        b = c["by_sport"][s]
        body = [f'<div class="note">{esc(STATUS_NOTE[s])}</div>',
                f'<div class="cards"><div class="card"><div class="k">{b["rows"]}</div><div class="l">listed</div></div>'
                f'<div class="card"><div class="k">{b["priced"]}</div><div class="l">priced</div></div>'
                f'<div class="card"><div class="k">{b["high"]}</div><div class="l">high</div></div></div>']
        if priced:
            body.append("<h2>Priced matches</h2>")
            body.append(pick_table(priced, preds, show_note=True))
        else:
            body.append('<div class="note">No match in this sport could be priced from an official numeric source '
                        'today. The listing is kept below so the gap is visible and checkable.</div>')
        if unpriced:
            body.append("<h2>Listed, not priced</h2><table><thead><tr><th>Event</th><th>Start (UTC)</th>"
                        "<th>OLBG market</th><th>Listing</th></tr></thead><tbody>")
            for r in unpriced:
                ol = r.get("olbg") or {}
                body.append(f'<tr><td>{esc(r["matchup"])}</td>'
                            f'<td class="mono">{esc(r["start_utc"][:16].replace("T"," ") or "—")}</td>'
                            f'<td>{esc(ol.get("market",""))} {esc(ol.get("selection",""))}</td>'
                            f'<td><a href="{esc(ol.get("event_url",""))}" rel="noopener">listing</a></td></tr>')
            body.append("</tbody></table>")
        if sflags:
            body.append("<h2>Flags on this sport</h2><ul>")
            for f in sflags:
                body.append(f'<li><strong>{esc(f["id"])}</strong> {esc(f["title"])} — {esc(f["detail"])} '
                            f'<a href="{esc(f["manual_url"])}" rel="noopener">check</a></li>')
            body.append("</ul>")
        (OUT / "sports" / f"{SLUG[s]}.html").write_text(
            page(f"{s}", "".join(body), rel="../"))

    payload = {
        "schema": "board-ar-site/1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "counts": c,
        "sports": SPORTS,
        "rows": rows,
        "flags": flg["flags"],
        "predictions": preds["notes"],
        "review": review,
    }
    (OUT / "data.json").write_text(json.dumps(payload, indent=1))
    print(json.dumps({"pages": len(SPORTS) + 6, "rows": len(rows), "priced": c["priced"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

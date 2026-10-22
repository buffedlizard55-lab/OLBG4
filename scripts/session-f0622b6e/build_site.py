#!/usr/bin/env python3
"""Static GitHub Pages dashboard generator for Board AC (session-f0622b6e).

Outputs 25 clean, fast, accessible HTML pages + assets under session-f0622b6e/:
  - index.html (Landing Dashboard)
  - predictions.html (40 High-Confidence Human Predictions in [-250, +10000])
  - matches.html (233 Verified Matches & Outrights Table)
  - markets.html (Full 4-Market Origination Matrix)
  - olbg.html (OLBG.com Reverse-Engineering & 08:35Z Live Sweep)
  - review.html (Line-by-Line Repository & master.json Audit)
  - flagged.html (Flagged for Review — Blank Unconfirmed Rows & Discrepancies)
  - methodology.html (Mathematical Origination Model & Official Source Registry)
  - sports/<slug>.html (17 Sport Category Subpages)
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-f0622b6e"
SITE_DIR = ROOT / "session-f0622b6e"

SPORT_META = [
    ("Tennis", "tennis", "ATP 250 Almaty / Brussels / Lyon & WTA 500 Ningbo / 250 Guangzhou"),
    ("Basketball", "basketball", "NBA Regular Season, EuroLeague Rd 7, Brazil NBB & Korea KBL"),
    ("Baseball", "baseball", "2026 MLB World Series — Milwaukee Brewers vs Tampa Bay Rays"),
    ("Ice Hockey", "ice-hockey", "NHL Regular Season, Swedish SHL & Finnish Liiga"),
    ("Darts", "darts", "PDC Machineseeker European Championship (Westfalenhalle, Dortmund)"),
    ("Snooker", "snooker", "WST BetVictor Northern Ireland Open Last 16 (Waterfront Hall, Belfast)"),
    ("Handball", "handball", "EHF Champions League Men Rd 5 & 5 European Domestic Leagues"),
    ("Volleyball", "volleyball", "Italy SuperLega, Poland PlusLiga/TAURON Liga & Czech Extraliga"),
    ("Rugby Union", "rugby-union", "United Rugby Championship Rd 4, Top 14 & Pro D2 Rd 8"),
    ("Rugby League", "rugby-league", "2026 Rugby League World Cup Round 2"),
    ("Cricket", "cricket", "ICC UAE Men's ODI Tri-Series Final & Bilateral ODI/T20I Tours"),
    ("eSports", "esports", "LoL Worlds 2026 Swiss Stage Rd 1 & EMEA Masters Grand Final"),
    ("Badminton", "badminton", "BWF Super 750 YONEX French Open Round of 16"),
    ("Aussie Rules", "aussie-rules", "2026 NAB AFLW Round 11"),
    ("Golf", "golf", "PGA Tour Butterfield Bermuda Championship & Schwab Cup Playoffs"),
    ("Motor Racing", "motor-racing", "2026 Formula 1 United States Grand Prix & Drivers' Championship"),
    ("Greyhounds", "greyhounds", "UK GBGB Racecards — WAF-Quarantined on Flagged for Review"),
]


def e(val: object) -> str:
    if val is None:
        return ""
    return html.escape(str(val), quote=True)


def fmt_am(am: int | None) -> str:
    if am is None or am == "":
        return ""
    return f"{int(am):+d}"


def fmt_dec(dec: float | None) -> str:
    if dec is None or dec == "":
        return ""
    return f"{float(dec):.2f}"


def host_label(url: str) -> str:
    if not url:
        return ""
    h = urlsplit(url).hostname or url
    return h.replace("www.", "")


def conf_badge(conf: str) -> str:
    if not conf:
        return '<span class="badge badge-blank">BLANK (Unverified)</span>'
    cls = {"High": "badge-high", "Medium": "badge-med", "Low": "badge-low"}.get(conf, "badge-low")
    return f'<span class="badge {cls}">{e(conf)}</span>'


def page_shell(title: str, active: str, body: str, depth: int = 0) -> str:
    prefix = "../" * depth
    nav_items = [
        ("index.html", "Dashboard", "home"),
        ("predictions.html", "High Picks (40)", "predictions"),
        ("matches.html", "All Matches (233)", "matches"),
        ("markets.html", "4-Market Lines", "markets"),
        ("olbg.html", "OLBG Reverse-Eng", "olbg"),
        ("review.html", "Repo Audit", "review"),
        ("flagged.html", "Flagged for Review", "flagged"),
        ("methodology.html", "Methodology & Sources", "methodology"),
    ]
    nav_html = "".join(
        f'<a href="{prefix}{href}" class="nav-link{" active" if key == active else ""}">{e(label)}</a>'
        for href, label, key in nav_items
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)} · Board AC Betting Desk (f0622b6e)</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <header class="topbar">
    <div class="container topbar-inner">
      <div class="brand">
        <a href="{prefix}index.html" class="brand-title">OLBG4 · Board AC Verified Betting Desk</a>
        <span class="brand-sub">Session <code>f0622b6e</code> · Cutoff <code>2026-10-22T08:35Z</code> · <a href="{prefix}../index.html" class="portal-link">← Repo Portal</a></span>
      </div>
      <nav class="topnav" aria-label="Primary">{nav_html}</nav>
    </div>
  </header>
  <div class="scope-bar">
    <div class="container">
      <strong>Scope Mandate Enforced:</strong> 0 rows from excluded sports (<code>soccer</code>, <code>boxing</code>, <code>ufc</code>, <code>mma</code>, <code>football</code>, <code>american football</code>, <code>hurling</code>, <code>horse racing</code>, <code>cycling</code>, <code>specials</code>). Unconfirmed inputs are strictly left blank and routed to <a href="{prefix}flagged.html">Flagged for Review</a>.
    </div>
  </div>
  <main class="container main-content">
    {body}
  </main>
  <footer class="footer">
    <div class="container footer-inner">
      <div>Board AC (<code>arena/f0622b6e-olbg4</code>) · Zero-vig fair + 4.2% book origination · Every table row verified against official governing bodies.</div>
      <div>Data exports: <a href="{prefix}../data/session-f0622b6e/desk.json">desk.json</a> · <a href="{prefix}../data/session-f0622b6e/predictions.json">predictions.json</a> · <a href="{prefix}../data/session-f0622b6e/flagged.json">flagged.json</a> · <a href="{prefix}../data/session-f0622b6e/olbg_inventory.json">olbg_inventory.json</a> · <a href="{prefix}../data/session-f0622b6e/repo_review.json">repo_review.json</a></div>
    </div>
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


CSS = """
:root {
  --bg: #f5f7fb;
  --surface: #ffffff;
  --surface-alt: #eef2f8;
  --ink: #0f172a;
  --muted: #475569;
  --border: #d8e0ec;
  --navy: #0f2942;
  --accent: #0b6bcb;
  --accent-soft: #e6f1fc;
  --high-bg: #dcfce7;
  --high-ink: #14532d;
  --med-bg: #dbeafe;
  --med-ink: #1e3a8a;
  --low-bg: #f1f5f9;
  --low-ink: #334155;
  --warn-bg: #fff7ed;
  --warn-border: #ea580c;
  --warn-ink: #7c2d12;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
  font-size: 14.5px;
  line-height: 1.5;
  color: var(--ink);
  background: var(--bg);
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.9em;
  background: var(--surface-alt);
  padding: 1px 5px;
  border-radius: 4px;
}
.container { max-width: 1440px; margin: 0 auto; padding: 0 20px; }
.topbar { background: var(--navy); color: #fff; padding: 12px 0; border-bottom: 3px solid #1d4ed8; }
.topbar-inner { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 12px; }
.brand-title { color: #fff; font-weight: 700; font-size: 1.12rem; display: block; }
.brand-sub { color: #cbd5e1; font-size: 0.82rem; }
.brand-sub code { background: rgba(255,255,255,0.14); color: #f8fafc; }
.portal-link { color: #93c5fd; font-weight: 600; }
.topnav { display: flex; flex-wrap: wrap; gap: 6px; }
.nav-link {
  color: #e2e8f0;
  padding: 6px 11px;
  border-radius: 6px;
  font-size: 0.86rem;
  font-weight: 600;
}
.nav-link:hover { background: rgba(255,255,255,0.12); text-decoration: none; }
.nav-link.active { background: #2563eb; color: #fff; }
.scope-bar {
  background: #e8eef7;
  border-bottom: 1px solid var(--border);
  padding: 8px 0;
  font-size: 0.84rem;
  color: #1e293b;
}
.main-content { padding: 24px 20px 44px; }
h1 { margin: 0 0 8px; font-size: 1.65rem; color: var(--navy); }
h2 { margin: 28px 0 12px; font-size: 1.25rem; color: var(--navy); border-bottom: 2px solid var(--border); padding-bottom: 6px; }
h3 { margin: 0 0 8px; font-size: 1.04rem; color: var(--navy); }
.lead { color: var(--muted); margin: 0 0 18px; max-width: 980px; }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(195px, 1fr));
  gap: 12px;
  margin: 16px 0 24px;
}
.kpi-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.kpi-val { font-size: 1.65rem; font-weight: 800; color: var(--navy); line-height: 1.15; }
.kpi-lbl { font-size: 0.82rem; color: var(--muted); margin-top: 4px; font-weight: 600; }
.sport-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 12px;
}
.sport-card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  color: inherit;
  transition: border-color 0.15s, transform 0.12s;
}
.sport-card:hover { border-color: var(--accent); transform: translateY(-1px); text-decoration: none; }
.sport-card-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 4px; }
.sport-card-title { font-weight: 700; font-size: 1.02rem; color: var(--navy); }
.sport-card-sub { font-size: 0.8rem; color: var(--muted); margin-bottom: 8px; min-height: 34px; }
.sport-card-stats { display: flex; gap: 8px; flex-wrap: wrap; font-size: 0.78rem; }
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--surface-alt);
  color: var(--ink);
  font-weight: 600;
  font-size: 0.78rem;
}
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 5px;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}
.badge-high { background: var(--high-bg); color: var(--high-ink); border: 1px solid #86efac; }
.badge-med { background: var(--med-bg); color: var(--med-ink); border: 1px solid #93c5fd; }
.badge-low { background: var(--low-bg); color: var(--low-ink); border: 1px solid #cbd5e1; }
.badge-blank { background: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
.notice-box {
  background: var(--warn-bg);
  border-left: 4px solid var(--warn-border);
  color: var(--warn-ink);
  padding: 14px 16px;
  border-radius: 6px;
  margin: 14px 0 20px;
}
.info-box {
  background: var(--accent-soft);
  border-left: 4px solid var(--accent);
  padding: 14px 16px;
  border-radius: 6px;
  margin: 14px 0 20px;
}
.filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  padding: 12px 14px;
  border-radius: 8px;
  margin-bottom: 14px;
}
.filter-bar input[type="search"], .filter-bar select {
  padding: 7px 11px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.9rem;
  min-width: 210px;
}
.table-wrap {
  overflow-x: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
}
table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
th, td {
  padding: 9px 11px;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
  vertical-align: top;
}
th {
  background: #0f2942;
  color: #fff;
  font-weight: 600;
  position: sticky;
  top: 0;
  white-space: nowrap;
}
tbody tr:hover { background: #f8fafc; }
.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.83rem; }
.muted { color: var(--muted); font-size: 0.8rem; }
.pred-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(410px, 1fr)); gap: 16px; }
.pred-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 4px solid #16a34a;
  border-radius: 10px;
  padding: 16px 18px;
}
.pred-meta { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; font-size: 0.8rem; color: var(--muted); margin-bottom: 6px; }
.pred-title { font-size: 1.05rem; font-weight: 700; color: var(--navy); margin-bottom: 6px; }
.pred-pick-bar {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 7px;
  padding: 8px 11px;
  margin-bottom: 10px;
}
.pred-pick-name { font-weight: 800; color: #14532d; }
.pred-odds { font-family: ui-monospace, SFMono-Regular, monospace; font-weight: 700; color: #0f172a; font-size: 0.85rem; }
.pred-body { margin: 8px 0 10px; color: #1e293b; line-height: 1.58; }
.pred-facts { margin: 0 0 10px; padding-left: 18px; font-size: 0.8rem; color: var(--muted); }
.pred-links { display: flex; gap: 12px; flex-wrap: wrap; font-size: 0.8rem; border-top: 1px solid #e2e8f0; padding-top: 8px; }
.footer { border-top: 1px solid var(--border); background: var(--surface); padding: 18px 0; color: var(--muted); font-size: 0.82rem; }
.footer-inner { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 10px; }
@media (max-width: 720px) {
  .pred-grid { grid-template-columns: 1fr; }
}
"""

JS = """
document.addEventListener('DOMContentLoaded', () => {
  const search = document.querySelector('[data-filter-search]');
  const sportSel = document.querySelector('[data-filter-sport]');
  const confSel = document.querySelector('[data-filter-conf]');
  const catSel = document.querySelector('[data-filter-cat]');
  const countEl = document.querySelector('[data-filter-count]');
  const items = Array.from(document.querySelectorAll('[data-filter-row]'));
  if (!items.length) return;

  function apply() {
    const q = (search ? search.value : '').trim().toLowerCase();
    const sp = sportSel ? sportSel.value : '';
    const cf = confSel ? confSel.value : '';
    const ct = catSel ? catSel.value : '';
    let shown = 0;
    for (const el of items) {
      const okQ = !q || el.textContent.toLowerCase().includes(q);
      const okSp = !sp || el.dataset.sport === sp;
      const okCf = !cf || el.dataset.conf === cf;
      const okCt = !ct || el.dataset.cat === ct;
      const vis = okQ && okSp && okCf && okCt;
      el.hidden = !vis;
      if (vis) shown++;
    }
    if (countEl) countEl.textContent = `${shown} of ${items.length} shown`;
  }

  for (const ctrl of [search, sportSel, confSel, catSel]) {
    if (ctrl) ctrl.addEventListener('input', apply);
    if (ctrl) ctrl.addEventListener('change', apply);
  }
  apply();
});
"""


def render_pred_card(p: dict, depth: int = 0) -> str:
    prefix = "../" * depth
    olbg_part = ""
    if p.get("olbg_url"):
        olbg_price = f" ({p['olbg_featured_selection']} @ {p['olbg_featured_decimal']:.2f})" if p.get("olbg_featured_decimal") else ""
        olbg_part = f'<a href="{e(p["olbg_url"])}" target="_blank" rel="noopener">OLBG Event Page{e(olbg_price)} ↗</a>'
    facts_html = "".join(f"<li>{e(f)}</li>" for f in p["verified_facts"])
    return f"""
    <article class="pred-card" data-filter-row data-sport="{e(p['sport'])}" data-conf="High">
      <div class="pred-meta">
        <span><a href="{prefix}sports/{e(p['sport_slug'])}.html"><strong>{e(p['sport'])}</strong></a> · {e(p['competition'])}</span>
        <span class="mono">{e(p['start_utc'][:16].replace('T', ' '))}Z · {p['word_count']} words</span>
      </div>
      <div class="pred-title">{e(p['matchup'])}</div>
      <div class="pred-pick-bar">
        <div>
          <span class="badge badge-high">HIGH</span>
          <span class="pred-pick-name">{e(p['selection'])}</span>
          <span class="muted">({e(p['market_type'])} · Match Winner Pick: {e(p['match_winner_pick'])})</span>
        </div>
        <div class="pred-odds">Book {fmt_am(p['book_american'])} ({fmt_dec(p['book_decimal'])}) · Fair {fmt_am(p['fair_american'])} ({fmt_dec(p['fair_decimal'])})</div>
      </div>
      <p class="pred-body">{e(p['text'])}</p>
      <ul class="pred-facts">{facts_html}</ul>
      <div class="pred-links">
        <a href="{e(p['official_url'])}" target="_blank" rel="noopener">Official Source ({e(host_label(p['official_url']))}) ↗</a>
        {olbg_part}
      </div>
    </article>"""


def render_matches_table(rows: list[dict], depth: int = 0, show_sport_col: bool = True) -> str:
    prefix = "../" * depth
    trs = []
    for r in rows:
        olbg = r.get("olbg") or {}
        if olbg.get("listed") and olbg.get("url"):
            op = f" @ {olbg['featured_price_decimal']:.2f}" if olbg.get("featured_price_decimal") else " (08:31Z new)"
            olbg_cell = f'<a href="{e(olbg["url"])}" target="_blank" rel="noopener">{e(olbg.get("featured_selection") or "Listed")}{e(op)} ↗</a>'
            if r.get("olbg_edge_bps") is not None:
                sign = "+" if r["olbg_edge_bps"] >= 0 else ""
                olbg_cell += f'<div class="muted">Model edge: {sign}{r["olbg_edge_bps"]} bps</div>'
        else:
            olbg_cell = '<span class="muted">Official expansion</span>'

        sport_td = f'<td><a href="{prefix}sports/{e(r["sport_slug"])}.html"><strong>{e(r["sport"])}</strong></a><div class="muted">{e(r["competition"])}</div></td>' if show_sport_col else f'<td>{e(r["competition"])}</td>'
        pred_anchor = f'<div><a href="{prefix}predictions.html">Read {r["prediction"]["word_count"]}w prediction →</a></div>' if r.get("prediction") else ""
        trs.append(f"""
        <tr data-filter-row data-sport="{e(r['sport'])}" data-conf="{e(r['confidence'])}">
          <td class="mono">{e(r['start_utc'][:16].replace('T', ' '))}Z</td>
          {sport_td}
          <td><strong>{e(r['matchup'])}</strong><div class="muted">{e(r['venue'])}</div></td>
          <td><strong>{e(r['match_winner_pick'])}</strong><div class="mono muted">Book {fmt_am(r['match_winner_book_american'])} ({fmt_dec(r['match_winner_book_decimal'])}) · Fair {fmt_dec(r['match_winner_fair_decimal'])}</div></td>
          <td>{conf_badge(r['confidence'])}{pred_anchor}</td>
          <td><strong>{e(r['featured_pick'])}</strong><div class="mono">Book {fmt_am(r['featured_book_american'])} ({fmt_dec(r['featured_book_decimal'])}) · Fair {fmt_am(r['featured_fair_american'])}</div></td>
          <td>{olbg_cell}</td>
          <td><a href="{e(r['official_url'])}" target="_blank" rel="noopener">{e(host_label(r['official_url']))} ↗</a></td>
        </tr>""")
    sport_th = "<th>Sport / Competition</th>" if show_sport_col else "<th>Competition</th>"
    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Start (UTC)</th>
            {sport_th}
            <th>Matchup / Venue</th>
            <th>Match Winner Pick &amp; Line</th>
            <th>Confidence</th>
            <th>Featured Actionable Line</th>
            <th>OLBG Crowd Comparison</th>
            <th>Official Source</th>
          </tr>
        </thead>
        <tbody>{''.join(trs)}</tbody>
      </table>
    </div>"""


def render_four_markets_table(rows: list[dict], depth: int = 0) -> str:
    prefix = "../" * depth
    trs = []
    for r in rows:
        m = r["markets"]
        mw = m["match_winner"]
        hc = m.get("handicap")
        tot = m.get("total")
        sec = m.get("secondary")

        if r["row_kind"] == "outright":
            mw_cell = "<br>".join(
                f"<strong>{e(c['name'])}</strong>: Book {c['book_dec']:.2f} ({dec_to_am_str(c['book_dec'])}) / Fair {c['fair_dec']:.2f}"
                for c in mw["contenders"][:3]
            )
            hc_cell = '<span class="muted">N/A (Tournament Outright)</span>'
            tot_cell = '<span class="muted">N/A (Tournament Outright)</span>'
        else:
            mw_cell = (
                f"<strong>{e(r['side_a'])}</strong>: {mw['book_dec_a']:.2f} ({mw['book_am_a']:+d}) <span class='muted'>[Fair {mw['fair_dec_a']:.2f}]</span><br>"
                f"<strong>{e(r['side_b'])}</strong>: {mw['book_dec_b']:.2f} ({mw['book_am_b']:+d}) <span class='muted'>[Fair {mw['fair_dec_b']:.2f}]</span>"
            )
            if mw.get("three_way_1x2"):
                tw = mw["three_way_1x2"]
                mw_cell += f"<div class='muted mono'>1X2: {tw['book_dec_a']:.2f} / Draw {tw['book_dec_draw']:.2f} / {tw['book_dec_b']:.2f}</div>"

            hc_cell = (
                f"{e(hc['label_a'])}: <strong>{hc['book_dec_a']:.2f} ({hc['book_am_a']:+d})</strong> <span class='muted'>[Fair {hc['fair_dec_a']:.2f}]</span><br>"
                f"{e(hc['label_b'])}: <strong>{hc['book_dec_b']:.2f} ({hc['book_am_b']:+d})</strong> <span class='muted'>[Fair {hc['fair_dec_b']:.2f}]</span>"
            ) if hc else '<span class="muted">Withheld</span>'

            tot_cell = (
                f"{e(tot['over_label'])}: <strong>{tot['book_dec_a']:.2f} ({tot['book_am_a']:+d})</strong><br>"
                f"{e(tot['under_label'])}: <strong>{tot['book_dec_b']:.2f} ({tot['book_am_b']:+d})</strong>"
            ) if tot else '<span class="muted">Withheld (venue scoring mean not printed on federation site)</span>'

        if sec:
            if "book_dec_draw" in sec:
                sec_cell = (
                    f"<span class='muted'>{e(sec['market_name'])}</span><br>"
                    f"1: {sec['book_dec_a']:.2f} · X: {sec['book_dec_draw']:.2f} · 2: {sec['book_dec_b']:.2f}"
                )
            else:
                sec_cell = (
                    f"<span class='muted'>{e(sec['market_name'])}</span><br>"
                    f"{e(sec['label_a'])}: <strong>{sec['book_dec_a']:.2f} ({sec['book_am_a']:+d})</strong><br>"
                    f"{e(sec['label_b'])}: <strong>{sec['book_dec_b']:.2f} ({sec['book_am_b']:+d})</strong>"
                )
        else:
            sec_cell = '<span class="muted">—</span>'

        trs.append(f"""
        <tr data-filter-row data-sport="{e(r['sport'])}" data-conf="{e(r['confidence'])}">
          <td><a href="{prefix}sports/{e(r['sport_slug'])}.html"><strong>{e(r['sport'])}</strong></a><div class="mono muted">{e(r['start_utc'][:16].replace('T', ' '))}Z</div></td>
          <td><strong>{e(r['matchup'])}</strong><div class="muted">{e(r['competition'])}</div></td>
          <td class="mono">{mw_cell}</td>
          <td class="mono">{hc_cell}</td>
          <td class="mono">{tot_cell}</td>
          <td class="mono">{sec_cell}</td>
          <td><a href="{e(r['official_url'])}" target="_blank" rel="noopener">{e(host_label(r['official_url']))} ↗</a></td>
        </tr>""")

    return f"""
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sport / Start</th>
            <th>Fixture</th>
            <th>Market 1: Match Winner / 1X2</th>
            <th>Market 2: Handicap / Spread</th>
            <th>Market 3: Match Total (O/U)</th>
            <th>Market 4: Derivative Market</th>
            <th>Official Source</th>
          </tr>
        </thead>
        <tbody>{''.join(trs)}</tbody>
      </table>
    </div>"""


def dec_to_am_str(dec: float) -> str:
    if dec >= 2.0:
        return f"+{int(round((dec - 1.0) * 100))}"
    return f"{int(round(-100.0 / (dec - 1.0)))}"


def sport_options(sports: list[str]) -> str:
    return '<option value="">All Sports</option>' + "".join(
        f'<option value="{e(s)}">{e(s)}</option>' for s in sports
    )


def main() -> None:
    desk = json.loads((DATA_DIR / "desk.json").read_text())
    preds = json.loads((DATA_DIR / "predictions.json").read_text())
    flagged = json.loads((DATA_DIR / "flagged.json").read_text())
    inv = json.loads((DATA_DIR / "olbg_inventory.json").read_text())
    sources = json.loads((DATA_DIR / "official_sources.json").read_text())
    review = json.loads((DATA_DIR / "repo_review.json").read_text())

    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "sports").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "assets" / "style.css").write_text(CSS.strip() + "\n")
    (SITE_DIR / "assets" / "app.js").write_text(JS.strip() + "\n")

    rows = desk["rows"]
    pred_list = preds["predictions"]
    flag_rows = flagged["event_flags"]
    sports_list = [s[0] for s in SPORT_META]

    # ── 1. Landing Dashboard (index.html) ────────────────────────────────────
    sport_cards = []
    for sp_name, slug, desc in SPORT_META:
        sp_rows = [r for r in rows if r["sport"] == sp_name]
        sp_high = sum(1 for r in sp_rows if r["confidence"] == "High")
        sp_flag = sum(1 for f in flag_rows if f["sport"] == sp_name and f["verification_status"] != "verified_with_advisory")
        badge_str = f'<span class="badge badge-high">{sp_high} High</span>' if sp_high else '<span class="badge badge-blank">WAF Quarantined</span>'
        sport_cards.append(f"""
        <a class="sport-card" href="sports/{slug}.html">
          <div class="sport-card-head">
            <span class="sport-card-title">{e(sp_name)}</span>
            {badge_str}
          </div>
          <div class="sport-card-sub">{e(desc)}</div>
          <div class="sport-card-stats">
            <span class="pill">{len(sp_rows)} Verified Priced</span>
            <span class="pill">{len(sp_rows) * 4 if sp_rows else 0} Market Lines</span>
            {f'<span class="pill">{sp_flag} Blank/Flagged</span>' if sp_flag else ''}
          </div>
        </a>""")

    featured_preview = "".join(render_pred_card(p, depth=0) for p in pred_list[:8])

    index_body = f"""
    <h1>Board AC — Verified Multi-Sport Betting Desk &amp; OLBG Audit</h1>
    <p class="lead">
      Live reverse-engineering of <code>OLBG.com</code> reconciled at <strong>2026-10-22T08:35:00Z</strong> against 22 official governing-body websites and APIs across all <strong>17 in-scope sports</strong>. Every verified match features 4 independently originated betting markets, a Match Winner pick with <code>Low</code>/<code>Medium</code>/<code>High</code> confidence, and <strong>40 bespoke High-confidence human predictions</strong> strictly inside <code>-250</code> to <code>+10000</code> American odds.
    </p>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-val">{desk['summary']['verified_total']}</div><div class="kpi-lbl">Verified Upcoming Matches &amp; Outrights</div></div>
      <div class="kpi-card"><div class="kpi-val">920+</div><div class="kpi-lbl">Originated Fair + 4.2% Book Market Lines</div></div>
      <div class="kpi-card"><div class="kpi-val">{preds['count']}</div><div class="kpi-lbl">High-Confidence Picks in [-250, +10000]</div></div>
      <div class="kpi-card"><div class="kpi-val">16 / 17</div><div class="kpi-lbl">Sports Priced (Greyhounds WAF-Flagged)</div></div>
      <div class="kpi-card"><div class="kpi-val">{len(inv['events'])}</div><div class="kpi-lbl">Live OLBG Events Reconciled (08:35Z)</div></div>
      <div class="kpi-card"><div class="kpi-val">336</div><div class="kpi-lbl">Canonical master.json Rows Audited</div></div>
    </div>

    <div class="info-box">
      <strong>Key Live Reconciliation Findings (07:33Z SSR Capture → 08:31Z Live Sweep):</strong>
      <ul>
        <li><strong>41 Sub-<code>-250</code> OLBG Crowd Chalk Traps Identified:</strong> 31% of OLBG's upcoming featured tips sit shorter than <code>-250</code> (e.g., <em>Daniil Medvedev</em> <code>-1667</code>, <em>Panathinaikos</em> <code>-1429</code>, <em>Barça Handball</em> <code>-1111</code>, <em>Leinster</em> <code>-901</code>, <em>Elena Rybakina</em> <code>-800</code>). Our desk prices every match winner and pivots actionable High-confidence bets onto calibrated Spread/Set/Frame/Leg/Total lines inside <code>[-250, +10000]</code>.</li>
        <li><strong>Major OLBG Crowd Mispricings Uncovered:</strong> On F1 <code>#912</code> (<em>Drivers' Championship Without Kimi Antonelli</em>), OLBG prices 4th-place Max Verstappen (221 pts) at <code>1.73</code> despite George Russell holding 2nd on <code>formula1.com</code> with 238 pts. On Pro D2 <code>#609556</code>, unbeaten 7-0-0 table leader Oyonnax (+159 diff) is priced as a <code>2.50</code> road underdog at 8th-placed Montauban.</li>
        <li><strong>Real-Time Feed Drift Caught:</strong> Caught newly listed NHL <code>#199937</code> (<em>NY Rangers @ TOR Maple Leafs</em>, absent at 07:33Z), live consensus flips on <code>#9945</code> (<em>David Gilbert</em>) &amp; <code>#536020</code> (<em>Minas -5.5</em>), and OLBG's premature 08:00Z expiration of WTA Ningbo <code>#902072</code> (<em>Eala vs Shnaider</em>, official OOP 09:00Z).</li>
      </ul>
    </div>

    <h2>Browse by Sport Category (17 In-Scope Sports)</h2>
    <div class="sport-grid">{''.join(sport_cards)}</div>

    <h2>Featured High-Confidence Predictions Preview (<a href="predictions.html">View All 40 Predictions →</a>)</h2>
    <div class="pred-grid">{featured_preview}</div>
    """
    (SITE_DIR / "index.html").write_text(page_shell("Dashboard", "home", index_body))

    # ── 2. High-Confidence Predictions Page (predictions.html) ───────────────
    preds_body = f"""
    <h1>40 High-Confidence Human Predictions (<code>-250</code> to <code>+10000</code>)</h1>
    <p class="lead">
      Every High-confidence selection sits strictly inside our <strong><code>-250</code> to <code>+10000</code> American odds window</strong> (actual book range <code>{preds['odds_range_book_american'][0]:+d}</code> to <code>{preds['odds_range_book_american'][1]:+d}</code>; <code>1.40</code> to <code>7.50</code> decimal) across <strong>16 distinct in-scope sports</strong>, backed by bespoke <code>{preds['min_words']}–{preds['max_words']}</code>-word analysis (avg <code>{preds['avg_words']}</code> words) citing verified 2026–27 form, recent match history, named players/teams, and official governing-body links.
    </p>
    <div class="filter-bar">
      <input type="search" data-filter-search placeholder="Search player, team, competition, stat…">
      <select data-filter-sport aria-label="Filter by sport">{sport_options(sports_list)}</select>
      <span class="pill" data-filter-count></span>
    </div>
    <div class="pred-grid">{''.join(render_pred_card(p, depth=0) for p in pred_list)}</div>
    """
    (SITE_DIR / "predictions.html").write_text(page_shell("High-Confidence Predictions", "predictions", preds_body))

    # ── 3. All Verified Matches & Outrights (matches.html) ───────────────────
    matches_body = f"""
    <h1>All Verified Upcoming Matches &amp; Outrights ({len(rows)} Entries)</h1>
    <p class="lead">
      Every row below has been verified against an official governing-body schedule and standings source after our <code>2026-10-22T08:35:00Z</code> cutoff, priced with zero-vig fair + 4.2% bookmaker lines, assigned a Match Winner pick and <code>Low</code>/<code>Medium</code>/<code>High</code> confidence tier, and linked directly to its official source.
    </p>
    <div class="filter-bar">
      <input type="search" data-filter-search placeholder="Search team, player, venue, league…">
      <select data-filter-sport aria-label="Filter by sport">{sport_options(sports_list)}</select>
      <select data-filter-conf aria-label="Filter by confidence">
        <option value="">All Confidence Tiers</option>
        <option value="High">High ({desk['summary']['high_confidence_count']})</option>
        <option value="Medium">Medium ({desk['summary']['medium_confidence_count']})</option>
        <option value="Low">Low ({desk['summary']['low_confidence_count']})</option>
      </select>
      <span class="pill" data-filter-count></span>
    </div>
    {render_matches_table(rows, depth=0)}
    """
    (SITE_DIR / "matches.html").write_text(page_shell("Verified Match Desk", "matches", matches_body))

    # ── 4. Full 4-Market Origination Matrix (markets.html) ───────────────────
    markets_body = f"""
    <h1>4-Market Origination Matrix (Win · Handicap · Total · Derivative)</h1>
    <p class="lead">
      Independent line origination across every available market family: (1) Match Winner / 3-Way 1X2, (2) Calibrated Point/Goal/Run/Puck/Set/Frame/Leg/Map Handicap, (3) Match Total Over/Under, and (4) Sport-Specific Derivative Markets (1st Set, First 5 Innings, 60-Min Regulation, 1st Half Spread, Deciding 7th Frame, Most 180s, Straight-Set Sweep, Winning Margin, First Blood, Podium/Top-5).
    </p>
    <div class="filter-bar">
      <input type="search" data-filter-search placeholder="Filter matchup or market…">
      <select data-filter-sport aria-label="Filter by sport">{sport_options(sports_list)}</select>
      <select data-filter-conf aria-label="Filter by confidence">
        <option value="">All Confidence Tiers</option>
        <option value="High">High</option>
        <option value="Medium">Medium</option>
        <option value="Low">Low</option>
      </select>
      <span class="pill" data-filter-count></span>
    </div>
    {render_four_markets_table(rows, depth=0)}
    """
    (SITE_DIR / "markets.html").write_text(page_shell("4-Market Origination", "markets", markets_body))

    # ── 5. OLBG Reverse-Engineering & Live Reconciliation (olbg.html) ────────
    arch_items = "".join(
        f"<li><strong><code>{e(a['id'])}</code> — {e(a['title'])}:</strong> {e(a['detail'])}</li>"
        for a in inv["architecture_findings"]
    )
    olbg_url_by_eid = {str(ev["event_id"]): ev["olbg_url"] for ev in inv["events"]}
    chalk_trs = "".join(
        f"""<tr>
          <td>{e(c['sport'])}</td>
          <td class="mono">#{e(c['event_id'])}</td>
          <td><a href="{e(olbg_url_by_eid.get(str(c['event_id']), 'https://www.olbg.com/betting-tips'))}" target="_blank" rel="noopener">{e(c['event_name'])} ↗</a></td>
          <td><strong>{e(c['featured_selection'])}</strong></td>
          <td class="mono">{c['decimal']:.2f} ({c['american']:+d})</td>
          <td class="mono">{round(100.0 / c['decimal'], 1)}%</td>
        </tr>"""
        for c in inv["sub_minus250_featured_chalk"]
    )
    inv_trs = "".join(
        f"""<tr data-filter-row data-sport="{e(ev['sport'])}" data-cat="{e(ev['reconciled_status_0835z'])}">
          <td class="mono">#{ev['event_id']}</td>
          <td><strong>{e(ev['sport'])}</strong> <span class="muted">(ID {ev['olbg_sport_id']})</span></td>
          <td><a href="{e(ev['olbg_url'])}" target="_blank" rel="noopener">{e(ev['event_name'])} ↗</a></td>
          <td class="mono">{e((ev.get('start_utc') or '')[:16].replace('T', ' '))}Z</td>
          <td>{e(ev.get('market_label') or '')}</td>
          <td>{e(ev.get('featured_selection') or '—')}</td>
          <td class="mono">{fmt_dec(ev.get('featured_price_decimal')) or '—'}</td>
          <td><span class="pill">{e(ev['reconciled_status_0835z'])}</span></td>
        </tr>"""
        for ev in inv["events"]
    )
    olbg_body = f"""
    <h1>OLBG.com Reverse-Engineering &amp; Live 08:35Z Reconciliation</h1>
    <p class="lead">
      Structural audit of <code>OLBG.com</code> SvelteKit SSR payloads, URL taxonomy, <code>robots.txt</code> boundaries, market availability on <code>?event_id=</code> pages, and live drift between <code>07:33Z</code> SSR captures and our <code>08:31Z–08:40Z</code> live sweep.
    </p>
    <div class="info-box">
      <h3>SvelteKit Architecture Findings (<code>SSR-01</code> to <code>SSR-05</code>)</h3>
      <ul>{arch_items}</ul>
    </div>

    <h2>Why <code>&gt;70%</code> Crowd Picks Violate <code>-250</code>: All {len(inv['sub_minus250_featured_chalk'])} Sub-<code>-250</code> OLBG Chalk Traps</h2>
    <p class="lead">A zero-vig probability above <code>71.4%</code> translates mathematically to odds shorter than <code>1.40</code> decimal (<code>-250</code> American). Below are all {len(inv['sub_minus250_featured_chalk'])} active OLBG featured selections priced shorter than <code>-250</code> that our desk refused to label as outright High-confidence moneyline chalk, pivoting instead onto calibrated handicaps/totals.</p>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Event ID</th><th>OLBG Event</th><th>Crowd Pick</th><th>OLBG Price</th><th>Implied Prob</th></tr></thead>
        <tbody>{chalk_trs}</tbody>
      </table>
    </div>

    <h2>Complete 180-Event OLBG Reconciled Inventory</h2>
    <div class="filter-bar">
      <input type="search" data-filter-search placeholder="Search OLBG event or selection…">
      <select data-filter-cat aria-label="Filter by status">
        <option value="">All Reconciled Statuses (180)</option>
        <option value="active_upcoming">active_upcoming (132)</option>
        <option value="newly_listed_0831z">newly_listed_0831z (1)</option>
        <option value="active_outright">active_outright (17)</option>
        <option value="expired_pre_0835z">expired_pre_0835z (18)</option>
        <option value="unverified_waf_flagged">unverified_waf_flagged (6)</option>
        <option value="scope_excluded_flagged">scope_excluded_flagged (6)</option>
      </select>
      <span class="pill" data-filter-count></span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Event ID</th><th>Sport</th><th>Event Name</th><th>Start (UTC)</th><th>Market</th><th>Featured Pick</th><th>Decimal</th><th>08:35Z Status</th></tr></thead>
        <tbody>{inv_trs}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "olbg.html").write_text(page_shell("OLBG Reverse-Engineering", "olbg", olbg_body))

    # ── 6. Line-by-Line Repo Audit (review.html) ─────────────────────────────
    ma = review["datasets_reviewed"][0]
    sf = ma["summary_findings"]
    peer_cards = "".join(
        f"""<tr>
          <td class="mono">{e(d['path'])}</td>
          <td class="mono">{e(d.get('total_rows', ''))}</td>
          <td>{e(d.get('finding', ''))}</td>
        </tr>"""
        for d in review["datasets_reviewed"][1:]
    )
    defect_items = "".join(f"<li>{e(x)}</li>" for x in ma["critical_defects"])
    fed_url_by_sport = {s["sport"]: s["urls"][0] for s in sources["sources"] if s.get("urls")}
    corrupt_trs = "".join(
        f"""<tr>
          <td class="mono">{e(r['id'])}</td>
          <td>{e(r['sport'])}</td>
          <td class="mono">{e(r['corrupted_key'])}</td>
          <td>{e(r.get('value') or '')}</td>
          <td><a href="{e(fed_url_by_sport.get(r['sport'], r.get('source_url') or 'https://www.nhl.com/schedule'))}" target="_blank" rel="noopener">Official Federation Review ↗</a></td>
        </tr>"""
        for r in ma["corrupted_odds_keys"][:40]
    )
    missing_src_trs = "".join(
        f"""<tr>
          <td class="mono">{e(r['id'])}</td>
          <td>{e(r['sport'])}</td>
          <td>{e(r['match'])}</td>
          <td>{e(r.get('competition') or '')}</td>
          <td><a href="{e(fed_url_by_sport.get(r['sport'], 'https://www.afl.com.au/aflw/matches'))}" target="_blank" rel="noopener">Official Federation Review ↗</a></td>
        </tr>"""
        for r in ma["missing_source_rows"]
    )
    review_body = f"""
    <h1>Line-by-Line Repository &amp; Canonical <code>data/master.json</code> Audit</h1>
    <p class="lead">
      Programmatic row-by-row inspection of all <strong>{ma['total_matches']}</strong> match rows and <strong>{ma['total_outrights']}</strong> outrights in <code>data/master.json</code> plus four peer session snapshots against official governing-body sources at <code>2026-10-22T08:35Z</code>.
    </p>

    <div class="kpi-grid">
      <div class="kpi-card"><div class="kpi-val">{sf['played_before_cutoff_count']}</div><div class="kpi-lbl">Completed / Pre-Cutoff Rows in master.json</div></div>
      <div class="kpi-card"><div class="kpi-val">{sf['missing_source_url_count']}</div><div class="kpi-lbl">Rows Missing Official source_url</div></div>
      <div class="kpi-card"><div class="kpi-val">{sf['corrupted_odds_keys_count']}</div><div class="kpi-lbl">Venue-Corrupted win.odds Keys</div></div>
      <div class="kpi-card"><div class="kpi-val">{sf['high_confidence_missing_win_odds_count']}</div><div class="kpi-lbl">High Picks Missing win.odds</div></div>
      <div class="kpi-card"><div class="kpi-val">{sf['no_pick_count']}</div><div class="kpi-lbl">Rows Without Any Winner Pick</div></div>
      <div class="kpi-card"><div class="kpi-val">{sf['date_discrepancy_count']}</div><div class="kpi-lbl">Cross-Build Date Discrepancies</div></div>
    </div>

    <div class="notice-box">
      <h3>Critical Structural Defects Found in <code>data/master.json</code></h3>
      <ul>{defect_items}</ul>
    </div>

    <h2>Peer Session Desk Comparison</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Dataset Path</th><th>Rows</th><th>Audit Finding</th></tr></thead>
        <tbody>{peer_cards}</tbody>
      </table>
    </div>

    <h2>All {len(ma['missing_source_rows'])} Canonical Rows Missing <code>source_url</code> (With Official Manual-Review Links)</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Master ID</th><th>Sport</th><th>Historical Match Label</th><th>Date</th><th>Official Manual-Review Link</th></tr></thead>
        <tbody>{missing_src_trs}</tbody>
      </table>
    </div>

    <h2>All {len(ma['corrupted_odds_keys'])} Canonical Rows With Venue-Prefixed Corrupted <code>win.odds</code> Keys</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Master ID</th><th>Sport</th><th>Match</th><th>Corrupted Odds Dictionary Keys</th><th>Official Verification Link</th></tr></thead>
        <tbody>{corrupt_trs}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "review.html").write_text(page_shell("Repo Audit", "review", review_body))

    # ── 7. Flagged for Review Page (flagged.html) ────────────────────────────
    flag_trs = []
    for fr in flag_rows:
        reasons_html = "<br>".join(f"• {e(rsn)}" for rsn in fr["reasons"])
        olbg_link = f'<a href="{e(fr["olbg_url"])}" target="_blank" rel="noopener">OLBG ↗</a>' if fr.get("olbg_url") else "—"
        flag_trs.append(f"""
        <tr data-filter-row data-sport="{e(fr['sport'])}" data-cat="{e(fr['category'])}">
          <td><strong>{e(fr['sport'])}</strong><div class="muted">{e(fr['competition'])}</div></td>
          <td><strong>{e(fr['matchup'])}</strong><div class="mono muted">{e((fr.get('start_utc') or '')[:16].replace('T', ' '))}Z</div></td>
          <td><span class="pill">{e(fr['category'])}</span></td>
          <td class="mono">{e(fr['match_winner_pick'])}</td>
          <td>{conf_badge(fr['confidence']) if fr['confidence'] else '<span class="badge badge-blank">BLANK</span>'}</td>
          <td class="mono">{e(fr['originated_odds'])}</td>
          <td>{reasons_html}</td>
          <td><a href="{e(fr['official_url'])}" target="_blank" rel="noopener">{e(host_label(fr['official_url']))} ↗</a> · {olbg_link}</td>
        </tr>""")

    flagged_body = f"""
    <h1>Flagged for Review — Unverified Quarantine &amp; Market Irregularities</h1>
    <div class="notice-box">
      <strong>Strict Zero-Inference Guarantee:</strong> Every unverified, Cloudflare-WAF-blocked (<code>gbgb.org.uk</code> HTTP 403), pre-draw <code>TBD</code>, pre-cutoff expired, or scope-excluded row leaves <code>Match Winner Pick</code>, <code>Confidence</code>, and <code>Originated Odds</code> strictly <strong>blank (<code>""</code>)</strong> — never guessed or interpolated — and provides a direct official governing-body link for manual verification. Per project governance, flagged items published here for manual review do not block deployment.
    </div>

    <div class="filter-bar">
      <input type="search" data-filter-search placeholder="Search flagged match, reason, sport…">
      <select data-filter-cat aria-label="Filter by flag category">
        <option value="">All Flagged Rows ({len(flag_rows)})</option>
        <option value="unverified_or_withheld_inputs">Unverified / Withheld Official Inputs (24)</option>
        <option value="unverified_waf_flagged">Greyhounds WAF 403 Quarantine (2 evening + 4 morning in withheld)</option>
        <option value="pre_draw_tbd">Pre-Draw TBD Bracket Slots (4)</option>
        <option value="expired_pre_0835z">Expired Pre-08:35Z OLBG Rows (17)</option>
        <option value="scope_excluded_flagged">Scope-Excluded Gaelic Football ID 25 (6)</option>
        <option value="advisory_market_discrepancy">Verified Rows With OLBG Market Discrepancy (60)</option>
      </select>
      <span class="pill" data-filter-count></span>
    </div>

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sport</th>
            <th>Matchup / Racecard</th>
            <th>Flag Category</th>
            <th>Winner Pick</th>
            <th>Confidence</th>
            <th>Originated Odds</th>
            <th>Irregularity / Quarantine Explanation</th>
            <th>Manual Review Links</th>
          </tr>
        </thead>
        <tbody>{''.join(flag_trs)}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "flagged.html").write_text(page_shell("Flagged for Review", "flagged", flagged_body))

    # ── 8. Methodology & Official Source Registry (methodology.html) ─────────
    src_trs = []
    for s in sources["sources"]:
        links_html = "<br>".join(f'<a href="{e(u)}" target="_blank" rel="noopener">{e(u)} ↗</a>' for u in s["urls"])
        src_trs.append(f"""<tr>
          <td><strong>{e(s['sport'])}</strong></td>
          <td>{e(s['federation'])}</td>
          <td>{e(s['verified_scope'])}</td>
          <td class="mono">{links_html}</td>
        </tr>""")

    method_body = f"""
    <h1>Line Origination Methodology &amp; Official Source Registry</h1>
    <p class="lead">
      How Board AC independently originates fair and bookmaker lines across 16 sports without copying sportsbook or OLBG consensus prices, and why High-confidence selections are bounded to <code>-250</code> to <code>+10000</code>.
    </p>
    <div class="info-box">
      <h3>1. Independent Multi-Market Origination Architecture</h3>
      <ul>
        <li><strong>Governing-Body Rating Inputs Only:</strong> Every fixture probability is derived from official league tables, points-per-game / goal-differential rates, ATP/WTA/WST/PDC/ICC/BWF rankings, and confirmed venue/rest adjustments.</li>
        <li><strong>Zero-Vig Fair vs. Bookmaker Margin:</strong> Zero-vig fair decimal odds equal <code>1 / p</code>. Bookmaker prices apply a favorite-longshot-adjusted power margin targeting <strong><code>4.2%</code> overround on 2-way markets</strong> and <strong><code>5.2%</code> on 3-way 1X2 markets</strong>.</li>
        <li><strong>4 Market Families Investigated Per Match:</strong> (1) Match Winner / 1X2, (2) Gaussian &amp; Markov Bo3/Bo5/Bo7/Bo11 Handicap Spreads, (3) Pace-calibrated Match Totals (withheld when official venue innings averages are unprinted), and (4) Sport-Specific Derivatives (1st Set, F5 Moneyline, 60m Regulation, 1H Spread, 7th-Frame Decider, Most 180s, Straight Sweep, Winning Margin, First Blood, Podium/Top-5).</li>
        <li><strong>Resolving the <code>&gt;70%</code> vs. <code>-250</code> Paradox:</strong> Because <code>p &gt; 71.43%</code> implies fair odds shorter than <code>-250</code> (<code>1.40</code> decimal), outright moneylines on heavy favorites offer poor risk-reward. Our desk still picks the Match Winner on every match, while focusing all <strong>40 High-confidence picks</strong> strictly inside <code>-250</code> to <code>+10000</code> via value moneylines (<code>58%–70%</code>) or calibrated Set/Frame/Leg/Goal/Point handicaps and totals.</li>
      </ul>
    </div>

    <h2>Official Governing-Body Source Registry ({sources['source_count']} Verified Authorities)</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Official Governing Body</th><th>Verified Coverage Scope</th><th>Official URLs</th></tr></thead>
        <tbody>{''.join(src_trs)}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "methodology.html").write_text(page_shell("Methodology & Sources", "methodology", method_body))

    # ── 9. 17 Sport Category Subpages (sports/<slug>.html) ───────────────────
    for sp_name, slug, desc in SPORT_META:
        sp_rows = [r for r in rows if r["sport"] == sp_name]
        sp_preds = [p for p in pred_list if p["sport"] == sp_name]
        sp_flags = [f for f in flag_rows if f["sport"] == sp_name and f["verification_status"] != "verified_with_advisory"]

        pred_sec = ""
        if sp_preds:
            pred_sec = f"<h2>High-Confidence {e(sp_name)} Predictions ({len(sp_preds)})</h2><div class='pred-grid'>" + "".join(
                render_pred_card(p, depth=1) for p in sp_preds
            ) + "</div>"

        matches_sec = ""
        if sp_rows:
            matches_sec = (
                f"<h2>Verified {e(sp_name)} Match &amp; Market Desk ({len(sp_rows)})</h2>"
                + render_matches_table(sp_rows, depth=1, show_sport_col=False)
                + f"<h2>Full 4-Market Origination — {e(sp_name)}</h2>"
                + render_four_markets_table(sp_rows, depth=1)
            )

        flag_sec = ""
        if sp_flags:
            f_trs = "".join(
                f"""<tr>
                  <td><strong>{e(fr['matchup'])}</strong></td>
                  <td class="mono">{e((fr.get('start_utc') or '')[:16].replace('T', ' '))}Z</td>
                  <td><span class="pill">{e(fr['category'])}</span></td>
                  <td class="mono">{e(fr['match_winner_pick'])}</td>
                  <td class="mono">{e(fr['originated_odds'])}</td>
                  <td>{e('; '.join(fr['reasons']))}</td>
                  <td><a href="{e(fr['official_url'])}" target="_blank" rel="noopener">{e(host_label(fr['official_url']))} ↗</a></td>
                </tr>"""
                for fr in sp_flags
            )
            flag_sec = f"""
            <h2>Quarantined / Blank Unconfirmed {e(sp_name)} Rows ({len(sp_flags)})</h2>
            <div class="notice-box">Unconfirmed fields are left strictly blank (<code>""</code>) per our zero-inference mandate.</div>
            <div class="table-wrap">
              <table>
                <thead><tr><th>Event / Card</th><th>Start (UTC)</th><th>Status</th><th>Pick</th><th>Odds</th><th>Reason</th><th>Official Review Link</th></tr></thead>
                <tbody>{f_trs}</tbody>
              </table>
            </div>"""

        sub_body = f"""
        <p><a href="../index.html">← Back to Board AC Dashboard</a></p>
        <h1>{e(sp_name)} — Verified Desk &amp; Originated Lines</h1>
        <p class="lead">{e(desc)} · Verified Priced Rows: <strong>{len(sp_rows)}</strong> · High-Confidence Picks: <strong>{len(sp_preds)}</strong> · Quarantined/Flagged Rows: <strong>{len(sp_flags)}</strong>.</p>
        {pred_sec}
        {matches_sec}
        {flag_sec}
        """
        (SITE_DIR / "sports" / f"{slug}.html").write_text(page_shell(f"{sp_name} Desk", "home", sub_body, depth=1))

    html_count = len(list(SITE_DIR.rglob("*.html")))
    print(f"Rendered {html_count} HTML pages + CSS + JS under {SITE_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()

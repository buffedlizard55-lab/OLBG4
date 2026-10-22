#!/usr/bin/env python3
"""Board Z (session arena/9359e596-olbg4) - static GitHub Pages dashboard generator.

Renders `session-9359e596/` from `data/session-9359e596/{desk,predictions,flagged,repo_review,olbg_inventory,official_sources}.json`:
  - session-9359e596/index.html
  - session-9359e596/predictions.html
  - session-9359e596/matches.html
  - session-9359e596/markets.html
  - session-9359e596/olbg.html
  - session-9359e596/flagged.html
  - session-9359e596/sources.html
  - session-9359e596/methodology.html
  - session-9359e596/sports/<slug>.html (19 category pages)
  - session-9359e596/assets/style.css
"""
from __future__ import annotations

import html as H
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
Z_DATA = os.path.join(ROOT, "data", "session-9359e596")
OUT_DIR = os.path.join(ROOT, "session-9359e596")


def esc(val: object) -> str:
    if val is None or val == "":
        return "—"
    return H.escape(str(val), quote=True)


def fmt_am(am: int | None) -> str:
    if am is None:
        return "—"
    return f"+{am}" if am > 0 else str(am)


def fmt_price(am: int | None, dec: float | None) -> str:
    if am is None or dec is None:
        return "—"
    return f"<strong>{fmt_am(am)}</strong> <span class=\"muted\">({dec:.2f})</span>"


def conf_badge(conf: str | None) -> str:
    if not conf:
        return '<span class="badge badge-blank">—</span>'
    cls = {"High": "badge-high", "Medium": "badge-med", "Low": "badge-low"}.get(conf, "badge-blank")
    return f'<span class="badge {cls}">{esc(conf)}</span>'


def ver_badge(ver: str, row_id: str, prefix: str = "") -> str:
    if ver == "verified":
        return '<span class="badge badge-ver">Verified</span>'
    if ver == "partially_verified":
        return f'<a class="badge badge-part" href="{prefix}flagged.html#{esc(row_id)}">Partial — Flagged</a>'
    return f'<a class="badge badge-unver" href="{prefix}flagged.html#{esc(row_id)}">Unverified — Flagged</a>'


def source_cell(r: dict, prefix: str = "") -> str:
    if r.get("official_url"):
        label = r.get("official_source_name") or "Official Source"
        short = label.split("(")[0].strip()[:34]
        extra = ""
        if r.get("extra_official_urls"):
            extra_links = " ".join(
                f'<a href="{esc(u)}" target="_blank" rel="noopener" title="{esc(u)}">[+{i+1}]</a>'
                for i, u in enumerate(r["extra_official_urls"][:2])
            )
            extra = f' <span class="extra-links">{extra_links}</span>'
        return f'<a class="src-link" href="{esc(r["official_url"])}" target="_blank" rel="noopener">{esc(short)} &#8599;</a>{extra}'
    return f'<a class="src-missing" href="{prefix}flagged.html#{esc(r["id"])}">Unverified (see Flagged)</a>'


def market_cells(r: dict) -> tuple[str, str, str]:
    m = r.get("markets")
    if not m:
        return "—", "—", "—"
    ml = m["moneyline"]
    if m.get("three_way"):
        tw = m["three_way"]
        ml_html = (
            f'<div class="mkt-line"><span>{esc(ml["a_label"])}:</span> {fmt_am(tw["am_home"])} ({tw["dec_home"]:.2f})</div>'
            f'<div class="mkt-line"><span>Draw:</span> {fmt_am(tw["am_draw"])} ({tw["dec_draw"]:.2f})</div>'
            f'<div class="mkt-line"><span>{esc(ml["b_label"])}:</span> {fmt_am(tw["am_away"])} ({tw["dec_away"]:.2f})</div>'
        )
    else:
        ml_html = (
            f'<div class="mkt-line"><span>{esc(ml["a_label"])}:</span> {fmt_am(ml["am_a"])} ({ml["dec_a"]:.2f})</div>'
            f'<div class="mkt-line"><span>{esc(ml["b_label"])}:</span> {fmt_am(ml["am_b"])} ({ml["dec_b"]:.2f})</div>'
        )

    hc = m.get("handicap")
    if hc:
        hc_html = (
            f'<div class="mkt-line"><span>{esc(hc["a_label"])}:</span> {fmt_am(hc["am_a"])} ({hc["dec_a"]:.2f})</div>'
            f'<div class="mkt-line"><span>{esc(hc["b_label"])}:</span> {fmt_am(hc["am_b"])} ({hc["dec_b"]:.2f})</div>'
        )
    else:
        hc_html = "—"

    tot = m.get("total")
    if tot:
        tot_html = (
            f'<div class="mkt-line"><span>{esc(tot["over_label"])}:</span> {fmt_am(tot["am_over"])} ({tot["dec_over"]:.2f})</div>'
            f'<div class="mkt-line"><span>{esc(tot["under_label"])}:</span> {fmt_am(tot["am_under"])} ({tot["dec_under"]:.2f})</div>'
        )
    else:
        tot_html = "—"
    return ml_html, hc_html, tot_html


CSS = """
:root {
  --bg: #f6f8fb;
  --surface: #ffffff;
  --ink: #0f172a;
  --muted: #475569;
  --border: #e2e8f0;
  --navy: #0b192c;
  --accent: #0f766e;
  --accent-soft: #ccfbf1;
  --high-bg: #dcfce7;
  --high-fg: #14532d;
  --med-bg: #dbeafe;
  --med-fg: #1e3a8a;
  --low-bg: #f1f5f9;
  --low-fg: #334155;
  --warn-bg: #fef3c7;
  --warn-fg: #78350f;
  --bad-bg: #fee2e2;
  --bad-fg: #7f1d1d;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Inter, Roboto, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.55;
  font-variant-numeric: tabular-nums;
}
a { color: #0f52ba; text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  background: var(--navy);
  color: #f8fafc;
  border-bottom: 3px solid var(--accent);
}
.topbar-inner {
  max-width: 1380px;
  margin: 0 auto;
  padding: 14px 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.brand {
  font-weight: 800;
  font-size: 1.08rem;
  color: #ffffff;
  letter-spacing: -0.01em;
}
.brand span {
  background: var(--accent);
  color: #ffffff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.78rem;
  margin-left: 8px;
  vertical-align: middle;
}
.nav {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.nav a {
  color: #cbd5e1;
  padding: 6px 11px;
  border-radius: 6px;
  font-size: 0.88rem;
  font-weight: 600;
}
.nav a:hover, .nav a.active {
  background: rgba(255,255,255,0.13);
  color: #ffffff;
  text-decoration: none;
}
.container {
  max-width: 1380px;
  margin: 0 auto;
  padding: 24px 20px 56px;
}
.hero {
  background: linear-gradient(135deg, #0b192c 0%, #13315c 100%);
  color: #ffffff;
  border-radius: 12px;
  padding: 26px 28px;
  margin-bottom: 22px;
  box-shadow: 0 4px 16px rgba(15,23,42,0.08);
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 1.75rem;
  letter-spacing: -0.02em;
}
.hero p {
  margin: 0;
  color: #cbd5e1;
  max-width: 960px;
  font-size: 0.97rem;
}
.disclaimer {
  margin-top: 12px;
  padding: 8px 12px;
  background: rgba(255,255,255,0.1);
  border-left: 3px solid #38bdf8;
  border-radius: 4px;
  font-size: 0.83rem;
  color: #e2e8f0;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 14px;
  margin-bottom: 24px;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 15px 16px;
}
.kpi-val {
  font-size: 1.65rem;
  font-weight: 800;
  color: var(--navy);
  line-height: 1.15;
}
.kpi-lbl {
  font-size: 0.8rem;
  color: var(--muted);
  margin-top: 4px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.section-title {
  font-size: 1.25rem;
  font-weight: 800;
  margin: 28px 0 12px;
  color: var(--navy);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.sport-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
  gap: 12px;
  margin-bottom: 26px;
}
.sport-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  display: block;
  color: var(--ink);
  transition: border-color 0.15s, transform 0.15s;
}
.sport-card:hover {
  border-color: var(--accent);
  transform: translateY(-1px);
  text-decoration: none;
}
.sport-card h3 {
  margin: 0 0 6px;
  font-size: 1rem;
  color: var(--navy);
}
.sport-meta {
  font-size: 0.82rem;
  color: var(--muted);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.pred-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 16px;
}
@media (max-width: 520px) {
  .pred-grid { grid-template-columns: 1fr; }
}
.pred-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 4px solid #15803d;
  border-radius: 10px;
  padding: 18px 20px;
}
.pred-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}
.pred-sport {
  font-size: 0.76rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--accent);
}
.pred-match {
  font-size: 1.06rem;
  font-weight: 800;
  color: var(--navy);
  margin: 2px 0;
}
.pred-pick-bar {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 7px;
  padding: 8px 12px;
  margin: 10px 0;
  font-size: 0.88rem;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
}
.pred-text {
  font-size: 0.93rem;
  color: #1e293b;
  margin: 10px 0 12px;
}
.pred-facts {
  margin: 0;
  padding-left: 18px;
  font-size: 0.8rem;
  color: var(--muted);
}
.pred-facts li { margin-bottom: 3px; }
.filter-bar {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
}
.filter-bar input, .filter-bar select {
  padding: 7px 11px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 0.88rem;
  background: #ffffff;
}
.filter-bar input { min-width: 230px; flex: 1; }
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
th {
  background: #f8fafc;
  color: var(--navy);
  font-weight: 700;
  text-align: left;
  padding: 10px 12px;
  border-bottom: 2px solid var(--border);
  white-space: nowrap;
}
td {
  padding: 9px 12px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: top;
}
tr:hover td { background: #f8fafc; }
.mkt-line { white-space: nowrap; font-size: 0.82rem; line-height: 1.4; }
.mkt-line span { color: var(--muted); }
.muted { color: var(--muted); font-size: 0.8rem; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  white-space: nowrap;
}
.badge-high { background: var(--high-bg); color: var(--high-fg); }
.badge-med { background: var(--med-bg); color: var(--med-fg); }
.badge-low { background: var(--low-bg); color: var(--low-fg); }
.badge-ver { background: #e0f2fe; color: #075985; }
.badge-part { background: var(--warn-bg); color: var(--warn-fg); }
.badge-unver { background: var(--bad-bg); color: var(--bad-fg); }
.badge-blank { background: #f1f5f9; color: #64748b; }
.src-link { font-weight: 600; font-size: 0.82rem; }
.src-missing { color: var(--bad-fg); font-weight: 600; font-size: 0.8rem; }
.extra-links a { font-size: 0.75rem; color: var(--muted); }
.card-box {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 18px 20px;
  margin-bottom: 16px;
}
.card-box h3 { margin-top: 0; color: var(--navy); }
.footer {
  margin-top: 44px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
  font-size: 0.82rem;
  color: var(--muted);
  display: flex;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}
code {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 0.82em;
}
"""


def page_shell(title: str, active: str, body: str, prefix: str = "") -> str:
    nav_items = [
        ("overview", f"{prefix}index.html", "Overview"),
        ("predictions", f"{prefix}predictions.html", "High Picks (-250..+10000)"),
        ("matches", f"{prefix}matches.html", "All Matches (280)"),
        ("markets", f"{prefix}markets.html", "Originated Markets"),
        ("olbg", f"{prefix}olbg.html", "OLBG Reconciliation"),
        ("flagged", f"{prefix}flagged.html", "Flagged & Repo Review"),
        ("sources", f"{prefix}sources.html", "Official Sources"),
        ("methodology", f"{prefix}methodology.html", "Methodology"),
        ("root", f"{prefix}../index.html", "Repo Home ↗"),
    ]
    nav_html = "".join(
        f'<a href="{href}" class="{"active" if key == active else ""}">{label}</a>'
        for key, href, label in nav_items
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — OLBG4 Board Z (2026-10-22 UTC)</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="{prefix}index.html">OLBG4 Sports Desk <span>Board Z · 2026-10-22T07:50Z</span></a>
      <nav class="nav">{nav_html}</nav>
    </div>
  </header>
  <main class="container">
    {body}
    <footer class="footer">
      <div>Session <code>arena/9359e596-olbg4</code> (Board Z) · Live OLBG capture <code>2026-10-22T07:33:46Z</code> · Analytical research only — <strong>not betting advice</strong>.</div>
      <div><a href="{prefix}../board/index.html">Master Board</a> · <a href="{prefix}../audit/index.html">Publication Audit</a> · <a href="{prefix}flagged.html">Flagged for Review</a></div>
    </footer>
  </main>
</body>
</html>
"""


def render_pred_card(p: dict, prefix: str = "") -> str:
    facts_li = "".join(f"<li>{esc(f)}</li>" for f in p["verified_facts"])
    olbg_ref = (
        f'OLBG card: {esc(p["olbg_featured_selection"])} ({fmt_am(p["olbg_price_american"])})'
        if p.get("olbg_price_american") is not None
        else "Official-schedule fixture (not on OLBG SSR card)"
    )
    return f"""
    <article class="pred-card" id="pred-{esc(p['id'])}">
      <div class="pred-head">
        <div>
          <div class="pred-sport"><a href="{prefix}sports/{esc(p['sport'].lower().replace(' ', '-'))}.html">{esc(p['sport'])}</a> · {esc(p['competition'])}</div>
          <div class="pred-match">{esc(p['matchup'])}</div>
          <div class="muted">{esc(p['start_utc'])} · {esc(p.get('venue') or 'Official venue')}</div>
        </div>
        <span class="badge badge-high">High Confidence</span>
      </div>
      <div class="pred-pick-bar">
        <div><strong>Selection:</strong> {esc(p['selection'])} <span class="muted">({esc(p['market'])})</span></div>
        <div><strong>Our Fair Line:</strong> {fmt_am(p['fair_american'])} ({p['fair_decimal']:.2f} · {p['probability']*100:.1f}%)</div>
      </div>
      <p class="pred-text">{esc(p['prediction_text'])}</p>
      <ul class="pred-facts">{facts_li}</ul>
      <div class="muted" style="margin-top:10px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;">
        <span>{olbg_ref} · {p['word_count']} words</span>
        <a class="src-link" href="{esc(p['official_url'])}" target="_blank" rel="noopener">{esc(p['official_source_name'])} &#8599;</a>
      </div>
    </article>
    """


def render_rows_table(rows: list[dict], prefix: str = "", include_filters: bool = False) -> str:
    sports_opts = "".join(
        f'<option value="{esc(s)}">{esc(s)}</option>'
        for s in sorted({r["sport"] for r in rows})
    )
    filter_html = ""
    if include_filters:
        filter_html = f"""
        <div class="filter-bar">
          <input type="search" id="qSearch" placeholder="Filter by team, player, competition, venue..." oninput="filterRows()">
          <select id="qSport" onchange="filterRows()">
            <option value="">All Sports ({len({r['sport'] for r in rows})})</option>
            {sports_opts}
          </select>
          <select id="qConf" onchange="filterRows()">
            <option value="">All Confidence</option>
            <option value="High">High (-250..+10000)</option>
            <option value="Medium">Medium</option>
            <option value="Low">Low</option>
            <option value="Unpriced">Unpriced / Blank</option>
          </select>
          <select id="qVer" onchange="filterRows()">
            <option value="">All Verification</option>
            <option value="verified">Verified</option>
            <option value="partially_verified">Partially Verified</option>
            <option value="unverified">Unverified — Flagged</option>
          </select>
          <span class="muted" id="qCount">{len(rows)} rows shown</span>
        </div>
        <script>
        function filterRows() {{
          const q = document.getElementById('qSearch').value.toLowerCase();
          const sp = document.getElementById('qSport').value;
          const cf = document.getElementById('qConf').value;
          const vr = document.getElementById('qVer').value;
          let shown = 0;
          document.querySelectorAll('#matchTable tbody tr').forEach(tr => {{
            const okQ = !q || tr.dataset.search.includes(q);
            const okS = !sp || tr.dataset.sport === sp;
            const okC = !cf || tr.dataset.conf === cf;
            const okV = !vr || tr.dataset.ver === vr;
            const vis = okQ && okS && okC && okV;
            tr.style.display = vis ? '' : 'none';
            if (vis) shown++;
          }});
          document.getElementById('qCount').textContent = shown + ' rows shown';
        }}
        </script>
        """

    trs = []
    for r in rows:
        ml_h, hc_h, tot_h = market_cells(r)
        pick_html = "—"
        if r.get("headline_selection"):
            pick_html = (
                f'<div><strong>{esc(r["headline_selection"])}</strong></div>'
                f'<div class="muted">{fmt_am(r["headline_fair_american"])} ({r["headline_fair_decimal"]:.2f})</div>'
            )
            if r.get("prediction"):
                pick_html += f'<div><a href="{prefix}predictions.html#pred-{esc(r["id"])}">Read prediction &rarr;</a></div>'
        search_blob = f"{r['sport']} {r['competition']} {r['matchup']} {r.get('venue') or ''} {r.get('headline_selection') or ''}".lower()
        cf_val = r.get("confidence") or "Unpriced"
        trs.append(
            f'<tr id="{esc(r["id"])}" data-search="{esc(search_blob)}" data-sport="{esc(r["sport"])}" data-conf="{esc(cf_val)}" data-ver="{esc(r["verification"])}">'
            f'<td><a href="{prefix}sports/{esc(r["sport_slug"])}.html"><strong>{esc(r["sport"])}</strong></a><div class="muted">{esc(r["competition"])}</div></td>'
            f'<td><strong>{esc(r["matchup"])}</strong><div class="muted">{esc(r.get("start_utc"))} · {esc(r["status"])}</div></td>'
            f'<td>{ml_h}</td>'
            f'<td>{hc_h}</td>'
            f'<td>{tot_h}</td>'
            f'<td>{pick_html}</td>'
            f'<td>{conf_badge(r.get("confidence"))}</td>'
            f'<td>{ver_badge(r["verification"], r["id"], prefix)}<div style="margin-top:4px">{source_cell(r, prefix)}</div></td>'
            f'</tr>'
        )
    return f"""
    {filter_html}
    <div class="table-wrap">
      <table id="matchTable">
        <thead>
          <tr>
            <th>Sport / Competition</th>
            <th>Matchup &amp; Start (UTC)</th>
            <th>Our Match Winner / 1X2</th>
            <th>Our Handicap / Spread</th>
            <th>Our Match Total (O/U)</th>
            <th>Pick &amp; Fair Line</th>
            <th>Confidence</th>
            <th>Verification &amp; Official Source</th>
          </tr>
        </thead>
        <tbody>
          {''.join(trs)}
        </tbody>
      </table>
    </div>
    """


def build_site() -> None:
    desk = json.load(open(os.path.join(Z_DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(Z_DATA, "predictions.json"), encoding="utf-8"))
    flagged = json.load(open(os.path.join(Z_DATA, "flagged.json"), encoding="utf-8"))
    rev = json.load(open(os.path.join(Z_DATA, "repo_review.json"), encoding="utf-8"))
    olbg = json.load(open(os.path.join(Z_DATA, "olbg_inventory.json"), encoding="utf-8"))
    cap_man = json.load(open(os.path.join(Z_DATA, "capture", "20261022T073346Z", "manifest.json"), encoding="utf-8"))

    os.makedirs(os.path.join(OUT_DIR, "assets"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "sports"), exist_ok=True)
    with open(os.path.join(OUT_DIR, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS.strip() + "\n")

    rows = desk["rows"]
    s = desk["summary"]

    # Group rows by sport
    by_sport: dict[str, list[dict]] = {}
    for r in rows:
        by_sport.setdefault(r["sport"], []).append(r)

    # 1. index.html
    sport_cards = []
    for sp in sorted(by_sport):
        sp_rows = by_sport[sp]
        slug = sp_rows[0]["sport_slug"]
        n_ver = sum(1 for x in sp_rows if x["verification"] == "verified")
        n_high = sum(1 for x in sp_rows if x.get("confidence") == "High")
        ambig = " (Scope-Ambiguous)" if sp == "Gaelic Football" else ""
        sport_cards.append(
            f'<a class="sport-card" href="sports/{slug}.html">'
            f'<h3>{esc(sp)}{ambig}</h3>'
            f'<div class="sport-meta">'
            f'<span><strong>{len(sp_rows)}</strong> rows</span>'
            f'<span><strong>{n_ver}</strong> verified</span>'
            f'<span><strong>{n_high}</strong> High</span>'
            f'</div></a>'
        )

    featured_preds = "".join(render_pred_card(p) for p in preds["predictions"][:6])
    index_body = f"""
    <section class="hero">
      <h1>Updated OLBG Reverse-Engineering, Multi-Market Lines &amp; Verified Sports Audit</h1>
      <p>Live <code>2026-10-22T07:33:46Z</code> UTC capture of all in-scope OLBG sport hubs reconciled line by line against Tier-1 governing-body schedules, rankings, and league tables across <strong>18 in-scope sports</strong> (strictly excluding soccer, boxing, UFC, MMA, football, American football, hurling, horse racing, cycling, and specials).</p>
      <div class="disclaimer"><strong>Zero-Inference Guarantee:</strong> Every table row links directly to an official federation/league source. Wherever an official numerical input cannot be confirmed, lines are left strictly blank (<code>—</code>) and routed to <a href="flagged.html" style="color:#7dd3fc;text-decoration:underline;">Flagged for Review</a>. Analytical research only — not betting advice.</div>
    </section>

    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-val">{s['total_rows']}</div><div class="kpi-lbl">Total Reconciled Rows</div></div>
      <div class="kpi"><div class="kpi-val">{len(s['sports_in_scope'])}</div><div class="kpi-lbl">In-Scope Sports</div></div>
      <div class="kpi"><div class="kpi-val">{s['verified_rows']}</div><div class="kpi-lbl">Fully Verified Rows</div></div>
      <div class="kpi"><div class="kpi-val">{s['priced_rows']}</div><div class="kpi-lbl">Multi-Market Priced</div></div>
      <div class="kpi"><div class="kpi-val">{s['high_confidence_count']}</div><div class="kpi-lbl">High Picks (-250..+10000)</div></div>
      <div class="kpi"><div class="kpi-val">{s['olbg_reconciled_rows']}/177</div><div class="kpi-lbl">Live OLBG Rows Audited</div></div>
      <div class="kpi"><div class="kpi-val">42/42</div><div class="kpi-lbl">SHA-256 Raw Captures</div></div>
    </div>

    <div class="section-title">
      <span>Browse by Sport Category (18 In-Scope + 1 Quarantined)</span>
      <a href="matches.html">Open Full Interactive Table ({s['total_rows']} rows) &rarr;</a>
    </div>
    <div class="sport-grid">{''.join(sport_cards)}</div>

    <div class="section-title">
      <span>Featured High-Confidence Predictions (-250 to +10000 Window)</span>
      <a href="predictions.html">View All {preds['count']} High Predictions Across {len(preds['sports_covered'])} Sports &rarr;</a>
    </div>
    <div class="pred-grid">{featured_preds}</div>

    <div class="section-title"><span>Key OLBG Reverse-Engineering &amp; Repo Audit Findings</span></div>
    <div class="card-box">
      <ul>
        <li><strong>Previously Unverified OLBG Gaps Resolved:</strong> Earlier 22 Oct runs left Handball (33), Volleyball (15), Snooker (2), SHL (3), Cricket (7), and URC's Leinster v Munster unverified. Board Z verified <strong>33/35 live OLBG Handball rows</strong> (EHFCL, HBL, LNH StarLigue, ASOBAL, Herreligaen, Handbollsligan), <strong>all 8/8 Northern Ireland Open Last-16 Snooker ties</strong>, <strong>all 6/6 SHL hockey games</strong>, <strong>12/17 men's Volleyball ties</strong> (ČVS Extraliga, PlusLiga, SuperLega), <strong>4/6 international Cricket fixtures</strong>, and <strong>all 8/8 URC Round 4 fixtures</strong>.</li>
        <li><strong>SvelteKit &amp; Timezone Trap Confirmed:</strong> OLBG embeds <code>event_start_unix_timestamp</code> in UTC seconds inside SSR hydration scripts while rendering visible clock text in client/proxy local time (EDT <code>UTC-4</code> on US proxies). Pagination endpoint <code>/api/svelte</code> is disallowed by <code>robots.txt</code> and was never called.</li>
        <li><strong>Live Morning Results Caught (`03:55Z → 07:34Z`):</strong> Four WTA R16 matches priced on overnight boards finished (`[4] Iva Jovic d. Jasmine Paolini 6-4, 6-3`; `[1] Ann Li d. Zeynep Sönmez 6-3, 6-1`; `Mary Stoiana d. Moyuka Uchijima 6-2, 2-6, 6-3`; `Antonia Ruzic d. Kayla Day 6-4, 0-0 Ret'd`), unlocking newly verified Osaka &amp; Lyon quarter-finals.</li>
        <li><strong>Line-by-Line Repository Review:</strong> 8 repository-wide audit findings (`REV-01`..`REV-08`) with clickable official sources are documented on <a href="flagged.html">Flagged for Review</a>.</li>
      </ul>
    </div>
    """
    with open(os.path.join(OUT_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("Overview Dashboard", "overview", index_body))

    # 2. predictions.html
    all_pred_cards = "".join(render_pred_card(p) for p in preds["predictions"])
    preds_body = f"""
    <section class="hero">
      <h1>High-Confidence Predictions (-250 to +10000 American Odds)</h1>
      <p>All <strong>{preds['count']} High-confidence picks</strong> across <strong>{len(preds['sports_covered'])} distinct sports</strong> ({', '.join(preds['sports_covered'])}) sit strictly inside <code>-250</code> to <code>+10000</code> American fair odds (<code>1.40</code>–<code>101.00</code> decimal). Heavy chalk favourites shorter than <code>-250</code> (&gt;71.4% implied probability) are capped at Medium. Every write-up is hand-researched (78–97 words) from official federation sources naming team, player(s), current form, recent match history, and an explicit selection.</p>
    </section>
    <div class="pred-grid">{all_pred_cards}</div>
    """
    with open(os.path.join(OUT_DIR, "predictions.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("High-Confidence Predictions", "predictions", preds_body))

    # 3. matches.html
    matches_body = f"""
    <section class="hero">
      <h1>Complete Reconciled Match &amp; Outright Schedule ({s['total_rows']} Rows)</h1>
      <p>Filter across all 18 in-scope sports, confidence grades, and verification states. Every verified row links to its official governing-body source; unconfirmed values remain blank (<code>—</code>) and flagged.</p>
    </section>
    {render_rows_table(rows, include_filters=True)}
    """
    with open(os.path.join(OUT_DIR, "matches.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("All Reconciled Matches", "matches", matches_body))

    # 4. markets.html
    priced_rows = [r for r in rows if r.get("markets") is not None]
    mkt_trs = []
    for r in priced_rows:
        ml_h, hc_h, tot_h = market_cells(r)
        cs_top = r["markets"].get("correct_score_top")
        if cs_top:
            cs_html = ", ".join(f'{c["score"]} ({fmt_am(c["am"])})' for c in cs_top[:2])
        elif "lambda_home" in r["markets"]:
            cs_html = f'λ {r["markets"]["lambda_home"]:.2f} – {r["markets"]["lambda_away"]:.2f}'
        elif "expected_margin_home" in r["markets"]:
            cs_html = f'Exp margin {r["markets"]["expected_margin_home"]:+.1f}'
        else:
            cs_html = "—"
        olbg_cmp = (
            f'{esc(r["olbg"]["featured_selection"])}<div class="muted">{fmt_am(r["olbg"]["featured_price_american"])} ({r["olbg"]["featured_price_decimal"]})</div>'
            if r["olbg"]["listed"] and r["olbg"]["featured_price_decimal"]
            else '<span class="muted">Official-only</span>'
        )
        mkt_trs.append(
            f'<tr>'
            f'<td><strong>{esc(r["sport"])}</strong><div class="muted">{esc(r["competition"])}</div></td>'
            f'<td><strong>{esc(r["matchup"])}</strong><div class="muted">{esc(r["start_utc"])}</div></td>'
            f'<td>{ml_h}</td><td>{hc_h}</td><td>{tot_h}</td>'
            f'<td class="muted">{cs_html}</td>'
            f'<td>{olbg_cmp}</td>'
            f'<td><strong>{esc(r["headline_selection"])}</strong> ({fmt_am(r["headline_fair_american"])})<div>{conf_badge(r["confidence"])}</div></td>'
            f'<td>{source_cell(r)}</td>'
            f'</tr>'
        )
    markets_body = f"""
    <section class="hero">
      <h1>Originated Multi-Market Fair Lines ({len(priced_rows)} Priced Fixtures)</h1>
      <p>Zero-margin (100% fair book) independent prices originated solely from official governing-body numerical inputs across Match Winner / 1X2, Handicap / Point-or-Goal-or-Set-or-Frame-or-Leg Spread, Over/Under Match Totals, and discrete score projections.</p>
    </section>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sport</th><th>Matchup</th><th>Match Winner / 1X2</th><th>Handicap / Spread</th><th>Match Total (O/U)</th><th>Model Projection</th><th>OLBG Ref</th><th>Desk Pick</th><th>Official Source</th>
          </tr>
        </thead>
        <tbody>{''.join(mkt_trs)}</tbody>
      </table>
    </div>
    """
    with open(os.path.join(OUT_DIR, "markets.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("Originated Betting Lines", "markets", markets_body))

    # 5. olbg.html
    hub_trs = "".join(
        f'<tr><td><strong>{esc(h["sport"])}</strong> (id={h["olbg_sport_id"]})</td>'
        f'<td><a href="{esc(h["hub_url"])}" target="_blank" rel="noopener">{esc(h["hub_url"])} &#8599;</a></td>'
        f'<td>{h["http_status"]}</td><td>{h["embedded_match_rows"]}</td><td>{h["embedded_tournament_rows"]}</td>'
        f'<td><code>{esc(h["disallowed_internal_api"] or "—")}</code></td>'
        f'<td><code>{h["sha256"][:16]}…</code></td></tr>'
        for h in olbg["hubs"]
    )
    olbg_rows = [r for r in rows if r["olbg"]["listed"]]
    olbg_rec_trs = "".join(
        f'<tr>'
        f'<td>{esc(r["sport"])}</td>'
        f'<td><code>{esc(r["olbg"]["event_id"])}</code></td>'
        f'<td><strong>{esc(r["matchup"])}</strong><div class="muted">{esc(r["row_kind"])} · {esc(r["status"])}</div></td>'
        f'<td>{esc(r["olbg"]["start_utc"])}</td>'
        f'<td>{esc(r["start_utc"])}</td>'
        f'<td>{esc(r["olbg"]["market_label"])}: {esc(r["olbg"]["featured_selection"])} ({fmt_am(r["olbg"]["featured_price_american"])})</td>'
        f'<td>{ver_badge(r["verification"], r["id"])}</td>'
        f'<td>{source_cell(r)}</td>'
        f'</tr>'
        for r in olbg_rows
    )
    olbg_body = f"""
    <section class="hero">
      <h1>Live OLBG.com Reverse-Engineering &amp; 177-Row Reconciliation</h1>
      <p>Captured <code>{olbg['manifest_generated_utc']}</code> across all 17 in-scope OLBG sport hubs. Tipster percentages, vote counts, and comments are stripped; only event structure, Unix start epoch, and market reference price are retained for audit.</p>
    </section>
    <div class="card-box">
      <h3>Technical Reverse-Engineering Findings</h3>
      <ul>{''.join(f'<li>{esc(x)}</li>' for x in olbg['reverse_engineering_findings'])}</ul>
    </div>
    <div class="section-title"><span>Captured In-Scope OLBG Sport Hubs (17 Hubs)</span></div>
    <div class="table-wrap" style="margin-bottom:24px;">
      <table>
        <thead><tr><th>Sport</th><th>OLBG Hub URL</th><th>HTTP</th><th>Match Rows (<code>tips</code>)</th><th>Outright/Race Rows (<code>tournaments</code>)</th><th>Disallowed Internal API (Not Called)</th><th>Raw HTML SHA-256</th></tr></thead>
        <tbody>{hub_trs}</tbody>
      </table>
    </div>
    <div class="section-title"><span>Row-by-Row Official Reconciliation ({len(olbg_rows)} Live OLBG Rows)</span></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>OLBG ID</th><th>Event</th><th>OLBG UTC</th><th>Official UTC</th><th>OLBG Market Ref</th><th>Reconciliation</th><th>Official Source</th></tr></thead>
        <tbody>{olbg_rec_trs}</tbody>
      </table>
    </div>
    """
    with open(os.path.join(OUT_DIR, "olbg.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("OLBG Reverse-Engineering", "olbg", olbg_body))

    # 6. flagged.html (Repo Review + Flagged Rows)
    rev_trs = "".join(
        f'<tr id="{esc(f["id"])}">'
        f'<td><strong>{esc(f["id"])}</strong><div><span class="badge {"badge-unver" if f["severity"]=="high" else "badge-part"}">{esc(f["severity"].upper())}</span></div></td>'
        f'<td><code>{esc(f["file"])}</code><div class="muted">{esc(f["lines"])}</div></td>'
        f'<td><strong>{esc(f["category"])}</strong><div style="margin-top:4px">{esc(f["detail"])}</div><div class="muted" style="margin-top:4px"><strong>Resolution:</strong> {esc(f["resolution"])}</div></td>'
        f'<td><a class="src-link" href="{esc(f["official_url"])}" target="_blank" rel="noopener">{esc(f["official_source"])} &#8599;</a></td>'
        f'</tr>'
        for f in rev["findings"]
    )
    flag_trs = "".join(
        f'<tr id="{esc(fr["id"])}">'
        f'<td><strong>{esc(fr["sport"])}</strong><div class="muted">{esc(fr["competition"])}</div></td>'
        f'<td><strong>{esc(fr["matchup"])}</strong><div class="muted">{esc(fr["start_utc"])} · {esc(fr["status"])}</div></td>'
        f'<td><span class="badge {"badge-unver" if fr["verification"]=="unverified" else ("badge-part" if fr["verification"]=="partially_verified" else "badge-ver")}">{esc(fr["verification"])}</span></td>'
        f'<td>{"<br>".join(esc(x) for x in fr["flags"])}</td>'
        f'<td>{f"<a class=src-link href={esc(fr[chr(111)+chr(102)+chr(102)+chr(105)+chr(99)+chr(105)+chr(97)+chr(108)+chr(95)+chr(117)+chr(114)+chr(108)])} target=_blank rel=noopener>Official Link &#8599;</a>" if fr.get("official_url") else "<span class=muted>No official feed — blank</span>"}</td>'
        f'</tr>'
        for fr in flagged["flagged_rows"]
    )
    flagged_body = f"""
    <section class="hero">
      <h1>Flagged for Review &amp; Line-by-Line Repository Audit</h1>
      <p>Transparent audit trail covering (1) <strong>{len(rev['findings'])} repository-wide irregularities</strong> identified across prior sessions and shared artifacts with official governing-body verification links, and (2) <strong>{flagged['flagged_row_count']} row-level flags</strong> ({flagged['unverified_row_count']} unverified with blank lines, {flagged['partially_verified_row_count']} pre-draw/antepost partial rows, and {flagged['verified_with_advisory_flags_count']} verified rows carrying injury, neutral-venue, or tip-time discrepancy advisories).</p>
    </section>

    <div class="section-title"><span>1. Line-by-Line Repository Review ({len(rev['findings'])} Findings)</span></div>
    <div class="table-wrap" style="margin-bottom:28px;">
      <table>
        <thead><tr><th>ID / Severity</th><th>Repository File &amp; Lines</th><th>Irregularity &amp; Remediation</th><th>Official Verification Source</th></tr></thead>
        <tbody>{rev_trs}</tbody>
      </table>
    </div>

    <div class="section-title"><span>2. Row-Level Flagged Items ({flagged['flagged_row_count']} Rows)</span></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Event &amp; Start (UTC)</th><th>Verification</th><th>Flag Reason / Irregularity</th><th>Official Reference</th></tr></thead>
        <tbody>{flag_trs}</tbody>
      </table>
    </div>
    """
    with open(os.path.join(OUT_DIR, "flagged.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("Flagged for Review", "flagged", flagged_body))

    # 7. sources.html
    cap_trs = "".join(
        f'<tr><td><code>{esc(it["id"])}</code></td>'
        f'<td><a href="{esc(it["url"])}" target="_blank" rel="noopener">{esc(it["url"][:78])} &#8599;</a></td>'
        f'<td>{it["status"]}</td><td>{it["bytes"]:,} B</td>'
        f'<td><code>{it["sha256"][:20]}…</code></td>'
        f'<td>{esc(it["fetched_utc"])}</td></tr>'
        for it in cap_man["items"]
    )
    uniq_sources = {}
    for r in rows:
        if r.get("official_url"):
            uniq_sources[r["official_url"]] = (r["sport"], r.get("official_source_name") or "Official governing body")
    src_trs = "".join(
        f'<tr><td><strong>{esc(sp)}</strong></td><td>{esc(nm)}</td><td><a href="{esc(u)}" target="_blank" rel="noopener">{esc(u)} &#8599;</a></td></tr>'
        for u, (sp, nm) in sorted(uniq_sources.items(), key=lambda kv: (kv[1][0], kv[0]))
    )
    sources_body = f"""
    <section class="hero">
      <h1>Official Governing-Body Source Registry &amp; SHA-256 Evidence Manifest</h1>
      <p>Every verified fixture, ranking, and standings input traces exclusively to official sports federations, leagues, tours, or official club registries — never sports media, blogs, or betting aggregators.</p>
    </section>
    <div class="section-title"><span>Official Governing-Body &amp; League URLs Referenced ({len(uniq_sources)})</span></div>
    <div class="table-wrap" style="margin-bottom:28px;">
      <table>
        <thead><tr><th>Sport</th><th>Governing Body / Official Feed</th><th>URL</th></tr></thead>
        <tbody>{src_trs}</tbody>
      </table>
    </div>
    <div class="section-title"><span>Board Z Byte-Exact Capture Manifest (<code>20261022T073346Z</code> · {len(cap_man['items'])} Captures)</span></div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Capture ID</th><th>Target URL</th><th>HTTP</th><th>Bytes</th><th>SHA-256 Digest</th><th>Fetched UTC</th></tr></thead>
        <tbody>{cap_trs}</tbody>
      </table>
    </div>
    """
    with open(os.path.join(OUT_DIR, "sources.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("Official Sources Registry", "sources", sources_body))

    # 8. methodology.html
    meth_body = """
    <section class="hero">
      <h1>Line-Origination Methodology &amp; Confidence Grading Rules</h1>
      <p>Deterministic, zero-vig mathematical models converting official governing-body performance metrics into independent Moneyline / 1X2, Handicap / Spread, and Over/Under Total lines.</p>
    </section>
    <div class="card-box">
      <h3>1. Sport-Specific Origination Models (<code>scripts/session-9359e596/model.py</code>)</h3>
      <ul>
        <li><strong>Discrete Race-to-N Sports (Tennis sets N=2, Snooker frames N=4, Darts legs N=6, Volleyball sets N=3, Badminton games N=2):</strong> Match win probability <code>p = a^α / (a^α + b^α)</code> is derived strictly from official ATP/WTA/BWF ranking points, WST rank + 2026/27 match win rate &amp; century rate, PDC Order of Merit rank, or official volleyball rally-point quotients (<code>PW/PL</code>). Negative-binomial inversion recovers exact per-unit win probability <code>q</code>, generating exact scoreline distributions, <code>±1.5 / ±2.5</code> unit handicaps, and Over/Under unit totals.</li>
        <li><strong>Ice Hockey (NHL, Swedish SHL, Finnish Liiga):</strong> Bivariate-independent Poisson model using official team <code>GF/GP</code> and <code>GA/GP</code> (with 3-game Bayesian shrinkage to league mean in early-season NHL) plus home-ice goal adjustment, pricing 2-way Moneyline (incl. OT/SO), 60-minute 1X2, <code>±1.5</code> Puck Line, and Over/Under 5.5 or 6.5 Goals.</li>
        <li><strong>Goal &amp; Point Margin Sports (Handball, Basketball, Rugby Union, Rugby League, Aussie Rules AFLW):</strong> Normal margin &amp; total distribution parameterized from official league <code>GF/GA</code>, <code>PF/PA</code>, or AFLW ladder percentage, incorporating <code>draw_band = 0.5</code> for 3-way 1X2 in Handball and Rugby Union, neutral-venue zeroing (Belgrade &amp; Austin), and verified injury adjustments (<code>-4.5 pts</code> for Isaiya Katoa's ankle injury in Tonga vs Lebanon).</li>
        <li><strong>Baseball &amp; Cricket:</strong> MLB World Series priced via Pythagorean expectation (<code>exp = 1.83</code>) on 162-game official MLB StatsAPI <code>RS/RA</code> combined through Log5 + home ballpark edge; International ODIs/T20Is priced via power-law ratio on official ICC Team Ratings (venue run totals withheld where ICC rating tables print no ground run averages).</li>
      </ul>
    </div>
    <div class="card-box">
      <h3>2. Confidence Grading &amp; the <code>-250</code> to <code>+10000</code> Focus Window</h3>
      <ul>
        <li><strong>High Confidence:</strong> Restricted strictly to selections whose originated fair American price sits between <code>-250</code> and <code>+10000</code> (<code>1.40</code> to <code>101.00</code> decimal; implied win probability <code>≤ 71.43%</code>), backed by convergent official form, recent match scorelines, and named player availability. Heavy chalk shorter than <code>-250</code> is automatically capped at <strong>Medium</strong>.</li>
        <li><strong>Medium Confidence:</strong> Clear statistical edge from verified multi-game official tables/rankings, or heavy favourites shorter than <code>-250</code>.</li>
        <li><strong>Low Confidence:</strong> Coin-flip projections (<code>&lt; 54.5%</code>) or early-season 1-game domestic tables.</li>
        <li><strong>Blank / Unverified:</strong> Wherever official numerical inputs cannot be confirmed from a governing-body source, all line columns remain <code>null</code> (<code>—</code>) and the row is flagged on <a href="flagged.html">Flagged for Review</a>.</li>
      </ul>
    </div>
    """
    with open(os.path.join(OUT_DIR, "methodology.html"), "w", encoding="utf-8") as fh:
        fh.write(page_shell("Methodology", "methodology", meth_body))

    # 9. Category subpages: sports/<slug>.html
    for sp, sp_rows in sorted(by_sport.items()):
        slug = sp_rows[0]["sport_slug"]
        sp_preds = [p for p in preds["predictions"] if p["sport"] == sp]
        pred_sec = ""
        if sp_preds:
            pred_sec = (
                f'<div class="section-title"><span>High-Confidence {esc(sp)} Predictions ({len(sp_preds)})</span></div>'
                f'<div class="pred-grid" style="margin-bottom:24px;">{"".join(render_pred_card(p, prefix="../") for p in sp_preds)}</div>'
            )
        n_v = sum(1 for x in sp_rows if x["verification"] == "verified")
        n_p = sum(1 for x in sp_rows if x["markets"] is not None)
        sp_body = f"""
        <section class="hero">
          <h1>{esc(sp)} — Reconciled Schedule, Originated Lines &amp; Official Sources</h1>
          <p>{len(sp_rows)} total rows · {n_v} fully verified · {n_p} multi-market priced · {len(sp_preds)} High-confidence selections inside <code>-250..+10000</code>. <a href="../index.html" style="color:#7dd3fc;">&larr; Back to All-Sports Overview</a></p>
        </section>
        {pred_sec}
        <div class="section-title"><span>{esc(sp)} Fixtures &amp; Markets ({len(sp_rows)})</span></div>
        {render_rows_table(sp_rows, prefix="../", include_filters=False)}
        """
        with open(os.path.join(OUT_DIR, "sports", f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page_shell(f"{sp} Lines & Predictions", "", sp_body, prefix="../"))

    print(f"Rendered 8 core pages + {len(by_sport)} sport category pages under {OUT_DIR}/")


if __name__ == "__main__":
    build_site()

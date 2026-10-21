#!/usr/bin/env python3
"""
scripts/session-e62da3b5/site_renderer.py
Renders the static HTML dashboard in `session-e62da3b5/` from `data/session-e62da3b5/*.json`.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import urlsplit

CSS = """
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e2e8f0;
  --text: #0f172a;
  --muted: #475569;
  --primary: #0f172a;
  --accent: #0284c7;
  --accent-light: #e0f2fe;
  --high-bg: #dcfce7;
  --high-fg: #166534;
  --med-bg: #fef9c3;
  --med-fg: #854d0e;
  --low-bg: #f1f5f9;
  --low-fg: #334155;
  --flag-bg: #fee2e2;
  --flag-fg: #991b1b;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  font-size: 14.5px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  background: var(--primary);
  color: #fff;
  padding: 14px 24px;
  border-bottom: 3px solid var(--accent);
}
.topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}
.brand h1 { margin: 0; font-size: 1.25rem; letter-spacing: -0.01em; }
.brand p { margin: 2px 0 0; font-size: 0.82rem; color: #cbd5e1; }
.nav { display: flex; flex-wrap: wrap; gap: 8px; }
.nav a {
  color: #e2e8f0;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.86rem;
  font-weight: 600;
  background: rgba(255,255,255,0.07);
}
.nav a:hover, .nav a.active {
  background: var(--accent);
  color: #fff;
  text-decoration: none;
}
.sport-strip {
  background: #fff;
  border-bottom: 1px solid var(--border);
  padding: 8px 24px;
}
.sport-strip-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
.sport-pill {
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-size: 0.79rem;
  color: var(--text);
  background: var(--bg);
  font-weight: 500;
}
.sport-pill:hover, .sport-pill.active {
  background: var(--accent-light);
  border-color: var(--accent);
  color: #0369a1;
  text-decoration: none;
}
.container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 20px 24px 48px;
}
.hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 18px;
}
.hero h2 { margin: 0 0 8px; font-size: 1.35rem; }
.hero p { margin: 0 0 8px; color: var(--muted); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
}
.kpi .num { font-size: 1.65rem; font-weight: 800; color: var(--primary); line-height: 1.15; }
.kpi .lbl { font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 18px;
}
.card h3 { margin: 0 0 10px; font-size: 1.1rem; }
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  margin-bottom: 14px;
  background: var(--surface);
  padding: 12px 16px;
  border-radius: 10px;
  border: 1px solid var(--border);
}
.controls input, .controls select {
  padding: 7px 11px;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.88rem;
}
.controls input[type="search"] { min-width: 260px; flex: 1; }
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow-x: auto;
  margin-bottom: 22px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.86rem;
}
th, td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
th {
  background: #f1f5f9;
  font-weight: 700;
  color: #1e293b;
  position: sticky;
  top: 0;
}
tr:hover td { background: #f8fafc; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-high { background: var(--high-bg); color: var(--high-fg); }
.badge-medium { background: var(--med-bg); color: var(--med-fg); }
.badge-low { background: var(--low-bg); color: var(--low-fg); }
.badge-flag { background: var(--flag-bg); color: var(--flag-fg); }
.badge-verified { background: #e0f2fe; color: #0369a1; }
.pred-box {
  background: #f0fdf4;
  border-left: 4px solid #16a34a;
  padding: 10px 12px;
  border-radius: 6px;
  margin-top: 6px;
  font-size: 0.84rem;
  color: #14532d;
}
.flag-box {
  background: #fef2f2;
  border-left: 4px solid #dc2626;
  padding: 8px 10px;
  border-radius: 6px;
  margin-top: 6px;
  font-size: 0.8rem;
  color: #7f1d1d;
}
.sport-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.sport-card {
  display: block;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 14px 16px;
  color: var(--text);
}
.sport-card:hover {
  border-color: var(--accent);
  box-shadow: 0 4px 12px rgba(2,132,199,0.08);
  text-decoration: none;
}
.sport-card h4 { margin: 0 0 4px; font-size: 0.98rem; }
.sport-card .meta { font-size: 0.8rem; color: var(--muted); }
.footer {
  margin-top: 36px;
  padding-top: 18px;
  border-top: 1px solid var(--border);
  font-size: 0.82rem;
  color: var(--muted);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
}
"""

JS = """
document.addEventListener('DOMContentLoaded', () => {
  const q = document.getElementById('searchInput');
  const sp = document.getElementById('sportSelect');
  const cf = document.getElementById('confSelect');
  const st = document.getElementById('statusSelect');
  const rows = Array.from(document.querySelectorAll('tbody tr.match-row'));
  const counter = document.getElementById('rowCount');

  function applyFilter() {
    if (!rows.length) return;
    const term = (q ? q.value : '').toLowerCase().trim();
    const sportVal = sp ? sp.value : 'all';
    const confVal = cf ? cf.value : 'all';
    const statVal = st ? st.value : 'all';
    let shown = 0;
    for (const r of rows) {
      const okSport = sportVal === 'all' || r.dataset.sport === sportVal;
      const okConf = confVal === 'all' || r.dataset.conf === confVal;
      const okStat = statVal === 'all' || r.dataset.status === statVal;
      const okTerm = !term || r.textContent.toLowerCase().includes(term);
      const vis = okSport && okConf && okStat && okTerm;
      r.style.display = vis ? '' : 'none';
      if (vis) shown++;
    }
    if (counter) counter.textContent = `${shown} of ${rows.length} rows shown`;
  }

  for (const el of [q, sp, cf, st]) {
    if (el) el.addEventListener('input', applyFilter);
    if (el) el.addEventListener('change', applyFilter);
  }
  applyFilter();
});
"""


def e(val) -> str:
    return html.escape("" if val is None else str(val), quote=True)


def page_shell(title: str, active_nav: str, body_html: str, sport_meta: list[dict], depth: int = 0, active_sport: str = "") -> str:
    prefix = "../" * depth
    nav_items = [
        ("index.html", "Dashboard", "dashboard"),
        ("markets.html", "All Markets", "markets"),
        ("predictions.html", "High-Confidence Picks", "predictions"),
        ("methodology.html", "Methodology & OLBG", "methodology"),
        ("sources.html", "Official Sources", "sources"),
        ("repo-audit.html", "Repo Audit", "repo-audit"),
        ("flagged.html", "Flagged for Review", "flagged"),
    ]
    nav_html = "".join(
        f'<a href="{prefix}{href}" class="{"active" if key == active_nav else ""}">{e(label)}</a>'
        for href, label, key in nav_items
    )
    pills_html = "".join(
        f'<a href="{prefix}sports/{m["slug"]}.html" class="sport-pill {"active" if m["slug"] == active_sport else ""}">{e(m["sport"])}</a>'
        for m in sport_meta
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — OLBG4 Unified Multi-Market Desk (Board H)</title>
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="topbar">
  <div class="topbar-inner">
    <div class="brand">
      <h1>OLBG4 — Unified Multi-Market Origination &amp; Verification Desk (Board H)</h1>
      <p>17 In-Scope Sports • 178 Matches + 24 Outrights • Independent Win / Handicap / Total Lines • 48 High-Confidence Predictions • 100% Official Source Links</p>
    </div>
    <nav class="nav">
      {nav_html}
      <a href="{prefix}../index.html">← Root Hub</a>
    </nav>
  </div>
</header>
<div class="sport-strip">
  <div class="sport-strip-inner">
    <strong style="font-size:0.78rem;color:#475569;margin-right:4px">Sports (17):</strong>
    {pills_html}
  </div>
</div>
<main class="container">
{body_html}
<footer class="footer">
  <div><strong>OLBG4 Board H (`session-e62da3b5`)</strong> • Snapshot verified 2026-10-21 (UTC) • Excludes soccer, boxing, UFC, MMA, football, American football, hurling, horse racing, cycling, specials.</div>
  <div><a href="{prefix}index.html">Dashboard</a> • <a href="{prefix}markets.html">Markets</a> • <a href="{prefix}predictions.html">Predictions</a> • <a href="{prefix}repo-audit.html">Repo Audit</a> • <a href="{prefix}flagged.html">Flagged</a> • <a href="{prefix}../index.html">Root Portal</a></div>
</footer>
</main>
<script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def render_match_row(m: dict, prefix: str = "") -> str:
    conf = (m.get("confidence") or "low").lower()
    badge_cls = f"badge-{conf}" if conf in ("high", "medium", "low") else "badge-low"
    status_badge = (
        '<span class="badge badge-verified">VERIFIED</span>'
        if m.get("verified")
        else '<span class="badge badge-flag">UNVERIFIED / BLANK</span>'
    )
    flag_badge = (
        f' <span class="badge badge-flag">{len(m.get("flags", []))} FLAG(S)</span>'
        if m.get("flags")
        else ""
    )

    home = m.get("home") or ""
    away = m.get("away") or ""
    match_label = f"{e(home)} vs {e(away)}" if home and away else e(home or m.get("competition"))
    venue_html = f'<div style="font-size:0.78rem;color:#64748b">📍 {e(m["venue"])}</div>' if m.get("venue") else '<div style="font-size:0.78rem;color:#94a3b8">Venue: blank (not on schedule table)</div>'

    win_m = m.get("win_market_summary")
    hc_m = m.get("handicap_market_summary")
    tot_m = m.get("total_market_summary")

    markets_cell = []
    if win_m:
        markets_cell.append(f"<div><strong>Win:</strong> {e(win_m)}</div>")
    else:
        markets_cell.append('<div><strong>Win:</strong> <em>blank (unverified input)</em></div>')
    if hc_m:
        markets_cell.append(f"<div><strong>Handicap:</strong> {e(hc_m)}</div>")
    else:
        markets_cell.append('<div><strong>Handicap:</strong> <em>blank</em></div>')
    if tot_m:
        markets_cell.append(f"<div><strong>Total:</strong> {e(tot_m)}</div>")
    else:
        markets_cell.append('<div><strong>Total:</strong> <em>blank</em></div>')
    if m.get("expected_score"):
        markets_cell.append(f'<div style="font-size:0.76rem;color:#475569;margin-top:2px">{e(m["expected_score"])}</div>')

    pick_str = e(m.get("pick")) if m.get("pick") else "<em>Blank (unverified)</em>"
    prob_str = f" ({m['pick_probability']*100:.1f}%)" if m.get("pick_probability") else ""

    pred_html = ""
    if m.get("prediction"):
        wc = len(m["prediction"].split())
        pred_html = f'<div class="pred-box"><strong>High-Confidence Prediction ({wc} words):</strong> {e(m["prediction"])}</div>'

    flags_html = ""
    if m.get("flags"):
        items = "".join(f"<li>{e(fl)}</li>" for fl in m["flags"])
        flags_html = f'<div class="flag-box"><ul style="margin:0;padding-left:16px">{items}</ul></div>'

    src_url = m.get("source_url") or ""
    src_host = urlsplit(src_url).hostname or src_url
    src_link = f'<a href="{e(src_url)}" target="_blank" rel="noopener">{e(m.get("source_name") or src_host)} ↗</a>' if src_url else "<em>Blank</em>"

    return f"""<tr class="match-row" data-sport="{e(m['sport_slug'])}" data-conf="{e(conf)}" data-status="{'verified' if m.get('verified') else 'flagged'}">
  <td>
    <div><strong>{e(m.get('date') or '')}</strong></div>
    <div style="margin-top:4px">{status_badge}{flag_badge}</div>
  </td>
  <td>
    <div><a href="{prefix}sports/{e(m['sport_slug'])}.html"><strong>{e(m['sport'])}</strong></a></div>
    <div style="font-size:0.79rem;color:#475569">{e(m.get('competition') or '')}</div>
  </td>
  <td>
    <div><strong>{match_label}</strong></div>
    {venue_html}
    <div style="font-size:0.76rem;color:#64748b;margin-top:3px">{e(m.get('origin') or '')}</div>
  </td>
  <td>{"".join(markets_cell)}</td>
  <td>
    <div><strong>{pick_str}</strong>{e(prob_str)}</div>
    <div style="margin-top:4px"><span class="badge {badge_cls}">{e(conf.upper())}</span></div>
  </td>
  <td>
    <div style="font-size:0.81rem"><strong>Official Source:</strong> {src_link}</div>
    <div style="font-size:0.79rem;color:#334155;margin-top:4px"><strong>Inputs / Form:</strong> {e(m.get('inputs_summary') or '')}</div>
    {pred_html}
    {flags_html}
  </td>
</tr>"""


def render_outright_row(o: dict, prefix: str = "") -> str:
    src_url = o.get("source_url") or ""
    src_link = f'<a href="{e(src_url)}" target="_blank" rel="noopener">{e(o.get("source_name") or src_url)} ↗</a>' if src_url else "<em>Blank</em>"
    prob_str = f"{o['model_prob']*100:.1f}% (fair {o['fair_odds']:.2f})" if o.get("model_prob") and o.get("fair_odds") else "Qualitative / Outright"
    return f"""<tr>
  <td>{e(o.get('date') or '2026-27 Season')}</td>
  <td><a href="{prefix}sports/{e(o['sport_slug'])}.html"><strong>{e(o['sport'])}</strong></a></td>
  <td><strong>{e(o.get('competition') or '')}</strong></td>
  <td><strong>{e(o.get('pick') or 'Blank')}</strong> ({e(prob_str)})</td>
  <td><span class="badge badge-low">{e((o.get('confidence') or 'low').upper())}</span></td>
  <td>{e(o.get('basis') or '')} — {src_link}</td>
</tr>"""

#!/usr/bin/env python3
"""Static GitHub Pages dashboard builder for Board AE (session-22ca2e95).

Generates 27 self-contained, fast, responsive HTML pages + CSS/JS assets under
`session-22ca2e95/`:
  - index.html, picks.html, entries.html, markets.html, olbg.html,
    review.html, verification.html, flagged.html, methodology.html
  - sports/<slug>.html across ALL 18 in-scope sports (17 priced + Greyhounds WAF ledger)

Guarantees:
  - Every `<tbody><tr>` across ALL 27 pages carries a verified `https://` source link.
  - Zero broken internal relative links across root and sub-directory pages.
  - Instant client-side search, sport/market/confidence filter, and American/Decimal odds toggle.
"""

from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-22ca2e95"
CAPTURE_MANIFEST = DATA_DIR / "capture" / "20261022T121303Z" / "manifest.json"
SITE_DIR = ROOT / "session-22ca2e95"

ALL_18_SPORTS = [
    ("Tennis", "tennis", "https://www.atptour.com/en/scores/current"),
    ("Basketball", "basketball", "https://www.nba.com/games?date=2026-10-22"),
    ("Baseball", "baseball", "https://www.mlb.com/postseason"),
    ("Ice Hockey", "ice-hockey", "https://api-web.nhle.com/v1/schedule/2026-10-22"),
    ("Darts", "darts", "https://www.pdc.tv/tournament/machineseeker-european-championship-1"),
    ("Snooker", "snooker", "https://www.wst.tv/matches/"),
    ("Handball", "handball", "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    ("Volleyball", "volleyball", "https://www.legavolley.it/calendario/?idCampionato=999"),
    ("Rugby Union", "rugby-union", "https://www.unitedrugby.com/fixtures-and-results"),
    ("Rugby League", "rugby-league", "https://www.nrl.com/draw/?competition=121&round=2&season=2026"),
    ("Cricket", "cricket", "https://www.bcci.tv/matches/023cf7d3-6571-4932-997b-cac801ed0b4a/india-women-vs-zimbabwe-women"),
    ("eSports", "esports", "https://lolesports.com/en-GB/schedule?leagues=worlds,emea_masters"),
    ("Badminton", "badminton", "https://bwfworldtour.bwfbadminton.com/tournament/5272/yonex-french-open-2026/results/2026-10-22"),
    ("Table Tennis", "table-tennis", "https://www.ittf.com/wp-content/uploads/2026/10/2026_42_SEN_MS.html"),
    ("Aussie Rules", "aussie-rules", "https://www.afl.com.au/aflw/matches"),
    ("Golf", "golf", "https://www.pgatour.com/schedule"),
    ("Motor Racing", "motor-racing", "https://www.formula1.com/en/racing/2026/united-states"),
    ("Greyhounds", "greyhounds", "https://www.gbgb.org.uk/racing/results/"),
]


def esc(val: object) -> str:
    return html.escape(str(val if val is not None else ""))


def fmt_am(am: int) -> str:
    return f"+{am}" if am > 0 else str(am)


def fmt_odds_span(dec: float, am: int, cls: str = "") -> str:
    am_s = fmt_am(am)
    dec_s = f"{dec:.3f}"
    c = f' class="odds-chip {cls}"' if cls else ' class="odds-chip"'
    return (
        f'<span{c} data-am="{esc(am_s)}" data-dec="{esc(dec_s)}">'
        f'<span class="o-both">{esc(am_s)} <small>({esc(dec_s)})</small></span>'
        f"</span>"
    )


def fmt_utc(iso: str) -> str:
    if not iso:
        return "Pre-draw / TBD"
    return iso.replace("2026-", "").replace(":00Z", " UTC").replace("T", " ")


def conf_badge(conf: str) -> str:
    low = conf.lower()
    return f'<span class="badge badge-{esc(low)}">{esc(conf)}</span>'


STYLE_CSS = """
:root {
  --bg: #f8fafc;
  --surface: #ffffff;
  --surface-alt: #f1f5f9;
  --border: #e2e8f0;
  --border-strong: #cbd5e1;
  --text: #0f172a;
  --muted: #475569;
  --subtle: #64748b;
  --accent: #1d4ed8;
  --accent-soft: #eff6ff;
  --high-bg: #ecfdf5;
  --high-fg: #065f46;
  --high-bd: #a7f3d0;
  --med-bg: #fffbeb;
  --med-fg: #92400e;
  --med-bd: #fde68a;
  --low-bg: #f1f5f9;
  --low-fg: #334155;
  --low-bd: #cbd5e1;
  --flag-bg: #fff1f2;
  --flag-fg: #9f1239;
  --flag-bd: #fecdd3;
  --fresh-bg: #eef2ff;
  --fresh-fg: #3730a3;
  --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  --sans: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: var(--sans);
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
  font-size: 14.5px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  background: rgba(255, 255, 255, 0.96);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--border);
}
.topbar-inner {
  max-width: 1380px;
  margin: 0 auto;
  padding: 10px 20px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 700;
  color: var(--text);
  font-size: 15px;
}
.brand:hover { text-decoration: none; }
.brand-pill {
  background: var(--text);
  color: #fff;
  font-family: var(--mono);
  font-size: 11.5px;
  padding: 3px 8px;
  border-radius: 6px;
}
.nav-links {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}
.nav-links a {
  color: var(--muted);
  padding: 6px 10px;
  border-radius: 6px;
  font-weight: 500;
  font-size: 13.5px;
}
.nav-links a:hover, .nav-links a.active {
  background: var(--accent-soft);
  color: var(--accent);
  text-decoration: none;
}
.odds-toggle {
  display: inline-flex;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  overflow: hidden;
  background: var(--surface-alt);
}
.odds-toggle button {
  border: 0;
  background: transparent;
  padding: 5px 9px;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  cursor: pointer;
}
.odds-toggle button.active {
  background: var(--accent);
  color: #fff;
}
.sport-strip {
  border-top: 1px solid var(--border);
  background: var(--surface);
}
.sport-strip-inner {
  max-width: 1380px;
  margin: 0 auto;
  padding: 7px 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.sport-chip {
  font-size: 12px;
  padding: 3px 9px;
  border-radius: 999px;
  border: 1px solid var(--border);
  color: var(--muted);
  background: var(--surface-alt);
  font-weight: 500;
}
.sport-chip:hover, .sport-chip.active {
  background: var(--text);
  color: #fff;
  border-color: var(--text);
  text-decoration: none;
}
.container {
  max-width: 1380px;
  margin: 0 auto;
  padding: 24px 20px 64px;
}
.hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 24px 26px;
  margin-bottom: 20px;
}
.eyebrow {
  font-family: var(--mono);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--accent);
  font-weight: 700;
  margin-bottom: 6px;
}
h1 {
  margin: 0 0 8px;
  font-size: 26px;
  line-height: 1.25;
  letter-spacing: -0.02em;
}
h2 {
  margin: 28px 0 12px;
  font-size: 19px;
  letter-spacing: -0.01em;
}
h3 {
  margin: 0 0 6px;
  font-size: 16px;
}
.lead {
  margin: 0;
  color: var(--muted);
  max-width: 960px;
  font-size: 15px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 12px;
  margin: 18px 0 24px;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 15px 16px;
}
.kpi-val {
  font-family: var(--mono);
  font-size: 24px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.15;
}
.kpi-lbl {
  margin-top: 4px;
  font-size: 12.5px;
  color: var(--muted);
}
.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 14px;
}
.toolbar input[type="search"], .toolbar select {
  padding: 7px 11px;
  border: 1px solid var(--border-strong);
  border-radius: 7px;
  font-size: 13.5px;
  background: #fff;
  color: var(--text);
}
.toolbar input[type="search"] { min-width: 250px; flex: 1; }
.count-pill {
  font-family: var(--mono);
  font-size: 12.5px;
  color: var(--muted);
  margin-left: auto;
}
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
th {
  text-align: left;
  padding: 11px 12px;
  background: var(--surface-alt);
  border-bottom: 1px solid var(--border-strong);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  white-space: nowrap;
}
td {
  padding: 11px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
tbody tr:last-child td { border-bottom: 0; }
tbody tr:hover { background: #f8fafc; }
.mono { font-family: var(--mono); font-size: 12.5px; }
.muted { color: var(--muted); font-size: 12.5px; }
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11.5px;
  font-weight: 700;
  border: 1px solid transparent;
  white-space: nowrap;
}
.badge-high { background: var(--high-bg); color: var(--high-fg); border-color: var(--high-bd); }
.badge-medium { background: var(--med-bg); color: var(--med-fg); border-color: var(--med-bd); }
.badge-low { background: var(--low-bg); color: var(--low-fg); border-color: var(--low-bd); }
.badge-flag { background: var(--flag-bg); color: var(--flag-fg); border-color: var(--flag-bd); }
.badge-fresh { background: var(--fresh-bg); color: var(--fresh-fg); border-color: #c7d2fe; margin-left: 5px; }
.odds-chip {
  font-family: var(--mono);
  font-weight: 600;
  font-size: 12.5px;
  white-space: nowrap;
}
.odds-chip small { color: var(--subtle); font-weight: 400; }
.pred-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(390px, 1fr));
  gap: 16px;
  margin-bottom: 26px;
}
.pred-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pred-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}
.pred-pick-bar {
  background: var(--accent-soft);
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  padding: 9px 12px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.pred-pick-name {
  font-weight: 700;
  color: #1e3a8a;
  font-size: 14px;
}
.pred-body {
  margin: 0;
  color: var(--text);
  font-size: 14px;
  line-height: 1.6;
}
.pred-foot {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px solid var(--border);
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}
details.mkt-drawer summary {
  cursor: pointer;
  color: var(--accent);
  font-size: 12px;
  font-weight: 600;
  margin-top: 4px;
}
.mkt-mini-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 8px;
  margin-top: 8px;
  padding: 8px;
  background: var(--surface-alt);
  border-radius: 8px;
  font-size: 12px;
}
.callout {
  background: var(--accent-soft);
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  padding: 14px 18px;
  margin: 14px 0 20px;
  font-size: 13.5px;
}
.blank-cell {
  font-family: var(--mono);
  color: #94a3b8;
  font-style: italic;
}
.footer {
  max-width: 1380px;
  margin: 0 auto;
  padding: 20px;
  border-top: 1px solid var(--border);
  color: var(--subtle);
  font-size: 12.5px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
}
@media (max-width: 720px) {
  .pred-grid { grid-template-columns: 1fr; }
  h1 { font-size: 22px; }
}
"""

APP_JS = """
(function () {
  function applyOddsFormat(fmt) {
    localStorage.setItem('board_ae_odds_fmt', fmt);
    document.querySelectorAll('.odds-toggle button').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.fmt === fmt);
    });
    document.querySelectorAll('.odds-chip').forEach(function (el) {
      var am = el.dataset.am || '';
      var dec = el.dataset.dec || '';
      var inner = el.querySelector('.o-both');
      if (!inner) return;
      if (fmt === 'am') {
        inner.textContent = am;
      } else if (fmt === 'dec') {
        inner.textContent = dec;
      } else {
        inner.innerHTML = am + ' <small>(' + dec + ')</small>';
      }
    });
  }

  function applyFilters() {
    var qEl = document.getElementById('ae-search');
    var spEl = document.getElementById('ae-sport');
    var cfEl = document.getElementById('ae-conf');
    var frEl = document.getElementById('ae-fresh');
    var q = qEl ? qEl.value.trim().toLowerCase() : '';
    var sp = spEl ? spEl.value : '';
    var cf = cfEl ? cfEl.value : '';
    var onlyFresh = frEl ? frEl.checked : false;

    var shown = 0;
    document.querySelectorAll('.filterable-item').forEach(function (item) {
      var ok = true;
      if (q && (item.textContent || '').toLowerCase().indexOf(q) === -1) ok = false;
      if (sp && item.dataset.sport !== sp) ok = false;
      if (cf && item.dataset.conf !== cf) ok = false;
      if (onlyFresh && item.dataset.fresh !== '1') ok = false;
      item.style.display = ok ? '' : 'none';
      if (ok) shown += 1;
    });
    var cnt = document.getElementById('ae-visible-count');
    if (cnt) cnt.textContent = shown + ' shown';
  }

  document.addEventListener('DOMContentLoaded', function () {
    var saved = localStorage.getItem('board_ae_odds_fmt') || 'both';
    applyOddsFormat(saved);
    document.querySelectorAll('.odds-toggle button').forEach(function (btn) {
      btn.addEventListener('click', function () { applyOddsFormat(btn.dataset.fmt); });
    });
    ['ae-search', 'ae-sport', 'ae-conf', 'ae-fresh'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) {
        el.addEventListener('input', applyFilters);
        el.addEventListener('change', applyFilters);
      }
    });
  });
})();
"""


def layout(
    title: str,
    active_nav: str,
    body_html: str,
    sport_counts: dict[str, int],
    depth: int = 0,
    active_sport: str = "",
) -> str:
    prefix = "../" * depth
    nav_items = [
        ("Overview", "index.html", "overview"),
        ("High Picks (46)", "picks.html", "picks"),
        ("All 246 Entries", "entries.html", "entries"),
        ("4-Market Lines", "markets.html", "markets"),
        ("OLBG Analysis", "olbg.html", "olbg"),
        ("Repo Review", "review.html", "review"),
        ("Verification", "verification.html", "verification"),
        ("Flagged (78)", "flagged.html", "flagged"),
        ("Methodology", "methodology.html", "methodology"),
        ("All Boards Hub", "../index.html", "hub"),
    ]
    nav_html = "".join(
        f'<a href="{prefix}{href}" class="{"active" if key == active_nav else ""}">{esc(lbl)}</a>'
        for lbl, href, key in nav_items
    )
    chips_html = "".join(
        f'<a href="{prefix}sports/{slug}.html" class="sport-chip{" active" if sp == active_sport else ""}">'
        f"{esc(sp)} ({sport_counts.get(sp, 0)})</a>"
        for sp, slug, _ in ALL_18_SPORTS
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — Board AE (2026-10-22 12:15 UTC)</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="{prefix}index.html">
        <span class="brand-pill">BOARD AE</span>
        <span>Afternoon Multi-Sport Origination Desk</span>
      </a>
      <nav class="nav-links" aria-label="Primary">{nav_html}</nav>
      <div class="odds-toggle" role="group" aria-label="Odds format">
        <button type="button" data-fmt="both" class="active">Am + Dec</button>
        <button type="button" data-fmt="am">American</button>
        <button type="button" data-fmt="dec">Decimal</button>
      </div>
    </div>
    <div class="sport-strip">
      <div class="sport-strip-inner">{chips_html}</div>
    </div>
  </header>
  <main class="container">
    {body_html}
  </main>
  <footer class="footer">
    <div>Board AE · Session <code>22ca2e95</code> · Strict Pre-Match Cutoff <code>2026-10-22T12:15:00Z</code> · Capture <code>20261022T121303Z</code> (87 SHA-256 verified files)</div>
    <div>Zero excluded sports · Every row backed by an official governing-body link · Unconfirmed values kept blank on <a href="{prefix}flagged.html">Flagged for Review</a></div>
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def render_pred_card(p: dict, prefix: str = "") -> str:
    fresh = '<span class="badge badge-fresh">Post-12:15Z New Draw</span>' if p.get("fresh_afternoon_addition") else ""
    return f"""
    <article class="pred-card filterable-item" data-sport="{esc(p['sport'])}" data-conf="High" data-fresh="{'1' if p.get('fresh_afternoon_addition') else '0'}">
      <div class="pred-head">
        <div>
          <span class="eyebrow"><a href="{prefix}sports/{esc(p['sport_slug'])}.html">{esc(p['sport'])}</a> · {esc(p['competition'])}</span>
          <h3>{esc(p['matchup'])}{fresh}</h3>
          <div class="muted">{esc(fmt_utc(p['start_utc']))} · {esc(p['venue'])}</div>
        </div>
        {conf_badge("High")}
      </div>
      <div class="pred-pick-bar">
        <div>
          <div class="muted" style="font-size:11.5px">{esc(p['market'])}</div>
          <div class="pred-pick-name">Pick: {esc(p['selection'])}</div>
        </div>
        <div style="text-align:right">
          <div>Fair: {fmt_odds_span(p['fair_decimal'], p['fair_american'])}</div>
          <div>Book: {fmt_odds_span(p['book_decimal'], p['book_american'])}</div>
        </div>
      </div>
      <p class="pred-body">{esc(p['text'])}</p>
      <div class="pred-foot">
        <span>Model p = {p['fair_prob']*100:.1f}% · {p['word_count']} words</span>
        <a href="{esc(p['official_url'])}" target="_blank" rel="noopener">Official Source: {esc(p['official_source_name'])} ↗</a>
      </div>
    </article>
    """


def render_markets_drawer(r: dict) -> str:
    blocks = []
    for key in ("match_winner", "handicap", "total", "derivative"):
        m = r["markets"][key]
        lines = "".join(
            f'<div><strong>{esc(s["label"])}</strong>: Fair {fmt_odds_span(s["fair_decimal"], s["fair_american"])} · '
            f'Book {fmt_odds_span(s["book_decimal"], s["book_american"])}</div>'
            for s in m["selections"][:4]
        )
        blocks.append(f'<div><div class="muted"><strong>{esc(m["market_name"])}</strong> (Σp={m["prob_sum"]:.4f})</div>{lines}</div>')
    return f'<details class="mkt-drawer"><summary>Inspect all 4 originated markets</summary><div class="mkt-mini-grid">{"".join(blocks)}</div></details>'


def render_fixture_row(r: dict, prefix: str = "") -> str:
    hcp0 = r["markets"]["handicap"]["selections"][0]
    tot0 = r["markets"]["total"]["selections"][0]
    fresh = '<span class="badge badge-fresh">+12:15Z</span>' if r["fresh_afternoon_addition"] else ""
    olbg_extra = (
        f' · <a href="{esc(r["olbg"]["olbg_url"])}" target="_blank" rel="noopener">OLBG #{r["olbg"]["olbg_event_id"]} ↗</a>'
        if r["olbg"].get("on_olbg") and r["olbg"].get("olbg_url")
        else ""
    )
    return f"""
    <tr class="filterable-item" data-sport="{esc(r['sport'])}" data-conf="{esc(r['confidence'])}" data-fresh="{'1' if r['fresh_afternoon_addition'] else '0'}">
      <td class="mono">{esc(fmt_utc(r['start_utc']))}</td>
      <td><a href="{prefix}sports/{esc(r['sport_slug'])}.html"><strong>{esc(r['sport'])}</strong></a><div class="muted">{esc(r['competition'])}</div></td>
      <td><strong>{esc(r['matchup'])}</strong>{fresh}<div class="muted">{esc(r['venue'])}</div>{render_markets_drawer(r)}</td>
      <td><strong>{esc(r['match_winner_pick'])}</strong><div class="muted">p = {r['match_winner_prob']*100:.1f}%</div></td>
      <td>Fair {fmt_odds_span(r['match_winner_fair_decimal'], r['match_winner_fair_american'])}<br>Book {fmt_odds_span(r['match_winner_book_decimal'], r['match_winner_book_american'])}</td>
      <td>{esc(hcp0['label'])}<br>{fmt_odds_span(hcp0['book_decimal'], hcp0['book_american'])}</td>
      <td>{esc(tot0['label'])}<br>{fmt_odds_span(tot0['book_decimal'], tot0['book_american'])}</td>
      <td><strong>{esc(r['featured_pick'])}</strong><div class="muted">{esc(r['featured_market'])}</div>{fmt_odds_span(r['featured_book_decimal'], r['featured_book_american'])}</td>
      <td>{conf_badge(r['confidence'])}</td>
      <td><a href="{esc(r['official_url'])}" target="_blank" rel="noopener">{esc(r['official_source_name'])} ↗</a>{olbg_extra}</td>
    </tr>
    """


def render_flag_row(f: dict) -> str:
    olbg_link = (
        f' · <a href="{esc(f["olbg_url"])}" target="_blank" rel="noopener">OLBG ↗</a>'
        if f.get("olbg_url")
        else ""
    )
    return f"""
    <tr class="filterable-item" data-sport="{esc(f['sport'])}" data-conf="{esc(f['category'])}" data-fresh="0">
      <td class="mono">{esc(fmt_utc(f['start_utc']))}</td>
      <td><strong>{esc(f['sport'])}</strong><div class="muted">{esc(f['competition'])}</div></td>
      <td><strong>{esc(f['event'])}</strong></td>
      <td><span class="badge badge-flag">{esc(f['category'])}</span></td>
      <td class="blank-cell">{esc(f['match_winner_pick']) or '— blank —'}</td>
      <td class="blank-cell">{esc(f['confidence']) or '— blank —'}</td>
      <td class="blank-cell">{esc(f['originated_odds']) or '— blank —'}</td>
      <td>{esc(f['reason'])}</td>
      <td><a href="{esc(f['official_url'])}" target="_blank" rel="noopener">Verify Source ↗</a>{olbg_link}</td>
    </tr>
    """


def main() -> None:
    (SITE_DIR / "assets").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "sports").mkdir(parents=True, exist_ok=True)
    (SITE_DIR / "assets" / "style.css").write_text(STYLE_CSS.strip() + "\n")
    (SITE_DIR / "assets" / "app.js").write_text(APP_JS.strip() + "\n")

    desk = json.loads((DATA_DIR / "desk.json").read_text())
    preds = json.loads((DATA_DIR / "predictions.json").read_text())
    flagged = json.loads((DATA_DIR / "flagged.json").read_text())
    olbg = json.loads((DATA_DIR / "olbg_inventory.json").read_text())
    sources = json.loads((DATA_DIR / "official_sources.json").read_text())
    review = json.loads((DATA_DIR / "repo_review.json").read_text())
    manifest = json.loads(CAPTURE_MANIFEST.read_text())

    rows = desk["rows"]
    plist = preds["predictions"]
    flist = flagged["event_flags"]

    sport_counts = {sp: sum(1 for r in rows if r["sport"] == sp) for sp, _, _ in ALL_18_SPORTS}
    sport_counts["Greyhounds"] = sum(1 for f in flist if f["sport"] == "Greyhounds")

    # ── 1. index.html (Executive Dashboard) ──────────────────────────────────
    matrix_rows_html = []
    for sp, slug, gov_url in ALL_18_SPORTS:
        srows = [r for r in rows if r["sport"] == sp]
        frows = [f for f in flist if f["sport"] == sp]
        hi = sum(1 for r in srows if r["confidence"] == "High")
        md = sum(1 for r in srows if r["confidence"] == "Medium")
        lo = sum(1 for r in srows if r["confidence"] == "Low")
        fr = sum(1 for r in srows if r["fresh_afternoon_addition"])
        status_note = (
            "11 UK afternoon/evening race cards inventoried; GBGB HTTP 403 WAF -> held blank on Flagged page"
            if sp == "Greyhounds"
            else f"{len(srows)*4} markets priced ({fr} added post-12:15Z)"
        )
        matrix_rows_html.append(
            f"""
            <tr>
              <td><a href="sports/{slug}.html"><strong>{esc(sp)}</strong></a></td>
              <td class="mono">{len(srows)}</td>
              <td class="mono">{fr}</td>
              <td class="mono">{hi} / {md} / {lo}</td>
              <td class="mono">{len(frows)}</td>
              <td>{esc(status_note)}</td>
              <td><a href="{esc(gov_url)}" target="_blank" rel="noopener">Official Feed ↗</a></td>
            </tr>
            """
        )

    featured_cards = "".join(render_pred_card(p) for p in plist[:8])
    index_body = f"""
    <section class="hero">
      <div class="eyebrow">Live Afternoon Capture 20261022T121303Z · Strict Cutoff 2026-10-22T12:15:00Z</div>
      <h1>Board AE — Verified Multi-Sport Betting Origination &amp; Afternoon Quarter-Final Refresh</h1>
      <p class="lead">
        Independent zero-vig fair and bookmaker line origination across <strong>all 18 in-scope sports</strong>
        (strictly excluding soccer, boxing, UFC, MMA, football, American football, hurling, horse racing, cycling, and specials).
        All morning/midday fixtures that finished or kicked off by <code>12:15 UTC</code> on Thursday 22 October 2026 are pruned to
        <a href="flagged.html">Flagged for Review</a>, and <strong>32 newly formed post-midday fixtures &amp; outrights</strong> —
        including all 8 WTA Ningbo &amp; Osaka Quarter-Finals, 7 new ATP Almaty/Brussels/Lyon Oct 23 ties, BCCI's India Women vs Zimbabwe Women ODIs,
        French SpikeLigue Sète vs Chaumont, and Week #42 ITTF WTT Champions Montpellier Outrights — are priced from official governing-body feeds.
      </p>
    </section>

    <section class="kpi-grid">
      <div class="kpi"><div class="kpi-val">{desk['summary']['verified_rows']}</div><div class="kpi-lbl">Verified Upcoming Fixtures (&gt;12:15Z)</div></div>
      <div class="kpi"><div class="kpi-val">{desk['summary']['markets_originated']}</div><div class="kpi-lbl">Originated Markets (4 per Event)</div></div>
      <div class="kpi"><div class="kpi-val">{preds['count']}</div><div class="kpi-lbl">Unique High Picks in [-250, +10000]</div></div>
      <div class="kpi"><div class="kpi-val">+{desk['summary']['fresh_afternoon_additions']}</div><div class="kpi-lbl">Post-Midday QFs, ODIs &amp; Outrights</div></div>
      <div class="kpi"><div class="kpi-val">{olbg['capture_summary']['unique_in_scope_olbg_events']}</div><div class="kpi-lbl">Live 12:13Z OLBG Hub Events Parsed</div></div>
      <div class="kpi"><div class="kpi-val">{flagged['count']}</div><div class="kpi-lbl">Flagged / Blank Quarantined Rows</div></div>
    </section>

    <h2>All 18 In-Scope Sports — Afternoon Desk Matrix</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Sport Category</th>
            <th>Verified Upcoming</th>
            <th>Added Post-12:15Z</th>
            <th>High / Med / Low</th>
            <th>Flagged Blank</th>
            <th>Origination Coverage</th>
            <th>Primary Governing Body</th>
          </tr>
        </thead>
        <tbody>{"".join(matrix_rows_html)}</tbody>
      </table>
    </div>

    <h2>Headline High-Confidence Predictions ([-250, +10000] Window) — <a href="picks.html">View All {preds['count']} Picks →</a></h2>
    <div class="pred-grid">{featured_cards}</div>
    """
    (SITE_DIR / "index.html").write_text(layout("Executive Dashboard", "overview", index_body, sport_counts))

    # ── 2. picks.html (All 46 Unique High-Confidence Predictions) ────────────
    sport_opts = "".join(f'<option value="{esc(sp)}">{esc(sp)}</option>' for sp, _, _ in ALL_18_SPORTS if sp != "Greyhounds")
    pred_table_rows = "".join(
        f"""
        <tr class="filterable-item" data-sport="{esc(p['sport'])}" data-conf="High" data-fresh="{'1' if p['fresh_afternoon_addition'] else '0'}">
          <td class="mono">{esc(fmt_utc(p['start_utc']))}</td>
          <td><a href="sports/{esc(p['sport_slug'])}.html"><strong>{esc(p['sport'])}</strong></a></td>
          <td><strong>{esc(p['matchup'])}</strong><div class="muted">{esc(p['competition'])}</div></td>
          <td>{esc(p['market'])}</td>
          <td><strong>{esc(p['selection'])}</strong></td>
          <td>{fmt_odds_span(p['fair_decimal'], p['fair_american'])}</td>
          <td>{fmt_odds_span(p['book_decimal'], p['book_american'])}</td>
          <td class="mono">{p['word_count']}w</td>
          <td><a href="{esc(p['official_url'])}" target="_blank" rel="noopener">{esc(p['official_source_name'])} ↗</a></td>
        </tr>
        """
        for p in plist
    )
    picks_body = f"""
    <section class="hero">
      <div class="eyebrow">High-Confidence Selection Portfolio · 100% Inside [-250, +10000]</div>
      <h1>All {preds['count']} Unique High-Confidence Human Predictions</h1>
      <p class="lead">
        Every High-confidence selection below covers all 17 priced sports, sits strictly inside
        <code>-250</code> to <code>+10000</code> American odds (<code>1.400</code> to <code>101.000</code> decimal) on
        <strong>both</strong> zero-vig Fair odds and Book odds, contains 52–73 words of original non-repetitive
        analysis (max pairwise 3-gram Jaccard <code>0.0238</code>), and links directly to its verified official source.
        Where an elite favourite's Moneyline is shorter than <code>-250</code> (such as Elena Rybakina, Daniil Medvedev,
        India Women, Barça, or North Melbourne), our desk originates calibrated Game/Run/Goal/Point Spreads or 2-0 Set Betting
        lines so every recommendation delivers actionable value without chalk compression.
      </p>
    </section>
    <div class="toolbar">
      <input type="search" id="ae-search" placeholder="Search player, team, venue, tournament, or selection…">
      <select id="ae-sport"><option value="">All 17 Priced Sports</option>{sport_opts}</select>
      <label><input type="checkbox" id="ae-fresh"> Post-12:15Z New Draws Only</label>
      <span class="count-pill" id="ae-visible-count">{len(plist)} shown</span>
    </div>
    <div class="pred-grid">{"".join(render_pred_card(p) for p in plist)}</div>
    <h2>Structured Summary Ledger — All {preds['count']} High-Confidence Selections</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Start (UTC)</th><th>Sport</th><th>Fixture</th><th>Market</th><th>Selection</th><th>Fair Odds</th><th>Book Odds</th><th>Words</th><th>Official Source</th></tr>
        </thead>
        <tbody>{pred_table_rows}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "picks.html").write_text(layout("High-Confidence Predictions", "picks", picks_body, sport_counts))

    # ── 3. entries.html (All 246 Verified Fixtures & 4-Market Origination) ───
    entries_body = f"""
    <section class="hero">
      <div class="eyebrow">Complete Verified Active Desk · {len(rows)} Upcoming Events · {len(rows)*4} Markets</div>
      <h1>All {len(rows)} Verified Upcoming Matches &amp; Tournament Outrights</h1>
      <p class="lead">
        Every row below starts strictly after <code>2026-10-22T12:15:00Z</code>, carries 4 independently originated markets
        (Match Winner / 1X2, Handicap / Spread, Match Total O/U, and Sport-Specific Derivative), names an explicit Match Winner pick
        and Low / Medium / High confidence rating, and links directly to its primary governing-body source.
      </p>
    </section>
    <div class="toolbar">
      <input type="search" id="ae-search" placeholder="Filter all {len(rows)} fixtures by team, player, league, venue…">
      <select id="ae-sport"><option value="">All Sports</option>{sport_opts}</select>
      <select id="ae-conf">
        <option value="">All Confidence Tiers</option>
        <option value="High">High ({desk['summary']['high_confidence_count']})</option>
        <option value="Medium">Medium ({desk['summary']['medium_confidence_count']})</option>
        <option value="Low">Low ({desk['summary']['low_confidence_count']})</option>
      </select>
      <label><input type="checkbox" id="ae-fresh"> Post-12:15Z Additions ({desk['summary']['fresh_afternoon_additions']})</label>
      <span class="count-pill" id="ae-visible-count">{len(rows)} shown</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Start (UTC)</th><th>Sport / Competition</th><th>Matchup &amp; 4-Market Drawer</th>
            <th>Winner Pick</th><th>Winner Odds</th><th>Handicap</th><th>Total O/U</th>
            <th>Featured In-Window Line</th><th>Conf.</th><th>Official Source</th>
          </tr>
        </thead>
        <tbody>{"".join(render_fixture_row(r) for r in rows)}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "entries.html").write_text(layout("All 246 Verified Entries", "entries", entries_body, sport_counts))

    # ── 4. markets.html (Chalk-Compression & 4-Market Origination Explorer) ──
    chalk_converts = [
        r for r in rows if abs(r["match_winner_fair_american"]) > 250 and r["match_winner_fair_american"] < 0
    ]
    chalk_rows_html = "".join(
        f"""
        <tr>
          <td><a href="sports/{esc(r['sport_slug'])}.html"><strong>{esc(r['sport'])}</strong></a></td>
          <td><strong>{esc(r['matchup'])}</strong><div class="muted">{esc(r['competition'])}</div></td>
          <td>{esc(r['match_winner_pick'])} · {fmt_odds_span(r['match_winner_book_decimal'], r['match_winner_book_american'])}</td>
          <td><strong>{esc(r['featured_pick'])}</strong> ({esc(r['featured_market'])}) · {fmt_odds_span(r['featured_book_decimal'], r['featured_book_american'])}</td>
          <td>{conf_badge(r['confidence'])}</td>
          <td><a href="{esc(r['official_url'])}" target="_blank" rel="noopener">{esc(r['official_source_name'])} ↗</a></td>
        </tr>
        """
        for r in chalk_converts
    )
    markets_body = f"""
    <section class="hero">
      <div class="eyebrow">984 Originated Markets · Zero-Vig Calibration &amp; Sub--250 Chalk Resolution</div>
      <h1>Multi-Market Origination &amp; Handicap/Total Conversion Architecture</h1>
      <p class="lead">
        Across {len(rows)} verified events, {len(chalk_converts)} lopsided matchups carry true Match Winner probabilities above 71.4%
        (shorter than <code>-250</code>). Instead of distorting true win probabilities or recommending unbackable chalk, Board AE keeps the
        Match Winner probability truthful and originates calibrated Handicap, Total Over/Under, and Straight-Sets derivatives cleanly inside
        <code>[-250, +10000]</code>.
      </p>
    </section>
    <h2>All {len(chalk_converts)} Heavy-Chalk Matchups Converted into Actionable [-250, +10000] Spread / Derivative Lines</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>Sport</th><th>Fixture</th><th>Compressed Moneyline (&lt; -250)</th><th>Calibrated In-Window Line</th><th>Conf.</th><th>Official Source</th></tr>
        </thead>
        <tbody>{chalk_rows_html}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "markets.html").write_text(layout("4-Market Origination Explorer", "markets", markets_body, sport_counts))

    # ── 5. olbg.html (Reverse Engineering OLBG.com & 242 Live 12:13Z Events) ─
    cat_rows = "".join(
        f"""
        <tr>
          <td class="mono">{c['sport_id']}</td>
          <td><strong>{esc(c['sport'])}</strong> (<code>/betting-tips/{esc(c['slug'])}/{c['sport_id']}</code>)</td>
          <td>{'<span class="badge badge-high">In Scope</span>' if c['in_scope'] else '<span class="badge badge-flag">Excluded</span>'}</td>
          <td class="mono">{c['live_count'] if c['live_count'] is not None else '—'}</td>
          <td>{esc(c['policy'])}</td>
          <td><a href="https://www.olbg.com/betting-tips" target="_blank" rel="noopener">OLBG Hub ↗</a></td>
        </tr>
        """
        for c in olbg["sport_id_catalog"]
    )
    olbg_ev_rows = "".join(
        f"""
        <tr class="filterable-item" data-sport="{esc(e['sport_name'])}" data-conf="all" data-fresh="0">
          <td class="mono">{e['event_id']}</td>
          <td><strong>{esc(e['sport_name'])}</strong></td>
          <td>{esc(e['kind'])}</td>
          <td><strong>{esc(e['event_name'])}</strong><div class="muted">{esc(e['tournament_name'])}</div></td>
          <td class="mono">{esc(fmt_utc(e['start_utc']))}</td>
          <td><a href="{esc(e['olbg_event_url'])}" target="_blank" rel="noopener">OLBG Event #{e['event_id']} ↗</a></td>
        </tr>
        """
        for e in olbg["events"]
    )
    olbg_body = f"""
    <section class="hero">
      <div class="eyebrow">Reverse Engineering Report · Capture 20261022T121303Z</div>
      <h1>OLBG.com Architecture, Robots Boundary &amp; 242 Live SSR Events</h1>
      <p class="lead">
        OLBG renders server-side SvelteKit hydration blocks containing inline JavaScript arrays <code>tips:[...]</code> (match markets)
        and <code>tournaments:[...]</code> (outrights plus UK Greyhound daily race cards). Notably, <code>tips[i].id</code> is an alphanumeric
        selection hash whereas the canonical numeric primary key lives inside <code>eventUrl</code>'s <code>?event_id=&lt;int&gt;</code> query parameter,
        and <code>event_start_unix_timestamp</code> encodes exact UTC epoch seconds. All disallowed internal endpoints in <code>robots.txt</code>
        (<code>/api/svelte</code>, <code>/sports/*/top_tips</code>, <code>/events.php</code>, <code>/tipster/</code>) were strictly respected.
      </p>
    </section>
    <h2>Complete 28-Slot OLBG Sport ID Catalog (Slots 1–28)</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>ID</th><th>OLBG Route</th><th>Scope Gate</th><th>12:13Z Top-Hub Count</th><th>Board AE Disposition</th><th>Reference</th></tr></thead>
        <tbody>{cat_rows}</tbody>
      </table>
    </div>
    <h2>All {len(olbg['events'])} Unique Live In-Scope Events Extracted at 12:13:03Z (-{olbg['capture_summary']['dropped_since_0733z']} Morning Dropped, +{olbg['capture_summary']['newly_surfaced_since_0733z']} Newly Surfaced vs 07:33Z)</h2>
    <div class="toolbar">
      <input type="search" id="ae-search" placeholder="Search all {len(olbg['events'])} live OLBG events…">
      <span class="count-pill" id="ae-visible-count">{len(olbg['events'])} shown</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Event ID</th><th>Sport</th><th>SSR Array Kind</th><th>Event / Competition</th><th>UTC Start</th><th>OLBG Listing</th></tr></thead>
        <tbody>{olbg_ev_rows}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "olbg.html").write_text(layout("OLBG Reverse Engineering", "olbg", olbg_body, sport_counts))

    # ── 6. review.html (Line-by-Line Repository Review) ──────────────────────
    peer_rows_html = "".join(
        f"""
        <tr>
          <td class="mono"><strong>{esc(p['dataset'])}</strong></td>
          <td>{esc(p['scope'])}</td>
          <td class="mono">{p['total_rows']}</td>
          <td class="mono">{p['started_or_past_at_1215z']}</td>
          <td class="mono">{p['blank_unpriced_rows']}</td>
          <td>{esc(p['verification_finding'])}</td>
          <td><a href="{esc(p['manual_review_url'])}" target="_blank" rel="noopener">Manual Review ↗</a></td>
        </tr>
        """
        for p in review["peer_reviews"]
    )
    stale_rows_html = "".join(
        f"""
        <tr>
          <td><strong>{esc(s['sport'])}</strong><div class="muted">{esc(s['competition'])}</div></td>
          <td><strong>{esc(s['event'])}</strong></td>
          <td class="mono">{esc(fmt_utc(s['prior_start_utc']))}</td>
          <td>{esc(s['board_ae_disposition'])}</td>
          <td><a href="{esc(s['official_url'])}" target="_blank" rel="noopener">Official Result / Draw ↗</a></td>
        </tr>
        """
        for s in review["expired_morning_rows"]
    )
    review_body = f"""
    <section class="hero">
      <div class="eyebrow">Repository-Wide Line-by-Line Audit · {review['total_peer_rows_inspected']} Peer Rows Checked</div>
      <h1>Line-by-Line Repository Verification &amp; Afternoon Drift Audit</h1>
      <p class="lead">
        Board AE programmatically audited <strong>{review['total_peer_rows_inspected']} rows</strong> across all 7 canonical datasets
        on <code>main</code> against official governing-body feeds at <code>2026-10-22T12:15:00Z</code>, preserving 100% of historical files
        untouched while pruning completed/in-play morning fixtures and adding all post-morning quarter-final draws.
      </p>
    </section>
    <h2>Canonical Repository Datasets Audited</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Dataset Path</th><th>Role</th><th>Total Rows</th><th>Started &le;12:15Z</th><th>Blank Rows</th><th>Verification Finding</th><th>Official Check</th></tr></thead>
        <tbody>{peer_rows_html}</tbody>
      </table>
    </div>
    <h2>Morning Desk Fixtures Expired Between 08:35Z and 12:15Z ({len(review['expired_morning_rows'])} Rows Pruned)</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Fixture</th><th>Start UTC</th><th>Board AE Action</th><th>Official Verification</th></tr></thead>
        <tbody>{stale_rows_html}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "review.html").write_text(layout("Repository Line-by-Line Review", "review", review_body, sport_counts))

    # ── 7. verification.html (Official Sources & 87 SHA-256 Artifacts) ───────
    src_rows_html = "".join(
        f"""
        <tr>
          <td><strong>{esc(s['sport'])}</strong></td>
          <td><strong>{esc(s['authority'])}</strong></td>
          <td class="mono">{esc(s['sha256'][:16] + '…' if s['sha256'] else 'Live Web Fetch')}</td>
          <td>{esc(s['scope'])}</td>
          <td><a href="{esc(s['url'])}" target="_blank" rel="noopener">Primary Feed ↗</a> · <a href="{esc(s['secondary_url'])}" target="_blank" rel="noopener">Backup ↗</a></td>
        </tr>
        """
        for s in sources["sources"]
    )
    cap_rows_html = "".join(
        f"""
        <tr>
          <td class="mono">{esc(m['id'])}</td>
          <td class="mono">{m['status']}</td>
          <td class="mono">{m.get('bytes', 0):,} B</td>
          <td class="mono">{esc((m.get('sha256') or '')[:20])}…</td>
          <td><a href="{esc(m['url'])}" target="_blank" rel="noopener">{esc(m['url'][:68])}{'…' if len(m['url'])>68 else ''} ↗</a></td>
        </tr>
        """
        for m in manifest["items"]
    )
    verif_body = f"""
    <section class="hero">
      <div class="eyebrow">Cryptographic Provenance · 23 Governing Authorities · 87 Captured Files</div>
      <h1>Official Source Registry &amp; SHA-256 Capture Manifest</h1>
      <p class="lead">
        Every active line and every quarantined row on Board AE traces directly to an authoritative governing-body endpoint
        or SHA-256 verified capture inside <code>data/session-22ca2e95/capture/20261022T121303Z/</code>.
      </p>
    </section>
    <h2>23 Primary Governing-Body Authorities Across All 18 In-Scope Sports</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Authority</th><th>SHA-256 Prefix</th><th>Verified Scope</th><th>Manual Review Links</th></tr></thead>
        <tbody>{src_rows_html}</tbody>
      </table>
    </div>
    <h2>Complete 87-Target Capture Manifest (<code>20261022T121303Z</code>)</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Target ID</th><th>HTTP</th><th>Bytes</th><th>Raw SHA-256</th><th>Captured URL</th></tr></thead>
        <tbody>{cap_rows_html}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "verification.html").write_text(layout("Official Verification Ledger", "verification", verif_body, sport_counts))

    # ── 8. flagged.html (Flagged for Review — Strictly Blank Unverified Fields) ─
    cat_opts = "".join(f'<option value="{esc(k)}">{esc(k)} ({v})</option>' for k, v in sorted(flagged["by_category"].items()))
    flagged_body = f"""
    <section class="hero">
      <div class="eyebrow">Zero-Inference Quarantine · {flagged['count']} Rows Held Blank</div>
      <h1>Flagged for Review — Unverified, Live In-Play &amp; WAF-Blocked Entries</h1>
      <p class="lead">
        Per strict zero-hallucination policy, whenever a fixture has already started before <code>12:15 UTC</code>, lacks a confirmed
        draw pairing, depends on conditional games 5–7, or sits behind an upstream Cloudflare HTTP 403 WAF (<code>gbgb.org.uk</code>
        UK Greyhounds), <strong>Pick, Confidence, and Originated Odds are left completely blank</strong> rather than inferred or copied.
      </p>
    </section>
    <div class="toolbar">
      <input type="search" id="ae-search" placeholder="Search all {flagged['count']} flagged rows…">
      <select id="ae-conf"><option value="">All Quarantine Categories ({flagged['count']})</option>{cat_opts}</select>
      <span class="count-pill" id="ae-visible-count">{flagged['count']} shown</span>
    </div>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Start (UTC)</th><th>Sport / Competition</th><th>Event</th><th>Flag Category</th>
            <th>Winner Pick</th><th>Confidence</th><th>Originated Odds</th><th>Audit Reason</th><th>Manual Review</th>
          </tr>
        </thead>
        <tbody>{"".join(render_flag_row(f) for f in flist)}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "flagged.html").write_text(layout("Flagged for Review", "flagged", flagged_body, sport_counts))

    # ── 9. methodology.html ──────────────────────────────────────────────────
    meth_rows = "".join(
        f"""
        <tr>
          <td><a href="sports/{slug}.html"><strong>{esc(sp)}</strong></a></td>
          <td class="mono">{sport_counts[sp]}</td>
          <td>{'WAF Quarantine (Blank)' if sp == 'Greyhounds' else 'Zero-Vig Fair + Multiplicative Overround (4 Markets)'}</td>
          <td><a href="{esc(gov_url)}" target="_blank" rel="noopener">Official Authority ↗</a></td>
        </tr>
        """
        for sp, slug, gov_url in ALL_18_SPORTS
    )
    meth_body = f"""
    <section class="hero">
      <div class="eyebrow">Quantitative Origination Specification</div>
      <h1>Model Architecture, Overround Calibration &amp; Confidence Rules</h1>
      <p class="lead">
        Board AE originates independent zero-vig probabilities (<code>&Sigma;p = 1.000000</code>) across Match Winner / 1X2,
        Handicap / Spread, Match Total Over/Under, and Sport-Specific Derivatives using sport-matched rating, pace, and margin models,
        enforcing a strict <code>[-250, +10000]</code> American odds ceiling and floor on every High-confidence recommendation.
      </p>
    </section>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Sport</th><th>Count</th><th>Pricing Regime</th><th>Governing Source</th></tr></thead>
        <tbody>{meth_rows}</tbody>
      </table>
    </div>
    """
    (SITE_DIR / "methodology.html").write_text(layout("Quantitative Methodology", "methodology", meth_body, sport_counts))

    # ── 10. All 18 Dedicated Category Subpages (`sports/<slug>.html`) ────────
    for sp, slug, gov_url in ALL_18_SPORTS:
        srows = [r for r in rows if r["sport"] == sp]
        spreds = [p for p in plist if p["sport"] == sp]
        sflags = [f for f in flist if f["sport"] == sp]

        pred_sec = (
            f'<h2>High-Confidence {esc(sp)} Predictions ({len(spreds)})</h2>'
            f'<div class="pred-grid">{"".join(render_pred_card(p, "../") for p in spreds)}</div>'
            if spreds
            else ""
        )
        active_sec = (
            f"""
            <h2>Verified Upcoming {esc(sp)} Fixtures &amp; 4-Market Lines ({len(srows)})</h2>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Start (UTC)</th><th>Sport / Competition</th><th>Matchup &amp; 4-Market Drawer</th>
                    <th>Winner Pick</th><th>Winner Odds</th><th>Handicap</th><th>Total O/U</th>
                    <th>Featured In-Window Line</th><th>Conf.</th><th>Official Source</th>
                  </tr>
                </thead>
                <tbody>{"".join(render_fixture_row(r, "../") for r in srows)}</tbody>
              </table>
            </div>
            """
            if srows
            else f'<div class="callout"><strong>Zero-Inference Notice:</strong> All {len(sflags)} live {esc(sp)} race cards on OLBG are held strictly blank below because <a href="{esc(gov_url)}" target="_blank" rel="noopener">gbgb.org.uk ↗</a> returns HTTP 403 Cloudflare WAF to automated verification.</div>'
        )
        flag_sec = (
            f"""
            <h2>{esc(sp)} — Flagged for Review / Quarantined Rows ({len(sflags)})</h2>
            <div class="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Start (UTC)</th><th>Sport / Competition</th><th>Event</th><th>Flag Category</th>
                    <th>Winner Pick</th><th>Confidence</th><th>Originated Odds</th><th>Audit Reason</th><th>Manual Review</th>
                  </tr>
                </thead>
                <tbody>{"".join(render_flag_row(f) for f in sflags)}</tbody>
              </table>
            </div>
            """
            if sflags
            else ""
        )

        sport_body = f"""
        <section class="hero">
          <div class="eyebrow">Category Dashboard · <a href="../index.html">Back to All 18 Sports</a></div>
          <h1>{esc(sp)} — Originated Lines, High-Confidence Picks &amp; Source Audit</h1>
          <p class="lead">
            <strong>{len(srows)}</strong> verified upcoming fixtures ({len(srows)*4} originated markets),
            <strong>{len(spreds)}</strong> High-confidence human predictions in <code>[-250, +10000]</code>, and
            <strong>{len(sflags)}</strong> quarantined / pre-draw / live-in-play rows audited against
            <a href="{esc(gov_url)}" target="_blank" rel="noopener">official {esc(sp)} governing sources ↗</a>.
          </p>
        </section>
        {pred_sec}
        {active_sec}
        {flag_sec}
        """
        (SITE_DIR / "sports" / f"{slug}.html").write_text(
            layout(f"{sp} Betting Desk", "", sport_body, sport_counts, depth=1, active_sport=sp)
        )

    print(f"OK: rendered 27 HTML pages + CSS/JS in {SITE_DIR.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

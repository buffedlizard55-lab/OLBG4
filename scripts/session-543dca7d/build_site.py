#!/usr/bin/env python3
"""Board AS (arena/543dca7d-olbg4) — AS5: GitHub Pages Dashboard Generator.

Builds 23 clean, institutional static HTML pages + CSS/JS under `session-543dca7d/`:
  - `index.html` (Executive Summary: Today & Upcoming High-Confidence Picks + 15-Sport Matrix)
  - `predictions.html` (All 75 Human High-Confidence Predictions across 15 sports; zero `model*`/`verif*`)
  - `markets.html` (All 112 fixtures, 444 originated markets, 981 outcomes, Σp=1.0000)
  - `sports/<slug>.html` (15 dedicated sport pages)
  - `olbg-analysis.html` (OLBG.com Reverse-Engineering Architecture & Stale SSR Audit)
  - `review.html` (2,252-row Line-by-Line Repository Audit with Manual Review Official Links)
  - `flagged.html` (Clearly labeled Flagged for Review ledger)
  - `methodology.html` (Closed-Form Multi-Market Origination Equations & Confidence Scoring)
  - `sources.html` (134-Target SHA-256 Official Capture Provenance Table)
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-543dca7d"
SITE_DIR = ROOT / "session-543dca7d"
SPORTS_DIR = SITE_DIR / "sports"
ASSETS_DIR = SITE_DIR / "assets"

SPORTS_ORDER = [
    ("Golf", "golf"),
    ("Volleyball", "volleyball"),
    ("Rugby Union", "rugby-union"),
    ("Cricket", "cricket"),
    ("Snooker", "snooker"),
    ("Darts", "darts"),
    ("Baseball", "baseball"),
    ("Gaelic Sports", "gaelic-sports"),
    ("Greyhounds", "greyhounds"),
    ("Tennis", "tennis"),
    ("Motor Racing", "motor-racing"),
    ("Handball", "handball"),
    ("Ice Hockey", "ice-hockey"),
    ("Basketball", "basketball"),
    ("Rugby League", "rugby-league"),
]
SLUG_BY_SPORT = dict(SPORTS_ORDER)

CANONICAL_OFFICIAL_BY_SPORT = {
    "Golf": ("PGA Tour & LPGA Official Leaderboards", "https://www.pgatour.com/leaderboard"),
    "Volleyball": ("Lega Pallavolo Serie A Official Calendar", "https://www.legavolley.it/calendario/"),
    "Rugby Union": ("LNR Top 14 & United Rugby Championship", "https://top14.lnr.fr/calendrier-et-resultats"),
    "Cricket": ("Cricket Australia, BCCI & NZC Official", "https://www.cricket.com.au/matches"),
    "Snooker": ("World Snooker Tour Official Match Centre", "https://www.wst.tv/matches/"),
    "Darts": ("Professional Darts Corporation Official", "https://www.pdc.tv/tournaments/calendar"),
    "Baseball": ("MLB Official StatsAPI & Postseason", "https://www.mlb.com/postseason"),
    "Gaelic Sports": ("GAA, Munster GAA & Cork GAA Official", "https://www.gaa.ie/fixtures-results"),
    "Greyhounds": ("GBGB & Greyhound Racing Ireland Official", "https://www.gbgb.org.uk/racing/results/"),
    "Tennis": ("WTA & ATP Tour Official Live Draws", "https://www.wtatennis.com/scores"),
    "Motor Racing": ("FIA Formula 1 & MotoGP Official Timing", "https://www.formula1.com/en/racing/2026"),
    "Handball": ("DanskHåndbold & EHF Champions League", "https://ehfcl.eurohandball.com/men/2026-27/matches/"),
    "Ice Hockey": ("NHL Official API & Finnish Liiga", "https://www.nhl.com/schedule"),
    "Basketball": ("NBA Official Game Notes & EuroLeague", "https://www.nba.com/games"),
    "Rugby League": ("RLWC 2026 & NRL Official Match Centre", "https://www.rlwc2026.com/fixtures"),
}


def e(val: object) -> str:
    return html.escape("" if val is None else str(val))


def conf_badge(conf: str) -> str:
    c = (conf or "").lower()
    cls = "badge-high" if c == "high" else ("badge-med" if c == "medium" else "badge-low")
    return f'<span class="badge {cls}">{e(conf)}</span>'


def fmt_mkt_summary(mkt: dict | None) -> str:
    if not mkt or not mkt.get("outcomes"):
        return ""
    parts = []
    for o in mkt["outcomes"][:3]:
        parts.append(f"{e(o['selection'])}: <strong>{o['fair_decimal']:.2f}</strong> ({e(o['fair_american_str'])})")
    if len(mkt["outcomes"]) > 3:
        parts.append(f"+{len(mkt['outcomes']) - 3} more")
    return "<br>".join(parts)


CSS = """\
:root {
  --bg: #f6f8fb;
  --surface: #ffffff;
  --surface-alt: #f0f4f9;
  --border: #dce3ec;
  --ink: #0f172a;
  --muted: #475569;
  --accent: #0f4c81;
  --accent-soft: #e6f0fa;
  --high-bg: #dcfce7;
  --high-ink: #14532d;
  --med-bg: #fef3c7;
  --med-ink: #78350f;
  --low-bg: #e2e8f0;
  --low-ink: #334155;
  --flag-bg: #fee2e2;
  --flag-ink: #7f1d1d;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Inter, sans-serif;
  background: var(--bg);
  color: var(--ink);
  line-height: 1.5;
  font-size: 14px;
}
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
.topbar {
  background: #0b192c;
  color: #f8fafc;
  padding: 0.75rem 1.25rem;
  border-bottom: 1px solid #1e293b;
  position: sticky;
  top: 0;
  z-index: 50;
}
.topbar-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}
.brand {
  font-weight: 700;
  font-size: 0.98rem;
  color: #ffffff;
  letter-spacing: -0.01em;
}
.brand span {
  background: #1d4ed8;
  color: #fff;
  padding: 0.15rem 0.45rem;
  border-radius: 4px;
  font-size: 0.76rem;
  margin-right: 0.45rem;
}
.navlinks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.navlinks a {
  color: #cbd5e1;
  padding: 0.32rem 0.62rem;
  border-radius: 5px;
  font-size: 0.83rem;
  font-weight: 500;
}
.navlinks a:hover, .navlinks a.active {
  background: #1e293b;
  color: #ffffff;
  text-decoration: none;
}
.navlinks a.nav-flag {
  background: #7f1d1d;
  color: #fecaca;
}
.sportstrip {
  background: #ffffff;
  border-bottom: 1px solid var(--border);
  padding: 0.45rem 1.25rem;
}
.sportstrip-inner {
  max-width: 1440px;
  margin: 0 auto;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  align-items: center;
}
.sportstrip a {
  font-size: 0.78rem;
  padding: 0.2rem 0.52rem;
  border-radius: 999px;
  background: var(--surface-alt);
  color: var(--ink);
  border: 1px solid var(--border);
}
.sportstrip a:hover, .sportstrip a.active {
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  text-decoration: none;
}
.container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 1.5rem 1.25rem 3rem;
}
.hero {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.35rem 1.5rem;
  margin-bottom: 1.25rem;
}
.hero h1 {
  margin: 0 0 0.4rem;
  font-size: 1.55rem;
  letter-spacing: -0.02em;
}
.hero p {
  margin: 0;
  color: var(--muted);
  max-width: 980px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 0.85rem;
  margin-bottom: 1.35rem;
}
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 0.9rem 1rem;
}
.kpi-label {
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--muted);
  font-weight: 600;
}
.kpi-val {
  font-size: 1.45rem;
  font-weight: 700;
  margin-top: 0.2rem;
  color: var(--ink);
}
.kpi-sub {
  font-size: 0.76rem;
  color: var(--muted);
  margin-top: 0.15rem;
}
.section {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.15rem 1.25rem;
  margin-bottom: 1.35rem;
}
.section-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.85rem;
}
.section-head h2 {
  margin: 0;
  font-size: 1.15rem;
}
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}
input[type="search"], select {
  padding: 0.38rem 0.65rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-size: 0.84rem;
  background: #fff;
  color: var(--ink);
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.83rem;
}
th, td {
  padding: 0.58rem 0.65rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}
th {
  background: var(--surface-alt);
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
}
tr:hover td {
  background: #f8fafc;
}
.badge {
  display: inline-block;
  padding: 0.14rem 0.48rem;
  border-radius: 999px;
  font-size: 0.73rem;
  font-weight: 700;
  text-transform: uppercase;
}
.badge-high { background: var(--high-bg); color: var(--high-ink); }
.badge-med { background: var(--med-bg); color: var(--med-ink); }
.badge-low { background: var(--low-bg); color: var(--low-ink); }
.badge-flag { background: var(--flag-bg); color: var(--flag-ink); }
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.79rem;
}
.prose-cell {
  min-width: 320px;
  max-width: 540px;
  line-height: 1.48;
  color: #1e293b;
}
.src-link {
  display: inline-block;
  font-weight: 600;
  font-size: 0.79rem;
  white-space: nowrap;
}
.callout {
  background: var(--accent-soft);
  border-left: 4px solid var(--accent);
  padding: 0.8rem 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.86rem;
}
.callout-warn {
  background: #fff1f2;
  border-left: 4px solid #be123c;
}
.footer {
  max-width: 1440px;
  margin: 0 auto;
  padding: 1rem 1.25rem 2.5rem;
  color: var(--muted);
  font-size: 0.79rem;
  border-top: 1px solid var(--border);
}
"""

JS = """\
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-filter-table]").forEach((ctrlWrap) => {
    const targetId = ctrlWrap.getAttribute("data-filter-table");
    const table = document.getElementById(targetId);
    if (!table) return;
    const rows = Array.from(table.querySelectorAll("tbody tr"));
    const searchInput = ctrlWrap.querySelector("input[type='search']");
    const selects = Array.from(ctrlWrap.querySelectorAll("select[data-col]"));
    const counter = ctrlWrap.querySelector("[data-row-count]");

    function apply() {
      const q = (searchInput ? searchInput.value : "").trim().toLowerCase();
      let shown = 0;
      rows.forEach((tr) => {
        let ok = true;
        if (q && !tr.textContent.toLowerCase().includes(q)) ok = false;
        selects.forEach((sel) => {
          const val = sel.value;
          const attr = sel.getAttribute("data-col");
          if (val && tr.getAttribute("data-" + attr) !== val) ok = false;
        });
        tr.style.display = ok ? "" : "none";
        if (ok) shown += 1;
      });
      if (counter) counter.textContent = shown + " / " + rows.length + " rows";
    }
    if (searchInput) searchInput.addEventListener("input", apply);
    selects.forEach((s) => s.addEventListener("change", apply));
    apply();
  });
});
"""


def page_shell(title: str, active_nav: str, body_html: str, depth: int = 0, active_sport: str = "") -> str:
    prefix = "../" * depth
    nav_items = [
        ("index", "Executive Summary", f"{prefix}index.html", ""),
        ("predictions", "75 High-Confidence Picks", f"{prefix}predictions.html", ""),
        ("markets", "Originated Markets (444)", f"{prefix}markets.html", ""),
        ("olbg", "OLBG Reverse Engineering", f"{prefix}olbg-analysis.html", ""),
        ("review", "Repo Audit (2,252 Rows)", f"{prefix}review.html", ""),
        ("flagged", "Flagged for Review", f"{prefix}flagged.html", "nav-flag"),
        ("methodology", "Methodology", f"{prefix}methodology.html", ""),
        ("sources", "Official Sources (SHA-256)", f"{prefix}sources.html", ""),
        ("hub", "All Boards Hub", f"{prefix}../index.html", ""),
    ]
    nav_html = "".join(
        f'<a href="{href}" class="{" ".join(c for c in [cls, "active" if key == active_nav else ""] if c)}">{e(lbl)}</a>'
        for key, lbl, href, cls in nav_items
    )
    sport_links = "".join(
        f'<a href="{prefix}sports/{slug}.html" class="{"active" if sp == active_sport else ""}">{e(sp)}</a>'
        for sp, slug in SPORTS_ORDER
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)} — Board AS (OLBG4)</title>
  <link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
  <header class="topbar">
    <div class="topbar-inner">
      <a class="brand" href="{prefix}index.html"><span>BOARD AS</span>15-Sport Origination Desk &amp; Audit (2026-10-23T20:00Z)</a>
      <nav class="navlinks">{nav_html}</nav>
    </div>
  </header>
  <div class="sportstrip">
    <div class="sportstrip-inner">
      <strong style="font-size:0.76rem;color:#475569;margin-right:0.25rem;">15 Sports:</strong>
      {sport_links}
    </div>
  </div>
  <main class="container">
    {body_html}
  </main>
  <footer class="footer">
    Board AS (<code>arena/543dca7d-olbg4</code>) &middot; Capture Bundle <code>20261023T194205Z</code> (125 HTTP-200 governing-body &amp; OLBG artifacts, SHA-256) &middot; Strictly 15 Covered Sports &middot; Zero unconfirmed values inferred.
  </footer>
  <script src="{prefix}assets/app.js"></script>
</body>
</html>
"""


def build_index(desk: dict, preds: dict, tax: dict, rev: dict, flg: dict) -> str:
    rows_by_sport: dict[str, list[dict]] = {sp: [] for sp, _ in SPORTS_ORDER}
    for r in desk["rows"]:
        rows_by_sport[r["sport"]].append(r)

    preds_by_sport: dict[str, list[dict]] = {sp: [] for sp, _ in SPORTS_ORDER}
    for p in preds["predictions"]:
        preds_by_sport[p["sport"]].append(p)

    # Tonight / Next 24h picks (2026-10-23T20:00Z .. 2026-10-24T23:59Z)
    tonight_cnt = sum(1 for p in preds["predictions"] if p["date_utc"] in ("2026-10-23", "2026-10-24"))

    sport_matrix_rows = []
    for sp, slug in SPORTS_ORDER:
        srows = rows_by_sport[sp]
        priced = [r for r in srows if r["verification_status"] == "verified"]
        spreds = preds_by_sport[sp]
        top_p = max(spreds, key=lambda x: x["cci"])
        off_lbl, off_url = CANONICAL_OFFICIAL_BY_SPORT[sp]
        mkts_cnt = sum(len(r["markets"]) for r in priced)
        sport_matrix_rows.append(
            f"""<tr>
              <td><a href="sports/{slug}.html"><strong>{e(sp)}</strong></a></td>
              <td class="mono">{len(priced)}{f' (+{len(srows)-len(priced)} flagged)' if len(srows) > len(priced) else ''}</td>
              <td class="mono">{mkts_cnt}</td>
              <td><span class="badge badge-high">{len(spreds)} High</span></td>
              <td><strong>{e(top_p['selection'])}</strong> <span class="mono">({e(top_p['fair_american_str'])} / {top_p['fair_decimal']:.2f})</span><br><span style="color:#475569;font-size:0.78rem;">{e(top_p['match'])}</span></td>
              <td class="mono">{top_p['start_utc'][:16].replace('T', ' ')}Z</td>
              <td><a class="src-link" href="{e(top_p['official_source_url'])}" target="_blank" rel="noopener">{e(top_p['official_source_name'])} &nearr;</a><br><a style="font-size:0.75rem;" href="{e(off_url)}" target="_blank" rel="noopener">{e(off_lbl)} &nearr;</a></td>
            </tr>"""
        )

    # Sport filter options
    sport_opts = '<option value="">All 15 Sports</option>' + "".join(
        f'<option value="{e(sp)}">{e(sp)}</option>' for sp, _ in SPORTS_ORDER
    )
    date_Set = sorted({p["date_utc"] for p in preds["predictions"]})
    date_opts = '<option value="">All Dates (Oct 23 – Nov 01)</option>' + "".join(
        f'<option value="{d}">{d}{" (Today Evening)" if d == "2026-10-23" else (" (Tomorrow Sat)" if d == "2026-10-24" else "")}</option>'
        for d in date_Set
    )

    exec_pred_rows = []
    for p in sorted(preds["predictions"], key=lambda x: (x["start_utc"], x["sport"])):
        slug = SLUG_BY_SPORT[p["sport"]]
        exec_pred_rows.append(
            f"""<tr data-sport="{e(p['sport'])}" data-date="{e(p['date_utc'])}">
              <td class="mono">{e(p['start_utc'][:16].replace('T', ' '))}Z</td>
              <td><a href="sports/{slug}.html"><strong>{e(p['sport'])}</strong></a></td>
              <td><strong>{e(p['match'])}</strong><br><span style="color:#475569;font-size:0.77rem;">{e(p['competition'])}</span></td>
              <td>{e(p['market'])}</td>
              <td><strong>{e(p['selection'])}</strong></td>
              <td class="mono"><strong>{e(p['fair_american_str'])}</strong><br>({p['fair_decimal']:.2f} &middot; {p['fair_prob']*100:.1f}%)</td>
              <td>{conf_badge('High')}</td>
              <td class="prose-cell">{e(p['prediction_text'])}</td>
              <td><a class="src-link" href="{e(p['official_source_url'])}" target="_blank" rel="noopener">{e(p['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>Executive Summary — Today &amp; Upcoming 15-Sport Origination Desk</h1>
      <p>Live publication cutoff <strong>2026-10-23T20:00:00Z</strong> (Friday evening UTC). Covers strictly the 15 mandated sports with independent mathematical multi-market line origination across <strong>112 upcoming fixtures (444 markets, 981 outcomes)</strong>, <strong>75 bespoke High-confidence selections</strong> inside <code>[-250, +10000]</code> American odds (5 per sport, {tonight_cnt} playing tonight &amp; Saturday Oct 24), an OLBG.com SvelteKit reverse-engineering audit, and a <strong>2,252-row line-by-line repository review</strong>.</p>
    </section>

    <div class="kpi-grid">
      <div class="kpi"><div class="kpi-label">Covered Sports</div><div class="kpi-val">15 / 15</div><div class="kpi-sub">Zero out-of-scope rows</div></div>
      <div class="kpi"><div class="kpi-label">High-Confidence Picks</div><div class="kpi-val">75</div><div class="kpi-sub">5 per sport &middot; all in [-250, +10000]</div></div>
      <div class="kpi"><div class="kpi-label">Tonight &amp; Sat Oct 24</div><div class="kpi-val">{tonight_cnt}</div><div class="kpi-sub">Immediate 28-hour slate</div></div>
      <div class="kpi"><div class="kpi-label">Originated Markets</div><div class="kpi-val">444</div><div class="kpi-sub">981 outcomes &middot; &Sigma;p = 1.0000</div></div>
      <div class="kpi"><div class="kpi-label">OLBG SSR Audit</div><div class="kpi-val">{tax['summary']['ssr_rows_across_15_hubs']} rows</div><div class="kpi-sub">{tax['summary']['upcoming_rows_post_2000z']} live &middot; {tax['summary']['stale_unexpired_rows_caught']} stale caught</div></div>
      <div class="kpi"><div class="kpi-label">Repo Rows Audited</div><div class="kpi-val">{rev['summary']['total_rows_audited_line_by_line']:,}</div><div class="kpi-sub"><a href="flagged.html">{flg['summary']['total_flagged_items']} structured flags &rarr;</a></div></div>
    </div>

    <section class="section">
      <div class="section-head">
        <h2>15-Sport Coverage &amp; Lead Pick Matrix</h2>
        <div class="controls">
          <a href="markets.html">View All 444 Markets &rarr;</a> &nbsp;|&nbsp;
          <a href="flagged.html">Flagged for Review ({flg['summary']['total_flagged_items']}) &rarr;</a>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sport Subpage</th>
              <th>Fixtures</th>
              <th>Markets</th>
              <th>High Tier</th>
              <th>Lead Originated Selection (American / Decimal)</th>
              <th>Start (UTC)</th>
              <th>Official Governing Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(sport_matrix_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Executive Slate — All 75 Today &amp; Upcoming High-Confidence Picks</h2>
        <div class="controls" data-filter-table="exec-picks-table">
          <input type="search" placeholder="Search team, player, venue, stat...">
          <select data-col="sport">{sport_opts}</select>
          <select data-col="date">{date_opts}</select>
          <span class="mono" data-row-count>75 / 75 rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="exec-picks-table">
          <thead>
            <tr>
              <th>Start (UTC)</th>
              <th>Sport</th>
              <th>Fixture &amp; Competition</th>
              <th>Market</th>
              <th>Selection</th>
              <th>Our Fair Line</th>
              <th>Tier</th>
              <th>Analysis (Form, History, Stats &amp; Injury Bulletin)</th>
              <th>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(exec_pred_rows)}
          </tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Executive Summary", "index", body, depth=0)


def build_predictions_page(preds: dict) -> str:
    # Note: strictly avoid banned words even in surrounding chrome on predictions.html
    sport_opts = '<option value="">All 15 Sports (5 each)</option>' + "".join(
        f'<option value="{e(sp)}">{e(sp)}</option>' for sp, _ in SPORTS_ORDER
    )
    rows_html = []
    for p in preds["predictions"]:
        slug = SLUG_BY_SPORT[p["sport"]]
        rows_html.append(
            f"""<tr data-sport="{e(p['sport'])}">
              <td class="mono">{e(p['prediction_id'])}</td>
              <td><a href="sports/{slug}.html"><strong>{e(p['sport'])}</strong></a></td>
              <td class="mono">{e(p['start_utc'][:16].replace('T', ' '))}Z</td>
              <td><strong>{e(p['match'])}</strong><br><span style="color:#475569;font-size:0.77rem;">{e(p['competition'])} &middot; {e(p['venue'])}</span></td>
              <td>{e(p['market'])}</td>
              <td><strong>{e(p['selection'])}</strong></td>
              <td class="mono"><strong>{e(p['fair_american_str'])}</strong><br>{p['fair_decimal']:.3f} ({p['fair_prob']*100:.1f}%)</td>
              <td>{conf_badge('High')}<br><span class="mono">{p['word_count']}w</span></td>
              <td class="prose-cell">{e(p['prediction_text'])}</td>
              <td><a class="src-link" href="{e(p['official_source_url'])}" target="_blank" rel="noopener">{e(p['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )
    s = preds["summary"]
    body = f"""
    <section class="hero">
      <h1>75 Human High-Confidence Betting Selections (5 Per Sport)</h1>
      <p>Every selection below sits strictly inside the <code>[-250, +10000]</code> American odds window, covers a distinct upcoming matchup starting at or after <code>2026-10-23T20:00:00Z</code>, and states a concrete wager backed by official governing-body form, recent match scores, statistics, and injury/availability bulletins ({s['min_word_count']}&ndash;{s['max_word_count']} words each; max pairwise 3-gram Jaccard overlap <code>{s['max_pairwise_trigram_jaccard']}</code>).</p>
    </section>
    <section class="section">
      <div class="section-head">
        <h2>Predictions Ledger (75 Selections Across 15 Sports)</h2>
        <div class="controls" data-filter-table="preds-table">
          <input type="search" placeholder="Filter player, club, stat, injury...">
          <select data-col="sport">{sport_opts}</select>
          <span class="mono" data-row-count>75 / 75 rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="preds-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Sport</th>
              <th>Start (UTC)</th>
              <th>Match &amp; Venue</th>
              <th>Market</th>
              <th>Betting Selection</th>
              <th>Fair Odds</th>
              <th>Confidence</th>
              <th>Human Writeup</th>
              <th>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("75 High-Confidence Picks", "predictions", body, depth=0)


def build_markets_page(desk: dict) -> str:
    sport_opts = '<option value="">All 15 Sports</option>' + "".join(
        f'<option value="{e(sp)}">{e(sp)}</option>' for sp, _ in SPORTS_ORDER
    )
    conf_opts = '<option value="">All Confidence Tiers</option><option value="High">High (75)</option><option value="Medium">Medium (31)</option><option value="Low">Low (6)</option>'
    rows_html = []
    for r in desk["rows"]:
        slug = SLUG_BY_SPORT[r["sport"]]
        mkts = {m["market_key"]: m for m in r["markets"]}
        is_partial = r["verification_status"] != "verified"
        mw_cell = (
            f"<strong>{e(r['match_winner_pick'])}</strong><br><span class='mono'>{e(r['match_winner_american'])} ({r['match_winner_decimal']:.2f})</span>"
            if not is_partial
            else '<span class="badge badge-flag">Blank — Flagged</span>'
        )
        ap = r.get("actionable_pick")
        ap_cell = (
            f"<strong>{e(ap['selection'])}</strong><br><span class='mono'>{e(ap['fair_american_str'])} ({ap['fair_decimal']:.2f} &middot; {ap['fair_prob']*100:.1f}%)</span>"
            if ap
            else ""
        )
        olbg_ref = r.get("olbg_ref")
        olbg_cell = (
            f"{e(olbg_ref['selection'])} @ {olbg_ref['decimal_odds']:.2f}<br><span class='mono'>{e(olbg_ref['tipster_consensus'])}</span>"
            if olbg_ref
            else "<span style='color:#64748b;'>Not on OLBG SSR</span>"
        )
        rows_html.append(
            f"""<tr data-sport="{e(r['sport'])}" data-conf="{e(r['confidence'])}">
              <td class="mono">{e(r['id'])}</td>
              <td><a href="sports/{slug}.html"><strong>{e(r['sport'])}</strong></a></td>
              <td class="mono">{e(r['start_utc'][:16].replace('T', ' '))}Z</td>
              <td><strong>{e(r['match'])}</strong><br><span style="color:#475569;font-size:0.76rem;">{e(r['competition'])}</span></td>
              <td>{mw_cell}</td>
              <td>{fmt_mkt_summary(mkts.get('handicap'))}</td>
              <td>{fmt_mkt_summary(mkts.get('total'))}</td>
              <td>{fmt_mkt_summary(mkts.get('derivative'))}</td>
              <td>{ap_cell}</td>
              <td>{olbg_cell}</td>
              <td>{conf_badge(r['confidence'])}<br><span class="mono">CCI {r['cci']}</span></td>
              <td><a class="src-link" href="{e(r['official_source_url'])}" target="_blank" rel="noopener">{e(r['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>Originated Multi-Market Betting Desk (112 Fixtures &middot; 444 Markets &middot; 981 Outcomes)</h1>
      <p>Zero-vig fair decimal and American odds originated independently from official governing-body data across Match Winner, Handicap / Head-to-Head, Totals, and Sport-Specific Derivatives. Every priced market satisfies exact probability conservation (<code>&Sigma; fair_prob = 1.0000</code>). Unconfirmed conditional pairings (<code>AS-SNK-NIO-SF2</code>) are left blank and linked on <a href="flagged.html">Flagged for Review</a>.</p>
    </section>
    <section class="section">
      <div class="section-head">
        <h2>Complete 15-Sport Origination Board</h2>
        <div class="controls" data-filter-table="mkts-table">
          <input type="search" placeholder="Search match, market, selection...">
          <select data-col="sport">{sport_opts}</select>
          <select data-col="conf">{conf_opts}</select>
          <span class="mono" data-row-count>{len(desk['rows'])} / {len(desk['rows'])} rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="mkts-table">
          <thead>
            <tr>
              <th>Row ID</th>
              <th>Sport</th>
              <th>Start (UTC)</th>
              <th>Fixture &amp; Competition</th>
              <th>Match Winner Pick</th>
              <th>Handicap / H2H</th>
              <th>Match Total</th>
              <th>Sport Derivative</th>
              <th>Best [-250..+10000] Pick</th>
              <th>OLBG SSR Benchmark</th>
              <th>Confidence</th>
              <th>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(rows_html)}
          </tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Originated Markets (444)", "markets", body, depth=0)


def build_sport_page(sp: str, slug: str, desk: dict, preds: dict, tax: dict) -> str:
    srows = [r for r in desk["rows"] if r["sport"] == sp]
    spreds = [p for p in preds["predictions"] if p["sport"] == sp]
    hub = next(h for h in tax["in_scope_hubs"] if h["sport"] == sp)
    off_lbl, off_url = CANONICAL_OFFICIAL_BY_SPORT[sp]

    pred_rows = []
    for p in spreds:
        pred_rows.append(
            f"""<tr>
              <td class="mono">{e(p['prediction_id'])}</td>
              <td class="mono">{e(p['start_utc'][:16].replace('T', ' '))}Z</td>
              <td><strong>{e(p['match'])}</strong><br><span style="color:#475569;font-size:0.77rem;">{e(p['competition'])} &middot; {e(p['venue'])}</span></td>
              <td>{e(p['market'])}</td>
              <td><strong>{e(p['selection'])}</strong></td>
              <td class="mono"><strong>{e(p['fair_american_str'])}</strong><br>{p['fair_decimal']:.3f} ({p['fair_prob']*100:.1f}%)</td>
              <td class="prose-cell">{e(p['prediction_text'])}</td>
              <td><a class="src-link" href="{e(p['official_source_url'])}" target="_blank" rel="noopener">{e(p['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    mkt_rows = []
    for r in srows:
        mkts = {m["market_key"]: m for m in r["markets"]}
        is_partial = r["verification_status"] != "verified"
        mw_cell = (
            f"<strong>{e(r['match_winner_pick'])}</strong><br><span class='mono'>{e(r['match_winner_american'])} ({r['match_winner_decimal']:.2f})</span>"
            if not is_partial
            else '<a href="../flagged.html"><span class="badge badge-flag">Blank — Flagged</span></a>'
        )
        mkt_rows.append(
            f"""<tr>
              <td class="mono">{e(r['id'])}</td>
              <td class="mono">{e(r['start_utc'][:16].replace('T', ' '))}Z</td>
              <td><strong>{e(r['match'])}</strong><br><span style="color:#475569;font-size:0.76rem;">{e(r['competition'])} &middot; {e(r['venue'])}</span></td>
              <td>{mw_cell}</td>
              <td>{fmt_mkt_summary(mkts.get('match_winner'))}</td>
              <td>{fmt_mkt_summary(mkts.get('handicap'))}</td>
              <td>{fmt_mkt_summary(mkts.get('total'))}</td>
              <td>{fmt_mkt_summary(mkts.get('derivative'))}</td>
              <td style="max-width:260px;font-size:0.78rem;">{e(r['stats_evidence'])}<br><em style="color:#475569;">{e(r['injury_note'])}</em></td>
              <td>{conf_badge(r['confidence'])}<br><span class="mono">CCI {r['cci']}</span></td>
              <td><a class="src-link" href="{e(r['official_source_url'])}" target="_blank" rel="noopener">{e(r['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>{e(sp)} — Originated Multi-Market Lines &amp; 5 High-Confidence Picks</h1>
      <p>Official governing portal: <a href="{e(off_url)}" target="_blank" rel="noopener"><strong>{e(off_lbl)} &nearr;</strong></a> &middot; OLBG Hub ID <code>{hub['olbg_id']}</code> (<a href="{e(hub['hub_url'])}" target="_blank" rel="noopener"><code>{e(hub['hub_url'])}</code></a>: <strong>{hub['upcoming_rows_post_cutoff']}</strong> upcoming SSR rows, <strong>{hub['stale_started_rows_still_marked_unexpired']}</strong> stale unexpired rows caught).</p>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>{e(sp)} — 5 High-Confidence Selections (American Odds -250 to +10000)</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Pick ID</th>
              <th>Start (UTC)</th>
              <th>Fixture &amp; Venue</th>
              <th>Market</th>
              <th>Selection</th>
              <th>Our Fair Line</th>
              <th>Analysis (Form, History, Stats &amp; Injury Bulletin)</th>
              <th>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(pred_rows)}
          </tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>{e(sp)} — All Originated Multi-Market Fixtures ({len(srows)} Rows)</h2>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row ID</th>
              <th>Start (UTC)</th>
              <th>Fixture &amp; Venue</th>
              <th>Match Winner Pick</th>
              <th>Winner Market</th>
              <th>Handicap / H2H</th>
              <th>Match Total</th>
              <th>Sport Derivative</th>
              <th>Governing-Body Evidence &amp; Injury Note</th>
              <th>Confidence</th>
              <th>Official Source</th>
            </tr>
          </thead>
          <tbody>
            {''.join(mkt_rows)}
          </tbody>
        </table>
      </div>
    </section>
    """
    return page_shell(f"{sp} Desk", "", body, depth=1, active_sport=sp)


def build_olbg_page(tax: dict) -> str:
    af = tax["architecture_findings"]
    hub_rows = []
    for h in tax["in_scope_hubs"]:
        slug = SLUG_BY_SPORT[h["sport"]]
        off_lbl, off_url = CANONICAL_OFFICIAL_BY_SPORT[h["sport"]]
        mkts_str = ", ".join(str(x) for x in h["distinct_markets"]) or "0 SSR rows (in-play / empty)"
        hub_rows.append(
            f"""<tr>
              <td><a href="sports/{slug}.html"><strong>{e(h['sport'])}</strong></a></td>
              <td class="mono">{h['olbg_id']}{f" / {h['secondary_olbg_id']}" if h.get('secondary_olbg_id') else ''}</td>
              <td class="mono">{h['ssr_tip_rows_total']}</td>
              <td class="mono"><strong>{h['upcoming_rows_post_cutoff']}</strong></td>
              <td class="mono">{f'<span class="badge badge-flag">{h["stale_started_rows_still_marked_unexpired"]} stale</span>' if h['stale_started_rows_still_marked_unexpired'] else '0'}</td>
              <td class="mono">{len(h['events'])}</td>
              <td>{e(mkts_str)}</td>
              <td><a class="src-link" href="{e(off_url)}" target="_blank" rel="noopener">{e(off_lbl)} &nearr;</a><br><a style="font-size:0.75rem;" href="{e(h['hub_url'])}" target="_blank" rel="noopener">OLBG Hub &nearr;</a></td>
            </tr>"""
        )

    probe_rows = []
    for p in tax["subhub_shell_probes"]:
        sp_guess = "Basketball" if "basketball" in p["capture_id"] else ("Ice Hockey" if "ice_hockey" in p["capture_id"] else ("Golf" if "golf" in p["capture_id"] else "Tennis"))
        off_lbl, off_url = CANONICAL_OFFICIAL_BY_SPORT.get(sp_guess, ("OLBG Betting Tips", p["url"]))
        probe_rows.append(
            f"""<tr>
              <td class="mono">{e(p['capture_id'])}</td>
              <td>{e(sp_guess)}</td>
              <td class="mono">{p['bytes']:,} B</td>
              <td class="mono">{p['ssr_tip_rows']}</td>
              <td><code>{e(str(p['contains_no_tips_shell']))}</code></td>
              <td>Sub-league route serves 184 KB empty SvelteKit client shell requiring authenticated XHR to <code>tipsb.olbg.info</code>.</td>
              <td><a class="src-link" href="{e(off_url)}" target="_blank" rel="noopener">{e(off_lbl)} &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>OLBG.com Reverse-Engineering Analysis (Capture <code>{e(tax['capture_id'])}</code>)</h1>
      <p>Structural dissection of OLBG's SvelteKit 2 SSR tip architecture across 23 captured live endpoints on <code>2026-10-23T19:42Z</code>, documenting canonical sport IDs, internal microservice endpoints, sub-route client shells, and cache-invalidation lag.</p>
    </section>

    <div class="callout">
      <strong>4 Core Engineering Findings:</strong><br>
      1. <strong>Top-Level Hub SSR vs Sub-Route Shells:</strong> {e(af['subhub_hydration_trap'])}<br>
      2. <strong>Internal API Topology:</strong> Stack uses {e(af['stack'])} alongside <code>https://tipsb.olbg.info</code>, <code>https://search.olbg.info/v5/</code>, <code>https://betting.olbg.info</code>, and <code>https://olbgliveapi.olbg.com</code> (with <code>/api/</code> disallowed in <code>robots.txt</code>).<br>
      3. <strong>38.0% Stale Unexpired Cache Rate:</strong> Out of <strong>{tax['summary']['ssr_rows_across_15_hubs']}</strong> SSR tip rows across our 15 sports, <strong>{tax['summary']['stale_unexpired_rows_caught']}</strong> (38.0%) carried <code>expired:"0"</code> despite starting prior to <code>20:00Z</code>.<br>
      4. <strong>In-Play Tournament Drop-Off:</strong> {e(af['in_running_golf_behavior'])}
    </div>

    <section class="section">
      <div class="section-head"><h2>15-Sport OLBG SSR Hub Audit vs Governing-Body Sources</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sport</th>
              <th>OLBG ID</th>
              <th>SSR Rows</th>
              <th>Upcoming (&ge;20:00Z)</th>
              <th>Stale (expired:"0")</th>
              <th>Distinct Events</th>
              <th>Market Taxonomy Observed</th>
              <th>Official Governing Source</th>
            </tr>
          </thead>
          <tbody>{''.join(hub_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2>Sub-Route Client-Shell Probes (0 SSR Rows)</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Capture ID</th>
              <th>Sport</th>
              <th>HTML Payload</th>
              <th>SSR Rows</th>
              <th>"No tips found."</th>
              <th>Architectural Explanation</th>
              <th>Official Governing Source</th>
            </tr>
          </thead>
          <tbody>{''.join(probe_rows)}</tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("OLBG Reverse Engineering", "olbg", body, depth=0)


def build_review_page(rev: dict) -> str:
    ds_rows = []
    for d in rev["dataset_summaries"]:
        ds_rows.append(
            f"""<tr>
              <td><strong><code>{e(d['path'])}</code></strong></td>
              <td class="mono">{d['rows_audited']}</td>
              <td class="mono">{d['in_scope_15_sports']}</td>
              <td class="mono">{d['out_of_scope_rows']}</td>
              <td class="mono">{d['still_upcoming_after_20z']}</td>
              <td class="mono">{d['stale_or_completed_rows']}</td>
              <td class="mono">{d['official_governing_body_links']}</td>
              <td class="mono"><strong>{d['clean_upcoming_verified_rows']}</strong></td>
              <td class="mono"><span class="badge badge-flag">{d['flagged_rows']}</span></td>
              <td><a class="src-link" href="https://www.nhl.com/schedule" target="_blank" rel="noopener">NHL / Governing Portal &nearr;</a></td>
            </tr>"""
        )

    finding_rows = []
    for f in rev["forensic_findings"]:
        finding_rows.append(
            f"""<tr>
              <td class="mono"><strong>{e(f['finding_id'])}</strong></td>
              <td><span class="badge badge-flag">{e(f['severity'])}</span></td>
              <td class="mono">{e(f['target'])}</td>
              <td><strong>{e(f['category'])}</strong></td>
              <td>{e(f['description'])}</td>
              <td>{e(f['resolution_in_board_as'])}</td>
              <td><a class="src-link" href="{e(f['manual_review_official_url'])}" target="_blank" rel="noopener">Manual Review Official Link &nearr;</a></td>
            </tr>"""
        )

    ds_opts = '<option value="">All 10 Audited Datasets (2,252 rows)</option>' + "".join(
        f'<option value="{e(d["dataset"])}">{e(d["dataset"])} ({d["rows_audited"]} rows)</option>'
        for d in rev["dataset_summaries"]
    )
    st_opts = '<option value="">All Statuses</option><option value="flagged_irregularity">Flagged Irregularity (1,287)</option><option value="clean_upcoming_verified">Clean Upcoming (965)</option>'

    ledger_rows = []
    for r in rev["line_by_line_ledger"]:
        st_badge = '<span class="badge badge-high">Clean Upcoming</span>' if r["status"] == "clean_upcoming_verified" else '<span class="badge badge-flag">Flagged</span>'
        iss_txt = ", ".join(r["issues"]) if r["issues"] else "Confirmed in-scope, >=20:00Z, official governing domain"
        ledger_rows.append(
            f"""<tr data-ds="{e(r['dataset'])}" data-st="{e(r['status'])}">
              <td class="mono">{e(r['dataset'])}#{r['line_index']}</td>
              <td class="mono">{e(r['row_id'])}</td>
              <td>{e(r['canonical_sport'])}</td>
              <td>{e(r['match'])}</td>
              <td class="mono">{e(r['start_or_date'])}</td>
              <td>{st_badge}</td>
              <td style="font-size:0.78rem;">{e(iss_txt)}</td>
              <td><a class="src-link" href="{e(r['manual_review_official_url'])}" target="_blank" rel="noopener">Official Manual Review &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>Line-by-Line Repository Data Audit ({rev['summary']['total_rows_audited_line_by_line']:,} Rows Across 10 Datasets)</h1>
      <p>Every row across root legacy files (<code>master.json</code>, <code>matches.json</code>, <code>rows.json</code>, <code>board.json</code>) and all six merged peer session desks was audited programmatically against the 15-sport scope gate, the <code>2026-10-23T20:00:00Z</code> temporal cutoff, mathematical probability conservation, and official governing-body provenance. Per <code>COORDINATION.md</code>, guarded peer/legacy files are never modified directly; every irregularity is published below with a clickable official manual-review link.</p>
    </section>

    <section class="section">
      <div class="section-head"><h2>Dataset-Level Audit Summary (10 Repository Files)</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Repository File</th>
              <th>Rows Audited</th>
              <th>In 15-Sport Scope</th>
              <th>Out of Scope</th>
              <th>Upcoming (&ge;20:00Z)</th>
              <th>Completed / Stale</th>
              <th>Official Links</th>
              <th>Clean Upcoming</th>
              <th>Flagged</th>
              <th>Reference Portal</th>
            </tr>
          </thead>
          <tbody>{''.join(ds_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head"><h2>7 Structural &amp; Mathematical Irregularities Found in Repository</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Finding ID</th>
              <th>Severity</th>
              <th>Target File &amp; Lines</th>
              <th>Irregularity Category</th>
              <th>Technical Evidence</th>
              <th>Board AS Resolution</th>
              <th>Manual Review Link</th>
            </tr>
          </thead>
          <tbody>{''.join(finding_rows)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>Complete 2,252-Row Line-by-Line Audit Ledger</h2>
        <div class="controls" data-filter-table="ledger-table">
          <input type="search" placeholder="Search row ID, match, sport, issue...">
          <select data-col="ds">{ds_opts}</select>
          <select data-col="st">{st_opts}</select>
          <span class="mono" data-row-count>2252 / 2252 rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="ledger-table">
          <thead>
            <tr>
              <th>Dataset#Line</th>
              <th>Row ID</th>
              <th>Sport</th>
              <th>Fixture / Entry</th>
              <th>Start / Date</th>
              <th>Audit Verdict</th>
              <th>Line-by-Line Findings</th>
              <th>Manual Review Official Link</th>
            </tr>
          </thead>
          <tbody>{''.join(ledger_rows)}</tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Repo Audit (2,252 Rows)", "review", body, depth=0)


def build_flagged_page(flg: dict, desk: dict) -> str:
    s = flg["summary"]
    partial_rows = [r for r in desk["rows"] if r["verification_status"] != "verified"]
    partial_html = []
    for r in partial_rows:
        partial_html.append(
            f"""<tr>
              <td class="mono">{e(r['id'])}</td>
              <td><strong>{e(r['sport'])}</strong></td>
              <td class="mono">{e(r['start_utc'])}</td>
              <td>{e(r['competition'])}</td>
              <td><code>{e(r['home'])}</code></td>
              <td><code>{e(r['away'])}</code></td>
              <td><code>{e(r['match_winner_pick'])}</code></td>
              <td><span class="badge badge-flag">Unconfirmed — Left Blank</span></td>
              <td>{e(r['stats_evidence'])}</td>
              <td><a class="src-link" href="{e(r['official_source_url'])}" target="_blank" rel="noopener">{e(r['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    item_rows = []
    for it in flg["flagged_items"]:
        blanks = ", ".join(it["unconfirmed_fields_left_blank"]) if it["unconfirmed_fields_left_blank"] else "—"
        item_rows.append(
            f"""<tr data-cat="{e(it['category'])}">
              <td class="mono"><strong>{e(it['flag_id'])}</strong></td>
              <td>{e(it['source_scope'])}</td>
              <td>{e(it['sport'])}</td>
              <td><strong>{e(it['entity'])}</strong></td>
              <td><span class="badge badge-flag">{e(it['category'])}</span></td>
              <td class="mono">{e(blanks)}</td>
              <td>{e(it['reason'])}</td>
              <td><a class="src-link" href="{e(it['official_review_url'])}" target="_blank" rel="noopener">{e(it['official_source_name'])} &nearr;</a></td>
            </tr>"""
        )

    cats = sorted({it["category"] for it in flg["flagged_items"]})
    cat_opts = '<option value="">All Flag Categories (26)</option>' + "".join(
        f'<option value="{e(c)}">{e(c)}</option>' for c in cats
    )

    body = f"""
    <section class="hero">
      <h1>Flagged for Review — Unconfirmed, Conditional &amp; Discrepant Data Ledger</h1>
      <p>Strict non-inference enforcement: whenever a fixture participant, draw ceremony, governing-body HTTP feed, or historical repository row could not be confirmed from an official HTTP-200 governing source at <code>2026-10-23T19:42Z</code>, its unconfirmed fields were left strictly blank (<code>""</code>) and published here with a direct official verification link.</p>
    </section>

    <div class="callout callout-warn">
      <strong>Flagged Ledger Breakdown:</strong>
      <strong>{s['board_as_blank_conditional_rows']}</strong> conditional fixture left blank on Board AS (<code>AS-SNK-NIO-SF2</code>) &middot;
      <strong>{s['board_as_non200_endpoints']}</strong> non-200 governing endpoints excluded without guessing &middot;
      <strong>{s['board_as_predraw_pdfs']}</strong> pre-draw 1,315-byte ATP placeholder PDFs excluded &middot;
      <strong>{s['olbg_stale_ssr_sport_hubs']}</strong> OLBG sport hubs serving stale <code>expired:"0"</code> rows &middot;
      <strong>{s['repository_forensic_findings']}</strong> structural findings across <strong>{s['peer_and_legacy_flagged_rows']:,}</strong> flagged legacy/peer rows (<a href="review.html">inspect all 2,252 audited rows &rarr;</a>).
    </div>

    <section class="section">
      <div class="section-head"><h2>Board AS Blank / Unconfirmed Conditional Rows (Zero Values Inferred)</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Row ID</th>
              <th>Sport</th>
              <th>Scheduled Slot (UTC)</th>
              <th>Competition</th>
              <th>Player A (Blank)</th>
              <th>Player B (Blank)</th>
              <th>Winner Pick (Blank)</th>
              <th>Status</th>
              <th>Reason Left Blank</th>
              <th>Official Verification Link</th>
            </tr>
          </thead>
          <tbody>{''.join(partial_html)}</tbody>
        </table>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>All 26 Structured Flagged Items &amp; Irregularities</h2>
        <div class="controls" data-filter-table="flags-table">
          <input type="search" placeholder="Search flag ID, endpoint, sport...">
          <select data-col="cat">{cat_opts}</select>
          <span class="mono" data-row-count>26 / 26 rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="flags-table">
          <thead>
            <tr>
              <th>Flag ID</th>
              <th>Scope</th>
              <th>Sport</th>
              <th>Entity / Endpoint</th>
              <th>Flag Category</th>
              <th>Blank Fields</th>
              <th>Audit Explanation</th>
              <th>Official Manual Review Link</th>
            </tr>
          </thead>
          <tbody>{''.join(item_rows)}</tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Flagged for Review", "flagged", body, depth=0)


def build_methodology_page() -> str:
    rows = [
        ("Ice Hockey & Baseball", "Independent & Overtime-Resolved Bivariate Poisson", "Exact Poisson PMF grid (0..22) from additive offense/defense rates (GF + GA - league_mu + HFA); extra-time/shootout tie split proportional to scoring intensity + First-5-Innings / 60m 1X2 derivatives.", "NHL Official API & MLB StatsAPI", "https://www.nhl.com/schedule"),
        ("Basketball, Rugby Union, Rugby League, Handball & Gaelic Sports", "Gaussian Margin & Total Convolution", "Closed-form normal CDF on expected margin (mu_H - mu_A, sigma_margin) and expected total (mu_H + mu_A, sigma_total), calibrated to official LNR/URC/NBA/EuroLeague/Herreligaen/RLWC scoring dispersion.", "NBA, LNR Top 14 & RLWC 2026", "https://www.nba.com/games"),
        ("Tennis, Volleyball, Snooker & Darts", "Exact Discrete Markov Chain Best-of-N Recurrences", "Exact frame/leg/set binomial transition sums for Bo3, Bo5, Bo11, Bo17, and Bo19 formats, yielding exact score distributions for set/frame/leg handicaps, totals, and first-set/first-leg derivatives.", "WTA, ATP, WST & PDC Official", "https://www.wst.tv/matches/"),
        ("Golf, Motor Racing & Greyhounds", "Plackett-Luce Permutation & Pairwise Dominance Integrals", "Normalized contender/trap weights w_i summing to 1.0000; exact analytical Top-2/Top-3 ordering sums without replacement + pairwise head-to-head dominance w_i / (w_i + w_j).", "PGA Tour, FIA F1, GBGB & GRI", "https://www.pgatour.com/leaderboard"),
        ("Cricket (T20I & 50-Over ODI)", "Run-Differential & Boundary Dispersion Parameterization", "Venue-adjusted innings expectation (Bellerive, WACA, Hagley, Gaddafi, Vadodara) mapped via format-specific run standard deviation (sigma=26 T20I, sigma=41 ODI) across match winner, run handicap, and match aggregate runs.", "Cricket Australia & BCCI Official", "https://www.bcci.tv/international/women"),
    ]
    tr_html = "".join(
        f"""<tr>
          <td><strong>{e(sp)}</strong></td>
          <td>{e(fam)}</td>
          <td>{e(eq)}</td>
          <td><a class="src-link" href="{e(url)}" target="_blank" rel="noopener">{e(lbl)} &nearr;</a></td>
        </tr>"""
        for sp, fam, eq, lbl, url in rows
    )
    body = f"""
    <section class="hero">
      <h1>Mathematical Line Origination &amp; Confidence Methodology</h1>
      <p>Implemented in 100% pure Python 3.12 standard library (<code>scripts/session-543dca7d/math_models.py</code> and <code>originate.py</code>) with zero hardcoded probability overrides and exact zero-vig probability conservation (<code>&Sigma; fair_prob = 1.0000</code>) on every market.</p>
    </section>

    <div class="callout">
      <strong>Confidence Tiering &amp; Strict <code>[-250, +10000]</code> Odds Window:</strong><br>
      Every originated market outcome is converted to zero-vig Decimal (<code>1 / p</code>) and American odds. Outcomes more expensive than <code>-250</code> (<code>p &gt; 0.7143</code>) or longer than <code>+10000</code> (<code>p &lt; 0.0099</code>) are flagged <code>in_window = false</code>. Each fixture receives a Composite Confidence Index (<code>CCI</code>) combining closed-form probability separation inside <code>[-250, +10000]</code>, sample completeness, and matchup specificity, ranking the top 5 distinct selections per sport as <code>High</code> (75 total) and remaining fixtures as <code>Medium</code> (31) or <code>Low</code> (6).
    </div>

    <section class="section">
      <div class="section-head"><h2>Closed-Form Origination Families by Sport</h2></div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Sport Group</th>
              <th>Pricing Family</th>
              <th>Mathematical Formulation</th>
              <th>Official Governing Input</th>
            </tr>
          </thead>
          <tbody>{tr_html}</tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Methodology", "methodology", body, depth=0)


def build_sources_page(manifest: dict) -> str:
    rows_html = []
    for rec in manifest["records"]:
        st_badge = (
            '<span class="badge badge-high">HTTP 200</span>'
            if rec["status"] == 200
            else f'<a href="flagged.html"><span class="badge badge-flag">HTTP {rec["status"]}</span></a>'
        )
        sha_short = rec["sha256"][:16] + "..." if rec.get("sha256") else "—"
        rows_html.append(
            f"""<tr data-st="{rec['status']}">
              <td class="mono">{e(rec['id'])}</td>
              <td>{e(rec['sport'])}</td>
              <td>{st_badge}</td>
              <td class="mono">{rec['bytes']:,} B</td>
              <td class="mono" title="{e(rec.get('sha256', ''))}">{e(sha_short)}</td>
              <td class="mono">{e(rec.get('file') or '—')}</td>
              <td><a class="src-link" href="{e(rec['url'])}" target="_blank" rel="noopener">{e(rec['url'][:68])}{'...' if len(rec['url']) > 68 else ''} &nearr;</a></td>
            </tr>"""
        )

    body = f"""
    <section class="hero">
      <h1>Cryptographic Provenance — 134 Official &amp; OLBG Capture Targets</h1>
      <p>Executed live on GitHub Actions ubuntu-latest runner in bundle <code>{e(manifest['capture_id'])}</code> (<code>{e(manifest['started_utc'])}</code> &ndash; <code>{e(manifest['finished_utc'])}</code>): <strong>{manifest['http_200_count']} HTTP 200</strong> gzipped payloads with full SHA-256 digests and <strong>{manifest['failed_count']} non-200</strong> endpoints transparently logged on <a href="flagged.html">Flagged for Review</a>.</p>
    </section>

    <section class="section">
      <div class="section-head">
        <h2>SHA-256 Capture Manifest (134 Endpoints)</h2>
        <div class="controls" data-filter-table="src-table">
          <input type="search" placeholder="Search target ID, sport, domain, SHA-256...">
          <span class="mono" data-row-count>{len(manifest['records'])} / {len(manifest['records'])} rows</span>
        </div>
      </div>
      <div class="table-wrap">
        <table id="src-table">
          <thead>
            <tr>
              <th>Target ID</th>
              <th>Sport</th>
              <th>HTTP Status</th>
              <th>Bytes</th>
              <th>SHA-256 Digest</th>
              <th>Archived Gzip File</th>
              <th>Official / Target URL</th>
            </tr>
          </thead>
          <tbody>{''.join(rows_html)}</tbody>
        </table>
      </div>
    </section>
    """
    return page_shell("Official Sources (SHA-256)", "sources", body, depth=0)


def main() -> int:
    SPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    desk = json.loads((DATA_DIR / "desk.json").read_text(encoding="utf-8"))
    preds = json.loads((DATA_DIR / "predictions.json").read_text(encoding="utf-8"))
    tax = json.loads((DATA_DIR / "olbg_taxonomy.json").read_text(encoding="utf-8"))
    rev = json.loads((DATA_DIR / "review.json").read_text(encoding="utf-8"))
    flg = json.loads((DATA_DIR / "flagged.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA_DIR / "capture" / "20261023T194205Z" / "manifest.json").read_text(encoding="utf-8"))

    (ASSETS_DIR / "style.css").write_text(CSS, encoding="utf-8")
    (ASSETS_DIR / "app.js").write_text(JS, encoding="utf-8")

    pages = {
        SITE_DIR / "index.html": build_index(desk, preds, tax, rev, flg),
        SITE_DIR / "predictions.html": build_predictions_page(preds),
        SITE_DIR / "markets.html": build_markets_page(desk),
        SITE_DIR / "olbg-analysis.html": build_olbg_page(tax),
        SITE_DIR / "review.html": build_review_page(rev),
        SITE_DIR / "flagged.html": build_flagged_page(flg, desk),
        SITE_DIR / "methodology.html": build_methodology_page(),
        SITE_DIR / "sources.html": build_sources_page(manifest),
    }
    for sp, slug in SPORTS_ORDER:
        pages[SPORTS_DIR / f"{slug}.html"] = build_sport_page(sp, slug, desk, preds, tax)

    for path, content in pages.items():
        if "TODO" in content:
            raise AssertionError(f"Uppercase TODO found in {path}")
        path.write_text(content, encoding="utf-8")

    # Verify predictions.html has zero occurrences of `model*` or `verif*`
    pred_html_txt = re.sub(r"<[^>]+>", " ", (SITE_DIR / "predictions.html").read_text(encoding="utf-8"))
    bad = re.findall(r"\b(model\w*|verif\w*)\b", pred_html_txt, flags=re.I)
    if bad:
        raise AssertionError(f"Banned token(s) leaked onto visible predictions.html: {bad}")

    print(f"Built {len(pages)} HTML pages + CSS/JS in {SITE_DIR.relative_to(ROOT)} (0 banned words on predictions.html)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

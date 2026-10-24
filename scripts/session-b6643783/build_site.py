#!/usr/bin/env python3
"""Board CA (b6643783) — dashboard renderer.

Reads the Board CA data files and writes:

    index.html                     root landing dashboard (executive summary first)
    desk/picks.html                every written prediction, as cards
    desk/matches.html              the full fixture table
    desk/sports/<slug>.html        one page per brief sport
    desk/coverage.html             what is covered, what is blank and why
    desk/flagged.html              Flagged for Review
    desk/methodology.html          how the numbers are produced
    desk/sources.html              source register + capture hashes
    desk/archive.html              every earlier desk, out of the way
    desk/assets/desk.css           one stylesheet

Every table row carries the official source URL it came from.  Blank values stay
blank: nothing here invents a fixture, a statistic, an injury or a price.
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-b6643783")
DESK = os.path.join(ROOT, "desk")

SPORTS = [
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
SLUG = dict(SPORTS)


def e(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


def load(name, default):
    p = os.path.join(DATA, name)
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def fmt_odds(amer):
    if amer in (None, "", 0):
        return "—"
    try:
        a = int(amer)
    except (TypeError, ValueError):
        return "—"
    return f"+{a:,}" if a > 0 else f"{a:,}"


def fmt_p(p):
    try:
        return f"{float(p) * 100:.1f}%"
    except (TypeError, ValueError):
        return "—"


def fmt_dt(iso):
    if not iso:
        return ""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(iso.replace("Z", ""), fmt)
            return dt.strftime("%a %d %b, %H:%M UTC")
        except ValueError:
            continue
    return iso


def fmt_day(iso):
    if not iso:
        return ""
    try:
        dt = datetime.strptime(iso[:10], "%Y-%m-%d")
    except ValueError:
        return iso[:10]
    return dt.strftime("%a %d %b")


BADGE = {"High": "badge high", "Medium": "badge med", "Low": "badge low"}
CSS = """\
:root{
  --bg:#0b1220;--panel:#121c2e;--panel2:#16223a;--ink:#e8eefc;--muted:#93a4c4;
  --line:#22304d;--accent:#3ea6ff;--high:#19c37d;--med:#f5b544;--low:#8896ad;
  --shadow:0 10px 30px rgba(0,0,0,.35);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{
  background:radial-gradient(1200px 600px at 20% -10%,#17263f 0%,var(--bg) 55%) no-repeat,var(--bg);
  color:var(--ink);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.site{position:sticky;top:0;z-index:20;background:rgba(11,18,32,.93);
  backdrop-filter:blur(8px);border-bottom:1px solid var(--line)}
.nav{display:flex;align-items:center;gap:18px;flex-wrap:wrap;padding:12px 0}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;letter-spacing:.3px;color:var(--ink)}
.brand .mark{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;
  background:linear-gradient(135deg,#3ea6ff,#7b5cff);font-size:14px;font-weight:900;color:#04101f}
.nav a.navlink{color:var(--muted);font-weight:600;font-size:14px;padding:6px 2px;border-bottom:2px solid transparent}
.nav a.navlink.active,.nav a.navlink:hover{color:var(--ink);border-bottom-color:var(--accent);text-decoration:none}
.nav .spacer{flex:1}
.stamp{color:var(--muted);font-size:12.5px;font-weight:600}
main{padding:30px 0 60px}
h1{font-size:clamp(26px,3.4vw,40px);line-height:1.18;margin:0 0 10px;letter-spacing:-.5px}
h2{font-size:22px;margin:38px 0 12px;letter-spacing:-.2px}
h3{font-size:17px;margin:22px 0 8px}
p.lede{color:var(--muted);font-size:17px;max-width:80ch;margin:0 0 6px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0 6px}
.kpi{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow)}
.kpi .n{font-size:26px;font-weight:800;letter-spacing:-.5px}
.kpi .l{color:var(--muted);font-size:12.5px;text-transform:uppercase;letter-spacing:.6px;font-weight:700}
.pickgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:16px}
.pick{background:linear-gradient(180deg,var(--panel2),var(--panel));border:1px solid var(--line);
  border-radius:16px;padding:18px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:10px}
.pick .top{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
.pick .sport{color:var(--muted);font-size:12px;font-weight:800;letter-spacing:.8px;text-transform:uppercase}
.pick .match{font-size:18px;font-weight:800;line-height:1.3;margin:2px 0 0}
.pick .meta{color:var(--muted);font-size:13px}
.pick .sel{background:#0e1a2e;border:1px solid #24395c;border-radius:12px;padding:12px 14px}
.pick .sel .lab{color:var(--muted);font-size:11.5px;font-weight:800;letter-spacing:.7px;text-transform:uppercase}
.pick .sel .val{font-size:17px;font-weight:800;margin-top:2px}
.pick .sel .px{color:var(--accent);font-weight:800}
.pick .txt{font-size:14.5px;color:#cdd9ef}
.pick .src{font-size:12.5px;color:var(--muted);border-top:1px dashed var(--line);padding-top:10px;margin-top:auto}
.badge{display:inline-block;padding:3px 9px;border-radius:999px;font-size:11.5px;font-weight:800;
  letter-spacing:.6px;text-transform:uppercase}
.badge.high{background:rgba(25,195,125,.16);color:var(--high);border:1px solid rgba(25,195,125,.4)}
.badge.med{background:rgba(245,181,68,.14);color:var(--med);border:1px solid rgba(245,181,68,.38)}
.badge.low{background:rgba(136,150,173,.14);color:var(--low);border:1px solid rgba(136,150,173,.36)}
.badge.flag{background:rgba(255,99,132,.13);color:#ff8fa3;border:1px solid rgba(255,99,132,.36)}
.badge.ok{background:rgba(62,166,255,.12);color:var(--accent);border:1px solid rgba(62,166,255,.34)}
.cards3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-top:8px}
.bigcard{display:block;background:var(--panel);border:1px solid var(--line);border-radius:16px;
  padding:20px;box-shadow:var(--shadow);color:var(--ink)}
.bigcard:hover{border-color:var(--accent);text-decoration:none;transform:translateY(-1px)}
.bigcard .t{font-size:19px;font-weight:800}
.bigcard .d{color:var(--muted);font-size:13.5px;margin-top:4px}
table{width:100%;border-collapse:collapse;background:var(--panel);border:1px solid var(--line);
  border-radius:14px;overflow:hidden;font-size:14px}
th,td{padding:10px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#0f1a2c;color:var(--muted);font-size:11.5px;text-transform:uppercase;letter-spacing:.7px;
  position:sticky;top:57px;z-index:5}
tbody tr:hover{background:#14213a}
tbody tr:last-child td{border-bottom:none}
td.mono,.mono{font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;background:#0e1a2e;border:1px solid #24395c;
  font-size:12px;color:var(--muted);margin:1px 2px}
.note{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
  border-radius:10px;padding:14px 16px;color:#c6d3e8;font-size:14px;margin:16px 0}
.note.warn{border-left-color:#ff8fa3}
.note.good{border-left-color:var(--high)}
.controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}
input[type=search],select{background:#0e1a2e;border:1px solid #24395c;color:var(--ink);
  padding:9px 12px;border-radius:10px;font-size:14px;min-width:220px}
.tablewrap{overflow:auto;border-radius:14px;max-height:none}
footer.site{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:26px 0 40px;margin-top:40px}
footer.site a{color:var(--muted)}
small.muted{color:var(--muted)}
ul.tight{margin:6px 0 0 18px;padding:0}
ul.tight li{margin:4px 0}
.tagrow{display:flex;gap:6px;flex-wrap:wrap;margin:6px 0 0}
@media(max-width:640px){
  th{position:static}
  .kpi .n{font-size:22px}
  .nav{gap:12px}
}
"""

NAV = [
    ("index.html", "Overview"),
    ("desk/picks.html", "Picks"),
    ("desk/matches.html", "Matches"),
    ("desk/coverage.html", "Sports"),
    ("desk/flagged.html", "Flagged"),
    ("desk/methodology.html", "Method"),
    ("desk/sources.html", "Sources"),
]


def page(title: str, body: str, depth: int, active: str, meta: dict) -> str:
    up = "../" * depth
    nav = []
    for href, label in NAV:
        act = " active" if href == active else ""
        nav.append(f'<a class="navlink{act}" href="{up}{href}">{e(label)}</a>')
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OLBG4 desk</title>
<meta name="description" content="OLBG4 — 15-sport OLBG coverage, our own originated lines, picks and written predictions.">
<link rel="stylesheet" href="{up}desk/assets/desk.css">
</head><body>
<header class="site"><div class="wrap"><div class="nav">
  <a class="brand" href="{up}index.html"><span class="mark">O4</span><span>OLBG4 desk</span></a>
  {''.join(nav)}
  <span class="spacer"></span>
  <span class="stamp">Data read {e(meta['capture_human'])}</span>
</div></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer class="site"><div class="wrap">
  <p><strong>OLBG4 desk</strong> — an independent record of upcoming matches in the 15 sports OLBG lists,
  our own originated prices, and written predictions. Every row links to the official body it came from;
  anything we could not confirm is published blank and listed on
  <a href="{up}desk/flagged.html">Flagged for Review</a>.</p>
  <p>Capture <span class="mono">{e(meta['capture_id'])}</span> ·
  window {e(meta['window_start'][:10])} → {e(meta['window_end'][:10])} ·
  build {e(meta['generated_utc'])} ·
  <a href="{up}desk/methodology.html">method</a> ·
  <a href="{up}desk/sources.html">sources</a> ·
  <a href="{up}desk/archive.html">earlier desks</a></p>
  <p>18+. Odds shown are our own originated fair prices, not bookmaker prices. No bet is risk-free.</p>
</div></footer>
</body></html>
"""


# ------------------------------------------------------------------ fragments
def pick_card(p: dict, up: str, show_full: bool = True) -> str:
    conf = p.get("confidence", "")
    txt = p.get("text", "")
    if not show_full and len(txt) > 300:
        txt = txt[:300].rsplit(" ", 1)[0] + "…"
    srcs = " · ".join(
        f'<a href="{e(s["url"])}" rel="noopener" target="_blank">{e(s["label"])}</a>'
        for s in p.get("sources", [])
    )
    return f"""<article class="pick">
  <div class="top">
    <div>
      <div class="sport">{e(p.get('sport'))} · {e(p.get('competition'))}</div>
      <div class="match">{e(p.get('match'))}</div>
      <div class="meta">{e(fmt_dt(p.get('start_utc')))}</div>
    </div>
    <span class="{BADGE.get(conf, 'badge')}">{e(conf)}</span>
  </div>
  <div class="sel">
    <div class="lab">Selection · {e(p.get('market'))}</div>
    <div class="val">{e(p.get('selection'))} <span class="px">{e(fmt_odds(p.get('fair_american')))}</span></div>
    <div class="meta">our fair price · implied {e(fmt_p(p.get('fair_prob')))}</div>
  </div>
  <p class="txt">{e(txt)}</p>
  <div class="src">Official sources: {srcs if srcs else '<em>none recorded — flagged</em>'}</div>
</article>"""


def row_tr(r: dict, up: str) -> str:
    pick = r.get("pick") or {}
    conf = pick.get("confidence", "")
    olbg = r.get("olbg") or {}
    mw = (r.get("markets") or {}).get("match_winner", {}).get("selections", [])
    line = ""
    if mw:
        line = " / ".join(f'{s["label"]} {fmt_odds(s["fair_american"])}' for s in mw[:2])
    flags = r.get("flags") or []
    olbg_cell = (f'<a href="{e(olbg["event_url"])}" rel="noopener" target="_blank">OLBG</a>'
                 if olbg.get("event_url") else "")
    src = (f'<a href="{e(r["official_url"])}" rel="noopener" target="_blank">{e(r.get("official_source_name") or "source")}</a>'
           if r.get("official_url") else '<span class="badge flag">blank</span>')
    return f"""<tr data-sport="{e(r.get('sport'))}" data-text="{e((r.get('side_a','')+' '+r.get('side_b','')+' '+r.get('competition','')+' '+(pick.get('selection',''))).lower())}">
  <td class="mono">{e(fmt_dt(r.get('start_utc')))}</td>
  <td>{e(r.get('sport'))}<br><small class="muted">{e(r.get('competition'))}</small></td>
  <td><strong>{e(r.get('side_a'))}</strong>{' <small class="muted">vs</small> ' if r.get('side_b') else ''}<strong>{e(r.get('side_b'))}</strong>
      {('<br><small class="muted">' + e(r.get('venue')) + '</small>') if r.get('venue') else ''}</td>
  <td class="mono">{line if line else '<small class="muted">not priced</small>'}</td>
  <td>{e(pick.get('selection','')) or '<small class="muted">no pick</small>'}
      {('<br><span class="mono">' + e(fmt_odds(pick.get('fair_american'))) + '</span>') if pick else ''}</td>
  <td>{('<span class="' + BADGE.get(conf, 'badge') + '">' + e(conf) + '</span>') if conf else ''}</td>
  <td>{olbg_cell}</td>
  <td>{src}</td>
  <td>{('<span class="badge flag">' + e(flags[0][:70]) + '</span>') if flags else ''}</td>
</tr>"""


def matches_table(rows: list, up: str, table_id: str = "rows") -> str:
    body = "".join(row_tr(r, up) for r in rows)
    return f"""<div class="controls">
  <input type="search" id="q-{table_id}" placeholder="Filter by team, player, competition…" aria-label="Filter rows">
  <select id="s-{table_id}" aria-label="Filter by sport">
    <option value="">All sports</option>
    {''.join(f'<option value="{e(s)}">{e(s)}</option>' for s, _ in SPORTS)}
  </select>
  <small class="muted" id="c-{table_id}"></small>
</div>
<div class="tablewrap"><table id="{table_id}">
<thead><tr><th>Start (UTC)</th><th>Sport / competition</th><th>Match</th><th>Our line</th>
<th>Pick</th><th>Confidence</th><th>OLBG</th><th>Official source</th><th>Flag</th></tr></thead>
<tbody>{body}</tbody></table></div>
<script>
(function(){{
  var q=document.getElementById('q-{table_id}'),s=document.getElementById('s-{table_id}'),
      c=document.getElementById('c-{table_id}'),rows=[].slice.call(document.querySelectorAll('#{table_id} tbody tr'));
  function apply(){{
    var t=q.value.toLowerCase().trim(),sp=s.value,n=0;
    rows.forEach(function(r){{
      var ok=(!sp||r.dataset.sport===sp)&&(!t||r.dataset.text.indexOf(t)>-1);
      r.style.display=ok?'':'none'; if(ok)n++;
    }});
    c.textContent=n+' of '+rows.length+' rows';
  }}
  q.addEventListener('input',apply);s.addEventListener('change',apply);apply();
}})();
</script>"""


def main() -> int:
    meta_raw = load("meta.json", {})
    desk = load("desk.json", {"rows": []})
    pred_doc = load("predictions.json", {"predictions": []})
    flag_doc = load("flags.json", {"flags": []})
    rows = desk.get("rows", [])
    preds = pred_doc.get("predictions", [])
    flags = flag_doc.get("flags", [])

    capture_human = meta_raw.get("capture_utc", "")
    meta = {
        "capture_id": meta_raw.get("capture_id", "—"),
        "capture_human": fmt_dt(capture_human) if capture_human else "—",
        "capture_utc": capture_human,
        "window_start": meta_raw.get("window_start", ""),
        "window_end": meta_raw.get("window_end", ""),
        "generated_utc": meta_raw.get("capture_utc", ""),
    }

    os.makedirs(os.path.join(DESK, "assets"), exist_ok=True)
    os.makedirs(os.path.join(DESK, "sports"), exist_ok=True)
    with open(os.path.join(DESK, "assets", "desk.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)

    pred_by_sport = {}
    for p in preds:
        pred_by_sport.setdefault(p["sport"], []).append(p)

    by_sport = {}
    for r in rows:
        by_sport.setdefault(r["sport"], []).append(r)
    for s in by_sport:
        by_sport[s].sort(key=lambda r: (r.get("start_utc") or "", r.get("side_a") or ""))

    # ---------------- counts
    priced = [r for r in rows if r.get("pick")]
    high = [p for p in preds if p.get("confidence") == "High"]
    today = "2026-10-24"
    today_rows = [r for r in rows if (r.get("start_utc") or "").startswith(today)]
    today_preds = [p for p in preds if (p.get("start_utc") or "").startswith(today)]

    # ============================================================ landing page
    top = sorted(preds, key=lambda p: (-(p.get("fair_prob") or 0)))[:6]
    kpis = [
        (len(rows), "matches in scope"),
        (len(priced), "with our line"),
        (len(preds), "written predictions"),
        (len(high), "high confidence"),
        (len(flags), "flagged for review"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="n">{n:,}</div><div class="l">{e(l)}</div></div>' for n, l in kpis
    )

    cov_rows = []
    for sport, slug in SPORTS:
        srows = by_sport.get(sport, [])
        sp = [r for r in srows if r.get("pick")]
        sh = [p for p in pred_by_sport.get(sport, []) if p.get("confidence") == "High"]
        if not srows:
            status = '<span class="badge flag">no official fixture located</span>'
        elif not sp:
            status = '<span class="badge low">listed, not priced</span>'
        elif sh:
            status = '<span class="badge high">high pick available</span>'
        else:
            status = '<span class="badge ok">priced</span>'
        cov_rows.append(
            f'<tr><td><a href="desk/sports/{slug}.html"><strong>{e(sport)}</strong></a></td>'
            f'<td class="mono">{len(srows)}</td><td class="mono">{len(sp)}</td>'
            f'<td class="mono">{len(pred_by_sport.get(sport, []))}</td><td class="mono">{len(sh)}</td>'
            f'<td>{status}</td></tr>'
        )

    lead = today_preds or preds
    top_today = sorted(lead, key=lambda p: (-(p.get("fair_prob") or 0)))[:3]
    lead_day = (sorted(lead, key=lambda p: p.get("start_utc") or "")[0].get("start_utc") or "")[:10]         if lead else ""
    lead_label = "Today's highest-confidence picks" if today_preds else "Next up: highest-confidence picks"
    lead_date = fmt_day(lead_day) if lead_day else ""
    todays_block = ""
    if top_today:
        no_today = ("" if today_preds else
                    "Nothing in scope kicks off later today, so these are the next fixtures with a written "
                    "prediction. ")
        todays_block = f"""
<h2>{lead_label} <small class="muted">— {e(lead_date)}</small></h2>
<p class="lede">{no_today}Each card shows the exact selection, our fair price and the confidence label.
The full reasoning is under <a href="desk/picks.html">Picks</a>.</p>
<div class="pickgrid">{''.join(pick_card(p, '', show_full=False) for p in top_today)}</div>"""
    else:
        todays_block = """
<h2>Today's highest-confidence picks</h2>
<div class="note warn"><strong>No match in scope kicks off today.</strong> The next fixtures are listed
below and on <a href="desk/matches.html">Matches</a>. Nothing has been invented to fill this space.</div>"""

    body = f"""
<h1>Every match we cover, our own line, and exactly where the pick is.</h1>
<p class="lede">OLBG lists fifteen sports outside football. This desk keeps one clean record of the
matches in those sports that are still to be played, originates a price for each one from official data,
labels a confidence, and writes the prediction out in full. Blanks are deliberate: an unconfirmed value is
never filled in.</p>
<div class="kpis">{kpi_html}</div>
<div class="note"><strong>Read this first.</strong> Official data was read at
<strong>{e(meta['capture_human'])}</strong>. Every fixture below starts after that read and after the
publishing cut-off, so nothing on this site is a finished match being passed off as a preview. Where a
governing body publishes no machine-readable fixture list (several do not), the sport is reported as covered
but unpriced rather than guessed at.</div>

{todays_block}

<h2>Where everything is</h2>
<div class="cards3">
  <a class="bigcard" href="desk/picks.html"><div class="t">Picks →</div>
    <div class="d">{len(preds)} written predictions. One card per pick: selection, price, confidence, reasoning, sources.</div></a>
  <a class="bigcard" href="desk/matches.html"><div class="t">Matches →</div>
    <div class="d">All {len(rows)} fixtures in one table, with our line, pick and official source on every row.</div></a>
  <a class="bigcard" href="desk/coverage.html"><div class="t">Sports →</div>
    <div class="d">The 15 covered sports, page by page: what we could price and what we could not.</div></a>
</div>

<h2>Coverage by sport</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>Matches</th><th>Priced</th><th>Predictions</th><th>High</th><th>Status</th></tr></thead>
<tbody>{''.join(cov_rows)}</tbody></table></div>

<h2>Strongest picks on the board</h2>
<p class="lede">The next strongest selections after the three above, across every sport. Prices are
originated from official data, not copied from a bookmaker.</p>
<div class="pickgrid">{''.join(pick_card(p, '', show_full=False) for p in top[3:6])}</div>

<h2>Next fixtures</h2>
<p class="lede">The soonest {min(12, len(rows))} matches in the window. The full list is on
<a href="desk/matches.html">Matches</a>.</p>
{matches_table(sorted(rows, key=lambda r: (r.get('start_utc') or '9999'))[:12], '', 'next')}

<div class="note"><strong>On the price window.</strong> A selection at 70% or better is, on fair odds, always
shorter than −250 (70% is exactly −233). The desk prints the true price rather than stretching a
probability to fit the −250 to +10,000 band, and lists every pick that falls outside it on
<a href="desk/flagged.html">Flagged for Review</a>.</div>

<div class="note good"><strong>How to trust a row.</strong> Open the “Official source” link: it goes to the
governing body's own page (NHL, MLB, EuroLeague, WTA, PGA Tour, GBGB, WRC and so on), or to OLBG's own event
page where OLBG is the only listing. The capture bytes behind every number are hashed and listed on
<a href="desk/sources.html">Sources</a>.</div>
"""
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Overview", body, 0, "index.html", meta))

    # ================================================================ picks
    groups = []
    for sport, slug in SPORTS:
        sp = sorted(pred_by_sport.get(sport, []), key=lambda p: (-(p.get("fair_prob") or 0)))
        if not sp:
            continue
        cards = "".join(pick_card(p, "../") for p in sp)
        groups.append(f'<h2 id="{slug}">{e(sport)} <small class="muted">— {len(sp)} pick(s)</small></h2>'
                      f'<div class="pickgrid">{cards}</div>')
    empty_sports = [s for s, _ in SPORTS if not pred_by_sport.get(s)]
    empty_note = ""
    if empty_sports:
        empty_note = (f'<div class="note warn"><strong>No written prediction for: '
                      f'{e(", ".join(empty_sports))}.</strong> A prediction is only published when an official '
                      f'fixture and the inputs behind a price could be confirmed. Those sports are listed with '
                      f'their reason on <a href="coverage.html">Sports</a> rather than padded with a pick.</div>')
    jump = " ".join(f'<a class="pill" href="#{slug}">{e(s)}</a>' for s, slug in SPORTS
                    if pred_by_sport.get(s))
    body = f"""
<h1>Picks</h1>
<p class="lede">Every written prediction on the desk, newest first within each sport. Each one names the
selection, the price we make it, the confidence and the official facts it rests on.</p>
<div class="tagrow">{jump}</div>
{empty_note}
{''.join(groups) if groups else '<div class="note warn">No predictions published for this capture.</div>'}
"""
    with open(os.path.join(DESK, "picks.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Picks", body, 1, "desk/picks.html", meta))

    # ============================================================== matches
    body = f"""
<h1>All matches</h1>
<p class="lede">{len(rows)} fixtures across {len(by_sport)} sports, every one starting after the capture
read. Filter by sport or type to narrow it. “Our line” is the price we originate; where a row is not priced
the reason is flagged in the last column and explained on <a href="coverage.html">Sports</a>.</p>
<div class="note">Rows with an <strong>OLBG</strong> link are the events OLBG itself lists — that is where
the pick can be placed. Rows without one are confirmed on the governing body's schedule but were not listed
on OLBG at capture time.</div>
{matches_table(sorted(rows, key=lambda r: (r.get('start_utc') or '9999')), '', 'all')}
"""
    with open(os.path.join(DESK, "matches.html"), "w", encoding="utf-8") as fh:
        fh.write(page("All matches", body, 1, "desk/matches.html", meta))

    # ============================================================== coverage
    cov_detail = []
    for sport, slug in SPORTS:
        srows = by_sport.get(sport, [])
        sp = [r for r in srows if r.get("pick")]
        probs = [p for p in pred_by_sport.get(sport, [])]
        cov_detail.append(
            f'<tr><td><a href="sports/{slug}.html"><strong>{e(sport)}</strong></a></td>'
            f'<td class="mono">{len(srows)}</td><td class="mono">{len(sp)}</td>'
            f'<td class="mono">{len(probs)}</td>'
            f'<td>{e(", ".join(sorted({r.get("competition","") for r in srows if r.get("competition")})[:3]))}</td></tr>'
        )
    gaps = meta_raw.get("gaps", [])
    gap_rows = "".join(
        f'<tr><td><strong>{e(g["sport"])}</strong></td><td>{e(g["reason"])}</td>'
        f'<td>{f"""<a href="{e(g["source_url"])}" rel="noopener" target="_blank">official page</a>""" if g.get("source_url") else "—"}</td></tr>'
        for g in gaps
    )
    body = f"""
<h1>Sports</h1>
<p class="lede">The brief names fifteen sports. This is exactly what we could confirm for each of them in
the window, and what we could not.</p>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>Matches</th><th>Priced</th><th>Predictions</th><th>Competitions seen</th></tr></thead>
<tbody>{''.join(cov_detail)}</tbody></table></div>

<h2>Why some sports are thin</h2>
<p class="lede">An unpriced sports page is a finding, not an omission. These are the governing-body pages we
read and what they returned.</p>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>What the official source returned</th><th>Page we read</th></tr></thead>
<tbody>{gap_rows or '<tr><td colspan="3">No coverage gaps recorded for this capture.</td></tr>'}</tbody></table></div>

<h2>Browse by sport</h2>
<div class="cards3">
{''.join(f'<a class="bigcard" href="sports/{slug}.html"><div class="t">{e(sport)}</div><div class="d">{len(by_sport.get(sport, []))} matches · {len([r for r in by_sport.get(sport, []) if r.get("pick")])} priced · {len(pred_by_sport.get(sport, []))} predictions</div></a>' for sport, slug in SPORTS)}
</div>
"""
    with open(os.path.join(DESK, "coverage.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Sports", body, 1, "desk/coverage.html", meta))

    # ========================================================= per-sport pages
    gap_by_sport = {g["sport"]: g for g in gaps}
    for sport, slug in SPORTS:
        srows = by_sport.get(sport, [])
        sp = sorted(pred_by_sport.get(sport, []), key=lambda p: (-(p.get("fair_prob") or 0)))
        priced_n = len([r for r in srows if r.get("pick")])
        gap = gap_by_sport.get(sport)
        gap_link = (f' <a href="{e(gap["source_url"])}" rel="noopener" target="_blank">Official page</a>.'
                    if gap and gap.get("source_url") else ".")
        gap_note = (f'<div class="note warn"><strong>Coverage note.</strong> {e(gap["reason"])}{gap_link}</div>'
                    if gap else "")
        pick_block = (f'<h2>Written predictions</h2><div class="pickgrid">'
                      f'{"".join(pick_card(p, "../../") for p in sp)}</div>' if sp else
                      '<div class="note">No written prediction for this sport in this window — see the coverage note above.</div>')
        body = f"""
<h1>{e(sport)}</h1>
<p class="lede">{len(srows)} matches · {priced_n} priced from official data · {len(sp)} written
prediction(s). Back to <a href="../coverage.html">all sports</a>.</p>
{gap_note}
{pick_block}
<h2>Fixtures</h2>
{matches_table(srows, "../../", 'sp-' + slug) if srows else '<div class="note warn">No official fixture for this sport was confirmed for the window.</div>'}
"""
        with open(os.path.join(DESK, "sports", f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(sport, body, 2, "desk/coverage.html", meta))

    # ================================================================ flagged
    sev = {"high": "badge flag", "medium": "badge med", "low": "badge low"}
    flag_rows = "".join(
        f"""<tr><td><code>{e(f.get('id',''))}</code></td><td>{e(f.get('sport',''))}</td>
        <td>{e(f.get('match',''))}</td><td>{e(f.get('issue',''))}</td>
        <td>{e(f.get('detail',''))}</td>
        <td>{f'<a href="{e(f["source_url"])}" rel="noopener" target="_blank">source</a>' if f.get('source_url') else '—'}</td>
        <td><span class="{sev.get(f.get('severity','low'),'badge low')}">{e(f.get('severity','low'))}</span></td></tr>"""
        for f in flags
    ) or '<tr><td colspan="7">No irregularities recorded.</td></tr>'
    body = f"""
<h1>Flagged for Review</h1>
<p class="lede">Everything on this page is published because we could not confirm it, it contradicts a
source, or it is a known defect in the repository. Nothing here blocks the rest of the desk; it is listed
so it can be checked by hand. Each item links to the page it came from.</p>
<div class="note warn"><strong>{len(flags)} item(s).</strong> Unconfirmed values are left blank on the desk —
they are never inferred, and no pick is built on one.</div>
<div class="tablewrap"><table>
<thead><tr><th>ID</th><th>Sport</th><th>Match / row</th><th>Issue</th><th>Detail</th><th>Source</th><th>Severity</th></tr></thead>
<tbody>{flag_rows}</tbody></table></div>
"""
    with open(os.path.join(DESK, "flagged.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Flagged for Review", body, 1, "desk/flagged.html", meta))

    # ============================================================ methodology
    body = """
<h1>Method</h1>
<p class="lede">Short version: official facts in, our own price out. No bookmaker or OLBG price is ever used
as an input to a line.</p>

<h2>1. What is in scope</h2>
<p>The fifteen sports OLBG lists outside football: Golf, Volleyball, Rugby Union, Cricket, Snooker, Darts,
Baseball, Gaelic Sports, Greyhounds, Tennis, Motor Racing, Handball, Ice Hockey, Basketball, Rugby League.
Football, horse racing, boxing, MMA, American football, Aussie Rules, cycling, bowls, table tennis, badminton,
netball and esports are out of scope.</p>

<h2>2. Where the fixtures come from</h2>
<p>Only from the governing body. Ice Hockey from the NHL's own schedule and standings APIs plus Liiga and the
SHL; Baseball from MLB's stats API; Basketball from EuroLeague's live API; Tennis from the WTA API and the
ATP's official posting service; Golf from the PGA Tour and DP World Tour; Greyhounds from the Greyhound Board
of Great Britain; Motor Racing from Formula 1 and MotoGP. OLBG's own sport hubs are read to record which
events OLBG is listing — that is the “OLBG” link on a row, and it is where a pick can be placed.</p>

<h2>3. How a price is made</h2>
<ul class="tight">
  <li><strong>Scoring sports</strong> (ice hockey, handball, football-shaped totals) use a Poisson goal model
  calibrated on the league's own goals-per-game rate, with team attack/defence rates taken from the official
  standings. The handicap and total markets are integrated from the same grid, so they cannot contradict the
  match-winner price.</li>
  <li><strong>Best-of formats</strong> (tennis, snooker, darts) convert a per-set or per-frame probability into
  the probability of winning the match at the official format length.</li>
  <li><strong>Rank-based sports</strong> (golf outrights, snooker, motorsport) use a logistic strength curve on
  the official ranking or standings gap, normalised so the field sums to 1.0000.</li>
  <li>Every two-way market is renormalised so the legs sum to exactly 1.0000 — there is no margin baked in, and
  no leg is allowed outside 0.005–0.995.</li>
</ul>

<h2>4. Confidence</h2>
<p><span class="badge high">High</span> 70% or better on our own number, and only where the official inputs
actually exist for that fixture. <span class="badge med">Medium</span> 55–70%.
<span class="badge low">Low</span> below 55%, or any model whose sample is one match / one round, which is
capped at Medium however strong it looks.</p>

<h2>5. The price window</h2>
<p>The brief asks for high-confidence picks between −250 and +10,000 American. On fair odds those two
conditions overlap only in a narrow band: 70% probability is exactly −233, so a genuine 70%+ pick is
<em>always</em> shorter than −250. The desk does not distort the probability to fit the window. It publishes
the true price and says so on the row, and every pick outside the window is listed on
<a href="flagged.html">Flagged for Review</a>.</p>

<h2>6. What we refuse to do</h2>
<ul class="tight">
  <li>No fixture is invented. If no official schedule lists it, the sport is reported as unpriced.</li>
  <li>No injury, suspension or team-news claim is published without a source that states it.</li>
  <li>No blank is filled from a neighbouring row, an average, or a previous season.</li>
  <li>No prediction is written without a named selection and a stated reason.</li>
</ul>

<h2>7. Words we do not use</h2>
<p>The predictions are written to be read by a person: they name the teams or players, the form, the relevant
recent results and the selection. They deliberately avoid internal process vocabulary.</p>
"""
    with open(os.path.join(DESK, "methodology.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Method", body, 1, "desk/methodology.html", meta))

    # ================================================================ sources
    cap_dir = os.path.join(DATA, "capture", meta_raw.get("capture_id", ""))
    man = {}
    mp = os.path.join(cap_dir, "manifest.json")
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            man = json.load(fh)
    recs = man.get("records", [])
    src_rows = "".join(
        f'<tr><td>{e(r.get("sport",""))}</td><td><a href="{e(r["url"])}" rel="noopener" target="_blank">'
        f'{e(r["url"])}</a></td><td class="mono">{r.get("bytes",0):,}</td>'
        f'<td class="mono"><code>{e(r.get("sha256","")[:16])}…</code></td></tr>'
        for r in sorted(recs, key=lambda r: (r.get("sport",""), r.get("id","")))
    )
    fails = "".join(
        f'<tr><td><a href="{e(f["url"])}" rel="noopener" target="_blank">{e(f["url"])}</a></td>'
        f'<td class="mono">{e(str(f.get("status") or ""))}</td><td>{e(f.get("error","")[:120])}</td></tr>'
        for f in man.get("failures", [])
    )
    body = f"""
<h1>Sources</h1>
<p class="lede">Every page we read, with the byte count and SHA-256 of the exact response. The capture is
committed to this repository, so any number on the site can be traced back to the bytes it came from.</p>
<div class="kpis">
  <div class="kpi"><div class="n">{man.get('ok', 0)}</div><div class="l">pages read</div></div>
  <div class="kpi"><div class="n">{man.get('failed', 0)}</div><div class="l">unavailable</div></div>
  <div class="kpi"><div class="n">{sum(r.get('bytes',0) for r in recs):,}</div><div class="l">bytes captured</div></div>
</div>
<div class="note">Capture <span class="mono">{e(man.get('capture_id', meta['capture_id']))}</span>,
started {e(man.get('started_utc','—'))}, finished {e(man.get('finished_utc','—'))}.</div>
<h2>Pages read</h2>
<div class="tablewrap"><table>
<thead><tr><th>Sport</th><th>URL</th><th>Bytes</th><th>SHA-256</th></tr></thead>
<tbody>{src_rows or '<tr><td colspan="4">Capture manifest not available for this build.</td></tr>'}</tbody></table></div>
<h2>Pages that refused us</h2>
<p class="lede">These are recorded rather than worked around. A source that blocks us is a reason to leave a
value blank, not to substitute another one.</p>
<div class="tablewrap"><table>
<thead><tr><th>URL</th><th>Status</th><th>Error</th></tr></thead>
<tbody>{fails or '<tr><td colspan="3">None.</td></tr>'}</tbody></table></div>
"""
    with open(os.path.join(DESK, "sources.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Sources", body, 1, "desk/sources.html", meta))

    # ================================================================ archive
    peers = meta_raw.get("peers", [])
    peer_rows = "".join(
        f'<tr><td><a href="../{e(p["href"])}">{e(p["label"])}</a></td><td>{e(p.get("note",""))}</td></tr>'
        for p in peers
    )
    body = f"""
<h1>Earlier desks</h1>
<p class="lede">Fifty-odd earlier working sessions published their own dashboards in this repository. They
are kept for the record and are <em>not</em> part of this desk. Their tables are dated snapshots from 21–23
October and many of their fixtures have since been played, so use the
<a href="../index.html">overview</a> for anything current.</p>
<div class="note">If you arrived from a search engine looking for a specific match, the current record is on
<a href="matches.html">Matches</a>. The pages below are history.</div>
<div class="tablewrap"><table>
<thead><tr><th>Desk</th><th>What it was</th></tr></thead>
<tbody>{peer_rows or '<tr><td colspan="2">No earlier desks recorded.</td></tr>'}</tbody></table></div>
"""
    with open(os.path.join(DESK, "archive.html"), "w", encoding="utf-8") as fh:
        fh.write(page("Earlier desks", body, 1, "desk/archive.html", meta))

    print(f"index.html + 7 desk pages + {len(SPORTS)} sport pages written "
          f"({len(rows)} rows, {len(preds)} predictions, {len(flags)} flags)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

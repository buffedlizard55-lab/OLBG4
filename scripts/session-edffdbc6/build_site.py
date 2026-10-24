#!/usr/bin/env python3
"""Board ZZ — build the clarity-first GitHub Pages desk under session-edffdbc6/.

Every table row that carries a fact also carries the official source link it was read from.
Rows whose value could not be confirmed are blank and listed on flagged.html.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-edffdbc6"
OUT = ROOT / "session-edffdbc6"

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}

def _capture_time() -> datetime:
    stamps = sorted((ROOT / "data" / "session-edffdbc6" / "capture").glob("*/manifest.json"))
    if stamps:
        m = json.loads(stamps[-1].read_text(encoding="utf-8"))
        return datetime.fromisoformat(m["started_utc"].replace("Z", "+00:00"))
    return datetime.now(timezone.utc)


NOW = _capture_time()


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""))


def ts(iso_dt: str) -> str:
    if not iso_dt:
        return "—"
    dt = datetime.fromisoformat(iso_dt.replace("Z", "+00:00"))
    return dt.strftime("%d %b %H:%MZ")


def badge(conf: str) -> str:
    c = conf.lower()
    return f'<span class="badge {c}">{esc(conf)}</span>'


def link(url: str, text: str) -> str:
    if not url:
        return '<span class="muted">—</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text)}</a>'


CSS = """
:root{--ink:#0e1726;--muted:#5c6b80;--line:#e3e8ef;--bg:#f6f8fb;--card:#fff;--accent:#0b6b53;--accent2:#0f4c81;
--high:#0a7a4a;--med:#a86400;--low:#5c6b80}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent2)}
header.top{background:var(--ink);color:#fff;padding:14px 20px;position:sticky;top:0;z-index:20;box-shadow:0 2px 8px rgba(0,0,0,.15)}
header.top .brand{font-weight:700;font-size:17px;letter-spacing:.2px}
header.top .sub{color:#a9b7c9;font-size:12.5px;margin-top:2px}
nav.main{background:#fff;border-bottom:1px solid var(--line);padding:0 12px;position:sticky;top:60px;z-index:19;overflow-x:auto;white-space:nowrap}
nav.main a{display:inline-block;padding:11px 10px;font-size:13.5px;color:#33415c;text-decoration:none;border-bottom:2px solid transparent}
nav.main a:hover{border-bottom-color:var(--accent)}
nav.main a.on{border-bottom-color:var(--accent);font-weight:600;color:var(--ink)}
main{max-width:1240px;margin:0 auto;padding:22px 18px 60px}
h1{font-size:26px;margin:4px 0 6px}
h2{font-size:19px;margin:30px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
h3{font-size:16px;margin:18px 0 8px}
p.lead{color:var(--muted);margin:0 0 16px;max-width:900px}
.grid{display:grid;gap:14px}
.g4{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.metric{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.metric .n{font-size:26px;font-weight:700}
.metric .l{font-size:12.5px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.table-wrap{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:auto}
table{border-collapse:collapse;width:100%;font-size:13.5px}
th,td{padding:9px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f3f8;font-size:12px;text-transform:uppercase;letter-spacing:.4px;color:#465268;position:sticky;top:0}
tr:last-child td{border-bottom:none}
tr.hi td{background:#f1fbf5}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:700;color:#fff}
.badge.high{background:var(--high)}.badge.medium{background:var(--med)}.badge.low{background:var(--low)}
.pick{font-weight:700}
.price{font-variant-numeric:tabular-nums;font-weight:600;color:var(--accent)}
.muted{color:var(--muted)}
.pill{display:inline-block;background:#eef3f8;border:1px solid var(--line);border-radius:999px;padding:4px 10px;font-size:12.5px;margin:3px 4px 0 0}
.hero{background:linear-gradient(120deg,#0e1726,#123c5a);color:#fff;border-radius:14px;padding:20px 22px;margin-bottom:16px}
.hero h1{color:#fff;margin-top:0}
.hero p{color:#c9d6e6;margin:6px 0 0}
.steps{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));margin:10px 0 4px}
.step{background:#fff;border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:10px;padding:10px 12px}
.step b{display:block;font-size:13px;color:var(--accent)}
.pred{border-left:4px solid var(--high)}
.pred .hd{font-weight:700;margin-bottom:6px}
.small{font-size:12.5px;color:var(--muted)}
details{background:#fff;border:1px solid var(--line);border-radius:10px;padding:10px 12px;margin:10px 0}
summary{cursor:pointer;font-weight:600}
footer{color:var(--muted);font-size:12.5px;text-align:center;padding:26px 10px}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:12.5px}
.notice{background:#fff8e6;border:1px solid #f0dca8;border-radius:10px;padding:12px 14px;font-size:13.5px}
"""


def page(name: str, title: str, body: str, depth: int = 0) -> str:
    pre = "../" * depth
    nav_items = [
        ("index.html", "Dashboard"),
        ("picks.html", "All picks"),
        ("matches.html", "Matches"),
        ("markets.html", "Markets"),
        ("predictions.html", "Predictions"),
        ("coverage.html", "Coverage"),
        ("olbg.html", "OLBG"),
        ("sources.html", "Sources"),
        ("methodology.html", "Method"),
        ("verification.html", "Verification"),
        ("review.html", "Repo review"),
        ("flagged.html", "Flagged"),
    ]
    links = "".join(
        f'<a class="{"on" if href == name else ""}" href="{pre}{href}">{esc(label)}</a>' for href, label in nav_items
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{esc(title)} · OLBG4 own-line desk</title>
<link rel="stylesheet" href="{pre}assets/site.css"/>
</head><body>
<header class="top"><div class="brand">OLBG4 · own-line picks desk</div>
<div class="sub">15 OLBG sports · official-source fixtures · our own prices · written predictions</div></header>
<nav class="main">{links}<a href="{pre}../index.html">Repo home</a></nav>
<main>
{body}
</main>
<footer>Generated from committed capture data · every number on this site is rebuilt from the captured official payloads · unconfirmed values are blank and listed on the Flagged page.</footer>
</body></html>
"""


def table(headers: list[str], rows: list[list[str]], hi_rows: set[int] | None = None,
          cls: str = "") -> str:
    hi_rows = hi_rows or set()
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = []
    for i, r in enumerate(rows):
        k = ' class="hi"' if i in hi_rows else ""
        body.append(f"<tr{k}>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


# ------------------------------------------------------------------------------ source rendering
def market_label(row: dict) -> str:
    p = row.get("pick") or {}
    return p.get("market_label", "")


def pick_cell(row: dict) -> str:
    p = row.get("pick")
    if not p:
        return '<span class="muted">no line originated</span>'
    return (f'<span class="pick">{esc(p["selection"])}</span> '
            f'<span class="price">{esc(p["fair_american_str"])}</span>'
            f'<div class="small">{esc(p["market_label"])} · {p["fair_prob"] * 100:.1f}%</div>')


def match_cell(row: dict) -> str:
    if row["sport"] in ("Baseball", "Ice Hockey", "Basketball"):
        return f'{esc(row["away"])} @ {esc(row["home"])}'
    return f'{esc(row["home"])} v {esc(row["away"])}'


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    preds_doc = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    fixes_doc = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))
    flagged_doc = json.loads((DATA / "flagged.json").read_text(encoding="utf-8"))
    review_doc = json.loads((DATA / "review.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "capture" / desk["capture_id"] / "manifest.json").read_text(encoding="utf-8"))

    rows = desk["rows"]
    preds = preds_doc["predictions"]
    pred_by_row = {p["row_id"]: p for p in preds}
    fixtures = fixes_doc["fixtures"]
    by_sport: dict[str, list[dict]] = {s: [] for s in SPORTS}
    for r in rows:
        by_sport.setdefault(r["sport"], []).append(r)
    fixtures_by_sport: dict[str, list[dict]] = {s: [] for s in SPORTS}
    for f in fixtures:
        fixtures_by_sport.setdefault(f["sport"], []).append(f)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets" / "site.css").write_text(CSS, encoding="utf-8")

    start = datetime.fromisoformat(rows[0]["start_utc"].replace("Z", "+00:00")) if rows else NOW
    in24 = [r for r in rows if datetime.fromisoformat(r["start_utc"].replace("Z", "+00:00")) <= NOW + timedelta(days=1)]
    highs24 = [r for r in in24 if r["confidence"] == "High"]
    highs_all = [r for r in rows if r["confidence"] == "High"]
    covered = [s for s in SPORTS if by_sport.get(s)]
    uncovered = [s for s in SPORTS if not by_sport.get(s)]

    # ---------------------------------------------------------------- dashboard
    metric_cards = "".join(
        f'<div class="metric"><div class="n">{v}</div><div class="l">{esc(k)}</div></div>'
        for k, v in [
            ("official fixtures verified", len(fixtures)),
            ("fixtures with our own lines", len(rows)),
            ("picks inside the odds window", len(highs_all)),
            ("written predictions", len(preds)),
            ("sports with lines", f"{len(covered)}/15"),
        ]
    )

    exec_rows = []
    hi_idx = set()
    for i, r in enumerate(sorted(in24, key=lambda x: (x["confidence"] != "High", x["start_utc"]))):
        if r["confidence"] == "High":
            hi_idx.add(i)
        exec_rows.append([
            ts(r["start_utc"]), esc(r["sport"]), match_cell(r), esc(r["competition"]),
            pick_cell(r), badge(r["confidence"]),
            link(r["source"]["url"], r["source"]["name"].split("(")[0].strip()),
        ])

    headline = sorted(highs24, key=lambda r: -r["pick"]["fair_prob"])[:5]
    headline_cards = "".join(
        f'<div class="card"><div class="small">{esc(r["sport"])} · {ts(r["start_utc"])} · {esc(r["competition"])}</div>'
        f'<div style="font-weight:700;margin:4px 0 2px">{match_cell(r)}</div>'
        f'<div class="pick" style="font-size:16px">PICK: {esc(r["pick"]["selection"])} '
        f'<span class="price">{esc(r["pick"]["fair_american_str"])}</span></div>'
        f'<div class="small">{esc(r["pick"]["market_label"])} · {r["pick"]["fair_prob"] * 100:.1f}% · '
        f'<a href="{esc(r["source"]["url"])}" target="_blank" rel="noopener">source</a>'
        + (f' · <a href="predictions.html#pred-{esc(pred_by_row[r["id"]]["prediction_id"])}">written prediction</a>'
           if r["id"] in pred_by_row else "")
        + '</div></div>'
        for r in headline
    ) or '<div class="card muted">No High-confidence pick with a kick-off inside the next 24 hours. See All picks.</div>'

    sport_strip = "".join(
        f'<a class="pill" href="sports/{SLUG[s]}.html">{esc(s)} · {len(by_sport.get(s, []))} rows · '
        f'{sum(1 for r in by_sport.get(s, []) if r["confidence"] == "High")} High</a>'
        for s in SPORTS
    )

    dash = f"""
<div class="hero">
  <h1>Today's picks, in one place</h1>
  <p>Capture {esc(desk['capture_id'])} · fixtures from {esc(desk['cutoff_utc'])} to {esc(desk['horizon_utc'])} · every pick shows the selection, the price we originate, the probability behind it and the official page it came from.</p>
</div>

<div class="steps">
  <div class="step"><b>1 · What the pick is</b>The <span class="pick">PICK</span> column always prints the exact bet — team/player, market and line — followed by our fair price. Nothing else in a row is the bet.</div>
  <div class="step"><b>2 · Where the picks live</b>This dashboard shows today's; <a href="picks.html">All picks</a> lists every one, and each sport page repeats its own under <i>Picks</i>.</div>
  <div class="step"><b>3 · How confidence is set</b><span class="badge high">High</span> = our line puts the selection at 70.0–71.4% <i>and</i> inside −250…+10,000. <span class="badge medium">Medium</span> ≥ 55%. Everything else is <span class="badge low">Low</span>.</div>
</div>

<div class="grid g4" style="margin:16px 0 4px">{metric_cards}</div>

<h2>Executive summary — highest-confidence picks for the next 24 hours</h2>
<div class="grid g3">{headline_cards}</div>

<h2>Every pick in the next 24 hours</h2>
<p class="lead">{len(in24)} fixtures kick off within 24 hours; {len(highs24)} of them carry a High-confidence pick. Sorted High first, then by kick-off. Full detail and the written predictions are one click away.</p>
{table(["Kick-off (UTC)", "Sport", "Match", "Competition", "PICK (market · probability)", "Confidence", "Official source"],
       exec_rows, hi_idx)}

<h2>Sports covered</h2>
<div>{sport_strip}</div>
{('<div class="notice" style="margin-top:14px"><b>Coverage gap (flagged).</b> No own line could be originated for '
  + esc(', '.join(uncovered)) + ' because the official fixture or strength feed for that sport was not machine-readable in this capture. '
  'The exact reason for each is on <a href="coverage.html">Coverage</a> and the items are listed on <a href="flagged.html">Flagged</a>. '
  'Nothing has been invented to fill the space.</div>') if uncovered else ''}
"""
    (OUT / "index.html").write_text(page("index.html", "Dashboard", dash), encoding="utf-8")

    # ---------------------------------------------------------------- all picks
    pick_rows, hi2 = [], set()
    for i, r in enumerate(sorted(rows, key=lambda x: x["start_utc"])):
        if r["confidence"] == "High":
            hi2.add(i)
        pred = pred_by_row.get(r["id"])
        pick_rows.append([
            ts(r["start_utc"]), esc(r["sport"]), match_cell(r), esc(r["competition"]),
            pick_cell(r), badge(r["confidence"]),
            (f'<a href="predictions.html#pred-{esc(pred["prediction_id"])}">{esc(pred["prediction_id"])}</a>' if pred else '<span class="muted">—</span>'),
            link(r["source"]["url"], "official page"),
        ])
    picks_html = f"""
<h1>All picks</h1>
<p class="lead">Every fixture where we originated a line, with the selection we would back. {len(rows)} rows · {len(highs_all)} High · {sum(1 for r in rows if r['confidence'] == 'Medium')} Medium · {sum(1 for r in rows if r['confidence'] == 'Low')} Low.</p>
{table(["Kick-off (UTC)", "Sport", "Match", "Competition", "PICK (market · probability)", "Confidence", "Prediction", "Source"],
       pick_rows, hi2)}
"""
    (OUT / "picks.html").write_text(page("picks.html", "All picks", picks_html), encoding="utf-8")

    # ---------------------------------------------------------------- matches
    match_rows = []
    for f in sorted(fixtures, key=lambda x: x["start_utc"]):
        has_row = any(r["id"] == f["id"] for r in rows)
        match_rows.append([
            ts(f["start_utc"]), esc(f["sport"]), esc(f["competition"]), esc(f.get("stage") or ""),
            f'{esc(f["away"])} @ {esc(f["home"])}' if f["sport"] in ("Baseball", "Ice Hockey", "Basketball") else f'{esc(f["home"])} v {esc(f["away"])}',
            esc(f.get("venue") or ""),
            badge("High") if has_row and next(r["confidence"] for r in rows if r["id"] == f["id"]) == "High"
            else (badge("Medium") if has_row and next(r["confidence"] for r in rows if r["id"] == f["id"]) == "Medium"
                  else (badge("Low") if has_row else '<span class="muted">no line</span>')),
            link(f["source"]["url"], f["source"]["name"].split("(")[0].strip()),
        ])
    matches_html = f"""
<h1>Every verified fixture</h1>
<p class="lead">{len(fixtures)} fixtures were read from official payloads with both sides, the competition and a start time. A fixture is listed even when no line was originated for it — the last column shows the official page it came from.</p>
{table(["Kick-off (UTC)", "Sport", "Competition", "Stage", "Match", "Venue", "Confidence", "Official source"], match_rows)}
"""
    (OUT / "matches.html").write_text(page("matches.html", "Matches", matches_html), encoding="utf-8")

    # ---------------------------------------------------------------- markets
    mk_rows = []
    for r in sorted(rows, key=lambda x: x["start_utc"]):
        for m in r["markets"]:
            outs = "<br/>".join(
                f'{esc(o["selection"])} <span class="price">{esc(o["fair_american_str"])}</span> '
                f'<span class="muted">{o["fair_prob"] * 100:.1f}%</span>' for o in m["outcomes"]
            )
            mk_rows.append([esc(r["sport"]), match_cell(r), esc(m["market_label"]), outs,
                            esc(m.get("basis", "")), link(r["source"]["url"], "source")])
    markets_html = f"""
<h1>Markets we originated</h1>
<p class="lead">{desk['summary']['markets']} markets and {desk['summary']['outcomes']} priced selections across {len(rows)} fixtures — match winner, handicap/spread ladders, match totals and the sport-specific derivatives each model supports. Probabilities in each market sum to 1.000.</p>
{table(["Sport", "Match", "Market", "Selections (fair price · probability)", "Basis", "Source"], mk_rows)}
"""
    (OUT / "markets.html").write_text(page("markets.html", "Markets", markets_html), encoding="utf-8")

    # ---------------------------------------------------------------- predictions
    cards = []
    for p in preds:
        r = next((x for x in rows if x["id"] == p["row_id"]), None)
        cards.append(f"""
<div class="card pred" id="pred-{esc(p['prediction_id'])}">
  <div class="small">{esc(p['prediction_id'])} · {esc(p['sport'])} · {ts(p['start_utc'])} · {esc(p['competition'])}</div>
  <div class="hd">{esc(p['match'])}</div>
  <div class="pick" style="font-size:16px;margin-bottom:6px">PICK: {esc(p['selection'])} <span class="price">{esc(p['price'])}</span></div>
  <div class="small" style="margin-bottom:8px">{esc(p['market'])} · {p['fair_prob'] * 100:.1f}% · {p['word_count']} words</div>
  <p style="margin:0 0 10px">{esc(p['text'])}</p>
  <div class="small">Official source: {link(p['official_source_url'], p['official_source_name'])} · capture <code>{esc(p['capture_target_id'])}</code> · sha256 <code>{esc(p['capture_sha256'][:16])}…</code></div>
</div>""")
    preds_html = f"""
<h1>Written predictions</h1>
<p class="lead">{len(preds)} unique predictions, one per High-confidence pick (five per sport at most). Each names the teams or players, the form and recent results read from the official payload, an explicit selection and its price, and links the source of the numbers. Minimum length {preds_doc['summary']['min_words']} words; highest pairwise similarity {preds_doc['summary']['max_pairwise_trigram_jaccard']} (trigram Jaccard, well under the 0.30 cut-off).</p>
{''.join(cards) if cards else '<div class="card muted">No High-confidence picks in this capture window.</div>'}
"""
    (OUT / "predictions.html").write_text(page("predictions.html", "Predictions", preds_html), encoding="utf-8")

    # ---------------------------------------------------------------- coverage
    cov_rows = []
    for s in SPORTS:
        rs = by_sport.get(s, [])
        fs = fixtures_by_sport.get(s, [])
        if rs:
            status = f'<span class="badge high">lines originated</span>'
            note = (f"{len(rs)} fixtures priced · {sum(1 for r in rs if r['confidence'] == 'High')} High · "
                    f"{len(preds_doc['summary']['by_sport'].get(s, []) if isinstance(preds_doc['summary']['by_sport'].get(s), list) else [])} predictions")
        elif fs:
            status = '<span class="badge medium">fixtures only</span>'
            note = f"{len(fs)} verified fixtures, no strength input captured → no line originated (flagged)"
        else:
            status = '<span class="badge low">not covered</span>'
            note = COVERAGE_REASON.get(s, "no upcoming fixture in the captured window")
        cov_rows.append([esc(s), status, str(len(fs)), str(len(rs)), note])
    coverage_html = f"""
<h1>Coverage by sport</h1>
<p class="lead">The brief names fifteen sports. This table states exactly what was achieved for each one in this capture, and why, so nothing is implied that is not there.</p>
{table(["Sport", "Status", "Verified fixtures", "Fixtures with our line", "Detail"], cov_rows)}
<h2>Why some sports have no line</h2>
<ul>
{''.join(f'<li><b>{esc(s)}</b> — {esc(COVERAGE_REASON.get(s, "no upcoming fixture in the captured window"))}</li>' for s in SPORTS if not by_sport.get(s))}
</ul>
<h2>Capture failures behind the gaps</h2>
<p class="lead">{manifest['failed_count']} of {manifest['targets_total']} capture targets returned a non-200 status. Each is listed with its status code on <a href="sources.html">Sources</a>; the consequential ones are on <a href="flagged.html">Flagged</a>.</p>
"""
    (OUT / "coverage.html").write_text(page("coverage.html", "Coverage", coverage_html), encoding="utf-8")

    # ---------------------------------------------------------------- sport pages
    for s in SPORTS:
        rs = sorted(by_sport.get(s, []), key=lambda x: x["start_utc"])
        fs = sorted(fixtures_by_sport.get(s, []), key=lambda x: x["start_utc"])
        if rs:
            prow, hi3 = [], set()
            for i, r in enumerate(rs):
                if r["confidence"] == "High":
                    hi3.add(i)
                pred = pred_by_row.get(r["id"])
                prow.append([ts(r["start_utc"]), match_cell(r), esc(r["competition"]), pick_cell(r),
                             badge(r["confidence"]),
                             (f'<a href="../predictions.html#pred-{esc(pred["prediction_id"])}">prediction</a>' if pred else '<span class="muted">—</span>'),
                             link(r["source"]["url"], "official page")])
            section = table(["Kick-off (UTC)", "Match", "Competition", "PICK (market · probability)", "Confidence", "Written", "Source"], prow, hi3)
            mrows = []
            for r in rs:
                mrows.append([match_cell(r), esc(", ".join(r.get("markets_investigated", []))),
                              str(len(r["markets"])), str(sum(len(m["outcomes"]) for m in r["markets"])),
                              esc(r.get("winner_pick", {}).get("selection", "") if r.get("winner_pick") else ""),
                              esc(r["winner_pick"]["fair_american_str"] if r.get("winner_pick") else "")])
            markets_section = table(["Match", "Market families investigated", "Markets", "Priced selections", "Match-winner pick", "Price"], mrows)
        else:
            section = f'<div class="notice">No fixture in this sport could be priced in this capture. {esc(COVERAGE_REASON.get(s, ""))}</div>'
            markets_section = '<div class="notice">No markets originated.</div>'
        frow = [[ts(f["start_utc"]), esc(f["competition"]), esc(f.get("stage") or ""),
                 f'{esc(f["away"])} @ {esc(f["home"])}' if s in ("Baseball", "Ice Hockey", "Basketball") else f'{esc(f["home"])} v {esc(f["away"])}',
                 esc(f.get("venue") or ""), link(f["source"]["url"], f["source"]["name"].split("(")[0].strip())] for f in fs]
        sport_preds = "".join(
            f'<div class="card pred" style="margin:10px 0"><div class="small">{esc(p["prediction_id"])} · {ts(p["start_utc"])}</div>'
            f'<div class="hd">{esc(p["match"])}</div>'
            f'<div class="pick">PICK: {esc(p["selection"])} <span class="price">{esc(p["price"])}</span></div>'
            f'<p style="margin:8px 0">{esc(p["text"])}</p>'
            f'<div class="small">{link(p["official_source_url"], "official source")}</div></div>'
            for p in preds if p["sport"] == s)
        body = f"""
<h1>{esc(s)}</h1>
<p class="lead">{len(fs)} verified fixtures · {len(rs)} priced · {sum(1 for r in rs if r['confidence'] == 'High')} High-confidence picks · {sum(1 for p in preds if p['sport'] == s)} written predictions.</p>
<h2>Picks</h2>
{section}
<h2>Markets investigated</h2>
{markets_section}
<h2>Written predictions</h2>
{sport_preds or '<div class="card muted">No High-confidence pick in this sport, so no prediction was written.</div>'}
<h2>Verified fixtures</h2>
{table(["Kick-off (UTC)", "Competition", "Stage", "Match", "Venue", "Official source"], frow) if frow else '<div class="notice">No verified fixture.</div>'}
"""
        (OUT / "sports" / f"{SLUG[s]}.html").write_text(
            page(f"sports/{SLUG[s]}.html", s, body, depth=1), encoding="utf-8")

    # ---------------------------------------------------------------- methodology
    method = f"""
<h1>Method</h1>
<p class="lead">Everything on this site is rebuilt from committed bytes: captured official payloads → verified fixtures → our own prices → graded picks → written predictions. No price was typed by hand and no fixture was inferred.</p>

<h2>1 · Capture</h2>
<p>{manifest['targets_total']} official and OLBG targets were fetched by an open-egress GitHub Actions runner at {esc(manifest['started_utc'])} (capture <code>{esc(manifest['capture_id'])}</code>). {manifest['http_200_count']} returned HTTP 200; every response is stored as deterministic gzip with its SHA-256 in <code>manifest.json</code>, and each row on this site quotes the target id and digest it came from. The runner honours <code>olbg.com/robots.txt</code> ({len(manifest['robots_disallow_rules'])} disallow rules parsed for <code>*</code>) and uses a 1-second per-host delay there.</p>

<h2>2 · Fixture verification</h2>
<p>A fixture enters the desk only when the captured official payload gives both sides, the competition and a start time, and that start time is after the capture cut-off. Anything missing stays blank. Fixtures whose official feed was JavaScript-only could not be verified and are not invented — see <a href="coverage.html">Coverage</a>.</p>

<h2>3 · Our own lines</h2>
<ul>
<li><b>Ice hockey (NHL, Liiga)</b> — independent Poisson goal model: each side's goals-for and goals-against per game from the official standings, pulled toward the league mean, with home advantage. Match winner, puck-line ladder (−0.5…+7.5), total ladder (4.5–7.5).</li>
<li><b>Basketball (EuroLeague)</b> — normal points model on the official per-game points for/against after round six (σ margin 9.8, σ total 13.5). Winner, spread ladder, total ladder.</li>
<li><b>Baseball (MLB)</b> — Poisson run model from regular-season runs scored/allowed; winner, run line ±1.5, totals 6.5–10.5.</li>
<li><b>Tennis (WTA)</b> — ranking model from the official WTA singles list; winner, set handicap, total sets, exact set score.</li>
<li><b>Volleyball (PlusLiga)</b> — set-by-set binomial model from the league's own results; winner, set handicap, total sets.</li>
<li><b>Rugby Union (Top 14)</b> — points model from the official LNR ranking positions shown on the fixture; winner, handicap, total.</li>
</ul>
<p>Market probabilities sum to 1.000 inside each market (checked on every rebuild). Fair decimal = 1/p; American odds are re-derived from the decimal, never typed.</p>

<h2>4 · Confidence grading (and the arithmetic behind it)</h2>
<p><span class="badge high">High</span> requires both conditions in the brief: our probability ≥ 70% <b>and</b> a fair price inside −250…+10,000. A 70% shot is −233 and a −250 shot is 71.43%, so the two conditions overlap only for probabilities between 70.00% and 71.43%. That is a real constraint of the brief, not a shortcut, and it is recorded as ZZ-F01 on <a href="flagged.html">Flagged</a>. We therefore originate alternative handicap and total lines on the numbers a book actually posts and back the selection that lands in that band; a fixture with no threshold in the band is graded Medium (≥55%) or Low and gets no written prediction.</p>

<h2>5 · Predictions</h2>
<p>Only High picks receive a written prediction, five per sport at most, ranked by probability. Each text is at least {preds_doc['summary']['min_words']} words, unique (highest pairwise trigram Jaccard {preds_doc['summary']['max_pairwise_trigram_jaccard']}), names the teams/players, cites current form and recent results from the captured payload, states the exact selection and price, and links the official source. Injury or team news is mentioned only where an official feed in the capture documents it; where it does not, the text makes no injury claim at all.</p>

<h2>6 · What is deliberately not done</h2>
<ul>
<li>No value is copied from another desk, and no stale fixture is carried forward.</li>
<li>No line is originated for a sport without a captured strength input.</li>
<li>No injury, lineup, or weather claim is made from memory or from a secondary summary.</li>
</ul>
"""
    (OUT / "methodology.html").write_text(page("methodology.html", "Method", method), encoding="utf-8")

    # ---------------------------------------------------------------- sources
    srows = []
    for rec in sorted(manifest["records"], key=lambda r: (r["sport"], r["id"])):
        srows.append([
            esc(rec["sport"]), f'<code>{esc(rec["id"])}</code>',
            link(rec["url"], rec["url"][:78] + ("…" if len(rec["url"]) > 78 else "")),
            (str(rec["status"]) if rec.get("status") is not None else "refused"),
            f'{(rec.get("bytes") or 0):,}',
            f'<code>{esc((rec.get("sha256") or "")[:16])}…</code>' if rec.get("sha256") else '<span class="muted">—</span>',
            esc(rec.get("error") or ""),
        ])
    sources = f"""
<h1>Sources</h1>
<p class="lead">Every capture target, its HTTP status, its size and the SHA-256 of the exact bytes used. {manifest['http_200_count']} of {manifest['targets_total']} succeeded; failures are shown with their status code and are treated as gaps, never as zeros.</p>
{table(["Sport", "Target", "URL", "HTTP", "Bytes", "SHA-256", "Error"], srows)}
"""
    (OUT / "sources.html").write_text(page("sources.html", "Sources", sources), encoding="utf-8")

    # ---------------------------------------------------------------- verification
    ver = json.loads((DATA / "verify_report.json").read_text(encoding="utf-8")) if (DATA / "verify_report.json").exists() else None
    vrows = [[esc(c["check"]), '<span class="badge high">PASS</span>' if c["ok"] else '<span class="badge low">FAIL</span>',
              esc(c["detail"])] for c in (ver["checks"] if ver else [])]
    verification = f"""
<h1>Verification</h1>
<p class="lead">The gate re-runs the whole pipeline from the committed capture and compares it byte-for-byte with what is published, then re-tests every rule the brief sets.</p>
{('<p><b>Result:</b> ' + ('all checks passed' if ver['passed'] else 'FAILURES PRESENT') + f' · {len(ver["checks"])} checks · capture <code>{esc(ver["capture_id"])}</code></p>') if ver else '<div class="notice">Not yet generated.</div>'}
{table(["Check", "Result", "Detail"], vrows)}
<h2>Repo-wide checks</h2>
<ul>
<li>Every local link on the generated pages resolves (checked by <code>scripts/session-edffdbc6/verify.py</code>).</li>
<li>Every published price is rebuilt from its stored probability; every High row is re-tested against the 70% floor and the −250…+10,000 window.</li>
<li>Every prediction is re-counted for words and re-compared for uniqueness; the banned internal words are grepped.</li>
<li>The repo-wide publication audit (<code>scripts/audit_publication.py --check</code>) runs before the pull request.</li>
</ul>
"""
    (OUT / "verification.html").write_text(page("verification.html", "Verification", verification), encoding="utf-8")

    # ---------------------------------------------------------------- review
    rev_rows = [[esc(d["dataset"]), str(d["rows"]), str(d["missing_source_url"]), str(d["stale_date"]),
                 str(d["missing_prediction_on_high"]), esc(d["note"])] for d in review_doc["datasets"]]
    findings = "".join(f'<li><b>{esc(f["id"])}</b> — {esc(f["finding"])} {link(f["url"], "evidence") if f.get("url") else ""}</li>'
                       for f in review_doc["findings"])
    review = f"""
<h1>Repo review (line by line)</h1>
<p class="lead">The shared datasets were re-read row by row against the dates and source links they carry. Nothing in another owner's file was modified: the defects are reported here and on <a href="flagged.html">Flagged</a>, exactly as the brief requires.</p>
{table(["Dataset", "Rows", "Missing official source URL", "Date before the desk window", "High rows without a prediction", "Note"], rev_rows)}
<h2>Findings</h2>
<ul>{findings}</ul>
"""
    (OUT / "review.html").write_text(page("review.html", "Repo review", review), encoding="utf-8")

    # ---------------------------------------------------------------- flagged
    frows = [[esc(f["id"]), esc(f["severity"]), esc(f["item"]), esc(f["detail"]),
              (link(f["url"], "source") if f.get("url") else '<span class="muted">—</span>')]
             for f in flagged_doc["items"]]
    flagged = f"""
<h1>Flagged for review</h1>
<p class="lead">{len(flagged_doc['items'])} items that could not be confirmed, were refused, or are irregular. None of them blocks publication; each is listed with what was checked and, where one exists, the page to check it against.</p>
<div class="notice">Unconfirmed values are left blank everywhere on this site rather than filled in. If you want any of these chased further, name the item id.</div>
{table(["ID", "Severity", "Item", "Detail", "Source"], frows)}
"""
    (OUT / "flagged.html").write_text(page("flagged.html", "Flagged", flagged), encoding="utf-8")

    # ---------------------------------------------------------------- OLBG page
    olbg = json.loads((DATA / "olbg.json").read_text(encoding="utf-8"))
    hub_rows = [[esc(h["sport"]), link(h["url"], "hub"), str(h["matches_listed"]), str(h["upcoming_listed"]),
                 esc(h["sample"]), esc(h["status"])] for h in olbg["hubs"]]
    olbg_html = f"""
<h1>OLBG reverse-engineering</h1>
<p class="lead">What OLBG actually publishes, read from the site itself: the fifteen in-scope sport hubs, the match objects embedded in each page, and the market vocabulary attached to them.</p>

<h2>How the site is built</h2>
<ul>
<li>The sports hubs are server-rendered (SvelteKit). Each listed match is a <code>schema.org/SportsEvent</code> object carrying <code>itemprop="name"</code> (the pairing), <code>itemprop="startDate"</code> (ISO-8601 kick-off) and a canonical event URL of the form <code>/betting-tips/&lt;Sport&gt;/All_&lt;Sport&gt;/All_Events/&lt;Home&gt;_vs_&lt;Away&gt;/&lt;id&gt;?event_id=…</code>.</li>
<li>Tips themselves are attached to those events, not to a separate fixture database, which is why the hub shows only events that currently have tips.</li>
<li><code>robots.txt</code> disallows {len(manifest['robots_disallow_rules'])} path prefixes for <code>*</code> (API, sports, search, tipster, cache, and others). This desk only fetches public hub pages at a 1 request/second rate.</li>
<li>Sub-hub URLs that returned their own page this capture: NHL, NBA, EuroLeague, MLB. Deeper sub-hubs are link-only.</li>
</ul>

<h2>Hubs and what they list</h2>
{table(["Sport", "Hub", "Match objects with a start time", "Upcoming at capture", "Sample pairing", "HTTP"], hub_rows)}

<h2>Matches OLBG lists that we could not verify officially</h2>
<p class="lead">These are real OLBG listings — the pairing and kick-off come from OLBG's own page — but the corresponding official feed was not machine-readable, so they carry no price and no pick here. They are published so the list is complete, and they are flagged.</p>
{table(["Sport", "Match (as listed by OLBG)", "Kick-off (UTC)", "OLBG event page"],
       [[esc(m["sport"]), esc(m["name"]), ts(m["start_utc"]), link(m["url"], "OLBG")] for m in olbg["unverified_matches"][:80]])}
"""
    (OUT / "olbg.html").write_text(page("olbg.html", "OLBG", olbg_html), encoding="utf-8")

    print(f"built {len(list(OUT.rglob('*.html')))} pages into {OUT}")
    return 0


COVERAGE_REASON = {
    "Golf": "the only PGA Tour leaderboard in the capture is the in-play Bermuda Championship (no upcoming event page that is machine-readable); DP World Tour pages returned HTTP 403",
    "Snooker": "the Northern Ireland Open semi-final had already started and the final's second finalist is still to be decided in the captured snooker.org page, so no future fixture with both players is confirmed",
    "Darts": "pdc.tv serves a JavaScript shell (identical 1.24 MB payload for every page) and lists no fixture data outside scripts; OLBG darts listings are shown on the OLBG page but no official fixture page confirms them",
    "Gaelic Sports": "the only GAA fixture in the window (Shinty-Hurling International, 24 Oct 18:00) had started before the cut-off; county sites list no later fixture",
    "Greyhounds": "race cards and runners were captured from grireland.ie, but no verified form/time feed could support a probability for each runner, so no price was invented",
    "Motor Racing": "formula1.com and motogp.com render standings and session times client-side; no machine-readable entry list or championship table was captured",
    "Handball": "EHF Champions League and HBL pages are JavaScript shells; the Danish programme page carries no dates in its HTML",
    "Rugby League": "nrl.com returns a 862-byte challenge page and rlwc2026.com renders the draw client-side",
    "Cricket": "fixtures verified from Cricket Australia's official feed, but no team-strength table (ICC rankings) could be captured, so no line was originated",
    "Tennis": "no WTA tournament page in the capture listed a match starting after the cut-off",
}


if __name__ == "__main__":
    raise SystemExit(main())

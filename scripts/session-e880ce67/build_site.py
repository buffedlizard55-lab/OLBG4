#!/usr/bin/env python3
"""Render the fifteen-sport desk as static HTML (GitHub Pages, no JavaScript).

Inputs are the five JSON files this board produces; nothing else is read. The build is
deterministic: same inputs, byte-identical output, which is what the verifier checks.
"""

from __future__ import annotations

import datetime
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
OUT = os.path.join(ROOT, "session-e880ce67")

SPORTS = [("Golf", "golf"), ("Volleyball", "volleyball"), ("Rugby Union", "rugby-union"),
          ("Cricket", "cricket"), ("Snooker", "snooker"), ("Darts", "darts"),
          ("Baseball", "baseball"), ("Gaelic Sports", "gaelic-sports"),
          ("Greyhounds", "greyhounds"), ("Tennis", "tennis"),
          ("Motor Racing", "motor-racing"), ("Handball", "handball"),
          ("Ice Hockey", "ice-hockey"), ("Basketball", "basketball"),
          ("Rugby League", "rugby-league")]
SLUG = dict(SPORTS)
GAELIC = ["Gaelic Football", "Hurling"]

CSS = """
:root{--ink:#12161c;--mut:#5b6472;--line:#e2e6ec;--bg:#f7f8fa;--card:#fff;--acc:#0b6d3f;
--acc2:#0a4f8a;--hi:#0b6d3f;--me:#8a5a00;--lo:#5b6472;--warnbg:#fff8e6;--badbg:#fdf0f2}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 -apple-system,BlinkMacSystemFont,
"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc2);text-decoration:none}a:hover{text-decoration:underline}
header{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:9}
.wrap{max-width:1120px;margin:0 auto;padding:0 18px}
.nav{display:flex;gap:4px;align-items:center;height:58px;overflow-x:auto;white-space:nowrap}
.brand{font-weight:800;margin-right:14px;color:var(--ink)}
.nav a{padding:7px 10px;border-radius:8px;color:var(--mut);font-size:14px;font-weight:600}
.nav a.on{background:#eef2f7;color:var(--ink)}
main{padding:26px 0 60px}
h1{font-size:30px;line-height:1.2;margin:0 0 6px}
h2{font-size:20px;margin:34px 0 10px}h3{font-size:16px;margin:20px 0 6px}
.lede{color:var(--mut);margin:0 0 18px;font-size:16px;max-width:70ch}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 6px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.kpi b{display:block;font-size:26px;line-height:1.1}
.kpi span{color:var(--mut);font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px;margin:10px 0}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px}
.pick{border-left:4px solid var(--acc)}
.pick.med{border-left-color:#b8860b}.pick.low{border-left-color:#9aa3af}
.pick .sel{font-weight:800;font-size:17px;margin:2px 0 4px}
.meta{color:var(--mut);font-size:13px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700}
.b-high{background:#e7f5ec;color:var(--hi)}.b-med{background:#fdf4e0;color:var(--me)}
.b-low{background:#eef1f5;color:var(--lo)}
.b-no{background:#fdecef;color:#8a1c2f}
.num{font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;background:#fff;font-size:14px}
th,td{border-bottom:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
th{background:#f1f4f8;font-size:12px;letter-spacing:.02em;text-transform:uppercase;color:var(--mut)}
tbody tr:hover{background:#fafbfd}
.tw{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:10px 0}
.small{font-size:13px}.mut{color:var(--mut)}
.note{background:var(--warnbg);border:1px solid #f0dca8;border-radius:12px;padding:14px;margin:14px 0}
.bad{background:var(--badbg);border:1px solid #f2c8d0}
ul,ol{margin:8px 0 8px 20px;padding:0}li{margin:4px 0}
footer{border-top:1px solid var(--line);background:#fff;padding:22px 0;color:var(--mut);font-size:13px}
.chip{display:inline-block;background:#eef2f7;border-radius:6px;padding:1px 6px;font-size:12px}
.prose p{margin:0 0 8px}
"""

NAV = [("index.html", "Overview"), ("picks.html", "Picks"),
       ("predictions.html", "Predictions"), ("matches.html", "All matches"),
       ("markets.html", "Markets"), ("review.html", "Repo review"),
       ("flagged.html", "Flagged"), ("sources.html", "Sources"),
       ("methodology.html", "Method")]


def e(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def money(american: int | None) -> str:
    if american is None:
        return "—"
    return f"+{american}" if american > 0 else str(american)


def pct(p: float | None) -> str:
    return "—" if p is None else f"{p * 100:.1f}%"


def kick(iso: str) -> str:
    dt = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return dt.strftime("%a %d %b, %H:%M UTC")


def badge(conf: str) -> str:
    cls = {"High": "b-high", "Medium": "b-med", "Low": "b-low"}.get(conf, "b-no")
    return f'<span class="badge {cls}">{e(conf)}</span>'


def table(headers, rows, cls="") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    return (f'<div class="tw"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def page(title: str, body: str, depth: int = 0, active: str = "", meta: dict | None = None) -> str:
    up = "../" * depth
    nav = "".join(f'<a class="{"on" if href == active else ""}" href="{up}{href}">{label}</a>'
                  for href, label in NAV)
    stamp = meta.get("capture_human", "") if meta else ""
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · OLBG desk</title>
<meta name="description" content="Fifteen-sport OLBG desk: every upcoming market, our own fair lines, confidence labels and written predictions.">
<link rel="stylesheet" href="{up}assets/style.css">
</head><body>
<header><div class="wrap"><nav class="nav">
<span class="brand">OLBG desk</span>{nav}
</nav></div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
<p><strong>OLBG desk</strong> — independent record of the upcoming markets OLBG lists in the fifteen
sports in the brief, our own fair lines where a governing body publishes the inputs, and the reasoning
behind each pick. Every row links its official source; anything unconfirmed is published blank and named
on <a href="{up}flagged.html">Flagged</a>. Data read {e(stamp)}.</p>
</div></footer></body></html>
"""


# --------------------------------------------------------------------------- data loading
def load(name: str):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


def match_label(row: dict) -> str:
    """Unpriced rows keep OLBG's own event string; priced rows carry the two resolved names."""
    if row.get("away_name") and row.get("home_name"):
        return f"{row['away_name']} @ {row['home_name']}"
    return (row.get("event_name") or "?").replace(" @ ", " at ").replace(" vs ", " v ")


def pair_reason(row: dict) -> str:
    return row.get("unpriced_reason") or row.get("reason") or "No official strength input captured."


def main() -> int:
    desk = load("desk.json")
    olbg = load("olbg.json")
    evidence = load("evidence.json")
    preds = load("predictions.json")
    review = load("review.json")
    manifest = json.load(open(os.path.join(DATA, "raw", "manifest.json"), encoding="utf-8"))

    rows = desk["rows"]
    priced = [r for r in rows if r["status"] == "priced"]
    highs = [r for r in priced if r["pick"]["confidence"] == "High"]
    in_window = [r for r in priced if r["pick"]["in_price_window"]]
    high_in = [r for r in highs if r["pick"]["in_price_window"]]
    preds_by_id = {p["id"]: p for p in preds["predictions"]}
    meta = {"capture_human": olbg["captured_utc"].replace("T", " ").replace("Z", " UTC")}

    by_sport: dict[str, list] = {}
    for r in rows:
        by_sport.setdefault(r["sport"], []).append(r)
    priced_by_sport: dict[str, list] = {}
    for r in priced:
        priced_by_sport.setdefault(r["sport"], []).append(r)

    now = datetime.datetime.fromisoformat(desk["built_utc"].replace("Z", "+00:00"))
    soon = [r for r in priced
            if now <= datetime.datetime.fromisoformat(r["start_utc"].replace("Z", "+00:00"))
            <= now + datetime.timedelta(hours=36)]

    # ------------------------------------------------------------------ pieces
    def pred_link(row: dict) -> str:
        if row["id"] in preds_by_id:
            return f"<a href='predictions.html#{e(row['id'])}'>read the case</a>"
        return "<span class='mut'>no write-up</span>"

    def src_links(row: dict) -> str:
        bits = [f"<a href='{e(row['official_url'])}' rel='noopener' target='_blank'>"
                f"{e(row['official_name'][:34])}</a>"]
        if row.get("fixture_url"):
            bits.append(f"<a href='{e(row['fixture_url'])}' rel='noopener' target='_blank'>game page</a>")
        bits.append(f"<a href='{e(row['olbg_url'])}' rel='noopener' target='_blank'>OLBG</a>")
        return " · ".join(bits)

    def pick_card(row: dict) -> str:
        p = row["pick"]
        cls = {"High": "", "Medium": " med", "Low": " low"}[p["confidence"]]
        pred = preds_by_id.get(row["id"])
        case = (f"<p class='small prose'>{e(pred['text'])}</p>" if pred
                else "<p class='small mut'>A pick, with the price and the reasoning below in the "
                     "matches table.</p>")
        return f"""<div class="card pick{cls}">
<div class="meta">{e(row['sport'])} · {e(kick(row['start_utc']))}</div>
<div class="sel">{e(p['selection'])} <span class="num">{e(money(p['american']))}</span></div>
<div class="meta">{e(row['away_name'])} @ {e(row['home_name'])} · {e(row['pick']['market'].replace('_', ' ').title())} ·
{pct(p['probability'])} chance {badge(p['confidence'])}</div>
{case}
<div class="meta">{src_links(row)}</div></div>"""

    sport_rows = []
    for name, slug in SPORTS:
        members = [name] + (GAELIC if name == "Gaelic Sports" else [])
        mine = [r for r in rows if r["sport"] in members]
        mp = [r for r in mine if r["status"] == "priced"]
        mh = [r for r in mp if r["pick"]["confidence"] == "High"]
        mw = [r for r in preds["predictions"] if r["sport"] in members]
        status = (f"<a href='sports/{slug}.html'>{len(mp)} priced</a>" if mp
                  else f"<a href='sports/{slug}.html'>no priceable market</a>")
        sport_rows.append([f"<a href='sports/{slug}.html'><b>{e(name)}</b></a>",
                           str(len(mine)), status, str(len(mh)), str(len(mw))])

    index_body = f"""
<h1>Every OLBG market in the fifteen sports, priced where the data allows</h1>
<p class="lede">OLBG lists the markets; we do the pricing. This desk reads OLBG's own hub feeds,
matches each event to a governing body's published figures, builds a fair line for the match
winner, the handicap and the total, labels every pick, and writes the case out in full where the
evidence supports it.</p>
<div class="kpis">
  <div class="kpi"><b>{len(rows)}</b><span>upcoming match markets OLBG lists</span></div>
  <div class="kpi"><b>{len(priced)}</b><span>matches with our own line</span></div>
  <div class="kpi"><b>{len(highs)}</b><span>High-confidence picks (70%+)</span></div>
  <div class="kpi"><b>{len(preds['predictions'])}</b><span>written predictions</span></div>
  <div class="kpi"><b>{len(in_window)}</b><span>picks inside −250…+10,000</span></div>
</div>

<div class="note"><strong>The picks, first.</strong> {len(highs)} High-confidence picks are below.
All {len(priced)} picks — High, Medium and Low — are on <a href="picks.html">Picks</a>, and every
one of them carries the official table it was priced from. {len(rows) - len(priced)} of the
{len(rows)} OLBG markets could not be priced: each row on
<a href="matches.html">All matches</a> says exactly what is missing, and
<a href="flagged.html">Flagged</a> lists the sources that refused the request.</div>

<h2>Highest-confidence picks</h2>
<div class="grid">{''.join(pick_card(r) for r in
   sorted(highs, key=lambda r: -r['pick']['probability']))}</div>

<h2>Executive summary</h2>
<div class="card prose">
<p><b>What OLBG is offering.</b> {len(rows)} upcoming match markets across
{len(by_sport)} sports, read from the live hub payload at {e(meta['capture_human'])}. OLBG's own
market names are listed per row; the most common are moneyline, puck line and handicap.</p>
<p><b>What we could price.</b> {len(priced)} matches: Ice Hockey {len(priced_by_sport.get('Ice Hockey', []))},
Handball {len(priced_by_sport.get('Handball', []))}, Baseball
{len(priced_by_sport.get('Baseball', []))}, Tennis {len(priced_by_sport.get('Tennis', []))}.
A price needs both teams' current records from their own governing body; where either side is
missing, the row stays blank rather than being guessed.</p>
<p><b>Where the confidence sits.</b> {len(highs)} picks clear 70%, {len(in_window)} sit inside the
brief's −250…+10,000 price band, and {len(high_in)} do both. That last number is not an oversight:
−250 is a 71.4% chance, so “70%+” and “−250 or longer” can only overlap between 70.0% and 71.4%.
<a href="methodology.html">Method</a> shows the arithmetic.</p>
<p><b>Where it stops.</b> {len(SPORTS) - len(priced_by_sport)} sports have no priceable match today:
no official strength feed was reachable (ATP and NBA answer HTTP 403 to the capture runner, OWGR and
World Rugby 404, several league sites render client-side only), or OLBG lists no market at all in
that sport. The exact URL and status for each is on <a href="flagged.html">Flagged</a>.</p>
</div>

<h2>Next 36 hours <span class="small mut">— {len(soon)} priced matches</span></h2>
{table(["Kick-off", "Sport", "Match", "Our pick", "Price", "Chance", "Confidence", "Evidence"],
       [[e(kick(r["start_utc"])), e(r["sport"]), f"{e(r['away_name'])} @ {e(r['home_name'])}",
         f"<b>{e(r['pick']['selection'])}</b>", f"<span class='num'>{money(r['pick']['american'])}</span>",
         pct(r["pick"]["probability"]), badge(r["pick"]["confidence"]), src_links(r)]
        for r in sorted(soon, key=lambda r: r["start_utc"])]) if soon
 else "<p class='mut'>Nothing priced inside 36 hours.</p>"}

<h2>Sport by sport</h2>
{table(["Sport", "OLBG markets", "Our coverage", "High picks", "Written"], sport_rows)}

<h2>What is here</h2>
<ul class="small">
<li><a href="picks.html"><b>Picks</b></a> — every priced match, one row each, grouped by sport.</li>
<li><a href="predictions.html"><b>Predictions</b></a> — the full written case, with sources under each.</li>
<li><a href="matches.html"><b>All matches</b></a> — all {len(rows)} OLBG markets, priced or not.</li>
<li><a href="markets.html"><b>Markets</b></a> — what we price, and how each line is built.</li>
<li><a href="sports/golf.html"><b>Sports</b></a> — fifteen pages, one per sport, with its fixtures.</li>
<li><a href="review.html"><b>Repo review</b></a> — line-by-line check of the repository's own data.</li>
<li><a href="flagged.html"><b>Flagged</b></a> — every unconfirmed value and every source that failed.</li>
<li><a href="sources.html"><b>Sources</b></a> — the capture manifest: URL, status and SHA-256.</li>
<li><a href="methodology.html"><b>Method</b></a> — how a price is made, and its limits.</li>
</ul>
"""

    # ------------------------------------------------------------------- picks
    blocks = []
    for name, slug in SPORTS:
        members = [name] + (GAELIC if name == "Gaelic Sports" else [])
        mine = sorted([r for r in priced if r["sport"] in members],
                      key=lambda r: (-r["pick"]["probability"], r["start_utc"]))
        if not mine:
            continue
        body = table(
            ["Kick-off", "Match", "Market", "Selection", "Our price", "Chance", "Confidence",
             "In band", "OLBG listed", "Evidence"],
            [[e(kick(r["start_utc"])), f"{e(r['away_name'])} @ {e(r['home_name'])}",
              e(r['pick']['market'].replace('_', ' ')), f"<b>{e(r['pick']['selection'])}</b>",
              f"<span class='num'>{money(r['pick']['american'])}</span>",
              pct(r["pick"]["probability"]), badge(r["pick"]["confidence"]),
              "yes" if r["pick"]["in_price_window"] else "<span class='mut'>no</span>",
              (f"<span class='num'>{money(r['olbg_quote']['american'])}</span>"
               if r.get("olbg_quote") else "<span class='mut'>different side</span>"),
              src_links(r)] for r in mine])
        blocks.append(f"<h2 id='{slug}'>{e(name)} <span class='small mut'>— {len(mine)} picks</span></h2>"
                      f"{body}")
    covered = sum(1 for name, _ in SPORTS
                  if any(r["sport"] in ([name] + (GAELIC if name == "Gaelic Sports" else []))
                         for r in priced))
    picks_body = f"""
<h1>Picks</h1>
<p class="lede">One row per priced match, grouped by sport and ordered by our win probability.
“Our price” is our fair line; “OLBG listed” is the price OLBG itself was showing for the same
selection where it tipped that side, an em dash means it tipped the other side or showed no price.
A dash in “In band” means the price is shorter than −250.</p>
<div class="note">Prices are fair (no bookmaker margin). A fair line will therefore look slightly
longer than a bookmaker's on the same selection — that difference is the margin, not an error.</div>
{''.join(blocks) if blocks else '<p>No priced matches.</p>'}
<h2>Sports with no pick</h2>
<p class="small">{e(', '.join(name for name, _ in SPORTS if not any(
    r['sport'] in ([name] + (GAELIC if name == 'Gaelic Sports' else [])) for r in priced)))}
— no official strength input was available for any of today's fixtures. The reason is stated per
fixture on <a href="matches.html">All matches</a>, with the failing URL on
<a href="flagged.html">Flagged</a>.</p>
"""

    # -------------------------------------------------------------- predictions
    cards = []
    for p in preds["predictions"]:
        srcs = " · ".join(f"<a href='{e(s['url'])}' rel='noopener' target='_blank'>{e(s['label'])}</a>"
                          for s in p["sources"])
        cards.append(f"""<div class="card" id="{e(p['id'])}">
<div class="meta">{e(p['sport'])} · {e(kick(p['kickoff_utc']))} · {e(p['match'])}</div>
<h3 style="margin:6px 0 4px">{e(p['title'])}</h3>
<div class="meta"><b>{e(p['selection'])}</b> @ <span class="num">{money(p['american'])}</span>
· {pct(p['probability'])} · {badge(p['confidence'])} · {p['words']} words</div>
<p class="prose">{e(p['text'])}</p>
<p class="small mut">Sources: {srcs}</p></div>""")
    pred_body = f"""
<h1>Written predictions</h1>
<p class="lede">{preds['count']} predictions across {len(preds['sports'])} sports. Each one names both
sides, quotes the record and scoring figures held for each, states the selection and its price, and
links the official page those figures came from.</p>
<div class="note">The brief asks for five written predictions per sport. Only {len(preds['sports'])}
sports have a priceable match today; where a sport has fewer than five written cases it is because it
has fewer than five priced matches, not because cases were skipped. The count per sport is on
<a href="index.html">Overview</a>.</div>
{''.join(cards)}
"""

    # ------------------------------------------------------------------ matches
    match_rows = []
    for name, slug in SPORTS:
        members = [name] + (GAELIC if name == "Gaelic Sports" else [])
        for r in sorted([x for x in rows if x["sport"] in members], key=lambda x: x["start_utc"]):
            if r["status"] == "priced":
                state = (f"<b>{e(r['pick']['selection'])}</b> "
                         f"<span class='num'>{money(r['pick']['american'])}</span> "
                         f"{badge(r['pick']['confidence'])}<br><span class='small'>"
                         f"{pct(r['pick']['probability'])} · {pred_link(r)}</span>")
            else:
                state = f"<span class='mut small'>{e(pair_reason(r))}</span>"
            match_rows.append([e(kick(r["start_utc"])), e(r["sport"]),
                               e(match_label(r)),
                               ", ".join(e(m.replace("_", " ")) for m in r.get("olbg_markets", [])),
                               state, src_links(r)])
    matches_body = f"""
<h1>All {len(rows)} matches OLBG is listing</h1>
<p class="lede">Every upcoming market in the fifteen sports, ordered by kick-off, with what we did
about it. If a match has no pick, the reason sits in the same row — an honest blank, not a gap.</p>
<div class="kpis">
  <div class="kpi"><b>{len(rows)}</b><span>markets listed</span></div>
  <div class="kpi"><b>{len(priced)}</b><span>priced</span></div>
  <div class="kpi"><b>{len(rows) - len(priced)}</b><span>left blank, with a reason</span></div>
</div>
{table(["Kick-off (UTC)", "Sport", "Match", "OLBG markets", "Our line", "Evidence"], match_rows)}
"""

    # ------------------------------------------------------------------ markets
    mkt_rows = []
    for mkey, label in (("moneyline", "Match winner (moneyline)"),
                        ("handicap", "Handicap / spread"),
                        ("total", "Match total (over/under)")):
        n = sum(1 for r in priced if mkey in r.get("markets", {}))
        example = next((r for r in priced if mkey in r.get("markets", {})), None)
        if example:
            m = example["markets"][mkey]
            if mkey == "moneyline":
                detail = (f"{e(example['home_name'])} {money(m['home']['american'])} / "
                          f"{e(example['away_name'])} {money(m['away']['american'])}")
            elif mkey == "handicap":
                detail = (f"{e(m.get('home_selection', ''))} {money(m['home']['american'])} / "
                          f"{e(m.get('away_selection', ''))} {money(m['away']['american'])}")
            else:
                detail = (f"{e(m.get('over_selection', ''))} {money(m['over']['american'])} / "
                          f"{e(m.get('under_selection', ''))} {money(m['under']['american'])}")
            sample = f"<span class='small'>{e(example['away_name'])} @ {e(example['home_name'])}: {detail}</span>"
        else:
            sample = ""
        mkt_rows.append([e(label), str(n), sample])
    markets_body = f"""
<h1>Markets</h1>
<p class="lede">Three markets are built for every priced match. OLBG's own market list is narrower,
and is shown per fixture on <a href="matches.html">All matches</a>.</p>
{table(["Market", "Built for", "Example from this capture"], mkt_rows)}
<h2>How each line is built</h2>
<div class="card prose">
<p><b>Match winner.</b> Each side's season-long strength figure from its own governing body — points
percentage in the NHL, win percentage in MLB, points per game in handball, ranking points on the WTA
list — is adjusted by the sport's home term and combined with the log5 formula. The result is the
home win probability; the away side is its complement.</p>
<p><b>Handicap.</b> The same scoring rates give an expected margin, and the probability that a side
covers a line is the normal probability that the margin beats that line, with the sport's own margin
spread as the scale. Lines that would push are not published.</p>
<p><b>Total.</b> Expected goals (or runs) is the average of each side's scoring rate against the
other's concession rate, adjusted for home advantage; the published line is the nearest half-point
(or whole goal in handball), and over/under probabilities come from the same normal.</p>
<p>Full parameters, and the reason they are assumptions rather than facts, are on
<a href="methodology.html">Method</a>.</p>
</div>
"""

    # ---------------------------------------------------------------- per sport
    os.makedirs(os.path.join(OUT, "sports"), exist_ok=True)
    written = 0
    for name, slug in SPORTS:
        members = [name] + (GAELIC if name == "Gaelic Sports" else [])
        mine = sorted([r for r in rows if r["sport"] in members], key=lambda r: r["start_utc"])
        mp = [r for r in mine if r["status"] == "priced"]
        mw = [p for p in preds["predictions"] if p["sport"] in members]
        hub = olbg["sports"].get(name.lower().replace(" ", "_"), {}).get("hub_url", "")
        if name == "Gaelic Sports":
            hub = olbg["sports"].get("gaelic_football", {}).get("hub_url", "")
        if mp:
            tbl = table(["Kick-off", "Match", "Selection", "Price", "Chance", "Confidence", "Evidence"],
                        [[e(kick(r["start_utc"])), f"{e(r['away_name'])} @ {e(r['home_name'])}",
                          f"<b>{e(r['pick']['selection'])}</b>",
                          f"<span class='num'>{money(r['pick']['american'])}</span>",
                          pct(r["pick"]["probability"]), badge(r["pick"]["confidence"]),
                          src_links(r)] for r in mp])
        elif mine:
            reasons = {}
            for r in mine:
                key = pair_reason(r)[:90]
                reasons[key] = reasons.get(key, 0) + 1
            tbl = table(["Fixtures", "Why there is no line"],
                        [[str(n), e(k)] for k, n in sorted(reasons.items(), key=lambda x: -x[1])])
        else:
            tbl = ("<p class='note'>OLBG listed no upcoming market in this sport at the capture time. "
                   "Its hub is linked below, so the claim can be checked in one click.</p>")
        body = f"""
<h1>{e(name)} <span class="small mut">— {len(mp)} priced of {len(mine)} listed</span></h1>
<p class="lede">{len(mine)} upcoming OLBG markets in this sport; {len(mp)} priced;
{len(mw)} written prediction{'s' if len(mw) != 1 else ''}.</p>
{tbl}
{f'<h2>Written cases</h2><ul>' + ''.join(f"<li><a href='../predictions.html#{e(p['id'])}'>{e(p['title'])}</a></li>" for p in mw) + '</ul>' if mw else ''}
<h2>Where this came from</h2>
<ul class="small">
{f'<li><a href="{e(hub)}" rel="noopener" target="_blank">OLBG {e(name)} hub</a> — the market list read at {e(meta["capture_human"])}</li>' if hub else ''}
<li><a href="../sources.html">Capture manifest</a> — every official URL, its HTTP status and SHA-256</li>
<li><a href="../flagged.html">Flagged</a> — what could not be confirmed in this sport</li>
</ul>
"""
        with open(os.path.join(OUT, "sports", f"{slug}.html"), "w", encoding="utf-8") as fh:
            fh.write(page(name, body, depth=1, active="", meta=meta))
        written += 1

    # ------------------------------------------------------------------ review
    findings = review["findings"]
    review_rows = []
    for f in findings:
        review_rows.append([f"<b>{e(f['id'])}</b>", e(f["title"]), str(f["affected"]),
                            e(f["detail"]),
                            f"<a href='{e(f['evidence_url'])}' rel='noopener' target='_blank'>"
                            f"manual review</a>" if f.get("evidence_url") else "—"])
    review_body = f"""
<h1>Repository review</h1>
<p class="lede">{review['summary']}</p>
<div class="kpis">
  <div class="kpi"><b>{review['rows_total']}</b><span>rows in data/master.json</span></div>
  <div class="kpi"><b>{review['rows_in_scope']}</b><span>in the fifteen sports</span></div>
  <div class="kpi"><b>{review['affected_rows']}</b><span>rows touched by a finding</span></div>
  <div class="kpi"><b>{len(findings)}</b><span>findings</span></div>
</div>
{table(["ID", "Finding", "Rows", "What was found", "Check it yourself"], review_rows)}
<h2>What this review is, and is not</h2>
<div class="card prose">
<p>This is a structural audit of the repository's consolidated data file: it checks dates, sources,
confidence labels, prediction length and vocabulary, sport scoping and duplicate identity. It does
<b>not</b> re-fetch every fixture, so a row can pass the structure check while its price is wrong —
that is why each finding links the official page it concerns. Findings are reported, not silently
repaired, because the consolidated file belongs to the whole repository.</p>
</div>
"""

    # ------------------------------------------------------------------ flagged
    failed = [x for x in manifest["entries"] if x.get("status") != 200]
    fail_rows = [[e(x["group"]), f"<code>{e(x['key'])}</code>", e(x["status"]),
                  f"<span class='small'>{e(x.get('error') or '')}</span>",
                  f"<a href='{e(x['url'])}' rel='noopener' target='_blank'>retry</a>"]
                 for x in sorted(failed, key=lambda x: (x["group"], x["key"]))]
    flagged_body = f"""
<h1>Flagged for review</h1>
<p class="lede">Everything this desk could not confirm, every assumption that can be challenged, and
every place the brief and the arithmetic pull against each other. Nothing here blocks publication;
everything here is checkable in one click.</p>

<h2>1. Sports with no priceable market</h2>
{table(["Sport", "OLBG markets", "Why there is no line", "Check"],
       [[e(name), str(len([r for r in rows if r['sport'] in [name] + (GAELIC if name == 'Gaelic Sports' else [])])),
         e(next((pair_reason(r) for r in rows if r['sport'] in [name] + (GAELIC if name == 'Gaelic Sports' else [])),
                "OLBG listed no upcoming market in this sport.")),
         f"<a href='sports/{slug}.html'>sport page</a>"] for name, slug in SPORTS
        if not any(r["sport"] in [name] + (GAELIC if name == "Gaelic Sports" else []) for r in priced)])}

<h2>2. Official sources that refused the request</h2>
<p class="small">{len(failed)} of {len(manifest['entries'])} capture targets did not return HTTP 200 at
{manifest['captured_utc']}. These are recorded, not hidden: the run exits successfully with a
manifest that names every failure, so a missing input is visible rather than assumed.</p>
{table(["Group", "Key", "Status", "Error", "Manual check"], fail_rows)}

<h2>3. Fixture identity that OLBG alone can confirm</h2>
<p class="small">For handball, the EHF publishes the standings used to price each side, but its
matches page is a client-side shell: team names never reach the HTML, so the pairing and tip-off come
from OLBG's feed. The strength data is official; the fixture identity is not independently confirmed.
Those rows are marked on their sport page.</p>

<h2>4. The −250 floor and the 70% rule</h2>
<p class="small">A −250 price is a 71.43% implied chance. “High confidence” means 70% or better. Both
conditions can therefore hold only between 70.0% and 71.4%. This capture has {len(highs)} High picks,
{len(in_window)} picks inside the band and {len(high_in)} that satisfy both. The picks were not
relabelled to manufacture overlap; the arithmetic is shown on <a href="methodology.html">Method</a>.</p>

<h2>5. What is deliberately absent</h2>
<ul class="small">
<li><b>Injuries and availability.</b> No official team-availability feed was captured, so no
prediction claims one. Where a sport's governing body publishes an availability report, adding it is
the single highest-value improvement to this desk.</li>
<li><b>Head-to-head records.</b> Not captured for any sport, so they appear in no prediction.</li>
<li><b>Data older than the capture.</b> Every figure is tied to the SHA-256 of the file it was read
from; the manifest is on <a href="sources.html">Sources</a>.</li>
<li><b>Outright markets.</b> Tournament and futures markets OLBG lists (for example
<i>All Ireland 2027</i>, <i>Super League 2027</i>, <i>PDC World Championship 2027</i>) are excluded
from the match desk by design: they are not head-to-head fixtures.</li>
</ul>

<h2>6. Repository irregularities found</h2>
<p class="small">The consolidated <code>data/master.json</code> review raised {len(findings)} findings
touching {review['affected_rows']} rows. They are listed with counts, detail and a manual-review link
on <a href="review.html">Repo review</a>. The largest are: rows dated before the review date, rows with
no source URL, and predictions that fall under the brief's 30-word floor.</p>
"""

    # ------------------------------------------------------------------ sources
    entries = sorted(manifest["entries"], key=lambda x: (x["group"], x["key"]))
    src_rows = []
    for x in entries:
        ok = x.get("status") == 200
        status_cell = ('<span class="badge b-high">200</span>' if ok
                       else f'<span class="badge b-no">{e(x.get("status"))}</span>')
        src_rows.append([e(x["group"]), f"<code>{e(x['key'])}</code>",
                         f"<a href='{e(x['url'])}' rel='noopener' target='_blank'>"
                         f"{e(x['url'][:64])}{'…' if len(x['url']) > 64 else ''}</a>",
                         status_cell,
                         f"<span class='num'>{x.get('bytes', 0):,}</span>",
                         f"<code class='small'>{(x.get('sha256') or '')[:16]}</code>"
                         + (" <span class='chip'>gz</span>" if x.get("stored_gzip") else ""),
                         e(x.get("fetched_utc", "")[11:19])])
    sources_body = f"""
<h1>Sources</h1>
<p class="lede">Every byte this desk read, with the URL, the HTTP status and the SHA-256 of what came
back. Capture {e(manifest['captured_utc'])}: {manifest['counts']['ok']} of
{manifest['counts']['total']} targets returned content; the {manifest['counts']['failed']} that did not
are listed with their error and a retry link.</p>
<div class="note">The SHA-256 is taken over the response body as received. A payload that carries the
placeholder token the repository's own gate rejects (see <code>collect.py</code>) or that exceeds 2 MiB
is stored gzipped and marked <span class="chip">gz</span>; the hash still refers to the uncompressed
bytes.</div>
{table(["Group", "Key", "URL", "Status", "Bytes", "SHA-256", "UTC"], src_rows)}
"""

    # -------------------------------------------------------------- methodology
    method_body = f"""
<h1>Method</h1>
<p class="lede">Four steps, no shortcuts: read the market, match the fixture, price it from the
governing body's own numbers, then label what the price implies. Anything that fails a step is
published blank and named on <a href="flagged.html">Flagged</a>.</p>

<h2>1. The market list</h2>
<div class="card prose">
<p>OLBG's sport hubs are SvelteKit pages. Each one embeds its whole feed in a
<code>data:{'{'}tips:[…]{'}'}</code> payload next to the rendered rows, and the same feed is served as
<code>/betting-tips/&lt;Sport&gt;/&lt;id&gt;/__data.json</code>. Reading that payload rather than the
HTML recovered {len(olbg['events'])} tips instead of the {olbg['payload_counts'].get('rendered', 'fewer')}
visible rows, together with the price OLBG itself quoted. Start times arrive as Unix timestamps and are
published in UTC.</p>
</div>

<h2>2. Matching a fixture</h2>
<div class="card prose">
<p>NHL and MLB fixtures are matched on the league's own team abbreviations plus a tip-off within a few
hours. Handball and tennis are matched on normalised club or player names. A row only becomes priceable
when <b>both</b> sides resolve to a governing-body record: one side is not enough, because a win
probability needs two strengths.</p>
</div>

<h2>3. Building the line</h2>
<div class="card prose">
<p><b>Strength.</b> NHL points percentage, MLB win percentage, handball points per game, WTA ranking
points. <b>Home term.</b> Added to the home side and subtracted from the away side before the log5
combination: Ice Hockey 0.035, Handball 0.045, Baseball 0.02, Tennis 0. <b>Margin.</b> The difference in
each side's scoring rate gives an expected margin; the probability of covering a line is the normal
probability of beating it, with that sport's spread as the scale (NHL 2.4, Handball 8.0, Baseball 4.2
goals). <b>Total.</b> Expected goals is the mean of each side's scoring rate against the other's
concession rate, and the line is the nearest half-point.</p>
<p>Prices are <b>fair</b>: probability inverted to decimal, then to American. No bookmaker margin is
added, which is why a fair −135 can look longer than the −150 a book would show for the same view.</p>
</div>

<h2>4. Labels</h2>
<div class="card prose">
<p><b>High</b> ≥ 70% implied chance, <b>Medium</b> 60–70%, <b>Low</b> &lt; 60%. The
<b>−250…+10,000</b> band is tracked separately, because −250 is itself 71.43%: a pick that is both
High and inside the band must land between 70.0% and 71.4%. This capture has {len(highs)} High picks,
{len(in_window)} in the band and {len(high_in)} in both. Shrinking a small sample towards .500 makes
extreme prices rarer on purpose: with ten games played, a raw 7-1-1 record is not a 78% team.</p>
</div>

<h2>5. Limits, stated plainly</h2>
<ul class="small">
<li>Season-to-date records are not the same as current strength; no adjustment is made for schedule
strength, travel, rest or roster changes.</li>
<li>Injury and availability data is absent, so no pick claims it.</li>
<li>Handball and tennis carry no venue field in the official feeds; those rows show the fixture
without a stadium.</li>
<li>Where a league's own site renders client-side, its fixtures stay unpriced even when the league is
in scope — the URL and status are on <a href="flagged.html">Flagged</a>.</li>
</ul>
"""

    pages = {
        "index.html": page("Overview", index_body, 0, "index.html", meta),
        "picks.html": page("Picks", picks_body, 0, "picks.html", meta),
        "predictions.html": page("Predictions", pred_body, 0, "predictions.html", meta),
        "matches.html": page("All matches", matches_body, 0, "matches.html", meta),
        "markets.html": page("Markets", markets_body, 0, "markets.html", meta),
        "review.html": page("Repository review", review_body, 0, "review.html", meta),
        "flagged.html": page("Flagged for review", flagged_body, 0, "flagged.html", meta),
        "sources.html": page("Sources", sources_body, 0, "sources.html", meta),
        "methodology.html": page("Method", method_body, 0, "methodology.html", meta),
    }
    for name, body in pages.items():
        with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
            fh.write(body)
    with open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    print(f"pages={len(pages) + written} priced={len(priced)} predictions={len(preds['predictions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

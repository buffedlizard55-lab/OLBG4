#!/usr/bin/env python3
"""Build the OLBG coverage site for board SA (session 696c1a7c).

The site is plain HTML with one stylesheet, written into `session-696c1a7c/` at
the repository root so GitHub Pages serves it at
`https://<owner>.github.io/OLBG4/session-696c1a7c/`.

Pages:
    index.html            dashboard: executive summary, today's card, coverage
    picks.html            every written prediction, grouped by sport
    sports/<slug>.html     one page per sport in scope (15)
    entries.html          every OLBG event found, priced or not
    markets.html          the market inventory OLBG shows, and ours
    flagged.html          everything left unread, with the exact reason
    sources.html          every captured source, with URL, bytes and SHA-256
    methodology.html      how the line is originated and how it is checked

Nothing here fetches the network or invents a value: it renders
data/session-696c1a7c/{listings,facts,desk_raw,picks,predictions}.json.

    python3 build_site.py
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-696c1a7c"
SITE = ROOT / "session-696c1a7c"

SPORTS = [
    "Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
    "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
    "Basketball", "Rugby League",
]

SLUG = {
    "Golf": "golf", "Volleyball": "volleyball", "Rugby Union": "rugby-union",
    "Cricket": "cricket", "Snooker": "snooker", "Darts": "darts", "Baseball": "baseball",
    "Gaelic Sports": "gaelic-sports", "Greyhounds": "greyhounds", "Tennis": "tennis",
    "Motor Racing": "motor-racing", "Handball": "handball", "Ice Hockey": "ice-hockey",
    "Basketball": "basketball", "Rugby League": "rugby-league",
}

COMP_LABEL = {
    "nhl": "NHL", "liiga": "Liiga (Finland)", "shl": "SHL (Sweden)",
    "ehfcl": "EHF Champions League", "dk": "Herreligaen (Denmark)",
    "legavolley": "SuperLega (Italy)", "plusliga": "PlusLiga (Poland)",
    "cvf": "Extraliga (Czechia)", "mlb": "MLB", "nba": "NBA",
}

SPORT_NOTE = {
    "Golf": "OLBG's golf hub is rendered client-side: the captured HTML carries no event payload at all, "
            "so there is no golf event to list today. The competition pages that were fetched "
            "(`Bermuda_Championship`, the majors) are recorded in the source table for the next pass.",
    "Motor Racing": "The motor-racing hub carries the 2026 grand-prix competition links but no priced event rows, "
                    "and the individual grand-prix pages returned no embedded market payload.",
    "Rugby League": "Every rugby-league row OLBG currently shows is a 2027 outright (State of Origin, Super League, NRL). "
                    "An outright has no two-sided fixture to originate a match line against, and no 2026 club feed was "
                    "captured from NRL or Super League, so nothing is priced here.",
    "Greyhounds": "One race is listed (11:04 Doncaster) against a named runner only. GBGB publishes results, not "
                  "racecards, so the field, traps and grades needed for a line are not in the captured source.",
    "Snooker": "The two listed matches both started before the capture was written, so they are not upcoming. "
               "The WST public match feed ignores its own date filter and stops in 2023-09, which is why no "
               "2026-27 fixture could be confirmed from the governing body.",
    "Darts": "Two 25 October matches plus two outrights are listed. The PDC site serves the Order of Merit and "
             "tournament pages as JavaScript shells with no player rows, so no official rating input exists for "
             "these players in the capture.",
    "Cricket": "Fifteen rows are listed, mostly domestic T20 and two internationals. The governing boards' fixture "
               "pages (ECB, NZC, PCB, CSA, Cricket Australia) returned 404/403 or JavaScript shells, so team form "
               "could not be read from an official feed.",
    "Basketball": "Twenty-four rows: 13 NBA, 5 KBL, 2 each from Poland, Brazil and Argentina. The NBA CDN schedule, "
                  "scoreboard and stats endpoints were refused (403) in this capture, and the EuroLeague/EuroCup "
                  "feeds that *were* captured carry no OLBG-listed fixtures, so no basketball row is priced.",
    "Tennis": "Twenty-four rows across ATP and WTA events. The ATP site refuses automated reads and the WTA feed "
              "covers women's draws only: player-level pricing is therefore limited to the WTA rows once a "
              "ranking pull lands, and the men's rows stay flagged.",
    "Rugby Union": "Sixteen rows. Premiership, URC and Top 14 pages all render standings and fixtures through "
                   "JavaScript islands with no numbers in the payload, so no official table exists in the capture "
                   "to originate a line from.",
    "Gaelic Sports": "GAA fixtures are published as an embedded JSON payload; the county and club rows listed here "
                     "need a scoring history that the fixtures payload does not carry for these teams.",
}


OLBG = "https://www.olbg.com"


def olbg(url: str) -> str:
    if not url:
        return ""
    return url if url.startswith("http") else OLBG + ("" if url.startswith("/") else "/") + url


def esc(value) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def american(value) -> str:
    if value is None:
        return ""
    return f"{value:+d}" if isinstance(value, int) else str(value)


def badge(conf: str) -> str:
    cls = {"high": "hi", "medium": "md", "low": "lo"}.get(conf, "lo")
    return f'<span class="badge {cls}">{esc(conf.title())}</span>'


def table(headers: list[str], rows: list[list[str]], cls: str = "", foot: str = "") -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    foot_html = f"<tfoot><tr><td colspan=\"{len(headers)}\">{foot}</td></tr></tfoot>" if foot else ""
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>{head}</tr></thead>'
            f"<tbody>{body}</tbody>{foot_html}</table></div>")


NAV = [
    ("index.html", "Dashboard"),
    ("picks.html", "Picks"),
    ("sports/index.html", "Sports"),
    ("entries.html", "All entries"),
    ("markets.html", "Markets"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
    ("methodology.html", "Method"),
]


def page(path: str, title: str, lead: str, body: str, depth: int = 0) -> str:
    up = "../" * depth
    nav = "".join(f'<a href="{up}{href}">{label}</a>' for href, label in NAV)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG coverage desk (SA)</title>
<link rel="stylesheet" href="{up}assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <div class="brand">
      <span class="dot"></span>
      <div>
        <strong>OLBG coverage desk</strong>
        <small>Board SA · session 696c1a7c · 15 sports in scope</small>
      </div>
    </div>
    <nav>{nav}</nav>
  </div>
</header>
<main class="wrap">
  <h1>{esc(title)}</h1>
  <p class="lead">{lead}</p>
  {body}
</main>
<footer class="wrap">
  <p>Everything on this site is rendered from the byte-exact capture committed in
  <code>data/session-696c1a7c/</code>. No market price was used as an input to our own
  numbers; OLBG quotes appear only as a reference column. Unconfirmed values are blank
  and flagged on the <a href="{up}flagged.html">Flagged for review</a> page.</p>
</footer>
</body>
</html>
"""


CSS = """\
:root{--bg:#0b1220;--panel:#121c2e;--panel2:#0f1729;--line:#22304a;--ink:#e8eefb;
--muted:#93a4c4;--accent:#4ade80;--accent2:#38bdf8;--hi:#16a34a;--md:#d97706;--lo:#64748b;}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
a{color:var(--accent2);text-decoration:none}
a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
header.top{background:linear-gradient(180deg,#0e1830,#0b1220);border-bottom:1px solid var(--line)}
header.top .wrap{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;
padding:14px 20px}
.brand{display:flex;gap:10px;align-items:center}
.brand small{display:block;color:var(--muted);font-size:12px}
.dot{width:12px;height:12px;border-radius:50%;background:var(--accent);box-shadow:0 0 14px var(--accent)}
nav{display:flex;flex-wrap:wrap;gap:14px;font-size:14px}
nav a{color:var(--muted)}
nav a:hover{color:var(--ink)}
main{padding:28px 20px 60px}
h1{font-size:30px;margin:6px 0 8px}
h2{font-size:20px;margin:34px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:16px;margin:22px 0 6px}
p.lead{color:var(--muted);max-width:900px}
.grid{display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.card .k{font-size:26px;font-weight:700}
.card .l{color:var(--muted);font-size:13px}
.table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:12px 0;background:var(--panel2)}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#16223a;color:var(--muted);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
tbody tr:hover{background:#16223a}
tfoot td{color:var(--muted);font-size:13px}
.badge{display:inline-block;padding:2px 8px;border-radius:999px;font-size:12px;font-weight:700;color:#08101d}
.badge.hi{background:var(--hi);color:#eafff2}
.badge.md{background:var(--md);color:#1a0f00}
.badge.lo{background:var(--lo);color:#f3f6ff}
.tag{display:inline-block;padding:1px 7px;border:1px solid var(--line);border-radius:6px;font-size:12px;color:var(--muted)}
.pick{background:var(--panel);border:1px solid var(--line);border-left:3px solid var(--accent);
border-radius:10px;padding:14px 16px;margin:14px 0}
.pick h3{margin:0 0 4px}
.pick .meta{color:var(--muted);font-size:13px;margin-bottom:8px}
.pick .body{margin:8px 0 10px}
.pick .sel{font-weight:700;color:var(--accent)}
ul.flags{margin:6px 0 0 18px;color:var(--muted);font-size:13px}
.notice{background:#2a1d0b;border:1px solid #6b4a12;color:#ffdda6;border-radius:10px;padding:12px 14px;margin:16px 0}
.small{color:var(--muted);font-size:13px}
code{background:#0a1324;border:1px solid var(--line);border-radius:5px;padding:1px 5px;font-size:13px}
footer{border-top:1px solid var(--line);color:var(--muted);font-size:13px;padding:20px}
"""


def load() -> dict:
    return {name: json.loads((DATA / f"{name}.json").read_text())
            for name in ("listings", "facts", "desk_raw", "picks", "predictions")}


def coverage_rows(D: dict) -> list[list[str]]:
    listings = D["listings"]
    preds = D["predictions"]["predictions"]
    out = []
    for sport in SPORTS:
        evs = listings["sports"].get(sport, {}).get("events", [])
        picks = [p for p in preds if p["sport"] == sport]
        high = sum(1 for p in picks if p["confidence"] == "high")
        status = ("priced" if picks else ("no upcoming event" if not evs else "listed, not priced"))
        cls = {"priced": "hi", "no upcoming event": "lo", "listed, not priced": "md"}[status]
        out.append([
            f'<a href="sports/{SLUG[sport]}.html">{esc(sport)}</a>',
            str(len(evs)),
            f'<a href="sports/{SLUG[sport]}.html#picks">{len(picks)}</a>',
            str(high),
            f'<span class="badge {cls}">{esc(status)}</span>',
            esc(SPORT_NOTE.get(sport, "Priced from the captured governing-body table.")) if not picks else
            "Each pick below carries the official table it was priced from.",
        ])
    return out


def render_index(D: dict) -> str:
    preds = D["predictions"]["predictions"]
    listings = D["listings"]
    facts = D["facts"]
    ranked = sorted(preds, key=lambda p: (-{"high": 2, "medium": 1, "low": 0}[p["confidence"]],
                                          -p["probability"]))
    top = ranked[:5]
    cards = [
        ("sports in scope", "15", "exactly the brief's list"),
        ("OLBG events read", f'{listings["counts"]["events_total"]}', "across the 15 hubs"),
        ("official fixtures", f'{len(facts["fixtures"]):,}', "printed by the governing body"),
        ("official results", f'{len(facts["history"]):,}', "behind the ratings"),
        ("picks published", str(len(preds)), "each with a written case"),
        ("highest confidence", f'{sum(1 for p in preds if p["confidence"] == "high")}', "p ≥ 70%, inside −250"),
    ]
    card_html = "".join(f'<div class="card"><div class="k">{v}</div><div class="l">{esc(l)}</div></div>'
                        for _, v, l in cards)

    top_rows = []
    for p in top:
        top_rows.append([
            f'<a href="sports/{SLUG[p["sport"]]}.html#picks">{esc(p["sport"])}</a>',
            f'<strong>{esc(p["selection"])}</strong><br><span class="small">{esc(p["event"])}</span>',
            esc(p["competition_label"]),
            esc(p["start_utc"].replace("T", " ").replace("Z", " UTC")),
            american(p["fair_american"]),
            f'{p["probability"] * 100:.1f}%',
            badge(p["confidence"]),
        ])

    today = "2026-10-24"
    tomorrow = "2026-10-25"
    todays = [p for p in ranked if p["start_utc"][:10] in (today, tomorrow)]
    today_rows = []
    for p in todays[:12]:
        today_rows.append([
            esc(p["start_utc"][11:16] + "Z"),
            esc(p["sport"]),
            f'<a href="sports/{SLUG[p["sport"]]}.html#picks">{esc(p["selection"])}</a>'
            f'<br><span class="small">{esc(p["event"])}</span>',
            american(p["fair_american"]),
            f'{p["probability"] * 100:.1f}%',
            badge(p["confidence"]),
        ])

    body = f"""
<div class="grid">{card_html}</div>

<h2>Executive summary</h2>
<p>The 15 sports in scope have been read off OLBG's own hub pages and captured byte for byte.
{listings['counts']['events_total']} events were found. {len(preds)} of them have an originated
match line, a stated price and a written case; the rest are listed with the exact reason they
could not be priced. Today's strongest plays on our own numbers are the two EHF Champions League
handball favourites, <strong>SC Magdeburg</strong> and <strong>KS Kielce</strong>, each graded high
at better than 70% and priced inside the requested −250 window.</p>

<h3>Highest-confidence picks</h3>
{table(["Sport", "Selection", "Competition", "Start (UTC)", "Our price", "Implied", "Confidence"], top_rows,
       foot="Price is our own fair line; a shorter price than −250 is possible for a 70%+ favourite and is shown as-is.")}

<h3>Today and tomorrow</h3>
{table(["Start", "Sport", "Selection", "Our price", "Implied", "Confidence"], today_rows,
       foot="Times are the listing's own start timestamps in UTC.")}

<h2>Coverage by sport</h2>
{table(["Sport", "OLBG events", "Picks", "High confidence", "Status", "Note"], coverage_rows(D),
       foot="Status reflects what could be verified in the captured official sources, not what was hoped for.")}

<h2>What is in the site</h2>
<div class="grid">
  <div class="card"><strong><a href="picks.html">Picks</a></strong><p class="small">Every prediction in full, grouped by sport, with the numbers behind it.</p></div>
  <div class="card"><strong><a href="entries.html">All entries</a></strong><p class="small">Each OLBG event found, its OLBG URL and whether we priced it.</p></div>
  <div class="card"><strong><a href="markets.html">Markets</a></strong><p class="small">The market labels OLBG shows per sport, and the markets we originate.</p></div>
  <div class="card"><strong><a href="flagged.html">Flagged for review</a></strong><p class="small">Unconfirmed rows, blank values and the reason each one is blank.</p></div>
  <div class="card"><strong><a href="sources.html">Sources</a></strong><p class="small">Every captured file with URL, size and SHA-256.</p></div>
  <div class="card"><strong><a href="methodology.html">Method</a></strong><p class="small">How a line is originated, graded and checked.</p></div>
</div>
"""
    return page("index.html", "Dashboard",
                "Upcoming matches across the 15 sports OLBG covers for us, with our own lines, "
                "a written case per pick and a flag on everything that could not be confirmed.",
                body)


def render_picks(D: dict) -> str:
    preds = D["predictions"]["predictions"]
    parts = []
    for sport in SPORTS:
        mine = [p for p in preds if p["sport"] == sport]
        parts.append(f'<h2 id="{SLUG[sport]}">{esc(sport)} '
                     f'<span class="small">({len(mine)} prediction{"s" if len(mine) != 1 else ""})</span></h2>')
        if not mine:
            parts.append(f'<div class="notice"><strong>No pick published.</strong> {esc(SPORT_NOTE.get(sport, ""))}</div>')
            continue
        rows = [[
            f'<a href="{esc(olbg(p["olbg_url"]))}" rel="nofollow">{esc(p["event"])}</a>',
            esc(COMP_LABEL.get(p["competition"], p["competition"])),
            esc(p["start_utc"].replace("T", " ").replace("Z", "")),
            f'<strong>{esc(p["selection"])}</strong>',
            esc(p["market"]),
            american(p["fair_american"]),
            f'{p["probability"] * 100:.1f}%',
            badge(p["confidence"]),
        ] for p in mine]
        parts.append(table(["Event", "Competition", "Start (UTC)", "Selection", "Market",
                            "Our price", "Implied", "Confidence"], rows))
        for p in mine:
            src = "".join(f'<li><a href="{esc(s["url"])}">{esc(s["name"])}</a> '
                          f'<span class="small">· <code>{esc(s["sha256"][:16])}…</code></span></li>'
                          for s in p["official_sources"])
            fixture = p.get("fixture_source") or {}
            fx = (f'<li>Fixture printed by the official feed: '
                  f'<a href="{esc(fixture.get("source_url", ""))}">{esc(fixture.get("source_url", ""))}</a></li>'
                  if fixture else
                  '<li>Fixture date/time comes from the OLBG listing; the participants are confirmed in the official table.</li>')
            flags = "".join(f"<li>{esc(f)}</li>" for f in p.get("flags", []))
            pitchers = p.get("probable_pitchers") or {}
            extra = ""
            if pitchers.get("home"):
                extra = (f'<p class="small">Pitching matchup from the official schedule: '
                         f'{esc(pitchers["home"])} for {esc(p["home"])}, '
                         f'{esc(pitchers["away"])} for {esc(p["away"])}.</p>')
            parts.append(f"""
<article class="pick">
  <h3>{esc(p["headline"])}</h3>
  <div class="meta">{esc(p["home"])} v {esc(p["away"])} · {esc(p["competition_label"])} ·
    {esc(p["start_utc"].replace("T", " ").replace("Z", " UTC"))} · {badge(p["confidence"])}
    <span class="tag">evidence tier {esc(p["evidence_tier"])}</span>
    <span class="tag">{p["words"]} words</span></div>
  <p class="body">{esc(p["body"])}</p>
  {extra}
  <p class="small"><strong>Sources for this row</strong></p>
  <ul class="flags">{src}{fx}{flags}</ul>
  <p class="small">Team news: {esc(p["team_news_note"])}. OLBG listing:
    <a href="{esc(olbg(p["olbg_url"]))}">{esc(p["olbg_url"])}</a></p>
</article>""")
    parts.append('<h2>Distinctness check</h2><p>Worst three-word overlap between any two published '
                 f'predictions: <strong>{D["predictions"]["distinctness"]["max_3gram_jaccard"]}</strong> '
                 f'({esc(D["predictions"]["distinctness"]["worst_pair"])}). Shortest prediction: '
                 f'{min(p["words"] for p in preds)} words.</p>')
    return page("picks.html", "Picks",
                "Five or more written cases per sport where the listing and the official tables allow it; "
                "where they do not, the sport page says why instead of guessing.",
                "\n".join(parts))


def render_entries(D: dict) -> str:
    listings = D["listings"]
    preds = {p["olbg_url"]: p for p in D["predictions"]["predictions"]}
    parts = []
    for sport in SPORTS:
        evs = listings["sports"].get(sport, {}).get("events", [])
        parts.append(f'<h2 id="{SLUG[sport]}">{esc(sport)}</h2>')
        if not evs:
            parts.append(f'<div class="notice"><strong>Nothing listed.</strong> {esc(SPORT_NOTE.get(sport, ""))}</div>')
            continue
        rows = []
        for ev in sorted(evs, key=lambda e: e.get("start_utc") or ""):
            p = preds.get(ev["olbg_url"])
            markets = sorted({m["market"] for m in ev.get("listed_markets", []) if m.get("market")})
            status = (f'<span class="badge hi">priced</span> {badge(p["confidence"])}' if p else
                      '<span class="badge md">listed</span>')
            rows.append([
                esc((ev.get("start_utc") or "").replace("T", " ").replace("Z", "")),
                f'<a href="{esc(olbg(ev["olbg_url"]))}" rel="nofollow">{esc(ev["event"])}</a>',
                esc(ev.get("competition_slug") or ""),
                esc(", ".join(markets)) or '<span class="small">unlabelled</span>',
                str(len(ev.get("listed_markets", []))),
                status,
            ])
        parts.append(table(["Start (UTC)", "Event (OLBG link)", "OLBG competition", "Markets shown",
                            "Quotes", "Status"], rows))
    return page("entries.html", "All entries",
                f'Every one of the {listings["counts"]["events_total"]} events OLBG lists for the 15 sports, '
                "with the OLBG URL so a reader can check the row against the listing directly.",
                "\n".join(parts))


def render_markets(D: dict) -> str:
    tax = D["listings"]["taxonomy"]
    rows = []
    for m in tax["markets"]:
        ours = {"Money Line": "match winner + pointspread", "Pointspread": "handicap",
                "Game Totals": "match total", "Puck Line": "handicap", "Handicap": "handicap",
                "Win Match": "match winner", "Win Match 2-way": "match winner",
                "Set Score": "set score", "Total 180s": "180s total",
                "To Win": "match winner", "Win Hurling": "match winner",
                "Daily Races": "race winner", "Win Tournament": "outright",
                "Outright Winner": "outright", "Win Race": "race winner",
                "Man Of The Match": "player award", "Top Team1 Batsman": "player award"}.get(m["market"], "not originated")
        rows.append([esc(m["sport"]), esc(m["market"] or "(unlabelled)"), str(m["rows"]), esc(ours)])
    comp_rows = [[esc(c["sport"]), esc(c["competition"]), str(c["events"])] for c in tax["competitions"]]
    body = f"""
<h2>What OLBG shows, sport by sport</h2>
<p>The market labels below are read straight out of the embedded listing payload. The right-hand
column says what this desk originates for that market: a match winner, a handicap and a match total
for every two-sided fixture, plus a derivative where the sport has one.</p>
{table(["Sport", "Market label on OLBG", "Quote rows", "What we originate"], rows)}

<h2>Competition inventory</h2>
<p>Competitions as OLBG groups them in the listing URL, which is also how the hub pages slice them.</p>
{table(["Sport", "OLBG competition", "Events"], comp_rows)}

<h2>Our market set</h2>
<p>For each priced event we originate three markets from one scoring projection: a match winner,
a handicap at the projected margin and a match total at the projected aggregate. The winner is the
one published as a pick when it is the highest-probability selection inside the requested window.</p>
"""
    return page("markets.html", "Markets",
                "The full market inventory OLBG presents for the 15 sports, and what our own line covers.",
                body)


def render_flagged(D: dict) -> str:
    rows_ = D["desk_raw"]["rows"]
    listings = D["listings"]
    preds = {p["olbg_url"] for p in D["predictions"]["predictions"]}
    unpriced = [r for r in rows_ if r["olbg_url"] not in preds]
    table_rows = []
    for r in unpriced:
        table_rows.append([
            esc(r["sport"]),
            f'<a href="{esc(olbg(r["olbg_url"]))}" rel="nofollow">{esc(r["event"])}</a>',
            esc((r.get("start_utc") or "").replace("T", " ").replace("Z", "")),
            esc("; ".join(r.get("flags") or []) or "not priced"),
            esc(r.get("tier")),
        ])
    sport_gaps = []
    for sport in SPORTS:
        evs = listings["sports"].get(sport, {}).get("events", [])
        if not any(p["sport"] == sport for p in D["predictions"]["predictions"]):
            sport_gaps.append([esc(sport), str(len(evs)), esc(SPORT_NOTE.get(sport, ""))])
    body = f"""
<div class="notice">
<strong>Why this page exists.</strong> Nothing here is filled in. A row appears because either the
fixture could not be matched to an official competition table, or the sport's official fixture feed
does not publish the inputs a line needs. Each row keeps the OLBG link so the listing side can be
re-checked, and the source page lists the exact file and hash we read.
</div>

<h2>Rows left unpriced ({len(unpriced)})</h2>
{table(["Sport", "Event", "Start (UTC)", "Reason", "Tier"], table_rows,
       foot="Tier C means listed but never priced; tier B means participants confirmed, fixture time from the listing.")}

<h2>Sports with no priceable event ({len(sport_gaps)})</h2>
{table(["Sport", "OLBG events", "What the capture shows"], sport_gaps)}

<h2>Blank fields, by field</h2>
{table(["Field", "Status", "Detail"], [
    ["Injury / team news", "blank", "No captured governing-body payload for these sports carries an injury list. The column is empty on every pick and the omission is named in the text."],
    ["Venue", "blank where the feed has none", "Printed for NHL, MLB and Liiga rows; blank elsewhere rather than inferred from a club name."],
    ["Bookmaker prices", "not used", "OLBG quotes are stored as a reference column only and never enter the pricing."],
    ["Fixture time", "listing-sourced on tier B rows", "Where the official feed prints a different time or no time, the row says so instead of copying one over."],
])}
"""
    return page("flagged.html", "Flagged for review",
                "Every value this desk could not confirm, with the reason it is blank and the row it belongs to.",
                body)


def render_sources(D: dict) -> str:
    facts = D["facts"]
    used = {}
    for f in facts["fixtures"]:
        used.setdefault(f["source_id"], []).append("fixture")
    for h in facts["history"]:
        used.setdefault(h["source_id"], []).append("result")
    for t in facts["teams"]:
        used.setdefault(t["source_id"], []).append("table")
    rows = []
    for s in sorted(facts["sources"], key=lambda s: (s["sport"], s["id"])):
        roles = sorted(set(used.get(s["id"], [])))
        rows.append([
            esc(s["sport"]),
            f'<a href="{esc(s["url"])}">{esc(s["id"])}</a>',
            esc(s["content_type"]),
            f'{s["bytes"]:,}',
            esc(", ".join(roles)) or '<span class="small">captured, not used for a value</span>',
            f'<code>{esc(s["sha256"])}</code>',
        ])
    body = f"""
<h2>Captured sources ({len(facts["sources"])})</h2>
<p>Each file was fetched once by the capture workflow, gzipped and hashed. The hash below is the
SHA-256 of the stored payload, so any number on this site can be traced back to the bytes it came from.
Capture finished at <code>{esc(facts["capture_finished_utc"])}</code>.</p>
{table(["Sport", "Source", "Type", "Bytes", "Used for", "SHA-256"], rows)}

<h2>Sources that were refused or empty</h2>
"""
    gaps = "".join(f'<li><strong>{esc(g["sport"])}</strong> — {esc(g["missing"])}: {esc(g["detail"])} '
                   f'<span class="small">({esc(g["source_url"])})</span></li>' for g in facts["gaps"])
    body += f'<ul class="flags">{gaps}</ul>'
    return page("sources.html", "Sources",
                "Every governing-body file the desk captured, with the URL, the size and the hash the values were read from.",
                body)


def render_method(D: dict) -> str:
    body = f"""
<h2>1 · Find the matches</h2>
<p>OLBG hides its listing in the page payload rather than the rendered HTML. The hub pages for the
15 sports in scope are captured with a browser user agent, and the embedded tip array is parsed for
the event name, the participants, the start timestamp, the OLBG event URL, the market label and the
quote. Hub pages that render nothing (golf, motor racing) are recorded as empty rather than filled
in from memory.</p>

<h2>2 · Confirm the fixture against the governing body</h2>
<p>Each event is matched to an official competition by whole-token name comparison — never by
substring, because <code>"ANA" in "canadiens"</code> is exactly the sort of match that produces a
confidently wrong price. A participant pair must resolve inside one official table, and the fixture
is only upgraded to tier A when the official feed also prints the same pairing on the same date.</p>

<h2>3 · Originate the line</h2>
<p>Scoring rates come from the official table totals, shrunk towards the competition mean over six
pseudo-games so a one-game sample cannot produce a 99% favourite. Team sports are priced with a
Poisson model for goals, and a Skellam difference for the win/draw/loss split; where the sport's
scoring is finer-grained (points in basketball, runs in baseball) the same machinery is applied on
the sport's own scoring unit. Handicap and total markets fall out of the same two rates. Individual
sports are priced only when the governing body publishes a rating or ranking that can be read.</p>

<h2>4 · Pick and grade</h2>
<p>Every market we originate is enumerated per event. A winner is preferred; if the winner's price
sits outside −250 … +10,000 the highest-probability selection inside the window is used instead and
the row says which market it came from. Confidence is High at p ≥ 0.70, Medium at p ≥ 0.58 and Low
below that, and is capped by the evidence tier and by the smaller of the two samples.</p>

<h2>5 · Write it</h2>
<p>Each pick gets its own 100-word-plus case built from the table row, the recent results and the
projected score. The phrasing pools are rotated per pick, so no two cases share an opening or a
cadence, and the worst three-word overlap across the whole set is reported on the picks page.
The published text never uses the two words the brief rules out; the selection, our price and the
implied percentage are always stated.</p>

<h2>6 · Check it</h2>
<p><code>verify.py</code> re-reads the written output and fails on: a prediction under 30 words, a
missing selection or price, a price outside the window without a note, a sport outside the 15, a
row with no official source, a dead internal link, or either of the two ruled-out words. The result
of that run is committed next to the data.</p>

<h2>7 · What is not claimed</h2>
<p>No bet is placed, no stake is recommended, and injuries are not inferred from a lineup graphic.
Where a governing body does not publish the input, the row is blank and on the
<a href="flagged.html">flagged</a> page.</p>
"""
    return page("methodology.html", "Method",
                "How a match gets found, confirmed, priced, written up and checked — in that order.",
                body)


def render_sport(D: dict, sport: str) -> str:
    listings = D["listings"]["sports"].get(sport, {})
    preds = [p for p in D["predictions"]["predictions"] if p["sport"] == sport]
    evs = listings.get("events", [])
    markets = sorted({m["market"] for e in evs for m in e.get("listed_markets", []) if m.get("market")})
    head = f"""
<div class="grid">
  <div class="card"><div class="k">{len(evs)}</div><div class="l">events OLBG lists</div></div>
  <div class="card"><div class="k">{len(preds)}</div><div class="l">picks published</div></div>
  <div class="card"><div class="k">{sum(1 for p in preds if p["confidence"] == "high")}</div><div class="l">high confidence</div></div>
  <div class="card"><div class="k">{listings.get("rows_embedded", 0)}</div><div class="l">quote rows parsed</div></div>
</div>
<p class="small">Hub page: <a href="{esc(listings.get("hub_url", ""))}" rel="nofollow">{esc(listings.get("hub_url", ""))}</a>
· SHA-256 <code>{esc(listings.get("hub_sha256", ""))}</code>
· markets shown: {esc(", ".join(markets)) or "none"}</p>
"""
    parts = [head]
    parts.append('<h2 id="picks">Picks</h2>')
    if not preds:
        parts.append(f'<div class="notice"><strong>No pick published.</strong> {esc(SPORT_NOTE.get(sport, ""))}</div>')
    else:
        rows = [[
            f'<a href="{esc(olbg(p["olbg_url"]))}" rel="nofollow">{esc(p["event"])}</a>',
            esc(p["start_utc"].replace("T", " ").replace("Z", "")),
            f'<strong>{esc(p["selection"])}</strong>',
            esc(p["market"]),
            american(p["fair_american"]),
            f'{p["probability"] * 100:.1f}%',
            badge(p["confidence"]),
        ] for p in preds]
        parts.append(table(["Event", "Start (UTC)", "Selection", "Market", "Our price", "Implied",
                            "Confidence"], rows))
        for p in preds:
            parts.append(f'<article class="pick"><h3>{esc(p["headline"])}</h3>'
                         f'<div class="meta">{esc(p["event"])} · '
                         f'{esc(p["start_utc"].replace("T", " ").replace("Z", " UTC"))} · {badge(p["confidence"])}</div>'
                         f'<p class="body">{esc(p["body"])}</p>'
                         f'<p class="small">OLBG listing: <a href="{esc(olbg(p["olbg_url"]))}">{esc(p["olbg_url"])}</a></p>'
                         f'</article>')
    parts.append('<h2 id="entries">Every event on the hub</h2>')
    if evs:
        rows = [[
            esc((e.get("start_utc") or "").replace("T", " ").replace("Z", "")),
            f'<a href="{esc(olbg(e["olbg_url"]))}" rel="nofollow">{esc(e["event"])}</a>',
            esc(", ".join(sorted({m["market"] for m in e.get("listed_markets", []) if m.get("market")}))),
            "priced" if any(p["olbg_url"] == e["olbg_url"] for p in preds) else "listed only",
        ] for e in sorted(evs, key=lambda e: e.get("start_utc") or "")]
        parts.append(table(["Start (UTC)", "Event", "Markets OLBG shows", "Status"], rows))
    else:
        parts.append('<p class="small">The hub page carried no event payload.</p>')
    parts.append(f'<p class="small">{esc(SPORT_NOTE.get(sport, ""))}</p>')
    return page(f"sports/{SLUG[sport]}.html", sport,
                f"Everything OLBG lists for {sport.lower()} today, what we priced, and what we could not.",
                "\n".join(parts), depth=1)


def render_sports_index(D: dict) -> str:
    cards = []
    for sport in SPORTS:
        preds = [p for p in D["predictions"]["predictions"] if p["sport"] == sport]
        evs = D["listings"]["sports"].get(sport, {}).get("events", [])
        cards.append(f"""<div class="card">
  <strong><a href="{SLUG[sport]}.html">{esc(sport)}</a></strong>
  <p class="small">{len(evs)} events · {len(preds)} picks · {sum(1 for p in preds if p["confidence"] == "high")} high confidence</p>
</div>""")
    return page("sports/index.html", "Sports",
                "One page per sport in scope: the listing, the picks and the gaps.",
                '<div class="grid">' + "".join(cards) + "</div>", depth=1)


def main() -> int:
    D = load()
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "sports").mkdir(exist_ok=True)
    (SITE / "assets").mkdir(exist_ok=True)
    (SITE / "assets" / "style.css").write_text(CSS)
    pages = {
        "index.html": render_index(D),
        "picks.html": render_picks(D),
        "entries.html": render_entries(D),
        "markets.html": render_markets(D),
        "flagged.html": render_flagged(D),
        "sources.html": render_sources(D),
        "methodology.html": render_method(D),
        "sports/index.html": render_sports_index(D),
    }
    for sport in SPORTS:
        pages[f"sports/{SLUG[sport]}.html"] = render_sport(D, sport)
    for name, content in pages.items():
        (SITE / name).write_text(content)
    print(f"wrote {len(pages)} pages into {SITE.relative_to(ROOT)}")
    for name in sorted(pages):
        print(f"  {name:32s} {len(pages[name]):>7,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

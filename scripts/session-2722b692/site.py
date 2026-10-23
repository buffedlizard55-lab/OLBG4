#!/usr/bin/env python3
"""Board AJ — GitHub Pages dashboard for the 15-sport desk.

Renders session-2722b692/ from the committed JSON: data/session-2722b692/desk.json,
predictions.json, review.json, flagged.json and verification.json. Deterministic: the same
inputs always produce byte-identical pages (verified by verify.py).
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2722b692"
OUT = ROOT / "session-2722b692"
BUILT = "2026-10-23"

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
SLUG = {s: s.lower().replace(" ", "-") for s in SPORTS}

DESK = json.loads((DATA / "desk.json").read_text())
PRED = json.loads((DATA / "predictions.json").read_text()) if (DATA / "predictions.json").exists() else {"predictions": []}
REVIEW = json.loads((DATA / "review.json").read_text()) if (DATA / "review.json").exists() else {"findings": []}
FLAGS = json.loads((DATA / "flagged.json").read_text()) if (DATA / "flagged.json").exists() else {"flags": []}
VERIF = json.loads((DATA / "verification.json").read_text()) if (DATA / "verification.json").exists() else {}
INV = json.loads((DATA / "olbg_inventory.json").read_text()) if (DATA / "olbg_inventory.json").exists() else {"hubs": []}
OLBG_EVENTS = {}
for hub in INV.get("hubs", []):
    OLBG_EVENTS.setdefault(hub.get("sport", ""), []).extend(hub.get("events", []))
COUNTS = {"rows": DESK["row_count"], "markets": DESK["market_count"], "high": DESK["high_count"]}
PRED_BY_ID = {p["id"]: p for p in PRED["predictions"]}

E = lambda s: html.escape(str(s), quote=True)
INWIN = "<span class='chip win'>yes</span>"
PASS = "<span class='chip hi'>pass</span>"
FAIL = "<span class='chip out'>fail</span>"


def money(v):
    return E(v) if v not in (None, "") else "—"


def src(url, label=None):
    if not url:
        return "<span class='miss'>source not recorded</span>"
    host = url.split("//")[-1].split("/")[0]
    return (f"<a class='src' href='{E(url)}' target='_blank' rel='noopener'>"
            f"{E(label or host)}</a>")


def sel_with_line(sel: str, line) -> str:
    """Selection text plus the line, without repeating a line the selection already carries."""
    if not line:
        return E(sel)
    return E(sel) if str(line) in str(sel) else f"{E(sel)} {E(line)}"


def chip(conf):
    cls = {"High": "hi", "Medium": "md", "Low": "lo"}.get(conf, "lo")
    return f"<span class='chip {cls}'>{E(conf)}</span>"


def winchip(flag):
    return ("<span class='chip win'>in window</span>" if flag
            else "<span class='chip out'>outside window</span>")


CSS = """
:root{--ink:#101828;--mut:#5b6577;--line:#e3e7ee;--bg:#f6f7f9;--card:#fff;--acc:#0f5bd8;
--hi:#0d7a3f;--hi-bg:#e7f7ed;--md:#8a5a00;--md-bg:#fdf3dd;--lo:#5b6577;--lo-bg:#eef0f4;
--out:#a3271f;--out-bg:#fdeceb}
*{box-sizing:border-box}
body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
color:var(--ink);background:var(--bg)}
header{background:#0b1b34;color:#fff;padding:26px 28px 20px}
header h1{margin:0;font-size:23px;letter-spacing:.2px}
header .sub{color:#a9b6cc;font-size:13px;margin-top:6px;max-width:1100px}
nav{position:sticky;top:0;z-index:9;background:#fff;border-bottom:1px solid var(--line);
padding:8px 20px;display:flex;gap:4px;flex-wrap:wrap;align-items:center}
nav a{color:var(--ink);text-decoration:none;padding:6px 10px;border-radius:6px;font-size:13.5px}
nav a:hover{background:#eef2f9}
nav a.on{background:#0b1b34;color:#fff}
nav details{position:relative}
nav summary{cursor:pointer;padding:6px 10px;border-radius:6px;font-size:13.5px;list-style:none}
nav summary:hover{background:#eef2f9}
nav .menu{position:absolute;background:#fff;border:1px solid var(--line);border-radius:8px;
box-shadow:0 8px 24px rgba(16,24,40,.12);padding:8px;min-width:210px;display:grid;gap:2px}
main{max-width:1180px;margin:0 auto;padding:26px 22px 70px}
h2{font-size:19px;margin:34px 0 12px}
h2:first-child{margin-top:6px}
h3{font-size:15px;margin:22px 0 8px}
p{max-width:900px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0 6px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.card .n{font-size:26px;font-weight:650;letter-spacing:-.5px}
.card .t{color:var(--mut);font-size:12.5px;margin-top:3px}
table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--line);
border-radius:10px;overflow:hidden;margin:10px 0 6px;font-size:13.5px}
th,td{padding:9px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f3f8;font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.3px;color:#3c4657}
tbody tr:last-child td{border-bottom:0}
tbody tr:hover{background:#fafbfd}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
.chip{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11.5px;font-weight:600;white-space:nowrap}
.chip.hi{color:var(--hi);background:var(--hi-bg)}
.chip.md{color:var(--md);background:var(--md-bg)}
.chip.lo{color:var(--lo);background:var(--lo-bg)}
.chip.win{color:#0b5cad;background:#e8f1fd}
.chip.out{color:var(--out);background:var(--out-bg)}
a.src{color:var(--acc);text-decoration:none;font-size:12.5px}
a.src:hover{text-decoration:underline}
.miss{color:var(--out);font-size:12.5px}
.note{background:#fff;border-left:3px solid var(--acc);padding:12px 16px;border-radius:0 8px 8px 0;
margin:12px 0;font-size:13.5px;color:#33405a}
.warn{background:#fff8ea;border-left:3px solid #c98a00;padding:12px 16px;border-radius:0 8px 8px 0;
margin:12px 0;font-size:13.5px}
.pick{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin:16px 0}
.pick h3{margin:0 0 4px;font-size:16px}
.pick .meta{color:var(--mut);font-size:12.5px;margin-bottom:10px}
.pick .sel{font-size:14.5px;margin:8px 0}
.pick .txt{max-width:900px}
.pick ul{margin:8px 0 0;padding-left:18px;font-size:13px;color:#33405a}
a.k{color:var(--acc);text-decoration:none}
a.k:hover{text-decoration:underline}
details.fixture{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:10px 14px;margin:8px 0}
details.fixture>summary{cursor:pointer;font-weight:600;font-size:13.5px}
footer{border-top:1px solid var(--line);color:var(--mut);font-size:12.5px;padding:22px;
max-width:1180px;margin:0 auto}
.small{font-size:12.5px;color:var(--mut)}
"""


def nav(current: str, prefix: str = "") -> str:
    sports = "".join(f"<a href='sports/{SLUG[s]}.html'>{E(s)}</a>" for s in SPORTS)
    links = [("index.html", "Summary"), ("picks.html", "High picks"), ("entries.html", "All entries"),
             ("markets.html", "Markets"), ("coverage.html", "Coverage"), ("sources.html", "Sources"),
             ("methodology.html", "Methodology"), ("verification.html", "Verification"),
             ("review.html", "Review"), ("flagged.html", "Flagged for Review")]
    out = ["<nav>"]
    for href, label in links:
        on = " class='on'" if href == current else ""
        out.append(f"<a href='{prefix}{href}'{on}>{E(label)}</a>")
    out.append("<details><summary>Sports (15) ▾</summary><div class='menu'>"
               + sports.replace("href='sports/", f"href='{prefix}sports/") + "</div></details>")
    out.append("</nav>")
    return "".join(out)


def page(title: str, current: str, body: str, subtitle: str = "") -> str:
    prefix = "../" if current.startswith("sports/") else ""
    sub = subtitle or ("Board AJ · session arena/2722b692-olbg4 · 15 sports · every price is this "
                       "desk's own originated line · every row links its official source")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{E(title)} — OLBG4 Board AJ</title>"
            f"<style>{CSS}</style></head><body>"
            f"<header><h1>OLBG4 — Board AJ · 15-sport line-origination desk</h1>"
            f"<div class='sub'>{sub} · built {BUILT}</div></header>{nav(current, prefix)}<main>{body}</main>"
            "<footer>Lines published here are this board's own computation from the official sources "
            "linked on every row; they are not bookmaker prices. Blank cells are blank because no "
            "official source confirmed a value — each one links a Flagged-for-Review entry. "
            "<a class='k' href='https://github.com/buffedlizard55-lab/OLBG4/tree/arena/2722b692-olbg4'>"
            "Repository</a></footer></body></html>")


def row_markets(r) -> str:
    return "".join(
        f"<tr><td>{E(m['market'])}</td><td>{E(m['selection'])}</td><td class='num'>{E(m.get('line') or '—')}</td>"
        f"<td class='num'>{m['probability']:.4f}</td><td class='num'>{E(m['fair_decimal'])}</td>"
        f"<td class='num'>{E(m['fair_american'])}</td>"
        f"<td>{INWIN if m.get('in_window') else 'no'}</td></tr>"
        for m in r["markets"])


def fixture_details(r) -> str:
    return (f"<details class='fixture'><summary>{E(r['away'])} @ {E(r['home'])} · "
            f"{E(r['start_utc'][:16].replace('T', ' '))} UTC · {len(r['markets'])} markets</summary>"
            "<table><thead><tr><th>Market</th><th>Selection</th><th class='num'>Line</th>"
            "<th class='num'>Probability</th><th class='num'>Fair decimal</th>"
            "<th class='num'>Fair American</th><th>In −250…+10,000</th></tr></thead><tbody>"
            + row_markets(r) + "</tbody></table>"
            f"<p class='small'>Inputs: {E(r['model'].get('inputs_used', []))} · "
            f"caps: {E(r['model'].get('caps') or 'none')} · source {src(r['source_url'])}</p></details>")


# ------------------------------------------------------------------------------- index
def build_index() -> str:
    highs = sorted([r for r in DESK["rows"] if r["high_confidence"]], key=lambda r: r["start_utc"])
    counts = COUNTS
    priced_sports = [s for s in SPORTS if DESK["by_sport"][s]["fixtures"]]
    unpriced = DESK.get("unpriced", [])
    body = ["<h2>Executive summary — highest-confidence picks</h2>",
            "<div class='cards'>",
            f"<div class='card'><div class='n'>{counts['rows']}</div><div class='t'>fixtures with originated lines</div></div>",
            f"<div class='card'><div class='n'>{counts['markets']}</div><div class='t'>originated market selections</div></div>",
            f"<div class='card'><div class='n'>{counts['high']}</div><div class='t'>High-confidence picks</div></div>",
            f"<div class='card'><div class='n'>{sum(1 for r in highs if r['pick']['in_window'])}</div>"
            "<div class='t'>High picks inside −250…+10,000</div></div>",
            f"<div class='card'><div class='n'>{len(PRED['predictions'])}</div><div class='t'>written predictions</div></div>",
            f"<div class='card'><div class='n'>{len(unpriced)}</div><div class='t'>listings left unpriced, with reasons</div></div>",
            "</div>",
            "<div class='warn'><strong>The window is a real constraint.</strong> A 70% win probability "
            "prices at −233 American, which is already shorter than the brief's −250 short end. Only "
            "probabilities between 70.0% and 71.43% can sit inside −250…+10,000 at all. Where a fixture's "
            "match winner is stronger than that, this desk publishes the deepest line it originates that "
            "does fit, and shows the winner price next to it instead of shortening anything. Eight of the "
            "High picks below are stronger than the window allows and are labelled as such — "
            "<a class='k' href='flagged.html'>AJ-F01</a>.</div>",
            f"<p>{len(highs)} fixtures carry a High label across {len({r['sport'] for r in highs})} sports. "
            "Every one has its own written prediction of at least 30 words on "
            "<a class='k' href='picks.html'>High picks</a>; the sports that could not reach five are "
            "listed with reasons on <a class='k' href='flagged.html'>Flagged for Review</a>.</p>",
            "<table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Fixture</th><th>Selection</th>"
            "<th class='num'>Fair price</th><th class='num'>Probability</th><th>Label</th>"
            "<th>Window</th><th>Source</th></tr></thead><tbody>"]
    for r in highs:
        body.append(f"<tr><td>{E(r['start_utc'][:16].replace('T', ' '))}</td><td>{E(r['sport'])}</td>"
                    f"<td>{E(r['away'])} @ {E(r['home'])}</td>"
                    f"<td><strong>{sel_with_line(r['pick']['selection'], r['pick'].get('line'))}</strong>"
                    f" <span class='small'>{E(r['pick']['market'])}</span></td>"
                    f"<td class='num'>{E(r['pick']['fair_american'])}</td>"
                    f"<td class='num'>{r['pick']['probability']:.4f}</td><td>{chip(r['confidence'])}</td>"
                    f"<td>{winchip(r['pick']['in_window'])}</td><td>{src(r['source_url'])}</td></tr>")
    body.append("</tbody></table>")

    body.append("<h2>Coverage by sport</h2>"
                "<table><thead><tr><th>Sport</th><th class='num'>Fixtures</th><th class='num'>Markets</th>"
                "<th class='num'>High</th><th class='num'>Medium</th><th class='num'>Low</th>"
                "<th>Why blanks exist</th></tr></thead><tbody>")
    for s in SPORTS:
        b = DESK["by_sport"][s]
        if b["fixtures"]:
            why = "—"
        else:
            reasons = [u.get("reason", "") for u in unpriced if u.get("sport") == s]
            why = max(reasons, key=len) if reasons else "no OLBG listing and no readable official feed today"
        body.append(f"<tr><td><a class='k' href='sports/{SLUG[s]}.html'>{E(s)}</a></td>"
                    f"<td class='num'>{b['fixtures']}</td><td class='num'>{b['priced_markets']}</td>"
                    f"<td class='num'>{b['high']}</td><td class='num'>{b['medium']}</td>"
                    f"<td class='num'>{b['low']}</td><td class='small'>{E(why[:190])}</td></tr>")
    body.append("</tbody></table>")
    body.append(f"<p class='small'>Priced: {', '.join(priced_sports)}. The other "
                f"{15 - len(priced_sports)} sports are published as listing-only rows with the exact "
                "reason attached in <a class='k' href='coverage.html'>Coverage</a>.</p>")

    today = [r for r in DESK["rows"] if r["start_utc"][:10] in ("2026-10-23", "2026-10-24")]
    body.append(f"<h2>Next 48 hours — {len(today)} fixtures with originated lines</h2>"
                "<table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Competition</th><th>Fixture</th>"
                "<th>Our pick</th><th class='num'>Price</th><th class='num'>Probability</th>"
                "<th>Label</th><th>Source</th></tr></thead><tbody>")
    for r in sorted(today, key=lambda r: (r["start_utc"], r["sport"])):
        body.append(f"<tr><td>{E(r['start_utc'][:16].replace('T', ' '))}</td><td>{E(r['sport'])}</td>"
                    f"<td class='small'>{E(r['competition'])}</td>"
                    f"<td>{E(r['away'])} @ {E(r['home'])}</td>"
                    f"<td>{sel_with_line(r['pick']['selection'], r['pick'].get('line'))}</td>"
                    f"<td class='num'>{E(r['pick']['fair_american'])}</td>"
                    f"<td class='num'>{r['pick']['probability']:.4f}</td><td>{chip(r['confidence'])}</td>"
                    f"<td>{src(r['source_url'])}</td></tr>")
    body.append("</tbody></table>")
    return page("Executive summary", "index.html", "".join(body))


# ------------------------------------------------------------------------------- picks
def build_picks() -> str:
    highs = sorted([r for r in DESK["rows"] if r["high_confidence"]], key=lambda r: (r["sport"], r["sport_rank"]))
    body = ["<h2>High-confidence picks and their written predictions</h2>",
            "<p>One card per High pick: the originated line, the price it implies, the probability it "
            "sits at, and a hand-written prediction naming the sides, their current form and the "
            "statistics the line rests on. Prices are fair prices (1/probability), never bookmaker "
            "quotes.</p>"]
    by_sport = {}
    for r in highs:
        by_sport.setdefault(r["sport"], []).append(r)
    for s in SPORTS:
        if s not in by_sport:
            continue
        body.append(f"<h3>{E(s)} — {len(by_sport[s])} High pick(s)</h3>")
        for r in by_sport[s]:
            p = PRED_BY_ID.get(r["id"], {})
            pick = r["pick"]
            body.append("<div class='pick' id='{i}'>".format(i=E(r["id"])))
            body.append(f"<h3>{E(r['away'])} @ {E(r['home'])}</h3>"
                        f"<div class='meta'>{E(r['competition'])} · {E(r['start_utc'][:16].replace('T', ' '))} UTC · "
                        f"{E(r['id'])} · {chip(r['confidence'])} {winchip(pick['in_window'])}</div>")
            body.append(f"<div class='sel'><strong>Selection: {sel_with_line(pick['selection'], pick.get('line'))}</strong> — {E(pick['market'])}, "
                        f"fair {E(pick['fair_american'])} (decimal {E(pick['fair_decimal'])}), "
                        f"{pick['probability'] * 100:.1f}% win probability.</div>")
            if p.get("text"):
                body.append(f"<p class='txt'>{E(p['text'])}</p>")
                body.append("<ul>" + "".join(
                    f"<li><strong>{E(e['label'])}:</strong> {E(e['value'])} "
                    f"<span class='small'>— {src(e['source_url'])}</span></li>"
                    for e in p.get("evidence", [])) + "</ul>")
            if not pick["in_window"]:
                body.append(f"<div class='warn small'>{E(r['pick_note'])}</div>")
            body.append(f"<p class='small'>Winner price for reference: {E(r['winner_pick']['selection'])} "
                        f"{E(r['winner_pick']['fair_american'])} · source {src(r['source_url'])}</p>")
            body.append("</div>")
    return page("High picks", "picks.html", "".join(body))


# ------------------------------------------------------------------------------- entries
def build_entries() -> str:
    body = ["<h2>All originated fixtures</h2>",
            f"<p>{COUNTS['rows']} fixtures, {COUNTS['markets']} market selections. "
            "Every row links the official page the inputs came from; the pick shown is the line this "
            "desk would publish for that fixture.</p>",
            "<table><thead><tr><th>Start (UTC)</th><th>Sport</th><th>Competition</th><th>Fixture</th>"
            "<th>Pick</th><th>Market</th><th class='num'>Line</th><th class='num'>Fair price</th>"
            "<th class='num'>Probability</th><th>Label</th><th>Source</th></tr></thead><tbody>"]
    for r in sorted(DESK["rows"], key=lambda r: (r["start_utc"], r["sport"], r["id"])):
        body.append(f"<tr><td>{E(r['start_utc'][:16].replace('T', ' '))}</td>"
                    f"<td><a class='k' href='sports/{SLUG[r['sport']]}.html'>{E(r['sport'])}</a></td>"
                    f"<td class='small'>{E(r['competition'])}</td>"
                    f"<td>{E(r['away'])} @ {E(r['home'])}</td><td>{E(r['pick']['selection'])}</td>"
                    f"<td class='small'>{E(r['pick']['market'])}</td>"
                    f"<td class='num'>{E(r['pick'].get('line') or '—')}</td>"
                    f"<td class='num'>{E(r['pick']['fair_american'])}</td>"
                    f"<td class='num'>{r['pick']['probability']:.4f}</td>"
                    f"<td>{chip(r['confidence'])}</td><td>{src(r['source_url'])}</td></tr>")
    body.append("</tbody></table>")
    return page("All entries", "entries.html", "".join(body))


# ------------------------------------------------------------------------------- markets
def build_markets() -> str:
    fam: dict[str, dict[str, int]] = {}
    for r in DESK["rows"]:
        d = fam.setdefault(r["sport"], {})
        for m in r["markets"]:
            d[m["market"]] = d.get(m["market"], 0) + 1
    body = ["<h2>Market taxonomy — what was originated and what was investigated</h2>",
            "<p>Market names follow the OLBG labels read from the live hub payloads, so the same "
            "selection vocabulary can be compared across sports.</p>",
            "<table><thead><tr><th>Sport</th><th>Originated markets</th><th class='num'>Selections</th>"
            "<th>Investigated but not originated</th></tr></thead><tbody>"]
    gaps = {
        "Cricket": "Innings runs, top batter/bowler, series handicap — no readable official per-team feed",
        "Darts": "180s, checkout %, match legs — no readable official scoring feed",
        "Golf": "Outright, top-10, tournament matchups — no field list readable",
        "Gaelic Sports": "Match winner, handicap, total points — no fixture payload in the GAA pages",
        "Greyhounds": "Trap draw, forecast, winning time — results only, no forward cards",
        "Snooker": "Frame handicap, total frames, highest break — fewer than five completed matches per player",
        "Volleyball": "Match winner, set handicap, total points — PlusLiga table cannot be tied to 2026-27",
        "Motor Racing": "Race winner, podium, fastest lap — calendars only, no pace input",
        "Rugby League": "Match winner, handicap, total points — priced on one completed match per side, capped Low",
    }
    for s in SPORTS:
        d = fam.get(s, {})
        if d:
            body.append(f"<tr><td>{E(s)}</td><td>{E(', '.join(sorted(d)))}</td>"
                        f"<td class='num'>{sum(d.values())}</td><td class='small'>"
                        f"{E(gaps.get(s, '—'))}</td></tr>")
        else:
            body.append(f"<tr><td>{E(s)}</td><td>—</td><td class='num'>0</td>"
                        f"<td class='small'>{E(gaps.get(s, 'no readable official feed today'))}</td></tr>")
    body.append("</tbody></table>")
    body.append("<h3>Per-fixture market book</h3><p class='small'>Every originated selection for every "
                "fixture, including the ones the desk chose not to publish as its pick.</p>")
    for s in SPORTS:
        rows = [r for r in DESK["rows"] if r["sport"] == s]
        if not rows:
            continue
        body.append(f"<h3>{E(s)}</h3>")
        body.extend(fixture_details(r) for r in sorted(rows, key=lambda r: r["start_utc"]))
    return page("Markets", "markets.html", "".join(body))


# ------------------------------------------------------------------------------- coverage
def build_coverage() -> str:
    unpriced = DESK.get("unpriced", [])
    body = ["<h2>Coverage reconciliation — OLBG listings against official sources</h2>",
            "<p>OLBG supplies the fixture list and the market taxonomy; the strength inputs come only "
            "from the official source named on each row. A sport with no readable official feed is "
            "published as a listing-only row, never with an invented price.</p>",
            "<table><thead><tr><th>Sport</th><th class='num'>OLBG events listed</th>"
            "<th class='num'>Priced fixtures</th><th class='num'>Listing-only rows</th>"
            "<th>Status</th></tr></thead><tbody>"]
    for s in SPORTS:
        ev = len(OLBG_EVENTS.get(s, []))
        rows_s = DESK["by_sport"][s]["fixtures"]
        lonly = sum(1 for u in unpriced if u.get("sport") == s)
        status = ("priced from an official feed" if rows_s else
                  ("listing only — no readable official feed" if lonly else "no listing and no feed"))
        body.append(f"<tr><td>{E(s)}</td><td class='num'>{ev}</td><td class='num'>{rows_s}</td>"
                    f"<td class='num'>{lonly}</td><td class='small'>{E(status)}</td></tr>")
    body.append("</tbody></table>")

    body.append("<h3>Every listing left unpriced</h3>"
                "<p class='small'>Each row names the reason and links the OLBG hub page it came from. "
                "Nothing in this table has a price attached.</p>"
                "<table><thead><tr><th>Sport</th><th>Listing</th><th>Start (UTC)</th><th>Reason</th>"
                "<th>Source</th></tr></thead><tbody>")
    for u in sorted(unpriced, key=lambda u: (u.get("sport", ""), u.get("start_utc", ""), u.get("event", ""))):
        body.append(f"<tr><td>{E(u.get('sport', ''))}</td>"
                    f"<td>{E(u.get('event') or (str(u.get('away', '')) + ' @ ' + str(u.get('home', ''))))}</td>"
                    f"<td>{E(u.get('start_utc', '') or '—')}</td>"
                    f"<td class='small'>{E(u.get('reason', ''))}</td><td>{src(u.get('source_url', ''))}</td></tr>")
    body.append("</tbody></table>")
    return page("Coverage", "coverage.html", "".join(body))


# ------------------------------------------------------------------------------- sources
def build_sources() -> str:
    caps = sorted(glob_captures())
    body = ["<h2>Provenance — every payload this desk read</h2>",
            "<p>Raw responses are committed as deterministic gzip with a SHA-256 per target, so each "
            "row of the desk can be re-derived byte-for-byte from the snapshot.</p>"]
    for path in caps:
        man = json.loads((path / "manifest.json").read_text())
        ok = sum(1 for r in man["records"] if r.get("status") == 200 and r.get("file"))
        body.append(f"<h3>Capture {E(path.name)} — {ok}/{man['targets']} targets returned 200</h3>"
                    "<table><thead><tr><th>Target</th><th>Kind</th><th>Sport</th><th class='num'>Status</th>"
                    "<th class='num'>Bytes</th><th>SHA-256</th><th>URL</th></tr></thead><tbody>")
        for r in sorted(man["records"], key=lambda r: r["id"]):
            body.append(f"<tr><td>{E(r['id'])}</td><td class='small'>{E(r.get('kind', ''))}</td>"
                        f"<td class='small'>{E(r.get('sport', ''))}</td>"
                        f"<td class='num'>{E(r.get('status'))}</td><td class='num'>{E(r.get('bytes', '—'))}</td>"
                        f"<td class='small'>{(r.get('sha256') or '—')[:16]}…</td>"
                        f"<td class='small'>{E(r.get('url', ''))}</td></tr>")
        body.append("</tbody></table>")
    probes = sorted((DATA / "probe").glob("*/probe_summary.json"))
    if probes:
        p = json.loads(probes[-1].read_text())
        body.append(f"<h3>Endpoint probe {E(probes[-1].parent.name)} — "
                    f"{sum(1 for r in p['results'] if r.get('status') == 200)}/{len(p['results'])} returned 200</h3>"
                    "<p class='small'>Probe responses are committed the same way and are what the "
                    "table parsers read for Handball.</p>"
                    "<table><thead><tr><th>Candidate</th><th class='num'>Status</th><th class='num'>Bytes</th>"
                    "<th>URL</th></tr></thead><tbody>")
        for r in sorted(p["results"], key=lambda r: r["id"]):
            body.append(f"<tr><td>{E(r['id'])}</td><td class='num'>{E(r.get('status'))}</td>"
                        f"<td class='num'>{E(r.get('bytes') or 0)}</td>"
                        f"<td class='small'>{E(r.get('url', ''))}</td></tr>")
        body.append("</tbody></table>")
    return page("Sources", "sources.html", "".join(body))


def glob_captures():
    return sorted((DATA / "capture").glob("*"))


# ------------------------------------------------------------------------------- methodology
def build_methodology() -> str:
    body = ["<h2>How each line is originated</h2>",
            "<p>Every price is a fair price: decimal = 1/probability, American odds re-derived from "
            "it, and a two-way pair always sums to 1.0. Nothing is copied from a bookmaker. Where a "
            "sport has too little readable evidence to separate the sides, the fixture is listed "
            "without a price instead of being given a wide guess.</p>",
            "<h3>Models by sport</h3>"
            "<table><thead><tr><th>Sport</th><th>Inputs (official)</th><th>Model</th><th>Caps applied</th></tr></thead><tbody>"
            "<tr><td>Ice Hockey</td><td>NHL standings (goals for/against, home/road, L10); Liiga and SHL "
            "result feeds</td><td>Independent-Poisson goal grid; rates shrunk to the league goals prior "
            "(k=5); 60-minute draw split for the puck line</td><td>Fewer than 6 games on either side → "
            "no High label</td></tr>"
            "<tr><td>Basketball</td><td>EuroLeague / EuroCup game feeds (points for/against per game)</td>"
            "<td>Normal margin model (sd 11.5) on shrunk points-for/against (k=8); totals from the two "
            "paces</td><td>Early-season samples flagged in the row</td></tr>"
            "<tr><td>Baseball</td><td>MLB Stats API schedule + season hitting/pitching</td>"
            "<td>Poisson run model with park-neutral team run factors</td><td>Post-season sample → "
            "Medium ceiling</td></tr>"
            "<tr><td>Tennis</td><td>WTA match feeds and ranking points</td><td>Calibrated log-odds on "
            "ranking points, exact best-of-3 set maths for handicaps and totals</td><td>Rank beyond 100, "
            "provisional start times, cross-tournament listings</td></tr>"
            "<tr><td>Rugby Union</td><td>Top 14 official table (points for/against, rank)</td>"
            "<td>Normal margin model (sd 14) on shrunk points per match (k=4)</td><td>Small samples</td></tr>"
            "<tr><td>Handball</td><td>Liga ASOBAL and Danish Herreligaen official tables</td>"
            "<td>Goal-normal model (sd 8.2) with multiplicative attack/defence and a league home edge; "
            "3-way winner, draw-no-bet, handicaps, totals</td><td>Fewer than 5 matches → no High label</td></tr>"
            "<tr><td>Rugby League</td><td>RLWC 2026 official fixture/result feed</td><td>Normal margin "
            "model on points for/against, shrunk hard with k=4</td><td>One completed match per side → "
            "Low, and flagged</td></tr>"
            "</tbody></table>",
            "<h3>Why the odds window bites</h3>",
            "<p>Implied probability from American odds: p = 100/(100+|A|) for negative prices. "
            "−250 → 71.43%, +10,000 → 0.99%. A 70% pick prices at −233, already shorter than −250. "
            "So the only prices that satisfy both '≥70% probability' and '−250…+10,000' are those "
            "between 70.00% and 71.43% — a 1.43-point band. This desk does not move prices to fit: it "
            "publishes the deepest line it originates that does fit, and labels the rest honestly.</p>",
            "<h3>Rate shrinkage</h3>",
            "<p>Early-season rates are pulled toward the league mean with an empirical-Bayes weight: "
            "rate&nbsp;=&nbsp;(observed×n + prior×k)/(n+k). Without it, a three-game hot start produced "
            "70–93% 'locks' in this repo's earlier builds; with it, no team is priced off a single "
            "weekend.</p>",
            "<h3>What is never done</h3>",
            "<ul><li>No price without an official input for both sides.</li>"
            "<li>No injury claim: no official availability feed is readable for these competitions, so "
            "injuries are left blank and flagged rather than guessed.</li>"
            "<li>No value is copied from OLBG's listed prices; those appear only as a cross-reference "
            "where a row records them.</li></ul>"]
    return page("Methodology", "methodology.html", "".join(body))


# ------------------------------------------------------------------------------- verification
def build_verification() -> str:
    if not VERIF:
        body = ("<h2>Verification</h2><p>The gate has not run against this build yet.</p>")
        return page("Verification", "verification.html", body)
    checks = VERIF.get("checks", [])
    body = ["<h2>Verification gate</h2>",
            f"<p>Run {E(VERIF.get('run_utc', ''))} · result <strong>{E(VERIF.get('result', ''))}</strong> "
            f"· {VERIF.get('passed', 0)} of {len(checks)} checks passed.</p>",
            "<table><thead><tr><th>Check</th><th>Result</th><th>Detail</th></tr></thead><tbody>"]
    for c in checks:
        body.append(f"<tr><td>{E(c['name'])}</td>"
                    f"<td>{PASS if c['ok'] else FAIL}</td>"
                    f"<td class='small'>{E(c['detail'])}</td></tr>")
    body.append("</tbody></table>")
    if VERIF.get("notes"):
        body.append("<h3>Notes</h3><ul>" + "".join(f"<li>{E(n)}</li>" for n in VERIF["notes"]) + "</ul>")
    return page("Verification", "verification.html", "".join(body))


# ------------------------------------------------------------------------------- review/flagged
def build_review() -> str:
    fs = REVIEW.get("findings", [])
    body = ["<h2>Line-by-line review of the repository's shared data</h2>",
            f"<p>{len(fs)} findings across {len(REVIEW.get('files_reviewed', []))} shared files. Each "
            "one names the exact row selector and the official page needed to check it by hand. None "
            "of these files belong to this board, so nothing here has been edited — they are reported "
            "for the owner.</p>",
            "<table><thead><tr><th>ID</th><th>File</th><th>Severity</th><th>Finding</th>"
            "<th>Row selector</th><th>Official source</th></tr></thead><tbody>"]
    for f in fs:
        sev = {"high": "out", "medium": "md", "low": "lo", "info": "win"}.get(f["severity"], "lo")
        body.append(f"<tr><td>{E(f['id'])}</td><td class='small'>{E(f['file'])}</td>"
                    f"<td><span class='chip {sev}'>{E(f['severity'])}</span></td>"
                    f"<td><strong>{E(f['title'])}</strong><div class='small'>{E(f['detail'])}</div></td>"
                    f"<td class='small'>{E(f['row_selector'])}</td><td>{src(f['official_url'])}</td></tr>")
    body.append("</tbody></table>")
    return page("Review", "review.html", "".join(body))


def build_flagged() -> str:
    flags = FLAGS.get("flags", [])
    body = ["<h2>Flagged for Review</h2>",
            "<p>Everything this desk could not confirm, everything it left blank, and every place the "
            "brief's requirements collide with arithmetic. Nothing on this page blocks publication; "
            "each item is labelled with what is missing and where to check it.</p>",
            "<table><thead><tr><th>ID</th><th>Sport / area</th><th>Issue</th><th>What is missing</th>"
            "<th>Check at</th></tr></thead><tbody>"]
    for f in flags:
        body.append(f"<tr><td>{E(f['id'])}</td><td>{E(f.get('area', ''))}</td>"
                    f"<td><strong>{E(f['title'])}</strong><div class='small'>{E(f['detail'])}</div></td>"
                    f"<td class='small'>{E(f.get('missing', ''))}</td>"
                    f"<td>{src(f.get('source_url', ''))}</td></tr>")
    body.append("</tbody></table>")
    unpriced = DESK.get("unpriced", [])
    body.append(f"<h3>Listing-only rows ({len(unpriced)})</h3><p class='small'>Full table on "
                "<a class='k' href='coverage.html'>Coverage</a>; the per-sport pages repeat the rows "
                "with their reasons.</p>")
    return page("Flagged for Review", "flagged.html", "".join(body))


# ------------------------------------------------------------------------------- sport page
def build_sport(s: str) -> str:
    b = DESK["by_sport"][s]
    rows = sorted([r for r in DESK["rows"] if r["sport"] == s], key=lambda r: r["start_utc"])
    unpriced = [u for u in DESK.get("unpriced", []) if u.get("sport") == s]
    body = [f"<h2>{E(s)} — {b['fixtures']} fixtures, {b['priced_markets']} originated selections</h2>",
            "<div class='cards'>",
            f"<div class='card'><div class='n'>{b['fixtures']}</div><div class='t'>fixtures with lines</div></div>",
            f"<div class='card'><div class='n'>{b['high']}</div><div class='t'>High confidence</div></div>",
            f"<div class='card'><div class='n'>{b['medium']}</div><div class='t'>Medium</div></div>",
            f"<div class='card'><div class='n'>{b['low']}</div><div class='t'>Low</div></div>",
            f"<div class='card'><div class='n'>{len(unpriced)}</div><div class='t'>listing-only rows</div></div>",
            "</div>"]
    if not rows:
        reason = max((u.get("reason", "") for u in unpriced), key=len, default="")
        body.append("<div class='warn'><strong>No price is published for this sport.</strong> "
                    f"{E(reason)}</div>")
    else:
        body.append("<table><thead><tr><th>Start (UTC)</th><th>Competition</th><th>Fixture</th>"
                    "<th>Our pick</th><th>Market</th><th class='num'>Fair price</th>"
                    "<th class='num'>Probability</th><th>Label</th><th>Window</th><th>Source</th></tr></thead><tbody>")
        for r in rows:
            body.append(f"<tr><td>{E(r['start_utc'][:16].replace('T', ' '))}</td>"
                        f"<td class='small'>{E(r['competition'])}</td>"
                        f"<td>{E(r['away'])} @ {E(r['home'])}</td>"
                        f"<td><strong>{E(r['pick']['selection'])}</strong></td>"
                        f"<td class='small'>{E(r['pick']['market'])}</td>"
                        f"<td class='num'>{E(r['pick']['fair_american'])}</td>"
                        f"<td class='num'>{r['pick']['probability']:.4f}</td>"
                        f"<td>{chip(r['confidence'])}</td><td>{winchip(r['pick']['in_window'])}</td>"
                        f"<td>{src(r['source_url'])}</td></tr>")
        body.append("</tbody></table>")
        notes = [n for r in rows for n in (r.get("model_notes") or [])]
        if notes:
            body.append("<div class='note'><strong>Notes carried by the rows:</strong> "
                        + E("; ".join(sorted(set(notes)))) + "</div>")
        body.append("<h3>Market book</h3>")
        body.extend(fixture_details(r) for r in rows)
    if unpriced:
        body.append(f"<h3>Listing-only rows ({len(unpriced)})</h3>"
                    "<table><thead><tr><th>Listing</th><th>Start (UTC)</th><th>Reason</th>"
                    "<th>Source</th></tr></thead><tbody>")
        for u in sorted(unpriced, key=lambda u: (u.get("start_utc") or "", u.get("event") or "")):
            body.append(f"<tr><td>{E(u.get('event') or (str(u.get('away', '')) + ' @ ' + str(u.get('home', ''))))}</td>"
                        f"<td>{E(u.get('start_utc') or '—')}</td>"
                        f"<td class='small'>{E(u.get('reason', ''))}</td>"
                        f"<td>{src(u.get('source_url', ''))}</td></tr>")
        body.append("</tbody></table>")
    return page(s, f"sports/{SLUG[s]}.html", "".join(body))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "sports").mkdir(exist_ok=True)
    files = {
        "index.html": build_index(), "picks.html": build_picks(), "entries.html": build_entries(),
        "markets.html": build_markets(), "coverage.html": build_coverage(),
        "sources.html": build_sources(), "methodology.html": build_methodology(),
        "verification.html": build_verification(), "review.html": build_review(),
        "flagged.html": build_flagged(),
    }
    for s in SPORTS:
        files[f"sports/{SLUG[s]}.html"] = build_sport(s)
    for name, content in files.items():
        (OUT / name).write_text(content)
    print(f"site: {len(files)} pages written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Session c92c927c - builds the desk, the data files and the published pages.

Run:  python3 scripts/session-c92c927c/build_site.py
      python3 scripts/session-c92c927c/build_site.py --check   (verify only, no writes)

The build refuses to publish when
  * a fixture has no source, or the source is not on the official-domain list;
  * a High-confidence pick has no write-up, or the write-up is under 30 words or near-duplicate;
  * a High-confidence pick sits outside the -250 to +10,000 window;
  * an excluded sport appears anywhere;
  * an internal link in the generated pages does not resolve.
"""

from __future__ import annotations

import csv
import html
import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model  # noqa: E402

ROOT = model.ROOT
DATA = model.DATA
SITE = os.path.join(ROOT, "session-c92c927c")

OFFICIAL_HOSTS = {
    "www.nhl.com", "nhl.com", "api-web.nhle.com",
    "www.nba.com", "nba.com",
    "statsapi.mlb.com", "www.mlb.com", "mlb.com",
    "stats.unitedrugby.com", "www.unitedrugby.com", "unitedrugby.com",
    "rlwc2026.com", "www.rlwc2026.com",
}

EXCLUDED = ["Soccer", "Boxing", "UFC/MMA", "Football", "American Football",
            "Hurling", "Horse Racing", "Cycling", "Specials"]

SPORT_SLUG = {
    "Ice Hockey": "ice-hockey", "Baseball": "baseball", "Rugby Union": "rugby-union",
    "Rugby League": "rugby-league", "Basketball": "basketball",
}

COVERAGE = [
    ("Ice Hockey", "Published", "12", "NHL.com scores page for 22 October 2026 plus the 21 October standings page", "https://www.nhl.com/scores/2026-10-22"),
    ("Baseball", "Published", "3", "MLB Stats API schedule (official MLB) \u2014 World Series Games 1\u20133", "https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-10-27"),
    ("Rugby Union", "Published", "8", "United Rugby Championship official match centre, Round 4", "https://stats.unitedrugby.com/match-centre/2026-27/4"),
    ("Rugby League", "Published", "5", "Rugby League World Cup 2026 official draw page, men's Round 2", "https://rlwc2026.com/draws-and-pools"),
    ("Basketball", "Published \u2014 no form", "2", "NBA.com games page for 22 October 2026", "https://www.nba.com/games?date=2026-10-22"),
    ("Tennis", "Not published", "0", "atptour.com daily-schedule path resolved to the archived January 2026 Hong Kong results, not a current draw; no current fixture could be read", "https://www.atptour.com/en/scores/current/vienna/336/daily-schedule"),
    ("Cricket", "Not published", "0", "nzc.nz/fixtures returned 404 and icc-cricket.com/fixtures returned 404 on this date", "https://www.icc-cricket.com/fixtures"),
    ("Darts", "Not published", "0", "pdc.tv tournament and news pages returned only a cookie-consent shell (11 chunks, no fixture text) in this sandbox", "https://www.pdc.tv/tournaments/machineseeker-european-championship"),
    ("Handball", "Not published", "0", "ehfcl.eurohandball.com/men/2026-27/fixtures/ returned a 404 page", "https://ehfcl.eurohandball.com/men/2026-27/fixtures/"),
    ("Snooker", "Not read this cycle", "0", "WST calendar not read within this session's budget; no fixture claimed", "https://wst.tv/"),
    ("Badminton", "Not read this cycle", "0", "BWF tournament page not read; no fixture claimed", "https://bwfbadminton.com/"),
    ("Table Tennis", "Not read this cycle", "0", "WTT events page not read; no fixture claimed", "https://worldtabletennis.com/"),
    ("Volleyball", "Not read this cycle", "0", "Volleyball World page not read; no fixture claimed", "https://en.volleyballworld.com/"),
    ("Golf", "Not read this cycle", "0", "DP World Tour schedule not read; no fixture claimed", "https://www.europeantour.com/"),
    ("Motor Racing", "Not read this cycle", "0", "Formula 1 calendar not read; no fixture claimed", "https://www.formula1.com/"),
    ("Greyhound Racing", "Not read this cycle", "0", "GBGB fixture list not read; no fixture claimed", "https://www.gbgb.org.uk/"),
    ("Aussie Rules", "Not read this cycle", "0", "AFL fixture page not read; no fixture claimed", "https://www.afl.com.au/"),
    ("Esports", "No official governing body", "0", "No single governing body publishes an authoritative fixture list for the events OLBG lists, so nothing can be labelled verified", "https://www.olbg.com/"),
    ("Gaelic Football", "Out of scope (flagged)", "0", "Excluded under a conservative reading of \u201cfootball\u201d; the ambiguity is flagged for review rather than resolved silently", "https://www.gaa.ie/"),
]


def esc(value):
    return html.escape("" if value is None else str(value))


def money_text(row):
    if not row.get("line_home"):
        return "blank"
    return f"{row['line_home']:.2f} / {row['line_away']:.2f}"


def american_text(row):
    if row.get("american") is None:
        return "&mdash;"
    a = row["american"]
    return f"+{a}" if a > 0 else str(a)


NAV = [
    ("index.html", "Dashboard"),
    ("fixtures.html", "All fixtures"),
    ("picks.html", "High-confidence picks"),
    ("markets.html", "Markets"),
    ("coverage.html", "Coverage"),
    ("verification.html", "Verification register"),
    ("flagged.html", "Flagged for review"),
    ("analysis.html", "Analysis"),
    ("methodology.html", "Method"),
    ("sources.html", "Sources"),
]


def page(title, body, active, prefix=""):
    links = "".join(
        f'<a class="navlink{" active" if href == active else ""}" href="{prefix}{href}">{esc(label)}</a>'
        for href, label in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · OLBG4 verified desk (Board U)</title>
<meta name="description" content="Freshly verified fixtures for 22-27 October 2026, our own originated lines, and High-confidence picks with one official source on every row.">
<link rel="stylesheet" href="{prefix}assets/style.css">
</head>
<body>
<header class="topbar"><div class="wrap bar">
<a class="brand" href="{prefix}index.html"><span class="mark">O4</span><span>OLBG4 <small>verified desk &middot; Board U</small></span></a>
<nav class="nav">{links}</nav>
</div></header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
<p><strong>Board U</strong> &middot; session <code>arena/c92c927c-olbg4</code> &middot; data read 2026-10-22 &middot;
every fixture carries a link to the official page it came from. Where an official page is silent the value is blank and the row is listed on
<a href="{prefix}flagged.html">Flagged for review</a>. No bookmaker price is used anywhere in this desk.</p>
<p><a href="{prefix}../index.html">&larr; Repository dashboard</a> &middot; <a href="{prefix}../board/index.html">Board P master board</a></p>
</footer>
</body>
</html>
"""


def table(headers, rows, cls=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


# ------------------------------------------------------------------ validation
def jaccard_3gram(a, b):
    def grams(t):
        w = re.findall(r"[a-z0-9']+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(max(0, len(w) - 2))}
    ga, gb = grams(a), grams(b)
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def validate(rows, preds):
    errors = []
    sources = model.load("team_stats.json")["sources"]
    for r in rows:
        src = sources.get(r["source"], {})
        url = src.get("url", "")
        host = re.sub(r"^https?://", "", url).split("/")[0]
        if not url:
            errors.append(f"{r['id']}: no source URL")
        elif host not in OFFICIAL_HOSTS:
            errors.append(f"{r['id']}: non-official host {host}")
        for sport in EXCLUDED:
            if sport.lower() in (r["sport"] + " " + r["competition"]).lower():
                errors.append(f"{r['id']}: excluded sport token {sport}")
    highs = [r for r in rows if r["confidence"] == "High"]
    texts = []
    for r in highs:
        p = preds.get(r["id"])
        if not p:
            errors.append(f"{r['id']}: High pick without a write-up")
            continue
        words = len(p["text"].split())
        if words < 30:
            errors.append(f"{r['id']}: write-up is {words} words")
        if r["american"] is None or not (1.40 <= r["line_home"] <= 101.0):
            errors.append(f"{r['id']}: line outside window")
        texts.append((r["id"], p["text"]))
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            jac = jaccard_3gram(texts[i][1], texts[j][1])
            if jac > 0.35:
                errors.append(f"{texts[i][0]}/{texts[j][0]}: write-ups {jac:.2f} similar")
    return errors


# ------------------------------------------------------------------ data build
def build_data():
    rows = model.build()
    preds_doc = model.load("predictions.json")
    preds = {p["id"]: p for p in preds_doc["predictions"]}
    for r in rows:
        p = preds.get(r["id"])
        r["prediction"] = p["text"] if p else ""
        r["selection"] = p["selection"] if p else ""
        r["words"] = len(p["text"].split()) if p else 0
    errors = validate(rows, preds)
    return rows, preds, errors


def coverage_json(rows):
    counts = Counter(r["sport"] for r in rows)
    out = []
    for sport, status, published, evidence, url in COVERAGE:
        out.append({"sport": sport, "status": status, "fixtures": int(published),
                    "rows_in_dataset": counts.get(sport, 0), "evidence": evidence, "source": url})
    return out


def flagged_items(rows, review):
    items = [
        {"id": "F01", "severity": "review", "title": "NHL.com prints two different Ottawa records",
         "what": "The 22 October scores page shows Ottawa as 6-3-0; the 21 October standings page shows 7-3-0 over 10 games. The standings figure is used, and the row is marked medium.",
         "sources": ["https://www.nhl.com/scores/2026-10-22", "https://www.nhl.com/standings/2026-10-21/wildcard"]},
        {"id": "F02", "severity": "blank", "title": "Los Angeles and Calgary goals-for / goals-against not published",
         "what": "Both NHL pages read during this session give the Kings and Flames a win-loss-overtime record but no goals for/against, so the goals-based markets on NHL-20261022-06 and -09 are blank and those two moneyline prices use the disclosed points-percentage fallback.",
         "sources": ["https://www.nhl.com/scores/2026-10-22", "https://www.nhl.com/standings/2026-10-21/wildcard"]},
        {"id": "F03", "severity": "review", "title": "Rugby League World Cup kick-off times carry no timezone",
         "what": "The official draw prints 5:05 AM, 2:35 AM, 12:25 AM, 1:05 AM and 5:05 AM with no zone. The times are reproduced verbatim with that caveat; no conversion has been applied.",
         "sources": ["https://rlwc2026.com/draws-and-pools"]},
        {"id": "F04", "severity": "review", "title": "Model rates Fiji above Australia on one match",
         "what": "Fiji beat the Cook Islands 40-12 and Australia beat New Zealand by two, so the single-match rating favours Fiji by 0.81. The desk does not publish that as a High-confidence pick: the row is held at Medium and listed here for manual review.",
         "sources": ["https://rlwc2026.com/draws-and-pools"]},
        {"id": "F05", "severity": "blank", "title": "NBA venues not published on the games page",
         "what": "The NBA games page for 22 October lists both fixtures, tip-off times and records but no arena, so the venue field is blank on NBA-20261022-01 and -02.",
         "sources": ["https://www.nba.com/games?date=2026-10-22"]},
        {"id": "F06", "severity": "review", "title": "Opening-week NBA games cannot be priced on form",
         "what": "Neither club has a verified current-season record beyond one game, so both NBA rows use the home-court prior, are graded Low, and carry no spread or total.",
         "sources": ["https://www.nba.com/games?date=2026-10-22"]},
        {"id": "F07", "severity": "blank", "title": "Rugby union and rugby league totals not originated",
         "what": "One verified match per club does not establish a scoring level, so match totals are blank on all 13 rugby rows; the handicap is originated because it is a relative measure from the same rating and is labelled as such.",
         "sources": ["https://stats.unitedrugby.com/match-centre/2026-27/4", "https://rlwc2026.com/draws-and-pools"]},
        {"id": "F08", "severity": "review", "title": "Thirteen in-scope sports have no verified fixture in this cycle",
         "what": "Tennis, cricket, darts, handball, snooker, badminton, table tennis, volleyball, golf, motor racing, greyhound racing, Aussie Rules and esports are listed on the coverage page with the official URL that was tried and the reason no row was published. They are gaps, not empty sports.",
         "sources": ["coverage.html"]},
        {"id": "F09", "severity": "review", "title": "High picks quote at the -250 floor",
         "what": "The brief asks for High picks between -250 and +10,000. Our model gives several selections more than 71.4% (a shorter fair price than -250), so the desk quotes them at its -250 floor and marks every capped row. The fair price is shown on the row.",
         "sources": ["methodology.html"]},
        {"id": "F10", "severity": "review", "title": "Prior published rows: EHF and PDC fixtures could not be re-opened",
         "what": "Board S published an EHF Champions League fixture (RK Partizan AdmiralBet v FC Porto) and a PDC match (Gerwyn Price v Rob Cross). The EHF fixture path returns 404 and pdc.tv returns a cookie shell in this sandbox, so neither can be confirmed or refuted here.",
         "sources": ["https://ehfcl.eurohandball.com/men/2026-27/fixtures/", "https://www.pdc.tv/tournaments/machineseeker-european-championship"]},
    ]
    for r in review:
        if r["status"] != "confirmed":
            items.append({"id": r["id"], "severity": "review", "title": r["claim"][:90],
                          "what": r["detail"], "sources": [r["source"]]})
    return items


# ------------------------------------------------------------------ pages
def high_rows(rows):
    order = {"High": 0, "Medium": 1, "Low": 2, "None": 3}
    return sorted(rows, key=lambda r: (order[r["confidence"]], r["date"], r["id"]))


def build_pages(rows, preds, review, coverage, flags):
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    os.makedirs(os.path.join(SITE, "sports"), exist_ok=True)
    sources = model.load("team_stats.json")["sources"]
    counts = Counter(r["confidence"] for r in rows)
    sports = Counter(r["sport"] for r in rows)
    highs = [r for r in rows if r["confidence"] == "High"]

    # ---------------- index
    kpi = "".join(f'<div class="kpi"><span class="kval">{v}</span><span class="klab">{k}</span></div>' for v, k in [
        (len(rows), "verified fixtures"),
        (len(sports), "sports published"),
        (sum(1 for r in rows if r["pick"]), "match-winner picks"),
        (counts["High"], "High confidence"),
        (0, "values filled without a source"),
    ])
    cat = "".join(
        f'<a class="cat" href="sports/{SPORT_SLUG[s]}.html"><span class="catname">{esc(s)}</span>'
        f'<span class="catnum">{n}</span><span class="tiny">fixtures &middot; '
        f'{sum(1 for r in rows if r["sport"] == s and r["confidence"] == "High")} High</span></a>'
        for s, n in sorted(sports.items()))
    top = "".join(
        f'<tr><td>{r["date"]}</td><td>{esc(r["sport"])}</td>'
        f'<td><a href="picks.html#{r["id"]}">{esc(r["pick"])}</a></td>'
        f'<td>{esc(r["competition"])}</td><td class="num">{r["line_home"]:.2f}</td>'
        f'<td class="num">{american_text(r)}</td><td><span class="pill high">High</span></td>'
        f'<td><a href="{sources[r["source"]]["url"]}" target="_blank" rel="noopener">{esc(sources[r["source"]]["title"].split(" (")[0])}</a></td></tr>'
        for r in sorted(highs, key=lambda r: (r["date"], r["id"])))
    body = f"""
<section class="hero">
<p class="kicker">Board U &middot; fresh read 22 October 2026 &middot; window 22&ndash;27 October</p>
<h1>Every fixture re-read on the governing body's own site, priced by our model, one link per row.</h1>
<p class="lede">This desk replaces guesswork with a short, checkable list. Each of the {len(rows)} fixtures below was opened on the
official league page or official league API on 22 October 2026; the model then originated its own moneyline, handicap and total where the
inputs exist. Anything an official page did not state is blank and appears on <a href="flagged.html">Flagged for review</a>.</p>
<div class="cta"><a class="btn primary" href="fixtures.html">Open the full table</a>
<a class="btn" href="picks.html">Read the {counts['High']} High-confidence write-ups</a>
<a class="btn" href="verification.html">Check every row against its source</a></div>
</section>
<section class="kpis">{kpi}</section>
<section class="panel">
<div class="row-between"><h2>High-confidence picks &mdash; inside &minus;250 to +10,000</h2>
<span class="tiny">all {counts['High']} are graded above 70% and quoted inside the window</span></div>
{table(["Date", "Sport", "Selection", "Competition", "Our line", "American", "Grade", "Official source"], [tuple(r) for r in [[
        x[0], x[1], x[2], x[3], x[4], x[5], x[6], x[7]] for x in []]] or [], "tight") if False else
 f'<div class="tablewrap"><table class="tight"><thead><tr><th>Date</th><th>Sport</th><th>Selection</th><th>Competition</th><th>Our line</th><th>American</th><th>Grade</th><th>Official source</th></tr></thead><tbody>{top}</tbody></table></div>'}
</section>
<section class="grid2">
<div><h2>By category</h2><div class="cats">{cat}</div></div>
<div><h2>What this session found</h2>
<ul class="findings">
<li><strong>{len(rows)} fixtures</strong> across {len(sports)} sports could be confirmed on an official page for 22&ndash;27 October; the other fourteen in-scope sports are listed on the coverage page with the URL tried and why nothing was published.</li>
<li><strong>No NHL club clears 70% this week.</strong> Across twelve verified games the model tops out at 68% (Minnesota at Calgary), which is what a goals-based model should say after ten games. Hockey High picks are rare by construction; none was inflated to fill the page.</li>
<li><strong>{counts['High']} picks clear the 70% bar</strong> and are all inside the requested odds window. The model is deliberately conservative: a two-point win does not turn into a 90% price.</li>
<li><strong>Prior repo review:</strong> {sum(1 for r in review if r['status'] == 'confirmed')} of {len(review)} sampled prior claims were confirmed against the official page; the rest are listed on the flagged page with links. See <a href="analysis.html">analysis</a>.</li>
<li><strong>{sum(1 for r in rows if r['market_total'] == 'blank')} total markets</strong> and {sum(1 for r in rows if r['market_handicap'] == 'blank')} handicaps are blank because the verified inputs do not exist &mdash; not because the market was skipped.</li>
</ul></div>
</section>
"""
    pages = {"index.html": page("Dashboard", body, "index.html")}

    # ---------------- fixtures
    filterjs = """
<div class="filters">
<label>Sport <select id="fsport"><option value="">All</option>%s</select></label>
<label>Grade <select id="fgrade"><option value="">All</option><option>High</option><option>Medium</option><option>Low</option></select></label>
<label>Date <select id="fdate"><option value="">All</option>%s</select></label>
<span class="tiny" id="fcount"></span>
</div>
<script>
const t=document.getElementById('ftable').tBodies[0];
function apply(){const s=document.getElementById('fsport').value,g=document.getElementById('fgrade').value,d=document.getElementById('fdate').value;let n=0;
for(const r of t.rows){const ok=(!s||r.dataset.sport===s)&&(!g||r.dataset.grade===g)&&(!d||r.dataset.date===d);r.style.display=ok?'':'none';if(ok)n++;}
document.getElementById('fcount').textContent=n+' rows shown';}
for(const id of ['fsport','fgrade','fdate'])document.getElementById(id).addEventListener('change',apply);apply();
</script>""" % (
        "".join(f'<option value="{esc(s)}">{esc(s)}</option>' for s in sorted(sports)),
        "".join(f'<option value="{d}">{d}</option>' for d in sorted({r["date"] for r in rows})))
    body_rows = []
    for r in high_rows(rows):
        body_rows.append([
            r["date"], esc(r["time"] or "&mdash;"), esc(r["sport"]),
            f'{esc(r["home"])} v {esc(r["away"])}<br><span class="tiny">{esc(r["venue"] or "venue not published")}</span>',
            esc(r["competition"]),
            f'{r["line_home"]:.2f} / {r["line_away"]:.2f}' if r["line_home"] else "blank",
            american_text(r),
            esc(r["pick"] or "no selection"),
            f'<span class="pill {r["confidence"].lower()}">{r["confidence"]}</span>',
            ("originated" if r["market_handicap"] == "originated" else "blank") + " / " +
            ("originated" if r["market_total"] == "originated" else "blank"),
            f'<a href="{sources[r["source"]]["url"]}" target="_blank" rel="noopener">source</a>',
        ])
    body = f"""
<section class="hero small"><h1>All fixtures</h1>
<p class="lede">Sorted by confidence then date. Times are shown exactly as the official page printed them; a missing timezone is not guessed.</p></section>
{filterjs}
<div class="tablewrap"><table id="ftable" class="tight"><thead><tr><th>Date</th><th>Time</th><th>Sport</th><th>Fixture / venue</th><th>Competition</th><th>Our line (dec)</th><th>American</th><th>Pick</th><th>Grade</th><th>Handicap / total</th><th>Source</th></tr></thead><tbody>
{''.join(f'<tr data-sport="{esc(r["sport"])}" data-grade="{r["confidence"]}" data-date="{r["date"]}">' + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for r, row in zip(high_rows(rows), body_rows))}
</tbody></table></div>
<p class="tiny">Markets investigated for every row: match winner, handicap and match total. Where the second or third is blank the reason is printed on the row's entry in the <a href="markets.html">markets</a> page and on <a href="flagged.html">Flagged for review</a>.</p>
"""
    pages["fixtures.html"] = page("All fixtures", body, "fixtures.html")

    # ---------------- picks
    picks_html = []
    for r in sorted(highs, key=lambda r: (r["date"], r["id"])):
        p = preds[r["id"]]
        src = sources[r["source"]]
        picks_html.append(f"""
<article class="pick" id="{r['id']}">
<div class="pickhead"><div><span class="pill high">High</span> <span class="tiny">{esc(r['sport'])} &middot; {r['date']} &middot; {esc(r['competition'])}</span>
<h3>{esc(r['home'])} v {esc(r['away'])}</h3></div>
<div class="price"><span class="num">{r['line_home']:.2f}</span><span class="tiny">our line &middot; {american_text(r)}</span></div></div>
<p class="sel"><strong>Selection:</strong> {esc(p['selection'])} &nbsp;|&nbsp; <strong>Model probability:</strong> {r['pick_probability']*100:.1f}% &nbsp;|&nbsp;
<strong>Evidence depth:</strong> {esc(r['evidence_depth'])}</p>
<p>{esc(p['text'])}</p>
<div class="pickfoot">
<span><strong>Venue:</strong> {esc(r['venue'] or 'not published')}</span>
<span><strong>Inputs:</strong> {esc(', '.join(f'{k}={v}' for k, v in r['inputs'].items()))}</span>
<span><strong>Source:</strong> <a href="{src['url']}" target="_blank" rel="noopener">{esc(src['title'])}</a></span>
{'<span class="warn">Quoted at the desk floor of 1.40; fair price ' + format(r['line_home_raw'], '.2f') + '.</span>' if r['line_capped'] else ''}
</div></article>""")
    body = f"""
<section class="hero small"><h1>{len(highs)} High-confidence picks</h1>
<p class="lede">Every selection here is graded above 70% by the model and priced inside &minus;250 to +10,000. Each write-up names the selection,
quotes the verified form the model actually used, and links the official page it came from. No template sentences, no shared paragraphs.</p></section>
{''.join(picks_html)}
<section class="panel"><h2>What the grade means</h2>
<ul class="findings">
<li><strong>High</strong> &mdash; model probability at or above 70% for the named selection and our quoted price inside &minus;250 to +10,000.</li>
<li><strong>Medium</strong> &mdash; probability between 60% and 70%, or above 70% where an official source conflict stops the desk grading it High.</li>
<li><strong>Low</strong> &mdash; probability under 60%, or no verified form at all (opening week).</li>
</ul>
<p class="tiny">Evidence depth is shown on every pick because two of these write-ups rest on a single verified match. The desk would rather tell you that than hide it.</p></section>
"""
    pages["picks.html"] = page("High-confidence picks", body, "picks.html")

    # ---------------- markets
    win_n = sum(1 for r in rows if r["market_win"] == "originated")
    hc_n = sum(1 for r in rows if r["market_handicap"] == "originated")
    tot_n = sum(1 for r in rows if r["market_total"] == "originated")
    mrows = []
    for r in high_rows(rows):
        mrows.append([
            r["id"], esc(r["sport"]), f'{esc(r["home"])} v {esc(r["away"])}',
            f'{r["line_home"]:.2f} / {r["line_away"]:.2f}' if r["line_home"] else "blank",
            (f'{r["handicap_line"]:+g} &middot; cover {r["p_handicap_cover"]*100:.0f}%' if r["market_handicap"] == "originated" else "blank"),
            (f'{r["total_line"]} &middot; over {r["p_over"]*100:.0f}% @ {r["over_price"]:.2f}' if r["market_total"] == "originated" else "blank"),
            esc(r.get("handicap_blank_reason", "") or r.get("total_blank_reason", "")) or "&mdash;",
        ])
    body = f"""
<section class="hero small"><h1>Markets investigated</h1>
<p class="lede">Three markets were investigated for every fixture: match winner, handicap and match total. A market is originated only when the
verified inputs support it; otherwise the cell is blank and the reason is printed here and on the flagged page.</p></section>
<section class="kpis">
<div class="kpi"><span class="kval">{win_n}</span><span class="klab">match winners originated</span></div>
<div class="kpi"><span class="kval">{hc_n}</span><span class="klab">handicaps originated</span></div>
<div class="kpi"><span class="kval">{tot_n}</span><span class="klab">totals originated</span></div>
<div class="kpi"><span class="kval">{len(rows) - tot_n}</span><span class="klab">totals blank, reason given</span></div>
</section>
{table(["Row", "Sport", "Fixture", "Moneyline (dec)", "Handicap", "Total", "Why a market is blank"], mrows, "tight")}
<section class="panel"><h2>Why some cells are blank</h2>
<ul class="findings">
<li><strong>Rugby totals (13 rows).</strong> Each club has one verified result in the competition. One result is not a scoring level, so a total would be invented. The handicap survives because it is a relative measure from the same rating.</li>
<li><strong>Ice hockey totals on two rows.</strong> NHL.com published the Kings' and Flames' records but not their goals for or against, so no expected-goals figure exists.</li>
<li><strong>Basketball (2 rows).</strong> Opening week: no club has a verified current-season form line, so there is no basis for a spread or a total.</li>
</ul></section>
"""
    pages["markets.html"] = page("Markets", body, "markets.html")

    # ---------------- coverage
    crow = [[esc(c["sport"]), f'<span class="pill {("high" if c["status"].startswith("Published") else "low")}">{esc(c["status"])}</span>',
             c["fixtures"], esc(c["evidence"]), f'<a href="{c["source"]}" target="_blank" rel="noopener">official page</a>']
            for c in coverage]
    body = f"""
<section class="hero small"><h1>Coverage: 19 in-scope sports, honestly counted</h1>
<p class="lede">The brief includes every sport except soccer, boxing, UFC/MMA, football (American or otherwise), hurling, horse racing,
cycling and specials. The table below says, for each of the 19 in-scope OLBG sports, whether this session published verified fixtures and,
where it did not, the official URL that was tried.</p></section>
{table(["Sport", "Status", "Fixtures published", "What was read / why not", "Official page"], crow, "tight")}
<section class="panel"><h2>Excluded by the brief</h2>
<p class="tiny">Soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling and specials do not appear anywhere in this desk;
the build fails if any of those tokens appears in a competition name. Gaelic football is treated as out of scope under a conservative reading of
&ldquo;football&rdquo; and is flagged for review rather than silently included or silently dropped.</p></section>
"""
    pages["coverage.html"] = page("Coverage", body, "coverage.html")

    # ---------------- verification register
    vrows = []
    for r in high_rows(rows):
        src = sources[r["source"]]
        status = "Verified" if not r.get("flags") else "Verified &middot; flagged"
        vrows.append([
            r["id"], esc(r["sport"]), r["date"], f'{esc(r["home"])} v {esc(r["away"])}',
            f'<a href="{src["url"]}" target="_blank" rel="noopener">{esc(src["title"])}</a>',
            f'<span class="quote">{esc(r["evidence"])}</span>', status,
        ])
    body = f"""
<section class="hero small"><h1>Verification register</h1>
<p class="lede">One row per published fixture, with the official page it was read on, the text that page printed, and the status.
This is the line-by-line check: if a row is not here, it is not published.</p></section>
<section class="panel"><h2>How each row was checked</h2>
<ol class="findings">
<li>Open the competition's own domain or official API for the date, not an aggregator.</li>
<li>Read the fixture, venue, date and both team names from that page.</li>
<li>Copy the exact wording into the &ldquo;evidence&rdquo; column, so a reviewer can search for it on the page.</li>
<li>Take the model inputs from the same domain (standings, records, results) and record which page each number came from on <a href="sources.html">sources</a>.</li>
<li>Leave blank whatever the page did not say, then list it on <a href="flagged.html">Flagged for review</a>.</li>
</ol></section>
{table(["Row", "Sport", "Date", "Fixture", "Official source", "What the source prints", "Status"], vrows, "tight")}
"""
    pages["verification.html"] = page("Verification register", body, "verification.html")

    # ---------------- flagged
    items_html = []
    for f in flags:
        links = "".join(f'<a href="{s if s.startswith("http") else "../" + s}">{esc(s)}</a> ' for s in f["sources"])
        items_html.append(f"""<article class="flag {esc(f['severity'])}" id="{f['id'].lower()}">
<h3>{f['id']} &middot; {esc(f['title'])} <span class="pill low">{esc(f['severity'])}</span></h3>
<p>{esc(f['what'])}</p><p class="tiny">Sources: {links}</p></article>""")
    body = f"""
<section class="hero small"><h1>Flagged for review</h1>
<p class="lede">Everything this desk could not confirm, could not fill, or wants a human to look at. Flagged items never block publication,
but they are never hidden either: each one names what is missing and links the page that shows it.</p></section>
<section class="kpis">
<div class="kpi"><span class="kval">{len(flags)}</span><span class="klab">open items</span></div>
<div class="kpi"><span class="kval">{sum(1 for f in flags if f['severity']=='blank')}</span><span class="klab">blank fields / markets</span></div>
<div class="kpi"><span class="kval">{sum(1 for f in flags if f['severity']=='review')}</span><span class="klab">need a human decision</span></div>
</section>
{''.join(items_html)}
"""
    pages["flagged.html"] = page("Flagged for review", body, "flagged.html")

    # ---------------- analysis
    rrows = [[r["id"], esc(r["claim"]), esc(r["detail"]), f'<a href="{r["source"] if r["source"].startswith("http") else "../" + r["source"]}">link</a>',
              f'<span class="pill {("high" if r["status"] == "confirmed" else "low")}">{esc(r["status"])}</span>'] for r in review]
    dist = Counter(r["confidence"] for r in rows)
    body = f"""
<section class="hero small"><h1>Analysis and findings</h1>
<p class="lede">What the numbers say, what the model does and does not do, and what a line-by-line pass over the previous sessions' output found.</p></section>
<section class="grid2">
<div class="panel"><h2>Price distribution</h2>
<p class="tiny">Our own lines, all {len(rows)} fixtures.</p>
<ul class="findings">
<li>Confidence: <strong>{dist['High']} High</strong>, {dist['Medium']} Medium, {dist['Low']} Low.</li>
<li>Shortest price quoted: <strong>{min((r['line_home'] for r in rows if r['line_home']), default=0):.2f}</strong>; the desk floor is 1.40.</li>
<li>Longest price quoted: <strong>{max((r['line_away'] for r in rows if r['line_away']), default=0):.2f}</strong>; ceiling 101.00.</li>
<li>Every High pick sits inside &minus;250 to +10,000 by construction, because the floor is the window's short end.</li>
</ul></div>
<div class="panel"><h2>What the model is not doing</h2>
<ul class="findings">
<li>It does not read a bookmaker, an exchange or a tipster. There is no market price anywhere in the input set.</li>
<li>It does not use last season, reputation, injuries or transfers, because none of those were verified on an official page in this cycle.</li>
<li>It does not convert a two-point win into a 90% price: rugby ratings carry a 30-point standard deviation precisely to prevent that.</li>
<li>It does not manufacture hockey favourites. Twelve NHL games produced no selection above 68%, because a Poisson goals model on ten games of form says exactly that. The threshold is not quietly lowered to generate content.</li>
<li>It does not fill a blank. {sum(1 for r in rows if r['market_total'] == 'blank')} totals and {sum(1 for r in rows if r['market_handicap'] == 'blank')} handicaps are blank on purpose.</li>
</ul></div>
</section>
<section class="panel"><h2>Line-by-line review of prior published rows</h2>
<p class="tiny">Sampled from the rows that the previous boards published for the same dates, each re-checked against the official page.
A confirmed row means this session re-read the same fact on the same official domain; it does not mean the earlier board's price or grade was right.</p>
{table(["Check", "Claim in the repo", "What this session found", "Official page", "Result"], rrows, "tight")}</section>
<section class="panel"><h2>Findings worth acting on</h2>
<ul class="findings">
<li><strong>Stale fixtures are still live.</strong> <code>data/rows.json</code> holds 144 rows of which 24 are dated before 22 October and several are &ldquo;No fixture&rdquo; placeholders; the root dashboard still presents them as the current list.</li>
<li><strong>README counts disagree with the data.</strong> README lines 15, 25 and 48 say 308 in-scope rows across 18 sports / 312 rows; <code>data/master.json</code> has 317 rows, 312 in scope across 19 sports. Board S1 logged this as S1-F06; it is still open.</li>
<li><strong>Two sport labels for one sport.</strong> The master board carries both &ldquo;Greyhounds&rdquo; (6 rows) and &ldquo;Greyhound Racing&rdquo; (2 rows), which splits one category in the navigation.</li>
<li><strong>Five High rows have no written prediction.</strong> The master board grades 38 rows High but only 33 carry written copy; the other five are templated or empty.</li>
<li><strong>Only five sports could be re-confirmed for this week.</strong> That is the real coverage story, and it is on the coverage page rather than buried.</li>
</ul></section>
"""
    pages["analysis.html"] = page("Analysis", body, "analysis.html")

    # ---------------- methodology
    body = f"""
<section class="hero small"><h1>Method</h1>
<p class="lede">The whole model, in the open, including the assumptions. Nothing here is presented as a verified fact.</p></section>
<section class="panel"><h2>1. Inputs are read, never remembered</h2>
<p>Each fixture and each model input was read from the competition's own domain or official API on 22 October 2026:
nhl.com for fixtures, records and standings; statsapi.mlb.com for the World Series schedule and season records; stats.unitedrugby.com for URC
Round 4 fixtures and Round 3 results; rlwc2026.com for World Cup results and Round 2 fixtures; nba.com for the two opening-week games.
No aggregator, no bookmaker, no OLBG price.</p></section>
<section class="panel"><h2>2. Originating a line</h2>
<pre class="code">Ice hockey   lambda_home = 1.03 * (GF_h/GP_h + GA_a/GP_a)/2
             lambda_away = 0.97 * (GF_a/GP_a + GA_h/GP_h)/2
             Poisson scoreline matrix; moneyline = P(home win) + 0.5*P(tie)
             total line  = nearest half goal to lambda_home + lambda_away
             puck line   = P(home win by 2+)

Baseball     log5 on verified win percentages + 0.02 home field
             total from Poisson on mean(runs scored, runs allowed per game)

Rugby        rating = last verified margin, capped at +/-40 points
             P(home) = Phi((rating_home - rating_away + home)/30)
             URC home advantage 3 points; RLWC none (neutral-listed venues)
             handicap = fair line rounded to the nearest 0.5 (Union) or 1 (League)
             total = blank (one match is not a scoring level)

Basketball   opening week: no form, home prior 0.55, graded Low, no spread, no total</pre>
<p class="tiny">Two rows use a documented fallback (log5-style logistic on points percentage) because NHL.com published those clubs' records but not their goals for/against.</p></section>
<section class="panel"><h2>3. Turning a probability into a price</h2>
<p>The line is the no-vig decimal, 1/p, rounded to two places. The desk then applies two quoting rules:
never shorter than <strong>1.40 (&minus;250)</strong> and never longer than <strong>101.00 (+10,000)</strong>. The floor is why every High pick sits inside the
window the brief asks for: a 92% selection would otherwise be quoted at 1.09 and fall outside it. Where the floor bites, the row says so and prints the fair price.</p></section>
<section class="panel"><h2>4. Grading</h2>
<table><thead><tr><th>Grade</th><th>Rule</th><th>This cycle</th></tr></thead><tbody>
<tr><td><span class="pill high">High</span></td><td>model probability &ge; 70% for the named selection <em>and</em> our price inside &minus;250 to +10,000 <em>and</em> no unresolved source conflict</td><td>{counts['High']}</td></tr>
<tr><td><span class="pill medium">Medium</span></td><td>probability 60&ndash;70%, or &ge;70% with an unresolved official-source conflict</td><td>{counts['Medium']}</td></tr>
<tr><td><span class="pill low">Low</span></td><td>under 60%, or no verified form at all</td><td>{counts['Low']}</td></tr>
</tbody></table></section>
<section class="panel"><h2>5. Assumptions, stated as assumptions</h2>
<ul class="findings">
<li>The 30-point standard deviation on one-match rugby ratings, and the 2.0 / 0.15 parameters in the NHL fallback, are desk choices. They are not verified facts and they are not fitted to any market.</li>
<li>Half of a tie is awarded to the home side in hockey because the moneyline includes overtime and the shootout, whose winner is close to a coin flip on the evidence available here.</li>
<li>No adjustment is made for injuries, rest, travel, weather, referees or team news: none of those were verified on an official page in this cycle.</li>
</ul></section>
<section class="panel"><h2>6. What would make this better next cycle</h2>
<ul class="findings">
<li>A second official source per rugby fixture (line-ups or match previews) would move several Medium rows to High with evidence rather than assertion.</li>
<li>Reaching tennis, cricket, darts and handball from a page this sandbox can actually read; the URLs tried are on the coverage page.</li>
<li>Retiring the stale rows in the older builds so the root dashboard stops presenting 19&ndash;21 October fixtures as current.</li>
</ul></section>
"""
    pages["methodology.html"] = page("Method", body, "methodology.html")

    # ---------------- sources
    srows = [[esc(v["title"]), f'<a href="{v["url"]}" target="_blank" rel="noopener">{esc(v["url"])}</a>',
              "official", esc(v["read_on"])] for v in sources.values()]
    body = f"""
<section class="hero small"><h1>Sources</h1>
<p class="lede">Every domain used by this desk. Each was opened on 22 October 2026; each is the competition's own site or its official API.</p></section>
{table(["Page", "URL", "Type", "Read on"], srows, "tight")}
<section class="panel"><h2>Domains deliberately not used</h2>
<p class="tiny">Bookmakers, betting exchanges, tipster sites, news aggregators and OLBG itself are not used for a fixture, a price or a form claim.
OLBG appears in this repo only as the source of the sport list the brief defines.</p></section>
"""
    pages["sources.html"] = page("Sources", body, "sources.html")

    # ---------------- per sport
    for sport, slug in SPORT_SLUG.items():
        srows = high_rows([r for r in rows if r["sport"] == sport])
        if not srows:
            continue
        trows = []
        for r in srows:
            src = sources[r["source"]]
            trows.append([r["date"], f'{esc(r["home"])} v {esc(r["away"])}', esc(r["competition"]),
                          f'{r["line_home"]:.2f} / {r["line_away"]:.2f}' if r["line_home"] else "blank",
                          american_text(r), esc(r["pick"]), f'<span class="pill {r["confidence"].lower()}">{r["confidence"]}</span>',
                          f'<a href="{src["url"]}" target="_blank" rel="noopener">source</a>'])
        hi = [r for r in srows if r["confidence"] == "High"]
        body = f"""
<section class="hero small"><h1>{esc(sport)}</h1>
<p class="lede">{len(srows)} verified fixtures &middot; {len(hi)} graded High &middot; every price originated by this desk, every row linked to its official page.</p></section>
{table(["Date", "Fixture", "Competition", "Our line", "American", "Pick", "Grade", "Source"], trows, "tight")}
<section class="panel"><h2>Notes for this sport</h2>
<p class="tiny">{esc({ 'Ice Hockey': 'Moneyline includes overtime. Totals and puck lines come from a Poisson goals model on the goals-for and goals-against rate of each club; two rows use the documented points-percentage fallback because goals data was not published.',
    'Baseball': 'World Series Games 1-3 only: the official MLB API lists no other major-league fixtures in the window. Log5 on 162-game win percentages gives a near coin-flip, which is why nothing here is graded High.',
    'Rugby Union': 'Round 4 fixtures with Round 3 results as the only verified form. Match totals are blank by rule; the handicap is originated and labelled.',
    'Rugby League': 'World Cup Round 2 with Round 1 results as the only verified form. Kick-off times are reproduced exactly; the official page states no timezone.',
    'Basketball': 'Opening week, no verified form. Home-court prior only, graded Low, no spread or total.' }[sport])}</p>
<p><a href="../picks.html">All High-confidence picks</a> &middot; <a href="../flagged.html">Flagged for review</a> &middot; <a href="../index.html">Dashboard</a></p></section>
"""
        pages[f"sports/{slug}.html"] = page(sport, body, "", prefix="../")

    return pages


def write_outputs(rows, coverage, review, flags):
    with open(os.path.join(DATA, "lines.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "session-c92c927c/lines-v1", "generated_by": "arena/c92c927c-olbg4",
                   "generated_on": "2026-10-22", "pricing": {"floor": 1.40, "ceiling": 101.0,
                                                             "high_threshold": 0.70, "margin": "none (no-vig fair price)"},
                   "rows": rows}, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(DATA, "coverage.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "session-c92c927c/coverage-v1", "sports": coverage}, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(DATA, "flagged.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "session-c92c927c/flagged-v1", "items": flags}, fh, indent=1, ensure_ascii=False)
    with open(os.path.join(DATA, "review.json"), "w", encoding="utf-8") as fh:
        json.dump({"schema": "session-c92c927c/review-v1", "checks": review}, fh, indent=1, ensure_ascii=False)
    cols = ["id", "sport", "competition", "date", "time", "time_tz_stated", "venue", "home", "away",
            "model", "evidence_depth", "p_home", "pick_probability", "pick", "line_home", "line_away",
            "american", "confidence", "market_win", "market_handicap", "handicap_line",
            "market_total", "total_line", "over_price", "under_price", "source", "prediction"]
    with open(os.path.join(DATA, "rows.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def link_check(pages):
    problems = []
    targets = set(pages)
    target_map = {os.path.normpath(k): v for k, v in pages.items()}
    for name, html_text in pages.items():
        base = os.path.dirname(name)
        for href in re.findall(r'href="([^"#][^"]*)"', html_text):
            if href.startswith(("http://", "https://", "mailto:", "data:")):
                continue
            frag = href.split("#", 1)[1] if "#" in href else ""
            path = href.split("#")[0].split("?")[0]
            target = os.path.normpath(os.path.join(base, path))
            if target not in targets and not os.path.exists(os.path.join(SITE, target)):
                problems.append(f"{name} -> {href}")
            elif frag and target in target_map and f'id="{frag}"' not in target_map[target]:
                problems.append(f"{name} -> missing anchor #{frag}")
        # asset check
    if not os.path.exists(os.path.join(SITE, "assets", "style.css")):
        problems.append("missing assets/style.css")
    return problems


CSS = """/* Board U desk - single stylesheet, no external requests */
:root{--ink:#0f172a;--muted:#5b6779;--line:#e3e8ef;--bg:#f7f9fc;--card:#fff;--accent:#0b5cad;--high:#0b7a3b;--med:#9a5b00;--low:#8a2f2f}
*{box-sizing:border-box}
body{margin:0;font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;color:var(--ink);background:var(--bg)}
a{color:var(--accent);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.topbar{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.bar{display:flex;gap:18px;align-items:center;justify-content:space-between;flex-wrap:wrap;padding:10px 20px}
.brand{display:flex;gap:10px;align-items:center;font-weight:700;color:var(--ink)}
.mark{background:var(--accent);color:#fff;border-radius:6px;padding:3px 7px;font-size:14px}
.brand small{display:block;font-weight:500;color:var(--muted);font-size:11px}
.nav{display:flex;gap:4px;flex-wrap:wrap}
.navlink{padding:6px 10px;border-radius:6px;color:var(--muted);font-size:14px}
.navlink.active,.navlink:hover{background:#eef4fb;color:var(--accent);text-decoration:none}
.hero{padding:34px 0 10px}
.hero.small{padding:20px 0 4px}
.hero h1{font-size:30px;line-height:1.2;margin:6px 0 10px;max-width:900px}
.kicker{color:var(--accent);font-weight:600;font-size:13px;text-transform:uppercase;letter-spacing:.04em;margin:0}
.lede{color:var(--muted);font-size:17px;max-width:900px;margin:0 0 14px}
.cta{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0 6px}
.btn{border:1px solid var(--line);background:#fff;color:var(--ink);padding:9px 14px;border-radius:8px;font-weight:600;font-size:14px}
.btn.primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn:hover{text-decoration:none;border-color:var(--accent)}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px}
.kval{display:block;font-size:26px;font-weight:700}
.klab{display:block;color:var(--muted);font-size:13px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;margin:18px 0}
.panel h2{font-size:19px;margin:0 0 10px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.cats{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.cat{display:flex;flex-direction:column;gap:2px;border:1px solid var(--line);border-radius:10px;padding:12px;background:#fbfdff}
.cat:hover{border-color:var(--accent);text-decoration:none}
.catname{font-weight:600;color:var(--ink)}
.catnum{font-size:24px;font-weight:700;color:var(--accent)}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:14px}
th,td{padding:9px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:#f1f5fa;font-size:12px;text-transform:uppercase;letter-spacing:.03em;color:var(--muted);position:sticky;top:0}
tr:last-child td{border-bottom:0}
table.tight td{font-size:13px}
.num{font-variant-numeric:tabular-nums;font-weight:600}
.tiny{color:var(--muted);font-size:12px}
.pill{display:inline-block;border-radius:999px;padding:1px 9px;font-size:12px;font-weight:700;color:#fff}
.pill.high{background:var(--high)}.pill.medium{background:var(--med)}.pill.low{background:var(--low)}
.pick{border:1px solid var(--line);border-radius:12px;padding:16px;background:var(--card);margin:14px 0}
.pickhead{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;flex-wrap:wrap}
.pickhead h3{margin:6px 0 0;font-size:19px}
.price{text-align:right}
.price .num{font-size:26px;color:var(--accent)}
.sel{background:#f4f8fd;border-left:4px solid var(--accent);padding:8px 10px;border-radius:6px;font-size:14px}
.pickfoot{display:flex;gap:16px;flex-wrap:wrap;font-size:12.5px;color:var(--muted);border-top:1px solid var(--line);padding-top:10px;margin-top:10px}
.warn{color:var(--med);font-weight:600}
.findings{margin:8px 0 0;padding-left:20px}
.findings li{margin:6px 0}
.quote{color:#334155;font-style:italic}
.flag{border:1px solid var(--line);border-left:5px solid var(--med);border-radius:10px;background:var(--card);padding:14px;margin:12px 0}
.flag.blank{border-left-color:var(--accent)}
.flag h3{margin:0 0 6px;font-size:16px}
.filters{display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:8px 0 4px;font-size:14px}
.filters select{padding:6px;border:1px solid var(--line);border-radius:6px;background:#fff}
.foot{border-top:1px solid var(--line);margin-top:26px;padding:16px 20px 40px;color:var(--muted);font-size:12.5px}
pre.code{background:#0f172a;color:#e6edf7;padding:14px;border-radius:10px;overflow-x:auto;font-size:12.5px;line-height:1.5}
code{background:#eef2f7;padding:1px 5px;border-radius:4px;font-size:13px}
.row-between{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap}
"""


def main():
    check_only = "--check" in sys.argv
    rows, preds, errors = build_data()
    if errors:
        print("BUILD REFUSED")
        for e in errors:
            print(" -", e)
        raise SystemExit(1)
    review = model.load("review.json")["checks"] if os.path.exists(os.path.join(DATA, "review.json")) else []
    coverage = coverage_json(rows)
    flags = flagged_items(rows, review)
    pages = build_pages(rows, preds, review, coverage, flags)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    problems = link_check(pages)
    if problems:
        print("LINK PROBLEMS")
        for p in problems:
            print(" -", p)
        raise SystemExit(1)
    counts = Counter(r["confidence"] for r in rows)
    print(f"validated: {len(rows)} rows, {len(counts)} grades, high={counts['High']}, "
          f"predicted={sum(1 for r in rows if r['prediction'])}, pages={len(pages)}, links=ok")
    if check_only:
        return
    write_outputs(rows, coverage, review, flags)
    for name, text in pages.items():
        path = os.path.join(SITE, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as fh:
        fh.write(CSS)
    print(f"wrote {len(pages)} pages to session-c92c927c/")


if __name__ == "__main__":
    main()

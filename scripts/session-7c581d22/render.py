#!/usr/bin/env python3
"""Board AD site renderer: data/session-7c581d22/board.json -> session-7c581d22/*.html
Deterministic, no timestamps beyond the capture date. Run after build.py."""
import html, json, os
from collections import Counter

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
B = json.load(open(os.path.join(ROOT, "data", "session-7c581d22", "board.json")))
SRC = json.load(open(os.path.join(ROOT, "data", "session-7c581d22", "sources.json")))["sources"]
OUT = os.path.join(ROOT, "session-7c581d22")
ROWS = B["rows"]; FOCUS = B["focus_picks"]; HIGH_OUT = B["high_shorter_than_minus250"]
def e(x): return html.escape(str(x), quote=True)
def am(v): return f"{v:+d}" if isinstance(v, int) and v > 0 else str(v)
SPORT_PAGE = {"Ice Hockey": "sport-ice-hockey.html", "Basketball": "sport-basketball.html",
              "Baseball": "sport-baseball.html", "Darts": "sport-darts.html",
              "Tennis": "sport-tennis.html", "eSports": "sport-esports.html"}

NAV = [("index.html", "Dashboard"), ("entries.html", "All entries"), ("picks.html", "Focus picks"),
       ("markets.html", "Markets"), ("coverage.html", "Coverage"), ("methodology.html", "Methodology"),
       ("sources.html", "Sources"), ("verification.html", "Verification"), ("flagged.html", "Flagged for Review")]
SPORT_NAV = [(v, k) for k, v in SPORT_PAGE.items()]

def page(title, body, active=""):
    nav = "".join(f'<a href="{h}"{" class=active" if h==active else ""}>{t}</a>' for h, t in NAV)
    snav = "".join(f'<a href="{h}"{" class=active" if h==active else ""}>{t}</a>' for h, t in SPORT_NAV)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} — OLBG4 Board AD</title><link rel="stylesheet" href="style.css"></head>
<body><header><div class="wrap"><h1>OLBG4 — Board AD</h1>
<p class="sub">Fresh-window desk, 23 Oct – 5 Nov 2026 · fixtures read 22 Oct 2026 from official league sources ·
all prices are our own originated fair prices (no bookmaker or OLBG price read)</p>
<nav>{nav}</nav><nav class="sports">{snav}</nav></div></header>
<main class="wrap">{body}</main>
<footer><div class="wrap"><p>Board AD · session <code>arena/7c581d22-olbg4</code> · data:
<code>data/session-7c581d22/board.json</code> · rebuild:
<code>python3 scripts/session-7c581d22/build.py &amp;&amp; python3 scripts/session-7c581d22/render.py &amp;&amp; python3 scripts/session-7c581d22/verify.py</code></p>
<p>18+ · Originated fair prices for research only — not betting advice. If you gamble, gamble responsibly.</p></div></footer>
</body></html>"""

def conf_badge(c): return f'<span class="conf {c.lower()}">{c}</span>' if c else ""

def market_cells(r):
    """compact market summary for tables"""
    m = r["markets"]
    if r["status"] != "priced":
        return "<em>unpriced — see reason</em>"
    out = []
    if "moneyline" in m:
        mm = m["moneyline"]
        out.append(f"ML {e(r['side_a'])} {mm['a']['decimal']} ({am(mm['a']['american'])}) · {e(r['side_b'])} {mm['b']['decimal']} ({am(mm['b']['american'])})")
    for k in ("puck_line", "run_line"):
        if k in m:
            out.append(f"{'Puck' if k=='puck_line' else 'Run'} line fav -1.5 {m[k]['fav_minus']['decimal']} ({am(m[k]['fav_minus']['american'])}) · dog +1.5 {m[k]['dog_plus']['decimal']} ({am(m[k]['dog_plus']['american'])})")
    if "spread" in m:
        out.append(f"Spread {e(r['side_b'])} {m['spread']['home_line']:+.1f} {m['spread']['b']['decimal']} ({am(m['spread']['b']['american'])})")
    if "total" in m:
        t = m["total"]
        out.append(f"Total {t['line']}: O {t['over']['decimal']} ({am(t['over']['american'])}) · U {t['under']['decimal']} ({am(t['under']['american'])})")
    return "<br>".join(out)

def inputs_summary(r):
    i = r["inputs"]
    if r["sport"] in ("Ice Hockey", "Basketball", "Baseball"):
        a, b = i["away"], i["home"]
        bits_a = " · ".join(f"{k} {v}" for k, v in a.items() if k != "team")
        bits_b = " · ".join(f"{k} {v}" for k, v in b.items() if k != "team")
        return f"<b>{e(r['side_a'])}</b>: {e(bits_a)}<br><b>{e(r['side_b'])}</b>: {e(bits_b)}"
    return e(json.dumps(i))

def row_tr(r):
    pick = r["pick"]
    pick_html = (f"{e(pick['selection'])} — {pick['decimal']} ({am(pick['american'])}), p={pick['p']:.3f} {conf_badge(pick['confidence'])}"
                 if pick else "<em>no pick (unpriced)</em>")
    note = f"<br><small>{e(r['notes'])}</small>" if r.get("notes") else ""
    if r["status"] == "unpriced":
        note += f"<br><small><b>Unpriced:</b> {e(r['unpriced_reason'])}</small>"
    return (f"<tr><td>{e(r['date'])}<br><small>{e(r['start_utc'])}</small></td>"
            f"<td>{e(r['sport'])}<br><small>{e(r['competition'])}</small></td>"
            f"<td><b>{e(r['fixture'])}</b><br><small>{e(r['venue'])}</small></td>"
            f"<td>{market_cells(r)}</td><td>{pick_html}{note}</td>"
            f"<td><a href=\"{e(r['source_url'])}\">official source</a><br><small>{e(r['source_name'])}</small></td></tr>")

def table(rows):
    return ("<table><thead><tr><th>Date (official)</th><th>Sport / competition</th><th>Fixture</th>"
            "<th>Our originated fair prices</th><th>Match pick &amp; confidence</th><th>Source</th></tr></thead><tbody>"
            + "".join(row_tr(r) for r in rows) + "</tbody></table>")

# ---------------- index
by_sport = Counter(r["sport"] for r in ROWS)
priced = sum(r["status"] == "priced" for r in ROWS)
confc = Counter(r["pick"]["confidence"] for r in ROWS if r["pick"])
cards = "".join(
    f'<div class="card"><h3><a href="{SPORT_PAGE[s]}">{s}</a></h3><p class="big">{n}</p>'
    f'<p>fixtures · {sum(1 for r in ROWS if r["sport"]==s and r["status"]=="priced")} priced</p></div>'
    for s, n in sorted(by_sport.items()))
top_focus = "".join(
    f"<tr><td>{e(f['date'])}</td><td>{e(f['fixture'])}</td><td><b>{e(f['selection'])}</b></td>"
    f"<td>{f['decimal']} ({am(f['american'])}), p={f['p']:.3f}</td></tr>" for f in FOCUS)
body = f"""
<section class="hero"><h2>What this desk is</h2>
<p>Board AD reverse-engineered OLBG's sport coverage, dropped the excluded sports (soccer/football, boxing,
UFC/MMA, American football, hurling, horse racing, cycling, specials), and rebuilt the
<b>23 October – 5 November 2026</b> fixture list for everything left <b>from official league sources only</b>,
read on 22 October 2026. {len(ROWS)} fixtures are listed; {priced} carry our <b>own originated fair prices</b>
(match winner everywhere priced, plus puck/run lines, spreads and match totals where verified inputs support them).
Every priced match has a winner pick graded Low / Medium / High. Written predictions are published for the
{len(FOCUS)} selections that are both High confidence (model probability &ge; 70%) and inside the requested
&minus;250 to +10,000 price window.</p>
<p class="stats">{len(ROWS)} fixtures · {priced} priced · {len(ROWS)-priced} listed unpriced (verified fixture, no verified
strength input) · match picks: {confc.get('High',0)} High / {confc.get('Medium',0)} Medium / {confc.get('Low',0)} Low ·
{len(FOCUS)} focus predictions · {len(HIGH_OUT)} High moneyline picks shorter than &minus;250 (listed separately, <a href="picks.html">picks page</a>)</p></section>
<section><h2>By sport</h2><div class="cards">{cards}</div>
<p>Every other in-scope OLBG sport is accounted for — with the official source attempted and the reason it is
coverage-only — on the <a href="coverage.html">Coverage</a> page. Nothing is silently missing.</p></section>
<section><h2>Focus picks — High confidence inside &minus;250 to +10,000</h2>
<table><thead><tr><th>Date</th><th>Fixture</th><th>Selection</th><th>Our fair price</th></tr></thead><tbody>{top_focus}</tbody></table>
<p>Full written prediction, verified inputs and source under each card on the <a href="picks.html">Focus picks</a> page.</p></section>
<section><h2>Rules this desk follows</h2><ul>
<li><b>Official sources only.</b> Every table row links the official league/tour/federation page or API; payload hashes are pinned in <a href="sources.html">Sources</a>.</li>
<li><b>No inferred values.</b> If a number could not be confirmed officially, the cell is blank and the item is on <a href="flagged.html">Flagged for Review</a>.</li>
<li><b>Our prices only.</b> Decimal = 1 &divide; model probability, no margin; the model per sport is on <a href="methodology.html">Methodology</a>.</li>
<li><b>Checkable.</b> <code>verify.py</code> re-derives every price, grade and window test and re-hashes every payload — see <a href="verification.html">Verification</a>.</li>
</ul></section>"""
open(os.path.join(OUT, "index.html"), "w").write(page("Dashboard", body, "index.html"))

# ---------------- entries + sport pages
body = f"<h2>All entries — {len(ROWS)} fixtures, 23 Oct – 5 Nov 2026</h2>" \
       "<p>Prices are our originated fair prices. Unpriced rows are verified fixtures whose prices are deliberately blank (reason on the row).</p>" + table(ROWS)
open(os.path.join(OUT, "entries.html"), "w").write(page("All entries", body, "entries.html"))
for sport, fname in SPORT_PAGE.items():
    rs = [r for r in ROWS if r["sport"] == sport]
    detail = ""
    for r in rs:
        detail += (f"<article class='match'><h3>{e(r['fixture'])}</h3><p class='meta'>{e(r['date'])} · {e(r['start_utc'])} · "
                   f"{e(r['competition'])} · {e(r['venue'])}</p><p>{market_cells(r)}</p>"
                   f"<p>{(e(r['pick']['selection']) + ' — p=' + format(r['pick']['p'],'.3f') + ' ' + conf_badge(r['pick']['confidence'])) if r['pick'] else '<em>no pick — unpriced</em>'}</p>"
                   f"<details><summary>Verified inputs used</summary><p>{inputs_summary(r)}</p></details>"
                   + (f"<p><small>{e(r['notes'])}</small></p>" if r.get("notes") else "")
                   + (f"<p><small><b>Unpriced:</b> {e(r['unpriced_reason'])}</small></p>" if r["status"] == "unpriced" else "")
                   + f"<p><small>Source: <a href=\"{e(r['source_url'])}\">{e(r['source_name'])}</a> · row <code>{e(r['id'])}</code></small></p></article>")
    open(os.path.join(OUT, fname), "w").write(page(sport, f"<h2>{e(sport)} — {len(rs)} fixtures</h2>{detail}", fname))

# ---------------- picks
cards_html = ""
for f in FOCUS:
    r = next(x for x in ROWS if x["id"] == f["row_id"])
    cards_html += (f"<article class='pick'><h3>{e(f['selection'])}</h3>"
                   f"<p class='meta'>{e(f['date'])} · {e(f['fixture'])} · {e(f['competition'])} · market: {e(f['market'])}</p>"
                   f"<p class='price'>Our fair price <b>{f['decimal']}</b> ({am(f['american'])}) · model probability <b>{f['p']:.1%}</b> · {conf_badge('High')} · inside &minus;250…+10,000 ✓</p>"
                   f"<p class='pred'>{e(f['prediction'])}</p>"
                   f"<details><summary>Verified inputs behind this prediction</summary><p>{inputs_summary(r)}</p></details>"
                   f"<p><small>Source: <a href=\"{e(f['source_url'])}\">official source</a> · row <code>{e(f['row_id'])}</code></small></p></article>")
outside_rows = "".join(
    f"<tr><td>{e(h['date'])}</td><td>{e(h['fixture'])}</td><td>{e(h['selection'])}</td><td>p={h['p']:.3f}</td>"
    f"<td>{am(h['american'])}</td><td><a href=\"{e(h['source_url'])}\">official source</a></td></tr>" for h in HIGH_OUT)
body = f"""<h2>Focus picks — High confidence inside &minus;250 to +10,000 ({len(FOCUS)})</h2>
<p>A selection qualifies only if our model makes it at least a 70% chance <i>and</i> its fair American price is
&minus;250 or longer. At fair odds those two conditions overlap only between 70.0% and 71.4%
(<a href="flagged.html">AD-F01</a>), which is why the list is short and deliberate. Each card carries an original
written prediction (all over 100 words) using only the verified inputs printed beneath it.</p>{cards_html}
<h2>High confidence, but shorter than &minus;250 ({len(HIGH_OUT)} moneyline picks)</h2>
<p>These clear the 70% bar comfortably but price outside the requested window, so per the brief they are listed
with prices and no write-up rather than relabelled.</p>
<table><thead><tr><th>Date</th><th>Fixture</th><th>Selection</th><th>Model p</th><th>Our fair American</th><th>Source</th></tr></thead>
<tbody>{outside_rows}</tbody></table>"""
open(os.path.join(OUT, "picks.html"), "w").write(page("Focus picks", body, "picks.html"))

# ---------------- markets
mk_rows = ""
for sport in sorted(by_sport):
    rs = [r for r in ROWS if r["sport"] == sport and r["status"] == "priced"]
    def has(k): return sum(1 for r in rs if k in r["markets"])
    n_sel = sum(2 * len(r["markets"]) for r in rs)
    mk_rows += (f"<tr><td>{sport}</td><td>{len(rs)}</td><td>{has('moneyline')}</td>"
                f"<td>{has('puck_line') + has('run_line') + has('spread')}</td><td>{has('total')}</td><td>{n_sel}</td></tr>")
body = f"""<h2>Markets originated</h2>
<p>Every available market was investigated. We originate a market only where a verified official input supports a
defensible probability; everything else is named on the <a href="flagged.html">Flagged</a> page (AD-F11) instead of being invented.</p>
<table><thead><tr><th>Sport</th><th>Priced fixtures</th><th>Match winner / moneyline</th><th>Handicap (puck/run line, spread)</th><th>Match total</th><th>Selections priced (both sides)</th></tr></thead>
<tbody>{mk_rows}</tbody></table>
<ul>
<li><b>Ice Hockey (NHL):</b> moneyline incl. OT, puck line ±1.5, match total at our originated line — all from one Poisson score matrix.</li>
<li><b>Basketball (EuroLeague):</b> match winner incl. OT, point spread at our originated line, match total — Normal margin/total model.</li>
<li><b>Baseball (MLB):</b> moneyline (log5), run line ±1.5 and match total (expected-runs model).</li>
<li><b>Darts (PDC):</b> match winner only — leg handicaps/totals and 180s markets have no verified input in this desk.</li>
<li><b>Tennis / eSports:</b> fixtures verified but no market originated (no verified strength input) — see row reasons.</li>
</ul>"""
open(os.path.join(OUT, "markets.html"), "w").write(page("Markets", body, "markets.html"))

# ---------------- coverage
cov_rows = "".join(
    f"<tr><td>{e(c['sport'])}</td><td>{c['olbg_id'] or '—'}</td><td>{e(c['board_ad_status'])}</td>"
    f"<td>{e(c['note'])}</td><td><a href=\"{e(c['olbg_url'])}\">OLBG page</a></td></tr>" for c in B["coverage"])
body = f"""<h2>Coverage — every in-scope OLBG sport accounted for</h2>
<p>Scope = every OLBG sport <b>except</b> soccer/football (1), horse racing (2), specials (6), American football (11),
boxing/UFC/MMA (16), cycling (17) and hurling (no standalone OLBG ID). Taxonomy: repo
<code>data/olbg-structure.json</code> (reverse-engineered 2026-10-21 from OLBG's sitemap).</p>
<table><thead><tr><th>Sport</th><th>OLBG ID</th><th>Board AD status</th><th>What was found / attempted</th><th>OLBG</th></tr></thead>
<tbody>{cov_rows}</tbody></table>"""
open(os.path.join(OUT, "coverage.html"), "w").write(page("Coverage", body, "coverage.html"))

# ---------------- methodology
m = B["method"]
body = f"""<h2>Methodology</h2>
<h3>How the list was built</h3><ol>
<li>OLBG's sport taxonomy was taken from the repo's reverse-engineering (<code>data/olbg-structure.json</code>) and the brief's exclusions applied.</li>
<li>Fixtures and form were read <b>only</b> from official league/tour/federation payloads or pages on 22 Oct 2026 (see <a href="sources.html">Sources</a> and <a href="verification.html">live checks</a>). OLBG was never used as a fixture or price source.</li>
<li>Each payload parsed by the build is SHA-256-pinned against the capturing session's manifest before use; the build fails on any mismatch.</li>
<li>Window: official local fixture dates 23 Oct – 5 Nov 2026, so nothing published here had already been played at capture.</li></ol>
<h3>Prices</h3><p>{e(m['prices'])}</p><p>{e(m['confidence'])} {e(m['focus_rule'])}</p>
<h3>Models (all constants disclosed)</h3><ul>
<li><b>NHL:</b> {e(m['nhl'])}</li><li><b>EuroLeague:</b> {e(m['euroleague'])}</li>
<li><b>MLB:</b> {e(m['mlb'])}</li><li><b>PDC darts:</b> {e(m['pdc'])}</li><li><b>Unpriced rows:</b> {e(m['unpriced'])}</li></ul>
<h3>Limitations</h3><p>Early-season samples are small (NHL 8–12 games, EuroLeague 6–7 derived games per team) and are
shrunk toward league means for exactly that reason. Injuries, line-ups, goaltenders, pitchers, rest, weather and
head-to-heads beyond the printed inputs were <b>not</b> checked (AD-F13). A High grade means the documented model
rates the selection &ge;70% on the verified inputs — it is not a promise about any real-world market.</p>"""
open(os.path.join(OUT, "methodology.html"), "w").write(page("Methodology", body, "methodology.html"))

# ---------------- sources
src_rows = ""
for s in SRC:
    h = f"<code>{s['sha256'][:16]}…</code>" if s.get("sha256") else "live read (no file)"
    man = "✓ matches capturing manifest" if s.get("hash_matches_manifest") else ("—" if s.get("sha256") else "see live checks")
    src_rows += (f"<tr><td>{e(s['name'])}</td><td><a href=\"{e(s['url'])}\">official URL</a></td>"
                 f"<td>{e(s.get('repo_file',''))}</td><td>{h}</td><td>{man}</td><td>{e(s['note'])}</td></tr>")
body = f"""<h2>Sources — official only, hash-pinned</h2>
<p>Full hashes: <code>data/session-7c581d22/sources.json</code>. “Matches capturing manifest” means the file parsed by
this build is byte-identical (or, for .gz captures, content-identical) to what the capturing session recorded on 22 Oct 2026.</p>
<table><thead><tr><th>Source</th><th>Official URL</th><th>Repo payload</th><th>SHA-256 (first 16)</th><th>Manifest check</th><th>Note</th></tr></thead>
<tbody>{src_rows}</tbody></table>"""
open(os.path.join(OUT, "sources.html"), "w").write(page("Sources", body, "sources.html"))

# ---------------- verification
lc_rows = "".join(
    f"<tr><td>{e(c['id'])}</td><td><a href=\"{e(c['url'])}\">{e(c['url'])}</a></td><td>{e(c['observed'])}</td>"
    f"<td>{e(c['compared_with'])}</td><td>{e(c['result'])}</td></tr>" for c in B["live_checks"])
body = f"""<h2>Verification — line by line</h2>
<h3>Machine gates (<code>scripts/session-7c581d22/verify.py</code>)</h3><ul>
<li>Every payload hash re-checked against the capturing manifests; build + verify both assert this.</li>
<li>Every row: official source URL present, date inside 23 Oct – 5 Nov 2026, sport not on the exclusion list.</li>
<li>Every price re-derived: decimal = 1/p, American conversion, two-sided markets sum to p=1.</li>
<li>Every confidence grade recomputed from its probability and the sport's sample cap.</li>
<li>Every focus pick: p &ge; 0.70, American inside &minus;250…+10,000, prediction &ge; 30 words, unique (exact and word-overlap), names both sides, states the selection.</li>
<li>Unpriced rows carry no prices, no pick, and a reason. Internal links on every page resolve to files in this directory.</li></ul>
<h3>Live reads performed this session (22 Oct 2026)</h3>
<table><thead><tr><th>#</th><th>Official URL</th><th>What was observed (verbatim where quoted)</th><th>Compared with</th><th>Result</th></tr></thead>
<tbody>{lc_rows}</tbody></table>
<p>Machine-readable log: <code>data/session-7c581d22/live_checks.json</code>. Reproduce everything with
<code>python3 scripts/session-7c581d22/build.py &amp;&amp; python3 scripts/session-7c581d22/render.py &amp;&amp; python3 scripts/session-7c581d22/verify.py</code>.</p>"""
open(os.path.join(OUT, "verification.html"), "w").write(page("Verification", body, "verification.html"))

# ---------------- flagged
fl_rows = "".join(
    f"<tr><td>{e(f['id'])}</td><td><b>{e(f['title'])}</b><br>{e(f['detail'])}</td>"
    f"<td>needs review (non-blocking)</td><td><a href=\"{e(f['source_url'])}\">review at source</a></td></tr>" for f in B["flagged"])
body = f"""<h2>Flagged for Review</h2>
<p>Everything uncertain, unverified or judgment-based is published here with a source link for manual review.
None of these items blocks the desk; values affected by them are left blank or capped rather than guessed.</p>
<table><thead><tr><th>ID</th><th>Finding</th><th>Status</th><th>Source for manual review</th></tr></thead>
<tbody>{fl_rows}</tbody></table>"""
open(os.path.join(OUT, "flagged.html"), "w").write(page("Flagged for Review", body, "flagged.html"))

CSS = """*{box-sizing:border-box}body{margin:0;font:15px/1.55 -apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#1c2430;background:#f6f8fb}
.wrap{max-width:1180px;margin:0 auto;padding:0 18px}
header{background:#0d2137;color:#fff;padding:22px 0 14px}header h1{margin:0;font-size:26px}.sub{color:#bcd2e8;margin:6px 0 12px}
nav a{color:#dcebf9;text-decoration:none;margin-right:14px;padding:4px 2px;display:inline-block}nav a.active{color:#fff;border-bottom:2px solid #ffb703;font-weight:600}
nav.sports a{font-size:13px;color:#9fc0dd}nav.sports a.active{color:#fff}
main{padding:24px 0 40px}h2{margin:26px 0 10px}h3{margin:18px 0 6px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d9e2ec;font-size:13.5px}
th,td{border-bottom:1px solid #e6edf4;padding:8px 10px;text-align:left;vertical-align:top}
th{background:#eef3f9}.hero,.pick,.match{background:#fff;border:1px solid #d9e2ec;border-radius:10px;padding:16px 18px;margin-bottom:16px}
.cards{display:flex;flex-wrap:wrap;gap:14px}.card{background:#fff;border:1px solid #d9e2ec;border-radius:10px;padding:14px 18px;min-width:160px}
.card .big{font-size:30px;margin:2px 0}.stats{font-weight:600}.meta{color:#5a6b7e}.pred{font-size:15.5px}
.conf{border-radius:20px;padding:1px 9px;font-size:12px;font-weight:700;color:#fff}
.conf.high{background:#157347}.conf.medium{background:#b8860b}.conf.low{background:#7a8794}
footer{background:#0d2137;color:#bcd2e8;padding:16px 0;font-size:13px}code{background:#eef3f9;padding:1px 5px;border-radius:4px;color:#14304d}
footer code{background:#1a3a56;color:#dcebf9}details{margin:8px 0}summary{cursor:pointer;color:#0d4f8b}
a{color:#0d4f8b}"""
open(os.path.join(OUT, "style.css"), "w").write(CSS)
print("rendered:", sorted(os.listdir(OUT)))

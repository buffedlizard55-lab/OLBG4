"""Builds the session-937ee172 dashboard. Deterministic: run `python3 scripts/session-937ee172/build.py`.
Inputs: data/session-937ee172/official/*.json (official pulls), scripts/session-937ee172/model.py output,
and scripts/session-937ee172/predictions.py (write-ups). Writes session-937ee172/*.html and data/session-937ee172/desk.json."""
import html, json, pathlib, sys, datetime as dt
from zoneinfo import ZoneInfo
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import model
from predictions import PREDICTIONS

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUTDIR = ROOT / "session-937ee172"
OUTDIR.mkdir(exist_ok=True)
DESK = model.run()
ET = ZoneInfo("America/New_York")
BASE = "https://buffedlizard55-lab.github.io/OLBG4/session-937ee172"
FETCH_NOTE = "Fetched 24 Oct 2026 (UTC) with the fetch tool; standings snapshot 2026-10-24T17:05:30Z"

SPORTS = [  # (label, file, status)
 ("Golf","golf.html"),("Volleyball","volleyball.html"),("Rugby Union","rugby-union.html"),("Cricket","cricket.html"),
 ("Snooker","snooker.html"),("Darts","darts.html"),("Baseball","baseball.html"),("Gaelic Sports","gaelic-sports.html"),
 ("Greyhounds","greyhounds.html"),("Tennis","tennis.html"),("Motor Racing","motor-racing.html"),("Handball","handball.html"),
 ("Ice Hockey","ice-hockey.html"),("Basketball","basketball.html"),("Rugby League","rugby-league.html")]
CAPTURED = {"Ice Hockey"}

def e(s): return html.escape(str(s))

def price(p):
    if p is None: return "—"
    return f"+{p}" if p > 0 else f"{p}"

def pct(p): return f"{p*100:.1f}%"

def et(iso):
    t = dt.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc).astimezone(ET)
    return t.strftime("%a %d %b, %I:%M %p ET")

def nav(active):
    items = ['<a href="index.html" class="%s">Overview</a>' % ("on" if active == "index" else "")]
    for lab, f in SPORTS:
        cls = "on" if active == f else ""
        items.append(f'<a href="{f}" class="{cls}">{e(lab)}</a>')
    items.append(f'<a href="flagged.html" class="{"on" if active=="flagged.html" else ""}">Flagged for Review</a>')
    items.append(f'<a href="methodology.html" class="{"on" if active=="methodology.html" else ""}">Methodology</a>')
    items.append(f'<a href="sources.html" class="{"on" if active=="sources.html" else ""}">Sources</a>')
    return '<nav class="side">' + "".join(items) + '</nav>'

CSS = """
*{box-sizing:border-box}body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#1b2430;background:#f5f7fa;font-size:15px;line-height:1.5}
.wrap{display:grid;grid-template-columns:230px 1fr;min-height:100vh}
nav.side{background:#14213d;color:#fff;padding:18px 12px}nav.side a{display:block;color:#dbe4f0;text-decoration:none;padding:6px 10px;border-radius:6px;font-size:14px}
nav.side a:hover{background:#22345a}nav.side a.on{background:#fca311;color:#14213d;font-weight:600}
nav.side::before{content:"OLBG4 · 24 Oct 2026";display:block;font-weight:700;padding:4px 10px 14px;color:#fff}
main{padding:24px 28px;max-width:1280px}
h1{font-size:24px;margin:0 0 6px}h2{font-size:18px;margin:28px 0 10px}h3{font-size:16px;margin:18px 0 6px}
.lead{color:#4a5568;margin:0 0 16px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:12px 0 18px}
.kpi{background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:12px 14px}.kpi b{display:block;font-size:24px}.kpi span{color:#5a6678;font-size:13px}
.card{background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:14px 16px;margin:12px 0}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13.5px}th,td{border-bottom:1px solid #e6ebf2;padding:7px 8px;text-align:left;vertical-align:top}
th{background:#eef2f8;font-weight:600;position:sticky;top:0}
.conf-High{background:#d4f5dd;color:#11622b;font-weight:700;padding:2px 6px;border-radius:4px}
.conf-Medium{background:#fff1c2;color:#7a5600;font-weight:700;padding:2px 6px;border-radius:4px}
.conf-Low{background:#e7ebf1;color:#3a4657;font-weight:600;padding:2px 6px;border-radius:4px}
.flag{background:#fdecea;color:#8a1c12;padding:2px 6px;border-radius:4px;font-weight:600}
.note{background:#eef6ff;border-left:4px solid #3b82f6;padding:10px 14px;border-radius:6px;margin:12px 0}
.warn{background:#fff7e6;border-left:4px solid #f59e0b;padding:10px 14px;border-radius:6px;margin:12px 0}
.pred{background:#fff;border:1px solid #dfe5ee;border-radius:10px;padding:14px 16px;margin:12px 0}.pred p{margin:6px 0}
.small{font-size:12.5px;color:#5a6678}a{color:#1d4ed8}
.wrapx{overflow-x:auto}
@media (max-width:860px){.wrap{grid-template-columns:1fr}nav.side{display:flex;flex-wrap:wrap;gap:4px}nav.side::before{width:100%}}
"""

def page(title, active, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · OLBG4 session 937ee172</title><style>{CSS}</style></head><body><div class="wrap">{nav(active)}<main>{body}
<p class="small">Data cut: 24 Oct 2026 (UTC). Every row links to the official or OLBG page it came from. Unverified values are left blank and listed on the <a href="flagged.html">Flagged for Review</a> page.</p>
</main></div></body></html>"""

games = DESK["games"]
high = [g for g in games if g["confidence"] == "High"]
med = [g for g in games if g["confidence"] == "Medium"]
low = [g for g in games if g["confidence"] == "Low"]
olbg_seen = [g for g in games if g["olbg_seen"]]
cands_total = [g for g in games if max(g["p_over_5_5"], g["p_under_5_5"]) >= 0.70]

# ---------- Ice hockey page ----------
def hockey_rows():
    rows = []
    for g in games:
        olbg = f'<a href="{e(g["olbg_seen"])}">OLBG event</a>' if g["olbg_seen"] else '<span class="flag">not seen</span>'
        pred = "written up below" if g["id"] in PREDICTIONS else "no write-up (Low)"
        rows.append(f"""<tr>
<td>{e(et(g["start_utc"]))}<br><span class="small">{e(g["venue"])}</span></td>
<td><b>{e(g["away"])}</b> @ <b>{e(g["home"])}</b><br><span class="small">{e(g["away_record"])} · {e(g["home_record"])}</span></td>
<td>{g["away_gf_pg"]} / {g["away_ga_pg"]}<br><span class="small">{g["home_gf_pg"]} / {g["home_ga_pg"]}</span><br><span class="small">(GF/GA per game, away / home)</span></td>
<td><b>{e(g["pick_side"])}</b> moneyline<br><span class="small">our win prob {pct(g["pick_p"])} · fair {price(g["pick_fair_american"])}</span></td>
<td><span class="conf-{g["confidence"]}">{g["confidence"]}</span></td>
<td>{e(g["away"])} {pct(g["p_away_ml"])} · {e(g["home"])} {pct(g["p_home_ml"])}</td>
<td>{e(g["away"])} {price(int(g["dk_ml"][g["away"]]))} · {e(g["home"])} {price(int(g["dk_ml"][g["home"]]))}<br><span class="small">reference only, not OLBG</span></td>
<td>Over 5.5 {pct(g["p_over_5_5"])}<br>Over 6.5 {pct(g["p_over_6_5"])}</td>
<td>{e(g["home"])} −1.5 {pct(g["p_home_minus_1_5"])}<br>{e(g["away"])} +1.5 {pct(g["p_away_plus_1_5"])}</td>
<td>{olbg}<br><span class="small"><a href="https://api-web.nhle.com/v1/score/2026-10-24">NHL source</a> · <a href="https://api-web.nhle.com/v1/standings/2026-10-24">standings</a></span><br><span class="small">{pred}</span></td>
</tr>""")
    return "\n".join(rows)

def hockey_preds():
    out = []
    for g in games:
        if g["id"] not in PREDICTIONS: continue
        p = PREDICTIONS[g["id"]]
        out.append(f"""<div class="pred"><h3>{e(g["away"])} @ {e(g["home"])} · {e(p["selection"])} · <span class="conf-{g["confidence"]}">{g["confidence"]}</span></h3>
<p>{e(p["text"])}</p>
<p class="small"><b>Selection:</b> {e(p["selection"])} · <b>Our win probability:</b> {pct(g["pick_p"])} · <b>Our fair price:</b> {price(g["pick_fair_american"])} · <b>Reference price (DK, not OLBG):</b> {price(int(g["dk_ml"][g["pick_side"]]))}<br>
<b>Sources:</b> {" · ".join(f'<a href="{e(s)}">{i+1}</a>' for i,s in enumerate(p["sources"]))}</p></div>""")
    return "\n".join(out)

hockey_body = f"""
<h1>Ice Hockey · NHL · 24 Oct 2026</h1>
<p class="lead">All 12 NHL games on the official schedule for 24 Oct 2026 (ET). Our own match-winner line for each, with puck line and totals alongside.</p>
<div class="kpis"><div class="kpi"><b>{len(games)}</b><span>official NHL games</span></div>
<div class="kpi"><b>{len(high)}</b><span>High picks</span></div><div class="kpi"><b>{len(med)}</b><span>Medium picks</span></div>
<div class="kpi"><b>{len(low)}</b><span>Low picks</span></div><div class="kpi"><b>{len(olbg_seen)}/12</b><span>seen on OLBG listing page read</span></div></div>
<div class="warn"><b>Why there are no High picks:</b> High needs a probability of 70% or more, a price inside −250 to +10,000 and at least 10 games played by both clubs. No game reaches 70% on our line: the highest is Boston at 67.5%. See the <a href="methodology.html">Methodology</a> page.</div>
<h2>Every game, every market we priced</h2>
<div class="wrapx"><table><thead><tr><th>Start</th><th>Match</th><th>GF / GA per game</th><th>Our pick</th><th>Confidence</th><th>Our match-winner probability</th><th>Reference moneyline (not OLBG)</th><th>Total</th><th>Puck line</th><th>Sources</th></tr></thead>
<tbody>{hockey_rows()}</tbody></table></div>
<h2>Written predictions (Medium picks)</h2>
<p class="small">No High pick qualified on 24 Oct, so these three are Medium write-ups. None uses injury or starting-goalie information, because none was confirmed for these games.</p>
{hockey_preds()}
<h2>Markets investigated</h2>
<p>Match winner (moneyline), puck line ±1.5, totals 5.5 and 6.5. Moneyline is the pick market. Puck line and totals are shown for every game in the table above. Candidate totals at or above 70%: {", ".join(f'{e(g["away"])} @ {e(g["home"])} Over 5.5 ({pct(g["p_over_5_5"])})' for g in cands_total) or "none"}. Their prices were not captured on OLBG, so they are not graded High.</p>
"""

# ---------- Landing ----------
top = sorted(games, key=lambda g: -g["pick_p"])[:5]
top_rows = "".join(f"""<tr><td>{e(et(g["start_utc"]))}</td><td>{e(g["away"])} @ {e(g["home"])}</td><td><b>{e(g["pick_side"])}</b> moneyline</td><td><span class="conf-{g["confidence"]}">{g["confidence"]}</span></td><td>{pct(g["pick_p"])}</td><td>{price(g["pick_fair_american"])}</td><td><a href="ice-hockey.html">game page</a></td></tr>""" for g in top)
sport_cards = "".join(
    f'<div class="kpi"><b><a href="{f}" style="text-decoration:none">{e(lab)}</a></b><span>{"Captured 24 Oct" if lab in CAPTURED else "Not captured in this session"}</span></div>'
    for lab, f in SPORTS)

index_body = f"""
<h1>OLBG4 · Daily desk · 24 Oct 2026</h1>
<p class="lead">Executive summary for today. Ice Hockey (NHL) is captured from official sources. The other 14 sports are listed for completeness and have not been captured in this session.</p>
<div class="kpis">
<div class="kpi"><b>0</b><span>High-confidence picks (≥70%, −250 to +10,000, 10+ games)</span></div>
<div class="kpi"><b>{len(med)}</b><span>Medium picks (60–70%)</span></div>
<div class="kpi"><b>{len(games)}</b><span>NHL games priced with our own lines</span></div>
<div class="kpi"><b>1 of 15</b><span>covered sports captured in this session</span></div>
</div>
<div class="note"><b>Executive summary.</b> On 24 Oct 2026 the official NHL schedule lists 12 games. We priced all 12 from the NHL standings alone, with no bookmaker or OLBG price as an input. No game clears the High rule. The three strongest selections are Medium: Boston moneyline, Vegas moneyline and Detroit moneyline. We did not reach the target of five High picks per sport: that target cannot be met from one day of one league, and the other 14 sports were not captured in this session.</div>
<h2>Highest-probability picks today (all Medium or Low)</h2>
<div class="wrapx"><table><thead><tr><th>Start (ET)</th><th>Match</th><th>Our pick</th><th>Confidence</th><th>Our win probability</th><th>Our fair price</th><th>Where</th></tr></thead><tbody>{top_rows}</tbody></table></div>
<h2>Sports</h2>
<div class="kpis">{sport_cards}</div>
<h2>What this desk did</h2>
<ul>
<li>Pulled the NHL standings and scoreboard from api-web.nhle.com (official NHL API) and checked the totals: 1,047 goals for, 1,047 against, 334 games-played across 32 clubs.</li>
<li>Read the OLBG ice hockey listing page (event IDs 199999–200010). 11 of the 12 official NHL games appear there; BUF @ WSH (event 200003) is not in the part of the page we read.</li>
<li>Built our own lines with shrinkage toward the league average, then labelled each pick Low, Medium or High.</li>
<li>Wrote three Medium write-ups with the team, form, scoring record and player stats taken from the official pages.</li>
</ul>
<p class="small">See <a href="flagged.html">Flagged for Review</a> for everything not confirmed, and <a href="sources.html">Sources</a> for each link. Repository coordination entry: <code>COORDINATION.md</code>, Board BZ.</p>
"""

def sport_page(lab, f):
    if lab in CAPTURED:
        return hockey_body
    return f"""<h1>{e(lab)}</h1>
<p class="lead">Not captured in this session. No {e(lab.lower())} fixture, price, prediction or statistic is shown here, because none was pulled from an official source in this session.</p>
<div class="warn"><b>Status:</b> not started. Listed so the category is visible on the dashboard. The OLBG {e(lab)} listing has not been read, and no official {e(lab.lower())} fixture feed has been checked. See <a href="flagged.html">Flagged for Review</a>.</div>
<h2>High picks</h2><p>None. 0 of the target 5.</p>"""

flags = [
 ("Scope", "14 of 15 covered sports were not captured in this session.", "Ice hockey only. The other sport pages say so.", "https://www.olbg.com/betting-tips", "Not started"),
 ("Coverage", "Target of 5 High picks per sport not met.", "Ice hockey produced 0 High picks on 24 Oct.", "https://api-web.nhle.com/v1/score/2026-10-24", "Result, not an error"),
 ("OLBG listing", "BUF @ WSH (NHL 2026020173) is not seen on the OLBG page read.", "OLBG event IDs run 200000–200010; ID 200003 was not in the section we read. Check the full OLBG NHL listing.", "https://www.olbg.com/betting-tips/Ice_Hockey/13", "Unverified on OLBG"),
 ("Injuries", "No injury or lineup information was captured for any game.", "Injury and starting-goalie cells are blank. Write-ups say so.", "https://www.nhl.com/schedule/2026-10-24", "Unverified — blank"),
 ("Prices", "Reference prices are DraftKings moneylines from the NHL API, not OLBG prices.", "OLBG match-winner prices were not captured, so the −250 to +10,000 test uses this reference.", "https://api-web.nhle.com/v1/score/2026-10-24", "Unverified against OLBG"),
 ("Lines input", "Home-ice advantage is not included in our lines.", "Excluding it slightly understates home sides; no official home-split figure was used.", "https://api-web.nhle.com/v1/standings/2026-10-24", "Known limitation"),
 ("Sample", "Season records are 8 to 12 games in, so early-season noise is large.", "Shrinkage (10 prior games) and the 10-game rule reduce, but do not remove, that noise.", "https://api-web.nhle.com/v1/standings/2026-10-24", "Known limitation"),
 ("Transcription", "Standings were transcribed by hand from the fetch output.", "Checks passed (GF total = GA total, games-played even, W+L+OTL = GP for every club). No second independent pull was made.", "https://api-web.nhle.com/v1/standings/now", "Re-check recommended"),
 ("Timing", "OLBG shows ANA @ PHI at 13:07 'Today'; NHL start is 13:00 ET.", "Time display differs by a few minutes; not used in any calculation.", "https://www.olbg.com/betting-tips/Ice_Hockey/13", "Observation"),
 ("Stale repo", "COORDINATION.md is about 695 KB and lists 90+ boards; the README points to older dashboards.", "This session did not audit those dashboards line by line; it only claims its own scope.", "https://github.com/buffedlizard55-lab/OLBG4/blob/main/COORDINATION.md", "Flagged, not audited"),
]
flag_rows = "".join(f"<tr><td>{e(a)}</td><td>{e(b)}</td><td>{e(c)}</td><td><a href=\"{e(u)}\">source</a></td><td><span class=\"flag\">{e(s)}</span></td></tr>" for a,b,c,u,s in flags)

flagged_body = f"""<h1>Flagged for Review</h1>
<p class="lead">Irregularities, blank values and limits. Each row links to the page it came from. Nothing here blocks publication; it is listed so you can review it.</p>
<div class="wrapx"><table><thead><tr><th>Area</th><th>Issue</th><th>Detail</th><th>Source</th><th>Status</th></tr></thead><tbody>{flag_rows}</tbody></table></div>"""

method_body = """<h1>Methodology</h1>
<p class="lead">How our own lines and confidence labels are produced. This is the same method for every game.</p>
<h2>Own line (ice hockey)</h2>
<ul>
<li><b>League rate:</b> L = total goals for ÷ total games-played across all 32 clubs = 1,047 ÷ 334 = 3.1347 goals per team-game.</li>
<li><b>Shrinkage:</b> each club's goals-for and goals-against per game are pulled toward L with a prior of 10 games: att = (GF + 10·L) ÷ (GP + 10), def = (GA + 10·L) ÷ (GP + 10).</li>
<li><b>Expected goals:</b> home = att_home × def_away ÷ L; away = att_away × def_home ÷ L.</li>
<li><b>Probabilities:</b> goals are treated as independent Poisson variables. A tie after 60 minutes is split 50/50 for overtime. Puck line and totals come from the same distribution.</li>
<li><b>Home advantage:</b> not included.</li>
</ul>
<h2>Confidence labels</h2>
<ul>
<li><b>High:</b> our win probability ≥ 70%, the reference price is between −250 and +10,000, and both clubs have played at least 10 games.</li>
<li><b>Medium:</b> probability 60% to 69.9%.</li>
<li><b>Low:</b> probability under 60%.</li>
</ul>
<div class="note"><b>Rule history.</b> The first run used unshrunk season rates and set no minimum sample. It gave one High pick, NJD moneyline, which rested on LAK's 8-game sample. We then added shrinkage and the 10-game rule before reading the final output. The rules were not changed to produce a pick.</div>
<h2>What is not an input</h2>
<p>No bookmaker, OLBG or tipster price or opinion is used to set a probability. Bookmaker prices appear only as a reference and never change a label.</p>
"""

sources_rows = [
 ("NHL standings (all 32 clubs)", "https://api-web.nhle.com/v1/standings/now", "resolves to /v1/standings/2026-10-24"),
 ("NHL scoreboard (24 Oct)", "https://api-web.nhle.com/v1/score/2026-10-24", "12 games, team records, scoring and goalie leaders, DK/FanDuel odds fields"),
 ("NHL schedule (24 Oct, cross-check)", "https://api-web.nhle.com/v1/schedule/2026-10-24", "first 3 games read; full list from scoreboard"),
 ("NHL standings (human page)", "https://www.nhl.com/standings", "linked for manual review; not read in this session"),
 ("OLBG ice hockey listing", "https://www.olbg.com/betting-tips/Ice_Hockey/13", "event IDs 199999–200010 read; ID 200003 not seen"),
]
src_rows = "".join(f"<tr><td>{e(a)}</td><td><a href=\"{e(u)}\">{e(u)}</a></td><td>{e(n)}</td></tr>" for a,u,n in sources_rows)
sources_body = f"""<h1>Sources</h1><p class="lead">{e(FETCH_NOTE)}</p>
<div class="wrapx"><table><thead><tr><th>Source</th><th>Link</th><th>Used for</th></tr></thead><tbody>{src_rows}</tbody></table></div>
<h2>Per-game sources</h2><p class="small">Each game row on the Ice Hockey page links to the NHL scoreboard and standings, and to the OLBG event where it was seen.</p>"""

def write(name, title, body):
    (OUTDIR / name).write_text(page(title, name, body))

write("index.html", "Overview", index_body)
for lab, f in SPORTS:
    write(f, lab, sport_page(lab, f))
write("flagged.html", "Flagged for Review", flagged_body)
write("methodology.html", "Methodology", method_body)
write("sources.html", "Sources", sources_body)

(ROOT / "data/session-937ee172/desk.json").write_text(json.dumps(DESK, indent=2))
print("built", len(list(OUTDIR.glob("*.html"))), "pages; high", len(high), "medium", len(med), "low", len(low))

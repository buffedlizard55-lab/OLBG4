#!/usr/bin/env python3
"""Board X site renderer. Run after build.py. Emits static HTML into session-e1161e0e/."""
import json, os, html
HERE=os.path.dirname(__file__)
D=json.load(open(os.path.join(HERE,"..","data","session-e1161e0e","board.json")))
ROWS=D["rows"]
E=lambda s: html.escape(str(s if s is not None else ""))
CSS="""*{box-sizing:border-box}body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#f6f7f9;color:#14202e}
header{background:#0d2137;color:#fff;padding:22px 18px}header h1{margin:0 0 6px;font-size:24px}header p{margin:0;opacity:.85;font-size:14px}
nav{display:flex;flex-wrap:wrap;gap:8px;background:#12304f;padding:10px 18px}nav a{color:#cfe3f7;text-decoration:none;font-size:13px;padding:5px 10px;border-radius:14px;background:#1a4066}nav a:hover{background:#24548a;color:#fff}
main{max-width:1240px;margin:0 auto;padding:20px 16px 50px}h2{font-size:19px;margin:22px 0 8px}h3{font-size:16px;margin:18px 0 6px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin:14px 0}
.card{background:#fff;border:1px solid #dde3ea;border-radius:10px;padding:14px}.card b{font-size:26px;display:block}.card span{font-size:12px;color:#5a6b7e;text-transform:uppercase;letter-spacing:.04em}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13px}th,td{border:1px solid #e1e6ec;padding:7px 8px;text-align:left;vertical-align:top}th{background:#eef3f8}
tr:hover td{background:#f4f8fc}.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:11px;font-weight:600}
.High{background:#d9f2e2;color:#0d6b33}.Medium{background:#fff1cf;color:#8a6100}.Low{background:#fde3e3;color:#9c2222}
.focus{background:#0d6b33;color:#fff}.out{background:#e8edf3;color:#41556b}small{color:#5a6b7e}a{color:#14579c}
.pred{background:#fff;border:1px solid #dde3ea;border-left:5px solid #0d6b33;border-radius:8px;padding:14px 16px;margin:12px 0}
.pred p{line-height:1.55;margin:8px 0}.filters{display:flex;gap:8px;flex-wrap:wrap;margin:12px 0}.filters select,.filters input{padding:7px;font-size:13px}
.flag{background:#fff8e6;border:1px solid #ecd9a0;border-radius:8px;padding:12px 14px;margin:10px 0}code{background:#eef3f8;padding:1px 5px;border-radius:4px}
footer{max-width:1240px;margin:0 auto;padding:0 16px 34px;color:#5a6b7e;font-size:12px}.wide{overflow-x:auto}"""
NAV=[("index.html","Dashboard"),("entries.html","All Entries"),("picks.html","High-Confidence Picks"),
 ("sport-ice-hockey.html","Ice Hockey"),("sport-basketball.html","Basketball"),("sport-baseball.html","Baseball"),
 ("sport-darts.html","Darts"),("sport-rugby-union.html","Rugby Union"),("sport-rugby-league.html","Rugby League"),
 ("sport-cricket.html","Cricket"),("markets.html","Markets"),("coverage.html","Coverage Register"),
 ("methodology.html","Methodology"),("sources.html","Sources"),("flagged.html","Flagged for Review"),("verification.html","Verification")]
def page(title, body):
    nav="".join(f'<a href="{u}">{E(t)}</a>' for u,t in NAV)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} — OLBG4 Board X</title><style>{CSS}</style></head><body>
<header><h1>OLBG4 — Board X desk</h1><p>Reverse-engineered OLBG coverage &middot; our own originated lines &middot; fixtures 23 Oct – 4 Nov 2026 &middot; captured 2026-10-22 from official sources &middot; fair prices, no bookmaker margin</p></header>
<nav>{nav}</nav><main>{body}</main>
<footer>Session arena/e1161e0e-olbg4 (Board X). Every price on this site is originated by the model documented on the Methodology page from the linked official source; no OLBG or bookmaker price was read. Unverifiable values are blank and listed on Flagged for Review. Analysis for research/entertainment — not betting advice.</footer></body></html>"""
def amer_fmt(r):
    return f"{r['pick_amer']:+d}" if r.get("pick_amer") is not None else "—"
def row_tr(r):
    conf=r.get("confidence") or "—"
    w='<span class="pill focus">IN WINDOW</span>' if r.get("in_window") and conf=="High" else ('<span class="pill out">outside −250…+10,000</span>' if conf=="High" else "")
    src=f'<a href="{E(r["source_url"])}" rel="noopener">{E(r["source_name"].split(";")[0])}</a>'
    markets="<br>".join(f"<b>{E(k)}:</b> "+", ".join(f"{E(a)} {E(b)}" for a,b in v.items()) for k,v in r["markets"].items())
    return (f'<tr data-sport="{E(r["sport"])}" data-conf="{E(conf)}"><td>{E(r["id"])}</td><td>{E(r["date"])}<br><small>{E(r.get("time_et",""))}</small></td>'
      f'<td>{E(r["sport"])}<br><small>{E(r["competition"])}</small></td>'
      f'<td><b>{E(r["away"])}</b> @ <b>{E(r["home"])}</b><br><small>{E(r.get("venue",""))}</small></td>'
      f'<td><small>H: {E(r.get("form_home",""))}<br>A: {E(r.get("form_away",""))}</small></td>'
      f'<td><small>{markets}</small></td>'
      f'<td><b>{E(r.get("pick","—"))}</b><br><small>{E(r.get("pick_market",""))} p={E(r.get("pick_p","—"))} · fair {E(r.get("pick_dec","—"))} ({amer_fmt(r)})</small></td>'
      f'<td><span class="pill {E(conf)}">{E(conf)}</span> {w}</td><td><small>{E(r.get("focus_play","") or "—")}</small></td><td><small>{src}</small></td></tr>')
def table(rows):
    return ('<div class="wide"><table><thead><tr><th>ID</th><th>Date</th><th>Sport / Competition</th><th>Match (away @ home)</th>'
      '<th>Verified form inputs</th><th>Our originated lines (fair decimal)</th><th>Pick</th><th>Confidence</th><th>Focus play (≥70% &amp; −250…+10,000)</th><th>Official source</th></tr></thead><tbody>'
      + "".join(row_tr(r) for r in rows) + "</tbody></table></div>")

priced=[r for r in ROWS if r["status"]=="priced"]
highs=[r for r in priced if r["confidence"]=="High"]
focus=[r for r in highs if r["in_window"]]
sports=sorted(set(r["sport"] for r in priced))
by_sport={s:[r for r in priced if r["sport"]==s] for s in sports}

# index
sport_cards="".join(f'<div class="card"><b>{len(v)}</b><span>{E(s)} fixtures priced</span></div>' for s,v in by_sport.items())
idx=f"""<h2>Dashboard — what this desk is</h2>
<p>Board X is a fresh-window refresh built only from fixtures that had <b>not yet been played</b> at capture (22 Oct 2026): every row is dated 23 Oct – 4 Nov 2026. It reverse-engineers OLBG's sport universe (every sport except soccer, boxing, UFC/MMA, football/American football, hurling, horse racing, cycling and specials), confirms each fixture on the official league/tour/federation site, originates <b>our own fair lines</b> for match-winner, handicap and totals markets wherever verified inputs exist, picks a winner with a Low/Medium/High confidence grade, and writes a unique human prediction for every High pick. Sports we could not price from an official feed are not hidden — they are listed with the reason on the <a href="coverage.html">Coverage Register</a> and <a href="flagged.html">Flagged for Review</a> pages.</p>
<div class="cards"><div class="card"><b>{len(priced)}</b><span>Fixtures priced with our lines</span></div>
<div class="card"><b>{len(highs)}</b><span>High-confidence picks (≥70%)</span></div>
<div class="card"><b>{len(focus)}</b><span>Focus picks in −250…+10,000 window</span></div>
<div class="card"><b>{len([r for r in priced if r['confidence']=='Medium'])}</b><span>Medium</span></div>
<div class="card"><b>{len([r for r in priced if r['confidence']=='Low'])}</b><span>Low</span></div>{sport_cards}</div>
<h2>Focus pick inside the requested window</h2>
<p>The brief's focus band — model probability at least 70% <i>and</i> a fair American price no shorter than −250 — is only 1.4 percentage points wide at fair odds (p 0.700–0.714). One match-winner selection lands in it this week; seven further High picks are shorter than −250 and are published, labelled, rather than relabelled to fit. See <a href="picks.html">High-Confidence Picks</a> for all eight write-ups.</p>
{table(focus)}
<h2>Next 12 fixtures</h2>{table(sorted(priced,key=lambda r:r['date'])[:12])}
<p><a href="entries.html">See all {len(ROWS)} entries →</a></p>"""
open(os.path.join(HERE,"index.html"),"w").write(page("Dashboard",idx))

# entries
opts="".join(f'<option>{E(s)}</option>' for s in sports)
ent=f"""<h2>All entries ({len(ROWS)})</h2><p>Every row carries its official source link. The one unpriced row (cricket ODI) is flagged in the table note and on Flagged for Review.</p>
<div class="filters"><select id="fs"><option value="">All sports</option>{opts}</select>
<select id="fc"><option value="">All confidence</option><option>High</option><option>Medium</option><option>Low</option></select>
<input id="fq" placeholder="Filter text…"></div>{table(sorted(ROWS,key=lambda r:(r['date'],r['sport'])))}
<script>const f=()=>{{const s=document.getElementById('fs').value,c=document.getElementById('fc').value,q=document.getElementById('fq').value.toLowerCase();
document.querySelectorAll('tbody tr').forEach(tr=>{{tr.style.display=(!s||tr.dataset.sport===s)&&(!c||tr.dataset.conf===c)&&(!q||tr.textContent.toLowerCase().includes(q))?'':'none'}})}};
document.querySelectorAll('.filters select,.filters input').forEach(el=>el.addEventListener('input',f));</script>"""
open(os.path.join(HERE,"entries.html"),"w").write(page("All Entries",ent))

# picks
cards=""
for r in highs:
    win='<span class="pill focus">FOCUS — inside −250…+10,000</span>' if r["in_window"] else '<span class="pill out">High probability but shorter than −250 — outside the requested focus window</span>'
    cards+=f"""<div class="pred"><h3>{E(r['away'])} @ {E(r['home'])} — {E(r['pick'])} to win</h3>
<p><small>{E(r['date'])} · {E(r['sport'])} · {E(r['competition'])} · {E(r.get('venue',''))} · model p={r['pick_p']} · fair decimal {r['pick_dec']} · American {amer_fmt(r)}</small> {win}</p>
<p>{E(r['prediction'])}</p>
<p><small><b>Verified inputs:</b> H: {E(r['form_home'])} · A: {E(r['form_away'])}. <b>Sample:</b> {E(r['sample'])}.<br>
<b>Source:</b> <a href="{E(r['source_url'])}" rel="noopener">{E(r['source_url'])}</a> · fixture: <a href="{E(r['fixture_url'])}" rel="noopener">{E(r['fixture_url'])}</a></small></p></div>"""
picks=f"""<h2>High-confidence picks ({len(highs)}) — written predictions</h2>
<p>Rule: High requires model probability ≥ 70% on an adequate sample (NBA 82-game records; PDC seeds from the 15-event European Tour Order of Merit). One-game Rugby League World Cup samples and the 3-round URC table are capped at Medium however lopsided they look. The focus window (−250…+10,000) is marked on every card; picks outside it are published with that label, never re-graded to fit. Every prediction below is unique, 88–92 words, names the teams/players, cites only form read on the linked official source, and states the selection plainly.</p>{cards}"""
open(os.path.join(HERE,"picks.html"),"w").write(page("High-Confidence Picks",picks))

SLUG={"Ice Hockey":"ice-hockey","Basketball":"basketball","Baseball":"baseball","Darts":"darts","Rugby Union":"rugby-union","Rugby League":"rugby-league","Cricket":"cricket"}
DESC={"Ice Hockey":"NHL moneyline (incl. OT/SO), puck line ±1.5 and total goals, from the official NHL.com standings (GP/W/L/OT/PTS/GF/GA, splits, L10, streak).",
"Basketball":"NBA moneyline and spread from final 2025-26 records (82 games); totals deliberately not originated — no official pace/efficiency table was captured.",
"Baseball":"2026 World Series (Rays @ Brewers) moneyline and run line ±1.5 from official 162-game records (MIL 103-59, TB 98-64). Totals blank: RS/RA splits not captured.",
"Darts":"PDC European Championship Round One (race to 6 legs): match winner, −1.5 leg handicap and total legs from published draw seeds (15-event European Tour Order of Merit).",
"Rugby Union":"URC Round 5: 1X2 result, handicap and total points from the official URC Match Centre table (3 rounds played — confidence capped at Medium; Round 4 intervenes).",
"Rugby League":"RLWC 2026 men & women, Rounds 2-3: match winner, handicap and total points from Round-1 margins only (one game each — confidence capped at Medium).",
"Cricket":"NZ v India T20Is from official ICC T20I team ratings (India 267, NZ 247 at 21 Oct 2026). The 1st ODI is listed unpriced — ICC ODI ratings were not read."}
for s,slug in SLUG.items():
    rs=by_sport.get(s,[])+[r for r in ROWS if r["sport"]==s and r["status"]!="priced"]
    body=f"""<h2>{E(s)} ({len(rs)} entries)</h2><p>{E(DESC[s])}</p>{table(sorted(rs,key=lambda r:r['date']))}"""
    open(os.path.join(HERE,f"sport-{slug}.html"),"w").write(page(s,body))

# markets
mk=""
for s in sports:
    rs=by_sport[s]; keys=[]
    for r in rs:
        for k in r["markets"]:
            base=("Match winner / moneyline" if ("winner" in k.lower() or "moneyline" in k.lower() or "1X2" in k) else
                  "Handicap (puck/run/leg/spread)" if any(x in k.lower() for x in ("puck","run line","handicap","spread")) else "Totals (over/under)")
            if base not in keys: keys.append(base)
    notorig=[]
    for r in rs:
        for k,v in r["markets"].items():
            if any("not originated" in str(x) for x in v.values()): notorig.append(k)
    mk+=f"<tr><td>{E(s)}</td><td>{len(rs)}</td><td>{E('; '.join(keys))}</td><td>{E('; '.join(sorted(set(notorig)))) or '—'}</td></tr>"
markets=f"""<h2>Markets investigated</h2><p>Every available market type was investigated for each sport. A market is only priced where the official source publishes the inputs the model needs; otherwise the field is left blank with the reason, never estimated.</p>
<div class="wide"><table><thead><tr><th>Sport</th><th>Fixtures</th><th>Markets originated</th><th>Investigated but NOT originated (reason in each row)</th></tr></thead><tbody>{mk}</tbody></table></div>
<p>Outright/tournament-winner markets (e.g. World Series winner, European Championship winner, RLWC winner) were investigated and deliberately not originated: pricing them honestly needs a full bracket simulation from verified inputs for every participant, which this capture does not contain. Correct-score markets were investigated and not originated for the same input reason. Both are logged on Flagged for Review.</p>"""
open(os.path.join(HERE,"markets.html"),"w").write(page("Markets",markets))

COVERAGE=[
 ("Ice Hockey","PRICED","NHL 23-27 Oct (26 games). KHL/European leagues listed by OLBG were not captured from an official feed this session."),
 ("Basketball","PRICED","NBA Week 1, 23-25 Oct (27 games). EuroLeague/other leagues not captured from an official feed this session."),
 ("Baseball","PRICED","MLB World Series Games 1-7 (5-7 if necessary)."),
 ("Darts","PRICED","PDC European Championship Round One, Friday 23 Oct (8 ties). Thursday's ties were already in progress/played at capture and are excluded."),
 ("Rugby Union","PRICED","URC Round 5, 30-31 Oct (8 games). Premiership/Top 14 not captured from an official feed this session."),
 ("Rugby League","PRICED","RLWC 2026 men R2+R3, women R2+R3 (17 games). Semi-final pairings (7-8 Nov) depend on pool results — not yet knowable."),
 ("Cricket","PARTIAL","NZ v India T20Is priced from ICC ratings; 1st ODI listed unpriced (ODI ratings not read). Other series (Pakistan tri-series, Namibia v Ireland) not confirmed on an official ICC page this session."),
 ("Tennis","NOT PRICED","ATP Basel & Vienna (26 Oct-1 Nov) confirmed on the official ATP calendar, but singles draws are published 23-24 Oct — no pairings existed to price at capture. Brussels/Lyon quarter-finalists likewise undecided."),
 ("Snooker","NOT PRICED","Northern Ireland Open quarter-finals fall on 23 Oct, but the pairings were decided by last-16 ties played on capture day (22 Oct) and could not be confirmed on wst.tv."),
 ("Esports","NOT PRICED","LoL Worlds 2026 Swiss Stage starts 23 Oct in Allen, TX (Riot primer); Swiss pairings are drawn round-by-round, so no fixture existed to price at capture. Quarter-final draw is 31 Oct."),
 ("Golf","NOT PRICED","No official tour field/tee-time sheet with verified scoring inputs was read this session."),
 ("Handball","NOT PRICED","EHF Champions League fixtures were not confirmed with standings inputs on an official EHF page this session."),
 ("Volleyball","NOT PRICED","No Volleyball World fixture + standings capture this session."),
 ("Badminton / Table Tennis","NOT PRICED","No BWF/WTT draw with verified rankings read this session."),
 ("Aussie Rules","NO FIXTURE","AFL men's season is in its off-season window in this period (repo master board records the same); no fixture to price."),
 ("Greyhound Racing","NOT PRICED","No GBGB racecard with verified form inputs read this session."),
 ("Motor Racing","NOT PRICED","No official entry list with verified performance inputs read this session; outright-only market not originated (see Markets)."),
 ("Gaelic Games (football)","EXCLUDED SCOPE NOTE","Gaelic football sits inside the brief's football exclusion as applied by earlier boards; hurling is excluded by name. Left out deliberately — flagged for the owner's confirmation."),
 ("Excluded by brief","OUT OF SCOPE","Soccer, boxing, UFC/MMA, football/American football, hurling, horse racing, cycling, specials."),
]
cov="".join(f"<tr><td>{E(a)}</td><td><span class='pill {'High' if b=='PRICED' else 'Medium' if b=='PARTIAL' else 'out'}'>{E(b)}</span></td><td>{E(c)}</td></tr>" for a,b,c in COVERAGE)
open(os.path.join(HERE,"coverage.html"),"w").write(page("Coverage Register",
 f"<h2>Coverage register — full in-scope sport list</h2><p>OLBG's sport universe (repo taxonomy, <code>data/sports.json</code> / OLBG.com) minus the brief's exclusions, with the honest state of each sport on this desk. 'Not priced' always means the official inputs could not be read this session — fixtures are never invented to fill a page.</p><div class='wide'><table><thead><tr><th>Sport</th><th>Status</th><th>What is / is not covered, and why</th></tr></thead><tbody>{cov}</tbody></table></div>"))

open(os.path.join(HERE,"methodology.html"),"w").write(page("Methodology","""<h2>Methodology — how every number is produced</h2>
<p><b>Prices are fair (no margin):</b> decimal = 1/p. No OLBG or bookmaker price is read anywhere; OLBG is used only to define the sport taxonomy. A value not on an official page is blank, flagged, and never inferred. Full model code: <code>session-e1161e0e/build.py</code>; data: <code>data/session-e1161e0e/board.json</code>.</p>
<h3>Confidence &amp; the focus window</h3><p>High = model p ≥ 0.70 on an adequate sample; Medium = p ≥ 0.58; else Low. Rugby League (1 game/team) and URC (3 rounds) are capped at Medium. <b>Focus</b> additionally requires the fair American price to sit inside −250…+10,000, i.e. p ≤ 0.7143. At fair odds the band 0.700–0.714 is narrow by arithmetic, which is why this desk has one in-window focus pick and seven labelled shorter-priced Highs.</p>
<h3>NHL</h3><p><code>pct=PTS/(2·GP); rating=0.5+(pct−0.5)·GP/(GP+12)+0.012·(GF−GA)/GP; p_home=0.5+(r_h−r_a)·0.80+0.035</code> (clamped .08–.92). Goal rates shrunk toward 3.05/team with 10-game weight; total line = expected total to nearest 0.5, P(over) from Normal(μ, sd 1.9); puck line ±1.5 from Normal on expected margin (sd 2.0). Inputs: NHL.com standings.</p>
<h3>NBA</h3><p><code>strength=0.5+0.75·(2025-26 win%−0.5); p_home=sigmoid(logit_h−logit_a+0.24)</code>; spread = −round½(Φ⁻¹(p)·11.5). The 0–2-game 2026-27 sample is not used. Totals: not originated (no official pace/efficiency table captured).</p>
<h3>MLB</h3><p><code>pct=0.5+(win%−0.5)·162/202; p_home=sigmoid(logit_h−logit_a+0.17)</code>; run line from Normal(expected margin=(p−0.5)·6, sd 3.2). Totals: not originated (RS/RA splits not captured). Probable pitchers not used — disclosed per row.</p>
<h3>Darts</h3><p>Per-leg <code>p=0.5+0.005·(opponent seed − own seed)</code> (seed = European Tour Order of Merit position after 15 events; a prize-money proxy, so the slope is deliberately conservative), then exact race-to-6 binomials for match winner, −1.5 leg handicap and total legs. Three Friday ties whose seeds were not on the official excerpt read are priced 50/50 and flagged.</p>
<h3>Rugby Union (URC)</h3><p>Expected margin = 0.9·(PD-per-game difference) + 3.0 home; 1X2 from Normal(sd 13) with a ±0.5 draw band; handicap at the rounded expected margin; total from PF/PA per game (sd 11). Three-round sample → Medium cap; Round 4 intervenes before Round 5.</p>
<h3>Rugby League (RLWC)</h3><p>Expected margin = 0.35·(Round-1 margin difference) + 4.0 for a genuine host-nation home game; winner/handicap/total from Normal(sds 16/13). One-game sample, shrunk 65% → Medium cap. Round-3 rows are priced before Round 2 is played and say so.</p>
<h3>Cricket</h3><p><code>p=1/(1+10^(−diff/60))</code> on official ICC T20I ratings (NZ 247 + 6 home points vs India 267). Runs/handicap markets not originated (no venue scoring history captured).</p>"""))

srcs=sorted(set((r["source_name"],r["source_url"]) for r in ROWS))
srows="".join(f"<tr><td>{E(a)}</td><td><a href='{E(b)}' rel='noopener'>{E(b)}</a></td><td>{sum(1 for r in ROWS if r['source_url']==b)}</td></tr>" for a,b in srcs)
open(os.path.join(HERE,"sources.html"),"w").write(page("Sources",
 f"""<h2>Sources — manual review links</h2><p>Every source actually read for this desk, with the number of rows it backs. All are official league/tour/federation pages except the disclosed NBA records archive.</p>
<div class='wide'><table><thead><tr><th>Source</th><th>URL</th><th>Rows</th></tr></thead><tbody>{srows}
<tr><td>NBA 2025-26 final records archive (cross-checked to NBA.com-published figures)</td><td><a href="https://www.basketball-reference.com/leagues/NBA_2026_standings.html" rel="noopener">basketball-reference.com/leagues/NBA_2026_standings.html</a></td><td>27</td></tr>
<tr><td>OLBG sport taxonomy (coverage definition only — never a fact or price source)</td><td><a href="https://www.olbg.com" rel="noopener">olbg.com</a> · repo <code>data/sports.json</code></td><td>—</td></tr>
</tbody></table></div>"""))

FLAGS=[
 ("X-F01","Odds-window arithmetic","Only 1 of 8 High picks (Toronto @ Washington, −242) sits inside −250…+10,000. The other seven are −253 to −537 at fair odds. This is arithmetic, not reticence: ≥70% and ≥−250 overlap only between p 0.700–0.714. Published labelled, per brief.","picks.html"),
 ("X-F02","NBA records source tier","Fixtures are from NBA.com, but the 82-game 2025-26 W-L inputs were read on the Basketball-Reference archive because NBA.com standings render as a script shell in this environment. Headline records (OKC 64-18, BOS 56-26, NYK 53-29, CLE 52-30, DEN 54-28, MIN 49-33, POR 42-40, UTA 22-60) agree with NBA.com-published figures in the captured excerpts. Disclosed on every NBA row.","https://www.nba.com/standings"),
 ("X-F03","NHL standings timestamp","Standings were current as of Oct 22, 3:24 AM EDT; eight Oct 22 evening games post-date the snapshot, so 23-27 Oct prices use pre-Oct-22 form. Stated on every NHL row.","https://www.nhl.com/standings"),
 ("X-F04","NHL Oct 27 slate completeness","Four Oct 27 games were listed at capture; the full slate could not be confirmed game-by-game, so later-listed games may exist. Flagged rather than guessed.","https://www.nhl.com/schedule"),
 ("X-F05","Three PDC ties priced 50/50","Joyce v Wattimena, Ratajski v Chisnall and Clayton v Springer: pairings confirmed on PDC.tv, but their seed numbers were not in the official excerpt read, so both players are priced 2.00 with Low confidence instead of inferring seeds from bracket arithmetic.","https://www.pdc.tv/news/2026/october/21/2026-machineseeker-european-championship-preview"),
 ("X-F06","URC table will move","URC Round 5 is priced from the post-Round-3 table; Round 4 (23-25 Oct) is played in between, so form inputs will be one round stale at kick-off. Re-price after Round 4.","https://stats.unitedrugby.com/match-centre/table/2026-27"),
 ("X-F07","RLWC one-game samples + Round 3 priced blind","All Rugby League prices rest on a single Round-1 margin per team (shrunk 65%, Medium cap). Round-3 rows are priced before Round 2 kicks off and will need repricing. Women's 4th Round-3 fixture (England v Samoa by group rotation) was not confirmed on an official page read and is NOT listed.","https://www.nrl.com/news/2026/10/20/world-cup-team-lists-mens-round-2/"),
 ("X-F08","Cricket series state + unpriced ODI","The 1st T20I (22 Oct, Christchurch) result was not known at capture, so the series score is blank on all cricket rows. The 1st ODI (4 Nov) is listed unpriced because ICC ODI ratings were not read this session.","https://www.icc-cricket.com/rankings/team-rankings/mens/t20i"),
 ("X-F09","Tennis / snooker / esports pairings did not exist at capture","Basel & Vienna draws publish 23-24 Oct; Northern Ireland Open QF pairings were decided on capture day; LoL Worlds Swiss pairings are drawn round-by-round from 23 Oct. All three sports are on the Coverage Register as NOT PRICED with no invented fixtures.","coverage.html"),
 ("X-F10","World Series Games 5-7 are if-necessary","Published with the same regular-season price and an explicit if-necessary label; they vanish if the series ends early. Probable pitchers are not modelled.","https://www.mlb.com/news/2026-mlb-playoff-and-world-series-schedule"),
 ("X-F11","Gaelic football scope call","Earlier boards treated Gaelic football as inside the brief's football exclusion (5 master rows excluded from strict views). Board X keeps that treatment and flags it for the owner's confirmation rather than silently changing scope.","coverage.html"),
 ("X-F12","Markets investigated but not originated","NBA totals, MLB totals, all outright/tournament-winner and correct-score markets: investigated, then left blank because the verified inputs (pace/efficiency, RS/RA splits, full-field ratings) were not captured. See Markets page.","markets.html"),
 ("X-F13","Venues blank on some NBA rows","Oct 23 venues were read from the published schedule; Oct 24-25 venues were not individually confirmed and are left blank rather than filled from memory.","https://www.nba.com/schedule"),
 ("X-F14","Repo integration request (not applied)","Root README/board counts describe the 21-Oct master (317 rows). Board X does not edit other boards' files; a future integration owner may add a Board X pointer. Logged in COORDINATION.md.","../COORDINATION.md"),
]
fl="".join(f"<div class='flag'><b>{E(a)} — {E(b)}</b><p>{E(c)}</p><p><small>Review: <a href='{E(d)}' rel='noopener'>{E(d)}</a> · Status: needs review (non-blocking)</small></p></div>" for a,b,c,d in FLAGS)
open(os.path.join(HERE,"flagged.html"),"w").write(page("Flagged for Review",f"<h2>Flagged for Review ({len(FLAGS)})</h2><p>Every irregularity, gap and judgement call on this desk, with its source link for manual review. None of these blocks publication; nothing here was silently filled in.</p>{fl}"))

json.dump({"flags":[{"id":a,"title":b,"detail":c,"review":d} for a,b,c,d in FLAGS],"coverage":[{"sport":a,"status":b,"note":c} for a,b,c in COVERAGE]},
  open(os.path.join(HERE,"..","data","session-e1161e0e","flagged.json"),"w"),indent=1,ensure_ascii=False)

open(os.path.join(HERE,"verification.html"),"w").write(page("Verification","""<h2>Verification</h2>
<p>Run <code>python3 session-e1161e0e/build.py &amp;&amp; python3 session-e1161e0e/render.py &amp;&amp; python3 session-e1161e0e/verify.py</code>. The verifier re-derives every price from the literal inputs in <code>build.py</code> and asserts, line by line:</p>
<ul><li>every row dated ≥ 2026-10-23 (nothing already played); every row has an http(s) official source URL;</li>
<li>Decimal = 1/p and American conversion recomputed for every pick; focus band exactly p∈[0.70,0.7143];</li>
<li>confidence grades match the published rule incl. the Rugby League / URC Medium caps;</li>
<li>every High pick has a unique written prediction of ≥30 words naming the pick; no duplicate prediction text desk-wide;</li>
<li>unpriced rows publish no pick and no price; all internal links resolve; byte-identical rebuild.</li></ul>
<p>Live sources read on 2026-10-22: NHL.com standings &amp; schedule releases, NBA.com schedule release, MLB.com World Series schedule &amp; FAQ, PDC.tv European Championship preview, URC Match Centre table &amp; unitedrugby.com fixtures, NRL.com World Cup Round-2 team lists (men &amp; women), ICC.com tour schedule &amp; T20I rankings, ATP Tour calendar, Riot LoL Esports Worlds primer. Result of the last run is recorded in <code>COORDINATION.md</code> (Board X completion record).</p>"""))
print("rendered:", ", ".join(sorted(u for u,_ in NAV)))

"""Fail-closed evidence desk. stdlib only; never invent a fixture or rating."""
import datetime as dt
import hashlib
import html
import json
import pathlib
import re
from model import originate

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT/'session-d28c49c5'
DATA = ROOT/'data/session-d28c49c5'
PEER = ROOT/'data/session-f0622b6e/desk.json'
NOW = '2026-10-22T12:00:00+00:00' # fixed review cutoff, not a retrieval timestamp
SPORTS = {
 'Tennis':'https://www.wtatennis.com/tournaments', 'Basketball':'https://www.nba.com/schedule',
 'Baseball':'https://www.mlb.com/schedule', 'Ice Hockey':'https://www.nhl.com/schedule',
 'Darts':'https://www.pdc.tv/tournaments', 'Snooker':'https://www.wst.tv/',
 'Handball':'https://www.eurohandball.com/', 'Volleyball':'https://www.volleyballworld.com/',
 'Rugby Union':'https://www.world.rugby/', 'Rugby League':'https://www.nrl.com/draw/',
 'Cricket':'https://www.icc-cricket.com/fixtures-results', 'eSports':'https://lolesports.com/',
 'Badminton':'https://bwfbadminton.com/calendar/', 'Aussie Rules':'https://www.afl.com.au/aflw/fixture',
 'Golf':'https://www.pgatour.com/schedule', 'Motor Racing':'https://www.formula1.com/en/racing/2026',
 'Greyhounds':'https://www.gbgb.org.uk/racing/', 'Table Tennis':'https://www.ittf.com/tournaments/',
}
def slug(s): return re.sub('[^a-z0-9]+','-',s.lower()).strip('-')
def esc(s): return html.escape(str(s),quote=True)
def link(url,label='Official source'):
 return f'<a href="{esc(url)}" rel="noopener noreferrer">{esc(label)}</a>' if url.startswith('https://') else ''
def load_evidence():
 manifest=json.loads((DATA/'manifest.json').read_text()) if (DATA/'manifest.json').exists() else []
 payload={}
 for m in manifest:
  if m.get('status') != 200 or not m.get('file'): continue
  body=(DATA/m['file']).read_bytes()
  if hashlib.sha256(body).hexdigest()!=m['sha256']: raise ValueError('Evidence hash mismatch: '+m['id'])
  if m['id']!='olbg': payload[m['id']]=json.loads(body)
 return manifest,payload

def fixtures(manifest,payload):
 rows=[]
 meta={m['id']:m for m in manifest}
 for day in payload.get('nhl_schedule',{}).get('gameWeek',[]):
  for g in day.get('games',[]):
   def name(t): return (t['placeName']['default']+' '+t['commonName']['default']).strip()
   rows.append(dict(id='nhl-'+str(g['id']),sport='Ice Hockey',competition='NHL',side_a=name(g['awayTeam']),side_b=name(g['homeTeam']),start_utc=g['startTimeUTC'],venue=g.get('venue',{}).get('default',''),state=g['gameState'],official_url=meta['nhl_schedule']['url'],evidence='nhl_schedule.raw',pointer=f"gameWeek[date={day['date']}].games[id={g['id']}]",captured_at=meta['nhl_schedule']['retrieved_at']))
 for day in payload.get('mlb_schedule',{}).get('dates',[]):
  for g in day.get('games',[]):
   a=g['teams']['away']['team']['name']; b=g['teams']['home']['team']['name']
   # A placeholder team is not a confirmed opponent.
   if not a or not b or 'TBD' in a+b: continue
   rows.append(dict(id='mlb-'+str(g['gamePk']),sport='Baseball',competition='MLB',side_a=a,side_b=b,start_utc=g.get('gameDate',''),venue=g.get('venue',{}).get('name',''),state=g.get('status',{}).get('detailedState',''),official_url=meta['mlb_schedule']['url'],evidence='mlb_schedule.raw',pointer=f"dates[date={day['date']}].games[gamePk={g['gamePk']}]",captured_at=meta['mlb_schedule']['retrieved_at']))
 for r in rows:
  r.update(verification='fixture fields confirmed in captured official response',pick='',confidence='',fair_odds='',prediction='')
 return sorted(rows,key=lambda r:(r['start_utc'],r['id']))

def audit(rows):
 peer=json.loads(PEER.read_text())
 result=[]
 for r in peer['rows']:
  matching=[f for f in rows if f['sport']==r['sport'] and f['side_a']==r['side_a'] and f['side_b']==r['side_b'] and f['start_utc']==r['start_utc']]
  issues=['Model inputs, form claims and calibration not independently verified; betting outputs withheld.']
  if not matching: issues.insert(0,'No exact opponent/order/UTC-time match in this capture. This is not proof the fixture is false; coverage is partial.')
  p=r.get('prediction') or {}
  fair=p.get('fair_decimal')
  implied=1/float(fair) if fair else None
  if r.get('confidence')=='High' and implied is not None and implied<.70:
   issues.append(f"Prior High label conflicts with its own selection fair odds: {fair} implies {implied:.2%}, below 70%.")
  expired=bool(r.get('start_utc') and r['start_utc']<'2026-10-22T12:00:00Z')
  if expired: issues.append('Start precedes the fixed review cutoff; do not present as an upcoming pick.')
  result.append(dict(id=r['id'],sport=r['sport'],claimed_matchup=r['matchup'],claimed_start_utc=r['start_utc'],fixture_match=bool(matching),official_url=r['official_url'],issues=issues,prior_confidence=r.get('confidence',''),prior_selection_fair_decimal=fair,prior_selection_implied_probability=implied,confirmed_pick='',confirmed_confidence='',confirmed_odds=''))
 return result

def table(headers,rows):
 return '<div class="table"><table><thead><tr>'+''.join('<th scope="col">'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'

def main():
 OUT.mkdir(exist_ok=True)
 manifest,payload=load_evidence(); rows=fixtures(manifest,payload); reviewed=audit(rows)
 lines=originate(rows,payload.get('nhl_standings',{}))
 (DATA/'exploratory_lines.json').write_text(json.dumps(lines,indent=2)+'\n')
 report={'review_cutoff_utc':NOW,'scope':'All 233 rows of data/session-f0622b6e/desk.json only; not a verification of all repo facts.', 'fixtures':rows,'review':reviewed,'manifest':manifest}
 (DATA/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 nav=[('index.html','Overview'),('matches.html','Official fixtures'),('review.html','Row audit'),('markets.html','Markets'),('lines.html','Exploratory lines'),('coverage.html','Coverage'),('flagged.html','Flagged for Review'),('sources.html','Evidence')]
 def page(path,title,body):
  (OUT/path).write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>'+esc(title)+' · OLBG Evidence Desk</title><link rel="stylesheet" href="style.css"><body><header><a class="brand" href="index.html">OLBG <span>Evidence desk</span></a><span>Independent review · 22 Oct 2026</span></header><nav aria-label="Main">'+''.join(f'<a {"aria-current=page" if path==u else ""} href="{u}">{t}</a>' for u,t in nav)+'</nav><main><p class="eyebrow">SOURCE-FIRST RESEARCH / BOARD AD</p><h1>'+esc(title)+'</h1>'+body+'</main><footer>Partial coverage. No guaranteed outcomes. Model estimates are not official facts. <a href="../index.html">Repository dashboard</a> · <a href="../data/session-d28c49c5/report.json">Download audit JSON</a></footer><script src="app.js"></script></body></html>')
 warning='<aside><strong>Verification boundary.</strong> Fixture confirmation does not verify betting value, current form, or a prediction. Unconfirmed outputs are deliberately blank. No high-confidence recommendations are released by this desk.</aside>'
 def fixture_table(items):
  return table(['Sport / competition','Away / side A','Home / side B','Start UTC','Venue','State at capture','Pick','Confidence','Fair odds','Official evidence'],[(esc(r['sport']+' / '+r['competition']),esc(r['side_a']),esc(r['side_b']),esc(r['start_utc']),esc(r['venue']),esc(r['state']),'','','',link(r['official_url'])+'<br>'+link('../data/session-d28c49c5/'+r['evidence'],'Captured bytes')+'<small>'+esc(r['pointer'])+'</small>') for r in items])
 conflicts=sum(any('below 70%' in i for i in r['issues']) for r in reviewed)
 page('index.html','A clearer view of the evidence', '<p class="intro">Official fixture snapshots, transparent coverage gaps, and a row-by-row review of an existing betting desk. No unsupported certainty.</p><section class="stats">'+''.join(f'<article><strong>{n}</strong><span>{label}</span></article>' for n,label in [(len(rows),'official fixture records'),(len(reviewed),'prior rows audited'),(conflicts,'High / probability conflicts'),(0,'released betting picks')])+'</section>'+warning+'<h2>Explore by sport</h2><div class="cards">'+''.join(f'<a href="{slug(s)}.html"><strong>{esc(s)}</strong><span>{sum(r["sport"]==s for r in rows)} captured fixtures · coverage not complete →</span></a>' for s in SPORTS)+'</div><h2>What this review does not claim</h2><p>This is not a full live OLBG mirror or an exhaustive market feed. No calibration or verified full-form dataset is available for releasing production lines or ≥30-word high-confidence predictions. An explicitly uncalibrated NHL baseline is provided separately for research, always labeled Low. Existing peer pages are not rewritten; their disputed claims are listed here for review.</p>')
 page('matches.html','Official fixture records',warning+'<p>Only exact fields parsed from hash-checked official response bytes. Records may include completed or in-progress games; check state and timestamp. This is a snapshot, not a live feed.</p><label>Filter fixtures <input type="search" placeholder="Team, competition, date…" data-filter></label>'+fixture_table(rows))
 for s,url in SPORTS.items():
  subset=[r for r in rows if r['sport']==s]
  page(slug(s)+'.html',s,warning+'<p>'+link(url,'Official governing source for manual review')+'</p>'+('<p>Captured records below; no claim of exhaustive coverage.</p>'+fixture_table(subset) if subset else '<p>No fixture fields independently confirmed by this capture. Entries and betting outputs withheld; coverage needs review.</p>'))
 audit_rows=[(esc(r['id']),esc(r['sport']),esc(r['claimed_matchup'])+'<small>Prior claim, not an adopted fact</small>',esc(r['claimed_start_utc']), 'Exact fixture match' if r['fixture_match'] else 'Unverified in this capture', '<ul>'+''.join('<li>'+esc(i)+'</li>' for i in r['issues'])+'</ul>',link(r['official_url'])) for r in reviewed]
 page('review.html','Row-by-row integrity review','<p>Every row of the scoped 233-row desk is listed. Original matchup and time are shown only as claims under review. Official URLs are review destinations, not proof that every linked claim was checked.</p><label>Search review <input type="search" data-filter></label>'+table(['Prior row ID','Sport','Claimed matchup','Claimed UTC time','Fixture check','Findings','Official review link'],audit_rows))
 page('flagged.html','Flagged for Review','<p>Non-blocking publication flags. No disputed betting values are promoted into confirmed columns. All scoped rows still lack independently verified model inputs/calibration.</p><h2>Confidence assignment defect</h2><p>The prior generator assigns High when a prewritten prediction exists (lines 1387–1410), not from a calibrated confidence gate. '+link('https://github.com/buffedlizard55-lab/OLBG4/blob/36c7bc1387122ab7cfa347aba69671fd7272414c/scripts/session-f0622b6e/originate_desk.py#L1387-L1410','Review pinned code')+'</p><h2>Rows requiring review</h2>'+table(['Row ID','Sport','Prior claimed matchup','Claimed UTC','Fixture check','Issues','Official review link'],audit_rows))
 page('markets.html','Market research & release policy',warning+'<p>Market families below are an investigation checklist, not a claim that a bookmaker offers them for every fixture. Own model prices must be distinguished from observed executable bookmaker prices.</p>'+table(['Sport','Market families to investigate','Release status','Official review destination'],[(esc(s),'Match winner; handicap/spread; total; sport-specific derivatives','Withheld: verified inputs + market rules + calibration required',link(u)) for s,u in SPORTS.items()])+'<h2>Odds-window mathematics</h2><p>American −250 implies 250 / 350 = 71.43%; +10000 implies 100 / 10100 = 0.99%. At fair odds, a ≥70% selection inside that window lies only between −250 and approximately −233.33. A handicap that moves the price into the window does not automatically preserve a 70% win chance. Observed odds alone do not establish a predictive edge.</p>')
 page('lines.html','Own lines · exploratory NHL baseline', '<aside><strong>Not calibrated, not High confidence.</strong> Every value below is a model estimate, not a fact confirmed by the NHL or an executable bookmaker quote. All confidence labels are Low regardless of price. No advice to bet is released.</aside><p>Inputs: exact team games played, goals for and goals against from the captured NHL standings. Each rate is shrunk toward the league mean using a fixed 20-game prior. Expected goals A = shrunk GF rate A × shrunk GA rate B / league scoring rate. Scores are independent Poisson variables; a regulation tie is allocated 50/50 for the winner estimate. Handicap and totals refer to regulation-score proxies only, not full-game bookmaker settlement.</p><p><strong>Limitations:</strong> source goal totals include overtime/shootout scoring, so regulation rates are only proxies. No goalie, injury, home advantage, strength-of-schedule, player form or out-of-sample validation inputs are available. These assumptions must be resolved before production release. No bookmaker odds are used to set the probabilities. Fair decimals are 1/p; fair American odds use the standard reciprocal conversion. No vig is added.</p>'+table(['Fixture / UTC','Market','Selection A','Model p(A)','Fair A','Selection B','Model p(B)','Fair B','Confidence','Official inputs'],[(esc(r['matchup'])+'<small>'+esc(r['start_utc'])+'</small>',esc(r['market']),esc(r['selection_a']),f"{r['p_a']:.2%}",f"{r['fair_decimal_a']:.2f} / {r['fair_american_a']:+d}",esc(r['selection_b']),f"{r['p_b']:.2%}",f"{r['fair_decimal_b']:.2f} / {r['fair_american_b']:+d}",'Low',link(r['official_url'],'Standings')+' · '+link(r['fixture_source'],'Fixture')) for r in lines])+'<p>'+link('../data/session-d28c49c5/exploratory_lines.json','Download exact inputs and model outputs')+'</p>')
 page('coverage.html','Coverage & exclusions','<p>Excluded: soccer, boxing, UFC, MMA, football (including American and Gaelic football), hurling, horse racing, cycling and specials. Australian rules is retained as an explicitly separate category; scope ambiguity remains reviewable. The catalog below is a research checklist, not a verified current OLBG taxonomy.</p>'+table(['Category','Captured records','Coverage limitation','Official destination'],[(esc(s),str(sum(r['sport']==s for r in rows)),'Partial NHL / MLB snapshot only' if any(r['sport']==s for r in rows) else 'Not captured; unverified; no fabricated entries',link(u)) for s,u in SPORTS.items()]))
 source_rows=[]
 for m in manifest:
  source_rows.append((esc(m['id']),esc(m['status']),esc(m['retrieved_at']),esc(m.get('sha256','')),link(m['url']),link('../data/session-d28c49c5/'+m['file'],'Captured response') if m.get('file') else esc(m.get('error',''))))
 page('sources.html','Evidence & reproducibility','<p>Captured response hashes establish byte integrity, not truth of unrelated claims. Retrieval timestamps are preserved from the runner. Rebuild: <code>python scripts/session-d28c49c5/build.py</code>. Run tests: <code>python scripts/session-d28c49c5/test_build.py</code>.</p>'+table(['Capture','HTTP status','Retrieved UTC','SHA-256','Source','Bytes / error'],source_rows)+'<h2>OLBG investigation</h2><p>The OLBG response is retained for inspection only; no hidden API endpoints, sport IDs or market completeness are asserted without parsing and independent verification. Prior reverse-engineering claims are not inherited.</p><h2>Review scope</h2><p>The peer desk is read-only. All its rows are mechanically checked for exact captured fixture matches and confidence/price inconsistencies. This does not certify all text, all repository datasets, or all official external links as available. Uncaptured facts remain unverified.</p>')
 print(f'{len(rows)} official records; {len(reviewed)} reviewed rows; {conflicts} probability conflicts')
if __name__=='__main__': main()

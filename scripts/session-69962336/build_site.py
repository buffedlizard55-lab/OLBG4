"""Evidence-first dashboard. Adapted collector/parsers credited to session e880ce67.
No copied betting prose; heuristic prices are quarantined as research, never tips.
"""
from pathlib import Path
from datetime import datetime, timezone
import json, html, gzip, hashlib
from urllib.parse import urlparse
import sys
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'data/session-69962336'
OUT=ROOT/'session-69962336'
sys.path.insert(0,str(Path(__file__).parent))
from spec import OLBG_URLS, OFFICIAL
E=lambda x:html.escape(str(x if x is not None else ''),quote=True)
def read(name): return json.loads((DATA/name).read_text())
def link(url,label): return f'<a href="{E(url)}" rel="noopener noreferrer">{E(label)}</a>' if url else ''
SPORTS={
'golf':('Golf','pga_leaderboard'),'volleyball':('Volleyball','cev_champions_league'),
'rugby_union':('Rugby Union','epcr_fixtures_en'),'cricket':('Cricket','icc_fixtures_results'),
'snooker':('Snooker','wst_matches'),'darts':('Darts','pdc_tournaments'),
'baseball':('Baseball','mlb_sched'),'gaelic':('Gaelic Sports','gaa_api_fixtures'),
'greyhounds':('Greyhounds','gbgb_results_today'),'tennis':('Tennis','wta_calendar'),
'motor_racing':('Motor Racing','f1_racing'),'handball':('Handball','ehfcl_matches'),
'ice_hockey':('Ice Hockey','nhl_standings'),'basketball':('Basketball','nba_schedule'),
'rugby_league':('Rugby League','superleague_fixtures')}
def sportkey(r): return 'gaelic' if r['sport_key'] in ('hurling','gaelic_football') else r['sport_key']
def table(headers,rows):
 return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+E(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+(''.join('<tr>'+''.join('<td>'+str(v)+'</td>' for v in r)+'</tr>' for r in rows) or '<tr><td colspan="20">No records meet this publication gate.</td></tr>')+'</tbody></table></div>'
CSS='''*{box-sizing:border-box}body{margin:0;background:#f3f6fa;color:#15273d;font:16px/1.55 system-ui,sans-serif}header{background:#102c40;color:white;padding:22px max(24px,calc((100vw - 1240px)/2))}header strong{font-size:23px}nav{display:flex;gap:18px;flex-wrap:wrap;margin-top:12px}header a{color:#c8edf0}main{max-width:1240px;margin:auto;padding:32px 24px}a{color:#066b78}h1{font-size:clamp(27px,4vw,40px);line-height:1.2}h2{margin-top:32px}.muted,small{color:#54677a}.notice{padding:18px 22px;border-left:5px solid #b77a12;background:#fff7df;margin:20px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:15px}.card{background:white;border:1px solid #d9e3ec;border-radius:12px;padding:20px}.number{font-size:32px;font-weight:750}.scroll{overflow:auto;background:white;border:1px solid #d9e3ec;border-radius:12px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{text-align:left;padding:14px;vertical-align:top;border-bottom:1px solid #e1e8ef}th{background:#eaf0f5;white-space:nowrap}td{min-width:120px}td:first-child{min-width:180px}.badge{background:#e7eff4;padding:4px 8px;border-radius:20px;font-size:12px}footer{margin-top:40px;border-top:1px solid #ccd6df;padding-top:20px}input{padding:12px;width:100%;border:1px solid #bccbd6;border-radius:7px;margin-bottom:16px}'''
NAV=[('index.html','Overview'),('picks.html','Picks & predictions'),('matches.html','Confirmed matches'),('listings.html','OLBG inventory'),('markets.html','Research lines'),('flagged.html','Flagged for Review'),('sources.html','Sources'),('method.html','Method')]
def page(name,title,body,stamp):
 nav=''.join(link(p,t) for p,t in NAV)
 text=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · OLBG evidence desk</title><link rel="stylesheet" href="style.css"></head><body><header><strong>OLBG / Evidence desk</strong><div>15 sports · source-first research · October 26 refresh</div><nav>{nav}</nav></header><main><small>Source capture started {E(stamp)} · Times UTC</small><h1>{E(title)}</h1>{body}<footer>Independent research, not OLBG. No guaranteed outcomes. Only bet where lawful, age 21+ where applicable. Never stake money you cannot afford to lose. <a href="../index.html">Repository landing page</a></footer></main></body></html>'''
 (OUT/name).write_text(text)
def main():
 OUT.mkdir(exist_ok=True)
 olbg=read('olbg.json'); ev=read('evidence.json'); desk=read('desk.json'); manifest=read('raw/manifest.json')
 stamp=olbg['captured_utc']; cutoff=stamp
 # Strict, exact-time fixture identity: never inherit loose six/eight-hour matching.
 fixtures=[]
 for group in ('ice_hockey','baseball'):
  seen=set()
  for f in ev[group]['fixtures']:
   if not f.get('start_utc') or f['start_utc']<=cutoff or f['id'] in seen: continue
   seen.add(f['id']); fixtures.append((group,f))
 rows=[]
 for r in desk['rows']:
  if r['start_utc']<=cutoff:continue
  r=dict(r); r['strict_identity']=False
  for group,f in fixtures:
   if r['sport_key']!=group:continue
   delta=abs((datetime.fromisoformat(r['start_utc'].replace('Z','+00:00'))-datetime.fromisoformat(f['start_utc'].replace('Z','+00:00'))).total_seconds())
   if delta>900:continue
   # Recheck canonical side identities using the adapter, then official fixture ID/time.
   from originate import ADAPTER
   m=ADAPTER.get(r['sport'],lambda *_:None)(r,ev)
   if m and m.get('fixture') and m['fixture']['id']==f['id']:
    r['strict_identity']=True;r['fixture_url']=m['fixture_url'];r['official_start_utc']=f['start_utc'];r['time_difference_seconds']=int(delta);break
  if not r['strict_identity']:
   r['pick']=None;r['markets']={};r['status']='withheld'
  rows.append(r)
 # No automatic High grade: heuristic thresholds are not calibration evidence.
 # Keep sourced own-price calculations separately, not as actionable recommendations.
 research=[r for r in rows if r['strict_identity'] and r.get('markets')]
 result={'capture_utc':stamp,'rows':rows,'research_count':len(research),'published_predictions':[]}
 (DATA/'publication.json').write_text(json.dumps(result,indent=2)+'\n')
 confirmed=[r for r in rows if r['strict_identity']]
 def sources(r):
  key=sportkey(r); reference=OFFICIAL[SPORTS[key][1]]
  return link(r.get('fixture_url') if r['strict_identity'] else reference,'Official fixture' if r['strict_identity'] else 'Official reference (not confirmation)')+'<br>'+link(r['olbg_url'],'OLBG listing')
 def matchtable(rs):
  return table(['Sport / event','Starts UTC (OLBG)','Official confirmation','Selection','Confidence','Sources'],[[E(r['sport'])+'<br><strong>'+E(r['event_name'])+'</strong>',E(r['start_utc']),('Official: '+E(r['official_start_utc'])+'<br>'+('Start times agree' if not r['time_difference_seconds'] else 'Timing discrepancy — review; no pick')) if r['strict_identity'] else 'Unconfirmed — withheld','','',sources(r)] for r in rs])
 summary='<div class="cards">'+''.join(f'<div class="card"><div class="number">{n}</div>{label}</div>' for n,label in [(len(rows),'upcoming named OLBG events'),(len(confirmed),'official identity crosswalks'),(0,'published betting picks'),(len(research),'research-priced matches')])+'</div>'
 notice='<div class="notice"><strong>No actionable picks cleared the full evidence standard.</strong> The 75-prediction daily target is not met. No High confidence, injury clearance, or bet availability is inferred from a listing or a price. Blank selection and confidence cells are intentional.</div>'
 coverage=[]
 for key,(label,ref) in SPORTS.items():
  rs=[r for r in rows if sportkey(r)==key]; cs=sum(r['strict_identity'] for r in rs)
  coverage.append([link(key+'.html',label),len(rs),cs,'0 / 5','Needs review',link(OFFICIAL[ref],'Official reference')])
 body='<p class="muted">A clear separation between what OLBG lists, what an official source confirms, and what is safe to publish as a researched selection.</p>'+summary+notice+'<h2>Executive summary · October 26 UTC</h2><p>No qualifying highest-confidence selections are published for today or later fixtures. The research lines are uncalibrated estimates, not bookmaker offers. They do not establish an edge or justify a High label.</p><p><strong>Where are the picks?</strong> '+link('picks.html','Picks & predictions')+' is the only recommendations page. '+link('listings.html','OLBG inventory')+' is discovery, not a picks list.</p><h2>Coverage and daily shortfall</h2>'+table(['Sport','OLBG events','Confirmed','Written / target','Status','Source'],coverage)
 page('index.html','Upcoming sports, without invented certainty',body,stamp)
 page('picks.html','Picks & written predictions',notice+'<p>Published predictions: <strong>0</strong>. We have not filled the quota with repetitive prose, unsupported facts, or low-quality favourites. Current form, recent results, injuries and a defensible probability must be documented for each future recommendation.</p>'+table(['Selection','Market','Confidence','Prediction','Official source'],[]),stamp)
 page('matches.html','Officially reconciled OLBG matches','<p>Only exact side identity and UTC start-times within 15 minutes are admitted; both source times are displayed separately. Any timing difference is flagged, not silently reconciled. Selection cells remain blank until analysis clears publication.</p>'+matchtable(confirmed),stamp)
 page('listings.html','OLBG discovery inventory','<div class="notice">These are OLBG-discovered named events, not a complete fixture feed or proof that every market accepts tips. Official-reference links on unconfirmed rows are review destinations only. Outrights and unnamed events are preserved in the downloadable raw inventory, but excluded here.</div>'+matchtable(rows)+'<p>'+link('../data/session-69962336/olbg.json','All parsed events and selections (JSON)')+'</p>',stamp)
 for key,(label,ref) in SPORTS.items():
  rs=[r for r in rows if sportkey(r)==key]
  page(key+'.html',label,notice+'<p>'+link(OFFICIAL[ref],'Official source for manual review')+'</p>'+matchtable(rs),stamp)
 markets=[]
 for r in research:
  for market,v in r['markets'].items():
   for side,quote in v.items():
    if isinstance(quote,dict) and 'probability' in quote:
     markets.append([E(r['event_name']),E(v.get('label',market)),E(v.get(side+'_selection',r.get(side+'_name',side))),E(quote['american']),E(quote['decimal']),E(quote['probability']),'Uncalibrated estimate — not a pick',sources(r)])
 page('markets.html','Own research lines · not recommendations','<div class="notice">These estimates use published team records and explicit heuristic assumptions inherited from the earlier research desk. They are not confirmed facts, offered odds, or calibrated winning chances. No confidence label or written tip is attached. Injuries, lineups and starting players have not been established.</div>'+table(['Match','Market','Side','Own American','Own decimal','Estimated probability','Status','Sources'],markets)+'<p>'+link('../data/session-69962336/desk.json','Calculations and assumptions')+'</p>',stamp)
 flags=[['PREDICTION SHORTFALL','0 of 75 minimum daily written predictions cleared. No confidence inferred from market prices.',link('picks.html','Publication register')],['LEGACY LANDING PAGE','Older root dashboard advertises -526 and -455, outside the requested -250 floor; October 24 cutoff is stale for October 26.',link('../index.html','Historical root desk')],['HEURISTIC PRICING','Existing copied calculator labels High by probability threshold alone. That label is not used for recommendations here.',link('markets.html','Research lines')],['COMPLETENESS','Only public tipped hub events were collected. Pagination, untranslated fields, hidden events and tip-submission eligibility are not proven.',link('listings.html','OLBG inventory')],['INJURIES','No official injury/lineup reconciliation was completed. No absence of injury is claimed.',link('sources.html','Capture register')]]
 for r in rows:
  if r['strict_identity'] and r['time_difference_seconds']: flags.append([E(r['event_name']),E(f"OLBG start {r['start_utc']}; official start {r['official_start_utc']}. {r['time_difference_seconds']} seconds difference. No recommendation published."),sources(r)])
  if not r['strict_identity']: flags.append([E(r['event_name']),'Official fixture within the 15-minute identity reconciliation window not established; selection, line and confidence withheld.',sources(r)])
 for m in manifest['entries']:
  if m.get('status')!=200 or not m.get('file'): flags.append([E(m['key']),E(f"HTTP {m.get('status')}: {m.get('error','No usable response')}"),link(m['url'],'Requested source')])
 page('flagged.html','Flagged for Review',table(['Item','Finding / action','Review sources'],flags),stamp)
 srcrows=[]
 for m in manifest['entries']:
  srcrows.append([E(m['key']),link(m['url'],'Official endpoint' if m['group']!='olbg' else 'OLBG endpoint'),E(m.get('status')),E(m.get('fetched_utc')),link('../'+m['file'],'Captured bytes') if m.get('file') else '',E(m.get('sha256',''))])
 page('sources.html','Source capture register','<p>HTTP 200 does not establish that a page contains usable facts. Response bodies may be client-side shells, redirects or stale content. Hashes cover decompressed response bytes. The manifest preserves failures as well as successes.</p>'+table(['Key','Source URL','HTTP','Fetched UTC','Evidence','SHA-256'],srcrows),stamp)
 page('method.html','Publication rules and limitations','''<h2>Evidence before prose</h2><ol><li>Read OLBG public sport hubs and SvelteKit tip payloads; preserve original bytes and hashes.</li><li>Parse official NHL and MLB fixture responses. Only canonical team identities and UTC starts within 15 minutes establish a candidate crosswalk here; both original times are retained and differences flagged. Other sports remain discovery-only unless an official fixture parser is supplied.</li><li>Leave unsupported factual fields blank. Estimates are not facts; keep heuristic own lines on a separate research page.</li><li>Do not promote a numerical probability threshold into High confidence without calibration, injury and lineup research, suitable sample history and an actual comparable offered market.</li><li>Do not write a prediction solely to hit a five-per-sport quota. No automatic template is published as original editorial analysis.</li></ol><h2>Odds restriction</h2><p>The requested American window is −250 through +10000 for the actual selection price. Fair prices and offered market prices must be tested separately. A 70% implied probability corresponds to approximately −233; −250 implies 71.43%. A High label is not automatically justified by either price.</p><h2>Market coverage</h2><p>The copied research calculator produces two-way winner, spread and total estimates for eligible fixtures. Draw markets, player props, race markets and sport-specific markets have not been exhaustively assessed. No claim of every market or every OLBG match is made.</p><h2>Time and freshness</h2><p>October 26 UTC can be October 25 in Los Angeles. All displayed starts use UTC. Snapshot pages do not automatically become fresh; compare the capture timestamp and recheck official sources before use.</p><h2>Reuse and audit scope</h2><p>Collector, spec, evidence parser and research calculator adapted from repository session e880ce67, with isolated paths and October 26 date targets. Review covered those paths, publication gates and the root landing claims; it was not a line-by-line certification of the entire large historical repository. The repository's existing scheduled three-league pipeline is separate and does not refresh this desk.</p>''',stamp)
 (OUT/'style.css').write_text(CSS)
 print(f'Built {len(list(OUT.glob("*.html")))} pages; {len(rows)} listings, {len(confirmed)} crosswalks, {len(research)} research matches; 0 recommendations')
if __name__=='__main__':main()

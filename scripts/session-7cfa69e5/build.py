"""Reproducible evidence desk. Official facts and our estimates are distinct."""
import gzip,hashlib,html,json,math,pathlib,re
from datetime import datetime,timezone
ROOT=pathlib.Path(__file__).resolve().parents[2]; D=ROOT/'data/session-7cfa69e5'; O=ROOT/'session-7cfa69e5'
def load(p):return json.loads(p.read_text())
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def esc(x):return html.escape(str(x if x is not None else ''))
def link(u,label='Official source'):return '<a href="'+esc(u)+'" target="_blank" rel="noopener noreferrer">'+esc(label)+'</a>' if u else ''
manifest=load(D/'capture/manifest.json'); records=manifest['records']; at=manifest['captured_utc']; cutoff=datetime.fromisoformat(at)
targets=load(ROOT/'scripts/session-7cfa69e5/targets.json'); sports={t['sport']:t['url'] for t in targets if t.get('sport')}
byid={r['id']:r for r in records}
def read(id):
    r=byid.get(id,{})
    if r.get('status')!=200 or not r.get('file'):return None
    b=gzip.decompress((D/'capture'/r['file']).read_bytes());assert hashlib.sha256(b).hexdigest()==r['sha256']
    try:return json.loads(b)
    except (ValueError,UnicodeError):return None
rows=[];markets=[];flags=[]
def flag(s,title,detail,url):flags.append({'sport':s,'title':title,'detail':detail,'source':url})
def add(id,sport,a,b,start,source,venue='',state='',extra=None):
    if not a or not b or not start:return
    try:
        if not cutoff < datetime.fromisoformat(start.replace('Z','+00:00')) < datetime(2026,11,3,tzinfo=timezone.utc):return
    except ValueError:return
    if any(r['id']==str(id) for r in rows):return
    rows.append(dict(id=str(id),sport=sport,away=a,home=b,start_utc=start,venue=venue,source=source,state=state,own_winner=None,confidence=None,olbg_event=None,**(extra or {})))
nhl=read('nhl_sched_2026_10_23');standings=read('nhl_standings_now')
teamstats={r['teamAbbrev']['default']:r for r in (standings or {}).get('standings',[])}
nhl_games={}
if nhl:
    for day in nhl.get('gameWeek',[]):
        for g in day.get('games',[]):
            if g.get('gameState') not in ('FUT','PRE'):continue
            def name(t):return t.get('placeName',{}).get('default','')+' '+t.get('commonName',{}).get('default','')
            add(g['id'],'Ice Hockey',name(g['awayTeam']),name(g['homeTeam']),g.get('startTimeUTC'),'https://api-web.nhle.com/v1/schedule/2026-10-23',g.get('venue',{}).get('default',''),g.get('gameState',''))
            nhl_games[str(g['id'])]=g
mlb=read('mlb_ws_schedule')
for day in (mlb or {}).get('dates',[]):
    for g in day.get('games',[]):
        if g.get('status',{}).get('abstractGameState')!='Preview' or g.get('status',{}).get('startTimeTBD'):continue
        add(g['gamePk'],'Baseball',g['teams']['away']['team']['name'],g['teams']['home']['team']['name'],g.get('gameDate'),'https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-04&hydrate=probablePitcher(note),team,venue,linescore',g.get('venue',{}).get('name',''),g['status']['detailedState'],{'conditional':g.get('ifNecessary')=='Y'})
# Only explicit UTC fields are used; local times are never guessed.
for target in ['euroleague_games_E2026','eurocup_games_U2026']:
    feed=read(target)
    for g in (feed or {}).get('data',[]):
        if g.get('played') or not g.get('confirmedDate') or not g.get('confirmedHour'):continue
        road=(g.get('road') or {}).get('club') or {};home=(g.get('local') or {}).get('club') or {}
        if road.get('isVirtual') or home.get('isVirtual'):continue
        add(g['identifier'],'Basketball',road.get('name'),home.get('name'),g.get('utcDate'),byid[target]['url'],(g.get('venue') or {}).get('name',''),g.get('gameStatus',''))
for g in read('liiga_games_2027') or []:
    if g.get('end'):continue
    add('liiga_'+str(g['id']),'Ice Hockey',(g.get('awayTeam') or {}).get('teamName'),(g.get('homeTeam') or {}).get('teamName'),g.get('start'),byid['liiga_games_2027']['url'],'','Upcoming (no end timestamp)')
# Fair research prices: no bookmaker odds are used or relabelled.
def odds(p):
    if not 0<p<1:raise ValueError('invalid probability')
    return round(-100*p/(1-p)) if p>=.5 else round(100*(1-p)/p)
def pmf(mu):return [math.exp(-mu)*mu**i/math.factorial(i) for i in range(60)]
def price(row,label,p):
    markets.append({'event_id':row['id'],'sport':row['sport'],'match':row['away']+' @ '+row['home'],'selection':label,'probability':round(p,8),'fair_american':odds(p),'fair_decimal':round(1/p,4),'confidence':'Low','source':row['source'],'inputs_source':'https://api-web.nhle.com/v1/standings/now','type':'Our estimate; not an official or bookmaker price'})
for r in rows:
    if r['sport']!='Ice Hockey':continue
    g=nhl_games.get(r['id'])
    if not g:continue
    a=teamstats.get(g['awayTeam']['abbrev']);h=teamstats.get(g['homeTeam']['abbrev'])
    if not a or not h or not a.get('gamesPlayed') or not h.get('gamesPlayed'):continue
    # No guessed injuries, starting goalies, home coefficient or copied market inputs.
    ma=(a['goalFor']/a['gamesPlayed']+h['goalAgainst']/h['gamesPlayed'])/2
    mh=(h['goalFor']/h['gamesPlayed']+a['goalAgainst']/a['gamesPlayed'])/2
    if not (0<ma<15 and 0<mh<15):continue
    pa,ph=pmf(ma),pmf(mh);assert abs(sum(pa)*sum(ph)-1)<1e-9
    away=sum(pa[i]*ph[j] for i in range(60) for j in range(60) if i>j)
    home=sum(pa[i]*ph[j] for i in range(60) for j in range(60) if j>i)
    draw=sum(pa[i]*ph[i] for i in range(60))
    for label,p in [(r['away']+' regulation win',away),(r['home']+' regulation win',home),('Regulation draw',draw)]:price(r,label,p)
    # The handicap and total explicitly settle in regulation; no shootout assumptions.
    home_cover=sum(pa[i]*ph[j] for i in range(60) for j in range(60) if j-i>1.5)
    over=sum(pa[i]*ph[j] for i in range(60) for j in range(60) if i+j>6.5)
    for label,p in [(r['home']+' -1.5 regulation',home_cover),(r['away']+' +1.5 regulation',1-home_cover),('Over 6.5 regulation goals',over),('Under 6.5 regulation goals',1-over)]:price(r,label,p)
    r['own_winner']=r['away'] if away>home else r['home'];r['confidence']='Low'
    r['winner_scope']='Team more likely to lead after regulation; not a moneyline pick'
    r['facts']={'away':{k:a.get(k) for k in ['gamesPlayed','wins','losses','otLosses','goalFor','goalAgainst','l10Wins','l10Losses','l10OtLosses']},'home':{k:h.get(k) for k in ['gamesPlayed','wins','losses','otLosses','goalFor','goalAgainst','l10Wins','l10Losses','l10OtLosses']}}
    r['estimated_goals']={'away':ma,'home':mh}
# Read-only row-by-row audit of the latest peer desk. A URL is not proof of its contents.
peer=load(ROOT/'data/session-b2c7308d/desk.json');review=[]
def normal(s):return re.sub(r'[^a-z0-9]','',__import__('unicodedata').normalize('NFKD',s).encode('ascii','ignore').decode().lower())
for p in peer['rows']:
    matches=[r for r in rows if r['sport']==p['sport'] and r['start_utc']==p.get('start_utc') and {normal(r['away']),normal(r['home'])}=={normal(p.get('side_a','')),normal(p.get('side_b',''))}]
    problems=[]
    if not matches:problems.append('Fixture not reconciled to fresh parsed official capture; values withheld here')
    if p.get('olbg') is None:problems.append('No event-level OLBG association in this peer row')
    if p.get('priced'):problems.append('Prices are calculated estimates, not facts certified by the linked official fixture source')
    if p.get('confidence')=='High':problems.append('High label not adopted: no out-of-sample calibration checked by this desk')
    for key,m in (p.get('markets') or {}).items():
        line=m.get('line')
        if key=='total' and isinstance(line,(int,float)) and float(line).is_integer():problems.append('Integer total requires explicit push treatment; two selection probabilities alone do not document it')
    review.append({'peer_id':p['id'],'sport':p['sport'],'peer_fixture':p.get('matchup',''),'fresh_fixture_id':matches[0]['id'] if matches else None,'fixture_status':'Matched names and UTC start' if matches else 'Unconfirmed','findings':problems,'source':p.get('official_url') or sports.get(p['sport'],''),'peer_file':'data/session-b2c7308d/desk.json'})
for s,u in sports.items():
    n=sum(r['sport']==s for r in rows)
    flag(s,'Coverage and prediction shortfall',f'{n} fresh parsed upcoming fixtures; 0 approved High predictions against a target of 5. Blank values are not evidence of no scheduled matches. No exhaustive OLBG event/market coverage established.',u)
flag('All sports','No event-level OLBG reconciliation','Hub capture does not establish that every official fixture has an OLBG market. No completeness claim; OLBG-event cells intentionally blank.','https://www.olbg.com/betting-tips')
flag('Ice Hockey','Research prices only','Poisson independence and season-average rates are uncalibrated. All confidence labels capped Low. Regulation markets must not be mistaken for match winner including overtime.','https://api-web.nhle.com/v1/standings/now')
flag('All sports','Odds window is not confidence evidence','At -250 the break-even probability is 71.43%; at +10000 it is 0.99%. A 70% probability by itself does not establish value, calibration or a reliable High pick.','https://www.olbg.com/betting-tips')
for record in records:
    if record.get('status')!=200:flag(record.get('sport','Source capture'),'Capture unavailable',record.get('error','No successful response'),record['url'])
rows.sort(key=lambda r:(r['start_utc'],r['id']))
dump(D/'desk.json',{'as_of':at,'scope':list(sports),'completeness':'partial; not a full OLBG match list','rows':rows,'markets':markets,'high_predictions':[]})
dump(D/'review.json',review);dump(D/'flagged.json',flags)
O.mkdir(exist_ok=True)
CSS='''*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#18283e;font:15px/1.6 system-ui,sans-serif}header{background:#122b48;color:white;padding:24px max(4vw,20px)}header b{font-size:22px}nav{display:flex;gap:22px;flex-wrap:wrap;margin-top:14px}a{color:#086777}header a{color:#cce9f3}main{max-width:1420px;margin:auto;padding:32px 4vw}h1{font-size:32px;line-height:1.2}h2{margin-top:32px}.note{padding:18px;background:#fff4d6;border-left:4px solid #d89713;margin:20px 0}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:16px}.card{padding:22px;background:white;border:1px solid #dce3eb;border-radius:10px}.card strong{font-size:32px;display:block}.table{overflow:auto;background:white;border:1px solid #dce3eb;border-radius:8px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:13px 16px;text-align:left;vertical-align:top;border-bottom:1px solid #e2e7ef}th{background:#eaf0f6;white-space:nowrap}td{min-width:110px}tr:hover{background:#f6fafc}input{width:100%;padding:13px;border:1px solid #b3c2d2;border-radius:6px;margin:12px 0}footer{margin-top:40px;color:#59697b}.small{font-size:13px;color:#53657b}.tag{font-size:12px;color:#915b00;text-transform:uppercase;font-weight:700}'''
(O/'style.css').write_text(CSS)
(O/'filter.js').write_text("document.querySelectorAll('input[data-filter]').forEach(i=>i.addEventListener('input',()=>{const t=document.getElementById(i.dataset.filter);t.querySelectorAll('tbody tr').forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(i.value.toLowerCase()))}));")
def table(headers,data,id='rows'):
    return '<label>Filter rows<input data-filter="'+id+'" type="search" placeholder="Search team, sport, status…" aria-label="Filter table"></label><div class="table"><table id="'+id+'"><thead><tr>'+''.join('<th scope="col">'+esc(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(c)+'</td>' for c in r)+'</tr>' for r in data)+'</tbody></table></div>'
def page(file,title,body):
    (O/file).write_text('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+esc(title)+' · OLBG research</title><link rel="stylesheet" href="style.css"><script defer src="filter.js"></script></head><body><header><b>OLBG / Evidence desk</b><nav><a href="index.html">Overview</a><a href="entries.html">Fixtures</a><a href="markets.html">Our lines</a><a href="review.html">Row audit</a><a href="flagged.html">Flagged for Review</a><a href="sources.html">Sources</a><a href="methodology.html">Methodology</a><a href="../index.html">Existing dashboards</a></nav></header><main><span class="tag">Partial coverage · research only</span><h1>'+esc(title)+'</h1><p class="small">Evidence snapshot '+esc(at)+' · UTC dates · no live-update claim</p>'+body+'<footer>18+ · Betting involves risk. No guaranteed outcomes. Missing data stays blank; a source homepage does not certify a fixture or our estimates.</footer></main></body></html>')
def fixture_table(rr):return table(['Sport','Fixture (away @ home)','Start UTC','Venue','Official status','Our regulation winner','Confidence','OLBG event','Evidence'],[[esc(r['sport']),esc(r['away']+' @ '+r['home']),esc(r['start_utc']),esc(r['venue']),esc(r['state'])+(' · if necessary' if r.get('conditional') else ''),esc(r['own_winner']),esc(r['confidence']),'',link(r['source'])] for r in rr])
page('entries.html','Upcoming fixtures', '<div class="note">Only freshly parsed official fixture facts are shown. Blank OLBG associations mean listing membership is unconfirmed. Date is UTC, not venue-local. Conditional games may not take place.</div>'+fixture_table(rows))
coverage=[]
for s,u in sports.items():
    slug=s.lower().replace(' ','-')+'.html';sr=[r for r in rows if r['sport']==s]
    coverage.append([link(slug,s),str(len(sr)),'0 / 5','Needs review',link(u)])
    page(slug,s,'<div class="note">0 approved High predictions; target 5. '+('No upcoming fixtures parsed by this desk. This does not mean there are no fixtures.' if not sr else 'Facts from the linked official feed; estimates remain Low confidence.')+'</div>'+fixture_table(sr))
page('index.html','Today & upcoming: evidence before confidence','<div class="note"><b>No approved High-confidence picks.</b> The five-per-sport target is unmet for all 15 sports. Previous desks contain estimates and predictions, but this desk does not promote them without checking calibration and current evidence. This is not a complete OLBG inventory.</div><div class="cards">'+''.join('<div class="card"><strong>'+str(v)+'</strong>'+label+'</div>' for v,label in [(len(rows),'Upcoming official fixtures'),(len(markets),'Own research selections'),(len(review),'Peer rows audited'),(len(flags),'Review flags')])+'</div><h2>Executive summary</h2><p>No High pick is recommended for today or upcoming fixtures. Research estimates are available only where current inputs were parsed. Fixtures dated after midnight UTC may belong to today in the venue timezone.</p><h2>15-sport coverage</h2>'+table(['Sport','Fresh fixtures','High predictions / target','Coverage','Official review link'],coverage))
page('markets.html','Our research lines','<div class="note">These are our estimates, not official statistics, bookmaker quotes or calibrated probabilities. All are Low confidence. Win markets settle in regulation (three-way), not including overtime. Handicap ±1.5 and total 6.5 have no push outcome. Other markets, match moneyline, injuries and goalie effects are unpriced pending adequate evidence.</div>'+table(['Fixture','Selection','Estimated probability','Fair American','Fair decimal','Confidence','Fixture evidence','Input evidence'],[[esc(m['match']),esc(m['selection']),f"{m['probability']:.2%}",str(m['fair_american']),str(m['fair_decimal']),m['confidence'],link(m['source']),link(m['inputs_source'])] for m in markets]))
page('review.html','Row-by-row peer audit','<p>Every one of the '+str(len(review))+' rows in the named peer dataset was inspected structurally and compared with the freshly parsed fixtures. This is not a certification of every repository line or factual validation of the peer estimates. Names and UTC start matching do not validate form, injuries, market availability or prices.</p>'+table(['Peer row','Sport','Fixture','Fresh fixture match','Findings','Official manual review'],[[esc(r['peer_id']),esc(r['sport']),esc(r['peer_fixture']),esc(r['fixture_status']),'<br>'.join(esc(f) for f in r['findings']),link(r['source'])] for r in review]))
page('flagged.html','Flagged for Review',table(['Sport','Issue','Finding / resolution needed','Source for manual review'],[[esc(f['sport']),esc(f['title']),esc(f['detail']),link(f['source'])] for f in flags]))
page('sources.html','Source capture register','<p>HTTP 200 proves retrieval only, not fixture extraction or factual accuracy. Hashes protect captured bytes against accidental changes; they do not authenticate their truth. Failed captures are retained as failures.</p>'+table(['Target','Captured UTC','HTTP','Bytes','SHA-256 / error','Public source'],[[esc(r['id']),esc(r['captured_utc']),str(r['status']),esc(r.get('bytes')),esc(r.get('sha256') or r.get('error')),link(r['url'])] for r in records]))
page('methodology.html','Methodology & limitations','''<h2>Facts and calculations are separate</h2><p>Only structured fresh NHL, MLB, EuroLeague, EuroCup and Liiga fixture feeds are parsed here. WTA timestamps are not assumed to be confirmed scheduled starts. The publication window ends exclusively at 3 November 2026 UTC. A successful homepage capture is never converted into an invented schedule. Upcoming means start UTC after the end of capture and before 3 November 2026 UTC. No OLBG event match has been established, so that column remains blank.</p><h2>Our transparent research prices</h2><p>For NHL only, away expected goals = (away season goals-for per game + home season goals-against per game) / 2; the home calculation is symmetric. Independent Poisson scoring on 0–59 goals yields regulation win/draw, regulation ±1.5 handicap and regulation 6.5 total probabilities. Truncated mass must differ from one by less than 10⁻⁹. Season scoring is a proxy for regulation scoring, so overtime/shootout contamination is a limitation. No arbitrary home advantage or injury adjustment is added.</p><p>Fair decimal = 1/p. Fair American = −100p/(1−p) for p ≥ 0.5, otherwise 100(1−p)/p, rounded to the nearest integer. There is no bookmaker margin and no value/edge claim without a contemporaneous market quote. A regulation winner is the team with the larger regulation-win estimate; the draw remains a separately priced outcome.</p><h2>Confidence gate</h2><p>All computed picks are Low. Neither an estimate above 70% nor an odds band proves predictive reliability. Medium and High require evidence quality and out-of-sample calibration not established in this session. High narratives are withheld rather than padded to five. Injuries, individual game history and unavailable form are left blank; last-ten aggregate fields, where present, are stored as source facts in the downloadable JSON, not invented match reports.</p><h2>Reproducibility</h2><p>Run <code>python scripts/session-7cfa69e5/build.py</code> then <code>python scripts/session-7cfa69e5/test.py</code>. Raw gzip captures, timestamps and hashes are in <a href="../data/session-7cfa69e5/capture/manifest.json">the manifest</a>. <a href="../data/session-7cfa69e5/desk.json">Download facts and estimates</a>. Automated GitHub capture is available via workflow_dispatch; it does not automatically publish refreshed picks or claim continuous coverage.</p>''')
print(f'{len(rows)} fresh fixtures, {len(markets)} research selections, {len(review)} peer rows audited, {len(flags)} flags')

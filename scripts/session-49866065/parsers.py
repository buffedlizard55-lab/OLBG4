"""Official JSON adapters. Every displayed factual field retains a JSON pointer.
No seeding-to-win-probability conversion; no OLBG timestamps used as official facts.
"""
from collections import defaultdict
from datetime import timedelta
from core import instant, norm, log5, price, in_window


def parse_official(e):
    rows=[]; errors=[]; seen={}
    horizon=e.cutoff+timedelta(days=16)
    def emit(sport,league,tid,path,id,away,home,start,status,fields,aliases=None,conditional=False):
        when=instant(start)
        if not when or not e.cutoff < when < horizon: return None
        facts=[]
        for label,p in fields:
            f=e.fact(tid,path+p,label)
            if f: facts.append(f)
        r=dict(id=id,sport=sport,competition=league,away=away,home=home,start_utc=when.isoformat().replace('+00:00','Z'),
               status=status,conditional=conditional,facts=facts,official_url=e.records[tid]['url'],
               aliases=aliases or [[away],[home]],markets=[],pick=None,confidence='',olbg_ids=[],flags=[],
               prediction='',injuries=None)
        if id in seen:
            old=seen[id]
            if any(r[k]!=old[k] for k in ('away','home','start_utc')):
                old['flags'].append('Contradictory fixture identity/time across official responses; prices withheld.')
            return None
        seen[id]=r;rows.append(r);return r
    def winner(r,wa,ga,wb,gb,tid,ap,bp,wn='wins',gn='gamesPlayed'):
        if not r or r['conditional']: return
        try: p=log5(wa,ga,wb,gb)
        except (ValueError,TypeError) as ex:
            r['flags'].append('Invalid or unavailable record: '+str(ex));return
        for side,prefix in [('Away',ap),('Home',bp)]:
            for label,key in [('wins',wn),('games played',gn)]:
                f=e.fact(tid,prefix+'/'+key,f'{side} season {label}')
                if f: r['facts'].append(f)
        sels=[dict(selection=r['away'],**price(p)),dict(selection=r['home'],**price(1-p))]
        r['markets'].append(dict(name='Match winner including overtime / extra innings',scope='Independent estimate; rule compatibility with OLBG unconfirmed',selections=sels))
        best=max(sels,key=lambda s:s['probability'])
        r['pick']=dict(best,in_requested_window=in_window(best['probability']))
        # No empirical calibration or injury/line-up coverage exists. Numerical p alone
        # must not produce an evidence confidence upgrade.
        r['confidence']='low'
        r['flags'].append('Low research confidence: fair-price method is not backtested; no current line-up/injury assessment. A large calculated probability is not High confidence.')
    # NHL regular season fixtures and standings use official stable team abbreviations.
    st=e.json('nhl_standings_now') or {}
    standings={s['teamAbbrev']['default']:(i,s) for i,s in enumerate(st.get('standings',[])) if s.get('seasonId')==20262027}
    for tid in sorted(e.records):
        if not tid.startswith('nhl_sched_'):continue
        obj=e.json(tid) or {}
        for di,day in enumerate(obj.get('gameWeek',[])):
            for gi,g in enumerate(day.get('games',[])):
                if g.get('season')!=20262027 or g.get('gameType')!=2:continue
                if g.get('gameState') not in ('FUT','PRE') or g.get('gameScheduleState')!='OK': continue
                a,b=g.get('awayTeam',{}),g.get('homeTeam',{})
                def name(t): return (t.get('placeName',{}).get('default','')+' '+t.get('commonName',{}).get('default','')).strip()
                fields=[('Away place','/awayTeam/placeName/default'),('Away name','/awayTeam/commonName/default'),
                        ('Home place','/homeTeam/placeName/default'),('Home name','/homeTeam/commonName/default'),
                        ('Start UTC','/startTimeUTC'),('Game state','/gameState'),('Season','/season'),('Game type','/gameType')]
                if 'venue' in g:fields.append(('Venue','/venue/default'))
                aliases=[[name(t),t.get('commonName',{}).get('default',''),t.get('abbrev','')+' '+t.get('commonName',{}).get('default','')] for t in (a,b)]
                r=emit('Ice Hockey','NHL',tid,f'/gameWeek/{di}/games/{gi}','nhl-'+str(g['id']),name(a),name(b),g.get('startTimeUTC'),g.get('gameState'),fields,aliases)
                if not r:continue
                aa,bb=standings.get(a.get('abbrev')),standings.get(b.get('abbrev'))
                if not aa or not bb:r['flags'].append('Official standings team/season missing.');continue
                ia,sa=aa;ib,sb=bb
                valid=all(s.get('wins',-1)+s.get('losses',-1)+s.get('otLosses',-1)==s.get('gamesPlayed') for s in (sa,sb))
                if not valid:r['flags'].append('NHL wins/losses/OT losses do not reconcile to games played.');continue
                for s in (sa,sb):
                    if str(s.get('date',''))>e.cutoff.date().isoformat(): valid=False
                if not valid:r['flags'].append('Standings dated after capture.');continue
                winner(r,sa['wins'],sa['gamesPlayed'],sb['wins'],sb['gamesPlayed'],'nhl_standings_now',f'/standings/{ia}',f'/standings/{ib}')
                for side,si,s in [('Away',ia,sa),('Home',ib,sb)]:
                    for key in ['losses','otLosses','goalFor','goalAgainst','l10Wins','l10Losses','l10OtLosses','l10GamesPlayed','date']:
                        if key in s:r['facts'].append(e.fact('nhl_standings_now',f'/standings/{si}/{key}',f'{side} {key}'))
                r['flags'].append('Regulation totals, 1X2 and handicap withheld: captured season goal aggregates include overtime/shootout scoring and do not establish settlement-aligned regulation distributions.')
    # MLB: conditional games retained as schedule facts but not actionable prices.
    ms=e.json('mlb_standings_2026') or {}
    records={}
    for di,d in enumerate(ms.get('records',[])):
        for ti,s in enumerate(d.get('teamRecords',[])):
            if s.get('season')=='2026':records[s['team']['id']]=(f'/records/{di}/teamRecords/{ti}',s)
    schedule=e.json('mlb_ws_schedule') or {}
    for di,d in enumerate(schedule.get('dates',[])):
        for gi,g in enumerate(d.get('games',[])):
            if g.get('status',{}).get('abstractGameState')!='Preview' or g.get('status',{}).get('startTimeTBD'):continue
            a,b=g['teams']['away']['team'],g['teams']['home']['team']
            aa,bb=records.get(a['id']),records.get(b['id'])
            aliases=[[a['name']],[b['name']]]
            if aa:aliases[0].append(aa[1]['team']['name'])
            if bb:aliases[1].append(bb[1]['team']['name'])
            fields=[('Away team','/teams/away/team/name'),('Home team','/teams/home/team/name'),('Start UTC','/gameDate'),('Status','/status/detailedState')]
            if 'venue' in g:fields.append(('Venue','/venue/name'))
            if 'ifNecessary' in g:fields.append(('If necessary','/ifNecessary'))
            r=emit('Baseball',g.get('seriesDescription','MLB'), 'mlb_ws_schedule',f'/dates/{di}/games/{gi}','mlb-'+str(g['gamePk']),a['name'],b['name'],g['gameDate'],g['status']['detailedState'],fields,aliases,g.get('ifNecessary')=='Y')
            if r and aa and bb:
                pa,sa=aa;pb,sb=bb
                if all(s.get('wins',-1)+s.get('losses',-1)==s.get('gamesPlayed') for s in (sa,sb)):
                    winner(r,sa['wins'],sa['gamesPlayed'],sb['wins'],sb['gamesPlayed'],'mlb_standings_2026',pa,pb)
                    for side,p,s in [('Away',pa,sa),('Home',pb,sb)]:
                        for key in ['runsScored','runsAllowed','losses','lastUpdated']:
                            if key in s:r['facts'].append(e.fact('mlb_standings_2026',p+'/'+key,f'{side} {key}'))
                else:r['flags'].append('MLB standings record fails arithmetic reconciliation.')
            if r:r['flags'].append('Pitcher/line-up adjusted run-line, total, innings and player markets withheld: no adequate inputs/settlement fit.')
    # EuroLeague and EuroCup: fixtures directly from official feeds. Do not turn
    # rankings into confidence; completed same-season games supply win records.
    for tid,league in [('euroleague_games_E2026','EuroLeague'),('eurocup_games_U2026','EuroCup')]:
        games=(e.json(tid) or {}).get('data',[])
        record=defaultdict(lambda:[0,0,[]])
        for i,g in enumerate(games):
            when=instant(g.get('utcDate'))
            if g.get('played') is True and when and when<e.cutoff:
                a,b=g.get('road',{}),g.get('local',{})
                if not isinstance(a.get('score'),int) or not isinstance(b.get('score'),int) or a['score']==b['score']:continue
                for side,opp in [(a,b),(b,a)]:
                    code=side.get('club',{}).get('code')
                    if not code:continue
                    record[code][0]+=int(side['score']>opp['score']);record[code][1]+=1;record[code][2].append(i)
        for i,g in enumerate(games):
            if g.get('played') is not False or g.get('confirmedDate') is not True or g.get('confirmedHour') is not True:continue
            a,b=g.get('road',{}).get('club',{}),g.get('local',{}).get('club',{})
            if a.get('isVirtual') or b.get('isVirtual') or not a.get('name') or not b.get('name'):continue
            aliases=[[a['name'],a.get('abbreviatedName',''),a.get('editorialName','')],[b['name'],b.get('abbreviatedName',''),b.get('editorialName','')]]
            r=emit('Basketball',league,tid,f'/data/{i}',tid+'-'+str(g.get('gameCode')),a['name'],b['name'],g.get('utcDate'),g.get('gameStatus',''),[('Away team','/road/club/name'),('Home team','/local/club/name'),('Start UTC','/utcDate'),('Played','/played')],aliases)
            if not r:continue
            ra,rb=record[a['code']],record[b['code']]
            if min(ra[1],rb[1])>=1:
                p=log5(ra[0],ra[1],rb[0],rb[1]);sels=[dict(selection=r['away'],**price(p)),dict(selection=r['home'],**price(1-p))]
                r['markets']=[dict(name='Match winner including overtime',scope='Log5 from captured completed same-season games; uncalibrated',selections=sels)]
                r['pick']=dict(max(sels,key=lambda s:s['probability']));r['pick']['in_requested_window']=in_window(r['pick']['probability']);r['confidence']='low'
                for label,rec in [('Away',ra),('Home',rb)]:
                    for gi in rec[2]:
                        for key in ['road/club/name','local/club/name','road/score','local/score','utcDate','played']:
                            r['facts'].append(e.fact(tid,f'/data/{gi}/{key}',label+' record input: '+key))
                r['record_inputs']={'away_wins':ra[0],'away_games':ra[1],'home_wins':rb[0],'home_games':rb[1]}
            r['flags'].append('No empirical calibration, line-up/injury coverage or scoring-variance fit. Confidence low; handicap, totals and player props withheld.')
    # WTA exact named pairings, including explicitly unscheduled entries (time blank).
    for tid in sorted(e.records):
        if not tid.startswith('wta_'):continue
        matches=(e.json(tid) or {}).get('matches',[])
        for i,m in enumerate(matches):
            if m.get('MatchState')!='U' or m.get('DrawMatchType')!='S' or m.get('Unscheduled'):continue
            if m.get('isEstimatedStartTime'):continue
            a=' '.join(str(m.get(k,'')).strip() for k in ('PlayerNameFirstA','PlayerNameLastA')).strip()
            b=' '.join(str(m.get(k,'')).strip() for k in ('PlayerNameFirstB','PlayerNameLastB')).strip()
            if not a or not b or any(x in norm(a+b) for x in ('qualifier','winner','tbd')):continue
            r=emit('Tennis','WTA event '+str(m.get('EventID')),tid,f'/matches/{i}',tid+'-'+str(m.get('MatchID')),a,b,m.get('MatchTimeStamp'),'Upcoming',[(k,'/'+k) for k in ('PlayerNameFirstA','PlayerNameLastA','PlayerNameFirstB','PlayerNameLastB','MatchTimeStamp','MatchState')])
            if r:r['flags'].append('Court times may be not-before bounds, not exact first serve. Ranking/seeding alone is insufficient for a form-based match, set, game-total or handicap price.')
    # Liiga: confirmed official game fixture identity; do not use future-result fields.
    games=e.json('liiga_games_2027') or []
    if isinstance(games,list):
        for i,g in enumerate(games):
            if g.get('started') is not False or g.get('ended') is not False or g.get('season')!=2027:continue
            a,b=g.get('awayTeam',{}),g.get('homeTeam',{})
            if not a.get('teamName') or not b.get('teamName'):continue
            r=emit('Ice Hockey','Liiga','liiga_games_2027',f'/{i}','liiga-'+str(g.get('id')),a['teamName'],b['teamName'],g.get('start'),'Scheduled',[(k,'/'+k) for k in ['awayTeam/teamName','homeTeam/teamName','start']])
            if r:r['flags'].append('Official fixture only. No independently validated current team-strength and regulation-scoring adapter; all lines withheld.')
    # NBA official schedule can be inaccessible; this adapter requires actual JSON,
    # timezone-aware timestamps and explicit scheduled status, never an HTML shell.
    for tid in ('nba_cdn_schedule_v2','nba_cdn_schedule_v2_1'):
        obj=e.json(tid) or {}
        for di,d in enumerate(obj.get('leagueSchedule',{}).get('gameDates',[])):
            for gi,g in enumerate(d.get('games',[])):
                if g.get('gameStatus')!=1:continue
                a,b=g.get('awayTeam',{}),g.get('homeTeam',{})
                def name(t):return (str(t.get('teamCity',''))+' '+str(t.get('teamName',''))).strip()
                path=f'/leagueSchedule/gameDates/{di}/games/{gi}'
                r=emit('Basketball','NBA',tid,path,'nba-'+str(g.get('gameId')),name(a),name(b),g.get('gameDateTimeUTC'),'Scheduled',[(k,'/'+k) for k in ['awayTeam/teamCity','awayTeam/teamName','homeTeam/teamCity','homeTeam/teamName','gameDateTimeUTC','gameStatus']],[[name(a),str(a.get('teamTricode',''))+' '+str(a.get('teamName',''))],[name(b),str(b.get('teamTricode',''))+' '+str(b.get('teamName',''))]])
                if r:r['flags'].append('Official NBA fixture only; contemporaneous official season-strength inputs absent. All lines withheld.')
    # Cricket Australia exposes a JSON.parse string with public fixture data.
    # Evidence.json safely decodes that string, not JavaScript execution.
    for i,g in enumerate(e.json('cricket_au_fixtures') or []):
        if g.get('isLive') or g.get('isCompleted') or g.get('isInProgress'):continue
        a,b=g.get('awayTeam',{}),g.get('homeTeam',{})
        if not a.get('name') or not b.get('name'):continue
        r=emit('Cricket',g.get('competition',{}).get('name',''),'cricket_au_fixtures',f'/{i}','ca-'+str(g.get('id')),a['name'],b['name'],g.get('startDateTime'),'Upcoming',[(k,'/'+k) for k in ['awayTeam/name','homeTeam/name','startDateTime','isCompleted','competition/name']])
        if r:
            r['flags'].append('Official pairing/time only. Match format, team selection, weather and innings distributions need supported inputs; winner, handicap, totals and player markets remain unpriced.')
    # URC article explicitly publishes IRE & UK kickoff times. Convert with the
    # standard Europe/London tz database, retaining the exact date/KO/season text.
    import re,html
    from datetime import datetime,timezone
    from zoneinfo import ZoneInfo
    tid='urc_fixtures_in_full';raw=e.text(tid)
    season=re.search(r'<h1[^>]*>\s*(2026/27) Fixtures in Full',raw)
    dates=list(re.finditer(r'(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s*(OCTOBER|NOVEMBER)\s+(\d{1,2})',raw))
    fixtures=list(re.finditer(r'<b>\s*<span[^>]*>([^<]{3,90}\sv\s[^<]{3,90})</span>\s*</b>',raw))
    if season:
        for mi,m in enumerate(fixtures):
            before=[d for d in dates if d.start()<m.start()]
            if not before:continue
            d=before[-1]
            # Only accept a nearby explicit day header; do not carry October dates
            # over later December/2027 rounds where another month heading intervenes.
            intervening=re.search(r'(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY),\s*([A-Z]+)\s+\d{1,2}',raw[d.end():m.start()])
            if intervening:continue
            text=html.unescape(m.group(1)).replace('\xa0',' ')
            parts=text.split(' v ')
            if len(parts)!=2:continue
            # Venue line must be the next italic paragraph, before next fixture.
            tail=raw[m.end():m.end()+700]
            v=re.search(r'<i>\s*<span[^>]*>([^<]+)</span>\s*</i>',tail)
            if not v:continue
            venue=html.unescape(v.group(1))
            ko=re.search(r'KO (\d{1,2})[.:](\d{2}) IRE & UK',venue)
            if not ko:continue
            local=datetime(2026,10 if d.group(1)=='OCTOBER' else 11,int(d.group(2)),int(ko.group(1)),int(ko.group(2)),tzinfo=ZoneInfo('Europe/London'))
            utc=local.astimezone(timezone.utc)
            if not e.cutoff<utc<horizon:continue
            facts=[e.excerpt_fact(tid,m.start(1),m.end(1),'Published pairing'),e.excerpt_fact(tid,d.start(),d.end(),'Published day'),e.excerpt_fact(tid,m.end()+v.start(1),m.end()+v.end(1),'Published venue and regional KO'),e.excerpt_fact(tid,season.start(1),season.end(1),'Published season')]
            id='urc-article-'+str(mi)
            r=dict(id=id,sport='Rugby Union',competition='United Rugby Championship',away=parts[0].strip(),home=parts[1].strip(),
                start_utc=utc.isoformat().replace('+00:00','Z'),status='Published schedule',conditional=False,facts=facts,
                official_url=e.records[tid]['url'],aliases=[[parts[0].strip()],[parts[1].strip()]],markets=[],pick=None,confidence='',olbg_ids=[],
                flags=['Published schedule article, not a live match-status feed. UTC is normalized from explicit IRE & UK kickoff via Europe/London; source text retained. Official current form/ratings absent: all prices withheld.'],prediction='',injuries=None,
                start_transformation=dict(local_iso=local.isoformat(),timezone='Europe/London',source_season='2026/27'))
            rows.append(r)
    for r in rows:
        if r['conditional']:r['flags'].append('If-necessary game: not guaranteed to take place; all prices withheld.')
        if len(r['facts'])<3:raise ValueError('Fixture lacks source facts')
        if any('Contradictory' in f for f in r['flags']):r['markets']=[];r['pick']=None;r['confidence']=''
    return sorted(rows,key=lambda r:(r['start_utc'],r['sport'],r['id'])),errors


def reconcile(listings,rows):
    """Require exact UTC timestamp plus two unambiguous officially sourced aliases.
    Suffix matching accepts city abbreviations only when an entire official nickname
    is preserved. Candidate ambiguity rejects the match; no date-only fallback.
    """
    for event in listings:
        if not event['active']:continue
        import re
        parts=re.split(r'\s+(?:@|vs\.?|v)\s+',event['listed_name'],maxsplit=1,flags=re.I)
        if len(parts)!=2:continue
        candidates=[]
        for r in rows:
            if r['sport']!=event['sport'] or instant(r['start_utc'])!=instant(event['listed_start']):continue
            def matches(part,aliases):
                return any(norm(a) and (norm(part)==norm(a) or (len(norm(a))>=4 and norm(part).endswith(norm(a)))) for a in aliases)
            a,b=r['aliases']
            if ((matches(parts[0],a) and matches(parts[1],b)) or
                (matches(parts[1],a) and matches(parts[0],b))):candidates.append(r)
        if len(candidates)==1:
            r=candidates[0];event['official_id']=r['id'];r['olbg_ids'].append(event['id'])
        elif candidates:event['reconciliation_flag']='Ambiguous official candidate; no match adopted.'

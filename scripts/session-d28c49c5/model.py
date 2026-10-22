"""Exploratory NHL baseline, NOT calibrated predictions or official betting lines.

Team GF/GA totals include overtime/shootout scoring. Treating those rates as a
regulation scoring proxy is a documented limitation. Never release High labels.
"""
import math

def american(p):
 if not 0<p<1: raise ValueError('Probability outside (0,1)')
 return round(-100*p/(1-p) if p>=.5 else 100*(1-p)/p)

def poisson(rate,limit=45):
 if not 0<rate<15: raise ValueError('Unsupported scoring rate')
 values=[math.exp(-rate)]
 for n in range(1,limit): values.append(values[-1]*rate/n)
 return values

def originate(fixtures,standings):
 teams={r['teamName']['default']:r for r in standings.get('standings',[])}
 if not teams: return []
 games=sum(t['gamesPlayed'] for t in teams.values())
 league=sum(t['goalFor'] for t in teams.values())/games
 result=[]
 for f in fixtures:
  if f['sport']!='Ice Hockey' or f['state']!='FUT': continue
  a=teams.get(f['side_a']); b=teams.get(f['side_b'])
  if not a or not b or min(a['gamesPlayed'],b['gamesPlayed'])<=0: continue
  # 20-game league-average shrinkage prior is a modeling choice, not source data.
  def rate(team,key): return (team[key]+20*league)/(team['gamesPlayed']+20)
  la=rate(a,'goalFor')*rate(b,'goalAgainst')/league
  lb=rate(b,'goalFor')*rate(a,'goalAgainst')/league
  pa,pb=poisson(la),poisson(lb)
  mass=sum(pa)*sum(pb)
  aw=tie=under=cover=0.
  for x,px in enumerate(pa):
   for y,py in enumerate(pb):
    p=px*py/mass
    aw+=p*(x>y); tie+=p*(x==y); under+=p*(x+y<6.5); cover+=p*(x-y>1.5)
  win=aw+tie/2
  markets=[('Match winner incl. OT / shootout (50% tie allocation)',f['side_a'],win,f['side_b'],1-win),('Regulation goals total 6.5 (proxy)','Under 6.5',under,'Over 6.5',1-under),('Regulation goal handicap (proxy)',f['side_a']+' -1.5',cover,f['side_b']+' +1.5',1-cover)]
  for name,sa,p,sb,q in markets:
   result.append(dict(fixture_id=f['id'],matchup=f['side_a']+' at '+f['side_b'],start_utc=f['start_utc'],market=name,selection_a=sa,p_a=p,fair_decimal_a=1/p,fair_american_a=american(p),selection_b=sb,p_b=q,fair_decimal_b=1/q,fair_american_b=american(q),winner_pick=(sa if p>=q else sb),confidence='Low',status='Exploratory / uncalibrated; not a betting recommendation',official_url='https://api-web.nhle.com/v1/standings/2026-10-22',fixture_source=f['official_url'],input_a={k:a[k] for k in ['teamName','gamesPlayed','goalFor','goalAgainst']},input_b={k:b[k] for k in ['teamName','gamesPlayed','goalFor','goalAgainst']},expected_goals_a=la,expected_goals_b=lb))
 # Stable publication precision across Python minor versions/libm implementations.
 def stable(value):
  if isinstance(value,float): return round(value,10)
  if isinstance(value,dict): return {k:stable(v) for k,v in value.items()}
  if isinstance(value,list): return [stable(v) for v in value]
  return value
 return stable(result)

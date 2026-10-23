"""Read-only row-by-row audit. Does not inherit peer 'verified' labels.
Run separately when choosing a new review baseline; build.py consumes its pinned output.
"""
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.parse import urlsplit
from core import ROOT, DATA, SPORTS, instant

DOMAINS=('nhl.com','nhle.com','nba.com','mlb.com','euroleague.net','wtatennis.com','atptour.com',
 'unitedrugby.com','nrl.com','internationalrugbyleague.com','rlwc2026.com','pdc.tv','wst.tv',
 'gaa.ie','gaacork.ie','gbgb.org.uk','cricket.com.au','icc-cricket.com','bcci.tv','ecb.co.uk',
 'nzc.nz','pcb.com.pk','legavolley.it','volleyballworld.com','eurohandball.com','liiga.fi',
 'formula1.com','motogp.com','pgatour.com','europeantour.com','lpga.com','swehockey.se')

def urls(value):
    if isinstance(value,str):return [value] if value.startswith('https://') else []
    if isinstance(value,dict):return [u for v in value.values() for u in urls(v)]
    if isinstance(value,list):return [u for v in value for u in urls(v)]
    return []

def official(url):
    p=urlsplit(url);host=p.hostname or ''
    return p.scheme=='https' and not p.username and not p.password and any(host==d or host.endswith('.'+d) for d in DOMAINS)

def main():
    paths=['data/master.json','data/matches.json','data/session-0ed96fe7/desk.json',
           'data/session-2722b692/desk.json','data/session-543dca7d/desk.json']
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out={'baseline_commit':commit,'scope':'Structural row audit only. No peer facts or confidence labels adopted as independently confirmed.', 'files':[],'rows':[]}
    cutoff=json.loads((DATA/'capture/manifest.json').read_text())['finished_at']
    when=instant(cutoff)
    for name in paths:
        p=ROOT/name
        if not p.exists():continue
        raw=p.read_bytes();data=json.loads(raw)
        key=''
        if isinstance(data,list):rows=data
        else:
            key=next((k for k in ['rows','matches','fixtures'] if isinstance(data.get(k),list)),None)
            if not key:continue
            rows=data[key]
        out['files'].append(dict(path=name,sha256=hashlib.sha256(raw).hexdigest(),rows=len(rows)))
        for i,r in enumerate(rows):
            candidates=sorted(set(u for u in urls(r) if official(u)))
            issues=['FACTUAL_RECHECK_NOT_PERFORMED: source link presence is not independent confirmation.']
            if not candidates:issues.append('NO_OFFICIAL_SOURCE_URL: official factual fields remain blank in this audit.')
            sport=r.get('sport','')
            if sport and sport not in SPORTS:issues.append('SCOPE_MISMATCH: not one of the 15 requested category labels; needs explicit mapping or exclusion.')
            start=r.get('start_utc') or r.get('date') or ''
            ts=instant(start)
            if ts and ts<=when:issues.append('PAST_AT_CUTOFF: cannot present this row as an upcoming match without refreshing status.')
            elif start and len(start)==10 and start<cutoff[:10]:issues.append('PAST_DATE_AT_CUTOFF: historical date, not upcoming.')
            elif not ts:issues.append('TIME_NOT_CONFIRMED: no timezone-aware official start adopted.')
            conf=r.get('confidence') or r.get('confidence_label') or ''
            if isinstance(conf,dict):conf=str(conf)
            if 'high' in str(conf).lower():issues.append('HIGH_NOT_REPRODUCED: no independently reproduced out-of-sample calibration in this audit.')
            prediction=r.get('prediction') or r.get('prediction_text') or ''
            if isinstance(prediction,str) and prediction and len(prediction.split())<30:issues.append('SHORT_PREDICTION: fewer than 30 whitespace-delimited words.')
            if r.get('build_verified') is False:issues.append('BUILD_MARKED_UNVERIFIED: historical row declares build_verified=false.')
            out['rows'].append(dict(file=name,pointer=f'/{key}/{i}' if key else f'/{i}',id=str(r.get('id',i)),
                official_source_candidates=candidates,issues=issues,confirmed_values={},status='unverified',
                blob_url=f'https://github.com/buffedlizard55-lab/OLBG4/blob/{commit}/{name}'))
    (DATA/'review.json').write_text(json.dumps(out,indent=2)+'\n')
    print('Pinned review:',len(out['rows']),'rows in',len(out['files']),'files')

if __name__=='__main__':main()

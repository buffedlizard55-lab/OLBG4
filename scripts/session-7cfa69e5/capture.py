"""Public-source capture. No credentials, internal APIs, or access-control bypasses."""
import concurrent.futures, gzip, hashlib, json, pathlib, urllib.request, urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urlsplit
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'data/session-7cfa69e5/capture'
UA='OLBG4Research/1.0 (+https://github.com/buffedlizard55-lab/OLBG4)'
def get(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=25) as r:
        data=r.read(12000000)
        if len(data)==12000000: raise ValueError('size limit')
        return data,r.status,r.geturl(),r.headers.get('Content-Type','')
def host_group(items):
    results=[]
    origin='{0.scheme}://{0.netloc}'.format(urlsplit(items[0]['url']))
    rp=urllib.robotparser.RobotFileParser()
    try:
        raw,_,_,_=get(origin+'/robots.txt');rp.parse(raw.decode(errors='replace').splitlines())
        robot_file='robots_'+urlsplit(origin).netloc.replace('.','_')+'.gz'
        (OUT/robot_file).write_bytes(gzip.compress(raw,mtime=0))
        robots='read'
        robots_sha=hashlib.sha256(raw).hexdigest()
    except Exception as e:
        # RFC 9309 permits access on a 4xx except 429. Fail closed on other failures.
        if getattr(e,'code',0) in (404,410): rp.parse([]);robots='absent'
        else: rp=None;robots=str(e)
    for t in items:
        r=dict(t,captured_utc=datetime.now(timezone.utc).isoformat(),robots=robots)
        if robots=='read':r.update(robots_file=robot_file,robots_sha256=robots_sha,robots_url=origin+'/robots.txt')
        try:
            if rp is None: raise ValueError('robots unavailable; capture withheld')
            if not rp.can_fetch(UA,t['url']): raise ValueError('robots disallow')
            import time
            time.sleep(max(1,float(rp.crawl_delay(UA) or 0)))
            raw,status,final,ctype=get(t['url'])
            fn=t['id']+'.gz';(OUT/fn).write_bytes(gzip.compress(raw,mtime=0))
            r.update(status=status,final_url=final,content_type=ctype,file=fn,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
        except Exception as e: r.update(status=0,error=str(e))
        results.append(r)
    return results
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    groups={}
    for t in json.loads((ROOT/'scripts/session-7cfa69e5/targets.json').read_text()):groups.setdefault(urlsplit(t['url']).netloc,[]).append(t)
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool: rows=[r for group in pool.map(host_group,groups.values()) for r in group]
    (OUT/'manifest.json').write_text(json.dumps({'captured_utc':datetime.now(timezone.utc).isoformat(),'records':rows},indent=2))
    print('Captured',sum(r['status']==200 for r in rows),'of',len(rows))

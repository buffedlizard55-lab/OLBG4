"""Read-only public captures. No credentials, private API, or access-control bypass."""
import concurrent.futures as futures
import gzip
import hashlib
import json
import threading
import time
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parents[2]
DATA = BASE / 'data/session-49866065'
AGENT = 'OLBG4EvidenceAudit/1.0 (+https://github.com/buffedlizard55-lab/OLBG4)'
LOCKS = {}
LOCK = threading.Lock()

def request(url):
    req = urllib.request.Request(url, headers={'User-Agent': AGENT, 'Accept': '*/*'})
    with urllib.request.urlopen(req, timeout=25) as r:
        body = r.read(16000000)
        if r.headers.get('Content-Encoding') == 'gzip': body = gzip.decompress(body)
        return r.status, r.geturl(), r.headers.get('Content-Type', ''), body

def main():
    out = DATA / 'capture'
    out.mkdir(parents=True, exist_ok=True)
    targets = json.loads((BASE / 'scripts/session-49866065/targets.json').read_text())
    stamp = datetime.now(timezone.utc).isoformat()
    robots = urllib.robotparser.RobotFileParser()
    robot_ok = False
    records = []
    try:
        status, final, ct, body = request('https://www.olbg.com/robots.txt')
        robots.parse(body.decode('utf-8').splitlines())
        robot_ok = status == 200
        fn = 'olbg_robots.gz'
        (out/fn).write_bytes(gzip.compress(body, mtime=0))
        records.append(dict(id='olbg_robots',url='https://www.olbg.com/robots.txt',status=status,
            final_url=final,content_type=ct,file=fn,bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),captured_at=stamp,error=''))
    except Exception as e:
        records.append(dict(id='olbg_robots',url='https://www.olbg.com/robots.txt',status=0,error=str(e),captured_at=stamp))
    def fetch(t):
        rec = dict(t, captured_at=datetime.now(timezone.utc).isoformat())
        host = urlsplit(t['url']).hostname
        if host == 'olbg.com' or host.endswith('.olbg.com'):
            if not robot_ok or not robots.can_fetch(AGENT, t['url']):
                return dict(rec,status=0,error='robots unavailable or path disallowed; not requested')
        with LOCK:
            lock = LOCKS.setdefault(host, threading.Lock())
        try:
            with lock:
                time.sleep(0.6)
                status, final, ct, body = request(t['url'])
            fn = t['id']+'.gz'
            (out/fn).write_bytes(gzip.compress(body, mtime=0))
            rec.update(status=status,final_url=final,content_type=ct,file=fn,bytes=len(body),
                       sha256=hashlib.sha256(body).hexdigest(),error='')
        except urllib.error.HTTPError as e:
            rec.update(status=e.code,error=str(e))
        except Exception as e:
            rec.update(status=0,error=f'{type(e).__name__}: {e}')
        print(rec['id'],rec['status'],rec.get('bytes',0),flush=True)
        return rec
    with futures.ThreadPoolExecutor(max_workers=8) as pool:
        records += list(pool.map(fetch,targets))
    manifest = dict(started_at=stamp,finished_at=datetime.now(timezone.utc).isoformat(),
                    records=sorted(records,key=lambda r:r['id']))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__ == '__main__': main()

"""Hard publication invariants; does not equate URL presence with fact verification."""
from pathlib import Path
from urllib.parse import urlparse,unquote
from html.parser import HTMLParser
import gzip,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2]; DATA=ROOT/'data/session-69962336'; SITE=ROOT/'session-69962336'
class Links(HTMLParser):
 def __init__(self):super().__init__();self.links=[]
 def handle_starttag(self,t,a):
  for k,v in a:
   if k in ('href','src'):self.links.append(v)
def main():
 checks=0
 def check(ok,msg):
  nonlocal checks
  checks+=1
  if not ok:raise AssertionError(msg)
 manifest=json.loads((DATA/'raw/manifest.json').read_text())
 for m in manifest['entries']:
  check(urlparse(m['url']).scheme=='https','non-HTTPS source')
  if m.get('file'):
   path=ROOT/m['file']; b=gzip.decompress(path.read_bytes()) if m.get('stored_gzip') else path.read_bytes()
   check(hashlib.sha256(b).hexdigest()==m['sha256'],m['key']+' hash mismatch')
 publication=json.loads((DATA/'publication.json').read_text())
 for r in publication['rows']:
  check(r['start_utc']>publication['capture_utc'],'expired event')
  if not r['strict_identity']:
   check(r['pick'] is None and not r['markets'],'unconfirmed selection leaked')
  else:check(urlparse(r['fixture_url']).hostname in ('www.nhl.com','www.mlb.com'),'nonofficial fixture')
 check(publication['published_predictions']==[],'unreviewed prose leaked')
 for path in SITE.glob('*.html'):
  p=Links();p.feed(path.read_text())
  for url in p.links:
   u=urlparse(url)
   if not u.scheme and not u.netloc:
    check((path.parent/unquote(u.path)).exists(),f'broken {path.name}: {url}')
  check('Flagged for Review' in path.read_text(),'missing review navigation')
 before={p.name:p.read_bytes() for p in SITE.iterdir() if p.is_file()}
 subprocess.run([sys.executable,str(Path(__file__).with_name('build_site.py'))],check=True)
 after={p.name:p.read_bytes() for p in SITE.iterdir() if p.is_file()}
 check(before==after,'nondeterministic build')
 for k in ('golf','volleyball','rugby_union','cricket','snooker','darts','baseball','gaelic','greyhounds','tennis','motor_racing','handball','ice_hockey','basketball','rugby_league'):
  check((SITE/(k+'.html')).exists(),'missing sport '+k)
 print(f'PASS {checks} source-hash, isolation, link, sport and deterministic-build checks')
if __name__=='__main__':main()

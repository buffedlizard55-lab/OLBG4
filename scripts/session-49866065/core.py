"""Evidence primitives and conservative independent fair-price arithmetic (stdlib only)."""
from __future__ import annotations
import gzip
import hashlib
import html
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'data/session-49866065'
SPORTS = {
 'Golf': ('olbg_golf_5', 'https://www.pgatour.com/leaderboard'),
 'Volleyball': ('olbg_volleyball_21', 'https://www.legavolley.it/calendario/'),
 'Rugby Union': ('olbg_rugby_union_9', 'https://www.unitedrugby.com/'),
 'Cricket': ('olbg_cricket_7', 'https://www.cricket.com.au/fixtures'),
 'Snooker': ('olbg_snooker_8', 'https://www.wst.tv/'),
 'Darts': ('olbg_darts_15', 'https://www.pdc.tv/'),
 'Baseball': ('olbg_baseball_12', 'https://www.mlb.com/schedule'),
 'Gaelic Sports': ('olbg_gaelic_25', 'https://www.gaa.ie/fixtures'),
 'Greyhounds': ('olbg_greyhounds_28', 'https://www.gbgb.org.uk/'),
 'Tennis': ('olbg_tennis_3', 'https://www.wtatennis.com/scores'),
 'Motor Racing': ('olbg_motor_racing_14', 'https://www.formula1.com/en/racing/2026'),
 'Handball': ('olbg_handball_20', 'https://ehfcl.eurohandball.com/'),
 'Ice Hockey': ('olbg_ice_hockey_13', 'https://www.nhl.com/schedule'),
 'Basketball': ('olbg_basketball_4', 'https://www.nba.com/schedule'),
 'Rugby League': ('olbg_rugby_league_10', 'https://www.internationalrugbyleague.com/'),
}

def slug(s): return re.sub('[^a-z0-9]+', '-', s.lower()).strip('-')
def instant(s):
    if not isinstance(s, str) or not re.search(r'(Z|[+-]\d\d:\d\d)$', s): return None
    try: return datetime.fromisoformat(s.replace('Z', '+00:00')).astimezone(timezone.utc)
    except ValueError: return None

def norm(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)

def pointer(value, path):
    for p in path.split('/')[1:]:
        p = p.replace('~1', '/').replace('~0', '~')
        value = value[int(p)] if isinstance(value, list) else value[p]
    return value

class Evidence:
    def __init__(self, directory=DATA/'capture'):
        self.directory = Path(directory)
        self.manifest = json.loads((self.directory/'manifest.json').read_text())
        self.records = {r['id']:r for r in self.manifest['records']}
        self.cache = {}
        self.json_cache = {}
        self.cutoff = instant(self.manifest['finished_at'])
        if not self.cutoff: raise ValueError('Capture must carry a timezone-aware cutoff')
        for r in self.records.values():
            if r.get('file'):
                p = self.directory/r['file']
                if not p.resolve().is_relative_to(self.directory.resolve()): raise ValueError('Unsafe evidence path')
                raw = gzip.decompress(p.read_bytes())
                if hashlib.sha256(raw).hexdigest() != r['sha256']: raise ValueError(f"Evidence tampering: {r['id']}")
                if len(raw) != r['bytes']: raise ValueError('Evidence byte-count mismatch')
                self.cache[r['id']] = raw
    def text(self, target): return self.cache.get(target, b'').decode('utf-8', errors='replace')
    def json(self, target):
        if target not in self.json_cache:
            try:
                text=self.text(target)
                if target=='cricket_au_fixtures':
                    m=re.search(r"window\.FIXTURES_DATA\s*=\s*JSON\.parse\('((?:\\.|[^'\\])*)'\)",text)
                    if not m: raise ValueError('No public embedded fixture array')
                    # Decode the JS string literal without evaluating JavaScript.
                    text=json.loads('"'+m.group(1).replace("\\'","'")+'"')
                self.json_cache[target] = json.loads(text)
            except (ValueError, TypeError): self.json_cache[target] = None
        return self.json_cache[target]
    def fact(self, target, path, label):
        record = self.records[target]
        value = pointer(self.json(target), path)
        if value is None or value == '': return None
        return dict(label=label,value=value,target=target,pointer=path,url=record['url'],sha256=record['sha256'],kind='embedded-json' if target=='cricket_au_fixtures' else 'json')
    def excerpt_fact(self,target,start,end,label):
        record=self.records[target]
        value=html.unescape(self.text(target)[start:end]).strip()
        return dict(label=label,value=value,target=target,pointer=f'html-chars:{start}:{end}',url=record['url'],sha256=record['sha256'],kind='html-excerpt')
    def fact_value(self,f):
        if f.get('kind')=='html-excerpt':
            _,start,end=f['pointer'].split(':')
            return html.unescape(self.text(f['target'])[int(start):int(end)]).strip()
        return pointer(self.json(f['target']),f['pointer'])

def price(p):
    if not math.isfinite(p) or not 0 < p < 1: raise ValueError('Probability must lie strictly inside (0,1)')
    return dict(probability=p,decimal=1/p,american=(-100*p/(1-p) if p >= .5 else 100*(1-p)/p))

def in_window(p): return -250 <= price(p)['american'] <= 10000

def log5(wa,ga,wb,gb):
    if not all(isinstance(x, int) and not isinstance(x,bool) for x in (wa,ga,wb,gb)): raise ValueError('Integer records required')
    if not 0 <= wa <= ga or not 0 <= wb <= gb or min(ga,gb) < 1: raise ValueError('Invalid season record')
    # Explicit subjective prior: Beta(2,2). No bookmaker or consensus inputs.
    a,b = (wa+2)/(ga+4),(wb+2)/(gb+4)
    return a*(1-b)/(a*(1-b)+b*(1-a))

def poisson_grid(a,b):
    if not all(math.isfinite(x) and 0 < x <= 15 for x in (a,b)): raise ValueError('Goal means outside supported range')
    def pmf(mu):
        vals=[math.exp(-mu)]
        for k in range(1,100): vals.append(vals[-1]*mu/k)
        return vals
    aa,bb=pmf(a),pmf(b)
    return [(i,j,p*q) for i,p in enumerate(aa) for j,q in enumerate(bb)]

# Lexical string reader: never executes JavaScript or searches across a tips array boundary.
def balanced(text,start,opening='[',closing=']'):
    depth=0; quote=None; escaped=False
    for i in range(start,len(text)):
        c=text[i]
        if quote:
            if escaped: escaped=False
            elif c=='\\': escaped=True
            elif c==quote: quote=None
        elif c in ('"',"'"): quote=c
        elif c==opening: depth+=1
        elif c==closing:
            depth-=1
            if depth==0: return text[start:i+1]
    raise ValueError('Truncated data payload')

FIELD=re.compile(r'(?:^|[,{])\s*([a-zA-Z_][a-zA-Z_0-9]*):\s*("(?:\\.|[^"\\])*"|-?\d+(?:\.\d+)?|true|false|null)')
def parse_tips(text):
    result=[]
    for m in re.finditer(r'\btips:\s*\[',text):
        body=balanced(text,m.end()-1)
        for x in re.finditer(r'\{id:"[0-9a-f]{40}",\s*selection:',body):
            obj=balanced(body,x.start(),'{','}')
            rec={f.group(1):json.loads(f.group(2)) for f in FIELD.finditer(obj)}
            if rec.get('event_name_alias') and rec.get('eventUrl'): result.append(rec)
    return result

def olbg_inventory(e):
    out=[]; seen={}
    for sport,(target,_) in SPORTS.items():
        for i,t in enumerate(parse_tips(e.text(target))):
            url=t['eventUrl']
            if url.startswith('/'): url='https://www.olbg.com'+url
            parsed=urlsplit(url)
            if parsed.scheme!='https' or parsed.hostname not in ('www.olbg.com','olbg.com'): continue
            eid=re.search(r'(?:\?|&)event_id=(\d+)',url)
            key=(sport,eid.group(1) if eid else url,t.get('event_start_unix_timestamp'))
            if key not in seen:
                ts=t.get('event_start_unix_timestamp')
                try: start=datetime.fromtimestamp(int(ts),timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
                except (ValueError,TypeError,OverflowError): start=''
                rec=dict(id=f'olbg-{len(out)+1}',sport=sport,listed_name=t['event_name_alias'],
                         listed_start=start,olbg_url=url,target=target,tip_index=i,active=False,markets=[],official_id=None)
                out.append(rec); seen[key]=rec
            r=seen[key]
            r['active'] |= str(t.get('expired'))=='0'
            market={'name':t.get('market_alias',''),'selection':t.get('selection','')}
            if market not in r['markets']: r['markets'].append(market)
    return out

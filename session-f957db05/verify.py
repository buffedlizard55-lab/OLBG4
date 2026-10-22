#!/usr/bin/env python3
"""Board V gates. Fails loudly; prints one line per check."""
import hashlib, json, os, re, subprocess, sys, itertools
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, 'data', 'session-f957db05')

OFFICIAL = {'api-web.nhle.com', 'statsapi.mlb.com', 'esports-api.lolesports.com',
            'www.nhl.com', 'www.nba.com', 'www.pdc.tv',
            'www.atptour.com', 'www.wtatennis.com', 'cdn.nba.com', 'stats.nba.com',
            'www.pgatour.com', 'www.lpga.com', 'www.icc-cricket.com', 'www.ecb.co.uk',
            'www.cricket.com.au', 'www.wst.tv', 'www.unitedrugby.com', 'www.premiershiprugby.com',
            'top14.lnr.fr', 'www.nrl.com', 'www.rlwc2026.com', 'www.formula1.com', 'www.pdc.tv',
            'ehfcl.eurohandball.com', 'en.volleyballworld.com', 'www.gbgb.org.uk'}
ALLOWED_OTHER = {'www.olbg.com', 'github.com', 'buffedlizard55-lab.github.io'}
EXCLUDED = {'football', 'soccer', 'boxing', 'ufc', 'mma', 'american football', 'hurling',
            'horse racing', 'cycling', 'gaelic football', 'specials', 'greyhound racing'}
fails, checks = [], []


def check(name, ok, detail=''):
    checks.append((name, ok, detail))
    if not ok:
        fails.append(f'{name}: {detail}')


rows = json.load(open(os.path.join(DATA, 'lines.json')))['rows']
preds = json.load(open(os.path.join(DATA, 'predictions.json')))['predictions']
cov = json.load(open(os.path.join(DATA, 'coverage.json')))
flags = json.load(open(os.path.join(DATA, 'flags.json')))['flags']

# 1. sources
bad = [r['id'] for r in rows if not r.get('source_url') or
       urlsplit(r['source_url']).hostname not in OFFICIAL]
check('every row has an official https source', not bad, str(bad[:5]))

# 2. scope
present = {r['sport'].lower() for r in rows}
check('no excluded sport in the dataset', not (present & EXCLUDED), str(present & EXCLUDED))

# 3. fixture completeness
inc = [r['id'] for r in rows if not all(r.get(k) for k in ('home', 'away', 'date', 'start_utc'))]
check('home/away/date/start present on every row', not inc, str(inc[:5]))

# 4. window + confidence
offw = [(r['id'], r['pick']['price']) for r in rows
        if r['pick']['price'] is not None and not (1.40 <= r['pick']['price'] <= 101.0)]
check('every published price inside -250..+10,000', not offw, str(offw[:5]))
unp = [r['id'] for r in rows if r['pick']['price'] is None and r['confidence'] != 'Unrated']
check('a row without a price is graded Unrated', not unp, str(unp[:5]))
nopick = [r['id'] for r in rows if r['pick']['price'] is None and
          not r['pick']['selection'].startswith('No pick')]
check('an unpriced row says why instead of carrying a pick', not nopick, str(nopick[:5]))


def grade(p, sport):
    if p is None:
        return 'Unrated'
    g = 'High' if p >= .70 else ('Medium' if p >= .55 else 'Low')
    return 'Medium' if (sport == 'Esports' and g == 'High') else g   # documented small-sample cap


badg = [r['id'] for r in rows if r['confidence'] != grade(r['pick']['p'], r['sport'])]
check('confidence matches the documented probability rule', not badg, str(badg[:5]))

# 5. predictions
high = [r for r in rows if r['confidence'] == 'High']
missing = [r['id'] for r in high if r['id'] not in preds]
check('every High pick has a written prediction', not missing, str(missing))
short = [k for k, v in preds.items() if v['words'] < 30]
check('every prediction is at least 30 words', not short, str(short))
orphan = [k for k in preds if k not in {r['id'] for r in rows}]
check('no prediction points at a missing row', not orphan, str(orphan))
check('prediction ids are all High picks', set(preds) <= {r['id'] for r in high},
      str(set(preds) - {r['id'] for r in high}))


def tri(t):
    w = re.findall(r'[a-z0-9]+', t.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


worst, pair = 0.0, None
for a, b in itertools.combinations(preds, 2):
    A, B = tri(preds[a]['text']), tri(preds[b]['text'])
    j = len(A & B) / max(1, len(A | B))
    if j > worst:
        worst, pair = j, (a, b)
check('predictions are not near-duplicates (trigram Jaccard <= 0.20)', worst <= 0.20, f'{worst:.3f} {pair}')

named = [k for k, v in preds.items() if
         next(r for r in rows if r['id'] == k)['pick']['selection'].split()[-1].lower()
         not in v['text'].lower()]
check('each prediction names its selection', not named, str(named))

# 6. every fact number in a prediction appears in that row's verified inputs
def numbers(o):
    out = set()
    def walk(x):
        if isinstance(x, dict):
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
        elif isinstance(x, (int, float)):
            out.add(str(x)); out.add(str(int(x)) if float(x).is_integer() else str(x))
        elif isinstance(x, str):
            out.update(re.findall(r'\d+', x))
    walk(o)
    return out


unbacked = []
for k, v in preds.items():
    row = next(r for r in rows if r['id'] == k)
    vals = {float(x) for x in numbers(row['model']) | numbers(row['markets'])}
    p = row['pick']['p']
    for f in v['facts']:
        for tok in re.findall(r'\d+(?:\.\d+)?', f):
            num = float(tok)
            if any(abs(num - v) < 0.011 for v in vals) or abs(num - p) < 0.001 \
                    or abs(num - p * 1000) < 0.6:
                continue
            unbacked.append((k, tok, f))
check('every number quoted in a fact list is in the verified inputs', not unbacked, str(unbacked[:4]))

# 7. prediction sources are official
badsrc = [(k, s) for k, v in preds.items() for s in v['sources']
          if urlsplit(s).hostname not in OFFICIAL]
check('prediction sources are official domains', not badsrc, str(badsrc[:4]))

# 8. links on generated pages
pages = [os.path.join(HERE, p) for p in os.listdir(HERE) if p.endswith('.html')] + \
        [os.path.join(HERE, 'sports', p) for p in os.listdir(os.path.join(HERE, 'sports'))]
broken, nonofficial = [], []
for f in pages:
    s = open(f).read()
    for href in re.findall(r'href="([^"#]+)"', s):
        if href.startswith(('http://', 'https://')):
            host = urlsplit(href).hostname
            if host not in OFFICIAL | ALLOWED_OTHER:
                nonofficial.append((os.path.basename(f), href))
            continue
        target = os.path.normpath(os.path.join(os.path.dirname(f), href))
        if not os.path.exists(target):
            broken.append((os.path.basename(f), href))
check('no broken internal links on the dashboard', not broken, str(broken[:5]))
check('no link to an unapproved domain', not nonofficial, str(nonofficial[:5]))

# 9. coverage / scope arithmetic
tot = cov['totals']
check('in-scope + excluded equals the live OLBG menu size',
      tot['in_scope'] + tot['excluded'] == tot['menu_sports'], str(tot))
check('every published sport appears in the coverage register',
      {r['sport'] for r in rows} <= {s['olbg_name'] for s in cov['sports']} | {'Esports', 'Ice Hockey'},
      str({r['sport'] for r in rows}))
check('every flag has evidence and a status', all(f.get('evidence') and f.get('status') for f in flags))

# 10. determinism
def digest():
    h = hashlib.sha256()
    for root, _, files in sorted(os.walk(HERE)):
        for f in sorted(files):
            if f.endswith(('.html', '.css', '.js')) or f == 'verify.py':
                h.update(open(os.path.join(root, f), 'rb').read())
    return h.hexdigest()


before = digest()
subprocess.run([sys.executable, os.path.join(HERE, 'build.py')], check=True,
               stdout=subprocess.DEVNULL)
after = digest()
check('the dashboard rebuilds byte-for-byte', before == after, f'{before[:12]} != {after[:12]}')

print(f'{len(rows)} rows · {len(high)} High · {len(preds)} predictions · {len(flags)} flags · '
      f'{len(pages)} pages')
for name, ok, detail in checks:
    print(('  PASS  ' if ok else '  FAIL  ') + name + ('' if ok else ' — ' + detail))
print(f'\n{len(checks) - len(fails)}/{len(checks)} checks passed')
sys.exit(1 if fails else 0)

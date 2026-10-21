#!/usr/bin/env python3
"""Board F — independent cross-build audit (session e1e0c27e).

Reads the published data layer of every build (A docs/, B session-7114b6a1/,
C session-74f9613e/, D root hub, E session-4afef1af/) and writes
session-e1e0c27e/data/audit_rows.json + summary.json + crossbuild.json.

Nothing here edits another board's files. The audit is mechanical:
  * every row is normalised to (build, id, sport, event, date, source URLs)
  * every source URL is classified by domain: official (governing body /
    league / official data feed), olbg (aggregator), secondary (media,
    wikipedia, stats sites, venue/host pages), none
  * a row "meets the brief" only if at least one source is official
  * the build's own verified/flag state is carried so mismatches can be seen
"""
import json, os, re, sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'session-e1e0c27e', 'data')
os.makedirs(OUT, exist_ok=True)

OFFICIAL = {
    # leagues / governing bodies / official data feeds
    'nba.com', 'cdn.nba.com', 'stats.nba.com', 'nhl.com', 'api-web.nhle.com',
    'mlb.com', 'statsapi.mlb.com', 'atptour.com', 'wtatennis.com', 'pdc.tv',
    'wst.tv', 'icc-cricket.com', 'cricket.com.au', 'nzc.nz', 'cricsa.co.za',
    'acb.af', 'pcb.com.pk', 'ehfcl.eurohandball.com', 'eurohandball.com',
    'ihf.info', 'fivb.com', 'volleyballworld.com', 'nrl.com',
    'stats.unitedrugby.com', 'unitedrugby.com', 'premiershiprugby.com',
    'world.rugby', 'pgatour.com', 'lpga.com', 'europeantour.com',
    'bwfbadminton.com', 'ittf.com', 'worldtabletennis.com', 'fftt.com',
    'afl.com.au', 'lolesports.com', 'valorantesports.com', 'gbgb.org.uk',
    'galwaygaa.ie', 'gaacork.ie', 'formula1.com', 'euroleaguebasketball.net',
    # national leagues / federations / official live-score domains used by Build G
    'protennislive.com', 'wtafiles.wtatennis.com', 'lnr.fr', 'plusliga.pl', 'tauron1liga.pl',
    'cricket.co.za', 'ice.hockey', 'volleyball-bundesliga.de', 'championsleague.basketball',
    'handbollsligan.se', 'legavolleyfemminile.it', 'tophaandbold.dk', 'kbl.or.kr', 'ecb.co.uk',
    'cricketireland.ie', 'munster.gaa.ie', 'gaa.ie', 'nottingham-greyhounds.co.uk', 'handball.no',
    'shl.se', 'mestaruusliiga.fi', 'volleybal.nl',
}
SECONDARY_NOTE = {
    'espn.com': 'media', 'bbc.com': 'media', 'bbc.co.uk': 'media',
    'skysports.com': 'media', 'wikipedia.org': 'wiki (user-edited)',
    'cricinfo.com': 'media/stats', 'espncricinfo.com': 'media/stats',
    'snooker.org': 'fan/stats database', 'etusuora.com': 'betting media',
    'findmygroup.uk': 'travel/ticket site', 'tempo.co': 'media',
    'usatoday.com': 'media', 'sportsdata.usatoday.com': 'media/stats',
    'basketnews.com': 'media', 'ariananews.af': 'media',
    'olympics.com': 'IOC news (not the competition organiser)',
    'montpellier.fr': 'host-city page (not the organiser)',
}

def domain(url):
    try:
        return urlparse(url).netloc.lower().removeprefix('www.')
    except Exception:
        return ''

def classify(url):
    d = domain(url)
    if not d:
        return 'none', ''
    if d == 'olbg.com':
        return 'olbg', 'aggregator / tipster site (not an official fixture source)'
    for o in OFFICIAL:
        if d == o or d.endswith('.' + o):
            return 'official', ''
    for s, note in SECONDARY_NOTE.items():
        if d == s or d.endswith('.' + s):
            return 'secondary', note
    return 'secondary', 'unlisted domain — review'

def et_date(utc_iso):
    try:
        dt = datetime.fromisoformat(utc_iso.replace('Z', '+00:00'))
        return dt.astimezone(ZoneInfo('America/New_York')).date().isoformat()
    except Exception:
        return ''

def norm_team(s):
    s = (s or '').lower()
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return ' '.join(s.split())

rows = []

def add(build, rid, sport, competition, event, date, sources, own_status, own_flag, pick, confidence, prediction, page, teams=None, extra=None):
    srcs = [s for s in sources if s]
    classes = [classify(s) for s in srcs]
    kinds = [c[0] for c in classes]
    if 'official' in kinds:
        verdict = 'official source present'
    elif 'olbg' in kinds and 'secondary' not in kinds:
        verdict = 'OLBG only — no official fixture source'
    elif kinds:
        verdict = 'secondary source only — no official source'
    else:
        verdict = 'no source'
    words = len(re.findall(r"[A-Za-z0-9'’\-]+", prediction or ''))
    rows.append({
        'build': build, 'id': rid, 'sport': sport, 'competition': competition,
        'event': event, 'date': date, 'sources': srcs,
        'source_classes': [{'url': u, 'class': c[0], 'note': c[1]} for u, c in zip(srcs, classes)],
        'verdict': verdict, 'own_status': own_status, 'own_flag': bool(own_flag),
        'pick': pick, 'confidence': (confidence or '').lower(),
        'prediction_words': words, 'page': page,
        'teams': teams or [], 'extra': extra or {},
    })

# ---------- Build A ----------
A = json.load(open(os.path.join(ROOT, 'data', 'rows.json')))
for i, r in enumerate(A, 1):
    add('A', f'A-{i:03d}', r['sport'], r['competition'], f"{r['home']} v {r['away']}", r['date'],
        [r.get('source')], r.get('status'), r.get('flag'), r.get('pick'), r.get('confidence'),
        r.get('prediction'), 'docs/', [norm_team(r['home']), norm_team(r['away'])])

# ---------- Build B ----------
B = json.load(open(os.path.join(ROOT, 'data', 'board.json')))['rows']
_bp = json.load(open(os.path.join(ROOT, 'data', 'predictions.json')))
_bpl = _bp['predictions'] if isinstance(_bp, dict) else _bp
B_PRED_NOTE = ''
if not (_bpl and isinstance(_bpl[0], dict) and 'match_id' in _bpl[0]):
    # data/predictions.json no longer holds Build B's schema (overwritten by a later session, commit cf9f024);
    # Build B's published site still embeds its original 9 write-ups, so read the last Build-B version from git.
    import subprocess
    _bpl = json.loads(subprocess.run(['git', 'show', '5918922:data/predictions.json'], capture_output=True, text=True, cwd=ROOT).stdout)['predictions']
    B_PRED_NOTE = 'data/predictions.json on main no longer matches Build B schema; Build B predictions read from git 5918922'
Bpred = {p['match_id']: p for p in _bpl}
for r in B:
    p = Bpred.get(r['id'], {})
    fact_urls = [f.get('source') or f.get('url') for f in p.get('facts', []) if isinstance(f, dict)]
    add('B', r['id'], r['sport'], r.get('competition', ''), r['match'], r.get('time_label', ''),
        [r.get('olbg_url')] + fact_urls, 'priced' if r.get('our_prob') is not None else 'unpriced',
        r.get('flag'), r.get('pick'), r.get('confidence'), p.get('body', ''), 'session-7114b6a1/',
        [norm_team(r['home']), norm_team(r['away'])])

# ---------- Build C ----------
Cj = json.load(open(os.path.join(ROOT, 'data', 'session-74f9613e', 'matches.json')))
Csrc = {s['id']: s for s in json.load(open(os.path.join(ROOT, 'data', 'session-74f9613e', 'sources.json')))['sources']}
Cpred = {p.get('match_id') or p.get('id'): p for p in json.load(open(os.path.join(ROOT, 'data', 'session-74f9613e', 'predictions.json'))).get('predictions', [])}
for r in Cj['matches']:
    urls = [Csrc[s]['url'] for s in r['fixture_sources'] + r['input_sources'] if s in Csrc]
    pk = r.get('pick') or {}
    pr = Cpred.get(r['id'], {})
    add('C', r['id'], r['sport'], r['competition'], f"{r['home']['name']} v {r['away']['name']}",
        et_date(r['start_utc']) or r['start_local'], urls, r['market_status'], not r['priced'],
        pk.get('selection', ''), r['confidence'], pr.get('text') or pr.get('body') or pr.get('prediction', ''),
        'session-74f9613e/', [norm_team(r['home']['name']), norm_team(r['away']['name'])])

# ---------- Build D (root hub) ----------
D = json.load(open(os.path.join(ROOT, 'data', 'matches.json')))
for r in D:
    add('D', r['id'], r['sport'], r['competition'], r['match'], r['date'], [r.get('sourceUrl')],
        'verified' if r.get('verified') else 'unverified', r.get('flagged'), r.get('pick'),
        r.get('confidence'), r.get('prediction') if r.get('confidence') == 'High' else '',
        f"{r['category']}.html", [norm_team(r.get('teamA')), norm_team(r.get('teamB'))],
        {'verified_field': r.get('verified')})

# ---------- Build E ----------
E = json.load(open(os.path.join(ROOT, 'session-4afef1af', 'data', 'fixtures.json')))
Ean = {a['fixture']['id'] if isinstance(a.get('fixture'), dict) else a.get('id'): a for a in json.load(open(os.path.join(ROOT, 'session-4afef1af', 'data', 'analysis.json')))}
Epred = json.load(open(os.path.join(ROOT, 'session-4afef1af', 'data', 'predictions.json')))
Epred_by = {}
for p in Epred:
    fid = p.get('fixture_id') or (p.get('fixture') or {}).get('id') or p.get('id')
    Epred_by[fid] = p
for f in E:
    p = Epred_by.get(f['id'], {})
    a = Ean.get(f['id'], {})
    pick = ''
    conf = ''
    picks = []
    an = a.get('analysis') if isinstance(a.get('analysis'), dict) else {}
    hp = an.get('headline_pick') or an.get('winner_pick')
    if hp:
        picks = [hp]
        pick = hp.get('selection', '') if isinstance(hp, dict) else str(hp)
        conf = hp.get('confidence', '') if isinstance(hp, dict) else ''
    add('E', f['id'], f['sport'], f['league'], f"{f['home']['name']} v {f['away']['name']}",
        et_date(f['start_utc']), f.get('official_source_urls') or f.get('source_urls'),
        'priced' if picks else 'withheld', not picks, pick, conf,
        p.get('text') or p.get('body') or p.get('prediction', ''), 'session-4afef1af/',
        [norm_team(f['home']['name']), norm_team(f['away']['name'])])

# ---------- Build G (session-6e0f382d/, data/matches/*.json) ----------
import glob
for f in sorted(glob.glob(os.path.join(ROOT, 'data', 'matches', '*.json'))):
    g = json.load(open(f))
    for i, r in enumerate(g.get('matches') or [], 1):
        slug = os.path.basename(f)[:-5]
        add('G', f"G-{slug}-{i:02d}", r.get('sport', ''), r.get('competition', ''), f"{r.get('home','')} v {r.get('away','')}",
            (r.get('date') or '')[:10], [r.get('source_url')], r.get('status', ''), bool(r.get('flags')),
            r.get('pick', ''), r.get('confidence', ''), r.get('prediction') or '', 'session-6e0f382d/',
            [norm_team(r.get('home')), norm_team(r.get('away'))])

# ---------- summary ----------
summary = {'generated_utc': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), 'builds': {}}
for b in 'ABCDEG':
    br = [r for r in rows if r['build'] == b]
    vc = Counter(r['verdict'] for r in br)
    dom = Counter(domain(u) for r in br for u in r['sources'])
    hi = [r for r in br if r['confidence'] == 'high']
    short = [r['id'] for r in hi if r['prediction_words'] and r['prediction_words'] < 30]
    nopred = [r['id'] for r in hi if not r['prediction_words']]
    own_verified_but_nonofficial = [r['id'] for r in br if r['verdict'] != 'official source present' and r['own_status'] in ('Verified', 'verified')]
    summary['builds'][b] = {
        'rows': len(br), 'verdicts': dict(vc), 'domains': dom.most_common(),
        'high_confidence_rows': len(hi), 'high_predictions_under_30_words': short,
        'high_rows_without_prediction_text_in_data': nopred,
        'rows_self_marked_verified_without_official_source': own_verified_but_nonofficial,
        'confidence_mix': dict(Counter(r['confidence'] or 'blank' for r in br)),
    }
summary['total_rows'] = len(rows)
summary['notes'] = [n for n in [B_PRED_NOTE] if n]
summary['total_verdicts'] = dict(Counter(r['verdict'] for r in rows))

# ---------- cross-build fixture matching (team-sport fixtures) ----------
# key = (sorted normalised team pair, ET date)
alias = {
    'crvena zvezda meridianbet belgrade': 'crvena zvezda', 'crvena zvezda meridianbet': 'crvena zvezda',
    'partizan mozzart bet belgrade': 'partizan', 'partizan mozzart bet': 'partizan',
}
def key(r):
    t = sorted(alias.get(x, x) for x in r['teams'] if x)
    if len(t) != 2 or not re.match(r'\d{4}-\d{2}-\d{2}$', r['date'] or ''):
        return None
    return (t[0], t[1], r['date'])
groups = defaultdict(list)
for r in rows:
    k = key(r)
    if k:
        groups[k].append(r)
cross = []
for k, g in groups.items():
    builds = sorted({r['build'] for r in g})
    if len(builds) < 2:
        continue
    picks = {r['build']: (r['pick'] or '') for r in g}
    conf = {r['build']: r['confidence'] for r in g}
    pk = {b: norm_team(p) for b, p in picks.items() if p}
    # do picks name different teams?
    named = set()
    for b, p in pk.items():
        for t in k[:2]:
            if t and (t in p or p in t):
                named.add(t)
    cross.append({'teams': [k[0], k[1]], 'et_date': k[2], 'builds': builds,
                  'ids': {r['build']: r['id'] for r in g}, 'picks': picks, 'confidence': conf,
                  'pick_conflict': len(named) > 1,
                  'sports': sorted({r['sport'] for r in g})})
cross.sort(key=lambda c: (c['et_date'], c['teams']))
summary['cross_build'] = {'fixtures_in_2_or_more_builds': len(cross),
                          'pick_conflicts': sum(1 for c in cross if c['pick_conflict'])}

json.dump(rows, open(os.path.join(OUT, 'audit_rows.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(summary, open(os.path.join(OUT, 'summary.json'), 'w'), indent=1, ensure_ascii=False)
json.dump(cross, open(os.path.join(OUT, 'crossbuild.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(summary, indent=1, ensure_ascii=False))

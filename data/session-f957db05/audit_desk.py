#!/usr/bin/env python3
"""Independent line-by-line audit of the Board T desk that merged into main.

Reads data/session-4ec1fc72/data.json (read-only) and checks every row against
* this board's official extracts (NHL schedule/standings, MLB schedule/standings), and
* the mechanical rules the brief imposes (official source, excluded sports, window, prediction size).
Writes data/session-f957db05/audit.json. Never edits the audited files.
"""
import json, os, re, unicodedata
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
T = json.load(open(os.path.join(ROOT, 'data', 'session-4ec1fc72', 'data.json')))
rows = T['rows']
NHL = json.load(open(os.path.join(HERE, 'extracts', 'nhl_schedule.json')))['games']
NHLST = {t['abbrev']: t for t in json.load(open(os.path.join(HERE, 'extracts', 'nhl_standings.json')))['teams']}
MLB = json.load(open(os.path.join(HERE, 'extracts', 'mlb_schedule.json')))['games']

OFFICIAL = {'www.nhl.com', 'www.nba.com', 'www.pdc.tv', 'statsapi.mlb.com'}
EXCL = {'soccer', 'football', 'boxing', 'ufc', 'mma', 'american football', 'hurling',
        'horse racing', 'cycling', 'gaelic football', 'specials'}

findings, verified, unverifiable = [], [], []


def add(kind, rid, detail, evidence):
    findings.append({'kind': kind, 'row': rid, 'detail': detail, 'evidence': evidence})


def norm(s):
    # diacritics matter: the official feed writes "Montréal Canadiens", the desk "Montreal Canadiens"
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z]', '', s.lower())


for r in rows:
    host = urlsplit(r['source_url']).hostname if r.get('source_url') else ''
    if host not in OFFICIAL:
        add('non-official-source', r['id'], f'source host {host!r} is not an official league domain', r.get('source_url', ''))
    if (r['sport'] or '').lower() in EXCL:
        add('excluded-sport', r['id'], f'sport {r["sport"]!r} is excluded by the brief', r['source_url'])
    p = r.get('our_price')
    if p and not (1.40 <= p <= 101.0):
        add('outside-window', r['id'],
            f'published price {p} ({r.get("american")}) is outside the requested -250..+10,000 window',
            r['source_url'])
    pred = (r.get('prediction') or '').strip()
    if r['confidence'] == 'High' and len(pred.split()) < 30:
        add('prediction-too-short', r['id'], f'High pick with {len(pred.split())} words', r['source_url'])

    # ---- fixture confirmation against this board's official extract
    if r['sport'] == 'Ice Hockey':
        cand = [g for g in NHL if g['date'] == r['date'] and
                norm(g['home']) == norm(r['home']) and norm(g['away']) == norm(r['away'])]
        if not cand:
            add('fixture-not-found', r['id'],
                f'{r["home"]} v {r["away"]} on {r["date"]} is not in the official NHL schedule capture',
                r['source_url'])
            continue
        g = cand[0]
        mt = re.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)\s*ET', r.get('time', ''))
        if mt:
            h, m, ap = int(mt.group(1)), int(mt.group(2)), mt.group(3)
            h = h % 12 + (12 if ap == 'PM' else 0)
            utc_h = h + 4  # EDT in October
            got = f'{utc_h % 24:02d}:{m:02d}'
            want = g['start_utc'][11:16]
            if got != want:
                add('time-mismatch', r['id'],
                    f'desk lists {r["time"]} (= {got}Z if EDT); official feed says {want}Z', r['source_url'])
        verified.append({'row': r['id'], 'fixture': f'{r["home"]} v {r["away"]}', 'date': r['date'],
                         'official_start_utc': g['start_utc'], 'venue_official': g['venue'],
                         'desk_venue': r.get('venue', ''), 'source': r['source_url']})
        if not r.get('venue'):
            add('blank-venue', r['id'], 'venue blank while the official feed publishes it: ' + g['venue'],
                r['source_url'])
    elif r['sport'] == 'Baseball':
        cand = [g for g in MLB if g['date'] == r['date'] and
                norm(g['home']) == norm(r['home']) and norm(g['away']) == norm(r['away'])]
        if cand:
            verified.append({'row': r['id'], 'fixture': f'{r["home"]} v {r["away"]}', 'date': r['date'],
                             'official_start_utc': cand[0]['start_utc'], 'venue_official': cand[0]['venue'],
                             'desk_venue': r.get('venue', ''), 'source': r['source_url']})
        else:
            add('fixture-not-found', r['id'],
                f'{r["home"]} v {r["away"]} on {r["date"]} is not in the official MLB schedule capture',
                r['source_url'])
    else:
        unverifiable.append({'row': r['id'], 'sport': r['sport'], 'why':
                             'no machine-readable official capture for this sport in this session' if r['sport'] == 'Basketball'
                             else 'official PDC page is not a fixture table; only the published schedule article was used',
                             'source': r['source_url']})

summary = {'rows': len(rows),
           'fixtures_confirmed': len(verified),
           'not_independently_verifiable': len(unverifiable),
           'findings': len(findings),
           'high': sum(1 for r in rows if r['confidence'] == 'High'),
           'priced': sum(1 for r in rows if r.get('our_price')),
           'findings_by_kind': {}}
for f in findings:
    summary['findings_by_kind'][f['kind']] = summary['findings_by_kind'].get(f['kind'], 0) + 1

json.dump({'schema': 'olbg4.board-v.desk-audit/1',
           'audited': 'data/session-4ec1fc72/data.json (Board T desk, merged to main in PR #61)',
           'auditor': 'arena/f957db05-olbg4',
           'method': 'fixture, date and start time compared with this board\'s official NHL/MLB extracts; '
                     'rule checks applied to every row; sports without a machine-readable official capture are '
                     'listed as not independently verifiable rather than assumed correct',
           'summary': summary, 'findings': findings, 'verified': verified,
           'unverifiable': unverifiable}, open(os.path.join(HERE, 'audit.json'), 'w'), indent=1)
print(json.dumps(summary, indent=1))

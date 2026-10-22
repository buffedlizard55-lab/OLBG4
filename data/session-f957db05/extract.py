#!/usr/bin/env python3
"""Board V extractor.

Reads the official-source snapshot captured by the Board U collector
(`data/session-e5f2dad3/raw/**`, manifest: `data/session-e5f2dad3/manifest.json`)
and the local copy under `data/session-f957db05/raw/**`, and emits compact
extracts. Every emitted value is copied from the raw bytes; nothing is inferred.

Run: python3 data/session-f957db05/extract.py
"""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PEER = os.path.join(ROOT, 'data', 'session-e5f2dad3')
LOCAL = os.path.join(HERE, 'raw')
OUT = os.path.join(HERE, 'extracts')


def find(fname):
    for base in (LOCAL, os.path.join(PEER, 'raw')):
        p = os.path.join(base, fname)
        if os.path.exists(p):
            return p
    return None


def load_json(fname):
    p = find(fname)
    if not p:
        sys.exit('missing raw file: ' + fname)
    with open(p, 'rb') as fh:
        b = fh.read()
    return json.loads(b), hashlib.sha256(b).hexdigest(), len(b)


def peer_manifest():
    for p in (os.path.join(LOCAL, 'peer-manifest.json'), os.path.join(PEER, 'manifest.json')):
        if os.path.exists(p):
            with open(p) as fh:
                return json.load(fh)
    return {'targets': []}


def url_for(name, targets):
    for t in targets:
        if t.get('name') == name:
            return t.get('url'), t.get('fetched_at_utc')
    return None, None


def main():
    os.makedirs(OUT, exist_ok=True)
    man = {'schema': 'olbg4.board-v.extracts/1', 'files': []}
    targets = peer_manifest()['targets']

    # ---------------- NHL schedule (12 dates) -------------------------------
    games, sched_sources = [], []
    dates = ['2026-10-22','2026-10-23','2026-10-24','2026-10-25','2026-10-26',
             '2026-10-27','2026-10-28','2026-10-29','2026-10-30','2026-10-31',
             '2026-11-01','2026-11-02']
    for d in dates:
        name = 'nhl_schedule_' + d
        doc, sha, size = load_json(name + '.json')
        url, fetched = url_for(name, targets)
        sched_sources.append({'file': name + '.json', 'url': url,
                              'sha256': sha, 'bytes': size, 'fetched_at_utc': fetched})
        for week in doc.get('gameWeek', []):
            if week.get('date') != d:
                continue
            for g in week.get('games', []):
                if g.get('gameType') != 2:
                    continue
                games.append({
                    'sport': 'Ice Hockey', 'competition': 'NHL regular season',
                    'game_id': g['id'],
                    'date': d,
                    'start_utc': g['startTimeUTC'],
                    'venue': (g.get('venue') or {}).get('default', ''),
                    'home': g['homeTeam']['placeName']['default'] + ' ' + g['homeTeam']['commonName']['default'],
                    'away': g['awayTeam']['placeName']['default'] + ' ' + g['awayTeam']['commonName']['default'],
                    'home_abbrev': g['homeTeam']['abbrev'], 'away_abbrev': g['awayTeam']['abbrev'],
                    'state': g.get('gameState', ''),
                    'source_url': url,
                })
    games.sort(key=lambda r: (r['date'], r['start_utc'], r['game_id']))
    write('nhl_schedule.json', {'schema': 'olbg4.board-v.nhl-schedule/1',
                                'note': 'Every field copied from api-web.nhle.com /v1/schedule/<date>; gameType 2 only (regular season).',
                                'sources': sched_sources, 'games': games})

    # ---------------- NHL standings ----------------------------------------
    doc, sha, size = load_json('nhl_standings_2026-10-22.json')
    url, fetched = url_for('nhl_standings_2026-10-22', targets)
    teams = []
    for t in doc['standings']:
        teams.append({
            'abbrev': t['teamAbbrev']['default'], 'name': t['teamName']['default'],
            'gp': t.get('gamesPlayed'), 'w': t.get('wins'), 'l': t.get('losses'), 'otl': t.get('otLosses'),
            'pts': t['points'], 'point_pct': t['pointPctg'],
            'gf': t['goalFor'], 'ga': t['goalAgainst'], 'diff': t['goalDifferential'],
            'l10_w': t['l10Wins'], 'l10_l': t['l10Losses'], 'l10_otl': t['l10OtLosses'],
            'l10_pts': t['l10Points'], 'l10_gf': t['l10GoalsFor'], 'l10_ga': t['l10GoalsAgainst'],
            'home_w': t.get('homeWins'), 'home_l': t.get('homeLosses'), 'home_otl': t.get('homeOtLosses'),
            'away_w': t.get('awayWins'), 'away_l': t.get('awayLosses'), 'away_otl': t.get('awayOtLosses'),
            'streak': str(t['streakCode']) + str(t['streakCount']),
            'conf': t['conferenceAbbrev'], 'div': t['divisionName'],
            'conf_seq': t['conferenceSequence'], 'league_seq': t['leagueSequence'],
        })
    write('nhl_standings.json', {
        'schema': 'olbg4.board-v.nhl-standings/1',
        'source_url': url, 'sha256': sha, 'bytes': size, 'fetched_at_utc': fetched,
        'standings_datetime_utc': doc.get('standingsDateTimeUtc'),
        'date_stamp': doc['standings'][0].get('date'),
        'note': 'Copied field by field from api-web.nhle.com /v1/standings/2026-10-22.',
        'teams': teams})

    # ---------------- MLB schedule + standings -----------------------------
    doc, sha, size = load_json('mlb_schedule.json')
    url, fetched = url_for('mlb_schedule', targets)
    mg = []
    for d in doc['dates']:
        for g in d['games']:
            mg.append({'sport': 'Baseball', 'competition': 'MLB post-season',
                       'game_id': str(g['gamePk']), 'date': d['date'],
                       'start_utc': g['gameDate'],
                       'venue': (g.get('venue') or {}).get('name', ''),
                       'home': g['teams']['home']['team']['name'],
                       'away': g['teams']['away']['team']['name'],
                       'state': g['status']['detailedState'],
                       'source_url': url})
    mg.sort(key=lambda r: (r['date'], r['start_utc']))
    write('mlb_schedule.json', {'schema': 'olbg4.board-v.mlb-schedule/1',
                                'source_url': url, 'sha256': sha, 'bytes': size,
                                'fetched_at_utc': fetched, 'games': mg})

    doc, sha, size = load_json('mlb_standings.json')
    url, fetched = url_for('mlb_standings', targets)
    mt = []
    for rec in doc.get('records', []):
        for t in rec.get('teamRecords', []):
            mt.append({'team': t['team']['name'], 'w': t['wins'], 'l': t['losses'],
                       'pct': t['winningPercentage'],
                       'rs': t.get('runsScored'), 'ra': t.get('runsAllowed'),
                       'diff': t.get('runDifferential')})
    write('mlb_standings.json', {'schema': 'olbg4.board-v.mlb-standings/1',
                                 'source_url': url, 'sha256': sha, 'bytes': size,
                                 'fetched_at_utc': fetched, 'teams': mt})

    # ---------------- LoL Esports schedule --------------------------------
    doc, sha, size = load_json('lolesports_schedule.json')
    url, fetched = url_for('lolesports_schedule', targets)
    lol = []
    for e in doc['data']['schedule']['events']:
        m = e.get('match') or {}
        tms = m.get('teams') or []
        if len(tms) < 2:
            continue
        lol.append({'sport': 'Esports', 'competition': (e.get('league') or {}).get('name', ''),
                    'event_id': m.get('id'), 'start_utc': e['startTime'], 'state': e['state'],
                    'best_of': (m.get('strategy') or {}).get('count'),
                    'block': e.get('blockName', ''),
                    'team1': tms[0].get('name'), 'team2': tms[1].get('name'),
                    'score1': (tms[0].get('result') or {}).get('gameWins'),
                    'score2': (tms[1].get('result') or {}).get('gameWins'),
                    'source_url': url})
    write('lolesports_schedule.json', {'schema': 'olbg4.board-v.lolesports/1',
                                       'source_url': url, 'sha256': sha, 'bytes': size,
                                       'fetched_at_utc': fetched, 'events': lol})
    print('extracted NHL games', len(games), 'MLB', len(mg), 'LoL', len(lol))


def write(name, obj):
    p = os.path.join(OUT, name)
    with open(p, 'w') as fh:
        json.dump(obj, fh, indent=1, sort_keys=False)
        fh.write('\n')
    print('wrote', p)


if __name__ == '__main__':
    main()

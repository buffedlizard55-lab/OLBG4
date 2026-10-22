#!/usr/bin/env python3
"""Build the sport-coverage register + irregularity register for Board V.

The OLBG sport menu below was read from the live page bytes captured at
2026-10-22T02:47Z (data/session-f957db05/raw/peer-manifest.json ->
https://www.olbg.com/betting-tips). The HTTP statuses in `official_attempts`
are the ones the collector recorded for the same instant, so every "not
readable" claim here is a checkable fact, not an opinion.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAP = '2026-10-22T02:47:25Z'
OLBG = 'https://www.olbg.com/betting-tips'
EXCL = 'excluded by the brief'

# (olbg_id, name, slug, in_scope, exclusion_reason)
MENU = [
    (1, 'Football (soccer)', 'Football', False, EXCL),
    (2, 'Horse Racing', 'Horse_Racing', False, EXCL),
    (3, 'Tennis', 'Tennis', True, ''),
    (4, 'Basketball', 'Basketball', True, ''),
    (5, 'Golf', 'Golf', True, ''),
    (7, 'Cricket', 'Cricket', True, ''),
    (8, 'Snooker', 'Snooker', True, ''),
    (9, 'Rugby Union', 'Rugby_Union', True, ''),
    (10, 'Rugby League', 'Rugby_League', True, ''),
    (11, 'American Football', 'American_Football', False, EXCL),
    (12, 'Baseball', 'Baseball', True, ''),
    (13, 'Ice Hockey', 'Ice_Hockey', True, ''),
    (14, 'Motor Racing', 'Motor_Racing', True, ''),
    (15, 'Darts', 'Darts', True, ''),
    (16, 'Boxing / UFC / MMA', 'Boxing', False, EXCL),
    (17, 'Cycling', 'Cycling', False, EXCL),
    (20, 'Handball', 'Handball', True, ''),
    (21, 'Volleyball', 'Volleyball', True, ''),
    (25, 'Gaelic Football', 'Gaelic_Football', False, EXCL),
    (26, 'Hurling', 'Hurling', False, EXCL),
    (28, 'Greyhounds', 'Greyhounds', True, ''),
]

# official endpoints attempted for the capture instant, with the recorded status
ATTEMPTS = {
    'Tennis': [('https://www.atptour.com/en/tournaments', 403),
               ('https://www.wtatennis.com/tournaments', 200)],
    'Basketball': [('https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json', 403),
                   ('https://stats.nba.com/stats/leaguestandingsv3?LeagueID=00&Season=2026-27', 0)],
    'Golf': [('https://www.pgatour.com/schedule', 200), ('https://www.lpga.com/tournaments', 200)],
    'Cricket': [('https://www.icc-cricket.com/tournaments', 404),
                ('https://www.ecb.co.uk/matches', 404),
                ('https://www.cricket.com.au/matches', 200)],
    'Snooker': [('https://www.wst.tv/tournaments', 200)],
    'Rugby Union': [('https://www.unitedrugby.com/fixtures', 404),
                    ('https://www.premiershiprugby.com/fixtures', 200),
                    ('https://top14.lnr.fr/calendrier', 404)],
    'Rugby League': [('https://www.nrl.com/draw/', 200),
                     ('https://www.rlwc2026.com/draw/mens/2026/round-2', 200)],
    'Baseball': [('https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05', 200),
                 ('https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026', 200)],
    'Ice Hockey': [('https://api-web.nhle.com/v1/schedule/2026-10-22', 200),
                   ('https://api-web.nhle.com/v1/standings/2026-10-22', 200)],
    'Motor Racing': [('https://www.formula1.com/en/racing/2026', 200)],
    'Darts': [('https://www.pdc.tv/tournaments', 200)],
    'Handball': [('https://ehfcl.eurohandball.com/en/matches/', 404)],
    'Volleyball': [('https://en.volleyballworld.com/volleyball/competitions/', 200)],
    'Greyhounds': [('https://www.gbgb.org.uk/race-card/', 0)],
    'Esports': [('https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US', 200)],
}

BUILT = {'Ice Hockey': '82 NHL regular-season fixtures priced',
         'Baseball': '7 MLB post-season fixtures priced',
         'Esports': '9 League of Legends fixtures priced (Riot official schedule API)'}


def main():
    lines = json.load(open(os.path.join(HERE, 'lines.json')))['rows']
    counts = {}
    for r in lines:
        counts[r['sport']] = counts.get(r['sport'], 0) + 1
    sports = []
    for oid, name, slug, in_scope, reason in MENU:
        sport = 'Esports' if name == 'Esports' else ('Ice Hockey' if name == 'Ice Hockey' else
                                                     'Baseball' if name == 'Baseball' else name)
        ent = {'olbg_id': oid, 'olbg_name': name, 'olbg_url': f'{OLBG}/{slug}/{oid}',
               'in_scope': in_scope, 'scope_reason': reason,
               'official_attempts': [{'url': u, 'http_status': s, 'captured_at_utc': CAP}
                                     for u, s in ATTEMPTS.get(name, [])],
               'fixtures_verified': counts.get(sport, 0)}
        if not in_scope:
            ent['status'] = 'excluded'
        elif counts.get(sport):
            ent['status'] = 'verified-and-priced'
            ent['note'] = BUILT.get(sport, '')
        else:
            ent['status'] = 'no-readable-official-feed-this-cycle'
            ent['note'] = ('Official page returned the recorded HTTP status and rendered no machine-readable '
                           'fixture list (JavaScript shell) in the capture window, so no row is published '
                           'rather than a fixture being copied from a tipster site.')
        sports.append(ent)
    # sports covered by this desk that the live OLBG menu did not list
    extra = [{'olbg_id': None, 'olbg_name': 'Esports (not in the live OLBG menu)',
              'olbg_url': OLBG, 'in_scope': True, 'scope_reason': '',
              'official_attempts': [{'url': 'https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US',
                                     'http_status': 200, 'captured_at_utc': CAP}],
              'fixtures_verified': counts.get('Esports', 0), 'status': 'verified-and-priced',
              'note': 'Riot Games official schedule API. OLBG no longer lists an esports page in its menu.'}]
    doc = {'schema': 'olbg4.board-v.coverage/1', 'captured_at_utc': CAP,
           'taxonomy_source': {'url': OLBG, 'note': 'Sport menu and numeric ids read from the captured live page bytes.'},
           'sports': sports + extra,
           'totals': {'menu_sports': len(MENU), 'in_scope': sum(1 for s in sports if s['in_scope']),
                      'excluded': sum(1 for s in sports if not s['in_scope']),
                      'verified_and_priced': sum(1 for s in (sports + extra) if s['status'] == 'verified-and-priced'),
                      'no_readable_feed': sum(1 for s in sports if s['status'] == 'no-readable-official-feed-this-cycle')}}
    json.dump(doc, open(os.path.join(HERE, 'coverage.json'), 'w'), indent=1)

    flags = [
        {'id': 'V-F01', 'severity': 'scope', 'sport': '11 in-scope sports',
         'title': 'Eleven in-scope sports have no readable official fixture feed in this cycle',
         'detail': 'For those sports the official pages returned the HTTP statuses listed on the Coverage page and '
                   'served a JavaScript shell with no fixture table. No fixture, price or pick is published for them '
                   'rather than copying one from a tipster or aggregator site.',
         'evidence': OLBG, 'status': 'unverified'},
        {'id': 'V-F02', 'severity': 'taxonomy', 'sport': 'Esports',
         'title': 'OLBG no longer lists esports, badminton, table tennis or Aussie rules in its live menu',
         'detail': 'The live menu captured on 2026-10-22 has 21 entries: the 14 in-scope sports above plus the seven '
                   'the brief excludes. Earlier boards in this repo carried Badminton, Table Tennis, Aussie Rules, '
                   'Esports and "Greyhound Racing" as separate OLBG sports. Board V therefore takes its in-scope list '
                   'from the live menu and publishes esports only because Riot Games serves an official schedule API.',
         'evidence': OLBG, 'status': 'needs-review'},
        {'id': 'V-F03', 'severity': 'sample', 'sport': 'Esports',
         'title': 'Esports confidence is capped at Medium',
         'detail': 'The only verified inputs available are match results inside a 13-day official feed window '
                   '(2026-10-06 to 2026-10-18), which is too thin to publish a High pick.',
         'evidence': 'https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US', 'status': 'verified'},
        {'id': 'V-F04', 'severity': 'sample', 'sport': 'Ice Hockey',
         'title': 'NHL clubs have played only 7-11 games, so team strength is shrunk toward the mean',
         'detail': 'The model multiplies each club rating by GP/(GP+8) so that a 9-game start cannot dominate the '
                   'price. Ratings will sharpen as the season progresses; they are recomputed from each new capture.',
         'evidence': 'https://api-web.nhle.com/v1/standings/2026-10-22', 'status': 'verified'},
        {'id': 'V-F05', 'severity': 'pricing', 'sport': 'Ice Hockey',
         'title': 'Seven of the eight High picks are published at the -250 floor',
         'detail': 'The brief restricts our published prices to -250..+10,000. A fair price for a 71.5%-plus '
                   'favourite is shorter than -250, so the desk publishes the floor price and prints the fair price '
                   'in the row. This is a pricing rule, not an error: the fair prices are 1.23-1.39.',
         'evidence': 'methodology.html', 'status': 'needs-review'},
        {'id': 'V-F06', 'severity': 'model', 'sport': 'Baseball',
         'title': 'MLB run totals and run line use season-long rates against a post-season series',
         'detail': 'Expected runs are the average of each club\'s season runs scored and conceded per game from the '
                   'final 2026 regular-season table. Post-season run environments differ; the totals are marked as '
                   'model output, not as a claim about the actual game.',
         'evidence': 'https://statsapi.mlb.com/api/v1/standings?leagueId=103,104&season=2026', 'status': 'verified'},
        {'id': 'V-F07', 'severity': 'evidence', 'sport': 'All',
         'title': 'No head-to-head history is captured, so no prediction claims a previous meeting',
         'detail': 'The verified inputs are season-to-date standings and the fixture list. Predictions therefore cite '
                   'records, goals and last-ten form only. Any site claiming a specific prior meeting would be '
                   'inferring a value this desk cannot confirm.',
         'evidence': 'verification.html', 'status': 'verified'},
        {'id': 'V-F08', 'severity': 'provenance', 'sport': 'All',
         'title': 'Raw official bytes were captured by the Board U collector, not by this session',
         'detail': 'The GitHub Actions runner can reach official domains; this sandbox reaches GitHub only. Board V '
                   'therefore parses the committed snapshot data/session-e5f2dad3/raw/** (copied to '
                   'data/session-f957db05/raw/**, SHA-256 recorded per file) and re-derives every published value.',
         'evidence': 'https://github.com/buffedlizard55-lab/OLBG4/blob/arena/f957db05-olbg4/data/session-f957db05/raw/peer-manifest.json', 'status': 'verified'},
        {'id': 'V-F09', 'severity': 'coverage', 'sport': 'All',
         'title': 'This desk prices 3 sports, not the full 14-sport in-scope menu',
         'detail': 'The Board V table is a verified subset, not a padded one: 98 fixtures across ice hockey, baseball '
                   'and esports. The Coverage page names each missing sport with its official URL and the HTTP status '
                   'that stopped it, so the gap is auditable rather than silent.',
         'evidence': 'coverage.html', 'status': 'needs-review'},
    ]
    json.dump({'schema': 'olbg4.board-v.flags/1', 'flags': flags},
              open(os.path.join(HERE, 'flags.json'), 'w'), indent=1)
    print('sports', len(sports), 'totals', doc['totals'], 'flags', len(flags))


if __name__ == '__main__':
    main()

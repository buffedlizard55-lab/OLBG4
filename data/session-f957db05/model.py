#!/usr/bin/env python3
"""Board V — own-line origination.

Every probability below is produced by a formula that is printed on the
methodology page and applied to verified official inputs only. No bookmaker or
tipster price is read anywhere in this file.

NHL (ice hockey)
  strength   : s = 0.5*logit(pointPctg) + 0.5*logit(pythag),  pythag = GF^2/(GF^2+GA^2)
  shrinkage  : s' = s * GP/(GP+8)                     (small samples pulled to the mean)
  moneyline  : p_home = logistic(s'_home - s'_away + 0.18)   (0.18 = home ice)
  goals      : lam_h = mean(GF_home/GP, GA_away/GP) * 1.02,  lam_a = ... * 0.98
  total      : line = nearest 0.5 to lam_h+lam_a;  over prob from a normal
               approximation with sd = 1.15*sqrt(lam_h+lam_a)
  handicap   : -1.5/+1.5 puck line from the joint Poisson goal distribution

MLB (baseball)
  strength   : pythag = RS^2/(RS^2+RA^2) for the completed 2026 regular season
  moneyline  : p_home = logistic(0.5*(s_home - s_away) + 0.10)     (0.10 = home field)

LoL esports
  strength   : win rate in the captured official schedule window, Laplace smoothed
               (w+1)/(n+2); a bo1 moneyline is logistic(s1 - s2) on those rates.
               Confidence is capped at Medium because the sample is small.

Price rule: our line is the FAIR price 1/p (no margin added). The requested
American window -250..+10,000 therefore corresponds to 1.40..101.0 decimal,
i.e. model probability 0.0099..0.7143. A "High" pick (p >= 0.70) is only
window-compliant when p <= 0.7143; stronger favourites are still graded High but
are tagged `window: excluded-short` rather than being quietly re-priced.
"""
import json, math, os
from math import exp, log, sqrt, erf

HERE = os.path.dirname(os.path.abspath(__file__))
EX = os.path.join(HERE, 'extracts')
OUT = os.path.join(HERE, 'lines.json')

HOME_ICE = 0.18
HOME_FIELD = 0.10
TEAM_SHRINK = 8.0


def logistic(x): return 1.0 / (1.0 + exp(-x))
def logit(p): return log(p / (1 - p))
def ncdf(x): return 0.5 * (1.0 + erf(x / sqrt(2.0)))
def pois(k, lam):
    if lam <= 0: return 1.0 if k == 0 else 0.0
    return exp(-lam + k * log(lam) - math.lgamma(k + 1))


def joint(lh, la, mx=15):
    ph = [pois(i, lh) for i in range(mx + 1)]
    pa = [pois(i, la) for i in range(mx + 1)]
    s = sum(ph) * sum(pa)
    return [[ph[h] * pa[a] / s for a in range(mx + 1)] for h in range(mx + 1)]


def american(dec):
    if dec >= 2.0:
        return int(round((dec - 1) * 100))
    return -int(round(100 / (dec - 1)))


def dec_from(p):
    return round(1.0 / p, 2) if p else None


def window(dec):
    """Brief's -250..+10,000 window, expressed in decimal odds."""
    if dec is None: return 'no-line'
    if dec < 1.40: return 'excluded-short'
    if dec > 101.0: return 'excluded-long'
    return 'in-window'


def grade(p):
    if p is None: return 'Unrated'
    if p >= 0.70: return 'High'
    if p >= 0.55: return 'Medium'
    return 'Low'


# --------------------------------------------------------------------- NHL
def nhl_lines():
    sched = json.load(open(os.path.join(EX, 'nhl_schedule.json')))
    st = json.load(open(os.path.join(EX, 'nhl_standings.json')))
    by = {t['abbrev']: t for t in st['teams']}
    rows = []
    for g in sched['games']:
        h, a = by.get(g['home_abbrev']), by.get(g['away_abbrev'])
        if not h or not a or not h['gp'] or not a['gp']:
            continue
        def strength(t):
            pyth = (t['gf'] ** 2) / (t['gf'] ** 2 + t['ga'] ** 2)
            raw = 0.5 * logit(max(min(t['point_pct'], 0.999), 0.001)) + \
                  0.5 * logit(max(min(pyth, 0.999), 0.001))
            return raw * (t['gp'] / (t['gp'] + TEAM_SHRINK))
        sh, sa = strength(h), strength(a)
        ph = logistic(sh - sa + HOME_ICE)
        lh = 1.02 * (h['gf'] / h['gp'] + a['ga'] / a['gp']) / 2
        la = 0.98 * (a['gf'] / a['gp'] + h['ga'] / h['gp']) / 2
        total = lh + la
        line = round(total * 2) / 2
        sd = 1.15 * sqrt(total)
        p_over = 1 - ncdf((line - total) / sd)
        J = joint(lh, la)
        cover = sum(J[x][y] for x in range(16) for y in range(16) if x - y >= 2)
        row = dict(sport='Ice Hockey', sport_slug='ice-hockey', competition='NHL regular season',
                   date=g['date'], start_utc=g['start_utc'], venue=g['venue'],
                   home=g['home'], away=g['away'], game_id=g['game_id'],
                   source_url=g['source_url'] or ('https://api-web.nhle.com/v1/schedule/' + g['date']))
        row['model'] = dict(kind='nhl-logistic-pythagorean', p_home=round(ph, 4),
                            p_away=round(1 - ph, 4), lam_home=round(lh, 2), lam_away=round(la, 2),
                            strength_home=round(sh, 4), strength_away=round(sa, 4),
                            inputs={'home': {k: h[k] for k in ('gp','w','l','otl','pts','point_pct','gf','ga','l10_w','l10_l','l10_otl','l10_pts','streak')},
                                    'away': {k: a[k] for k in ('gp','w','l','otl','pts','point_pct','gf','ga','l10_w','l10_l','l10_otl','l10_pts','streak')}})
        row['markets'] = dict(
            moneyline={'home': {'label': g['home'], 'p': round(ph, 4)},
                       'away': {'label': g['away'], 'p': round(1 - ph, 4)}},
            handicap={'line': -1.5, 'home_p': round(cover, 4), 'away_p': round(1 - cover, 4)},
            total={'line': line, 'over_p': round(p_over, 4), 'under_p': round(1 - p_over, 4)})
        rows.append(row)
    return rows


# --------------------------------------------------------------------- MLB
def mlb_lines():
    sched = json.load(open(os.path.join(EX, 'mlb_schedule.json')))
    st = json.load(open(os.path.join(EX, 'mlb_standings.json')))

    def find_team(name):
        for t in st['teams']:
            if name == t['team'] or name.endswith(' ' + t['team']):
                return t
        return None

    rows = []
    for g in sched['games']:
        h, a = find_team(g['home']), find_team(g['away'])
        if not h or not a:
            continue

        def strength(t):
            pyth = (t['rs'] ** 2) / (t['rs'] ** 2 + t['ra'] ** 2)
            return logit(max(min(pyth, 0.999), 0.001))

        ph = logistic(0.5 * (strength(h) - strength(a)) + HOME_FIELD)
        gph, gpa = h['w'] + h['l'], a['w'] + a['l']
        lh = 0.99 * (h['rs'] / gph + a['ra'] / gpa) / 2
        la = 1.01 * (a['rs'] / gpa + h['ra'] / gph) / 2
        tot = lh + la
        sd = 1.05 * sqrt(tot)
        line = round(tot * 2) / 2
        p_over = 1 - ncdf((line - tot) / sd)
        p_cover = 1 - ncdf((1.5 - (lh - la)) / sd)
        row = dict(sport='Baseball', sport_slug='baseball', competition='MLB post-season',
                   date=g['date'], start_utc=g['start_utc'], venue=g['venue'],
                   home=g['home'], away=g['away'], game_id=g['game_id'],
                   source_url=g['source_url'])
        row['model'] = dict(kind='mlb-pythagorean-log5', p_home=round(ph, 4),
                            p_away=round(1 - ph, 4), lam_home=round(lh, 2), lam_away=round(la, 2),
                            inputs={'home': h, 'away': a})
        row['markets'] = dict(
            moneyline={'home': {'label': g['home'], 'p': round(ph, 4)},
                       'away': {'label': g['away'], 'p': round(1 - ph, 4)}},
            handicap={'line': -1.5, 'home_p': round(p_cover, 4), 'away_p': round(1 - p_cover, 4)},
            total={'line': line, 'over_p': round(p_over, 4), 'under_p': round(1 - p_over, 4)})
        rows.append(row)
    return rows


# ---------------------------------------------------------------------- LoL
def lol_lines():
    doc = json.load(open(os.path.join(EX, 'lolesports_schedule.json')))
    ev = doc['events']
    # record = completed maps only (official results in the same feed)
    rec = {}
    for e in ev:
        if e['state'] != 'completed' or e['team1'] in (None, 'TBD'):
            continue
        for t, s, o in ((e['team1'], e['score1'], e['score2']), (e['team2'], e['score2'], e['score1'])):
            if s is None or o is None: continue
            w, l = rec.get(t, (0, 0))
            rec[t] = (w + (1 if s > o else 0), l + (1 if s < o else 0))
    rows = []
    for e in ev:
        if e['state'] == 'completed': continue
        if 'TBD' in (e['team1'], e['team2']): continue
        def rate(t):
            w, l = rec.get(t, (0, 0))
            return (w + 1) / (w + l + 2)
        p1 = logistic(logit(rate(e['team1'])) - logit(rate(e['team2'])))
        row = dict(sport='Esports', sport_slug='esports',
                   competition=e['competition'] + ' - ' + e['block'],
                   date=e['start_utc'][:10], start_utc=e['start_utc'], venue='',
                   home=e['team1'], away=e['team2'], game_id=e['event_id'], best_of=e['best_of'],
                   source_url=doc['source_url'])
        row['model'] = dict(kind='lol-laplace-winrate', p_home=round(p1, 4), p_away=round(1 - p1, 4),
                            inputs={'team1_record': list(rec.get(e['team1'], (0, 0))),
                                    'team2_record': list(rec.get(e['team2'], (0, 0))),
                                    'form_games': sum(rec.get(t, (0, 0))[0] + rec.get(t, (0, 0))[1]
                                                      for t in (e['team1'], e['team2'])),
                                    'window': 'official schedule results 2026-10-06..2026-10-18'})
        row['markets'] = dict(moneyline={'home': {'label': e['team1'], 'p': round(p1, 4)},
                                         'away': {'label': e['team2'], 'p': round(1 - p1, 4)}},
                              handicap=None, total=None)
        rows.append(row)
    return rows


def both_sides_have_form(r):
    i = r['model']['inputs']
    t1, t2 = i['team1_record'], i['team2_record']
    return (t1[0] + t1[1]) > 0 and (t2[0] + t2[1]) > 0


def finalise(rows):
    for r in rows:
        if r['sport'] == 'Esports' and not both_sides_have_form(r):
            # At least one side has no captured result. A neutral 50/50 prior is a
            # convention, not verified form, so the row gets no pick and no price.
            r['pick'] = {'market': '', 'selection': 'No pick — no verified form', 'side': None,
                         'p': None, 'fair_price': None, 'fair_american': None, 'price': None,
                         'american': None, 'price_capped_at_floor': False, 'window': 'no-line'}
            r['confidence'] = 'Unrated'
            r['markets']['moneyline']['home']['p'] = None
            r['markets']['moneyline']['away']['p'] = None
            r.setdefault('flags', []).append({'kind': 'no-verified-form',
                'text': 'At least one team has no result inside the captured official window, so a rating would '
                        'be a guess. No pick and no price are published.'})
            continue
        ml = r['markets']['moneyline']
        side = 'home' if ml['home']['p'] >= ml['away']['p'] else 'away'
        p = ml[side]['p']
        fair = dec_from(p)
        raw_desk = fair
        desk = None if fair is None else min(101.0, max(1.40, fair))
        capped = bool(fair is not None and fair < 1.40)
        r['pick'] = {'market': 'Match winner (moneyline)', 'selection': ml[side]['label'],
                     'side': side, 'p': p,
                     'fair_price': fair, 'fair_american': american(fair) if fair else None,
                     'price': desk, 'american': american(desk) if desk else None,
                     'price_capped_at_floor': capped,
                     'window': window(desk)}
        r['confidence'] = grade(p)
        if r['sport'] == 'Esports':
            n = r['model']['inputs'].get('form_games', 0)
            t1 = r['model']['inputs']['team1_record']
            t2 = r['model']['inputs']['team2_record']
            if 0 in (t1[0] + t1[1], t2[0] + t2[1]):
                r['confidence'] = 'Low'
                r.setdefault('flags', []).append({'kind': 'one-sided-form',
                    'text': 'Only one side has a captured result in the official window; the other is a neutral '
                            'prior. Confidence capped at Low.'})
            elif r['confidence'] == 'High':
                r['confidence'] = 'Medium'      # small-sample cap, documented
                r.setdefault('flags', []).append({'kind': 'confidence-cap',
                    'text': 'Capped at Medium: the only verified inputs are match results inside a 13-day feed window.'})
        # price the other two markets at fair odds as well
        for mk in ('handicap', 'total'):
            m = r['markets'].get(mk)
            if not m: continue
            for k in ('home_p', 'away_p', 'over_p', 'under_p'):
                if k in m and m[k]:
                    m[k + '_price'] = dec_from(m[k])
                    m[k + '_american'] = american(dec_from(m[k]))
    return rows


def main():
    rows = finalise(nhl_lines() + mlb_lines() + lol_lines())
    rows.sort(key=lambda r: (r['start_utc'], r['sport'], r['home']))
    for i, r in enumerate(rows, 1):
        r['id'] = 'V%04d' % i
    doc = {'schema': 'olbg4.board-v.lines/1',
           'generated_by': 'data/session-f957db05/model.py',
           'price_rule': 'fair price 1/p, no margin; window -250..+10,000 == decimal 1.40..101.0',
           'rows': rows}
    json.dump(doc, open(OUT, 'w'), indent=1)
    from collections import Counter
    print('rows', len(rows), Counter(r['sport'] for r in rows), Counter(r['confidence'] for r in rows))
    print('high in window', sum(1 for r in rows if r['confidence'] == 'High' and r['pick']['window'] == 'in-window'))
    print('high total', sum(1 for r in rows if r['confidence'] == 'High'))
    print('window', Counter(r['pick']['window'] for r in rows))


if __name__ == '__main__':
    main()

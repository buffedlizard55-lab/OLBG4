#!/usr/bin/env python3
"""
tools/model.py — Mechanical line origination for the OLBG dashboard.

Reads ONLY the verified input files in data/verified/ and writes originated
lines to data/matches/{sport}.json. Every probability comes from a documented
formula applied to verified inputs (see docs/methodology.html). Nothing is
copied from bookmaker or tipster prices.

Confidence rules (applied uniformly):
  high   : model probability >= 0.70 AND inputs are current-season official
           data with an adequate sample (>=5 team games, or full official
           ranking lists)
  medium : probability 0.57-0.699, OR capped (prior-season / secondary /
           small-sample inputs)
  low    : probability < 0.57, qualitative picks, outrights
Caps are applied per league as documented in the verified files' flags.
"""
import json, math, os, re
from math import exp, log, sqrt, erf, comb

ROOT = os.path.join(os.path.dirname(__file__), '..')
VD = os.path.join(ROOT, 'data', 'verified')
OD = os.path.join(ROOT, 'data', 'matches')
os.makedirs(OD, exist_ok=True)

# ---------------------------------------------------------------- helpers
def logistic(x):
    return 1.0 / (1.0 + exp(-x))

def ncdf(x):
    return 0.5 * (1.0 + erf(x / sqrt(2.0)))

def pois(k, lam):
    if lam <= 0:
        return 1.0 if k == 0 else 0.0
    return exp(-lam + k * log(lam) - math.lgamma(k + 1))

def joint_dist(lh, la, mx=60):
    ph = [pois(i, lh) for i in range(mx + 1)]
    pa = [pois(i, la) for i in range(mx + 1)]
    return {(h, a): ph[h] * pa[a] for h in range(mx + 1) for a in range(mx + 1)}

def diff_total(jd):
    diff, tot = {}, {}
    for (h, a), p in jd.items():
        diff[h - a] = diff.get(h - a, 0.0) + p
        tot[h + a] = tot.get(h + a, 0.0) + p
    return diff, tot

def race_score_dist(p, need):
    """{(winner_is_p_side, loser_score): prob} for race to `need`."""
    out = {}
    q = 1 - p
    for k in range(need):
        out[(True, k)] = comb(need - 1 + k, k) * p**need * q**k
        out[(False, k)] = comb(need - 1 + k, k) * q**need * p**k
    return out

TIERS = ['low', 'medium', 'high']
def confidence(prob, cap='high'):
    if prob is None:
        t = 'low'
    elif prob >= 0.70:
        t = 'high'
    elif prob >= 0.57:
        t = 'medium'
    else:
        t = 'low'
    return TIERS[min(TIERS.index(t), TIERS.index(cap))]

def fair_odds(p):
    return round(1.0 / p, 2) if p and p > 0 else None

def line(market, selection, line_value, prob):
    return {'market': market, 'selection': selection, 'line': line_value,
            'probability': round(prob, 4) if prob is not None else None,
            'fair_odds': fair_odds(prob)}

def fair_half_line(diff_dist, fav_is_home=True):
    """Half-point handicap on the favourite with cover prob closest to 0.5."""
    best = None
    for _n in range(-90, 91):
        L = _n + 0.5  # half-point handicaps only (no pushes)
        if fav_is_home:
            pc = sum(p for d, p in diff_dist.items() if d > L)
        else:
            pc = sum(p for d, p in diff_dist.items() if -d > L)
        if best is None or abs(pc - 0.5) < abs(best[1] - 0.5):
            best = (L, pc)
    return best

def fair_total_line(tot_dist):
    """Half-point total with P(over) closest to 0.5. Returns (line, p_over)."""
    lo, hi = min(tot_dist), max(tot_dist)
    best = None
    x = lo + 0.5  # half-point totals only (no pushes)
    while x < hi:
        po = sum(p for t, p in tot_dist.items() if t > x)
        if best is None or abs(po - 0.5) < abs(best[1] - 0.5):
            best = (x, po)
        x += 1.0
    return best

def load(sport_file):
    with open(os.path.join(VD, sport_file)) as fh:
        return json.load(fh)

def out(sport_file, payload):
    with open(os.path.join(OD, sport_file), 'w') as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)

def norm_outrights(raw, pick_key='model_pick', basis_key='basis'):
    res = []
    for o in raw or []:
        res.append({
            'event_id': o.get('event_id'),
            'competition': o.get('competition'),
            'date': o.get('date_time') or o.get('date'),
            'pick': o.get(pick_key) or o.get('pick'),
            'pick_probability': o.get('_model_probability'),
            'basis': o.get(basis_key) or o.get('pick_basis') or o.get('basis'),
            'confidence': 'low',
            'source_url': o.get('source_url') or o.get('source'),
            'source_name': o.get('source_name'),
            'flags': o.get('flags') or ([o['flag']] if o.get('flag') else []),
        })
    return res

UNMATCHED = []
def lookup(table, name):
    if name in table:
        return table[name]
    UNMATCHED.append(name)
    return None

def shrunk_rate(pts_for, gp, lg, k):
    return (pts_for + k * lg) / (gp + k)

# ---------------------------------------------------------------- score models
def poisson_match(lh, la, allow_draw, mx=80):
    jd = joint_dist(lh, la, mx)
    diff, tot = diff_total(jd)
    p_home = sum(p for d, p in diff.items() if d > 0)
    p_draw = diff.get(0, 0.0)
    p_away = sum(p for d, p in diff.items() if d < 0)
    if not allow_draw:
        share = lh / (lh + la)
        ot_home = 0.5 + 0.5 * (share - 0.5)
        p_home += p_draw * ot_home
        p_away += p_draw * (1 - ot_home)
        p_draw = None
    fav_home = lh >= la
    hl, hcover = fair_half_line(diff, fav_home)
    tline, pover = fair_total_line(tot)
    return {'p_home': p_home, 'p_draw': p_draw, 'p_away': p_away,
            'handicap': hl, 'handicap_cover': hcover, 'fav_home': fav_home,
            'total_line': tline, 'p_over': pover, 'exp_home': lh, 'exp_away': la}

def normal_match(lh, la, sd_margin, sd_total):
    """Normal margin/total probabilities (for compound-scored sports where
    pure Poisson is under-dispersed). Draw = mass on margin 0."""
    mu_m, mu_t = lh - la, lh + la
    diff = {d: ncdf((d + 0.5 - mu_m) / sd_margin) - ncdf((d - 0.5 - mu_m) / sd_margin)
            for d in range(-90, 91)}
    tot = {t: ncdf((t + 0.5 - mu_t) / sd_total) - ncdf((t - 0.5 - mu_t) / sd_total)
           for t in range(0, 181)}
    p_home = sum(p for d, p in diff.items() if d > 0)
    p_draw = diff.get(0, 0.0)
    p_away = sum(p for d, p in diff.items() if d < 0)
    fav_home = lh >= la
    hl, hcover = fair_half_line(diff, fav_home)
    tline, pover = fair_total_line(tot)
    return {'p_home': p_home, 'p_draw': p_draw, 'p_away': p_away,
            'handicap': hl, 'handicap_cover': hcover, 'fav_home': fav_home,
            'total_line': tline, 'p_over': pover, 'exp_home': lh, 'exp_away': la}

def build_team_match(base, res, home, away, unit, cap):
    fav = home if res['fav_home'] else away
    fav_prob = res['p_home'] if fav == home else res['p_away']
    ml_name = 'Money Line' if res['p_draw'] is None else 'Match Winner (3-way)'
    lines = [line(ml_name, fav, None, fav_prob),
             line('Handicap', f"{fav} -{res['handicap']:g}", -res['handicap'], res['handicap_cover']),
             line('Match Totals', f"Over {res['total_line']:g}", res['total_line'], res['p_over'])]
    base.update({
        'prob_home': round(res['p_home'], 4),
        'prob_draw': round(res['p_draw'], 4) if res['p_draw'] is not None else None,
        'prob_away': round(res['p_away'], 4),
        'pick': fav, 'pick_probability': round(fav_prob, 4),
        'confidence': confidence(fav_prob, cap),
        'expected_score': f"Modelled expected score: {home} {res['exp_home']:.1f} - {res['exp_away']:.1f} {away} ({unit})",
        'lines': lines, 'status': 'modelled', 'prediction': None,
    })
    return base

# ---------------------------------------------------------------- TENNIS
def set_prob_from_game(g):
    q = 1 - g
    win = sum(comb(5 + k, k) * g**6 * q**k for k in range(5))  # 6-0..6-4
    p55 = comb(10, 5) * g**5 * q**5
    win += p55 * (g**2 + 2 * g * q * g)  # 7-5, or 6-6 then tiebreak (won w.p. g)
    return win

def games_per_set_dist(g):
    q = 1 - g
    dist = {}
    for loser in range(5):
        dist[6 + loser] = comb(5 + loser, loser) * (g**6 * q**loser + q**6 * g**loser)
    p55 = comb(10, 5) * g**5 * q**5
    dist[12] = dist.get(12, 0) + p55 * (g**2 + q**2)
    dist[13] = dist.get(13, 0) + p55 * (2 * g * q)
    return dist

def solve_for(fn, target, lo=0.01, hi=0.99):
    for _ in range(60):
        mid = (lo + hi) / 2
        if fn(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2

def model_tennis():
    d = load('tennis.json')
    matches = []
    for m in d['matches']:
        p1, p2 = m['p1'], m['p2']
        pts1, pts2 = max(p1['points'], 1), max(p2['points'], 1)
        pm1 = logistic(1.15 * log(pts1 / pts2))
        fav = p1 if pm1 >= 0.5 else p2
        p_fav = max(pm1, 1 - pm1)
        s = solve_for(lambda s: s * s * (3 - 2 * s), p_fav)
        g = solve_for(set_prob_from_game, s)
        p20, p21 = s**2, 2 * s**2 * (1 - s)
        p3 = 1 - (s**2 + (1 - s)**2)
        gd = games_per_set_dist(g)
        mg = {}
        items = list(gd.items())
        for g1, pr1 in items:
            for g2, pr2 in items:
                mg[g1 + g2] = mg.get(g1 + g2, 0) + pr1 * pr2 * (1 - p3)
                for g3, pr3 in items:
                    mg[g1 + g2 + g3] = mg.get(g1 + g2 + g3, 0) + pr1 * pr2 * pr3 * p3
        tot = sum(mg.values())
        mg = {k: v / tot for k, v in mg.items()}
        tline, pover = fair_total_line(mg)
        exp_games = sum(k * v for k, v in mg.items())
        matches.append({
            'event_id': m['event_id'], 'sport': 'Tennis',
            'competition': m['competition'] + (f" - {m['round']}" if m.get('round') else ''),
            'date': '2026-10-21/22 (per OLBG listing; see flags)',
            'venue': None, 'home': p1['name'], 'away': p2['name'],
            'prob_home': round(pm1, 4), 'prob_draw': None, 'prob_away': round(1 - pm1, 4),
            'pick': fav['name'], 'pick_probability': round(p_fav, 4),
            'confidence': confidence(p_fav),
            'expected_score': f"Most likely: {fav['name']} to win " + ("2-0" if p20 >= p21 else "2-1") + f"; expected total games {exp_games:.1f}",
            'lines': [line('Win Match', fav['name'], None, p_fav),
                      line('Set Betting', f"{fav['name']} 2-0", None, p20),
                      line('Set Betting', f"{fav['name']} 2-1", None, p21),
                      line('1st Set Winner', fav['name'], None, s),
                      line('Total Games', f"Over {tline:g}", tline, pover)],
            'inputs_summary': (f"Official ranking points (19 Oct 2026): {p1['name']} #{p1['rank']} ({pts1} pts) vs "
                               f"{p2['name']} #{p2['rank']} ({pts2} pts). Match prob via logistic on log points ratio "
                               f"(k=1.15); set/game lines chained mechanically (see Methodology)."),
            'form_context': f"{p1['name']}: {p1.get('form','')} {p2['name']}: {p2.get('form','')}".strip(),
            'source_url': m['competition_source'], 'source_name': m['competition_source_name'],
            'flags': m.get('flags', []), 'status': 'modelled', 'prediction': None,
        })
    out('tennis.json', {'sport': 'Tennis', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- BASKETBALL
def parse_pfpa(rec):
    if not rec:
        return None
    mm = re.search(r'PF\s*(\d+)\s*PA\s*(\d+)', rec)
    w = re.match(r'(\d+)-(\d+)', rec)
    if mm and w:
        return int(mm.group(1)), int(mm.group(2)), int(w.group(1)) + int(w.group(2))
    return None

def model_basketball():
    d = load('basketball.json')
    lc = d['league_context']
    el = lc['EuroLeague_2026_27_after_R6']['teams_PF_PA_GP6']
    el_lg = sum(v[0] for v in el.values()) / (6 * len(el))
    ec_teams = {}
    for grp in ('A', 'B', 'C', 'D'):
        for t, v in (lc['EuroCup_2026_27_groups'].get(grp) or {}).items():
            ec_teams[t] = v
    ec_lg = sum(v[3] for v in ec_teams.values()) / sum(v[0] for v in ec_teams.values())
    nba = lc['NBA_2025_26_final_standings_W_L']['teams']
    matches = []
    for m in d['matches']:
        comp = m['competition']
        base = {'event_id': m['event_id'], 'sport': 'Basketball', 'competition': comp,
                'date': m.get('date_time'), 'venue': m.get('venue'),
                'home': m['home'], 'away': m['away'],
                'source_url': m['source'], 'source_name': m['source_name'],
                'flags': list(m.get('flags', [])), 'form_context': m.get('form_note', ''),
                'prediction': None}
        flags_txt = ' '.join(base['flags'])
        if comp.startswith('NBA'):
            th, ta = lookup(nba, m['home']), lookup(nba, m['away'])
            wph = 0.5 + 0.75 * (th['W'] / (th['W'] + th['L']) - 0.5)
            wpa = 0.5 + 0.75 * (ta['W'] / (ta['W'] + ta['L']) - 0.5)
            margin = 26.0 * (wph - wpa) + 2.6
            sd = 12.2
            p_home = ncdf(margin / sd)
            fav_home = margin >= 0
            fav = m['home'] if fav_home else m['away']
            fp = p_home if fav_home else 1 - p_home
            hcap = math.floor(abs(margin)) + 0.5
            cover = 1 - ncdf((hcap - abs(margin)) / sd)
            base.update({'prob_home': round(p_home, 4), 'prob_draw': None, 'prob_away': round(1 - p_home, 4),
                         'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp, 'medium'),
                         'expected_score': f"Modelled margin: {fav} by {abs(margin):.1f} pts (no totals line - see flags)",
                         'lines': [line('Money Line', fav, None, fp),
                                   line('Point Spread', f"{fav} -{hcap:g}", -hcap, cover)],
                         'inputs_summary': (f"Prior-season (2025-26) official W-L: {m['home']} {th['W']}-{th['L']}, {m['away']} "
                                            f"{ta['W']}-{ta['L']}; win% shrunk 25% toward .500, normal margin model (SD 12.2, home +2.6)."),
                         'status': 'modelled'})
        elif comp.startswith('EuroLeague') or comp.startswith('BKT EuroCup'):
            is_el = comp.startswith('EuroLeague')
            lg, k = (el_lg, 3) if is_el else (ec_lg, 2)
            hp = parse_pfpa(m.get('home_record'))
            ap = parse_pfpa(m.get('away_record'))
            if hp is None:
                tv = lookup(el if is_el else ec_teams, m['home'])
                hp = (tv[0], tv[1], 6) if is_el else (tv[3], tv[4], tv[0])
            if ap is None:
                tv = lookup(el if is_el else ec_teams, m['away'])
                ap = (tv[0], tv[1], 6) if is_el else (tv[3], tv[4], tv[0])
            att_h = shrunk_rate(hp[0], hp[2], lg, k); def_h = shrunk_rate(hp[1], hp[2], lg, k)
            att_a = shrunk_rate(ap[0], ap[2], lg, k); def_a = shrunk_rate(ap[1], ap[2], lg, k)
            lh = att_h * def_a / lg; la = att_a * def_h / lg
            ha = 1.0 if 'neutral venue' in flags_txt.lower() else (1.02 if 'Sofia' in flags_txt else 1.04)
            lh *= ha; la /= ha
            res = poisson_match(lh, la, allow_draw=False, mx=170)
            cap = 'high' if is_el else 'medium'
            base['inputs_summary'] = (f"{'EuroLeague' if is_el else 'EuroCup'} official PF/PA: {m['home']} {hp[0]}/{hp[1]} in {hp[2]}g, "
                                      f"{m['away']} {ap[0]}/{ap[1]} in {ap[2]}g; league avg {lg:.1f}/team; shrunk Poisson (k={k}), home x{ha:g}.")
            base = build_team_match(base, res, m['home'], m['away'], 'points', cap)
            base['lines'][1]['market'] = 'Point Spread'
            base['lines'][2]['market'] = 'Game Totals'
        elif comp.startswith('Basketball Champions'):
            base.update({'prob_home': None, 'prob_draw': None, 'prob_away': None,
                         'pick': m['home'], 'pick_probability': None, 'confidence': 'low',
                         'expected_score': 'Not originated (insufficient verified data).',
                         'lines': [],
                         'inputs_summary': (f"Official BCL standings view gave W/L only ({m.get('home_record')} vs "
                                            f"{m.get('away_record')}, one game each). Qualitative pick: designated home team."),
                         'status': 'qualitative'})
        elif comp.startswith('Korean'):
            hw = re.match(r'(\d+)-(\d+)', m.get('home_record', ''))
            aw = re.match(r'(\d+)-(\d+)', m.get('away_record', ''))
            wph = (int(hw.group(1)) + 2) / (int(hw.group(1)) + int(hw.group(2)) + 4)
            wpa = (int(aw.group(1)) + 2) / (int(aw.group(1)) + int(aw.group(2)) + 4)
            margin = 24.0 * (wph - wpa) + 2.4
            sd = 10.5
            p_home = ncdf(margin / sd)
            fav_home = margin >= 0
            fav = m['home'] if fav_home else m['away']
            fp = p_home if fav_home else 1 - p_home
            hcap = math.floor(abs(margin)) + 0.5
            cover = 1 - ncdf((hcap - abs(margin)) / sd)
            base.update({'prob_home': round(p_home, 4), 'prob_draw': None, 'prob_away': round(1 - p_home, 4),
                         'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp, 'low'),
                         'expected_score': f"Modelled margin: {fav} by {abs(margin):.1f} pts (totals not originated - see flags)",
                         'lines': [line('Money Line', fav, None, fp),
                                   line('Point Spread', f"{fav} -{hcap:g}", -hcap, cover)],
                         'inputs_summary': (f"Official KBL W/L only: {m['home']} {m.get('home_record')}, {m['away']} "
                                            f"{m.get('away_record')}; shrunk win% margin model (SD 10.5). Totals blank per verified file."),
                         'status': 'modelled'})
        matches.append(base)
    out('basketball.json', {'sport': 'Basketball', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- HANDBALL
def model_handball():
    d = load('handball.json')
    lc = d['league_context']
    ehf = {}
    for grp, teams in lc['EHF_CL_2026_27_group_phase'].items():
        if isinstance(teams, dict) and grp not in ('source', 'format'):
            for t, v in teams.items():
                ehf[t] = v
    def lg_avg(table):
        return sum(v[4] for v in table.values()) / sum(v[0] for v in table.values())
    danish = lc['Danish_Herreligaen_2026_27']['teams']
    swedish = lc['Swedish_Handbollsligan_2026_27_partial']['teams']
    norwegian = lc['Norwegian_REMA1000_2026_27_partial']['teams']
    QUAL_PICKS = {12108: None, 12110: 'Kosovo'}  # 12108: home side per verified pick_basis
    matches = []
    for m in d['matches']:
        comp = m['competition']
        base = {'event_id': m['event_id'], 'sport': 'Handball', 'competition': comp,
                'date': m.get('date_time'), 'venue': None,
                'home': m['home'], 'away': m['away'],
                'source_url': m['source'], 'source_name': m['source_name'],
                'flags': list(m.get('flags', [])), 'form_context': '', 'prediction': None}
        if m.get('rating_inputs') is None and 'pick_basis' in m:
            pick = QUAL_PICKS.get(m['event_id']) or m['home']
            base.update({'prob_home': None, 'prob_draw': None, 'prob_away': None,
                         'pick': pick, 'pick_probability': None, 'confidence': 'low',
                         'expected_score': 'Not originated (no verified quantitative inputs).',
                         'lines': [], 'inputs_summary': m['pick_basis'], 'status': 'qualitative'})
            matches.append(base)
            continue
        if comp.startswith('EHF Champions'):
            table, lg, k, cap = ehf, lg_avg(ehf), 2, 'medium'
        elif comp.startswith('Danish'):
            table, lg, k, cap = danish, lg_avg(danish), 3, 'high'
        elif comp.startswith('Swedish'):
            table, lg, k, cap = swedish, lg_avg(swedish), 2, 'medium'
        elif comp.startswith('Norwegian'):
            table, lg, k, cap = norwegian, lg_avg(norwegian), 2, 'medium'
        else:
            UNMATCHED.append(f"handball comp {comp}")
            continue
        th, ta = lookup(table, m['home']), lookup(table, m['away'])
        att_h = shrunk_rate(th[4], th[0], lg, k); def_h = shrunk_rate(th[5], th[0], lg, k)
        att_a = shrunk_rate(ta[4], ta[0], lg, k); def_a = shrunk_rate(ta[5], ta[0], lg, k)
        lh = att_h * def_a / lg * 1.05; la = att_a * def_h / lg / 1.05
        res = poisson_match(lh, la, allow_draw=True, mx=70)
        base['inputs_summary'] = (f"Official standings GF/GA: {m['home']} {th[4]}:{th[5]} in {th[0]}g, {m['away']} {ta[4]}:{ta[5]} in {ta[0]}g; "
                                  f"league avg {lg:.1f} goals/team; shrunk Poisson (k={k}), home x1.05; 3-way incl. draw.")
        base = build_team_match(base, res, m['home'], m['away'], 'goals', cap)
        base['lines'][0]['market'] = 'Money Line (3-way)'
        base['lines'].insert(1, line('Money Line (3-way)', 'Draw', None, res['p_draw']))
        matches.append(base)
    out('handball.json', {'sport': 'Handball', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- RUGBY UNION
def model_rugby_union():
    d = load('rugby-union.json')
    lc = d['league_context']
    def lg_avg(table):
        return sum(v[4] for v in table.values()) / sum(v[0] for v in table.values())
    matches = []
    for m in d['matches']:
        key = m['league']
        table = lc[key]['teams']
        lg = lg_avg(table)
        cap = 'medium' if key.startswith('URC') else 'high'
        th, ta = lookup(table, m['home']), lookup(table, m['away'])
        k = 2
        att_h = shrunk_rate(th[4], th[0], lg, k); def_h = shrunk_rate(th[5], th[0], lg, k)
        att_a = shrunk_rate(ta[4], ta[0], lg, k); def_a = shrunk_rate(ta[5], ta[0], lg, k)
        lh = att_h * def_a / lg * 1.10; la = att_a * def_h / lg / 1.10
        # Compound scoring (3/5/7 pts): Normal margin SD 15 / total SD 13.
        res = normal_match(lh, la, sd_margin=15.0, sd_total=13.0)
        base = {'event_id': m['event_id'], 'sport': 'Rugby Union', 'competition': m['competition'],
                'date': m.get('date_time'), 'venue': None, 'home': m['home'], 'away': m['away'],
                'source_url': m['source'], 'source_name': m['source_name'],
                'flags': list(m.get('flags', [])), 'form_context': '', 'prediction': None,
                'inputs_summary': (f"Official table PF/PA: {m['home']} {th[4]}:{th[5]} in {th[0]}g, {m['away']} {ta[4]}:{ta[5]} in {ta[0]}g; "
                                   f"league avg {lg:.1f} pts/team; shrunk attack/defence (k=2), home x1.10; Normal margin SD 15 / total SD 13.")}
        base = build_team_match(base, res, m['home'], m['away'], 'points', cap)
        base['lines'][0]['market'] = 'To Win (3-way incl. draw)'
        base['lines'].insert(1, line('To Win (3-way incl. draw)', 'Draw', None, res['p_draw']))
        matches.append(base)
    out('rugby-union.json', {'sport': 'Rugby Union', 'matches': matches,
                             'outrights': norm_outrights(d.get('outrights'))})
    return matches

# ---------------------------------------------------------------- VOLLEYBALL
def model_volleyball():
    d = load('volleyball.json')
    lc = d['league_context']
    matches = []
    for m in d['matches']:
        base = {'event_id': m['event_id'], 'sport': 'Volleyball', 'competition': m['competition'],
                'date': m.get('date_time'), 'venue': None, 'home': m['home'], 'away': m['away'],
                'source_url': m['source'], 'source_name': m['source_name'],
                'flags': list(m.get('flags', [])), 'form_context': '', 'prediction': None}
        if m.get('rating_inputs') is None and 'pick_basis' in m:
            base.update({'prob_home': None, 'prob_draw': None, 'prob_away': None,
                         'pick': m['home'], 'pick_probability': None, 'confidence': 'low',
                         'expected_score': 'Not originated (no verified numeric inputs).',
                         'lines': [], 'inputs_summary': m['pick_basis'], 'status': 'qualitative'})
            matches.append(base)
            continue
        key = m['league']
        table = lc[key]['teams']
        th, ta = lookup(table, m['home']), lookup(table, m['away'])
        def srate(v):
            return (v[2] + 2.0) / (v[2] + v[3] + 4.0)
        rh, ra = srate(th), srate(ta)
        p_set = rh * (1 - ra) / (rh * (1 - ra) + ra * (1 - rh))
        p_set = logistic(log(p_set / (1 - p_set)) + 0.12)
        dist = race_score_dist(p_set, 3)
        p_home = sum(v for (w, _), v in dist.items() if w)
        fav_home = p_home >= 0.5
        fav = m['home'] if fav_home else m['away']
        fp = p_home if fav_home else 1 - p_home
        dmap, tot_sets = {}, {}
        for (w, ls), v in dist.items():
            margin = (3 - ls) if w else (ls - 3)
            dmap[margin] = dmap.get(margin, 0) + v
            tot_sets[3 + ls] = tot_sets.get(3 + ls, 0) + v
        hl, hcover = fair_half_line(dmap, fav_home)
        p_over35 = sum(v for t, v in tot_sets.items() if t > 3.5)
        lines = [line('Win Match', fav, None, fp),
                 line('Set Handicap', f"{fav} -{hl:g} sets", -hl, hcover),
                 line('Total Sets', 'Over 3.5', 3.5, p_over35)]
        score_txt = None
        if key == 'Italy_A1_women':
            lg_ps = sum(v[4] for v in table.values()) / sum(v[2] + v[3] for v in table.values())
            h_ps = th[4] / (th[2] + th[3]); h_pa = th[5] / (th[2] + th[3])
            a_ps = ta[4] / (ta[2] + ta[3]); a_pa = ta[5] / (ta[2] + ta[3])
            set_total = h_ps * a_pa / lg_ps + a_ps * h_pa / lg_ps
            exp_pts = sum(v * (set_total * t if t < 5 else set_total * 4.62) for t, v in tot_sets.items())
            tline = math.floor(exp_pts) + 0.5
            pover = 1 - ncdf((tline - exp_pts) / 16.0)
            lines.append(line('Total Points', f"Over {tline:g}", tline, pover))
            score_txt = f"Modelled expected total rally points: {exp_pts:.0f}"
        exp_sets = sum(t * v for t, v in tot_sets.items())
        cap = 'low' if key.startswith('Poland') else 'medium'
        best = max(dist.items(), key=lambda kv: kv[1])
        wname = m['home'] if best[0][0] else m['away']
        base.update({'prob_home': round(p_home, 4), 'prob_draw': None, 'prob_away': round(1 - p_home, 4),
                     'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp, cap),
                     'expected_score': f"Most likely score: {wname} 3-{best[0][1]}; expected sets {exp_sets:.1f}" + (f"; {score_txt}" if score_txt else ''),
                     'lines': lines, 'status': 'modelled',
                     'inputs_summary': (f"Official set records: {m['home']} {th[2]}-{th[3]} sets ({th[0]} matches), {m['away']} {ta[2]}-{ta[3]} sets "
                                        f"({ta[0]} matches); shrunk set-win rates -> log5 set probability (home logit +0.12) -> race-to-3.")})
        matches.append(base)
    out('volleyball.json', {'sport': 'Volleyball', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- DARTS
def model_darts():
    d = load('darts.json')
    players = d['players']
    matches = []
    for m in d['matches']:
        a, b = players[m['p1']], players[m['p2']]
        p_leg1 = logistic(0.30 * (log(a['oom_money']) - log(b['oom_money'])))
        dist = race_score_dist(p_leg1, 6)
        p1w = sum(v for (w, _), v in dist.items() if w)
        fav1 = p1w >= 0.5
        fav = m['p1'] if fav1 else m['p2']
        fp = p1w if fav1 else 1 - p1w
        dmap, tmap = {}, {}
        for (w, ls), v in dist.items():
            margin = (6 - ls) if w else (ls - 6)
            dmap[margin] = dmap.get(margin, 0) + v
            tmap[6 + ls] = tmap.get(6 + ls, 0) + v
        hl, hcover = fair_half_line(dmap, fav1)
        tline, pover = fair_total_line(tmap)
        matches.append({
            'event_id': m['event_id'], 'sport': 'Darts', 'competition': m['competition'],
            'date': m.get('date_time'), 'venue': 'Westfalenhallen, Dortmund',
            'home': m['p1'], 'away': m['p2'],
            'prob_home': round(p1w, 4), 'prob_draw': None, 'prob_away': round(1 - p1w, 4),
            'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp),
            'expected_score': f"Modelled per-leg win probability: {m['p1']} {p_leg1*100:.0f}%; expected legs {sum(t*v for t,v in tmap.items()):.1f} (best of 11)",
            'lines': [line('Win Match', fav, None, fp),
                      line('Handicap (legs)', f"{fav} -{hl:g}", -hl, hcover),
                      line('Total Legs', f"Over {tline:g}", tline, pover)],
            'inputs_summary': (f"Official PDC Order of Merit (2-yr prize money): {m['p1']} world #{a['world_rank']} "
                               f"GBP {a['oom_money']:,} (EC seed {a['ec_seed']}); {m['p2']} world #{b['world_rank']} "
                               f"GBP {b['oom_money']:,} (EC seed {b['ec_seed']}). Leg prob via logistic on log-money (k=0.30)."),
            'form_context': m.get('form', ''),
            'source_url': m['source'], 'source_name': m['source_name'],
            'flags': list(m.get('flags', [])), 'status': 'modelled', 'prediction': None})
    out('darts.json', {'sport': 'Darts', 'matches': matches,
                       'outrights': norm_outrights(d.get('outrights'), 'model_pick', 'pick_basis')})
    return matches

# ---------------------------------------------------------------- SNOOKER
def model_snooker():
    d = load('snooker.json')
    matches = []
    for m in d['matches']:
        r1 = m['seeding'][m['p1']]; r2 = m['seeding'][m['p2']]
        better_is_1 = r1 < r2
        p_frame_better = logistic(0.40 * abs(log(max(r1, r2)) - log(min(r1, r2))))
        p_frame1 = p_frame_better if better_is_1 else 1 - p_frame_better
        dist = race_score_dist(p_frame1, 4)
        p1w = sum(v for (w, _), v in dist.items() if w)
        fav = m['p1'] if p1w >= 0.5 else m['p2']
        fp = max(p1w, 1 - p1w)
        dmap, tmap = {}, {}
        for (w, ls), v in dist.items():
            margin = (4 - ls) if w else (ls - 4)
            dmap[margin] = dmap.get(margin, 0) + v
            tmap[4 + ls] = tmap.get(4 + ls, 0) + v
        hl, hcover = fair_half_line(dmap, p1w >= 0.5)
        p_over55 = sum(v for t, v in tmap.items() if t > 5.5)
        scores = sorted(dist.items(), key=lambda kv: -kv[1])[:3]
        score_txt = '; '.join(f"{m['p1'] if w else m['p2']} 4-{ls} ({v*100:.0f}%)" for (w, ls), v in scores)
        matches.append({
            'event_id': m['event_id'], 'sport': 'Snooker',
            'competition': d['competition'].split(',')[0] + ' - Round 2 (best of 7)',
            'date': m['date'], 'venue': 'Waterfront Hall, Belfast',
            'home': m['p1'], 'away': m['p2'],
            'prob_home': round(p1w, 4), 'prob_draw': None, 'prob_away': round(1 - p1w, 4),
            'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp),
            'expected_score': f"Most likely correct scores: {score_txt}",
            'lines': [line('Win Match', fav, None, fp),
                      line('Handicap (frames)', f"{fav} -{hl:g}", -hl, hcover),
                      line('Total Frames', 'Over 5.5', 5.5, p_over55)],
            'inputs_summary': (f"Official tournament seedings (= WST world rankings at cut-off): {m['p1']} #{r1}, {m['p2']} #{r2}. "
                               f"Frame prob via logistic on log-rank gap (k=0.40), first to 4 frames."),
            'form_context': m.get('form_context', ''),
            'source_url': m['source_url'], 'source_name': 'WST (wst.tv) official match centre / rankings',
            'flags': [d['event_flag']] if d.get('event_flag') else [],
            'status': 'modelled', 'prediction': None})
    out('snooker.json', {'sport': 'Snooker', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- CRICKET
def model_cricket():
    d = load('cricket.json')
    matches = []
    for m in d['matches']:
        if 'icc_odi_rating' in m:
            ratings, divisor, home_adj = m['icc_odi_rating'], 18.0, 6.0
        elif 'icc_t20i_rating_women' in m:
            ratings, divisor, home_adj = m['icc_t20i_rating_women'], 30.0, 8.0
        else:
            ratings, divisor, home_adj = m['icc_t20i_rating'], 30.0, 8.0
        def _r(name):
            return ratings[name] if name in ratings else ratings[name.replace(' Women', '')]
        r1, r2 = _r(m['p1']), _r(m['p2'])
        adj = 0.0 if m.get('neutral_venue') else home_adj
        p1w = logistic((r1 - r2 + adj) / divisor)
        fav = m['p1'] if p1w >= 0.5 else m['p2']
        fp = max(p1w, 1 - p1w)
        matches.append({
            'event_id': m['event_id'], 'sport': 'Cricket', 'competition': m['competition'],
            'date': m['date'], 'venue': m['venue'], 'home': m['p1'], 'away': m['p2'],
            'prob_home': round(p1w, 4), 'prob_draw': None, 'prob_away': round(1 - p1w, 4),
            'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp),
            'expected_score': 'Win Match market only (no runs totals originated - see Methodology).',
            'lines': [line('Win Match', fav, None, fp)],
            'inputs_summary': (f"Official ICC ratings (Oct 2026): {m['p1']} {r1}, {m['p2']} {r2}"
                               + (f"; home adjustment +{home_adj:g} to {m['p1']}" if adj else '; neutral venue, no home adjustment')
                               + f"; logistic divisor {divisor:g}."),
            'form_context': m.get('form_context', ''),
            'source_url': m['source_url'], 'source_name': 'ICC / official board',
            'flags': [m['flag']] if m.get('flag') else [], 'status': 'modelled', 'prediction': None})
    for m in d['csa_pro20_cup']['matches']:
        matches.append({
            'event_id': m['event_id'], 'sport': 'Cricket',
            'competition': 'CSA Pro20 Cup 2026/2027 (South Africa domestic T20)',
            'date': m['date'], 'venue': m['venue'], 'home': m['p1'], 'away': m['p2'],
            'prob_home': None, 'prob_draw': None, 'prob_away': None,
            'pick': m['model_pick'], 'pick_probability': None, 'confidence': 'low',
            'expected_score': 'Not originated (no complete official standings).',
            'lines': [], 'inputs_summary': m['basis'], 'form_context': '',
            'source_url': m['source_url'], 'source_name': 'Cricket South Africa (official fixtures)',
            'flags': [m['flag']] if m.get('flag') else [], 'status': 'qualitative', 'prediction': None})
    out('cricket.json', {'sport': 'Cricket', 'matches': matches,
                         'outrights': norm_outrights(d.get('outrights'), 'pick', 'basis')})
    return matches

# ---------------------------------------------------------------- ICE HOCKEY
def hockey_lines(lh, la):
    jd = joint_dist(lh, la, 15)
    p_home_reg = sum(p for (h, a), p in jd.items() if h > a)
    p_tie = sum(p for (h, a), p in jd.items() if h == a)
    p_away_reg = sum(p for (h, a), p in jd.items() if h < a)
    share = lh / (lh + la)
    ot_home = 0.5 + 0.5 * (share - 0.5)
    p_home = p_home_reg + p_tie * ot_home
    p_away = p_away_reg + p_tie * (1 - ot_home)
    if lh >= la:
        puck = sum(p for (h, a), p in jd.items() if h - a >= 2)
    else:
        puck = sum(p for (h, a), p in jd.items() if a - h >= 2)
    tot = {}
    for (h, a), p in jd.items():
        t = h + a + (1 if h == a else 0)  # OT decider goal counts in total
        tot[t] = tot.get(t, 0) + p
    tline, pover = fair_total_line(tot)
    return p_home, p_away, puck, tline, pover

def model_ice_hockey():
    d = load('ice-hockey.json')
    leagues = d['leagues']
    nhl_avg = leagues['NHL']['league_avg_goals_per_team_game']
    ice = leagues['ICE_Hockey_League_(OLBG: Austria EHL)']
    shl = leagues['SHL']
    matches = []
    for m in d['matches']:
        if m['league'] == 'NHL':
            th = leagues['NHL']['teams'][m['home']]; ta = leagues['NHL']['teams'][m['away']]
            hg = (th['gp'], th['gf'], th['ga']); ag = (ta['gp'], ta['gf'], ta['ga'])
            lg, cap, comp = nhl_avg, 'high', 'NHL'
        elif m['league'].startswith('ICE'):
            tbl = ice['table_gp_w_l_otw_otl_gf_ga_pts']
            v = tbl[m['home']]; hg = (v[0], v[5], v[6])
            v = tbl[m['away']]; ag = (v[0], v[5], v[6])
            lg, cap, comp = ice['league_avg_goals_per_team_game'], 'high', 'ICE Hockey League (OLBG: "Austria EHL")'
        else:
            tbl = shl['table_gp_w_l_otw_otl_gf_ga_pts']
            v = tbl[m['home']]; hg = (v[0], v[5], v[6])
            v = tbl[m['away']]; ag = (v[0], v[5], v[6])
            lg, cap, comp = shl['league_avg_goals_per_team_game'], 'medium', 'Swedish Hockey League (SHL)'
        k = 5
        att_h = shrunk_rate(hg[1], hg[0], lg, k); def_h = shrunk_rate(hg[2], hg[0], lg, k)
        att_a = shrunk_rate(ag[1], ag[0], lg, k); def_a = shrunk_rate(ag[2], ag[0], lg, k)
        lh = att_h * def_a / lg * 1.045; la = att_a * def_h / lg / 1.045
        p_home, p_away, puck, tline, pover = hockey_lines(lh, la)
        fav = m['home'] if p_home >= 0.5 else m['away']
        fp = max(p_home, p_away)
        matches.append({
            'event_id': m['event_id'], 'sport': 'Ice Hockey', 'competition': comp,
            'date': m['date'], 'venue': m.get('venue'), 'home': m['home'], 'away': m['away'],
            'prob_home': round(p_home, 4), 'prob_draw': None, 'prob_away': round(p_away, 4),
            'pick': fav, 'pick_probability': round(fp, 4), 'confidence': confidence(fp, cap),
            'expected_score': f"Modelled expected goals: {m['home']} {lh:.2f} - {la:.2f} {m['away']}",
            'lines': [line('Money Line (incl. OT)', fav, None, fp),
                      line('Puck Line', f"{fav} -1.5", -1.5, puck),
                      line('Game Totals', f"Over {tline:g}", tline, pover)],
            'inputs_summary': (f"Official standings GF/GA: {m['home']} {hg[1]}:{hg[2]} in {hg[0]}g, {m['away']} {ag[1]}:{ag[2]} in {ag[0]}g; "
                               f"league avg {lg} goals/team/game; shrunk Poisson (k=5), home x1.045, OT split by lambda share."),
            'form_context': m.get('form_context', ''),
            'source_url': m['source_url'], 'source_name': 'League official standings',
            'flags': [m['flag']] if m.get('flag') else [], 'status': 'modelled', 'prediction': None})
    out('ice-hockey.json', {'sport': 'Ice Hockey', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- BASEBALL
def model_baseball():
    d = load('baseball.json')
    m = d['matches'][0]
    si = m['strength_inputs']
    A, B = si['tb_blended_winpct'], si['mil_blended_winpct']  # A=away TB, B=home MIL
    p_away = (A - A * B) / (A + B - 2 * A * B)  # log5
    p_away = logistic(log(p_away / (1 - p_away)) - 0.16)  # home-field shift to MIL
    p_home = 1 - p_away
    lg = d['league_avg_runs_per_team_game']
    tb = d['teams']['Tampa Bay Rays']; mil = d['teams']['Milwaukee Brewers']
    l_tb = (tb['runs_scored'] / 162) * (mil['runs_allowed'] / 162) / lg / 1.03
    l_mil = (mil['runs_scored'] / 162) * (tb['runs_allowed'] / 162) / lg * 1.03
    jd = joint_dist(l_mil, l_tb, 20)
    runline = sum(p for (h, a), p in jd.items() if h - a >= 2)
    _, tot = diff_total(jd)
    p_tie = sum(p for (h, a), p in jd.items() if h == a)
    tline, pover = fair_total_line(tot)
    matches = [{
        'event_id': m['event_id'], 'sport': 'Baseball', 'competition': m['competition'],
        'date': m['date'], 'venue': m['venue'], 'home': m['home'], 'away': m['away'],
        'prob_home': round(p_home, 4), 'prob_draw': None, 'prob_away': round(p_away, 4),
        'pick': m['home'], 'pick_probability': round(p_home, 4), 'confidence': confidence(p_home),
        'expected_score': f"Modelled expected runs: {m['away']} {l_tb:.1f} - {l_mil:.1f} {m['home']} (regulation model; extra innings not modelled for totals)",
        'lines': [line('Money Line', m['home'], None, p_home),
                  line('Run Line', f"{m['home']} -1.5", -1.5, runline),
                  line('Game Totals', f"Over {tline:g}", tline, pover)],
        'inputs_summary': (f"Official MLB 2026 regular season: TB 98-64 (736 RS, 650 RA), MIL 103-59 (832 RS, 618 RA); league avg {lg} "
                           f"runs/team/game. Money Line via blended actual/Pythagorean win% + log5 + home shift; Run Line/Totals via "
                           f"Poisson run model (regulation-tie probability {p_tie*100:.0f}% would go to extra innings)."),
        'form_context': m.get('form_context', ''),
        'source_url': m['source_url'], 'source_name': 'MLB Stats API (official)',
        'flags': [m['flag']] if m.get('flag') else [], 'status': 'modelled', 'prediction': None}]
    out('baseball.json', {'sport': 'Baseball', 'matches': matches, 'outrights': []})
    return matches

# ---------------------------------------------------------------- GAELIC FOOTBALL
def model_gaelic():
    d = load('gaelic-football.json')
    MARGINS = {3530: ("St Finbarr's", 0.5), 3532: ('Moycullen (Maigh Cuilinn)', 4.5),
               3531: ('Éire Óg', 1.0), 3536: ('Rathgormack', 3.0)}
    matches = []
    for m in d['matches']:
        team, em = MARGINS[m['event_id']]
        sd = 8.0
        p_win = 1 - ncdf((0.5 - em) / sd)
        p_draw = ncdf((0.5 - em) / sd) - ncdf((-0.5 - em) / sd)
        p_lose = ncdf((-0.5 - em) / sd)
        hcap = math.floor(em) + 0.5
        cover = 1 - ncdf((hcap - em) / sd)
        other = m['p2'] if team == m['p1'] else m['p1']
        prob_map = {team: p_win, other: p_lose}
        matches.append({
            'event_id': m['event_id'], 'sport': 'Gaelic Football', 'competition': m['competition'],
            'date': m['date'], 'venue': m['venue'], 'home': m['p1'], 'away': m['p2'],
            'prob_home': round(prob_map[m['p1']], 4), 'prob_draw': round(p_draw, 4),
            'prob_away': round(prob_map[m['p2']], 4),
            'pick': team, 'pick_probability': round(p_win, 4), 'confidence': confidence(p_win, 'medium'),
            'expected_score': f"Modelled margin: {team} by {em:g} pts (draw = level at full time)",
            'lines': [line('Match Winner (3-way)', team, None, p_win),
                      line('Match Winner (3-way)', 'Draw', None, p_draw),
                      line('Handicap', f"{team} -{hcap:g}", -hcap, cover)],
            'inputs_summary': f"Verified knockout margins + champion adjustment -> expected margin {em:g} pts; Normal margin model (SD 8). {m.get('expected_margin_input','')}",
            'form_context': m.get('context', ''),
            'source_url': m['source_url'], 'source_name': 'Official county board / Munster GAA / Galway GAA',
            'flags': [m['flag']] if m.get('flag') else [], 'status': 'modelled', 'prediction': None})
    out('gaelic-football.json', {'sport': 'Gaelic Football', 'matches': matches,
                                 'outrights': norm_outrights(d.get('outrights'), 'pick', 'basis')})
    return matches

# ---------------------------------------------------------------- GOLF
def model_golf():
    d = load('golf.json')
    probs = {}
    for key, ev in d['owgr_field_events'].items():
        ratings = [(name, sgwr * pp / (pp + 2.0)) for rank, name, sgwr, pp in ev['players']]
        mx = max(r for _, r in ratings)
        ws = [(n, exp((r - mx) / 0.6)) for n, r in ratings]
        s = sum(w for _, w in ws)
        probs[key] = {n: w / s for n, w in ws}
    outrights = []
    for o in d['outrights']:
        oo = dict(o)
        if o.get('rating_key') and o['rating_key'] in probs:
            pr = probs[o['rating_key']]
            top = max(pr.items(), key=lambda kv: kv[1])
            # Published pick follows the rating model (top-rated in extracted field).
            oo['model_pick'] = top[0]
            oo['_model_probability'] = round(top[1], 4)
            note = '' if top[0] == o['model_pick'] else (
                f" (The verified file's Order-of-Merit-based nomination was {o['model_pick']}, "
                f"rated {pr.get(o['model_pick'], 0.0)*100:.1f}% by the same model; the published pick "
                f"follows the model's top-rated player for consistency.)")
            oo['pick_basis'] = oo.get('pick_basis', '') + (
                f" Model (Performance-Points-shrunk SGWR, softmax sigma=0.6 over {len(pr)} extracted contenders): "
                f"{top[0]} {top[1]*100:.1f}% (top-rated). "
                f"Probabilities conditional on the winner coming from the extracted contender set.{note}")
        outrights.append(oo)
    out('golf.json', {'sport': 'Golf', 'matches': [],
                      'outrights': norm_outrights(outrights, 'model_pick', 'pick_basis')})
    return []

# ---------------------------------------------------------------- MOTOR / RL / ZEROS / GREYHOUNDS
def model_simple_outrights():
    collected = []
    d = load('motor-racing.json')
    motor = []
    for e in d.get('events', []):
        motor.append({
            'event_id': e['event_id'], 'sport': 'Motor Racing', 'competition': e['competition'],
            'date': e['date'], 'venue': e['venue'], 'home': 'Race winner (22-car field)', 'away': None,
            'prob_home': None, 'prob_draw': None, 'prob_away': None,
            'pick': e['pick'], 'pick_probability': None, 'confidence': 'low',
            'expected_score': 'No precise probability originated for a 22-car field.',
            'lines': [line('Win Race', e['pick'], None, None)],
            'inputs_summary': e['basis'], 'form_context': d.get('race_winners_2026_visible', ''),
            'source_url': e['source_url'], 'source_name': 'Formula1.com official results',
            'flags': [], 'status': 'qualitative', 'prediction': None})
    out('motor-racing.json', {'sport': 'Motor Racing', 'matches': motor,
                              'outrights': norm_outrights(d.get('outrights'), 'pick', 'basis')})
    collected += motor
    d = load('rugby-league.json')
    out('rugby-league.json', {'sport': 'Rugby League', 'matches': [],
                              'outrights': norm_outrights(d.get('outrights'), 'pick', 'basis'),
                              'zero_event_check': d.get('zero_event_cross_check')})
    for f, name in [('aussie-rules.json', 'Aussie Rules'), ('esports.json', 'eSports')]:
        dd = load(f)
        out(f, {'sport': name, 'matches': [], 'outrights': [],
                'zero_event_check': dd.get('zero_event_cross_check')})
    d = load('greyhounds.json')
    greys = []
    for e in d['events']:
        greys.append({
            'event_id': e['event_id'], 'sport': 'Greyhounds',
            'competition': f"GBGB graded race - {e['race']}",
            'date': e['date'], 'venue': e['race'].split(' ', 1)[1] if ' ' in e['race'] else None,
            'home': e['race'], 'away': None, 'prob_home': None, 'prob_draw': None, 'prob_away': None,
            'pick': None, 'pick_probability': None, 'confidence': 'low',
            'expected_score': 'No line originated - see Flagged for Review.',
            'lines': [], 'inputs_summary': d['explanation'], 'form_context': '',
            'source_url': e['source_url'], 'source_name': 'GBGB (governing body)',
            'flags': [e['flag']], 'status': 'flagged', 'prediction': None})
    out('greyhounds.json', {'sport': 'Greyhounds', 'matches': greys, 'outrights': []})
    collected += greys
    return collected

# ---------------------------------------------------------------- main
if __name__ == '__main__':
    all_matches = []
    for fn in [model_tennis, model_basketball, model_handball, model_rugby_union,
               model_volleyball, model_darts, model_snooker, model_cricket,
               model_ice_hockey, model_baseball, model_gaelic, model_golf,
               model_simple_outrights]:
        ms = fn()
        all_matches += ms
        print(f"{fn.__name__:26s} {len(ms):3d} matches")
    pred_path = os.path.join(ROOT, 'tools', 'predictions.json')
    if os.path.exists(pred_path):
        preds = json.load(open(pred_path))
        import glob as _glob
        for fp in _glob.glob(os.path.join(OD, '*.json')):
            payload = json.load(open(fp))
            changed = False
            for mm in payload.get('matches', []):
                if str(mm['event_id']) in preds:
                    mm['prediction'] = preds[str(mm['event_id'])]
                    changed = True
            if changed:
                json.dump(payload, open(fp, 'w'), indent=1, ensure_ascii=False)
        for mm in all_matches:
            if str(mm['event_id']) in preds:
                mm['prediction'] = preds[str(mm['event_id'])]
        print(f"attached {len(preds)} predictions")
    from collections import Counter
    print('total matches:', len(all_matches))
    print(Counter(m['confidence'] for m in all_matches))
    print(Counter(m['status'] for m in all_matches))
    print('\nHIGH-CONFIDENCE (need written predictions):')
    for m in all_matches:
        if m['confidence'] == 'high':
            mark = 'OK  ' if m.get('prediction') else 'NEED'
            print(f"  {mark} [{m['sport']}] {m['home']} vs {m['away']} -> {m['pick']} ({(m['pick_probability'] or 0)*100:.1f}%) ev={m['event_id']}")
    if UNMATCHED:
        print('\nUNMATCHED LOOKUPS:', sorted(set(UNMATCHED)))

#!/usr/bin/env python3
"""Regenerate each prediction's evidence bullets directly from lines.json.

Hand-typing a record is the easiest way to publish a wrong number, so the fact
lists are generated: every figure below is copied from the same verified inputs
the model used. Prose is written by the session; facts are not.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
rows = {r['id']: r for r in json.load(open(os.path.join(HERE, 'lines.json')))['rows']}
pp = os.path.join(HERE, 'predictions.json')
doc = json.load(open(pp))


def pl(n, one, many=None):
    return f'{n} {one if n == 1 else (many or one + "s")}'


for rid, p in doc['predictions'].items():
    r = rows[rid]
    i = r['model']['inputs']
    h, a = i['home'], i['away']
    p['facts'] = [
        f"{r['home']}: {h['w']}-{h['l']}-{h['otl']} record, {h['pts']} points, "
        f"{h['gf']} goals for, {h['ga']} goals against",
        f"{r['home']} last ten: {pl(h['l10_w'], 'win')}, {pl(h['l10_l'], 'loss', 'losses')}, "
        f"{pl(h['l10_otl'], 'overtime loss', 'overtime losses')}; streak {h['streak']}",
        f"{r['away']}: {a['w']}-{a['l']}-{a['otl']} record, {a['pts']} points, "
        f"{a['gf']} goals for, {a['ga']} goals against",
    ]

json.dump(doc, open(pp, 'w'), indent=1)
print('facts regenerated for', len(doc['predictions']), 'predictions')

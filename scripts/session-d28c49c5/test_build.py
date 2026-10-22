import hashlib
import importlib.util
import json
import math
import pathlib
import sys
import unittest
from html.parser import HTMLParser
from urllib.parse import unquote, urlsplit
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import build
import model

class Links(HTMLParser):
 def __init__(self): super().__init__(); self.targets=[]
 def handle_starttag(self,tag,attrs):
  self.targets += [v for k,v in attrs if k in ('href','src')]

class Verification(unittest.TestCase):
 def setUp(self): self.manifest,self.payload=build.load_evidence()
 def test_capture_integrity(self):
  self.assertEqual(len(self.manifest),4)
  for m in self.manifest:
   self.assertEqual(m['status'],200)
   raw=(build.DATA/m['file']).read_bytes()
   self.assertEqual(len(raw),m['bytes'])
   self.assertEqual(hashlib.sha256(raw).hexdigest(),m['sha256'])
 def test_fixture_fields_exactly_from_response(self):
  rows=build.fixtures(self.manifest,self.payload)
  self.assertEqual(len({r['id'] for r in rows}),len(rows))
  for r in rows:
   if r['id'].startswith('nhl-'):
    g=next(g for day in self.payload['nhl_schedule']['gameWeek'] for g in day['games'] if 'nhl-'+str(g['id'])==r['id'])
    self.assertEqual(r['start_utc'],g['startTimeUTC'])
    self.assertEqual(r['venue'],g['venue']['default'])
    self.assertEqual(r['side_a'],g['awayTeam']['placeName']['default']+' '+g['awayTeam']['commonName']['default'])
   else:
    g=next(g for day in self.payload['mlb_schedule']['dates'] for g in day['games'] if 'mlb-'+str(g['gamePk'])==r['id'])
    self.assertEqual(r['side_a'],g['teams']['away']['team']['name'])
    self.assertEqual(r['side_b'],g['teams']['home']['team']['name'])
    self.assertEqual(r['start_utc'],g['gameDate'])
   for key in ['pick','confidence','fair_odds','prediction']: self.assertEqual(r[key],'')
 def test_model(self):
  self.assertEqual(model.american(.5),-100)
  self.assertEqual(model.american(5/7),-250)
  self.assertEqual(model.american(1/101),10000)
  for p in [0,1,-.1]:
   with self.assertRaises(ValueError): model.american(p)
  self.assertAlmostEqual(sum(model.poisson(3)),1)
  lines=model.originate(build.fixtures(self.manifest,self.payload),self.payload['nhl_standings'])
  self.assertGreater(len(lines),0)
  for r in lines:
   self.assertAlmostEqual(r['p_a']+r['p_b'],1)
   self.assertAlmostEqual(r['fair_decimal_a']*r['p_a'],1)
   self.assertEqual(r['confidence'],'Low')
 def test_no_inherited_verification_or_picks(self):
  review=build.audit(build.fixtures(self.manifest,self.payload))
  peer=json.loads(build.PEER.read_text())['rows']
  self.assertEqual([r['id'] for r in review],[r['id'] for r in peer])
  for r in review:
   self.assertEqual(r['confirmed_pick'],'')
   self.assertEqual(r['confirmed_confidence'],'')
   if r['prior_confidence']=='High' and r['prior_selection_implied_probability']<.7:
    self.assertTrue(any('below 70%' in i for i in r['issues']))
 def test_rebuild_and_links(self):
  before={p:p.read_bytes() for p in build.OUT.glob('*.html')}
  build.main()
  for p,b in before.items(): self.assertEqual(p.read_bytes(),b)
  for p in build.OUT.glob('*.html'):
   parser=Links(); parser.feed(p.read_text())
   for target in parser.targets:
    url=urlsplit(target)
    if url.scheme or url.netloc: continue
    self.assertTrue((p.parent/unquote(url.path)).exists(),f'{p}: {target}')
 def test_html_escapes(self): self.assertEqual(build.esc('<script>'),'&lt;script&gt;')

if __name__=='__main__': unittest.main(verbosity=2)

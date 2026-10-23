"""Network-free adversarial, provenance, arithmetic and publication regression tests."""
import gzip
import hashlib
import json
import math
import tempfile
import unittest
from datetime import datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit,unquote
from unittest.mock import patch
from core import Evidence,DATA,ROOT,SPORTS,price,in_window,log5,instant,parse_tips,balanced,norm
from parsers import parse_official,reconcile
from build import make_desk,validate,Site,OUT
from review import official

class PrimitiveTests(unittest.TestCase):
    def test_american_probability_roundtrip(self):
        for p in (.01,.07,.3,.5,.7,.8,.99):
            row=price(p);a=row['american']
            recovered=(-a)/(100-a) if a<0 else 100/(a+100)
            self.assertAlmostEqual(p,recovered,places=13)
            self.assertAlmostEqual(p*row['decimal'],1)
    def test_no_clamping_and_odds_window(self):
        self.assertTrue(in_window(.7))
        self.assertFalse(in_window(.72))
        self.assertEqual(price(.5)['decimal'],2)
        self.assertAlmostEqual(price(.7)['american'],-233.3333333333333)
        self.assertTrue(price(.95)['american'] < -250)
    def test_invalid_probability_rejected(self):
        for x in (0,1,-.1,1.1,float('nan'),float('inf')):
            with self.assertRaises(ValueError):price(x)
    def test_log5_symmetry_and_equal_strength(self):
        self.assertAlmostEqual(log5(8,12,8,12),.5)
        self.assertAlmostEqual(log5(9,12,4,11)+log5(4,11,9,12),1)
    def test_invalid_records_do_not_become_prices(self):
        for args in [(1,0,1,2),(5,4,2,3),(True,4,2,3),(1.1,4,2,3)]:
            with self.assertRaises(ValueError):log5(*args)
    def test_timezone_is_required(self):
        self.assertIsNone(instant('2026-10-24'))
        self.assertIsNone(instant('2026-10-24T12:00:00'))
        self.assertEqual(instant('2026-10-24T10:30+09:00').hour,1)
    def test_official_domain_boundary(self):
        self.assertTrue(official('https://api-web.nhle.com/v1/schedule/2026-10-23'))
        for u in ['https://nhle.com.attacker.example/a','https://evilnhle.com/a','https://user@www.nhl.com/a','http://www.nhl.com/a','https://www.olbg.com/']:
            self.assertFalse(official(u))
    def test_js_payload_escaping_and_boundary(self):
        tip='{id:"'+'a'*40+'",selection:"Player \\"Q\\"",event_name_alias:"A } vs B ]",eventUrl:"/event?event_id=1",expired:"0"}'
        text='tips:['+tip+']; unrelated:['+tip+'];'
        rows=parse_tips(text)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['selection'],'Player "Q"')
        self.assertEqual(rows[0]['event_name_alias'],'A } vs B ]')
    def test_truncated_js_fails_closed(self):
        with self.assertRaises(ValueError):parse_tips('tips:[{id:"'+'a'*40+'",selection:"unfinished')
    def test_markup_like_names_are_not_executed(self):
        from build import esc,link
        self.assertNotIn('<script>',esc('<script>bad</script>'))
        with self.assertRaises(ValueError):link('javascript:alert(1)')
    def test_time_mismatch_never_matches(self):
        r=dict(id='r',sport='Baseball',start_utc='2026-10-24T00:00:00Z',aliases=[['Rays'],['Brewers']],olbg_ids=[])
        l=dict(id='l',sport='Baseball',listed_name='TB Rays @ MIL Brewers',listed_start='2026-10-24T00:01:00Z',active=True,official_id=None)
        reconcile([l],[r]);self.assertIsNone(l['official_id'])
    def test_ambiguous_identity_rejected(self):
        r=dict(id='r',sport='Baseball',start_utc='2026-10-24T00:00:00Z',aliases=[['Rays'],['Brewers']],olbg_ids=[])
        l=dict(id='l',sport='Baseball',listed_name='TB Rays @ MIL Brewers',listed_start=r['start_utc'],active=True,official_id=None)
        reconcile([l],[r,dict(r,id='other')]);self.assertIsNone(l['official_id'])
    def test_exact_match_and_expired_rules(self):
        r=dict(id='r',sport='Baseball',start_utc='2026-10-24T00:00:00Z',aliases=[['Rays'],['Brewers']],olbg_ids=[])
        l=dict(id='l',sport='Baseball',listed_name='TB Rays @ MIL Brewers',listed_start=r['start_utc'],active=False,official_id=None)
        reconcile([l],[r]);self.assertIsNone(l['official_id'])
        l['active']=True;reconcile([l],[r]);self.assertEqual(l['official_id'],'r')
    def test_tampered_capture_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);raw=b'{"x":1}'
            (p/'a.gz').write_bytes(gzip.compress(raw))
            (p/'manifest.json').write_text(json.dumps(dict(finished_at='2026-10-23T12:00:00Z',records=[dict(id='a',file='a.gz',sha256='0'*64,bytes=len(raw))])))
            with self.assertRaisesRegex(ValueError,'tampering'):Evidence(p)

class PageParser(HTMLParser):
    def __init__(self):super().__init__();self.links=[];self.ids=set();self.main=False
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if attrs.get('id'):self.ids.add(attrs['id'])
        if tag=='main':self.main=True
        for k in ('href','src'):
            if attrs.get(k):self.links.append(attrs[k])

class PublishedEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e=Evidence();cls.d=make_desk(cls.e)
    def test_all_adopted_values_equal_capture_at_pointer(self):
        validate(self.e,self.d)
        self.assertGreater(len(self.d['rows']),0)
        for r in self.d['rows']:
            self.assertTrue(official(r['official_url']))
            for f in r['facts']:
                self.assertEqual(self.e.fact_value(f),f['value'])
                self.assertEqual(f['sha256'],self.e.records[f['target']]['sha256'])
    def test_no_injuries_or_predictions_invented(self):
        self.assertEqual(self.d['high_predictions'],[])
        for r in self.d['rows']:
            self.assertIsNone(r['injuries'])
            self.assertEqual(r['prediction'],'')
            self.assertIn(r['confidence'],('','low'))
    def test_exact_fifteen_sport_scope(self):
        self.assertEqual(len(SPORTS),15)
        self.assertEqual(set(self.d['sports']),set(SPORTS))
        self.assertTrue(all(r['sport'] in SPORTS for r in self.d['rows']))
    def test_invalid_or_conditional_rows_not_priced(self):
        for r in self.d['rows']:
            if r['conditional'] or any('Contradictory' in f for f in r['flags']):
                self.assertEqual(r['markets'],[])
                self.assertIsNone(r['pick'])
    def test_price_recomputation_from_official_records(self):
        for r in self.d['rows']:
            if not r['pick']:continue
            facts={f['label']:f['value'] for f in r['facts']}
            if 'record_inputs' in r:
                v=r['record_inputs'];a,b,c,d=[v[k] for k in ['away_wins','away_games','home_wins','home_games']]
            else:a,b,c,d=[facts[k] for k in ['Away season wins','Away season games played','Home season wins','Home season games played']]
            p=log5(a,b,c,d)
            self.assertAlmostEqual(p,r['markets'][0]['selections'][0]['probability'])
    def test_regulation_scoring_misalignment_never_becomes_line(self):
        for r in self.d['rows']:
            if r['competition']=='NHL':
                self.assertTrue(all('winner' in m['name'].lower() for m in r['markets']))
    def test_legacy_facts_are_blank_not_inherited(self):
        for r in self.d['review']['rows']:
            self.assertEqual(r['confirmed_values'],{})
            self.assertEqual(r['status'],'unverified')
    def test_site_local_files_and_fragments(self):
        parsed={}
        for p in OUT.glob('*.html'):
            parser=PageParser();parser.feed(p.read_text());parsed[p.resolve()]=parser
            self.assertTrue(parser.main)
        self.assertEqual(len(parsed),24)
        for p,parser in parsed.items():
            for u in parser.links:
                url=urlsplit(u)
                if url.scheme or url.netloc:continue
                target=(p.parent/unquote(url.path)).resolve() if url.path else p
                if target.is_dir():target/='index.html'
                self.assertTrue(target.is_relative_to(ROOT),u)
                self.assertTrue(target.exists(),f'{p.name}: {u}')
                if url.fragment and target in parsed:
                    self.assertIn(unquote(url.fragment),parsed[target].ids,f'{p.name}: {u}')
    def test_deterministic_regeneration(self):
        before={p.name:p.read_bytes() for p in OUT.glob('*.html')}
        Site(self.e,self.d).build()
        self.assertEqual(before,{p.name:p.read_bytes() for p in OUT.glob('*.html')})
    def test_each_sport_has_a_gap_or_confirmed_register(self):
        for sport in SPORTS:
            self.assertTrue(any(f['sport']==sport and 'Five High' in f['subject'] for f in self.d['flags']))
            self.assertTrue((OUT/(sport.lower().replace(' ','-')+'.html')).exists())

if __name__=='__main__':unittest.main()

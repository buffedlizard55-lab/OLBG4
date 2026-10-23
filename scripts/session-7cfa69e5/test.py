"""Offline publication gates; never confuse these with factual source validation."""
import gzip,hashlib,json,math,pathlib,subprocess,sys,unittest
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=pathlib.Path(__file__).resolve().parents[2]; D=ROOT/'data/session-7cfa69e5';O=ROOT/'session-7cfa69e5'
def load(p):return json.loads(p.read_text())
class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for k,v in attrs:
            if k in ('href','src') and v:self.links.append(v)
class Publication(unittest.TestCase):
    def test_capture_hashes(self):
        for r in load(D/'capture/manifest.json')['records']:
            if r.get('file'):
                b=gzip.decompress((D/'capture'/r['file']).read_bytes())
                self.assertEqual(hashlib.sha256(b).hexdigest(),r['sha256']);self.assertEqual(len(b),r['bytes'])
    def test_robots_evidence_hashes(self):
        for r in load(D/'capture/manifest.json')['records']:
            if r.get('robots_file'):
                raw=gzip.decompress((D/'capture'/r['robots_file']).read_bytes())
                self.assertEqual(hashlib.sha256(raw).hexdigest(),r['robots_sha256'])

    def test_every_fixture_field_against_capture(self):
        def raw(id):
            return json.loads(gzip.decompress((D/'capture'/(id+'.gz')).read_bytes()))
        expected={}
        for day in raw('nhl_sched_2026_10_23')['gameWeek']:
            for g in day['games']:
                def name(t):return t['placeName']['default']+' '+t['commonName']['default']
                expected[str(g['id'])]=(name(g['awayTeam']),name(g['homeTeam']),g['startTimeUTC'],g.get('venue',{}).get('default',''))
        for day in raw('mlb_ws_schedule')['dates']:
            for g in day['games']:
                expected[str(g['gamePk'])]=(g['teams']['away']['team']['name'],g['teams']['home']['team']['name'],g['gameDate'],g.get('venue',{}).get('name',''))
        for id in ['euroleague_games_E2026','eurocup_games_U2026']:
            for g in raw(id)['data']:
                expected[g['identifier']]=(g['road']['club']['name'],g['local']['club']['name'],g['utcDate'],(g.get('venue') or {}).get('name',''))
        for g in raw('liiga_games_2027'):
            expected['liiga_'+str(g['id'])]=(g['awayTeam']['teamName'],g['homeTeam']['teamName'],g['start'],'')
        for r in load(D/'desk.json')['rows']:
            self.assertEqual((r['away'],r['home'],r['start_utc'],r['venue']),expected[r['id']])

    def test_no_missing_local_links(self):
        for p in O.glob('*.html'):
            parser=Links();parser.feed(p.read_text())
            for u in parser.links:
                parsed=urlsplit(u)
                if parsed.scheme or parsed.netloc or not parsed.path:continue
                self.assertTrue((p.parent/unquote(parsed.path)).exists(),f'{p}: {u}')
    def test_all_15_sports(self):
        d=load(D/'desk.json');self.assertEqual(len(d['scope']),15)
        for s in d['scope']:self.assertTrue((O/(s.lower().replace(' ','-')+'.html')).exists())
    def test_unique_fixtures_and_sources(self):
        rr=load(D/'desk.json')['rows'];self.assertEqual(len({r['id'] for r in rr}),len(rr))
        for r in rr:
            self.assertTrue(r['source'].startswith('https://'));self.assertIsNone(r['olbg_event'])
            self.assertIn(r['confidence'],[None,'Low'])
    def test_estimates(self):
        d=load(D/'desk.json');groups={}
        for m in d['markets']:
            p=m['probability'];self.assertTrue(0<p<1)
            self.assertAlmostEqual(m['fair_decimal'],1/p,places=3)
            a=round(-100*p/(1-p)) if p>=.5 else round(100*(1-p)/p)
            self.assertEqual(a,m['fair_american']);self.assertEqual(m['confidence'],'Low')
            groups.setdefault(m['event_id'],[]).append(m)
        for id,mm in groups.items():
            self.assertEqual(len(mm),7)
            for selections in [mm[:3],mm[3:5],mm[5:7]]:self.assertAlmostEqual(sum(m['probability'] for m in selections),1,places=6)
        self.assertEqual(d['high_predictions'],[])
    def test_every_peer_row_audited(self):
        peer=load(ROOT/'data/session-b2c7308d/desk.json')['rows'];rr=load(D/'review.json')
        self.assertEqual({r['peer_id'] for r in rr},{r['id'] for r in peer})
        for r in rr:self.assertTrue(r['source'].startswith('https://'))
    def test_flags_sources_and_shortfalls(self):
        flags=load(D/'flagged.json')
        for f in flags:self.assertTrue(f['source'].startswith('https://'))
        self.assertEqual(sum(f['title']=='Coverage and prediction shortfall' for f in flags),15)
    def test_rebuild_is_deterministic(self):
        paths=list(O.glob('*'))+[D/'desk.json',D/'review.json',D/'flagged.json']
        before={p:p.read_bytes() for p in paths if p.is_file()}
        subprocess.run([sys.executable,str(ROOT/'scripts/session-7cfa69e5/build.py')],check=True,stdout=subprocess.PIPE)
        self.assertEqual(before,{p:p.read_bytes() for p in before})
if __name__=='__main__':unittest.main(verbosity=2)

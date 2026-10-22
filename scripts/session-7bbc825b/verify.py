"""Structural checks only: deliberately not an official-source factual verification."""
import hashlib,json,unittest
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
ROOT=Path(__file__).resolve().parents[2]
class Links(HTMLParser):
 def __init__(self): super().__init__();self.links=[]
 def handle_starttag(self,tag,attrs):
  for k,v in attrs:
   if k in ('href','src'):self.links.append(v)
class ReviewTests(unittest.TestCase):
 def test_rows(self):
  d=json.loads((ROOT/'data/session-7bbc825b/review.json').read_text())
  self.assertEqual(len(d['rows']),sum(f['rows'] for f in d['files']))
  self.assertEqual(len(d['rows']),len({r['audit_id'] for r in d['rows']}))
  for r in d['rows']:
   self.assertEqual(r['status'],'unverified')
   for k in ('verified_match','verified_start_utc','winner_pick','confidence','originated_lines','prediction'):self.assertEqual(r[k],'')
   p=json.loads((ROOT/r['file']).read_text()); i=int(r['pointer'].split('/')[-1]);self.assertEqual(r['legacy_id'],p['rows'][i].get('id',''))
  for f in d['files']:self.assertEqual(f['sha256'],hashlib.sha256((ROOT/f['path']).read_bytes()).hexdigest())
 def test_links(self):
  for p in (ROOT/'session-7bbc825b').glob('*.html'):
   parser=Links();parser.feed(p.read_text())
   for link in parser.links:
    u=urlsplit(link)
    if not u.scheme and u.path:self.assertTrue((p.parent/unquote(u.path)).exists(),f'{p}: {link}')
if __name__=='__main__': unittest.main()

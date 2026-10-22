"""Capture exact official responses. No invented fallback data."""
import datetime, hashlib, json, pathlib, urllib.request
ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT/'data/session-d28c49c5'
SOURCES = {
 'nhl_schedule': 'https://api-web.nhle.com/v1/schedule/2026-10-22',
 'nhl_standings': 'https://api-web.nhle.com/v1/standings/2026-10-22',
 'mlb_schedule': 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-22&endDate=2026-11-05&hydrate=team',
 'olbg': 'https://www.olbg.com/betting-tips',
}
def main():
 OUT.mkdir(parents=True, exist_ok=True)
 manifest=[]
 for key,url in SOURCES.items():
  row={'id':key,'url':url,'retrieved_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'OLBG4-evidence-audit/1.0'})
   with urllib.request.urlopen(req,timeout=40) as res:
    body=res.read(8_000_001)
    if len(body)>8_000_000: raise ValueError('Response exceeds capture limit')
    row.update(status=res.status,final_url=res.url,content_type=res.headers.get('Content-Type',''))
   filename=key+'.raw'
   (OUT/filename).write_bytes(body)
   row.update(file=filename,sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
  except Exception as exc: row.update(status='unavailable',error=str(exc))
  manifest.append(row)
 (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
if __name__=='__main__': main()

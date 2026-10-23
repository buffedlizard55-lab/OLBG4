"""Byte-for-byte public HTTPS read-back. Run on an open-egress Actions runner.
No successful deployment claim is made merely from a Pages build status.
"""
import hashlib
import time
import urllib.request
from pathlib import Path
from core import ROOT

BASE='https://buffedlizard55-lab.github.io/OLBG4/'

def main():
    paths=['session-49866065/'+p.name for p in sorted((ROOT/'session-49866065').glob('*.html'))]
    paths+=['session-49866065/style.css','session-49866065/app.js','data/session-49866065/capture/manifest.json']
    checks=[]
    for path in paths:
        expected=(ROOT/path).read_bytes()
        with urllib.request.urlopen(BASE+path,timeout=30) as response:
            actual=response.read()
            if response.status!=200:raise AssertionError((path,response.status))
        if actual!=expected:raise AssertionError('Public bytes differ: '+path)
        checks.append(path)
        print('HTTP 200 / exact SHA-256',hashlib.sha256(actual).hexdigest(),path,flush=True)
        time.sleep(.15)
    with urllib.request.urlopen(BASE,timeout=30) as response:
        root=response.read().decode('utf-8')
        assert response.status==200 and 'session-49866065/index.html' in root
    print('PASS:',len(checks),'exact public files plus root dashboard pointer')

if __name__=='__main__':
    for attempt in range(12):
        try:
            main();break
        except (OSError,AssertionError) as ex:
            if attempt==11:raise
            print('Public build not ready yet:',ex,flush=True)
            time.sleep(20)

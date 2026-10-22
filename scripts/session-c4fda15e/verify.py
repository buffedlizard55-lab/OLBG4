#!/usr/bin/env python3
"""Board Y (session c4fda15e) - publication gate. Exit 1 on any error."""
from __future__ import annotations

import gzip
import hashlib
import json
import os
import re
import sys
from urllib.parse import urlsplit, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-c4fda15e")
SITE = os.path.join(ROOT, "session-c4fda15e")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import model as M  # noqa: E402

OFFICIAL = ("atptour.com", "protennislive.com", "wtatennis.com", "pdc.tv", "pdcservices.co.uk", "nba.com", "euroleaguebasketball.net",
            "euroleague.net", "lnr.fr", "unitedrugby.com", "mlb.com", "liiga.fi")
errors, notes = [], []
desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
WR = json.load(open(os.path.join(DATA, "writeups.json"), encoding="utf-8"))["writeups"]


def official_url(u):
    h = (urlsplit(u or "").hostname or "").lower()
    return any(h == d or h.endswith("." + d) for d in OFFICIAL)


# 1. rows
for r in desk["rows"] + desk["official_only"]:
    v = r["verification"]
    if v.startswith("verified") or v == "partially verified":
        if not r.get("official") or not official_url(r["official"].get("url")):
            errors.append(f"{r['event_name']}: verified without an official URL")
    elif v == "unverified":
        if r.get("official") or not r.get("flags"):
            errors.append(f"{r['event_name']}: unverified row must have blank official fields and a flag")
    if r.get("pick") and not r.get("line"):
        errors.append(f"{r['event_name']}: pick without line")
    if r.get("line") and not official_url(r["line"].get("inputs_url")):
        errors.append(f"{r['event_name']}: line inputs not from an official URL ({r['line'].get('inputs_url')})")

# 2. High picks
highs = [r for r in desk["rows"] if (r.get("pick") or {}).get("confidence") == "High"]
texts = []
for r in highs:
    pk = r["pick"]
    w = WR.get(str(r["event_id"]))
    if r["verification"] != "verified":
        errors.append(f"High {r['event_name']}: fixture not verified")
    if not M.in_window(pk["fair_american"]):
        errors.append(f"High {r['event_name']}: fair price {pk['fair_american']} outside -250..+10000")
    if pk["market_reference"] is not None and not M.in_window(pk["market_reference"]):
        errors.append(f"High {r['event_name']}: market price outside window")
    if not w:
        errors.append(f"High {r['event_name']}: missing write-up")
        continue
    words = len(w["text"].split())
    if words < 30:
        errors.append(f"High {r['event_name']}: write-up {words} words (<30)")
    if pk["selection"].split()[-1] not in w["text"]:
        errors.append(f"High {r['event_name']}: write-up does not name the selection")
    if not w.get("facts") or not all(official_url(u) for _, u in w["facts"]):
        errors.append(f"High {r['event_name']}: write-up facts must all link to official domains")
    texts.append((r["event_name"], w["text"]))
for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        a = set(re.findall(r"[a-z']+", texts[i][1].lower()))
        b = set(re.findall(r"[a-z']+", texts[j][1].lower()))
        jac = len(a & b) / len(a | b)
        if jac > 0.45:
            errors.append(f"write-ups too similar ({jac:.2f}): {texts[i][0]} / {texts[j][0]}")
sent = {}
for name, t in texts:
    for s in re.split(r"(?<=[.!?])\s+", t):
        s2 = s.strip().lower()
        if len(s2) > 25:
            if s2 in sent:
                errors.append(f"repeated sentence in {name} and {sent[s2]}")
            sent[s2] = name

# 3. capture integrity
ncap = 0
for stamp in sorted(os.listdir(os.path.join(DATA, "capture"))):
    mp = os.path.join(DATA, "capture", stamp, "manifest.json")
    if not os.path.exists(mp):
        continue
    for it in json.load(open(mp, encoding="utf-8"))["items"]:
        if not it.get("file"):
            continue
        b = gzip.open(os.path.join(DATA, "capture", stamp, it["file"])).read()
        ncap += 1
        if hashlib.sha256(b).hexdigest() != it["sha256"]:
            errors.append(f"sha256 mismatch {stamp}/{it['file']}")

# 4/5. site links + no OLBG tip data
nlink = 0
for f in sorted(os.listdir(SITE)):
    if not f.endswith(".html"):
        continue
    s = open(os.path.join(SITE, f), encoding="utf-8").read()
    if re.search(r"\bWin Tips\b|\d+/\d+ Win Tips|win_tips", s):
        errors.append(f"{f}: OLBG tip counts reproduced")
    for m in re.finditer(r'(?:href|src)="([^"]+)"', s):
        p = urlsplit(m.group(1))
        if p.scheme or p.netloc or not p.path:
            continue
        t = os.path.normpath(os.path.join(SITE, unquote(p.path)))
        if os.path.isdir(t):
            t = os.path.join(t, "index.html")
        nlink += 1
        if not os.path.isfile(t):
            errors.append(f"{f}: broken local link {m.group(1)}")

print(json.dumps({"rows": len(desk["rows"]), "official_only": len(desk["official_only"]), "high": len(highs), "captures_hashed": ncap,
                  "local_links": nlink, "errors": errors}, indent=1))
sys.exit(1 if errors else 0)

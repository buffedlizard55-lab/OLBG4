#!/usr/bin/env python3
"""Gate for Board K. Exits non-zero on any broken rule; CI-friendly."""
import json, os, re, sys, collections, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
fail, warn = [], []
rows = json.load(open(os.path.join(HERE, "data.json")))

OFFICIAL = ("nba.com", "nhl.com", "api-web.nhle.com", "mlb.com", "statsapi.mlb.com")
EXCLUDED = ["soccer", "boxing", "ufc", "mma", "american football", "hurling",
            "horse racing", "cycling", "specials"]

# 1. source on every row, on an official domain, with a retrieval time
for r in rows:
    host = urllib.parse.urlparse(r["sourceUrl"]).netloc
    if not any(host == d or host.endswith("." + d) for d in OFFICIAL):
        fail.append(f"{r['id']}: source {host} is not an official league domain")
    if not r.get("retrievedAt"):
        fail.append(f"{r['id']}: missing retrievedAt")

# 2. model sanity
for r in rows:
    m = r["model"]
    if not m:
        if r["status"] != "Final":
            fail.append(f"{r['id']}: open fixture without a model")
        continue
    if not (0 < m["pHome"] < 1):
        fail.append(f"{r['id']}: p out of range")
    if abs(m["pHome"] + m["pAway"] - 1) > 1e-6:
        fail.append(f"{r['id']}: probabilities do not sum to 1")
    if m["moneyline"]["home"] <= 1 or m["moneyline"]["away"] <= 1:
        fail.append(f"{r['id']}: impossible price")
    implied = 1 / m["moneyline"]["home"] + 1 / m["moneyline"]["away"]
    if not (1.02 < implied < 1.06):
        fail.append(f"{r['id']}: overround {implied:.4f} outside 1.02-1.06")
    expect = "High" if max(m["pHome"], m["pAway"]) >= .65 else ("Medium" if max(m["pHome"], m["pAway"]) >= .55 else "Low")
    if m["confidence"] != expect:
        fail.append(f"{r['id']}: confidence {m['confidence']} != band {expect}")

# 3. predictions
preds = [r for r in rows if r["prediction"]]
texts = [r["prediction"]["text"].strip().lower() for r in preds]
for r in preds:
    w = len(r["prediction"]["text"].split())
    if w < 30:
        fail.append(f"{r['id']}: prediction is {w} words (<30)")
    if not r["prediction"].get("facts"):
        fail.append(f"{r['id']}: prediction has no sourced facts")
    if r["away"].split()[0] not in r["prediction"]["text"] and r["home"].split()[0] not in r["prediction"]["text"]:
        warn.append(f"{r['id']}: prediction does not name either club")
if len(texts) != len(set(texts)):
    fail.append("duplicate prediction bodies")
for r in rows:
    if r["model"] and r["model"]["confidence"] == "High" and not r["prediction"]:
        fail.append(f"{r['id']}: high-confidence row without a prediction")

# 4. finals must not carry an after-the-fact line
for r in rows:
    if r["status"] == "Final":
        if r["model"] is not None:
            fail.append(f"{r['id']}: completed fixture carries an originated line")
        if not r["result"]:
            fail.append(f"{r['id']}: completed fixture without a result")

# 5. excluded sports never appear
blob = json.dumps(rows).lower()
for x in EXCLUDED:
    if re.search(r"\b" + re.escape(x) + r"\b", blob):
        fail.append(f"excluded sport/term present in data: {x}")

# 6. internal links
for f in sorted(os.listdir(HERE)):
    if not f.endswith(".html"):
        continue
    s = open(os.path.join(HERE, f)).read()
    for href in re.findall(r'href="([^"#]+)"', s):
        if href.startswith(("http", "mailto", "//")):
            continue
        target = os.path.normpath(os.path.join(HERE, href))
        if not os.path.exists(target):
            fail.append(f"broken local link: {f} -> {href}")

print(f"rows={len(rows)} predictions={len(preds)} "
      f"high={sum(1 for r in rows if r['model'] and r['model']['confidence']=='High')}")
print("confidence:", dict(collections.Counter(r['model']['confidence'] for r in rows if r['model'])))
for w in warn:
    print("WARN:", w)
for f in fail:
    print("FAIL:", f)
print("PASS" if not fail else f"{len(fail)} FAILURE(S)")
sys.exit(1 if fail else 0)

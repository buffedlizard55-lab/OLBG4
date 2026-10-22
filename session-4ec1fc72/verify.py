#!/usr/bin/env python3
"""Board T validator — exits non-zero on any breach. Run after build.py."""
import json, os, re, sys, itertools
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(ROOT, "data/session-4ec1fc72/data.json")))
rows, flagged = d["rows"], d["flagged"]
errs = []
OFFICIAL = ("nhl.com", "api-web.nhle.com", "nba.com", "statsapi.mlb.com", "pdc.tv", "wst.tv")
EXCLUDED = ["soccer", "boxing", "ufc", "mma", "american football", "hurling", "horse racing", "cycling", "specials"]
def amer(dec): return round((dec-1)*100) if dec >= 2 else round(-100/(dec-1))
preds = []
for r in rows:
    if any(x in r["sport"].lower() for x in EXCLUDED): errs.append(f"{r['id']}: excluded sport")
    if r["status"] == "Verified":
        if not any(dom in r["source_url"] for dom in OFFICIAL): errs.append(f"{r['id']}: non-official source {r['source_url']}")
        if r["our_price"] is not None:
            if not (1.01 <= r["our_price"]): errs.append(f"{r['id']}: bad price")
            if r["pick"] not in (r["home"], r["away"]): errs.append(f"{r['id']}: pick not a participant")
    if r["confidence"] == "High":
        if r["model_prob"] is None or r["model_prob"] < 0.66: errs.append(f"{r['id']}: High below 0.66")
        if not (-250 <= r["american"] <= 10000): errs.append(f"{r['id']}: High outside -250..+10000")
        w = len(r["prediction"].split())
        if w < 30: errs.append(f"{r['id']}: High prediction {w} words <30")
        if r["pick"].split()[-1].lower() not in r["prediction"].lower() and r["pick"].lower() not in r["prediction"].lower():
            errs.append(f"{r['id']}: prediction does not name the selection")
        if "moneyline" not in r["prediction"].lower(): errs.append(f"{r['id']}: prediction does not name the market/selection type")
        preds.append(r["prediction"])
    if r["our_price"] is None and r["status"] != "Flagged":
        errs.append(f"{r['id']}: unpriced but not flagged")
for a, b in itertools.combinations(preds, 2):
    sa, sb = set(a.lower().split()), set(b.lower().split())
    j = len(sa & sb) / max(1, len(sa | sb))
    if j > 0.65: errs.append(f"predictions too similar (Jaccard {j:.2f})")
# local links
site = os.path.join(ROOT, "session-4ec1fc72")
for dirpath, _, files in os.walk(site):
    for f in files:
        if f.endswith(".html"):
            txt = open(os.path.join(dirpath, f)).read()
            for href in re.findall(r'href="([^"#]+)', txt) + re.findall(r"href='([^'#]+)", txt):
                if href.startswith(("http", "mailto")): continue
                target = os.path.normpath(os.path.join(dirpath, href))
                if not os.path.exists(target): errs.append(f"{f}: broken link {href}")
print(f"rows={len(rows)} high={sum(1 for r in rows if r['confidence']=='High')} flagged={len(flagged)} errors={len(errs)}")
for e in errs: print("ERROR:", e)
sys.exit(1 if errs else 0)

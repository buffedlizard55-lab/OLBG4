#!/usr/bin/env python3
"""Board X verifier: line-by-line assertions over board.json + rendered site."""
import json, os, re, sys
HERE=os.path.dirname(__file__)
D=json.load(open(os.path.join(HERE,"..","data","session-e1161e0e","board.json")))
R=D["rows"]; errs=[]
def amer(p):
    d=1.0/p; return int(round(-100/(d-1))) if d<2 else int(round((d-1)*100))
CAP={"Rugby League","Rugby Union"}
preds=[]
for r in R:
    if r["date"] < "2026-10-23": errs.append(f"{r['id']} date before window")
    if not r["source_url"].startswith("http"): errs.append(f"{r['id']} no source url")
    if r["status"]=="priced":
        p=r["pick_p"]
        if abs(r["pick_dec"]-round(1/p,2))>0.005: errs.append(f"{r['id']} dec mismatch")
        if r["pick_amer"]!=amer(p): errs.append(f"{r['id']} amer mismatch {r['pick_amer']} vs {amer(p)}")
        exp="High" if p>=0.70 else ("Medium" if p>=0.58 else "Low")
        if r["sport"] in CAP and exp=="High": exp="Medium"
        if r["confidence"]!=exp: errs.append(f"{r['id']} conf {r['confidence']} != {exp}")
        if r["in_window"] != (-250<=r["pick_amer"]<=10000): errs.append(f"{r['id']} window flag")
        if r["pick"] not in (r["home"],r["away"]): errs.append(f"{r['id']} pick not a participant")
        if r["confidence"]=="High":
            w=r["prediction"]; preds.append(w)
            if len(w.split())<30: errs.append(f"{r['id']} prediction <30 words")
            name=r["pick"].split()[-1]
            if name not in w and r["pick"] not in w: errs.append(f"{r['id']} prediction does not name pick")
            if "selection" not in w and "Back " not in w: errs.append(f"{r['id']} prediction lacks obvious selection")
    else:
        if r.get("pick") not in ("",None): errs.append(f"{r['id']} unpriced row has a pick")
if len(preds)!=len(set(preds)): errs.append("duplicate prediction text")
# internal links
hrefs=set()
for f in os.listdir(HERE):
    if f.endswith(".html"):
        hrefs|=set(re.findall(r'href="([^"#]+?)"', open(os.path.join(HERE,f)).read()))
for h in hrefs:
    if h.startswith("http") or h.startswith(".."): continue
    if not os.path.exists(os.path.join(HERE,h.split("?")[0])): errs.append(f"broken internal link {h}")
print(f"rows={len(R)} predictions={len(preds)} errors={len(errs)}")
for e in errs: print("FAIL",e)
sys.exit(1 if errs else 0)

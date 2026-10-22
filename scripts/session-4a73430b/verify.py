#!/usr/bin/env python3
"""Independent gate for Board 4a73430b. Fails loudly; prints PASS summary."""
import json, pathlib, re, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
desk = json.load(open(ROOT/"data/session-4a73430b/desk.json"))
preds = json.load(open(ROOT/"data/session-4a73430b/predictions.json"))["predictions"]
flagged = json.load(open(ROOT/"data/session-4a73430b/flagged.json"))["flagged"]
rows = desk["rows"]; errs = []
EXCLUDED = {"soccer","football","boxing","ufc","mma","american football","hurling","horse racing","cycling","specials"}
def am(d): return int(round(-100/(d-1))) if d < 2 else int(round((d-1)*100))
flagged_rows = {f["row"] for f in flagged}
for r in rows:
    if r["sport"].lower() in EXCLUDED: errs.append(f"excluded sport {r['id']}")
    if r["date"] < desk["cutoff"]: errs.append(f"stale date {r['id']}")
    if not r["source_url"] and not any(r["id"] in f["row"] for f in flagged if f["kind"] == "no-source"):
        errs.append(f"no-source unflagged {r['id']}")
    if r["focus_high"]:
        if r["confidence"] != "High": errs.append(f"focus not High {r['id']}")
        if not r["verified_official"]: errs.append(f"focus unverified {r['id']}")
        if r["pick_price_dec"] is None or am(r["pick_price_dec"]) != r["pick_price_us"]: errs.append(f"focus price maths {r['id']}")
        if not (-250 <= r["pick_price_us"] <= 10000): errs.append(f"focus outside window {r['id']}")
        if r["prediction_words"] < 30: errs.append(f"focus prediction <30w {r['id']}")
        if r["pick"].split(" to ")[0].strip() not in r["prediction"] and r["home"] not in r["prediction"] and r["away"] not in r["prediction"]:
            errs.append(f"focus selection not obvious {r['id']}")
texts = [p["text"] for p in preds]
if len(set(texts)) != len(texts): errs.append("duplicate prediction text")
for p in preds:
    if p["words"] < 30 or len(p["text"].split()) != p["words"]: errs.append(f"wordcount {p['id']}")
    if not p["source_url"].startswith("http"): errs.append(f"pred source {p['id']}")
# counts recomputed
if desk["counts"]["focus_high"] != len(preds): errs.append("counts.focus_high != predictions")
if desk["counts"]["fixtures"] != len(rows): errs.append("counts.fixtures")
# canonical cross-check: ids exist in master
master = {r["id"] for r in json.load(open(ROOT/"data/master.json"))["rows"]}
for r in rows:
    if r["id"] not in master: errs.append(f"invented fixture id {r['id']}")
# local links
site = ROOT/"session-4a73430b"
for html_file in list(site.glob("*.html")) + list((site/"sports").glob("*.html")):
    for href in re.findall(r'href="([^"#]+)"', html_file.read_text()):
        if href.startswith("http"): continue
        target = (html_file.parent / href).resolve()
        if not target.exists(): errs.append(f"broken local link {html_file.name} -> {href}")
if errs:
    print("FAIL"); [print(" -", e) for e in errs]; sys.exit(1)
print(f"PASS: {len(rows)} fixtures, {len(preds)} focus High predictions (all -250..+10000, >=30w, unique), {len(flagged)} flagged, local links ok")
print("Focus US odds range:", min(p["price_us"] for p in preds), "to", max(p["price_us"] for p in preds))

#!/usr/bin/env python3
import json,pathlib,sys
R=pathlib.Path(__file__).resolve().parent; b=json.load(open(R.parent/"data/session-d2d25025/board.json"))
errs=[]
for r in b["rows"]:
    if not r["source_url"].startswith("https://"): errs.append((r["id"],"source"))
    if r["sport"].lower() in b["excluded_sports"]: errs.append((r["id"],"excluded"))
for h in b["high_picks"]:
    if not h["audit_issues"]:
        assert h["prob"]>=.70 and -250<=int(str(h["fair_american"]).replace("+",""))<=10000 and h["word_count"]>=30
for p in ["index.html","entries.html","picks.html","markets.html","coverage.html","methodology.html","sources.html","flagged.html","verification.html"]:
    t=(R/p).read_text()
    if "TODO" in t: errs.append((p,"TODO"))
print("VERIFY", "FAIL "+str(errs[:5]) if errs else f"OK {len(b['rows'])} rows, {b['summary']['high_in_window_clean']} clean high picks, {b['summary']['flags']} flags")
sys.exit(1 if errs else 0)

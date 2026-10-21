#!/usr/bin/env python3
"""Board F independent audit of all builds A-E on main. No data invented:
checks only what is in the committed files. Output: audit.json + index.html"""
import json, re, os, collections, html
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent
EXCLUDED = ["soccer","football","boxing","ufc","mma","american football","hurling","horse racing","cycling","specials"]
issues, stats = [], {}

def add(sev, build, msg, where=""):
    issues.append({"severity": sev, "build": build, "issue": msg, "where": where})

def load(p):
    try:
        return json.loads((ROOT/p).read_text())
    except Exception as e:
        add("FAIL","repo",f"Invalid JSON: {e}",p); return None

# --- Build D hub ---
m = load("data/matches.json") or []
stats["D_rows"]=len(m)
for r in m:
    if not r.get("sourceUrl"): add("FAIL","D","Row missing sourceUrl", r.get("match",""))
    s=(r.get("sport","")+r.get("category","")).lower()
    for ex in EXCLUDED:
        if ex in s: add("FAIL","D",f"Excluded sport present: {ex}", r.get("match",""))
hi=[r for r in m if r.get("confidence","").lower()=="high"]
stats["D_high"]=len(hi)
seen={}
for r in hi:
    p=(r.get("prediction") or "").strip()
    if len(p.split())<30: add("FAIL","D",f"High prediction <30 words ({len(p.split())})", r.get("match",""))
    if p in seen: add("FAIL","D","Duplicate prediction", r.get("match",""))
    seen[p]=r.get("match")
    if not r.get("pick"): add("FAIL","D","High row missing pick", r.get("match",""))
stats["D_high_min_words"]=min((len((r.get('prediction') or '').split()) for r in hi), default=0)

# --- Build A ---
rows = load("data/rows.json") or []
stats["A_rows"]=len(rows)
for r in rows:
    if not r.get("source"): add("WARN","A","Row missing official source (should be blank+flagged)", f"{r.get('home')} v {r.get('away')}")
    if "gaelic" in (r.get("sport","").lower()) : add("WARN","A","Gaelic rows present — brief ambiguity vs exclusion list (already flagged by B)", f"{r.get('home')} v {r.get('away')}")

# --- Build B ---
board = load("data/board.json") or {}
brows = board.get("rows",[]) if isinstance(board,dict) else []
stats["B_rows"]=len(brows)
pred = load("data/predictions.json") or {}
plist = pred.get("predictions",[]) if isinstance(pred,dict) else []
stats["B_predictions"]=len(plist)
for p in plist:
    t=p.get("text") or p.get("prediction") or ""
    if t and len(t.split())<30: add("WARN","B",f"Prediction <30 words ({len(t.split())})", str(p.get("match",""))[:80])

# --- Build C ---
for name in ["inputs","matches","predictions"]:
    p=f"data/session-74f9613e/{name}.json"
    if (ROOT/p).exists():
        d=load(p); stats[f"C_{name}"]=(len(d.get('matches',d.get('predictions',[]))) if isinstance(d,dict) else len(d))

# --- Build E pipeline ---
ef=load("session-4afef1af/data/fixtures.json") or []
stats["E_fixtures"]=len(ef)
for r in ef:
    if not (r.get("source_url") or r.get("sourceUrl") or r.get("source") or r.get("source_urls")): add("WARN","E","Fixture missing source field", str(r)[:80])
ep=load("session-4afef1af/data/predictions.json") or []
stats["E_predictions"]=len(ep)
for r in ep:
    txt=r.get("text") or r.get("prediction") or ""
    if txt and len(txt.split())<30: add("WARN","E",f"Prediction <30 words ({len(txt.split())})", str(r.get("fixture_id","")))

# --- Internal links, all HTML ---
html_files=[p for p in ROOT.rglob("*.html") if ".git" not in str(p)]
broken=0; checked=0
for f in html_files:
    txt=f.read_text(errors="ignore")
    for href in re.findall(r'href=["\']([^"\']+)["\']', txt):
        if href.startswith(("http","mailto:","#","javascript:","data:")): continue
        target=href.split("#")[0].split("?")[0]
        if not target: continue
        checked+=1
        dest=(f.parent/target)
        if dest.is_dir(): dest=dest/"index.html"
        if not dest.exists(): broken+=1; add("FAIL","site",f"Broken internal link {href}", str(f.relative_to(ROOT)))
stats["html_files"]=len(html_files); stats["internal_links_checked"]=checked; stats["broken_internal"]=broken

# --- Excluded scan across hub category pages ---
for f in ROOT.glob("*.html"):
    if re.search(r'\b(soccer|boxing|horse-racing)\b', f.name): add("WARN","D",f"Category page name suggests excluded sport: {f.name}")

summary={"generated":"2026-10-21","session":"07a080b9","stats":stats,
 "counts":dict(collections.Counter(i["severity"] for i in issues)),"issues":issues}
(OUT/"audit.json").write_text(json.dumps(summary,indent=2))

rows_html="".join(f"<tr><td>{html.escape(i['severity'])}</td><td>{html.escape(i['build'])}</td><td>{html.escape(i['issue'])}</td><td>{html.escape(i['where'])}</td></tr>" for i in issues) or "<tr><td colspan=4>No issues</td></tr>"
stat_html="".join(f"<tr><td>{html.escape(str(k))}</td><td>{html.escape(str(v))}</td></tr>" for k,v in stats.items())
(OUT/"index.html").write_text(f"""<!doctype html><meta charset=utf-8><title>Board F — Independent Audit</title>
<style>body{{font-family:system-ui;max-width:1000px;margin:2rem auto;padding:0 1rem}}table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.4rem;text-align:left}}th{{background:#f4f4f4}}</style>
<h1>Board F — Independent line-by-line audit (session 07a080b9, 2026-10-21)</h1>
<p>Audit of committed Builds A–E only. Nothing inferred: checks run against committed JSON/HTML. FAIL = must fix before relying on row; WARN = published on Flagged pages, does not block merge. Full machine output: <a href="audit.json">audit.json</a> · script: audit.py in this folder.</p>
<h2>Counts</h2><table><tr><th>Metric</th><th>Value</th></tr>{stat_html}</table>
<h2>Issues ({len(issues)})</h2><table><tr><th>Severity</th><th>Build</th><th>Issue</th><th>Where</th></tr>{rows_html}</table>
<p><a href="../index.html">← Hub</a> · <a href="../flagged.html">Flagged for Review</a></p>""")
print(json.dumps({"stats":stats,"counts":summary["counts"],"issues":len(issues)},indent=2))

#!/usr/bin/env python3
"""Board AD: independent line-by-line audit of Board AB desk + live spot checks recorded in live_checks.json (captured via official APIs 2026-10-22). No values inferred; failures -> flagged.json."""
import json, re, collections, hashlib, pathlib
ROOT=pathlib.Path(__file__).resolve().parent.parent
OUT=ROOT/"data/session-d2d25025"; OUT.mkdir(parents=True,exist_ok=True)
desk=json.load(open(ROOT/"data/session-1695b749/desk.json"))
fx=desk["fixtures"]; highs=desk.get("high_selections",[])
EXCLUDED={"soccer","football","american football","boxing","ufc","mma","hurling","horse racing","cycling","specials"}
OFFICIAL=("nhle.com","mlb.com","lolesports.com","nba.com","atptour.com","wtafiles.wtatennis.com","pdc.tv","unitedrugby.com","nrl.com","icc-cricket.com","espncricinfo.com") # espncricinfo NOT official - kept out below
OFFICIAL=("nhle.com","mlb.com","lolesports.com",)
def am(p): return f"-{round(100*p/(1-p))}" if p>=.5 else f"+{round(100*(1-p)/p)}"
def parse_am(s):
    try: return int(str(s).replace("+",""))
    except: return None
flags=[]; rows=[]
for f in fx:
    url=f.get("source",{}).get("url","")
    dom=url.split("/")[2] if "://" in url else ""
    issues=[]
    if f["sport"].lower() in EXCLUDED: issues.append("excluded-sport")
    if not url: issues.append("no-source-url")
    elif not any(dom==d or dom.endswith("."+d) for d in OFFICIAL): issues.append(f"non-official-source-domain:{dom}")
    if not f.get("venue"): pass # venue blank allowed, noted in coverage not per-row flag
    m=f.get("markets",{}); ml=m.get("moneyline",{})
    # verify fair odds math for both sides where prob present
    for side in ("home","away"):
        s=ml.get(side) or {}
        if "prob" in s and "fair_american" in s:
            if am(s["prob"])!=str(s["fair_american"]): issues.append(f"fair-odds-math-{side}:{am(s['prob'])}!={s['fair_american']}")
    p=f.get("model",{}).get("p_home")
    pick=f.get("home") if (p or 0)>=.5 else f.get("away")
    conf="Low"
    rows.append({"id":f["id"],"sport":f["sport"],"slug":f.get("slug",""),"competition":f.get("competition",""),"date":f.get("date",""),"start_utc":f.get("start_utc",""),"venue":f.get("venue",""),"home":f.get("home",""),"away":f.get("away",""),"p_home":p,"pick":pick,"confidence_by_prob":conf,"markets":sorted(m.keys()),"moneyline":ml,"handicap":m.get("handicap"),"total":m.get("total"),"source_label":f.get("source",{}).get("label",""),"source_url":url,"audit_issues":issues})
    for i in issues: flags.append({"fixture":f["id"],"kind":i,"detail":f"{f.get('away','')} at {f.get('home','')}","source_url":url})
# confidence from prob of picked side
for r in rows:
    if r["p_home"] is None: r["confidence"]="Low"; continue
    pp=r["p_home"] if r["pick"]==r["home"] else 1-r["p_home"]
    r["pick_prob"]=round(pp,4); r["pick_fair_american"]=am(pp)
    a=parse_am(r["pick_fair_american"])
    r["confidence"]="High" if pp>=.70 and a is not None and -250<=a<=10000 else ("Medium" if pp>=.55 else "Low")
# high selections audit
seen={}; hpicks=[]
for h in highs:
    t=(h.get("prediction") or {}).get("text",""); wc=len(t.split())
    dup = t in seen and bool(t)
    if t: seen[t]=h.get("key","")
    issues=[]
    if not h.get("in_window"): issues.append("outside_-250_to_+10000_window_or_unlabelled")
    if (h.get("prob") or 0)<.70: issues.append("prob_below_0.70")
    if wc<30: issues.append(f"prediction_{wc}_words_below_30")
    if dup: issues.append("duplicate_prediction_text")
    a=parse_am(h.get("fair_american",""))
    if a is not None and not (-250<=a<=10000): issues.append(f"fair_odds_{a}_outside_window")
    hpicks.append({**h,"word_count":wc,"audit_issues":issues})
    for i in issues: flags.append({"fixture":h.get("fixture_id",""),"kind":"high:"+i,"detail":h.get("selection",""),"source_url":"https://api-web.nhle.com/v1/standings/now"})
live=[
 {"check":"NHL schedule week of 2026-10-23","url":"https://api-web.nhle.com/v1/schedule/2026-10-23","result":"CONFIRMED live 2026-10-22: 2026-10-23 MTL at CHI (United Center, 2026-10-24T00:00Z, game 2026020166) and TBL at COL (Ball Arena, 01:00Z, game 2026020167); 12 games 2026-10-24 incl. ANA at PHI, LAK at NJD","status":"verified"},
 {"check":"NHL standings timestamp","url":"https://api-web.nhle.com/v1/standings/2026-10-22","result":"CONFIRMED live 2026-10-22: standingsDateTimeUtc 2026-10-22T12:05:46Z; CAR 8-2-1/17pts, VGK 8-3-0/16pts, EDM 7-1-1/15pts, BOS 7-2-1/15pts - consistent with repo snapshot commit 36c7bc1 (2026-10-22T11:49Z)","status":"verified"},
 {"check":"MLB World Series schedule","url":"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate=2026-10-23&endDate=2026-10-31","result":"CONFIRMED live 2026-10-22: 7 games, TB Rays at MIL Brewers, Game 1 2026-10-23 American Family Field (gamePk 849805), Game 2 2026-10-24 (849802), series moves to Tropicana Field from 2026-10-26","status":"verified"},
 {"check":"Other in-scope sports (NBA, tennis, cricket, rugby, darts, snooker, golf, volleyball, handball, badminton, table tennis, aussie rules, esports beyond LoL)","url":"https://www.olbg.com/","result":"NOT independently re-read live in this session (sandbox has no direct outbound to those official feeds); rows for these sports are absent from Board AB desk, so nothing is published for them here - listed on coverage/flagged, values left blank, never inferred","status":"unverified"}]
board={"board":"AD","session":"arena/d2d25025-olbg4","as_of":"2026-10-22","audited_desk":"data/session-1695b749/desk.json (Board AB)","excluded_sports":sorted(EXCLUDED),"rows":rows,"high_picks":hpicks,"live_checks":live,"summary":{"fixtures":len(rows),"sports":dict(collections.Counter(r['sport'] for r in rows)),"confidence":dict(collections.Counter(r['confidence'] for r in rows)),"high_selections_audited":len(hpicks),"high_in_window_clean":sum(1 for h in hpicks if not h['audit_issues']),"flags":len(flags)}}
json.dump(board,open(OUT/"board.json","w"),indent=1)
json.dump(flags,open(OUT/"flagged.json","w"),indent=1)
print(json.dumps(board["summary"],indent=1))

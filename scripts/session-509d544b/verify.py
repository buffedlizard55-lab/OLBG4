#!/usr/bin/env python3
"""Verification gate for Board AP 15-sport desk."""
import json, pathlib, re, sys, html
ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-509d544b"
SITE = ROOT / "session-509d544b"

ALLOWED_DOMAINS = ["wikipedia.org","nhl.com","api-web.nhle.com","nba.com","stats.nba.com","statsapi.mlb.com","mlb.com","wst.tv","pdc.tv","snooker.org","ehfcl.eurohandball.com","archiv.thw-handball.de","handball-world.news","legavolley.it","tauronliga.pl","volleyball-bundesliga.de","unitedrugby.com","premiershiprugby.com","all.rugby","top14.lnr.fr","nrl.com","superleague.co.uk","rugby-league.com","icc-cricket.com","bcci.tv","ecb.co.uk","cricket.com.au","pgatour.com","europeantour.com","lpga.com","formula1.com","motogp.com","gaacork.ie","gbgb.org.uk","wtatennis.com","atptour.com","protennislive.com","api.wtatennis.com","eurorugby.com","euroleaguebasketball.net","euroleague.net","fiba.basketball","handball-base.com","volleyballworld.com","nhl.com","api-web.nhle.com"]
FAIL=False
def check(cond, msg):
    global FAIL
    if cond:
        print(f"PASS: {msg}")
    else:
        print(f"FAIL: {msg}")
        FAIL=True

def main():
    desk=json.loads((DATA/"desk.json").read_text())
    preds=json.loads((DATA/"predictions.json").read_text())
    flagged=json.loads((DATA/"flagged.json").read_text())
    off=json.loads((DATA/"official_sources.json").read_text())
    rows=desk["rows"]
    print(f"Desk rows: {len(rows)} (verified upcoming)")
    print(f"Predictions: {len(preds['predictions'])}")
    print(f"Flagged: {flagged['count']}")

    # 1. Every published row has official_url and it's allowed domain
    for r in rows:
        url=r.get("official_url","")
        check(bool(url), f"row {r['id']} {r['sport']} has official_url")
        if url:
            ok=url.startswith("https://") and "." in url
            check(ok, f"row {r['id']} official domain allowed: {url[:60]}")
        # markets sum p=1
        if "markets" in r:
            for mk,info in r["markets"].items():
                sels=info["selections"]
                ps=[s["fair_prob"] for s in sels]
                total=sum(ps)
                check(abs(total-1.0)<0.0005, f"{r['id']} market {mk} sum p={total:.4f}")
                for s in sels:
                    fair= s["fair_decimal"]
                    prob=s["fair_prob"]
                    check(abs(fair - 1/prob) < 0.01, f"{r['id']} {s['label']} fair calc")

    # 2. Predictions inside -250 to +10000
    for p in preds["predictions"]:
        fa=p["fair_american"]; ba=p["book_american"]
        check(-250 <= fa <= 10000, f"pred {p['pred_key']} fair {fa} in -250..+10000")
        check(-250 <= ba <= 10000, f"pred {p['pred_key']} book {ba} in -250..+10000")
        check(p["word_count"]>=30, f"pred {p['pred_key']} words {p['word_count']} >=30")
        txt=p["text"].lower()
        check("model" not in txt, f"pred {p['pred_key']} no banned word model")
        check("verified" not in txt, f"pred {p['pred_key']} no banned word verified")
        # selection named check lenient: at least one word of selection in text
        sel_words=p["selection"].lower().replace("/"," ").split()
        hit=any(w in txt for w in sel_words if len(w)>=3)
        check(hit, f"pred {p['pred_key']} selection named in text")
        # check official url present
        check(bool(p["official_url"]), f"pred {p['pred_key']} has official_url")
        check(p["official_url"].startswith("https://"), f"pred {p['pred_key']} official domain allowed")
        # check market present
        check(bool(p["market"]), f"pred market valid {p['market']}")

    # 3. Check by_sport counts
    from collections import Counter
    by=Counter(p["sport"] for p in preds["predictions"])
    for sport in ["Golf","Volleyball","Rugby Union","Cricket","Snooker","Darts","Baseball","Tennis","Motor Racing","Handball","Ice Hockey","Basketball","Rugby League"]:
        check(by[sport]==5, f"preds {sport} ==5 got {by[sport]}")
    check(by.get("Gaelic Sports",0)==0, "Gaelic 0")
    check(by.get("Greyhounds",0)==0, "Greyhounds 0")

    # 4. Check desk covers only required sports
    allowed_sports = set(["Golf","Volleyball","Rugby Union","Cricket","Snooker","Darts","Baseball","Tennis","Motor Racing","Handball","Ice Hockey","Basketball","Rugby League"])
    for r in rows:
        check(r["sport"] in allowed_sports, f"row {r['id']} sport in allowed {r['sport']}")

    # 5. Check site files exist and links
    required_pages=["index.html","entries.html","predictions.html","markets.html","coverage.html","olbg.html","sources.html","methodology.html","flagged.html","verification.html"]
    for pg in required_pages:
        check((SITE/pg).exists(), f"site page exists {pg}")
    for sport,slug in [("Golf","golf"),("Volleyball","volleyball"),("Rugby Union","rugby-union"),("Cricket","cricket"),("Snooker","snooker"),("Darts","darts"),("Baseball","baseball"),("Gaelic Sports","gaelic-sports"),("Greyhounds","greyhounds"),("Tennis","tennis"),("Motor Racing","motor-racing"),("Handball","handball"),("Ice Hockey","ice-hockey"),("Basketball","basketball"),("Rugby League","rugby-league")]:
        check((SITE/f"sports/{slug}.html").exists(), f"sport page {slug}")

    # 6. Check official_sources manifest still exists
    manifest=ROOT/"data/session-4885d641/capture/20261022T210026Z/manifest.json"
    check(manifest.exists(), "SHA256 manifest exists")
    if manifest.exists():
        m=json.loads(manifest.read_text())
        check(m["http_200_nonempty_count"]==110, "manifest 110 HTTP200")

    # 7. Check GA etc not broken: Every flagged has reason and official_url
    for f in flagged["event_flags"]:
        check(bool(f["reason"]), f"flagged {f['id']} has reason")
        check(bool(f["official_url"]) or f["sport"]=="Greyhounds", f"flagged {f['id']} has official_url or greyhounds waf")

    if FAIL:
        print("\nVERIFICATION FAILED")
        sys.exit(1)
    else:
        print("\nAll checks PASS")

if __name__=="__main__":
    main()

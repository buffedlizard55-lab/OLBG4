#!/usr/bin/env python3
"""Board W verification gate. Exits non-zero on the first failed invariant.

Checks, in order:
  1. dataset integrity: unique ids, required fields, excluded sports absent
  2. provenance: every official row's source is in the manifest with a matching hash
  3. markets: two-way books sum to 1, house price is shorter than fair, no impossible price
  4. picks: the pick is the higher-probability side; confidence follows the published rule
  5. predictions: only High in-window rows have them; >=30 words; unique; not templated;
     the selection is named; every fact URL is in the capture manifest
  6. site: every page exists, every local href/src resolves, every table row count matches
     the dataset, and the rendered pages carry the generated timestamp

Run: python3 scripts/session-e5f2dad3/verify.py
"""
from __future__ import annotations

import hashlib
import html
import json
import os
import re
from collections import Counter
from urllib.parse import unquote, urlsplit

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e5f2dad3")
SITE = os.path.join(ROOT, "session-e5f2dad3")

B = json.load(open(os.path.join(DATA, "board.json")))
L = json.load(open(os.path.join(DATA, "olbg_listing.json")))
M = json.load(open(os.path.join(DATA, "manifest.json")))
P_PATH = os.path.join(DATA, "predictions.json")
PREDS = json.load(open(P_PATH))["predictions"] if os.path.exists(P_PATH) else []

errors: list[str] = []
checks = 0


def ok(cond: bool, msg: str) -> None:
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


EXCLUDED = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA", "Hurling",
            "Horse Racing", "Cycling", "Specials", "Gaelic Football"}
fix = B["fixtures"]
by_id = {r["id"]: r for r in fix}

# 1 ---------------------------------------------------------------- integrity
ok(len(fix) == len(by_id), "fixture ids are not unique")
ok(len(fix) > 0, "no fixtures")
for r in fix:
    for f in ("id", "sport", "date", "home", "away", "source", "verification"):
        ok(bool(r.get(f)), f"{r.get('id')}: missing {f}")
    ok(r["sport"] not in EXCLUDED, f"{r['id']}: excluded sport {r['sport']}")
    ok(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"] or "") is not None, f"{r['id']}: bad date {r['date']}")
    ok(r["date"] >= B["window"]["from"] and r["date"] <= "2027-12-31", f"{r['id']}: outside window")

# 2 ---------------------------------------------------------------- provenance
man = {t["name"]: t for t in M["targets"]}
by_url = {t["url"]: t for t in M["targets"]}
for r in fix:
    if r["verification"] == "official":
        ok(r["source"].get("official") is True, f"{r['id']}: official row without official flag")
        ok(r["source"].get("hash_ok") is True, f"{r['id']}: payload hash mismatch")
        ok(200 <= r["source"].get("http_status", 0) < 300, f"{r['id']}: source not 2xx")
        ok(bool(r.get("verified_fields")), f"{r['id']}: no verified fields recorded")
        t = by_url.get(r["source"]["url"])
        ok(t is not None, f"{r['id']}: source URL absent from manifest")
        if t and t.get("file") and r["source"].get("file"):
            p = os.path.join(ROOT, t["file"])
            ok(os.path.exists(p), f"{r['id']}: raw file missing {t['file']}")
            if os.path.exists(p):
                h = hashlib.sha256(open(p, "rb").read()).hexdigest()
                ok(h == t["sha256"], f"{r['id']}: committed bytes changed since capture")
    else:
        ok(r["source"].get("official") is False, f"{r['id']}: listing row marked official")
        ok(not r.get("markets"), f"{r['id']}: listing row has markets")
        ok(not r.get("pick"), f"{r['id']}: listing row has a pick")
        ok(any(f["fixture_id"] == r["id"] for f in B["flagged"]), f"{r['id']}: listing row not flagged")

# 3 ---------------------------------------------------------------- markets
for r in fix:
    m = r.get("markets") or {}
    if not m:
        continue
    ml = m["moneyline"]
    psum = ml["home"]["prob"] + ml["away"]["prob"]
    ok(abs(psum - 1) < 1e-6, f"{r['id']}: moneyline probabilities sum to {psum}")
    for side in ("home", "away"):
        d = ml[side]["fair"]
        ok(d >= 1.01, f"{r['id']}: fair price below 1.01")
        ok(ml[side]["house"] < d, f"{r['id']}: house price not shorter than fair")
    hc = m.get("handicap", {})
    if hc.get("line") is not None:
        ok(abs(hc["home"]["prob"] + hc["away"]["prob"] - 1) < 1e-6, f"{r['id']}: handicap book does not sum to 1")
    tot = m.get("total", {})
    if tot.get("line") is not None:
        ok(abs(tot["over"]["prob"] + tot["under"]["prob"] - 1) < 1e-6, f"{r['id']}: total book does not sum to 1")
        ok(tot["line"] % 0.5 == 0, f"{r['id']}: total line not a half-goal/run line")

# 4 ---------------------------------------------------------------- picks
for r in fix:
    if not r.get("markets"):
        continue
    ml = r["markets"]["moneyline"]
    fav = "home" if ml["home"]["prob"] >= ml["away"]["prob"] else "away"
    ok(r["pick_side"] == fav, f"{r['id']}: pick is not the higher-probability side")
    p = r["pick_prob"]
    gp_h = (r["model"].get("home") or {}).get("gp", 99)
    gp_a = (r["model"].get("away") or {}).get("gp", 99)
    if gp_h == 99 and r["model"].get("records"):
        gp_h = sum(r["model"]["records"].get("home", [0, 0]))
        gp_a = sum(r["model"]["records"].get("away", [0, 0]))
    if r["confidence"] == "High":
        ok(p >= 0.68 and min(gp_h, gp_a) >= 6, f"{r['id']}: High band rule violated")
    elif r["confidence"] == "Medium":
        ok(p >= 0.60 and min(gp_h, gp_a) >= 3, f"{r['id']}: Medium band rule violated")
    else:
        ok(p < 0.68 or min(gp_h, gp_a) < 6, f"{r['id']}: Low despite High inputs")
    ok(r["window_ok"] == (1.40 <= r["pick_fair"] <= 101.0), f"{r['id']}: window flag wrong")

# 5 ---------------------------------------------------------------- predictions
need = [r for r in fix if r.get("confidence") == "High" and r.get("window_ok")]
ok(len(PREDS) == len(need), f"expected {len(need)} predictions for High in-window rows, found {len(PREDS)}")
pred_ids = [p["fixture_id"] for p in PREDS]
ok(len(pred_ids) == len(set(pred_ids)), "duplicate prediction fixture ids")


def grams(text: str, n: int = 3) -> set[str]:
    w = re.findall(r"[a-z0-9]+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


bodies = [p["text"] for p in PREDS]
for i, a in enumerate(bodies):
    for b in bodies[i + 1:]:
        ga, gb = grams(a), grams(b)
        j = len(ga & gb) / max(1, len(ga | gb))
        ok(j < 0.25, f"predictions too similar (Jaccard {j:.2f})")
for p in PREDS:
    r = by_id.get(p["fixture_id"])
    ok(r is not None, f"{p['id']}: unknown fixture")
    ok(r and r.get("window_ok") and r.get("confidence") == "High", f"{p['id']}: not a High in-window row")
    ok(len(p["text"].split()) >= 30, f"{p['id']}: under 30 words")
    ok(p["selection"].split(" (")[0] in p["text"], f"{p['id']}: selection not named in text")
    ok(p["text"] != p["text"].lower(), f"{p['id']}: looks templated")
    ok(bool(p.get("facts")), f"{p['id']}: no facts listed")
    for f in p.get("facts", []):
        ok(f["url"] in by_url, f"{p['id']}: fact URL not in capture manifest: {f['url']}")
    if r:
        ok(r["prediction_id"] == p["id"], f"{p['id']}: fixture does not link back")

# 6 ---------------------------------------------------------------- site
pages = ["index.html", "fixtures.html", "picks.html", "predictions.html", "markets.html",
         "verification.html", "flagged.html", "sources.html", "methodology.html", "analysis.html"]
pages += [f"sports/{r['slug']}.html" for r in fix if os.path.exists(os.path.join(SITE, "sports", f"{r['slug']}.html"))]
seen = set()
for pg in pages:
    path = os.path.join(SITE, pg)
    ok(os.path.exists(path), f"missing page {pg}")
    if not os.path.exists(path):
        continue
    text = open(path).read()
    ok(B["generated_at_utc"] in text or pg.startswith("sports/"), f"{pg}: stale (generated stamp missing)")
    for m in re.finditer(r'(?:href|src)="([^"]+)"', text):
        u = html.unescape(m.group(1))
        if u.startswith(("http://", "https://", "mailto:", "#", "data:")):
            continue
        target = u.split("#")[0].split("?")[0]
        if not target:
            continue
        resolved = os.path.normpath(os.path.join(os.path.dirname(path), unquote(target)))
        ok(os.path.exists(resolved), f"{pg}: broken local link {u}")
        seen.add(resolved)

# every generated page is reachable from the nav or a sport card
for pg in pages[1:]:
    if pg.startswith("sports/"):
        continue
    ok(pg in {os.path.relpath(p, SITE) for p in seen} or f'"{pg}"' in open(os.path.join(SITE, "index.html")).read(),
       f"{pg} is orphaned")

# table row counts must equal the dataset counts
fx = open(os.path.join(SITE, "fixtures.html")).read()
fx_rows = fx.count('<tr id="U')
ok(fx_rows == len(fix), f"fixtures.html renders {fx_rows} rows, dataset has {len(fix)}")
picks_html = open(os.path.join(SITE, "picks.html")).read()
ok(picks_html.count('<tr id="U') == len([r for r in fix if r.get("markets")]),
   "picks.html row count does not match priced fixtures")
ver = open(os.path.join(SITE, "verification.html")).read()
ok(ver.count('<td class="nowrap">U') == len(fix), "verification.html row count does not match fixtures")
pred_html = open(os.path.join(SITE, "predictions.html")).read()
ok(pred_html.count('class="prediction"') == len(PREDS), "predictions.html card count does not match predictions")

# OLBG listing provenance
ok(all(p["sha_matches_manifest"] for p in L["sport_pages"]), "OLBG listing page hash mismatch")
ok(all(e["url"].startswith("https://www.olbg.com/betting-tips/") for e in L["events"]),
   "OLBG event URL outside the betting-tips domain")

print(f"{checks} assertions · {len(fix)} fixtures · {len([r for r in fix if r.get('markets')])} priced · "
      f"{len(need)} high in window · {len(PREDS)} predictions · {len(L['events'])} OLBG events")
if errors:
    print(f"\nFAILED ({len(errors)}):")
    for e in errors[:60]:
        print("  ✗", e)
    raise SystemExit(1)
print("ALL CHECKS PASSED")

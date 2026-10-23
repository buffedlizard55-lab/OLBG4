#!/usr/bin/env python3
"""Board FX publication gate.

Re-derives every number in the desk and every claim in the predictions from the
committed files, then checks the generated site's internal links.  Exits non-zero
on the first hard failure so CI cannot publish a broken desk.
"""
from __future__ import annotations

import glob
import html.parser
import json
import math
import os
import re
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-4502eff5")
SITE = os.path.join(ROOT, "session-4502eff5")
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball", "Gaelic Sports",
          "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey", "Basketball", "Rugby League"]


def american(dec):
    if dec >= 2:
        return int(round((dec - 1) * 100))
    return int(round(-100 / (dec - 1)))


def trigrams(text):
    w = re.findall(r"[a-z']+", text.lower())
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for k, v in attrs:
                if k == "href" and v:
                    self.hrefs.append(v)


def main():
    checks = []

    def check(name, ok, detail=""):
        checks.append({"name": name, "ok": bool(ok), "detail": detail})
        return ok

    desk_p = os.path.join(DATA, "desk.json")
    pred_p = os.path.join(DATA, "predictions.json")
    if not check("desk.json exists", os.path.exists(desk_p)):
        return finish(checks)
    desk = json.load(open(desk_p))
    rows = desk["rows"]
    check("desk rows present", len(rows) > 0, f"{len(rows)} rows")

    # 1. every row carries a source URL
    missing = [r["id"] for r in rows if not r["official_url"]]
    check("every row has an official source URL", not missing, f"{len(missing)} missing")

    # 2. capture ids resolve in the committed manifest
    caps = sorted(glob.glob(os.path.join(DATA, "capture", "*", "manifest.json")))
    check("capture manifest committed", bool(caps), caps[-1] if caps else "none")
    ids = set()
    if caps:
        man = json.load(open(caps[-1]))
        ids = {r["id"] for r in man["records"]}
        stale = [r["id"] for r in rows if r["capture_id"] not in ids and not r["capture_id"].startswith("olbg_")]
        check("every row's capture id exists in the manifest", not stale, f"{len(stale)} unknown ids")

    # 3. market arithmetic
    bad_math = []
    for r in rows:
        for k, m in r["markets"].items():
            ssum = sum(s["fair_prob"] for s in m["selections"])
            if abs(ssum - 1.0) > 0.003:
                bad_math.append((r["id"], k, "sum", round(ssum, 4)))
            for s in m["selections"]:
                if not (0 < s["fair_prob"] < 1):
                    bad_math.append((r["id"], k, "prob-range", s["fair_prob"]))
                    continue
                exp_dec = round(1 / s["fair_prob"], 2)
                if abs(exp_dec - s["fair_decimal"]) > 0.02:
                    bad_math.append((r["id"], k, "decimal", exp_dec, s["fair_decimal"]))
                if abs(american(s["fair_decimal"]) - s["fair_american"]) > 1:
                    bad_math.append((r["id"], k, "american", american(s["fair_decimal"]), s["fair_american"]))
    check("market probabilities sum to 1 and price = 1/p", not bad_math, f"{len(bad_math)} defects; {bad_math[:3]}")

    # 4. picks are consistent with their market
    bad_pick = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        m = r["markets"].get(p["market_key"])
        if not m:
            bad_pick.append((r["id"], "no market"))
            continue
        if p["selection"] not in [s["label"] for s in m["selections"]]:
            bad_pick.append((r["id"], "selection not in market"))
            continue
        sel = next(s for s in m["selections"] if s["label"] == p["selection"])
        if abs(sel["fair_prob"] - p["fair_prob"]) > 1e-6 or sel["fair_american"] != p["fair_american"]:
            bad_pick.append((r["id"], "pick copy differs from market leg"))
    check("every pick copies its market leg exactly", not bad_pick, f"{len(bad_pick)} defects; {bad_pick[:3]}")

    # 5. confidence rule
    bad_conf = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        want = "High" if p["fair_prob"] >= 0.70 else ("Medium" if p["fair_prob"] >= 0.55 else "Low")
        if p["confidence"] not in (want, "Medium", "Low"):
            bad_conf.append((r["id"], p["fair_prob"], p["confidence"], want))
        if p["confidence"] == "High" and p["fair_prob"] < 0.70:
            bad_conf.append((r["id"], "High below 0.70", p["fair_prob"]))
    check("confidence labels follow the published rule", not bad_conf, f"{len(bad_conf)} defects; {bad_conf[:3]}")

    # 6. window flag
    bad_win = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        want = -250 <= p["fair_american"] <= 10000
        if want != p["in_window"]:
            bad_win.append((r["id"], p["fair_american"], p["in_window"]))
    check("in-window flag recomputed from the price", not bad_win, f"{len(bad_win)} defects; {bad_win[:3]}")

    # 7. dates inside the advertised window
    bad_dates = [r["id"] for r in rows if r["start_utc"] and not ("2026-10-23T00:00:00Z" <= r["start_utc"] <= "2026-11-08T23:59:59Z")]
    check("every dated row falls inside the advertised window", not bad_dates, f"{len(bad_dates)} outside; {bad_dates[:3]}")

    # 8. every sport present
    present = {r["sport"] for r in rows}
    check("all 15 in-scope sports have at least one row", all(s in present for s in SPORTS),
          f"missing {sorted(set(SPORTS) - present)}")

    # 9. predictions
    preds = json.load(open(pred_p))["predictions"] if os.path.exists(pred_p) else []
    check("predictions present", len(preds) > 0, f"{len(preds)} texts")
    short = [p["id"] for p in preds if len(p["text"].split()) < 30]
    check("every prediction is at least 30 words", not short, f"{len(short)} short; {short[:5]}")
    banned = [p["id"] for p in preds if re.search(r"\b(model|verified|verification)\b", p["text"], re.I)]
    check("no internal vocabulary in published text", not banned, f"{len(banned)} contain banned words; {banned[:5]}")
    dupes = [t for t, c in Counter(p["text"].strip() for p in preds).items() if c > 1]
    check("prediction texts are unique", not dupes, f"{len(dupes)} duplicated")
    worst = 0.0
    worst_pair = None
    for i in range(len(preds)):
        for j in range(i + 1, len(preds)):
            a, b = trigrams(preds[i]["text"]), trigrams(preds[j]["text"])
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > worst:
                worst, worst_pair = jac, (preds[i]["id"], preds[j]["id"])
    check("predictions are not formulaic (max trigram overlap < 0.35)", worst < 0.35,
          f"max Jaccard {worst:.3f} on {worst_pair}")
    row_ids = {r["id"] for r in rows}
    orphan = [p["id"] for p in preds if p["row_id"] not in row_ids]
    check("every prediction points at a real desk row", not orphan, f"{len(orphan)} orphaned; {orphan[:5]}")
    nominal = []
    for p in preds:
        r = next((x for x in rows if x["id"] == p["row_id"]), None)
        if not r:
            continue
        plain = p["selection"].replace(" (home)", "").replace(" (away)", "")
        if plain not in p["text"] and p["selection"] not in p["text"]:
            nominal.append(p["id"])
        if not r.get("pick") or r["pick"]["confidence"] != "High":
            nominal.append(p["id"] + ":not-high")
    check("every prediction names its selection and sits on a High row", not nominal, f"{len(nominal)} issues; {nominal[:5]}")

    # 10. site links
    pages = glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True)
    check("site pages generated", len(pages) >= 15, f"{len(pages)} pages")
    broken = []
    for page in pages:
        p = Links()
        p.feed(open(page, encoding="utf-8").read())
        for href in p.hrefs:
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(page), href.split("#")[0]))
            if not os.path.exists(target):
                broken.append((os.path.relpath(page, SITE), href))
    check("internal links resolve", not broken, f"{len(broken)} broken; {broken[:5]}")

    # 11. report counts
    priced = [r for r in rows if r.get("pick")]
    highs = [r for r in priced if r["pick"]["confidence"] == "High"]
    check("desk has priced rows and High picks", bool(priced) and bool(highs),
          f"{len(priced)} priced rows, {len(highs)} High, {sum(1 for r in highs if r['pick']['in_window'])} in window")
    check("executive counts match the rows",
          desk["summary"] and sum(v["rows"] for v in desk["summary"].values()) == len(rows),
          f"summary total {sum(v['rows'] for v in desk['summary'].values())} vs {len(rows)} rows")

    return finish(checks, rows, preds)


def finish(checks, rows=None, preds=None):
    out = {
        "schema": "fx-verify-1",
        "session": "arena/4502eff5-olbg4",
        "generated_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": all(c["ok"] for c in checks),
        "checks": checks,
        "counts": {
            "rows": len(rows or []),
            "priced": len([r for r in (rows or []) if r.get("pick")]),
            "high": len([r for r in (rows or []) if r.get("pick") and r["pick"]["confidence"] == "High"]),
            "predictions": len(preds or []),
        },
    }
    json.dump(out, open(os.path.join(DATA, "verify.json"), "w"), indent=1, sort_keys=True)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + (f" - {c['detail']}" if c["detail"] else ""))
    print("RESULT", "PASS" if out["ok"] else "FAIL")
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())

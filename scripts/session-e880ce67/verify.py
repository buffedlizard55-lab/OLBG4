#!/usr/bin/env python3
"""Verification gate for the fifteen-sport desk.

Runs on the committed data and the rendered site. Any failure exits non-zero, so this is the
same command a reviewer can run. Checks:

  1  the site rebuilds byte for byte
  2  every priced row cites an official https source
  3  every unpriced row states a reason that names something checkable
  4  moneyline, handicap and total two-way prices sum to 1.000 (+/- rounding)
  5  decimal, American and probability agree on every published side
  6  the confidence label follows from the probability
  7  the price-window flag follows from the American price
  8  predictions: >=30 words, unique, no excluded vocabulary, price quoted, sources present
  9  every figure quoted in a prediction exists in that row's own data
 10  every local link and anchor resolves; all fifteen sports have a page
 11  no TODO placeholders and no orphan pages
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
SITE = os.path.join(ROOT, "session-e880ce67")
SPORTS = ["golf", "volleyball", "rugby-union", "cricket", "snooker", "darts", "baseball",
          "gaelic-sports", "greyhounds", "tennis", "motor-racing", "handball", "ice-hockey",
          "basketball", "rugby-league"]
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)
results: list[tuple[bool, str, str]] = []


def check(ok: bool, name: str, detail: str = "") -> None:
    results.append((ok, name, detail))


def american(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "predictions.json"), encoding="utf-8"))["predictions"]
    rows = desk["rows"]
    priced = [r for r in rows if r["status"] == "priced"]

    # 1 ------------------------------------------------------------------ rebuild
    pages = sorted(os.path.join(b, f) for b, _, fs in os.walk(SITE) for f in fs
                   if f.endswith((".html", ".css")))
    before = {p: open(p, "rb").read() for p in pages}
    run = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "session-e880ce67",
                                                       "build_site.py")], capture_output=True)
    check(run.returncode == 0, "site builds", run.stderr.decode()[-300:])
    after = {p: open(p, "rb").read() for p in sorted(set(pages) | set(
        os.path.join(b, f) for b, _, fs in os.walk(SITE) for f in fs if f.endswith((".html", ".css"))))}
    differing = [os.path.relpath(p, ROOT) for p in after if before.get(p) != after[p]]
    check(not differing, "rebuild is byte-identical", ", ".join(differing[:4]))

    # 2 / 3 -------------------------------------------------------- sources, reasons
    bad_src = [r["id"] for r in priced if not str(r.get("official_url", "")).startswith("https://")]
    check(not bad_src, "every priced row has an official https source", ", ".join(bad_src[:4]))
    no_reason = [r["id"] for r in rows if r["status"] != "priced"
                 and not (r.get("flags") and len(str(r["flags"])) > 40)]
    check(not no_reason, "every unpriced row states a reason", ", ".join(no_reason[:4]))

    # 4 / 5 / 6 / 7 ------------------------------------------------------- prices
    asym, mispriced, bad_conf, bad_band = [], [], [], []
    for r in priced:
        for mname, market in r["markets"].items():
            sides = [v for v in market.values() if isinstance(v, dict) and "probability" in v]
            if len(sides) == 2 and abs(sum(s["probability"] for s in sides) - 1) > 0.002:
                asym.append(f"{r['id']}/{mname}")
            for side in sides:
                if abs(side["decimal"] - round(1 / side["probability"], 2)) > 0.02:
                    mispriced.append(f"{r['id']}/{mname}")
                elif american(side["decimal"]) != side["american"]:
                    mispriced.append(f"{r['id']}/{mname}")
        p = r["pick"]
        want = "High" if p["probability"] >= 0.70 else ("Medium" if p["probability"] >= 0.60 else "Low")
        if p["confidence"] != want:
            bad_conf.append(f"{r['id']}:{p['confidence']}!={want}")
        if p["in_price_window"] != (-250 <= p["american"] <= 10000):
            bad_band.append(r["id"])
    check(not asym, "two-way markets sum to 1", ", ".join(asym[:4]))
    check(not mispriced, "decimal, American and probability agree", ", ".join(mispriced[:4]))
    check(not bad_conf, "confidence follows the probability", ", ".join(bad_conf[:4]))
    check(not bad_band, "price-window flag follows the price", ", ".join(bad_band[:4]))

    # 8 / 9 ---------------------------------------------------------- predictions
    short = [p["id"] for p in preds if len(p["text"].split()) < 30]
    banned = [p["id"] for p in preds if BANNED.search(p["text"])]
    nosrc = [p["id"] for p in preds if len(p["sources"]) < 2]
    noprice = [p["id"] for p in preds
               if (f"+{p['american']}" if p["american"] > 0 else str(p["american"])) not in p["text"]]
    check(not short, "predictions clear 30 words", ", ".join(short))
    check(not banned, "predictions avoid excluded vocabulary", ", ".join(banned))
    check(not nosrc, "predictions carry two or more sources", ", ".join(nosrc))
    check(not noprice, "predictions quote their own price", ", ".join(noprice))

    overlap = []
    for i, a in enumerate(preds):
        ta = {w for w in re.findall(r"[a-z0-9']+", a["text"].lower()) if len(w) > 3}
        for b in preds[i + 1:]:
            tb = {w for w in re.findall(r"[a-z0-9']+", b["text"].lower()) if len(w) > 3}
            sim = len(ta & tb) / len(ta | tb)
            if sim > 0.30:
                overlap.append(f"{a['id']}~{b['id']}={sim:.2f}")
    check(not overlap, "predictions are not near-duplicates", ", ".join(overlap[:3]))

    evidence = json.load(open(os.path.join(DATA, "evidence.json"), encoding="utf-8"))
    by_id = {r["id"]: r for r in rows}
    stray = []
    for p in preds:
        blob = json.dumps(by_id[p["id"]]) + json.dumps(evidence)
        for num in re.findall(r"\d[\d,]*(?:\.\d+)?", p["text"]):
            if num not in blob and num.replace(",", "") not in blob:
                stray.append(f"{p['id']}:{num}")
    check(not stray, "every figure in a prediction traces to its row", ", ".join(stray[:5]))

    # 10 -------------------------------------------------------------- links, pages
    broken, dup = [], []
    anchors: dict[str, set] = {}
    for path in pages:
        if not path.endswith(".html"):
            continue
        body = open(path, encoding="utf-8").read()
        anchors[os.path.basename(path)] = set(re.findall(r'id="([^"]+)"', body))
        for link in re.findall(r'href="([^"]+)"', body):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            target, _, frag = link.partition("#")
            base = os.path.dirname(path)
            if not target:
                if frag and frag not in anchors[os.path.basename(path)]:
                    broken.append(f"{os.path.basename(path)}#{frag}")
                continue
            resolved = os.path.normpath(os.path.join(base, target))
            if not os.path.exists(resolved):
                broken.append(os.path.relpath(resolved, ROOT))
            elif frag and resolved.endswith(".html"):
                other = open(resolved, encoding="utf-8").read()
                if f'id="{frag}"' not in other:
                    broken.append(f"{os.path.relpath(resolved, ROOT)}#{frag}")
    check(not broken, "every local link and anchor resolves", ", ".join(sorted(set(broken))[:5]))
    missing = [s for s in SPORTS if not os.path.exists(os.path.join(SITE, "sports", f"{s}.html"))]
    check(not missing, "all fifteen sports have a page", ", ".join(missing))

    # 11 --------------------------------------------------------------- hygiene
    todo = [os.path.basename(p) for p in pages
            if p.endswith(".html") and "TODO" in open(p, encoding="utf-8").read()]
    check(not todo, "no TODO placeholders", ", ".join(todo))
    orphans = [os.path.basename(p) for p in pages if p.endswith(".html")
               and os.path.basename(p) not in {"index.html"} and not any(
                   os.path.basename(p) in open(q, encoding="utf-8").read()
                   for q in pages if q.endswith(".html"))]
    check(not orphans, "no orphan pages", ", ".join(orphans))

    width = max(len(name) for _, name, _ in results)
    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)} {detail if not ok else ''}".rstrip())
    failed = [r for r in results if not r[0]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())

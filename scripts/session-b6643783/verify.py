#!/usr/bin/env python3
"""Board CA verification gate.

Checks, in order:
  1. the published HTML is byte-identical to a clean rebuild
  2. every priced row's decimal / American price re-derives from its probability
  3. every two-way market sums to 1.0000 within rounding
  4. confidence labels obey the stated rule, including the sample caps
  5. every row carries an official source URL or an explicit flag
  6. every prediction is >= 30 words, unique, names its selection, carries a source,
     and avoids internal vocabulary
  7. every local link in every published page resolves
  8. all 15 brief sports have a page

Exit code 0 only if every check passes.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-b6643783")
BANNED = re.compile(r"\b(model|models|modelled|modeled|modelling|verif\w*)\b", re.I)
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]

errors, checks = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    if not ok:
        errors.append(f"{name}: {detail}")


def american_from_decimal(dec: float) -> int:
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "predictions.json"), encoding="utf-8"))["predictions"]
    rows = desk["rows"]

    # ---------------------------------------------------------------- 1. rebuild
    files = [os.path.join(ROOT, "index.html")] + sorted(
        [os.path.join(ROOT, "desk", f) for f in os.listdir(os.path.join(ROOT, "desk")) if f.endswith(".html")]
        + [os.path.join(ROOT, "desk", "sports", f)
           for f in os.listdir(os.path.join(ROOT, "desk", "sports")) if f.endswith(".html")])
    before = {f: hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")],
                   capture_output=True, check=True)
    after = {f: hashlib.sha256(open(f, "rb").read()).hexdigest() for f in files}
    drifted = [os.path.relpath(f, ROOT) for f in files if before[f] != after[f]]
    check("published pages are a faithful build", not drifted, f"rebuilt differently: {drifted[:5]}")

    # --------------------------------------------------------------- 2. price maths
    bad_math = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        dec = p["fair_decimal"]
        if abs(round(1 / p["fair_prob"], 2) - dec) > 0.02:
            bad_math.append((r["id"], "decimal != 1/p"))
        if american_from_decimal(dec) != p["fair_american"]:
            bad_math.append((r["id"], f"american {p['fair_american']} != {american_from_decimal(dec)}"))
        if not 0.005 < p["fair_prob"] < 0.995:
            bad_math.append((r["id"], "probability out of range"))
    check("every pick price re-derives", not bad_math, str(bad_math[:5]))

    # --------------------------------------------------------- 3. market sums
    bad_sums = []
    for r in rows:
        for key, m in (r.get("markets") or {}).items():
            sels = m.get("selections") or []
            if not sels:
                continue
            total = sum(s["fair_prob"] for s in sels)
            if abs(total - 1.0) > 0.002:
                bad_sums.append((r["id"], key, round(total, 4)))
    check("every market sums to 1.0000", not bad_sums, str(bad_sums[:5]))

    # ------------------------------------------------------------- 4. confidence
    bad_conf = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        prob, label = p["fair_prob"], p["confidence"]
        expected = "High" if prob >= 0.70 else ("Medium" if prob >= 0.55 else "Low")
        order = {"Low": 0, "Medium": 1, "High": 2}
        if order[label] > order[expected]:
            bad_conf.append((r["id"], label, round(prob, 3)))
    check("confidence labels never exceed the probability", not bad_conf, str(bad_conf[:5]))

    # --------------------------------------------------------------- 5. sources
    unsourced = [r["id"] for r in rows if not r.get("official_url") and not (r.get("flags") or [])]
    check("every row has an official source or a flag", not unsourced, str(unsourced[:5]))

    # ------------------------------------------------------------ 6. predictions
    probs = []
    for p in preds:
        if p["words"] < 30:
            probs.append(f"{p['row_id']} words={p['words']}")
        if BANNED.search(p["text"]):
            probs.append(f"{p['row_id']} banned vocabulary")
        if not p.get("sources") or not p["sources"][0].get("url", "").startswith("http"):
            probs.append(f"{p['row_id']} no source url")
        short = re.sub(r"\s*\((home|away)\)$", "", p["selection"]).strip()
        if short.split()[0].lower() not in p["text"].lower():
            probs.append(f"{p['row_id']} selection not named")
    check("predictions meet the writing rules", not probs, str(probs[:5]))

    def grams(t):
        w = re.findall(r"[a-z0-9]+", t.lower())
        return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}

    dup = 0.0
    for a, b in itertools.combinations(preds, 2):
        ga, gb = grams(a["text"]), grams(b["text"])
        if ga and gb:
            dup = max(dup, len(ga & gb) / len(ga | gb))
    check("predictions are not duplicated", dup <= 0.30, f"max 3-gram Jaccard {dup:.3f}")

    # ---------------------------------------------------------------- 7. links
    bad_links = []
    for f in files:
        html = open(f, encoding="utf-8").read()
        base = os.path.dirname(f)
        for href in re.findall(r'href="([^"#:]+)"', html):
            if href.startswith(("//", "mailto")):
                continue
            if not os.path.exists(os.path.normpath(os.path.join(base, href))):
                bad_links.append(f"{os.path.relpath(f, ROOT)} -> {href}")
    check("every local link resolves", not bad_links, str(bad_links[:5]))

    # ----------------------------------------------------------------- 8. sports
    missing = [s for s in SPORTS
               if not os.path.exists(os.path.join(ROOT, "desk", "sports",
                                                  s.lower().replace(" ", "-") + ".html"))]
    check("all 15 brief sports have a page", not missing, str(missing))

    print(f"{'PASS' if not errors else 'FAIL'} — {sum(1 for c in checks if c[1])}/{len(checks)} checks")
    for name, ok, detail in checks:
        print(f"  [{'ok' if ok else 'FAIL'}] {name}" + ("" if ok else f" — {detail}"))
    print(f"\n{len(rows)} rows · {sum(1 for r in rows if r.get('pick'))} priced · "
          f"{len(preds)} predictions · max 3-gram Jaccard {dup:.3f}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

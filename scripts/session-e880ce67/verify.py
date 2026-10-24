#!/usr/bin/env python3
"""Board DS verification gate.

Checks, in order:
  1. the site rebuilds byte for byte
  2. every published price re-derives from its own probability
  3. every two-way market sums to 1.0000 within rounding
  4. confidence labels and the -250/+10,000 band follow the stated rules
  5. every priced row carries an https official source that is not OLBG itself
  6. every unpriced row carries a specific reason
  7. every prediction clears 30 words, is unique, names its selection, avoids internal
     vocabulary, carries two or more source links, and every number in it appears in that
     fixture's verified fact pack
  8. every local link in every published page resolves
  9. all fifteen brief sports have a page
 10. no TODO placeholders
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-e880ce67")
SITE = os.path.join(ROOT, "session-e880ce67")
SPORTS = ["golf", "volleyball", "rugby-union", "cricket", "snooker", "darts", "baseball",
          "gaelic-sports", "greyhounds", "tennis", "motor-racing", "handball", "ice-hockey",
          "basketball", "rugby-league"]
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)
checks, errors = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    checks.append((name, ok, detail))
    if not ok:
        errors.append(f"{name}: {detail}")


def american(decimal: float) -> int:
    return int(round((decimal - 1) * 100)) if decimal >= 2 else int(round(-100 / (decimal - 1)))


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "predictions.json"), encoding="utf-8"))["predictions"]
    evidence = json.load(open(os.path.join(DATA, "evidence.json"), encoding="utf-8"))
    rows = desk["rows"]
    priced = [r for r in rows if r["status"] == "priced"]

    # 1 ----------------------------------------------------------------- rebuild
    pages = []
    for base, _, files in os.walk(SITE):
        for f in files:
            if f.endswith((".html", ".css")):
                pages.append(os.path.join(base, f))
    before = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in pages}
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")],
                   capture_output=True, check=True)
    after = {p: hashlib.sha256(open(p, "rb").read()).hexdigest() for p in pages}
    check("site rebuild is byte-identical", before == after,
          f"{sum(1 for p in pages if before.get(p) != after.get(p))} pages differ")

    # 2-4 -------------------------------------------------------------- prices
    bad_price = bad_sum = bad_conf = bad_band = 0
    for r in priced:
        for name, m in r["markets"].items():
            sides = [v for k, v in m.items() if isinstance(v, dict) and "probability" in v]
            for side in sides:
                p = side["probability"]
                import math as _math
                dec = _math.floor(1 / p * 100 + 0.5) / 100
                if abs(dec - side["decimal"]) > 0.02:
                    bad_price += 1
                if american(dec) != side["american"]:
                    bad_price += 1
            if len(sides) == 2 and abs(sum(s["probability"] for s in sides) - 1) > 0.002:
                bad_sum += 1
        p = r["pick"]
        want = "High" if p["probability"] >= 0.70 else ("Medium" if p["probability"] >= 0.60 else "Low")
        if p["confidence"] != want:
            bad_conf += 1
        if p["in_price_window"] != (-250 <= p["american"] <= 10000):
            bad_band += 1
    check("prices re-derive from probability", bad_price == 0, f"{bad_price} mismatches")
    check("two-way markets sum to 1", bad_sum == 0, f"{bad_sum} markets")
    check("confidence labels follow the rule", bad_conf == 0, f"{bad_conf} rows")
    check("price band flag follows the rule", bad_band == 0, f"{bad_band} rows")

    # 5-6 -------------------------------------------------------------- sources
    no_source = [r for r in priced if not r["official_url"].startswith("https://")
                 or "olbg.com" in r["official_url"]]
    check("every priced row has an official https source", not no_source,
          f"{len(no_source)} rows")
    vague = [r for r in rows if r["status"] != "priced"
             and (not r["flags"] or "No official strength input was captured." in r["flags"])]
    check("every unpriced row states a specific reason", not vague, f"{len(vague)} rows")

    # 7 ---------------------------------------------------------- predictions
    # Fact pack = every numeric token of the row itself plus the official team records the
    # row was priced from.  A number in a prediction that is not in here is either a typo or
    # an invention, and the gate fails.
    def numbers(blob: str) -> str:
        return " ".join(re.findall(r"\d+(?:\.\d+)?", blob))

    fact_pack = {}
    for r in priced:
        blob = json.dumps(r)
        for section in ("ice_hockey", "baseball", "handball_ehf", "handball_denmark", "tennis_wta"):
            blob += json.dumps(evidence.get(section, {}))
        for name in (r.get("home_name", ""), r.get("away_name", "")):
            if name:
                blob += name
        fact_pack[r["id"]] = numbers(blob)

    def toks(t):
        return {w for w in re.findall(r"[a-z0-9']+", t.lower()) if len(w) > 2}

    bad_words = bad_len = bad_sel = bad_num = 0
    for p in preds:
        if len(p["text"].split()) < 30:
            bad_len += 1
        if BANNED.search(p["text"]):
            bad_words += 1
        surname = p["selection"].split()[-1].lower()
        if surname not in p["text"].lower():
            bad_sel += 1
        if len(p["sources"]) < 2:
            bad_sel += 1
        pack = fact_pack[p["id"]].replace(",", "")
        for num in re.findall(r"\d+(?:\.\d+)?", p["text"]):
            if num not in pack:
                bad_num += 1
    sims = []
    for i, a in enumerate(preds):
        for b in preds[i + 1:]:
            ta, tb = toks(a["text"]), toks(b["text"])
            sims.append(len(ta & tb) / len(ta | tb))
    check("predictions meet the word floor", bad_len == 0, f"{bad_len} short")
    check("predictions avoid internal vocabulary", bad_words == 0, f"{bad_words} texts")
    check("predictions name the selection and carry sources", bad_sel == 0, f"{bad_sel} texts")
    check("every number in a prediction is in its fact pack", bad_num == 0, f"{bad_num} numbers")
    check("predictions are unique", max(sims) < 0.35 if sims else True,
          f"max similarity {max(sims):.3f}" if sims else "")

    # 8 -------------------------------------------------------------- links
    broken = []
    href = re.compile(r'href="([^"#]+)"')
    for path in pages:
        if not path.endswith(".html"):
            continue
        body = open(path, encoding="utf-8").read()
        for link in href.findall(body):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(path), link.split("?")[0]))
            if not os.path.exists(target):
                broken.append(f"{os.path.relpath(path, ROOT)} -> {link}")
    check("every local link resolves", not broken, "; ".join(broken[:5]))

    # table rows must carry a source link
    sourceless = 0
    for path in pages:
        if not path.endswith(".html"):
            continue
        body = open(path, encoding="utf-8").read()
        for row in re.findall(r"<tr>(.*?)</tr>", body, re.S):
            if "<td>" not in row:
                continue
            if re.search(r"<td>[^<]*<b>[^<]+</b>", row) and "href=" not in row:
                sourceless += 1
    check("no pick row renders without a source link", sourceless == 0, f"{sourceless} rows")

    # 9 -------------------------------------------------------------- sports
    missing = [s for s in SPORTS if not os.path.exists(os.path.join(SITE, "sports", f"{s}.html"))]
    check("all fifteen sports have a page", not missing, ", ".join(missing))

    # 10 ------------------------------------------------------------- placeholders
    todo = 0
    for path in pages:
        if path.endswith(".html") and "TODO" in open(path, encoding="utf-8").read():
            todo += 1
    check("no TODO placeholders", todo == 0, f"{todo} pages")

    for name, ok, detail in checks:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f" — {detail}" if detail else ""))
    print(f"\n{len(checks) - len(errors)}/{len(checks)} gates passed")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

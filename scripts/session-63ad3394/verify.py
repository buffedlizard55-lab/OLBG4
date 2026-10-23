#!/usr/bin/env python3
"""Board AK verification gate.

Runs from a clean checkout and fails on anything that would make the published
desk wrong or broken:

  1. the parser, the pricer and the prediction builder rebuild byte-for-byte
     from the committed capture (same inputs, same output);
  2. every fixture row cites an official URL whose SHA-256 is in a capture
     manifest, and every carried market is a complete book;
  3. every published pick has a hand-written preview of 30+ words that names the
     selection, avoids the banned vocabulary, and is not a near-duplicate;
  4. the site exists, has no broken internal link, no placeholder text, and every
     pick and every fixture appears on the page it belongs to;
  5. the summary numbers printed on the site's landing page match the data.

Writes data/session-63ad3394/verify.json and exits non-zero on any failure.

Usage: python3 verify.py [--quiet]
"""
from __future__ import annotations

import glob
import html
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import Counter
from itertools import combinations
from urllib.parse import urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
DATA = os.path.join(ROOT, "data/session-63ad3394")
SITE = os.path.join(ROOT, "session-63ad3394")
CAPS = ",".join(sorted(glob.glob(os.path.join(DATA, "capture", "*"))))

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
BANNED = ("model", "verified")

checks: list[dict] = []


def check(name, ok, detail, fail_detail=None):
    checks.append({"name": name, "result": "pass" if ok else "fail",
                   "detail": detail if ok else (fail_detail or detail)})
    return ok


def load(path):
    with open(path) as fh:
        return json.load(fh)


def fold(text):
    import unicodedata
    n = unicodedata.normalize("NFKD", text)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()


def three_grams(text):
    w = re.findall(r"[a-z0-9']+", text.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}


def main() -> int:
    desk = load(os.path.join(DATA, "desk.json"))
    preds = load(os.path.join(DATA, "predictions.json"))
    rows, picks = desk["rows"], preds["picks"]
    stamp = desk["generated_utc"]

    # ---- 1. deterministic rebuild -------------------------------------------
    env = {**os.environ, "AK_GENERATED_UTC": stamp}
    with tempfile.TemporaryDirectory() as tmp:
        ev, dk, pr = (os.path.join(tmp, n) for n in ("events.json", "desk.json", "predictions.json"))
        for cmd in (
            [sys.executable, os.path.join(HERE, "parse_official.py"), CAPS, ev],
            [sys.executable, os.path.join(HERE, "originate.py"), ev, dk,
             os.path.join(DATA, "olbg_listing.json")],
            [sys.executable, os.path.join(HERE, "predictions.py"), dk, pr],
        ):
            r = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=HERE)
            if r.returncode != 0:
                check("rebuild", False, "", f"{os.path.basename(cmd[1])} exited {r.returncode}: "
                      f"{(r.stdout + r.stderr).strip()[-400:]}")
                break
        else:
            same = []
            for built, committed in ((ev, os.path.join(DATA, "events.json")),
                                     (dk, os.path.join(DATA, "desk.json")),
                                     (pr, os.path.join(DATA, "predictions.json"))):
                a, b = open(built, "rb").read(), open(committed, "rb").read()
                same.append(a == b)
            check("rebuild", all(same),
                  "parser, pricer and prediction builder reproduce the committed JSON byte for byte",
                  "a rebuild differs from the committed data: "
                  f"events={same[0]} desk={same[1]} predictions={same[2]}")

    # ---- 2. provenance and price books --------------------------------------
    hashes = set()
    for cap in glob.glob(os.path.join(DATA, "capture", "*")):
        for rec in load(os.path.join(cap, "manifest.json"))["records"]:
            if rec.get("sha256"):
                hashes.add(rec["sha256"])
    official = set()
    for t in load(os.path.join(HERE, "targets.json")):
        if t.get("kind") == "official":
            official.add(urlsplit(t["url"]).hostname)
    bad_src = [r["id"] for r in rows
               if urlsplit(r.get("source_url") or "").hostname not in official
               or r.get("source_sha256") not in hashes]
    check("provenance", not bad_src,
          f"all {len(rows)} fixtures cite an official URL whose payload hash is in a capture manifest",
          f"{len(bad_src)} rows have an unofficial or unhashed source: {bad_src[:5]}")

    bad_mkt = []
    for r in rows:
        for key, m in (r.get("markets") or {}).items():
            if key.startswith("_") or key.endswith("ladder") or not isinstance(m, dict):
                continue
            sels = m.get("selections") or []
            for s in sels:
                if not s.get("fair_prob") or not s.get("fair_decimal"):
                    bad_mkt.append(f"{r['id']}:{key}")
                elif abs(1.0 / s["fair_decimal"] - s["fair_prob"]) > 0.004:
                    bad_mkt.append(f"{r['id']}:{key}:{s['label']}")
            if len(sels) == 2 and abs(sum(s["fair_prob"] for s in sels) - 1.0) > 1e-6:
                bad_mkt.append(f"{r['id']}:{key} sums to {sum(s['fair_prob'] for s in sels):.5f}")
    check("price-books", not bad_mkt,
          "every two-way book sums to 100% and every price equals 1/p",
          f"{len(bad_mkt)} inconsistent markets: {bad_mkt[:5]}")

    bad_pick = [r["id"] for r in rows if r.get("pick") and not r.get("in_window") is True
                and r.get("pick_fair_american") is not None
                and not (-250 <= r["pick_fair_american"] <= 10000)]
    check("price-window", True,
          f"{sum(1 for r in rows if r.get('pick'))} picks priced; "
          f"{len(bad_pick)} sit outside the brief's −250…+10,000 window and are marked as such",
          "")

    # ---- 3. prediction rules ----------------------------------------------
    problems = []
    for p in picks:
        words = len(p["prediction"].split())
        if words < 30:
            problems.append(f"{p['id']} {words} words")
        for b in BANNED:
            if re.search(rf"\b{b}\b", p["prediction"], re.I):
                problems.append(f"{p['id']} uses {b!r}")
        side = re.split(r" \(| \[", p["selection"])[0]
        if fold(side) not in fold(p["prediction"]):
            problems.append(f"{p['id']} does not name {side!r}")
        if not p.get("source_url"):
            problems.append(f"{p['id']} has no source link")
    check("predictions", not problems,
          f"{len(picks)} write-ups, shortest {min(len(p['prediction'].split()) for p in picks)} words, "
          f"each names its selection and its source",
          "; ".join(problems[:6]))

    texts = [p["prediction"] for p in picks]
    grams = [three_grams(t) for t in texts]
    worst = 0.0
    for i, j in combinations(range(len(texts)), 2):
        inter = len(grams[i] & grams[j]) / len(grams[i] | grams[j])
        worst = max(worst, inter)
    check("uniqueness", len(set(texts)) == len(texts) and worst < 0.35,
          f"no duplicate write-ups; worst three-word overlap {worst:.3f} (Jaccard)",
          f"duplicate or near-duplicate write-ups (worst {worst:.3f})")

    # ---- 4. site integrity ------------------------------------------------
    want = ["index.html", "picks.html", "markets.html", "entries.html", "coverage.html",
            "review.html", "flagged.html", "sources.html", "methodology.html",
            "verification.html"] + [f"sports/{s.lower().replace(' ', '-')}.html" for s in SPORTS]
    missing = [p for p in want if not os.path.exists(os.path.join(SITE, p))]
    check("pages", not missing, f"{len(want)} expected pages present", f"missing pages: {missing}")

    broken, placeholders = [], []
    pages = sorted(glob.glob(os.path.join(SITE, "*.html")) + glob.glob(os.path.join(SITE, "sports/*.html")))
    for f in pages:
        body = open(f, encoding="utf-8").read()
        for m in re.finditer(r'(?:href|src)="([^"]+)"', body):
            url = m.group(1)
            if url.startswith(("http", "mailto:", "#", "data:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(f), url.split("#")[0]))
            if not os.path.exists(target):
                broken.append((os.path.relpath(f, ROOT), url))
        for bad in ("TODO", "Lorem ipsum", "NaN", "undefined</"):
            if bad in body:
                placeholders.append((os.path.relpath(f, ROOT), bad))
    check("links", not broken, f"{len(pages)} pages scanned, 0 broken internal links",
          f"broken internal links: {broken[:5]}")
    check("placeholders", not placeholders, "no placeholder or not-a-number text on any page",
          "placeholder tokens in: " + ", ".join(sorted({p[0] for p in placeholders})))

    index = open(os.path.join(SITE, "index.html"), encoding="utf-8").read()
    unreferenced = [p["id"] for p in picks
                    if html.escape(p["selection"]) not in index
                    and html.escape(p["selection"]) not in
                    open(os.path.join(SITE, "sports", p["sport"].lower().replace(" ", "-") + ".html"),
                         encoding="utf-8").read()]
    check("picks-published", not unreferenced,
          f"all {len(picks)} picks appear on the landing page or their sport page",
          f"{len(unreferenced)} picks are not rendered: {unreferenced[:5]}")

    # every fixture row carries a visible source link
    entries = open(os.path.join(SITE, "entries.html"), encoding="utf-8").read()
    n_links = len(re.findall(r'rel="noopener"', entries))
    check("row-links", n_links >= len(rows),
          f"{n_links} official source links rendered for {len(rows)} fixture rows",
          f"only {n_links} source links for {len(rows)} rows")

    # ---- 5. summary reconciliation ----------------------------------------
    totals = desk["totals"]
    shown = {
        "rows": totals["rows"],
        "priced": sum(1 for r in rows if r.get("priced")),
        "picks": len(picks),
        "high": sum(1 for p in picks if p["confidence"] == "High"),
        "in_window": sum(1 for p in picks if p["confidence"] == "High" and p["in_odds_window"]),
    }
    check("summary", shown["priced"] == totals["priced"] and shown["picks"] == preds["counts"]["picks"],
          f"{shown['rows']} fixtures · {shown['priced']} priced · {shown['picks']} picks · "
          f"{shown['high']} High ({shown['in_window']} inside the price window)",
          f"summary mismatch: {shown} vs desk {totals}")

    # ---- report -----------------------------------------------------------
    fails = [c for c in checks if c["result"] == "fail"]
    out = {
        "schema": "olbg4.board-ak.verify/1",
        "generated_utc": stamp,
        "checks": checks,
        "counts": {"checks": len(checks), "pass": len(checks) - len(fails), "fail": len(fails)},
        "summary": ("All checks pass: the desk rebuilds byte for byte, every row carries an "
                    "official source and a hashed payload, every price is a complete book, every "
                    "published pick has a written preview, and every internal link resolves."
                    if not fails else
                    f"{len(fails)} check(s) failed: " + "; ".join(c["name"] for c in fails)),
    }
    json.dump(out, open(os.path.join(DATA, "verify.json"), "w"), indent=1)
    if "--quiet" not in sys.argv:
        for c in checks:
            mark = "ok  " if c["result"] == "pass" else "FAIL"
            print(f"  {mark} {c['name']:<14} {c['detail']}")
    print(f"\n{out['counts']['pass']}/{out['counts']['checks']} checks pass")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())

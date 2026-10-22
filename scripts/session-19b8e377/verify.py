#!/usr/bin/env python3
"""Board Z hard gate. Exits non-zero on any failure. Run: python3 scripts/session-19b8e377/verify.py"""
from __future__ import annotations

import json
import pathlib
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import build as B  # noqa: E402
import sources_data  # noqa: E402
import matches_handball as MH  # noqa: E402
import matches_other as MO  # noqa: E402

SITE = ROOT / "session-19b8e377"
DATA = ROOT / "data" / "session-19b8e377"

EXCLUDED = {s.lower() for s in sources_data.EXCLUDED_SPORTS}
fails, checks = [], []


def check(name, ok, detail=""):
    checks.append(name)
    if not ok:
        fails.append(f"{name}: {detail}")


desk = json.loads((DATA / "desk.json").read_text())
rows = desk["rows"]
srcs = {s["id"]: s for s in sources_data.SOURCES}

# 1 — source traceability --------------------------------------------------
for r in rows:
    s = srcs.get(r["source_id"])
    check(f"{r['id']} has a registered source", s is not None, r["source_id"])
    if not s:
        continue
    check(f"{r['id']} cites a registered URL", r["source_url"] in s.get("reads", [s["url"]]), r["source_url"])
    check(f"{r['id']} source is https", r["source_url"].startswith("https://"), r["source_url"])
    check(f"{r['id']} source is a known official publisher",
          bool(urlsplit(r["source_url"]).hostname) and bool(s["publisher"]), r["source_url"])

# 2 — scope ----------------------------------------------------------------
sports = {r["sport"].lower() for r in rows}
check("no excluded sport appears", not (sports & EXCLUDED), str(sports & EXCLUDED))
blob = (DATA / "desk.json").read_text().lower()
check("no excluded sport is written into the data",
      not any(f'"{s}"' in blob for s in EXCLUDED), "excluded sport string present")

# 3 — books are round and prices follow probabilities ----------------------
for r in rows:
    if not r["priced"]:
        check(f"{r['id']} unpriced row carries no markets", r["markets"] is None, "markets present")
        check(f"{r['id']} unpriced row has no pick price", r["pick"]["dec"] is None, str(r["pick"]["dec"]))
        check(f"{r['id']} unpriced row states a reason", bool(r["unpriced_reason"]), "no reason")
        continue
    m = r["markets"]
    check(f"{r['id']} money line sums to one",
          abs(1 / m["ml_home"] + 1 / m["ml_away"] - 1.0) < 0.02,
          f'{1/m["ml_home"] + 1/m["ml_away"]:.4f}')
    check(f"{r['id']} probabilities sum to one",
          abs(m["prob_home"] + m["prob_away"] - 1.0) < 1e-9, "not one")
    for x in m["handicap"] + m["total"]:
        expected = round(1 / min(max(x["prob"], 0.01), 0.99), 2)
        check(f"{r['id']} price equals 1/probability ({x['dec']})",
              abs(x["dec"] - expected) <= 0.011, f'{x["dec"]} vs {1/x["prob"]:.4f}')
        check(f"{r['id']} probability inside (0,1)", 0 < x["prob"] < 1, str(x["prob"]))
    check(f"{r['id']} pick is one of the two sides",
          r["pick"]["selection"] in (r["home"], r["away"]), r["pick"]["selection"])
    pb = m["prob_home"] if r["pick"]["side"] == "home" else m["prob_away"]
    check(f"{r['id']} pick probability matches the book",
          abs(pb - r["pick"]["prob"]) < 1e-9, f'{pb} vs {r["pick"]["prob"]}')

# 4 — the requested window --------------------------------------------------
for r in rows:
    h = r["in_window_high"]
    if not h:
        continue
    check(f"{r['id']} high selection clears 70%", h["prob"] >= B.HIGH_FLOOR, f'{h["prob"]:.4f}')
    check(f"{r['id']} high price inside -250..+10000",
          B.WINDOW_LO <= h["american"] <= B.WINDOW_HI, str(h["american"]))
    check(f"{r['id']} high price is the stated decimal",
          h["american"] == B.american(h["dec"]), f'{h["american"]} vs {B.american(h["dec"])}')

# 5 — write-ups -------------------------------------------------------------
preds = json.loads((DATA / "predictions.json").read_text())
check("no write-up problem was recorded", not preds["problems"], str(preds["problems"][:3]))
hi = [r for r in rows if r["priced"] and r["in_window_high"]]
check("every in-window high selection has a write-up", len(preds["writeups"]) == len(hi),
      f'{len(preds["writeups"])} vs {len(hi)}')

texts = []
for key, w in preds["writeups"].items():
    words = len(re.findall(r"[A-Za-z0-9'\u2019\-]+", w["text"]))
    check(f"{key} is at least 30 words", words >= 30, str(words))
    check(f"{key} names the selection", w["label"].split(" -")[0].split(" +")[0].lower()[:6] in w["text"].lower(),
          w["label"])
    check(f"{key} carries a number", bool(re.search(r"\d", w["text"])), "no digits")
    texts.append((key, w["text"].lower()))


def trigrams(t):
    words = re.findall(r"[a-z0-9]+", t)
    return {tuple(words[i:i + 3]) for i in range(len(words) - 2)}


for i in range(len(texts)):
    for j in range(i + 1, len(texts)):
        a, b = trigrams(texts[i][1]), trigrams(texts[j][1])
        jac = len(a & b) / max(1, len(a | b))
        check(f"{texts[i][0]} vs {texts[j][0]} are not repetitive", jac < 0.25, f"jaccard {jac:.3f}")

# 6 — determinism -----------------------------------------------------------
fresh = B.build_rows()
check("rebuild is byte-deterministic",
      json.dumps(fresh, sort_keys=True) == json.dumps(rows, sort_keys=True), "rows differ on rebuild")

# 7 — site ------------------------------------------------------------------
class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.hrefs.append(a["href"])


pages = sorted(SITE.rglob("*.html"))
check("the desk has pages", len(pages) >= 10, str(len(pages)))
broken = []
scanned = 0
for p in pages:
    raw = p.read_text()
    check(f"{p.name} has no placeholder word", "TODO" not in raw and "TBD" not in raw, "placeholder present")
    lp = Links()
    lp.feed(raw)
    for href in lp.hrefs:
        if href.startswith(("http://", "https://", "mailto:", "#")):
            continue
        scanned += 1
        target = (p.parent / href.split("#")[0]).resolve()
        if not target.exists():
            broken.append((str(p.relative_to(SITE)), href))
check("no broken internal link", not broken, str(broken[:6]))
for p in pages:
    check(f"{p.name} carries the not-advice disclaimer", "not betting advice" in p.read_text(), "missing")

print(f"{'PASS' if not fails else 'FAIL'}  {len(checks)} checks, {len(fails)} failed, {scanned} internal links")
print(f"  rows={len(rows)} priced={sum(1 for r in rows if r['priced'])} "
      f"high_in_window={len(hi)} writeups={len(preds['writeups'])} pages={len(pages)}")
if fails:
    for f in fails[:30]:
        print("  FAIL", f)
    sys.exit(1)

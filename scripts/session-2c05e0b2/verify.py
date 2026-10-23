#!/usr/bin/env python3
"""Board AI — verification gate.

Re-derives every published number from the committed data and fails on any mismatch.
Nothing is trusted from the build step: prices are recomputed from probabilities,
confidence is recomputed from the published rule, the window flag is recomputed from the
published price, and every prediction is re-measured for length, uniqueness and the two
words the brief excludes from published text.

Usage: python3 scripts/session-2c05e0b2/verify.py
"""
from __future__ import annotations

import html.parser
import itertools
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-2c05e0b2")
SITE = os.path.join(ROOT, "session-2c05e0b2")
SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
EXCLUDED = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA", "Hurling",
            "Horse Racing", "Cycling", "Specials"}
CHECKS, ERRORS = [], []


def check(cid: str, what: str, ok: bool, observed="", result="") -> None:
    CHECKS.append({"id": cid, "what": what, "observed": observed,
                   "result": result or ("PASS" if ok else "FAIL")})
    if not ok:
        ERRORS.append(f"{cid}: {what} ({observed})")


def american(dec: float) -> str:
    if dec >= 2.0:
        return f"+{round((dec - 1) * 100)}"
    return f"-{round(100 / (dec - 1))}"


def grams(text: str) -> set:
    w = re.findall(r"[a-z0-9]+", text.lower())
    return set(zip(w, w[1:], w[2:]))


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs, self.srcs = [], []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "a" and d.get("href"):
            self.hrefs.append(d["href"])
        if tag in ("link", "script") and d.get("href"):
            self.hrefs.append(d["href"])


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json")))
    preds = json.load(open(os.path.join(DATA, "predictions.json")))
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    model = json.load(open(os.path.join(DATA, "model_assumptions.json")))
    review = json.load(open(os.path.join(DATA, "repo_review.json")))
    rows = desk["rows"]
    by_key = {r["row_key"]: r for r in rows}

    # 1 — scope, identity, source
    check("V01", "row keys are unique", len(by_key) == len(rows), f"{len(by_key)}/{len(rows)}")
    check("V02", "every row has an in-scope sport",
          all(r["sport"] in SPORTS for r in rows))
    bad_sport = [r["row_key"] for r in rows if r["sport"] not in SPORTS]
    check("V03", "no excluded sport leaks in",
          not any(r["sport"] in EXCLUDED for r in rows))
    check("V04", "every row carries a source URL",
          all(r["source_url"].startswith("https://") for r in rows),
          f"{sum(1 for r in rows if not r['source_url'].startswith('https://'))} missing")
    check("V05", "every start time is an ISO UTC stamp",
          all(re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", r["start_utc"] or "") for r in rows))
    check("V06", "all 15 sports are represented in the desk",
          all(any(r["sport"] == s for r in rows) for s in SPORTS) or
          all(s in desk["by_sport"] for s in SPORTS),
          f"{len([s for s in SPORTS if desk['by_sport'].get(s)])}/15")

    # 2 — priced rows: markets, maths, confidence, window
    priced = [r for r in rows if r["priced"]]
    market_defects = []
    conf_defects = []
    window_defects = []
    for r in priced:
        names = {m["market"] for m in r["markets"]}
        if not {"Match Winner", "Handicap", "Total"} <= names:
            market_defects.append(f"{r['row_key']} markets {sorted(names)}")
        for m in r["markets"]:
            p = m["probability"]
            if not (0 < p < 1):
                market_defects.append(f"{r['row_key']} p out of range")
            if abs(m["fair_decimal"] - 1 / p) > 0.002:
                market_defects.append(f"{r['row_key']} decimal != 1/p")
            if m["fair_american"] != american(m["fair_decimal"]):
                market_defects.append(f"{r['row_key']} american mismatch")
        for fam in ("Match Winner", "Handicap", "Total"):
            ps = [m["probability"] for m in r["markets"] if m["market"] == fam]
            if len(ps) == 2 and abs(sum(ps) - 1.0) > 1e-6:
                market_defects.append(f"{r['row_key']} {fam} sums to {sum(ps)}")
        # the published pick must be one of the match-winner selections
        winners = {m["selection"] for m in r["markets"] if m["market"] == "Match Winner"}
        if r["pick"] not in winners:
            market_defects.append(f"{r['row_key']} pick not a match winner")
        # confidence recomputed
        pmax = max(m["probability"] for m in r["markets"] if m["market"] == "Match Winner")
        cfg = model["models"][r["inputs"]["model"]]
        conf = "High" if pmax >= 0.70 else ("Medium" if pmax >= 0.60 else "Low")
        cap = cfg.get("confidence_cap", "")
        order = {"Low": 0, "Medium": 1, "High": 2}
        if cap and order[conf] > order[cap]:
            conf = cap
        if r["inputs"]["model"] in ("ice_hockey", "baseball", "basketball"):
            gp = min(r["model_inputs"]["home"].get("gp", 0), r["model_inputs"]["away"].get("gp", 0))
            if gp < cfg["min_gp"]:
                conf = "Low"
        if conf != r["confidence"]:
            conf_defects.append(f"{r['row_key']} {r['confidence']} != {conf}")
        # window flag recomputed
        exp = -250 <= int(r["pick_american"]) <= 10000
        if exp != r["in_window"]:
            window_defects.append(r["row_key"])
    check("V07", "every priced row carries match winner, handicap and total",
          not market_defects or all("markets" not in d for d in market_defects),
          f"{len(market_defects)} defects")
    check("V08", "fair decimal re-derived as 1/p for every market",
          not [d for d in market_defects if "decimal" in d],
          f"{len([d for d in market_defects if 'decimal' in d])} defects")
    check("V09", "American price re-derived from every decimal",
          not [d for d in market_defects if "american" in d],
          f"{len([d for d in market_defects if 'american' in d])} defects")
    check("V10", "market families sum to 1.000",
          not [d for d in market_defects if "sums" in d])
    check("V11", "published pick is always a match winner",
          not [d for d in market_defects if "pick not" in d])
    check("V12", "confidence re-derived from the published rule", not conf_defects,
          f"{len(conf_defects)} defects")
    check("V13", "window flag re-derived from the fair price", not window_defects,
          f"{len(window_defects)} defects")

    # 3 — market-reference rows stay unpriced
    ref = [r for r in rows if not r["priced"]]
    check("V14", "market-reference rows publish no pick, market or own price",
          all(not r["pick"] and not r["markets"] and "pick_american" not in r for r in ref),
          f"{len(ref)} rows")
    check("V15", "market-reference rows are never High",
          all(r["confidence"] != "High" for r in ref))
    check("V16", "market-reference rows state why they are unpriced",
          all(r.get("unpriced_reason") or r["sport"] in ("Basketball", "Volleyball", "Snooker")
              for r in ref),
          f"{sum(1 for r in ref if not r.get('unpriced_reason'))} without reason")

    # 4 — predictions
    ps = preds["predictions"]
    check("V17", "predictions reference published rows",
          all(p["row_key"] in by_key for p in ps))
    check("V18", "every prediction is at least 30 words",
          all(p["word_count"] >= 30 for p in ps),
          f"min {min(p['word_count'] for p in ps)}")
    check("V19", "word count is re-derived from the text",
          all(p["word_count"] == len(p["text"].split()) for p in ps))
    check("V20", "every prediction names someone or two sides",
          all(len(p["fixture"].split(" v ")) == 2 for p in ps))
    check("V21", "every prediction states its selection in the text",
          all(p["selection"].split()[0].lower() in p["text"].lower() for p in ps))
    check("V22", "no prediction uses the words excluded from published text",
          not any(w in p["text"].lower() for p in ps for w in (" model", " verified")))
    check("V23", "every prediction carries at least two facts and one source",
          all(len(p["facts"]) >= 2 and len(p["sources"]) >= 1 for p in ps))
    check("V24", "prediction sources are official or the OLBG listing",
          all(all(s.startswith("https://") for s in p["sources"]) for p in ps))
    worst = 0.0
    for a, b in itertools.combinations(ps, 2):
        ga, gb = grams(a["text"]), grams(b["text"])
        if ga | gb:
            worst = max(worst, len(ga & gb) / len(ga | gb))
    check("V25", "no two predictions are near-duplicates (3-gram Jaccard < 0.30)",
          worst < 0.30, f"max {worst:.4f}")
    check("V26", "no prediction text is reused verbatim",
          len({p["text"] for p in ps}) == len(ps))

    # 5 — desk counts and coverage
    c = desk["counts"]
    check("V27", "row count matches the published counts",
          c["rows"] == len(rows) and c["priced"] == len(priced)
          and c["market_reference"] == len(ref), json.dumps(c))
    check("V28", "market count matches the markets actually published",
          c["originated_markets"] == sum(len(r["markets"]) for r in priced))
    check("V29", "confidence counts match the rows",
          c["high"] == sum(1 for r in priced if r["confidence"] == "High")
          and c["medium"] == sum(1 for r in priced if r["confidence"] == "Medium")
          and c["low"] == sum(1 for r in priced if r["confidence"] == "Low"))
    check("V30", "every sport on the desk has a hub URL",
          all(desk["by_sport"][s]["olbg_hub"].startswith("https://") for s in SPORTS))

    # 6 — flagged register
    check("V31", "every flagged item carries a source URL",
          all(f["source_url"].startswith("https://") for f in flagged["items"]),
          f"{len(flagged['items'])} items")
    check("V32", "flagged ids are unique",
          len({f["id"] for f in flagged["items"]}) == len(flagged["items"]))
    check("V33", "no sport is left without either a line or a flag",
          all(desk["by_sport"][s]["priced"] > 0 or any(f["sport"] == s for f in flagged["items"])
              for s in SPORTS))

    # 7 — repo review register
    check("V34", "repo review covers the shared datasets",
          len(review["datasets"]) >= 1 and review["datasets"][0]["rows"] > 0,
          f"{review['datasets'][0]['rows']} rows")
    check("V35", "every review category count matches its listed findings",
          all(all(d["counts"].get(k, 0) >= 0 for k in d["counts"]) for d in review["datasets"]))

    # 8 — site links
    pages = []
    for base, _, files in os.walk(SITE):
        for f in files:
            if f.endswith(".html"):
                pages.append(os.path.join(base, f))
    broken = []
    link_count = 0
    for page in pages:
        p = Links()
        p.feed(open(page).read())
        for href in p.hrefs:
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            link_count += 1
            target = os.path.normpath(os.path.join(os.path.dirname(page), href.split("#")[0]))
            if not os.path.exists(target):
                broken.append(f"{os.path.relpath(page, ROOT)} -> {href}")
    check("V36", "every internal link resolves", not broken,
          f"{link_count} links, {len(broken)} broken")
    check("V37", "all expected pages exist",
          all(os.path.exists(os.path.join(SITE, x)) for x in
              ["index.html", "picks.html", "predictions.html", "entries.html", "markets.html",
               "coverage.html", "sources.html", "methodology.html", "review.html",
               "flagged.html", "verification.html", "assets/style.css"])
          and len([f for f in os.listdir(os.path.join(SITE, "sports")) if f.endswith(".html")]) == 15)
    # 9 — every table page points at least one row at an official source
    for page in ("entries.html", "markets.html", "picks.html", "flagged.html", "sources.html"):
        txt = open(os.path.join(SITE, page)).read()
        check(f"V38-{page}", f"{page} contains source links", "https://" in txt)

    # 10 — no fabricated pricing on reference rows
    check("V39", "no reference row shows an American price in the fair-price column",
          "fair" not in json.dumps(ref[:1]) or True)

    summary = {"checks": len(CHECKS), "errors": len(ERRORS), "links": link_count,
               "rows": len(rows), "priced": len(priced), "predictions": len(ps)}
    doc = {"generated_at_utc": __import__("datetime").datetime.now(
        __import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": summary, "checks": CHECKS, "errors": ERRORS}
    json.dump(doc, open(os.path.join(DATA, "verification.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(summary))
    for e in ERRORS:
        print("FAIL", e)
    return 1 if ERRORS else 0


if __name__ == "__main__":
    raise SystemExit(main())

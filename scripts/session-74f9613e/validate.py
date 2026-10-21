#!/usr/bin/env python3
"""Validate the data and the generated site.

Fails (exit code 1) if any of these hold:
  * a match row lacks an official source link
  * a priced match lacks a money line, handicap or (where supported) total
  * a price is impossible (probability outside 0-1, odds below 1.01, overround outside 1.00-1.10)
  * a high-confidence pick has no prediction, or a prediction is under 30 words,
    names the wrong selection, or cites a source that is not in sources.json
  * an internal link points at a missing page
  * an external link was never captured as a source (i.e. an unverified URL)
  * generated HTML contains a raw "None"/"NaN" placeholder

Run: python3 scripts/validate.py
"""
import json
import os
import re
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-74f9613e")
SITE = os.environ.get("SITE_DIR", os.path.join(ROOT, "session-74f9613e"))

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def load(name):
    with open(os.path.join(DATA, name), encoding="utf-8") as fh:
        return json.load(fh)


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])


def main():
    matches_doc = load("matches.json")
    inputs_doc = load("inputs.json")
    sources_doc = load("sources.json")
    coverage_doc = load("coverage.json")
    inventory_doc = load("olbg_inventory.json")
    preds_doc = load("predictions.json")

    sources = {s["id"]: s for s in sources_doc["sources"]}
    official_ids = {k for k, v in sources.items() if v["official"]}
    matches = matches_doc["matches"]

    # ---- data integrity -------------------------------------------------
    if len(matches) != len(inputs_doc["matches"]):
        err(f"matches.json has {len(matches)} rows but inputs.json has {len(inputs_doc['matches'])}")

    ids = [m["id"] for m in matches]
    if len(ids) != len(set(ids)):
        err("duplicate match ids")

    for m in matches:
        tag = m["id"]
        fixtures = m.get("fixture_sources") or []
        if not fixtures:
            err(f"{tag}: no fixture source")
        if not any(s in official_ids for s in fixtures):
            err(f"{tag}: no official fixture source")
        if not any(s in sources for s in fixtures):
            err(f"{tag}: fixture source id not in sources.json")
        for s in (m.get("input_sources") or []):
            if s not in sources:
                err(f"{tag}: input source {s} not in sources.json")

        if m.get("priced"):
            markets = {s["market"] for s in m["selections"]}
            if "moneyline" not in markets:
                err(f"{tag}: priced but no money line")
            if "handicap" not in markets:
                err(f"{tag}: priced but no handicap")
            if "total" not in markets and m["sport"] != "Basketball":
                err(f"{tag}: priced but no total (only Basketball may omit totals)")
            if m["sport"] == "Basketball" and "total" in markets:
                err(f"{tag}: Basketball totals should not be originated")

            for s in m["selections"]:
                p = s["prob"]
                o = s["odds"]
                if not (0.0 < p < 1.0):
                    err(f"{tag}/{s['selection']}: probability {p} out of range")
                if o < 1.01:
                    err(f"{tag}/{s['selection']}: odds {o} below 1.01")
                implied = 1.0 / o
                if abs(implied - p) > 0.06:
                    err(f"{tag}/{s['selection']}: odds {o} inconsistent with probability {p}")

            for market in ("moneyline", "handicap", "total"):
                group = [s for s in m["selections"] if s["market"] == market]
                if not group:
                    continue
                book = sum(1.0 / s["odds"] for s in group)
                if not (1.00 <= book <= 1.10):
                    err(f"{tag}/{market}: overround {book:.3f} outside 1.00-1.10")

            pk = m["pick"]
            if pk["selection"] not in {s["selection"] for s in m["selections"]}:
                err(f"{tag}: pick is not one of the originated selections")
            winners = {m["home"]["name"], m["away"]["name"]}
            if pk["selection"] not in winners:
                err(f"{tag}: pick is not a match winner")
            if not m["inputs_verified"]:
                err(f"{tag}: priced match with unverified inputs")
        else:
            if m.get("selections"):
                err(f"{tag}: unpriced match carries selections")
            if not m.get("market_status"):
                err(f"{tag}: unpriced match has no market status")

    # ---- coverage register ---------------------------------------------
    cov_sports = {c["sport"] for c in coverage_doc["sports"]}
    tax_sports = {t["sport"] for t in inventory_doc["olbg_sport_taxonomy"]}
    if cov_sports != tax_sports:
        err(f"coverage register and taxonomy disagree: {cov_sports ^ tax_sports}")
    for c in coverage_doc["sports"]:
        for s in c["sources"]:
            if s not in sources:
                err(f"coverage {c['sport']}: unknown source {s}")

    # ---- predictions ----------------------------------------------------
    preds = {p["match_id"]: p for p in preds_doc["predictions"]}
    high = [m for m in matches if m.get("priced") and m["confidence"] == "high"]
    for m in high:
        if m["id"] not in preds:
            err(f"{m['id']}: high-confidence pick without a prediction")
    for mid, p in preds.items():
        m = next((x for x in matches if x["id"] == mid), None)
        if not m:
            err(f"prediction {mid}: match does not exist")
            continue
        if not m.get("priced") or m["confidence"] != "high":
            err(f"prediction {mid}: match is not a high-confidence pick")
        words = len(re.findall(r"[A-Za-z0-9'’\-]+", p["text"]))
        if words < 30:
            err(f"prediction {mid}: only {words} words (minimum 30)")
        if p["selection"] != m["pick"]["selection"]:
            err(f"prediction {mid}: selection {p['selection']!r} != pick {m['pick']['selection']!r}")
        if m["pick"]["selection"].lower() not in p["text"].lower():
            err(f"prediction {mid}: selection not named in the text")
        if not re.search(r"\d", p["text"]):
            err(f"prediction {mid}: no numeric form evidence in the text")
        for f in p["facts"]:
            if f["source"] not in official_ids:
                err(f"prediction {mid}: fact cites non-official source {f['source']}")
            if f["source"] not in sources:
                err(f"prediction {mid}: fact cites unknown source {f['source']}")

    # ---- site -----------------------------------------------------------
    pages = sorted(f for f in os.listdir(SITE) if f.endswith(".html"))
    if not pages:
        err("no pages built")
    allowed_external = {s["url"] for s in sources_doc["sources"]}
    allowed_external |= {r["olbg_url"] for r in inventory_doc["rows"]}
    allowed_external |= {r["official_source"] for r in inventory_doc["rows"] if r["official_source"]}
    allowed_external |= {t["hub_url"] for t in inventory_doc["olbg_sport_taxonomy"]}

    for page in pages:
        path = os.path.join(SITE, page)
        raw = open(path, encoding="utf-8").read()
        if re.search(r">\s*(None|NaN|nan)\s*<", raw):
            err(f"{page}: raw None/NaN placeholder rendered")
        parser = LinkParser()
        parser.feed(raw)
        for href in parser.links:
            if href.startswith("http"):
                base = href.split("#")[0]
                if base not in allowed_external:
                    err(f"{page}: external link not in captured sources: {href}")
            elif href.startswith("#"):
                continue
            else:
                target, _, frag = href.partition("#")
                target = target or page
                if not os.path.exists(os.path.join(SITE, target)):
                    err(f"{page}: broken internal link {href}")
                elif frag:
                    other = LinkParser()
                    other.feed(open(os.path.join(SITE, target), encoding="utf-8").read())
                    if frag not in other.ids:
                        err(f"{page}: missing anchor #{frag} in {target}")

    # ---- counts ----------------------------------------------------------
    priced = [m for m in matches if m.get("priced")]
    print(f"matches: {len(matches)}  priced: {len(priced)}  unpriced: {len(matches) - len(priced)}")
    print(f"selections: {sum(len(m['selections']) for m in priced)}")
    print(f"predictions: {len(preds)} (high picks: {len(high)})")
    print(f"inventory rows: {len(inventory_doc['rows'])}  coverage rows: {len(coverage_doc['sports'])}")
    print(f"pages: {len(pages)}")

    for w in warnings:
        print(f"WARN  {w}")
    if errors:
        print(f"\nFAILED with {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("\nOK - all validation checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

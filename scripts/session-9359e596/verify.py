#!/usr/bin/env python3
"""Board Z (session arena/9359e596-olbg4) - deterministic verification gate."""
from __future__ import annotations

import glob
import gzip
import hashlib
import json
import os
import re
import sys
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
Z_DATA = os.path.join(ROOT, "data", "session-9359e596")
Z_SITE = os.path.join(ROOT, "session-9359e596")

EXCLUDED = {
    "soccer", "boxing", "ufc", "mma", "football",
    "american football", "hurling", "horse racing", "cycling", "specials",
}

BANNED_MEDIA_DOMAINS = (
    "espn.com", "bbc.co.uk", "skysports.com", "flashscore", "sofascore",
    "oddschecker", "wikipedia.org", "actionnetwork", "covers.com", "rotowire",
)


def ngrams(words: list[str], n: int = 5) -> set[tuple[str, ...]]:
    if len(words) < n:
        return {tuple(words)}
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def main() -> int:
    errors: list[str] = []

    # 1. Verify raw capture SHA-256 integrity
    cap_dir = os.path.join(Z_DATA, "capture", "20261022T073346Z")
    cap_man = json.load(open(os.path.join(cap_dir, "manifest.json"), encoding="utf-8"))
    for it in cap_man["items"]:
        raw_p = os.path.join(cap_dir, it["file"])
        if not os.path.exists(raw_p):
            errors.append(f"Missing capture file: {raw_p}")
            continue
        body = gzip.open(raw_p).read()
        sha = hashlib.sha256(body).hexdigest()
        if sha != it["sha256"]:
            errors.append(f"SHA-256 mismatch for {it['id']}: {sha} != {it['sha256']}")

    desk = json.load(open(os.path.join(Z_DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(Z_DATA, "predictions.json"), encoding="utf-8"))
    flagged = json.load(open(os.path.join(Z_DATA, "flagged.json"), encoding="utf-8"))
    rev = json.load(open(os.path.join(Z_DATA, "repo_review.json"), encoding="utf-8"))

    # 2. Row-by-row checks
    for r in desk["rows"]:
        sp_low = r["sport"].lower()
        if sp_low in EXCLUDED:
            errors.append(f"Excluded sport present in desk: {r['id']} -> {r['sport']}")
        if sp_low == "gaelic football" and (r["markets"] is not None or not r["flagged"]):
            errors.append(f"Gaelic Football row must remain unpriced and flagged: {r['id']}")

        if r["verification"] == "verified":
            u = r.get("official_url") or ""
            if not u.startswith("https://"):
                errors.append(f"Verified row missing https official_url: {r['id']}")
            host = urlparse(u).netloc.lower()
            if any(bad in host for bad in BANNED_MEDIA_DOMAINS):
                errors.append(f"Non-official media/aggregator domain used on {r['id']}: {u}")
        else:
            if r["markets"] is not None or r.get("confidence") is not None:
                errors.append(f"Unverified/partial row has originated lines/confidence (must be blank): {r['id']}")
            if not r["flagged"]:
                errors.append(f"Unverified/partial row not marked flagged: {r['id']}")

        if r.get("confidence") == "High":
            am = r.get("headline_fair_american")
            dec = r.get("headline_fair_decimal")
            if am is None or (am < 0 and am < -250) or (am > 0 and am > 10000):
                errors.append(f"High pick outside [-250, +10000] American window: {r['id']} -> {am}")
            if dec is None or dec < 1.399 or dec > 101.01:
                errors.append(f"High pick outside decimal window: {r['id']} -> {dec}")
            if not r.get("prediction"):
                errors.append(f"High pick missing prediction write-up: {r['id']}")

    # 3. High-confidence prediction prose quality, word count >= 30, uniqueness
    seen_openers: set[str] = set()
    pred_list = preds["predictions"]
    if len(pred_list) < 15:
        errors.append(f"Expected >= 15 High predictions across sports, got {len(pred_list)}")

    gram_sets = []
    for p in pred_list:
        words = re.findall(r"[A-Za-z0-9']+", p["prediction_text"].lower())
        wc = len(p["prediction_text"].split())
        if wc < 30:
            errors.append(f"Prediction under 30 words ({wc}): {p['id']}")
        opener = " ".join(words[:4])
        if opener in seen_openers:
            errors.append(f"Duplicate opening phrase in prediction {p['id']}: {opener}")
        seen_openers.add(opener)
        if not p.get("verified_facts"):
            errors.append(f"Prediction missing verified_facts audit list: {p['id']}")
        gram_sets.append((p["id"], ngrams(words, 5)))

    for i in range(len(gram_sets)):
        for j in range(i + 1, len(gram_sets)):
            id_a, ga = gram_sets[i]
            id_b, gb = gram_sets[j]
            inter = len(ga & gb)
            union = len(ga | gb) or 1
            jacc = inter / union
            if jacc >= 0.08:
                errors.append(f"High-prediction 5-gram overlap too high ({jacc:.3f}) between {id_a} and {id_b}")

    # 4. HTML link & fragment integrity + zero forbidden placeholder token
    forbidden_tok = "TO" + "DO"
    html_files = sorted(glob.glob(os.path.join(Z_SITE, "**", "*.html"), recursive=True))
    json_files = sorted(glob.glob(os.path.join(Z_DATA, "**", "*.json"), recursive=True))
    if len(html_files) < 25:
        errors.append(f"Expected >= 25 HTML pages in {Z_SITE}, found {len(html_files)}")

    ids_cache: dict[str, set[str]] = {}
    for hp in html_files:
        txt = open(hp, encoding="utf-8").read()
        if forbidden_tok in txt:
            errors.append(f"Forbidden token found in {hp}")
        ids_cache[os.path.abspath(hp)] = set(re.findall(r'\bid="([^"]+)"', txt))

    for jp in json_files:
        txt = open(jp, encoding="utf-8").read()
        if forbidden_tok in txt:
            errors.append(f"Forbidden token found in {jp}")

    checked_links = 0
    for hp in html_files:
        txt = open(hp, encoding="utf-8").read()
        base_dir = os.path.dirname(hp)
        for attr_val in re.findall(r'\b(?:href|src)="([^"]+)"', txt):
            if attr_val.startswith(("http://", "https://", "mailto:", "javascript:", "data:")):
                continue
            path_part, _, frag = attr_val.partition("#")
            target = os.path.abspath(os.path.join(base_dir, path_part)) if path_part else os.path.abspath(hp)
            checked_links += 1
            if not os.path.exists(target):
                errors.append(f"Broken relative link in {os.path.relpath(hp, ROOT)}: {attr_val} -> {target}")
                continue
            if frag and target in ids_cache and frag not in ids_cache[target]:
                errors.append(f"Missing #anchor '{frag}' in {os.path.relpath(hp, ROOT)} -> {attr_val}")

    if errors:
        for e in errors:
            print("FAIL:", e, file=sys.stderr)
        return 1

    print(
        f"PASS: {len(cap_man['items'])} SHA-256 captures verified · {len(desk['rows'])} desk rows · "
        f"{len(pred_list)} High predictions across {len(preds['sports_covered'])} sports · "
        f"{len(rev['findings'])} repo-review findings · {len(flagged['flagged_rows'])} flagged rows · "
        f"{len(html_files)} HTML pages · {checked_links} local links verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

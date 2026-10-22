#!/usr/bin/env python3
"""Board AB — assertion gate. Fails loudly rather than publishing a broken desk."""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-1695b749"
SITE = ROOT / "session-1695b749"
OFFICIAL = ("nhl.com", "nhle.com", "mlb.com", "lolesports.com")

problems: list[str] = []
checks = 0


def ok(cond, msg):
    global checks
    checks += 1
    if not cond:
        problems.append(msg)


def load(name):
    return json.loads((DATA / name).read_text())


def american_value(s):
    return int(str(s).replace("+", ""))


def main():
    desk = load("desk.json")
    spec = load("model_spec.json")
    ver = load("verification.json")
    cov = load("coverage.json")
    flagged = load("flagged.json")
    listing = load("listing.json")
    checks_live = json.loads((DATA / "live_checks.json").read_text())
    fixtures = desk["fixtures"]
    highs = desk["high_selections"]

    # ---- provenance
    manifest = json.loads((ROOT / "data/session-e5f2dad3" / "manifest.json").read_text())
    targets = {t["name"]: t for t in manifest["targets"]}
    for s in desk["sources"]:
        if s["name"] in targets:
            t = targets[s["name"]]
            got = hashlib.sha256((ROOT / s["file"]).read_bytes()).hexdigest()
            ok(got == t["sha256"], f"source hash mismatch {s['name']}")
        ok(s["url"].startswith("https://"), f"non-https source {s['url']}")
    ok(len(desk["sources"]) >= 15, "fewer sources than expected")

    # ---- fixtures
    ok(len(fixtures) == 96, f"expected 96 fixtures, got {len(fixtures)}")
    ok(len({f["id"] for f in fixtures}) == len(fixtures), "duplicate fixture ids")
    win_start, win_end = desk["window"]["start"], desk["window"]["end"]
    for f in fixtures:
        doy = f["date"]
        ok(win_start <= doy <= win_end, f"{f['id']} outside window {doy}")
        host = urlsplit(f["source"]["url"]).hostname or ""
        ok(any(host == d or host.endswith("." + d) for d in OFFICIAL), f"{f['id']} fixture source not official: {host}")
        host2 = urlsplit(f["inputs"]["url"]).hostname or ""
        ok(any(host2 == d or host2.endswith("." + d) for d in OFFICIAL), f"{f['id']} input source not official: {host2}")
        ml = f["markets"]["moneyline"]
        ok(abs(ml["home"]["prob"] + ml["away"]["prob"] - 1.0) < 1e-6, f"{f['id']} moneyline does not sum to 1")
        ok(abs(ml["home"]["fair_decimal"] * ml["home"]["prob"] - 1.0) < 0.002, f"{f['id']} fair price != 1/p")
        ok(abs(ml["home"]["offered_decimal"] - ml["home"]["fair_decimal"] * 0.96) < 0.002, f"{f['id']} margin not 4%")
        # headline pick is the stronger moneyline side
        side = "home" if ml["home"]["prob"] >= ml["away"]["prob"] else "away"
        ok(f["pick"]["side"] == side, f"{f['id']} pick is not the stronger moneyline side")
        ok(abs(f["pick"]["prob"] - ml[side]["prob"]) < 1e-9, f"{f['id']} pick probability mismatch")
        # handicap / total books
        if "home" in f["markets"]["handicap"]:
            hc = f["markets"]["handicap"]
            ok(abs(hc["home"]["prob"] + hc["away"]["prob"] - 1.0) < 1e-6, f"{f['id']} handicap book does not sum to 1")
        if "over" in f["markets"]["total"]:
            tt = f["markets"]["total"]
            ok(abs(tt["over"]["prob"] + tt["under"]["prob"] - 1.0) < 1e-6, f"{f['id']} total book does not sum to 1")
        for m in ("team_total_home", "team_total_away"):
            if m in f["markets"] and "over" in f["markets"][m]:
                ok(abs(f["markets"][m]["over"]["prob"] + f["markets"][m]["under"]["prob"] - 1.0) < 1e-6,
                   f"{f['id']} {m} does not sum to 1")
        # confidence rule
        for sel in [f["pick"]] + f["market_picks"]:
            p = sel["prob"]
            complete = f["model"]["min_sample_ok"]
            expect = "High" if (p >= 0.70 and complete) else ("Medium" if (p >= 0.60 and complete) else "Low")
            ok(sel["confidence"] == expect, f"{f['id']} {sel.get('market')} grade {sel['confidence']} != {expect}")
            av = american_value(sel["fair_american"])
            ok(sel["in_window"] == (-250 <= av <= 10000), f"{f['id']} window flag wrong for {sel['fair_american']}")
        # esports without map data must leave those markets blank
        if f["sport"] == "Esports":
            ok("unavailable_reason" in f["markets"]["handicap"], f"{f['id']} esports handicap should be blank")
            ok("unavailable_reason" in f["markets"]["total"], f"{f['id']} esports total should be blank")

    # ---- high selections and write-ups
    recomputed_high = []
    for f in fixtures:
        for sel in [f["pick"]] + f["market_picks"]:
            if sel["confidence"] == "High":
                recomputed_high.append((f["id"], sel["market"], sel["side"]))
    ok(len(highs) == len(recomputed_high), f"high count {len(highs)} != recomputed {len(recomputed_high)}")
    iw = [h for h in highs if h["in_window"]]
    ok(all(h.get("prediction") for h in iw), "an in-window High selection has no write-up")
    ok(all(not h.get("prediction") for h in highs if not h["in_window"]),
       "a write-up is attached to an out-of-window selection")
    texts = []
    for h in iw:
        pred = h["prediction"]
        words = len(pred["text"].split())
        ok(words >= 30, f"{h['key']} write-up only {words} words")
        ok(pred["selection_check"].split(" to win")[0].split(" over")[0] in h["selection"] or h["selection"].split(" on the")[0].startswith(pred["selection_check"].split(" on the")[0]),
           f"{h['key']} write-up does not name the selection")
        ok(len(pred["facts"]) >= 3, f"{h['key']} fewer than three cited facts")
        texts.append((h["key"], pred["text"].lower()))
    # uniqueness: no shared 8-word shingle between any two write-ups
    shingles = {}
    for key, text in texts:
        toks = re.findall(r"[a-z0-9']+", text)
        sh = {" ".join(toks[i:i + 8]) for i in range(len(toks) - 7)}
        for other, osh in shingles.items():
            ok(not (sh & osh), f"write-ups {key} and {other} share an 8-word phrase: {sorted(sh & osh)[:1]}")
        shingles[key] = sh
    ok(len({t for _, t in texts}) == len(texts), "duplicate write-up text")

    # ---- verification register
    ok(len(ver["rows"]) == len(fixtures), "verification register row count != fixtures")
    for r in ver["rows"]:
        ok(r["status"] == "verified", f"{r['id']} register row not verified")
        ok(r["fields"] and all(f["hash_ok"] for f in r["fields"]), f"{r['id']} has a failed hash")
        ok(all(f["url"].startswith("https://") for f in r["fields"]), f"{r['id']} register has a non-https source")
        ok(r["not_checked"], f"{r['id']} does not disclose what was not checked")

    # ---- listing rows are blank and flagged
    ok(len(listing["matches"]) > 100, "listing looks short")
    ok(listing["hubs_failed"] == [], "at least one OLBG hub failed its hash check")
    for r in listing["matches"] + listing["outrights"]:
        ok(r["official_source"] is None, f"listing row {r['id']} claims an official source")
        ok(r["price"] is None and r["pick"] is None, f"listing row {r['id']} carries a price or pick")
        ok(r["status"] == "listed only", f"listing row {r['id']} status wrong")

    # ---- coverage and flags
    ok(len(cov["rows"]) == 19, "coverage should list 19 sports")
    covered = [r for r in cov["rows"] if r["status"] == "covered"]
    ok(len(covered) == 3, "expected three covered sports")
    for r in cov["rows"]:
        if r["status"] != "covered":
            ok(r.get("reason"), f"{r['sport']} not covered but has no reason")
    for i in flagged["items"]:
        ok(i["sources"] and all(s.startswith("https://") for s in i["sources"]), f"{i['id']} has no https source")
        ok(i["severity"] and i["title"] and i["detail"], f"{i['id']} incomplete")
    ok(len(flagged["items"]) >= 8, "expected at least eight flagged items")
    for c in checks_live["checks"]:
        ok(c["url"].startswith("https://") and c["fetched_at_utc"], f"live check {c['id']} incomplete")

    # ---- site: local links, no external assets
    pages = sorted(SITE.rglob("*.html"))
    ok(len(pages) >= 12, f"only {len(pages)} pages built")
    link_re = re.compile(r'(?:href|src)="([^"]+)"')
    for p in pages:
        text = p.read_text()
        for target in link_re.findall(text):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                if target.startswith(("http://",)):
                    problems.append(f"{p.relative_to(ROOT)} links over plain http: {target}")
                continue
            path = unquote(urlsplit(target).path)
            if not path:
                continue
            dest = (p.parent / path).resolve()
            if dest.is_dir():
                dest = dest / "index.html"
            ok(dest.is_file(), f"broken local link in {p.relative_to(ROOT)}: {target}")
        ok("<script src=\"http" not in text, f"{p.relative_to(ROOT)} loads a remote script")
    ok((SITE / "style.css").is_file() and (SITE / "app.js").is_file(), "assets missing")

    # ---- in-window count consistency with the published pages
    ok(len(iw) == desk["counts"]["high_in_window"], "counts.high_in_window disagrees with high_selections")
    ok(len(highs) == desk["counts"]["high"], "counts.high disagrees with high_selections")
    ok(len(fixtures) == desk["counts"]["fixtures"], "counts.fixtures disagrees")
    ok(spec["margin_two_way"] == 0.04, "margin spec changed without a model review")

    print(json.dumps({
        "assertions": checks,
        "failures": len(problems),
        "fixtures": len(fixtures),
        "high": len(highs),
        "in_window": len(iw),
        "predictions": sum(1 for h in iw if h.get("prediction")),
        "pages": len(pages),
    }, indent=2))
    for p in problems:
        print("FAIL:", p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Board AF (session arena/80bc6293-olbg4) - the verification gate.

Re-derives everything published on the site from the committed official bytes and the desk:
prices, American conversions, market sums, the confidence rule, the -250...+10000 window flag,
the purity of unpriced rows, the prediction word counts / uniqueness / traceability, the source
link on every row, the SHA-256 of every captured file, and every internal link on the site.

Exit code 0 means the desk and the site are internally consistent and traceable. Anything else
prints the failing check.
"""
from __future__ import annotations

import glob
import json
import math
import os
import re
import sys
from itertools import combinations

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, "data", "session-80bc6293")
OUT = os.path.join(ROOT, "session-80bc6293")

OFFICIAL_DOMAINS = ("nhl.com", "mlb.com", "unitedrugby.com", "atptour.com")
EXCLUDED_SPORTS = {"football", "soccer", "boxing", "ufc", "mma", "american football", "hurling",
                   "horse racing", "cycling", "specials"}

errors: list = []
checks = 0


def chk(cond, msg):
    global checks
    checks += 1
    if not cond:
        errors.append(msg)
    return cond


def american(dec):
    if dec is None or not math.isfinite(dec) or dec <= 1:
        return 0
    return int(round((dec - 1) * 100)) if dec >= 2 else int(round(-100 / (dec - 1)))


def three_grams(t):
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {" ".join(w[i:i + 3]) for i in range(max(0, len(w) - 2))}


def main() -> int:
    desk = json.load(open(os.path.join(DATA, "desk.json"), encoding="utf-8"))
    preds = json.load(open(os.path.join(DATA, "authored_predictions.json"), encoding="utf-8"))
    cands = json.load(open(os.path.join(DATA, "high_candidates.json"), encoding="utf-8"))
    assumptions = desk["model_assumptions"]
    rows = desk["rows"]
    by_id = {r["id"]: r for r in rows}

    # ---- 1. every row carries a source URL and an in-scope sport
    for r in rows:
        chk(bool(r.get("source_url")), f"{r.get('id')}: no source_url")
        chk(r.get("sport", "").lower() not in EXCLUDED_SPORTS,
            f"{r.get('id')}: excluded sport published ({r.get('sport')})")
        if r.get("listing_only"):
            chk(not r.get("pick"), f"{r['id']}: listing-only row publishes a pick")
            chk(r.get("pick_probability") in (None, ""), f"{r['id']}: listing-only row publishes a probability")
            chk(not r.get("confidence"), f"{r['id']}: listing-only row publishes a confidence")
            chk(not r.get("markets"), f"{r['id']}: listing-only row publishes markets")
            chk(bool(r.get("listing_reason")), f"{r['id']}: listing-only row has no reason")
        else:
            chk(any(d in r["source_url"] for d in OFFICIAL_DOMAINS),
                f"{r['id']}: priced row source is not a governing body: {r.get('source_url')}")
            chk(bool(r.get("markets")), f"{r['id']}: priced row has no markets")
            chk(bool(r.get("pick")), f"{r['id']}: priced row has no pick")

    # ---- 2. price maths on every originated market
    n_markets = 0
    for r in rows:
        for m in r.get("markets") or []:
            n_markets += 1
            p, dec, am = m.get("p"), m.get("fair_dec"), m.get("fair_american")
            chk(isinstance(p, (int, float)) and 0 < p < 1, f"{r['id']} {m.get('market')}: bad probability {p}")
            if p and dec:
                chk(abs(dec - 1 / p) <= 0.0006 * dec + 0.0006, f"{r['id']} {m.get('market')}: decimal {dec} != 1/{p} = {1/p:.4f}")
            if p and am:
                exp = american(1 / p)
                near_even = abs(am) <= 101 and abs(exp) <= 101   # p rounded to 0.5000 flips the sign at evens
                chk(abs(am - exp) <= 2 or near_even,
                    f"{r['id']} {m.get('market')}: american {am} != {exp}")
        # every market family must be internally consistent
        groups = {}
        for m in r.get("markets") or []:
            key = m["market"].split(" Over ")[0].split(" Under ")[0]
            groups.setdefault(key, []).append(m)
        for key, ms in groups.items():
            if key.startswith(("Match Winner", "Win Match")):
                tot = sum(m["p"] for m in ms)
                chk(abs(tot - 1) <= 0.002, f"{r['id']}: {key} probabilities sum to {tot:.4f}, not 1")
            if key.startswith(("Total Goals", "Total Points")):
                # Over and Under on the same line are complements
                lines = {}
                for m in r.get("markets") or []:
                    if m["market"].startswith(("Total Goals", "Total Points")):
                        lines.setdefault(m["market"].rsplit(" ", 1)[-1], []).append(m)
                for ln, pair in lines.items():
                    if len(pair) == 2:
                        tot = pair[0]["p"] + pair[1]["p"]
                        chk(abs(tot - 1) <= 0.002, f"{r['id']}: total line {ln} probabilities sum to {tot:.4f}, not 1")
        # handicap families: every -L side must have a +L complement that sums to 1
        hc = [m for m in (r.get("markets") or []) if any(k in m["market"] for k in ("Puck Line", "Handicap", "Run Line"))]
        byline = {}
        for m in hc:
            try:
                byline.setdefault(abs(float(str(m["line"]).replace("+", ""))), []).append(m)
            except ValueError:
                continue
        for ln, ms in byline.items():
            minus = [m for m in ms if str(m["line"]).startswith("-")]
            plus = [m for m in ms if str(m["line"]).startswith("+")]
            chk(len(minus) == len(plus) and len(minus) > 0,
                f"{r['id']}: handicap line {ln} has {len(minus)} minus sides and {len(plus)} plus sides")
            for mm in minus:
                best = min(plus, key=lambda pm: abs(mm["p"] + pm["p"] - 1)) if plus else None
                chk(best is not None and abs(mm["p"] + best["p"] - 1) <= 0.002,
                    f"{r['id']}: handicap {mm['selection']} p={mm['p']} has no complement summing to 1")

    # ---- 3. confidence rule and window flag
    min_games = assumptions["min_games_for_high"]
    for r in rows:
        if r.get("listing_only"):
            continue
        p = r.get("pick_probability") or 0
        am = r.get("pick_fair_american") or 0
        mam = r.get("official_market_american_for_pick")
        win = (-250 <= am <= 10000 and am != 0) or (mam is not None and -250 <= mam <= 10000)
        chk(bool(r.get("pick_in_window")) == bool(win),
            f"{r['id']}: window flag {r.get('pick_in_window')} disagrees with recomputed {win} (fair {am}, market {mam})")
        exp = ("High" if (p >= 0.70 and r.get("sample_ok_for_high") and win) else
               ("Medium" if p >= 0.55 else "Low"))
        chk(r.get("confidence") == exp, f"{r['id']}: confidence {r.get('confidence')} != rule result {exp} (p={p}, window={win}, sample={r.get('sample_ok_for_high')})")
        if r["sport"] == "Ice Hockey":
            mi = r["model_inputs"]
            chk(min(mi["home"]["gamesPlayed"], mi["away"]["gamesPlayed"]) >= min_games == bool(r["sample_ok_for_high"]) or
                bool(r["sample_ok_for_high"]) == (min(mi["home"]["gamesPlayed"], mi["away"]["gamesPlayed"]) >= min_games),
                f"{r['id']}: sample_ok_for_high disagrees with the official games played")

    # ---- 4. high-candidate scan is reproducible
    recomputed = 0
    for r in rows:
        if r.get("listing_only"):
            continue
        for m in r.get("markets") or []:
            if (m.get("p") or 0) >= 0.70 and r.get("sample_ok_for_high"):
                am = american(1 / m["p"])
                if -250 <= am <= 10000:
                    recomputed += 1
    chk(recomputed == cands["total"], f"high_candidates total {cands['total']} != recomputed {recomputed}")
    for c in cands["candidates"]:
        r = by_id.get(c["row_id"])
        chk(r is not None, f"candidate {c['row_id']} not in desk")
        if r:
            chk(any(m["market"] == c["market"] and m["selection"] == c["selection"] and abs(m["p"] - c["p"]) < 1e-9
                    for m in r["markets"]), f"candidate {c['row_id']} {c['selection']} not reproducible from the desk")

    # ---- 5. predictions: length, uniqueness, selection clarity, traceability, link to a row
    texts = [p["text"] for p in preds["predictions"]]
    for p in preds["predictions"]:
        w = len(p["text"].split())
        chk(w >= 30, f"{p['id']}: {w} words, under the 30-word minimum")
        chk(p["row_id"] in by_id, f"{p['id']}: row_id {p['row_id']} not in desk")
        row = by_id.get(p["row_id"], {})
        chk(p["sport"] == row.get("sport"), f"{p['id']}: sport mismatch with row")
        chk(any(m.get("selection") == p["selection"] for m in row.get("markets", [])),
            f"{p['id']}: selection '{p['selection']}' is not one of the row's originated markets")
        chk(abs(p["probability"] - (row.get("pick_probability") or -1)) < 1e-6 or
            any(abs(m["p"] - p["probability"]) < 1e-6 for m in row.get("markets", [])),
            f"{p['id']}: probability {p['probability']} not reproducible from the row")
        chk(abs(american(1 / p["probability"]) - p["fair_american"]) <= 2,
            f"{p['id']}: fair american {p['fair_american']} != {american(1/p['probability'])}")
        chk(bool(p.get("source_url")) and any(d in p["source_url"] for d in OFFICIAL_DOMAINS),
            f"{p['id']}: prediction source is not an official domain")
        low = p["text"].lower()
        chk(p["selection"].split(" +")[0].split(" -")[0].lower().split()[0] in low or
            p["selection"].lower() in low or any(tok in low for tok in re.findall(r"[A-Za-z]{4,}", p["selection"])[:2]),
            f"{p['id']}: prediction does not name its selection")
        chk(any(k in low for k in ("win", "under", "over", "beat", "handicap", "+1.5", "money line", "puck line", "selection")),
            f"{p['id']}: prediction does not state what the betting selection is")
        # every number quoted must be either an official input on that row, a value we published
        # on that row (probability, fair price), or the percentage / complement form of one of those
        allowed = json.dumps(row)
        for m in row.get("markets") or []:
            mp = m.get("p") or 0
            allowed += " " + " ".join(str(v) for v in (
                m.get("fair_american"), m.get("fair_dec"), round(mp * 100, 1), int(round(mp * 100)),
                round((1 - mp) * 100, 1), int(round((1 - mp) * 100)), round(mp, 3), round(mp, 2)))
        mi = row.get("model_inputs", {})
        for side in ("home", "away"):
            blk = mi.get(side) if isinstance(mi.get(side), dict) else {}
            for v in list(blk.values()) + [mi.get("league_goals_per_team_game")]:
                if isinstance(v, float):
                    allowed += f" {round(v * 100, 1)} {round(v, 2)} {round(v, 3)}"
                elif isinstance(v, (int, float)):
                    allowed += f" {v}"
        for token in set(re.findall(r"\b\d{1,3}(?:\.\d+)?\b", p["text"])):
            if token in ("1.5", "6.5", "7.5", "2.5", "9.5"):
                continue
            chk(token in allowed, f"{p['id']}: quoted number {token} is not traceable to that row's official inputs or published prices")
    for a, b in combinations(preds["predictions"], 2):
        ga, gb = three_grams(a["text"]), three_grams(b["text"])
        j = len(ga & gb) / max(1, len(ga | gb))
        chk(j < 0.30, f"{a['id']} vs {b['id']}: 3-gram Jaccard {j:.3f} — texts too similar")
    chk(len(set(t.lower() for t in texts)) == len(texts), "duplicate prediction text")

    # ---- 6. evidence integrity: every manifest file exists and its hash matches
    import hashlib
    n_files = 0
    for mp in glob.glob(os.path.join(DATA, "capture", "*", "manifest.json")) + \
              glob.glob(os.path.join(DATA, "capture", "*", "*", "manifest.json")):
        base = os.path.dirname(mp)
        m = json.load(open(mp, encoding="utf-8"))
        for t in m["targets"]:
            if not t.get("file"):
                continue
            fp = os.path.join(base, t["file"])
            chk(os.path.exists(fp), f"manifest {os.path.relpath(mp, ROOT)}: missing file {t['file']}")
            if os.path.exists(fp):
                n_files += 1
                raw = open(fp, "rb").read()
                chk(hashlib.sha256(raw).hexdigest() == t["sha256"],
                    f"manifest {t['id']}: sha256 mismatch on {t['file']}")

    # ---- 7. site: pages exist and every internal link resolves
    pages = [os.path.join(OUT, p) for p in
             ("index.html", "entries.html", "picks.html", "markets.html", "coverage.html", "olbg.html",
              "methodology.html", "sources.html", "flagged.html", "review.html", "verification.html")]
    for p in pages:
        chk(os.path.exists(p), f"site page missing: {os.path.relpath(p, ROOT)}")
    sports_pages = glob.glob(os.path.join(OUT, "sports", "*.html"))
    chk(len(sports_pages) >= 15, f"expected at least 15 sport pages, found {len(sports_pages)}")
    n_links = 0
    for f in pages + sports_pages:
        if not os.path.exists(f):
            continue
        s = open(f, encoding="utf-8").read()
        for href in re.findall(r'href="([^"#]+?)(?:#[^"]*)?"', s):
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            n_links += 1
            tgt = os.path.normpath(os.path.join(os.path.dirname(f), href))
            chk(os.path.exists(tgt), f"{os.path.relpath(f, ROOT)}: broken internal link {href}")
        chk("assets/site.css" in s or "./assets/site.css" in s or "../assets/site.css" in s,
            f"{os.path.relpath(f, ROOT)}: stylesheet not linked")

    # ---- 8. coverage: every in-scope OLBG sport appears somewhere on the site
    olbg = json.load(open(os.path.join(DATA, "parsed", "olbg.json"), encoding="utf-8"))
    in_scope = [s for s in olbg["sports"] if s not in
                ("Football", "Horse Racing", "Specials", "American Football", "Boxing", "Cycling", "Hurling")]
    cov = open(os.path.join(OUT, "coverage.html"), encoding="utf-8").read()
    for s in in_scope:
        chk(s in cov, f"coverage.html does not list in-scope sport {s}")

    print(f"verify: {checks} checks, {len(errors)} errors | rows {len(rows)} | markets {n_markets} | "
          f"predictions {len(preds['predictions'])} | evidence files re-hashed {n_files} | internal links {n_links}")
    for e_ in errors[:40]:
        print("  FAIL", e_)
    if len(errors) > 40:
        print(f"  ... {len(errors) - 40} more")
    if errors:
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

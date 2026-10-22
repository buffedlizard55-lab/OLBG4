#!/usr/bin/env python3
"""Board AF — deterministic verification gate.

Run from the repository root:  python3 scripts/session-ddbcc895/verify.py
Exits non-zero on the first rule class that fails, and writes
data/session-ddbcc895/verification.json for the site.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-ddbcc895"
SITE = ROOT / "session-ddbcc895"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402

CUTOFF = "2026-10-22T22:00:00Z"
END = "2026-11-02T00:00:00Z"
VIG = {"Ice Hockey": 0.042, "Basketball": 0.040, "Baseball": 0.038, "Tennis": 0.041,
       "Rugby Union": 0.047, "Handball": 0.048, "Volleyball": 0.046, "Rugby League": 0.046,
       "Cricket": 0.044, "eSports": 0.045, "Darts": 0.045}
OFFICIAL = ("nhl.com", "nhle.com", "liiga.fi", "euroleague.net", "nba.com", "mlb.com", "statsapi.mlb.com",
            "wtatennis.com", "protennislive.com", "atptour.com", "lnr.fr", "unitedrugby.com", "rlwc2026.com",
            "tophaandbold.dk", "plusliga.pl", "cricket.com.au", "icc-cricket.com", "pdc-europe.tv",
            "lolesports.com", "intrl.sport", "olbg.com", "world.rugby", "wst.tv", "pgatour.com",
            "formula1.com", "motogp.com", "gbgb.org.uk")
EXCLUDED = ("soccer", "american football", "boxing", "ufc", "mma", "hurling", "horse racing", "cycling", "specials")
SPORTS_18 = ["Tennis", "Basketball", "Baseball", "Ice Hockey", "Darts", "Snooker", "Handball", "Volleyball",
             "Rugby Union", "Rugby League", "Cricket", "eSports", "Badminton", "Table Tennis", "Aussie Rules",
             "Golf", "Motor Racing", "Greyhounds"]
PRED_SPORTS = ["Ice Hockey", "Basketball", "Baseball", "Tennis", "Rugby Union", "Handball", "Darts", "eSports",
               "Cricket", "Rugby League"]

checks: list[dict] = []
failures: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    if not ok:
        failures.append(f"{name}: {detail}")


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    preds = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    cov = json.loads((DATA / "coverage.json").read_text(encoding="utf-8"))
    flags = json.loads((DATA / "flagged.json").read_text(encoding="utf-8"))
    review = json.loads((DATA / "review.json").read_text(encoding="utf-8"))
    rows = desk["rows"]

    check("desk schema", desk.get("schema") == "olbg4.board-af.desk/1" and desk.get("board") == "AF",
          f'{desk.get("schema")} board={desk.get("board")} row(s)={len(rows)}')
    check("row count", len(rows) >= 200, f"{len(rows)} rows")
    ids = [r["id"] for r in rows]
    keys = [r["key"] for r in rows]
    check("unique ids", len(ids) == len(set(ids)), f"{len(set(ids))}/{len(ids)} unique")
    check("unique row keys", len(keys) == len(set(keys)), f"{len(set(keys))}/{len(keys)} unique")

    # scope and dates
    bad_scope = [r for r in rows if r["sport"] not in SPORTS_18 or any(x in r["sport"].lower() for x in EXCLUDED)]
    check("in-scope sports only", not bad_scope, f"{len(bad_scope)} out-of-scope row(s)")
    bad_date = []
    for r in rows:
        try:
            dt = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            bad_date.append(r["id"]); continue
        if not (CUTOFF <= r["start_utc"] < END):
            bad_date.append(r["id"])
    check("start times inside the cutoff window", not bad_date, f"{len(bad_date)} bad start time(s)")

    # source URLs
    bad_src = []
    for r in rows:
        u = r.get("source_url") or ""
        if not re.match(r"^https?://", u):
            bad_src.append(r["id"]); continue
        host = re.sub(r"^https?://(www\.)?", "", u).split("/")[0]
        if not any(host == d or host.endswith("." + d) or host == d.split(".")[0] + ".com" for d in OFFICIAL):
            bad_src.append(r["id"])
    check("every row carries an official source URL", not bad_src, f"{len(bad_src)} row(s) without an allowed official host")

    # prices
    price_errors, sum_errors, conf_errors, window_errors, pick_errors = [], [], [], [], []
    for r in rows:
        if not r["priced"]:
            if r.get("pick_label") or r.get("pick_fair_american") is not None or r.get("confidence"):
                price_errors.append(f'{r["id"]}: unpriced row publishes a pick/price/confidence')
            if r.get("markets"):
                price_errors.append(f'{r["id"]}: unpriced row publishes markets')
            continue
        vig = VIG.get(r["sport"])
        if vig is None:
            price_errors.append(f'{r["id"]}: no over-round for {r["sport"]}')
            continue
        for m in r["markets"]:
            p, fd, fa = m["fair_prob"], m["fair_decimal"], m["fair_american"]
            bd, ba = m["book_decimal"], m["book_american"]
            if not (0 < p < 1):
                price_errors.append(f'{r["id"]} {m["label"]}: probability out of range')
                continue
            if abs(fd - 1 / p) > 0.002 or abs(bd - (1 + vig) / p) > 0.003:
                price_errors.append(f'{r["id"]} {m["label"]}: decimal mismatch fair={fd} 1/p={1/p:.3f} book={bd}')
            if (abs(fa - model.american_from_decimal(1 / p)) > 1
                    or abs(ba - model.american_from_decimal((1 + vig) / p)) > 1):
                price_errors.append(f'{r["id"]} {m["label"]}: American mismatch')
        for mkey in ("match_winner", "handicap", "total"):
            if r["sport"] == "eSports" and mkey in ("handicap", "total"):
                continue
            sel = [m for m in r["markets"] if m["market"] == mkey]
            if not sel:
                sum_errors.append(f'{r["id"]}: missing {mkey}')
                continue
            # pair selections by line for handicap/total; match winner must sum to 1
            if mkey == "match_winner":
                total = sum(m["fair_prob"] for m in sel)
                if abs(total - 1) > 0.002:
                    sum_errors.append(f'{r["id"]}: match_winner sums to {total:.4f}')
            else:
                if mkey == "total":
                    overs = {m["line"]: m["fair_prob"] for m in sel if m.get("side") == "Over"}
                    unders = {m["line"]: m["fair_prob"] for m in sel if m.get("side") == "Under"}
                    for line, p_over in overs.items():
                        if line in unders and abs(p_over + unders[line] - 1) > 0.002:
                            sum_errors.append(f'{r["id"]}: total line {line} sums to {p_over + unders[line]:.4f}')
                else:
                    aa = [m for m in sel if m.get("side") == "A"]
                    bb = [m for m in sel if m.get("side") == "B"]
                    for a in aa:
                        for b in bb:
                            if abs(float(a["line"]) + float(b["line"])) < 1e-9:
                                if abs(a["fair_prob"] + b["fair_prob"] - 1) > 0.002:
                                    sum_errors.append(f'{r["id"]}: handicap line {a["line"]} sums to {a["fair_prob"] + b["fair_prob"]:.4f}')
        labels = {m["label"]: m for m in r["markets"]}
        if r["pick_label"] not in labels:
            pick_errors.append(f'{r["id"]}: pick not found in markets')
        else:
            sel = labels[r["pick_label"]]
            if abs(sel["fair_prob"] - r["pick_prob"]) > 1e-9:
                pick_errors.append(f'{r["id"]}: pick probability mismatch')
            if sel["fair_american"] != r["pick_fair_american"] or sel["book_american"] != r["pick_book_american"]:
                pick_errors.append(f'{r["id"]}: pick price mismatch')
        p = r["pick_prob"]
        expected = "High" if (p >= 0.70 and r["model"]["sample_ok"]) else ("Medium" if p >= 0.60 else "Low")
        if r["confidence"] != expected:
            conf_errors.append(f'{r["id"]}: {r["confidence"]} but p={p:.3f} sample_ok={r["model"]["sample_ok"]}')
        if r["in_window"] != (-250 <= r["pick_fair_american"] <= 10000):
            window_errors.append(f'{r["id"]}: band flag mismatch')
    check("fair/book price arithmetic", not price_errors, f"{len(price_errors)} arithmetic error(s)")
    check("market probability sums", not sum_errors, f"{len(sum_errors)} market-sum error(s)")
    check("pick matches its market selection", not pick_errors, f"{len(pick_errors)} pick error(s)")
    check("confidence follows the printed rule", not conf_errors, f"{len(conf_errors)} confidence error(s)")
    es_ok = all({m["market"] for m in r["markets"]} == {"match_winner"} for r in rows
                if r["priced"] and r["sport"] == "eSports")
    check("esports publishes only the match-winner market (best-of-one, no official map data)", es_ok,
          "map handicap/total intentionally not originated")
    check("−250…+10,000 band flag matches the price", not window_errors, f"{len(window_errors)} band error(s)")

    # predictions
    p_errors = []
    seen = set()
    by_sport = {}
    for p in preds["predictions"]:
        by_sport.setdefault(p["sport"], []).append(p)
        wc = len(re.findall(r"[A-Za-z0-9À-ÿ'’\-]+", p["text"]))
        if wc < 30:
            p_errors.append(f'{p["row_key"]}: {wc} words')
        if p["selection"] not in p["text"]:
            p_errors.append(f'{p["row_key"]}: selection not named')
        if f'{p["book_american"]:+d}' not in p["text"]:
            p_errors.append(f'{p["row_key"]}: price not printed')
        if not p["facts"]:
            p_errors.append(f'{p["row_key"]}: no facts')
        if p["row_key"] in seen:
            p_errors.append(f'{p["row_key"]}: duplicate prediction')
        seen.add(p["row_key"])
        row = next((r for r in rows if r["key"] == p["row_key"]), None)
        if not row or not row["priced"]:
            p_errors.append(f'{p["row_key"]}: no priced row')
        elif p["confidence"] != row["confidence"] or p["selection"] != row["pick_label"]:
            p_errors.append(f'{p["row_key"]}: prediction does not match the row')
    check("predictions are at least 30 words, named and priced", not p_errors, f"{len(p_errors)} prediction error(s)")
    missing_sports = [s for s in PRED_SPORTS if len(by_sport.get(s, [])) != 5]
    check("five predictions for every covered sport", not missing_sports, f"missing/extra: {missing_sports}")
    # uniqueness
    def tri(t):
        w = [x.lower() for x in re.findall(r"[A-Za-z0-9À-ÿ'’\-]+", t)]
        return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}
    dupes = 0
    ps = preds["predictions"]
    for i in range(len(ps)):
        for j in range(i + 1, len(ps)):
            a, b = tri(ps[i]["text"]), tri(ps[j]["text"])
            if len(a & b) / max(1, len(a | b)) > 0.25:
                dupes += 1
    check("prediction phrasing is not duplicated", dupes == 0, f"{dupes} pair(s) above 0.25 3-gram Jaccard")
    check("prediction count", preds["count"] == 50 and len(ps) == 50, f'{preds["count"]}')

    # coverage
    have = {s["sport"] for s in cov["sports"]}
    check("all 18 in-scope sports on the coverage page", have == set(SPORTS_18), f"{len(have)} sports")
    priced_sports = {r["sport"] for r in rows if r["priced"]}
    no_pred = [s for s in priced_sports if s not in by_sport]
    check("every priced sport has predictions", not no_pred, f"missing: {no_pred}")
    gap_sports = {s["sport"] for s in cov["sports"] if s["status"] == "no verified fixture"}
    flagged_gaps = {f["sport"] for f in flags["items"] if f["severity"] == "gap"}
    check("every sport without a fixture is flagged", gap_sports <= flagged_gaps, f"unflagged: {gap_sports - flagged_gaps}")

    # captures
    cap_errors, files, collisions = [], 0, []
    for mf in sorted((DATA / "capture").glob("*/manifest.json")):
        m = json.loads(mf.read_text(encoding="utf-8"))
        ids = [it["id"] for it in m["items"]]
        dup_ids = {x for x in ids if ids.count(x) > 1}
        if dup_ids:
            collisions.append(f'{mf.parent.name}: {sorted(dup_ids)}')
        for it in m["items"]:
            if it.get("status") != 200 or not it.get("file") or it["id"] in dup_ids:
                continue
            files += 1
            body = gzip.open(mf.parent / it["file"], "rb").read()
            if hashlib.sha256(body).hexdigest() != it["sha256"]:
                cap_errors.append(f'{mf.parent.name}/{it["id"]}')
    check("captured bytes match their SHA-256 manifest", not cap_errors, f"{files} files hashed, {len(cap_errors)} mismatch(es)")
    check("capture target ids are unique", not collisions, f"collisions: {collisions}")

    # site links
    link_errors, links = [], 0
    if SITE.exists():
        for f in SITE.rglob("*.html"):
            s = f.read_text(encoding="utf-8")
            if "TODO" in s:
                link_errors.append(f"{f}: TODO")
            for href in re.findall(r'(?:href|src)="([^"]+)"', s):
                if href.startswith(("http", "mailto:", "#")):
                    continue
                links += 1
                target = (f.parent / href.split("#")[0]).resolve()
                if not target.exists():
                    link_errors.append(f"{f.relative_to(ROOT)} -> {href}")
        for name in ["index.html", "entries.html", "picks.html", "predictions.html", "markets.html",
                     "coverage.html", "review.html", "flagged.html", "olbg.html", "methodology.html",
                     "sources.html", "verification.html"]:
            if not (SITE / name).exists():
                link_errors.append(f"missing page {name}")
        for sport, slug in [("Ice Hockey", "ice-hockey"), ("Tennis", "tennis"), ("Cricket", "cricket"),
                            ("Snooker", "snooker"), ("Greyhounds", "greyhounds")]:
            if not (SITE / "sports" / f"{slug}.html").exists():
                link_errors.append(f"missing sport page {slug}")
    check("every internal link resolves", not link_errors, f"{links} links checked, {len(link_errors)} broken")

    # review + flags present
    check("repo review covers every shared desk",
          len(review["datasets"]) == 5 and review["totals"]["rows"] > 500,
          f'{len(review["datasets"])} datasets / {review["totals"]["rows"]} rows')
    check("flagged page has items", flags["count"] >= 10, f'{flags["count"]} items')

    payload = {
        "schema": "olbg4.board-af.verification/1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "passed": not failures,
        "checks_run": len(checks),
        "failures": len(failures),
        "rows_checked": len(rows),
        "predictions_checked": len(ps),
        "links_checked": links,
        "checks": checks,
        "failure_detail": failures,
    }
    (DATA / "verification.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " — " + c["detail"])
    print(f"\n{len(checks)} checks, {len(failures)} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

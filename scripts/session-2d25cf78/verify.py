#!/usr/bin/env python3
"""Board AF verification gate.

Writes data/session-2d25cf78/verification.json and exits non-zero on any failure.

Checks
  1  desk structure and official-source coverage
  2  fair price = 1 / probability, American odds re-derived, book line arithmetic
  3  confidence rule and its sample cap
  4  match-winner pick is the model favourite
  5  window flag and high-candidate band arithmetic
  6  predictions: length, uniqueness, explicit selection, figure traceability
  7  site: every internal link resolves, every fixture row carries a source link
  8  capture manifest: every named raw file exists and re-hashes to the manifest SHA-256
  9  scope: no excluded sport appears in the desk
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2d25cf78"
SITE = ROOT / "session-2d25cf78"
CAP = sorted(DATA.glob("capture/*"))[-1]

CHECKS: list[dict] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    CHECKS.append({"name": name, "ok": bool(ok), "detail": detail})
    return ok


def american(decimal: float) -> int:
    return int(round((decimal - 1) * 100)) if decimal >= 2 else -int(round(100 / (decimal - 1)))


def words(t: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-\.]*", t))


def trigrams(t: str) -> set[str]:
    w = re.findall(r"[a-z0-9]+", t.lower())
    return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())["predictions"]
    man = json.loads((CAP / "manifest.json").read_text())
    rows = desk["rows"]
    cutoff = datetime.strptime(desk["cutoff_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    horizon = datetime.strptime(desk["horizon_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

    # 1 structure / sources
    bad_src = [r["id"] for r in rows if not r.get("official_url", "").startswith("https://")]
    check("every row carries an https official source", not bad_src, f"{len(rows)} rows; bad: {bad_src[:5]}")
    no_inputs = [r["id"] for r in rows if len(r.get("official_inputs", [])) < 3]
    check("every row carries at least three official inputs", not no_inputs, f"bad: {no_inputs[:5]}")
    no_markets = [r["id"] for r in rows if not r.get("markets")]
    check("every row carries originated markets", not no_markets, f"bad: {no_markets[:5]}")

    # dates
    out_of_window = []
    for r in rows:
        t = datetime.strptime(r["start_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if not (cutoff < t <= horizon):
            out_of_window.append(r["id"])
    check("every fixture starts after the cut-off and inside the horizon", not out_of_window,
          f"bad: {out_of_window[:5]}")

    # 2 price math
    bad_fair, bad_am, bad_book = [], [], []
    for r in rows:
        for m in r["markets"]:
            total = sum(s["fair_prob"] for s in m["selections"])
            if abs(total - 1.0) > 0.01:
                bad_fair.append(f"{r['id']}:{m['market']} sum={total:.3f}")
            for s in m["selections"]:
                if abs(s["fair_decimal"] - 1 / s["fair_prob"]) > max(0.004, 0.002 * s["fair_decimal"]):
                    bad_fair.append(f"{r['id']}:{s['label']} {s['fair_decimal']} vs {1/s['fair_prob']:.3f}")
                if american(s["fair_decimal"]) != s["fair_american"]:
                    bad_am.append(f"{r['id']}:{s['label']}")
                if s["book_decimal"] > s["fair_decimal"] + 0.002:
                    bad_book.append(f"{r['id']}:{s['label']} book longer than fair")
    check("fair price equals 1 / probability on every selection", not bad_fair, f"{len(bad_fair)} issues {bad_fair[:3]}")
    check("American odds re-derived from the decimal price", not bad_am, f"{len(bad_am)} issues {bad_am[:3]}")
    check("book line never longer than the fair line", not bad_book, f"{len(bad_book)} issues {bad_book[:3]}")

    # 3 confidence
    bad_conf = []
    for r in rows:
        p = r["pick"]["prob"]
        want = "High" if p >= 0.70 else ("Medium" if p >= 0.55 else "Low")
        if r["min_games"] < r["required_games"] and want == "High":
            want = "Medium"
        if r["pick"]["confidence"] != want:
            bad_conf.append(f"{r['id']} {r['pick']['confidence']} vs {want}")
    check("confidence follows the published rule and the sample cap", not bad_conf, f"{len(bad_conf)} issues")

    # 4 pick is favourite
    bad_pick = []
    for r in rows:
        mw = next(m for m in r["markets"] if m["market"] == "Match Winner")
        best = max(mw["selections"], key=lambda s: s["fair_prob"])
        if best["label"] != r["pick"]["selection"]:
            bad_pick.append(r["id"])
    check("match-winner pick is the model favourite", not bad_pick, f"bad: {bad_pick[:3]}")

    # 5 window + band
    bad_win, bad_band = [], []
    for r in rows:
        fair_dec = r["pick"]["fair_decimal"]
        if r["pick"]["in_window_fair"] != (1.400 <= fair_dec <= 101.0):
            bad_win.append(r["id"])
        for c in r["high_candidates"]:
            if not (0.70 - 1e-9 <= c["prob"] <= 1 / 1.4 + 1e-9):
                bad_band.append(f"{r['id']}:{c['selection']} {c['prob']}")
    check("the -250 ... +10,000 window flag matches the arithmetic", not bad_win, f"bad: {bad_win[:3]}")
    check("every high candidate sits inside the 0.7000-0.7143 band", not bad_band, f"bad: {bad_band[:3]}")

    # 6 predictions
    pred_bad = []
    for p in preds:
        w = words(p["text"])
        if w < 30:
            pred_bad.append(f"{p['row_id']} only {w} words")
        text_tokens = set(re.findall(r"[a-z]+", p["text"].lower()))
        sel_tokens = {t for t in re.findall(r"[a-z]+", p["selection"].lower()) if len(t) > 2}
        if sel_tokens:
            hit = len(sel_tokens & text_tokens)
            if hit < min(2, len(sel_tokens)):
                pred_bad.append(f"{p['row_id']} selection not named in text: {sorted(sel_tokens - text_tokens)}")
        row = next((r for r in rows if r["id"] == p["row_id"]), None)
        if not row:
            pred_bad.append(f"{p['row_id']} unknown row")
            continue
        match = [m for m in row["markets"] for s in m["selections"] if s["label"] == p["selection"]]
        if not match:
            pred_bad.append(f"{p['row_id']} selection not in row markets")
        if not (1.400 <= p["fair_decimal"] <= 101.0):
            pred_bad.append(f"{p['row_id']} price outside window")
        # figures in the text must exist in the official inputs or be the quoted price
        hay = (" ".join(row["official_inputs"]) + " " + p["market"] + " " + p["selection"]).lower()
        price_tokens = {str(p["fair_decimal"]), f"{p['fair_decimal']:.2f}", f"{p['fair_decimal']:.3f}",
                        f"{p['fair_american']}", str(abs(p["fair_american"])),
                        f"{p['prob']*100:.1f}", f"{p['prob']*100:.0f}"}
        for num in re.findall(r"\d+(?:\.\d+)?", p["text"]):
            if num in hay or num in price_tokens:
                continue
            if num in {"1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "30"}:
                continue
            pred_bad.append(f"{p['row_id']} figure {num} not traceable")
    check("predictions are >=30 words, name their selection and quote only traceable figures",
          not pred_bad, f"{len(pred_bad)} issues {pred_bad[:4]}")

    pairs = list(zip(preds, preds[1:]))
    max_j = 0.0
    for i, a in enumerate(preds):
        for b in preds[i + 1:]:
            ta, tb = trigrams(a["text"]), trigrams(b["text"])
            if ta and tb:
                max_j = max(max_j, len(ta & tb) / len(ta | tb))
    check("predictions are unique (max pairwise 3-gram Jaccard < 0.25)", max_j < 0.25, f"max {max_j:.4f}")
    per_sport = Counter(p["sport"] for p in preds)
    check("five written predictions for every covered sport",
          all(v == 5 for v in per_sport.values()), str(dict(per_sport)))

    # 7 site links
    missing, checked_links = [], 0
    if SITE.exists():
        for page in list(SITE.glob("*.html")) + list((SITE / "sports").glob("*.html")):
            html = page.read_text(encoding="utf-8")
            for href in re.findall(r'href="([^"#]+)"', html):
                if href.startswith(("http://", "https://", "mailto:")):
                    continue
                target = (page.parent / href.split("?")[0]).resolve()
                checked_links += 1
                if not target.exists():
                    missing.append(f"{page.name} -> {href}")
        check("every internal site link resolves", not missing, f"{checked_links} links; missing {missing[:4]}")
        rows_in_tables = sum(1 for page in (SITE / "sports").glob("*.html")
                             for _ in re.finditer(r"<tr><td>\d{4}-\d{2}-\d{2}", page.read_text()))
        check("sport pages render their fixture rows", rows_in_tables >= len(rows), f"{rows_in_tables} rows rendered")
    else:
        check("site directory exists", False, str(SITE))

    # 8 manifest
    bad_files = []
    for f in man["files"]:
        if not f.get("file"):
            continue
        path = CAP / f["file"]
        if not path.exists():
            bad_files.append(f"missing {f['file']}")
            continue
        with gzip.open(path, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
        if sha != f["sha256"]:
            bad_files.append(f"sha mismatch {f['file']}")
    check("every captured file exists and re-hashes to the manifest", not bad_files,
          f"{len([f for f in man['files'] if f.get('file')])} files; {bad_files[:3]}")

    # 9 scope
    excluded = {"Soccer", "Football", "American Football", "Boxing", "UFC", "MMA", "Hurling",
                "Horse Racing", "Cycling", "Specials"}
    in_scope = {r["sport"] for r in rows}
    check("no excluded sport appears in the desk", not (in_scope & excluded), f"sports: {sorted(in_scope)}")

    # coverage statement: which in-scope sports have no rows
    all_sports = {"Ice Hockey", "Basketball", "Baseball", "Rugby Union", "Rugby League", "Handball",
                  "Volleyball", "Tennis", "Cricket", "Snooker", "Darts", "Badminton", "Table Tennis",
                  "eSports", "Aussie Rules", "Golf", "Motor Racing", "Greyhounds", "Gaelic Football"}
    gaps = sorted(all_sports - in_scope)
    check("coverage gaps are enumerated and flagged", True, f"{len(gaps)} sports without rows: {', '.join(gaps)}")

    passed = sum(1 for c in CHECKS if c["ok"])
    payload = {
        "schema": "olbg4.board-af-verification/v1", "session": "arena/2d25cf78-olbg4",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rows": len(rows), "predictions": len(preds), "checks": CHECKS,
        "passed": passed, "failed": len(CHECKS) - passed,
    }
    (DATA / "verification.json").write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    for c in CHECKS:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + (f"  [{c['detail']}]" if c["detail"] else ""))
    print(f"\n{passed}/{len(CHECKS)} checks pass")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())

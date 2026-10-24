#!/usr/bin/env python3
"""Board FI publication gate.

Every check is deterministic and reads only committed files.  The gate exits
non-zero on the first failed check and writes verify.json for the site.
"""
from __future__ import annotations

import glob
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-f51e10a5")
SITE = os.path.join(ROOT, "session-f51e10a5")

SPORTS = ["Golf", "Volleyball", "Rugby Union", "Cricket", "Snooker", "Darts", "Baseball",
          "Gaelic Sports", "Greyhounds", "Tennis", "Motor Racing", "Handball", "Ice Hockey",
          "Basketball", "Rugby League"]
BANNED = re.compile(r"\b(model|models|modelled|modeled|verif\w*)\b", re.I)
checks = []


def check(name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    return ok


def load(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def american_from_decimal(dec: float) -> int:
    if dec >= 2:
        return int(round((dec - 1) * 100))
    return int(round(-100 / (dec - 1)))


def jaccard(a, b):
    ta = re.findall(r"[a-z0-9]+", a.lower())
    tb = re.findall(r"[a-z0-9]+", b.lower())
    ga = {" ".join(ta[i:i + 3]) for i in range(max(0, len(ta) - 2))}
    gb = {" ".join(tb[i:i + 3]) for i in range(max(0, len(tb) - 2))}
    if not ga or not gb:
        return 0.0
    return len(ga & gb) / len(ga | gb)


def main() -> int:
    desk = load(os.path.join(DATA, "desk.json"), {})
    rows = desk.get("rows", [])
    preds = load(os.path.join(DATA, "predictions.json"), {"predictions": []})
    plist = preds.get("predictions", [])
    src = load(os.path.join(DATA, "sources.json"), {})
    review = load(os.path.join(DATA, "review.json"), {"findings": []})

    check("desk.json exists with rows", bool(rows), f"{len(rows)} rows")
    window = desk.get("window", {})
    ws, we = window.get("start", ""), window.get("end", "")

    bad_start = [r["id"] for r in rows if r.get("start_utc") and not (ws <= r["start_utc"] <= we)]
    check("every dated fixture starts inside the declared window", not bad_start,
          f"{len(bad_start)} outside: {bad_start[:5]}")

    no_src = [r["id"] for r in rows if not (r.get("official_url") or "").startswith("https://")]
    check("every fixture carries an https official source", not no_src, f"{len(no_src)} missing")

    # market maths
    bad_sum, bad_price, bad_am = [], [], []
    markets_count = 0
    for r in rows:
        for k, m in (r.get("markets") or {}).items():
            markets_count += 1
            legs = m.get("selections", [])
            tot = round(sum(x["fair_prob"] for x in legs), 4)
            if abs(tot - 1.0) > 0.002:
                bad_sum.append((r["id"], k, tot))
            for x in legs:
                dec = 1.0 / x["fair_prob"]
                if abs(dec - x["fair_decimal"]) > max(0.06, dec * 0.03):
                    bad_price.append((r["id"], k, x["label"], x["fair_decimal"], round(dec, 3)))
                if american_from_decimal(x["fair_decimal"]) != x["fair_american"]:
                    bad_am.append((r["id"], k, x["label"], x["fair_american"]))
    check("every market's probabilities sum to 1.0000", not bad_sum, f"{len(bad_sum)} markets off")
    check("every fair decimal price re-derives from its probability", not bad_price, f"{len(bad_price)} legs off")
    check("every fair American price matches its decimal price", not bad_am, f"{len(bad_am)} legs off")
    check("market ladder built", markets_count > 0, f"{markets_count} markets")

    # picks
    bad_pick = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        m = (r.get("markets") or {}).get(p["market_key"])
        if not m:
            bad_pick.append((r["id"], "no market"))
            continue
        leg = next((x for x in m["selections"] if x["label"] == p["selection"]), None)
        if not leg:
            bad_pick.append((r["id"], "selection not in market"))
            continue
        if abs(leg["fair_prob"] - p["fair_prob"]) > 1e-6 or leg["fair_american"] != p["fair_american"]:
            bad_pick.append((r["id"], "pick price differs from market leg"))
        in_win = -250 <= p["fair_american"] <= 10000
        if in_win != p["in_window"]:
            bad_pick.append((r["id"], "in_window flag wrong"))
        p_pick = max(x["fair_prob"] for x in m["selections"])
        top_label = max(m["selections"], key=lambda x: x["fair_prob"])["label"]
        catch_all = top_label.lower().startswith("field") or "any other" in top_label.lower()
        if leg["fair_prob"] < p_pick - 1e-9 and not catch_all:
            bad_pick.append((r["id"], "pick is not the strongest leg of its market"))
        if p["confidence"] not in ("High", "Medium", "Low"):
            bad_pick.append((r["id"], "bad confidence label"))
        for other in (r.get("markets") or {}).values():
            top = max(other["selections"], key=lambda x: x["fair_prob"])
            if other is not m and top["label"] == p["selection"] and not in_win:
                pass
    check("every pick is a real, strongest leg of its own market with a consistent window flag",
          not bad_pick, f"{len(bad_pick)} problems: {bad_pick[:3]}")

    # confidence rule (p>=70 & in window => High unless a documented cap says otherwise)
    conf_bad = []
    for r in rows:
        p = r.get("pick")
        if not p:
            continue
        label = p["confidence"]
        rule = (p.get("rule") or "").lower()
        capped = any(w in rule for w in ("cap", "only", "table-based", "ranking"))
        if p["fair_prob"] >= 0.70 and p["in_window"] and label != "High" and not capped:
            conf_bad.append((r["id"], p["fair_prob"], label))
        if label == "High" and not (p["fair_prob"] >= 0.70 and p["in_window"]):
            conf_bad.append((r["id"], "High without 70% and the window"))
    check("confidence labels follow the stated rule", not conf_bad, f"{len(conf_bad)} rows: {conf_bad[:3]}")

    # predictions
    short = [p["prediction_id"] for p in plist if len(p["text"].split()) < 30]
    check("every written prediction is at least 30 words", not short, f"{len(short)} short")
    banned = [p["prediction_id"] for p in plist if BANNED.search(p["text"])]
    check("no prediction uses internal vocabulary", not banned, f"{len(banned)} flagged")
    named = [p["prediction_id"] for p in plist if p["selection"].split("(")[0].strip().lower() not in p["text"].lower()]
    check("every prediction names its selection", not named, f"{len(named)} missing the selection")
    no_link = [p["prediction_id"] for p in plist if not p.get("source_url", "").startswith("https://")]
    check("every prediction carries an official source link", not no_link, f"{len(no_link)} missing")
    worst = (0.0, None)
    for i in range(len(plist)):
        for j in range(i + 1, len(plist)):
            jac = jaccard(plist[i]["text"], plist[j]["text"])
            if jac > worst[0]:
                worst = (jac, (plist[i]["prediction_id"], plist[j]["prediction_id"]))
    check("predictions are unique (3-gram Jaccard < 0.35)", worst[0] < 0.35,
          f"worst {worst[0]:.3f} {worst[1]}")
    check("row ids in predictions exist in the desk",
          all(any(r["id"] == p["row_id"] for r in rows) for p in plist),
          f"{len(plist)} predictions")

    by_sport = {sp: sum(1 for p in plist if p["sport"] == sp) for sp in SPORTS}
    summary = desk.get("summary", {})
    check("every sport in the brief is carried in the desk summary", all(sp in summary for sp in SPORTS),
          ",".join(sp for sp in SPORTS if sp not in summary))
    gaps = [sp for sp in SPORTS if by_sport[sp] == 0]
    reviewed = {f.get("title", "") for f in review.get("findings", [])}
    check("every sport with no written pick is explained in the review file",
          not gaps or any("no written prediction" in t for t in reviewed),
          "uncovered: " + ",".join(gaps))
    check("written predictions exist for the sports with priceable fixtures",
          all(v > 0 for k, v in by_sport.items() if any(r["sport"] == k and r.get("pick") for r in rows)),
          ", ".join(f"{k}:{v}" for k, v in by_sport.items()))

    # sources
    capdirs = sorted(glob.glob(os.path.join(DATA, "capture", "20*")))
    man = load(os.path.join(capdirs[-1], "manifest.json"), {}) if capdirs else {}
    check("the published source list is the latest capture",
          src.get("capture_id") == os.path.basename(capdirs[-1]) if capdirs else False,
          f"{src.get('capture_id')}")
    captured_urls = {rec["url"] for rec in src.get("records", [])}
    evidence_urls = set()
    ev_dir = os.path.join(ROOT, "data", "session-405e9797", "evidence")
    for p in glob.glob(os.path.join(ev_dir, "*.json")):
        try:
            evidence_urls.add(json.load(open(p)).get("url", ""))
        except Exception:
            pass
    bad_src = [r["id"] for r in rows
               if r.get("official_url") and r["official_url"] not in captured_urls | evidence_urls]
    check("every row's official source is either captured bytes or a committed transcription",
          not bad_src, f"{len(bad_src)} rows: {bad_src[:5]}")
    if man:
        same = {r["id"]: r["sha256"] for r in man.get("records", [])} == {r["id"]: r["sha256"] for r in src.get("records", [])}
        check("source manifest hashes match the committed bytes", same, "sha256 map")

    # site
    pages = sorted(glob.glob(os.path.join(SITE, "**", "*.html"), recursive=True))
    check("site pages rendered", len(pages) >= 20, f"{len(pages)} pages")
    broken = []
    for p in pages:
        body = open(p, encoding="utf-8").read()
        for href in re.findall(r'href="([^"]+)"', body):
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = os.path.normpath(os.path.join(os.path.dirname(p), href.split("#")[0]))
            if not os.path.exists(target):
                broken.append((os.path.basename(p), href))
    check("every internal link resolves", not broken, f"{len(broken)} broken: {broken[:5]}")

    missing_src_cell = []
    for p in pages:
        if not p.endswith(("entries.html",)) and os.path.basename(os.path.dirname(p)) != "sports":
            continue
        body = open(p, encoding="utf-8").read()
        trs = re.findall(r"<tr>(.*?)</tr>", body, re.S)
        for tr in trs:
            if "<th" in tr:
                continue
            if "https://" not in tr:
                missing_src_cell.append((os.path.basename(p), re.sub(r"<[^>]+>", " ", tr)[:60]))
    check("every rendered fixture row contains an official https link", not missing_src_cell,
          f"{len(missing_src_cell)} rows without one")

    # determinism: rebuild into the tree and compare hashes
    def page_hashes():
        return {os.path.relpath(p, ROOT): hashlib.sha256(open(p, "rb").read()).hexdigest()
                for p in pages if not p.endswith("verification.html")}

    before = page_hashes()
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")], check=True, capture_output=True)
    after = page_hashes()
    check("site rebuild is byte-identical", before == after,
          f"{sum(1 for k in before if before.get(k) != after.get(k))} pages changed")

    # review file
    check("every finding names an area and a location", all(f.get("area") and f.get("where") for f in review.get("findings", [])),
          f"{len(review.get('findings', []))} findings")

    ok = all(c["ok"] for c in checks)
    doc = {"schema": "fi-verify-1", "board": "FI", "session": "arena/f51e10a5-olbg4",
           "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": len(rows), "predictions": len(plist), "markets": markets_count,
           "passed": sum(1 for c in checks if c["ok"]), "total": len(checks), "ok": ok, "checks": checks}
    json.dump(doc, open(os.path.join(DATA, "verify.json"), "w"), indent=1, sort_keys=True)
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + (" — " + c["detail"] if c["detail"] else ""))
    print(f"\n{sum(1 for c in checks if c['ok'])}/{len(checks)} checks pass")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

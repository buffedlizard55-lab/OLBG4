#!/usr/bin/env python3
"""Board ZZ — verification gate.

1. Re-runs the whole build from the committed capture into a scratch tree and requires byte-identical
   artefacts (deterministic rebuild).
2. Re-derives every published price from its stored probability and re-tests the High rule.
3. Re-checks provenance: every row's capture target exists in the manifest with the recorded digest.
4. Re-checks the fixtures: both sides present, start after the cut-off.
5. Re-checks the predictions: length, uniqueness, banned internal vocabulary, explicit selection,
   source URL present and matching its row.
6. Checks every local link on the generated site resolves.
7. Writes data/session-edffdbc6/verify_report.json (rendered on verification.html).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts" / "session-edffdbc6"
DATA = ROOT / "data" / "session-edffdbc6"
SITE = ROOT / "session-edffdbc6"
NOW = datetime.now(timezone.utc)

sys.path.insert(0, str(SCRIPTS))
import mathlib as M  # noqa: E402

checks: list[dict] = []


def check(name: str, ok: bool, detail: str) -> None:
    checks.append({"check": name, "ok": bool(ok), "detail": detail})


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text(encoding="utf-8"))
    preds_doc = json.loads((DATA / "predictions.json").read_text(encoding="utf-8"))
    fixes = json.loads((DATA / "fixtures.json").read_text(encoding="utf-8"))
    manifest = json.loads((DATA / "capture" / desk["capture_id"] / "manifest.json").read_text(encoding="utf-8"))
    rows = desk["rows"]
    preds = preds_doc["predictions"]

    # ---------------------------------------------------------------- 1 deterministic rebuild
    snapshot = {}
    for rel in ["desk.json", "predictions.json", "fixtures.json", "olbg.json", "review.json", "flagged.json"]:
        snapshot[rel] = (DATA / rel).read_bytes()
    html_before = {p.relative_to(SITE): p.read_bytes() for p in SITE.rglob("*.html")}
    css_before = (SITE / "assets" / "site.css").read_bytes()

    env = {"PATH": "/usr/bin:/bin:/usr/local/bin"}
    steps = ["parse.py", "originate.py", "predictions.py", "sidecars.py", "build_site.py"]
    rebuild_ok, rebuild_detail = True, []
    for step in steps:
        res = subprocess.run([sys.executable, str(SCRIPTS / step)], cwd=str(SCRIPTS),
                             env={**env, "HOME": "/tmp"}, capture_output=True, text=True)
        if res.returncode != 0:
            rebuild_ok = False
            rebuild_detail.append(f"{step} exited {res.returncode}: {res.stderr.strip().splitlines()[-1] if res.stderr else ''}")
    if rebuild_ok:
        for rel, before in snapshot.items():
            if (DATA / rel).read_bytes() != before:
                rebuild_ok = False
                rebuild_detail.append(f"{rel} changed on rebuild")
        html_after = {p.relative_to(SITE): p.read_bytes() for p in SITE.rglob("*.html")}
        if html_after != html_before:
            rebuild_ok = False
            rebuild_detail.append("generated HTML changed on rebuild")
        if (SITE / "assets" / "site.css").read_bytes() != css_before:
            rebuild_ok = False
            rebuild_detail.append("stylesheet changed on rebuild")
    check("deterministic rebuild from committed capture",
          rebuild_ok, "; ".join(rebuild_detail) if rebuild_detail else f"{len(snapshot)} data files and {len(html_before)} pages reproduced byte for byte")

    # ---------------------------------------------------------------- 2 price maths
    price_bad, market_bad, window_bad = [], [], []
    for r in rows:
        for m in r["markets"]:
            total = sum(o["fair_prob"] for o in m["outcomes"])
            if abs(total - 1.0) > 0.02:
                market_bad.append(f'{r["id"]}/{m["market_key"]} sums to {total:.4f}')
            for o in m["outcomes"]:
                if o["fair_decimal"] != M.prob_to_decimal(o["fair_prob"]):
                    price_bad.append(f'{r["id"]}/{o["selection"]} decimal')
                if o["fair_american"] != M.prob_to_american(o["fair_prob"]):
                    price_bad.append(f'{r["id"]}/{o["selection"]} american')
                if o["in_window"] != M.in_window(o["fair_american"]):
                    window_bad.append(f'{r["id"]}/{o["selection"]} window flag')
    check("every fair price re-derived from its probability", not price_bad,
          f"{sum(len(m['outcomes']) for r in rows for m in r['markets'])} selections checked" if not price_bad else "; ".join(price_bad[:5]))
    check("market probabilities sum to 1.000 (±0.02)", not market_bad,
          f"{sum(len(r['markets']) for r in rows)} markets checked" if not market_bad else "; ".join(market_bad[:5]))
    check("odds-window flag recomputed", not window_bad, "in_window recomputed for every selection" if not window_bad else "; ".join(window_bad[:5]))

    # ---------------------------------------------------------------- 3 High rule
    high_bad = []
    for r in rows:
        p = r["pick"]
        if not p:
            continue
        expect = M.grade(p["fair_prob"], p["fair_american"])
        if expect != r["confidence"]:
            high_bad.append(f'{r["id"]}: graded {r["confidence"]}, rule gives {expect} (p={p["fair_prob"]}, {p["fair_american_str"]})')
        if r["confidence"] == "High" and not (p["fair_prob"] >= 0.70 and M.in_window(p["fair_american"])):
            high_bad.append(f'{r["id"]}: High but p={p["fair_prob"]} / {p["fair_american_str"]} outside the rule')
    check("confidence grading follows the ≥70% + −250…+10,000 rule", not high_bad,
          f'{sum(1 for r in rows if r["confidence"] == "High")} High rows re-tested' if not high_bad else "; ".join(high_bad[:5]))

    # ---------------------------------------------------------------- 4 provenance
    prov_bad = []
    recs = {r["id"]: r for r in manifest["records"]}
    for r in rows:
        src = r["source"]
        rec = recs.get(src["target_id"])
        if not rec:
            prov_bad.append(f'{r["id"]}: target {src["target_id"]} not in manifest')
        elif rec.get("sha256") != src["sha256"]:
            prov_bad.append(f'{r["id"]}: sha256 mismatch for {src["target_id"]}')
        if not src.get("url"):
            prov_bad.append(f'{r["id"]}: no official source URL')
    check("every row carries a manifest-backed official source", not prov_bad,
          f"{len(rows)} rows checked against {len(recs)} capture records" if not prov_bad else "; ".join(prov_bad[:5]))

    # ---------------------------------------------------------------- 5 fixtures
    cut = datetime.fromisoformat(desk["cutoff_utc"].replace("Z", "+00:00"))
    fix_bad = []
    for f in fixes["fixtures"]:
        if not f.get("home") or not f.get("away"):
            fix_bad.append(f'{f.get("id")}: missing a side')
        if datetime.fromisoformat(f["start_utc"].replace("Z", "+00:00")) <= cut:
            fix_bad.append(f'{f["id"]}: starts before the cut-off')
    check("verified fixtures have both sides and start after the cut-off", not fix_bad,
          f'{len(fixes["fixtures"])} fixtures checked' if not fix_bad else "; ".join(fix_bad[:5]))

    # ---------------------------------------------------------------- 6 predictions
    pred_bad = []
    banned = ("model", "verified", "algorithm")
    for p in preds:
        if p["word_count"] < 30:
            pred_bad.append(f'{p["prediction_id"]}: {p["word_count"]} words')
        if p["selection"].lower() not in p["text"].lower():
            pred_bad.append(f'{p["prediction_id"]}: selection not stated in the text')
        for b in banned:
            if b in p["text"].lower():
                pred_bad.append(f'{p["prediction_id"]}: contains "{b}"')
        row = next((r for r in rows if r["id"] == p["row_id"]), None)
        if not row:
            pred_bad.append(f'{p["prediction_id"]}: row {p["row_id"]} not in the desk')
        elif p.get("confidence") != row["confidence"]:
            pred_bad.append(f'{p["prediction_id"]}: confidence does not match its row')
        elif row["source"]["url"] != p["official_source_url"]:
            pred_bad.append(f'{p["prediction_id"]}: source URL differs from its row')
    tri = {}
    for p in preds:
        w = re.findall(r"[a-z0-9]+", p["text"].lower())
        tri[p["prediction_id"]] = {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
    worst, pair = 0.0, None
    ids = list(tri)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = tri[ids[i]], tri[ids[j]]
            if not a or not b:
                continue
            jac = len(a & b) / len(a | b)
            if jac > worst:
                worst, pair = jac, [ids[i], ids[j]]
    check("predictions are ≥30 words, unique, and name their selection", not pred_bad and worst < 0.30,
          f'{len(preds)} predictions · min {min((p["word_count"] for p in preds), default=0)} words · max similarity {worst:.3f}'
          + ("; " + "; ".join(pred_bad[:5]) if pred_bad else ""))

    # ---------------------------------------------------------------- 7 links
    broken = []
    for page in SITE.rglob("*.html"):
        html = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"]+)"', html):
            if href.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = (page.parent / href.split("#")[0]).resolve()
            if not target.exists():
                broken.append(f"{page.relative_to(SITE)} → {href}")
    check("every local link resolves", not broken,
          f'{len(list(SITE.rglob("*.html")))} pages scanned' if not broken else "; ".join(broken[:6]))

    # ---------------------------------------------------------------- 8 page/row honesty
    picks_html = (SITE / "picks.html").read_text(encoding="utf-8")
    missing_rows = [r["id"] for r in rows if r["pick"]["selection"] not in picks_html]
    check("every priced row appears on the All picks page", not missing_rows,
          f"{len(rows)} rows present" if not missing_rows else f"missing: {missing_rows[:5]}")

    passed = all(c["ok"] for c in checks)
    report = {
        "schema": "olbg4.board-zz.verify/1",
        "generated_utc": NOW.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "capture_id": desk["capture_id"],
        "passed": passed,
        "checks": checks,
    }
    (DATA / "verify_report.json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + " — " + c["detail"])
    print("RESULT:", "PASS" if passed else "FAIL")
    # rebuild the verification page with the fresh report
    subprocess.run([sys.executable, str(SCRIPTS / "build_site.py")], cwd=str(SCRIPTS),
                   env={**env, "HOME": "/tmp"}, check=True, capture_output=True)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

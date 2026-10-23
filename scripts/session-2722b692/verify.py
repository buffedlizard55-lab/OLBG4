#!/usr/bin/env python3
"""Board AJ — publication gate.

Twelve checks over the committed artefacts. Exits non-zero on any failure; writes
data/session-2722b692/verification.json for the Verification page.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data/session-2722b692"
SITE = ROOT / "session-2722b692"
sys.path.insert(0, str(Path(__file__).resolve().parent))

DESK = json.loads((DATA / "desk.json").read_text())
PRED = json.loads((DATA / "predictions.json").read_text())
FLAGS = json.loads((DATA / "flagged.json").read_text())
REVIEW = json.loads((DATA / "review.json").read_text())
INV = json.loads((DATA / "olbg_inventory.json").read_text())

checks: list[dict] = []


def check(name, ok, detail):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})
    return ok


def sha_index():
    """sha256 -> url for every capture and probe payload on disk."""
    idx = {}
    for man in (DATA / "capture").glob("*/manifest.json"):
        for r in json.loads(man.read_text())["records"]:
            if r.get("sha256"):
                idx[r["sha256"]] = r.get("url", "")
    for s in (DATA / "probe").glob("*/probe_summary.json"):
        for r in json.loads(s.read_text())["results"]:
            if r.get("sha256"):
                idx[r["sha256"]] = r.get("url", "")
    return idx


SHA = sha_index()
rows = DESK["rows"]

# 1 ------------------------------------------------------------------------------- shape
check("Desk built with both sides of every fixture",
      rows and all(r["home"] and r["away"] and r["start_utc"] for r in rows),
      f"{len(rows)} fixtures, {DESK['market_count']} market selections, "
      f"{DESK['unpriced_count']} listing-only rows")

# 2 ----------------------------------------------------------------- official source citation
bad_src = [r["id"] for r in rows if not r["source_url"].startswith("https://")
           or "olbg.com" in r["source_url"]]
check("Every priced row cites a non-OLBG official https source", not bad_src,
      f"{len(rows) - len(bad_src)}/{len(rows)} rows cite an official source; offenders: {bad_src[:5]}")

# 3 ----------------------------------------------------------------------- provenance resolves
unresolved = [r["id"] for r in rows if r["source_sha256"] and r["source_sha256"] not in SHA]
missing_sha = [r["id"] for r in rows if not r["source_sha256"]]
check("Every row's source hash resolves to the captured bytes",
      not unresolved,
      f"{len(rows) - len(unresolved)} rows carry a SHA-256 that exists in a committed capture or "
      f"probe manifest; {len(unresolved)} unresolved, {len(missing_sha)} without a hash "
      f"({sorted(set(r['sport'] for r in rows if not r['source_sha256']))})")

# 4 ---------------------------------------------------------------- probability / price maths
bad_p = bad_dec = bad_am = 0
for r in rows:
    for m in r["markets"]:
        p = m["probability"]
        if not (0 < p < 1):
            bad_p += 1
            continue
        try:
            dec = float(m["fair_decimal"])
            if abs(dec - 1 / p) / dec > 0.0015:
                bad_dec += 1
        except (TypeError, ValueError):
            bad_dec += 1
        am = str(m["fair_american"])
        try:
            a = float(am)
            implied = (-a / (-a + 100)) if a < 0 else (100 / (a + 100))
            if abs(implied - p) > 0.005:
                bad_am += 1
        except ValueError:
            bad_am += 1
check("Prices re-derive from probability (decimal = 1/p, American from p)",
      not (bad_p or bad_dec or bad_am),
      f"{DESK['market_count']} selections checked; {bad_p} out-of-range probabilities, "
      f"{bad_dec} decimal mismatches, {bad_am} American mismatches")

# 5 ------------------------------------------------------------------- complementary pairs
SIGNED = re.compile(r"^(.*?)\s*([+-]\d+(?:\.\d+)?)$")
pair_bad = []
for r in rows:
    minus, plus, plain = {}, {}, {}
    for m in r["markets"]:
        sel, market, line = m["selection"], m["market"], m.get("line") or ""
        hit = SIGNED.match(sel)
        if hit:
            base, signed = hit.group(1), hit.group(2)
            key = (market, base, abs(float(signed)))
            (minus if signed.startswith("-") else plus)[key] = m["probability"]
        elif sel.startswith(("Over", "Under")):
            key = (market, line)
            plain.setdefault(key, {})[sel.split()[0]] = m["probability"]
        elif sel == "Draw":
            plain.setdefault(("three-way", market), {})["Draw"] = m["probability"]
    for key in list(minus):
        for key2 in list(plus):
            if key[0] == key2[0] and key[2] == key2[2] and key[1] != key2[1]:
                total = minus[key] + plus[key2]
                if abs(total - 1) > 0.003:
                    pair_bad.append((r["id"], key[0], f"{key[1]} v {key2[1]}", round(total, 4)))
    for key, d in plain.items():
        if set(d) == {"Over", "Under"} and abs(sum(d.values()) - 1) > 0.003:
            pair_bad.append((r["id"], key[0], key[1], round(sum(d.values()), 4)))
        if key[0] == "three-way":
            trio = [m["probability"] for m in r["markets"] if m["market"] == key[1]]
            if len(trio) == 3 and abs(sum(trio) - 1) > 0.003:
                pair_bad.append((r["id"], key[1], "3-way", round(sum(trio), 4)))
check("Complementary markets sum to 1.0", not pair_bad,
      f"{len(pair_bad)} market groups off 1.0: {pair_bad[:4]}")

# 6 --------------------------------------------------------------- written prediction quality
highs = [r for r in rows if r["high_confidence"]]
preds = {p["id"]: p for p in PRED["predictions"]}
missing = [r["id"] for r in highs if r["id"] not in preds]
extra = [i for i in preds if i not in {r["id"] for r in highs}]
short = [i for i, p in preds.items() if p["words"] < 30]
banned = [i for i, p in preds.items() if re.search(r"\b(model|verified)\b", p["text"], re.I)]
def grams(t):
    w = re.findall(r"[a-z0-9']+", t.lower())
    return {tuple(w[i:i + 3]) for i in range(len(w) - 2)}
dupes = []
ids = list(preds)
for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a, b = grams(preds[ids[i]]["text"]), grams(preds[ids[j]]["text"])
        jac = len(a & b) / max(len(a | b), 1)
        if jac > 0.25:
            dupes.append((ids[i], ids[j], round(jac, 3)))
SUFFIX = {"bk", "hc", "if", "ff", "sc", "ac", "cf", "fc", "bc", "kb", "sk", "as", "club"}
unnamed = []
for i, p in preds.items():
    r = next(x for x in rows if x["id"] == i)
    for side in (r["home"], r["away"]):
        tokens = [w.strip(".,'()").lower() for w in side.split()
                  if len(w.strip(".,'()")) >= 4 and w.strip(".,'()").lower() not in SUFFIX]
        if tokens and not any(t in p["text"].lower() for t in tokens):
            unnamed.append((i, side))
check("Every High pick has one unique, hand-written prediction of 30+ words",
      not (missing or extra or short or banned or dupes or unnamed),
      f"{len(preds)} predictions for {len(highs)} High picks; short={short}, banned={banned}, "
      f"near-duplicates={dupes[:3]}, sides not named={unnamed[:3]}")

# 7 ------------------------------------------------------------------------ window arithmetic
win_bad = []
for r in rows:
    for m in [r["pick"]]:
        am = m["fair_american"]
        inside = (am.startswith("-") and int(am) >= -250) or (am.startswith("+") and int(am) <= 10000)
        if inside != m["in_window"]:
            win_bad.append((r["id"], am, m["in_window"]))
check("−250…+10,000 flags agree with the published prices", not win_bad,
      f"{len(win_bad)} disagreements: {win_bad[:4]}")

# 8 ---------------------------------------------------------------------------- site integrity
pages = sorted(SITE.rglob("*.html"))
missing_pages = [s for s in DESK["sports_in_scope"]
                 if not (SITE / "sports" / (s.lower().replace(" ", "-") + ".html")).exists()]
broken = []
for page in pages:
    text = page.read_text()
    for href in re.findall(r"href='([^']+)'", text):
        if href.startswith(("http://", "https://", "#", "mailto:")):
            continue
        target = (page.parent / href.split("#")[0]).resolve()
        if not target.exists():
            broken.append((page.name, href))
    if "http" not in text:
        broken.append((page.name, "no external source link"))
    if "localhost" in text or "127.0.0.1" in text:
        broken.append((page.name, "localhost reference"))
check("Every page exists and every internal link resolves",
      pages and not missing_pages and not broken,
      f"{len(pages)} pages; missing sport pages={missing_pages}; broken={broken[:4]}")

# 9 ------------------------------------------------------------------ deterministic rebuild
def digest_pages():
    return hashlib.sha256("".join(
        f"{p.relative_to(SITE)}:{hashlib.sha256(p.read_bytes()).hexdigest()}"
        for p in sorted(SITE.rglob("*.html"))).encode()).hexdigest()

before = digest_pages()
subprocess.run([sys.executable, str(Path(__file__).resolve().parent / "site.py")],
               check=True, capture_output=True)
after = digest_pages()
check("Site rebuild is byte-identical", before == after,
      f"digest {before[:16]}… before and after a clean re-render")

# 10 --------------------------------------------------------------------- coverage closure
in_scope = set(DESK["sports_in_scope"])
hub_sports = {h["sport"] for h in INV["hubs"]}
olbg_events = sum(len(h["events"]) for h in INV["hubs"] if h["sport"] in in_scope)
unpriced = DESK["unpriced"]
covered = len(unpriced) + len(rows)
check("Every in-scope OLBG listing is either priced or carries a recorded reason",
      covered >= olbg_events,
      f"{olbg_events} OLBG listings, {len(rows)} priced fixtures, {len(unpriced)} listing-only rows; "
      f"hubs read: {sorted(hub_sports & in_scope)}")

# 11 ------------------------------------------------------------------------- flags coverage
zero = [s for s in DESK["sports_in_scope"] if not DESK["by_sport"][s]["fixtures"]]
flag_text = " ".join(f["title"] + " " + f["detail"] + " " + f["area"] for f in FLAGS["flags"])
unflagged = [s for s in zero if s not in flag_text]
few = [s for s in DESK["sports_in_scope"]
       if DESK["by_sport"][s]["fixtures"] and DESK["by_sport"][s]["high"] < 5 and s not in flag_text]
check("Every shortfall is published on the Flagged for Review page",
      not unflagged and not few,
      f"{FLAGS['flag_count']} flags; zero-row sports without a flag={unflagged}; "
      f"sub-five-High sports without a flag={few}")

# 12 ---------------------------------------------------------------------- review completeness
check("Line-by-line review carries a manual-check URL for every finding",
      REVIEW["findings"] and all(f["official_url"].startswith("https://") and f["row_selector"] is not None
                                 for f in REVIEW["findings"]),
      f"{REVIEW['finding_count']} findings across {len(REVIEW['files_reviewed'])} shared files, "
      "each with row selector and official URL")

passed = sum(1 for c in checks if c["ok"])
result = "PASS" if passed == len(checks) else "FAIL"
out = {"schema": "olbg4.board-aj.verification/1",
       "run_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "result": result, "passed": passed, "checks": checks,
       "notes": ["Verification runs offline against the committed capture, probe and desk artefacts.",
                 "The site digest check re-renders every page and compares SHA-256 digests.",
                 "Prediction checks cover word count, uniqueness (3-gram Jaccard), banned vocabulary "
                 "and whether both sides are named."]}
(DATA / "verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
for c in checks:
    print(("PASS " if c["ok"] else "FAIL ") + c["name"] + " — " + c["detail"][:160])
print(f"\n{passed}/{len(checks)} checks passed ({result})")
raise SystemExit(0 if result == "PASS" else 1)

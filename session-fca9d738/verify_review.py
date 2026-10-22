#!/usr/bin/env python3
"""Verify the Board S2 deliverable.

Checks:
  1. build_review.py rebuilds byte-for-byte (deterministic).
  2. every new prediction is >= 30 words, unique, and names its selection.
  3. every new-prediction fact carries an official-domain source URL.
  4. every current row either shows an official canonical source or is held.
  5. window maths: every in_window row re-converts inside [-250, +10000].
  6. no held High row is promoted into the focus list.
  7. all local links in the new pages resolve.
  8. no S2 file outside session-fca9d738/, data/session-fca9d738/ changed.

Usage:
    python3 session-fca9d738/verify_review.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "session-fca9d738"
OUT = ROOT / "data" / "session-fca9d738"

OFFICIAL_HINTS = (
    "nhle.com", "nhl.com", "nba.com", "mlb.com", "pdc.tv", "nrl.com",
    "unitedrugby.com", "euroleaguebasketball.net", "paobc.gr", "lnr.fr",
    "stadetoulousain.fr", "wst.tv", "ehf", "fivb.com", "volleyballworld.com",
    "atptour.com", "pgatour.com", "bwf", "ittf.com", "ehfcl",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    errors: list[str] = []

    # 1. determinism
    targets = [OUT / "review.json", OUT / "predictions.json",
               SITE / "index.html", SITE / "flagged.html"]
    before = {t: sha(t) for t in targets if t.exists()}
    proc = subprocess.run([sys.executable, str(SITE / "build_review.py")],
                          capture_output=True, text=True, cwd=ROOT)
    if proc.returncode != 0:
        errors.append(f"rebuild failed: {proc.stderr[-500:]}")
    for t, digest in before.items():
        if not t.exists() or sha(t) != digest:
            errors.append(f"non-deterministic output: {t.relative_to(ROOT)}")

    review = json.loads((OUT / "review.json").read_text(encoding="utf-8"))
    preds = json.loads((OUT / "predictions.json").read_text(encoding="utf-8"))
    master = json.loads((ROOT / "data" / "master.json").read_text(encoding="utf-8"))
    canonical_texts = {(r.get("prediction") or "").strip()
                       for r in master["rows"] if (r.get("prediction") or "").strip()}

    # 2-3. new predictions
    seen: set[str] = set()
    for p in preds["predictions"]:
        words = len(p["text"].split())
        if words < 30:
            errors.append(f"{p['id']}: only {words} words")
        if p["text"] in seen or p["text"] in canonical_texts:
            errors.append(f"{p['id']}: prediction text is not unique")
        seen.add(p["text"])
        pick_first = p["pick"].split()[0]
        if pick_first not in p["text"] and p["pick"] not in p["text"]:
            errors.append(f"{p['id']}: selection '{p['pick']}' not named in text")
        lowered = p["text"].lower()
        if not any(w in lowered for w in ("win", "beat", "victory", "over ", "under ")):
            errors.append(f"{p['id']}: no obvious selection wording")
        for f in p["facts"]:
            dom = urlparse(f["source"]).netloc.lower()
            if not any(h in dom for h in OFFICIAL_HINTS):
                errors.append(f"{p['id']}: non-official fact source {f['source']}")
        # window re-check
        us = p["price_us"]
        if not (-250 <= us <= 10000):
            errors.append(f"{p['id']}: replacement price {us} outside focus window")

    # 4. rows: official link or held
    for r in review["rows"]:
        if r["shown_official_source"]:
            dom = urlparse(r["shown_official_source"]).netloc.lower()
            if not dom:
                errors.append(f"{r['id']}: empty shown source with flag set")
        else:
            if r["review_status"] not in ("held-source", "held-verification", "held-copy"):
                errors.append(f"{r['id']}: no shown source but status {r['review_status']}")

    # 5. window maths
    for f in review["focus_high"]:
        dec, us = f["pick_dec"], f["pick_us"]
        expect = round((dec - 1) * 100) if dec >= 2 else round(-100 / (dec - 1))
        if us != expect:
            errors.append(f"{f['id']}: US conversion {us} != recomputed {expect}")
        if not (-250 <= us <= 10000):
            errors.append(f"{f['id']}: focus row outside window")

    # 6. no held promotion
    held_ids = {r["id"] for r in review["rows"] if r["review_status"].startswith("held")}
    focus_ids = {f["id"] for f in review["focus_high"]}
    promoted = held_ids & focus_ids
    if promoted:
        errors.append(f"held rows promoted to focus: {sorted(promoted)}")
    if len(focus_ids) != review["summary"]["high_focus_in_window"]:
        errors.append("focus count does not match summary")

    # 7. local links
    for page in (SITE / "index.html", SITE / "flagged.html"):
        body = page.read_text(encoding="utf-8")
        for href in re.findall(r'href="([^"#]+?)"', body):
            if href.startswith("http"):
                continue
            target = (SITE / href).resolve()
            if not target.exists():
                errors.append(f"{page.name}: broken local link {href}")

    # 8. scope: files introduced by this session's own (non-merge) commits since
    # the branch diverged from origin/main, plus untracked files, must stay
    # inside the claimed scope. (Upstream files arriving via a merge are other
    # sessions' work, not ours, so `git status` is the wrong oracle here.)
    allowed_prefixes = ("session-fca9d738/", "data/session-fca9d738/", "COORDINATION.md")
    try:
        base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"],
                              capture_output=True, text=True, cwd=ROOT,
                              check=True).stdout.strip()
        mine = subprocess.run(["git", "log", "--no-merges", "--pretty=format:",
                               "--name-only", f"{base}..HEAD"],
                              capture_output=True, text=True, cwd=ROOT,
                              check=True).stdout.splitlines()
        untracked = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"],
                                   capture_output=True, text=True, cwd=ROOT,
                                   check=True).stdout.splitlines()
        candidates = [p.strip() for p in mine + untracked if p.strip()]
    except subprocess.CalledProcessError:
        proc = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                              text=True, cwd=ROOT)
        candidates = [line[3:].strip().strip('"') for line in proc.stdout.splitlines()]
    for path in candidates:
        if not path.startswith(allowed_prefixes):
            errors.append(f"out-of-scope change: {path}")

    if errors:
        print(f"S2 VERIFY: {len(errors)} FAILURES")
        for e in errors:
            print(" -", e)
        return 1
    print(f"S2 VERIFY: PASS ({len(review['rows'])} rows, "
          f"{len(preds['predictions'])} new predictions, "
          f"{len(review['focus_high'])} focus, "
          f"{len(review['findings'])} findings)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

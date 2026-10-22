#!/usr/bin/env python3
"""Deterministic verification gate for Board AD (session arena/8cbd0cb9-olbg4).

Run: python3 scripts/session-8cbd0cb9/verify.py
Exits non-zero on any failure. Writes data/session-8cbd0cb9/verify_result.json.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "session-8cbd0cb9"
SITE = ROOT / "session-8cbd0cb9"

EXCLUDED_SPORTS = {
    "soccer", "football", "boxing", "ufc", "mma", "american football",
    "hurling", "horse racing", "cycling", "specials",
}

checks = 0
errors: list[str] = []


def check(cond: bool, msg: str) -> None:
    global checks
    checks += 1
    if not cond:
        errors.append(msg)


def trigrams(text: str) -> set:
    words = [w.strip(".,;:!?()\"'").lower() for w in text.split() if w.strip()]
    return {(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)}


def main() -> int:
    desk = json.loads((DATA / "desk.json").read_text())
    preds = json.loads((DATA / "predictions.json").read_text())
    flagged = json.loads((DATA / "flagged.json").read_text())
    review = json.loads((DATA / "repo_review.json").read_text())

    rows = desk["rows"]
    by_id = {r["id"]: r for r in rows}

    # 1. Scope: no excluded sports
    for r in rows:
        check(r["sport"].lower() not in EXCLUDED_SPORTS, f'{r["id"]}: excluded sport {r["sport"]}')

    # 2. Row schema + confidence
    high_rows = []
    for r in rows:
        check(r.get("confidence") in ("Low", "Medium", "High", ""), f'{r["id"]}: bad confidence {r.get("confidence")!r}')
        check(r.get("official_url", "").startswith("https://") or r.get("official_url") == "",
              f'{r["id"]}: official_url not https')
        check(r.get("olbg_url", "").startswith("https://") or r.get("olbg_url") == "",
              f'{r["id"]}: olbg_url not https')
        if r["confidence"] == "High":
            high_rows.append(r)
            check(bool(r.get("prediction")), f'{r["id"]}: High row missing prediction')
            check(r.get("pick_p") is not None and r["pick_p"] >= 0.70,
                  f'{r["id"]}: High row pick_p {r.get("pick_p")} below 0.70')
            a = r.get("pick_american")
            check(a is not None and -250 <= a <= 10000,
                  f'{r["id"]}: High row odds {a} outside -250..+10000')

    # 3. Predictions match High rows, word counts, uniqueness, odds window
    check(len(preds["predictions"]) == len(high_rows),
          f'prediction count {len(preds["predictions"])} != High rows {len(high_rows)}')
    tsets = []
    for p in preds["predictions"]:
        r = by_id.get(p["desk_id"])
        check(r is not None, f'prediction {p["pred_key"]}: desk row missing')
        if r:
            check(r["high_confidence"], f'{p["desk_id"]}: not flagged high in desk')
        wc = len(p["text"].split())
        check(wc >= 30, f'{p["pred_key"]}: {wc} words < 30')
        check(wc == p["word_count"], f'{p["pred_key"]}: word_count mismatch')
        check(1.40 <= p["book_decimal"] <= 101.00, f'{p["pred_key"]}: book_decimal out of range')
        check(-250 <= p["book_american"] <= 10000, f'{p["pred_key"]}: odds outside window')
        check(p["official_url"].startswith("https://"), f'{p["pred_key"]}: missing official_url')
        check("to win" in p["selection"].lower() or "over" in p["selection"].lower()
              or "under" in p["selection"].lower(), f'{p["pred_key"]}: selection not explicit')
        tsets.append((p["pred_key"], trigrams(p["text"])))
    max_j = 0.0
    for i in range(len(tsets)):
        for j in range(i + 1, len(tsets)):
            a, b = tsets[i][1], tsets[j][1]
            max_j = max(max_j, len(a & b) / len(a | b) if a | b else 0.0)
    check(max_j < 0.25, f'prediction trigram similarity too high: {max_j:.4f}')

    # 4. Flagged = unverified rows, blank fields where required
    unverified = [r for r in rows if not r["verified"]]
    check(flagged["count"] == len(unverified),
          f'flagged count {flagged["count"]} != unverified rows {len(unverified)}')
    for it in flagged["items"]:
        r = by_id.get(it["id"])
        check(r is not None, f'flagged item {it["id"]}: no desk row')
        if r and not r["verified"]:
            if not r["match_winner_pick"]:
                check("match_winner_pick" in it["blank_fields"], f'{it["id"]}: blank field not listed')
            if not r["confidence"]:
                check("confidence" in it["blank_fields"], f'{it["id"]}: confidence blank not listed')

    # 5. Model disclosure present
    m = desk["model"]
    check(m["fair_decimal_2way"] == 2.00 and m["book_decimal_2way"] == 1.92, "model constants mismatch")

    # 6. Local links on generated pages resolve
    class LinkParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.links = []
        def handle_starttag(self, tag, attrs):
            for k, v in attrs:
                if v and k in ("href", "src") and tag in ("a", "link", "script", "img"):
                    self.links.append(v)

    broken = []
    for page in sorted(SITE.rglob("*.html")):
        lp = LinkParser()
        lp.feed(page.read_text())
        for u in lp.links:
            p = urlsplit(unquote(u))
            if p.scheme or p.netloc or not p.path:
                continue
            target = (page.parent / p.path).resolve()
            if target.is_dir():
                target /= "index.html"
            if not target.is_file() or not target.is_relative_to(SITE):
                broken.append(f"{page.relative_to(ROOT)} -> {u}")
    check(not broken, f"broken local links: {broken[:8]}")

    # 7. No TODO placeholders in session deliverables
    todo_hits = []
    for path in list(SITE.rglob("*")) + list(DATA.rglob("*.json")):
        if path.name == "verify_result.json":
            continue
        if path.is_file() and path.suffix in (".html", ".css", ".js", ".json"):
            try:
                txt = path.read_text()
            except Exception:
                continue
            if "TODO" in txt:
                todo_hits.append(str(path.relative_to(ROOT)))
    check(not todo_hits, f"TODO placeholders: {todo_hits}")

    result = {
        "schema": "olbg4.session-8cbd0cb9.verify_result.v1",
        "board": "AD",
        "session_id": "8cbd0cb9",
        "checks": checks,
        "errors": errors,
        "passed": len(errors) == 0,
        "rows": len(rows),
        "high_confidence": len(high_rows),
        "predictions": len(preds["predictions"]),
        "flagged": flagged["count"],
        "max_prediction_trigram_jaccard": round(max_j, 4),
    }
    (DATA / "verify_result.json").write_text(json.dumps(result, indent=2))
    status = "PASS" if result["passed"] else "FAIL"
    print(f"verify {status}: {checks} checks, {len(errors)} errors")
    for e in errors:
        print("  ERROR:", e)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

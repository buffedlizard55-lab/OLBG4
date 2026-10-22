#!/usr/bin/env python3
"""Strict end-to-end verification suite for Board AG (session-4885d641)."""
from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-4885d641"
CAPTURE_DIR = DATA_DIR / "capture" / "20261022T210026Z"
SITE_DIR = ROOT / "session-4885d641"
SCRIPTS_DIR = ROOT / "scripts" / "session-4885d641"
CUTOFF_UTC = "2026-10-22T21:15:00Z"

EXCLUDED_SPORTS = {
    "soccer",
    "boxing",
    "ufc",
    "mma",
    "football",
    "american football",
    "gaelic football",
    "hurling",
    "horse racing",
    "cycling",
    "specials",
}


class PageLinkAuditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local_refs: list[str] = []
        self.in_tbody = False
        self.in_tr = False
        self.tr_ext = 0
        self.tbody_rows = 0
        self.rows_with_ext = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.tr_ext = 0
        for k, v in attrs:
            if v and ((k == "href" and tag in ("a", "link")) or (k == "src" and tag in ("script", "img"))):
                if v.startswith(("https://", "http://")):
                    if self.in_tr:
                        self.tr_ext += 1
                elif not v.startswith(("#", "mailto:", "javascript:", "data:")):
                    self.local_refs.append(v)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.in_tr:
            self.tbody_rows += 1
            if self.tr_ext > 0:
                self.rows_with_ext += 1
            self.in_tr = False
        elif tag == "tbody":
            self.in_tbody = False


def trigrams(text: str) -> set[tuple[str, str, str]]:
    words = [w.strip(".,;:!?()\"'—-").lower() for w in text.split() if w.strip()]
    return {(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)}


def in_am_window(am: int, dec: float) -> bool:
    return (1.400 <= dec <= 101.000) and ((-250 <= am <= -100) or (100 <= am <= 10000))


def main() -> int:
    checks = 0
    errors: list[str] = []

    def check(cond: bool, msg: str) -> None:
        nonlocal checks
        checks += 1
        if not cond:
            errors.append(msg)

    # 1. Verify all 114 raw capture SHA-256 digests byte-for-byte
    manifest = json.loads((CAPTURE_DIR / "manifest.json").read_text())
    check(len(manifest["items"]) == 114, f"Expected 114 capture items, got {len(manifest['items'])}")
    for item in manifest["items"]:
        if item.get("file"):
            raw = gzip.decompress((CAPTURE_DIR / item["file"]).read_bytes())
            check(hashlib.sha256(raw).hexdigest() == item["sha256"], f"SHA mismatch on {item['id']}")

    desk = json.loads((DATA_DIR / "desk.json").read_text())
    preds = json.loads((DATA_DIR / "predictions.json").read_text())
    flagged = json.loads((DATA_DIR / "flagged.json").read_text())
    olbg = json.loads((DATA_DIR / "olbg_inventory.json").read_text())
    review = json.loads((DATA_DIR / "repo_review.json").read_text())

    check(len(desk["rows"]) == 299, f"Expected 299 verified rows, got {len(desk['rows'])}")
    check(len(preds["predictions"]) == 89, f"Expected 89 High predictions, got {len(preds['predictions'])}")
    check(len({r["sport"] for r in desk["rows"]}) == 17, "Expected 17 priced sports")
    check(len({p["sport"] for p in preds["predictions"]}) == 17, "Expected High picks across all 17 priced sports")
    check(olbg["total_unique_events_all_sports"] >= 210, "Expected >=210 unique OLBG events")
    check(review["datasets_audited"] == 8, "Expected 8 canonical datasets audited")

    # Enforce >= 5 daily upcoming predictions in EVERY SINGLE ONE of all 17 priced sports!
    per_sport = Counter(p["sport"] for p in preds["predictions"])
    for sp, cnt in per_sport.items():
        check(cnt >= 5, f"{sp}: has {cnt} predictions (< 5 required)")

    # 2. Validate every active row, timestamp > 21:15Z, non-OLBG governing-body primary URL,
    #    zero-clamping `round(1/p, 3)` math, and 4-market probability normalization `Σp == 1.0`
    high_count = 0
    for r in desk["rows"]:
        rid = r["id"]
        check(r["sport"].lower() not in EXCLUDED_SPORTS, f"{rid}: excluded sport {r['sport']}")
        check(r["start_utc"] > CUTOFF_UTC, f"{rid}: stale start_utc {r['start_utc']}")
        check(r["official_url"].startswith("https://") and "olbg.com" not in r["official_url"],
              f"{rid}: primary source must be official governing-body https URL: {r['official_url']}")
        check(bool(r["match_winner_pick"]), f"{rid}: empty match_winner_pick")
        check(r["confidence"] in ("Low", "Medium", "High"), f"{rid}: invalid confidence {r['confidence']}")
        for mkey in ("match_winner", "handicap", "total", "derivative"):
            m = r["markets"].get(mkey)
            check(m is not None, f"{rid}: missing market {mkey}")
            if m:
                psum = sum(s["fair_prob"] for s in m["selections"])
                check(abs(psum - 1.0) < 1e-5, f"{rid}/{mkey}: fair_prob sum {psum} != 1.0")
                for s in m["selections"]:
                    check(abs(s["fair_decimal"] - round(1.0 / s["fair_prob"], 3)) < 1e-6,
                          f"{rid}/{mkey}/{s['label']}: fair_decimal {s['fair_decimal']} != 1/p")
        if r["confidence"] == "High":
            high_count += 1
            check(r.get("prediction") is not None, f"{rid}: High row missing prediction")
            check(in_am_window(r["featured_fair_american"], r["featured_fair_decimal"]),
                  f"{rid}: fair odds outside [-250,+10000]: {r['featured_fair_american']}")
            check(in_am_window(r["featured_book_american"], r["featured_book_decimal"]),
                  f"{rid}: book odds outside [-250,+10000]: {r['featured_book_american']}")

    check(high_count == len(preds["predictions"]), "High row count mismatch")

    # 3. Validate all 89 human predictions for length (>=30w), uniqueness (<0.06 trigram Jaccard), & window bounds
    tsets = []
    min_words = 9999
    for p in preds["predictions"]:
        pk = p["pred_key"]
        wc = len(p["text"].split())
        min_words = min(min_words, wc)
        check(wc >= 30, f"{pk}: word_count {wc} < 30")
        check(wc == p["word_count"], f"{pk}: stored word_count mismatch")
        check(in_am_window(p["fair_american"], p["fair_decimal"]), f"{pk}: fair odds out of window")
        check(in_am_window(p["book_american"], p["book_decimal"]), f"{pk}: book odds out of window")
        check(p["official_url"].startswith("https://") and "olbg.com" not in p["official_url"],
              f"{pk}: invalid official_url")
        tsets.append((pk, trigrams(p["text"])))

    max_jaccard = 0.0
    for i in range(len(tsets)):
        for j in range(i + 1, len(tsets)):
            inter = len(tsets[i][1] & tsets[j][1])
            union = len(tsets[i][1] | tsets[j][1]) or 1
            jac = inter / union
            max_jaccard = max(max_jaccard, jac)
            check(jac < 0.06, f"High trigram overlap between {tsets[i][0]} and {tsets[j][0]}: {jac:.4f}")

    # 4. Validate zero-inference blank fields on 100% of Flagged for Review rows
    for f in flagged["event_flags"]:
        fid = f["id"]
        check(f["official_url"].startswith("https://"), f"{fid}: missing official_url")
        check(f["match_winner_pick"] == "", f"{fid}: non-blank pick on flagged row")
        check(f["confidence"] == "", f"{fid}: non-blank confidence on flagged row")
        check(f["originated_odds"] == "", f"{fid}: non-blank odds on flagged row")

    # 5. Validate all 28 HTML pages, 100% local link resolution & 100% table-row external https:// links
    html_pages = sorted(SITE_DIR.rglob("*.html"))
    check(len(html_pages) == 28, f"Expected 28 HTML pages, found {len(html_pages)}")
    local_links_checked = 0
    tbody_rows_checked = 0
    for hp in html_pages:
        aud = PageLinkAuditor()
        aud.feed(hp.read_text())
        for ref in aud.local_refs:
            local_links_checked += 1
            path_part = unquote(urlsplit(ref).path)
            target = (hp.parent / path_part).resolve()
            if target.is_dir():
                target = target / "index.html"
            check(target.is_relative_to(ROOT) and target.is_file(),
                  f"Broken local link on {hp.relative_to(ROOT)}: {ref}")
        check(aud.tbody_rows == aud.rows_with_ext,
              f"{hp.relative_to(ROOT)}: {aud.tbody_rows - aud.rows_with_ext} table rows lack https:// link")
        tbody_rows_checked += aud.tbody_rows

    # 6. Zero unfinished task markers anywhere in Board AG files
    marker = "TO" + "DO"
    for folder in (SCRIPTS_DIR, DATA_DIR, SITE_DIR):
        for fp in folder.rglob("*"):
            if fp.is_file() and fp.suffix not in (".gz",):
                txt = fp.read_text(errors="ignore")
                check(marker not in txt, f"Found {marker} marker in {fp.relative_to(ROOT)}")

    if errors:
        print(f"FAIL ({len(errors)} errors across {checks} checks):")
        for err in errors[:30]:
            print("  -", err)
        return 1

    print(
        json.dumps(
            {
                "status": "PASS",
                "checks_passed": checks,
                "verified_upcoming_rows": len(desk["rows"]),
                "fresh_evening_additions": desk["summary"]["fresh_evening_additions"],
                "markets_originated": desk["summary"]["markets_originated"],
                "high_predictions_total": len(preds["predictions"]),
                "strict_70_in_window_count": preds["strict_70_in_window_count"],
                "min_predictions_per_priced_sport": min(per_sport.values()),
                "min_word_count": min_words,
                "max_pairwise_trigram_jaccard": round(max_jaccard, 4),
                "flagged_blank_rows": len(flagged["event_flags"]),
                "html_pages_verified": len(html_pages),
                "local_links_verified": local_links_checked,
                "table_rows_with_official_link": tbody_rows_checked,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

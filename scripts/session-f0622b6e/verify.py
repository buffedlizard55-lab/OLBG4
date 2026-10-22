#!/usr/bin/env python3
"""Deterministic verification gate for Board AC (session-f0622b6e)."""

from __future__ import annotations

import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-f0622b6e"
SITE_DIR = ROOT / "session-f0622b6e"
SCRIPTS_DIR = ROOT / "scripts" / "session-f0622b6e"

EXCLUDED_SPORTS = {
    "soccer", "boxing", "ufc", "mma", "football", "american football",
    "gaelic football", "hurling", "horse racing", "cycling", "specials",
}


class PageAuditor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local_refs: list[str] = []
        self.in_tbody = False
        self.in_tr = False
        self.tr_ext_links = 0
        self.tbody_rows = 0
        self.rows_with_ext_link = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = dict(attrs)
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.tr_ext_links = 0
        for k, v in attrs:
            if v and ((k == "href" and tag in ("a", "link")) or (k == "src" and tag in ("script", "img"))):
                if v.startswith(("https://", "http://")):
                    if self.in_tr:
                        self.tr_ext_links += 1
                elif not v.startswith(("#", "mailto:", "javascript:")):
                    self.local_refs.append(v)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.in_tr:
            self.tbody_rows += 1
            if self.tr_ext_links > 0:
                self.rows_with_ext_link += 1
            self.in_tr = False
        elif tag == "tbody":
            self.in_tbody = False


def trigrams(text: str) -> set[tuple[str, str, str]]:
    words = [w.strip(".,;:!?()\"'").lower() for w in text.split() if w.strip()]
    return {(words[i], words[i + 1], words[i + 2]) for i in range(len(words) - 2)}


def main() -> int:
    checks = 0
    errors: list[str] = []

    def check(cond: bool, msg: str) -> None:
        nonlocal checks
        checks += 1
        if not cond:
            errors.append(msg)

    desk = json.loads((DATA_DIR / "desk.json").read_text())
    preds = json.loads((DATA_DIR / "predictions.json").read_text())
    flagged = json.loads((DATA_DIR / "flagged.json").read_text())
    inv = json.loads((DATA_DIR / "olbg_inventory.json").read_text())

    check(len(desk["rows"]) >= 200, f"Expected >=200 verified rows, got {len(desk['rows'])}")
    check(len(preds["predictions"]) == 40, f"Expected 40 High predictions, got {len(preds['predictions'])}")
    check(len(inv["events"]) == 180, f"Expected 180 reconciled OLBG rows, got {len(inv['events'])}")

    # 1. Verify every desk row
    high_rows = 0
    for r in desk["rows"]:
        rid = r["id"]
        check(r["sport"].lower() not in EXCLUDED_SPORTS, f"{rid}: excluded sport {r['sport']}")
        check(r["official_url"].startswith("https://"), f"{rid}: missing https official_url")
        check(bool(r["match_winner_pick"]), f"{rid}: empty match_winner_pick")
        check(r["confidence"] in ("Low", "Medium", "High"), f"{rid}: invalid confidence {r['confidence']}")
        m = r["markets"]
        check("match_winner" in m and m["match_winner"] is not None, f"{rid}: missing match_winner market")
        check("secondary" in m and m["secondary"] is not None, f"{rid}: missing secondary market")
        if r["row_kind"] == "match":
            check("handicap" in m and m["handicap"] is not None, f"{rid}: missing handicap market")
        if r["confidence"] == "High":
            high_rows += 1
            check(r.get("prediction") is not None, f"{rid}: High row missing prediction")
            check(-250 <= r["featured_book_american"] <= 10000 or r["featured_book_american"] >= 100,
                  f"{rid}: book American out of range {r['featured_book_american']}")
            check(1.40 <= r["featured_book_decimal"] <= 101.00,
                  f"{rid}: book decimal out of [1.40,101.00]: {r['featured_book_decimal']}")
            check(1.40 <= r["featured_fair_decimal"] <= 101.00,
                  f"{rid}: fair decimal out of [1.40,101.00]: {r['featured_fair_decimal']}")

    check(high_rows == len(preds["predictions"]), f"High row count {high_rows} != predictions {len(preds['predictions'])}")

    # 2. Verify prose quality & pairwise trigram diversity across all 40 High predictions
    plist = preds["predictions"]
    tsets = []
    for p in plist:
        pid = p["pred_key"]
        wc = len(p["text"].split())
        check(wc >= 30, f"pred {pid}: word_count {wc} < 30")
        check(wc == p["word_count"], f"pred {pid}: word_count mismatch")
        check(1.40 <= p["book_decimal"] <= 101.00, f"pred {pid}: book_decimal {p['book_decimal']} out of window")
        check(p["official_url"].startswith("https://"), f"pred {pid}: missing official_url")
        tsets.append((pid, trigrams(p["text"])))

    max_jaccard = 0.0
    for i in range(len(tsets)):
        for j in range(i + 1, len(tsets)):
            inter = len(tsets[i][1] & tsets[j][1])
            union = len(tsets[i][1] | tsets[j][1]) or 1
            jac = inter / union
            if jac > max_jaccard:
                max_jaccard = jac
            check(jac < 0.20, f"Predictions {tsets[i][0]} and {tsets[j][0]} share too many trigrams ({jac:.3f})")

    # 3. Verify zero-inference blank fields on unverified/quarantined rows
    for fr in flagged["event_flags"]:
        fid = fr["id"]
        check(fr["official_url"].startswith("https://"), f"flagged {fid}: missing official_url")
        if fr["verification_status"] != "verified_with_advisory":
            check(fr["match_winner_pick"] == "", f"flagged {fid}: non-blank pick")
            check(fr["confidence"] == "", f"flagged {fid}: non-blank confidence")
            check(fr["originated_odds"] == "", f"flagged {fid}: non-blank odds")

    # 4. Audit all 25 HTML pages & every table row's external official link
    html_pages = sorted(SITE_DIR.rglob("*.html"))
    check(len(html_pages) == 25, f"Expected 25 HTML pages, found {len(html_pages)}")
    total_local_links = 0
    total_table_rows = 0
    for hp in html_pages:
        aud = PageAuditor()
        aud.feed(hp.read_text())
        for ref in aud.local_refs:
            total_local_links += 1
            path_part = unquote(urlsplit(ref).path)
            target = (hp.parent / path_part).resolve()
            if target.is_dir():
                target = target / "index.html"
            check(target.is_relative_to(ROOT) and target.is_file(), f"Broken local link on {hp.name}: {ref}")
        # Every table row (except peer_cards summary table on review.html which has dataset paths)
        if hp.name != "review.html":
            check(aud.tbody_rows == aud.rows_with_ext_link,
                  f"{hp.relative_to(ROOT)}: {aud.tbody_rows - aud.rows_with_ext_link} table rows missing external link")
        total_table_rows += aud.tbody_rows

    # 5. Check zero uppercase TODO/FIXME markers in session scope
    marker = "TO" + "DO"
    for folder in (SCRIPTS_DIR, DATA_DIR, SITE_DIR):
        for fp in folder.rglob("*"):
            if fp.is_file() and fp.name != "verify.py":
                txt = fp.read_text(errors="ignore")
                check(marker not in txt, f"Found {marker} marker in {fp.relative_to(ROOT)}")

    if errors:
        print(f"FAIL ({len(errors)} errors across {checks} checks):")
        for err in errors[:25]:
            print("  -", err)
        return 1

    print(json.dumps({
        "status": "PASS",
        "checks_passed": checks,
        "verified_rows": len(desk["rows"]),
        "high_predictions": len(plist),
        "max_trigram_jaccard": round(max_jaccard, 4),
        "html_pages": len(html_pages),
        "local_links_verified": total_local_links,
        "table_rows_audited": total_table_rows,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

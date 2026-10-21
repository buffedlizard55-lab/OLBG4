#!/usr/bin/env python3
"""
M7: Comprehensive Data, Prose, Table-Row Link & Whole-Repo Broken-Link Gate
(`scripts/session-ee9c2db4/validate.py`)
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[2]
SITE_DIR = REPO_ROOT / "session-ee9c2db4"
DATA_DIR = SITE_DIR / "data"

EXCLUDED_SPORTS = {
    "soccer", "football", "association football", "boxing", "ufc", "mma",
    "american football", "hurling", "horse racing", "cycling", "specials",
}


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.hrefs: list[str] = []
        self.srcs: list[str] = []
        self.in_tbody = False
        self.in_tr = False
        self.cur_tr_https: list[str] = []
        self.cur_tr_colspan = False
        self.tr_audit: list[tuple[bool, list[str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = dict(attrs)
        if ad.get("id"):
            self.ids.add(ad["id"])
        if tag == "a" and ad.get("href"):
            h = ad["href"]
            self.hrefs.append(h)
            if self.in_tbody and self.in_tr and h.startswith("https://"):
                self.cur_tr_https.append(h)
        if tag in ("script", "img", "link") and (ad.get("src") or ad.get("href")):
            v = ad.get("src") or ad.get("href") or ""
            self.srcs.append(v)
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.cur_tr_https = []
            self.cur_tr_colspan = False
        elif tag == "td" and self.in_tr and ad.get("colspan"):
            self.cur_tr_colspan = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "tr" and self.in_tbody and self.in_tr:
            self.tr_audit.append((self.cur_tr_colspan, list(self.cur_tr_https)))
            self.in_tr = False
        elif tag == "tbody":
            self.in_tbody = False


def main() -> None:
    # 1. Validate JSON schemas & mathematical invariants
    events = json.loads((DATA_DIR / "matches.json").read_text())
    markets = json.loads((DATA_DIR / "markets.json").read_text())
    preds = json.loads((DATA_DIR / "predictions.json").read_text())
    review = json.loads((DATA_DIR / "repo_review.json").read_text())
    sources = json.loads((DATA_DIR / "sources.json").read_text())
    flags = json.loads((DATA_DIR / "flagged.json").read_text())
    taxonomy = json.loads((DATA_DIR / "olbg_taxonomy.json").read_text())

    assert taxonomy["summary"]["included_sports_count"] == 17
    assert taxonomy["summary"]["live_olbg_total_events"] == 194
    assert len(events) >= 260

    for ev in events:
        sp = ev["sport"].strip().lower()
        assert sp not in EXCLUDED_SPORTS, f"Excluded sport leaked: {sp}"
        assert ev["source_url"].startswith("https://"), f"Missing https official source on {ev['id']}"
        assert "olbg.com" not in ev["source_url"].lower(), f"OLBG used as match source on {ev['id']}"
        if ev["status"] == "unverified":
            assert ev["pick"] == "", f"Unverified row must leave pick blank: {ev['id']}"
            assert ev["markets"] == [], f"Unverified row must leave markets blank: {ev['id']}"
        if ev["confidence"] == "high":
            wc = len(ev["prediction"].split())
            assert wc >= 30, f"High pick {ev['id']} under 30 words ({wc})"
        else:
            assert ev.get("prediction", "") == "", f"Non-high row {ev['id']} must not carry prose prediction"

    for mk in markets:
        s = sum(o["prob"] for o in mk["outcomes"])
        assert abs(s - 1.0) <= 0.0005, f"Market book probability sum != 1.0 on {mk}: {s}"
        assert all(o["fair_odds"] >= 1.0 for o in mk["outcomes"]), f"Invalid decimal odds on {mk}"

    # 2. Inspect every generated HTML page in `session-ee9c2db4/` for 100% per-row official https:// links
    our_html = sorted(SITE_DIR.rglob("*.html"))
    assert len(our_html) == 25, f"Expected 25 HTML pages in session-ee9c2db4/, found {len(our_html)}"

    total_our_trs = 0
    for hp in our_html:
        txt = hp.read_text()
        assert "TODO" not in txt and "FIXME" not in txt, f"Placeholder token in {hp}"
        ins = PageInspector()
        ins.feed(txt)
        for is_empty_placeholder, links in ins.tr_audit:
            if is_empty_placeholder:
                continue
            total_our_trs += 1
            assert len(links) >= 1, f"Table row without https:// official review link in {hp}"
            assert any("olbg.com" not in u.lower() for u in links), f"Table row in {hp} lacks non-OLBG official https:// link: {links}"

    # 3. Whole-repository internal link & fragment anchor audit across ALL HTML files in /home/user/OLBG4
    all_html = sorted(
        p for p in REPO_ROOT.rglob("*.html")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )
    id_cache: dict[Path, set[str]] = {}
    href_records: list[tuple[Path, str]] = []

    for hp in all_html:
        ins = PageInspector()
        ins.feed(hp.read_text(errors="replace"))
        id_cache[hp.resolve()] = ins.ids
        for h in ins.hrefs + ins.srcs:
            href_records.append((hp, h))

    broken: list[str] = []
    checked_local = 0
    for src_page, raw_h in href_records:
        h = raw_h.strip()
        if not h or h.startswith(("http://", "https://", "mailto:", "tel:", "javascript:", "data:")):
            continue
        checked_local += 1
        path_part, _, frag = h.partition("#")
        path_part = unquote(path_part.split("?", 1)[0])
        if path_part == "":
            target = src_page.resolve()
        elif path_part.startswith("/"):
            target = (REPO_ROOT / path_part.lstrip("/")).resolve()
        else:
            target = (src_page.parent / path_part).resolve()

        if target.is_dir():
            target = (target / "index.html").resolve()

        if not target.exists():
            broken.append(f"{src_page.relative_to(REPO_ROOT)} -> {raw_h} (missing target {target})")
            continue

        # Enforce fragment anchor check across all pages inside `session-ee9c2db4/`
        if frag and SITE_DIR.resolve() in target.parents:
            t_ids = id_cache.get(target, set())
            if frag not in t_ids:
                broken.append(f"{src_page.relative_to(REPO_ROOT)} -> {raw_h} (missing #anchor '{frag}' in {target.relative_to(REPO_ROOT)})")

    assert not broken, "Broken local links/anchors found:\n  " + "\n  ".join(broken[:25])

    print(
        f"M7 validation PASSED 100%:\n"
        f"  Board Q HTML pages verified    : {len(our_html)}\n"
        f"  Board Q table rows w/ official : {total_our_trs}/{total_our_trs} (100.0%)\n"
        f"  Originated events / books      : {len(events)} events / {len(markets)} complete books (sum(p)==1.0000)\n"
        f"  High-confidence human prose    : {preds['count']} write-ups (min {preds['min_words']}w, max Jaccard {preds['max_pairwise_3gram_jaccard']})\n"
        f"  Audited existing repo rows     : {review['total_committed_rows_audited']} rows ({len(sources)} official sources, {len(flags)} flags)\n"
        f"  Whole-repo HTML link gate      : {len(all_html)} HTML files, {checked_local} local links/anchors, 0 broken"
    )


if __name__ == "__main__":
    main()

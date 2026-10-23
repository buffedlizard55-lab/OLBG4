#!/usr/bin/env python3
"""Board FB (arena/48de8c1d-olbg4) — FB6: End-to-End Verification Gate.

Asserts all hard engineering, mathematical, scope, prose, source-link, and HTML integrity
requirements across `data/session-48de8c1d/` and `session-48de8c1d/`.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "session-48de8c1d"
SITE_DIR = ROOT / "session-48de8c1d"
CAP_DIR = DATA_DIR / "capture" / "20261023T213547Z"

COVERED_SPORTS = {
    "Golf",
    "Volleyball",
    "Rugby Union",
    "Cricket",
    "Snooker",
    "Darts",
    "Baseball",
    "Gaelic Sports",
    "Greyhounds",
    "Tennis",
    "Motor Racing",
    "Handball",
    "Ice Hockey",
    "Basketball",
    "Rugby League",
}
CUTOFF_UTC = "2026-10-23T21:40:00Z"
BANNED_RE = re.compile(r"\b(model\w*|verif\w*)\b", re.I)


class PageInspector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.local_refs: list[str] = []
        self.in_tbody = False
        self.in_tr = False
        self.tr_ext_links = 0
        self.tbody_rows = 0
        self.rows_missing_official_link = 0
        self.in_prose_cell = False
        self.prose_buf: list[str] = []
        self.prose_cells: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = dict(attrs)
        if tag in ("a", "link", "script"):
            ref = ad.get("href") or ad.get("src")
            if ref:
                if ref.startswith(("http://", "https://")):
                    if self.in_tbody and self.in_tr and tag == "a":
                        self.tr_ext_links += 1
                elif not ref.startswith(("#", "mailto:", "javascript:")):
                    self.local_refs.append(ref.split("#")[0].split("?")[0])
        if tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.in_tr = True
            self.tr_ext_links = 0
        elif tag == "td" and ad.get("class") and "prose-cell" in ad["class"]:
            self.in_prose_cell = True
            self.prose_buf = []

    def handle_data(self, data: str) -> None:
        if self.in_prose_cell:
            self.prose_buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "tbody":
            self.in_tbody = False
        elif tag == "tr" and self.in_tbody and self.in_tr:
            self.tbody_rows += 1
            if self.tr_ext_links == 0:
                self.rows_missing_official_link += 1
            self.in_tr = False
        elif tag == "td" and self.in_prose_cell:
            self.prose_cells.append("".join(self.prose_buf))
            self.in_prose_cell = False


def main() -> int:
    desk = json.loads((DATA_DIR / "desk.json").read_text(encoding="utf-8"))
    preds = json.loads((DATA_DIR / "predictions.json").read_text(encoding="utf-8"))
    rev = json.loads((DATA_DIR / "review.json").read_text(encoding="utf-8"))
    flg = json.loads((DATA_DIR / "flagged.json").read_text(encoding="utf-8"))
    manifest = json.loads((CAP_DIR / "manifest.json").read_text(encoding="utf-8"))

    # 1. Verify SHA-256 capture manifest integrity on disk
    rec_by_id = {r["id"]: r for r in manifest["records"]}
    ok_200 = [r for r in manifest["records"] if r["status"] == 200]
    assert len(ok_200) == 128, f"Expected 128 HTTP-200 captures, got {len(ok_200)}"
    for r in ok_200:
        fp = CAP_DIR / r["file"]
        assert fp.exists(), f"Missing capture file {fp}"
        digest = hashlib.sha256(gzip.open(fp, "rb").read()).hexdigest()
        assert digest == r["sha256"], f"SHA-256 mismatch on {fp}"

    # 2. Verify desk scope, cutoff, probability conservation & SHA-256 provenance
    sports_seen = {r["sport"] for r in desk["rows"]}
    assert sports_seen == COVERED_SPORTS, f"Sport set mismatch: {sports_seen ^ COVERED_SPORTS}"
    priced = [r for r in desk["rows"] if r["verification_status"] == "verified"]
    partial = [r for r in desk["rows"] if r["verification_status"] != "verified"]
    assert len(priced) == 113 and len(partial) == 1, f"Unexpected priced/partial split: {len(priced)}/{len(partial)}"

    total_mkts = 0
    for r in desk["rows"]:
        assert r["start_utc"] >= CUTOFF_UTC, f"Stale fixture {r['id']} ({r['start_utc']})"
        assert r["official_source_url"].startswith("https://"), f"Missing HTTPS official URL on {r['id']}"
        cid = r["capture_target_id"]
        assert cid in rec_by_id and rec_by_id[cid]["status"] == 200, f"Unverified capture {cid} on {r['id']}"
        assert r["capture_sha256"] == rec_by_id[cid]["sha256"], f"SHA mismatch on {r['id']}"
        if r["verification_status"] != "verified":
            assert r["home"] == "" and r["away"] == "" and r["match_winner_pick"] == "" and r["markets"] == [], (
                f"Partial row {r['id']} must leave unconfirmed fields blank"
            )
        else:
            assert r["match_winner_pick"] != "", f"Missing match winner pick on {r['id']}"
            assert r["confidence"] in ("High", "Medium", "Low")
            for m in r["markets"]:
                total_mkts += 1
                s = sum(o["fair_prob"] for o in m["outcomes"])
                assert abs(s - 1.0) <= 0.0005, f"Prob sum drift on {r['id']} {m['market_key']}: {s}"
    assert total_mkts == 452, f"Expected 452 markets, got {total_mkts}"

    # 3. Verify 75 High-confidence predictions (5 per sport, [-250..+10000], >=30 words, 0 banned words)
    plist = preds["predictions"]
    assert len(plist) == 75, f"Expected 75 predictions, got {len(plist)}"
    by_sp: dict[str, int] = {}
    for p in plist:
        by_sp[p["sport"]] = by_sp.get(p["sport"], 0) + 1
        assert -250 <= p["fair_american"] <= 10000, f"Out-of-window American odds {p['fair_american']} on {p['prediction_id']}"
        wc = len(p["prediction_text"].split())
        assert wc >= 30, f"Too short ({wc} words) on {p['prediction_id']}"
        bad = BANNED_RE.findall(p["prediction_text"])
        assert not bad, f"Banned word(s) {bad} in {p['prediction_id']}"
        assert p["official_source_url"].startswith("https://")
    assert set(by_sp.keys()) == COVERED_SPORTS and all(v == 5 for v in by_sp.values()), f"Predictions per sport mismatch: {by_sp}"

    # 4. Verify review & flagged ledgers
    assert rev["summary"]["total_rows_audited_line_by_line"] == 2364
    assert flg["summary"]["total_flagged_items"] == 26

    # 5. Verify all 23 HTML pages: local links, official source link on EVERY tbody row, zero banned words in prose, zero TODO
    html_files = sorted(SITE_DIR.rglob("*.html"))
    assert len(html_files) == 23, f"Expected 23 HTML pages in session-48de8c1d/, found {len(html_files)}"
    total_tbody_rows = 0
    for hf in html_files:
        raw = hf.read_text(encoding="utf-8")
        assert "TODO" not in raw, f"Uppercase TODO found in {hf}"
        insp = PageInspector()
        insp.feed(raw)
        for ref in insp.local_refs:
            if not ref:
                continue
            target = (hf.parent / ref).resolve()
            assert target.exists(), f"Broken local link `{ref}` in `{hf.relative_to(ROOT)}` -> `{target}`"
        assert insp.rows_missing_official_link == 0, (
            f"{insp.rows_missing_official_link} table rows missing official source link in {hf.relative_to(ROOT)}"
        )
        for pc in insp.prose_cells:
            bad = BANNED_RE.findall(pc)
            assert not bad, f"Banned token {bad} in prose cell of {hf.relative_to(ROOT)}"
        total_tbody_rows += insp.tbody_rows

    # Extra check: zero banned words anywhere on predictions.html visible text
    pred_txt = re.sub(r"<[^>]+>", " ", (SITE_DIR / "predictions.html").read_text(encoding="utf-8"))
    assert not BANNED_RE.findall(pred_txt), "Banned word found in predictions.html"

    # 6. Run repo-wide audit_publication.py --check (verify zero broken local targets across repo)
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "audit_publication.py"), "--check"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    pub = json.loads(proc.stdout)
    assert pub["broken"] == [], f"audit_publication broken links: {pub['broken']}"

    print(
        json.dumps(
            {
                "status": "PASS",
                "sha256_captures_verified": len(ok_200),
                "sports_covered": len(sports_seen),
                "priced_fixtures": len(priced),
                "flagged_partial_fixtures": len(partial),
                "markets_originated": total_mkts,
                "high_predictions_verified": len(plist),
                "repo_rows_audited": rev["summary"]["total_rows_audited_line_by_line"],
                "html_pages_verified": len(html_files),
                "html_table_rows_all_with_official_links": total_tbody_rows,
                "repo_local_links_checked": pub["local_targets_checked"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

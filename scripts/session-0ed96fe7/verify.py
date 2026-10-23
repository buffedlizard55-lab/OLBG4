"""Board EZ (arena/0ed96fe7-olbg4) — publication gate.

Fails (exit 1) on anything that would make the published board wrong:
  * desk/flagged/review JSON invalid, or review reporting hard failures
  * any row without an official https source link
  * any unpriced row with leftover price fields, or whose sport carries no flag
  * any high-confidence row outside the -250..+10000 window, under 70% win
    probability, or without a >=30-word unique prediction free of internal
    vocabulary
  * any internal site link that does not resolve to a built page/anchor
  * any sport page whose table rows lack an official source link
  * a non-deterministic rebuild (two consecutive builds must be byte-identical)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
DATA = os.path.join(ROOT, "data", "session-0ed96fe7")
SITE = os.path.join(ROOT, "session-0ed96fe7")
BANNED = ("model", "verified")


def main() -> int:
    fails: list[str] = []

    desk = json.load(open(os.path.join(DATA, "desk.json")))
    flagged = json.load(open(os.path.join(DATA, "flagged.json")))
    review = json.load(open(os.path.join(DATA, "review.json")))
    rows = desk["rows"]

    if review["hard_failures"]:
        fails.append(f"review reports {len(review['hard_failures'])} hard failures")
    ids = {r["id"] for r in rows}
    sports_with_flags = {f["sport"] for f in flagged["flags"]}
    flag_ids = {f["id"] for f in flagged["flags"]}

    for r in rows:
        if not r.get("official_url", "").startswith("https://"):
            fails.append(f"{r['id']}: no https official link")
        if not r.get("priced"):
            if r.get("markets"):
                fails.append(f"{r['id']}: unpriced row carries markets")
            if r["sport"] not in sports_with_flags:
                fails.append(f"{r['id']}: unpriced row's sport has no flag")
        elif r.get("confidence") == "High":
            if not r.get("in_window"):
                fails.append(f"{r['id']}: high-confidence row outside window")
            if (r.get("pick_prob") or 0) < 0.70:
                fails.append(f"{r['id']}: high-confidence row under 70%")

    # predictions sanity (review re-checks pairwise similarity; here: presence + words)
    import importlib.util
    spec = importlib.util.spec_from_file_location("pb", os.path.join(HERE, "predictions_bank.py"))
    pb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pb)
    by_id = {r["id"]: r for r in rows}
    for rid, text in pb.PREDICTIONS:
        if rid not in ids or not by_id[rid].get("priced"):
            fails.append(f"prediction {rid}: row missing/unpriced")
        if len(text.split()) < 30:
            fails.append(f"prediction {rid}: under 30 words")
        low = text.lower()
        if any(b in low for b in BANNED):
            fails.append(f"prediction {rid}: internal vocabulary in output text")

    # internal links resolve
    pages = {}
    for dirpath, _, files in os.walk(SITE):
        for fn in files:
            if fn.endswith(".html"):
                full = os.path.join(dirpath, fn)
                pages[os.path.relpath(full, SITE)] = open(full).read()
    for rel, html_txt in pages.items():
        base = os.path.dirname(rel)
        for href in re.findall(r'href="([^"#]+)(#[^"]*)?"', html_txt):
            target, anchor = href
            if target.startswith(("http://", "https://", "mailto:")):
                continue
            resolved = os.path.normpath(os.path.join(base, target))
            if resolved not in pages:
                on_disk = os.path.exists(os.path.join(SITE, resolved))
                if not on_disk:
                    fails.append(f"{rel}: broken internal link {target}")
            elif anchor and anchor[1:] not in pages[resolved]:
                fails.append(f"{rel}: missing anchor {anchor} in {target}")

    # every row renders with a source link on its sport page
    for r in rows:
        slug = r["sport_slug"]
        page = pages.get(f"sports/{slug}.html")
        if page is None:
            fails.append(f"{r['id']}: sport page missing ({slug})")
            continue
        if f"id='{r['id']}'" not in page:
            fails.append(f"{r['id']}: row not rendered on {slug} page")
        seg = page.split(f"id='{r['id']}'")[1][:1200] if f"id='{r['id']}'" in page else ""
        if "href='" not in seg and "href=\"" not in seg:
            fails.append(f"{r['id']}: row has no source link in rendered table")

    # flag anchors referenced by chips exist
    body_all = "\n".join(pages.values())
    for f in flagged["flags"]:
        fl = pages.get("flagged.html", "")
        if f'id="{f["id"]}"' not in fl and f"id='{f['id']}'" not in fl:
            fails.append(f"flag {f['id']}: no anchor on flagged page")

    # no TODO strings anywhere in the site
    if "TODO" in body_all:
        fails.append("site contains TODO strings")

    # deterministic rebuild
    before = {rel: open(os.path.join(SITE, rel), "rb").read() for rel in pages}
    subprocess.run([sys.executable, os.path.join(HERE, "build_site.py")],
                   check=True, capture_output=True)
    for rel, blob in before.items():
        if open(os.path.join(SITE, rel), "rb").read() != blob:
            fails.append(f"rebuild is not deterministic: {rel}")

    print(f"[board-ez] verify: rows={len(rows)} pages={len(pages)} flags={len(flagged['flags'])} "
          f"fails={len(fails)}")
    for f in fails[:20]:
        print("  FAIL", f)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

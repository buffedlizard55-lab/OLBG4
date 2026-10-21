#!/usr/bin/env python3
"""Board K: keep `docs/index.html` reproducible.

`gen_pages.py` (Build A's generator) rewrites `docs/index.html` from scratch, so the additive
cross-build banner that Board B inserted after `<body>` is destroyed on every run. This was
observed twice: once during Board K's restoration pass and again when re-running the generator
for the K11 gate.

This script re-inserts that banner after `gen_pages.py`, so the documented build order is:

    python3 build_site.py && python3 gen_pages.py && python3 scripts/session-47b1b4e2/restore_docs_banner.py

The banner is restored verbatim, and one Board K correction is appended inside it: Board B's
sentence "Gaelic football is on the exclusion list but 2 rows remain in build A" repeats finding
F-07, which is retracted - the brief excludes hurling, not Gaelic football. Board B's original
wording is kept and the retraction is clearly attributed, matching how K7 handled the flag itself.

Run: python3 scripts/session-47b1b4e2/restore_docs_banner.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAGE = os.path.join(ROOT, "docs", "index.html")

# Board B's banner, verbatim as published (681 chars), plus the Board K retraction note.
BANNER = (
    '<div style="max-width:1180px;margin:12px auto 0;padding:12px 16px;border:1px solid #cddffd;'
    'background:#eaf1ff;border-radius:12px;font:14px/1.5 -apple-system,BlinkMacSystemFont,Segoe UI,'
    'Roboto,Helvetica,Arial,sans-serif;color:#12161c">'
    '<b>Two verified builds are published here.</b> This is build A (144 rows, 15 sports, '
    'governing-body sources). Build B \u2014 116 fixtures read directly off OLBG\u2019s live pages, with '
    'our own win/handicap/total lines and 9 high-confidence write-ups \u2014 is at '
    '<a href="../session-7114b6a1/index.html"><b>session-7114b6a1/</b></a>. Build B also carries the '
    'cross-session review note: Gaelic football is on the exclusion list but 2 rows remain in build A.'
    '<div style="margin-top:9px;padding-top:9px;border-top:1px dashed #9db8e8">'
    '<b>Board K correction (2026-10-21).</b> The sentence above is <b>retracted</b>. The brief excludes '
    '<i>hurling</i>, not Gaelic football, so build A\u2019s two Gaelic football rows are in scope and are '
    'not a breach; the corresponding flag has been withdrawn on '
    '<a href="../session-7114b6a1/flagged.html">build B\u2019s Flagged for Review page</a> with the '
    'original wording preserved. Board B\u2019s text is left intact above so the correction is auditable. '
    'See the <a href="../session-47b1b4e2/index.html">Board K remediation report</a>.'
    '</div></div>'
)

MARKER = '<div style="max-width:1180px'


def main():
    with open(PAGE, encoding="utf-8") as f:
        txt = f.read()

    if MARKER in txt:
        if "Board K correction" in txt:
            print("docs/index.html: banner and Board K correction already present, nothing to do")
            return 0
        # an older banner without the correction - replace it
        start = txt.index(MARKER)
        end = txt.index("</div>", txt.index("</div>", start) + 1) + len("</div>")
        txt = txt[:start] + BANNER + txt[end:]
        action = "replaced the banner with the corrected version"
    else:
        at = txt.index("<header>")
        txt = txt[:at] + BANNER + txt[at:]
        action = "re-inserted the banner before <header>"

    with open(PAGE, "w", encoding="utf-8") as f:
        f.write(txt)
    print("docs/index.html: %s (%d chars)" % (action, len(BANNER)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

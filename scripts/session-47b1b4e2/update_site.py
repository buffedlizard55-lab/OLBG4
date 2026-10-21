#!/usr/bin/env python3
"""Board K site updates: qualify overstated verification claims (K9), publish the
cross-build pick-conflict reconciliation (K8), correct flagged.html's stale RL01 note,
and add the Board K remediation card + report link.

Every replacement is an exact-string edit; the script fails loudly if a target string
is missing or has already been applied, so it is safe to re-run and cannot silently
half-edit a page.

Run: python3 scripts/session-47b1b4e2/update_site.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPORT_HREF = "session-47b1b4e2/"
edits = []          # (path, old, new, label)
already = []        # (path, label)


def sub(path, old, new, label, required=True):
    edits.append((os.path.join(ROOT, path), old, new, label, required))


# ---------------------------------------------------------------- category pages
CAT_OLD = ("This is a filtered view of the same verified <code>data/matches.json</code> used on the "
           "dashboard. Every row below was verified line-by-line against its official source on "
           "2026-10-21. Use the filters to narrow further.")
CAT_NEW = ("This is a filtered view of the same <code>data/matches.json</code> used on the dashboard. "
           "Each row shows its own source class: rows marked <strong>VERIFIED (official source)</strong> "
           "link a governing body, while rows whose only source is a secondary site (ESPN, BBC, Sky, "
           "Wikipedia, a betting blog) are marked <strong>FLAGGED / UNVERIFIED</strong> and are never "
           "presented as confirmed. Not every entry is a match &mdash; use the <em>Entry</em> filter to "
           "separate fixtures from tournaments, completed results and notes. Corrections and withdrawn "
           "predictions from the Board K remediation are disclosed inline on the affected rows. "
           "See <a href=\"" + REPORT_HREF + "\">the remediation report</a>.")

for p in ["tennis.html", "basketball.html", "baseball.html", "cricket.html", "rugby.html",
          "ice-hockey.html", "snooker.html", "darts.html", "golf.html", "badminton.html",
          "table-tennis.html", "volleyball.html", "handball.html", "esports.html", "aussie-rules.html"]:
    sub(p, CAT_OLD, CAT_NEW, "category hero claim")

# ---------------------------------------------------------------- index.html
sub("index.html",
    "<p>Verified matches • Originated lines • No hallucinations • Every row sourced • 6 builds preserved</p>",
    "<p>Originated lines • Every row sourced • Source class shown per row • 6 builds preserved</p>",
    "header tagline")

sub("index.html",
    'content="OLBG4 — Six verified builds: gov-body-verified hub (66 entries, 15 high predictions), '
    'docs/ 144 rows, session-7114b6a1 116 OLBG-live fixtures, session-74f9613e 43 fixtures 182 '
    'selections. Every row sourced."',
    'content="OLBG4 — six builds. Hub (Build D): 66 entries, 32 of them matches, each row labelled '
    'with its source class; only governing-body-sourced rows are marked verified. docs/ 144 rows, '
    'session-7114b6a1 116 OLBG-live fixtures, session-74f9613e 43 fixtures 182 selections. '
    'Every row carries a source link; unconfirmed values are blank and flagged."',
    "meta description")

sub("index.html",
    "This <b>hub (Build D)</b> is the primary dashboard (66 entries, governing-body verified, "
    "15 high-confidence predictions — most exclusion-compliant).",
    "This <b>hub (Build D)</b> is the primary dashboard: 66 entries, of which <b>32 are matches</b> "
    "and the rest are tournaments, completed results or coverage notes (use the <b>Entry</b> filter). "
    "<b>43 rows link a governing body</b>; the other 23 link a secondary site and are flagged "
    "unverified rather than presented as confirmed. <b>2 high-confidence predictions</b> remain "
    "published — the 14 that could not be supported by an official source were withdrawn by the "
    "Board K remediation and are disclosed, with their text, on the "
    "<a href=\"flagged.html\">Flagged for Review</a> page. Most exclusion-compliant build.",
    "banner Build D claim")

sub("index.html",
    "<p>66 entries, 16 sports, 15 high-confidence predictions (68-105 words), gov-body verified "
    "(ATP, NBA, MLB, NHL, WST, PDC, PGA/LPGA, BWF, WTT/ITTF, FIVB). Most exclusion-compliant. "
    "Use the filterable table below.</p>",
    "<p>66 entries, 16 sports. After the Board K remediation: <b>32 matches</b> (plus 28 "
    "tournament/round entries, 3 completed results, 3 notes), <b>43 rows on a governing-body "
    "source</b> (NBA, MLB, NHL, ATP/WTA, PGA/LPGA, Cricket Australia, PCB, ECB, EuroLeague, "
    "EHF/IHF, FIVB, ITTF/FFTT, PDC, WST, AFL, NRL/RLWC, Riot) and <b>2 high-confidence "
    "predictions</b> that survive line-by-line official verification. 14 predictions were "
    "withdrawn and are published with their text and reasons on the Flagged page. Most "
    "exclusion-compliant. Use the filterable table below.</p>",
    "Build D portal card")

sub("index.html",
    "13 findings. Note: 26 rows of this hub are still marked verified without an official source,\n"
    "           several hub predictions are contradicted by NHL.com / MLB.com / NRL.com, and a later session overwrote\n"
    "           Build A/B data files (F-11/F-12) — see its Flagged for Review page.</p>",
    "13 findings. <b>All of its high-severity findings have now been remediated by Board K</b> —\n"
    "           the 26 rows verified without an official source are downgraded and flagged, the predictions\n"
    "           contradicted by NHL.com / MLB.com / RLWC2026.com are withdrawn, the wrong fixture fields\n"
    "           (CRK03, CRK05, MLB03, EL02, RL01) are corrected against governing-body pages, and Build A/B's\n"
    "           overwritten files (F-11/F-12) are restored. See its Flagged for Review page and the\n"
    "           <a href=\"" + REPORT_HREF + "\">Board K remediation report</a>.</p>",
    "Board J portal card")

sub("index.html",
    "      <strong>Every row has an official source link.</strong> If a value can't be confirmed, it is left blank and flagged — never inferred.",
    "      <strong>Every row has a source link, and each row states whether that source is a governing body or a secondary site.</strong> "
    "Only governing-body-sourced rows are marked verified. If a value can't be confirmed on an official source, it is left blank and flagged — never inferred.",
    "hero official-source claim")

# K8 — cross-build pick-conflict reconciliation (Board J F-06). Inserted after the hero <h2>.
K8_ANCHOR = ('  <section class="hero" id="hub-table">\n'
             '    <h2>Updated matches for every covered sport — excluding soccer, boxing, UFC/MMA, football, horse racing, cycling, hurling, specials</h2>\n')
K8_NEW = K8_ANCHOR + '''    <div class="notice" style="margin-top:10px;border-left:4px solid #b45309;background:#fffbeb">
      <strong>Reading the builds side by side? Board J finding F-06, reconciled.</strong>
      Six independent builds in this repo modelled the same window with different inputs and different
      models, so <strong>93 fixtures appear in two or more builds and 10 of them have opposite
      match-winner picks</strong> — for example Charlotte Hornets v Brooklyn Nets on 21 Oct is a
      <em>high-confidence Charlotte</em> pick in Build C and a <em>low-confidence Brooklyn</em> pick in
      Build A. That is a genuine disagreement between models, not a data error, and no build has been
      edited to hide it. Each build publishes its own model constants and its own source per row, so
      the disagreement is auditable: compare the two rows' sources before treating either as a tip.
      All 93 overlaps and the 10 conflicts are listed on
      <a href="session-e1e0c27e/crossbuild.html">Board J's cross-build page</a>. Where this hub's own
      rows were wrong, Board K corrected or withdrew them — see the
      <a href="''' + REPORT_HREF + '''">remediation report</a>.
    </div>
'''
sub("index.html", K8_ANCHOR, K8_NEW, "K8 cross-build reconciliation")

# Board K portal card, inserted immediately before the Board J audit card.
BJ_CARD = '      <a class="portal-card" href="session-e1e0c27e/" style="border-color:#b91c1c;background:#fef2f2">'
BK_CARD = '''      <a class="portal-card" href="''' + REPORT_HREF + '''" style="border-color:#15803d;background:#f0fdf4">
        <h3>Board K remediation — session-47b1b4e2/ (what changed and why)</h3>
        <p>Applies every high-severity Board J finding: Build A restored to its pre-overwrite 144 rows
           and 12 hand-written predictions, Build B's broken renderer repaired, 26 hub rows downgraded
           from verified, 14 predictions withdrawn, 14 rows corrected against governing-body pages
           (NHL.com, MLB.com, PCB, ECB, EuroLeague, PDC, RLWC2026.com), and non-match entries separated
           from the match table. Every change lists the official URL it was checked against.</p>
      </a>
''' + BJ_CARD
sub("index.html", BJ_CARD, BK_CARD, "Board K portal card")

# ---------------------------------------------------------------- flagged.html
sub("flagged.html",
    "<td class=\"small\">Pacific Championships fixture (Aus vs NZ Oct 25 7:50pm) appears on NRL.com but could not be fetched via allowed outbound hosts at cut-off; listed with NRL.com link and flagged to request manual verification on <a href=\"https://www.nrl.com/pacific-championships/\" target=\"_blank\">nrl.com/pacific-championships</a>.</td>",
    "<td class=\"small\"><strong>Corrected by Board K (2026-10-21).</strong> There is no Pacific Championships in 2026 &mdash; the tournament is the <strong>Rugby League World Cup</strong> (15 Oct &ndash; 15 Nov). <a href=\"https://www.rlwc2026.com/draws-and-pools\" target=\"_blank\" rel=\"noopener\">rlwc2026.com</a> shows Australia v New Zealand was <strong>Round 1 on 15 Oct at Allianz Stadium, Sydney</strong> (Australia won 24-22), and that the <strong>25 Oct Brisbane fixture at Suncorp Stadium is Australia v Fiji</strong>, Round 2 Pool A, 7:05pm local &mdash; confirmed on the <a href=\"https://suncorpstadium.com.au/events/rugby-league-world-cup-2026--men-s-australia-v-fiji\" target=\"_blank\" rel=\"noopener\">venue's own event page</a>. The final is 15 Nov in Brisbane, not 8 Nov in Sydney. Row RL01 has been rewritten as the Australia v Fiji match with the <a href=\"https://www.rlwc2026.com/draw/mens/2026/round-2/australia-v-fiji\" target=\"_blank\" rel=\"noopener\">official match centre</a>; its old pick and line were withdrawn because they were derived from the wrong fixture.</td>",
    "flagged RL01 static row")

sub("flagged.html",
    "<p>These entries were published but marked <span class=\"badge badge-flagged\">FLAGGED</span> because one or more fields could not be confirmed on an official site at the 2026-10-21 cut-off.",
    "<p><strong>Board K remediation (2026-10-21) is reflected below.</strong> 26 rows that were marked verified on a secondary source are now unverified and flagged; 14 predictions whose claims could not be confirmed on a governing-body page are withdrawn (their full text is preserved and shown on each row and below); 14 rows were corrected against official pages (NHL.com, MLB.com, PCB, ECB, EuroLeague Basketball, PDC, RLWC2026.com). See the <a href=\"" + REPORT_HREF + "\">remediation report</a> for the change-by-change log.</p>\n    <p>These entries were published but marked <span class=\"badge badge-flagged\">FLAGGED</span> because one or more fields could not be confirmed on an official site at the 2026-10-21 cut-off.",
    "flagged page intro")

sub("flagged.html",
    '<a href="flagged.html" class="active">Flagged for Review</a>',
    '<a href="flagged.html" class="active">Flagged for Review</a>\n      <a href="' + REPORT_HREF + '">Board K remediation</a>',
    "flagged nav link")


def main():
    failed = []
    touched = {}
    for path, old, new, label, required in edits:
        rel = os.path.relpath(path, ROOT)
        if path in touched:
            # a previous edit in this run already modified this file - build on that, not on disk
            txt = touched[path]
        else:
            try:
                with open(path, encoding="utf-8") as f:
                    txt = f.read()
            except OSError as e:
                failed.append((rel, label, "cannot read: %s" % e))
                continue
        if new in txt and old not in txt:
            already.append((rel, label))
            continue
        if old not in txt:
            if required:
                failed.append((rel, label, "target string not found"))
            continue
        n = txt.count(old)
        txt = txt.replace(old, new)
        touched.setdefault(path, txt)
        touched[path] = txt
        print("  %-22s %-32s (%d occurrence%s)" % (rel, label, n, "" if n == 1 else "s"))

    for path, txt in touched.items():
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)

    print("\napplied to %d files" % len(touched))
    if already:
        print("already applied (skipped): %d" % len(already))
        for rel, label in already:
            print("   -", rel, "|", label)
    if failed:
        print("\nFAILED:", file=sys.stderr)
        for rel, label, why in failed:
            print("  %s | %s | %s" % (rel, label, why), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# COORDINATION — OLBG4

Session: arena/f0402305-olbg4 (this session) | Branch: arena/f0402305-olbg4 | Date: 2026-10-21

| # | Task | Status | Owner | File scope |
|---|------|--------|-------|-----------|
| 1 | Reverse-engineer OLBG sport coverage; define included sports (all except soccer, boxing, UFC/MMA, football/American football, hurling, horse racing, cycling, specials) | in progress | arena/f0402305-olbg4 | COORDINATION.md, data/, docs/ |
| 2 | Collect upcoming fixtures per included sport from official governing-body sources only | in progress | arena/f0402305-olbg4 | data/fixtures.json |
| 3 | Originate own lines (transparent model), pick winner, confidence low/med/high, investigate markets (match win, handicap, totals where official market definition exists) | in progress | arena/f0402305-olbg4 | data/picks.json, docs/METHODOLOGY.md |
| 4 | High-confidence human predictions >=30 words with verified form/history | in progress | arena/f0402305-olbg4 | data/picks.json |
| 5 | GitHub Pages site: landing + subpages by sport, tables, Flagged for Review | in progress | arena/f0402305-olbg4 | docs/ (Pages source), index/HTML/CSS/JS |
| 6 | Final integration: line-by-line verification, no broken links, PR to main + merge + Pages deploy | done | arena/f0402305-olbg4 | index.html, COORDINATION.md |

Rules (per brief): every row needs an official source link; unconfirmed values left blank + flagged unverified; no inferred values; flagged items do not block merge; shared index/nav changed only by final integration session (this session acts as integration at end).

## Log
- 2026-10-21: Session arena/f0402305-olbg4 claimed tasks 1-5 on branch arena/f0402305-olbg4. Repo was empty except README "# OLBG4" (commit f40a495).

## Completion record (2026-10-21, session arena/f0402305-olbg4)
- Tasks 1-5 DONE by this session acting also as final integration (task 6): 144 rows, 15 included sports, 12 high-confidence picks (each unique, >=30 words; min 66 words), 15 flagged rows.
- Sources (official only): NBA.com, NHL.com (+NHL standings 20 Oct), stats.unitedrugby.com, premiershiprugby.com, nrl.com (RLWC R1/R2), ehfcl.eurohandball.com, pdc.tv, mlb.com, nzc.nz, icc-cricket.com, galwaygaa.ie, gaacork.ie, volleyballworld.com, wst.tv, atptour.com, europeantour.com, formula1.com, gbgb.org.uk; OLBG.com used only to define sport universe + cross-check.
- Irregularities flagged on site /flagged.html: (1) OLBG snooker pairing Cheung v Bingham not on WST match centre; (2) OLBG Galway final 14:00 vs Galway GAA 19:00; (3) OLBG Cork final 12:00 vs Cork GAA 16:00; (4) Australia v Fiji model conflict; (5) scope limit disclosure; (6) handicap/total markets investigated but not originated (no verified scoring inputs) — fields blank.
- Verification: predictions uniqueness/word-count asserted in build; internal links checked (0 broken); external source links sampled live (NHL, URC, EHF, PDC, MLB, ICC, Volleyball World all resolved 21 Oct).
- Integration/PR record: PR #1 (main feature, 144 rows + site) MERGED 2026-10-21: https://github.com/buffedlizard55-lab/OLBG4/pull/1
- Pages: repo Pages source is pre-set to main /(root) and cannot be changed by this token (API 403 on POST/PUT Pages). PR #2 added root index.html redirecting to docs/ — MERGED: https://github.com/buffedlizard55-lab/OLBG4/pull/2
- Deploy confirmed: Pages status "built"; live site verified by fetching https://buffedlizard55-lab.github.io/OLBG4/docs/ and /docs/flagged.html (both render with all tables). Root: https://buffedlizard55-lab.github.io/OLBG4/
- Task 6 status: done.

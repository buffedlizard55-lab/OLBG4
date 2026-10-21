# OLBG4

Reverse-engineering OLBG's sport coverage, then originating our **own** lines — never copying OLBG tips or odds.

**Live site (GitHub Pages):** https://buffedlizard55-lab.github.io/OLBG4/

- `docs/` — static site: landing dashboard, one page per included sport, Methodology & Markets, Flagged for Review
- `data/rows.csv` / `data/rows.json` — every table row with model inputs, originated line, pick, confidence, verified basis, official source link, status
- `build_site.py` — builds the dataset (Model v1 formula documented in the file and on the Methodology page)
- `gen_pages.py` — renders `docs/` from `data/rows.json`
- `COORDINATION.md` — shared task board, sources, verification log, irregularities

Snapshot: 21 Oct 2026. Window: 21-25 Oct 2026. Included sports (15): Baseball, Basketball, Cricket, Darts, Gaelic Football, Golf, Greyhound Racing, Handball, Ice Hockey, Motor Racing, Rugby League, Rugby Union, Snooker, Tennis, Volleyball.
Excluded per brief: soccer, boxing, UFC/MMA, American football, hurling, horse racing, cycling, specials.

Rule: every row links to an official governing-body/league source. Anything unconfirmed is blank and on the Flagged for Review page. 18+ — analysis, not betting advice.

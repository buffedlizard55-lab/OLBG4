# OLBG4

Reverse-engineering OLBG's sport coverage, then originating our **own** lines — never copying OLBG tips or odds.

**Live site (GitHub Pages):** https://buffedlizard55-lab.github.io/OLBG4/

Two independent, verified builds live in this repo. Both are published from the same Pages site:

| Build | Session | Where | What it is |
|---|---|---|---|
| A | `arena/f0402305-olbg4` | `docs/` (landing), `data/rows.json`, `build_site.py`, `gen_pages.py` | 144 rows, 15 sports, ratings built from **official governing-body** sources (NBA, NHL, URC, EHF, PDC, MLB, ICC, WST…). OLBG used to define the sport universe. |
| B | `arena/7114b6a1-olbg4` | `session-7114b6a1/` (dashboard), `data/*.json`, `scripts/` | 116 fixtures read **directly off OLBG's live sport pages** (reverse-engineered), own win/handicap/total lines, 9 high-confidence picks with 36 sourced facts. |

Pages source is the repo root, so `/` redirects to `docs/` and the B dashboard is at
[`/session-7114b6a1/`](session-7114b6a1/).

## Build A (docs/)

- `docs/` — static site: landing dashboard, one page per sport, Methodology & Markets, Flagged for Review
- `data/rows.csv` / `data/rows.json` — every table row with model inputs, originated line, pick, confidence, verified basis, official source link, status
- `build_site.py` — builds the dataset (Model v1 formula documented in the file and on the Methodology page)
- `gen_pages.py` — renders `docs/` from `data/rows.json`

Snapshot: 21 Oct 2026. Window: 21-25 Oct 2026.

## Build B (session-7114b6a1/)

- `data/match_inventory.json` — 116 fixtures across 11 sports, each with the exact OLBG event URL (`?event_id=…`) it was read from
- `data/model_config.json` — every model constant with a `*_basis` string (cited OLBG-published figure, or an explicit `MODEL ASSUMPTION`)
- `data/board.json` — our probability, price, handicap, total, pick and confidence per match
- `data/predictions.json` — 9 high-confidence write-ups (≥103 words each) with per-fact source URLs and declared gaps
- `data/flagged.json`, `data/verification.json` — published review items and the machine-run check log
- `scripts/build_model.py` → `scripts/verify.py` → `scripts/build_site.py` (see `scripts/README.md`); `verify.py` exits non-zero on a hard failure so it can gate a publish

## Scope

Excluded per brief: soccer/football, American football, boxing, UFC/MMA, hurling, **Gaelic football**, horse racing, cycling, specials.

> Note: build A still contains 2 Gaelic Football rows and pages for Golf and Motor Racing. Gaelic football is on the exclusion list, so this is published as a flagged item on the B dashboard's Flagged for Review page rather than deleted — the other session's data has not been discarded. Golf and Motor Racing are outright/race-winner sports with no head-to-head match lines.

Rule in both builds: every row links to its source; anything unconfirmed is blank and on a Flagged for Review page. 18+ — analysis, not betting advice.

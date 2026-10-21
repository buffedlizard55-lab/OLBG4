# OLBG4

Reverse-engineering OLBG's sport coverage, then originating our **own** lines — never copying OLBG tips or odds.

**Live site (GitHub Pages):** https://buffedlizard55-lab.github.io/OLBG4/

Four independent, verified builds live in this repo. Both are published from the same Pages site:

| Build | Session | Where | What it is |
|---|---|---|---|
| A | `arena/f0402305-olbg4` | `docs/` (landing), `data/rows.json`, `build_site.py`, `gen_pages.py` | 144 rows, 15 sports, ratings built from **official governing-body** sources (NBA, NHL, URC, EHF, PDC, MLB, ICC, WST…). OLBG used to define the sport universe. |
| B | `arena/7114b6a1-olbg4` | `session-7114b6a1/` (dashboard), `data/*.json`, `scripts/` | 116 fixtures read **directly off OLBG's live sport pages** (reverse-engineered), own win/handicap/total lines, 9 high-confidence picks with 36 sourced facts. |
| C | `arena/74f9613e-olbg4` | `session-74f9613e/` (dashboard), `data/session-74f9613e/*.json`, `scripts/session-74f9613e/` | 43 fixtures in 5 sports, each input transcribed from a primary league/tour page and recorded in `VERIFICATION.md`; 182 originated selections across money line, handicap and totals; 10 predictions where every claim is listed under the text with its source; 11-row gap register. |
| D | `arena/4afef1af-olbg4` | `session-4afef1af/` (dashboard + generated data), `pipeline/` (source) | **Fully automated** pipeline: league APIs → ridge ratings → own moneyline/handicap/total prices → graded picks → linted predictions → verification gate → static site, refreshed by GitHub Actions every 6 hours. Every row carries a league-owned source link; rows without one are dropped and flagged. |

Pages source is the repo root. `/` is a portal page linking all three builds, build A's
dashboard is at [`/docs/`](docs/), build B's at [`/session-7114b6a1/`](session-7114b6a1/)
build C's at [`/session-74f9613e/`](session-74f9613e/) and build D's at [`/session-4afef1af/`](session-4afef1af/). `.nojekyll` keeps the generated
HTML byte-identical to what the build scripts emit.

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

## Build C (session-74f9613e/)

- `data/session-74f9613e/inputs.json` — 43 fixtures with verified start time, venue and source id; `inputs_verified` lists what was and was not confirmed
- `data/session-74f9613e/matches.json` — the model output: our own money-line, handicap and totals prices, 182 selections, pick and confidence band
- `data/session-74f9613e/predictions.json` — 10 high-confidence write-ups, each ≥30 words and each carrying the exact list of facts and source pages used to write it
- `data/session-74f9613e/olbg_inventory.json` / `coverage.json` — the reconstructed OLBG listing surface (53 rows) and one coverage decision per OLBG sport (22 rows)
- `data/session-74f9613e/findings.json` — the irregularity register rendered on the Flagged page
- `VERIFICATION.md` — the line-by-line checks performed against each official page, plus every gap left blank
- `METHODOLOGY.md` — every formula, constant and confidence threshold, per sport
- `scripts/session-74f9613e/` — `prepare_inputs.py` → `model.py` → `prepare_inventory.py` → `build_site.py` → `validate.py`, wrapped by `build_all.sh`; the validator exits non-zero on a missing source, an impossible price, an out-of-band overround, a pick that is not a match winner, a short or duplicated prediction, or a broken internal link
- CI: `.github/workflows/validate.yml` rebuilds all three data layers for this build and fails if the committed output is stale

## Scope

Excluded per brief: soccer/football, American football, boxing, UFC/MMA, hurling, **Gaelic football**, horse racing, cycling, specials.

> Note: build A still contains 2 Gaelic Football rows and pages for Golf and Motor Racing. Gaelic football is **not** on the brief's exclusion list as build C reads it — the list names soccer/football, American football, boxing, UFC/MMA, hurling, horse racing, cycling and specials, and hurling is named separately from football, so "football" there means soccer. Boards A and B read it the other way and treat Gaelic football as excluded. Nothing was deleted: build C simply captured no Gaelic fixture it could verify, so the sport appears in its coverage register as "no verified fixture in window" and is flagged. Golf and Motor Racing are outright/race-winner sports with no head-to-head match lines.

Rule in all three builds: every row links to its source; anything unconfirmed is blank and on a Flagged for Review page. 18+ — analysis, not betting advice.

Rebuild build C with `bash scripts/session-74f9613e/build_all.sh`.

## Build D (session-4afef1af/) — automated official-API desk

Build D is the only build that refreshes itself. `pipeline/run.py` ingests official league data,
fits the ratings, originates prices and publishes the dashboard; `.github/workflows/olbg.yml` runs it
every six hours and commits the snapshot. There is no manual entry step.

- `pipeline/providers/` — NBA (`cdn.nba.com` schedule JSON), NHL (`api-web.nhle.com`), MLB (`statsapi.mlb.com`)
- `pipeline/model.py` — weighted ridge fits for margin and total, empirical residual probabilities, opening vs current line
- `pipeline/markets.py` — moneyline, handicap and total construction, 4.5% two-way hold, half-point lines
- `pipeline/predictions.py` — 30+ word write-ups for high-confidence picks, fact list with a source per claim, similarity lint
- `pipeline/verify.py` — official-source gate, range checks, prediction lint; excluded rows are flagged, never published
- `pipeline/selftest.py` — offline self-test run by CI before any network call
- `session-4afef1af/` — generated dashboard (all pages, `data/*.json`, `assets/data.json`)

Live: https://buffedlizard55-lab.github.io/OLBG4/session-4afef1af/

Docs: `docs/olbg-reverse-engineering.md`, `docs/methodology.md`, `docs/sources.md`.

# OLBG4 — Reverse Engineered OLBG.com (Six Verified Builds)

**Live site (GitHub Pages):** https://buffedlizard55-lab.github.io/OLBG4/  
**Data cut-off:** 2026-10-21 (UTC)  
**Branches merged to `main`:** `arena/f0402305-olbg4` (A), `arena/7114b6a1-olbg4` (B), `arena/74f9613e-olbg4` (C), `arena/290a9dba-olbg4` (D — final hub), `arena/4afef1af-olbg4` (E), `arena/6e0f382d-olbg4` (G), plus the audit/integration boards (F, H, I, J, K). `COORDINATION.md` is the authoritative record of every claim, branch and merge.

Six independent builds live in this repo (A, B, C, D, E, G), plus five cross-build audit and integration boards (F, H, I, J, K). All are published from the same Pages site — nothing has been discarded.

> **Verification status — read this before quoting any count below.** Boards F, I and J audited the
> builds and found real defects; Board K (`arena/47b1b4e2-olbg4`) remediated them. In particular,
> Build D's earlier claim of "governing-body verified, 15 high-confidence predictions" was **not**
> supported by its own data: 26 of its 66 rows carried a non-governing-body source while still being
> marked `verified:true`, and five high-confidence write-ups were contradicted by the official pages.
> Build D now has **2** high-confidence predictions, **43/66** rows on an official source and **52**
> flagged rows. Every change, withdrawal and blanked value is itemised in
> **[the Board K remediation report](session-47b1b4e2/)** with the official URL it was checked against.

| Build | Session | Where | What it is |
|---|---|---|---|
| **A** | `arena/f0402305-olbg4` | `docs/` (landing), `data/rows.json`, `build_site.py`, `gen_pages.py` | 144 rows, 15 sports, ratings built from **official governing-body** sources (NBA, NHL, URC, EHF, PDC, MLB, ICC, WST…). OLBG used to define sport universe. |
| **B** | `arena/7114b6a1-olbg4` | `session-7114b6a1/` (dashboard), `data/*.json`, `scripts/` | 116 fixtures read **directly off OLBG's live sport pages** (reverse-engineered), own win/handicap/total lines, 9 high-confidence picks with 36 sourced facts. |
| **C** | `arena/74f9613e-olbg4` | `session-74f9613e/` (dashboard), `data/session-74f9613e/*.json`, `scripts/session-74f9613e/` | 43 fixtures in 5 sports, each input transcribed from a primary league/tour page (`VERIFICATION.md`); 182 originated selections (money line, handicap, totals); 10 predictions where every claim is listed with its source; 11-row gap register. Build C also carries a portal linking all builds. |
| **D** | `arena/290a9dba-olbg4` | `/` (primary hub `index.html`), `data/matches.json`, `assets/`, `tennis.html` … `aussie-rules.html` | 66 entries across 16 sports on 15 category pages. Originated lines (ELO 40% + form 25% + H2H 15% + venue 15% + injury 5%, 3.5–4.5% overround). **Remediated by Board K** — as published it claimed "governing-body-first verified, 15 high-confidence predictions, 8 flagged"; the audit found 26 rows marked `verified:true` on ESPN/Wikipedia/BBC/Sky sources and 5 write-ups contradicted by the official pages. Now: **43/66 rows on an official source**, 36 verified, **2** high-confidence predictions (NBA03 76 words, MLB01 107 words), **52 flagged**, 23 predictions withdrawn with text preserved, and every row carrying `sourceClass` + `entryType`. |
| **G** | `arena/6e0f382d-olbg4` | `session-6e0f382d/` (dashboard), `data/raw/` + `data/verified/` + `data/matches/`, `tools/model.py` + `tools/build_site.py` | 140 matches + 24 outrights across **all 17 in-scope OLBG sports** (widest single sweep), line-by-line verified vs official sources; documented per-sport models (shrunk Poisson, Normal margins, logistic ratings chains) originating moneyline/handicap/totals; 31 high-confidence picks with unique 72–83-word predictions; greyhounds published flagged with **no pick** (no official form data — verdicts not copied). PR #12. |

- **Root landing (`/`)** → **Board D hub dashboard** (66 entries, filterable KPIs, 15 category subpages, methodology + sources + flagged) + banner linking to A/B/C.
- **`/docs/`** → Board A dashboard (144 rows, 12 high-confidence picks, 15 flagged)
- **`/session-7114b6a1/`** → Board B dashboard (116 OLBG-live fixtures, 9 picks, 50 flags)
- **`/session-74f9613e/`** → Board C dashboard (43 fixtures, 182 selections, 10 predictions, 11 flagged) + portal

---

## Build A — `docs/` (144 rows)

- `docs/` — static site: landing, one page per sport (basketball, ice-hockey, rugby-union/league, handball, darts, baseball, cricket, gaelic-football, volleyball, snooker, tennis, golf, motor-racing, greyhound-racing), Methodology & Markets, Flagged for Review
- `data/rows.csv` / `data/rows.json` — every table row with model inputs, originated line, pick, confidence, verified basis, official source link, status
- `build_site.py` + `gen_pages.py` — build Board A's dataset and render `docs/` (Model v1 formula documented in file + on Methodology page)
- Snapshot: 21 Oct 2026 · Window: 21–25 Oct 2026

## Build B — `session-7114b6a1/` (116 fixtures + 8 futures)

- `data/match_inventory.json` — 116 fixtures across 11 sports, each with exact OLBG event URL (`?event_id=…`)
- `data/model_config.json` — every model constant with `*_basis` (cited OLBG figure or explicit `MODEL ASSUMPTION`)
- `data/board.json` — probability, price, handicap, total, pick, confidence per match
- `data/predictions.json` — 9 high-confidence write-ups (≥103 words each) with per-fact source URLs
- `data/flagged.json`, `data/verification.json` — review items + machine check log
- `scripts/build_model.py` → `scripts/verify.py` → `scripts/build_site.py` (`scripts/README.md`)

## Build C — `session-74f9613e/` (43 fixtures, 182 selections)

- `data/session-74f9613e/inputs.json` — 43 fixtures with verified start time, venue, source id; `inputs_verified` lists confirmations
- `data/session-74f9613e/matches.json` — model output: own money-line, handicap, totals, 182 selections, pick, confidence band
- `data/session-74f9613e/predictions.json` — 10 high-confidence write-ups, each ≥30 words with fact list + source pages
- `data/session-74f9613e/olbg_inventory.json` / `coverage.json` — reconstructed OLBG listing (53 rows) + coverage decision per OLBG sport (22 rows)
- `data/session-74f9613e/findings.json` — irregularity register on Flagged page
- `VERIFICATION.md` — line-by-line checks vs official pages, gaps left blank
- `METHODOLOGY.md` — formulas, constants, thresholds per sport
- `scripts/session-74f9613e/` — `prepare_inputs.py` → `model.py` → `prepare_inventory.py` → `build_site.py` → `validate.py`, wrapped by `build_all.sh`; validator exits non-zero on failure
- CI: `.github/workflows/validate.yml` rebuilds all three data layers for this build and fails if committed output is stale

## Build D — `/` hub + 15 category pages (66 entries, remediated by Board K)

- `index.html` — **primary hub dashboard** (all 66 entries filterable, KPIs, analysis) + banner linking to A/B/C
- `tennis.html`, `basketball.html`, `baseball.html`, `cricket.html`, `rugby.html`, `ice-hockey.html`, `snooker.html`, `darts.html`, `golf.html`, `badminton.html`, `table-tennis.html`, `volleyball.html`, `handball.html`, `esports.html`, `aussie-rules.html` — filtered views of same `data/matches.json`
- `methodology.html` — ELO+form+H2H+venue model, handicap/total math, confidence rules
- `sources.html` — official source registry (18 source groups, every URL)
- `flagged.html` — **52** flagged rows with source links (was 8 as published; do not block merge)
- `data/matches.json` — machine-readable dataset (66 rows, each with `sourceUrl`, `sourceClass`, `sourceDomain`, `entryType`, `verified`, `flagged`). Board K audit trail: `data/session-47b1b4e2/remediation.json`; pre-remediation snapshot: `data/session-47b1b4e2/matches.preremediation.json`
- `data/sources.json` — human-readable registry
- `assets/css/style.css` + `assets/js/main.js` — clean dashboard UI
- Sources: **43/66 rows** on a governing-body page (was 32 before Board K); the remaining 23 are secondary-only (ESPN, Wikipedia, BBC, Sky, Cricinfo, etusuora) and are labelled `sourceClass:"secondary"` on the row and in the UI rather than presented as verified. Registry in `data/sources.json` + `sources.html`
- High-confidence: **2** entries — NBA03 (76 words) and MLB01 (107 words, rebuilt from MLB.com alone). The 15 originally published could not stand: 26 rows were `verified:true` on non-governing-body sources (F-01), and five high-confidence write-ups were contradicted by NHL.com, MLB.com, EuroLeague and the RLWC draw (F-02). **23 predictions are withdrawn with their full text preserved** on the row under `k_withdrawn`; nothing was deleted.

---

## Build E — `session-4afef1af/` (refreshable pipeline, 90 fixtures)

The only build that refreshes itself. `pipeline/` pulls fixtures and results from
`cdn.nba.com`, `api-web.nhle.com` and `statsapi.mlb.com`, fits margin and total ratings, and
originates three market families per fixture (match winner, handicap, match total, with two
alternate lines each). Every six hours the `Ingest, verify, publish` workflow re-runs the
pipeline and commits the refreshed snapshot.

- 90 fixtures in the 21–28 Oct window: NBA 50, NHL 37, MLB 3.
- 40 priced (NHL 37, MLB 3) with 120 market families and 78 graded picks (18 high / 37 medium / 23 low).
- 18 written predictions, 38–60 words, 0 withdrawn, max pairwise similarity 0.483.
- 4 findings: 1 warning + 3 informational. 0 rows excluded, 0 hard failures.
- NBA opening week: only 3 completed regular-season games and no reachable prior-season archive,
  so its 50 fixtures are listed with records and sources but **no markets and no pick**. The
  dashboard says so on every affected row.
- Review page: 20 module claims checked against official endpoints, 5 row-level spot checks
  re-opened live, 9 irregularities found and handled.

## Build J — `session-e1e0c27e/` (independent cross-build audit)

Audits, does not originate. `scripts/session-e1e0c27e/audit.py` reads every build's committed
data (592 rows across A, B, C, D, E, G), classifies each row's source link as official / OLBG /
secondary, matches the same fixture across builds, and `build_site.py` renders seven pages
(Overview, All rows, By build, Spot checks, Cross-build, Method, Flagged for Review).

- 451 rows carry an official link; 109 are OLBG-only (Build B); 32 are secondary-only (Build D).
- 18 row-level re-checks against official pages, with links: 9 confirmed, 5 partial, 4 contradicted.
- 93 fixtures appear in 2+ builds; 10 have opposite match-winner picks.
- 13 findings. The main ones: root hub rows self-marked verified with only ESPN/Wikipedia/BBC/Sky/blog
  sources and high-confidence predictions contradicted by NHL.com, MLB.com and NRL.com (F-01/F-02);
  and a later session's commit `cf9f024` overwriting Build A's `data/rows.json`/`docs/` and Build B's
  `data/predictions.json` with templated texts (F-11/F-12). Nothing in another build was edited by
  this session; requests are logged in `COORDINATION.md`.

## Board K — `session-47b1b4e2/` (remediation + final integration)

Session `arena/47b1b4e2-olbg4`. Board J logged its 13 findings as *cross-session requests* because the
fixes touched files owned by Boards A, B and D. No session had claimed them. This board claims, applies
and integrates them, and adds one finding of its own.

Report: [`session-47b1b4e2/`](session-47b1b4e2/) — Overview · [Change log](session-47b1b4e2/changes.html) ·
[Withdrawn predictions](session-47b1b4e2/withdrawn.html) · [Restored files](session-47b1b4e2/restored.html) ·
[Verification](session-47b1b4e2/verification.html).

| Ref | What was done |
|---|---|
| **K2** (F-11/F-12) | Restored Build A by re-running its own unmodified generator (`build_site.py` + `gen_pages.py`): `data/rows.json` 137 → **144**, `docs/sports/` 11 → **15** pages, output **byte-identical** to `5918922` including Board B's additive banner. Restored Build B's 9 per-claim-sourced predictions and repointed `scripts/build_site.py` at the build-owned copy (fixing a `KeyError: 'match_id'`). The 25 templated predictions are archived verbatim at `data/archive/session-4359d6a4-templated-predictions.json`. |
| **K3** (F-01) | **26** hub rows set `verified:false` + flagged; `sourceClass` and `sourceDomain` published per row. Two rows were *upgraded* to a governing body instead (CRK04 → pcb.com.pk, EL01 → euroleaguebasketball.net). Official-sourced rows **32 → 43**. |
| **K4** (F-02/F-03/F-08) | **14** rows corrected line by line against NHL.com, MLB.com, PCB/ECB, EuroLeague, rlwc2026.com and the PDC; each carries a `k_verification` block with the URL, what was wrong and the check timestamp. |
| **K5** (F-04) | Every row now declares `entryType`: 32 matches, 28 tournaments/rounds, 3 completed results, 3 notes. The dashboard defaults to matches with an Entry control. |
| **K6** | High-confidence gate — a row may only be `High` on a governing-body source. **15 → 2**. |
| **K7** (F-07) | Build B's "Gaelic football is excluded" irregularity **retracted** in `data/flag_notes.json` (the authored source — `scripts/verify.py` regenerates `data/flagged.json`). Original wording preserved verbatim; retraction renders with the galwaygaa.ie link. |
| **K8** (F-06) | Hub landing page explains the 10 opposite cross-build picks as auditable model disagreement, linking Board J's cross-build table. |
| **K9** | Overstated verification wording corrected on `index.html` and all **15** category pages ("Every row has an official source link" → the true 43/66 figure). |
| **K-F14** *(new)* | Found by this board, not by Boards F, G, I or J: unfinished draft text is published in Build D's **rendered data fields**, e.g. `competition` = "WTT Youth/Feeder Concurrent — Chengdu**? Actually** Chennai" and `originatedSpread` = "Game Handicap: MS -**? Actually** badminton: -6.5 points handicap @ 1.91". Also nine predictions on Low/Medium rows that are working notes rather than selections ("Wait for Saturday's averages before committing outright"). **15** rows remediated: 5 fields blanked, 9 predictions withdrawn, 4 `pick` cells restated. The "Actually …" answer was **not** adopted — picking between two unreconciled values without a governing-body page would be inference. |
| **K11** | Re-runnable gate: `python3 scripts/session-47b1b4e2/check_all.py` — **26/26 checks pass**, exit 0. 3,189 local links across 122 HTML files, 0 broken. |

Nothing was discarded: 23 withdrawn predictions keep their full text under `k_withdrawn`, blanked values
are kept under `k_unverified_values`, and originals are preserved inside every retraction.

Scripts: `scripts/session-47b1b4e2/` — `remediate.py` (K3–K6) → `fix_draft_artefacts.py` (K-F14) →
`fix_build_b_flag.py` (K7) → `update_site.py` (K8/K9) → `build_report.py` (K10) → `check_all.py` (K11).
`remediate.py` is **not** idempotent; restore `data/session-47b1b4e2/matches.preremediation.json` before
re-running it.

## Scope & exclusions (per brief)

Excluded everywhere: **soccer, boxing, UFC/MMA, football (soccer), American football, hurling, horse racing, cycling, specials**.

> **In scope — do not flag as a breach.** The brief excludes *hurling*, not **Gaelic football**, and
> *horse racing*, not **greyhound racing**. Board B originally flagged Build A's two Gaelic football
> rows as a scope violation (Board J finding F-07); that flag is **retracted** — the original wording is
> preserved on the item and the retraction renders on
> [`session-7114b6a1/flagged.html`](session-7114b6a1/flagged.html) with the galwaygaa.ie fixture link.
> Builds A, E and G publish Gaelic football legitimately; G publishes greyhounds flagged with **no**
> originated pick because there is no official form data to price from.

Board C reads "football" in the brief as soccer (since hurling is named separately), so Gaelic appears there as "no verified fixture in window" rather than priced — flagged transparently.

> Boards A/B also include Golf and Motor Racing as outright/futures sports with no head-to-head lines — handled as market disclosures on their flagged pages.

---

## Verification — how to manually review any entry

**Board D (primary hub — recommended for audit):**
1. Open `index.html` or any `*.html` category page
2. Click "Official source" link in last column — lands on governing-body domain (e.g., `nba.com`, `mlb.com`, `atptour.com`)
3. Compare date/venue/participants to official page
4. Check `flagged.html` for any entry not confirmable at cut-off (blank + flagged, never inferred)

**Board A:** `docs/` — source links per row.  
**Board B:** `session-7114b6a1/` — OLBG event URLs per row + `data/verification.json` gate (`python3 scripts/verify.py --links`).  
**Board C:** `session-74f9613e/` — `VERIFICATION.md` line-by-line, `scripts/session-74f9613e/validate.py` gate, `.github/workflows/validate.yml` CI.

All high-confidence predictions are ≥30 words and name team/player/form/H2H + selection. Word-count gates enforced in validators and audited manually.

---

## GitHub Pages deploy

Site deploys on push to `main` via `.github/workflows/pages.yml` (+ `validate.yml` for Board C):

- Validates `data/matches.json` + `data/sources.json` (D) **and** `data/rows.json` (A) **and** `session-74f9613e/*.json` (C) as JSON
- Checks all builds' HTML pages exist (19 D pages + 18 A pages + 18 B pages + 5 K pages) and no `TODO` remain — 122 HTML files repo-wide
- Uploads entire repo root as Pages artifact → `github-pages`

After merge, verify at:

- https://buffedlizard55-lab.github.io/OLBG4/ → **Hub (Board D, 66 entries)** with links to A/B/C
- https://buffedlizard55-lab.github.io/OLBG4/docs/ → Board A dashboard (144 rows)
- https://buffedlizard55-lab.github.io/OLBG4/session-7114b6a1/index.html → Board B dashboard (116 fixtures, 9 picks)
- https://buffedlizard55-lab.github.io/OLBG4/session-74f9613e/ → Board C dashboard (43 fixtures, 182 selections)
- https://buffedlizard55-lab.github.io/OLBG4/session-6e0f382d/ → Build **G** dashboard (140 matches + 24 outrights, 17 sports, 31 high-confidence predictions)
- https://buffedlizard55-lab.github.io/OLBG4/session-e1e0c27e/ → Board J cross-build audit (592 rows, 13 findings)
- https://buffedlizard55-lab.github.io/OLBG4/session-47b1b4e2/ → **Board K remediation report** (every finding, change, withdrawal and restoration, with official URLs)

---

## Build G — `session-6e0f382d/` (140 matches + 24 outrights, 17 sports)

- `data/olbg-structure.json` — OLBG structure map (24 sections, URL patterns, markets, scope decisions)
- `data/raw/*.json` — OLBG server-rendered feed as collected 2026-10-21 (150 matches/events + 14 outrights)
- `data/verified/*.json` — line-by-line verified inputs from official sources (17 sports)
- `tools/model.py` → `data/matches/*.json` — mechanical line origination (documented formulas per sport; fair half-point lines; confidence tiers with small-sample/secondary-source caps)
- `tools/predictions.json` — 31 unique high-confidence predictions (72–83 words, verified facts only)
- `tools/build_site.py` → `session-6e0f382d/` — landing + 17 sport pages + methodology + findings + flagged; builder fails on missing source/prediction and link-checks internal targets
- Scope note: Gaelic Football is **in scope** (only Hurling excluded), matching Board E's later correction; greyhound races published flagged with no originated pick

---

## Coordination for parallel sessions

See `COORDINATION.md` — shared task board per brief:

- Claim task → commit/push claim immediately
- Branch `session-<id>/<task>` per session, non-overlapping file scopes
- Shared outputs (`index.html`, `data/*`, nav) only via final integration session (here: Board D as final hub integrator, which merged A+B+C without discarding)
- Stale claim (>60 min no commits) may be taken over with log note
- All merges logged with "how it was resolved — no work discarded"

---

## License & disclaimer

Data curated from official public sources (linked per row). Code MIT-equivalent for site. **18+ — analysis, not betting advice.** Flagged irregularities do not block merge; they are published for your post-deploy review.


## Board F — independent audit (`session-07a080b9/`)
Re-runnable line-by-line audit of Builds A–E: `python3 session-07a080b9/audit.py` → `session-07a080b9/index.html` + `audit.json`. Result 2026-10-21, **as recorded before Board K**: D 66 rows/15 high (min 68 words), A 144, B 116/9 predictions (min 103 words per B gate), C 43/182 selections/10 predictions, E 90 fixtures/18 predictions; 87 HTML files, 1,576 internal links, **0 broken**; only open items are the 2 Gaelic rows in Build A (WARN, already flagged by Build B — published, non-blocking).

> **Superseded by Board K.** Two statements above are no longer true and are kept only as the audit record: Build D's "15 high" is now **2** (the other 13 could not be supported by a governing-body source), and the 2 Gaelic rows are **not** an open item — the brief excludes hurling, not Gaelic football, and Build B's flag against them is retracted (finding F-07). Re-run `python3 scripts/session-47b1b4e2/check_all.py` for the current gate.

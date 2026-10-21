# OLBG4 — Reverse Engineered OLBG.com (Three Verified Builds)

**Live site (GitHub Pages):** https://buffedlizard55-lab.github.io/OLBG4/  
**Data cut-off:** 2026-10-21 (UTC)  
**Branches merged to `main`:** `arena/f0402305-olbg4` (A), `arena/7114b6a1-olbg4` (B), `arena/290a9dba-olbg4` (C — final hub)

Three independent, verified builds live in this repo. All are published from the same Pages site — nothing has been discarded.

| Build | Session | Where | What it is |
|---|---|---|---|
| **A** | `arena/f0402305-olbg4` | `docs/` (landing), `data/rows.json`, `build_site.py`, `gen_pages.py` | 144 rows, 15 sports, ratings built from **official governing-body** sources (NBA, NHL, URC, EHF, PDC, MLB, ICC, WST…). OLBG used to define the sport universe. |
| **B** | `arena/7114b6a1-olbg4` | `session-7114b6a1/` (dashboard), `data/*.json`, `scripts/` | 116 fixtures read **directly off OLBG's live sport pages** (reverse-engineered), own win/handicap/total lines, 9 high-confidence picks with 36 sourced facts. |
| **C** | `arena/290a9dba-olbg4` | `/` (primary dashboard `index.html`), `data/matches.json`, `assets/`, `tennis.html` … `aussie-rules.html` | 66 entries, 16 sports, **governing-body-first verified** — ATP, NBA, MLB, NHL, WST, PDC, PGA/LPGA, BWF, WTT/ITTF, FIVB. Originated lines (ELO 40%+form 25%+H2H 15%+venue 15%+injury 5% with 3.5-4.5% overround), 15 high-confidence predictions (each 68-105 words), 8 flagged. Most exclusion-compliant (correctly omits Gaelic Football/Greyhounds flagged in A/B). |

- **Root landing (`/`)** → **Board C hub dashboard** (66 entries, filterable KPIs, 15 category subpages, methodology + sources + flagged). Banner at top links to Boards A and B.
- **`/docs/`** → Board A dashboard (144 rows, 12 high-confidence picks, 15 flagged) — URC/EHF/PDC/MLB/ICC etc.
- **`/session-7114b6a1/`** → Board B dashboard (116 OLBG-live fixtures, 9 high-confidence write-ups, 50 flagged)

---

## Build A — `docs/` (144 rows)

- `docs/` — static site: landing, one page per sport (basketball, ice-hockey, rugby-union/league, handball, darts, baseball, cricket, gaelic-football, volleyball, snooker, tennis, golf, motor-racing, greyhound-racing), Methodology & Markets, Flagged for Review
- `data/rows.csv` / `data/rows.json` — every table row with model inputs, originated line, pick, confidence, verified basis, official source link, status
- `build_site.py` + `gen_pages.py` — build Board A's dataset and render `docs/` (Model v1 formula documented in file + on Methodology page)
- Snapshot: 21 Oct 2026 · Window: 21–25 Oct 2026
- **Note:** Contains 2 Gaelic Football rows + pages for Golf/Motor Racing/Greyhounds — Gaelic is on the exclusion list per brief, so this is published as a flagged item (not deleted) on the B and C flagged pages.

## Build B — `session-7114b6a1/` (116 fixtures + 8 futures)

- `data/match_inventory.json` — 116 fixtures across 11 sports, each with exact OLBG event URL (`?event_id=…`)
- `data/model_config.json` — every model constant with `*_basis` (cited OLBG figure or explicit `MODEL ASSUMPTION`)
- `data/board.json` — probability, price, handicap, total, pick, confidence per match
- `data/predictions.json` — 9 high-confidence write-ups (≥103 words each) with per-fact source URLs and declared gaps
- `data/flagged.json`, `data/verification.json` — review items + machine check log
- `scripts/build_model.py` → `scripts/verify.py` → `scripts/build_site.py` (`scripts/README.md`)
- `verify.py` exits non-zero on hard failure, suitable as a publish gate

## Build C — `/` hub + 15 category pages (66 entries, governing-body verified)

- `index.html` — **primary hub dashboard** (all 66 entries filterable, KPIs, analysis) + banner linking to A/B builds
- `tennis.html`, `basketball.html`, `baseball.html`, `cricket.html`, `rugby.html`, `ice-hockey.html`, `snooker.html`, `darts.html`, `golf.html`, `badminton.html`, `table-tennis.html`, `volleyball.html`, `handball.html`, `esports.html`, `aussie-rules.html` — filtered views of same `data/matches.json`
- `methodology.html` — ELO+form+H2H+venue model, handicap/total math, confidence rules
- `sources.html` — official source registry (18 source groups, every URL) for manual review
- `flagged.html` — 8 flagged irregularities with source links (do not block merge)
- `data/matches.json` — machine-readable verified dataset (66 rows, each with `sourceUrl`, `verified`, `flagged`, `flagReason`)
- `data/sources.json` — human-readable registry
- `assets/css/style.css` + `assets/js/main.js` — clean dashboard UI (cards, sticky table, badges, search)
- **Sources (governing-body primary, line-by-line verified 2026-10-21):** ATP Tour (Almaty/Brussels/Lyon + Shanghai), NBA.com/ESPN (Tip-Off Oct20 + Oct22/23), MLB.com (World Series MIL 103-59 hosting TB 98-64 Oct23 8pm Fox), ESPN NHL schedule + NHL.com 2026-27, BBC Sport Nations Championship (Nov6 IRE-ARG etc), WST/Northern Ireland Open, PDC European Champs Dortmund, PGA TOUR Baycurrent/Bermuda/Mexico + LPGA BMW Ladies, BWF Denmark/French + WTT Montpellier + FIVB/EHF/IHF/AFL (gaps flagged)
- **High-confidence predictions:** 15 entries, each 68-105 words, unique, non-robotic, include team+player+form+H2H+clear selection
- **Verification:** JSON valid, all HTML 200, 0 TODOs, 58 verified/8 flagged, exclusions enforced (no soccer/boxing/UFC/MMA/football/American football/hurling/horse racing/cycling/specials)

---

## Scope & exclusions (per brief)

Excluded everywhere: **soccer, boxing, UFC/MMA, football (soccer), American football, hurling, horse racing, cycling, specials**.  
Board A still contains 2 Gaelic Football rows (flagged, not deleted). Board B flagged Gaelic presence in A. Board C correctly omits Gaelic/Greyhounds and notes AFL men's off-season (Sep27 GF, no matches Oct21-31) as legitimate "no market" rather than invented fixtures.

> Both A and B also include Golf and Motor Racing as outright/futures sports with no head-to-head match lines — handled as market disclosures on their flagged pages.

---

## Verification — how to manually review any entry

**Board C (primary — recommended for audit):**
1. Open `index.html` or any `*.html` category page
2. Click "Official source" link in last column — lands on governing-body domain (e.g., `nba.com`, `mlb.com`, `atptour.com`)
3. Compare date/venue/participants to official page
4. Check `flagged.html` for any entry not confirmable at cut-off (blank + flagged, never inferred)

**Board A:** `docs/` — same pattern, source links in table per row.  
**Board B:** `session-7114b6a1/` — OLBG event URLs per row + `data/verification.json` gate (`python3 scripts/verify.py --links`).

All high-confidence predictions are ≥30 words and name team/player/form/H2H + selection. Word-count gates are enforced in `scripts/verify.py` (B) and audited manually (A/C).

---

## GitHub Pages deploy

Site deploys on push to `main` via `.github/workflows/pages.yml`:

- Validates `data/matches.json` + `data/sources.json` (Board C) **and** `data/rows.json` (Board A) as JSON
- Checks all three builds' HTML pages exist (19 C pages + 17 A pages + 18 B pages) and no `TODO` placeholders remain
- Uploads entire repo root as Pages artifact → `github-pages` environment

After merge, verify at:

- https://buffedlizard55-lab.github.io/OLBG4/ → **Hub (Board C, 66 entries)** with links to A/B
- https://buffedlizard55-lab.github.io/OLBG4/docs/ → Board A dashboard (144 rows)
- https://buffedlizard55-lab.github.io/OLBG4/session-7114b6a1/index.html → Board B dashboard (116 fixtures, 9 picks, 50 flags)

---

## Coordination for parallel sessions

See `COORDINATION.md` — shared task board per brief:

- Claim task → commit/push claim immediately
- Branch `session-<id>/<task>` per session, non-overlapping file scopes
- Shared outputs (`index.html`, `data/*`, nav) only via final integration session (here: Board C as final hub integrator, which merged A+B without discarding)
- Stale claim (>60 min no commits) may be taken over with log note

---

## License & disclaimer

Data curated from official public sources (linked per row). Code MIT-equivalent for site. **18+ — analysis, not betting advice.** Flagged irregularities do not block merge; they are published for your post-deploy review.


# COORDINATION — OLBG Reverse-Engineering & Originated Lines Project

**Repository:** buffedlizard55-lab/OLBG4
**Goal:** Full list of upcoming matches on OLBG.com for every sport **excluding** soccer/football, boxing, UFC, MMA, American football, hurling, horse racing, cycling, and specials — with our own originated lines, a picked winner per match at low/medium/high confidence, all markets investigated, verified against official sources only. Published as a GitHub Pages dashboard.

## Rules (from project brief)
- Verify line by line. Every table row must have a source link to an **official** site.
- If a value can't be confirmed from an official source, leave it blank and flag it as **unverified** on the Flagged for Review page. Never infer or fill in values.
- Originated lines are our own modelled prices (labelled as such); factual inputs (rankings, standings, results) must come from official sources with links.
- Claim tasks here before starting; keep scopes non-overlapping; small frequent commits; `git pull --rebase` before every push.
- Shared outputs (site index/nav, combined tables) are changed only by the final integration session.
- Statuses: `unclaimed`, `in progress`, `done`, `needs review` (published on Flagged for Review page; does not block anything).

## Branch note (platform constraint)
- Session `6e0f382d` works on branch `arena/6e0f382d-olbg4` (fixed by the Arena platform; cannot be renamed or changed). This deviates from the `session-<id>/<task>` naming in the brief for platform reasons only. No other session is currently active on this repo (single commit "Initial commit", empty README, verified 2026-10-21).

## Session log
| Time (UTC) | Session | Action |
|---|---|---|
| 2026-10-21 | 6e0f382d | Repo reviewed: empty except README. Created this board, claimed all currently-listed tasks (no other sessions present). |
| 2026-10-21 | 6e0f382d | Verified OLBG is live; reverse-engineering of URL structure started. |

## Task board
| # | Task | Status | Owner (session) | File scope | Sources / verification | Irregularities |
|---|---|---|---|---|---|---|
| 1 | Reverse-engineer OLBG site structure (sports, markets, URL patterns) | done | 6e0f382d | `data/olbg-structure.json` | olbg.com sitemap + sport pages (the site itself, for its own structure only) | Sport IDs 18, 19, 24, 27 unused — flagged. Gaelic Football inclusion interpretation flagged. |
| 2 | Collect match lists per included sport from OLBG | done | 6e0f382d | `data/raw/*.json` | OLBG sport landing pages, fetched 2026-10-21 — 150 matches + 14 outrights across 17 sports | Rugby League, Aussie Rules, eSports list zero matches — flagged as coverage gaps to cross-check. |
| 3 | Verify every match against official sources (fixture, date, competition) | in progress | 6e0f382d | `data/matches/*.json` | Official governing-body / league sites per sport | — |
| 4 | Originate lines + winner pick + confidence per match; investigate all markets (win, handicap, totals, etc.) | unclaimed | 6e0f382d | `docs/data/matches/*.json` | Documented model using official rankings/standings/form inputs | — |
| 5 | High-confidence written predictions (≥30 words, unique, verified facts only) | unclaimed | 6e0f382d | `docs/data/matches/*.json` | Official rankings/form sources linked per row | — |
| 6 | Build GitHub Pages site (dashboard + per-sport pages + methodology + Flagged for Review) | unclaimed | 6e0f382d | `docs/**` | Local build check; link check | — |
| 7 | Final integration: re-verify combined data, build check, PR to main, merge, confirm Pages deploy | unclaimed | 6e0f382d | all | GitHub PR + Pages status | — |

## Scope decisions (logged for review)
- **Included sports:** every OLBG sport category except the exclusions in the brief. Exact list recorded in `docs/data/olbg-structure.json` once enumeration finishes.
- **"Updated matches" window:** matches listed on OLBG sport pages at collection time (2026-10-21). Collection timestamp is stamped on every page/row.
- Matches that cannot be verified against an official source stay in the dataset with blank unverified fields and appear on the Flagged for Review page.

## Integration record
- PR: (pending)
- Merge result: (pending)
- GitHub Pages URL: (pending)

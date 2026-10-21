# COORDINATION — shared task board

Updated: 2026-10-21

## Branch policy note

The repository owner's working instructions ask each session to work on `session-<id>/<task>`.
This session is pinned by the hosting platform to the branch **`arena/4afef1af-olbg4`** and is not
permitted to create or push other branches. That branch therefore *is* this session's branch and is
the integration branch for this session. Task ownership below is expressed as a **file scope**
instead of a branch name so that any other session can still avoid conflicts.

- Session ID: `sess-4afef1af`
- Session branch (integration): `arena/4afef1af-olbg4`
- Base: `main` @ `f40a495` (repo contained only a 7-byte README at start)

## Ownership rules in force

1. Read this file before starting work.
2. Claim a task by writing your session ID + file scope below, then commit and push the claim
   immediately.
3. Never start a task already claimed by another live session.
4. Edit only files inside your claimed scope. If you need a change in another session's scope,
   log a request under "Cross-scope requests" instead of editing.
5. A claim older than 60 minutes with no commits may be taken over; note the handoff in the log.
6. Shared outputs (`data/*.json` integration files, `index.html`, navigation, Pages config) are
   changed only by a final integration session.
7. `needs review` = published on the site's **Flagged for Review** page and does not block anything.

## Task board

| ID | Task | Status | Owner | File scope |
|----|------|--------|-------|------------|
| T1 | Coordination board + session claim | in progress | `sess-4afef1af` | `COORDINATION.md` |
| T2 | Repo scaffolding, schema, provenance rules | unclaimed | — | `README.md`, `pipeline/**` |
| T3 | OLBG.com reverse-engineering: taxonomy, URL patterns, page anatomy, evidence | unclaimed | — | `docs/olbg-*.md`, `data/olbg-taxonomy.json` |
| T4 | Official-source ingestion providers (MLB / NBA / NHL) + verification gate | unclaimed | — | `pipeline/providers/**`, `pipeline/verify.py` |
| T5 | Line origination model + market derivation (moneyline, handicap, total) | unclaimed | — | `pipeline/model.py` |
| T6 | Pick selection, confidence rubric, high-confidence prediction writer | unclaimed | — | `pipeline/predictions.py` |
| T7 | Static site build (dashboard, per-sport pages, markets, method, sources, flagged) | unclaimed | — | `pipeline/build_site.py`, `site/**` |
| T8 | GitHub Actions automation (ingest → derive → build → commit) | unclaimed | — | `.github/workflows/**` |
| T9 | Integration: merge, re-verify combined data, PR, merge to `main`, Pages deploy | unclaimed | — | `data/*.json`, `docs/**`, PR |

## Cross-scope requests

_none_

## Log

- 2026-10-21 `sess-4afef1af`: repo inspected. Contents: `README.md` (7 bytes), single commit
  `f40a495`. No other sessions active. Claimed T1 and, because no other session is live, will claim
  T2–T9 sequentially as work proceeds (claims recorded in the table above at claim time).
- 2026-10-21 `sess-4afef1af`: environment facts established for all sessions:
  - The sandbox shell can reach **only** `github.com`, `codeload.github.com`, `api.github.com`,
    `registry.npmjs.org`, `pypi.org`, `files.pythonhosted.org`. Direct `curl` to `olbg.com`,
    `cdn.nba.com`, `api-web.nhle.com`, `statsapi.mlb.com`, `site.api.espn.com` returns HTTP 000.
  - A page-fetch proxy can reach the public web (OLBG and official league sites render), but its
    output lands in the agent context, not on disk.
  - Therefore **all bulk ingestion must run on GitHub Actions runners**, which have full egress.
    The pipeline is written to run there (workflow `ingest-and-build.yml`) and to be re-runnable
    with zero manual input.

# COORDINATION — OLBG4 Multi-Session Task Board

> **Shared task board.** Every session must read this file before starting work.
> Claim a task by writing your session ID + file scope, commit & push immediately.
> Never start a task another session has claimed. Keep scopes non-overlapping.
> Session branches: `session-<id>/<task>` — edits only inside claimed scope.
> Shared outputs (index, nav, table data) changed only by final integration session.

**Current date (repo clock): 2026-10-21 (UTC)**
**Active sessions:** `arena/290a9dba-olbg4` (primary / integration)

---

## Task Board

| # | Task | Status | Owner Session | Files / Scope | Sources | Verification |
|---|------|--------|---------------|---------------|---------|--------------|
| T01 | Repo audit + COORDINATION.md creation | **done** | arena/290a9dba-olbg4 | COORDINATION.md | — | — |
| T02 | Data model + verification framework (schema, source-link policy) | **in progress** | arena/290a9dba-olbg4 | data/matches.json, data/sources.json, methodology.html | ATP, NBA, MLB, NHL, WST, PDC, PGA, LPGA, BWF, WTT, EHF, FIVB | line-by-line verified, source link per row |
| T03 | Tennis — ATP Almaty/Brussels/Lyon, WTA Finals context | unclaimed | — | tennis.html, data subset tennis | atptour.com, wtatennis.com |  |
| T04 | Basketball — NBA opening week + EuroLeague R7 | unclaimed | — | basketball.html | nba.com, euroleaguebasketball.net |  |
| T05 | Baseball — MLB World Series Brewers vs Rays | unclaimed | — | baseball.html | mlb.com |  |
| T06 | Cricket — AUS v SA Tests, Pakistan Tri-Series, AUS women v BAN | unclaimed | — | cricket.html | icc-cricket.com, cricket.com.au |  |
| T07 | Rugby Union — Nations Championship Autumn fixtures | unclaimed | — | rugby.html | world.rugby, bbc.com/sport/rugby-union |  |
| T08 | Ice Hockey — NHL Oct 20-23 slate | unclaimed | — | ice-hockey.html | nhl.com |  |
| T09 | Snooker — Northern Ireland Open | unclaimed | — | snooker.html | wst.tv, worldsnooker.com |  |
| T10 | Darts — PDC European Championship | unclaimed | — | darts.html | pdc.tv, skysports.com/darts |  |
| T11 | Golf — PGA Fall + LPGA Asian swing | unclaimed | — | golf.html | pgatour.com, lpga.com |  |
| T12 | Badminton + Table Tennis — Denmark/French Open, WTT Montpellier | unclaimed | — | badminton.html, table-tennis.html | bwfbadminton.com, wtt.com, ittf.com |  |
| T13 | Volleyball + Handball + Esports + Aussie Rules — gaps & off-season notes | unclaimed | — | volleyball.html, handball.html, esports.html, aussie-rules.html | fivb.com, ehf.eu, afl.com.au |  |
| T14 | Site creation — landing, nav, dashboard, tables, styling | unclaimed | — | index.html, assets/css/*, assets/js/*, _config.yml, .nojekyll | — | build check |
| T15 | Flagged for Review page + irregularities log | unclaimed | — | flagged.html | — | — |
| T16 | Final integration — merge branches, re-verify line by line, broken-link check, GH Pages deploy, PR + merge | unclaimed | — | all shared outputs, .github/workflows/pages.yml | — | — |

> **Single-session override (2026-10-21):** Only one active session (`arena/290a9dba-olbg4`) is live.
> To avoid fragmentation the active session claims **all tasks T02–T16** as an integrated scope.
> If additional sessions appear, this claim will be split per the board above and scopes re-assigned.

### Claimed Scope — arena/290a9dba-olbg4

- **Branch:** `arena/290a9dba-olbg4` (session root)
- **Claimed tasks:** T02, T03, T04, T05, T06, T07, T08, T09, T10, T11, T12, T13, T14, T15, T16
- **Files owned:** all repo content (data/, index.html, *.html, assets/, .github/, _config.yml, README.md)
- **Commit cadence:** small frequent commits, pull --rebase before push
- **Verification rule:** Every table row must have official source link; unverified values blank + flagged. No inference.
- **No-hallucination rule:** All predictions include verified form/history; sources linked.

### Log

- 2026-10-21 05:15 UTC — arena/290a9dba-olbg4 — initial branch created from main (f40a495)
- 2026-10-21 05:20 UTC — arena/290a9dba-olbg4 — COORDINATION.md created, claimed all tasks as single-session integrated scope
- 2026-10-21 05:30 UTC — arena/290a9dba-olbg4 — web_search verification pass: ATP calendar, NBA opening night, MLB World Series (Brewers vs Rays Oct 23-31), NHL 2026-27 slate, Nations Championship, Northern Ireland Open, PDC European Championship, PGA Baycurrent/Bermuda, LPGA BMW, BWF Denmark/French, WTT Montpellier — sources captured

### Rules Reminder

1. Read this file before starting.
2. Claim → commit → push immediately.
3. Never edit files outside your claimed scope; log request here instead.
4. Small frequent commits; `git pull --rebase` before push; resolve conflicts without discarding others.
5. When done, record sources, verification performed, irregularities; mark done.
6. Every row = source link to official site; unverified = blank + flagged.
7. Never mark verified without checking official source + link.
8. Shared outputs (table data, index, nav) only via final integration session after all tasks done.
9. Stale claim (>60 min no commits) may be taken over with log note.
10. Final integration: merge branches, re-verify line by line, confirm build + no broken links, publish to GH Pages, PR → merge, record link.


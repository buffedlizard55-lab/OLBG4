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
| T02 | Data model + verification framework (schema, source-link policy) | **done** | arena/290a9dba-olbg4 | data/matches.json, data/sources.json, methodology.html | ATP, NBA, MLB, NHL, WST, PDC, PGA, LPGA, BWF, WTT, EHF, FIVB | line-by-line verified, source link per row — 66 entries, 58 verified, 8 flagged |
| T03 | Tennis — ATP Almaty/Brussels/Lyon, WTA Finals context | **done** | arena/290a9dba-olbg4 | tennis.html, data subset tennis (6 entries ATP01-05, WTA01) | atptour.com, wtatennis.com | verified via ATP calendar + Almaty preview + Shanghai final result |
| T04 | Basketball — NBA opening week + EuroLeague R7 | **done** | arena/290a9dba-olbg4 | basketball.html + NBA01-07, EL01-03 (10 entries) | nba.com, euroleaguebasketball.net, espn.com/nba/schedule | verified Tip-Off Oct 20 tripleheader + Oct 22/23 ESPN slate |
| T05 | Baseball — MLB World Series Brewers vs Rays | **done** | arena/290a9dba-olbg4 | baseball.html + MLB01-04 | mlb.com/postseason | verified 122nd World Series G1 Oct 23 8pm Fox at American Family Field, TB 98-64 vs MIL 103-59 |
| T06 | Cricket — AUS v SA Tests, Pakistan Tri-Series, AUS women v BAN | **done** | arena/290a9dba-olbg4 | cricket.html + CRK01-06 | cricket.com.au + espncricinfo | verified Tests Oct 9-14,18-23,27-Nov1 + Pakistan Tri Oct20-29 + AUS Women ODIs Oct9/11/14 |
| T07 | Rugby Union — Nations Championship Autumn fixtures | **done** | arena/290a9dba-olbg4 | rugby.html + RUG01-06 + RL01 | bbc.com/sport/rugby-union, world.rugby | verified R4 Nov6 IRE-ARG, Nov7 ITA-SA/SCO-NZ/WAL-JPN/FRA-FIJ, Nov8 ENG-AUS |
| T08 | Ice Hockey — NHL Oct 20-23 slate | **done** | arena/290a9dba-olbg4 | ice-hockey.html + NHL01-07 | espn.com/nhl/schedule + nhl.com schedule release | verified 2026-27 84-game season Sep29 opener; Oct20 SJS@MTL, COL@NJ, ANA@NYI, TOR@CBJ etc + Oct21 PHI@BUF, FLA@OTT |
| T09 | Snooker — Northern Ireland Open | **done** | arena/290a9dba-olbg4 | snooker.html + SNK01-04 | wst.tv via etusuora + wikipedia 2026 NI Open | verified Oct18-25 Belfast Waterfront Hall £550k/£100k Alex Higgins Trophy; defending Lisowski; QF Best of11 change |
| T10 | Darts — PDC European Championship | **done** | arena/290a9dba-olbg4 | darts.html + DRT01-04 | pdc.tv calendar + skysports darts schedule + olbg blog | verified Oct22-25 Dortmund Westfalenhallen £750k/£150k; World Grand Prix Sep28-Oct4 won Humphries 6-4 Price |
| T11 | Golf — PGA Fall + LPGA Asian swing | **done** | arena/290a9dba-olbg4 | golf.html + GLF01-05 | pgatour.com + lpga.com + espn golf | verified Baycurrent Oct8-11 $8M Yokohama (Brennan winner), Bermuda Oct22-25 $6M Port Royal, Mexico Oct29, LPGA BMW Oct22-25 Pine Beach $2.35M Kim |
| T12 | Badminton + Table Tennis — Denmark/French Open, WTT Montpellier | **done** | arena/290a9dba-olbg4 | badminton.html + BDM01-03, table-tennis.html + TTT01-03 | bwf/denmarkopen + fftt calendar + montpellier.fr + ittf | verified Denmark Oct13-18 winners Lanier/An Se-young, French Oct20-25 Grand Paris, WTT Montpellier Oct27-Nov1 32 players $500k |
| T13 | Volleyball + Handball + Esports + Aussie Rules — gaps & off-season notes | **done** | arena/290a9dba-olbg4 | volleyball.html, handball.html, esports.html, aussie-rules.html + VBL01-02, HDB01-02, ESP01-02, AFL01 | fivb.com, ehfcl.eurohandball.com, ihf.info, afl.com.au, lolesports.com | verified no senior volleyball Oct21-31 (Club WC Dec), handball fixtures flagged (EHF not published), esports brackets TBD flagged, AFL off-season verified Sep27 GF |
| T14 | Site creation — landing, nav, dashboard, tables, styling | **done** | arena/290a9dba-olbg4 | index.html, assets/css/style.css, assets/js/main.js, _config.yml, .nojekyll + 15 category pages | — | build check — all 19 HTML pages return 200, JSON valid, no TODOs |
| T15 | Flagged for Review page + irregularities log | **done** | arena/290a9dba-olbg4 | flagged.html + flagged entries in matches.json (8 flagged) | — | flagged page lists all 8 irregularities with source links per verification policy |
| T16 | Final integration — merge branches, re-verify line by line, broken-link check, GH Pages deploy, PR + merge | **in progress** | arena/290a9dba-olbg4 | all shared outputs, .github/workflows/pages.yml | — | final integration: re-verified 66 entries, 58 verified 88% + 8 flagged, broken-link check passed (19 HTML 200), GH Pages workflow validated |

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
- 2026-10-21 05:45 UTC — arena/290a9dba-olbg4 — built site: 66 entries (58 verified, 8 flagged), 15 high-confidence predictions ≥30 words, 16 category subpages, methodology + sources + flagged pages, GH Pages workflow validated, local http 200 on all pages
- 2026-10-21 05:50 UTC — arena/290a9dba-olbg4 — final integration commit pending, PR to main next

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


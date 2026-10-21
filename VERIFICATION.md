# VERIFICATION LOG

Capture window: **2026-10-21 (UTC)**. This log records what was checked, against which official
page, and what came out. It is deliberately written per source rather than per summary so a
reviewer can re-run any single line.

Rule applied throughout: **a value that could not be confirmed is blank and flagged. It is never
inferred, interpolated or "corrected".**

---

## 1. NHL — 12 fixtures, 12 priced

**Fixtures** — `https://www.nhl.com/schedule/2026-10-22` (S11). Checked: every matchup, every
face-off time and the zone label (EDT).

| Check | Result |
| --- | --- |
| Games listed on the official schedule for 22 Oct 2026 | 12 |
| Games captured | 12 |
| Matchups identical to source | 12 / 12 |
| Times identical to source | 12 / 12 |
| Venue | **not published on the schedule table used**, so the venue column is left blank rather than filled from memory |

**Inputs** — `https://www.nhl.com/standings/2026-10-20/wildcard` (S10), page stamp
"current as of Oct 21, 1:14 AM EDT". Checked field by field for all 32 clubs: GP, W, L, OT, PTS,
GF, GA, home record, away record, L10, streak. 32 / 32 rows matched the transcription in
`scripts/prepare_inputs.py`.

*Irregularity noted:* the standings URL contains `2026-10-20` while the page stamp says 21 Oct.
The date in the URL was left as published; no assumption was made about why.

---

## 2. NBA — 11 fixtures, 9 priced, 2 flagged

**Fixtures** — `https://www.nba.com/schedule?date=10/21/2026` (S14). The page header states
"Wednesday, October 21 — 11 Games". All 11 were captured after reading both rendered chunks, each
with its tip-off time (ET) and venue.

**Inputs** — `https://www.nba.com/standings?Season=2025-26` (S12) and
`https://www.nba.com/standings` (S13).

| Check | Result |
| --- | --- |
| Eastern Conference rows matched | 15 / 15 |
| Western Conference rows matched | 13 / 15 — the render truncated at Memphis (13th); Sacramento and Utah rows were not present |
| 2026-27 records matched | 6 clubs had played (DET 1-0, PHI 1-0, OKC 1-0, BOS 0-1, NYK 0-1, SAS 0-1); all other listed clubs 0-0 |

**Consequence:** Utah at Memphis and Sacramento at LA Clippers are published **without a line**
because a required record could not be read. Both are on the Flagged page. No substitute value
was used.

*Irregularity noted:* the 2025-26 table carries clinch markers (`e`, `a`, `x`, `pi`, `o`) that are
no longer meaningful after the season; they were ignored and are not reproduced anywhere.

---

## 3. MLB — 1 fixture, 1 priced

**Fixture** — `https://www.mlb.com/standings/` (S15) lists, for both Tampa Bay and Milwaukee,
a next game on **Oct 23** with the opponent and a link to game `849805`. The Gameday page (S16)
resolves to `/rays-vs-brewers/2026/10/23/849805`, confirming the matchup and date.

| Check | Result |
| --- | --- |
| Fixture confirmed by two official pages | yes |
| First-pitch time | **not stated on either page** → left blank, labelled "first-pitch time not confirmed" |
| Venue | not stated in the captured rows → blank |

**Inputs** — S15 final 2026 regular-season table: TB 98-64, RS 736, RA 650, home 55-26, away
43-38; MIL 103-59, RS 832, RA 618, home 55-26, away 48-33. All 12 values match.

*Irregularity noted:* the standings page was headed "Sunday Sep 27" while showing final records
and an Oct 23 next game. The header date appears to be a stale control; the record columns are the
final regular-season figures. This is recorded rather than silently corrected.

---

## 4. Snooker — 11 fixtures, 2 priced, 9 flagged

**Fixtures** — `https://www.wst.tv/matches/b4533c9e-8d2c-4ecc-8dfd-c6b284705578` (S18). The page
groups matches into "Completed" and "Scheduled". All 11 "Scheduled · Round 2 · Wed 21 Oct" rows
were captured with their published UK times: 05:00 (2), 08:00 (2), 09:00 (2), 14:00 (3), 15:00 (2).

| Check | Result |
| --- | --- |
| Scheduled Round 2 matches on the official page | 11 |
| Captured | 11 |
| Best-of-7 format evidenced by completed Round 2 scorelines (e.g. 3-4, 4-2) | yes |
| Round 1 results used in predictions | Higgins 4-1 Highfield; Jak Jones 4-1 Ford; Williams 4-2 R. Williams; Zhang 4-2 Pullen — all read from the same official page |

**Inputs** — `https://www.wst.tv/rankings/abfba8fe-1423-5a2a-a96b-d77e8b413ca8?showLive=false`
(S17). Positions 1-36 with exact prize money were read and transcribed; all 36 match.

**Consequence:** only Higgins v Jak Jones and Zhang Anda v Mark Williams have both players inside
the captured top 36. The other nine matches are listed with the official fixture link and no line.

---

## 5. Rugby Union — 8 URC fixtures, 8 priced; 11 French fixtures flagged

**Fixtures** — `https://stats.unitedrugby.com/match-centre/2026-27/4` (S19). Round 4 shows three
Friday matches at 14:45 and five Saturday matches at 07:45, 10:00, 10:00, 13:00 and 14:00, each
with a venue. All eight captured.

| Check | Result |
| --- | --- |
| Round 4 fixtures on the official page | 8 |
| Captured | 8 |
| Venue strings identical | 8 / 8 |
| Time zone | page states "All times shown are **Local**" → recorded as local, **no UTC conversion** |
| Round 3 results used in predictions | Glasgow 36-19 Connacht; Dragons 31-38 Ospreys; Bulls 57-15 Lions; Stormers 39-22 Sharks; Zebre 12-29 Edinburgh; Scarlets 27-26 Benetton; Ulster 26-26 Munster; Leinster 29-5 Cardiff — all read from S19 |

**Inputs** — `https://stats.unitedrugby.com/match-centre/table/2026-27` (S20). All 16 clubs:
PTS, PL, W, D, L, BP, PF, PA. 16 / 16 matched.

*Scope gap flagged:* OLBG's rugby-union page also listed eleven French Top 14 / Pro D2 fixtures.
No official LNR or Pro D2 page was captured this cycle, so those eleven are on the Flagged page
with the OLBG link and an explicit "no official source" marker.

---

## 6. Cricket — 10 fixtures, 0 priced

**Fixtures** — `https://www.icc-cricket.com/` (S21) "Live and Upcoming" list. Ten fixtures were
captured with ICC's own timestamps, including Afghanistan v Bangladesh (ODI, 21 Oct 07:30) and
Namibia v Ireland 1st and 2nd ODIs (22 and 24 Oct 03:30).

**Inputs attempted** — `https://www.icc-cricket.com/rankings/team-rankings/mens/odi` (S22). The
ranking table rendered as empty table cells. No team-strength number was taken from any other
page, and no line was originated. The fixture list is published; the prices are blank.

---

## 7. Darts — 16 fixtures, 0 priced

**Listing** — `https://www.olbg.com/betting-tips/Darts/All_Darts/All_Events/15` (S02). Sixteen
European Championship first-round pairings with times were captured.

**Official confirmation attempt** — `https://www.pdc.tv/tournaments/machineseeker-european-championship`
(S23). The page confirms the event, the venue (Westfalenhallen, Dortmund), the field size (32
players, seeded on European Tour performance) and the short-format leg play, but its draw did not
render as readable data. No pairing is treated as confirmed.

**Result:** all 16 are flagged, not priced. No PDC Order of Merit data was captured, so no
player-strength input exists either.

---

## 8. Tennis — 15 fixtures, 0 priced

**Listing** — `https://www.olbg.com/betting-tips/Tennis/All_Tennis/3` (S04). Fifteen pairings with
times were captured.

**Official confirmation attempt** — `https://www.atptour.com/en/scores/current` (S24) returns live
scores and completed results, not the forward draw. A constructed draw URL
(`/en/scores/current/vienna/9410/draw`) returned HTTP 404. No per-player ranking or form table was
successfully captured.

**Result:** all 15 are flagged, not priced.

---

## 9. Rugby League — 0 fixtures

`https://www.olbg.com/betting-tips/Rugby_League/All_Rugby_League/All_Events/10` (S07) listed three
rows, all outright/tournament markets: State of Origin 2027, Super League 2027 Grand Final, NRL
2027 Grand Final. No head-to-head fixture existed to price.

---

## 10. Model outputs — internal consistency

`scripts/validate.py` enforces, on every run:

- every priced match has a money line, a handicap and (except NBA) a total;
- every selection has 0 < probability < 1 and odds >= 1.01;
- implied probability from the published odds is within 0.06 of the model probability;
- each market's overround is between 1.00 and 1.10;
- the published pick is one of the originated selections and is one of the two match winners;
- no match is priced unless `inputs_verified` is true;
- every high-confidence pick has a prediction of at least 30 words that names the selection,
  contains numeric form evidence, and cites only official sources;
- no internal link on the site is broken and no external link points at a URL that was not
  actually captured as a source.

Latest run: **43 matches, 32 priced, 182 selections, 10 predictions, 18 pages — all checks pass.**

---

## 11. Known irregularities to review

1. **NBA Western Conference rows truncated** (Memphis, Sacramento, Utah) → two games unpriced.
2. **ICC ODI ranking table empty** → no cricket lines at all.
3. **PDC and ATP draws not machine-readable** → darts and tennis only listed, never priced.
4. **MLB first-pitch time and venue absent from the captured pages** → left blank.
5. **NHL venue absent from the schedule table used** → left blank.
6. **French rugby fixtures listed by OLBG but not verified** → flagged, not priced.
7. **MLB standings page header date ("Sunday Sep 27") inconsistent with its final records** →
   recorded, records used, header not reproduced.
8. **NBA 2025-26 clinch markers** are stale post-season and were ignored.
9. **URC kick-off times are local**, not UTC; no conversion was attempted.
10. **OLBG is never a fact source.** It is used only to reconstruct which fixtures and markets the
    site lists. Every fact on the site traces to an official page.

# Board S2 — high-confidence odds-window focus + 22 Oct freshness verification

Session: `arena/fca9d738-olbg4` · review boundary: **2026-10-22** (UTC) ·
canonical input: `data/master.json` (generated 2026-10-21, 317 rows).

## What this is

A session-scoped desk that answers the brief's focus question: **which High
picks sit between -250 and +10000, and are they verified?**

- Every current in-scope canonical fixture (164, dated ≥ 22 Oct) was checked
  line by line; each row keeps its canonical official link or is held.
- All **30 current High fixtures were live-confirmed** against official
  league/tour/federation/club pages read on 22 Oct 2026 (28 confirmed, 2
  corroborated via secondary excerpts against an official round calendar).
- Each High pick's **own matching originated price** was converted to American
  odds. **19 sit inside -250/+10000** (from -244 to -171, i.e. none shorter
  than -250); 11 cannot be placed in the window (7 moneyline picks with no
  published moneyline, 4 totals/handicap picks whose line has no matching
  published price) and are held from the focus list.
- **4 replacement written predictions** (72–93 words, unique, human) were
  authored for the High rows whose canonical text is templated
  (M0139, M0240, M0246, M0274). Every factual claim cites the official page it
  was read on. The 5th templated High (M0071, 21 Oct) predates the boundary,
  so no replacement is authored.
- **15 findings** are published on `flagged.html` with source links, including
  two official-source quirks found while verifying (NRL.com's Tonga margin
  inconsistency; a wrong-city claim in canonical M0240 copy, corrected here).

Nothing was invented, re-priced, or re-graded. Other boards' files are
untouched; anything needing another owner is logged as an integration request
in `COORDINATION.md`, not applied.

## Pages and data

| Path | Contents |
|---|---|
| `session-fca9d738/index.html` | Focus desk: 19-pick focus list with predictions + filterable 164-row table |
| `session-fca9d738/flagged.html` | 15 findings with source links |
| `data/session-fca9d738/review.json` | Machine-readable review (rows, focus, findings, live sources) |
| `data/session-fca9d738/predictions.json` | 4 replacement predictions with per-fact sources |

## Official pages read (2026-10-22)

NHL schedule/score API (`api-web.nhle.com`, 22–27 Oct slates) · PDC draw +
schedule pages (`pdc.tv`) · NRL R2 late mail + R1 wrap (`nrl.com`) · URC R4
match centre (`stats.unitedrugby.com`) · Panathinaikos schedule (`paobc.gr`) ·
EuroLeague R7 game centre (`euroleaguebasketball.net`) · LNR Pro D2 calendar
(`prod2.lnr.fr`) · Stade Toulousain official site (`stadetoulousain.fr`).
Full URL list with coverage notes is in `review.json` → `live_sources`.

## Rebuild / verify

```bash
python3 session-fca9d738/build_review.py
python3 session-fca9d738/verify_review.py
```

The verifier rebuilds byte-for-byte, asserts prediction length/uniqueness/
selection wording, re-checks the window maths, confirms no held row is
promoted, checks local links, and confirms no out-of-scope file changed.

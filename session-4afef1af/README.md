# Build D — official-data line desk

Automated counterpart to builds A, B and C in this repository. No hand-entered rows: every
fixture, record and form line is pulled from a league-owned endpoint at build time, every
number is either read from that feed or computed by `pipeline/` and labelled as model output.

**Dashboard:** `session-4afef1af/index.html` (published at
`https://buffedlizard55-lab.github.io/OLBG4/session-4afef1af/`).

## What it does

1. **Ingest** — NBA (`cdn.nba.com` schedule JSON), NHL (`api-web.nhle.com`), MLB
   (`statsapi.mlb.com`). Only regular-season games feed the ratings.
2. **Rate** — ridge least squares for margin and total, 120-day half-life, with an opening
   line fitted on the previous completed season.
3. **Price** — three market families per fixture (match winner, handicap, match total) with
   two alternate lines each; probabilities come from the empirical residual distribution.
4. **Pick** — one headline selection per priced fixture, graded high / medium / low from
   probability, sample size and a second confirming fit.
5. **Write** — for every high-confidence pick, a 30+ word prediction assembled only from
   verified facts and linted for length, explicit selection and uniqueness.
6. **Verify** — official-domain source check, schema, probability sum/range, price range,
   window, prediction lint. Failing rows are excluded and flagged, never published.
7. **Publish** — 13 static pages, no external assets, relative links only.

## Running it

```bash
python -m pipeline.selftest          # offline, no network
python -m pipeline.run --strict      # ingest → model → verify → site
```

CI (`.github/workflows/olbg.yml`) runs both every six hours and on every change to
`pipeline/**`, then commits the refreshed snapshot and site back to the branch.

## Honest limits

- Only leagues with an official machine-readable feed are ingested. Every other OLBG sport is
  listed on the Sources page as *not ingested*, with the reason.
- If a league's per-team sample is under 20 completed games, its fixtures are published with
  records and sources but **no markets and no pick**. This is the NBA's state during opening
  week: `stats.nba.com` does not answer from the build runner and the CDN carries only the
  current season.
- No bookmaker or OLBG price is used anywhere. Prices are our own model output.
- Unconfirmable values are left blank and listed on `flagged.html`; nothing is estimated.

## Map

| Path | Contents |
|---|---|
| `pipeline/providers/` | one module per league, official endpoints only |
| `pipeline/model.py` | ratings, opening line, empirical probabilities |
| `pipeline/markets.py` | market construction, prices, picks |
| `pipeline/predictions.py` | fact extraction, block composer, lint |
| `pipeline/verify.py` | verification gate and findings |
| `pipeline/review.py` | line-by-line review log and spot checks |
| `session-4afef1af/` | generated dashboard (data + 13 pages) |
| `docs/methodology.md`, `docs/sources.md` | method and source register |

# Board AF — 22 October 2026 evening desk

Session `arena/ddbcc895-olbg4`. An independent refresh of every in-scope OLBG sport, read from the
governing body's own page, priced by our own model, with a hand-written prediction for the five
strongest selections in each covered sport.

## What is here

| Page | What it shows |
|---|---|
| `index.html` | dashboard, totals and sport coverage |
| `entries.html` | every fixture, priced or not, with the official source on each row |
| `picks.html` | one featured selection per priced fixture, with confidence and the −250…+10,000 flag |
| `predictions.html` | 50 hand-written predictions (10 sports × 5), 33–61 words |
| `markets.html` | match winner, handicap, total and derivative coverage by sport |
| `coverage.html` | all 18 in-scope sports, including the seven with no verifiable fixture |
| `review.html` | line-by-line audit of five committed desks (1,144 rows) against this evening's capture |
| `flagged.html` | 23 irregularities, gaps and judgement calls, each with the official page tried |
| `olbg.html` | OLBG reverse-engineering and the reconciliation of all 158 live listings |
| `methodology.html`, `sources.html`, `verification.html` | how the numbers were made and checked |
| `sports/<slug>.html` | one page for each of the 18 sports |

## Numbers

- **336 verified fixtures / rows** across 11 sports; **270 priced** across 10 sports.
- **6,010 market selections** (match winner, handicap, total, winning-margin derivative).
- **204 High-confidence selections**, **113 of them inside −250…+10,000**.
- **50 predictions**, 10 sports × 5, minimum 33 words, no pair above 0.25 3-gram Jaccard.
- **25 verification checks, 0 failures.**

## Rebuild

```bash
python3 scripts/session-ddbcc895/extract.py data/session-ddbcc895/capture/20261022T211325Z data/session-ddbcc895/fixtures_raw.json
python3 scripts/session-ddbcc895/ratings.py  data/session-ddbcc895/capture/20261022T211325Z
python3 scripts/session-ddbcc895/originate.py
python3 scripts/session-ddbcc895/predictions.py
python3 scripts/session-ddbcc895/flags.py
python3 scripts/session-ddbcc895/review.py
python3 scripts/session-ddbcc895/build_site.py
python3 scripts/session-ddbcc895/verify.py
```

The capture itself is produced by `.github/workflows/af-ddbcc895.yml` on a runner with open egress;
the raw bytes and their SHA-256 manifest are committed under `data/session-ddbcc895/capture/`.

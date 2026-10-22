# Board V — verified fixtures, own lines, confidence-graded picks

**Live:** https://buffedlizard55-lab.github.io/OLBG4/session-f957db05/
**Session:** `arena/f957db05-olbg4` · **Data cut-off:** 2026-10-22 (UTC)

This folder is a self-contained dashboard. It is generated, never hand-edited:

```bash
python3 data/session-f957db05/extract.py        # official bytes -> compact extracts
python3 data/session-f957db05/model.py          # extracts -> probabilities, prices, picks
python3 data/session-f957db05/build_coverage.py # live OLBG taxonomy + irregularity register
python3 data/session-f957db05/facts.py          # evidence bullets, generated from inputs
python3 session-f957db05/build.py               # render this site
python3 session-f957db05/verify.py              # 19 gates, all must pass
```

## What is in it

| Page | Content |
|---|---|
| `index.html` | 98 priced fixtures, filterable, one official source link per row |
| `picks.html` | 8 High-confidence picks, each with a written prediction (48–56 words) and generated evidence bullets |
| `markets.html` | moneyline / handicap / total coverage per sport, with the formulas |
| `coverage.html` | all 21 sports on the live OLBG menu: in-scope or excluded, the official source attempted, the HTTP status it returned, fixtures priced |
| `verification.html` | one line per published fixture with the verified inputs and the exact official URL |
| `sources.html` | domains, endpoints, byte counts and SHA-256 of every captured document |
| `methodology.html` | the formulas, the price rule, the −250 arithmetic, and the limitations |
| `flagged.html` | nine irregularities, each with evidence, published rather than smoothed over |
| `sports/*.html` | the same data per sport |

## The three numbers that matter

- **98 fixtures** across ice hockey (82), baseball (7) and esports (9) — each confirmed against an official
  league feed (`api-web.nhle.com`, `statsapi.mlb.com`, `esports-api.lolesports.com`).
- **8 High picks**, all inside the requested −250 … +10,000 window, each with a written prediction.
- **11 in-scope sports unpriced** — named on `coverage.html` with the official URL and HTTP status that stopped
  them, and logged as V-F01/V-F09. No fixture, price or pick was borrowed from a tipster site to fill the gap.

## Honest limitations

The shell in this sandbox reaches GitHub only; the official bytes were captured by the Board U collector on a
GitHub Actions runner at 2026-10-22T02:47Z and are reproduced here with their SHA-256 (V-F08). No request in this
session went to an official domain directly. Head-to-head history is not captured, so no prediction claims one
(V-F07). Club-level ratings rest on 7–11 games and are shrunk accordingly (V-F04).

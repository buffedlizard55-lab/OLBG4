# Methodology — official-data line desk (build D)

This document describes exactly what `pipeline/` computes. It is the reference for the
**Methodology** page of the dashboard (`session-4afef1af/methodology.html`), which is generated
from the same constants.

## 1. Scope

In scope: every sport on OLBG except the ones the owner excluded — soccer/association football,
American football, boxing, UFC/MMA, hurling, horse racing, cycling and specials. Gaelic football
**is in scope**: the owner named hurling separately and confirmed Gaelic football stays in, so it
is listed as in-scope and only excluded from the *priced* set because no official machine-readable
GAA fixture/result feed was identified.

Eligible for ingestion: sports with an **official, machine-readable** fixture/results feed. Three
qualify today:

| Sport | League | Feed | Official domain |
|---|---|---|---|
| Basketball | NBA | `cdn.nba.com/static/json/staticData/scheduleLeagueV2.json` | nba.com |
| Ice Hockey | NHL | `api-web.nhle.com/v1/*` | nhl.com |
| Baseball | MLB | `statsapi.mlb.com/api/v1/*` | mlb.com |

Every other sport is listed on the dashboard's Sources page as *not ingested*, with the reason.
No unofficial aggregator is substituted. A row is never published without a source URL on the
league's own domain.

### When a league is listed but not priced

If the per-team sample behind a league is below **20 completed games**, the fixture is published
with its record and official source link but **no markets and no pick**. A line originated on a
one- or three-game sample is a guess with a decimal point on it; the project would rather show a
"withheld" state. This applies to the NBA during its opening week: `stats.nba.com` (the official
prior-season source) does not respond from the build runner and the CDN carries only the current
season, so the NBA rating sample is three games. The reason is written into the row, into
`data/snapshot.json` and onto the Flagged for Review page.

## 2. Inputs

Fixtures and results are fetched at build time; nothing is cached across days in the repository
except the generated JSON snapshot. Each fetch is logged with URL, HTTP status, byte size, SHA-256
and timestamp in `session-4afef1af/data/snapshot.json` (`fetch_log`).

* **Completed results** (training): all final games in a lookback window — 420 days for the NBA and
  NHL, 400 days for MLB.
* **Fixtures** (publishing): games starting inside the window, default 7 days from the start of
  today (UTC). The window is written into the snapshot and displayed on every page.
* **Context fields**: win-loss record as published by the feed, venue, series description and game
  number (MLB), probable pitchers (MLB, only when announced), standings points (NHL).

## 3. Ratings

Two weighted ridge regressions per sport, solved by Gaussian elimination with partial pivoting.

Margin model:

```
margin_i = home_advantage + rating(home_i) − rating(away_i) + e_i
```

Total model:

```
total_i = league_total + offence(home_i) + defence(away_i) + e_i
```

* Weights: `w_i = 0.5 ^ (age_days / 120)`, normalised to mean 1.
* Ridge penalty: `λ = 6.0` on team parameters only, in squared scoring units per game.
* The offence/defence pair is centred after the solve to remove the shift the ridge leaves
  unidentified.
* Rating uncertainty is summarised by the weighted residual standard deviation (`σ_margin`,
  `σ_total`), reported per sport on the dashboard.

## 4. Probabilities

Probabilities are **empirical**, not normal:

* Home win: share of weighted training residuals `e` with `e > −projected_margin`.
* Home handicap `L`: share with `e > L − projected_margin`.
* Over total `T`: share with `e_total > T − projected_total`.

A Laplace correction `(above + 0.5) / (total + 1)` keeps the estimate away from 0 and 1, and the
result is bounded to `[0.01, 0.99]`. This matters most for hockey and baseball, where scoring is
low and discrete.

## 5. Lines and prices

* **Moneyline**: two-way, priced from the win probability.
* **Handicap**: home line `= −(floor(|margin|) + 0.5) × sign(margin)` — always a half-point, so the
  market cannot push. Away line is the mirror.
* **Total**: `floor(projected_total) + 0.5`.
* **Alternates**: the handicap and total are also priced one point either side (`±1`) and shown in
  the match detail.
* **Price**: `1 / (p × 1.045)` — a 4.5% two-way overround — floored at 1.01 so an extreme
  probability never produces an impossible decimal price. Fair odds `1/p` are displayed next to it.

## 6. Opening line versus current line

Two fits per sport:

* **Opening**: only the previous completed season (equal weights). If fewer than 100 prior games
  exist, a league-average opener is used and the record says so.
* **Current**: all available results with the 120-day half-life.

The difference is the information the current season has added. A handicap or total selection is
nominated only when the current projection differs from the opener by at least:

| Sport | Handicap | Total |
|---|---|---|
| NBA | 1.5 points | 2.0 points |
| NHL | 0.30 goals | 0.35 goals |
| MLB | 0.35 runs | 0.45 runs |

The selection is quoted at the **opening** line, where the edge exists, and the current fair line is
shown alongside.

## 7. Picks and confidence

Every match receives a match-winner pick (the higher model probability). Handicap and total picks
are added only when the thresholds above are met.

| Grade | Match winner | Handicap / total |
|---|---|---|
| High | p ≥ 62%, ≥ 40 games per team, and the stability check agrees on the same winner | edge ≥ 2× threshold, p ≥ 60%, ≥ 40 games per team, opener not a league-average fallback |
| Medium | p ≥ 55%, ≥ 20 games per team | edge ≥ threshold, p ≥ 55%, ≥ 20 games per team |
| Low | everything else | everything else |

The stability check is: does our opening model agree on the same winner? When there is no prior
season to build an opener from (for example MLB, whose season is complete and whose prior season is
outside the lookback), we instead refit the model **without the last 14 days of games** and require
that fit to agree. Either way the check is recorded on the pick (`stability_basis`).

If the match-winner pick fails the stability test it is capped at medium. If the opener is a
league-average fallback, handicap/total picks are capped at medium: there is no prior season to have
moved away from, so the "edge" is only a deviation from the league mean.

## 8. Written predictions

Produced only for **high-confidence** picks. Each write-up is composed from verified fields:

* official record and its exact definition,
* last five completed results with scores and opponents,
* venue, series context and probable pitchers when published,
* our opening line, current line and model probability.

No injuries, quotes, transfers or tactical claims are invented. Each prediction carries a `facts`
list, and every fact names the official page it came from. Automated lint rejects:

* anything under 30 words,
* copy where the selection is not stated explicitly,
* promotional language (`guaranteed`, `lock`, `sure thing`, `risk-free`, `banker`, …),
* any pair of predictions sharing more than 55% of their vocabulary.

A failing prediction is withdrawn and listed on the review page; the pick itself stays.

## 9. Backtest

For each sport the model is refitted using only games older than 30 days, then scored on the last
30 days. Reported: accuracy, Brier score, log loss and a calibration table (mean predicted
probability versus observed win rate by band). Small samples are shown as unavailable rather than
papered over.

## 10. Verification gate

`pipeline/verify.py` enforces, on every run:

1. required schema fields and an ISO-8601 start time;
2. at least one source URL on the sport's official domain — otherwise the row is **excluded**;
3. probabilities strictly between 0 and 1, and two-way markets summing to 1 ± 0.01;
4. decimal prices above 1.00;
5. a confidence value in `{low, medium, high}`;
6. start time inside the publishing window;
7. the prediction lint above.

Hard failures (a *published* row failing 1–6, zero fixtures, or more than 25% of ingested rows
excluded) fail `--strict` and stop the publish. Everything else — missing optional fields, stale
context, provider gaps, withdrawn predictions — is published on the Flagged for Review page and does
not block.

## 11. Limitations

* Only three leagues have feeds this pipeline can verify. The dashboard's coverage table names every
  sport it does not ingest and why.
* No market comparison: prices are our own model output, not bookmaker quotes. A "value" claim is
  relative to our own opening line, not to the live market.
* Ratings do not use injuries, travel, rest, weather, umpire/referee assignment or line
  combinations. Those are not in the official feeds used here.
* Early-season samples are thin by definition. The confidence rubric reduces the grade rather than
  hiding the uncertainty, and the backtest reports the sample size.
* The model is a research tool, not betting advice.

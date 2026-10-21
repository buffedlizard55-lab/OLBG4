# METHODOLOGY

This document is the audit trail for every number published by the dashboard. If a formula or a
constant is not written down here, it is not used.

## 1. Capture and verification

| Stage | Data | Source type |
| --- | --- | --- |
| Listing surface (reverse engineering) | OLBG sport taxonomy and in-scope fixture lists: participants, published time, and the market OLBG displayed | OLBG pages (listing source only, never a fact source) |
| Fixture confirmation | Date, time, venue, competition | Official league / tour / federation pages |
| Model inputs | Standings, records, goals or points for and against, ranking prize money | Same official pages |

Transcription is done by `scripts/prepare_inputs.py`, where every table appears as a literal
tuple alongside a comment naming the official page it came from. A value that is not on the page
is not written down. There is no scraping heuristics, no interpolation and no manual estimate
anywhere in the input layer.

## 2. Line origination

All models are deterministic. Probabilities are converted to decimal odds at the last step:

```
decimal odds = 1 / (probability x overround)
two-way overround  = 1.04   (4.0% margin)
three-way overround = 1.05  (5.0% margin)
```

### 2.1 NHL

Inputs per team: GP, W, L, OT, PTS, GF, GA, home/away records, last ten, streak.

```
pct          = PTS / (2 x GP)
rating       = 0.5 + (pct - 0.5) x GP / (GP + 12) + 0.012 x (GF - GA) / GP
p_home_win   = 0.5 + (rating_home - rating_away) x 0.80 + 0.035      [clamped 0.08 .. 0.92]
```

The `GP / (GP + 12)` term shrinks early-season points percentage toward .500; `0.035` is the
home-ice term. Money line is a two-way market including overtime and shootout.

Totals use per-team goal rates shrunk toward a 3.05 goals-per-team league average with weight 10
games, then:

```
expected_home = (gpg_home_for + gpg_away_against) / 2
expected_away = (gpg_away_for + gpg_home_against) / 2
total_mean    = expected_home + expected_away        [clamped 4.5 .. 8.5]
P(over)       = 1 - Phi(line, total_mean, sd = 1.9)
```

The line is the expected total rounded to the nearest 0.5. The puck line is +/-1.5, priced from
`Phi(1.5, expected_home - expected_away, sd = 2.0)`.

### 2.2 NBA

Inputs per team: the official final 2025-26 record and the 2026-27 record to date.

```
strength = 0.75 x (prior_win_pct - 0.5) + 0.25 x (current_win_pct - 0.5) x GP / (GP + 20)
logit    = ln((0.5 + strength) / (0.5 - strength))
p_home   = sigmoid(logit_home - logit_away + 0.24)                    [clamped 0.05 .. 0.95]
spread   = -round_to_half(inverse_normal(p_home) x 11.5)
```

`0.24` corresponds to roughly a 57.5% base home win rate; `11.5` is the assumed standard
deviation of an NBA margin in points. **Totals are not originated for the NBA** because no
official pace or offensive/defensive-efficiency table was captured. That is a deliberate blank,
not an omission.

### 2.3 MLB

Inputs per team: W, L, RS, RA, home and away splits.

```
pct        = 0.5 + (W / (W + L) - 0.5) x 162 / 202
p_home     = sigmoid(logit(pct_home) - logit(pct_away) + 0.17)         [clamped 0.10 .. 0.90]
expected_h = (RS_home / 162 + RA_away / 162) / 2 + 0.12
expected_a = (RS_away / 162 + RA_home / 162) / 2 - 0.12
```

`0.17` is roughly a 54% home-field term. Totals use `sd = 4.2` runs; the run line is +/-1.5 priced
from the same normal on the expected run difference.

### 2.4 United Rugby Championship

Inputs per team: PTS, PL, W, D, L, BP, PF, PA from the official league table.

```
win_rate = (W + 0.5 x D) / PL
rating   = 0.5 + (win_rate + 0.010 x (PF - PA) / PL - 0.5) x PL / (PL + 6)
p_home_raw = 0.5 + (rating_home - rating_away) x 0.90 + 0.05
draw       = 0.055
p_home     = p_home_raw x (1 - draw)
p_away     = (1 - p_home_raw) x (1 - draw)
```

Match points are shrunk toward a 47.5-point competition average with weight 6 rounds, then
`Phi(line, expected_total, sd = 12)`. The handicap is
`-round_to_half(inverse_normal(p_home_raw) x 13)`.

### 2.5 Snooker

Inputs per player: official world-ranking position and prize money.

```
per_frame_q = sigmoid(0.45 x (ln(prize_home) - ln(prize_away)))        [clamped 0.15 .. 0.85]
P(win best of 7) = q^4 + 4 q^4 (1-q) + 10 q^4 (1-q)^2 + 20 q^4 (1-q)^3
```

Because the exact series distribution is available, the frame handicap (-1.5 = win by two frames
or more) and the total-frames line are computed exactly rather than approximated. The total-frames
line is the expected number of frames rounded to the nearest 0.5, and over/under probabilities are
the exact sums of the 4, 5, 6 and 7-frame outcomes either side of that line.

## 3. Pick selection and confidence

The published pick is the model's **match winner** — the higher-probability side on the money
line, excluding the draw. Confidence is a band on that probability:

| Band | Rule |
| --- | --- |
| High | p >= 0.65 and every input verified |
| Medium | 0.57 <= p < 0.65 |
| Low | p < 0.57 |

A match with any unverified input is not priced at all, so it can never be labelled high.

## 4. Written predictions

Predictions exist only for high-confidence picks. Each one:

- names the selection explicitly, using the full team or player name;
- states the verified form line (record, ranking, points difference or prize money);
- references the most recent confirmed match result;
- is at least 30 words and is written separately for each match (no shared template text);
- lists every factual claim underneath, each tied to an official source ID.

`scripts/validate.py` enforces the word count, the selection match, the presence of numeric
evidence, and that every cited source is official and present in the registry.

## 5. Known limitations

- No injury, suspension, team-news, weather or rest-days modelling.
- Early-season shrinkage reduces but does not eliminate small-sample noise.
- The model is not fitted to market prices, so it cannot identify value against a bookmaker; it
  only states our own independent price.
- Where an official page was not machine-readable in this environment (PDC draw, ATP draw, ICC
  ranking table, part of the NBA standings), the affected rows are blank and flagged rather than
  estimated.

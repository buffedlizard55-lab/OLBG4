# Board AF — verified fixtures, originated lines and written predictions

Session `arena/2d25cf78-olbg4` · live dashboard: `https://buffedlizard55-lab.github.io/OLBG4/session-2d25cf78/`

## What this is

A desk built only from official league / governing-body pages captured on 22 October 2026:

* **126 verified fixtures** between the 22 October 21:30 UTC cut-off and 31 October 2026, across six in-scope
  OLBG sports: NHL, EuroLeague, MLB World Series, Top 14, EHF Champions League and SuperLega.
* **Every market the official inputs support** — match winner, handicap / puck / run / set line ladders, match
  totals and team totals — priced by our own model. No bookmaker or OLBG price is an input.
* **30 written predictions**, five per covered sport, each ≥30 words, unique, tied to one selection inside the
  requested −250 … +10,000 window, quoting only figures that appear in the official inputs printed under it.
* **A line-by-line review** of the shared `data/master.json` (336 rows) and an inventory of 40 peer desks.
* **A Flagged for Review page** listing every gap and every judgement call, with the source link.

## Rebuild

```bash
python3 scripts/session-2d25cf78/originate.py      # capture -> desk.json (126 rows, 3,460 markets)
python3 scripts/session-2d25cf78/predict.py        # five picks per sport -> predictions.json
python3 scripts/session-2d25cf78/olbg.py           # OLBG inventory cross-check -> olbg.json
python3 scripts/session-2d25cf78/review.py         # master.json review + our flagged list
python3 scripts/session-2d25cf78/build_site.py     # this site
python3 scripts/session-2d25cf78/verify.py         # 19-check gate, must print 19/19
```

The capture is fetched by `.github/workflows/capture-2d25cf78.yml` (open egress) and committed with a SHA-256
manifest under `data/session-2d25cf78/capture/<UTC_STAMP>/`.

## The arithmetic everyone should know

−250 is a decimal price of 1.400 — a 71.43% implied chance. A pick that is simultaneously “more than 70% to win”
and “no shorter than −250” must therefore sit in a 1.4%‑wide band (70.00%–71.43%). This site publishes the 70%+
match-winner picks it finds even when they are shorter than −250 (labelled as such), and builds the five
predictions per sport from the highest-probability selections that do fall inside the window.

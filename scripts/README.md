# Scripts — build and verification pipeline

All commands are run from the repo root. No network access is needed to rebuild the site
from the captured data; the capture itself was done with the agent's page-fetch tools
because this sandbox's egress allow-list does not include `olbg.com`.

```bash
python3 scripts/build_model.py     # inventory + model config -> data/board.json
python3 scripts/verify.py          # data checks + data/flagged.json + data/verification.json
python3 scripts/build_site.py      # renders index.html, one page per sport, and the report pages
python3 scripts/verify.py --links  # re-run with the internal link audit (needs the HTML)
python3 scripts/build_site.py      # re-render so the site shows the final audit numbers
```

`verify.py` exits non-zero on a hard failure (missing source URL, prediction under 30
words, duplicate prediction body, broken local link), so it can gate a publish step.

## Files

| File | What it is |
|---|---|
| `data/sports.json` | OLBG sport taxonomy: covered ids + evidence URLs, excluded list, unobserved ids left null |
| `data/match_inventory.json` | verbatim capture: fixture, market, selection, tip counts, OLBG event URL |
| `data/model_config.json` | every model constant, each with a `*_basis` string (cited figure or declared assumption) |
| `data/board.json` | output: our probability, price, handicap, total, pick, confidence per match |
| `data/predictions.json` | the 9 high-confidence write-ups with per-fact sources and declared gaps |
| `data/flag_notes.json` | hand-written irregularities (conflicts, capture gaps, blanks) |
| `data/flagged.json` | merged flag list published on `flagged.html` |
| `data/verification.json` | machine output behind `verification.html` |

## Reproducing the capture

1. Open each sport page listed in `data/sports.json` (`https://www.olbg.com/betting-tips/<Sport>/<id>`).
2. Record every row visible without pressing “Load More Tips”, including the event URL
   (`?event_id=…`), the highlighted market, selection, and the printed `x/y Win Tips · z%`.
3. Compare one or two fixtures against a dated listing on the governing body's site — this
   is how the 5-hour timezone offset in OLBG's rendered clock times was found.

# OLBG4 — OLBG Reverse-Engineered: Modelled Lines Dashboard

A from-scratch rebuild of OLBG.com's sports coverage for every in-scope sport
(17 of 24 — excluding football, horse racing, specials, American football,
boxing/UFC/MMA, cycling and hurling):

- **140 upcoming matches + 24 tournament outrights**, each verified line-by-line
  against official sources (a source link is shown on every row).
- **Original betting lines originated by documented statistical models**
  (money line, handicap/spread, totals, plus sport-specific markets) — never
  copied from bookmakers or tipsters.
- A picked winner per match at **low / medium / high** confidence, with unique
  written predictions (verified facts only) for all 31 high-confidence picks.
- Anything unverifiable is left blank and published on a **Flagged for Review** page.

**Live site:** https://buffedlizard55-lab.github.io/OLBG4/ (redirects to `docs/`)

## Repository layout
- `data/olbg-structure.json` — reverse-engineered OLBG structure (sports, IDs, markets).
- `data/raw/` — OLBG event lists as collected 2026-10-21.
- `data/verified/` — line-by-line verified inputs from official sources.
- `data/matches/` — modelled output (originated lines, picks, confidence, predictions).
- `tools/model.py` — mechanical line-origination models.
- `tools/predictions.json` — hand-written high-confidence predictions.
- `tools/build_site.py` — static site generator (validates sources/predictions, link-checks).
- `docs/` — generated GitHub Pages site.
- `COORDINATION.md` — multi-session task board, scope decisions, integration record.

## Rebuild
```bash
python3 tools/model.py        # data/verified -> data/matches
python3 tools/build_site.py   # data/matches  -> docs/
```

Modelled lines are probabilities for analysis — not bookmaker prices and not betting advice.

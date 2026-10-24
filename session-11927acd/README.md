# Board RI — strict release-integrity desk

Open `index.html` for the executive summary and four written High predictions.

## Reproduce

```bash
bash scripts/session-11927acd/run_gates.sh
```

The runner reads `generated_utc` from `data/session-11927acd/meta.json` so a rebuild is byte-stable. Set `RI_GENERATED_UTC` explicitly when creating a new release.

## Pipeline

1. `audit.py` recomputes every stored payload digest, audits all 401 row source types, and records the 17 legacy numerical candidates.
2. `build_data.py` normalizes fair prices, independently recomputes NHL lines from raw standings/schedules, applies official-fixture/OLBG/sample gates, and writes four unique predictions plus all ledgers.
3. `build_site.py` renders 24 static pages: nine desk pages and 15 sport pages.
4. `verify.py` independently recomputes each published selection, checks every price, source, OLBG event, writing rule, shortfall and internal link.

The all-matches inventory includes OLBG listings and clearly labelled official-schedule supplements. Only captured OLBG events can enter the written-pick list. Fair prices are calculations, not sportsbook offers. No injury/team-news claim is made because the pinned capture has no official availability report.

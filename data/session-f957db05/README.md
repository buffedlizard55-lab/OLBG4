# Board V data

| File | Role |
|---|---|
| `raw/` | the official bytes parsed by this board (NHL schedules 2026-10-22…11-02, NHL standings 2026-10-22, MLB schedule + standings, Riot LoL schedule) plus the collector manifest `peer-manifest.json` recording URL, HTTP status, byte count and SHA-256 for each |
| `extracts/` | compact per-sport extracts; every field copied from `raw/`, nothing inferred |
| `lines.json` | model output: probability, fair price, desk price, pick, confidence, handicap and total per fixture |
| `predictions.json` | the written prediction for every High pick, with generated evidence bullets and official source URLs |
| `coverage.json` | live OLBG sport menu, scope decision per sport, official endpoints attempted |
| `flags.json` | the irregularity register rendered on `flagged.html` |

`raw/` is a copy of `data/session-e5f2dad3/raw/` for the files this board consumes, so the dashboard can be rebuilt
even if that board's branch is rebased. The collector's manifest is the authority on capture time and status.

Pipeline scripts live beside this README: `extract.py`, `model.py`, `build_coverage.py`, `facts.py`.

# Session S1 — 2026-10-22 freshness and publication review

This directory is a **read-only audit overlay** for the committed OLBG4 master
board. It deliberately does not modify any earlier session's fixture, odds,
selection, prediction, or root navigation.

## What it publishes

- `index.html` — a filterable table containing every canonical master record.
  It shows an official source link only when the canonical record itself has an
  official-source classification. Current/future rows are structurally carried
  only when the original build marked them verified.
- `flagged.html` — explicit source, freshness, unique-copy, focus-range and
  documentation findings.
- `../data/session-4e9d03cf/review.json` — machine-readable review output.

The review boundary is **2026-10-22 UTC**. It uses committed input only:
`data/master.json`, `session-4afef1af/data/snapshot.json`, and
`session-4afef1af/data/predictions.json`.

## Build and verify

```bash
python3 session-4e9d03cf/build_review.py
python3 session-4e9d03cf/verify_review.py
```

`verify_review.py` checks that the output is deterministic, that every source
shown as official came from a canonical official-tier record, that held rows are
not accidentally promoted, that high templated copy remains held, and that local
review links resolve.

## Important limitation

S1 had no general outbound access to the sports-provider domains. It did not
claim a fresh live read of an official page. Existing official URLs are therefore
published for manual review, and the most recent GitHub Actions pipeline run is
linked as provenance for its NBA/NHL/MLB snapshot.

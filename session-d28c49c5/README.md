# Evidence Desk AD

Published entry point: https://buffedlizard55-lab.github.io/OLBG4/session-d28c49c5/

This isolated dashboard reviews all 233 rows of `data/session-f0622b6e/desk.json`.
It does **not** certify other peer datasets or claim exhaustive OLBG coverage.

## Reproduce

```sh
python scripts/session-d28c49c5/build.py
python scripts/session-d28c49c5/test_build.py
python scripts/audit_publication.py --check
```

Captured official response bytes and SHA-256 manifests live in
`data/session-d28c49c5/`. Capture run:
https://github.com/buffedlizard55-lab/OLBG4/actions/runs/39775775443

The optional manual-dispatch capture workflow updates evidence on the session
branch only. Run the builder after capture and verify before publication. There
is no claim of automatic live multi-sport coverage. The last fixed review cutoff
is documented separately from actual response retrieval timestamps.

## Findings

- 56 official fixture records parsed from NHL/MLB response bytes.
- 233 peer rows reviewed; exact matching deliberately uses side order, full names
  and UTC start time. An unmatched row is **unverified**, not proven false.
- 39 prior High-labeled selections have reciprocal fair odds below 70%.
- Prior High assignment depends on a prewritten-prediction lookup, not a
  probability/calibration gate. The generator also clamps some featured decimal
  prices to 1.42/1.40 instead of retaining the original calculated price.
- Official fixture details are separated from exploratory model outputs.
- NHL own fair lines: independent Poisson baseline, fixed 20-game shrinkage,
  explicitly Low confidence. Goals-for/against input totals include extra-time
  scoring, so regulation markets are proxies only. No executable bookmaker quote,
  calibrated edge, or high-confidence recommendation is claimed.
- No High predictions are released without independent verification of their
  form/history inputs and confidence. Empty confirmed values are intentional.

Root files remain read-only because PR #102 owns their integration scope. A link
request is recorded in COORDINATION.md. All local links are tested; successful
local link checks do not establish availability of external official URLs.

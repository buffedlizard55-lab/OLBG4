# Board AF — OLBG Evidence Desk

Static dashboard for the 22 October 2026 evidence capture. Open `index.html`.

## Current verified output

- Capture `20261022T210227Z`, generated `2026-10-22T21:03:13Z`; 112 raw responses hash-checked.
- 220 officially confirmed fixtures; 212 priced with independent fair lines across ice hockey, basketball, baseball and tennis. Eight LoL fixtures are confirmed but unpriced.
- 19 High selections with unique 50–58-word predictions. Seven are +1.5 hockey handicaps inside the requested −250…+10,000 window; 12 moneyline High picks are shorter than −250 and labelled separately.
- 17 OLBG sport category pages. Only ice hockey meets the five-focus-match target; every other shortfall is explicit.
- 181 flagged items and 558 read-only peer-review findings. Unmatched OLBG listings are not promoted into the official fixture table.

## Rebuild and verify

```bash
bash scripts/session-0d3b826c/build_all.sh
```

The final verifier re-hashes every raw response, recomputes every price and confidence grade, checks prediction facts/length/uniqueness/selection clarity, validates per-sport counts and flags, resolves every local link, and runs a byte-identical rebuild.

## Evidence boundary

Official pricing inputs: NHL API, Liiga API, EuroLeague/EuroCup official games feeds, MLB Stats API, WTA tournament/rankings APIs and Riot's official schedule. OLBG is used only for public listing structure. NBA responses were HTTP 403; two ICC routes were 404. EuroLeague roster/statistics pages were read through the page reader after runner HTTP 429 responses; exact excerpts are in `data/session-0d3b826c/live_checks.json`.

No bookmaker or OLBG price enters a model. All displayed prices are margin-free model estimates, not observed market quotes or guarantees. Unsupported values remain blank and flagged.

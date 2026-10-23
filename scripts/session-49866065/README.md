# FA — strict public-evidence desk

**Scope:** the brief's exact 15 sports. Python 3.11+, standard library only.
**Site:** `session-49866065/index.html`.

## Reproduce the pinned publication (no network)

```sh
python3 scripts/session-49866065/build.py
python3 -m unittest discover -s scripts/session-49866065 -p 'test_*.py' -v
# A second build must not change desk.json or generated HTML:
python3 scripts/session-49866065/build.py
git diff --exit-code -- data/session-49866065/desk.json session-49866065
```

`data/session-49866065/capture/manifest.json` pins the capture. Gzip bytes are
retained in Git (about 5 MB compressed). SHA-256 is over uncompressed bytes.
The separate `review.json` pins **structural**, not factual, legacy-row findings.
`review.py` is deliberately not run by the site builder: a new review baseline
must be explicitly chosen, not silently changed when peers commit new data.

## Refresh

The GitHub workflow **FA evidence capture and strict dashboard tests** can capture
public sources from an open-egress runner. Dispatch with `capture=true` on the
fixed `arena/49866065-olbg4` branch; it preserves raw evidence only on that branch.
The current sandbox cannot fetch sports sites or Azure artifact downloads; this
is why evidence is pulled back through Git. Build, test, inspect flags, open a PR,
wait for CI, merge and confirm Pages before calling a new capture published.
`capture=false` runs offline tests. PRs affecting this desk run its offline gate.

This is **not** an unattended all-sport daily publishing system. Existing dated
competition URLs need maintenance; a scheduled run of fixed URLs is not a safe
substitute for a rolling calendar. This limitation is displayed on the site.

## Design boundaries

- `capture.py`: public reads only, bounded response size, per-host spacing,
  fetched OLBG robots policy fails closed. No browser challenge bypass/login.
- `core.py`: hash validation, safe lexical public payload parsing, JSON pointers,
  HTML spans, URL/time normalization, independent Log5 fair prices.
- `parsers.py`: NHL, MLB, EuroLeague/EuroCup, WTA, Liiga, Cricket Australia, URC.
  Other sports retain coverage gaps rather than invented rows. NBA adapter
  requires actual official JSON; 403 responses do not become data.
- `build.py`: 24 accessible static pages with no external JS/CSS/font dependency,
  source-linked tables, exact 15 categories, mobile navigation, search/filters,
  fair-line separation, field evidence and Flagged for Review.
- `test_desk.py`: adversarial payload/URL tests, source equality, price arithmetic,
  reconciliation, confidence/blank-value gates, deterministic builds and local
  file/fragment links.

**Confidence:** all 179 currently priced winner rows are low research confidence.
No backtest, complete injury/lineup research or OLBG posting eligibility exists.
No High picks or write-ups are invented to fill five-per-sport quotas. Own-line
odds filtering is not claimed to be an offered-price filter. Missing injury data
means unknown, not no injuries. Every unsupported factual cell stays blank.

## Independence and settlement

No OLBG percentages, bookmaker odds or public tip votes feed our own prices.
A Beta(2,2) prior and Log5 comparison are declared subjective choices, not official
facts. No fitted home edge. NHL regulation handicaps/totals cannot be priced from
season goals that include overtime/shootout effects; those markets are withheld.
Conditional MLB games are unpriced. No market completeness claim is made.

## Coordination

Other sessions' files remain read-only. The integration change is only an
additive pointer on root `index.html`, after a specific coordination-board claim.
Legacy claims remain historical and are not endorsed by this desk.

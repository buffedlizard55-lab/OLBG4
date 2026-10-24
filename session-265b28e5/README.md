# Board GF — dated 15-sport evidence desk

**Review instant:** 2026-10-24 17:10:06Z

**OLBG capture:** 2026-10-23 21:36:58Z

**Earlier official-source desk cutoff:** 2026-10-23 21:40:00Z

This is a conservative audit and static dashboard, not a live odds feed. It preserves the 15 requested sports exactly, shows all 58 captured OLBG event IDs whose saved start time was still in the future at the fixed review instant, and links each OLBG row to its own listing. Four event/date crosswalks were checked against official sources (PCB, Cork GAA, Kilkenny GAA and EHF); three of those official pages state the start time. For Pakistan v England, the PCB page states the teams/date/venue but not the start time, which remains an OLBG/source-desk observation.

No prediction is released. The previous desk has five future numeric candidates at or above 70% inside the requested price band, but none maps to an exact OLBG event in this snapshot and their form claims, line inputs and availability were not independently reconciled. Old prose is withheld. Unsupported source fields remain blank and appear on **Flagged for Review**.

## Pages

- `index.html` — executive dashboard, gate status and sport coverage
- `olbg.html` — captured OLBG upcoming listings (not live-checked)
- `coverage.html` — exact 15-sport coverage matrix and OLBG hub links
- `sports/*.html` — one subpage for each requested sport
- `fixtures.html` — all 114 historical source-desk fixture rows, separated by time status
- `picks.html` — five unreleased numeric candidates; no recommendations
- `markets.html` — 452 historical fair-line families / 997 outcomes, marked unaudited
- `sources.html` — official crosswalks, capture integrity, and three non-reproducible OLBG hub spot-checks
- `flagged.html` — source, freshness, schedule, probability, and availability issues
- `methodology.html` — time, scope, crosswalk, and release gates

## Rebuild and verify

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/audit.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/build_site.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/session-265b28e5/verify.py
```

Generated machine-readable files:

- `data/session-265b28e5/audit.json` — event-, outcome-, source-, capture-, and finding-level audit
- `data/session-265b28e5/dashboard.json` — machine-readable landing-page and sport-page index

The build reads Board FB inputs in `data/session-48de8c1d/` without changing them. The raw capture manifest and its successful payload hashes are checked; a matching hash proves payload integrity only, not factual support.

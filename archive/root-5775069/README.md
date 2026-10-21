# Preserved root desk — commit 5775069 (Board N, session `arena/8070bc18-olbg4`)

These pages served the repository root before Board P (`arena/d908be47-olbg4`) replaced the landing page with the
consolidated 312-row master board. They are kept so nothing is lost.

What changed when they were moved here:

- **Nothing in their text, markup or data.** The only edit is mechanical: every relative `href`/`src` gained the
  `../../` prefix it needs one directory deeper, so the pages, their stylesheet (`assets/integrated.css`) and their
  links to `session-*/`, `docs/`, `audit/` and `verification.html` still resolve. Verified by
  `python3 scripts/audit_publication.py` → 0 broken local targets.
- Their data files were never touched: `data/integrated/`, `data/matches.json`, `data/board_k/`, `docs/` and every
  `session-*/` directory are exactly as that session left them.

Entry point: `index.html`.

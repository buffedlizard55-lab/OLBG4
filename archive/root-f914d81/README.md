# Preserved root desk — commit f914d81 (integration sessions `83451f65` / `8070bc18`)

The root pages that `main` served immediately before Board P (`arena/d908be47-olbg4`) published the consolidated
312-row master board. Kept so nothing is lost.

The only edit is mechanical: relative `href`/`src` values gained the `../../` prefix needed one directory deeper, so the
pages, their stylesheet and their links to `session-*/`, `docs/`, `audit/` and `verification.html` still resolve
(`scripts/audit_publication.py`: 0 broken local targets). Their data files were not touched.

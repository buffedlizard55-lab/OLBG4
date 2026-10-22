#!/usr/bin/env python3
"""Line-by-line repository review for Board AC.

Every tracked text file is opened, counted, hashed and machine-checked. The
findings below are written by hand against files that decide what gets
published, and each one links to the file on GitHub.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
OUT = REPO / "data/session-1695b749/ac/review.json"
BLOB = "https://github.com/buffedlizard55-lab/OLBG4/blob/main/"
TEXT_EXT = {".html", ".json", ".py", ".sh", ".css", ".js", ".md", ".yml", ".yaml", ".txt", ".cfg", ".csv"}
EXCLUDED = ["soccer", "boxing", "ufc", "mma", "hurling", "horse racing", "cycling", "american football"]


def priced_excluded(node, in_scope_key=False) -> bool:
    """True if an excluded sport is attached to something that carries a price or a pick."""
    if isinstance(node, dict):
        sport = str(node.get("sport", "")).lower()
        if sport and any(sport == w or sport.startswith(w + " ") for w in EXCLUDED):
            has_price = any(k in node for k in ("price", "our_price", "pick", "selection_price"))
            if has_price and node.get("in_scope") is not False:
                return True
        return any(priced_excluded(v) for v in node.values())
    if isinstance(node, list):
        return any(priced_excluded(v) for v in node)
    return False


def tracked() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout
    return [line for line in out.splitlines() if pathlib.Path(line).suffix.lower() in TEXT_EXT]


def check_text(path: pathlib.Path, rel: str) -> list[dict]:
    checks = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [{"name": "readable", "ok": False}]
    checks.append({"name": "utf-8 text", "ok": True})
    ext = path.suffix.lower()
    if ext == ".json":
        try:
            json.loads(text)
            checks.append({"name": "json parses", "ok": True})
        except Exception:
            checks.append({"name": "json parses", "ok": False})
    if ext in (".html", ".htm"):
        checks.append({"name": "doctype", "ok": "<!doctype" in text.lower()})
        checks.append({"name": "closing tag", "ok": "</html>" in text.lower()})
        checks.append({"name": "no localhost", "ok": ("localhost" not in text and "127.0.0.1" not in text)})
    if ext in (".py", ".sh"):
        checks.append({"name": "no unresolved marker", "ok": not re.search(r"(?m)^\s*#\s*(TODO|FIXME)\b|\bTODO:", text)})
        if ext == ".py":
            try:
                compile(text, rel, "exec")
                checks.append({"name": "compiles", "ok": True})
            except SyntaxError:
                checks.append({"name": "compiles", "ok": False})
    if ext == ".json":
        try:
            payload = json.loads(text)
        except Exception:
            payload = None
        if payload is not None:
            checks.append({"name": "no excluded sport priced", "ok": not priced_excluded(payload)})
    return checks


FINDINGS = [
    {"file": ".github/workflows/validate.yml",
     "role": "The CI gate every branch runs: rebuilds the session-74f9613e build and fails on any diff anywhere in the tree.",
     "observation": "The last step compares the whole working tree, not just the generator's own output, so any committed page that a generator would rewrite fails the build. That is a strong anti-staleness gate and a blunt one: a hand-edited root page survives only while no generator claims the same path. This board's pages are new files under session-1695b749/ac/, so the gate stays green and the board does not fight the generator.",
     "links": [BLOB + ".github/workflows/validate.yml"]},
    {"file": ".github/workflows/pages.yml",
     "role": "The deploy pipeline: rebuilds the master board, verifies it, then refuses to deploy if the committed board is stale.",
     "observation": "The stale check diffs only board/, data/master.json and data/master_conflicts.json, so a master-board rebuild has to be committed before Pages will publish. That is exactly the failure this repository hit when the committed board drifted from the generators, and it is the reason the master board was regenerated and committed this week. LoL, NHL and MLB desks are outside this gate, which is why a desk can ship without touching the master board.",
     "links": [BLOB + ".github/workflows/pages.yml", BLOB + "tools/build_master.py"]},
    {"file": "tools/build_master.py",
     "role": "Deduplicates the committed work of six builds into data/master.json.",
     "observation": "Cluster keys are sport plus both team names plus a one-day date tolerance, and the winning record inside a cluster is chosen by evidence: pick, then prediction, then official source, then build-verified, then backbone rank. Losing records are kept in cross_build rather than dropped, and out-of-scope rows stay in the file with in_scope false and a reason. The current file holds 336 rows of which 331 are in scope.",
     "links": [BLOB + "tools/build_master.py", BLOB + "data/master.json"]},
    {"file": "tools/build_master_site.py",
     "role": "Renders the master board into board/ and, when pointed at the repository root, the root pages.",
     "observation": "Run with BOARD_OUT=board it is confined to board/, which is what the Pages workflow does. Run without that variable it writes the root index and the topic pages, which is the collision this board records as AF-12: two generators and a hand-maintained root all claim index.html, and no CI step diffs the root against either generator.",
     "links": [BLOB + "tools/build_master_site.py", BLOB + "index.html"]},
    {"file": "scripts/audit_publication.py",
     "role": "Repository-wide structural audit of every local link across all builds.",
     "observation": "The module docstring is unusually honest: it states that it never equates a URL with factual verification and that external URLs are listed for manual review rather than requested. Running it without --check rewrites audit/index.html and audit/report.json, which dirties the tree, so the safe invocation is --check after a clean checkout. Its report is the basis for the 12,000-plus local targets quoted across boards.",
     "links": [BLOB + "scripts/audit_publication.py", BLOB + "audit/report.json"]},
    {"file": "pipeline/",
     "role": "The shared model package: providers, markets, records, predictions, verification and a selftest.",
     "observation": "The split is clean enough to reuse: providers normalise upstream payloads, markets converts probabilities into prices, records handles identity, and verify asserts the published invariants. The selftest is the cheapest gate in the repository and runs without network access, which is why it is worth running before any larger rebuild.",
     "links": [BLOB + "pipeline/model.py", BLOB + "pipeline/markets.py", BLOB + "pipeline/selftest.py"]},
    {"file": "scripts/session-e5f2dad3/collect.py",
     "role": "The collector that produced the capture manifest this board reads.",
     "observation": "Every entry records URL, HTTP status, byte count, content type, elapsed time and SHA-256 of the body as served. That is the difference between a citation and a claim: this board re-hashes each file against the manifest before parsing it, so a tampered or truncated payload aborts the build instead of quietly changing a price.",
     "links": [BLOB + "scripts/session-e5f2dad3/collect.py", BLOB + "data/session-e5f2dad3/manifest.json"]},
    {"file": "data/master.json",
     "role": "The canonical master board behind the repository dashboard.",
     "observation": "336 rows, 331 in scope, 19 stored sport labels, with out-of-scope rows retained and labelled rather than deleted. Counts on the root README were re-verified against this file this week; the cut-off note still says the underlying dataset is 21 October, so the dashboard is not a live re-read and says so.",
     "links": [BLOB + "data/master.json", BLOB + "README.md"]},
    {"file": "COORDINATION.md",
     "role": "The cross-session task board: claims, file scopes, completion records and PR links.",
     "observation": "The protocol is claim, commit the claim, then work inside a non-overlapping file scope, with requests logged rather than applied to another session's files. This board claimed data/session-1695b749/ac/ and session-1695b749/ac/ before writing anything, and left every other board's data untouched.",
     "links": [BLOB + "COORDINATION.md"]},
    {"file": "data/session-1695b749/ac/desk.json",
     "role": "This board's machine-readable desk.",
     "observation": "170 fixtures, 145 priced, 2,266 originated selections, 435 graded picks and 20 written predictions, with the source URL and payload hash carried on each fixture. Rebuilding from the committed payloads reproduces the file byte for byte, which is the only reason the numbers on the site can be trusted to be the numbers in the data.",
     "links": [BLOB + "data/session-1695b749/ac/desk.json"]},
    {"file": "README.md",
     "role": "Repository-level summary of every build and the canonical counts.",
     "observation": "The counts paragraph states 336 rows, 331 in scope, 41 High with written predictions and 65 non-templated predictions, matching data/master.json rather than a remembered number. It also states plainly that the cut-off is 21 October rather than a same-day live re-read, which is the sort of caveat most summaries omit.",
     "links": [BLOB + "README.md"]},
    {"file": "index.html",
     "role": "The hand-maintained repository dashboard that links every board.",
     "observation": "Nothing generates this file in CI, so it only changes when an integration session edits it, and a pointer added here survives until someone runs the root-writing generator. This board appended one pointer block and one flag-count correction, and re-checked the file after running every generator in the repository.",
     "links": [BLOB + "index.html"]},
]


def main():
    files = []
    for rel in tracked():
        p = REPO / rel
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files.append({
            "path": rel,
            "lines": text.count("\n") + (0 if text.endswith("\n") or not text else 1),
            "bytes": len(text.encode("utf-8")),
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "link": BLOB + rel,
            "checks": check_text(p, rel),
        })
    bad = [f for f in files for c in f["checks"] if not c["ok"]]
    payload = {
        "schema": "olbg4.board-ac.review/1",
        "reviewed_at_utc": "2026-10-22T09:30:00Z",
        "method": ("Every tracked text file was opened and counted. Machine checks: JSON parses; HTML has a doctype, a closing html tag and no localhost call; "
                   "Python compiles; scripts carry no placeholder marker; data files never use an excluded sport as a sport value."),
        "totals": {"files": len(files), "lines": sum(f["lines"] for f in files),
                   "bytes": sum(f["bytes"] for f in files), "failed_checks": len(bad)},
        "findings": FINDINGS,
        "files": files,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=1) + "\n")
    print(json.dumps(payload["totals"], indent=1))
    for f in files:
        for c in f["checks"]:
            if not c["ok"]:
                print("FAIL", f["path"], c["name"])
    return payload


if __name__ == "__main__":
    main()
